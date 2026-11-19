"""Tarihli BIST üyelik arşivinde LightGBM, göreli Ridge ve pasif portföy replay'i."""
from __future__ import annotations

import argparse
import hashlib
from datetime import date, datetime, timedelta
from importlib.metadata import version
import json
import math
from pathlib import Path
import sys
import tempfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from advisor import calendar, corporate, costs, history, learning, policy
from advisor import portfolio_candidates as portfolio
from advisor import specialized, universe
from advisor.ledger import Ledger, atomic_json
from advisor.service import configuration
from advisor.simulation import quote
from scripts.portfolio_research import LIGHTGBM

ARMS = ('relative-lightgbm', 'relative-ridge', 'core-passive')
DAILY_ARMS = {'daily-lightgbm': 'relative-lightgbm', 'daily-ridge': 'relative-ridge'}


def fit_models(frame, members, cutoff):
    from lightgbm import LGBMRegressor
    # Truncation precedes construction of every forward return, including the
    # cross-sectional reference when a stock missed a session.
    prefix = frame[(frame.date < cutoff) & frame.symbol.isin(members)]
    raw = learning.features(prefix, 20)
    relative, names = specialized.prepared(raw, 'bist', 20)
    train = relative[relative.quality_ok].dropna(subset=names + ['forward_pct', 'label_end'])
    dates = sorted(train.date.unique())[-756:]
    if len(dates) < 504:
        raise ValueError('Eğitim için olgunlaşmış 504 seans gerekli.')
    train = train[train.date.isin(dates)]
    absolute = raw[raw.quality_ok].dropna(subset=learning.FEATURES + ['forward_pct', 'label_end'])
    base = learning.fit(absolute, 20)
    ridge = learning.fit(train, 20, names, 126, 756)
    booster = LGBMRegressor(**LIGHTGBM).fit(train[names], train.forward_pct)
    return base, ridge, booster, {
        'signal_date': cutoff, 'train_rows': len(train), 'train_dates': len(dates),
        'last_label_date': str(train.label_end.max()), 'last_base_label_date': str(absolute.label_end.max())}


def quotes_for(bars, field, cfg, now):
    result = {}
    for symbol, row in bars.items():
        px = row[field]
        if math.isfinite(px) and px > 0:
            result[symbol] = quote(symbol, px, now, cfg, tradable=row['volume'] > 0)
    return result


def intraday_stops(ledger, bars, cfg, now):
    # Opening gaps on positions held overnight are handled by _tactical at
    # the open. With daily bars, the remaining stop breach is an assumed fill.
    for symbol, pos in ledger.account('tactical')['positions'].items():
        stop = pos.get('stop')
        if not stop:
            continue
        bar = bars.get(symbol)
        if bar is None or bar['volume'] <= 0:
            continue
        if not math.isfinite(bar['low']) or bar['low'] <= 0:
            raise ValueError(f'{symbol}: stop için geçerli gün içi düşük yok.')
        sell_factor = policy.execution_price({'bid': 1.0}, cfg, 'SELL')
        trigger_bid = stop / sell_factor
        if bar['low'] <= trigger_bid:
            price = min(trigger_bid, bar['open'])
            q = quote(symbol, price, now, cfg)
            action = portfolio._trade(ledger, cfg, {symbol: q}, now, 'tactical', symbol,
                                      'SELL', float(pos['quantity']) * price, reason='intraday_stop')
            if action['status'] != 'doldu':
                raise ValueError(f'{symbol}: stop emri gerçekleşmedi: {action}')


def sessions(start, end, cfg):
    day = date.fromisoformat(start)
    last = date.fromisoformat(end)
    while day <= last:
        if calendar.trading_day(day, cfg):
            yield day.isoformat()
        day += timedelta(days=1)


