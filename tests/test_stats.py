"""Ölçüm çekirdeği testleri — projenin epistemolojisi burada sabitlenir.

Bu dosyadaki `test_sahte_devasa_alfa_yine_de_yetersiz` tek başına projenin
dürüstlük sözleşmesini kodluyor: sistem erken kenar iddia EDEMEZ.
"""

from __future__ import annotations

import numpy as np
import pytest

from src import stats


class TestEdgeVerdict:
    """ZAYIF N, BÜYÜK FARKI EZER — bu fonksiyonun bütün amacı."""

    def test_zayif_n_buyuk_farki_ezer(self):
        h = stats.edge_verdict(diff_p=5.0, n=3, weak_n=15, min_diff_p=1.0)
        assert h.startswith(stats.HUKUM_YETERSIZ)
        assert "N=3" in h

    def test_yeterli_n_kucuk_fark_kenar_yok(self):
        assert stats.edge_verdict(0.4, 100, 15, 1.0) == stats.HUKUM_KENAR_YOK

    def test_yeterli_n_buyuk_fark_zayif_kanit(self):
        assert stats.edge_verdict(2.5, 100, 15, 1.0).startswith(stats.HUKUM_ZAYIF_KANIT)

    def test_dogrulandi_hukmu_YOK(self):
        """En güçlü ifade 'zayıf kanıt'tır. Ne kadar büyük olursa olsun."""
        for fark in (1.0, 10.0, 100.0, 1e6):
            h = stats.edge_verdict(fark, 10_000, 15, 1.0)
            assert h.startswith(stats.HUKUM_ZAYIF_KANIT)
            assert "doğrulan" not in h.lower()
            assert "kanıtlan" not in h.lower()

    def test_isaret_hukumde_gorunur(self):
        """Hüküm BÜYÜKLÜK hükmüdür ama işareti metinde taşımalı —
        yoksa kaybettiren faktör 'kanıt' sanılır (gerçek hata, 2026-07-26)."""
        assert "-" in stats.edge_verdict(-2.5, 100, 15, 1.0)
        assert "+" in stats.edge_verdict(+2.5, 100, 15, 1.0)

    @pytest.mark.parametrize("d,n", [(None, 10), (1.0, 0), (float("nan"), 50)])
    def test_olcum_yok(self, d, n):
        assert stats.edge_verdict(d, n, 15, 1.0) == stats.HUKUM_OLCUM_YOK


class TestRequiredN:
    def test_formul(self):
        # (2 × 5.0 / 0.72)² ≈ 192.9 → 193
        assert stats.required_n(0.72, 5.0) == 193

    def test_kucuk_sinyal_devasa_n_ister(self):
        assert stats.required_n(0.1, 5.0) > 9000

    def test_isaret_onemsiz(self):
        assert stats.required_n(-0.72, 5.0) == stats.required_n(0.72, 5.0)

    @pytest.mark.parametrize("ort,sd", [(0, 5.0), (1.0, 0), (None, 5.0), (1.0, None)])
    def test_tanimsiz_none(self, ort, sd):
        assert stats.required_n(ort, sd) is None


class TestForwardReturns:
    def test_giris_t_arti_1(self):
        """Sinyalin oluştuğu barın KAPANIŞINDA işlem yapılamaz.

        close[t] ile giriş varsaymak look-ahead'in en yaygın biçimidir.
        """
        fiyat = [100, 110, 121, 133.1]
        # t=0 sinyali → giriş fiyat[1]=110, çıkış fiyat[2]=121 → +%10
        r = stats.forward_returns_nonoverlap(["d"] * 4, fiyat, [0], horizon=1)
        assert r == pytest.approx([10.0])

    def test_ortusme_atlanir(self):
        """Bir pencere kullanıldıysa sonraki giriş en az horizon gün ileriden."""
        fiyat = list(range(100, 130))
        idx = list(range(0, 20))               # her gün sinyal
        r = stats.forward_returns_nonoverlap(["d"] * 30, fiyat, idx, horizon=5)
        # 20 sinyalden yalnız ~4 bağımsız pencere çıkar
        assert len(r) <= 5, f"örtüşme engellenmemiş: {len(r)} pencere"

    def test_pencereler_gun_paylasmaz(self):
        """Değişmez: iki pencere hiçbir günü paylaşmaz."""
        fiyat = list(range(100, 200))
        idx = list(range(0, 90, 3))
        h = 10
        kullanilan, son = [], -1
        for t in sorted(idx):
            giris = t + 1
            if giris <= son:
                continue
            cikis = giris + h
            if cikis >= len(fiyat):
                continue
            kullanilan.append((giris, cikis))
            son = cikis
        for (a1, b1), (a2, b2) in zip(kullanilan, kullanilan[1:]):
            assert a2 >= b1, "pencereler örtüşüyor"

    def test_sinir_disi_atlanir(self):
        r = stats.forward_returns_nonoverlap(["d"] * 3, [1, 2, 3], [2], horizon=5)
        assert r == []

    def test_gecersiz_fiyat_atlanir(self):
        r = stats.forward_returns_nonoverlap(
            ["d"] * 4, [100, 0, 121, 133], [0], horizon=1)
        assert r == []          # giriş fiyatı 0 → kullanılamaz


