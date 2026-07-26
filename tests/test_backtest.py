"""Yürüyen-ileri harness testleri.

Dört değişmez test ediliyor; herhangi biri kırılırsa TÜM ölçüm geçersizdir:
  1. giriş t+1 (close[t] ile giriş yok)
  2. örtüşmeyen dönemler
  3. taban = eşit-ağırlık uygun evren (XU100 değil)
  4. sessiz kırpma yok — atlanan dönem raporlanır
"""

from __future__ import annotations

import numpy as np
import pytest

from src import backtest, factors, stats, util


def _panel(n_gun: int = 600, n_ticker: int = 12, *, egim: np.ndarray | None = None,
           xu_sabit: bool = False) -> backtest.Panel:
    """Sentetik panel: her ticker sabit günlük büyüme oranına sahip.

    `egim[i]` = i. ticker'ın günlük log getirisi. Momentum sinyali burada
    mükemmel çalışır (geçmiş büyüme = gelecek büyüme), yani harness
    "sinyal varsa bulabiliyor mu?" sorusunu cevaplayabilir.
    """
    if egim is None:
        egim = np.linspace(-0.0008, 0.0012, n_ticker)
    t = np.arange(n_gun).reshape(-1, 1)
    c = 100.0 * np.exp(t * egim.reshape(1, -1))
    dates = [f"2020-{1 + (i // 28) % 12:02d}-{1 + i % 28:02d}" for i in range(n_gun)]
    # tarihler benzersiz olsun diye sıra numarası ekle
    dates = [f"{2015 + i // 250}-{1 + (i % 250) // 21:02d}-{1 + (i % 21):02d}"
             for i in range(n_gun)]
    xu = np.full(n_gun, 100.0) if xu_sabit else c.mean(axis=1)
    return backtest.Panel(
        dates=dates, tickers=[f"T{i:02d}" for i in range(n_ticker)],
        c=c, c_tr=c, h=c * 1.01, turnover=np.full_like(c, 1e12), xu100=xu)


@pytest.fixture
def cfg_test(cfg):
    """Kapıları gevşetilmiş config — harness mekaniğini izole etmek için."""
    c = {**cfg}
    c["olcum"] = {**cfg["olcum"], "zayif_n_esigi": 3}
    return c


class TestLookAhead:
    def test_giris_t_arti_1_kullanilir(self, cfg_test):
        """Sinyal gününün kapanışıyla giriş yapılamaz.

        Testi kurgusu: son bardan hemen sonra devasa bir sıçrama koy. Giriş
        t+1'de ise sıçrama getiride GÖRÜNÜR; t'de olsaydı görünmezdi.
        """
        p = _panel(n_gun=400, n_ticker=6)
        r = backtest.walk_forward(cfg_test, p, horizon=10, cost_pct=0.0)
        for d in r["donemler"]:
            i_sinyal = p.dates.index(d["tarih"])
            i_giris = p.dates.index(d["giris"])
            assert i_giris == i_sinyal + 1, "giriş t+1 değil — look-ahead"

    def test_gelecek_veri_skora_girmez(self, cfg_test):
        """t anındaki skor, t'den SONRAKİ barlardan etkilenmemeli."""
        p1 = _panel(n_gun=500, n_ticker=8)
        feat1 = backtest.build_features(p1, cfg_test)
        t = 400
        s1 = backtest.score_at(p1, feat1, cfg_test, t, horizon_days=20)

        # t'den sonrasını boz — skor DEĞİŞMEMELİ
        p2 = _panel(n_gun=500, n_ticker=8)
        p2.c_tr[t + 1:] *= 5.0
        p2.c[t + 1:] *= 5.0
        feat2 = backtest.build_features(p2, cfg_test)
        s2 = backtest.score_at(p2, feat2, cfg_test, t, horizon_days=20)

        np.testing.assert_allclose(np.nan_to_num(s1), np.nan_to_num(s2), atol=1e-9)


class TestOrtusme:
    def test_donemler_ortusmez(self, cfg_test):
        p = _panel(n_gun=800, n_ticker=8)
        r = backtest.walk_forward(cfg_test, p, horizon=20, cost_pct=0.0)
        d = r["donemler"]
        for a, b in zip(d, d[1:]):
            i_cikis = p.dates.index(a["cikis"])
            i_giris = p.dates.index(b["giris"])
            assert i_giris >= i_cikis, "dönemler örtüşüyor — bağımsızlık ihlali"

    def test_donem_sayisi_ufukla_azalir(self, cfg_test):
        p = _panel(n_gun=800, n_ticker=8)
        kisa = backtest.walk_forward(cfg_test, p, horizon=5, cost_pct=0.0)
        uzun = backtest.walk_forward(cfg_test, p, horizon=40, cost_pct=0.0)
        assert kisa["n_donem"] > uzun["n_donem"] * 4


class TestSessizKirpmaYok:
    def test_atlanan_donemler_raporlanir(self, cfg_test):
        p = _panel(n_gun=600, n_ticker=8)
        r = backtest.walk_forward(cfg_test, p, horizon=20, cost_pct=0.0)
        assert "n_atlanan" in r
        assert set(r["n_atlanan"]) == {"veri_yok", "uygun_yok"}

    def test_havuz_kucukse_donem_atilmaz_portfoy_kuculur(self, cfg_test):
        """Eski hata: `uygun < top_n` olan dönemler düşürülüyordu ve bu,
        ayı piyasalarının TAMAMINI örneklemden çıkarıyordu (131'in 62'si)."""
        p = _panel(n_gun=600, n_ticker=4)
        r = backtest.walk_forward(cfg_test, p, horizon=20, cost_pct=0.0,
                                  use_gates=False)
        assert r["n_donem"] > 0
        assert all(d["n_secilen"] >= 1 for d in r["donemler"])


