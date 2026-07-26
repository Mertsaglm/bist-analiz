"""Ortak test fixture'ları.

İki tür test var ve karıştırılmamalı:

  * **Sentetik testler** — geçici veritabanı + elle kurulmuş barlar. Mantığı test
    eder, ağ gerektirmez, daima çalışır.
  * **Gerçek veri testleri** — proje veritabanını (`data/bist.db`) okur ve veri
    KAYNAĞININ davranışını test eder (ör. yfinance temettü düzeltmesi hâlâ
    çalışıyor mu). Bunlar `real_con` fixture'ını kullanır ve veritabanı boşsa
    atlanır. Amaçları LESSONS L-005: "inancı fixture testine çevir".
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src import db, util


@pytest.fixture
def cfg(tmp_path: Path) -> dict:
    """Gerçek config, ama veritabanı ve dump geçici dizinde."""
    c = util.load_config(fresh=True)
    c = {**c, "paths": {**c["paths"],
                        "db": str(tmp_path / "test.db"),
                        "db_dump": str(tmp_path / "test.sql"),
                        "log_dir": str(tmp_path / "logs")}}
    return c


@pytest.fixture
def con(cfg: dict):
    c = db.connect(cfg)
    yield c
    c.close()


@pytest.fixture
def real_cfg() -> dict:
    return util.load_config(fresh=True)


@pytest.fixture
def real_con(real_cfg: dict):
    """Proje veritabanı. Yoksa/boşsa test atlanır."""
    p = db.db_path(real_cfg)
    if not p.exists():
        pytest.skip(f"Proje veritabanı yok ({p}) — önce `bist veri backfill`")
    c = db.connect(real_cfg)
    n = c.execute("SELECT COUNT(*) FROM bars_daily").fetchone()[0]
    if n == 0:
        c.close()
        pytest.skip("bars_daily boş — önce `bist veri backfill`")
    yield c
    c.close()


# ------------------------------------------------------------------ yardımcılar
def add_bars(con: sqlite3.Connection, ticker: str, rows: list[tuple]) -> None:
    """rows: [(date, o, h, l, c, v, c_tr)]"""
    now = util.utc_now_iso()
    con.executemany(
        "INSERT OR REPLACE INTO bars_daily "
        "(ticker,date,o,h,l,c,v,c_tr,turnover_try,source,ingested_utc) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(ticker, d, o, h, low, c, v, ctr, (c or 0) * (v or 0), "test", now)
         for d, o, h, low, c, v, ctr in rows])
    con.commit()


def add_index(con: sqlite3.Connection, symbol: str, dates: list[str],
              close: float = 100.0) -> None:
    now = util.utc_now_iso()
    con.executemany(
        "INSERT OR REPLACE INTO index_daily (symbol,date,o,h,l,c,ingested_utc) "
        "VALUES (?,?,?,?,?,?,?)",
        [(symbol, d, close, close, close, close, now) for d in dates])
    con.commit()


def add_universe(con: sqlite3.Connection, ticker: str, *, sector: str = "test",
                 tier: str = "cekirdek", in_live: bool = True,
                 in_measure: bool = True) -> None:
    con.execute(
        "INSERT OR REPLACE INTO universe "
        "(ticker,yf_symbol,name,sector,tier,in_live,in_measure) VALUES (?,?,?,?,?,?,?)",
        (ticker, f"{ticker}.IS", ticker, sector, tier, int(in_live), int(in_measure)))
    con.commit()
