"""Deterministik plan menüsü — LLM'e sunulan seçenekler.

Bu katmanın tek işi: **LLM'in uydurabileceği her sayıyı önceden hesaplamak.**
Giriş bandı, stop, hedefler, R:R, pozisyon boyutu, zaman bariyeri — hepsi
burada, kuralla üretilir. LLM yalnızca bir `plan_id` seçer.

İki sert kural:

1. **Hedefler UYDURULMAZ.** Yalnız gerçek pivot/direnç seviyelerinden ya da
   52-hafta zirvesinden gelir. Geçerli seviye yoksa hedef YOK, plan da YOK.
   "ATR×3 yukarısı" gibi türetilmiş hedefler bilerek kullanılmıyor: onlar
   seviye değil, ölçü çubuğudur ve piyasada karşılığı yoktur.

2. **Her fiyat geçerli tick ızgarasında.** Yuvarlanmamış fiyat uygulanamaz plandır.

⚠ Yeniden çerçeveleme (ADR #008): bu planlar bir KENAR iddiası taşımıyor.
Ölçüm, mevcut skorun pozitif kenar üretmediğini söyledi. Planların işi
"kazandıracak işlem bulmak" değil, **karar verilmişse o kararı disiplinli
bir geometriye oturtmak**: nereye stop, ne kadar boyut, hangi seviyede ne olur.
Her çıktı bu ibareyi taşır.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, asdict, field

import numpy as np
import pandas as pd

from . import db, levels as lv, risk, util

UYARI = ("Ölçülen kenar yok (ADR #008). Bu seviyeler planlama geometrisidir, "
         "yön iddiası değildir.")

# ⚠ `breakout_above_resistance` KALDIRILDI (2026-07-27 denetimi). `build_options`
# onu hiç üretmiyordu ve `resolver.entry_fill` doluma DAİMA aşağıdan bakıyor
# (`r.l <= entry_high`). Yani listede duran bir kırılım tetikleyicisi, birinin
# onu üretmesi halinde SESSİZCE TERS yönde doldurulurdu. Desteklenmeyen bir
# değeri "izinli" listesinde tutmak, ileride onu kullanacak kişiye kurulmuş
# bir tuzaktır.
ENTRY_TRIGGERS = ("direct", "pullback_to_sma20", "pullback_to_sma50",
                  "support_retest")
STOP_METHODS = ("atr_2x", "atr_2.5x", "atr_3x", "swing_low", "sma_break_buffer")


@dataclass(frozen=True, slots=True)
class PlanOption:
    plan_id: str
    ticker: str
    asof: str
    kind: str
    entry_low: float
    entry_high: float
    entry_trigger: str
    stop_price: float
    stop_method: str
    stop_atr_multiple: float
    targets: list[dict]
    rr_at_t1: float
    # Gidiş-dönüş maliyeti düşülmüş R:R. **KAPI DEĞİL** — `min_rr_t1` brüte
    # uygulanır, çünkü nete geçmek eşiği fiilen yükseltir ve bu
    # `docs/on-kayit-seviye-02.md` §4'ün ön kayıt gerektiren parametrelerinden
    # biridir. Alan, raporun "R:R 1.52" derken 1.42'yi gizlememesi için var.
    rr_at_t1_net: float | None
    maliyet_pct: float
    time_barrier_days: int
    time_barrier_date: str
    position_size_pct: float
    max_loss_pct_of_portfolio: float
    entry_zone_status: str
    daily_limit_note: str
    ex_date_in_window: str | None
    # `asof` barının günlük fiyat marjına göre durumu (serbest / limite_yakin /
    # kilitli / limit_disi). `kilitli` isimlerde plan zaten ÜRETİLMEZ; bu alan
    # kalan iki uyarı hâlini plana taşır. Bkz. risk.limit_durumu.
    limit_durumu: str | None = None
    invalidations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # R:R'ın hangi giriş bandı / stop yöntemi kombinasyonuyla sağlandığı ve
    # ondan önce hangi adayların elendiği. R:R planlar arası kıyaslanabilir
    # bir sayı DEĞİLDİR; bu iki alan farkı görünür kılar (bkz. build_options).
    rr_secim: str = ""
    elenen_adaylar: list[str] = field(default_factory=list)
    uyari: str = UYARI


# ---------------------------------------------------------------- yardımcılar
def entry_zone_status(price: float, low: float, high: float, atr: float) -> str:
    """Fiyat giriş bandına göre nerede? Tolerans 0.25×ATR."""
    tol = 0.25 * atr
    if price < low - tol:
        return "below_zone"
    if price > high + tol:
        return "above_zone"
    return "in_zone"


def _stop_candidates(price: float, atr: float, sma20: float | None,
                     sma50: float | None, swing_low: float | None) -> list[tuple]:
    """(yöntem, ham stop fiyatı) adayları. Sıralama sabit — determinizm için."""
    out = [("atr_2x", price - 2.0 * atr),
           ("atr_2.5x", price - 2.5 * atr),
           ("atr_3x", price - 3.0 * atr)]
    if swing_low and swing_low < price:
        out.append(("swing_low", swing_low * 0.995))
    for ad, s in (("sma_break_buffer", sma20), ("sma_break_buffer", sma50)):
        if s and s < price:
            out.append((ad, s * 0.985))
    return out


def build_options(cfg: dict, *, ticker: str, asof: str, bars: pd.DataFrame,
                  ind: dict, seviyeler: list[lv.Level], regime: dict,
                  ex_date: str | None = None, tier: str | None = None,
                  time_barrier_date: str | None = None,
                  limit: dict | None = None
                  ) -> tuple[list[PlanOption], str | None]:
    """Geçerli plan menüsü ve — üretilemediyse — SEBEBİ.

    Sebebi döndürmek şart: "plan yok" tek bir olgu değil. "Zirvede olduğu için
    hedef yok" ile "R:R yetmedi" tamamen farklı iki durumdur ve aynı cümleyle
    raporlamak okuyanı yanıltır (L-003).

    `ex_date`: `build_menu` bunu ZATEN önceden eleyip buraya hiç gelmiyor;
    parametre doğrudan çağıran yollar (replay, testler) için korunur ve
    `PlanOption.ex_date_in_window` alanına yazılır.
    """
    p = cfg["planlayici"]
    fiyat = float(bars["c"].iloc[-1])
    atr = ind.get("atr14")
    if not atr or not np.isfinite(atr) or atr <= 0:
        return [], "ATR hesaplanamadı"

    # Kurumsal işlem plan penceresine düşüyorsa plan ÜRETİLMEZ: ex-tarihte
    # fiyat mekanik olarak düşer ve stop'u yapay tetikler.
    if ex_date:
        return [], f"plan penceresinde ex-tarih: {ex_date}"

    sma20, sma50 = ind.get("sma20"), ind.get("sma50")
    destekler = lv.supports_below(seviyeler, fiyat, 3)
    direncler = lv.resistances_above(seviyeler, fiyat, 3)
    swing_low = destekler[0].price if destekler else None

    # ---- HEDEFLER: yalnız gerçek seviyeler. Yoksa plan yok. ----
    hedef_kaynaklari: list[tuple[float, str]] = [
        (d.price, f"pivot@{d.last_date} ({d.touches} dokunuş)") for d in direncler]
    y52 = ind.get("high_52w")
    if y52 and y52 > fiyat and all(abs(y52 - h) > 0.5 * atr for h, _ in hedef_kaynaklari):
        hedef_kaynaklari.append((float(y52), "52 hafta zirvesi"))
    if not hedef_kaynaklari:
        if lv.at_all_time_high(bars):
            return [], ("tüm zamanların zirvesinde — ÜSTTE DİRENÇ YOK, o bölgede "
                        "hiç işlem geçmemiş; hedef uydurulmadı")
        return [], "üstte geçerli seviye yok — hedef üretilemedi"

    hedef_kaynaklari.sort(key=lambda x: x[0])

    # ---- GİRİŞ BANTLARI ----
    # Fiyattan çok uzak bir seviye TETİKLENEBİLİR bir giriş değildir. EUPWR
    # vakası: fiyat ~90 TL iken 3 yıl önceki 32 TL seviyesi "destek retest"
    # diye plan üretiyordu (R:R 6.39 — tamamen artefakt). Uzaklık ATR ölçekli
    # sınırlanır; mutlak yüzde kullanmak volatil ve sakin hisseyi eşitlerdi.
    maks_uzaklik = float(p["maks_giris_uzakligi_atr"]) * atr
    en_dusuk_giris = fiyat - maks_uzaklik

    bantlar: list[tuple[str, float, float, str]] = [
        ("dogrudan", fiyat * 0.995, fiyat, "direct")]
    if sma20 and en_dusuk_giris <= sma20 < fiyat:
        bantlar.append(("sma20_geri_cekilme", sma20 * 0.99, min(sma20 * 1.01, fiyat),
                        "pullback_to_sma20"))
    if destekler and en_dusuk_giris <= destekler[0].price < fiyat:
        d = destekler[0].price
        bantlar.append(("destek_retest", d * 0.995, min(d * 1.015, fiyat),
                        "support_retest"))

    secenekler: list[PlanOption] = []
    # R:R'ın NASIL sağlandığı kaydedilir — bkz. aşağıdaki uyarı.
    elenen: list[str] = []

    for i, (kind, ham_low, ham_high, trigger) in enumerate(bantlar):
        if ham_low >= ham_high or ham_low <= 0:
            continue
        e_low = risk.round_to_tick(ham_low, cfg, "down")
        e_high = risk.round_to_tick(ham_high, cfg, "up")
        if e_low >= e_high:
            continue

        for yontem, ham_stop in _stop_candidates(e_high, atr, sma20, sma50, swing_low):
            if ham_stop <= 0 or ham_stop >= e_low:
                continue
            stop = risk.round_to_tick(ham_stop, cfg, "down")
            katsayi = risk.stop_atr_multiple(e_high, stop, atr)
            alt, ust = p["stop_atr_bandi"]
            if katsayi is None or not (alt <= katsayi <= ust):
                elenen.append(f"{kind}/{yontem}: {katsayi}×ATR ∉ [{alt},{ust}]")
                continue

            hedefler = []
            for h, dayanak in hedef_kaynaklari:
                hp = risk.round_to_tick(h, cfg, "up")
                if hp <= e_high:
                    continue
                hedefler.append({
                    "price": hp, "rr": risk.rr(e_high, stop, hp),
                    "rr_net": risk.rr_net(e_high, stop, hp, cfg),
                    "atr_distance": round((hp - e_high) / atr, 2),
                    "basis": dayanak})
            if not hedefler:
                elenen.append(f"{kind}/{yontem}: girişin üstünde hedef yok")
                continue
            # ⚠ KAPI BRÜT R:R'a UYGULANIR — bilerek. Nete geçmek `min_rr_t1`'i
            # fiilen 1.5 → ~1.60 yükseltir; `docs/on-kayit-seviye-02.md` §4 bu
            # parametreyi ön kayıtlı tura bağlamış ve §3'teki tetikleyicilerin
            # hiçbiri oluşmadı. ÖLÇÜLDÜ (58 geçmiş plan): nete geçmek %33'ünü
            # elerdi. Sayıyı görüp eşik oynatmak, `on-kayit-revizyon-01.md` §5'in
            # açıkça yasakladığı harekettir. Net değer plana YAZILIR, kapıya
            # GİRMEZ — `tests/test_planner.py::TestNetRR` bunu zorlar.
            if (hedefler[0]["rr"] or 0) < float(p["min_rr_t1"]):
                elenen.append(f"{kind}/{yontem}: R:R {hedefler[0]['rr']} < "
                              f"{p['min_rr_t1']}")
                continue

            boyut = risk.position_size_pct(
                entry=e_high, stop=stop, cfg=cfg,
                regime_multiplier=float(regime.get("size_multiplier", 1.0)),
                tier=tier)
            # Anlamlı soru: GİRİŞTEN sonra stop tek günde tetiklenebilir mi?
            # (boşluk riski). Bugünkü fiyattan ölçmek yanlış referans olurdu —
            # geri çekilme planında henüz girilmemiştir. L-003: iki farklı
            # olguyu aynı kelimelerle raporlama.
            bosluk_riski = risk.reachable_in_one_day(e_low, stop, cfg)
            stop_uzaklik = (e_high - stop) / e_high * 100

            secenekler.append(PlanOption(
                plan_id=f"{ticker}-{asof}-{chr(65 + len(secenekler))}",
                ticker=ticker, asof=asof, kind=kind,
                entry_low=e_low, entry_high=e_high, entry_trigger=trigger,
                stop_price=stop, stop_method=yontem, stop_atr_multiple=katsayi,
                targets=hedefler[:3], rr_at_t1=hedefler[0]["rr"],
                rr_at_t1_net=hedefler[0]["rr_net"],
                maliyet_pct=float(cfg["risk"]["islem_maliyeti_gidis_donus_pct"]),
                time_barrier_days=int(p["zaman_bariyeri_gun"]),
                time_barrier_date=time_barrier_date or "",
                position_size_pct=boyut,
                max_loss_pct_of_portfolio=risk.max_loss_pct_of_portfolio(
                    entry=e_high, stop=stop, position_size_pct_=boyut),
                entry_zone_status=entry_zone_status(fiyat, e_low, e_high, atr),
                daily_limit_note=_limit_notu(cfg, stop_uzaklik, bosluk_riski, limit),
                ex_date_in_window=ex_date,
                limit_durumu=(limit or {}).get("durum"),
                invalidations=_invalidations(sma50, destekler),
                notes=[f"{len(direncler)} direnç, {len(destekler)} destek seviyesi kullanıldı"],
                # ⚠ R:R BİR SONUÇ DEĞİL, BİR SEÇİM ÜRÜNÜ. Hedef sabittir (en
                # yakın gerçek direnç); giriş ve stop ise seçilir. Döngü
                # `dogrudan → sma20_geri_cekilme → destek_retest` sırasıyla
                # ilerler ve R:R ≥ min_rr_t1 sağlayan İLK kombinasyonda durur.
                # Yani eşitsizlik, GİRİŞİ AŞAĞI İTEREK ve/veya STOP'U
                # DARALTARAK çözülür.
                #
                # Ölçüldü (2026-07-24): 12 planın 10'u `above_zone` — yani
                # gerçekleşmesi bir geri çekilmeye bağlı. Replay'de tetiklenmeme
                # oranı %46.4. İki planın R:R'ı bu yüzden KIYASLANABİLİR DEĞİL:
                # biri stop daraltarak, diğeri girişi %8 aşağı çekerek elde
                # edilmiş olabilir. Aşağıdaki alan bunu görünür kılar.
                rr_secim=f"{i + 1}. giriş bandı ({kind}), stop {yontem}",
                elenen_adaylar=list(elenen),
            ))
            break      # her giriş bandı için TEK stop yöntemi — menü şişmesin

        if len(secenekler) >= int(p["maks_plan_per_hisse"]):
            break

    if secenekler:
        return secenekler, None
    return [], (f"{len(bantlar)} giriş bandı denendi; hiçbiri "
                f"stop∈{p['stop_atr_bandi']}×ATR + R:R≥{p['min_rr_t1']} "
                f"kurallarını birlikte sağlayamadı")


def _limit_notu(cfg: dict, stop_uzaklik: float, bosluk_riski: bool,
                limit: dict | None) -> str:
    """Stop'un tek günde tetiklenip tetiklenemeyeceği — ve o iddianın SINIRI.

    ⚠ Eski sürüm koşulsuz "tek günde tetiklenemez" diyordu. ÖLÇÜLDÜ
    (2026-08-07, canlı evren 50.999 bar): barların **%0.14'ünde** günlük getiri
    ±%10 marjını AŞIYOR — yani o günlerde bu cümle yanlış. Hepsi piyasa geneli
    olağanüstü gün (15 Temmuz sonrası açılış, COVID, deprem sonrası açılış, kur
    krizi). Yorum bir iddiadır (AGENTS.md §8); iddianın ölçülmüş istisnası
    varsa cümlenin içinde durmalı, dipnotta değil.
    """
    L = float(cfg["risk"]["gunluk_fiyat_limiti_pct"])
    bas = f"stop girişten %{stop_uzaklik:.1f} uzakta; girildikten sonra "
    if bosluk_riski:
        return bas + "tek günde tetiklenebilir (boşluk riski var)"
    son = (f"tek günde tetiklenemez — ±%{L:.0f} marj dışında "
           f"(ölçülen istisna: barların %{risk.LIMIT_DISI_ORAN_PCT:.2f}'ünde "
           "marj aşılmış — olağanüstü piyasa günleri)")
    if (limit or {}).get("durum") == "limit_disi":
        son += ". ⚠ BUGÜN TAM O İSTİSNADA: " + limit["aciklama"]
    return bas + son


def _invalidations(sma50: float | None, destekler: list[lv.Level]) -> list[str]:
    out = []
    if sma50:
        out.append(f"SMA50 ({sma50:.2f}) altına günlük kapanış")
    if destekler:
        out.append(f"{destekler[0].price:.2f} desteğinin altına kapanış")
    out.append("hacim 20 günlük ortalamanın %50 altına inerse tez zayıflar")
    return out


# ---------------------------------------------------------------- doğrulama
def validate_option(opt: PlanOption, cfg: dict) -> list[str]:
    """Plan kendi kendini denetler. LLM'e GEÇERSİZ plan sunulamaz."""
    p = cfg["planlayici"]
    ihlal: list[str] = []

    if not (opt.entry_low < opt.entry_high):
        ihlal.append("entry_low >= entry_high")
    if not (opt.stop_price < opt.entry_low):
        ihlal.append("stop giriş bandının altında değil")
    for ad, f in (("entry_low", opt.entry_low), ("entry_high", opt.entry_high),
                  ("stop", opt.stop_price)):
        if not risk.on_tick_grid(f, cfg):
            ihlal.append(f"{ad} geçerli tick ızgarasında değil: {f}")
    alt, ust = p["stop_atr_bandi"]
    if not (alt <= opt.stop_atr_multiple <= ust):
        ihlal.append(f"stop_atr_multiple {opt.stop_atr_multiple} ∉ [{alt}, {ust}]")
    if not opt.targets:
        ihlal.append("hedef yok")
    for t in opt.targets:
        if t["price"] <= opt.entry_high:
            ihlal.append(f"hedef giriş bandının üstünde değil: {t['price']}")
        if not risk.on_tick_grid(t["price"], cfg):
            ihlal.append(f"hedef geçerli tick ızgarasında değil: {t['price']}")
        if not t.get("basis"):
            ihlal.append("hedefin dayanağı yok — uydurulmuş seviye")
    if (opt.rr_at_t1 or 0) < float(p["min_rr_t1"]):
        ihlal.append(f"R:R {opt.rr_at_t1} < {p['min_rr_t1']}")
    if opt.position_size_pct <= 0 or opt.position_size_pct > cfg["risk"]["maks_pozisyon_pct"]:
        ihlal.append(f"pozisyon boyutu bandı dışında: {opt.position_size_pct}")
    if opt.entry_trigger not in ENTRY_TRIGGERS:
        ihlal.append(f"bilinmeyen entry_trigger: {opt.entry_trigger}")
    if opt.stop_method not in STOP_METHODS:
        ihlal.append(f"bilinmeyen stop_method: {opt.stop_method}")
    return ihlal


