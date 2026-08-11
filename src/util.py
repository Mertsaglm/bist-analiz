"""Paylaşılan çekirdek: config/env yükleme, JSON io, tarih ve sayı yardımcıları.

Buraya iş mantığı GİRMEZ. Bir fonksiyon "BIST" veya "faktör" kelimesini biliyorsa
yanlış modüldedir.
"""

from __future__ import annotations

import json
import os
import hashlib
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

# Proje kökü — src/util.py'nin bir üstü. Tüm göreli yollar buna göre çözülür.
ROOT = Path(__file__).resolve().parent.parent

_CONFIG_CACHE: dict[str, dict] = {}


# ---------------------------------------------------------------- yollar
def resolve(rel: str | Path) -> Path:
    """Göreli yolu proje köküne göre çözer. Mutlak yol verilirse dokunmaz."""
    p = Path(rel)
    return p if p.is_absolute() else ROOT / p


def ensure_parent(path: str | Path) -> Path:
    p = resolve(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------- config / env
def load_yaml(path: str | Path) -> dict:
    p = resolve(path)
    with p.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_config(path: str | Path = "config.yaml", *, fresh: bool = False) -> dict:
    """config.yaml'ı yükler ve önbellekler.

    Tüm eşik/oran/URL burada. Kod içine sabit gömülmez — bir eşiği değiştirmek
    isteyen tek yere bakar.
    """
    key = str(resolve(path))
    if fresh or key not in _CONFIG_CACHE:
        _CONFIG_CACHE[key] = load_yaml(path)
    return _CONFIG_CACHE[key]


def load_env(path: str | Path = ".env") -> None:
    """Bağımlılıksız .env yükleyici.

    `setdefault` kullanır: gerçek ortam değişkeni dosyadaki değeri EZER.
    Bu sayede CI'da secret enjekte etmek yerel .env'i geçersiz kılar.
    """
    p = resolve(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def env(name: str, default: str | None = None) -> str | None:
    load_env()
    val = os.environ.get(name, default)
    return val if val else default


# ---------------------------------------------------------------- JSON
class _Encoder(json.JSONEncoder):
    """numpy / pandas / Path / datetime farkında kodlayıcı.

    NaN'ı None'a çevirir — `json.dumps` varsayılanı geçersiz JSON olan çıplak
    `NaN` literali üretir ve bunu okuyan her araç patlar.
    """

    def default(self, o: Any) -> Any:  # noqa: D102
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, Path):
            return str(o)
        if hasattr(o, "item"):  # numpy skaler
            try:
                return o.item()
            except Exception:
                pass
        if hasattr(o, "isoformat"):  # pandas.Timestamp
            return o.isoformat()
        if hasattr(o, "tolist"):  # numpy dizi
            return o.tolist()
        return str(o)


def _clean_nan(obj: Any) -> Any:
    """NaN/Inf → None. json.dumps bunları geçersiz JSON olarak yazar."""
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean_nan(v) for v in obj]
    if isinstance(obj, float):
        if obj != obj or obj in (float("inf"), float("-inf")):
            return None
    return obj


def json_dump(obj: Any, *, pretty: bool = True, canonical: bool = False) -> str:
    """JSON metni üretir.

    canonical=True: sha hesabı için kararlı biçim (sıralı anahtar, sabit ayraç).
    Aynı içerik daima aynı metni ve dolayısıyla aynı sha'yı verir.
    """
    obj = _clean_nan(obj)
    if canonical:
        return json.dumps(obj, cls=_Encoder, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":"))
    kw = {"indent": 2} if pretty else {"separators": (",", ":")}
    return json.dumps(obj, cls=_Encoder, ensure_ascii=False, **kw)


def read_json(path: str | Path, default: Any = None) -> Any:
    p = resolve(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: str | Path, obj: Any, *, pretty: bool = True) -> Path:
    """ATOMİK yazma: geçici dosya + rename.

    Doğrudan write_text yarım dosya bırakabilir (süreç ölürse). Journal ve
    plan menüsü gibi dosyalarda yarım dosya sessiz veri kaybıdır.
    """
    p = ensure_parent(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json_dump(obj, pretty=pretty) + "\n", encoding="utf-8")
    tmp.replace(p)
    return p


