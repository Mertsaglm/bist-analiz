import sys, json, sqlite3, collections, hashlib, gzip
from pathlib import Path
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
root=Path(sys.argv[1]); sys.path.insert(0,str(root))
from advisor import history, service, policy, notifications, capsule
from advisor.ledger import Ledger
cfg=service.configuration(root); market=cfg['market']; base=Path(sys.argv[2]).resolve(); base.mkdir(parents=True,exist_ok=True)
out={'market':market,'root':str(root),'tables':{},'ledgers':{}}
with history.connection(root,market) as c:
    target=sqlite3.connect(base/(market+'-restored.db')); c.backup(target);target.close()
    out['integrity']=c.execute('pragma integrity_check').fetchone()[0]
    out['foreign_key_violations']=[tuple(r) for r in c.execute('pragma foreign_key_check')]
    for t, in c.execute("select name from sqlite_master where type='table'"):
        cols=[r[1] for r in c.execute(f'pragma table_info("{t}")')]
        stamps=[k for k in cols if k in ['date','asof','created_utc','tarih_tr','resolved_date','ts_utc','published_utc']]
        out['tables'][t]={'rows':c.execute(f'select count(*) from "{t}"').fetchone()[0],**{k:c.execute(f'select max("{k}") from "{t}"').fetchone()[0] for k in stamps}}
    if market=='bist':
        out['latest_prices']=[dict(r) for r in c.execute('select ticker,count(*) n,max(date) last from bars_daily group by ticker')]
        out['latest_sessions']=[dict(r) for r in c.execute("select date,count(*) n from bars_daily where date>='2026-09-15' group by date")]
        out['runs']=[dict(r) for r in c.execute("select * from otonom_kosu where tarih_tr>='2026-09-25'")]
        out['sasa']=[dict(r) for r in c.execute("select date,c,c_tr,v from bars_daily where ticker='SASA' and date>='2026-08-28'")]

def independent(events,book):
    cash=contributed=realized=receivable=debt=fees=0;positions={}
    for e in events:
        d=e['data'];kind=e['kind']
        if d.get('book')!=book:continue
        if kind=='account_checkpoint':
            a=d['account'];cash=a['cash_cents'];contributed=a['contributed_cents'];realized=a['realized_cents'];receivable=a['receivable_cents'];debt=a.get('fee_liability_cents',0);fees=a.get('account_fees_cents',0)
            positions={s:[Decimal(str(p['quantity'])),p['cost_cents']] for s,p in a['positions'].items()}
        elif kind=='contribution':cash+=d['amount_cents'];contributed+=d['amount_cents']
        elif kind=='account_fee':debt+=d['amount_cents'];fees+=d['amount_cents']
        elif kind=='fill':
            q=Decimal(d['quantity']);p=positions.setdefault(d['symbol'],[Decimal(0),0]);n=d['notional_cents'];fee=d['fee_cents']
            assert int((q*Decimal(str(d['price']))*100).quantize(Decimal(1),rounding=ROUND_HALF_UP))==n
            if d['side']=='BUY':cash-=n+fee;p[0]+=q;p[1]+=n+fee
            else:
                assert p[0]>=q
                cost=int((Decimal(p[1])*q/p[0]).quantize(Decimal(1),rounding=ROUND_HALF_UP));cash+=n-fee;realized+=n-fee-cost;p[0]-=q;p[1]-=cost
        elif kind=='corporate_action':
            if d['action']=='split' and d['symbol'] in positions:positions[d['symbol']][0]*=Decimal(str(d['ratio']))
            elif d['action']!='split':cash+=d['net_cents']
        elif kind=='dividend_receivable':receivable+=d['amount_cents']
        elif kind=='dividend_payment':receivable-=d['amount_cents'];cash+=d['amount_cents']
        paid=min(cash,debt);cash-=paid;debt-=paid
        assert min(cash,receivable,debt)>=0
    return {'cash_cents':cash,'contributed_cents':contributed,'realized_cents':realized,'receivable_cents':receivable,'fee_liability_cents':debt,'account_fees_cents':fees}, {s:(q,cost) for s,(q,cost) in positions.items() if q>0}

