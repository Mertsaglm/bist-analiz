"""Ön uçuş kontrolü — sessiz bozulma taraması.

2026-07-27 denetiminin ürettiği risk listesi elle koşulacak SQL'ler olarak
kalırsa koşulmaz (LESSONS L-002). Hepsi burada, tek çağrıda.

⚠ Bu mantık Faz 8'de `cli.cmd_saglik`'ten BURAYA taşındı. Sebebi katman
disiplini: otonom koşu (`src/otonom.py`) sağlık kapısını çağırmak zorunda ve
hiçbir modül `cli`'ı import edemez (`test_sozlesme.py::test_kimse_cli_yi_
import_etmez`). CLI artık ince bir kabuk: burayı çağırıp basıyor.

Çıkış kodu sözleşmesi — otomasyonun kapısı bu:
    0 temiz · 1 en az bir UYARI · 2 en az bir KRİTİK

═══════════════════════════════════════════════════════════════════════════
İKİ SINIF KONTROL — ve neden ayrıldıkları (2026-08-11 denetimi, L-016)
═══════════════════════════════════════════════════════════════════════════

**KAPI kontrolleri** — "bugünkü VERİYE güvenilir mi?" Yanıt hayırsa analiz
etmek zararlıdır, çünkü şeklen geçerli ama içi boş bir paket üretilir (L-009).
Bunlar KRİTİK olabilir ve `otonom.gunluk` onlarda durur. Hepsinin ortak
özelliği: **koşunun KENDİSİ tarafından düzeltilebilirler.** Bayat bar → veri
adımı çeker. Eksik gösterge → gösterge adımı hesaplar. Yarım bar → ayıklanır.

**GÖZLEM kontrolleri** — "sistem SÜREÇ olarak sağlıklı mı?" Bunlar sistemin
kendi geçmişine bakar ve **ASLA kapıyı kapatamazlar** (`ekle_gozlem` şiddeti
UYARI'da tavanlar). Sebep bir kilitlenme:

    L-015'te eklenen "atlanan koşu" kontrolü `MAX(predictions.asof)`e bakıyor
    ve fark ≥2 ise KRİTİK diyordu. `predictions` ise kapının ARKASINDA yazılır.
    2026-08-06'da GitHub runner işi almayınca fark 2 oldu, kapı kapandı ve
    AÇILAMADI — açılması için gereken tahmin, kapının arkasındaydı. Sistem
    4 işlem günü boyunca veri çekti, commit attı, SIFIR analiz üretti.

Kural: **bir gözlemci, gözlediği sürecin ürününe bakıp o süreci durduramaz.**
Yapısal karşılığı `ekle_gozlem`'dir; davranışsal kilidi
`tests/test_saglik.py::TestKapiKendiCiktisinaBakmaz`.
"""

from __future__ import annotations

import sqlite3

from . import db, journal, migrations, news, universe, util

KRITIK = "KRİTİK"
UYARI = "UYARI"
BILGI = "BİLGİ"
OK = "OK"

ISARET = {OK: "✓", KRITIK: "🛑", UYARI: "⚠", BILGI: "·"}

# Sistemin KENDİ GEÇMİŞİNE bakan kontroller. Kapıyı kapatamazlar; şiddetleri
# `ekle_gozlem` içinde UYARI'da tavanlanır. Liste belge değil SÖZLEŞMEDİR:
# `tests/test_saglik.py` her birinin KRİTİK üretemediğini davranışla sınar.
GOZLEM_KONTROLLERI = frozenset({
    "atlanan koşu",      # planlı koşu düştü mü (heartbeat)
    "analizsiz gün",     # koşu var ama analist üretmiyor
    "açık plan",         # journal'da açık plan var, portföy boş
    "çıktı mührü",       # analysis.json ezilmiş mi
})


