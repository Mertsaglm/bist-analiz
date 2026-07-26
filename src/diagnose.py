"""Teşhis — kayıp nereden geliyor?

⚠ BU BİR REVİZYON TURU DEĞİLDİR. Burada strateji SEÇİLMEZ; enstrüman doğrulanır
ve kayıp bileşenlerine ayrılır. Çıktısı bir hüküm değil, bir TEŞHİSTİR.

Ayrım neden önemli: "geçene kadar varyant deneme" veri madenciliğidir. Teşhis
adımı bundan şu iki şeyle ayrılır —
  (a) hiçbir varyant "kazanan" ilan edilmez,
  (b) her kol ORTAK bir referanstan TEK TEK saptırılır, kombinasyon aranmaz.

İki soru:

1. **Enstrüman sağlam mı?** IC(tüm kesit) pozitif iken alfa negatifse, bu ya bir
   kurgu hatasıdır ya bir popülasyon farkıdır. `ic_tum` KAPISIZ tüm kesitte,
   `alfa_ew` ise KAPILI havuzun üst dilimlerinde hesaplanır — aynı şeyi
   ölçmezler. `ic_uygun` (kapılı havuz İÇİNDEKİ IC) bu ikisinin arasındaki
   köprüdür ve ayrışmanın kaynağını tek hamlede söyler.

2. **Kayıp hangi kolda?** Bu sistemde gerçekten DEĞİŞKEN olan beş kol var:
   kapı · maliyet · seçim genişliği · evren · ufuk. (Pozisyon büyüklüğü eşit
   ağırlık, rebalance takvimi ufka sabit, sektör kısıtı backtest'te yok —
   bunlar şu an sabit, ölçülecek bir şey sunmuyorlar.)
"""

from __future__ import annotations

import logging
import sqlite3

import numpy as np

from . import backtest, factors

log = logging.getLogger(__name__)


def run(cfg: dict, con: sqlite3.Connection) -> dict:
    """Enstrüman doğrulaması + beş kollu atıf dekompozisyonu."""
    from . import universe

    o = cfg["olcum"]
    olcum_ev = universe.measure(con)
    canli_ev = universe.live(con)
    smap = universe.sector_map(con)

    H = int(o["ana_ufuk_gun"])
    TF = 1 / 3
    COST = float(cfg["risk"]["islem_maliyeti_gidis_donus_pct"])

    p67 = backtest.load_panel(con, olcum_ev)
    p18 = backtest.load_panel(con, canli_ev)
    bol67 = backtest.split_index(p67, o["oos_split"])

    def koş(panel, **kw):
        varsayilan = dict(horizon=H, top_frac=TF, cost_pct=COST,
                          sector_map=smap, use_gates=True)
        return backtest.walk_forward(cfg, panel, **{**varsayilan, **kw})

    # ---------------------------------------------------------- referans
    ref = koş(p67)

    # ---------------------------------------------------------- 1) enstrüman
    enstruman = {
        "ic_tum": ref["ic_tum"],          # KAPISIZ tüm kesit
        "ic_uygun": ref["ic"],            # kapılı havuz İÇİ
        "ort_havuz": ref["ort_havuz"],
        "ort_secilen": ref["ort_secilen"],
    }
    # Skor→seçim yönü tutarlılığı: seçilenlerin ortalama skoru havuz
    # ortalamasından YÜKSEK olmalı. Değilse sıralama ters uygulanıyordur.
    feat = backtest.build_features(p67, cfg)
    yon_ok = yon_kontrol = 0
    for d in ref["donemler"]:
        skor = backtest.score_at(p67, feat, cfg, d["t"], horizon_days=H)
        sec = [p67.tickers.index(x) for x in d["secilenler"]]
        if not sec or not np.isfinite(skor).any():
            continue
        yon_kontrol += 1
        if float(np.nanmean(skor[sec])) > float(np.nanmean(skor)):
            yon_ok += 1
    enstruman["secim_yonu_dogru_oran"] = yon_ok / max(yon_kontrol, 1)
    enstruman["secim_yonu_n"] = yon_kontrol

    # ---------------------------------------------------------- 2) atıf
    # Her kol ORTAK referanstan TEK TEK saptırılır. Kombinasyon YOK.
    kollar: dict[str, dict] = {}

    kollar["kapı: kapalı (SMA200 yok)"] = koş(p67, use_gates=False)
    kollar["maliyet: %0.00"] = koş(p67, cost_pct=0.0)
    for tf in (0.15, 0.25, 0.50, 0.75):
        kollar[f"genişlik: üst %{tf*100:.0f}"] = koş(p67, top_frac=tf)
    kollar["evren: canlı 18 isim"] = koş(p18)
    for h in (10, 42, 63):
        kollar[f"ufuk: H={h}"] = koş(p67, horizon=h)

    ref_ort = ref["alfa_ew"]["ort"] or 0.0
    atif = []
    for ad, r in kollar.items():
        ort = r["alfa_ew"]["ort"]
        atif.append({
            "kol": ad, "n": r["alfa_ew"]["n"], "alfa": ort,
            "t": r["alfa_ew"]["t"],
            "delta": (ort - ref_ort) if ort is not None else None,
            "ic_tum": r["ic_tum"]["ic_ort"], "ic_uygun": r["ic"]["ic_ort"],
            "hukum": r["hukum"],
        })
    atif.sort(key=lambda x: -(x["delta"] or -1e9))

    # ---------------------------------------------------------- 3) IC × ufuk
    # Sıralama bilgisi hangi ufukta yaşıyor? Kapısız, tüm kesit.
    ic_ufuk = {}
    for h in (5, 10, 20, 42, 63):
        r = koş(p67, horizon=h, use_gates=False)
        ic_ufuk[h] = {"ic": r["ic_tum"], "alfa": r["alfa_ew"], "n": r["alfa_ew"]["n"]}

    # ---------------------------------------------------------- 4) faktör × IC
    fakt_ic = {}
    for ad in factors.FACTOR_NAMES:
        r = koş(p67, weights=backtest.solo(ad), use_gates=False)
        r_oos = koş(p67, weights=backtest.solo(ad), use_gates=False, start_idx=bol67)
        fakt_ic[ad] = {"tam": r["ic_tum"], "oos": r_oos["ic_tum"],
                       "alfa_tam": r["alfa_ew"], "alfa_oos": r_oos["alfa_ew"]}

    return {
        "referans": {"alfa": ref["alfa_ew"], "ic_tum": ref["ic_tum"],
                     "ic_uygun": ref["ic"], "n": ref["n_donem"],
                     "ayar": f"kapılı · %{COST:.2f} maliyet · üst %{TF*100:.0f} · "
                             f"67 isim · H={H}"},
        "enstruman": enstruman,
        "atif": atif,
        "ic_ufuk": ic_ufuk,
        "faktor_ic": fakt_ic,
        "n_test": len(kollar) + len(ic_ufuk) + 2 * len(fakt_ic) + 1,
    }


