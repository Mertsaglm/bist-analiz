"""Salt okunur piyasa arşiviyle ayrı tahmin ve kalibrasyon araştırması."""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
from importlib.metadata import version
import math
import os
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from advisor import calendar, history, learning, portfolio_candidates, specialized, universe
from advisor.ledger import canonical, digest
from scripts.portfolio_research import LIGHTGBM

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'docs/TAHMIN-ARASTIRMA-ON-KAYIT-2026-11-25.md'
HORIZONS = (5, 20, 60)
TEST_DATES = CALIBRATION_DATES = 126
TRAIN_MIN, TRAIN_WINDOW, BLOCK = 504, 756, 5
QUANTILES = (.1, .5, .9)
EXTRA = ['volume_ratio', 'turnover_ratio', 'momentum_rank', 'volatility_rank']


def bist_members(records, asof):
    selected = portfolio_candidates.core_members(records, asof, 'bist')
    if len(selected) != 30:
        raise ValueError(f'{asof}: BIST30 üyeliği eksik veya tutarsız ({len(selected)}/30).')
    return selected


def bist_sessions(index_dates, frame, cfg):
    valid = frame.loc[frame.close.gt(0) & frame.volume.gt(0)]
    counts = valid.groupby('date').symbol.nunique()
    market_dates = set(counts.index[counts.ge(24)])
    return sorted(day for day in set(index_dates) | market_dates if calendar.trading_day(day, cfg))


def bist_inputs(con, frame, asof, root=ROOT):
    selected = bist_members(universe.read(root), asof)
    frame = frame.loc[frame.symbol.isin(selected)]
    index_dates = {r[0] for r in con.execute(
        "SELECT date FROM index_daily WHERE symbol='XU030' AND c>0 AND date<=?", (asof,))}
    sessions = bist_sessions(index_dates, frame, {'calendar': calendar.load(root)})
    return frame, selected, sessions, sorted(set(sessions) - index_dates)


def source_digest(frame, sessions):
    return digest({'sessions': sessions, 'frame': pd.util.hash_pandas_object(
        frame, index=False).astype(str).tolist()})


def panel(frame, sessions, market):
    """Sembolün eksik satırı ortak piyasa takvimini değiştiremez."""
    sessions = pd.Index(sessions, name='date')
    parts = []
    for symbol, group in frame.groupby('symbol', sort=True):
        aligned = group.set_index('date').reindex(sessions).drop(columns='symbol')
        aligned['symbol'] = symbol
        observed = aligned.close.gt(0) & aligned.total_close.gt(0)
        if market == 'bist':
            observed &= (aligned.low.gt(0) & aligned.volume.gt(0)
                         & aligned.low.le(aligned[['open', 'close']].min(axis=1))
                         & aligned.high.ge(aligned[['open', 'close']].max(axis=1))
                         & aligned.open.gt(0))
        else:
            observed &= aligned.ons_usd.gt(0) & aligned.usdtry.gt(0)
        aligned.loc[~observed, ['close', 'total_close', 'high', 'low', 'volume']] = np.nan
        if market == 'gold':
            aligned.loc[~observed, ['ons_usd', 'usdtry']] = np.nan
        daily_return = aligned.total_close.pct_change(fill_method=None)
        aligned['ewma_vol'] = daily_return.ewm(span=20, min_periods=20).std() * 100
        aligned['eligible_endpoint'] = observed & daily_return.abs().lt(.3)
        if market == 'bist':
            turnover = aligned.close * aligned.volume
            for name, values in (('volume_ratio', aligned.volume), ('turnover_ratio', turnover)):
                aligned[name] = np.log(values.rolling(20).mean() / values.rolling(60).mean())
        parts.append(aligned.reset_index())
    if not parts:
        raise ValueError('Araştırma evreninde fiyat yok.')
    features = learning.features(pd.concat(parts, ignore_index=True), 20)
    if market == 'bist':
        for name, source in (('momentum_rank', 'momentum20'), ('volatility_rank', 'volatility20')):
            features[name] = features[source].where(features.quality_ok).groupby(features.date).rank(pct=True)
    return features


