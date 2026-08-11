"""Sağlık kontrolü — mekanizma testleri.

Bu modül Faz 8'de `cli.cmd_saglik`'ten çıkarıldı (katman disiplini: otonom koşu
CLI'ı import edemez). Buradaki asıl test **bar tazeliği**: otomasyonun tek
gerçek dış-dünya kontrolü odur.
"""

from __future__ import annotations

from datetime import date

import pytest

from src import saglik as sag
from tests.conftest import add_index, add_universe, is_gunleri


def _veri_kur(con, cfg, tarihler: list[str], ticker="THYAO"):
    """bars + indicator + data_quality + universe — kontrollerin beklediği asgari."""
    from src import db

    add_universe(con, ticker, sector="ulasim")
    db.upsert_many(
        con, "bars_daily",
        ["ticker", "date", "o", "h", "l", "c", "v", "c_tr", "turnover_try",
         "source", "ingested_utc"],
        [(ticker, d, 10.0, 11.0, 9.0, 10.0, 1000.0, 10.0, 1e9, "test", "now")
         for d in tarihler])
    db.upsert_many(
        con, "indicator_daily", ["ticker", "date", "set_version", "computed_utc"],
        [(ticker, d, cfg["gostergeler"]["set_version"], "now") for d in tarihler])
    db.upsert_many(
        con, "data_quality", ["ticker", "date", "ok"],
        [(ticker, tarihler[-1], 1)])


class TestBarTazeligi:
    """⚠ NE OLURDU: 1-3. kontroller göstergeyi/kaliteyi `MAX(bars_daily.date)`e
    kıyaslıyor. Barlar bayatlarsa `asof` da bayatlar ve HEPSİ tutarlı görünür —
    kontroller birbirini doğrular, hiçbiri dış dünyaya bakmaz. Otomasyonda
    karşılığı: veri gelmediği gün DÜNKÜ rapor bugünmüş gibi bildirilir."""

    def test_bir_seans_geride_UYARI(self, cfg, con, monkeypatch):
        from src.calendar_bist import BistCalendar
        _veri_kur(con, cfg, ["2026-07-29", "2026-07-30"])
        monkeypatch.setattr(BistCalendar, "last_closed_session",
                            lambda self, ts=None: date(2026, 7, 31))
        monkeypatch.setattr(BistCalendar, "trading_days_between",
                            lambda self, a, b: 1)

        s = sag.kontrol(cfg, con)
        satir = [b for b in s["bulgular"] if b[1] == "bar tazeliği"][0]
        assert satir[0] == sag.UYARI
        assert "1 seans geride" in satir[2]
        # Not: koşunun TOPLAM çıkış kodu burada iddia EDİLMEZ — minimal
        # fixture'da başka kontroller de düşer ve test o gürültüye bağlanırdı.
        # Çıkış kodu mantığının kendi testi var (TestCikisKodu).

    def test_iki_seans_geride_KRITIK(self, cfg, con, monkeypatch):
        """Bir seans gecikme olağan (yfinance), iki seans değil."""
        from src.calendar_bist import BistCalendar
        _veri_kur(con, cfg, ["2026-07-29", "2026-07-30"])
        monkeypatch.setattr(BistCalendar, "last_closed_session",
                            lambda self, ts=None: date(2026, 8, 3))
        monkeypatch.setattr(BistCalendar, "trading_days_between",
                            lambda self, a, b: 2)

        s = sag.kontrol(cfg, con)
        satir = [b for b in s["bulgular"] if b[1] == "bar tazeliği"][0]
        assert satir[0] == sag.KRITIK

    def test_guncelse_OK(self, cfg, con, monkeypatch):
        from src.calendar_bist import BistCalendar
        _veri_kur(con, cfg, ["2026-07-29", "2026-07-30"])
        monkeypatch.setattr(BistCalendar, "last_closed_session",
                            lambda self, ts=None: date(2026, 7, 30))
        monkeypatch.setattr(BistCalendar, "trading_days_between",
                            lambda self, a, b: 0)

        s = sag.kontrol(cfg, con)
        satir = [b for b in s["bulgular"] if b[1] == "bar tazeliği"][0]
        assert satir[0] == sag.OK


