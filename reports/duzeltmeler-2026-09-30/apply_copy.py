from pathlib import Path
import sqlite3,json,sys,hashlib
sys.path.insert(0,str(Path.cwd()))
from src import corporate_repair
source=Path('/tmp/bist-audit-20260930/bist-restored.db');base=Path('/tmp/bist-fix-20260930')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before_hash=sha(source)
with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as original:
 con=sqlite3.connect(base/'corporate-apply-copy.db');original.backup(con)
con.row_factory=sqlite3.Row
before={r['prediction_id']:dict(r) for r in con.execute('SELECT * FROM outcomes')}
plan=json.loads((base/'corporate-plan-full.json').read_text());receipt=corporate_repair.apply(con,plan)
first=[dict(r) for r in con.execute('SELECT * FROM outcomes ORDER BY prediction_id')]
again=corporate_repair.apply(con,plan)
assert again==receipt and first==[dict(r) for r in con.execute('SELECT * FROM outcomes ORDER BY prediction_id')]
after={r['prediction_id']:dict(r) for r in con.execute('SELECT * FROM outcomes')}
changed=[k for k in before if before[k]!=after[k]]
assert changed==['2026-09-15-BIMAS-1'] and before_hash==sha(source)
assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
receipt.update(source_hash_unchanged=before_hash,changed_prediction_ids=changed,total_outcomes=len(before),idempotent=True,new_corporate_actions=len(plan['actions']))
(base/'corporate-apply-copy.json').write_text(json.dumps(receipt,indent=2));con.close();print(receipt)
