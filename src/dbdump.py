"""SQLite'ı git'te diff'lenebilir hale getiren DETERMİNİSTİK SQL dump.

Neden: `.db` ikili bir dosyadır; git'te diff'lenmez, birleştirilemez ve her
çalıştırmada (WAL, sayfa sırası) baytları değişir. Aynı verinin iki dumpi
BİREBİR aynı metni vermelidir — aksi halde "veri değişti mi?" sorusu
cevaplanamaz.

Determinizm kuralları:
  * tablolar ada göre sıralı
  * satırlar birincil anahtara göre sıralı
  * float'lar repr ile değil sabit biçimle yazılır
  * zaman damgası / rastgelelik YOK
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import db, util

# Dump'a girmeyen tablolar: yeniden üretilebilir türev veri.
# Bunlar dump'a girse repo şişer ve her çalıştırmada gürültülü diff üretirdi.
ATLA: set[str] = {"indicator_daily", "levels_daily", "data_quality"}


def _quote(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, (int,)):
        return str(v)
    if isinstance(v, float):
        if v != v:                       # NaN
            return "NULL"
        return repr(round(v, 10))
    if isinstance(v, bytes):
        return "X'" + v.hex() + "'"
    return "'" + str(v).replace("'", "''") + "'"


def _tables(con: sqlite3.Connection) -> list[str]:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    return [r[0] for r in rows if r[0] not in ATLA]


def _pk_order(con: sqlite3.Connection, table: str) -> str:
    """Birincil anahtar sırası; yoksa tüm kolonlar (yine de deterministik)."""
    cols = con.execute(f"PRAGMA table_info({table})").fetchall()
    pk = [c[1] for c in sorted((c for c in cols if c[5]), key=lambda c: c[5])]
    return ", ".join(pk or [c[1] for c in cols])


def dump(cfg: dict, out_path: str | Path | None = None) -> Path:
    """Veritabanını deterministik SQL metnine yazar. Yazılan yolu döner.

    Bağlantı SALT-OKUNUR: bir "dump" işleminin şema uygulaması ya da migration
    ilerletmesi beklenmez. İlk sürüm `db.connect(cfg)` çağırıyordu, yani
    okumak için açılan bir komut yazma yapıyordu.
    """
    con = db.connect(cfg, readonly=True)
    p = util.ensure_parent(out_path or cfg["paths"]["db_dump"])

    parts: list[str] = [
        "-- BIST analiz — deterministik SQL dump.",
        "-- Elle düzenleme. `bist db dump` ile üretilir, `bist db restore` ile geri yüklenir.",
        f"-- şema sürümü: {con.execute('PRAGMA user_version').fetchone()[0]}",
        "PRAGMA foreign_keys = OFF;",
        "BEGIN TRANSACTION;",
    ]

    for t in _tables(con):
        cols = [c[1] for c in con.execute(f"PRAGMA table_info({t})").fetchall()]
        rows = con.execute(f"SELECT {','.join(cols)} FROM {t} ORDER BY {_pk_order(con, t)}")
        parts.append(f"-- ---- {t} ----")
        n = 0
        for row in rows:
            vals = ",".join(_quote(v) for v in row)
            parts.append(f"INSERT INTO {t} ({','.join(cols)}) VALUES ({vals});")
            n += 1
        parts.append(f"-- {t}: {n} satır")

    parts += ["COMMIT;", ""]
    con.close()

    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text("\n".join(parts), encoding="utf-8")
    tmp.replace(p)
    return p


def restore(cfg: dict, in_path: str | Path | None = None) -> dict:
    """Dump'ı boş bir veritabanına geri yükler.

    Var olan veritabanının ÜZERİNE yazmaz — hedefte tablo doluysa hata verir.
    """
    p = util.resolve(in_path or cfg["paths"]["db_dump"])
    if not p.exists():
        raise FileNotFoundError(f"Dump bulunamadı: {p}")

    con = db.connect(cfg)
    dolu = [t for t in _tables(con)
            if (con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] or 0) > 0]
    if dolu:
        con.close()
        raise RuntimeError(
            f"Hedef veritabanı boş değil (dolu tablolar: {', '.join(dolu)}). "
            "Üzerine yazmamak için duruyorum — önce data/bist.db dosyasını taşı.")

    con.executescript(p.read_text(encoding="utf-8"))
    con.commit()
    sayim = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in _tables(con)}
    con.close()
    return sayim
