"""Denetim — HF-01..HF-31. Geçmeyen çıktı journal'a GİREMEZ.

⚠ Yukarıdaki aralık elle yazılır ve BAYATLAYABİLİR: HF-31 eklendikten sonra
dört ayrı yer (bu dosya, `cli.py`, `README.md`, `ai/PROJECT.md`) üst ucu
30'da bırakmaya devam etti — yani 31 sert kontrol varken kullanıcıya 30
diye anlatılıyordu. Otorite `all_codes()`tir;
`tests/test_dokuman.py::test_yazili_HF_ARALIGI_gercek_kod_sayisiyla_ayni`
artık yazılı aralığı koda karşı doğruluyor.

Her kontrol `(bundle, out, con, cfg)`'nin saf fonksiyonudur ve her birinin
tek bir testi vardır (`tests/test_audit.py`).

**HF-17 taşıyıcı koldur.** Şemada fiyat alanı olmaması yalnız YAPISAL sızıntıyı
durdurur; asıl hata modu metinseldir — modelin tez cümlesine *"324 TL civarında
bir hedef makul"* yazması. HF-17 prose'daki her sayısal token'ı pakete karşı
doğrular.

⚠ AMA "imkânsız kılar" DEMEK YANLIŞ — bu dosya bir zamanlar öyle diyordu.
ÖLÇÜLDÜ (2026-07-27, canlı paket, 1054 izinli token): iki ondalıklı uydurma
fiyatların %99.5'i yakalanıyor, ama −50..+50 tamsayıların **%56'sı serbest**.
Sebep `config.denetim` beyaz listeleri (0-31 tamsayı, yıllar,
`ek_izinli_sayilar`) — bilinçli bir tercih, ama sonucu bilmek şart:
*"AKBNK %20 potansiyel taşıyor"* denetimden temiz geçer. `format_report`
"temiz" derken bunu da basar.

Tasarım kararı: uyarılar (`W-xx`) hiçbir şeyi engellemez ama rapora girer.
Her şeyi sert hata yapmak modeli işlemez hale getirir; hiçbir şeyi yapmamak
denetimi süse çevirir.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass
from typing import Any

from . import db, journal, llm_io, schema

SERT = "hard_fail"
UYARI = "warning"

_FIYAT_KALIBI = re.compile(r"\d+[.,]\d{1,2}\s*(?:TL|₺|lira)", re.IGNORECASE)
_YUZDE_KALIBI = re.compile(r"%\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*%")
_GOZLEM_KELIMELERI = ("kapanış", "kapanis", "hacim", "seviye", "kır", "kir",
                      "üst", "ust", "alt", "gün", "gun", "aç", "ac", "test",
                      "geç", "gec", "düş", "dus", "yüksel", "yuksel", "bar")


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    severity: str
    ticker: str | None
    message: str
    got: Any = None
    expected: Any = None


def hard_fails(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.severity == SERT]


def format_report(findings: list[Finding]) -> str:
    if not findings:
        return (f"✅ Denetim temiz — {len(all_codes())} sert kontrolün hiçbiri "
                "patlamadı.\n"
                "   ⚠ HF-17 küçük tamsayılara ve yuvarlak yüzdelere karşı "
                "GEÇİRGENDİR (config.denetim beyaz listeleri); prose'daki "
                "\"%20 potansiyel\" gibi ifadeler denetlenmez.")
    L = []
    sert = hard_fails(findings)
    L.append(f"{'🛑' if sert else '⚠️'} {len(sert)} sert hata, "
             f"{len(findings) - len(sert)} uyarı")
    L.append("")
    for f in findings:
        isaret = "🛑" if f.severity == SERT else "⚠️"
        hedef = f" [{f.ticker}]" if f.ticker else ""
        L.append(f"{isaret} **{f.code}**{hedef} {f.message}")
        if f.got is not None or f.expected is not None:
            L.append(f"     bulunan: {f.got!r}  ·  beklenen: {f.expected!r}")
    return "\n".join(L)


# ==================================================================== denetim
def audit(cfg: dict, bundle: dict, out: dict, con: sqlite3.Connection | None = None
          ) -> list[Finding]:
    f: list[Finding] = []
    E = cfg["llm"]["enums"]
    D = cfg["llm"]
    evren = {e["ticker"] for e in bundle.get("evren", [])}
    plan_ids = bundle.get("izin_verilen_degerler", {}).get("plan_ids", {})
    ev_map = {e["ticker"]: e for e in bundle.get("evren", [])}
    stocks = out.get("stocks") or []

    # ---------------------------------------------- kimlik ve yapı (01-06)
    if out.get("schema_version") != schema.OUTPUT_SCHEMA_VERSION:
        f.append(Finding("HF-01", SERT, None, "şema sürümü uyuşmuyor",
                         out.get("schema_version"), schema.OUTPUT_SCHEMA_VERSION))
    if out.get("bundle_sha") != bundle.get("bundle_sha"):
        f.append(Finding(
            "HF-02", SERT, None,
            "bundle_sha uyuşmuyor — BAŞKA/ESKİ bir paket analiz edilmiş olabilir. "
            "Bu sessiz bir felakettir: sayılar bugünün, yorum dünün olur.",
            out.get("bundle_sha"), bundle.get("bundle_sha")))
    if out.get("asof") != bundle.get("asof"):
        f.append(Finding("HF-03", SERT, None, "asof uyuşmuyor",
                         out.get("asof"), bundle.get("asof")))

    gorulen: list[str] = []
    for s in stocks:
        t = s.get("ticker")
        gorulen.append(t)
        if t not in evren:
            f.append(Finding("HF-04", SERT, t, "evrende olmayan ticker"))
    tekrar = {t for t in gorulen if gorulen.count(t) > 1}
    for t in sorted(tekrar):
        f.append(Finding("HF-05", SERT, t, "aynı ticker birden çok kez"))

    kapsanan = set(gorulen) | set(out.get("not_covered") or [])
    eksik = evren - kapsanan
    if eksik:
        f.append(Finding(
            "HF-06", SERT, None,
            "evrendeki her hisse ya stocks[] ya not_covered içinde olmalı — "
            "sessizce atlanamaz", sorted(eksik), "hepsi"))

    # ---------------------------------------------- enum disiplini (07-11)
    for s in stocks:
        t = s.get("ticker")
        if s.get("signal") not in E["signal"]:
            f.append(Finding("HF-07", SERT, t, "signal izinli enum dışında",
                             s.get("signal"), E["signal"]))
        if s.get("action") not in E["action"]:
            f.append(Finding("HF-08", SERT, t, "action izinli enum dışında",
                             s.get("action"), E["action"]))
        c = s.get("confidence")
        if isinstance(c, (int, float)) or c not in E["confidence"]:
            f.append(Finding("HF-09", SERT, t,
                             "confidence enum olmalı, SAYI olamaz", c, E["confidence"]))
        v, a = s.get("veto_code"), s.get("action")
        if a == "plan_reddet" and not v:
            f.append(Finding("HF-10", SERT, t, "plan_reddet için veto_code zorunlu"))
        if v and a != "plan_reddet":
            f.append(Finding("HF-10", SERT, t,
                             "veto_code var ama action plan_reddet değil", a))
        if v and v not in E["veto_code"]:
            f.append(Finding("HF-10", SERT, t, "veto_code enum dışında", v,
                             E["veto_code"]))

    mv = out.get("market_view") or {}
    if mv.get("regime_agreement") not in E["regime_agreement"]:
        f.append(Finding("HF-11", SERT, None, "regime_agreement enum dışında",
                         mv.get("regime_agreement"), E["regime_agreement"]))
    if mv.get("portfolio_action") not in E["portfolio_action"]:
        f.append(Finding("HF-11", SERT, None, "portfolio_action enum dışında",
                         mv.get("portfolio_action"), E["portfolio_action"]))

    # ---------------------------------------------- plan menüsü (12-16)
    for s in stocks:
        t, a = s.get("ticker"), s.get("action")
        pid = s.get("selected_plan_id")
        izinli = plan_ids.get(t, [])
        if pid and pid not in izinli:
            f.append(Finding("HF-12", SERT, t,
                             "UYDURULMUŞ plan_id — menüde yok", pid, izinli))
        if a == "plan_sec" and not pid:
            f.append(Finding("HF-13", SERT, t, "plan_sec ama selected_plan_id yok"))
        if a != "plan_sec" and pid:
            f.append(Finding("HF-14", SERT, t,
                             "plan_sec değil ama plan seçilmiş", a))
        e = ev_map.get(t, {})
        if pid and e.get("plan_yok_nedeni"):
            f.append(Finding("HF-15", SERT, t,
                             "plan üretilmemiş bir hisseye plan seçilmiş",
                             e.get("plan_yok_nedeni")))
        if pid and not (e.get("veri_kalitesi") or {}).get("ok", True):
            f.append(Finding("HF-16", SERT, t,
                             "veri kalitesi bozuk hisseye plan seçilmiş",
                             (e.get("veri_kalitesi") or {}).get("uyarilar")))

    # ---------------------------------------------- sayısal sızıntı (17-19)
    izinli_sayilar = llm_io.allowed_numeric_tokens(bundle, cfg)
    izinli_yuzdeler = _yuzde_tokenlari(bundle, cfg)
    for s in stocks:
        t = s.get("ticker")
        for alan in schema.STOCK_PROSE:
            metin = s.get(alan)
            if not metin:
                continue
            kacak = llm_io.numeric_tokens(metin) - izinli_sayilar
            if kacak:
                f.append(Finding(
                    "HF-17", SERT, t,
                    f"`{alan}` içinde PAKETTE OLMAYAN sayı — model sayı uydurmuş",
                    sorted(kacak)[:5], "yalnız paketteki sayılar"))
            # HF-18/19 HF-17'DEN BAĞIMSIZ olmalı. İlk sürümde ikisi de
            # `kacak` boş değilse ateşleniyordu — yani HF-17 zaten patlamışken
            # aynı olguyu tekrar raporluyorlardı ve TEK BAŞLARINA hiç
            # ateşlenemiyorlardı. "30 sert kontrol" gerçekte 28'di.
            #
            # Ayrı bir olguyu yakalamaları gerekiyordu ve şimdi yakalıyorlar:
            # sayı paketten gelse BİLE, ona fiyat/yüzde ANLAMI yüklemek
            # uydurmadır. Paketteki 95.00 bir stop fiyatıdır; "%95 olasılık"
            # ya da "hedef 95.00 TL" diye yazmak o sayıyı başka bir büyüklüğe
            # çevirir ve denetim bunu görmelidir.
            for m in _FIYAT_KALIBI.finditer(metin):
                if not _fiyat_alani_ile_tutarli(m.group(0), ev_map.get(t, {}), cfg):
                    f.append(Finding(
                        "HF-18", SERT, t,
                        f"`{alan}` içinde plandan GELMEYEN fiyat ifadesi — "
                        "sayı pakette olsa bile ona fiyat anlamı yüklenemez",
                        m.group(0), "yalnız plan/gösterge fiyatları"))
                    break
            for m in _YUZDE_KALIBI.finditer(metin):
                tok = llm_io.numeric_tokens(m.group(0))
                if tok and not (tok & izinli_yuzdeler):
                    f.append(Finding(
                        "HF-19", SERT, t,
                        f"`{alan}` içinde pakette YÜZDE olarak bulunmayan oran",
                        m.group(0), "yalnız paketteki yüzde alanları"))
                    break
    if mv.get("regime_note"):
        kacak = llm_io.numeric_tokens(mv["regime_note"]) - izinli_sayilar
        if kacak:
            f.append(Finding("HF-17", SERT, None,
                             "`regime_note` içinde pakette olmayan sayı",
                             sorted(kacak)[:5]))

    # ---------------------------------------------- tutarlılık (20-25)
    bogaci = {"strong_buy", "buy", "accumulate"}
    secilen = [s for s in stocks if s.get("action") == "plan_sec"]
    tutulan = journal.holdings(con) if con is not None else {}
    pol = (bundle.get("rejim") or {}).get("pozisyon_politikasi") or {}

    for s in stocks:
        t = s.get("ticker")
        if s.get("signal") in bogaci and s.get("action") in ("plan_reddet", "islem_yok"):
            f.append(Finding("HF-20", SERT, t,
                             "boğa sinyali ile aksiyon çelişiyor",
                             f"{s.get('signal')} / {s.get('action')}"))
        if s.get("signal") == "sell" and t not in tutulan:
            f.append(Finding("HF-21", SERT, t,
                             "olmayan pozisyon satılamaz — holdings'te yok"))
        if s.get("signal") == "strong_buy":
            pct = ((ev_map.get(t, {}).get("faktorler") or {}).get("yuzdelik"))
            esik = float(D["strong_buy_min_yuzdelik"])
            # ⚠ `pct is None` İZİN DEĞİL, SERT HATADIR. İlk sürüm `if pct is not
            # None and pct < esik` diyordu; `yuzdelik` ise YALNIZ kapıdan geçen
            # isimlerde doluyor. Yani kontrol tam da kapının ELEDİĞİ isimlerde
            # atlanıyordu. Ölçüldü (2026-07-27): canlı evrenin 18 isminden
            # 8'inde `yuzdelik: None` → HF-22 hiç ateşlenemiyordu, üstelik
            # altısı SMA200/likidite kapısının eledikleriydi.
            # Skorlanmamış ya da elenmiş bir isimde `strong_buy` zaten meşru değil.
            if pct is None:
                f.append(Finding(
                    "HF-22", SERT, t,
                    "strong_buy ama hisse SKORLANMADI/ELENDİ — sıralamadaki "
                    "yeri bilinmeyen isme en güçlü sinyal verilemez",
                    None, f">= {esik}"))
            elif pct < esik:
                f.append(Finding("HF-22", SERT, t,
                                 "strong_buy ama skor yüzdeliği bandın altında",
                                 pct, f">= {esik}"))

    if pol.get("maks_pozisyon") is not None and len(secilen) > int(pol["maks_pozisyon"]):
        f.append(Finding("HF-23", SERT, None, "rejimin izin verdiğinden fazla pozisyon",
                         len(secilen), pol["maks_pozisyon"]))
    if pol.get("sektor_basi_maks") is not None:
        sayim: dict[str, int] = {}
        for s in secilen:
            sek = ev_map.get(s.get("ticker"), {}).get("sektor")
            sayim[sek] = sayim.get(sek, 0) + 1
        for sek, n in sayim.items():
            if n > int(pol["sektor_basi_maks"]):
                f.append(Finding("HF-24", SERT, None,
                                 f"sektör tavanı aşıldı: {sek}", n,
                                 pol["sektor_basi_maks"]))
    if (mv.get("portfolio_action") == "risk_artir"
            and (bundle.get("rejim") or {}).get("etiket") == "risk-off"):
        f.append(Finding("HF-25", SERT, None,
                         "risk-off rejimde risk_artir önerilemez"))

    # ---------------------------------------------- prose kalitesi (26-29)
    min_kr = int(D["min_prose_karakter"])
    hashler: dict[str, list[str]] = {}
    haber_idleri = {h["id"] for e in bundle.get("evren", [])
                    for h in (e.get("haberler") or []) if isinstance(h, dict) and "id" in h}
    for s in stocks:
        t = s.get("ticker")
        for alan in ("thesis", "counter_scenario", "key_risk", "falsifier"):
            metin = (s.get(alan) or "").strip()
            if len(metin) < min_kr:
                f.append(Finding("HF-26", SERT, t,
                                 f"`{alan}` boş veya çok kısa", len(metin),
                                 f">= {min_kr} karakter"))
        birlesik = " ".join((s.get(a) or "") for a in
                            ("thesis", "counter_scenario", "key_risk", "falsifier"))
        if birlesik.strip():
            hashler.setdefault(_normalize_hash(birlesik), []).append(t)

        refs = s.get("news_refs") or []
        uydurma = [r for r in refs if r not in haber_idleri]
        if uydurma:
            f.append(Finding("HF-28", SERT, t, "UYDURULMUŞ haber id'si", uydurma))
        if s.get("news_reading") and not refs:
            f.append(Finding("HF-29", SERT, t,
                             "kaynaksız haber yorumu — news_refs boş"))

    for h, tickerlar in hashler.items():
        if len(tickerlar) >= 2:
            f.append(Finding("HF-27", SERT, None,
                             "ŞABLON tez: aynı prose birden çok hissede",
                             tickerlar))

    # ---------------------------------------------- yapısal sızıntı (31)
    # `schema.py` bu listeleri "savunma amaçlı geniş tutulmuştur" diye
    # tanımlıyordu ama HİÇBİR YERDE kontrol edilmiyorlardı (2026-07-27
    # denetimi: 5 sabit, 0 referans). Yani belgelenen savunma yoktu.
    #
    # Zarar sınırlıydı (`journal.ANALIST_ALANLARI` fazla anahtarı yok sayar)
    # ama SİNYAL kayboluyordu: modelin şemayı genişletmeye çalıştığı fark
    # edilmiyordu — `journal.py`'nin açıkça istediğinin tersi.
    for s in stocks:
        t = s.get("ticker")
        fazla = set(s) - schema.STOCK_ALANLARI
        sayisal = fazla & schema.YASAK_SAYISAL_ALANLAR
        if sayisal:
            f.append(Finding("HF-31", SERT, t,
                             "çıktıda YASAK sayısal alan — model hesaplanabilir "
                             "bir sayı üretmeye çalışıyor", sorted(sayisal),
                             "yalnız enum + prose"))
        elif fazla:
            f.append(Finding("HF-31", SERT, t,
                             "şema dışı alan — sessizce yok saymak, modelin "
                             "şemayı genişletmeye çalıştığını gizlerdi",
                             sorted(fazla), sorted(schema.STOCK_ALANLARI)))
        eksik_alan = schema.STOCK_ZORUNLU - set(s)
        if eksik_alan:
            f.append(Finding("HF-31", SERT, t, "zorunlu alan eksik",
                             sorted(eksik_alan), sorted(schema.STOCK_ZORUNLU)))
    for ad, kume, deger in (("market_view", schema.MARKET_ALANLARI, mv),
                            ("kök", schema.TOP_ALANLARI, out)):
        fazla = set(deger) - kume
        if fazla:
            f.append(Finding("HF-31", SERT, None,
                             f"`{ad}` içinde şema dışı alan", sorted(fazla),
                             sorted(kume)))

    # ---------------------------------------------- süreç (30)
    if con is not None:
        acik_ticker = {p["ticker"] for p in journal.open_predictions(con, bundle["asof"])}
        dusen = acik_ticker & evren - set(gorulen)
        if dusen:
            f.append(Finding("HF-30", SERT, None,
                             "açık tahmini olan hisse stocks[] içinde yok — "
                             "taşınan tez sessizce düşürülmüş", sorted(dusen)))

    # ---------------------------------------------- uyarılar (engellemez)
    for s in stocks:
        t = s.get("ticker")
        fals = (s.get("falsifier") or "").lower()
        if fals and not any(k in fals for k in _GOZLEM_KELIMELERI):
            f.append(Finding("W-01", UYARI, t,
                             "falsifier gözlemlenebilir bir olay içermiyor gibi"))
        pct = ((ev_map.get(t, {}).get("faktorler") or {}).get("yuzdelik"))
        if s.get("confidence") == "yuksek" and pct is not None and pct < 60:
            f.append(Finding("W-02", UYARI, t,
                             "yüksek güven ama skor yüzdeliği düşük", pct))
    nc = out.get("not_covered") or []
    if evren and len(nc) > len(evren) / 2:
        f.append(Finding("W-03", UYARI, None,
                         "evrenin yarısından fazlası kapsanmamış", len(nc)))
    return f


# Anahtar adı bunlardan birini içeriyorsa değeri bir ORAN'dır.
_YUZDE_ANAHTARI = re.compile(r"pct|yuzde|oran|prox", re.IGNORECASE)


def _yuzde_tokenlari(bundle: dict, cfg: dict) -> set[str]:
    """Pakette gerçekten YÜZDE olarak bulunan değerlerin token'ları.

    HF-19'un HF-17'den farkı burada: bir sayının pakette bulunması, ona ORAN
    anlamı yüklemeye izin vermez. THYAO'nun stop fiyatı 275.00 diye pakette
    duruyor olabilir; "%275 getiri" yazmak yine uydurmadır. Bu küme yalnız
    adı oran ima eden alanlardan (`*_pct`, `yuzdelik`, `*_orani`, `*_prox`)
    beslenir, artı config'in küçük tamsayı beyaz listesi (prose'da "%3 düştü"
    gibi ifadeler sayı uydurma değildir).
    """
    d = cfg["denetim"]
    basamak = int(d["ondalik_tolerans_basamak"])
    ham: set[float] = set()

    def gez(obj, yuzde_baglami: bool) -> None:
        if isinstance(obj, bool):
            return
        if isinstance(obj, (int, float)):
            if yuzde_baglami:
                ham.add(float(obj))
        elif isinstance(obj, dict):
            for k, v in obj.items():
                gez(v, yuzde_baglami or bool(_YUZDE_ANAHTARI.search(str(k))))
        elif isinstance(obj, (list, tuple)):
            for v in obj:
                gez(v, yuzde_baglami)

    gez(bundle, False)
    izin: set[str] = set()
    for v in ham:
        izin |= llm_io._varyantlar(v, basamak)
    for v in d.get("ek_izinli_sayilar", []):
        izin |= llm_io._varyantlar(float(v), basamak)
    for i in range(0, int(d["sayisal_beyaz_liste_tamsayi_maks"]) + 1):
        izin |= llm_io._varyantlar(float(i), basamak)
    return izin


def _hisse_fiyatlari(e: dict, cfg: dict) -> set[str]:
    """Bir hissenin pakette FİYAT olarak geçen değerleri (token biçiminde)."""
    basamak = int(cfg["denetim"]["ondalik_tolerans_basamak"])
    ham: set[float] = set()

    def ekle(x) -> None:
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            ham.add(float(x))

    fiyat = e.get("fiyat") or {}
    for k in ("kapanis", "onceki_kapanis", "yuksek_52h", "dusuk_52h"):
        ekle(fiyat.get(k))
    g = e.get("gostergeler") or {}
    for k in ("atr14", "sma20", "sma50", "sma200"):
        ekle(g.get(k))
    for p in (e.get("plan_menusu") or []):
        for k in ("entry_low", "entry_high", "stop_price"):
            ekle(p.get(k))
        for h in (p.get("targets") or []):
            ekle((h or {}).get("price"))

    out: set[str] = set()
    for v in ham:
        out |= llm_io._varyantlar(v, basamak)
    return out


def _fiyat_alani_ile_tutarli(ifade: str, e: dict, cfg: dict) -> bool:
    """"324.75 TL" ifadesindeki sayı, BU hissenin fiyat alanlarından biri mi?

    Paketin herhangi bir yerinde bulunmak yetmez: başka bir hissenin kapanışını
    alıp bu hisseye fiyat diye yazmak da uydurmadır ve HF-17 onu göremez.
    """
    tok = llm_io.numeric_tokens(ifade)
    return bool(tok & _hisse_fiyatlari(e, cfg))


def _normalize_hash(metin: str) -> str:
    """Sayı ve noktalama atılmış, küçük harfe indirilmiş prose'un hash'i.

    Model aynı cümleyi farklı sayılarla tekrarlıyorsa bu yine ŞABLONDUR.
    """
    t = re.sub(r"\d+", "", metin.lower())
    t = re.sub(r"[^\wçğıöşü]+", " ", t, flags=re.UNICODE).strip()
    return hashlib.sha1(t.encode("utf-8")).hexdigest()


def all_codes() -> list[str]:
    return [f"HF-{i:02d}" for i in range(1, 32)]
