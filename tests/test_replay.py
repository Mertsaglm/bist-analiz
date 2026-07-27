"""Replay testleri — VEKİL ANALİST ve KAYNAK AYRIMI.

Replay planın en yüksek getirili tek aracı: iki yıllık canlı beklemeyi
dakikalara indirir. Ama tam bu yüzden iki riski var ve ikisi de sessiz:

1. **Taklit ettiği hattı koşmazsa kanıt gücü yoktur.** İlk sürüm
   `planner.build_options`'ı DOĞRUDAN çağırıyor, `build_menu`'yü atlıyordu;
   böylece canlı hattaki üç kontrol replay'de HİÇ koşmuyordu (veri kalitesi
   kapısı, ex-tarih elemesi, `atlanan` gerekçesi). Replay'in tek işi "boru hattı
   çalışıyor mu"yu kanıtlamak — atladığı her kontrol o kanıttan düşer.

2. **Vekil analistin sayıları gerçek analizle KARIŞMAMALI.** Vekil kasten
   aptaldır (deterministik bir kural). Alfasını gerçek LLM kayıtlarıyla aynı
   potaya koymak, ölçümün ne ölçtüğünü belirsizleştirir — ve rapor bunu hiçbir
   yerde yazmaz. `tool='replay'` etiketi bu ayrımın taşıyıcısıdır.

(`build_menu` kullanımı ve kalitenin O GÜNE göre hesaplanması
`tests/test_planner.py::TestKaliteKapisiVeReplay` içinde ayrıca sabitli.)
"""

from __future__ import annotations

import pytest

from src import db, evaluate, journal, replay, resolver

from tests.conftest import add_plan, kur_sentetik_evren


# ============================================================ vekil analist
class TestVekilAnalist:
    def test_ilk_sirada_plan_secer(self, real_cfg):
        a = replay._vekil_analist(0, 10, 1.23)
        assert (a["signal"], a["action"]) == ("buy", "plan_sec")
        assert a["confidence"] == "orta"

    def test_ust_dilimde_biriktirir(self, real_cfg):
        a = replay._vekil_analist(1, 12, 0.5)
        assert (a["signal"], a["action"]) == ("accumulate", "plan_sec")

    def test_alt_dilimde_yalniz_izler(self, real_cfg):
        a = replay._vekil_analist(9, 12, -0.5)
        assert (a["signal"], a["action"]) == ("hold", "izle")
        assert a["confidence"] == "dusuk"

    def test_skor_yoksa_patlamaz(self, real_cfg):
        a = replay._vekil_analist(0, 3, None)
        assert "Skor yok" in a["thesis"]

    @pytest.mark.parametrize("sira,toplam", [(0, 1), (0, 3), (1, 3), (2, 3),
                                             (0, 10), (3, 10), (9, 10)])
    def test_URETILEN_ENUMLAR_daima_izinli(self, real_cfg, sira, toplam):
        """Vekil, journal'ın enum süzgecinden geçmek ZORUNDA.

        Geçmezse replay ortasında `ValueError` ile durur ve boru hattı kanıtı
        yarım kalır.
        """
        a = replay._vekil_analist(sira, toplam, 0.1)
        e = real_cfg["llm"]["enums"]
        assert a["signal"] in e["signal"]
        assert a["action"] in e["action"]
        assert a["confidence"] in e["confidence"]

    def test_yalniz_ANALIST_ALANLARINI_doldurur(self, real_cfg):
        """Vekil de şemanın dışına yazamaz — `journal.record` reddederdi."""
        a = replay._vekil_analist(0, 5, 1.0)
        assert set(a) <= journal.ANALIST_ALANLARI

    def test_prose_VEKIL_olarak_ISARETLENIR(self, real_cfg):
        """Vekil metni gerçek analiz gibi görünmemeli.

        Raporda ya da journal'da bir tez okuyan kişi, onu bir insanın/LLM'in
        yazdığını sanmamalı — etiket bu yüzden metnin İÇİNDE.
        """
        a = replay._vekil_analist(0, 5, 1.0)
        for alan in ("thesis", "counter_scenario", "key_risk", "falsifier"):
            assert "VEKİL" in a[alan], alan

    def test_prose_KENAR_IDDIA_ETMEZ(self, real_cfg):
        a = replay._vekil_analist(0, 5, 1.0)
        assert "yargı değil" in a["thesis"]
        assert "kenar iddiası değildir" in a["key_risk"]

    def test_deterministik(self, real_cfg):
        """Aynı girdi aynı çıktı — replay'in tekrar edilebilirliği buna dayanır."""
        assert replay._vekil_analist(2, 9, 0.5) == replay._vekil_analist(2, 9, 0.5)

    def test_vekil_etiketi_sabit(self):
        assert replay.VEKIL == "replay"


