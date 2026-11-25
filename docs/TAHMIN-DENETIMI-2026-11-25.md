# İki AI denetimine verilen teknik yanıt

25 Kasım 2026. BIST için masraflı saf sıralama, uzun 5 seans sınavı ve
ara düşüş tahmini çalıştırıldı. Altın için drift, hibrit gram ve aynı gün
banka kotasyonu kıyasları üretildi. Yeni 5 seans gölge kayıt açıldı.
Üretim ve yayımlama işlemleri bu oturumda yalnız okundu.
[Ek deney kuralları](TAHMIN-DENETIMI-ON-KAYIT-2026-11-25.md)

## BIST sıralama ve net servet

Eski 126 tarihin günlük IC ve ilk beş farkları, aynı tarih bloklarıyla
2.000 kez örneklendi. 20 seans blokta LambdaRank tek başına IC aralığı
**[+0,052, +0,146]**. Regresyona karşı eşli IC farkı **[−0,016, +0,077]**,
momentuma karşı **[−0,058, +0,273]**. Momentum karşısındaki ilk beş brüt
farkının aralığı **[−2,61, +3,81] puan**. Dolayısıyla bütün sinyallerin
sıfırla aynı olduğu iddiası bu kesitte desteklenmiyor. Model üstünlüğü
iddiası da desteklenmiyor. 10 ve 40 seans blok duyarlılığı, katlama
sonuçları ve rastgele beşli referansı ayrı kayıtta. Rastgele beşli her
tarihte yeniden çekilir ve gerçek bir elde tutma politikası sayılmaz.
20 seans rastgele referansının merkezî %95 aralığı −0,67 ile +0,71 puan.
126 tarihte 20 seans için 7, 5 seans için 26 örtüşmeyen başlangıç var.
Bunlar kesin bağımsız örnek sayısı değildir.
[Eşli ölçüm ve katlamalar](../reports/forecast-audit-2026-11-25/bist.json)

25 Eylül–24 Kasım arasındaki 42 gerçek seanslı replay'de tarihli BIST30,
eş 60.000 TL katkı, ortak %80 çekirdek, %20 taktik, ilk 5 giriş ve ilk
10 tutma kuralı kullanıldı. OHLC'den türeyen açılış fiyatı ve stop dolumu
varsayımdır. Taktik devir, alım ve satım tutarlarının ortalama hesap
değerine oranıdır.

| Kol | 1× son net TL | 1,5× | 2× | 1× taktik alım/satış | 1× taktik devir |
|---|---:|---:|---:|---:|---:|
| Pasif | 52.634,27 | 52.469,25 | 52.326,79 | 74/0 | %19,8 |
| Saf göreli Ridge | 52.576,44 | 52.411,37 | 52.197,89 | 36/27 | %159,7 |
| Saf 120–20 momentum | 52.135,60 | 51.986,51 | 51.790,42 | 31/22 | %115,0 |
| Saf LambdaRank | 51.752,75 | 51.649,82 | 51.453,16 | 28/19 | %97,9 |
| Eşit sıra ortalaması | 51.779,42 | 51.648,65 | 51.366,88 | 33/23 | %128,7 |
| LambdaRank ve mutlak Ridge kapısı | 51.796,08 | 51.633,96 | 51.506,24 | 28/19 | %98,7 |

1× saf LambdaRank momentumdan **382,85 TL**, pasiften **881,52 TL**
geride. Kapıyı kaldırmak 1× koşuda **43,33 TL** daha düşük değer verdi.
Fark 1,5× koşuda yön değiştirdi. Bu kesit, kapının genel etkisi hakkında
karar vermek için kısa. Çıktıda günlük net değer, TWR, düşüş, masraf,
kapsam ve stop sayısı var. Diğer tahsis sıklıkları bu pakette ayrı sınanmadı.
[Maliyetli replay](../reports/forecast-audit-2026-11-25/bist.json)

## Üyelik, takvim ve risk

