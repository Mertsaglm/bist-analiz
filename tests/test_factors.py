"""Faktör ve kesitsel skorlama testleri.

Üç iddia sabitlenir, üçü de sessizce bozulabilecek türden:

1. **Kapılar skorlanmaz, ELER.** Bir şeye ağırlık vermek onu diğerleriyle takas
   edilebilir yapar; kapı yapmak yapmaz. SMA200 altındaki bir hisse "momentumu
   çok güçlü" diye seçilememeli.
2. **z TÜM evrende, sıralama YALNIZ uygunlar arasında.** Uygun olmayanları z
   tabanından çıkarmak dağılımı kaydırır ve kalan isimlerin skorlarını,
   kendileri hiç değişmediği halde değiştirir.
3. **Eksik faktör 0 sayılmaz, PAYDADAN DÜŞER.** Aksi halde eksik veri sessizce
   "nötr oy" olur ve skoru sıfıra doğru çeker — yani veri yokluğu bir GÖRÜŞE
   dönüşür.

Ayrıca L-007'nin kilidi: kesit daraldığında (`indicator_daily` eksik) bu
UYARIYLA söylenmeli. Ölçüldü (2026-07-27): 67 isim istenip 16 isimle
skorlanıyordu ve hiçbir yerde yazmıyordu — `pct=100` "67'de birinci" değil
"10'da birinci" demekti.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from src import factors

from tests.conftest import add_bars, add_indicator, add_universe, bar_serisi

TEMIZ_KALITE = {"ok": True, "zero_vol_ratio_252": 0.0}


def _row(**kw) -> pd.Series:
    """Kapı testleri için tek panel satırı — varsayılanlar TEMİZ geçer."""
    taban = {"c_tr": 100.0, "sma200_tr": 90.0, "turnover_med_63": 500_000_000.0,
             "mom_6_1": 5.0, "mom_12_1": 8.0}
    return pd.Series({**taban, **kw})


# ============================================================ ham faktörler
class TestHamFaktorler:
    def test_momentum_SON_AYI_DISLAR(self):
        """`6-1` demek: 6 aylık getiri, SON AY hariç.

        Kısa vadeli tersine dönüş etkisini momentum sinyalinden ayırmak için.
        Ölçüm bunu destekliyor: saf 21 günlük getiri faktör olarak NEGATİF
        (−0.29pp, kazanma %43). Son ayı dahil etmek iki farklı olguyu tek
        sayıya karıştırır.
        """
        panel = pd.DataFrame({
            "ticker": ["A"],
            "ret_21": [50.0],      # son ay patlamış
            "ret_126": [50.0],     # 6 aylık getiri de aynı → önceki 5 ay DÜZ
            "ret_252": [50.0],
            "dist_high52_pct": [-1.0],
            "vol_ann_63": [30.0],
        })
        raw = factors.raw_factors(panel)
        # (1+0.50)/(1+0.50) - 1 = 0 → son ay dışlandığında momentum YOK
        assert raw["mom_6_1"].iloc[0] == pytest.approx(0.0)
        assert raw["mom_12_1"].iloc[0] == pytest.approx(0.0)

    def test_formul_bilesik_getiriden_turetilir(self):
        panel = pd.DataFrame({
            "ticker": ["A"], "ret_21": [10.0], "ret_126": [33.0], "ret_252": [70.0],
            "dist_high52_pct": [-5.0], "vol_ann_63": [40.0]})
        raw = factors.raw_factors(panel)
        assert raw["mom_6_1"].iloc[0] == pytest.approx((1.33 / 1.10 - 1) * 100)
        assert raw["mom_12_1"].iloc[0] == pytest.approx((1.70 / 1.10 - 1) * 100)

    def test_zirve_yakinligi_dogrudan_tasinir(self):
        panel = pd.DataFrame({
            "ticker": ["A"], "ret_21": [0.0], "ret_126": [0.0], "ret_252": [0.0],
            "dist_high52_pct": [-12.5], "vol_ann_63": [20.0]})
        assert factors.raw_factors(panel)["high52_prox"].iloc[0] == -12.5

    def test_sifir_volatilite_sifira_BOLMEZ(self):
        """vol=0 → volscaled_mom NaN olmalı, sonsuz DEĞİL.

        `inf` bir skora girerse z-skor tüm kesiti bozar ve hata fırlatmaz.
        """
        panel = pd.DataFrame({
            "ticker": ["A"], "ret_21": [0.0], "ret_126": [20.0], "ret_252": [30.0],
            "dist_high52_pct": [-1.0], "vol_ann_63": [0.0]})
        v = factors.raw_factors(panel)["volscaled_mom"].iloc[0]
        assert pd.isna(v)


# ============================================================ kapılar
class TestKapilar:
    def test_temiz_satir_gecer(self, cfg):
        uygun, nedenler = factors.eligibility_gates(_row(), TEMIZ_KALITE, cfg)
        assert uygun and nedenler == []

    def test_sma200_altinda_elenir(self, cfg):
        tol = float(cfg["faktorler"]["kapilar"]["sma200_tolerans"])
        r = _row(c_tr=100.0, sma200_tr=100.0 / (1 - tol) + 1.0)
        uygun, nedenler = factors.eligibility_gates(r, TEMIZ_KALITE, cfg)
        assert not uygun and "sma200_alti" in nedenler

    def test_tolerans_icinde_kalirsa_gecer(self, cfg):
        """Tolerans BANDIN İÇİNİ kapsar; sınırda elemek kapıyı sıkılaştırır."""
        tol = float(cfg["faktorler"]["kapilar"]["sma200_tolerans"])
        r = _row(c_tr=100.0 * (1 - tol), sma200_tr=100.0)
        uygun, nedenler = factors.eligibility_gates(r, TEMIZ_KALITE, cfg)
        assert uygun, nedenler

    def test_sma200_yoksa_elenir(self, cfg):
        uygun, nedenler = factors.eligibility_gates(
            _row(sma200_tr=np.nan), TEMIZ_KALITE, cfg)
        assert not uygun and "sma200_yok" in nedenler

    def test_likidite_zayifsa_elenir(self, cfg):
        esik = float(cfg["evren"]["min_medyan_islem_hacmi_try"])
        uygun, nedenler = factors.eligibility_gates(
            _row(turnover_med_63=esik - 1), TEMIZ_KALITE, cfg)
        assert not uygun and "likidite_zayif" in nedenler

    def test_likidite_bilinmiyorsa_elenir(self, cfg):
        """"Bilinmiyor" ile "yeterli" AYNI ÇIKTIYA DÜŞMEZ."""
        uygun, nedenler = factors.eligibility_gates(
            _row(turnover_med_63=np.nan), TEMIZ_KALITE, cfg)
        assert not uygun and "likidite_bilinmiyor" in nedenler

    def test_kalite_KAYDI_YOKSA_elenir(self, cfg):
        """`kalite is None` "sorun yok" DEĞİL "değerlendirilmedi" demektir.

        İlk sürüm bu bloğu tamamen atlıyordu: `bist veri kalite` koşulmayan her
        gün kalite kapısı SESSİZCE devre dışı kalıyordu (L-007 §3).
        """
        uygun, nedenler = factors.eligibility_gates(_row(), None, cfg)
        assert not uygun and "kalite_degerlendirilmedi" in nedenler

    def test_kalite_gecmezse_elenir(self, cfg):
        uygun, nedenler = factors.eligibility_gates(
            _row(), {"ok": False, "zero_vol_ratio_252": 0.0}, cfg)
        assert not uygun and "veri_kalitesi" in nedenler

    def test_sifir_hacim_orani_yuksekse_elenir(self, cfg):
        """SASA profili: 505 barın %23.2'sinde hacim sıfır."""
        esik = float(cfg["evren"]["maks_sifir_hacim_orani"])
        uygun, nedenler = factors.eligibility_gates(
            _row(), {"ok": True, "zero_vol_ratio_252": esik + 0.01}, cfg)
        assert not uygun and "sifir_hacim" in nedenler

    def test_kurumsal_islem_penceresi_eler(self, cfg):
        uygun, nedenler = factors.eligibility_gates(
            _row(), TEMIZ_KALITE, cfg, ex_date_in_window=True)
        assert not uygun and "kurumsal_islem" in nedenler

    @pytest.mark.parametrize("alan", ["mom_6_1", "mom_12_1"])
    def test_faktor_yoksa_elenir(self, cfg, alan):
        uygun, nedenler = factors.eligibility_gates(
            _row(**{alan: np.nan}), TEMIZ_KALITE, cfg)
        assert not uygun and f"{alan}_yok" in nedenler

    def test_nedenler_BIRIKIR(self, cfg):
        """Tek sebep raporlamak, düzelten kişiyi ikinci turda tekrar patlatır."""
        r = _row(sma200_tr=np.nan, turnover_med_63=np.nan, mom_6_1=np.nan)
        uygun, nedenler = factors.eligibility_gates(r, None, cfg)
        assert not uygun
        assert {"sma200_yok", "likidite_bilinmiyor", "kalite_degerlendirilmedi",
                "mom_6_1_yok"} <= set(nedenler)


