"""Sıralı eylem listesi testleri — ADR #015.

⚠ Bu dosyanın EN ÖNEMLİ testi `test_SKOR_YOK`: sıra bir GETİRİ iddiası
taşımamalı. Merdiven'in ΔEV mantığı bir beklenen-getiri karşılaştırmasıdır;
bizim beklenen getirimiz YOK ve olmadığı ölçüldü (ADR #007). Aynı formülü
"skor" diye kurmak, ölçülmemiş bir kenar iddiasını arka kapıdan sokmak olur.
"""

from __future__ import annotations

from src import eylem


def _e(ticker, **kw):
    """Paket `evren` girdisi — yalnız sıralamanın okuduğu alanlar."""
    d = {
        "ticker": ticker,
        "veri_kalitesi": {"ok": True, "uyarilar": []},
        "limit_durumu": {"durum": "serbest"},
        "bilanco_penceresi": {"durum": "kapali", "bildirimler": []},
        "aktif_vetolar": [],
        "plan_menusu": [],
    }
    d.update(kw)
    return d


def _plan(pid="X-A", zone="in_zone", rr_net=1.8, kayip=0.5):
    return [{"plan_id": pid, "entry_zone_status": zone,
             "max_loss_pct_of_portfolio": kayip,
             "targets": [{"price": 100.0, "rr": 2.0, "rr_net": rr_net}]}]


def _bundle(evren, *, maks=5, etiket="neutral"):
    return {"evren": evren,
            "rejim": {"etiket": etiket,
                      "pozisyon_politikasi": {"maks_pozisyon": maks,
                                              "nakit_pct": 40.0}}}


class TestSira:
    def test_temiz_plan_GIR_olur(self):
        r = eylem.siralama(_bundle([_e("AAA", plan_menusu=_plan())]))
        assert [x.ticker for x in r["gir"]] == ["AAA"]
        assert r["gir"][0].hazir

    def test_above_zone_plan_BEKLEr(self):
        r = eylem.siralama(_bundle([_e("AAA", plan_menusu=_plan(zone="above_zone"))]))
        assert not r["gir"] and [x.ticker for x in r["izle"]] == ["AAA"]

    def test_kilitli_isim_ENGELLI(self):
        r = eylem.siralama(_bundle([
            _e("AAA", plan_menusu=_plan(),
               limit_durumu={"durum": "kilitli", "yon": "tavan"})]))
        assert not r["gir"]
        assert [x.ticker for x in r["engelli"]] == ["AAA"]
        assert "kilitli" in r["engelli"][0].engeller[0]

    def test_azalt_sinyali_EN_USTE(self, ):
        """Ölçüldü: alt kuyruk üst kuyruğun ~1.8 katı ve açığa satamazsın."""
        r = eylem.siralama(
            _bundle([_e("AAA", plan_menusu=_plan()), _e("BBB")]),
            holdings={"BBB": {"qty": 10}},
            analiz=[{"ticker": "BBB", "signal": "sell", "thesis": "t"}])
        assert [x.ticker for x in r["azalt"]] == ["BBB"]

    def test_bilanco_penceresi_GIRIS_i_geri_iter(self):
        r = eylem.siralama(_bundle([
            _e("AAA", plan_menusu=_plan()),
            _e("BBB", plan_menusu=_plan(pid="B-A"),
               bilanco_penceresi={"durum": "acik", "bildirimler": [{}, {}]})]))
        assert [x.ticker for x in r["gir"]] == ["AAA"]
        assert [x.ticker for x in r["izle"]] == ["BBB"]

    def test_aktif_veto_GIRIS_i_geri_iter(self):
        r = eylem.siralama(_bundle([
            _e("AAA", plan_menusu=_plan(),
               aktif_vetolar=[{"veto_code": "haber_riski",
                               "kalan_islem_gunu": 2}])]))
        assert not r["gir"] and r["izle"]
        assert "haber_riski" in r["izle"][0].gerekce[0]

    def test_BILINMIYOR_risk_yok_SAYILMAZ(self):
        """L-007: bilmemek, risk olmadığı anlamına gelmez."""
        r = eylem.siralama(_bundle([
            _e("AAA", plan_menusu=_plan(),
               bilanco_penceresi={"durum": "bilinmiyor", "bildirimler": []})]))
        assert not r["gir"], "bilinmiyor sessizce 'temiz' sayıldı"
        assert "BİLİNMİYOR" in r["izle"][0].gerekce[0]


