"""Rejim testleri — PAYDA, DEFANSİF VARSAYILAN ve AĞIRLIKLARA DOKUNMAMA.

Üç iddia:

1. **Genişlik PAYDASINI döndürür.** Ölçüldü (2026-07-24 paketi): 67 isimlik
   ölçüm evreni istenmesine rağmen 16 isim kullanılmış, genişlik 5/16 = %31.25
   çıkmış ve `risk_off` eşiği tetiklenmişti — XU100 SMA200'ünün **%9.7
   ÜSTÜNDEYKEN**, nakit önerisi %90'a çıkmıştı. Kimse paydaya bakmıyordu.
2. **Eksik veri DAİMA defansif tarafa düşer.** Bilmemek, bilmek gibi
   davranmaktan iyidir.
3. **Rejim FAKTÖR AĞIRLIKLARINI ETKİLEMEZ.** Rejim-koşullu ağırlıklandırma
   klasik bir overfit kapısıdır: rejim tanımı bir serbestlik derecesidir ve
   dondurulmadan doğrulanamaz. Rejimin işi risk yönetimi — NE alacağını değil
   NE KADAR alacağını söyler.
"""

from __future__ import annotations

import json

import pytest

from src import regime, util

from tests.conftest import add_bars, add_indicator, add_universe, is_gunleri


def _xu100(con, n: int = 220, son: float = 100.0, taban: float = 100.0,
           sembol: str = "XU100") -> list[str]:
    """`n` barlık düz endeks serisi; SON bar `son` değerinde.

    SMA200 ~ `taban` olur, dolayısıyla `son`u değiştirmek XU100–SMA200 farkını
    doğrudan kontrol eder. Rejim eşiklerini bilinçli tetiklemenin en sade yolu.
    """
    tarihler = is_gunleri(n, "2023-01-02")
    now = util.utc_now_iso()
    con.executemany(
        "INSERT OR REPLACE INTO index_daily (symbol,date,o,h,l,c,ingested_utc) "
        "VALUES (?,?,?,?,?,?,?)",
        [(sembol, d, taban, taban, taban, taban, now) for d in tarihler[:-1]]
        + [(sembol, tarihler[-1], son, son, son, son, now)])
    con.commit()
    return tarihler


def _evren_kur(con, cfg, asof: str, *, n: int, gostergeli: int, ustunde: int):
    """`n` ölçüm ismi; `gostergeli` tanesinin göstergesi var, `ustunde` tanesi SMA50 üstü."""
    for i in range(n):
        t = f"T{i:02d}"
        add_universe(con, t, sector="sek", in_live=False, in_measure=True)
        add_bars(con, t, [(asof, 100.0, 101.0, 99.0, 100.0, 1e6, 100.0)])
        if i < gostergeli:
            add_indicator(con, cfg, t, asof,
                          sma50=90.0 if i < ustunde else 110.0, atr14=2.0)


