"""Kâğıt portföy — ADR #019.

Bu dosyanın en önemli testi `test_KARNE_ile_AYRISMAZ`: portföyün TL sonucu
`outcomes.ret_pct`'ten türetilir, yeniden hesaplanmaz. Ayrı bir formül yazmak,
karne ile portföyün farklı sayı basacağı ilk yer olurdu — ADR #019'un
"portföy TÜREV bir görünümdür, defter değil" kararının tüm gerekçesi bu.
"""

from __future__ import annotations

import pytest

from src import db, portfoy
from tests.conftest import add_universe


def _bar(con, ticker, tarihler, fiyat=100.0):
    db.upsert_many(
        con, "bars_daily",
        ["ticker", "date", "o", "h", "l", "c", "v", "c_tr", "turnover_try",
         "source", "ingested_utc"],
        [(ticker, d, fiyat, fiyat * 1.02, fiyat * 0.98, fiyat, 1e6, fiyat, 1e9,
          "test", "now") for d in tarihler])


def _plan(con, *, pid, asof, ticker, boyut=10.0, regime="risk-on",
          tool="gemini-3.5-flash", entry=(99.0, 100.0), stop=90.0):
    db.upsert_many(con, "llm_runs",
                   ["run_id", "asof", "tool", "bundle_sha", "output_path",
                    "audit_passed", "created_utc"],
                   [(f"run-{pid}", asof, tool, "sha",
                     f"llm/out/{asof}/{pid}.json", 1, "now")])
    db.upsert_many(
        con, "plan_options",
        ["plan_id", "asof", "ticker", "kind", "payload", "created_utc"],
        [(f"{ticker}-{asof}-A", asof, ticker, "dogrudan", "{}", "now")])
    db.upsert_many(
        con, "predictions",
        ["prediction_id", "run_id", "asof", "ticker", "regime", "plan_id",
         "position_size_pct", "entry_low", "entry_high", "stop_price",
         "time_barrier_date", "signal", "action", "confidence", "confidence_p",
         "thesis", "counter_scenario", "key_risk", "falsifier",
         "close_at_asof", "factor_set_version", "weights_hash",
         "indicator_set_version", "created_utc"],
        [(pid, f"run-{pid}", asof, ticker, regime, f"{ticker}-{asof}-A",
          boyut, entry[0], entry[1], stop, "2099-01-01", "buy", "plan_sec",
          "orta", 0.5, "t", "c", "k", "f", 100.0, "v1", "h", "v1", "now")])


def _sonuc(con, pid, *, giris, giris_fiyat, cikis, cikis_fiyat, ret_pct,
           resolution="hedef"):
    db.upsert_many(
        con, "outcomes",
        ["prediction_id", "resolved_date", "resolution", "entry_date",
         "entry_price", "exit_date", "exit_price", "ret_pct",
         "resolver_version", "resolved_utc"],
        [(pid, cikis, resolution, giris, giris_fiyat, cikis, cikis_fiyat,
          ret_pct, "resolver_v1", "now")])


@pytest.fixture
def kur(cfg, con):
    """İki isim, bol bar. Fiyat sabit 100 — aritmetik gözle doğrulanabilsin."""
    gunler = [f"2026-03-{d:02d}" for d in range(2, 28)]
    for t, sek in (("AAA", "banka"), ("BBB", "sanayi"), ("CCC", "banka")):
        add_universe(con, t, sector=sek)
        _bar(con, t, gunler)
    return gunler


