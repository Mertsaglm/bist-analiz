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
        # ⚠ Bu küme BİR SÖZLEŞMEDİR. 2026-08-07'de bilerek büyüdü (ADR #016):
        # düzeltilmemiş kurumsal işlem barı yüzünden düşürülen gözlemler de
        # sayılır. Sessiz eleme yok — her eleme türünün adı ve sayısı burada.
        assert set(r["n_atlanan"]) == {"veri_yok", "uygun_yok", "kirli_gozlem"}

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


class TestAgirlikParmakIzi:
    """⚠ REGRESYON KİLİDİ (2026-07-27 denetimi).

    `weights_hash` yalnız HAM config ağırlıklarını hashliyordu; gerçekte
    kullanılan `effective_weights(cfg, horizon)` ise `h < high52_min_ufuk_gun`
    iken `high52_prox`'u sıfırlayıp yeniden normalize ediyor. Sonuç: H=20 ve
    H=42 MADDİ olarak farklı skor üretirken parmak izleri AYNIYDI — yani
    "ağırlık değişince çatallanır" mekanizması sessizce çalışmıyordu.
    """

    def test_ufuk_degisince_parmak_izi_DEGISIR(self, cfg):
        import copy
        from src import factors
        c42 = copy.deepcopy(cfg)
        c42["planlayici"]["zaman_bariyeri_gun"] = 42
        assert factors.effective_weights(cfg) != factors.effective_weights(c42)
        assert factors.weights_hash(cfg) != factors.weights_hash(c42), \
            "farklı etkin ağırlıklar aynı parmak izini üretiyor"

    def test_ayni_ayar_ayni_parmak_izi(self, cfg):
        from src import factors
        assert factors.weights_hash(cfg, 20) == factors.weights_hash(cfg, 20)

    def test_ufuk_argumani_imzaya_giriyor(self, cfg):
        from src import factors
        assert factors.weights_hash(cfg, 20) != factors.weights_hash(cfg, 42)