# ============================================================ koşu
@pytest.fixture
def replay_dunyasi(cfg, con):
    """600 barlık sentetik dünya — replay için yeterli ısınma + ileri bar."""
    kur_sentetik_evren(cfg, con, n_bar=600)
    return [r["date"] for r in db.fetch_all(
        con, "SELECT DISTINCT date FROM bars_daily ORDER BY date")]


class TestKosu:
    def test_tahmin_uretir_ve_cozer(self, cfg, con, replay_dunyasi):
        tarihler = replay_dunyasi
        r = replay.run(cfg, con, start=tarihler[300], end=tarihler[-1], top_n=3)
        assert r["donem"] > 0, r
        assert r["tahmin"] > 0, r
        assert r["cozum"]["cozulen"] > 0, r

    def test_tum_kayitlar_REPLAY_etiketli(self, cfg, con, replay_dunyasi):
        """Kaynak ayrımının taşıyıcısı bu etiket."""
        tarihler = replay_dunyasi
        replay.run(cfg, con, start=tarihler[300], end=tarihler[-1], top_n=2)
        araclar = {r["tool"] for r in db.fetch_all(con, "SELECT tool FROM llm_runs")}
        assert araclar == {replay.VEKIL}

    def test_PLAN_YOK_sayilir_sessizce_dusmez(self, cfg, con, replay_dunyasi):
        """"Plan üretilemedi" bir olgudur ve raporlanır.

        Sessizce düşürülürse "replay az tahmin üretti" ile "planlayıcı hiçbir
        şey bulamadı" ayırt edilemez — ve kalite kapısı sıkılaştırıldığında
        replay'in TAMAMEN elendiği fark edilmez (90 plan_yok, 0 tahmin).
        """
        tarihler = replay_dunyasi
        r = replay.run(cfg, con, start=tarihler[300], end=tarihler[-1], top_n=3)
        assert "plan_yok" in r and "atlanan_gun" in r
        assert r["tahmin"] + r["plan_yok"] > 0

    def test_isinmadan_ONCEKI_gunler_ATLANIR(self, cfg, con, replay_dunyasi):
        """`ISINMA_BAR` dolmadan skor hesaplanamaz — o günler atlanır, uydurulmaz."""
        tarihler = replay_dunyasi
        r = replay.run(cfg, con, start=tarihler[0], end=tarihler[100], top_n=2)
        assert r["donem"] == 0
        assert r["atlanan_gun"] > 0
        assert r["tahmin"] == 0

    def test_adim_ufka_gore_ortusmez(self, cfg, con, replay_dunyasi):
        """Varsayılan adım = zaman bariyeri → dönemler örtüşmez.

        Örtüşen dönemler N'i şişirir ve kazanma oranını abartır.
        """
        tarihler = replay_dunyasi
        r = replay.run(cfg, con, start=tarihler[300], end=tarihler[-1])
        assert r["adim_gun"] == int(cfg["planlayici"]["zaman_bariyeri_gun"])

    def test_journal_kayitlarinda_SKOR_dolu(self, cfg, con, replay_dunyasi):
        """Vekil de faktör skorunu KODDAN alır; IC ölçümü buna dayanır."""
        tarihler = replay_dunyasi
        replay.run(cfg, con, start=tarihler[300], end=tarihler[-1], top_n=2)
        satirlar = db.fetch_all(con, "SELECT score, rank, pct, weights_hash, "
                                     "close_at_asof FROM predictions")
        assert satirlar
        for s in satirlar:
            assert s["score"] is not None
            assert s["rank"] is not None and s["rank"] >= 1
            assert s["pct"] is not None and 0 <= s["pct"] <= 100
            assert s["weights_hash"]
            assert s["close_at_asof"] is not None

    def test_referans_kapanis_O_GUNUN_bari(self, cfg, con, replay_dunyasi):
        """`close_at_asof` gelecekten gelemez — slippage ve alfa buna dayanır."""
        tarihler = replay_dunyasi
        replay.run(cfg, con, start=tarihler[300], end=tarihler[-1], top_n=2)
        for p in db.fetch_all(con, "SELECT asof, ticker, close_at_asof FROM predictions"):
            gercek = db.scalar(con, "SELECT c FROM bars_daily WHERE ticker=? AND date=?",
                               (p["ticker"], p["asof"]))
            assert p["close_at_asof"] == pytest.approx(gercek)

    def test_ikinci_kosu_YENI_RUN_acar(self, cfg, con, replay_dunyasi):
        """Journal değişmez; aynı gün ikinci kez koşmak yeni bir run demektir."""
        tarihler = replay_dunyasi
        replay.run(cfg, con, start=tarihler[300], end=tarihler[400], top_n=2)
        n1 = db.scalar(con, "SELECT COUNT(*) FROM predictions")
        replay.run(cfg, con, start=tarihler[300], end=tarihler[400], top_n=2)
        assert db.scalar(con, "SELECT COUNT(*) FROM predictions") == 2 * n1
        assert db.scalar(con, "SELECT COUNT(DISTINCT run_id) FROM llm_runs") >= 2


