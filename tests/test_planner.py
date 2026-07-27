"""Plan üretici testleri.

Plan üreticinin sözleşmesi: ürettiği HER plan `validate_option`'ı geçer.
LLM'e geçersiz plan sunulamaz — çünkü LLM'in tek işi menüden seçmek ve
menüdeki geçersiz bir satır doğrudan uygulanamaz bir karara dönüşür.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src import levels as lv, planner, risk
from tests.conftest import add_universe


def _bars(n: int = 300, taban: float = 100.0) -> pd.DataFrame:
    """Yükselen trend + düzenli geri çekilmeler (pivot üretsin diye)."""
    c = []
    for i in range(n):
        egim = taban + i * 0.15
        dalga = 3.0 * ((i % 20) - 10) / 10.0
        c.append(round(egim + dalga, 2))
    return pd.DataFrame({
        "date": [f"2024-{1 + i // 28 % 12:02d}-{1 + i % 28:02d}" for i in range(n)],
        "o": c, "h": [x * 1.012 for x in c], "l": [x * 0.988 for x in c],
        "c": c, "v": [1_000_000] * n, "c_tr": c, "turnover_try": [1e9] * n,
    })


@pytest.fixture
def kurulum(cfg):
    bars = _bars()
    fiyat = float(bars["c"].iloc[-1])
    ind = {"atr14": 2.5, "sma20": fiyat * 0.97, "sma50": fiyat * 0.94,
           "high_52w": fiyat * 1.25}
    sev = [
        lv.Level(fiyat * 0.95, "destek", 3, "2024-01-01", "2024-05-01", 10),
        lv.Level(fiyat * 1.08, "direnc", 3, "2024-01-01", "2024-05-01", 10),
        lv.Level(fiyat * 1.16, "direnc", 2, "2024-01-01", "2024-05-01", 10),
    ]
    rej = {"size_multiplier": 1.0, "max_positions": 5, "cash_pct": 40.0}
    return cfg, bars, ind, sev, rej


class TestSozlesme:
    def test_uretilen_her_plan_dogrulamayi_gecer(self, kurulum):
        cfg, bars, ind, sev, rej = kurulum
        opts, _ = planner.build_options(cfg, ticker="TEST", asof="2024-06-01",
                                        bars=bars, ind=ind, seviyeler=sev, regime=rej)
        assert opts, "hiç plan üretilmedi"
        for o in opts:
            assert planner.validate_option(o, cfg) == [], f"{o.plan_id} geçersiz"

    def test_stop_daima_giris_altinda(self, kurulum):
        cfg, bars, ind, sev, rej = kurulum
        opts, _ = planner.build_options(cfg, ticker="TEST", asof="2024-06-01",
                                        bars=bars, ind=ind, seviyeler=sev, regime=rej)
        for o in opts:
            assert o.stop_price < o.entry_low < o.entry_high

    def test_hedefler_daima_girisin_ustunde(self, kurulum):
        cfg, bars, ind, sev, rej = kurulum
        opts, _ = planner.build_options(cfg, ticker="TEST", asof="2024-06-01",
                                        bars=bars, ind=ind, seviyeler=sev, regime=rej)
        for o in opts:
            for t in o.targets:
                assert t["price"] > o.entry_high

    def test_tum_fiyatlar_tick_izgarasinda(self, kurulum):
        cfg, bars, ind, sev, rej = kurulum
        opts, _ = planner.build_options(cfg, ticker="TEST", asof="2024-06-01",
                                        bars=bars, ind=ind, seviyeler=sev, regime=rej)
        for o in opts:
            for f in (o.entry_low, o.entry_high, o.stop_price,
                      *(t["price"] for t in o.targets)):
                assert risk.on_tick_grid(f, cfg), f"{f} ızgarada değil"

    def test_stop_atr_bandi_icinde(self, kurulum):
        cfg, bars, ind, sev, rej = kurulum
        alt, ust = cfg["planlayici"]["stop_atr_bandi"]
        opts, _ = planner.build_options(cfg, ticker="TEST", asof="2024-06-01",
                                        bars=bars, ind=ind, seviyeler=sev, regime=rej)
        for o in opts:
            assert alt <= o.stop_atr_multiple <= ust

    def test_her_hedefin_dayanagi_var(self, kurulum):
        """Hedef UYDURULMAZ — her biri gerçek bir seviyeye dayanır."""
        cfg, bars, ind, sev, rej = kurulum
        opts, _ = planner.build_options(cfg, ticker="TEST", asof="2024-06-01",
                                        bars=bars, ind=ind, seviyeler=sev, regime=rej)
        for o in opts:
            for t in o.targets:
                assert t["basis"], "dayanaksız hedef — uydurulmuş seviye"


class TestPlanUretilmeyenDurumlar:
    def test_ustte_seviye_yoksa_plan_yok(self, kurulum):
        """Zirvede olan hisseye hedef uydurulmaz → plan üretilmez."""
        cfg, bars, ind, _, rej = kurulum
        ind2 = {**ind, "high_52w": float(bars["c"].iloc[-1]) * 0.9}
        opts, neden = planner.build_options(
            cfg, ticker="TEST", asof="2024-06-01", bars=bars, ind=ind2,
            seviyeler=[lv.Level(float(bars["c"].iloc[-1]) * 0.9, "destek", 3,
                                "a", "b", 1)], regime=rej)
        assert opts == []
        assert "seviye" in neden or "zirve" in neden

    def test_ex_tarihi_varsa_plan_yok(self, kurulum):
        """Plan penceresine düşen ex-tarih stop'u YAPAY tetikler."""
        cfg, bars, ind, sev, rej = kurulum
        opts, neden = planner.build_options(
            cfg, ticker="TEST", asof="2024-06-01", bars=bars, ind=ind,
            seviyeler=sev, regime=rej, ex_date="2024-06-15")
        assert opts == []
        assert "ex-tarih" in neden

    def test_atr_yoksa_plan_yok(self, kurulum):
        cfg, bars, ind, sev, rej = kurulum
        opts, neden = planner.build_options(
            cfg, ticker="TEST", asof="2024-06-01", bars=bars,
            ind={**ind, "atr14": None}, seviyeler=sev, regime=rej)
        assert opts == []
        assert "ATR" in neden

    def test_uzak_seviye_giris_bandi_uretmez(self, kurulum):
        """VAKA: EUPWR fiyat ~90 iken 3 yıl önceki 32 TL seviyesi 'destek
        retest' diye plan üretiyordu (R:R 6.39) — tetiklenemez artefakt."""
        cfg, bars, ind, _, rej = kurulum
        fiyat = float(bars["c"].iloc[-1])
        cok_uzak = [lv.Level(fiyat * 0.35, "destek", 5, "2021-01-01", "2021-06-01", 10),
                    lv.Level(fiyat * 1.10, "direnc", 3, "2024-01-01", "2024-05-01", 10)]
        opts, _ = planner.build_options(cfg, ticker="TEST", asof="2024-06-01",
                                        bars=bars, ind=ind, seviyeler=cok_uzak,
                                        regime=rej)
        for o in opts:
            uzaklik_atr = (fiyat - o.entry_low) / ind["atr14"]
            assert uzaklik_atr <= cfg["planlayici"]["maks_giris_uzakligi_atr"] + 1


