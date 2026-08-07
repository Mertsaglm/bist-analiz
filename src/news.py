"""Haber katmanı — KAP bildirimlerinin saklanması ve sorgulanması.

**Artımlı çekim:** veritabanındaki en son bildirim tarihinden itibaren çekilir,
aynı haberler tekrar taranmaz. `disclosure_id` birincil anahtar olduğu için
üst üste çekmek zararsızdır — çakışan kayıt sessizce güncellenir.

**Haber sayıya çevrilmez.** Duygu skoru YOK, ağırlık YOK. Sebep: TR finans
haberinin sinyal/gürültü oranı ÖLÇÜLMEDİ ve ölçülmeden sayıya çevirmek
uydurulmuş bir kesinlik üretmek olurdu. Haber, analiste ham başlık olarak
gider; yorum prose'da kalır ve `news_refs` ile kaynağa bağlanır.

`importance` alanı bir HEURİSTİKTİR ve bunu her yerde yazıyoruz: sıralama ve
gösterim içindir, hiçbir hesaba girmez.
"""

from __future__ import annotations

import logging
import sqlite3

from . import db, util
from .sources import kap

log = logging.getLogger(__name__)

DISC_COLS = ["disclosure_id", "ticker", "published_utc", "tier", "importance",
             "title", "summary", "url", "category", "company", "fetched_utc"]


def last_seen(con: sqlite3.Connection, ticker: str | None = None) -> str | None:
    """Veritabanındaki en son bildirim zamanı — artımlı çekimin başlangıcı."""
    if ticker:
        return db.scalar(con, "SELECT MAX(published_utc) FROM disclosures "
                              "WHERE ticker = ?", (ticker.upper(),))
    return db.scalar(con, "SELECT MAX(published_utc) FROM disclosures")


def store(con: sqlite3.Connection, kayitlar: list[dict],
          tickers: set[str] | None = None) -> dict:
    """Bildirimleri saklar. `tickers` verilirse yalnız o hisselere ait olanlar.

    Bir bildirim birden çok hisseye aitse HER BİRİ için satır yazılır —
    bileşik anahtar bunu mümkün kılar.
    """
    now = util.utc_now_iso()
    rows, gorulen = [], set()
    for k in kayitlar:
        for t in k["tickers"]:
            if tickers is not None and t not in tickers:
                continue
            rows.append((k["disclosure_id"], t, k["published_utc"], k["tier"],
                         k["importance"], k["title"], k["summary"], k["url"],
                         k["category"], k["company"], now))
            gorulen.add(t)
    n = db.upsert_many(con, "disclosures", DISC_COLS, rows)
    return {"yazilan": n, "bildirim": len(kayitlar), "ticker": len(gorulen)}


def sync(cfg: dict, con: sqlite3.Connection, *, until: str | None = None,
         full: bool = False, gun: int | None = None) -> dict:
    """Artımlı KAP senkronu — evrendeki hisselerle sınırlı.

    Dönen sözlükte `hata` ve `atlanan_aralik` DAİMA bulunur. Çağıran taraf
    (CLI) bunları görünür kılmakla yükümlüdür: "0 bildirim" ile "çekilemedi"
    aynı çıktıya düşerse sistem sessizce habersiz çalışmaya devam eder.
    """
    from . import universe

    if not cfg["sources"]["kap"].get("enabled", False):
        log.info("KAP kapalı (config.sources.kap.enabled)")
        return {"atlandi": True, "yazilan": 0, "hata": None,
                "atlanan_aralik": None}

    ev = set(universe.all_tickers(con))
    since = None if full else last_seen(con)
    s = kap.fetch_incremental(cfg, since=since, until=until, tam_gun=gun)
    sonuc = store(con, s.kayitlar, tickers=ev)
    sonuc.update({
        "since": since or "(tam çekim)",
        "atlandi": False,
        "hata": s.hata,
        "tickersiz": s.tickersiz,
        "atlanan_aralik": s.atlanan_aralik,
    })
    return sonuc


