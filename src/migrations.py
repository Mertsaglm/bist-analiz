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

MIGRATIONS: list[Migration] = [
    # Örnek (şu an yok):
    # (2, "bars_daily'ye vwap kolonu", lambda con: con.execute(
    #     "ALTER TABLE bars_daily ADD COLUMN vwap REAL")),
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
