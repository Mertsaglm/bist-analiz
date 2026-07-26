"""Replay — tüm boru hattını LLM OLMADAN geçmişte koşturur.

Planın en yüksek getirili tek aracı: iki yıllık canlı beklemeyi dakikalara
indirir. Veri → gösterge → seviye → faktör → plan → journal → resolver →
değerlendirme zinciri baştan sona işler, ama analist yerine **deterministik
bir vekil** geçer.

Vekil analist kasten APTALDIR: skoru en yüksek plana `plan_sec` der, gerekçe
olarak da hangi kuralı uyguladığını yazar. Amacı iyi karar vermek değil,
**boru hattının çalıştığını ve look-ahead sızdırmadığını kanıtlamak**.

Bu sayede Faz 6'nın değerlendirme metrikleri (IC, eşleştirilmiş alfa, hata
taksonomisi, slippage) LLM katmanı hiç yokken test edilebilir. Metrikler
canlıda ilk gün doğru çalışsın diye.
"""

from __future__ import annotations

import logging
import sqlite3

import numpy as np

from . import (backtest, db, factors, indicators, journal, levels as lv,
               planner, prices, regime as rj, resolver, universe, util)
from .calendar_bist import BistCalendar

log = logging.getLogger(__name__)

VEKIL = "replay"


