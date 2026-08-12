"""UÇTAN UCA boru hattı testi — LLM sınırı dahil, gerçek modül dizisiyle.

Bu dosya tek bir soruyu cevaplar: **`bist gunluk → denetle → kaydet → coz →
degerlendir` zinciri gerçekten baştan sona koşuyor mu?**

Neden ayrı bir dosya gerekiyor: bu projede bulunan en pahalı hatalar tek modülde
DEĞİL, modüller arası varsayımda çıktı ve hepsi birim testlerinden geçiyordu:

* Paket faktör skorunu taşımıyordu → HF-22 üretimde hiç ateşlenemiyor ve
  `bist kaydet` NOT NULL hatasıyla patlıyordu.
* Kalite kaydı eksik olduğunda dört tüketici de "kayıt yok"u "sorun yok"
  okuyordu.
* `replay` `build_menu`'yü atlayıp `build_options`'ı doğrudan çağırıyordu; canlı
  hattaki üç kontrol replay'de hiç koşmuyordu.
* Kalite kapısı sıkılaştırılınca replay'in TAMAMI elendi (90 plan_yok, 0 tahmin)
  ve testler yeşil kaldı.

Son madde bu dosyanın asıl gerekçesi: *her düzeltmeden sonra ETKİLENEN HATTI
uçtan uca koş; test yeşil diye geçme* (AGENTS.md §11, tuzak 1).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from src import (audit, db, evaluate, journal, llm_io, planner, report,
                 resolver, schema, universe, util)

from tests.conftest import (GECERLI_PROSE as PROSE, analist_ciktisi as _analist_cikti,
                            kur_sentetik_evren)


def _kaydet(cfg, con, bundle, out) -> str:
    """`cli.cmd_kaydet`in iş mantığı — CLI'a bağımlı olmadan aynı sıra."""
    menu = planner.build_menu(cfg, con, bundle["asof"])
    for opts in menu["menu"].values():
        planner.store(cfg, con, opts)

    run_id = journal.create_run(cfg, con, asof=bundle["asof"],
                                tool=out["tool"], bundle_sha=bundle["bundle_sha"])
    plan_map = {p["plan_id"]: p
                for ps in planner.load_for_date(cfg, con, bundle["asof"]).values()
                for p in ps}
    ev = {e["ticker"]: e for e in bundle["evren"]}
    for st in out["stocks"]:
        analist = {k: v for k, v in st.items() if k in journal.ANALIST_ALANLARI}
        journal.record(
            cfg, con, run_id=run_id, asof=bundle["asof"], ticker=st["ticker"],
            analist=analist, plan=plan_map.get(st.get("selected_plan_id")) or {},
            faktor=llm_io.faktor_to_journal(ev[st["ticker"]].get("faktorler")),
            regime=bundle["rejim"]["etiket"],
            referans={"close": ev[st["ticker"]]["fiyat"]["kapanis"],
                      "atr14": ev[st["ticker"]]["gostergeler"].get("atr14")})
    return run_id


@pytest.fixture
def hat(cfg, con):
    """Paketi kurulmuş, plan üretilmiş bir dünya. `asof`'tan sonra 40 bar var."""
    asof = kur_sentetik_evren(cfg, con, asof_geri=40)
    bundle = llm_io.build_bundle(cfg, con, asof)
    llm_io.write_bundle(cfg, bundle)
    planli = [e["ticker"] for e in bundle["evren"] if e["plan_menusu"]]
    return {"asof": asof, "bundle": bundle, "planli": planli}


