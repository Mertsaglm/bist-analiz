"""Ortak test fixture'ları.

İki tür test var ve karıştırılmamalı:

  * **Sentetik testler** — geçici veritabanı + elle kurulmuş barlar. Mantığı test
    eder, ağ gerektirmez, daima çalışır.
  * **Gerçek veri testleri** — proje veritabanını (`data/bist.db`) okur ve veri
    KAYNAĞININ davranışını test eder (ör. yfinance temettü düzeltmesi hâlâ
    çalışıyor mu). Bunlar `real_con` fixture'ını kullanır ve veritabanı boşsa
    atlanır. Amaçları LESSONS L-005: "inancı fixture testine çevir".
"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from src import db, util


# --------------------------------------------------------------- güvenlik ağı
@pytest.fixture(autouse=True)
def ag_yasak(monkeypatch, request):
    """Testler AĞA ÇIKAMAZ — yapısal güvence.

    ⚠ YAŞANMIŞ OLAY (2026-08-25 / 08-28 denetimleri): `test_temiz_cekim_0`
    yalnız `news.sync`'i mock'luyordu, ama `cli.cmd_haber` aynı komutta ayrıca
    `news.sync_beklenen` çağırıyor ve o MOCK'SUZDU. Yani "temiz çekim 0 döner"
    diye yazılmış test, gerçek KAP'a bağlanıyordu. Ağı olan makinede yeşil,
    olmayanda kırmızı — sonuç testin ne kanıtladığına bağlı değil, ağ durumuna
    bağlıydı (AGENTS §11 madde 5: testin gerçekten ne kanıtladığını sor).

    Ölçüldü: ağ kapatılınca 2 test düştü ve İKİNCİSİ daha ciddiydi —
    `test_kap_kapaliysa_0`, yani `sources.kap.enabled=False` iken bile KAP'a
    çıkılıyordu. Kapatma anahtarı kapatmıyordu; testin ağ sızıntısı o hatayı
    GİZLİYORDU. Sızıntıyı kapatmak, arkasındaki gerçek hatayı görünür kıldı.

    Tek testi mock'lamak SINIFI KAPATMAZ (§11 tuzak 5): bir sonraki testte aynı
    sızıntı yeniden açılır. Bu yüzden yasak suite geneline konur — yeni bir
    doğrudan HTTP çağrısı ekleyen test kırmızıya döner ve bunu fark eder.

    Gerçekten ağ isteyen bir test olursa `@pytest.mark.ag_gerekli` ile
    işaretlenir; işaret GÖRÜNÜRDÜR ve gerekçesi testin docstring'ine yazılır.
    Localhost serbesttir (yerel yardımcı süreçler ağ değildir).
    """
    if request.node.get_closest_marker("ag_gerekli"):
        yield
        return

    import socket

    yerel = ("127.0.0.1", "::1", "localhost")
    orijinal_connect = socket.socket.connect
    orijinal_create = socket.create_connection

    def _yerel_mi(adres) -> bool:
        try:
            return isinstance(adres, tuple) and adres[0] in yerel
        except Exception:                                    # noqa: BLE001
            return False

    def korumali_connect(self, adres, *a, **k):
        if _yerel_mi(adres):
            return orijinal_connect(self, adres, *a, **k)
        raise OSError(
            f"TEST AĞA ÇIKMAYA ÇALIŞTI: {adres}\n"
            "Testler dış servise bağlanmaz — dış sınırları mock'la. "
            "Gerçekten gerekiyorsa `@pytest.mark.ag_gerekli` ile işaretle ve "
            "gerekçesini docstring'e yaz. Bu koruma tests/conftest.py "
            "içindedir ve KALDIRILMAMALIDIR — bkz. oradaki gerekçe.")

    def korumali_create(adres, *a, **k):
        if _yerel_mi(adres):
            return orijinal_create(adres, *a, **k)
        raise OSError(f"TEST AĞA ÇIKMAYA ÇALIŞTI: {adres}")

    monkeypatch.setattr(socket.socket, "connect", korumali_connect)
    monkeypatch.setattr(socket, "create_connection", korumali_create)
    yield


@pytest.fixture(autouse=True)
def gercek_dbye_yazma_korumasi(monkeypatch):
    """`pytest` kullanıcının GERÇEK veritabanına YAZAMAZ — yapısal güvence.

    ⚠ Bu bir süs değil, yaşanmış bir olayın kilidi: `real_con` fixture'ının ilk
    sürümü `db.connect(real_cfg)` çağırıyordu ve şemayı uygulayıp MIGRATION'LARI
    İLERLETİYORDU. `pytest` koşmak, kullanıcının veritabanını sessizce
    değiştiriyordu (2026-07-27 denetimi: v6 migration'ı elle koşulmadan önce bir
    test koşusunda uygulanmıştı).

    O olay `real_con`'u salt-okunur yaparak kapatıldı — ama düzeltme TEK BİR
    ÇAĞRI YERİNDEYDİ. Bir sonraki testi yazan kişinin (ya da modelin) aynı
    tuzağa yeniden düşmesini engelleyen hiçbir şey yoktu. Bu fixture o boşluğu
    kapatır: hangi test olursa olsun, gerçek `paths.db` dosyasına YAZILABİLİR
    bir bağlantı açmaya çalışmak testi patlatır.

    Salt-okunur (`readonly=True`) bağlantılar serbesttir — gerçek veri testleri
    veri KAYNAĞININ davranışını ölçer ve bunun için okumak yeterlidir.
    """
    gercek = db.db_path(util.load_config()).resolve()
    orijinal = db.connect

    def korumali(cfg_: dict, *, readonly: bool = False):
        if not readonly and db.db_path(cfg_).resolve() == gercek:
            raise RuntimeError(
                f"TEST GERÇEK VERİTABANINA YAZMAYA ÇALIŞTI: {gercek}\n"
                "Testler `cfg` fixture'ını kullanır (veritabanı tmp_path'te). "
                "Gerçek veriyi okumak için `real_con` (salt-okunur) var. "
                "Bu koruma tests/conftest.py içinde tanımlıdır ve "
                "KALDIRILMAMALIDIR — bkz. oradaki gerekçe.")
        return orijinal(cfg_, readonly=readonly)

    monkeypatch.setattr(db, "connect", korumali)
    yield


@pytest.fixture
def cfg(tmp_path: Path) -> dict:
    """Gerçek config, ama YAZILAN HER YOL geçici dizinde.

    ⚠ İlk sürüm yalnız `db` / `db_dump` / `log_dir`'i yönlendiriyordu. Yani
    `llm_in_dir`, `llm_out_dir` ve `reports_dir` GERÇEK proje dizinlerini
    gösteriyordu ve `write_bundle` / `report.write` çağıran her test
    kullanıcının repo'suna dosya bırakıyordu (ölçüldü: `llm/in/<tarih>/` ve
    `llm/out/<tarih>/` klasörleri test koşusundan sonra ortaya çıkıyordu).

    Bu, `real_con`'un salt-okunur yapılmasıyla kapatılan aynı sınıf hatanın
    dosya sistemi hâliydi: bir test suite'inin yan etkisi olmaz.

    Okunan girdiler (`universe_file`, `holidays_file`) BİLEREK gerçek kalır —
    o dosyaların içeriği testin konusudur.
    """
    c = util.load_config(fresh=True)
    c = {**c, "paths": {**c["paths"],
                        "db": str(tmp_path / "test.db"),
                        "db_dump": str(tmp_path / "test.sql"),
                        "log_dir": str(tmp_path / "logs"),
                        "llm_in_dir": str(tmp_path / "llm" / "in"),
                        "llm_out_dir": str(tmp_path / "llm" / "out"),
                        "reports_dir": str(tmp_path / "reports")},
         # ⚠ `paths` DIŞINDAKİ yol anahtarları da yönlendirilmeli. Yaşandı
         # (2026-08-01): `telegram.outbox_file` başka bir blokta olduğu için
         # gözden kaçtı ve Telegram testleri kullanıcının repo'sundaki
         # `data/telegram_outbox.jsonl` dosyasına 33 satır yazdı. Yani "pytest
         # yan etkisizdir" kuralı, kuralın YAZILDIĞI blokta tutuyor ama
         # simetriğinde tutmuyordu (L-008: düzeltme aynı hatanın BİR DAHA
         # yapılamayacağı yeri de kapsamalı).
         #
         # Yeni bir yol anahtarı eklerken sor: `cfg` fixture'ı bunu geçici
         # dizine taşıyor mu? Taşımıyorsa test suite'in yan etkisi var demektir.
         "telegram": {**c["telegram"],
                      "outbox_file": str(tmp_path / "telegram_outbox.jsonl")}}
    return c


@pytest.fixture
def con(cfg: dict):
    c = db.connect(cfg)
    yield c
    c.close()


@pytest.fixture
def real_cfg() -> dict:
    return util.load_config(fresh=True)


@pytest.fixture
def real_con(real_cfg: dict):
    """Proje veritabanı — **SALT OKUNUR**. Yoksa/boşsa test atlanır.

    ⚠ İlk sürüm `db.connect(real_cfg)` çağırıyordu; o da şemayı uygulayıp
    MIGRATION'LARI İLERLETİYORDU. Yani `pytest` koşmak, kullanıcının gerçek
    veritabanını sessizce değiştiriyordu — bir test suite'inden beklenecek en
    son şey. (2026-07-27 denetiminde fark edildi: v6 migration'ı, ben onu
    elle koşmadan önce bir test koşusunda uygulanmıştı.)

    Salt-okunur bağlantı ayrıca testin niyetini de doğru anlatıyor: bunlar
    veri KAYNAĞININ davranışını ölçer, veriyi kurmaz.
    """
    p = db.db_path(real_cfg)
    if not p.exists():
        pytest.skip(f"Proje veritabanı yok ({p}) — önce `bist veri backfill`")
    c = db.connect(real_cfg, readonly=True)
    n = c.execute("SELECT COUNT(*) FROM bars_daily").fetchone()[0]
    if n == 0:
        c.close()
        pytest.skip("bars_daily boş — önce `bist veri backfill`")
    yield c
    c.close()


# ------------------------------------------------------------------ yardımcılar
def add_bars(con: sqlite3.Connection, ticker: str, rows: list[tuple]) -> None:
    """rows: [(date, o, h, l, c, v, c_tr)]"""
    now = util.utc_now_iso()
    con.executemany(
        "INSERT OR REPLACE INTO bars_daily "
        "(ticker,date,o,h,l,c,v,c_tr,turnover_try,source,ingested_utc) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(ticker, d, o, h, low, c, v, ctr, (c or 0) * (v or 0), "test", now)
         for d, o, h, low, c, v, ctr in rows])
    con.commit()


def add_index(con: sqlite3.Connection, symbol: str, dates: list[str],
              close: float = 100.0) -> None:
    now = util.utc_now_iso()
    con.executemany(
        "INSERT OR REPLACE INTO index_daily (symbol,date,o,h,l,c,ingested_utc) "
        "VALUES (?,?,?,?,?,?,?)",
        [(symbol, d, close, close, close, close, now) for d in dates])
    con.commit()


def add_universe(con: sqlite3.Connection, ticker: str, *, sector: str = "test",
                 tier: str = "cekirdek", in_live: bool = True,
                 in_measure: bool = True) -> None:
    con.execute(
        "INSERT OR REPLACE INTO universe "
        "(ticker,yf_symbol,name,sector,tier,in_live,in_measure) VALUES (?,?,?,?,?,?,?)",
        (ticker, f"{ticker}.IS", ticker, sector, tier, int(in_live), int(in_measure)))
    con.commit()


def add_plan(con: sqlite3.Connection, plan_id: str, ticker: str = "TEST",
             asof: str = "2024-01-02") -> None:
    """Journal `plan_id` için FK doğrulaması yapar — testte planı önce sakla."""
    con.execute(
        "INSERT OR REPLACE INTO plan_options "
        "(plan_id, asof, ticker, kind, payload, created_utc) VALUES (?,?,?,?,?,?)",
        (plan_id, asof, ticker, "test", "{}", util.utc_now_iso()))
    con.commit()


def add_indicator(con: sqlite3.Connection, cfg: dict, ticker: str, tarih: str,
                  **degerler) -> None:
    """`indicator_daily`'ye tek satır. Verilmeyen kolonlar NULL kalır.

    Kesitsel her oranın PAYDASI bu tablodur (bkz. db.SCHEMA yorumu): burada
    satırı olmayan ticker `factors._panel` ve `regime.breadth` JOIN'lerinde
    sessizce düşer. Testlerin paydayı bilinçli daraltıp genişletebilmesi için
    bu yardımcı gerekiyor.
    """
    cols = ["ticker", "date", "set_version", "computed_utc", *degerler]
    vals = [ticker, tarih, cfg["gostergeler"]["set_version"], util.utc_now_iso(),
            *degerler.values()]
    ph = ",".join("?" * len(cols))
    con.execute(f"INSERT OR REPLACE INTO indicator_daily ({','.join(cols)}) "
                f"VALUES ({ph})", vals)
    con.commit()


def add_quality(con: sqlite3.Connection, ticker: str, tarih: str, *,
                ok: bool = True, zero_vol: float | None = 0.0,
                reasons: list[str] | None = None, bars: int = 252) -> None:
    """`data_quality`'ye tek satır — kalite kapısının açık/kapalı hâlini kurar."""
    con.execute(
        "INSERT OR REPLACE INTO data_quality "
        "(ticker,date,bars_252,zero_vol_ratio_252,max_gap_days,stale_close_days,"
        " unexplained_jump,ok,reasons) VALUES (?,?,?,?,?,?,?,?,?)",
        (ticker, tarih, bars, zero_vol, 3, 1, 0, 1 if ok else 0,
         json.dumps(reasons if reasons is not None else ([] if ok else ["test"]))))
    con.commit()


