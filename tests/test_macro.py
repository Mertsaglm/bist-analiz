"""Makro bağlam testleri — EKSİK VERİ UYDURULMAZ.

`macro.context()` sözleşmesi tek cümle: **veri yoksa anahtar sözlükte HİÇ
BULUNMAZ** — `None` olarak bile değil. Rapor o satırı gizler. Yerine vekil
koymak ölçümü sahtelemektir (gold projesindeki karar aynen geçerli: `^TNX`
nominal getiridir, onu "reel faiz" diye sunmak sahteleme olurdu).

İki hesap ayrıca sabitlenir, ikisi de "makul görünen yanlış" üretebilir:

* **Reel faiz FISHER'dır, çıkarma DEĞİL.** Yüksek enflasyonda `faiz − enflasyon`
  ciddi biçimde yanlıştır ve yanlışlığı gözle görünmez.
* **TÜFE YoY penceresi TARİHE göre kurulur, satır sayısına göre değil.** İlk
  sürüm `rows[-13]`'ü "12 ay önce" sayıyordu; seride tek bir eksik/fazla ay
  varsa o varsayım bozulur ve enflasyon SESSİZCE yanlış pencereden hesaplanır.
"""

from __future__ import annotations

import pytest

from src import macro


def _kod(cfg: dict, mantiksal: str) -> str:
    return cfg["sources"]["evds"]["series"][mantiksal]


def _ekle(con, cfg, mantiksal: str, kayitlar: list[tuple[str, float | None]]) -> None:
    con.executemany(
        "INSERT OR REPLACE INTO evds_daily (date, series_code, value) VALUES (?,?,?)",
        [(d, _kod(cfg, mantiksal), v) for d, v in kayitlar])
    con.commit()


def _aylik(bas_yil: int, bas_ay: int, degerler: list[float]) -> list[tuple[str, float]]:
    out = []
    y, m = bas_yil, bas_ay
    for v in degerler:
        out.append((f"{y:04d}-{m:02d}-01", v))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


# ============================================================ eksik veri
class TestEksikVeriUydurulmaz:
    def test_bos_veritabaninda_bos_sozluk(self, cfg, con):
        assert macro.context(cfg, con) == {}

    def test_olmayan_anahtar_None_OLARAK_BILE_KONMAZ(self, cfg, con):
        """`ctx.get('politika_faizi')` ile yokluk görülür.

        Anahtarı `None` ile koymak, rapor tarafında "veri var ama boş" ile
        "veri yok"u ayırt edilemez hale getirir ve biçimlendirme `None`'ı "0.00"
        diye basma riskine girer.
        """
        _ekle(con, cfg, "aofm_politika", [("2026-07-25", 45.0)])
        ctx = macro.context(cfg, con, "2026-07-27")
        assert ctx["politika_faizi"] == 45.0
        for yok in ("tufe_yoy", "enf_bek_12ay", "mevduat_1yil_net", "usdtry",
                    "reel_net_mevduat"):
            assert yok not in ctx, f"{yok} anahtarı eklenmiş (değeri: {ctx.get(yok)!r})"

    def test_null_deger_veri_SAYILMAZ(self, cfg, con):
        _ekle(con, cfg, "aofm_politika", [("2026-07-25", None)])
        assert "politika_faizi" not in macro.context(cfg, con, "2026-07-27")

    def test_null_pct_tamamen_eksikte_100(self, cfg):
        assert macro.null_pct(cfg, {}) == pytest.approx(100.0)

    def test_null_pct_tam_veride_0(self, cfg, con):
        # ⚠ Günlük seriler asof'a YAKIN: 2026-08-11'den beri bayat gözlem
        # ctx'e hiç girmiyor ve `null_pct` onu doğal olarak eksik sayıyor.
        _ekle(con, cfg, "aofm_politika", [("2025-01-30", 45.0)])
        _ekle(con, cfg, "enf_bek_12ay", [("2025-01-01", 25.0)])
        _ekle(con, cfg, "mevduat_1yil", [("2025-01-01", 40.0)])
        _ekle(con, cfg, "usdtry_sell", [("2025-01-30", 35.0)])
        _ekle(con, cfg, "tufe", _aylik(2024, 1, [100.0 + 5 * i for i in range(13)]))
        ctx = macro.context(cfg, con, "2025-01-31")
        assert macro.null_pct(cfg, ctx) == pytest.approx(0.0)

    def test_null_pct_kismi_eksikte_ARADA(self, cfg, con):
        _ekle(con, cfg, "aofm_politika", [("2025-01-30", 45.0)])
        ctx = macro.context(cfg, con, "2025-01-31")
        oran = macro.null_pct(cfg, ctx)
        assert 0.0 < oran < 100.0


