"""Değerlendirme — HIZLI DÖNGÜ. Ağırlıklara ASLA dokunmaz.

İki döngü ayrımı (ADR #004) burada uygulanır:

    YAVAŞ döngü (`backtest.py`) : 10 yıl × geniş evren → faktör AĞIRLIKLARI
    HIZLI döngü (bu dosya)      : canlı journal → ağırlığa dokunmaz

Hızlı döngünün ölçtükleri ve ne zaman anlamlı hale gelecekleri:

| metrik | ne ölçer | ne zaman anlamlı |
|---|---|---|
| dönem-içi IC | sıralama kalitesi | ~18 ay |
| eşleştirilmiş alfa | seçim kalitesi | 3-4 yıl |
| LLM katkısı | LLM sıralamaya değer katıyor mu | ~18-24 ay |
| veto değeri | veto işe yarıyor mu | ~1 yıl |
| slippage | plan uygulanabilir mi | ~3 ay |
| Brier / güvenilirlik | güven kalibrasyonu | 2+ yıl |
| hata taksonomisi | nitel | sürekli |

**Bu modülün en önemli davranışı erken kenar iddia ETMEMESİ.** Her hüküm
`edge_verdict`ten geçer ve `required_n` her raporda basılır — "ne zaman
bilebiliriz?" bir his değil, hesaplanmış bir sayıdır.
"""

from __future__ import annotations

import logging
import sqlite3
from collections import Counter

import numpy as np

from . import backtest, db, stats

log = logging.getLogger(__name__)

# LLM sinyalini sıralanabilir sayıya çeviren harita (yüksek = daha boğa)
SIGNAL_ORDINAL = {"strong_buy": 6, "buy": 5, "accumulate": 4, "hold": 3,
                  "reduce": 2, "sell": 1, "avoid": 0}


class KaynakKarisik(RuntimeError):
    """Journal birden çok araçtan kayıt taşıyor ama hangisi ölçüleceği belirsiz."""


def araclar(con: sqlite3.Connection) -> dict[str, int]:
    """Journal'da hangi araçtan kaç ÇÖZÜLMÜŞ tahmin var."""
    return {r["tool"]: r["n"] for r in db.fetch_all(
        con,
        "SELECT r.tool, COUNT(*) n FROM predictions p "
        "  JOIN outcomes o ON o.prediction_id = p.prediction_id "
        "  JOIN llm_runs r ON r.run_id = p.run_id "
        " GROUP BY r.tool ORDER BY n DESC")}


def kaynak_sec(con: sqlite3.Connection, tool: str | None) -> str | None:
    """`--tool` verilmediyse güvenli kaynağı seç ya da REDDET.

    ⚠ Sessizce karıştırmak yasak. `bist replay` VEKİL bir analist kullanır
    (kasten aptal, deterministik bir kural); onun alfasını gerçek LLM
    kayıtlarıyla aynı potaya koymak, ölçümün ne ölçtüğünü belirsizleştirir —
    ve rapor bunu hiçbir yerde yazmazdı.

    Tek kaynak varsa sürtünme yaratmaya gerek yok: seç, ama HANGİSİNİ
    seçtiğini söyle. Birden çok kaynak varsa karar kullanıcınındır.
    """
    if tool:
        return tool
    mevcut = araclar(con)
    if len(mevcut) <= 1:
        return next(iter(mevcut), None)
    dokum = " · ".join(f"{k}={v}" for k, v in mevcut.items())
    raise KaynakKarisik(
        f"Journal {len(mevcut)} farklı araçtan kayıt taşıyor ({dokum}).\n"
        "Bunları karıştırmak ölçümün ne ölçtüğünü belirsizleştirir — "
        "`replay` VEKİL bir analisttir, gerçek analizle aynı potaya girmez.\n"
        f"Hangisini ölçmek istediğini yaz:  bist degerlendir --tool "
        f"{next(iter(mevcut))}")