def is_gunleri(n: int, baslangic: str = "2023-01-02") -> list[str]:
    """`n` ardışık HAFTA İÇİ gün (ISO). Takvim testleri için değil, seri kurmak için."""
    d = date.fromisoformat(baslangic)
    out: list[str] = []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def kur_sentetik_evren(cfg: dict, con: sqlite3.Connection, *, n_ticker: int = 6,
                       n_bar: int = 320, kalite: bool = True,
                       asof_geri: int = 0) -> str:
    """Uçtan uca testler için ÇALIŞAN bir sentetik kurulum. `asof` döner.

    Kurulan: evren + barlar + XU100 endeksi + hesaplanmış göstergeler
    (+ istenirse kalite kaydı). Bu, `llm_io.build_bundle`'ın gerçekten
    üretilebildiği en küçük dünyadır — planlayıcı, faktörler, rejim, seviyeler
    ve haber katmanının tamamı bunun üzerinde koşar.

    Neden gerekli: bu projenin en pahalı hatalarının çoğu TEK MODÜLDE değil,
    modüller arası varsayımda çıktı (paket faktör skorunu taşımıyordu → HF-22
    hiç ateşlenemiyor ve `bist kaydet` NOT NULL ile patlıyordu). O sınıfı
    yakalayan tek şey uçtan uca kurulumdur.

    Sektörler ikili gruplanır (`sek0, sek0, sek1, sek1, …`) — sektör tavanı
    kontrollerinin tetiklenebilir olması için.

    `asof_geri > 0`: `asof` son bardan bu kadar bar GERİYE alınır, yani seride
    "gelecek" barlar kalır. Resolver'ı (üçlü bariyer) çalıştırabilmenin tek
    yolu bu — bariyer tarihine kadar barın var olması gerekir. Look-ahead
    riski yok: hesaplayan her fonksiyon `date <= asof` süzüyor.
    """
    from src import indicators, prices

    tarihler: list[str] = []
    for i in range(n_ticker):
        t = chr(ord("A") + i) * 3
        add_universe(con, t, sector=f"sek{i // 2}")
        rows = bar_serisi(n_bar, fiyat=100.0 + 10 * i, gunluk_egim=0.0015,
                          dalga=4.0 + i, periyot=15 + i)
        add_bars(con, t, rows)
        tarihler = [r[0] for r in rows]

    now = util.utc_now_iso()
    con.executemany(
        "INSERT OR REPLACE INTO index_daily (symbol,date,o,h,l,c,ingested_utc) "
        "VALUES (?,?,?,?,?,?,?)",
        [(("XU100"), d, 100.0 + i * 0.1, 100.0 + i * 0.1, 100.0 + i * 0.1,
          100.0 + i * 0.1, now) for i, d in enumerate(tarihler)])
    con.commit()

    indicators.compute_and_store(cfg, con)
    asof = tarihler[-1 - asof_geri]
    if kalite:
        prices.assess_quality(cfg, con, asof=asof)
    return asof