def kaynak_durumu(con: sqlite3.Connection, asof: str, *,
                  bayat_gun: int = 5) -> dict:
    """Haber katmanının SAĞLIK durumu — pakete girer.

    Pakette boş bir `haberler` listesi iki farklı olguyu temsil edebilir:
    "bu hissede bildirim yok" ve "KAP taraması hiç çalışmadı / bayat". İkisini
    ayırt edemeyen analist ikincisini birincisi sanar. Bu fonksiyon farkı
    tek bir alana indirger.
    """
    son = last_seen(con)
    if son is None:
        return {"ok": False, "son_bildirim": None,
                "not": "KAP taraması hiç çalışmadı — `bist haber cek`"}
    gun = None
    d_son, d_asof = util.parse_date(son[:10]), util.parse_date(asof)
    if d_son and d_asof:
        gun = (d_asof - d_son).days
    if gun is not None and gun > bayat_gun:
        return {"ok": False, "son_bildirim": son, "gecikme_gun": gun,
                "not": f"KAP verisi {gun} gün bayat — boş haber listesi "
                       f"'bildirim yok' anlamına GELMEZ"}
    return {"ok": True, "son_bildirim": son, "gecikme_gun": gun, "not": None}


def for_ticker(con: sqlite3.Connection, ticker: str, *, since: str | None = None,
               limit: int = 8) -> list[dict]:
    """Bir hissenin bildirimleri, yeniden eskiye.

    `since` verilirse yalnız o andan SONRAKİLER — "aynı haberi tekrar tarama"
    kuralının paket tarafındaki karşılığı.
    """
    sql = "SELECT * FROM disclosures WHERE ticker = ?"
    params: list = [ticker.upper()]
    if since:
        sql += " AND published_utc > ?"
        params.append(since)
    return db.fetch_all(con, sql + " ORDER BY published_utc DESC LIMIT ?",
                        (*params, limit))


def bundle_view(con: sqlite3.Connection, ticker: str, *, since: str | None = None,
                limit: int = 8) -> list[dict]:
    """Pakete giren sade biçim. `id` alanı HF-28'in doğruladığı referanstır."""
    return [{
        "id": r["disclosure_id"],
        "tarih": r["published_utc"][:16].replace("T", " "),
        "kaynak": "KAP (resmî beyan)" if r["tier"] == 1 else "diğer",
        "onem": r["importance"],
        "baslik": r["title"],
        "ozet": r["summary"],
        "url": r["url"],
    } for r in for_ticker(con, ticker, since=since, limit=limit)]


def summary(con: sqlite3.Connection) -> dict:
    return {
        "toplam": db.scalar(con, "SELECT COUNT(*) FROM disclosures") or 0,
        "ticker": db.scalar(con, "SELECT COUNT(DISTINCT ticker) FROM disclosures") or 0,
        "ilk": db.scalar(con, "SELECT MIN(published_utc) FROM disclosures"),
        "son": db.scalar(con, "SELECT MAX(published_utc) FROM disclosures"),
        "onem": {r["importance"]: r["n"] for r in db.fetch_all(
            con, "SELECT importance, COUNT(*) n FROM disclosures "
                 "GROUP BY importance ORDER BY n DESC")},
    }


# ================================================== beklenen bildirim (ileriye dönük)
BEKLENEN_YOK = {
    "durum": "bilinmiyor", "bildirimler": [],
    "not": "beklenen bildirim takvimi değerlendirilmedi",
}

#: Takvimde görünmeyen bir ismin "zaten açıkladı" sayılabilmesi için finansal
#: rapor bildiriminin en fazla kaç gün önce olması gerektiği. Çeyreklik raporlama
#: döngüsü ~90 gün; 75 gün, bir sonraki dönemin penceresi açılmadan önceki
#: güvenli aralıktır.
BEKLENEN_FR_KANIT_GUN = 75


