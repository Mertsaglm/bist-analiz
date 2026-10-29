"""Otonom koşu — mekanizma testleri (Faz 8).

Buradaki testlerin ortak sorusu tek: **hangi hata koşuyu durdurur, hangisi
durdurmaz?** Bu ayrım yanlış kurulursa iki felaketten biri olur:

  * Fazla hoşgörü → iş HER ZAMAN yeşil biter, bozukluk günlerce fark edilmez
    (gold'da yaşandı: 17 gün donuk tablo, ADR #004 / L-002).
  * Fazla katılık  → haber katmanındaki geçici bir aksama yüzünden o günün
    plan geometrisi ve raporu hiç üretilmez.

AĞ YOK: tüm dış çağrılar monkeypatch'lenir.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src import otonom, saglik as sag


def date_of(d):
    """`is_trading_day` hem `date` hem ISO metin alabilir."""
    return d if isinstance(d, date) else date.fromisoformat(str(d)[:10])


@pytest.fixture
def sessiz_telegram(monkeypatch):
    """Telegram'a gerçekten gitmesin; ne gönderildiğini topla."""
    gonderilen: list[str] = []
    monkeypatch.setattr(otonom.tg, "bildir",
                        lambda cfg, metin: gonderilen.append(metin) or True)
    return gonderilen


def _adimlari_sahtele(monkeypatch, *, saglik_kritik=False, dusen: set | None = None):
    """Tüm dış adımları sahtele. `dusen` içindeki adımlar istisna fırlatır."""
    dusen = dusen or set()
    cagrilan: list[str] = []

    from src import indicators, llm_io, news, prices, resolver, macro

    def kaydet(ad, deger):
        def f(*a, **k):
            cagrilan.append(ad)
            if ad in dusen:
                raise RuntimeError(f"{ad} bilerek düştü")
            return deger
        return f

    monkeypatch.setattr(macro, 'daily', lambda *a, **k: {})
    monkeypatch.setattr(news, 'sync_beklenen', lambda *a, **k: {'ok':True,'yazilan':0,'ticker':0})
    monkeypatch.setattr(prices, "daily", kaydet(
        "veri", {"tickers": 70, "hayalet_silinen": 0, "yarim_bar_silinen": 0,
                 "kalite_gecmeyen": 1, "start": "2026-07-14"}))
    # ⚠ Sahtelenmezse GERÇEK `sync_indices` koşar ve test ağa çıkar; adım
    # kritik olmadığı için hata sessizce yutulur ve suite yavaşlar.
    monkeypatch.setattr(prices, "sync_actions", kaydet(
        "kurumsal", {"ok": True, "kayit": 5, "tickers": 70, "failed": {}}))
    monkeypatch.setattr(prices, "sync_indices", kaydet(
        "endeks", {"XU100": 250, "USDTRY": 365}))
    monkeypatch.setattr(indicators, "compute_and_store", kaydet(
        "gosterge", {"satir": {"THYAO": 2900}, "tickers": 70,
                     "set_version": "v1"}))
    monkeypatch.setattr(news, "sync", kaydet(
        "haber", {"yazilan": 5, "atlanan_aralik": None}))
    monkeypatch.setattr(resolver, "resolve_open", kaydet(
        "coz", {"cozulen": 0, "hala_acik": 0, "dagilim": {}}))
    monkeypatch.setattr(llm_io, "build_bundle", kaydet("paket", _bundle()))
    monkeypatch.setattr(llm_io, "write_bundle", lambda cfg, b: {})

    def sahte_saglik(cfg, con):
        cagrilan.append("saglik")
        if "saglik" in dusen:
            raise RuntimeError("saglik bilerek düştü")
        kritik = [(sag.KRITIK, "gösterge tazeliği", "bayat")] if saglik_kritik else []
        return {"asof": "2026-07-29",
                "bulgular": kritik or [(sag.OK, "hepsi", "temiz")],
                "kritik": kritik, "uyari": []}

    monkeypatch.setattr(otonom.sag, "kontrol", sahte_saglik)
    return cagrilan


def _bundle(asof="2026-07-29"):
    return {"asof": asof, "uyari": "test", "bundle_sha": "sha",
            "rejim": {"etiket": "neutral",
                      "pozisyon_politikasi": {"nakit_pct": 40.0,
                                              "maks_pozisyon": 5,
                                              "sektor_basi_maks": 2}},
            "evren": []}


