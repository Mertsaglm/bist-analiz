# Tahmin araştırması V1 · 25 Kasım 2026

Bu ön kayıt yerel keşif koşusunu tanımlar. İki piyasanın kararları, sanal
hesapları, ortak T0 açılışı ve mevcut ileri ölçümleri bağımsız yürür.

| Tasarım | Sabit seçim |
|---|---|
| Ufuk ve değerlendirme | 5, 20, 60 seans. Her piyasa için 60 seansın da olgunlaşabildiği en son 126 ortak sinyal tarihi. |
| Takvim | BIST XU030 pozitif kapanışı veya en az 24 üyenin fiyat ve hacim kaydı, bilinen tam tatiller ve hafta sonları hariç. Altın teorik arşiv tarihleri. Sembolün eksik barı etiket vadesini ileri taşımaz. |
| Eğitim | 5 seanslık bloklar, en çok 756 ve en az 504 eğitim tarihi. Etiket bitişi blok başlangıcından kesin önce. Ridge 20 ceza, 126 seans yarı ömür. |
| Ölçek ve kalibrasyon | Tahmin modelleri eğitimde gördükleri verilerle ölçeklenir. Ridge ve BIST LightGBM regresyonunda affine kalibrasyon ile ham tahmin karşılaştırılır. Kalibrasyon ve aralıklar ilk test tarihinden önce olgunlaşmış son 126 OOS tarihte öğrenilir. |
| BIST örneklemi | Kaynak kesitindeki tarihli BIST30 üyeliği geçmişe sabitlenir. Seçim yanlılığı açıkça taşınır. Gün başına beklenen isimlerin en az %80'i aynı özellik ve vade ile bulunmalı. Ortak satırlardaki eşit ağırlıklı getiri göreli hedefin referansıdır. |
| BIST adayları | Sıfır fazla getiri, 120–20 momentum, göreli Ridge, Elastic Net, LightGBM regresyonu ve gün gruplu LambdaRank. 20 seansta fiyat dışı eklemeyi izole eden göreli Ridge genişlemesi hacim, işlem tutarı ve kesitsel momentum/oynaklık sıralarını kullanır. Aynı gün göreli ve mutlak getirinin sırası özdeştir. |
| Altın adayları | Sıfır getiri, eğitim ortalaması, temel Ridge, bacak özellikli doğrudan gram Ridge, Elastic Net ve ayrı ons/kur log-getiri Ridge. Son aday iki log tahminini toplar ve bileşik basit getiriye çevirir. Kaynak değişimi ve senkronizasyon ayrı veri konularıdır. |
| Olasılık ve aralık | Eğitimde geçmiş olay sıklığına karşı L2 lojistik. Olay BIST'te brüt eşit ağırlıklı araştırma sepetini geçmek, altında teorik gramın brüt pozitif getirisidir. Ham Ridge hata yüzdelikleri ile EWMA oynaklığına ölçekli hata yüzdelikleri kıyaslanır. Yüzdelikler 10/50/90. |
| Ölçütler | MAE, RMSE, sıfır referansına göre OOS R², sapma, kalibrasyon eğimi, BIST Rank IC ve ilk beşin brüt sepet farkı. Brier, log loss, reliability dilimleri, aralık kapsaması, genişlik ve pinball kaybı. Tarih bazlı paydalar ve örtüşmeyen vade sayısı. |

Elastic Net: standardizasyon, alpha 0,1 ve L1 oranı 0,5. Lojistik:
standardizasyon, C=1. LightGBM: repodaki sabit parametreler, LambdaRank için
günlük gerçekleşen getirinin beş yüzdelik sınıfı ve ilk beş odaklı sıralama.
Affine eğim, 1'e doğru düzenlileştirilir ve işareti serbesttir. Aralıklar
tarih boyunca sabit tahmin periyodunda ölçülür, kapsama garantisi içermez.

Sonuçlar geriye dönük ve keşif amaçlıdır. Ortak 126 tarihin önemli bir
bölümü önceki araştırma dönemi ile örtüşebilir. İlk beş farkı brüt kapanış
ölçümüdür. Gerçek banka net getirisi, altın katkı zamanlaması, spread,
stop ve nakit fırsat maliyeti ayrı ekonomik sınav gerektirir. Bir model
seri üretime alınmadan önce sürümüyle ileri gölge tahminleri ve eş bütçeli
sanal deneyi ayrı kaydedilir. İlk araştırma hiçbir canlı kapı eklemez.

İlk geliştirme koşusunda genel izleme evreninin 32 ad içerdiği ve XU030'un
yüksek hisse katılımlı 16 arşiv gününü tek başına kaçırdığı bulundu. Üye
kümesi proje çekirdek seçicisine bağlandı ve ortak takvim veri kapsamı
kontrolüyle tamamlandı. Aday, ufuk ve başarı ölçütleri bu düzeltmeler
sırasında sabit kaldı.

## İlk ileri BIST gölge kaydı

Araştırmanın 20 seanslık bütün sıralayıcıları tek bir yerel, yazıldıktan
sonra üzerine yazılamayan dosyaya kaydedilir. Girdi, kayıt anında son
tamamlanmış seanstır. Eğitim etiketleri sinyal gününden önce kapanmış
olur. Karar anında en az 24/30 uygun girdi gerekir. O gün puanlanan isim
ve kapsam dışı kalan isim birlikte açıklanır. Ölçüm aynı seçili isimler
için vade kapanışında Rank IC ve ilk beşin brüt eşit ağırlıklı farkını
verir. Puanlanmış bir ismin fiyat ucu eksikse ölçüm bekler. Gölge sonuçta
banka maliyeti, alım/satım ve pozisyon yoktur. Yerel zaman damgası harici
yayın makbuzu değildir.