def _cozulmus(con: sqlite3.Connection, *, tool: str | None = None) -> list[dict]:
    # `p.*` `position_size_pct`'i de getirir — boyutlandırma karşı-olgusu ona
    # dayanır ve şema değişikliği gerektirmez.
    sql = ("SELECT p.*, o.resolution, o.ret_pct, o.ret_pct_equal_size, "
           "       o.alpha_vs_ew, o.alpha_vs_xu100, o.hit, o.error_tag, "
           "       o.slippage_pct, o.holding_days, r.tool "
           "  FROM predictions p "
           "  JOIN outcomes o ON o.prediction_id = p.prediction_id "
           "  JOIN llm_runs r ON r.run_id = p.run_id")
    params: tuple = ()
    if tool:
        sql += " WHERE r.tool = ?"
        params = (tool,)
    return db.fetch_all(con, sql + " ORDER BY p.asof", params)


# ============================================================ metrikler
def paired_alpha(cfg: dict, con: sqlite3.Connection, *, tool: str | None = None) -> dict:
    """Gerçekleşen alfa — eşit-ağırlık evrene göre, AYNI dönemde.

    Eşleştirilmiş tasarım: piyasa faktörü tam sadeleşir. Getirisi olmayan
    sonuçlar (giris_olmadi, iptal_*) HARİÇTİR — onlar tahmin değil,
    gerçekleşmemiş plandır.

    ⚠ PAYDA GÖRÜNÜR OLMALI (AGENTS.md §11 madde 2, 2026-08-11 denetimi).
    `ort` **girişi tetiklenen** planların ortalamasıdır; ölçüldüğünde 20
    çözülmüş tahminin 7'si (%35) hiç dolmamış ve paydadan sessizce düşmüştü.
    Haftalık Telegram satırı ise "replay (N=20) alfa 4.27pp" diye basıyordu —
    okuyan kişi 20 gözlemli bir 4.27 sanıyor, gerçekte 13 gözlemli.

    O yüzden burası İKİ sayı birden döner:
        ort              → girişi olan planların alfası (N = `n`)
        ort_karar_basina → girmeyenler 0 alfa sayılarak (N = `n_karar`)
    İkisi farklı soruyu cevaplar ("plan tuttuğunda ne oldu?" vs "karar başına
    ne kazandım?") ve ikisi de raporlanır.
    """
    tum = _cozulmus(con, tool=tool)
    rows = [r for r in tum if r["alpha_vs_ew"] is not None]
    a = [r["alpha_vs_ew"] for r in rows]
    o = cfg["olcum"]
    s = stats.dist_stats(a, o["zayif_n_esigi"])
    s["hukum"] = stats.edge_verdict(s["ort"], s["n"], o["zayif_n_esigi"],
                                    o["min_anlamli_fark_puan"])
    s["xu100_ort"] = (float(np.mean([r["alpha_vs_xu100"] for r in rows
                                     if r["alpha_vs_xu100"] is not None]))
                      if rows else None)
    s["n_karar"] = len(tum)
    s["n_girmeyen"] = len(tum) - len(rows)
    s["ort_karar_basina"] = (
        float(np.mean([r["alpha_vs_ew"] or 0.0 for r in tum])) if tum else None)
    return s


