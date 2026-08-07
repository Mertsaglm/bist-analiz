"""Sağlık kontrolü — mekanizma testleri.

Bu modül Faz 8'de `cli.cmd_saglik`'ten çıkarıldı (katman disiplini: otonom koşu
CLI'ı import edemez). Buradaki asıl test **bar tazeliği**: otomasyonun tek
gerçek dış-dünya kontrolü odur.
"""

from __future__ import annotations

from datetime import date

import pytest

from src import saglik as sag
from tests.conftest import add_universe


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
