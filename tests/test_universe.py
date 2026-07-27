"""Evren testleri — İKİ EVREN ve `universe.yaml`'ın kendi kriterleri.

İki evren vardır ve karıştırılmamalıdır:

    CANLI  (`in_live`)     — sinyal üretilen isimler
    ÖLÇÜM  (`in_measure`)  — ağırlık kalibrasyonuna giren, ≥~8 yıl geçmişli isimler

Kısa geçmişli bir isim (ASTOR 878 bar, EUPWR 817 bar) canlı listede olabilir ama
ağırlık BELİRLEYEMEZ — 3 yıllık veriyle 10 yıllık parametre kalibre edilmez.
Bu ayrım kaybolursa hiçbir hata çıkmaz; yalnız backtest kısa geçmişli isimlerin
gürültüsüyle ağırlık kalibre etmeye başlar.

İkinci bölüm `universe.yaml`'ın KENDİ yazdığı seçim kriterlerini dosyaya karşı
sınar. Bir kriteri yazıp uygulamamak, "ölçülmüş" görünen bir listeyi elle
seçilmiş bir listeye çevirir — ve fark edilmez.
"""

from __future__ import annotations

from collections import Counter

import pytest

from src import universe, util
from src.sources import yf

TIER_KUMESI = {"cekirdek", "sanayi", "firsat", "yuksek_risk", "test_vakasi", "olcum"}


@pytest.fixture
def yaml_evren(real_cfg) -> dict:
    return universe.load_yaml_universe(real_cfg)


# ============================================================ senkron
class TestSync:
    def test_yaml_tablonun_TEK_GERCEK_KAYNAGI(self, cfg, con):
        r = universe.sync(cfg, con)
        yaml_ev = universe.load_yaml_universe(cfg)
        beklenen = {str(h["ticker"]).upper() for h in yaml_ev["hisseler"]}
        beklenen |= {str(t).upper() for liste in yaml_ev["olcum_evreni"].values()
                     for t in liste}
        tabloda = set(universe.all_tickers(con))
        assert tabloda == beklenen
        assert r["yazilan"] == len(beklenen)

    def test_yamldan_silinen_TABLODAN_da_silinir(self, cfg, con):
        """Aksi halde eski isim sessizce evrende kalır ve backtest ile canlı
        liste ayrışır — iki farklı evren üzerinde ölçüm yapılır."""
        universe.sync(cfg, con)
        con.execute("INSERT OR REPLACE INTO universe "
                    "(ticker,yf_symbol,name,sector,tier,in_live,in_measure) "
                    "VALUES ('HAYALET','HAYALET.IS',NULL,'x','olcum',1,1)")
        con.commit()
        assert "HAYALET" in universe.all_tickers(con)
        r = universe.sync(cfg, con)
        assert "HAYALET" in r["silinen"]
        assert "HAYALET" not in universe.all_tickers(con)

    def test_olcum_evreni_CANLI_SINYAL_URETMEZ(self, cfg, con):
        """`olcum_evreni` yalnız kesitsel dağılım içindir: in_live=0, in_measure=1."""
        universe.sync(cfg, con)
        yaml_ev = universe.load_yaml_universe(cfg)
        sadece_olcum = {str(t).upper() for liste in yaml_ev["olcum_evreni"].values()
                        for t in liste}
        canli = set(universe.live(con))
        olcum = set(universe.measure(con))
        assert not (sadece_olcum & canli), "ölçüm evreni canlı listeye sızdı"
        assert sadece_olcum <= olcum
        for t in sorted(sadece_olcum)[:3]:
            r = con.execute("SELECT tier, in_live, in_measure FROM universe "
                            "WHERE ticker = ?", (t,)).fetchone()
            assert (r["tier"], r["in_live"], r["in_measure"]) == ("olcum", 0, 1)

    def test_cakisan_isimde_CANLI_KAYIT_kazanir(self, cfg, con, monkeypatch):
        """Aynı isim iki listede olursa canlı tanımı (sektör/tier) korunur."""
        monkeypatch.setattr(universe, "load_yaml_universe", lambda c: {
            "hisseler": [{"ticker": "AAA", "sektor": "banka", "tier": "cekirdek",
                          "in_live": True, "in_measure": True}],
            "olcum_evreni": {"holding": ["AAA", "BBB"]}})
        universe.sync(cfg, con)
        r = con.execute("SELECT sector, tier, in_live FROM universe "
                        "WHERE ticker='AAA'").fetchone()
        assert (r["sector"], r["tier"], r["in_live"]) == ("banka", "cekirdek", 1)
        assert universe.all_tickers(con) == ["AAA", "BBB"]

    def test_ticker_BUYUK_HARFE_normalize(self, cfg, con, monkeypatch):
        monkeypatch.setattr(universe, "load_yaml_universe", lambda c: {
            "hisseler": [{"ticker": "thyao", "sektor": "ulasim", "tier": "cekirdek"}],
            "olcum_evreni": {"banka": ["isctr"]}})
        universe.sync(cfg, con)
        assert universe.all_tickers(con) == ["ISCTR", "THYAO"]

    def test_iki_kez_sync_cogaltmaz(self, cfg, con):
        universe.sync(cfg, con)
        n = len(universe.all_tickers(con))
        universe.sync(cfg, con)
        assert len(universe.all_tickers(con)) == n

    def test_bos_yaml_patlamaz(self, cfg, con, monkeypatch):
        monkeypatch.setattr(universe, "load_yaml_universe", lambda c: {})
        r = universe.sync(cfg, con)
        assert r["yazilan"] == 0