# ============================================================ kesitsel skor
def _raw3() -> pd.DataFrame:
    return pd.DataFrame({
        "ticker": ["A", "B", "C"],
        "mom_6_1": [10.0, 0.0, -10.0],
        "mom_12_1": [10.0, 0.0, -10.0],
        "high52_prox": [-1.0, -5.0, -20.0],
        "volscaled_mom": [0.5, 0.0, -0.5],
    })


def _hepsi_uygun(tickerlar) -> dict:
    return {t: (True, []) for t in tickerlar}


class TestKesitselSkor:
    def test_siralama_ve_yuzdelik_bandi(self, cfg):
        out = factors.cross_sectional_scores(
            _raw3(), _hepsi_uygun("ABC"), cfg, horizon_days=20)
        s = out.set_index("ticker")
        assert s.loc["A", "score"] > s.loc["B", "score"] > s.loc["C", "score"]
        assert s.loc["A", "rank"] == 1 and s.loc["C", "rank"] == 3
        assert s.loc["A", "pct"] == pytest.approx(100.0)
        assert s.loc["C", "pct"] == pytest.approx(0.0)
        assert out["pct"].dropna().between(0, 100).all()

    def test_UYGUN_OLMAYAN_isim_digerlerinin_skorunu_DEGISTIRMEZ(self, cfg):
        """z TÜM evrende hesaplanır — kapı sıralamayı değiştirir, SKORU DEĞİL.

        Uygun olmayanı z tabanından çıkarmak, kalan isimlerin skorunu kendileri
        hiç değişmediği halde değiştirir. O zaman "skor" bir ismin özelliği
        değil, o gün kimin elendiğinin fonksiyonu olur.
        """
        hepsi = factors.cross_sectional_scores(
            _raw3(), _hepsi_uygun("ABC"), cfg, horizon_days=20).set_index("ticker")
        c_elendi = factors.cross_sectional_scores(
            _raw3(), {"A": (True, []), "B": (True, []), "C": (False, ["sma200_alti"])},
            cfg, horizon_days=20).set_index("ticker")
        assert c_elendi.loc["A", "score"] == pytest.approx(hepsi.loc["A", "score"])
        assert c_elendi.loc["B", "score"] == pytest.approx(hepsi.loc["B", "score"])
        # ...ama sıralama yalnız uygunlar arasında
        assert pd.isna(c_elendi.loc["C", "rank"])
        assert c_elendi.loc["A", "rank"] == 1 and c_elendi.loc["B", "rank"] == 2

    def test_elenen_ismin_skoru_YINE_HESAPLANIR(self, cfg):
        """Skoru olan ama uygun olmayan isim: skor var, sıra YOK.

        Bu ayrım HF-22'nin dayanağı: `yuzdelik is None` "sıralamadaki yeri
        bilinmiyor" demektir ve o isme `strong_buy` verilemez.
        """
        out = factors.cross_sectional_scores(
            _raw3(), {"A": (False, ["likidite_zayif"]), "B": (True, []),
                      "C": (True, [])}, cfg, horizon_days=20).set_index("ticker")
        assert np.isfinite(out.loc["A", "score"])
        assert pd.isna(out.loc["A", "pct"])

    def test_eksik_faktor_PAYDADAN_DUSER(self, cfg):
        """Eksik faktör 0 oy DEĞİL, hiç oy değildir.

        0 saymak skoru sıfıra doğru çeker: veri yokluğu "nötr görüş"e dönüşür ve
        eksik verisi olan isim yapay olarak ortalamaya yaklaşır.
        """
        raw = _raw3()
        raw.loc[0, "volscaled_mom"] = np.nan          # A'nın bir faktörü yok
        out = factors.cross_sectional_scores(
            raw, _hepsi_uygun("ABC"), cfg, horizon_days=20).set_index("ticker")

        w = factors.effective_weights(cfg, 20)
        var = [f for f in factors.FACTOR_NAMES
               if w[f] != 0 and np.isfinite(out.loc["A", f"z_{f}"])]
        pay = sum(w[f] * out.loc["A", f"z_{f}"] for f in var)
        payda = sum(abs(w[f]) for f in var)
        assert out.loc["A", "score"] == pytest.approx(pay / payda)

        # 0 sayılmış olsaydı payda TÜM sıfır-olmayan ağırlıkların toplamı olurdu
        payda_yanlis = sum(abs(v) for v in w.values() if v != 0)
        if abs(payda_yanlis - payda) > 1e-9:
            assert out.loc["A", "score"] != pytest.approx(pay / payda_yanlis)

    def test_hicbir_faktor_yoksa_skor_NaN(self, cfg):
        raw = _raw3()
        for f in factors.FACTOR_NAMES:
            raw[f] = np.nan
        # `np.where` iki dalı da hesaplar → 0/0 uyarısı; sonuç yine NaN.
        with np.errstate(invalid="ignore"):
            out = factors.cross_sectional_scores(
                raw, _hepsi_uygun("ABC"), cfg, horizon_days=20)
        assert out["score"].isna().all()
        assert out["rank"].isna().all()

    def test_gate_reasons_JSON_olarak_saklanir(self, cfg):
        out = factors.cross_sectional_scores(
            _raw3(), {"A": (True, []), "B": (False, ["sma200_alti", "sifir_hacim"]),
                      "C": (True, [])}, cfg, horizon_days=20).set_index("ticker")
        assert json.loads(out.loc["B", "gate_reasons"]) == ["sma200_alti", "sifir_hacim"]
        assert json.loads(out.loc["A", "gate_reasons"]) == []

    def test_uygunluk_bilinmeyen_ticker_VARSAYILAN_ELENIR(self, cfg):
        """Uygunluk sözlüğünde olmayan isim "uygun" sayılmaz."""
        out = factors.cross_sectional_scores(
            _raw3(), {"A": (True, [])}, cfg, horizon_days=20).set_index("ticker")
        assert not out.loc["B", "eligible"]
        assert json.loads(out.loc["B", "gate_reasons"]) == ["bilinmiyor"]

    def test_tek_uygun_isimde_yuzdelik_100(self, cfg):
        out = factors.cross_sectional_scores(
            _raw3(), {"A": (True, []), "B": (False, ["x"]), "C": (False, ["x"])},
            cfg, horizon_days=20).set_index("ticker")
        assert out.loc["A", "pct"] == pytest.approx(100.0)
        assert out.loc["A", "rank"] == 1

    def test_sektor_notr_VARSAYILAN_KAPALI(self, cfg):
        """Ölçüldü: sektör nötralizasyonu kenarı düşürüyor (6-1 mom t: 1.86→0.62).

        Kod yolu duruyor ama varsayılan KAPALI olmalı; açmak ölçülmüş bir
        gerekçe ister.
        """
        assert cfg["faktorler"]["sektor_notr"] is False
        smap = {"A": "banka", "B": "banka", "C": "sanayi"}
        kapali = factors.cross_sectional_scores(
            _raw3(), _hepsi_uygun("ABC"), cfg, sector_map=smap, horizon_days=20)
        acik_cfg = {**cfg, "faktorler": {**cfg["faktorler"], "sektor_notr": True}}
        acik = factors.cross_sectional_scores(
            _raw3(), _hepsi_uygun("ABC"), acik_cfg, sector_map=smap, horizon_days=20)
        assert not np.allclose(kapali["z_mom_6_1"], acik["z_mom_6_1"])

    def test_sektor_demean_ortalamayi_sifirlar(self):
        z = np.array([2.0, 0.0, -1.0, 1.0])
        tickerlar = ["A", "B", "C", "D"]
        smap = {"A": "x", "B": "x", "C": "y", "D": "y"}
        out = factors._sector_demean(z, tickerlar, smap)
        assert out[:2].mean() == pytest.approx(0.0)
        assert out[2:].mean() == pytest.approx(0.0)


