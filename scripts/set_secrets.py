"""`.env` içindeki anahtarları GitHub Actions secret'ı olarak yükler.

    python scripts/set_secrets.py <pat_dosyasi>

`<pat_dosyasi>`: GitHub Personal Access Token'ın TEK BAŞINA yazılı olduğu dosya.
Token komut satırına yazılmaz — kabuk geçmişine düşerdi.

Neden `gh` CLI değil: kurulu olduğu garanti değil ve tek iş için bağımlılık
eklemeye değmez. Sadece stdlib + `pynacl` (GitHub secret'ları libsodium sealed
box ile şifrelenmek ZORUNDA; düz metin kabul edilmiyor).

    pip install pynacl

Değerler HİÇBİR YERDE basılmaz — yalnız anahtar adı ve HTTP durumu.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from base64 import b64encode
from pathlib import Path

REPO = "Mertsaglm/bist-analiz"

# ⚠ Bu liste `.github/workflows/*.yml` içindeki `secrets.*` atıflarıyla
# UYUŞMALI. Eksik bir secret CI'da "anahtar yok" olarak değil, zincirin o
# halkasının sessizce elenmesi olarak görünür (`analist.zincir`) — yani
# Gemini anahtarı unutulursa sistem her gün OpenAI'a düşer ve fark edilmez.
SECRETS = [
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "EVDS_API_KEY",
]

API = "https://api.github.com"


def _istek(yol: str, token: str, veri: dict | None = None) -> dict:
    r = urllib.request.Request(
        f"{API}{yol}",
        data=json.dumps(veri).encode() if veri else None,
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
        method="PUT" if veri else "GET")
    with urllib.request.urlopen(r) as yanit:
        govde = yanit.read()
        return {"status": yanit.status,
                "json": json.loads(govde) if govde else {}}


def _sifrele(public_key_b64: str, deger: str) -> str:
    from nacl import encoding, public

    pk = public.PublicKey(public_key_b64.encode(), encoding.Base64Encoder())
    return b64encode(public.SealedBox(pk).encrypt(deger.encode())).decode()


def _env_oku(yol: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not yol.exists():
        return out
    for satir in yol.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if not satir or satir.startswith("#") or "=" not in satir:
            continue
        k, v = satir.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    token = Path(sys.argv[1]).read_text(encoding="utf-8").strip()
    env = _env_oku(Path(__file__).resolve().parent.parent / ".env")

    anahtar = _istek(f"/repos/{REPO}/actions/secrets/public-key", token)["json"]
    for ad in SECRETS:
        deger = env.get(ad)
        if not deger:
            print(f"  ATLANDI  {ad}  (.env'de yok)")
            continue
        try:
            r = _istek(f"/repos/{REPO}/actions/secrets/{ad}", token,
                       {"encrypted_value": _sifrele(anahtar["key"], deger),
                        "key_id": anahtar["key_id"]})
            print(f"  YAZILDI  {ad}  (HTTP {r['status']})")
        except urllib.error.HTTPError as e:
            print(f"  HATA     {ad}  (HTTP {e.code})")

    mevcut = _istek(f"/repos/{REPO}/actions/secrets", token)["json"]
    print("\nRepodaki secret adları:",
          ", ".join(s["name"] for s in mevcut.get("secrets", [])) or "(yok)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
