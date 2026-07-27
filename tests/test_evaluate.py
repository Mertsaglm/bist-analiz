"""Değerlendirme testleri.

`TestDurustluk` bu dosyanın kalbi: sistem erken kenar iddia EDEMEZ. Bu testler
geçmezse rapor yalan söyleyebilir hale gelir ve yalanı fark eden olmaz.
"""

from __future__ import annotations

import pytest

from src import evaluate, journal, resolver, stats, util
from tests.conftest import add_plan, add_universe

ANALIST = {"signal": "buy", "action": "plan_sec", "confidence": "orta",
           "thesis": "t", "counter_scenario": "c", "key_risk": "k",
           "falsifier": "f"}


def _kayit(cfg, con, *, asof, ticker, alfa, hit=1, guven="orta",
           signal="buy", action="plan_sec", score=1.0, run_id=None):
    """Tek bir çözülmüş tahmin üretir (plan/bar zinciri olmadan, doğrudan)."""
    add_universe(con, ticker)
    add_plan(con, f"{ticker}-{asof}", ticker=ticker, asof=asof)
    if run_id is None:
        run_id = journal.create_run(cfg, con, asof=asof, tool="test",
                                    bundle_sha="s")
    pid = journal.record(
        cfg, con, run_id=run_id, asof=asof, ticker=ticker,
        analist={**ANALIST, "signal": signal, "action": action, "confidence": guven},
        plan={"plan_id": f"{ticker}-{asof}", "entry_low": 99.0, "entry_high": 100.0,
              "stop_price": 95.0, "targets": [{"price": 110.0}],
              "time_barrier_date": asof, "position_size_pct": 5.0},
        faktor={"score": score, "rank": 1, "pct": 90.0, "weights_hash": "h"},
        referans={"close": 100.0})
    con.execute(
        f"INSERT INTO outcomes ({','.join(resolver.OUTCOME_COLS)}) "
        f"VALUES ({','.join('?' * len(resolver.OUTCOME_COLS))})",
        (pid, asof, "hedef", asof, 100.0, asof, 110.0, 5,
         alfa, alfa, alfa, 0.0, 0.0, alfa, alfa, None, None, 0.0, hit,
         "hedef", resolver.RESOLVER_VERSION, util.utc_now_iso()))
    con.commit()
    return run_id


class TestDurustluk:
    """Sistemin kendi hakkında abartılı konuşamaması."""

    def test_sahte_alfa_erken_kenar_iddia_etmez(self, cfg, con):
        """5 döneme DEVASA sahte alfa besle — hüküm HÂLÂ 'ölçüm yetersiz'.

        Bu tek test projenin epistemolojisinin tamamını kodluyor. Sistem erken
        kenar iddia EDERSE kod yalan söylüyordur.
        """
        for i in range(5):
            _kayit(cfg, con, asof=f"2024-0{i + 1}-15", ticker=f"T{i}", alfa=50.0)
        a = evaluate.paired_alpha(cfg, con)
        assert a["n"] == 5
        assert a["ort"] == pytest.approx(50.0)
        assert a["hukum"].startswith(stats.HUKUM_YETERSIZ), (
            f"5 dönemle kenar iddia edildi: {a['hukum']}")

    def test_gerekli_n_daima_raporlanir(self, cfg, con):
        """'Ne zaman bilebiliriz?' bir his değil, basılmış bir sayı."""
        for i, alfa in enumerate([1.0, -2.0, 3.0, 0.5, -1.5]):
            _kayit(cfg, con, asof=f"2024-0{i + 1}-15", ticker=f"T{i}", alfa=alfa)
        assert evaluate.paired_alpha(cfg, con)["gerekli_n"] is not None

    def test_getirisiz_sonuclar_alfaya_girmez(self, cfg, con):
        """`giris_olmadi` ve `iptal_*` tahmin değildir — gerçekleşmemiş plandır."""
        _kayit(cfg, con, asof="2024-01-15", ticker="AAA", alfa=5.0)
        add_universe(con, "BBB")
        add_plan(con, "BBB-2024-02-15", ticker="BBB", asof="2024-02-15")
        rid = journal.create_run(cfg, con, asof="2024-02-15", tool="test",
                                 bundle_sha="s")
        pid = journal.record(
            cfg, con, run_id=rid, asof="2024-02-15", ticker="BBB", analist=ANALIST,
            plan={"plan_id": "BBB-2024-02-15", "time_barrier_date": "2024-03-15"},
            faktor={"score": 1.0, "rank": 1, "pct": 90.0, "weights_hash": "h"},
            referans={"close": 100.0})
        con.execute(
            f"INSERT INTO outcomes ({','.join(resolver.OUTCOME_COLS)}) "
            f"VALUES ({','.join('?' * len(resolver.OUTCOME_COLS))})",
            (pid, "2024-03-15", "giris_olmadi", None, None, None, None, None,
             None, None, None, None, None, None, None, None, None, None, None,
             "tetiklenmedi", resolver.RESOLVER_VERSION, util.utc_now_iso()))
        con.commit()
        assert evaluate.paired_alpha(cfg, con)["n"] == 1


