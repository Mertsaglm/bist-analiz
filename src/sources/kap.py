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
from datetime import date, datetime, timedelta

import requests

from .. import util

log = logging.getLogger(__name__)

TIMEOUT = 30
BASE = "https://www.kap.org.tr"
ENDPOINT = "/tr/api/disclosure/members/byCriteria"

# Önem sınıflandırması — HEURİSTİK, ölçülmedi. Amacı sıralama/gösterim,
# ağırlıklandırma değil. Analist ham başlığı da görür.
_YUKSEK = ("sermaye artırımı", "bedelsiz", "bölünme", "birleşme", "devralma",
           "kâr payı", "kar payı", "temettü", "geri alım", "pay geri alım",
           "finansal rapor", "bilanço", "kâr", "zarar", "ihale", "sözleşme",
           "yatırım teşvik", "ortaklık yapısı", "yönetim kurulu")
_DUSUK = ("devre kesici", "tipe dönüşüm", "genel kurul toplantı çağrısı",
          "yatırımcı sunumu", "faaliyet raporu", "sürdürülebilirlik")


def available() -> bool:
    return True          # anahtar gerektirmiyor


def _headers(cfg: dict) -> dict:
    return {
        "User-Agent": cfg["sources"]["kap"].get("user_agent", "bist-analiz/0.1"),
        "Referer": f"{BASE}/tr/bildirim-sorgu",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _parse_dt(s: str | None) -> str | None:
    """'25.07.2026 17:25:43' → ISO. Sıralanabilirlik şart (bkz. util.to_iso_date)."""
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%d.%m.%Y %H:%M:%S").isoformat()
    except ValueError:
        iso = util.to_iso_date(s.split(" ")[0])
        return f"{iso}T00:00:00" if iso else None


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


def fetch(cfg: dict, *, from_date: str, to_date: str) -> list[dict]:
    """Tarih aralığındaki bildirimler. Hata → boş liste (asla istisna)."""
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
        return []
    if not isinstance(ham, list):
        log.warning("KAP beklenmeyen yanıt tipi: %s", type(ham).__name__)
        return []
    return [n for n in (_normalize(x) for x in ham) if n]


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
                      overlap_days: int = 2, max_days: int = 90) -> list[dict]:
    """`since`'den bugüne YENİ bildirimler.

    `overlap_days` kadar geriye taşarak çeker: KAP geç yayımlanan (`isLate`)
    bildirimler içeriyor ve tam sınırdan başlamak onları kaçırırdı. Tekrarları
    `disclosure_id` birincil anahtarı eler — üst üste çekmek zararsızdır.
    """
    bitis = util.parse_date(until) if until else date.today()
    if since:
        bas = (util.parse_date(since) or bitis) - timedelta(days=overlap_days)
    else:
        bas = bitis - timedelta(days=30)
    if (bitis - bas).days > max_days:
        bas = bitis - timedelta(days=max_days)
        log.info("KAP penceresi %d güne kırpıldı", max_days)
    return fetch(cfg, from_date=bas.isoformat(), to_date=bitis.isoformat())
