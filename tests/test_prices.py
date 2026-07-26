"""Fiyat katmanı testleri.

Bu dosyanın asıl işi VERİ KAYNAĞININ davranışını sabitlemek. LESSONS L-005:
araştırmadan gelen "bilinen sorun" bilgisi bayatlar; inancı fixture testine
çevir ki kaynak regresyona giderse CI söylesin.
"""

from __future__ import annotations

import pytest

from src import prices
from tests.conftest import add_bars, add_index, add_universe


# ============================================================ gerçek veri
class TestKaynakDavranisi:
    """yfinance'in BIST davranışı — inanç değil, ölçüm."""

    def test_temettu_duzeltmesi_uygulaniyor(self, real_con):
        """TUPRS 2025-03-28, 7.78 TL temettü.

        Ham kapanış temettü kadar düşer (−%2.95); toplam getiri serisi düşmez
        (+%2.67). İkisi AYNI yönde çıkarsa `c_tr` artık toplam getiri değildir
        ve momentum faktörleri sessizce bozulur.
        """
        df = prices.bars(real_con, "TUPRS", start="2025-03-20", end="2025-04-02")
        if df.empty or "2025-03-28" not in set(df["date"]):
            pytest.skip("TUPRS 2025-03-28 barı veritabanında yok")

        i = df.index[df["date"] == "2025-03-28"][0]
        assert i > 0, "önceki bar gerekli"
        ham = df["c"][i] / df["c"][i - 1] - 1
        duz = df["c_tr"][i] / df["c_tr"][i - 1] - 1

        assert ham < 0, f"ham getiri negatif olmalı (temettü düşüşü), bulunan {ham:.4f}"
        assert duz > 0, f"düzeltilmiş getiri pozitif olmalı, bulunan {duz:.4f}"
        assert duz - ham > 0.04, (
            "toplam getiri ile ham getiri arasındaki fark temettü kadar olmalı; "
            f"fark {duz - ham:.4f} — yfinance düzeltmeyi bırakmış olabilir")

    def test_bedelsiz_geri_duzeltiliyor(self, real_con):
        """FROTO 2025-05-07, 10:1 bedelsiz. Seri sürekli olmalı.

        Geri düzeltme çalışmazsa o gün ~%90 düşüş görünür ve bu, sistemin
        her katmanını (stop, ATR, momentum) tek başına bozar.
        """
        df = prices.bars(real_con, "FROTO", start="2025-05-01", end="2025-05-15")
        if df.empty or "2025-05-07" not in set(df["date"]):
            pytest.skip("FROTO 2025-05-07 barı veritabanında yok")

        i = df.index[df["date"] == "2025-05-07"][0]
        assert i > 0
        getiri = abs(df["c"][i] / df["c"][i - 1] - 1)
        assert getiri < 0.05, (
            f"bedelsiz gününde |getiri| %{getiri*100:.1f} — seri süreksiz, "
            "yfinance geri düzeltmeyi bırakmış olabilir")

    def test_tatil_gunlerinde_bar_yok(self, real_con, real_cfg):
        """Hayalet bar ayıklaması gerçekten çalışıyor mu.

        Yahoo, BIST kapalıyken v=0 & o=h=l=c bar üretiyor. 2026-05-27/28/29
        Kurban Bayramı — bu tarihlerde HİÇBİR hissenin barı olmamalı.
        """
        for tarih in ("2026-05-27", "2026-05-28", "2026-05-29"):
            n = real_con.execute(
                "SELECT COUNT(*) FROM bars_daily WHERE date = ?", (tarih,)).fetchone()[0]
            assert n == 0, f"{tarih} tatil ama {n} bar var — hayalet ayıklaması çalışmıyor"

    def test_endeks_tatilde_temiz(self, real_con):
        """XU100 hayalet bar ÜRETMİYOR — takvimin otoriter kaynağı olmasının şartı."""
        n = real_con.execute(
            "SELECT COUNT(*) FROM index_daily WHERE symbol='XU100' "
            "AND date IN ('2026-05-27','2026-05-28','2026-05-29','2026-01-01')"
        ).fetchone()[0]
        assert n == 0, "XU100'de tatil barı var — takvim türetmesi güvenilmez"