2015'te başlayan 73 isimli arşivden 2018-10-17–2026-11-12 arasında
**324 eşli 5 seans başlangıcı** ve 25 katlama çıktı. Kasım sabit üyeleri ve
geçmiş 63 seans işlem tutarıyla seçilen likidite evreni ayrı eğitildi.
Eşit faktör bileşiği IC'si sabit evrende **+0,0202**, likidite evreninde
**+0,0053**. Momentum ilk beş farkı **+0,070 → +0,095 puan**.
Regresyon ilk beş farkı **+0,157 → +0,065**, hedefi kırpılan regresyon
**−0,023 → −0,030**. İlk koşu sonrasında eklenen LambdaRank duyarlılık
kolunda IC yaklaşık **−0,0001 → −0,0040**, ilk beş farkı
**−0,146 → +0,042**. Uzun sınavda ağaç modelleri sekiz ortak temel
özelliği kullanıyor. Eldeki 73 ismin dışındaki ve arşivden çıkmış
şirketler eksik. Bu test evren duyarlılığını gösteriyor. Resmî tarihsel
BIST30 üyelik yanlılığının büyüklüğü açık.

Doğrudan %10 ara düşüş kuantili, ampirik referansa göre pinball kaybını
sabit evrende **0,933 → 0,907**, likidite evreninde **1,010 → 0,962**
puana indirdi. Alt sınır ihlali sırasıyla **%11,45** ve **%11,52**.
Hedef, karar kapanışından sonra gelen beş seansın en düşük düzeltilmiş
fiyatıdır. Banka dolumu, pozisyon stop testi ve otomatik karar kapısı
olarak kullanılmaz. [Uzun sınav ve kuantil makbuzu](../reports/forecast-audit-2026-11-25/bist-long.json)