# ============================================================ sorgular
class TestSorgular:
    def test_siralama_deterministik(self, cfg, con):
        universe.sync(cfg, con)
        for fn in (universe.live, universe.measure, universe.all_tickers):
            liste = fn(con)
            assert liste == sorted(liste), f"{fn.__name__} sıralı değil"

    def test_all_tickers_canli_olmayanlari_da_kapsar(self, cfg, con):
        universe.sync(cfg, con)
        assert set(universe.live(con)) <= set(universe.all_tickers(con))
        assert set(universe.measure(con)) <= set(universe.all_tickers(con))
        assert len(universe.all_tickers(con)) > len(universe.live(con))

    def test_sektor_ve_tier_haritalari_tum_evreni_kapsar(self, cfg, con):
        universe.sync(cfg, con)
        tum = set(universe.all_tickers(con))
        assert set(universe.sector_map(con)) == tum
        assert set(universe.tier_map(con)) == tum
        assert all(v for v in universe.sector_map(con).values()), "sektör boş olamaz"

    def test_index_symbols_endeks_ve_KUR_birlikte(self, real_cfg):
        s = universe.index_symbols(real_cfg)
        y = real_cfg["sources"]["yf"]
        assert set(s) == set(y["endeksler"]) | set(y["kur"])
        assert "XU100" in s and "USDTRY" in s

    def test_takvim_kaynagi_endeks_listesinde(self, real_cfg):
        """İşlem takvimi bu endeksin barlarından TÜRETİLİR; çekilmiyorsa takvim
        yoktur ve zaman bariyeri hesabı sessizce tatil listesine düşer."""
        kaynak = real_cfg["takvim"]["turet_kaynak_endeks"]
        assert kaynak in universe.index_symbols(real_cfg)

    def test_yf_sembol_eki_idempotent(self, real_cfg):
        assert yf.yf_symbol("THYAO", real_cfg) == "THYAO.IS"
        assert yf.yf_symbol("THYAO.IS", real_cfg) == "THYAO.IS"
        assert yf.yf_symbol(" thyao ", real_cfg) == "THYAO.IS"