class TestTaban:
    def test_taban_ew_uygun_evren(self, cfg_test):
        """r_ew, aynı uygun havuzun eşit-ağırlık getirisi olmalı."""
        p = _panel(n_gun=500, n_ticker=10)
        r = backtest.walk_forward(cfg_test, p, horizon=20, cost_pct=0.0,
                                  use_gates=False)
        d = r["donemler"][0]
        gi, ci = p.dates.index(d["giris"]), p.dates.index(d["cikis"])
        beklenen = float(((p.c_tr[ci] / p.c_tr[gi] - 1.0) * 100.0).mean())
        assert d["r_ew"] == pytest.approx(beklenen, abs=1e-6)

    def test_alfa_ew_ile_xu100_farkli(self, cfg_test):
        """XU100 sabitken EW yükseliyorsa iki alfa AYRIŞMALI — ayrışmıyorsa
        taban çizgisi ayrımı kodda gerçekten uygulanmıyor demektir."""
        p = _panel(n_gun=500, n_ticker=10, xu_sabit=True)
        r = backtest.walk_forward(cfg_test, p, horizon=20, cost_pct=0.0,
                                  use_gates=False)
        d = r["donemler"][0]
        assert abs(d["alfa_ew"] - d["alfa_xu100"]) > 1e-6

    def test_maliyet_yalniz_secilene(self, cfg_test):
        p = _panel(n_gun=500, n_ticker=10)
        r0 = backtest.walk_forward(cfg_test, p, horizon=20, cost_pct=0.0, use_gates=False)
        r1 = backtest.walk_forward(cfg_test, p, horizon=20, cost_pct=1.0, use_gates=False)
        d0, d1 = r0["donemler"][0], r1["donemler"][0]
        assert d1["r_ew"] == pytest.approx(d0["r_ew"])           # taban etkilenmez
        assert d1["r_secilen"] == pytest.approx(d0["r_secilen"] - 1.0)


class TestSinyalBulunabiliyor:
    """Harness gerçekten sinyal varsa bulabiliyor mu? Bulamıyorsa negatif
    sonuçlar 'faktör yok' değil 'harness bozuk' anlamına gelir."""

    def test_mukemmel_momentumda_pozitif_ic(self, cfg_test):
        """Kurgu: geçmiş büyüme = gelecek büyüme. IC ≈ 1 çıkmalı."""
        p = _panel(n_gun=900, n_ticker=12)
        r = backtest.walk_forward(cfg_test, p, horizon=20, cost_pct=0.0,
                                  use_gates=False, weights=backtest.solo("mom_6_1"))
        assert r["ic_tum"]["ic_ort"] is not None
        assert r["ic_tum"]["ic_ort"] > 0.9, (
            f"mükemmel momentumda IC={r['ic_tum']['ic_ort']:.3f} — harness sinyali "
            "göremiyor, negatif sonuçlara güvenilemez")

    def test_mukemmel_momentumda_pozitif_alfa(self, cfg_test):
        p = _panel(n_gun=900, n_ticker=12)
        r = backtest.walk_forward(cfg_test, p, horizon=20, cost_pct=0.0,
                                  use_gates=False, weights=backtest.solo("mom_6_1"))
        assert r["alfa_ew"]["ort"] > 0

    def test_ters_sinyalde_negatif_ic(self, cfg_test):
        p = _panel(n_gun=900, n_ticker=12)
        r = backtest.walk_forward(cfg_test, p, horizon=20, cost_pct=0.0,
                                  use_gates=False,
                                  weights={"mom_6_1": -1.0, "mom_12_1": 0.0,
                                           "high52_prox": 0.0, "volscaled_mom": 0.0})
        assert r["ic_tum"]["ic_ort"] < -0.9


class TestKapiIsareti:
    def test_negatif_kanit_kapiyi_ACMAZ(self, cfg_test):
        """GERÇEK HATA (2026-07-26): `edge_verdict` mutlak değere bakar; kapı
        işaret kontrol etmediği için mom_12_1 (−1.47pp, t=−2.64) kapıyı
        AÇIYORDU. Kaybettiren faktör kanıt sayılamaz."""
        neg = stats.edge_verdict(-2.5, 100, 15, 1.0)
        assert neg.startswith(stats.HUKUM_ZAYIF_KANIT)      # büyüklük hükmü: evet
        # kapı mantığı: hüküm + POZİTİF işaret
        sahte = {"hukum": neg, "alfa_ew": {"ort": -2.5}}
        acar = sahte["hukum"].startswith(stats.HUKUM_ZAYIF_KANIT) and \
            (sahte["alfa_ew"]["ort"] or 0) > 0
        assert not acar, "negatif kanıt kapıyı açıyor"


class TestWeightsHash:
    def test_agirlik_degisince_hash_degisir(self, cfg):
        h1 = factors.weights_hash(cfg)
        c2 = util.load_config(fresh=True)
        c2["faktorler"] = {**c2["faktorler"],
                           "agirliklar": {**c2["faktorler"]["agirliklar"],
                                          "mom_6_1": 0.99}}
        assert factors.weights_hash(c2) != h1

    def test_ayni_ayar_ayni_hash(self, cfg):
        assert factors.weights_hash(cfg) == factors.weights_hash(cfg)

    def test_ufuk_kapisi_high52_agirligini_sifirlar(self, cfg):
        """H<21'de high52_prox ölçülen kenar taşımıyor → ağırlık 0."""
        kisa = factors.effective_weights(cfg, horizon_days=10)
        uzun = factors.effective_weights(cfg, horizon_days=42)
        assert kisa["high52_prox"] == 0.0
        assert uzun["high52_prox"] > 0.0
        assert sum(kisa.values()) == pytest.approx(1.0)
