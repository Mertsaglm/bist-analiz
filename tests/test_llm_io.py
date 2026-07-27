"""LLM girdi paketi testleri — PAKET DIŞINDA GİRDİ YOKTUR.

`build_bundle`'ın sözleşmesi: analistin göreceği her şey pakette. Pakette
olmayan bir sayı prose'da geçemez (HF-17), pakette olmayan bir plan seçilemez
(HF-12), pakette olmayan bir haber referans verilemez (HF-28). Yani paket
denetimin OTORİTESİDİR — eksik bir alan, denetimin o boyutta kör kalması demek.

Bunun canlı örneği yaşandı: faktör skorları pakete GİRMİYORDU. Sonucu iki
yerdeydi ve ikisi de sessizdi — HF-22 (sıralamayı ezme kontrolü) üretimde HİÇ
ateşlenemiyordu ve `bist kaydet` NOT NULL hatasıyla patlıyordu.

İkinci bölüm sayısal token normalizasyonunu sabitler. `_varyantlar`ın ilk
sürümü YUVARLAYARAK biçim üretiyordu ve bu HF-17'de delik açıyordu: uydurma
"47.3" değeri "47" varyantını doğuruyor, pakette 47.00 varsa denetimi
ATLIYORDU.
"""

from __future__ import annotations

import json

import pytest

from src import llm_io, schema, util

from tests.conftest import kur_sentetik_evren


@pytest.fixture
def paket(cfg, con):
    """Sentetik ama GERÇEK boru hattından geçmiş paket."""
    asof = kur_sentetik_evren(cfg, con)
    return llm_io.build_bundle(cfg, con, asof)


# ============================================================ token normalizasyonu
class TestVaryantlar:
    def test_deger_degistirmeyen_bicimler_uretilir(self):
        assert llm_io._varyantlar(47.0, 2) == {"47", "47.0", "47.00"}
        assert llm_io._varyantlar(312.5, 2) == {"312.5", "312.50"}

    def test_YUVARLAYARAK_bicim_URETILMEZ(self):
        """`47.3` için "47" ÜRETİLMEZ — o başka bir sayıdır.

        ⚠ Bu ilk sürümdeki gerçek bir delikti: her sayı için 0/1/2 basamaklı
        biçimler KOŞULSUZ üretiliyordu. Prose'daki uydurma "47.3" değeri "47"
        varyantını doğuruyor ve pakette 47.00 varsa HF-17'yi atlıyordu. Denetim
        biçim farkını değil DEĞER farkını cezalandırmak zorunda.
        """
        v = llm_io._varyantlar(47.3, 2)
        assert "47" not in v and "47.0" not in v
        assert v == {"47.3", "47.30"}

    def test_iki_ondalikli_deger_tam_sayiya_dusmez(self):
        v = llm_io._varyantlar(47.25, 2)
        assert v == {"47.25"}

    def test_negatif_deger_isareti_korunur(self):
        assert "-3.50" in llm_io._varyantlar(-3.5, 2)
        assert "3.50" not in llm_io._varyantlar(-3.5, 2)


class TestSayiAyristirma:
    @pytest.mark.parametrize("metin,deger", [
        ("1234.56", 1234.56),
        ("1.234,56", 1234.56),      # TR binlik + ondalık
        ("1,234.56", 1234.56),      # EN binlik + ondalık
        ("42", 42.0),
        ("-3.5", -3.5),
        ("12,5", 12.5),             # TR ondalık
        ("1,234", 1234.0),          # tek virgül + 3 basamak → binlik
    ])
    def test_TR_ve_EN_yazim_ayni_degere_duser(self, metin, deger):
        assert llm_io._parse_sayi(metin) == pytest.approx(deger)

    def test_bozuk_token_None(self):
        assert llm_io._parse_sayi("") is None
        assert llm_io._parse_sayi("abc") is None

    def test_TR_ve_EN_yazim_ayni_TOKENA_duser(self):
        """Biçim değiştirerek denetimi atlatmak mümkün olmamalı."""
        assert (llm_io.numeric_tokens("hedef 1.234,56 seviyesinde")
                & llm_io.numeric_tokens("hedef 1234.56 seviyesinde"))

    def test_belirsiz_1_234_IKI_YORUMU_da_uretir(self):
        """"1.234" hem binlik hem ondalık olabilir; İKİSİ de token üretir.

        Binlik yorumu `1234`; ondalık yorumu ise `ondalik_tolerans_basamak`
        (=2) ile kanonikleşir ve `1.23` olur. İki yorumdan yalnız birini
        üretmek, TR yazımıyla yazılmış meşru bir sayıyı uydurma sayardı.
        """
        tok = llm_io.numeric_tokens("seviye 1.234")
        assert "1234" in tok, "binlik yorumu üretilmiyor"
        assert "1.23" in tok, "ondalık yorumu üretilmiyor"


