"""LLM girdi/çıktı sözleşmesi — saf tanımlar, harici jsonschema yok.

**Bu dosyanın tek cümlesi: LLM hesaplanabilir hiçbir sayıyı üretmez.**

Çıktı şemasında fiyat / hedef / stop / giriş / pozisyon boyutu / R:R /
sayısal güven alanı **YOKTUR**. Analist bir `plan_id` seçer, enum verir,
prose yazar. Journal'a giren her sayı `plan_options` ya da `factor_daily`
tablosundan okunur.

Ama şemada alan olmaması yalnız YAPISAL sızıntıyı durdurur. Asıl hata modu
metinseldir: modelin tez cümlesine *"324 TL civarında bir hedef makul"*
yazması. Onu HF-17 durdurur (bkz. `audit.py`) — taşıyıcı kol odur.
"""

from __future__ import annotations

BUNDLE_VERSION = "bist_bundle_v1"
OUTPUT_SCHEMA_VERSION = "bist_llm_v1"

# Analistin yazabileceği alanların TAMAMI — bu listenin dışı yasak.
STOCK_ALANLARI = {
    "ticker", "signal", "action", "selected_plan_id", "veto_code",
    "confidence", "thesis", "counter_scenario", "key_risk", "falsifier",
    "news_refs", "news_reading",
}
STOCK_ZORUNLU = {"ticker", "signal", "action", "confidence",
                 "thesis", "counter_scenario", "key_risk", "falsifier"}
STOCK_PROSE = ("thesis", "counter_scenario", "key_risk", "falsifier", "news_reading")

MARKET_ALANLARI = {"regime_agreement", "regime_note", "portfolio_action"}
TOP_ALANLARI = {"schema_version", "asof", "bundle_sha", "tool",
                "market_view", "stocks", "not_covered", "analyst_notes"}

# ⚠ Bu alanlardan HERHANGİ BİRİ çıktıda görünürse model sayı üretmeye
# çalışıyordur. Liste savunma amaçlı geniş tutulmuştur.
YASAK_SAYISAL_ALANLAR = {
    "entry", "entry_low", "entry_high", "entry_price", "stop", "stop_price",
    "stop_loss", "target", "targets", "t1", "t2", "t3", "t1_price", "t2_price",
    "price", "hedef", "hedef_fiyat", "position_size", "position_size_pct",
    "size", "boyut", "rr", "risk_reward", "rr_at_t1", "confidence_pct",
    "confidence_p", "probability", "olasilik", "guven_yuzde", "score", "skor",
    "expected_return", "beklenen_getiri", "atr", "stop_atr_multiple",
}


def output_iskelet(asof: str, bundle_sha: str, tool: str) -> dict:
    """Analistin dolduracağı boş çıktı iskeleti — prompt'a örnek olarak konur."""
    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "asof": asof,
        "bundle_sha": bundle_sha,
        "tool": tool,
        "market_view": {
            "regime_agreement": "katiliyorum|katilmiyorum",
            "regime_note": "<≤400 karakter>",
            "portfolio_action": "risk_azalt|koru|risk_artir",
        },
        "stocks": [{
            "ticker": "THYAO",
            "signal": "strong_buy|buy|accumulate|hold|reduce|sell|avoid",
            "action": "plan_sec|plan_reddet|izle|islem_yok",
            "selected_plan_id": "<plan_ids listesinden VEYA null>",
            "veto_code": "<action=plan_reddet ise zorunlu, yoksa null>",
            "confidence": "yuksek|orta|dusuk",
            "thesis": "<prose>",
            "counter_scenario": "<prose>",
            "key_risk": "<prose>",
            "falsifier": "<5 işlem gününde GÖZLEMLENEBİLİR bir olay>",
            "news_refs": [],
            "news_reading": None,
        }],
        "not_covered": [],
        "analyst_notes": "",
    }


def kurallar_ozeti() -> list[str]:
    """Prompt'un başına konan sert kurallar — denetimle birebir eşleşir."""
    return [
        "Hiçbir sayı ÜRETME. Prose içinde kullandığın her sayı bu paketten "
        "BİREBİR gelmeli; paket dışı sayı denetimde reddedilir (HF-17).",
        "Fiyat / stop / hedef / pozisyon boyutu YAZMA — `selected_plan_id` seç, "
        "sayılar plandan okunur.",
        "Güveni yüzde olarak verme; `yuksek|orta|dusuk` enum'u kullan.",
        "Evrendeki HER hisse ya `stocks[]` içinde ya `not_covered` içinde olmalı.",
        "`falsifier`: 5 işlem günü içinde GÖZLEMLENEBİLİR bir olay yaz. "
        "Jenerik cümle yazma; şablon tespiti var (HF-27).",
        "Haber yorumu yapıyorsan `news_refs`'e paketteki haber id'lerini koy. "
        "Pakette olmayan id uydurma (HF-28).",
        "Bir planı beğenmiyorsan `plan_reddet` + `veto_code` kullan — bu gerçek "
        "bir karardır ve performansı ölçülür.",
        "Bu sistemde ÖLÇÜLEN KENAR YOKTUR (ADR #008). Seviyeler planlama "
        "geometrisidir; yön iddiası üretme.",
    ]
