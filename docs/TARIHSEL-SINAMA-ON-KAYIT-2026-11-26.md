# BIST ve altın tarihsel sınama ön kaydı

26 Kasım 2026. Aynı tarihlerde 2, 3, 5 yıllık ve genişleyen eğitim
pencerelerinin farkını ölç. 20 seansı sabitle. Önceki 5 seans uzun araştırması
ve üç vadeli kısa araştırma bu koşunun dışında kalır. Tarihsel veri daha önce
araştırıldı. Bu test keşif amaçlıdır ve T0 ya da bağımsız ileri adaylara kapı eklemez.

## Ortak tasarım

- 2022-01-01 sonrasındaki ilk arşiv seansından itibaren her 20. seansta bir sinyal.
  Sonuçlanmamış son sinyaller değerlendirilmez. Rapor dönemleri 2022, 2023–2024
  ve 2025–veri kesiti. Bunlar önceden sabit takvim dilimleridir.
- Model her sinyalde yalnız etiket sonu sinyal tarihinden kesin önce olan
  örneklerle yeniden kurulur. 2, 3 ve 5 takvim yıllık pencereler sinyalden
  geriye gider. Genişleyen pencere ilk kullanılabilir eğitimden başlar.
  Ortak alt sınır 400 eğitim tarihi. Özellikler önceki 25 Kasım çalışmasından,
  Ridge cezası 20. Pencere etkisini ölçerken 126 seans üstel ağırlığı kaldırıp
  eğitim satırlarını eşit ağırlıklandır. Bu Ridge'ler ayrı araştırma adaylarıdır.
- Kaynak günleri, bar sayısı, fiyat ve özellik kapsamı, atlanan sinyaller,
  eğitim etiketi kesiti, veri ve kod hash'leri raporda. Sinyal havuzu
  gelecek fiyatlardan bağımsız kurulur. Sonuç fiyatı yoksa o dönem eksik
  işaretlenir. Eksik isim çıkarılarak ekonomik payda küçülmez.
- Deneme sayısı bu protokolle sınırlı. Önceki toplam deneme sayısı bilinmediği
  için PBO veya deflated Sharpe ile tarihsel veri tekrar kullanımına sayısal
  güven atfetme. BIST birincil senaryosunda eşli farklar için 3 ve 6 dönemlik
  dairesel blok bootstrap ve iki evrendeki tüm aktif adayları aynı anda
  kapsayan %95 aralık raporla. Bu aralık yalnız bu koşuya koşulludur.

## BIST

- Son kayıtlı 30 üyeyi geçmişe sabitleyen evren ve arşivdeki hisselerden
  sinyal anındaki son 63 barın medyan işlem tutarına göre en likit 30 evreni.
  Her ikisi de tarihsel üyelik ve piyasadan çıkan şirketler açısından eksik.
  Resmî BIST30 kaydı ayrı kapsam ölçümüdür. Sıralama için sinyal günü bazında Spearman Rank IC kullan.
- Altı aktif kol. Dört göreli Ridge, 120–20 momentum, 3 yıllık LambdaRank.
  80% eşit ağırlıklı ortak sepet ve 20% ilk beş, nakit ya da eşit ağırlıklı
  pasif ek dilim. Evren başına en az 24 uygun özellik satırı. Hedef,
  20. seans düzeltilmiş kapanış getirisinin ilgili havuzun ortalamasından farkı.
- Sinyal ertesi seans açılışında al, 20. seans kapanışında sat. Düzeltilmiş
  toplam getiri serisi, açılışta aynı günün düzeltilmiş/ham oranıyla
  ölçeklenir. Oransal komisyon %0,20, komisyon BSMV %5, borsa payı %0,003
  ve kayma 5 baz puan her iki yönde. Birincil 1× ve duyarlılık 2×.
  Min. komisyon, saklama, stop, gerçek temettü nakdi ve lotlar kapsam dışı.
- Her pencere bağımsız, 50.000 TL ile yeniden başlar. Böylece elde tutma
  süresi ve ortak çekirdek aynı kalır. Birincil ölçüt, 100% eşit ağırlıklı
  pasife karşı ortalama net getiri farkı. Yalnız her iki evrende eksiksiz olan
  eşli dönemler ana tabloya girer. Ayrı raporda tüm uygun dönemler ve eksik
  semboller yer alır. Dönem içi kapanışlardan en kötü net düşüş ve toplam
  alış/satış tutarının başlangıç sermayesine oranı raporlanır.
  Bu test güncel beş kollu defterin tam çok yıllı portföy tekrarı değildir.

## Altın

- Dört doğrudan Ridge ve 3 yıllık ayrı ons/kur Ridge, sıfır getiri ve
  pozitif SMA50 trendi kıyası. MAE, yani ortalama mutlak hata, sıfır
  getiriyle eşli ölçülür. Tarihsel teorik gram serisi GC=F ve USDTRY temelli.
- Kesintisiz sanal hesap 50.000 TL ile ilk icra gününde açılır.
  Sonraki her ayın ilk arşiv gününde 5.000 TL eklenir. 80% ortak altın
  çekirdeği, 20% sinyale bağlı altın veya nakit. 100% al-tut ve 80/20
  sabit nakit referansları. Sinyal sonraki arşiv kapanışında işlenir.
  Vadesi henüz dolmayan son sinyal portföyde işlenir ve MAE'ye girmez.
  Model ve SMA50 için aynı karar sıklığı. Modelde teorik tahmin,
  karşılıklı makas ve alım vergisinin bileşik maliyetini geçerse altın.
  SMA50 için sinyal gününün fiyatı SMA50 üzerindeyse altın.
- Teorik fiyat orta fiyat kabul edilir. Makas, ask/bid − 1 olarak %3
  birincil, %4 duyarlılık. Alım vergisi %0,20, ek kayma varsayımı her yönde 5 baz puan,
  lot 0,01 gram. Nakit faizsiz. Banka fiyatı, gün içi kotasyon ve stop
  ölçülemez. Portföy her kapanışta varsayımsal satış fiyatıyla değerlenir.
  Birincil ölçüt terminal net TL farkı. Katkıdan arındırılmış getiri,
  düşüş, devir, maliyet, net gram ve altın maruziyeti de raporlanır.
  Eksik model sinyalinde mevcut hedef korunur ve olay sayılır.
