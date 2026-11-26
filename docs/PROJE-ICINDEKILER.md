# Birikim projesi — doküman haritası

> **2026-11-26 devir notu.** Güncel üretim, yerel paket, bağımsız momentum ve ortak T0 durumu [STATE kaydında](../ai/STATE.md). Bu sayfadaki tarihli kesitler kendi koşullarına aittir.


**Güncelleme:** 2026-11-26. Başlangıç için [kapsam](../ai/PROJECT.md), [durum ve kabul](../ai/STATE.md), [kararlar](../ai/DECISIONS.md) ve [dersler](../ai/LESSONS.md).

[24 Kasım denetimi](DENETIM-2026-11-24.md) işlemsizlik, karar kapıları ve açık kanıtları toplar. [İşletim rehberi](ISLETIM-2026-11-18.md) yerel düzeltmeleri açıklar. [Dış AI bağlamı](AI-DANISMA-BAGLAMI.md) 24 Eylül tarihsel mimari kesitini ve güncel kaynakları gösterir. [26 Kasım tarihsel sınaması](TARIHSEL-SINAMA-2026-11-26.md) 20 seanslık eğitim pencerelerini ve ekonomik kıyası ölçer.

## Önce mimariyi doğru ayır

- `src/`: BIST'in önceki (V1) veri, nicel analiz, plan, LLM, günlük ve ölçüm hattı.
  Günlük veri/rapor üretimi sürer. V1 kâğıt portföyü V2 hesabından ayrıdır.
- `advisor/`: BIST V2'nin güncel, deterministik karar ve sanal hesap hattı.
  Altının ayrı `gold_tracking_system` deposunda aynı motorun altın sürümü bulunur.
- `dashboard/`: BIST ve altın depolarının son `latest.json` görünümünü okuyan ortak panel.
- `.github/workflows/`: iki hattın zamanlanması, teslimi, nöbeti ve yedeği.
- Gerçek banka/borsa emir bağlantısı yoktur. V2'de LLM sayısal işlem kararı vermez.

## Seçilebilir bölümler

[26 Kasım takip denetimi](AGIRLIK-VE-TAKVIM-DENETIMI-2026-11-26.md) eş tarihli
Ridge ağırlığını, BIST hedef vadesini ve T0 kabul durumunu belgeler.

### 01 — Amaç, kapsam ve başarı ölçütü

- BIST ve İş Bankası gram altını için iki bağımsız sanal hesap; ortak görünüm.
- Katkı, net getiri, varlık miktarı ve aynı bütçeli al-tut karşılaştırması.
- Kanıtlanmış kazanç iddiası yerine ölçülebilir karar ve risk disiplini.
- Kaynak: `ai/PROJECT.md`, `docs/V2-REHBER.md`, `advisor/config.json`.

### 02 — İki depo ve uçtan uca veri akışı

- BIST `src/` günlük arşivi → V2 tarihsel veri → model → güncel kotasyon → karar.
- Karar → olay defteri → son görünüm → Telegram ve panel.
- Altın deposunda kapanış yenilemesi ve ayrı sanal hesap; panelde birleşme.
- Kaynak: `advisor/service.py`, `.github/workflows/portfolio.yml`, `dashboard/lib/status.mjs`.

### 03 — Piyasa evreni, takvim ve veri kaynakları

- BIST canlı izleme evreni ile geniş tarihsel araştırma evreninin ayrımı.
- Yahoo günlük barları, endeks, TCMB EVDS ve KAP; V2'de İş Yatırım son fiyatı.
- Altında tarihsel ons×kur ile güncel İş Bankası gram alış/satışının ayrımı.
- Seans, tatil, yarım gün ve veri zaman damgası kuralları.
- Kaynak: `universe.yaml`, `src/prices.py`, `src/macro.py`, `src/news.py`,
  `advisor/history.py`, `advisor/marketdata.py`, `advisor/calendar.py`.

### 04 — Veri kalitesi ve güven kapıları

- Eksik/yarım/hayalet bar, bayat fiyat, makas, geçersiz zaman ve kapsama paydası.
- “Veri yok” ile “sorun yok” ayrımı; yeni alımın ne zaman durduğu.
- Mevcut pozisyonun koruyucu satışının ayrı değerlendirilmesi.
- Kaynak: `src/prices.py`, `src/saglik.py`, `advisor/marketdata.py`, `advisor/service.py`.

### 05 — Eski BIST nicel analiz ve planlama (V1)

