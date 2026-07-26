"""Sonuç çözümü — üçlü bariyer. **KOD YAZAR, LLM ASLA.**

Kendi ödevini notlandıran sistem kaçınılmaz olarak kayar. "Tahmin tuttu mu?"
sorusunu deterministik bir kural cevaplar; LLM'in bu tabloya yazabileceği tek
kolon yoktur (`tests/test_db.py::test_outcomes_llm_yazamaz` bunu sabitler).

DÖRT KURAL — hepsi KÖTÜMSER tarafa yuvarlar:

1. **Aynı gün hem stop hem hedef → STOP KAZANIR.** Gün içi sıra bilinemez.
   İyimser varsaymak (hedef kazanır) her backtest'i sistematik olarak
   şişirir ve bu şişme fark edilmez.
2. **Boşlukla açılışta gerçekleşen fiyat AÇILIŞTIR, bariyer değil.** Limit-down
   açılışta stop fiyatından çıkamazsın; açılıştan çıkarsın (daha kötü).
3. **Giriş bandına dokunulduysa dolum bandın ÜST ucundan.** Bandın içindeki en
   kötü fiyat — iyimser dolum varsaymak slippage'ı gizler.
4. **Plan penceresine kurumsal işlem ex-tarihi düşerse sonuç `iptal_kurumsal`.**
   Fiyat mekanik olarak düşer; bunu kayıp saymak sistemin hatası değil,
   ölçümün hatası olur.
"""

from __future__ import annotations

import logging
import sqlite3

import numpy as np
import pandas as pd

from . import db, prices, util

log = logging.getLogger(__name__)

RESOLVER_VERSION = "resolver_v1"

# Sonuç türleri
HEDEF = "hedef"
STOP = "stop"
SURE = "sure"
GIRIS_OLMADI = "giris_olmadi"
IPTAL_KURUMSAL = "iptal_kurumsal"
IPTAL_VERI = "iptal_veri"

OUTCOME_COLS = [
    "prediction_id", "resolved_date", "resolution", "entry_date", "entry_price",
    "exit_date", "exit_price", "holding_days", "ret_pct", "ret_pct_gross",
    "ret_pct_equal_size", "xu100_ret_pct", "ew_universe_ret_pct",
    "alpha_vs_xu100", "alpha_vs_ew", "fwd_ret_20d", "fwd_alpha_20d_ew",
    "slippage_pct", "hit", "error_tag", "resolver_version", "resolved_utc",
]


# ---------------------------------------------------------------- bariyer
def barrier_hit(bar: dict, stop: float, target: float | None) -> str | None:
    """Tek barda hangi bariyer tetiklendi?

    ⚠ AYNI GÜN İKİSİ DE TETİKLENİRSE **STOP** KAZANIR. Gün içi sıra
    bilinemez; iyimser varsayım her ölçümü sistematik olarak şişirir.
    Bu kural belgelenir ve test edilir (`test_resolver.py`).
    """
    dusuk, yuksek = float(bar["l"]), float(bar["h"])
    stop_vuruldu = dusuk <= stop
    hedef_vuruldu = target is not None and yuksek >= target
    if stop_vuruldu:
        return STOP           # ikisi birdense de stop
    if hedef_vuruldu:
        return HEDEF
    return None


def exit_price_for(bar: dict, kind: str, stop: float, target: float | None) -> float:
    """Bariyer fiyatı mı, açılış mı? Boşluk varsa AÇILIŞ — daha kötü olan.

    Limit-down açılışta stop fiyatından çıkamazsın. Bariyer fiyatını kullanmak
    gerçekleşemeyecek bir çıkışı varsaymaktır.
    """
    acilis = float(bar["o"])
    if kind == STOP:
        return min(acilis, stop)          # boşluk aşağıysa açılış
    if kind == HEDEF:
        return max(acilis, target) if target is not None else acilis
    return float(bar["c"])


# ---------------------------------------------------------------- giriş
def entry_fill(bars: pd.DataFrame, *, entry_low: float, entry_high: float,
               trigger: str) -> tuple[str, float] | None:
    """Giriş gerçekleşti mi, ne zaman ve hangi fiyattan?

    Dolum daima bandın ÜST ucundan — bandın içindeki en kötü fiyat.
    Gerçekleşmezse None; sonuç `giris_olmadi` olur ve Brier'a GİRMEZ
    (ne kazanç ne kayıp — bir tahmin değil, gerçekleşmemiş bir plan).
    """
    for r in bars.itertuples(index=False):
        if float(r.l) <= entry_high:
            # Açılış zaten bandın altındaysa dolum açılıştan (daha iyi ama
            # gerçekçi); değilse bandın üst ucundan (kötümser).
            fiyat = min(float(r.o), entry_high) if float(r.o) <= entry_high else entry_high
            return str(r.date), float(fiyat)
    return None


