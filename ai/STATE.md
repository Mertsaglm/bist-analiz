# STATE.md — Mevcut Durum

> Usta her oturumun başında bu dosyayı okur, sonunda günceller.
> KISA TUT: ~100 satırı aşınca eskiyi `ai/archive/STATE-YYYY-MM.md`'ye taşı.

**Son güncelleme:** 2026-07-26
**Aktif milestone:** 🛑 **Faz 2 kapısı KAPALI — karar Mert'te** (bkz. DECISIONS #007)

## ✅ Tamamlananlar

**Faz 0 — iskelet** (2026-07-26)
- Kural dosyaları alt klasörden **köke taşındı** (L-004)
- `config.yaml` (tüm eşikler + gerekçeleri), `universe.yaml` (18 hisse, hepsi canlı ölçüldü),
  `holidays_tr.yaml`, poetry + Python 3.12.13 ortamı
- Ölçüme dayanan 4 ADR: #002 taban çizgisi, #003 sektör nötr, #004 iki döngü + IC, #005 LLM sayı üretmez
- Eski `bist-coach` skill'i `~/.claude/skills/_arsiv/` altına taşındı (silinmedi)

**Faz 1 — veri temeli** (2026-07-26)
- Modüller: `util`, `db`+`migrations`, `calendar_bist`, `sources/yf`, `sources/evds`,
  `prices`, `universe`, `macro`, `dbdump`, `logging_setup`, `cli`
- Veri yüklendi: **50.942 bar** (19 ticker × ~2946), 14.542 endeks/kur barı, 461 kurumsal işlem
- **83 test geçiyor**

**Faz 1'de ölçülen üç şey** (hepsi hafızadan değil, veriden):
1. **Yahoo BIST tatillerinde HAYALET bar üretiyor** → ADR #006. Ayıklama ölçütü
   üç koşulun birleşimi; 841 hayalet silindi, 142+63 gerçek bar korundu.
   Sonuç: sıfır-hacim oranı 18 ticker'da %1.2 → **%0.0**, bayat kapanış 3 → 1.
2. **Fiyat adımı tablosu TEYİT EDİLDİ** — web kaynağından değil, kendi verimizden.
   Son kurumsal işlem sonrası 4.372 düzeltilmemiş bar: 0-20→1kr, 20-50→2kr,
   50-100→5kr, 100-250→10kr, 250-500→25kr. 500 TL üstü **ölçülemedi (varsayım)**.
3. **Seans saatleri TEYİT EDİLDİ** — 09:40 emir toplama / 10:00-18:00 kesintisiz
   sürekli işlem (öğle arası 2016'da kaldırıldı) / 18:10 kapanış.

**Faz 1 DoD — hepsi karşılandı:**
- `bist veri backfill` → 19 ticker × ~2946 bar + XU100/XU030/XBANK/XUSIN/USDTRY ✓
- `bist veri kalite` → SASA %45.2 sıfır hacimle eleniyor, 18/19 geçiyor ✓
- `bist takvim` → 2026'da 146 hafta içi gün / 137 işlem günü; eksik 9 gün tatil
  listesiyle **birebir**; `+20 → ters kontrol 20` ✓
- `bist db dump` iki kez → **birebir aynı dosya** (sha 57df150f…) ✓
- Seans saatleri ve fiyat adımları teyitli ✓

**Faz 2 — ölçüm harness'i** (2026-07-26)
- Modüller: `stats`, `indicators`, `factors`, `backtest`, `report` + CLI
  (`bist gosterge`, `bist backtest`). **134 test geçiyor.**
- Ölçüm evreni 67 hisseye çıkarıldı (`universe.yaml → olcum_evreni`); canlı
  evren 18'de kaldı. 16 isimle kesitsel sıralama ÖLÇÜLEMİYOR.
- **KAPI KAPALI** — OOS'ta pozitif kanıt yok; `bist backtest` çıkış kodu 2.
- Yol boyunca iki harness hatası bulundu ve düzeltildi (dönem düşürme yanlılığı,
  işarete kör kapı) — ikisi de sonucu değiştirdi. Ayrıntı: DECISIONS #007.
- Rapor: `reports/olcum_2026-07-26.md`

## 🔨 Devam Edenler
- **Karar bekliyor:** kapı kapalı. Üç seçenek Mert'e sunuldu —
  (A) ön kayıtlı sınırlı revizyon turu, (B) "izleme + disiplin aracı" olarak
  yeniden çerçeveleme, (C) dur. Plan gereği Faz 3-6'ya GEÇİLMEDİ.

## 🧱 Bloklar / Bekleyenler
- **EVDS_API_KEY yok** (`.env`). Makro katmanı kod olarak hazır ama veri boş;
  `macro.context()` eksik anahtarı SÖZLÜĞE HİÇ KOYMUYOR, rapor satırı gizlenecek
  (uydurma yok). Anahtar girilince: `bist makro backfill`.

## 🎯 Sıradaki 3 İş
1. **Mert'in kapı kararı** — A / B / C. Bu cevaplanmadan kod yazılmaz.
2. (A seçilirse) **Ön kayıtlı revizyon turu.** Varyantlar ÖNCEDEN yazılır,
   sonra koşulur, `bonferroni_note` uygulanır. Ölçümün işaret ettiği üçlü:
   SMA200 kapısını kaldır · ana ufuk H=42 · kısa vadeli tersine dönüş işareti.
   DoD: OOS'ta POZİTİF `zayıf kanıt` var mı — evet/hayır, tek turda.
3. (Karar ne olursa olsun) **Faz 3-6 altyapısı** yine kurulacak; değişen tek şey
   çıktının DİLİ: kenar iddiası mı, "planlama geometrisi + disiplin" mi.

## 📦 Backlog (şimdi değil, unutma da)
- `data/*.sql` dump şu an **gitignore**'da (15 MB türev veri, 3 dakikada yeniden
  üretiliyor). Faz 8'de Actions bağlanınca bu satır KALDIRILACAK — Actions kendi
  veritabanını sıfırdan kurar, arşivin repoda olması gerekir.
- `Proje Yardımcısı/` klasöründe şablonun kendi README + `yeni-proje.sh`'si duruyor
  (Mert "kullanabilirsin" dedi, yerinde bırakıldı).
- `volscaled_mom` faktörü ÖLÇÜLMEDİ — ağırlığı 0.10'da sabit; Faz 2 OOS'unda katkı
  göstermezse 0'a düşür.
- 500 TL üstü fiyat adımı ölçülemedi (evrende gözlem yok) — bir hisse o banda
  girerse önce yeniden ölç.
- ASTOR/EUPWR profilini 6 ayda bir yeniden doğrula (kısa geçmiş, yüksek vol).
- Faz 7 KAP/haber (KAP 308 yönlendirme döndürüyor), Faz 8 Actions + Telegram.
