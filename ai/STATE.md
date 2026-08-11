# STATE.md — Mevcut Durum

> Usta her oturumun başında bu dosyayı okur, sonunda günceller.
> KISA TUT: ~100 satırı aşınca eskiyi `ai/archive/STATE-YYYY-MM.md`'ye taşı.

**Son güncelleme:** 2026-08-11
**Aktif milestone:** **Faz 10 KAPANDI** (ADR **#017** · L-016/17/18).
Bağımsız denetim, sistemin **dört işlem günüdür ölü** olduğunu buldu; kilit
açıldı, kalıcı çözüm uygulandı ve canlı doğrulandı. Suite **1193 → 1226**.
Şema **v9 → v11**.

## ✅ Tamamlananlar

**Faz 10 — kilitlenme ve denetim izi** (2026-08-11) — ADR **#017**

Bulgu: sistem 2026-08-06'dan beri sıfır analiz üretiyordu. Kod doğruydu,
1193 test yeşildi, veri her gün çekiliyordu. **Kırılan şey modüller arası
varsayımdı:** L-015'in "atlanan koşu" kontrolü `MAX(predictions.asof)`e bakıp
KRİTİK dönüyordu, `predictions` ise kapının ARKASINDA yazılıyordu → kilit
kalıcı (L-016).

| # | Ne | Kanıt |
|---|---|---|
| 1 | **KAPI ↔ GÖZLEM ayrımı** — gözlem kontrolü kapıyı kapatamaz | `ekle_gozlem` şiddeti kodda tavanlar; eski hata geri konunca **7 test kırmızı** |
| 2 | **`otonom_kosu` heartbeat** (şema v10) — koşunun EN BAŞINDA yazılır | kapı kapansa bile kayıt duruyor (`test_HEARTBEAT_kapi_kapansa_bile_yazilir`) |
| 3 | **Nöbetçi** — L-015'in niyeti DIŞARIDA uygulandı | `nobetci.yml` canlı koştu: "✅ son koşu 2026-08-11" |
| 4 | **Yarım bar koruması** | kurtarma koşusunda **70 yarım bar** gerçekten elendi — hata aktifmiş |
| 5 | **Çıktı mührü** `output_sha` (şema v11) + run'a özel dosya | 2026-07-30'da journal ile dosya ayrışmıştı (farklı model, farklı plan) |
| 6 | **Makro zinciri + EVDS tazeliği** | TÜFE **253 gündür** donmuş çıktı; değer artık pakete girmiyor |
| 7 | **Payda görünürlüğü** | "alfa 4.27pp (girişi olan **13/20**) · karar başına 2.78pp" |
| 8 | **`test.yml` günlük cron** | otonom push workflow tetiklemiyor; suite 08-07'den beri hiç koşmamıştı |

**Kurtarma koşusu (2026-08-11) uçtan uca tamamlandı** ve canlı karne başladı:
`bist coz` altı gündür bekleyen 4 sonucu yazdı — TUPRS ×2 **HEDEF**
(+12.56% / +10.61%), KRDMD ×2 **STOP** (−5.69% / −7.06%). Hiçbir sonuç
kaybolmamıştı; resolver bar verisinden geriye dönük çözdü.

**Faz 9 — karar anı katmanı** (2026-08-07) — ADR #015, #016 · L-012/13/14/15.
Dış repo incelemesinin 10 maddesi uygulandı. Rapor:
`reports/repo-inceleme-2026-08-07.md`.

**Faz 8 — otonom koşu** (2026-08-01) — ADR #013, L-010/011.
**Faz 0-7 + denetim** (2026-07-26 … 07-29) — `ai/archive/STATE-2026-07.md`.
Özet: **ölçüm kapısı KAPALI** (#007), ön kayıtlı revizyon GEÇMEDİ (#008) →
sistem "izleme + risk disiplini + haber/veto". Kurallar teste devredildi (#011).

## 🔨 Devam Edenler
- _(yok)_

## 🧱 Bloklar / Bekleyenler
- _(yok)_

## 🎯 Sıradaki 3 İş

1. **Zincirin KENDİ BAŞINA iki gün koştuğunu gör.** Kilit açıldı ama kanıtı
   elle koşulmuş tek bir tur. DoD: 2026-08-12 ve 08-13 akşamları `gunluk.yml`
   yeşil bitiyor, Telegram'a rapor düşüyor, ve `bist saglik` "atlanan koşu"
   satırı ✓ basıyor (bugün "heartbeat boş" diyor — ikinci koşudan sonra
   gerçek karşılaştırma başlar). Elle iş yok, cron yapacak.
2. **Replay'in +4.27pp'si GEOMETRİDEN mi geliyor?** Panel ölçümü aynı seçim
   için −0.92pp derken replay +4.27pp diyor; fark limitli girişten olabilir
   (planların %35'i hiç dolmuyor). DoD: `backtest`'e "t+1 açılışta piyasa
   emri" varyantı eklenip aynı dönemlerde koşuluyor; fark bir satır olarak
   `reports/olcum_*.md`'ye giriyor. **Ön kayıt gerekmez** — mevcut bir sayının
   kaynağını ayrıştırıyor, yeni bir kenar iddiası aramıyor.
3. **Veto değeri ölçümünü ÖNE AL.** Backlog'da "3 ay sonra" yazıyordu; canlı
   pencerede veto edilenler seçilenleri **+5.76pp** geçti (n=6, anekdot —
   TUPRS 08-05'te `tez_zayif` ile vetolandı ve dört günde +%17 yaptı).
   DoD: vetolanan isimlerin PLANSIZ ileri getirisi `outcomes`'a benzer bir
   yapıda izlenmeye başlıyor; `bist degerlendir` "Veto" bölümünde
   "ölçülemez" yerine bir sayı basıyor.

## 📦 Backlog (şimdi değil, unutma da)
- **TÜFE serisi ÖLDÜ** — `TP.FE.OKTG01` son gözlem 2025-12-01 (253 gün).
  Tazelik kontrolü artık bunu her gün basıyor ve değer pakete girmiyor.
  Yapılacak: EVDS'de serinin yeni kodunu bul (TÜİK 2026 baz revizyonu
  olabilir) ve `config.sources.evds.series.tufe`'yi güncelle.
- **`falsifier` toplanıyor ama HİÇ sınanmıyor.** `journal.py` dışında kodda
  hiçbir yerde okunmuyor; bazıları mantıken ters (`avoid` için "düşerse tez
  çürür"). Otomatik yön kontrolü BİLEREK yazılmadı: naif metin araması kendi
  yorumunu yakalar (L-012). Ya anlamlı bir HF kuralı ya da alanın kaldırılması.
- **Analist katmanının katkısı ~sıfır ölçüldü** (canlı 90 tahmin): sinyal,
  deterministik yüzdeliğin monoton fonksiyonu (avoid 10.5 → accumulate 77.4).
  ADR #013'ün "hangi model daha iyi" ölçümü artık araç başına veri topluyor.
- **`bist portfoy ekle` kullanılmıyor** → kontenjan ve "azalt" bölümü kör.
  Rapor ve `bist saglik` artık bunu her gün yazıyor.
- **Net R:R kapıya alınsın mı?** 58 planın 19'u (%33) elenirdi. `min_rr_t1`
  `docs/on-kayit-seviye-02.md` §4'ün parametresi → **ön kayıt ister**.
- **`high52_prox` hipotezi** — OOS'ta +1.61pp (t=1.81), IC 0.113 (t=2.42):
  34 karşılaştırmada çıtayı geçen TEK satır. Sonucu görüp seçmek p-hacking →
  AYRI ve ön kayıtlı tur hak ediyor.
- **R:R'ın seçimle sağlanması** (#009): `docs/on-kayit-seviye-02.md` HAZIR
  ama koşulmadı.
- **Ekonomik takvim (TCMB/TÜFE)** ve **ikinci fiyat kaynağı kıyası** —
  repo incelemesinin #11 ve #12'si, ölçüm bekliyor.
- **Dump churn** — ölü koşular bile günde ~2.100 satır oynatıyor
  (`SATIR_KUME=500`). Repo 17,6 MB; acil değil, bir yıl sonra konuşulur.
- **KAP dilim bölme derinliği** — beklenen-bildirim ucunun tavanı 2000;
  45 günlük pencere 1863 kayıt veriyor, kırpılırsa SAKLANMIYOR.
- **Model zinciri sırası VERİYLE kurulmalı** (#013) — araç başına ölçüm
  2026-08-11'de fiilen başladı (replay 20 · gemini-3.6-flash 3 · claude-code 1).
