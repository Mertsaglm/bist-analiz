"""İşlem takvimi testleri.

Takvimin iki ayrı rejimi var ve sınır kritik:
  * sol taraf (endeks barı olan tarihler) → OTORİTER
  * sağ taraf (gelecek)                   → tatil listesiyle TAHMİNİ
Karıştırmak zaman bariyerlerini kaydırır ve bu hata sessizdir.
"""

from __future__ import annotations

from datetime import date

import pytest

from src import util
from src.calendar_bist import BistCalendar
from tests.conftest import add_index


@pytest.fixture
def cal(cfg, con):
    # 2026-01-05..09 (Pzt-Cum) ve 12..13; 07 kapalı (sentetik tatil)
    add_index(con, "XU100", ["2026-01-05", "2026-01-06", "2026-01-08",
                             "2026-01-09", "2026-01-12", "2026-01-13"])
    return BistCalendar(cfg, con)


class TestGunSorgulari:
    def test_bar_olan_gun_islem_gunu(self, cal):
        assert cal.is_trading_day(date(2026, 1, 5))

    def test_bar_olmayan_gun_kapali(self, cal):
        """07 Ocak hafta içi ama endekste barı yok → kapalı. OTORİTER karar."""
        assert not cal.is_trading_day(date(2026, 1, 7))
        assert cal.is_derived(date(2026, 1, 7))

    def test_hafta_sonu_kapali(self, cal):
        assert not cal.is_trading_day(date(2026, 1, 10))   # Cumartesi
        assert not cal.is_trading_day(date(2026, 1, 11))   # Pazar

    def test_gelecek_tahmini(self, cal):
        """Sınırın sağında bar yok → tatil listesi + hafta sonu kuralı."""
        ileri = date(2026, 3, 3)                            # Salı, tatil değil
        assert not cal.is_derived(ileri)
        assert cal.is_trading_day(ileri)

    def test_gelecekteki_tatil_kapali(self, cal):
        """23 Nisan 2026 Perşembe — holidays_tr.yaml'de tam gün tatil."""
        assert not cal.is_trading_day(date(2026, 4, 23))

    def test_yarim_gun_islem_gunudur(self, cal):
        """Arife: bar OLUŞUR, seans kısadır → takvim aritmetiğinde SAYILIR."""
        arife = date(2026, 3, 19)
        assert cal.is_half_day(arife)
        assert cal.is_trading_day(arife)


class TestAritmetik:
    def test_ekleme_ve_fark_tersine_donusumlu(self, cal):
        d = date(2026, 1, 5)
        for n in (1, 2, 3, 5):
            hedef = cal.add_trading_days(d, n)
            assert cal.trading_days_between(d, hedef) == n

    def test_kapali_gunu_atlar(self, cal):
        """05 → +2: 06 (1), 07 kapalı atlanır, 08 (2)."""
        assert cal.add_trading_days(date(2026, 1, 5), 2) == date(2026, 1, 8)

    def test_hafta_sonunu_atlar(self, cal):
        """09 Cuma → +1 = 12 Pazartesi."""
        assert cal.add_trading_days(date(2026, 1, 9), 1) == date(2026, 1, 12)

    def test_negatif_geriye_gider(self, cal):
        assert cal.add_trading_days(date(2026, 1, 8), -2) == date(2026, 1, 5)

    def test_sifir_ayni_gun(self, cal):
        assert cal.add_trading_days(date(2026, 1, 7), 0) == date(2026, 1, 7)

    def test_fark_ters_yonde_negatif(self, cal):
        assert cal.trading_days_between(date(2026, 1, 8), date(2026, 1, 5)) == -2

    def test_ayni_gun_sifir(self, cal):
        assert cal.trading_days_between(date(2026, 1, 5), date(2026, 1, 5)) == 0

    def test_next_prev_inclusive(self, cal):
        assert cal.next_trading_day(date(2026, 1, 7)) == date(2026, 1, 8)
        assert cal.prev_trading_day(date(2026, 1, 7)) == date(2026, 1, 6)
        assert cal.next_trading_day(date(2026, 1, 8), inclusive=True) == date(2026, 1, 8)
        assert cal.prev_trading_day(date(2026, 1, 8), inclusive=True) == date(2026, 1, 8)

    def test_trading_days_listesi(self, cal):
        g = cal.trading_days(date(2026, 1, 5), date(2026, 1, 9))
        assert [d.isoformat() for d in g] == [
            "2026-01-05", "2026-01-06", "2026-01-08", "2026-01-09"]


class TestSeans:
    def test_seans_durumlari(self, cal):
        """Seans saatleri config'ten okunur — koda gömülmez."""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/Istanbul")

        def durum(saat, dakika, gun=5):
            ts = datetime(2026, 1, gun, saat, dakika, tzinfo=tz)
            return cal.session_state(ts.astimezone(ZoneInfo("UTC")))

        assert durum(8, 0) == "kapali"
        assert durum(9, 45) == "acilis_muzayede"
        assert durum(12, 0) == "surekli_islem"     # öğle arası YOK (2016'da kaldırıldı)
        assert durum(18, 5) == "kapanis_muzayede"
        assert durum(19, 0) == "sonrasi"
        assert durum(12, 0, gun=10) == "kapali"    # Cumartesi

    def test_last_closed_session_acik_seansi_kullanmaz(self, cal):
        """Kapanmamış seansın barı değişebilir; onu kullanmak look-ahead'dir."""
        from datetime import datetime
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Europe/Istanbul")

        ogle = datetime(2026, 1, 8, 12, 0, tzinfo=tz).astimezone(ZoneInfo("UTC"))
        assert cal.last_closed_session(ogle) == date(2026, 1, 6)

        aksam = datetime(2026, 1, 8, 19, 0, tzinfo=tz).astimezone(ZoneInfo("UTC"))
        assert cal.last_closed_session(aksam) == date(2026, 1, 8)


class TestGercekTakvim:
    def test_2026_takvimi_tatil_listesiyle_birebir(self, real_con, real_cfg):
        """Türetilmiş takvim ile tatil listesi ÇELİŞMEMELİ.

        Bu testin asıl işi hayalet bar regresyonunu yakalamak: Yahoo tekrar
        tatil barı üretmeye başlarsa buradaki fark açılır.
        """
        cal = BistCalendar(real_cfg, real_con)
        if cal.son_bar is None or cal.son_bar.year < 2026:
            pytest.skip("2026 verisi yok")

        hol = util.load_yaml(real_cfg["paths"]["holidays_file"])
        tatil = {str(d) for y in hol["tam_gun"].values() for d in y}

        from datetime import timedelta
        d, kapali = date(2026, 1, 1), []
        while d <= cal.son_bar:
            if d.weekday() < 5 and not cal.is_trading_day(d):
                kapali.append(d.isoformat())
            d += timedelta(days=1)

        assert set(kapali) <= tatil, (
            f"Tatil listesinde OLMAYAN kapalı hafta içi günler: "
            f"{sorted(set(kapali) - tatil)} — ya endeks verisi eksik ya liste eski")
