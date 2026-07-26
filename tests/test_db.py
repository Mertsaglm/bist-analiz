"""Şema, migration ve deterministik dump testleri."""

from __future__ import annotations

import pytest

from src import db, dbdump, migrations
from tests.conftest import add_bars, add_index, add_universe


class TestMigrations:
    def test_yeni_db_hedef_surumde(self, con):
        """Yeni kurulan veritabanı TÜM migration'lar uygulanmış olarak açılır."""
        assert migrations.current_version(con) == migrations.target_version()

    def test_apply_idempotent(self, con):
        v = migrations.current_version(con)
        assert migrations.apply(con) == []          # bekleyen yok
        assert migrations.current_version(con) == v

    def test_sira_kopuksa_hata(self, con, monkeypatch):
        """Aradaki adım eksikse sessizce atlamaz — patlar.

        Sessiz atlama, farklı makinelerdeki veritabanlarının ayrışması demektir.
        """
        kopuk = migrations.current_version(con) + 3
        monkeypatch.setattr(migrations, "MIGRATIONS",
                            [(kopuk, "kopuk", lambda c: None)])
        with pytest.raises(RuntimeError, match="sırası kopuk"):
            migrations.apply(con)

    def test_migration_uygulanir_ve_surum_ilerler(self, con, monkeypatch):
        sonraki = migrations.current_version(con) + 1
        monkeypatch.setattr(migrations, "MIGRATIONS", [
            (sonraki, "test kolonu", lambda c: c.execute(
                "ALTER TABLE holdings ADD COLUMN test_kolon TEXT")),
        ])
        assert migrations.apply(con) == [f"v{sonraki}: test kolonu"]
        assert migrations.current_version(con) == sonraki
        kolonlar = [r[1] for r in con.execute("PRAGMA table_info(holdings)")]
        assert "test_kolon" in kolonlar


class TestSema:
    def test_outcomes_llm_yazamaz(self, con):
        """`outcomes` tablosunda LLM'in yazabileceği TEK kolon olmamalı.

        Bu bir mimari değişmez: kendi ödevini notlandıran sistem kayar.
        Aşağıdaki liste büyürse birisi LLM'e sonuç yazdırmaya çalışıyor demektir.
        """
        kolonlar = {r[1] for r in con.execute("PRAGMA table_info(outcomes)")}
        yasak = {"thesis", "signal", "confidence", "action", "veto_code",
                 "counter_scenario", "key_risk", "falsifier", "news_reading",
                 "analyst_notes", "llm_comment"}
        assert not (kolonlar & yasak), f"outcomes'a LLM alanı sızmış: {kolonlar & yasak}"

    def test_predictions_benzersizlik(self, con):
        """(asof, ticker, run_id) UNIQUE — journal DEĞİŞMEZ."""
        idx = con.execute("PRAGMA index_list(predictions)").fetchall()
        assert any(r[2] for r in idx), "predictions üzerinde unique kısıt yok"

    def test_iki_fiyat_serisi_var(self, con):
        """c (seviye/plan) ve c_tr (getiri/momentum) ayrı kolonlar olmalı."""
        kolonlar = {r[1] for r in con.execute("PRAGMA table_info(bars_daily)")}
        assert {"c", "c_tr"} <= kolonlar

    def test_foreign_keys_acik(self, con):
        assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1


class TestDump:
    def _doldur(self, con):
        add_universe(con, "TEST")
        add_index(con, "XU100", ["2026-01-05", "2026-01-06"])
        add_bars(con, "TEST", [
            ("2026-01-05", 10.5, 11.0, 9.5, 10.0, 1000, 10.0),
            ("2026-01-06", 10.0, 12.0, 10.0, 11.5, 2000, 11.5),
        ])

    def test_deterministik(self, cfg, con):
        """Aynı veri → BİREBİR aynı metin.

        Aksi halde `git diff` her çalıştırmada gürültü üretir ve
        "veri değişti mi?" sorusu cevaplanamaz hale gelir.
        """
        self._doldur(con)
        p1 = dbdump.dump(cfg).read_text(encoding="utf-8")
        p2 = dbdump.dump(cfg).read_text(encoding="utf-8")
        assert p1 == p2

    def test_satirlar_sirali(self, cfg, con):
        self._doldur(con)
        icerik = dbdump.dump(cfg).read_text(encoding="utf-8")
        i5 = icerik.index("2026-01-05")
        i6 = icerik.index("2026-01-06")
        assert i5 < i6, "satırlar birincil anahtara göre sıralı değil"

    def test_turev_tablolar_atlanir(self, cfg, con):
        """Yeniden üretilebilir türev veri dump'a girmez — repo şişmesin."""
        self._doldur(con)
        icerik = dbdump.dump(cfg).read_text(encoding="utf-8")
        for t in dbdump.ATLA:
            assert f"INSERT INTO {t} " not in icerik

    def test_restore_dolu_dbye_yazmaz(self, cfg, con):
        """Üzerine yazmak veri kaybıdır — açıkça reddeder."""
        self._doldur(con)
        dbdump.dump(cfg)
        with pytest.raises(RuntimeError, match="boş değil"):
            dbdump.restore(cfg)

    def test_restore_bos_dbye_yazar(self, cfg, con):
        self._doldur(con)
        dbdump.dump(cfg)
        for t in ("bars_daily", "index_daily", "universe"):
            con.execute(f"DELETE FROM {t}")
        con.commit()
        con.close()
        sayim = dbdump.restore(cfg)
        assert sayim["bars_daily"] == 2
        assert sayim["universe"] == 1

    def test_nan_null_olur(self, cfg, con):
        add_universe(con, "TEST")
        add_bars(con, "TEST", [("2026-01-05", 10.0, 11.0, 9.0, 10.0, None, None)])
        icerik = dbdump.dump(cfg).read_text(encoding="utf-8")
        assert "NULL" in icerik and "nan" not in icerik.lower()


class TestYardimcilar:
    def test_upsert_bos_liste(self, con):
        assert db.upsert_many(con, "holdings", ["ticker", "qty"], []) == 0

    def test_scalar_bos_none(self, con):
        assert db.scalar(con, "SELECT MAX(date) FROM bars_daily") is None
