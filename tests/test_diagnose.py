"""Teşhis testleri — İŞARET KÖRLÜĞÜNE KARŞI KİLİT.

`diagnose.verdict` bu projenin en tehlikeli hata sınıfının tam merkezinde:
**büyüklüğe bakıp anlamlılığa bakmamak, ya da anlamlılığa bakıp işareti yok
saymak** (LESSONS L-006). İki ayrı sürümde iki ayrı yönde yanlış yapıldı:

1. İlk sürüm `ic_uygun > 0` diye kontrol ediyordu → IC=0.009 (t=0.20), yani
   düpedüz sıfır, "pozitif" sayılıp yanlış tanı üretiyordu.
2. Sonra `t_t < T_ANLAMLI` yazıldı ve güçlü NEGATİF bir IC'yi (t=−3, yani skor
   kesiti güvenilir biçimde TERS sıralıyor) "sıralama bilgisi yok" diye
   etiketliyordu. Bu, aynı körlüğün ayna görüntüsü: büyüklük anlamlı, yön yok
   sayılıyor.

Ters sinyal **bilgisizlik değildir, ters işaretli bilgidir** — ve değerli bir
bulgudur. Aşağıdaki testler altı tanı dalının hepsini ayrı ayrı sabitler;
sınırlar (t = ±2.0) tek tek yoklanır çünkü bu eşiklerde bir `<` ile `<=` farkı
tanıyı sessizce değiştirir.
"""

from __future__ import annotations

import pytest

from src import diagnose


def _t(*, ic_tum, t_tum, ic_uygun=0.03, t_uygun=1.0, yon=1.0, n_yon=20,
       atif=None) -> dict:
    return {
        "enstruman": {
            "ic_tum": {"ic_ort": ic_tum, "t": t_tum},
            "ic_uygun": {"ic_ort": ic_uygun, "t": t_uygun},
            "secim_yonu_dogru_oran": yon,
            "secim_yonu_n": n_yon,
            "ort_havuz": 20.0, "ort_secilen": 7.0,
        },
        "atif": atif if atif is not None else [
            {"kol": "maliyet: %0.00", "delta": 0.30, "n": 16, "alfa": -0.5,
             "t": -1.0, "ic_tum": 0.04, "ic_uygun": 0.01, "hukum": "kenar yok"}],
    }