# ============================================================ 1. paket → denetim
class TestPaketDenetimden_GECER:
    def test_gecerli_cikti_SERT_HATA_uretmez(self, cfg, con, hat):
        """Kurulum anlamsızlaşmasın: elle yazılmış geçerli çıktı GEÇMELİ.

        Bu testin patlaması iki şeyden birini söyler — ya denetim aşırı
        sıkılaştı (meşru çıktıyı reddediyor), ya paket ile şema ayrıştı. İkisi
        de sessizce sistemi kullanılamaz hale getirir.
        """
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        bulgular = audit.audit(cfg, hat["bundle"], out, con)
        sert = audit.hard_fails(bulgular)
        assert not sert, [f"{f.code}[{f.ticker}] {f.message}" for f in sert]

    def test_planli_hisse_gercekten_var(self, hat):
        assert hat["planli"], (
            "sentetik kurulum hiç plan üretmiyor — uçtan uca test anlamsızlaşır")

    def test_uydurulmus_FIYAT_journal_a_giremez(self, cfg, con, hat):
        """HF-17/HF-18 taşıyıcı kol: prose'a uydurma fiyat yazmak hattı DURDURUR."""
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        out["stocks"][0]["thesis"] += " Hedef 91827.36 TL civarında makul görünüyor."
        kodlar = {f.code for f in audit.hard_fails(audit.audit(cfg, hat["bundle"], out, con))}
        assert kodlar & {"HF-17", "HF-18"}, kodlar

    def test_uydurulmus_PLAN_ID_journal_a_giremez(self, cfg, con, hat):
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        out["stocks"][0]["action"] = "plan_sec"
        out["stocks"][0]["selected_plan_id"] = "UYDURMA-2026-01-01-Z"
        kodlar = {f.code for f in audit.hard_fails(audit.audit(cfg, hat["bundle"], out, con))}
        assert "HF-12" in kodlar

    def test_EKSIK_hisse_journal_a_giremez(self, cfg, con, hat):
        """Evrendeki bir isim sessizce atlanamaz (HF-06)."""
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        out["stocks"] = out["stocks"][:-1]
        kodlar = {f.code for f in audit.hard_fails(audit.audit(cfg, hat["bundle"], out, con))}
        assert "HF-06" in kodlar

    def test_ESKI_PAKET_analiz_edilirse_yakalanir(self, cfg, con, hat):
        """HF-02: sessiz felaket — sayılar bugünün, yorum dünün olur."""
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        out["bundle_sha"] = "eski" + out["bundle_sha"][4:]
        kodlar = {f.code for f in audit.hard_fails(audit.audit(cfg, hat["bundle"], out, con))}
        assert "HF-02" in kodlar

    def test_SABLON_tez_yakalanir(self, cfg, con, hat):
        """Tüm hisselere aynı prose yazmak HF-27'yi patlatır."""
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        for s in out["stocks"]:
            for k in PROSE:
                s[k] = PROSE[k].format(t="AYNI")
        kodlar = {f.code for f in audit.hard_fails(audit.audit(cfg, hat["bundle"], out, con))}
        assert "HF-27" in kodlar


# ============================================================ 2. journal
class TestKaydetmeYolu:
    def test_tum_hisseler_journal_a_yazilir(self, cfg, con, hat):
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        _kaydet(cfg, con, hat["bundle"], out)
        n = db.scalar(con, "SELECT COUNT(*) FROM predictions WHERE asof = ?",
                      (hat["asof"],))
        assert n == len(hat["bundle"]["evren"])

    def test_KOD_yazdigi_alanlar_dolu(self, cfg, con, hat):
        """`score` / `pct` / `confidence_p` / referans anları KOD tarafından yazılır.

        Bunlardan biri boş kalırsa ölçüm zinciri sessizce kopar: IC skoru
        okuyamaz, Brier `confidence_p` olmadan hesaplanamaz, slippage referans
        kapanışa dayanır.
        """
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        _kaydet(cfg, con, hat["bundle"], out)
        satirlar = db.fetch_all(con, "SELECT * FROM predictions WHERE asof = ?",
                                (hat["asof"],))
        harita = cfg["llm"]["guven_olasilik"]
        for r in satirlar:
            assert r["score"] is not None, r["ticker"]
            assert r["pct"] is not None, r["ticker"]
            assert r["weights_hash"], r["ticker"]
            assert r["close_at_asof"] is not None
            assert r["confidence_p"] == pytest.approx(harita[r["confidence"]])
            assert r["factor_set_version"] == cfg["faktorler"]["set_version"]
            assert r["indicator_set_version"] == cfg["gostergeler"]["set_version"]
            assert r["regime"] == hat["bundle"]["rejim"]["etiket"]

    def test_plan_secilen_hissede_PLAN_FIYATLARI_plandan_gelir(self, cfg, con, hat):
        t = hat["planli"][0]
        out = _analist_cikti(hat["bundle"], plan_secilen=t)
        _kaydet(cfg, con, hat["bundle"], out)
        r = db.fetch_one(con, "SELECT * FROM predictions WHERE ticker = ?", (t,))
        plan = [e for e in hat["bundle"]["evren"] if e["ticker"] == t][0]["plan_menusu"][0]
        assert r["plan_id"] == plan["plan_id"]
        assert r["entry_low"] == pytest.approx(plan["entry_low"])
        assert r["stop_price"] == pytest.approx(plan["stop_price"])
        assert r["t1_price"] == pytest.approx(plan["targets"][0]["price"])
        assert r["rr_at_t1"] == pytest.approx(plan["rr_at_t1"])
        assert r["time_barrier_date"] == plan["time_barrier_date"]

    def test_plan_secilmeyen_hissede_fiyat_alanlari_BOS(self, cfg, con, hat):
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        _kaydet(cfg, con, hat["bundle"], out)
        izleyen = [s["ticker"] for s in out["stocks"] if s["action"] == "izle"][0]
        r = db.fetch_one(con, "SELECT * FROM predictions WHERE ticker = ?", (izleyen,))
        assert r["plan_id"] is None and r["stop_price"] is None

    def test_ayni_run_ikinci_kez_yazamaz(self, cfg, con, hat):
        """Journal DEĞİŞMEZDİR — düzeltme yeni bir run açar."""
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        _kaydet(cfg, con, hat["bundle"], out)
        run1 = db.scalar(con, "SELECT run_id FROM llm_runs LIMIT 1")
        with pytest.raises(RuntimeError, match="DEĞİŞMEZ"):
            journal.record(
                cfg, con, run_id=run1, asof=hat["asof"],
                ticker=out["stocks"][0]["ticker"],
                analist={k: v for k, v in out["stocks"][0].items()
                         if k in journal.ANALIST_ALANLARI},
                referans={"close": 100.0})

    def test_yeni_run_ile_yeniden_yazilabilir(self, cfg, con, hat):
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        _kaydet(cfg, con, hat["bundle"], out)
        _kaydet(cfg, con, hat["bundle"], out)
        assert db.scalar(con, "SELECT COUNT(DISTINCT run_id) FROM predictions") == 2


