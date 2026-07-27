"""yfinance adaptörü — BIST fiyat ve kurumsal işlem verisi.

İKİ fiyat serisi döner, ikisi de aynı satırda:
    c     = Close (auto_adjust=False)  → bölünme düzeltmeli, temettü düzeltmesiz
    c_tr  = Adj Close                  → toplam getiri

ÖLÇÜLDÜ (2026-07-26), araştırmadaki iki "bilinen sorun"un aksine:
  * Temettü düzeltmesi ÇALIŞIYOR. TUPRS 2025-03-28 (7.78 TL temettü):
        Close 142.20 → 138.00  = −%2.95   |   Adj 124.16 → 127.47 = +%2.67
  * Bölünme geri düzeltmesi ÇALIŞIYOR. FROTO 2025-05-07 bedelsiz 10:1 sürekli.
  * XU100.IS 2020 bölen değişiminde sürekli.
Bunlar `tests/test_prices.py` içinde fixture testine bağlandı — Yahoo regresyona
giderse CI söyler. Bkz. LESSONS L-005.

Bu modül ASLA istisna fırlatmaz; başarısızlıkta boş DataFrame / boş liste döner.
Çağıran taraf "veri yok"u normal bir durum olarak ele alır (uydurma yapılmaz).
"""

from __future__ import annotations

import logging
import time
from datetime import date

import pandas as pd
import yfinance as yf

log = logging.getLogger(__name__)

_BAR_COLS = ["date", "o", "h", "l", "c", "v", "c_tr"]


def yf_symbol(ticker: str, cfg: dict) -> str:
    """'THYAO' → 'THYAO.IS'. Zaten ekliyse dokunmaz."""
    suffix = cfg["sources"]["yf"]["suffix"]
    t = ticker.strip().upper()
    return t if t.endswith(suffix) else f"{t}{suffix}"


def _history(symbol: str, cfg: dict, *, start: str | None, end: str | None,
             period: str | None = None) -> pd.DataFrame:
    """Ham yfinance çağrısı; yeniden deneme ve nazik bekleme ile."""
    ycfg = cfg["sources"]["yf"]
    deneme = int(ycfg.get("yeniden_deneme", 3))
    bekle = float(ycfg.get("istek_arasi_saniye", 0.4))
    son_hata: Exception | None = None

    for i in range(deneme):
        try:
            t = yf.Ticker(symbol)
            kw = {"auto_adjust": False, "actions": True}
            if period:
                df = t.history(period=period, **kw)
            else:
                df = t.history(start=start, end=end, **kw)
            time.sleep(bekle)
            if df is not None and not df.empty:
                return df
            log.warning("%s: boş veri döndü (deneme %d/%d)", symbol, i + 1, deneme)
        except Exception as e:                                  # noqa: BLE001
            son_hata = e
            log.warning("%s: hata (deneme %d/%d): %s", symbol, i + 1, deneme, e)
        time.sleep(bekle * (i + 1))

    if son_hata:
        log.error("%s: %d denemede alınamadı: %s", symbol, deneme, son_hata)
    return pd.DataFrame()


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """yfinance çıktısını (date, o, h, l, c, v, c_tr) tablosuna çevirir."""
    if df is None or df.empty:
        return pd.DataFrame(columns=_BAR_COLS)

    out = pd.DataFrame(index=df.index)
    out["o"] = df.get("Open")
    out["h"] = df.get("High")
    out["l"] = df.get("Low")
    out["c"] = df.get("Close")
    out["v"] = df.get("Volume")
    # Adj Close yoksa (bazı endekslerde) toplam getiri = ham kapanış.
    out["c_tr"] = df["Adj Close"] if "Adj Close" in df.columns else df.get("Close")

    out = out.reset_index()
    ts_col = out.columns[0]                      # 'Date' veya 'Datetime'
    out["date"] = pd.to_datetime(out[ts_col]).dt.strftime("%Y-%m-%d")
    out = out[_BAR_COLS]
    # Kapanışı olmayan satır kullanılamaz — sessizce taşımak yerine at.
    return out.dropna(subset=["c"]).drop_duplicates(subset=["date"], keep="last")


def fetch_bars(ticker: str, cfg: dict, *, start: str | None = None,
               end: str | None = None, period: str | None = None) -> pd.DataFrame:
    """Bir hissenin günlük barları. Sütunlar: date, o, h, l, c, v, c_tr."""
    sym = yf_symbol(ticker, cfg)
    start = start or cfg["sources"]["yf"]["backfill_start"]
    return _normalize(_history(sym, cfg, start=start, end=end, period=period))


def fetch_index(symbol: str, cfg: dict, *, start: str | None = None,
                end: str | None = None) -> pd.DataFrame:
    """Endeks/kur barları. `symbol` doğrudan Yahoo sembolüdür ('XU100.IS', 'USDTRY=X')."""
    start = start or cfg["sources"]["yf"]["backfill_start"]
    return _normalize(_history(symbol, cfg, start=start, end=end))


def fetch_actions(ticker: str, cfg: dict) -> list[dict]:
    """Kurumsal işlemler: temettü ve bölünme/bedelsiz.

    Döner: [{date, kind, value}] — kind ∈ {temettu, bolunme}.
    yfinance bunları hem uygular hem listeler; biz ayrıca SAKLIYORUZ çünkü
    plan penceresine düşen bir ex-tarih stop'u yapay olarak tetikler ve o planın
    sonucu 'iptal_kurumsal' olmalıdır (getiri/kayıp olarak sayılmamalı).
    """
    sym = yf_symbol(ticker, cfg)
    out: list[dict] = []
    try:
        t = yf.Ticker(sym)
        acts = t.actions
        time.sleep(float(cfg["sources"]["yf"].get("istek_arasi_saniye", 0.4)))
        if acts is None or acts.empty:
            return out
        for ts, row in acts.iterrows():
            d = pd.Timestamp(ts).strftime("%Y-%m-%d")
            div = float(row.get("Dividends", 0) or 0)
            spl = float(row.get("Stock Splits", 0) or 0)
            if div > 0:
                out.append({"date": d, "kind": "temettu", "value": div})
            if spl > 0:
                out.append({"date": d, "kind": "bolunme", "value": spl})
    except Exception as e:                                       # noqa: BLE001
        log.warning("%s: kurumsal işlem alınamadı: %s", sym, e)
    return out


def probe(ticker: str, cfg: dict, *, period: str = "6mo") -> dict:
    """Bir sembolün canlı durumu — evren taraması için hafif kontrol.

    Döner: {ticker, ok, bars, first_date, last_date, median_turnover_try,
            vol_ann_pct, zero_vol_ratio, reason}
    """
    df = fetch_bars(ticker, cfg, period=period)
    if df.empty:
        return {"ticker": ticker, "ok": False, "bars": 0, "reason": "veri yok"}

    import numpy as np

    c, v = df["c"].astype(float), df["v"].astype(float)
    r = np.log(c / c.shift()).dropna()
    return {
        "ticker": ticker,
        "ok": True,
        "bars": len(df),
        "first_date": df["date"].iloc[0],
        "last_date": df["date"].iloc[-1],
        "median_turnover_try": float((c * v).median()),
        "vol_ann_pct": float(r.std() * (252 ** 0.5) * 100) if len(r) > 1 else None,
        "zero_vol_ratio": float((v == 0).mean()),
        "reason": None,
    }
