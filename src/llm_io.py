"""LLM girdi paketi üretimi ve çıktı okuma.

Üç dosya yazılır:
    llm/in/<asof>/bundle.json   → DENETİMİN OTORİTESİ (makine okur)
    llm/in/<asof>/context.md    → analistin IDE'de okuduğu Türkçe hâli
    llm/in/<asof>/prompt.md     → görev + kurallar + çıktı iskeleti

`bundle_sha` ikisinde de görünür ve çıktıda birebir taşınması ZORUNLUDUR
(HF-02). Sebebi: analist yanlışlıkla dünkü paketi analiz edip bugünün
dosyasına yazarsa bu, tespit edilmedikçe sessiz bir felakettir.

**Sayısal sızıntı denetiminin tabanı burada.** `allowed_numeric_tokens`
paketteki her sayıyı kanonik biçime çevirir; `numeric_tokens` prose'daki
sayıları aynı biçime indirger. Türkçe (1.234,56) ve İngilizce (1234.56)
yazımlar aynı token'a düşer — aksi halde model sadece biçim değiştirerek
denetimi atlardı.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path

from . import db, journal, planner, schema, util

log = logging.getLogger(__name__)

# 1.234,56 · 1234.56 · 1,234.56 · 42 · -3.5 · %12
_SAYI = re.compile(r"[-+]?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|[-+]?\d+(?:[.,]\d+)?")


def _kanonik(deger: float, basamak: int = 2) -> str:
    return f"{round(float(deger), basamak):.{basamak}f}"


def _varyantlar(deger: float, basamak: int = 2) -> set[str]:
    """Bir sayının izinli yazım biçimleri — DEĞERİ DEĞİŞTİRMEYENLER.

    Model "312.00"u "312" ya da "312.0" diye yazabilir; üçü de aynı sayıdır ve
    üçü de kabul edilmelidir. Aksi halde denetim, sayı uydurmayı değil biçim
    farkını cezalandırırdı.

    ⚠ AMA yuvarlayarak biçim üretmek DELİK AÇAR: ilk sürüm her sayı için
    0/1/2 basamaklı biçimleri koşulsuz üretiyordu, yani prose'daki uydurma
    "47.3" değeri "47" varyantını da doğuruyor ve pakette 47.00 varsa
    denetimi ATLIYORDU. Artık yalnız değeri değiştirmeyen biçimler üretilir:
        47.00 → {"47", "47.0", "47.00"}      (hepsi aynı sayı)
        47.30 → {"47.3", "47.30"}            ("47" YOK — farklı sayı)
    """
    out = set()
    d = float(deger)
    for b in range(0, basamak + 1):
        r = round(d, b)
        if abs(r - d) < 1e-9:
            out.add(f"{r:.{b}f}")
    return out or {_kanonik(d, basamak)}


def _parse_sayi(s: str) -> float | None:
    """Metindeki bir sayı token'ını float'a çevirir (TR ve EN yazım)."""
    t = s.strip().replace(" ", "")
    if not t:
        return None
    nokta, virgul = t.rfind("."), t.rfind(",")
    try:
        if nokta >= 0 and virgul >= 0:
            # Sonda hangisi varsa ONDALIK ayırıcıdır
            if virgul > nokta:                       # 1.234,56 → TR
                t = t.replace(".", "").replace(",", ".")
            else:                                    # 1,234.56 → EN
                t = t.replace(",", "")
        elif virgul >= 0:
            # Tek virgül: 3 basamak grubuysa binlik, değilse ondalık
            t = t.replace(",", "") if len(t) - virgul - 1 == 3 else t.replace(",", ".")
        elif nokta >= 0 and len(t) - nokta - 1 == 3 and t.count(".") == 1:
            # 1.234 belirsiz — hem binlik hem ondalık olabilir. İKİSİNİ de dene
            # (çağıran taraf her iki yorumu da izinli sayıyor).
            return float(t.replace(".", ""))
        return float(t)
    except ValueError:
        return None


def numeric_tokens(text: str | None) -> set[str]:
    """Prose'daki sayısal token'lar, kanonik biçimde."""
    if not text:
        return set()
    out: set[str] = set()
    for m in _SAYI.finditer(text):
        ham = m.group(0)
        v = _parse_sayi(ham)
        if v is not None:
            out |= _varyantlar(v)
        # '1.234' belirsizliği: ondalık yorumu da ekle
        if ham.count(".") == 1 and len(ham) - ham.rfind(".") - 1 == 3:
            try:
                out |= _varyantlar(float(ham))
            except ValueError:
                pass
    return out


def _sayilari_topla(obj, out: set[float]) -> None:
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.add(float(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _sayilari_topla(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _sayilari_topla(v, out)
    elif isinstance(obj, str):
        # Paket içindeki metinlere gömülü sayılar da izinlidir
        for m in _SAYI.finditer(obj):
            v = _parse_sayi(m.group(0))
            if v is not None:
                out.add(v)


def allowed_numeric_tokens(bundle: dict, cfg: dict) -> set[str]:
    """Prose'da kullanılmasına İZİN VERİLEN sayısal token'lar.

    Paketteki her sayı + yıl aralığı + küçük tamsayılar + config beyaz listesi.
    Küçük tamsayılar ("3 gün", "2 hedef") sayı uydurma değildir; onları
    yasaklamak modeli anlamsız dolambaçlara iterdi.
    """
    d = cfg["denetim"]
    ham: set[float] = set()
    _sayilari_topla(bundle, ham)

    izin: set[str] = set()
    basamak = int(d["ondalik_tolerans_basamak"])
    for v in ham:
        izin |= _varyantlar(v, basamak)
    for v in d.get("ek_izinli_sayilar", []):
        izin |= _varyantlar(float(v), basamak)
    for y in range(int(d["sayisal_beyaz_liste_yil"][0]),
                   int(d["sayisal_beyaz_liste_yil"][1]) + 1):
        izin |= _varyantlar(float(y), 0)
    for i in range(0, int(d["sayisal_beyaz_liste_tamsayi_maks"]) + 1):
        izin |= _varyantlar(float(i), basamak)
    return izin


# ---------------------------------------------------------------- paket
def bundle_sha(bundle: dict) -> str:
    """Paketin parmak izi. `bundle_sha` alanı hesaba KATILMAZ (kendine referans)."""
    kopya = {k: v for k, v in bundle.items() if k != "bundle_sha"}
    return util.sha256_canonical(kopya)


def build_bundle(cfg: dict, con: sqlite3.Connection, asof: str) -> dict:
    """Analistin göreceği her şey. Paket dışında hiçbir girdi yoktur."""
    from . import indicators, macro, news, prices, universe
    from dataclasses import asdict

    from . import factors

    menu = planner.build_menu(cfg, con, asof)
    rej = menu["rejim"]
    snap = indicators.snapshot(con, asof, cfg)
    kalite = prices.quality_map(con, asof)
    sektorler = universe.sector_map(con)
    tutulan = journal.holdings(con)
    acik = journal.open_predictions(con, asof)

    # Faktör skorları pakete GİRMELİ: hem analistin sıralamayı görmesi için,
    # hem de journal `score` kolonunu doldurabilsin diye. İlk sürümde eksikti;
    # sonucu HF-22 (sıralamayı ezme kontrolü) üretimde HİÇ ateşlenemiyordu ve
    # `bist kaydet` NOT NULL hatasıyla patlıyordu. Testle yakalandı.
    fdf = factors.compute_for_date(cfg, con, asof, universe.measure(con),
                                   kalite=kalite)
    fmap = {r["ticker"]: r for _, r in fdf.iterrows()} if not fdf.empty else {}
    wh = factors.weights_hash(cfg)

    # Hisse başına "en son ne zaman analiz ettik" — haber taraması bu andan
    # ileriye bakar. Kullanıcının şartı: aynı haberler tekrar taranmasın.
    son_analiz = {r["ticker"]: r["son"] for r in db.fetch_all(
        con, "SELECT ticker, MAX(created_utc) son FROM predictions "
             "WHERE asof < ? GROUP BY ticker", (asof,))}

    evren = []
    for t in universe.live(con):
        ind = snap.get(t) or {}
        bars = prices.bars(con, t, end=asof).tail(2)
        if bars.empty:
            continue
        son = bars.iloc[-1]
        onceki = bars.iloc[0] if len(bars) > 1 else son
        planlar = [asdict(o) for o in menu["menu"].get(t, [])]
        evren.append({
            "ticker": t,
            "sektor": sektorler.get(t),
            "fiyat": {
                "kapanis": round(float(son["c"]), 4),
                "onceki_kapanis": round(float(onceki["c"]), 4),
                "gunluk_degisim_pct": round(
                    (float(son["c"]) / float(onceki["c"]) - 1) * 100, 2)
                if float(onceki["c"]) else None,
                "yuksek_52h": ind.get("high_52w"),
                "dusuk_52h": ind.get("low_52w"),
            },
            "gostergeler": {k: ind.get(k) for k in
                            ("rsi14", "macd_hist", "atr14", "atr_pct", "adx14",
                             "sma20", "sma50", "sma200", "bb_pctb")},
            "faktorler": _faktor_ozeti(fmap.get(t), wh),
            "likidite": {"medyan_gunluk_tl": ind.get("turnover_med_63")},
            "veri_kalitesi": {"ok": (kalite.get(t) or {}).get("ok", True),
                              "uyarilar": (kalite.get(t) or {}).get("reasons", [])},
            "plan_menusu": planlar,
            "plan_yok_nedeni": menu["atlanan"].get(t),
            "acik_tahminler": [
                {"prediction_id": p["prediction_id"], "asof": p["asof"],
                 "signal": p["signal"], "bariyer": p["time_barrier_date"]}
                for p in acik if p["ticker"] == t],
            # Son analizden BU YANA çıkan bildirimler — aynı haber tekrar
            # taranmaz. Sayıya çevrilmez; analist ham başlığı görür ve
            # yorumunu news_refs ile kaynağa bağlar (HF-28 uydurmayı yakalar).
            "haberler": news.bundle_view(con, t, since=son_analiz.get(t)),
        })

    bundle = {
        "bundle_version": schema.BUNDLE_VERSION,
        "asof": asof,
        "karar_gunu": menu["zaman_bariyeri"],
        "generated_utc": util.utc_now_iso(),
        "uyari": menu["uyari"],
        "takvim": {"son_kapali_seans": asof,
                   "zaman_bariyeri_tarihi": menu["zaman_bariyeri"],
                   "islem_gunu_sayisi": int(cfg["planlayici"]["zaman_bariyeri_gun"])},
        "rejim": {
            "etiket": rej["label"],
            "xu100_sma200_farki_pct": rej.get("xu100_vs_sma200_pct"),
            "genislik_sma50_ustu_pct": rej.get("breadth_above_sma50_pct"),
            "xu100_vol_yillik_21g": rej.get("xu100_vol_ann_21"),
            "makro": macro.context(cfg, con, asof),
            "pozisyon_politikasi": {
                "nakit_pct": rej["cash_pct"],
                "maks_pozisyon": rej["max_positions"],
                "sektor_basi_maks": rej["sektor_basi_maks"],
            },
        },
        "evren": evren,
        "portfoy": {"pozisyonlar": [
            {"ticker": t, "adet": r["qty"], "ortalama_maliyet": r["avg_cost"]}
            for t, r in sorted(tutulan.items())]},
        "izin_verilen_degerler": {
            **cfg["llm"]["enums"],
            "plan_ids": {e["ticker"]: [p["plan_id"] for p in e["plan_menusu"]]
                         for e in evren},
        },
        "kurallar_ozeti": schema.kurallar_ozeti(),
    }
    bundle["bundle_sha"] = bundle_sha(bundle)
    return bundle


def write_bundle(cfg: dict, bundle: dict) -> dict[str, Path]:
    """bundle.json + context.md + prompt.md yazar."""
    d = Path(cfg["paths"]["llm_in_dir"]) / bundle["asof"]
    yollar = {
        "bundle": util.write_json(d / "bundle.json", bundle),
        "context": util.ensure_parent(d / "context.md"),
        "prompt": util.ensure_parent(d / "prompt.md"),
    }
    yollar["context"].write_text(render_context(bundle), encoding="utf-8")
    yollar["prompt"].write_text(render_prompt(cfg, bundle), encoding="utf-8")
    return yollar


def read_output(cfg: dict, asof: str, tool: str = "claude-code") -> dict:
    p = util.resolve(Path(cfg["paths"]["llm_out_dir"]) / asof / "analysis.json")
    if not p.exists():
        raise FileNotFoundError(
            f"Analist çıktısı yok: {p}\n"
            f"IDE'de `llm/in/{asof}/prompt.md`'yi çalıştır ve sonucu buraya kaydet.")
    return util.read_json(p)


# ---------------------------------------------------------------- sunum
def render_context(bundle: dict) -> str:
    """Paketin okunabilir Türkçe hâli — analistin IDE'de gördüğü."""
    L = [f"# Analiz Paketi — {bundle['asof']}", "",
         f"> ⚠ {bundle['uyari']}", "",
         f"**bundle_sha:** `{bundle['bundle_sha']}` — çıktına BİREBİR kopyala.", ""]
    r = bundle["rejim"]
    L += [f"## Piyasa rejimi: **{r['etiket']}**", "",
          f"- XU100 SMA200 farkı: {_f(r['xu100_sma200_farki_pct'], '%')}",
          f"- Genişlik (SMA50 üstü): {_f(r['genislik_sma50_ustu_pct'], '%')}",
          f"- Politika: nakit %{r['pozisyon_politikasi']['nakit_pct']:.0f}, "
          f"maks {r['pozisyon_politikasi']['maks_pozisyon']} pozisyon, "
          f"sektör başına maks {r['pozisyon_politikasi']['sektor_basi_maks']}", ""]
    if r["makro"]:
        L.append("- Makro: " + ", ".join(f"{k}={_f(v)}" for k, v in r["makro"].items()))
    else:
        L.append("- Makro: **veri yok** (EVDS anahtarı girilmemiş) — bu satırlar "
                 "uydurulmaz, gizlenir.")
    L += ["", f"## Evren ({len(bundle['evren'])} hisse)", ""]

    for e in bundle["evren"]:
        L.append(f"### {e['ticker']} · {e['sektor']}")
        f = e["fiyat"]
        L.append(f"Kapanış **{f['kapanis']}** ({_f(f['gunluk_degisim_pct'], '%')} günlük) "
                 f"· 52h {_f(f['dusuk_52h'])}–{_f(f['yuksek_52h'])}")
        g = e["gostergeler"]
        L.append(f"RSI {_f(g['rsi14'])} · ATR {_f(g['atr14'])} ({_f(g['atr_pct'], '%')}) "
                 f"· ADX {_f(g['adx14'])} · SMA20 {_f(g['sma20'])} / "
                 f"SMA50 {_f(g['sma50'])} / SMA200 {_f(g['sma200'])}")
        if not e["veri_kalitesi"]["ok"]:
            L.append(f"⚠ **Veri kalitesi:** {'; '.join(e['veri_kalitesi']['uyarilar'])}")
        if e["acik_tahminler"]:
            L.append(f"📌 Açık tahmin: " + ", ".join(
                f"{a['signal']} (bariyer {a['bariyer']})" for a in e["acik_tahminler"]))
        if e["haberler"]:
            L.append("")
            L.append("**KAP bildirimleri** (son analizden bu yana):")
            for h in e["haberler"]:
                L.append(f"- `{h['id']}` · {h['tarih']} · önem: {h['onem']} — "
                         f"{h['baslik']}"
                         + (f" — {h['ozet']}" if h.get("ozet") else ""))
            L.append("")
            L.append("_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._")
        if e["plan_menusu"]:
            L.append("")
            L.append("| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |")
            L.append("|---|---|---|---|---|---|")
            for p in e["plan_menusu"]:
                t1 = p["targets"][0] if p["targets"] else {}
                L.append(f"| `{p['plan_id']}` | {p['kind']} | "
                         f"{p['entry_low']}–{p['entry_high']} | {p['stop_price']} | "
                         f"{t1.get('price')} ({t1.get('rr')}) | "
                         f"{p['position_size_pct']} |")
        else:
            L.append(f"_Plan yok: {e['plan_yok_nedeni']}_")
        L.append("")
    return "\n".join(L)