# Prose'da SAYI YOK: HF-17 paketteki sayılara izin verse de testin amacı denetimi
# sayı tartışmasına sokmak değil. Ticker adı gövdeye giriyor çünkü HF-27 (şablon
# tez) prose'u SAYILARI SOYARAK hash'ler — aynı cümleyi farklı sayılarla
# tekrarlamak yine şablondur.
GECERLI_PROSE = {
    "thesis": ("{t} için taşıyıcı gerekçe: kesitsel sıralamadaki yeri ve trend "
               "kapısından geçmesi birlikte değerlendirildi; plan geometrisi "
               "kabul edilebilir görünüyor ve pozisyon disiplini korunabilir."),
    "counter_scenario": ("{t} tarafında karşı senaryo: sıralamanın ileri getiriyle "
                         "ilişkisiz olması ve geri çekilmenin hiç gelmemesi; bu "
                         "durumda plan tetiklenmez ve tez kendiliğinden düşer."),
    "key_risk": ("{t} ana riski: sektör yoğunlaşması ve haber akışının plan "
                 "penceresine denk gelmesi; likidite daralırsa stop mesafesi "
                 "gerçekleşen kayıptan küçük kalabilir."),
    "falsifier": ("{t} günlük kapanışı destek seviyesinin altına inerse ve hacim "
                  "ortalamanın altında kalırsa tez düşer; beş işlem günü içinde "
                  "gözlemlenebilir bir olaydır."),
}


