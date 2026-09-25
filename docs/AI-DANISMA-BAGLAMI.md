# Birikim sistemi — dış yapay zekâ için teknik bağlam

**Kesit tarihi:** 2026-09-24. **Amaç:** Bu belgeyi okuyan, depolara erişimi olmayan
bir yapay zekâ sistemin hangi problemi çözdüğünü, hangi parçanın gerçekten çalıştığını,
hangi sonucun ölçüldüğünü ve önerisinin nereye oturacağını anlayabilsin. Bu bir
uygulama talimatı veya canlı yatırım sinyali değildir. Tarihli kanıt ile güncel durum
ayrı verilir; güncel işletim kaydı `ai/STATE.md` dosyasıdır.

## 0. En kısa doğru zihinsel model

- Sistem **iki ayrı Python deposundan** oluşur: `BIST tahmin` ve
  `gold_tracking_system`. Her depo kendi fiyat geçmişini, sanal hesabını,
  `advisor/config.json` ayarını, `data/advisor/events.jsonl` olay defterini ve
  `data/advisor/latest.json` son görünümünü tutar.
- Bu depoda **V1** (`src/`) günlük veri ve eski BIST analist/LLM araştırma hattıdır;
  otomatik veri, göstergeler, plan, analiz, rapor üretimi sürmektedir. **V2**
  (`advisor/`) güncel sanal yatırım kararının sahibidir. İkisinin portföyü ve
  başarı karnesi birbirine karıştırılmaz. Altın deposunda da eski `src/` hattı
  ve V2 `advisor/` ayrımı vardır.
- V2'nin yön, fiyat, adet, stop, hedef ve işlem kararı **deterministik Python**
  kodundan çıkar. V1 LLM analistinin anlatısı V2'de sayısal karar girdisi değildir.
- Ortak `dashboard/`, GitHub'daki iki ayrı `latest.json` görünümünü okuyup tek
  panelde gösterir. Vercel paneli karar motorunu çalıştırmaz. Telegram da hesap
  oluşturmaz; kararı iletir.
- Para bütünüyle **sanal**dır. Banka/broker kimlik doğrulaması, emir gönderimi,
  kredi ve gerçek varlık içe aktarımı yoktur. Kullanıcının gerçek hesapları bu
  defterlerde temsil edilmiyor.
- “Model kâr sağlıyor” sonucu yoktur: tarihsel ve canlı model onay kapıları
  2026-09-23 durumunda kapalıdır. Veri kalitesi, defter bütünlüğü ve ölçümün dürüst
  olması ürünün birinci önceliğidir.

### Uçtan uca şema

```text
BIST: Yahoo/KAP/EVDS -> V1 SQLite/SQL arşivi ------+
                                                   |-> V2 history/features/model
Altın: ons×kur/EVDS -> ayrı SQLite/SQL arşivi ------+       |
                                                           v
                  güncel referans fiyat + takvim + kurumsal işlem
                                                           |
                                                           v
              deterministik karar -> sanal fill -> hash zincirli olay defteri
                                                           |
                           +-------------------------------+----------------+
                           |                               |                |
                      latest.json                    Telegram makbuzu   karar kapsülü
                           |
                        ortak panel (iki depodan yalnız okuma)
```

## 1. Amaç, kullanıcı, kapsam ve başarı ölçütü

**Kullanıcı:** Mert; Python, SQLite, GitHub Actions, finansal veri ve test odaklı
kişisel otomasyon projelerinde deneyimli. Düşük maliyet, araç bağımsızlığı ve
kanıtlanabilirlik önemli. İstenen çıktı Türkçe, kısa günlük karar; gerektiğinde
ayrıntılı açıklama ve denetlenebilir kayıt. Mert'in gerçek portföyü bilinmediği
için sistem onun yerine işlem yapıyormuş gibi davranamaz.

**Ürün hedefi:** BIST hisseleri ve İş Bankası gram altın ürünü için ayrı sanal
hesaplarla fırsatları izlemek; fiyat/makas/komisyon/risk sonrası karar vermek;
nakit, hisse adedi veya gramı, toplam değer ve katkıdan arındırılmış sonucu
aynı bütçeli al-tut ile karşılaştırmak. Her kararın sebebi ve her sanal işlemin
fiyat kaynağı, zamanı, miktarı ve maliyeti saklanır.

**Bütçe sözleşmesi:** Her piyasa için 2026-09-15 başlangıç tarihli 5.000 TL
başlangıç + her ay 5.000 TL katkı varsayılır (`advisor/config.json`). Katkı kâr
sayılmaz. Kaçırılan ayın katkısı nakit olarak deftere tamamlanır; geçmişe dönük
uydurma alım yapılmaz. Hesap açıldıktan sonra başlangıç/bütçe tanımının sessizce
değişmesine `advisor/service.py` izin vermez; yeni hesap sürümü gerekir.

**Başarı ayrımı:** (a) Mekanik doğruluk: nakit negatif değil, elde olmayan
varlık satılmıyor, tekrar koşu ek işlem yazmıyor, eksik fiyat belirsizlik olarak
görünüyor. (b) Tahmin kalitesi: zaman sıralı, sonuç vadesi ayrılmış sınav.
(c) Yatırım sonucu: canlı sanal getiri, eş bütçeli al-tut ve bağımsız dönemler.
(a)'nın doğrulanması (c)'yi kanıtlamaz. 2026-09-22 üretim denetiminde
defter/kapsül mekanikleri güçlü bulundu; canlı üstünlük kanıtı bulunmadı.

**Bilinçli kapsam dışı:** gerçek emir, gerçek bakiyelerin otomatik okunması,
kredi, garanti edilmiş stop dolumu, anlık emir defteri, V2 için LLM kaynaklı
sayısal al/sat, tarihsel banka kotasyonu varmış gibi davranma. Gelecek için
panelden ayar, gerçek işlem günlüğü ve etkileşimli senaryo ekranı backlog'dadır.

## 2. Depolar, modüller ve çalışma akışı

| Konum | Rol | Önemli dosyalar |
|---|---|---|
| BIST `src/` | V1 fiyat/toplama/analiz/LLM/rapor | `src/otonom.py`, `src/cli.py`, `src/prices.py`, `src/analist.py`, `src/report.py` |
| BIST `advisor/` | V2 model, karar, sanal defter, sonuç | `advisor/service.py`, `advisor/learning.py`, `advisor/policy.py`, `advisor/ledger.py` |
| Altın deposu `src/` | Eski altın veri/rapor hattı, V2 öncesi kapanış yenilemesi | `src/daily_job.py`, `src/history.py`, `src/advisor_refresh.py` |
| Altın deposu `advisor/` | Aynı V2 çekirdeğinin altın ayarlı sürümü | Ortak modüller + ayrı `advisor/config.json` |
| BIST `dashboard/` | İki hesabın salt okunur web görünümü | `dashboard/lib/status.mjs`, `dashboard/api/status.js`, `dashboard/public/` |
| Her iki repo `.github/workflows/` | Günlük veri, portföy, nöbet, kurtarma | `portfolio.yml`, `advisor-watchdog.yml`, diğer piyasa işleri |

