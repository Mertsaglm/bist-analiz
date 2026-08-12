"""SÖZLEŞME TESTLERİ — bu dosya projenin zırhıdır.

Buradaki testler bir davranışı değil, **projenin kendisi hakkındaki iddialarını**
sabitler. Amaç tek bir cümleyle: *bu projeye sonradan dokunan herkes — insan ya
da model — bir savunmayı sessizce kaldıramasın.*

Neden ayrı bir dosya: normal testler "kod doğru çalışıyor mu" diye sorar.
Bunlar "kodun VARSAYDIĞI yapı hâlâ ayakta mı" diye sorar. 2026-07-27 denetiminin
gösterdiği gibi bu projenin en pahalı hata sınıfı mantık hatası değil, **doğru
görünen ama karşılığı olmayan yapı**: `schema.py` beş sabit tanımlıyordu, hiçbir
yerden okunmuyorlardı (HF-31 yoktu); `regime.store` yazılmıştı, hiç
çağrılmıyordu (tablo boştu); `measure_level_edge` vardı, hiçbir komut onu
koşmuyordu. Hepsi "belgelenmiş ama var olmayan savunma"ydı.

Dört sınıf iddia test edilir:

1. **Kolon listesi ↔ şema.** Koddaki `*_COLS` listeleri tablo kolonlarıyla
   BİREBİR. Bu ikisi ayrışırsa yazma sessizce yanlış kolona düşer.
2. **LLM sınırı yapısal olarak kapalı.** Şema kümeleri, journal'ın kabul ettiği
   alanlar ve prompt'a konan iskelet birbirinden ayrışamaz.
3. **Eşikler GEVŞETİLEMEZ.** Dürüstlük eşikleri (zayıf N, min fark, maliyet,
   prose uzunluğu) yalnız SIKILAŞTIRILABİLİR; gevşetmek ön kayıt ister.
4. **Katman disiplini.** Saf modüller iş mantığı bilmez; resolver LLM katmanını
   tanımaz; kimse CLI'ı import etmez.
"""

from __future__ import annotations

import ast
import itertools
import re
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from src import (audit, backtest, cli, db, dbdump, evaluate, factors, indicators,
                 journal, llm_io, migrations, news, planner, prices, regime,
                 resolver, schema, stats, util)

from tests.conftest import bar_serisi

SRC = Path(util.ROOT) / "src"


def _kolonlar(con: sqlite3.Connection, tablo: str) -> list[str]:
    return [r[1] for r in con.execute(f"PRAGMA table_info({tablo})")]


# ============================================================ 1. kolon ↔ şema
KOLON_SOZLESMESI = [
    ("bars_daily", prices.BAR_COLS),
    ("indicator_daily", indicators.INDICATOR_COLS),
    ("factor_daily", factors.FACTOR_COLS),
    ("predictions", journal.PREDICTION_COLS),
    ("outcomes", resolver.OUTCOME_COLS),
    ("disclosures", news.DISC_COLS),
    ("llm_runs", journal.LLM_RUN_COLS),
]


class TestKolonSozlesmesi:
    """Koddaki kolon listeleri ↔ `db.SCHEMA` — BİREBİR ve AYNI SIRADA.

    Bu testin varlık sebebi `upsert_many`'nin çalışma biçimi: kolon adlarını ve
    değerleri AYRI listeler olarak alır ve pozisyona göre eşler. Şemaya bir
    kolon eklenip koddaki listeye eklenmezse (ya da tersi) yazma ya patlar ya
    da — daha kötüsü — değerler bir kolon kayarak sessizce yanlış yere düşer.
    Bir gösterge değerinin `atr14` yerine `atr_pct` kolonuna yazılması hiçbir
    hata fırlatmaz ve her ölçümü bozar.
    """

    @pytest.mark.parametrize("tablo,kod", KOLON_SOZLESMESI,
                             ids=[t for t, _ in KOLON_SOZLESMESI])
    def test_liste_semayla_ayni_ve_sirali(self, con, tablo, kod):
        assert _kolonlar(con, tablo) == list(kod), (
            f"`{tablo}` şeması ile koddaki liste ayrıştı. Kolon eklerken/"
            f"kaldırırken İKİSİNİ birlikte güncelle.")

    def test_indicator_cols_dilimleme_sozlesmesi(self, cfg):
        """`compute_and_store` `INDICATOR_COLS[3:-1]` diye DİLİMLİYOR.

        Yani listenin ilk üçü ve sonu POZİSYONEL bir sözleşmedir; aradaki her
        ad `enrich()` çıktısında gerçek bir kolon olmak zorundadır. Bir gösterge
        adını listeye ekleyip `enrich`'e eklememek `AttributeError` verir, ama
        SIRAYI bozmak sessizce yanlış kolona yazar.
        """
        assert indicators.INDICATOR_COLS[:3] == ["ticker", "date", "set_version"]
        assert indicators.INDICATOR_COLS[-1] == "computed_utc"

        df = pd.DataFrame(bar_serisi(300, gunluk_egim=0.001, dalga=2.0),
                          columns=["date", "o", "h", "l", "c", "v", "c_tr"])
        df["turnover_try"] = df["c"] * df["v"]
        uretilen = set(indicators.enrich(df, cfg).columns)
        eksik = [k for k in indicators.INDICATOR_COLS[3:-1] if k not in uretilen]
        assert not eksik, f"`enrich` bu kolonları üretmiyor: {eksik}"

    def test_factor_cols_faktor_adlarindan_turetilir(self):
        """Faktör eklemek ÜÇ yeri birlikte değiştirmeyi gerektirir.

        `FACTOR_COLS` = kimlik + ham faktörler + z'leri + skor bloğu. Bir faktör
        eklenip listenin şekli bozulursa `factors.store` yanlış kolona yazar.
        """
        beklenen = (["ticker", "date", "set_version", "weights_hash"]
                    + factors.FACTOR_NAMES
                    + [f"z_{f}" for f in factors.FACTOR_NAMES]
                    + ["score", "rank", "pct", "eligible", "gate_reasons"])
        assert list(factors.FACTOR_COLS) == beklenen

    def test_her_faktorun_backtest_karsiligi_var(self, cfg, con):
        """`FACTOR_NAMES`'e faktör eklemek `build_features`'a da eklemeyi gerektirir.

        `score_at` `feat[ad]` diye okur: eksik faktör KeyError'dır — ama yalnız
        ölçüm koşulduğunda, yani aylar sonra. Burada anında patlar.
        """
        from tests.conftest import add_bars, add_index, add_universe
        tarihler = [r[0] for r in bar_serisi(30)]
        add_universe(con, "AAA")
        add_bars(con, "AAA", bar_serisi(30))
        add_index(con, "XU100", tarihler)
        feat = backtest.build_features(backtest.load_panel(con, ["AAA"]), cfg)
        eksik = [a for a in factors.FACTOR_NAMES if a not in feat]
        assert not eksik, f"`build_features` bu faktörleri üretmiyor: {eksik}"

    def test_dbdump_atladigi_tablolar_gercekten_var(self, con):
        """Var olmayan bir tabloyu "atlamak" sessiz bir yazım hatasıdır.

        `ATLA` yalnız TÜREV tabloları içerebilir: yeniden üretilemeyen bir
        tabloyu dump'tan düşürmek veri kaybıdır.
        """
        mevcut = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        assert dbdump.ATLA <= mevcut, (
            f"`dbdump.ATLA` var olmayan tablo içeriyor: {dbdump.ATLA - mevcut}")
        # Türev olmayan bir tablo asla atlanamaz.
        korunmasi_gerekenler = {"predictions", "outcomes", "llm_runs", "bars_daily",
                                "plan_options", "universe", "disclosures",
                                "corporate_actions", "index_daily", "holdings"}
        assert not (dbdump.ATLA & korunmasi_gerekenler)


