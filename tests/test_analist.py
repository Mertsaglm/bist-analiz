"""Otonom analist zinciri — sözleşme + mekanizma testleri (ADR #013).

AĞ YOK: her HTTP çağrısı monkeypatch'lenir. Bir testin gerçekten ağa çıkması
suite'i sağlayıcının o anki durumuna bağlar — ve o sağlayıcı bir gün cevap
vermediğinde kırmızı olan şey bizim kodumuz sanılır.
"""

from __future__ import annotations

import json

import pytest

from src import analist, util


# ============================================================ SÖZLEŞME
class TestZincirSozlesmesi:
    def test_istenen_model_sirasi_birebir_korunur(self, real_cfg):
        """2026-09-24: Model sırası değişirken eski/yanlış kimlikler geri gelmesin."""
        assert real_cfg["llm"]["zincir"] == [
            "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash",
            "gemini-3.1-pro-preview", "gpt-6-luna", "gpt-5.6-luna",
        ]
        # Eski analizlerin kaynak etiketleri silinirse geçmiş karne okunamaz.
        assert {"gemini-3.5-flash", "gemini-2.5-pro", "gpt-5-mini"} <= set(
            real_cfg["llm"]["enums"]["tool"])

    def test_zincir_modelleri_enum_icinde(self, real_cfg):
        """Zincirdeki her model `llm.enums.tool` içinde OLMALI.

        ⚠ NE OLURDU: `tool` enum'u HF denetiminde kontrol edilmiyor ama
        `journal.create_run` bu değeri yazıyor ve `bist degerlendir --tool`
        onunla filtreliyor. Zincire enum'da olmayan bir model eklenirse
        otonom turlar journal'a "tanınmayan araç" olarak girer ve ölçümde
        sessizce kaybolur. İkisi TEK YERDEN değil iki yerden tanımlandığı
        için ayrışma kaçınılmaz — bu test onu görünür kılar.
        """
        zincir = real_cfg["llm"]["zincir"]
        izinli = set(real_cfg["llm"]["enums"]["tool"])
        eksik = [m for m in zincir if m not in izinli]
        assert not eksik, (
            f"Zincirde olup `llm.enums.tool`'da olmayan model: {eksik} — "
            f"bu modellerin turları ölçümde kaybolur")

    def test_gemini_openaiden_once(self, real_cfg):
        """2026-09-24 sırası: dört Gemini halkasından sonra iki OpenAI halkası."""
        zincir = real_cfg["llm"]["zincir"]
        saglayicilar = [analist.provider_of(m) for m in zincir]
        ilk_openai = next((i for i, p in enumerate(saglayicilar)
                           if p == "openai"), len(saglayicilar))
        son_google = max((i for i, p in enumerate(saglayicilar)
                          if p == "google"), default=-1)
        assert son_google < ilk_openai, (
            f"OpenAI modeli Gemini'den ÖNCE geliyor: {zincir} — "
            f"kullanıcının belirlediği sağlayıcı sırası değişmiş")

    def test_zincir_bos_degil_ve_tekrarsiz(self, real_cfg):
        zincir = real_cfg["llm"]["zincir"]
        assert zincir, "zincir boş — otonom analist hiç çalışamaz"
        assert len(zincir) == len(set(zincir)), f"zincirde tekrar var: {zincir}"

    def test_dusunme_ayarlari_tanimli(self, real_cfg):
        """Her iki sağlayıcı için düşünme seviyesi tanımlı olmalı."""
        d = real_cfg["llm"]["zincir_dusunme"]
        assert d.get("gemini") and d.get("openai")