def labeled(features, market, horizon, expected_names):
    """Bütün etiketleri aynı seans sonuna sabitle ve ortak paydayı kaydet."""
    rows = features.copy()
    by_symbol = rows.groupby('symbol', sort=False)
    rows['label_end'] = by_symbol.date.shift(-horizon)
    end_ok = by_symbol.eligible_endpoint.shift(-horizon).eq(True)
    rows['forward_pct'] = 100 * (by_symbol.total_close.shift(-horizon) / rows.total_close - 1)
    if market == 'gold':
        for leg in ('ons_usd', 'usdtry'):
            rows[leg + '_target'] = 100 * np.log(by_symbol[leg].shift(-horizon) / rows[leg])
    names = (learning.ADAPTIVE_FEATURES + EXTRA if market == 'bist'
             else learning.FEATURES + specialized.GOLD_LEGS)
    rows = rows.loc[rows.quality_ok & end_ok].dropna(
        subset=names + ['ewma_vol', 'forward_pct', 'label_end'])
    rows = rows.sort_values(['date', 'symbol']).copy()
    if market == 'bist':
        counts = rows.groupby('date').symbol.transform('size')
        rows = rows.loc[counts.ge(math.ceil(.8 * expected_names))].copy()
        rows['forward_pct'] -= rows.groupby('date').forward_pct.transform('mean')
    return rows


def forecast(training, testing, market, horizon):
    from sklearn.linear_model import ElasticNet, LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    def ridge(names, target='forward_pct'):
        sample = training.assign(forward_pct=training[target])
        model = learning.fit(sample, 20, names, 126)
        return learning.predict(model, testing)

    names = learning.ADAPTIVE_FEATURES if market == 'bist' else learning.FEATURES
    xtrain, xtest = training[names], testing[names]
    target = training.forward_pct
    positive = target.gt(0)
    frequency = float(positive.mean())
    elastic = make_pipeline(StandardScaler(), ElasticNet(alpha=.1, l1_ratio=.5))
    predictions = {
        'zero': 0., 'ridge': ridge(names),
        'elastic-net': elastic.fit(xtrain, target).predict(xtest),
        'prob-base': frequency,
        'prob-logistic': (make_pipeline(StandardScaler(), LogisticRegression(C=1))
                          .fit(xtrain, positive).predict_proba(xtest)[:, 1]
                          if positive.nunique() == 2 else frequency),
    }
    if market == 'bist':
        from lightgbm import LGBMRanker, LGBMRegressor

        # İlk ve son grup indeksleri yalnız aynı seansın hisselerini kapsar.
        labels = (training.groupby('date').forward_pct.rank(pct=True) * 5).apply(np.ceil).astype(int) - 1
        groups = training.groupby('date', sort=False).size().tolist()
        regression = LGBMRegressor(**LIGHTGBM).fit(xtrain, target)
        ranking = LGBMRanker(**LIGHTGBM, objective='lambdarank', lambdarank_truncation_level=5)
        ranking.fit(xtrain, labels, group=groups)
        predictions.update({'momentum-120-20': (100 + testing.momentum120) / (100 + testing.momentum20),
                            'lightgbm-regression': regression.predict(xtest),
                            'lightgbm-ranking': ranking.predict(xtest)})
        if horizon == 20:
            predictions['ridge-expanded'] = ridge(names + EXTRA)
    else:
        legs = names + specialized.GOLD_LEGS
        separate = ridge(legs, 'ons_usd_target') + ridge(legs, 'usdtry_target')
        predictions.update({'training-mean': float(target.mean()), 'ridge-legs': ridge(legs),
                            'ridge-separate-legs': 100 * np.expm1(separate / 100)})
    return testing[['date', 'symbol', 'label_end', 'forward_pct', 'ewma_vol']].assign(**predictions)


def walk_forward(rows, evaluation_dates, market, horizon):
    predictions, folds = [], []
    for offset in range(0, len(evaluation_dates), BLOCK):
        dates = evaluation_dates[offset:offset + BLOCK]
        training = rows.loc[rows.label_end.lt(dates[0])]
        train_dates = training.date.unique()[-TRAIN_WINDOW:]
        if len(train_dates) < TRAIN_MIN:
            raise ValueError(f'{dates[0]} için {TRAIN_MIN} olgun eğitim tarihi gerekli.')
        training = training.loc[training.date.ge(train_dates[0])]
        testing = rows.loc[rows.date.isin(dates)]
        predictions.append(forecast(training, testing, market, horizon))
        folds.append({'start': dates[0], 'end': dates[-1], 'train_rows': len(training),
                      'train_dates': len(train_dates), 'test_rows': len(testing),
                      'train_label_end': training.label_end.max()})
    return pd.concat(predictions, ignore_index=True), folds