V2 komut girişi `python -m advisor`; `cycle`, `status`, `notify`, `weekly`,
`watchdog`, `audit`, `research`, `simulate`, `reproduce`, `backup`,
`recovery-check`, `settle-dividends`, `cost-observations`, `universe-import`
komutları vardır. `cycle` varsayılan olarak Telegram göndermez. `notify`, son
görünümden gönderir. `--offline` canlı üretim DB'sinde deneme yapmak için değil;
ayrı kopyadaki inceleme içindir. Yerel SQLite ikilisi yerine, üretim gerçekliği
GitHub'a kaydedilmiş deterministik SQL dump ve olay dosyalarındadır.

V2 `service.cycle` akışı: yapılandırma/takvim → seans kapısı → defter kilidi ve
katkı → SQL geçmişi → model önbelleği/eğitimi → canlı ve elde tutulan evren →
gündem/kotasyon/kurumsal işlem → olgun tahmini çözme → taze tahmin/kalibrasyon
→ gölge hesaplar → karar motoru → kapsül → benchmark → değerleme/sağlık →
`events.jsonl` ve `latest.json`. Seans dışı çağrı `session_check` izini bırakır
ama fiyat/model/işlem aşamasına girmez. BIST günlük V1 işi ile V2 portföy işi
ayrı workflow'lardır; birincinin raporu ikincinin sanal işlemi değildir.

**Ortak kod bakımı:** V2 çekirdeği iki depoda kopyalıdır ve
`advisor/shared-manifest.json` ile `scripts/advisor_manifest.py` eşlik kontrolü
bulunur. Altına özgü veri yenilemesi altın `src/` tarafındadır; BIST V1 LLM
model sırası değişikliği altın motorunu etkilemez.

## 3. Piyasa evreni, tarihsel veri, güncel kotasyon ve takvim

### BIST

- `universe.yaml` iki düzeyi tanımlar: **canlı 18 hisse** ve kalibrasyon için
  daha geniş **70 hisselik araştırma tabanı** (2026-09-22 kesiti). Bu BIST30'un
  tamamı değildir. `src/universe.py`, YAML'ı SQLite `universe` tablosuna yazar;
  canlı (`in_live`) ile ölçüm (`in_measure`) bayrakları ayrıdır. Kısa geçmişli
  canlı hisse izlenebilir ama uzun tarihli ağırlık kalibrasyonuna girmez.
- V1 `src/prices.py` Yahoo Finance'ten günlük OHLCV, endeks ve USD/TRY toplar;
  düzeltilmiş toplam getiri fiyatı `c_tr` tutulur. `src/sources/kap.py` KAP
  bildirimini ve beklenen açıklama takvimini; `src/macro.py` TCMB EVDS serilerini
  toplar. V1 SQLite tabloları `bars_daily`, `index_daily`, `indicator_daily`,
  `factor_daily`, `regime_daily`, `plan_options`, `predictions`, `outcomes`,
  `disclosures`, `evds_daily` vb. SQL dump `data/bist.sql` içindedir.
- V2 model geçmişi `advisor/history.py` ile aynı SQL'den `bars_daily` ve
  `universe` birleştirilerek okunur. Beklenen canlı hisse paydası fiyat
  satırlarından değil evren tablosundan gelir: tüm barı kaybolan hisse başarı
  yüzdesinden sessizce düşmez. Ana, benchmark ve iki gölge hesapta tutulan
  varlık, canlı evrenden çıkmış olsa da stop izlemi için saklanır.
- V2 güncel hisse referansı `advisor/marketdata.py` ile İş Yatırım'ın herkese
  açık **gecikmeli son fiyat** tablosudur. Tek `bid=ask` son fiyat kullanılır,
  her yön için yapılandırılmış 5 baz puan sanal kayma uygulanır. Sayfanın
  önbellek zamanı bireysel hissenin son işlem zamanı değildir; kod bu ayrımı
  kotasyonun `timestamp_kind=page_cache` alanında taşır. Gerçek dolum iddiası yoktur.

### Gram altın

- V2 işlem referansı Döviz.com'daki **İş Bankası gram altın** alış/satışıdır:
  müşteri alışında banka satış (`ask`), satışında banka alış (`bid`). Bu ikincil
  kaynak kişisel İşCep kotasyonu değildir; sayfa yalnız saat verdiği için gün
  aynı gün varsayılır. Kaynak gün içi fiyat tarihi belirsizliği kayıtlıdır.
- Model geçmişi altın SQL'indeki `history_daily.gram_teorik` serisidir.
  Bu seri geçmiş ons/kur temsili olup tarihsel banka gram alış/satışı değildir.
  `advisor/history.py` sentetik altın serisine gerçek OHLC/volume uydurmak
  yerine yüksek/düşük = kapanış ve kalite için hacim = 1 işaretleyicisi verir;
  `advisor/learning.py` altında gerçek ATR varmış gibi kullanmaz.
- Gün içi `GC=F × TRY=X / 31.1034768` ayrıca referans aranır. Amaç analiz
  kapanışından beri olmuş hareketi gelecekte olacak hareket diye ikinci kez
  saymamaktır. Referans yok/geçersizse yeni altın alımı engellenir; eldeki
  pozisyonun koruyucu stop/hedefi güncel banka fiyatı doğrulanabiliyorsa izlenir.
- Altın `src/advisor_refresh.py`, portföy işinden önce son **tamamlanmış**
  kapanışı geçici DB'de üretip beklenen günü doğrular; ancak tam veriyse SQL
  dump'ını atomik değiştirir. Kaynak başarısızsa eski SQL baytları korunur,
  V2 önceki kapanış eksikliğini görüp yeni alımı kapatır.

### Takvim ve tazelik

İstanbul saat dilimi ve `holidays_tr.yaml` kullanılır. V2 ihtiyatlı sanal işlem
penceresi hafta içi **10:15–17:45 TR**; yarım gün kapanış sınırı **12:15**.
Fiyatın sayısal/geçerli olması, saat dilimi taşıması, gelecekte olmaması,
bugüne ait olması ve en çok **25 dakika** yaşında olması gerekir. Güncel
görünümde analiz tarihi ve beklenen önceki kapanış ayrı tutulur. Beklenen
kapanış eksikse yeni tahmin ve yeni alım açılmaz; mevcut stop/hedef izlenebilir.
GitHub cron'un kesin zamanlı çalışacağı varsayılmaz.

