import json,sys,socket,hashlib,shutil
from pathlib import Path
from datetime import datetime,timedelta
import requests
root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root))
from advisor import service,recovery
from advisor.ledger import Ledger
from advisor.accounts import state_path

def forbidden(*args,**kwargs):raise AssertionError('Integration test attempted network')
requests.Session.request=forbidden
socket.socket.connect=forbidden
try:
 from curl_cffi.requests import Session
 Session.request=forbidden
except ImportError:pass
cfg=service.configuration(root);market=cfg['market'];state=state_path(root,cfg)
legacy=root/'data/advisor/events.jsonl';legacy_hash=hashlib.sha256(legacy.read_bytes()).hexdigest()
latest=json.loads((root/'data/advisor/latest.json').read_text());now=datetime.fromisoformat(latest['generated_at'])
quotes=latest['quotes'];before_count=len(Ledger(state/'events.jsonl').events)
views=[]
for i in range(2):
 snapshot=service.cycle(root,now=now,quotes=quotes,offline=True)
 books={b:Ledger(state/'events.jsonl').account(b) for b in ['strategy','benchmark','shadow_reference','shadow_candidate']}
 if i:assert books==previous, 'repeat_changed_books'
 previous=books
 views.append({'analysis_date':snapshot['analysis_date'],'expected':snapshot['health']['expected_analysis_date'],
               'issues':snapshot['health']['analysis_issues'],'decision_codes':{code:sum(d['code']==code for d in snapshot['decisions']) for code in {d['code'] for d in snapshot['decisions']}},
               'equity':snapshot['strategy']['equity_try'],'contributed':snapshot['strategy']['contributed_try'],
               'candidate_count':len(snapshot.get('candidates',[]))})
assert hashlib.sha256(legacy.read_bytes()).hexdigest()==legacy_hash
assert snapshot['strategy']['contributed_try']==50000
assert len(snapshot.get('candidates',[]))==4
if market=='bist':
 close=service.cycle(root,now=datetime.fromisoformat('2026-09-30T21:03:58+00:00'),quotes=quotes,offline=True,closing_refresh=True)
 assert not close.get('skipped') and close['monitoring']['phase']=='valuation'
 midnight={'skipped':False,'phase':close['monitoring']['phase']}
else:midnight=None
backup=root.parent/(market+'-fixed-backup.zip');recovery.backup(root,backup)
restore=recovery.restore(backup,root.parent/(market+'-restored'))
assert restore['ledger_hash']==Ledger(state/'events.jsonl').root_hash
result={'market':market,'initial_active_events':before_count,'cycles':views,'repeat_unchanged':True,'legacy_unchanged':True,
        'midnight':midnight,'restore_hash':restore['ledger_hash'],'restore_files':restore['files']}
(root.parent/(market+'-integration.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str))
print(json.dumps(result,ensure_ascii=False),flush=True)
