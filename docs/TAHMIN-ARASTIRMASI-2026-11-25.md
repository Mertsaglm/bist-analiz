# BIST ve gram altın tahmin araştırması

25 Kasım 2026. BIST30'da 20 seanslık doğrudan sıralama, bu arşivde hem
göreli Ridge'i hem 120–20 momentumu geçti. Gram altında üç ufukta da sıfır
getiri tahmini en düşük mutlak hatayı verdi. Araştırma motoru iki sonucu aynı
zaman sıralı protokolle üretiyor. İlk BIST gölge kaydı 29 hisse ve altı
sıralayıcı için kapandı. Ekonomik karar ve canlı deneyler kendi kayıtlarıyla
izleniyor. [Ön kayıt](TAHMIN-ARASTIRMA-ON-KAYIT-2026-11-25.md)

## Projenin çalışma akışı

Amaç BIST ve İş Bankası gram altını için ayrı ayrı 50.000 TL başlangıç ve
aylık 5.000 TL katkıyla, faizsiz nakit ve eş bütçeli pasif karşısında
maliyet sonrası sanal serveti ölçmek. Katkılar performanstan arındırılır.
Kararlar günlük kapanış girdisiyle başlar. Taze kotasyon, işlem penceresi,
nakit, maliyet ve risk dolumu belirler. Mevcut pozisyonun koruyucu izlemesi
yeni girişten ayrıdır. Gerçek emir bağlantısı yoktur. [Proje kapsamı](../ai/PROJECT.md)

| Katman | Davranış ve kanıt |
|---|---|
| BIST V1 | Yahoo günlük OHLCV, düzeltilmiş getiri ve endeks verileri, KAP, EVDS → SQLite → deterministik SQL. Eski plan ve replay araçları kalır. Üretim V1 LLM kapalıdır. [Fiyat](../src/prices.py) · [Günlük akış](../src/otonom.py) |
| Altın V1 | Ons vadeli kapanışı ile EVDS USD/TRY'nin kesişimi teorik gramı üretir. Tick, prim, bağımsızlık bayrağı ve eski gram bazlı karar defteri ayrı tablolardadır. [Altın geçmişi](https://github.com/Mertsaglm/gold_tracking_system/blob/1bad05fc791c3bc1512ced7327a596189c4b7411/src/history.py) · [Kapanış yenilemesi](https://github.com/Mertsaglm/gold_tracking_system/blob/1bad05fc791c3bc1512ced7327a596189c4b7411/src/advisor_refresh.py) |
| V2 eğitim | İki piyasada canlı taban 20 seanslık mutlak getiri Ridge. Sekiz temel özellik momentum, trend, oynaklık, drawdown ve RSI'dan gelir. Ölçek eğitim verisinden öğrenilir. Altın geçmişi sentetik kapanış içerdiği için gerçek gram ATR'si türetilmez. [Özellik ve eğitim](../advisor/learning.py) |
| V2 karar ve kayıt | Kapanış girdisi, eğitim/model, gündem, fiyat, kurumsal işlem, olgun tahmin ve risk → sanal alış/satış → zincirli defter, karar kapsülü, `latest.json`. BIST fiyatı İş Yatırım gecikmeli referansıdır. Altın, Döviz.com'daki İş Bankası alış/satış kotasyonudur. [Çevrim](../advisor/service.py) · [Kotasyon](../advisor/marketdata.py) · [Defter](../advisor/ledger.py) |
| İşletim ve çıktı | GitHub Actions günlük veri ile V2 çevrimlerini ayrı yürütür. Nöbetçi ve telafi eksikleri kontrol eder. Telegram makbuzu son görünümün defter özetine bağlanır. Ortak Vercel paneli iki görünümü okur. [İşletim](ISLETIM-2026-11-18.md) · [Panel veri okuması](../dashboard/lib/status.mjs) |
| Deneyler | SMA50, yakın dönem Ridge ve diğer eski adaylar ayrı sanal defterlerde izlenir. %80 çekirdek/%20 taktik beş kolun ortak T0'ı kapalı. 25 Kasım için planlanan momentum portföyü kendi ilk uygun seansını bekliyor. [Çekirdek ve taktik](PORTFOY-DENEYI-2026-10-01.md) · [Bağımsız momentum](../advisor/forward_momentum.py) |

