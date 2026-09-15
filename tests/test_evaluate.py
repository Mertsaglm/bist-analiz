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
    """⚠ HEDEF DEĞİŞKEN 2026-08-16'da DEĞİŞTİ: `outcomes.alpha_vs_ew` yerine
    PLANSIZ alfa. Sebep, eski kesitin yapısal olarak hiç dolmamasıydı
    (bkz. `TestOlcumKendiKonusunuElemez`). Buradaki testler bu yüzden alfayı
    enjekte eder — konuları sıralama mantığı, alfa hesabı değil (onun kendi
    testi var: `test_plansiz_alfa_UFUK_dolmadiysa_SIFIR_DEGIL_YOK`)."""

    @staticmethod
    def _alfa_enjekte(monkeypatch, harita: dict):
        monkeypatch.setattr(
            evaluate, "_plansiz_alfa",
            lambda cfg_, con_, satirlar: {
                r["prediction_id"]: harita[r["ticker"]]
                for r in satirlar if r["ticker"] in harita})

    def test_uc_isimden_az_kesit_atlanir(self, cfg, con, monkeypatch):
        """3 isimden az kesitte sıra korelasyonu anlamsızdır."""
        rid = _kayit(cfg, con, asof="2024-01-15", ticker="AAA", alfa=5.0)
        _kayit(cfg, con, asof="2024-01-15", ticker="BBB", alfa=1.0, run_id=rid)
        self._alfa_enjekte(monkeypatch, {"AAA": 5.0, "BBB": 1.0})
        assert evaluate.llm_contribution(cfg, con)["n"] == 0

    def test_llm_siralamasi_skordan_iyiyse_pozitif(self, cfg, con, monkeypatch):
        """LLM sinyali gerçek alfayı, skordan daha iyi sıralıyorsa fark > 0."""
        rid = None
        for tk, alfa, sig, sk in (("AAA", 9.0, "strong_buy", 0.1),
                                  ("BBB", 5.0, "buy", 0.2),
                                  ("CCC", 1.0, "hold", 0.3)):
            rid = _kayit(cfg, con, asof="2024-01-15", ticker=tk, alfa=alfa,
                         signal=sig, score=sk, run_id=rid)
        self._alfa_enjekte(monkeypatch, {"AAA": 9.0, "BBB": 5.0, "CCC": 1.0})
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