def _vekil_analist(sira: int, toplam: int, skor: float | None) -> dict:
    """Deterministik vekil analist — kasten basit, kasten şeffaf.

    Enum'ları kuralla seçer, prose'a hangi kuralı uyguladığını yazar. LLM'in
    yerini almaz; boru hattının analist olmadan da uçtan uca koştuğunu gösterir.
    """
    if sira == 0:
        signal, action = "buy", "plan_sec"
    elif sira < max(1, toplam // 3):
        signal, action = "accumulate", "plan_sec"
    else:
        signal, action = "hold", "izle"
    guven = "orta" if sira == 0 else "dusuk"
    return {
        "signal": signal, "action": action, "confidence": guven,
        "thesis": (f"[VEKİL ANALİST] Kesitsel skor sıralamasında {sira + 1}. sırada "
                   f"(skor {skor:.3f}). Bu bir yargı değil, deterministik kural."
                   if skor is not None else "[VEKİL ANALİST] Skor yok."),
        "counter_scenario": "[VEKİL] Skor sıralaması ileri getiriyle ilişkisiz olabilir.",
        "key_risk": "[VEKİL] Ölçülen kenar yok (ADR #008); bu bir kenar iddiası değildir.",
        "falsifier": "[VEKİL] 5 işlem günü içinde plan stop'u tetiklenirse tez düşer.",
    }


def run(cfg: dict, con: sqlite3.Connection, *, start: str, end: str,
        adim_gun: int | None = None, top_n: int = 3) -> dict:
    """Boru hattını `start`–`end` arasında `adim_gun` aralıklarla koşturur."""
    cal = BistCalendar(cfg, con)
    adim = adim_gun or int(cfg["planlayici"]["zaman_bariyeri_gun"])
    canli = universe.live(con)
    olcum = universe.measure(con)
    smap = universe.sector_map(con)
    tiers = universe.tier_map(con)

    # Faktörler için panel bir kez kurulur — dönem başına SQL sorgusu yapılmaz.
    panel = backtest.load_panel(con, olcum, start=None, end=end)
    feat = backtest.build_features(panel, cfg)
    tarih_idx = {d: i for i, d in enumerate(panel.dates)}
    H = int(cfg["planlayici"]["zaman_bariyeri_gun"])
    wh = factors.weights_hash(cfg)

    gunler = [d.isoformat() for d in cal.trading_days(start, end)]
    gunler = [d for d in gunler if d in tarih_idx][::adim]

    kayit = {"donem": 0, "tahmin": 0, "plan_yok": 0, "atlanan": 0}
    for asof in gunler:
        t = tarih_idx[asof]
        if t < backtest.ISINMA_BAR or t + H + 1 >= panel.n:
            kayit["atlanan"] += 1
            continue

        skor = backtest.score_at(panel, feat, cfg, t, horizon_days=H,
                                 sector_map=smap)
        rej = rj.classify(cfg, con, asof)
        bariyer = cal.add_trading_days(asof, H).isoformat()
        snap = indicators.snapshot(con, asof, cfg)
        xu = prices.index_series(con, "XU100", start=asof, end=asof)

        # Canlı evrendeki isimleri skora göre sırala
        adaylar = []
        for tk in canli:
            if tk not in panel.tickers:
                continue
            i = panel.tickers.index(tk)
            if np.isfinite(skor[i]):
                adaylar.append((tk, float(skor[i]), i))
        if not adaylar:
            kayit["atlanan"] += 1
            continue
        adaylar.sort(key=lambda x: -x[1])

        run_id = journal.create_run(cfg, con, asof=asof, tool=VEKIL,
                                    bundle_sha=f"replay-{asof}")
        kayit["donem"] += 1

        for sira, (tk, s, i) in enumerate(adaylar[:top_n]):
            ind = snap.get(tk)
            bars = prices.bars(con, tk, end=asof)
            if not ind or len(bars) < 260:
                kayit["plan_yok"] += 1
                continue
            sev = lv.build_levels(bars, cfg, atr=ind.get("atr14"))
            opts, _ = planner.build_options(
                cfg, ticker=tk, asof=asof, bars=bars, ind=ind, seviyeler=sev,
                regime=rej, tier=tiers.get(tk), time_barrier_date=bariyer)
            gecerli = [o for o in opts if not planner.validate_option(o, cfg)]
            if not gecerli:
                kayit["plan_yok"] += 1
                continue

            planner.store(cfg, con, gecerli[:1])
            journal.record_from_plan(
                cfg, con, run_id=run_id, asof=asof, ticker=tk,
                plan_option=gecerli[0],
                analist=_vekil_analist(sira, len(adaylar), s),
                faktor={"score": s, "rank": sira + 1,
                        "pct": (len(adaylar) - sira - 1) / max(len(adaylar) - 1, 1) * 100,
                        "weights_hash": wh},
                regime=rej["label"],
                referans={"close": float(panel.c[t, i]),
                          "xu100": float(xu["c"].iloc[0]) if len(xu) else None,
                          "ew_index": None,
                          "atr14": ind.get("atr14")})
            kayit["tahmin"] += 1

    coz = resolver.resolve_open(cfg, con)
    return {"donem": kayit["donem"], "tahmin": kayit["tahmin"],
            "plan_yok": kayit["plan_yok"], "atlanan_gun": kayit["atlanan"],
            "cozum": coz, "aralik": f"{start} … {end}", "adim_gun": adim}


def reset(cfg: dict, con: sqlite3.Connection) -> dict:
    """Replay çıktısını temizler — GERÇEK analiz kayıtlarına dokunmaz.

    Yalnız `tool='replay'` olan run'lar ve onlara bağlı tahmin/sonuçlar silinir.
    """
    run_ids = [r["run_id"] for r in db.fetch_all(
        con, "SELECT run_id FROM llm_runs WHERE tool = ?", (VEKIL,))]
    if not run_ids:
        return {"run": 0, "tahmin": 0, "sonuc": 0}
    ph = ",".join("?" * len(run_ids))
    n_out = con.execute(
        f"DELETE FROM outcomes WHERE prediction_id IN "
        f"(SELECT prediction_id FROM predictions WHERE run_id IN ({ph}))",
        run_ids).rowcount
    n_pred = con.execute(
        f"DELETE FROM predictions WHERE run_id IN ({ph})", run_ids).rowcount
    n_run = con.execute(f"DELETE FROM llm_runs WHERE run_id IN ({ph})",
                        run_ids).rowcount
    con.commit()
    return {"run": n_run, "tahmin": n_pred, "sonuc": n_out}