Temmuz–Ağustos V1 faktör ve LLM replay'leri yeterli kenar bulmadı. Eylül'de
V2 gerçekçi maliyet, ayrı bütçe ve olay defterine geçti. Ekim'de
çekirdek/taktik ve uzmanlaşmış modeller eklendi, ardından ek ücretli altyapı
kapatıldı. Kasım'da kaynak, teslim, işlemsizlik ve zaman sırası denetimleri
ilerledi. Önceki 126 tarihli BIST göreli getiri regresyonunda LightGBM
Rank IC +0,1213, Ridge −0,0120 idi. Ayrı 37 seanslık maliyetli replay'de
LightGBM 54.385,57 TL, Ridge 54.638,47 TL, pasif 55.322,11 TL üretti.
Bu çalışmada evren, tarih kesiti ve seans eşlemesi farklı olduğu için
eski ve yeni Rank IC değerleri ayrı kesitler olarak saklanır.
[Eski proje kapsamı](../ai/archive/PROJECT-V1-2026-10-01.md) · [Kasım karşılaştırması](BIST-ILERI-SIRALAMA-2026-11-18.md)

## Üretim ve arşiv doğrulaması

| 25 Kasım seans öncesi kontrol | BIST | Gram altın |
|---|---|---|
| SQL arşivi | 2015-01-02–2026-11-24, 73 isim, 209.345 bar. 24 Kasım 71/73, BIST30 30/30, beş kur/endeks serisi son güne ulaştı. Eksikler ARCLK ve SELEC. | 2016-01-04–2026-11-23, 2.645 teorik gram günü. Bütün ons girdileri GC=F. USD/TRY tarafı 2.645/2.645 EVDS satış kuruyla eşleşti. |
| V2 görünümü | 21.54 İstanbul, analiz 24 Kasım, 33/33 fiyat, ana hesap 60.000 TL nakit. | 21.49 İstanbul, analiz 23 Kasım, 1/1 fiyat, ana hesap 60.000 TL nakit. |
| Defter ve bildirim | 38.733 olay. Telegram 304 aynı görünüm hash'ine bağlı ve `closing_complete=true`. | 9.409 olay. Telegram 418 aynı görünüm hash'ine bağlı standart V2 bildirimi. Günlük V1 rapor koşusu başarılı. V2 kapanış makbuzu ayrı izleniyor. |
| Model ve deney | Canlı Ridge `approved=false`, tamamlanmış ana strateji roundtrip 0. Momentum ilk uygun seans bekliyor. | Canlı Ridge `approved=false`, tamamlanmış ana strateji roundtrip 0. Ortak T0 iki uzak ayarda da boş. |

