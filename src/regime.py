"""Piyasa rejimi — pozisyon boyutunu ve nakit oranını etkiler.

**FAKTÖR AĞIRLIKLARINI ETKİLEMEZ.** Rejim-koşullu ağırlıklandırma klasik bir
overfit kapısıdır: rejim tanımı serbestlik derecesidir ve dondurulmadan
doğrulanamaz. Rejimin işi risk yönetimi — ne alacağını değil, NE KADAR
alacağını ve ne kadar nakitte kalacağını söyler.

Bu ayrım ölçülene kadar korunur. Ölçüm aracı: `outcomes.ret_pct_equal_size`
karşı-olgusu — rejim boyutuyla açılan pozisyonun PORTFÖY KATKISI vs sabit
referans boyutla açılsaydı ne katardı (`evaluate.sizing_counterfactual`).

⚠ Bu kolon 2026-07-27'ye kadar `ret_pct`'in KOPYASIYDI, yani fark tanım gereği
sıfırdı ve rejim katmanı ölçülüyor görünüp hiç ölçülmüyordu (ADR #009).
Düzeltildikten sonraki İLK ölçüm: replay N=13, **−0.22pp (t=−2.51)** — yani
rejimin kırptığı pozisyonlar kazanmış olabilir. Hüküm `ölçüm yetersiz`;
N≥15'e ulaşınca ilk kez gerçek bir cevap verilebilecek.

⚠ Yeniden çerçeveleme notu (ADR #008): rejim etiketi bir TAHMİN değil, bir
DURUM TESPİTİdir. "Risk-off" piyasanın düşeceğini söylemez; şu anda geniş
tabanlı bir zayıflık olduğunu söyler ve buna göre daha az risk alınmasını önerir.
"""

from __future__ import annotations

import logging
import sqlite3

import numpy as np

from . import db, macro, prices, util

log = logging.getLogger(__name__)

ETIKETLER = ("risk-on", "neutral", "transition", "risk-off")


def _vol_ann(seri: np.ndarray, n: int = 21) -> float | None:
    if len(seri) < n + 1:
        return None
    r = np.diff(np.log(seri[-(n + 1):]))
    if not np.isfinite(r).all():
        return None
    return float(np.std(r, ddof=1) * np.sqrt(252) * 100)


def breadth(con: sqlite3.Connection, cfg: dict, asof: str) -> tuple[float | None, int, int]:
    """Evrenin yüzde kaçı SMA50'sinin üstünde? `(pct, kullanilan_n, istenen_n)`.

    Endeks yükselirken genişlik düşüyorsa ralli birkaç isme dayanıyordur —
    endeksin tek başına söylemediği şey budur.

    ⚠ PAYDA DÖNDÜRÜLÜR ÇÜNKÜ PAYDA SESSİZCE DÜŞÜYORDU. Bu sorgu
    `indicator_daily`'ye JOIN atar; göstergesi hesaplanmamış isim satır
    üretmez. Ölçüldü (2026-07-24 paketi): 67 isimlik ölçüm evreni istenmesine
    rağmen 16 isim kullanılmış, genişlik 5/16 = %31.25 çıkmış ve `risk_off`
    eşiği (≤%35) tetiklenmişti — XU100 SMA200'ünün **%9.7 ÜSTÜNDEYKEN**,
    nakit önerisi %90'a çıkmıştı. 67 isimle eşiğin hangi tarafına düşeceği
    bilinmiyordu, çünkü kimse paydaya bakmıyordu.
    """
    from . import universe

    tickers = universe.measure(con)
    if not tickers:
        return None, 0, 0
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
        log.warning("%s: genişlik ölçülemiyor — %d ticker istendi, %d tanesinin "
                    "göstergesi var (<5)", asof, len(tickers), len(gecerli))
        return None, len(gecerli), len(tickers)
    if len(gecerli) < len(tickers) * 0.8:
        log.warning("%s: genişlik DAR PAYDA ile hesaplanıyor — %d/%d isim. "
                    "Rejim etiketi ve nakit oranı buna dayanıyor; tamamlamak "
                    "için `bist gosterge`.", asof, len(gecerli), len(tickers))
    pct = float(sum(1 for r in gecerli if r["c"] > r["sma50"]) / len(gecerli) * 100)
    return pct, len(gecerli), len(tickers)


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
    gen_pct, gen_n, gen_istenen = breadth(con, cfg, asof)
    girdiler["breadth_above_sma50_pct"] = gen_pct
    girdiler["breadth_n"] = gen_n                  # PAYDA — denetlenebilirlik
    girdiler["breadth_istenen_n"] = gen_istenen
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
    # ⚠ `makro_eksik_pct` **`**girdiler` yayılımından ÖNCE** eklenmeli; ilk
    # sürümde sonra ekleniyordu ve alan `inputs` içinde görünüp üst seviyede
    # görünmüyordu (aynı sözlük nesnesi olduğu için).
    eksik = macro.null_pct(cfg, mctx)
    girdiler["makro_eksik_pct"] = eksik
    if eksik > 70:
        pol["nakit_pct"] = min(100.0, pol["nakit_pct"] + 10.0)

    return {
        "date": asof, "label": etiket, **girdiler,
        # Etiketi hangi koşulun ürettiği. `store` yalnız adı geçen kolonları
        # yazar, bu alan şemayı bozmaz; paket ve rapor buradan okur.
        "tetikleyici": tetikleyici(girdiler, r, etiket),
        "cash_pct": pol["nakit_pct"], "max_positions": pol["maks_pozisyon"],
        "size_multiplier": pol["boyut_carpani"],
        "sektor_basi_maks": r["sektor_basi_maks_pozisyon"],
        "inputs": girdiler,
    }