# ============================================================ ağırlıklar
class TestEtkinAgirliklar:
    def test_toplam_bire_normalize(self, cfg):
        for h in (5, 20, 21, 42, 63):
            w = factors.effective_weights(cfg, h)
            assert sum(abs(v) for v in w.values()) == pytest.approx(1.0)

    def test_kisa_ufukta_high52_sifirlanir(self, cfg):
        esik = int(cfg["faktorler"]["high52_min_ufuk_gun"])
        assert factors.effective_weights(cfg, esik - 1)["high52_prox"] == 0.0
        assert factors.effective_weights(cfg, esik)["high52_prox"] > 0.0

    def test_sifirlanan_agirlik_DIGERLERINE_dagitilir(self, cfg):
        """Yeniden normalize edilmezse toplam <1 kalır ve skor küçülür —
        sıralamayı bozmaz ama skorun ölçeğini sessizce değiştirir."""
        kisa = factors.effective_weights(cfg, 20)
        uzun = factors.effective_weights(cfg, 42)
        assert kisa["mom_6_1"] > uzun["mom_6_1"]
        assert sum(kisa.values()) == pytest.approx(1.0)

    def test_ufuk_verilmezse_zaman_bariyeri_kullanilir(self, cfg):
        assert (factors.effective_weights(cfg)
                == factors.effective_weights(cfg, cfg["planlayici"]["zaman_bariyeri_gun"]))

    def test_negatif_agirlik_MUTLAK_degerle_normalize(self, cfg):
        """Ölçüm tersini söylerse negatif ağırlık MEŞRU bir kullanımdır.

        İşaretli normalize etmek, negatif ağırlıklı faktörün kendini paydada
        götürmesine ve skorun işaretinin geri dönmesine yol açardı.
        """
        c = {**cfg, "faktorler": {**cfg["faktorler"],
                                  "agirliklar": {"mom_6_1": 0.5, "mom_12_1": -0.5,
                                                 "high52_prox": 0.0,
                                                 "volscaled_mom": 0.0}}}
        w = factors.effective_weights(c, 42)
        assert sum(abs(v) for v in w.values()) == pytest.approx(1.0)
        assert w["mom_12_1"] < 0