class TestICHukmu:
    """IC için BÜYÜKLÜK değil ANLAMLILIK. edge_verdict'i IC'ye uygulamak
    her pozitif IC'yi 'zayıf kanıt' ilan ediyordu — işaret körlüğünün
    başka kılıkta hâli."""

    def test_anlamsiz_t_kenar_yok(self):
        assert stats.ic_verdict(0.057, n=20, t=1.46, weak_n=15) == stats.HUKUM_KENAR_YOK

    def test_anlamli_t_zayif_kanit(self):
        h = stats.ic_verdict(0.057, n=20, t=2.4, weak_n=15)
        assert h.startswith(stats.HUKUM_ZAYIF_KANIT)

    def test_zayif_n_ezer(self):
        h = stats.ic_verdict(0.9, n=3, t=99.0, weak_n=15)
        assert h.startswith(stats.HUKUM_YETERSIZ)

    def test_mukemmel_siralamada_ic_1(self):
        assert stats.ic_summary([1.0] * 30)["ic_ort"] == pytest.approx(1.0)

    def test_rastgele_siralamada_ic_sifira_yakin(self):
        import numpy as np
        rng = np.random.default_rng(0)
        ics = [float(stats.spearman(rng.random(20), rng.random(20)) or 0)
               for _ in range(60)]
        s = stats.ic_summary(ics)
        assert abs(s["ic_ort"]) < 0.15
        assert s["hukum"] == stats.HUKUM_KENAR_YOK


class TestBrier:
    def test_mukemmel_tahminde_sifira_yakin(self, cfg, con):
        """confidence_p haritası 1.0 değil (0.65) — mükemmel isabette bile
        Brier sıfır olmaz. Bu, kalibrasyonun HENÜZ yapılmadığını gösterir."""
        for i in range(5):
            _kayit(cfg, con, asof=f"2024-0{i + 1}-15", ticker=f"T{i}",
                   alfa=5.0, hit=1, guven="yuksek")
        b = evaluate.brier(cfg, con)
        beklenen = (1 - cfg["llm"]["guven_olasilik"]["yuksek"]) ** 2
        assert b["brier"] == pytest.approx(beklenen, abs=1e-6)

    def test_kova_dagilimi(self, cfg, con):
        _kayit(cfg, con, asof="2024-01-15", ticker="AAA", alfa=5.0, guven="yuksek")
        _kayit(cfg, con, asof="2024-02-15", ticker="BBB", alfa=-5.0, hit=0,
               guven="dusuk")
        kovalar = {k["seviye"]: k for k in evaluate.brier(cfg, con)["kovalar"]}
        assert kovalar["yuksek"]["gerceklesen"] == 1.0
        assert kovalar["dusuk"]["gerceklesen"] == 0.0

    def test_az_veride_olcum_yetersiz(self, cfg, con):
        _kayit(cfg, con, asof="2024-01-15", ticker="AAA", alfa=5.0)
        assert evaluate.brier(cfg, con)["hukum"].startswith(stats.HUKUM_YETERSIZ)


