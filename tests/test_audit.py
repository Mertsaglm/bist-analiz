"""Denetim testleri — HER HF kodu tek tek tetiklenir.

Faz 5'in tanımlı bitişi bu dosya: kasten bozulmuş bir çıktı, tam olarak
beklenen HF kodunu patlatmalı. Bir kod hiç tetiklenemiyorsa o kontrol
ölüdür ve varlığı yanlış güven verir.
"""

from __future__ import annotations

import copy

import pytest

from src import audit, journal, llm_io, schema
from tests.conftest import add_plan, add_universe


def _bundle(cfg) -> dict:
    b = {
        "bundle_version": schema.BUNDLE_VERSION,
        "asof": "2026-07-24",
        "uyari": "Ölçülen kenar yok.",
        "rejim": {
            "etiket": "neutral",
            "pozisyon_politikasi": {"nakit_pct": 40.0, "maks_pozisyon": 2,
                                    "sektor_basi_maks": 1},
        },
        "evren": [
            {"ticker": "AAA", "sektor": "banka",
             "fiyat": {"kapanis": 100.0, "onceki_kapanis": 99.0},
             "gostergeler": {"atr14": 2.5},
             "faktorler": {"yuzdelik": 90.0},
             "veri_kalitesi": {"ok": True, "uyarilar": []},
             "plan_menusu": [{"plan_id": "AAA-1", "entry_high": 100.0,
                              "stop_price": 95.0, "targets": [{"price": 110.0}]}],
             "plan_yok_nedeni": None, "acik_tahminler": [],
             "haberler": [{"id": "kap-1", "baslik": "x"}]},
            {"ticker": "BBB", "sektor": "banka",
             "fiyat": {"kapanis": 50.0, "onceki_kapanis": 50.0},
             "gostergeler": {"atr14": 1.0},
             "faktorler": {"yuzdelik": 30.0},
             "veri_kalitesi": {"ok": True, "uyarilar": []},
             "plan_menusu": [{"plan_id": "BBB-1", "entry_high": 50.0,
                              "stop_price": 47.0, "targets": [{"price": 56.0}]}],
             "plan_yok_nedeni": None, "acik_tahminler": [], "haberler": []},
            {"ticker": "CCC", "sektor": "telekom",
             "fiyat": {"kapanis": 20.0, "onceki_kapanis": 20.0},
             "gostergeler": {"atr14": 0.5},
             "faktorler": {"yuzdelik": 10.0},
             "veri_kalitesi": {"ok": False, "uyarilar": ["sıfır hacim"]},
             "plan_menusu": [], "plan_yok_nedeni": "veri kalitesi",
             "acik_tahminler": [], "haberler": []},
        ],
        "portfoy": {"pozisyonlar": []},
        "izin_verilen_degerler": {
            **cfg["llm"]["enums"],
            "plan_ids": {"AAA": ["AAA-1"], "BBB": ["BBB-1"], "CCC": []},
        },
        "kurallar_ozeti": [],
    }
    b["bundle_sha"] = llm_io.bundle_sha(b)
    return b


def _prose(ad: str) -> dict:
    """Yeterince uzun ve BİRBİRİNDEN FARKLI prose (şablon tespitine takılmasın)."""
    return {
        "thesis": f"{ad} için kurulan tez, plan geometrisinin makul olmasına dayanıyor "
                  f"ve rejimin izin verdiği sınırlar içinde kalıyor bugün.",
        "counter_scenario": f"{ad} tersine dönerse geniş tabanlı bir zayıflık "
                            f"başlamış demektir ve tez erken kapatılmalıdır hemen.",
        "key_risk": f"{ad} tarafında ölçülen kenar yoktur; bu bir kenar iddiası "
                    f"değil, yalnızca disiplinli bir geometri denemesidir burada.",
        "falsifier": f"{ad} önümüzdeki beş işlem gününde destek seviyesinin altına "
                     f"günlük kapanış yaparsa tez düşer ve pozisyon kapatılır.",
    }


