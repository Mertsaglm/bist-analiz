"""CLI testleri — KOMUT YÜZEYİ ve ÇIKIŞ KODLARI.

CLI 33 KB'lık en dış kabuk ve tek bir testi yoktu. İki şeyi sabitliyoruz:

**1. Komut yüzeyi.** README'de yazılı her komut gerçekten var mı, alt komut
seçenekleri neler? Bir komutu yeniden adlandırmak dokümandaki her satırı
sessizce yalanlar — ve kullanıcı bunu ancak komutu yazdığında öğrenir.

**2. Çıkış kodları.** Bu projede çıkış kodu bir SÖZLEŞMEDİR, süs değil:

    bist denetle      0 temiz · 1 girdi yok · 2 SERT HATA (journal'a giremez)
    bist kaydet       2 → sert hata var, YAZILMADI
    bist backtest     2 → kapı KAPALI
    bist haber cek    0 temiz · 1 aralık atlandı · 2 KAP hatası
    bist saglik       0 temiz · 1 uyarı · 2 KRİTİK
    bist degerlendir  2 → kaynak karışık, `--tool` şart
    bist revizyon     2 → ön kayıtlı tur GEÇMEDİ

Faz 8'de bu komutlar GitHub Actions'a bağlanacak; orada tek görünen şey çıkış
kodudur. "0 dönen" bir hata, otomasyonda sessiz bozulmadır (LESSONS L-002).

⚠ Her test `cli._cfg`'yi geçici config'e yönlendirir. Aksi halde CLI testleri
kullanıcının GERÇEK veritabanına yazardı — conftest'teki koruma bunu yakalar ama
testin niyeti baştan doğru olmalı.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src import cli, db, util

from tests.conftest import analist_ciktisi, kur_sentetik_evren


@pytest.fixture
def cli_cfg(cfg, con, monkeypatch):
    """`cli._cfg` → geçici config. Veritabanı da açık kalır (dosya var olur)."""
    monkeypatch.setattr(cli, "_cfg", lambda: cfg)
    return cfg


def _kos(*argv: str) -> int:
    return cli.main(list(argv))


# ============================================================ komut yüzeyi
BEKLENEN_KOMUTLAR = {
    "veri": ["backfill", "gunluk", "kalite", "temizle"],
    "evren": ["sync", "tara"],
    "takvim": None,
    "makro": ["backfill", "gunluk", "durum"],
    "gosterge": None,
    "backtest": None,
    "plan": None,
    "gunluk": None,
    "denetle": None,
    "kaydet": None,
    "replay": None,
    "journal": ["durum", "acik"],
    "coz": None,
    "degerlendir": None,
    "rapor": None,
    # `durum` 2026-08-16'da eklendi: KÂĞIT PORTFÖY (ADR #019).
    # Sistem kendi kararlarını 10.000 TL ile takip eder; `ekle/sil`
    # Mert'in ELLE defteri olarak kalır ve simülasyonu EZER.
    "portfoy": ["ekle", "sil", "listele", "durum"],
    "haber": ["cek", "durum", "listele"],
    "saglik": None,
    "seviye": None,
    "teshis": None,
    "revizyon": None,
    # `nobetci` 2026-08-11'de eklendi: koşunun DIŞINDAN bakan gözcü. Ayrı bir
    # alt komut olması şart — aynı işin içinde koşan bir kontrol, o iş hiç
    # başlamazsa konuşamaz (L-015/L-016).
    "otonom": ["gunluk", "haftalik", "nobetci"],
    "bildir": None,
    "db": ["dump", "restore", "durum"],
}


def _alt_parserlar():
    p = cli.build_parser()
    for aksiyon in p._subparsers._group_actions:
        return aksiyon.choices
    return {}


class TestKomutYuzeyi:
    def test_beklenen_komutlarin_HEPSI_var(self):
        assert set(_alt_parserlar()) == set(BEKLENEN_KOMUTLAR), (
            "komut yüzeyi değişti — README ve AGENTS.md'yi de güncelle")

    @pytest.mark.parametrize("komut,secenekler",
                             [(k, v) for k, v in BEKLENEN_KOMUTLAR.items() if v])
    def test_alt_komut_secenekleri_sabit(self, komut, secenekler):
        alt = _alt_parserlar()[komut]
        aksiyon = next(a for a in alt._actions if a.dest == "alt")
        assert list(aksiyon.choices) == secenekler

    @pytest.mark.parametrize("komut", list(BEKLENEN_KOMUTLAR))
    def test_her_komutun_calisacak_fonksiyonu_var(self, komut):
        assert callable(_alt_parserlar()[komut].get_default("fn"))

    @pytest.mark.parametrize("komut", list(BEKLENEN_KOMUTLAR))
    def test_her_komutun_yardim_metni_var(self, komut):
        """Yardımı olmayan komut, olmayan komuttur — kimse bulamaz."""
        p = cli.build_parser()
        aksiyon = next(a for a in p._subparsers._group_actions)
        assert aksiyon._choices_actions, "alt komut yardımları kayboldu"
        yardimlar = {a.dest: a.help for a in aksiyon._choices_actions}
        assert yardimlar.get(komut), komut

    def test_YATIRIM_TAVSIYESI_DEGILDIR_uyarisi_parserda(self):
        """Uyarı `--help` çıktısında görünmeli; yalnız kodda durması yetmez."""
        assert "YATIRIM TAVSİYESİ DEĞİLDİR" in cli.UYARI.upper()
        assert cli.UYARI in cli.build_parser().description

    def test_bilinmeyen_komut_reddedilir(self):
        with pytest.raises(SystemExit) as e:
            cli.main(["olmayan-komut"])
        assert e.value.code == 2

    def test_komut_verilmezse_reddedilir(self):
        with pytest.raises(SystemExit):
            cli.main([])

    def test_gecersiz_alt_komut_reddedilir(self):
        with pytest.raises(SystemExit) as e:
            cli.main(["journal", "olmayan"])
        assert e.value.code == 2

    def test_iptal_130_doner(self, monkeypatch):
        """KeyboardInterrupt standart 130 kodu ile biter — çökme değil."""
        monkeypatch.setattr(cli, "cmd_coz",
                            lambda a: (_ for _ in ()).throw(KeyboardInterrupt()))
        p = cli.build_parser()
        monkeypatch.setattr(cli, "build_parser", lambda: p)
        for aksiyon in p._subparsers._group_actions:
            aksiyon.choices["coz"].set_defaults(fn=cli.cmd_coz)
        assert cli.main(["coz"]) == 130


# ============================================================ çıkış kodları
class TestDenetleCikisKodu:
    def test_paket_yoksa_1(self, cli_cfg, capsys):
        assert _kos("denetle", "--asof", "2026-07-27") == 1
        assert "önce `bist gunluk`" in capsys.readouterr().out

    def test_analist_ciktisi_yoksa_1(self, cli_cfg, con, capsys):
        from src import llm_io
        asof = kur_sentetik_evren(cli_cfg, con)
        llm_io.write_bundle(cli_cfg, llm_io.build_bundle(cli_cfg, con, asof))
        assert _kos("denetle", "--asof", asof) == 1
        assert "Analist çıktısı yok" in capsys.readouterr().out

    def test_temiz_cikti_0(self, cli_cfg, con):
        from src import llm_io
        asof = kur_sentetik_evren(cli_cfg, con)
        b = llm_io.build_bundle(cli_cfg, con, asof)
        llm_io.write_bundle(cli_cfg, b)
        planli = next(e["ticker"] for e in b["evren"] if e["plan_menusu"])
        util.write_json(f"{cli_cfg['paths']['llm_out_dir']}/{asof}/analysis.json",
                        analist_ciktisi(b, plan_secilen=planli))
        assert _kos("denetle", "--asof", asof) == 0

    def test_SERT_HATA_2(self, cli_cfg, con, capsys):
        from src import llm_io
        asof = kur_sentetik_evren(cli_cfg, con)
        b = llm_io.build_bundle(cli_cfg, con, asof)
        llm_io.write_bundle(cli_cfg, b)
        out = analist_ciktisi(b)
        out["schema_version"] = "yanlis_surum"
        util.write_json(f"{cli_cfg['paths']['llm_out_dir']}/{asof}/analysis.json", out)
        assert _kos("denetle", "--asof", asof) == 2
        assert "HF-01" in capsys.readouterr().out


class TestKaydetCikisKodu:
    def test_sert_hata_varsa_2_ve_JOURNAL_BOS_KALIR(self, cli_cfg, con, capsys):
        """Denetimden geçmeyen çıktı journal'a GİREMEZ — bu, projenin ana kapısı."""
        from src import llm_io
        asof = kur_sentetik_evren(cli_cfg, con)
        b = llm_io.build_bundle(cli_cfg, con, asof)
        llm_io.write_bundle(cli_cfg, b)
        out = analist_ciktisi(b)
        out["stocks"][0]["signal"] = "olmayan_sinyal"
        util.write_json(f"{cli_cfg['paths']['llm_out_dir']}/{asof}/analysis.json", out)

        assert _kos("kaydet", "--asof", asof) == 2
        assert "journal'a YAZILMADI" in capsys.readouterr().out
        assert db.scalar(con, "SELECT COUNT(*) FROM predictions") == 0

    def test_temiz_ciktida_0_ve_tahminler_yazilir(self, cli_cfg, con, capsys):
        from src import llm_io
        asof = kur_sentetik_evren(cli_cfg, con)
        b = llm_io.build_bundle(cli_cfg, con, asof)
        llm_io.write_bundle(cli_cfg, b)
        planli = next(e["ticker"] for e in b["evren"] if e["plan_menusu"])
        util.write_json(f"{cli_cfg['paths']['llm_out_dir']}/{asof}/analysis.json",
                        analist_ciktisi(b, plan_secilen=planli))
        assert _kos("kaydet", "--asof", asof) == 0
        assert db.scalar(con, "SELECT COUNT(*) FROM predictions") == len(b["evren"])
        assert "journal'a yazıldı" in capsys.readouterr().out