def sync_beklenen(cfg: dict, con: sqlite3.Connection) -> dict:
    """KAP'ın ileriye dönük bildirim takvimini çeker ve TAM İSE saklar.

    ⚠ KIRPIK YANIT SAKLANMAZ. Tavana dayanmış bir listede bir şirketin
    bulunmaması "bildirimi yok" değil "göremedim" demektir; ikisini aynı satıra
    yazmak L-007'nin tam kendisidir. Kırpıldığında eski (tam) anlık görüntü
    korunur ve yaşı `pencere()`yi `bilinmiyor`a düşürür.

    ⚠ TABLO HER ÇEKİMDE SIFIRLANIR. Bir şirket raporunu yayımlayınca uçtan
    DÜŞER; eski satır silinmezse "hâlâ bekleniyor" diye yaşamaya devam eder.
    Yani burada üstüne yazmak değil, DEĞİŞTİRMEK gerekiyor.
    """
    from .sources import kap

    s = kap.fetch_beklenen(cfg)
    if not s.ok:
        return {"ok": False, "hata": s.hata, "kirpik": s.kirpik,
                "ham": s.ham, "yazilan": 0,
                "not": ("yanıt TAVANA dayandı, saklanmadı — eski anlık görüntü "
                        "korunuyor" if s.kirpik else s.hata)}

    # ad → ticker: KAP'ın KENDİ verisinden (stockCodes ile birlikte gelmişti),
    # yani eşleme inşaen doğrudur. Kendi sözlüğümüzü kurmak, kırılgan bir HTML
    # kazımasına (borsapy'nin memberOid yolu) bağımlı olmamızı engelliyor.
    ad2t: dict[str, str] = {
        (r["company"] or "").strip(): r["ticker"]
        for r in db.fetch_all(
            con, "SELECT company, ticker FROM disclosures "
                 " WHERE company IS NOT NULL GROUP BY company, ticker")}

    now = util.utc_now_iso()
    rows = []
    for k in s.kayitlar:
        t = ad2t.get(k["kap_title"])
        if not t:
            continue                      # evrenimiz dışındaki şirket
        rows.append((t, k["kap_title"], k["subject"], k["period"], k["year"],
                     k["start_date"], k["end_date"], now))
    con.execute("DELETE FROM expected_disclosures")
    n = db.upsert_many(
        con, "expected_disclosures",
        ["ticker", "kap_title", "subject", "period", "year",
         "start_date", "end_date", "fetched_utc"], rows)
    con.commit()
    log.info("beklenen bildirim: %d ham kayıt → %d satır (%d ticker)",
             s.ham, n, len({r[0] for r in rows}))
    return {"ok": True, "hata": None, "kirpik": False, "ham": s.ham,
            "yazilan": n, "ticker": len({r[0] for r in rows}), "not": None}


def beklenen_durumu(cfg: dict, con: sqlite3.Connection, asof: str) -> dict:
    """Takvimin SAĞLIĞI — `kaynak_durumu`nun beklenen-bildirim karşılığı.

    Boş bir sonuç iki farklı olgu olabilir: "bu şirketin bekleyen bildirimi
    yok" ve "takvim hiç çekilmedi / bayat". Ayrımı tek alana indirger.
    """
    b = (cfg["sources"]["kap"].get("beklenen_bildirim") or {})
    if not b.get("enabled", False):
        return {"ok": False, "not": "beklenen bildirim katmanı kapalı"}
    son = db.scalar(con, "SELECT MAX(fetched_utc) FROM expected_disclosures")
    if not son:
        return {"ok": False, "son_cekim": None,
                "not": "takvim hiç çekilmedi — `bist haber cek`"}
    d_son, d_asof = util.parse_date(son[:10]), util.parse_date(asof)
    yas = (d_asof - d_son).days if (d_son and d_asof) else None
    maks = int(b.get("maks_yas_gun", 7))
    if yas is not None and yas > maks:
        return {"ok": False, "son_cekim": son, "yas_gun": yas,
                "not": f"takvim {yas} gün bayat (>{maks}) — bu arada bilanço "
                       "açıklanmış olabilir; boş sonuç 'risk yok' DEĞİLDİR"}
    return {"ok": True, "son_cekim": son, "yas_gun": yas, "not": None}


