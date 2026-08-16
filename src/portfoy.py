"""Kâğıt portföy — sistemin kendi kararlarını KENDİ takip etmesi (ADR #019).

Mert'in kararı (2026-08-16): *"portföy şu an tamamen boş; proje kendisini bana
kanıtlamalı. Başlangıç olarak proje gerçek zamanlı alım satım yapıyormuş gibi
bu portföyü kullanmalı, kayıtlarını almalı."*

⚠ EN ÖNEMLİ TASARIM KARARI — **portföy bir TÜREV GÖRÜNÜMDÜR, ayrı defter değil.**

Yeni tablo yok, yeni gerçek kaynağı yok: pozisyonlar `predictions` + `outcomes`
üzerinden kronolojik olarak yeniden hesaplanır. Gerekçe projenin kendi kuralıdır
(`journal.aktif_vetolar`): *"`predictions` DEĞİŞMEZDİR ve veto oradan TÜRETİLİR
— ayrı bir tablo tutmak aynı gerçeği iki yerde saklamak olurdu ve ikisi
ayrışırdı."* Portföy için bedeli daha ağır olurdu: karne ile portföy aynı işlem
için farklı sayı basardı.

**Giriş `resolver` ile AYNI fonksiyondan gelir.** `outcomes` zaten
`resolver.entry_fill` mantığıyla ölçüyor; portföy başka bir mantık kullansaydı
aynı işlem için iki farklı giriş fiyatı çıkardı. Kopya mantık yazılmaz —
çözülmüş tahminde `outcomes.entry_price` okunur, çözülmemişte aynı fonksiyon
çağrılır.

**Kâr/zarar `outcomes.ret_pct`'ten gelir** (maliyet dahil). TL sonucu ondan
türetilir, yeniden hesaplanmaz — karne ile portföyün ayrışması böylece
aritmetik olarak imkânsız hale gelir.

**Reddedilen plan sessizce kaybolmaz.** Bir plan kontenjan/çift isim/sektör/
sermaye yüzünden alınmadıysa sebebi SINIF KODUYLA kaydedilir (L-020: birleşik
bir gerekçe hangi koşulun düştüğünü gizler).
"""

from __future__ import annotations

import logging
import math
import sqlite3

from . import db, util

log = logging.getLogger(__name__)

# Bir planın portföye ALINMAMA sebebi — ince sınıf. Rapor bunu kullanır ve
# eşliği test zorlar (§12.2): kümede olup etiketi olmayan bir kod eklenirse
# suite kırmızıya döner, yani rapor sessizce "None" basmaz.
RED_SEBEPLERI = (
    "kontenjan_dolu",     # rejimin maks_pozisyon tavanı doluydu
    "isim_zaten_acik",    # aynı ticker'da açık pozisyon var
    "sektor_tavani",      # sektör başına pozisyon tavanı doluydu
    "sermaye_yetersiz",   # boyut × sermaye, bir lot bile etmiyor (adet 0)
    "giris_olmadi",       # plan hiç tetiklenmedi (fiyat banda dokunmadı)
)

RED_ETIKET = {
    "kontenjan_dolu":   "rejim tavanı dolu",
    "isim_zaten_acik":  "bu isimde açık pozisyon var",
    "sektor_tavani":    "sektör tavanı dolu",
    "sermaye_yetersiz": "sermaye bir lota yetmiyor",
    "giris_olmadi":     "plan tetiklenmedi",
}


def _politika(cfg: dict, etiket: str | None) -> dict:
    """Rejim politikası. Bilinmeyen etikette EN SIKI olan seçilir.

    ⚠ Varsayılanı gevşek bırakmak, bilinmeyen bir rejim etiketinde tavanı
    sessizce kaldırırdı — "veri yok" ile "sorun yok"un portföy hâli (#009).
    """
    pol = cfg["rejim"]["politika"]
    if etiket in pol:
        return pol[etiket]
    return min(pol.values(), key=lambda p: p.get("maks_pozisyon", 99))