# ============================================================ 3. çözüm
class TestCozumYolu:
    def test_plan_secilen_tahmin_COZULUR(self, cfg, con, hat):
        """Zaman bariyerine kadar bar varsa sonuç yazılmalı.

        Çözülmeyen bir tahmin sessizce AÇIK kalır ve hiçbir metriğe girmez —
        yani ölçüm zinciri kopar ama hata çıkmaz.
        """
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        _kaydet(cfg, con, hat["bundle"], out)
        r = resolver.resolve_open(cfg, con)
        assert r["cozulen"] >= 1, r
        assert set(r["dagilim"]) <= {resolver.HEDEF, resolver.STOP, resolver.SURE,
                                     resolver.GIRIS_OLMADI, resolver.IPTAL_KURUMSAL,
                                     resolver.IPTAL_VERI}

    def test_plansiz_tahminler_ACIK_KALIR(self, cfg, con, hat):
        """`izle` kararı bir plan değildir; bariyeri yoktur, çözülemez."""
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        _kaydet(cfg, con, hat["bundle"], out)
        resolver.resolve_open(cfg, con)
        acik = journal.open_predictions(con)
        assert all(p["time_barrier_date"] is None for p in acik)

    def test_sonuc_satiri_KOD_alanlarini_tasir(self, cfg, con, hat):
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        _kaydet(cfg, con, hat["bundle"], out)
        resolver.resolve_open(cfg, con)
        for o in db.fetch_all(con, "SELECT * FROM outcomes"):
            assert o["resolver_version"] == resolver.RESOLVER_VERSION
            assert o["resolved_utc"]
            assert o["resolution"]
            if o["resolution"] in (resolver.HEDEF, resolver.STOP, resolver.SURE):
                assert o["ret_pct"] is not None
                assert o["hit"] in (0, 1)
                # maliyet DÜŞÜLÜR — brütten küçük olmak zorunda
                assert o["ret_pct"] < o["ret_pct_gross"]

    def test_ikinci_cozum_turu_TEKRAR_YAZMAZ(self, cfg, con, hat):
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        _kaydet(cfg, con, hat["bundle"], out)
        a = resolver.resolve_open(cfg, con)
        b = resolver.resolve_open(cfg, con)
        assert b["cozulen"] == 0
        assert db.scalar(con, "SELECT COUNT(*) FROM outcomes") == a["cozulen"]