class TestKontenjan:
    def test_tavan_doluysa_YENI_GIRIS_onerilmez(self):
        r = eylem.siralama(
            _bundle([_e("AAA", plan_menusu=_plan()), _e("BBB")], maks=1),
            holdings={"BBB": {"qty": 10}})
        assert r["kontenjan"] == 0
        assert not r["gir"], "rejim tavanı doluyken yeni giriş önerildi"
        aaa = next(x for x in r["izle"] if x.ticker == "AAA")
        assert any("tavanı DOLU" in g for g in aaa.gerekce)

    def test_kontenjan_varsa_giris_onerilir(self):
        r = eylem.siralama(
            _bundle([_e("AAA", plan_menusu=_plan()), _e("BBB")], maks=3),
            holdings={"BBB": {"qty": 10}})
        assert r["kontenjan"] == 2 and [x.ticker for x in r["gir"]] == ["AAA"]

    def test_baslik_ile_GRUP_celismez(self):
        """Grubu 'izle' olan bir satır başlığında 'GİR' diyemez.

        İlk sürüm tam bunu yapıyordu ve okuyanı sisteme güvensiz kılıyordu.
        """
        r = eylem.siralama(
            _bundle([_e("AAA", plan_menusu=_plan(),
                        bilanco_penceresi={"durum": "acik", "bildirimler": [{}]})]))
        for x in r["izle"]:
            assert not x.baslik.startswith("GİR")


class TestKenarIddiasiYok:
    def test_SKOR_YOK(self):
        """⚠ ADR #015'in çekirdeği: tek bir birleşik sayı ÜRETİLMEZ.

        Bileşenleri bir skorda toplamak ağırlıklarını uydurmak olurdu ve
        sıralanmış bir sayı, sıralamanın bir şey BİLDİĞİNİ ima eder.
        """
        r = eylem.siralama(_bundle([_e("AAA", plan_menusu=_plan())]))
        alanlar = set(eylem.Eylem.__slots__)
        yasak = {"skor", "score", "ev", "beklenen_getiri", "puan"}
        assert not (alanlar & yasak), f"eylem kaydına skor alanı sızmış: {alanlar & yasak}"
        assert not hasattr(r["gir"][0], "skor")

    def test_siralama_yalniz_GOZLEMLENEN_olgulara_dayanir(self):
        """Sıralama anahtarı bir tahmin fonksiyonu ÇAĞIRMAMALI."""
        import inspect
        kaynak = inspect.getsource(eylem)
        for yasak in ("predict", "forecast", "expected_return", "beklenen_getiri",
                      "confidence_p", "guven_olasilik"):
            assert yasak not in kaynak, \
                f"sıralamaya tahmin/olasılık girdisi sızmış: {yasak}"

    def test_secimi_DEGISTIRMEZ(self):
        """Liste plan üretmez, üretilmişleri sıralar — kapıya dokunmaz."""
        import inspect
        kaynak = inspect.getsource(eylem)
        assert "build_menu" not in kaynak and "build_options" not in kaynak
        assert "min_rr_t1" not in kaynak

    def test_analist_yoksa_bunu_SOYLER(self):
        """Boş azaltma listesi 'azaltacak bir şey yok' anlamına gelmez."""
        r = eylem.siralama(_bundle([_e("AAA")]), holdings={"AAA": {"qty": 1}})
        assert r["analist_var"] is False


