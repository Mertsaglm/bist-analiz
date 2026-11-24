# 25 Kasım denetimi için ek araştırma kuralları

Önceki araştırma ve ileri kayıtlar kendi sürümleriyle saklanır. Buradaki
adaylar geçmiş sonuçlar görüldükten sonra tanımlanan keşif adaylarıdır.

- BIST ekonomik replay'i 25 Eylül–24 Kasım, tarihli BIST30, 50.000 TL ve
  aylık 5.000 TL, ortak %80 çekirdek ve %20 taktik bütçe kullanır. Haftalık
  ilk 5 giriş, ilk 10 elde tutma ve ortak stop kuralları uygulanır. Saf
  LambdaRank, 120–20 momentum, göreli Ridge ve momentum/regresyon/LambdaRank
  eşit sıra ortalaması aynı düzenle karşılaştırılır. LambdaRank'in mutlak
  Ridge beklentili eşi olan kol, eşik etkisini izole eder. İki LambdaRank
  kolunda sıra puanı aynı ve pozitif ölçektedir. %100 pasif referans ayrı.
  Komisyon, borsa payı, minimum komisyon ve kayma 1×, 1,5×, 2× sınanır.
- Mevcut BIST istatistiklerinde dairesel bitişik tarih blokları yeniden örneklenir.
  Blok uzunluğu birincil olarak ufuk kadar, 20 seansta ayrıca 10 ve 40.
  Modellerin farkı aynı tarihlerden hesaplanır. 2.000 tekrar, sabit seed 42.
  Tarihsel 5 seans hızlı tanı ölçütüdür. Önceki ileri vadeler kendi
  dosyalarında kalır.
- Yeni hızlı ileri kayıt 5 seans, yalnız tamamlanmış son kapanış ve
  aynı günün BIST30 kümesiyle açılır. 24/30 ortak girdi asgaridir.
  Momentum, Ridge, Elastic Net, LightGBM regresyonu ve LambdaRank için
  aynı seansın sıralaması ile ilk beş brüt farkı ölçülür. Kayıt yereldir.
- Altın aynı tarih ve katlamalarda ayrı bacaklar, sıfır ve geçmiş 20/60
  seans log drift kıyasları ile sınanır. Drift vade ile ölçeklenir.
  Aynı gün ilk uygun %4 kotasyon ile 15.30 öncesi %2,75, sonrasında %4
  sınırı arasında ayrı zamanlama kıyası yapılır.
  Son gözlem seçilerek geçmişten dolum uydurulmaz.
- Üretim T0 kabulü, kayıtlı gündüz fiyatı ve ürün kimliğiyle salt okunur
  incelenir. Yerel araştırma, üretim yayını ve bağımsız zaman damgası ayrı
  kanıtlardır.
- Uzun BIST 5 seans sınavı 2018'den itibaren her beşinci ortak seansı
  değerlendirir ve yaklaşık 63 seansta bir model yeniler. Sabit Kasım
  üyeleri, arşivdeki isimlerden son 63 seans yeterli gözlemle nominal TL
  medyan işlem tutarı en yüksek 30 isimle karşılaştırılır. Bu ikinci küme
  likidite hipotezidir. Bir günde ortak özellikli en az 24 hisse gerekir.
  Rakipler 120–20 momentum, eşit faktör sırası (momentum, düşük oynaklık,
  beş seans ters hareket, hacim), göreli LightGBM ve eğitim hedefi yalnız
  eğitimde %2/%98 sınırlanmış LightGBM'dir. Düşük kuantil riski için
  kapanıştan sonraki beş günlük düzeltilmiş en düşük fiyat, aynı izin
  verilen eğitim setinin ampirik %10 kuantili ile doğrudan LightGBM %10
  kuantiline karşı ölçülür.