def _output(b: dict) -> dict:
    return {
        "schema_version": schema.OUTPUT_SCHEMA_VERSION,
        "asof": b["asof"],
        "bundle_sha": b["bundle_sha"],
        "tool": "claude-code",
        "market_view": {"regime_agreement": "katiliyorum",
                        "regime_note": "Rejim nötr, katılıyorum.",
                        "portfolio_action": "koru"},
        "stocks": [
            {"ticker": "AAA", "signal": "buy", "action": "plan_sec",
             "selected_plan_id": "AAA-1", "veto_code": None,
             "confidence": "orta", **_prose("AAA"),
             "news_refs": [], "news_reading": None},
            {"ticker": "BBB", "signal": "hold", "action": "izle",
             "selected_plan_id": None, "veto_code": None,
             "confidence": "dusuk", **_prose("BBB"),
             "news_refs": [], "news_reading": None},
        ],
        "not_covered": ["CCC"],
        "analyst_notes": "",
    }


@pytest.fixture
def temiz(cfg, con):
    add_universe(con, "AAA"); add_universe(con, "BBB"); add_universe(con, "CCC")
    b = _bundle(cfg)
    return b, _output(b)


def _kodlar(bulgular) -> set[str]:
    return {f.code for f in audit.hard_fails(bulgular)}


class TestTemiz:
    def test_gecerli_cikti_temiz_gecer(self, cfg, con, temiz):
        b, o = temiz
        assert _kodlar(audit.audit(cfg, b, o, con)) == set()


