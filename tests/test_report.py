"""Rapor testleri — RAPORUN DİLİ ÖLÇÜMDEN GELİR, tersi değil.

Raporlar bu projenin tek insan arayüzü ve 30 KB'lık `report.py`'nin tek testi
yoktu. Test edilen şey biçim değil, **iddia disiplini**:

* Hiçbir hüküm hücresinde "doğrulandı" geçemez — `edge_verdict`in o dalı yok.
* `gerekli N` her ölçüm raporunda BASILIR: "ne zaman bilebiliriz?" bir his
  değil, hesaplanmış bir sayıdır (ai/PROJECT.md).
* Çoklu test uyarısı basılır — 30+ karşılaştırmada biri şansa bağlı iyi görünür.
* Survivorship eğilimi düzeltilmiyor ama İFŞA EDİLİYOR; ifşayı silmek eğilimi
  gizlemek olur.
* Kapı KAPALIYSA rapor bunu açıkça yazar ve TERS kanıtı ayrı bir bulgu sayar
  (L-006: büyüklük hükmünü yön hükmü sanmak).

Ölçümler sentetik ama GERÇEK harness üzerinde koşar (`backtest.full_measurement`,
`diagnose.run`, `revizyon.run`) — böylece rapor ile ölçüm sözlüğü arasındaki
anahtar ayrışmaları da yakalanır. Elle kurulmuş sözlükler o ayrışmayı gizlerdi.
"""

from __future__ import annotations

import pytest

from src import backtest, diagnose, report, revizyon, stats, util

from tests.conftest import kur_sentetik_evren


def _hukum_hucreleri(metin: str) -> list[str]:
    """Markdown tablolarındaki **kalın** hüküm hücreleri."""
    return [h.strip() for satir in metin.splitlines() if satir.startswith("|")
            for h in satir.split("|") if "**" in h]


def _iddia_etmiyor(metin: str) -> None:
    """Hiçbir HÜKÜM hücresi kesinlik iddia etmemeli.

    Açıklama satırlarında ("bu sistemde 'doğrulandı' YOKTUR") geçmesi serbest —
    yasak olan, bir hüküm olarak basılması.
    """
    for h in _hukum_hucreleri(metin):
        alt = h.lower()
        for yasak in ("doğrulandı", "kanıtlandı", "onaylandı", "garanti"):
            assert yasak not in alt, f"hüküm olarak geçmiş: {h}"


@pytest.fixture(scope="module")
def _olcum_dunyasi(tmp_path_factory):
    """Ölçüm harness'i için tek kurulum — modül boyunca paylaşılır (pahalı).

    Salt-okunur kullanılıyor: hiçbir test bu dünyayı DEĞİŞTİRMEZ, yalnız
    üzerinde ölçüm koşar.
    """
    from src import db
    tmp = tmp_path_factory.mktemp("olcum")
    c = util.load_config(fresh=True)
    c = {**c, "paths": {**c["paths"], "db": str(tmp / "t.db"),
                        "db_dump": str(tmp / "t.sql"),
                        "llm_in_dir": str(tmp / "llm" / "in"),
                        "llm_out_dir": str(tmp / "llm" / "out"),
                        "reports_dir": str(tmp / "reports"),
                        "log_dir": str(tmp / "logs")}}
    con = db.connect(c)
    kur_sentetik_evren(c, con, n_bar=600)
    sonuc = backtest.full_measurement(c, con)
    teshis = diagnose.run(c, con)
    rev = revizyon.run(c, con)
    yield {"cfg": c, "olcum": sonuc, "teshis": teshis,
           "hukum": diagnose.verdict(teshis), "revizyon": rev}
    con.close()


@pytest.fixture
def olcum(_olcum_dunyasi):
    return _olcum_dunyasi["olcum"]


@pytest.fixture
def ocfg(_olcum_dunyasi):
    return _olcum_dunyasi["cfg"]