def kontrol(cfg: dict, con: sqlite3.Connection, *,
            bugun_tr: str | None = None) -> dict:
    """Tüm kontrolleri koşar. {asof, bulgular:[(seviye, ad, mesaj)], kritik, uyari}

    Bağlantı SALT OKUNUR verilebilir ve verilmelidir — sağlık kontrolü hiçbir
    şeyi değiştirmez.

    `bugun_tr` yalnız TEST için enjekte edilir; verilmezse İstanbul duvar saati
    kullanılır. Zaman kaynağını gizlemek, AGENTS.md §11 madde 6'nın yasakladığı
    şeydir — o yüzden parametre var ve varsayılanı açıkça yazılı.
    """
    asof = db.scalar(con, "SELECT MAX(date) FROM bars_daily")
    bulgular: list[tuple[str, str, str]] = []
    bugun_tr = bugun_tr or util.bugun_tr(cfg["takvim"]["timezone"])

    def ekle(seviye, ad, tamam, mesaj):
        bulgular.append((OK if tamam else seviye, ad, mesaj))

    def ekle_gozlem(seviye, ad, tamam, mesaj):
        """GÖZLEM bulgusu — şiddet UYARI'da TAVANLANIR.

        Bu tavan bir üslup tercihi değil, kilidin YAPISAL çözümü: bir gözlem
        kontrolü ne döndürürse döndürsün kapıyı kapatamaz. Birisi ileride
        `return KRITIK, ...` yazsa bile sistem durmaz, sadece uyarır.
        """
        if ad not in GOZLEM_KONTROLLERI:
            raise RuntimeError(
                f"'{ad}' `ekle_gozlem` ile eklendi ama GOZLEM_KONTROLLERI "
                "kümesinde yok. Kontrolün sınıfı belirsiz kalmasın.")
        bulgular.append((OK if tamam else (UYARI if seviye == KRITIK else seviye),
                         ad, mesaj))

    # 0) BAR TAZELİĞİ — takvime göre. Diğer TÜM kontrollerin dayanağı budur.
    #
    # ⚠ Bu kontrol Faz 8'de eklendi ve gerçek bir körlüğü kapattı: aşağıdaki
    # kontroller göstergeyi/kaliteyi `MAX(bars_daily.date)`'e kıyaslıyor. Barlar
    # bayatlarsa `asof` da bayatlar ve her şey "tutarlı" görünür — kontroller
    # birbirini doğrular, hiçbiri dış dünyaya bakmaz. Otomasyonda bunun
    # karşılığı şu: veri gelmediği gün sistem DÜNKÜ raporu bugünmüş gibi
    # bildirir ve hiçbir yerde uyarı çıkmaz (L-007'nin bu projedeki üçüncü
    # görünümü: kod doğru, veri sessizce bayat, çıktı hâlâ geçerli görünüyor).
    #
    # Şiddet kademeli: yfinance'in bir seans gecikmesi olağan (gözlendi
    # 2026-08-01: cuma barı cumartesi sabahı hâlâ yoktu), iki seans değil.
    try:
        from .calendar_bist import BistCalendar
        cal = BistCalendar(cfg, con)
        beklenen = cal.last_closed_session()
        gecikme = cal.trading_days_between(asof, beklenen.isoformat()) if asof else 99
    except Exception:                                       # noqa: BLE001
        gecikme, beklenen = 0, None                         # takvim kurulamadıysa sus
    if beklenen is not None:
        ekle(KRITIK if gecikme >= 2 else UYARI, "bar tazeliği", gecikme <= 0,
             f"son bar {asof} · beklenen {beklenen.isoformat()}"
             + ("" if gecikme <= 0 else
                f" → {gecikme} seans geride (`bist veri gunluk`)"))

    # 1) Gösterge kapsaması — kesitsel her oranın PAYDASI
    n_bar = db.scalar(con, "SELECT COUNT(DISTINCT ticker) FROM bars_daily") or 0
    n_ind = db.scalar(con, "SELECT COUNT(DISTINCT ticker) FROM indicator_daily") or 0
    ekle(KRITIK, "gösterge kapsaması", n_ind >= n_bar,
         f"{n_ind}/{n_bar} ticker" + ("" if n_ind >= n_bar else " → `bist gosterge`"))

    # 2) Gösterge tazeliği
    son_ind = db.scalar(con, "SELECT MAX(date) FROM indicator_daily")
    ekle(KRITIK, "gösterge tazeliği", son_ind == asof,
         f"gösterge {son_ind} · bar {asof}"
         + ("" if son_ind == asof else " → `bist gosterge`"))

    # 3) Kalite kapısı açık mı
    son_kal = db.scalar(con, "SELECT MAX(date) FROM data_quality")
    ekle(KRITIK, "kalite kapısı", son_kal == asof,
         f"kalite {son_kal} · bar {asof}"
         + ("" if son_kal == asof else " → `bist veri kalite`"))

    # 4) Haber katmanı sağlığı
    hd = news.kaynak_durumu(con, asof) if asof else {"ok": False, "not": "veri yok"}
    ekle(KRITIK, "haber katmanı", bool(hd["ok"]),
         hd.get("not") or f"son bildirim {hd.get('son_bildirim')}")

    # 5) Tick ızgarası — açık uçlu bant TEK İSİMLE ölçüldü (EGEEN, 2.50 TL).
    # İkinci bir isim o banda GERÇEKTEN girerse (son kurumsal işlemden sonraki
    # ham barlarla) ölçüm tekrarlanmalı; split-düzeltmeli eski fiyatlar ham
    # ızgarada değildir ve yanlış alarm üretir.
    ust = max((b["ust_sinir"] or 0) for b in cfg["risk"]["fiyat_adimlari"][:-1])
    asan = db.fetch_all(
        con,
        "SELECT b.ticker, MAX(b.c) m FROM bars_daily b "
        "  JOIN (SELECT ticker, MAX(date) d FROM corporate_actions GROUP BY ticker) k "
        "    ON k.ticker = b.ticker AND b.date > k.d "
        " WHERE b.c > ? GROUP BY b.ticker ORDER BY m DESC", (ust,))
    ekle(UYARI, "tick ızgarası", len(asan) <= 1,
         f"açık uçlu bant (>{ust:.2f} TL) {len(asan)} isimle ölçülü: "
         + (", ".join(f"{r['ticker']}={r['m']:.0f}" for r in asan) or "gözlem yok")
         + ("" if len(asan) <= 1 else " → ikinci isim girdi, YENİDEN ÖLÇ"))

    # 6) Journal kaynak karışıklığı
    arac = {r["tool"]: r["n"] for r in db.fetch_all(
        con, "SELECT r.tool, COUNT(*) n FROM predictions p "
             " JOIN llm_runs r ON r.run_id = p.run_id GROUP BY r.tool")}
    ekle(UYARI, "journal kaynağı", len(arac) <= 1,
         f"{arac or 'kayıt yok'}"
         + ("" if len(arac) <= 1 else " → `bist degerlendir --tool ...` şart"))

    # 7) Evren ↔ taban çizgisi tutarlılığı
    n_out = db.scalar(con, "SELECT COUNT(*) FROM outcomes "
                           "WHERE alpha_vs_ew IS NOT NULL") or 0
    ekle(BILGI, "EW tabanlı sonuç", True,
         f"{n_out} kayıt · evren {len(universe.live(con))} canlı / "
         f"{len(universe.measure(con))} ölçüm")

    # 8) Şema sürümü
    sv = con.execute("PRAGMA user_version").fetchone()[0]
    ekle(KRITIK, "şema sürümü", sv == migrations.target_version(),
         f"v{sv} / hedef v{migrations.target_version()}")

    # 9-10) KESİTSEL AKIL SAĞLIĞI — iki uçtan da
    for seviye, ad, tamam, mesaj in _kesit_kontrolleri(cfg, con):
        ekle(seviye, ad, tamam, mesaj)

    # 11) DÜZELTİLMEMİŞ KURUMSAL İŞLEM — TÜM GEÇMİŞ, pencere YOK
    seviye, ad, tamam, mesaj = _duzeltilmemis_kurumsal(cfg, con)
    ekle(seviye, ad, tamam, mesaj)

    # 12) YARIM BAR — KAPI kontrolü. Kapanmamış seansın barıyla analiz yapmak
    # look-ahead'in en sinsi biçimidir ve journal DEĞİŞMEZ olduğu için
    # sonradan düzeltilemez (yaşandı: 2026-07-29, 18 tahmin, ort. %1.21 sapma).
    ekle(*_yarim_bar(cfg, con, asof))

    # 13) EVDS TAZELİĞİ — "değer var" ile "değer güncel" ayrı iki olgu
    ekle(*_evds_tazelik(cfg, con))

    # 14) ENDEKS TAZELİĞİ — 13'ün ARANMAYAN SİMETRİĞİ (L-008).
    # EVDS için tazelik kontrolü yazılmıştı, endeks için yazılmamıştı; ikisini
    # besleyen adım da aynı sebeple (zincire bağlı olmama) donmuştu.
    ekle(*_index_tazelik(cfg, con, asof))

    # --- GÖZLEM kontrolleri: buradan sonrası KAPIYI KAPATAMAZ (modül docstring) ---
    ekle_gozlem(*_atlanan_kosu(cfg, con, bugun_tr))
    ekle_gozlem(*_analizsiz_gun(cfg, con, asof))
    ekle_gozlem(*_acik_plan(cfg, con))
    ekle_gozlem(*_cikti_muhru(cfg, con))

    return {
        "asof": asof,
        "bugun_tr": bugun_tr,
        "bulgular": bulgular,
        "kritik": [b for b in bulgular if b[0] == KRITIK],
        "uyari": [b for b in bulgular if b[0] == UYARI],
    }