# ============================================================ bugünkü veto
class TestBugunkuAnalistKarari:
    """⚠ NE OLMUŞTU (2026-08-15 denetimi): elde-OLMAYAN isimler dalı analist
    çıktısına HİÇ bakmıyordu. `siralama` `analiz` parametresini alıyor ve
    `a = an.get(t)` satırı bile vardı — ama `a` yalnız `holdings` dalında
    okunuyordu ve portföy boştu.

    Okunan tek veto kaynağı `e["aktif_vetolar"]` idi; o da paket üretilirken
    (otonom zincir adım 7) hesaplanır, analist adım 8'de koşar. Yani bugünkü
    veto o listede YAPISAL OLARAK bulunamaz.

    Ölçülen sonuç: 2026-08-14 raporunun §0'ı "🟢 KCHOL — GİR — plan bugün
    tetiklenebilir, ENGEL YOK" yazdı; aynı raporun §2'si ve aynı günün
    Telegram özeti "plan_reddet · VETO rejim_uyumsuz" dedi.

    Aşağıdaki ilk test o günün verisinin BİREBİR kopyasıdır.
    """

    _ANALIZ = [{"ticker": "KCHOL", "signal": "hold", "action": "plan_reddet",
                "veto_code": "rejim_uyumsuz", "thesis": "planlari uygulamiyoruz"}]

    def _bundle_kchol(self):
        return _bundle([_e("KCHOL", plan_menusu=_plan("KCHOL-2026-08-14-A"))],
                       maks=2, etiket="risk-off")

    def test_bugun_reddedilen_plan_GIR_diyemez(self):
        r = eylem.siralama(self._bundle_kchol(), holdings={}, analiz=self._ANALIZ)
        assert r["gir"] == [], "analist reddettiği hâlde 'GİR' önerildi"
        assert [x.ticker for x in r["izle"]] == ["KCHOL"]
        assert any("BUGÜN planı reddetti" in g for g in r["izle"][0].gerekce)
        assert "rejim_uyumsuz" in " ".join(r["izle"][0].gerekce)

    def test_analist_karari_CIKTIYI_DEGISTIRIR(self):
        """Asıl kilit. Eski kodda bu iki çağrı BİREBİR aynı sonucu veriyordu —
        yani analist katmanı eylem listesi için yok hükmündeydi."""
        b = self._bundle_kchol()
        ile = eylem.siralama(b, holdings={}, analiz=self._ANALIZ)
        siz = eylem.siralama(b, holdings={}, analiz=None)
        assert [x.baslik for x in ile["gir"]] != [x.baslik for x in siz["gir"]], (
            "analistin plan_reddet + veto kararı eylem listesini DEĞİŞTİRMİYOR")

    def test_veto_kodu_tek_basina_da_yeter(self):
        """`action` başka olsa bile dolu bir `veto_code` bir risktir."""
        analiz = [{"ticker": "KCHOL", "signal": "hold", "action": "izle",
                   "veto_code": "haber_riski"}]
        r = eylem.siralama(self._bundle_kchol(), holdings={}, analiz=analiz)
        assert r["gir"] == []
        assert any("haber_riski" in g for g in r["izle"][0].gerekce)

    def test_azalt_sinyali_elde_OLMAYAN_ismi_de_geri_iter(self):
        """`avoid` diyen bir analistin planına 'engel yok' denemez."""
        analiz = [{"ticker": "KCHOL", "signal": "avoid", "action": "islem_yok"}]
        r = eylem.siralama(self._bundle_kchol(), holdings={}, analiz=analiz)
        assert r["gir"] == []
        assert any("`avoid`" in g for g in r["izle"][0].gerekce)

    def test_TEMIZ_analist_karari_GIR_i_engellemez(self):
        """Simetri: düzeltme her şeyi 'BEKLE'ye çevirmemeli."""
        analiz = [{"ticker": "KCHOL", "signal": "buy", "action": "plan_sec",
                   "veto_code": None}]
        r = eylem.siralama(self._bundle_kchol(), holdings={}, analiz=analiz)
        assert [x.ticker for x in r["gir"]] == ["KCHOL"]
        assert r["gir"][0].hazir