def _adaylar(cfg: dict, con: sqlite3.Connection) -> list[dict]:
    """Portföye aday kararlar: canlı zincirin `plan_sec` tahminleri.

    `replay` HARİÇ (`config.portfoy.haric_araclar`) — vekil analistin kararları
    sistemin karnesine girmez.
    """
    haric = list(cfg["portfoy"].get("haric_araclar") or [])
    ph = ",".join("?" * len(haric)) or "''"
    return db.fetch_all(
        con,
        f"SELECT p.prediction_id, p.asof, p.ticker, p.regime, p.position_size_pct, "
        f"       p.entry_low, p.entry_high, p.stop_price, p.t1_price, "
        f"       p.time_barrier_date, r.tool, u.sector, "
        f"       o.entry_date, o.entry_price, o.exit_date, o.exit_price, "
        f"       o.ret_pct, o.resolution "
        f"  FROM predictions p "
        f"  JOIN llm_runs r ON r.run_id = p.run_id "
        f"  LEFT JOIN universe u ON u.ticker = p.ticker "
        f"  LEFT JOIN outcomes o ON o.prediction_id = p.prediction_id "
        f" WHERE p.action = 'plan_sec' AND p.plan_id IS NOT NULL "
        f"   AND r.tool NOT IN ({ph}) "
        f" ORDER BY p.asof, p.ticker", tuple(haric))


def _dolum(con: sqlite3.Connection, ad: dict) -> tuple[str, float] | None:
    """Giriş gerçekleşti mi? ÇÖZÜLMÜŞSE `outcomes`'tan, değilse resolver'dan.

    ⚠ İkinci dal kendi mantığını YAZMAZ, `resolver.entry_fill`i ÇAĞIRIR. Kopya
    bir dolum kuralı, karne ile portföyün ayrışacağı ilk yer olurdu.
    """
    if ad["entry_date"]:
        return ad["entry_date"], float(ad["entry_price"])
    if ad["resolution"]:
        return None                      # çözülmüş ama girişsiz (giris_olmadi/iptal)
    if ad["entry_low"] is None or ad["entry_high"] is None:
        return None

    from . import prices, resolver
    bars = prices.bars(con, ad["ticker"], start=ad["asof"],
                       end=ad["time_barrier_date"])
    if len(bars) < 2:
        return None
    return resolver.entry_fill(bars.iloc[1:].reset_index(drop=True),
                               entry_low=ad["entry_low"],
                               entry_high=ad["entry_high"])


