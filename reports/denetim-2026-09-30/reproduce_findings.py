"""Sabit BIST arşivinde salt-okur denetim. Değişiklikler yalnız bellektedir.
Usage: python reproduce_findings.py /path/to/extracted-bist-archive
"""
import json
import sqlite3
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root))
from advisor import history, service, calendar, costs, universe
from advisor.ledger import Ledger, fund
from src import resolver, util

cfg = service.configuration(root)
cfg['calendar'] = calendar.load(root)
state = service.state_path(root, cfg)
snapshot = json.loads((state / 'latest.json').read_text())
result = {'snapshot_at': snapshot['generated_at'], 'analysis_date': snapshot['analysis_date'],
          'expected_analysis_date': snapshot['health']['expected_analysis_date'],
          'account_id': cfg.get('account_id'), 'initial_try': cfg['initial_try'],
          'decision_codes': dict(Counter(d.get('code') for d in snapshot['decisions']))}
with history.connection(root, 'bist') as source:
    result['corporate_latest'] = source.execute('select max(date) from corporate_actions').fetchone()[0]
    result['price_latest'] = source.execute('select max(date) from bars_daily').fetchone()[0]
    result['expected_disclosures_latest'] = source.execute('select max(fetched_utc) from expected_disclosures').fetchone()[0]
    result['stored'] = dict(source.execute('select * from outcomes where prediction_id=?', ('2026-09-15-BIMAS-1',)).fetchone())
    memory = sqlite3.connect(':memory:')
    source.backup(memory)
memory.row_factory = sqlite3.Row
corporate = json.loads((state / 'corporate.json').read_text())
action = next(a for a in corporate['BIMAS']['actions'] if a['date'] == '2026-09-16')
memory.execute('insert or replace into corporate_actions(ticker,date,kind,value,source) values(?,?,?,?,?)',
               (action['ticker'], action['date'], action['kind'], action['value'], 'audit-memory-only'))
prediction = dict(memory.execute('select * from predictions where prediction_id=?', ('2026-09-15-BIMAS-1',)).fetchone())
result['corporate_used'] = action
result['recomputed'] = resolver.resolve_prediction(util.load_config(root / 'config.yaml'), memory, prediction)
memory.close()

# Gerçek defter yüklenir, eklenen olaylar kaydedilmez; save() çağrısı yoktur.
ledger = Ledger(state / 'events.jsonl')
now = datetime.fromisoformat('2026-10-01T08:00:00+00:00')
fund(ledger, cfg, '2026-10-01', now.isoformat())
first = ledger.account('strategy')['contributed_cents']
fund(ledger, cfg, '2026-10-01', now.isoformat())
result['october_contribution'] = {'once_cents': first, 'twice_cents': ledger.account('strategy')['contributed_cents']}
result['october_custody'] = costs.accrue(ledger, cfg, snapshot['quotes'], now)
result['october_fees'] = [e['data'] for e in ledger.events if e['kind'] == 'account_fee']
sept = set(universe.members(universe.read(root), '2026-09-30'))
october = set(universe.members(universe.read(root), '2026-10-01'))
result['october_membership'] = {'added': sorted(october-sept), 'removed': sorted(sept-october), 'count': len(october)}
assert result['stored']['resolution'] == 'hedef'
assert result['recomputed']['resolution'] == 'iptal_kurumsal'
assert first == result['october_contribution']['twice_cents'] == 5500000
print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
