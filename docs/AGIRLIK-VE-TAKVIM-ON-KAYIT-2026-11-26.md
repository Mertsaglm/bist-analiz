# Ağırlık ve takvim takip sınaması

26 Kasım 2026. Önceki tarihsel koşunun 25 Kasım SQL kesitini ve aynı
sinyal tarihlerini kullan. Bu takip keşif amaçlıdır.

- Altında aynı 59 olgun sinyal için ceza 20, 20 seanslık hedef ve
  sinyalden kesin önce olgunlaşan etiketleri kullan. Temel özellikler
  ve yüklenen üretim ayarındaki ana Ridge ayrı ölçülür. 756 tarih ve
  genişleyen pencerenin her birinde 126 seans yarı ömrünü eşit ağırlığa
  karşı ölç. Ons/kur özellikli T0 adayında da 756 tarih ve yarı ömrü
  dışında her şey aynı kalsın. Birincil ölçüt eşli MAE farkıdır.
  Dairesel 3 ve 6 dönem blok bootstrap aralıkları tanısaldır.
  Aynı tahminlerle önceki %3/%4 makaslı portföy vekilini de tekrarla.
- BIST'te veri işleme ve tarih kapsamı etkisini ayırmak için ilk ve gözlenen
  bar koşularındaki 1× sonuçları aynı eşli tarihlerde karşılaştır. Yeni
  yöntemin o tarihlerdeki farkı ile aynı yöntemin ek tarihlerdeki farkı
  ayrı kaydedilir. Hiçbir tarihin eksik fiyatını doldurma.
- BIST üretim yolunu SQL'den ham sembol barlarıyla çalıştır. 9 Nisan
  yarım seansının etrafındaki özellik, karar girdisi ve 20 seans hedefi
  etkisini ayrıca ölç. 25 Kasım’a kadarki üyelik ve her iki günde fiyat
  kapsamını çok yıllı replay için önceden say. Eksik üyeliğe sepet uydurma.
