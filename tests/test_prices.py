"""Fiyat katmanı testleri.

Bu dosyanın asıl işi VERİ KAYNAĞININ davranışını sabitlemek. LESSONS L-005:
araştırmadan gelen "bilinen sorun" bilgisi bayatlar; inancı fixture testine
çevir ki kaynak regresyona giderse CI söylesin.
"""

from __future__ import annotations

import pytest

from src import prices
from tests.conftest import add_bars, add_index, add_universe


# ============================================================ gerçek veri
class TestKaynakDavranisi:
    """yfinance'in BIST davranışı — inanç değil, ölçüm."""

    def test_temettu_duzeltmesi_uygulaniyor(self, real_con):
        """TUPRS 2025-03-28, 7.78 TL temettü.

        Ham kapanış temettü kadar düşer (−%2.95); toplam getiri serisi düşmez
        (+%2.67). İkisi AYNI yönde çıkarsa `c_tr` artık toplam getiri değildir
        ve momentum faktörleri sessizce bozulur.
        """
        df = prices.bars(real_con, "TUPRS", start="2025-03-20", end="2025-04-02")
        if df.empty or "2025-03-28" not in set(df["date"]):
            pytest.skip("TUPRS 2025-03-28 barı veritabanında yok")

        i = df.index[df["date"] == "2025-03-28"][0]
        assert i > 0, "önceki bar gerekli"
        ham = df["c"][i] / df["c"][i - 1] - 1
        duz = df["c_tr"][i] / df["c_tr"][i - 1] - 1

        assert ham < 0, f"ham getiri negatif olmalı (temettü düşüşü), bulunan {ham:.4f}"
        assert duz > 0, f"düzeltilmiş getiri pozitif olmalı, bulunan {duz:.4f}"
        assert duz - ham > 0.04, (
            "toplam getiri ile ham getiri arasındaki fark temettü kadar olmalı; "
            f"fark {duz - ham:.4f} — yfinance düzeltmeyi bırakmış olabilir")

    def test_bedelsiz_geri_duzeltiliyor(self, real_con):
        """FROTO 2025-05-07, 10:1 bedelsiz. Seri sürekli olmalı.

        Geri düzeltme çalışmazsa o gün ~%90 düşüş görünür ve bu, sistemin
        her katmanını (stop, ATR, momentum) tek başına bozar.
        """
        df = prices.bars(real_con, "FROTO", start="2025-05-01", end="2025-05-15")
        if df.empty or "2025-05-07" not in set(df["date"]):
            pytest.skip("FROTO 2025-05-07 barı veritabanında yok")

        i = df.index[df["date"] == "2025-05-07"][0]
        assert i > 0
        getiri = abs(df["c"][i] / df["c"][i - 1] - 1)
        assert getiri < 0.05, (
            f"bedelsiz gününde |getiri| %{getiri*100:.1f} — seri süreksiz, "
            "yfinance geri düzeltmeyi bırakmış olabilir")

    def test_tatil_gunlerinde_bar_yok(self, real_con, real_cfg):
        """Hayalet bar ayıklaması gerçekten çalışıyor mu.

        Yahoo, BIST kapalıyken v=0 & o=h=l=c bar üretiyor. 2026-05-27/28/29
        Kurban Bayramı — bu tarihlerde HİÇBİR hissenin barı olmamalı.
        """
        for tarih in ("2026-05-27", "2026-05-28", "2026-05-29"):
            n = real_con.execute(
                "SELECT COUNT(*) FROM bars_daily WHERE date = ?", (tarih,)).fetchone()[0]
            assert n == 0, f"{tarih} tatil ama {n} bar var — hayalet ayıklaması çalışmıyor"

    def test_endeks_tatilde_temiz(self, real_con):
        """XU100 hayalet bar ÜRETMİYOR — takvimin otoriter kaynağı olmasının şartı."""
        n = real_con.execute(
            "SELECT COUNT(*) FROM index_daily WHERE symbol='XU100' "
            "AND date IN ('2026-05-27','2026-05-28','2026-05-29','2026-01-01')"
        ).fetchone()[0]
        assert n == 0, "XU100'de tatil barı var — takvim türetmesi güvenilmez"


