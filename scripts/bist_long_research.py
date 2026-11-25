"""Uzun 5 seans BIST sınavı, likidite evreni ve ara düşüş kuantili."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from advisor import calendar, history, learning
from advisor.ledger import canonical
from scripts import forecast_research as research
from scripts.portfolio_research import LIGHTGBM

HORIZON = 5
FEATURES = learning.FEATURES
RANKERS = ('momentum', 'factor', 'regression', 'winsorized', 'lambdarank')


def prepare(frame, sessions):
    features = research.panel(frame, sessions, 'bist')
    grouped = features.groupby('symbol', sort=False)
    turnover = features.close * features.volume
    features['liquidity'] = turnover.groupby(features.symbol).transform(
        lambda x: x.rolling(63, min_periods=50).median())
    lows = features.total_close * (features.low / features.close)
    future_low = lows.groupby(features.symbol).transform(
        lambda x: x.rolling(HORIZON).min().shift(-HORIZON))
    features['adverse_pct'] = (100 * (future_low / features.total_close - 1)).clip(upper=0)
    features['liquid30'] = features.liquidity.groupby(features.date).rank(
        ascending=False, method='first').le(30)
    return research.labeled(features, 'bist', HORIZON, 30), int(grouped.ngroups)


def eligible(data):
    counts = data.groupby('date').symbol.transform('size')
    data = data.loc[counts.ge(24)].copy()
    data['forward_pct'] -= data.groupby('date').forward_pct.transform('mean')
    return data


def predict(train, test):
    from lightgbm import LGBMRanker, LGBMRegressor

    x, y = train[FEATURES], train.forward_pct
    percentiles = y.quantile([.02, .98]).to_numpy()
    linear = LGBMRegressor(**LIGHTGBM).fit(x, y)
    winsor = LGBMRegressor(**LIGHTGBM).fit(x, y.clip(*percentiles))
    labels = np.ceil(train.groupby('date').forward_pct.rank(pct=True) * 5).astype(int) - 1
    ranker = LGBMRanker(**LIGHTGBM, objective='lambdarank', lambdarank_truncation_level=5)
    ranker.fit(x, labels, group=train.groupby('date', sort=False).size().tolist())
    risk_rows = train.dropna(subset=['adverse_pct'])
    risk = LGBMRegressor(**LIGHTGBM, objective='quantile', alpha=.1)
    risk.fit(risk_rows[FEATURES], risk_rows.adverse_pct)
    ranks = test.assign(momentum=(100 + test.momentum120) / (100 + test.momentum20),
                        low_vol=-test.volatility20, reversal=-test.momentum5)
    equal = ranks.groupby('date')[['momentum', 'low_vol', 'reversal', 'volume_ratio']].rank(pct=True)
    return ranks.assign(factor=equal.mean(axis=1), regression=linear.predict(test[FEATURES]),
                        winsorized=winsor.predict(test[FEATURES]),
                        lambdarank=ranker.predict(test[FEATURES]),
                        quantile=risk.predict(test[FEATURES]), empirical=risk_rows.adverse_pct.quantile(.1))


def evaluate(data, dates):
    predictions, folds = [], []
    # Every fifth session is tested, so 13 test dates span roughly one quarter.
    for offset in range(0, len(dates), 13):
        block = dates[offset:offset + 13]
        train = data.loc[data.label_end.lt(block[0])]
        window = train.date.unique()[-research.TRAIN_WINDOW:]
        if len(window) < research.TRAIN_MIN:
            continue
        train = train.loc[train.date.ge(window[0])]
        test = data.loc[data.date.isin(block)]
        predictions.append(predict(train, test))
        folds.append({'start': block[0], 'end': block[-1], 'last_train_label': train.label_end.max(),
                      'train_dates': len(window), 'test_rows': len(test)})
    all_predictions = pd.concat(predictions, ignore_index=True)
    daily = []
    for date, rows in all_predictions.groupby('date'):
        scores = {}
        for name in RANKERS:
            ic = rows[name].rank().corr(rows.forward_pct.rank())
            top = rows.sort_values([name, 'symbol'], ascending=[False, True]).head(5)
            scores[name] = {'ic': float(ic) if np.isfinite(ic) else None, 'top5_pct': float(top.forward_pct.mean())}
        daily.append({'date': date, 'symbols': rows.symbol.tolist(), 'ranking': scores})
    risk = {}
    measured = all_predictions.dropna(subset=['adverse_pct'])
    for name in ('quantile', 'empirical'):
        error = measured.adverse_pct - measured[name]
        risk[name] = {'pinball_pct': float(np.maximum(.1 * error, -.9 * error).mean()),
                      'breach_share': float(error.lt(0).mean()), 'rows': len(error)}
    return {'folds': folds, 'daily': daily, 'risk': risk, 'prediction_rows': len(all_predictions)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--asof', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with history.connection(research.ROOT, 'bist', args.database) as con:
        frame = history.load(con, 'bist', args.asof)
        _, selected, _, _ = research.bist_inputs(con, frame, args.asof)
        index_dates = {r[0] for r in con.execute(
            "SELECT date FROM index_daily WHERE symbol='XU030' AND c>0 AND date<=?", (args.asof,))}
    sessions = research.bist_sessions(index_dates, frame, {'calendar': calendar.load(research.ROOT)})
    data, archived_symbols = prepare(frame, sessions)
    branches = {'fixed': eligible(data.loc[data.symbol.isin(selected)]),
                'liquid30': eligible(data.loc[data.liquid30])}
    common = set(branches['fixed'].date) & set(branches['liquid30'].date)
    dates = [d for d in sessions[::HORIZON] if d >= '2018-01-01' and d in common]
    results = {name: evaluate(rows, dates) for name, rows in branches.items()}
    matched = {row['date'] for row in results['fixed']['daily']} & {row['date'] for row in results['liquid30']['daily']}
    for branch in results.values():
        rows = [row for row in branch['daily'] if row['date'] in matched]
        branch['matched'] = {name: {field: float(np.mean([row['ranking'][name][field] for row in rows
                                                         if row['ranking'][name][field] is not None]))
                                    for field in ('ic', 'top5_pct')}
                             for name in RANKERS}
    with args.output.open('x', encoding='utf-8') as out:
        out.write(canonical({'asof': args.asof, 'archive_first_session': sessions[0],
                             'archive_symbols': archived_symbols, 'matched_dates': len(matched),
                             'matched_first': min(matched), 'matched_last': max(matched),
                             'source_sha256': research.source_digest(frame, sessions), 'branches': results}) + '\n')


if __name__ == '__main__':
    main()
