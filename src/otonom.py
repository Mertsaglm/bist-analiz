"""Otonom koşu — GitHub Actions'ın çağırdığı tek giriş noktası (Faz 8).

Elle koşulan zincirin (`veri gunluk → gosterge → haber cek → saglik → gunluk →
denetle → kaydet → coz → rapor`) tek komuta indirilmiş hâli.

**HATA FELSEFESİ** (`gold_tracking_system/src/daily_job.py`'den):
Her adım kendi `try/except`'i içinde koşar ve hiçbir adım diğerini KESMEZ —
`gunluk()` istisna fırlatmaz. Sebep: haber katmanı çökse bile rapor üretilmeli,
analist zinciri düşse bile deterministik plan geometrisi elde kalmalı.

Ama gold'da bunun bir bedeli yaşandı ve buraya ders olarak geçti: altı adımın
hepsi istisnayı yutunca iş HER ZAMAN yeşil bitiyordu ve `logs/` gitignore'da
olduğu için bir modül günlerce bozuk kalmıştı (ADR #004, L-002). Bu yüzden
yutmak yetmez, SINIFLANDIRMAK gerekir:

    KRITIK_ADIMLAR düşerse → çıkış kodu 1 → Actions kırmızı → Telegram'a hata
    diğerleri düşerse      → çıkış 0, ama rapor "eksik" olduğunu SÖYLER

`analist` bilerek kritik DEĞİL: zincirin tamamı düşse bile o gün üretilen plan
geometrisi ve risk çerçevesi tek başına değerlidir ve rapor "analist çıktısı
yok" ibaresini zaten basar (ADR #013).

**Sağlık kapısı GERÇEK bir kapıdır:** `bist saglik` KRİTİK dönerse sonraki
adımlar HİÇ koşmaz. Bayat göstergeyle üretilen paket boş ama şeklen geçerli
olur (L-009) — ve o paketi analiz etmek, sistemin en pahalı hata sınıfıdır.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date

from . import db, report, saglik as sag, telegram_bist as tg, util

log = logging.getLogger(__name__)

# Bu adımlardan biri düşerse koşu BAŞARISIZ sayılır (çıkış 1).
# `analist` ve `haber` listede YOK: ikisi de düşse rapor hâlâ anlamlıdır.
KRITIK_ADIMLAR = ("veri", "gosterge", "saglik", "rapor")


def _hata(sonuc: dict, adim: str, e: Exception) -> None:
    log.warning("%s hata: %s", adim, e)
    sonuc.setdefault("hatalar", {})[adim] = str(e)[:500]


def _say(x, ond: int = 2, birim: str = "") -> str:
    """Eksik değer `—` basar; `0.0` ile `None`u ASLA aynı göstermez."""
    if x is None:
        return "—"
    try:
        return f"{float(x):.{ond}f}{birim}"
    except (TypeError, ValueError):
        return str(x)


def basarisiz_mi(sonuc: dict) -> list[str]:
    return [a for a in KRITIK_ADIMLAR if a in sonuc.get("hatalar", {})]


# ---------------------------------------------------------------- günlük
def gunluk(cfg: dict, con: sqlite3.Connection, *, bugun: date | None = None,
           analist_calistir: bool = True) -> dict:
    """Tam günlük koşu. İstisna FIRLATMAZ; sonucu sözlük olarak döner."""
    from .calendar_bist import BistCalendar

    sonuc: dict = {"adimlar": {}}
    cal = BistCalendar(cfg, con)
    gun = bugun or date.today()

    # 0) Takvim kapısı. Cron hafta içi TATİLLERİ bilmez; bilseydi bile tatil
    # günü koşmak yeni bar olmadığı için `saglik`i boş yere KRİTİK yapardı.
    if not cal.is_trading_day(gun):
        sonuc["atlandi"] = f"{gun.isoformat()} işlem günü değil"
        log.info(sonuc["atlandi"])
        return sonuc

    # 1) Fiyat verisi (+ kalite kapısı otomatik koşar)
    try:
        from . import prices
        r = prices.daily(cfg, con)
        sonuc["adimlar"]["veri"] = (
            f"{r['tickers']} hisse · {r['hayalet_silinen']} hayalet bar ayıklandı "
            f"· kalite {r['kalite_gecmeyen']} isim geçemedi")
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "veri", e)

    # 2) Göstergeler — L-009'UN KALICI ÇÖZÜMÜ.
    # Bu adım akışın İÇİNDE olduğu için artık unutulamaz. Elle koşulan sırada
    # yoktu ve README'de de geçmiyordu; sonuç: 0 skorlanan isim, 0 plan, rejim
    # paydası 0 olan "geçerli görünen" boş bir paket. Sıfır hata koduyla.
    try:
        from . import indicators
        r = indicators.compute_and_store(cfg, con)
        sonuc["adimlar"]["gosterge"] = (
            f"{sum(r['satir'].values()):,} satır / {r['tickers']} ticker".replace(",", "."))
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "gosterge", e)

    # 3) Haber (KAP) — kritik DEĞİL; düşerse pakette `haber_taramasi.ok=False`
    # olur ve analist "haber yok" ile "bakılmadı"yı ayırt edebilir.
    try:
        from . import news
        r = news.sync(cfg, con)
        sonuc["adimlar"]["haber"] = f"{r.get('yazilan', 0)} bildirim"
        if r.get("atlanan_aralik"):
            sonuc.setdefault("uyarilar", []).append(
                f"KAP atlanan aralık: {r['atlanan_aralik']}")
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "haber", e)

    # 4) SAĞLIK KAPISI — buradan sonrası veriye güvenir.
    try:
        s = sag.kontrol(cfg, con)
        sonuc["saglik"] = s
        sonuc["adimlar"]["saglik"] = sag.tek_satir(s)
        if s["kritik"]:
            # Kapı KAPALI: paket üretme, analiz etme, rapor yazma.
            _hata(sonuc, "saglik",
                  RuntimeError("KRİTİK: " + "; ".join(f"{ad} ({m})"
                                                      for _, ad, m in s["kritik"])))
            _bildir_hata(cfg, sonuc, gun)
            return sonuc
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "saglik", e)
        _bildir_hata(cfg, sonuc, gun)
        return sonuc

    asof = db.scalar(con, "SELECT MAX(date) FROM bars_daily")
    sonuc["asof"] = asof

    # 5) LLM paketi
    try:
        from . import llm_io
        bundle = llm_io.build_bundle(cfg, con, asof)
        llm_io.write_bundle(cfg, bundle)
        planli = sum(1 for e in bundle["evren"] if e["plan_menusu"])
        sonuc["adimlar"]["paket"] = f"{len(bundle['evren'])} hisse · {planli} planlı"
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "paket", e)
        bundle = None

    # 6) Analist zinciri — KRİTİK DEĞİL (docstring'deki gerekçe)
    if analist_calistir and bundle is not None:
        try:
            from . import analist
            r = analist.calistir(cfg, con, asof)
            sonuc["analist_model"] = r["model"]
            sonuc["adimlar"]["analist"] = f"{r['model']} ({len(r['denemeler'])} deneme)"
            _kaydet(cfg, con, asof, bundle, r["out"], sonuc)
        except Exception as e:                              # noqa: BLE001
            _hata(sonuc, "analist", e)

    # 7) Çözüm — rapordan ÖNCE. Gold dersi: bugün kapanan tahminler o günün
    # raporundaki karneye girmeli, bir gün gecikmeli değil.
    try:
        from . import resolver
        r = resolver.resolve_open(cfg, con)
        sonuc["cozulen_n"] = r["cozulen"]
        sonuc["cozulen_dagilim"] = r["dagilim"]
        sonuc["adimlar"]["coz"] = f"{r['cozulen']} çözüldü · {r['hala_acik']} açık"
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "coz", e)

    # 8) Rapor + Telegram (gold deseni: TG gönderimi rapor adımının İÇİNDE —
    # bildirimin sessizce kaybolması, bildirimin kendisinden tehlikelidir)
    try:
        from . import journal
        b = bundle if bundle is not None else util.read_json(
            f"{cfg['paths']['llm_in_dir']}/{asof}/bundle.json")
        if b is None:
            raise RuntimeError(f"paket yok: llm/in/{asof}/bundle.json")
        analiz = db.fetch_all(
            con, "SELECT * FROM predictions WHERE asof = ? ORDER BY ticker", (asof,))
        tutulan = journal.holdings(con)
        metin = report.daily_report(cfg, b, holdings=tutulan, analiz=analiz)
        sonuc["rapor"] = report.write(cfg, f"gunluk_{asof}.md", metin)

        ozet = report.telegram_ozet(
            cfg, b, analiz=analiz, holdings=tutulan,
            cozulen=[{"resolution": k} for k, v in
                     (sonuc.get("cozulen_dagilim") or {}).items() for _ in range(v)],
            analist_model=sonuc.get("analist_model"),
            saglik=sag.tek_satir(sonuc["saglik"]) if sonuc.get("saglik") else None)
        if sonuc.get("hatalar"):
            ozet += "\n\n⚠ Düşen adım: " + ", ".join(sorted(sonuc["hatalar"]))
        tg.bildir(cfg, ozet)
        sonuc["adimlar"]["rapor"] = sonuc["rapor"]
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "rapor", e)

    return sonuc


def _kaydet(cfg: dict, con: sqlite3.Connection, asof: str, bundle: dict,
            out: dict, sonuc: dict) -> None:
    """Denetimden geçmiş analist çıktısını journal'a yazar.

    `cli.cmd_kaydet` ile aynı iş; buraya kopyalanmasının sebebi katman
    disiplini (hiçbir modül `cli`'ı import edemez). Denetim BURADA tekrar
    koşmaz: `analist.calistir` yalnız sert hatasız çıktı döndürür — iki kez
    denetlemek, denetimin nerede yapıldığı sorusunu bulanıklaştırır.
    """
    from . import journal, planner

    menu = planner.build_menu(cfg, con, asof)
    for opts in menu["menu"].values():
        planner.store(cfg, con, opts)

    from . import llm_io
    run_id = journal.create_run(cfg, con, asof=asof, tool=out.get("tool", "diger"),
                                bundle_sha=bundle["bundle_sha"],
                                output_path=f"llm/out/{asof}/analysis.json")
    plan_map = {p["plan_id"]: p
                for ps in planner.load_for_date(cfg, con, asof).values() for p in ps}
    ev = {e["ticker"]: e for e in bundle["evren"]}
    n = 0
    for st in out["stocks"]:
        t = st["ticker"]
        plan = plan_map.get(st.get("selected_plan_id")) or {}
        analist_alanlari = {k: v for k, v in st.items()
                            if k in journal.ANALIST_ALANLARI}
        journal.record(cfg, con, run_id=run_id, asof=asof, ticker=t,
                       analist=analist_alanlari, plan=plan,
                       faktor=llm_io.faktor_to_journal(ev[t].get("faktorler")),
                       regime=bundle["rejim"]["etiket"],
                       referans={"close": ev[t]["fiyat"]["kapanis"],
                                 "atr14": ev[t]["gostergeler"].get("atr14")})
        n += 1
    sonuc["kaydedilen"] = n
    sonuc["run_id"] = run_id


def _bildir_hata(cfg: dict, sonuc: dict, gun: date) -> None:
    """Sağlık kapısı kapandığında tek satırlık alarm.

    Bu bildirim try/except içinde: Telegram da çökmüş olabilir ve o durumda
    asıl hatanın (sağlık) üstünü örtmemeli.
    """
    try:
        mesaj = (f"🛑 BIST otonom — {gun.isoformat()}\n"
                 f"Koşu DURDURULDU.\n"
                 + "\n".join(f"· {a}: {m}" for a, m in
                             sorted(sonuc.get("hatalar", {}).items())))
        tg.bildir(cfg, mesaj)
    except Exception as e:                                  # noqa: BLE001
        log.warning("hata bildirimi gönderilemedi: %s", e)


# ---------------------------------------------------------------- haftalık
def haftalik(cfg: dict, con: sqlite3.Connection) -> dict:
    """Haftalık değerlendirme özeti — araç BAŞINA ayrı ölçüm.

    Araçları karıştırmamak bu projede sert bir kural (`evaluate.kaynak_sec`):
    `replay` VEKİL bir analisttir ve alfası gerçek LLM kayıtlarıyla aynı potaya
    girmez. Burada da her araç ayrı ayrı ölçülür — hangi modelin daha iyi
    analist olduğu sorusu böylece kanaatle değil VERİYLE cevaplanır (ADR #013).
    """
    from . import evaluate

    sonuc: dict = {"adimlar": {}}
    L = [f"📈 BIST haftalık — {report.bugun()}", ""]

    try:
        araclar = evaluate.araclar(con)
        if not araclar:
            L.append("Henüz çözülmüş tahmin yok — ölçüm başlamadı.")
        for arac, n in sorted(araclar.items(), key=lambda kv: -kv[1]):
            e = evaluate.run(cfg, con, tool=arac)
            metin = report.evaluate_report(cfg, e)
            report.write(cfg, f"degerlendirme_{arac}_{report.bugun()}.md", metin)
            a = e.get("alfa") or {}
            ic = e.get("ic") or {}
            L.append(f"🔹 {arac} (N={n})")
            L.append(f"   alfa {_say(a.get('ort'), 2, 'pp')} · "
                     f"hüküm: {a.get('hukum', '—')}")
            if ic.get("n"):
                L.append(f"   IC {_say(ic.get('ort'), 3)} (N={ic['n']})")
            L.append("")
        sonuc["adimlar"]["degerlendir"] = f"{len(araclar)} araç"
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "degerlendir", e)
        L.append(f"⚠ Değerlendirme koşulamadı: {e}")

    L.append("`ölçüm yetersiz` bir sonuçtur, eksiklik değil.")
    try:
        tg.bildir(cfg, "\n".join(L))
    except Exception as e:                                  # noqa: BLE001
        _hata(sonuc, "bildir", e)
    sonuc["ozet"] = "\n".join(L)
    return sonuc
