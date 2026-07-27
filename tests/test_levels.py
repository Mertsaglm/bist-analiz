"""Seviye testleri.

`test_look_ahead_korumasi` bu dosyanın varlık sebebidir: geçmezse seviyelere
dayanan HER ölçüm geçersizdir — ve geçersizliği fark edilmez, çünkü sonuçlar
"çok iyi" çıkar.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import levels as lv


def _bars(closes: list[float], *, yuksek_carpan: float = 1.01,
          dusuk_carpan: float = 0.99) -> pd.DataFrame:
    n = len(closes)
    return pd.DataFrame({
        "date": [f"2024-{1 + i // 28 % 12:02d}-{1 + i % 28:02d}" for i in range(n)],
        "o": closes,
        "h": [c * yuksek_carpan for c in closes],
        "l": [c * dusuk_carpan for c in closes],
        "c": closes,
        "v": [1_000_000] * n,
        "c_tr": closes,
        "turnover_try": [1e9] * n,
    })


class TestPivot:
    def test_tepe_bulunur(self):
        h = np.array([1, 2, 3, 10, 3, 2, 1], dtype=float)
        l = np.array([1, 1, 1, 1, 1, 1, 1], dtype=float)
        piv = lv.find_pivots(h, l, [f"g{i}" for i in range(7)], k=3)
        tepeler = [p for p in piv if p.kind == "tepe"]
        assert any(p.idx == 3 and p.price == 10 for p in tepeler)

    def test_confirm_idx_k_bar_sonra(self):
        """Bir pivot ancak k bar SONRA bilinebilir."""
        h = np.array([1, 2, 3, 10, 3, 2, 1], dtype=float)
        l = np.ones(7)
        piv = lv.find_pivots(h, l, [f"g{i}" for i in range(7)], k=3)
        tepe = next(p for p in piv if p.kind == "tepe" and p.idx == 3)
        assert tepe.confirm_idx == 3 + 3

    def test_kenarlarda_pivot_yok(self):
        h = np.arange(10, dtype=float)
        piv = lv.find_pivots(h, h, [f"g{i}" for i in range(10)], k=3)
        assert all(3 <= p.idx <= 6 for p in piv)


class TestLookAhead:
    def test_look_ahead_korumasi(self):
        """t anında `confirm_idx > t` olan pivot ASLA kullanılamaz.

        Kurgu: serinin SONUNA doğru belirgin bir tepe var. asof_idx tam o
        tepenin üstündeyken, tepe henüz doğrulanmamıştır (k bar geçmemiştir)
        ve seviyeye DÖNÜŞMEMELİDİR.
        """
        closes = [100.0] * 300 + [100 + i for i in range(10)] + [109.0]
        # 310. barda zirve; k=5 ile ancak 315'te doğrulanabilir
        df = _bars(closes)
        cfg = {"seviyeler": {"pivot_k": 5, "pencere_bar": 500,
                             "yeniden_hesap_bar": 10, "kumeleme_atr_carpani": 0.5,
                             "min_dokunus": 2, "set_version": "t"}}
        zirve_idx = len(closes) - 1
        sev = lv.build_levels(df, cfg, asof_idx=zirve_idx, atr=1.0)
        # Zirvenin kendisi seviye olarak GÖRÜNMEMELİ
        assert all(s.price < 108.0 for s in sev), (
            f"doğrulanmamış pivot seviyeye dönüşmüş: {[s.price for s in sev]}")

    def test_gec_asof_ile_pivot_gorunur(self):
        """Aynı pivot, yeterli bar geçtikten SONRA görünür hale gelmeli."""
        closes = ([100.0] * 200 + [100 + i for i in range(10)]
                  + [109.0] + [100.0] * 50 + [109.0] * 2 + [100.0] * 50)
        df = _bars(closes)
        cfg = {"seviyeler": {"pivot_k": 5, "pencere_bar": 500,
                             "yeniden_hesap_bar": 10, "kumeleme_atr_carpani": 2.0,
                             "min_dokunus": 2, "set_version": "t"}}
        sev = lv.build_levels(df, cfg, asof_idx=len(closes) - 1, atr=1.0)
        assert sev, "yeterli gecikmeden sonra da seviye bulunamadı"


class TestSeviyeler:
    def test_min_dokunus_uygulanir(self):
        # Düz taban KULLANILMAZ: sabit seride her bar hem max hem min olur ve
        # yüzlerce sahte pivot üretir. Hafif eğimli + periyodik tepe.
        closes = [100.0 + i * 0.05 + (5 if i % 40 == 20 else 0) for i in range(300)]
        df = _bars(closes)
        cfg = {"seviyeler": {"pivot_k": 5, "pencere_bar": 500,
                             "yeniden_hesap_bar": 10, "kumeleme_atr_carpani": 1.0,
                             "min_dokunus": 20, "set_version": "t"}}
        assert lv.build_levels(df, cfg, atr=1.0) == []

    def test_bos_veri_bos_liste(self):
        cfg = {"seviyeler": {"pivot_k": 5, "pencere_bar": 500,
                             "yeniden_hesap_bar": 10, "kumeleme_atr_carpani": 1.0,
                             "min_dokunus": 2, "set_version": "t"}}
        assert lv.build_levels(pd.DataFrame(), cfg) == []


class TestZirve:
    def test_zirvede_ustte_direnc_YOK(self):
        """Fiyat tüm zamanların zirvesindeyse üstte direnç YOKTUR —
        o bölgede hiç işlem geçmemiştir. Perakende TA'nın direnç uydurduğu yer."""
        seviyeler = [lv.Level(90.0, "destek", 3, "2024-01-01", "2024-02-01", 10),
                     lv.Level(95.0, "destek", 2, "2024-01-01", "2024-02-01", 10)]
        assert lv.resistances_above(seviyeler, 100.0) == []

    def test_at_all_time_high(self):
        df = _bars([10, 20, 30, 40, 50], yuksek_carpan=1.0, dusuk_carpan=1.0)
        assert lv.at_all_time_high(df)
        df2 = _bars([10, 50, 30, 40, 45], yuksek_carpan=1.0, dusuk_carpan=1.0)
        assert not lv.at_all_time_high(df2)

    def test_en_yakin_alt_ust(self):
        s = [lv.Level(90.0, "destek", 3, "a", "b", 1),
             lv.Level(95.0, "destek", 2, "a", "b", 1),
             lv.Level(110.0, "direnc", 2, "a", "b", 1)]
        assert lv.nearest_below(s, 100.0).price == 95.0
        assert lv.nearest_above(s, 100.0).price == 110.0
        assert lv.nearest_above(s, 200.0) is None