class TestTaniDallari:
    def test_IC_hic_hesaplanamadiysa_OLCULEMEDI(self):
        """Bu bir teşhis değil, ölçüm eksikliğidir — ikisini karıştırmak
        "sistem bozuk" sanısına yol açar (L-003)."""
        h = diagnose.verdict(_t(ic_tum=None, t_tum=None))
        assert h["tani"] == "olculemedi"
        assert "ölçüm eksikliği" in h["aciklama"]

    def test_secim_yonu_bozuksa_KURGU_HATASI(self):
        """Seçilenlerin ortalama skoru havuzun altındaysa sıralama TERS uygulanıyor.

        Bu, faktör tartışmasından ÖNCE düzeltilmesi gereken bir yazılım hatası;
        onu "faktör çalışmıyor" diye okumak aylar kaybettirir.
        """
        h = diagnose.verdict(_t(ic_tum=0.05, t_tum=3.0, yon=0.5))
        assert h["tani"] == "kurgu_hatasi"
        assert "ters uygulanıyor" in h["aciklama"]

    def test_GUCLU_NEGATIF_IC_bilgisizlik_DEGIL_TERS_SIRALAMA(self):
        """⚠ L-006 KİLİDİ: t=−3 "bilgi yok" değildir.

        Güvenilir biçimde ters sıralayan bir skor DEĞERLİ bir bulgudur; onu
        "sıralama bilgisi yok" diye etiketlemek bulguyu çöpe atar.
        """
        h = diagnose.verdict(_t(ic_tum=-0.06, t_tum=-3.0))
        assert h["tani"] == "siralama_TERS"
        assert "TERS" in h["aciklama"]
        assert "ön kayıtsız yapılamaz" in h["aciklama"], (
            "işaret çevirmenin ön kayıt gerektirdiği söylenmeli — sonucu görüp "
            "işaret seçmek p-hacking'in ta kendisi")

    def test_sifira_yakin_IC_BILGI_YOK(self):
        """IC=0.05 kulağa büyük gelir ama t=0.3 ise gürültüdür."""
        h = diagnose.verdict(_t(ic_tum=0.05, t_tum=0.3))
        assert h["tani"] == "siralama_bilgisi_yok"
        assert "kurtarmaz" in h["aciklama"]

    def test_kapi_bilgiyi_yok_ediyorsa_ADLANDIRILIR(self):
        """Tüm kesitte anlamlı, kapılı havuzda kayıp → kapı tasarımı sorunu.

        Bu bir kurgu hatası DEĞİL: kapı, skorun ayırt edeceği aralığı zaten
        kesip atıyor. Ölçüldü: bilginin %79'u SMA200 kapısında kayboluyor.
        """
        h = diagnose.verdict(_t(ic_tum=0.042, t_tum=2.42, ic_uygun=0.009, t_uygun=0.2))
        assert h["tani"] == "kapi_bilgiyi_yok_ediyor"
        assert "%" in h["aciklama"] and "kapıda kayboluyor" in h["aciklama"]
        assert "kurgu hatası DEĞİL" in h["aciklama"]

    def test_her_iki_IC_anlamliysa_UYGULAMA_yiyor(self):
        h = diagnose.verdict(_t(ic_tum=0.06, t_tum=3.0, ic_uygun=0.05, t_uygun=2.5))
        assert h["tani"] == "sinyal_var_uygulama_yiyor"
        assert "uygulamada" in h["aciklama"]


class TestEsikSinirlari:
    """t = ±2.0 sınırında `<` ile `<=` farkı tanıyı sessizce değiştirir."""

    @pytest.mark.parametrize("t_tum,beklenen", [
        (-2.01, "siralama_TERS"),
        (-2.0, "siralama_TERS"),          # eşitlik TERS tarafına düşer
        (-1.99, "siralama_bilgisi_yok"),
        (1.99, "siralama_bilgisi_yok"),
        (2.0, "kapi_bilgiyi_yok_ediyor"), # anlamlı → sonraki dala geçer
    ])
    def test_ic_tum_esigi(self, t_tum, beklenen):
        h = diagnose.verdict(_t(ic_tum=0.05, t_tum=t_tum, ic_uygun=0.01, t_uygun=0.5))
        assert h["tani"] == beklenen

    @pytest.mark.parametrize("t_uygun,beklenen", [
        (1.99, "kapi_bilgiyi_yok_ediyor"),
        (2.0, "sinyal_var_uygulama_yiyor"),
    ])
    def test_ic_uygun_esigi(self, t_uygun, beklenen):
        h = diagnose.verdict(_t(ic_tum=0.06, t_tum=3.0, ic_uygun=0.05, t_uygun=t_uygun))
        assert h["tani"] == beklenen

    def test_t_esigi_2_0_de_KALIR(self):
        """Eşiği düşürmek her gürültüyü "sinyal" yapar."""
        assert diagnose.T_ANLAMLI == 2.0

    def test_secim_yonu_esigi(self):
        assert diagnose.verdict(_t(ic_tum=0.05, t_tum=3.0, yon=0.89))["tani"] \
            == "kurgu_hatasi"
        assert diagnose.verdict(_t(ic_tum=0.05, t_tum=3.0, yon=0.9,
                                   ic_uygun=0.05, t_uygun=3.0))["tani"] \
            == "sinyal_var_uygulama_yiyor"


