"""util testleri — özellikle sessiz bozulma üreten yerler."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from src import util


class TestToIsoDate:
    """Tarih normalizasyonu. Sıralanabilirlik kritik: 'GG-AA-YYYY' ile
    `ORDER BY date` kronolojik DEĞİLDİR ve bu sessizce yanlış sonuç üretir."""

    @pytest.mark.parametrize("girdi,beklenen", [
        ("2026-07-26", "2026-07-26"),          # zaten ISO
        ("2026-07-26T10:00:00", "2026-07-26"),  # ISO + saat
        ("26-07-2026", "2026-07-26"),          # GG-AA-YYYY (EVDS günlük)
        ("26.07.2026", "2026-07-26"),          # GG.AA.YYYY
        ("2026-7", "2026-07-01"),              # YYYY-A (EVDS aylık)
        ("2026-07", "2026-07-01"),             # YYYY-AA
        ("2026-Q3", "2026-07-01"),             # çeyreklik → çeyrek başı
        ("2026-Q1", "2026-01-01"),
        (date(2026, 7, 26), "2026-07-26"),
        (datetime(2026, 7, 26, 13, 5), "2026-07-26"),
        (None, None),
        ("", None),
        ("saçma", None),
    ])
    def test_bicimler(self, girdi, beklenen):
        assert util.to_iso_date(girdi) == beklenen

    def test_ggaayyyy_siralanabilir_hale_gelir(self):
        """Ham biçimde '05-01-2026' < '26-07-2025' (yanlış); ISO'da doğru sıralanır."""
        ham = sorted(["05-01-2026", "26-07-2025"])
        iso = sorted(util.to_iso_date(x) for x in ["05-01-2026", "26-07-2025"])
        assert ham[0] == "05-01-2026"          # ham sıralama yanlış
        assert iso == ["2025-07-26", "2026-01-05"]


class TestJson:
    def test_kanonik_bicim_kararli(self):
        """Aynı içerik → aynı sha, anahtar sırası fark etmez.

        bundle_sha bunun üzerine kurulu: LLM çıktısı hangi paketi analiz ettiğini
        bu sha ile kanıtlar (HF-02).
        """
        a = {"b": 1, "a": [1, 2], "c": {"y": 2, "x": 1}}
        b = {"c": {"x": 1, "y": 2}, "a": [1, 2], "b": 1}
        assert util.sha256_canonical(a) == util.sha256_canonical(b)

    def test_icerik_degisince_sha_degisir(self):
        assert util.sha256_canonical({"a": 1}) != util.sha256_canonical({"a": 2})

    def test_nan_none_olur(self):
        """json.dumps varsayılanı geçersiz JSON olan çıplak `NaN` yazar."""
        s = util.json_dump({"x": float("nan"), "y": float("inf"), "z": 1.5})
        assert "NaN" not in s and "Infinity" not in s
        assert '"x": null' in s and '"y": null' in s

    def test_turkce_karakter_korunur(self):
        assert "ölçüm" in util.json_dump({"a": "ölçüm"})

    def test_atomik_yazma(self, tmp_path):
        """Yarım dosya bırakmaz: tmp + rename."""
        p = tmp_path / "x" / "y.json"
        util.write_json(p, {"a": 1})
        assert util.read_json(p) == {"a": 1}
        assert not list(p.parent.glob("*.tmp")), "geçici dosya temizlenmemiş"

    def test_olmayan_dosya_default_doner(self, tmp_path):
        assert util.read_json(tmp_path / "yok.json", default={"d": 1}) == {"d": 1}


class TestSayi:
    @pytest.mark.parametrize("girdi,beklenen", [
        ("1.234,56", 1234.56),
        ("45,71", 45.71),
        ("1234.56", 1234.56),
        ("%12,5", 12.5),
        ("1.234,56 TL", 1234.56),
        (42, 42.0),
        (None, None),
        ("", None),
        ("abc", None),
    ])
    def test_tr_sayi(self, girdi, beklenen):
        assert util.parse_tr_number(girdi) == beklenen

    def test_pct_sifir_paydada_none(self):
        """Payda 0 → None, 0 DEĞİL. 0 döndürmek 'değişim yok' anlamına gelir
        ve bu, 'hesaplanamadı'dan tamamen farklıdır."""
        assert util.pct(10, 0) is None
        assert util.pct(10, None) is None
        assert util.pct(None, 10) is None
        assert util.pct(110, 100) == pytest.approx(10.0)