class TestTemel:
    def test_bos_journal_baslangic_sermayesi(self, cfg, con):
        d = portfoy.simule(cfg, con)
        assert d["sermaye"] == cfg["portfoy"]["baslangic_sermaye_try"]
        assert d["pozisyonlar"] == [] and d["kapanan"] == []
        assert d["getiri_pct"] == 0.0

    def test_adet_TAM_SAYI_ve_asagi_yuvarlanir(self, cfg, con, kur):
        """10.000 × %10 = 1.000 TL; 100 TL'lik hisseden tam 10 adet."""
        _plan(con, pid="p1", asof="2026-03-03", ticker="AAA", boyut=10.0)
        _sonuc(con, "p1", giris="2026-03-04", giris_fiyat=100.0,
               cikis="2026-03-10", cikis_fiyat=110.0, ret_pct=9.7)
        d = portfoy.simule(cfg, con)
        al = [x for x in d["islemler"] if x["yon"] == "AL"][0]
        assert al["adet"] == 10
        assert al["tutar"] == 1000.0

    def test_sermaye_bir_lota_yetmezse_ALINMAZ(self, cfg, con, kur):
        """⚠ Sessizce 0 adet almak, portföyü 'işlem yapmış' göstermek olurdu."""
        _plan(con, pid="p1", asof="2026-03-03", ticker="AAA", boyut=0.5,
              entry=(99.0, 100.0))
        _bar(con, "AAA", ["2026-03-04"], fiyat=100.0)
        d = portfoy.simule(cfg, con)
        assert d["islemler"] == []
        assert [r["sebep"] for r in d["reddedilen"]] == ["sermaye_yetersiz"]


class TestKarneIleTutarlilik:
    def test_KARNE_ile_AYRISMAZ(self, cfg, con, kur):
        """TL kâr `outcomes.ret_pct`'ten TÜRETİLİR — ADR #019'un çekirdeği.

        Ayrı bir formül (ör. çıkış−giriş, maliyet elle) yazsaydık portföy ile
        karne aynı işlem için farklı sayı basardı ve hangisinin doğru olduğu
        sorusu cevapsız kalırdı.
        """
        _plan(con, pid="p1", asof="2026-03-03", ticker="AAA", boyut=10.0)
        _sonuc(con, "p1", giris="2026-03-04", giris_fiyat=100.0,
               cikis="2026-03-10", cikis_fiyat=112.0, ret_pct=11.7)
        d = portfoy.simule(cfg, con)
        k = d["kapanan"][0]
        assert k["ret_pct"] == 11.7
        # 10 adet × 100 TL = 1000 TL maliyet; %11.7 → 117 TL kâr
        assert k["kar_try"] == pytest.approx(117.0, abs=0.01)
        assert d["sermaye"] == pytest.approx(10117.0, abs=0.01)
        assert d["gerceklesen_kar_try"] == pytest.approx(117.0, abs=0.01)

    def test_giris_fiyati_OUTCOMES_tan_gelir(self, cfg, con, kur):
        """Resolver ne dediyse o. Portföy kendi dolum kuralını YAZMAZ."""
        _plan(con, pid="p1", asof="2026-03-03", ticker="AAA", boyut=10.0,
              entry=(99.0, 100.0))
        _sonuc(con, "p1", giris="2026-03-09", giris_fiyat=97.5,
               cikis="2026-03-12", cikis_fiyat=105.0, ret_pct=7.4)
        d = portfoy.simule(cfg, con)
        al = [x for x in d["islemler"] if x["yon"] == "AL"][0]
        assert al["fiyat"] == 97.5 and al["tarih"] == "2026-03-09"