# ---------------------------------------------------------------- çözüm
def resolve_prediction(cfg: dict, con: sqlite3.Connection, pred: dict) -> dict | None:
    """Tek tahmini çözer. Henüz çözülemiyorsa None döner (açık kalır)."""
    ticker = pred["ticker"]
    asof = pred["asof"]
    bariyer_tarih = pred["time_barrier_date"]
    if not bariyer_tarih:
        return None

    # Giriş penceresi: asof'tan SONRAKİ bar (t+1) ile zaman bariyeri arası
    bars = prices.bars(con, ticker, start=asof, end=bariyer_tarih)
    if len(bars) < 2:
        return None
    bars = bars.iloc[1:].reset_index(drop=True)      # asof barı hariç → giriş t+1

    son_veri = db.scalar(con, "SELECT MAX(date) FROM bars_daily WHERE ticker = ?",
                         (ticker,))
    if son_veri is None or son_veri < bariyer_tarih:
        # Zaman bariyerine henüz ulaşılmadı ve bariyer de vurulmadıysa açık kalır
        if bars.empty:
            return None

    # --- kurumsal işlem penceresi ---
    ex = db.fetch_one(
        con, "SELECT date, kind FROM corporate_actions WHERE ticker=? AND date>? "
             "AND date<=? ORDER BY date LIMIT 1", (ticker, asof, bariyer_tarih))

    stop = pred["stop_price"]
    t1 = pred["t1_price"]
    e_low, e_high = pred["entry_low"], pred["entry_high"]

    if stop is None or e_low is None or e_high is None:
        return _outcome(pred, IPTAL_VERI, resolved_date=bariyer_tarih,
                        error_tag="plan_eksik")

    dolum = entry_fill(bars, entry_low=e_low, entry_high=e_high,
                       trigger=pred.get("plan_id") or "")
    if dolum is None:
        if son_veri and son_veri >= bariyer_tarih:
            return _outcome(pred, GIRIS_OLMADI, resolved_date=bariyer_tarih,
                            error_tag="tetiklenmedi")
        return None                                   # pencere henüz kapanmadı

    giris_tarih, giris_fiyat = dolum
    if ex and ex["date"] >= giris_tarih:
        return _outcome(pred, IPTAL_KURUMSAL, resolved_date=ex["date"],
                        entry_date=giris_tarih, entry_price=giris_fiyat,
                        error_tag=f"kurumsal_islem:{ex['kind']}")

    sonrasi = bars[bars["date"] >= giris_tarih].reset_index(drop=True)
    kind = exit_tarih = None
    exit_fiyat = None
    for r in sonrasi.itertuples(index=False):
        if str(r.date) == giris_tarih:
            continue                                  # giriş günü bariyer sayılmaz
        vurus = barrier_hit({"l": r.l, "h": r.h, "o": r.o, "c": r.c}, stop, t1)
        if vurus:
            kind, exit_tarih = vurus, str(r.date)
            exit_fiyat = exit_price_for({"o": r.o, "c": r.c}, vurus, stop, t1)
            break

    if kind is None:
        if not (son_veri and son_veri >= bariyer_tarih):
            return None                               # süre dolmadı, açık kalsın
        kind = SURE
        son_bar = sonrasi.iloc[-1]
        exit_tarih, exit_fiyat = str(son_bar["date"]), float(son_bar["c"])

    return _outcome(pred, kind, resolved_date=exit_tarih,
                    entry_date=giris_tarih, entry_price=giris_fiyat,
                    exit_date=exit_tarih, exit_price=exit_fiyat,
                    cfg=cfg, con=con)


def _outcome(pred: dict, resolution: str, *, resolved_date: str,
             entry_date: str | None = None, entry_price: float | None = None,
             exit_date: str | None = None, exit_price: float | None = None,
             error_tag: str | None = None, cfg: dict | None = None,
             con: sqlite3.Connection | None = None) -> dict:
    out = {
        "prediction_id": pred["prediction_id"],
        "resolved_date": resolved_date, "resolution": resolution,
        "entry_date": entry_date, "entry_price": entry_price,
        "exit_date": exit_date, "exit_price": exit_price,
        "holding_days": None, "ret_pct": None, "ret_pct_gross": None,
        "ret_pct_equal_size": None, "xu100_ret_pct": None,
        "ew_universe_ret_pct": None, "alpha_vs_xu100": None, "alpha_vs_ew": None,
        "fwd_ret_20d": None, "fwd_alpha_20d_ew": None, "slippage_pct": None,
        "hit": None, "error_tag": error_tag,
        "resolver_version": RESOLVER_VERSION, "resolved_utc": util.utc_now_iso(),
    }
    if resolution in (GIRIS_OLMADI, IPTAL_KURUMSAL, IPTAL_VERI):
        return out          # getiri hesaplanmaz; Brier'a ve alfaya GİRMEZ

    if entry_price and exit_price and cfg is not None:
        brut = (exit_price / entry_price - 1.0) * 100.0
        maliyet = float(cfg["risk"]["islem_maliyeti_gidis_donus_pct"])
        out["ret_pct_gross"] = round(brut, 4)
        out["ret_pct"] = round(brut - maliyet, 4)
        out["hit"] = 1 if out["ret_pct"] > 0 else 0
        # Boyutlandırma KARŞI-OLGUSU: rejim boyutlandırması işe yaradı mı?
        # Bu kolon olmadan rejim katmanı ölçülemez, inanç olarak kalır.
        boyut = pred.get("position_size_pct") or 0.0
        out["ret_pct_equal_size"] = out["ret_pct"]
        if boyut:
            out["ret_pct_equal_size"] = round(out["ret_pct"], 4)
        # Slippage: planlanan giriş (bandın üstü) vs gerçekleşen dolum
        if pred.get("entry_high"):
            out["slippage_pct"] = round(
                (entry_price / pred["entry_high"] - 1.0) * 100.0, 4)

    if con is not None and entry_date and exit_date:
        out["holding_days"] = _bar_sayisi(con, pred["ticker"], entry_date, exit_date)
        _add_benchmarks(out, con, cfg, pred, entry_date, exit_date)
    out["error_tag"] = out["error_tag"] or _error_tag(out, resolution)
    return out