# ============================================================ sentetik
class TestHayaletAyiklama:
    def test_sadece_uc_kosul_birlikte_siler(self, cfg, con):
        """Ayıklama ölçütü: düz VE sıfır hacim VE endekste yok.

        Üçünün birleşimi şart. Ölçüm (2026-07-26) gösterdi ki:
          - yalnız "endekste yok" → 142 gerçek bar silinirdi (endeks boşlukları)
          - yalnız "düz+sıfır"    →  63 gerçek bar silinirdi (işlem durdurma)
        """
        add_universe(con, "TEST")
        add_index(con, "XU100", ["2026-01-05", "2026-01-06", "2026-01-08"])
        add_bars(con, "TEST", [
            ("2026-01-05", 10, 11, 9, 10, 1000, 10),    # normal seans
            ("2026-01-06", 10, 10, 10, 10, 0, 10),      # düz+sıfır AMA endekste VAR → kalmalı
            ("2026-01-07", 10, 10, 10, 10, 0, 10),      # düz+sıfır+endekste YOK → HAYALET
            ("2026-01-08", 10, 12, 9, 11, 2000, 11),    # normal
            ("2026-01-09", 11, 13, 10, 12, 3000, 12),   # endekste yok AMA gerçek → kalmalı
        ])
        r = prices.purge_phantom_bars(cfg, con)

        assert r["silinen"] == 1
        kalan = set(prices.bars(con, "TEST")["date"])
        assert "2026-01-07" not in kalan, "hayalet bar silinmedi"
        assert "2026-01-06" in kalan, "gerçek seansta düz+sıfır bar yanlışlıkla silindi"
        assert "2026-01-09" in kalan, "endeks boşluğundaki gerçek bar yanlışlıkla silindi"

    def test_endeks_sonrasina_dokunmaz(self, cfg, con):
        """Endeks bir gün gecikebilir; o penceredeki hisse barları gerçektir.

        Doğrulandı: THYAO 2026-07-24 (hacim 23,4mn) varken XU100 son barı 07-23.
        """
        add_universe(con, "TEST")
        add_index(con, "XU100", ["2026-01-05"])
        add_bars(con, "TEST", [
            ("2026-01-05", 10, 11, 9, 10, 1000, 10),
            ("2026-01-06", 10, 10, 10, 10, 0, 10),   # endeks sınırının SONRASI → korunur
        ])
        r = prices.purge_phantom_bars(cfg, con)
        assert r["silinen"] == 0
        assert "2026-01-06" in set(prices.bars(con, "TEST")["date"])

    def test_endeks_yoksa_atlar(self, cfg, con):
        """Endeks verisi yokken ayıklama YAPILMAZ — ölçüt kurulamaz.

        Sessizce her şeyi silmek yerine açıkça atlar ve uyarır.
        """
        add_universe(con, "TEST")
        add_bars(con, "TEST", [("2026-01-06", 10, 10, 10, 10, 0, 10)])
        r = prices.purge_phantom_bars(cfg, con)
        assert r["atlandi"] is True
        assert r["silinen"] == 0


class TestOkuma:
    def test_bars_tarihe_gore_sirali(self, con):
        add_universe(con, "TEST")
        add_bars(con, "TEST", [
            ("2026-01-08", 3, 3, 3, 3, 1, 3),
            ("2026-01-05", 1, 1, 1, 1, 1, 1),
            ("2026-01-06", 2, 2, 2, 2, 1, 2),
        ])
        df = prices.bars(con, "TEST")
        assert list(df["date"]) == ["2026-01-05", "2026-01-06", "2026-01-08"]

    def test_turnover_hesaplaniyor(self, con):
        add_universe(con, "TEST")
        add_bars(con, "TEST", [("2026-01-05", 10, 10, 10, 10, 500, 10)])
        assert prices.bars(con, "TEST")["turnover_try"][0] == pytest.approx(5000.0)