# ============================================================ 4. değerlendirme
class TestDegerlendirmeYolu:
    def test_bos_journalda_bile_rapor_URETILIR(self, cfg, con):
        """Taze kurulumda `bist degerlendir` ÇÖKMEZ.

        Eksik anahtar bu komutu taze kurulumda KeyError ile çökertiyordu; boş
        dönüşte de tüm anahtarların bulunması sözleşmenin parçası.
        """
        e = evaluate.run(cfg, con)
        metin = report.evaluate_report(cfg, e)
        assert "Değerlendirme Raporu" in metin

    def test_uctan_uca_rapor_ERKEN_KENAR_IDDIA_ETMEZ(self, cfg, con, hat):
        """Az gözlemle "kenar var" denemez — bu raporun ana davranışı."""
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        _kaydet(cfg, con, hat["bundle"], out)
        resolver.resolve_open(cfg, con)
        e = evaluate.run(cfg, con)
        metin = report.evaluate_report(cfg, e)

        # Açıklama satırı ("bu sistemde 'doğrulandı' YOKTUR") serbest; yasak
        # olan, bir HÜKÜM hücresinde geçmesi.
        hukumler = [h for satir in metin.splitlines() if satir.startswith("|")
                    for h in satir.split("|") if "**" in h]
        assert not any("doğrulandı" in h.lower() or "kanıtlandı" in h.lower()
                       for h in hukumler), hukumler
        assert "gerekli N" in metin
        assert e["tool"] == "claude-code"
        # N küçük olduğu için hüküm "ölçüm yetersiz" ya da "ölçüm yok" olmalı
        assert e["alfa"]["hukum"].startswith(("ölçüm", "kenar yok")), e["alfa"]["hukum"]

    def test_KARISIK_KAYNAK_reddedilir(self, cfg, con, hat):
        """`replay` VEKİL analisttir; gerçek analizle aynı potaya girmez.

        Sessizce birleştirmek ölçümün NE ölçtüğünü belirsizleştirir ve rapor
        bunu hiçbir yerde yazmaz.
        """
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        _kaydet(cfg, con, hat["bundle"], out)
        resolver.resolve_open(cfg, con)
        # ikinci bir araçtan kayıt
        out2 = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0],
                              tool="replay")
        _kaydet(cfg, con, hat["bundle"], out2)
        resolver.resolve_open(cfg, con)
        with pytest.raises(evaluate.KaynakKarisik, match="--tool"):
            evaluate.run(cfg, con)
        # açık kaynak verilince koşar
        assert evaluate.run(cfg, con, tool="replay")["tool"] == "replay"