class TestEtkinDonem:
    def test_sinyal_sayisi_donem_sayisi_degildir(self):
        """500 sinyal ile 500 bağımsız gözlem aynı şey DEĞİLDİR."""
        assert stats.effective_periods(500, 20) == 25


class TestSpearman:
    def test_mukemmel_siralama(self):
        assert stats.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)

    def test_ters_siralama(self):
        assert stats.spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)

    def test_dogrusal_olmayan_monoton_yine_1(self):
        """Sıra korelasyonu — büyüklüğe değil sıraya bakar."""
        assert stats.spearman([1, 2, 3, 4], [1, 4, 9, 1000]) == pytest.approx(1.0)

    def test_yetersiz_gozlem_none(self):
        assert stats.spearman([1, 2], [1, 2]) is None

    def test_sabit_seri_none(self):
        assert stats.spearman([1, 2, 3, 4], [5, 5, 5, 5]) is None

    def test_nan_atlanir(self):
        assert stats.spearman([1, 2, 3, float("nan")],
                              [1, 2, 3, 99]) == pytest.approx(1.0)


class TestKesitsel:
    def test_winsorize_ucu_kirpar_silmez(self):
        a = [1, 2, 3, 4, 5, 6, 7, 8, 9, 1000]
        w = stats.winsorize(a, 5, 95)
        assert len(w) == len(a)
        assert w.max() < 1000

    def test_zscore_ortalama_sifir(self):
        z = stats.zscore([1, 2, 3, 4, 5])
        assert float(np.nanmean(z)) == pytest.approx(0.0, abs=1e-9)

    def test_zscore_sabit_seri_sifira_bolmez(self):
        z = stats.zscore([5, 5, 5, 5])
        assert np.all(z == 0.0)

    def test_zscore_nan_korunur(self):
        z = stats.zscore([1, 2, float("nan"), 4])
        assert np.isnan(z[2])
        assert np.isfinite(z[0])


class TestDurustlukSozlesmesi:
    """Bu sınıf projenin en önemli testini içerir."""

    def test_sahte_devasa_alfa_yine_de_yetersiz(self):
        """5 döneme devasa sahte alfa besle — hüküm HÂLÂ 'ölçüm yetersiz' olmalı.

        Bu tek test, projenin epistemolojisinin tamamını kodluyor. Sistem
        erken kenar iddia EDERSE kod yalan söylüyordur; bu test o yalanı
        imkânsız kılar.
        """
        sahte = [50.0, 48.0, 52.0, 49.0, 51.0]        # dönem başına +%50 (!)
        s = stats.dist_stats(sahte, weak_n=15)
        h = stats.edge_verdict(s["ort"], s["n"], weak_n=15, min_diff_p=1.0)
        assert h.startswith(stats.HUKUM_YETERSIZ), (
            f"5 dönemle kenar iddia edildi: {h} — sistem kendini kandırıyor")

    def test_ic_ozeti_de_zayif_n_ile_yetersiz(self):
        s = stats.ic_summary([0.9, 0.85, 0.95], weak_n=15)
        assert s["hukum"].startswith(stats.HUKUM_YETERSIZ)

    def test_gerekli_n_daima_raporlanabilir(self):
        """'Ne zaman bilebiliriz?' bir his değil, basılmış bir sayı."""
        s = stats.dist_stats([0.7, -1.2, 2.0, 0.3, -0.5] * 10)
        assert s["gerekli_n"] is not None and s["gerekli_n"] > 0

    def test_bonferroni_notu_sayiyi_soyler(self):
        assert "54" in stats.bonferroni_note(54)