# ============================================================ 2. LLM sınırı
class TestLLMSinirininYapisi:
    """Şema kümeleri, journal ve prompt iskeleti AYRIŞAMAZ.

    HF-31 bu kümeleri ZORLUYOR. Yani kümelerden biri kaydığında sonuç bir
    "şema hatası" değil, denetimin YANLIŞ ŞEYİ reddetmesi olur: modelin kendi
    prompt'unda gördüğü iskelet, denetimin yasakladığı bir alanı içerebilir ve
    her çıktı reddedilir. Ya da tersi: journal kabul ettiği bir alanı denetim
    görmez ve sızıntı açılır.
    """

    def test_yasak_sayisal_alan_ile_izinli_alan_kesismez(self):
        assert not (schema.YASAK_SAYISAL_ALANLAR & schema.STOCK_ALANLARI), (
            "Bir alan hem izinli hem yasak olamaz — HF-31 kendi kendisiyle çelişir.")

    def test_zorunlu_ve_prose_alanlari_izinli_kumede(self):
        assert schema.STOCK_ZORUNLU <= schema.STOCK_ALANLARI
        assert set(schema.STOCK_PROSE) <= schema.STOCK_ALANLARI

    def test_journalin_kabul_ettigi_alanlar_semadan_genis_DEGIL(self):
        """Journal, denetimin görmediği bir alanı kabul edemez.

        Aksi halde model şemayı genişletir, HF-31 görmez, `journal.record` kabul
        eder ve sızıntı fark edilmeden veritabanına girer.
        """
        assert journal.ANALIST_ALANLARI <= schema.STOCK_ALANLARI

    def test_prompt_iskeleti_kendi_semasina_uyar(self):
        """Prompt'a konan örnek iskelet HF-31'i TETİKLEMEMELİ.

        Model iskeleti birebir doldurursa çıktı geçerli olmalı. İskelet ile
        şema kümesi ayrışırsa model kendi prompt'una uyarak denetimi patlatır —
        ve suçlanacak yer kod değil, kullanıcı olur.
        """
        isk = schema.output_iskelet("2026-07-27", "sha123", "claude-code")
        assert set(isk) <= schema.TOP_ALANLARI
        assert set(isk["market_view"]) <= schema.MARKET_ALANLARI
        assert set(isk["stocks"][0]) <= schema.STOCK_ALANLARI
        assert schema.STOCK_ZORUNLU <= set(isk["stocks"][0])

    def test_iskelette_HIC_SAYI_YOK(self):
        """İskelet bir sayı önerirse model sayı üretmeyi meşru sanar.

        Bu dosyanın tek cümlesi "LLM hesaplanabilir hiçbir sayıyı üretmez";
        örnek şablonun kendisi bunu ihlal edemez.
        """
        def gez(o, yol="kok"):
            if isinstance(o, bool):
                return
            assert not isinstance(o, (int, float)), f"iskelette sayı var: {yol}={o!r}"
            if isinstance(o, dict):
                for k, v in o.items():
                    gez(v, f"{yol}.{k}")
            elif isinstance(o, (list, tuple)):
                for i, v in enumerate(o):
                    gez(v, f"{yol}[{i}]")

        gez(schema.output_iskelet("2026-07-27", "sha", "claude-code"))

    def test_confidence_p_analistin_yazabilecegi_alan_DEGIL(self):
        """Sayısal güveni KOD yazar. Bu, journal.py'nin ana iddiası.

        Kalibre edilmemiş bir olasılığı LLM'den almak, onu ölçüm zincirine
        sokmak demektir (Brier, güvenilirlik eğrisi hepsi buna dayanır).
        """
        assert "confidence_p" not in journal.ANALIST_ALANLARI
        assert "confidence_p" not in schema.STOCK_ALANLARI
        assert "confidence_p" in journal.PREDICTION_COLS
        for kod_alani in ("score", "rank", "pct", "weights_hash", "plan_id"):
            assert kod_alani not in journal.ANALIST_ALANLARI

    def test_outcomes_tablosunda_analist_alani_YOK(self):
        """Kendi ödevini notlandıran sistem kayar — `outcomes` KOD tablosudur."""
        assert not (set(resolver.OUTCOME_COLS) & journal.ANALIST_ALANLARI)
        assert not (set(resolver.OUTCOME_COLS) & schema.STOCK_ALANLARI)

    def test_kod_sabitleri_config_ile_ayni(self, real_cfg):
        """Sürüm dizeleri iki yerde yazılı; ayrışırlarsa HF-01 sahte alarm verir."""
        assert schema.OUTPUT_SCHEMA_VERSION == real_cfg["llm"]["output_schema_version"]
        assert schema.BUNDLE_VERSION == real_cfg["llm"]["bundle_version"]

    def test_guven_haritasi_enumu_TAM_kapsar(self, real_cfg):
        """Yeni bir güven seviyesi eklenip haritaya eklenmezse `confidence_to_p` patlar.

        Ve patladığı yer `bist kaydet`in ortası olur: denetim geçmiş, plan
        saklanmış, journal yazılırken hata. Burada anında görünür.
        """
        assert (set(real_cfg["llm"]["guven_olasilik"])
                == set(real_cfg["llm"]["enums"]["confidence"]))
        for v in real_cfg["llm"]["guven_olasilik"].values():
            assert 0.0 < float(v) < 1.0

    def test_signal_ordinal_enumu_TAM_kapsar(self, real_cfg):
        """`evaluate.SIGNAL_ORDINAL` eksik kalırsa LLM katkısı SESSİZCE yanlış ölçülür.

        `.get(signal, 3)` varsayılanı "hold" demek: yeni bir sinyal eklenip
        haritaya girmezse o karar nötr sayılır ve sıra korelasyonu bozulur —
        hata fırlatmadan.
        """
        assert (set(evaluate.SIGNAL_ORDINAL)
                == set(real_cfg["llm"]["enums"]["signal"]))
        # Sıralama boğa→ayı monoton olmalı; aksi halde IC'nin işareti anlamsızlaşır.
        sirali = [evaluate.SIGNAL_ORDINAL[s] for s in real_cfg["llm"]["enums"]["signal"]]
        assert sirali == sorted(sirali, reverse=True), (
            "config'teki sinyal listesi boğadan ayıya sıralı olmalı ve "
            "SIGNAL_ORDINAL bununla tutarlı olmalı")

    def test_desteklenmeyen_tetikleyici_izinli_listede_DURAMAZ(self):
        """`breakout_above_resistance` KALDIRILDI ve geri gelmemeli.

        `resolver.entry_fill` doluma DAİMA aşağıdan bakar (`l <= entry_high`).
        Bir kırılım tetikleyicisi listede dururken biri onu üretirse plan
        SESSİZCE ters yönde doldurulur. Desteklenmeyen bir değeri "izinli"
        listesinde tutmak, onu kullanacak kişiye kurulmuş bir tuzaktır.
        """
        assert "breakout_above_resistance" not in planner.ENTRY_TRIGGERS
        for t in planner.ENTRY_TRIGGERS:
            assert "breakout" not in t and "kirilim" not in t