# ---------------------------------------------------------------- saklama
def store(cfg: dict, con: sqlite3.Connection, opts: list[PlanOption]) -> int:
    if not opts:
        return 0
    now = util.utc_now_iso()
    return db.upsert_many(
        con, "plan_options",
        ["plan_id", "asof", "ticker", "kind", "payload", "created_utc"],
        [(o.plan_id, o.asof, o.ticker, o.kind,
          util.json_dump(asdict(o), pretty=False), now) for o in opts])


def build_menu(cfg: dict, con: sqlite3.Connection, asof: str,
               tickers: list[str] | None = None,
               kalite: dict[str, dict] | None = None) -> dict:
    """Tüm canlı evren için plan menüsü. Plan üretilemeyenler GEREKÇESİYLE döner.

    "Plan yok" bir hata değil, geçerli bir çıktıdır ve sebebi yazılır —
    sessizce boş liste döndürmek, kullanıcıya "bakmadım" ile "baktım, uygun
    değil"i aynı şey gibi gösterir.

    `kalite`: verilmezse `data_quality` tablosundan (asof'a kadarki en son
    kayıt) okunur. GEÇMİŞE dönük koşan çağıranlar (replay) o güne ait kaliteyi
    kendileri hesaplayıp buradan geçirmelidir — tablo yalnız bugünü tutar ve
    eksik kayıt artık ELEYİCİDİR. Bu parametre olmadan replay'in tamamı
    "kalite değerlendirilmedi" diye elenir (ölçüldü: 30 dönem × 3 isim = 90
    plan_yok, 0 tahmin).
    """
    from . import indicators, prices, regime as rj, universe
    from .calendar_bist import BistCalendar

    tickers = tickers or universe.live(con)
    cal = BistCalendar(cfg, con)
    rej = rj.classify(cfg, con, asof)
    # Rejim kararı DONDURULUR: "o gün neden risk-off dedik?" sorusunun cevabı
    # girdileriyle birlikte saklanmazsa cevaplanamaz (bkz. regime.store).
    rj.store(cfg, con, rej)
    snap = indicators.snapshot(con, asof, cfg)
    kalite = prices.quality_map(con, asof) if kalite is None else kalite
    tiers = universe.tier_map(con)
    H = int(cfg["planlayici"]["zaman_bariyeri_gun"])
    bariyer = cal.add_trading_days(asof, H).isoformat()

    menu: dict[str, list[PlanOption]] = {}
    atlanan: dict[str, str] = {}
    # Plan üretilmeme SEBEBİNİN SINIFI. Metin ayrıştırmak kırılgandır ve
    # denetim katmanının buna ihtiyacı var: "veri güvenilmez" ile "geometri
    # kurulamadı" TAMAMEN farklı iki şeydir. Birincisinde boğa sinyali
    # savunulamaz, ikincisinde gayet meşrudur (`izle` tam da odur).
    #   veri     → veriye güvenmiyoruz / hesaplayamadık
    #   limit    → bugün işlem görmüyor (tavan/taban kilidi)
    #   kurumsal → mekanik fiyat düzeltmesi penceresi
    #   geometri → fiyat sağlam, plan iskeleti kurulamadı
    atlanan_sinif: dict[str, str] = {}
    # Limit durumu TÜM isimler için hesaplanır — kalite kapısından eleneni de
    # kapsar, çünkü "bu isim neden yok" sorusunun cevabı bağımsız bir olgudur.
    limitler = prices.limit_map(cfg, con, asof, tickers)

    # Bilanço penceresi. ⚠ ELEYİCİ DEĞİL, İŞARETLEYİCİ — ex-temettüden farkı bu:
    # ex-tarihte fiyat MEKANİK olarak düşer ve stop'u yapay tetikler, bu yüzden
    # plan üretilmez. Bilanço mekanik bir düzeltme değil, bir VOLATİLİTE
    # olayıdır. Üstelik ölçüldü (2026-08-07): 19 ismin 9'unda pencere açık —
    # elemek, sistemi her çeyrek yarı yarıya susturmak olurdu.
    from . import news
    bb_saglik = news.beklenen_durumu(cfg, con, asof)
    bilancolar = {t: news.beklenen_pencere(con, t, asof, bariyer, saglik=bb_saglik)
                  for t in tickers}

    for t in tickers:
        ind = snap.get(t)
        if not ind:
            atlanan[t] = "gösterge yok"
            atlanan_sinif[t] = "veri"
            continue
        # Eksik kalite kaydı "sorun yok" DEĞİLDİR — `quality_for` onu
        # `ok=False, kalite değerlendirilmedi` olarak döndürür. Aksi halde
        # `bist veri kalite` koşulmayan her gün kapı sessizce kapanırdı.
        k = prices.quality_for(kalite, t)
        if not k["ok"]:
            atlanan[t] = "veri kalitesi: " + "; ".join(k["uyarilar"])
            atlanan_sinif[t] = "veri"
            continue

        bars = prices.bars(con, t, end=asof)
        if len(bars) < 260:
            atlanan[t] = f"yetersiz bar ({len(bars)})"
            atlanan_sinif[t] = "veri"
            continue

        ex = _ex_date_in_window(con, t, asof, bariyer)
        if ex:
            atlanan[t] = f"plan penceresinde kurumsal işlem ex-tarihi: {ex}"
            atlanan_sinif[t] = "kurumsal"
            continue

        # --- LİMİT KAPISI (2026-08-07, Merdiven'den alınan fikir) -----------
        # Tavana/tabana kilitli bir barın kapanışı BASTIRILMIŞ bir fiyattır:
        # karşı taraf boştur, gerçek denge fiyatı bilinmez. O kapanışın üzerine
        # kurulan giriş bandı / stop / ATR "doğru hesaplanmış ama uygulanamaz"
        # bir plan üretir — L-007'nin tam imzası.
        #
        # Neden ELEME, sadece uyarı değil: ADR #008'e göre planlar zaten kenar
        # iddiası taşımıyor, dolayısıyla bir planı ÜRETMEMENİN ölçülebilir bir
        # maliyeti yok; uygulanamaz bir plan yayımlamanın ise var. Fail-closed,
        # kalite kapısıyla aynı desen. Frekans ölçüldü: canlı evrende %0.97.
        lim = limitler.get(t) or risk.limit_durumu(prev_close=None, c=None, cfg=cfg)
        if lim["durum"] == "kilitli":
            atlanan[t] = f"günlük fiyat marjı: {lim['aciklama']}"
            atlanan_sinif[t] = "limit"
            continue

        sev = lv.build_levels(bars, cfg, atr=ind.get("atr14"))
        # Seviyeler de dondurulur: plan hangi geometriye dayandıysa o geometri
        # sonradan denetlenebilmeli (`levels_daily` uzun süre boş kalmıştı).
        lv.store(cfg, con, t, asof, sev)
        opts, neden = build_options(cfg, ticker=t, asof=asof, bars=bars, ind=ind,
                                    seviyeler=sev, regime=rej, tier=tiers.get(t),
                                    time_barrier_date=bariyer, limit=lim)
        gecerli = [o for o in opts if not validate_option(o, cfg)]
        if gecerli:
            menu[t] = gecerli
        elif opts:
            atlanan[t] = (f"{len(opts)} aday üretildi, hepsi doğrulamadan geçemedi: "
                          + "; ".join(validate_option(opts[0], cfg)[:2]))
            atlanan_sinif[t] = "geometri"
        else:
            atlanan[t] = neden or "bilinmeyen"
            atlanan_sinif[t] = "veri" if neden == "ATR hesaplanamadı" else "geometri"

    return {"asof": asof, "rejim": rej, "menu": menu, "atlanan": atlanan,
            "zaman_bariyeri": bariyer, "uyari": UYARI, "limitler": limitler,
            "atlanan_sinif": atlanan_sinif,
            "bilancolar": bilancolar, "bilanco_saglik": bb_saglik}


def _ex_date_in_window(con: sqlite3.Connection, ticker: str, asof: str,
                       bitis: str) -> str | None:
    row = db.fetch_one(
        con, "SELECT date FROM corporate_actions WHERE ticker=? AND date>? "
             "AND date<=? ORDER BY date LIMIT 1", (ticker, asof, bitis))
    return row["date"] if row else None


def load_for_date(cfg: dict, con: sqlite3.Connection, asof: str) -> dict[str, list[dict]]:
    import json
    rows = db.fetch_all(
        con, "SELECT ticker, payload FROM plan_options WHERE asof = ? ORDER BY plan_id",
        (asof,))
    out: dict[str, list[dict]] = {}
    for r in rows:
        out.setdefault(r["ticker"], []).append(json.loads(r["payload"]))
    return out
