"""Tahmin günlüğü testleri — DEĞİŞMEZLİK ve görev bölüşümü.

Journal'ın sözleşmesi iki cümle: analist yalnız enum ve prose yazar, sayıları
kod yazar; ve yazılan kayıt DEĞİŞMEZ.
"""

from __future__ import annotations

import pytest

from src import journal
from tests.conftest import add_plan, add_universe


ANALIST = {"signal": "buy", "action": "plan_sec", "confidence": "orta",
           "thesis": "tez", "counter_scenario": "karşıt", "key_risk": "risk",
           "falsifier": "yanlışlayıcı"}

PLAN = {"plan_id": "P1", "entry_low": 99.0, "entry_high": 100.0,
        "stop_price": 95.0, "targets": [{"price": 110.0}, {"price": 120.0}],
        "rr_at_t1": 2.0, "time_barrier_date": "2024-01-30",
        "position_size_pct": 5.0}

FAKTOR = {"score": 1.23, "rank": 2, "pct": 88.0, "weights_hash": "abc123"}

REFERANS = {"close": 100.0, "xu100": 9000.0, "atr14": 2.5}


@pytest.fixture
def run_id(cfg, con):
    add_universe(con, "TEST")
    add_plan(con, "P1")
    return journal.create_run(cfg, con, asof="2024-01-02", tool="test",
                              bundle_sha="sha1")


class TestGorevBolusumu:
    def test_confidence_p_KOD_yazar(self, cfg, con, run_id):
        """LLM enum verir, olasılığı KOD yazar. Kalibre edilmemiş bir sayıyı
        LLM'e yazdırmak, ölçüm zincirine denetlenmemiş bir değer sokmaktır."""
        journal.record(cfg, con, run_id=run_id, asof="2024-01-02", ticker="TEST",
                       analist=ANALIST, plan=PLAN, faktor=FAKTOR, referans=REFERANS)
        r = con.execute("SELECT confidence, confidence_p FROM predictions").fetchone()
        assert r["confidence"] == "orta"
        assert r["confidence_p"] == pytest.approx(cfg["llm"]["guven_olasilik"]["orta"])

    def test_plan_fiyatlari_plandan_gelir(self, cfg, con, run_id):
        journal.record(cfg, con, run_id=run_id, asof="2024-01-02", ticker="TEST",
                       analist=ANALIST, plan=PLAN, faktor=FAKTOR, referans=REFERANS)
        r = con.execute("SELECT * FROM predictions").fetchone()
        assert r["entry_high"] == 100.0
        assert r["stop_price"] == 95.0
        assert r["t1_price"] == 110.0
        assert r["t2_price"] == 120.0

    def test_analist_sema_disina_yazamaz(self, cfg, con, run_id):
        """Sessizce yok saymak, LLM'in şemayı genişletmeye çalıştığını gizlerdi."""
        with pytest.raises(ValueError, match="şemanın dışına"):
            journal.record(cfg, con, run_id=run_id, asof="2024-01-02",
                           ticker="TEST", analist={**ANALIST, "stop_price": 42.0},
                           plan=PLAN, faktor=FAKTOR, referans=REFERANS)

    def test_analist_fiyat_yazamaz(self, cfg, con, run_id):
        for yasak in ("entry_low", "t1_price", "position_size_pct", "confidence_p"):
            with pytest.raises(ValueError):
                journal.record(cfg, con, run_id=run_id, asof="2024-01-02",
                               ticker="TEST", analist={**ANALIST, yasak: 1.0},
                               plan=PLAN, faktor=FAKTOR, referans=REFERANS)

    @pytest.mark.parametrize("alan,kotu", [
        ("signal", "yukselir"), ("action", "al_hemen"), ("confidence", "%80")])
    def test_izinsiz_enum_reddedilir(self, cfg, con, run_id, alan, kotu):
        with pytest.raises(ValueError, match="enum"):
            journal.record(cfg, con, run_id=run_id, asof="2024-01-02",
                           ticker="TEST", analist={**ANALIST, alan: kotu},
                           plan=PLAN, faktor=FAKTOR, referans=REFERANS)

    def test_sayisal_guven_reddedilir(self, cfg, con, run_id):
        """Güven SAYI olarak gelemez — enum olmak zorunda."""
        with pytest.raises(ValueError):
            journal.record(cfg, con, run_id=run_id, asof="2024-01-02",
                           ticker="TEST", analist={**ANALIST, "confidence": 0.75},
                           plan=PLAN, faktor=FAKTOR, referans=REFERANS)

    def test_zorunlu_alan_eksikse_patlar(self, cfg, con, run_id):
        eksik = {k: v for k, v in ANALIST.items() if k != "signal"}
        with pytest.raises(ValueError, match="eksik"):
            journal.record(cfg, con, run_id=run_id, asof="2024-01-02",
                           ticker="TEST", analist=eksik, plan=PLAN, faktor=FAKTOR, referans=REFERANS)


class TestDegismezlik:
    def test_ayni_kayit_ikinci_kez_yazilamaz(self, cfg, con, run_id):
        """Journal DÜZELTİLMEZ. Yanlışsa yeni bir run açılır."""
        journal.record(cfg, con, run_id=run_id, asof="2024-01-02", ticker="TEST",
                       analist=ANALIST, plan=PLAN, faktor=FAKTOR, referans=REFERANS)
        with pytest.raises(RuntimeError, match="DEĞİŞMEZ"):
            journal.record(cfg, con, run_id=run_id, asof="2024-01-02",
                           ticker="TEST", analist=ANALIST, plan=PLAN, faktor=FAKTOR, referans=REFERANS)

    def test_yeni_run_ile_yeniden_yazilabilir(self, cfg, con, run_id):
        journal.record(cfg, con, run_id=run_id, asof="2024-01-02", ticker="TEST",
                       analist=ANALIST, plan=PLAN, faktor=FAKTOR, referans=REFERANS)
        run2 = journal.create_run(cfg, con, asof="2024-01-02", tool="test",
                                  bundle_sha="sha2")
        assert run2 != run_id
        journal.record(cfg, con, run_id=run2, asof="2024-01-02", ticker="TEST",
                       analist=ANALIST, plan=PLAN, faktor=FAKTOR, referans=REFERANS)
        assert con.execute("SELECT COUNT(*) FROM predictions").fetchone()[0] == 2


class TestSorgular:
    def test_acik_tahminler(self, cfg, con, run_id):
        journal.record(cfg, con, run_id=run_id, asof="2024-01-02", ticker="TEST",
                       analist=ANALIST, plan=PLAN, faktor=FAKTOR, referans=REFERANS)
        assert len(journal.open_predictions(con)) == 1

    def test_ozet(self, cfg, con, run_id):
        journal.record(cfg, con, run_id=run_id, asof="2024-01-02", ticker="TEST",
                       analist=ANALIST, plan=PLAN, faktor=FAKTOR, referans=REFERANS)
        s = journal.summary(con)
        assert s["tahmin"] == 1 and s["acik"] == 1 and s["cozulen"] == 0


class TestPortfoy:
    def test_ekle_ve_sil(self, con):
        journal.set_holding(con, "TEST", 100, 42.0)
        assert journal.holdings(con)["TEST"]["qty"] == 100
        journal.set_holding(con, "TEST", 0)
        assert "TEST" not in journal.holdings(con)
