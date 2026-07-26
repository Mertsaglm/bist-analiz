"""Emir mekaniği testleri.

Fiyat adımı tablosu KENDİ VERİMİZDEN ölçüldü (config.yaml). Bu testler o
tablonun sınırlarını ve yuvarlama YÖNÜNÜ sabitler — yön yanlışsa her backtest
sistematik olarak iyimser olur.
"""

from __future__ import annotations

import pytest

from src import risk


class TestTickSize:
    @pytest.mark.parametrize("fiyat,beklenen", [
        (0.50, 0.01), (10.00, 0.01), (19.98, 0.01), (19.99, 0.01),
        (20.00, 0.02), (30.00, 0.02), (49.98, 0.02),
        (50.00, 0.05), (99.95, 0.05),
        (100.00, 0.10), (249.90, 0.10),
        (250.00, 0.25), (499.75, 0.25),
        (500.00, 0.50), (999.50, 0.50),
        (1000.00, 1.00), (5000.00, 1.00),
    ])
    def test_bant_sinirlari(self, cfg, fiyat, beklenen):
        assert risk.tick_size(fiyat, cfg) == beklenen

    def test_sinir_gecisleri(self, cfg):
        """19.99 → 20.00 → 20.01 geçişi: kritik sınır."""
        assert risk.tick_size(19.99, cfg) == 0.01
        assert risk.tick_size(20.00, cfg) == 0.02
        assert risk.tick_size(20.01, cfg) == 0.02


class TestYuvarlama:
    def test_stop_asagi_yuvarlanir(self, cfg):
        """Aşağı yuvarlamak stop'u UZAKLAŞTIRIR → gürültüyle erken tetiklenme azalır."""
        assert risk.round_to_tick(47.3183, cfg, "down") == pytest.approx(47.30)

    def test_hedef_yukari_yuvarlanir(self, cfg):
        """Yukarı yuvarlamak hedefi ZORLAŞTIRIR → iyimserliğe değil kötümserliğe."""
        assert risk.round_to_tick(47.3183, cfg, "up") == pytest.approx(47.32)

    def test_nearest(self, cfg):
        # 47.32 bandında adım 0.02 (20-49.98 bandı)
        assert risk.round_to_tick(47.319, cfg, "nearest") == pytest.approx(47.32)
        assert risk.round_to_tick(47.329, cfg, "nearest") == pytest.approx(47.32)
        # 50-99.95 bandında adım 0.05
        assert risk.round_to_tick(77.77, cfg, "nearest") == pytest.approx(77.75)

    @pytest.mark.parametrize("fiyat", [5.234, 19.999, 20.001, 33.333, 77.77,
                                       123.456, 300.33, 777.7, 1234.5])
    def test_her_zaman_izgarada(self, cfg, fiyat):
        for mod in ("down", "up", "nearest"):
            s = risk.round_to_tick(fiyat, cfg, mod)
            assert risk.on_tick_grid(s, cfg), f"{fiyat} → {s} ızgarada değil ({mod})"

    def test_yon_korunur(self, cfg):
        for fiyat in (5.234, 33.333, 123.456, 300.33):
            assert risk.round_to_tick(fiyat, cfg, "down") <= fiyat
            assert risk.round_to_tick(fiyat, cfg, "up") >= fiyat

    def test_izgaradaki_fiyat_degismez(self, cfg):
        assert risk.round_to_tick(47.30, cfg, "down") == pytest.approx(47.30)
        assert risk.round_to_tick(47.30, cfg, "up") == pytest.approx(47.30)

    @pytest.mark.parametrize("kotu", [0, -5, None, float("nan")])
    def test_gecersiz_fiyat_patlar(self, cfg, kotu):
        with pytest.raises(ValueError):
            risk.round_to_tick(kotu, cfg)

    def test_bilinmeyen_mod_patlar(self, cfg):
        with pytest.raises(ValueError):
            risk.round_to_tick(10.0, cfg, "saçma")


