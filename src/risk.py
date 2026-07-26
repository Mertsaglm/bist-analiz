"""Emir mekaniği ve pozisyon boyutu.

Bu modülün varlık sebebi: **yuvarlanmamış fiyat uygulanamaz plandır.** ATR'den
çıkan 47.3183 TL'lik bir stop piyasada yoktur; emir reddedilir ya da başka bir
fiyattan gerçekleşir. Plan üreticinin ürettiği her fiyat buradan geçer.

Fiyat adımı tablosu KENDİ VERİMİZDEN ölçüldü (config.yaml'daki gerekçeye bak),
web kaynağından değil.

⚠ Yeniden çerçeveleme notu (ADR #008): pozisyon boyutu formülü bir KENAR
iddiasına dayanmıyor. Ölçülen kenar yok. Boyutlandırmanın işi getiriyi
büyütmek değil, **kaybı sınırlamak** — her pozisyonda portföyün en fazla
`pozisyon_basi_risk_pct` kadarı stop'ta riske edilir.
"""

from __future__ import annotations

import math


# ---------------------------------------------------------------- fiyat adımı
def tick_size(price: float, cfg: dict) -> float:
    """Verilen fiyat seviyesinde geçerli fiyat adımı."""
    for band in cfg["risk"]["fiyat_adimlari"]:
        ust = band["ust_sinir"]
        if ust is None or price <= float(ust) + 1e-9:
            return float(band["adim"])
    return float(cfg["risk"]["fiyat_adimlari"][-1]["adim"])


def round_to_tick(price: float, cfg: dict, mode: str = "nearest") -> float:
    """Fiyatı geçerli ızgaraya oturtur.

    YÖN RİSK YÖNÜNDEDİR ve bu bilerek böyle:
      * `down` → stop için. Aşağı yuvarlamak stop'u biraz UZAKLAŞTIRIR;
        gürültüyle erken tetiklenme riskini azaltır.
      * `up`   → hedef için. Yukarı yuvarlamak hedefi biraz ZORLAŞTIRIR.
    İkisi de iyimserliğe değil, KÖTÜMSERLİĞE yuvarlar. Ters yönde yuvarlamak
    her backtest'i sistematik olarak iyimser yapardı.
    """
    if price is None or not math.isfinite(price) or price <= 0:
        raise ValueError(f"Yuvarlanamaz fiyat: {price!r}")
    adim = tick_size(price, cfg)
    n = price / adim
    if mode == "down":
        k = math.floor(n + 1e-9)
    elif mode == "up":
        k = math.ceil(n - 1e-9)
    elif mode == "nearest":
        k = math.floor(n + 0.5)
    else:
        raise ValueError(f"Bilinmeyen mod: {mode}")
    # Bant sınırında yuvarlama fiyatı bir alt/üst banda taşıyabilir; bir kez
    # daha çözerek tutarlı ızgaraya oturt.
    sonuc = round(k * adim, 6)
    yeni_adim = tick_size(sonuc, cfg)
    if yeni_adim != adim:
        n2 = sonuc / yeni_adim
        k2 = (math.floor(n2 + 1e-9) if mode == "down"
              else math.ceil(n2 - 1e-9) if mode == "up"
              else math.floor(n2 + 0.5))
        sonuc = round(k2 * yeni_adim, 6)
    return sonuc


def on_tick_grid(price: float, cfg: dict) -> bool:
    """Fiyat geçerli ızgarada mı? Plan doğrulaması bunu kullanır."""
    adim = tick_size(price, cfg)
    return abs(price / adim - round(price / adim)) < 1e-6


# ---------------------------------------------------------------- günlük limit
def daily_limit_band(prev_close: float, cfg: dict) -> tuple[float, float]:
    """BIST günlük fiyat marjı (±%10, config'ten). (alt, üst) döner.

    Neden gerekli: ATR'ye göre %12 uzaktaki bir stop, tek günde TETİKLENEMEZ —
    fiyat oraya gidemez. Resolver bunu bilmezse limit-down günlerinde
    gerçekleşmeyen bir stop'u gerçekleşmiş sayar.
    """
    p = float(cfg["risk"]["gunluk_fiyat_limiti_pct"]) / 100.0
    return prev_close * (1 - p), prev_close * (1 + p)


def reachable_in_one_day(prev_close: float, hedef: float, cfg: dict) -> bool:
    alt, ust = daily_limit_band(prev_close, cfg)
    return alt <= hedef <= ust


# ---------------------------------------------------------------- boyut
def position_size_pct(*, entry: float, stop: float, cfg: dict,
                      regime_multiplier: float = 1.0,
                      tier: str | None = None) -> float:
    """Portföyün yüzde kaçı bu pozisyona ayrılır.

    Volatilite-hedefli: stop mesafesi ne kadar genişse pozisyon o kadar küçük.
        boyut% = pozisyon_başı_risk% / stop_mesafesi%  × rejim_çarpanı
    `maks_pozisyon_pct` ile sınırlanır.

    ⚠ ÖLÇÜLEN DAVRANIŞ: mevcut ayarlarla (risk %1, tavan %10) tavan, stop
    mesafesi **%10'un altındaki her planda BAĞLAYICIDIR** — tipik ATR stopları
    %6-9 olduğu için boyut pratikte hep tavana oturur ve volatilite hedeflemesi
    atıl kalır. Bu bir hata değil, bilinçli muhafazakârlık: gerçekleşen risk
    %1 yerine ~%0.6-0.9'a düşer. Volatilite hedeflemesinin gerçekten çalışmasını
    istiyorsan tavanı yükselt ya da riski düşür — ama ikisi de ölçülmüş bir
    gerekçe ister, sezgiyle oynanmaz.

    ⚠ LLM'in güven seviyesi BURAYA GİRMEZ. Güven→boyut eşlemesi ancak güven
    kalibrasyonu ÖLÇÜLDÜKTEN sonra meşrudur ve o ölçüm için yıllarca veri
    gerekiyor (bkz. ai/PROJECT.md, required_n).
    """
    if entry <= 0 or stop <= 0 or stop >= entry:
        raise ValueError(f"Geçersiz entry/stop: {entry}/{stop}")
    r = cfg["risk"]
    stop_mesafe_pct = (entry - stop) / entry * 100.0
    ham = float(r["pozisyon_basi_risk_pct"]) / stop_mesafe_pct * 100.0
    boyut = ham * float(regime_multiplier)
    if tier == "yuksek_risk":
        boyut *= 0.5          # kısa geçmişli / yüksek vol isimler yarım boy
    return round(min(boyut, float(r["maks_pozisyon_pct"])), 2)


def max_loss_pct_of_portfolio(*, entry: float, stop: float,
                              position_size_pct_: float) -> float:
    """Stop tetiklenirse portföyün yüzde kaçı gider (komisyon hariç)."""
    return round((entry - stop) / entry * position_size_pct_, 3)


def rr(entry_high: float, stop: float, target: float) -> float | None:
    """Risk/getiri — giriş bandının ÜST ucundan hesaplanır.

    Orta noktadan hesaplamak R:R'ı sistematik olarak iyimser gösterir: gerçekte
    kötü senaryoda bandın üstünden alırsın.
    """
    risk = entry_high - stop
    if risk <= 0:
        return None
    return round((target - entry_high) / risk, 2)


def stop_atr_multiple(entry_high: float, stop: float, atr: float) -> float | None:
    if atr is None or atr <= 0:
        return None
    return round((entry_high - stop) / atr, 2)