class TestHaberCikisKodu:
    def test_atlanan_aralik_1(self, cli_cfg, con, monkeypatch, capsys):
        """"0 bildirim" ile "aralık atlandı" AYNI ÇIKTIYA DÜŞEMEZ."""
        from src import news
        monkeypatch.setattr(news, "sync", lambda *a, **k: {
            "atlandi": False, "bildirim": 0, "yazilan": 0, "ticker": 0,
            "since": "x", "hata": None, "tickersiz": 0,
            "atlanan_aralik": "2026-05-01…2026-05-03"})
        assert _kos("haber", "cek") == 1
        assert "ATLANAN ARALIK" in capsys.readouterr().out

    def test_kap_hatasi_2(self, cli_cfg, con, monkeypatch, capsys):
        """KAP hatası "haber yok" DEĞİLDİR; paketteki boş listelere güvenilmez."""
        from src import news
        monkeypatch.setattr(news, "sync", lambda *a, **k: {
            "atlandi": False, "bildirim": 0, "yazilan": 0, "ticker": 0,
            "since": "x", "hata": "ConnectionError: kap", "tickersiz": 0,
            "atlanan_aralik": None})
        assert _kos("haber", "cek") == 2
        cikti = capsys.readouterr().out
        assert "KAP HATASI" in cikti and "DEĞİL" in cikti

    def test_temiz_cekim_0(self, cli_cfg, con, monkeypatch):
        from src import news
        monkeypatch.setattr(news, "sync", lambda *a, **k: {
            "atlandi": False, "bildirim": 5, "yazilan": 5, "ticker": 2,
            "since": "x", "hata": None, "tickersiz": 0, "atlanan_aralik": None})
        assert _kos("haber", "cek") == 0

    def test_kap_kapaliysa_0(self, cli_cfg, con, monkeypatch, capsys):
        kapali = {**cli_cfg, "sources": {**cli_cfg["sources"],
                                         "kap": {**cli_cfg["sources"]["kap"],
                                                 "enabled": False}}}
        monkeypatch.setattr(cli, "_cfg", lambda: kapali)
        assert _kos("haber", "cek") == 0
        assert "KAP kapalı" in capsys.readouterr().out

    def test_bayat_veri_durumda_1(self, cli_cfg, con):
        from tests.conftest import add_bars, add_universe
        add_universe(con, "AAA")
        add_bars(con, "AAA", [("2026-07-27", 10.0, 11.0, 9.0, 10.0, 1e6, 10.0)])
        assert _kos("haber", "durum") == 1

    def test_taze_veri_durumda_0(self, cli_cfg, con):
        from tests.conftest import add_bars, add_universe
        add_universe(con, "AAA")
        add_bars(con, "AAA", [("2026-07-27", 10.0, 11.0, 9.0, 10.0, 1e6, 10.0)])
        con.execute(
            "INSERT INTO disclosures (disclosure_id,ticker,published_utc,tier,"
            "title,fetched_utc) VALUES ('kap-1','AAA','2026-07-27T10:00:00+00:00',"
            "1,'t',?)", (util.utc_now_iso(),))
        con.commit()
        assert _kos("haber", "durum") == 0