- Göstergeler, faktörler, rejim, destek/direnç ve kesitsel sıralama.
- Deterministik giriş/stop/hedef/miktar plan menüsü; sektör ve risk kuralları.
- Walk-forward, replay, taban çizgisi ve eski kâğıt portföyünün sınırları.
- Kaynak: `src/indicators.py`, `src/factors.py`, `src/regime.py`, `src/levels.py`,
  `src/planner.py`, `src/backtest.py`, `src/replay.py`, `src/portfoy.py`.

### 06 — Eski BIST LLM analist hattı (V1)

- Girdi paketi, model zinciri/fallback, JSON çıktı ve sert hata denetimi.
- LLM yalnız izin verilen planı seçer veya veto eder; fiyat/stop/miktar icat edemez.
- Journal, model/araç kimliği, sonuç çözümü ve katkı ölçümü.
- 2026-09-24 model sırası notu tarihsel kesittir; geçerli sıra için `config.yaml` okunur.
- Kaynak: `src/llm_io.py`, `src/analist.py`, `src/audit.py`, `src/journal.py`,
  `src/resolver.py`, `src/evaluate.py`, `src/otonom.py`, `config.yaml`.

### 07 — V2 tahmin modeli ve öğrenme

- Trend/momentum/oynaklık/RSI özellikleri; ridge modeli ve zaman sıralı sınav.
- Sonucu henüz olgunlaşmamış tarihin eğitime girmemesi ve örtüşmeyen dönemler.
- Model onayı, küçük deneme, tahmin kalibrasyonu ve model sürümleri.
- Ayrı aday olarak BIST 20 seans göreli Ridge ve altın ons/kur Ridge;
  LightGBM yalnız offline. Tarihli replay üstünlük göstermedi.
- Kaynak: `advisor/learning.py`, `advisor/outcomes.py`, `advisor/evidence.py`,
  `advisor/shadow.py`, `advisor/specialized.py`, `advisor/config.json`,
  `scripts/portfolio_research.py`.
- [25 Kasım tahmin araştırması](TAHMIN-ARASTIRMASI-2026-11-25.md)
  ortak seans etiketlerini, yeni adayları, kalibrasyon sonuçlarını ve
  bağımsız ileri BIST gölge kaydını içerir.
- [İki AI denetimine teknik yanıt](TAHMIN-DENETIMI-2026-11-25.md) maliyetli
  sıralama, uzun 5 seans deneyi ve banka kotasyonu karşılaştırmasını içerir.

### 08 — V2 karar, risk ve sanal işlem kuralları

- AL/SAT/TUT/BEKLE/VERİ BEKLENİYOR; gerekçe ve ret kodları.
- Stop/hedef/süre, net beklenti, getiri:risk, nakit rezervi ve sektör/pozisyon sınırı.
- Lot/gram adımı, işlem penceresi, aynı gün tekrar ve fiyat kayması.
- Eski ana politika ile T0 bekleyen %80 çekirdek/%20 taktik adayının kapıları ayrıdır.
- Kaynak: `advisor/engine.py`, `advisor/policy.py`, `advisor/risk.py`,
  `advisor/portfolio_candidates.py`, `advisor/decision_trace.py`, `advisor/calendar.py`.

### 09 — V2 sanal defter, maliyet ve kurumsal işlemler

- Başlangıç ve aylık katkı; hash zincirli olaylar ve tekrarın tekilleştirilmesi.
- Alış/satış, komisyon/vergi, nakit, miktar, gerçekleşen ve değerleme getirisi.
- Bölünme, temettü alacağı/ödemesi ve kanıta bağlı mutabakat.
- Çekirdek/taktik kısmi dolumları ayrı lotlarda; saklama ücreti hesapta tek kez.
- Kaynak: `advisor/ledger.py`, `advisor/corporate.py`, `advisor/observations.py`,
  `advisor/portfolio_candidates.py`.

### 10 — Karşılaştırma, sonuç ve deneyler

- Aynı katkı ve masrafla al-tut; katkıdan arındırılmış getiri eğrisi.
- Tahmin vadesi, hata, kaçan hareket, gölge model/portföy ve maliyet stresi.
- Ayrı tam portföy simülasyonu; tarihsel veri ve üyelik yanlılıkları.
- Aynı T0/katkı/maliyetle beş aday; 20 seans çalışma, 63/126 seans ekonomik
  değerlendirme. Otomatik model terfisi yok.
