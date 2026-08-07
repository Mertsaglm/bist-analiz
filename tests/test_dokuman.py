"""Doküman ↔ kod tutarlılığı — DOKÜMAN ÇÜRÜMESİNE KARŞI.

AGENTS.md §8'de üç kural yazılı ve üçü de 2026-07-27 denetiminden doğdu:

1. **Sayı gömme.** README'ye "302 test" gibi bir sayı yazma; ilk değişiklikte
   sessizce yalan olur. Sayıyı üreten KOMUTU yaz.
2. **Ölü referans bırakma.** Bir dosyaya atıf verirken o dosyanın gerçekten
   repoda olduğunu doğrula — gitignore'daki bir dosyaya atıf, taze klonda kırık
   bir bağlantıdır.
3. **Yorum bir iddiadır.** "Şu komut şunu yapar" cümlesinin KODDA karşılığı
   olmalı. Denetimde bulunan en pahalı yanılgılar kod hatası değil, **doğru
   görünen ama karşılığı olmayan cümlelerdi.**

Bu dosya o üç kuralı MAKİNEYE devrediyor. Bir kuralı insanın hatırlamasına
bırakmak, onu bir kere uygulayıp bırakmakla aynı şeydir.

⚠ Bu testler dokümanı kodun ARDINDAN sürüklemez; sadece **var olmayan bir şeye
atıf verilmesini** engeller. Yani komut adını değiştiren kişi dokümanı da
güncellemek zorunda kalır — ama dokümanın üslubuna karışılmaz.
"""

from __future__ import annotations

import hashlib
import re
import subprocess

import pytest

from src import audit, cli, revizyon, util

KOK = util.ROOT

KURAL_DOSYALARI = ["README.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md"]
HAFIZA_DOSYALARI = ["ai/PROJECT.md", "ai/STATE.md", "ai/DECISIONS.md",
                    "ai/LESSONS.md"]
KAYNAK_DOSYALARI = [str(p.relative_to(KOK)) for p in (KOK / "src").rglob("*.py")]
# Mühürlü ön kayıtlar KAPSAM DIŞI: koşudan önce sha256'ları alındı ve
# DEĞİŞTİRİLEMEZLER. İçlerindeki atıflar (ör. `reports/teshis_2026-07-26.md`,
# gitignore'da) tarihsel kayıttır; düzeltmek mührü kırar.
MUHURLU = [str(p.relative_to(KOK)) for p in (KOK / "docs").glob("on-kayit-*.md")]

TARANAN = KURAL_DOSYALARI + HAFIZA_DOSYALARI + KAYNAK_DOSYALARI


def _oku(rel: str) -> str:
    return (KOK / rel).read_text(encoding="utf-8")


def _komut_haritasi() -> dict[str, list[str]]:
    p = cli.build_parser()
    out: dict[str, list[str]] = {}
    for aksiyon in p._subparsers._group_actions:
        for ad, alt in aksiyon.choices.items():
            alt_aksiyon = next((x for x in alt._actions if x.dest == "alt"), None)
            out[ad] = list(alt_aksiyon.choices) if alt_aksiyon else []
    return out


# ============================================================ komut atıfları
_KOMUT = re.compile(r"`bist ([a-z]+)(?:\s+([a-z]+))?[^`]*`"
                    r"|poetry run bist ([a-z]+)(?:\s+([a-z]+))?")


def _komut_atiflari() -> list[tuple[str, str, str | None]]:
    out = []
    for f in TARANAN + MUHURLU:
        for m in _KOMUT.finditer(_oku(f)):
            out.append((f, m.group(1) or m.group(3), m.group(2) or m.group(4)))
    return out


