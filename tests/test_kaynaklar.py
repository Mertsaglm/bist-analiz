"""Veri kaynağı adaptörleri ve veri akışı — AĞ SINIRINDA NE OLUYOR?

Adaptörlerin tek sözleşmesi var: **ASLA istisna fırlatmazlar, ama HATAYI DA
GİZLEMEZLER.** İkisi aynı şey değil ve fark hayati:

* İstisna fırlatmak günlük akışı çökertir.
* Hatayı sessizce boş listeye çevirmek daha kötüdür: "bugün veri yok" ile
  "kaynağa ulaşılamadı" aynı çıktıya düşer, çıkış kodu 0 olur ve sistem
  habersiz çalışmaya devam eder (LESSONS L-002 deseni).

Ayrıca iki ölçülmüş tuzak sabitlenir:

1. **EVDS değerleri NOKTA ondalıklıdır** ('45.71340000'). Türkçe virgül
   ayrıştırıcısını buraya uygulamak 10 kat hata üretir ve sessizce geçer.
2. **EVDS/KAP geniş pencereyi KIRPAR.** Tek istekte 10 yıllık günlük seri
   istemek eksik veri döndürür ve eksiklik "seri kısaymış" gibi görünür. Çözüm
   dilimlemedir ve dilimlemenin GERÇEKTEN koştuğu test edilir.

Bu dosyada AĞ YOKTUR: her çağrı monkeypatch'lenmiş. Gerçek kaynak davranışı
`tests/test_prices.py` ve `tests/test_calendar.py` içindeki `real_con`
testleriyle ölçülür (LESSONS L-005: inancı fixture testine çevir).
"""

from __future__ import annotations

import types

import pandas as pd
import pytest

from src import db, logging_setup, prices, universe, util
from src.sources import evds, yf

from tests.conftest import add_universe, bar_serisi


# ============================================================ yfinance
def _yf_ham(n: int = 5, adj: bool = True) -> pd.DataFrame:
    """yfinance'in döndürdüğü biçim: indeks tarih, kolonlar büyük harfli."""
    idx = pd.to_datetime([f"2026-07-{20 + i:02d}" for i in range(n)])
    d = pd.DataFrame(index=idx)
    d["Open"] = [100.0 + i for i in range(n)]
    d["High"] = [101.0 + i for i in range(n)]
    d["Low"] = [99.0 + i for i in range(n)]
    d["Close"] = [100.5 + i for i in range(n)]
    d["Volume"] = [1_000_000] * n
    if adj:
        d["Adj Close"] = [90.5 + i for i in range(n)]      # BİLEREK ayrı
    return d


class TestYfNormalizasyon:
    def test_iki_fiyat_serisi_AYRI_tasinir(self):
        """`c` = Close, `c_tr` = Adj Close. Karıştırmak ya seviyeleri ya
        momentumu sessizce bozar (ölçüldü: TUPRS 2025-03-28)."""
        out = yf._normalize(_yf_ham())
        assert list(out.columns) == ["date", "o", "h", "l", "c", "v", "c_tr"]
        assert out["c"].iloc[0] == 100.5
        assert out["c_tr"].iloc[0] == 90.5
        assert (out["c"] != out["c_tr"]).all()

    def test_adj_close_YOKSA_toplam_getiri_ham_kapanistir(self):
        """Bazı endekslerde Adj Close yok; uydurma yapılmaz, ham kapanış kullanılır."""
        out = yf._normalize(_yf_ham(adj=False))
        assert (out["c_tr"] == out["c"]).all()

    def test_tarih_ISO_ve_siralanabilir(self):
        out = yf._normalize(_yf_ham())
        assert out["date"].iloc[0] == "2026-07-20"
        assert list(out["date"]) == sorted(out["date"])

    def test_KAPANISI_OLMAYAN_satir_atilir(self):
        """Sessizce taşımak yerine atmak: NaN kapanış her göstergeyi bozar."""
        ham = _yf_ham()
        ham.loc[ham.index[2], "Close"] = None
        out = yf._normalize(ham)
        assert len(out) == 4
        assert "2026-07-22" not in set(out["date"])

    def test_TEKRARLI_tarih_teklestirilir(self):
        ham = pd.concat([_yf_ham(2), _yf_ham(2)])
        out = yf._normalize(ham)
        assert len(out) == 2

    def test_bos_girdi_BOS_TABLO(self):
        for girdi in (None, pd.DataFrame()):
            out = yf._normalize(girdi)
            assert out.empty
            assert list(out.columns) == ["date", "o", "h", "l", "c", "v", "c_tr"]


