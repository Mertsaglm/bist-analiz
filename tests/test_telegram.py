"""Telegram gönderim katmanı — mekanizma testleri (Faz 8).

AĞ YOK. `requests.post` monkeypatch'lenir; gerçek bot token'ı olmadan da
tam davranış sınanır.
"""

from __future__ import annotations

import json

import pytest

from src import report, telegram_bist as tg, util


class SahteYanit:
    def raise_for_status(self): pass

    def json(self): return {"ok": True}


@pytest.fixture
def sahte_post(monkeypatch):
    """Giden istekleri toplar."""
    gonderilen: list[dict] = []

    def post(url, data=None, timeout=None):
        gonderilen.append({"url": url, "data": data})
        return SahteYanit()

    monkeypatch.setattr(tg.requests, "post", post)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123456789")
    monkeypatch.setattr(util, "load_env", lambda *a, **k: None)
    return gonderilen


# ============================================================ bölme
class TestChunk:
    def test_kisa_metin_tek_parca(self):
        assert tg.chunks("merhaba", 100) == ["merhaba"]

    def test_SATIR_SINIRINDA_boler(self):
        """⚠ Körlemesine karakter bölmesi bir tabloyu/madde imini ortadan
        keser ve mesaj okunmaz olur. Bölme daima satır sınırında."""
        beklenen = [f"satir-{i:02d}" for i in range(20)]
        parcalar = tg.chunks("\n".join(beklenen), 40)
        assert len(parcalar) > 1
        for p in parcalar:
            assert len(p) <= 40
        # Hiçbir satır ortadan kesilmemiş: parçaları birleştirince orijinal
        # satır listesi BİREBİR geri gelmeli.
        geri = [s for p in parcalar for s in p.split("\n")]
        assert geri == beklenen

    def test_tek_satir_siniri_asarsa_sert_bolunur(self):
        """Nadir ama mümkün: tek bir satır sınırdan uzunsa zorunlu sert bölme."""
        parcalar = tg.chunks("x" * 250, 100)
        assert [len(p) for p in parcalar] == [100, 100, 50]

    def test_hicbir_parca_siniri_asmaz(self):
        metin = "\n".join("a" * 70 for _ in range(30))
        for p in tg.chunks(metin, 100):
            assert len(p) <= 100

    def test_bos_metin(self):
        assert tg.chunks("", 100) == [""]


class TestMarkdownTemizleme:
    def test_kalin_kod_baslik_alinti_temizlenir(self):
        """Rapor DÜZ METİN gider: Markdown modunda tek kaçırılmamış karakter
        Telegram'da 400 döndürür ve bildirimin tamamı kaybolur."""
        ham = "# Başlık\n> uyarı\n**kalın** ve `kod`"
        d = tg.md_to_plain(ham)
        assert "#" not in d and ">" not in d
        assert "**" not in d and "`" not in d
        assert "Başlık" in d and "kalın" in d and "kod" in d


