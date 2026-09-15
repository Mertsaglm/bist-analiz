from src import prices
import pandas as pd


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