# ============================================================ takvim kapısı
class TestTakvimKapisi:
    def test_islem_gunu_degilse_HICBIR_adim_kosmaz(self, cfg, con, monkeypatch,
                                                   sessiz_telegram):
        """⚠ Cron hafta içi TATİLLERİ bilmez. Tatilde koşmak yeni bar
        olmadığı için `saglik`i boş yere KRİTİK yapar ve her tatilde
        yanlış alarm üretirdi."""
        cagrilan = _adimlari_sahtele(monkeypatch)
        from src.calendar_bist import BistCalendar
        monkeypatch.setattr(BistCalendar, "is_trading_day", lambda self, d: False)

        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 1, 1))
        assert "atlandi" in sonuc
        assert cagrilan == [], "tatil gününde adım koşmuş"
        assert not sessiz_telegram, "tatilde bildirim gönderilmiş"

    def test_islem_gununde_adimlar_KOSAR(self, cfg, con, monkeypatch,
                                         sessiz_telegram):
        cagrilan = _adimlari_sahtele(monkeypatch)
        from src.calendar_bist import BistCalendar
        monkeypatch.setattr(BistCalendar, "is_trading_day", lambda self, d: True)

        otonom.gunluk(cfg, con, bugun=date(2026, 7, 29), analist_calistir=False)
        assert "veri" in cagrilan and "gosterge" in cagrilan

    def test_GECIKEN_kosu_HAFTA_SONUNA_tasinca_CUMAYI_analiz_eder(
            self, cfg, con, monkeypatch, sessiz_telegram):
        """⚠ GERÇEK OLAY — 2026-08-28 (Cuma) slotu 08-29T00:39Z'de koştu.

        Koşunun günü `bugun_tr()`ten okunuyordu: etiket "2026-08-29"
        (CUMARTESİ) oldu, takvim kapısı "işlem günü değil" dedi ve koşu
        hiçbir adım atmadan ATLANDI. Cuma seansı o gün analiz edilmedi;
        `otonom_kosu`da 2026-08-29 için `durum='atlandi'` bir kayıt duruyor.
        GitHub gecikmesi işin TAMAMINI yedi ve hiçbir hata fırlamadı.

        Sözleşme: koşunun günü ANALİZ ETTİĞİ SEANSTIR. Gecikme onu kaydıramaz.
        """
        cagrilan = _adimlari_sahtele(monkeypatch)
        from src import journal
        from src.calendar_bist import BistCalendar
        # Cumartesi 00:39Z — kapanmış son seans hâlâ Cuma (08-28).
        monkeypatch.setattr(BistCalendar, "last_closed_session",
                            lambda s, ts=None: date(2026, 8, 28))
        monkeypatch.setattr(BistCalendar, "is_trading_day",
                            lambda s, d: date_of(d).weekday() < 5)

        sonuc = otonom.gunluk(cfg, con, analist_calistir=False)
        assert "atlandi" not in sonuc, (
            "gecikme koşuyu Cumartesiye taşıdı ve iş atlandı — L-026 tekrarı")
        assert "veri" in cagrilan and "gosterge" in cagrilan
        k = journal.son_kosu_zamana_gore(con, tur="gunluk")
        assert k["tarih_tr"] == "2026-08-28", (
            f"heartbeat etiketi seansa değil duvar saatine bağlanmış: "
            f"{k['tarih_tr']}")

    def test_ENDEKS_zincirde_kosar(self, cfg, con, monkeypatch, sessiz_telegram):
        """L-002'NİN ÜÇÜNCÜ TEKRARININ KİLİDİ.

        ⚠ NE OLMUŞTU: `prices.daily` yalnız HİSSE barlarını çeker. Endeksi
        çeken `sync_indices`'in tek çağrı yeri `cli.cmd_veri` idi — yani
        `index_daily` ancak Mert elle `bist veri gunluk` koştuğunda
        tazeleniyordu. Ölçüldü (2026-08-15): endeks 08-06'da donmuş,
        hisse barları 08-14'teydi; `regime_daily`'nin üç girdisi beş gün
        boyunca bit bit aynı yazıldı ve hiçbir hata fırlamadı.

        Aynı ders daha önce `history_daily` (L-002) ve `macro.daily` için
        öğrenilmişti; üçüncüsü aynı dosyada, 30 satır arayla duruyordu.
        """
        cagrilan = _adimlari_sahtele(monkeypatch)
        from src.calendar_bist import BistCalendar
        monkeypatch.setattr(BistCalendar, "is_trading_day", lambda self, d: True)

        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29),
                              analist_calistir=False)
        assert "endeks" in cagrilan, (
            "otonom zincir `sync_indices` çağırmıyor — `index_daily` DONAR "
            "ve rejim bayat XU100 ile karar verir (L-002)")
        assert "endeks" in sonuc["adimlar"], "endeks adımı rapora yazılmıyor"

    def test_ENDEKS_dususu_KRITIK_DEGIL(self, cfg, con, monkeypatch,
                                        sessiz_telegram):
        """Tek koşuluk bir yfinance arızası fiyat tarafını da öldürmemeli.

        Boşluk BİRİKİRSE `saglik._index_tazelik` (KAPI, 2 seans toleranslı)
        koşuyu zaten durdurur — L-017 gereği bu devralma `otonom.gunluk`
        adım 2b'nin yorumunda açıkça yazılıdır.
        """
        cagrilan = _adimlari_sahtele(monkeypatch, dusen={"endeks"})
        from src.calendar_bist import BistCalendar
        monkeypatch.setattr(BistCalendar, "is_trading_day", lambda self, d: True)

        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29),
                              analist_calistir=False)
        assert "endeks" in sonuc["hatalar"]
        assert otonom.basarisiz_mi(sonuc) == [], "endeks düşüşü koşuyu kırmızıya çevirdi"
        assert "gosterge" in cagrilan and "paket" in cagrilan, "zincir durdu"


# ============================================================ sağlık kapısı
class TestSaglikKapisi:
    @pytest.fixture(autouse=True)
    def _islem_gunu(self, monkeypatch):
        from src.calendar_bist import BistCalendar
        monkeypatch.setattr(BistCalendar, "is_trading_day", lambda self, d: True)

    def test_KRITIK_saglik_sonraki_adimlari_DURDURUR(self, cfg, con, monkeypatch,
                                                     sessiz_telegram):
        """⚠ NE OLURDU: bayat göstergeyle üretilen paket BOŞ ama şeklen
        geçerli olur (L-009: 0 skorlanan isim, 0 plan, rejim paydası 0) ve
        analist onu analiz eder. Sistemin en pahalı hata sınıfı tam olarak bu:
        kod doğru, veri sessizce dar, çıktı hâlâ 'geçerli' görünüyor."""
        cagrilan = _adimlari_sahtele(monkeypatch, saglik_kritik=True)
        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29))

        assert "paket" not in cagrilan, "sağlık kapalıyken paket üretilmiş"
        assert "coz" not in cagrilan
        assert "saglik" in sonuc["hatalar"]
        assert otonom.basarisiz_mi(sonuc) == ["saglik"]

    def test_KRITIK_saglikta_TELEGRAMA_alarm_duser(self, cfg, con, monkeypatch,
                                                   sessiz_telegram):
        _adimlari_sahtele(monkeypatch, saglik_kritik=True)
        otonom.gunluk(cfg, con, bugun=date(2026, 7, 29))
        assert sessiz_telegram, "kritik sağlıkta bildirim gitmemiş"
        assert "🛑" in sessiz_telegram[0]

    def test_telegram_de_coktuyse_asil_hata_KAYBOLMAZ(self, cfg, con, monkeypatch):
        """Bildirim gönderilemese bile sağlık hatası sonuçta durmalı."""
        _adimlari_sahtele(monkeypatch, saglik_kritik=True)
        monkeypatch.setattr(otonom.tg, "bildir",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("tg yok")))
        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29))
        assert otonom.basarisiz_mi(sonuc) == ["saglik"]


