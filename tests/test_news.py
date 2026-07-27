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
    def test_tarih_UTC_ye_cevrilir(self):
        """'GG.AA.YYYY SS:DD:SS' İSTANBUL saatidir; kolon `published_utc`.

        Naif bırakmak, adı UTC içeriği yerel bir alan üretiyordu ve o alan
        `predictions.created_utc` (gerçek UTC) ile METİN olarak
        karşılaştırılınca 3 saatlik sessiz kayma veriyordu.
        """
        assert kap._parse_dt("25.07.2026 17:25:43") == "2026-07-25T14:25:43+00:00"

    def test_damgalar_ayni_uzunlukta_ve_siralanabilir(self):
        """Metin karşılaştırması kronolojik olsun diye biçim SABİT olmalı."""
        a = kap._parse_dt("25.07.2026 17:25:43")
        b = kap._parse_dt("25.07.2026 17:25:44")
        assert len(a) == len(b) and a < b

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
        assert news.last_seen(con) == "2026-07-22T07:00:00+00:00"
        assert news.last_seen(con, "THYAO") == "2026-07-22T07:00:00+00:00"

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

    def test_aralik_PARCA_PARCA_cekilir(self, cfg, monkeypatch):
        """⚠ REGRESYON KİLİDİ (2026-07-27, canlı API ölçümü).

        KAP geniş pencereyi SESSİZCE kırpıyor: 7 gün → 931 kayıt tam,
        21 gün → 1578 kayıt ama yalnız son 14 gün. Tek istekle 90 gün
        istemek 76 gününü hata vermeden kaybetmekti. Aralık dilimlenmeli.
        """
        from src import util
        pencereler = []

        def sahte(cfg, *, from_date, to_date):
            pencereler.append((util.parse_date(to_date)
                               - util.parse_date(from_date)).days + 1)
            return kap.FetchSonuc([])

        monkeypatch.setattr(kap, "fetch", sahte)
        kap.fetch_incremental(cfg, since=None, until="2026-07-25",
                              tam_gun=30, parca_gun=7)
        assert len(pencereler) >= 4, "tek istekte çekmiş — dilimleme yok"
        assert max(pencereler) <= 7, f"dilim çok geniş: {max(pencereler)}"

    def test_dilimler_araligi_TAM_kapsar(self, cfg, monkeypatch):
        from src import util
        gunler = set()

        def sahte(cfg, *, from_date, to_date):
            d, son = util.parse_date(from_date), util.parse_date(to_date)
            while d <= son:
                gunler.add(d.isoformat())
                d += __import__("datetime").timedelta(days=1)
            return kap.FetchSonuc([])

        monkeypatch.setattr(kap, "fetch", sahte)
        kap.fetch_incremental(cfg, since=None, until="2026-07-25",
                              tam_gun=20, parca_gun=7)
        assert len(gunler) == 21, f"aralıkta boşluk/örtüşme var: {len(gunler)}"
        assert "2026-07-05" in gunler and "2026-07-25" in gunler

    def test_dilim_DOYARSA_gorunur(self, cfg, monkeypatch):
        """Dilim kayıt tavanına dayanırsa sessiz geçilemez."""
        def sahte(cfg, *, from_date, to_date):
            return kap.FetchSonuc(
                [kap._normalize(_kayit(1, "THYAO", tarih="25.07.2026 10:00:00"))],
                kayitlar_ham=2000)          # tavana dayandı

        monkeypatch.setattr(kap, "fetch", sahte)
        s = kap.fetch_incremental(cfg, since=None, until="2026-07-25",
                                  tam_gun=14, parca_gun=7)
        assert s.atlanan_aralik is not None

    def test_BILDIRIMSIZ_gun_yanlis_alarm_URETMEZ(self, cfg, monkeypatch):
        """⚠ Dilimin ilk günü boşsa bu KIRPILMA DEĞİLDİR — tatil olabilir.
        İlk sürüm buna 'KIRPILDI' diyordu ve canlı koşuda yanlış alarm verdi
        (2026-05-05 istendi, 05-06 döndü — o gün gerçekten bildirim yoktu)."""
        def sahte(cfg, *, from_date, to_date):
            return kap.FetchSonuc(
                [kap._normalize(_kayit(1, "THYAO", tarih="25.07.2026 10:00:00"))],
                kayitlar_ham=5)             # tavandan ÇOK uzak

        monkeypatch.setattr(kap, "fetch", sahte)
        s = kap.fetch_incremental(cfg, since=None, until="2026-07-25",
                                  tam_gun=14, parca_gun=7)
        assert s.atlanan_aralik is None, "bildirimsiz gün kırpılma sanıldı"

    def test_tekrarlar_elenir(self, cfg, monkeypatch):
        """Dilimler örtüşmese de aynı id iki kez gelirse tekilleşmeli."""
        monkeypatch.setattr(kap, "fetch", lambda cfg, **kw: kap.FetchSonuc(
            [kap._normalize(_kayit(7, "THYAO", tarih="01.01.2026 10:00:00"))]))
        s = kap.fetch_incremental(cfg, since=None, until="2026-07-25",
                                  tam_gun=21, parca_gun=7)
        assert len(s.kayitlar) == 1