class TestSaglikCikisKodu:
    @pytest.fixture
    def zaman_dondur(self, monkeypatch):
        """Sentetik evren 2023-2024 tarihlidir; `bar tazeliği` kontrolü ise
        DUVAR SAATİNE bakar (ve bakmalıdır — sorduğu soru "bugünün verisi
        geldi mi?"). Referans zamanı testin kendisi ilan eder, yoksa suite
        takvim ilerledikçe kayan bir teste dönüşür.
        """
        from src.calendar_bist import BistCalendar

        def dondur(asof: str):
            monkeypatch.setattr(BistCalendar, "last_closed_session",
                                lambda self, ts=None: date.fromisoformat(asof))
        return dondur

    def test_bos_veritabaninda_KRITIK(self, cli_cfg, con, capsys):
        """Ön uçuş kontrolü boş kurulumda temiz DEMEMELİ."""
        assert _kos("saglik") == 2
        cikti = capsys.readouterr().out
        assert "KRİTİK" in cikti and "haber katmanı" in cikti

    def test_bar_bayatsa_UYARI_verir(self, cli_cfg, con, capsys, zaman_dondur):
        """⚠ Faz 8'de eklendi. NE OLURDU: diğer kontroller göstergeyi/kaliteyi
        `MAX(bars_daily.date)`e kıyaslar; barlar bayatlarsa `asof` da bayatlar
        ve hepsi TUTARLI görünür. Otomasyonda karşılığı: veri gelmeyen gün
        dünkü rapor bugünmüş gibi bildirilir, hiçbir uyarı çıkmaz."""
        asof = kur_sentetik_evren(cli_cfg, con)
        con.execute(
            "INSERT INTO disclosures (disclosure_id,ticker,published_utc,tier,"
            "title,fetched_utc) VALUES ('kap-1','AAA',?,1,'t',?)",
            (f"{asof}T10:00:00+00:00", util.utc_now_iso()))
        con.commit()
        # Takvim bir seans ileride: veri gelmemiş.
        d = date.fromisoformat(asof) + timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        zaman_dondur(d.isoformat())

        assert _kos("saglik") == 1
        assert "bar tazeliği" in capsys.readouterr().out

    def test_tam_kurulumda_temiz(self, cli_cfg, con, capsys, zaman_dondur):
        asof = kur_sentetik_evren(cli_cfg, con)
        zaman_dondur(asof)
        con.execute(
            "INSERT INTO disclosures (disclosure_id,ticker,published_utc,tier,"
            "title,fetched_utc) VALUES ('kap-1','AAA',?,1,'t',?)",
            (f"{asof}T10:00:00+00:00", util.utc_now_iso()))
        con.commit()
        kod = _kos("saglik")
        cikti = capsys.readouterr().out
        assert kod == 0, cikti
        assert "Tüm kontroller temiz" in cikti

    def test_gosterge_bayatsa_KRITIK(self, cli_cfg, con, capsys, zaman_dondur):
        """Fiyat ilerlemiş, gösterge geride kalmışsa kesit sessizce daralır."""
        from tests.conftest import add_bars
        kur_sentetik_evren(cli_cfg, con)
        add_bars(con, "AAA", [("2030-01-02", 10.0, 11.0, 9.0, 10.0, 1e6, 10.0)])
        zaman_dondur("2030-01-02")      # barlar taze; bayat olan GÖSTERGE
        assert _kos("saglik") == 2
        assert "gösterge tazeliği" in capsys.readouterr().out