# ============================================================ hata sınıfları
class TestHataSiniflari:
    @pytest.fixture(autouse=True)
    def _islem_gunu(self, monkeypatch):
        from src.calendar_bist import BistCalendar
        monkeypatch.setattr(BistCalendar, "is_trading_day", lambda self, d: True)

    def test_KRITIK_adim_listesi_beklenen(self):
        """Bu liste bir karardır (ADR #013); sessizce değişmemeli.

        `analist` ve `haber` bilerek DIŞARIDA: ikisi de düşse o günün plan
        geometrisi ve risk çerçevesi tek başına değerlidir.
        """
        assert otonom.KRITIK_ADIMLAR == ("veri", "kurumsal", "gosterge", "saglik", "rapor")
        assert "analist" not in otonom.KRITIK_ADIMLAR
        assert "haber" not in otonom.KRITIK_ADIMLAR

    def test_haber_dususu_koseyi_DURDURMAZ(self, cfg, con, monkeypatch,
                                           sessiz_telegram):
        cagrilan = _adimlari_sahtele(monkeypatch, dusen={"haber"})
        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29),
                              analist_calistir=False)
        assert "haber" in sonuc["hatalar"]
        assert "coz" in cagrilan, "haber düştü diye sonraki adımlar atlanmış"
        assert otonom.basarisiz_mi(sonuc) == [], "haber kritik sayılmış"

    def test_analist_dususu_KRITIK_DEGIL_rapor_yine_uretilir(
            self, cfg, con, monkeypatch, sessiz_telegram):
        """Zincirin tamamı düşse bile deterministik rapor üretilmeli."""
        _adimlari_sahtele(monkeypatch)
        from src import analist
        monkeypatch.setattr(analist, "calistir", lambda *a, **k: (
            _ for _ in ()).throw(analist.TumModellerDustu("hepsi düştü")))

        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29))
        assert "analist" in sonuc["hatalar"]
        assert otonom.basarisiz_mi(sonuc) == []
        assert sonuc.get("rapor"), "analist düşünce rapor da üretilmemiş"

    def test_veri_dususu_KRITIK(self, cfg, con, monkeypatch, sessiz_telegram):
        _adimlari_sahtele(monkeypatch, dusen={"veri"})
        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29),
                              analist_calistir=False)
        assert "veri" in otonom.basarisiz_mi(sonuc)

    def test_gosterge_dususu_KRITIK(self, cfg, con, monkeypatch, sessiz_telegram):
        """L-009'un kilidi: gösterge adımı artık akışın içinde VE kritik."""
        _adimlari_sahtele(monkeypatch, dusen={"gosterge"})
        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29),
                              analist_calistir=False)
        assert "gosterge" in otonom.basarisiz_mi(sonuc)

    def test_gunluk_ISTISNA_FIRLATMAZ(self, cfg, con, monkeypatch, sessiz_telegram):
        """Her adım düşse bile fonksiyon sözlük döner — çağıran karar verir."""
        _adimlari_sahtele(monkeypatch,
                          dusen={"veri", "gosterge", "haber", "coz", "paket"})
        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29),
                              analist_calistir=False)
        assert isinstance(sonuc, dict) and sonuc["hatalar"]


# ============================================================ sıra
class TestAdimSirasi:
    def test_coz_RAPORDAN_ONCE_kosar(self, cfg, con, monkeypatch, sessiz_telegram):
        """Gold dersi: bugün kapanan tahminler O GÜNÜN raporundaki karneye
        girmeli, bir gün gecikmeli değil."""
        from src.calendar_bist import BistCalendar
        monkeypatch.setattr(BistCalendar, "is_trading_day", lambda self, d: True)
        cagrilan = _adimlari_sahtele(monkeypatch)

        # Raporu da aynı listeye yazdır ki SIRA tek yerden okunabilsin.
        gercek_yaz = otonom.report.write
        monkeypatch.setattr(
            otonom.report, "write",
            lambda *a, **k: cagrilan.append("rapor") or gercek_yaz(*a, **k))
        otonom.gunluk(cfg, con, bugun=date(2026, 7, 29), analist_calistir=False)

        assert "coz" in cagrilan and "rapor" in cagrilan
        assert cagrilan.index("coz") < cagrilan.index("rapor"), \
            f"çözüm rapordan SONRA koşmuş: {cagrilan}"

    def test_gosterge_VERIDEN_SONRA(self, cfg, con, monkeypatch, sessiz_telegram):
        from src.calendar_bist import BistCalendar
        monkeypatch.setattr(BistCalendar, "is_trading_day", lambda self, d: True)
        cagrilan = _adimlari_sahtele(monkeypatch)
        otonom.gunluk(cfg, con, bugun=date(2026, 7, 29), analist_calistir=False)
        assert cagrilan.index("veri") < cagrilan.index("gosterge")
        assert cagrilan.index("gosterge") < cagrilan.index("saglik")


