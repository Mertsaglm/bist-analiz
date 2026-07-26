# STATE.md — Mevcut Durum

> Usta her oturumun başında bu dosyayı okur, sonunda günceller.
> KISA TUT: ~100 satırı aşınca eskiyi `ai/archive/STATE-YYYY-MM.md`'ye taşı.

**Son güncelleme:** 2026-07-26
**Aktif milestone:** ✅ v1 TAMAM — Faz 0-6 bitti, sistem çalışır durumda

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

**Teşhis + ön kayıtlı revizyon turu #1** (2026-07-26)
- `diagnose.py` + `revizyon.py` + CLI (`bist teshis`, `bist revizyon`)
- Teşhis: ayrışma bug DEĞİL — sıralama bilgisinin **%79'u SMA200 kapısında**
  kayboluyor (`ic_tum` 0.042 t=2.42 → `ic_uygun` 0.009 t=0.20). Enstrüman sağlam.
- Ön kayıt koşudan ÖNCE mühürlendi: `docs/on-kayit-revizyon-01.md` sha `6677c296…`
- **Revizyon GEÇMEDİ:** OOS N=21, Δ=+0.81pp, t=0.89 → `kenar yok` (çıta 1.0pp).
  Yön düzeldi (−1.12pp → +0.81pp) ama çıtaya ulaşmadı. **İkinci tur yok.**
- Ayrıca üçüncü bir işaret-körlüğü bulundu ve düzeltildi: `diagnose.verdict`
  `ic>0` diye bakıyordu; IC=0.009 (t=0.20) "pozitif" sayılıyordu → artık t tabanlı.

**Faz 3 — plan üretici + risk + rejim** (2026-07-26)
- Modüller: `risk`, `levels`, `regime`, `planner` + CLI (`bist plan`).
  **214 test geçiyor.**
- Her plan `validate_option`'dan geçiyor; tüm fiyatlar ölçülmüş tick ızgarasında;
  stop [1.5,4.0]×ATR; hedefler YALNIZ gerçek pivot/52h zirvesinden.
- Yeniden çerçeveleme uygulandı: her plan `uyari` alanında
  "Ölçülen kenar yok (ADR #008) — planlama geometrisidir" taşıyor.
- Yol boyunca üç kusur bulundu ve düzeltildi:
  1. **EUPWR artefaktı:** fiyat ~90 TL iken 3 yıl önceki 32 TL seviyesi
     "destek retest" planı üretiyordu (R:R 6.39). → `maks_giris_uzakligi_atr: 3.0`
  2. **Yanıltıcı limit mesajı:** stop uzaklığı GİRİŞTEN, ulaşılabilirlik
     BUGÜNKÜ FİYATTAN ölçülüyordu — iki referans tek cümlede (L-003).
     → boşluk riski artık girişten ölçülüyor.
  3. **"Plan yok" gerekçesi tek cümleye sıkışmıştı** — "zirvede, hedef yok" ile
     "R:R yetmedi" farklı olgular. → `build_options` artık sebebi döndürüyor.
- Ölçülen tasarım gerçeği: risk %1 + tavan %10 ile stop <%10 olan her planda
  TAVAN BAĞLIYOR; volatilite hedeflemesi pratikte atıl, gerçekleşen risk
  ~%0.6-0.9. Bilinçli muhafazakârlık olarak bırakıldı, koda not düşüldü.

**Faz 4 — journal + resolver + replay** (2026-07-27)
- Modüller: `journal`, `resolver`, `replay` + CLI (`bist replay`, `bist journal`,
  `bist coz`). **248 test geçiyor.**
- Boru hattı LLM OLMADAN uçtan uca koşuyor: `bist replay 2024-01-01 → 2026-06-30`
  → 30 dönem, 28 tahmin, 28'i çözüldü, 0 açık.
- Sonuç dağılımı: giris_olmadi 13 · hedef 5 · stop 5 · sure 4 · iptal_kurumsal 1
- **%46'sı hiç tetiklenmemiş** — plan tasarımı hakkında gerçek bilgi (geri
  çekilme girişleri sık sık dolmuyor).
- ⚠ Replay'in ortalama alfası +3.62pp (N=14) BULGU DEĞİLDİR: vekil analistle,
  `edge_verdict` çıtasının (N≥15) altında. Faz 6 buna "ölçüm yetersiz" diyecek.
- Yol boyunca iki kusur: (1) journal hata mesajı FK ihlalini "değişmezlik
  ihlali" diye raporluyordu (yine L-003) → ayrıştırıldı ve plan referansı
  önceden doğrulanıyor; (2) `referans['close']` eksikse çıplak NOT NULL hatası
  veriyordu → açık gerekçeli hata.

**Faz 5 — LLM sınırı + denetim** (2026-07-27)
- Modüller: `schema`, `llm_io`, `audit` + CLI (`bist gunluk/denetle/kaydet`).
  **289 test geçiyor.**