class TestDegerlendirCikisKodu:
    def test_tool_verilirse_KaynakKarisik_hala_2(self, cli_cfg, con, monkeypatch,
                                                 capsys):
        """`--tool` yolunda karıştırma koruması AYNEN duruyor."""
        from src import evaluate
        monkeypatch.setattr(evaluate, "run", lambda *a, **k: (_ for _ in ()).throw(
            evaluate.KaynakKarisik("iki araç var — `--tool` ver")))
        assert _kos("degerlendir", "--tool", "replay") == 2
        assert "--tool" in capsys.readouterr().out

    def test_toolsuz_TUM_kaynaklari_ayri_ayri_basar(self, cli_cfg, con,
                                                    monkeypatch, capsys):
        """⚠ NE OLMUŞTU: `--tool` verilmeyince komut `KaynakKarisik` ile çıkış
        kodu 2 döndürüyordu ve kullanıcı HİÇBİR ŞEY göremiyordu. Sonuç: canlı
        analistlerin çözülmüş kararları hiçbir raporda görünmedi; beş bağımsız
        dış inceleme "raporlar donmuş" alarmı verdi — oysa raporlar donuk
        değildi, yalnız tek bir kaynağı (replay) gösteriyordu.

        Karıştırma yasağı GEVŞEMEDİ: kaynaklar yan yana, ayrı bölümlerde ve
        her biri kendi N'iyle basılır. Yasağın kendisi `evaluate.run` üzerinde
        hâlâ kilitli (bkz. `test_uctan_uca`).
        """
        from src import evaluate, report
        sahte = {"sayim": {"replay": 20, "claude-code": 1},
                 "kaynaklar": [{"tool": "replay"}, {"tool": "claude-code"}]}
        monkeypatch.setattr(evaluate, "run_all", lambda *a, **k: sahte)
        monkeypatch.setattr(report, "evaluate_report_all",
                            lambda cfg, h: "\n".join(
                                f"Kaynak: {k['tool']}" for k in h["kaynaklar"]))
        assert _kos("degerlendir") == 0
        cikti = capsys.readouterr().out
        assert "replay" in cikti and "claude-code" in cikti

    def test_bos_journalda_0(self, cli_cfg, con):
        assert _kos("degerlendir") == 0


