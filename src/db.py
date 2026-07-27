"""SQLite şeması ve bağlantı.

Tek `SCHEMA` string'i; `connect()` her çağrıda uygular (IF NOT EXISTS) ve
`migrations.apply()` ile sürüm ilerletir.

Şemanın en önemli kararı `bars_daily` içindeki İKİ fiyat serisidir:
    c     → bölünme düzeltmeli, temettü düzeltmesiz  → SEVİYE / ATR / PLAN
    c_tr  → toplam getiri (Adj Close)                → GETİRİ / MOMENTUM / FAKTÖR
Ölçüm (2026-07-26): TUPRS 2025-03-28'de ham getiri −%2.95, düzeltilmiş +%2.67.
İkisi gerçekten ayrışıyor; yanlışını kullanmak ya seviyeleri ya momentumu
SESSİZCE bozar. Kolon yorumları bu yüzden burada duruyor.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from . import util

SCHEMA_VERSION = 1

SCHEMA = """
-- ======================== Evren ========================
CREATE TABLE IF NOT EXISTS universe (
    ticker      TEXT PRIMARY KEY,           -- 'THYAO' (.IS eki YOK)
    yf_symbol   TEXT NOT NULL,              -- 'THYAO.IS'
    name        TEXT,
    sector      TEXT NOT NULL,
    tier        TEXT NOT NULL,              -- cekirdek|sanayi|firsat|yuksek_risk|test_vakasi
    in_live     INTEGER NOT NULL DEFAULT 1, -- canlı sinyal evreninde mi
    in_measure  INTEGER NOT NULL DEFAULT 1, -- ağırlık kalibrasyonuna girer mi (>=~8y geçmiş)
    listed_from TEXT,
    notes       TEXT
);

-- ======================== Fiyat ========================
CREATE TABLE IF NOT EXISTS bars_daily (
    ticker       TEXT NOT NULL,
    date         TEXT NOT NULL,   -- ISO YYYY-MM-DD, BIST yerel işlem günü
    o REAL, h REAL, l REAL, c REAL,  -- bölünme düzeltmeli / temettü düzeltmesiz
    v            REAL,
    c_tr         REAL,            -- toplam getiri serisi (Adj Close)
    turnover_try REAL,            -- c * v
    source       TEXT NOT NULL,
    ingested_utc TEXT NOT NULL,
    PRIMARY KEY (ticker, date)
);
CREATE INDEX IF NOT EXISTS idx_bars_date ON bars_daily(date);

