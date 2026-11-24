"""Tek bir ileri BIST sıralama sınavını kaydet veya vadesinde ölç."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from advisor import calendar, history, learning, specialized, universe
from advisor.ledger import digest
from scripts.portfolio_research import LIGHTGBM

ROOT = Path(__file__).resolve().parents[1]
HORIZON = 20


def freeze(frame, members, day, maturity, created):
    import lightgbm

    frame = frame.loc[(frame.date <= day) & frame.symbol.isin(members)].copy()
    if frame.empty:
        raise ValueError('Seçili evren için veri yok.')
    raw = learning.features(frame, HORIZON)
    # Farklı sembollerin 20. barı farklı tarihlere denk gelebilir.
    # Göreli hedefe giren her hissenin etiketi kesimden önce kapanmış olmalı.
    raw.loc[raw.label_end.isna() | (raw.label_end >= day), 'forward_pct'] = np.nan
    prepared, names = specialized.prepared(raw, 'bist', HORIZON)
    eligible = prepared.loc[prepared.quality_ok].dropna(subset=names)
    train = eligible.dropna(subset=['forward_pct', 'label_end'])
    dates = sorted(train.date.unique())[-756:]
    if len(dates) < 504:
        raise ValueError('504 sonuçlanmış eğitim seansı gerekli.')
    train = train.loc[train.date.isin(dates)]
    now = eligible.loc[eligible.date == day].sort_values('symbol')
    if set(now.symbol) != members:
        raise ValueError('Seçili evrende eksik veya kalitesiz girdi: ' +
                         ', '.join(sorted(members - set(now.symbol))))
    if len(now) < 3:
        raise ValueError('Sıralama için en az üç hisse gerekli.')
    ridge = learning.fit(train, 20, names, 126, 756)
    booster = lightgbm.LGBMRegressor(**LIGHTGBM).fit(train[names], train.forward_pct)
    scores = now[['symbol', 'total_close']].assign(
        ridge=learning.predict(ridge, now), lightgbm=booster.predict(now[names]))
    return dict(created_at=created, asof=day, maturity=maturity, horizon=HORIZON,
                training_dates=len(dates), training_rows=len(train),
                training_label_end=train.label_end.max(), features=names,
                source_hash=digest(pd.util.hash_pandas_object(frame, index=False).astype(str).tolist()),
                lightgbm_version=lightgbm.__version__, lightgbm_parameters=LIGHTGBM,
                lightgbm_model=booster.booster_.model_to_string(), ridge_model=ridge,
                scores=scores.to_dict('records'))


def save_once(path, trial):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, encoding='utf-8') as out:
        json.dump({'sha256': digest(trial), 'trial': trial}, out, ensure_ascii=False, allow_nan=False)
        out.flush()
        os.fsync(out.fileno())
        os.link(out.name, path)


def measure(trial, frame):
    start, end = trial['asof'], trial['maturity']
    expected = pd.DataFrame(trial['scores']).set_index('symbol')
    result = {'asof': start, 'maturity': end, 'expected': len(expected)}
    if frame.empty or frame.date.max() < end:
        return dict(result, status='vade bekleniyor')
    # İki kapanışı aynı veri revizyonundan al: temettü/bölünme bazını karıştırma.
    prices = frame.pivot(index='symbol', columns='date', values='total_close').reindex(
        index=expected.index, columns=[start, end])
    missing = prices.index[~(prices.gt(0) & np.isfinite(prices)).all(axis=1)].tolist()
    if missing:
        return dict(result, status='eksik fiyat', missing=missing)
    actual = prices[end] / prices[start] - 1
    correlations = {}
    for name in ('ridge', 'lightgbm'):
        ranks = expected[name].rank()
        ic = ranks.corr(actual.rank()) if ranks.nunique() > 1 and actual.nunique() > 1 else None
        correlations[name] = ic
    return dict(result, status='ölçüldü', rank_ic=correlations,
                sessions_evaluated=1, realized_returns_pct=(100 * actual).to_dict())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['freeze', 'measure'])
    parser.add_argument('--trial', type=Path, required=True)
    parser.add_argument('--database', type=Path)
    args = parser.parse_args()
    now = datetime.now(calendar.IST)
    cfg = {'calendar': calendar.load(ROOT)}
    day = calendar.last_closed_session(now, cfg).isoformat()
    with history.connection(ROOT, 'bist', args.database) as con:
        frame = history.load(con, 'bist', day)
    if args.action == 'freeze':
        maturity = calendar.add_sessions(day, HORIZON, cfg)
        calendar.require_coverage(day, maturity, cfg)
        trial = freeze(frame, universe.members(universe.read(ROOT), day), day, maturity, now.isoformat())
        save_once(args.trial, trial)
        result = {'asof': day, 'maturity': maturity, 'symbols': len(trial['scores'])}
    else:
        record = json.loads(args.trial.read_text())
        if record['sha256'] != digest(record['trial']):
            raise ValueError('Kayıt özeti uyuşmuyor.')
        result = measure(record['trial'], frame)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
