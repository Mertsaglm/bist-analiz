"""Telegram bildirimi — YALNIZ GÖNDERİM (Faz 8).

`gold_tracking_system/src/telegram_bot.py`'den taşındı, ama bilerek KÜÇÜLTÜLDÜ:
oradaki uzun-yoklamalı bot döngüsü (`run_bot`, `/durum`, `/rapor`... komutları)
buraya alınmadı. Gerekçe YAGNI — bize lazım olan tek yön dışarı doğru: Actions
koşusu bitince bir özet düşsün. Komut arayüzü isteği DOĞARSA o zaman eklenir;
şimdi eklenirse sürekli çalışan bir süreç ve onu yöneten bir supervisor gerekir,
ikisi de bu projede yok.

Token ve chat_id YALNIZCA ortamdan okunur (`TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHAT_ID`); config'e yazılmaz. Sebep basit: config repoda, secret değil.

**Outbox.** Gönderilen her mesaj `config.telegram.outbox_file` yoluna jsonl
olarak da yazılır. Neden: "sistem geçen hafta ne bildirdi?" sorusunu
Telegram'dan dışa aktarım yapmadan cevaplayabilmek için — bildirim de bir
çıktıdır ve arşivlenmelidir. `chat` alanına yalnız son 3 hane girer.
(Yol buraya GÖMÜLMEZ; tek kaynak config'tir.)
"""

from __future__ import annotations

import logging
import re

import requests

from . import util

log = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{token}/{method}"


class TelegramYapilandirilmamis(RuntimeError):
    """Token ya da chat_id yok."""


def _token() -> str:
    t = util.env("TELEGRAM_BOT_TOKEN")
    if not t:
        raise TelegramYapilandirilmamis("TELEGRAM_BOT_TOKEN tanımlı değil")
    return t


def _chat_id() -> str:
    c = util.env("TELEGRAM_CHAT_ID")
    if not c:
        raise TelegramYapilandirilmamis("TELEGRAM_CHAT_ID tanımlı değil")
    return c


def yapilandirilmis() -> bool:
    """Bildirim gönderilebilir mi? (Çağıran taraf sessizce atlayabilsin diye.)"""
    return bool(util.env("TELEGRAM_BOT_TOKEN") and util.env("TELEGRAM_CHAT_ID"))


def _call(method: str, **params):
    r = requests.post(API.format(token=_token(), method=method),
                      data=params, timeout=35)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------- biçim
_MD_KALIP = (
    (re.compile(r"^#{1,6}\s*", re.M), ""),      # başlık işaretleri
    (re.compile(r"^>\s?", re.M), ""),           # alıntı
    (re.compile(r"\*\*(.+?)\*\*", re.S), r"\1"),  # kalın
    (re.compile(r"`([^`]+)`"), r"\1"),          # satır içi kod
)


def md_to_plain(text: str) -> str:
    """Markdown → düz metin.

    Raporlar Telegram'a DÜZ METİN gider, `parse_mode` YOK. Gerekçe: Markdown/HTML
    modunda her `_`, `*`, `[` kaçırılmak zorundadır ve rapor metni bunlarla dolu
    (ticker adları, oranlar, tablolar). Tek bir kaçırılmamış karakter Telegram'da
    400 döndürür — yani biçim uğruna bildirimin tamamı kaybolur. Düz metin bu
    hata sınıfını tamamen ortadan kaldırır.
    """
    out = text
    for kalip, yerine in _MD_KALIP:
        out = kalip.sub(yerine, out)
    return out


def chunks(text: str, size: int) -> list[str]:
    """Metni `size` sınırını aşmayan parçalara böler — SATIR SINIRINDA.

    Karakter sayısına göre körlemesine bölmek bir tabloyu ya da madde imini
    ortadan keser ve okunmaz hale getirir. Tek bir satır tek başına sınırı
    aşıyorsa (nadir) o satır zorunlu olarak sert bölünür.
    """
    parcalar: list[str] = []
    tampon = ""
    for satir in text.split("\n"):
        while len(satir) > size:            # tek satır sınırı aşıyorsa sert böl
            if tampon:
                parcalar.append(tampon)
                tampon = ""
            parcalar.append(satir[:size])
            satir = satir[size:]
        aday = f"{tampon}\n{satir}" if tampon else satir
        if len(aday) > size:
            parcalar.append(tampon)
            tampon = satir
        else:
            tampon = aday
    if tampon:
        parcalar.append(tampon)
    return parcalar or [""]


