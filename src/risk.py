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


# ---------------------------------------------------------------- limit durumu
LIMIT_DURUMLARI = ("serbest", "limite_yakin", "kilitli", "limit_disi")

#: `limit_disi` barların ölçülen oranı — `daily_limit_note`'un standing uyarısı.
#: Canlı evren, 50.999 bar (2026-08-07 ölçümü). Son 2 yılda 0.
LIMIT_DISI_ORAN_PCT = 0.14


def limit_durumu(*, prev_close: float | None, c: float | None,
                 h: float | None = None, l: float | None = None,
                 cfg: dict) -> dict:
    """Bir barın günlük fiyat marjına göre durumu — DÖRT hâl, üçü değil.

    Neden gerekli (Merdiven'den alınan fikir, 2026-08-07 repo incelemesi):
    tavana kilitli bir hissede alıcı doludur, satıcı yoktur. O barın kapanışı
    **bastırılmış** bir fiyattır ve gerçek denge fiyatı bilinmez. Bu kapanışın
    üzerine kurulan giriş bandı, stop ve ATR uygulanabilir değildir — yani
    "doğru hesaplanmış ama gerçek dünyada karşılığı olmayan" bir çıktı üretir.
    Bu, L-007'nin imzasıdır ve `plan_yok` ile kapatılır (bkz. planner.build_menu).

    DÖRDÜNCÜ hâl (`limit_disi`) neden var: ölçüm, ±%10 modelinin barların
    %0.14'ünde GEÇERSİZ olduğunu gösterdi (canlı evren, 50.999 bar). Hepsi
    piyasa geneli olağanüstü gün (15 Temmuz, COVID, deprem sonrası açılış, kur
    krizi). Bunu "kilitli" diye raporlamak iki farklı olguyu aynı kelimeye
    sıkıştırmak olurdu (L-003). Ayrıca o günlerde `daily_limit_note`'un
    "stop tek günde tetiklenemez" iddiası **kanıtlanmış biçimde yanlıştır**.

    Döner: {durum, getiri_pct, yon, intraday_dokunma, band, aciklama}
    `prev_close` yoksa `durum='serbest'` DEĞİL, `None` döner — "bilmiyorum" ile
    "sorun yok" aynı değere düşmez (L-007).
    """
    if not prev_close or prev_close <= 0 or c is None or c <= 0:
        return {"durum": None, "getiri_pct": None, "yon": None,
                "intraday_dokunma": None, "band": None,
                "aciklama": "önceki kapanış yok — limit durumu değerlendirilmedi"}

    L = float(cfg["risk"]["gunluk_fiyat_limiti_pct"]) / 100.0
    b = cfg["risk"]["limit_bandi"]
    kilit_alt = L * float(b["kilit_alt_orani"])
    disi_ust = L * float(b["disi_ust_orani"])
    yakin = L * float(b["yakin_orani"])

    g = c / prev_close - 1.0
    alt, ust = daily_limit_band(prev_close, cfg)
    yon = "tavan" if g > 0 else "taban"

    # intraday dokunma: kapanış limitte olmasa bile gün içinde banda değdi mi?
    dokunma = False
    if h is not None and h > 0:
        dokunma = dokunma or (kilit_alt <= (h / prev_close - 1.0) <= disi_ust)
    if l is not None and l > 0:
        dokunma = dokunma or (kilit_alt <= -(l / prev_close - 1.0) <= disi_ust)

    if abs(g) > disi_ust:
        durum = "limit_disi"
        aciklama = (f"getiri %{g*100:+.2f} — ±%{L*100:.0f} marjının ÖTESİNDE. "
                    "Bu bar için günlük limit modeli geçerli değil (olağanüstü "
                    "piyasa günü); 'tek günde tetiklenemez' iddiaları bugün "
                    "GÜVENİLMEZ.")
    elif abs(g) >= kilit_alt:
        durum = "kilitli"
        aciklama = (f"{yon.upper()}DA kapandı (getiri %{g*100:+.2f}). Kapanış "
                    "bastırılmış bir fiyattır; karşı taraf boştur ve gerçek "
                    "denge fiyatı bilinmez.")
    elif dokunma or abs(g) >= yakin:
        durum = "limite_yakin"
        aciklama = (f"getiri %{g*100:+.2f}"
                    + (", gün içinde limite değdi" if dokunma else "")
                    + f" — ±%{L*100:.0f} marjına yakın.")
    else:
        durum = "serbest"
        aciklama = f"getiri %{g*100:+.2f} — marjdan uzak."

    return {"durum": durum, "getiri_pct": round(g * 100.0, 2),
            "yon": yon if durum in ("kilitli", "limit_disi") else None,
            "intraday_dokunma": bool(dokunma),
            "band": [round(alt, 4), round(ust, 4)], "aciklama": aciklama}