class TestKomutAtiflari:
    def test_atif_bulundu(self):
        """Tarama gerçekten bir şey buluyor mu? (Regex bozulursa test susardı.)"""
        assert len(_komut_atiflari()) > 30

    def test_atif_verilen_her_komut_GERCEKTEN_VAR(self):
        """`bist xyz` diye yazılan her komut CLI'da olmalı.

        Bir komutu yeniden adlandırmak dokümandaki her satırı sessizce yalanlar
        ve kullanıcı bunu ancak komutu yazdığında öğrenir.
        """
        komutlar = _komut_haritasi()
        hatali = [(f, k, a) for f, k, a in _komut_atiflari() if k not in komutlar]
        assert not hatali, f"var olmayan komuta atıf: {hatali}"

    def test_atif_verilen_her_ALT_KOMUT_gercekten_var(self):
        komutlar = _komut_haritasi()
        hatali = [(f, k, a) for f, k, a in _komut_atiflari()
                  if k in komutlar and a and komutlar[k] and a not in komutlar[k]]
        assert not hatali, f"var olmayan alt komuta atıf: {hatali}"

    def test_README_gunluk_akisin_TAMAMINI_listeler(self):
        """Günlük akışın hiçbir adımı dokümandan düşmemeli.

        Bir adım README'den düşerse kullanıcı onu koşmaz ve o adımın beslediği
        tablo DONAR — LESSONS L-002'nin tam olarak uyardığı durum.
        """
        metin = _oku("README.md")
        for komut in ("bist veri gunluk", "bist haber cek", "bist gunluk",
                      "bist denetle", "bist kaydet", "bist rapor",
                      "bist coz", "bist degerlendir", "bist saglik"):
            assert komut in metin, f"README'de eksik: {komut}"

    def test_README_CIKIS_KODLARINI_yazar(self):
        """Çıkış kodu bir sözleşmedir; yazılı olmayan sözleşme yoktur."""
        metin = _oku("README.md")
        assert "0 temiz · 1 uyarı · 2 KRİTİK" in metin
        assert "0 temiz · 1 aralık atlandı · 2 hata" in metin
        # 2026-08-07: `haber cek` artık beklenen-bildirim takvimini de çekiyor
        # ve o düşerse de 1 döndürüyor. Çıkış kodunun ANLAMI genişledi; yazılı
        # sözleşme de genişlemeli, yoksa 1 gören kişi yanlış yere bakar.
        assert "takvim kırpık/çekilemedi de 1 döndürür" in metin


# ============================================================ config atıfları
_CFG_ATIF = re.compile(r"config\.([a-z_]+)\.([a-z_0-9]+)")


class TestConfigAtiflari:
    def test_atif_verilen_her_config_anahtari_VAR(self, real_cfg):
        """`config.risk.fiyat_adimlari` gibi her atıf gerçek bir anahtar olmalı.

        Anahtar adı değişince dokümandaki atıf sessizce ölü kalır ve okuyan
        kişiyi olmayan bir ayarı aramaya iter.
        """
        hatali = []
        for f in TARANAN + MUHURLU:
            for m in _CFG_ATIF.finditer(_oku(f)):
                ust, alt = m.group(1), m.group(2)
                if ust not in real_cfg:
                    hatali.append((f, f"{ust}.{alt}", "üst blok yok"))
                elif isinstance(real_cfg[ust], dict) and alt not in real_cfg[ust]:
                    hatali.append((f, f"{ust}.{alt}", "anahtar yok"))
        assert not hatali, f"ölü config atfı: {hatali}"

    def test_atif_bulundu(self, real_cfg):
        """Tarama gerçekten bir şey buluyor mu? (Regex bozulursa test susardı.)"""
        toplam = sum(len(_CFG_ATIF.findall(_oku(f))) for f in TARANAN + MUHURLU)
        assert toplam >= 5, "config atıf taraması hiçbir şey bulmuyor"


# ============================================================ dosya atıfları
# ⚠ `jsonl` `json`DAN ÖNCE gelmeli: alternasyon soldan eşleşir ve `json` önce
# yazılırsa `outbox.jsonl` atfı `outbox.json` diye KIRPILIR — sonra da var
# olmayan bir dosyaya atıf gibi raporlanır (2026-07-29'da yaşandı).
_YOL = re.compile(r"`((?:docs|ai|src|tests|reports|data|llm)/"
                  r"[A-Za-z0-9_./-]+\.(?:md|py|yaml|sql|jsonl|json))")

