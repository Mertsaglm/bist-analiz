"""Ön uçuş kontrolü — sessiz bozulma taraması.

2026-07-27 denetiminin ürettiği risk listesi elle koşulacak SQL'ler olarak
kalırsa koşulmaz (LESSONS L-002). Hepsi burada, tek çağrıda.

⚠ Bu mantık Faz 8'de `cli.cmd_saglik`'ten BURAYA taşındı. Sebebi katman
disiplini: otonom koşu (`src/otonom.py`) sağlık kapısını çağırmak zorunda ve
hiçbir modül `cli`'ı import edemez (`test_sozlesme.py::test_kimse_cli_yi_
import_etmez`). CLI artık ince bir kabuk: burayı çağırıp basıyor.

Çıkış kodu sözleşmesi — otomasyonun kapısı bu:
    0 temiz · 1 en az bir UYARI · 2 en az bir KRİTİK
"""

from __future__ import annotations

import sqlite3

from . import db, migrations, news, universe

KRITIK = "KRİTİK"
UYARI = "UYARI"
BILGI = "BİLGİ"
OK = "OK"

ISARET = {OK: "✓", KRITIK: "🛑", UYARI: "⚠", BILGI: "·"}


def kontrol(cfg: dict, con: sqlite3.Connection) -> dict:
    """Tüm kontrolleri koşar. {asof, bulgular:[(seviye, ad, mesaj)], kritik, uyari}

    Bağlantı SALT OKUNUR verilebilir ve verilmelidir — sağlık kontrolü hiçbir
    şeyi değiştirmez.
    """
    asof = db.scalar(con, "SELECT MAX(date) FROM bars_daily")
    bulgular: list[tuple[str, str, str]] = []

    def ekle(seviye, ad, tamam, mesaj):
        bulgular.append((OK if tamam else seviye, ad, mesaj))

    # 0) BAR TAZELİĞİ — takvime göre. Diğer TÜM kontrollerin dayanağı budur.
    #
    # ⚠ Bu kontrol Faz 8'de eklendi ve gerçek bir körlüğü kapattı: aşağıdaki
    # kontroller göstergeyi/kaliteyi `MAX(bars_daily.date)`'e kıyaslıyor. Barlar
    # bayatlarsa `asof` da bayatlar ve her şey "tutarlı" görünür — kontroller
    # birbirini doğrular, hiçbiri dış dünyaya bakmaz. Otomasyonda bunun
    # karşılığı şu: veri gelmediği gün sistem DÜNKÜ raporu bugünmüş gibi
    # bildirir ve hiçbir yerde uyarı çıkmaz (L-007'nin bu projedeki üçüncü
    # görünümü: kod doğru, veri sessizce bayat, çıktı hâlâ geçerli görünüyor).
    #
    # Şiddet kademeli: yfinance'in bir seans gecikmesi olağan (gözlendi
    # 2026-08-01: cuma barı cumartesi sabahı hâlâ yoktu), iki seans değil.
    try:
        from .calendar_bist import BistCalendar
        cal = BistCalendar(cfg, con)
        beklenen = cal.last_closed_session()
        gecikme = cal.trading_days_between(asof, beklenen.isoformat()) if asof else 99
    except Exception:                                       # noqa: BLE001
        gecikme, beklenen = 0, None                         # takvim kurulamadıysa sus
    if beklenen is not None:
        ekle(KRITIK if gecikme >= 2 else UYARI, "bar tazeliği", gecikme <= 0,
             f"son bar {asof} · beklenen {beklenen.isoformat()}"
             + ("" if gecikme <= 0 else
                f" → {gecikme} seans geride (`bist veri gunluk`)"))

    # 1) Gösterge kapsaması — kesitsel her oranın PAYDASI
    n_bar = db.scalar(con, "SELECT COUNT(DISTINCT ticker) FROM bars_daily") or 0
    n_ind = db.scalar(con, "SELECT COUNT(DISTINCT ticker) FROM indicator_daily") or 0
    ekle(KRITIK, "gösterge kapsaması", n_ind >= n_bar,
         f"{n_ind}/{n_bar} ticker" + ("" if n_ind >= n_bar else " → `bist gosterge`"))

    # 2) Gösterge tazeliği
    son_ind = db.scalar(con, "SELECT MAX(date) FROM indicator_daily")
    ekle(KRITIK, "gösterge tazeliği", son_ind == asof,
         f"gösterge {son_ind} · bar {asof}"
         + ("" if son_ind == asof else " → `bist gosterge`"))

    # 3) Kalite kapısı açık mı
    son_kal = db.scalar(con, "SELECT MAX(date) FROM data_quality")
    ekle(KRITIK, "kalite kapısı", son_kal == asof,
         f"kalite {son_kal} · bar {asof}"
         + ("" if son_kal == asof else " → `bist veri kalite`"))

    # 4) Haber katmanı sağlığı
    hd = news.kaynak_durumu(con, asof) if asof else {"ok": False, "not": "veri yok"}
    ekle(KRITIK, "haber katmanı", bool(hd["ok"]),
         hd.get("not") or f"son bildirim {hd.get('son_bildirim')}")

    # 5) Tick ızgarası — açık uçlu bant TEK İSİMLE ölçüldü (EGEEN, 2.50 TL).
    # İkinci bir isim o banda GERÇEKTEN girerse (son kurumsal işlemden sonraki
    # ham barlarla) ölçüm tekrarlanmalı; split-düzeltmeli eski fiyatlar ham
    # ızgarada değildir ve yanlış alarm üretir.
    ust = max((b["ust_sinir"] or 0) for b in cfg["risk"]["fiyat_adimlari"][:-1])
    asan = db.fetch_all(
        con,
        "SELECT b.ticker, MAX(b.c) m FROM bars_daily b "
        "  JOIN (SELECT ticker, MAX(date) d FROM corporate_actions GROUP BY ticker) k "
        "    ON k.ticker = b.ticker AND b.date > k.d "
        " WHERE b.c > ? GROUP BY b.ticker ORDER BY m DESC", (ust,))
    ekle(UYARI, "tick ızgarası", len(asan) <= 1,
         f"açık uçlu bant (>{ust:.2f} TL) {len(asan)} isimle ölçülü: "
         + (", ".join(f"{r['ticker']}={r['m']:.0f}" for r in asan) or "gözlem yok")
         + ("" if len(asan) <= 1 else " → ikinci isim girdi, YENİDEN ÖLÇ"))

    # 6) Journal kaynak karışıklığı
    arac = {r["tool"]: r["n"] for r in db.fetch_all(
        con, "SELECT r.tool, COUNT(*) n FROM predictions p "
             " JOIN llm_runs r ON r.run_id = p.run_id GROUP BY r.tool")}
    ekle(UYARI, "journal kaynağı", len(arac) <= 1,
         f"{arac or 'kayıt yok'}"
         + ("" if len(arac) <= 1 else " → `bist degerlendir --tool ...` şart"))

    # 7) Evren ↔ taban çizgisi tutarlılığı
    n_out = db.scalar(con, "SELECT COUNT(*) FROM outcomes "
                           "WHERE alpha_vs_ew IS NOT NULL") or 0
    ekle(BILGI, "EW tabanlı sonuç", True,
         f"{n_out} kayıt · evren {len(universe.live(con))} canlı / "
         f"{len(universe.measure(con))} ölçüm")

    # 8) Şema sürümü
    sv = con.execute("PRAGMA user_version").fetchone()[0]
    ekle(KRITIK, "şema sürümü", sv == migrations.target_version(),
         f"v{sv} / hedef v{migrations.target_version()}")

    return {
        "asof": asof,
        "bulgular": bulgular,
        "kritik": [b for b in bulgular if b[0] == KRITIK],
        "uyari": [b for b in bulgular if b[0] == UYARI],
    }