# ============================================================ sentetik
class TestHayaletAyiklama:
    def test_sadece_uc_kosul_birlikte_siler(self, cfg, con):
        """Ayıklama ölçütü: düz VE sıfır hacim VE endekste yok.

        Üçünün birleşimi şart. Ölçüm (2026-07-26) gösterdi ki:
          - yalnız "endekste yok" → 142 gerçek bar silinirdi (endeks boşlukları)
          - yalnız "düz+sıfır"    →  63 gerçek bar silinirdi (işlem durdurma)
        """
        add_universe(con, "TEST")
        add_index(con, "XU100", ["2026-01-05", "2026-01-06", "2026-01-08"])
        add_bars(con, "TEST", [
            ("2026-01-05", 10, 11, 9, 10, 1000, 10),    # normal seans
            ("2026-01-06", 10, 10, 10, 10, 0, 10),      # düz+sıfır AMA endekste VAR → kalmalı
            ("2026-01-07", 10, 10, 10, 10, 0, 10),      # düz+sıfır+endekste YOK → HAYALET
            ("2026-01-08", 10, 12, 9, 11, 2000, 11),    # normal
            ("2026-01-09", 11, 13, 10, 12, 3000, 12),   # endekste yok AMA gerçek → kalmalı
        ])
        r = prices.purge_phantom_bars(cfg, con)

        assert r["silinen"] == 1
        kalan = set(prices.bars(con, "TEST")["date"])
        assert "2026-01-07" not in kalan, "hayalet bar silinmedi"
        assert "2026-01-06" in kalan, "gerçek seansta düz+sıfır bar yanlışlıkla silindi"
        assert "2026-01-09" in kalan, "endeks boşluğundaki gerçek bar yanlışlıkla silindi"

    def test_endeks_sonrasina_dokunmaz(self, cfg, con):
        """Endeks bir gün gecikebilir; o penceredeki hisse barları gerçektir.

        Doğrulandı: THYAO 2026-07-24 (hacim 23,4mn) varken XU100 son barı 07-23.
        """
        add_universe(con, "TEST")
        add_index(con, "XU100", ["2026-01-05"])
        add_bars(con, "TEST", [
            ("2026-01-05", 10, 11, 9, 10, 1000, 10),
            ("2026-01-06", 10, 10, 10, 10, 0, 10),   # endeks sınırının SONRASI → korunur
        ])
        r = prices.purge_phantom_bars(cfg, con)
        assert r["silinen"] == 0
        assert "2026-01-06" in set(prices.bars(con, "TEST")["date"])

    def test_endeks_yoksa_atlar(self, cfg, con):
        """Endeks verisi yokken ayıklama YAPILMAZ — ölçüt kurulamaz.

        Sessizce her şeyi silmek yerine açıkça atlar ve uyarır.
        """
        add_universe(con, "TEST")
        add_bars(con, "TEST", [("2026-01-06", 10, 10, 10, 10, 0, 10)])
        r = prices.purge_phantom_bars(cfg, con)
        assert r["atlandi"] is True
        assert r["silinen"] == 0


class TestOkuma:
    def test_bars_tarihe_gore_sirali(self, con):
        add_universe(con, "TEST")
        add_bars(con, "TEST", [
            ("2026-01-08", 3, 3, 3, 3, 1, 3),
            ("2026-01-05", 1, 1, 1, 1, 1, 1),
            ("2026-01-06", 2, 2, 2, 2, 1, 2),
        ])
        df = prices.bars(con, "TEST")
        assert list(df["date"]) == ["2026-01-05", "2026-01-06", "2026-01-08"]

    def test_turnover_hesaplaniyor(self, con):
        add_universe(con, "TEST")
        add_bars(con, "TEST", [("2026-01-05", 10, 10, 10, 10, 500, 10)])
        assert prices.bars(con, "TEST")["turnover_try"][0] == pytest.approx(5000.0)