class TestDayaniklilik:
    def test_ag_hatasi_istisna_firlatmaz_ama_GIZLENMEZ(self, cfg, monkeypatch):
        """Bu modül ASLA istisna fırlatmaz — ama hatayı da YUTMAZ.

        'Bugün bildirim yok' ile 'KAP'a ulaşılamadı' aynı çıktıya düşerse
        sistem sessizce habersiz çalışmaya devam eder (LESSONS L-002).
        """
        def patla(*a, **k):
            raise ConnectionError("ağ yok")
        monkeypatch.setattr("requests.post", patla)
        s = kap.fetch(cfg, from_date="2026-07-01", to_date="2026-07-02")
        assert s.kayitlar == []
        assert s.ok is False and "ConnectionError" in s.hata

    def test_beklenmeyen_yanit_hata_olarak_isaretlenir(self, cfg, monkeypatch):
        class Sahte:
            status_code = 200
            def raise_for_status(self): pass
            def json(self): return {"hata": "beklenmedik yapı"}
        monkeypatch.setattr("requests.post", lambda *a, **k: Sahte())
        s = kap.fetch(cfg, from_date="2026-07-01", to_date="2026-07-02")
        assert s.kayitlar == [] and s.ok is False

    def test_basarili_cekimde_hata_none(self, cfg, monkeypatch):
        class Sahte:
            def raise_for_status(self): pass
            def json(self): return [_kayit(1, "THYAO")]
        monkeypatch.setattr("requests.post", lambda *a, **k: Sahte())
        s = kap.fetch(cfg, from_date="2026-07-01", to_date="2026-07-02")
        assert s.ok is True and len(s.kayitlar) == 1

    def test_hissesiz_bildirim_SAYILIR(self, cfg, monkeypatch):
        """`stockCodes` boş bildirim hiçbir hisseye bağlanamaz ve düşer —
        ama '0 satır yazıldı' ile 'hepsi hissesizdi' farklı olgulardır."""
        class Sahte:
            def raise_for_status(self): pass
            def json(self): return [_kayit(1, ""), _kayit(2, "THYAO")]
        monkeypatch.setattr("requests.post", lambda *a, **k: Sahte())
        s = kap.fetch(cfg, from_date="2026-07-01", to_date="2026-07-02")
        assert len(s.kayitlar) == 1 and s.tickersiz == 1

    def test_hata_news_sync_uzerinden_TASINIR(self, cfg, con, monkeypatch):
        def patla(*a, **k):
            raise ConnectionError("ağ yok")
        monkeypatch.setattr("requests.post", patla)
        r = news.sync(cfg, con)
        assert r["hata"] is not None, "hata sözlükte taşınmıyor — CLI göremez"

    def test_kap_kapaliyken_atlanir(self, cfg, con):
        c = {**cfg, "sources": {**cfg["sources"],
                                "kap": {**cfg["sources"]["kap"], "enabled": False}}}
        assert news.sync(c, con)["atlandi"] is True


