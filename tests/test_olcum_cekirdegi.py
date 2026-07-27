"""Ölçüm çekirdeği — KAPI AYRIMI, PAYDA İŞARETİ ve seviye kenarı harness'i.

`tests/test_backtest.py` look-ahead, örtüşme, taban çizgisi ve kapı işaretini
sabitliyor. Bu dosya onun kapsamadığı üç mekanizmayı ekliyor:

1. **Kapılar ayrı ayrı açılıp kapanabilir ve bu BİLİNÇLİ.** Ölçüm gösterdi ki
   SMA200 bir **bilgi** kapısıdır (skorun sıralayacağı varyansı keser),
   likidite ve veri kalitesi ise **uygulanabilirlik** kapılarıdır (işlem
   yapılamayan ismi eler, bilgi yok etmez). İkisini tek bayrağın arkasına
   koymak, birini ölçerken diğerini de kapatmaya zorluyordu — ve teşhis adımı
   ("bilginin %79'u kapıda kayboluyor") tam olarak bu ayrımla mümkün oldu.

2. **Skor paydası MUTLAK ağırlık toplamıdır.** İşaretli toplansaydı negatif
   ağırlıklı bir faktör (ölçüm tersini söylediğinde meşru bir kullanım) kendini
   paydada götürür ve skorun İŞARETİNİ geri çevirirdi — sessizce.

3. **`measure_level_edge` gerçekten koşuyor mu?** Bu harness yazılmıştı ama
   hiçbir yerden çağrılmıyordu (2026-07-27 denetimi). Koşulmayan bir ölçüm
   harness'i, silinmesi değil bağlanması gereken bir eksiktir.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import backtest, factors, levels, stats

from tests.conftest import add_bars, add_index, add_universe, bar_serisi


@pytest.fixture
def panel(cfg, con):
    """4 ticker × 320 bar; likidite ve SMA200 durumları BİLEREK farklı.

    * BOL  : yüksek ciro, güçlü trend  → tüm kapılardan geçer
    * INCE : ciro eşiğin ALTINDA        → likidite kapısı eler
    * DUSUK: SMA200'ün altında          → SMA200 kapısı eler
    * KISA : yalnız 30 bar              → veri kapısı eler
    """
    tarihler = None
    for ad, egim, hacim, n in (("BOL", 0.0015, 8_000_000.0, 320),
                               ("INCE", 0.0015, 100.0, 320),
                               ("DUSUK", -0.0030, 8_000_000.0, 320),
                               ("KISA", 0.0015, 8_000_000.0, 30)):
        add_universe(con, ad)
        rows = bar_serisi(n, fiyat=100.0, gunluk_egim=egim, dalga=2.0, hacim=hacim)
        add_bars(con, ad, rows)
        if n == 320:
            tarihler = [r[0] for r in rows]
    add_index(con, "XU100", tarihler)
    p = backtest.load_panel(con, ["BOL", "INCE", "DUSUK", "KISA"])
    return p, backtest.build_features(p, cfg)


def _idx(p, ad: str) -> int:
    return p.tickers.index(ad)


# ============================================================ kapı ayrımı
class TestKapiAyrimi:
    def test_varsayilan_UC_KAPI_acik(self):
        assert backtest.VARSAYILAN_KAPILAR == {"sma200": True, "likidite": True,
                                               "veri": True}

    def test_tum_kapilar_acikken_yalniz_UYGUN_isim_gecer(self, cfg, panel):
        p, feat = panel
        m = backtest.eligible_mask(p, feat, cfg, p.n - 1)
        assert m[_idx(p, "BOL")]
        assert not m[_idx(p, "INCE")], "likidite kapısı geçirdi"
        assert not m[_idx(p, "DUSUK")], "SMA200 kapısı geçirdi"
        assert not m[_idx(p, "KISA")], "veri kapısı geçirdi"

    def test_SMA200_kapisi_TEK_BASINA_kapatilabilir(self, cfg, panel):
        """Bilgi kapısını kapatıp uygulanabilirlik kapılarını AÇIK tutmak,
        teşhisin ("bilgi kapıda kayboluyor") ön koşulu."""
        p, feat = panel
        m = backtest.eligible_mask(p, feat, cfg, p.n - 1,
                                   {"sma200": False})
        assert m[_idx(p, "DUSUK")], "SMA200 kapatıldı ama isim yine elenmiş"
        assert not m[_idx(p, "INCE")], "likidite kapısı da kapanmış"

    def test_LIKIDITE_kapisi_tek_basina_kapatilabilir(self, cfg, panel):
        p, feat = panel
        m = backtest.eligible_mask(p, feat, cfg, p.n - 1, {"likidite": False})
        assert m[_idx(p, "INCE")]
        assert not m[_idx(p, "DUSUK")]

    def test_VERI_kapisi_kapansa_bile_FIYAT_sarti_kalir(self, cfg, panel):
        """Fiyatı olmayan bir isim hiçbir kapı ayarında skorlanamaz.

        Bu, kapı bayraklarının ARKASINDA olmayan tek şart — çünkü fiyat yoksa
        ne skor ne getiri hesaplanabilir.
        """
        p, feat = panel
        m = backtest.eligible_mask(p, feat, cfg, p.n - 1,
                                   {"sma200": False, "likidite": False,
                                    "veri": False})
        assert m[_idx(p, "KISA")] == bool(np.isfinite(p.c_tr[p.n - 1,
                                                             _idx(p, "KISA")]))

    def test_kapisiz_havuz_kapili_havuzdan_GENIS(self, cfg, panel):
        p, feat = panel
        t = p.n - 1
        kapili = backtest.eligible_mask(p, feat, cfg, t).sum()
        kapisiz = backtest.eligible_mask(
            p, feat, cfg, t, {"sma200": False, "likidite": False}).sum()
        assert kapisiz > kapili


# ============================================================ skor paydası
class TestSkorPaydasi:
    def test_MUTLAK_agirlik_paydasi(self, cfg, panel):
        """Payda `abs(agirlik)` toplamı — işaretli toplamak skoru ters çevirir.

        Örnek: {+0.5, −0.5} ağırlıklarıyla işaretli payda 0 olur; sıfıra bölme
        ya `inf` ya işaret çevirmesi üretir ve ikisi de sessizdir.
        """
        p, feat = panel
        t = p.n - 1
        w = {"mom_6_1": 0.5, "mom_12_1": -0.5, "high52_prox": 0.0,
             "volscaled_mom": 0.0}
        with np.errstate(invalid="ignore"):
            skor = backtest.score_at(p, feat, cfg, t, horizon_days=20, weights=w)
        assert np.isfinite(skor).any()
        assert not np.isinf(skor[np.isfinite(skor)]).any()

    @staticmethod
    def _elle_feat(p, degerler: dict) -> dict:
        """Faktör matrislerini ELLE kurar — son satır `degerler`den gelir.

        Sentetik panelde `BOL` ile `INCE` aynı fiyat serisine sahip (yalnız
        hacimleri farklı), dolayısıyla faktörlerin z-desenleri birbirinin
        AYNISI çıkıyor ve payda aritmetiği gözlemlenemiyor. Bu yüzden burada
        faktör değerleri bilinçli olarak AYRIŞTIRILARAK kuruluyor.
        """
        feat = {}
        for ad in factors.FACTOR_NAMES:
            m = np.full((p.n, len(p.tickers)), np.nan)
            m[-1] = degerler[ad]
            feat[ad] = m
        return feat

    def test_paydanin_ARITMETIGI(self, cfg, panel):
        """Skor = Σ(ağırlık × z) / Σ|ağırlık|, yalnız GEÇERLİ faktörler üzerinden."""
        p, _ = panel
        t = p.n - 1
        feat = self._elle_feat(p, {"mom_6_1": [3.0, 1.0, -1.0, -3.0],
                                   "mom_12_1": [-3.0, -1.0, 1.0, 3.0],
                                   "high52_prox": [0.0, -5.0, -10.0, -20.0],
                                   "volscaled_mom": [2.0, 0.5, -0.5, -2.0]})
        w = factors.effective_weights(cfg, 20)
        lo, hi = cfg["faktorler"]["winsor_pct"]

        pay = np.zeros(len(p.tickers))
        payda = np.zeros(len(p.tickers))
        for ad, agirlik in w.items():
            if agirlik == 0:
                continue
            z = stats.zscore(stats.winsorize(feat[ad][t], lo, hi))
            pay += agirlik * np.nan_to_num(z)
            payda += abs(agirlik) * np.isfinite(z)
        beklenen = np.where(payda > 0, pay / payda, np.nan)

        skor = backtest.score_at(p, feat, cfg, t, horizon_days=20)
        np.testing.assert_allclose(skor, beklenen)

    def test_eksik_faktor_PAYDADAN_duser(self, cfg, panel):
        """Bir faktörün verisi yoksa 0 oy DEĞİL, hiç oy sayılır.

        0 saymak skoru sıfıra doğru çeker: veri yokluğu sessizce "nötr görüş"e
        dönüşür ve eksik verisi olan isim yapay olarak ortalamaya yaklaşır.
        """
        p, _ = panel
        t = p.n - 1
        temel = {"mom_6_1": [3.0, 1.0, -1.0, -3.0],
                 "mom_12_1": [3.0, 1.0, -1.0, -3.0],
                 "high52_prox": [0.0, -5.0, -10.0, -20.0],
                 "volscaled_mom": [-3.0, -1.0, 1.0, 3.0]}   # TERS yönde
        feat = self._elle_feat(p, temel)
        bozuk = self._elle_feat(p, {**temel,
                                    "volscaled_mom": [np.nan] * len(p.tickers)})

        w = factors.effective_weights(cfg, 20)
        assert w["volscaled_mom"] != 0, "test anlamsızlaştı: ağırlık sıfır"

        with np.errstate(invalid="ignore"):
            a = backtest.score_at(p, feat, cfg, t, horizon_days=20)
            b = backtest.score_at(p, bozuk, cfg, t, horizon_days=20)
        assert not np.allclose(a, b), (
            "ters yönlü bir faktörün kaybolması skoru DEĞİŞTİRMELİ")
        # Eksik faktör 0 sayılsaydı skor sıfıra doğru bastırılırdı; paydadan
        # düştüğü için kalan faktörlerin tam ağırlığıyla hesaplanır.
        assert abs(b[0]) > abs(a[0])
        assert np.isfinite(b).any(), "eksik faktör tüm skoru yok etmemeli"

    def test_sifir_agirlikli_faktor_HESABA_GIRMEZ(self, cfg, panel):
        """H=20'de `high52_prox` ağırlığı 0 → değeri ne olursa olsun etkisiz."""
        p, _ = panel
        t = p.n - 1
        temel = {"mom_6_1": [3.0, 1.0, -1.0, -3.0],
                 "mom_12_1": [1.0, 2.0, 3.0, 4.0],
                 "high52_prox": [0.0, -5.0, -10.0, -20.0],
                 "volscaled_mom": [2.0, 0.5, -0.5, -2.0]}
        assert factors.effective_weights(cfg, 20)["high52_prox"] == 0.0
        a = backtest.score_at(p, self._elle_feat(p, temel), cfg, t, horizon_days=20)
        b = backtest.score_at(
            p, self._elle_feat(p, {**temel, "high52_prox": [999.0, -999.0, 0.0, 1.0]}),
            cfg, t, horizon_days=20)
        np.testing.assert_allclose(a, b)

    def test_solo_yalniz_bir_faktoru_izole_eder(self):
        w = backtest.solo("mom_6_1")
        assert set(w) == set(factors.FACTOR_NAMES)
        assert w["mom_6_1"] == 1.0
        assert sum(v for k, v in w.items() if k != "mom_6_1") == 0.0