class TestWeightsHash:
    """Skoru üreten AYAR SETİNİN parmak izi — çatallanma mekanizması.

    `factor_daily` birincil anahtarında `weights_hash` var: imza değişmezse
    farklı ayarla üretilen satır ESKİSİNİN ÜSTÜNE yazar ve geçmiş ölçüm sessizce
    kaybolur.
    """

    @pytest.mark.parametrize("yama", [
        {"sektor_notr": True},
        {"winsor_pct": [10, 90]},
        {"set_version": "factors_v2"},
        {"high52_min_ufuk_gun": 30},
        {"agirliklar": {"mom_6_1": 1.0, "mom_12_1": 0.0,
                        "high52_prox": 0.0, "volscaled_mom": 0.0}},
    ])
    def test_ayar_degisince_imza_DEGISIR(self, cfg, yama):
        h1 = factors.weights_hash(cfg)
        h2 = factors.weights_hash({**cfg, "faktorler": {**cfg["faktorler"], **yama}})
        assert h1 != h2, f"{list(yama)} imzayı etkilemiyor"

    def test_ilgisiz_ayar_imzayi_ETKILEMEZ(self, cfg):
        """İmza yalnız SKORU üreten ayarları kapsar; rapor dili girmez."""
        h1 = factors.weights_hash(cfg)
        h2 = factors.weights_hash({**cfg, "rapor": {**cfg["rapor"], "dil": "en"}})
        assert h1 == h2

    def test_imza_kisa_ve_kararli(self, cfg):
        h = factors.weights_hash(cfg)
        assert len(h) == 12 and h == factors.weights_hash(cfg)


