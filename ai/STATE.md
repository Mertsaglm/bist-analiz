# STATE.md — Mevcut Durum

> Usta her oturumun başında bu dosyayı okur, sonunda günceller.
> KISA TUT: ~100 satırı aşınca eskiyi `ai/archive/STATE-YYYY-MM.md`'ye taşı.

**Son güncelleme:** 2026-07-27
**Aktif milestone:** v1 çalışıyor (Faz 0-7) · denetim uygulandı (#009/#010) ·
**kurallar teste devredildi (#011)**

## ✅ Tamamlananlar

**Faz 0-7 — v1 boru hattı** (2026-07-26 … 2026-07-27)
Ayrıntı `ai/archive/STATE-2026-07.md`'de. Özet:
veri → gösterge → faktör → seviye → plan → LLM sınırı (HF-01..HF-31) →
journal → resolver (üçlü bariyer) → değerlendirme → rapor + KAP/haber katmanı.
Ölçüm kapısı **KAPALI** (#007) ve ön kayıtlı revizyon turu **GEÇMEDİ** (#008) →
sistem "izleme + risk disiplini + haber/veto aracı" olarak çerçevelendi.

**Bağımsız denetim + düzeltmeler** (2026-07-27) — ADR **#009 · #010**, **L-007**
1 kritik + 5 yüksek + 22 düşük bulgu; 62 madde tek tek kodla sınandı ve
kapatıldı. Ortak imza: *kod doğru, veri sessizce dar/bayat, çıktı hâlâ
"geçerli" görünüyor.* Ölçülen etki, kanıtlar ve tam liste ADR #009/#010'da
(ör. pakete giren KAP bildirimi 12 → 141; kesit 16 → 67 isim; replay
tetiklenmeme %46.4 → %35.0). Yapısal eklemeler: `HF-31` · migration **v6** ·
`bist saglik` · `bist seviye` · `factor_daily`/`levels_daily`/`regime_daily`
artık gerçekten yazılıyor.

**İki VARSAYIM ölçüldü, biri YANLIŞ çıktı:** 1000+ TL tick adımı `1.00`
sanılıyordu → ölçüldü **2.50** (EGEEN, 735 fiyat). KAP geniş pencereyi
**sessizce kırpıyor** (90 gün istendi, 14 gün döndü) → çekim dilimleniyor.

**Test zırhı — kurallar koşulabilir hale getirildi** (2026-07-27) — ADR **#011**, **L-008**
Abonelik bitiyor; projeye bundan sonra bağlamı taşımayan modeller dokunacak.
Kuralların çoğu yorumda yazılıydı ve **hiçbir yerde zorlanmıyordu** — bir eşiği
gevşetmek, bir kolonu şemadan ayırmak ya da rejim politikasının yönünü ters
çevirmek suite'i kırmıyordu. Üç katmanlı test mimarisi kuruldu:
**sözleşme** (yapı ayakta mı) · **mekanizma** (doğru girdi/payda mı) ·
**uçtan uca** (zincir koşuyor mu). Sıfır testi olan 13 modül kapsandı.
Artık zorlanan şeyler: eşik zeminleri, kolon↔şema eşliği, LLM sınırı kümeleri,
katman disiplini, ön kayıt mührünün sha256'sı ve doküman↔kod atıfları.
`pytest` yan etkisiz: gerçek veritabanına yazan test hata veriyor.

**Test yazarken çıkan 3 kırılganlık düzeltildi** (`src/diagnose.py`): sıfıra
bölme · `0.0 or -1e9` sıralama tuzağı · `ic_uygun` için None koruması yokluğu.
Ayrıca `bist backtest`/`bist teshis` çıktısını kirleten numpy uyarısı susturuldu
ve dört yerde üst ucu 30'da kalmış denetim kodu aralığı güncellendi — 31 kontrol
varken kullanıcıya 30 diye anlatılıyordu (artık testle korunuyor).

## 🔨 Devam Edenler
- _(yok)_

## 🧱 Bloklar / Bekleyenler
- **EVDS_API_KEY yok** (`.env`). Makro katmanı hazır, veri boş. `macro.context()`
  eksik anahtarı sözlüğe HİÇ koymuyor → rapor satırı gizlenir, uydurma yok.
  Yan etki: eksik oranı %100 → rejim nakdi +10pp defansif kaydırıyor (bilinçli).
  Anahtar girilince: `bist makro backfill`.

## 🎯 Sıradaki 3 İş
1. **İlk gerçek LLM turu.** DoD: `bist gunluk → denetle → kaydet → rapor`
   uçtan uca koşuyor; rapor tez + veto taşıyor ve `bist degerlendir` karışık
   kaynak uyarısı verip `--tool` istiyor.
2. **Haber katmanını günlük akışa bağla.** DoD: `bist veri gunluk` sonrası
   `bist haber cek` çıkış kodu 0 ve `bist haber durum` "TAZE" diyor; bir gün
   atlanırsa paketteki `haber_taramasi.ok` false oluyor.
3. **`bist seviye` ölçümünü tüm evrende koş ve yorumla.** DoD: sonuç
   `reports/` altına yazılır ve "seviyeler yön iddiası taşıyor mu" sorusuna
   `edge_verdict` diliyle cevap verilir (tek hisse denendi, THYAO direnç
   −1.4pp çıktı — çoklu test uyarısıyla okunmalı).

## 📦 Backlog (şimdi değil, unutma da)
- **`high52_prox` hipotezi** — revizyon koşusunda tek başına OOS'ta +1.61pp
  (t=1.81), IC 0.113 (t=2.42): çıtayı geçen TEK satır. 34 karşılaştırma içinden
  sonucu görüp seçmek p-hacking olurdu → AYRI ve ön kayıtlı bir tur hak ediyor.
  Not: H=20 ile bu faktörün ağırlığı zaten 0'a çekiliyor.
- `volscaled_mom` OOS'ta katkı göstermedi (−0.22pp, IC t=0.74) — ağırlığı 0'a
  düşürmek için de ön kayıt gerekir.
- **R:R'ın seçimle sağlanması** (#009'da ifşa edildi, düzeltilmedi): hedef
  sabit, eşitsizlik girişi aşağı iterek çözülüyor. Mekanizmayı değiştirmek ön
  kayıt ister → `docs/on-kayit-seviye-02.md` HAZIR ama **koşulmadı**;
  tetikleyici koşullardan biri (20 günde ort. <2 plan · N≥30 çözülmüş tahmin ·
  evren genişlemesi) oluşmadan koşulmayacak.
- **KAP dilim bölme derinliği** — tek gün bile tavanı aşarsa (derinlik 6)
  sayfalama desteği araştırılmalı. Şu an 90 günde bir kez bölme yetti.
- Evren BIST-100 tamamına genişletilirse kesitsel dağılım artar; OOS N de 2+ yıl
  sonra artar. İkisi de aynı ön kaydın tekrar koşulmasını mümkün kılar.
- 500 TL üstü fiyat adımı TEK İSİMLE ölçüldü (EGEEN) — bandın tamamını temsil
  ettiği varsayımı sürüyor. `bist saglik` ikinci isim girdiğinde uyarıyor.
- ASTOR/EUPWR profilini 6 ayda bir yeniden doğrula (kısa geçmiş, yüksek vol).
- `data/*.sql` dump gitignore'da (15 MB türev veri). Faz 8'de Actions bağlanınca
  bu satır KALDIRILACAK — Actions kendi veritabanını sıfırdan kurar.
- Faz 8'de suite CI'da koşacak; süre büyürse pahalı ölçüm testleri ayrı bir
  pytest markerine alınır (#011'in "tekrar gözden geçir" maddesi).
- `Proje Yardımcısı/` klasöründe şablonun kendi README + `yeni-proje.sh`'si
  duruyor (Mert "kullanabilirsin" dedi, yerinde bırakıldı).
- **Faz 8:** GitHub Actions + Telegram.