class TestCikisKodu:
    """0 temiz · 1 uyarı · 2 KRİTİK — otomasyonun kapısı bu sayı."""

    def test_kritik_2_dondurur(self):
        assert sag.cikis_kodu({"kritik": [("K", "a", "b")], "uyari": []}) == 2

    def test_yalniz_uyari_1_dondurur(self):
        assert sag.cikis_kodu({"kritik": [], "uyari": [("U", "a", "b")]}) == 1

    def test_temiz_0_dondurur(self):
        assert sag.cikis_kodu({"kritik": [], "uyari": []}) == 0

    def test_kritik_uyariyi_EZER(self):
        assert sag.cikis_kodu({"kritik": [("K", "a", "b")],
                               "uyari": [("U", "c", "d")]}) == 2


class TestTekSatir:
    """Telegram özetine giren hâl — kritik varsa SEBEBİ de görünmeli."""

    def test_kritikte_ad_ve_mesaj_gorunur(self):
        t = sag.tek_satir({"kritik": [(sag.KRITIK, "gösterge tazeliği", "bayat")],
                           "uyari": []})
        assert "🛑" in t and "gösterge tazeliği" in t and "bayat" in t

    def test_uyarida_sayi(self):
        t = sag.tek_satir({"kritik": [], "uyari": [("U", "a", "b"), ("U", "c", "d")]})
        assert "2 uyarı" in t

    def test_temizde_kisa(self):
        assert sag.tek_satir({"kritik": [], "uyari": []}) == "✓ Sağlık temiz"


class TestGostergeKapsamasi:
    def test_eksik_gosterge_KRITIK(self, cfg, con):
        """L-009: gösterge kapsaması düşerse kesitsel yüzdelik sessizce daralır."""
        from src import db
        _veri_kur(con, cfg, ["2026-07-30"], ticker="THYAO")
        # Göstergesi OLMAYAN ikinci bir ticker ekle
        db.upsert_many(
            con, "bars_daily",
            ["ticker", "date", "o", "h", "l", "c", "v", "c_tr", "turnover_try",
             "source", "ingested_utc"],
            [("AKBNK", "2026-07-30", 10.0, 11.0, 9.0, 10.0, 1000.0, 10.0,
              1e9, "test", "now")])

        s = sag.kontrol(cfg, con)
        satir = [b for b in s["bulgular"] if b[1] == "gösterge kapsaması"][0]
        assert satir[0] == sag.KRITIK
        assert "1/2" in satir[2]


class TestBicimleme:
    def test_bicimle_tum_bulgulari_basar(self, cfg, con):
        _veri_kur(con, cfg, ["2026-07-30"])
        s = sag.kontrol(cfg, con)
        metin = sag.bicimle(s)
        for _, ad, _ in s["bulgular"]:
            assert ad in metin