# ---------------------------------------------------------------- boyut
def position_size_pct(*, entry: float, stop: float, cfg: dict,
                      regime_multiplier: float = 1.0,
                      tier: str | None = None) -> float:
    """Portföyün yüzde kaçı bu pozisyona ayrılır.

    Volatilite-hedefli: stop mesafesi ne kadar genişse pozisyon o kadar küçük.
        boyut% = pozisyon_başı_risk% / stop_mesafesi%  × rejim_çarpanı
    `maks_pozisyon_pct` ile sınırlanır.

    ⚠ ÖLÇÜLEN DAVRANIŞ — İKİ AYRI SINIRLAYICI, KARIŞTIRMA:

    1. **Rejim çarpanı < 1 iken** boyutu o belirler, tavan değil. Ölçüldü
       (2026-07-24, risk-off, çarpan 0.40): stop mesafesi %6.9 → ham boyut
       %14.5 → çarpanla %5.83 → tavan (%10) BAĞLAMIYOR. Gerçekleşen risk
       %1 değil %0.40.
    2. **Çarpan 1.0 iken** (risk-on) tavan, stop mesafesi %10'un altındaki
       her planda bağlar ve volatilite hedeflemesi atıl kalır.

    İlk sürümdeki yorum yalnız (2)'yi yazıyor ve "her planda" diyordu; canlı
    rejimlerin çoğunda geçerli olan (1)'i atlıyordu (2026-07-27 denetimi).
    Her iki durumda da gerçekleşen risk hedeflenenin ALTINDA kalır — bilinçli
    muhafazakârlık. Değiştirmek istiyorsan ölçülmüş bir gerekçe gerekir.

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


def rr_net(entry_high: float, stop: float, target: float, cfg: dict) -> float | None:
    """R:R'ın GİDİŞ-DÖNÜŞ MALİYETİ düşülmüş hâli.

    Neden gerekti (2026-08-07, Merdiven'in ΔEV fikrinin çekirdeği): maliyet
    bu projede yalnız `backtest.py`'de yaşıyordu. Yani aynı sistem bir yerde
    "maliyet var" diyor, plan üretirken yok sayıyordu. Rapor "R:R 1.52" yazıyor,
    gerçekte 1.42.

    Maliyet İKİ TARAFI DA vurur ve asimetrik değil: giriş+çıkış komisyonu
    kaybederken de kazanırken de ödenir.
        net_risk = (giriş − stop) + giriş × maliyet
        net_ödül = (hedef − giriş) − giriş × maliyet

    ⚠ BU DEĞER KAPI DEĞİLDİR ve olmamalı — bkz. `planner.build_options`.
    `min_rr_t1` NET'e uygulanırsa eşik fiilen 1.5 → ~1.60 yükselir ve bu,
    `docs/on-kayit-seviye-02.md` §4'ün ön kayıt gerektiren üç parametresinden
    biridir. ÖLÇÜLDÜ (58 geçmiş plan): net eşiğe geçmek planların **%33'ünü**
    (19/58) elerdi. Bu sayı, ön kayıt turu koşulduğunda kanıt olarak kullanılmak
    üzere buraya yazıldı — bugün ona göre karar VERİLMEZ.
    """
    m = float(cfg["risk"]["islem_maliyeti_gidis_donus_pct"]) / 100.0
    net_risk = (entry_high - stop) + entry_high * m
    if net_risk <= 0:
        return None
    return round(((target - entry_high) - entry_high * m) / net_risk, 2)


def stop_atr_multiple(entry_high: float, stop: float, atr: float) -> float | None:
    if atr is None or atr <= 0:
        return None
    return round((entry_high - stop) / atr, 2)