def performance(series, ledger):
    nav = peak = 1.
    drawdown = 0.
    previous_equity = previous_contribution = 0.
    for row in series:
        flow = row['contributed_try'] - previous_contribution
        nav *= row['equity_try'] / (previous_equity + flow)
        peak = max(peak, nav)
        drawdown = min(drawdown, nav / peak - 1)
        previous_equity, previous_contribution = row['equity_try'], row['contributed_try']
    fills = [e['data'] for e in ledger.events if e['kind'] == 'fill']
    tactical = [f for f in fills if f['book'] == 'tactical']
    return {**series[-1], 'net_time_weighted_return_pct': 100 * (nav - 1),
            'max_drawdown_pct': 100 * drawdown, 'fills': len(fills),
            'tactical_buys': sum(f['side'] == 'BUY' for f in tactical),
            'tactical_sells': sum(f['side'] == 'SELL' for f in tactical),
            'stop_exits': sum(f['reason'] in ('tactical_stop', 'intraday_stop') for f in tactical),
            'trading_fees_try': sum(f['fee_cents'] for f in fills) / 100,
            'series': series}


def replay(frame, records, actions, cfg, start, end, tmp, *, compare_daily=False):
    calendar.require_coverage(start, end, cfg)
    # Stored OHLC are split-adjusted. Applying a second share multiplier
    # would create synthetic wealth. Require an as-traded reconstruction first.
    if any(a['kind'] == 'bolunme' and start <= a['date'] <= end
           and a['ticker'] in {r['symbol'] for r in records} for a in actions):
        raise ValueError('Bölünme içeren aralık için tarihsel ham lot/fiyat mutabakatı gerekir.')
    arms = (*ARMS, *DAILY_ARMS) if compare_daily else ARMS
    ledgers = {arm: Ledger(tmp / arm) for arm in arms}
    series = {arm: [] for arm in arms}
    folds, coverage = [], []
    models = active = features = None
    raw_by_day = {d: g.set_index('symbol').to_dict('index') for d, g in
                  frame[frame.date.between(start, end)].groupby('date')}
    for i, day in enumerate(sessions(start, end, cfg)):
        now = datetime.fromisoformat(day + 'T10:30:00').replace(tzinfo=calendar.IST)
        prior = calendar.last_closed_session(now, cfg).isoformat()
        members = universe.members(records, day)
        # Only start once this universe is actually known, and refit on changes.
        if len(portfolio.core_members(records, day, 'bist')) != 30:
            raise ValueError(f'{day}: tarihli BIST30 üyeliği eksik.')
        universe_changed = active != members
        if universe_changed:
            active = members
            features = learning.features(frame[frame.symbol.isin(active)], 20)
        if universe_changed or i % 5 == 0:
            base, ridge, booster, fold = fit_models(frame, members, prior)
            folds.append(fold)
            models = base, ridge, booster
        base, ridge, booster = models
        signal = features[features.date == prior]
        names = ridge['features']
        valid = signal[signal.quality_ok].dropna(subset=names)
        if valid.empty:
            raise ValueError(f'{prior}: kullanılabilir sinyal yok.')
        forecasts = dict(zip(valid.symbol, learning.predict(base, valid)))
        ranks = {'relative-ridge': dict(zip(valid.symbol, learning.predict(ridge, valid))),
                 'relative-lightgbm': dict(zip(valid.symbol, booster.predict(valid[names])))}
        rows = signal.set_index('symbol').to_dict('index')
        bars = raw_by_day.get(day, {})
        if not bars:
            raise ValueError(f'{day}: fiyat arşivinde seans eksik.')
        cfg.update(expected_analysis_date=prior, allowed_entry_symbols=sorted(members),
                   execution_phase='entry')
        opening = quotes_for(bars, 'open', cfg, now)
        close = now.replace(hour=12 if day in cfg['calendar']['half_days'] else 17, minute=30)
        marks = quotes_for(bars, 'close', cfg, close)
        coverage.append({'day': day, 'members': len(members), 'eligible_signals': len(valid),
                         'missing_price': sorted(members - opening.keys()),
                         'zero_volume': sorted(s for s in members & bars.keys() if bars[s]['volume'] <= 0)})
        for arm, ledger in ledgers.items():
            portfolio._fund(ledger, cfg, day, now, arm)
            cfg['blocked_symbols'] = corporate.reconcile(
                ledger, [a for a in actions if a['date'] == day], cfg, now, books=('core', 'tactical'))
            portfolio._core(ledger, cfg, records, rows, opening, now)
            if arm == 'core-passive':
                portfolio._core(ledger, cfg, records, rows, opening, now, book='tactical')
            else:
                portfolio._tactical(ledger, cfg, rows, opening, forecasts,
                                    ranks[DAILY_ARMS.get(arm, arm)], now, review_daily=arm in DAILY_ARMS)
                intraday_stops(ledger, bars, cfg, now.replace(hour=11, minute=45))
            fees = costs.accrue(ledger, cfg, marks, close, books=(('portfolio', ('core', 'tactical'), 'core'),))
            if fees['pending']:
                raise ValueError(f'{day}: eksik saklama matrahı.')
            view = portfolio._view(ledger, cfg, marks, close, arm)
            if not view['valuation_complete']:
                raise ValueError(f'{day}: {arm} kapanış değerlemesi eksik.')
            series[arm].append({key: view[key] for key in ('contributed_try', 'equity_try', 'account_fees_try')}
                               | {'date': day})
    return {'folds': folds, 'coverage': coverage,
            'arms': {a: performance(series[a], ledgers[a]) for a in arms}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path)
    parser.add_argument('--asof')
    parser.add_argument('--compare-daily', action='store_true',
                        help='Haftalık kontrol kollarına her seans yeniden karar veren iki aday ekle.')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cfg = configuration(ROOT)
    cfg['calendar'] = calendar.load(ROOT)
    records = universe.read(ROOT)
    start = max(cfg['start_date'], min(r['known_at'] for r in records))
    cfg['start_date'] = start
    with history.connection(ROOT, 'bist', args.database) as con:
        latest = con.execute('SELECT MAX(date) FROM bars_daily').fetchone()[0]
        end = min(args.asof or latest, latest)
        frame = history.load(con, 'bist', end)
        actions = [dict(row) for row in con.execute(
            'SELECT ticker,date,kind,value FROM corporate_actions WHERE date BETWEEN ? AND ?', (start, end))]
    if start > end:
        raise ValueError('Kayıtlı üyelikten sonra tamamlanmış seans yok.')
    with tempfile.TemporaryDirectory(prefix='bist-rank-replay-') as tmp:
        report = replay(frame, records, actions, cfg, start, end, Path(tmp), compare_daily=args.compare_daily)
    data_hash = hashlib.sha256(pd.util.hash_pandas_object(frame, index=False).values.tobytes()).hexdigest()
    report.update(start=start, end=end, sessions=len(report['coverage']), input_rows=len(frame),
                  frame_sha256=data_hash, lightgbm_version=version('lightgbm'),
                  production_eligible=False, independent_holdout=False,
                  initial_try=cfg['initial_try'], monthly_try=cfg['monthly_try'],
                  policy=portfolio.POLICY_ID, model_parameters=LIGHTGBM,
                  daily_review_candidate=args.compare_daily,
                  limitations=[
                      'Eski 126 tarihli model sınavıyla örtüşen ve önceden incelenmiş arşiv. Bağımsız ileri sınav yok.',
                      'Üyelik tarihli kayıtla sınırlı. Önceki eğitim fiyatları revizyon ve evrende kalma yanlılığı taşıyabilir.',
                      'Fiyatlar günlük bar; gerçek banka kotasyonu, emir sırası, likidite ve saatlik stop gerçekleşmesi bilinmiyor.',
                      'Bir önceki kapanışla sıralama, sonraki açılışla sanal dolum. Açılışta boşluk varsa stop açılıştan, gün içinde kayma sonrası satış fiyatı eşiğe temas ederse stop seviyesinden satılır.',
                      'Sıfır günlük hacim işlem engeli olarak kullanılır; açılış likiditesi ayrıca gözlenemiyor.',
                      'Ortak mutlak Ridge tahmini, iki göreli sıralayıcıda aynı maliyet ve risk filtresine girer. Canlı kalibrasyon uygulanmaz.',
                      'Komisyon, BSMV, borsa payı, kayma, tamamlanan çeyrek saklaması ve net temettü alacağı dahildir. Kişisel tarife, MKK ve henüz kapanmamış çeyrek ücreti bilinmiyor.',
                      'Düşüş ve zaman ağırlıklı getiri günlük net tasfiye değerleriyle hesaplanır; seans içi en büyük düşüş bilinmiyor.'])
    atomic_json(args.output, report)
    print(json.dumps({k: {m: v for m, v in a.items() if m != 'series'}
                      for k, a in report['arms'].items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
