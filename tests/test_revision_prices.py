from src import prices
import pandas as pd
import pytest
from datetime import datetime
from src.calendar_bist import BistCalendar
from tests.conftest import add_index, add_bars, add_universe


def test_unchanged_bar_preserves_ingestion_but_correction_is_stored(con, monkeypatch):
    """Tekrar okuma tüm SQL'i değiştiriyordu; gerçek fiyat düzeltmesi korunmalı."""
    frame=pd.DataFrame([dict(date='2026-09-14',o=99.,h=101.,l=98.,c=100.,v=1000.,c_tr=100.)])
    monkeypatch.setattr(prices.util,'utc_now_iso',lambda:'2026-09-15T10:00:00Z')
    assert prices._store_bars(con,'AAA',frame)==1
    monkeypatch.setattr(prices.util,'utc_now_iso',lambda:'2026-09-15T11:00:00Z')
    assert prices._store_bars(con,'AAA',frame)==0
    assert con.execute("SELECT ingested_utc FROM bars_daily WHERE ticker='AAA'").fetchone()[0]=='2026-09-15T10:00:00Z'
    frame.loc[0,'c_tr']=101
    assert prices._store_bars(con,'AAA',frame)==1
    assert con.execute("SELECT c_tr,ingested_utc FROM bars_daily WHERE ticker='AAA'").fetchone()[0]==101


@pytest.mark.parametrize('column,value',[('c',97),('o',102),('h',float('inf')),('l',0)])
def test_invalid_ohlc_cannot_replace_a_good_bar_or_partially_write_batch(con,column,value):
    good=pd.DataFrame([dict(date='2026-10-22',o=99.,h=101.,l=98.,c=100.,v=1000.,c_tr=100.)])
    prices._store_bars(con,'TMSN',good)
    bad=good.copy();bad.loc[0,column]=value
    later=good.copy();later.loc[0,'date']='2026-10-23'
    with pytest.raises(ValueError,match='Geçersiz OHLC: TMSN 2026-10-22'):
        prices._store_bars(con,'TMSN',pd.concat([later,bad]))
    assert [tuple(r) for r in con.execute('SELECT date,c FROM bars_daily')]==[('2026-10-22',100.)]


@pytest.mark.parametrize('market',['stocks','indices'])
def test_one_invalid_symbol_does_not_prevent_other_symbols_from_refreshing(cfg,con,monkeypatch,market):
    from src import universe
    frame=pd.DataFrame([dict(date='2026-10-22',o=99.,h=101.,l=98.,c=100.,v=1000.,c_tr=100.)])
    bad=frame.copy();bad.loc[0,'c']=97
    now=datetime.fromisoformat('2026-10-23T08:00:00+00:00')
    if market=='stocks':
        for symbol in ('BAD','GOOD'):add_universe(con,symbol)
        monkeypatch.setattr(prices.yf,'fetch_bars',lambda symbol,*a,**k:bad if symbol=='BAD' else frame)
        call=lambda:prices.daily(cfg,con,['BAD','GOOD'],simdi=now)
        sql="SELECT ticker FROM bars_daily"
    else:
        monkeypatch.setattr(universe,'index_symbols',lambda c:{'BAD':'BAD','GOOD':'GOOD'})
        monkeypatch.setattr(prices.yf,'fetch_index',lambda symbol,*a,**k:bad if symbol=='BAD' else frame)
        call=lambda:prices.sync_indices(cfg,con,simdi=now)
        sql="SELECT symbol FROM index_daily"
    with pytest.raises(prices.InvalidOHLCError,match='BAD'):
        call()
    assert [r[0] for r in con.execute(sql)]==['GOOD']


@pytest.mark.parametrize('stamp,expected,left',[
    ('2026-10-28T09:39:00+00:00','2026-10-27',0),
    ('2026-10-28T09:40:00+00:00','2026-10-28',1),
    ('2026-10-28T13:00:00+00:00','2026-10-28',1),
])
def test_half_day_completed_stock_and_index_bars_survive_together(cfg,con,stamp,expected,left):
    # 28 Ekim: V2 12:40 kapanışı beklerken V1 18:10'a dek barı siliyordu.
    add_universe(con,'AAA')
    add_index(con,'XU100',['2026-10-27','2026-10-28'])
    add_bars(con,'AAA',[(day,100,101,99,100,1000,100) for day in ['2026-10-27','2026-10-28']])
    now=datetime.fromisoformat(stamp)
    assert BistCalendar(cfg,con).last_closed_session(now).isoformat()==expected
    prices.purge_incomplete_bars(cfg,con,simdi=now)
    assert con.execute("SELECT count(*) FROM bars_daily WHERE date='2026-10-28'").fetchone()[0]==left
    assert con.execute("SELECT count(*) FROM index_daily WHERE date='2026-10-28'").fetchone()[0]==left
    assert con.execute("SELECT count(*) FROM bars_daily WHERE date='2026-10-27'").fetchone()[0]==1
