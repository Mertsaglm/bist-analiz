"""Sıralı eylem listesi — "bugün ne yapılabilir?"

ADR #015. Bu modül raporun EN ÜSTÜNE tek bir sıralı liste koyar. Sebebi
2026-08-07 repo incelemesinde ölçüldü: sistem dünyanın durumunu titizlikle
okuyor ama **"şu anda ne yapılabilir"i hiç sormuyordu**. 19 hisse için 19 ayrı
başlık üretiliyor, aralarında öncelik yok, sermayenin nereye gideceği yok.

⚠ EN ÖNEMLİ SINIR — bu dosyanın varlık şartı:

    SIRA BİR GETİRİ İDDİASI DEĞİLDİR.

Merdiven'in ΔEV mantığı bir **beklenen getiri** karşılaştırmasıdır. Bizim
beklenen getirimiz YOK ve olmadığı ÖLÇÜLDÜ (ADR #007; `required_n ≈ 11,5 yıl`).
Aynı formülü kurmak, ölçülmemiş bir kenar iddiasını arka kapıdan sokmak olurdu.
Buradaki sıra bir **uygulanabilirlik ve risk** sırasıdır: bugün işlem görebilir
mi, önünde bilanço var mı, veri sağlam mı, veto yürürlükte mi, plan
tetiklenebilir mi, kaç lira riske ediliyor.

⚠ SKOR YOK, TEK SAYI YOK. Sıralama sözlükbilimseldir (lexicographic): bileşenleri
tek bir sayıda toplamak, ağırlıklarını uydurmak olurdu. borsaci'nin Buffett
skorunda tam olarak bu yapılmış ve toplam skor modelin KENDİ uydurduğu alt
skorlardan besleniyor — kopyalanmayacak desen tam olarak budur.

⚠ SEÇİMİ DEĞİŞTİRMEZ. Liste hangi planların üretileceğini etkilemez; yalnız
üretilmiş olanları sıraya koyar. Sıralama seçime dokunduğu gün
`docs/on-kayit-seviye-02.md` disiplini devreye girer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Ölçüldü (2026-07-26): alt kuyruk (−1.03pp) üst kuyruğun ~1.8 katı ve retail
# olarak açığa satamazsın. Bu yüzden AZALT daima önce gelir — rapor sırası bir
# estetik tercih değil, ölçüm sonucu (bkz. config.rapor.once_azalt_bolumu).
AZALT_SINYALLERI = ("reduce", "sell", "avoid")
BOGA_SINYALLERI = ("strong_buy", "buy", "accumulate")


@dataclass(frozen=True, slots=True)
class Eylem:
    tur: str                       # azalt | gir | izle | engelli
    ticker: str
    baslik: str
    gerekce: list[str] = field(default_factory=list)
    engeller: list[str] = field(default_factory=list)
    plan_id: str | None = None
    riske_edilen_pct: float | None = None
    rr_net: float | None = None
    uygulanabilir: bool = True

    @property
    def hazir(self) -> bool:
        return self.uygulanabilir and not self.engeller


def _engeller(e: dict) -> list[str]:
    """Bu ismi BUGÜN uygulanamaz kılan olgular. Hepsi deterministik.

    Not: bunlar "kötü fikir" değil, **yapılamaz** sebepleridir. İkisini
    karıştırmak L-003'tür.
    """
    out: list[str] = []
    ld = e.get("limit_durumu") or {}
    if ld.get("durum") == "kilitli":
        out.append(f"bugün {ld.get('yon', '')} kilitli — karşı taraf boş")
    elif ld.get("durum") == "limit_disi":
        out.append("olağanüstü fiyat hareketi — günlük marj modeli geçersiz")
    vk = e.get("veri_kalitesi") or {}
    if not vk.get("ok", False):
        out.append("veri kalitesi: " + "; ".join(vk.get("uyarilar") or ["bilinmiyor"]))
    return out


def _analist_riskleri(a: dict | None) -> list[str]:
    """Analistin **BUGÜNKÜ** kararı. `aktif_vetolar`'ın kapatamadığı boşluk.

    ⚠ NE OLUYORDU (2026-08-15 denetimi): `siralama` analiz sözlüğünü kuruyor
    ama elde-OLMAYAN isimler dalında ONA HİÇ BAKMIYORDU; yalnız `holdings`
    dalı okuyordu ve portföy boş. Okunan tek veto kaynağı
    `e["aktif_vetolar"]` idi — o da paket üretilirken (zincir adım 7)
    hesaplanır, analist ise adım 8'de koşar. Yani bugünkü veto o listede
    YAPISAL OLARAK bulunamaz; ancak ertesi gün "yürürlükte" diye görünürdü.

    Ölçülen sonuç: 2026-08-14 raporunun §0'ı "🟢 KCHOL — GİR — plan bugün
    tetiklenebilir, ENGEL YOK" yazdı; aynı raporun §2'si ve aynı günün
    Telegram özeti "plan_reddet · VETO rejim_uyumsuz" dedi. Rapor kendi
    içinde ve kanallar arasında çelişti — üstelik en çok okunan bölümde.

    Bunlar ENGEL değil RİSKTİR (L-003): plan deterministik olarak hâlâ
    uygulanabilir, ama "engel yok" cümlesi kurulamaz. `siralama`'daki
    `gerçekten_gir = ... and not risk` koşulu gerisini kendi halleder.
    """
    if not a:
        return []
    out: list[str] = []
    vk = a.get("veto_code")
    if a.get("action") == "plan_reddet":
        out.append("analist BUGÜN planı reddetti"
                   + (f" · veto `{vk}`" if vk else ""))
    elif vk:
        out.append(f"analist BUGÜN veto koydu: `{vk}`")
    if a.get("signal") in AZALT_SINYALLERI:
        out.append(f"analistin bugünkü sinyali `{a['signal']}`")
    return out


def _riskler(e: dict, vetolar: list[dict], analiz: dict | None = None) -> list[str]:
    """Uygulamayı ENGELLEMEYEN ama sırayı geriye iten olgular."""
    out: list[str] = _analist_riskleri(analiz)
    bp = e.get("bilanco_penceresi") or {}
    if bp.get("durum") == "acik":
        n = len(bp.get("bildirimler") or [])
        out.append(f"plan ufkunda bilanço ({n} bekleyen bildirim)")
    elif bp.get("durum") == "bilinmiyor":
        out.append("bilanço penceresi BİLİNMİYOR (risk yok demek değil)")
    # `tekrar` ARDIŞIK BİR SERİ DEĞİL: `journal.aktif_vetolar` süresi dolanı
    # eliyor, yani sayılan şey bugün hâlâ yürürlükte olan tekrar sayısıdır ve
    # veto yeniden konmadan AZALABİLİR. "üst üste" demek iki farklı olguyu aynı
    # kelimeyle adlandırmaktı (L-003) — aynı hata rapor tablosunda da vardı ve
    # ikisi ayrı yerlerde yaşadığı için biri düzeltilirken diğeri atlanmıştı
    # (§11 kapatma tuzağı #5: simetriğini ara).
    for v in vetolar:
        out.append(f"yürürlükte veto `{v['veto_code']}` "
                   f"({v['kalan_islem_gunu']} işlem günü kaldı"
                   + (f", {v['tekrar']}× yürürlükte)" if v.get("tekrar", 1) > 1
                      else ")"))
    ld = e.get("limit_durumu") or {}
    if ld.get("durum") == "limite_yakin":
        out.append("günlük marja yakın kapandı")
    return out


def siralama(bundle: dict, *, holdings: dict | None = None,
             analiz: list[dict] | None = None) -> dict:
    """Bugünün sıralı eylem listesi. Saf fonksiyon — DB'ye dokunmaz.

    Sıra SÖZLÜKBİLİMSELDİR ve şu önceliktedir:

        1. AZALT — elde tutulan, analist `reduce/sell/avoid` demiş
        2. AZALT — elde tutulan, uygulanamaz hale gelmiş (kilit / veri)
        3. GİR   — planı olan, bugün tetiklenebilir, riski düşük
        4. İZLE  — planı olan ama bekleyen (above_zone / bilanço / veto)
        5. ENGELLİ — bugün yapılamaz olanlar, sebebiyle

    Son kırıcı `rr_net`tir ve bu bir GETİRİ SIRASI DEĞİLDİR: eşit
    uygulanabilirlikteki iki plan arasında maliyetten sonra daha geniş
    geometriye sahip olanı öne almak, kenar iddiası taşımaz.
    """
    tutulan = holdings or {}
    an = {a["ticker"]: a for a in (analiz or [])}
    rej = bundle.get("rejim") or {}
    pol = rej.get("pozisyon_politikasi") or {}
    maks = pol.get("maks_pozisyon")
    kontenjan = None if maks is None else max(0, int(maks) - len(tutulan))

    azalt: list[Eylem] = []
    gir: list[Eylem] = []
    izle: list[Eylem] = []
    engelli: list[Eylem] = []

    for e in bundle.get("evren", []):
        t = e["ticker"]
        vetolar = e.get("aktif_vetolar") or []
        eng = _engeller(e)
        a = an.get(t)
        # `a` ARTIK HER İKİ DALDA DA OKUNUYOR. Eskiden yalnız `holdings`
        # dalı okuyordu; elde olmayan isimler analistin bugünkü kararını
        # görmüyordu (bkz. `_analist_riskleri`).
        risk = _riskler(e, vetolar, a)
        planlar = e.get("plan_menusu") or []
        p = planlar[0] if planlar else None
        t1 = (p or {}).get("targets") or [{}]

        # ---------------------------------------------------- 1-2) ELDEKİLER
        if t in tutulan:
            sinyal = (a or {}).get("signal")
            if sinyal in AZALT_SINYALLERI:
                azalt.append(Eylem(
                    "azalt", t, f"AZALT — analist `{sinyal}`",
                    gerekce=[(a.get("thesis") or "")[:200]] if a else [],
                    engeller=eng, uygulanabilir=not eng))
            elif eng:
                azalt.append(Eylem(
                    "azalt", t, "GÖZDEN GEÇİR — pozisyon var ama uygulanamaz durumda",
                    gerekce=risk, engeller=eng, uygulanabilir=False))
            else:
                izle.append(Eylem("izle", t, "TUT — azaltma sinyali yok",
                                  gerekce=risk))
            continue

        # ---------------------------------------------------- 3-5) ELDE OLMAYANLAR
        if eng:
            engelli.append(Eylem("engelli", t, "bugün yapılamaz",
                                 engeller=eng, uygulanabilir=False))
            continue
        if not p:
            # Plan yok — sebebi zaten raporun ayrı bölümünde. Listeyi şişirmez.
            continue
        tetiklenebilir = p.get("entry_zone_status") == "in_zone"
        # ⚠ Kontenjan 0 ise YENİ GİRİŞ ÖNERİLMEZ. Rejim tavanı zaten dolmuşsa
        # "gir" demek, sistemin kendi kuralını yok saymasıdır — ve tam da bu
        # tür sessiz tutarsızlıklar okuyanı sisteme güvensiz kılar.
        kontenjan_var = kontenjan is None or kontenjan > 0
        if not kontenjan_var:
            risk = risk + [f"rejim tavanı DOLU ({len(tutulan)}/{maks}) — "
                           "yeni pozisyon için önce bir şey azaltılmalı"]
        # Başlık ile grup ASLA çelişmez: risk taşıyan bir plan "GİR" diyemez.
        gerçekten_gir = tetiklenebilir and kontenjan_var and not risk
        if gerçekten_gir:
            baslik = "GİR — plan bugün tetiklenebilir, engel yok"
        elif tetiklenebilir:
            baslik = "BEKLE — plan tetiklenebilir AMA aşağıdaki riskler var"
        else:
            baslik = ("BEKLE — plan bir geri çekilmeye bağlı "
                      f"({p.get('entry_zone_status')})")
        ey = Eylem(
            "gir" if gerçekten_gir else "izle", t, baslik,
            gerekce=risk, plan_id=p.get("plan_id"),
            riske_edilen_pct=p.get("max_loss_pct_of_portfolio"),
            rr_net=t1[0].get("rr_net"))
        (gir if ey.tur == "gir" else izle).append(ey)

    def _anahtar(x: Eylem):
        # Sözlükbilimsel: önce risk sayısı (az olan önde), sonra maliyetli
        # geometri (geniş olan önde), sonra ticker (determinizm).
        return (len(x.gerekce), -(x.rr_net or 0.0), x.ticker)

    azalt.sort(key=lambda x: (x.uygulanabilir, x.ticker))
    gir.sort(key=_anahtar)
    izle.sort(key=_anahtar)
    engelli.sort(key=lambda x: x.ticker)

    return {
        "azalt": azalt, "gir": gir, "izle": izle, "engelli": engelli,
        "kontenjan": kontenjan, "tutulan_n": len(tutulan),
        "maks_pozisyon": maks, "rejim": rej.get("etiket"),
        "nakit_pct": pol.get("nakit_pct"),
        # Analist çıktısı yoksa "azalt" tarafı boş görünür ve bu, "azaltacak
        # bir şey yok" ile karıştırılabilir (L-007).
        "analist_var": bool(analiz),
    }