class TestLLMKatkisi:
    def test_uc_isimden_az_kesit_atlanir(self, cfg, con):
        """3 isimden az kesitte sıra korelasyonu anlamsızdır."""
        rid = _kayit(cfg, con, asof="2024-01-15", ticker="AAA", alfa=5.0)
        _kayit(cfg, con, asof="2024-01-15", ticker="BBB", alfa=1.0, run_id=rid)
        assert evaluate.llm_contribution(cfg, con)["n"] == 0

    def test_llm_siralamasi_skordan_iyiyse_pozitif(self, cfg, con):
        """LLM sinyali gerçek alfayı, skordan daha iyi sıralıyorsa fark > 0."""
        rid = None
        for tk, alfa, sig, sk in (("AAA", 9.0, "strong_buy", 0.1),
                                  ("BBB", 5.0, "buy", 0.2),
                                  ("CCC", 1.0, "hold", 0.3)):
            rid = _kayit(cfg, con, asof="2024-01-15", ticker=tk, alfa=alfa,
                         signal=sig, score=sk, run_id=rid)
        r = evaluate.llm_contribution(cfg, con)
        assert r["n"] == 1 and r["ort"] > 0


class TestTaksonomi:
    def test_sonuc_ve_hata_sayimi(self, cfg, con):
        _kayit(cfg, con, asof="2024-01-15", ticker="AAA", alfa=5.0)
        t = evaluate.error_taxonomy(con)
        assert t["sonuc"]["hedef"] == 1
        assert t["hata_etiketi"]["hedef"] == 1
        assert t["toplam"] == 1

    def test_bos_veride_patlamaz(self, cfg, con):
        t = evaluate.error_taxonomy(con)
        assert t["toplam"] == 0 and t["tetiklenmeme_orani"] is None


class TestRapor:
    def test_bos_veride_rapor_uretilir(self, cfg, con):
        from src import report
        e = evaluate.run(cfg, con)
        metin = report.evaluate_report(cfg, e)
        assert "ölçüm yok" in metin or "ölçüm yetersiz" in metin
        assert "yatırım tavsiyesi değildir" in metin

    def test_raporda_dogrulandi_gecmez(self, cfg, con):
        """Bu sistemde 'doğrulandı' hükmü YOKTUR — raporda da geçemez."""
        from src import report
        for i in range(20):
            _kayit(cfg, con, asof=f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}",
                   ticker=f"T{i}", alfa=50.0)
        metin = report.evaluate_report(cfg, evaluate.run(cfg, con))
        # Açıklama satırı ("bu sistemde 'doğrulandı' YOKTUR") serbest; yasak
        # olan, bir HÜKÜM hücresinde geçmesi.
        hukumler = [h.strip() for satir in metin.splitlines() if satir.startswith("|")
                    for h in satir.split("|") if "**" in h]
        assert not any("doğrulandı" in h.lower() or "kanıtlandı" in h.lower()
                       for h in hukumler), f"hüküm olarak geçmiş: {hukumler}"


class TestBoyutlandirmaKarsiOlgusu:
    """⚠ REGRESYON KİLİDİ (2026-07-27 denetimi).

    `resolver` bu kolona `ret_pct`'i AYNEN yazıyordu (iki dalda da aynı değer),
    dolayısıyla fark TANIM GEREĞİ sıfırdı ve rejim katmanı ölçülemiyordu.
    Üstelik `resolver.py`, `db.SCHEMA` ve `regime.py`'de üç ayrı yorum
    ölçülüyormuş izlenimi veriyordu.
    """

    def test_kolon_ret_pct_ile_AYNI_DEGIL(self, cfg, con):
        import pandas as pd
        pred = {"prediction_id": "p1", "ticker": "AAA", "entry_high": 100.0,
                "position_size_pct": 4.0}
        out = resolver._outcome(pred, resolver.HEDEF, resolved_date="2024-02-01",
                                entry_date="2024-01-02", entry_price=100.0,
                                exit_date="2024-02-01", exit_price=110.0, cfg=cfg)
        assert out["ret_pct_equal_size"] is not None
        assert out["ret_pct_equal_size"] != out["ret_pct"], \
            "karşı-olgu hâlâ ret_pct'in kopyası"
        # eşit boyut = maks_pozisyon_pct (%10) → 9.70 × 10/100 = 0.97
        assert abs(out["ret_pct_equal_size"]
                   - out["ret_pct"] * cfg["risk"]["maks_pozisyon_pct"] / 100) < 1e-6

    def test_boyut_bilinmiyorsa_UYDURULMAZ(self, cfg):
        out = resolver._outcome({"prediction_id": "p", "ticker": "A",
                                 "entry_high": 100.0, "position_size_pct": None},
                                resolver.HEDEF, resolved_date="2024-02-01",
                                entry_date="2024-01-02", entry_price=100.0,
                                exit_date="2024-02-01", exit_price=110.0, cfg=cfg)
        assert out["ret_pct_equal_size"] is None, \
            "bilinmeyen boyut için 'fark sıfır' uyduruluyor"

    def test_fark_gercekten_olculuyor(self, cfg, con):
        _kayit(cfg, con, asof="2024-01-02", ticker="AAA", alfa=2.0)
        # `_kayit` outcomes'a ret_pct_equal_size = alfa yazıyor; boyut %5.
        s = evaluate.sizing_counterfactual(cfg, con)
        assert s["n"] == 1
        assert s["ort"] is not None


