"""Geç gelen kurumsal işlem için açık, sürümlü V1 karne düzeltmesi."""
import hashlib
import json
import math
import sqlite3
from . import resolver, util


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def plan(cfg, source, actions):
    """Gerçek kaydı değiştirme; aynı resolver ile yalnız ek girdinin etkisini bul."""
    actions = sorted(actions, key=lambda a: (a['ticker'], a['date'], a['kind']))
    memory = sqlite3.connect(':memory:')
    source.backup(memory)
    memory.row_factory = sqlite3.Row
    try:
        for a in actions:
            if a['kind'] not in ('temettu','bolunme') or not a['ticker'] or not util.parse_date(a['date']):
                raise ValueError('Kurumsal işlem kaydı geçersiz.')
            if not math.isfinite(float(a['value'])) or float(a['value']) <= 0:
                raise ValueError('Kurumsal işlem tutarı/oranı pozitif ve sonlu olmalı.')
            memory.execute('INSERT OR REPLACE INTO corporate_actions(ticker,date,kind,value,source) VALUES(?,?,?,?,?)',
                           (a['ticker'],a['date'],a['kind'],a['value'],'verified_corporate_repair'))
        changes=[]
        for old in source.execute("SELECT * FROM outcomes WHERE resolution != 'iptal_kurumsal'"):
            old=dict(old)
            pred=memory.execute('SELECT * FROM predictions WHERE prediction_id=?',(old['prediction_id'],)).fetchone()
            new=resolver.resolve_prediction(cfg,memory,dict(pred))
            if new and new['resolution']==resolver.IPTAL_KURUMSAL:
                new['resolver_version']=resolver.RESOLVER_VERSION + '_repair_20260930'
                changes.append({'before':old,'after':new})
        result={'version':1,'actions':actions,'changes':changes,'created_at':util.utc_now_iso()}
        result['id']=digest(result)
        return result
    finally:
        memory.close()


def apply(con, plan):
    """Planı kontrol ederek uygula; önceki/sonraki satır dışında bir durumu ezme."""
    content={k:v for k,v in plan.items() if k!='id'}
    if digest(content)!=plan['id']:
        raise ValueError('Düzeltme planı mührü geçersiz.')
    with con:
        for item in plan['changes']:
            current=con.execute('SELECT * FROM outcomes WHERE prediction_id=?',(item['before']['prediction_id'],)).fetchone()
            if current is None or dict(current) not in (item['before'],item['after']):
                raise ValueError('Sonuç plan hazırlandıktan sonra değişmiş; yeni inceleme gerekli.')
        for a in plan['actions']:
            prior=con.execute('SELECT value FROM corporate_actions WHERE ticker=? AND date=? AND kind=?',
                              (a['ticker'],a['date'],a['kind'])).fetchone()
            if prior and prior[0] != a['value']:
                raise ValueError('Mevcut kurumsal işlemle çelişki var; otomatik üzerine yazılmaz.')
            con.execute('INSERT OR IGNORE INTO corporate_actions(ticker,date,kind,value,source) VALUES(?,?,?,?,?)',
                        (a['ticker'],a['date'],a['kind'],a['value'],'verified_corporate_repair:'+plan['id']))
        for item in plan['changes']:
            new=item['after'];cols=[c for c in resolver.OUTCOME_COLS if c!='prediction_id']
            con.execute('UPDATE outcomes SET '+','.join(c+'=?' for c in cols)+' WHERE prediction_id=?',
                        [new[c] for c in cols]+[new['prediction_id']])
    return {'plan_id':plan['id'],'changed':len(plan['changes'])}