class TestNobetci:
    """Gözcü — koşunun DIŞINDAN bakan tek kontrol (ADR #017, L-015/L-016).

    ⚠ REFERANS `son_bar` DEĞİL, TAKVİMDİR.

    İlk sürüm `son_analiz`i `son_bar`la karşılaştırıyordu. İkisi de günlük
    koşunun ürünüdür: koşu hiç olmazsa yeni bar da girmez, analiz de yazılmaz
    ve fark 0 çıkar — iki BAYAT sayı birbirini doğrular. L-010'un aynen
    tekrarı: *"kontroller birbirini doğruluyorsa hiçbiri dış dünyaya
    bakmıyordur."* Referans artık TAKVİM (`last_closed_session`), yani koşuya
    bağlı olmayan tek şey.

    ⚠⚠ İKİNCİ TUR (L-026, 2026-09-02): referans takvimdi ama SORU hâlâ duvar
    saatiyle soruluyordu — *"bugün (TR takvim günü) koşu kaydı var mı?"*.
    GitHub cron gecikmesi bu soruyu iki yönde birden bozdu ve gözcü,
    OLMAYAN arızada bağırıp GERÇEK arızada sustu. Aşağıdaki iki test
    (`test_GECE_YARISINI_ASAN_*`, `test_CUMARTESIYE_TASAN_*`) o iki gerçek
    olayın kilididir; soru duvar saatine geri dönerse ikisi birden kırılır.
    """

    # Gözcü artık ZAMANA bakıyor (heartbeat kapanıştan sonra mı başladı?),
    # etikete değil. O yüzden testin `baslangic_utc`yi ELDE kurması şart:
    # `kosu_basla` gerçek `utc_now()` yazar ve o değer duvar saatine bağlıdır
    # (AGENTS §11/6 — zaman kaynağı enjekte edilebilir olmalı).
    @staticmethod
    def _kur(con, cfg, bar_gunleri, analiz_gunu=None, kosu_gunu=None,
             kosu_baslangic=None, durum="tamam"):
        from src import db, journal
        from tests.conftest import add_bars, add_index, add_universe
        add_universe(con, "AAA")
        add_bars(con, "AAA", [(d, 10.0, 11.0, 9.0, 10.0, 1000.0, 10.0)
                              for d in bar_gunleri])
        add_index(con, "XU100", bar_gunleri)
        if kosu_gunu:
            kid = journal.kosu_basla(cfg, con, tur="gunluk", tarih_tr=kosu_gunu)
            # Varsayılan: o günün seansı kapandıktan 1,5 saat sonra (19:40 TR).
            bas = kosu_baslangic or f"{kosu_gunu}T16:40:00+00:00"
            con.execute("UPDATE otonom_kosu SET baslangic_utc = ? WHERE kosu_id = ?",
                        (bas, kid))
            if durum != "kosuyor":
                journal.kosu_bitir(con, kid, durum=durum)
                con.execute("UPDATE otonom_kosu SET baslangic_utc = ? "
                            "WHERE kosu_id = ?", (bas, kid))
            con.commit()
        if analiz_gunu:
            db.upsert_many(con, "llm_runs",
                           ["run_id", "asof", "tool", "bundle_sha",
                            "output_path", "audit_passed", "created_utc"],
                           [("r", analiz_gunu, "test", "s", "", 1, "now")])
            db.upsert_many(
                con, "predictions",
                ["prediction_id", "run_id", "asof", "ticker", "signal", "action",
                 "confidence", "confidence_p", "factor_set_version", "weights_hash",
                 "indicator_set_version", "regime", "thesis", "counter_scenario",
                 "key_risk", "falsifier", "close_at_asof", "created_utc"],
                [("p", "r", analiz_gunu, "AAA", "hold", "izle", "orta", 0.5,
                  "v1", "h", "v1", "neutral", "t", "c", "k", "f", 10.0, "now")])

    def _takvim(self, monkeypatch, son_seans):
        from src.calendar_bist import BistCalendar
        monkeypatch.setattr(BistCalendar, "last_closed_session",
                            lambda s, ts=None: date.fromisoformat(son_seans))
        monkeypatch.setattr(BistCalendar, "is_trading_day", lambda s, d: True)

    def test_kosu_ve_analiz_guncelse_SESSIZ_DEGIL_TEMIZ(self, cfg, con, monkeypatch):
        from src import otonom
        from tests.conftest import is_gunleri
        g = is_gunleri(4, "2026-08-03")
        self._kur(con, cfg, g, analiz_gunu=g[-1], kosu_gunu=g[-1])
        self._takvim(monkeypatch, g[-1])
        n = otonom.nobetci(cfg, con, bugun_tr=g[-1])
        assert not n["sessiz"] and not n["analizsiz"] and n["satirlar"] == []

    def test_seans_kapandi_ama_KOSU_YOKSA_alarm(self, cfg, con, monkeypatch):
        """2026-08-06 vakası: iş hiç başlamadı, o gün tamamen sessizdi."""
        from src import otonom
        from tests.conftest import is_gunleri
        g = is_gunleri(4, "2026-08-03")
        self._kur(con, cfg, g, analiz_gunu=g[-2], kosu_gunu=g[-2])
        self._takvim(monkeypatch, g[-1])
        n = otonom.nobetci(cfg, con, bugun_tr=g[-1])
        assert n["sessiz"]
        assert any("koşu YOK" in s for s in n["satirlar"])

    def test_GECE_YARISINI_ASAN_gozcu_YANLIS_ALARM_VERMEZ(self, cfg, con,
                                                          monkeypatch):
        """⚠ GERÇEK OLAY — 2026-09-01 (ve aynısı 2026-08-26).

        Günlük iş 19:31Z'de sorunsuz koştu ve bitti. Gözcünün 19:40Z slotu
        GitHub'da 2 saat 18 dakika gecikti: 21:58Z, yani TR saatiyle
        02 Eylül 00:58. `bugun_tr` "2026-09-02" dedi, heartbeat "2026-09-01"
        diyordu, gözcü "bugün koşu KAYDI YOK" deyip işi KIRMIZI yaptı ve
        GitHub arıza maili gönderdi. Ortada arıza YOKTU.

        Gecikme GitHub'ın; onu düzeltemeyiz. Düzeltilebilen şey SORUYDU.
        """
        from src import otonom
        # Seans günü Salı 2026-09-01; günlük iş 19:31Z'de (TR 22:31) koştu.
        self._kur(con, cfg, ["2026-08-31", "2026-09-01"],
                  analiz_gunu="2026-09-01", kosu_gunu="2026-09-01",
                  kosu_baslangic="2026-09-01T19:31:57+00:00")
        self._takvim(monkeypatch, "2026-09-01")
        n = otonom.nobetci(cfg, con, bugun_tr="2026-09-02",
                           simdi=datetime(2026, 9, 1, 21, 58, tzinfo=timezone.utc))
        assert not n["sessiz"] and not n["analizsiz"], (
            "gözcü gece yarısını aşınca YANLIŞ ALARM verdi — duvar saatine "
            "geri dönülmüş (L-026)")
        assert n["satirlar"] == []

    def test_CUMARTESIYE_TASAN_gozcu_SUSMAZ(self, cfg, con, monkeypatch):
        """⚠ GERÇEK OLAY — 2026-08-29T02:25Z. Aynı hatanın SESSİZ yüzü.

        Cuma (08-28) slotu gecikip Cumartesiye taştı. Eski sürüm önce
        `is_trading_day(bugun_tr)` soruyordu; Cumartesi False döndü ve gözcü
        "koşu beklenmiyor" deyip TEMİZ raporladı. Oysa tam o anda Cuma seansı
        analiz edilmemişti (`son_analiz` 08-26'da duruyordu).

        Bir gözcünün yapabileceği en pahalı hata: gerçek arızada susmak.
        """
        from src import otonom
        # Cuma seansı kapandı; son analiz iki seans geride, koşu da eski.
        self._kur(con, cfg, ["2026-08-26", "2026-08-27", "2026-08-28"],
                  analiz_gunu="2026-08-26", kosu_gunu="2026-08-26",
                  kosu_baslangic="2026-08-26T18:21:29+00:00")
        self._takvim(monkeypatch, "2026-08-28")
        n = otonom.nobetci(cfg, con, bugun_tr="2026-08-29",       # CUMARTESİ
                           simdi=datetime(2026, 8, 29, 2, 25, tzinfo=timezone.utc))
        assert n["sessiz"], "hafta sonuna taşan gözcü sustu — L-026 tekrarı"
        assert n["analizsiz"], "analiz edilmemiş Cuma seansı görülmedi"

    def test_ANALIZSIZ_seans_isi_KIRMIZIYA_cevirir(self, cfg, con, monkeypatch):
        """⚠ GERÇEK OLAY — 2026-08-28T03:51Z.

        Gözcü doğru bulguyu buldu ("son analiz 08-26, kapanmış son seans
        08-27 → 1 işlem günü analizsiz") ama `sessiz` False olduğu için çıkış
        0 döndü: Actions YEŞİL, GitHub maili YOK. Bulgu yalnız Telegram'a
        düştü ve fark edilmedi; o hafta 08-27 ve 08-31 seansları hiç analiz
        edilmeden geçti.

        Gözcünün BULDUĞU arıza, gözcünün SUSTUĞU arıza olmamalı.
        """
        from src import otonom
        self._kur(con, cfg, ["2026-08-26", "2026-08-27"],
                  analiz_gunu="2026-08-26", kosu_gunu="2026-08-27",
                  kosu_baslangic="2026-08-28T01:06:02+00:00")
        self._takvim(monkeypatch, "2026-08-27")
        n = otonom.nobetci(cfg, con, bugun_tr="2026-08-28",
                           simdi=datetime(2026, 8, 28, 3, 51, tzinfo=timezone.utc))
        assert not n["sessiz"], "koşu gerçekten olmuştu — yanlış olguya bakıldı"
        assert n["analizsiz"], "analizsiz seans bulgusu üretilmedi"
        assert any("analizsiz" in s for s in n["satirlar"])

    def test_BAYAT_BAR_gozcuyu_KANDIRAMAZ(self, cfg, con, monkeypatch):
        """⚠ ASIL KİLİT. Koşu hiç olmayınca bar da analiz de bayat kalır ve
        `son_analiz == son_bar` olur. Eski sürüm burada "temiz" derdi."""
        from src import otonom
        from tests.conftest import is_gunleri
        g = is_gunleri(6, "2026-08-03")
        # Bar VE analiz ikisi de 3 seans geride — birbirleriyle "tutarlı".
        self._kur(con, cfg, g[:-3], analiz_gunu=g[-4], kosu_gunu=g[-1])
        self._takvim(monkeypatch, g[-1])          # takvim: bugün seans kapandı
        n = otonom.nobetci(cfg, con, bugun_tr=g[-1])
        assert n["son_analiz"] == n["son_bar"], "kurulum yanlış — ikisi eşit olmalı"
        assert any("analizsiz" in s for s in n["satirlar"]), (
            "iki bayat sayı birbirini doğruladı ve gözcü sustu — L-010 tekrarı")
        assert n["analizsiz"], "bulgu üretildi ama çıkış kodunu kırmızıya çevirmiyor"

    def test_kosu_BASLAYIP_bitmemisse_alarm(self, cfg, con, monkeypatch):
        """`durum='kosuyor'` kalması bilgidir: süreç bitmeden ölmüş."""
        from src import otonom
        from tests.conftest import is_gunleri
        g = is_gunleri(4, "2026-08-03")
        self._kur(con, cfg, g, analiz_gunu=g[-1], kosu_gunu=g[-1],
                  durum="kosuyor")
        self._takvim(monkeypatch, g[-1])
        n = otonom.nobetci(cfg, con, bugun_tr=g[-1])
        assert n["sessiz"] and any("bitmedi" in s for s in n["satirlar"])

    def test_gozcu_TAKVIM_GUNUNE_degil_SEANSA_bakar(self, cfg, con, monkeypatch):
        """Eski `test_islem_gunu_degilse_KOSU_BEKLENMEZ`in yerine geçer.

        O test şunu kilitliyordu: "bugün işlem günü değilse gözcü hiçbir şey
        sormaz". Kilitlediği şey ARIZANIN KENDİSİYDİ — gecikme gözcüyü hafta
        sonuna taşıdığında tam olarak bu dal çalışıp gözcüyü kör ediyordu.

        Yeni sözleşme: gözcünün takvim günü ne olursa olsun, sorusu daima
        KAPANMIŞ SON SEANS hakkındadır. Hafta sonu koşan gözcü Cuma'yı sorar.
        """
        from src import otonom
        self._kur(con, cfg, ["2026-08-27", "2026-08-28"],
                  analiz_gunu="2026-08-28", kosu_gunu="2026-08-28",
                  kosu_baslangic="2026-08-28T16:40:00+00:00")
        self._takvim(monkeypatch, "2026-08-28")               # Cuma
        n = otonom.nobetci(cfg, con, bugun_tr="2026-08-30",   # PAZAR
                           simdi=datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc))
        assert n["beklenen_seans"] == "2026-08-28"
        assert not n["sessiz"] and not n["analizsiz"] and n["satirlar"] == []


    def test_llm_kapaliyken_analiz_yoklugu_alarm_degil(self, cfg, con, monkeypatch):
        self._kur(con, cfg, ["2026-08-28"], kosu_gunu="2026-08-28")
        self._takvim(monkeypatch, "2026-08-28")
        n = otonom.nobetci(cfg, con, analist_bekleniyor=False)
        assert n["son_analiz"] is None
        assert n["beklenen_hisse"] == 1
        assert not n["analizsiz"] and not n["verisiz"] and not n["sessiz"]
        assert n["satirlar"] == [] and "LLM kapalı" in n["not"]

    def test_llm_kapaliyken_tek_taze_hisse_eksik_evreni_gizlemez(self, cfg, con, monkeypatch):
        from tests.conftest import add_universe, add_bars
        self._kur(con, cfg, ["2026-08-28"], kosu_gunu="2026-08-28")
        add_universe(con, "BBB")
        add_bars(con, "BBB", [("2026-08-27", 10., 11., 9., 10., 1000., 10.)])
        self._takvim(monkeypatch, "2026-08-28")
        n = otonom.nobetci(cfg, con, analist_bekleniyor=False)
        assert n["son_bar"] == n["beklenen_seans"]
        assert n["verisiz"] and n["eksik_hisseler"] == ["BBB"]
        assert "1/2" in n["satirlar"][0]

    def test_llm_kapaliyken_bos_evren_ve_baslamayan_kosu_alarm(self, cfg, con, monkeypatch):
        self._takvim(monkeypatch, "2026-08-28")
        n = otonom.nobetci(cfg, con, analist_bekleniyor=False)
        assert n["verisiz"] and n["sessiz"]
        assert any("evren boş" in s for s in n["satirlar"])