class TestLLMKatkisiHukmu:
    """⚠ L-006'nın atlanmış çağrı yeri: IC farkına yüzde-puan eşiği."""

    def test_hukum_t_tabanli(self, cfg, con):
        for i, t in enumerate(("AAA", "BBB", "CCC")):
            _kayit(cfg, con, asof="2024-01-02", ticker=t, alfa=1.0 + i,
                   score=float(i))
        s = evaluate.llm_contribution(cfg, con)
        # N küçük → 'ölçüm yok' ya da 'ölçüm yetersiz'; ASLA 'zayıf kanıt' değil
        assert not s["hukum"].startswith(stats.HUKUM_ZAYIF_KANIT)

    def test_isaret_koru_yorum_alani_KALDIRILDI(self, cfg, con):
        s = evaluate.llm_contribution(cfg, con)
        assert "yorum" not in s, "işarete bakıp anlamlılığa bakmayan alan geri gelmiş"


class TestKaynakAyrimi:
    """⚠ `replay` VEKİL bir analisttir (kasten aptal, deterministik kural).
    Onun alfasını gerçek LLM kayıtlarıyla aynı potaya koymak, ölçümün ne
    ölçtüğünü belirsizleştirir — ve rapor bunu hiçbir yerde yazmazdı."""

    def test_tek_kaynakta_surtunme_yok(self, cfg, con):
        _kayit(cfg, con, asof="2024-01-02", ticker="AAA", alfa=1.0)
        e = evaluate.run(cfg, con)          # --tool YOK
        assert e["tool"] == "test", "tek kaynak varsa seçilip ADI basılmalı"

    def test_karisik_kaynak_REDDEDILIR(self, cfg, con):
        from src import journal
        _kayit(cfg, con, asof="2024-01-02", ticker="AAA", alfa=1.0)
        r2 = journal.create_run(cfg, con, asof="2024-02-02", tool="replay",
                                bundle_sha="s")
        _kayit(cfg, con, asof="2024-02-02", ticker="BBB", alfa=2.0, run_id=r2)
        with pytest.raises(evaluate.KaynakKarisik) as e:
            evaluate.run(cfg, con)
        assert "--tool" in str(e.value), "hata mesajı çıkış yolunu göstermiyor"

    def test_tool_verilince_calisir(self, cfg, con):
        from src import journal
        _kayit(cfg, con, asof="2024-01-02", ticker="AAA", alfa=1.0)
        r2 = journal.create_run(cfg, con, asof="2024-02-02", tool="replay",
                                bundle_sha="s")
        _kayit(cfg, con, asof="2024-02-02", ticker="BBB", alfa=2.0, run_id=r2)
        assert evaluate.run(cfg, con, tool="replay")["tool"] == "replay"

    def test_bos_journal_patlamaz(self, cfg, con):
        e = evaluate.run(cfg, con)
        assert e["tool"] == "(kayıt yok)" and e["alfa"]["n"] == 0
