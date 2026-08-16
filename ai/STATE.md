# STATE.md — Mevcut Durum

> Usta her oturumun başında bu dosyayı okur, sonunda günceller.
> KISA TUT: ~100 satırı aşınca eskiyi `ai/archive/STATE-YYYY-MM.md`'ye taşı.

**Son güncelleme:** 2026-08-16
**Aktif milestone:** **Faz 12 KAPANDI** — 2026-08-15 bağımsız denetiminin
13 bulgusunun 12'si kapatıldı + kâğıt portföy (ADR **#019**) eklendi.
Suite **1251 → 1299**. Yeni dersler: L-021/022/023.

## ✅ Tamamlananlar

**Faz 12 — denetim düzeltmeleri + kâğıt portföy** (2026-08-16)

| # | İş | Kanıt |
|---|---|---|
| 1 | **Faz 11 canlıya alındı** | 08-14 kesitinde plan üretilen isim 5→9, sektör 3→7, kayıp 0 |
| 2 | **Endeks zincire bağlandı** (L-021) | `index_daily` 08-06'da donmuştu; gerçek veriyle 08-14'e çekildi, kontrol `KRİTİK → OK` |
| 3 | **Eylem listesi bugünkü vetoyu okuyor** (L-022) | 08-14 raporunda "YENİ GİRİŞ" bölümü kayboldu, 5 isim gerekçeli BEKLE'ye düştü |
| 4 | **Haftalık IC satırı** | `ic.get("n")` ≠ `n_donem`; `.get` sessizdi, satır hiç basılmıyordu |
| 5 | **Kâğıt portföy** (ADR #019) | 10.000 TL · üretim verisinde 9.970,99 TL (−0.29%), 2 açık / 1 kapandı |
| 6 | **Ölçüm hattı onarımı** (L-023) | `fwd_ret_20d` 24/24 NULL'du → 20 dolduruldu · `veto_value` 0 diyordu → 17 veto görünür · `llm_contribution` yapısal olarak asla dolmayacaktı → kesit 18 isme açıldı |
| 7 | **Örtüşme ayıklaması** | TUPRS çift sayımı: gemini-3.6-flash +5.46pp (n=3) → **+2.35pp (n=2)** |
| 8 | **IC dönem seti sonuç-koşullu değil** | Dönemler `outcomes`'tan değil `predictions`'tan |
| 9 | **Yarım bar koşusu ayrıldı** | `2026-07-29-claude-code-1` ölçümle yakalandı (18/18 sapan, ort −1.21%) |
| 10 | **Kaçan planın bedeli ölçülüyor** | replay: tetiklenmeyen +6.93pp vs tetiklenen +5.08pp → **+1.85pp** |

Her düzeltmenin kilidi **eski hata geri konarak** sınandı; toplam 14 test
kırmızıya döndü ve geri alınca yeşile döndü.

**Faz 11 — gizli hedef filtresi** (2026-08-12) — ADR **#018** · L-019/020.
**Faz 10 — kilitlenme ve denetim izi** (2026-08-11) — ADR **#017** · L-016/17/18.
**Faz 9 — karar anı katmanı** (2026-08-07) — ADR #015, #016 · L-012/13/14/15.
**Faz 8 — otonom koşu** (2026-08-01) — ADR #013, L-010/011.
**Faz 0-7 + denetim** (2026-07-26 … 07-29) — `ai/archive/STATE-2026-07.md`.
Özet: **ölçüm kapısı KAPALI** (#007), ön kayıtlı revizyon GEÇMEDİ (#008) →
sistem "izleme + risk disiplini + haber/veto". Kurallar teste devredildi (#011).

## 🔨 Devam Edenler
- _(yok)_

## 🧱 Bloklar / Bekleyenler
- _(yok)_

## 🎯 Sıradaki 3 İş

1. **Pazartesi (2026-08-17) koşusunu doğrula — beş düzeltmenin ilk gerçek sınavı.**
   Bakılacaklar: `index_daily` max = `bars_daily` max mı · raporun §0'ı analistin
   bugünkü vetosunu içeriyor mu · §1'de kâğıt karne var mı · Telegram'da 💼
   satırı geldi mi · sağlıkta "endeks tazeliği" OK mü.
   ⚠ Endeks adımı düşerse zincir durmaz ama boşluk 2 seansı geçerse `saglik`
   koşuyu KAPATIR — bu bilinçli, ama ilk kez canlıda sınanacak.
   DoD: beşi de gözlendi; sapma varsa STATE'e yazıldı.

2. **Rejim OR/AND asimetrisini karara bağla.** 2026-07-24'ten beri **11 koşunun
   11'i risk-off** ve XU100 SMA200'ün DAİMA üstünde (+5.7…+9.7%); tetikleyen tek
   koşul genişlik. Aynı 15 işlem gününde ölçüm evreni −1.48% → duruş bu dönemde
   pahalıya patlamadı, ama kural tartışılmadan sürüyor. Artık kâğıt portföy
   sayesinde **bedeli TL olarak ölçülebilir**: risk-off tavanı (maks 2) yüzünden
   alınamayan planlar `reddedilen` listesinde `kontenjan_dolu` olarak duruyor
   (üretimde TUPRS iki kez — karnedeki en iyi iki işlem).
   DoD: bir ADR — ya asimetri gerekçelendirilip kalır, ya ön kayıtlı bir tur açılır.

3. **`falsifier` ya sınansın ya kalksın.** Alan her tahminde toplanıyor,
   `journal.py` dışında **hiçbir yerde okunmuyor**, bazıları mantıken ters.
   Otomatik yön kontrolü bilerek yazılmamıştı (naif metin araması kendi yorumunu
   yakalar, L-012) — ama artık `fwd_ret_20d` dolu, yani "yanlışlayıcı gerçekleşti
   mi" sorusu bir ölçüme bağlanabilir.
   DoD: ya anlamlı bir HF kuralı ya da alanın kaldırılması (ikisi de karar).

## 📦 Backlog (şimdi değil, unutma da)
- **Analist katkısı ölçümü artık ÇALIŞIYOR ama veri bekliyor.** Üç bağımsız yol
  (sinyal↔`pct` monotonluğu · %93 gün gün değişmeme · 68 `avoid`'in 63'ü zaten
  `sma200_alti`) katkının ~sıfır olduğunu gösteriyor; `llm_contribution` artık
  bunu KARNEDE ölçebilir. Canlı ufuklar dolunca (≈2026-09) ilk gerçek sayı gelir.
- **Kâğıt portföy 20+ kapanmış işleme ulaşınca** `bist degerlendir`'e TL bazlı
  bölüm (ADR #019 "tekrar gözden geçir" b maddesi).
- **`levels_daily` birikmiyor** — dump'tan hariç + her koşuda DB yeniden kuruluyor.
- **`high52_prox` ↔ hedef filtresi gerilimi** — `zirveye_yakin` sınıfıyla görünür.
- **Ölçüm şablonundan düşen "ters yönde kanıt" uyarısı** — şablon regresyonu.
- **TÜFE serisi ÖLDÜ** — `TP.FE.OKTG01` son gözlem 2025-12-01 (258 gün).
  EVDS'de yeni seri kodunu bul (TÜİK 2026 baz revizyonu olabilir).
- **Net R:R kapıya alınsın mı?** 58 planın 19'u (%33) elenirdi → **ön kayıt ister**.
- **`high52_prox` hipotezi** — OOS +1.61pp (t=1.81), IC 0.113 (t=2.42); sonucu
  görüp seçmek p-hacking → AYRI ve ön kayıtlı tur.
- **R:R'ın seçimle sağlanması** (#009): `docs/on-kayit-seviye-02.md` HAZIR, koşulmadı.
- **Ekonomik takvim (TCMB/TÜFE)** ve **ikinci fiyat kaynağı kıyası** — ölçüm bekliyor.
- **Dump churn** — ölü koşular bile günde ~2.100 satır oynatıyor; acil değil.
- **KAP dilim bölme derinliği** — beklenen-bildirim ucu tavan 2000; 45 günlük
  pencere 1863 kayıt veriyor, kırpılırsa SAKLANMIYOR.