class TestTarihMaskesi:
    def test_prose_daki_tarih_TOKEN_uretmez(self):
        """Analist "bariyer 2026-08-21'e kadar" yazabilmeli.

        Maskeleme olmasa HF-17, sayı uydurmayı değil TAKVİM YAZMAYI cezalandırırdı.
        `YYYY-AA-GG` bir fiyat ya da yüzde ifade edemez, dolayısıyla maskelemek
        kaçış yolu açmaz.
        """
        assert llm_io.numeric_tokens("bariyer 2026-08-21'e kadar") == set()
        assert llm_io.numeric_tokens("2026-07-24T21:04:50+00:00") == set()
        assert llm_io.numeric_tokens("saat 09:40'ta") == set()

    def test_paketteki_tarih_NEGATIF_TAMSAYI_enjekte_etmez(self, real_cfg):
        """⚠ Ölçülmüş bir kazara sızıntı: `-07`, `-24` izinli listeye giriyordu.

        Sonuç: prose'daki uydurma "%-7 geriledi" denetimden temiz geçiyor ve
        hangi negatif sayının geçtiği O GÜNKÜ TAKVİME bağlı oluyordu. Bir
        denetimin gücünün tarihe göre değişmesi, denetim olmamasıyla aynı şeydir.
        """
        izin = llm_io.allowed_numeric_tokens({"asof": "2026-07-24"}, real_cfg)
        assert "-7" not in izin and "-7.00" not in izin
        assert "-24" not in izin and "-24.00" not in izin

    def test_tarih_maskesi_iki_yonlu_simetrik(self, real_cfg):
        """Toplama ve okuma AYNI maskeyi kullanmalı.

        Biri maskelerken diğeri maskelemezse denetim ya yanlış alarm verir ya
        sessizce delinir.
                """
        b = {"not": "2026-07-24 tarihli kayıt"}
        izin = llm_io.allowed_numeric_tokens(b, real_cfg)
        assert llm_io.numeric_tokens("2026-07-24 tarihli kayıt") <= izin


class TestIzinliTokenlar:
    def test_paketteki_her_sayi_izinli(self, real_cfg):
        b = {"evren": [{"fiyat": {"kapanis": 312.75}, "atr": 4.5}]}
        izin = llm_io.allowed_numeric_tokens(b, real_cfg)
        assert "312.75" in izin and "4.5" in izin and "4.50" in izin

    def test_yil_araligi_izinli(self, real_cfg):
        alt, ust = real_cfg["denetim"]["sayisal_beyaz_liste_yil"]
        izin = llm_io.allowed_numeric_tokens({}, real_cfg)
        assert str(alt) in izin and str(ust) in izin
        assert str(int(ust) + 1) not in izin

    def test_kucuk_tamsayilar_izinli(self, real_cfg):
        """"3 gün", "2 hedef" sayı uydurma değildir; yasaklamak modeli anlamsız
        dolambaçlara iterdi. Sınır ölçüldü ve README'de yazılı."""
        maks = int(real_cfg["denetim"]["sayisal_beyaz_liste_tamsayi_maks"])
        izin = llm_io.allowed_numeric_tokens({}, real_cfg)
        assert str(maks) in izin
        assert str(maks + 1) not in izin

    def test_boolean_sayi_SAYILMAZ(self, real_cfg):
        """`True` Python'da 1'dir; sayı olarak toplamak izinli listeyi kirletir."""
        izin_bos = llm_io.allowed_numeric_tokens({}, real_cfg)
        izin_bool = llm_io.allowed_numeric_tokens({"ok": True, "x": False}, real_cfg)
        assert izin_bool == izin_bos


