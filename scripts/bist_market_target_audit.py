"""BIST piyasa seansı hedefi v1, üretimden bağımsız etiket deneyi."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from advisor import calendar, history, learning
from advisor.ledger import canonical
from scripts import forecast_research


def market_target(rows, sessions, horizon):
    """Özellikleri koru, yalnız vadeyi piyasa takvimine bağla."""
    result = rows.copy()
    result['label_end'] = result.date.map(dict(zip(sessions, sessions[horizon:])))
    prices = rows.loc[rows.total_close.gt(0) & rows.volume.gt(0)].set_index(['symbol', 'date']).total_close
    end = prices.reindex(result.set_index(['symbol', 'label_end']).index).to_numpy()
    result['forward_pct'] = 100 * (end / result.total_close.where(result.total_close.gt(0)) - 1)
    return result


def compare(frame, sessions, horizon):
    base = learning.features(frame, horizon)
    model_rows = base.loc[base.quality_ok].dropna(subset=learning.FEATURES + ['forward_pct', 'label_end'])
    model_rows = model_rows.loc[model_rows.date.isin(sessions[:-horizon])]
    alternative = market_target(base, sessions, horizon).loc[model_rows.index]
    measured = alternative.forward_pct.notna()
    shifted = model_rows.label_end.ne(alternative.label_end)
    delta = alternative.loc[measured, 'forward_pct'] - model_rows.loc[measured, 'forward_pct']
    shifts = Counter(model_rows.loc[shifted, 'date'].str[:4])
    return {'base_rows': len(model_rows), 'shifted': int(shifted.sum()),
            'missing_exact_end_price': int((~measured).sum()),
            'shifted_with_exact_price': int((shifted & measured).sum()),
            'mean_absolute_return_change_on_shifted_pct': float(delta.loc[shifted].abs().mean()) if (shifted & measured).any() else None,
            'shifted_by_signal_year': dict(shifts)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--asof', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = forecast_research.ROOT
    with history.connection(root, 'bist', args.database) as con:
        frame = history.load(con, 'bist', args.asof)
        index = {r[0] for r in con.execute("SELECT date FROM index_daily WHERE symbol='XU030' AND c>0 AND date<=?", (args.asof,))}
    sessions = forecast_research.bist_sessions(index, frame, {'calendar': calendar.load(root)})
    report = {'candidate': 'bist-market-session-target-v1', 'asof': args.asof,
              'source_sha256': forecast_research.source_digest(frame, sessions),
              'horizons': {str(h): compare(frame, sessions, h) for h in (5, 20, 60)}}
    with args.output.open('x') as out:
        out.write(canonical(report) + '\n')


if __name__ == '__main__':
    main()