# Şablon/örnek/tarihsel atıflar — gerçek dosya olmaları BEKLENMEZ.
YER_TUTUCULAR = {
    "ai/archive/STATE-YYYY-MM.md",   # AGENTS.md'deki arşiv adlandırma şablonu
    "docs/y.md",                     # AGENTS.md kural metnindeki genel örnek
    "reports/x.md",                  # AGENTS.md kural metnindeki genel örnek
    "src/history.py",                # LESSONS L-002: BAŞKA bir projenin dosyası
}

# YEREL ÜRETİLEN dosyalar: gerçek dosyalardır ama repoya BİLEREK girmezler.
# Yer tutuculardan ayrı tutuluyorlar çünkü farklı bir olgu: `docs/y.md` hiç var
# olmayan bir örnek; `ai/PROFILE.md` var olan ama kişisel olduğu için
# izlenmeyen bir dosya (projeler arası ortak, gitignore'da).
#
# ⚠ Bu ayrım TAZE KLONDA yakalandı: çalışma kopyasında PROFILE.md durduğu için
# test yeşil geçiyordu, klonda ise yoktu. Aynı istisna testin gitignore dalında
# YAZILIYDI ama varlık dalında yazılmamıştı — LESSONS L-008'in ta kendisi:
# savunmayı bir yerde uygulayıp simetriğinde atlamak.
YEREL_URETILEN = {
    "ai/PROFILE.md",                 # kişisel profil; `yeni-proje.sh` taşır, repo tutmaz
}


def _dosya_atiflari() -> dict[str, set[str]]:
    ref: dict[str, set[str]] = {}
    for f in TARANAN:
        for m in _YOL.finditer(_oku(f)):
            ref.setdefault(m.group(1), set()).add(f)
    return ref


class TestDosyaAtiflari:
    def test_atif_verilen_her_dosya_VAR(self):
        """⚠ Bu test TAZE KLONDA da geçmeli — asıl kontrol edilen o.

        Çalışma kopyasında her şey durur; kırık bağlantı ancak repoyu ilk kez
        klonlayan kişide görünür. Bu yüzden istisnalar açıkça listelenir:
        yer tutucular (hiç var olmayan örnekler) ve yerel üretilenler (var olan
        ama bilerek izlenmeyen dosyalar).
        """
        ref = _dosya_atiflari()
        assert len(ref) > 10, "dosya atıf taraması çalışmıyor"
        muaf = YER_TUTUCULAR | YEREL_URETILEN
        eksik = {y: sorted(s) for y, s in ref.items()
                 if y not in muaf and not (KOK / y).exists()}
        assert not eksik, f"var olmayan dosyaya atıf: {eksik}"

    def test_YEREL_URETILEN_dosyalar_gercekten_izlenmiyor(self):
        """Muafiyet listesi kötüye kullanılamasın: muaf dosya GERÇEKTEN
        gitignore'da olmalı. Aksi halde bu liste, unutulmuş bir dosyayı
        gizlemenin kolay yoluna dönüşür."""
        for yol in sorted(YEREL_URETILEN):
            r = subprocess.run(["git", "check-ignore", yol],
                               cwd=KOK, capture_output=True, text=True)
            assert r.returncode == 0, (
                f"{yol} gitignore'da değil — muafiyet listesinde işi yok")

    def test_atif_verilen_dosya_GITIGNORE_da_DEGIL(self):
        """Gitignore'daki bir dosyaya atıf, TAZE KLONDA kırık bağlantıdır.

        README bunu kendi yazıyor: *"Bu README'de rapor dosyasına atıf verilmez
        — taze klonda bulunmaz."* İstisna `YEREL_URETILEN`: bilinçli olarak
        kişisel olan ve repoya girmeyen dosyalar; onlara atıf veren tek yer
        kural dosyasının "bu dosyayı doldur" talimatı.
        """
        var = [y for y in _dosya_atiflari()
               if (KOK / y).exists() and y not in YEREL_URETILEN]
        r = subprocess.run(["git", "check-ignore", *var],
                           cwd=KOK, capture_output=True, text=True)
        yoksayilan = [x for x in r.stdout.split() if x]
        assert not yoksayilan, (
            f"gitignore'daki dosyaya atıf: {yoksayilan} — taze klonda kırık")

    def test_KURAL_DOSYALARI_kokte(self):
        """L-004: yanlış yerdeki doğru dosya = yok hükmünde.

        Hiçbir IDE alt klasördeki AGENTS.md/CLAUDE.md'yi otomatik okumaz; sistem
        hata vermeden atıl kalır.
        """
        for f in KURAL_DOSYALARI:
            assert (KOK / f).exists(), f
        assert (KOK / ".github" / "copilot-instructions.md").exists()

    def test_KOPRU_dosyalari_AGENTS_e_isaret_eder(self):
        """Araç köprüleri kural KOPYALAMAZ, kanonik dosyaya YÖNLENDİRİR.

        Kuralı iki yere yazmak, iki farklı kural setine dönüşmesinin en kısa
        yoludur.
        """
        for f in ("CLAUDE.md", "GEMINI.md",
                  ".github/copilot-instructions.md"):
            metin = _oku(f)
            assert "AGENTS.md" in metin, f
            assert len(metin.splitlines()) < 40, (
                f"{f} kural kopyalıyor olabilir ({len(metin.splitlines())} satır)")