# ============================================================ ölçüm raporu
class TestBacktestRaporu:
    def test_uretilebiliyor(self, ocfg, olcum):
        metin = report.backtest_report(ocfg, olcum)
        assert metin.startswith("# Ölçüm Raporu")
        assert len(metin.splitlines()) > 50

    def test_UYARI_metni_basta(self, ocfg, olcum):
        metin = report.backtest_report(ocfg, olcum)
        assert ocfg["rapor"]["uyari"].split("\n")[0][:40] in metin

    def test_SURVIVORSHIP_ifsa_edilir(self, ocfg, olcum):
        """Düzeltilmeyen bir eğilim en azından yazılı olmalı.

        "Düzeltilmiyor; büyüklüğü bilinmiyor" cümlesi bilinçli: düzeltiliyormuş
        gibi yapmak daha kötü olurdu.
        """
        metin = report.backtest_report(ocfg, olcum)
        assert "Survivorship" in metin
        assert "Düzeltilmiyor" in metin

    def test_EW_TABANI_neden_XU100_DEGIL_yazili(self, ocfg, olcum):
        """XU100'e göre alfa, eşit-ağırlığın bedava üstünlüğünü sessizce içerir."""
        metin = report.backtest_report(ocfg, olcum)
        assert "neden XU100 değil" in metin
        assert "sıfır beceri" in metin

    def test_GEREKLI_N_basilir(self, ocfg, olcum):
        metin = report.backtest_report(ocfg, olcum)
        assert "gerekli N" in metin
        assert "(2×sd/|ort|)²" in metin

    def test_COKLU_TEST_uyarisi_basilir(self, ocfg, olcum):
        metin = report.backtest_report(ocfg, olcum)
        assert stats.bonferroni_note(olcum["n_test"]) in metin
        assert olcum["n_test"] > 10, "çoklu test sayısı gerçekçi değil"

    def test_SESSIZ_KIRPMA_YOK_bolumu(self, ocfg, olcum):
        """Atlanan dönemler raporlanır: yalnız boğa dönemlerinde ölçüm yapılmadığı
        GÖRÜNÜR olmalı (eski sürüm 131 dönemin 62'sini düşürüyordu)."""
        metin = report.backtest_report(ocfg, olcum)
        assert "sessiz kırpma yok" in metin.lower()
        assert "Atlanan" in metin

    def test_hicbir_hukum_IDDIA_ETMEZ(self, ocfg, olcum):
        _iddia_etmiyor(report.backtest_report(ocfg, olcum))

    def test_kapi_kararini_ACIKCA_yazar(self, ocfg, olcum):
        metin = report.backtest_report(ocfg, olcum)
        assert "## Kapı kararı" in metin
        if olcum["kapi"]["acik"]:
            assert "Kapı AÇIK" in metin
        else:
            assert "Kapı KAPALI" in metin

    def test_TERS_KANIT_ayri_bir_BULGU_olarak_yazilir(self, ocfg, olcum):
        """Güvenilir biçimde KAYBETTİREN bir faktör "kanıt" sayılamaz.

        İlk sürümde kapı yalnız hükme bakıyordu ve `mom_12_1` (−1.47pp, t=−2.64)
        kapıyı AÇIYORDU (L-006). Ters kanıt bir başarısızlık değil bulgudur —
        ama kapıyı açmaz.
        """
        metin = report.backtest_report(ocfg, olcum)
        assert "büyüklük" in metin and "yön hükmü değil" in metin
        if olcum["kapi"]["ters"]:
            assert "Ters yönde kanıt" in metin
            for ad in olcum["kapi"]["ters"]:
                assert ad in metin

    def test_kenarsiz_ufuk_ETIKETLENIR(self, ocfg, olcum):
        """H=5'te ölçülen kenar SIFIR; o satır kalıcı etiketle sunulur."""
        metin = report.backtest_report(ocfg, olcum)
        if ocfg["olcum"]["kenarsiz_ufuklar"]:
            assert "kenarsız kabul edilen ufuk" in metin

    def test_maliyet_duyarliligi_tum_senaryolarla(self, ocfg, olcum):
        metin = report.backtest_report(ocfg, olcum)
        for c in ocfg["olcum"]["maliyet_duyarliligi_pct"]:
            assert f"%{c:.2f}" in metin

    def test_okuma_kurallari_bolumu(self, ocfg, olcum):
        metin = report.backtest_report(ocfg, olcum)
        assert "Bu raporun okunma kuralları" in metin
        assert "Zayıf N büyük farkı ezer" in metin