def _kesit_kontrolleri(cfg: dict, con: sqlite3.Connection
                       ) -> list[tuple[str, str, bool, str]]:
    """Kesit tek yöne mi düştü? — Merdiven'in devre kesicisinin genellenmiş hâli.

    İki AYRI soru, iki ayrı kontrol (L-003: farklı olguları aynı satıra sıkıştırma):

    **9. plan üretim oranı** — bir günde evrenin çoğunda plan çıkıyorsa bozulan
    piyasa değil, seviye/R:R mantığıdır. Ölçüldü (23 asof günü): medyan 2/18,
    gözlemlenen maksimum 9/18 = %50. Tel %60'a konur — yani "bu daha önce hiç
    olmadı" eşiği. Aynı satır, TERS uçtaki tetikleyiciyi de basar: STATE.md
    Backlog'undaki "20 günde ort. <2 plan → ön kayıtlı seviye turu" koşulu.
    Yazılı bir tetikleyici hatırlanmaya bırakılırsa hatırlanmaz (AGENTS.md §12).

    **10. analist sinyal dağılımı** — HF-23 rejim tavanını `plan_sec` SAYISINA
    uyguluyor ama `signal` alanına hiçbir tavan yok. L-008'in "simetriğini ara"
    kuralı tam buraya bakıyor: 18 ismin 15'ine `buy` demek, aracın bozulduğunu
    gösterir ve hiçbir HF kodu bunu yakalamaz.

    Salt-okunur: yalnız `plan_options` ve `predictions` okunur, `build_menu`
    ÇAĞRILMAZ (o yazar; sağlık kontrolü hiçbir şeyi değiştirmez).
    """
    k = cfg["saglik"]["kesit"]
    n_canli = len(universe.live(con)) or 1
    out: list[tuple[str, str, bool, str]] = []

    gunler = db.fetch_all(
        con, "SELECT asof, COUNT(DISTINCT ticker) n FROM plan_options "
             " GROUP BY asof ORDER BY asof DESC LIMIT ?", (int(k["pencere_gun"]),))
    if not gunler:
        out.append((BILGI, "plan üretim oranı", True,
                    "plan_options boş — henüz ölçülecek gün yok"))
    else:
        son = gunler[0]
        oran = son["n"] / n_canli
        ort = sum(g["n"] for g in gunler) / len(gunler)
        tel = float(k["ust_tel_orani"])
        alt = float(k["alt_tetik_ort"])
        # Payda GÖRÜNÜR: kaç gün üzerinden, kaç isimlik evrende (L-007).
        ozet = (f"son gün {son['asof']}: {son['n']}/{n_canli} isim (%{oran*100:.0f}) "
                f"· son {len(gunler)} plan gününde ort. {ort:.2f} isim")
        if oran > tel:
            out.append((UYARI, "plan üretim oranı", False,
                        ozet + f" → **%{tel*100:.0f} telini AŞTI**; gözlemlenen "
                               "maksimum %50'ydi. Kesit tek yöne düştüyse önce "
                               "seviye/R:R mantığından şüphelen"))
        elif len(gunler) >= int(k["pencere_gun"]) and ort < alt:
            out.append((UYARI, "plan üretim oranı", False,
                        ozet + f" → ortalama {alt} altında: STATE.md'deki ön "
                               "kayıtlı seviye turu tetikleyicisi OLUŞTU "
                               "(docs/on-kayit-seviye-02.md)"))
        else:
            out.append((BILGI, "plan üretim oranı", True, ozet))

    son_run = db.fetch_one(
        con, "SELECT p.run_id, p.asof, r.tool, COUNT(*) n,"
             "  SUM(CASE WHEN p.signal IN ('strong_buy','buy','accumulate') "
             "           THEN 1 ELSE 0 END) boga,"
             "  SUM(CASE WHEN p.signal IN ('reduce','sell','avoid') "
             "           THEN 1 ELSE 0 END) ayi "
             "  FROM predictions p JOIN llm_runs r ON r.run_id = p.run_id "
             " GROUP BY p.run_id ORDER BY p.asof DESC, p.run_id DESC LIMIT 1")
    if not son_run or not son_run["n"]:
        out.append((BILGI, "sinyal dağılımı", True, "journal'da tahmin yok"))
    elif son_run["n"] < int(k["sinyal_min_n"]):
        # Payda küçükken oran anlamsızdır ve "temiz" demek de yanıltıcıdır.
        out.append((BILGI, "sinyal dağılımı", True,
                    f"{son_run['asof']} ({son_run['tool']}): n={son_run['n']} "
                    f"< {k['sinyal_min_n']} → oran DEĞERLENDİRİLMEDİ"))
    else:
        tel = float(k["sinyal_ust_tel"])
        pb, pa = son_run["boga"] / son_run["n"], son_run["ayi"] / son_run["n"]
        ozet = (f"{son_run['asof']} ({son_run['tool']}): n={son_run['n']} · "
                f"boğa %{pb*100:.0f} · ayı %{pa*100:.0f}")
        tek_yon = max(pb, pa) > tel
        out.append((UYARI if tek_yon else BILGI, "sinyal dağılımı", not tek_yon,
                    ozet + (f" → **%{tel*100:.0f} telini AŞTI**; 18 ismin çoğuna "
                            "aynı şeyi demek araç şüphesidir" if tek_yon else "")))
    return out