# ============================================================ paket yapısı
class TestPaketYapisi:
    def test_ust_seviye_alanlar_TAM(self, paket):
        zorunlu = {"bundle_version", "asof", "karar_gunu", "generated_utc", "uyari",
                   "takvim", "kesit", "haber_taramasi", "rejim", "evren", "portfoy",
                   "izin_verilen_degerler", "kurallar_ozeti", "bundle_sha"}
        assert zorunlu <= set(paket), f"eksik: {zorunlu - set(paket)}"
        assert paket["bundle_version"] == schema.BUNDLE_VERSION

    def test_KESIT_PAYDASI_pakette(self, paket):
        """Sıralamanın anlamı tamamen kaç isim üzerinde yapıldığına bağlı.

        `pct=100` "67'de birinci" ile "10'da birinci"yi ayırt edemiyorsa
        sıralama bir bilgi değil, bir izlenimdir (L-007).
        """
        k = paket["kesit"]
        assert {"istenen", "skorlanan", "uygun", "not"} <= set(k)
        assert k["istenen"] >= k["skorlanan"] >= k["uygun"] >= 0
        assert "yuzdelik" in k["not"]

    def test_REJIM_PAYDASI_pakette(self, paket):
        r = paket["rejim"]
        assert "genislik_n" in r and "genislik_istenen_n" in r
        assert r["genislik_n"] <= r["genislik_istenen_n"]
        assert r["etiket"] in ("risk-on", "neutral", "transition", "risk-off")
        pol = r["pozisyon_politikasi"]
        assert {"nakit_pct", "maks_pozisyon", "sektor_basi_maks"} == set(pol)

    def test_HABER_TARAMASI_SAGLIGI_pakette(self, paket):
        """Boş `haberler` listesi iki farklı olguyu temsil eder.

        "Bu hissede bildirim yok" ile "KAP taraması hiç çalışmadı". Analist
        ikisini ayırt edemezse ikincisini birincisi sanar — ve ADR #008 sonrası
        haber/veto sistemin kalan ANA ürünü.
        """
        h = paket["haber_taramasi"]
        assert "ok" in h
        assert h["ok"] is False, "kurulumda hiç KAP kaydı yok → ok=False olmalı"
        assert h["not"], "neden güvenilmez olduğu yazılmalı"

    def test_her_hissede_FAKTOR_OZETI_var(self, paket):
        """Skor pakete girmezse HF-22 ateşlenemez ve journal `score` yazamaz."""
        for e in paket["evren"]:
            f = e["faktorler"]
            assert {"skor", "sira", "yuzdelik", "weights_hash", "kapilar"} <= set(f)
            assert isinstance(f["kapilar"]["uygun"], bool)
            assert f["weights_hash"], "hangi ağırlık setiyle üretildiği yazılmalı"

    def test_skorlanmayan_isimde_alanlar_None_ve_UYGUN_DEGIL(self):
        """Skor yoksa UYDURULMAZ: None kalır ve kapı kapanır."""
        ozet = llm_io._faktor_ozeti(None, "abc123")
        assert ozet["skor"] is None and ozet["yuzdelik"] is None
        assert ozet["kapilar"]["uygun"] is False
        assert ozet["kapilar"]["nedenler"] == ["skorlanmadı"]

    def test_her_hissede_VERI_KALITESI_var(self, paket):
        for e in paket["evren"]:
            vk = e["veri_kalitesi"]
            assert {"ok", "uyarilar", "degerlendirildi"} <= set(vk)
            assert isinstance(vk["ok"], bool)

    def test_plan_yoksa_SEBEBI_yazili(self, paket):
        """"Plan yok" tek bir olgu değildir; sebebi yazılmadan raporlamak
        okuyanı yanıltır (L-003)."""
        for e in paket["evren"]:
            varsa = bool(e["plan_menusu"])
            neden = e["plan_yok_nedeni"]
            assert varsa != bool(neden), (
                f"{e['ticker']}: plan {len(e['plan_menusu'])}, neden {neden!r} — "
                "ikisi birlikte ya da ikisi birden yok olamaz")

    def test_plan_ids_evrenle_TUTARLI(self, paket):
        """HF-12 bu listeye dayanır: liste ile menü ayrışırsa ya meşru plan
        reddedilir ya uydurma plan kabul edilir."""
        pid = paket["izin_verilen_degerler"]["plan_ids"]
        assert set(pid) == {e["ticker"] for e in paket["evren"]}
        for e in paket["evren"]:
            assert pid[e["ticker"]] == [p["plan_id"] for p in e["plan_menusu"]]

    def test_enumlar_configten_gelir(self, paket, real_cfg):
        izin = paket["izin_verilen_degerler"]
        for ad, degerler in real_cfg["llm"]["enums"].items():
            assert izin[ad] == degerler

    def test_planlarda_UYARI_ibaresi(self, paket):
        """ADR #008: her plan "ölçülen kenar yok" ibaresini TAŞIR."""
        assert "kenar yok" in paket["uyari"].lower()
        for e in paket["evren"]:
            for p in e["plan_menusu"]:
                assert "kenar yok" in p["uyari"].lower()

    def test_kurallar_ozeti_SERT_KURALLARI_tasir(self, paket):
        metin = " ".join(paket["kurallar_ozeti"]).lower()
        assert "hiçbir sayı üretme" in metin
        assert "hf-17" in metin
        assert "not_covered" in metin
        assert "veto" in metin

    def test_takvim_bloguzaman_bariyerini_tasir(self, paket, real_cfg):
        t = paket["takvim"]
        assert t["son_kapali_seans"] == paket["asof"]
        assert t["zaman_bariyeri_tarihi"] == paket["karar_gunu"]
        assert t["islem_gunu_sayisi"] == real_cfg["planlayici"]["zaman_bariyeri_gun"]
        assert paket["karar_gunu"] > paket["asof"]

    def test_paket_JSON_SERILESTIRILEBILIR(self, paket):
        """Paket diske yazılıp makineyle okunur; NaN geçersiz JSON üretir."""
        metin = util.json_dump(paket)
        assert "NaN" not in metin and "Infinity" not in metin
        json.loads(metin)

    def test_ayni_gun_ayni_paket_ayni_sha(self, cfg, con):
        """`generated_utc` dışında paket deterministik olmalı.

        (Damga saniye çözünürlüklü olduğu için sha karşılaştırması `generated_utc`
        çıkarılarak yapılır — asıl iddia: VERİ aynıysa içerik aynıdır.)
        """
        asof = kur_sentetik_evren(cfg, con)
        a = llm_io.build_bundle(cfg, con, asof)
        b = llm_io.build_bundle(cfg, con, asof)
        for x in (a, b):
            x.pop("generated_utc")
            x.pop("bundle_sha")
        assert util.sha256_canonical(a) == util.sha256_canonical(b)


