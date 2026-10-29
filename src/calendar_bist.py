"""BIST işlem takvimi.

GEÇMİŞ işlem günleri BARLARDAN TÜRETİLİR — otoriter ve sıfır bakım.
`holidays_tr.yaml` YALNIZCA gelecek tarihler için gerekli: zaman bariyeri hesabı
("bugünden 20 işlem günü sonrası?") geleceğe bakar ve gelecekteki barlar yoktur.

Sınır kritik: sınırın solunda barlara, sağında tatil listesine güvenilir. İkisini
karıştırmak (ör. geçmiş için tatil listesine bakmak) 2020'de bir gün kayması
üretirdi ve bu tüm zaman bariyerlerini bir gün kaydırırdı.

⚠ İKİ KAYNAK, ÇÜNKÜ TEK KAYNAK YALAN SÖYLEDİ (ADR #012, 2026-07-29).
Bu dosya eskiden takvimi YALNIZ XU100'den türetiyordu ve docstring'i
*"eksik 9 hafta-içi gün holidays_tr.yaml ile BİREBİR aynı"* diye ölçülmüş bir
iddia taşıyordu. Taze veri o iddiayı çürüttü: yfinance bir SEANS GÜNÜNDE de
endeks barı vermeyebiliyor — 2026-07-24 ve 2026-07-28'i XU100, XU030 ve
XBANK'in üçünde birden atladı; oysa 70 hissenin hepsi o günler işlem gördü.

Ölçüldü (2015-2026, gerçek veri) ve ayrımda GRİ BÖLGE YOK:

    endeks barı YOK ama hisse barı VAR    → 10 gün, hepsinde 67-70 hisse
    holidays_tr.yaml'deki gerçek tatiller → 12 gün, hepsinde  0 hisse

Bu yüzden bir gün, endeks barı VARSA **ya da** en az
`takvim.min_hisse_bari_seans_icin` kadar hisse barı varsa işlem günü sayılır.

Not — döngüsellik yok: `prices.purge_phantom_bars` hayalet barı elerken
(1) o=h=l=c, (2) v=0 ve (3) endeks barı yok koşullarının ÜÇÜNÜ birden arıyor.
Yani gerçek bir seansın barları purge'den sağ çıkıyor (ölçüldü: 142 bar
"endeksin kendi boşluğu, hisse barı gerçek" diye korundu) ve gerçek tatilin
barları eleniyor. İki modül artık aynı olgu hakkında AYNI şeyi söylüyor;
eskiden zıt varsayım taşıyorlardı ve çelişkiyi hiçbir test görmüyordu.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from . import util


class BistCalendar:
    def __init__(self, cfg: dict, con: sqlite3.Connection | None = None) -> None:
        self.cfg = cfg
        tcfg = cfg["takvim"]
        self.tz = ZoneInfo(tcfg["timezone"])
        self._seans = tcfg["seans"]

        hol = util.load_yaml(cfg["paths"]["holidays_file"])
        self._tam_gun: set[str] = {
            str(d) for yil in (hol.get("tam_gun") or {}).values() for d in yil
        }
        self._yarim_gun: set[str] = {
            str(d) for yil in (hol.get("yarim_gun") or {}).values() for d in yil
        }

        # Barlardan türetilen otoriter geçmiş
        self._bar_gunleri: set[str] = set()
        self._son_bar: date | None = None
        if con is not None:
            self.reload(con)

    # ------------------------------------------------------------ yükleme
    def reload(self, con: sqlite3.Connection) -> int:
        """Otoriter işlem günlerini yeniden okur. Gün sayısını döner.

        İKİ KAYNAĞIN BİRLEŞİMİ (bkz. modül docstring'i): endeks barı olan her
        gün + eşiği aşan sayıda hisse barı olan her gün. Tek kaynak yeterli
        değil çünkü yfinance gerçek bir seansta endeks barını atlayabiliyor ve
        bunu SESSİZCE yapıyor — o gün tatil sanılıp takvim aritmetiği kayıyordu.
        """
        sym = self.cfg["takvim"]["turet_kaynak_endeks"]
        gunler = {r[0] for r in con.execute(
            "SELECT date FROM index_daily WHERE symbol = ?", (sym,)).fetchall()}

        # Hisse tarafı: eşik "bu kadar isim işlem gördüyse borsa açıktı" demek.
        # Ölçülen dağılımda 0 ile 67 arasında gözlem YOK; eşik boşluğun ortasında.
        esik = int(self.cfg["takvim"]["min_hisse_bari_seans_icin"])
        gunler |= {r[0] for r in con.execute(
            "SELECT date FROM bars_daily GROUP BY date HAVING COUNT(*) >= ?",
            (esik,)).fetchall()}

        self._bar_gunleri = gunler
        # Otoriter geçmişin sınırı da birleşimden gelir: endeks bir gün
        # gecikirse hisse barları o günü zaten kanıtlıyor.
        self._son_bar = date.fromisoformat(max(gunler)) if gunler else None
        return len(self._bar_gunleri)

    @property
    def son_bar(self) -> date | None:
        """Türetilmiş geçmişin sınırı. Bu tarihten sonrası tatil dosyasıyla tahmin edilir."""
        return self._son_bar

    # ------------------------------------------------------------ gün sorguları
    def is_trading_day(self, d: date | str) -> bool:
        d = self._as_date(d)
        iso = d.isoformat()
        if self._son_bar is not None and d <= self._son_bar:
            return iso in self._bar_gunleri        # otoriter: bar var mı
        return d.weekday() < 5 and iso not in self._tam_gun   # tahmin

    def is_half_day(self, d: date | str) -> bool:
        """Arife — bar OLUŞUR, seans kısadır. Takvim aritmetiğinde işlem günü SAYILIR."""
        return self._as_date(d).isoformat() in self._yarim_gun

    def is_derived(self, d: date | str) -> bool:
        """Bu tarih otoriter (bar) mı, tahmini (tatil listesi) mi?"""
        return self._son_bar is not None and self._as_date(d) <= self._son_bar

    # ------------------------------------------------------------ aritmetik
    def next_trading_day(self, d: date | str, *, inclusive: bool = False) -> date:
        d = self._as_date(d)
        if inclusive and self.is_trading_day(d):
            return d
        for _ in range(400):
            d += timedelta(days=1)
            if self.is_trading_day(d):
                return d
        raise RuntimeError("400 gün içinde işlem günü bulunamadı — takvim bozuk")

    def prev_trading_day(self, d: date | str, *, inclusive: bool = False) -> date:
        d = self._as_date(d)
        if inclusive and self.is_trading_day(d):
            return d
        for _ in range(400):
            d -= timedelta(days=1)
            if self.is_trading_day(d):
                return d
        raise RuntimeError("400 gün geriye işlem günü bulunamadı — takvim bozuk")

    def add_trading_days(self, d: date | str, n: int) -> date:
        """d'den n işlem günü ileri/geri. n=0 → d'nin kendisi (işlem günü olmasa bile).

        `trading_days_between` ile tersine dönüşümlüdür:
            trading_days_between(d, add_trading_days(d, n)) == n   (d işlem günüyse)
        """
        d = self._as_date(d)
        if n == 0:
            return d
        adim = 1 if n > 0 else -1
        kalan = abs(n)
        while kalan:
            d += timedelta(days=adim)
            if self.is_trading_day(d):
                kalan -= 1
        return d

    def trading_days_between(self, d0: date | str, d1: date | str) -> int:
        """(d0, d1] aralığındaki işlem günü sayısı. d1 < d0 ise negatif."""
        d0, d1 = self._as_date(d0), self._as_date(d1)
        if d0 == d1:
            return 0
        isaret = 1 if d1 > d0 else -1
        bas, son = (d0, d1) if isaret > 0 else (d1, d0)
        n, cur = 0, bas
        while cur < son:
            cur += timedelta(days=1)
            if self.is_trading_day(cur):
                n += 1
        return n * isaret

    def trading_days(self, d0: date | str, d1: date | str) -> list[date]:
        """[d0, d1] aralığındaki işlem günleri, sıralı."""
        d0, d1 = self._as_date(d0), self._as_date(d1)
        out, cur = [], d0
        while cur <= d1:
            if self.is_trading_day(cur):
                out.append(cur)
            cur += timedelta(days=1)
        return out

    # ------------------------------------------------------------ seans
    def session_state(self, ts_utc: datetime | None = None) -> str:
        """'kapali'|'acilis_muzayede'|'surekli_islem'|'kapanis_muzayede'|'sonrasi'

        Saatler config'ten okunur, koda gömülmez. Faz 1 DoD'sinde TEYİT EDİLDİ
        (2026-07-26): 09:40 emir toplama · 10:00-18:00 KESİNTİSİZ sürekli işlem
        (öğle arası 2016'da kaldırıldı) · 18:10 kapanış seansı bitişi.
        Gerekçe `config.takvim.seans` yorumunda.
        """
        ts = (ts_utc or util.utc_now()).astimezone(self.tz)
        if not self.is_trading_day(ts.date()):
            return "kapali"
        t = ts.time()
        s = self._session_times(ts.date())
        if t < self._t(s["acilis_muzayede_baslangic"]):
            return "kapali"
        if t < self._t(s["surekli_islem_baslangic"]):
            return "acilis_muzayede"
        if t < self._t(s["surekli_islem_bitis"]):
            return "surekli_islem"
        if t < self._t(s["kapanis_muzayede_bitis"]):
            return "kapanis_muzayede"
        return "sonrasi"

    def session_close_utc(self, d: date | str) -> datetime:
        """`d` seansının KAPANIŞ anı, UTC olarak.

        Neden gerekli: "bugün koşu oldu mu?" sorusu duvar saatiyle sorulamaz
        (L-026). Doğru referans "SEANS KAPANDIKTAN SONRA koşu başladı mı?"dır
        ve o karşılaştırma için seansın kapanış ANI lazım — takvim günü değil.
        """
        d = self._as_date(d)
        t = self._t(self._session_times(d)["kapanis_muzayede_bitis"])
        return datetime.combine(d, t, tzinfo=self.tz).astimezone(timezone.utc)

    def last_closed_session(self, ts_utc: datetime | None = None) -> date:
        """Kapanışı KESİNLEŞMİŞ son işlem günü.

        Analiz daima kapanmış seans üzerinden yapılır — açık seansın barı henüz
        değişebilir ve onu kullanmak look-ahead'in en sinsi biçimidir.
        """
        instant = ts_utc or util.utc_now()
        ts = instant.astimezone(self.tz)
        d = ts.date()
        if self.is_trading_day(d) and self.session_state(instant) == "sonrasi":
            return d
        return self.prev_trading_day(d)

    # ------------------------------------------------------------ iç
    def _session_times(self, day):
        result = dict(self._seans)
        if self.is_half_day(day):
            result['surekli_islem_bitis'] = self._seans.get('yarim_gun_surekli_islem_bitis','12:30')
            result['kapanis_muzayede_bitis'] = self._seans.get('yarim_gun_kapanis_muzayede_bitis','12:40')
        return result

    @staticmethod
    def _as_date(d: date | str) -> date:
        if isinstance(d, datetime):
            return d.date()
        if isinstance(d, date):
            return d
        parsed = util.parse_date(d)
        if parsed is None:
            raise ValueError(f"Tarih çözülemedi: {d!r}")
        return parsed

    @staticmethod
    def _t(hhmm: str) -> time:
        h, m = hhmm.split(":")
        return time(int(h), int(m))
