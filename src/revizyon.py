"""Ön kayıtlı revizyon turu #1.

Ön kayıt: `docs/on-kayit-revizyon-01.md`
sha256 (koşudan ÖNCE mühürlendi): 6677c29647460357d75605c13d6daf7e8867c6a9211a991a2893b42f8acddf70

İKİ değişiklik, teşhisin İŞARET ETTİĞİ:
  1. SMA200 kapısı skorlama yolundan çıkar (likidite + veri kapıları KALIR)
  2. Ana ufuk H=20 → H=42

Karar kuralı SONUCU GÖRMEDEN yazıldı ve burada MEKANİK olarak uygulanır:
    OOS'ta EW tabana göre  N≥15  VE  |Δ|≥1.0pp  VE  işaret POZİTİF
Gevşetilmiş eşik (t>1.65 vb.) KULLANILMAZ.

Başarısızlık halinde ikinci tur YOK — doğrudan yeniden çerçeveleme.
"""

from __future__ import annotations

import sqlite3

from . import backtest, factors, stats

ON_KAYIT_SHA = "6677c29647460357d75605c13d6daf7e8867c6a9211a991a2893b42f8acddf70"

# --- ön kayıtlı konfigürasyon ---
YENI_UFUK = 42
YENI_KAPILAR = {"sma200": False, "likidite": True, "veri": True}


def run(cfg: dict, con: sqlite3.Connection) -> dict:
    from . import universe

    o = cfg["olcum"]
    ev = universe.measure(con)
    smap = universe.sector_map(con)
    p = backtest.load_panel(con, ev)
    bol = backtest.split_index(p, o["oos_split"])

    TF = 1 / 3
    COST = float(cfg["risk"]["islem_maliyeti_gidis_donus_pct"])
    ESKI_UFUK = int(o["ana_ufuk_gun"])

    def koş(**kw):
        varsayilan = dict(top_frac=TF, cost_pct=COST, sector_map=smap)
        return backtest.walk_forward(cfg, p, **{**varsayilan, **kw})

    # --- referans (Faz 2'de başarısız olan kurulum) ---
    ref_tam = koş(horizon=ESKI_UFUK)
    ref_oos = koş(horizon=ESKI_UFUK, start_idx=bol)

    # --- ÖN KAYITLI KONFİGÜRASYON ---
    yeni_tam = koş(horizon=YENI_UFUK, kapilar=YENI_KAPILAR)
    yeni_oos = koş(horizon=YENI_UFUK, kapilar=YENI_KAPILAR, start_idx=bol)
    yeni_is = koş(horizon=YENI_UFUK, kapilar=YENI_KAPILAR, end_idx=bol)

    # --- tek-kol OOS katkıları (yorumlanabilirlik; karar VERMEZ) ---
    kollar = {
        "yalnız SMA200 kaldırıldı (H=20)":
            koş(horizon=ESKI_UFUK, kapilar=YENI_KAPILAR, start_idx=bol),
        "yalnız H=42 (SMA200 kapısı DURUYOR)":
            koş(horizon=YENI_UFUK, start_idx=bol),
    }

    # --- faktör bazlı OOS (yeni konfigürasyon) ---
    fakt = {ad: koş(horizon=YENI_UFUK, kapilar=YENI_KAPILAR,
                    weights=backtest.solo(ad), start_idx=bol)
            for ad in factors.FACTOR_NAMES}

    # --- KARAR: mekanik, ön kayıttaki kurala göre ---
    a = yeni_oos["alfa_ew"]
    zn = int(o["zayif_n_esigi"])
    md = float(o["min_anlamli_fark_puan"])
    hukum = stats.edge_verdict(a["ort"], a["n"], zn, md)
    gecti = (a["n"] >= zn and a["ort"] is not None
             and a["ort"] > 0 and abs(a["ort"]) >= md)

    return {
        "on_kayit_sha": ON_KAYIT_SHA,
        "ayar": {"ufuk": YENI_UFUK, "kapilar": YENI_KAPILAR, "top_frac": TF,
                 "maliyet": COST, "evren": len(ev), "oos_split": o["oos_split"]},
        "referans": {"tam": ref_tam, "oos": ref_oos, "ufuk": ESKI_UFUK},
        "yeni": {"tam": yeni_tam, "in_sample": yeni_is, "oos": yeni_oos},
        "kollar": kollar,
        "faktorler": fakt,
        "karar": {
            "gecti": gecti, "hukum": hukum,
            "kural": f"N≥{zn} VE |Δ|≥{md:.1f}pp VE işaret pozitif",
            "olculen": {"N": a["n"], "delta": a["ort"], "t": a["t"]},
        },
        # Gerçekten koşulan `koş()` sayısı: ref_tam, ref_oos, yeni_tam,
        # yeni_oos, yeni_is (5) + 2 kol + faktör başına 1. İlk sürüm `6 + len`
        # yazıyordu ve bir eksikti — çoklu test muhasebesini eksik gösteriyordu.
        "n_test": 7 + len(fakt),
        "n_teshis_test": 24,
    }
