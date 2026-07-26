"""Veri kalite kapısı testleri.

Kapının varlık sebebi: yfinance'in BIST kusurları GENEL değil KAYIT BAZLI.
"yfinance bozuk mu?" yanlış soru; doğru soru "bu ticker'ın bu verisi
kullanılabilir mi?".
"""

from __future__ import annotations

import pytest

from src import prices
from tests.conftest import add_bars, add_universe


def _bar_serisi(n: int, *, sifir_hacim_her: int | None = None,
                sabit_fiyat: bool = False, baslangic: str = "2025-01-01"):
    """n işlem günlük sentetik seri (hafta sonlarını atlar)."""
    from datetime import date, timedelta
    d = date.fromisoformat(baslangic)
    rows, fiyat = [], 100.0
    while len(rows) < n:
        if d.weekday() < 5:
            i = len(rows)
            if not sabit_fiyat:
                fiyat = 100.0 + i * 0.1
            v = 0 if (sifir_hacim_her and i % sifir_hacim_her == 0) else 1_000_000
            rows.append((d.isoformat(), fiyat, fiyat * 1.01, fiyat * 0.99, fiyat, v, fiyat))
        d += timedelta(days=1)
    return rows


class TestSifirHacimKapisi:
    def test_temiz_seri_gecer(self, cfg, con):
        add_universe(con, "TEMIZ")
        add_bars(con, "TEMIZ", _bar_serisi(200))
        r = prices.assess_quality(cfg, con, tickers=["TEMIZ"])[0]
        assert r["ok"] is True, r["reasons"]
        assert r["zero_vol_ratio_252"] == 0.0

    def test_sasa_profili_elenir(self, cfg, con):
        """SASA vakası: her ikinci barda sıfır hacim (~%50) → kapı elemeli.

        Gerçek ölçüm (2026-07-26): SASA son 252 barın %45.2'sinde hacim sıfır;
        diğer 18 ticker %0.0. Hacim tabanlı her faktör bu isimde çöp üretir.
        """
        add_universe(con, "SASAVARI")
        add_bars(con, "SASAVARI", _bar_serisi(200, sifir_hacim_her=2))
        r = prices.assess_quality(cfg, con, tickers=["SASAVARI"])[0]
        assert r["ok"] is False
        assert any("sıfır hacim" in x for x in r["reasons"])

    def test_esik_altinda_kalirsa_gecer(self, cfg, con):
        """Eşik %5; her 40 barda bir sıfır (%2.5) → geçmeli."""
        add_universe(con, "AZSIFIR")
        add_bars(con, "AZSIFIR", _bar_serisi(200, sifir_hacim_her=40))
        r = prices.assess_quality(cfg, con, tickers=["AZSIFIR"])[0]
        assert r["ok"] is True, r["reasons"]


class TestDigerKapilar:
    def test_bayat_kapanis_yakalanir(self, cfg, con):
        add_universe(con, "BAYAT")
        add_bars(con, "BAYAT", _bar_serisi(200, sabit_fiyat=True))
        r = prices.assess_quality(cfg, con, tickers=["BAYAT"])[0]
        assert r["ok"] is False
        assert any("bayat" in x for x in r["reasons"])

    @staticmethod
    def _seviye_atlamasi(rows: list, i: int, carpan: float) -> list:
        """i. bardan İTİBAREN kalıcı seviye kayması.

        Gerçekçi olan bu: bedelsiz/temettü fiyatı bir kez kaydırır ve orada
        bırakır. Tek barı çarpmak yapay bir sıçra-ve-dön üretir, yani İKİ
        büyük getiri — testi de ölçtüğü şeyi de bozar.
        """
        return [r if k < i else
                (r[0], r[1] * carpan, r[2] * carpan, r[3] * carpan,
                 r[4] * carpan, r[5], r[6] * carpan)
                for k, r in enumerate(rows)]

    def test_aciklanamayan_sicrama_yakalanir(self, cfg, con):
        """|getiri| > %15 ve kayıtlı kurumsal işlem yok → bayrak."""
        add_universe(con, "SICRA")
        rows = self._seviye_atlamasi(_bar_serisi(100), 50, 1.5)
        add_bars(con, "SICRA", rows)
        r = prices.assess_quality(cfg, con, tickers=["SICRA"])[0]
        assert r["unexplained_jump"] == 1
        assert any("sıçrama" in x for x in r["reasons"])

    def test_kurumsal_islem_varsa_sicrama_sayilmaz(self, cfg, con):
        """Kayıtlı bir bölünme/temettü varsa o gün 'açıklanamayan' değildir."""
        add_universe(con, "SICRA2")
        rows = self._seviye_atlamasi(_bar_serisi(100), 50, 1.5)
        add_bars(con, "SICRA2", rows)
        con.execute("INSERT INTO corporate_actions (ticker,date,kind,value,source) "
                    "VALUES (?,?,?,?,?)", ("SICRA2", rows[50][0], "bolunme", 2.0, "test"))
        con.commit()
        r = prices.assess_quality(cfg, con, tickers=["SICRA2"])[0]
        assert r["unexplained_jump"] == 0
        assert not any("sıçrama" in x for x in r["reasons"])

    def test_veri_yoksa_elenir(self, cfg, con):
        add_universe(con, "BOS")
        r = prices.assess_quality(cfg, con, tickers=["BOS"])[0]
        assert r["ok"] is False
        assert r["reasons"] == ["veri yok"]

    def test_kalite_tabloya_yaziliyor(self, cfg, con):
        add_universe(con, "TEMIZ")
        add_bars(con, "TEMIZ", _bar_serisi(200))
        prices.assess_quality(cfg, con, tickers=["TEMIZ"])
        asof = con.execute("SELECT MAX(date) FROM data_quality").fetchone()[0]
        qm = prices.quality_map(con, asof)
        assert "TEMIZ" in qm
        assert qm["TEMIZ"]["ok"] is True
        assert isinstance(qm["TEMIZ"]["reasons"], list)


class TestGercekVeri:
    def test_sasa_gercekten_eleniyor(self, real_cfg, real_con):
        """Kapının canlı test vakası. SASA evrende bilerek duruyor (in_live=0)."""
        rows = prices.assess_quality(real_cfg, real_con, tickers=["SASA"])
        if not rows or rows[0]["bars_252"] == 0:
            pytest.skip("SASA verisi yok")
        assert rows[0]["ok"] is False, "SASA kapıdan geçti — kapı çalışmıyor"

    def test_canli_evrenin_tamami_geciyor(self, real_cfg, real_con):
        """SASA dışındaki her canlı isim kapıdan geçmeli.

        Geçmiyorsa ya veri bozulmuş ya evren revize edilmeli — ikisi de
        sessizce devam edilecek durum değil.
        """
        from src import universe
        canli = [t for t in universe.live(real_con)]
        rows = prices.assess_quality(real_cfg, real_con, tickers=canli)
        kotu = [(r["ticker"], r["reasons"]) for r in rows if not r["ok"]]
        assert not kotu, f"canlı evrende kapıdan geçemeyen isimler: {kotu}"