def _yarim_bar(cfg: dict, con: sqlite3.Connection, asof: str | None
               ) -> tuple[str, str, bool, str]:
    """KAPANMAMIŞ seansın barı veritabanında mı? — KAPI kontrolü.

    ⚠ GERÇEK OLAY (2026-07-29, 2026-08-11 denetiminde bulundu): paket TR
    saatiyle 13:29'da, seans SÜRERKEN üretildi. O anki yfinance barı "kapanış"
    diye paketlendi ve 18 tahmin journal'a öyle yazıldı. Gerçek kapanışla
    karşılaştırma: 18/18 ismde sapma, ortalama %1.21, maksimum %2.47
    (AKBNK 64.90 → 63.30). Journal DEĞİŞMEZ olduğu için düzeltilemez.

    `purge_phantom_bars` bunu yakalayamaz: yarım bir seans barının hacmi de
    OHLC'si de gerçektir, sadece EKSİKTİR. Ayrı bir ölçüt gerekiyordu ve
    zaten vardı — `BistCalendar.last_closed_session`, ta Faz 1'den beri.
    Kimse çağırmıyordu.

    KAPI olması meşru çünkü koşunun KENDİSİ düzeltir: `prices.daily` içindeki
    `purge_incomplete_bars` sağlık adımından ÖNCE koşar ve satırı siler.
    Buraya düşmek "ayıklama çalışmadı" demektir — o zaman durmak doğrudur.
    """
    if not asof:
        return BILGI, "yarım bar", True, "veri yok"
    try:
        from .calendar_bist import BistCalendar
        kapali = BistCalendar(cfg, con).last_closed_session().isoformat()
    except Exception:                                       # noqa: BLE001
        return BILGI, "yarım bar", True, "takvim kurulamadı"
    if asof <= kapali:
        return OK, "yarım bar", True, f"son bar {asof} ≤ kapanmış seans {kapali}"
    return (KRITIK, "yarım bar", False,
            f"son bar {asof} · kapanışı KESİNLEŞMİŞ son seans {kapali} → "
            "kapanmamış seansın barı veritabanında. Bu barla üretilen her "
            "gösterge, plan ve tahmin yarım veriye dayanır ve journal "
            "değişmez olduğu için sonradan düzeltilemez "
            "(`bist veri gunluk` ayıklar).")