# ============================================================ teşhis raporu
class TestTeshisRaporu:
    def test_REVIZYON_TURU_DEGIL_ibaresi(self, _olcum_dunyasi):
        """Teşhis ile revizyon karıştırılırsa "geçene kadar varyant deneme"ye
        dönüşür — yani veri madenciliği."""
        metin = report.diagnose_report(_olcum_dunyasi["cfg"],
                                       _olcum_dunyasi["teshis"],
                                       _olcum_dunyasi["hukum"])
        assert "revizyon turu DEĞİLDİR" in metin
        assert "kazanan" in metin and "kombinasyon aranmaz" in metin

    def test_iki_IC_nin_AYNI_SEY_OLMADIGI_yazili(self, _olcum_dunyasi):
        metin = report.diagnose_report(_olcum_dunyasi["cfg"],
                                       _olcum_dunyasi["teshis"],
                                       _olcum_dunyasi["hukum"])
        assert "ic_tum" in metin and "ic_uygun" in metin
        assert "KAPISIZ" in metin and "KAPILI" in metin

    def test_tani_ve_aciklama_rapora_girer(self, _olcum_dunyasi):
        h = _olcum_dunyasi["hukum"]
        metin = report.diagnose_report(_olcum_dunyasi["cfg"],
                                       _olcum_dunyasi["teshis"], h)
        assert f"`{h['tani']}`" in metin
        assert h["aciklama"][:40] in metin

    def test_her_kol_TEK_SAPMA_oldugunu_yazar(self, _olcum_dunyasi):
        metin = report.diagnose_report(_olcum_dunyasi["cfg"],
                                       _olcum_dunyasi["teshis"],
                                       _olcum_dunyasi["hukum"])
        assert "tek bir" in metin and "sapma" in metin
        for a in _olcum_dunyasi["teshis"]["atif"]:
            assert a["kol"] in metin

    def test_COKLU_TEST_uyarisi_ve_HUKUM_VERMEME(self, _olcum_dunyasi):
        t = _olcum_dunyasi["teshis"]
        metin = report.diagnose_report(_olcum_dunyasi["cfg"], t,
                                       _olcum_dunyasi["hukum"])
        assert stats.bonferroni_note(t["n_test"]) in metin
        assert "hüküm verilmiyor" in metin

    def test_n_test_muhasebesi_GERCEK_kol_sayisiyla_uyumlu(self, _olcum_dunyasi):
        """Çoklu test sayısı eksik yazılırsa Bonferroni uyarısı olduğundan
        iyimser görünür."""
        t = _olcum_dunyasi["teshis"]
        assert t["n_test"] == len(t["atif"]) + len(t["ic_ufuk"]) + 2 * len(t["faktor_ic"]) + 1


# ============================================================ revizyon raporu
class TestRevizyonRaporu:
    def test_ON_KAYIT_MUHRU_rapora_girer(self, _olcum_dunyasi):
        """Ön kayıt sha'sı raporda görünmeli: "koşudan önce mühürlendi" iddiası
        doğrulanabilir olsun."""
        r = _olcum_dunyasi["revizyon"]
        metin = report.revizyon_report(_olcum_dunyasi["cfg"], r)
        assert r["on_kayit_sha"][:32] in metin
        assert "koşudan **önce** mühürlendi" in metin
        assert "docs/on-kayit-revizyon-01.md" in metin

    def test_KARAR_KURALI_sonucu_gormeden_yazildi_ibaresi(self, _olcum_dunyasi):
        metin = report.revizyon_report(_olcum_dunyasi["cfg"],
                                       _olcum_dunyasi["revizyon"])
        assert "sonucu görmeden yazıldı" in metin
        assert _olcum_dunyasi["revizyon"]["karar"]["kural"] in metin

    def test_gecmediyse_IKINCI_TUR_YOK_yazar(self, _olcum_dunyasi):
        """Başarısızlıkta ikinci tur YOK — doğrudan yeniden çerçeveleme.

        "Bir daha denesek" cümlesi ön kaydın engellemek için yazıldığı şeydir.
        """
        r = _olcum_dunyasi["revizyon"]
        metin = report.revizyon_report(_olcum_dunyasi["cfg"], r)
        if not r["karar"]["gecti"]:
            assert "GEÇMEDİ" in metin and "ikinci tur yok" in metin
            assert "yeniden çerçeveleme" in metin
        else:
            assert "GEÇTİ" in metin

    def test_tek_kol_katkilarinin_KARAR_VERMEDIGI_yazili(self, _olcum_dunyasi):
        metin = report.revizyon_report(_olcum_dunyasi["cfg"],
                                       _olcum_dunyasi["revizyon"])
        assert "karar VERMEZ" in metin

    def test_COKLU_TEST_teshisle_BIRLIKTE_sayilir(self, _olcum_dunyasi):
        """Teşhiste yapılan karşılaştırmalar bu turun muhasebesine EKLENİR.

        Ayrı ayrı saymak, toplam arama alanını olduğundan küçük gösterir.
        """
        r = _olcum_dunyasi["revizyon"]
        metin = report.revizyon_report(_olcum_dunyasi["cfg"], r)
        assert stats.bonferroni_note(r["n_teshis_test"] + r["n_test"]) in metin

    def test_hicbir_hukum_IDDIA_ETMEZ(self, _olcum_dunyasi):
        _iddia_etmiyor(report.revizyon_report(_olcum_dunyasi["cfg"],
                                              _olcum_dunyasi["revizyon"]))