class TestAnalistAksiyonuGorunur:
    """B-10 KİLİDİ — §0 analistin bugünkü kararını GÖSTERİR.

    ⚠ NE OLUYORDU (2026-08-28 denetimi): `_analist_riskleri` yalnız
    `plan_reddet` ve azalt sinyallerini yazıyordu; `izle` / `islem_yok`
    hiçbir satır üretmiyordu. Ölçülen sonuç — 2026-08-24 raporu §0:

        1. 🟢 **ASELS** — GİR — plan bugün tetiklenebilir, engel yok

    Aynı günün journal kaydı: `ASELS · signal accumulate · action izle`.
    Yani analist SEÇMEMEYİ tercih etmişti ve raporun en çok okunan satırı
    bunu göstermiyordu; "engel yok" cümlesi okuyucuya analistin de itirazı
    olmadığını ima ediyordu.

    L-022 bu sınıfı `plan_reddet` için kapatmıştı; simetriği yazılmamıştı
    (L-008 madde 1: bir parametreyi aldığın her dalda ya kullan ya da
    kullanılmadığını yaz).
    """

    IZLE = [{"ticker": "AAA", "signal": "accumulate", "action": "izle",
             "thesis": "t"}]

    def test_izle_karari_SIRALAMADA_gorunur(self):
        r = eylem.siralama(_bundle([_e("AAA", plan_menusu=_plan())]),
                           analiz=self.IZLE)
        assert r["gir"], "plan GİR listesine hiç girmedi"
        assert r["gir"][0].analist_aksiyon == "izle", \
            "analistin `izle` kararı §0'a hiç taşınmadı"

    def test_izle_karari_SECIMI_DEGISTIRMEZ(self):
        """ADR #015 madde 3: §0 seçimi değiştirmez — `izle` bir ENGEL değildir.

        Bu test bilerek var: düzeltmenin kendisi yeni bir hata doğurabilirdi
        (§11 tuzak 1). `izle`yi `gerekce`ye koymak hem sıralamayı hem
        `gerçekten_gir` koşulunu değiştirir, yani bir RAPOR düzeltmesi sessizce
        bir KARAR değişikliğine dönüşürdü.
        """
        b = _bundle([_e("AAA", plan_menusu=_plan())])
        analizsiz = eylem.siralama(b, analiz=None)
        izleli = eylem.siralama(b, analiz=self.IZLE)
        assert [x.ticker for x in izleli["gir"]] == \
               [x.ticker for x in analizsiz["gir"]], \
            "`izle` kararı GİR listesini değiştirdi — ADR #015 madde 3 ihlali"
        assert izleli["gir"][0].gerekce == analizsiz["gir"][0].gerekce, \
            "`izle` bir RİSK olarak eklenmiş; o bir engel değil, bir olgudur"
        assert izleli["gir"][0].baslik == analizsiz["gir"][0].baslik

    def test_plan_reddet_HALA_risk_olarak_kalir(self):
        """L-022'nin kilidi bozulmamalı: `plan_reddet` RİSKTİR, olgu değil."""
        b = _bundle([_e("AAA", plan_menusu=_plan())])
        r = eylem.siralama(b, analiz=[{"ticker": "AAA", "signal": "hold",
                                       "action": "plan_reddet",
                                       "veto_code": "rejim_uyumsuz",
                                       "thesis": "t"}])
        assert not r["gir"], "veto edilen isim hâlâ GİR diyor (L-022 regresyonu)"
        assert any("planı reddetti" in g for g in r["izle"][0].gerekce)