## 4. Veri kalitesi, eksiklik anlamı ve güven kapıları

V1 `src/prices.py`, Yahoo'nun tatil/hayalet barlarını, tamamlanmamış barları,
OHLC ve hacim tutarsızlıklarını inceler. `src/saglik.py` sağlık bulgularını
**KAPI** (girdiye güven) ve **GÖZLEM** (sürecin sağlığı) diye ayırır. KAPI kritik
olabilir; örneğin bayat bar, gösterge kapsamı veya yanlış payda analizi
durdurur. Atlanan koşu gibi sürecin kendi çıktısına bakan GÖZLEM, işi durdurmaz;
geçmişte böyle bir kapı dört işlem günü analizi kilitlemişti. Bu sınıf ayrımı
kod ve testlerle zorlanır.

V2 `marketdata.price_problem` geçersiz/bayat/gelecek fiyatı ayrı hata olarak
döndürür. `usable` buna seans, tatil, işlem yapılabilirlik ve en çok %3 makas
koşulunu ekler. Makas kapısı yeni alışta uygulanır; eldeki varlığın koruyucu
satışı geniş makas nedeniyle tek başına engellenmez. Kaynak erişim hatası
`haber yok` veya `fırsat yok` anlamına çevrilmez. Haber kaynağının `ok` bilgisi
ayrıdır. Eksik veya bayat fiyat mevcut pozisyonu sıfır değerlemez:
`equity_try` ve `pnl_try` **null** olur, `last_known_equity_try` ayrı ve kesin
servet diye kullanılmayan alan olarak kalır. Belirsiz bölünmede adet bilinmediği
için yeni risk bütçesi ve kesin değerleme gösterilmez.

Sistemin bilinçli **payda disiplini** vardır: beklenen evren sayısı fiyat tablosu
daralsa bile korunur; fiyat kapsamı `valid_quotes/expected_quotes` olarak
görülebilir. V1'de kesitsel skor, sıralamaya giren isim sayısı ve gerçek
gözlem sayısı ayrı açıklanır. Böylece `0 geçersiz hisse` ile `0 hisse kontrol
edildi` aynı sonuç değildir.

## 5. BIST V1 araştırma, planlama, LLM ve karne hattı

V1 günlük komutu `bist otonom gunluk` / `python -m src.cli otonom gunluk`.
Kabaca: koşu heartbeat'i → doğru **analiz seansı** → fiyat, endeks/kur,
gösterge, EVDS, KAP → sağlık kapısı → LLM girdi paketi → analist zinciri →
üçlü bariyer sonuç çözümü → Markdown rapor ve gerekirse Telegram. `veri`,
`gosterge`, `saglik`, `rapor` kritik; analist, haber, makro düşse hata
görünür ama deterministik kısım yaşayabilir. `ADVISOR_V2=1` iken V1 uzun
normal Telegram raporu bastırılır; V2 kısa özeti gönderir. V1 kritik veri
hatası uyarısı korunur.

Nicel kısım `src/indicators.py` içinde SMA/EMA, RSI, MACD, Bollinger, ATR,
ADX ve hacim/volatilite göstergelerini sürümlü hesaplar. `src/factors.py`
momentum ve 52 hafta zirvesi yakınlığı gibi faktörleri winsorize edip
kesitsel z skora dönüştürür; skor tüm araştırma kesitinden, sıralama ise
uygun hisselerden çıkar. Sektör nötralizasyonu ölçümde faydayı düşürdüğü
için varsayılan kapalı; sektör yoğunluğu pozisyon kısıtında kontrol edilir.
`src/regime.py`, XU100 trend/volatilite ve piyasa genişliğini kullanır;
etiketin hangi girdiden geldiği açıklanır. `src/levels.py` destek/direnç
pivotlarını planlama geometrisi olarak üretir, yön üstünlüğü iddia etmez.
`src/planner.py` gerçek fiyat adımı, stop ATR bandı, hedef mesafesi ve net
getiri:risk koşullarıyla giriş/stop/hedef/boyut menüsü kurar. Plan yoksa
sebep sınıfı saklanır; hedef çok yakın ile stop bandı hatası ayrılır.

LLM yalnız paket içindeki plan kimliğini seçebilir, reddedebilir, izleyebilir
veya veto/gerekçe yazabilir. **Fiyat, hedef, stop, adet veya sayısal güven
üretemez.** `src/llm_io.py` girdi ve şemayı; `src/audit.py` HF-01…HF-32 sert
denetimleri taşır. Prose içindeki sayılar dahi izinli girdi tokenlarıyla
karşılaştırılır. Geçmeyen çıktı `src/journal.py` içine yazılmaz. Çıktı ve
girdi, koşu/model kimliğiyle mühürlenir; aynı analiz günü ikinci karar seti
yaratılmaması için tekrar analist turu atlanır.

Otonom zincir `src/analist.py` içinde REST çağrılarıyla sırayla denenir:
2026-09-24 **yerel, henüz üretime yayımlanmamış** sıra
`gemini-3.8-flash → gemini-3.7-flash → gemini-3.6-flash →
gemini-3.1-pro-preview → gpt-6-luna → gpt-5.6-luna`.
Kota/ağ/zaman aşımı/JSON/şema/HF hatası bir halkayı düşürür; ilk temiz cevap
kazanır. Ara halkalarda tekrar yok, son halkada yapılandırılmış tekrar var.
Model kimliğini LLM değil kod yazar; deneme günlükleri `llm/out/<gün>/attempts.jsonl`
dosyasına gider. Bu model değişikliği V2 deterministik motorunu değiştirmez.

`src/resolver.py` giriş/stop/hedef/zaman üçlü bariyer sonucunu fiyat barından
çözer; `src/evaluate.py`, `src/backtest.py`, `src/replay.py` farklı araştırma
ve ölçüm araçlarıdır. Araç/model kaynakları ve replay ayrılır. 20 seanslık
örtüşen kararlar 18 hisseyle çarpılıp bağımsız gözlem sanılmaz. Tarihsel V1
faktör ölçümünde genel pozitif getiri üstünlüğü kanıtlanmadı; V1'in kalan
değeri izleme, risk disiplini, plan geometrisi ve denetlenebilir yorumdur.
V1 `src/portfoy.py` kâğıt portföyü `predictions/outcomes` görünümünden türetilir;
V2'nin ayrı olay defteriyle birleştirilmemelidir.