def sha256_canonical(obj: Any) -> str:
    """İçeriğin kararlı sha256'sı. Anahtar sırası ve boşluk etkilemez."""
    return hashlib.sha256(json_dump(obj, canonical=True).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- zaman
def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().replace(microsecond=0).isoformat()


def to_utc_iso(dt: datetime, *, assume_tz: str | None = None) -> str:
    """Bir datetime'ı `+00:00` ekli, KARŞILAŞTIRILABİLİR UTC ISO metnine çevirir.

    ⚠ Naif (tz'siz) datetime, `assume_tz` verilmedikçe UTC sayılır. Yerel saatli
    bir kaynağı (ör. KAP: İstanbul saati) naif bırakıp `_utc` adlı bir kolona
    yazmak, adı doğru içeriği yanlış bir alan üretir; sonra o alan gerçek UTC
    damgalarıyla METİN olarak karşılaştırıldığında 3 saatlik sessiz kayma verir.
    Bu fonksiyonun varlık sebebi o kaymayı tek yerde kapatmaktır.

    Çıktı biçimi daima aynı uzunlukta ve aynı ofsetle olduğu için `ORDER BY` ve
    `>` karşılaştırmaları metin üzerinde de kronolojiktir.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(assume_tz) if assume_tz else timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def bugun_tr(tz: str = "Europe/Istanbul", *, simdi: datetime | None = None) -> str:
    """Verilen saat diliminde BUGÜNÜN ISO tarihi.

    ⚠ `date.today()` sunucunun saat dilimine bağlıdır. GitHub Actions UTC
    koşar; TR ile 3 saat fark vardır ve akşam koşan bir iş UTC'de hâlâ "dün"
    olabilir. Koşu günü bir TAKVİM olgusu olduğu için daima borsa saat
    diliminden okunur (AGENTS.md §11 madde 6: zaman kaynağı açık olsun).

    `simdi` yalnız test içindir: duvar saatine bağlı bir testin ne zaman
    kırmızıya döneceğini kimse bilemez.
    """
    return (simdi or utc_now()).astimezone(ZoneInfo(tz)).date().isoformat()


def local_day_end_utc_iso(day: str | date, tz: str) -> str:
    """Verilen YEREL günün son anını (23:59:59) UTC ISO olarak döner.

    "Şu güne kadar analiz ettim, ondan sonrasını göster" tipi filtrelerin doğru
    referansı budur: analizin ASOF GÜNÜ, kaydın diske yazıldığı an değil.
    """
    d = parse_date(day) if isinstance(day, str) else day
    if d is None:
        raise ValueError(f"Tarih çözülemedi: {day!r}")
    yerel = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=ZoneInfo(tz))
    return yerel.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def to_iso_date(value: Any) -> str | None:
    """Tarih benzeri her şeyi SIRALANABİLİR ISO'ya (YYYY-MM-DD) çevirir.

    Sıralanabilirlik kritik: 'GG-AA-YYYY' biçimindeki tarihlerle `ORDER BY date`
    kronolojik DEĞİLDİR ve bu sessizce yanlış sonuç üretir.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    s = str(value).strip()
    if not s:
        return None
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":       # zaten ISO
        return s[:10]
    if len(s) == 10 and s[2] == "-" and s[5] == "-":       # GG-AA-YYYY
        d, m, y = s.split("-")
        return f"{y}-{m}-{d}"
    if len(s) == 10 and s[2] == "." and s[5] == ".":       # GG.AA.YYYY
        d, m, y = s.split(".")
        return f"{y}-{m}-{d}"
    if "-Q" in s.upper():                                   # YYYY-Q1 → çeyrek başı
        y, q = s.upper().split("-Q")
        return f"{y}-{(int(q) - 1) * 3 + 1:02d}-01"
    if "-" in s:                                            # YYYY-A / YYYY-AA → ay başı
        y, _, m = s.partition("-")
        if y.isdigit() and m.isdigit():
            return f"{y}-{int(m):02d}-01"
    return None


def parse_date(value: Any) -> date | None:
    iso = to_iso_date(value)
    return date.fromisoformat(iso) if iso else None