class TestDogrulama:
    def _plan(self, **kw):
        temel = dict(
            plan_id="X-1", ticker="X", asof="2024-06-01", kind="dogrudan",
            entry_low=99.0, entry_high=100.0, entry_trigger="direct",
            stop_price=95.0, stop_method="atr_2x", stop_atr_multiple=2.0,
            targets=[{"price": 110.0, "rr": 2.0, "atr_distance": 4.0, "basis": "pivot"}],
            rr_at_t1=2.0, time_barrier_days=20, time_barrier_date="2024-06-28",
            position_size_pct=5.0, max_loss_pct_of_portfolio=0.25,
            entry_zone_status="in_zone", daily_limit_note="", ex_date_in_window=None)
        return planner.PlanOption(**{**temel, **kw})

    def test_gecerli_plan_temiz(self, cfg):
        assert planner.validate_option(self._plan(), cfg) == []

    def test_ters_giris_bandi_yakalanir(self, cfg):
        ihlal = planner.validate_option(self._plan(entry_low=101.0), cfg)
        assert any("entry_low" in x for x in ihlal)

    def test_stop_girisin_ustunde_yakalanir(self, cfg):
        ihlal = planner.validate_option(self._plan(stop_price=99.5), cfg)
        assert any("stop" in x for x in ihlal)

    def test_izgara_disi_fiyat_yakalanir(self, cfg):
        ihlal = planner.validate_option(self._plan(stop_price=95.033), cfg)
        assert any("ızgara" in x for x in ihlal)

    def test_dayanaksiz_hedef_yakalanir(self, cfg):
        ihlal = planner.validate_option(self._plan(
            targets=[{"price": 110.0, "rr": 2.0, "atr_distance": 4.0, "basis": ""}]), cfg)
        assert any("dayanağı" in x for x in ihlal)

    def test_dusuk_rr_yakalanir(self, cfg):
        ihlal = planner.validate_option(self._plan(rr_at_t1=0.5), cfg)
        assert any("R:R" in x for x in ihlal)

    def test_atr_bandi_disi_yakalanir(self, cfg):
        ihlal = planner.validate_option(self._plan(stop_atr_multiple=9.0), cfg)
        assert any("stop_atr_multiple" in x for x in ihlal)

    def test_bilinmeyen_enum_yakalanir(self, cfg):
        ihlal = planner.validate_option(self._plan(entry_trigger="uydurma"), cfg)
        assert any("entry_trigger" in x for x in ihlal)