def simule(cfg: dict, con: sqlite3.Connection, *, asof: str | None = None) -> dict:
    """Kâğıt portföyün o güne kadarki durumu. Deterministik ve yeniden üretilebilir.

    Zaman çizgisi olay olay yürütülür. Bir GÜN içinde sıra:
        1. AÇILIŞLAR — o günün başındaki kontenjanla
        2. KAPANIŞLAR — yer ertesi güne boşalır

    ⚠ Sıra KÖTÜMSER tarafa kurulu ve bu bilinçli: gün içi sıra bilinemez
    (`resolver.barrier_hit` ile aynı gerekçe). Kapanışı önce işlemek, aynı gün
    boşalan yere hemen yeni pozisyon aldırırdı — yani gün içinde iki kez risk
    alındığını varsaymak. Bu varsayım her simülasyonu sistematik olarak şişirir
    ve şişme fark edilmez.
    """
    P = cfg["portfoy"]
    nakit = float(P["baslangic_sermaye_try"])
    baslangic = nakit
    ikinci_izinli = bool(P.get("ayni_isimde_ikinci_pozisyon", False))

    adaylar = _adaylar(cfg, con)
    acilis: dict[str, list[dict]] = {}
    kapanis: dict[str, list[dict]] = {}
    reddedilen: list[dict] = []

    for ad in adaylar:
        if asof and ad["asof"] > asof:
            continue
        d = _dolum(con, ad)
        if d is None:
            reddedilen.append({"asof": ad["asof"], "ticker": ad["ticker"],
                               "sebep": "giris_olmadi", "tarih": None})
            continue
        tarih, fiyat = d
        if asof and tarih > asof:
            continue                      # giriş henüz olmadı (bu tarihe göre)
        acilis.setdefault(tarih, []).append({**ad, "giris_tarih": tarih,
                                             "giris_fiyat": float(fiyat)})

    gunler = sorted(acilis)
    acik: dict[str, dict] = {}            # ticker -> pozisyon
    kapanan: list[dict] = []
    islem: list[dict] = []

    def _kapanislari_planla(poz: dict) -> None:
        if poz["exit_date"] and poz["ret_pct"] is not None:
            if not asof or poz["exit_date"] <= asof:
                kapanis.setdefault(poz["exit_date"], []).append(poz)

    # Tüm olay günleri: açılış + (planlanacak) kapanışlar birlikte yürür.
    i = 0
    islenen: set[str] = set()
    while True:
        adaylar_gun = sorted(set(gunler) | set(kapanis)) if kapanis else gunler
        kalan = [g for g in adaylar_gun if g not in islenen]
        if not kalan:
            break
        gun = kalan[0]
        islenen.add(gun)

        # --- 1) AÇILIŞLAR (o günün başındaki kontenjanla) ---
        for poz in sorted(acilis.get(gun, []), key=lambda x: (x["asof"], x["ticker"])):
            pol = _politika(cfg, poz["regime"])
            maks = int(pol.get("maks_pozisyon", 0))
            sektor_maks = int(cfg["rejim"].get("sektor_basi_maks_pozisyon", 99))
            t = poz["ticker"]

            if t in acik and not ikinci_izinli:
                sebep = "isim_zaten_acik"
            elif len(acik) >= maks:
                sebep = "kontenjan_dolu"
            elif sum(1 for p in acik.values()
                     if p["sector"] and p["sector"] == poz["sector"]) >= sektor_maks:
                sebep = "sektor_tavani"
            else:
                sebep = None

            adet = 0
            if sebep is None:
                boyut = float(poz["position_size_pct"] or 0.0)
                sermaye_o_an = nakit + sum(p["adet"] * p["giris_fiyat"]
                                           for p in acik.values())
                adet = math.floor(sermaye_o_an * boyut / 100.0 / poz["giris_fiyat"])
                if adet < 1 or adet * poz["giris_fiyat"] > nakit:
                    sebep = "sermaye_yetersiz"

            if sebep:
                reddedilen.append({"asof": poz["asof"], "ticker": t,
                                   "sebep": sebep, "tarih": gun})
                continue

            maliyet = adet * poz["giris_fiyat"]
            nakit -= maliyet
            acik[t] = {**poz, "adet": adet, "maliyet_try": round(maliyet, 2)}
            islem.append({"tarih": gun, "yon": "AL", "ticker": t, "adet": adet,
                          "fiyat": poz["giris_fiyat"], "tutar": round(maliyet, 2),
                          "prediction_id": poz["prediction_id"]})
            _kapanislari_planla(acik[t])

        # --- 2) KAPANIŞLAR (yer ertesi güne boşalır) ---
        for poz in sorted(kapanis.get(gun, []), key=lambda x: x["ticker"]):
            t = poz["ticker"]
            if acik.get(t, {}).get("prediction_id") != poz["prediction_id"]:
                continue
            p = acik.pop(t)
            # ⚠ TL sonucu `outcomes.ret_pct`'ten TÜRETİLİR, yeniden
            # hesaplanmaz. Maliyet zaten orada düşülmüş; burada ikinci kez
            # düşmek ya da farklı bir formül kullanmak, karne ile portföyün
            # ayrışacağı tam nokta olurdu.
            getiri = float(poz["ret_pct"])
            gelir = p["maliyet_try"] * (1.0 + getiri / 100.0)
            nakit += gelir
            kar = gelir - p["maliyet_try"]
            kapanan.append({
                "ticker": t, "asof": p["asof"], "giris_tarih": p["giris_tarih"],
                "cikis_tarih": poz["exit_date"], "adet": p["adet"],
                "giris_fiyat": p["giris_fiyat"], "cikis_fiyat": poz["exit_price"],
                "ret_pct": getiri, "kar_try": round(kar, 2),
                "sonuc": poz["resolution"], "prediction_id": p["prediction_id"]})
            islem.append({"tarih": poz["exit_date"], "yon": "SAT", "ticker": t,
                          "adet": p["adet"], "fiyat": poz["exit_price"],
                          "tutar": round(gelir, 2),
                          "prediction_id": p["prediction_id"]})
        i += 1
        if i > 10_000:                                     # koşum sigortası
            raise RuntimeError("portföy simülasyonu yakınsamadı")

    # --- açık pozisyonları güncel fiyattan değerle ---
    son_gun = asof or db.scalar(con, "SELECT MAX(date) FROM bars_daily")
    pozisyonlar = []
    for t, p in sorted(acik.items()):
        son = db.scalar(con, "SELECT c FROM bars_daily WHERE ticker=? AND date<=? "
                             "ORDER BY date DESC LIMIT 1", (t, son_gun))
        deger = p["adet"] * float(son) if son else None
        pozisyonlar.append({
            "ticker": t, "adet": p["adet"], "giris_tarih": p["giris_tarih"],
            "giris_fiyat": p["giris_fiyat"], "maliyet_try": p["maliyet_try"],
            "son_fiyat": son, "deger_try": None if deger is None else round(deger, 2),
            "kar_try": None if deger is None else round(deger - p["maliyet_try"], 2),
            "getiri_pct": None if not son else round(
                (float(son) / p["giris_fiyat"] - 1) * 100, 2),
            "stop_price": p["stop_price"], "t1_price": p["t1_price"],
            "time_barrier_date": p["time_barrier_date"],
            "prediction_id": p["prediction_id"], "sector": p["sector"]})

    poz_deger = sum(x["deger_try"] or x["maliyet_try"] for x in pozisyonlar)
    sermaye = nakit + poz_deger
    return {
        "baslangic_sermaye": baslangic,
        "asof": son_gun,
        "nakit": round(nakit, 2),
        "pozisyon_degeri": round(poz_deger, 2),
        "sermaye": round(sermaye, 2),
        "getiri_pct": round((sermaye / baslangic - 1) * 100, 2),
        "nakit_pct": round(nakit / sermaye * 100, 1) if sermaye else None,
        "pozisyonlar": pozisyonlar,
        "kapanan": kapanan,
        "islemler": islem,
        "reddedilen": reddedilen,
        "gerceklesen_kar_try": round(sum(k["kar_try"] for k in kapanan), 2),
    }