[BIST arşiv ve bildirim kesiti](https://github.com/Mertsaglm/bist-analiz/commit/591cb3a3979df11b53bfd2b4d3ffb1a3f1a54d6c) · [BIST günlük arşiv koşusu](https://github.com/Mertsaglm/bist-analiz/actions/runs/45463514435) · [Altın arşiv kesiti](https://github.com/Mertsaglm/gold_tracking_system/commit/76b8dd2edcf317ba05e7c5dbe31415bfb5739e2d) · [Altın günlük raporu](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/45464140195)

BIST V2 işi defteri yazdıktan sonra eksik kapanış telafisini hata koduyla
bildirdi. GitHub koşu sonucu başarısız ve defterdeki Telegram kapanış
makbuzu tamamlanmış. Ölçümler farklı aşamaları kapsıyor.
[BIST V2 koşusu](https://github.com/Mertsaglm/bist-analiz/actions/runs/45464353034)

İki SQL geçici SQLite'a geri yüklendi ve bütünlük kontrolünden geçti.
Uzak ana defterlerin zinciri baştan doğrulandı. Yerel çalışma ağacındaki
SQL ve SQLite daha eski kesitlerdir. Test, ölçüm ve rapor dosyaları dışındaki
finansal kayıtlar geçici dizinde salt okunur kullanıldı.

SQL SHA-256 değerleri BIST için
`32d834c01c0204e104d89aad4890ab4218091e67dc8305e3f485c5bf0f9b1897`,
altın için
`4ce18e082989c4103c04f90ab3d8ce2aad3ee20de6bf783152819757616bb601`.

## Veri ve hedef denetimi

| Bulgu | Araştırma karşılığı |
|---|---|
| V2 mutlak hedef vadesi sembolün ileri barından geliyor. Tek endeks de seans atlayabiliyor. | Bu pakette her isim aynı vade tarihine bağlanır. XU030'un tek başına kaçırdığı 16 gün en az 24 üyedeki işlem kaydıyla tamamlandı. 24 Kasım arşivinde tek-XU030 karşılaştırması 86.406 eşlenebilir 20 seanslık satırın 7.085'inde farklı vade gösterdi. Fark hem sembol hem endeks takvimi açıklığı içeriyor. Yeni test döneminde bu ilk karşılaştırmanın 3.780 ham satırında vade farkı çıkmadı. [V1 seans kaynağı](../src/calendar_bist.py) · [V2 etiket](../advisor/outcomes.py) |
| Genel izleme kümesinde 32 aktif isim var. Tarihli çekirdek BIST30 30 isim. | Araştırma çekirdek üyelik seçicisini kullanır. Ekim'de TRMET giriş ve DSTKF çıkışı resmî duyuruyla tutarlı. Tarihsel üyelik dosyası 25 Eylül öncesine uzanmadığı için Kasım üyeleri uzun geçmişte sabit, geriye dönük bir araştırma örneklemidir. [Kayıt](../advisor/universe-history.json) · [Borsa İstanbul dönemsel duyuruları](https://borsaistanbul.com/duyuru/15598/bist-pay-endeksleri-donemsel-degisiklikleri) |
| 30 üyenin tamamında son kapanış var. Uzun ve kesintisiz özellik geçmişi daha dar. | Son desen 29/30, SASA'nın sıfır hacimli barları var. Ortak tarihsel testte günde 27/30, eksikler SASA, TRALT ve TRMET. Tarihsel yeni ihraç/eksik bar kapsamı sonuçların paydasında açık. CCOLA/HEKTS düzeltmeleri ana arşiv için açık kalır. [24 Kasım veri denetimi](DENETIM-2026-11-24.md) |
| Göreli hedefin sepeti ve ekonomik pasif kol ayrı tanımlar. | Aynı gün 27 eşleşen hisseyle temettü/bölünme düzeltilmiş brüt eşit ağırlık referansı oluştu. Bir tarihte bu sabitin her hisseden çıkarılması sıralamayı korur. Kullanılabilir barlar ve güncel evrenle oluşan bu kıyas, eş katkılı pasif hesabın net tasfiye kıyasından ayrıdır. [Pasif hesap](../advisor/benchmark.py) |
| 2.645 gram satırının her biri aynı gün etiketli GC=F × EVDS kur bölü troy ons formülüne sayısal olarak uyuyor. | Ons ve kur ayrı zamanlarda oluşur, vadeli kontrat geçişi spot değişiminden ayrılır. Ortak tarih etiketi eşzamanlı fiyat anlamına gelmez. Banka makası, prim ve vergi kotasyon katmanında ölçülür. [CME kontrat ve uzlaşma kuralları](https://www.cmegroup.com/markets/metals/precious/gold/specs) |
| BIST KAP 3.992 kayıt, 28 Nisan–24 Kasım. Altında EVDS var, temel V2 eğitiminde makro kullanılmıyor. | KAP ve temel veriler daha kısa ayrı kapsama sahip. Yayın ve ilk erişim tarihleri saklanmalı. Makro yalnız o gün yayımlanmış değerle birleştirilmeli. DFII10 veri yayın gecikmesine bir örnek. DTWEXBGS geniş dolar endeksi, modelde DXY adıyla taşınmamalı. [FRED DFII10](https://fred.stlouisfed.org/series/DFII10) · [ALFRED sürümleri](https://alfred.stlouisfed.org/series?seid=DFII10) |

FRED'in 23 Kasım DFII10 gözlemi için gösterdiği güncelleme 25 Kasım
00.16 İstanbul. Gözlem tarihini erişim anı kabul eden bir birleştirme,
değeri daha erken bir BIST kararına taşıyabilir. Geçmiş ek girdilerde
yayımlanma tarihini ve ilk erişim zamanını ayrı tut.
[FRED yayın zamanı](https://fred.stlouisfed.org/series/DFII10)

Canlı kalibrasyon zaten mevcut. Olgunlaşan tahminlerden örtüşmeyen dönemleri
seçip en son 24 dönem ortalama ham hatasını izliyor. En az 10 dönemden sonra
düzeltme ±2 puanla sınırlı. Yeni araştırmadaki OOS affine katsayı,
olasılık ve aralıklar bu canlı düzeltmeden bağımsızdır. Özelleşmiş altın
Ridge geçmiş ons/kur özelliklerini doğrudan gram modeline ekler. Bu pakette
ayrıca ons ve kuru ayrı hedefler olarak eğiten baskın olmayan bir rakip var.
[Canlı hata kalibrasyonu](../advisor/outcomes.py) · [Özelleşmiş Ridge](../advisor/specialized.py)

## BIST tarihsel sonuçları

25 Şubat–31 Ağustos 2026. Her ufuk 126 sinyal günü, 26 test bloğu ve
3.402/3.780 ortak hisse-gün. 5, 20 ve 60 seans için sırasıyla 26, 7 ve 3
örtüşmeyen başlangıç var. Sonuçlar aynı tarihteki hisseleri bağımsız kabul
etmeden yorumlanmalı. [BIST ölçüm makbuzu](../reports/forecast-research-2026-11-25/bist.json)

| Sıralayıcı | 5 seans IC | 20 seans IC | 60 seans IC | 20 seans ilk beş brüt farkı |
|---|---:|---:|---:|---:|
| 120–20 momentum | +0,0030 | −0,0014 | −0,0404 | +1,51 puan |
| Göreli Ridge | +0,0055 | −0,0309 | −0,0883 | +0,18 puan |
| Elastic Net | +0,0337 | +0,0286 | −0,0111 | +1,15 puan |
| LightGBM regresyon | +0,0323 | +0,0677 | −0,0120 | +1,45 puan |
| LightGBM LambdaRank | +0,0434 | +0,0984 | +0,0058 | +1,89 puan |
| Ridge ve ek özellik grubu | — | −0,0643 | — | −1,58 puan |

20 seansta LightGBM regresyonun MAE'si 6,689 → kalibrasyonla 6,685 puan,
sıfır göreli tahminin hatası 6,713. Ridge 6,835 → 6,758 puan. Affine
kalibrasyon sıralamayı bu kesitte değiştirmedi. Lojistik Brier 0,2510,
basit sıklık 0,2481. %80 hedefli ham hata aralığı %78,3 kapsadı ve
18,86 puan genişti. EWMA ile %87,5 kapsama için genişlik 24,56 puana çıktı.
Aralık büyüklüğü pozisyon kararı için ekonomik karşılığı ölçülmeden
kullanılmaz.

Bu bölümün öncelikli hipotezi 20 seanslık doğrudan sıralama. Ortalama Rank
IC ve ilk beş farkı birlikte izlenmeli. Örneğin 5 seansta LambdaRank daha
yüksek IC verirken momentumun ilk beş farkı daha yüksek. Modelin faydası
stratejinin hangi sıraya ve ne sıklıkta işlem yaptığına bağlıdır.

## Altın tarihsel sonuçları

17 Şubat–27 Ağustos 2026. Ufuk başına 126 ortak tarih ve 26 test bloğu.
MAE teorik gramın brüt getiri hatası, yüzde puan. [Altın ölçüm makbuzu](../reports/forecast-research-2026-11-25/gold.json)

| Tahmin | 5 seans | 20 seans | 60 seans |
|---|---:|---:|---:|
| Sıfır getiri | 3,30 | 5,90 | 8,04 |
| Eğitim ortalaması | 3,37 | 7,99 | 16,91 |
| Temel Ridge | 3,85 | 11,96 | 31,99 |
| Doğrudan gram, ons/kur özellikli Ridge | 3,98 | 12,11 | 32,40 |
| Ayrı ons ve kur Ridge | 3,99 | 12,34 | 34,03 |
| Elastic Net | 3,45 | 9,90 | 27,46 |

20 seansta affine düzeltmeyle Ridge MAE 15,58'e çıktı. Nominal %80
aralığın kapsaması ham hata için %12,7, EWMA ile %26,2. 60 seansta iki
aralık da bu kesitte %0 kapsadı. Yalnız üç örtüşmeyen 60 seans başlangıcı
vardı. Sonuç, geçmiş kalibrasyonun rejim kaymasında uygulanabilirliğini
yeniden sınamayı gerektiriyor. 20 seans lojistik Brier 0,5587,
basit sıklık 0,4245. 60 seans Brier azalsa da log loss 2,44'ten
5,45'e çıktı, yüksek güvenli hatalar ayrıca izlenmeli.

**Bacak uzmanlaşması için ek sınav.** Aynı özellik matrisi ve Ridge
ayarlarıyla iki log bileşen tahmininin toplamı, toplam log getiriyi tek
modelle tahmin etmeye eşdeğerdir. Bu yüzden 5/20/60 seanslık aynı test
katlamaları ikinci kez kullanılır. İlk kol gram log getirisini gram ve
iki bacağın tüm özellikleriyle tahmin eder. İkinci kol ons ve kuru kendi
dörder momentum/trend/oynaklık özelliğiyle ayrı eğitir. Sıfır ve ilk
deneyin doğrudan gram kontrolleri aynıdır. Aynı Ridge ayarlarında iki
tam özellikli bacağın toplamı sayısal eşitlik kontrolüdür. Gram bileşik
MAE, RMSE ve bacak başına sıfır getiri kıyası raporlanır.

Ek sınavın 5/20/60 seans gram MAE'si uzmanlaşmış bacaklarda
3,76 / 9,48 / 20,00 puan. Bütün özellikleri alan doğrudan log modelinde
3,99 / 12,34 / 34,03. İki tam özellikli bacak ile doğrudan log model
arasındaki en büyük tahmin farkı 4 × 10⁻¹⁴ puanın altında. 20 seansta
kur bacağı 0,21 puan hatayla sıfırın 1,60 puanını geçti. Ons bacağı
9,46 puanla sıfırın 6,25 puanının gerisinde. Bu kesitte gramdaki ana
hata ons tarafında. Kur bulgusu yakın dönem kur trendi ve daha eski
rejimlerle ayrıca karşılaştırılmalı.
[Eşleşen bacak sınavı](../reports/forecast-research-2026-11-25/gold-legs.json)

İş Bankası'nın gerçek kaydedilmiş referans kotasyonlarıyla mevcut zamanlama
replay'i de çalıştırıldı. 25 Eylül–24 Kasım'da 42 seansın 37'sinde
1.191 geçerli giriş gözlemi vardı. İki kol 60.000 TL katkı aldı ve ikişer
alış yaptı. İlk uygun %4 kolu 48.563,34 TL ve 9,01 gram, üç seansa kadar
%2,75 bekleyen kol 48.330,93 TL ve 8,97 gram üretti. İkinci alım
2 Kasım yerine 5 Kasım gerçekleşti. Alımlar sonraki farklı referans
kotasyonunda simüle edildi. Son değerler aynı geç banka alış fiyatından
hesaplandı. 232,41 TL
fark tek farklı katkı zamanına dayanıyor. Ayrı ileri zamanlama deneyinin
amacı bu farkın farklı makas ve fiyat rejimlerinde tekrarlanmasını ölçmek.
[Kotasyon replay makbuzu](../reports/forecast-research-2026-11-25/gold-quote-timing.json)

## İleri kayıtlar ve araştırma sırası

Önceki 32 Ridge/LightGBM tahmininin vadesi 15 Aralık 2026. Bağımsız
30 hisse momentum sıralamasının vadesi 22 Aralık. İki dosya üretimdeki
baytlarla birebir eşleşti. Yeni 20 seans gölge kaydı 25 Kasım 01.09
İstanbul'da 24 Kasım kapanışıyla ayrı dosyaya yazıldı. Altı sıralayıcı,
29/30 hisse, 756 eğitim tarihi ve 21.607 eğitim satırı. Son eğitim etiketi
23 Kasım. Sabit vade 22 Aralık ve ilk ölçüm `vade bekleniyor` döndürdü.
[Önceki sıralama](../reports/bist-forward-2026-11-17.json) · [Önceki momentum](../reports/champion-challenger-2026-11-24/bist-momentum-forward.json) · [Yeni yerel gölge kaydı](../reports/forecast-research-2026-11-25/bist-shadow.json)

| Araştırma sorusu | Sınama ve ölçülebilir çıktı |
|---|---|
| Sıralama ekonomik katkıya dönüyor mu? | LambdaRank, regresyon ve momentum için aynı net mutlak getiri ve maliyet kuralı altında sıralamayı tek değişken yap. Eş sermaye, pasif, nakit, harcanan komisyon, pozisyon saatleri, devir ve net düşüş. Aynı pozisyonda işlem sıklaştırmamak için giriş ve elde tutma sırası ayrı ölçülür. Önceki 37/39 seans replay'leri karşılaştırmanın gerekçesidir. |
| Basit ek sinyaller hangi günlerde faydalı? | Hacim ile kesitsel dönüşümleri ayrı ablation, ardından BIST30/sektör göreceli momentum, beta ve piyasa genişliği. BIST fiyat sıralama ile piyasa zamanlaması için ayrı hedef, örneklem ve benchmark. Sektör ve şirket kimliği o gün bilinen kayda bağlanır. |
| Ortalama getiriden önce risk tahmin edilebilir mi? | Geçmiş oynaklık ve EWMA'ya karşı sade GARCH ve doğrudan kuantil regresyon. Kapanış getirisi aralığı ile pozisyon ömrü içi maksimum olumsuz hareket ayrı hedef. Pinball, kapsama, genişlik ve yüksek oynaklık dönemlerinde hata; iyileşirse eş risk bütçeli tahsis deneyi. [Hansen ve Lunde](https://doi.org/10.1002/jae.800) · [Xu ve Xie](https://proceedings.mlr.press/v139/xu21h.html) |
| Altında en iyi tahmin hedefi fiyat mı, katkı maliyeti mi? | Bir sonraki uygun banka kotasyonunda daralma olasılığı ve beklenen gram farkı. Sinyal saati, sonraki farklı kotasyon ve azami bekleme süresi sabitlenir. Fiyat, makas ve kaçan yükseliş ayrı ölçülür. GC=F roll duyarlılığı ve bağımsız spot ile USD bacağının eşzamanlılığı fiyat çalışmasından önce doğrulanır. |
| Model birleştirme ve rejim uyumu faydalı mı? | OOS hatalarının tarih bazında korelasyonunu çıkar. BIST sıra ortalaması veya altın tahmin ortalaması eş ağırlıklı taban olsun. Döneme göre ağırlıklandırma yalnız geçmişte olgunlaşmış hatalarla güncellenir. Az arama bütçesi ve bütün aday kaydı korunur. [Hyndman ve Athanasopoulos](https://otexts.com/fpp3/combinations.html) · [Aye ve diğerleri](https://repository.up.ac.za/bitstream/2263/45456/3/Aye_Forecasting_2015.pdf) |
| Daha karmaşık modeller ne zaman bilgi ekler? | CatBoost/XGBoost, küçük açıklanabilir spline ve uzun/kısa pencere Ridge, eş örneklemde kontrollü rakipler. KAP NLP yalnız tarihli metin ve ilk yayın saatiyle. LSTM/Transformer/temel modeller sınırlı ayrı araştırma. RL ve otomatik politika ağırlıklandırması önce maliyetli simülasyon ve karar sonrası veri ile sınanır. [Gu, Kelly ve Xiu](https://academic.oup.com/rfs/article/33/5/2223/5758276) · [Hanauer ve Kalsbach](https://www.sciencedirect.com/science/article/pii/S0165188923001318) · [Bailey ve diğerleri](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) |

## Tekrar üretim

İki SQL arşivini ilgili repo şemasıyla yalnız boş, ayrı bir geçici SQLite
dosyasına geri yükle. Altının restore komutu hedefteki mevcut DB'yi değiştirir.
`BIST_DB` ve `GOLD_DB` bu geçici kopyalara, `BIST_NEXT_DB` ise vade tarihinde
veya sonrasında aynı kaynak zincirinden alınmış güncel kopyaya işaret eder.
Araştırma bağımlılıkları `requirements-research.txt` içindedir.

```sh
python -m scripts.forecast_research --market bist --database "$BIST_DB" \
  --asof 2026-11-24 --output /tmp/bist-forecast-result.json
python -m scripts.forecast_research --market gold --database "$GOLD_DB" \
  --asof 2026-11-23 --output /tmp/gold-forecast-result.json
python -m scripts.gold_leg_research --database "$GOLD_DB" \
  --schedule /tmp/gold-forecast-result.json --output /tmp/gold-legs-result.json
python -m scripts.forecast_rank_shadow measure --database "$BIST_NEXT_DB" \
  --trial reports/forecast-research-2026-11-25/bist-shadow.json
```

Yeni ileri dosya için `forecast_rank_shadow freeze`, `--database`,
`--source-ref` ve henüz var olmayan ayrı `--trial` kullanır. Çıktılar
kaynak ve kod hash'lerini, çalışma sürümlerini, aday sonuçlarını, test ve
kalibrasyon tarihlerini taşır. Model eğitimi bu CPU araştırma komutlarında,
saatlik portföy işi kendi akışında yürütülür.

25 Kasım yerel doğrulamasında 42 hedefli test geçti. BIST paketinde
1.545 test geçti ve önceden kaldırılmış `Proje Yardımcısı/yeni-proje.sh`
dosyasını arayan altı şablon testi başarısız oldu. Altın paketinde 1.049
test geçti, 14 atlandı. 39 ortak motor modülü eşleşti.