def cikis_kodu(sonuc: dict) -> int:
    """0 temiz · 1 uyarı · 2 KRİTİK. Otomasyonun kapısı bu sayıdır."""
    if sonuc["kritik"]:
        return 2
    return 1 if sonuc["uyari"] else 0


def bicimle(sonuc: dict) -> str:
    L = [f"Sağlık kontrolü — {sonuc['asof']}", ""]
    for seviye, ad, mesaj in sonuc["bulgular"]:
        L.append(f"  {ISARET[seviye]} {ad:22} {mesaj}")
    L.append("")
    if sonuc["kritik"]:
        L.append(f"🛑 {len(sonuc['kritik'])} KRİTİK kontrol düştü — "
                 f"sessiz yanlış sonuç riski var.")
    elif sonuc["uyari"]:
        L.append(f"⚠ {len(sonuc['uyari'])} uyarı.")
    else:
        L.append("✅ Tüm kontroller temiz.")
    return "\n".join(L)


def tek_satir(sonuc: dict) -> str:
    """Telegram özetine giren tek satırlık hâl."""
    if sonuc["kritik"]:
        return "🛑 Sağlık: " + "; ".join(f"{ad} ({mesaj})"
                                        for _, ad, mesaj in sonuc["kritik"])
    if sonuc["uyari"]:
        return f"⚠ Sağlık: {len(sonuc['uyari'])} uyarı"
    return "✓ Sağlık temiz"
