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