# ============================================================ yardımcılar
class TestPanelYardimcilari:
    def test_shift_gelecege_BAKMAZ(self):
        """`_shift(a, k)` k bar GERİYE kaydırır: t anındaki değer t−k'den gelir."""
        a = np.arange(10, dtype=float).reshape(10, 1)
        s = backtest._shift(a, 3)
        assert np.isnan(s[:3]).all()
        assert s[3, 0] == 0.0 and s[9, 0] == 6.0

    def test_shift_negatif_ILERI_kaydirir(self):
        a = np.arange(5, dtype=float).reshape(5, 1)
        s = backtest._shift(a, -2)
        assert s[0, 0] == 2.0
        assert np.isnan(s[-2:]).all()

    def test_split_index_ilk_uygun_bari_bulur(self, panel):
        p, _ = panel
        i = backtest.split_index(p, p.dates[100])
        assert i == 100
        assert backtest.split_index(p, "1900-01-01") == 0
        assert backtest.split_index(p, "2999-01-01") == p.n

    def test_load_panel_ENDEKSLE_kesisir(self, cfg, con):
        """Takvimin otoritesi endekstir; hisse tarafındaki artıklar taşınmaz."""
        add_universe(con, "AAA")
        rows = bar_serisi(20)
        add_bars(con, "AAA", rows)
        add_index(con, "XU100", [r[0] for r in rows[:15]])
        p = backtest.load_panel(con, ["AAA"])
        assert p.n == 15

    def test_bos_panel_ACIK_HATA_verir(self, con):
        """Sessizce boş panel döndürmek, "ölçüm 0 dönem buldu" diye görünür."""
        with pytest.raises(ValueError, match="Panel boş"):
            backtest.load_panel(con, ["YOK"])

    def test_taban_EW_vs_XU100_olculur(self, cfg, panel):
        """Eşit-ağırlığın XU100'e göre BEDAVA üstünlüğü raporda görünmek zorunda."""
        p, _ = panel
        s = backtest.baseline_ew_vs_xu100(p, cfg, horizon=20)
        assert set(s) >= {"n", "ort", "medyan", "t", "gerekli_n"}