# ============================================================ universe.yaml
class TestYamlButunlugu:
    """`universe.yaml`'ın kendi yazdığı kriterler dosyaya UYGULANMIŞ mı?

    Kriterler dosyanın başında `seciim_kriterleri` altında yazılı. Yazıp
    uygulamamak, "ölçülmüş" görünen bir listeyi elle seçilmiş bir listeye
    çevirir — ve okuyan kimse farkı göremez.
    """

    def test_ticker_tekil_ve_buyuk_harf(self, yaml_evren):
        hisseler = [h["ticker"] for h in yaml_evren["hisseler"]]
        olcum = [t for liste in yaml_evren["olcum_evreni"].values() for t in liste]
        tekrar = [t for t, n in Counter(hisseler + olcum).items() if n > 1]
        assert not tekrar, f"tekrarlanan ticker: {tekrar}"
        for t in hisseler + olcum:
            assert t == t.upper() and t.isalpha(), t

    def test_zorunlu_alanlar_ve_tier(self, yaml_evren):
        for h in yaml_evren["hisseler"]:
            assert {"ticker", "sektor", "tier"} <= set(h), h
            assert h["tier"] in TIER_KUMESI, h
            assert h["sektor"] and h["sektor"] == h["sektor"].lower()

    def test_SEKTOR_TAVANI_uygulanmis(self, yaml_evren, real_cfg):
        """"sektör başına maksimum 2" — dosyanın kendi kriteri.

        Tavan, planlayıcıdaki `sektor_basi_maks_pozisyon` kısıtıyla da uyumlu
        olmalı: evrende bir sektörde 3 isim varken portföyde 2 ile sınırlamak
        kısıtı bağlayıcı ama evreni tutarsız bırakır.
        """
        tavan = int(real_cfg["rejim"]["sektor_basi_maks_pozisyon"])
        sayim = Counter(h["sektor"] for h in yaml_evren["hisseler"]
                        if h.get("in_live", True))
        asanlar = {s: n for s, n in sayim.items() if n > tavan}
        assert not asanlar, f"sektör tavanı ({tavan}) aşıldı: {asanlar}"

    def test_in_measure_MIN_GECMIS_kriterini_saglar(self, yaml_evren, real_cfg):
        """`in_measure=1` ⟹ ölçülen bar sayısı `evren.min_gecmis_gun_olcum` üstünde.

        Bu kural config'te yazılı ama kod onu OKUMUYOR — `in_measure` elle
        işaretleniyor. Dolayısıyla kuralı uygulayan tek şey bu testtir: kısa
        geçmişli bir ismi ölçüm evrenine almak burada patlar.
        """
        esik = int(real_cfg["evren"]["min_gecmis_gun_olcum"])
        for h in yaml_evren["hisseler"]:
            if not h.get("in_measure", True):
                continue
            bar = (h.get("olcum") or {}).get("bar")
            assert bar is not None, f"{h['ticker']}: ölçüm kaydı yok"
            assert bar >= esik, (
                f"{h['ticker']} in_measure=1 ama yalnız {bar} bar (< {esik}). "
                f"Kısa geçmişli isim AĞIRLIK BELİRLEYEMEZ.")

    def test_kisa_gecmisli_isimler_olcum_evreninde_DEGIL(self, yaml_evren, real_cfg):
        esik = int(real_cfg["evren"]["min_gecmis_gun_olcum"])
        kisa = [h["ticker"] for h in yaml_evren["hisseler"]
                if ((h.get("olcum") or {}).get("bar") or 0) < esik]
        assert kisa, "fixture anlamsızlaştı: kısa geçmişli hiç isim yok"
        for h in yaml_evren["hisseler"]:
            if h["ticker"] in kisa:
                assert not h.get("in_measure", True), h["ticker"]

    def test_CANLI_isimler_likidite_kriterini_saglar(self, yaml_evren, real_cfg):
        """Ölçülmüş medyan ciro, canlı evren eşiğinin üstünde olmalı."""
        esik_mn = float(real_cfg["evren"]["min_medyan_islem_hacmi_try"]) / 1e6
        for h in yaml_evren["hisseler"]:
            if not h.get("in_live", True):
                continue
            medyan = (h.get("olcum") or {}).get("medyan_tl_mn")
            assert medyan is not None, f"{h['ticker']}: ölçüm yok"
            assert medyan >= esik_mn, (
                f"{h['ticker']}: medyan {medyan}mn < {esik_mn:.0f}mn eşiği")

    def test_CANLI_isimler_sifir_hacim_kriterini_saglar(self, yaml_evren, real_cfg):
        """SASA vakası: %23.2 sıfır hacim → canlı evrende OLMAMALI."""
        esik_pct = float(real_cfg["evren"]["maks_sifir_hacim_orani"]) * 100
        for h in yaml_evren["hisseler"]:
            if not h.get("in_live", True):
                continue
            oran = (h.get("olcum") or {}).get("sifir_hacim_pct")
            assert oran is not None, f"{h['ticker']}: ölçüm yok"
            assert oran < esik_pct, (
                f"{h['ticker']}: sıfır hacim %{oran} ≥ %{esik_pct:.0f}")

    def test_test_vakasi_canli_DEGIL(self, yaml_evren):
        """`test_vakasi` tier'ı kapı testleri içindir; sinyal üretmemeli.

        SASA bilerek evrende tutuluyor: kalite kapısının GERÇEKTEN elediğini
        gösteren canlı fixture o. Ama canlı listeye girerse plan üretilir.
        """
        for h in yaml_evren["hisseler"]:
            if h["tier"] == "test_vakasi":
                assert not h.get("in_live", True), h["ticker"]

    def test_yuksek_risk_tier_i_olcum_evreninde_DEGIL(self, yaml_evren):
        """`yuksek_risk` = kısa geçmiş + yüksek vol → ağırlık belirleyemez."""
        for h in yaml_evren["hisseler"]:
            if h["tier"] == "yuksek_risk":
                assert not h.get("in_measure", True), h["ticker"]

    def test_olcum_evreni_sektore_gore_gruplu(self, yaml_evren):
        for sektor, liste in yaml_evren["olcum_evreni"].items():
            assert sektor == sektor.lower() and liste, sektor
            assert len(liste) == len(set(liste)), sektor

    def test_olcum_evreni_KESITSEL_DAGILIM_icin_yeterince_genis(self, yaml_evren):
        """Kesitsel z-skorun sıralayacak bir dağılımı olmalı.

        Ölçüm evreni daralırsa `pct` daha az isim üzerinden hesaplanır ve
        "birinci" olmak anlamını yitirir (L-007'nin ta kendisi).
        """
        toplam = (len(yaml_evren["hisseler"])
                  + sum(len(v) for v in yaml_evren["olcum_evreni"].values()))
        assert toplam >= 50, f"ölçüm evreni yalnız {toplam} isim"

    def test_survivorship_uyarisi_dosyada_YAZILI(self, real_cfg):
        """Düzeltilmeyen bir eğilim, en azından İFŞA EDİLMİŞ olmalı.

        Bu sabit bir listedir, nokta-zamanlı BIST-100 üyeliği değil. Uyarıyı
        dosyadan silmek, eğilimi gizlemek olur.
        """
        metin = util.resolve(real_cfg["paths"]["universe_file"]).read_text(
            encoding="utf-8")
        assert "SURVIVORSHIP" in metin.upper()
