"""Piyasa rejimi — pozisyon boyutunu ve nakit oranını etkiler.

**FAKTÖR AĞIRLIKLARINI ETKİLEMEZ.** Rejim-koşullu ağırlıklandırma klasik bir
overfit kapısıdır: rejim tanımı serbestlik derecesidir ve dondurulmadan
doğrulanamaz. Rejimin işi risk yönetimi — ne alacağını değil, NE KADAR
alacağını ve ne kadar nakitte kalacağını söyler.

Bu ayrım ölçülene kadar korunur. Ölçmek için: `outcomes.ret_pct_equal_size`
karşı-olgusu (rejim boyutlandırmalı getiri vs eşit boyutlandırmalı) — Faz 6.

⚠ Yeniden çerçeveleme notu (ADR #008): rejim etiketi bir TAHMİN değil, bir
DURUM TESPİTİdir. "Risk-off" piyasanın düşeceğini söylemez; şu anda geniş
tabanlı bir zayıflık olduğunu söyler ve buna göre daha az risk alınmasını önerir.
"""

from __future__ import annotations

import sqlite3

import numpy as np

from . import db, macro, prices, util

ETIKETLER = ("risk-on", "neutral", "transition", "risk-off")


def _vol_ann(seri: np.ndarray, n: int = 21) -> float | None:
    if len(seri) < n + 1:
        return None
    r = np.diff(np.log(seri[-(n + 1):]))
    if not np.isfinite(r).all():
        return None
    return float(np.std(r, ddof=1) * np.sqrt(252) * 100)


def breadth(con: sqlite3.Connection, cfg: dict, asof: str) -> float | None:
    """Evrenin yüzde kaçı SMA50'sinin üstünde? Genişlik = katılım ölçüsü.

    Endeks yükselirken genişlik düşüyorsa ralli birkaç isme dayanıyordur —
    endeksin tek başına söylemediği şey budur.
    """
    from . import universe

    tickers = universe.measure(con)
    if not tickers:
        return None
    ph = ",".join("?" * len(tickers))
    # `sma50` FİYAT uzayında hesaplanıyor (indicators.py), dolayısıyla ham
    # kapanış `c` ile karşılaştırılır. `c_tr` (toplam getiri) ile kıyaslamak
    # birim hatası olurdu — temettü kadar sistematik sapma üretirdi.
    rows = db.fetch_all(
        con,
        f"SELECT b.c, i.sma50 FROM bars_daily b "
        f"JOIN indicator_daily i ON i.ticker = b.ticker AND i.date = b.date "
        f"WHERE b.date = ? AND i.set_version = ? AND b.ticker IN ({ph})",
        (asof, cfg["gostergeler"]["set_version"], *tickers))
    gecerli = [r for r in rows if r["c"] and r["sma50"]]
    if len(gecerli) < 5:
        return None
    return float(sum(1 for r in gecerli if r["c"] > r["sma50"]) / len(gecerli) * 100)


def classify(cfg: dict, con: sqlite3.Connection, asof: str) -> dict:
    """Rejim etiketi + pozisyon politikası. Girdiler denetlenebilir biçimde saklanır."""
    r = cfg["rejim"]
    xu = prices.index_series(con, "XU100", end=asof)
    usd = prices.index_series(con, "USDTRY", end=asof)

    girdiler: dict = {}
    xu_c = xu["c"].to_numpy(float) if len(xu) else np.array([])
    sma200 = float(np.mean(xu_c[-200:])) if len(xu_c) >= 200 else None
    xu_fark = (float(xu_c[-1] / sma200 - 1) * 100
               if sma200 and len(xu_c) else None)
    girdiler["xu100_vs_sma200_pct"] = xu_fark
    girdiler["breadth_above_sma50_pct"] = breadth(con, cfg, asof)
    girdiler["xu100_vol_ann_21"] = _vol_ann(xu_c) if len(xu_c) else None
    girdiler["usdtry_vol_ann_21"] = (_vol_ann(usd["c"].to_numpy(float))
                                     if len(usd) else None)

    mctx = macro.context(cfg, con, asof)
    for k in ("politika_faizi", "tufe_yoy", "enf_bek_12ay", "reel_net_mevduat"):
        girdiler[k] = mctx.get(k)

    etiket = _label(girdiler, r)
    pol = dict(r["politika"][etiket])

    # Makro verisi büyük ölçüde eksikse DEFANSİF kayma. Bilmemek, bilmek gibi
    # davranmaktan iyidir — nakit önerisi yukarı çekilir.
    eksik = macro.null_pct(cfg, mctx)
    if eksik > 70:
        pol["nakit_pct"] = min(100.0, pol["nakit_pct"] + 10.0)
        girdiler["makro_eksik_pct"] = eksik

    return {
        "date": asof, "label": etiket, **girdiler,
        "cash_pct": pol["nakit_pct"], "max_positions": pol["maks_pozisyon"],
        "size_multiplier": pol["boyut_carpani"],
        "sektor_basi_maks": r["sektor_basi_maks_pozisyon"],
        "inputs": girdiler,
    }


def _label(g: dict, r: dict) -> str:
    """Etiketleme — eksik veri varsa DAİMA daha defansif tarafa düşer."""
    fark, gen = g.get("xu100_vs_sma200_pct"), g.get("breadth_above_sma50_pct")
    if fark is None or gen is None:
        return "transition"          # bilmiyorsak orta-defansif
    on, off = r["esikler"]["risk_on"], r["esikler"]["risk_off"]
    if fark >= on["xu100_sma200_farki_pct_min"] and gen >= on["genislik_sma50_ustu_pct_min"]:
        return "risk-on"
    if fark <= off["xu100_sma200_farki_pct_maks"] or gen <= off["genislik_sma50_ustu_pct_maks"]:
        return "risk-off"
    if fark < 0 or gen < 50:
        return "transition"
    return "neutral"


def store(cfg: dict, con: sqlite3.Connection, rej: dict) -> int:
    return db.upsert_many(
        con, "regime_daily",
        ["date", "label", "xu100_vs_sma200_pct", "breadth_above_sma50_pct",
         "xu100_vol_ann_21", "usdtry_vol_ann_21", "policy_rate", "cpi_yoy",
         "inflation_exp_12m", "real_rate", "cash_pct", "max_positions",
         "size_multiplier", "inputs"],
        [(rej["date"], rej["label"], rej.get("xu100_vs_sma200_pct"),
          rej.get("breadth_above_sma50_pct"), rej.get("xu100_vol_ann_21"),
          rej.get("usdtry_vol_ann_21"), rej.get("politika_faizi"),
          rej.get("tufe_yoy"), rej.get("enf_bek_12ay"), rej.get("reel_net_mevduat"),
          rej["cash_pct"], rej["max_positions"], rej["size_multiplier"],
          util.json_dump(rej["inputs"], pretty=False))])
