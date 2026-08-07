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


# Oturum boyunca GERÇEKTEN ateşlenen kodlar. `TestKapsam` bunu kullanır:
# kaynak metnini greplemek bir kodun tetiklenebildiğini KANITLAMAZ.
GORULEN_KODLAR: set[str] = set()


def _kodlar(bulgular) -> set[str]:
    k = {f.code for f in audit.hard_fails(bulgular)}
    GORULEN_KODLAR.update(k)
    return k


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

    def test_HF17_tarih_izinli_sayi_URETMEZ(self, cfg):
        """⚠ REGRESYON KİLİDİ (2026-07-27 denetimi).

        `_SAYI` regex'i "2026-07-24" dizesinde `-07` ve `-24`'ü de yakalıyordu;
        paketteki her tarih izinli listeye NEGATİF TAMSAYI enjekte ediyordu.
        Sonuç: uydurma "%-7 geriledi" denetimden geçiyor VE hangi negatif
        sayının geçtiği o günkü TAKVİME bağlı oluyordu.
        """
        izin = llm_io.allowed_numeric_tokens(
            {"asof": "2026-07-24", "karar_gunu": "2026-08-21", "evren": []}, cfg)
        assert "-7" not in izin and "-24" not in izin and "-8" not in izin

    def test_HF17_prosedeki_tarih_YANLIS_ALARM_uretmez(self, cfg, con, temiz):
        """Simetri şart: tarih paket tarafında maskeleniyorsa prose tarafında da
        maskelenmeli, yoksa denetim sayı uydurmayı değil takvim yazmayı cezalandırır."""
        b, o = temiz
        o["stocks"][0]["thesis"] = (
            "AAA için zaman bariyeri 2026-08-21 tarihine kadar geçerli olacak "
            "ve o gün pozisyon yeniden değerlendirilecektir mutlaka.")
        assert "HF-17" not in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF18_paketteki_sayiya_FIYAT_anlami_yuklenemez(self, cfg, con, temiz):
        """HF-18, HF-17'DEN BAĞIMSIZ olmalı.

        İlk sürümde koşulu `... and kacak` idi; yani HF-17 zaten patlamışken
        aynı olguyu tekrarlıyordu ve tek başına hiç ateşlenemiyordu.
        Yakalaması gereken ayrı olgu şu: sayı pakette VAR ama BU hissenin
        fiyatı değil — başka bir hissenin kapanışını buraya fiyat diye yazmak.
        """
        b, o = temiz
        # 50.00 pakette var (BBB'nin kapanışı) ama AAA'nın fiyatı değil.
        o["stocks"][0]["key_risk"] = (
            "Fiyat 50.00 TL civarına gerilerse tez tamamen geçersiz kalır ve "
            "pozisyonun kapatılması gerekir hemen ertesi gün mutlaka.")
        kodlar = _kodlar(audit.audit(cfg, b, o, con))
        assert "HF-18" in kodlar
        assert "HF-17" not in kodlar, "HF-18 bağımsız ateşlenemiyor"

    def test_HF18_kendi_fiyatini_yazmak_serbest(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["key_risk"] = (
            "Stop 95.00 TL seviyesinde duruyor ve bu geometri rejimin izin "
            "verdiği sınırlar içinde kalmaya devam ediyor bugün itibarıyla.")
        assert "HF-18" not in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF19_paketteki_sayiya_YUZDE_anlami_yuklenemez(self, cfg, con, temiz):
        """HF-19 da bağımsız: 95.00 pakette bir STOP FİYATIDIR; "%95 olasılık"
        yazmak o sayıyı bambaşka bir büyüklüğe çevirir ve HF-17 bunu göremez."""
        b, o = temiz
        o["stocks"][0]["counter_scenario"] = (
            "Tezin tutma olasılığını %95 civarında görüyorum ve bu senaryoda "
            "pozisyon korunmalıdır, aksi halde erken kapatılır hemen.")
        kodlar = _kodlar(audit.audit(cfg, b, o, con))
        assert "HF-19" in kodlar
        assert "HF-17" not in kodlar, "HF-19 bağımsız ateşlenemiyor"

    def test_HF19_gercek_yuzde_alani_serbest(self, cfg, con, temiz):
        b, o = temiz
        b["evren"][0]["fiyat"]["gunluk_degisim_pct"] = 2.5
        b["bundle_sha"] = llm_io.bundle_sha(b)
        o["bundle_sha"] = b["bundle_sha"]
        o["stocks"][0]["counter_scenario"] = (
            "Günlük değişim %2.5 seviyesinde kaldı; bu, tezin dayandığı "
            "sakin seyrin bozulmadığını gösteriyor bugün itibarıyla açıkça.")
        assert "HF-19" not in _kodlar(audit.audit(cfg, b, o, con))


class TestYapisalSizinti:
    """HF-31 — `schema.py`'de belgelenen ama HİÇ ZORLANMAYAN savunma."""

    def test_HF31_yasak_sayisal_alan(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["t1_price"] = 412.0
        assert "HF-31" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF31_sema_disi_alan(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["benim_ekstra_alanim"] = "x"
        assert "HF-31" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF31_zorunlu_alan_eksik(self, cfg, con, temiz):
        b, o = temiz
        del o["stocks"][0]["key_risk"]
        assert "HF-31" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF31_kok_seviyesinde_fazla_alan(self, cfg, con, temiz):
        b, o = temiz
        o["expected_return"] = 12.5
        assert "HF-31" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF31_temiz_ciktida_atesLENMEZ(self, cfg, con, temiz):
        b, o = temiz
        assert "HF-31" not in _kodlar(audit.audit(cfg, b, o, con))


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

    def test_HF22_SKORLANMAMIS_isme_strong_buy_verilemez(self, cfg, con, temiz):
        """⚠ REGRESYON KİLİDİ (2026-07-27 denetimi).

        `yuzdelik` YALNIZ kapıdan geçen isimlerde dolar. İlk sürüm
        `if pct is not None and pct < esik` diyordu → kontrol tam da kapının
        ELEDİĞİ isimlerde atlanıyordu. Ölçüldü: canlı evrenin 18 isminden
        8'inde `yuzdelik: None`, yani HF-22 evrenin %44'ünde ölüydü.
        """
        b, o = temiz
        b["evren"][1]["faktorler"]["yuzdelik"] = None
        b["bundle_sha"] = llm_io.bundle_sha(b)
        o["bundle_sha"] = b["bundle_sha"]
        o["stocks"][1]["signal"] = "strong_buy"
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


class TestUyarilar:
    def test_uyarilar_engellemez(self, cfg, con, temiz):
        b, o = temiz
        o["stocks"][0]["confidence"] = "yuksek"
        b["evren"][0]["faktorler"]["yuzdelik"] = 20.0
        bulgular = audit.audit(cfg, b, o, con)
        assert any(f.code == "W-02" for f in bulgular)
        assert not audit.hard_fails(bulgular), "uyarı sert hataya dönüşmüş"


# ⚠ Bu sınıf dosyanın SONUNDA durmalı: `GORULEN_KODLAR`'ı yukarıdaki tüm
# testler doldurur ve pytest bir dosyayı tanım sırasına göre koşar.
class TestDeterministikTavan:
    """HF-32 — deterministik katman bir TAVANDIR, model onu aşamaz.

    Fikir borsaci'nin `skill/borsaci/references/buffett.md` dosyasından
    (2026-08-07 repo incelemesi): *"Niteliksel katman kararı YALNIZCA AŞAĞI
    çekebilir, asla yukarı çıkaramaz."* Bizde bu örtük olarak doğruydu
    (LLM sayı üretemez, menüden seçer, rejim tavanı var) ama HİÇBİR YERDE
    YAZMIYOR ve HİÇBİR KOD ZORLAMIYORDU.

    ⚠ NE AÇIKTI: HF-20 boğa sinyalini yalnız `plan_reddet`/`islem_yok` ile
    eşleşince yakalıyor. Yani veri kalitesi düştüğü ya da hisse tavana kilitli
    olduğu için plan BİLE ÜRETİLMEMİŞ bir isme `strong_buy` + `izle` demek
    denetimden temiz geçiyordu: sistem "bu ismin verisine güvenmiyorum" derken
    model en güçlü sinyali verebiliyordu.
    """

    def test_HF32_veri_sinifinda_boga_sinyali_YASAK(self, cfg, con, temiz):
        b, o = temiz
        b["evren"][1]["plan_menusu"] = []
        b["evren"][1]["plan_yok_nedeni"] = "veri kalitesi: sıfır hacim %46"
        b["evren"][1]["plan_yok_sinifi"] = "veri"
        o["stocks"][1]["signal"] = "buy"
        o["stocks"][1]["action"] = "izle"
        o["stocks"][1]["selected_plan_id"] = None
        assert "HF-32" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF32_limit_sinifinda_da_YASAK(self, cfg, con, temiz):
        """Tavana kilitli hisse bugün işlem görmüyor — 'al' diyemezsin."""
        b, o = temiz
        b["evren"][1]["plan_menusu"] = []
        b["evren"][1]["plan_yok_sinifi"] = "limit"
        o["stocks"][1]["signal"] = "accumulate"
        o["stocks"][1]["action"] = "izle"
        o["stocks"][1]["selected_plan_id"] = None
        assert "HF-32" in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF32_GEOMETRI_sinifinda_boga_sinyali_SERBEST(self, cfg, con, temiz):
        """Fiyat sağlam, yalnız plan iskeleti kurulamadı — `izle` tam da odur.

        Bu testin işi kuralın FAZLA GENİŞ olmadığını kanıtlamak. Geometri
        sınıfını da kapatmak, sistemin "R:R yetmedi" dediği her isimde
        analistin görüş bildirmesini yasaklardı.
        """
        b, o = temiz
        b["evren"][1]["plan_menusu"] = []
        b["evren"][1]["plan_yok_nedeni"] = "R:R yetmedi"
        b["evren"][1]["plan_yok_sinifi"] = "geometri"
        o["stocks"][1]["signal"] = "buy"
        o["stocks"][1]["action"] = "izle"
        o["stocks"][1]["selected_plan_id"] = None
        assert "HF-32" not in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF32_veri_sinifinda_HOLD_serbest(self, cfg, con, temiz):
        """Aşağı inmek daima serbest — tavan yalnız YUKARI kapalı."""
        b, o = temiz
        b["evren"][1]["plan_menusu"] = []
        b["evren"][1]["plan_yok_sinifi"] = "veri"
        o["stocks"][1]["signal"] = "hold"
        o["stocks"][1]["action"] = "izle"
        o["stocks"][1]["selected_plan_id"] = None
        assert "HF-32" not in _kodlar(audit.audit(cfg, b, o, con))

    def test_HF32_temiz_ciktida_atesLENMEZ(self, cfg, con, temiz):
        b, o = temiz
        assert "HF-32" not in _kodlar(audit.audit(cfg, b, o, con))


class TestSureliVetoUyarisi:
    """W-04 — aktif veto varken plan seçmek. ENGELLEMEZ ama görünür olur."""

    def test_W04_aktif_veto_ustune_plan_secilirse_uyarir(self, cfg, con, temiz):
        b, o = temiz
        b["evren"][0]["aktif_vetolar"] = [
            {"veto_code": "haber_riski", "konuldu": "2026-07-28",
             "bitis": "2026-08-04", "kalan_islem_gunu": 3, "arac": "test",
             "gerekce": "x"}]
        o["stocks"][0]["action"] = "plan_sec"
        # ⚠ `_kodlar` YALNIZ sert hataları döner; W-xx uyarıları oraya girmez.
        bulgular = audit.audit(cfg, b, o, con)
        w = [f for f in bulgular if f.code == "W-04"]
        assert w, f"W-04 ateşlenmedi: {[f.code for f in bulgular]}"
        # SERT HATA DEĞİL: modelin fikrini değiştirme hakkı var, SESSİZCE
        # değiştirme hakkı yok.
        assert all(f.severity == audit.UYARI for f in w)
        assert "W-04" not in _kodlar(bulgular)

    def test_W04_vetosuz_isimde_atesLENMEZ(self, cfg, con, temiz):
        b, o = temiz
        assert not [f for f in audit.audit(cfg, b, o, con) if f.code == "W-04"]


class TestKapsam:
    def test_her_HF_kodu_GERCEKTEN_atesLENDI(self):
        """Bir kod hiç tetiklenemiyorsa o kontrol ÖLÜDÜR ve yanlış güven verir.

        ⚠ İlk sürüm bunu KAYNAK METNİNİ grepleyerek yapıyordu:
        `if "HF18" not in inspect.getsource(test_modulu)`. `def test_HF18_...`
        adı bu koşulu tek başına karşılıyordu; testin o kodu gerçekten
        tetiklediğini doğrulamıyordu. Nitekim HF-18 ve HF-19 aylarca yalnız
        HF-17 ile BİRLİKTE ateşlenebiliyordu ve bu test onları yeşil sayıyordu
        (2026-07-27 denetimi). Artık `audit.audit()`'in gerçekten döndürdüğü
        kodlar sayılır — totoloji değil, gözlem.
        """
        eksik = sorted(set(audit.all_codes()) - GORULEN_KODLAR)
        assert not eksik, (
            f"hiç tetiklenemeyen HF kodları: {eksik}. "
            f"Görülenler: {sorted(GORULEN_KODLAR)}")