# ============================================================ gönderim
class TestGonderim:
    def test_uzun_mesaj_birden_cok_istekte_gider(self, cfg, sahte_post):
        cfg["telegram"]["mesaj_limiti"] = 300
        cfg["telegram"]["mesaj_payi"] = 100      # etkin sınır 200
        metin = "\n".join(f"satir {i}" for i in range(60))
        n = tg.send_message(cfg, metin)
        assert n > 1 and len(sahte_post) == n

    def test_chat_id_ve_metin_gonderilir(self, cfg, sahte_post):
        tg.send_message(cfg, "test mesajı")
        d = sahte_post[0]["data"]
        assert d["chat_id"] == "123456789"
        assert "test mesajı" in d["text"]

    def test_token_urlde_metinde_DEGIL(self, cfg, sahte_post):
        """Token yalnız URL'de; gövdeye ya da loga sızmamalı."""
        tg.send_message(cfg, "merhaba")
        assert "test-token" in sahte_post[0]["url"]
        assert "test-token" not in json.dumps(sahte_post[0]["data"])

    def test_anahtarsiz_bildir_SESSIZCE_atlar(self, cfg, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        monkeypatch.setattr(util, "load_env", lambda *a, **k: None)
        assert tg.bildir(cfg, "mesaj") is False

    def test_kapaliysa_gondermez(self, cfg, sahte_post):
        cfg["telegram"]["enabled"] = False
        assert tg.bildir(cfg, "mesaj") is False
        assert not sahte_post

    def test_gonderim_hatasi_YUTULMAZ(self, cfg, monkeypatch):
        """⚠ Sessiz bildirim kaybı, bildirimin kendisinden tehlikelidir:
        iş yeşil görünür ama kimse haberdar olmaz (gold dersi)."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "1")
        monkeypatch.setattr(util, "load_env", lambda *a, **k: None)

        def patlayan(*a, **k):
            raise tg.requests.exceptions.HTTPError("400")

        monkeypatch.setattr(tg.requests, "post", patlayan)
        with pytest.raises(tg.requests.exceptions.HTTPError):
            tg.bildir(cfg, "mesaj")


class TestOutbox:
    def test_giden_mesaj_jsonl_olarak_arsivlenir(self, cfg, sahte_post, tmp_path):
        cfg["telegram"]["outbox_file"] = str(tmp_path / "outbox.jsonl")
        tg.send_message(cfg, "arşivlenecek mesaj")

        satirlar = (tmp_path / "outbox.jsonl").read_text(encoding="utf-8").strip().split("\n")
        kayit = json.loads(satirlar[-1])
        assert kayit["metin"] == "arşivlenecek mesaj"
        assert kayit["parca"] == 1
        assert kayit["ts_utc"]

    def test_chat_id_TAM_yazilmaz(self, cfg, sahte_post, tmp_path):
        """Gereksiz kimlik bilgisi biriktirmenin savunulacak tarafı yok."""
        cfg["telegram"]["outbox_file"] = str(tmp_path / "outbox.jsonl")
        tg.send_message(cfg, "mesaj")
        kayit = json.loads((tmp_path / "outbox.jsonl").read_text(encoding="utf-8").strip())
        assert kayit["chat"] == "789"
        assert "123456789" not in json.dumps(kayit)

    def test_outbox_hatasi_GONDERIMI_ETKILEMEZ(self, cfg, sahte_post):
        """Arşiv bir yan kayıt; yazılamaması bildirimi düşürmemeli."""
        cfg["telegram"]["outbox_file"] = "/olmayan/dizin/xyz/outbox.jsonl"
        assert tg.send_message(cfg, "mesaj") == 1
        assert len(sahte_post) == 1

    def test_kapaliysa_yazmaz(self, cfg, sahte_post, tmp_path):
        cfg["telegram"]["outbox_enabled"] = False
        cfg["telegram"]["outbox_file"] = str(tmp_path / "outbox.jsonl")
        tg.send_message(cfg, "mesaj")
        assert not (tmp_path / "outbox.jsonl").exists()


# ============================================================ özet biçimi
def _bundle(asof="2026-07-29"):
    return {"asof": asof, "uyari": "test",
            "rejim": {"etiket": "risk-off",
                      "pozisyon_politikasi": {"nakit_pct": 90.0,
                                              "maks_pozisyon": 2,
                                              "sektor_basi_maks": 2}},
            "evren": []}


class TestTelegramOzet:
    def test_analist_yoksa_bunu_SOYLER(self, cfg):
        t = report.telegram_ozet(cfg, _bundle())
        assert "Analist çıktısı yok" in t
        assert "risk-off" in t

    def test_veto_ve_plan_gorunur(self, cfg):
        analiz = [
            {"ticker": "EUPWR", "action": "plan_reddet", "veto_code": "tez_zayif"},
            {"ticker": "KRDMD", "action": "plan_sec", "signal": "buy"},
        ]
        t = report.telegram_ozet(cfg, _bundle(), analiz=analiz,
                                 analist_model="gemini-3.5-flash")
        assert "EUPWR (tez_zayif)" in t
        assert "KRDMD" in t
        assert "gemini-3.5-flash" in t

    def test_AZALT_elde_tutulan_icin_ve_ONCE_gelir(self, cfg):
        """Rapor sırası ölçüme dayanıyor: azalt önce, yeni plan sonra."""
        analiz = [{"ticker": "THYAO", "action": "izle", "signal": "reduce"},
                  {"ticker": "KRDMD", "action": "plan_sec", "signal": "buy"}]
        t = report.telegram_ozet(cfg, _bundle(), analiz=analiz,
                                 holdings={"THYAO": {"qty": 100}})
        assert "AZALT: THYAO" in t
        assert t.index("AZALT") < t.index("Plan seçildi")

    def test_elde_olmayan_hisse_AZALT_bolumune_girmez(self, cfg):
        analiz = [{"ticker": "AKBNK", "action": "islem_yok", "signal": "avoid"}]
        t = report.telegram_ozet(cfg, _bundle(), analiz=analiz, holdings={})
        assert "AZALT" not in t

    def test_cozulen_tahminler_ozetlenir(self, cfg):
        t = report.telegram_ozet(cfg, _bundle(), analiz=[{"ticker": "X"}],
                                 cozulen=[{"resolution": "stop"},
                                          {"resolution": "stop"},
                                          {"resolution": "hedef"}])
        assert "hedef=1" in t and "stop=2" in t

    def test_kenar_yok_ibaresi_DAIMA_var(self, cfg):
        """Her çıktı bu ibareyi taşır (ADR #008) — bildirim de bir çıktıdır."""
        assert "kenar yok" in report.telegram_ozet(cfg, _bundle()).lower()

    def test_sakin_gun_KISA_kalir(self, cfg):
        """Bildirimin uzunluğu o gün olan bitenle orantılı olmalı."""
        t = report.telegram_ozet(cfg, _bundle())
        assert len(t.split("\n")) <= 8
