"""Tahmin günlüğü — DEĞİŞMEZ kayıtlar.

Görev bölüşümü kolonda değil, KODDA zorlanır:

    KOD yazar   : skor, sıra, yüzdelik, plan fiyatları (giriş/stop/hedef/R:R),
                  pozisyon boyutu, zaman bariyeri, referans anları,
                  **confidence_p**
    Analist verir: signal, action, confidence (ENUM), veto_code, ve prose

`confidence_p`'yi kodun yazması kritik: LLM'e sayısal güven yazdırmak, kalibre
edilmemiş bir olasılığı ölçüm zincirine sokmak demektir. LLM enum verir,
config'teki harita sayıya çevirir. Harita değişirse geçmiş kayıtlar
DEĞİŞMEZ — yeni kayıtlar yeni haritayla yazılır ve fark izlenebilir kalır.

`(asof, ticker, run_id)` UNIQUE: aynı gün aynı hisse için ikinci bir yazma
çakışır. Journal düzeltilmez; yanlışsa yeni bir run açılır.
"""

from __future__ import annotations

from datetime import timedelta

import logging
import sqlite3
from dataclasses import asdict

from . import db, util

log = logging.getLogger(__name__)

PREDICTION_COLS = [
    "prediction_id", "run_id", "asof", "ticker",
    "score", "rank", "pct", "factor_set_version", "weights_hash",
    "indicator_set_version", "regime", "plan_id",
    "entry_low", "entry_high", "stop_price", "t1_price", "t2_price", "rr_at_t1",
    "time_barrier_date", "position_size_pct",
    "signal", "action", "confidence", "confidence_p", "veto_code",
    "thesis", "counter_scenario", "key_risk", "falsifier",
    "news_refs", "news_reading",
    "close_at_asof", "xu100_at_asof", "ew_index_at_asof", "atr14_at_asof",
    "created_utc",
]

# Analistin doldurabileceği alanların TAMAMI. Bu listede olmayan bir anahtar
# gelirse yazma reddedilir — sessizce yok saymak, LLM'in şemayı genişletmeye
# çalıştığını gizlerdi.
ANALIST_ALANLARI = {
    "signal", "action", "confidence", "veto_code",
    "thesis", "counter_scenario", "key_risk", "falsifier",
    "news_refs", "news_reading",
}


def create_run(cfg: dict, con: sqlite3.Connection, *, asof: str, tool: str,
               bundle_sha: str, output_path: str = "", model_hint: str | None = None,
               audit_passed: bool = True,
               hard_fail_codes: list[str] | None = None) -> str:
    """Bir analiz çalıştırması açar ve `run_id` döner."""
    mevcut = db.scalar(con, "SELECT COUNT(*) FROM llm_runs WHERE asof = ?", (asof,)) or 0
    run_id = f"{asof}-{tool}-{mevcut + 1}"
    db.upsert_many(
        con, "llm_runs",
        ["run_id", "asof", "tool", "model_hint", "bundle_sha", "output_path",
         "audit_passed", "hard_fail_codes", "created_utc"],
        [(run_id, asof, tool, model_hint, bundle_sha, output_path,
          1 if audit_passed else 0,
          util.json_dump(hard_fail_codes or [], pretty=False), util.utc_now_iso())])
    return run_id


def confidence_to_p(cfg: dict, confidence: str) -> float:
    """Enum → olasılık. **KOD yazar.** Kalibrasyon ölçülene kadar sabit harita."""
    harita = cfg["llm"]["guven_olasilik"]
    if confidence not in harita:
        raise ValueError(f"Bilinmeyen güven seviyesi: {confidence!r}")
    return float(harita[confidence])