T_ANLAMLI = 2.0


def verdict(t: dict) -> dict:
    """Teşhisten çıkan mekanik sonuç — strateji SEÇMEZ, mekanizma ADLANDIRIR.

    ⚠ İŞARETE DEĞİL ANLAMLILIĞA bakar. İlk sürüm `ic_uygun > 0` diye kontrol
    ediyordu ve IC=0.009 (t=0.20) — yani düpedüz sıfır — "pozitif" sayılıp
    yanlış tanı üretiyordu. Sıfırdan büyük olmak bilgi taşımak değildir.
    """
    e = t["enstruman"]
    ic_t, t_t = e["ic_tum"]["ic_ort"], (e["ic_tum"]["t"] or 0.0)
    ic_u, t_u = e["ic_uygun"]["ic_ort"], (e["ic_uygun"]["t"] or 0.0)

    if e["secim_yonu_dogru_oran"] < 0.9:
        tani = "kurgu_hatasi"
        aciklama = ("Seçim yönü skorla tutarsız — sıralama ters uygulanıyor. "
                    "Revizyon konuşulmadan önce bu düzeltilmeli.")
    elif t_t < T_ANLAMLI:
        tani = "siralama_bilgisi_yok"
        aciklama = (f"Skor kapısız tüm kesitte bile sıralayamıyor "
                    f"(IC={ic_t:.3f}, t={t_t:.2f}). Uygulama düzeltmeleri bunu kurtarmaz.")
    elif t_u < T_ANLAMLI:
        tani = "kapi_bilgiyi_yok_ediyor"
        aciklama = (
            f"Sıralama bilgisi TÜM kesitte anlamlı (IC={ic_t:.3f}, t={t_t:.2f}) ama "
            f"kapının bıraktığı havuzun İÇİNDE yok oluyor (IC={ic_u:.3f}, t={t_u:.2f}) — "
            f"bilginin %{(1 - (ic_u or 0) / ic_t) * 100:.0f}'i kapıda kayboluyor. "
            "Ayrışma bir kurgu hatası DEĞİL: kapı, skorun ayırt edeceği aralığı "
            "zaten kesip atıyor. SMA200 filtresi düşük momentumlu isimleri "
            "eliyor — yani skorun sıralayacağı varyansın kaynağını.")
    else:
        tani = "sinyal_var_uygulama_yiyor"
        aciklama = ("Sıralama bilgisi hem tüm kesitte hem kapılı havuzda ANLAMLI. "
                    "Kayıp sıralamada değil uygulamada: genişlik, maliyet, yoğunlaşma.")

    return {"tani": tani, "aciklama": aciklama,
            "baskin_kol": t["atif"][0] if t["atif"] else None}