# ============================================================ boru hattı
def _gun_kur(con, cfg, tickerlar, tarih="2024-06-03", *, gosterge_olanlar=None):
    """Belirli bir gün için bars + (seçilen tickerlarda) indicator satırı kurar."""
    gosterge_olanlar = tickerlar if gosterge_olanlar is None else gosterge_olanlar
    for i, t in enumerate(tickerlar):
        add_universe(con, t, sector=f"sek{i}")
        add_bars(con, t, [(tarih, 100.0, 101.0, 99.0, 100.0, 5_000_000.0, 100.0)])
        if t in gosterge_olanlar:
            add_indicator(con, cfg, t, tarih,
                          ret_21=1.0 + i, ret_63=3.0, ret_126=10.0 + i,
                          ret_252=20.0 + i, dist_high52_pct=-2.0 - i,
                          vol_ann_63=30.0, turnover_med_63=900_000_000.0,
                          sma200_tr=80.0, sma50_tr=95.0, atr14=2.0)
    return tarih


class TestBoruHatti:
    def test_kesit_DARSA_uyarir(self, cfg, con, caplog):
        """L-007 kilidi: payda düştüğünde SÖYLENMELİ.

        `_panel` JOIN'i göstergesi olmayan ismi sessizce düşürür; `pct` yine
        0-100 arasına yayılır, yani sıralamanın ANLAMI değişir ve hiçbir yerde
        yazmaz.
        """
        tarih = _gun_kur(con, cfg, ["AAA", "BBB", "CCC"],
                         gosterge_olanlar=["AAA", "BBB"])
        with caplog.at_level("WARNING"):
            df = factors.compute_for_date(cfg, con, tarih, ["AAA", "BBB", "CCC"],
                                          kalite={t: TEMIZ_KALITE
                                                  for t in ("AAA", "BBB", "CCC")})
        assert len(df) == 2
        assert "kesit DAR" in caplog.text
        assert "3 ticker istendi, 2" in caplog.text

    def test_hic_gosterge_yoksa_BOS_ve_uyari(self, cfg, con, caplog):
        tarih = _gun_kur(con, cfg, ["AAA"], gosterge_olanlar=[])
        with caplog.at_level("WARNING"):
            df = factors.compute_for_date(cfg, con, tarih, ["AAA"])
        assert df.empty
        assert "gösterge bulunan YOK" in caplog.text

    def test_bos_ticker_listesi_patlamaz(self, cfg, con):
        assert factors.compute_for_date(cfg, con, "2024-06-03", []).empty

    def test_kalite_gecirilmezse_HEPSI_elenir(self, cfg, con):
        """`kalite` verilmezse `{}` olur → her isim "değerlendirilmedi" → ELENİR.

        Bu bilinçli: replay gibi geçmişe dönük çağıranlar o güne ait kaliteyi
        kendileri hesaplayıp geçirmek ZORUNDA.
        """
        tarih = _gun_kur(con, cfg, ["AAA", "BBB"])
        df = factors.compute_for_date(cfg, con, tarih, ["AAA", "BBB"])
        assert not df["eligible"].any()
        assert all("kalite_degerlendirilmedi" in json.loads(r)
                   for r in df["gate_reasons"])

    def test_kalite_gecirilince_uygun_olur(self, cfg, con):
        tarih = _gun_kur(con, cfg, ["AAA", "BBB"])
        df = factors.compute_for_date(
            cfg, con, tarih, ["AAA", "BBB"],
            kalite={"AAA": TEMIZ_KALITE, "BBB": TEMIZ_KALITE})
        assert df["eligible"].all()

    def test_store_ve_geri_okuma(self, cfg, con):
        tarih = _gun_kur(con, cfg, ["AAA", "BBB", "CCC"])
        df = factors.compute_for_date(
            cfg, con, tarih, ["AAA", "BBB", "CCC"],
            kalite={t: TEMIZ_KALITE for t in ("AAA", "BBB", "CCC")})
        n = factors.store(cfg, con, df)
        assert n == 3
        satirlar = con.execute(
            "SELECT ticker, score, rank, pct, eligible, weights_hash "
            "  FROM factor_daily WHERE date = ? ORDER BY ticker", (tarih,)).fetchall()
        assert len(satirlar) == 3
        assert {r[5] for r in satirlar} == {factors.weights_hash(cfg)}
        for r in satirlar:
            assert r[4] == 1
            assert isinstance(r[2], int) and r[2] >= 1

    def test_bos_df_store_sifir(self, cfg, con):
        assert factors.store(cfg, con, pd.DataFrame()) == 0

    def test_NaN_None_olarak_saklanir(self, cfg, con):
        """`_n`/`_i`: NaN sayıya çevrilmez. NOT NULL olmayan kolonlarda NULL."""
        assert factors._n(np.nan) is None
        assert factors._n(np.inf) is None
        assert factors._n("x") is None
        assert factors._i(np.nan) is None
        assert factors._i(3.7) == 3

    def test_agirlik_degisince_ESKI_SATIR_KORUNUR(self, cfg, con):
        """Ağırlık değişince satır ÇATALLANIR, üstüne yazılmaz.

        `weights_hash` birincil anahtarın parçası olduğu için iki ayar seti aynı
        gün için ayrı satırlar üretir — yavaş döngü eski ölçümleri bozmadan
        çalışabilir.
        """
        tarih = _gun_kur(con, cfg, ["AAA", "BBB", "CCC"])
        kal = {t: TEMIZ_KALITE for t in ("AAA", "BBB", "CCC")}
        df = factors.compute_for_date(cfg, con, tarih, ["AAA", "BBB", "CCC"], kalite=kal)
        factors.store(cfg, con, df)

        yeni = {**cfg, "faktorler": {**cfg["faktorler"],
                                     "agirliklar": {"mom_6_1": 1.0, "mom_12_1": 0.0,
                                                    "high52_prox": 0.0,
                                                    "volscaled_mom": 0.0}}}
        factors.store(yeni, con, factors.compute_for_date(
            yeni, con, tarih, ["AAA", "BBB", "CCC"], kalite=kal))
        n_hash = con.execute(
            "SELECT COUNT(DISTINCT weights_hash) FROM factor_daily").fetchone()[0]
        assert n_hash == 2
        assert con.execute("SELECT COUNT(*) FROM factor_daily").fetchone()[0] == 6
