"""Haber katmanı testleri.

Bu katmanın sözleşmesi: **haber sayıya çevrilmez.** `importance` bir
heuristiktir ve hiçbir hesaba girmez; testler bunu da sabitler.
"""

from __future__ import annotations

import pytest

from src import audit, news
from src.sources import kap
from tests.conftest import add_universe


def _kayit(idx: int, tickers: str, *, konu="Özel Durum Açıklaması",
           ozet=None, kategori="ODA", tarih="20.07.2026 14:30:00") -> dict:
    return {"disclosureIndex": idx, "stockCodes": tickers, "publishDate": tarih,
            "subject": konu, "summary": ozet, "disclosureCategory": kategori,
            "kapTitle": "TEST A.Ş.", "relatedStocks": None}


class TestAyristirma:
    def test_tarih_ISO_ye_cevrilir(self):
        """'GG.AA.YYYY SS:DD:SS' sıralanabilir olmalı — ham biçimde ORDER BY
        kronolojik DEĞİLDİR."""
        assert kap._parse_dt("25.07.2026 17:25:43") == "2026-07-25T17:25:43"

    def test_bozuk_tarih_none(self):
        assert kap._parse_dt("saçma") is None
        assert kap._parse_dt(None) is None

    def test_stockCodes_kullanilir_relatedStocks_degil(self):
        """ÖLÇÜLDÜ: `relatedStocks` çoğunlukla null; `stockCodes` güvenilir."""
        n = kap._normalize(_kayit(1, "THYAO"))
        assert n["tickers"] == ["THYAO"]

    def test_coklu_ticker_ayristirilir(self):
        n = kap._normalize(_kayit(1, "KCHOL, TUPRS"))
        assert set(n["tickers"]) == {"KCHOL", "TUPRS"}

    def test_id_ve_url(self):
        n = kap._normalize(_kayit(1636749, "THYAO"))
        assert n["disclosure_id"] == "kap-1636749"
        assert n["url"].endswith("/1636749")

    def test_tier_daima_1(self):
        """KAP resmî beyandır — tek tier-1 kaynak."""
        assert kap._normalize(_kayit(1, "THYAO"))["tier"] == 1

    @pytest.mark.parametrize("bozuk", [
        {"disclosureIndex": None, "publishDate": "20.07.2026 10:00:00"},
        {"disclosureIndex": 1, "publishDate": None},
    ])
    def test_eksik_alanli_kayit_atlanir(self, bozuk):
        assert kap._normalize(bozuk) is None


class TestOnem:
    """`importance` HEURİSTİKTİR — sıralama/gösterim içindir, hesaba girmez."""

    @pytest.mark.parametrize("konu,beklenen", [
        ("Bedelsiz Sermaye Artırımı", "yuksek"),
        ("Kâr Payı Dağıtımı", "yuksek"),
        ("Pay Bazında Devre Kesici Bildirimi", "dusuk"),
        ("Borsada İşlem Gören Tipe Dönüşüm Duyurusu", "dusuk"),
        ("Özel Durum Açıklaması (Genel)", "orta"),
    ])
    def test_siniflandirma(self, konu, beklenen):
        assert kap.importance(konu, None, "ODA") == beklenen

    def test_finansal_rapor_yuksek(self):
        assert kap.importance("Bir şey", None, "FR") == "yuksek"


class TestSaklama:
    def test_coklu_ticker_coklu_satir(self, con):
        """Bir bildirim birden çok hisseye aitse HER BİRİ için satır yazılır."""
        n = kap._normalize(_kayit(1, "KCHOL, TUPRS"))
        r = news.store(con, [n])
        assert r["yazilan"] == 2
        assert len(news.for_ticker(con, "KCHOL")) == 1
        assert len(news.for_ticker(con, "TUPRS")) == 1

    def test_evren_disi_filtrelenir(self, con):
        n = kap._normalize(_kayit(1, "THYAO, BILINMEYEN"))
        news.store(con, [n], tickers={"THYAO"})
        assert len(news.for_ticker(con, "BILINMEYEN")) == 0

    def test_tekrar_yazma_cogaltmaz(self, con):
        """Aynı bildirimi üst üste çekmek ZARARSIZ olmalı — artımlı çekim
        güvenlik payıyla geriye taşar."""
        n = kap._normalize(_kayit(1, "THYAO"))
        news.store(con, [n])
        news.store(con, [n])
        assert len(news.for_ticker(con, "THYAO")) == 1

    def test_last_seen(self, con):
        news.store(con, [kap._normalize(_kayit(1, "THYAO",
                                               tarih="20.07.2026 10:00:00")),
                         kap._normalize(_kayit(2, "THYAO",
                                               tarih="22.07.2026 10:00:00"))])
        assert news.last_seen(con) == "2026-07-22T10:00:00"
        assert news.last_seen(con, "THYAO") == "2026-07-22T10:00:00"

    def test_bos_veride_last_seen_none(self, con):
        assert news.last_seen(con) is None