class TestKesitselDevreKesici:
    """⚠ REGRESYON KİLİDİ (2026-08-07, Merdiven M6'dan uyarlandı).

    Merdiven'in cümlesi: *"aynı mumda 30'dan fazla AL sinyali gelirse bypass —
    30 hisse aynı anda underpriced olamaz."* Genellenmiş hâli: **kesit tek yöne
    düştüyse bozulan piyasa değil, ölçüm aracıdır.**

    Yakaladığı iki boşluk:
    (a) L-007 "payda sessizce daralır" dedi; bunun aynadaki görüntüsü olan
        "pay sessizce şişer" hiçbir yerde kontrol edilmiyordu.
    (b) L-008 "simetriğini ara": rejim tavanı LLM tarafında HF-23 ile zorlanıyor,
        deterministik plan üretiminde ve `signal` alanında hiç zorlanmıyordu.

    Eşikler ÖLÇÜLDÜ (23 asof günü): medyan 2/18 isim, gözlemlenen maks 9/18=%50.
    Tel %60 — kalibrasyon değil, "bu hiç olmadı" çizgisi.
    """

    @staticmethod
    def _plan_gunleri(con, gunler: dict[str, int]):
        """{asof: kaç isim} → plan_options satırları."""
        from src import db
        rows = []
        for asof, n in gunler.items():
            for i in range(n):
                t = f"T{i:02d}"
                rows.append((f"{t}-{asof}-A", asof, t, "dogrudan", "{}", "now"))
        db.upsert_many(con, "plan_options",
                       ["plan_id", "asof", "ticker", "kind", "payload", "created_utc"],
                       rows)

    @staticmethod
    def _evren(con, n: int):
        for i in range(n):
            add_universe(con, f"T{i:02d}", sector=f"s{i}")

    def _bul(self, cfg, con, ad: str):
        return next(b for b in sag.kontrol(cfg, con)["bulgular"] if b[1] == ad)

    def test_evrenin_cogunda_plan_UYARI(self, cfg, con):
        self._evren(con, 10)
        self._plan_gunleri(con, {"2026-07-30": 7})        # 7/10 = %70 > %60
        seviye, _, mesaj = self._bul(cfg, con, "plan üretim oranı")
        assert seviye == sag.UYARI, mesaj
        assert "telini AŞTI" in mesaj

    def test_normal_oranda_SESSIZ(self, cfg, con):
        """Kontrol grubu: tel her gün ateşliyorsa tel değil, gürültüdür."""
        self._evren(con, 10)
        self._plan_gunleri(con, {"2026-07-30": 2})        # %20 — gözlenen medyan
        seviye, _, _ = self._bul(cfg, con, "plan üretim oranı")
        assert seviye == sag.OK

    def test_payda_MESAJDA_gorunur(self, cfg, con):
        """L-007: bir oran yazıyorsan paydasını da yaz."""
        self._evren(con, 10)
        self._plan_gunleri(con, {"2026-07-30": 3})
        _, _, mesaj = self._bul(cfg, con, "plan üretim oranı")
        assert "3/10" in mesaj and "plan gününde ort." in mesaj

    def test_ON_KAYIT_tetikleyicisi_kosulabilir(self, cfg, con):
        """STATE.md Backlog'undaki '20 günde ort. <2 plan' artık KOD."""
        self._evren(con, 10)
        n = int(cfg["saglik"]["kesit"]["pencere_gun"])
        self._plan_gunleri(con, {f"2026-01-{i+1:02d}": 1 for i in range(n)})
        seviye, _, mesaj = self._bul(cfg, con, "plan üretim oranı")
        assert seviye == sag.UYARI
        assert "ön kayıt" in mesaj and "on-kayit-seviye-02" in mesaj

    def test_pencere_dolmadan_on_kayit_tetiklenmez(self, cfg, con):
        """Az günle tetiklemek yanlış alarm üretir — pencere DOLMALI."""
        self._evren(con, 10)
        self._plan_gunleri(con, {f"2026-01-{i+1:02d}": 1 for i in range(3)})
        seviye, _, _ = self._bul(cfg, con, "plan üretim oranı")
        assert seviye == sag.OK

    def test_plan_options_bossa_TEMIZ_DEMEZ(self, cfg, con):
        self._evren(con, 10)
        seviye, _, mesaj = self._bul(cfg, con, "plan üretim oranı")
        assert "ölçülecek gün yok" in mesaj

    # ---------------------------------------------------------- sinyal dağılımı
    @staticmethod
    def _tahminler(con, sinyaller: list[str], asof="2026-07-30"):
        from src import db
        db.upsert_many(
            con, "llm_runs",
            ["run_id", "asof", "tool", "bundle_sha", "output_path",
             "audit_passed", "created_utc"],
            [("r1", asof, "test-model", "sha", "/dev/null", 1, "now")])
        db.upsert_many(
            con, "predictions",
            ["prediction_id", "run_id", "asof", "ticker", "signal", "action",
             "confidence", "confidence_p", "factor_set_version", "weights_hash",
             "indicator_set_version", "regime", "thesis", "counter_scenario",
             "key_risk", "falsifier", "close_at_asof", "created_utc"],
            [(f"p{i}", "r1", asof, f"T{i:02d}", s, "izle", "orta", 0.5,
              "v1", "h", "v1", "neutral", "t", "c", "k", "f", 10.0, "now")
             for i, s in enumerate(sinyaller)])

    def test_sinyallerin_cogu_tek_yonde_UYARI(self, cfg, con):
        """HF-23 `plan_sec` SAYISINI kapıyor; `signal` alanına hiç tavan yoktu."""
        self._evren(con, 12)
        self._tahminler(con, ["buy"] * 10 + ["hold"] * 2)     # %83 > %70
        seviye, _, mesaj = self._bul(cfg, con, "sinyal dağılımı")
        assert seviye == sag.UYARI and "telini AŞTI" in mesaj

    def test_dengeli_dagilim_SESSIZ(self, cfg, con):
        self._evren(con, 12)
        self._tahminler(con, ["buy"] * 3 + ["hold"] * 5 + ["reduce"] * 4)
        seviye, _, _ = self._bul(cfg, con, "sinyal dağılımı")
        assert seviye == sag.OK

    def test_kucuk_paydada_ORAN_DEGERLENDIRILMEZ(self, cfg, con):
        """Replay koşuları n=1-2 üretiyor; orada %100 boğa anlamsızdır."""
        self._evren(con, 3)
        self._tahminler(con, ["buy", "buy"])                 # n=2 < min_n
        seviye, _, mesaj = self._bul(cfg, con, "sinyal dağılımı")
        assert seviye == sag.OK
        assert "DEĞERLENDİRİLMEDİ" in mesaj, \
            "küçük paydada 'temiz' demek, ölçmediğini ölçmüş gibi göstermektir"

    def test_ayi_tarafi_da_TEL_ATEŞLER(self, cfg, con):
        """Tel simetrik olmalı — yalnız boğa tarafını kapamak yarım savunmadır."""
        self._evren(con, 12)
        self._tahminler(con, ["sell"] * 10 + ["hold"] * 2)
        seviye, _, _ = self._bul(cfg, con, "sinyal dağılımı")
        assert seviye == sag.UYARI