class TestYfDayaniklilik:
    def test_hata_ISTISNA_FIRLATMAZ(self, real_cfg, monkeypatch):
        """Adaptör çökmez — çağıran "veri yok"u normal bir durum olarak ele alır."""
        def patla(*a, **k):
            raise RuntimeError("ağ yok")
        monkeypatch.setattr(yf.yf, "Ticker", patla)
        monkeypatch.setattr(yf.time, "sleep", lambda s: None)
        assert yf.fetch_bars("THYAO", real_cfg).empty
        assert yf.fetch_index("XU100.IS", real_cfg).empty
        assert yf.fetch_actions("THYAO", real_cfg) == []

    def test_YENIDEN_DENEME_config_kadar(self, real_cfg, monkeypatch):
        sayac = {"n": 0}

        class Sahte:
            def __init__(self, sym): pass
            def history(self, **k):
                sayac["n"] += 1
                raise RuntimeError("geçici")

        monkeypatch.setattr(yf.yf, "Ticker", Sahte)
        monkeypatch.setattr(yf.time, "sleep", lambda s: None)
        yf.fetch_bars("THYAO", real_cfg)
        assert sayac["n"] == int(real_cfg["sources"]["yf"]["yeniden_deneme"])

    def test_bos_donusde_de_yeniden_denenir(self, real_cfg, monkeypatch):
        """Boş yanıt geçici olabilir; tek denemede pes etmek veri kaybıdır."""
        sayac = {"n": 0}

        class Sahte:
            def __init__(self, sym): pass
            def history(self, **k):
                sayac["n"] += 1
                return pd.DataFrame()

        monkeypatch.setattr(yf.yf, "Ticker", Sahte)
        monkeypatch.setattr(yf.time, "sleep", lambda s: None)
        yf.fetch_bars("THYAO", real_cfg)
        assert sayac["n"] == int(real_cfg["sources"]["yf"]["yeniden_deneme"])

    def test_TEMETTU_DUZELTMESI_KAPALI_istenir(self, real_cfg, monkeypatch):
        """`auto_adjust=False` ŞART: iki seriyi ayrı tutabilmenin tek yolu.

        `auto_adjust=True` olsaydı `Close` da düzeltilmiş olur ve `c` ile `c_tr`
        AYNI seriye düşerdi — plan fiyatları piyasada olmayan seviyelere kayardı.
        """
        gorulen = {}

        class Sahte:
            def __init__(self, sym): pass
            def history(self, **k):
                gorulen.update(k)
                return _yf_ham()

        monkeypatch.setattr(yf.yf, "Ticker", Sahte)
        monkeypatch.setattr(yf.time, "sleep", lambda s: None)
        yf.fetch_bars("THYAO", real_cfg)
        assert gorulen["auto_adjust"] is False
        assert gorulen["actions"] is True

    def test_probe_veri_yoksa_ok_FALSE(self, real_cfg, monkeypatch):
        monkeypatch.setattr(yf, "fetch_bars", lambda *a, **k: pd.DataFrame())
        p = yf.probe("XXXX", real_cfg)
        assert p["ok"] is False and p["reason"] == "veri yok"

    def test_probe_olcumleri_uretir(self, real_cfg, monkeypatch):
        rows = bar_serisi(120, gunluk_egim=0.001)
        df = pd.DataFrame(rows, columns=["date", "o", "h", "l", "c", "v", "c_tr"])
        monkeypatch.setattr(yf, "fetch_bars", lambda *a, **k: df)
        p = yf.probe("AAA", real_cfg)
        assert p["ok"] and p["bars"] == 120
        assert p["median_turnover_try"] > 0
        assert p["zero_vol_ratio"] == 0.0
        assert p["vol_ann_pct"] is not None