class TestOhlcTutarliligi:
    """⚠ REGRESYON KİLİDİ (2026-08-07, Merdiven `sanitizeQuotes` fikrinden).

    Kalite kapısı bar SAYISINA, sıfır hacme, boşluğa, donuk kapanışa ve
    açıklanamayan sıçramaya bakıyordu — barın KENDİ İÇİNDE tutarlı olup
    olmadığına (`h ≥ l`, `l ≤ o,c ≤ h`) hiç bakmıyordu. `l > c` olan tek bir
    bar `levels.build_levels`'daki swing tespitini ve ATR'yi sessizce bozar ve
    hiçbir kontrol patlamaz — L-007'nin imzası.

    ÖLÇÜLDÜ: gerçek `bars_daily`'de 197.191 barda **0 ihlal**. Yani bu bir
    temizlik değil, bir TELDİR.
    """

    @staticmethod
    def _df(rows):
        import pandas as pd
        return pd.DataFrame(rows, columns=["date", "o", "h", "l", "c"])

    def test_saglam_bar_temiz(self):
        from src import prices
        d = self._df([("2026-01-02", 10.0, 11.0, 9.0, 10.5)])
        assert not prices.ohlc_ihlalleri(d).any()

    @pytest.mark.parametrize("o,h,l,c,ad", [
        (10.0, 9.0, 11.0, 10.0, "h < l"),
        (10.0, 11.0, 9.0, 12.0, "c > h"),
        (10.0, 11.0, 9.0, 8.0, "c < l"),
        (12.0, 11.0, 9.0, 10.0, "o > h"),
        (8.0, 11.0, 9.0, 10.0, "o < l"),
        (10.0, 11.0, 9.0, 0.0, "c = 0"),
        (10.0, 11.0, -1.0, 10.0, "l < 0"),
        (10.0, 11.0, 9.0, None, "c NULL"),
    ])
    def test_bozuk_bar_yakalanir(self, o, h, l, c, ad):
        from src import prices
        assert prices.ohlc_ihlalleri(self._df([("2026-01-02", o, h, l, c)])).any(), \
            f"{ad} yakalanmadı"

    def test_TOLERANS_YOK(self):
        """`h ≥ l` bir muhasebe kimliğidir. En küçük ihlal bile ihlaldir."""
        from src import prices
        d = self._df([("2026-01-02", 10.0, 11.0, 9.0, 11.0000001)])
        assert prices.ohlc_ihlalleri(d).any()

    def test_kalite_kapisi_bozuk_bari_ELER(self, cfg, con):
        """Sayaç yetmez — kapı gerçekten KAPANMALI (ok=False)."""
        from src import prices
        from tests.conftest import add_bars, add_universe, bar_serisi
        add_universe(con, "AAA")
        rows = bar_serisi(120)
        d, o, h, low, c, v, ctr = rows[60]
        rows[60] = (d, o, low - 1.0, h + 1.0, c, v, ctr)      # h ile l ters
        add_bars(con, "AAA", rows)
        r = prices.assess_quality(cfg, con, tickers=["AAA"], store=False)[0]
        assert r["ohlc_ihlal"] >= 1
        assert r["ok"] is False
        assert any("KENDİ İÇİNDE tutarsız" in x for x in r["reasons"])

    def test_saglam_seride_kapi_ACIK_KALIR(self, cfg, con):
        """Kontrol grubu: kontrol her şeyi eliyorsa kontrol değil, arızadır."""
        from src import prices
        from tests.conftest import add_bars, add_universe, bar_serisi
        add_universe(con, "BBB")
        add_bars(con, "BBB", bar_serisi(120))
        r = prices.assess_quality(cfg, con, tickers=["BBB"], store=False)[0]
        assert r["ohlc_ihlal"] == 0
        assert not any("tutarsız" in x for x in r["reasons"])

    def test_bos_seride_ihlal_SIFIR_DEGIL_None(self, cfg, con):
        """Veri yokken 0 ihlal demek, ölçmediğini 'temiz' diye raporlamaktır."""
        from src import prices
        from tests.conftest import add_universe
        add_universe(con, "CCC")
        r = prices.assess_quality(cfg, con, tickers=["CCC"], store=False)[0]
        assert r["ohlc_ihlal"] is None
        assert r["ok"] is False