class TestBaskinKol:
    def test_en_iyi_kol_tasinir(self):
        atif = [{"kol": "ufuk: H=42", "delta": 1.2},
                {"kol": "maliyet: %0.00", "delta": 0.3}]
        h = diagnose.verdict(_t(ic_tum=0.05, t_tum=0.3, atif=atif))
        assert h["baskin_kol"]["kol"] == "ufuk: H=42"

    def test_atif_bossa_None(self):
        h = diagnose.verdict(_t(ic_tum=0.05, t_tum=0.3, atif=[]))
        assert h["baskin_kol"] is None

    def test_tani_her_zaman_BILINEN_kumede(self):
        """Yeni bir dal eklenirse rapor onu tanımaz — burada anında görünür.

        Fuzz TUTARLI çiftler üzerinde koşar: `t = ort/(sd/√n)` olduğu için
        `ic_ort == 0` iken `t` de 0'dır. Tutarsız bir çift (ic=0, t=3) gerçek
        veride oluşamaz; oluşabildiği tek yer elle kurulmuş bir sözlüktür ve
        orada kod bölme hatası verir (bkz. `test_ic_sifir_ve_t_anlamli_...`).
        """
        bilinen = {"olculemedi", "kurgu_hatasi", "siralama_TERS",
                   "siralama_bilgisi_yok", "kapi_bilgiyi_yok_ediyor",
                   "sinyal_var_uygulama_yiyor"}
        ciftler = [(-0.5, -5.0), (-0.06, -3.0), (-0.02, -2.0), (-0.01, -1.0),
                   (0.0, 0.0), (0.01, 1.0), (0.04, 2.0), (0.5, 5.0)]
        for ic, t in ciftler:
            for t_u in (0.0, 1.99, 2.0, 3.0):
                for yon in (0.0, 0.95, 1.0):
                    h = diagnose.verdict(_t(ic_tum=ic, t_tum=t, ic_uygun=ic / 2,
                                            t_uygun=t_u, yon=yon))
                    assert h["tani"] in bilinen, (ic, t, t_u, yon, h["tani"])

    def test_ic_ort_SIFIRSA_t_de_sifirdir(self):
        """Kodun örtük varsayımı: `ic_ort == 0` ⟹ `t == 0`.

        `verdict`in `kapi_bilgiyi_yok_ediyor` dalı `ic_t`'ye BÖLER. O dala
        girmek için `t ≥ 2` gerekir; `t = ort/(sd/√n)` olduğundan `t ≥ 2`
        iken ortalama sıfır olamaz. Yani bölme gerçek veride güvenli — ama bu
        bir varsayımdır ve varsayımın yazılı olması gerekir.
        """
        from src import stats
        for ics in ([0.1, -0.1], [0.0, 0.0, 0.0], [0.5, -0.5, 0.2, -0.2]):
            s = stats.ic_summary(ics)
            if s["ic_ort"] == 0.0:
                assert s["t"] in (None, 0.0) or abs(s["t"]) < 1e-9, s

    def test_ic_SIFIRKEN_bolme_hatasi_vermez(self):
        """⚠ REGRESYON KİLİDİ: `1 - ic_u/ic_t` sıfıra bölerdi.

        NE OLMUŞTU: `kapi_bilgiyi_yok_ediyor` dalı kaybolan bilgi oranını
        `ic_t`'ye bölerek hesaplıyordu ve `ic_t = 0` olasılığını korumuyordu.
        Gerçek veride bu dala girmek `t ≥ 2` gerektirdiği için ortalama sıfır
        olamaz — yani canlı risk yoktu. Ama "buraya gelinemez" bir savunma
        değildir: varsayım bozulduğu gün `bist teshis` ortasında çökerdi.

        Artık oran hesaplanamıyorsa UYDURULMAZ, cümleden düşer.
        """
        h = diagnose.verdict(_t(ic_tum=0.0, t_tum=3.0, ic_uygun=0.0, t_uygun=0.5))
        assert h["tani"] == "kapi_bilgiyi_yok_ediyor"
        assert "ölçülebilir bilgi kalmıyor" in h["aciklama"]
        assert "kapıda kayboluyor" not in h["aciklama"], (
            "hesaplanamayan oran yine de basılmış — uydurma")

    def test_KAPILI_havuzun_IC_si_HIC_olculemediyse_patlamaz(self):
        """⚠ REGRESYON KİLİDİ: `ic_uygun` None iken `f"{None:.3f}"` patlıyordu.

        NE OLMUŞTU: `ic_t` için None koruması yazılmış, simetriği olan `ic_u`
        için yazılmamıştı. Ve bu ERİŞİLEBİLİR bir durum: kapılı havuz her dönem
        3 isimden aza düşerse `ic_summary` boş liste alır → `ic_ort` None,
        `t` None. Yani tam da "kapı bilgiyi yok ediyor" tanısının UÇ HÂLİ, o
        tanının metnini üretirken TypeError veriyordu.

        Savunmayı bir yerde uygulayıp simetriğinde atlamak bu projede
        tekrarlayan bir kalıp (LESSONS L-007).
        """
        h = diagnose.verdict(_t(ic_tum=0.05, t_tum=3.0, ic_uygun=None, t_uygun=None))
        assert h["tani"] == "kapi_bilgiyi_yok_ediyor"
        assert "—" in h["aciklama"], "ölçülemeyen IC sayı gibi basılmamalı"

    @pytest.mark.parametrize("ic_u,t_u", [(None, None), (None, 0.0), (0.0, 0.0)])
    def test_olculemeyen_ic_uygun_TUM_dallarda_guvenli(self, ic_u, t_u):
        for ic_t, t_t in ((None, None), (-0.06, -3.0), (0.01, 0.5), (0.05, 3.0)):
            h = diagnose.verdict(_t(ic_tum=ic_t, t_tum=t_t,
                                    ic_uygun=ic_u, t_uygun=t_u))
            assert h["tani"] and h["aciklama"]