def record(cfg: dict, con: sqlite3.Connection, *, run_id: str, asof: str,
           ticker: str, analist: dict, plan: dict | None = None,
           faktor: dict | None = None, regime: str = "neutral",
           referans: dict | None = None) -> str:
    """Tek tahmin kaydeder. Analistin yazamayacağı her alanı KOD doldurur."""
    fazla = set(analist) - ANALIST_ALANLARI
    if fazla:
        raise ValueError(
            f"Analist şemanın dışına yazmaya çalıştı: {sorted(fazla)}. "
            "Bu alanları KOD doldurur; sessizce yok saymak sorunu gizlerdi.")

    for zorunlu in ("signal", "action", "confidence"):
        if not analist.get(zorunlu):
            raise ValueError(f"Analist alanı eksik: {zorunlu}")

    enums = cfg["llm"]["enums"]
    for alan, anahtar in (("signal", "signal"), ("action", "action"),
                          ("confidence", "confidence")):
        if analist[alan] not in enums[anahtar]:
            raise ValueError(f"{alan} izinli enum dışında: {analist[alan]!r}")

    plan = plan or {}
    faktor = faktor or {}
    referans = referans or {}
    if referans.get("close") is None:
        raise ValueError(
            "referans['close'] zorunlu — tahminin yazıldığı andaki kapanış "
            "bilinmeden sonuç ölçülemez (slippage, alfa, getiri hepsi buna dayanır).")
    hedefler = plan.get("targets") or []
    pid = f"{asof}-{ticker}-{run_id.rsplit('-', 1)[-1]}"

    satir = (
        pid, run_id, asof, ticker,
        faktor.get("score"), faktor.get("rank"), faktor.get("pct"),
        cfg["faktorler"]["set_version"], faktor.get("weights_hash", ""),
        cfg["gostergeler"]["set_version"], regime,
        plan.get("plan_id"),
        plan.get("entry_low"), plan.get("entry_high"), plan.get("stop_price"),
        hedefler[0]["price"] if len(hedefler) > 0 else None,
        hedefler[1]["price"] if len(hedefler) > 1 else None,
        plan.get("rr_at_t1"),
        plan.get("time_barrier_date"), plan.get("position_size_pct"),
        analist["signal"], analist["action"], analist["confidence"],
        confidence_to_p(cfg, analist["confidence"]),          # KOD yazar
        analist.get("veto_code"),
        analist.get("thesis", ""), analist.get("counter_scenario", ""),
        analist.get("key_risk", ""), analist.get("falsifier", ""),
        util.json_dump(analist.get("news_refs") or [], pretty=False),
        analist.get("news_reading"),
        referans.get("close"), referans.get("xu100"),
        referans.get("ew_index"), referans.get("atr14"),
        util.utc_now_iso(),
    )
    # Plan referansı ÖNCEDEN doğrulanır. Aksi halde çıplak bir
    # "FOREIGN KEY constraint failed" alınır ve bu, tekrar-yazma hatasıyla
    # karıştırılır — iki farklı olguyu aynı mesajla raporlamak okuyanı
    # yanlış yere bakmaya iter (LESSONS L-003).
    plan_id = plan.get("plan_id")
    if plan_id and not db.scalar(
            con, "SELECT 1 FROM plan_options WHERE plan_id = ?", (plan_id,)):
        raise RuntimeError(
            f"plan_id '{plan_id}' `plan_options` tablosunda yok. Journal'a "
            "kaydetmeden ÖNCE planı sakla (`planner.store`) — tahmin, referans "
            "verdiği planın kaybolmasına dayanamaz.")

    try:
        # INSERT (upsert DEĞİL) — journal değişmezdir; çakışma sessizce
        # üzerine yazmak yerine hata vermelidir.
        con.execute(
            f"INSERT INTO predictions ({','.join(PREDICTION_COLS)}) "
            f"VALUES ({','.join('?' * len(PREDICTION_COLS))})", satir)
        con.commit()
    except sqlite3.IntegrityError as e:
        mesaj = str(e).lower()
        if "unique" in mesaj or "primary key" in mesaj:
            raise RuntimeError(
                f"Journal DEĞİŞMEZDİR — ({asof}, {ticker}, {run_id}) zaten var. "
                f"Düzeltme için yeni bir run aç.") from e
        raise RuntimeError(f"Journal yazılamadı ({asof}, {ticker}): {e}") from e
    return pid