# ============================================================ haftalık IC
class TestHaftalikIC:
    """YAPI EŞLİĞİ (AGENTS §12.2): üreticinin anahtarları ile tüketicininki.

    ⚠ NE OLMUŞTU (2026-08-15 denetimi): `otonom.haftalik` `ic.get("n")` ve
    `ic.get("ort")` okuyordu; `stats.ic_summary` ise `n_donem` ve `ic_ort`
    döndürür. `.get` SESSİZDİR — KeyError yok, `if ic.get("n"):` daima False,
    satır hiç basılmıyordu. Telegram geçmişindeki iki haftalık mesajın
    (2026-08-02, 08-09) ikisinde de IC yok; sebebi veri değil anahtar adıydı.

    Pahalı olan yanı: dönem-içi IC, PROJECT.md'nin İKİNCİ başarı kriteridir
    ve düzenli okunan tek kanal Telegram'dır. `report.py` aynı sözlükten
    DOĞRU anahtarları okuyordu — yani iki tüketiciden biri yanlıştı ve
    ayrışma kimseye görünmedi (L-022'nin kardeşi).

    Bu test `ic` sözlüğünü ELDE KURMAZ; gerçek `stats.ic_summary`'den üretir.
    Anahtar adı üretici tarafında değişirse test kırılır — kilidin şartı bu.
    """

    @pytest.fixture
    def _sahte_olcum(self, monkeypatch):
        from src import evaluate, stats

        ic = stats.ic_summary([0.10, 0.22, -0.05, 0.14])   # GERÇEK üretici
        alfa = stats.dist_stats([1.0, -2.0, 3.5])
        alfa.update(hukum="ölçüm yetersiz (N=3)", n_karar=5, n_girmeyen=2,
                    ort_karar_basina=0.9, xu100_ort=1.2)
        # `evaluate._tek`'in gerçekte doldurduğu alanlar — fixture ondan
        # ayrışırsa test kendi kurgusunu doğrular, kodu değil (L-012).
        bos_hukumlu = dict(stats.dist_stats([]), hukum="ölçüm yok")
        sonuc = {"tool": "gemini-3.5-flash", "alfa": alfa, "ic": ic,
                 "llm_katkisi": dict(bos_hukumlu),
                 "veto": {"veto_sayisi": 0, "veto_kodlari": {},
                          "secilen_ort_alfa": None, "not": ""},
                 "boyutlandirma": dict(bos_hukumlu, **{"not": ""}),
                 "brier": {"n": 0, "brier": None, "hukum": "ölçüm yok",
                           "kovalar": [], "not": ""},
                 "slippage": stats.dist_stats([]),
                 "taksonomi": {"sonuc": {}, "hata_etiketi": {},
                               "tetiklenmeme_orani": None, "toplam": 0},
                 "donem_yil": 12.6}
        monkeypatch.setattr(evaluate, "araclar", lambda con: {"gemini-3.5-flash": 5})
        monkeypatch.setattr(evaluate, "run", lambda cfg, con, tool=None: sonuc)
        return ic

    def test_IC_satiri_TELEGRAMA_basilir(self, cfg, con, monkeypatch,
                                         sessiz_telegram, _sahte_olcum):
        otonom.haftalik(cfg, con)
        assert sessiz_telegram, "haftalık özet gönderilmedi"
        ozet = sessiz_telegram[0]
        assert "IC " in ozet, (
            "haftalık özette IC satırı YOK — `ic_summary`'nin anahtarları ile "
            "`otonom.haftalik`'ın okudukları ayrışmış olabilir")
        assert f"N={_sahte_olcum['n_donem']} dönem" in ozet

    def test_IC_DEGERI_dogru_anahtardan_geliyor(self, cfg, con, monkeypatch,
                                                sessiz_telegram, _sahte_olcum):
        """Satırın basılması yetmez: basılan SAYI `ic_ort` olmalı.

        `ic.get("ort")` None döndürüp `_say` onu `—` bassaydı satır yine
        görünürdü — "IC —" bir ölçüm değil, bir arıza kaydıdır.
        """
        otonom.haftalik(cfg, con)
        beklenen = f"{_sahte_olcum['ic_ort']:.3f}"
        assert f"IC {beklenen}" in sessiz_telegram[0]
        assert "IC —" not in sessiz_telegram[0]

    def test_IC_OLCULEMEDIYSE_satir_BASILMAZ(self, cfg, con, monkeypatch,
                                             sessiz_telegram):
        """Boş ölçüm `IC —` diye basılmaz; hiç basılmaz (`—` yanıltır)."""
        from src import evaluate, stats

        bos = {"tool": "x", "alfa": stats.dist_stats([]),
               "ic": stats.ic_summary([]), "llm_katkisi": stats.dist_stats([]),
               "veto": {}, "boyutlandirma": stats.dist_stats([]),
               "brier": {"n": 0, "brier": None, "hukum": "ölçüm yok",
                         "kovalar": [], "not": ""},
               "slippage": stats.dist_stats([]),
               "taksonomi": {"sonuc": {}, "hata_etiketi": {},
                             "tetiklenmeme_orani": None, "toplam": 0},
               "donem_yil": 12.6}
        monkeypatch.setattr(evaluate, "araclar", lambda con: {"x": 1})
        monkeypatch.setattr(evaluate, "run", lambda cfg, con, tool=None: bos)

        otonom.haftalik(cfg, con)
        assert "IC " not in sessiz_telegram[0]


