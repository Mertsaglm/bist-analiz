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


def _m003(con: sqlite3.Connection) -> None:
    """predictions.score/rank/pct → NULL kabul eder.

    Gerekçe: "bu isim skorlanmadı" GERÇEK bir durumdur (ölçüm evreni dışındaki
    ASTOR/EUPWR gibi isimler, ya da gösterge penceresi dolmamış hisseler).
    NOT NULL bırakmak, bilinmeyeni sayıya çevirmeye zorlar — yani tam da bu
    projenin yasakladığı şeye: veri yokken veri uydurmaya.

    SQLite ALTER ile NOT NULL kaldıramaz → tablo yeniden kurulur ve kopyalanır.

    ⚠ TUZAK (testle yakalandı): SQLite varsayılan olarak `ALTER TABLE RENAME`
    sırasında DİĞER tabloların FK referanslarını da yeniden yazar. `predictions`
    → `predictions_eski` yeniden adlandırılınca `outcomes` tablosunun FK'sı da
    `predictions_eski`'yi işaret etmeye başlıyor; eski tablo silinince
    `outcomes` üzerindeki her sorgu "no such table: predictions_eski" ile
    patlıyordu. `legacy_alter_table = ON` bu yeniden yazmayı kapatır.
    """
    kolonlar = [r[1] for r in con.execute("PRAGMA table_info(predictions)")]
    if not kolonlar:
        return
    ph = ",".join(kolonlar)
    con.executescript(f"""
        PRAGMA foreign_keys = OFF;
        PRAGMA legacy_alter_table = ON;
        ALTER TABLE predictions RENAME TO predictions_eski;
        CREATE TABLE predictions (
            prediction_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL REFERENCES llm_runs(run_id),
            asof   TEXT NOT NULL,
            ticker TEXT NOT NULL,
            score REAL, rank INTEGER, pct REAL,
            factor_set_version TEXT NOT NULL, weights_hash TEXT NOT NULL,
            indicator_set_version TEXT NOT NULL, regime TEXT NOT NULL,
            plan_id TEXT REFERENCES plan_options(plan_id),
            entry_low REAL, entry_high REAL, stop_price REAL,
            t1_price REAL, t2_price REAL, rr_at_t1 REAL,
            time_barrier_date TEXT, position_size_pct REAL,
            signal     TEXT NOT NULL,
            action     TEXT NOT NULL,
            confidence TEXT NOT NULL,
            confidence_p REAL NOT NULL,
            veto_code TEXT,
            thesis TEXT NOT NULL, counter_scenario TEXT NOT NULL,
            key_risk TEXT NOT NULL, falsifier TEXT NOT NULL,
            news_refs TEXT, news_reading TEXT,
            close_at_asof REAL NOT NULL,
            xu100_at_asof REAL, ew_index_at_asof REAL, atr14_at_asof REAL,
            created_utc TEXT NOT NULL,
            UNIQUE (asof, ticker, run_id)
        );
        INSERT INTO predictions ({ph}) SELECT {ph} FROM predictions_eski;
        DROP TABLE predictions_eski;
        CREATE INDEX IF NOT EXISTS idx_pred_asof ON predictions(asof);
        PRAGMA legacy_alter_table = OFF;
        PRAGMA foreign_keys = ON;
    """)


def _m004(con: sqlite3.Connection) -> None:
    """v3'ün bozduğu `outcomes` FK'sını onarır.

    v3 ilk sürümü `legacy_alter_table` olmadan koştuğu için `outcomes`
    referansı silinmiş bir tabloya kaldı. Bu migration onu yeniden kurar.
    Zaten sağlam olan veritabanlarında zararsızdır (aynı şemayı kurar).

    Not: v3 yayımlanmamıştı ama düzeltmesi yine de AYRI bir adım olarak
    yazıldı — çünkü v3'ü ALMIŞ bir veritabanı (bu makine) mevcut ve
    yayımlanmış migration'ı geçmişe dönük değiştirmek, farklı makinelerde
    sessizce ayrışan şemalar demektir.
    """
    sql = con.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='outcomes'"
    ).fetchone()
    if not sql or "predictions_eski" not in (sql[0] or ""):
        return
    kolonlar = [r[1] for r in con.execute("PRAGMA table_info(outcomes)")]
    ph = ",".join(kolonlar)
    duzeltilmis = sql[0].replace("predictions_eski", "predictions")
    con.executescript(f"""
        PRAGMA foreign_keys = OFF;
        PRAGMA legacy_alter_table = ON;
        ALTER TABLE outcomes RENAME TO outcomes_eski;
        {duzeltilmis};
        INSERT INTO outcomes ({ph}) SELECT {ph} FROM outcomes_eski;
        DROP TABLE outcomes_eski;
        PRAGMA legacy_alter_table = OFF;
        PRAGMA foreign_keys = ON;
    """)


def _m005(con: sqlite3.Connection) -> None:
    """disclosures: (disclosure_id, ticker) bileşik anahtar + önem/özet kolonları.

    Bir KAP bildirimi BİRDEN ÇOK hisseye ait olabilir (ör. holding + bağlı
    ortaklık). Tek `disclosure_id` birincil anahtarı bunu temsil edemiyordu:
    ya bildirim tek hisseye zorlanır ya da diğerleri sessizce düşerdi.
    """
    con.executescript("""
        PRAGMA foreign_keys = OFF;
        PRAGMA legacy_alter_table = ON;
        DROP TABLE IF EXISTS disclosures;
        CREATE TABLE disclosures (
            disclosure_id TEXT NOT NULL,
            ticker        TEXT NOT NULL,
            published_utc TEXT NOT NULL,
            tier          INTEGER NOT NULL,   -- 1 = KAP (resmî beyan)
            importance    TEXT,               -- yuksek|orta|dusuk (HEURİSTİK, ölçülmedi)
            title TEXT, summary TEXT, url TEXT, category TEXT, company TEXT,
            fetched_utc TEXT NOT NULL,
            PRIMARY KEY (disclosure_id, ticker)
        );
        CREATE INDEX IF NOT EXISTS idx_disc_ticker
            ON disclosures(ticker, published_utc);
        CREATE INDEX IF NOT EXISTS idx_disc_tarih ON disclosures(published_utc);
        PRAGMA legacy_alter_table = OFF;
        PRAGMA foreign_keys = ON;
    """)


MIGRATIONS: list[Migration] = [
    (2, "indicator_daily: sma50_tr / sma200_tr (trend kapısı toplam getiri uzayında)", _m002),
    (3, "predictions.score/rank/pct nullable — 'skorlanmadı' gerçek bir durumdur", _m003),
    (4, "v3'ün bozduğu outcomes FK'sını onar (legacy_alter_table tuzağı)", _m004),
    (5, "disclosures: (disclosure_id, ticker) bileşik anahtar + önem/özet", _m005),
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
