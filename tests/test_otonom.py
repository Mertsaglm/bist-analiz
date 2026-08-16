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

from datetime import date

import pytest

from src import otonom, saglik as sag


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

    from src import indicators, llm_io, news, prices, resolver

    def kaydet(ad, deger):
        def f(*a, **k):
            cagrilan.append(ad)
            if ad in dusen:
                raise RuntimeError(f"{ad} bilerek düştü")
            return deger
        return f

    monkeypatch.setattr(prices, "daily", kaydet(
        "veri", {"tickers": 70, "hayalet_silinen": 0, "yarim_bar_silinen": 0,
                 "kalite_gecmeyen": 1, "start": "2026-07-14"}))
    # ⚠ Sahtelenmezse GERÇEK `sync_indices` koşar ve test ağa çıkar; adım
    # kritik olmadığı için hata sessizce yutulur ve suite yavaşlar.
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
        assert otonom.KRITIK_ADIMLAR == ("veri", "gosterge", "saglik", "rapor")
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
    """⚠ Gözcünün yapabileceği EN KÖTÜ hata: alarm vermesi gereken anda
    "temiz" demek. Bu sınıf tam olarak onu kilitler.

    İlk sürüm `son_analiz`i `son_bar`la karşılaştırıyordu. İkisi de günlük
    koşunun ürünüdür: koşu hiç olmazsa yeni bar da girmez, analiz de yazılmaz
    ve fark 0 çıkar — iki BAYAT sayı birbirini doğrular. L-010'un aynen
    tekrarı: *"kontroller birbirini doğruluyorsa hiçbiri dış dünyaya
    bakmıyordur."* Referans artık TAKVİM (`last_closed_session`), yani koşuya
    bağlı olmayan tek şey.
    """

    @staticmethod
    def _kur(con, cfg, bar_gunleri, analiz_gunu=None, kosu_gunu=None):
        from src import db, journal
        from tests.conftest import add_bars, add_index, add_universe
        add_universe(con, "AAA")
        add_bars(con, "AAA", [(d, 10.0, 11.0, 9.0, 10.0, 1000.0, 10.0)
                              for d in bar_gunleri])
        add_index(con, "XU100", bar_gunleri)
        if kosu_gunu:
            journal.kosu_bitir(
                con, journal.kosu_basla(cfg, con, tur="gunluk",
                                        tarih_tr=kosu_gunu), durum="tamam")
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
        assert not n["sessiz"] and n["satirlar"] == []

    def test_bugun_KOSU_YOKSA_alarm(self, cfg, con, monkeypatch):
        """2026-08-06 vakası: iş hiç başlamadı, o gün tamamen sessizdi."""
        from src import otonom
        from tests.conftest import is_gunleri
        g = is_gunleri(4, "2026-08-03")
        self._kur(con, cfg, g, analiz_gunu=g[-2], kosu_gunu=g[-2])
        self._takvim(monkeypatch, g[-1])
        n = otonom.nobetci(cfg, con, bugun_tr=g[-1])
        assert n["sessiz"]
        assert any("KAYDI YOK" in s for s in n["satirlar"])

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

    def test_kosu_BASLAYIP_bitmemisse_alarm(self, cfg, con, monkeypatch):
        """`durum='kosuyor'` kalması bilgidir: süreç bitmeden ölmüş."""
        from src import journal, otonom
        from tests.conftest import is_gunleri
        g = is_gunleri(4, "2026-08-03")
        self._kur(con, cfg, g, analiz_gunu=g[-1])
        journal.kosu_basla(cfg, con, tur="gunluk", tarih_tr=g[-1])   # bitirilmedi
        self._takvim(monkeypatch, g[-1])
        n = otonom.nobetci(cfg, con, bugun_tr=g[-1])
        assert n["sessiz"] and any("bitmedi" in s for s in n["satirlar"])

    def test_islem_gunu_degilse_KOSU_BEKLENMEZ(self, cfg, con, monkeypatch):
        from src import otonom
        from src.calendar_bist import BistCalendar
        from tests.conftest import is_gunleri
        g = is_gunleri(4, "2026-08-03")
        self._kur(con, cfg, g, analiz_gunu=g[-1], kosu_gunu=g[-1])
        monkeypatch.setattr(BistCalendar, "is_trading_day", lambda s, d: False)
        n = otonom.nobetci(cfg, con, bugun_tr="2026-08-08")
        assert not n["sessiz"] and "işlem günü değil" in n["not"]


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
