# BIST ileri sıralama sınavı · 18 Kasım 2026

> **2026-11-25 devir notu.** Güncel üretim, yerel paket, bağımsız momentum ve ortak T0 durumu [STATE kaydında](../ai/STATE.md). Bu sayfadaki tarihli kesitler kendi koşullarına aittir.


17 Kasım kapanış verisiyle, 18 Kasım seansından önce 32 hissenin 20 seanslık göreli getiri tahmini kaydedildi. Eğitimde etiketi en geç 16 Kasım'da sonuçlanan 756 seans ve 24.001 hisse-gün kullanıldı. İki model aynı hisseleri, özellikleri ve eğitim tarihlerini kullanıyor. Ridge ve LightGBM ayarları önceki araştırmadan alındı. Eğitim tarihindeki seçilmiş hisselerin eski fiyatları kullanıldığı için geçmiş üyelik yanlılığı eğitimde sürüyor.

Modeller, tahminler, son girdi tarihi ve veri özeti `reports/bist-forward-2026-11-17.json` dosyasındadır. Yeniden yüklenen iki model de kayıtlı 32 tahmini birebir üretti. Bu ileri sınav, üretim karar akışından ayrı yürütülen bir araştırmadır.

24 Kasım kontrolünde komut 32 kayıt için `vade bekleniyor` döndürdü. [İşlemsizlik ve deney durumu](DENETIM-2026-11-24.md)

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

## Masraflı tarihsel portföy karşılaştırması

25 Eylül–17 Kasım 2026 arasında 37 işlem seansı için üç sanal hesap aynı günlerde toplam 60.000 TL katkı aldı. İki adayda katkının %80'i ortak çekirdek sepete, %20'si taktik stratejiye ayrıldı. Pasif hesap iki payda da çekirdek sepet kuralını izledi. Günlük fiyat aralığıyla simüle edilen stoplar ve işlem masrafları portföy değerine yansıtıldı.

| Yöntem | Son net değer | Katkı etkisinden arındırılmış getiri | En büyük kapanış düşüşü | Alış ve satış sayısı |
|---|---:|---:|---:|---:|
| Pasif sepet | 55.322,11 TL | −%10,08 | −%18,71 | 212 |
| Ridge | 54.638,47 TL | −%11,11 | −%18,31 | 181 |
| LightGBM | 54.385,57 TL | −%11,54 | −%18,49 | 181 |

LightGBM bu kesitte pasif sepetin 936,54 TL gerisinde kaldı. Kesit önceki sıralama araştırmasında kullanılan arşivle örtüşüyor. Günlük barlardan çıkarılan stop fiyatları ve kullanılan maliyet tarifesi gerçekleşmiş banka işlemlerini yaklaşıklar. Aday araştırmada kalıyor.

```sh
python -m scripts.bist_rank_replay --asof 2026-11-17 --output /tmp/bist-replay.json
```

Ayrıntılar ve günlük değerler `reports/bist-rank-replay-2026-11-17.json` dosyasındadır.
