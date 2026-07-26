"""Sonuç çözümü testleri.

`test_ayni_gun_stop_kazanir` bu dosyanın en önemli testi: iyimser varsayım
(hedef kazanır) her backtest'i sistematik olarak şişirir ve şişme fark edilmez.
"""

from __future__ import annotations

import pytest

from src import journal, resolver
from tests.conftest import add_bars, add_index, add_plan, add_universe


class TestBariyer:
    def test_yalniz_stop(self):
        bar = {"o": 100, "h": 102, "l": 94, "c": 96}
        assert resolver.barrier_hit(bar, stop=95, target=110) == resolver.STOP

    def test_yalniz_hedef(self):
        bar = {"o": 100, "h": 112, "l": 99, "c": 111}
        assert resolver.barrier_hit(bar, stop=95, target=110) == resolver.HEDEF

    def test_hicbiri(self):
        bar = {"o": 100, "h": 105, "l": 98, "c": 102}
        assert resolver.barrier_hit(bar, stop=95, target=110) is None

    def test_ayni_gun_stop_kazanir(self):
        """⚠ EN ÖNEMLİ TEST. Gün içi sıra BİLİNEMEZ → kötümser kural.

        Bar hem 94'e (stop 95) hem 112'ye (hedef 110) gitmiş. Hangisinin önce
        olduğu günlük barla bilinemez. Hedefin kazandığını varsaymak her
        ölçümü şişirir; bu şişme sessizdir çünkü sonuçlar 'iyi' çıkar.
        """
        bar = {"o": 100, "h": 112, "l": 94, "c": 105}
        assert resolver.barrier_hit(bar, stop=95, target=110) == resolver.STOP

    def test_hedefsiz_plan(self):
        bar = {"o": 100, "h": 150, "l": 99, "c": 149}
        assert resolver.barrier_hit(bar, stop=95, target=None) is None


class TestCikisFiyati:
    def test_bosluk_asagida_acilistan_cikilir(self):
        """Limit-down açılışta stop FİYATINDAN çıkamazsın; açılıştan çıkarsın."""
        bar = {"o": 88.0, "c": 87.0}
        assert resolver.exit_price_for(bar, resolver.STOP, stop=95.0,
                                       target=110.0) == 88.0

    def test_normal_gunde_stop_fiyatindan(self):
        bar = {"o": 100.0, "c": 96.0}
        assert resolver.exit_price_for(bar, resolver.STOP, stop=95.0,
                                       target=110.0) == 95.0

    def test_hedef_bosluk_yukarida_acilistan(self):
        bar = {"o": 115.0, "c": 116.0}
        assert resolver.exit_price_for(bar, resolver.HEDEF, stop=95.0,
                                       target=110.0) == 115.0


class TestGiris:
    def _bars(self, satirlar):
        import pandas as pd
        return pd.DataFrame(satirlar)

    def test_banda_dokunulunca_dolar(self):
        bars = self._bars([
            {"date": "2024-01-02", "o": 105, "h": 106, "l": 104, "c": 105},
            {"date": "2024-01-03", "o": 103, "h": 104, "l": 99, "c": 100},
        ])
        d = resolver.entry_fill(bars, entry_low=98, entry_high=100, trigger="x")
        assert d is not None
        assert d[0] == "2024-01-03"

    def test_dolum_bandin_ust_ucundan(self):
        """Bandın İÇİNDEKİ en kötü fiyat — iyimser dolum slippage'ı gizler."""
        bars = self._bars([
            {"date": "2024-01-03", "o": 103, "h": 104, "l": 99, "c": 100}])
        _, fiyat = resolver.entry_fill(bars, entry_low=98, entry_high=100,
                                       trigger="x")
        assert fiyat == 100.0

    def test_acilis_bandin_altindaysa_acilistan(self):
        bars = self._bars([
            {"date": "2024-01-03", "o": 97, "h": 99, "l": 95, "c": 98}])
        _, fiyat = resolver.entry_fill(bars, entry_low=98, entry_high=100,
                                       trigger="x")
        assert fiyat == 97.0

    def test_dokunulmazsa_dolum_yok(self):
        bars = self._bars([
            {"date": "2024-01-02", "o": 105, "h": 106, "l": 104, "c": 105},
            {"date": "2024-01-03", "o": 106, "h": 107, "l": 105, "c": 106},
        ])
        assert resolver.entry_fill(bars, entry_low=98, entry_high=100,
                                   trigger="x") is None


