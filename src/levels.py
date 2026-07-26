"""Destek/direnç seviyeleri — fraktal pivot + ATR ölçekli kümeleme.

**LOOK-AHEAD KORUMASI BU DOSYANIN VARLIK ŞARTIDIR.** Bir fraktal pivot ancak
`k` bar SONRA bilinebilir: bugünün yüksek noktasının tepe olduğunu, sağındaki
k barın daha düşük kaldığını görmeden söyleyemezsin. `Pivot.confirm_idx` bunu
taşır ve `build_levels(asof_idx)` yalnız `confirm_idx <= asof_idx` olan
pivotları kullanır. Bu gecikmeye uyulmazsa seviyelere dayanan HER ölçüm
geçersizdir — ve geçersizliği fark edilmez, çünkü sonuçlar "çok iyi" çıkar.

⚠ Yeniden çerçeveleme notu (ADR #008): bu seviyeler **planlama geometrisidir**,
yön iddiası değil. Fiyatın nereye gideceğini söylemezler; girişin/stop'un/hedefin
nereye konacağını söylerler. `measure_level_edge()` ile yön üstünlükleri
ölçülebilir ve ölçüm sonucu raporun dilini belirler — tersi değil.

Ayrıca test edilmiş bir kural: **fiyat tüm zamanların zirvesindeyse ÜSTTE DİRENÇ
YOKTUR** — o bölgede hiç işlem geçmemiştir. Perakende teknik analizin sessizce
direnç uydurduğu yer tam olarak burasıdır.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from . import db, stats, util


@dataclass(frozen=True, slots=True)
class Pivot:
    idx: int
    date: str
    price: float
    kind: str           # 'tepe' | 'dip'
    confirm_idx: int    # bu pivot ancak BU bardan itibaren bilinebilir


@dataclass(frozen=True, slots=True)
class Level:
    price: float
    kind: str           # 'destek' | 'direnc'
    touches: int
    first_date: str
    last_date: str
    confirm_idx: int    # kümedeki EN GEÇ doğrulanan pivot


# ---------------------------------------------------------------- pivotlar
def find_pivots(high: np.ndarray, low: np.ndarray, dates: list[str],
                k: int = 5) -> list[Pivot]:
    """Fraktal pivotlar. `confirm_idx = idx + k` — k bar gecikmeyle bilinebilir."""
    out: list[Pivot] = []
    n = len(high)
    for i in range(k, n - k):
        pencere = slice(i - k, i + k + 1)
        if np.isfinite(high[i]) and high[i] == np.nanmax(high[pencere]):
            out.append(Pivot(i, dates[i], float(high[i]), "tepe", i + k))
        if np.isfinite(low[i]) and low[i] == np.nanmin(low[pencere]):
            out.append(Pivot(i, dates[i], float(low[i]), "dip", i + k))
    return out


def _cluster(pivots: list[Pivot], tolerans: float, min_dokunus: int) -> list[Level]:
    """Birbirine `tolerans` kadar yakın pivotları tek seviyeye toplar."""
    if not pivots:
        return []
    sirali = sorted(pivots, key=lambda p: p.price)
    kumeler: list[list[Pivot]] = [[sirali[0]]]
    for p in sirali[1:]:
        if abs(p.price - kumeler[-1][-1].price) <= tolerans:
            kumeler[-1].append(p)
        else:
            kumeler.append([p])

    out: list[Level] = []
    for kume in kumeler:
        if len(kume) < min_dokunus:
            continue
        tarihler = sorted(p.date for p in kume)
        tepe = sum(1 for p in kume if p.kind == "tepe")
        out.append(Level(
            price=round(float(np.mean([p.price for p in kume])), 4),
            kind="direnc" if tepe * 2 >= len(kume) else "destek",
            touches=len(kume),
            first_date=tarihler[0], last_date=tarihler[-1],
            confirm_idx=max(p.confirm_idx for p in kume),
        ))
    return sorted(out, key=lambda l: l.price)


def build_levels(bars: pd.DataFrame, cfg: dict, *, asof_idx: int | None = None,
                 atr: float | None = None) -> list[Level]:
    """`asof_idx` anında BİLİNEBİLİR seviyeler.

    asof_idx verilmezse son bar varsayılır. Kümeleme toleransı ATR ölçekli:
    volatil bir hissede 1 TL'lik ayrım anlamsız, sakin bir hissede anlamlıdır.
    """
    s = cfg["seviyeler"]
    n = len(bars)
    if n == 0:
        return []
    t = n - 1 if asof_idx is None else int(asof_idx)
    if t < 0:
        return []

    pencere = int(s["pencere_bar"])
    lo = max(0, t - pencere + 1)
    alt = bars.iloc[lo:t + 1]
    if len(alt) < 2 * int(s["pivot_k"]) + 1:
        return []

    piv = find_pivots(alt["h"].to_numpy(float), alt["l"].to_numpy(float),
                      alt["date"].tolist(), int(s["pivot_k"]))
    # LOOK-AHEAD KORUMASI — yerel indeks uzayında
    yerel_t = t - lo
    piv = [p for p in piv if p.confirm_idx <= yerel_t]
    if not piv:
        return []

    if atr is None or not np.isfinite(atr) or atr <= 0:
        atr = float(alt["c"].astype(float).pct_change().abs().median()
                    * alt["c"].iloc[-1]) or 1.0
    tolerans = float(s["kumeleme_atr_carpani"]) * float(atr)
    return _cluster(piv, tolerans, int(s["min_dokunus"]))


# ---------------------------------------------------------------- sorgular
def nearest_below(levels: list[Level], price: float) -> Level | None:
    alt = [l for l in levels if l.price < price]
    return max(alt, key=lambda l: l.price) if alt else None


def nearest_above(levels: list[Level], price: float) -> Level | None:
    ust = [l for l in levels if l.price > price]
    return min(ust, key=lambda l: l.price) if ust else None


def resistances_above(levels: list[Level], price: float, n: int = 3) -> list[Level]:
    """Fiyatın ÜSTÜNDEKİ seviyeler, yakından uzağa.

    Boş dönebilir ve bu NORMALDİR: fiyat tüm zamanların zirvesindeyse üstte
    direnç YOKTUR. Çağıran taraf boş listeyi "seviye bulunamadı" diye
    yorumlayıp uydurmamalı.
    """
    return sorted([l for l in levels if l.price > price],
                  key=lambda l: l.price)[:n]


def supports_below(levels: list[Level], price: float, n: int = 3) -> list[Level]:
    return sorted([l for l in levels if l.price < price],
                  key=lambda l: -l.price)[:n]


def at_all_time_high(bars: pd.DataFrame, asof_idx: int | None = None) -> bool:
    t = (len(bars) - 1) if asof_idx is None else asof_idx
    if t < 0 or len(bars) == 0:
        return False
    return float(bars["c"].iloc[t]) >= float(bars["h"].iloc[:t + 1].max()) - 1e-9


# ---------------------------------------------------------------- saklama
def store(cfg: dict, con: sqlite3.Connection, ticker: str, date: str,
          levels: list[Level]) -> int:
    return db.upsert_many(
        con, "levels_daily", ["ticker", "date", "set_version", "payload"],
        [(ticker, date, cfg["seviyeler"]["set_version"],
          util.json_dump([asdict(l) for l in levels], pretty=False))])


def load(cfg: dict, con: sqlite3.Connection, ticker: str, date: str) -> list[Level]:
    row = db.fetch_one(
        con, "SELECT payload FROM levels_daily WHERE ticker=? AND date=? AND set_version=?",
        (ticker, date, cfg["seviyeler"]["set_version"]))
    if not row:
        return []
    return [Level(**d) for d in json.loads(row["payload"])]


# ---------------------------------------------------------------- ölçüm
def measure_level_edge(cfg: dict, bars: pd.DataFrame, *, horizon: int,
                       yakinlik_atr: float = 0.5) -> dict:
    """Seviyeye yakınlığın YÖN ÜSTÜNLÜĞÜ var mı? Ölçüm raporun dilini belirler.

    Yöntem: her `yeniden_hesap_bar` barda seviyeler LOOK-AHEAD KORUMALI olarak
    yeniden kurulur; fiyat bir desteğe/dirence `yakinlik_atr × ATR` kadar
    yaklaştığı günler sinyal sayılır; ileri getiriler ÖRTÜŞMEYEN pencerelerle
    ve KOŞULSUZ TABANA göre karşılaştırılır.

    Not: `gold_tracking_system` aynı ölçümü altında yaptı ve **kenar
    bulamadı** (1 ay ufkunda −0.1p / +0.6p). Buradaki sonuç ne çıkarsa çıksın,
    seviyeler plan geometrisi olarak kullanılmaya devam eder — yön iddiası
    ancak ölçüm izin verirse yapılır.
    """
    o, s = cfg["olcum"], cfg["seviyeler"]
    n = len(bars)
    if n < 300:
        return {"destek": stats.dist_stats([]), "direnc": stats.dist_stats([]),
                "not": "yetersiz bar"}

    c = bars["c"].to_numpy(float)
    step = int(s["yeniden_hesap_bar"])
    atr_seri = (bars["h"].astype(float) - bars["l"].astype(float)) \
        .rolling(14, min_periods=14).mean().to_numpy()

    destek_idx: list[int] = []
    direnc_idx: list[int] = []
    seviyeler: list[Level] = []
    for t in range(260, n):
        if (t - 260) % step == 0 or not seviyeler:
            seviyeler = build_levels(bars, cfg, asof_idx=t, atr=atr_seri[t])
        if not seviyeler or not np.isfinite(atr_seri[t]):
            continue
        tol = yakinlik_atr * atr_seri[t]
        d = nearest_below(seviyeler, c[t])
        r = nearest_above(seviyeler, c[t])
        if d and abs(c[t] - d.price) <= tol:
            destek_idx.append(t)
        if r and abs(r.price - c[t]) <= tol:
            direnc_idx.append(t)

    tarihler = bars["date"].tolist()
    kw = dict(weak_n=int(o["zayif_n_esigi"]),
              min_diff_p=float(o["min_anlamli_fark_puan"]))
    return {
        "destek": stats.measure_edge(tarihler, c, destek_idx, horizon, **kw),
        "direnc": stats.measure_edge(tarihler, c, direnc_idx, horizon, **kw),
        "n_bar": n,
    }