class TestTeshisKosusu:
    """`diagnose.run` gerçekten koşuyor mu ve kurgu hatası ÜRETMİYOR mu?"""

    @pytest.fixture(scope="class")
    def kosu(self, tmp_path_factory):
        from src import db
        from src import util as u
        from tests.conftest import kur_sentetik_evren
        tmp = tmp_path_factory.mktemp("teshis")
        c = u.load_config(fresh=True)
        c = {**c, "paths": {**c["paths"], "db": str(tmp / "t.db"),
                            "db_dump": str(tmp / "t.sql"),
                            "log_dir": str(tmp / "logs")}}
        con = db.connect(c)
        kur_sentetik_evren(c, con, n_bar=600)
        t = diagnose.run(c, con)
        yield t
        con.close()

    def test_secim_yonu_TAM_dogru(self, kosu):
        """Sıralama doğru uygulanıyorsa oran 1.0 olmalı.

        1.0'ın altına düşmesi `score_at` ile `walk_forward`'ın seçim yönünün
        ayrıştığını gösterir — yani ölçümün tamamı geçersizdir.
        """
        e = kosu["enstruman"]
        assert e["secim_yonu_n"] > 0, "yön kontrolü hiç koşmadı"
        assert e["secim_yonu_dogru_oran"] == pytest.approx(1.0)
        assert diagnose.verdict(kosu)["tani"] != "kurgu_hatasi"

    def test_her_kol_TEK_sapma(self, kosu):
        """Kombinasyon aranmaz: kol adları tek bir boyutu adlandırır."""
        boyutlar = ("kapı", "maliyet", "genişlik", "evren", "ufuk")
        for a in kosu["atif"]:
            assert sum(1 for b in boyutlar if a["kol"].startswith(b)) == 1, a["kol"]

    def test_atif_deltaya_gore_sirali(self, kosu):
        """⚠ REGRESYON KİLİDİ: en çok iyileştiren kol üstte — rapor böyle okunuyor.

        NE OLMUŞTU: sıralama `-(x["delta"] or -1e9)` ile yapılıyordu ve Python'da
        `0.0 or -1e9` → `-1e9` olduğu için ETKİSİ TAM SIFIR olan bir kol, en
        kötü kol gibi listenin dibine düşüyordu. "Fark yok" ile "en çok zarar
        veren" iki farklı bulgudur; aynı yerde göstermek okuyanı yanıltır
        (LESSONS L-003).

        Sıfır delta gerçek bir olgudur ve bu testte artık HARİÇ TUTULMUYOR.
        """
        sirali = [a["delta"] for a in kosu["atif"] if a["delta"] is not None]
        assert sirali == sorted(sirali, reverse=True)

    def test_SIFIR_delta_en_alta_DUSMEZ(self, kosu):
        """Etkisi TAM SIFIR olan kol, en kötü kol gibi gösterilemez.

        `0.0 or -1e9` tuzağının doğrudan kilidi: sıfır delta varsa, ondan DAHA
        KÖTÜ (negatif) bir kol onun ALTINDA olmalı.
        """
        deltalar = [a["delta"] for a in kosu["atif"] if a["delta"] is not None]
        if 0.0 in deltalar and any(d < 0 for d in deltalar):
            assert deltalar.index(0.0) < max(
                i for i, d in enumerate(deltalar) if d < 0)

    def test_referans_ayari_yazili(self, kosu):
        """"Hangi kurulumdan saptık?" sorusu raporda cevaplanabilir olmalı."""
        ayar = kosu["referans"]["ayar"]
        for parca in ("kapılı", "maliyet", "üst %", "H="):
            assert parca in ayar


