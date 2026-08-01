# STATE.md — Mevcut Durum

> Usta her oturumun başında bu dosyayı okur, sonunda günceller.
> KISA TUT: ~100 satırı aşınca eskiyi `ai/archive/STATE-YYYY-MM.md`'ye taşı.

**Son güncelleme:** 2026-08-01
**Aktif milestone:** **Faz 8 kodu TAMAM** (#013) — otonom koşu + model zinciri
+ Telegram + repo arşivi. Kurulum adımları (bot, secret, ilk push) BEKLİYOR.

## ✅ Tamamlananlar

**Faz 8 — otonom koşu** (2026-08-01) — ADR **#013**, **L-010**
Tek komut: `bist otonom gunluk` → takvim kapısı → veri → **gösterge** → haber
→ sağlık (KRİTİK ise DURUR) → paket → **analist zinciri** → çözüm → rapor +
Telegram. Kritik adımlar `(veri, gosterge, saglik, rapor)`; analist ve haber
bilerek dışarıda — düşseler de o günün plan geometrisi üretilir.
Yeni: `src/analist.py` (zincir) · `src/telegram_bist.py` · `src/otonom.py` ·
`src/saglik.py` (CLI'dan çıkarıldı, katman disiplini) · 3 workflow ·
`scripts/set_secrets.py`. **Suite 989 → 1078.**

Zincir ücretsizden ücretliye, OpenAI daima sonda (`config.llm.zincir`).
Maliyet GERÇEK paketle ölçüldü (girdi ~10K, çıktı ~8.2K token) → ay tavanı
**~$3**; PROJECT.md bütçe kısıtı buna göre revize edildi. `tool` alanını KOD
yazar, model değil.

**Uygulama sırasında çıkan üç bulgu** (ayrıntı ADR #013): (1) **L-010** —
sağlık kontrollerinin üçü de `MAX(bars_daily.date)`e bakıyordu, barlar
bayatlarsa hepsi TEMİZ diyordu; `bar tazeliği` eklendi. (2) Dump **52.3 →
32.9 MB** (satır başına tekrarlanan INSERT başlığı 16.7 MB'mış). (3) Testler
kullanıcının repo'suna yazmış — `telegram.outbox_file` conftest'in taşıdığı
blokta değildi (L-008 simetrisi); düzeltildi ve teste devredildi.

**İLK CANLI OTONOM TUR** (2026-08-01) — **L-011**
Zincir mekanik olarak kusursuz koştu ama önce **6/6 model denetimden düştü** —
sebep modellerde değildi: istem, denetimin zorladığı kuralların çoğunu
söylemiyordu (HF-26 altı modelde de patladı). İstem sözleşmeyle hizalandı +
çıktı token tavanı eklendi (`gemini-3.5-flash` 17K karakterde sessizce
kesiliyordu). Sonuç: **ilk halka ilk denemede geçiyor**; 18 tahmin journal'da
(`2026-07-30-gemini-3.6-flash-1`). Not: Pro halkaları ücretsizde **429** veriyor.

**Telegram + makro canlı** (2026-08-01)
Yeni bot açıldı, `bist bildir --test` mesaj düşürdü; `bist bildir --chat-id`
eklendi. EVDS girildi: **8.130 satır** makro; belgelenen davranış doğrulandı —
eksik oranı %100 → **%0**, rejim nakdi %90 → **%80**.

**İlk ELLE LLM turu** (2026-07-29) — **L-009**
`claude-code`, denetim ilk seferde temiz, 18 tahmin (2 `plan_sec`, 2 veto).
Bulgu: akışta `gosterge` yoktu → boş ama şeklen geçerli paket; Faz 8'de çözüldü.

**Takvim iki kaynaktan** (2026-07-29) — ADR **#012** · yfinance 07-24 ve
07-28'i üç endekste atlamış, 70 hisse işlem görmüştü. Ölçüm: endeks boşluğu
10 gün / 67-70 hisse · tatil 12 gün / 0 hisse → "endeks barı VEYA ≥10 hisse".

**Faz 0-7 + denetim + test zırhı** (2026-07-26 … 2026-07-27)
Tam anlatım `ai/archive/STATE-2026-07.md`'de; kararlar ADR #001-#011'de. Özet:
v1 boru hattı (veri → gösterge → faktör → seviye → plan → LLM sınırı → journal
→ resolver → değerlendirme → rapor + KAP). **Ölçüm kapısı KAPALI** (#007) ve
ön kayıtlı revizyon turu **GEÇMEDİ** (#008) → sistem "izleme + risk disiplini
+ haber/veto aracı". Bağımsız denetim (#009/#010, L-007): 1 kritik + 5 yüksek
bulgu, ortak imza *kod doğru, veri sessizce dar, çıktı hâlâ geçerli görünüyor*.
Kurallar teste devredildi (#011, L-008): sözleşme · mekanizma · uçtan uca.

## 🔨 Devam Edenler
- _(yok)_

## 🧱 Bloklar / Bekleyenler
- 🔑 **Faz 8 kurulumu — son iki adım.** ✅ bot · ✅ EVDS · ✅ Gemini · ✅ private
  repo · ✅ ilk canlı otonom tur. Kalan: (1) secret'ları yükle
  (`python scripts/set_secrets.py <pat_dosyasi>` — PAT dosyadan okunur,
  komut satırına yazılmaz), (2) `gunluk.yml`'yi Actions'ta
  `workflow_dispatch` ile elle tetikleyip yeşil gördükten sonra cron'a bırak.

## 🎯 Sıradaki 3 İş
1. **Faz 8'i canlıya al.** DoD: `workflow_dispatch` ile tetiklenen koşu
   Actions'ta yeşil; repoda yeni commit (`data/bist.sql`, `reports/`, `llm/`);
   Telegram'a özet düşüyor ve `analysis.json`'daki `tool` alanı zincirdeki bir
   model. Ardından ertesi işlem günü cron KENDİLİĞİNDEN koşuyor.
2. **`bist seviye` ölçümünü tüm evrende koş ve yorumla.** DoD: sonuç
   `reports/` altına yazılır ve "seviyeler yön iddiası taşıyor mu" sorusuna
   `edge_verdict` diliyle cevap verilir (tek hisse denendi, THYAO direnç
   −1.4pp çıktı — çoklu test uyarısıyla okunmalı).
3. **İlk çözüm turu (2026-07-29 tahminleri).** DoD: zaman bariyeri dolunca
   `bist coz` 18 tahmini çözüyor; ardından `bist degerlendir` KARIŞIK KAYNAK
   nedeniyle duruyor ve `--tool` istiyor (çıkış 2). Not: `araclar()` yalnız
   ÇÖZÜLMÜŞ tahminleri sayar, bu yüzden uyarı ancak çözümden sonra çıkar —
   `bist saglik` ise şimdiden uyarıyor. İkisi farklı soru soruyor, hata değil.

## 📦 Backlog (şimdi değil, unutma da)
- **`poetry run bist` YEREL'de çalışmıyor** (2026-07-29): klasör adındaki
  boşluk venv konsol script'inin shebang'ini kırıyor. Çalışan biçim
  `poetry run python -m src.cli <komut>` (Actions'ta sorun yok — Linux yolunda
  boşluk yok). Seçenek: (a) klasörü boşluksuz adlandır, (b) README'yi çevir.
- **Replay'i yeniden koş?** (#012) `asof 2024-12-18` tahmini bir gün geniş
  bariyerle çözüldü; yeniden koşmak journal'ı yeniden yazar → ayrı karar.
  20 kayıttan 1'i, 13 alfa gözleminden en fazla 1'i etkilenir.
- **`bist saglik`'e kısmi seans kontrolü** (#012): bir gün 0 < hisse barı <
  eşik olursa uyarsın — şu an böyle bir gün yok.
- **`high52_prox` hipotezi** — OOS'ta tek başına +1.61pp (t=1.81), IC 0.113
  (t=2.42): 34 karşılaştırmada çıtayı geçen TEK satır. Sonucu görüp seçmek
  p-hacking → AYRI ve ön kayıtlı tur hak ediyor (H=20'de ağırlığı zaten 0).
  `volscaled_mom` ise katkı göstermedi (−0.22pp) — 0'a çekmek de ön kayıt ister.
- **R:R'ın seçimle sağlanması** (#009'da ifşa edildi, düzeltilmedi): hedef
  sabit, eşitsizlik girişi aşağı iterek çözülüyor. Mekanizmayı değiştirmek ön
  kayıt ister → `docs/on-kayit-seviye-02.md` HAZIR ama **koşulmadı**;
  tetikleyici koşullardan biri (20 günde ort. <2 plan · N≥30 çözülmüş tahmin ·
  evren genişlemesi) oluşmadan koşulmayacak.
- **Dump yerel↔Actions arasında 4 satır oynuyor** (2026-08-01, ölçüldü):
  197.191 satırın 4'ü, `turnover_try` kolonunda, SON BİT farkı — macOS/Ubuntu
  SQLite'ının ondalık→double çevriminde 1 ULP ayrışması (yerelde ayrıştırma
  birebir, test edildi). **Kovalanmadı:** türev kolonda son bit ve o kolon
  200M TL eşiğinde kullanılıyor; hassasiyeti kırpmak kozmetik gürültü için
  gerçek veriyi değiştirmek olurdu. Yalnız Actions dump'larken tekrarlamaz.
- **KAP dilim bölme derinliği** — tek gün bile tavanı aşarsa (derinlik 6)
  sayfalama araştırılmalı. Şu an 90 günde bir kez bölme yetti.
- Evren BIST-100'e genişletilirse kesitsel dağılım ve OOS N artar → aynı ön
  kaydın tekrar koşulmasını mümkün kılar.
- 500 TL üstü fiyat adımı TEK İSİMLE ölçüldü (EGEEN); `bist saglik` ikinci
  isim girdiğinde uyarıyor. ASTOR/EUPWR profilini 6 ayda bir doğrula.
- **Model zinciri sırası VERİYLE kurulmalı** (#013) — 3 ay sonra araç başına
  veto değeri/isabet ölçülünce. Suite CI süresi (~35 sn) büyürse pahalı ölçüm
  testleri ayrı markere alınır (#011). `Proje Yardımcısı/` yerinde bırakıldı.