# ============================================================ ölçüm kendi konusunu elemez
class TestOlcumKendiKonusunuElemez:
    """⚠ 2026-08-15 denetiminin en sinsi bulgu sınıfı: bir ölçüm, ölçmesi
    gereken şeyi kaynak sorgusunda eliyordu.

    * `veto_value` → `outcomes` ile INNER JOIN. Veto edilen tahminin
      `plan_id`'si NULL, plan açılmaz, outcome yazılmaz, satır JOIN'de düşer.
      `predictions`'ta 17 `plan_reddet` varken karne `veto_sayisi: 0` diyordu —
      üstelik günlük rapor "veto analistin en ölçülebilir katkısı" başlığını
      her gün basıyordu.
    * `llm_contribution` → kesit yalnız SEÇİLEN isimlerden kuruluyor ve
      dönem başına ≥3 isim isteniyordu; sistem dönem başına en fazla 2 plan
      seçer. Eşik YAPISAL OLARAK hiç geçilemezdi.

    İkisi de "henüz veri yok" gibi görünüyordu; gerçekte hiç dolmayacaklardı.
    """

    def _gun(self, cfg, con, asof, isimler, *, run_id=None):
        """Bir günün TAM kesiti: bazıları seçilmiş, bazıları vetolanmış."""
        from tests.conftest import add_bars, bar_serisi
        for t, (signal, action, score) in isimler.items():
            add_universe(con, t)
            add_bars(con, t, bar_serisi(80, gunluk_egim=0.001, dalga=1.0))
        return isimler

    def test_VETO_edilenler_karneye_GIRER(self, cfg, con):
        """Veto sayısı `predictions`'tan gelir, `outcomes`'tan değil."""
        run = journal.create_run(cfg, con, asof="2026-03-02", tool="test",
                                 bundle_sha="s")
        _kayit(cfg, con, asof="2026-03-02", ticker="AAA", alfa=2.0,
               action="plan_sec", run_id=run)
        add_universe(con, "BBB")
        journal.record(
            cfg, con, run_id=run, asof="2026-03-02", ticker="BBB",
            analist={**ANALIST, "action": "plan_reddet", "signal": "avoid",
                     "veto_code": "rejim_uyumsuz"},
            plan=None, faktor={"score": 0.1, "rank": 9, "pct": 10.0,
                               "weights_hash": "h"},
            referans={"close": 100.0})

        v = evaluate.veto_value(cfg, con, tool="test")
        assert v["veto_sayisi"] == 1, (
            "veto edilen tahmin karneye girmiyor — kaynak sorgusu `outcomes` "
            "ile INNER JOIN yapıyor olabilir")
        assert v["veto_kodlari"] == {"rejim_uyumsuz": 1}

    def test_veto_farkinin_ISARETI_yorumlu(self, cfg, con):
        """`not` alanı işaretin ne demek olduğunu YAZMALI: pozitif fark
        veto'nun ZARAR verdiği anlamına gelir ve bu sezgiye terstir."""
        v = evaluate.veto_value(cfg, con, tool="test")
        assert "POZİTİFSE veto ZARAR" in v["not"]
        assert "plansız" in v["not"].lower()

    def test_LLM_katkisi_kesiti_TUM_tahminlerden(self, cfg, con, monkeypatch):
        """Kesit seçilen 2 isimden değil, o günün tamamından kurulur.

        Burada 5 isimlik bir gün kuruluyor ve YALNIZ BİRİ `plan_sec`. Eski
        mantıkta kesit 1 isimdi → `< 3` → dönem atlanırdı. Yenisinde 5 isim.
        """
        run = journal.create_run(cfg, con, asof="2026-03-02", tool="test",
                                 bundle_sha="s")
        for i, t in enumerate(("AAA", "BBB", "CCC", "DDD", "EEE")):
            add_universe(con, t)
            journal.record(
                cfg, con, run_id=run, asof="2026-03-02", ticker=t,
                analist={**ANALIST, "action": "plan_sec" if i == 0 else "izle",
                         "signal": ["buy", "hold", "hold", "avoid", "hold"][i]},
                plan=None,
                faktor={"score": 5.0 - i, "rank": i + 1, "pct": 90.0 - i * 10,
                        "weights_hash": "h"},
                referans={"close": 100.0})

        rows = evaluate._tum_tahminler(con, tool="test")
        assert len(rows) == 5, "kesit tüm tahminlerden kurulmuyor"
        # Plansız alfa sahtelenir: bar zinciri bu testin konusu değil.
        monkeypatch.setattr(
            evaluate, "_plansiz_alfa",
            lambda cfg_, con_, satirlar: {r["prediction_id"]: float(i)
                                          for i, r in enumerate(satirlar)})
        l = evaluate.llm_contribution(cfg, con, tool="test")
        assert l["n"] == 1, (
            "dönem hâlâ atlanıyor — kesit `outcomes`'a bağlı olabilir")

    def test_plansiz_alfa_UFUK_dolmadiysa_SIFIR_DEGIL_YOK(self, cfg, con):
        """⚠ Ufku dolmamış tahmin için 0.0 döndürmek, bilinmeyeni sayıya
        çevirmek olurdu (#009). Anahtar hiç bulunmamalı."""
        from tests.conftest import add_bars, bar_serisi
        add_universe(con, "AAA")
        add_bars(con, "AAA", bar_serisi(30, gunluk_egim=0.001, dalga=1.0))
        son = con.execute("SELECT MAX(date) FROM bars_daily").fetchone()[0]
        run = journal.create_run(cfg, con, asof=son, tool="test", bundle_sha="s")
        pid = journal.record(
            cfg, con, run_id=run, asof=son, ticker="AAA", analist=ANALIST,
            plan=None, faktor={"score": 1.0, "rank": 1, "pct": 90.0,
                               "weights_hash": "h"},
            referans={"close": 100.0})
        m = evaluate._plansiz_alfa(cfg, con, evaluate._tum_tahminler(con, tool="test"))
        assert pid not in m, "ufku dolmamış tahmine değer atanmış"


