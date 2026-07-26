"""BIST işlem takvimi.

GEÇMİŞ işlem günleri XU100 bar tarihlerinden TÜRETİLİR — otoriter ve sıfır bakım.
Ölçüm (2026-07-26): 2026 YTD'de XU100 138 bar / 147 iş günü; eksik 9 hafta-içi gün
`holidays_tr.yaml` listesiyle BİREBİR aynı. Yani tatil dosyasını geçmiş için
tutmak gereksiz iş ve sessiz hata kaynağıdır.

`holidays_tr.yaml` YALNIZCA gelecek tarihler için gerekli: zaman bariyeri hesabı
("bugünden 20 işlem günü sonrası?") geleceğe bakar ve gelecekteki barlar yoktur.

Sınır kritik: sınırın solunda barlara, sağında tatil listesine güvenilir. İkisini
karıştırmak (ör. geçmiş için tatil listesine bakmak) 2020'de bir gün kayması
üretirdi ve bu tüm zaman bariyerlerini bir gün kaydırırdı.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta
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
        """Endeks bar tarihlerini yeniden okur. Bar sayısını döner."""
        sym = self.cfg["takvim"]["turet_kaynak_endeks"]
        rows = con.execute(
            "SELECT date FROM index_daily WHERE symbol = ? ORDER BY date", (sym,)
        ).fetchall()
        self._bar_gunleri = {r[0] for r in rows}
        self._son_bar = date.fromisoformat(rows[-1][0]) if rows else None
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

        ⚠ Saatler config'ten okunur ve config'te DOĞRULA: notu var — BIST 2016'da
        hisse senedinde öğle arasını kaldırdı (sürekli işlem), ama tam dakikalar
        Faz 1 DoD'sinde resmî kaynağa karşı teyit edilecek. Koda gömülmez.
        """
        ts = (ts_utc or util.utc_now()).astimezone(self.tz)
        if not self.is_trading_day(ts.date()):
            return "kapali"
        t = ts.time()
        s = self._seans
        if t < self._t(s["acilis_muzayede_baslangic"]):
            return "kapali"
        if t < self._t(s["surekli_islem_baslangic"]):
            return "acilis_muzayede"
        if t < self._t(s["surekli_islem_bitis"]):
            return "surekli_islem"
        if t < self._t(s["kapanis_muzayede_bitis"]):
            return "kapanis_muzayede"
        return "sonrasi"

    def last_closed_session(self, ts_utc: datetime | None = None) -> date:
        """Kapanışı KESİNLEŞMİŞ son işlem günü.

        Analiz daima kapanmış seans üzerinden yapılır — açık seansın barı henüz
        değişebilir ve onu kullanmak look-ahead'in en sinsi biçimidir.
        """
        ts = (ts_utc or util.utc_now()).astimezone(self.tz)
        d = ts.date()
        if self.is_trading_day(d) and self.session_state(ts_utc) == "sonrasi":
            return d
        return self.prev_trading_day(d)

    # ------------------------------------------------------------ iç
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