# ============================================================ 5. günlük rapor
class TestGunlukRapor:
    def test_analist_YOKSA_rapor_bunu_SOYLER(self, cfg, con, hat):
        """Deterministik katmanı "rapor" diye sunmak yanıltıcı olurdu."""
        metin = report.daily_report(cfg, hat["bundle"], holdings={}, analiz=None)
        assert "Analist çıktısı yok" in metin

    def test_analist_VARSA_tez_ve_sinyal_rapora_GIRER(self, cfg, con, hat):
        """İlk sürüm yalnız paketi okuyordu; analistin tezi, karşı senaryosu ve
        VETOSU Mert'in okuduğu belgeye HİÇ ulaşmıyordu."""
        t = hat["planli"][0]
        out = _analist_cikti(hat["bundle"], plan_secilen=t)
        _kaydet(cfg, con, hat["bundle"], out)
        analiz = db.fetch_all(con, "SELECT * FROM predictions WHERE asof = ?",
                              (hat["asof"],))
        metin = report.daily_report(cfg, hat["bundle"], holdings={}, analiz=analiz)
        assert "Analist çıktısı yok" not in metin
        assert PROSE["thesis"].format(t=t)[:40] in metin
        assert "plan_sec" in metin

    def test_rapor_AZALT_bolumuyle_baslar(self, cfg, con, hat):
        """Ölçüldü: alt kuyruk üst kuyruğun ~1.8 katı ve retail açığa satamaz →
        sistemin en savunulabilir çıktısı "hangisini azalt". Rapor sırası bu
        ölçümden geliyor; çoğu perakende araç bunu ters yapar."""
        metin = report.daily_report(cfg, hat["bundle"], holdings={}, analiz=None)
        i_azalt = metin.index("## 1. Elindekiler")
        i_plan = metin.index("## 2. Plan geometrisi")
        assert i_azalt < i_plan
        assert cfg["rapor"]["once_azalt_bolumu"] is True

    def test_raporda_KENAR_IDDIASI_yok(self, cfg, con, hat):
        metin = report.daily_report(cfg, hat["bundle"], holdings={}, analiz=None)
        assert "doğrulandı" not in metin.lower()
        assert "öneri değil" in metin
        assert "yatırım tavsiyesi değildir" in metin.lower()

    def test_above_zone_orani_GOSTERILEN_plana_ait(self, cfg, con, hat):
        """⚠ NE OLMUŞTU: banner paydası TÜM aday planları sayıyordu
        (`sum(len(plan_menusu))`) ama gövde her hisseden yalnız `plan_menusu[0]`
        basıyor. 2026-07-30 raporu "3/7 plan above_zone" diyordu; ekranda 3 plan
        vardı ve ÜÇÜ DE `in_zone`'du. Okuyan, hiç göremediği bir oranı
        doğrulamaya çalışıyordu — üç bağımsız dış inceleme buna takıldı.
        """
        import re
        metin = report.daily_report(cfg, hat["bundle"], holdings={}, analiz=None)
        m = re.search(r"\*\*(\d+)/(\d+) plan `above_zone`\*\*", metin)
        assert m, "above_zone banner'ı raporda bulunamadı"
        planli = [e for e in hat["bundle"]["evren"] if e["plan_menusu"]]
        gosterilen = [e["plan_menusu"][0] for e in planli]
        assert int(m.group(2)) == len(gosterilen), (
            f"payda {m.group(2)} ama gövdede {len(gosterilen)} plan gösteriliyor")
        assert int(m.group(1)) == sum(
            1 for p in gosterilen if p.get("entry_zone_status") == "above_zone")

    def test_veto_tablosu_YURURLUKTEKI_tekrari_der(self, cfg, con, hat):
        """⚠ NE OLMUŞTU: sütun "tekrar → 3× üst üste" diyordu.

        `journal.aktif_vetolar` süresi DOLANI eliyor, yani saydığı şey ardışık
        bir seri değil, bugün hâlâ yürürlükte olan tekrar sayısı. Bu yüzden
        veto yeniden konmadan sayı 3'ten 2'ye düşebiliyordu ve bir dış inceleme
        bunu "sayaç geriye gidiyor" diye bug raporladı. Sayaç doğruydu; etiket
        iki farklı olguyu aynı kelimeyle adlandırıyordu (L-003).
        """
        bundle = json.loads(json.dumps(hat["bundle"]))     # kopyala, bozma
        bundle["evren"][0]["aktif_vetolar"] = [{
            "veto_code": "tez_zayif", "konuldu": "2026-08-05",
            "bitis": "2026-08-12", "kalan_islem_gunu": 2,
            "arac": "test", "gerekce": "x", "tekrar": 3}]
        metin = report.daily_report(cfg, bundle, holdings={}, analiz=None)
        assert "yürürlükteki tekrar" in metin
        assert "3× yürürlükte" in metin
        assert "üst üste" not in metin, \
            "etiket hâlâ ardışık seri iddia ediyor — sayılan şey o değil"

    def test_plan_yok_SINIFA_gore_gruplanir(self, cfg, con, hat):
        """⚠ NE OLMUŞTU: plan üretilmeyen her isim tek ve aynı cümleyi alıyordu
        ("stop∈[...]×ATR + R:R≥1.5 kurallarını BİRLİKTE sağlayamadı"). 2026-08-12
        huni teşhisinde elenen 15 ismin 15'inde de stop bandı geçmişti; öldüren
        tek şey R:R'dı. Gerekçe okuyanı yanlış kurala baktırıyordu.
        """
        metin = report.daily_report(cfg, hat["bundle"], holdings={}, analiz=None)
        planyok = [e for e in hat["bundle"]["evren"] if not e["plan_menusu"]]
        if not planyok:
            pytest.skip("bu kurulumda plan üretilmeyen isim yok")
        assert all(e.get("plan_yok_detay") for e in planyok), \
            "pakette ince sınıf taşınmıyor — rapor gruplayamaz"
        etiketler = {planner.PLAN_YOK_ETIKET[e["plan_yok_detay"]] for e in planyok}
        assert any(f"**{et}**" in metin for et in etiketler), \
            f"bölüm 3 sınıf başlığı basmıyor; beklenen: {etiketler}"

    def test_rapor_dosyaya_YAZILIR(self, cfg, con, hat):
        metin = report.daily_report(cfg, hat["bundle"], holdings={}, analiz=None)
        yol = report.write(cfg, f"gunluk_{hat['asof']}.md", metin)
        assert util.resolve(yol).exists()
        assert cfg["paths"]["reports_dir"] in str(yol)