class TestOlcumCikisKodlari:
    def test_backtest_kapi_kapaliysa_2(self, cli_cfg, con, monkeypatch):
        """Kapı kapalıysa otomasyon bunu FARK ETMELİ."""
        from src import backtest, report
        monkeypatch.setattr(backtest, "full_measurement",
                            lambda *a, **k: {"kapi": {"acik": False}, "tarih": "x"})
        monkeypatch.setattr(report, "backtest_report", lambda cfg, s: "rapor")
        assert _kos("backtest") == 2

    def test_backtest_kapi_acikken_0(self, cli_cfg, con, monkeypatch):
        from src import backtest, report
        monkeypatch.setattr(backtest, "full_measurement",
                            lambda *a, **k: {"kapi": {"acik": True}, "tarih": "x"})
        monkeypatch.setattr(report, "backtest_report", lambda cfg, s: "rapor")
        assert _kos("backtest") == 0

    def test_revizyon_gecmediyse_2(self, cli_cfg, con, monkeypatch):
        """Ön kayıtlı tur GEÇMEDİ — bu bir başarı değil, sonucun kendisi."""
        from src import report, revizyon
        monkeypatch.setattr(revizyon, "run",
                            lambda *a, **k: {"karar": {"gecti": False}})
        monkeypatch.setattr(report, "revizyon_report", lambda cfg, r: "rapor")
        assert _kos("revizyon") == 2

    def test_makro_anahtar_yoksa_1(self, cli_cfg, con, monkeypatch, capsys):
        """EVDS anahtarı yoksa uydurma YAPILMAZ; rapor satırları gizlenir."""
        from src.sources import evds
        monkeypatch.setattr(evds, "available", lambda: False)
        assert _kos("makro", "durum") == 1
        cikti = capsys.readouterr().out
        assert "EVDS_API_KEY yok" in cikti and "uydurma yapılmaz" in cikti


