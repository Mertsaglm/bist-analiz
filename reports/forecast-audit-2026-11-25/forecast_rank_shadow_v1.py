"""BIST30 tahmin araştırmasının ayrı, yerel ileri sıralama kaydı."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

import numpy as np
import pandas as pd

from advisor import calendar, history, learning
from advisor.ledger import digest
from scripts import forecast_research as research
from scripts.bist_forward_trial import save_once

HORIZON = 20
MODELS = ('momentum-120-20', 'ridge', 'elastic-net', 'lightgbm-regression',
          'lightgbm-ranking', 'ridge-expanded')


def freeze(frame, sessions, selected, asof, maturity, created, source_ref):
    if not sessions or sessions[-1] != asof or asof >= maturity:
        raise ValueError('Son tamamlanan ortak seans ve ileri vade gerekli.')
    features = research.panel(frame, sessions, 'bist')
    names = learning.ADAPTIVE_FEATURES + research.EXTRA
    current = features.loc[features.date.eq(asof) & features.quality_ok].dropna(
        subset=names + ['ewma_vol']).sort_values('symbol')
    if len(current) < 24:
        raise ValueError(f'Gölge kayıt için en az 24/30 geçerli girdi gerekli ({len(current)}/30).')
    training = research.labeled(features, 'bist', HORIZON, len(selected))
    training = training.loc[training.label_end.lt(asof)]
    dates = training.date.unique()[-research.TRAIN_WINDOW:]
    if len(dates) < research.TRAIN_MIN:
        raise ValueError('Gölge kayıt için yeterli olgun eğitim tarihi yok.')
    training = training.loc[training.date.ge(dates[0])]
    predictions = research.forecast(training, current, 'bist', HORIZON)
    scored = predictions[['symbol', *MODELS]]
    if not np.isfinite(scored[list(MODELS)].to_numpy()).all():
        raise ValueError('Sonlu olmayan gölge tahmin.')
    return {'protocol': 'bist-forecast-research-shadow-v1', 'created_at': created,
            'asof': asof, 'maturity': maturity, 'horizon': HORIZON,
            'selected': sorted(selected), 'missing_features': sorted(selected - set(scored.symbol)),
            'training_dates': len(dates), 'training_rows': len(training),
            'training_label_end': training.label_end.max(), 'source_ref': source_ref,
            'source_sha256': research.source_digest(frame, sessions),
            'protocol_sha256': hashlib.sha256(research.PROTOCOL.read_bytes()).hexdigest(),
            'code_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (Path(__file__), Path(research.__file__), Path(learning.__file__),
                                      research.ROOT / 'scripts/portfolio_research.py')},
            'versions': {name: version(name) for name in ('lightgbm', 'scikit-learn', 'numpy', 'pandas')},
            'scores': scored.to_dict('records')}


def measure(trial, frame):
    start, end = trial['asof'], trial['maturity']
    scores = pd.DataFrame(trial['scores']).set_index('symbol')
    result = {'asof': start, 'maturity': end, 'expected': len(scores),
              'missing_features_at_freeze': trial['missing_features']}
    if frame.empty or frame.date.max() < end:
        return dict(result, status='vade bekleniyor')
    prices = frame.pivot(index='symbol', columns='date', values='total_close').reindex(
        index=scores.index, columns=[start, end])
    missing = prices.index[~(prices.gt(0) & np.isfinite(prices)).all(axis=1)].tolist()
    if missing:
        return dict(result, status='eksik fiyat', missing=missing)
    realized = (prices[end] / prices[start] - 1) * 100
    scores = scores.assign(actual=realized, symbol=scores.index).reset_index(drop=True)
    metrics = {}
    for model in MODELS:
        ic = scores[model].rank().corr(scores.actual.rank()) if (
            scores[model].nunique() > 1 and realized.nunique() > 1) else None
        top = scores.sort_values([model, 'symbol'], ascending=[False, True]).head(5)
        metrics[model] = {'rank_ic': float(ic) if ic is not None else None,
                          'top5_excess_pct': float(top.actual.mean() - realized.mean())}
    return dict(result, status='ölçüldü', metrics=metrics, realized_returns_pct=realized.to_dict())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'measure'))
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--trial', type=Path, required=True)
    parser.add_argument('--source-ref', help='Girdi arşivinin Git commit veya dosya kimliği')
    args = parser.parse_args()
    cfg = {'calendar': calendar.load(research.ROOT)}
    now = datetime.now(calendar.IST)
    asof = calendar.last_closed_session(now, cfg).isoformat()
    with history.connection(research.ROOT, 'bist', args.database) as con:
        frame = history.load(con, 'bist', asof)
        if args.action == 'freeze':
            if args.trial.exists() or not args.source_ref:
                parser.error('Yeni bir --trial ve girdi için --source-ref gerekli.')
            maturity = calendar.add_sessions(asof, HORIZON, cfg)
            calendar.require_coverage(asof, maturity, cfg)
            frame, selected, sessions, _ = research.bist_inputs(con, frame, asof)
            trial = freeze(frame, sessions, selected, asof, maturity, now.isoformat(), args.source_ref)
            save_once(args.trial, trial)
            result = {'asof': asof, 'maturity': maturity, 'symbols': len(trial['scores']),
                      'missing_features': trial['missing_features']}
        else:
            record = json.loads(args.trial.read_text())
            trial = record['trial']
            if record['sha256'] != digest(trial) or trial.get('protocol') != 'bist-forecast-research-shadow-v1':
                raise ValueError('Gölge tahmin kimliği veya özeti uyuşmuyor.')
            result = measure(trial, frame)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