def _evds_tazelik(cfg: dict, con: sqlite3.Connection) -> tuple[str, str, bool, str]:
    """Makro serilerinden hangisi DONMUŞ? — "değer var" ≠ "değer güncel".

    ⚠ GERÇEK OLAY (2026-08-11 denetimi): TÜFE serisi (`TP.FE.OKTG01`)
    2025-12-01'de durmuştu. `macro.context` en son gözlemi alıyor, tazeliğe
    BAKMIYORDU; sonuç: **Aralık 2025 enflasyonu, Ağustos 2026'nın enflasyonu
    olarak** pakete giriyordu. Üstelik `makro_eksik_pct` 0.0 diyordu — çünkü
    o fonksiyon VARLIĞA bakıyordu, tazeliğe değil. Donmuş bir seri ile taze
    bir seri ayırt edilemiyordu.

    Bu bir UYARI, KRİTİK değil: bayat makro rejim ETİKETİNİ değiştirmiyor
    (`regime._label` yalnız XU100/genişlik kullanır) ve koşuyu durdurmak
    fiyat tarafını da öldürürdü. Ama görünmez kalmamalı.
    """
    from . import macro

    bayat = macro.bayat_seriler(cfg, con)
    if not bayat:
        return OK, "EVDS tazeliği", True, "tüm seriler tolerans içinde"
    ozet = " · ".join(f"{b['ad']} {b['son']} ({b['yas_gun']}g > {b['tolerans']}g)"
                      for b in bayat)
    return (UYARI, "EVDS tazeliği", False,
            f"{len(bayat)} seri donmuş: {ozet} → değerleri pakete GİRMİYOR "
            "(`bist makro gunluk`; seri kodu değişmiş olabilir)")


def _index_tazelik(cfg: dict, con: sqlite3.Connection, asof: str | None
                   ) -> tuple[str, str, bool, str]:
    """Endeks barları hisse barlarıyla aynı günde mi? — KAPI kontrolü.

    ⚠ GERÇEK OLAY (2026-08-15 denetimi): `index_daily` 2026-08-06'da donmuştu,
    `bars_daily` 08-14'teydi. Sebep `prices.sync_indices`'in otonom zincire
    HİÇ bağlı olmamasıydı (L-002'nin üçüncü tekrarı; bkz. `otonom.gunluk`
    adım 2b). Beş işlem günü boyunca `regime_daily`'nin dört girdisinden ÜÇÜ
    bit bit aynı yazıldı ve `alpha_vs_xu100` NULL'a düştü — hiçbir hata,
    hiçbir uyarı. "Veri yok" ile "sorun yok" aynı çıktıya düşüyordu (#009).

    Neden `_evds_tazelik` gibi UYARI değil, KAPI: bayat makro rejim ETİKETİNİ
    değiştirmez (`regime._label` yalnız XU100 + genişlik kullanır) — ama bayat
    ENDEKS tam da o etiketi besler. Yani burada bozulan şey pozisyon boyutu,
    nakit oranı ve maks pozisyon sayısıdır.

    Şiddet kademeli, `bar tazeliği` ile aynı desende: yfinance'in endeks
    tarafında bir seans gecikmesi olağandır, iki seans değildir. Bu tolerans
    adım 2b'yi fiilen "2 seans toleranslı kritik" sınıfına taşır ve L-017
    gereği o devralma orada da yazılıdır — gizli değil.

    Ölçüt `bars_daily`'ye GÖRE, duvar saatine göre değil: hisse barı da
    gelmediyse sorun endekste değildir ve onu `bar tazeliği` raporlar
    (aynı olguyu iki kez KRİTİK basmak L-003'tür).
    """
    sym = cfg["takvim"]["turet_kaynak_endeks"]
    son_ix = db.scalar(con, "SELECT MAX(date) FROM index_daily WHERE symbol = ?",
                       (sym,))
    # ⚠ `tamam=False` + `BILGI`: "endeks yok" ne başarı ne arızadır, bir
    # DURUMDUR (taze kurulum → `bist veri backfill`). `tamam=True` dönmek
    # `ekle`'yi OK'e düşürür ve boş tabloyu "sağlıklı" diye basardı — bu
    # projenin tam olarak yasakladığı şey (#009: "veri yok" ≠ "sorun yok").
    # BİLGİ ne `kritik` ne `uyari` listesine girer; kapı açık kalır.
    if not asof or not son_ix:
        return BILGI, "endeks tazeliği", False, f"{sym} {son_ix or '—'} · bar {asof or '—'}"
    try:
        from .calendar_bist import BistCalendar
        gecikme = BistCalendar(cfg, con).trading_days_between(son_ix, asof)
    except Exception:                                       # noqa: BLE001
        return BILGI, "endeks tazeliği", False, f"{sym} {son_ix} · takvim kurulamadı"
    return (KRITIK if gecikme >= 2 else UYARI, "endeks tazeliği", gecikme <= 0,
            f"{sym} {son_ix} · bar {asof}"
            + ("" if gecikme <= 0 else
               f" → {gecikme} seans geride; rejim girdileri (XU100/SMA200, "
               "volatilite, kur) BAYAT (`bist veri gunluk`)"))


