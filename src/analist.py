"""Otonom analist — LLM model zinciri (ADR #013).

Elle koşulan IDE turunun otomatik karşılığı. Aynı paketi (`llm/in/<asof>/`)
okur, aynı şemayı üretir, aynı denetimden geçer. Tek fark: analisti bir insan
değil, sıralı bir model listesi sağlar.

**ZİNCİR SEMANTİĞİ** (inkline `lib/ai/provider.ts` deseninden):
Liste baştan denenir; bir model cevap veremezse SIRADAKİNE geçilir. "Cevap
verememek" geniş tanımlıdır ve hepsi aynı kefeye girer:

    kota/429 · 5xx · zaman aşımı · ağ · geçersiz JSON · şema dışı çıktı
    · **`bist denetle` sert hatası**

Sondaki madde bu projeye özgü ve önemli: **HF denetimi zincirin bir halkasıdır.**
Şemaya uyan ama HF-01..31'den geçemeyen bir çıktı (uydurma sayı, uydurma
plan_id, rejim tavanını aşan pozisyon...) "cevap verilmedi" sayılır. Model
yalnız geçerli JSON üretmekle kalmaz, projenin kurallarına da uymak zorundadır.

**Ara halkalarda tekrar YOK.** Aynı modele ısrar etmek, arkasında beş yedek
varken zaman kaybıdır; asıl yedekleme zincirin kendisidir. Yalnız son halkada
`llm.son_halka_tekrar` kadar tekrar denenir.

**`tool` alanını KOD yazar, model değil.** Model kendi kimliğini yanlış yazarsa
(ya da iskeletteki `"<araç>"` yer tutucusunu olduğu gibi bırakırsa) ölçüm
kirlenir: `bist degerlendir --tool X` yanlış kayıtları toplar. Çıktı parse
edildikten sonra `out["tool"]` KOD tarafından model kimliğine set edilir.

SDK yok: `requests` ile düz REST. Gerekçe PROJECT.md'deki araç bağımsızlığı
kısıtı — bir sağlayıcının SDK'sına bağlanmak, o sağlayıcıyı zincirden çıkarmayı
zorlaştırır.
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import uuid
from pathlib import Path

import requests

from . import audit, util

log = logging.getLogger(__name__)

GEMINI_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
              "{model}:generateContent")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

ANAHTAR = {"google": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY"}


class ZincirBos(RuntimeError):
    """Hiçbir sağlayıcının anahtarı yok — zincir kurulamıyor."""


class TumModellerDustu(RuntimeError):
    """Zincirdeki her model denendi, hiçbiri denetimden geçen çıktı vermedi."""


# ---------------------------------------------------------------- sağlayıcı
def provider_of(model_id: str) -> str:
    """Model kimliğinden sağlayıcı. `gemini*` → google, gerisi → openai."""
    return "google" if re.match(r"^(gemini|gemma)", model_id, re.I) else "openai"


def _anahtar_var(provider: str) -> bool:
    return bool(util.env(ANAHTAR[provider]))


def zincir(cfg: dict) -> list[str]:
    """Denenecek modeller, sırayla. Anahtarı olmayan sağlayıcının modelleri ELENİR.

    Eleme sessiz değil: hangi modelin neden düştüğü loglanır. Aksi halde
    "zincir neden gpt'ye düştü?" sorusu cevapsız kalır ve eksik bir anahtar
    kota sorunu gibi görünür.
    """
    out = []
    for m in cfg["llm"]["zincir"]:
        p = provider_of(m)
        if _anahtar_var(p):
            out.append(m)
        else:
            log.info("zincir: %s atlandı — %s tanımlı değil", m, ANAHTAR[p])
    return out


def _dusunme_destekler(model_id: str) -> bool:
    """`thinkingLevel` Gemini 3 ve sonrasının parametresi.

    ⚠ gemini-2.5-* bunu TANIMAZ ve gönderilirse istek 400 döner (inkline'da
    yaşandı). O modeller kendi dinamik düşünme varsayılanıyla çalışır. Zincirin
    3. halkası tam olarak bir 2.5 modeli olduğu için bu kontrol süs değil:
    olmazsa o halka HER ZAMAN düşer ve sebebi "kota" sanılır.
    """
    m = re.match(r"^gemini-(\d+)", model_id)
    return bool(m) and int(m.group(1)) >= 3


def _akil_yurutme_modeli(model_id: str) -> bool:
    """OpenAI akıl yürütme modelleri (gpt-5*, o-serisi) `temperature` KABUL ETMEZ."""
    return bool(re.match(r"^(gpt-5|o[1-9])", model_id)) and not model_id.endswith("-chat-latest")


# ---------------------------------------------------------------- çağrı
def _gemini_cagir(cfg: dict, model_id: str, prompt: str, zaman_asimi: int) -> str:
    govde: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            # ⚠ AÇIKÇA VERİLMEZSE sağlayıcının varsayılanına düşer ve çıktı
            # SESSİZCE KESİLİR. Yaşandı (2026-08-01, ilk otonom tur):
            # gemini-3.5-flash JSON'u 17.000 karakterde kesildi, hata
            # "Expecting ',' delimiter" diye göründü ve zincir bir sonraki
            # modele düştü — yani en iyi halka bir biçim kazası yüzünden
            # kaybedildi. 18 hisselik çıktı ~4.3K token; düşünme token'ları
            # da bu bütçeden yendiği için pay geniş tutulur.
            "maxOutputTokens": int(cfg["llm"]["maks_cikti_token"]),
        },
    }
    if _dusunme_destekler(model_id):
        govde["generationConfig"]["thinkingConfig"] = {
            "thinkingLevel": cfg["llm"]["zincir_dusunme"]["gemini"]}

    r = requests.post(
        GEMINI_URL.format(model=model_id),
        headers={"x-goog-api-key": util.env(ANAHTAR["google"]),
                 "Content-Type": "application/json"},
        json=govde, timeout=zaman_asimi)
    r.raise_for_status()
    veri = r.json()
    try:
        parcalar = veri["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError) as e:
        # Güvenlik filtresi / boş aday da bir "cevap verememe"dir; zincir devam etsin.
        raise RuntimeError(f"beklenmeyen Gemini yanıtı: {str(veri)[:200]}") from e
    return "".join(p.get("text", "") for p in parcalar)


def _openai_cagir(cfg: dict, model_id: str, prompt: str, zaman_asimi: int) -> str:
    govde: dict = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        # Gemini tarafındaki kesilme kazasının simetriği (bkz. `_gemini_cagir`).
        # Akıl yürütme modellerinde düşünme token'ları da bu bütçeden yenir.
        "max_completion_tokens": int(cfg["llm"]["maks_cikti_token"]),
    }
    if _akil_yurutme_modeli(model_id):
        govde["reasoning_effort"] = cfg["llm"]["zincir_dusunme"]["openai"]

    r = requests.post(
        OPENAI_URL,
        headers={"Authorization": f"Bearer {util.env(ANAHTAR['openai'])}",
                 "Content-Type": "application/json"},
        json=govde, timeout=zaman_asimi)
    r.raise_for_status()
    veri = r.json()
    try:
        return veri["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"beklenmeyen OpenAI yanıtı: {str(veri)[:200]}") from e


def _cagir(cfg: dict, model_id: str, prompt: str) -> str:
    z = int(cfg["llm"].get("istek_zaman_asimi_s", 180))
    if provider_of(model_id) == "google":
        return _gemini_cagir(cfg, model_id, prompt, z)
    return _openai_cagir(cfg, model_id, prompt, z)


# ---------------------------------------------------------------- çıktı
def _json_ayikla(ham: str) -> dict:
    """Modelin ürettiği metinden JSON nesnesini çıkarır.

    `responseMimeType`/`response_format` istenmiş olsa da bazı modeller çıktıyı
    ```json çitiyle sarar. Kırılgan bir temizlik yerine ilk `{` ile son `}`
    arası alınır — sarmalayıcı ne olursa olsun çalışır.
    """
    s = ham.strip()
    bas, son = s.find("{"), s.rfind("}")
    if bas < 0 or son <= bas:
        raise ValueError(f"çıktıda JSON nesnesi yok: {s[:200]}")
    return json.loads(s[bas:son + 1])


def istem_oku(cfg: dict, asof: str) -> str:
    """Analistin göreceği tam metin: görev tanımı + paketin okunabilir hâli.

    Elle koşulan turda insan `prompt.md`'yi açar ve `context.md`'ye bakar; model
    tek bir metin aldığı için ikisi burada birleştirilir. Kaynak dosyalar aynı
    (`bist gunluk` üretir) — yani otomatik analist ile elle analist BİREBİR aynı
    girdiyi görür ve ölçümleri kıyaslanabilir kalır.
    """
    d = util.resolve(Path(cfg["paths"]["llm_in_dir"]) / asof)
    istem, baglam = d / "prompt.md", d / "context.md"
    if not istem.exists() or not baglam.exists():
        raise FileNotFoundError(f"Paket eksik: {d} — önce `bist gunluk`")
    return (istem.read_text(encoding="utf-8")
            + "\n\n---\n\n"
            + baglam.read_text(encoding="utf-8"))


def _cikti_yaz(cfg: dict, asof: str, out: dict) -> Path:
    return util.write_json(
        Path(cfg["paths"]["llm_out_dir"]) / asof / "analysis.json", out)


def _guvenli_hata(error: Exception) -> str:
    text = str(error)
    for name in ANAHTAR.values():
        secret = util.env(name)
        if secret:
            text = text.replace(secret, '[gizli]')
    return re.sub(r'([?&](?:key|api_key)=)[^&\s]+', r'\1[gizli]', text)[:300]


def _deneme_kaydet(cfg, asof, cycle_id, attempt):
    path = Path(cfg['paths']['llm_out_dir']) / asof / 'attempts.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {'cycle_id': cycle_id, 'at': util.utc_now_iso(), **attempt}
    with path.open('a', encoding='utf-8') as file:
        file.write(json.dumps(row, ensure_ascii=False) + '\n')


# ---------------------------------------------------------------- zincir
def calistir(cfg: dict, con: sqlite3.Connection, asof: str,
             *, modeller: list[str] | None = None) -> dict:
    """Zinciri koşar. İlk DENETİMDEN GEÇEN çıktı kazanır.

    Dönen sözlük: {model, out, denemeler:[{model, sonuc, detay}]}
    `denemeler` her zaman doldurulur — başarılı turda bile hangi modellerin
    denendiği raporlanabilsin diye (haftalık rapor bunu kullanır).

    Başarısızlıkta `TumModellerDustu` fırlatır: çağıran taraf bunu "analist yok"
    olarak ele alır ve deterministik rapor yine üretilir.
    """
    liste = modeller if modeller is not None else zincir(cfg)
    if not liste:
        raise ZincirBos(
            "Zincirde model yok — GEMINI_API_KEY / OPENAI_API_KEY tanımlı değil.")

    bundle = util.read_json(
        Path(cfg["paths"]["llm_in_dir"]) / asof / "bundle.json")
    if bundle is None:
        raise FileNotFoundError(f"Paket yok: llm/in/{asof}/bundle.json")

    prompt = istem_oku(cfg, asof)
    denemeler: list[dict] = []
    cycle_id = uuid.uuid4().hex
    son_hata: Exception | None = None

    for i, model_id in enumerate(liste):
        sondaki = i == len(liste) - 1
        # Ara halkada tek deneme; son halkada config'teki kadar tekrar.
        tekrar = int(cfg["llm"].get("son_halka_tekrar", 2)) if sondaki else 0

        for deneme in range(tekrar + 1):
            try:
                ham = _cagir(cfg, model_id, prompt)
                out = _json_ayikla(ham)
                # `tool`u KOD yazar — modelin beyanına güvenilmez (docstring).
                out["tool"] = model_id

                bulgular = audit.audit(cfg, bundle, out, con)
                sert = audit.hard_fails(bulgular)
                if sert:
                    kodlar = sorted({f.code for f in sert})
                    raise RuntimeError(f"denetim sert hatası: {', '.join(kodlar)}")

                # YALNIZ denetimden geçen çıktı diske yazılır: yarım/hatalı bir
                # analysis.json bırakmak, sonraki `bist denetle` çağrısını
                # yanıltır ve "kaydedilmiş gibi" görünür.
                _cikti_yaz(cfg, asof, out)
                denemeler.append({"model": model_id, "sonuc": "temiz"})
                _deneme_kaydet(cfg, asof, cycle_id, denemeler[-1])
                log.info("analist: %s temiz çıktı verdi", model_id)
                return {"model": model_id, "out": out, "denemeler": denemeler}

            except Exception as e:                      # noqa: BLE001 - sınıf fark etmez
                son_hata = e
                detay = _guvenli_hata(e)
                denemeler.append({"model": model_id, "sonuc": "hata",
                                  "detay": detay})
                _deneme_kaydet(cfg, asof, cycle_id, denemeler[-1])
                kalan = tekrar - deneme
                log.warning("analist: %s cevap veremedi (%s)%s",
                            model_id, detay,
                            f" — {kalan} tekrar kaldı" if kalan else "")

    raise TumModellerDustu(
        f"Zincirdeki {len(liste)} modelin hiçbiri denetimden geçen çıktı vermedi. "
        f"Son hata: {_guvenli_hata(son_hata)}")