- Boru hattı tam: `gunluk` → paket (bundle.json + context.md + prompt.md) →
  IDE'de analiz → `denetle` (HF-01..HF-30) → `kaydet` (journal).
- **DoD karşılandı:** her HF kodu tek tek tetiklendi (30 test). Canlı doğrulama:
  plan_id uydur → HF-12 · sayı uydur → HF-17 · sha boz → HF-02 · sayısal güven → HF-09.
- Yol boyunca DÖRT kusur bulundu ve düzeltildi:
  1. **HF-17'de gerçek delik:** `_varyantlar` yuvarlayarak biçim üretiyordu,
     uydurma "47.3" değeri "47" varyantı doğurup pakette 47.00 varsa denetimi
     ATLIYORDU → artık yalnız değeri değiştirmeyen biçimler.
  2. `build_bundle` faktör skorlarını pakete hiç koymuyordu → HF-22 üretimde
     ASLA ateşlenemezdi, `bist kaydet` NOT NULL ile patlıyordu.
  3. Paket Türkçe anahtar (`skor`), journal İngilizce (`score`) bekliyordu →
     tek yerde eşleme (`llm_io.faktor_to_journal`).
  4. **Migration tuzağı:** SQLite `ALTER TABLE RENAME` diğer tabloların FK'sını
     da yeniden yazıyor; v3 `outcomes`'u silinmiş tabloya bağladı → `legacy_
     alter_table = ON` + onarım migration'ı v4. Testler yakaladı.

**Faz 6 — değerlendirme + rapor** (2026-07-27)
- Modüller: `evaluate` + rapor/CLI (`bist degerlendir`, `bist rapor`, `bist portfoy`).
  **302 test geçiyor.**
- **DoD karşılandı:** `bist degerlendir` N=14'te 3.62pp'ye rağmen
  **"ölçüm yetersiz (N=14)"** diyor; sentetik-alfa testi bunu sabitliyor.
- Günlük rapor **AZALT bölümüyle başlıyor** (ölçüm: alt kuyruk üst kuyruğun
  1.8 katı; retail açığa satamaz → en savunulabilir çıktı "hangisini azalt").
- İki kusur: (1) IC hükmü `edge_verdict` kullandığı için t=1.46'da bile
  "zayıf kanıt" diyordu → `ic_verdict` ile ANLAMLILIĞA bakılıyor; (2)
  `bist degerlendir` taze kurulumda panel yokken ÇÖKÜYORDU → "ölçülemez" bir
  durum, hata değil.

## 🔨 Devam Edenler
- _(yok — v1 tamam)_

## 🧱 Bloklar / Bekleyenler
- **EVDS_API_KEY yok** (`.env`). Makro katmanı kod olarak hazır ama veri boş;
  `macro.context()` eksik anahtarı SÖZLÜĞE HİÇ KOYMUYOR, rapor satırı gizlenecek
  (uydurma yok). Anahtar girilince: `bist makro backfill`.

## 🎯 Sıradaki 3 İş
1. **Faz 6 — değerlendirme + rapor.** DoD: `bist degerlendir` ilk gün
   "ölçüm yetersiz" demek ZORUNDA; sentetik-alfa testi bunu sabitliyor.
3. **Faz 7-8 (opsiyonel):** KAP/haber katmanı, GitHub Actions + Telegram.

## 📦 Backlog (şimdi değil, unutma da)
- `data/*.sql` dump şu an **gitignore**'da (15 MB türev veri, 3 dakikada yeniden
  üretiliyor). Faz 8'de Actions bağlanınca bu satır KALDIRILACAK — Actions kendi
  veritabanını sıfırdan kurar, arşivin repoda olması gerekir.
- `Proje Yardımcısı/` klasöründe şablonun kendi README + `yeni-proje.sh`'si duruyor
  (Mert "kullanabilirsin" dedi, yerinde bırakıldı).
- **`high52_prox` hipotezi** — revizyon koşusunda tek başına OOS'ta +1.61pp
  (t=1.81), IC 0.113 (t=2.42) verdi, yani çıtayı geçen TEK satır. 34
  karşılaştırma içinden sonucu görüp seçmek p-hacking olacağı için bugünkü
  karara GİRMEDİ. Gelecekte AYRI ve ön kayıtlı bir tur hak ediyor.
- `volscaled_mom` OOS'ta katkı göstermedi (−0.22pp, IC t=0.74) — ağırlığı
  0'a düşürmek için de ön kayıt gerekir.
- Evren BIST-100 tamamına genişletilirse kesitsel dağılım artar; OOS N de
  2+ yıl sonra artacak. İkisi de aynı ön kaydın tekrar koşulmasını mümkün kılar.
- 500 TL üstü fiyat adımı ölçülemedi (evrende gözlem yok) — bir hisse o banda
  girerse önce yeniden ölç.
- ASTOR/EUPWR profilini 6 ayda bir yeniden doğrula (kısa geçmiş, yüksek vol).
- Faz 7 KAP/haber (KAP 308 yönlendirme döndürüyor), Faz 8 Actions + Telegram.