# ============================================================ sunum
class TestSunum:
    def test_write_bundle_UC_dosya_yazar(self, cfg, con):
        asof = kur_sentetik_evren(cfg, con)
        b = llm_io.build_bundle(cfg, con, asof)
        yollar = llm_io.write_bundle(cfg, b)
        assert set(yollar) == {"bundle", "context", "prompt"}
        for p in yollar.values():
            assert p.exists() and p.stat().st_size > 0
        geri = util.read_json(yollar["bundle"])
        assert geri["bundle_sha"] == b["bundle_sha"]

    def test_context_SHA_yi_gorunur_yazar(self, paket):
        """Analist sha'yı çıktısına birebir kopyalamak ZORUNDA (HF-02)."""
        metin = llm_io.render_context(paket)
        assert paket["bundle_sha"] in metin
        assert "BİREBİR" in metin

    def test_context_makro_YOKSA_UYDURMAZ(self, paket):
        metin = llm_io.render_context(paket)
        assert "veri yok" in metin and "uydurulmaz" in metin

    def test_context_kalite_uyarisini_GORUNUR_yapar(self, paket):
        """Kalite bozuksa analist görmeli — HF-16 zaten plan seçimini engelliyor,
        ama sebebini okumak analistin işi."""
        bozuk = json.loads(json.dumps(paket))
        bozuk["evren"][0]["veri_kalitesi"] = {"ok": False, "uyarilar": ["sıfır hacim %23"]}
        metin = llm_io.render_context(bozuk)
        assert "Veri kalitesi" in metin and "sıfır hacim %23" in metin

    def test_context_haber_onem_etiketini_HEURISTIK_ilan_eder(self, paket):
        bozuk = json.loads(json.dumps(paket))
        bozuk["evren"][0]["haberler"] = [
            {"id": "kap-1", "tarih": "2026-07-20 10:00", "onem": "yuksek",
             "baslik": "Test bildirimi", "ozet": None, "kaynak": "KAP", "url": "u"}]
        metin = llm_io.render_context(bozuk)
        assert "HEURİSTİK" in metin and "hiçbir hesaba girmez" in metin

    def test_prompt_iskeleti_ve_kurallari_tasir(self, paket, real_cfg):
        metin = llm_io.render_prompt(real_cfg, paket)
        assert paket["bundle_sha"] in metin
        assert schema.OUTPUT_SCHEMA_VERSION in metin
        assert "VETO" in metin
        assert "ölçülen kenar YOKTUR" in metin
        assert f"llm/out/{paket['asof']}/analysis.json" in metin
        for k in paket["kurallar_ozeti"]:
            assert k in metin

    def test_prompt_TEK_JSON_ister(self, paket, real_cfg):
        metin = llm_io.render_prompt(real_cfg, paket)
        assert "TEK JSON" in metin
        assert "Markdown yok" in metin

    def test_render_bos_evrende_patlamaz(self, real_cfg):
        b = {"asof": "2026-07-27", "bundle_sha": "x", "uyari": "u",
             "rejim": {"etiket": "neutral", "xu100_sma200_farki_pct": None,
                       "genislik_sma50_ustu_pct": None, "makro": {},
                       "pozisyon_politikasi": {"nakit_pct": 40.0, "maks_pozisyon": 5,
                                               "sektor_basi_maks": 2}},
             "evren": [], "kurallar_ozeti": ["kural"]}
        assert "Analiz Paketi" in llm_io.render_context(b)
        assert "Görev" in llm_io.render_prompt(real_cfg, b)


