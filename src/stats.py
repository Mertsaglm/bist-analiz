"""Ölçüm çekirdeği — bu projenin epistemolojisi bu dosyada.

Üç kural, üçü de pahalı deneyimden geliyor:

1. **Bilgi mutlak değerde değil, KOŞULSUZ TABANDAN FARKTA.**
   "Sinyal verdiğinde ortalama %+3 getiri" hiçbir şey söylemez; taban da
   %+3 olabilir. Ölçülen daima farktır.

2. **Örtüşmeyen pencere.** Örtüşen pencereler N'i şişirir ve kazanma oranını
   abartır; gözlemler bağımsız değildir. Bir pencere kullanıldıysa sonraki
   giriş en az `horizon` gün ileriden seçilir.

3. **ZAYIF N, BÜYÜK FARKI EZER.** `edge_verdict`'in bütün varlık sebebi budur.
   Verilebilecek EN GÜÇLÜ hüküm "zayıf kanıt"tır — "doğrulandı" dalı YOKTUR.

Ayrıca `required_n()`: "ne zaman bilebiliriz?" sorusu bir his değil, basılmış
bir sayıdır. Bu projede getiri kenarı için o sayı yüzlerce dönem, yani yıllar.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

HUKUM_OLCUM_YOK = "ölçüm yok"
HUKUM_YETERSIZ = "ölçüm yetersiz"
HUKUM_KENAR_YOK = "kenar yok"
HUKUM_ZAYIF_KANIT = "zayıf kanıt"


# ============================================================ hüküm
def edge_verdict(diff_p: float | None, n: int, weak_n: int, min_diff_p: float) -> str:
    """Taban çizgisine göre ölçülen farkın hükmü.

    ZAYIF N, BÜYÜK FARKI EZER — bu fonksiyonun bütün amacı budur. N=3 ile
    +5.0 puanlık fark "kanıt" değildir, gürültüdür.

    Bilerek YOK: "doğrulandı" dalı. En güçlü ifade "zayıf kanıt"tır.
    Bu bir eksiklik değil, tasarım kararıdır — sistemin kendi hakkında
    abartılı konuşmasını yapısal olarak imkânsız kılar.
    """
    if diff_p is None or n <= 0 or (isinstance(diff_p, float) and math.isnan(diff_p)):
        return HUKUM_OLCUM_YOK
    if n < weak_n:
        return f"{HUKUM_YETERSIZ} (N={n})"
    if abs(diff_p) < min_diff_p:
        return HUKUM_KENAR_YOK
    return f"{HUKUM_ZAYIF_KANIT}: {diff_p:+.1f}p"


def bonferroni_note(n_tests: int) -> str:
    """Çoklu test uyarısı — 30+ karşılaştırmada biri şansa bağlı iyi görünür."""
    return (f"{n_tests} karşılaştırma yapıldı; en iyi görünen sonucun şansa bağlı "
            f"olma olasılığı yüksektir. Tek tek 'en iyi' satıra bakma.")


def required_n(mean: float | None, sd: float | None, t_target: float = 2.0) -> int | None:
    """t=t_target'a ulaşmak için gereken bağımsız gözlem sayısı.

        n = (t_target × sd / |ort|)²

    Bu projenin en dürüst sayısı. Ölçüm (2026-07-26): en iyi faktörde H=15'te
    ort=+0.72pp, sd=5.00 → n ≈ 193 dönem ≈ 11,5 yıl. Yani canlı günlük getiri
    kenarını ASLA kanıtlamayacak. Bunu bilmek, bilmemekten iyidir.
    """
    if mean is None or sd is None or mean == 0 or sd <= 0:
        return None
    if math.isnan(mean) or math.isnan(sd):
        return None
    return int(math.ceil((t_target * sd / abs(mean)) ** 2))


def t_stat(values: Sequence[float]) -> float | None:
    """Tek örneklem t istatistiği (H0: ortalama = 0)."""
    a = _clean(values)
    if len(a) < 2:
        return None
    sd = float(a.std(ddof=1))
    if sd == 0:
        return None
    return float(a.mean() / (sd / math.sqrt(len(a))))


# ============================================================ dağılım
def dist_stats(values: Sequence[float], weak_n: int = 15) -> dict:
    """Bir getiri dağılımının özeti. Boşsa n=0 döner, patlamaz."""
    a = _clean(values)
    if a.size == 0:
        return {"n": 0, "ort": None, "medyan": None, "sd": None,
                "kazanma_pct": None, "t": None, "gerekli_n": None}
    sd = float(a.std(ddof=1)) if a.size > 1 else None
    ort = float(a.mean())
    return {
        "n": int(a.size),
        "ort": ort,
        "medyan": float(np.median(a)),
        "sd": sd,
        "kazanma_pct": float((a > 0).mean() * 100),
        "t": t_stat(a),
        "gerekli_n": required_n(ort, sd),
        "zayif": a.size < weak_n,
    }


def paired_stats(diffs: Sequence[float], weak_n: int = 15) -> dict:
    """Eşleştirilmiş farkların özeti.

    Eşleştirme kritik: aynı dönemde 'seçilen − seçilmeyen' alındığında piyasa
    faktörü TAM OLARAK sadeleşir. Ölçüm: eşleştirilmemiş getiri sd'si ~%15-20,
    eşleştirilmiş ~%5-6. Bu, gereken N'i ~9 kat azaltır.
    """
    return dist_stats(diffs, weak_n)


# ============================================================ ileri getiri
def forward_returns_nonoverlap(dates: Sequence[str], prices: Sequence[float],
                               signal_idx: Sequence[int], horizon: int
                               ) -> list[float]:
    """Örtüşmeyen ileri getiriler (yüzde).

    * Giriş t+1'de — sinyalin oluştuğu barın KAPANIŞINDA işlem yapılamaz.
      `close[t]` ile giriş varsaymak look-ahead'in en yaygın biçimidir.
    * Bir pencere kullanıldıysa sonraki giriş en az `horizon` gün ileriden
      seçilir → bağımsız örneklem.
    """
    p = np.asarray(prices, dtype=float)
    n = p.size
    out: list[float] = []
    son_cikis = -1
    for t in sorted(set(int(i) for i in signal_idx)):
        giris = t + 1
        if giris <= son_cikis:              # önceki pencereyle örtüşüyor
            continue
        cikis = giris + horizon
        if cikis >= n or giris >= n:
            continue
        p0, p1 = p[giris], p[cikis]
        if not (np.isfinite(p0) and np.isfinite(p1)) or p0 <= 0:
            continue
        out.append(float((p1 / p0 - 1.0) * 100.0))
        son_cikis = cikis
    return out


def effective_periods(n_signals: int, horizon: int) -> int:
    """Örtüşmeyen pencereye çevrilince kalan ETKİN dönem sayısının üst sınırı.

    "500 sinyal" ile "500 bağımsız gözlem" aynı şey değildir. Bu fonksiyon
    farkı görünür kılar.
    """
    if horizon <= 0:
        return n_signals
    return max(0, n_signals // horizon)


def measure_edge(dates: Sequence[str], prices: Sequence[float],
                 signal_idx: Sequence[int], horizon: int, *,
                 weak_n: int = 15, min_diff_p: float = 1.0,
                 baseline_idx: Sequence[int] | None = None) -> dict:
    """Bir sinyal kümesinin KOŞULSUZ TABANA göre farkı.

    Taban varsayılan olarak TÜM günlerdir, aynı örtüşmeyen pencere yöntemiyle.
    Bilgi mutlak medyanda değil, tabandan farktadır.
    """
    sig = dist_stats(forward_returns_nonoverlap(dates, prices, signal_idx, horizon), weak_n)
    taban_idx = baseline_idx if baseline_idx is not None else range(len(prices))
    base = dist_stats(forward_returns_nonoverlap(dates, prices, taban_idx, horizon), weak_n)

    fark = None
    if sig["n"] and base["n"] and sig["medyan"] is not None and base["medyan"] is not None:
        fark = sig["medyan"] - base["medyan"]

    return {"stat": sig, "taban": base, "fark": fark, "n": sig["n"],
            "hukum": edge_verdict(fark, sig["n"], weak_n, min_diff_p),
            "etkin_donem": effective_periods(len(list(signal_idx)), horizon)}


# ============================================================ kesitsel
def winsorize(values: Sequence[float], lo_pct: float = 5.0,
              hi_pct: float = 95.0) -> np.ndarray:
    """Uç değerleri yüzdelik sınırlara çeker (silmez).

    Neden gerekli: evrende volatilitesi %80'e varan isimler var (ASTOR, EUPWR).
    Bunlar z-skorun standart sapmasını şişirir ve TÜM diğer isimlerin skorunu
    sıfıra doğru bastırır. Silmek yerine kırpmak, bilgiyi koruyup etkiyi sınırlar.
    """
    a = np.asarray(values, dtype=float)
    gecerli = np.isfinite(a)
    if gecerli.sum() < 3:
        return a
    lo = np.nanpercentile(a[gecerli], lo_pct)
    hi = np.nanpercentile(a[gecerli], hi_pct)
    return np.clip(a, lo, hi)


def zscore(values: Sequence[float]) -> np.ndarray:
    """Kesitsel z-skor. sd=0 ise sıfır vektörü döner (sıfıra bölme yok)."""
    a = np.asarray(values, dtype=float)
    gecerli = np.isfinite(a)
    if gecerli.sum() < 2:
        return np.full(a.shape, np.nan)
    mu = float(np.nanmean(a[gecerli]))
    sd = float(np.nanstd(a[gecerli], ddof=1))
    if sd == 0 or not np.isfinite(sd):
        return np.where(gecerli, 0.0, np.nan)
    return np.where(gecerli, (a - mu) / sd, np.nan)


def spearman(x: Sequence[float], y: Sequence[float]) -> float | None:
    """Sıra korelasyonu (Spearman rho). Ortak geçerli gözlem <3 ise None.

    HIZLI DÖNGÜNÜN ANA METRİĞİ: dönem başına Spearman(skor, ileri alfa).
    Getiri kenarından çok daha erken ölçülebilir hale gelir çünkü her dönem
    evrenin TAMAMINI kullanır ve eşleştirilmiş bir tasarımdır.
    """
    a = np.asarray(x, dtype=float)
    b = np.asarray(y, dtype=float)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3:
        return None
    ra, rb = _rank(a[m]), _rank(b[m])
    sa, sb = ra.std(), rb.std()
    if sa == 0 or sb == 0:
        return None
    return float(((ra - ra.mean()) * (rb - rb.mean())).mean() / (sa * sb))


T_ANLAMLI = 2.0


def ic_verdict(ic_ort: float | None, n: int, t: float | None,
               weak_n: int, t_esik: float = T_ANLAMLI) -> str:
    """IC hükmü — BÜYÜKLÜĞE DEĞİL ANLAMLILIĞA bakar.

    `edge_verdict` yüzde-puan farkları için yazıldı ve orada mutlak büyüklük
    (|fark| ≥ 1.0p) anlamlı bir eşik. IC için öyle DEĞİL: IC=0.057 kulağa
    büyük gelir ama t=1.46 ise gürültüdür. İlk sürüm `edge_verdict`i IC'ye
    de uyguluyordu ve her pozitif IC'yi "zayıf kanıt" ilan ediyordu —
    kapıdaki işaret körlüğünün aynısı, sadece başka kılıkta.
    """
    if ic_ort is None or n <= 0 or t is None:
        return HUKUM_OLCUM_YOK
    if n < weak_n:
        return f"{HUKUM_YETERSIZ} (N={n})"
    if abs(t) < t_esik:
        return HUKUM_KENAR_YOK
    return f"{HUKUM_ZAYIF_KANIT}: IC={ic_ort:+.3f}"


def ic_summary(ics: Sequence[float | None], weak_n: int = 15) -> dict:
    """Dönem-içi IC serisinin özeti.

    `ic_ir` = ortalama IC / IC standart sapması (bilgi oranı).
    """
    a = _clean([i for i in ics if i is not None])
    if a.size == 0:
        return {"n_donem": 0, "ic_ort": None, "ic_sd": None, "ic_ir": None,
                "t": None, "gerekli_n": None, "hukum": HUKUM_OLCUM_YOK}
    sd = float(a.std(ddof=1)) if a.size > 1 else None
    ort = float(a.mean())
    t = t_stat(a)
    return {
        "n_donem": int(a.size),
        "ic_ort": ort,
        "ic_sd": sd,
        "ic_ir": (ort / sd) if sd else None,
        "t": t,
        "gerekli_n": required_n(ort, sd),
        "hukum": ic_verdict(ort, int(a.size), t, weak_n),
    }


# ============================================================ iç
def _clean(values: Sequence[float]) -> np.ndarray:
    a = np.asarray(list(values), dtype=float)
    return a[np.isfinite(a)]


def _rank(a: np.ndarray) -> np.ndarray:
    """Ortalama-bağ sıralaması (scipy'siz)."""
    sira = a.argsort()
    r = np.empty(a.size, dtype=float)
    r[sira] = np.arange(a.size, dtype=float)
    # eşitlikleri ortalamaya çek
    _, ilk, sayim = np.unique(a, return_index=True, return_counts=True)
    for deger, adet in zip(np.unique(a), sayim):
        if adet > 1:
            m = a == deger
            r[m] = r[m].mean()
    return r