def beklenen_pencere(con: sqlite3.Connection, ticker: str, asof: str,
                     bitis: str, *, saglik: dict | None = None) -> dict:
    """Bu hissenin plan penceresine düşen beklenen bildirimleri.

    Üç hâl, ve üçü ASLA aynı değere düşmez (L-007):
        acik       — pencerede bekleyen bildirim VAR (bilanço riski)
        kapali     — takvim sağlıklı ve bu isimde bekleyen bildirim YOK
        bilinmiyor — takvim bayat/eksik ya da bu isim hiç eşleşmedi

    ⚠ `bilinmiyor` "risk yok" DEĞİLDİR. Bilanço tarihini bilmemek, bilanço
    olmadığı anlamına gelmez — tam tersine, en tehlikeli durum budur.
    """
    if saglik is not None and not saglik.get("ok", False):
        return {**BEKLENEN_YOK, "not": saglik.get("not") or "takvim güvenilmez"}
    rows = db.fetch_all(
        con,
        "SELECT subject, period, year, start_date, end_date "
        "  FROM expected_disclosures "
        " WHERE ticker = ? AND start_date <= ? AND end_date >= ? "
        " ORDER BY end_date, subject",
        (ticker.upper(), bitis, asof))
    if rows:
        return {"durum": "acik", "bildirimler": [dict(r) for r in rows],
                "not": (f"{len(rows)} bekleyen bildirim plan penceresine "
                        f"({asof} … {bitis}) düşüyor")}
    var = db.scalar(con, "SELECT COUNT(*) FROM expected_disclosures WHERE ticker = ?",
                    (ticker.upper(),))
    if var:
        return {"durum": "kapali", "bildirimler": [],
                "not": "takvimde var, plan penceresinde bekleyen bildirim yok"}

    # Takvimde HİÇ yok. İki sebebi olabilir ve bunlar aynı şey DEĞİL:
    #   (a) şirket raporunu ZATEN AÇIKLADI → uç onu listeden düşürür
    #   (b) ad eşleşmesi kurulamadı        → görmüyoruz
    # (a)'nın KANITI kendi verimizde: yakın tarihli bir `FR` bildirimi.
    # Doğrulandı 2026-08-07: AKBNK 07-28, GARAN 07-30 finansal rapor yayımladı
    # ve ikisi de beklenen-bildirim ucunda YOK. Yani kanıt varsa `kapali`
    # demek bir varsayım değil, bir gözlemdir.
    son_fr = db.scalar(
        con,
        "SELECT MAX(published_utc) FROM disclosures "
        " WHERE ticker = ? AND (category = 'FR' OR title LIKE '%Finansal Rapor%') "
        "   AND published_utc <= ?",
        (ticker.upper(), asof + "T23:59:59+00:00"))
    if son_fr:
        d_fr, d_asof = util.parse_date(son_fr[:10]), util.parse_date(asof)
        gun = (d_asof - d_fr).days if (d_fr and d_asof) else None
        if gun is not None and gun <= BEKLENEN_FR_KANIT_GUN:
            return {"durum": "kapali", "bildirimler": [],
                    "not": (f"takvimde yok; {son_fr[:10]} tarihli finansal rapor "
                            f"bildirimi var ({gun} gün önce) → dönemin raporunu "
                            "AÇIKLAMIŞ")}
    return {**BEKLENEN_YOK,
            "not": "bu isim takvimde hiç görünmüyor ve yakın tarihli finansal "
                   "rapor bildirimi de yok — açıkladı mı, ad eşleşmesi mi "
                   "kurulamadı, AYIRT EDİLEMİYOR"}
