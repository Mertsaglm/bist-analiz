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

    # 9-10) KESİTSEL AKIL SAĞLIĞI — iki uçtan da
    for seviye, ad, tamam, mesaj in _kesit_kontrolleri(cfg, con):
        ekle(seviye, ad, tamam, mesaj)

    # 11) DÜZELTİLMEMİŞ KURUMSAL İŞLEM — TÜM GEÇMİŞ, pencere YOK
    seviye, ad, tamam, mesaj = _duzeltilmemis_kurumsal(cfg, con)
    ekle(seviye, ad, tamam, mesaj)

    # 12) ATLANAN OTONOM KOŞU — bildirimin ULAŞAMADIĞI arıza sınıfı
    seviye, ad, tamam, mesaj = _atlanan_kosu(cfg, con, asof)
    ekle(seviye, ad, tamam, mesaj)

    return {
        "asof": asof,
        "bulgular": bulgular,
        "kritik": [b for b in bulgular if b[0] == KRITIK],
        "uyari": [b for b in bulgular if b[0] == UYARI],
    }


def _kesit_kontrolleri(cfg: dict, con: sqlite3.Connection
                       ) -> list[tuple[str, str, bool, str]]:
    """Kesit tek yöne mi düştü? — Merdiven'in devre kesicisinin genellenmiş hâli.

    İki AYRI soru, iki ayrı kontrol (L-003: farklı olguları aynı satıra sıkıştırma):

    **9. plan üretim oranı** — bir günde evrenin çoğunda plan çıkıyorsa bozulan
    piyasa değil, seviye/R:R mantığıdır. Ölçüldü (23 asof günü): medyan 2/18,
    gözlemlenen maksimum 9/18 = %50. Tel %60'a konur — yani "bu daha önce hiç
    olmadı" eşiği. Aynı satır, TERS uçtaki tetikleyiciyi de basar: STATE.md
    Backlog'undaki "20 günde ort. <2 plan → ön kayıtlı seviye turu" koşulu.
    Yazılı bir tetikleyici hatırlanmaya bırakılırsa hatırlanmaz (AGENTS.md §12).

    **10. analist sinyal dağılımı** — HF-23 rejim tavanını `plan_sec` SAYISINA
    uyguluyor ama `signal` alanına hiçbir tavan yok. L-008'in "simetriğini ara"
    kuralı tam buraya bakıyor: 18 ismin 15'ine `buy` demek, aracın bozulduğunu
    gösterir ve hiçbir HF kodu bunu yakalamaz.

    Salt-okunur: yalnız `plan_options` ve `predictions` okunur, `build_menu`
    ÇAĞRILMAZ (o yazar; sağlık kontrolü hiçbir şeyi değiştirmez).
    """
    k = cfg["saglik"]["kesit"]
    n_canli = len(universe.live(con)) or 1
    out: list[tuple[str, str, bool, str]] = []

    gunler = db.fetch_all(
        con, "SELECT asof, COUNT(DISTINCT ticker) n FROM plan_options "
             " GROUP BY asof ORDER BY asof DESC LIMIT ?", (int(k["pencere_gun"]),))
    if not gunler:
        out.append((BILGI, "plan üretim oranı", True,
                    "plan_options boş — henüz ölçülecek gün yok"))
    else:
        son = gunler[0]
        oran = son["n"] / n_canli
        ort = sum(g["n"] for g in gunler) / len(gunler)
        tel = float(k["ust_tel_orani"])
        alt = float(k["alt_tetik_ort"])
        # Payda GÖRÜNÜR: kaç gün üzerinden, kaç isimlik evrende (L-007).
        ozet = (f"son gün {son['asof']}: {son['n']}/{n_canli} isim (%{oran*100:.0f}) "
                f"· son {len(gunler)} plan gününde ort. {ort:.2f} isim")
        if oran > tel:
            out.append((UYARI, "plan üretim oranı", False,
                        ozet + f" → **%{tel*100:.0f} telini AŞTI**; gözlemlenen "
                               "maksimum %50'ydi. Kesit tek yöne düştüyse önce "
                               "seviye/R:R mantığından şüphelen"))
        elif len(gunler) >= int(k["pencere_gun"]) and ort < alt:
            out.append((UYARI, "plan üretim oranı", False,
                        ozet + f" → ortalama {alt} altında: STATE.md'deki ön "
                               "kayıtlı seviye turu tetikleyicisi OLUŞTU "
                               "(docs/on-kayit-seviye-02.md)"))
        else:
            out.append((BILGI, "plan üretim oranı", True, ozet))

    son_run = db.fetch_one(
        con, "SELECT p.run_id, p.asof, r.tool, COUNT(*) n,"
             "  SUM(CASE WHEN p.signal IN ('strong_buy','buy','accumulate') "
             "           THEN 1 ELSE 0 END) boga,"
             "  SUM(CASE WHEN p.signal IN ('reduce','sell','avoid') "
             "           THEN 1 ELSE 0 END) ayi "
             "  FROM predictions p JOIN llm_runs r ON r.run_id = p.run_id "
             " GROUP BY p.run_id ORDER BY p.asof DESC, p.run_id DESC LIMIT 1")
    if not son_run or not son_run["n"]:
        out.append((BILGI, "sinyal dağılımı", True, "journal'da tahmin yok"))
    elif son_run["n"] < int(k["sinyal_min_n"]):
        # Payda küçükken oran anlamsızdır ve "temiz" demek de yanıltıcıdır.
        out.append((BILGI, "sinyal dağılımı", True,
                    f"{son_run['asof']} ({son_run['tool']}): n={son_run['n']} "
                    f"< {k['sinyal_min_n']} → oran DEĞERLENDİRİLMEDİ"))
    else:
        tel = float(k["sinyal_ust_tel"])
        pb, pa = son_run["boga"] / son_run["n"], son_run["ayi"] / son_run["n"]
        ozet = (f"{son_run['asof']} ({son_run['tool']}): n={son_run['n']} · "
                f"boğa %{pb*100:.0f} · ayı %{pa*100:.0f}")
        tek_yon = max(pb, pa) > tel
        out.append((UYARI if tek_yon else BILGI, "sinyal dağılımı", not tek_yon,
                    ozet + (f" → **%{tel*100:.0f} telini AŞTI**; 18 ismin çoğuna "
                            "aynı şeyi demek araç şüphesidir" if tek_yon else "")))
    return out