# ============================================================ okuma komutları
class TestOkumaKomutlari:
    def test_gunluk_paketi_UC_dosya_yazar(self, cli_cfg, con, capsys):
        asof = kur_sentetik_evren(cli_cfg, con)
        assert _kos("gunluk", "--asof", asof) == 0
        d = util.resolve(f"{cli_cfg['paths']['llm_in_dir']}/{asof}")
        assert {p.name for p in d.iterdir()} == {"bundle.json", "context.md",
                                                 "prompt.md"}
        cikti = capsys.readouterr().out
        assert "bundle_sha" in cikti and "bist denetle" in cikti

    def test_plan_menusu_UYARI_ibaresini_basar(self, cli_cfg, con, capsys):
        asof = kur_sentetik_evren(cli_cfg, con)
        assert _kos("plan", "--asof", asof) == 0
        cikti = capsys.readouterr().out
        assert "Ölçülen kenar yok" in cikti
        assert "Rejim:" in cikti

    def test_plan_kaydet_bayragi_saklar(self, cli_cfg, con):
        asof = kur_sentetik_evren(cli_cfg, con)
        assert _kos("plan", "--asof", asof, "--kaydet") == 0
        assert db.scalar(con, "SELECT COUNT(*) FROM plan_options") > 0

    def test_rapor_paket_yoksa_1(self, cli_cfg, con, capsys):
        from tests.conftest import add_bars, add_universe
        add_universe(con, "AAA")
        add_bars(con, "AAA", [("2026-07-27", 10.0, 11.0, 9.0, 10.0, 1e6, 10.0)])
        assert _kos("rapor") == 1
        assert "önce `bist gunluk" in capsys.readouterr().out

    def test_rapor_paket_varsa_yazar(self, cli_cfg, con, capsys):
        asof = kur_sentetik_evren(cli_cfg, con)
        _kos("gunluk", "--asof", asof)
        capsys.readouterr()
        assert _kos("rapor", "--asof", asof) == 0
        assert (util.resolve(cli_cfg["paths"]["reports_dir"])
                / f"gunluk_{asof}.md").exists()

    def test_takvim_sorgusu(self, cli_cfg, con, capsys):
        assert _kos("takvim", "2026-07-27") == 0
        cikti = capsys.readouterr().out
        assert "2026-07-27" in cikti
        assert "İŞLEM GÜNÜ" in cikti or "kapalı" in cikti

    def test_takvim_aritmetigi_TERS_KONTROL_basar(self, cli_cfg, con, capsys):
        assert _kos("takvim", "2026-07-27", "20") == 0
        assert "ters kontrol: 20" in capsys.readouterr().out

    def test_journal_durum(self, cli_cfg, con, capsys):
        assert _kos("journal", "durum") == 0
        assert "Tahmin" in capsys.readouterr().out

    def test_journal_acik(self, cli_cfg, con):
        assert _kos("journal", "acik") == 0

    def test_coz_bos_journalda_patlamaz(self, cli_cfg, con, capsys):
        assert _kos("coz") == 0
        assert "0 tahmin çözüldü" in capsys.readouterr().out

    def test_portfoy_ekle_listele_sil(self, cli_cfg, con, capsys):
        assert _kos("portfoy", "ekle", "THYAO", "100", "312.5") == 0
        assert _kos("portfoy", "listele") == 0
        assert "THYAO" in capsys.readouterr().out
        assert _kos("portfoy", "sil", "THYAO") == 0
        assert _kos("portfoy", "listele") == 0
        assert "Elle girilmiş pozisyon yok" in capsys.readouterr().out

    def test_portfoy_durum_KAGIT_karneyi_basar(self, cli_cfg, con, capsys):
        """ADR #019 — boş journal'da bile başlangıç sermayesini gösterir.

        "Kayıt yok" ile "sermaye sıfır" ayrı iki şeydir; komut sessiz kalırsa
        okuyan kişi ikincisini varsayar (#009).
        """
        assert _kos("portfoy", "durum") == 0
        cikti = capsys.readouterr().out
        assert "Kâğıt portföy" in cikti
        assert "10.000,00 TL" in cikti

    def test_gosterge_hesaplar(self, cli_cfg, con, capsys):
        from tests.conftest import add_bars, add_universe, bar_serisi
        add_universe(con, "AAA")
        add_bars(con, "AAA", bar_serisi(300, gunluk_egim=0.001, dalga=2.0))
        assert _kos("gosterge") == 0
        assert db.scalar(con, "SELECT COUNT(*) FROM indicator_daily") == 300
        assert cli_cfg["gostergeler"]["set_version"] in capsys.readouterr().out

    def test_gosterge_atlanani_SOYLER(self, cli_cfg, con, capsys):
        """Yetersiz barla atlanan ticker sessizce kaybolmaz."""
        from tests.conftest import add_bars, add_universe, bar_serisi
        add_universe(con, "KISA")
        add_bars(con, "KISA", bar_serisi(30))
        assert _kos("gosterge") == 0
        assert "Yetersiz bar" in capsys.readouterr().out

    def test_evren_sync(self, cli_cfg, con, capsys):
        assert _kos("evren", "sync") == 0
        cikti = capsys.readouterr().out
        assert "canlı" in cikti and "ölçüm" in cikti

    def test_veri_kalite_raporu(self, cli_cfg, con, capsys):
        assert _kos("veri", "kalite") == 0
        assert "Veri kalitesi" in capsys.readouterr().out

    def test_veri_temizle(self, cli_cfg, con, capsys):
        assert _kos("veri", "temizle") == 0
        assert "Hayalet bar" in capsys.readouterr().out

    def test_db_durum(self, cli_cfg, con, capsys):
        assert _kos("db", "durum") == 0
        cikti = capsys.readouterr().out
        assert "Şema sürümü" in cikti and "predictions" in cikti

    def test_db_dump_deterministik_dosya_yazar(self, cli_cfg, con, capsys):
        assert _kos("db", "dump") == 0
        yol = util.resolve(cli_cfg["paths"]["db_dump"])
        assert yol.exists()
        birinci = yol.read_text(encoding="utf-8")
        _kos("db", "dump")
        assert yol.read_text(encoding="utf-8") == birinci

    def test_seviye_olcumu_KENAR_IDDIASI_TASIMAZ(self, cli_cfg, con, capsys):
        """`measure_level_edge` yazılmıştı ama HİÇBİR YERDEN çağrılmıyordu.

        Ölçüm kültürü olan bir projede koşulmayan bir ölçüm harness'i,
        silinmesi değil BAĞLANMASI gereken bir eksiktir.
        """
        kur_sentetik_evren(cli_cfg, con)
        assert _kos("seviye", "AAA") == 0
        cikti = capsys.readouterr().out
        assert "KENAR İDDİASI DEĞİLDİR" in cikti
        assert "doğrulandı" in cikti and "yoktur" in cikti  # "…dalı yoktur"

    def test_replay_sifirla_GERCEK_kayitlara_dokunmaz(self, cli_cfg, con, capsys):
        """`--sifirla` yalnız `tool='replay'` kayıtlarını silmeli."""
        from src import journal
        asof = kur_sentetik_evren(cli_cfg, con)
        for arac in ("replay", "claude-code"):
            rid = journal.create_run(cli_cfg, con, asof=asof, tool=arac,
                                     bundle_sha="x")
            from tests.conftest import add_plan
            add_plan(con, f"P-{arac}", ticker="AAA", asof=asof)
            journal.record(cli_cfg, con, run_id=rid, asof=asof, ticker="AAA",
                           analist={"signal": "hold", "action": "izle",
                                    "confidence": "orta"},
                           plan={"plan_id": f"P-{arac}"},
                           referans={"close": 100.0})
        assert _kos("replay", "--sifirla") == 0
        kalan = {r["tool"] for r in db.fetch_all(
            con, "SELECT DISTINCT r.tool FROM predictions p "
                 " JOIN llm_runs r ON r.run_id = p.run_id")}
        assert kalan == {"claude-code"}
        assert "gerçek analiz kayıtlarına dokunulmadı" in capsys.readouterr().out
