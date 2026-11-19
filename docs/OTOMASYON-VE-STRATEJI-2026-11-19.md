# Otomasyon ve strateji revizyonu · 2026-11-19

## Üretimde gözlenen akış

GitHub Actions koşuları ve iki üretim hesabının olay defteri salt okunur
incelendi. SQL arşivleri geçici veritabanlarına geri yüklendi ve bütünlük
kontrolünden geçti. Yeni kaynak çekimi işletim kanıtı olarak kullanılmadı.
Saatler İstanbul saatidir.

| Kontrol | BIST | Gram altın |
|---|---|---|
| Tarihsel arşiv | 209.128 fiyat barı, 73 sembol. 17–19 Kasım kapanışlarının her biri 73/73. USD/TRY ve dört endeks 19 Kasım’da. | 2.642 tarih. Son model girdisi 18 Kasım, 19 Kasım çevriminin beklediği son tamamlanmış gün. Son üç günlük ons kaynağı GC=F. |
| Gerçek otomatik işlem çevrimleri | 17 ve 18 Kasım’da sıfır. 19 Kasım’da 10.17–17.17 arasında fiyat kapsamı tam sekiz çevrim. | 17 Kasım’da yeterli fiyat kapsamı ve çevrim hatası olmayan 27/34, 18 Kasım’da 35/35. 18 Kasım’da ardışık çevrimler arasında en büyük gözlenen ara 183 dakika. |
| Son kayıtlı karar | 19 Kasım 19.40, 33/33 fiyat ve tahmin. 31 fırsat/filtre BEKLE, 2 kazanç/risk BEKLE. Model hazır, onay kapısı geçilmemiş. | 19 Kasım 18.43, 18.41 damgalı banka referansı ve 1/1 tahmin. Geniş makas nedeniyle BEKLE. Gözlenen satış/alış farkı alış maliyetine göre yaklaşık %14,01 (banka satış / banka alış − 1). |
| Sanal defter | 19 Kasım’da pasif kolda 25 AL, stratejide sıfır gerçekleşme. | Son üç günde pasif ve strateji kollarında sıfır gerçekleşme. Pasif kolda daha eski bir alım bulunuyor. |
| Telegram | 19 Kasım 16.15 ve 17.15 koşularında bağlantı hatası. Kapanış görünümüyle eşleşen 282 numaralı makbuz 19.42’de kaydedildi. | 19 Kasım 10.01 durum mesajının makbuzu 410. 18.43 çıktısı öncesi son kayıtta yeni mesaj yok. Mevcut gönderim politikası aynı durumun tekrarını bastırıyor. |

BIST'in 219 yeni barında açık/yüksek/düşük/kapanış tutarsızlığı ve eksik ya da
sıfır hacim yok. Aynı günlerin 15 endeks/kur kaydı fiyat tutarlılığı kontrolünü
geçti. Altında son üç arşiv gününün gram girdisi kayıtlı ons ve kurdan yeniden
hesaplanarak eşleşti. İki görünüm kendi olay defterindeki hash ile eşleşti.

- **P1 · Seans içi boşluk.** Kapanış raporu iki BIST günündeki eksikliği
  gidermedi. Altında 19 Kasım 18.40 nöbetçisi 45 dakika aralığı aşıldığını
  kaydetti. Dış tetikleyici boşluğunun kök nedeni doğrulanmadı.
  [Altın nöbetçisi](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/44557363905)