# ---------------------------------------------------------------- outbox
def _outbox_yaz(cfg: dict, cid: str, metin: str, parca: int) -> None:
    """Giden mesajı repoya da yaz. HATASI GÖNDERİMİ ASLA ETKİLEMEZ.

    Arşiv yazımı bir yan kayıttır; başarısız olması bildirim başarısız oldu
    demek değildir. try/except olmasaydı dolu bir disk yüzünden bildirim
    hattı tamamen dururdu.
    """
    tg = cfg.get("telegram", {})
    if not tg.get("outbox_enabled", False):
        return
    try:
        p = util.ensure_parent(tg["outbox_file"])
        kayit = {"ts_utc": util.utc_now_iso(), "chat": str(cid)[-3:],
                 "parca": parca, "metin": metin}
        with p.open("a", encoding="utf-8") as fh:
            fh.write(util.json_dump(kayit, pretty=False) + "\n")
    except Exception as e:                              # noqa: BLE001
        log.warning("outbox yazılamadı: %s", e)


# ---------------------------------------------------------------- gönderim
def send_message(cfg: dict, text: str, chat_id: str | None = None) -> int:
    """Düz metin mesaj gönderir; kaç parçaya bölündüğünü döner."""
    cid = chat_id or _chat_id()
    tg = cfg.get("telegram", {})
    sinir = int(tg.get("mesaj_limiti", 4096)) - int(tg.get("mesaj_payi", 200))
    govde = md_to_plain(text)

    n = 0
    for parca in chunks(govde, sinir):
        _call("sendMessage", chat_id=cid, text=parca,
              disable_web_page_preview="true")
        n += 1

    log.info("telegram: %d parça gönderildi (chat=…%s)", n, str(cid)[-3:])
    _outbox_yaz(cfg, cid, govde, n)
    return n


def sohbetleri_bul() -> list[dict]:
    """Bota yazan sohbetleri listeler — kurulumda `TELEGRAM_CHAT_ID` bulmak için.

    Telegram bir botun kendi sohbet kimliğini sorgulamasına izin vermez; kimlik
    ancak biri bota YAZDIKTAN sonra `getUpdates` ile görünür. Bu yüzden akış
    şu sırayla işler: bot açılır → kullanıcı bota bir mesaj atar → burası okur.

    Yalnız TOKEN gerekir (chat_id henüz yok), o yüzden `_chat_id()` çağrılmaz.
    """
    r = requests.get(API.format(token=_token(), method="getUpdates"), timeout=35)
    r.raise_for_status()
    out, gorulen = [], set()
    for g in r.json().get("result", []):
        sohbet = ((g.get("message") or g.get("channel_post") or {}).get("chat")
                  or {})
        cid = sohbet.get("id")
        if cid is None or cid in gorulen:
            continue
        gorulen.add(cid)
        out.append({"id": cid, "tur": sohbet.get("type"),
                    "ad": sohbet.get("title") or sohbet.get("first_name") or "—"})
    return out


def bildir(cfg: dict, text: str) -> bool:
    """Yapılandırılmışsa gönder, değilse SESSİZCE atla.

    Çağıran tarafın her seferinde `if yapilandirilmis()` yazmasını önler.
    Gönderim hatasını YUTMAZ — çağıran taraf hatayı görmeli ki iş kırmızıya
    dönebilsin (gold dersi: sessiz bildirim kaybı, bildirimin kendisinden
    daha tehlikelidir).
    """
    if not cfg.get("telegram", {}).get("enabled", False):
        log.info("telegram kapalı (config.telegram.enabled)")
        return False
    if not yapilandirilmis():
        log.info("telegram anahtarı yok — bildirim atlandı")
        return False
    send_message(cfg, text)
    return True
