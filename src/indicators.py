"""Teknik göstergeler — tek kaynak, deterministik, versiyonlu.

HANGİ SERİ NEREDE — bu dosyanın en önemli kararı:

    c     (bölünme düzeltmeli, temettü düzeltmesiz)
        → SMA/EMA, Bollinger, ATR, 52h yüksek/düşük
        Neden: bunlar İŞLEM YAPILABİLİR fiyat seviyeleridir. Stop'u temettü
        düzeltmeli bir seviyeye koyamazsın; o fiyat piyasada yoktur.

    c_tr  (toplam getiri)
        → RSI, MACD, tüm getiriler (ret_21/63/126/252), sma50_tr/sma200_tr
        Neden: temettü ex-tarihinde ham seri düşer ama bu bir ZAYIFLIK DEĞİLDİR.
        Momentumu ham seriden ölçmek, temettü ödeyen her hisseyi yapay olarak
        zayıf gösterir. Ölçüm: TUPRS 2025-03-28'de ham −%2.95 / düzeltilmiş +%2.67.

    sma200_tr trend KAPISI için ayrı tutulur: `c` üzerinden SMA200, 200 günlük
    pencerede birikmiş temettü kadar yukarı kaymış geçmiş fiyatların ortalamasıdır
    → fiyatı sistematik olarak SMA200'ün altında gösterir. %3-5 temettü verimiyle
    bu, %2'lik kapı toleransından büyüktür, yani kapıyı bozar.

Yetersiz veride SESSİZCE NaN taşınmaz — `None` döner ve satır yazılmaz.
"""

from __future__ import annotations

import logging
import sqlite3

import numpy as np
import pandas as pd

from . import db, prices, util

log = logging.getLogger(__name__)

INDICATOR_COLS = [
    "ticker", "date", "set_version",
    "sma20", "sma50", "sma200", "ema12", "ema26",
    "rsi14", "macd", "macd_signal", "macd_hist",
    "bb_mid", "bb_up", "bb_low", "bb_pctb", "bb_width",
    "atr14", "atr_pct", "adx14", "di_plus", "di_minus",
    "high_52w", "low_52w", "dist_high52_pct",
    "vol_ann_63", "turnover_med_63",
    "ret_21", "ret_63", "ret_126", "ret_252",
    "sma50_tr", "sma200_tr",
    "computed_utc",
]


# ============================================================ saf göstergeler
def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _wilder(s: pd.Series, n: int) -> pd.Series:
    """Wilder yumuşatma = ewm(alpha=1/n). Klasik EMA'dan (2/(n+1)) FARKLIDIR;
    karıştırmak RSI/ATR/ADX'i sessizce başka bir göstergeye çevirir."""
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    kazanc = _wilder(d.clip(lower=0.0), n)
    kayip = _wilder((-d).clip(lower=0.0), n)
    rs = kazanc / kayip.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    # kayıp=0 → RSI 100 (sonsuz rs); kazanç=0 ve kayıp=0 → tanımsız
    out = out.where(~((kayip == 0) & (kazanc > 0)), 100.0)
    return out


def macd(s: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
         ) -> tuple[pd.Series, pd.Series, pd.Series]:
    line = ema(s, fast) - ema(s, slow)
    sig = ema(line, signal)
    return line, sig, line - sig


def bollinger(s: pd.Series, n: int = 20, std: float = 2.0
              ) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    mid = sma(s, n)
    sd = s.rolling(n, min_periods=n).std(ddof=0)
    up, low = mid + std * sd, mid - std * sd
    genislik = (up - low) / mid.replace(0.0, np.nan)
    pctb = (s - low) / (up - low).replace(0.0, np.nan)
    return mid, up, low, pctb, genislik


def true_range(h: pd.Series, l: pd.Series, c: pd.Series) -> pd.Series:
    onceki = c.shift()
    return pd.concat([h - l, (h - onceki).abs(), (l - onceki).abs()], axis=1).max(axis=1)


def atr(h: pd.Series, l: pd.Series, c: pd.Series, n: int = 14) -> pd.Series:
    return _wilder(true_range(h, l, c), n)