# ============================================================ kâğıt portföy
class TestKagitPortfoy:
    """ADR #019 — portföy zincire eklendi; DÜŞERSE rapor yine üretilmeli.

    Yeni bir adım eklerken sorulacak ilk soru bu: kritiklik sınıfı ne?
    Portföy TÜREV bir görünümdür — hesaplanamaması veriye güvenilmediği
    anlamına GELMEZ. O yüzden `KRITIK_ADIMLAR`'da değil ve düşüşü raporu
    engellemez; yalnız o günün raporunda karne bölümü olmaz.
    """

    @pytest.fixture(autouse=True)
    def _islem_gunu(self, monkeypatch):
        from src.calendar_bist import BistCalendar
        monkeypatch.setattr(BistCalendar, "is_trading_day", lambda self, d: True)

    def test_portfoy_ADIMI_kosar(self, cfg, con, monkeypatch, sessiz_telegram):
        _adimlari_sahtele(monkeypatch)
        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29),
                              analist_calistir=False)
        assert "portfoy" in sonuc["adimlar"], "kâğıt portföy zincirde koşmuyor"
        assert "TL" in sonuc["adimlar"]["portfoy"]

    def test_portfoy_DUSERSE_rapor_yine_uretilir(self, cfg, con, monkeypatch,
                                                 sessiz_telegram):
        _adimlari_sahtele(monkeypatch)
        from src import portfoy as pfm
        monkeypatch.setattr(pfm, "simule", lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("portföy bilerek düştü")))

        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29),
                              analist_calistir=False)
        assert "portfoy" in sonuc["hatalar"]
        assert otonom.basarisiz_mi(sonuc) == [], "portföy düşüşü koşuyu kırdı"
        assert "rapor" in sonuc["adimlar"], "portföy düşünce rapor da üretilmedi"

    def test_TELEGRAM_ozetinde_TL_satiri(self, cfg, con, monkeypatch,
                                         sessiz_telegram):
        """Bildirimin en somut satırı: pp değil TL."""
        _adimlari_sahtele(monkeypatch)
        otonom.gunluk(cfg, con, bugun=date(2026, 7, 29), analist_calistir=False)
        assert sessiz_telegram
        assert "💼" in sessiz_telegram[0]
        assert "TL" in sessiz_telegram[0]