class TestKurumsalIslem:
    def test_temettu_ve_bolunme_ayrilir(self, real_cfg, monkeypatch):
        acts = pd.DataFrame(
            {"Dividends": [7.78, 0.0], "Stock Splits": [0.0, 10.0]},
            index=pd.to_datetime(["2025-03-28", "2025-05-07"]))

        class Sahte:
            def __init__(self, sym): pass
            actions = acts

        monkeypatch.setattr(yf.yf, "Ticker", Sahte)
        monkeypatch.setattr(yf.time, "sleep", lambda s: None)
        out = yf.fetch_actions("TUPRS", real_cfg)
        assert {"date": "2025-03-28", "kind": "temettu", "value": 7.78} in out
        assert {"date": "2025-05-07", "kind": "bolunme", "value": 10.0} in out

    def test_sifir_degerli_kayit_YAZILMAZ(self, real_cfg, monkeypatch):
        acts = pd.DataFrame({"Dividends": [0.0], "Stock Splits": [0.0]},
                            index=pd.to_datetime(["2025-01-02"]))

        class Sahte:
            def __init__(self, sym): pass
            actions = acts

        monkeypatch.setattr(yf.yf, "Ticker", Sahte)
        monkeypatch.setattr(yf.time, "sleep", lambda s: None)
        assert yf.fetch_actions("AAA", real_cfg) == []


# ============================================================ EVDS
class TestEvdsDegerAyristirma:
    @pytest.mark.parametrize("ham,beklenen", [
        ("45.71340000", 45.7134),
        ("45", 45.0),
        (" 3.5 ", 3.5),
        ("0", 0.0),
    ])
    def test_NOKTA_ondalik(self, ham, beklenen):
        assert evds._parse_value(ham) == pytest.approx(beklenen)

    def test_TR_VIRGUL_AYRISTIRICISI_KULLANILMAZ(self):
        """⚠ '45,71' burada float'a ÇEVRİLMEZ → None.

        Bu bilinçli: EVDS nokta ondalık kullanıyor. Virgülü ondalık sayan bir
        ayrıştırıcı '45.71'i 4571 yapardı (10 kat hata) ve sessizce geçerdi.
        None dönmek, yanlış sayı dönmekten iyidir.
        """
        assert evds._parse_value("45,71") is None

    def test_bos_ve_None_None(self):
        assert evds._parse_value(None) is None
        assert evds._parse_value("") is None
        assert evds._parse_value("abc") is None


