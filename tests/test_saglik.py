"""Sağlık kontrolü — mekanizma testleri.

Bu modül Faz 8'de `cli.cmd_saglik`'ten çıkarıldı (katman disiplini: otonom koşu
CLI'ı import edemez). Buradaki asıl test **bar tazeliği**: otomasyonun tek
gerçek dış-dünya kontrolü odur.
"""

from __future__ import annotations

from datetime import date

import pytest

from src import saglik as sag
from tests.conftest import add_universe


def _veri_kur(con, cfg, tarihler: list[str], ticker="THYAO"):
    """bars + indicator + data_quality + universe — kontrollerin beklediği asgari."""
    from src import db

    add_universe(con, ticker, sector="ulasim")
    db.upsert_many(
        con, "bars_daily",
        ["ticker", "date", "o", "h", "l", "c", "v", "c_tr", "turnover_try",
         "source", "ingested_utc"],
        [(ticker, d, 10.0, 11.0, 9.0, 10.0, 1000.0, 10.0, 1e9, "test", "now")
         for d in tarihler])
    db.upsert_many(
        con, "indicator_daily", ["ticker", "date", "set_version", "computed_utc"],
        [(ticker, d, cfg["gostergeler"]["set_version"], "now") for d in tarihler])
    db.upsert_many(
        con, "data_quality", ["ticker", "date", "ok"],
        [(ticker, tarihler[-1], 1)])


class TestBarTazeligi:
    """⚠ NE OLURDU: 1-3. kontroller göstergeyi/kaliteyi `MAX(bars_daily.date)`e
    kıyaslıyor. Barlar bayatlarsa `asof` da bayatlar ve HEPSİ tutarlı görünür —
    kontroller birbirini doğrular, hiçbiri dış dünyaya bakmaz. Otomasyonda
    karşılığı: veri gelmediği gün DÜNKÜ rapor bugünmüş gibi bildirilir."""

    def test_bir_seans_geride_UYARI(self, cfg, con, monkeypatch):
        from src.calendar_bist import BistCalendar
        _veri_kur(con, cfg, ["2026-07-29", "2026-07-30"])
        monkeypatch.setattr(BistCalendar, "last_closed_session",
                            lambda self, ts=None: date(2026, 7, 31))
        monkeypatch.setattr(BistCalendar, "trading_days_between",
                            lambda self, a, b: 1)

        s = sag.kontrol(cfg, con)
        satir = [b for b in s["bulgular"] if b[1] == "bar tazeliği"][0]
        assert satir[0] == sag.UYARI
        assert "1 seans geride" in satir[2]
        # Not: koşunun TOPLAM çıkış kodu burada iddia EDİLMEZ — minimal
        # fixture'da başka kontroller de düşer ve test o gürültüye bağlanırdı.
        # Çıkış kodu mantığının kendi testi var (TestCikisKodu).

    def test_iki_seans_geride_KRITIK(self, cfg, con, monkeypatch):
        """Bir seans gecikme olağan (yfinance), iki seans değil."""
        from src.calendar_bist import BistCalendar
        _veri_kur(con, cfg, ["2026-07-29", "2026-07-30"])
        monkeypatch.setattr(BistCalendar, "last_closed_session",
                            lambda self, ts=None: date(2026, 8, 3))
        monkeypatch.setattr(BistCalendar, "trading_days_between",
                            lambda self, a, b: 2)

        s = sag.kontrol(cfg, con)
        satir = [b for b in s["bulgular"] if b[1] == "bar tazeliği"][0]
        assert satir[0] == sag.KRITIK

    def test_guncelse_OK(self, cfg, con, monkeypatch):
        from src.calendar_bist import BistCalendar
        _veri_kur(con, cfg, ["2026-07-29", "2026-07-30"])
        monkeypatch.setattr(BistCalendar, "last_closed_session",
                            lambda self, ts=None: date(2026, 7, 30))
        monkeypatch.setattr(BistCalendar, "trading_days_between",
                            lambda self, a, b: 0)

        s = sag.kontrol(cfg, con)
        satir = [b for b in s["bulgular"] if b[1] == "bar tazeliği"][0]
        assert satir[0] == sag.OK


class TestCikisKodu:
    """0 temiz · 1 uyarı · 2 KRİTİK — otomasyonun kapısı bu sayı."""

    def test_kritik_2_dondurur(self):
        assert sag.cikis_kodu({"kritik": [("K", "a", "b")], "uyari": []}) == 2

    def test_yalniz_uyari_1_dondurur(self):
        assert sag.cikis_kodu({"kritik": [], "uyari": [("U", "a", "b")]}) == 1

    def test_temiz_0_dondurur(self):
        assert sag.cikis_kodu({"kritik": [], "uyari": []}) == 0

    def test_kritik_uyariyi_EZER(self):
        assert sag.cikis_kodu({"kritik": [("K", "a", "b")],
                               "uyari": [("U", "c", "d")]}) == 2


class TestTekSatir:
    """Telegram özetine giren hâl — kritik varsa SEBEBİ de görünmeli."""

    def test_kritikte_ad_ve_mesaj_gorunur(self):
        t = sag.tek_satir({"kritik": [(sag.KRITIK, "gösterge tazeliği", "bayat")],
                           "uyari": []})
        assert "🛑" in t and "gösterge tazeliği" in t and "bayat" in t

    def test_uyarida_sayi(self):
        t = sag.tek_satir({"kritik": [], "uyari": [("U", "a", "b"), ("U", "c", "d")]})
        assert "2 uyarı" in t

    def test_temizde_kisa(self):
        assert sag.tek_satir({"kritik": [], "uyari": []}) == "✓ Sağlık temiz"


class TestGostergeKapsamasi:
    def test_eksik_gosterge_KRITIK(self, cfg, con):
        """L-009: gösterge kapsaması düşerse kesitsel yüzdelik sessizce daralır."""
        from src import db
        _veri_kur(con, cfg, ["2026-07-30"], ticker="THYAO")
        # Göstergesi OLMAYAN ikinci bir ticker ekle
        db.upsert_many(
            con, "bars_daily",
            ["ticker", "date", "o", "h", "l", "c", "v", "c_tr", "turnover_try",
             "source", "ingested_utc"],
            [("AKBNK", "2026-07-30", 10.0, 11.0, 9.0, 10.0, 1000.0, 10.0,
              1e9, "test", "now")])

        s = sag.kontrol(cfg, con)
        satir = [b for b in s["bulgular"] if b[1] == "gösterge kapsaması"][0]
        assert satir[0] == sag.KRITIK
        assert "1/2" in satir[2]


class TestBicimleme:
    def test_bicimle_tum_bulgulari_basar(self, cfg, con):
        _veri_kur(con, cfg, ["2026-07-30"])
        s = sag.kontrol(cfg, con)
        metin = sag.bicimle(s)
        for _, ad, _ in s["bulgular"]:
            assert ad in metin