class TestKaynakDurumu:
    """Boş `haberler` listesi iki ayrı olguyu temsil edebilir."""

    def test_hic_tarama_yoksa_ok_false(self, con):
        d = news.kaynak_durumu(con, "2026-07-24")
        assert d["ok"] is False and "hiç çalışmadı" in d["not"]

    def test_taze_tarama_ok_true(self, con):
        news.store(con, [kap._normalize(_kayit(1, "THYAO",
                                               tarih="23.07.2026 10:00:00"))])
        assert news.kaynak_durumu(con, "2026-07-24")["ok"] is True

    def test_bayat_tarama_ok_false(self, con):
        news.store(con, [kap._normalize(_kayit(1, "THYAO",
                                               tarih="01.07.2026 10:00:00"))])
        d = news.kaynak_durumu(con, "2026-07-24")
        assert d["ok"] is False and d["gecikme_gun"] == 23


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


class TestPaketTaramaPenceresi:
    """⚠ REGRESYON KİLİDİ (2026-07-27 denetimi) — EN PAHALI HATA.

    `llm_io.build_bundle` haber penceresini `MAX(created_utc)` ile belirliyordu.
    `created_utc` kaydın DİSKE YAZILDIĞI duvar saatidir. `bist replay`
    2024-2026'nın tamamını tek seferde yazınca her hissenin `created_utc`'si
    "şimdi" oluyor ve `published_utc > since` HİÇBİR haberi geçirmiyordu.
    Ölçüldü: bildirimi olan 14 hissenin 8'inde 47 gerçek KAP bildirimi
    sessizce gizlenmişti — ADR #008 sonrası sistemin kalan ANA ÜRÜNÜ.
    """

    def _hazirla(self, cfg, con):
        from src import journal
        from tests.conftest import add_plan, add_universe
        add_universe(con, "THYAO")
        add_plan(con, "THYAO-p", ticker="THYAO", asof="2026-07-10")
        run_id = journal.create_run(cfg, con, asof="2026-07-10", tool="replay",
                                    bundle_sha="s")
        journal.record(
            cfg, con, run_id=run_id, asof="2026-07-10", ticker="THYAO",
            analist={"signal": "buy", "action": "plan_sec", "confidence": "orta",
                     "thesis": "t", "counter_scenario": "c", "key_risk": "k",
                     "falsifier": "f"},
            plan={"plan_id": "THYAO-p"},
            faktor={"score": 1.0, "rank": 1, "pct": 90.0, "weights_hash": "h"},
            referans={"close": 100.0})
        # Analiz gününden SONRA yayımlanmış gerçek bir bildirim
        news.store(con, [kap._normalize(_kayit(1, "THYAO",
                                               tarih="15.07.2026 10:00:00"))])
        return run_id

    def test_since_ASOF_gununden_turetilir(self, cfg, con):
        from src import db, util
        self._hazirla(cfg, con)
        tz = cfg["takvim"]["timezone"]
        son = {r["ticker"]: util.local_day_end_utc_iso(r["son"], tz)
               for r in db.fetch_all(
                   con, "SELECT ticker, MAX(asof) son FROM predictions "
                        "WHERE asof < ? GROUP BY ticker", ("2026-07-24",))}
        assert son["THYAO"].startswith("2026-07-10T")

    def test_replay_sonrasi_haber_GIZLENMEZ(self, cfg, con):
        """created_utc kullanılsaydı bu liste boş dönerdi."""
        from src import db, util
        self._hazirla(cfg, con)
        tz = cfg["takvim"]["timezone"]
        row = db.fetch_one(con, "SELECT MAX(asof) son, MAX(created_utc) c "
                                "FROM predictions WHERE ticker='THYAO'")
        # created_utc "şimdi"dir ve bildirimden SONRADIR — eski hatanın kanıtı
        assert row["c"] > "2026-07-15T07:00:00+00:00"
        assert news.bundle_view(con, "THYAO", since=row["c"]) == []
        # asof tabanlı pencere ise bildirimi GÖSTERİR
        dogru = util.local_day_end_utc_iso(row["son"], tz)
        assert len(news.bundle_view(con, "THYAO", since=dogru)) == 1