def information_coefficient(cfg: dict, con: sqlite3.Connection, *,
                            tool: str | None = None) -> dict:
    """Dönem-içi IC — karar VERDİĞİMİZ günlerde, TÜM kesit üzerinde.

    Journal yalnız 2-3 isim taşır; sıralama kalitesini o üç isimle ölçmek
    anlamsız olurdu. Bunun yerine journal bize KARAR GÜNLERİNİ verir, panel
    de o günlerdeki tam kesiti — böylece her dönem evrenin tamamı kullanılır.
    """
    from . import universe

    tarihler = sorted({r["asof"] for r in _cozulmus(con, tool=tool)})
    if not tarihler:
        return stats.ic_summary([])

    olcum_ev = universe.measure(con)
    if not olcum_ev:
        return stats.ic_summary([])
    try:
        p = backtest.load_panel(con, olcum_ev)
    except ValueError:
        # Fiyat paneli yoksa IC ÖLÇÜLEMEZ — bu bir hata değil, bir durumdur.
        # İstisna fırlatmak `bist degerlendir`i taze kurulumda çökertirdi.
        log.info("Panel yok — IC ölçülemiyor (önce `bist veri backfill`)")
        return stats.ic_summary([])
    feat = backtest.build_features(p, cfg)
    idx = {d: i for i, d in enumerate(p.dates)}
    H = int(cfg["olcum"]["ana_ufuk_gun"])
    smap = universe.sector_map(con)

    ics: list[float] = []
    for d in tarihler:
        t = idx.get(d)
        if t is None or t < backtest.ISINMA_BAR or t + H + 1 >= p.n:
            continue
        skor = backtest.score_at(p, feat, cfg, t, horizon_days=H, sector_map=smap)
        with np.errstate(invalid="ignore"):
            fwd = (p.c_tr[t + 1 + H] / p.c_tr[t + 1] - 1.0) * 100.0
        m = np.isfinite(skor) & np.isfinite(fwd)
        if m.sum() < 4:
            continue
        i = np.where(m)[0]
        # Spearman SIRA korelasyonudur; kesitten sabit bir ortalama çıkarmak
        # sıraları değiştirmez. Eski kod `fwd[i] - fwd[i].mean()` yazıyordu —
        # zararsız ama işlevsiz; "alfaya göre IC" izlenimi veriyordu, oysa
        # ham ileri getiriyle birebir aynı sonucu üretir.
        ic = stats.spearman(skor[i], fwd[i])
        if ic is not None:
            ics.append(ic)
    return stats.ic_summary(ics, cfg["olcum"]["zayif_n_esigi"])


def llm_contribution(cfg: dict, con: sqlite3.Connection, *,
                     tool: str | None = None) -> dict:
    """LLM'in sıralaması saf skordan İYİ Mİ?

    Dönem başına iki IC hesaplanır (LLM sinyal sırası vs deterministik skor
    sırası, aynı isimler üzerinde) ve farkları eşleştirilmiş olarak özetlenir.
    Fark ≤ 0 ise LLM sıralamaya değer KATMIYOR demektir ve veto+haber görevine
    indirilir. Bu, LLM katmanının kendini savunmak zorunda olduğu yerdir.
    """
    rows = [r for r in _cozulmus(con, tool=tool) if r["alpha_vs_ew"] is not None]
    donemler: dict[str, list[dict]] = {}
    for r in rows:
        donemler.setdefault(r["asof"], []).append(r)

    farklar: list[float] = []
    for _, grup in sorted(donemler.items()):
        if len(grup) < 3:
            continue                     # 3 isimden az kesitte sıra korelasyonu anlamsız
        alfa = [g["alpha_vs_ew"] for g in grup]
        llm = [SIGNAL_ORDINAL.get(g["signal"], 3) for g in grup]
        skor = [g["score"] for g in grup]
        if any(s is None for s in skor):
            continue
        ic_llm = stats.spearman(llm, alfa)
        ic_skor = stats.spearman(skor, alfa)
        if ic_llm is not None and ic_skor is not None:
            farklar.append(ic_llm - ic_skor)

    o = cfg["olcum"]
    s = stats.dist_stats(farklar, o["zayif_n_esigi"])
    # ⚠ BİRİM: bu bir IC FARKI (korelasyon), yüzde puan değil. `edge_verdict`
    # mutlak büyüklüğe bakar ve eşiği `min_anlamli_fark_puan` = 1.0 puandır;
    # IC farkını 100'le çarpıp o eşiğe sokmak, 0.01'lik bir farkı "zayıf kanıt"
    # ilan ediyordu. Bu tam olarak LESSONS L-006'da düzeltilen işaret/büyüklük
    # körlüğü — `ic_summary` düzeltilmiş ama BU ÇAĞRI YERİ atlanmıştı
    # (2026-07-27 denetimi). IC için doğru eşik türü t'dir.
    s["hukum"] = stats.ic_verdict(s["ort"], s["n"], s["t"], o["zayif_n_esigi"])
    # `yorum` alanı KALDIRILDI: `(s["ort"] or 0) > 0` diye işarete bakıp
    # anlamlılığa bakmıyordu ve hiçbir rapora da girmiyordu. Hüküm `hukum`da.
    return s