# ============================================================ 3. eşik zemini
class TestEsiklerGevsetilemez:
    """Dürüstlük eşikleri yalnız SIKILAŞTIRILABİLİR.

    ⚠ Bu testler "config'e dokunma" demiyor — "sonucu görüp eşiği gevşetme"
    diyor. Projenin kuralı yazılı: *eşiği sonucu görüp gevşetmek yasak*
    (`docs/on-kayit-revizyon-01.md` §5). Bir eşiği gevşetmek isteyen kişi bu
    testi de değiştirmek zorunda kalır — yani kararı GÖRÜNÜR olur, sessiz bir
    config düzenlemesi olarak geçmez.
    """

    def test_zayif_n_esigi_dusurulemez(self, real_cfg):
        assert int(real_cfg["olcum"]["zayif_n_esigi"]) >= 15, (
            "Zayıf N eşiğini düşürmek, az gözlemle hüküm vermeye izin verir — "
            "`edge_verdict`in bütün varlık sebebi buna engel olmaktı.")

    def test_min_anlamli_fark_dusurulemez(self, real_cfg):
        assert float(real_cfg["olcum"]["min_anlamli_fark_puan"]) >= 1.0, (
            "Revizyon turunun çıtası |Δ|≥1.0pp'ydi ve tur GEÇMEDİ. Çıtayı "
            "sonradan düşürmek o kararı geçmişe dönük tersine çevirmektir.")

    def test_maliyet_dusurulemez(self, real_cfg):
        assert float(real_cfg["risk"]["islem_maliyeti_gidis_donus_pct"]) >= 0.30, (
            "Maliyet ölçülmüş bir sayıdır (komisyon + BSMV + spread) ve kenarın "
            "~1/3'ünü yiyor. Düşürmek her ölçümü iyimser yapar.")

    def test_prose_ve_yuzdelik_esikleri_dusurulemez(self, real_cfg):
        assert int(real_cfg["llm"]["min_prose_karakter"]) >= 80
        assert float(real_cfg["llm"]["strong_buy_min_yuzdelik"]) >= 70.0, (
            "HF-22 LLM'in sıralamayı ezmesini engeller; bandı indirmek "
            "kontrolü işlevsizleştirir.")

    def test_denetim_beyaz_listesi_genisletilemez(self, real_cfg):
        """Beyaz listeyi genişletmek HF-17'yi GEÇİRGENLEŞTİRİR.

        Ölçüldü: 0-31 tamsayı listesiyle bile −50..+50 aralığının %56'sı
        izinli. Tavanı yükseltmek bu oranı sessizce büyütür.
        """
        d = real_cfg["denetim"]
        assert int(d["sayisal_beyaz_liste_tamsayi_maks"]) <= 31
        assert int(d["ondalik_tolerans_basamak"]) == 2, (
            "Tolerans basamağını artırmak, uydurma sayıların yuvarlanarak "
            "izinli hale gelmesine kapı açar (bkz. `_varyantlar` uyarısı).")
        assert len(d["ek_izinli_sayilar"]) <= 12

    def test_pozisyon_riski_ve_tavan_makul_bantta(self, real_cfg):
        r = real_cfg["risk"]
        assert 0 < float(r["pozisyon_basi_risk_pct"]) <= 2.0
        assert 0 < float(r["maks_pozisyon_pct"]) <= 25.0
        assert float(r["gunluk_fiyat_limiti_pct"]) == 10.0, (
            "BIST günlük marjı ±%10'dur; bu bir tercih değil, piyasa kuralı.")

    def test_plan_kurallari_gevsetilemez(self, real_cfg):
        p = real_cfg["planlayici"]
        alt, ust = p["stop_atr_bandi"]
        assert 0 < float(alt) < float(ust) <= 5.0
        assert float(p["min_rr_t1"]) >= 1.5, (
            "R:R çıtası ADR #009'da ifşa edildi ve DEĞİŞTİRİLMEDİ; değiştirmek "
            "`docs/on-kayit-seviye-02.md` ön kaydının koşulmasını gerektirir.")
        assert int(p["maks_plan_per_hisse"]) <= 5
        assert float(p["maks_giris_uzakligi_atr"]) <= 4.0, (
            "EUPWR vakası: uzak seviye tetiklenemez bir R:R artefaktı üretti.")

        # --- hedef mesafe zemini (ADR #018) ---------------------------------
        # Zemin eşiği DEĞİŞTİRMEYİ YASAKLAMAZ, GÖRÜNÜR kılar: değiştiren kişi
        # bu testi de değiştirmek zorunda kalır, yani karar sessiz bir config
        # düzenlemesi olarak geçemez (AGENTS §12.1).
        mh = float(p["min_hedef_uzakligi_atr"])
        assert mh >= float(alt) / 1.5, (
            "hedef zemini stop tabanının mantığının altına düştü — eşik oradan "
            "türetildi: günlük salınımın içindeki bir bariyer gürültüyle "
            "tetiklenir ve bu hedef için de geçerlidir (ADR #018).")
        # Üst sınır: en DAR stop (alt×ATR) ile bile R:R'ı otomatik geçirmemeli,
        # yoksa `min_rr_t1` dekoratif bir kapıya döner.
        assert mh < float(alt) * float(p["min_rr_t1"]), (
            f"min_hedef_uzakligi_atr {mh} ≥ {alt}×{p['min_rr_t1']} — bu eşikte "
            "R:R kapısı kendiliğinden sağlanır ve hiçbir şey elemez.")

    def test_kalite_kapilari_gevsetilemez(self, real_cfg):
        ev = real_cfg["evren"]
        assert float(ev["maks_sifir_hacim_orani"]) <= 0.05, (
            "SASA profili (%23.2 sıfır hacim) elenmeye devam etmeli.")
        assert int(ev["maks_bar_bosluk_gun"]) <= 10
        assert int(ev["maks_bayat_kapanis_gun"]) <= 5
        assert float(ev["min_medyan_islem_hacmi_try"]) >= 100_000_000

    def test_look_ahead_korumasi_kapatilamaz(self, real_cfg):
        """`pivot_k` 0 olursa fraktal pivot ANINDA bilinir hale gelir — sızıntı."""
        assert int(real_cfg["seviyeler"]["pivot_k"]) >= 1
        assert int(real_cfg["seviyeler"]["min_dokunus"]) >= 2, (
            "Tek dokunuşlu bir 'seviye' seviye değildir; ortalama tek pivotun "
            "kendisi olur ve hedef uydurmaya dönüşür.")
        assert int(real_cfg["gostergeler"]["min_bar_hesap_icin"]) >= 200