# ============================================================ biçimlendirme
class TestBicimlendirme:
    def test_None_TIRE_olarak_basilir(self):
        """None'ı "0.00" diye basmak, veri yokluğunu bir DEĞERE çevirir."""
        assert report._s(None) == "—"
        assert report._n(None) == "—"

    def test_sayi_bicimi(self):
        assert report._s(1.5, 2, "pp") == "1.50pp"
        assert report._s(0.123456, 3) == "0.123"
        assert report._n(1234567) == "1.234.567"

    def test_sayi_olmayan_deger_patlamaz(self):
        assert report._s("abc") == "abc"

    def test_write_reports_dizinine_yazar(self, cfg):
        yol = report.write(cfg, "test_raporu.md", "# içerik")
        p = util.resolve(yol)
        assert p.exists()
        assert p.read_text(encoding="utf-8") == "# içerik\n"
        assert cfg["paths"]["reports_dir"] in str(yol)

    def test_bugun_ISO(self):
        from datetime import date
        assert report.bugun() == date.today().isoformat()


# ============================================================ değerlendirme
class TestDegerlendirmeRaporuKenarDurumlari:
    def test_TAMAMEN_BOS_olcumde_patlamaz(self, cfg, con):
        """Taze kurulumda `bist degerlendir` çökmemeli.

        Eksik anahtar bu komutu KeyError ile çökertiyordu; boş dönüşte de tüm
        anahtarların bulunması sözleşmenin parçası.
        """
        from src import evaluate
        metin = report.evaluate_report(cfg, evaluate.run(cfg, con))
        assert "ölçüm yok" in metin or "ölçüm yetersiz" in metin
        _iddia_etmiyor(metin)

    def test_BOYUTLANDIRMA_bolumu_ve_gecmisi_yazili(self, cfg, con):
        """Bu satır uzun süre TANIM GEREĞİ sıfırdı; rapor bunu itiraf ediyor."""
        from src import evaluate
        metin = report.evaluate_report(cfg, evaluate.run(cfg, con))
        assert "Rejim boyutlandırması" in metin
        assert "TANIM GEREĞİ sıfır" in metin

    def test_XU100_KARAR_ICIN_KULLANILMAZ_etiketi(self, cfg, con):
        from src import evaluate
        e = evaluate.run(cfg, con)
        e["alfa"]["xu100_ort"] = 1.23
        metin = report.evaluate_report(cfg, e)
        assert "karar için" in metin and "kullanılmaz" in metin
        assert "sermaye-ağırlık" in metin

    def test_okuma_kurallari_OLCUM_YETERSIZ_i_SONUC_sayar(self, cfg, con):
        from src import evaluate
        metin = report.evaluate_report(cfg, evaluate.run(cfg, con))
        assert "bir sonuçtur, bir eksiklik değil" in metin
        assert "Ağırlıklar bu rapordan DEĞİŞMEZ" in metin