def veto_value(cfg: dict, con: sqlite3.Connection, *, tool: str | None = None) -> dict:
    """Veto edilen isimler sonradan nasıl gitti?

    Veto POZİTİF değerliyse vetolananların alfası seçilenlerinkinden DÜŞÜK
    olmalı. Tersi çıkarsa veto zarar veriyordur ve kapatılır — LLM katmanının
    en savunulabilir işlevi bile ölçüme tabidir.
    """
    rows = _cozulmus(con, tool=tool)
    veto = [r for r in rows if r["action"] == "plan_reddet"]
    secilen = [r["alpha_vs_ew"] for r in rows
               if r["action"] == "plan_sec" and r["alpha_vs_ew"] is not None]
    kodlar = Counter(r["veto_code"] for r in veto if r["veto_code"])
    return {
        "veto_sayisi": len(veto),
        "veto_kodlari": dict(kodlar),
        "secilen_ort_alfa": float(np.mean(secilen)) if secilen else None,
        "not": ("Veto edilen isimlerin sonraki getirisi ölçülemez — veto "
                "edildikleri için plan açılmadı. Ölçüm için vetolananların "
                "PLANSIZ ileri getirisi ayrıca izlenmeli (Faz 7 backlog)."),
    }


def sizing_counterfactual(cfg: dict, con: sqlite3.Connection, *,
                          tool: str | None = None) -> dict:
    """Rejim boyutlandırması işe yaradı mı? (ADR #004 §1.4)

    Karşılaştırılan iki büyüklük PORTFÖY KATKISIDIR, hisse getirisi değil:

        gerçekleşen = ret_pct × position_size_pct / 100   (rejim + tier boyutu)
        eşit        = ret_pct × maks_pozisyon_pct / 100   (boyutlandırma YOK)

    Pozitif fark, rejimin küçülttüğü pozisyonların ZARAR ettiğini (yani
    boyutlandırmanın işe yaradığını); negatif fark, kırpılan pozisyonların
    KAZANDIĞINI (boyutlandırmanın kenar yediğini) gösterir.

    ⚠ İlk sürümde `resolver` bu kolona `ret_pct`'i aynen yazıyordu, dolayısıyla
    fark TANIM GEREĞİ sıfırdı ve rejim katmanı ölçülemiyordu (2026-07-27
    denetimi). Şimdi gerçekten hesaplanıyor.
    """
    rows = [r for r in _cozulmus(con, tool=tool)
            if r["ret_pct"] is not None and r["ret_pct_equal_size"] is not None
            and r["position_size_pct"]]
    fark = [r["ret_pct"] * r["position_size_pct"] / 100.0 - r["ret_pct_equal_size"]
            for r in rows]
    s = stats.dist_stats(fark, cfg["olcum"]["zayif_n_esigi"])
    s["hukum"] = stats.edge_verdict(s["ort"], s["n"],
                                    cfg["olcum"]["zayif_n_esigi"],
                                    cfg["olcum"]["min_anlamli_fark_puan"])
    s["not"] = ("Birim: portföy yüzde PUANI (hisse getirisi değil). Pozitif = "
                "rejimin kırptığı pozisyonlar zarar etmiş (boyutlandırma işe "
                "yaramış); negatif = kırpılanlar kazanmış (boyutlandırma kenar "
                "yiyor). Referans boyut: `risk.maks_pozisyon_pct`.")
    return s