def _onceki_analiz_yaz(con, asof: str = "2026-07-29", ticker: str = "THYAO") -> None:
    """O `asof` için journal'da ZATEN bir karar seti varmış gibi yapar.

    Bar da yazılır: zincir `asof`u `MAX(bars_daily.date)`ten okur ve olayın
    KENDİSİ tam olarak buydu — bar ilerlemeyince `asof` yerinde saydı.
    """
    con.execute(
        "INSERT INTO bars_daily (ticker, date, c, c_tr, source, ingested_utc) "
        "VALUES (?,?,100.0,100.0,'test','x')", (ticker, asof))
    con.execute(
        "INSERT INTO llm_runs (run_id, asof, tool, bundle_sha, output_path, "
        "  audit_passed, hard_fail_codes, created_utc) "
        "VALUES (?,?,'onceki','sha','',1,'[]','x')",
        (f"{asof}-onceki-1", asof))
    con.execute(
        "INSERT INTO predictions (prediction_id, run_id, asof, ticker, "
        "  factor_set_version, weights_hash, indicator_set_version, regime, "
        "  signal, action, confidence, confidence_p, thesis, counter_scenario, "
        "  key_risk, falsifier, close_at_asof, created_utc) "
        "VALUES (?,?,?,?, 'v1','h','v1','neutral', 'hold','izle','dusuk',0.3, "
        "        't','c','k','f', 100.0, 'x')",
        (f"p-{asof}-{ticker}", f"{asof}-onceki-1", asof, ticker))
    con.commit()


