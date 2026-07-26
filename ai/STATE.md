# STATE.md — Mevcut Durum

> Usta her oturumun başında bu dosyayı okur, sonunda günceller.
> KISA TUT: ~100 satırı aşınca eskiyi `ai/archive/STATE-YYYY-MM.md`'ye taşı.

**Son güncelleme:** 2026-07-26
**Aktif milestone:** Faz 0 — İskelet ve kural dosyaları

## ✅ Tamamlananlar
- 2026-07-23 — Usta sistemi kuruldu (AGENTS.md + ai/ hafıza katmanı + IDE köprüleri)
- 2026-07-26 — Proje planı yazıldı ve onaylandı → `~/.claude/plans/bist-hisse-analiz-ve-sparkling-toucan.md`
- 2026-07-26 — **Ön ölçümler yapıldı** (canlı yfinance, 2016-2026). Altı tasarım
  varsayımı çürüdü; kararlar DECISIONS #002-#005'e yazıldı. Özet:
  - EW sepet vs XU100 = +0.36pp/15g, t=2.89 → **XU100 taban olamaz** (#002)
  - Sektör nötralizasyonu 6-1 mom t'sini 1.86 → 0.62 yapıyor → **kapalı** (#003)
  - H=5'te kenar sıfır (−0.01pp, t=−0.05); H=21'de t=2.07 → **bariyer 20 gün**
  - Alt kuyruk (−1.03pp) üst kuyruğun 1.8 katı → **rapor "azalt" ile başlar**
  - yfinance temettü/bölünme düzeltmesi ÇALIŞIYOR; gerçek kusur SASA %23.2 sıfır hacim (L-005)
  - `required_n` ≈ 193 dönem ≈ 11,5 yıl → **getiri kenarı kanıtlanamaz** (PROJECT.md)
- 2026-07-26 — Kural dosyaları `Proje Yardımcısı/` alt klasöründen **köke taşındı** (L-004)
- 2026-07-26 — `config.yaml`, `universe.yaml` (18 hisse, hepsi canlı doğrulandı),
  `holidays_tr.yaml`, `pyproject.toml`, `.gitignore` yazıldı

## 🔨 Devam Edenler
- Faz 0 kalanı: `git init` + ilk commit, README.md, eski `bist-coach` skill'ini arşivle

## 🧱 Bloklar / Bekleyenler
- **DOĞRULA (Faz 1 DoD):** `config.yaml` içinde iki blok resmî kaynağa karşı teyit edilmedi —
  BIST seans saatleri ve fiyat adımı (tick) tablosu. Teyide kadar bunlara dayanan plan "taslak".
- **EVDS_API_KEY** gerekli (`.env`). Yoksa makro katmanı null döner ve rapor satırı gizlenir
  (uydurma yapılmaz — gold #006 A kültürü).

## 🎯 Sıradaki 3 İş
1. Faz 0'ı kapat: `git init` + `.env.example` + README.md + ilk commit — DoD: `git log` ilk
   commit'i gösteriyor **ve** yeni bir oturumda `/durum` yazınca gerçekten bu dosya okunuyor
   (L-004'ün kendi kuralı: dosyanın varlığını görmek YETMEZ)
2. Faz 1 — veri temeli: `util`, `db`+`migrations`, `calendar_bist`, `sources/yf`, `prices`,
   `macro` — DoD: 18 ticker × 10 yıl backfill, veri kalite raporu SASA'yı bayraklıyor,
   `bist db dump` iki kez çalıştırılınca birebir aynı dosya
3. Faz 2 — **ölçüm harness'i (KAPI)** — DoD: backtest raporu EW ve XU100 tabanlarını ayrı
   basıyor, `required_n` ve `edge_verdict` her satırda. **OOS'ta hiçbir faktör "zayıf kanıt"a
   ulaşmazsa Faz 3-6'ya GEÇME** — projeyi yeniden çerçevele.

## 📦 Backlog (şimdi değil, unutma da)
- `Proje Yardımcısı/` klasöründe şablonun kendi `README.md` + `yeni-proje.sh`'si kaldı.
  Ana kopya `projeler/Proje Yardımcısı - Orijinal dosya`'da duruyor — bu klasör silinebilir,
  **Mert'e sorulacak** (untracked dosya silmek geri alınamaz).
- Faz 7 — KAP/haber katmanı (KAP 308 yönlendirme döndürüyor, takip gerekli)
- Faz 8 — GitHub Actions + Telegram (kod buna hazır yazılıyor, şimdi bağlanmıyor)
- `volscaled_mom` faktörü ÖLÇÜLMEDİ — ağırlığı 0.10'da sabit; Faz 2 OOS'unda katkı
  göstermezse 0'a düşür
- ASTOR/EUPWR profilini 6 ayda bir yeniden doğrula (kısa geçmiş, yüksek vol)
