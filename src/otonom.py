"""Otonom koşu — GitHub Actions'ın çağırdığı tek giriş noktası (Faz 8).

Elle koşulan zincirin (`veri gunluk → gosterge → haber cek → saglik → gunluk →
denetle → kaydet → coz → rapor`) tek komuta indirilmiş hâli.

**HATA FELSEFESİ** (`gold_tracking_system/src/daily_job.py`'den):
Her adım kendi `try/except`'i içinde koşar ve hiçbir adım diğerini KESMEZ —
`gunluk()` istisna fırlatmaz. Sebep: haber katmanı çökse bile rapor üretilmeli,
analist zinciri düşse bile deterministik plan geometrisi elde kalmalı.

Ama gold'da bunun bir bedeli yaşandı ve buraya ders olarak geçti: altı adımın
hepsi istisnayı yutunca iş HER ZAMAN yeşil bitiyordu ve `logs/` gitignore'da
olduğu için bir modül günlerce bozuk kalmıştı (ADR #004, L-002). Bu yüzden
yutmak yetmez, SINIFLANDIRMAK gerekir:

    KRITIK_ADIMLAR düşerse → çıkış kodu 1 → Actions kırmızı → Telegram'a hata
    diğerleri düşerse      → çıkış 0, ama rapor "eksik" olduğunu SÖYLER

`analist` bilerek kritik DEĞİL: zincirin tamamı düşse bile o gün üretilen plan
geometrisi ve risk çerçevesi tek başına değerlidir ve rapor "analist çıktısı
yok" ibaresini zaten basar (ADR #013).

**Sağlık kapısı GERÇEK bir kapıdır:** `bist saglik` KRİTİK dönerse sonraki
adımlar HİÇ koşmaz. Bayat göstergeyle üretilen paket boş ama şeklen geçerli
olur (L-009) — ve o paketi analiz etmek, sistemin en pahalı hata sınıfıdır.

⚠⚠ AMA KAPI YALNIZ VERİYE BAKAR — bu ayrım bir kilitlenmeden doğdu (L-016).
2026-08-07'de eklenen "atlanan koşu" kontrolü `MAX(predictions.asof)`e bakıp
KRİTİK dönüyordu. `predictions` ise bu dosyanın 6. adımında, yani KAPININ
ARKASINDA yazılır. 2026-08-06'da GitHub runner işi almayınca fark 2 oldu,
kapı kapandı ve bir daha açılamadı: açılması için gereken tahmin kapının
arkasındaydı. Sistem dört işlem günü boyunca veri çekti, commit attı, sıfır
analiz üretti — ve her gün aynı 🛑 mesajını gönderdi.

Kural: **kapıyı yalnız KOŞUNUN KENDİSİNİN düzeltebileceği şeyler kapatır.**
Sistemin kendi geçmişine bakan kontroller UYARI seviyesinde tavanlanır
(`saglik.ekle_gozlem`). Koşunun varlığı artık `otonom_kosu` heartbeat'ine
yazılır ve o kayıt kapının ÖNÜNDE, adımlar başlamadan önce atılır.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime, timedelta

from . import db, journal, report, saglik as sag, telegram_bist as tg, util

log = logging.getLogger(__name__)

# Bu adımlardan biri düşerse koşu BAŞARISIZ sayılır (çıkış 1).
# `analist`, `haber` ve `makro` listede YOK: üçü de düşse rapor hâlâ anlamlıdır.
KRITIK_ADIMLAR = ("veri", "gosterge", "saglik", "rapor")


def _hata(sonuc: dict, adim: str, e: Exception) -> None:
    log.warning("%s hata: %s", adim, e)
    sonuc.setdefault("hatalar", {})[adim] = str(e)[:500]


def _say(x, ond: int = 2, birim: str = "") -> str:
    """Eksik değer `—` basar; `0.0` ile `None`u ASLA aynı göstermez."""
    if x is None:
        return "—"
    try:
        return f"{float(x):.{ond}f}{birim}"
    except (TypeError, ValueError):
        return str(x)


def basarisiz_mi(sonuc: dict) -> list[str]:
    return [a for a in KRITIK_ADIMLAR if a in sonuc.get("hatalar", {})]


# ---------------------------------------------------------------- günlük
def gunluk(cfg: dict, con: sqlite3.Connection, *, bugun: date | None = None,
           analist_calistir: bool = True) -> dict:
    """Tam günlük koşu. İstisna FIRLATMAZ; sonucu sözlük olarak döner."""
    from .calendar_bist import BistCalendar

    sonuc: dict = {"adimlar": {}}
    cal = BistCalendar(cfg, con)
    # ⚠⚠ KOŞUNUN GÜNÜ = ANALİZ ETTİĞİ SEANS, duvar saati DEĞİL (L-026).
    #
    # Eskiden `bugun_tr()` okunuyordu — yani "iş hangi TR takvim gününde
    # BAŞLADI". GitHub cron gecikince (bu repoda ölçüldü: 8,5 saat) etiket
    # kaydı ve üç ayrı arıza üretti:
    #
    #   * 2026-08-27 ve 2026-08-31 slotları gece yarısını aştı; heartbeat
    #     ertesi günün etiketiyle yazıldı. O iki gün için `otonom_kosu`da
    #     KAYIT YOK, 2026-09-01'de ise İKİ kayıt var. "Hangi gün koştum?"
    #     sorusunun cevabı journal'dan okunamaz hale geldi.
    #   * 2026-08-28 (Cuma) slotu 08-29T00:39Z'de koştu; etiket Cumartesi
    #     oldu, takvim kapısı "işlem günü değil" deyip koşuyu ATLADI ve
    #     Cuma seansı hiç analiz edilmedi. Gecikme, işin TAMAMINI yedi.
    #   * Gözcü de aynı etikete baktığı için yanlış alarm verdi (bkz. `nobetci`).
    #
    # `last_closed_session()` takvimden gelir: gecikme onu kaydıramaz. Üstelik
    # `asof`un zaten kullandığı çıpa budur — koşunun KİMLİĞİ ile ÜRÜNÜ artık
    # aynı günü gösteriyor. Cumartesiye taşan Cuma koşusu Cuma'yı analiz eder.
    gun = bugun or cal.last_closed_session()

    # ⚠⚠ 0) HEARTBEAT — HER ŞEYDEN ÖNCE, takvim kapısından bile önce.
    #
    # Bu satırın yeri tesadüf değil, kilidin çözümü. "Koşu atlandı mı?" sorusu
    # koşunun ÜRÜNÜNE (tahminlere) bakarak cevaplanırsa, ürünü engelleyen her
    # kapı gözlemcinin de gözünü kapatır — ve gözlemci kapıyı kapatabiliyorsa
    # kilit kalıcı olur. 2026-08-06/11 arasında tam olarak bu yaşandı.
    #
    # Buradan sonra ne olursa olsun (kapı kapansın, süreç çöksün, tatil
    # yüzünden atlansın) kayıt DURUR: "koştum" ile "iş ürettim" ayrı iki olgu.
    kosu_id = None
    try:
        kosu_id = journal.kosu_basla(cfg, con, tur="gunluk",
                                     tarih_tr=gun.isoformat())
        sonuc["kosu_id"] = kosu_id
    except Exception as e:                                  # noqa: BLE001
        # Heartbeat yazılamazsa koşu YİNE DE devam eder: gözlem katmanının
        # arızası, iş katmanını durdurmak için bir sebep değildir.
        log.warning("heartbeat yazılamadı: %s", e)

    # 1) Takvim kapısı. Cron hafta içi TATİLLERİ bilmez; bilseydi bile tatil
    # günü koşmak yeni bar olmadığı için `saglik`i boş yere KRİTİK yapardı.
    if not cal.is_trading_day(gun):
        sonuc["atlandi"] = f"{gun.isoformat()} işlem günü değil"
        log.info(sonuc["atlandi"])
        _kosu_bitir(con, kosu_id, sonuc, "atlandi")
        return sonuc

    # 2) Fiyat verisi (+ yarım bar ayıklaması + kalite kapısı otomatik koşar)
    try:
        from . import prices
        r = prices.daily(cfg, con)
        sonuc["adimlar"]["veri"] = (
            f"{r['tickers']} hisse · {r['hayalet_silinen']} hayalet + "
            f"{r['yarim_bar_silinen']} yarım bar ayıklandı "
            f"· kalite {r['kalite_gecmeyen']} isim geçemedi")
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "veri", e)

    # 2b) ENDEKS ve KUR — kritik DEĞİL, ama sağlık onu 2 seans TOLERANSLA izler.
    #
    # ⚠ BU ADIM 2026-08-16'ya KADAR ZİNCİRDE YOKTU ve bu L-002'nin ÜÇÜNCÜ
    # tekrarıydı: `history_daily` (07-24), `macro.daily` (08-11), şimdi
    # `index_daily`. `prices.daily` yalnız HİSSE barlarını çeker; endeksi
    # çeken `sync_indices`'in tek çağrı yeri `cli.cmd_veri` idi — yani
    # endeks ancak Mert elle `bist veri gunluk` koştuğunda tazeleniyordu.
    #
    # ÖLÇÜLDÜ (2026-08-15 denetimi): `index_daily` 2026-08-06'da donmuştu,
    # `bars_daily` 08-14'teydi. Beş işlem günü boyunca `regime_daily`'nin
    # dört girdisinden ÜÇÜ (xu100_vs_sma200, xu100_vol_21, usdtry_vol_21)
    # bit bit aynı yazıldı ve `alpha_vs_xu100` hesaplanamaz oldu
    # (`2026-08-05-KRDMD-1` outcome'unda NULL). Hiçbir hata fırlamadı.
    #
    # Neden KRİTİK_ADIMLAR'da değil: tek koşuluk bir yfinance arızası fiyat
    # tarafını da öldürmemeli. Ama boşluk BİRİKİRSE rejim girdisi bayatlar —
    # o yüzden `saglik._index_tazelik` bir KAPI kontrolüdür ve 2 seanstan
    # sonra koşuyu durdurur. Yani bu adım fiilen "2 seans toleranslı kritik"
    # sınıfındadır; L-017 gereği bu devralma GİZLENMEZ, burada yazılıdır.
    try:
        from . import prices
        # Pencere ~400 gün: SMA200 için gereken geçmiş zaten DB'de; buradaki iş
        # yalnız yeni barları eklemek ve geriye dönük düzeltmeleri yakalamak.
        # Referans `gun` — koşunun İstanbul TAKVİM günü, `date.today()` değil
        # (AGENTS §11/6: zaman kaynağı açık ve enjekte edilebilir olmalı).
        # `replace(year=...)` bilerek kullanılmadı: 29 Şubat'ta ValueError atar.
        r = prices.sync_indices(cfg, con,
                                start=(gun - timedelta(days=400)).isoformat())
        sonuc["adimlar"]["endeks"] = " · ".join(f"{ad} {n}" for ad, n in sorted(r.items()))
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "endeks", e)

    # 3) Göstergeler — L-009'UN KALICI ÇÖZÜMÜ.
    # Bu adım akışın İÇİNDE olduğu için artık unutulamaz. Elle koşulan sırada
    # yoktu ve README'de de geçmiyordu; sonuç: 0 skorlanan isim, 0 plan, rejim
    # paydası 0 olan "geçerli görünen" boş bir paket. Sıfır hata koduyla.
    try:
        from . import indicators
        r = indicators.compute_and_store(cfg, con)
        sonuc["adimlar"]["gosterge"] = (
            f"{sum(r['satir'].values()):,} satır / {r['tickers']} ticker".replace(",", "."))
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "gosterge", e)

    # 4) Makro (TCMB EVDS) — kritik DEĞİL.
    #
    # ⚠ BU ADIM 2026-08-11'e KADAR ZİNCİRDE YOKTU. `macro.daily`nin tek çağrı
    # yeri `cli.cmd_makro` idi, yani EVDS verisi ancak Mert elle koştuğunda
    # tazeleniyordu. Sonuç LESSONS L-002'nin bir kez daha tekrarı: bağlı
    # olmayan tablo donar ve hiçbir hata fırlatmaz. TÜFE serisi 2025-12-01'de
    # durmuştu ve Aralık 2025 enflasyonu Ağustos 2026'nın enflasyonu olarak
    # pakete giriyordu. Artık hem çekiliyor hem tazeliği `saglik`te ölçülüyor.
    try:
        from . import macro
        r = macro.daily(cfg, con)
        sonuc["adimlar"]["makro"] = f"{sum(r.values())} satır / {len(r)} seri"
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "makro", e)

    # 5) Haber (KAP) — kritik DEĞİL; düşerse pakette `haber_taramasi.ok=False`
    # olur ve analist "haber yok" ile "bakılmadı"yı ayırt edebilir.
    try:
        from . import news
        r = news.sync(cfg, con)
        sonuc["adimlar"]["haber"] = f"{r.get('yazilan', 0)} bildirim"
        if r.get("atlanan_aralik"):
            sonuc.setdefault("uyarilar", []).append(
                f"KAP atlanan aralık: {r['atlanan_aralik']}")
        # İleriye dönük takvim AYNI adımda — L-002: otomatik boru hattına
        # bağlı olmayan tablo donar ve bayat takvim `bilinmiyor`u kalıcı hale
        # getirir. Ayrı bir `try` çünkü uç ayrı: biri düşerse diğeri koşsun.
        try:
            bb = news.sync_beklenen(cfg, con)
            sonuc["adimlar"]["beklenen_bildirim"] = (
                f"{bb.get('yazilan', 0)} satır / {bb.get('ticker', 0)} ticker"
                if bb["ok"] else f"BAŞARISIZ: {bb.get('not')}")
            if not bb["ok"]:
                sonuc.setdefault("uyarilar", []).append(
                    f"beklenen bildirim takvimi: {bb.get('not')}")
        except Exception as e:                              # noqa: BLE001
            _hata(sonuc, "beklenen_bildirim", e)
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "haber", e)

    # 6) SAĞLIK KAPISI — buradan sonrası veriye güvenir.
    #
    # ⚠ Kapıyı YALNIZ veri bütünlüğü kontrolleri kapatabilir. Sistemin kendi
    # geçmişine bakan kontroller (`saglik.GOZLEM_KONTROLLERI`) yapısal olarak
    # UYARI'da tavanlanır ve buraya HİÇ düşemez — sebebi modül docstring'inde.
    try:
        s = sag.kontrol(cfg, con)
        sonuc["saglik"] = s
        sonuc["adimlar"]["saglik"] = sag.tek_satir(s)
        if s["kritik"]:
            # Kapı KAPALI: paket üretme, analiz etme, rapor yazma.
            _hata(sonuc, "saglik",
                  RuntimeError("KRİTİK: " + "; ".join(f"{ad} ({m})"
                                                      for _, ad, m in s["kritik"])))
            _bildir_hata(cfg, sonuc, gun)
            _kosu_bitir(con, kosu_id, sonuc, "durduruldu")
            return sonuc
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "saglik", e)
        _bildir_hata(cfg, sonuc, gun)
        _kosu_bitir(con, kosu_id, sonuc, "durduruldu")
        return sonuc

    asof = db.scalar(con, "SELECT MAX(date) FROM bars_daily")
    sonuc["asof"] = asof

    # 7) LLM paketi
    try:
        from . import llm_io
        bundle = llm_io.build_bundle(cfg, con, asof)
        llm_io.write_bundle(cfg, bundle)
        planli = sum(1 for e in bundle["evren"] if e["plan_menusu"])
        sonuc["adimlar"]["paket"] = f"{len(bundle['evren'])} hisse · {planli} planlı"
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "paket", e)
        bundle = None

    # 8) Analist zinciri — KRİTİK DEĞİL (docstring'deki gerekçe)
    #
    # ⚠ KAPI: bu gün ZATEN analiz edildiyse analist YENİDEN KOŞMAZ.
    # YAŞANDI (2026-08-28 denetimi): 08-27'nin planlı koşusu GitHub'da hiç
    # görünmedi; sonraki koşu 08-28T01:05Z'de başladı ve o an `bars_daily` max
    # hâlâ 2026-08-26 idi. `asof = MAX(bars_daily.date)` olduğu için zincir
    # ZATEN ANALİZ EDİLMİŞ bir günü yeniden analiz etti. `create_run` sessizce
    # `-2` sonekiyle ikinci bir koşu açtı ve journal aynı `asof` için iki karar
    # seti taşımaya başladı — üstelik ikisi birbirinden ÇOK farklı:
    # 18 ismin 12'sinde karar değişti (birinci koşu 0 plan seçti, ikincisi 2
    # pozisyon açtı). Değişmezlik ürünün kendisidir (ADR #014); "3 ay önce
    # sistem ne diyordu?" sorusu iki cevaplı hale geldi.
    #
    # NEDEN DURDURMA DEĞİL ATLAMA (AGENTS §12a): bu bir GÖZLEM'dir, kapı değil —
    # "bu bulguyu bu koşunun KENDİSİ düzeltebilir mi?" sorusunun cevabı hayır.
    # O yüzden zincir DURMAZ: veri/gösterge/çözüm/rapor adımları koşmaya devam
    # eder (hepsi idempotent). Kilitlenemez de: `asof` veriyle ilerler ve veri
    # adımı bundan ÖNCE koşar — yeni bar gelince analist kendiliğinden döner.
    # Bar akmıyorsa onu zaten `saglik`in "bar tazeliği" ve "atlanan koşu"
    # kontrolleri bağırır; bu kapı onların işini üstlenmez.
    if analist_calistir and bundle is not None:
        onceki = db.scalar(
            con, "SELECT COUNT(*) FROM predictions WHERE asof = ?", (asof,)) or 0
        if onceki:
            sonuc["analist_atlandi"] = "zaten_analiz_edildi"
            sonuc["adimlar"]["analist"] = (
                f"ATLANDI — {asof} zaten analiz edilmiş ({onceki} tahmin). "
                f"Journal değişmezdir; aynı gün ikinci kez analiz edilmez.")
            log.info("analist atlandı: %s zaten analiz edilmiş (%d tahmin)",
                     asof, onceki)
        else:
            try:
                from . import analist
                r = analist.calistir(cfg, con, asof)
                sonuc["analist_model"] = r["model"]
                sonuc["adimlar"]["analist"] = \
                    f"{r['model']} ({len(r['denemeler'])} deneme)"
                _kaydet(cfg, con, asof, bundle, r["out"], sonuc)
            except Exception as e:                          # noqa: BLE001
                _hata(sonuc, "analist", e)

    # 9) Çözüm — rapordan ÖNCE. Gold dersi: bugün kapanan tahminler o günün
    # raporundaki karneye girmeli, bir gün gecikmeli değil.
    try:
        from . import resolver
        r = resolver.resolve_open(cfg, con)
        sonuc["cozulen_n"] = r["cozulen"]
        sonuc["cozulen_dagilim"] = r["dagilim"]
        # ⚠ İZLENECEK SAYI `cozulebilir_acik`. Eski satır `hala_acik` basıyordu
        # ve o, planı olmayan karar kayıtlarını da içerdiği için her seans 18
        # artıyordu (337'ye ulaşmıştı); gerçek açık plan 17'ydi ve aynı gün
        # `saglik` onu doğru basıyordu. Bir mertebe fark, gerçek sinyali
        # gizliyordu (bkz. `resolver.resolve_open`).
        sonuc["adimlar"]["coz"] = (
            f"{r['cozulen']} çözüldü · {r.get('cozulebilir_acik', 0)} açık plan"
            f" · {r.get('karar_kaydi', 0)} karar kaydı")
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "coz", e)

    # 10) Rapor + Telegram (gold deseni: TG gönderimi rapor adımının İÇİNDE —
    # bildirimin sessizce kaybolması, bildirimin kendisinden tehlikelidir)
    try:
        b = bundle if bundle is not None else util.read_json(
            f"{cfg['paths']['llm_in_dir']}/{asof}/bundle.json")
        if b is None:
            raise RuntimeError(f"paket yok: llm/in/{asof}/bundle.json")
        analiz = db.fetch_all(
            con, "SELECT * FROM predictions WHERE asof = ? ORDER BY ticker", (asof,))
        # KÂĞIT PORTFÖY (ADR #019). Kontenjan artık KÖR DEĞİL: `holdings`
        # boşken "0/2 dolu" diyen satır, sistemin kendi açık pozisyonlarını
        # saymaya başladı. Elle girilen kayıt ÜSTÜN — Mert gerçek bir pozisyon
        # girdiyse o gerçektir ve simülasyon onu ezemez.
        try:
            from . import portfoy as pfm
            pf = pfm.simule(cfg, con, asof=asof)
            sonuc["adimlar"]["portfoy"] = pfm.ozet_satiri(pf)
        except Exception as e:                              # noqa: BLE001
            _hata(sonuc, "portfoy", e)
            pf = None
        elle = journal.holdings(con)
        tutulan = {**(pfm.holdings_gorunumu(pf) if pf else {}), **elle}
        acik_plan = len([p for p in journal.open_predictions(con)
                         if p["action"] == "plan_sec"])
        metin = report.daily_report(cfg, b, holdings=tutulan, analiz=analiz,
                                    acik_plan=acik_plan, portfoy=pf)
        sonuc["rapor"] = report.write(cfg, f"gunluk_{asof}.md", metin)

        ozet = report.telegram_ozet(
            cfg, b, analiz=analiz, holdings=tutulan,
            cozulen=[{"resolution": k} for k, v in
                     (sonuc.get("cozulen_dagilim") or {}).items() for _ in range(v)],
            analist_model=sonuc.get("analist_model"),
            saglik=sag.tek_satir(sonuc["saglik"]) if sonuc.get("saglik") else None,
            portfoy=pf)
        if sonuc.get("hatalar"):
            ozet += "\n\n⚠ Düşen adım: " + ", ".join(sorted(sonuc["hatalar"]))
        import os
        if os.environ.get('ADVISOR_V2') != '1':
            tg.bildir(cfg, ozet)
        elif sonuc.get('hatalar'):
            tg.bildir(cfg, '⚠ BIST veri hattı: ' + ', '.join(sorted(sonuc['hatalar'])) + '. Ayrıntı günlük arşivde.')
        sonuc["adimlar"]["rapor"] = sonuc["rapor"]
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "rapor", e)

    _kosu_bitir(con, kosu_id, sonuc,
                "durduruldu" if basarisiz_mi(sonuc) else "tamam")
    return sonuc


def _kosu_bitir(con: sqlite3.Connection, kosu_id: str | None, sonuc: dict,
                durum: str) -> None:
    """Heartbeat'i kapatır. Her çıkış yolunda çağrılır.

    Çağrılamadığı durum da bilgi taşır: `durum='kosuyor'` kalan bir kayıt,
    sürecin bitmeden öldüğü (OOM, timeout, runner iptali) anlamına gelir ve
    nöbetçi bunu görür.
    """
    if not kosu_id:
        return
    try:
        journal.kosu_bitir(con, kosu_id, durum=durum, asof=sonuc.get("asof"),
                           adimlar=sonuc.get("adimlar"),
                           hatalar=sonuc.get("hatalar"))
    except Exception as e:                                  # noqa: BLE001
        log.warning("heartbeat kapatılamadı: %s", e)


def _kaydet(cfg: dict, con: sqlite3.Connection, asof: str, bundle: dict,
            out: dict, sonuc: dict) -> None:
    """Denetimden geçmiş analist çıktısını journal'a yazar.

    `cli.cmd_kaydet` ile aynı iş; buraya kopyalanmasının sebebi katman
    disiplini (hiçbir modül `cli`'ı import edemez). Denetim BURADA tekrar
    koşmaz: `analist.calistir` yalnız sert hatasız çıktı döndürür — iki kez
    denetlemek, denetimin nerede yapıldığı sorusunu bulanıklaştırır.
    """
    from . import planner

    menu = planner.build_menu(cfg, con, asof)
    for opts in menu["menu"].values():
        planner.store(cfg, con, opts)

    from . import llm_io
    run_id = journal.create_run(cfg, con, asof=asof, tool=out.get("tool", "diger"),
                                bundle_sha=bundle["bundle_sha"])
    # ⚠ Çıktı MÜHÜRLENİR ve run'a özel bir dosyaya kopyalanır. `analysis.json`
    # yolu yalnız tarihe bağlıydı ve aynı günün ikinci turu onu journal'a haber
    # vermeden eziyordu (2026-07-30'da yaşandı: kayıt `gemini-3.6-flash`,
    # dosya `gemini-3.5-flash`, TUPRS'ta hem sinyal hem plan farklı).
    m = journal.muhurle_cikti(cfg, con, run_id=run_id, asof=asof)
    if not m["ok"]:
        log.warning("çıktı mühürlenemedi (%s): %s", run_id, m.get("not"))
    # GİRDİ de mühürlenir — L-018'in simetriği (bkz. `journal.muhurle_girdi`).
    g = journal.muhurle_girdi(cfg, run_id=run_id, asof=asof, bundle=bundle)
    if not g["ok"]:
        log.warning("girdi mühürlenemedi (%s): %s", run_id, g.get("not"))
    plan_map = {p["plan_id"]: p
                for ps in planner.load_for_date(cfg, con, asof).values() for p in ps}
    ev = {e["ticker"]: e for e in bundle["evren"]}
    n = 0
    for st in out["stocks"]:
        t = st["ticker"]
        plan = plan_map.get(st.get("selected_plan_id")) or {}
        analist_alanlari = {k: v for k, v in st.items()
                            if k in journal.ANALIST_ALANLARI}
        journal.record(cfg, con, run_id=run_id, asof=asof, ticker=t,
                       analist=analist_alanlari, plan=plan,
                       faktor=llm_io.faktor_to_journal(ev[t].get("faktorler")),
                       regime=bundle["rejim"]["etiket"],
                       referans={"close": ev[t]["fiyat"]["kapanis"],
                                 "atr14": ev[t]["gostergeler"].get("atr14")})
        n += 1
    sonuc["kaydedilen"] = n
    sonuc["run_id"] = run_id


def _bildir_hata(cfg: dict, sonuc: dict, gun: date) -> None:
    """Sağlık kapısı kapandığında tek satırlık alarm.

    Bu bildirim try/except içinde: Telegram da çökmüş olabilir ve o durumda
    asıl hatanın (sağlık) üstünü örtmemeli.
    """
    try:
        mesaj = (f"🛑 BIST otonom — {gun.isoformat()}\n"
                 f"Koşu DURDURULDU.\n"
                 + "\n".join(f"· {a}: {m}" for a, m in
                             sorted(sonuc.get("hatalar", {}).items())))
        tg.bildir(cfg, mesaj)
    except Exception as e:                                  # noqa: BLE001
        log.warning("hata bildirimi gönderilemedi: %s", e)


# ---------------------------------------------------------------- haftalık
def haftalik(cfg: dict, con: sqlite3.Connection) -> dict:
    """Haftalık değerlendirme özeti — araç BAŞINA ayrı ölçüm.

    Araçları karıştırmamak bu projede sert bir kural (`evaluate.kaynak_sec`):
    `replay` VEKİL bir analisttir ve alfası gerçek LLM kayıtlarıyla aynı potaya
    girmez. Burada da her araç ayrı ayrı ölçülür — hangi modelin daha iyi
    analist olduğu sorusu böylece kanaatle değil VERİYLE cevaplanır (ADR #013).
    """
    from . import evaluate

    sonuc: dict = {"adimlar": {}}
    bugun = util.bugun_tr(cfg["takvim"]["timezone"])
    kosu_id = None
    try:
        kosu_id = journal.kosu_basla(cfg, con, tur="haftalik", tarih_tr=bugun)
    except Exception as e:                                  # noqa: BLE001
        log.warning("heartbeat yazılamadı: %s", e)

    L = [f"📈 BIST haftalık — {report.bugun()}", ""]

    # ⚠ "DEĞİŞMEDİ" İLE "VERİ YOK" AYRI OLGULARDIR (L-007, 2026-08-28 denetimi).
    # 2026-08-16 ve 08-23 haftalık mesajları BİREBİR AYNIYDI ve okuyucu
    # "bu hafta hiçbir şey değişmedi" ile "aynı rapor tekrar basıldı"yı ayırt
    # edemiyordu. Veri değişmediyse rapor da değişmez — bu DOĞRU davranış;
    # eksik olan, değişmediğinin SÖYLENMESİYDİ.
    try:
        yeni = db.scalar(
            con, "SELECT COUNT(*) FROM outcomes "
                 " WHERE resolved_date > date('now', '-7 day')") or 0
        son = db.scalar(con, "SELECT MAX(resolved_date) FROM outcomes")
        L.append(f"bu hafta yeni çözülen: {yeni}"
                 + (f" · son çözüm: {son}" if son else " · hiç çözüm yok"))
        L.append("")
    except Exception as e:                                  # noqa: BLE001
        log.warning("haftalık çözüm sayacı okunamadı: %s", e)

    try:
        araclar = evaluate.araclar(con)
        if not araclar:
            # "tahmin" — bkz. `cli.cmd_degerlendir` içindeki aynı not (L-024).
            L.append("Journal'da hiç tahmin yok — ölçüm başlamadı.")
        for arac, n in sorted(araclar.items(), key=lambda kv: -kv[1]):
            e = evaluate.run(cfg, con, tool=arac)
            metin = report.evaluate_report(cfg, e)
            report.write(cfg, f"degerlendirme_{arac}_{report.bugun()}.md", metin)
            a = e.get("alfa") or {}
            ic = e.get("ic") or {}
            # ⚠ `n` ARTIK TAHMİN SAYISI. `evaluate.araclar` `outcomes` ile
            # INNER JOIN yapıyordu ve aktif model (252 tahmin, 79 veto) bu
            # listede HİÇ görünmüyordu; JOIN kalkınca sayının anlamı da
            # değişti. Etiketi güncellemeden bırakmak, doğru sayının yanına
            # yanlış kelimeyi yazmak olurdu (AGENTS §8: yorum bir iddiadır).
            # Çözülmüş sayısı zaten alt satırda payda olarak basılıyor.
            L.append(f"🔹 {arac} — {n} tahmin")
            # ⚠ PAYDA AÇIK YAZILIR. Eski biçim "replay (N=20) alfa 4.27pp"
            # diyordu ve iki farklı N'i yan yana basıyordu: 20 çözülmüş karar,
            # 13 gözlemli alfa. Aradaki 7 plan hiç tetiklenmemişti ve paydadan
            # SESSİZCE düşüyordu (AGENTS.md §11 madde 2 — 2026-08-11 denetimi).
            L.append(f"   alfa {_say(a.get('ort'), 2, 'pp')} "
                     f"(girişi olan {a.get('n', 0)}/{a.get('n_karar', n)}) · "
                     f"hüküm: {a.get('hukum', '—')}")
            if a.get("n_girmeyen"):
                L.append(f"   karar başına {_say(a.get('ort_karar_basina'), 2, 'pp')}"
                         f" — {a['n_girmeyen']} plan hiç tetiklenmedi")
            # ⚠ ÖRTÜŞME. Aynı isim art arda seçilince AYNI İŞLEM birden çok
            # satır olur ve bağımsız gözlem sayılır; `t` de şişer. Hüküm bu
            # satıra göre okunur (2026-08-15 denetimi).
            if a.get("ortusen_kayit"):
                L.append(f"   örtüşme ayıklanmış "
                         f"{_say(a.get('ort_bagimsiz'), 2, 'pp')} "
                         f"(bağımsız {a.get('n_bagimsiz')}/{a.get('n')}) · "
                         f"{a.get('hukum_bagimsiz', '—')}")
            # ⚠ ANAHTAR ADI. Burası `ic.get("n")` / `ic.get("ort")` okuyordu;
            # `stats.ic_summary` ise `n_donem` / `ic_ort` döndürür. `.get`
            # sessizdir: KeyError yok, satır hiç basılmıyordu. Sonuç —
            # PROJECT.md'nin İKİNCİ başarı kriteri (dönem-içi IC) düzenli
            # okunan tek kanalda görünmüyordu (2026-08-02 ve 08-09 haftalık
            # mesajlarında IC satırı yok). `report.py` aynı sözlükten DOĞRU
            # anahtarları okuyordu; iki tüketiciden biri yanlıştı ve ayrışma
            # sessiz kaldı. Eşliği artık test zorluyor (§12.2):
            # tests/test_otonom.py::TestHaftalikIC
            if ic.get("n_donem"):
                L.append(f"   IC {_say(ic.get('ic_ort'), 3)} "
                         f"(N={ic['n_donem']} dönem) · {ic.get('hukum', '—')}")
            # ⚠ VETO SATIRI. `araclar()`ın `outcomes` JOIN'i kalkınca aktif
            # model haftalığa girdi — ama o modelin FİİLEN ÜRETTİĞİ şey veto:
            # 252 tahminin 79'u. Sayı zaten hesaplanıyordu (`evaluate.run`
            # → `veto`), hiçbir kanalda BASILMIYORDU. ADR #008 sonrası sistemin
            # kalan ana ürünü "haber/veto" diye tanımlanmıştı; o ürün üç hafta
            # boyunca hiçbir raporda görünmedi.
            #
            # `n_olculen` AYRI basılır: "79 veto kondu" ile "vetonun değeri
            # ölçüldü" iki farklı olgudur ve aynı satıra sıkıştırılamaz (L-003).
            v = e.get("veto") or {}
            if v.get("veto_sayisi"):
                kod = " · ".join(f"{k} {n2}" for k, n2 in
                                 sorted((v.get("veto_kodlari") or {}).items(),
                                        key=lambda kv: -kv[1]))
                L.append(f"   veto {v['veto_sayisi']}"
                         + (f" ({kod})" if kod else "")
                         + f" · değeri: {v.get('hukum', '—')}"
                         + f" (ölçülen {v.get('n_olculen', 0)})")
            L.append("")
        sonuc["adimlar"]["degerlendir"] = f"{len(araclar)} araç"
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "degerlendir", e)
        L.append(f"⚠ Değerlendirme koşulamadı: {e}")

    L.append("`ölçüm yetersiz` bir sonuçtur, eksiklik değil.")
    try:
        tg.bildir(cfg, "\n".join(L))
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "bildir", e)
    sonuc["ozet"] = "\n".join(L)
    _kosu_bitir(con, kosu_id, sonuc,
                "durduruldu" if sonuc.get("hatalar") else "tamam")
    return sonuc


# ---------------------------------------------------------------- nöbetçi
def nobetci(cfg: dict, con: sqlite3.Connection, *,
            bugun_tr: str | None = None,
            simdi: datetime | None = None) -> dict:
    """DIŞARIDAN bakan gözcü — "bugün koşu oldu mu?" sorusunu sorar.

    ═══════════════════════════════════════════════════════════════════════
    NEDEN AYRI BİR İŞ OLMAK ZORUNDA
    ═══════════════════════════════════════════════════════════════════════
    L-015'in kendi cümlesi: **bir süreç kendi yokluğunu haber veremez.**
    2026-08-06'da günlük iş GitHub tarafında runner alamadı, HİÇ BAŞLAMADI;
    dolayısıyla ne rapor, ne Telegram, ne hata. O gün tamamen sessizdi.

    O cümlenin doğru sonucu şuydu: çözüm sürecin DIŞINDA olmalı. İlk
    denemede çözüm yine sürecin içine kondu (`saglik`'e bir kontrol) ve
    sistemi kilitledi. Bu fonksiyon o hatanın düzeltilmiş hâli: AYRI bir
    workflow, AYRI bir zamanlama, AYRI bir runner talebi. Günlük iş runner
    alamazsa bu iş alabilir ve haber verir.

    ⚠ Bu fonksiyon hiçbir şeyi DÜZELTMEZ, yalnız SÖYLER. Bir gözcünün
    tamir etmeye kalkması, gözcülüğü de tamiri de bozar.

    Çıkış: {"sessiz": bool, "analizsiz": bool, ...}. İKİSİ DE işi kırmızıya
    çevirir: `sessiz` → beklenen koşu hiç başlamamış · `analizsiz` →
    koşu olmuş ama kapanmış son seans analiz edilmemiş.
    """
    from .calendar_bist import BistCalendar

    simdi = simdi or util.utc_now()
    bugun_tr = bugun_tr or util.bugun_tr(cfg["takvim"]["timezone"], simdi=simdi)
    cal = BistCalendar(cfg, con)

    # ⚠⚠ REFERANS DUVAR SAATİ DEĞİL, KAPANMIŞ SON SEANSTIR (L-026).
    #
    # Eski sürüm "bugün (TR takvim günü) koşu kaydı var mı?" diye soruyordu ve
    # bu soru GitHub cron gecikmesi altında İKİ YÖNDE birden bozuluyordu:
    #
    #   YANLIŞ ALARM — günlük iş TR gece yarısından ÖNCE, gözcü SONRA koştu.
    #     Ölçüldü: 2026-08-26 ve 2026-09-01. Günlük iş sorunsuz bitmişti;
    #     gözcü "bugün koşu YOK" deyip işi kırmızıya çevirdi ve mail attı.
    #
    #   SESSİZLİK — gecikme gözcüyü CUMARTESİye taşıdı, `is_trading_day`
    #     False döndü ve gözcü "koşu beklenmiyor" deyip SUSTU. Ölçüldü:
    #     2026-08-29T02:25Z. Tam o anda Cuma (08-28) seansı analiz EDİLMEMİŞTİ.
    #
    # Yani gözcü, olmayan arızada bağırıp gerçek arızada susuyordu. Sebep tek:
    # "hangi gün için koştum?" sorusunun cevabı koşunun BAŞLAMA SAATİNDEN
    # okunuyordu. Takvim gecikmeyi bilmez; seans kapanışı bilir.
    #
    # Yeni soru — gecikmeden BAĞIMSIZ: *kapanmış son seanstan BERİ* bir günlük
    # koşu başladı mı? Gözcü 3 saat de gecikse, gece yarısını da aşsa, hafta
    # sonuna da taşsa cevap DEĞİŞMEZ.
    beklenen = cal.last_closed_session(simdi)
    kapanis = util.to_utc_iso(cal.session_close_utc(beklenen))
    out: dict = {"tarih": bugun_tr, "beklenen_seans": beklenen.isoformat(),
                 "seans_kapanis_utc": kapanis,
                 "sessiz": False, "analizsiz": False, "satirlar": []}

    kosu = journal.son_kosu_zamana_gore(con, tur="gunluk")
    son_bar = db.scalar(con, "SELECT MAX(date) FROM bars_daily")
    son_analiz = db.scalar(con, "SELECT MAX(asof) FROM predictions")
    out.update(son_kosu=(kosu or {}).get("tarih_tr"),
               son_kosu_baslangic=(kosu or {}).get("baslangic_utc"),
               son_bar=son_bar, son_analiz=son_analiz)

    kapanistan_sonra = bool(kosu) and str(kosu["baslangic_utc"]) >= kapanis

    if not kapanistan_sonra:
        out["sessiz"] = True
        out["satirlar"].append(
            f"Kapanmış son seans {beklenen.isoformat()} (kapanış {kapanis}) "
            f"için günlük koşu YOK. Son koşu başlangıcı: "
            f"{(kosu or {}).get('baslangic_utc', '—')}. "
            "İş hiç başlamamış olabilir (runner kapasitesi) — "
            "Actions geçmişini kontrol et.")
    elif kosu["durum"] == "kosuyor":
        out["sessiz"] = True
        out["satirlar"].append(
            f"Koşu BAŞLADI ama bitmedi ({kosu['baslangic_utc']}). "
            "Süreç bitmeden ölmüş olabilir (timeout / iptal).")
    elif kosu["durum"] == "durduruldu":
        out["satirlar"].append(
            f"Son koşu DURDURULDU: {kosu.get('hatalar') or '—'}")

    # İkinci soru, ayrı: koşu oldu ama analiz üretti mi? (L-003: iki olgu,
    # iki satır — tek satıra sıkıştırılırsa hangisinin bozuk olduğu görünmez.)
    #
    # ⚠⚠ REFERANS TAKVİMDİR, `son_bar` DEĞİL — ve bu ayrım L-010'un ta kendisi:
    # *"kontroller birbirini doğruluyorsa hiçbiri dış dünyaya bakmıyordur."*
    #
    # İlk sürüm `son_analiz`i `son_bar`la karşılaştırıyordu. İkisi de günlük
    # koşunun ürünü: koşu hiç olmazsa yeni bar da GİRMEZ, analiz de yazılmaz
    # ve fark 0 çıkar. Yani gözcü, tam da alarm vermesi gereken durumda
    # "temiz" derdi — iki bayat sayı birbirini doğruladığı için. Bir nöbetçinin
    # yapabileceği en kötü hata bu.
    #
    # `last_closed_session()` takvimden gelir ve koşuya bağlı DEĞİLDİR; dış
    # dünyanın referansı odur. Eşik 1: nöbetçi günlük işten SONRA koşar,
    # dolayısıyla kapanmış son seansın analizini talep etmeye hakkı vardır.
    #
    # ⚠ ŞİDDET (2026-09-02): bu bulgu ARTIK İŞİ KIRMIZIYA ÇEVİRİR.
    # Eskiden yalnız `sessiz` çıkışı 1 yapardı; "koşu oldu ama seans analizsiz
    # kaldı" satırı Telegram'a düşüp Actions'ta YEŞİL kalıyordu. Ölçüldü
    # 2026-08-28T03:51Z: gözcü "son analiz 08-26, kapanmış son seans 08-27 →
    # 1 işlem günü analizsiz" dedi, iş yeşil bitti, GitHub maili ÇIKMADI.
    # Aynı hafta 08-27 ve 08-31 seansları hiç analiz edilmeden geçti.
    # Gözcünün BULDUĞU arıza, gözcünün SUSTUĞU arızaydı.
    if not son_analiz:
        out["analizsiz"] = True
        out["satirlar"].append("Journal boş — hiç analiz üretilmemiş.")
    else:
        fark = cal.trading_days_between(son_analiz, beklenen.isoformat())
        if fark >= 1:
            out["analizsiz"] = True
            out["satirlar"].append(
                f"Son analiz {son_analiz}, kapanmış son seans "
                f"{beklenen.isoformat()} → {fark} işlem günü analizsiz. "
                f"(son bar: {son_bar})")
    return out