def calibrate(prior, testing, market, horizon):
    """İlk testten önce olgunlaşmış geçmiş OOS tahminlerini kullan."""
    if prior.label_end.max() >= testing.date.min() or prior.date.nunique() != CALIBRATION_DATES:
        raise ValueError('Kalibrasyon tarihleri eksik veya testle örtüşüyor.')
    testing = testing.copy()
    fits = {}
    models = ('ridge', 'lightgbm-regression') if market == 'bist' else ('ridge',)
    for name in models:
        x, y = prior[name] - prior[name].mean(), prior.forward_pct - prior.forward_pct.mean()
        slope = float((np.mean(x * y) + 1) / (np.mean(x * x) + 1))
        offset = float(prior.forward_pct.mean() - slope * prior[name].mean())
        fits[name] = {'offset_pct': offset, 'slope': slope}
        testing[name + '-calibrated'] = offset + slope * testing[name]
    errors = prior.forward_pct - prior.ridge
    old_scale = prior.ewma_vol.clip(lower=.1) * np.sqrt(horizon)
    new_scale = testing.ewma_vol.clip(lower=.1) * np.sqrt(horizon)
    for q, raw, normalized in zip(QUANTILES, np.quantile(errors, QUANTILES),
                                  np.quantile(errors / old_scale, QUANTILES)):
        testing[f'raw-q{q}'] = testing.ridge + raw
        testing[f'ewma-q{q}'] = testing.ridge + new_scale * normalized
    return testing, fits


def scores(testing, market):
    target = testing.forward_pct
    rank_only = {'momentum-120-20', 'lightgbm-ranking'}
    ignored = {'date', 'symbol', 'label_end', 'forward_pct', 'ewma_vol'}
    point, ranks, intervals, probabilities = {}, {}, {}, {}
    for name in testing.columns:
        if name in ignored or name.startswith(('prob-', 'raw-q', 'ewma-q')):
            continue
        values = testing[name]
        if name not in rank_only:
            error = values - target
            variance = float(values.var(ddof=0))
            mse = float((error ** 2).mean())
            base_mse = float((target ** 2).mean())
            point[name] = {'mae_pct': float(error.abs().mean()), 'rmse_pct': math.sqrt(mse),
                           'oos_r2_zero': 1 - mse / base_mse if base_mse else None,
                           'bias_pct': float(error.mean()),
                           'slope': float(np.mean((values - values.mean()) *
                                                 (target - target.mean())) / variance) if variance else None}
        if market == 'bist' and name != 'zero':
            by_date = []
            for day, rows in testing.groupby('date'):
                correlations = rows[[name, 'forward_pct']].rank().corr()
                ic = correlations.loc[name, 'forward_pct']
                top = rows.sort_values([name, 'symbol'], ascending=[False, True]).head(5)
                by_date.append({'date': day, 'n': len(rows), 'rank_ic': float(ic) if pd.notna(ic) else None,
                                'top5_excess_pct': float(top.forward_pct.mean())})
            valid = [r['rank_ic'] for r in by_date if r['rank_ic'] is not None]
            ranks[name] = {'rank_ic': float(np.mean(valid)) if valid else None, 'ic_dates': len(valid),
                           'top5_excess_pct': float(np.mean([r['top5_excess_pct'] for r in by_date])),
                           'by_date': by_date}
    event = target.gt(0)
    for name in ('prob-base', 'prob-logistic'):
        values = testing[name].clip(1e-8, 1 - 1e-8)
        bins = pd.cut(values, bins=np.linspace(0, 1, 6), include_lowest=True)
        reliability = [{'bin': str(bucket), 'rows': len(group), 'predicted': float(group.p.mean()),
                        'observed': float(group.y.mean())}
                       for bucket, group in pd.DataFrame({'p': values, 'y': event}).groupby(bins, observed=True)]
        probabilities[name] = {'brier': float(((values - event) ** 2).mean()),
                               'log_loss': float(-np.where(event, np.log(values), np.log1p(-values)).mean()),
                               'reliability': reliability}
    for name in ('raw', 'ewma'):
        values = [testing[f'{name}-q{q}'] for q in QUANTILES]
        intervals[name] = {'coverage': float(target.between(values[0], values[-1]).mean()),
                           'width_pct': float((values[-1] - values[0]).mean()),
                           'pinball': {str(q): float(np.maximum(q * (target - y), (q - 1) * (target - y)).mean())
                                       for q, y in zip(QUANTILES, values)}}
    return {'point': point, 'rank': ranks, 'probability': probabilities, 'interval': intervals}