# ============================================================ Fisher
class TestReelFaiz:
    def test_FISHER_ile_hesaplanir_cikarma_DEGIL(self, cfg, con):
        """(1+i)/(1+π) − 1 ≠ i − π. Yüksek enflasyonda fark büyüktür."""
        _ekle(con, cfg, "mevduat_1yil", [("2025-01-01", 40.0)])
        _ekle(con, cfg, "enf_bek_12ay", [("2025-01-01", 30.0)])
        ctx = macro.context(cfg, con, "2025-01-31")

        stopaj = float(cfg["sources"]["evds"]["mevduat_stopaj_pct"])
        net = 40.0 * (1 - stopaj / 100.0)
        fisher = ((1 + net / 100) / (1 + 30.0 / 100) - 1) * 100

        assert ctx["mevduat_1yil_brut"] == 40.0
        assert ctx["mevduat_1yil_net"] == pytest.approx(net)
        assert ctx["reel_net_mevduat"] == pytest.approx(fisher)
        assert ctx["reel_net_mevduat"] != pytest.approx(net - 30.0), (
            "çıkarma ile hesaplanmış görünüyor")

    def test_stopaj_uygulanir(self, cfg, con):
        _ekle(con, cfg, "mevduat_1yil", [("2025-01-01", 50.0)])
        ctx = macro.context(cfg, con, "2025-01-31")
        assert ctx["mevduat_1yil_net"] < ctx["mevduat_1yil_brut"]

    def test_enflasyon_beklentisi_YOKSA_tufe_yoy_kullanilir(self, cfg, con):
        """Beklenti serisi eksikse gerçekleşen enflasyona düşülür — ama UYDURULMAZ."""
        _ekle(con, cfg, "mevduat_1yil", [("2025-01-01", 40.0)])
        _ekle(con, cfg, "tufe", _aylik(2024, 1, [100.0 * (1.02 ** i) for i in range(13)]))
        ctx = macro.context(cfg, con, "2025-01-31")
        assert "enf_bek_12ay" not in ctx
        assert "reel_net_mevduat" in ctx
        beklenen = ((1 + ctx["mevduat_1yil_net"] / 100)
                    / (1 + ctx["tufe_yoy"] / 100) - 1) * 100
        assert ctx["reel_net_mevduat"] == pytest.approx(beklenen)

    def test_enflasyon_hic_yoksa_reel_faiz_HESAPLANMAZ(self, cfg, con):
        _ekle(con, cfg, "mevduat_1yil", [("2025-01-01", 40.0)])
        ctx = macro.context(cfg, con, "2025-01-31")
        assert "mevduat_1yil_net" in ctx
        assert "reel_net_mevduat" not in ctx


