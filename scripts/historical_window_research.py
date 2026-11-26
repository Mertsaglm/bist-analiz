"""Ridge eğitim pencerelerini ve iki piyasanın tarihsel ekonomik vekillerini ölç."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
from importlib.metadata import version
import math
from pathlib import Path

import numpy as np
import pandas as pd

from advisor import calendar, history, learning, policy, specialized
from advisor.ledger import canonical, cents
from scripts import forecast_research as research
from scripts.portfolio_research import LIGHTGBM

ROOT = research.ROOT
PROTOCOL = ROOT / 'docs/TARIHSEL-SINAMA-ON-KAYIT-2026-11-26.md'
SENSITIVITY = ROOT / 'docs/TARIHSEL-SINAMA-DUYARLILIK-2026-11-26.md'
HORIZON = 20
START = '2022-01-01'
WINDOWS = {'ridge-2y': 2, 'ridge-3y': 3, 'ridge-5y': 5, 'ridge-expanding': None}
BIST_ACTIVE = (*WINDOWS, 'momentum', 'lambdarank')
GOLD_ACTIVE = (*WINDOWS, 'ridge-separate-3y', 'sma50')
NAMES = {'bist': learning.ADAPTIVE_FEATURES, 'gold': learning.FEATURES}
LEG_NAMES = learning.FEATURES + specialized.GOLD_LEGS


def period(day):
    year = day[:4]
    return '2022' if year == '2022' else '2023–2024' if year < '2025' else '2025+'


def cadence(sessions, future=HORIZON):
    first = next(i for i, day in enumerate(sessions) if day >= START)
    return range(first, len(sessions) - future, HORIZON)


def features_for(panel, market):
    """Sinyal filtresi yalnız bu seanstaki ve önceki fiyatları görür."""
    names = NAMES[market] if market == 'bist' else LEG_NAMES
    valid = panel.loc[panel.quality_ok].dropna(subset=names)
    if market == 'bist':
        counts = valid.groupby('date').symbol.transform('size')
        valid = valid.loc[counts.ge(24)]
    return valid.sort_values(['date', 'symbol'])


def targets(signal, panel, market):
    by_symbol = panel.groupby('symbol', sort=False)
    ends = panel[['date', 'symbol']].assign(
        label_end=by_symbol.date.shift(-HORIZON),
        end_ok=by_symbol.eligible_endpoint.shift(-HORIZON).eq(True),
        forward_pct=100 * (by_symbol.total_close.shift(-HORIZON) / panel.total_close - 1),
    )
    if market == 'gold':
        for leg in ('ons_usd', 'usdtry'):
            ends[leg + '_target'] = 100 * np.log(by_symbol[leg].shift(-HORIZON) / panel[leg])
    rows = signal.drop(columns=['label_end', 'forward_pct']).merge(
        ends, on=['date', 'symbol'], validate='one_to_one')
    valid = rows.loc[rows.end_ok & rows.forward_pct.notna()].copy()
    if market == 'bist':
        # Eğitimde de hedef sepeti, karar anında sabitlenmiş aynı isimlerdir.
        sizes = rows.groupby('date').symbol.size()
        actual = valid.groupby('date').symbol.transform('size')
        valid = valid.loc[actual.eq(valid.date.map(sizes))].copy()
        valid['forward_pct'] -= valid.groupby('date').forward_pct.transform('mean')
    return valid.sort_values(['date', 'symbol'])


def gap_tolerant_bist_features(panel):
    """Yalnız göstergeler gözlenen barlarda ilerler. Seans vadesi panelde kalır."""
    observed = panel.close.gt(0) & panel.total_close.gt(0)
    coverage = observed.groupby(panel.symbol).transform(lambda x: x.rolling(200).sum())
    features = learning.features(panel.loc[observed], HORIZON)
    keys = ['date', 'symbol']
    fields = [*NAMES['bist'], 'quality_ok']
    features = features[keys + fields].merge(
        panel.loc[coverage.ge(190), keys], on=keys, validate='one_to_one')
    result = panel.drop(columns=fields).merge(features, on=keys, how='left', validate='one_to_one')
    result['quality_ok'] = result.quality_ok.eq(True)
    return result


def forecasts(training, testing, market):
    cutoff = testing.date.iloc[0]
    prior = training.loc[training.label_end.lt(cutoff)]
    windows = {}
    fits = {}
    if prior.date.nunique() < 400:
        return None, fits
    result = testing[['symbol']].set_index('symbol').copy()
    for arm, years in WINDOWS.items():
        first = (pd.Timestamp(cutoff) - pd.DateOffset(years=years)).date().isoformat() if years else None
        sample = prior.loc[prior.date.ge(first)] if first else prior
        n_dates = sample.date.nunique()
        if n_dates < 400:
            return None, fits
        windows[arm] = sample
        fits[arm] = {'first': sample.date.min(), 'last': sample.date.max(),
                     'last_label': sample.label_end.max(), 'dates': n_dates, 'rows': len(sample)}
        result[arm] = learning.predict(learning.fit(sample, 20, NAMES[market]), testing)

    sample = windows['ridge-3y']
    if market == 'bist':
        from lightgbm import LGBMRanker

        result['momentum'] = ((100 + testing.momentum120) / (100 + testing.momentum20)).to_numpy()
        labels = np.ceil(sample.groupby('date').forward_pct.rank(pct=True) * 5).astype(int) - 1
        ranker = LGBMRanker(**LIGHTGBM, objective='lambdarank', lambdarank_truncation_level=5)
        ranker.fit(sample[NAMES[market]], labels, group=sample.groupby('date', sort=False).size().tolist())
        result['lambdarank'] = ranker.predict(testing[NAMES[market]])
    else:
        legs = [learning.predict(learning.fit(sample.assign(forward_pct=sample[leg + '_target']),
                                              20, LEG_NAMES), testing)
                for leg in ('ons_usd', 'usdtry')]
        result['ridge-separate-3y'] = 100 * np.expm1((legs[0] + legs[1]) / 100)
        result['zero'] = 0.
        result['sma50'] = testing.trend50.to_numpy()
    return result, fits


def bist_prices(panel, sessions):
    valid = panel.loc[panel.close.gt(0) & panel.total_close.gt(0)]
    close = valid.pivot(index='date', columns='symbol', values='total_close').reindex(sessions)
    op = valid.assign(adj_open=valid.open * valid.total_close / valid.close)
    return close, op.pivot(index='date', columns='symbol', values='adj_open')


def bist_episode(prices, opening, closing, scores, cost_scale):
    symbols = scores.index
    marks = prices[0].loc[opening:closing].reindex(columns=symbols)
    entries = prices[1].reindex(index=[opening], columns=symbols).iloc[0]
    misses = marks.isna().any() | entries.isna()
    if misses.any():
        return None, misses.index[misses].tolist()
    fee = (.002 * 1.05 + .00003) * cost_scale
    slip = .0005 * cost_scale
    mark_ratio = marks / entries
    paths = mark_ratio * ((1 - slip) * (1 - fee) / ((1 + slip) * (1 + fee)))
    basket = paths.mean(axis=1)
    weights = {'passive': basket, 'cash': .8 * basket + .2}
    shares = {'passive': 1., 'cash': .8}
    for arm in scores:
        ranked = scores[arm].sort_values(ascending=False, kind='stable')
        weights[arm] = .8 * basket + .2 * paths[ranked.index[:5]].mean(axis=1)
        shares[arm] = 1.
    result = {}
    for arm, path in weights.items():
        trace = np.r_[1., path.to_numpy()]
        sold = (trace[-1] - (1 - shares[arm])) / (1 - fee)
        bought = shares[arm] / (1 + fee)
        result[arm] = {'net_pct': 100 * (trace[-1] - 1),
                       'drawdown_pct': 100 * np.min(trace / np.maximum.accumulate(trace) - 1),
                       'turnover_pct': 100 * (bought + sold),
                       'fee_try': 50_000 * fee * (bought + sold)}
    return result, []


def bist_forecast_metrics(scores, target):
    realized = target.set_index('symbol').forward_pct.reindex(scores.index)
    if realized.isna().any():
        return None
    result = {}
    for arm in scores:
        rank = scores[arm].sort_values(ascending=False, kind='stable')
        ic = rank.rank().corr(realized.rank()) if rank.nunique() > 1 and realized.nunique() > 1 else np.nan
        result[arm] = {'rank_ic': ic if np.isfinite(ic) else None,
                       'top5_pct': realized.loc[rank.index[:5]].mean(),
                       'mae_pct': (scores[arm] - realized).abs().mean() if arm in WINDOWS else None}
    return result


def mean_metrics(rows, arm):
    result = {}
    for field in ('rank_ic', 'top5_pct', 'mae_pct'):
        values = [r['forecast'][arm][field] for r in rows if r['forecast'][arm][field] is not None]
        result[field] = float(np.mean(values)) if values else None
    return result


def bist_summary(rows):
    if not rows:
        return {}
    return {
        scale: {arm: {
            'windows': len(rows),
            'mean_net_pct': np.mean([r['economics'][scale][arm]['net_pct'] for r in rows]),
            'mean_passive_excess_pct': np.mean([r['economics'][scale][arm]['net_pct']
                                               - r['economics'][scale]['passive']['net_pct'] for r in rows]),
            'worst_drawdown_pct': min(r['economics'][scale][arm]['drawdown_pct'] for r in rows),
            'mean_turnover_pct': np.mean([r['economics'][scale][arm]['turnover_pct'] for r in rows]),
            'mean_fees_try': np.mean([r['economics'][scale][arm]['fee_try'] for r in rows]),
        } for arm in (*BIST_ACTIVE, 'cash', 'passive')} for scale in ('1x', '2x')
    }


def simultaneous_bist(branches, schedule, matched):
    keys = [(branch, arm) for branch in branches for arm in BIST_ACTIVE]
    lookup = {branch: {r['signal']: r for r in rows} for branch, rows in branches.items()}
    comparison = []
    for day in schedule:
        comparison.append([lookup[branch][day]['economics']['1x'][arm]['net_pct']
                           - lookup[branch][day]['economics']['1x']['passive']['net_pct']
                           for branch, arm in keys] if day in matched else [np.nan] * len(keys))
    values = np.asarray(comparison)
    if len(matched) < 12:
        return {}
    center = np.nanmean(values, axis=0)
    rng = np.random.default_rng(20261126)
    intervals = {}
    for block in (3, 6):
        starts = rng.integers(len(values), size=(4000, math.ceil(len(values) / block), 1))
        indices = ((starts + np.arange(block)) % len(values)).reshape(4000, -1)[:, :len(values)]
        draws = values[indices]
        counts = np.isfinite(draws[:, :, 0]).sum(axis=1)
        draws, counts = draws[counts > 0], counts[counts > 0]
        means = np.nansum(draws, axis=1) / counts[:, None]
        radius = np.quantile(np.max(np.abs(means - center), axis=1), .95)
        intervals[str(block)] = {f'{branch}/{arm}': [avg - radius, avg + radius]
                                 for (branch, arm), avg in zip(keys, center)}
    return intervals


def evaluate_bist(panel, sessions, selected):
    traded = panel.close * panel.volume
    liquid = traded.groupby(panel.symbol).transform(lambda x: x.rolling(63, min_periods=50).median())
    liquid_rank = liquid.where(panel.close.notna()).groupby(panel.date).rank(ascending=False, method='first')
    prices = bist_prices(panel, sessions)
    branches = {}
    for name, criterion in [('fixed', panel.symbol.isin(selected)), ('liquid', liquid_rank.le(30))]:
        subset = panel.loc[criterion].copy()
        # Cross-sectional features must use the same historical candidate universe.
        momentum = subset.momentum20.where(subset.quality_ok)
        subset['relative20'] = subset.momentum20 - momentum.groupby(subset.date).transform('median')
        breadth = subset.trend50.gt(0).where(subset.trend50.notna() & subset.quality_ok)
        subset['breadth50'] = breadth.groupby(subset.date).transform('mean').astype(float)
        signals = features_for(subset, 'bist')
        training = targets(signals, panel, 'bist')
        daily_signals = dict(iter(signals.groupby('date')))
        trained_dates = dict(iter(training.groupby('date')))
        outcomes = []
        for i in cadence(sessions):
            signal, opening, closing = sessions[i], sessions[i + 1], sessions[i + HORIZON]
            row = {'signal': signal, 'entry': opening, 'exit': closing,
                   'missing_symbols': [], 'economics': None, 'forecast': None}
            outcomes.append(row)
            testing = daily_signals.get(signal)
            if testing is None:
                row['status'] = 'insufficient_signal_coverage'
                continue
            row['symbols'] = testing.symbol.tolist()
            scores, row['training'] = forecasts(training, testing, 'bist')
            if scores is None:
                row['status'] = 'insufficient_training_coverage'
                continue
            row['scores'] = scores.to_dict()
            if signal in trained_dates:
                row['forecast'] = bist_forecast_metrics(scores, trained_dates[signal])
            base, missing = bist_episode(prices, opening, closing, scores, 1.)
            if base is None:
                row.update(status='incomplete_prices', missing_symbols=missing)
                continue
            stress, _ = bist_episode(prices, opening, closing, scores, 2.)
            row.update(status='complete', economics={'1x': base, '2x': stress})
        branches[name] = outcomes

    matched = set.intersection(*({r['signal'] for r in rows if r['economics']} for rows in branches.values()))
    forecasts_matched = set.intersection(*({r['signal'] for r in rows if r['forecast']} for rows in branches.values()))
    reports = {}
    for name, rows in branches.items():
        main = [r for r in rows if r['signal'] in matched]
        forecast_rows = [r for r in rows if r['signal'] in forecasts_matched]
        reports[name] = {
            'status_counts': dict(Counter(r['status'] for r in rows)),
            'matched': bist_summary(main), 'all_priced': bist_summary([r for r in rows if r['economics']]),
            'periods': {era: bist_summary([r for r in main if period(r['signal']) == era])
                        for era in ('2022', '2023–2024', '2025+')},
            'forecast_matched': {arm: mean_metrics(forecast_rows, arm) for arm in BIST_ACTIVE},
            'episodes': rows,
        }
    schedule = [sessions[i] for i in cadence(sessions)]
    return {'schedule': schedule, 'economic_paired_windows': len(matched),
            'forecast_paired_windows': len(forecasts_matched), 'branches': reports,
            'simultaneous_excess_intervals_pct': simultaneous_bist(branches, schedule, matched)}


def gram_prices(mid, spread):
    bid = 2 * mid / (2 + spread)
    return bid * (1 - .0005), bid * (1 + spread) * (1 + .0005)


def gold_portfolio(mids, execution_signals, arm, spread):
    tax = .002
    fee_cfg = {'market': 'gold', 'gold_buy_tax_rate': tax}
    hurdle = (1 + spread) * (1 + .0005) / (1 - .0005) * (1 + tax) - 1
    # Separate 80/20 sleeves preserve the identical core and contribution split.
    cash, qty = [0, 0], [0, 0]
    target = arm == 'passive'
    month = ''
    contributed = fees = execution_cost = turnover = 0
    buys = sells = 0
    trace = []
    for day, mid in mids.items():
        bid, ask = gram_prices(mid, spread)
        flow = 0
        if day[:7] != month:
            flow = 50_000_00 if not month else 5_000_00
            cash[0] += flow * 4 // 5
            cash[1] += flow // 5
            month = day[:7]
            contributed += flow
        if day in execution_signals and arm in GOLD_ACTIVE:
            signal = execution_signals[day].get(arm)
            if signal is not None:
                target = signal > (0 if arm == 'sma50' else 100 * hurdle)
        if not target and qty[1]:
            sale = cents(qty[1] / 100 * bid)
            cash[1] += sale
            turnover += sale
            execution_cost += cents(qty[1] / 100 * (mid - bid))
            qty[1] = 0
            sells += 1
        if flow or day in execution_signals:
            for sleeve in range(1 + int(target)):
                grams = policy.quantity_for(cash[sleeve], ask, fee_cfg)
                if not grams:
                    continue
                buy = cents(float(grams) * ask)
                tax_cents = policy.fee(fee_cfg, float(grams) * ask, 'BUY')
                new_units = int(grams * 100)
                qty[sleeve] += new_units
                cash[sleeve] -= buy + tax_cents
                turnover += buy
                fees += tax_cents
                execution_cost += cents(float(grams) * (ask - mid))
                buys += 1
        nav = sum(cash) + cents(sum(qty) / 100 * bid)
        trace.append({'day': day, 'net_try': nav / 100, 'flow_try': flow / 100,
                      'grams': sum(qty) / 100, 'tactical_in_gold': bool(qty[1])})
    returns = gold_returns(trace)
    return {**returns, 'net_try': trace[-1]['net_try'], 'contributed_try': contributed / 100,
            'grams': trace[-1]['grams'], 'liquidation_grams': trace[-1]['net_try'] / bid,
            'buy_tax_try': fees / 100, 'paid_spread_and_slippage_try': execution_cost / 100,
            'turnover_of_mean_nav_pct': turnover / np.mean([r['net_try'] for r in trace]),
            'buys': buys, 'sells': sells,
            'tactical_in_gold_share': np.mean([r['tactical_in_gold'] for r in trace]),
            'periods': {era: gold_returns(trace, era) for era in ('2022', '2023–2024', '2025+')},
            'series': trace}


def gold_returns(trace, era=None):
    factors = [
        (r['net_try'] - r['flow_try']) / trace[i - 1]['net_try'] if i else r['net_try'] / r['flow_try']
        for i, r in enumerate(trace) if era is None or period(r['day']) == era]
    nav = np.cumprod([1., *factors])
    return {'twr_pct': 100 * (nav[-1] - 1),
            'drawdown_pct': 100 * np.min(nav / np.maximum.accumulate(nav) - 1)}


def evaluate_gold(panel, sessions):
    signals = features_for(panel, 'gold')
    training = targets(signals, panel, 'gold')
    realized = training.set_index('date').forward_pct
    execution_signals = {}
    forecasts_by_day = []
    for i in cadence(sessions, future=1):
        signal, opening = sessions[i], sessions[i + 1]
        test = signals.loc[signals.date.eq(signal)]
        scores, folds = forecasts(training, test, 'gold') if not test.empty else (None, {})
        predictions = scores.iloc[0].to_dict() if scores is not None else {}
        execution_signals[opening] = predictions
        end = sessions[i + HORIZON] if i + HORIZON < len(sessions) else None
        forecasts_by_day.append({'signal': signal, 'execution': opening, 'exit': end,
                                 'predictions': predictions, 'training': folds,
                                 'realized_pct': realized.get(signal)})
    paired = [r for r in forecasts_by_day if r['predictions'] and r['realized_pct'] is not None]
    first = min(execution_signals)
    mids = panel.set_index('date').loc[first:, 'total_close']
    if not (mids.gt(0) & np.isfinite(mids)).all():
        raise ValueError('Altın günlük değerleme serisinde geçersiz fiyat var.')
    scenarios = {}
    for spread in (.03, .04):
        accounts = {arm: gold_portfolio(mids, execution_signals, arm, spread)
                    for arm in (*GOLD_ACTIVE, 'cash', 'passive')}
        passive = accounts['passive']['net_try']
        scenarios[str(round(spread * 100))] = {
            arm: {**row, 'passive_excess_try': row['net_try'] - passive} for arm, row in accounts.items()}
    periods = {'all': paired, **{era: [r for r in paired if period(r['signal']) == era]
                                 for era in ('2022', '2023–2024', '2025+')}}
    return {'signals': forecasts_by_day, 'matched_windows': len(paired),
            'missed_signals': sum(not r['predictions'] for r in forecasts_by_day),
            'mae_windows': {era: len(rows) for era, rows in periods.items()},
            'mae_pct': {
                label: {arm: (np.mean([abs(r['predictions'][arm] - r['realized_pct']) for r in rows])
                              if rows else None)
                        for arm in (*WINDOWS, 'ridge-separate-3y', 'zero')}
                for label, rows in periods.items()},
            'scenarios': scenarios}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--market', required=True, choices=('bist', 'gold'))
    parser.add_argument('--database', required=True, type=Path)
    parser.add_argument('--asof', required=True, type=lambda s: date.fromisoformat(s).isoformat())
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--bist-observed-features', action='store_true')
    args = parser.parse_args()
    if args.bist_observed_features and args.market != 'bist':
        parser.error('Gözlenen bar duyarlılığı yalnız BIST için geçerli.')
    if args.output.exists():
        parser.error('Önceki kanıt korunur. Yeni çıktı yolu gerekli.')

    code_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                   (Path(__file__), Path(research.__file__), Path(learning.__file__),
                    Path(policy.__file__), ROOT / 'scripts/portfolio_research.py')}
    protocol_hash = hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()
    with history.connection(ROOT, args.market, args.database) as con:
        frame = history.load(con, args.market, args.asof)
        if args.market == 'bist':
            from advisor import universe

            records = universe.read(ROOT)
            selected = research.bist_members(records, args.asof)
            index_dates = {r[0] for r in con.execute(
                "SELECT date FROM index_daily WHERE symbol='XU030' AND c>0 AND date<=?", (args.asof,))}
            sessions = research.bist_sessions(index_dates, frame, {'calendar': calendar.load(ROOT)})
            coverage = {'fixed_members': sorted(selected), 'first_membership_record': min(r['known_at'] for r in records),
                        'sessions_without_xu030': sorted(set(sessions) - index_dates)}
        else:
            sessions = frame.date.tolist()
            coverage = {'source_names': [r[0] for r in con.execute(
                'SELECT DISTINCT ons_source FROM history_daily WHERE date <= ? ORDER BY ons_source', (args.asof,))]}

    if sessions[-1] != args.asof:
        raise ValueError('İstenen son kaynak seansı eksik.')
    panel = research.panel(frame, sessions, args.market)
    if args.bist_observed_features:
        panel = gap_tolerant_bist_features(panel)
    report = evaluate_bist(panel, sessions, selected) if args.market == 'bist' else evaluate_gold(panel, sessions)
    report.update(market=args.market, source_commit=args.source_commit, asof=args.asof,
                  archive_rows=len(frame), archive_symbols=frame.symbol.nunique(),
                  first_session=sessions[0], calendar_sessions=len(sessions), source=coverage,
                  source_sha256=research.source_digest(frame, sessions),
                  quality_fail_observed_rows=int(((~panel.quality_ok) & panel.close.notna()).sum()),
                  protocol_sha256=protocol_hash, code_sha256=code_hashes,
                  versions={pkg: version(pkg) for pkg in ('numpy', 'pandas', 'lightgbm')},
                  distinct_economic_candidates=len(BIST_ACTIVE) if args.market == 'bist' else len(GOLD_ACTIVE),
                  formal_independent_holdout=False, production_promotion=False)
    if args.bist_observed_features:
        report['sensitivity_sha256'] = hashlib.sha256(SENSITIVITY.read_bytes()).hexdigest()
    out = canonical(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        handle.write(out + '\n')


if __name__ == '__main__':
    main()
