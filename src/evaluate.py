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
    """Journal'da hangi araçtan kaç TAHMİN var — çözülmüş olma şartı YOK.

    ⚠ NE OLUYORDU (2026-08-28 denetimi): bu sorgu `outcomes` ile INNER JOIN
    yapıyordu, yani yalnız ÇÖZÜLMÜŞ sonucu olan araçları görüyordu. Ölçüldü:

        araclar()  →  {'replay': 20, 'gemini-3.6-flash': 3, 'claude-code': 2}
        gerçek     →  gemini-3.5-flash 252 · gemini-3.6-flash 54 · replay 20 ·
                      gpt-5-mini 18 · claude-code 18

    Son üç haftanın BÜTÜN kararlarını veren model (`gemini-3.5-flash`, 252
    tahmin, 79 veto) değerlendirmeye hiç girmiyordu: `reports/` altında
    `degerlendirme_gemini-3.5-flash_*.md` diye bir dosya YOK ve 2026-08-16 ile
    08-23 Telegram haftalık özetleri birbirinin birebir aynısıydı. Kullanıcının
    sohbetinde günlük mesajlar her gün "🤖 gemini-3.5-flash" diyordu; haftalık
    özet o modeli hiç anmadı.

    Bu, ADR #013'ün temel vaadini — *"hangi model daha iyi analist sorusunu
    sistem kendisi cevaplayacak"* — YAPISAL OLARAK imkânsız kılıyordu: yeni bir
    modele geçildiği an o model, ilk sonucu çözülene kadar (≈1 ay) görünmez
    oluyor ve bu arada eski modellerin karnesi rapor ediliyordu.

    L-023 aynı JOIN'i `veto_value` ve `llm_contribution` için kaldırmıştı
    (bkz. `_tum_tahminler`) ama ARAÇ SAYIMINA uygulamamıştı — L-008'in
    "simetriğini ara" kuralı, aynı dosyanın 40 satır yukarısında.

    ⚠ Dönen sayı ÇÖZÜLMÜŞ değil TAHMİN sayısıdır; tüketici bunu öyle
    etiketlemek zorundadır. `saglik` "journal kaynağı" kontrolü aynı olguyu
    zaten böyle sayıyordu — iki kanalın eşliğini artık test zorluyor
    (tests/test_evaluate.py::TestAracSayimi).
    """
    return {r["tool"]: r["n"] for r in db.fetch_all(
        con,
        "SELECT r.tool, COUNT(*) n FROM predictions p "
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


def _tum_tahminler(con: sqlite3.Connection, *, tool: str | None = None) -> list[dict]:
    """TÜM tahminler — çözülmüş olma şartı YOK.

    ⚠ `_cozulmus` `outcomes` ile INNER JOIN yapar ve bu, iki ölçümü sessizce
    öldürüyordu (2026-08-15 denetimi):
      * `veto_value` — veto edilen tahminin `plan_id`'si NULL → plan açılmaz →
        outcome yazılmaz → satır JOIN'de düşer. 17 veto varken karne `0` diyordu.
      * `llm_contribution` — kesit yalnız SEÇİLEN 2 isimden kuruluyordu ve
        fonksiyon dönem başına ≥3 isim istiyordu; yani eşik yapısal olarak
        HİÇ geçilemezdi (üç kaynakta da `n=0`).
    Bu fonksiyon o iki ölçümün doğru paydasıdır.
    """
    sql = ("SELECT p.*, r.tool FROM predictions p "
           "  JOIN llm_runs r ON r.run_id = p.run_id")
    params: tuple = ()
    if tool:
        sql += " WHERE r.tool = ?"
        params = (tool,)
    return db.fetch_all(con, sql + " ORDER BY p.asof, p.ticker", params)


def _plansiz_alfa(cfg: dict, con: sqlite3.Connection,
                  satirlar: list[dict]) -> dict[str, float]:
    """{prediction_id: H günlük PLANSIZ alfa} — giriş/stop/hedef HESABA GİRMEZ.

    "Bu ismi o gün alıp H gün tutsaydık, eşit-ağırlık evrene göre ne olurdu?"
    Plan tetiklenmemiş, hatta hiç açılmamış olabilir — ölçtüğü şey planın değil
    KARARIN kalitesi. `veto_value` ve `llm_contribution` bunun üzerine kurulur.

    `resolver`ın ızgarası ve EW tabanı KULLANILIR, kopyalanmaz: ileri getiri
    tanımı sistemde tek olmalı (`fwd_ret_20d` de aynı yerden gelir).
    """
    from . import resolver

    H = int(cfg["olcum"]["ana_ufuk_gun"])
    gunler = resolver._izgara(con)
    idx = {d: i for i, d in enumerate(gunler)}
    ew_onbellek: dict[tuple[str, str], float | None] = {}
    out: dict[str, float] = {}

    for r in satirlar:
        t = idx.get(r["asof"])
        if t is None or t + 1 + H >= len(gunler):
            continue                      # ufuk dolmadı — ölçüm YOK, sıfır DEĞİL
        d0, d1 = gunler[t + 1], gunler[t + 1 + H]
        a = db.scalar(con, "SELECT c_tr FROM bars_daily WHERE ticker=? AND date=?",
                      (r["ticker"], d0))
        b = db.scalar(con, "SELECT c_tr FROM bars_daily WHERE ticker=? AND date=?",
                      (r["ticker"], d1))
        if not a or not b:
            continue
        if (d0, d1) not in ew_onbellek:
            ew_onbellek[(d0, d1)] = resolver._ew_return(con, cfg, d0, d1)
        ew = ew_onbellek[(d0, d1)]
        if ew is None:
            continue
        out[r["prediction_id"]] = (float(b) / float(a) - 1.0) * 100.0 - ew
    return out


def _cozulmus(con: sqlite3.Connection, *, tool: str | None = None) -> list[dict]:
    # `p.*` `position_size_pct`'i de getirir — boyutlandırma karşı-olgusu ona
    # dayanır ve şema değişikliği gerektirmez.
    sql = ("SELECT p.*, o.resolution, o.ret_pct, o.ret_pct_equal_size, "
           "       o.alpha_vs_ew, o.alpha_vs_xu100, o.hit, o.error_tag, "
           "       o.slippage_pct, o.holding_days, "
           "       o.entry_date, o.exit_date, r.tool "
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

    # ÜÇÜNCÜ SAYI — ÖRTÜŞME AYIKLANMIŞ (2026-08-15 denetimi).
    #
    # ⚠ Journal her işlem günü yeni bir tahmin yazar; aynı isim art arda
    # seçilirse AYNI İŞLEM birden çok satır olur ve `dist_stats` onları
    # bağımsız gözlem sayar. ÖLÇÜLDÜ: `2026-07-30-TUPRS-1` ve
    # `2026-08-03-TUPRS-1` aynı gün girdi (08-04), aynı gün çıktı (08-06) —
    # tek işlem, iki "hedef" kaydı. Canlı karne bu yüzden **+2.25pp (n=4)**
    # diyordu; örtüşme ayıklanınca **−0.90pp (n=3)**.
    #
    # Bedeli yalnız ortalama değil: örtüşen gözlemle `sd` küçülür ve `t`
    # ŞİŞER — yani sistem kendine olması gerekenden fazla güvenir. PROJECT.md
    # "örtüşmeyen pencere" disiplinini `backtest.py` için yazmıştı; canlı
    # journal'a hiç uygulanmamıştı.
    #
    # Üç sayı da raporlanır çünkü ÜÇ FARKLI SORU: "plan tuttuğunda ne oldu?"
    # (ort) · "karar başına ne kazandım?" (ort_karar_basina) · "kaç BAĞIMSIZ
    # olay yaşadım?" (ort_bagimsiz).
    tekil: dict[tuple, list[float]] = {}
    for r in rows:
        tekil.setdefault(
            (r["ticker"], r["entry_date"], r["exit_date"]), []).append(
                r["alpha_vs_ew"])
    bagimsiz = [float(np.mean(v)) for v in tekil.values()]
    b = stats.dist_stats(bagimsiz, o["zayif_n_esigi"])
    s["n_bagimsiz"] = len(bagimsiz)
    s["ort_bagimsiz"] = b["ort"]
    s["t_bagimsiz"] = b["t"]
    s["hukum_bagimsiz"] = stats.edge_verdict(
        b["ort"], b["n"], o["zayif_n_esigi"], o["min_anlamli_fark_puan"])
    s["ortusen_kayit"] = len(rows) - len(bagimsiz)
    return s


def information_coefficient(cfg: dict, con: sqlite3.Connection, *,
                            tool: str | None = None) -> dict:
    """Dönem-içi IC — karar VERDİĞİMİZ günlerde, TÜM kesit üzerinde.

    Journal yalnız 2-3 isim taşır; sıralama kalitesini o üç isimle ölçmek
    anlamsız olurdu. Bunun yerine journal bize KARAR GÜNLERİNİ verir, panel
    de o günlerdeki tam kesiti — böylece her dönem evrenin tamamı kullanılır.
    """
    from . import universe

    # ⚠ DÖNEM SETİ `outcomes`'A BAĞLI OLAMAZ (2026-08-15 denetimi). Eski sürüm
    # `_cozulmus`tan alıyordu, yani IC yalnız "o gün bir plan açıldı VE çözüldü"
    # günlerinden hesaplanıyordu. Canlıda 10 karar günü vardı, IC 4'ünü görüyordu;
    # plan üretilmeyen bir gün (08-14) hiç girmiyordu. Bu gizli bir KOŞULLAMADIR:
    # sıralama kalitesi ölçümü, plan SONUÇLARINA koşullanmış bir alt kümeden
    # hesaplanıyordu. IC zaten panelden hesaplanır; `outcomes`'a ihtiyacı yok.
    tarihler = sorted({r["asof"] for r in _tum_tahminler(con, tool=tool)})
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
    sırası, AYNI isimler üzerinde) ve farkları eşleştirilmiş olarak özetlenir.
    Fark ≤ 0 ise LLM sıralamaya değer KATMIYOR demektir ve veto+haber görevine
    indirilir. Bu, LLM katmanının kendini savunmak zorunda olduğu yerdir.

    ⚠ KESİT `outcomes`'TAN DEĞİL, O GÜNÜN TÜM TAHMİNLERİNDEN kurulur.
    Eski sürüm çözülmüş tahminleri kullanıyordu ve dönem başına ≥3 isim
    istiyordu; sistem ise dönem başına en fazla 2 plan seçiyor
    (`maks_pozisyon` risk-off'ta 2). Yani eşik YAPISAL OLARAK hiç geçilemezdi
    ve metrik üç kaynakta da `n=0` / "ölçüm yok" diyordu — bir "henüz veri yok"
    değil, hiç dolmayacak bir ölçüm (2026-08-15 denetimi).

    Doğru kesit 18 isimdir: LLM o günün TAMAMINA sinyal verir, sıralama
    kalitesi de tamamı üzerinden ölçülür. Hedef değişken PLANSIZ alfadır —
    plan tetiklenmiş olsun olmasın, kararın kendisi ölçülür.
    """
    rows = _tum_tahminler(con, tool=tool)
    alfa_map = _plansiz_alfa(cfg, con, rows)
    donemler: dict[str, list[dict]] = {}
    for r in rows:
        if r["prediction_id"] in alfa_map:
            donemler.setdefault(r["asof"], []).append(r)

    farklar: list[float] = []
    for _, grup in sorted(donemler.items()):
        # Skoru olmayan isimler (SMA200 kapısından düşenler) sıralamaya
        # GİREMEZ: `pct` NULL'ken "en kötü" saymak, bilinmeyeni sayıya
        # çevirmek olurdu. LLM tarafı için de aynı kesit kullanılır ki
        # iki IC AYNI isimler üzerinde hesaplansın (eşleştirme şartı).
        grup = [g for g in grup if g["score"] is not None]
        if len(grup) < 3:
            continue                     # 3 isimden az kesitte sıra korelasyonu anlamsız
        alfa = [alfa_map[g["prediction_id"]] for g in grup]
        llm = [SIGNAL_ORDINAL.get(g["signal"], 3) for g in grup]
        skor = [g["score"] for g in grup]
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

    Fark, vetolananların ortalama plansız alfası eksi seçilenlerinkidir.
    Negatif farkta vetolanan grup daha zayıf gitmiştir. Pozitif fark,
    veto edilen grupta daha yüksek ileri alfa görüldüğünü gösterir.

    ⚠ BU ÖLÇÜM 2026-08-16'ya KADAR KENDİ KONUSUNU ELİYORDU. Kaynak `_cozulmus`
    idi ve o `outcomes` ile INNER JOIN yapıyor; veto edilen bir tahminin
    `plan_id`'si NULL → plan açılmaz → outcome yazılmaz → satır JOIN'de düşer.
    Sonuç: `predictions`'ta 17 `plan_reddet` varken karne her kaynakta
    `veto_sayisi: 0` diyordu. Günlük rapor ise "veto analistin en ölçülebilir
    katkısı" başlığını her gün basıyordu (2026-08-15 denetimi).

    Fonksiyonun eski `not` alanı zaten doğru şeyi söylüyordu: *"vetolananların
    PLANSIZ ileri getirisi ayrıca izlenmeli"*. Artık izleniyor — `fwd_ret_20d`
    ile aynı tanım, aynı ızgara, aynı EW taban.

    İki grup AYNI ölçekte karşılaştırılır (ikisi de plansız alfa): "seçtiğimiz
    plan ne kadar kazandırdı" ile "elediğimiz isim ne yaptı" farklı sorular ve
    farklı ölçeklerdir; birini `outcomes.alpha_vs_ew`, diğerini plansız alfayla
    ölçmek elmayla armut kıyaslamak olurdu.
    """
    rows = _tum_tahminler(con, tool=tool)
    alfa_map = _plansiz_alfa(cfg, con, rows)
    veto = [r for r in rows if r["action"] == "plan_reddet"]
    v_alfa = [alfa_map[r["prediction_id"]] for r in veto
              if r["prediction_id"] in alfa_map]
    s_alfa = [alfa_map[r["prediction_id"]] for r in rows
              if r["action"] == "plan_sec" and r["prediction_id"] in alfa_map]
    kodlar = Counter(r["veto_code"] for r in veto if r["veto_code"])

    o = cfg["olcum"]
    fark = (float(np.mean(v_alfa)) - float(np.mean(s_alfa))
            if v_alfa and s_alfa else None)
    # Fark POZİTİFSE veto ZARAR veriyor (elediklerimiz daha iyi gitti).
    # `edge_verdict` mutlak büyüklüğe bakar; işaret yorumu `not`ta yazılı.
    s = stats.dist_stats(v_alfa, o["zayif_n_esigi"])
    return {
        "veto_sayisi": len(veto),
        "veto_kodlari": dict(kodlar),
        "n_olculen": len(v_alfa),
        "vetolanan_ort_alfa": float(np.mean(v_alfa)) if v_alfa else None,
        "secilen_ort_alfa": float(np.mean(s_alfa)) if s_alfa else None,
        "fark": fark,
        "hukum": stats.edge_verdict(fark, min(len(v_alfa), len(s_alfa)),
                                    o["zayif_n_esigi"], o["min_anlamli_fark_puan"])
        if fark is not None else stats.HUKUM_OLCUM_YOK,
        "sd": s.get("sd"),
        "not": ("Birim: yüzde puan, PLANSIZ ileri getiri (H=ana_ufuk_gun), EW "
                "tabana göre. **Fark POZİTİFSE veto ZARAR veriyor** — elenen "
                "isimler seçilenleri geçmiş demektir. Vetolananların planı "
                "açılmadığı için ikisi de plansız ölçülür; aksi hâlde farklı "
                "ölçekler kıyaslanırdı."),
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


def yarim_bar_kosulari(con: sqlite3.Connection, *, tool: str | None = None,
                       tolerans_pct: float = 0.10,
                       oran_esigi: float = 0.5) -> list[dict]:
    """Kapanmamış seansın barıyla üretilmiş koşuları BULUR — kayıttan değil ÖLÇÜMDEN.

    ⚠ YAŞANDI (2026-07-29): o günün 18 tahmininin **18'inde de**
    `close_at_asof`, barın gerçek kapanışından yüksekti — ortalama %1.21, hepsi
    aynı yönde. `llm_runs.created_utc` 10:38 UTC (13:38 TR): seans AÇIKTI.
    Yarım bar kapısı 2026-08-11'de eklendi ama o kayıt journal'da duruyor ve
    `claude-code` aracının **tek canlı karne satırı** o koşudan geliyor.

    Journal DEĞİŞMEZDİR — silme yok. Yapılacak şey ayırmak: karne bu koşuyu
    ayrıca işaretler, okuyan kişi hangi sayının hangi zemine dayandığını bilir.

    NEDEN BİR BAYRAK KOLONU DEĞİL: bayrak yazılırken unutulabilir ya da yanlış
    yazılabilir; bu hesap `predictions.close_at_asof` ile `bars_daily.c`'yi
    karşılaştırır ve HER ZAMAN gerçeği söyler. Kayıt değil, ölçüm.

    `tolerans_pct` float32→float64 gürültüsünün üstünde (gözlendi: 42.6 vs
    42.5999984741 = %0.0000004); `oran_esigi` ise tek bir ismin geriye dönük
    düzeltmesiyle TÜM koşuyu suçlamamak için — yarım bar KESİTSELDİR, o gün
    işlem gören her ismi birden etkiler.
    """
    sql = ("SELECT r.run_id, r.tool, r.asof, r.created_utc, "
           "       COUNT(*) n, "
           "       SUM(CASE WHEN b.c IS NOT NULL AND p.close_at_asof > 0 "
           "                 AND ABS(b.c / p.close_at_asof - 1.0) * 100 > ? "
           "            THEN 1 ELSE 0 END) sapan, "
           "       AVG(CASE WHEN b.c IS NOT NULL AND p.close_at_asof > 0 "
           "            THEN (b.c / p.close_at_asof - 1.0) * 100 END) ort_sapma "
           "  FROM predictions p "
           "  JOIN llm_runs r ON r.run_id = p.run_id "
           "  LEFT JOIN bars_daily b ON b.ticker = p.ticker AND b.date = p.asof ")
    params: list = [tolerans_pct]
    if tool:
        sql += " WHERE r.tool = ? "
        params.append(tool)
    sql += " GROUP BY r.run_id HAVING sapan >= n * ? AND n >= 3"
    params.append(oran_esigi)
    return [dict(r, sapan_oran=round(r["sapan"] / r["n"] * 100, 1))
            for r in db.fetch_all(con, sql, tuple(params))]


def tetiklenmeme_bedeli(cfg: dict, con: sqlite3.Connection, *,
                        tool: str | None = None) -> dict:
    """Tetiklenmeyen planlar ölçümden düşüyor — DÜŞERKEN ne kaybediyoruz?

    `giris_olmadi` sonucu getiri hesaplanmadan kapanır ve `paired_alpha`'nın
    paydasından TAMAMEN çıkar. Bu, limitli girişin bedelini görünmez kılar:
    geri çekilme yapmayan (yani YÜKSELEN) isimler sistematik olarak elenir.

    ÖLÇÜLDÜ (2026-08-15): 20 replay sonucunun 7'si (%35) hiç tetiklenmedi;
    plansız H=20 alfaları **+6.93pp**, tetiklenenlerinki **+5.08pp** → fark
    **+1.85pp**. Yön, "limitli giriş bir avantajdır" hipotezinin TERSİ.

    Burada karşılaştırılan iki büyüklük de PLANSIZ alfadır (`fwd_alpha_20d_ew`)
    — tetiklenmeyenin planlı getirisi zaten yok; planlıyla plansızı kıyaslamak
    farklı ölçekleri kıyaslamak olurdu.
    """
    rows = _cozulmus(con, tool=tool)
    ids = {r["prediction_id"] for r in rows}
    if not ids:
        return {"n_tetiklenmeyen": 0, "n_tetiklenen": 0, "fark": None,
                "hukum": stats.HUKUM_OLCUM_YOK, "not": ""}
    ph = ",".join("?" * len(ids))
    fwd = {r["prediction_id"]: r["fwd_alpha_20d_ew"] for r in db.fetch_all(
        con, f"SELECT prediction_id, fwd_alpha_20d_ew FROM outcomes "
             f" WHERE prediction_id IN ({ph}) AND fwd_alpha_20d_ew IS NOT NULL",
        tuple(ids))}
    yok = [fwd[r["prediction_id"]] for r in rows
           if r["resolution"] == "giris_olmadi" and r["prediction_id"] in fwd]
    var = [fwd[r["prediction_id"]] for r in rows
           if r["resolution"] not in ("giris_olmadi", "iptal_kurumsal",
                                      "iptal_veri")
           and r["prediction_id"] in fwd]
    fark = (float(np.mean(yok)) - float(np.mean(var))) if yok and var else None
    o = cfg["olcum"]
    return {
        "n_tetiklenmeyen": len(yok), "n_tetiklenen": len(var),
        "tetiklenmeyen_ort": float(np.mean(yok)) if yok else None,
        "tetiklenen_ort": float(np.mean(var)) if var else None,
        "fark": fark,
        "hukum": (stats.edge_verdict(fark, min(len(yok), len(var)),
                                     o["zayif_n_esigi"], o["min_anlamli_fark_puan"])
                  if fark is not None else stats.HUKUM_OLCUM_YOK),
        "not": ("Birim: yüzde puan, PLANSIZ ileri getiri. **Fark POZİTİFSE "
                "kaçırdıklarımız girdiklerimizden iyi gitmiş** — yani limitli "
                "giriş bir avantaj değil, bir SEÇİM YANLILIĞI olabilir ve karne "
                "bunu göremez (`giris_olmadi` paydadan düşer)."),
    }


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
    return _tek(cfg, con, tool)


def run_all(cfg: dict, con: sqlite3.Connection) -> dict:
    """HER kaynağı AYRI ayrı ölçer. Hiçbir metrik toplanmaz.

    ⚠ `run()` birden çok kaynak varken `KaynakKarisik` fırlatır ve bu bilinçli
    bir sürtünmedir — ama elle koşulan `bist degerlendir` için çıkmaz sokaktı:
    kullanıcı `--tool` yazmadıkça HİÇBİR şey göremiyordu. Sonuç, canlı
    analistlerin çözülmüş kararlarının hiçbir raporda görünmemesiydi.

    Buradaki çözüm kuralı GEVŞETMİYOR: karıştırma yasağı "iki kaynağın sayısını
    tek bir sayıda topla" demekti; yan yana ve ayrı ayrı basmak o yasağın ihlali
    değil, tam da amacı. `run()` değişmedi — programatik çağıranlar hâlâ tek
    kaynak seçmek zorunda.
    """
    mevcut = araclar(con)
    sirali = sorted(mevcut.items(), key=lambda kv: (-kv[1], kv[0]))
    return {"sayim": mevcut,
            "kaynaklar": [_tek(cfg, con, t) for t, _ in sirali]}


def _tek(cfg: dict, con: sqlite3.Connection, tool: str | None) -> dict:
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
        "tetiklenmeme": tetiklenmeme_bedeli(cfg, con, tool=tool),
        "yarim_bar": yarim_bar_kosulari(con, tool=tool),
        "donem_yil": 252.0 / int(cfg["olcum"]["ana_ufuk_gun"]),
    }
