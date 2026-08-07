# STATE.md — Mevcut Durum

> Usta her oturumun başında bu dosyayı okur, sonunda günceller.
> KISA TUT: ~100 satırı aşınca eskiyi `ai/archive/STATE-YYYY-MM.md`'ye taşı.

**Son güncelleme:** 2026-08-07
**Aktif milestone:** **Faz 9 KAPANDI** (ADR **#015**, **#016**). Dış repo
incelemesi (Merdiven · borsaci · borsapy) 10 maddeye dönüştü, **10'u da
uygulandı**; yolda çıkan panel bulgusu da karara bağlandı.
Suite **1078 → 1185**. Şema **v6 → v9**.

## ✅ Tamamlananlar

**Faz 9 — karar anı katmanı** (2026-08-07) — ADR **#015**, **#016** ·
L-012/13/14/15
Rapor: `reports/repo-inceleme-2026-08-07.md` (34 satırlık karşılaştırma).
Bulgu: karar ÖNCESİ her boyutta öndeyiz, **karar ANINDA** 9 satırda "—" vardı.

| # | Ne | Ölçüm / kanıt |
|---|---|---|
| 1 | **Tavan/taban kilidi** — kilitli isimde plan ÜRETİLMEZ | canlı evren %0.97 kilit; EUPWR son 2y **23 kez** (%4.65) |
| 2 | **Kesitsel devre kesici** (`saglik`) | plan oranı %60 teli + ön kayıt tetikleyicisi; sinyal tek yön %70 |
| 3 | **OHLC iç tutarlılık** kalite kapısına | 197.191 barda **0 ihlal** → tel, temizlik değil |
| 4 | **Bilanço penceresi** (KAP beklenen bildirim) | canlı doğrulandı; 19 isim → 9 açık / 10 kapalı / **0 bilinmiyor** |
| 5 | **Sıralı eylem listesi** (rapor §0) | ADR #015 · skor YOK, sözlükbilimsel, seçimi değiştirmez |
| 6 | **Net R:R** (maliyet düşülmüş) | 58 geçmiş planın **19'u (%33)** net eşiğin altında |
| 7 | **Süreli veto** — koşuya değil takvime bağlı | `veto_suresi_gun`, işlem günü cinsinden, W-04 |
| 8 | **HF-32** — deterministik katman bir TAVANDIR | `plan_yok_sinifi ∈ {veri,limit}` iken boğa sinyali yasak |
| 9 | **Enjeksiyon savunması** — KAP metni veridir | `llm_io.dis_metin` + istemde açık ibare |
| 10 | **Bedelsiz kapsama ÖLÇÜMÜ** | yfinance kaçırmıyor (8/8) — ama 5 sahte bar buldu → **ADR #016** |

Yeni: `src/eylem.py` · `prices.limit_map` / `ohlc_ihlalleri` ·
`risk.limit_durumu` / `rr_net` · `news.sync_beklenen` / `beklenen_pencere` ·
`journal.aktif_vetolar` · `saglik.duzeltilmemis_kurumsal_tara` ·
migration v7/v8/v9.

**Dört ders yolda çıktı:** L-012 (naif grep kendi yorumunu yakalar — aynı gün
**iki kez**), L-013 (son 8 kayda bakıp "sapma ≤%0.06" demiştim; gerçek maks
**%1.796**), L-014 (kayan pencereli kontrol, pencerenin gerisindeki bozulmayı
onaylar), **L-015** (2026-08-06 otonom koşusu GitHub runner kapasitesinden hiç
başlamadı → Telegram bildirimi de çıkmadı; bir süreç kendi yokluğunu haber
veremez → `saglik`'e "atlanan koşu" kontrolü eklendi).

**Faz 8 — otonom koşu** (2026-08-01) — ADR **#013**, L-010/011 · İlk canlı tur
6/6 modelde düştü, sebep modeller değil GÖRÜNMEZ kurallardı; istem sözleşmeyle
hizalandıktan sonra ilk halka ilk denemede geçti. Telegram + EVDS canlı.

**Faz 0-7 + denetim** (2026-07-26 … 2026-07-29) — tam anlatım
`ai/archive/STATE-2026-07.md`. Özet: **ölçüm kapısı KAPALI** (#007), ön kayıtlı
revizyon **GEÇMEDİ** (#008) → sistem "izleme + risk disiplini + haber/veto".
Takvim iki kaynaktan (#012). Kurallar teste devredildi (#011).

## 🔨 Devam Edenler
- _(yok)_

## 🧱 Bloklar / Bekleyenler
- _(yok)_ — **Faz 8 KAPANDI.** Doğrulandı 2026-08-07: 5 secret 08-01'de
  yüklenmiş, cron hafta içi koşuyor (08-03/04/05 commit'leri), Test workflow
  yeni kodla yeşil. STATE bu maddede bayatmış, düzeltildi.

## 🎯 Sıradaki 3 İş

Üçü de **ZAMAN KAPILI** — yapılacak iş kalmadı, beklenecek olay var.

1. **İlk çözüm turu — 2026-08-26'dan sonra.** En yakın bariyer o tarihte;
   bugün `bist coz` doğru olarak 0 çözüyor (29 `plan_sec` tahminin hepsinin
   bariyeri ileride). DoD: bariyer dolunca `bist coz` çözüyor, ardından
   `bist degerlendir` KARIŞIK KAYNAK nedeniyle durup `--tool` istiyor (çıkış 2).
   ⚠ `araclar()` yalnız ÇÖZÜLMÜŞ tahminleri sayar; bugün hepsi `replay`
   olduğu için çıkış 0 — bu bir hata değil, o kapı henüz açılmadı.
2. **Faz 9'u ANALİSTLİ bir günde gör.** Deterministik zincir 2026-08-05
   verisiyle uçtan uca koşuldu (CI taklidi dahil, çıkış 0); kalan yalnız
   analist halkasıyla birlikte görmek. Elle iş yok, cron yapacak.
   DoD: bir sonraki `reports/gunluk_*.md` dosyasının **§0 listesinde** en az
   bir satır analist sinyaliyle (`AZALT — analist ...`) çıkıyor VE aynı gün
   `bist saglik` "atlanan koşu" satırı ✓ basıyor.
3. **`kirli_gozlem` ve `plan üretim oranı` sayaçlarını izle.** İkisi de
   `bist saglik`'te ve ölçüm raporunda basılıyor.
   DoD: haftada bir `bist saglik` çıktısına bakılıyor; `kirli_gozlem > 20`
   ya da `plan üretim oranı` ortalaması `< 2.0` görülürse STATE Backlog'undaki
   ilgili madde (sırasıyla ikinci kaynak kıyası · ön kayıtlı seviye turu)
   "devam eden"e taşınıyor.

_Not: `reports/olcum_2026-08-07.md` ADR #016 sonrası yeniden üretildi —
kirli gözlem sayısı raporun "Kapsama" bölümünde basılıyor._

## 📦 Backlog (şimdi değil, unutma da)
- ✅ **ÇÖZÜLDÜ — panel kirliliği** → **ADR #016**. 5 sahte bar (CCOLA
  2024-08-01 −%90.7 · TSPOR +%94.6 · AYGAZ +%72.5 · HEKTS −%64.8 / +%44.1)
  artık `backtest.bozuk_bar_mask` ile **gözlem düzeyinde** düşüyor; isim
  düşmüyor, evren 67'de kalıyor. Ölçüldü: alfa −0.861 → **−0.920pp**, hüküm
  HER dilimde aynı (`kenar yok`, kapı `[]`) → **ADR #007 ayakta**. Ön kayıt
  gerekmedi çünkü değişiklik sonucu KÖTÜLEŞTİRDİ (gerekçe ADR #016'da).
  ⚠ İzlenecek: `kirli_gozlem` sayısı 20'yi aşarsa kaynak sorunu demektir.
- **`poetry run bist` YEREL'de çalışmıyor**: klasör adındaki boşluk shebang'i
  kırıyor; çalışan biçim `poetry run python -m src.cli <komut>` (Actions temiz).
- **Net R:R kapıya alınsın mı?** ÖLÇÜLDÜ: 58 planın 19'u (%33) elenirdi.
  `min_rr_t1` `docs/on-kayit-seviye-02.md` §4'ün parametresi → **ön kayıt ister**;
  §3 tetikleyicileri oluşmadı (son 20 plan gününde ort. **2.10** isim, eşik 2.0 —
  sınıra çok yakın, `bist saglik` her gün basıyor).
- **Replay'i yeniden koş?** (#012) `asof 2024-12-18` bir gün geniş bariyerle
  çözüldü; yeniden koşmak journal'ı yeniden yazar → ayrı karar.
- **`high52_prox` hipotezi** — OOS'ta +1.61pp (t=1.81), IC 0.113 (t=2.42):
  34 karşılaştırmada çıtayı geçen TEK satır. Sonucu görüp seçmek p-hacking →
  AYRI ve ön kayıtlı tur hak ediyor. `volscaled_mom` katkı göstermedi (−0.22pp).
- **R:R'ın seçimle sağlanması** (#009): hedef sabit, eşitsizlik girişi aşağı
  iterek çözülüyor. `docs/on-kayit-seviye-02.md` HAZIR ama koşulmadı.
- **Ekonomik takvim (TCMB/TÜFE)** ve **ikinci fiyat kaynağı kıyası**
  (İş Yatırım vs yfinance) — repo incelemesinin #11 ve #12'si, ölçüm bekliyor.
- **Dump yerel↔Actions arası 4 satır oynuyor**: 197.191 satırın 4'ü,
  `turnover_try`'da SON BİT (macOS/Ubuntu SQLite 1 ULP farkı). Kovalanmadı.
- **Supabase aynası** — ADR #014: gerek YOK; git arşivi karşılıyor.
- **KAP dilim bölme derinliği** — tek gün tavanı aşarsa (derinlik 6) sayfalama.
  Beklenen-bildirim ucunun ayrı bir tavanı var (**2000**); 45 günlük pencere
  1863 kayıt veriyor, kırpılırsa SAKLANMIYOR.
- **Model zinciri sırası VERİYLE kurulmalı** (#013) — 3 ay sonra araç başına
  veto değeri/isabet ölçülünce. Suite CI süresi büyürse pahalı ölçümler ayrı
  markere (#011). 500 TL üstü fiyat adımı TEK İSİMLE ölçüldü (EGEEN).