class TestGercekVerideOhlc:
    """ÖLÇÜLMÜŞ GERÇEK — kaynak regresyona giderse CI söyler (L-005 deseni).

    2026-08-07 ölçümü:
        bars_daily   197.191 bar → **0 ihlal**
        index_daily   14.553 bar → 54 ihlal, **TAMAMI USDTRY** (3.013 barın %1.8'i)
        XU100 / XU030 / XBANK / XUSIN → 0 ihlal

    ⚠ İLK YAZDIĞIM DEĞER YANLIŞTI ve bu test onu yakaladı. En son 8 ihlale
    bakıp "sapma ≤ %0.06" demiştim — kısmi örnekten genelleme. Tam dağılım:
        medyan %0.0068 · %0.1 üstü 6 · %0.5 üstü 3 · %1 üstü 2 · maks **%1.796**
    Kuyruk gerçek ve açıklanabilir: 2021-03-22 (TCMB başkanının görevden
    alınmasının ardından TL boşluklu açtı, Yahoo'nun barı boşluğu tutmadı) ve
    2024-01-01 / 2023-12-25 (tatil, donuk kotasyon). Yani bu bir "gürültü" değil,
    **medyanı gürültü, kuyruğu olay** olan bir dağılım.

    Bizim için sonucu yok: `regime.classify` USDTRY'den yalnız `c` okur ve
    ürettiği `usdtry_vol_ann_21` kaydedilen bir girdidir, rejim eşiği değil.
    Ama BİLİNMEZSE bir gün "veri bozuldu" diye teşhis edilir (L-003).

    Bu yüzden test MAKSİMUMA değil DAĞILIMA bakar: maksimum 2021'de donmuş tek
    bir olaydır ve ona eşik koymak, geçmişi test etmek olur.
    """

    def test_hisse_barlari_TAMAMEN_tutarli(self, real_con):
        n = real_con.execute(
            "SELECT COUNT(*) FROM bars_daily WHERE h < l OR c > h OR c < l "
            "   OR o > h OR o < l OR c <= 0").fetchone()[0]
        assert n == 0, f"{n} hisse barı kendi içinde tutarsız — yfinance regresyonu?"

    def test_BIST_endeksleri_tutarli(self, real_con):
        n = real_con.execute(
            "SELECT COUNT(*) FROM index_daily WHERE symbol LIKE 'X%' "
            "  AND (h < l OR c > h OR c < l)").fetchone()[0]
        assert n == 0, f"{n} BIST endeks barı tutarsız"

    def test_USDTRY_ihlali_SEYREK_kalir(self, real_con):
        """Oran büyürse bu artık 'bilinen kusur' değil, gerçek bir bozulmadır."""
        r = real_con.execute(
            "SELECT COUNT(*) n, SUM(CASE WHEN c > h OR c < l THEN 1 ELSE 0 END) k "
            "  FROM index_daily WHERE symbol = 'USDTRY'").fetchone()
        if not r["n"]:
            pytest.skip("USDTRY verisi yok")
        oran = (r["k"] or 0) / r["n"]
        assert oran < 0.05, \
            f"USDTRY ihlal oranı %{oran*100:.1f} — 2026-08-07'de %1.8'di"

    def test_USDTRY_ihlallerinin_MEDYANI_gurultu_boyutunda(self, real_con):
        """Tipik ihlal gürültüdür; TİPİK olmaktan çıkarsa yapı değişmiştir."""
        import statistics as st
        v = [max((x["c"] - x["h"]) / x["h"], (x["l"] - x["c"]) / x["l"])
             for x in real_con.execute(
                 "SELECT h, l, c FROM index_daily WHERE symbol = 'USDTRY' "
                 "  AND (c > h OR c < l)")]
        if not v:
            return
        assert st.median(v) < 0.001, \
            f"medyan sapma %{st.median(v)*100:.4f} — 2026-08-07'de %0.0068'di"

    def test_USDTRY_yalniz_KAPANIS_kolonuyla_tuketilir(self):
        """Kuyruğun zararsız olmasının SEBEBİ budur — sebep değişirse test kırılsın.

        `regime.classify` USDTRY'nin h/l'sine dokunursa, yukarıdaki 'bizim için
        sonucu yok' cümlesi sessizce yalan olur (AGENTS.md §8: yorum bir iddiadır).
        """
        import inspect
        from src import regime
        kaynak = inspect.getsource(regime.classify)
        i = kaynak.index("USDTRY")
        blok = kaynak[i:i + 400]
        assert 'usd["h"]' not in blok and 'usd["l"]' not in blok, \
            "regime artık USDTRY'nin high/low'unu okuyor — FX bar kusuru " \
            "ARTIK ZARARSIZ DEĞİL, prices.ohlc_ihlalleri notunu güncelle"