class TestGercekVeri:
    def test_gercek_hissede_seviye_uretiliyor(self, real_cfg, real_con):
        from src import indicators, prices
        df = prices.bars(real_con, "THYAO")
        if len(df) < 300:
            pytest.skip("yeterli veri yok")
        ind = indicators.enrich(df, real_cfg)
        sev = lv.build_levels(df, real_cfg, atr=float(ind["atr14"].iloc[-1]))
        assert sev, "gerçek veride hiç seviye bulunamadı"
        assert all(s.touches >= real_cfg["seviyeler"]["min_dokunus"] for s in sev)

    def test_gecmis_asof_gelecegi_gormez(self, real_cfg, real_con):
        """Aynı hissede iki farklı asof: erken asof, geç asof'un seviyelerini
        BİLEMEZ. Bilirse look-ahead sızıntısı var demektir."""
        from src import prices
        df = prices.bars(real_con, "THYAO")
        if len(df) < 800:
            pytest.skip("yeterli veri yok")
        erken = lv.build_levels(df, real_cfg, asof_idx=500, atr=5.0)
        gec = lv.build_levels(df, real_cfg, asof_idx=700, atr=5.0)
        erken_tarihler = {s.last_date for s in erken}
        sinir = df["date"].iloc[500]
        assert all(d <= sinir for d in erken_tarihler), (
            "erken asof, gelecekteki bir pivotu kullanmış")
        assert gec is not None


class TestKumeGenisligi:
    """⚠ REGRESYON KİLİDİ (2026-07-27 denetimi).

    `_cluster` tek-bağlantı (single linkage) yapıyordu: yeni pivot kümenin
    SON üyesiyle karşılaştırılıyordu. Ardışık farkların her biri ≤ tolerans
    olan bir zincir toplamda N × tolerans kadar yayılabilir ve kümenin
    ORTALAMASI hiçbir gerçek pivotun bulunmadığı bir fiyata düşebilir —
    `planner`'ın "hedefler UYDURULMAZ" kuralının sessiz ihlali.
    """

    def _piv(self, fiyatlar):
        return [lv.Pivot(i, f"2024-01-{i+1:02d}", p, "tepe", i)
                for i, p in enumerate(fiyatlar)]

    def test_zincir_tek_kumeye_TOPLANMAZ(self):
        # 10.0 → 10.9 → 11.8 → 12.7: ardışık farklar 0.9 ≤ 1.0 ama
        # toplam yayılım 2.7 — tek küme olsaydı ortalama 11.35 çıkardı ve
        # o fiyatta HİÇBİR pivot yok.
        kumeler = lv._cluster(self._piv([10.0, 10.9, 11.8, 12.7]), 1.0, 1)
        assert len(kumeler) > 1, "tek-bağlantı zinciri hâlâ tek küme üretiyor"
        for k in kumeler:
            assert k.spread <= 1.0 + 1e-9, f"küme toleranstan geniş: {k.spread}"

    def test_gercekten_yakin_pivotlar_toplanir(self):
        kumeler = lv._cluster(self._piv([10.0, 10.2, 10.4]), 1.0, 2)
        assert len(kumeler) == 1 and kumeler[0].touches == 3

    def test_spread_tasiniyor(self):
        k = lv._cluster(self._piv([10.0, 10.4]), 1.0, 2)[0]
        assert abs(k.spread - 0.4) < 1e-9


class TestSaklama:
    """`levels_daily` artık gerçekten yazılıyor (uzun süre boştu). Yazılan bir
    tablonun OKUYUCUSU da olmalı; `load` o okuyucudur ve burada sabitlenir."""

    def test_gidis_donus(self, cfg, con):
        sev = [lv.Level(90.0, "destek", 3, "2024-01-01", "2024-02-01", 10, 0.4),
               lv.Level(110.0, "direnc", 2, "2024-01-05", "2024-03-01", 12, 0.0)]
        lv.store(cfg, con, "AAA", "2024-03-05", sev)
        geri = lv.load(cfg, con, "AAA", "2024-03-05")
        assert geri == sev, "seviyeler kayıptan sonra birebir geri gelmiyor"

    def test_spread_de_saklaniyor(self, cfg, con):
        lv.store(cfg, con, "AAA", "2024-03-05",
                 [lv.Level(90.0, "destek", 3, "a", "b", 10, 0.75)])
        assert lv.load(cfg, con, "AAA", "2024-03-05")[0].spread == 0.75

    def test_kayit_yoksa_bos_liste(self, cfg, con):
        assert lv.load(cfg, con, "YOK", "2024-03-05") == []