def record_from_plan(cfg: dict, con: sqlite3.Connection, *, run_id: str,
                     asof: str, ticker: str, plan_option, analist: dict,
                     faktor: dict | None = None, regime: str = "neutral",
                     referans: dict | None = None) -> str:
    """`PlanOption` dataclass'ından kayıt — plan fiyatları BURADAN okunur."""
    return record(cfg, con, run_id=run_id, asof=asof, ticker=ticker,
                  analist=analist, plan=asdict(plan_option), faktor=faktor,
                  regime=regime, referans=referans)


# ---------------------------------------------------------------- sorgular
def open_predictions(con: sqlite3.Connection, asof: str | None = None) -> list[dict]:
    """Henüz sonucu çözülmemiş tahminler."""
    sql = ("SELECT p.* FROM predictions p "
           "LEFT JOIN outcomes o ON o.prediction_id = p.prediction_id "
           "WHERE o.prediction_id IS NULL")
    params: tuple = ()
    if asof:
        sql += " AND p.asof <= ?"
        params = (asof,)
    return db.fetch_all(con, sql + " ORDER BY p.asof, p.ticker", params)


def summary(con: sqlite3.Connection) -> dict:
    return {
        "tahmin": db.scalar(con, "SELECT COUNT(*) FROM predictions") or 0,
        "cozulen": db.scalar(con, "SELECT COUNT(*) FROM outcomes") or 0,
        "acik": len(open_predictions(con)),
        "run": db.scalar(con, "SELECT COUNT(*) FROM llm_runs") or 0,
        "ilk": db.scalar(con, "SELECT MIN(asof) FROM predictions"),
        "son": db.scalar(con, "SELECT MAX(asof) FROM predictions"),
    }


# ---------------------------------------------------------------- portföy
def set_holding(con: sqlite3.Connection, ticker: str, qty: float,
                avg_cost: float | None = None) -> None:
    """Elle güncellenen pozisyon kaydı.

    Neden gerekli: ölçümün en güçlü sinyali "azalt" tarafındaydı ve neyi
    tuttuğunu bilmeden azaltamazsın. Ayrıca HF-21 (olmayan pozisyonu satmak)
    bu tabloya dayanır.
    """
    if qty <= 0:
        con.execute("DELETE FROM holdings WHERE ticker = ?", (ticker.upper(),))
    else:
        con.execute(
            "INSERT OR REPLACE INTO holdings (ticker, qty, avg_cost, updated_utc) "
            "VALUES (?,?,?,?)", (ticker.upper(), qty, avg_cost, util.utc_now_iso()))
    con.commit()


def holdings(con: sqlite3.Connection) -> dict[str, dict]:
    return {r["ticker"]: r for r in db.fetch_all(con, "SELECT * FROM holdings")}