def _atlanan_kosu(cfg: dict, con: sqlite3.Connection, bugun_tr: str
                  ) -> tuple[str, str, bool, str]:
    """Planlı koşu atlandı mı? — GÖZLEM kontrolü (kapıyı KAPATAMAZ).

    ⚠ GERÇEK OLAY (2026-08-06): planlanmış otonom koşu GitHub tarafında
    "The job was not acquired by Runner of type hosted" ile düştü. İş HİÇ
    BAŞLAMADI; `otonom.py` koşmadı, Telegram bildirimi de çıkmadı. O gün
    kullanıcı açısından **tamamen sessizdi.** Bir süreç kendi yokluğunu
    haber veremez.

    ⚠⚠ VE İLK ÇÖZÜM YANLIŞTI (2026-08-11 denetimi, L-016): bu kontrol
    `MAX(predictions.asof)`e bakıyor ve fark ≥2 ise KRİTİK diyordu. O tablo
    kapının ARKASINDA yazılır — kapı bir kez kapanınca sayaç donuyor, fark
    her gün büyüyor ve sistem kendi kendini süresiz kilitliyordu. Yani
    L-015'in kendi cümlesi ("süreç kendi yokluğunu haber veremez") çözümün
    içinde ihlal edilmişti: çözüm yine sürecin İÇİNE konmuştu.

    Şimdi sayaç `otonom_kosu` heartbeat'inden okunuyor. O kayıt koşunun EN
    BAŞINDA yazılır, yani kapı kapansa bile ilerler. Kilit kurulamaz.

    ⚠ `once=bugun_tr`: kontrol koşunun İÇİNDEN çağrıldığında bugünün
    heartbeat'i zaten yazılmıştır. Soru "bugün koştum mu?" değil,
    **"bugüne kadar bir gün atladım mı?"** — o yüzden bugün hariç tutulur.

    ⚠ Bu kontrol yalnız BİR SONRAKİ koşu gerçekleştiğinde konuşabilir. Hiç
    koşu olmayan durumun tek çaresi DIŞARIDAKİ bir nöbetçidir
    (`.github/workflows/nobetci.yml`) — bu kontrol onun yerini TUTMAZ.
    """
    onceki = journal.son_kosu(con, tur="gunluk", once=bugun_tr)
    if not onceki:
        return (BILGI, "atlanan koşu", True,
                "heartbeat boş — henüz kayıtlı önceki koşu yok")
    try:
        from .calendar_bist import BistCalendar
        cal = BistCalendar(cfg, con)
        beklenen = cal.last_closed_session().isoformat()
        fark = cal.trading_days_between(onceki["tarih_tr"], beklenen)
    except Exception:                                       # noqa: BLE001
        return BILGI, "atlanan koşu", True, "takvim kurulamadı"
    ozet = f"önceki koşu {onceki['tarih_tr']} ({onceki['durum']}) · son seans {beklenen}"
    # Normal ritim: her seans akşamı bir koşu → fark 1. 2 ve üstü, aradaki
    # en az bir seansın hiç işlenmediği anlamına gelir.
    if fark <= 1:
        return OK, "atlanan koşu", True, ozet
    return (UYARI, "atlanan koşu", False,
            ozet + f" → arada **{fark - 1} seans** koşusuz. İş hiç başlamazsa "
                   "Telegram bildirimi de ÇIKMAZ (gözlendi 2026-08-06); "
                   "Actions geçmişini kontrol et.")


def _analizsiz_gun(cfg: dict, con: sqlite3.Connection, asof: str | None
                   ) -> tuple[str, str, bool, str]:
    """Koşu var ama ANALİST üretemiyor mu? — GÖZLEM kontrolü.

    "Koştum" ile "iş ürettim" AYRI iki olgudur ve tek satıra sıkıştırılırsa
    (L-003) hangisinin bozuk olduğu görünmez. `_atlanan_kosu` birincisini,
    bu ikincisini sorar.

    ⚠ Şiddet neden KRİTİK değil: `analist` bilerek kritik adım DEĞİL (ADR #013
    — zincir düşse bile deterministik plan geometrisi tek başına değerli).
    Bu kontrolün kapıyı kapatması, o kararı sessizce iptal ederdi: analistin
    iki gün üst üste düşmesi deterministik katmanı da öldürürdü. Tam olarak
    2026-08-06/11 arasında olan buydu.

    ⚠ Fark 1 NORMALDİR: sağlık adımı zincirde analistten ÖNCE (adım 4 vs 6)
    koşar, yani bugünün tahmini henüz yazılmamıştır.
    """
    if not asof:
        return BILGI, "analizsiz gün", True, "veri yok"
    son_analiz = db.scalar(con, "SELECT MAX(asof) FROM predictions")
    if not son_analiz:
        return BILGI, "analizsiz gün", True, "journal boş — henüz analiz yok"
    try:
        from .calendar_bist import BistCalendar
        fark = BistCalendar(cfg, con).trading_days_between(son_analiz, asof)
    except Exception:                                       # noqa: BLE001
        return BILGI, "analizsiz gün", True, "takvim kurulamadı"
    ozet = f"son analiz {son_analiz} · son bar {asof}"
    if fark <= 1:
        return OK, "analizsiz gün", True, ozet
    return (UYARI, "analizsiz gün", False,
            ozet + f" → **{fark} işlem günü analizsiz**. Koşu ayakta ama "
                   "analist halkası üretmiyor olabilir (`bist otonom gunluk` "
                   "çıktısında `analist` adımına bak).")