def render_prompt(cfg: dict, bundle: dict) -> str:
    """Görev tanımı + sert kurallar + çıktı iskeleti."""
    iskelet = schema.output_iskelet(bundle["asof"], bundle["bundle_sha"], "<araç>")
    L = [
        f"# Görev — BIST analizi, {bundle['asof']}", "",
        "Sen deneyimli bir portföy yöneticisisin. `context.md` dosyasındaki "
        "paketi oku ve aşağıdaki şemaya uygun TEK bir JSON üret.", "",
        f"> ⚠ {bundle['uyari']}",
        "> Bu sistemde ölçülen kenar YOKTUR. Görevin fiyat tahmin etmek değil; "
        "hazır plan geometrisini değerlendirmek, riskini adlandırmak ve "
        "sayısal olmayan bilgiyi (haber, bağlam, kurumsal durum) yorumlamaktır.", "",
        "## Sert kurallar", "",
    ]
    L += [f"{i + 1}. {k}" for i, k in enumerate(bundle["kurallar_ozeti"])]
    L += ["", "## En değerli katkın: VETO", "",
          "Bir plan geometrik olarak geçerli olabilir ama yine de kötü bir fikir "
          "olabilir — haber riski, kurumsal işlem, likidite, sektör yoğunluğu. "
          "`action: \"plan_reddet\"` + `veto_code` bunun içindir. Veto gerçek bir "
          "karardır ve performansı AYRI ölçülür: veto ettiklerin seçtiklerinden "
          "iyi giderse veto negatif değerlidir ve kapatılır.", "",
          "## Çıktı", "",
          f"`llm/out/{bundle['asof']}/analysis.json` — TEK JSON nesnesi, "
          "ilk karakter `{`, son karakter `}`. Markdown yok, açıklama yok.", "",
          "```json", util.json_dump(iskelet), "```", "",
          "## Denetim", "", "Çıktın `bist denetle` ile denetlenecek. "
          "HF kodlarından biri patlarsa journal'a GİRMEZ.",
          ]
    return "\n".join(L)