class TestUyari:
    def test_her_planda_yeniden_cerceveleme_ibaresi(self, kurulum):
        """Ölçülen kenar yok — her plan bunu taşımalı (ADR #008)."""
        cfg, bars, ind, sev, rej = kurulum
        opts, _ = planner.build_options(cfg, ticker="TEST", asof="2024-06-01",
                                        bars=bars, ind=ind, seviyeler=sev, regime=rej)
        for o in opts:
            assert "kenar yok" in o.uyari
            assert "planlama geometrisi" in o.uyari


class TestKaliteKapisiVeReplay:
    """⚠ REGRESYON KİLİDİ (2026-07-27 denetimi, İKİ AŞAMALI).

    (1) `build_menu` kalite kaydı eksik olan ismi ELEMELİ — eksik kayıt
        "sorun yok" değildir.
    (2) AMA `data_quality` yalnız BUGÜNÜ tutar. Geçmişe dönük koşan replay
        tabloya güvenirse TAMAMI elenir — ilk düzeltmede tam olarak bu oldu:
        30 dönem × 3 isim = 90 plan_yok, **0 tahmin**. Bu yüzden `build_menu`
        `kalite` parametresi kabul eder ve replay o güne ait kaliteyi kendisi
        hesaplayıp geçirir (look-ahead yok: `assess_quality` yalnız
        `date <= asof` barlarını okur).
    """

    @staticmethod
    def _gosterge_ekle(con, ticker="AAA", tarih="2024-01-02"):
        """Kalite kapısına ULAŞABİLMEK için gösterge satırı şart —
        `build_menu` önce `gösterge yok` diye eler."""
        con.execute(
            "INSERT OR REPLACE INTO indicator_daily "
            "(ticker,date,set_version,atr14,sma20,sma50,computed_utc) "
            "VALUES (?,?,?,?,?,?,?)",
            (ticker, tarih, "core_indicators_v1", 2.5, 99.0, 98.0, "x"))
        con.commit()

    def test_kalite_kaydi_yoksa_ELENIR(self, cfg, con):
        from src import planner
        add_universe(con, "AAA")
        self._gosterge_ekle(con)
        r = planner.build_menu(cfg, con, "2024-01-02", tickers=["AAA"])
        assert "veri kalitesi" in r["atlanan"]["AAA"], \
            f"kalite kaydı yokken kapı sessizce açık kaldı: {r['atlanan']['AAA']}"

    def test_kalite_gecirilince_kapi_gecilir(self, cfg, con):
        from src import planner
        add_universe(con, "AAA")
        self._gosterge_ekle(con)
        r = planner.build_menu(cfg, con, "2024-01-02", tickers=["AAA"],
                               kalite={"AAA": {"ok": True, "reasons": []}})
        assert "veri kalitesi" not in r["atlanan"]["AAA"], \
            "kalite geçirildiği halde kapı yine de eledi — replay çalışamaz"

    def test_replay_build_menu_KULLANIR(self):
        """Replay canlı hattı taklit ettiğini iddia ediyorsa onu KOŞMALI."""
        import inspect
        from src import replay
        kaynak = inspect.getsource(replay.run)
        assert "planner.build_menu(" in kaynak
        assert "planner.build_options(" not in kaynak, \
            "replay hâlâ build_options'ı doğrudan çağırıyor — kalite ve " \
            "ex-tarih kapıları koşmuyor demektir"

    def test_replay_kaliteyi_O_GUNE_gore_hesaplar(self):
        """Tabloya güvenirse replay'in TAMAMI elenir (ölçüldü: 0 tahmin)."""
        import inspect
        from src import replay
        kaynak = inspect.getsource(replay.run)
        assert "assess_quality" in kaynak and "store=False" in kaynak
