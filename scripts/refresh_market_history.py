"""V2 öncesi eksik kapanışı telafi et; yalnız SQL arşivini yaz, karar üretme.

SQL yazan Actions işleri repo-commit concurrency grubunu paylaşır. Yerel çağrı
ayrı bir checkout/kopyada yapılmalıdır; çalışan başka SQL yazarıyla yarışmamalı.
"""
from __future__ import annotations
import argparse
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from advisor import calendar, service
from advisor.ledger import atomic_json
from src import db, dbdump, prices, universe, util


def refresh(root, now=None, closing_refresh=False):
    root = Path(root).resolve()
    now = now or datetime.now(timezone.utc)
    cfg = service.configuration(root)
    if cfg['market'] != 'bist':
        return {'ok': True, 'skipped': 'market'}
    cfg['calendar'] = calendar.load(root)
    if not closing_refresh and calendar.phase(now, cfg) == 'closed':
        return {'ok': True, 'skipped': 'outside_observation'}
    expected = calendar.last_closed_session(now, cfg).isoformat()
    legacy = copy.deepcopy(util.load_config(root / 'config.yaml'))
    legacy['paths'] = {k: str(root / v) if not Path(v).is_absolute() else v
                       for k, v in legacy['paths'].items()}
    output = root / 'data/bist.sql'
    with tempfile.TemporaryDirectory(prefix='bist-catchup-') as temp:
        legacy['paths']['db'] = str(Path(temp) / 'history.db')
        legacy['paths']['db_dump'] = str(output)
        dbdump.restore(legacy)
        con = db.connect(legacy)
        try:
            tickers = universe.all_tickers(con)
            if not tickers:
                raise ValueError('Beklenen hisse evreni boş.')
            def missing():
                dates = dict(con.execute('SELECT ticker,max(date) FROM bars_daily GROUP BY ticker'))
                return [t for t in tickers if dates.get(t, '') < expected]
            before = missing()
            from src.calendar_bist import BistCalendar
            cutoff_before = BistCalendar(legacy, con).last_closed_session(now).isoformat()
            indices = universe.index_symbols(legacy)
            index_dates = dict(con.execute('SELECT symbol,max(date) FROM index_daily GROUP BY symbol'))
            stale_indices = [s for s in indices if index_dates.get(s, '') < expected]
            if not before and not stale_indices:
                return {'ok': True, 'expected': expected, 'skipped': 'already_current', 'missing': []}
            # Eksik kapanış için sonraki koşu tekrar dener; kalite kapısı gevşemez.
            errors = {}
            rejected_indices = []
            if before:
                try:
                    prices.daily(legacy, con, tickers=before, simdi=now)
                except prices.InvalidOHLCError as exc:
                    errors['stocks'] = str(exc)
            if stale_indices:
                try:
                    prices.sync_indices(legacy, con, start=(now.date()-timedelta(days=400)).isoformat(), simdi=now, rejected_records=rejected_indices)
                except prices.InvalidOHLCError as exc:
                    errors['indices'] = str(exc)
            current_rejections = [r for r in rejected_indices if r['date'] >= expected]
            if current_rejections:
                errors['indices'] = '; '.join(r['reason'] for r in current_rejections)
            after = missing()
            index_dates = dict(con.execute('SELECT symbol,max(date) FROM index_daily GROUP BY symbol'))
            stale_indices = [s for s in indices if index_dates.get(s, '') < expected]
            result = {'ok': not after and not stale_indices and not errors, 'expected': expected,
                      'errors': errors, 'rejected_indices': rejected_indices,
                      'missing_before': before, 'missing': after, 'missing_indices': stale_indices,
                      'legacy_cutoff_before': cutoff_before,
                      'legacy_cutoff_after': BistCalendar(legacy, con).last_closed_session(now).isoformat(),
                      'attempted_at': now.isoformat()}
            # Başarılı alt küme kaybolmaz; eksik isimler başarılı diye sunulmaz.
            dbdump.dump(legacy, output)
            atomic_json(root / 'data/advisor/history_refresh.json', result)
            return result
        finally:
            con.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--closing-refresh', action='store_true')
    args = parser.parse_args()
    result = refresh(args.root, closing_refresh=args.closing_refresh)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result['ok'] else 1)