- **P1 · Bildirim teslimi.** Karar üretildikten sonra Telegram bağlantısı iki
  koşuda kesildi. Eski log, isteğin hangi ağ aşamasında kaldığını göstermiyor.
  [16.15 koşusu](https://github.com/Mertsaglm/bist-analiz/actions/runs/44531587040)
  [17.15 koşusu](https://github.com/Mertsaglm/bist-analiz/actions/runs/44541699205)
- **P2 · Günlük görünürlük.** Gün içi karar özeti kapanış raporu yerine
  kullanılıyordu. Başarıyla kaydedilen ama aynı kararı veren kapanış, yeni
  bildirim üretemeyebiliyordu. Ayrıca ilk başarısız bulut telafisi aynı zaman
  aralığındaki yeni telafiyi kilitleyebiliyordu.

Mevcut ayrı sanal aday defterleri BIST’te hareket etmiş. 19 Kasım görünümünde
50 seans trend kolunda 49, yakın dönem 20 seans kolunda 4, geri çekilme kolunda
2 gerçekleşme var. Dört adayın son değeri 58.490,40–60.000,00 TL aralığında.
Aynı görünümde pasif kıyas 53.335,90 TL, faizsiz nakit 60.000 TL. Düşen piyasada
pasifi geçmek ile katkıdan bağımsız para kazanmak farklı hedeflerdir. Altın
aday defterlerinde gerçekleşmiş strateji işlemi yok.

## Yerel düzeltme

- Gün sonu Telegram raporu son fiyat kapsamını, tamamlanmış işlem çevrimlerini,
  son karar dağılımını ve defterde gerçekten gerçekleşen strateji/pasif
  işlemlerini gösterir. Aynı günün eksik kapanışı daha sonra eksiksiz
  tamamlanırsa güncel rapor da gönderilir.
- Bağlantının kurulamadığı doğrulanabilen Telegram hatalarında en çok üç
  deneme yapılır. Yanıt kaybolduğunda teslim belirsizliği korunur. Makbuzlar
  karar zamanı ve defter kimliğine bağlıdır. Ağ sınıfı, bot adresi olmadan loglanır.
- Bulut telafisi bekleyen işleri ve 10 dakikalık aralığı korur. Aynı zaman
  aralığında başarısız olan otomatik telafiden sonra bir denemeye daha izin verir.

## Strateji sınavı

Borsa İstanbul’un seans ve piyasa kuralları sanal dolum şartlarını belirler.
İş Bankası'nın yayımladığı tarife ve gram alış/satış marjı maliyet modeline
girer. İş Bankası gram kotasyonunu geçmiş ons × kur serisiyle eşitlemek
alış-satış maliyetini gizler. Trend ve momentum ayrı aday özellikleri olarak
ölçülür. Masraflar ve sinyalin zayıflaması karar sıklığıyla birlikte sınanır.
[BIST seansları](https://www.borsaistanbul.com/piyasalar/pay-piyasasi/islem-saatleri)
[BIST piyasa işleyişi](https://www.borsaistanbul.com/piyasalar/pay-piyasasi/piyasa-isleyisi)
[İş Bankası altın hesabı](https://www.isbank.com.tr/vadesiz-altin-hesabi)
[İş Bankası tarifesi](https://www.isbank.com.tr/urun-ve-hizmet-ucretleri)
[Dinamik işlem ve maliyet](https://www.nber.org/papers/w15205)
[Zaman serisi momentumu](https://www.sciencedirect.com/science/article/pii/S0304405X11002613)
[Altının getiri bileşenleri](https://www.gold.org/goldhub/tools/gold-return-attribution-model)

BIST’te 25 Eylül–19 Kasım arasındaki 39 seansta 9 eğitim kesiti ile
aynı 60.000 TL katkı ve aynı masraflarla kıyas yapıldı. Yeni kollar her seans
pozisyonu tekrar inceler. Çıkış, sıralama/net beklenti değişimi veya stop ile
oluşabilir. Eğitim etiketinin 20 seans olması çıkış tarihi değildir.

| Kol | Son değer (TL) | En büyük kapanış düşüşü | Taktik AL/SAT |
|---|---:|---:|---:|
| Pasif | 54.018,08 | %18,71 | — |
| Haftalık LightGBM | 53.154,98 | %18,49 | 31/24 |
| Haftalık Ridge | 53.285,00 | %18,31 | 33/22 |
| Günlük LightGBM | 53.909,48 | %18,84 | 66/35 |
| Günlük Ridge | 53.070,27 | %19,59 | 80/41 |

Altında 5/10/20 seans hedeflerinde 26 zaman sıralı kesit kullanıldı. Temel
Ridge ve ons/kur özellikli Ridge için aynı ufuktaki mutlak tahmin hataları
sırasıyla 3,42/3,50, 5,85/5,95 ve 12,48/12,74 yüzde puan. Daha kısa ufkun
getirisi de daha kısa dönemdir. Bu ölçümün ekonomik karar eşiği, banka
alış/satış fiyatıyla maliyet sonrası ayrı portföy sınavı gerektirir.

Tekrar üretim komutları (`DB` üretim SQL'inden izole geri yüklenmiş kopyadır):

```sh
python scripts/bist_rank_replay.py --database "$DB" --asof 2026-11-19 --compare-daily --output /tmp/bist-replay.json
python scripts/portfolio_research.py --market gold --database "$DB" --asof 2026-11-18 --horizon-sessions 5 --output /tmp/gold-research.json
```

Altın komutu 10 ve 20 seans için ayrı çıktıyla tekrarlanır. Git SQL blob
kimlikleri BIST için `6c09f9a19c28bf658ee8f2781a72b185d529a5a3`, altın için
`0a0e0a6a1f2be28ed180a931a00c55190abde393`. BIST replay daha önce incelenmiş
bir dönemi içerir. Günlük OHLC sanal stop varsayımı içerir ve banka gerçekleşmesi
olarak kullanılamaz. Pasif kıyası geçen bir taktik kol veya canlı terfi oluşmadı.

## Üretim motoru seçimi

- **BIST:** Mevcut düzenlileştirilmiş Ridge, ana tahmin motoru ve karşılaştırma
  tabanı. Basit trend, göreli Ridge ve LightGBM ayrı sınavlar. Borsa
  İstanbul'un seansları, takvimi ve piyasa işleyişi işlem katmanını belirler.
  Gecikmeli son fiyat ve hacimle, emir defteri likiditesi veya devre kesicide
  dolum varsayılmaz. Komisyon, kayma, saklama, net temettü ve nakit kıyası
  performans değerlendirmesine dahildir.
- **Altın:** Temel Ridge, ons/kur bileşimine dayalı tarihsel gram serisiyle
  çalışır. Banka marjı ve alım vergisi ekonomik karar katmanına aittir.
  Banka referansının zamanı, saflık, işlem miktarı ve kaynağı ayrı tanımlanır.
  Ek ons/kur özellikleri ve banka fiyatıyla ölçülen yeni modeller ayrı kalır.
- **Öğrenme:** Kapanış girdisi değişince proje kendi Ridge modelini günceller.
  Tahminleri tarihle mühürler, vade dolduğunda sonucu yazar ve yeterli
  bağımsız dönem oluştuğunda sınırlı hata düzeltmesi uygular. BIST göreli
  hedefinin paydasında eğitim anında sonucu belli olan paylar bulunur.
  Olgunlaşmamış bir payın getirisi, aynı günün diğer paylarına sızamaz.
  Kârlılık kararı masraf sonrası servet ve düşüş ölçümüyle verilir.

## Üretim kabulü

Yayın onayından sonra iki depoda mevcut olmayan seans saati zorlanmadan,
bir sonraki otomatik seans ve kapanış izlenir. Her piyasa için beklenen fiyat
sayısı, kaynak zamanı, tahmin sayısı, olay defteri hash’i ve Telegram makbuzu
eşleştirilir. Eksik çevrim ve teslim arızasında tetikleme, runner, giriş verisi ve
yeniden deneme kaydı ayrı okunur. Vercel, karar ve defter kaydının okuma yüzüdür.
İki görünüm panel şema doğrulamasından geçti. Hesabın Kasım Actions bütçe
tüketimi kişisel faturalama API'sinde mevcut yetkiyle doğrulanamadı.
Projenin salt okunur nöbetçisi son çevrim için fiyat kaynaklarını, model
kimliğini, tahmin ve mühürlü kayıt kapsamını, defter hash'ini ve son Telegram
makbuzunun birebir çevrim eşleşmesini ayrı alanlarda raporlar.
