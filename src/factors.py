"""Faktör hesabı ve kesitsel skorlama.

3 faktör + 1 hipotez. Altı faktör YAZILMADI: 161 bağımsız gözlemde altı
serbestlik derecesi overfit demektir; ölçüm ~1,5 faktörün çalıştığını söylüyor.

**Kapılar skorlanmaz, ELER.** Bir şeye ağırlık vermek onu diğerleriyle takas
edilebilir yapar; kapı yapmak yapmaz. Örnek: SMA200 altındaki bir hisse
"momentumu çok güçlü" diye seçilememeli.

**Sektör nötralizasyonu VARSAYILAN KAPALI** — ölçüldü, kenarı düşürüyor
(6-1 momentumda t: 1.86 → 0.62). BIST'te sektör momentumu sinyalin kendisidir;
bankalar tek blok hareket eder ve "bankalar çalışıyor" gerçek bilgidir.
Sektör kontrolü skorlama katmanında değil, planlayıcıda KISIT olarak yaşar.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3

import numpy as np
import pandas as pd

from . import db, stats, util

log = logging.getLogger(__name__)

FACTOR_NAMES = ["mom_6_1", "mom_12_1", "high52_prox", "volscaled_mom"]

FACTOR_COLS = (
    ["ticker", "date", "set_version", "weights_hash"]
    + FACTOR_NAMES
    + [f"z_{f}" for f in FACTOR_NAMES]
    + ["score", "rank", "pct", "eligible", "gate_reasons"]
)


def weights_hash(cfg: dict) -> str:
    """Skoru üreten AYAR SETİNİN parmak izi.

    Ağırlık değiştiğinde geçmiş satırlar geçersiz olmaz — ÇATALLANIR. Yavaş
    döngü (ağırlık kalibrasyonu) bu sayede eski ölçümleri bozmadan çalışabilir.
    """
    f = cfg["faktorler"]
    imza = {
        "agirliklar": dict(sorted(f["agirliklar"].items())),
        "sektor_notr": bool(f["sektor_notr"]),
        "winsor": list(f["winsor_pct"]),
        "high52_min_ufuk": f["high52_min_ufuk_gun"],
        "set_version": f["set_version"],
    }
    return hashlib.sha1(util.json_dump(imza, canonical=True).encode()).hexdigest()[:12]


def effective_weights(cfg: dict, horizon_days: int | None = None) -> dict[str, float]:
    """Ufka göre düzeltilmiş ağırlıklar.

    `high52_prox` UFUK KAPILI: ölçüm H=42'de +2.06pp (t=2.04) veriyor ama
    H=15'te ~0. Kısa ufukta ağırlığı sıfırlanır — çalışmadığı yerde oy
    kullandırmak, ölçümü gürültüyle sulandırmaktır.
    """
    f = cfg["faktorler"]
    w = dict(f["agirliklar"])
    h = horizon_days if horizon_days is not None else cfg["planlayici"]["zaman_bariyeri_gun"]
    if h < int(f["high52_min_ufuk_gun"]):
        w["high52_prox"] = 0.0
    toplam = sum(abs(v) for v in w.values())
    return {k: (v / toplam if toplam else 0.0) for k, v in w.items()}


# ============================================================ ham faktörler
def _panel(con: sqlite3.Connection, cfg: dict, asof: str,
           tickers: list[str]) -> pd.DataFrame:
    """Bir gün için evrenin gösterge + fiyat paneli.

    `c_tr` bars_daily'den geliyor çünkü trend kapısı toplam getiri uzayında
    karşılaştırma yapar (`c_tr` vs `sma200_tr`) — `c` ile `sma200_tr`'yi
    karşılaştırmak birim hatasıdır.
    """
    if not tickers:
        return pd.DataFrame()
    ph = ",".join("?" * len(tickers))
    sql = f"""
        SELECT i.*, b.c, b.c_tr, b.v, b.turnover_try
          FROM indicator_daily i
          JOIN bars_daily b ON b.ticker = i.ticker AND b.date = i.date
         WHERE i.date = ? AND i.set_version = ? AND i.ticker IN ({ph})
    """
    params = [asof, cfg["gostergeler"]["set_version"], *[t.upper() for t in tickers]]
    return pd.read_sql_query(sql, con, params=params)


def raw_factors(panel: pd.DataFrame) -> pd.DataFrame:
    """Ham faktör değerleri (yüzde birimi).

    Momentumlar SON AYI DIŞLAR (`6-1`, `12-1`) — kısa vadeli tersine dönüş
    etkisini momentum sinyalinden ayırmak için standart uygulama. Ölçüm bunu
    destekliyor: saf 21 günlük getiri faktör olarak NEGATİF (−0.29pp, kazanma %43).

    Depolanan getirilerden türetim:
        c_tr[t-21]/c_tr[t-126] = (1 + ret_126) / (1 + ret_21)
    """
    out = panel[["ticker"]].copy()
    r21 = panel["ret_21"] / 100.0
    r126 = panel["ret_126"] / 100.0
    r252 = panel["ret_252"] / 100.0

    out["mom_6_1"] = ((1 + r126) / (1 + r21) - 1.0) * 100.0
    out["mom_12_1"] = ((1 + r252) / (1 + r21) - 1.0) * 100.0
    out["high52_prox"] = panel["dist_high52_pct"]          # ≤0: zirveye uzaklık
    vol = panel["vol_ann_63"].replace(0.0, np.nan)
    out["volscaled_mom"] = out["mom_6_1"] / vol
    return out


# ============================================================ kapılar
def eligibility_gates(row: pd.Series, kalite: dict | None, cfg: dict,
                      ex_date_in_window: bool = False) -> tuple[bool, list[str]]:
    """Skorlanmayan, ELEYEN kısıtlar. (uygun, [neden kodları]) döner."""
    f, ev = cfg["faktorler"], cfg["evren"]
    nedenler: list[str] = []

    tol = float(f["kapilar"]["sma200_tolerans"])
    c_tr, sma200_tr = row.get("c_tr"), row.get("sma200_tr")
    if pd.isna(c_tr) or pd.isna(sma200_tr):
        nedenler.append("sma200_yok")
    elif c_tr < sma200_tr * (1 - tol):
        nedenler.append("sma200_alti")

    ciro = row.get("turnover_med_63")
    if pd.isna(ciro):
        nedenler.append("likidite_bilinmiyor")
    elif ciro < float(ev["min_medyan_islem_hacmi_try"]):
        nedenler.append("likidite_zayif")

    if kalite is not None:
        if not kalite.get("ok", False):
            nedenler.append("veri_kalitesi")
        zv = kalite.get("zero_vol_ratio_252")
        if zv is not None and zv > float(ev["maks_sifir_hacim_orani"]):
            nedenler.append("sifir_hacim")

    if ex_date_in_window:
        nedenler.append("kurumsal_islem")

    for k in ("mom_6_1", "mom_12_1"):
        if k in row and pd.isna(row[k]):
            nedenler.append(f"{k}_yok")

    return (not nedenler), nedenler


# ============================================================ kesitsel skor
def cross_sectional_scores(raw: pd.DataFrame, uygunluk: dict[str, tuple],
                           cfg: dict, *, sector_map: dict[str, str] | None = None,
                           horizon_days: int | None = None) -> pd.DataFrame:
    """winsorize → z → [sektör nötr: VARSAYILAN KAPALI] → ağırlıklı toplam.

    ÖNEMLİ: z-skor TÜM evrende hesaplanır, sıralama YALNIZ uygun olanlar
    arasında yapılır. Uygun olmayanları z tabanından çıkarmak dağılımı kaydırır
    ve kalan isimlerin skorlarını, kendileri değişmediği halde değiştirir.
    """
    f = cfg["faktorler"]
    lo, hi = f["winsor_pct"]
    w = effective_weights(cfg, horizon_days)
    out = raw.copy()

    for ad in FACTOR_NAMES:
        z = stats.zscore(stats.winsorize(out[ad].to_numpy(dtype=float), lo, hi))
        if f["sektor_notr"] and sector_map:
            z = _sector_demean(z, out["ticker"].tolist(), sector_map)
        out[f"z_{ad}"] = z

    skor = np.zeros(len(out), dtype=float)
    agirlik_toplam = np.zeros(len(out), dtype=float)
    for ad, agirlik in w.items():
        if agirlik == 0:
            continue
        z = out[f"z_{ad}"].to_numpy(dtype=float)
        var = np.isfinite(z)
        skor = np.where(var, skor + agirlik * np.nan_to_num(z), skor)
        # MUTLAK ağırlık toplamı — bkz. backtest.score_at'teki aynı gerekçe.
        agirlik_toplam = np.where(var, agirlik_toplam + abs(agirlik), agirlik_toplam)
    # Eksik faktörü 0 saymak yerine PAYDADAN DÜŞ — "verisi gelmeyen gösterge
    # paydadan düşer" (gold ölçüm kültürü). Aksi halde eksik veri sessizce
    # nötr oy olur ve skoru sıfıra doğru çeker.
    out["score"] = np.where(agirlik_toplam > 0, skor / agirlik_toplam, np.nan)

    out["eligible"] = [uygunluk.get(t, (False, ["bilinmiyor"]))[0] for t in out["ticker"]]
    out["gate_reasons"] = [util.json_dump(uygunluk.get(t, (False, ["bilinmiyor"]))[1],
                                          pretty=False) for t in out["ticker"]]

    uyg = out["eligible"] & out["score"].notna()
    out["rank"] = np.nan
    out["pct"] = np.nan
    if uyg.any():
        alt = out.loc[uyg, "score"]
        siralama = alt.rank(ascending=False, method="min")
        out.loc[uyg, "rank"] = siralama
        n = len(alt)
        out.loc[uyg, "pct"] = (n - siralama) / max(n - 1, 1) * 100.0 if n > 1 else 100.0
    return out


def _sector_demean(z: np.ndarray, tickers: list[str],
                   sector_map: dict[str, str]) -> np.ndarray:
    out = z.copy()
    sektorler = pd.Series([sector_map.get(t, "?") for t in tickers])
    for s in sektorler.unique():
        m = (sektorler == s).to_numpy() & np.isfinite(out)
        if m.sum() >= 2:
            out[m] = out[m] - out[m].mean()
    return out


# ============================================================ boru hattı
def compute_for_date(cfg: dict, con: sqlite3.Connection, asof: str,
                     tickers: list[str], *, kalite: dict | None = None,
                     horizon_days: int | None = None) -> pd.DataFrame:
    """Tek gün için tam faktör tablosu (ham + z + skor + kapılar)."""
    from . import universe

    panel = _panel(con, cfg, asof, tickers)
    if panel.empty:
        return pd.DataFrame()

    raw = raw_factors(panel)
    birlesik = panel.merge(raw, on="ticker")

    kalite = kalite if kalite is not None else {}
    uygunluk = {}
    for _, r in birlesik.iterrows():
        uygunluk[r["ticker"]] = eligibility_gates(r, kalite.get(r["ticker"]), cfg)

    skor = cross_sectional_scores(
        raw, uygunluk, cfg,
        sector_map=universe.sector_map(con), horizon_days=horizon_days)
    skor["date"] = asof
    return skor


def store(cfg: dict, con: sqlite3.Connection, df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    sv, wh = cfg["faktorler"]["set_version"], weights_hash(cfg)
    rows = []
    for r in df.itertuples(index=False):
        rows.append((
            r.ticker, r.date, sv, wh,
            *(_n(getattr(r, a)) for a in FACTOR_NAMES),
            *(_n(getattr(r, f"z_{a}")) for a in FACTOR_NAMES),
            _n(r.score), _i(r.rank), _n(r.pct),
            1 if r.eligible else 0, r.gate_reasons))
    return db.upsert_many(con, "factor_daily", FACTOR_COLS, rows)


def _n(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(v) else v


def _i(x) -> int | None:
    v = _n(x)
    return None if v is None else int(v)