def _acik_plan(cfg: dict, con: sqlite3.Connection) -> tuple[str, str, bool, str]:
    """Journal'da açık plan var ama portföy BOŞ mu? — GÖZLEM kontrolü.

    ⚠ ÖLÇÜLDÜ (2026-08-11 denetimi): 9 açık `plan_sec` tahmini varken
    `holdings` 0 satırdı. Rapor §0 "Kontenjan: 0/2 pozisyon dolu" basıyordu —
    çünkü kontenjan `holdings`'ten sayılıyor, açık planlardan değil. Sonuç:
    KRDMD 5 gün üst üste seçildi ve planlar harfiyen uygulansa tek isimde
    **%26.9** birikirdi; rejim tavanı ise TOPLAM %20 hisseydi.

    Rapor bu boşluğu zaten yazıyor ("Portföyde kayıtlı pozisyon yok"); eksik
    olan, boşluğun bir SAYIYLA yan yana görünmesiydi.
    """
    acik = db.scalar(
        con, "SELECT COUNT(*) FROM predictions p "
             " LEFT JOIN outcomes o ON o.prediction_id = p.prediction_id "
             " WHERE o.prediction_id IS NULL AND p.action = 'plan_sec'") or 0

    # ⚠ KAYNAK RAPORLA AYNI OLMALI (2026-08-28 denetimi). Burası `holdings`
    # TABLOSUNU sayıyordu; oysa ADR #019 kontenjanı TÜRETİLMİŞ portföye bağladı
    # ve `otonom.gunluk` raporu `pfm.holdings_gorunumu(pf)` ile besliyor.
    # Sonuç: aynı gün rapor "Kontenjan: 2/4 pozisyon dolu" derken `saglik`
    # "0 kayıtlı pozisyon → kontenjan KÖR" diyordu ve bu uyarı 2026-08-17'den
    # beri KESİNTİSİZ basılıyordu (Telegram'daki "4 uyarı"nın içinde).
    #
    # İki kat zarar: (1) README "aynı ad üç gün üst üste çıkıyorsa elini uzat"
    # diyor — bu ad on gündür çıkıyordu ve YANLIŞTI, uyarıların anlamı aşınıyor;
    # (2) önerilen komut (`bist portfoy ekle`) ADR #019 gereği elle kaydı ÜSTÜN
    # sayar, yani uyarıya uyan kullanıcı ölçüm aletini bozardı.
    #
    # L-021/L-022'nin birebir aynısı: tüketici yeni kaynağa bağlandı, GÖZLEMCİ
    # eski kaynakta bırakıldı. Eşliği artık test zorluyor
    # (tests/test_saglik.py::TestAcikPlanKaynagi).
    elle = journal.holdings(con)
    kagit: dict = {}
    try:
        from . import portfoy as pfm
        pf = pfm.simule(cfg, con)
        kagit = pfm.holdings_gorunumu(pf)
    except Exception as e:                                   # noqa: BLE001
        # Portföy türetilemezse GÖZLEM susmaz ama yanlış da konuşmaz.
        return (UYARI, "açık plan", False,
                f"{acik} açık plan · portföy türetilemedi ({e}) — kontenjan "
                f"doğrulanamıyor")
    tutulan = len({**kagit, **elle})

    ozet = (f"{acik} açık plan · {tutulan} pozisyon "
            f"({len(kagit)} kâğıt · {len(elle)} elle)")
    if acik == 0 or tutulan > 0:
        return OK, "açık plan", True, ozet
    return (UYARI, "açık plan", False,
            ozet + " → kontenjan ve 'azalt' bölümü portföye dayanır; portföy "
                   "boşken ikisi de kör kalır (`bist portfoy ekle ...`).")


def _cikti_muhru(cfg: dict, con: sqlite3.Connection) -> tuple[str, str, bool, str]:
    """Journal'ın gösterdiği analist çıktısı hâlâ AYNI dosya mı? — GÖZLEM.

    ⚠ GERÇEK OLAY (2026-08-11 denetimi): `llm_runs.output_path` "bu tahmini
    üreten çıktı şu dosyadadır" diyor. 2026-07-30 için doğru DEĞİLDİ —
    journal `gemini-3.6-flash` diyordu, dosyanın içi `gemini-3.5-flash`'tı ve
    TUPRS'ta hem sinyal hem seçilen plan farklıydı. Sebep: yol yalnız TARİHE
    bağlıydı, aynı günün ikinci turu dosyayı sessizce eziyordu.

    Mühürsüz (v11 öncesi) kayıtlar ayrı sayılır ve "doğru" DEĞİL
    "doğrulanamaz" diye raporlanır — geçmişe dönük sha yazmak, ezilmiş bir
    dosyayı doğruymuş gibi mühürlemek olurdu.
    """
    kayitlar = db.fetch_all(
        con, "SELECT run_id, output_path, output_sha FROM llm_runs "
             " WHERE output_path IS NOT NULL AND output_path != ''")
    if not kayitlar:
        return BILGI, "çıktı mührü", True, "kayıt yok"
    muhursuz = [r for r in kayitlar if not r["output_sha"]]
    bozuk, kayip = [], []
    for r in kayitlar:
        if not r["output_sha"]:
            continue
        icerik = util.read_json(util.resolve(r["output_path"]))
        if icerik is None:
            kayip.append(r["run_id"])
        elif util.sha256_canonical(icerik) != r["output_sha"]:
            bozuk.append(r["run_id"])
    ozet = (f"{len(kayitlar) - len(muhursuz)}/{len(kayitlar)} kayıt mühürlü"
            + (f" · {len(muhursuz)} mühürsüz (doğrulanamaz)" if muhursuz else ""))
    if not bozuk and not kayip:
        return (OK if not muhursuz else BILGI), "çıktı mührü", True, ozet
    return (UYARI, "çıktı mührü", False,
            ozet + (f" · **mühür tutmuyor**: {', '.join(bozuk)}" if bozuk else "")
            + (f" · dosya yok: {', '.join(kayip)}" if kayip else ""))


