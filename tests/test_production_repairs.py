"""2026-09-30 gerçek üretim arızalarının davranış regresyonları."""
from datetime import date, datetime, timezone
import copy
import importlib.util
import json
from pathlib import Path
import sqlite3

import pandas as pd
import pytest
import yaml

from advisor import calendar, service
from advisor.ledger import Ledger
from src import corporate_repair, dbdump, otonom, prices, resolver
from src.sources import kap, yf
from tests.conftest import add_bars, add_universe
from tests.test_otonom import _adimlari_sahtele
from tests.test_resolver import TestUctanUca as ResolverFixture

ROOT=Path(__file__).resolve().parents[1]


def script(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_daily_fetches_corporate_before_decision_and_stops_on_source_failure(cfg,con,monkeypatch):
    # Eski tabloda eksik temettü sessiz BIMAS başarısı üretmişti.
    calls=_adimlari_sahtele(monkeypatch)
    monkeypatch.setattr(otonom.tg,'bildir',lambda *a: True)
    from src.calendar_bist import BistCalendar
    monkeypatch.setattr(BistCalendar,'is_trading_day',lambda *a: True)
    otonom.gunluk(cfg,con,bugun=date(2026,9,30),analist_calistir=False)
    assert calls.index('kurumsal') < calls.index('paket') < calls.index('coz')
    calls.clear()
    monkeypatch.setattr(prices,'sync_actions',lambda *a: {'ok':False,'failed':{'TEST':'Timeout'}})
    result=otonom.gunluk(cfg,con,bugun=date(2026,9,30),analist_calistir=False)
    assert 'kurumsal' in otonom.basarisiz_mi(result)
    assert 'paket' not in calls and 'coz' not in calls


def test_corporate_source_failure_is_not_an_empty_success(cfg,monkeypatch,con):
    class Broken:
        def history(self,**kwargs):raise RuntimeError('offline')
    monkeypatch.setattr(yf.yf,'Ticker',lambda *a:Broken())
    result=prices.sync_actions(cfg,con,['TEST'])
    assert result['ok'] is False and result['failed']=={'TEST':'RuntimeError'}
    class EmptyActions:
        def history(self,**kwargs):
            return pd.DataFrame({'Close':[100.0],'Dividends':[0.0],'Stock Splits':[0.0]},index=pd.to_datetime([date.today()]))
    monkeypatch.setattr(yf.yf,'Ticker',lambda *a:EmptyActions())
    monkeypatch.setattr(yf.time,'sleep',lambda *a:None)
    result=prices.sync_actions(cfg,con,['TEST'])
    assert result['ok'] and result['kayit']==0


def test_corporate_repair_preserves_before_and_is_explicit_and_idempotent(cfg,con):
    rows=[('2024-01-02',100,101,99,100,1e6,100),('2024-01-03',100,101,99,100,1e6,100),
          ('2024-01-04',100,112,99,111,1e6,111),('2024-01-19',111,112,110,111,1e6,111)]
    pid=ResolverFixture()._kur(cfg,con,rows,stop=95,t1=110,e_low=99,e_high=100)
    resolver.resolve_open(cfg,con)
    old=dict(con.execute('SELECT * FROM outcomes WHERE prediction_id=?',(pid,)).fetchone())
    assert old['resolution']=='hedef'
    plan=corporate_repair.plan(cfg,con,[{'ticker':'TEST','date':'2024-01-03','kind':'temettu','value':2.5}])
    assert dict(con.execute('SELECT * FROM outcomes').fetchone())==old
    assert plan['changes'][0]['before']==old
    assert plan['changes'][0]['after']['resolution']=='iptal_kurumsal'
    corporate_repair.apply(con,plan);corporate_repair.apply(con,plan)
    new=dict(con.execute('SELECT * FROM outcomes').fetchone())
    assert new==plan['changes'][0]['after'] and new['ret_pct'] is None and new['hit'] is None
    changed=copy.deepcopy(plan);changed['changes'][0]['after']['hit']=1
    with pytest.raises(ValueError,match='mührü'):corporate_repair.apply(con,changed)
    con.execute("UPDATE outcomes SET resolution='stop'");con.commit()
    with pytest.raises(ValueError,match='değişmiş'):corporate_repair.apply(con,plan)


@pytest.mark.parametrize('stamp,expected',[
    ('2026-09-29T21:03:58+00:00','2026-09-29'),
    ('2026-09-25T22:18:00+00:00','2026-09-25'),
    ('2026-09-28T06:00:00+00:00','2026-09-25'),
    ('2026-09-30T15:09:00+00:00','2026-09-29'),
    ('2026-09-30T15:10:00+00:00','2026-09-30'),
    ('2026-10-28T09:39:00+00:00','2026-10-27'),
    ('2026-10-28T09:40:00+00:00','2026-10-28'),
])
def test_closing_date_is_a_session_not_midnight(stamp,expected):
    cfg=service.configuration(ROOT);cfg['calendar']=calendar.load(ROOT)
    assert calendar.last_closed_session(datetime.fromisoformat(stamp),cfg).isoformat()==expected


def test_refresh_catches_missing_close_and_skips_after_recovery(cfg,con,tmp_path,monkeypatch):
    # Çok sayıda taze kotasyon, eski günlük SQL'i kendiliğinden yenilemiyordu.
    module=script('refresh_market_history')
    (tmp_path/'advisor').mkdir();(tmp_path/'data').mkdir()
    (tmp_path/'advisor/config.json').write_text((ROOT/'advisor/config.json').read_text())
    (tmp_path/'holidays_tr.yaml').write_text((ROOT/'holidays_tr.yaml').read_text())
    (tmp_path/'config.yaml').write_text(yaml.safe_dump(cfg))
    add_universe(con,'AAA');add_bars(con,'AAA',[('2026-09-28',100,101,99,100,1000,100)])
    dbdump.dump(cfg,tmp_path/'data/bist.sql')
    calls=[]
    def daily(c,conn,**kwargs):
        calls.append(kwargs['tickers']);add_bars(conn,'AAA',[('2026-09-29',101,102,100,101,1000,101)])
    def indices(c,conn,**kwargs):
        from src.universe import index_symbols
        for symbol in index_symbols(c):
            conn.execute('INSERT INTO index_daily(symbol,date,o,h,l,c,ingested_utc) VALUES(?,?,?,?,?,?,?)',
                         (symbol,'2026-09-29',100,101,99,100,'2026-09-30T08:00:00+00:00'))
        conn.commit()
    monkeypatch.setattr(module.prices,'daily',daily);monkeypatch.setattr(module.prices,'sync_indices',indices)
    now=datetime(2026,9,30,8,tzinfo=timezone.utc)
    result=module.refresh(tmp_path,now);assert result['ok'] and result['missing_before']==['AAA']
    assert module.refresh(tmp_path,now)['skipped']=='already_current'
    assert calls==[['AAA']]
    # Ertesi gün kaynak eksik kalırsa önceki başarı bugünün başarısı sayılamaz.
    monkeypatch.setattr(module.prices,'daily',lambda *a, **k: {})
    monkeypatch.setattr(module.prices,'sync_indices',lambda *a, **k: {})
    failed=module.refresh(tmp_path,datetime(2026,10,1,8,tzinfo=timezone.utc))
    assert failed['ok'] is False and failed['missing']==['AAA']
    assert json.loads((tmp_path/'data/advisor/history_refresh.json').read_text())['ok'] is False


def test_expected_calendar_splits_full_window_and_requires_all_slices(cfg,monkeypatch):
    cfg=copy.deepcopy(cfg);b=cfg['sources']['kap']['beklenen_bildirim'];b.update(tavan_kayit=3,pencere_gun=1)
    calls=[]
    def row(name):return dict(kapTitle=name,subject='Finansal Rapor',startDate='01.09.2026',endDate='30.09.2026')
    class Response:
        def __init__(self,rows):self.rows=rows
        def raise_for_status(self):pass
        def json(self):return self.rows
    def post(url,**kwargs):
        q=kwargs['json'];calls.append((q['startDate'],q['endDate']))
        return Response([row('full')]*3 if q['startDate']!=q['endDate'] else [row(q['startDate']),row('duplicate')])
    monkeypatch.setattr(kap.requests,'post',post)
    result=kap.fetch_beklenen(cfg)
    assert result.ok and result.ham==4 and len(result.kayitlar)==3
    assert len(calls)==3 and calls[1][0]==calls[0][0] and calls[2][1]==calls[0][1]
    monkeypatch.setattr(kap.requests,'post',lambda *a,**k:Response([row('full')]*3))
    result=kap.fetch_beklenen(cfg)
    assert not result.ok and result.kirpik and not result.kayitlar
    calls.clear()
    def fail_second(*args,**kwargs):
        if len(calls)==2:raise TimeoutError('slice failed')
        return post(*args,**kwargs)
    monkeypatch.setattr(kap.requests,'post',fail_second)
    assert not kap.fetch_beklenen(cfg).ok


def test_auditor_finds_every_account_and_handles_fee_debt(tmp_path):
    audit=script('audit_production')
    for rel in ['events.jsonl','accounts/new/events.jsonl','accounts/new/candidates/sma/events.jsonl']:
        ledger=Ledger(tmp_path/'data/advisor'/rel)
        ledger.add('contribution','initial','2026-09-30T08:00:00+00:00',book='strategy',amount_cents=100)
        ledger.add('account_fee','fee','2026-09-30T08:01:00+00:00',book='strategy',amount_cents=150)
        ledger.add('contribution','next','2026-10-01T08:00:00+00:00',book='strategy',amount_cents=100)
        ledger.save()
        calculated=audit.independent(ledger.events,'strategy')
        assert calculated['cash_cents']==50 and calculated['fee_liability_cents']==0 and calculated['account_fees_cents']==150
    assert len(audit.audit_ledgers(tmp_path))==3


def test_sql_writers_share_non_replacing_queue_and_checkout_current_main():
    # Aynı grupta varsayılan tek bekleyen, sık portföy işi gelince günlüğü siler.
    writers=[yaml.safe_load((ROOT/'.github/workflows'/n).read_text()) for n in ['gunluk.yml','haftalik.yml','portfolio.yml']]
    assert {w['concurrency']['group'] for w in writers}=={'repo-commit'}
    for w in writers:
        assert w['concurrency']['queue']=='max' and w['concurrency']['cancel-in-progress'] is False
        checkout=next(s for j in w['jobs'].values() for s in j['steps'] if 'actions/checkout@' in s.get('uses',''))
        assert checkout['with']['ref']=='main'
    steps=writers[-1]['jobs']['portfolio']['steps']
    refresh=next(i for i,s in enumerate(steps) if s.get('id')=='history')
    cycle=next(i for i,s in enumerate(steps) if s.get('id')=='cycle')
    assert refresh<cycle and steps[refresh]['continue-on-error'] is True
    assert any('git add data/advisor/ data/bist.sql' in s.get('run','') for s in steps)
    schedule=writers[-1].get('on',writers[-1].get(True))['schedule'][0]['cron']
    assert schedule=='17 7-16 * * 1-5'


def test_corporate_after_closed_trade_cannot_erase_its_result(cfg,con):
    # Gerçek TAVHL: 1 Eylül'de kapanan işlem 22 Eylül temettüsüyle iptal edilmemeli.
    rows=[('2024-01-02',100,101,99,100,1e6,100),('2024-01-03',100,101,99,100,1e6,100),
          ('2024-01-04',100,101,90,91,1e6,91),('2024-01-19',91,93,90,92,1e6,92)]
    pid=ResolverFixture()._kur(cfg,con,rows,stop=95,t1=110,e_low=99,e_high=100)
    resolver.resolve_open(cfg,con)
    plan=corporate_repair.plan(cfg,con,[{'ticker':'TEST','date':'2024-01-19','kind':'temettu','value':2.5}])
    assert plan['changes']==[]
    assert con.execute('SELECT resolution FROM outcomes WHERE prediction_id=?',(pid,)).fetchone()[0]=='stop'


def test_http_and_curl_network_bans_cannot_be_swallowed_as_source_failures():
    import requests
    from curl_cffi.requests import Session
    # Kaynak katmanının except Exception bloğu, pytest.fail'i yutamaz.
    with pytest.raises(pytest.fail.Exception,match='requests taşıyıcısı'):
        try:requests.get('https://example.com')
        except Exception:pass
    with pytest.raises(pytest.fail.Exception,match='curl_cffi taşıyıcısı'):
        try:Session().get('https://example.com')
        except Exception:pass


def test_refresh_preserves_valid_subset_and_error_diagnosis_after_invalid_ohlc(cfg,con,tmp_path,monkeypatch):
    module=script('refresh_market_history')
    (tmp_path/'advisor').mkdir();(tmp_path/'data').mkdir()
    for name in ('advisor/config.json','holidays_tr.yaml'):
        (tmp_path/name).write_text((ROOT/name).read_text())
    (tmp_path/'config.yaml').write_text(yaml.safe_dump(cfg))
    for symbol in ('BAD','GOOD'):
        add_universe(con,symbol);add_bars(con,symbol,[('2026-09-28',100,101,99,100,1000,100)])
    dbdump.dump(cfg,tmp_path/'data/bist.sql')
    def partial(c,conn,**kwargs):
        add_bars(conn,'GOOD',[('2026-09-29',100,101,99,100,1000,100)])
        raise prices.InvalidOHLCError('Geçersiz OHLC: BAD 2026-09-29')
    monkeypatch.setattr(module.prices,'daily',partial)
    monkeypatch.setattr(module.prices,'sync_indices',lambda *a,**k:{})
    result=module.refresh(tmp_path,datetime(2026,9,30,8,tzinfo=timezone.utc))
    assert not result['ok'] and result['missing']==['BAD']
    assert 'BAD' in result['errors']['stocks']
    from src import db, migrations
    restored=sqlite3.connect(':memory:')
    restored.executescript(db.SCHEMA);migrations.apply(restored)
    restored.executescript((tmp_path/'data/bist.sql').read_text())
    assert restored.execute("SELECT max(date) FROM bars_daily WHERE ticker='GOOD'").fetchone()[0]=='2026-09-29'
    assert json.loads((tmp_path/'data/advisor/history_refresh.json').read_text())==result