class TestTamCekimPenceresi:
    """Tam çekim derinliği config'ten okunur — koda gömülü sabit değil."""

    def test_config_degeri_kullanilir(self, cfg, monkeypatch):
        from src import util
        yakalanan = {}

        def sahte(cfg, *, from_date, to_date):
            yakalanan["toplam"] = yakalanan.get("toplam", 0) + (
                util.parse_date(to_date) - util.parse_date(from_date)).days + 1
            return kap.FetchSonuc([])

        monkeypatch.setattr(kap, "fetch", sahte)
        kap.fetch_incremental(cfg, since=None, until="2026-07-25")
        assert yakalanan["toplam"] == cfg["sources"]["kap"]["tam_cekim_gun"] + 1

    def test_acik_gun_config_i_ezer(self, cfg, monkeypatch):
        from src import util
        yakalanan = {}

        def sahte(cfg, *, from_date, to_date):
            yakalanan["toplam"] = yakalanan.get("toplam", 0) + (
                util.parse_date(to_date) - util.parse_date(from_date)).days + 1
            return kap.FetchSonuc([])

        monkeypatch.setattr(kap, "fetch", sahte)
        kap.fetch_incremental(cfg, since=None, until="2026-07-25", tam_gun=10)
        assert yakalanan["toplam"] == 11


class TestUyarlanabilirBolme:
    """⚠ Sabit dilim genişliği KIRILGAN: bildirim hacmi mevsimlik. Temmuz'da
    7 gün 931 kayıt, Mayıs'ta (bilanço sezonu) aynı 7 gün tavanı aşıyor.
    Doymayı gözleyip TEPKİ vermek, sabit bir sayı tahmin etmekten güvenli."""

    def test_doyan_dilim_IKIYE_BOLUNUR(self, cfg, monkeypatch):
        istekler = []

        def sahte(cfg, *, from_date, to_date):
            istekler.append((from_date, to_date))
            gun = (util.parse_date(to_date) - util.parse_date(from_date)).days + 1
            # 3 günden geniş her dilim "doyuyor" gibi davransın
            if gun > 3:
                return kap.FetchSonuc(
                    [kap._normalize(_kayit(1, "THYAO", tarih="25.07.2026 10:00:00"))],
                    kayitlar_ham=5000)
            return kap.FetchSonuc([], kayitlar_ham=1)

        from src import util
        monkeypatch.setattr(kap, "fetch", sahte)
        s = kap.fetch_incremental(cfg, since=None, until="2026-07-25",
                                  tam_gun=13, parca_gun=7)
        genislikler = [(util.parse_date(b) - util.parse_date(a)).days + 1
                       for a, b in istekler]
        assert min(genislikler) <= 3, "doyan dilim hiç bölünmemiş"
        assert s.atlanan_aralik is None, "bölme başarılı olduğu halde kayıp bildirildi"

    def test_tek_gun_bile_doyuyorsa_ITIRAF_EDILIR(self, cfg, monkeypatch):
        """Bölmenin bir sınırı var; aşılırsa SESSİZ KALINMAZ."""
        monkeypatch.setattr(kap, "fetch", lambda cfg, **kw: kap.FetchSonuc(
            [kap._normalize(_kayit(1, "THYAO", tarih="25.07.2026 10:00:00"))],
            kayitlar_ham=99999))
        s = kap.fetch_incremental(cfg, since=None, until="2026-07-25",
                                  tam_gun=6, parca_gun=7)
        assert s.atlanan_aralik is not None
