"""Önceki tarihsel sınamayı eş tarihler ve üretim öğrenme yolu ile denetle."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd

from advisor import calendar, history, learning, portfolio_candidates, universe
from advisor.ledger import canonical
from scripts import forecast_research as forecast
from scripts import historical_window_research as study

ROOT = forecast.ROOT
RECEIPTS = ROOT / 'reports/historical-window-2026-11-26'
ASOF = '2026-11-25'
HALF_DAY = '2024-04-09'
ARMS = {
    'main-ridge': (learning.FEATURES, None, None),
    'main-ridge-hl126': (learning.FEATURES, None, 126),
    'window756-equal': (learning.FEATURES, 756, None),
    'window756-hl126': (learning.FEATURES, 756, 126),
    't0-gold-legs-equal': (study.LEG_NAMES, 756, None),
    't0-gold-legs-hl126': (study.LEG_NAMES, 756, 126),
    'recent20-v1': (learning.ADAPTIVE_FEATURES, 756, 126),
}
PAIRS = (
    ('main-ridge-hl126', 'main-ridge'),
    ('window756-hl126', 'window756-equal'),
    ('t0-gold-legs-hl126', 't0-gold-legs-equal'),
)


def read_report(name):
    return json.loads((RECEIPTS / f'{name}.json').read_text())


def gold_test(frame, cfg):
    policy = cfg['learning']
    assert cfg['horizon_sessions'] == 20 and policy['ridge_penalty'] == 20.
    assert policy.get('half_life_sessions') is None and policy.get('window_sessions') is None
    features = learning.features(frame, 20)
    by_date = features.set_index('date', drop=False)
    valid = features.loc[features.quality_ok].dropna(subset=['label_end', 'forward_pct'])
    prior_report = read_report('gold')
    rows = []
    execute_at = {}
    for receipt in prior_report['signals']:
        day = receipt['signal']
        if day not in by_date.index:
            raise ValueError(f'{day}: önceki tahmin günü yok.')
        test = by_date.loc[[day]]
        training = valid.loc[valid.label_end.lt(day)]
        if training.date.nunique() < policy['min_training_dates']:
            raise ValueError(f'{day}: olgun eğitim örneklemi eksik.')
        preds = {'zero': 0.}
        for arm, (names, window, half_life) in ARMS.items():
            sample = training.dropna(subset=names)
            model = learning.fit(sample, 20., names, half_life, window)
            preds[arm] = float(learning.predict(model, test)[0])
        if receipt['realized_pct'] is not None:
            if test.label_end.iloc[0] != receipt['exit'] or not np.isclose(test.forward_pct.iloc[0], receipt['realized_pct']):
                raise ValueError(f'{day}: önceki hedefle eşleşmiyor.')
            rows.append({'signal': day, 'last_training_label': training.label_end.max(),
                         'realized_pct': receipt['realized_pct'], 'predictions': preds})
        execute_at[receipt['execution']] = preds
    errors = pd.DataFrame([{arm: abs(score - r['realized_pct']) for arm, score in r['predictions'].items()}
                           for r in rows])
    by_period = pd.Series([study.period(row['signal']) for row in rows])
    means = {era: dict(errors.loc[by_period.eq(era)].mean()) for era in by_period.unique()}
    means['all'] = dict(errors.mean())
    rng = np.random.default_rng(20261126)
    draws = {}
    for block in (3, 6):
        starts = rng.integers(len(rows), size=(4000, (len(rows) + block - 1) // block, 1))
        draws[block] = ((starts + np.arange(block)) % len(rows)).reshape(4000, -1)[:, :len(rows)]
    paired = {}
    for weighted, equal in PAIRS:
        delta = (errors[weighted] - errors[equal]).to_numpy()
        paired[weighted] = {'equal_arm': equal, 'mae_delta_pct': float(delta.mean()),
                            'weighted_better_days': int((delta < 0).sum()),
                            'intervals': {str(l): np.quantile(delta[idx].mean(axis=1), [.025, .975]).tolist()
                                          for l, idx in draws.items()}}
    mids = frame.set_index('date').loc[min(execute_at):, 'total_close']
    portfolios = {}
    for spread in (.03, .04):
        results = {}
        for arm in (*ARMS, 'passive', 'cash'):
            replay_arm = arm if arm in ('passive', 'cash') else 'ridge-2y'
            signals = {day: {replay_arm: preds[arm]} for day, preds in execute_at.items()} if arm in ARMS else execute_at
            view = study.gold_portfolio(mids, signals, replay_arm, spread)
            results[arm] = {k: v for k, v in view.items() if k != 'series'}
        portfolios[str(round(spread * 100))] = results
    return {'paired_dates': len(rows), 'rows': rows, 'mae_pct': means, 'paired': paired,
            'portfolio': portfolios}


def decompose_bist():
    old, new = (read_report(name) for name in ('bist', 'bist-observed-features'))
    def complete(report, branch):
        return {r['signal']: r['economics']['1x'] for r in report['branches'][branch]['episodes']
                if r['economics'] is not None}

    samples = [{name: complete(report, name) for name in ('fixed', 'liquid')} for report in (old, new)]
    old_days, new_days = [set(data['fixed']) & set(data['liquid']) for data in samples]
    common = sorted(old_days & new_days)
    extra = sorted(new_days - old_days)
    metrics = {}
    for branch in ('fixed', 'liquid'):
        metrics[branch] = {}
        for arm in study.BIST_ACTIVE:
            values = []
            for sample, dates in ((samples[0], common), (samples[1], common),
                                  (samples[1], extra), (samples[1], sorted(new_days))):
                vals = [sample[branch][d][arm]['net_pct'] - sample[branch][d]['passive']['net_pct'] for d in dates]
                values.append(float(np.mean(vals)))
            metrics[branch][arm] = dict(zip(('strict_common', 'observed_common', 'observed_extra', 'observed_full'), values))
    return {'common_dates': common, 'extra_dates': extra, 'strict_only_dates': sorted(old_days - new_days),
            'mean_excess_total_portfolio_pct': metrics}


def bist_audit(frame, sessions, records):
    raw = learning.features(frame, 20)
    expected = dict(zip(sessions, sessions[20:]))
    usable = raw.quality_ok & raw[learning.FEATURES].notna().all(axis=1)
    compare = raw.loc[usable & raw.label_end.notna() & raw.date.isin(expected)].copy()
    compare['expected'] = compare.date.map(expected)
    off = compare.loc[compare.label_end.ne(compare.expected)]
    crossing = compare.loc[compare.date.lt(HALF_DAY) & compare.expected.ge(HALF_DAY)
                           & compare.date.ge(sessions[sessions.index(HALF_DAY) - 20])]
    wrong = crossing.loc[crossing.label_end.ne(crossing.expected)]
    selected = forecast.bist_members(records, ASOF)
    panel = forecast.panel(frame, sessions, 'bist')
    dates = sessions[sessions.index(HALF_DAY):sessions.index(HALF_DAY) + 200]
    daily = {'production': {}, 'aligned_research': {}}
    for name, data in (('production', raw), ('aligned_research', panel)):
        sample = data.loc[data.symbol.isin(selected) & data.date.isin(dates)]
        counts = sample.loc[sample.quality_ok & sample[learning.FEATURES].notna().all(axis=1)].groupby('date').size()
        daily[name] = {day: int(counts.get(day, 0)) for day in dates}
    latest = raw.loc[raw.date.le(HALF_DAY) & raw.symbol.isin(selected)].groupby('symbol').tail(1)
    ready = latest.loc[latest.date.eq(HALF_DAY) & latest.quality_ok]
    membership_days = [d for d in sessions if '2022-01-01' <= d <= ASOF]
    valid_sources = frame.loc[frame.volume.gt(0) & frame.close.gt(0)].groupby('date').symbol.agg(set)
    missing_price = []
    known = []
    for day in membership_days:
        members = portfolio_candidates.core_members(records, day, 'bist')
        if len(members) != 30:
            continue
        known.append(day)
        missing = sorted(members - valid_sources.get(day, set()))
        if missing:
            missing_price.append({'date': day, 'members': missing})
    return {'half_day': HALF_DAY, 'core_apr09_usable_out_of_current_30': len(ready),
            'days_core_has_at_least_24_of_30': {name: sum(n >= 24 for n in obs.values()) for name, obs in daily.items()},
            'days_measured': len(dates), 'day_counts': daily,
            'label_drift_total': {'rows': len(compare), 'shifted': len(off)},
            'label_drift_half_day_nearby': {'rows': len(crossing), 'shifted': len(wrong),
               'example': wrong[['symbol', 'date', 'expected', 'label_end']].iloc[0].to_dict() if len(wrong) else None},
            'multi_year_replay_coverage': {'sessions': len(membership_days), 'official_30_known': len(known),
              'first_known_session': min(known), 'last_known_session': max(known),
              'known_sessions_with_missing_price': missing_price,
              'missing_prices_when_membership_unknown': None}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ('bist-db', 'gold-db', 'gold-config', 'output'):
        p.add_argument('--' + arg, type=Path, required=True)
    args = p.parse_args()
    with history.connection(ROOT, 'bist', args.bist_db) as con:
        frame = history.load(con, 'bist', ASOF)
        index_dates = {r[0] for r in con.execute("SELECT date FROM index_daily WHERE symbol='XU030' AND c>0 AND date<=?", (ASOF,))}
    sessions = forecast.bist_sessions(index_dates, frame, {'calendar': calendar.load(ROOT)})
    report = {'bist_decomposition': decompose_bist(), 'bist_production_path': bist_audit(frame, sessions, universe.read(ROOT))}
    with history.connection(ROOT, 'gold', args.gold_db) as con:
        gram = history.load(con, 'gold', ASOF)
    report['gold_ablation'] = gold_test(gram, json.loads(args.gold_config.read_text()))
    report['source_asof'] = ASOF
    report['source_sha256'] = {'bist': forecast.source_digest(frame, sessions),
                               'gold': forecast.source_digest(gram, gram.date.tolist())}
    report['code_sha256'] = sha256(Path(__file__).read_bytes()).hexdigest()
    with args.output.open('x') as out:
        out.write(canonical(report) + '\n')


if __name__ == '__main__':
    main()