# ============================================================ örtüşme
class TestOrtusmeAyiklama:
    """⚠ Journal her işlem günü yeni tahmin yazar; aynı isim art arda
    seçilirse AYNI İŞLEM birden çok satır olur ve `dist_stats` onları bağımsız
    gözlem sayar.

    ÖLÇÜLDÜ (2026-08-15): `2026-07-30-TUPRS-1` ve `2026-08-03-TUPRS-1` aynı gün
    girdi (08-04), aynı gün çıktı (08-06) — tek işlem, iki "hedef" kaydı. Canlı
    karne **+2.25pp (n=4)** diyordu; örtüşme ayıklanınca **−0.90pp (n=3)**.

    Bedeli yalnız ortalama değil: örtüşen gözlemle `sd` küçülür ve `t` ŞİŞER,
    yani sistem kendine olması gerekenden fazla güvenir. PROJECT.md'nin
    "örtüşmeyen pencere" disiplini `backtest.py` için yazılmış, canlı journal'a
    hiç uygulanmamıştı.
    """

    def _ayni_islem(self, cfg, con):
        """İki farklı tahmin, AYNI giriş ve AYNI çıkış — tek gerçek işlem."""
        rid = None
        for asof, alfa in (("2024-01-15", 12.0), ("2024-01-16", 8.0)):
            rid = _kayit(cfg, con, asof=asof, ticker="AAA", alfa=alfa, run_id=rid)
        con.execute("UPDATE outcomes SET entry_date='2024-01-20', "
                    "exit_date='2024-01-25'")
        con.commit()

    def test_ayni_islem_TEK_gozlem_sayilir(self, cfg, con):
        self._ayni_islem(cfg, con)
        a = evaluate.paired_alpha(cfg, con)
        assert a["n"] == 2, "ham sayı da raporlanmalı (üç soru, üç sayı)"
        assert a["n_bagimsiz"] == 1, (
            "aynı (ticker, giriş, çıkış) üçlüsü hâlâ iki bağımsız gözlem "
            "sayılıyor — örtüşme ayıklanmıyor")
        assert a["ortusen_kayit"] == 1
        assert a["ort_bagimsiz"] == pytest.approx(10.0)   # (12+8)/2

    def test_FARKLI_islemler_ayiklanmaz(self, cfg, con):
        """Simetri: gerçekten ayrı iki işlem birleştirilmemeli."""
        rid = _kayit(cfg, con, asof="2024-01-15", ticker="AAA", alfa=12.0)
        _kayit(cfg, con, asof="2024-02-15", ticker="BBB", alfa=8.0, run_id=rid)
        con.execute("UPDATE outcomes SET entry_date='2024-01-20', "
                    "exit_date='2024-01-25' WHERE prediction_id LIKE '%AAA%'")
        con.execute("UPDATE outcomes SET entry_date='2024-02-20', "
                    "exit_date='2024-02-25' WHERE prediction_id LIKE '%BBB%'")
        con.commit()
        a = evaluate.paired_alpha(cfg, con)
        assert a["n_bagimsiz"] == 2 and a["ortusen_kayit"] == 0

    def test_hukum_BAGIMSIZ_sayidan_da_uretilir(self, cfg, con):
        """Rapor hükmü örtüşme ayıklanmış satıra göre okur; o satırın kendi
        hükmü olmalı, ham hükmün kopyası değil."""
        self._ayni_islem(cfg, con)
        a = evaluate.paired_alpha(cfg, con)
        assert "hukum_bagimsiz" in a
        assert "N=1" in a["hukum_bagimsiz"]