class TestUctanUca:
    """Elle hesaplanmış fixture'larla tam çözüm."""

    def _kur(self, cfg, con, bar_satirlari, *, stop, t1, e_low, e_high,
             bariyer="2024-01-19"):
        add_universe(con, "TEST")
        add_plan(con, "P1")
        add_index(con, "XU100", [r[0] for r in bar_satirlari])
        add_bars(con, "TEST", bar_satirlari)
        run_id = journal.create_run(cfg, con, asof="2024-01-02", tool="test",
                                    bundle_sha="x")
        pid = journal.record(
            cfg, con, run_id=run_id, asof="2024-01-02", ticker="TEST",
            analist={"signal": "buy", "action": "plan_sec", "confidence": "orta",
                     "thesis": "t", "counter_scenario": "c", "key_risk": "k",
                     "falsifier": "f"},
            plan={"plan_id": "P1", "entry_low": e_low, "entry_high": e_high,
                  "stop_price": stop, "targets": [{"price": t1}],
                  "rr_at_t1": 2.0, "time_barrier_date": bariyer,
                  "position_size_pct": 5.0},
            faktor={"score": 1.0, "rank": 1, "pct": 90.0, "weights_hash": "h"},
            referans={"close": 100.0})
        return pid

    def test_hedef_vurulur(self, cfg, con):
        satirlar = [("2024-01-02", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-03", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-04", 100, 112, 99, 111, 1e6, 111),
                    ("2024-01-19", 111, 112, 110, 111, 1e6, 111)]
        self._kur(cfg, con, satirlar, stop=95, t1=110, e_low=99, e_high=100)
        r = resolver.resolve_open(cfg, con)
        assert r["dagilim"].get(resolver.HEDEF) == 1

    def test_stop_vurulur(self, cfg, con):
        satirlar = [("2024-01-02", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-03", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-04", 100, 101, 94, 95, 1e6, 95),
                    ("2024-01-19", 95, 96, 94, 95, 1e6, 95)]
        self._kur(cfg, con, satirlar, stop=95, t1=110, e_low=99, e_high=100)
        r = resolver.resolve_open(cfg, con)
        assert r["dagilim"].get(resolver.STOP) == 1

    def test_ayni_gun_ikisi_de_stop_kazanir(self, cfg, con):
        satirlar = [("2024-01-02", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-03", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-04", 100, 115, 94, 105, 1e6, 105),
                    ("2024-01-19", 105, 106, 104, 105, 1e6, 105)]
        self._kur(cfg, con, satirlar, stop=95, t1=110, e_low=99, e_high=100)
        r = resolver.resolve_open(cfg, con)
        assert r["dagilim"].get(resolver.STOP) == 1, "iyimser çözüm — hedef kazanmış"

    def test_sure_bariyeri(self, cfg, con):
        satirlar = [("2024-01-02", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-03", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-19", 102, 103, 101, 102, 1e6, 102)]
        self._kur(cfg, con, satirlar, stop=95, t1=110, e_low=99, e_high=100)
        r = resolver.resolve_open(cfg, con)
        assert r["dagilim"].get(resolver.SURE) == 1

    def test_giris_olmadi(self, cfg, con):
        """Tetiklenmemiş plan ne kazanç ne kayıptır — Brier'a GİRMEZ."""
        satirlar = [("2024-01-02", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-03", 120, 121, 119, 120, 1e6, 120),
                    ("2024-01-19", 130, 131, 129, 130, 1e6, 130)]
        self._kur(cfg, con, satirlar, stop=95, t1=110, e_low=98, e_high=99)
        resolver.resolve_open(cfg, con)
        o = con.execute("SELECT * FROM outcomes").fetchone()
        assert o["resolution"] == resolver.GIRIS_OLMADI
        assert o["ret_pct"] is None and o["hit"] is None

    def test_kurumsal_islem_iptal(self, cfg, con):
        """Ex-tarihte fiyat MEKANİK düşer; bunu kayıp saymak ölçümün hatasıdır."""
        satirlar = [("2024-01-02", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-03", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-04", 100, 101, 50, 52, 1e6, 100),
                    ("2024-01-19", 52, 53, 51, 52, 1e6, 100)]
        self._kur(cfg, con, satirlar, stop=95, t1=110, e_low=99, e_high=100)
        con.execute("INSERT INTO corporate_actions (ticker,date,kind,value,source) "
                    "VALUES ('TEST','2024-01-04','bolunme',2.0,'test')")
        con.commit()
        resolver.resolve_open(cfg, con)
        o = con.execute("SELECT * FROM outcomes").fetchone()
        assert o["resolution"] == resolver.IPTAL_KURUMSAL
        assert o["ret_pct"] is None, "kurumsal işlem kayıp olarak sayılmış"

    def test_maliyet_dusulur(self, cfg, con):
        satirlar = [("2024-01-02", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-03", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-04", 100, 112, 99, 111, 1e6, 111),
                    ("2024-01-19", 111, 112, 110, 111, 1e6, 111)]
        self._kur(cfg, con, satirlar, stop=95, t1=110, e_low=99, e_high=100)
        resolver.resolve_open(cfg, con)
        o = con.execute("SELECT * FROM outcomes").fetchone()
        maliyet = cfg["risk"]["islem_maliyeti_gidis_donus_pct"]
        assert o["ret_pct_gross"] - o["ret_pct"] == pytest.approx(maliyet, abs=0.001)


class TestHataEtiketi:
    def test_hizli_stop_ayirt_edilir(self, cfg, con):
        """3 gün içinde stop = tez daha başlamadan çöktü — ayrı bir olgu."""
        satirlar = [("2024-01-02", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-03", 100, 101, 99, 100, 1e6, 100),
                    ("2024-01-04", 100, 101, 94, 95, 1e6, 95),
                    ("2024-01-19", 95, 96, 94, 95, 1e6, 95)]
        TestUctanUca()._kur(cfg, con, satirlar, stop=95, t1=110,
                            e_low=99, e_high=100)
        resolver.resolve_open(cfg, con)
        o = con.execute("SELECT * FROM outcomes").fetchone()
        assert o["error_tag"] == "hizli_stop"