# ============================================================ genişlik / payda
class TestGenislik:
    def test_payda_dondurulur(self, cfg, con):
        """`(pct, kullanilan_n, istenen_n)` — üçü birlikte.

        Yalnız oranı döndürmek, oranın hangi popülasyon üzerinde hesaplandığını
        gizler. Bu testin varlık sebebi: paydası yazılmayan her oran yalan
        söyleyebilir (LESSONS L-007).
        """
        asof = "2024-06-03"
        _evren_kur(con, cfg, asof, n=10, gostergeli=10, ustunde=6)
        pct, n, istenen = regime.breadth(con, cfg, asof)
        assert pct == pytest.approx(60.0)
        assert n == 10 and istenen == 10

    def test_gosterge_eksikse_payda_DUSER_ve_uyarir(self, cfg, con, caplog):
        """Göstergesi olmayan isim JOIN'de sessizce düşer — ama sessiz KALMAZ."""
        asof = "2024-06-03"
        _evren_kur(con, cfg, asof, n=10, gostergeli=5, ustunde=1)
        with caplog.at_level("WARNING"):
            pct, n, istenen = regime.breadth(con, cfg, asof)
        assert (n, istenen) == (5, 10)
        assert pct == pytest.approx(20.0)
        assert "DAR PAYDA" in caplog.text
        assert "5/10" in caplog.text

    def test_bes_isimden_az_ise_OLCULEMEZ(self, cfg, con, caplog):
        """4 isimle "piyasa genişliği" ölçülemez — None döner, 0 DEĞİL.

        0 döndürmek "genişlik yok" demek olurdu ve doğrudan `risk-off` tetiklerdi.
        """
        asof = "2024-06-03"
        _evren_kur(con, cfg, asof, n=8, gostergeli=4, ustunde=0)
        with caplog.at_level("WARNING"):
            pct, n, istenen = regime.breadth(con, cfg, asof)
        assert pct is None and n == 4 and istenen == 8
        assert "ölçülemiyor" in caplog.text

    def test_bos_evren_sifir_payda(self, cfg, con):
        assert regime.breadth(con, cfg, "2024-06-03") == (None, 0, 0)

    def test_HAM_kapanis_ile_karsilastirilir(self, cfg, con):
        """`sma50` FİYAT uzayında hesaplanıyor → `c` ile kıyaslanır.

        `c_tr` (toplam getiri) ile kıyaslamak birim hatasıdır: temettü kadar
        sistematik sapma üretir ve genişliği yapay olarak yükseltir.
        """
        asof = "2024-06-03"
        for i in range(6):
            t = f"D{i}"
            add_universe(con, t, in_live=False, in_measure=True)
            # c = 100 (SMA50 100'ün altında değil), ama c_tr = 130 → yalnız c_tr
            # kullanılsaydı hepsi "üstünde" sayılırdı.
            add_bars(con, t, [(asof, 100.0, 101.0, 99.0, 100.0, 1e6, 130.0)])
            add_indicator(con, cfg, t, asof, sma50=105.0)
        pct, n, _ = regime.breadth(con, cfg, asof)
        assert n == 6
        assert pct == pytest.approx(0.0), "c_tr ile karşılaştırılıyor olabilir"

    def test_gosterge_set_version_e_gore_suzulur(self, cfg, con):
        asof = "2024-06-03"
        _evren_kur(con, cfg, asof, n=6, gostergeli=6, ustunde=6)
        yabanci = {**cfg, "gostergeler": {**cfg["gostergeler"],
                                          "set_version": "baska_v9"}}
        pct, n, istenen = regime.breadth(con, yabanci, asof)
        assert pct is None and n == 0 and istenen == 6


# ============================================================ etiketleme
class TestEtiketleme:
    """`_label` saf fonksiyondur — eşik davranışı doğrudan sınanır."""

    @pytest.fixture
    def r(self, cfg):
        return cfg["rejim"]

    def test_eksik_girdi_TRANSITION(self, r):
        """Bilmiyorsak orta-defansif. `neutral` demek iyimserlik olurdu."""
        assert regime._label({"xu100_vs_sma200_pct": None,
                              "breadth_above_sma50_pct": 70.0}, r) == "transition"
        assert regime._label({"xu100_vs_sma200_pct": 10.0,
                              "breadth_above_sma50_pct": None}, r) == "transition"
        assert regime._label({}, r) == "transition"

    def test_risk_on_IKISINI_de_ister(self, r):
        on = r["esikler"]["risk_on"]
        f = float(on["xu100_sma200_farki_pct_min"])
        g = float(on["genislik_sma50_ustu_pct_min"])
        assert regime._label({"xu100_vs_sma200_pct": f,
                              "breadth_above_sma50_pct": g}, r) == "risk-on"
        # Endeks güçlü ama genişlik zayıf → ralli birkaç isme dayanıyor
        assert regime._label({"xu100_vs_sma200_pct": f + 20,
                              "breadth_above_sma50_pct": g - 1}, r) != "risk-on"

    def test_risk_off_BIRI_yeterli(self, r):
        off = r["esikler"]["risk_off"]
        f = float(off["xu100_sma200_farki_pct_maks"])
        g = float(off["genislik_sma50_ustu_pct_maks"])
        assert regime._label({"xu100_vs_sma200_pct": f,
                              "breadth_above_sma50_pct": 99.0}, r) == "risk-off"
        assert regime._label({"xu100_vs_sma200_pct": 99.0,
                              "breadth_above_sma50_pct": g}, r) == "risk-off"

    def test_zayif_ara_bolge_transition(self, r):
        assert regime._label({"xu100_vs_sma200_pct": -1.0,
                              "breadth_above_sma50_pct": 55.0}, r) == "transition"
        assert regime._label({"xu100_vs_sma200_pct": 1.0,
                              "breadth_above_sma50_pct": 45.0}, r) == "transition"

    def test_neutral_yalniz_iki_taraf_da_olumluysa(self, r):
        assert regime._label({"xu100_vs_sma200_pct": 1.0,
                              "breadth_above_sma50_pct": 55.0}, r) == "neutral"

    def test_uretilen_etiket_DAIMA_bilinen_kumede(self, r):
        for fark in (-50, -3.1, -3, -0.1, 0, 1, 2.9, 3, 50, None):
            for gen in (0, 20, 35, 36, 49, 50, 59, 60, 100, None):
                etiket = regime._label({"xu100_vs_sma200_pct": fark,
                                        "breadth_above_sma50_pct": gen}, r)
                assert etiket in regime.ETIKETLER, (fark, gen, etiket)
                assert etiket in r["politika"]


