"""Şema migration'ları — `PRAGMA user_version` tabanlı, sıralı ve idempotent.

`db.SCHEMA` yalnızca "IF NOT EXISTS" ile taban şemayı kurar. Var olan bir tabloya
kolon eklemek / veri dönüştürmek gerektiğinde buraya bir adım eklenir.

Kural: bir migration YAYINLANDIKTAN sonra DEĞİŞTİRİLMEZ. Yanlışsa üstüne yeni
migration yazılır. Aksi halde farklı makinelerdeki veritabanları sessizce ayrışır.
"""

from __future__ import annotations

import sqlite3
from typing import Callable

# (hedef_sürüm, açıklama, fonksiyon)
# Sürüm 1 = db.SCHEMA'nın kurduğu taban. İlk gerçek migration 2'den başlar.
Migration = tuple[int, str, Callable[[sqlite3.Connection], None]]

def _add_column(con: sqlite3.Connection, table: str, col: str, tip: str) -> None:
    """Kolonu yoksa ekler. SQLite `ADD COLUMN IF NOT EXISTS` desteklemez;
    taban şema (db.SCHEMA) yeni kurulumlarda kolonu zaten getirdiği için
    bu adım mevcut veritabanlarında çalışır, yenilerinde sessizce geçer."""
    var = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
    if col not in var:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {tip}")


def _m002(con: sqlite3.Connection) -> None:
    """Trend kapısı için toplam-getiri uzayında SMA50/SMA200.

    Gerekçe: `c` (temettü düzeltmesiz) üzerinden SMA200, 200 günlük pencerede
    birikmiş temettü kadar yukarıda kalmış geçmiş fiyatların ortalamasıdır →
    fiyatı sistematik olarak SMA200'ün ALTINDA gösterir. %3-5 temettü verimiyle
    bu sapma, kapının %2'lik toleransından büyük; yani kapıyı bozar.
    Türev veri olduğu için geri doldurma gerekmez — `bist gosterge hesapla`
    satırları yeniden yazar.
    """
    _add_column(con, "indicator_daily", "sma50_tr", "REAL")
    _add_column(con, "indicator_daily", "sma200_tr", "REAL")


MIGRATIONS: list[Migration] = [
    (2, "indicator_daily: sma50_tr / sma200_tr (trend kapısı toplam getiri uzayında)", _m002),
]

BASELINE_VERSION = 1


def current_version(con: sqlite3.Connection) -> int:
    return int(con.execute("PRAGMA user_version").fetchone()[0])


def set_version(con: sqlite3.Connection, v: int) -> None:
    # PRAGMA parametre bağlama kabul etmez; v int'e zorlanmış durumda.
    con.execute(f"PRAGMA user_version = {int(v)}")


def apply(con: sqlite3.Connection) -> list[str]:
    """Bekleyen migration'ları sırayla uygular. Uygulananların açıklamasını döner."""
    v = current_version(con)
    if v == 0:
        set_version(con, BASELINE_VERSION)
        v = BASELINE_VERSION

    uygulanan: list[str] = []
    for hedef, aciklama, fn in sorted(MIGRATIONS, key=lambda m: m[0]):
        if hedef <= v:
            continue
        if hedef != v + 1:
            raise RuntimeError(
                f"Migration sırası kopuk: veritabanı v{v}, sıradaki v{hedef}. "
                "Aradaki adım eksik — MIGRATIONS listesini kontrol et."
            )
        fn(con)
        set_version(con, hedef)
        con.commit()
        uygulanan.append(f"v{hedef}: {aciklama}")
        v = hedef
    return uygulanan


def target_version() -> int:
    return max([m[0] for m in MIGRATIONS], default=BASELINE_VERSION)