class TestOlculemeyenKol:
    """Ölçülemeyen kol (`delta is None`) sıralamanın SONUNDA durur.

    Sıralamaya sokmak onu bir sayıya çevirmek olurdu; "ölçülemedi" ile "en kötü"
    aynı yere düşerse rapor bir bilinmeyeni bir bulgu gibi gösterir.
    """

    @pytest.fixture(scope="class")
    def kisa_kosu(self, tmp_path_factory):
        """320 bar: `ufuk: H=63` kolu için hiç dönem kalmaz → `delta` None."""
        from src import db
        from src import util as u
        from tests.conftest import kur_sentetik_evren
        tmp = tmp_path_factory.mktemp("teshis_kisa")
        c = u.load_config(fresh=True)
        c = {**c, "paths": {**c["paths"], "db": str(tmp / "t.db"),
                            "db_dump": str(tmp / "t.sql"),
                            "log_dir": str(tmp / "logs")}}
        con = db.connect(c)
        kur_sentetik_evren(c, con, n_bar=320)
        t = diagnose.run(c, con)
        yield t
        con.close()

    def test_kurulum_gercekten_olculemeyen_kol_uretiyor(self, kisa_kosu):
        assert any(a["delta"] is None for a in kisa_kosu["atif"]), (
            "fixture anlamsızlaştı: hiçbir kol ölçülemez hâle gelmedi")

    def test_olculemeyen_kollar_EN_SONDA(self, kisa_kosu):
        deltalar = [a["delta"] for a in kisa_kosu["atif"]]
        ilk_none = deltalar.index(None)
        assert all(d is None for d in deltalar[ilk_none:]), (
            f"ölçülemeyen kol sıralamanın ortasında: {deltalar}")

    def test_olculen_kollar_kendi_arasinda_sirali(self, kisa_kosu):
        olculen = [a["delta"] for a in kisa_kosu["atif"] if a["delta"] is not None]
        assert olculen == sorted(olculen, reverse=True)

    def test_baskin_kol_OLCULEBILEN_bir_kol(self, kisa_kosu):
        """"Baskın kol" ölçülememiş bir kol olamaz — rapor onu öneri gibi basar."""
        h = diagnose.verdict(kisa_kosu)
        assert h["baskin_kol"]["delta"] is not None

    def test_rapor_OLCULEMEYEN_kolu_TIRE_ile_basar(self, kisa_kosu, real_cfg):
        """Ölçülemeyen delta raporda sayı gibi görünmemeli."""
        from src import report
        metin = report.diagnose_report(real_cfg, kisa_kosu,
                                       diagnose.verdict(kisa_kosu))
        assert "**—**" in metin, "ölçülemeyen kol bir sayı gibi basılmış olabilir"