class TestKimlikYapi:
    def test_HF01_sema_surumu(self, cfg, con, temiz):
        b, o = temiz
        o["schema_version"] = "eski_v0"
        assert "HF-01" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF02_bundle_sha(self, cfg, con, temiz):
        """Sessiz felaket: sayılar bugünün, yorum dünün olur."""
        b, o = temiz
        o["bundle_sha"] = "baska-bir-paket"
        assert "HF-02" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF03_asof(self, cfg, con, temiz):
        b, o = temiz
        o["asof"] = "2026-07-23"
        assert "HF-03" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF04_bilinmeyen_ticker(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["ticker"] = "ZZZ"
        assert "HF-04" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF05_tekrarli_ticker(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"].append(copy.deepcopy(o["stocks"][0]))
        assert "HF-05" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF06_kapsama(self, cfg, con, temiz):
        b, o = temiz
        o["not_covered"] = []
        assert "HF-06" in _kodlar(audit.audit(cfg, b, o, con))


class TestEnum:
    def test_HF07_signal(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["signal"] = "yukselir"
        assert "HF-07" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF08_action(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["action"] = "hemen_al"
        assert "HF-08" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF09_sayisal_guven(self, cfg, con, temiz):
        """Güven SAYI olamaz — kalibre edilmemiş olasılık ölçüme sokulamaz."""
        b, o = temiz
        o["stocks"][0]["confidence"] = 0.85
        assert "HF-09" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF10_veto_kodu_eksik(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["action"] = "plan_reddet"
        o["stocks"][0]["selected_plan_id"] = None
        assert "HF-10" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF11_market_view_enum(self, cfg, con, temiz):
        b, o = temiz
        o["market_view"]["portfolio_action"] = "her_seyi_sat"
        assert "HF-11" in _kodlar(audit.audit(cfg, b, o, con))


class TestPlanMenusu:
    def test_HF12_uydurulmus_plan_id(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["selected_plan_id"] = "AAA-UYDURMA"
        assert "HF-12" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF13_plan_sec_ama_plan_yok(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["selected_plan_id"] = None
        assert "HF-13" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF14_plan_var_ama_aksiyon_farkli(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][1]["selected_plan_id"] = "BBB-1"
        assert "HF-14" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF15_plan_uretilmemis_hisseye_plan(self, cfg, con, temiz):
        b, o = temiz
        o["not_covered"] = []
        o["stocks"].append({"ticker": "CCC", "signal": "buy", "action": "plan_sec",
                            "selected_plan_id": "CCC-1", "veto_code": None,
                            "confidence": "orta", **_prose("CCC"),
                            "news_refs": [], "news_reading": None})
        b["izin_verilen_degerler"]["plan_ids"]["CCC"] = ["CCC-1"]
        assert "HF-15" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF16_veri_kalitesi_bozuk_hisseye_plan(self, cfg, con, temiz):
        b, o = temiz
        b["evren"][2]["plan_yok_nedeni"] = None
        b["izin_verilen_degerler"]["plan_ids"]["CCC"] = ["CCC-1"]
        o["not_covered"] = []
        o["stocks"].append({"ticker": "CCC", "signal": "buy", "action": "plan_sec",
                            "selected_plan_id": "CCC-1", "veto_code": None,
                            "confidence": "orta", **_prose("CCC"),
                            "news_refs": [], "news_reading": None})
        assert "HF-16" in _kodlar(audit.audit(cfg, b, o, con))


class TestSayisalSizinti:
    """HF-17 TAŞIYICI KOL: şemada fiyat alanı olmaması yalnız YAPISAL sızıntıyı
    durdurur; asıl hata modu metinseldir."""

    def test_HF17_uydurulmus_sayi(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["thesis"] = (
            "Hedefin 3247.89 seviyesine kadar uzanması makul görünüyor bu "
            "koşullarda ve tez bunun üzerine kuruluyor bugün itibarıyla.")
        assert "HF-17" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF17_paketteki_sayi_serbest(self, cfg, con, temiz):
        """Paketteki sayıyı kullanmak YASAK DEĞİL — uydurmak yasak."""
        b, o = temiz
        o["stocks"][0]["thesis"] = (
            "Stop 95.00 seviyesinde duruyor ve giriş 100.00 bandında; bu "
            "geometri rejimin izin verdiği sınırlar içinde kalıyor bugün.")
        assert "HF-17" not in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF17_tr_ve_en_yazim_ayni_token(self, cfg, con, temiz):
        """Model biçim değiştirerek denetimi ATLAYAMAZ."""
        assert llm_io.numeric_tokens("1.234,56") & llm_io.numeric_tokens("1234.56")

    def test_HF18_izinsiz_fiyat_ifadesi(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["key_risk"] = (
            "Fiyat 987.65 TL civarına gerilerse tez tamamen geçersiz kalır ve "
            "pozisyonun kapatılması gerekir hemen ertesi gün.")
        assert "HF-18" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF19_izinsiz_yuzde(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["counter_scenario"] = (
            "Beklenen getiri %47.3 seviyesinde olabilir ve bu senaryoda tez "
            "fazlasıyla iyimser kalır, dolayısıyla dikkatli olunmalıdır.")
        assert "HF-19" in _kodlar(audit.audit(cfg, b, o, con))


class TestTutarlilik:
    def test_HF20_sinyal_aksiyon_celiskisi(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["action"] = "islem_yok"
        o["stocks"][0]["selected_plan_id"] = None
        assert "HF-20" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF21_olmayan_pozisyon_satilamaz(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][1]["signal"] = "sell"
        assert "HF-21" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF21_tutulan_pozisyon_satilabilir(self, cfg, con, temiz):
        b, o = temiz
        journal.set_holding(con, "BBB", 100, 50.0)
        o["stocks"][1]["signal"] = "sell"
        assert "HF-21" not in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF22_strong_buy_siralamayi_ezemez(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][1]["signal"] = "strong_buy"      # yüzdelik 30 < 70
        o["stocks"][1]["action"] = "plan_sec"
        o["stocks"][1]["selected_plan_id"] = "BBB-1"
        assert "HF-22" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF23_maks_pozisyon_asilamaz(self, cfg, con, temiz):
        b, o = temiz
        b["rejim"]["pozisyon_politikasi"]["maks_pozisyon"] = 1
        b["rejim"]["pozisyon_politikasi"]["sektor_basi_maks"] = 5
        o["stocks"][1]["action"] = "plan_sec"
        o["stocks"][1]["selected_plan_id"] = "BBB-1"
        o["stocks"][1]["signal"] = "buy"
        assert "HF-23" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF24_sektor_tavani(self, cfg, con, temiz):
        b, o = temiz
        b["rejim"]["pozisyon_politikasi"]["maks_pozisyon"] = 5
        o["stocks"][1]["action"] = "plan_sec"        # AAA ve BBB ikisi de banka
        o["stocks"][1]["selected_plan_id"] = "BBB-1"
        o["stocks"][1]["signal"] = "buy"
        assert "HF-24" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF25_riskoff_ta_risk_artirilamaz(self, cfg, con, temiz):
        b, o = temiz
        b["rejim"]["etiket"] = "risk-off"
        o["market_view"]["portfolio_action"] = "risk_artir"
        assert "HF-25" in _kodlar(audit.audit(cfg, b, o, con))


class TestProseKalitesi:
    def test_HF26_bos_prose(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["falsifier"] = ""
        assert "HF-26" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF27_sablon_tez(self, cfg, con, temiz):
        """Aynı prose birden çok hissede → kopyala-yapıştır."""
        b, o = temiz
        for alan in ("thesis", "counter_scenario", "key_risk", "falsifier"):
            o["stocks"][1][alan] = o["stocks"][0][alan]
        assert "HF-27" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF27_sadece_sayi_degistirmek_yetmez(self, cfg, con, temiz):
        """Model aynı cümleyi farklı sayılarla tekrarlıyorsa bu YİNE şablondur."""
        b, o = temiz
        for alan in ("thesis", "counter_scenario", "key_risk", "falsifier"):
            o["stocks"][1][alan] = o["stocks"][0][alan].replace("AAA", "AAA 42")
        assert "HF-27" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF28_uydurulmus_haber_id(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["news_refs"] = ["kap-uydurma-999"]
        assert "HF-28" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF29_kaynaksiz_haber_yorumu(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["news_reading"] = "Haber olumlu görünüyor."
        o["stocks"][0]["news_refs"] = []
        assert "HF-29" in _kodlar(audit.audit(cfg, b, o, con))


class TestSurec:
    def test_HF30_acik_tez_sessizce_dusurulemez(self, cfg, con, temiz):
        b, o = temiz
        add_plan(con, "AAA-1", ticker="AAA", asof="2026-07-01")
        run_id = journal.create_run(cfg, con, asof="2026-07-01", tool="t",
                                    bundle_sha="s")
        journal.record(cfg, con, run_id=run_id, asof="2026-07-01", ticker="AAA",
                       analist={"signal": "buy", "action": "plan_sec",
                                "confidence": "orta", "thesis": "t",
                                "counter_scenario": "c", "key_risk": "k",
                                "falsifier": "f"},
                       plan={"plan_id": "AAA-1", "time_barrier_date": "2026-08-01"},
                       faktor={"score": 1.0, "rank": 1, "pct": 90.0,
                               "weights_hash": "h"},
                       referans={"close": 100.0})
        o["stocks"] = [s for s in o["stocks"] if s["ticker"] != "AAA"]
        o["not_covered"] = ["AAA", "CCC"]
        assert "HF-30" in _kodlar(audit.audit(cfg, b, o, con))


class TestKapsam:
    def test_her_HF_kodunun_testi_var(self):
        """Bir kod hiç tetiklenemiyorsa o kontrol ÖLÜDÜR ve yanlış güven verir."""
        import inspect
        kaynak = inspect.getsource(__import__("tests.test_audit", fromlist=["x"]))
        eksik = [k for k in audit.all_codes() if k.replace("-", "") not in
                 kaynak.replace("-", "")]
        assert not eksik, f"testi olmayan HF kodları: {eksik}"


class TestUyarilar:
    def test_uyarilar_engellemez(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["confidence"] = "yuksek"
        b["evren"][0]["faktorler"]["yuzdelik"] = 20.0
        bulgular = audit.audit(cfg, b, o, con)
        assert any(f.code == "W-02" for f in bulgular)
        assert not audit.hard_fails(bulgular), "uyarı sert hataya dönüşmüş"