def evaluate(frame, sessions, market, expected_names):
    features = panel(frame, sessions, market)
    data = {h: labeled(features, market, h, expected_names) for h in HORIZONS}
    common = sorted(set.intersection(*(set(rows.date) for rows in data.values())))
    test_dates = common[-TEST_DATES:]
    if len(test_dates) < TEST_DATES:
        raise ValueError(f'En az {TEST_DATES} ortak test tarihi gerekli.')
    horizon_reports = {}
    for horizon, rows in data.items():
        prior_dates = rows.loc[rows.label_end.lt(test_dates[0]), 'date'].unique()[-CALIBRATION_DATES:]
        if len(prior_dates) < CALIBRATION_DATES:
            raise ValueError(f'En az {CALIBRATION_DATES} kalibrasyon tarihi gerekli.')
        prior, prior_folds = walk_forward(rows, prior_dates, market, horizon)
        testing, test_folds = walk_forward(rows, test_dates, market, horizon)
        testing, fits = calibrate(prior, testing, market, horizon)
        next_day, nonoverlapping, coverage = '', [], []
        for day, group in testing.groupby('date'):
            coverage.append({'date': day, 'end': group.label_end.iloc[0], 'rows': len(group)})
            if day >= next_day:
                next_day = group.label_end.iloc[0]
                nonoverlapping.append(day)
        horizon_reports[str(horizon)] = {
            'rows': len(testing), 'expected_rows': TEST_DATES * expected_names,
            'coverage': coverage, 'nonoverlapping_anchor_dates': nonoverlapping,
            'calibration': {'start': prior_dates[0], 'end': prior_dates[-1],
                            'label_end': prior.label_end.max(), 'rows': len(prior), 'fits': fits,
                            'folds': prior_folds},
            'test_folds': test_folds, 'metrics': scores(testing, market),
        }
    dates = [d for d in sessions if test_dates[0] <= d <= test_dates[-1]]
    return {'horizons': horizon_reports, 'excluded_test_span_dates': sorted(set(dates) - set(test_dates)),
            'first_test_date': test_dates[0], 'last_test_date': test_dates[-1]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--market', required=True, choices=('bist', 'gold'))
    parser.add_argument('--database', required=True, type=Path, help='Salt okunur SQLite arşiv kopyası')
    parser.add_argument('--asof', required=True, help='Sabit son kaynak tarihi, YYYY-MM-DD')
    parser.add_argument('--output', required=True, type=Path, help='Henüz var olmayan JSON raporu')
    args = parser.parse_args()
    if args.output.suffix != '.json' or args.output.exists():
        parser.error('Henüz var olmayan ayrı bir .json dosyası gerekli.')
    asof = date.fromisoformat(args.asof).isoformat()
    with history.connection(ROOT, args.market, args.database) as con:
        frame = history.load(con, args.market, asof)
        if args.market == 'bist':
            frame, selected, sessions, extra_sessions = bist_inputs(con, frame, asof)
        else:
            selected = {'GRAM'}
            sessions = frame.date.tolist()
            extra_sessions = []
    if not selected or not sessions or sessions[-1] != asof:
        parser.error('Evren veya istenen son kaynak seansı eksik.')
    result = evaluate(frame, sessions, args.market, len(selected))
    result.update(market=args.market, asof=asof, protocol=PROTOCOL.name, selected_symbols=sorted(selected),
                  observed_symbols=sorted(frame.symbol.unique()), source_rows=len(frame),
                  sessions_without_index=extra_sessions,
                  source_sha256=source_digest(frame, sessions),
                  protocol_sha256=hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
                  code_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (Path(__file__), Path(learning.__file__),
                                         ROOT / 'scripts/portfolio_research.py')},
                  versions={'numpy': np.__version__, 'pandas': pd.__version__,
                            'sklearn': version('scikit-learn'),
                            'lightgbm': version('lightgbm') if args.market == 'bist' else None},
                  economic_claim=False, automatic_promotion=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=args.output.parent, encoding='utf-8') as tmp:
        tmp.write(canonical(result) + '\n')
        tmp.flush()
        os.link(tmp.name, args.output)
    print(f'{args.market} {asof}: {args.output}')


if __name__ == '__main__':
    main()