# ============================================================ temizleme
class TestReset:
    def _iki_kaynak(self, cfg, con, asof):
        for arac in (replay.VEKIL, "claude-code"):
            rid = journal.create_run(cfg, con, asof=asof, tool=arac, bundle_sha="x")
            add_plan(con, f"P-{arac}", ticker="AAA", asof=asof)
            journal.record(cfg, con, run_id=rid, asof=asof, ticker="AAA",
                           analist={"signal": "hold", "action": "izle",
                                    "confidence": "orta"},
                           plan={"plan_id": f"P-{arac}"},
                           referans={"close": 100.0})

    def test_yalniz_REPLAY_kayitlari_silinir(self, cfg, con):
        """Gerçek analiz kayıtları DOKUNULMAZ — journal değişmezliğinin sınırı."""
        self._iki_kaynak(cfg, con, "2024-06-03")
        r = replay.reset(cfg, con)
        assert r["run"] == 1 and r["tahmin"] == 1
        kalan = db.fetch_all(con, "SELECT r.tool FROM predictions p "
                                  " JOIN llm_runs r ON r.run_id = p.run_id")
        assert [x["tool"] for x in kalan] == ["claude-code"]

    def test_bagli_SONUCLAR_da_silinir(self, cfg, con):
        """Yetim `outcomes` satırı FK'sı olmayan bir ölçüme dönüşür."""
        self._iki_kaynak(cfg, con, "2024-06-03")
        pid = db.scalar(con, "SELECT p.prediction_id FROM predictions p "
                             " JOIN llm_runs r ON r.run_id = p.run_id "
                             " WHERE r.tool = ?", (replay.VEKIL,))
        db.upsert_many(con, "outcomes", resolver.OUTCOME_COLS,
                       [tuple({**{k: None for k in resolver.OUTCOME_COLS},
                               "prediction_id": pid, "resolved_date": "2024-07-01",
                               "resolution": resolver.SURE,
                               "resolver_version": resolver.RESOLVER_VERSION,
                               "resolved_utc": "2024-07-01T00:00:00+00:00"}[k]
                              for k in resolver.OUTCOME_COLS)])
        r = replay.reset(cfg, con)
        assert r["sonuc"] == 1
        assert db.scalar(con, "SELECT COUNT(*) FROM outcomes") == 0

    def test_replay_kaydi_yoksa_sifir(self, cfg, con):
        assert replay.reset(cfg, con) == {"run": 0, "tahmin": 0, "sonuc": 0}


# ============================================================ kaynak ayrımı
class TestKaynakAyrimi:
    def test_replay_ile_gercek_analiz_KARISTIRILMAZ(self, cfg, con):
        """`bist degerlendir` iki kaynak görünce DURMALI.

        Vekilin alfası gerçek analizinkiyle aynı potaya girerse rapor "kimin
        alfası" sorusunu cevaplayamaz — ve bunu hiçbir yerde yazmaz.
        """
        asof = "2024-06-03"
        for arac in (replay.VEKIL, "claude-code"):
            rid = journal.create_run(cfg, con, asof=asof, tool=arac, bundle_sha="x")
            add_plan(con, f"Q-{arac}", ticker="AAA", asof=asof)
            pid = journal.record(cfg, con, run_id=rid, asof=asof, ticker="AAA",
                                 analist={"signal": "hold", "action": "izle",
                                          "confidence": "orta"},
                                 plan={"plan_id": f"Q-{arac}"},
                                 referans={"close": 100.0})
            db.upsert_many(con, "outcomes", resolver.OUTCOME_COLS,
                           [tuple({**{k: None for k in resolver.OUTCOME_COLS},
                                   "prediction_id": pid,
                                   "resolved_date": "2024-07-01",
                                   "resolution": resolver.SURE,
                                   "resolver_version": resolver.RESOLVER_VERSION,
                                   "resolved_utc": "2024-07-01T00:00:00+00:00"}[k]
                                  for k in resolver.OUTCOME_COLS)])

        assert evaluate.araclar(con) == {replay.VEKIL: 1, "claude-code": 1}
        with pytest.raises(evaluate.KaynakKarisik):
            evaluate.kaynak_sec(con, None)
        assert evaluate.kaynak_sec(con, replay.VEKIL) == replay.VEKIL