CREATE TABLE IF NOT EXISTS index_daily (
    symbol TEXT NOT NULL,         -- 'XU100'|'XU030'|'XBANK'|'XUSIN'|'USDTRY'
    date   TEXT NOT NULL,
    o REAL, h REAL, l REAL, c REAL,
    ingested_utc TEXT NOT NULL,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS corporate_actions (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,         -- ex-tarih
    kind   TEXT NOT NULL,         -- temettu|bolunme|bedelsiz|bilinmeyen
    value  REAL NOT NULL,         -- temettü: TL/pay; bölünme: oran
    source TEXT NOT NULL,         -- yfinance|kap|manuel
    PRIMARY KEY (ticker, date, kind)
);

-- Kayıt bazlı kalite kapısı. Ölçüm: gerçek kusurlar genel değil ticker-spesifik
-- (SASA 505 barın 117'sinde sıfır hacim = %23.2; diğerleri %0.6).
CREATE TABLE IF NOT EXISTS data_quality (
    ticker             TEXT NOT NULL,
    date               TEXT NOT NULL,   -- değerlendirmenin yapıldığı gün
    bars_252           INTEGER,
    zero_vol_ratio_252 REAL,
    max_gap_days       INTEGER,
    stale_close_days   INTEGER,
    unexplained_jump   INTEGER,         -- |getiri|>eşik ve kayıtlı kurumsal işlem yok
    ok                 INTEGER NOT NULL,
    reasons            TEXT,            -- JSON liste
    PRIMARY KEY (ticker, date)
);

-- ======================== Analitik (dondurulmuş) ========================
-- ⚠ `indicator_daily` KESİTSEL İSTATİSTİKLERİN PAYDASIDIR. `factors._panel` ve
-- `regime.breadth` buraya JOIN atar; göstergesi hesaplanmamış bir ticker
-- SESSİZCE satır üretmez ve kesit daralır — hata yok, uyarı yok, sadece
-- daha küçük bir popülasyon. Ölçüldü (2026-07-27): tablo 70 ticker'ın 19'unu
-- kapsıyordu, dolayısıyla 67 isimlik ölçüm evreni istenirken 16 isimle
-- skorlanıyor ve piyasa genişliği 5/16 = %31 çıkıp rejimi `risk-off`
-- yapıyordu. Evren her değiştiğinde `bist gosterge` YENİDEN koşulmalı;
-- paket artık paydayı `kesit` ve `rejim.genislik_n` alanlarında yazıyor.
CREATE TABLE IF NOT EXISTS indicator_daily (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,
    set_version TEXT NOT NULL,          -- 'core_indicators_v1'
    sma20 REAL, sma50 REAL, sma200 REAL, ema12 REAL, ema26 REAL,
    rsi14 REAL, macd REAL, macd_signal REAL, macd_hist REAL,
    bb_mid REAL, bb_up REAL, bb_low REAL, bb_pctb REAL, bb_width REAL,
    atr14 REAL, atr_pct REAL, adx14 REAL, di_plus REAL, di_minus REAL,
    high_52w REAL, low_52w REAL, dist_high52_pct REAL,
    vol_ann_63 REAL, turnover_med_63 REAL,
    ret_21 REAL, ret_63 REAL, ret_126 REAL, ret_252 REAL,   -- c_tr üzerinden
    -- Trend KAPISI toplam getiri uzayında: `c` üzerinden SMA200, pencerede
    -- birikmiş temettü kadar yukarıda kalmış fiyatların ortalamasıdır ve
    -- fiyatı sistematik olarak altında gösterir (bkz. migrations._m002).
    sma50_tr REAL, sma200_tr REAL,
    computed_utc TEXT NOT NULL,
    PRIMARY KEY (ticker, date, set_version)
);

CREATE TABLE IF NOT EXISTS levels_daily (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,
    set_version TEXT NOT NULL,
    payload TEXT NOT NULL,   -- JSON [{price,kind,touches,score,first_date,last_date}]
    PRIMARY KEY (ticker, date, set_version)
);

CREATE TABLE IF NOT EXISTS factor_daily (
    ticker TEXT NOT NULL,
    date   TEXT NOT NULL,
    set_version  TEXT NOT NULL,   -- 'factors_v1'
    weights_hash TEXT NOT NULL,   -- hangi ağırlık setiyle üretildi
    mom_6_1 REAL, mom_12_1 REAL, high52_prox REAL, volscaled_mom REAL,
    z_mom_6_1 REAL, z_mom_12_1 REAL, z_high52_prox REAL, z_volscaled_mom REAL,
    score REAL, rank INTEGER, pct REAL,
    eligible INTEGER NOT NULL,
    gate_reasons TEXT,            -- JSON liste
    PRIMARY KEY (ticker, date, set_version, weights_hash)
);

CREATE TABLE IF NOT EXISTS evds_daily (
    date        TEXT NOT NULL,
    series_code TEXT NOT NULL,
    value       REAL,
    PRIMARY KEY (date, series_code)
);

CREATE TABLE IF NOT EXISTS regime_daily (
    date TEXT PRIMARY KEY,
    label TEXT NOT NULL,          -- risk-on|neutral|transition|risk-off
    xu100_vs_sma200_pct REAL,
    breadth_above_sma50_pct REAL,
    xu100_vol_ann_21 REAL,
    usdtry_vol_ann_21 REAL,
    policy_rate REAL, cpi_yoy REAL, inflation_exp_12m REAL, real_rate REAL,
    cash_pct REAL, max_positions INTEGER, size_multiplier REAL,
    inputs TEXT                   -- JSON: hangi girdi hangi değer (denetlenebilirlik)
);

-- ======================== Plan menüsü ========================
CREATE TABLE IF NOT EXISTS plan_options (
    plan_id TEXT PRIMARY KEY,     -- 'THYAO-2026-07-27-A'
    asof    TEXT NOT NULL,
    ticker  TEXT NOT NULL,
    kind    TEXT NOT NULL,
    payload TEXT NOT NULL,        -- PlanOption JSON
    created_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_plan_asof ON plan_options(asof, ticker);

-- ======================== LLM çalıştırmaları ========================
CREATE TABLE IF NOT EXISTS llm_runs (
    run_id     TEXT PRIMARY KEY,  -- '<asof>-<tool>-<n>'
    asof       TEXT NOT NULL,
    tool       TEXT NOT NULL,
    model_hint TEXT,
    bundle_sha TEXT NOT NULL,     -- çıktı bunu birebir taşımalı (HF-02)
    output_path TEXT NOT NULL,
    audit_passed INTEGER NOT NULL,
    hard_fail_codes TEXT,
    created_utc TEXT NOT NULL
);

-- ======================== Tahmin günlüğü (DEĞİŞMEZ) ========================
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES llm_runs(run_id),
    asof   TEXT NOT NULL,
    ticker TEXT NOT NULL,
    -- --- deterministik alanlar: KOD yazar, LLM ASLA ---
    -- NULL kabul eder: "bu isim skorlanmadı" GERÇEK bir durumdur (ölçüm evreni
    -- dışı isimler). NOT NULL bırakmak bilinmeyeni sayıya çevirmeye zorlardı.
    score REAL, rank INTEGER, pct REAL,
    factor_set_version TEXT NOT NULL, weights_hash TEXT NOT NULL,
    indicator_set_version TEXT NOT NULL, regime TEXT NOT NULL,
    plan_id TEXT REFERENCES plan_options(plan_id),
    entry_low REAL, entry_high REAL, stop_price REAL,
    t1_price REAL, t2_price REAL, rr_at_t1 REAL,
    time_barrier_date TEXT, position_size_pct REAL,
    -- --- LLM'den gelen: SADECE enum + prose ---
    signal     TEXT NOT NULL,     -- strong_buy|buy|accumulate|hold|reduce|sell|avoid
    action     TEXT NOT NULL,     -- plan_sec|plan_reddet|izle|islem_yok
    confidence TEXT NOT NULL,     -- yuksek|orta|dusuk  (SAYI DEĞİL)
    confidence_p REAL NOT NULL,   -- KOD yazar: config enum→olasılık haritasından
    veto_code TEXT,
    thesis TEXT NOT NULL, counter_scenario TEXT NOT NULL,
    key_risk TEXT NOT NULL, falsifier TEXT NOT NULL,
    news_refs TEXT, news_reading TEXT,
    -- --- referans anları: KOD yazar ---
    close_at_asof REAL NOT NULL,
    xu100_at_asof REAL,
    ew_index_at_asof REAL,
    atr14_at_asof REAL,
    created_utc TEXT NOT NULL,
    UNIQUE (asof, ticker, run_id)
);
CREATE INDEX IF NOT EXISTS idx_pred_asof ON predictions(asof);

-- ======================== Sonuçlar (YALNIZ KOD YAZAR) ========================
-- Bu tabloda LLM'in yazabileceği TEK kolon yoktur. Kendi ödevini notlandıran
-- sistem kaçınılmaz olarak kayar.
CREATE TABLE IF NOT EXISTS outcomes (
    prediction_id TEXT PRIMARY KEY REFERENCES predictions(prediction_id),
    resolved_date TEXT NOT NULL,
    resolution    TEXT NOT NULL,  -- hedef|stop|sure|giris_olmadi|iptal_kurumsal|iptal_veri
    entry_date TEXT, entry_price REAL,
    exit_date  TEXT, exit_price  REAL,
    holding_days INTEGER,
    ret_pct REAL,                 -- maliyet dahil
    ret_pct_gross REAL,
    -- Boyutlandırma karşı-olgusu: PORTFÖY KATKISI (hisse getirisi DEĞİL),
    -- pozisyon `maks_pozisyon_pct` ile açılsaydı ne olurdu. Gerçekleşen katkı
    -- `predictions.position_size_pct` ile hesaplanır; ikisinin farkı rejim
    -- boyutlandırmasının değeridir. NULL = boyut bilinmiyor, ölçülemez.
    ret_pct_equal_size REAL,
    xu100_ret_pct REAL,
    ew_universe_ret_pct REAL,
    alpha_vs_xu100 REAL,          -- İKİNCİL — sermaye-ağırlık eğilimi içerir
    alpha_vs_ew REAL,             -- BİRİNCİL METRİK
    fwd_ret_20d REAL,             -- plandan bağımsız saf faktör ölçümü (IC için)
    fwd_alpha_20d_ew REAL,
    slippage_pct REAL,            -- planlanan giriş vs gerçekleşebilir giriş
    hit INTEGER,                  -- Brier için
    error_tag TEXT,               -- kural tabanlı, KOD atar
    resolver_version TEXT NOT NULL,
    resolved_utc TEXT NOT NULL
);

-- ======================== Portföy (elle güncellenir) ========================
CREATE TABLE IF NOT EXISTS holdings (
    ticker TEXT PRIMARY KEY,
    qty REAL NOT NULL,
    avg_cost REAL,
    updated_utc TEXT
);

-- ======================== Haber / KAP (Faz 7) ========================
-- ⚠ Bu taban tanım migration v5 tarafından DEĞİŞTİRİLİR: bir bildirim birden
-- çok hisseye ait olabildiği için birincil anahtar (disclosure_id, ticker)
-- olur ve importance/summary/company kolonları eklenir. v6 ise published_utc'yi
-- İstanbul yerel saatinden gerçek UTC'ye çevirir. Güncel şema için
-- `migrations._m005` / `_m006`'ya bak.
CREATE TABLE IF NOT EXISTS disclosures (
    disclosure_id TEXT PRIMARY KEY,
    ticker TEXT,
    published_utc TEXT NOT NULL,  -- +00:00 ekli UTC (v6 sonrası)
    tier INTEGER NOT NULL,        -- 1=KAP resmî, 2=kurumsal ajans, 3=diğer
    title TEXT, url TEXT, category TEXT, raw TEXT
);
CREATE INDEX IF NOT EXISTS idx_disc_ticker ON disclosures(ticker, published_utc);
"""


def db_path(cfg: dict) -> Path:
    return util.resolve(cfg["paths"]["db"])


def connect(cfg: dict, *, readonly: bool = False) -> sqlite3.Connection:
    """Bağlantı açar; `readonly=False` ise şemayı uygular ve migration'ları ilerletir.

    ⚠ `readonly=True` GERÇEKTEN salt-okunur bir bağlantı açar (`mode=ro`).
    İlk sürüm yalnız şema uygulamayı atlıyordu — yani "readonly" adlı bir
    bağlantıyla veritabanına pekâlâ yazılabiliyordu. Adı doğru davranışı
    yanlış bir bayrak, onu okuyan bir sonraki kişiyi yanıltır.
    """
    from . import migrations

    p = util.ensure_parent(db_path(cfg))
    if readonly:
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=30.0)
        con.row_factory = sqlite3.Row
        return con

    con = sqlite3.connect(p, timeout=30.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.executescript(SCHEMA)
    migrations.apply(con)
    con.commit()
    return con


# ---------------------------------------------------------------- yardımcılar
def upsert_many(con: sqlite3.Connection, table: str, cols: list[str],
                rows: list[tuple]) -> int:
    """INSERT OR REPLACE toplu yazma. Yazılan satır sayısını döner."""
    if not rows:
        return 0
    ph = ",".join("?" * len(cols))
    sql = f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({ph})"
    con.executemany(sql, rows)
    con.commit()
    return len(rows)


def fetch_all(con: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in con.execute(sql, params).fetchall()]


def fetch_one(con: sqlite3.Connection, sql: str, params: tuple = ()) -> dict | None:
    row = con.execute(sql, params).fetchone()
    return dict(row) if row else None


def scalar(con: sqlite3.Connection, sql: str, params: tuple = ()):
    row = con.execute(sql, params).fetchone()
    return row[0] if row else None