def holdings_gorunumu(d: dict) -> dict[str, dict]:
    """Simüle portföyü `journal.holdings` FORMATINDA döndürür.

    Böylece `eylem.siralama` ve raporun §1'i tek satır bile değişmeden çalışır:
    kontenjan artık gerçek pozisyonlardan sayılır ve "portföyde kayıtlı pozisyon
    yok → kontenjan KÖR" uyarısı kendiliğinden kalkar.

    ⚠ Elle girilen `holdings` ÜSTÜN olmalı (bkz. çağrı yeri): Mert gerçek bir
    pozisyon girdiyse o gerçektir, simülasyon onu ezemez.
    """
    return {p["ticker"]: {"ticker": p["ticker"], "qty": p["adet"],
                          "avg_cost": p["giris_fiyat"], "kagit": True}
            for p in d.get("pozisyonlar", [])}


def tl(x: float | None) -> str:
    """TL biçimi — binlik ayracı nokta, ondalık virgül (TR)."""
    if x is None:
        return "—"
    return f"{x:,.2f} TL".replace(",", " ").replace(".", ",").replace(" ", ".")


def ozet_satiri(d: dict) -> str:
    """Tek satır — Telegram ve log için."""
    return (f"portföy {tl(d['sermaye'])} "
            f"({d['getiri_pct']:+.2f}%) · {len(d['pozisyonlar'])} açık · "
            f"{len(d['kapanan'])} kapandı · nakit %{d['nakit_pct'] or 0:.0f}")