# ============================================================ 6. bütünlük
class TestBoruHattiButunlugu:
    def test_evren_TAMAMI_pakette(self, cfg, con, hat):
        """Canlı evrendeki bir isim paketten düşerse analist onu göremez ve
        HF-06 de tetiklenmez — sessizce kapsam dışı kalır."""
        canli = set(universe.live(con))
        pakette = {e["ticker"] for e in hat["bundle"]["evren"]}
        assert pakette == canli

    def test_planlar_journal_FK_si_icin_SAKLANIR(self, cfg, con, hat):
        """Tahmin, referans verdiği planın kaybolmasına dayanamaz."""
        out = _analist_cikti(hat["bundle"], plan_secilen=hat["planli"][0])
        _kaydet(cfg, con, hat["bundle"], out)
        eksik = db.fetch_all(
            con, "SELECT p.ticker FROM predictions p LEFT JOIN plan_options o "
                 "  ON o.plan_id = p.plan_id "
                 " WHERE p.plan_id IS NOT NULL AND o.plan_id IS NULL")
        assert eksik == []

    def test_dondurulmus_tablolar_GERCEKTEN_yaziliyor(self, cfg, con, hat):
        """`factor_daily` / `levels_daily` / `regime_daily` uzun süre BOŞTU.

        Üçü de "girdiler denetlenebilir biçimde saklanır" diye belgelenmişti ama
        besleyen çağrı yoktu (LESSONS L-002). Paket üretimi artık üçünü de
        yazıyor; bu test onu sabitler.
        """
        for tablo in ("factor_daily", "levels_daily", "regime_daily"):
            n = db.scalar(con, f"SELECT COUNT(*) FROM {tablo}")
            assert n > 0, f"{tablo} boş — besleyen çağrı kayboldu"

    def test_paket_dosyasi_diske_yazildi_ve_geri_okunabilir(self, cfg, con, hat):
        yol = util.resolve(f"{cfg['paths']['llm_in_dir']}/{hat['asof']}/bundle.json")
        assert yol.exists()
        geri = json.loads(yol.read_text(encoding="utf-8"))
        assert geri["bundle_sha"] == hat["bundle"]["bundle_sha"]
        # Diskten okunan paketle denetim yine geçmeli (JSON gidiş-dönüşü)
        out = _analist_cikti(geri, plan_secilen=hat["planli"][0])
        assert not audit.hard_fails(audit.audit(cfg, geri, out, con))