# ============================================================ çıktı okuma
class TestCiktiOkuma:
    def test_cikti_yoksa_YOL_GOSTEREN_hata(self, cfg):
        """Hata mesajı ne yapılacağını söylemeli; çıplak bir istisna kullanıcıyı
        dosya aramaya iter."""
        with pytest.raises(FileNotFoundError) as e:
            llm_io.read_output(cfg, "2026-07-27")
        assert "prompt.md" in str(e.value)

    def test_cikti_okunur(self, cfg):
        yol = util.resolve(f"{cfg['paths']['llm_out_dir']}/2026-07-27/analysis.json")
        util.write_json(yol, {"schema_version": schema.OUTPUT_SCHEMA_VERSION})
        assert llm_io.read_output(cfg, "2026-07-27")["schema_version"] == \
            schema.OUTPUT_SCHEMA_VERSION


class TestFaktorEslemesi:
    def test_turkce_anahtar_ingilizce_kolona_TEK_YERDE_eslenir(self):
        """Dağıtık eşleme sessizce None yazan bir hataya dönüşür.

        Nitekim ilk sürümde `skor` ile `score` ayrışıp `predictions` üzerinde
        NOT NULL hatası patlattı.
        """
        ozet = {"skor": 1.5, "sira": 2, "yuzdelik": 80.0, "weights_hash": "abc"}
        assert llm_io.faktor_to_journal(ozet) == {
            "score": 1.5, "rank": 2, "pct": 80.0, "weights_hash": "abc"}

    def test_bos_faktor_None_doner(self):
        m = llm_io.faktor_to_journal(None)
        assert m["score"] is None and m["weights_hash"] == ""
