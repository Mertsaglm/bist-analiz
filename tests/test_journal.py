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


class TestSureliVeto:
    """⚠ REGRESYON KİLİDİ (2026-08-07, Merdiven'in süreli "bypass" fikrinden).

    NE EKSİKTİ: veto bir KOŞUYA bağlıydı, takvime değil. Bugün `haber_riski`
    diye veto edilen bir isim, hiçbir şey değişmeden yarın tertemiz görünüyordu
    — ertesi günün paketinde vetonun izi yoktu. ADR #008'den beri veto sistemin
    kalan ANA ürünü; ömrü tek bir koşu kadar olamaz.

    Süre İŞLEM GÜNÜ cinsindendir (duvar saati değil): uzun tatillerde vetoyu
    erken düşürmek, tam da piyasanın kapalı olduğu için hiçbir şeyin
    değişmediği günlerde korumayı kaldırmak olurdu.
    """

    @staticmethod
    def _veto(con, ticker, asof, kod, run="r1"):
        from src import db
        db.upsert_many(con, "llm_runs",
                       ["run_id", "asof", "tool", "bundle_sha", "output_path",
                        "audit_passed", "created_utc"],
                       [(run, asof, "test", "sha", "/dev/null", 1, "now")])
        db.upsert_many(
            con, "predictions",
            ["prediction_id", "run_id", "asof", "ticker", "signal", "action",
             "confidence", "confidence_p", "veto_code", "factor_set_version",
             "weights_hash", "indicator_set_version", "regime", "thesis",
             "counter_scenario", "key_risk", "falsifier", "close_at_asof",
             "created_utc"],
            [(f"p-{ticker}-{asof}-{run}", run, asof, ticker, "hold", "plan_reddet",
              "orta", 0.5, kod, "v1", "h", "v1", "neutral", "t", "c",
              "GEREKÇE-METNİ", "f", 10.0, "now")])

    def test_veto_ERTESI_GUN_de_aktif(self, cfg, con):
        from src import journal
        from tests.conftest import add_index, is_gunleri
        g = is_gunleri(30, "2026-07-01")
        add_index(con, "XU100", g)
        self._veto(con, "AAA", g[10], "haber_riski")        # süre 3 işlem günü
        v = journal.aktif_vetolar(cfg, con, g[11])
        assert "AAA" in v, "veto ertesi gün buharlaştı"
        assert v["AAA"][0]["kalan_islem_gunu"] >= 1

    def test_suresi_dolan_veto_DUSER(self, cfg, con):
        from src import journal
        from tests.conftest import add_index, is_gunleri
        g = is_gunleri(30, "2026-07-01")
        add_index(con, "XU100", g)
        self._veto(con, "AAA", g[5], "haber_riski")         # 3 işlem günü
        assert "AAA" not in journal.aktif_vetolar(cfg, con, g[12])

    def test_sure_VETO_KODUNA_gore_degisir(self, cfg, con):
        """`likidite_zayif` yapısaldır, `haber_riski` hızla soğur."""
        from src import journal
        from tests.conftest import add_index, is_gunleri
        g = is_gunleri(40, "2026-07-01")
        add_index(con, "XU100", g)
        self._veto(con, "AAA", g[5], "haber_riski", run="rA")
        self._veto(con, "BBB", g[5], "likidite_zayif", run="rB")
        v = journal.aktif_vetolar(cfg, con, g[15])
        assert "AAA" not in v, "kısa süreli veto hâlâ aktif"
        assert "BBB" in v, "uzun süreli veto erken düştü"

    def test_gerekce_ve_arac_TASINIR(self, cfg, con):
        """Veto neden konuldu ve hangi araç koydu — ikisi de kayıpsız gelmeli."""
        from src import journal
        from tests.conftest import add_index, is_gunleri
        g = is_gunleri(20, "2026-07-01")
        add_index(con, "XU100", g)
        self._veto(con, "AAA", g[10], "tez_zayif")
        x = journal.aktif_vetolar(cfg, con, g[11])["AAA"][0]
        assert x["gerekce"] == "GEREKÇE-METNİ"
        assert x["arac"] == "test"
        assert x["konuldu"] == g[10] and x["bitis"] > g[10]

    def test_vetosuz_tahmin_LISTEYE_GIRMEZ(self, cfg, con):
        from src import journal
        from tests.conftest import add_index, is_gunleri
        g = is_gunleri(20, "2026-07-01")
        add_index(con, "XU100", g)
        from src import db
        db.upsert_many(con, "llm_runs",
                       ["run_id", "asof", "tool", "bundle_sha", "output_path",
                        "audit_passed", "created_utc"],
                       [("r0", g[10], "test", "s", "/dev/null", 1, "now")])
        db.upsert_many(
            con, "predictions",
            ["prediction_id", "run_id", "asof", "ticker", "signal", "action",
             "confidence", "confidence_p", "factor_set_version", "weights_hash",
             "indicator_set_version", "regime", "thesis", "counter_scenario",
             "key_risk", "falsifier", "close_at_asof", "created_utc"],
            [("pz", "r0", g[10], "ZZZ", "hold", "izle", "orta", 0.5, "v1", "h",
              "v1", "neutral", "t", "c", "k", "f", 10.0, "now")])
        assert "ZZZ" not in journal.aktif_vetolar(cfg, con, g[11])

    def test_AYNI_veto_tekrar_ederse_TEK_SATIR(self, cfg, con):
        """⚠ Gerçek koşuda görüldü (2026-08-05): EUPWR'de `rejim_uyumsuz`
        DÖRT kez listeleniyordu — art arda koşan günlük analiz aynı vetoyu her
        gün yeniden koyuyor. Hepsini basmak bilgi değil GÜRÜLTÜ üretir ve
        okuyanı asıl uyarılardan uzaklaştırır.
        """
        from src import journal
        from tests.conftest import add_index, is_gunleri
        g = is_gunleri(30, "2026-07-01")
        add_index(con, "XU100", g)
        for i, gun in enumerate(g[8:11]):
            self._veto(con, "AAA", gun, "rejim_uyumsuz", run=f"r{i}")
        v = journal.aktif_vetolar(cfg, con, g[11])["AAA"]
        assert len(v) == 1, f"aynı veto {len(v)} kez listelendi"
        assert v[0]["tekrar"] == 3, "tekrar sayısı kayboldu"

    def test_tekrarda_EN_GEC_biten_kazanir(self, cfg, con):
        """Koruma en UZUN süreye göre yaşamalı — erken bitene indirgenmemeli."""
        from src import journal
        from tests.conftest import add_index, is_gunleri
        g = is_gunleri(30, "2026-07-01")
        add_index(con, "XU100", g)
        self._veto(con, "AAA", g[8], "rejim_uyumsuz", run="rA")
        self._veto(con, "AAA", g[10], "rejim_uyumsuz", run="rB")   # daha geç
        v = journal.aktif_vetolar(cfg, con, g[11])["AAA"][0]
        assert v["konuldu"] == g[10]
        assert v["kalan_islem_gunu"] >= 1

    def test_FARKLI_veto_kodlari_AYRI_kalir(self, cfg, con):
        """Tekilleştirme koda göredir; iki ayrı sebep tek satıra sıkışmaz."""
        from src import journal
        from tests.conftest import add_index, is_gunleri
        g = is_gunleri(30, "2026-07-01")
        add_index(con, "XU100", g)
        self._veto(con, "AAA", g[10], "rejim_uyumsuz", run="rA")
        self._veto(con, "AAA", g[10], "likidite_zayif", run="rB")
        assert len({x["veto_code"] for x in
                    journal.aktif_vetolar(cfg, con, g[11])["AAA"]}) == 2