class TestEvdsCekim:
    def _yanit(self, items):
        class R:
            status_code = 200
            def raise_for_status(self): pass
            def json(self_inner): return {"items": items}
        return R()

    def test_anahtar_YOKSA_bos_liste(self, real_cfg, monkeypatch):
        """Anahtar yoksa uydurma yapılmaz; rapor satırı gizlenir."""
        monkeypatch.delenv("EVDS_API_KEY", raising=False)
        monkeypatch.setattr(evds, "available", lambda: False)
        assert evds.fetch_series(real_cfg, "TP.APIFON4") == []

    def test_GG_AA_YYYY_tarihi_ISOya_cevrilir(self, real_cfg, monkeypatch):
        """ISO'ya çevrilmezse `ORDER BY date` kronolojik OLMAZ — sessiz bozulma."""
        monkeypatch.setenv("EVDS_API_KEY", "test")
        istekler = []

        def sahte_get(url, **k):
            istekler.append(url)
            return self._yanit([{"Tarih": "05-03-2025", "TP_APIFON4": "45.5"},
                                {"Tarih": "06-03-2025", "TP_APIFON4": "45.7"}])

        monkeypatch.setattr(evds, "requests", types.SimpleNamespace(get=sahte_get))
        out = evds.fetch_series(real_cfg, "TP.APIFON4")
        assert [r["date"] for r in out] == ["2025-03-05", "2025-03-06"]
        assert out[0]["value"] == pytest.approx(45.5)
        assert "series=TP.APIFON4" in istekler[0]

    def test_alan_adi_NOKTASIZ_aranir(self, real_cfg, monkeypatch):
        """EVDS alan adında noktayı alt çizgiye çevirir: TP.FE.OKTG01 → TP_FE_OKTG01."""
        monkeypatch.setenv("EVDS_API_KEY", "test")
        monkeypatch.setattr(evds, "requests", types.SimpleNamespace(
            get=lambda url, **k: self._yanit(
                [{"Tarih": "01-01-2025", "TP_FE_OKTG01": "2500.5"}])))
        out = evds.fetch_series(real_cfg, "TP.FE.OKTG01")
        assert out[0]["value"] == pytest.approx(2500.5)

    def test_bozuk_tarih_ATLANIR(self, real_cfg, monkeypatch):
        monkeypatch.setenv("EVDS_API_KEY", "test")
        monkeypatch.setattr(evds, "requests", types.SimpleNamespace(
            get=lambda url, **k: self._yanit(
                [{"Tarih": "", "TP_APIFON4": "1"},
                 {"Tarih": "01-01-2025", "TP_APIFON4": "2"}])))
        assert len(evds.fetch_series(real_cfg, "TP.APIFON4")) == 1

    def test_ag_hatasi_BOS_liste_ISTISNA_YOK(self, real_cfg, monkeypatch):
        monkeypatch.setenv("EVDS_API_KEY", "test")

        def patla(url, **k):
            raise RuntimeError("bağlanamadı")

        monkeypatch.setattr(evds, "requests", types.SimpleNamespace(get=patla))
        assert evds.fetch_series(real_cfg, "TP.APIFON4") == []

    def test_beklenmeyen_yanit_tipi_BOS_liste(self, real_cfg, monkeypatch):
        monkeypatch.setenv("EVDS_API_KEY", "test")

        class R:
            def raise_for_status(self): pass
            def json(self): return ["liste beklenmiyordu"]

        monkeypatch.setattr(evds, "requests", types.SimpleNamespace(
            get=lambda url, **k: R()))
        assert evds.fetch_series(real_cfg, "TP.APIFON4") == []

    def test_ANAHTAR_HEADERDA_gonderilir(self, real_cfg, monkeypatch):
        """Nisan 2024 kuralı: key query string'de değil HEADER'da."""
        monkeypatch.setenv("EVDS_API_KEY", "gizli")
        gorulen = {}

        def sahte_get(url, **k):
            gorulen.update({"url": url, **k})
            return self._yanit([])

        monkeypatch.setattr(evds, "requests", types.SimpleNamespace(get=sahte_get))
        evds.fetch_series(real_cfg, "TP.APIFON4")
        assert gorulen["headers"]["key"] == "gizli"
        assert "gizli" not in gorulen["url"]

    def test_DILIMLEME_yil_yil_ceker(self, real_cfg, monkeypatch):
        """⚠ Tek istekte 10 yıllık günlük seri SESSİZCE kırpılır.

        Dilimleme kaybolursa eksik veri "seri kısaymış" gibi görünür — yani
        hata değil, yanlış bir gerçek olarak sisteme girer.
        """
        monkeypatch.setenv("EVDS_API_KEY", "test")
        cagrilar = []

        def sahte(cfg, kod, *, start=None, end=None):
            cagrilar.append((start, end))
            return [{"date": f"{start[-4:]}-06-01", "value": 1.0}]

        monkeypatch.setattr(evds, "fetch_series", sahte)
        out = evds.fetch_series_chunked(real_cfg, "TP.DK.USD.S.YTL",
                                        start_year=2020)
        from datetime import date
        beklenen_yil = date.today().year - 2020 + 1
        assert len(cagrilar) == beklenen_yil
        assert cagrilar[0] == ("01-01-2020", "31-12-2020")
        assert len(out) == beklenen_yil

    def test_dilimler_TEKRARI_eler_ve_siralar(self, real_cfg, monkeypatch):
        monkeypatch.setenv("EVDS_API_KEY", "test")
        monkeypatch.setattr(evds, "fetch_series", lambda cfg, kod, **k: [
            {"date": "2021-01-05", "value": 2.0},
            {"date": "2020-01-05", "value": 1.0}])
        out = evds.fetch_series_chunked(real_cfg, "X", start_year=2020)
        assert [r["date"] for r in out] == ["2020-01-05", "2021-01-05"]