# ============================================================ TÜFE YoY
class TestTufeYoY:
    def test_pencere_TARIHE_gore_kurulur(self, cfg, con):
        """Seride FAZLA bir gözlem varsa `rows[-13]` yanlış aya kayar.

        Kurulum: aylık seri + 2024-06'da ikinci bir gözlem. Doğru pencere
        2025-01 ↔ 2024-01 (tam 12 ay). `rows[-13]` ise 2024-02'yi gösterir ve
        enflasyonu düşük hesaplar.
        """
        kayitlar = _aylik(2024, 1, [100.0, 110.0, 120.0, 130.0, 140.0, 150.0,
                                    160.0, 170.0, 175.0, 180.0, 190.0, 195.0, 200.0])
        kayitlar.append(("2024-06-15", 155.0))          # FAZLA gözlem
        _ekle(con, cfg, "tufe", kayitlar)
        ctx = macro.context(cfg, con, "2025-01-31")
        assert ctx["tufe_yoy"] == pytest.approx(100.0), (
            "satır sayısına dayalı pencere kullanılıyor olabilir")
        assert ctx["tufe_tarih"] == "2025-01-01"

    def test_12_ay_oncesi_COK_UZAKSA_olculemez(self, cfg, con):
        """45 günden fazla sapma varsa YoY ölçülmez — yaklaşık pencere uydurmaktır."""
        kayitlar = [("2023-10-01", 100.0)] + _aylik(2024, 2, [110.0 + 5 * i
                                                              for i in range(12)])
        _ekle(con, cfg, "tufe", kayitlar)
        ctx = macro.context(cfg, con, "2025-01-31")
        assert "tufe_yoy" not in ctx

    def test_13_gozlemden_az_ise_olculemez(self, cfg, con):
        _ekle(con, cfg, "tufe", _aylik(2024, 1, [100.0 + i for i in range(12)]))
        assert "tufe_yoy" not in macro.context(cfg, con, "2025-01-31")

    def test_asof_GELECEGE_bakmaz(self, cfg, con):
        """`asof` sonrası gözlemler bağlama girmez."""
        _ekle(con, cfg, "aofm_politika",
              [("2025-06-25", 45.0), ("2026-06-25", 30.0)])
        assert macro.context(cfg, con, "2025-06-30")["politika_faizi"] == 45.0
        assert macro.context(cfg, con, "2026-06-30")["politika_faizi"] == 30.0

    def test_asof_verilmezse_EN_SON_gozlem(self, cfg, con):
        """`asof` yokken tazelik BUGÜNE göre ölçülür — o yüzden fixture
        bugüne görelidir. Sabit tarih yazmak testi takvimde bir gün
        sessizce kırmızıya döndürürdü."""
        from datetime import date, timedelta
        eski = (date.today() - timedelta(days=9)).isoformat()
        yeni = (date.today() - timedelta(days=1)).isoformat()
        _ekle(con, cfg, "aofm_politika", [(eski, 45.0), (yeni, 30.0)])
        assert macro.context(cfg, con)["politika_faizi"] == 30.0

    def test_29_subat_kenar_durumu(self, cfg, con):
        """`d.replace(year=y-1)` 29 Şubat'ta ValueError verir — 28'e düşülür."""
        kayitlar = ([(f"2023-{m:02d}-01", 100.0 + m) for m in range(1, 13)]
                    + [("2024-01-01", 113.0), ("2024-02-29", 120.0)])
        _ekle(con, cfg, "tufe", kayitlar)
        ctx = macro.context(cfg, con, "2024-03-01")
        assert "tufe_yoy" in ctx
        assert ctx["tufe_yoy"] > 0