class TestArtimli:
    def test_since_sonrasi_filtrelenir(self, con):
        """'Aynı haberler tekrar taranmasın' kuralının paket tarafı."""
        news.store(con, [kap._normalize(_kayit(1, "THYAO",
                                               tarih="20.07.2026 10:00:00")),
                         kap._normalize(_kayit(2, "THYAO",
                                               tarih="24.07.2026 10:00:00"))])
        yeni = news.for_ticker(con, "THYAO", since="2026-07-22T00:00:00")
        assert len(yeni) == 1
        assert yeni[0]["disclosure_id"] == "kap-2"

    def test_pencere_kirpilir(self, cfg, monkeypatch):
        """Çok eski `since` ile devasa pencere istenmemeli."""
        yakalanan = {}

        def sahte(cfg, *, from_date, to_date):
            yakalanan["gun"] = (util.parse_date(to_date)
                                - util.parse_date(from_date)).days
            return []

        from src import util
        monkeypatch.setattr(kap, "fetch", sahte)
        kap.fetch_incremental(cfg, since="2000-01-01", until="2026-07-25",
                              max_days=90)
        assert yakalanan["gun"] <= 90


class TestDayaniklilik:
    def test_ag_hatasi_bos_liste(self, cfg, monkeypatch):
        """Bu modül ASLA istisna fırlatmaz — haber yoksa analiz yine yapılır."""
        def patla(*a, **k):
            raise ConnectionError("ağ yok")
        monkeypatch.setattr("requests.post", patla)
        assert kap.fetch(cfg, from_date="2026-07-01", to_date="2026-07-02") == []

    def test_beklenmeyen_yanit_bos_liste(self, cfg, monkeypatch):
        class Sahte:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return {"hata": "beklenmedik yapı"}
        monkeypatch.setattr("requests.post", lambda *a, **k: Sahte())
        assert kap.fetch(cfg, from_date="2026-07-01", to_date="2026-07-02") == []

    def test_kap_kapaliyken_atlanir(self, cfg, con):
        c = {**cfg, "sources": {**cfg["sources"],
                                "kap": {**cfg["sources"]["kap"], "enabled": False}}}
        assert news.sync(c, con)["atlandi"] is True


class TestDenetimBaglantisi:
    def test_bundle_id_HF28_ile_uyumlu(self, cfg, con):
        """Pakete giren `id`, HF-28'in doğruladığı referanstır. Biçim
        değişirse analistin gerçek haberi bile 'uydurma' sayılırdı."""
        add_universe(con, "THYAO")
        news.store(con, [kap._normalize(_kayit(42, "THYAO"))])
        gorunum = news.bundle_view(con, "THYAO")
        assert gorunum and gorunum[0]["id"] == "kap-42"

        bundle = {"asof": "2026-07-24", "bundle_sha": "x",
                  "evren": [{"ticker": "THYAO", "haberler": gorunum}],
                  "rejim": {"etiket": "neutral", "pozisyon_politikasi": {}},
                  "izin_verilen_degerler": {**cfg["llm"]["enums"],
                                            "plan_ids": {"THYAO": []}}}
        out = {"schema_version": "bist_llm_v1", "asof": "2026-07-24",
               "bundle_sha": "x", "tool": "claude-code",
               "market_view": {"regime_agreement": "katiliyorum",
                               "portfolio_action": "koru", "regime_note": "n"},
               "stocks": [{"ticker": "THYAO", "signal": "hold", "action": "izle",
                           "selected_plan_id": None, "veto_code": None,
                           "confidence": "orta",
                           "thesis": "T" * 90, "counter_scenario": "K" * 90,
                           "key_risk": "R" * 90, "falsifier": "F" * 90,
                           "news_refs": ["kap-42"], "news_reading": "Yorum."}],
               "not_covered": [], "analyst_notes": ""}
        kodlar = {f.code for f in audit.hard_fails(audit.audit(cfg, bundle, out, con))}
        assert "HF-28" not in kodlar, "gerçek haber id'si uydurma sayıldı"

    def test_uydurma_id_yakalanir(self, cfg, con):
        add_universe(con, "THYAO")
        bundle = {"asof": "2026-07-24", "bundle_sha": "x",
                  "evren": [{"ticker": "THYAO", "haberler": []}],
                  "rejim": {"etiket": "neutral", "pozisyon_politikasi": {}},
                  "izin_verilen_degerler": {**cfg["llm"]["enums"],
                                            "plan_ids": {"THYAO": []}}}
        out = {"schema_version": "bist_llm_v1", "asof": "2026-07-24",
               "bundle_sha": "x", "tool": "claude-code",
               "market_view": {"regime_agreement": "katiliyorum",
                               "portfolio_action": "koru", "regime_note": "n"},
               "stocks": [{"ticker": "THYAO", "signal": "hold", "action": "izle",
                           "selected_plan_id": None, "veto_code": None,
                           "confidence": "orta",
                           "thesis": "T" * 90, "counter_scenario": "K" * 90,
                           "key_risk": "R" * 90, "falsifier": "F" * 90,
                           "news_refs": ["kap-UYDURMA"], "news_reading": "Yorum."}],
               "not_covered": [], "analyst_notes": ""}
        kodlar = {f.code for f in audit.hard_fails(audit.audit(cfg, bundle, out, con))}
        assert "HF-28" in kodlar


class TestSayiyaCevrilmez:
    def test_onem_sadece_etiket(self, con):
        """Haber SAYIYA çevrilmez: `importance` bir string etikettir, skor değil.
        Sayısal bir duygu alanı eklenirse bu test kırılmalı."""
        news.store(con, [kap._normalize(_kayit(1, "THYAO"))])
        kayit = news.for_ticker(con, "THYAO")[0]
        assert isinstance(kayit["importance"], str)
        sayisal = [k for k, v in kayit.items()
                   if isinstance(v, (int, float)) and k not in ("tier",)]
        assert not sayisal, f"habere sayısal alan sızmış: {sayisal}"