class TestICDonemSeti:
    def test_IC_donemleri_OUTCOMES_a_bagli_DEGIL(self, cfg, con, monkeypatch):
        """⚠ Eski sürüm dönemleri `_cozulmus`tan alıyordu: IC yalnız "o gün bir
        plan açıldı VE çözüldü" günlerinden hesaplanıyordu. Canlıda 10 karar
        günü vardı, IC 4'ünü görüyordu. Bu gizli bir KOŞULLAMADIR — sıralama
        kalitesi ölçümü plan SONUÇLARINA koşullanmış bir alt kümeden geliyordu.
        """
        gorulen: list[str] = []
        monkeypatch.setattr(evaluate.stats, "ic_summary",
                            lambda ics, *a, **k: {"n_donem": len(ics)})
        # Çözülmüş tahmin YOK; yalnız kayıtlı bir karar var.
        add_universe(con, "AAA")
        run = journal.create_run(cfg, con, asof="2024-01-15", tool="test",
                                 bundle_sha="s")
        journal.record(cfg, con, run_id=run, asof="2024-01-15", ticker="AAA",
                       analist=ANALIST, plan=None,
                       faktor={"score": 1.0, "rank": 1, "pct": 90.0,
                               "weights_hash": "h"},
                       referans={"close": 100.0})
        assert evaluate._cozulmus(con, tool="test") == [], "ön koşul bozuldu"
        assert len(evaluate._tum_tahminler(con, tool="test")) == 1, (
            "IC dönem seti hâlâ `outcomes`'a bağlı — çözülmemiş bir karar günü "
            "sıralama ölçümünden düşüyor")


# ============================================================ yarım bar / kaçanlar
class TestYarimBarKosusu:
    """⚠ YAŞANDI (2026-07-29): o günün 18 tahmininin 18'inde de
    `close_at_asof`, barın gerçek kapanışından yüksekti (ort %1.21, hepsi aynı
    yönde). `created_utc` 10:38 UTC = 13:38 TR — seans AÇIKTI.

    Yarım bar KAPISI 2026-08-11'de eklendi ama kayıt journal'da duruyor ve
    `claude-code` aracının TEK canlı karne satırı o koşudan geliyor. Journal
    değişmezdir: silinmez, AYRILIR.
    """

    def _kosu(self, cfg, con, *, asof, kapanis, kayitli, n=4):
        from tests.conftest import add_bars, bar_serisi
        run = journal.create_run(cfg, con, asof=asof, tool="test", bundle_sha="s")
        for i in range(n):
            t = f"T{i}"
            add_universe(con, t)
            con.execute(
                "INSERT OR REPLACE INTO bars_daily "
                "(ticker,date,o,h,l,c,v,c_tr,turnover_try,source,ingested_utc) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (t, asof, kapanis, kapanis, kapanis, kapanis, 1e6, kapanis,
                 1e9, "test", "now"))
            journal.record(cfg, con, run_id=run, asof=asof, ticker=t,
                           analist=ANALIST, plan=None,
                           faktor={"score": 1.0, "rank": 1, "pct": 90.0,
                                   "weights_hash": "h"},
                           referans={"close": kayitli})
        con.commit()
        return run

    def test_YARIM_BAR_kosusu_yakalanir(self, cfg, con):
        """Kayıtlı fiyat gerçek kapanıştan %1.2 yüksek → kesitin tamamı sapar."""
        self._kosu(cfg, con, asof="2024-01-15", kapanis=98.8, kayitli=100.0)
        r = evaluate.yarim_bar_kosulari(con)
        assert len(r) == 1 and r[0]["sapan"] == r[0]["n"] == 4
        assert r[0]["ort_sapma"] == pytest.approx(-1.2, abs=0.01)

    def test_TEMIZ_kosu_yakalanmaz(self, cfg, con):
        """Simetri: kapanışla kayıt uyuşuyorsa bayrak KALKMAZ."""
        self._kosu(cfg, con, asof="2024-01-15", kapanis=100.0, kayitli=100.0)
        assert evaluate.yarim_bar_kosulari(con) == []

    def test_float_gurultusu_YANLIS_ALARM_vermez(self, cfg, con):
        """⚠ Gözlendi: 42.6 kaydı ile 42.5999984741 barı (float32→64). Tolerans
        bu gürültünün ÜSTÜNDE olmalı, yoksa her koşu 'yarım bar' sanılır."""
        self._kosu(cfg, con, asof="2024-01-15", kapanis=42.5999984741,
                   kayitli=42.6)
        assert evaluate.yarim_bar_kosulari(con) == []

    def test_TEK_ismin_duzeltmesi_TUM_kosuyu_suclamaz(self, cfg, con):
        """Yarım bar KESİTSELDİR. Bir ismin geriye dönük düzeltmesi koşuyu
        şaibeli yapmaz — eşik oransaldır."""
        run = self._kosu(cfg, con, asof="2024-01-15", kapanis=100.0,
                         kayitli=100.0, n=4)
        con.execute("UPDATE predictions SET close_at_asof = 90.0 "
                    " WHERE ticker = 'T0'")
        con.commit()
        assert evaluate.yarim_bar_kosulari(con) == []


