import sys,json,shutil,tempfile,hashlib,socket
from pathlib import Path
from datetime import datetime
import numpy as np
root=Path(sys.argv[1]);sys.path.insert(0,str(root))
from advisor import capsule,service,learning,history,calendar,policy,recovery
from advisor.ledger import Ledger
cfg=service.configuration(root);market=cfg['market'];base=Path(sys.argv[2]).resolve(); base.mkdir(parents=True,exist_ok=True)
state=root/'data/advisor'
if cfg.get('account_id'):state=state/'accounts'/cfg['account_id']
inventory=json.loads((base/(market+'-inventory.json')).read_text())
results={'market':market,'replays':[],'models':[]}
for l in inventory['ledgers'].values():
    for path in l['replay_samples']:
        try:results['replays'].append(dict(path=path,**capsule.reproduce(path)))
        except Exception as e:results['replays'].append({'path':path,'error':str(e)})
print(market,'replay samples',len(results['replays']),'ok',sum(r.get('ok',False) for r in results['replays']),flush=True)
s=json.loads((state/'latest.json').read_text());now=datetime.fromisoformat(s['generated_at'])
with history.connection(root,market) as con:frame=history.load(con,market,s['analysis_date'])
if cfg.get('watchlist_enabled'):
    from advisor import universe
    watched=sorted(universe.members(universe.read(root),now.astimezone(calendar.IST).date().isoformat()))
    frame['in_live']=frame.symbol.isin(watched).astype(int);frame.attrs['live_symbols']=watched
configs=[('main',state,cfg)]
if cfg.get('candidates_enabled'):
    from advisor import candidates
    configs += [(spec['id'],state/'candidates'/spec['id'],candidates.configuration(cfg,spec)) for spec in candidates.CATALOG]
for name,folder,c in configs:
    saved=json.loads((folder/'model.json').read_text())
    if saved.get('kind')=='sma50':continue
    import inspect
    actual,_=learning.train(frame,c,s['analysis_date'],**({'evaluate':False} if 'evaluate' in inspect.signature(learning.train).parameters else {}))
    maxdiff=max(float(np.max(np.abs(np.array(saved[k])-np.array(actual[k])))) for k in ['weights','mean','scale','intercept'])
    assert maxdiff<1e-10,(name,maxdiff)
    assert all(f['train_label_end']<f['test_start'] for f in saved['folds'])
    assert saved['label_end']<=saved['asof']
    results['models'].append({'name':name,'max_coefficient_difference':maxdiff,'approved':saved['approved'],'training_rows':saved['training_rows'],'evaluation':{k:saved['evaluation'].get(k) for k in ['periods','mae_pct','baseline_mae_pct','lower_95_pct']}})
print(market,'model refit OK',flush=True)
# Every subsequent external call is an audit failure. Production data remain read-only.
def deny(*a,**k):raise AssertionError('audit attempted external network')
socket.socket.connect=deny;socket.create_connection=deny
before=Ledger(state/'events.jsonl');books=['strategy','benchmark','shadow_reference','shadow_candidate']
with tempfile.TemporaryDirectory(prefix='bist-runtime-audit-') as tmp:
    work=Path(tmp)/'copy';work.mkdir();(work/'advisor').mkdir()
    shutil.copytree(root/'data',work/'data')
    shutil.copy2(root/'advisor/config.json',work/'advisor/config.json')
    for name in ['universe-history.json']:
        if (root/'advisor'/name).exists():shutil.copy2(root/'advisor'/name,work/'advisor'/name)
    for name in ['config.yaml','universe.yaml','holidays_tr.yaml']:
        if (root/name).exists():shutil.copy2(root/name,work/name)
    ws=work/state.relative_to(root)
    previous={book:before.account(book) for book in books}
    candidate_before={p.parent.name:Ledger(p).account() for p in (ws/'candidates').glob('*/events.jsonl')}
    cycles=[]
    for i in range(2):
        current=service.cycle(work,now=now,quotes=s['quotes'],offline=True)
        after=Ledger(ws/'events.jsonl')
        cycles.append({'run':i,'accounts_unchanged':{book:previous[book]==after.account(book) for book in books},'errors':current['health']['errors'],'candidates_unchanged':{p.parent.name:candidate_before[p.parent.name]==Ledger(p).account() for p in (ws/'candidates').glob('*/events.jsonl')}})
    results['repeat_cycles']=cycles
    if market=='bist':
        late=service.cycle(work,now=datetime.fromisoformat('2026-09-29T21:03:58+00:00'),quotes=s['quotes'],offline=True,closing_refresh=True)
        results['midnight_closing_refresh']={k:late.get(k) for k in ['generated_at','skipped','skip_reason']}
    backup=Path(tmp)/'backup.zip';results['backup']=recovery.backup(root,backup);results['restore']=recovery.drill(backup)
print(market,'cycle and recovery done',flush=True)
(base/(market+'-runtime.json')).write_text(json.dumps(results,ensure_ascii=False,indent=2))