class TestGunlukLimit:
    def test_band(self, cfg):
        alt, ust = risk.daily_limit_band(100.0, cfg)
        assert alt == pytest.approx(90.0)
        assert ust == pytest.approx(110.0)

    def test_uzak_stop_tek_gunde_ulasilamaz(self, cfg):
        """ATR'ye göre %12 uzaktaki stop bir günde TETİKLENEMEZ.

        Resolver bunu bilmezse limit-down günlerinde gerçekleşmeyen bir stop'u
        gerçekleşmiş sayar.
        """
        assert not risk.reachable_in_one_day(100.0, 88.0, cfg)
        assert risk.reachable_in_one_day(100.0, 92.0, cfg)


class TestPozisyonBoyutu:
    """DİKKAT: mevcut ayarlarla (risk %1, tavan %10) stop mesafesi %10'un
    altındaki her planda TAVAN BAĞLAR. Volatilite hedeflemesini test etmek için
    tavanı aşmayan (geniş) stoplar kullanılmalı — aksi halde test, formülü
    değil tavanı ölçer."""

    def test_tavan_tipik_stoplarda_baglar(self, cfg):
        """Bilinçli muhafazakârlık: %5 stop → formül %20 der, tavan %10'a çeker."""
        b = risk.position_size_pct(entry=100.0, stop=95.0, cfg=cfg)
        assert b == pytest.approx(cfg["risk"]["maks_pozisyon_pct"])
        kayip = risk.max_loss_pct_of_portfolio(
            entry=100.0, stop=95.0, position_size_pct_=b)
        assert kayip < cfg["risk"]["pozisyon_basi_risk_pct"]   # risk BÜTÇENİN ALTINDA

    def test_genis_stop_kucuk_pozisyon(self, cfg):
        """Tavanın bağlamadığı bölgede volatilite hedeflemesi çalışır."""
        dar = risk.position_size_pct(entry=100.0, stop=85.0, cfg=cfg)     # %15 stop
        genis = risk.position_size_pct(entry=100.0, stop=75.0, cfg=cfg)   # %25 stop
        assert dar > genis

    def test_risk_sabit_kalir(self, cfg):
        """Tavan bağlamadığı sürece portföy riski stop mesafesinden BAĞIMSIZ."""
        for stop in (85.0, 80.0, 75.0):
            b = risk.position_size_pct(entry=100.0, stop=stop, cfg=cfg)
            kayip = risk.max_loss_pct_of_portfolio(
                entry=100.0, stop=stop, position_size_pct_=b)
            assert kayip == pytest.approx(cfg["risk"]["pozisyon_basi_risk_pct"], abs=0.02)

    def test_tavan_asilmaz(self, cfg):
        assert risk.position_size_pct(entry=100.0, stop=99.9, cfg=cfg) \
            <= cfg["risk"]["maks_pozisyon_pct"]

    def test_rejim_carpani(self, cfg):
        tam = risk.position_size_pct(entry=100.0, stop=85.0, cfg=cfg,
                                     regime_multiplier=1.0)
        kisik = risk.position_size_pct(entry=100.0, stop=85.0, cfg=cfg,
                                       regime_multiplier=0.4)
        assert kisik == pytest.approx(tam * 0.4, rel=0.01)

    def test_yuksek_risk_tier_yarim_boy(self, cfg):
        normal = risk.position_size_pct(entry=100.0, stop=85.0, cfg=cfg)
        riskli = risk.position_size_pct(entry=100.0, stop=85.0, cfg=cfg,
                                        tier="yuksek_risk")
        assert riskli == pytest.approx(normal * 0.5, rel=0.01)

    def test_gecersiz_stop_patlar(self, cfg):
        with pytest.raises(ValueError):
            risk.position_size_pct(entry=100.0, stop=100.0, cfg=cfg)
        with pytest.raises(ValueError):
            risk.position_size_pct(entry=100.0, stop=105.0, cfg=cfg)


class TestRR:
    def test_giris_ustunden_hesaplanir(self):
        """Orta noktadan hesaplamak R:R'ı sistematik olarak İYİMSER gösterir."""
        assert risk.rr(entry_high=100.0, stop=90.0, target=120.0) == pytest.approx(2.0)

    def test_negatif_risk_none(self):
        assert risk.rr(entry_high=100.0, stop=100.0, target=120.0) is None

    def test_stop_atr_katsayisi(self):
        assert risk.stop_atr_multiple(100.0, 90.0, 5.0) == pytest.approx(2.0)
        assert risk.stop_atr_multiple(100.0, 90.0, 0) is None