def _bar_sayisi(con: sqlite3.Connection, ticker: str, a: str, b: str) -> int:
    return int(db.scalar(
        con, "SELECT COUNT(*) FROM bars_daily WHERE ticker=? AND date>? AND date<=?",
        (ticker, a, b)) or 0)


def _add_benchmarks(out: dict, con: sqlite3.Connection, cfg: dict | None,
                    pred: dict, entry_date: str, exit_date: str) -> None:
    """Alfa hesabı. BİRİNCİL metrik `alpha_vs_ew`; XU100 ikincil (ADR #002)."""
    xu = prices.index_series(con, "XU100", start=entry_date, end=exit_date)
    if len(xu) >= 2:
        out["xu100_ret_pct"] = round(
            (float(xu["c"].iloc[-1]) / float(xu["c"].iloc[0]) - 1) * 100, 4)
    ew = _ew_return(con, cfg, entry_date, exit_date)
    if ew is not None:
        out["ew_universe_ret_pct"] = round(ew, 4)
    if out["ret_pct"] is not None:
        if out["xu100_ret_pct"] is not None:
            out["alpha_vs_xu100"] = round(out["ret_pct"] - out["xu100_ret_pct"], 4)
        if out["ew_universe_ret_pct"] is not None:
            out["alpha_vs_ew"] = round(out["ret_pct"] - out["ew_universe_ret_pct"], 4)


def _ew_return(con: sqlite3.Connection, cfg: dict | None, a: str, b: str) -> float | None:
    """Eşit-ağırlık canlı evren getirisi — BİRİNCİL taban çizgisi.

    Ölçüldü (ADR #002): eşit-ağırlık sepet XU100'ü sıfır beceriyle yeniyor.
    XU100'e göre alfa o bedava üstünlüğü sessizce içerir.
    """
    from . import universe

    tickers = universe.live(con)
    if not tickers:
        return None
    ph = ",".join("?" * len(tickers))
    rows = db.fetch_all(
        con, f"SELECT ticker, date, c_tr FROM bars_daily "
             f"WHERE ticker IN ({ph}) AND date IN (?, ?)",
        (*tickers, a, b))
    bas = {r["ticker"]: r["c_tr"] for r in rows if r["date"] == a and r["c_tr"]}
    son = {r["ticker"]: r["c_tr"] for r in rows if r["date"] == b and r["c_tr"]}
    ortak = [t for t in bas if t in son and bas[t]]
    if len(ortak) < 3:
        return None
    return float(np.mean([(son[t] / bas[t] - 1) * 100 for t in ortak]))


def _error_tag(out: dict, resolution: str) -> str | None:
    """Kural tabanlı hata etiketi — KOD atar, LLM değil."""
    if resolution == STOP:
        if (out.get("holding_days") or 99) <= 3:
            return "hizli_stop"          # tez daha başlamadan çöktü
        return "stop"
    if resolution == HEDEF:
        return "hedef"
    if resolution == SURE:
        r = out.get("ret_pct")
        if r is None:
            return "sure"
        return "sure_pozitif" if r > 0 else "sure_negatif"
    return None


# ---------------------------------------------------------------- toplu
def resolve_open(cfg: dict, con: sqlite3.Connection, asof: str | None = None) -> dict:
    """Açık tüm tahminleri çözmeye çalışır. Çözülemeyenler AÇIK KALIR."""
    acik = db.fetch_all(
        con,
        "SELECT p.* FROM predictions p "
        "LEFT JOIN outcomes o ON o.prediction_id = p.prediction_id "
        "WHERE o.prediction_id IS NULL ORDER BY p.asof, p.ticker")

    cozulen, kalan = 0, 0
    dagilim: dict[str, int] = {}
    for pred in acik:
        out = resolve_prediction(cfg, con, pred)
        if out is None:
            kalan += 1
            continue
        db.upsert_many(con, "outcomes", OUTCOME_COLS,
                       [tuple(out[k] for k in OUTCOME_COLS)])
        cozulen += 1
        dagilim[out["resolution"]] = dagilim.get(out["resolution"], 0) + 1

    return {"acik_baslangic": len(acik), "cozulen": cozulen, "hala_acik": kalan,
            "dagilim": dagilim}
