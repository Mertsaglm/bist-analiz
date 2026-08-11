"""BIST analiz CLI.

Her komut ince bir sarmalayıcıdır; iş mantığı modüllerde durur. Bu, ileride
GitHub Actions'a bağlamayı "dosya taşımak" değil "satır eklemek" yapar.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

from . import db, dbdump, logging_setup, macro, prices, universe, util
from .calendar_bist import BistCalendar

UYARI = ("Bu bir karar destek aracıdır, YATIRIM TAVSİYESİ DEĞİLDİR. "
         "Kişisel ve deneysel kullanım içindir.")


def _cfg() -> dict:
    cfg = util.load_config()
    logging_setup.setup(cfg)
    return cfg


def _tl(x: float | None) -> str:
    return "—" if x is None else f"{x/1e6:,.0f} mn"


# ---------------------------------------------------------------- veri
def cmd_veri(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    universe.sync(cfg, con)

    if args.alt == "backfill":
        print("Endeksler ve kur çekiliyor…")
        idx = prices.sync_indices(cfg, con)
        for ad, n in idx.items():
            print(f"  {ad:8} {n:>6} bar")

        tickers = universe.all_tickers(con)
        print(f"\n{len(tickers)} hisse çekiliyor (bu birkaç dakika sürer)…")
        r = prices.backfill(cfg, con, tickers)
        for t, n in r["bars"].items():
            print(f"  {t:8} {n:>6} bar")
        print(f"\nHayalet bar ayıklandı: {r['hayalet_silinen']} satır "
              f"(Yahoo, BIST tatillerinde v=0 & o=h=l=c bar üretiyor)")

        print("\nKurumsal işlemler…")
        a = prices.sync_actions(cfg, con, tickers)
        print(f"  {a['kayit']} kayıt")

    elif args.alt == "gunluk":
        prices.sync_indices(cfg, con, start=(
            date.today().replace(year=date.today().year - 1)).isoformat())
        r = prices.daily(cfg, con)
        print(f"{r['tickers']} hisse güncellendi ({r['start']} sonrası); "
              f"{r['hayalet_silinen']} hayalet bar ayıklandı")
        print(f"Kalite kapısı otomatik koştu: {r['kalite_degerlendirilen']} "
              f"ticker, {r['kalite_gecmeyen']} tanesi geçemedi "
              f"(ayrıntı: `bist veri kalite`)")

    elif args.alt == "temizle":
        r = prices.purge_phantom_bars(cfg, con)
        print(f"Hayalet bar ayıklandı: {r['silinen']} satır (sınır: {r['sinir']})")

    elif args.alt == "kalite":
        rows = prices.assess_quality(cfg, con)
        print(f"\nVeri kalitesi — {rows[0]['date'] if rows else '—'}\n")
        print(f"{'ticker':<8}{'bar':>5}{'sıfır hac.':>12}{'boşluk':>8}"
              f"{'bayat':>7}{'sıçrama':>9}  durum")
        print("-" * 70)
        for r in sorted(rows, key=lambda x: (x["ok"], x["ticker"])):
            zv = "—" if r["zero_vol_ratio_252"] is None else f"%{r['zero_vol_ratio_252']*100:.1f}"
            durum = "OK" if r["ok"] else "; ".join(r["reasons"])
            print(f"{r['ticker']:<8}{r['bars_252']:>5}{zv:>12}"
                  f"{str(r['max_gap_days'] or '—'):>8}{str(r['stale_close_days'] or '—'):>7}"
                  f"{str(r['unexplained_jump'] or 0):>9}  {durum}")
        kotu = [r for r in rows if not r["ok"]]
        print(f"\n{len(rows) - len(kotu)}/{len(rows)} ticker kapıdan geçti.")
    con.close()
    return 0


# ---------------------------------------------------------------- evren
def cmd_evren(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)

    if args.alt == "sync":
        r = universe.sync(cfg, con)
        print(f"{r['yazilan']} ticker yazıldı — canlı {r['canli']}, ölçüm {r['olcum']}")
        if r["silinen"]:
            print(f"YAML'dan silindiği için kaldırıldı: {', '.join(r['silinen'])}")

    elif args.alt == "tara":
        print("Canlı yoklama (2 yıl)…\n")
        rows = universe.scan(cfg)
        print(f"{'ticker':<8}{'bar':>6}{'ilk tarih':>13}{'medyan TL':>13}"
              f"{'vol%':>7}{'sıfır%':>8}  ihlaller")
        print("-" * 82)
        for r in rows:
            if not r["ok"]:
                print(f"{r['ticker']:<8}{'—':>6}{'—':>13}{'—':>13}{'—':>7}{'—':>8}  VERİ YOK")
                continue
            print(f"{r['ticker']:<8}{r['bars']:>6}{r['first_date']:>13}"
                  f"{_tl(r['median_turnover_try']):>13}"
                  f"{r['vol_ann_pct']:>7.1f}{r['zero_vol_ratio']*100:>8.1f}"
                  f"  {'; '.join(r['ihlaller']) or '—'}")
        ihlalli = [r for r in rows if r["ihlaller"]]
        print(f"\n{len(rows) - len(ihlalli)}/{len(rows)} kriterleri karşılıyor.")
    con.close()
    return 0


# ---------------------------------------------------------------- takvim
def cmd_takvim(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    cal = BistCalendar(cfg, con)

    d = util.parse_date(args.tarih) if args.tarih else date.today()
    print(f"Türetilmiş geçmiş sınırı (son {cfg['takvim']['turet_kaynak_endeks']} barı): "
          f"{cal.son_bar or '— (önce veri çek)'}")
    print(f"{d}: {'İŞLEM GÜNÜ' if cal.is_trading_day(d) else 'kapalı'}"
          f"{' (yarım gün)' if cal.is_half_day(d) else ''}"
          f"  [{'otoriter/bar' if cal.is_derived(d) else 'tahmini/tatil listesi'}]")
    if args.gun:
        hedef = cal.add_trading_days(d, args.gun)
        geri = cal.trading_days_between(d, hedef)
        print(f"{d} + {args.gun} işlem günü = {hedef}  (ters kontrol: {geri})")
    print(f"Şu anki seans durumu: {cal.session_state()}")
    con.close()
    return 0


# ---------------------------------------------------------------- makro
def cmd_makro(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from .sources import evds as _evds

    if not _evds.available():
        print("EVDS_API_KEY yok (.env). Makro katmanı boş kalır — rapor ilgili "
              "satırları GİZLER, uydurma yapılmaz.")
        con.close()
        return 1

    if args.alt == "backfill":
        for k, n in macro.backfill(cfg, con).items():
            print(f"  {k:18} {n:>6} satır")
    elif args.alt == "gunluk":
        for k, n in macro.daily(cfg, con).items():
            print(f"  {k:18} {n:>6} satır")
    elif args.alt == "durum":
        ctx = macro.context(cfg, con)
        if not ctx:
            print("Makro verisi yok.")
        for k, v in ctx.items():
            print(f"  {k:22} {v:.2f}" if isinstance(v, float) else f"  {k:22} {v}")
        print(f"\n  eksik oranı: %{macro.null_pct(cfg, ctx):.0f}")
    con.close()
    return 0


# ---------------------------------------------------------------- gösterge
def cmd_gosterge(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import indicators

    r = indicators.compute_and_store(cfg, con, start=args.start)
    toplam = sum(r["satir"].values())
    bos = [t for t, n in r["satir"].items() if n == 0]
    print(f"{r['set_version']}: {toplam:,} satır / {r['tickers']} ticker".replace(",", "."))
    if bos:
        print(f"Yetersiz bar nedeniyle atlanan: {', '.join(bos)}")
    con.close()
    return 0


# ---------------------------------------------------------------- ölçüm
def cmd_backtest(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import backtest, report

    print("Ölçüm koşuyor (yürüyen-ileri, örtüşmeyen pencere)…\n")
    sonuc = backtest.full_measurement(cfg, con, start=args.start, end=args.end,
                                      top_frac=args.top_frac)
    metin = report.backtest_report(cfg, sonuc)
    yol = report.write(cfg, f"olcum_{sonuc['tarih']}.md", metin)

    print(metin)
    print(f"\n\nRapor yazıldı: {yol}")
    con.close()
    # Kapı kapalıysa çıkış kodu 2 — otomasyon bunu fark edebilsin.
    return 0 if sonuc["kapi"]["acik"] else 2


# ---------------------------------------------------------------- plan
def cmd_plan(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import planner

    asof = args.asof or db.scalar(con, "SELECT MAX(date) FROM bars_daily")
    r = planner.build_menu(cfg, con, asof,
                           tickers=[args.ticker.upper()] if args.ticker else None)
    rj = r["rejim"]
    print(f"Plan menüsü — {asof}  (zaman bariyeri {r['zaman_bariyeri']})")
    print(f"Rejim: {rj['label']}  ·  nakit %{rj['cash_pct']:.0f}  ·  "
          f"maks {rj['max_positions']} pozisyon  ·  boyut ×{rj['size_multiplier']}")
    print(f"\n\u26a0 {r['uyari']}\n")

    if not r["menu"]:
        print("Geçerli plan üretilmedi.")
    for t, opts in sorted(r["menu"].items()):
        print(f"\n{t}")
        for o in opts:
            hedefler = ", ".join(f"{h['price']:.2f} (R:R {h['rr']})" for h in o.targets)
            print(f"  [{o.plan_id}] {o.kind} · tetik {o.entry_trigger}")
            print(f"     giriş {o.entry_low:.2f}–{o.entry_high:.2f} ({o.entry_zone_status})"
                  f" · stop {o.stop_price:.2f} ({o.stop_method}, {o.stop_atr_multiple}×ATR)")
            print(f"     hedefler: {hedefler}")
            print(f"     boyut %{o.position_size_pct:.1f} · maks kayıp "
                  f"%{o.max_loss_pct_of_portfolio:.2f} · {o.daily_limit_note}")
    if r["atlanan"]:
        print(f"\nPlan üretilmeyenler ({len(r['atlanan'])}):")
        for t, neden in sorted(r["atlanan"].items()):
            print(f"  {t:8} {neden}")

    if args.kaydet:
        n = sum(planner.store(cfg, con, o) for o in r["menu"].values())
        print(f"\n{n} plan kaydedildi.")
    con.close()
    return 0


# ---------------------------------------------------------------- LLM sınırı
def cmd_gunluk(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import llm_io

    asof = args.asof or db.scalar(con, "SELECT MAX(date) FROM bars_daily")
    print(f"Paket hazırlanıyor — {asof}\n")
    bundle = llm_io.build_bundle(cfg, con, asof)
    yollar = llm_io.write_bundle(cfg, bundle)
    planli = sum(1 for e in bundle["evren"] if e["plan_menusu"])
    print(f"  evren        : {len(bundle['evren'])} hisse ({planli} tanesinde plan var)")
    print(f"  rejim        : {bundle['rejim']['etiket']}")
    print(f"  bundle_sha   : {bundle['bundle_sha'][:16]}…")
    for k, v in yollar.items():
        print(f"  {k:12} : {v}")
    print(f"\nŞimdi IDE'de {yollar['prompt']} dosyasını çalıştır ve çıktıyı\n"
          f"llm/out/{asof}/analysis.json olarak kaydet. Sonra: bist denetle")
    con.close()
    return 0


def cmd_denetle(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import audit, llm_io

    asof = args.asof or db.scalar(con, "SELECT MAX(date) FROM bars_daily")
    bundle = util.read_json(f"{cfg['paths']['llm_in_dir']}/{asof}/bundle.json")
    if bundle is None:
        print(f"Paket yok: llm/in/{asof}/bundle.json — önce `bist gunluk`")
        con.close()
        return 1
    try:
        out = llm_io.read_output(cfg, asof)
    except FileNotFoundError as e:
        print(e)
        con.close()
        return 1

    bulgular = audit.audit(cfg, bundle, out, con)
    print(audit.format_report(bulgular))
    con.close()
    return 0 if not audit.hard_fails(bulgular) else 2


def cmd_kaydet(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import audit, journal, llm_io, planner

    asof = args.asof or db.scalar(con, "SELECT MAX(date) FROM bars_daily")
    bundle = util.read_json(f"{cfg['paths']['llm_in_dir']}/{asof}/bundle.json")
    out = llm_io.read_output(cfg, asof)
    bulgular = audit.audit(cfg, bundle, out, con)
    sert = audit.hard_fails(bulgular)
    if sert:
        print(audit.format_report(bulgular))
        print("\n🛑 Sert hata var — journal'a YAZILMADI.")
        con.close()
        return 2

    # Planlar journal FK'sı için önce saklanır
    menu = planner.build_menu(cfg, con, asof)
    for opts in menu["menu"].values():
        planner.store(cfg, con, opts)

    run_id = journal.create_run(cfg, con, asof=asof, tool=out.get("tool", "diger"),
                                bundle_sha=bundle["bundle_sha"])
    # Çıktı mühürlenir ve run'a özel dosyaya kopyalanır — `analysis.json`
    # ezilebilir bir yoldur ve gerçekten ezildi (2026-07-30). Simetri: girdi
    # `bundle_sha` ile, çıktı `output_sha` ile mühürlü (L-008).
    m = journal.muhurle_cikti(cfg, con, run_id=run_id, asof=asof)
    plan_map = {p["plan_id"]: p for ps in planner.load_for_date(cfg, con, asof).values()
                for p in ps}
    ev = {e["ticker"]: e for e in bundle["evren"]}
    n = 0
    for st in out["stocks"]:
        t = st["ticker"]
        plan = plan_map.get(st.get("selected_plan_id")) or {}
        analist = {k: v for k, v in st.items() if k in journal.ANALIST_ALANLARI}
        journal.record(cfg, con, run_id=run_id, asof=asof, ticker=t,
                       analist=analist, plan=plan,
                       faktor=llm_io.faktor_to_journal(ev[t].get("faktorler")),
                       regime=bundle["rejim"]["etiket"],
                       referans={"close": ev[t]["fiyat"]["kapanis"],
                                 "atr14": ev[t]["gostergeler"].get("atr14")})
        n += 1
    print(f"✅ {n} tahmin journal'a yazıldı (run {run_id}).")
    print(f"   çıktı mührü: {m.get('sha', '—')[:12]} → {m.get('yol', m.get('not'))}")
    if bulgular:
        print(f"\n{len(bulgular)} uyarı:")
        print(audit.format_report(bulgular))
    con.close()
    return 0


# ---------------------------------------------------------------- replay / journal
def cmd_replay(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import replay

    if args.sifirla:
        r = replay.reset(cfg, con)
        print(f"Replay temizlendi: {r['run']} run, {r['tahmin']} tahmin, "
              f"{r['sonuc']} sonuç silindi (gerçek analiz kayıtlarına dokunulmadı)")
        con.close()
        return 0

    print(f"Replay koşuyor: {args.start} … {args.end} (LLM YOK, vekil analist)\n")
    r = replay.run(cfg, con, start=args.start, end=args.end,
                   adim_gun=args.adim, top_n=args.top)
    print(f"Dönem      : {r['donem']}")
    print(f"Tahmin     : {r['tahmin']}   (plan üretilemeyen: {r['plan_yok']})")
    print(f"Atlanan gün: {r['atlanan_gun']}")
    c = r["cozum"]
    print(f"\nÇözüm: {c['cozulen']} çözüldü, {c['hala_acik']} açık")
    for k, v in sorted(c["dagilim"].items()):
        print(f"  {k:16} {v}")
    con.close()
    return 0


def cmd_journal(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import journal

    if args.alt == "durum":
        s = journal.summary(con)
        print(f"Tahmin : {s['tahmin']}  (çözülen {s['cozulen']}, açık {s['acik']})")
        print(f"Run    : {s['run']}")
        print(f"Aralık : {s['ilk']} … {s['son']}")
    elif args.alt == "acik":
        for p in journal.open_predictions(con):
            print(f"  {p['asof']}  {p['ticker']:8} {p['signal']:12} "
                  f"bariyer {p['time_barrier_date']}")
    con.close()
    return 0


def cmd_coz(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import resolver

    r = resolver.resolve_open(cfg, con)
    print(f"{r['cozulen']} tahmin çözüldü, {r['hala_acik']} hâlâ açık")
    for k, v in sorted(r["dagilim"].items()):
        print(f"  {k:16} {v}")
    con.close()
    return 0


# ---------------------------------------------------------------- değerlendirme
def cmd_degerlendir(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import evaluate, report

    try:
        e = evaluate.run(cfg, con, tool=args.tool)
    except evaluate.KaynakKarisik as hata:
        print(f"🛑 {hata}")
        con.close()
        return 2
    metin = report.evaluate_report(cfg, e)
    yol = report.write(cfg, f"degerlendirme_{report.bugun()}.md", metin)
    print(metin)
    print(f"\n\nRapor yazıldı: {yol}")
    con.close()
    return 0


def cmd_rapor(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import journal, llm_io, report

    asof = args.asof or db.scalar(con, "SELECT MAX(date) FROM bars_daily")
    bundle = util.read_json(f"{cfg['paths']['llm_in_dir']}/{asof}/bundle.json")
    if bundle is None:
        print(f"Paket yok — önce `bist gunluk --asof {asof}`")
        con.close()
        return 1
    # Analistin o güne ait kayıtları rapora GİRER. Yoksa rapor bunu açıkça
    # yazar; sessizce deterministik katmanı "rapor" diye sunmaz.
    analiz = db.fetch_all(
        con, "SELECT * FROM predictions WHERE asof = ? ORDER BY ticker", (asof,))
    metin = report.daily_report(
        cfg, bundle, holdings=journal.holdings(con), analiz=analiz,
        acik_plan=len([p for p in journal.open_predictions(con)
                       if p["action"] == "plan_sec"]))
    yol = report.write(cfg, f"gunluk_{asof}.md", metin)
    print(metin)
    print(f"\n\nRapor yazıldı: {yol}")
    con.close()
    return 0


def cmd_portfoy(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import journal

    if args.alt == "ekle":
        journal.set_holding(con, args.ticker, args.adet, args.maliyet)
        print(f"{args.ticker.upper()}: {args.adet} adet kaydedildi.")
    elif args.alt == "sil":
        journal.set_holding(con, args.ticker, 0)
        print(f"{args.ticker.upper()} silindi.")
    elif args.alt == "listele":
        h = journal.holdings(con)
        if not h:
            print("Portföyde kayıtlı pozisyon yok.")
        for t, r in sorted(h.items()):
            print(f"  {t:8} {r['qty']:>10.0f} adet  ort. maliyet "
                  f"{r['avg_cost'] if r['avg_cost'] is not None else '—'}")
    con.close()
    return 0


# ---------------------------------------------------------------- haber
def cmd_haber(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import news

    kod = 0
    if args.alt == "cek":
        r = news.sync(cfg, con, full=args.tam, gun=args.gun)
        if r.get("atlandi"):
            print("KAP kapalı (config.sources.kap.enabled)")
        else:
            print(f"{r['bildirim']} bildirim tarandı, {r['yazilan']} satır yazıldı "
                  f"({r['ticker']} ticker) · başlangıç: {r['since']}")
            if r.get("tickersiz"):
                print(f"  {r['tickersiz']} bildirim hisseye bağlı değildi "
                      f"(piyasa geneli) — yazılmadı")
            # ⚠ "0 bildirim" ile "çekilemedi" AYNI ÇIKTIYA DÜŞEMEZ.
            if r.get("atlanan_aralik"):
                print(f"  ⚠ ATLANAN ARALIK: {r['atlanan_aralik']} — bu boşluk "
                      f"bir daha çekilmez; kapatmak için `bist haber cek --tam`")
                kod = 1
            if r.get("hata"):
                print(f"  🛑 KAP HATASI: {r['hata']}\n"
                      f"     Bu bir 'haber yok' durumu DEĞİL. Paketteki boş "
                      f"haber listelerine güvenme.")
                kod = 2
        # İleriye dönük takvim AYNI komutta çekilir. L-002: "bir kere elle
        # çalıştırdım, gerisi otomatik" varsayımı yanlıştır — otomatik boru
        # hattına bağlı olmayan tablo donar ve hiçbir hata fırlatmaz. Donması
        # burada `bilinmiyor`un sessizce kalıcılaşması demekti.
        bb = news.sync_beklenen(cfg, con)
        if bb.get("not") and not bb["ok"]:
            print(f"  ⚠ beklenen bildirim takvimi: {bb['not']}")
            kod = max(kod, 1)
        elif bb["ok"]:
            print(f"  beklenen bildirim: {bb['ham']} kayıt tarandı → "
                  f"{bb['yazilan']} satır ({bb.get('ticker', 0)} ticker)")
    elif args.alt == "durum":
        s = news.summary(con)
        asof = db.scalar(con, "SELECT MAX(date) FROM bars_daily") or ""
        d = news.kaynak_durumu(con, asof) if asof else {"ok": None, "not": None}
        print(f"Bildirim : {s['toplam']} ({s['ticker']} ticker)")
        print(f"Aralık   : {s['ilk']} … {s['son']}")
        print(f"Önem     : {s['onem']}  (HEURİSTİK — ölçülmedi, hesaba girmez)")
        print(f"Sağlık   : {'TAZE' if d['ok'] else 'BAYAT/YOK'}"
              + (f" — {d['not']}" if d.get("not") else ""))
        if d["ok"] is False:
            kod = 1
    elif args.alt == "listele":
        for h in news.bundle_view(con, args.ticker or "THYAO", limit=15):
            print(f"  {h['tarih']}  {h['onem']:7} {h['baslik']}")
    con.close()
    return kod


# ---------------------------------------------------------------- sağlık
def cmd_saglik(args) -> int:
    """Sessiz bozulmaya karşı ön uçuş kontrolü.

    Mantık `src/saglik.py`'de — otonom koşu da aynı kapıyı kullanır ve hiçbir
    modül `cli`'ı import edemez (katman disiplini). Burası ince kabuk.
    Çıkış kodu: 0 temiz · 1 uyarı var · 2 en az bir KRİTİK kontrol düştü.
    """
    from . import saglik as sag

    cfg = _cfg()
    con = db.connect(cfg, readonly=True)
    sonuc = sag.kontrol(cfg, con)
    print(sag.bicimle(sonuc))
    con.close()
    return sag.cikis_kodu(sonuc)


# ---------------------------------------------------------------- seviye ölçümü
def cmd_seviye(args) -> int:
    """Seviyeye yakınlığın YÖN üstünlüğü var mı? — ölçüm, iddia değil.

    `levels.measure_level_edge` yazılmıştı ama HİÇBİR YERDEN çağrılmıyordu
    (2026-07-27 denetimi). Ölçüm kültürü olan bir projede koşulmayan bir ölçüm
    harness'i, silinmesi değil BAĞLANMASI gereken bir eksiktir: seviyeler
    planlayıcının temeli ve yön üstünlükleri hâlâ ölçülmedi.
    """
    cfg = _cfg()
    con = db.connect(cfg)
    from . import levels as lv, prices as pr, universe

    H = int(cfg["olcum"]["ana_ufuk_gun"])
    tickers = [args.ticker.upper()] if args.ticker else universe.live(con)
    print(f"Seviye kenarı ölçülüyor — H={H}, örtüşmeyen pencere, "
          f"{len(tickers)} hisse\n")
    print(f"{'ticker':<8}{'destek N':>10}{'Δ medyan':>11}{'hüküm':>26}"
          f"{'direnç N':>10}{'Δ medyan':>11}{'hüküm':>26}")
    print("-" * 102)
    for t in tickers:
        bars = pr.bars(con, t)
        r = lv.measure_level_edge(cfg, bars, horizon=H)
        if r.get("not"):
            print(f"{t:<8}{r['not']:>10}")
            continue
        d, k = r["destek"], r["direnc"]
        print(f"{t:<8}{d['n']:>10}{_f2(d['fark']):>11}{d['hukum']:>26}"
              f"{k['n']:>10}{_f2(k['fark']):>11}{k['hukum']:>26}")
    print("\n⚠ Bu tablo bir KENAR İDDİASI DEĞİLDİR. Hüküm `edge_verdict`ten "
          "geçer ve bu sistemde 'doğrulandı' dalı yoktur. Tek tek 'en iyi' "
          "satıra bakma — çoklu test.")
    con.close()
    return 0


def _f2(x) -> str:
    return "—" if x is None else f"{x:+.2f}pp"


# ---------------------------------------------------------------- teşhis
def cmd_teshis(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import diagnose, report

    print("Teşhis koşuyor (enstrüman doğrulaması + 5 kollu atıf)…\n")
    t = diagnose.run(cfg, con)
    h = diagnose.verdict(t)
    metin = report.diagnose_report(cfg, t, h)
    yol = report.write(cfg, f"teshis_{report.bugun()}.md", metin)
    print(metin)
    print(f"\n\nRapor yazıldı: {yol}")
    con.close()
    return 0


# ---------------------------------------------------------------- revizyon
def cmd_revizyon(args) -> int:
    cfg = _cfg()
    con = db.connect(cfg)
    from . import report, revizyon

    print("Ön kayıtlı revizyon turu #1 koşuyor…\n")
    r = revizyon.run(cfg, con)
    metin = report.revizyon_report(cfg, r)
    yol = report.write(cfg, f"revizyon01_{report.bugun()}.md", metin)
    print(metin)
    print(f"\n\nRapor yazıldı: {yol}")
    con.close()
    return 0 if r["karar"]["gecti"] else 2


# ---------------------------------------------------------------- bildir
def cmd_bildir(args) -> int:
    """Telegram hattının ayakta olduğunu doğrular.

    Kurulumda tek gereken şey bu: token/chat doğru mu, mesaj gerçekten
    düşüyor mu? Actions'ta ilk kez öğrenmek istemeyeceğin bir şey.
    """
    from . import report, telegram_bist as tg

    cfg = _cfg()

    # Kurulum sırası: token → bota mesaj yaz → chat_id'yi öğren → .env'e yaz.
    # `--chat-id` yalnız TOKEN ister; chat_id henüz bilinmiyor olabilir.
    if args.chat_id:
        if not util.env("TELEGRAM_BOT_TOKEN"):
            print("🛑 TELEGRAM_BOT_TOKEN tanımlı değil (.env).")
            return 1
        sohbetler = tg.sohbetleri_bul()
        if not sohbetler:
            print("Bota yazan sohbet bulunamadı.\n"
                  "Telegram'da botunu aç, ona herhangi bir mesaj yaz "
                  "(ör. /start), sonra bu komutu tekrar koş.")
            return 1
        print("Bota yazan sohbetler — `TELEGRAM_CHAT_ID`'ye bunu yaz:\n")
        for s in sohbetler:
            print(f"  {s['id']}   ({s['tur']}) {s['ad']}")
        return 0

    if not tg.yapilandirilmis():
        print("🛑 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID tanımlı değil (.env).")
        return 1
    metin = (f"✅ BIST bildirim testi — {report.bugun()}\n"
             "Hat çalışıyor. Bu mesaj `bist bildir --test` ile gönderildi.")
    n = tg.send_message(cfg, metin)
    print(f"Gönderildi ({n} parça).")
    return 0


# ---------------------------------------------------------------- otonom
def cmd_otonom(args) -> int:
    """Actions'ın çağırdığı tek komut. Mantık `src/otonom.py`'de.

    Çıkış kodu: 0 başarılı (ya da işlem günü değil) · 1 KRİTİK adım düştü.
    Kritik olmayan adımların düşmesi çıkışı kırmızıya çevirmez ama rapora ve
    Telegram özetine yazılır — sessiz bozulma bu projede en pahalı hata sınıfı.
    """
    from . import otonom

    cfg = _cfg()
    con = db.connect(cfg)
    if args.alt == "nobetci":
        # Gözcü: hiçbir şey düzeltmez, yalnız söyler. Çıkış 1 = sessizlik var.
        n = otonom.nobetci(cfg, con)
        con.close()
        if n.get("not"):
            print(n["not"])
        for s in n["satirlar"]:
            print(f"  ⚠ {s}")
        if not n["satirlar"]:
            print(f"✅ Nöbetçi temiz — son koşu {n.get('son_kosu')} · "
                  f"son bar {n.get('son_bar')} · son analiz {n.get('son_analiz')}")
            return 0
        from . import telegram_bist as tg
        try:
            tg.bildir(cfg, "👁 BIST nöbetçi — " + n["tarih"] + "\n"
                      + "\n".join(f"· {s}" for s in n["satirlar"]))
        except Exception as e:                              # noqa: BLE001
            print(f"  (Telegram gönderilemedi: {e})")
        return 1 if n["sessiz"] else 0

    if args.alt == "gunluk":
        sonuc = otonom.gunluk(cfg, con, analist_calistir=not args.analistsiz)
    else:
        sonuc = otonom.haftalik(cfg, con)
    con.close()

    if sonuc.get("atlandi"):
        print(sonuc["atlandi"])
        return 0
    for ad, mesaj in sonuc.get("adimlar", {}).items():
        print(f"  ✓ {ad:12} {mesaj}")
    for ad, mesaj in sorted(sonuc.get("hatalar", {}).items()):
        print(f"  ✗ {ad:12} {mesaj}")
    for u in sonuc.get("uyarilar", []):
        print(f"  ⚠ {u}")

    dusen = otonom.basarisiz_mi(sonuc)
    if dusen:
        print(f"\n🛑 KRİTİK ADIM BAŞARISIZ: {', '.join(dusen)}")
        return 1
    print("\n✅ Otonom koşu tamam.")
    return 0


# ---------------------------------------------------------------- db
def cmd_db(args) -> int:
    cfg = _cfg()
    if args.alt == "dump":
        p = dbdump.dump(cfg)
        print(f"Yazıldı: {p}  ({p.stat().st_size/1e6:.2f} MB)")
    elif args.alt == "restore":
        for t, n in dbdump.restore(cfg).items():
            print(f"  {t:22} {n:>8} satır")
    elif args.alt == "durum":
        con = db.connect(cfg)
        print(f"Veritabanı : {db.db_path(cfg)}")
        print(f"Şema sürümü: {con.execute('PRAGMA user_version').fetchone()[0]}\n")
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        for (t,) in rows:
            n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t:22} {n:>8}")
        con.close()
    return 0


# ---------------------------------------------------------------- main
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bist", description=f"BIST analiz. {UYARI}")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("veri", help="fiyat verisi çek / kalite kontrol")
    v.add_argument("alt", choices=["backfill", "gunluk", "kalite", "temizle"])
    v.set_defaults(fn=cmd_veri)

    e = sub.add_parser("evren", help="evren senkron / canlı tarama")
    e.add_argument("alt", choices=["sync", "tara"])
    e.set_defaults(fn=cmd_evren)

    t = sub.add_parser("takvim", help="işlem günü sorgusu ve aritmetiği")
    t.add_argument("tarih", nargs="?", help="YYYY-MM-DD (varsayılan: bugün)")
    t.add_argument("gun", nargs="?", type=int, help="eklenecek işlem günü sayısı")
    t.set_defaults(fn=cmd_takvim)

    m = sub.add_parser("makro", help="TCMB EVDS")
    m.add_argument("alt", choices=["backfill", "gunluk", "durum"])
    m.set_defaults(fn=cmd_makro)

    g = sub.add_parser("gosterge", help="göstergeleri hesapla ve dondur")
    g.add_argument("--start", help="YYYY-MM-DD (varsayılan: tüm geçmiş)")
    g.set_defaults(fn=cmd_gosterge)

    bt = sub.add_parser("backtest", help="ÖLÇÜM harness'i — Faz 2 kapısı")
    bt.add_argument("--start", help="YYYY-MM-DD")
    bt.add_argument("--end", help="YYYY-MM-DD")
    bt.add_argument("--top-frac", type=float, dest="top_frac", help="uygun havuzun kaçta kaçı seçilsin (varsayılan 0.33)")
    bt.set_defaults(fn=cmd_backtest)

    pl = sub.add_parser("plan", help="deterministik plan menüsü")
    pl.add_argument("ticker", nargs="?", help="tek hisse (varsayılan: tüm canlı evren)")
    pl.add_argument("--asof", help="YYYY-MM-DD")
    pl.add_argument("--kaydet", action="store_true", help="plan_options tablosuna yaz")
    pl.set_defaults(fn=cmd_plan)

    gn = sub.add_parser("gunluk", help="LLM girdi paketini hazırla")
    gn.add_argument("--asof", help="YYYY-MM-DD")
    gn.set_defaults(fn=cmd_gunluk)

    dn = sub.add_parser("denetle", help="analist çıktısını HF-01..HF-32 ile denetle")
    dn.add_argument("--asof", help="YYYY-MM-DD")
    dn.set_defaults(fn=cmd_denetle)

    kd = sub.add_parser("kaydet", help="denetimden geçen çıktıyı journal'a yaz")
    kd.add_argument("--asof", help="YYYY-MM-DD")
    kd.set_defaults(fn=cmd_kaydet)

    rp = sub.add_parser("replay", help="LLM'siz tam boru hattı tekrarı")
    rp.add_argument("--start", default="2024-01-01")
    rp.add_argument("--end", default="2026-06-30")
    rp.add_argument("--adim", type=int, help="kaç işlem günde bir (varsayılan: ufuk)")
    rp.add_argument("--top", type=int, default=3, help="dönem başına kaç isim")
    rp.add_argument("--sifirla", action="store_true", help="replay kayıtlarını sil")
    rp.set_defaults(fn=cmd_replay)

    jr = sub.add_parser("journal", help="tahmin günlüğü")
    jr.add_argument("alt", choices=["durum", "acik"])
    jr.set_defaults(fn=cmd_journal)

    cz = sub.add_parser("coz", help="açık tahminleri çöz (üçlü bariyer)")
    cz.set_defaults(fn=cmd_coz)

    dg = sub.add_parser("degerlendir", help="hızlı döngü metrikleri")
    dg.add_argument("--tool", help="yalnız bu araçtan gelen kayıtlar (ör. replay)")
    dg.set_defaults(fn=cmd_degerlendir)

    rp2 = sub.add_parser("rapor", help="günlük Türkçe markdown rapor")
    rp2.add_argument("--asof", help="YYYY-MM-DD")
    rp2.set_defaults(fn=cmd_rapor)

    pf = sub.add_parser("portfoy", help="elle tutulan pozisyonlar")
    pf.add_argument("alt", choices=["ekle", "sil", "listele"])
    pf.add_argument("ticker", nargs="?")
    pf.add_argument("adet", nargs="?", type=float, default=0.0)
    pf.add_argument("maliyet", nargs="?", type=float)
    pf.set_defaults(fn=cmd_portfoy)

    hb = sub.add_parser("haber", help="KAP bildirimleri")
    hb.add_argument("alt", choices=["cek", "durum", "listele"])
    hb.add_argument("ticker", nargs="?")
    hb.add_argument("--tam", action="store_true", help="artımlı değil tam çekim")
    hb.add_argument("--gun", type=int,
                    help="tam çekimde kaç gün geriye (varsayılan: "
                         "config.sources.kap.tam_cekim_gun)")
    hb.set_defaults(fn=cmd_haber)

    sg = sub.add_parser("saglik", help="ön uçuş kontrolü — sessiz bozulma taraması")
    sg.set_defaults(fn=cmd_saglik)

    sv = sub.add_parser("seviye", help="seviye yakınlığının yön üstünlüğünü ÖLÇ")
    sv.add_argument("ticker", nargs="?", help="tek hisse (varsayılan: canlı evren)")
    sv.set_defaults(fn=cmd_seviye)

    ts = sub.add_parser("teshis", help="kayıp atıfı — revizyon turu DEĞİL")
    ts.set_defaults(fn=cmd_teshis)

    rv = sub.add_parser("revizyon", help="ön kayıtlı revizyon turu #1")
    rv.set_defaults(fn=cmd_revizyon)

    ot = sub.add_parser("otonom", help="tam otomatik koşu (GitHub Actions)")
    ot.add_argument("alt", choices=["gunluk", "haftalik", "nobetci"])
    ot.add_argument("--analistsiz", action="store_true",
                    help="LLM zincirini atla, yalnız deterministik katman")
    ot.set_defaults(fn=cmd_otonom)

    bd = sub.add_parser("bildir", help="Telegram bildirim testi / kurulum")
    bd.add_argument("--test", action="store_true", help="deneme mesajı gönder")
    bd.add_argument("--chat-id", action="store_true",
                    help="bota yazan sohbetlerin kimliğini listele (kurulum)")
    bd.set_defaults(fn=cmd_bildir)

    d = sub.add_parser("db", help="veritabanı dump/restore/durum")
    d.add_argument("alt", choices=["dump", "restore", "durum"])
    d.set_defaults(fn=cmd_db)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        print("\nİptal edildi.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
