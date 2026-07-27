"""Evren yönetimi — `universe.yaml` → `universe` tablosu, ve evren sorguları.

İki ayrı evren vardır ve karıştırılmamalıdır:
  * CANLI evren (`in_live`)    — sinyal üretilen 18 hisse
  * ÖLÇÜM evreni (`in_measure`) — ağırlık kalibrasyonuna giren, ≥~8 yıl geçmişli isimler

Kısa geçmişli bir isim (ASTOR 878 bar, EUPWR 817 bar) canlı listede olabilir ama
ağırlık BELİRLEYEMEZ — 3 yıllık veriyle 10 yıllık parametre kalibre edilmez.
"""

from __future__ import annotations

import sqlite3

from . import db, util
from .sources import yf


def load_yaml_universe(cfg: dict) -> dict:
    return util.load_yaml(cfg["paths"]["universe_file"])


def sync(cfg: dict, con: sqlite3.Connection) -> dict:
    """`universe.yaml` → `universe` tablosu. YAML tek gerçek kaynaktır.

    YAML'dan silinen ticker tablodan da silinir; aksi halde eski isimler sessizce
    evrende kalır ve backtest ile canlı liste ayrışır.
    """
    data = load_yaml_universe(cfg)
    rows = []
    gorulen: set[str] = set()

    for h in (data.get("hisseler") or []):
        t = str(h["ticker"]).upper()
        gorulen.add(t)
        rows.append((
            t,
            yf.yf_symbol(t, cfg),
            h.get("name"),
            h["sektor"],
            h["tier"],
            1 if h.get("in_live", True) else 0,
            1 if h.get("in_measure", True) else 0,
            (h.get("olcum") or {}).get("ilk_tarih"),
            h.get("not"),
        ))

    # Ölçüm evreni: canlı sinyal ÜRETMEZ (in_live=0), yalnız kalibrasyona girer.
    # Kesitsel sıralamanın sıralayacak bir dağılımı olsun diye var.
    for sektor, liste in (data.get("olcum_evreni") or {}).items():
        for ad in liste:
            t = str(ad).upper()
            if t in gorulen:            # canlı evrende zaten varsa oradaki kazanır
                continue
            gorulen.add(t)
            rows.append((t, yf.yf_symbol(t, cfg), None, sektor, "olcum",
                         0, 1, None, "yalnız ölçüm evreni"))

    cols = ["ticker", "yf_symbol", "name", "sector", "tier",
            "in_live", "in_measure", "listed_from", "notes"]
    db.upsert_many(con, "universe", cols, rows)

    yaml_set = {r[0] for r in rows}
    mevcut = {r["ticker"] for r in db.fetch_all(con, "SELECT ticker FROM universe")}
    silinecek = mevcut - yaml_set
    for t in silinecek:
        con.execute("DELETE FROM universe WHERE ticker = ?", (t,))
    con.commit()

    return {
        "yazilan": len(rows),
        "silinen": sorted(silinecek),
        "canli": sum(r[5] for r in rows),
        "olcum": sum(r[6] for r in rows),
    }


# ---------------------------------------------------------------- sorgular
def live(con: sqlite3.Connection) -> list[str]:
    """Canlı sinyal evreni — sıralı ticker listesi."""
    return [r["ticker"] for r in db.fetch_all(
        con, "SELECT ticker FROM universe WHERE in_live = 1 ORDER BY ticker")]


def measure(con: sqlite3.Connection) -> list[str]:
    """Ağırlık kalibrasyonu evreni."""
    return [r["ticker"] for r in db.fetch_all(
        con, "SELECT ticker FROM universe WHERE in_measure = 1 ORDER BY ticker")]


def all_tickers(con: sqlite3.Connection) -> list[str]:
    """Veri çekilecek her şey — canlı olmayan test vakaları dahil (ör. SASA)."""
    return [r["ticker"] for r in db.fetch_all(
        con, "SELECT ticker FROM universe ORDER BY ticker")]


def sector_map(con: sqlite3.Connection) -> dict[str, str]:
    return {r["ticker"]: r["sector"] for r in
            db.fetch_all(con, "SELECT ticker, sector FROM universe")}


def tier_map(con: sqlite3.Connection) -> dict[str, str]:
    return {r["ticker"]: r["tier"] for r in
            db.fetch_all(con, "SELECT ticker, tier FROM universe")}


def index_symbols(cfg: dict) -> dict[str, str]:
    """{'XU100': 'XU100.IS', ..., 'USDTRY': 'USDTRY=X'} — endeks + kur birlikte."""
    ycfg = cfg["sources"]["yf"]
    return {**ycfg["endeksler"], **ycfg["kur"]}


def scan(cfg: dict) -> list[dict]:
    """Evrendeki her sembolü CANLI yoklar — `universe.yaml`'daki ölçümleri tazeler.

    universe.yaml'daki sayılar hafızadan değil ölçümden gelir; bu komut onları
    yeniden üretir. Kriter ihlallerini `ihlaller` alanında işaretler.
    """
    ev = cfg["evren"]
    data = load_yaml_universe(cfg)
    out = []
    for h in (data.get("hisseler") or []):
        t = str(h["ticker"]).upper()
        p = yf.probe(t, cfg, period="2y")
        ihlaller = []
        if not p["ok"]:
            ihlaller.append("veri yok")
        else:
            if (p["median_turnover_try"] or 0) < ev["min_medyan_islem_hacmi_try"]:
                ihlaller.append(
                    f"likidite {p['median_turnover_try']/1e6:.0f}mn < "
                    f"{ev['min_medyan_islem_hacmi_try']/1e6:.0f}mn")
            if (p["zero_vol_ratio"] or 0) > ev["maks_sifir_hacim_orani"]:
                ihlaller.append(
                    f"sıfır hacim %{p['zero_vol_ratio']*100:.1f} > "
                    f"%{ev['maks_sifir_hacim_orani']*100:.0f}")
        out.append({**p, "tier": h.get("tier"), "sektor": h.get("sektor"),
                    "in_live": h.get("in_live", True), "ihlaller": ihlaller})
    return out
