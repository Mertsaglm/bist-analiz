"""KAP (Kamuyu Aydınlatma Platformu) bildirim akışı.

KAP **tier-1 kaynaktır**: şirketin kendi resmî beyanı. Türkiye'de yatırım
kararına girebilecek tek gerçekten güvenilir haber kaynağı budur — ana akım
finans basını ve forumlar bilerek dışarıda bırakıldı, çünkü güvenilirlikleri
ölçülmedi ve büyük kısmı tekrar/manipülatif içerik.

ÖLÇÜLDÜ (2026-07-27): `POST /tr/api/disclosure/members/byCriteria` doğru
başlıklarla (User-Agent + Referer) **200 ve JSON** dönüyor. Planın "KAP 308
yönlendirme döndürüyor" notu YANLIŞ çıktı — yine LESSONS L-005: araştırmadan
gelen bilgi bayatlar, ölçerek doğrula.

Kayıt yapısı (ölçüldü):
    publishDate      "25.07.2026 17:25:43"   (GG.AA.YYYY SS:DD:SS)
    stockCodes       "THYAO"  ← GÜVENİLİR alan
    relatedStocks    çoğunlukla null         ← kullanma
    disclosureIndex  benzersiz id
    disclosureCategory  ODA | STT | FR | null
    subject / summary   başlık ve özet

**Haber SAYIYA ÇEVRİLMEZ.** Duygu skoru üretilmiyor: TR finans haberinin
sinyal/gürültü oranı ölçülmedi ve ölçülmeden sayıya çevirmek, uydurulmuş bir
kesinlik üretmek olurdu. Haber, LLM'e ham başlık olarak gider; yorum prose'da
kalır ve `news_refs` ile kaynağa bağlanır (HF-28 uydurma id'yi yakalar).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import requests

from .. import util

log = logging.getLogger(__name__)

TIMEOUT = 30
BASE = "https://www.kap.org.tr"
ENDPOINT = "/tr/api/disclosure/members/byCriteria"
TZ = "Europe/Istanbul"          # KAP damgaları yerel saattir

# Önem sınıflandırması — HEURİSTİK, ölçülmedi. Amacı sıralama/gösterim,
# ağırlıklandırma değil. Analist ham başlığı da görür.
_YUKSEK = ("sermaye artırımı", "bedelsiz", "bölünme", "birleşme", "devralma",
           "kâr payı", "kar payı", "temettü", "geri alım", "pay geri alım",
           "finansal rapor", "bilanço", "kâr", "zarar", "ihale", "sözleşme",
           "yatırım teşvik", "ortaklık yapısı", "yönetim kurulu")
_DUSUK = ("devre kesici", "tipe dönüşüm", "genel kurul toplantı çağrısı",
          "yatırımcı sunumu", "faaliyet raporu", "sürdürülebilirlik")


@dataclass(frozen=True, slots=True)
class FetchSonuc:
    """KAP çekiminin sonucu — `hata` None DEĞİLSE `kayitlar` güvenilmezdir."""
    kayitlar: list[dict]
    hata: str | None = None
    tickersiz: int = 0
    atlanan_aralik: str | None = None
    # API'nin döndürdüğü HAM kayıt sayısı (normalize/filtre öncesi). Kırpılma
    # tespiti buna bakar: yanıt tavana dayandıysa pencere doymuştur.
    kayitlar_ham: int | None = None

    @property
    def ok(self) -> bool:
        return self.hata is None


def _headers(cfg: dict) -> dict:
    return {
        "User-Agent": cfg["sources"]["kap"].get("user_agent", "bist-analiz/0.1"),
        "Referer": f"{BASE}/tr/bildirim-sorgu",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _parse_dt(s: str | None) -> str | None:
    """'25.07.2026 17:25:43' (İSTANBUL YEREL) → `+00:00` ekli UTC ISO.

    ⚠ KAP damgaları İstanbul saatidir; kolonun adı `published_utc`. İlk sürüm
    bunları naif biçimde yazıyordu, yani adı UTC içeriği yerel bir alan üretiyordu.
    Sonra o alan `predictions.created_utc` (gerçek UTC, `+00:00` ekli) ile METİN
    olarak karşılaştırılıyordu → 3 saatlik sessiz kayma + farklı uzunluktaki
    dizelerin yanlış sıralanması. Dönüşüm burada, tek yerde yapılır.
    """
    if not s:
        return None
    try:
        ham = datetime.strptime(s.strip(), "%d.%m.%Y %H:%M:%S")
    except ValueError:
        iso = util.to_iso_date(s.split(" ")[0])
        if not iso:
            return None
        ham = datetime.fromisoformat(f"{iso}T00:00:00")
    return util.to_utc_iso(ham, assume_tz=TZ)


def importance(subject: str | None, summary: str | None,
               category: str | None) -> str:
    """yuksek | orta | dusuk — HEURİSTİK, ölçülmedi.

    Sıralama ve gösterim içindir; hiçbir sayısal ağırlığa çevrilmez.
    """
    metin = f"{subject or ''} {summary or ''}".lower()
    if any(k in metin for k in _DUSUK):
        return "dusuk"
    if category == "FR" or any(k in metin for k in _YUKSEK):
        return "yuksek"
    return "orta"


def fetch(cfg: dict, *, from_date: str, to_date: str) -> "FetchSonuc":
    """Tarih aralığındaki bildirimler. İstisna FIRLATMAZ, ama HATAYI GİZLEMEZ.

    ⚠ Neden `(kayitlar, hata)` döndürüyor: ilk sürüm her istisnada sessizce boş
    liste veriyordu. O zaman "bugün bildirim yok" ile "KAP'a ulaşılamadı" aynı
    çıktıya düşüyor, `bist haber cek` 0 koduyla bitiyor ve pakete her hisse için
    `haberler: []` yazılıyordu. ADR #008 sonrası haber/veto sistemin kalan ana
    ürünü olduğu için bu ayrımın taşınması ŞART (bkz. LESSONS L-002 deseni:
    sessiz bozulma alarm üretmez).
    """
    kcfg = cfg["sources"]["kap"]
    url = kcfg.get("base", BASE) + kcfg.get("disclosures_path", ENDPOINT)
    body = {"fromDate": from_date, "toDate": to_date, "disclosureClass": "",
            "index": "", "market": "", "memberType": "IGS",
            "mkkMemberOidList": [], "subjectList": [], "term": "", "year": ""}
    try:
        r = requests.post(url, headers=_headers(cfg), json=body, timeout=TIMEOUT)
        r.raise_for_status()
        ham = r.json()
    except Exception as e:                                       # noqa: BLE001
        log.warning("KAP çekilemedi (%s … %s): %s", from_date, to_date, e)
        return FetchSonuc([], f"{type(e).__name__}: {e}", 0)
    if not isinstance(ham, list):
        log.warning("KAP beklenmeyen yanıt tipi: %s", type(ham).__name__)
        return FetchSonuc([], f"beklenmeyen yanıt tipi: {type(ham).__name__}", 0)

    kayitlar, tickersiz = [], 0
    for x in ham:
        n = _normalize(x)
        if n is None:
            continue
        # `stockCodes` boşsa bildirim hiçbir hisseye bağlanamaz ve `news.store`
        # onu sessizce düşürür (piyasa geneli duyurular). Düşmesi doğru, ama
        # SAYILMASI şart: "0 satır yazıldı" ile "hepsi hissesizdi" farklı olgular.
        if not n["tickers"]:
            tickersiz += 1
            continue
        kayitlar.append(n)
    return FetchSonuc(kayitlar, None, tickersiz, kayitlar_ham=len(ham))


def _normalize(x: dict) -> dict | None:
    idx = x.get("disclosureIndex")
    yayin = _parse_dt(x.get("publishDate"))
    if idx is None or not yayin:
        return None
    # `stockCodes` GÜVENİLİR; `relatedStocks` çoğunlukla null (ölçüldü).
    kodlar = [k.strip().upper() for k in (x.get("stockCodes") or "").split(",")
              if k.strip()]
    konu, ozet = x.get("subject"), x.get("summary")
    return {
        "disclosure_id": f"kap-{idx}",
        "tickers": kodlar,
        "published_utc": yayin,
        "tier": 1,                       # KAP = resmî beyan
        "title": (konu or "").strip() or None,
        "summary": (ozet or "").strip() or None,
        "url": f"{BASE}/tr/Bildirim/{idx}",
        "category": x.get("disclosureCategory"),
        "importance": importance(konu, ozet, x.get("disclosureCategory")),
        "company": x.get("kapTitle"),
    }


def fetch_incremental(cfg: dict, *, since: str | None, until: str | None = None,
                      overlap_days: int = 2, tam_gun: int | None = None,
                      parca_gun: int | None = None) -> FetchSonuc:
    """`since`'den bugüne YENİ bildirimler — PARÇA PARÇA çekilir.

    `overlap_days` kadar geriye taşarak çeker: KAP geç yayımlanan (`isLate`)
    bildirimler içeriyor ve tam sınırdan başlamak onları kaçırırdı. Tekrarları
    `disclosure_id` birincil anahtarı eler — üst üste çekmek zararsızdır.

    ⚠⚠ **KAP GENİŞ PENCEREYİ SESSİZCE KIRPIYOR.** ÖLÇÜLDÜ (2026-07-27,
    canlı API): dar pencereler birebir doğru dönüyor, geniş pencereler
    ~1578 kayıtta doyuyor ve YALNIZ EN YENİ kısmı veriyor:

           7 gün istendi →  931 kayıt, 07-20…07-27   tam
          14 gün istendi → 1578 kayıt, 07-13…07-27   tam
          21 gün istendi → 1578 kayıt, 07-13…07-27   ⚠ KIRPILDI
          90 gün istendi → 1578 kayıt, 07-13…07-27   ⚠ KIRPILDI
        (2026-05-01…05-10 ayrıca birebir döndü → `fromDate` ÇALIŞIYOR,
         sorun pencere genişliği.)

    Yani tek istekle 90 gün istemek, 76 gününü sessizce kaybetmek demekti —
    hiçbir hata da vermeden. `evds.fetch_series_chunked` aynı tuzağı aynı
    çözümle aşıyor (LESSONS L-005: inancı ölçüme çevir).

    Bu yüzden aralık `parca_gun`'lük dilimlere bölünür ve HER DİLİM ayrıca
    kırpılma açısından denetlenir: dönen en eski kayıt istenen başlangıçtan
    yeniyse o dilim eksiktir ve `atlanan_aralik`'ta rapor edilir.
    """
    kcfg = cfg["sources"]["kap"]
    if tam_gun is None:
        tam_gun = int(kcfg.get("tam_cekim_gun", 90))
    if parca_gun is None:
        parca_gun = int(kcfg.get("parca_gun", 7))
    doyma_esigi = int(kcfg.get("doyma_esigi", 1400))

    bitis = util.parse_date(until) if until else date.today()
    if since:
        bas = (util.parse_date(since) or bitis) - timedelta(days=overlap_days)
    else:
        # Tam çekim: `tam_cekim_gun` kadar geriye. Config'ten okunur çünkü
        # "ne kadar geriye" bir ürün kararıdır, koda gömülecek bir sabit değil.
        bas = bitis - timedelta(days=tam_gun)
    if bas > bitis:
        bas = bitis

    tekil: dict[str, dict] = {}
    durum = {"tickersiz": 0, "hata": None, "kirpilan": []}

    def cek(a: date, b: date, derinlik: int = 0) -> None:
        """Bir aralığı çeker; DOYDUYSA ikiye bölüp kendini tekrar çağırır.

        ⚠ Sabit dilim genişliği KIRILGAN. Bildirim hacmi mevsimlik: Temmuz'da
        7 gün 931 kayıt, Mayıs'ta (bilanço sezonu) aynı 7 gün tavanı (2000)
        aşıyor. Sabit bir sayı seçmek, yoğun haftalarda sessizce veri
        kaybetmek demek. Doymayı GÖZLEYİP tepki vermek, tahmin etmekten
        güvenli — `parca_gun` yalnız bir başlangıç değeridir.
        """
        s = fetch(cfg, from_date=a.isoformat(), to_date=b.isoformat())
        if not s.ok:
            durum["hata"] = durum["hata"] or s.hata   # ilk hatayı taşı, devam et
            return
        durum["tickersiz"] += s.tickersiz
        ham = s.kayitlar_ham if s.kayitlar_ham is not None else len(s.kayitlar)
        for k in s.kayitlar:
            tekil[k["disclosure_id"]] = k

        # KIRPILMA ÖLÇÜTÜ: "ilk gün boş" DEĞİL, "yanıt tavana dayandı".
        # Bildirimsiz bir gün (tatil) tamamen normaldir ve ilk sürümde yanlış
        # alarm veriyordu (2026-05-05 → 05-06: o gün gerçekten bildirim yoktu).
        tarihler = sorted(k["published_utc"][:10] for k in s.kayitlar)
        doydu = ham >= doyma_esigi and tarihler and tarihler[0] > a.isoformat()
        if not doydu:
            return
        if a == b or derinlik >= 6:
            # Tek güne indik ve hâlâ doyuyor → bu günün tamamı alınamıyor.
            durum["kirpilan"].append(f"{a.isoformat()}…{tarihler[0]}")
            log.warning("KAP: %s tek başına tavanı aşıyor (%d kayıt) — "
                        "o günün tamamı alınamadı", a, ham)
            return
        orta = a + (b - a) // 2
        log.info("KAP dilimi doydu (%d kayıt, %s…%s) — ikiye bölünüyor",
                 ham, a, b)
        cek(a, orta, derinlik + 1)
        cek(orta + timedelta(days=1), b, derinlik + 1)

    p_bas = bas
    while p_bas <= bitis:
        p_son = min(p_bas + timedelta(days=parca_gun - 1), bitis)
        cek(p_bas, p_son)
        p_bas = p_son + timedelta(days=1)

    kayitlar = [tekil[k] for k in sorted(tekil)]
    atlanan = " · ".join(durum["kirpilan"]) if durum["kirpilan"] else None
    return FetchSonuc(kayitlar, durum["hata"], durum["tickersiz"], atlanan)


# ==================================================== beklenen bildirim (ileriye dönük)
@dataclass(frozen=True, slots=True)
class BeklenenSonuc:
    """Beklenen bildirim çekiminin sonucu.

    `kirpik=True` ise liste TAVANA DAYANMIŞTIR ve içindeki YOKLUK hiçbir şey
    kanıtlamaz — "bu şirketin bildirimi yok" ile "listede göremedim" aynı
    çıktıya düşer. Bu yüzden kırpık yanıt SAKLANMAZ (bkz. `news.sync_beklenen`).

    `kapali=True` ise katman KONFİGLE kapatılmıştır — bu bir HATA DEĞİLDİR.
    İkisini aynı kovaya atmak L-003'tür ve yaşandı: `sources.kap.enabled=False`
    iken komut hem "KAP kapalı" hem "⚠ beklenen bildirim takvimi:
    ConnectionError" basıyor, üstelik çıkış kodunu 1 yapıyordu. `news.sync`
    aynı olguyu zaten `atlandi` ile ayırıyordu; simetriği burada eksikti.
    """
    kayitlar: list[dict]
    hata: str | None = None
    kirpik: bool = False
    ham: int = 0
    sirket: int = 0
    kapali: bool = False

    @property
    def ok(self) -> bool:
        return self.hata is None and not self.kirpik and not self.kapali


def _bb_tarih(s: str | None) -> str | None:
    """'01.07.2026' → '2026-07-01'. Beklenen bildirim ucu SAAT taşımaz."""
    if not s:
        return None
    p = str(s).strip().split(" ")[0].split(".")
    if len(p) != 3:
        return None
    try:
        return date(int(p[2]), int(p[1]), int(p[0])).isoformat()
    except ValueError:
        return None


def fetch_beklenen(cfg: dict) -> BeklenenSonuc:
    """KAP'ın HENÜZ AÇIKLANMAMIŞ bildirim takvimi (finansal rapor pencereleri).

    Uç, bir şirket raporunu yayımladığında onu listeden DÜŞÜRÜR — yani canlı
    bir geri sayımdır. Doğrulandı 2026-08-07: AKBNK (07-28) ve GARAN (07-30)
    bilançolarını açıkladıktan sonra listede yoklar.

    `stockCode` alanı kayıtların yalnız %6.7'sinde dolu olduğu için ticker'a
    ORADAN bağlanmaz; bağlama `kapTitle` ↔ `disclosures.company` üzerinden
    `news` katmanında yapılır (o eşleme KAP'ın kendi verisinden, `stockCodes`
    ile birlikte gelmiştir — yani inşaen doğrudur).
    """
    k = cfg["sources"]["kap"]
    # ⚠ ANA ANAHTAR ÖNCE. `sources.kap.enabled` KAP katmanının tamamını kapatır;
    # bu fonksiyon yalnız kendi alt anahtarına (`beklenen_bildirim.enabled`)
    # bakıyordu ve ana anahtar KAPALIYKEN BİLE ağa çıkıyordu.
    #
    # Ölçüldü (2026-08-28 denetimi): `sources.kap.enabled=False` iken
    # `bist haber cek` şunu basıyordu —
    #     KAP kapalı (config.sources.kap.enabled)
    #     ⚠ beklenen bildirim takvimi: ConnectionError: ... kap.org.tr
    # yani kapatma anahtarı kapatmıyordu; komut "kapalı" deyip aynı nefeste
    # KAP'a bağlanmayı deniyordu. Bir kaynak düştüğü için onu kapatan kullanıcı,
    # kapattığını sanarak aynı hataya devam ederdi.
    #
    # Kontrol KAYNAK SINIRINA konur (§11 tuzak 5): tek çağrı yerini düzeltmek
    # kuralı uygulamak değildir — burada hiçbir çağıran atlayamaz.
    if not k.get("enabled", False):
        return BeklenenSonuc([], "KAP kapalı (config.sources.kap.enabled)",
                            kapali=True)
    b = k.get("beklenen_bildirim") or {}
    if not b.get("enabled", False):
        return BeklenenSonuc([], "beklenen_bildirim kapalı", kapali=True)
    gun = int(b.get("pencere_gun", 45))
    bugun = util.today_local(cfg["takvim"]["timezone"]) if hasattr(util, "today_local") \
        else date.today()
    body = {
        "startDate": bugun.isoformat(),
        "endDate": (bugun + timedelta(days=gun)).isoformat(),
        "memberTypes": ["IGS"], "mkkMemberOidList": [], "disclosureClass": "",
        "subjects": [], "mainSector": "", "sector": "", "subSector": "",
        "market": "", "index": "", "year": "", "term": "", "ruleType": "",
    }
    h = dict(_headers(cfg))
    h["Origin"] = "https://kap.org.tr"
    h["Referer"] = "https://kap.org.tr/tr/beklenen-bildirim-sorgu"
    tavan = int(b.get("tavan_kayit", 1950))
    budget = int(b.get('maks_sorgu', 63))
    requests_used = 0

    def fetch_window(start, end):
        nonlocal requests_used
        requests_used += 1
        if requests_used > budget:
            raise ValueError('Beklenen bildirim sorgu bütçesi aşıldı; tamlık doğrulanamadı.')
        query = dict(body, startDate=start.isoformat(), endDate=end.isoformat())
        response = requests.post('https://kap.org.tr' + b.get('path', ''),
                                 json=query, headers=h, timeout=TIMEOUT)
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise ValueError('Beklenmeyen beklenen-bildirim yanıtı.')
        if len(rows) < tavan:
            return rows, False
        if start == end:
            # Tek güne kadar bölündüğünde hâlâ doluysa yokluk kanıtı üretme.
            return [], True
        midpoint = start + (end-start)//2
        left, clipped = fetch_window(start, midpoint)
        if clipped:
            return [], True
        right, clipped = fetch_window(midpoint + timedelta(days=1), end)
        return ([] if clipped else left + right), clipped

    try:
        ham, kirpik = fetch_window(bugun, bugun + timedelta(days=gun))
    except Exception as e:
        log.warning('KAP beklenen bildirim tam alınamadı: %s', type(e).__name__)
        return BeklenenSonuc([], type(e).__name__ + ': takvim tam alınamadı')
    if kirpik:
        return BeklenenSonuc([], 'Tek günlük yanıt tavanda; takvim tam alınamadı.', True, tavan)

    kayitlar = []
    for x in ham:
        bas, son = _bb_tarih(x.get("startDate")), _bb_tarih(x.get("endDate"))
        baslik = (x.get("kapTitle") or "").strip()
        konu = (x.get("subject") or "").strip()
        if not (baslik and konu and bas and son):
            continue
        kayitlar.append({
            "kap_title": baslik, "subject": konu,
            "period": (x.get("ruleTypeTerm") or "").strip() or None,
            "year": x.get("year"), "start_date": bas, "end_date": son,
        })
    # Komşu sorgularda tekrar dönen rapor aynı olaydır, iki bildirim değildir.
    unique = {tuple(str(row[k]) for k in ('kap_title','subject','period','year','start_date','end_date')): row
              for row in kayitlar}
    kayitlar = [unique[key] for key in sorted(unique)]
    sirket = len({row['kap_title'] for row in kayitlar})
    return BeklenenSonuc(kayitlar, None, False, len(ham), sirket)