# ============================================================ ön kayıt mührü
class TestOnKayitMuhru:
    def test_revizyon_on_kaydi_MUHURLU_kalmis(self):
        """⚠ Ön kayıt bir MÜHÜRDÜR: koşudan önce sha256'sı koda yazıldı.

        Belgeyi sonradan düzenlemek, "sonucu görmeden yazıldı" iddiasını
        geçersiz kılar — ve p-hacking'i belgelenmiş bir yönteme çevirir. Bu
        test, mührün hâlâ tuttuğunu doğrular; kırılırsa ya belge değişmiştir ya
        sabit değişmiştir ve ikisi de ciddidir.
        """
        yol = KOK / "docs" / "on-kayit-revizyon-01.md"
        assert yol.exists(), "ön kayıt belgesi kayboldu"
        sha = hashlib.sha256(yol.read_bytes()).hexdigest()
        assert sha == revizyon.ON_KAYIT_SHA, (
            f"MÜHÜR KIRILDI — belge değişmiş.\n  beklenen: {revizyon.ON_KAYIT_SHA}"
            f"\n  bulunan : {sha}")

    def test_on_kayitta_KARAR_KURALI_sonucdan_once_yazili(self):
        metin = _oku("docs/on-kayit-revizyon-01.md")
        assert "N≥15" in metin or "N ≥ 15" in metin
        assert "1.0pp" in metin

    def test_bekleyen_on_kayit_belgesi_VAR_ve_atifli(self):
        """`docs/on-kayit-seviye-02.md` HAZIR ama KOŞULMADI (STATE.md backlog).

        Bekleyen bir ön kaydın dosyası kaybolursa, tetikleyici koşul oluştuğunda
        turu kimse koşamaz — ve "ön kayıt vardı" iddiası doğrulanamaz hale gelir.
        """
        assert (KOK / "docs" / "on-kayit-seviye-02.md").exists()
        assert "on-kayit-seviye-02.md" in _oku("ai/STATE.md")