XU030'un eksik olduğu 16 günün 11'inde XU100 var. 16 günün tamamında
70–73 pozitif hacimli hisse kaydı var. Yeni birleştirilmiş takvimle
**20 ileri seans** karşılaştırmasında 86.874
eşlenebilir satırın **480'inde** sembol barı vadesi piyasa vadesinden
farklı. Farkların tamamı 2024'te. Önceki 7.085 sayısı yalnız XU030'a
göreydi. Üretim eğitimine ve eski tahmin çözümüne geçiş, yeni hedef
sürümünü ve ayrı geriye uyumluluk testini gerektiriyor.
[Arşiv ve mühür denetimi](../reports/forecast-audit-2026-11-25/coverage.json) · [Borsa İstanbul tatil kayıtları](https://www.borsaistanbul.com/resmi-tatil-gunleri)

## Ölçüm sözlüğü

| Rapor ve sayı | Hedef ve vade | Evren ve tarih | Payda veya ölçüm gücü |
|---|---|---|---|
| Canlı BIST Ridge MAE 10,861 | Mutlak düzeltilmiş getiri, 20 seans | Geniş V2 eğitim evreni. 2017-10-18–2026-10-02 ilk/son ekonomik başlangıç. | 2.763 eğitim tarihi, 192.883 eğitim satırı. 113 örtüşmeyen ekonomik başlangıç MAE paydasıyla aynı sayı değildir. |
| 17 Kasım göreli BIST Ridge −0,0120, LightGBM +0,1213 IC | Göreli getiri, 20 seans | O gün seçilmiş 32 isim, 2026-04-16–10-19 | 126 gün, 3.942 hisse-gün. Eski rapor ayrı örtüşmeyen başlangıç sayısını vermiyor. |
| 25 Kasım BIST Ridge MAE 6,8355 ve LambdaRank IC +0,0984 | Ortak vadeli brüt göreli getiri, 20 seans | Sabit Kasım BIST30, ortak 27 isim, 2026-02-25–08-31 | 126 gün, 3.402 hisse-gün, 7 örtüşmeyen başlangıç. |
| Canlı altın Ridge MAE 5,350 | Teorik gram mutlak getiri, 20 seans | Geniş geçmiş. 2018-11-19–2026-10-22 ilk/son ekonomik başlangıç. | 2.426 eğitim tarihi, 97 örtüşmeyen ekonomik başlangıç. |
| 25 Kasım altın Ridge MAE 11,9638 | Teorik gram mutlak getiri, 20 seans | Son 126 ortak hedef tarihinin kesiti, 2026-02-17–08-27 | 126 gün, 26 katlama, 7 örtüşmeyen başlangıç. |

Farklı evren, hedef ve dönemlerden gelen sayılar model ilerlemesini
doğrudan ölçmez. Özellikle eski altın üretim MAE'si ile yeni 126 tarihli
Ridge aynı değerlendirme örneğine sahip değildir.

Önceki aralık makbuzu iki uçtaki pinball kaybını zaten içeriyordu.
Buradan hesaplanan %80 interval score, 20 seansta BIST ham/EWMA için
33,76/33,22, altında 99,85/97,31. Düşük değer daha iyi. 60 seansta
EWMA iki piyasada skoru kötüleştirdi. Kapsama tek başına seçim ölçütü
olarak kullanılmadı.

## Altın drift ve zamanlama

20 seansta kur Ridge MAE **0,210**, 20 seans geçmiş drift **0,241**,
60 seans drift **0,287**, eğitim ortalaması **0,655**, sıfır **1,595**.
5 seansta kısa drift **0,0693**, Ridge **0,0695**. Sıfır ons ve kur Ridge
birleşimi 20 seansta gram MAE'sini **6,235** puana getiriyor. Sıfır gram
**5,902**. 5 seansta en iyi basit hibrit farkı **3,3043 → 3,2955** puan.
Yön tahmini mevcut bulgularla ekonomik politika adayı olarak ilerletilmedi.
Altın zamanlama ve risk deneyleri ayrı araştırma olarak kalır.
[Drift ve hibrit karşılaştırması](../reports/forecast-audit-2026-11-25/gold-legs.json)

Gün içi %4 ilk uygun ile 15.30'a kadar %2,75 bekleyen kollar, her
gözlenen günde ayrı varsayımsal 1.000 TL ile sonraki taze kotasyonda
karşılaştırıldı. 37 gözlenen giriş gününde eşleşen dolum **36**, farklı
zamanlı dolum **22**. Eşleşen alımlarda bekleyen kolun satış fiyatı
ortalama yaklaşık **%0,09** daha düşük. Bir erken kapanış gününde bekleyen
kol dolmadı. Bu ayrı günlük deneme gerçek aylık katkı tekrarından
farklıdır. Bir önceki günler arası tekrarda ayrışan katkı sayısı birdi.
[Gün içi kotasyonlar](../reports/forecast-audit-2026-11-25/gold-timing.json)

24 Kasım gündüzünde çekirdeğin %4 sınırına uyan **32/32** geçerli altın
giriş gözlemi vardı. Akşam kotasyonu bütün günün uygunluğunu temsil
etmiyor. Bu oturumdaki kontrol 25 Kasım seansından önce yapıldı. İki
uzak ayarda T0 boş. Yeni altın arşiv işi başarılı oldu ve yalnız Kasım
CSV'si değişti. SQL blob ve V2 defter başı aynı kaldı. Sonraki T0 kabulü
için gün içi eşleşme ve iki piyasanın canlı kabulü açık. Bağımsız BIST
sanal kolları ortak T0'dan ayrı kimlikle yürütülebilir.
[Son altın arşiv koşusu](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/45501115930)

Altın SQLite kesitinde türetilmiş prim **527 kayıt ve 83 tarih**,
vadeli GCZ26 kaynak kirliliği **342 kayıt ve 19 tarih**. Her iki
grup da bu deneylerde özellik yapılmadı. Tarihsel teorik seride
2.645 satırın kaynak etiketi yalnız `GC=F`, tekil kontrat kimliği yok.
CME'nin Kasım sonu takvimi Aralık kontratından Şubat aktif kontratına
geçişi tarif ediyor. Bu takvim Yahoo'nun sürekli seriyi hangi barla
geçirdiğini göstermiyor. Bağımsız spot ve eşzamanlı kur farkı açık.
[CME uzlaşma ve roll kuralları](https://www.cmegroup.com/content/dam/cmegroup/notices/ser/2025/12/ser-9637.pdf)

## Sözleşme, mühür ve doğrulama

Başlamış bir deneyi geçici defterde iki kez çalıştıran test, raporlama
dosyasına yapılan temsili değişiklikten sonra beş hesabın ilerleyebildiğini
ve asıl politika dosyası değişince reddedildiğini doğruluyor. İki depoda
yeni sözleşme kod kapsamı ekonomik modülleri korur. Bildirim, raporlama ve
nöbetçi dosyaları hariç tutulur. İlk tam build özeti kanıt olarak saklanır.
Eski kapsamı olmayan sözleşmelerde tam hash kontrolü korunur. Sözleşme
kayıtları geçmişten dönüştürülmedi.

Önceki iki uzak BIST mührü 591cb3a kesitiyle aynı. Önceki yerel ML
kaydının dosyası ve onunla birebir eşleşen kaynak kopyası saklandı.
İlk ön kayıt Git izinde bulunmayan yerel bir dosya. Yerel koşuların
sırası belgelenmiş olsa da bağımsız ön kayıt tarihi gösterilemez.
Yeni **5 seans** gölge **29/30** hisse ve beş sıralayıcıyla ayrı
yazıldı. Vade **1 Aralık 2026**, ölçüm beklemede. Yerel kayıtlar için
harici zaman damgası oluşmadı. Aralık'taki tekli ve örtüşen tarihler
süreç doğrulaması sağlar ve tek başına terfi kararı taşımaz.
[Mühür hash’leri](../reports/forecast-audit-2026-11-25/coverage.json) · [5 seans gölge kaydı](../reports/forecast-audit-2026-11-25/bist-shadow-5.json) · [Önceki 20 seans kayıt kodu](../reports/forecast-audit-2026-11-25/forecast_rank_shadow_v1.py)

Kalan işler bağımsız canlı maliyetli portföy, altın V2 kapanış makbuzu,
karar anında bilinen resmi tarihsel üyelik, güvenilir bağımsız prim ve
GC=F roll/spot kıyası. Sonuçlar yerel ve keşif kapsamındadır.

## Tekrar üretim

`BIST_DB` ve `GOLD_DB` 24 Kasım üretim kesitlerinin geçici SQLite
kopyalarıdır. `GOLD_LEDGER` aynı kesitin salt okunur altın defteridir.

```sh
python -m scripts.forecast_audit --database "$BIST_DB" \
  --receipt reports/forecast-research-2026-11-25/bist.json --output /tmp/bist-audit.json
python -m scripts.bist_long_research --database "$BIST_DB" \
  --asof 2026-11-24 --output /tmp/bist-long-audit.json
python -m scripts.gold_leg_research --audit --database "$GOLD_DB" \
  --schedule reports/forecast-research-2026-11-25/gold.json --output /tmp/gold-legs-audit.json
python -m scripts.gold_timing_audit --ledger "$GOLD_LEDGER" \
  --config ../gold_tracking_system/advisor/config.json --output /tmp/gold-timing-audit.json
```

Tam yerel pakette BIST **1.549 geçti, 6 şablon testi başarısız**,
altın **1.051 geçti, 14 atlandı**. BIST başarısızlıkları eski çalışma
kopyasında kaldırılmış `Proje Yardımcısı/yeni-proje.sh` dosyasını arıyor.
44 hedefli test geçti. Davranış testleri sabit sözleşme ve saf sıra dolumunu, drift aritmetiğini,
eşlemeli blok özetini ve eski gölge vadesini ayrı sınar. Gerçek arşiv
koşuları test fixture'larından ayrı çalıştırıldı.
[Kod ve makbuz özetleri](../reports/forecast-audit-2026-11-25/manifest.json)
