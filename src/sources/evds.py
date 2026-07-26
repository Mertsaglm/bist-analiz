"""TCMB EVDS adaptörü — makro bağlam (politika faizi, TÜFE, kur, enflasyon beklentisi).

İki hayati ayrıntı:

1. **Değerler NOKTA ondalıklıdır** ('45.71340000'). Türkçe virgül ayrıştırıcısı
   burada KULLANILMAZ — kullanılırsa 10 kat hata üretir ve sessizce geçer.

2. **Tarihler 'GG-AA-YYYY' gelir** ve ISO'ya çevrilmeden saklanırsa
   `ORDER BY date` kronolojik OLMAZ. Bu, fark edilmesi zor bir bozulmadır.

API anahtarı HEADER'da gönderilir (Nisan 2024 kuralı), query string'de değil.
Anahtar yoksa modül boş liste döner — rapor ilgili satırları GİZLER, uydurmaz.
"""

from __future__ import annotations

import logging
from datetime import date

import requests

from .. import util

log = logging.getLogger(__name__)

TIMEOUT = 30


def available() -> bool:
    return bool(util.env("EVDS_API_KEY"))


def _headers() -> dict:
    return {"key": util.env("EVDS_API_KEY") or "", "User-Agent": "bist-analiz/0.1"}


def _parse_value(raw) -> float | None:
    """EVDS değeri → float. NOKTA ondalık; TR ayrıştırıcı KULLANMA."""
    if raw is None or raw == "":
        return None
    try:
        return float(str(raw).strip())
    except ValueError:
        return None


def _ddmmyyyy(d: date | str) -> str:
    dt = util.parse_date(d) if isinstance(d, str) else d
    return dt.strftime("%d-%m-%Y")


def fetch_series(cfg: dict, series_code: str, *, start: str | None = None,
                 end: str | None = None) -> list[dict]:
    """Tek seri çeker → [{date, value}] (date ISO). Hata → boş liste."""
    ec = cfg["sources"]["evds"]
    if not available():
        log.info("EVDS_API_KEY yok — %s atlandı", series_code)
        return []

    start = start or ec["start_date"]
    end = end or _ddmmyyyy(date.today())
    url = (f"{ec['base']}/series={series_code}"
           f"&startDate={start}&endDate={end}&type=json")

    try:
        r = requests.get(url, headers=_headers(), timeout=TIMEOUT)
        r.raise_for_status()
        js = r.json()
    except Exception as e:                                       # noqa: BLE001
        log.warning("EVDS %s hata: %s", series_code, e)
        return []

    items = js.get("items", []) if isinstance(js, dict) else []
    field = series_code.replace(".", "_")
    out = []
    for it in items:
        iso = util.to_iso_date(it.get("Tarih"))
        if not iso:
            continue
        val = _parse_value(it.get(field, it.get(series_code)))
        out.append({"date": iso, "value": val})
    return out


def fetch_series_chunked(cfg: dict, series_code: str, *,
                         start_year: int | None = None) -> list[dict]:
    """Yıl yıl çeker — EVDS'nin ~1000 satır/istek sınırını aşar.

    Günlük seriler için kritik: 10 yıllık günlük seri tek istekte sessizce
    kırpılır ve eksik veri "veri yok" gibi değil, "seri kısaymış" gibi görünür.
    """
    ec = cfg["sources"]["evds"]
    ilk = start_year or int(util.to_iso_date(ec["start_date"])[:4])
    bu_yil = date.today().year
    out: list[dict] = []
    for yil in range(ilk, bu_yil + 1):
        out.extend(fetch_series(cfg, series_code,
                                start=f"01-01-{yil}", end=f"31-12-{yil}"))
    # Aynı tarih birden çok kez gelirse sonuncusu kalsın
    tekil = {r["date"]: r for r in out}
    return [tekil[d] for d in sorted(tekil)]