def _atlanan_kosu(cfg: dict, con: sqlite3.Connection, asof: str | None
                  ) -> tuple[str, str, bool, str]:
    """Analiz KOŞMADIĞI günleri yakalar — bildirimin ulaşamadığı arıza sınıfı.

    ⚠ GERÇEK OLAY (2026-08-06): planlanmış otonom koşu GitHub tarafında
    "The job was not acquired by Runner of type hosted" ile düştü. İş HİÇ
    BAŞLAMADI; dolayısıyla `otonom.py` koşmadı, Telegram bildirimi de çıkmadı.
    Kullanıcı açısından o gün **tamamen sessizdi** — ne rapor geldi, ne uyarı.
    Fark edilmesi yalnızca eksik bir commit'e gözle rastlamaya kalmıştı.

    Bu, L-010'un kardeşi ve bir adım daha kötüsü: L-010'da kontroller kendi
    verisine bakıyordu; burada **bildirim mekanizması, gözlediği sürecin
    İÇİNDE yaşıyor.** Bir süreç kendi yokluğunu haber veremez.

    Çözüm, bir sonraki koşan sürecin GERİYE bakması: journal'daki son analiz
    günü ile beklenen son seans arasındaki işlem günü farkı. Fark ≥1 ise
    aradaki bir koşu atlanmıştır. Bu kontrol elle `bist saglik` ile de
    koşulabilir, yani hiç Actions çalışmasa bile görünür.
    """
    if not asof:
        return BILGI, "atlanan koşu", True, "veri yok"
    son_analiz = db.scalar(con, "SELECT MAX(asof) FROM predictions")
    if not son_analiz:
        return BILGI, "atlanan koşu", True, "journal boş — henüz analiz yok"
    try:
        from .calendar_bist import BistCalendar
        cal = BistCalendar(cfg, con)
        fark = cal.trading_days_between(son_analiz, asof)
    except Exception:                                       # noqa: BLE001
        return BILGI, "atlanan koşu", True, "takvim kurulamadı"
    ozet = f"son analiz {son_analiz} · son bar {asof}"
    if fark <= 0:
        return OK, "atlanan koşu", True, ozet
    # Şiddet kademeli: bir gün gecikme (yfinance bekleyişi, tek seferlik runner
    # arızası) olağan; iki gün üst üste analiz yoksa zincir gerçekten duruyor.
    return ((KRITIK if fark >= 2 else UYARI), "atlanan koşu", False,
            ozet + f" → **{fark} işlem günü analizsiz**. Planlı koşu düşmüş "
                   "olabilir; iş hiç başlamazsa Telegram bildirimi de ÇIKMAZ "
                   "(gözlendi 2026-08-06). Actions geçmişini kontrol et.")