# ============================================================ sınıflandırma
class TestSiniflandirma:
    def test_guclu_endeks_ve_genis_katilim_risk_on(self, cfg, con):
        tarihler = _xu100(con, n=220, son=110.0)
        asof = tarihler[-1]
        _evren_kur(con, cfg, asof, n=10, gostergeli=10, ustunde=8)
        rej = regime.classify(cfg, con, asof)
        assert rej["label"] == "risk-on"
        assert rej["breadth_n"] == 10 and rej["breadth_istenen_n"] == 10
        assert rej["xu100_vs_sma200_pct"] > 3.0

    def test_zayif_endeks_risk_off(self, cfg, con):
        tarihler = _xu100(con, n=220, son=80.0)
        asof = tarihler[-1]
        _evren_kur(con, cfg, asof, n=10, gostergeli=10, ustunde=9)
        rej = regime.classify(cfg, con, asof)
        assert rej["label"] == "risk-off"

    def test_makro_eksikse_nakit_DEFANSIF_kayar(self, cfg, con):
        """EVDS verisi yokken nakit +10pp — BİLİNÇLİ muhafazakârlık.

        ⚠ `makro_eksik_pct` alanının ÜST SEVİYEDE görünmesi de test edilir:
        ilk sürümde `**girdiler` yayılmasından SONRA ekleniyordu ve alan yalnız
        `inputs` içinde kalıyordu (aynı sözlük nesnesi olduğu için fark
        edilmemişti).
        """
        tarihler = _xu100(con, n=220, son=110.0)
        asof = tarihler[-1]
        _evren_kur(con, cfg, asof, n=10, gostergeli=10, ustunde=8)
        rej = regime.classify(cfg, con, asof)
        taban = cfg["rejim"]["politika"]["risk-on"]["nakit_pct"]
        assert rej["makro_eksik_pct"] == pytest.approx(100.0)
        assert rej["cash_pct"] == pytest.approx(min(100.0, taban + 10.0))
        assert "makro_eksik_pct" in rej["inputs"]

    def test_politika_configten_gelir(self, cfg, con):
        tarihler = _xu100(con, n=220, son=110.0)
        asof = tarihler[-1]
        _evren_kur(con, cfg, asof, n=10, gostergeli=10, ustunde=8)
        rej = regime.classify(cfg, con, asof)
        pol = cfg["rejim"]["politika"]["risk-on"]
        assert rej["max_positions"] == pol["maks_pozisyon"]
        assert rej["size_multiplier"] == pol["boyut_carpani"]
        assert rej["sektor_basi_maks"] == cfg["rejim"]["sektor_basi_maks_pozisyon"]

    def test_veri_hic_yoksa_transition(self, cfg, con):
        rej = regime.classify(cfg, con, "2024-06-03")
        assert rej["label"] == "transition"
        assert rej["xu100_vs_sma200_pct"] is None

    def test_kisa_endeks_serisinde_sma200_yok(self, cfg, con):
        """200 bardan az veriyle SMA200 UYDURULMAZ."""
        tarihler = _xu100(con, n=50, son=110.0)
        rej = regime.classify(cfg, con, tarihler[-1])
        assert rej["xu100_vs_sma200_pct"] is None
        assert rej["label"] == "transition"

    def test_vol_hesabi_kisa_seride_None(self):
        import numpy as np
        assert regime._vol_ann(np.array([100.0] * 10)) is None
        assert regime._vol_ann(np.array([100.0] * 30)) == pytest.approx(0.0)

    def test_gelecege_BAKMAZ(self, cfg, con):
        """`asof` sonrası barlar rejime girmez — look-ahead'in en sinsi biçimi."""
        tarihler = _xu100(con, n=220, son=110.0)
        asof = tarihler[-1]
        _evren_kur(con, cfg, asof, n=10, gostergeli=10, ustunde=8)
        once = regime.classify(cfg, con, asof)
        # asof'tan SONRA çöküş ekle
        now = util.utc_now_iso()
        con.execute("INSERT OR REPLACE INTO index_daily "
                    "(symbol,date,o,h,l,c,ingested_utc) VALUES (?,?,?,?,?,?,?)",
                    ("XU100", "2030-12-31", 10.0, 10.0, 10.0, 10.0, now))
        con.commit()
        assert regime.classify(cfg, con, asof) == once