# ============================================================ 4. hüküm dili
class TestDogrulandiDaliYOK:
    """Sistemin verebileceği EN GÜÇLÜ hüküm "zayıf kanıt"tır.

    Bu bir eksiklik değil tasarım kararı: sistemin kendi hakkında abartılı
    konuşmasını YAPISAL olarak imkânsız kılar. Fuzz ile sabitlenir — tek bir
    örnek test, `edge_verdict`e eklenen yeni bir dalı kaçırabilir.
    """

    YASAK = ("doğrulandı", "dogrulandi", "kanıtlandı", "kanitlandi", "onaylandı",
             "kesin", "garanti", "güçlü kanıt", "guclu kanit")

    def test_edge_verdict_fuzz(self):
        for diff, n in itertools.product(
                [None, 0.0, 0.5, 1.0, -1.0, 5.0, -5.0, 100.0, -100.0, 1e9],
                [0, 1, 14, 15, 16, 1000]):
            h = stats.edge_verdict(diff, n, 15, 1.0).lower()
            assert not any(y in h for y in self.YASAK), (diff, n, h)

    def test_ic_verdict_fuzz(self):
        for ic, n, t in itertools.product(
                [None, 0.0, 0.05, -0.05, 0.9, -0.9],
                [0, 14, 15, 500], [None, 0.0, 1.9, 2.0, -3.0, 50.0]):
            h = stats.ic_verdict(ic, n, t, 15).lower()
            assert not any(y in h for y in self.YASAK), (ic, n, t, h)

    def test_hukum_sabitleri_iddia_ETMEZ(self):
        sabitler = [v for k, v in vars(stats).items()
                    if k.startswith("HUKUM_") and isinstance(v, str)]
        assert sabitler, "hüküm sabitleri kayboldu"
        for s in sabitler:
            assert not any(y in s.lower() for y in self.YASAK), s

    def test_devasa_fark_bile_zayif_N_ile_yetersiz(self):
        """ZAYIF N, BÜYÜK FARKI EZER — sıralama tersine çevrilemez."""
        assert stats.HUKUM_YETERSIZ in stats.edge_verdict(999.0, 3, 15, 1.0)
        assert stats.HUKUM_YETERSIZ in stats.ic_verdict(0.95, 3, 99.0, 15)


# ============================================================ 5. denetim kapsamı
class TestDenetimKapsami:
    def test_kod_listesi_kesintisiz(self):
        kodlar = audit.all_codes()
        assert kodlar == sorted(kodlar)
        sayilar = [int(k.split("-")[1]) for k in kodlar]
        assert sayilar == list(range(1, max(sayilar) + 1)), "HF numaralarında boşluk var"
        assert len(kodlar) >= 31, "sert kontrol sayısı AZALTILAMAZ"

    def test_audit_yalniz_BILINEN_kod_uretir(self, cfg, con):
        """Denetim, `all_codes()` dışında bir kod üretemez.

        Aksi halde `format_report` "N sert kontrolün hiçbiri patlamadı" derken
        listede olmayan bir kontrolü sayamaz ve `test_her_HF_kodu_...` kapsam
        testi o kodu hiç görmez — belgelenmemiş bir kontrol doğar.
        """
        bilinen = set(audit.all_codes())
        bundle = {"asof": "2026-07-27", "bundle_sha": "x", "evren": [],
                  "izin_verilen_degerler": {"plan_ids": {}}, "rejim": {}}
        bozuk_ciktilar = [
            {},
            {"schema_version": "yanlis", "stocks": [{"ticker": "YOK"}]},
            {"stocks": [{"ticker": "A", "signal": 5, "action": None,
                         "confidence": 0.9, "entry": 12.5}]},
            {"market_view": {"regime_agreement": "belki"}, "stocks": []},
            {"stocks": [], "not_covered": ["A", "B"], "fazla_alan": 1},
        ]
        for out in bozuk_ciktilar:
            for f in audit.audit(cfg, bundle, out, con):
                assert f.code in bilinen or f.code.startswith("W-"), f.code
                assert f.severity in (audit.SERT, audit.UYARI)

    def test_temiz_rapor_HF17_SINIRINI_ITIRAF_EDER(self):
        """"Denetim temiz" cümlesi, denetimin ölçülmüş boşluğunu da yazmalı.

        Gizlenen bir sınır, olmayan bir garantiye dönüşür: HF-17 iki ondalıklı
        uydurma fiyatları yakalıyor ama küçük tamsayılara ve yuvarlak yüzdelere
        GEÇİRGEN (ölçüldü 2026-07-27). Kullanıcı "temiz" gördüğünde bunu da
        görmeli.
        """
        metin = audit.format_report([])
        assert "HF-17" in metin
        assert "GEÇİRGEN" in metin.upper() or "geçirgen" in metin

    def test_hard_fails_yalniz_sert_hatalari_suzer(self):
        bulgular = [audit.Finding("HF-01", audit.SERT, None, "x"),
                    audit.Finding("W-01", audit.UYARI, None, "y")]
        assert [f.code for f in audit.hard_fails(bulgular)] == ["HF-01"]

    def test_uyari_kodlari_journal_i_ENGELLEMEZ(self):
        """Tasarım kararı: `W-xx` rapora girer, yazmayı durdurmaz."""
        sadece_uyari = [audit.Finding("W-02", audit.UYARI, "A", "z")]
        assert audit.hard_fails(sadece_uyari) == []


# ============================================================ 6. katman disiplini
def _import_edilen_yerel_moduller(dosya: Path) -> set[str]:
    """Bir dosyanın import ettiği PROJE İÇİ modül adları (göreli import'lar)."""
    agac = ast.parse(dosya.read_text(encoding="utf-8"))
    out: set[str] = set()
    for d in ast.walk(agac):
        if isinstance(d, ast.ImportFrom) and (d.level or 0) > 0:
            if d.module:
                out.add(d.module.split(".")[0])
            for a in d.names:
                out.add(a.name.split(".")[0])
        elif isinstance(d, ast.Import):
            for a in d.names:
                if a.name.startswith("src."):
                    out.add(a.name.split(".")[1])
    return out


class TestKatmanDisiplini:
    """Modül bağımlılık yönü — tersine dönmesi sessiz bir mimari çürümedir."""

    @pytest.mark.parametrize("modul", ["util", "stats", "schema", "risk"])
    def test_saf_moduller_is_mantigi_IMPORT_ETMEZ(self, modul):
        """Bu dördü SAF: proje içinden hiçbir şey import etmezler.

        `util.py`'nin kendi ifadesi: *"Buraya iş mantığı GİRMEZ. Bir fonksiyon
        'BIST' veya 'faktör' kelimesini biliyorsa yanlış modüldedir."* Bir
        `from . import db` eklemek bu cümleyi sessizce yalanlar ve döngüsel
        import riskini doğurur.
        """
        yerel = _import_edilen_yerel_moduller(SRC / f"{modul}.py")
        assert not yerel, f"src/{modul}.py saf olmalı ama import ediyor: {sorted(yerel)}"

    def test_stats_veritabani_TANIMAZ(self):
        kaynak = (SRC / "stats.py").read_text(encoding="utf-8")
        assert "sqlite3" not in kaynak and "pandas" not in kaynak, (
            "Ölçüm çekirdeği veri erişim katmanını tanımaz; tanırsa saf "
            "fonksiyonlar test edilemez hale gelir.")

    def test_resolver_LLM_KATMANINI_import_etmez(self):
        """Sonucu KOD yazar, LLM ASLA. Bu, import grafiğinde de görünmeli.

        `resolver` `audit`/`llm_io`/`schema`'yı tanımazsa, birinin oraya "LLM
        çıktısından sonucu düzelt" mantığı eklemesi imkânsıza yakın olur.
        """
        yerel = _import_edilen_yerel_moduller(SRC / "resolver.py")
        assert not (yerel & {"audit", "llm_io", "schema", "evaluate", "report"}), (
            f"resolver LLM katmanını import ediyor: {sorted(yerel)}")

    def test_kimse_cli_yi_import_etmez(self):
        """CLI en dış kabuktur; iş mantığı ona bağlanırsa Actions'a taşımak zorlaşır."""
        for p in SRC.rglob("*.py"):
            if p.name == "cli.py":
                continue
            assert "cli" not in _import_edilen_yerel_moduller(p), f"{p.name} → cli"

    def test_kaynak_adaptorleri_ust_katmani_TANIMAZ(self):
        """`src/sources/*` yalnız `util` bilir — yukarı doğru bağımlılık yok."""
        for p in (SRC / "sources").glob("*.py"):
            yerel = _import_edilen_yerel_moduller(p)
            assert yerel <= {"util"}, f"{p.name} fazladan import ediyor: {sorted(yerel)}"


