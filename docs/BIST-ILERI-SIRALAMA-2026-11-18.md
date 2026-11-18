# BIST ileri sıralama sınavı · 18 Kasım 2026

17 Kasım kapanış verisiyle, 18 Kasım seansından önce 32 hissenin 20 seanslık göreli getiri tahmini kaydedildi. Eğitimde etiketi en geç 16 Kasım'da sonuçlanan 756 seans ve 24.001 hisse-gün kullanıldı. İki model aynı hisseleri, özellikleri ve eğitim tarihlerini kullanıyor. Ridge ve LightGBM ayarları önceki araştırmadan alındı. Eğitim tarihindeki seçilmiş hisselerin eski fiyatları kullanıldığı için geçmiş üyelik yanlılığı eğitimde sürüyor.

Modeller, tahminler, son girdi tarihi ve veri özeti `reports/bist-forward-2026-11-17.json` dosyasındadır. Yeniden yüklenen iki model de kayıtlı 32 tahmini birebir üretti. Bu ileri sınav, üretim karar akışından ayrı yürütülen bir araştırmadır.

## 15 Aralık kapanışında ölçüm

Güncel üretim SQL arşivini içeren çalışma kopyasında çalıştırılacak komut:

```sh
python -m scripts.bist_forward_trial measure --trial reports/bist-forward-2026-11-17.json
```

Güncel SQLite kopyası için `--database /yol/bist.db` verilebilir. Ölçüm komutu arşivi salt okunur açar. Sonuç vade gelene kadar beklemede kalır. Hesap, aynı veri sürümündeki 17 Kasım ve 15 Aralık temettü/bölünme düzeltilmiş kapanışlarını kullanır. Beklenen herhangi bir fiyat eksikse etkilenen hisseleri bildirir ve toplu skor üretmez. İki sıralamanın gerçekleşen getiri sırasıyla Spearman korelasyonu ölçülür. Eşit skorlar ortalama sırayı alır. Tamamen sabit sıralama için korelasyon tanımsızdır.

Bu tek 20 seanslık gözlemden terfi kararı çıkmaz. Sonraki karşılaştırmalarda geçmiş tahmini koruyarak yeni vadeler ayrı dosyada açılabilir. Birden çok örtüşmeyen dönemde masraf sonrası servet, işlem sayısı ve düşüş birlikte değerlendirilmeli. Ölçüm komutu elle çalışır.

## Tekrar üretim

Yeni bir tahmin kaydı için araştırma ortamında LightGBM gereklidir. Komut, doğrulanmış takvimde son kapanan seansı kullanır. Seçili evrenin tamamında güncel özellik bulunması gerekir. Var olan dosyanın üzerine yazmaz.

```sh
python -m scripts.bist_forward_trial freeze --trial reports/bist-forward-YENI-TARIH.json
```