# ============================================================ HF atıfları
class TestDenetimAtiflari:
    def test_atif_verilen_her_HF_kodu_GERCEKTEN_VAR(self):
        """Var olmayan bir kontrole atıf, olmayan bir garantiyi belgeler."""
        bilinen = set(audit.all_codes())
        hatali = []
        for f in TARANAN + MUHURLU:
            for kod in set(re.findall(r"\bHF-\d{2}\b", _oku(f))):
                if kod not in bilinen:
                    hatali.append((f, kod))
        assert not hatali, f"var olmayan HF koduna atıf: {hatali}"

    def test_yazili_HF_ARALIGI_gercek_kod_sayisiyla_ayni(self):
        """"HF-01..HF-NN" diye yazılan aralığın üst ucu GÜNCEL olmalı.

        ⚠ NE OLMUŞTU: HF-31 eklendikten sonra dört ayrı yer (`README.md`,
        `ai/PROJECT.md`, `src/audit.py`, `src/cli.py`) "HF-01..HF-30" demeye
        devam etti. Var olmayan koda atıf yoktu — o yüzden diğer test bunu
        yakalayamadı. Eksik olan TERS yöndü: belgelenen aralık, var olan
        kontrolleri EKSİK sayıyordu. Bu, "31 sert kontrol var" iddiasını
        kullanıcıya 30 diye satmak demek.
        """
        ust_kod = max(int(k.split("-")[1]) for k in audit.all_codes())
        hatali = []
        for f in TARANAN + MUHURLU:
            for yazili in re.findall(r"HF-01\.\.HF-(\d{2})", _oku(f)):
                if int(yazili) != ust_kod:
                    hatali.append((f, f"HF-01..HF-{yazili}", f"gerçek: HF-{ust_kod}"))
        assert not hatali, f"bayat HF aralığı: {hatali}"

    def test_HF17_SINIRI_README_de_ITIRAF_EDILIYOR(self):
        """Gizlenen bir sınır, olmayan bir garantiye dönüşür.

        HF-17 tasarlandığı hata modunda çalışıyor ama prose'un doğal kaydında
        geçirgen — ve bu ÖLÇÜLDÜ. README bunu yazıyor; silinmesi, kullanıcıya
        var olmayan bir koruma satmak olur.
        """
        metin = _oku("README.md")
        assert "Denetimin bilinen sınırları" in metin
        assert "geçirgen" in metin.lower()
        assert "%56" in metin, "ölçülen geçirgenlik oranı yazılı kalmalı"

    def test_R_R_KIYASLANAMAZ_uyarisi_README_de(self):
        """R:R bir SONUÇ değil, bir SEÇİM ürünü — ifşa edildi, düzeltilmedi."""
        metin = _oku("README.md")
        assert "kıyaslanabilir değildir" in metin
        assert "rr_secim" in metin