# ============================================================ 7. migration
class TestMigrationDisiplini:
    """Yayınlanmış migration DEĞİŞTİRİLMEZ; yanlışsa üstüne yenisi yazılır.

    Sebep: farklı makinelerdeki veritabanları sessizce ayrışır. `_m004`'ün
    varlığı bu kuralın bedelini gösteriyor — `_m003`'ü düzeltmek yerine ayrı
    bir adım yazıldı.
    """

    def test_surumler_kesintisiz_ve_sirali(self):
        hedefler = [m[0] for m in migrations.MIGRATIONS]
        assert hedefler == sorted(hedefler), "MIGRATIONS listesi sıralı olmalı"
        assert hedefler == list(range(migrations.BASELINE_VERSION + 1,
                                      migrations.BASELINE_VERSION + 1 + len(hedefler))), (
            "sürüm numaralarında boşluk var — `apply` bunu RuntimeError ile reddeder")
        assert migrations.target_version() == max(hedefler)

    def test_migration_sayisi_AZALAMAZ(self):
        """Bir migration'ı silmek, onu almış veritabanlarını geri döndürülemez
        biçimde ayrıştırır. Liste yalnız BÜYÜR."""
        assert len(migrations.MIGRATIONS) >= 5

    def test_her_migrationin_gerekcesi_yazili(self):
        for hedef, aciklama, fn in migrations.MIGRATIONS:
            assert aciklama and len(aciklama) > 20, f"v{hedef}: açıklama yetersiz"
            assert fn.__doc__ and len(fn.__doc__.strip()) > 40, (
                f"v{hedef}: migration'ın NEDEN yazıldığı docstring'de yok")

    def test_apply_iki_kez_kosmak_zararsiz(self, con):
        assert migrations.apply(con) == []
        assert migrations.apply(con) == []
        assert migrations.current_version(con) == migrations.target_version()

    def test_ALTER_ile_eklenen_kolon_DUMP_TABLOSUNDA_sona_yazilir(self, con):
        """⚠ TAZE ŞEMA ile MIGRATE EDİLMİŞ ŞEMA aynı SIRADA olmalı.

        SQLite `ALTER TABLE ADD COLUMN` yeni kolonu daima SONA koyar. Taban
        şemada (`db.SCHEMA`) aynı kolon başka bir yere yazılırsa iki kurulum
        ayrışır:

            yerel makine  → migrate edilmiş → kolon SONDA
            GitHub Actions→ dump'tan taze  → kolon ORTADA

        Yazma güvende kalır (kolonlar ada göre yazılır) ama `dbdump` PRAGMA
        sırasını kullanır: **aynı veri iki farklı metin üretir** ve dump'ın
        varlık sebebi olan determinizm çöker. Her koşuda sahte, devasa bir
        diff görünürdü ve "veri değişti mi?" sorusu cevapsız kalırdı.

        ⚠ Yalnız DUMP'A GİREN tablolar denetlenir: `dbdump.ATLA`daki türev
        tablolar (indicator/levels/data_quality) dump'a girmediği için sıra
        ayrışması onlarda sonuç doğurmaz — ve `data_quality` bugün gerçekten
        bu durumda (v7/v8 kolonları ortada). Kuralı oraya da dayatmak, bedeli
        olmayan bir kozmetik borç yaratırdı.
        """
        import ast

        kaynak = ast.parse((SRC / "migrations.py").read_text(encoding="utf-8"))
        eklenen: dict[str, list[str]] = {}
        for d in ast.walk(kaynak):
            if (isinstance(d, ast.Call) and isinstance(d.func, ast.Name)
                    and d.func.id == "_add_column" and len(d.args) >= 3
                    and all(isinstance(a, ast.Constant) for a in d.args[1:3])):
                eklenen.setdefault(d.args[1].value, []).append(d.args[2].value)

        assert eklenen, "hiç `_add_column` bulunamadı — tarama bozulmuş olabilir"
        denetlenen = 0
        for tablo, kolonlar in eklenen.items():
            if tablo in dbdump.ATLA:
                continue
            denetlenen += 1
            gercek = _kolonlar(con, tablo)
            assert gercek[-len(kolonlar):] == kolonlar, (
                f"`{tablo}`: ALTER ile eklenen {kolonlar} taban şemada SONDA "
                f"değil (gerçek son kolonlar: {gercek[-len(kolonlar):]}). "
                "Taze ve migrate edilmiş veritabanları ayrışır → dump "
                "determinizmi kırılır.")
        assert denetlenen, "dump'a giren hiçbir tabloya ALTER yapılmamış — test kör"

    def test_taban_sema_idempotent(self, con):
        """`db.SCHEMA` her `connect`te koşar; ikinci koşuş hata vermemeli."""
        con.executescript(db.SCHEMA)
        con.executescript(db.SCHEMA)

    def test_v3_tuzagi_kilidi_outcomes_sorgulanabilir(self, con):
        """`legacy_alter_table` tuzağı: `outcomes` FK'sı silinmiş tabloyu gösteriyordu.

        Belirti çıplaktı: `outcomes` üzerindeki HER sorgu
        "no such table: predictions_eski" ile patlıyordu. Bu test o belirtiyi
        sabitler.
        """
        con.execute("SELECT COUNT(*) FROM outcomes").fetchone()
        sql = con.execute("SELECT sql FROM sqlite_master WHERE name='outcomes'"
                          ).fetchone()[0]
        assert "predictions_eski" not in sql
        assert "REFERENCES predictions" in sql


