"""Makro bağlam — TCMB EVDS serilerinin çekilmesi, saklanması ve yorumlanması.

`context()` rapor ve rejim katmanının kullandığı tek arayüzdür. Veri yoksa
ilgili anahtar SÖZLÜKTE HİÇ BULUNMAZ (None olarak da değil) — rapor o satırı
gizler. Yerine vekil koymak ölçümü sahtelemektir; gold projesindeki karar aynen
geçerli: `^TNX` nominal getiridir, onu "reel faiz" diye sunmak sahteleme olurdu.
"""

from __future__ import annotations

import logging
import sqlite3

from . import db, util
from .sources import evds

log = logging.getLogger(__name__)


def _series_map(cfg: dict) -> dict[str, str]:
    return dict(cfg["sources"]["evds"]["series"])


def _store(con: sqlite3.Connection, code: str, rows: list[dict]) -> int:
    return db.upsert_many(con, "evds_daily", ["date", "series_code", "value"],
                          [(r["date"], code, r["value"]) for r in rows])


def backfill(cfg: dict, con: sqlite3.Connection) -> dict:
    """Yapılandırmadaki `backfill` listesini yıl yıl çeker."""
    smap = _series_map(cfg)
    hedef = cfg["sources"]["evds"].get("backfill", list(smap))
    sonuc: dict[str, int] = {}
    for mantiksal in hedef:
        code = smap.get(mantiksal)
        if not code:
            continue
        sonuc[mantiksal] = _store(con, code, evds.fetch_series_chunked(cfg, code))
        log.info("EVDS backfill %s (%s): %d satır", mantiksal, code, sonuc[mantiksal])
    return sonuc


def daily(cfg: dict, con: sqlite3.Connection) -> dict:
    """Tüm serileri kayan pencereyle günceller (revizyonları da yakalar)."""
    from datetime import date, timedelta

    gun = int(cfg["sources"]["evds"].get("gunluk_pencere_gun", 45))
    start = (date.today() - timedelta(days=gun)).strftime("%d-%m-%Y")
    sonuc: dict[str, int] = {}
    for mantiksal, code in _series_map(cfg).items():
        sonuc[mantiksal] = _store(con, code, evds.fetch_series(cfg, code, start=start))
    return sonuc


# ---------------------------------------------------------------- okuma
def _latest(con: sqlite3.Connection, code: str, asof: str | None = None
            ) -> tuple[str | None, float | None]:
    sql = ("SELECT date, value FROM evds_daily WHERE series_code = ? AND value IS NOT NULL")
    params: list = [code]
    if asof:
        sql += " AND date <= ?"; params.append(asof)
    row = con.execute(sql + " ORDER BY date DESC LIMIT 1", params).fetchone()
    return (row[0], row[1]) if row else (None, None)


def _cpi_yoy(con: sqlite3.Connection, code: str, asof: str | None = None) -> float | None:
    """TÜFE ENDEKSİNDEN yıllık enflasyon. Endeks kullanılır, 'oran' serisi değil.

    ⚠ Karşılaştırma TARİHE göre yapılır, satır sayısına göre DEĞİL. İlk sürüm
    `rows[-13]`'ü "12 ay önce" sayıyordu; seride tek bir eksik ay varsa o
    varsayım bozulur ve enflasyon SESSİZCE yanlış bir pencereden hesaplanır.
    """
    from datetime import date as _date

    sql = "SELECT date, value FROM evds_daily WHERE series_code = ? AND value IS NOT NULL"
    params: list = [code]
    if asof:
        sql += " AND date <= ?"; params.append(asof)
    rows = con.execute(sql + " ORDER BY date", params).fetchall()
    if len(rows) < 13:
        return None

    son_tarih, son = rows[-1][0], rows[-1][1]
    d_son = util.parse_date(son_tarih)
    if d_son is None or not son:
        return None
    try:
        hedef = d_son.replace(year=d_son.year - 1)
    except ValueError:                       # 29 Şubat
        hedef = d_son.replace(year=d_son.year - 1, day=28)

    # Hedefe en yakın (ve ondan büyük olmayan) gözlem; 45 günden uzaksa ölçme.
    aday = [(util.parse_date(d), v) for d, v in rows]
    onceki = [(d, v) for d, v in aday if d is not None and d <= hedef and v]
    if not onceki:
        return None
    d_ref, yil_once = onceki[-1]
    if abs((hedef - d_ref).days) > 45:
        log.info("TÜFE YoY ölçülemedi: %s için 12 ay öncesine en yakın gözlem "
                 "%s (%d gün sapma)", son_tarih, d_ref, (hedef - d_ref).days)
        return None
    return (son / yil_once - 1.0) * 100.0


def context(cfg: dict, con: sqlite3.Connection, asof: str | None = None) -> dict:
    """Makro bağlam sözlüğü.

    Veri yoksa anahtar HİÇ EKLENMEZ. Çağıran `ctx.get('politika_faizi')` ile
    yokluğu görür ve satırı gizler — uydurulmuş vekil değer konulmaz.
    """
    smap = _series_map(cfg)
    stopaj = float(cfg["sources"]["evds"].get("mevduat_stopaj_pct", 15.0))
    ctx: dict = {}

    _, pol = _latest(con, smap.get("aofm_politika", ""), asof)
    if pol is not None:
        ctx["politika_faizi"] = pol

    tufe_tarih, _ = _latest(con, smap.get("tufe", ""), asof)
    yoy = _cpi_yoy(con, smap.get("tufe", ""), asof)
    if yoy is not None:
        ctx["tufe_yoy"] = yoy
        ctx["tufe_tarih"] = tufe_tarih

    _, bek = _latest(con, smap.get("enf_bek_12ay", ""), asof)
    if bek is not None:
        ctx["enf_bek_12ay"] = bek

    _, dep = _latest(con, smap.get("mevduat_1yil", ""), asof)
    if dep is not None:
        ctx["mevduat_1yil_brut"] = dep
        ctx["mevduat_1yil_net"] = dep * (1.0 - stopaj / 100.0)

    _, usd = _latest(con, smap.get("usdtry_sell", ""), asof)
    if usd is not None:
        ctx["usdtry"] = usd

    # Reel net mevduat faizi — FISHER (geometrik), çıkarma DEĞİL.
    # Yüksek enflasyonda "faiz − enflasyon" ciddi biçimde yanlıştır.
    if "mevduat_1yil_net" in ctx:
        enf = ctx.get("enf_bek_12ay", ctx.get("tufe_yoy"))
        if enf is not None:
            ctx["reel_net_mevduat"] = (
                (1 + ctx["mevduat_1yil_net"] / 100) / (1 + enf / 100) - 1) * 100

    return ctx


def null_pct(cfg: dict, ctx: dict) -> float:
    """Beklenen makro alanların yüzde kaçı eksik.

    Rejim katmanı bunu kullanır: eksik oranı yüksekse nakit önerisi defansif
    tarafa kayar (bilmemek, bilmek gibi davranmaktan iyidir).
    """
    beklenen = ["politika_faizi", "tufe_yoy", "enf_bek_12ay",
                "mevduat_1yil_net", "usdtry", "reel_net_mevduat"]
    eksik = sum(1 for k in beklenen if ctx.get(k) is None)
    return eksik / len(beklenen) * 100.0