# ============================================================ seviye kenarı
class TestSeviyeKenariOlcumu:
    def test_yetersiz_barda_OLCMEZ(self, cfg):
        """300 bardan az veriyle seviye kenarı ölçülemez — uydurulmaz."""
        df = pd.DataFrame(bar_serisi(100),
                          columns=["date", "o", "h", "l", "c", "v", "c_tr"])
        r = levels.measure_level_edge(cfg, df, horizon=20)
        assert r["not"] == "yetersiz bar"
        assert r["destek"]["n"] == 0 and r["direnc"]["n"] == 0

    def test_yeterli_barda_HUKUM_uretir(self, cfg):
        df = pd.DataFrame(bar_serisi(500, gunluk_egim=0.0005, dalga=6.0, periyot=25),
                          columns=["date", "o", "h", "l", "c", "v", "c_tr"])
        r = levels.measure_level_edge(cfg, df, horizon=20)
        assert "not" not in r
        for taraf in ("destek", "direnc"):
            assert {"stat", "taban", "fark", "n", "hukum"} <= set(r[taraf])
            assert r[taraf]["hukum"].startswith(
                (stats.HUKUM_OLCUM_YOK, stats.HUKUM_YETERSIZ,
                 stats.HUKUM_KENAR_YOK, stats.HUKUM_ZAYIF_KANIT))

    def test_hukum_ASLA_dogrulandi_DEMEZ(self, cfg):
        df = pd.DataFrame(bar_serisi(500, gunluk_egim=0.0005, dalga=6.0),
                          columns=["date", "o", "h", "l", "c", "v", "c_tr"])
        r = levels.measure_level_edge(cfg, df, horizon=20)
        for taraf in ("destek", "direnc"):
            assert "doğrulandı" not in r[taraf]["hukum"].lower()

    def test_TABANA_gore_fark_olculur(self, cfg):
        """Bilgi mutlak medyanda değil, KOŞULSUZ TABANDAN farkta."""
        df = pd.DataFrame(bar_serisi(500, gunluk_egim=0.0005, dalga=6.0),
                          columns=["date", "o", "h", "l", "c", "v", "c_tr"])
        r = levels.measure_level_edge(cfg, df, horizon=20)
        for taraf in ("destek", "direnc"):
            if r[taraf]["n"] and r[taraf]["taban"]["n"]:
                assert r[taraf]["fark"] == pytest.approx(
                    r[taraf]["stat"]["medyan"] - r[taraf]["taban"]["medyan"])

    def test_seviyeler_LOOK_AHEAD_KORUMALI_yeniden_kurulur(self, cfg):
        """Ölçüm boyunca seviyeler `asof_idx` ile kurulur.

        Koruma kalkarsa sonuçlar "çok iyi" çıkar ve geçersizliği FARK EDİLMEZ —
        bu dosyanın en pahalı hata sınıfı.
        """
        cagrilar = []
        gercek = levels.build_levels

        def izleyen(bars, c, *, asof_idx=None, atr=None):
            cagrilar.append(asof_idx)
            return gercek(bars, c, asof_idx=asof_idx, atr=atr)

        levels.build_levels = izleyen
        try:
            df = pd.DataFrame(bar_serisi(500, gunluk_egim=0.0005, dalga=6.0),
                              columns=["date", "o", "h", "l", "c", "v", "c_tr"])
            levels.measure_level_edge(cfg, df, horizon=20)
        finally:
            levels.build_levels = gercek
        assert cagrilar, "seviyeler hiç yeniden kurulmadı"
        assert all(i is not None for i in cagrilar), (
            "asof_idx verilmemiş — seviyeler TÜM seriden kurulmuş olabilir")
        assert cagrilar == sorted(cagrilar)

    def test_yeniden_hesap_araligi_configten(self, cfg):
        """Her gün seviye kurmak O(n²) maliyet, sıfır bilgi."""
        assert int(cfg["seviyeler"]["yeniden_hesap_bar"]) >= 5

    def test_yakinlik_esigi_ATR_olcekli(self, cfg):
        """Mutlak yüzde kullanmak volatil ve sakin hisseyi eşitlerdi."""
        df = pd.DataFrame(bar_serisi(500, gunluk_egim=0.0005, dalga=6.0),
                          columns=["date", "o", "h", "l", "c", "v", "c_tr"])
        gevsek = levels.measure_level_edge(cfg, df, horizon=20, yakinlik_atr=2.0)
        siki = levels.measure_level_edge(cfg, df, horizon=20, yakinlik_atr=0.1)
        assert (gevsek["destek"]["n"] + gevsek["direnc"]["n"]
                >= siki["destek"]["n"] + siki["direnc"]["n"])