class TestBozukBarMaskesi:
    """⚠ REGRESYON KİLİDİ — ADR #016.

    NE OLMUŞTU: `eligible_mask`'in "veri" kapısı yalnız *momentum
    hesaplanabiliyor mu* diye soruyordu; kayıt bazlı kalite kapısı
    (`prices.assess_quality`) YALNIZ canlı hatta koşuyordu. Yani canlı katman
    "bu ismin verisine güvenmiyorum" derken ölçüm katmanı aynı barları sessizce
    kullanıyordu — L-008'in "simetriğini ara" kuralının tam hedefi.

    ÖLÇÜLDÜ (gerçek panel): 5 sahte getiri barı — CCOLA 2024-08-01 **−%90.7**
    (11:1 bölünme, seri geriye düzeltilmemiş) · TSPOR +%94.6 · AYGAZ +%72.5 ·
    HEKTS −%64.8 / +%44.1.

    Karar: ismin TAMAMI değil, yalnız ZEHİRLENEN GÖZLEM düşer (ADR #016).
    Ölçülen etki: alfa −0.861 → −0.920pp, hüküm HER DİLİMDE aynı (`kenar yok`).
    """

    KIRLI_T = 700          # kirlilik hangi barda başlıyor
    KIRLI_J = 1            # hangi isimde

    @staticmethod
    def _panel(n=900, kirlilik=None):
        """DETERMİNİSTİK panel; `kirlilik=(t, j, oran)` verilirse o bardan
        İTİBAREN j'inci ismin seviyesi orana bölünür (düzeltilmemiş bölünme).

        ⚠ Seriler FARKLI eğimli olmak zorunda: özdeş serilerde kesitsel z-skor
        tanımsızdır (std=0 → NaN) ve havuz boş kalır. İlk kurgum bu yüzden
        yanlış alarm veriyordu — testin kendisi bozuktu, kod değil.
        """
        import numpy as np
        from src.backtest import Panel
        t_, k = n, 4
        adim = np.arange(t_).reshape(-1, 1)
        egim = np.array([0.05, 0.08, 0.11, 0.14]).reshape(1, -1)
        dalga = 3.0 * np.sin(adim / 15.0 + np.arange(k).reshape(1, -1))
        c = 100.0 + adim * egim + dalga
        if kirlilik:
            ti, j, oran = kirlilik
            c[ti:, j] /= oran
        return Panel(
            dates=[f"2020-{1 + i // 300:02d}-{1 + i % 28:02d}" for i in range(t_)],
            tickers=["AAA", "BBB", "CCC", "DDD"],
            c=c.copy(), c_tr=c.copy(),
            h=c * 1.01, turnover=np.full((t_, k), 1e9),
            xu100=100.0 + np.arange(t_) * 0.07)

    def test_temiz_panelde_maske_BOS(self, cfg_test):
        from src import backtest
        assert not backtest.bozuk_bar_mask(self._panel(), cfg_test).any()

    def test_duzeltilmemis_bolunme_YAKALANIR(self, cfg_test):
        from src import backtest
        m = backtest.bozuk_bar_mask(
            self._panel(kirlilik=(self.KIRLI_T, self.KIRLI_J, 11.0)), cfg_test)
        assert m[self.KIRLI_T, self.KIRLI_J], "−%90'lık bar yakalanmadı"
        assert m.sum() == 1, "yalnız kırılma barı işaretlenmeliydi"

    def test_GERCEK_piyasa_ucu_yakalanMAZ(self, cfg_test):
        """+%22.2 (2023-02-15 deprem sonrası açılış) bir veri hatası DEĞİLDİR.

        Eşik oraya inerse ölçüm, kriz günlerini örneklemden atarak yalnız sakin
        dönemlerde yapılmış olur — sistematik iyimserlik.
        """
        from src import backtest
        m = backtest.bozuk_bar_mask(self._panel(kirlilik=(self.KIRLI_T, self.KIRLI_J, 1 / 1.222)), cfg_test)
        assert not m.any()

    def test_esik_config_ten_okunur_TEK_KAYNAK(self, cfg_test):
        """`risk`, `prices` ve `backtest` aynı anahtarı okumalı (L-011)."""
        import copy
        from src import backtest
        gevsek = copy.deepcopy(cfg_test)
        gevsek["evren"]["duzeltilmemis_kurumsal_pct"] = 95.0
        p = self._panel(kirlilik=(self.KIRLI_T, self.KIRLI_J, 11.0))
        assert backtest.bozuk_bar_mask(p, cfg_test).any()
        assert not backtest.bozuk_bar_mask(p, gevsek).any()

    def test_walk_forward_ZEHIRLENEN_gozlemi_DUSURUR(self, cfg_test):
        from src import backtest
        r = backtest.walk_forward(cfg_test, self._panel(kirlilik=(self.KIRLI_T, self.KIRLI_J, 11.0)),
                                  horizon=20, use_gates=False)
        assert r["n_atlanan"]["kirli_gozlem"] >= 1, \
            "kirli gözlem düşürülmedi — ölçüm hattı hâlâ sahte getiriyi okuyor"

    def test_temiz_panelde_HIC_gozlem_dusmez(self, cfg_test):
        """Kontrol grubu: maske her şeyi eliyorsa maske değil, arızadır."""
        from src import backtest
        r = backtest.walk_forward(cfg_test, self._panel(), horizon=20, use_gates=False)
        assert r["n_atlanan"]["kirli_gozlem"] == 0

    def test_ISIM_TAMAMEN_dusmez(self, cfg_test):
        """ADR #016'nın çekirdeği: sorun isimde değil, bir avuç barda.

        İsmi elemek ölçüm evrenini değiştirmek olurdu (ölçüldü: 67→63,
        alfa −0.861 → −0.946pp); oysa kirli gözlem sayısı yalnız 5.
        """
        from src import backtest
        p = self._panel(kirlilik=(self.KIRLI_T, self.KIRLI_J, 11.0))
        r = backtest.walk_forward(cfg_test, p, horizon=20, use_gates=False)
        # Kirlenmeden ÖNCEKİ dönemlerde o isim hâlâ havuzda olmalı.
        onceki = [d for d in r["donemler"] if d["n_havuz"] > 0]
        assert onceki, "isim tamamen düştü — cerrahi eleme yapılmamış"

    def test_SESSIZ_eleme_YOK_sayac_raporlanir(self, cfg_test):
        """Raporda görünmeyen eleme, bir sonraki okuyucu için görünmez varsayımdır."""
        from src import backtest
        r = backtest.walk_forward(cfg_test, self._panel(kirlilik=(self.KIRLI_T, self.KIRLI_J, 11.0)),
                                  horizon=20, use_gates=False)
        assert "kirli_gozlem" in r["n_atlanan"]