def duzeltilmemis_kurumsal_tara(cfg: dict, con: sqlite3.Connection) -> list[dict]:
    """TÜM GEÇMİŞTE düzeltilmemiş bedelsiz/bölünme şüphesi taşıyan barlar.

    Neden `data_quality`'ye güvenilmez: o yalnız SON 252 BARA bakar ve CCOLA'yı
    görünmez kılan tam olarak buydu. 2024-08-01'deki −%90.7'lik bar bugün
    pencerenin dışında kalıyor, `unexplained_jump=0` yazıyor ve tablo "temiz"
    diyor — oysa bar hâlâ orada ve backtest paneli hâlâ onu okuyor.

    Bu yüzden burası **pencerelenmez.** Bulgu, düzeltilene ya da bilinçli
    olarak kabul edilene kadar HER GÜN görünür. (AGENTS.md §11: düzeltilemeyen
    bulgu sessizce bırakılmaz, ifşa edilir.)
    """
    esik = float(cfg["evren"]["duzeltilmemis_kurumsal_pct"]) / 100.0
    rows = db.fetch_all(
        con,
        "SELECT ticker, date, getiri, in_live, in_measure FROM ("
        "  SELECT b.ticker, b.date,"
        "         b.c / LAG(b.c) OVER (PARTITION BY b.ticker ORDER BY b.date) - 1 getiri,"
        "         u.in_live, u.in_measure"
        "    FROM bars_daily b LEFT JOIN universe u ON u.ticker = b.ticker"
        ") WHERE getiri IS NOT NULL AND ABS(getiri) > ? ORDER BY ABS(getiri) DESC",
        (esik,))
    return [{**r, "getiri_pct": round(r["getiri"] * 100, 1)} for r in rows]


def _duzeltilmemis_kurumsal(cfg: dict, con: sqlite3.Connection
                            ) -> tuple[str, str, bool, str]:
    esik = cfg["evren"]["duzeltilmemis_kurumsal_pct"]
    try:
        bulgular = duzeltilmemis_kurumsal_tara(cfg, con)
    except sqlite3.OperationalError as e:              # pencere fonksiyonu yoksa
        return BILGI, "düzeltilmemiş kurumsal", True, f"taranamadı: {e}"
    if not bulgular:
        return OK, "düzeltilmemiş kurumsal", True, f"|getiri|>%{esik:.0f} bar yok"
    canli = [b for b in bulgular if b["in_live"]]
    # ŞİDDET, ETKİLENEN HATTA GÖRE: canlı evrende bir bar varsa günlük kararı
    # doğrudan besliyor demektir (KRİTİK); yalnız ölçüm evrenindeyse geçmişe
    # dönük bir kalibrasyon sorunudur (UYARI) — ikisi aynı şey değil (L-003).
    ilk = "; ".join(f"{b['ticker']} {b['date']} {b['getiri_pct']:+.1f}%"
                    for b in bulgular[:4])
    return ((KRITIK if canli else UYARI), "düzeltilmemiş kurumsal", False,
            f"{len(bulgular)} bar (|getiri|>%{esik:.0f}) · "
            f"canlı evrende {len(canli)} · ölçüm evreninde "
            f"{sum(1 for b in bulgular if b['in_measure'])} → {ilk}"
            + ("" if len(bulgular) <= 4 else f" … (+{len(bulgular)-4})"))


def cikis_kodu(sonuc: dict) -> int:
    """0 temiz · 1 uyarı · 2 KRİTİK. Otomasyonun kapısı bu sayıdır."""
    if sonuc["kritik"]:
        return 2
    return 1 if sonuc["uyari"] else 0


def bicimle(sonuc: dict) -> str:
    L = [f"Sağlık kontrolü — {sonuc['asof']}", ""]
    for seviye, ad, mesaj in sonuc["bulgular"]:
        L.append(f"  {ISARET[seviye]} {ad:22} {mesaj}")
    L.append("")
    if sonuc["kritik"]:
        L.append(f"🛑 {len(sonuc['kritik'])} KRİTİK kontrol düştü — "
                 f"sessiz yanlış sonuç riski var.")
    elif sonuc["uyari"]:
        L.append(f"⚠ {len(sonuc['uyari'])} uyarı.")
    else:
        L.append("✅ Tüm kontroller temiz.")
    return "\n".join(L)


TEK_SATIR_AD_LIMITI = 3


def tek_satir(sonuc: dict) -> str:
    """Telegram özetine giren tek satırlık hâl.

    ⚠ Uyarı dalı eskiden yalnız SAYI basıyordu ("⚠ Sağlık: 5 uyarı"). Kritik
    dalı adı da mesajı da veriyordu; uyarı dalı vermiyordu. Bu asimetri
    telefonda eylem üretmeyen bir bilgi bırakıyordu: beş uyarının hangileri
    olduğunu görmek için repoya gitmek gerekiyordu. Adlar artık ŞİDDET
    sırasına göre, eşitlikte ad sırasına göre basılır — sıra deterministik
    olmalı, yoksa aynı sağlık durumu her koşuda farklı bir metin üretir.
    """
    if sonuc["kritik"]:
        return "🛑 Sağlık: " + "; ".join(f"{ad} ({mesaj})"
                                        for _, ad, mesaj in sonuc["kritik"])
    uyarilar = sonuc["uyari"]
    if uyarilar:
        adlar = sorted(ad for _, ad, _ in uyarilar)
        gosterilen = adlar[:TEK_SATIR_AD_LIMITI]
        kalan = len(adlar) - len(gosterilen)
        return (f"⚠ Sağlık: {len(adlar)} uyarı — " + ", ".join(gosterilen)
                + (f" …+{kalan}" if kalan else ""))
    return "✓ Sağlık temiz"