# ============================================================ hafıza disiplini
class TestHafizaDisiplini:
    def test_STATE_kisa_kalmis(self):
        """AGENTS.md eşiği: ~100 satır hedef, aşınca arşive taşı.

        Bu test bir nag değil, KAÇAK BÜYÜME kilidi: STATE.md kontrolsüz
        büyürse her oturumun başında okunan bağlam bir arşive dönüşür ve
        "nerede kaldık" sorusu cevaplanamaz hale gelir.
        """
        n = len(_oku("ai/STATE.md").splitlines())
        assert n <= 120, (
            f"ai/STATE.md {n} satır — hedef ~100. Eskiyeni "
            f"`ai/archive/STATE-YYYY-MM.md`'ye taşı.")

    def test_SIRADAKI_3_IS_numaralari_ATLANMAMIS(self):
        """AGENTS.md §8 zorunlu kontrolü: madde numaraları atlanmadan yazılır.

        Atlanan bir numara, tamamlanmış bir işin listede bırakıldığının en sık
        belirtisi — ve bir sonraki oturumu yanlış işe başlatır.
        """
        metin = _oku("ai/STATE.md")
        bolum = metin.split("Sıradaki 3 İş")[1].split("## ")[0]
        numaralar = [int(m) for m in re.findall(r"^(\d+)\.", bolum, re.MULTILINE)]
        assert numaralar, "Sıradaki 3 İş listesi BOŞ — oturum sonu ritüeli atlanmış"
        assert numaralar == list(range(1, len(numaralar) + 1)), numaralar

    def test_SIRADAKI_ISLERIN_DoD_u_var(self):
        """"Çalışıyor" bir DoD değil; doğrulanabilir bir cümle gerekir."""
        bolum = _oku("ai/STATE.md").split("Sıradaki 3 İş")[1].split("## ")[0]
        maddeler = re.split(r"^\d+\.", bolum, flags=re.MULTILINE)[1:]
        for m in maddeler:
            assert "DoD" in m, f"DoD'si olmayan madde: {m.strip()[:60]}"

    @pytest.mark.parametrize("dosya,kalip", [
        ("ai/DECISIONS.md", r"^## #(\d{3}) — "),
        ("ai/LESSONS.md", r"^## L-(\d{3}) — "),
    ])
    def test_kayit_numaralari_KESINTISIZ_ve_yeniden_eskiye(self, dosya, kalip):
        """Boşluk, silinmiş bir karar/ders demektir; ikisi de silinmez.

        Numaralar dosyada YENİDEN ESKİYE sıralı: en son karar en üstte, çünkü
        oturum başında okunacak olan o.
        """
        n = [int(m) for m in re.findall(kalip, _oku(dosya), re.MULTILINE)]
        assert n, f"{dosya}: kayıt bulunamadı"
        assert n == sorted(n, reverse=True), f"{dosya}: sıralama bozuk → {n}"
        assert n == list(range(max(n), max(n) - len(n), -1)), (
            f"{dosya}: numara boşluğu var → {n}")

    def test_kayitlarda_MUTLAK_TARIH(self):
        """"Geçen hafta" gibi göreli ifade kullanılmaz (AGENTS.md §8).

        Göreli tarih, dosya okunduğu ANDA anlamını değiştirir; bir hafıza
        dosyasında bu sessiz bir yanlış bilgilendirmedir.
        """
        for dosya, kalip in (("ai/DECISIONS.md", r"^## #\d{3} — (\S+) — "),
                             ("ai/LESSONS.md", r"^## L-\d{3} — (\S+) — ")):
            tarihler = re.findall(kalip, _oku(dosya), re.MULTILINE)
            assert tarihler, dosya
            for t in tarihler:
                assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", t), f"{dosya}: {t!r}"

    _GORELI = re.compile(r"\b(geçen hafta|geçen ay|bu hafta|bu ay|dün|yarın|"
                         r"birkaç gün önce|önümüzdeki hafta)\b", re.IGNORECASE)

    def test_hafiza_dosyalarinda_GORELI_TARIH_yok(self):
        hatali = []
        for f in HAFIZA_DOSYALARI:
            for m in self._GORELI.finditer(_oku(f)):
                hatali.append((f, m.group(0)))
        assert not hatali, f"göreli tarih ifadesi: {hatali}"


# ============================================================ sayı gömme
class TestSayiGomme:
    def test_README_TEST_SAYISI_gommez(self):
        """"302 test" yazmak, ilk değişiklikte sessizce yalan olur.

        Kural: sayıyı üreten KOMUTU yaz. README bunu kendi de söylüyor
        ("sayı basılır — README'ye gömülmez").
        """
        metin = _oku("README.md")
        gomulu = re.findall(r"(\d{2,4})\s*(?:adet\s*)?test\b", metin, re.IGNORECASE)
        assert not gomulu, f"README'ye gömülmüş test sayısı: {gomulu}"
        assert "pytest" in metin, "sayıyı üreten komut yazılmalı"

    def test_evren_sayilari_universe_yamldan_TURETILEBILIR(self, real_cfg):
        """README "18 hisse" diyor; bu sayı `universe.yaml`'dan doğrulanabilir.

        Gömülü bir sayı ancak ÜRETEN KAYNAKLA sınanabiliyorsa yalan söylemez.
        Bu test o bağı kurar: sayı değişirse ya README ya evren güncellenmeli.
        """
        from src import universe
        yaml_ev = universe.load_yaml_universe(real_cfg)
        canli = sum(1 for h in yaml_ev["hisseler"] if h.get("in_live", True))
        metin = _oku("README.md")
        assert f"{canli} hisse" in metin, (
            f"README'de canlı evren sayısı ({canli}) ile uyumsuz")

    def test_PROJECT_ve_README_ayni_UFKU_soyler(self, real_cfg):
        """Ana karar ufku üç yerde yazılı; ayrışırsa hangisi doğru bilinmez."""
        H = int(real_cfg["planlayici"]["zaman_bariyeri_gun"])
        assert f"H={H}" in _oku("README.md")
        assert f"{H} işlem günü" in _oku("ai/PROJECT.md")