# ---------------------------------------------------------------- süreli veto
def aktif_vetolar(cfg: dict, con: sqlite3.Connection, asof: str,
                  cal=None) -> dict[str, list[dict]]:
    """`asof` gününde HÂLÂ GEÇERLİ olan vetolar — {ticker: [veto, ...]}.

    NE EKSİKTİ (2026-08-07, Merdiven'in "bypass" fikrinden): veto bir KOŞUYA
    bağlıydı, takvime değil. Bugün `haber_riski` diye veto edilen bir isim,
    hiçbir şey değişmeden yarın tertemiz görünüyordu — ertesi günün paketinde
    vetonun izi yoktu. ADR #008'den beri veto sistemin kalan ana ürünü; ömrü
    tek bir koşu kadar olamaz.

    Süre veto SEBEBİNE göre değişir (`config.llm.veto_suresi_gun`) ve İŞLEM
    GÜNÜ cinsindendir — H=20 ufkuyla aynı takvim. Duvar saati kullanmak, uzun
    tatillerde vetoyu erken düşürürdü (AGENTS.md §11 madde 6: zaman kaynağını
    açıkça belirt).

    `predictions` DEĞİŞMEZDİR ve veto oradan TÜRETİLİR — ayrı bir "vetolar"
    tablosu tutmak aynı gerçeği iki yerde saklamak olurdu ve ikisi ayrışırdı.
    """
    from .calendar_bist import BistCalendar

    sure = cfg["llm"]["veto_suresi_gun"]
    varsayilan = int(sure.get("varsayilan", 5))
    cal = cal or BistCalendar(cfg, con)
    # En geniş süre kadar geriye bak; daha eskisi hiçbir şekilde aktif olamaz.
    #
    # ⚠ Alt sınır TAKVİM GÜNÜYLE hesaplanır, işlem günüyle DEĞİL — bilerek.
    # `add_trading_days` geriye giderken bar bulamazsa (verinin başlangıcından
    # önce, ya da bir veri boşluğunda) sonsuza yürür. Burada gereken şey
    # kesinlik değil, YETERİNCE ERKEN bir sınır: bu yalnız taranacak satır
    # sayısını kısıtlar, hangi vetonun aktif olduğunu belirlemez. Kesinlik
    # gereken yer aşağıdaki `bitis` hesabıdır ve orası İLERİ gider (güvenli).
    enfazla = max([varsayilan] + [int(v) for k, v in sure.items()
                                  if k != "varsayilan"])
    bas = (util.parse_date(asof) - timedelta(days=enfazla * 2 + 14)).isoformat()

    # ⚠ (ticker, veto_code) başına TEK satır. Art arda koşan günlük analiz aynı
    # vetoyu her gün yeniden koyar; hepsini listelemek bilgi değil GÜRÜLTÜ
    # üretir (ölçüldü 2026-08-05: EUPWR'de `rejim_uyumsuz` dört kez). En GEÇ
    # biten kayıt tutulur — koruma en uzun süreye göre yaşar. Tekrar sayısı
    # atılmaz, `tekrar` alanına yazılır: "üç gün üst üste aynı veto" gerçek bir
    # bilgidir ve tek satıra sıkıştırılırken kaybedilmemeli.
    tekil: dict[tuple[str, str], dict] = {}
    for r in db.fetch_all(
            con,
            "SELECT p.ticker, p.asof, p.veto_code, p.key_risk, r.tool "
            "  FROM predictions p JOIN llm_runs r ON r.run_id = p.run_id "
            " WHERE p.veto_code IS NOT NULL AND p.asof <= ? AND p.asof >= ? "
            " ORDER BY p.asof DESC", (asof, bas)):
        gun = int(sure.get(r["veto_code"], varsayilan))
        bitis = cal.add_trading_days(r["asof"], gun).isoformat()
        if bitis < asof:
            continue                       # süresi dolmuş
        k = (r["ticker"], r["veto_code"])
        onceki = tekil.get(k)
        if onceki is None:
            tekil[k] = {
                "veto_code": r["veto_code"], "konuldu": r["asof"], "bitis": bitis,
                "kalan_islem_gunu": cal.trading_days_between(asof, bitis),
                "arac": r["tool"], "gerekce": r["key_risk"], "tekrar": 1,
            }
        else:
            onceki["tekrar"] += 1
            if bitis > onceki["bitis"]:    # en GEÇ biten kazanır
                onceki.update(konuldu=r["asof"], bitis=bitis, arac=r["tool"],
                              gerekce=r["key_risk"],
                              kalan_islem_gunu=cal.trading_days_between(asof, bitis))

    out: dict[str, list[dict]] = {}
    for (t, _), v in tekil.items():
        out.setdefault(t, []).append(v)
    for v in out.values():
        v.sort(key=lambda x: (-x["kalan_islem_gunu"], x["veto_code"]))
    return out