def _faktor_ozeti(satir, weights_hash: str) -> dict:
    """Faktör skorunun pakete giren hâli. Skor yoksa alanlar None kalır —
    uydurma yapılmaz, `kapilar.uygun` False olur."""
    if satir is None:
        return {"skor": None, "sira": None, "yuzdelik": None,
                "weights_hash": weights_hash,
                "kapilar": {"uygun": False, "nedenler": ["skorlanmadı"]}}
    import json
    import math

    def n(x):
        try:
            v = float(x)
            return None if not math.isfinite(v) else round(v, 4)
        except (TypeError, ValueError):
            return None

    try:
        nedenler = json.loads(satir.get("gate_reasons") or "[]")
    except (ValueError, TypeError):
        nedenler = []
    return {
        "skor": n(satir.get("score")), "sira": n(satir.get("rank")),
        "yuzdelik": n(satir.get("pct")), "weights_hash": weights_hash,
        "mom_6_1": n(satir.get("mom_6_1")), "mom_12_1": n(satir.get("mom_12_1")),
        "zirve_yakinlik": n(satir.get("high52_prox")),
        "kapilar": {"uygun": bool(satir.get("eligible")), "nedenler": nedenler},
    }


def faktor_to_journal(bundle_faktor: dict | None) -> dict:
    """Paket (Türkçe anahtar) → journal (İngilizce kolon) eşlemesi.

    Paket kullanıcıya bakar, veritabanı kolonları koda. İkisini tek yerde
    eşlemek şart: dağıtık eşleme, sessizce None yazan bir hataya dönüşür
    (nitekim ilk sürümde `skor` ile `score` ayrışıp NOT NULL patlattı).
    """
    f = bundle_faktor or {}
    return {"score": f.get("skor"), "rank": f.get("sira"), "pct": f.get("yuzdelik"),
            "weights_hash": f.get("weights_hash", "")}


def _f(v, birim: str = "") -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.2f}{birim}"
    except (TypeError, ValueError):
        return str(v)