# ============================================================ MEKANİZMA
class TestSaglayiciOzellikleri:
    def test_provider_ayrimi(self):
        assert analist.provider_of("gemini-3.8-flash") == "google"
        assert analist.provider_of("gemini-3.7-flash") == "google"
        assert analist.provider_of("gemini-3.5-flash") == "google"
        assert analist.provider_of("gemini-2.5-pro") == "google"
        assert analist.provider_of("gpt-5-mini") == "openai"
        assert analist.provider_of("gpt-5.6-luna") == "openai"
        assert analist.provider_of("gpt-6-luna") == "openai"

    def test_gemini_3_dusunme_destekler_25_DESTEKLEMEZ(self):
        """⚠ NE OLURDU: gemini-2.5-* `thinkingLevel` alanını TANIMAZ ve
        gönderilirse istek 400 döner (inkline'da yaşandı). Eski model
        kayıtlarını yeniden koşarken bu davranış korunmalıdır."""
        assert analist._dusunme_destekler("gemini-3.8-flash")
        assert analist._dusunme_destekler("gemini-3.7-flash")
        assert analist._dusunme_destekler("gemini-3.5-flash")
        assert analist._dusunme_destekler("gemini-3.6-flash")
        assert analist._dusunme_destekler("gemini-3.1-pro-preview")
        assert not analist._dusunme_destekler("gemini-2.5-pro")
        assert not analist._dusunme_destekler("gemini-2.5-flash")

    def test_gemini25_istegine_thinking_KONMAZ(self, cfg, monkeypatch):
        """Gövde düzeyinde doğrula — fonksiyonun döndürdüğü bool'a değil,
        GERÇEKTEN giden isteğe bak (yorum bir iddiadır, §12)."""
        yakalanan = {}

        class SahteYanit:
            status_code = 200

            def raise_for_status(self): pass

            def json(self):
                return {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}

        def sahte_post(url, headers=None, json=None, timeout=None):
            yakalanan["govde"] = json
            return SahteYanit()

        monkeypatch.setenv("GEMINI_API_KEY", "test")
        monkeypatch.setattr(analist.requests, "post", sahte_post)

        analist._gemini_cagir(cfg, "gemini-2.5-pro", "merhaba", 30)
        assert "thinkingConfig" not in yakalanan["govde"]["generationConfig"]

        analist._gemini_cagir(cfg, "gemini-3.5-flash", "merhaba", 30)
        assert yakalanan["govde"]["generationConfig"]["thinkingConfig"][
            "thinkingLevel"] == cfg["llm"]["zincir_dusunme"]["gemini"]

    def test_cikti_tavani_HER_IKI_saglayiciya_da_gonderilir(self, cfg, monkeypatch):
        """⚠ NE OLMUŞTU (2026-08-01, ilk otonom tur): tavan gönderilmiyordu,
        sağlayıcının varsayılanına düşülüyordu ve gemini-3.5-flash'ın JSON
        çıktısı 17.000 karakterde SESSİZCE kesildi. Hata "Expecting ','
        delimiter" diye göründü — yani biçim hatası gibi. Zincir gereksiz
        yere bir sonraki modele düştü; en iyi halka bir kaza yüzünden kayboldu.
        """
        yakalanan = {}

        class SahteGemini:
            def raise_for_status(self): pass

            def json(self):
                return {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]}

        class SahteOpenAI:
            def raise_for_status(self): pass

            def json(self):
                return {"choices": [{"message": {"content": "{}"}}]}

        tavan = int(cfg["llm"]["maks_cikti_token"])
        monkeypatch.setenv("GEMINI_API_KEY", "t")
        monkeypatch.setenv("OPENAI_API_KEY", "t")

        monkeypatch.setattr(analist.requests, "post",
                            lambda u, headers=None, json=None, timeout=None:
                            yakalanan.__setitem__("g", json) or SahteGemini())
        analist._gemini_cagir(cfg, "gemini-3.5-flash", "x", 30)
        assert yakalanan["g"]["generationConfig"]["maxOutputTokens"] == tavan

        monkeypatch.setattr(analist.requests, "post",
                            lambda u, headers=None, json=None, timeout=None:
                            yakalanan.__setitem__("o", json) or SahteOpenAI())
        analist._openai_cagir(cfg, "gpt-5-mini", "x", 30)
        assert yakalanan["o"]["max_completion_tokens"] == tavan

    @pytest.mark.parametrize("model", ["gpt-6-luna", "gpt-5.6-luna"])
    def test_openai_akil_yurutme_modelinde_reasoning_effort(self, cfg, monkeypatch, model):
        yakalanan = {}

        class SahteYanit:
            def raise_for_status(self): pass

            def json(self):
                return {"choices": [{"message": {"content": "{}"}}]}

        def sahte_post(url, headers=None, json=None, timeout=None):
            yakalanan["govde"] = json
            return SahteYanit()

        monkeypatch.setenv("OPENAI_API_KEY", "test")
        monkeypatch.setattr(analist.requests, "post", sahte_post)

        analist._openai_cagir(cfg, model, "merhaba", 30)
        assert yakalanan["govde"]["model"] == model
        assert yakalanan["govde"]["reasoning_effort"] == \
            cfg["llm"]["zincir_dusunme"]["openai"]
        # Her iki Luna sürümüne akıl yürütme ayarı gitmeli; temperature gönderilmez.
        assert "temperature" not in yakalanan["govde"]