# ============================================================ veri akışı
class TestVeriAkisi:
    """Ağ çağrıları taklit; test edilen şey ORKESTRASYON.

    LESSONS L-002: "bir kere elle çalıştırdım, gerisi otomatik" varsayımı
    yanlıştır. Bir tabloyu besleyen adım günlük akışa BAĞLI DEĞİLSE donar ve
    hiçbir hata fırlatmaz. Aşağıdaki testler o bağların yerinde olduğunu
    doğrular.
    """

    @pytest.fixture
    def sahte_yf(self, monkeypatch):
        monkeypatch.setattr(prices.yf, "fetch_bars", lambda t, cfg, **k: pd.DataFrame(
            bar_serisi(30, gunluk_egim=0.001),
            columns=["date", "o", "h", "l", "c", "v", "c_tr"]))
        monkeypatch.setattr(prices.yf, "fetch_index", lambda s, cfg, **k: pd.DataFrame(
            bar_serisi(30), columns=["date", "o", "h", "l", "c", "v", "c_tr"]))
        monkeypatch.setattr(prices.yf, "fetch_actions", lambda t, cfg, **kwargs: [
            {"date": "2023-02-01", "kind": "temettu", "value": 1.5}])

    def test_backfill_HAYALET_AYIKLAMAYI_kosar(self, cfg, con, sahte_yf):
        """Ayıklama boru hattının PARÇASI — elle çalıştırılan adım bırakılmaz."""
        add_universe(con, "AAA")
        r = prices.backfill(cfg, con, ["AAA"])
        assert r["bars"]["AAA"] == 30
        assert "hayalet_silinen" in r

    def test_gunluk_KALITE_KAPISINI_kosar(self, cfg, con, sahte_yf):
        """Kapı donduğunda sessizce KAPANIR (`quality_map` boş döner) — bu yüzden
        `bist veri gunluk` onu kendisi çağırmak zorunda."""
        add_universe(con, "AAA")
        r = prices.daily(cfg, con, ["AAA"])
        assert r["kalite_degerlendirilen"] == 1
        assert db.scalar(con, "SELECT COUNT(*) FROM data_quality") == 1

    def test_gunluk_KAYAN_PENCERE_kullanir(self, cfg, con, sahte_yf):
        """Tek bar çekmek eski satırları BAYAT bırakır: yfinance temettü
        ex-tarihinde geçmiş Adj Close'ları geriye dönük düzeltir."""
        add_universe(con, "AAA")
        r = prices.daily(cfg, con, ["AAA"], gun=15)
        from datetime import date, timedelta
        assert r["start"] == (date.today() - timedelta(days=15)).isoformat()

    def test_sync_indices_TUM_sembolleri_yazar(self, cfg, con, sahte_yf):
        sonuc = prices.sync_indices(cfg, con)
        beklenen = set(universe.index_symbols(cfg))
        assert set(sonuc) == beklenen
        yazilan = {r["symbol"] for r in db.fetch_all(
            con, "SELECT DISTINCT symbol FROM index_daily")}
        assert yazilan == beklenen

    def test_takvim_kaynagi_endeksi_YAZILIR(self, cfg, con, sahte_yf):
        """Takvim XU100 barlarından türetiliyor; o seri yazılmazsa takvim yoktur."""
        prices.sync_indices(cfg, con)
        kaynak = cfg["takvim"]["turet_kaynak_endeks"]
        assert db.scalar(con, "SELECT COUNT(*) FROM index_daily WHERE symbol=?",
                         (kaynak,)) == 30

    def test_sync_actions_kurumsal_islemi_SAKLAR(self, cfg, con, sahte_yf):
        """yfinance fiyata zaten uyguluyor; biz AYRICA saklıyoruz çünkü plan
        penceresine düşen ex-tarih sonucu `iptal_kurumsal` yapar."""
        add_universe(con, "AAA")
        r = prices.sync_actions(cfg, con, ["AAA"])
        assert r["kayit"] == 1
        satir = db.fetch_one(con, "SELECT * FROM corporate_actions")
        assert satir["kind"] == "temettu" and satir["source"] == "yfinance"

    def test_turnover_YAZMA_aninda_hesaplanir(self, cfg, con, sahte_yf):
        """Likidite kapısı `turnover_try`'a dayanır; NULL kalırsa kapı
        "bilinmiyor" der ve her ismi eler."""
        add_universe(con, "AAA")
        prices.backfill(cfg, con, ["AAA"])
        satir = db.fetch_one(con, "SELECT c, v, turnover_try FROM bars_daily LIMIT 1")
        assert satir["turnover_try"] == pytest.approx(satir["c"] * satir["v"])

    def test_bos_kaynak_donusu_SATIR_YAZMAZ(self, cfg, con, monkeypatch):
        monkeypatch.setattr(prices.yf, "fetch_bars",
                            lambda t, cfg, **k: pd.DataFrame())
        monkeypatch.setattr(prices.yf, "fetch_index",
                            lambda s, cfg, **k: pd.DataFrame())
        add_universe(con, "AAA")
        r = prices.backfill(cfg, con, ["AAA"])
        assert r["bars"]["AAA"] == 0
        assert db.scalar(con, "SELECT COUNT(*) FROM bars_daily") == 0

    def test_NaN_deger_None_olarak_yazilir(self, cfg, con, monkeypatch):
        rows = bar_serisi(3)
        df = pd.DataFrame(rows, columns=["date", "o", "h", "l", "c", "v", "c_tr"])
        df.loc[1, "v"] = float("nan")
        monkeypatch.setattr(prices.yf, "fetch_bars", lambda t, cfg, **k: df)
        monkeypatch.setattr(prices.yf, "fetch_index",
                            lambda s, cfg, **k: pd.DataFrame())
        add_universe(con, "AAA")
        prices.backfill(cfg, con, ["AAA"])
        hacimler = [r["v"] for r in db.fetch_all(
            con, "SELECT v FROM bars_daily ORDER BY date")]
        assert hacimler[1] is None


# ============================================================ loglama
class TestLoglama:
    def test_setup_dizini_olusturur_ve_IDEMPOTENT(self, cfg, monkeypatch):
        """İkinci çağrı hiçbir şey yapmamalı: aksi halde her komut yeni bir
        handler ekler ve loglar katlanarak çoğalır."""
        monkeypatch.setattr(logging_setup, "_KURULDU", False)
        logging_setup.setup(cfg, sessiz=True)
        dizin = util.resolve(cfg["paths"]["log_dir"])
        assert dizin.exists()
        import logging
        n = len(logging.getLogger().handlers)
        logging_setup.setup(cfg, sessiz=True)
        assert len(logging.getLogger().handlers) == n

    def test_gurultulu_kutuphaneler_kisitlanir(self, cfg, monkeypatch):
        """yfinance/urllib3 DEBUG logu dosyayı doldurup gerçek uyarıları gizler."""
        import logging
        monkeypatch.setattr(logging_setup, "_KURULDU", False)
        logging_setup.setup(cfg, sessiz=True)
        for ad in ("yfinance", "urllib3", "peewee"):
            assert logging.getLogger(ad).level >= logging.WARNING