# ============================================================ tazelik
class TestBayatSeriDegerUretmez:
    """⚠ REGRESYON KİLİDİ — 2026-08-11 denetiminin en sinsi bulgusu.

    NE OLMUŞTU: `TP.FE.OKTG01` (TÜFE endeksi) 2025-12-01'de sessizce durdu.
    `macro.context` en son gözlemi alıyor ve YAŞINA bakmıyordu; sonuç:
    **Aralık 2025 enflasyonu, 2026-08-05 paketinde `tufe_yoy = 30.89` olarak,
    güncelmiş gibi** analiste gitti. Üstelik `makro_eksik_pct` 0.0 diyordu —
    çünkü o sayı VARLIĞA bakıyordu, tazeliğe değil. Donmuş bir seri ile taze
    bir seri hiçbir yerde ayırt edilemiyordu.

    Modülün kendi kuralı zaten cevabı söylüyordu: *"veri yoksa anahtar HİÇ
    EKLENMEZ — uydurulmuş vekil değer konulmaz."* Sekiz aylık bir TÜFE,
    bugünün TÜFE'si için uydurulmuş bir vekildir.
    """

    def test_bayat_gunluk_seri_ctx_e_GIRMEZ(self, cfg, con):
        _ekle(con, cfg, "aofm_politika", [("2025-01-01", 45.0)])
        ctx = macro.context(cfg, con, "2025-03-01")      # 59 gün — tolerans 14
        assert "politika_faizi" not in ctx

    def test_taze_ayni_seri_ctx_e_GIRER(self, cfg, con):
        """Aynı veri, tolerans içinde bir asof ile: DEĞER GELİR.

        İki testin farkı yalnız `asof` — yani düşüren şey verinin yokluğu
        değil YAŞI. Bu ayrım olmadan "tazelik kontrolü çalışıyor" denemez.
        """
        _ekle(con, cfg, "aofm_politika", [("2025-01-01", 45.0)])
        assert macro.context(cfg, con, "2025-01-10")["politika_faizi"] == 45.0

    def test_bayat_TUFE_yoy_URETMEZ_ama_YASINI_SOYLER(self, cfg, con):
        """Sessizce düşmek de bir arıza olurdu: "TÜFE satırı neden yok?"
        sorusunun cevabı pakette durmalı."""
        _ekle(con, cfg, "tufe", _aylik(2024, 1, [100.0 + 5 * i for i in range(13)]))
        ctx = macro.context(cfg, con, "2025-08-01")      # son gözlem 2025-01-01
        assert "tufe_yoy" not in ctx
        assert ctx["tufe_bayat_tarih"] == "2025-01-01"

    def test_bayat_seri_null_pct_i_YUKSELTIR(self, cfg, con):
        """Düzeltme tek yerde (`context`) yapıldı; `null_pct` onu kendiliğinden
        eksik sayıyor. İki yerde saymak, ikisinin ayrışmasına davetiye olurdu."""
        _ekle(con, cfg, "aofm_politika", [("2025-01-01", 45.0)])
        taze = macro.null_pct(cfg, macro.context(cfg, con, "2025-01-10"))
        bayat = macro.null_pct(cfg, macro.context(cfg, con, "2025-06-01"))
        assert bayat > taze

    def test_bayat_seriler_RAPORLANIR(self, cfg, con):
        """`saglik` bunu basar. Sessiz bir düşüş, sessiz bir bayatlıktan iyi
        değildir — ikisi de görünmez."""
        _ekle(con, cfg, "aofm_politika", [("2025-01-01", 45.0)])
        bayat = macro.bayat_seriler(cfg, con, "2025-06-01")
        assert [b["ad"] for b in bayat] == ["aofm_politika"]
        assert bayat[0]["yas_gun"] == 151
        assert bayat[0]["tolerans"] == 14

    def test_hic_veri_YOKSA_bayat_SAYILMAZ(self, cfg, con):
        """"Hiç veri yok" ile "veri donmuş" ayrı iki olgu (L-003). Birincisini
        `null_pct` sayar, ikincisini bu liste."""
        assert macro.bayat_seriler(cfg, con, "2025-06-01") == []


# ============================================================ yazma yolu
class TestSeriEslemesi:
    def test_config_kodlari_okunur(self, cfg, con):
        """Seri kodu config'ten gelir; koda gömülmüş bir kod sessiz kırılmadır."""
        assert macro._series_map(cfg) == dict(cfg["sources"]["evds"]["series"])

    def test_bilinmeyen_seri_kodu_bos_doner(self, cfg, con):
        """Yanlış kodla yazılmış bir seri "0" değil "yok" olarak görünür."""
        con.execute("INSERT INTO evds_daily (date, series_code, value) "
                    "VALUES ('2025-01-01', 'YANLIS.KOD', 99.0)")
        con.commit()
        assert macro.context(cfg, con, "2025-01-31") == {}

    def test_beklenen_alanlar_null_pct_ile_TUTARLI(self, cfg, con):
        """`null_pct`'in beklediği alan listesi `context`'in ürettikleriyle uyumlu mu?

        Liste ayrışırsa eksiklik oranı yanlış hesaplanır ve rejimin defansif
        kayması yanlış tetiklenir (ya da hiç tetiklenmez).
        """
        _ekle(con, cfg, "aofm_politika", [("2025-01-30", 45.0)])
        _ekle(con, cfg, "enf_bek_12ay", [("2025-01-01", 25.0)])
        _ekle(con, cfg, "mevduat_1yil", [("2025-01-01", 40.0)])
        _ekle(con, cfg, "usdtry_sell", [("2025-01-30", 35.0)])
        _ekle(con, cfg, "tufe", _aylik(2024, 1, [100.0 + 5 * i for i in range(13)]))
        ctx = macro.context(cfg, con, "2025-01-31")
        beklenen = {"politika_faizi", "tufe_yoy", "enf_bek_12ay",
                    "mevduat_1yil_net", "usdtry", "reel_net_mevduat"}
        assert beklenen <= set(ctx), f"context üretmiyor: {beklenen - set(ctx)}"