def analist_ciktisi(bundle: dict, *, plan_secilen: str | None = None,
                    tool: str = "claude-code") -> dict:
    """Denetimden GEÇMESİ gereken, elle kurulmuş geçerli analist çıktısı.

    Kasten sade: `strong_buy` yok (HF-22 yüzdelik bandı ister), `sell` yok
    (HF-21 holdings ister), boğa sinyaliyle çelişen aksiyon yok (HF-20).
    Bir denetim kuralını test etmek isteyen, buradan bir alanı BOZARAK başlar.
    """
    from src import schema

    stocks = []
    for e in bundle["evren"]:
        t = e["ticker"]
        sec = plan_secilen == t and bool(e["plan_menusu"])
        stocks.append({
            "ticker": t,
            "signal": "buy" if sec else "hold",
            "action": "plan_sec" if sec else "izle",
            "selected_plan_id": e["plan_menusu"][0]["plan_id"] if sec else None,
            "veto_code": None,
            "confidence": "orta" if sec else "dusuk",
            **{k: v.format(t=t) for k, v in GECERLI_PROSE.items()},
            "news_refs": [],
            "news_reading": None,
        })
    return {
        "schema_version": schema.OUTPUT_SCHEMA_VERSION,
        "asof": bundle["asof"],
        "bundle_sha": bundle["bundle_sha"],
        "tool": tool,
        "market_view": {
            "regime_agreement": "katiliyorum",
            "regime_note": ("Rejim tespiti makul; geniş tabanlı bir zayıflık "
                            "görünmüyor ama kenar iddiası da yok."),
            "portfolio_action": "koru",
        },
        "stocks": stocks,
        "not_covered": [],
        "analyst_notes": "",
    }