# ============================================================ dondurma
class TestSaklama:
    def test_store_girdileri_DENETLENEBILIR_yazar(self, cfg, con):
        """"2026-07-24'te neden risk-off dedik?" sorusunun cevabı bir yerde durmalı.

        Bu fonksiyon uzun süre HİÇ ÇAĞRILMADI (tablo 0 satır) — oysa `classify`
        docstring'i "girdiler denetlenebilir biçimde saklanır" diyordu. Yani
        belgelenmiş ama var olmayan bir savunmaydı (LESSONS L-002 deseni).
        """
        tarihler = _xu100(con, n=220, son=110.0)
        asof = tarihler[-1]
        _evren_kur(con, cfg, asof, n=10, gostergeli=6, ustunde=5)
        rej = regime.classify(cfg, con, asof)
        assert regime.store(cfg, con, rej) == 1

        satir = con.execute("SELECT * FROM regime_daily WHERE date = ?",
                            (asof,)).fetchone()
        assert satir["label"] == rej["label"]
        assert satir["cash_pct"] == rej["cash_pct"]
        girdiler = json.loads(satir["inputs"])
        # PAYDA da saklanmalı: oran tek başına yeniden üretilemez.
        assert girdiler["breadth_n"] == 6
        assert girdiler["breadth_istenen_n"] == 10
        assert "makro_eksik_pct" in girdiler

    def test_store_iki_kez_cogaltmaz(self, cfg, con):
        tarihler = _xu100(con, n=220, son=110.0)
        asof = tarihler[-1]
        _evren_kur(con, cfg, asof, n=10, gostergeli=10, ustunde=8)
        rej = regime.classify(cfg, con, asof)
        regime.store(cfg, con, rej)
        regime.store(cfg, con, rej)
        assert con.execute("SELECT COUNT(*) FROM regime_daily").fetchone()[0] == 1

    def test_plan_menusu_rejimi_DONDURUR(self, cfg, con):
        """`planner.build_menu` her çağrıda `regime.store` çağırmalı.

        LESSONS L-002: besleyen script yoksa tablo donar ve hiçbir hata
        fırlatmaz. Rejim girdileri her gün yeniden hesaplanıp atılıyordu.
        """
        from src import planner
        tarihler = _xu100(con, n=220, son=110.0)
        asof = tarihler[-1]
        _evren_kur(con, cfg, asof, n=10, gostergeli=10, ustunde=8)
        planner.build_menu(cfg, con, asof, tickers=[])
        assert con.execute("SELECT COUNT(*) FROM regime_daily WHERE date = ?",
                           (asof,)).fetchone()[0] == 1


# ============================================================ ağırlık sınırı
class TestRejimAgirliklaraDOKUNMAZ:
    def test_ciktida_agirlik_alani_YOK(self, cfg, con):
        """Rejim çıktısı faktör ağırlığı taşımaz — taşırsa biri onu kullanır."""
        tarihler = _xu100(con, n=220, son=110.0)
        asof = tarihler[-1]
        _evren_kur(con, cfg, asof, n=10, gostergeli=10, ustunde=8)
        rej = regime.classify(cfg, con, asof)
        yasak = {"agirliklar", "weights", "agirlik", "faktor_agirliklari"}
        assert not (set(rej) & yasak)
        assert not (set(rej["inputs"]) & yasak)

    def test_rejim_modulu_agirlik_fonksiyonunu_TANIMAZ(self):
        """Import grafiği de bu ayrımı korumalı.

        `regime.py` `factors.effective_weights`'i çağırabilir hale gelirse
        rejim-koşullu ağırlıklandırma bir satırlık mesafeye iner.
        """
        kaynak = (util.ROOT / "src" / "regime.py").read_text(encoding="utf-8")
        assert "effective_weights" not in kaynak
        assert "import factors" not in kaynak and "from . import factors" not in kaynak