def brier(cfg: dict, con: sqlite3.Connection, *, tool: str | None = None) -> dict:
    """Güven kalibrasyonu. 2+ yıl `ölçüm yetersiz` diyecek — bu NORMALDİR."""
    NOT = ("Kova başına ~30-50 çözülmüş tahmin gerekir; bu 2+ yıl demektir.")
    rows = [r for r in _cozulmus(con, tool=tool) if r["hit"] is not None]
    if not rows:
        # Boş dönüşte de TÜM anahtarlar bulunmalı: rapor her durumda
        # üretilebilmeli. Eksik anahtar `bist degerlendir`i taze kurulumda
        # KeyError ile çökertiyordu.
        return {"n": 0, "brier": None, "hukum": stats.HUKUM_OLCUM_YOK,
                "kovalar": [], "not": NOT}
    skor = float(np.mean([(r["confidence_p"] - r["hit"]) ** 2 for r in rows]))

    kovalar = []
    for seviye in ("yuksek", "orta", "dusuk"):
        alt = [r for r in rows if r["confidence"] == seviye]
        if not alt:
            continue
        kovalar.append({
            "seviye": seviye, "n": len(alt),
            "iddia": float(np.mean([r["confidence_p"] for r in alt])),
            "gerceklesen": float(np.mean([r["hit"] for r in alt])),
        })
    zn = int(cfg["olcum"]["zayif_n_esigi"])
    return {"n": len(rows), "brier": round(skor, 4), "kovalar": kovalar,
            "hukum": (f"{stats.HUKUM_YETERSIZ} (N={len(rows)})" if len(rows) < zn * 3
                      else "ölçülebilir"),
            "not": NOT}


def slippage(con: sqlite3.Connection, *, tool: str | None = None) -> dict:
    """Planlanan giriş vs gerçekleşen dolum. En hızlı ölçülebilen metrik (~3 ay)."""
    v = [r["slippage_pct"] for r in _cozulmus(con, tool=tool)
         if r["slippage_pct"] is not None]
    return stats.dist_stats(v)


def error_taxonomy(con: sqlite3.Connection, *, tool: str | None = None) -> dict:
    rows = _cozulmus(con, tool=tool)
    return {
        "sonuc": dict(Counter(r["resolution"] for r in rows)),
        "hata_etiketi": dict(Counter(r["error_tag"] for r in rows if r["error_tag"])),
        "tetiklenmeme_orani": (
            round(sum(1 for r in rows if r["resolution"] == "giris_olmadi")
                  / len(rows) * 100, 1) if rows else None),
        "toplam": len(rows),
    }


# ============================================================ toplu
def run(cfg: dict, con: sqlite3.Connection, *, tool: str | None = None) -> dict:
    # Kaynak KARIŞIKSA burada durur (KaynakKarisik). "hepsi" diye sessizce
    # birleştirmek, vekil analistin sayılarını gerçek analizinkiyle aynı
    # potaya koymaktı — ve rapor bunu hiçbir yerde yazmıyordu.
    tool = kaynak_sec(con, tool)
    return {
        "tool": tool or "(kayıt yok)",
        "alfa": paired_alpha(cfg, con, tool=tool),
        "ic": information_coefficient(cfg, con, tool=tool),
        "llm_katkisi": llm_contribution(cfg, con, tool=tool),
        "veto": veto_value(cfg, con, tool=tool),
        "boyutlandirma": sizing_counterfactual(cfg, con, tool=tool),
        "brier": brier(cfg, con, tool=tool),
        "slippage": slippage(con, tool=tool),
        "taksonomi": error_taxonomy(con, tool=tool),
        "donem_yil": 252.0 / int(cfg["olcum"]["ana_ufuk_gun"]),
    }