- Kaynak: `advisor/benchmark.py`, `advisor/outcomes.py`, `advisor/shadow.py`,
  `advisor/simulation.py`, `advisor/reporting.py`, `advisor/portfolio_candidates.py`,
  `docs/PORTFOY-DENEYI-2026-10-01.md`.

### 11 — Ortak web paneli

- Genel bakış, kararlar, sanal portföy, gelişim karnesi ve geçmiş raporlar.
- İki depodan salt okunur son görünüm, parola, erişim hatası ve veri tazeliği.
- Vercel yeni statik sürümü yayımladı; parolalı veri görünümü henüz doğrulanmadı.
- Kaynak: `dashboard/public/`, `dashboard/api/status.js`,
  `dashboard/lib/status.mjs`, `dashboard/server.mjs`, `dashboard/vercel.json`.

### 12 — Telegram, rapor ve teslim güvenilirliği

- V1 uzun günlük raporu ve V2 kısa işlem/karar özetinin ayrımı.
- Gönderim makbuzu, yeniden deneme, olası mükerrer mesaj ve haftalık özet.
- 2026-10-01 altın yeni kod gönderimi `message_id: 320`; BIST ilk koşusu
  seans dışında atlandığından yeni bildirim üretmedi.
- Kaynak: `advisor/notifications.py`, `advisor/reporting.py`,
  `src/report.py`, `src/telegram_bist.py`, `ops/push_retry.sh`.

### 13 — Otomasyon, nöbetçi, yedek ve kurtarma

- GitHub Actions günlük veri, seans içi sanal hesap, haftalık rapor ve test işleri.
- Cron gecikmesi, dış dispatch belirsizliği, boşluk gözlemi ve hata artifact'i.
- Defter yedeği, salt okunur kurtarma denemesi ve karar kapsülünün yeniden üretimi.
- Kaynak: `.github/workflows/`, `advisor/watchdog.py`, `advisor/recovery.py`,
  `advisor/capsule.py`, `ops/`.

### 14 — Depolama, kanıt zinciri ve güvenlik sınırları

- V1 SQLite/SQL dump; V2 JSONL olay defteri ve `latest.json` okuma görünümü.
- Kod/ayar/model/girdi/karar kapsülleri; farklı çalışma ortamında tekrar üretim sınırı.
- Tokenların sunucuda kalması, panelin salt okunur olması, testlerin ağ ve gerçek veriden ayrımı.
- Kaynak: `src/db.py`, `src/dbdump.py`, `advisor/ledger.py`,
  `advisor/capsule.py`, `data/advisor/`, `tests/conftest.py`.

### 15 — Test, üretim denetimi ve açık riskler

- Sözleşme, davranış, uçtan uca akış, gerçek arşiv replay ve panel API testleri.
- Yeni beş deney hesabı için T0 henüz açılmadı; getiri sonucu yok.
- Cron yedeği, Telegram alıcı ekranı, kişisel tarife ve tarihsel banka makası açık.
- Kaynak: `tests/`, `dashboard/test/`, `reports/URETIM-DENETIMI-2026-09-22.md`,
  `reports/ACIK-RISKLER-2026-09-23.md`, `ai/STATE.md`.

## Tarihli ölçümler ve arşiv

- 24 Kasım veri toplama grafikleri [BIST](../reports/veri-toplama-2026-11-24/bist-veri-toplama.html) ve [altın](../reports/veri-toplama-2026-11-24/altin-veri-toplama.html).
- [32 ileri tahmin](BIST-ILERI-SIRALAMA-2026-11-18.md) 15 Aralık vadelidir. BEKLE ölçümü BIST deposundaki `scripts/decision_activity.py` ile alınır.
- [17 Kasım denetimi](DENETIM-2026-11-17.md), [19 Kasım işletim revizyonu](OTOMASYON-VE-STRATEJI-2026-11-19.md) ve [Ekim yayını](YAYIN-SONUCU-2026-10-29.md) tarihli kanıt kayıtlarıdır.
- [Hafıza arşivi](../ai/archive/README.md) ve mühürlü V1 ön kayıtlar [seviye](on-kayit-seviye-02.md) ile [revizyon](on-kayit-revizyon-01.md).

## Ayrıntı paketi hazırlanırken

Seçilen numara için amaç, mevcut davranış, akış, ilgili dosyalar, veri sözleşmesi,
ölçülmüş sonuç, açık sınır ve dış yapay zekâya sorulacak net sorular tek başına
anlaşılacak biçimde verilir. API anahtarı, token, parola ve özel hesap olayları
paylaşım metnine konmaz.