# ============================================================ iddia ↔ kod
class TestIddiaKarsiligi:
    def test_README_deki_TABAN_CIZGISI_kararı_kodla_uyumlu(self, real_cfg):
        """"Birincil taban eşit-ağırlık evren" iddiasının kodda karşılığı var mı?

        `walk_forward`ın hükmü `alfa_ew` üzerinden verilir; XU100 yalnız
        raporlanır. İddia ile kod ayrışırsa rapor doğru görünen yanlış bir
        cümle basar.
        """
        assert real_cfg["olcum"]["birincil_taban"] == "esit_agirlik_evren"
        assert real_cfg["olcum"]["ikincil_taban"] == "XU100"
        kaynak = _oku("src/backtest.py")
        assert 'stats.edge_verdict(s_ew["ort"]' in kaynak, (
            "hüküm EW tabanından verilmiyor olabilir")

    def test_LLM_SAYI_URETMEZ_iddiasinin_kodda_karsiligi(self):
        """README'nin "tek sert kural"ı yapısal olarak zorlanıyor mu?

        Üç ayrı yerde: şema kümesi, HF-31 kontrolü ve journal'ın alan süzgeci.
        Biri kaybolursa iddia belgelenmiş ama var olmayan bir savunmaya döner —
        ki HF-31 yazılana kadar tam olarak öyleydi.
        """
        assert "hesaplanabilir hiçbir sayıyı üretmez" in _oku("README.md")
        assert "YASAK_SAYISAL_ALANLAR" in _oku("src/schema.py")
        assert "HF-31" in _oku("src/audit.py")
        assert "ANALIST_ALANLARI" in _oku("src/journal.py")

    def test_AZALT_ONCE_kararinin_kodda_karsiligi(self, real_cfg):
        assert real_cfg["rapor"]["once_azalt_bolumu"] is True
        assert "AZALT" in _oku("README.md")
        assert "## 1. Elindekiler — azaltma adayları" in _oku("src/report.py")

    def test_SEKTOR_NOTR_KAPALI_iddiasinin_kodda_karsiligi(self, real_cfg):
        assert real_cfg["faktorler"]["sektor_notr"] is False
        assert "kapalı" in _oku("README.md")

    def test_PROJECT_kapsam_disi_maddeleri_KODDA_YOK(self):
        """"Bilerek YOK" denen şeyler gerçekten yok mu?

        Otomatik emir gönderimi ve iki-AI konsensüs kapsam dışı ilan edildi.
        Sessizce eklenmeleri projenin kimliğini değiştirir.
        """
        kaynak = " ".join(_oku(f) for f in KAYNAK_DOSYALARI)
        for yasak in ("place_order", "submit_order", "send_order", "broker_api"):
            assert yasak not in kaynak, f"otomatik emir izi: {yasak}"

    def test_UYARI_metni_uc_yerde_TUTARLI(self, real_cfg):
        """Yatırım tavsiyesi uyarısı config'te tek kaynak; CLI ve rapor onu taşır."""
        assert "yatırım tavsiyesi değildir" in real_cfg["rapor"]["uyari"].lower()
        assert "YATIRIM TAVSİYESİ DEĞİLDİR" in cli.UYARI.upper()
        assert "yatırım tavsiyesi değildir" in _oku("README.md").lower()