class TestKisitlar:
    def test_AYNI_ISIMDE_ikinci_pozisyon_ACILMAZ(self, cfg, con, kur):
        """⚠ 2026-08-15 denetimi: KRDMD altı gün üst üste seçilmişti; harfiyen
        uygulansa tek isimde ~%29 birikirdi, rejim tavanı toplam %20 iken."""
        for i, gun in enumerate(("2026-03-03", "2026-03-04", "2026-03-05")):
            _plan(con, pid=f"p{i}", asof=gun, ticker="AAA", boyut=10.0)
            _sonuc(con, f"p{i}", giris="2026-03-06", giris_fiyat=100.0,
                   cikis="2026-03-20", cikis_fiyat=105.0, ret_pct=4.7)
        d = portfoy.simule(cfg, con)
        assert len([x for x in d["islemler"] if x["yon"] == "AL"]) == 1
        assert [r["sebep"] for r in d["reddedilen"]] == \
            ["isim_zaten_acik", "isim_zaten_acik"]

    def test_KONTENJAN_rejim_tavanindan_gelir(self, cfg, con, kur):
        """risk-off'ta maks 2 pozisyon — üçüncü isim alınmaz."""
        for i, t in enumerate(("AAA", "BBB", "CCC")):
            _plan(con, pid=f"p{i}", asof="2026-03-03", ticker=t, boyut=5.0,
                  regime="risk-off")
            _sonuc(con, f"p{i}", giris="2026-03-04", giris_fiyat=100.0,
                   cikis="2026-03-20", cikis_fiyat=105.0, ret_pct=4.7)
        d = portfoy.simule(cfg, con)
        maks = cfg["rejim"]["politika"]["risk-off"]["maks_pozisyon"]
        assert len([x for x in d["islemler"] if x["yon"] == "AL"]) == maks
        assert "kontenjan_dolu" in [r["sebep"] for r in d["reddedilen"]]

    def test_SEKTOR_tavani_uygulanir(self, cfg, con, kur):
        """AAA ve CCC aynı sektörde (banka); tavan 2 ise ikisi de girer,
        1 olsaydı ikincisi elenirdi. Kural config'ten okunur, koda gömülmez."""
        cfg = {**cfg, "rejim": {**cfg["rejim"], "sektor_basi_maks_pozisyon": 1}}
        for i, t in enumerate(("AAA", "CCC")):
            _plan(con, pid=f"p{i}", asof="2026-03-03", ticker=t, boyut=5.0)
            _sonuc(con, f"p{i}", giris="2026-03-04", giris_fiyat=100.0,
                   cikis="2026-03-20", cikis_fiyat=105.0, ret_pct=4.7)
        d = portfoy.simule(cfg, con)
        assert len([x for x in d["islemler"] if x["yon"] == "AL"]) == 1
        assert "sektor_tavani" in [r["sebep"] for r in d["reddedilen"]]

    def test_KAPANAN_pozisyonun_yeri_ERTESI_GUN_bosalir(self, cfg, con, kur):
        """⚠ KÖTÜMSER SIRA. Gün içi sıra bilinemez (`resolver.barrier_hit` ile
        aynı gerekçe); kapanışı önce işlemek, aynı gün boşalan yere hemen yeni
        pozisyon aldırırdı — yani gün içinde iki kez risk alındığını varsaymak.
        """
        _plan(con, pid="p1", asof="2026-03-03", ticker="AAA", boyut=5.0,
              regime="risk-off")
        _sonuc(con, "p1", giris="2026-03-04", giris_fiyat=100.0,
               cikis="2026-03-10", cikis_fiyat=105.0, ret_pct=4.7)
        _plan(con, pid="p2", asof="2026-03-05", ticker="BBB", boyut=5.0,
              regime="risk-off")
        _sonuc(con, "p2", giris="2026-03-06", giris_fiyat=100.0,
               cikis="2026-03-20", cikis_fiyat=105.0, ret_pct=4.7)
        # Üçüncü isim, AAA'nın kapandığı GÜN girmeye çalışıyor
        _plan(con, pid="p3", asof="2026-03-09", ticker="CCC", boyut=5.0,
              regime="risk-off")
        _sonuc(con, "p3", giris="2026-03-10", giris_fiyat=100.0,
               cikis="2026-03-20", cikis_fiyat=105.0, ret_pct=4.7)
        d = portfoy.simule(cfg, con)
        alinanlar = [x["ticker"] for x in d["islemler"] if x["yon"] == "AL"]
        assert "CCC" not in alinanlar, "kapanan pozisyonun yeri AYNI GÜN boşaldı"
        assert "kontenjan_dolu" in [r["sebep"] for r in d["reddedilen"]]


