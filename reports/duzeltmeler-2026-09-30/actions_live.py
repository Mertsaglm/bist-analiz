import sys,json,sqlite3,hashlib,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from src import util,prices,corporate_repair
base=Path('/tmp/bist-fix-20260930');source=Path('/tmp/bist-audit-20260930/bist-restored.db')
with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as original:
 con=sqlite3.connect(base/'corporate-verification.db');original.backup(con)
con.row_factory=sqlite3.Row
cfg=util.load_config('config.yaml');begin=time.time()
old={(r['ticker'],r['date'],r['kind']):dict(r) for r in con.execute('SELECT * FROM corporate_actions')}
result=prices.sync_actions(cfg,con)
new=[dict(r) for r in con.execute('SELECT * FROM corporate_actions')]
added=[r for r in new if (r['ticker'],r['date'],r['kind']) not in old]
revised=[{'before':old[(r['ticker'],r['date'],r['kind'])],'after':r} for r in new if (r['ticker'],r['date'],r['kind']) in old and old[(r['ticker'],r['date'],r['kind'])]['value']!=r['value']]
result.update(elapsed_seconds=round(time.time()-begin,2),added=added,revised=revised)
(base/'corporate-live-refresh.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
if result['ok']:
 with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as original:
  original.row_factory=sqlite3.Row
  plan=corporate_repair.plan(cfg,original,added)
 (base/'corporate-plan-full.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
 print(json.dumps({'ok':True,'tickers':result['tickers'],'new_actions':len(added),'revised':len(revised),'outcome_changes':len(plan['changes']),'seconds':result['elapsed_seconds']},ensure_ascii=False))
else:print(json.dumps(result,ensure_ascii=False))
con.close()
