"""Yürüyen-ileri ölçüm harness'i — projenin KAPISI.

Bu dosya "strateji ne kadar kazandırır" sorusunu DEĞİL, "bu skorun taban
çizgisine göre ölçülebilir bir üstünlüğü var mı" sorusunu cevaplar.

Dört değişmez, dördü de ihlal edilirse ölçüm geçersizdir:

1. **Giriş t+1.** Sinyalin oluştuğu barın kapanışında işlem yapılamaz.
2. **Örtüşmeyen dönemler.** Denge tarihleri `horizon` aralıklı → bağımsız gözlem.
3. **Taban = EŞİT AĞIRLIK UYGUN EVREN, XU100 DEĞİL.** Ölçüldü (2026-07-26,
   29 likit isim, H=15, N=175): eşit-ağırlık sepet XU100'ü SIFIR beceriyle
   +0.36pp/dönem, %60 kazanma, t=2.89 ile yeniyor. XU100'e göre alfa bu
   bedava üstünlüğü sessizce içerir. XU100 raporda kalır ama hüküm EW'ye göre.
4. **Maliyet yalnız seçilen portföye.** Seçim her dönem tam devir yapar;
   EW tabanı yaklaşık al-tut'tur. Maliyeti ikisine de yüklemek onları
   sadeleştirir ve maliyet duyarlılığını anlamsızlaştırır. Bu asimetri
   stratejinin ALEYHİNEDİR — doğru yön budur.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import factors, stats, util

log = logging.getLogger(__name__)

ISINMA_BAR = 260          # 252 günlük pencereler dolsun


@dataclass
class Panel:
    """Evrenin hizalanmış matris görünümü. Tüm backtest bunun üzerinde çalışır."""
    dates: list[str]
    tickers: list[str]
    c: np.ndarray          # bölünme düzeltmeli → seviye
    c_tr: np.ndarray       # toplam getiri → getiri/momentum
    h: np.ndarray
    turnover: np.ndarray
    xu100: np.ndarray

    @property
    def n(self) -> int:
        return len(self.dates)


def load_panel(con: sqlite3.Connection, tickers: list[str], *,
               start: str | None = None, end: str | None = None) -> Panel:
    """Barları tek seferde matrise alır — dönem başına SQL sorgusu yapmaz."""
    ph = ",".join("?" * len(tickers))
    sql = (f"SELECT ticker, date, c, c_tr, h, turnover_try FROM bars_daily "
           f"WHERE ticker IN ({ph})")
    params: list = [t.upper() for t in tickers]
    if start:
        sql += " AND date >= ?"; params.append(start)
    if end:
        sql += " AND date <= ?"; params.append(end)
    df = pd.read_sql_query(sql + " ORDER BY date", con, params=params)
    if df.empty:
        raise ValueError("Panel boş — önce `bist veri backfill`")

    piv = {k: df.pivot(index="date", columns="ticker", values=v)
           for k, v in [("c", "c"), ("c_tr", "c_tr"), ("h", "h"), ("to", "turnover_try")]}

    xs = pd.read_sql_query(
        "SELECT date, c FROM index_daily WHERE symbol='XU100' ORDER BY date",
        con).set_index("date")["c"]

    # Endeks barı OLAN günlerle kesiştir: takvimin otoritesi endekstir ve
    # hisse tarafındaki artıkları buraya taşımanın anlamı yok.
    idx = piv["c"].index.intersection(xs.index)
    kol = sorted(piv["c"].columns)

    return Panel(
        dates=list(idx),
        tickers=kol,
        c=piv["c"].loc[idx, kol].to_numpy(float),
        c_tr=piv["c_tr"].loc[idx, kol].to_numpy(float),
        h=piv["h"].loc[idx, kol].to_numpy(float),
        turnover=piv["to"].loc[idx, kol].to_numpy(float),
        xu100=xs.loc[idx].to_numpy(float),
    )


# ============================================================ vektörel faktörler
def _shift(a: np.ndarray, k: int) -> np.ndarray:
    out = np.full_like(a, np.nan)
    if k > 0:
        out[k:] = a[:-k]
    elif k < 0:
        out[:k] = a[-k:]
    else:
        out[:] = a
    return out


def _roll_mean(a: np.ndarray, n: int) -> np.ndarray:
    return pd.DataFrame(a).rolling(n, min_periods=n).mean().to_numpy()


def _roll_med(a: np.ndarray, n: int) -> np.ndarray:
    return pd.DataFrame(a).rolling(n, min_periods=n).median().to_numpy()


def _roll_max(a: np.ndarray, n: int) -> np.ndarray:
    return pd.DataFrame(a).rolling(n, min_periods=100).max().to_numpy()


def build_features(p: Panel, cfg: dict) -> dict[str, np.ndarray]:
    """Faktörler ve kapı girdileri — tarih × ticker matrisleri.

    Her değer t anında BİLİNEBİLİR olmalıdır: yalnız geçmişe bakan pencereler.
    """
    ctr = p.c_tr
    r = lambda k: ctr / _shift(ctr, k) - 1.0                      # noqa: E731

    mom_6_1 = ((1 + r(126)) / (1 + r(21)) - 1.0) * 100.0
    mom_12_1 = ((1 + r(252)) / (1 + r(21)) - 1.0) * 100.0
    high52 = _roll_max(p.h, 252)
    high52_prox = (p.c / high52 - 1.0) * 100.0

    logret = np.log(ctr / _shift(ctr, 1))
    vol63 = (pd.DataFrame(logret).rolling(cfg["gostergeler"]["vol_pencere_gun"],
                                          min_periods=cfg["gostergeler"]["vol_pencere_gun"])
             .std(ddof=1).to_numpy() * np.sqrt(252.0) * 100.0)

    with np.errstate(divide="ignore", invalid="ignore"):
        volscaled = mom_6_1 / np.where(vol63 > 0, vol63, np.nan)

    return {
        "mom_6_1": mom_6_1,
        "mom_12_1": mom_12_1,
        "high52_prox": high52_prox,
        "volscaled_mom": volscaled,
        "sma200_tr": _roll_mean(ctr, 200),
        "turnover_med_63": _roll_med(p.turnover, 63),
        "vol_ann_63": vol63,
    }


# Kapılar ayrı ayrı açılıp kapanabilir. Sebep: ölçüm (2026-07-26) bunların
# AYNI ŞEY OLMADIĞINI gösterdi — SMA200 bir BİLGİ kapısıdır (skorun sıralayacağı
# varyansı keser), likidite ve veri kalitesi ise UYGULANABİLİRLİK kapılarıdır
# (işlem yapılamayan ismi elerler, bilgi yok etmezler). İkisini tek bayrağın
# arkasına koymak, birini ölçerken diğerini de kapatmaya zorluyordu.
VARSAYILAN_KAPILAR = {"sma200": True, "likidite": True, "veri": True}


def eligible_mask(p: Panel, feat: dict, cfg: dict, t: int,
                  kapilar: dict[str, bool] | None = None) -> np.ndarray:
    """t anında hangi isimler skorlanabilir. Kapılar skorlanmaz, ELER."""
    f, ev = cfg["faktorler"], cfg["evren"]
    k = {**VARSAYILAN_KAPILAR, **(kapilar or {})}
    n = len(p.tickers)

    m = np.isfinite(p.c_tr[t]) & (p.c_tr[t] > 0)          # fiyat her hâlde şart

    if k["sma200"]:
        tol = float(f["kapilar"]["sma200_tolerans"])
        s200 = feat["sma200_tr"][t]
        m &= np.isfinite(s200) & (p.c_tr[t] >= s200 * (1 - tol))
    if k["likidite"]:
        likit = feat["turnover_med_63"][t] >= float(ev["min_medyan_islem_hacmi_try"])
        m &= np.nan_to_num(likit, nan=False).astype(bool)
    if k["veri"]:
        m &= np.isfinite(feat["mom_6_1"][t]) & np.isfinite(feat["mom_12_1"][t])
    return m if m.shape == (n,) else np.zeros(n, dtype=bool)


def score_at(p: Panel, feat: dict, cfg: dict, t: int, *,
             horizon_days: int, weights: dict[str, float] | None = None,
             sector_map: dict[str, str] | None = None) -> np.ndarray:
    """t anındaki kesitsel skor. z TÜM evrende, sıralama uygunlar arasında."""
    f = cfg["faktorler"]
    lo, hi = f["winsor_pct"]
    w = weights or factors.effective_weights(cfg, horizon_days)

    skor = np.zeros(len(p.tickers))
    payda = np.zeros(len(p.tickers))
    for ad, agirlik in w.items():
        if agirlik == 0:
            continue
        z = stats.zscore(stats.winsorize(feat[ad][t], lo, hi))
        if f["sektor_notr"] and sector_map:
            z = factors._sector_demean(z, p.tickers, sector_map)
        var = np.isfinite(z)
        skor = np.where(var, skor + agirlik * np.nan_to_num(z), skor)
        # Payda MUTLAK ağırlık toplamı. İşaretli toplasaydık negatif ağırlıklı
        # bir faktör (ölçüm tersini söylediğinde meşru bir kullanım) kendini
        # paydada götürür ve skorun işaretini geri çevirirdi.
        payda = np.where(var, payda + abs(agirlik), payda)
    # `np.where` İKİ DALI DA hesaplar: payda=0 olan isimlerde 0/0 yapılır ve
    # numpy uyarı basar. Sonuç doğru (o hücreler zaten NaN'a gidiyor) ama uyarı
    # `bist backtest` / `bist teshis` çıktısını kirletir ve GERÇEK uyarıları
    # gözden kaçırtır. Bastırılan şey bir hata değil, beklenen bir hücre.
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(payda > 0, skor / payda, np.nan)


def bozuk_bar_mask(p: Panel, cfg: dict) -> np.ndarray:
    """Düzeltilmemiş kurumsal işlem BARLARI — (tarih × ticker) boolean maske.

    ⚠ NE OLMUŞTU (2026-08-07): `eligible_mask`'in "veri" kapısı yalnız
    *momentum hesaplanabiliyor mu* diye soruyordu. Kayıt bazlı kalite kapısı
    (`prices.assess_quality`) ise YALNIZ CANLI hatta koşuyordu. Yani canlı
    katman "bu ismin verisine güvenmiyorum" derken ölçüm katmanı aynı barları
    sessizce kullanıyordu — L-008'in "simetriğini ara" kuralı tam buraya
    bakıyordu.

    ÖLÇÜLDÜ: panelde 5 böyle bar var (CCOLA 2024-08-01 **−%90.7** ·
    TSPOR +%94.6 · AYGAZ +%72.5 · HEKTS −%64.8 / +%44.1). ±%10 marjlı bir
    piyasada bunlar getiri DEĞİL, düzeltilmemiş bölünmedir.

    Eşik `evren.duzeltilmemis_kurumsal_pct` — gerçek piyasa ucundan (+%22.2,
    2023-02-15 deprem sonrası açılış) yukarıda, en küçük artefakttan (+%44)
    aşağıda. `risk`/`prices` ile AYNI config anahtarından okunur.
    """
    esik = float(cfg["evren"]["duzeltilmemis_kurumsal_pct"]) / 100.0
    onceki = _shift(p.c_tr, 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        g = p.c_tr / onceki - 1.0
    return np.isfinite(g) & (np.abs(g) > esik)


# ============================================================ yürüyen ileri
def walk_forward(cfg: dict, p: Panel, *, horizon: int, top_frac: float = 1 / 3,
                 cost_pct: float = 0.0, weights: dict[str, float] | None = None,
                 sector_map: dict[str, str] | None = None,
                 use_gates: bool = True,
                 kapilar: dict[str, bool] | None = None,
                 start_idx: int | None = None,
                 end_idx: int | None = None) -> dict:
    """Örtüşmeyen dönemlerle yürüyen-ileri ölçüm.

    İKİ AYRI SORU ölçülür, karıştırılmaz:

    * **`ic_tum`** — skor TÜM kesiti sıralayabiliyor mu? Kapı UYGULANMADAN,
      geçerli veriye sahip her isim üzerinde. Bu, hızlı döngünün ana metriği.
    * **`alfa_ew`** — kapı + seçim birlikte, aynı UYGUN küme içinde eşit-ağırlık
      tabana göre. Eşleştirilmiş tasarım: piyasa faktörü tam sadeleşir.

    Neden ayrı: kapı sıralamadan ÖNCE eler, yani skorun ayırt edeceği aralığı
    daraltır. İkisini tek sayıya sıkıştırmak "skor kötü" ile "kapı çok dar"ı
    ayırt edilemez hale getirir.

    **SESSİZ KIRPMA YOK:** uygun isim sayısı azaldığında dönem atlanmaz,
    portföy küçülür (`n_secilen`). Atlanan dönemler `n_atlanan`'da raporlanır.
    Eski sürüm `uygun < top_n` olan dönemleri düşürüyordu ve bu, 2016-2019 ile
    2024-2025'in TAMAMINI örneklemden çıkarıyordu (131 dönemin 62'si) —
    yani ölçüm yalnız geniş boğa dönemlerinde yapılıyordu.
    """
    feat = build_features(p, cfg)
    bozuk = bozuk_bar_mask(p, cfg)
    bas = max(start_idx or ISINMA_BAR, ISINMA_BAR)
    son = (end_idx if end_idx is not None else p.n) - horizon - 1

    kayit: list[dict] = []
    ic_tum_seri: list[float] = []
    atlanan = {"veri_yok": 0, "uygun_yok": 0}
    n_kirli_gozlem = 0

    for t in range(bas, son, horizon):
        giris, cikis = t + 1, t + 1 + horizon
        if cikis >= p.n:
            break

        skor = score_at(p, feat, cfg, t, horizon_days=horizon,
                        weights=weights, sector_map=sector_map)
        with np.errstate(invalid="ignore"):
            fwd = (p.c_tr[cikis] / p.c_tr[giris] - 1.0) * 100.0

        # ⚠ CERRAHİ ELEME: ismin TAMAMI değil, yalnız ZEHİRLENEN gözlem düşer.
        # Pencerede düzeltilmemiş bir kurumsal işlem barı varsa o dönemin
        # ileri getirisi bir getiri değil, bir veri hatasıdır. İsmi tamamen
        # çıkarmak ölçüm evrenini değiştirmek olurdu (ölçüldü: 67→63 isim,
        # alfa −0.861 → −0.946pp) — oysa sorun isimde değil, o bir avuç barda.
        kirli = bozuk[giris + 1:cikis + 1].any(axis=0)
        if kirli.any():
            n_kirli_gozlem += int(kirli.sum())
            fwd = np.where(kirli, np.nan, fwd)

        # --- (1) sıralama kalitesi: KAPISIZ, tüm geçerli kesit ---
        tum = np.isfinite(skor) & np.isfinite(fwd)
        if tum.sum() < 4:
            atlanan["veri_yok"] += 1
            continue
        ti = np.where(tum)[0]
        ic_tum = stats.spearman(skor[ti], fwd[ti] - float(fwd[ti].mean()))
        if ic_tum is not None:
            ic_tum_seri.append(ic_tum)

        # --- (2) kapı + seçim: aynı uygun küme içinde eşleştirilmiş ---
        uygun = (eligible_mask(p, feat, cfg, t, kapilar) if use_gates
                 else np.ones(len(p.tickers), dtype=bool))
        havuz = uygun & tum
        if havuz.sum() < 2:
            atlanan["uygun_yok"] += 1
            continue

        hi = np.where(havuz)[0]
        k = max(1, int(round(len(hi) * top_frac)))
        secilen = hi[np.argsort(-skor[hi])][:k]

        r_sec = float(fwd[secilen].mean()) - cost_pct   # tam devir → maliyet burada
        r_ew = float(fwd[hi].mean())                    # ~al-tut → maliyetsiz
        r_xu = float((p.xu100[cikis] / p.xu100[giris] - 1.0) * 100.0)
        ic_uygun = stats.spearman(skor[hi], fwd[hi] - r_ew)

        kayit.append({
            "t": t, "tarih": p.dates[t], "giris": p.dates[giris], "cikis": p.dates[cikis],
            "n_havuz": len(hi), "n_secilen": len(secilen), "n_tum": int(tum.sum()),
            "r_secilen": r_sec, "r_ew": r_ew, "r_xu100": r_xu,
            "alfa_ew": r_sec - r_ew, "alfa_xu100": r_sec - r_xu,
            "ic_uygun": ic_uygun, "ic_tum": ic_tum,
            "secilenler": [p.tickers[i] for i in secilen],
        })

    # ⚠ Sayaç HER İKİ dönüş dalında da taşınır. İlk sürüm yalnız normal dalda
    # yazıyordu; `kayit` boş dönen bir ölçümde anahtar hiç oluşmuyordu ve
    # tüketici tarafta `KeyError` üretiyordu. Bir eleme sayacının bazı
    # dallarda var bazı dallarda yok olması, tam da "sessiz eleme"nin
    # kılık değiştirmiş hâlidir.
    atlanan["kirli_gozlem"] = n_kirli_gozlem
    o = cfg["olcum"]
    zn = o["zayif_n_esigi"]
    if not kayit:
        return {"n_donem": 0, "donemler": [], "n_atlanan": atlanan,
                "alfa_ew": stats.dist_stats([]), "alfa_xu100": stats.dist_stats([]),
                "ic": stats.ic_summary([]), "ic_tum": stats.ic_summary(ic_tum_seri, zn),
                "hukum": stats.HUKUM_OLCUM_YOK}

    s_ew = stats.dist_stats([k["alfa_ew"] for k in kayit], zn)
    s_xu = stats.dist_stats([k["alfa_xu100"] for k in kayit], zn)

    return {
        "n_donem": len(kayit),
        "n_atlanan": atlanan,
        "donemler": kayit,
        "alfa_ew": s_ew,
        "alfa_xu100": s_xu,
        "ic": stats.ic_summary([k["ic_uygun"] for k in kayit], zn),
        "ic_tum": stats.ic_summary(ic_tum_seri, zn),
        "ort_havuz": float(np.mean([k["n_havuz"] for k in kayit])),
        "ort_secilen": float(np.mean([k["n_secilen"] for k in kayit])),
        # HÜKÜM DAİMA EW TABANINA GÖRE — XU100 yalnız iletişim içindir.
        "hukum": stats.edge_verdict(s_ew["ort"], s_ew["n"], zn, o["min_anlamli_fark_puan"]),
        "ayar": {"horizon": horizon, "top_frac": top_frac, "cost_pct": cost_pct,
                 "kapilar": ({**VARSAYILAN_KAPILAR, **(kapilar or {})}
                             if use_gates else "hepsi kapalı"),
                 "sektor_notr": cfg["faktorler"]["sektor_notr"],
                 "agirliklar": weights or factors.effective_weights(cfg, horizon)},
    }


def baseline_ew_vs_xu100(p: Panel, cfg: dict, *, horizon: int) -> dict:
    """Eşit-ağırlık uygun evrenin XU100'e göre BEDAVA üstünlüğü.

    Bu sayı raporda mutlaka görünmeli: "XU100'e göre alfa" iddialarının ne
    kadarının beceri, ne kadarının sermaye-ağırlık artefaktı olduğunu gösterir.
    """
    feat = build_features(p, cfg)
    farklar = []
    for t in range(ISINMA_BAR, p.n - horizon - 1, horizon):
        giris, cikis = t + 1, t + 1 + horizon
        uygun = eligible_mask(p, feat, cfg, t)
        with np.errstate(invalid="ignore"):
            fwd = (p.c_tr[cikis] / p.c_tr[giris] - 1.0) * 100.0
        m = uygun & np.isfinite(fwd)
        if m.sum() < 3:
            continue
        r_xu = float((p.xu100[cikis] / p.xu100[giris] - 1.0) * 100.0)
        farklar.append(float(fwd[m].mean()) - r_xu)
    return stats.dist_stats(farklar, cfg["olcum"]["zayif_n_esigi"])


def solo(ad: str) -> dict[str, float]:
    """Tek faktörü izole eden ağırlık sözlüğü."""
    return {f: (1.0 if f == ad else 0.0) for f in factors.FACTOR_NAMES}


def split_index(p: Panel, tarih: str) -> int:
    """OOS bölme noktasının bar indeksi."""
    for i, d in enumerate(p.dates):
        if d >= tarih:
            return i
    return p.n


# ============================================================ tam ölçüm
def full_measurement(cfg: dict, con: sqlite3.Connection, *,
                     start: str | None = None, end: str | None = None,
                     top_frac: float | None = None) -> dict:
    """Faz 2'nin tamamı: faktör kenarı, sıralama kalitesi, IS/OOS, ufuk, maliyet.

    Kapı kararı burada HESAPLANIR ama verilmez — rapor yazar, insan okur.
    """
    from . import universe

    o = cfg["olcum"]
    tickers = universe.measure(con)
    p = load_panel(con, tickers, start=start, end=end)
    smap = universe.sector_map(con)

    H = int(o["ana_ufuk_gun"])
    tf = top_frac or (1 / 3)
    cost = float(cfg["risk"]["islem_maliyeti_gidis_donus_pct"])
    bol = split_index(p, o["oos_split"])
    n_test = 0

    def koş(**kw):
        nonlocal n_test
        n_test += 1
        return walk_forward(cfg, p, sector_map=smap, top_frac=tf, **kw)

    fakt = {ad: koş(horizon=H, cost_pct=cost, weights=solo(ad))
            for ad in factors.FACTOR_NAMES}
    birlesik = koş(horizon=H, cost_pct=cost)

    dilimler = {
        "tam": birlesik,
        "in-sample": koş(horizon=H, cost_pct=cost, end_idx=bol),
        "OOS": koş(horizon=H, cost_pct=cost, start_idx=bol),
    }
    ufuklar = {h: koş(horizon=h, cost_pct=cost) for h in o["ufuklar_gun"]}
    maliyetler = {c: koş(horizon=H, cost_pct=c) for c in o["maliyet_duyarliligi_pct"]}

    # Kapı yardım mı ediyor, zarar mı? Sıralamadan ÖNCE elediği için
    # skorun ayırt edeceği aralığı daraltıyor olabilir — ölçülmeden bilinmez.
    kapisiz = koş(horizon=H, cost_pct=cost, use_gates=False)

    # --- KAPI KARARI ---
    # Birincil ölçüt PLANDAKİ gibi: OOS'ta EW tabanına göre `zayıf kanıt`.
    # ⚠ İŞARET ŞART: `edge_verdict` bir BÜYÜKLÜK hükmüdür (|fark| bakar), yön
    # hükmü değil. İlk sürümde kapı yalnız hükme bakıyordu ve güvenilir biçimde
    # KAYBETTİREN bir faktör (mom_12_1: −1.47pp, t=−2.64) kapıyı AÇIYORDU.
    # Kapı pozitif kanıt ister; negatif kanıt ayrı ve DEĞERLİ bir bulgudur.
    oos_fakt = {ad: koş(horizon=H, cost_pct=cost, weights=solo(ad), start_idx=bol)
                for ad in factors.FACTOR_NAMES}
    tum_oos = {**oos_fakt, "birleşik": dilimler["OOS"]}

    def _kanit(r) -> bool:
        return r["hukum"].startswith(stats.HUKUM_ZAYIF_KANIT)

    gecen = [ad for ad, r in tum_oos.items()
             if _kanit(r) and (r["alfa_ew"]["ort"] or 0) > 0]
    ters = [ad for ad, r in tum_oos.items()
            if _kanit(r) and (r["alfa_ew"]["ort"] or 0) < 0]

    ic_gecen = [ad for ad, r in tum_oos.items()
                if (r["ic_tum"]["t"] or 0) >= 2.0]

    return {
        "tarih": util.utc_now_iso()[:10],
        "n_ticker": len(tickers), "tickers": tickers,
        "ilk_tarih": p.dates[0], "son_tarih": p.dates[-1], "n_bar": p.n,
        "horizon": H, "top_frac": tf, "cost_pct": cost, "donem_yil": 252.0 / H,
        "taban_ew_vs_xu100": baseline_ew_vs_xu100(p, cfg, horizon=H),
        "faktorler": fakt, "birlesik": birlesik, "dilimler": dilimler,
        "ufuklar": ufuklar, "maliyetler": maliyetler,
        "kapisiz": kapisiz, "oos_faktorler": oos_fakt,
        "kapi": {"gecen": gecen, "acik": bool(gecen),
                 "ters": ters, "ic_gecen": ic_gecen},
        "n_test": n_test,
    }