## 6. V2 tarihsel model, test ve canlı öğrenme

V2 `advisor/learning.py` bilinçli olarak küçük/sabit bir **ridge regresyon**
kullanır. Girdi özellikleri: 20/60/120 günlük momentum, 50/200 günlük trend,
20 günlük oynaklık, 60 günlük drawdown ve RSI14. Hedef, yapılandırılmış
`horizon_sessions=20` sonrasındaki toplam getiri yüzdesidir. Ölçekleme yalnız
eğitim verisinde öğrenilir; sınav başlangıcında sonucu henüz tamamlanmamış
etiket eğitimden çıkar (`train.label_end < test.start`). Test blokları 126
seans, minimum eğitim tarihi 504; aynı günün hisseleri birbirinden bağımsız
piyasa dönemleri gibi sayılmaz. Performans raporu örtüşmeyen 20 seanslık
dönemleri ve maliyetin 1×/1,5×/2× duyarlılığını verir.

Tarihsel `approved` kapısı: en az 24 bağımsız sınav dönemi, al-tut üstü farkın
%95 alt sınırı pozitif ve ortalama mutlak tahmin hatası sabit tahmin tabanından
daha düşük. `approved=false` modeli tamamen kapatmaz; **sınırlı sanal deneme**
olarak çalışır. O durumda azami pozisyon tutarı `trial_position_multiplier=0.5`
ile küçülür. BIST'in azami tek pozisyon payı %20, altının %80 ayarı bu sınıra
girmeden önceki tavanlardır. Model önbelleği veri+kod+ayar fingerprint'iyle
yenilenir; `data/advisor/model.json` ve sürümlü `models/<id>.json` saklanır.

**Canlı geri besleme:** Karar anındaki ilk uygulanabilir ham tahmin, modeli,
analiz gününü ve **o günün 20 seanslık vadesini** `forecast` olayıyla mühürler.
Vade dolunca `advisor/outcomes.py`, düzeltilmiş toplam getiri fiyatı üzerinden
gerçekleşen hareketi ve tahmin hatasını hesaplar. Bu **net banka getirisi**
değildir. Sonradan ayar vadesi değişirse eski kayıt yeni vade ile yeniden
çözülmez. En az 10 bağımsız dönemden sonra ölçülen ortalama yanlılık en fazla
2 yüzde puanla yeni tahminden düşülebilir; 2026-09-23 durumunda olgunlaşmış
canlı sonuç olmadığından kalibrasyon sıfırdır.

**Canlı risk büyütme kapısı:** `advisor/evidence.py` strateji ile eş bütçeli
benchmark'ın katkıdan arındırılmış NAV'ını, örtüşmeyen 20 seanslık dönemlerde
eşleştirir. En az 24 dönem ve pozitif yaklaşık t güven aralığı alt sınırı
gerekir. Buna ek olarak en az 10 kapanmış canlı sanal işlem gerekir.
2026-09-23'te dönem ve satış sayıları bu kapıyı geçmez. Drawdown -%12 veya
daha kötü olursa yeni risk çarpanı 0,25'e düşer; bu, modelin yeniden
öğrenmesini engelleyen kalıcı kilit değildir.

**Gölge karşılaştırma:** `advisor/shadow.py` önceki sabit modeli ve güncel
yeniden eğitim politikasını ayrı tahminler ve ayrı sanal defterlerle izler;
aynı başlangıç hesabı ve katkılarla kıyaslar. Ortalama tahmin hatası farkı
işlem kârına eşit değildir. Gölge performansı otomatik model terfisi yapmaz,
ana portföye fill eklemez.

**Bilinen araştırma sınırları:** BIST'te güncel evreni geçmişe yansıtmak
survivorship yanlılığı yaratabilir; tarihsel üyelik kanıtı elde yok. Geçmiş
fiyatlar sonradan düzeltilmiş olabilir. Altında geçmiş gram serisi banka
kotasyonu değil; vadeli ons×kur, roll/baz ve tarihsel makas belirsizliği var.
Bu yüzden V2 model değerlendirmesi tam portföy backtest'i veya kâr kanıtı
diye sunulmaz.

## 7. V2 karar motoru ve risk sırası

Temel giriş `advisor/engine.py::run`, tek sembol kararı
`advisor/policy.py::decision`, gerçek sanal fill `execute` içindedir.
Karar sözlüğünde `symbol`, `asof`, `action`, `code`, `reasons`, `forecast_pct`,
`remaining_forecast_pct`, `model_id`, `horizon_sessions`, `stop`, `target`,
`price`, `confidence`, `deadline` bulunur. Eylemler: `AL`, `SAT`, `TUT`,
`BEKLE`, `VERİ BEKLENİYOR`. `code` sınıflandırılmış sebep; kullanıcı metni
`reasons`. Model sonucu bilinmiyorsa karar mekanizması alımı zorlamaz.

**Karar sırası:**

1. Analiz satırının tarih/kalitesi, model vadesi, güncel kotasyon, seans ve
   kurumsal işlem belirsizliği kontrol edilir. Önceki işlem gününün kapanışı
   eksikse yeni tahmin/alım kapalıdır. Mevcut pozisyon için eski analiz,
   doğrulanmış güncel fiyat varsa stop/hedef takibini tek başına kapatmaz.
2. Pozisyon varsa satış öncelikleri: kayıtlı stop, kayıtlı hedef, BIST için
   20 seans sonu, ardından taze negatif model görünümü + zayıf kısa trend.
   Hiçbiri yoksa `TUT`. Stop değeri, fiyatta aradaki boşluk varsa garanti
   edilmiş çıkış fiyatı anlamına gelmez.
3. Pozisyon yoksa modelin kapanıştaki tahmini güncel referansa taşınır:
   `remaining = (analysis_close * (1 + forecast_pct/100) / current_reference - 1)*100`.
   Bu formül son kapanıştan beri yaşanmış fiyat hareketini geleceğe ikinci
   kez saymaz. Alım için maliyet sonrası net beklenti en az %1, 50 günlük
   trend pozitif, RSI14 < 75 gerekir.
4. Aday stopu yaklaşık `max(2.5 × kısa oynaklık, %2)` mesafeyle kurulur;
   hedef tahmine dayanır. Komisyon dahil net ödül/risk en az 1,5 olmalı.
   Fill'den önce **gerçek lot veya 0,01 gram adedi ve asgari komisyonla**
   ikinci kez kontrol edilir; soyut 1.000 TL hesabını geçip gerçek adette
   düşen aday `BEKLE` olur.