def _label(g: dict, r: dict) -> str:
    """Etiketleme — eksik veri varsa DAİMA daha defansif tarafa düşer.

    ⚠ KURAL ASİMETRİKTİR ve bu bilinçlidir: `risk-on` İKİ koşulu birden ister
    (AND), `risk-off` ise BİRİNE yeter (OR). Gerekçe "dar ralliye güvenme" —
    endeks yükselirken genişlik düşükse ralli birkaç isme dayanıyordur.

    Ama sonucu görünür olmalı: ölçüldü (37 kayıt), 16 risk-off etiketinin
    **14'ü** genişlik tek başına tetiklemiş ve bunların çoğunda XU100 SMA200'ün
    ÜSTÜNDEYDİ (2026-03-31'de +%11.13). Etiketi okuyan biri "endeks düşüyor"
    sanıyordu. `tetikleyici()` bu yanılgıyı kapatır.
    """
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


def tetikleyici(g: dict, r: dict, etiket: str) -> str:
    """Etiketi HANGİ koşul üretti? Rapora ve pakete giren tek satır.

    `_label` ile AYNI eşiklere bakar ve onun hemen yanında durur — ikisi
    ayrışırsa rapor, kararı üreten kuraldan başka bir şey anlatır (§12.2).
    Bu bir ölçüm değil, bir İFŞADIR: rejim politikası burada değişmez.
    """
    fark, gen = g.get("xu100_vs_sma200_pct"), g.get("breadth_above_sma50_pct")
    if fark is None or gen is None:
        eksik = "XU100/SMA200" if fark is None else "genişlik"
        return f"{eksik} hesaplanamadı → bilmiyorsak defansif tarafa düşülür"
    on, off = r["esikler"]["risk_on"], r["esikler"]["risk_off"]
    xu = f"XU100 SMA200'ün %{abs(fark):.2f} {'ÜSTÜNDE' if fark >= 0 else 'ALTINDA'}"
    gn = f"genişlik %{gen:.1f}"
    if etiket == "risk-off":
        # OR kuralı: hangisinin tetiklediğini AYRI AYRI söyle.
        xu_tetikledi = fark <= off["xu100_sma200_farki_pct_maks"]
        gen_tetikledi = gen <= off["genislik_sma50_ustu_pct_maks"]
        nedenler = []
        if xu_tetikledi:
            nedenler.append(f"{xu} (≤ %{off['xu100_sma200_farki_pct_maks']})")
        if gen_tetikledi:
            nedenler.append(f"{gn} ≤ %{off['genislik_sma50_ustu_pct_maks']}")
        # ⚠ TETİKLEMEYEN koşulu da yaz — "endeks düşüyor" yanılgısını kapatan
        # şey tam olarak budur. Yalnız genişlik tetiklediğinde XU100'ün NEREDE
        # olduğunu görmek gerekir; çoğu zaman SMA200'ün üstündedir.
        if len(nedenler) == 1:
            nedenler.append(f"{gn if xu_tetikledi else xu} ise eşiğin dışında")
        return " · ".join(nedenler)
    if etiket == "risk-on":
        return (f"{xu} (≥ %{on['xu100_sma200_farki_pct_min']}) ve "
                f"{gn} ≥ %{on['genislik_sma50_ustu_pct_min']}")
    return f"{xu} · {gn} — hiçbir uç eşik tetiklenmedi"


def store(cfg: dict, con: sqlite3.Connection, rej: dict) -> int:
    """Rejim kararını `regime_daily`'ye dondurur.

    ⚠ Bu fonksiyon uzun süre HİÇ ÇAĞRILMADI (2026-07-27 denetimi: 0 referans,
    tablo 0 satır) — oysa `classify`'ın docstring'i "girdiler denetlenebilir
    biçimde saklanır" diyordu. Yani "2026-07-24'te neden risk-off dedik?"
    sorusunun cevabı hiçbir yerde yoktu; girdiler (genişlik, payda, makro
    eksikliği) her gün yeniden hesaplanıp atılıyordu. `planner.build_menu`
    artık her çağrıda buraya yazar — LESSONS L-002'nin tam olarak uyardığı
    "besleyen script yoksa tablo donar" durumu.
    """
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