def duzeltilmemis_kurumsal_tara(cfg: dict, con: sqlite3.Connection) -> list[dict]:
    """TÜM GEÇMİŞTE düzeltilmemiş bedelsiz/bölünme şüphesi taşıyan barlar.

    Neden `data_quality`'ye güvenilmez: o yalnız SON 252 BARA bakar ve CCOLA'yı
    görünmez kılan tam olarak buydu. 2024-08-01'deki −%90.7'lik bar bugün
    pencerenin dışında kalıyor, `unexplained_jump=0` yazıyor ve tablo "temiz"
    diyor — oysa bar hâlâ orada ve backtest paneli hâlâ onu okuyor.

    Bu yüzden burası **pencerelenmez.** Bulgu, düzeltilene ya da bilinçli
    olarak kabul edilene kadar HER GÜN görünür. (AGENTS.md §11: düzeltilemeyen
    bulgu sessizce bırakılmaz, ifşa edilir.)
    """
    esik = float(cfg["evren"]["duzeltilmemis_kurumsal_pct"]) / 100.0
    rows = db.fetch_all(
        con,
        "SELECT ticker, date, getiri, in_live, in_measure FROM ("
        "  SELECT b.ticker, b.date,"
        "         b.c / LAG(b.c) OVER (PARTITION BY b.ticker ORDER BY b.date) - 1 getiri,"
        "         u.in_live, u.in_measure"
        "    FROM bars_daily b LEFT JOIN universe u ON u.ticker = b.ticker"
        ") WHERE getiri IS NOT NULL AND ABS(getiri) > ? ORDER BY ABS(getiri) DESC",
        (esik,))
    return [{**r, "getiri_pct": round(r["getiri"] * 100, 1)} for r in rows]


def _duzeltilmemis_kurumsal(cfg: dict, con: sqlite3.Connection
                            ) -> tuple[str, str, bool, str]:
    esik = cfg["evren"]["duzeltilmemis_kurumsal_pct"]
    try:
        bulgular = duzeltilmemis_kurumsal_tara(cfg, con)
    except sqlite3.OperationalError as e:              # pencere fonksiyonu yoksa
        return BILGI, "düzeltilmemiş kurumsal", True, f"taranamadı: {e}"
    if not bulgular:
        return OK, "düzeltilmemiş kurumsal", True, f"|getiri|>%{esik:.0f} bar yok"
    canli = [b for b in bulgular if b["in_live"]]
    # ŞİDDET, ETKİLENEN HATTA GÖRE: canlı evrende bir bar varsa günlük kararı
    # doğrudan besliyor demektir (KRİTİK); yalnız ölçüm evrenindeyse geçmişe
    # dönük bir kalibrasyon sorunudur (UYARI) — ikisi aynı şey değil (L-003).
    ilk = "; ".join(f"{b['ticker']} {b['date']} {b['getiri_pct']:+.1f}%"
                    for b in bulgular[:4])
    return ((KRITIK if canli else UYARI), "düzeltilmemiş kurumsal", False,
            f"{len(bulgular)} bar (|getiri|>%{esik:.0f}) · "
            f"canlı evrende {len(canli)} · ölçüm evreninde "
            f"{sum(1 for b in bulgular if b['in_measure'])} → {ilk}"
            + ("" if len(bulgular) <= 4 else f" … (+{len(bulgular)-4})"))


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