5. Satışlar alışlardan önce ele alınır. Alış için nakit rezervi (%20), azami
   tek pozisyon, BIST'te aynı sektörde en çok 2 pozisyon, işlem başı %1
   (altın config'inde %2) risk, portföy toplam %5 stop riski ve eldeki
   miktar/komisyon birlikte uygulanır. Onaysız model, canlı kapı geçmemesi,
   -%12 drawdown veya yakın Fed kararı yeni tutarı ayrıca küçültür.
6. Aynı gün satılan sembol tekrar alınmaz; aynı sanal işlem benzersiz
   olay anahtarıyla tekrar çalıştırmada çoğalmaz. BIST tam lot, altın
   0,01 gram adımı kullanır. Nakit eksiye veya satılan miktar eldeki adedin
   üstüne çıkarsa defter diske yazılmadan hata verir.

Altında elde zaten GRAM varken ay içi yeni katkıyla **yeni fırsat** oluşursa
aylık ekleme değerlendirilebilir; zorunlu ay sonu satış yoktur. Altında makas
yüksekse yeni alış kapalı, doğrulanmış mevcut koruyucu satış yalnız makas
nedeniyle kapalı değildir. BIST evren dışına çıkan sembolde yeni alış yok;
eldeki pozisyon izlenmeye devam eder.

## 8. Maliyet, sanal muhasebe, kurumsal işlem ve fiyatın anlamı

`advisor/policy.py::fee` BIST için işlem tutarının %0,20'si standart komisyon,
asgari 1 TL (işlem tutarının %1 tavanıyla), komisyon üzerinden %5 BSMV,
ayrıca %0,003 borsa payı varsayımını uygular. İki yönde 5 baz puan sanal
kayma vardır. Altında müşteri alışında banka ask + %0,20 KMV, satışta
banka bid kullanılır; sanal banka makası kotasyondan gelir. Kişisel ekstre
tarifesi ve saklama/MKK dönemsel ücretleri doğrulanmadığından bu sonuç
tam gerçek hesap maliyeti değildir. Maliyet ayarları olay defterindeki
`cost_policy` olayıyla ve görünümdeki notlarla açıklanır.

`advisor/ledger.py` olay defteri `events.jsonl` satırlarında `kind`, benzersiz
`key`, saat, `data`, `previous` ve SHA-256 `hash` tutar. Açarken bütün zincir
ve anahtar eşsizliği doğrulanır; eski satır değiştirilmişse açılmaz. `add`
aynı anahtarı tekrar eklemez. Dosyaya yazım geçici dosya + `fsync` + atomik
`os.replace`; süreçler arası kilit `.lock` dosyasıdır. TL **kuruş** tamsayısı,
miktar `Decimal` ile hesaplanır. `account(book)`, olayları yeniden oynatarak
nakit, katkı, gerçekleşen sonuç, temettü alacağı, pozisyon ve fill'leri çıkarır.
Kitaplar: `strategy`, `benchmark`, `shadow_reference`, `shadow_candidate`.

Bir pozisyonun güncel net satılabilir değeri, geçerli bid ve satış masrafıyla
hesaplanır. Portföy değeri = nakit + geçerli net pozisyon değerleri + bilinen
temettü alacağı. Eksik/bayat kotasyonda kesin toplam değer **null** olur;
alacak henüz nakit değildir. `feedback` katkıdan arındırılmış zincir NAV,
drawdown ve kapanmış işlemleri izler. Haftalık rapor da son yedi gündeki
katkıyı yatırım sonucundan ayrı gösterir; masraf net sonuçta zaten vardır,
ikinci kez düşülmez.

`advisor/corporate.py`, Yahoo/SQL kurumsal işlemlerini birleştirir. Bölünme
eldeki adedi ve stop/hedef seviyesini oranla düzeltir. Ex-date öncesi hisse
adedi hak sahipliği için kullanılır. Bölünme haberi geçmiş sanal işlemlerden
sonra gelip çelişiyorsa kod geçmişi sessizce yeniden yazmaz; sembolü
mutabakata bloklar. Temettü, varsayılan %15 kesinti sonrası **alacak** olur.
Ödeme günü doğrulanmış kanıt referanslı dosyayla `settle-dividends` üzerinden
bir kez nakde çevrilebilir. Maliyet gözlemleri `cost-observations` ile ayrı
kanıt kaydı olarak girilebilir; olmayan ekstre/banka geçmişi uydurulmaz.

## 9. Benchmark, sonuç, gölge hesap ve tarihsel simülasyon

`advisor/benchmark.py` stratejiyle aynı başlangıç ve aylık katkıyı kullanan
al-tut hesabı tutar. BIST'te eşit katkı cebi her canlı sembole ayrılır;
bir hissenin kotasyonu eksik diye diğer uygun hisselerin alımı durmaz.
Tam lota yetmeyen nakit o sembol cebinde sonraki katkıya eklenir. Altında
tek GRAM al-tut hesabı aynı banka fiyatı/adet adımı ve maliyetle yürür.
Benchmark, V1 eski araştırmadaki eşit ağırlık/XU100 tabanı ile **aynı
mekanizma değildir**; V2 gerçek sanal katkı ve fill hesabıdır.

`advisor/outcomes.py` yalnız vadesi dolmuş tahminleri çözer. Tahmin hatası
fiyat serisinin hareketini açıklar, al/sat fill kârını değil.
`advisor/evidence.py` canlı strateji ile al-tut NAV'ını yaklaşık bağımsız
20 seanslık bloklarda karşılaştırır; aynı piyasa hareketi 18 ayrı başarı
gibi sayılmaz. `advisor/shadow.py`, donmuş referans ve güncel modelin hem
tahmin hatasını hem ayrı sanal portföylerini karşılaştırır; ana hesap etkilenmez.

`python -m advisor simulate --start ... --end ... --output ...`, geçici
defterde tarih sırasıyla aynı karar/masraf/nakit/lot mekanizmasını uygular.
Karar, o günün açılışında **yalnız önceki veriyi** görür. Günlük bar içindeki
stop/hedef sırası bilinmediğinde ihtiyatlı olarak stop önce kabul edilir;
gap, satılamama, bayat fiyat, atlanan seans ve maliyet çarpanı senaryoları
vardır. Bu çıktı `production_eligible=false`: geçmiş banka makası ve
gerçekleşme fiyatı yoktur. Tarihli BIST üyelik kanıtı verilmezse güncel
evren geçmişe taşınır ve sonuç üstünlük kanıtı olamaz. `advisor/universe.py`
kanıtlı tarihli üyeliği `known_at` ve `effective_from` ile içe alabilecek
yapıya sahiptir; elde güvenilir tarihsel üyelik veri kümesi yoktur.

**Ölçüm sonucu (2026-09-22 sabit üretim arşivi):** BIST ve altın tarihsel
model onayı kapalı. BIST modelinde 111 bağımsız tarihsel dönem ve al-tut
farkı %95 alt sınırı yaklaşık **−0,021 yüzde puan**; altında 94 dönem ve
alt sınır yaklaşık **−2,167 yüzde puan**. Bunlar o kesitin sayılarıdır,
bugünün canlı sonucu değildir. Her iki hesapta olgunlaşmış canlı V2 tahmin
sonucu ve bağımsız canlı başarı dönemi sıfırdı.

## 10. Panel, API, görünüm sözleşmesi ve dağıtım

`dashboard/` Node 22+ ile haricî npm paketi gerektirmeyen küçük bir web
uygulamasıdır. `dashboard/public/index.html` gezinmeyi, `app.js` beş ekranı,
`insights.js` karar hunisi/haftalık/risk/kanıt açıklamalarını oluşturur.
Ekranlar: **Genel bakış**, **Kararlar**, **Sanal portföy**, **Gelişim karnesi**,
**Geçmiş raporlar**. Piyasa seçimi BIST/GRAM; karar arama/filtre, pozisyon,
fill, masraf, katkıdan arındırılmış eğri, benchmark, veri eksikliği, model
sınırı ve V1 kaynak karışımı gösterilir. İlk iki gün gelmeden çizgi grafik
uydurulmaz. Ekranda `live`/taze etiketi son görünüm saatinden türetilir;
arka planda fiyat yayını değildir.

Her V2 koşusu `latest.json` sözleşmesi üretir: `schema_version=2`,
`market`, `generated_at`, `analysis_date`, `mode=paper`, `strategy`,
`benchmark`, `decisions`, `quotes`, `news`, `learning`, `feedback`,
`history`, `legacy`, `health`, `risk`, `weekly`, `funnel`, `reproduction`,
`budget`, `costs` ve maliyet notları. `dashboard/lib/status.mjs` temel tipleri
ve karar enumlarını doğrular; bozuk tek hesabı diğerinden ayrı hata olarak
gösterir. Bu JSON ayrıntılı olay defteri değil, okunabilir **son görünüm**dür.
Geçmişin tamamı hash zincirli defter ve eski SQL arşivindedir.

**Canlı mimari:** Vercel `dashboard/api/status.js` isteğinde GitHub API'den
BIST özel deposunun ve herkese açık altın deposunun `main` dalındaki
`data/advisor/latest.json` dosyasını okur; 45 saniyelik sunucu içi cache
vardır. API yalnız GET; parola yoksa 503, yanlış/parolasız istek 401.
`ADVISOR_DASHBOARD_PASSWORD` sunucuda kalır; Basic Auth kullanıcı adı
`mert`. BIST için `ADVISOR_GITHUB_TOKEN` yalnız sunucuda Contents Read
yetkisiyle kullanılır; tarayıcıya verilmez. Tarayıcı parola bilgisini yalnız
oturum belleğinde tutar. API yeni analiz, eğitim, fill veya GitHub'a yazma
yapmaz. Yerel `node dashboard/server.mjs`, iki `latest.json` dosyasını
`BIST_SNAPSHOT` / `GOLD_SNAPSHOT` yollarıyla doğrudan okuyabilir.

**Doğrulanan canlı kesit:** `ai/STATE.md` 2026-09-23'te Vercel production
deployment'ının `Ready` olduğunu; parolasız API'nin 401 döndüğünü; parola
sonrası BIST fiyat kapsamının 18/18, altının 1/1 ve her ikisinin analiz
tarihinin 2026-09-22 olduğunu kaydeder. Bu, sonraki günlerde tazelik veya
görsel durumun otomatik kanıtı değildir. Panel BIST'teki eski LLM zinciri
yerel model sırası değişikliğini yayımlamaz; değişiklik ayrı beklemektedir.

## 11. Telegram, rapor ve teslim sözleşmesi

V1 BIST `src/report.py` ayrıntılı Markdown günlük üretir; V1 `src/telegram_bist.py`
ayrı Telegram taşıyıcısıdır. V2 `advisor/notifications.py`, 1.000 karakteri
aşmayan kısa Türkçe özet üretir: önce tüm sanal AL/SAT satırları, sonra kısa
gerekçeler, analiz günü, varsa gündem/veri uyarısı, portföy/nakit ve panel
bağlantısı. İşlem yapılmadıysa bu açık söylenir. Bozuk/eksik değerleme
kesin kâr veya sıfır zarar gibi sunulmaz.

`notify` önce görünümün zamanının geçerli ve yeterince yeni olduğunu
kontrol eder; eski başarılı kararı yeni turmuş gibi göndermez. Bildirim
durumu karar/işlem, hata ve analiz güncelliği üzerinden özetlenir;
saatlik fiyat değişimi aynı mesajı tekrar üretmez. A→hata→A dizisinde son
**gönderilmiş** durumla karşılaştırıldığı için iyileşme mesajı kaybolmaz.
Telegram API `ok` yanıtı sonrası `notification` olayı mesaj metni, kaynak
görünüm zamanı/hash'i, `message_id` ve Telegram zamanıyla deftere yazılır.
Nöbetçi son karar durumunun makbuzunu inceler. Makbuz, API kabulünü kanıtlar;
alıcının uygulamada gördüğünü kanıtlamaz. Yanıt ağda kaybolduysa tekrar
denemede mükerrer mesaj olasılığı vardır; tam bir kez teslim garantisi yoktur.

V2 haftalık özet, son yedi gün katkısı, yatırım sonucu, toplam masraf,
al-tut farkı ve alış/satış sayısını aynı pencere için üretir. Cuma uygun
zamanda ve hazır veriyle gönderilir. Geçersiz/eksik metin yerine işin
başarısızlığı görünür kalır. Eski altın V1 Telegram rapor ve bot komutları
ayrı eski üründür; V2 kısa bildirimle aynı kanıt sayılmamalıdır.

## 12. İşletim: GitHub Actions, gözlemci, yedek ve tekrar üretim

**BIST V1 günlük** `.github/workflows/gunluk.yml`: hafta içi nominal
19:35 TR kapanış sonrası çağrı; SQL dump'tan DB'yi açar, `bist otonom gunluk`
koşturur, dump/rapor/LLM arşivini commit/push eder. Kapanış verisinin
yayımlanması için pay bırakılır; GitHub cron gecikebilir. Kritik adım düşse
bile o ana kadar oluşan veri/rapor izi `if: always()` ile commit edilmeye
çalışılır. Haftalık değerlendirme ve V1 nöbetçi ayrı workflow'lardır.

**V2 portföy** `.github/workflows/portfolio.yml`: `workflow_run`, dış/elle
`workflow_dispatch` ve seans içinde nominal 30 dakikalık GitHub `schedule`
yedeğiyle tetiklenir. `concurrency` aynı depo içinde V2 defterine tek yazar
sağlar. Sıra: bağımlılık → cycle → arşiv kopyası → Git commit/push → kısa
Telegram → bildirim makbuzu commit/push → uygunsa haftalık mesaj. Push
denemeleri tükenirse iş kırmızı olur, başarısızlık artifact'i 14 gün tutulur.
Altın V2 workflow'u cycle öncesi `src.advisor_refresh` ile beklenen kapanışı
yenilemeyi dener. Bu adım kaynak hatasında üretim SQL'ini değiştirmez;
cycle, eksik tarih için yeni alımı kapatır. V2 tek yazar ilkesi depo başınadır;
iki depo birbirinin defterine yazmaz.

**Gözlemci** `.github/workflows/advisor-watchdog.yml` ayrı salt okunur iştir.
`advisor/watchdog.py` beklenen seans slotunu, son cycle başarısını, 45
dakikayı aşan seans içi boşluğu, fiyat/karar kapsamını, kurumsal belirsizliği,
analiz gününü, defter hash'ini ve Telegram makbuzunu denetler. Bulgular exit 1
üretir ama gözlemci hesabı tamir etmez ve karar koşusunu durdurmaz. Seans
dışı `session_check` kaydı, kaçırılmış seans içi koşuyu başarılı gösteremez.

**Yedek/kurtarma:** `advisor/recovery.py`, izinli veri/kod/ayar/SQL dosyalarını
SHA-256 manifestli zip yapar. Geri dönüş yalnız önceden var olmayan boş
dizine yapılır; yol geçişi ve checksum denetlenir. `recovery-check`, geçici
dizine açıp dört hesabın nakit/hash tutarlılığını inceler, mevcut üretim
dosyalarının üstüne yazmaz. Ayrı `advisor-recovery.yml` düzenli recovery
denemesi yapar. 2026-09-22 gerçek arşiv kopyalarında geri dönüş dört hesap
için doğrulandı.

**Karar kapsülü:** `advisor/capsule.py`, her V2 koşusunun girdi defteri,
fiyat/özellik satırları, tahmin, model, ayar, zaman, karar sonucu, Python
`advisor/*.py` kaynakları ve bağımlılık sürümlerini sıkıştırılmış JSON'a
mühürler. `reproduce`, hash ve runtime eşliğini denetleyerek arşivlenmiş
kararı geçici, ağsız süreçte yeniden üretir. Bu kapsüller **güvenilir kendi
arşivi** içindir; başka birinden gelen kod paketini çalıştırma aracı değildir.
2026-09-22 sabit üretim kesitinde iki depodan toplam 143 mühürlü paket kendi
runtime/koduyla birebir üretildi. Daha eski kapsül öncesi kararların aynı
güçte yeniden üretim kanıtı yoktur. Paketler geçmiş defter bağlamını da
taşıdığı için depolama büyümesi izlenir.

**Zamanlama sınırı:** 2026-09-21/22 üretiminde yaklaşık 15 dakikalık
`workflow_dispatch` çevrimleri gözlendi; haricî çağırıcının kimliği ve
güvencesi doğrulanmadı. 30 dakika cron yedeği 2026-09-23'te yayımlandı,
fakat ilk gerçek yedek tetiklenmesi ve 45 dakika nöbetçi uyarısı
`ai/STATE.md` kesitinde henüz gözlenmemişti. GitHub zaman garantisi yok;
bu sistem kesintisiz stop gözetimi veya 15 dakika SLA'sı sunmaz. Sanal stop
yalnız çevrimin gördüğü geçerli fiyatla değerlendirilir.

## 13. Test katmanları, denetim yöntemi ve mevcut kanıt

**Sözleşme testleri** yapı/şema, eşik zemini, ortak motor hash eşliği, doküman
referansları, LLM sayı/plan sınırı ve ağ/gerçek dosya izolasyonunu zorlar.
**Mekanizma testleri** fiyat, takvim, model zaman ayrımı, karar, komisyon,
defter, kurumsal işlem, bildirim ve hata dönüşlerini sınar. **Uçtan uca
testler** geçici veri kökünde katkı → alım → tekrar → yeniden açılış → satış
→ değerleme/benchmark/teslim zincirini çalıştırır. Altın testleri de dış ağ,
gerçek DB ve gerçek log yazımını varsayılan olarak kapatır. BIST `tests/`
ve altın `tests/` ayrı paketlerdir; panel için `dashboard/test/` Node
testleri vardır. Mevcut proje kuralı: testin yeşilliğini sonuç üstünlüğü
kanıtı sanma; testin kaynağı mı davranışı mı sınadığını belirt.

**Komutlar (ilgili repo kökünden):**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/advisor_manifest.py --peer '../gold_tracking_system'
cd dashboard && npm test && npm run build
```

Python 3.12 ve `requirements-runtime.txt` doğrulanmış çalışma bağımlılıklarını
kurar; BIST `pyproject.toml` / Poetry de geliştirme tanımıdır. 2026-09-24
BIST durum kaydı, yerel V1 LLM sıra düzenlemesi sonrası tam pytest
sonucunu **1415 geçti** olarak kaydeder. Bu tarihli sayıdır, sabit test
sayısı iddiası değildir. Panel ve iki depo testleri 2026-09-23 denetim
sonrasında tekrar koşturuldu; son işin kendisi kod davranışı değiştirmediği
için burada yeni test başarısı iddia edilmiyor.

**Gerçek veri denetimi:** 2026-09-22 tarihli
`reports/URETIM-DENETIMI-2026-09-22.md`, sabit GitHub commit arşivlerinin
SQL/JSONL içeriğini, kapsül tekrarını, bağımsız muhasebe hesabını ve
kontrollü replay'i inceler. `scripts/audit_production.py` komutu geçici
**sabit kopya** bekler; gerçek üretim arşivine yazmadan yeniden üretim ve
düzeltme doğrulaması yapar. 2026-09-23'te düzeltmeler iki `main` dalına
yayımlandı; ilk yeni cycle ve panelde iki hesabın görünmesi `ai/STATE.md`
ile kaydedildi. Denetim raporundaki “henüz yayımlanmadı” cümlesi rapor
tarihinin durumudur, 2026-09-24'ün durumu değildir.

## 14. Açık sınırlar, doğrulanmış durum ve geliştirme alanları

### 2026-09-23/24 itibarıyla doğrulanmış

- BIST V2 canlı evreni 18 hisse; altın V2 tek GRAM ürünüdür. BIST30'un
  tamamı veya gerçek kullanıcı varlıkları kapsanmıyor.
- 2026-09-22 üretim kesitinde BIST ana strateji hesabında 1 alış, 0 satış;
  altın ana strateji hesabında 0 işlem vardı. Dört kitabın muhasebesi ve
  tekrar çevrimi bağımsız yöntemle sınandı. Bunlar tarihli kesittir.
- Model onayları kapalı; canlı tahmin sonucu ve canlı kalibrasyon düzeltmesi
  yoktu. V2 ekonomik üstünlük veya gerçek işlem güvenliği kanıtı yok.
- 2026-09-23 kod yayımlandı; ilk yeni BIST/altın `run_status.json` kayıtları
  `ok=true`, `skipped=false`. Parola sonrası panel iki hesabı gösterdi.
- 2026-09-24 **yalnız yerelde**, V1 BIST LLM zincirinin model sırası değişti;
  bu değişiklik üretim davranışı olarak anlatılmamalı.

### Henüz kapanmamış riskler veya dış kanıt gereksinimleri

1. İlk gerçek V2 satış/stop, aylık yeni katkı ve 20 seanslık tahmin sonucu
   canlıda henüz görülmedi; mekanizma testleri bu ekonomik/operasyonel
   olayların canlı kanıtı değildir.
2. Nominal 30 dakika cron yedeğinin gerçekten tetiklenmesi ve 45 dakika
   boşluk uyarısının gerçek koşuda çalışması henüz doğrulanmadı. Haricî
   15 dakika dispatch çağırıcısının kimliği bilinmiyor.
3. Telegram API makbuzu var, fakat 2026-09-15 sonrası alıcı dışa aktarımı
   elde olmadığından kullanıcının ekranında teslim bağımsız doğrulanmadı.
4. Altın eski V1 mutabakatında 303 yanlış “tamamlandı” bayrağı geçici
   kopyada düzeltildi; üretimde yeni uzlaştırıcı çalışıp arşiv yenilenene
   kadar eski bayraklar ve eski raporlar geçersiz kanıt sayılır.
5. Kişisel banka/broker komisyon ekstresi, saklama/MKK ücretleri, tarihsel
   İş Bankası makası, gerçek temettü ödeme belgesi ve BIST tarihsel üyelik
   arşivi yok. Mevcut maliyet/kârlılık bunları içeriyormuş gibi sunulmamalı.
6. Altın V1 bağımsız prim serisi ve FRED reel faiz kaynağı sorunlu.
   Bu eski rapor ölçümlerini etkiler; V2 modeline prim veya FRED yön skoru
   girdiği varsayılmamalı.
7. Altın GC=F referansında vadeli kontrat roll etkisi için 2026-11-25
   yeniden ölçüm backlog'dadır. Kapsül arşivlerinin depolama maliyeti de
   izlenecek.

### Projeye uygun geliştirme ölçütü

Yeni bir fikir değerlendirilecekse önce **hangi hattı** değiştirdiği
belirtilmeli: BIST V1 araştırma/LLM mi, BIST V2 sanal karar mı, altın V2 mi,
ortak panel mi, işletim/kanıt mı? Ardından değişen karar sözleşmesi, ihtiyaç
duyduğu gerçek veri, aynı bütçeli taban, zaman sızıntısı riski, komisyon/makas,
gerçek deftere dokunmadan deney ve başarısızlıkta davranış anlatılmalı.
Yeni oran kapısında hem payın hem paydanın sınırı incelenmeli. Gözlemci
işi durdurmamalı; durduran kapı yalnız bu çevrimin düzeltebileceği girdiye
bakmalı. “Veri yok” olumlu hükme dönmemeli. Kısıtlı kullanıcı bütçesi için
önce az parçalı ve geri alınabilir çözüm düşünülmeli.

## 15. Dış yapay zekâya verilecek çalışma talimatı

Bu belgenin tamamı veya seçilen bölümü aşağıdaki istemle birlikte verilebilir:

> Bu, çalışan ama getirisi kanıtlanmamış kişisel bir BIST + gram altın sanal
> karar sisteminin teknik bağlamıdır. Depolara erişimin yok; anlatılmayan
> dosya veya üretim sonucunu var sayma. Önerilerini mevcut V1/V2 sınırına
> göre ver. Her öneri için (1) çözdüğü somut sorun veya sınanacak hipotez,
> (2) değişecek modül/veri sözleşmesi, (3) gerekli dış veri ve maliyet,
> (4) aynı bütçeli al-tut veya mevcut politika karşısında ölçüm,
> (5) olası sessiz yanlış sonuç ve koruyucu test, (6) geri alma yolunu yaz.
> Önce canlı karar doğruluğu/kanıt, sonra arayüz kolaylığı düşün. Yeni
> özellik gerektirmeyen bulguyu da açıkça söyle. Gerçek para işlemi veya
> kanıtlanmamış getiri üstünlüğü varsayma.

**Paylaşım hijyeni:** Bu doküman bilerek API anahtarı, parola, bot tokenı,
kişisel portföy miktarı veya ham `events.jsonl` içermiyor. Başka sisteme
ham üretim arşivi, `.env`, karar kapsülü veya `latest.json` eklenirse
önce özel finansal/operasyonel alanlar ayrıca gözden geçirilmelidir.

## Kaynak hiyerarşisi ve hızlı dosya haritası

- Güncel kapsam/durum: `ai/PROJECT.md`, `ai/STATE.md`.
- Gerekçeli önemli kararlar: `ai/DECISIONS.md`; yaşanmış hata dersleri:
  `ai/LESSONS.md`; kullanıcı kısıtları: `ai/PROFILE.md`.
- V2 kullanım ve mimari: `docs/V2-REHBER.md`; 2026-09-16 uygulama planı:
  `docs/IYILESTIRME-2026-09-16.md`.
- Sabit üretim kanıtı: `reports/URETIM-DENETIMI-2026-09-22.md` ve aynı
  adlı JSON ekleri. Açık risklerin tarihli açıklaması:
  `reports/ACIK-RISKLER-2026-09-23.md`.
- Canlı davranışın kaynağı yorum/rapor değil `advisor/`, `src/`, workflow
  ve `dashboard/` kodudur. Raporlardaki tarihli sayı, yeni tarihte otomatik
  geçerli kabul edilmemelidir.