# ============================================================ 8. config bütünlüğü
class TestConfigButunlugu:
    def test_paths_anahtarlarinin_hepsi_KULLANILIYOR(self, real_cfg):
        """Okunmayan bir config anahtarı, onu değiştirene "ayarladım" hissi
        veren sessiz bir yalandır (config.yaml'ın kendi ifadesi)."""
        kaynak = " ".join(p.read_text(encoding="utf-8") for p in SRC.rglob("*.py"))
        for k in real_cfg["paths"]:
            assert f'"{k}"' in kaynak or f"'{k}'" in kaynak, (
                f"`paths.{k}` kodda hiç okunmuyor — ya bağla ya kaldır.")

    # Bilerek deklaratif bırakılmış anahtarlar: kodda okunmuyorlar ama
    # dokümantasyon/ön kayıt değeri taşıyorlar. Liste DONDURULMUŞTUR — yeni bir
    # okunmayan anahtar eklemek bu testi patlatır ve yazan kişiyi karar vermeye
    # zorlar: bağla, kaldır, ya da BİLİNÇLİ olarak buraya ekle.
    DEKLARATIF = {
        "evren.min_gecmis_gun_olcum",     # in_measure kriteri — universe.yaml'da elle uygulanır
        "gostergeler.hacim_sma",          # ayrılmış; hacim göstergesi henüz yok
        "planlayici.stop_yontemleri",     # planner.STOP_METHODS ile aynı; belge amaçlı
        "planlayici.hedef_kaynaklari",    # "hedef uydurulmaz" kuralının yazılı hâli
        "llm.output_schema_version",      # schema.OUTPUT_SCHEMA_VERSION ile eşliği test edilir
        "llm.bundle_version",             # schema.BUNDLE_VERSION ile eşliği test edilir
        "olcum.birincil_taban",           # ADR #002 kararının yazılı hâli
        "olcum.ikincil_taban",
        "olcum.kenarsiz_ufuklar",         # H=5 ölçümünün kaydı
        "rapor.dil",
        "rapor.once_azalt_bolumu",        # rapor sırası testte sabitlenir
    }

    # `llm.veto_suresi_gun` alt anahtarları DİNAMİK okunur
    # (`journal.aktif_vetolar`: `sure.get(r["veto_code"], varsayilan)`), yani
    # literal metin araması onları göremez. Gevşetmek yerine DAHA SIKI bir
    # sözleşmeye bağlandılar: aşağıdaki test, anahtar kümesinin `veto_code`
    # enum'uyla BİREBİR aynı olmasını zorlar (AGENTS.md §12, yapı eşliği).
    # Böylece "okunmayan anahtar" testi gevşemiş olmuyor; başka bir testin
    # kapsamına giriyor.
    DINAMIK_OKUNAN = {f"llm.veto_suresi_gun.{k}" for k in
                      ("haber_riski", "kurumsal_islem", "likidite_zayif",
                       "sektor_yogunlugu", "tez_zayif", "veri_supheli",
                       "rejim_uyumsuz")}

    def test_yeni_OKUNMAYAN_config_anahtari_eklenmedi(self, real_cfg):
        kaynak = " ".join(p.read_text(encoding="utf-8") for p in SRC.rglob("*.py"))

        def kullanilir(ad: str) -> bool:
            return f'"{ad}"' in kaynak or f"'{ad}'" in kaynak

        okunmayan: list[str] = []

        def gez(d: dict, yol: str = "") -> None:
            for k, v in d.items():
                tam = f"{yol}.{k}" if yol else k
                if isinstance(v, dict):
                    if kullanilir(k):
                        gez(v, tam)
                    else:
                        okunmayan.append(tam)
                elif not kullanilir(k):
                    okunmayan.append(tam)

        gez(real_cfg)
        yeni = sorted(set(okunmayan) - self.DEKLARATIF - self.DINAMIK_OKUNAN)
        assert not yeni, (
            f"Kodda okunmayan YENİ config anahtarı: {yeni}. Ya bağla, ya "
            f"kaldır, ya da gerekçesiyle `DEKLARATIF` listesine ekle.")

    def test_veto_suresi_anahtarlari_ENUM_ile_BIREBIR(self, real_cfg):
        """⚠ YAPI EŞLİĞİ (AGENTS.md §12). Eksik anahtar SESSİZCE varsayılana düşer.

        Yeni bir `veto_code` eklenip süresi yazılmazsa, o veto varsayılan süreyi
        alır ve kimse fark etmez — yani bir karar, config düzenlemesi olarak
        değil, config'i DÜZENLEMEYEREK alınmış olur. Bu test onu görünür kılar.
        """
        kodlar = set(real_cfg["llm"]["enums"]["veto_code"])
        sureler = set(real_cfg["llm"]["veto_suresi_gun"]) - {"varsayilan"}
        assert sureler == kodlar, (
            f"veto_code enum'u ile veto_suresi_gun ayrıştı — "
            f"süresi olmayan: {sorted(kodlar - sureler)}, "
            f"karşılığı olmayan: {sorted(sureler - kodlar)}")
        assert all(int(v) > 0 for k, v in real_cfg["llm"]["veto_suresi_gun"].items()), \
            "veto süresi 0 ya da negatif olamaz — veto anında düşer"

    def test_fiyat_adimlari_artan_ve_acik_uclu(self, real_cfg):
        bantlar = real_cfg["risk"]["fiyat_adimlari"]
        assert bantlar[-1]["ust_sinir"] is None, (
            "Son bant AÇIK UÇLU olmalı; aksi halde tavanın üstündeki bir fiyat "
            "`tick_size`'ın son satır fallback'ine düşer ve sessizce yanlış "
            "ızgara kullanılır.")
        sinirlar = [b["ust_sinir"] for b in bantlar[:-1]]
        assert sinirlar == sorted(sinirlar), "bantlar artan sırada olmalı"
        adimlar = [b["adim"] for b in bantlar]
        assert all(a > 0 for a in adimlar)
        assert adimlar == sorted(adimlar), (
            "adım fiyatla birlikte büyümeli — küçülmesi ölçüme aykırı")
        for b in bantlar[:-1]:
            assert len(str(b["ust_sinir"])) <= 8

    def test_rejim_politikasi_etiketleri_TAM(self, real_cfg):
        assert set(real_cfg["rejim"]["politika"]) == set(regime.ETIKETLER)
        for etiket, pol in real_cfg["rejim"]["politika"].items():
            assert set(pol) == {"nakit_pct", "maks_pozisyon", "boyut_carpani"}, etiket
            assert 0 <= pol["nakit_pct"] <= 100
            assert pol["maks_pozisyon"] >= 1
            assert 0 < pol["boyut_carpani"] <= 1.0

    def test_rejim_politikasi_DEFANSIFLIK_YONUNDE_monoton(self, real_cfg):
        """risk-on → neutral → transition → risk-off boyunca defansiflik ARTAR.

        Bu sıra ters çevrilirse rejim katmanı riski YANLIŞ yönde ölçekler ve
        hiçbir test patlamaz: sayılar hâlâ geçerli, çıktı hâlâ "makul" görünür.
        Tam olarak bu projenin en pahalı hata sınıfı.
        """
        sira = ["risk-on", "neutral", "transition", "risk-off"]
        pol = real_cfg["rejim"]["politika"]
        nakit = [pol[s]["nakit_pct"] for s in sira]
        poz = [pol[s]["maks_pozisyon"] for s in sira]
        carpan = [pol[s]["boyut_carpani"] for s in sira]
        assert nakit == sorted(nakit), f"nakit oranı monoton artmıyor: {nakit}"
        assert poz == sorted(poz, reverse=True), f"maks pozisyon azalmıyor: {poz}"
        assert carpan == sorted(carpan, reverse=True), f"boyut çarpanı azalmıyor: {carpan}"

    def test_rejim_esikleri_tutarli(self, real_cfg):
        on = real_cfg["rejim"]["esikler"]["risk_on"]
        off = real_cfg["rejim"]["esikler"]["risk_off"]
        assert off["xu100_sma200_farki_pct_maks"] < on["xu100_sma200_farki_pct_min"]
        assert off["genislik_sma50_ustu_pct_maks"] < on["genislik_sma50_ustu_pct_min"]

    def test_faktor_agirliklari_faktor_adlariyla_ayni(self, real_cfg):
        assert set(real_cfg["faktorler"]["agirliklar"]) == set(factors.FACTOR_NAMES)

    def test_seans_saatleri_sirali(self, real_cfg):
        s = real_cfg["takvim"]["seans"]
        sirali = [s["acilis_muzayede_baslangic"], s["surekli_islem_baslangic"],
                  s["surekli_islem_bitis"], s["kapanis_muzayede_bitis"]]
        assert sirali == sorted(sirali), f"seans saatleri sıralı değil: {sirali}"

    def test_ana_ufuk_ufuklar_listesiyle_uyumlu(self, real_cfg):
        o = real_cfg["olcum"]
        assert int(o["ana_ufuk_gun"]) > 0
        assert int(real_cfg["planlayici"]["zaman_bariyeri_gun"]) > 0
        assert all(u > 0 for u in o["ufuklar_gun"])
        assert set(o["kenarsiz_ufuklar"]) <= set(o["ufuklar_gun"]), (
            "kenarsız olarak etiketlenen bir ufuk, ölçülen ufuklar arasında olmalı")

    def test_kap_dilimleme_olculen_tavanin_altinda(self, real_cfg):
        """KAP ~1578 kayıtta doyuyor (ölçüldü). Dilim ve eşik buna göre."""
        k = real_cfg["sources"]["kap"]
        assert int(k["parca_gun"]) <= 14, (
            "14 günden geniş dilim ölçülen doyma sınırına dayanır ve KAP "
            "pencereyi SESSİZCE kırpar.")
        assert int(k["doyma_esigi"]) <= 1578
        assert int(k["tam_cekim_gun"]) >= int(k["parca_gun"])


