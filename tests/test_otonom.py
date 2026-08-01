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
        "veri", {"tickers": 70, "hayalet_silinen": 0, "kalite_gecmeyen": 1,
                 "start": "2026-07-14"}))
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