# ═══════════════════════════════════════════════════════════════════════════
# KİLİTLENME — 2026-08-11 denetiminin en pahalı bulgusu (L-016)
# ═══════════════════════════════════════════════════════════════════════════
def _kosu_ekle(con, cfg, tarih_tr: str, durum: str = "tamam") -> str:
    from src import journal
    kid = journal.kosu_basla(cfg, con, tur="gunluk", tarih_tr=tarih_tr)
    journal.kosu_bitir(con, kid, durum=durum)
    return kid


def _tahmin_ekle(con, asof: str, *, action: str = "izle") -> None:
    from src import db
    db.upsert_many(con, "llm_runs",
                   ["run_id", "asof", "tool", "bundle_sha", "output_path",
                    "audit_passed", "created_utc"],
                   [(f"r-{asof}", asof, "test", "s", "", 1, "now")])
    db.upsert_many(
        con, "predictions",
        ["prediction_id", "run_id", "asof", "ticker", "signal", "action",
         "confidence", "confidence_p", "factor_set_version", "weights_hash",
         "indicator_set_version", "regime", "thesis", "counter_scenario",
         "key_risk", "falsifier", "close_at_asof", "created_utc"],
        [(f"p-{asof}", f"r-{asof}", asof, "THYAO", "hold", action, "orta", 0.5,
          "v1", "h", "v1", "neutral", "t", "c", "k", "f", 10.0, "now")])


def _takvim_sabitle(monkeypatch, son_seans: str):
    """`last_closed_session` duvar saatine bakar; testte sabitlenir."""
    from src.calendar_bist import BistCalendar
    monkeypatch.setattr(BistCalendar, "last_closed_session",
                        lambda self, ts=None: date.fromisoformat(son_seans))