class TestTetiklenmemeBedeli:
    """`giris_olmadi` getirisi hesaplanmadan kapanır ve paydadan TAMAMEN düşer.
    Bu, limitli girişin bedelini görünmez kılar: geri çekilme yapmayan (yani
    YÜKSELEN) isimler sistematik olarak elenir.

    ÖLÇÜLDÜ (2026-08-15, replay): tetiklenmeyenlerin plansız H=20 alfası
    +6.93pp, tetiklenenlerinki +5.08pp → fark +1.85pp. Yön, "limitli giriş bir
    avantajdır" hipotezinin TERSİ.
    """

    def test_kacan_planlarin_bedeli_olculur(self, cfg, con):
        rid = _kayit(cfg, con, asof="2024-01-15", ticker="AAA", alfa=2.0)
        _kayit(cfg, con, asof="2024-02-15", ticker="BBB", alfa=1.0, run_id=rid)
        con.execute("UPDATE outcomes SET resolution='giris_olmadi', "
                    "fwd_alpha_20d_ew=9.0 WHERE prediction_id LIKE '%AAA%'")
        con.execute("UPDATE outcomes SET fwd_alpha_20d_ew=3.0 "
                    " WHERE prediction_id LIKE '%BBB%'")
        con.commit()
        t = evaluate.tetiklenmeme_bedeli(cfg, con)
        assert t["n_tetiklenmeyen"] == 1 and t["n_tetiklenen"] == 1
        assert t["fark"] == pytest.approx(6.0)
        assert "SEÇİM YANLILIĞI" in t["not"]

    def test_fwd_yoksa_SIFIR_DEGIL_HARIC(self, cfg, con):
        """Ufku dolmamış tahmin ortalamayı sulandırmamalı (#009)."""
        _kayit(cfg, con, asof="2024-01-15", ticker="AAA", alfa=2.0)
        t = evaluate.tetiklenmeme_bedeli(cfg, con)
        assert t["fark"] is None and t["hukum"] == stats.HUKUM_OLCUM_YOK