# ============================================================ 6. otonom koşu
class TestOtonomKosu:
    """Faz 8: `bist otonom gunluk` zinciri — MOCK'SUZ modüller arası akış.

    `test_otonom.py` orkestrasyonu (hangi hata durdurur?) sahte adımlarla
    sınar. Burada tersi yapılır: adımlar GERÇEK, yalnız dış dünya (yfinance,
    KAP, Telegram, LLM) kapatılır. Yakaladığı hata sınıfı farklı — her modül
    tek başına doğruyken aralarındaki varsayımın kırılması (AGENTS.md §12).
    """

    @pytest.fixture
    def dis_dunya_kapali(self, cfg, con, monkeypatch):
        """Ağ çağrılarını sustur; veri ZATEN kurulu olsun."""
        from src import indicators, news, otonom, prices
        from src.calendar_bist import BistCalendar

        # `asof_geri=0`: otonom koşu `MAX(bars_daily.date)`i asof sayar; seride
        # "gelecek" bar bırakmak kalite kaydıyla barları ayrıştırır ve sağlık
        # kapısı — HAKLI OLARAK — bayat der. Burada canlı günü taklit ediyoruz.
        asof = kur_sentetik_evren(cfg, con)
        # Takvim: `asof` son kapalı seans olsun ki `bar tazeliği` temiz çıksın.
        monkeypatch.setattr(BistCalendar, "last_closed_session",
                            lambda self, ts=None: date.fromisoformat(asof))
        monkeypatch.setattr(BistCalendar, "is_trading_day", lambda self, d: True)
        # Dış kaynaklar: veri zaten var, tekrar çekilmesin.
        monkeypatch.setattr(prices, "daily", lambda *a, **k: {
            "tickers": 6, "hayalet_silinen": 0, "yarim_bar_silinen": 0,
            "kalite_gecmeyen": 0, "kalite_degerlendirilen": 6, "start": asof})
        monkeypatch.setattr(indicators, "compute_and_store", lambda *a, **k: {
            "satir": {"AAA": 320}, "tickers": 6, "set_version": "v1"})
        monkeypatch.setattr(news, "sync", lambda *a, **k: {
            "yazilan": 0, "atlanan_aralik": None})
        # Haber katmanı sağlık kontrolünden geçsin diye bir bildirim koy.
        con.execute(
            "INSERT OR REPLACE INTO disclosures (disclosure_id,ticker,"
            "published_utc,tier,title,fetched_utc) VALUES ('kap-e2e','AAA',?,1,'t',?)",
            (f"{asof}T10:00:00+00:00", util.utc_now_iso()))
        con.commit()
        gonderilen: list[str] = []
        monkeypatch.setattr(otonom.tg, "bildir",
                            lambda c, m: gonderilen.append(m) or True)
        return {"asof": asof, "telegram": gonderilen}

    def test_analistsiz_kosu_UCTAN_UCA(self, cfg, con, dis_dunya_kapali):
        """Zincirin tamamı: sağlık → paket → çözüm → rapor → bildirim."""
        from src import otonom

        s = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29),
                          analist_calistir=False)

        assert otonom.basarisiz_mi(s) == [], f"kritik adım düştü: {s.get('hatalar')}"
        assert s["asof"] == dis_dunya_kapali["asof"]
        # Rapor GERÇEKTEN diske yazıldı ve okunabilir
        yol = Path(s["rapor"])
        assert yol.exists() and "BIST Günlük" in yol.read_text(encoding="utf-8")
        # Telegram özeti gitti ve zorunlu ibareyi taşıyor
        assert dis_dunya_kapali["telegram"], "bildirim gönderilmedi"
        assert "kenar yok" in dis_dunya_kapali["telegram"][0].lower()

    def test_analist_zinciriyle_journala_YAZAR(self, cfg, con, dis_dunya_kapali,
                                               monkeypatch):
        """Zincir temiz çıktı verirse tahminler journal'a girer ve `tool`
        alanı MODEL KİMLİĞİ olur — ölçüm bu alana dayanıyor."""
        from src import analist, otonom

        asof = dis_dunya_kapali["asof"]

        def sahte_model(c, model_id, prompt):
            # Paketi DİSKTEN oku — gerçek analist de öyle yapar. Testte
            # önceden kurulmuş bir paket kullanmak HF-02'ye takılır: her
            # `build_bundle` çağrısı `generated_utc` yazdığı için sha değişir.
            b = util.read_json(f"{cfg['paths']['llm_in_dir']}/{asof}/bundle.json")
            planli = [e["ticker"] for e in b["evren"] if e["plan_menusu"]]
            out = _analist_cikti(b, plan_secilen=planli[0] if planli else None)
            out["tool"] = "yanlis-beyan"        # model kendini yanlış tanıtıyor
            return json.dumps(out)

        monkeypatch.setattr(analist, "_cagir", sahte_model)
        monkeypatch.setattr(analist, "zincir", lambda c: ["gemini-3.5-flash"])

        s = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29))

        assert otonom.basarisiz_mi(s) == [], f"kritik adım düştü: {s.get('hatalar')}"
        assert s.get("analist_model") == "gemini-3.5-flash"
        assert s.get("kaydedilen", 0) > 0
        arac = db.scalar(con, "SELECT tool FROM llm_runs WHERE run_id = ?",
                         (s["run_id"],))
        assert arac == "gemini-3.5-flash", "journal modelin YANLIŞ beyanını yazmış"

    def test_zincir_dususu_raporu_ENGELLEMEZ(self, cfg, con, dis_dunya_kapali,
                                             monkeypatch):
        """Analist kritik DEĞİL: zincirin tamamı düşse de o günün plan
        geometrisi ve raporu üretilmeli (ADR #013)."""
        from src import analist, otonom

        monkeypatch.setattr(analist, "zincir", lambda c: ["a", "b"])
        monkeypatch.setattr(analist, "_cagir", lambda c, m, p: (
            _ for _ in ()).throw(RuntimeError("429 kota")))

        s = otonom.gunluk(cfg, con, bugun=date(2026, 7, 29))

        assert "analist" in s["hatalar"]
        assert otonom.basarisiz_mi(s) == []
        assert Path(s["rapor"]).exists()
        assert "Analist çıktısı yok" in dis_dunya_kapali["telegram"][0]

    # ══════════════════════════════════════════════════════════════════════
    # KİLİTLENME — L-016'nın uçtan uca kilidi
    # ══════════════════════════════════════════════════════════════════════
    def test_ATLANMIS_gunden_sonra_zincir_UCTAN_UCA_TAMAMLANIR(
            self, cfg, con, dis_dunya_kapali, monkeypatch):
        """⚠⚠ DÖRT İŞLEM GÜNÜ SÜREN ÜRETİM ARIZASININ KİLİDİ (2026-08-06→11).

        NE OLMUŞTU — sırayla:
          1. 2026-08-06'da GitHub runner günlük işi almadı. Koşu HİÇ başlamadı;
             ne rapor, ne Telegram, ne hata. O gün tamamen sessizdi.
          2. Ertesi gün L-015'in "atlanan koşu" kontrolü `MAX(predictions.asof)`
             ile son barı karşılaştırdı, farkı 2 buldu ve **KRİTİK** döndü.
          3. `otonom.gunluk` KRİTİK'te durur — ve `predictions` tam olarak o
             durduğu noktanın ARKASINDA yazılır. Kapının açılması için gereken
             şey kapının arkasındaydı.
          4. Fark her işlem günü 1 arttı: 2 → 3 → 4 → ... Sistem veri çekmeye ve
             commit atmaya devam etti, **sıfır analiz üretti**, her gün aynı 🛑
             mesajını gönderdi. Kendi kendini süresiz kilitlemişti.

        Birim testlerin HİÇBİRİ bunu göremezdi: `saglik` doğru çalışıyordu,
        `otonom` doğru çalışıyordu, kırılan şey aralarındaki varsayımdı
        (AGENTS.md §12, üçüncü katman).

        Bu test o senaryoyu kurar: journal bilerek GERİDE bırakılır ve zincirin
        UÇTAN UCA tamamlanması istenir. Kilit geri gelirse burası kırmızı yanar.
        """
        from src import analist, otonom

        asof = dis_dunya_kapali["asof"]

        # 1) Journal'ı GERİDE bırak: 10 işlem günü önce bir tahmin, sonrası yok.
        #    (Gerçek olayda fark 2'den başlayıp büyüyordu; 10 fazlasıyla temsil eder.)
        eski = db.fetch_all(
            con, "SELECT DISTINCT date FROM bars_daily ORDER BY date DESC LIMIT 11"
        )[-1]["date"]
        db.upsert_many(con, "llm_runs",
                       ["run_id", "asof", "tool", "bundle_sha", "output_path",
                        "audit_passed", "created_utc"],
                       [("eski-run", eski, "test", "s", "", 1, "now")])
        db.upsert_many(
            con, "predictions",
            ["prediction_id", "run_id", "asof", "ticker", "signal", "action",
             "confidence", "confidence_p", "factor_set_version", "weights_hash",
             "indicator_set_version", "regime", "thesis", "counter_scenario",
             "key_risk", "falsifier", "close_at_asof", "created_utc"],
            [("eski-p", "eski-run", eski, "AAA", "hold", "izle", "orta", 0.5,
              "v1", "h", "v1", "neutral", "t", "c", "k", "f", 100.0, "now")])

        def sahte_model(c, model_id, prompt):
            b = util.read_json(f"{cfg['paths']['llm_in_dir']}/{asof}/bundle.json")
            planli = [e["ticker"] for e in b["evren"] if e["plan_menusu"]]
            return json.dumps(_analist_cikti(
                b, plan_secilen=planli[0] if planli else None))

        monkeypatch.setattr(analist, "_cagir", sahte_model)
        monkeypatch.setattr(analist, "zincir", lambda c: ["gemini-3.5-flash"])

        s = otonom.gunluk(cfg, con, bugun=date.fromisoformat(asof))

        # ⚠ ASIL İDDİA: zincir DURMADI ve yeni tahmin ÜRETTİ.
        assert otonom.basarisiz_mi(s) == [], (
            f"geride kalmış journal koşuyu durdurdu — KİLİT GERİ GELDİ: "
            f"{s.get('hatalar')}")
        assert s.get("kaydedilen", 0) > 0, "yeni tahmin yazılmadı"
        assert db.scalar(con, "SELECT MAX(asof) FROM predictions") == asof, (
            "journal ilerlemedi — bir sonraki koşu yine aynı boşluğu görecekti")
        assert Path(s["rapor"]).exists()

        # Boşluk GÖRÜNMEZ olmadı: uyarı olarak raporlanıyor, kapı olarak değil.
        adlar = {b[1] for b in s["saglik"]["uyari"]}
        assert "analizsiz gün" in adlar, (
            "boşluk sessizce yutuldu — uyarmadan geçmek de bir arızadır")

    def test_HEARTBEAT_kapi_kapansa_bile_yazilir(self, cfg, con, dis_dunya_kapali,
                                                 monkeypatch):
        """Kilidin ikinci yarısı: sayaç KAPININ ÖNÜNDE ilerlemeli.

        Heartbeat kapıdan sonra yazılsaydı, durdurulan bir koşu "hiç koşmadım"
        derdi ve `atlanan koşu` her gün alarm verirdi — yani gözlemci yine
        gözlediği şeyin ürününe bağlı kalırdı.
        """
        from src import otonom, saglik

        # Sağlık kapısını ZORLA kapat (veri bütünlüğü arızası taklidi).
        gercek = saglik.kontrol
        monkeypatch.setattr(saglik, "kontrol", lambda c, o, **k: {
            **gercek(c, o, **k),
            "kritik": [("KRİTİK", "bar tazeliği", "taklit arıza")]})

        gun = date.fromisoformat(dis_dunya_kapali["asof"])
        s = otonom.gunluk(cfg, con, bugun=gun, analist_calistir=False)

        assert "saglik" in s["hatalar"], "kapı kapanmadı — test kendini kandırıyor"
        kayit = db.fetch_one(con, "SELECT * FROM otonom_kosu WHERE kosu_id = ?",
                             (s["kosu_id"],))
        assert kayit is not None, "kapı kapanınca heartbeat HİÇ yazılmamış"
        assert kayit["durum"] == "durduruldu"
        assert kayit["tarih_tr"] == gun.isoformat()