for path in (root/'data/advisor').rglob('events.jsonl'):
    l=Ledger(path); books=sorted({'strategy','benchmark'}|{e['data']['book'] for e in l.events if 'book' in e['data']});daily=collections.defaultdict(list)
    info={'events':len(l.events),'hash':l.root_hash,'kinds':dict(collections.Counter(e['kind'] for e in l.events)),'books':{},'daily':{},'capsules':0,'replay_samples':[]}
    for book in books:
        expected,pos=independent(l.events,book); actual=l.account(book)
        for k,v in expected.items():assert v==actual.get(k,0),(path,book,k)
        assert pos=={s:(p['quantity'],p['cost_cents']) for s,p in actual['positions'].items()}
        info['books'][book]={**expected,'positions':len(pos),'fills':len(actual['fills'])}
    for e in l.events:
        if e['kind']=='session_check' and e['data'].get('in_observation_window',e['data'].get('in_execution_window',True)):daily[e['at'][:10]].append(e)
    for day,es in daily.items():
        times=[datetime.fromisoformat(e['at']) for e in es];d=es[-1]['data']
        info['daily'][day]={'cycles':len(es),'first':es[0]['at'],'last':es[-1]['at'],'max_gap_minutes':max([(b-a).total_seconds()/60 for a,b in zip(times,times[1:])],default=0),'full_quote_cycles':sum(e['data']['valid_quotes']==e['data']['expected_quotes'] for e in es),'fresh_analysis_cycles':sum(not e['data'].get('analysis_issues') for e in es),'last_analysis_issues':d.get('analysis_issues',{}),'last_data_blocks':len(d.get('data_blocked_symbols',[]))}
    info['fills']=[dict(at=e['at'],**e['data']) for e in l.events if e['kind']=='fill']
    receipts=[dict(at=e['at'],**e['data']) for e in l.events if e['kind']=='notification']
    info['notifications']=[{k:e.get(k) for k in ['at','snapshot_at','message_id','text']} for e in receipts]
    sp=path.parent/'latest.json'
    if sp.exists():
        s=json.loads(sp.read_text()); info['snapshot_at']=s['generated_at']
        if 'health' in s and s['health']['ledger_hash'] in {e['hash'] for e in l.events}:
            index=next(i for i,e in enumerate(l.events) if e['hash']==s['health']['ledger_hash'])
            prefix=Ledger(Path('/nonexistent-audit-prefix'));prefix.events=l.events[:index+1]
            viewcfg=dict(cfg);viewcfg['blocked_symbols']={symbol:'unverified' for symbol,p in s['health'].get('corporate_sources',{}).items() if not p['ok']}
            info['snapshot_discrepancies']=[]
            for book in ['strategy','benchmark']:
                actual=policy.value_account(prefix.account(book),s['quotes'],viewcfg,datetime.fromisoformat(s['generated_at']))
                for k in ['equity_try','cash_try','contributed_try','pnl_try','receivable_try']:
                    if actual[k]!=s[book][k]:info['snapshot_discrepancies'].append([book,k,actual[k],s[book][k]])
            info['notification_matches']=notifications.delivered(l,s)
    packages=[e for e in l.events if e['kind']=='decision_capsule']
    for e in packages:
        p=path.parent/e['data']['path'];envelope=json.loads(gzip.decompress(p.read_bytes()))
        assert capsule.digest(envelope['payload'])==envelope['hash']==e['data']['id']
        assert all(r['date']<=envelope['payload']['context']['now'][:10] for r in envelope['payload']['context']['rows'])
        info['capsules']+=1
    if packages:
        info['replay_samples']=[str(path.parent/e['data']['path']) for e in [packages[0],packages[len(packages)//2],packages[-1]]]
    out['ledgers'][str(path.relative_to(root))]=info
    print(market,str(path.relative_to(root)),info['events'],'ledger+independent-account OK','capsules',info['capsules'],flush=True)
(base/(market+'-inventory.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2,default=str))
print(market,'COMPLETE',out['integrity'],len(out['foreign_key_violations']),flush=True)