class TestAracSayimi:
    """B-01 KİLİDİ — sonucu OLMAYAN ama tahmini OLAN araç görünmeli.

    ⚠ NE OLUYORDU (2026-08-28 denetimi): `evaluate.araclar` `outcomes` ile
    INNER JOIN yapıyordu. Ölçüldü:

        araclar()  →  {'replay': 20, 'gemini-3.6-flash': 3, 'claude-code': 2}
        gerçek     →  gemini-3.5-flash 252 · gemini-3.6-flash 54 · replay 20 ·
                      gpt-5-mini 18 · claude-code 18

    Son üç haftanın BÜTÜN kararlarını veren model haftalık değerlendirmeye hiç
    girmiyordu; `reports/degerlendirme_gemini-3.5-flash_*.md` diye bir dosya
    yoktu ve 08-16 ile 08-23 Telegram özetleri birebir aynıydı. Kullanıcının
    sohbetinde günlük mesajlar her gün o modeli yazıyor, haftalık hiç anmıyordu.

    ADR #013'ün vaadi (*"hangi model daha iyi analist sorusunu sistem kendisi
    cevaplar"*) bu JOIN yüzünden YAPISAL OLARAK imkânsızdı: yeni bir modele
    geçilince o model ilk sonucu çözülene kadar (≈1 ay) görünmez oluyordu.
    """

    def _kur(self, con, tool, n, *, sonuclu=False):
        """Bir aracın `n` tahmini olsun; `sonuclu` ise çözülmüş sonucu da olsun."""
        rid = f"2026-08-26-{tool}-1"
        con.execute(
            "INSERT INTO llm_runs (run_id, asof, tool, bundle_sha, output_path, "
            "  audit_passed, hard_fail_codes, created_utc) "
            "VALUES (?,?,?,'sha','',1,'[]','x')", (rid, "2026-08-26", tool))
        for i in range(n):
            pid = f"{tool}-p{i}"
            con.execute(
                "INSERT INTO predictions (prediction_id, run_id, asof, ticker, "
                "  factor_set_version, weights_hash, indicator_set_version, regime, "
                "  signal, action, confidence, confidence_p, thesis, "
                "  counter_scenario, key_risk, falsifier, close_at_asof, created_utc) "
                "VALUES (?,?,?,?, 'v1','h','v1','neutral', 'hold','izle','dusuk',"
                "        0.3, 't','c','k','f', 100.0, 'x')",
                (pid, rid, "2026-08-26", f"T{i}"))
            if sonuclu:
                con.execute(
                    "INSERT INTO outcomes (prediction_id, resolved_date, "
                    "  resolution, resolver_version, resolved_utc) "
                    "VALUES (?,'2026-08-26','sure','v1','x')", (pid,))
        con.commit()

    def test_SONUCU_OLMAYAN_arac_GORUNUR(self, con):
        from src import evaluate
        self._kur(con, "yeni-model", 5)                 # hiç çözülmüş sonucu yok
        self._kur(con, "eski-model", 2, sonuclu=True)

        a = evaluate.araclar(con)
        assert "yeni-model" in a, \
            "sonucu olmayan ama 5 tahmini olan araç sayımda YOK — aktif model görünmez"
        assert a["yeni-model"] == 5, f"tahmin sayısı yanlış: {a}"
        assert a["eski-model"] == 2

    def test_saglik_ile_evaluate_AYNI_sayiyi_verir(self, con):
        """L-022 madde 2: iki kanal aynı olguyu basıyorsa eşliği test zorlar.

        `saglik` "journal kaynağı" kontrolü bu olguyu DOĞRU sayıyordu
        (`predictions` × `llm_runs`), `evaluate.araclar` yanlış. İki kaynağın
        ayrışması tam olarak bu bulguyu üretti.
        """
        from src import db, evaluate
        self._kur(con, "yeni-model", 5)
        self._kur(con, "eski-model", 2, sonuclu=True)

        saglik_sayimi = {r["tool"]: r["n"] for r in db.fetch_all(
            con, "SELECT r.tool, COUNT(*) n FROM predictions p "
                 " JOIN llm_runs r ON r.run_id = p.run_id GROUP BY r.tool")}
        assert evaluate.araclar(con) == saglik_sayimi, \
            "iki kanal aynı olguyu FARKLI sayıyor"

    def test_sonucu_olmayan_arac_run_COKMEZ(self, cfg, con):
        """Görünür olmak yetmez: değerlendirme o araçta çökmemeli."""
        from src import evaluate
        self._kur(con, "yeni-model", 5)
        e = evaluate.run(cfg, con, tool="yeni-model")
        assert (e.get("alfa") or {}).get("hukum") == "ölçüm yok"