class TestKaynak:
    def test_REPLAY_portfoye_GIRMEZ(self, cfg, con, kur):
        """`replay` VEKİL bir analisttir (`evaluate.kaynak_sec`); kararları
        sistemin karnesine karıştırılmaz."""
        _plan(con, pid="p1", asof="2026-03-03", ticker="AAA", tool="replay")
        _sonuc(con, "p1", giris="2026-03-04", giris_fiyat=100.0,
               cikis="2026-03-10", cikis_fiyat=110.0, ret_pct=9.7)
        d = portfoy.simule(cfg, con)
        assert d["islemler"] == [] and d["reddedilen"] == []
        assert d["sermaye"] == cfg["portfoy"]["baslangic_sermaye_try"]


class TestSozlesme:
    def test_RED_SEBEPLERI_etiket_esligi(self):
        """§12.2 yapı eşliği: kümede olup etiketi olmayan bir kod eklenirse
        rapor sessizce 'None' basar."""
        assert set(portfoy.RED_SEBEPLERI) == set(portfoy.RED_ETIKET)

    def test_reddedilen_sebepleri_KUMEDE(self, cfg, con, kur):
        for i, t in enumerate(("AAA", "BBB", "CCC")):
            _plan(con, pid=f"p{i}", asof="2026-03-03", ticker=t, boyut=5.0,
                  regime="risk-off")
            _sonuc(con, f"p{i}", giris="2026-03-04", giris_fiyat=100.0,
                   cikis="2026-03-20", cikis_fiyat=105.0, ret_pct=4.7)
        d = portfoy.simule(cfg, con)
        for r in d["reddedilen"]:
            assert r["sebep"] in portfoy.RED_SEBEPLERI

    def test_BILINMEYEN_rejimde_EN_SIKI_politika(self, cfg, con, kur):
        """⚠ Gevşek varsayılan, bilinmeyen bir etikette tavanı sessizce
        kaldırırdı — "veri yok" ile "sorun yok"un portföy hâli (#009)."""
        p = portfoy._politika(cfg, "boyle-bir-rejim-yok")
        en_siki = min(cfg["rejim"]["politika"].values(),
                      key=lambda x: x["maks_pozisyon"])
        assert p["maks_pozisyon"] == en_siki["maks_pozisyon"]

    def test_DETERMINIST(self, cfg, con, kur):
        """Aynı girdi → aynı çıktı. Türev bir görünümün ilk şartı."""
        for i, t in enumerate(("AAA", "BBB")):
            _plan(con, pid=f"p{i}", asof="2026-03-03", ticker=t, boyut=5.0)
            _sonuc(con, f"p{i}", giris="2026-03-04", giris_fiyat=100.0,
                   cikis="2026-03-10", cikis_fiyat=105.0, ret_pct=4.7)
        a = portfoy.simule(cfg, con)
        b = portfoy.simule(cfg, con)
        assert a == b


class TestAsof:
    def test_asof_GELECEGI_gormez(self, cfg, con, kur):
        """`asof` verilince o günden sonraki giriş/çıkış İŞLENMEZ —
        geçmişe dönük rapor üretmek look-ahead'siz olmalı."""
        _plan(con, pid="p1", asof="2026-03-03", ticker="AAA", boyut=10.0)
        _sonuc(con, "p1", giris="2026-03-04", giris_fiyat=100.0,
               cikis="2026-03-20", cikis_fiyat=110.0, ret_pct=9.7)
        d = portfoy.simule(cfg, con, asof="2026-03-10")
        assert d["kapanan"] == [], "çıkış asof'tan SONRA ama kapanmış sayıldı"
        assert [p["ticker"] for p in d["pozisyonlar"]] == ["AAA"]
        assert d["gerceklesen_kar_try"] == 0.0