class TestDuzeltilmemisKurumsal:
    """⚠ REGRESYON KİLİDİ (2026-08-07, #10 ölçümünden çıkan GERÇEK bulgu).

    NE OLMUŞTU: CCOLA'nın 2024-08-01 barı **−%90.7**. `corporate_actions`'ta
    kayıt VARDI (2024-08-13, oran 11.0) ama (a) tarih 12 gün kaymıştı ve
    (b) seri geriye düzeltilmemişti — 2024-07-31 kapanışı hâlâ 846 TL, ertesi
    gün 78.27 TL. yfinance bölünmeyi yanlış güne yazıp öncesini düzeltmemiş.

    `unexplained_jump` bunu YAKALAYAMAZ çünkü farklı bir soru sorar: "bu
    sıçramanın kaydı var mı?". Kayıt vardı ama başka gündeydi; yani kontrol
    ya affeder ya yanlış günü suçlar. Buradaki kural daha güçlü ve kayıttan
    BAĞIMSIZ: **düzgün düzeltilmiş bir seride ±%10 marjlı bir piyasada
    −%50'lik bar bulunmaz.**

    Eşik ÖLÇÜLDÜ: gerçek piyasa ucu +%22.2 / −%28.3, artefaktlar +%44 ve üstü.
    Aradaki boşluğa (%35) konuldu.
    """

    @staticmethod
    def _duzeltilmemis_seri(n: int, *, fiyat: float, kirilma: int, oran: float):
        """`kirilma` barından İTİBAREN tüm seviye `oran`a bölünür.

        Gerçek düzeltilmemiş bölünme böyle görünür: CCOLA 846 → 78 ve orada
        KALIR. Tek bir barı düşürüp bırakmak, ertesi gün +%1000'lik ikinci bir
        sahte sıçrama üretir ve testi gerçeğe benzemez hâle getirir.
        """
        from tests.conftest import bar_serisi
        rows = bar_serisi(n, fiyat=fiyat)
        out = []
        for i, (d, o, h, low, c, v, ctr) in enumerate(rows):
            k = oran if i >= kirilma else 1.0
            out.append((d, round(o / k, 4), round(h / k, 4), round(low / k, 4),
                        round(c / k, 4), v, round(ctr / k, 4)))
        return out

    def test_bedelsiz_gibi_gorunan_bar_KAPIYI_KAPATIR(self, cfg, con):
        from src import prices
        from tests.conftest import add_bars, add_universe
        add_universe(con, "AAA")
        rows = self._duzeltilmemis_seri(120, fiyat=800.0, kirilma=60, oran=11.0)
        add_bars(con, "AAA", rows)
        r = prices.assess_quality(cfg, con, tickers=["AAA"], store=False)[0]
        assert r["duzeltilmemis_kurumsal"] >= 1
        assert r["ok"] is False
        assert any("DÜZELTİLMEMİŞ" in x for x in r["reasons"])

    def test_KAYIT_VARSA_BILE_affetmez(self, cfg, con):
        """CCOLA'nın imzası buydu: kayıt vardı, seri yine bozuktu."""
        from src import db, prices
        from tests.conftest import add_bars, add_universe
        add_universe(con, "BBB")
        rows = self._duzeltilmemis_seri(120, fiyat=800.0, kirilma=60, oran=11.0)
        d = rows[60][0]
        add_bars(con, "BBB", rows)
        db.upsert_many(con, "corporate_actions",
                       ["ticker", "date", "kind", "value", "source"],
                       [("BBB", d, "bolunme", 11.0, "test")])
        r = prices.assess_quality(cfg, con, tickers=["BBB"], store=False)[0]
        assert r["unexplained_jump"] == 0, "kayıt sıçramayı 'açıkladı' (beklenen)"
        assert r["duzeltilmemis_kurumsal"] >= 1, \
            "kayıt varken kapı açık kaldı — CCOLA aynen böyle geçmişti"
        assert r["ok"] is False

    def test_GERCEK_piyasa_ucu_ELENMEZ(self, cfg, con):
        """2023-02-15 deprem sonrası açılış: 25 isim birden +%18…+%22.

        Eşik oraya inerse sistem bir kriz gününde 25 ismi birden eler —
        yani en çok bilgi lazım olan gün susar.
        """
        from src import prices
        from tests.conftest import add_bars, add_universe, bar_serisi
        add_universe(con, "CCC")
        rows = bar_serisi(120, fiyat=100.0)
        d = rows[60][0]
        yeni = round(rows[59][4] * 1.222, 4)         # +%22.2 — ölçülen gerçek uç
        rows[60] = (d, yeni, yeni * 1.001, rows[59][4], yeni, rows[60][5], yeni)
        add_bars(con, "CCC", rows)
        r = prices.assess_quality(cfg, con, tickers=["CCC"], store=False)[0]
        assert r["duzeltilmemis_kurumsal"] == 0, \
            "gerçek kriz günü artefakt sayıldı — eşik çok dar"

    def test_esik_config_ten_okunur(self, cfg, con):
        import copy
        from src import prices
        from tests.conftest import add_bars, add_universe
        add_universe(con, "DDD")
        rows = self._duzeltilmemis_seri(120, fiyat=100.0, kirilma=60, oran=1 / 0.60)
        add_bars(con, "DDD", rows)
        assert prices.assess_quality(
            cfg, con, tickers=["DDD"], store=False)[0]["duzeltilmemis_kurumsal"] >= 1
        gevsek = copy.deepcopy(cfg)
        gevsek["evren"]["duzeltilmemis_kurumsal_pct"] = 50.0
        assert prices.assess_quality(
            gevsek, con, tickers=["DDD"], store=False)[0]["duzeltilmemis_kurumsal"] == 0


