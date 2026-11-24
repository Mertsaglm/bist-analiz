"""BIST araştırmasının eşleştirilmiş istatistik ve maliyetli portföy denetimi."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

from advisor import calendar, history, learning, portfolio_candidates, universe
from advisor.ledger import canonical
from advisor.service import configuration
from scripts import bist_rank_replay as replay, forecast_research as research

RANKERS = {'rank-lambda': 'lightgbm-ranking', 'rank-momentum': 'momentum-120-20',
           'rank-ridge': 'ridge'}


def block_interval(values, length, rng, repetitions=2000):
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n < length or not np.isfinite(values).all():
        return None
    starts = rng.integers(0, n, size=(repetitions, (n + length - 1) // length))
    # Equal inclusion for endpoint dates, including when only two blocks fit.
    sample = ((starts[..., None] + np.arange(length)) % n).reshape(repetitions, -1)[:, :n]
    return np.quantile(values[sample].mean(axis=1), [.025, .975]).tolist()


def statistics(receipt, frame, sessions):
    rng = np.random.default_rng(42)
    features = research.panel(frame, sessions, 'bist')
    result = {}
    for key, prior in receipt['horizons'].items():
        horizon = int(key)
        ranks = prior['metrics']['rank']
        names = ['lightgbm-ranking', 'lightgbm-regression', 'momentum-120-20', 'elastic-net', 'ridge']
        daily = {name: pd.DataFrame(ranks[name]['by_date']).set_index('date') for name in names}
        dates = daily[names[0]].index
        rows = research.labeled(features, 'bist', horizon, len(receipt['selected_symbols']))
        randomized = np.zeros(2000)
        for day, group in rows.loc[rows.date.isin(dates)].groupby('date'):
            if len(group) != daily[names[0]].loc[day, 'n']:
                raise ValueError(f'{day}: rapor ve gerçek sepet paydaları farklı.')
            values = group.forward_pct.to_numpy()
            chosen = rng.random((len(randomized), len(values))).argpartition(4, axis=1)[:, :5]
            randomized += values[chosen].mean(axis=1) / len(dates)
        fields = ('rank_ic', 'top5_excess_pct')
        intervals = {}
        for length in ((10, 20, 40) if horizon == 20 else (horizon,)):
            intervals[str(length)] = {
                name: {field: block_interval(daily[name][field], length, rng) for field in fields}
                for name in names}
            for other in ('momentum-120-20', 'lightgbm-regression'):
                intervals[str(length)]['lambda-minus-' + other] = {
                    field: block_interval(daily[names[0]][field] - daily[other][field], length, rng)
                    for field in fields}
        groups = rows[rows.date.isin(dates)].groupby('date').symbol.agg(list)
        result[key] = {'dates': len(dates), 'rows': prior['rows'],
                       'omitted_symbols': sorted(set(receipt['selected_symbols']) - set(sum(groups.tolist(), []))),
                       'nonoverlapping_windows': len(prior['nonoverlapping_anchor_dates']),
                       'intervals_95': intervals, 'random_top5_95': np.quantile(randomized, [.025, .975]).tolist(),
                       'random_top5_lambda_tail': float(np.mean(randomized >= ranks[names[0]]['top5_excess_pct'])),
                       'folds': [{'start': f['start'], 'end': f['end'], 'models': {
                           name: {field: float(daily[name].loc[f['start']:f['end'], field].mean())
                                  for field in fields} for name in names}} for f in prior['test_folds']]}
    return result


def ranking_inputs(frame, index_dates, records, cfg, start, end):
    inputs, folds = {}, []
    active = frozenset()
    days = list(replay.sessions(start, end, cfg))
    for i, day in enumerate(days):
        now = datetime.fromisoformat(day + 'T10:30:00').replace(tzinfo=calendar.IST)
        prior = calendar.last_closed_session(now, cfg).isoformat()
        members = portfolio_candidates.core_members(records, day, 'bist')
        if len(members) != 30:
            raise ValueError(f'{day}: tarihli BIST30 üyeliği eksik.')
        changed = active != members
        if changed:
            active = members
            selection = frame.loc[frame.symbol.isin(members)]
            features = research.panel(selection, research.bist_sessions(index_dates, selection, cfg), 'bist')
            labels = research.labeled(features, 'bist', 20, len(members))
        if changed or i % 5 == 0:
            training = labels.loc[labels.label_end.lt(prior)]
            window = training.date.unique()[-research.TRAIN_WINDOW:]
            if len(window) < research.TRAIN_MIN:
                raise ValueError(f'{prior}: 504 etiketli eğitim tarihi yok.')
            training = training.loc[training.date.ge(window[0])]
            absolute, _, _, _ = replay.fit_models(frame, members, prior, with_lightgbm=False)
            folds.append({'signal_date': prior, 'members': sorted(members), 'train_rows': len(training),
                          'train_label_end': training.label_end.max()})
        signal = features.loc[features.date.eq(prior)]
        valid = signal.loc[signal.quality_ok].dropna(subset=learning.ADAPTIVE_FEATURES)
        if len(valid) < 24:
            # Existing stops still run on the raw position marks.
            empty = {name: {} for name in replay.AUDIT_ARMS}
            inputs[day] = (signal, valid.iloc[:0], {}, empty)
            continue
        scored = research.forecast(training, valid, 'bist', 20).set_index('symbol')
        scores = {name: scored[column].rank(pct=True).to_dict() for name, column in RANKERS.items()}
        scores['rank-ensemble'] = scored[['lightgbm-ranking', 'lightgbm-regression', 'momentum-120-20']
                                        ].rank(pct=True).mean(axis=1).to_dict()
        scores['lambda-with-absolute-gate'] = scores['rank-lambda']
        inputs[day] = (signal, valid, dict(zip(valid.symbol, learning.predict(absolute, valid))), scores)
    return inputs, folds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    existing = json.loads(args.receipt.read_text())
    end = existing['asof']
    cfg = configuration(research.ROOT)
    cfg['calendar'] = calendar.load(research.ROOT)
    records = universe.read(research.ROOT)
    start = max(cfg['start_date'], min(row['known_at'] for row in records))
    cfg['start_date'] = start
    with history.connection(research.ROOT, 'bist', args.database) as con:
        raw = history.load(con, 'bist', end)
        frame, _, sessions, _ = research.bist_inputs(con, raw, end)
        index_dates = {row[0] for row in con.execute(
            "SELECT date FROM index_daily WHERE symbol='XU030' AND c>0 AND date<=?", (end,))}
        actions = [dict(row) for row in con.execute(
            'SELECT ticker,date,kind,value FROM corporate_actions WHERE date BETWEEN ? AND ?', (start, end))]
    if research.source_digest(frame, sessions) != existing['source_sha256']:
        raise ValueError('Önceki sınavın kaynak kesiti uyuşmuyor.')
    stats = statistics(existing, frame, sessions)
    rank_inputs, folds = ranking_inputs(raw, index_dates, records, cfg, start, end)
    economic = {}
    costs = ('commission_rate', 'commission_min_try', 'exchange_fee_rate', 'slippage_bps')
    for multiplier in (1., 1.5, 2.):
        adjusted = {**cfg, **{key: cfg[key] * multiplier for key in costs}}
        with TemporaryDirectory(prefix='forecast-audit-bist-') as tmp:
            economic[str(multiplier)] = replay.replay(
                raw, records, actions, adjusted, start, end, Path(tmp), rank_inputs=rank_inputs)
    with args.output.open('x', encoding='utf-8') as out:
        out.write(canonical({'source_sha256': existing['source_sha256'], 'start': start, 'end': end,
                             'statistics': stats, 'economic_folds': folds, 'economic': economic}) + '\n')
    print(args.output)


if __name__ == '__main__':
    main()