# ============================================================ 9. koruma ağı
class TestGercekVeritabaniKorumasi:
    """`pytest` kullanıcının verisine DOKUNMAZ — iddiası test edilir."""

    def test_readonly_baglanti_GERCEKTEN_salt_okunur(self, cfg, con):
        """`readonly=True` yalnız şema uygulamayı atlamıyor; yazmayı da reddediyor.

        İlk sürüm sadece `executescript(SCHEMA)`'yı atlıyordu — yani "readonly"
        adlı bağlantıyla pekâlâ yazılabiliyordu. Adı doğru davranışı yanlış bir
        bayrak, onu okuyan sonraki kişiyi yanıltır.
        """
        ro = db.connect(cfg, readonly=True)
        try:
            with pytest.raises(sqlite3.OperationalError):
                ro.execute("INSERT INTO holdings (ticker, qty) VALUES ('X', 1)")
                ro.commit()
        finally:
            ro.close()

    def test_koruma_gercek_db_yolunu_REDDEDER(self, real_cfg):
        """conftest'teki güvenlik ağının kendisi çalışıyor mu?

        Bir koruma testi olmadan koruma da "belgelenmiş ama var olmayan
        savunma"lardan biri olur.
        """
        with pytest.raises(RuntimeError, match="GERÇEK VERİTABANINA"):
            db.connect(real_cfg)

    def test_koruma_salt_okunur_erisimi_ENGELLEMEZ(self, real_cfg):
        p = db.db_path(real_cfg)
        if not p.exists():
            pytest.skip("proje veritabanı yok")
        c = db.connect(real_cfg, readonly=True)
        c.close()

    @pytest.mark.parametrize("anahtar", ["db", "db_dump", "log_dir",
                                         "llm_in_dir", "llm_out_dir", "reports_dir"])
    def test_cfg_fixture_YAZILAN_HER_YOLU_yonlendirir(self, cfg, real_cfg, anahtar):
        """Test suite'inin dosya sistemi yan etkisi OLMAZ.

        ⚠ Ölçüldü: `cfg` fixture'ının ilk hâli yalnız veritabanını
        yönlendiriyordu; `llm_in_dir` / `llm_out_dir` / `reports_dir` gerçek
        proje dizinlerini gösteriyordu ve `write_bundle` çağıran bir test
        kullanıcının repo'sunda `llm/in/<tarih>/` klasörü bırakıyordu.

        Bu test, o yönlendirmenin sessizce kaldırılmasını engeller. Yeni bir
        YAZILAN yol eklendiğinde buraya da eklenmeli.
        """
        assert cfg["paths"][anahtar] != real_cfg["paths"][anahtar], (
            f"`paths.{anahtar}` gerçek projeyi gösteriyor — testler oraya yazar.")
        # Asıl iddia: yazılan yol REPO DIŞINDA. (Geçici dizin adı platforma
        # göre değişir; "tmp" aramak kırılgan bir kontroldür.)
        yol = Path(cfg["paths"][anahtar]).resolve()
        assert not yol.is_relative_to(Path(util.ROOT).resolve()), (
            f"`paths.{anahtar}` repo içine yazıyor: {yol}")

    def test_okunan_girdiler_GERCEK_kalir(self, cfg, real_cfg):
        """Evren ve tatil dosyası BİLEREK gerçek: içerikleri testin konusudur."""
        for anahtar in ("universe_file", "holidays_file"):
            assert cfg["paths"][anahtar] == real_cfg["paths"][anahtar]


# ============================================================ 10. determinizm
class TestDeterminizm:
    def test_ayni_paket_ayni_sha(self):
        b = {"asof": "2026-07-27", "evren": [{"ticker": "A", "fiyat": {"c": 1.5}}]}
        assert llm_io.bundle_sha(dict(b)) == llm_io.bundle_sha(dict(b))

    def test_bundle_sha_kendini_HESABA_KATMAZ(self):
        """Alan hesaba girerse sha'yı hesaplamak imkânsızlaşır (kendine referans)."""
        b = {"asof": "2026-07-27", "x": 1}
        s = llm_io.bundle_sha(b)
        assert llm_io.bundle_sha({**b, "bundle_sha": "farkli"}) == s
        assert llm_io.bundle_sha({**b, "bundle_sha": s}) == s

    def test_icerik_degisince_sha_DEGISIR(self):
        b = {"asof": "2026-07-27", "evren": [{"ticker": "A", "fiyat": {"c": 1.5}}]}
        b2 = {"asof": "2026-07-27", "evren": [{"ticker": "A", "fiyat": {"c": 1.6}}]}
        assert llm_io.bundle_sha(b) != llm_io.bundle_sha(b2)

    def test_anahtar_sirasi_sha_yi_etkilemez(self):
        assert (util.sha256_canonical({"a": 1, "b": 2})
                == util.sha256_canonical({"b": 2, "a": 1}))

    def test_resolver_surumu_sabit_ve_isimli(self):
        """Sonuçlar hangi kuralla çözüldüyse o kural izlenebilir olmalı."""
        assert resolver.RESOLVER_VERSION.startswith("resolver_")
        assert "resolver_version" in resolver.OUTCOME_COLS


