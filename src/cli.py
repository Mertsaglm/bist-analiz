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