def bar_serisi(n: int, *, baslangic: str = "2023-01-02", fiyat: float = 100.0,
               gunluk_egim: float = 0.0, dalga: float = 0.0, periyot: int = 20,
               hacim: float = 5_000_000.0, temettu_verimi: float = 0.0
               ) -> list[tuple]:
    """DETERMİNİSTİK sentetik bar serisi — `add_bars` biçiminde.

    Rastgelelik YOK (`math.sin` ile dalga): aynı çağrı daima aynı seriyi verir,
    yoksa gösterge testleri arada bir patlayan testlere dönüşür.

    `temettu_verimi > 0` iken `c_tr` ham `c`'den AYRIŞIR — hangi göstergenin
    hangi seriden beslendiğini (bkz. indicators.py başlığı) test etmenin tek
    yolu bu ayrışmayı kurmaktır.
    """
    rows = []
    for i, d in enumerate(is_gunleri(n, baslangic)):
        taban = fiyat * (1.0 + gunluk_egim) ** i
        c = taban + dalga * math.sin(2 * math.pi * i / periyot)
        o = c * 0.998
        h = c * 1.010
        low = c * 0.990
        c_tr = c * (1.0 + temettu_verimi) ** i
        rows.append((d, round(o, 4), round(h, 4), round(low, 4), round(c, 4),
                     hacim, round(c_tr, 4)))
    return rows


@pytest.fixture(autouse=True)
def advisor_real_archive_is_read_only(monkeypatch):
    """2026-09-16: yeni V2 defteri de testlerin gerçek veri yasağına dahildir."""
    from pathlib import Path
    project = Path(__file__).resolve().parents[1]
    protected = [project/'data/advisor', project.parent/'gold_tracking_system/data/advisor', project.parent/'BIST tahmin/data/advisor']
    original = Path.open
    def safe_open(path, mode='r', *args, **kwargs):
        target = path.resolve()
        if any(flag in mode for flag in ('w','a','x','+')) and any(target.is_relative_to(p.resolve()) for p in protected):
            raise RuntimeError('Test gerçek V2 arşivine yazamaz; tmp_path kullan.')
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', safe_open)