class TestKapiKendiCiktisinaBakmaz:
    """⚠⚠ EN ÖNEMLİ REGRESYON KİLİDİ — bir KİLİTLENMENİN davranışsal kilidi.

    NE OLMUŞTU (2026-08-06 → 2026-08-11, dört işlem günü):
      1. GitHub runner günlük işi almadı; koşu HİÇ başlamadı, Telegram sessiz.
      2. Ertesi gün L-015'in "atlanan koşu" kontrolü devreye girdi. O kontrol
         `MAX(predictions.asof)`e bakıyor ve fark ≥2 ise **KRİTİK** diyordu.
      3. `otonom.gunluk` KRİTİK'te durur ve `predictions` o durduğu noktanın
         ARKASINDA yazılır. Yani kapının açılması için gereken şey, kapının
         arkasındaydı.
      4. Fark her gün 1 arttı. Sistem veri çekmeye ve commit atmaya devam etti,
         **sıfır analiz üretti** ve her gün aynı 🛑 mesajını gönderdi.

    Bu sınıf tek bir kuralı davranışla sabitler: **JOURNAL'IN DURUMU KAPIYI
    KAPATAMAZ.** Kaynak metni değil davranışı sınar (AGENTS.md §12) — biri
    yarın yeni bir kontrol yazıp `predictions`e bakarak KRİTİK dönerse burası
    kırmızı yanar.
    """

    @staticmethod
    def _kritikler(cfg, con, bugun):
        return {b[1] for b in sag.kontrol(cfg, con, bugun_tr=bugun)["kritik"]}

    @pytest.mark.parametrize("gerilik", [0, 1, 2, 3, 5, 10, 30])
    def test_JOURNALIN_YASI_kapiyi_DEGISTIRMEZ(self, cfg, con, monkeypatch, gerilik):
        """⚠ Kilidin kalbi — DİFERANSİYEL test.

        Mutlak bir "hiç KRİTİK olmasın" iddiası fixture'ın eksikliklerini de
        yakalar ve asıl soruyu bulanıklaştırır. Sorulan tek şey şu: **journal'ın
        yaşı kapı kümesini değiştiriyor mu?** Eski davranışta `gerilik>=2`
        kümeye `atlanan koşu` ekliyordu ve fark her gün büyüdüğü için kilit
        KALICIYDI.
        """
        g = is_gunleri(40, "2026-06-01")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _takvim_sabitle(monkeypatch, g[-1])

        taze = self._kritikler(cfg, con, g[-1])          # journal BOŞ
        _tahmin_ekle(con, g[-1 - gerilik])               # journal `gerilik` gün eski
        eski = self._kritikler(cfg, con, g[-1])

        assert eski == taze, (
            f"{gerilik} gün eski journal kapı kümesini değiştirdi: "
            f"{sorted(eski - taze)} eklendi")

    def test_BOS_journal_gozlem_disinda_KRITIK_URETMEZ(self, cfg, con, monkeypatch):
        """Hiç tahmin yokken hiçbir GÖZLEM kontrolü kapıyı kapatmamalı —
        yoksa sistem ilk gününde hiç başlayamaz."""
        g = is_gunleri(5, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _takvim_sabitle(monkeypatch, g[-1])
        s = sag.kontrol(cfg, con, bugun_tr=g[-1])
        assert not (self._kritikler(cfg, con, g[-1]) & sag.GOZLEM_KONTROLLERI), s["kritik"]

    def test_GOZLEM_kontrolleri_KRITIK_seviyesine_CIKAMAZ(self, cfg, con, monkeypatch):
        """Yapısal kilit: `ekle_gozlem` şiddeti UYARI'da tavanlar. Bir gözlem
        kontrolü ileride `return KRITIK, ...` yazsa bile sistem durmaz."""
        g = is_gunleri(40, "2026-06-01")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _tahmin_ekle(con, g[0])                      # kadim bir analiz
        _kosu_ekle(con, cfg, g[0])                   # kadim bir koşu
        _takvim_sabitle(monkeypatch, g[-1])
        s = sag.kontrol(cfg, con, bugun_tr=g[-1])
        gozlem = [b for b in s["bulgular"] if b[1] in sag.GOZLEM_KONTROLLERI]
        assert gozlem, "gözlem kontrolleri hiç çalışmadı — test kendini kandırıyor"
        assert all(b[0] != sag.KRITIK for b in gozlem), gozlem

    def test_gozlem_kontrolu_KUMEYE_yazilmadan_eklenemez(self, cfg, con):
        """Sınıflandırılmamış bir kontrol sessizce gözlem sayılmasın."""
        assert "atlanan koşu" in sag.GOZLEM_KONTROLLERI
        assert "bar tazeliği" not in sag.GOZLEM_KONTROLLERI, (
            "veri bütünlüğü kontrolü gözleme kaydırılırsa kapı işlevsizleşir")


class TestAtlananKosu:
    """⚠ REGRESYON KİLİDİ — GERÇEK OLAY 2026-08-06 (L-015) + düzeltmesi (L-016).

    Sayaç artık `otonom_kosu` heartbeat'inden okunur. O kayıt koşunun EN
    BAŞINDA, kapıdan ÖNCE yazılır — durdurulmuş bir koşu bile "koştum" der.
    Böylece sayaç kapının önünde ilerler ve kilit KURULAMAZ.
    """

    def _bul(self, cfg, con, bugun):
        return next(b for b in sag.kontrol(cfg, con, bugun_tr=bugun)["bulgular"]
                    if b[1] == "atlanan koşu")

    def test_her_seans_kosulmussa_TEMIZ(self, cfg, con, monkeypatch):
        g = is_gunleri(5, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _kosu_ekle(con, cfg, g[-2])                  # dünkü koşu var
        _takvim_sabitle(monkeypatch, g[-1])
        assert self._bul(cfg, con, g[-1])[0] == sag.OK

    def test_bir_seans_atlanmissa_UYARI(self, cfg, con, monkeypatch):
        g = is_gunleri(5, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _kosu_ekle(con, cfg, g[-3])                  # aradaki seans koşusuz
        _takvim_sabitle(monkeypatch, g[-1])
        seviye, _, mesaj = self._bul(cfg, con, g[-1])
        assert seviye == sag.UYARI
        assert "1 seans" in mesaj

    def test_KAC_seans_atlanirsa_atlansin_UYARI_KALIR(self, cfg, con, monkeypatch):
        """Kilit tam olarak buradaydı: eski kodda fark ≥2 KRİTİK'ti ve fark
        her gün büyüdüğü için sistem bir daha asla açılamıyordu."""
        g = is_gunleri(20, "2026-07-01")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _kosu_ekle(con, cfg, g[0])
        _takvim_sabitle(monkeypatch, g[-1])
        seviye, _, _ = self._bul(cfg, con, g[-1])
        assert seviye == sag.UYARI

    def test_BUGUNKU_kosu_sayilmaz(self, cfg, con, monkeypatch):
        """Kontrol koşunun İÇİNDEN çağrılır ve bugünün heartbeat'i zaten
        yazılmıştır. Onu saymak "hiç boşluk yok" derdi — soru "bugün koştum
        mu?" değil, "bugüne kadar bir gün atladım mı?"."""
        g = is_gunleri(5, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _kosu_ekle(con, cfg, g[-3])                  # boşluk VAR
        _kosu_ekle(con, cfg, g[-1])                  # bugünün koşusu (sayılmamalı)
        _takvim_sabitle(monkeypatch, g[-1])
        assert self._bul(cfg, con, g[-1])[0] == sag.UYARI

    def test_heartbeat_bossa_ALARM_VERMEZ(self, cfg, con, monkeypatch):
        """Yeni kurulumda kayıt yokluğu arıza değildir; geçmişi UYDURMAK ise
        tam da bu kontrolün engellemeye çalıştığı şey olurdu."""
        g = is_gunleri(4, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _takvim_sabitle(monkeypatch, g[-1])
        seviye, _, mesaj = self._bul(cfg, con, g[-1])
        # `tamam=True` bulguyu OK'a çevirir — "kayıt yok" bir arıza değil.
        assert seviye == sag.OK and "heartbeat boş" in mesaj

    def test_DURDURULAN_kosu_da_KOSMUS_sayilir(self, cfg, con, monkeypatch):
        """"Koştum" ile "iş ürettim" ayrı iki olgu (L-003). Durdurulan koşu
        birincisini kanıtlar; ikincisini `analizsiz gün` sorar."""
        g = is_gunleri(5, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _kosu_ekle(con, cfg, g[-2], durum="durduruldu")
        _takvim_sabitle(monkeypatch, g[-1])
        seviye, _, mesaj = self._bul(cfg, con, g[-1])
        assert seviye == sag.OK and "durduruldu" in mesaj

    def test_mesaj_NEREYE_BAKILACAGINI_yazar(self, cfg, con, monkeypatch):
        """L-011: uyarıyı gören kişi nereye bakacağını mesajdan öğrenmeli."""
        g = is_gunleri(5, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _kosu_ekle(con, cfg, g[-3])
        _takvim_sabitle(monkeypatch, g[-1])
        _, _, mesaj = self._bul(cfg, con, g[-1])
        assert "Telegram bildirimi de ÇIKMAZ" in mesaj
        assert "Actions geçmişini" in mesaj


class TestAnalizsizGun:
    """Koşu ayakta ama analist üretmiyor — `atlanan koşu`dan AYRI soru.

    İkisini tek satıra sıkıştırmak (L-003) hangisinin bozuk olduğunu görünmez
    kılardı: runner mı düştü, LLM zinciri mi tükendi?
    """

    def _bul(self, cfg, con, bugun):
        return next(b for b in sag.kontrol(cfg, con, bugun_tr=bugun)["bulgular"]
                    if b[1] == "analizsiz gün")

    def test_bir_gun_gerilik_NORMALDIR(self, cfg, con, monkeypatch):
        """Sağlık adımı zincirde analistten ÖNCE koşar (adım 6 vs 8); bugünün
        tahmini henüz yazılmamıştır ve bu bir arıza değildir."""
        g = is_gunleri(5, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _tahmin_ekle(con, g[-2])
        _takvim_sabitle(monkeypatch, g[-1])
        assert self._bul(cfg, con, g[-1])[0] == sag.OK

    def test_iki_gun_analizsizse_UYARI(self, cfg, con, monkeypatch):
        g = is_gunleri(6, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _tahmin_ekle(con, g[-3])
        _takvim_sabitle(monkeypatch, g[-1])
        seviye, _, mesaj = self._bul(cfg, con, g[-1])
        assert seviye == sag.UYARI and "analist" in mesaj


class TestYarimBar:
    """⚠ REGRESYON KİLİDİ — GERÇEK OLAY 2026-07-29.

    Paket TR saatiyle 13:29'da, SEANS SÜRERKEN üretildi. yfinance'in o anki
    kısmi barı "kapanış" sanıldı ve 18 tahmin journal'a öyle yazıldı:
    18/18 isimde sapma, ortalama %1.21, maksimum %2.47 (AKBNK 64.90 → 63.30).
    Journal DEĞİŞMEZ olduğu için o kayıtlar kalıcı olarak yarım veriye dayanıyor.

    Ölçüt Faz 1'den beri vardı (`last_closed_session`) ve kimse çağırmıyordu.
    """

    def _bul(self, cfg, con, bugun):
        return next(b for b in sag.kontrol(cfg, con, bugun_tr=bugun)["bulgular"]
                    if b[1] == "yarım bar")

    def test_kapanmis_seans_TEMIZ(self, cfg, con, monkeypatch):
        g = is_gunleri(4, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _takvim_sabitle(monkeypatch, g[-1])
        assert self._bul(cfg, con, g[-1])[0] == sag.OK

    def test_KAPANMAMIS_seansin_bari_KRITIKTIR(self, cfg, con, monkeypatch):
        """Bu KAPI kontrolüdür ve olması gereken de budur: yarım barla üretilen
        her gösterge/plan/tahmin yanlıştır ve journal onu geri alamaz."""
        g = is_gunleri(4, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _takvim_sabitle(monkeypatch, g[-2])          # son bar seans kapanmadan
        seviye, _, mesaj = self._bul(cfg, con, g[-1])
        assert seviye == sag.KRITIK
        assert "kapanmamış seansın barı" in mesaj

    def test_kapi_KENDINI_ONARIR(self, cfg, con, monkeypatch):
        """KRİTİK olması meşru çünkü koşunun KENDİSİ düzeltir: `prices.daily`
        içindeki `purge_incomplete_bars` sağlık adımından ÖNCE koşar. Yani bu
        kapı, `atlanan koşu`nun aksine kilitlenemez."""
        from src import prices
        g = is_gunleri(4, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _takvim_sabitle(monkeypatch, g[-2])
        assert self._bul(cfg, con, g[-1])[0] == sag.KRITIK
        prices.purge_incomplete_bars(cfg, con)       # koşunun 2. adımı
        assert self._bul(cfg, con, g[-1])[0] == sag.OK


class TestAcikPlan:
    """Journal'da açık plan varken portföy boşsa kontenjan KÖRDÜR.

    ÖLÇÜLDÜ (2026-08-11): 9 açık `plan_sec` varken `holdings` 0 satırdı ve
    rapor "Kontenjan: 0/2 pozisyon dolu" basıyordu. KRDMD 5 gün üst üste
    seçildi; planlar harfiyen uygulansa tek isimde %26.9 birikirdi (rejim
    tavanı TOPLAM %20 hisseydi).
    """

    def _bul(self, cfg, con, bugun):
        return next(b for b in sag.kontrol(cfg, con, bugun_tr=bugun)["bulgular"]
                    if b[1] == "açık plan")

    def test_acik_plan_yokken_TEMIZ(self, cfg, con, monkeypatch):
        g = is_gunleri(4, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _takvim_sabitle(monkeypatch, g[-1])
        assert self._bul(cfg, con, g[-1])[0] == sag.OK

    def test_acik_plan_VARKEN_portfoy_BOSSA_UYARI(self, cfg, con, monkeypatch):
        g = is_gunleri(4, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _tahmin_ekle(con, g[-2], action="plan_sec")
        _takvim_sabitle(monkeypatch, g[-1])
        seviye, _, mesaj = self._bul(cfg, con, g[-1])
        assert seviye == sag.UYARI and "1 açık plan" in mesaj

    def test_portfoy_DOLUYSA_TEMIZ(self, cfg, con, monkeypatch):
        from src import journal
        g = is_gunleri(4, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _tahmin_ekle(con, g[-2], action="plan_sec")
        journal.set_holding(con, "THYAO", 100, 10.0)
        _takvim_sabitle(monkeypatch, g[-1])
        assert self._bul(cfg, con, g[-1])[0] == sag.OK


class TestCiktiMuhru:
    """⚠ REGRESYON KİLİDİ — GERÇEK OLAY 2026-07-30.

    `llm_runs.output_path` "bu tahmini üreten çıktı şu dosyadadır" diyordu.
    Doğru DEĞİLDİ: kayıt `gemini-3.6-flash`, dosya `gemini-3.5-flash`'a aitti
    ve TUPRS'ta hem sinyal (hold vs accumulate) hem seçilen plan (A vs B)
    farklıydı. Sebep: yol yalnız TARİHE bağlıydı, aynı günün ikinci turu
    dosyayı journal'a haber vermeden eziyordu.
    """

    def _bul(self, cfg, con, bugun):
        return next(b for b in sag.kontrol(cfg, con, bugun_tr=bugun)["bulgular"]
                    if b[1] == "çıktı mührü")

    def _kur(self, cfg, con, monkeypatch):
        g = is_gunleri(4, "2026-08-03")
        _veri_kur(con, cfg, g)
        add_index(con, "XU100", g)
        _takvim_sabitle(monkeypatch, g[-1])
        return g

    def test_muhurlenen_cikti_DOGRULANIR(self, cfg, con, monkeypatch):
        from src import journal, util
        g = self._kur(cfg, con, monkeypatch)
        asof = g[-1]
        util.write_json(f"{cfg['paths']['llm_out_dir']}/{asof}/analysis.json",
                        {"tool": "test", "stocks": []})
        rid = journal.create_run(cfg, con, asof=asof, tool="test", bundle_sha="s")
        assert journal.muhurle_cikti(cfg, con, run_id=rid, asof=asof)["ok"]
        assert self._bul(cfg, con, g[-1])[0] == sag.OK

    def test_EZILEN_cikti_YAKALANIR(self, cfg, con, monkeypatch):
        """Mühürden sonra dosya değişirse mühür tutmaz — 2026-07-30'un tam
        olarak yakalanamamış hâli."""
        from src import journal, util
        g = self._kur(cfg, con, monkeypatch)
        asof = g[-1]
        util.write_json(f"{cfg['paths']['llm_out_dir']}/{asof}/analysis.json",
                        {"tool": "test", "stocks": []})
        rid = journal.create_run(cfg, con, asof=asof, tool="test", bundle_sha="s")
        journal.muhurle_cikti(cfg, con, run_id=rid, asof=asof)
        # Başka bir koşu dosyayı ezdi
        util.write_json(f"{cfg['paths']['llm_out_dir']}/{asof}/{rid}.json",
                        {"tool": "BASKA-MODEL", "stocks": []})
        seviye, _, mesaj = self._bul(cfg, con, g[-1])
        assert seviye == sag.UYARI and "mühür tutmuyor" in mesaj

    def test_MUHURSUZ_kayit_DOGRU_degil_DOGRULANAMAZ_der(self, cfg, con, monkeypatch):
        """v11 öncesi kayıtlara geçmişe dönük sha yazmak, ezilmiş bir dosyayı
        doğruymuş gibi mühürlemek olurdu."""
        from src import db
        g = self._kur(cfg, con, monkeypatch)
        db.upsert_many(con, "llm_runs",
                       ["run_id", "asof", "tool", "bundle_sha", "output_path",
                        "audit_passed", "created_utc"],
                       [("eski", g[-1], "test", "s", "llm/out/x/analysis.json",
                         1, "now")])
        seviye, _, mesaj = self._bul(cfg, con, g[-1])
        assert seviye != sag.KRITIK
        assert "doğrulanamaz" in mesaj