class TestAyniGunIkiKezAnaliz:
    """B-16 KİLİDİ — journal'ın değişmezliği (ADR #014).

    ⚠ NE OLMUŞTU (2026-08-28 denetimi): 2026-08-27'nin planlı koşusu GitHub'da
    hiç görünmedi; sonraki koşu 08-28T01:05Z'de başladı (nominal saatten 8,5
    saat sapma, TAKVİM GÜNÜNÜ AŞTI). O anda `bars_daily` max hâlâ 2026-08-26
    idi, yani `asof = MAX(bars_daily.date)` ZATEN ANALİZ EDİLMİŞ bir günü
    gösterdi. Zincirde "bu gün zaten analiz edildi mi?" diye soran hiçbir yer
    yoktu: `journal.create_run` sessizce `-2` sonekiyle ikinci bir koşu açtı.

    Somut hasar: aynı `asof` için iki karar seti (18 ismin 12'sinde FARKLI
    karar — birinci koşu 0 plan seçti, ikincisi 2 pozisyon açtı),
    `reports/gunluk_2026-08-26.md` iki gün sonra üzerine yazıldı, o gün
    journal'a 17 veto girdi (10+7) ve `aktif_vetolar` tekrar sayacı şişti.

    Bu testler eski davranış geri konduğunda (kapı kaldırılınca) KIRMIZIYA
    döner — doğrulandı.
    """

    def _hazirla(self, monkeypatch):
        from src.calendar_bist import BistCalendar
        monkeypatch.setattr(BistCalendar, "is_trading_day", lambda self, d: True)
        return _adimlari_sahtele(monkeypatch)

    def _analist_sahtele(self, monkeypatch, cagrilan):
        """Analist koşarsa listeye yazsın — koşup koşmadığı TEK yerden okunur."""
        from src import analist

        def sahte(cfg, con, asof):
            cagrilan.append("analist")
            return {"model": "test-model", "denemeler": ["test-model"],
                    "out": {"tool": "test-model", "stocks": []}}

        monkeypatch.setattr(analist, "calistir", sahte)

    def test_ZATEN_analiz_edilmis_gun_YENIDEN_analiz_EDILMEZ(
            self, cfg, con, monkeypatch, sessiz_telegram):
        cagrilan = self._hazirla(monkeypatch)
        self._analist_sahtele(monkeypatch, cagrilan)

        # O `asof` için journal'da ZATEN bir kayıt var.
        _onceki_analiz_yaz(con)

        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29),
                              analist_calistir=True)

        assert "analist" not in cagrilan, \
            "zaten analiz edilmiş gün YENİDEN analiz edildi — journal değişmez olmalı"
        assert sonuc.get("analist_atlandi") == "zaten_analiz_edildi"
        n = con.execute("SELECT COUNT(*) FROM predictions "
                        "WHERE asof='2026-07-29'").fetchone()[0]
        assert n == 1, f"tahmin sayısı değişti: {n} (ikinci karar seti yazılmış)"
        # İkinci bir koşu kaydı da AÇILMAMALI.
        r = con.execute("SELECT COUNT(*) FROM llm_runs "
                        "WHERE asof='2026-07-29'").fetchone()[0]
        assert r == 1, f"aynı asof için {r} koşu kaydı var"

    def test_ANALIZSIZ_gun_normal_analiz_EDILIR(self, cfg, con, monkeypatch,
                                                sessiz_telegram):
        """Kapı fazla katı olmasın: hiç analiz edilmemiş gün KOŞMALI.

        Bu testin varlığı bilinçli — L-016'nın dersi, bir kapının
        gereğinden fazlasını durdurmasının kilitlenme ürettiğidir.
        """
        cagrilan = self._hazirla(monkeypatch)
        self._analist_sahtele(monkeypatch, cagrilan)

        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29),
                              analist_calistir=True)

        assert "analist" in cagrilan, "temiz günde analist hiç koşmadı"
        assert "analist_atlandi" not in sonuc

    def test_kapi_ZINCIRI_DURDURMAZ(self, cfg, con, monkeypatch, sessiz_telegram):
        """AGENTS §12a: bu bir GÖZLEM, kapı değil — atlar, DURDURMAZ.

        Zincirin geri kalanı (çözüm, rapor, Telegram) koşmaya devam etmeli;
        aksi halde bir cron gecikmesi o günün raporunu da yok ederdi.
        """
        cagrilan = self._hazirla(monkeypatch)
        self._analist_sahtele(monkeypatch, cagrilan)
        _onceki_analiz_yaz(con)

        sonuc = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29),
                              analist_calistir=True)

        assert "coz" in cagrilan, "analist atlanınca çözüm adımı da koşmadı"
        assert "rapor" in sonuc["adimlar"], "analist atlanınca rapor üretilmedi"
        assert otonom.basarisiz_mi(sonuc) == [], "atlama koşuyu BAŞARISIZ yaptı"
        assert sessiz_telegram, "analist atlanınca bildirim hiç gitmedi"