class TestGercekVerideKurumsalIslem:
    """ÖLÇÜLMÜŞ GERÇEK (2026-08-07) — dört isimde düzeltilmemiş kurumsal işlem.

        TSPOR 2025-06-19 +94.6% · CCOLA 2024-08-01 −90.7%
        AYGAZ 2022-09-01 +72.5% · HEKTS 2024-09-09 −64.8% · HEKTS 2021-04-30 +44.1%

    Dördü de `in_measure=1` (faktör ağırlıklarını kalibre eden panel),
    hiçbiri `in_live` DEĞİL. Bu test ikinci gerçeği kilitler: bir gün bu
    isimlerden biri canlı evrene alınırsa test kırılır ve kimse bunu
    fark etmeden yapamaz.
    """

    def test_canli_evrende_duzeltilmemis_bar_YOK(self, real_cfg, real_con):
        from src import saglik
        b = [x for x in saglik.duzeltilmemis_kurumsal_tara(real_cfg, real_con)
             if x["in_live"]]
        assert not b, (
            "CANLI evrende düzeltilmemiş kurumsal işlem barı var: "
            + "; ".join(f"{x['ticker']} {x['date']} {x['getiri_pct']:+.1f}%" for x in b)
            + " — günlük karar hattı doğrudan besleniyor demektir")

    def test_olcum_evrenindeki_bulgu_GORUNUR_kalir(self, real_cfg, real_con):
        """Düzeltilene kadar her gün görünmeli — sessizce kaybolmamalı."""
        from src import saglik
        b = saglik.duzeltilmemis_kurumsal_tara(real_cfg, real_con)
        if not b:
            return                       # veri düzeltilmişse sorun yok
        assert all(x["ticker"] in {"TSPOR", "CCOLA", "AYGAZ", "HEKTS"} for x in b), \
            ("2026-08-07'de bilinen dört isim dışında YENİ bir vaka çıktı: "
             + "; ".join(f"{x['ticker']} {x['date']}" for x in b))


def test_daily_bootstraps_only_missing_symbol_history(cfg, con, monkeypatch):
    """2026-09-25: yeni BIST30 üyesini 15 barla aylarca bekletme."""
    import pandas as pd
    add_universe(con, "AAA")
    add_universe(con, "BBB")
    add_bars(con, "AAA", [("2026-09-01",100.,101.,99.,100.,1000.,100.)])
    calls = {}
    def fetch(ticker, config, start):
        calls[ticker] = start
        return pd.DataFrame()
    monkeypatch.setattr(prices.yf, 'fetch_bars', fetch)
    monkeypatch.setattr(prices, '_store_bars', lambda *a:0)
    monkeypatch.setattr(prices, 'purge_phantom_bars', lambda *a:{'silinen':0})
    monkeypatch.setattr(prices, 'purge_incomplete_bars', lambda *a:{'silinen_bar':0,'silinen_endeks':0})
    monkeypatch.setattr(prices, 'assess_quality', lambda *a,**k:[])
    result=prices.daily(cfg,con,tickers=['AAA','BBB'])
    assert calls['AAA']==result['start']
    assert calls['BBB']==cfg['sources']['yf']['backfill_start']