# ============================================================ 8. otomasyon (Faz 8)
class TestOtomasyonSozlesmesi:
    """Actions ↔ kod ↔ secret betiği arasındaki sessiz ayrışmalar.

    Bu üçlünün ayrışması CI'da anlamlı bir hata üretmez: eksik bir secret
    "anahtar yok" demez, zincirin o halkasını SESSİZCE eler
    (`analist.zincir`) — yani Gemini anahtarı unutulursa sistem her gün
    OpenAI'a düşer, para harcar ve kimse fark etmez.
    """

    WF = Path(util.ROOT) / ".github" / "workflows"

    def _wf_metni(self) -> str:
        return " ".join(p.read_text(encoding="utf-8")
                        for p in self.WF.glob("*.yml"))

    def test_workflowlarin_kullandigi_her_secret_BETIKTE_var(self):
        import importlib.util as _il

        spec = _il.spec_from_file_location(
            "set_secrets", Path(util.ROOT) / "scripts" / "set_secrets.py")
        mod = _il.module_from_spec(spec)
        spec.loader.exec_module(mod)

        kullanilan = set(re.findall(r"secrets\.([A-Z_]+)", self._wf_metni()))
        eksik = sorted(kullanilan - set(mod.SECRETS))
        assert not eksik, (
            f"Workflow bu secret'ları kullanıyor ama `scripts/set_secrets.py` "
            f"yüklemiyor: {eksik} — kurulumda sessizce eksik kalırlar")

    def test_workflowlarin_cagirdigi_her_komut_VAR(self):
        """`python -m src.cli <komut>` atıfları gerçekten var mı?

        Bir komutu yeniden adlandırmak workflow'u sessizce kırar ve bunu
        ancak ertesi sabah bildirim gelmeyince fark ederdin.
        """
        p = cli.build_parser()
        harita = next(a.choices for a in p._subparsers._group_actions)

        cagrilan = list(re.finditer(
            r"python -m src\.cli ([a-z]+)(?: ([a-z]+))?", self._wf_metni()))
        assert cagrilan, "workflow'lar hiçbir `bist` komutu çağırmıyor — regex bayat"

        for m in cagrilan:
            komut, alt = m.group(1), m.group(2)
            assert komut in harita, f"workflow olmayan komutu çağırıyor: {komut}"
            if alt:
                # Alt komutlar bu projede positional `choices` ile tanımlı
                # (`db dump|restore|durum`, `otonom gunluk|haftalik`).
                gecerli = {c for act in harita[komut]._actions
                           for c in (act.choices or [])}
                assert alt in gecerli, (
                    f"`{komut}` için geçersiz alt komut: {alt} "
                    f"(geçerli: {sorted(gecerli)})")

    def test_gunluk_workflow_ISLEM_GUNU_kapisina_guveniyor(self):
        """Cron hafta içi tatilleri bilmez; kapı kodda olmalı ve workflow
        onu ATLAMAMALI (ör. `--force` gibi bir bayrakla)."""
        metin = (self.WF / "gunluk.yml").read_text(encoding="utf-8")
        assert "otonom gunluk" in metin
        assert "--force" not in metin

    def test_commit_adimi_HATA_HALINDE_de_kosar(self):
        """⚠ Kritik adım düşse bile o ana kadar çekilen veri commit'lenmeli;
        aksi halde ertesi gün aynı veri yeniden çekilir ve BOZULMANIN İZİ
        kaybolur."""
        metin = (self.WF / "gunluk.yml").read_text(encoding="utf-8")
        commit_blogu = metin.split("Commit + push")[1]
        assert "if: always()" in metin.split("Commit + push")[0][-200:], \
            "commit adımı `if: always()` taşımıyor"
        assert "git pull --rebase" in commit_blogu, "push çakışma koruması yok"

    def test_workflowlar_ayni_concurrency_grubunda(self):
        """İki iş aynı anda push ederse biri kaybolur."""
        gruplar = re.findall(r"group:\s*(\S+)", self._wf_metni())
        commit_edenler = [g for g in gruplar if g == "repo-commit"]
        assert len(commit_edenler) >= 2, \
            "commit atan workflow'lar aynı concurrency grubunda değil"

    def test_arsiv_dizinleri_ARTIK_izleniyor(self):
        """Faz 8: Actions veritabanını her koşuda sıfırdan kurar. Arşiv
        gitignore'da kalırsa sistemin hafızası olmaz."""
        gi = (Path(util.ROOT) / ".gitignore").read_text(encoding="utf-8")
        satirlar = {s.strip() for s in gi.splitlines()
                    if s.strip() and not s.strip().startswith("#")}
        for yasak in ("data/*.sql", "reports/*.md", "llm/out/"):
            assert yasak not in satirlar, (
                f"`{yasak}` hâlâ gitignore'da — Actions arşivi commit'leyemez")

    # ------------------------------------------------------ test yan etkisizliği
    #
    # Testin YAZDIĞI her yol geçici dizine taşınmalı. Aşağıdakiler BİLEREK
    # gerçek kalır: testin konusu o dosyaların İÇERİĞİDİR (evren tanımı,
    # tatil listesi), yalnız okunurlar.
    SALT_OKUNUR_YOLLAR = {"universe_file", "holidays_file"}

    def test_yazilabilir_her_yol_GECICI_dizine_tasiniyor(self, cfg, real_cfg):
        """⚠ NE OLMUŞTU (2026-08-01): `cfg` fixture'ı `paths.*` anahtarlarını
        geçici dizine taşıyordu ama `telegram.outbox_file` BAŞKA BİR BLOKTA
        olduğu için gözden kaçtı. Telegram testleri kullanıcının repo'sundaki
        `data/telegram_outbox.jsonl` dosyasına 33 satır yazdı.

        "pytest yan etkisizdir" kuralı yazıldığı blokta tutuyor, simetriğinde
        tutmuyordu (L-008). Bu test o simetriyi zorlar: config'teki yol
        görünümlü HER anahtar ya geçiciye taşınmış ya da salt-okunur ilan
        edilmiş olmalı.
        """
        def yollar(d: dict, yol: str = ""):
            for k, v in d.items():
                tam = f"{yol}.{k}" if yol else k
                if isinstance(v, dict):
                    yield from yollar(v, tam)
                elif isinstance(v, str) and re.search(
                        r"^(data|reports|logs|llm)/|\.(db|sql|jsonl|log)$", v):
                    yield tam, k, v

        tasinmamis = []
        for tam, anahtar, gercek_deger in yollar(real_cfg):
            if anahtar in self.SALT_OKUNUR_YOLLAR:
                continue
            # `cfg` içindeki karşılığını bul
            dugum = cfg
            for parca in tam.split("."):
                dugum = dugum[parca]
            if dugum == gercek_deger:
                tasinmamis.append(tam)

        assert not tasinmamis, (
            f"Bu config yolları testte GERÇEK hedefe bakıyor: {tasinmamis}. "
            f"`tests/conftest.py::cfg` içinde geçici dizine taşı — yoksa "
            f"pytest kullanıcının dosyalarına yazar.")