class TestZincirEleme:
    def test_anahtarlar_varsa_istenen_sira_korunur(self, real_cfg, monkeypatch):
        """Gerçek çağrı zinciri YAML sırasını aynen kullanmalı."""
        monkeypatch.setattr(analist, "_anahtar_var", lambda provider: True)
        assert analist.zincir(real_cfg) == real_cfg["llm"]["zincir"]

    def test_anahtarsiz_saglayici_zincirden_DUSER(self, cfg, monkeypatch):
        """Anahtarı olmayan sağlayıcının modelleri denenmez.

        Aksi halde her koşuda 4 başarısız istek atılır ve gerçek hata
        (anahtar yok) 401 gürültüsünün altında kaybolur.
        """
        monkeypatch.setenv("GEMINI_API_KEY", "test")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # util.env `.env` dosyasını da okur; testte dosyayı devre dışı bırak
        monkeypatch.setattr(util, "load_env", lambda *a, **k: None)

        z = analist.zincir(cfg)
        assert z, "Gemini anahtarı varken zincir boş kalmamalı"
        assert all(analist.provider_of(m) == "google" for m in z)

    def test_hic_anahtar_yoksa_ZincirBos(self, cfg, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setattr(util, "load_env", lambda *a, **k: None)
        assert analist.zincir(cfg) == []


class TestJsonAyiklama:
    def test_duz_json(self):
        assert analist._json_ayikla('{"a": 1}') == {"a": 1}

    def test_markdown_citli_json(self):
        """Model `responseMimeType` istense de çıktıyı ```json ile sarabilir."""
        ham = '```json\n{"a": 1}\n```'
        assert analist._json_ayikla(ham) == {"a": 1}

    def test_onsozlu_json(self):
        ham = 'İşte analiz:\n{"a": 1}\nUmarım yardımcı olur.'
        assert analist._json_ayikla(ham) == {"a": 1}

    def test_json_yoksa_hata(self):
        with pytest.raises(ValueError):
            analist._json_ayikla("hiç JSON yok")


class TestCalistirZinciri:
    """`calistir` — zincirin asıl davranışı. Sahte paket + sahte HTTP."""

    @staticmethod
    def _paket_kur(cfg, asof="2026-07-29"):
        """Minimal ama GERÇEK yapılı paket: denetim bunun üstünde koşacak."""
        bundle = {
            "bundle_version": cfg["llm"]["bundle_version"],
            "asof": asof,
            "bundle_sha": "sha-test",
            "uyari": "test",
            "rejim": {"etiket": "neutral",
                      "pozisyon_politikasi": {"nakit_pct": 40.0,
                                              "maks_pozisyon": 5,
                                              "sektor_basi_maks": 2}},
            "evren": [{"ticker": "THYAO", "sektor": "ulasim",
                       "fiyat": {"kapanis": 300.0}, "gostergeler": {"atr14": 9.0},
                       "faktorler": {"skor": 1.0, "sira": 1, "yuzdelik": 90.0,
                                     "kapilar": {"uygun": True, "nedenler": []}},
                       "veri_kalitesi": {"ok": True, "uyarilar": []},
                       "plan_menusu": [], "plan_yok_nedeni": "test",
                       "acik_tahminler": [], "haberler": []}],
            "izin_verilen_degerler": {**cfg["llm"]["enums"], "plan_ids": {}},
        }
        d = util.resolve(f"{cfg['paths']['llm_in_dir']}/{asof}")
        d.mkdir(parents=True, exist_ok=True)
        util.write_json(d / "bundle.json", bundle)
        (d / "prompt.md").write_text("görev", encoding="utf-8")
        (d / "context.md").write_text("paket", encoding="utf-8")
        return bundle

    @staticmethod
    def _gecerli_cikti(bundle, asof="2026-07-29", tool="yanlis-arac"):
        """HF denetiminden GEÇEN minimal çıktı."""
        uzun = ("Bu isim uzun vadeli ortalamasının altında olduğu için trend "
                "kapısından geçemiyor ve sıralamada yeri hesaplanmıyor bugün.")
        return {
            "schema_version": "bist_llm_v1", "asof": asof,
            "bundle_sha": bundle["bundle_sha"], "tool": tool,
            "market_view": {"regime_agreement": "katiliyorum",
                            "regime_note": "test",
                            "portfolio_action": "koru"},
            "stocks": [{"ticker": "THYAO", "signal": "hold", "action": "izle",
                        "selected_plan_id": None, "veto_code": None,
                        "confidence": "orta", "thesis": uzun,
                        "counter_scenario": uzun + " Karşı senaryo tarafı.",
                        "key_risk": uzun + " Risk tarafı ayrıca şu.",
                        "falsifier": "Uzun vadeli ortalamanın üzerinde bir günlük "
                                     "kapanış gelirse bu değerlendirme düşer.",
                        "news_refs": [], "news_reading": None}],
            "not_covered": [], "analyst_notes": "",
        }

    def test_ilk_model_temizse_digerleri_DENENMEZ(self, cfg, con, monkeypatch):
        bundle = self._paket_kur(cfg)
        cagrilan = []

        def sahte(cfg_, model_id, prompt):
            cagrilan.append(model_id)
            return json.dumps(self._gecerli_cikti(bundle))

        monkeypatch.setattr(analist, "_cagir", sahte)
        r = analist.calistir(cfg, con, "2026-07-29",
                             modeller=["model-a", "model-b", "model-c"])
        assert cagrilan == ["model-a"]
        assert r["model"] == "model-a"

    def test_tool_alanini_KOD_yazar(self, cfg, con, monkeypatch):
        """⚠ NE OLURDU: model `tool` alanına iskeletteki `"<araç>"` yer
        tutucusunu ya da uydurma bir ad yazarsa `bist degerlendir --tool X`
        o turu bulamaz; ölçüm sessizce eksik kalır. Modelin kendi kimliği
        hakkındaki beyanına GÜVENİLMEZ."""
        bundle = self._paket_kur(cfg)
        monkeypatch.setattr(
            analist, "_cagir",
            lambda c, m, p: json.dumps(
                self._gecerli_cikti(bundle, tool="tamamen-uydurma")))

        r = analist.calistir(cfg, con, "2026-07-29", modeller=["gemini-3.5-flash"])
        assert r["out"]["tool"] == "gemini-3.5-flash"
        # Diske yazılan dosyada da düzeltilmiş olmalı
        yazilan = util.read_json(f"{cfg['paths']['llm_out_dir']}/2026-07-29/analysis.json")
        assert yazilan["tool"] == "gemini-3.5-flash"

    def test_denetimden_gecemeyen_model_ATLANIR(self, cfg, con, monkeypatch):
        """HF denetimi zincirin bir halkasıdır: geçerli JSON yetmez.

        Burada 1. model UYDURMA bir plan_id seçiyor (HF-12) — şema açısından
        kusursuz, kural açısından reddedilir. Zincir 2. modele geçmeli.
        """
        bundle = self._paket_kur(cfg)

        def sahte(cfg_, model_id, prompt):
            out = self._gecerli_cikti(bundle)
            if model_id == "kotu-model":
                out["stocks"][0]["action"] = "plan_sec"
                out["stocks"][0]["selected_plan_id"] = "UYDURMA-PLAN-1"
            return json.dumps(out)

        monkeypatch.setattr(analist, "_cagir", sahte)
        r = analist.calistir(cfg, con, "2026-07-29",
                             modeller=["kotu-model", "iyi-model"])

        assert r["model"] == "iyi-model"
        assert r["denemeler"][0]["sonuc"] == "hata"
        assert "denetim" in r["denemeler"][0]["detay"]

    def test_denetimden_gecemeyen_cikti_DISKE_YAZILMAZ(self, cfg, con, monkeypatch):
        """⚠ Sert hatalı çıktı `analysis.json`'a yazılırsa, sonradan elle
        koşulan `bist denetle` onu bulur ve "bir analiz var" sanılır."""
        bundle = self._paket_kur(cfg)
        monkeypatch.setattr(
            analist, "_cagir",
            lambda c, m, p: json.dumps({"schema_version": "YANLIS"}))

        with pytest.raises(analist.TumModellerDustu):
            analist.calistir(cfg, con, "2026-07-29", modeller=["a", "b"])

        p = util.resolve(f"{cfg['paths']['llm_out_dir']}/2026-07-29/analysis.json")
        assert not p.exists(), "sert hatalı çıktı diske yazılmış"

    def test_ag_hatasi_da_zinciri_ILERLETIR(self, cfg, con, monkeypatch):
        """Hata SINIFI fark etmez: kota, 5xx, zaman aşımı, JSON — hepsi aynı."""
        bundle = self._paket_kur(cfg)

        def sahte(cfg_, model_id, prompt):
            if model_id == "dusen":
                raise analist.requests.exceptions.Timeout("zaman aşımı")
            return json.dumps(self._gecerli_cikti(bundle))

        monkeypatch.setattr(analist, "_cagir", sahte)
        r = analist.calistir(cfg, con, "2026-07-29", modeller=["dusen", "saglam"])
        assert r["model"] == "saglam"

    def test_hepsi_dusunce_TumModellerDustu(self, cfg, con, monkeypatch):
        self._paket_kur(cfg)
        monkeypatch.setattr(
            analist, "_cagir",
            lambda c, m, p: (_ for _ in ()).throw(RuntimeError("429 kota")))

        with pytest.raises(analist.TumModellerDustu):
            analist.calistir(cfg, con, "2026-07-29", modeller=["a", "b"])

    def test_ara_halkada_tekrar_YOK_son_halkada_VAR(self, cfg, con, monkeypatch):
        """Ara halkada ısrar zaman kaybı; asıl yedekleme zincirin kendisi."""
        self._paket_kur(cfg)
        sayac: dict[str, int] = {}

        def sahte(cfg_, model_id, prompt):
            sayac[model_id] = sayac.get(model_id, 0) + 1
            raise RuntimeError("hep düşer")

        monkeypatch.setattr(analist, "_cagir", sahte)
        cfg["llm"]["son_halka_tekrar"] = 2

        with pytest.raises(analist.TumModellerDustu):
            analist.calistir(cfg, con, "2026-07-29", modeller=["ilk", "son"])

        assert sayac["ilk"] == 1, "ara halka tekrar denenmiş"
        assert sayac["son"] == 3, "son halkada 1 + 2 tekrar bekleniyordu"

    def test_paket_yoksa_anlamli_hata(self, cfg, con, monkeypatch):
        monkeypatch.setattr(analist, "_cagir", lambda c, m, p: "{}")
        with pytest.raises(FileNotFoundError):
            analist.calistir(cfg, con, "1999-01-01", modeller=["a"])