def adx(h: pd.Series, l: pd.Series, c: pd.Series, n: int = 14
        ) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Wilder ADX. Döner: (adx, +DI, -DI)."""
    yukari = h.diff()
    asagi = -l.diff()
    art_dm = pd.Series(np.where((yukari > asagi) & (yukari > 0), yukari, 0.0), index=h.index)
    eksi_dm = pd.Series(np.where((asagi > yukari) & (asagi > 0), asagi, 0.0), index=h.index)

    tr_n = _wilder(true_range(h, l, c), n).replace(0.0, np.nan)
    art_di = 100.0 * _wilder(art_dm, n) / tr_n
    eksi_di = 100.0 * _wilder(eksi_dm, n) / tr_n
    toplam = (art_di + eksi_di).replace(0.0, np.nan)
    dx = 100.0 * (art_di - eksi_di).abs() / toplam
    return _wilder(dx, n), art_di, eksi_di


def realized_vol(s: pd.Series, n: int = 63) -> pd.Series:
    """Yıllıklaştırılmış gerçekleşen volatilite (log getiri)."""
    r = np.log(s / s.shift())
    return r.rolling(n, min_periods=n).std(ddof=1) * np.sqrt(252.0) * 100.0


# ============================================================ zenginleştirme
def enrich(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Bar tablosuna gösterge kolonları ekler. Girdi `prices.bars()` çıktısı."""
    g = cfg["gostergeler"]
    out = df.copy()
    c = out["c"].astype(float)          # fiyat uzayı  → seviyeler
    ctr = out["c_tr"].astype(float)     # toplam getiri → momentum
    h, l = out["h"].astype(float), out["l"].astype(float)

    for n in g["sma"]:
        out[f"sma{n}"] = sma(c, n)
    for n in g["ema"]:
        out[f"ema{n}"] = ema(c, n)

    # Trend KAPISI toplam getiri uzayında — temettü kaymasını almasın diye
    out["sma50_tr"] = sma(ctr, 50)
    out["sma200_tr"] = sma(ctr, 200)

    out["rsi14"] = rsi(ctr, g["rsi_length"])
    m = g["macd"]
    out["macd"], out["macd_signal"], out["macd_hist"] = macd(ctr, m["fast"], m["slow"], m["signal"])

    b = g["bollinger"]
    out["bb_mid"], out["bb_up"], out["bb_low"], out["bb_pctb"], out["bb_width"] = \
        bollinger(c, b["length"], b["std"])

    out["atr14"] = atr(h, l, c, g["atr_length"])
    out["atr_pct"] = out["atr14"] / c.replace(0.0, np.nan) * 100.0
    out["adx14"], out["di_plus"], out["di_minus"] = adx(h, l, c, g["adx_length"])

    out["high_52w"] = h.rolling(252, min_periods=100).max()
    out["low_52w"] = l.rolling(252, min_periods=100).min()
    out["dist_high52_pct"] = (c / out["high_52w"] - 1.0) * 100.0

    out["vol_ann_63"] = realized_vol(ctr, g["vol_pencere_gun"])
    out["turnover_med_63"] = out["turnover_try"].rolling(
        g["vol_pencere_gun"], min_periods=g["vol_pencere_gun"]).median()

    for n in (21, 63, 126, 252):
        out[f"ret_{n}"] = (ctr / ctr.shift(n) - 1.0) * 100.0

    return out


# ============================================================ saklama
def compute_and_store(cfg: dict, con: sqlite3.Connection,
                      tickers: list[str] | None = None,
                      start: str | None = None) -> dict:
    """Göstergeleri hesaplar ve `indicator_daily`'ye yazar (dondurur)."""
    from . import universe

    g = cfg["gostergeler"]
    sv = g["set_version"]
    min_bar = int(g["min_bar_hesap_icin"])
    tickers = tickers or universe.all_tickers(con)
    now = util.utc_now_iso()
    sonuc: dict[str, int] = {}

    for t in tickers:
        df = prices.bars(con, t)
        if len(df) < min_bar:
            log.warning("%s: %d bar < %d — gösterge hesaplanmadı", t, len(df), min_bar)
            sonuc[t] = 0
            continue

        e = enrich(df, cfg)
        if start:
            e = e[e["date"] >= start]

        rows = []
        for r in e.itertuples(index=False):
            rows.append((t, r.date, sv,
                         *(_n(getattr(r, k)) for k in INDICATOR_COLS[3:-1]),
                         now))
        sonuc[t] = db.upsert_many(con, "indicator_daily", INDICATOR_COLS, rows)
        log.info("gösterge %s: %d satır", t, sonuc[t])

    return {"tickers": len(tickers), "satir": sonuc, "set_version": sv}


def _n(x) -> float | None:
    """NaN → None. Sessiz NaN taşımak, 'hesaplanamadı'yı 'sıfır' gibi gösterir."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(v) else v


def load(con: sqlite3.Connection, ticker: str, cfg: dict, *,
         start: str | None = None, end: str | None = None) -> pd.DataFrame:
    sql = ("SELECT * FROM indicator_daily WHERE ticker = ? AND set_version = ?")
    params: list = [ticker.upper(), cfg["gostergeler"]["set_version"]]
    if start:
        sql += " AND date >= ?"; params.append(start)
    if end:
        sql += " AND date <= ?"; params.append(end)
    return pd.read_sql_query(sql + " ORDER BY date", con, params=params)


def snapshot(con: sqlite3.Connection, asof: str, cfg: dict) -> dict[str, dict]:
    """{ticker: gösterge satırı} — belirli bir gün için tüm evren."""
    rows = db.fetch_all(
        con, "SELECT * FROM indicator_daily WHERE date = ? AND set_version = ?",
        (asof, cfg["gostergeler"]["set_version"]))
    return {r["ticker"]: r for r in rows}
