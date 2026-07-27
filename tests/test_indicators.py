"""Gösterge testleri — özellikle **HANGİ SERİ NEREDE** sorusu.

`src/indicators.py`'nin en önemli kararı iki fiyat serisinin ayrılmasıdır:

    c     (temettü düzeltmesiz) → SMA / Bollinger / ATR / 52h  → İŞLEM SEVİYESİ
    c_tr  (toplam getiri)       → RSI / MACD / getiriler / *_tr → MOMENTUM

Bu eşlemeyi karıştırmak HİÇBİR HATA FIRLATMAZ. Stop'u temettü düzeltmeli bir
seviyeye koymak piyasada olmayan bir fiyat üretir; momentumu ham seriden ölçmek
temettü ödeyen her hisseyi yapay olarak zayıf gösterir (ölçüldü: TUPRS
2025-03-28'de ham −%2.95 / düzeltilmiş +%2.67). Aşağıdaki `TestSeriYonlendirmesi`
sınıfı bu eşlemeyi tek tek sabitler — testler `c` ile `c_tr`'yi bilerek
AYRIŞTIRARAK kurulur, aksi halde ikisi aynı sonucu verir ve test hiçbir şey
kanıtlamaz.

Ayrıca: Wilder yumuşatma ≠ klasik EMA. Karıştırmak RSI/ATR/ADX'i sessizce
BAŞKA bir göstergeye çevirir; sayı hâlâ makul görünür.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import indicators as ind

from tests.conftest import add_bars, add_universe, bar_serisi


def _df(rows: list[tuple]) -> pd.DataFrame:
    d = pd.DataFrame(rows, columns=["date", "o", "h", "l", "c", "v", "c_tr"])
    d["turnover_try"] = d["c"] * d["v"]
    return d


@pytest.fixture
def ayrisan() -> pd.DataFrame:
    """`c` ve `c_tr` BİLEREK ayrışan 320 barlık seri (yıllık ~%28 temettü kayması)."""
    return _df(bar_serisi(320, gunluk_egim=0.0008, dalga=3.0,
                          temettu_verimi=0.001))


# ============================================================ saf göstergeler
class TestYumusatma:
    def test_wilder_klasik_emadan_FARKLI(self):
        """alpha=1/n ile alpha=2/(n+1) aynı şey değildir.

        `_wilder` yerine `ema` kullanmak RSI'ı, ATR'ı ve ADX'i başka bir
        göstergeye çevirir — ve çıktı hâlâ 0-100 arasında makul görünür.
        """
        s = pd.Series(np.linspace(1, 100, 100))
        w, e = ind._wilder(s, 14), ind.ema(s, 14)
        assert not np.allclose(w.to_numpy(), e.to_numpy())
        # Wilder daha yavaş: son değeri seriye daha UZAK kalır.
        assert abs(w.iloc[-1] - s.iloc[-1]) > abs(e.iloc[-1] - s.iloc[-1])

    def test_wilder_alpha_tanimi(self):
        s = pd.Series([10.0, 20.0, 30.0])
        beklenen = s.ewm(alpha=1 / 5, adjust=False).mean()
        pd.testing.assert_series_equal(ind._wilder(s, 5), beklenen)


class TestSMA:
    def test_pencere_dolmadan_NaN(self):
        """Eksik pencere SESSİZCE kısmi ortalama vermez.

        `min_periods=n` olmadan pandas ilk barda tek elemanın ortalamasını verir
        ve "SMA200" adıyla 1 barlık bir ortalama dolaşıma girer.
        """
        s = pd.Series([1.0] * 10)
        out = ind.sma(s, 5)
        assert out.iloc[:4].isna().all()
        assert out.iloc[4] == 1.0

    def test_bilinen_deger(self):
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
        assert ind.sma(s, 5).iloc[-1] == 3.0


class TestRSI:
    def test_kesintisiz_yukselisde_100(self):
        """Kayıp yoksa RSI 100'dür — sıfıra bölme NaN'a düşmemeli."""
        s = pd.Series(np.arange(1, 60, dtype=float))
        assert ind.rsi(s, 14).iloc[-1] == pytest.approx(100.0)

    def test_bandin_icinde_kalir(self):
        s = pd.Series(100 + 10 * np.sin(np.arange(200) / 7.0))
        v = ind.rsi(s, 14).dropna()
        assert len(v) > 100
        assert v.between(0.0, 100.0).all()

    def test_dususte_50_altinda(self):
        s = pd.Series(np.arange(200, 1, -1, dtype=float))
        assert ind.rsi(s, 14).iloc[-1] < 50.0

    def test_sabit_seride_tanimsiz(self):
        """Ne kazanç ne kayıp → RSI TANIMSIZ. 50 uydurmak yanlış olurdu."""
        s = pd.Series([100.0] * 60)
        assert pd.isna(ind.rsi(s, 14).iloc[-1])


class TestATR:
    def test_true_range_bosluklari_gorur(self):
        """TR yalnız gün içi aralık değildir; önceki kapanışa boşluk da girer."""
        h = pd.Series([10.0, 20.0])
        l = pd.Series([9.0, 19.0])
        c = pd.Series([9.5, 19.5])
        tr = ind.true_range(h, l, c)
        assert tr.iloc[0] == pytest.approx(1.0)          # ilk bar: h-l
        assert tr.iloc[1] == pytest.approx(10.5)         # boşluk: |h - önceki c|

    def test_atr_wilder_ile_yumusatilir(self):
        rows = bar_serisi(80, gunluk_egim=0.002, dalga=1.5)
        d = _df(rows)
        beklenen = ind._wilder(ind.true_range(d["h"], d["l"], d["c"]), 14)
        pd.testing.assert_series_equal(ind.atr(d["h"], d["l"], d["c"], 14), beklenen)

    def test_atr_daima_pozitif(self):
        d = _df(bar_serisi(120, gunluk_egim=-0.001, dalga=2.0))
        v = ind.atr(d["h"], d["l"], d["c"], 14).dropna()
        assert (v > 0).all()


class TestADX:
    def test_bandin_icinde(self):
        d = _df(bar_serisi(300, gunluk_egim=0.001, dalga=2.0))
        adx, dip, dim = ind.adx(d["h"], d["l"], d["c"], 14)
        for s in (adx, dip, dim):
            v = s.dropna()
            assert len(v) > 50
            assert v.between(0.0, 100.0).all()

    def test_yukari_trendde_arti_di_baskin(self):
        d = _df(bar_serisi(200, gunluk_egim=0.004))
        _, dip, dim = ind.adx(d["h"], d["l"], d["c"], 14)
        assert dip.iloc[-1] > dim.iloc[-1]

    def test_asagi_trendde_eksi_di_baskin(self):
        d = _df(bar_serisi(200, gunluk_egim=-0.004))
        _, dip, dim = ind.adx(d["h"], d["l"], d["c"], 14)
        assert dim.iloc[-1] > dip.iloc[-1]


class TestBollinger:
    def test_bant_sirasi_ve_pctb(self):
        d = _df(bar_serisi(120, dalga=5.0))
        mid, up, low, pctb, gen = ind.bollinger(d["c"], 20, 2.0)
        i = -1
        assert low.iloc[i] < mid.iloc[i] < up.iloc[i]
        assert gen.iloc[i] > 0
        # pctb tanımı: bandın alt ucunda 0, üst ucunda 1
        beklenen = (d["c"].iloc[i] - low.iloc[i]) / (up.iloc[i] - low.iloc[i])
        assert pctb.iloc[i] == pytest.approx(beklenen)

    def test_sabit_seride_sifira_bolmez(self):
        s = pd.Series([50.0] * 40)
        mid, up, low, pctb, gen = ind.bollinger(s, 20, 2.0)
        assert pd.isna(pctb.iloc[-1]) or np.isfinite(pctb.iloc[-1])
        assert not np.isinf(np.nan_to_num(pctb.to_numpy(), posinf=np.inf)).any()


class TestVolatilite:
    def test_yillklastirma_carpani(self):
        """√252 ile yıllıklaştırma ve %100 ölçeği — birim hatası sessizdir."""
        rng = np.random.default_rng(0)
        s = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 400))))
        v = ind.realized_vol(s, 63).iloc[-1]
        # günlük sd ~0.01 → yıllık ~%15.9
        assert 8.0 < v < 30.0

    def test_pencere_dolmadan_NaN(self):
        s = pd.Series(np.linspace(100, 110, 40))
        assert ind.realized_vol(s, 63).isna().all()


# ============================================================ seri yönlendirmesi
class TestSeriYonlendirmesi:
    """Her gösterge DOĞRU fiyat serisinden besleniyor mu?

    Bu sınıfın tamamı `c` ile `c_tr`'nin ayrıştığı bir seri üzerinde koşar.
    Ayrışma olmadan bu testler hiçbir şey kanıtlamaz — bu yüzden fixture
    `temettu_verimi` ile kasten bir kayma kurar.
    """

    def test_seri_gercekten_ayrisiyor(self, ayrisan):
        """Testin ön koşulu: `c` ile `c_tr` farklı olmalı."""
        fark = abs(ayrisan["c_tr"].iloc[-1] / ayrisan["c"].iloc[-1] - 1) * 100
        assert fark > 10, f"fixture ayrışma kurmuyor (fark %{fark:.2f})"

    @pytest.mark.parametrize("kolon,n", [("sma20", 20), ("sma50", 50), ("sma200", 200)])
    def test_sma_HAM_fiyattan(self, ayrisan, cfg, kolon, n):
        """SMA'lar işlem seviyesidir → `c`. `c_tr`'den hesaplanan bir SMA200,
        pencerede birikmiş temettü kadar yukarı kaymış bir seviyedir ve stop
        oraya konamaz."""
        e = ind.enrich(ayrisan, cfg)
        beklenen = ind.sma(ayrisan["c"].astype(float), n)
        assert e[kolon].iloc[-1] == pytest.approx(beklenen.iloc[-1])
        assert e[kolon].iloc[-1] != pytest.approx(
            ind.sma(ayrisan["c_tr"].astype(float), n).iloc[-1])

    def test_trend_kapisi_SMA_leri_TOPLAM_GETIRIDEN(self, ayrisan, cfg):
        """`sma50_tr` / `sma200_tr` kapı içindir → `c_tr`.

        `c` üzerinden SMA200, fiyatı sistematik olarak SMA200'ün ALTINDA
        gösterir; %3-5 temettü verimiyle bu sapma kapının %2'lik toleransından
        büyüktür, yani kapıyı bozar (migration v2'nin gerekçesi).
        """
        e = ind.enrich(ayrisan, cfg)
        ctr = ayrisan["c_tr"].astype(float)
        assert e["sma50_tr"].iloc[-1] == pytest.approx(ind.sma(ctr, 50).iloc[-1])
        assert e["sma200_tr"].iloc[-1] == pytest.approx(ind.sma(ctr, 200).iloc[-1])
        assert e["sma200_tr"].iloc[-1] != pytest.approx(e["sma200"].iloc[-1])

    def test_rsi_ve_macd_TOPLAM_GETIRIDEN(self, ayrisan, cfg):
        e = ind.enrich(ayrisan, cfg)
        ctr = ayrisan["c_tr"].astype(float)
        assert e["rsi14"].iloc[-1] == pytest.approx(ind.rsi(ctr, 14).iloc[-1])
        m_line, m_sig, m_hist = ind.macd(ctr, 12, 26, 9)
        assert e["macd"].iloc[-1] == pytest.approx(m_line.iloc[-1])
        assert e["macd_hist"].iloc[-1] == pytest.approx(m_hist.iloc[-1])
        # Ham seriden hesaplanan MACD farklı olurdu
        assert e["macd"].iloc[-1] != pytest.approx(
            ind.macd(ayrisan["c"].astype(float), 12, 26, 9)[0].iloc[-1])

    @pytest.mark.parametrize("n", [21, 63, 126, 252])
    def test_getiriler_TOPLAM_GETIRIDEN(self, ayrisan, cfg, n):
        """Momentumu ham seriden ölçmek temettü ödeyen hisseyi zayıf gösterir."""
        e = ind.enrich(ayrisan, cfg)
        ctr = ayrisan["c_tr"].astype(float)
        beklenen = (ctr.iloc[-1] / ctr.iloc[-1 - n] - 1.0) * 100.0
        assert e[f"ret_{n}"].iloc[-1] == pytest.approx(beklenen)

    def test_atr_ve_bollinger_HAM_fiyattan(self, ayrisan, cfg):
        e = ind.enrich(ayrisan, cfg)
        c = ayrisan["c"].astype(float)
        beklenen_atr = ind.atr(ayrisan["h"].astype(float), ayrisan["l"].astype(float),
                               c, 14)
        assert e["atr14"].iloc[-1] == pytest.approx(beklenen_atr.iloc[-1])
        assert e["atr_pct"].iloc[-1] == pytest.approx(
            beklenen_atr.iloc[-1] / c.iloc[-1] * 100.0)
        assert e["bb_mid"].iloc[-1] == pytest.approx(ind.sma(c, 20).iloc[-1])

    def test_52_hafta_HAM_yuksek_dusukten(self, ayrisan, cfg):
        e = ind.enrich(ayrisan, cfg)
        h = ayrisan["h"].astype(float)
        l = ayrisan["l"].astype(float)
        assert e["high_52w"].iloc[-1] == pytest.approx(
            h.rolling(252, min_periods=100).max().iloc[-1])
        assert e["low_52w"].iloc[-1] == pytest.approx(
            l.rolling(252, min_periods=100).min().iloc[-1])

    def test_volatilite_TOPLAM_GETIRIDEN(self, ayrisan, cfg):
        e = ind.enrich(ayrisan, cfg)
        assert e["vol_ann_63"].iloc[-1] == pytest.approx(
            ind.realized_vol(ayrisan["c_tr"].astype(float), 63).iloc[-1])

    def test_zirveye_uzaklik_ASLA_POZITIF_olamaz(self, ayrisan, cfg):
        """`dist_high52_pct` = c / max(h) − 1. Kapanış aynı günün yükseğini
        aşamayacağı için bu değer ≤ 0'dır. Pozitif çıkması, ham/düzeltilmiş seri
        karışımının en net belirtisidir."""
        e = ind.enrich(ayrisan, cfg)
        v = e["dist_high52_pct"].dropna()
        assert len(v) > 50
        assert (v <= 1e-9).all(), f"pozitif değer var: {v.max()}"

    def test_ciro_medyani_turnoverdan(self, ayrisan, cfg):
        e = ind.enrich(ayrisan, cfg)
        assert e["turnover_med_63"].iloc[-1] == pytest.approx(
            ayrisan["turnover_try"].rolling(63, min_periods=63).median().iloc[-1])

    def test_enrich_girdiyi_DEGISTIRMEZ(self, ayrisan, cfg):
        once = ayrisan.copy(deep=True)
        ind.enrich(ayrisan, cfg)
        pd.testing.assert_frame_equal(ayrisan, once)

    def test_enrich_deterministik(self, ayrisan, cfg):
        a = ind.enrich(ayrisan, cfg)
        b = ind.enrich(ayrisan, cfg)
        pd.testing.assert_frame_equal(a, b)


# ============================================================ saklama
class TestSaklama:
    def test_NaN_sessizce_TASINMAZ(self):
        """`_n`: hesaplanamadı → None. NaN'ı 0.0 gibi taşımak "hesaplanamadı"yı
        "sıfır" gibi gösterirdi ve sıfır bir DEĞERDİR."""
        assert ind._n(float("nan")) is None
        assert ind._n(float("inf")) is None
        assert ind._n(None) is None
        assert ind._n("abc") is None
        assert ind._n(3) == 3.0
        assert ind._n(np.float64(2.5)) == 2.5

    def test_yetersiz_bar_SATIR_YAZMAZ(self, cfg, con, caplog):
        """`min_bar_hesap_icin` altındaki ticker için satır üretilmez ve bu
        UYARIYLA söylenir — sessizce boş bırakmak, paydanın neden daraldığını
        gizler."""
        add_universe(con, "KISA")
        add_bars(con, "KISA", bar_serisi(50))
        with caplog.at_level("WARNING"):
            r = ind.compute_and_store(cfg, con, tickers=["KISA"])
        assert r["satir"]["KISA"] == 0
        assert "gösterge hesaplanmadı" in caplog.text
        assert con.execute("SELECT COUNT(*) FROM indicator_daily").fetchone()[0] == 0

    def test_yeterli_barda_yazilir_ve_set_version_dogru(self, cfg, con):
        add_universe(con, "UZUN")
        add_bars(con, "UZUN", bar_serisi(300, gunluk_egim=0.001, dalga=2.0))
        r = ind.compute_and_store(cfg, con, tickers=["UZUN"])
        assert r["satir"]["UZUN"] == 300
        assert r["set_version"] == cfg["gostergeler"]["set_version"]
        sv = {x[0] for x in con.execute("SELECT DISTINCT set_version FROM indicator_daily")}
        assert sv == {cfg["gostergeler"]["set_version"]}

    def test_start_filtresi_yalniz_sonrasini_yazar(self, cfg, con):
        rows = bar_serisi(300, gunluk_egim=0.001)
        add_universe(con, "UZUN")
        add_bars(con, "UZUN", rows)
        kesme = rows[250][0]
        ind.compute_and_store(cfg, con, tickers=["UZUN"], start=kesme)
        en_eski = con.execute("SELECT MIN(date) FROM indicator_daily").fetchone()[0]
        assert en_eski == kesme

    def test_iki_kez_kosmak_cogaltmaz(self, cfg, con):
        add_universe(con, "UZUN")
        add_bars(con, "UZUN", bar_serisi(300, gunluk_egim=0.001))
        ind.compute_and_store(cfg, con, tickers=["UZUN"])
        n1 = con.execute("SELECT COUNT(*) FROM indicator_daily").fetchone()[0]
        ind.compute_and_store(cfg, con, tickers=["UZUN"])
        assert con.execute("SELECT COUNT(*) FROM indicator_daily").fetchone()[0] == n1

    def test_snapshot_set_version_e_gore_suzer(self, cfg, con):
        """Farklı gösterge sürümleri KARIŞMAZ — sürüm çatallanmanın aracıdır."""
        rows = bar_serisi(300, gunluk_egim=0.001)
        add_universe(con, "UZUN")
        add_bars(con, "UZUN", rows)
        ind.compute_and_store(cfg, con, tickers=["UZUN"])
        asof = rows[-1][0]
        assert "UZUN" in ind.snapshot(con, asof, cfg)
        yabanci = {**cfg, "gostergeler": {**cfg["gostergeler"],
                                          "set_version": "baska_surum_v9"}}
        assert ind.snapshot(con, asof, yabanci) == {}

    def test_snapshot_olmayan_gun_bos(self, cfg, con):
        assert ind.snapshot(con, "1999-01-01", cfg) == {}


# ============================================================ gerçek veri
class TestGercekVeri:
    def test_gercek_hissede_gostergeler_makul_bantta(self, real_cfg, real_con):
        """Gerçek veriyle sınır kontrolü: RSI 0-100, ATR>0, ADX 0-100.

        Bu bir formül testi değil, KAYNAK regresyon testi: yfinance bir gün
        bozuk bar döndürürse (negatif fiyat, ters h/l) burada görünür.
        """
        from src import prices, universe
        canli = universe.live(real_con)
        if not canli:
            pytest.skip("evren boş")
        t = canli[0]
        bars = prices.bars(real_con, t)
        if len(bars) < 300:
            pytest.skip(f"{t}: yetersiz bar")
        e = ind.enrich(bars, real_cfg)
        son = e.iloc[-1]
        assert 0.0 <= son["rsi14"] <= 100.0
        assert son["atr14"] > 0
        assert 0.0 <= son["adx14"] <= 100.0
        assert son["dist_high52_pct"] <= 1e-9
        assert son["low_52w"] <= son["high_52w"]

    def test_gercek_veride_h_l_tutarli(self, real_con):
        """h >= l ve h >= c >= l — kaynağın en temel sözleşmesi."""
        bozuk = real_con.execute(
            "SELECT COUNT(*) FROM bars_daily "
            " WHERE h < l OR c > h + 1e-6 OR c < l - 1e-6").fetchone()[0]
        assert bozuk == 0, f"{bozuk} barda OHLC tutarsız — kaynak regresyona gitti"
