"""Fiyat verisi: backfill / günlük güncelleme / kurumsal işlem / kalite kapısı.

Kalite kapısı bu projenin en yüksek getirili küçük parçası. Ölçüm (2026-07-26)
gösterdi ki yfinance'in BIST kusurları GENEL değil KAYIT BAZLI:
    SASA.IS : 505 barın 117'sinde hacim SIFIR (%23.2)
    THYAO / EKGYO / ASTOR : %0.6
Yani "yfinance BIST'te bozuk mu?" yanlış soru; doğru soru "bu ticker'ın bu
verisi kullanılabilir mi?". Kapı bunu her ticker için ayrı cevaplar.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import db, util
from .sources import yf

log = logging.getLogger(__name__)

BAR_COLS = ["ticker", "date", "o", "h", "l", "c", "v", "c_tr",
            "turnover_try", "source", "ingested_utc"]


# ---------------------------------------------------------------- yazma
def _store_bars(con: sqlite3.Connection, ticker: str, df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    now = util.utc_now_iso()
    rows = [
        (ticker, r.date, _f(r.o), _f(r.h), _f(r.l), _f(r.c), _f(r.v), _f(r.c_tr),
         (_f(r.c) or 0.0) * (_f(r.v) or 0.0), "yfinance", now)
        for r in df.itertuples(index=False)
    ]
    return db.upsert_many(con, "bars_daily", BAR_COLS, rows)


def _f(x) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if v != v else v          # NaN → None


def purge_phantom_bars(cfg: dict, con: sqlite3.Connection) -> dict:
    """Yahoo'nun BIST TATİLLERİNDE ürettiği HAYALET barları siler.

    ÖLÇÜLDÜ (2026-07-26, 19 ticker × ~2946 bar): Yahoo, borsanın kapalı olduğu
    günlerde de bar döndürüyor — hacim 0 ve o=h=l=c=önceki kapanış. Örnek,
    Kurban Bayramı 2026-05-27/28/29 (holidays_tr.yaml'de tam gün tatil):

        2026-05-26  o 297.50  h 298.00  l 295.25  c 296.75  v 11.744.557
        2026-05-27  o 296.75  h 296.75  l 296.75  c 296.75  v 0      ← hayalet
        2026-05-28  o 296.75  h 296.75  l 296.75  c 296.75  v 0      ← hayalet
        2026-05-29  o 296.75  h 296.75  l 296.75  c 296.75  v 0      ← hayalet

    Zararı sessiz ve büyük: ATR bastırılır, volatilite olduğundan düşük ölçülür,
    zaman bariyeri 4 güne kadar kayar, RSI/ADX bozulur.

    AYIKLAMA ÖLÇÜTÜ — üç koşulun birleşimi, tek tek hiçbiri yeterli değil:
        (1) o=h=l=c  ve  (2) v=0  ve  (3) o gün ENDEKSİN barı yok
    Ölçüm bu birleşimin kesinliğini doğruluyor:
        841 hayalet bar  → silindi   (tamamı gerçekten tatil günü)
        142 bar          → KORUNDU: endeksin kendi boşluğu, hisse barı gerçek
         63 bar          → KORUNDU: gerçek seans gününde düz+sıfır hacim
                                    (ASELS 13, KCHOL 15 — muhtemelen işlem durdurma)
    Yalnız (3) kullanılsaydı 142 gerçek bar; yalnız (1)+(2) kullanılsaydı 63
    gerçek bar silinirdi.

    Endeksin son barından SONRAKİ tarihlere dokunulmaz — endeks bir gün gecikebilir
    ve o penceredeki hisse barları gerçektir (doğrulandı: THYAO 2026-07-24,
    hacim 23,4mn, gerçek OHLC aralığı).
    """
    sym = cfg["takvim"]["turet_kaynak_endeks"]
    son = db.scalar(con, "SELECT MAX(date) FROM index_daily WHERE symbol = ?", (sym,))
    if not son:
        log.warning("Endeks (%s) verisi yok — hayalet bar ayıklaması ATLANDI", sym)
        return {"silinen": 0, "sinir": None, "atlandi": True}

    cur = con.execute(
        "DELETE FROM bars_daily "
        " WHERE date <= ? AND v = 0 AND o = c AND h = c AND l = c "
        "   AND date NOT IN (SELECT date FROM index_daily WHERE symbol = ?)",
        (son, sym))
    con.commit()
    n = cur.rowcount or 0
    if n:
        log.info("hayalet bar ayıklandı: %d satır (sınır %s)", n, son)
    return {"silinen": n, "sinir": son, "atlandi": False}


def backfill(cfg: dict, con: sqlite3.Connection,
             tickers: list[str] | None = None, start: str | None = None) -> dict:
    """Tam geçmişi çeker. Uzun sürer; günlük boru hattında ÇAĞRILMAZ."""
    from . import universe

    tickers = tickers or universe.all_tickers(con)
    start = start or cfg["sources"]["yf"]["backfill_start"]
    sonuc: dict[str, int] = {}
    for t in tickers:
        df = yf.fetch_bars(t, cfg, start=start)
        sonuc[t] = _store_bars(con, t, df)
        log.info("backfill %s: %d bar", t, sonuc[t])
    # Ayıklama boru hattının PARÇASI — elle çalıştırılan adım bırakılmaz (L-002).
    temiz = purge_phantom_bars(cfg, con)
    return {"tickers": len(tickers), "bars": sonuc, "hayalet_silinen": temiz["silinen"]}


def daily(cfg: dict, con: sqlite3.Connection,
          tickers: list[str] | None = None, gun: int = 15) -> dict:
    """Son N takvim gününü çeker ve üzerine yazar.

    Neden sadece "son bar" değil: yfinance geçmiş barları düzeltebilir (temettü
    ex-tarihinde geriye dönük Adj Close değişir). Kayan pencere bu düzeltmeleri
    yakalar; tek bar çekmek eski satırları bayat bırakırdı.
    """
    from . import universe

    tickers = tickers or universe.all_tickers(con)
    start = (date.today() - timedelta(days=gun)).isoformat()
    sonuc: dict[str, int] = {}
    for t in tickers:
        sonuc[t] = _store_bars(con, t, yf.fetch_bars(t, cfg, start=start))
    temiz = purge_phantom_bars(cfg, con)
    # Kalite kapısı boru hattının PARÇASI — elle çalıştırılan adım bırakılmaz.
    # LESSONS L-002: "bir kere elle çalıştırdım, gerisi otomatik" varsayımı
    # yanlıştır; bağlı olmayan script donar ve hiçbir hata fırlatmaz. Burada
    # donması, kalite kapısının sessizce kapanması demekti (bkz. quality_map).
    kalite = assess_quality(cfg, con, tickers=tickers)
    return {"tickers": len(tickers), "bars": sonuc, "start": start,
            "hayalet_silinen": temiz["silinen"],
            "kalite_degerlendirilen": len(kalite),
            "kalite_gecmeyen": sum(1 for r in kalite if not r["ok"])}


def sync_indices(cfg: dict, con: sqlite3.Connection, start: str | None = None) -> dict:
    """Endeks ve kur barları. XU100 ayrıca İŞLEM TAKVİMİNİN kaynağıdır."""
    from . import universe

    start = start or cfg["sources"]["yf"]["backfill_start"]
    now = util.utc_now_iso()
    sonuc: dict[str, int] = {}
    for ad, sym in universe.index_symbols(cfg).items():
        df = yf.fetch_index(sym, cfg, start=start)
        rows = [(ad, r.date, _f(r.o), _f(r.h), _f(r.l), _f(r.c), now)
                for r in df.itertuples(index=False)]
        sonuc[ad] = db.upsert_many(
            con, "index_daily", ["symbol", "date", "o", "h", "l", "c", "ingested_utc"], rows)
        log.info("endeks %s (%s): %d bar", ad, sym, sonuc[ad])
    return sonuc


def sync_actions(cfg: dict, con: sqlite3.Connection,
                 tickers: list[str] | None = None) -> dict:
    """Temettü/bölünme kayıtları.

    yfinance bunları fiyata zaten uyguluyor; biz AYRICA saklıyoruz çünkü plan
    penceresine düşen bir ex-tarih stop'u yapay tetikler → o planın sonucu
    'iptal_kurumsal' olmalı, kayıp olarak sayılmamalı.
    """
    from . import universe

    tickers = tickers or universe.all_tickers(con)
    toplam = 0
    for t in tickers:
        acts = yf.fetch_actions(t, cfg)
        rows = [(t, a["date"], a["kind"], a["value"], "yfinance") for a in acts]
        toplam += db.upsert_many(
            con, "corporate_actions", ["ticker", "date", "kind", "value", "source"], rows)
    return {"tickers": len(tickers), "kayit": toplam}


# ---------------------------------------------------------------- okuma
def bars(con: sqlite3.Connection, ticker: str, *, start: str | None = None,
         end: str | None = None, limit: int | None = None) -> pd.DataFrame:
    """Bir hissenin barları, tarihe göre sıralı DataFrame."""
    sql = "SELECT date,o,h,l,c,v,c_tr,turnover_try FROM bars_daily WHERE ticker = ?"
    params: list = [ticker.upper()]
    if start:
        sql += " AND date >= ?"; params.append(start)
    if end:
        sql += " AND date <= ?"; params.append(end)
    sql += " ORDER BY date"
    df = pd.read_sql_query(sql, con, params=params)
    return df.tail(limit).reset_index(drop=True) if limit else df


def index_series(con: sqlite3.Connection, symbol: str, *, start: str | None = None,
                 end: str | None = None) -> pd.DataFrame:
    sql = "SELECT date,o,h,l,c FROM index_daily WHERE symbol = ?"
    params: list = [symbol]
    if start:
        sql += " AND date >= ?"; params.append(start)
    if end:
        sql += " AND date <= ?"; params.append(end)
    return pd.read_sql_query(sql + " ORDER BY date", con, params=params)


def action_dates(con: sqlite3.Connection, ticker: str) -> set[str]:
    return {r["date"] for r in db.fetch_all(
        con, "SELECT date FROM corporate_actions WHERE ticker = ?", (ticker.upper(),))}


# ---------------------------------------------------------------- kalite kapısı
def assess_quality(cfg: dict, con: sqlite3.Connection, asof: str | None = None,
                   tickers: list[str] | None = None,
                   store: bool = True) -> list[dict]:
    """Ticker bazlı veri kalitesi. Sonuçları döner; `store` ise tabloya yazar.

    `store=False`: yalnız ÖLÇ, yazma. Salt-okunur bir bağlantıyla (ör. gerçek
    veri testleri) kapının hâlâ çalıştığını doğrulamak için gerekli — aksi
    halde `pytest` koşmak kullanıcının `data_quality` tablosunu sessizce
    değiştiriyordu (2026-07-27 denetimi).
    """
    from . import universe

    ev = cfg["evren"]
    tickers = tickers or universe.all_tickers(con)
    asof = asof or (db.scalar(con, "SELECT MAX(date) FROM bars_daily") or
                    date.today().isoformat())

    sonuc = []
    for t in tickers:
        df = bars(con, t, end=asof).tail(252).reset_index(drop=True)
        r = _quality_row(t, df, action_dates(con, t), ev)
        r["date"] = asof
        sonuc.append(r)

    if store:
        db.upsert_many(
            con, "data_quality",
            ["ticker", "date", "bars_252", "zero_vol_ratio_252", "max_gap_days",
             "stale_close_days", "unexplained_jump", "ok", "reasons"],
            [(r["ticker"], r["date"], r["bars_252"], r["zero_vol_ratio_252"],
              r["max_gap_days"], r["stale_close_days"], r["unexplained_jump"],
              1 if r["ok"] else 0, util.json_dump(r["reasons"], pretty=False))
             for r in sonuc])
    return sonuc


def _quality_row(ticker: str, df: pd.DataFrame, act_dates: set[str], ev: dict) -> dict:
    reasons: list[str] = []
    if df.empty:
        return {"ticker": ticker, "bars_252": 0, "zero_vol_ratio_252": None,
                "max_gap_days": None, "stale_close_days": None,
                "unexplained_jump": None, "ok": False, "reasons": ["veri yok"]}

    c = df["c"].astype(float)
    v = df["v"].astype(float).fillna(0.0)
    d = pd.to_datetime(df["date"])

    zero_ratio = float((v == 0).mean())
    max_gap = int(d.diff().dt.days.max()) if len(d) > 1 else 0
    stale = int(_max_run(c.diff().fillna(1.0) == 0))

    ret = c.pct_change()
    esik = ev["aciklanamayan_sicrama_pct"] / 100.0
    buyuk = df.loc[ret.abs() > esik, "date"].tolist()
    unexplained = sum(1 for dt in buyuk if dt not in act_dates)

    if len(df) < 60:
        reasons.append(f"yetersiz bar ({len(df)})")
    if zero_ratio > ev["maks_sifir_hacim_orani"]:
        reasons.append(f"sıfır hacim %{zero_ratio*100:.1f} > "
                       f"%{ev['maks_sifir_hacim_orani']*100:.0f}")
    if max_gap > ev["maks_bar_bosluk_gun"]:
        reasons.append(f"bar boşluğu {max_gap}g > {ev['maks_bar_bosluk_gun']}g")
    if stale > ev["maks_bayat_kapanis_gun"]:
        reasons.append(f"bayat kapanış {stale}g > {ev['maks_bayat_kapanis_gun']}g")
    if unexplained:
        reasons.append(f"{unexplained} açıklanamayan sıçrama "
                       f"(|getiri|>%{ev['aciklanamayan_sicrama_pct']:.0f}, kurumsal işlem yok)")

    return {"ticker": ticker, "bars_252": int(len(df)),
            "zero_vol_ratio_252": zero_ratio, "max_gap_days": max_gap,
            "stale_close_days": stale, "unexplained_jump": int(unexplained),
            "ok": not reasons, "reasons": reasons}


def _max_run(mask: pd.Series) -> int:
    """Bir boolean serideki en uzun ardışık True dizisi."""
    best = cur = 0
    for x in mask:
        cur = cur + 1 if x else 0
        best = max(best, cur)
    return best


KALITE_YOK = {"ok": False, "uyarilar": ["kalite değerlendirilmedi"],
              "reasons": ["kalite_degerlendirilmedi"], "degerlendirildi": False}


def quality_map(con: sqlite3.Connection, asof: str) -> dict[str, dict]:
    """{ticker: `asof`'a kadarki EN SON kalite kaydı}.

    ⚠ İlk sürüm `WHERE date = ?` ile TAM EŞLEŞME arıyordu. `assess_quality`
    yalnız `bist veri kalite` ile koştuğu ve `bist veri gunluk` onu çağırmadığı
    için, fiyat verisi bir gün ilerlediğinde bu sorgu BOŞ dönüyordu — ve dört
    tüketicinin dördü de "kayıt yok"u "sorun yok" diye okuyordu (planner kapıyı
    atlıyor, paket `ok: true` yazıyor, HF-16 ateşlenmiyor, `eligibility_gates`
    tüm kalite bloğunu geçiyordu). Yani kapı, fark edilmeden kapanıyordu.
    Ölçüldü (2026-07-27): `quality_map('2026-07-27')` → 0 kayıt.

    Artık `date <= asof` içindeki en son değerlendirme kullanılır ve kaydın
    YAŞI (`yas_gun`) taşınır; çağıran taraf bayatlığı görebilir.
    """
    rows = db.fetch_all(
        con,
        "SELECT q.* FROM data_quality q "
        " JOIN (SELECT ticker, MAX(date) d FROM data_quality "
        "        WHERE date <= ? GROUP BY ticker) s "
        "   ON s.ticker = q.ticker AND s.d = q.date",
        (asof,))
    d_asof = util.parse_date(asof)
    out = {}
    for r in rows:
        d_q = util.parse_date(r["date"])
        out[r["ticker"]] = {
            **r, "ok": bool(r["ok"]), "reasons": _loads(r["reasons"]),
            "degerlendirildi": True,
            "yas_gun": (d_asof - d_q).days if (d_asof and d_q) else None,
        }
    return out


def quality_for(kalite: dict[str, dict], ticker: str) -> dict:
    """Pakete/rapora giren kalite görünümü. **Eksik kayıt "OK" DEĞİLDİR.**

    Projenin kuralı: "verisi gelmeyen gösterge paydadan düşer — uydurma
    yapılmaz". Bilinmeyen bir kaliteyi `ok: true` diye sunmak tam olarak
    uydurmaktır ve SASA vakasının (505 barın %23.2'sinde sıfır hacim) plana
    girmesine izin verirdi.
    """
    r = kalite.get(ticker)
    if not r:
        return dict(KALITE_YOK)
    return {"ok": bool(r["ok"]), "uyarilar": list(r.get("reasons") or []),
            "degerlendirildi": True, "yas_gun": r.get("yas_gun")}


def _loads(s) -> list:
    import json
    if isinstance(s, str) and s:
        try:
            return json.loads(s)
        except ValueError:
            return []
    return []
