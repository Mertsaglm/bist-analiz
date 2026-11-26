# BIST ve altın eğitim penceresi sınaması

26 Kasım 2026 tarihli yerel araştırma. Her iki SQL kaynağının son seansı
25 Kasım 2026. 20 seanslık hedef, 2, 3, 5 takvim yıllık ve genişleyen Ridge
eğitimi, aynı sinyal günlerinde karşılaştırıldı. Her eğitimde yalnız sinyalden
önce olgunlaşmış etiketler kullanıldı. 20 seanslık ayrı dönemler de birbirinden
tam bağımsız kabul edilmedi. T0 için üretim ayarı 27 Kasım ve son iki sabit
makbuzun durumu “T0 bekleniyor”. [Ön kayıt](TARIHSEL-SINAMA-ON-KAYIT-2026-11-26.md) ·
[Kaynak, defter ve T0 makbuzları](../reports/historical-window-2026-11-26/sources.json)

## Veri kapsamı

| Kaynak | Kesit | Doğrulanan sınır |
|---|---|---|
| BIST | 2015-01-02–2026-11-25, 73 hisse ve 209.420 Yahoo barı | Son kaynak gününde 73 bar. 341 satırda sıfır hacim, 0 eksik veya sıfır O/C/düzeltilmiş kapanış ve 0 O/H/L/C iç tutarsızlığı. USDTRY endeks serisinde önceki 61 OHLC ihlali sürüyor. Kur bu koşunun özelliği değil. |
| Teorik altın | 2016-01-04–2026-11-25, 2.647 kapanış | 2.647 satırın tamamı GC=F. Pozitif fiyat ve ons × kur ÷ 31,1034768 kimliği doğrulandı. Ayrı kontrat, spot baz farkı ve iki bacağın aynı anda gözlenmesi doğrulanmadı. |
| GRAM banka referansı | 2026-10-01–2026-11-26, 40 İstanbul tarihi | Olay zinciri doğrulandı. 1.291 pozitif ve sıralı banka alış/satış gözlemi. Bu sayı bütün saatlerin işlem için uygun olduğu anlamına gelmez. Çok yıllı banka replay'i için yetersiz. |

BIST sabit sepeti 25 Kasım'da bilinen 30 üyenin geçmişe uygulanmasıdır.
Borsa İstanbul'un 1 Ekim 2026 için ilan ettiği TRMET giriş ve DSTKF
çıkışı projedeki kayıtla uyumlu. Önceki yılların üyelik zinciri
elde yok. Likidite evreni her gün geçmiş 63 seansın işlem tutarına
bakar. Her iki evren 73 isimlik arşivle sınırlı ve arşiv dışı hisseleri
içermez. [Repo üyelik kaydı](../advisor/universe-history.json) ·
[Borsa İstanbul dönem değişimi](https://www.borsaistanbul.com/duyuru/15598/bist-pay-endeksleri-donemsel-degisiklikleri) ·
[Resmî duyuru arşivi](https://www.borsaistanbul.com/endeksler/endeks-duyurulari)

## BIST

İlk koşu 61 planlı sinyalden **19 eşli ekonomik dönem** ve 20 eşli tahmin
dönemi verdi. Son fiyatlı dönem 25 Mart 2024'te bitti. 9 Nisan 2024 gerçek
yarım seansında iki endeks barı var, 15 hisse barının hacmi sıfır.
Takvimdeki tek boşluk 200 seans isteyen özellikleri takip eden aylarda
boş bıraktı. İki yıllık eğitim kapsamı da düştü. Piyasa vadesini
ve işlemin fiyat gereksinimini sabit tutan ayrı duyarlılık koşusu
**57 eşli ekonomik dönem** ve **60 eşli tahmin dönemi** üretti.
Dört ekonomik dönem eksik fiyatla ölçülemedi. Duyarlılık 3 Ocak 2022
sinyaliyle başlıyor, 17 Kasım 2026 kapanışıyla bitiyor. [Resmî yarım seans](https://www.borsaistanbul.com/files/pay-piyasasi-2024-yili-tatil-tablosu.pdf) ·
[Duyarlılık kuralı](TARIHSEL-SINAMA-DUYARLILIK-2026-11-26.md)

| Taktik dilimin kullanımı | Sabit 30 | Likit 30 | Sabit 30, 2025 ve sonrası | Likit 30, 2025 ve sonrası |
|---|---:|---:|---:|---:|
| 2 yıl Ridge | −0,08 | −0,07 | ≈0,00 | −0,38 |
| 3 yıl Ridge | −0,07 | +0,15 | +0,08 | +0,08 |
| 5 yıl Ridge | −0,04 | −0,10 | +0,20 | −0,23 |
| Genişleyen Ridge | −0,27 | −0,02 | +0,03 | +0,01 |
| 120–20 momentum | −0,03 | +0,08 | +0,04 | +0,09 |
| LambdaRank | −0,24 | −0,08 | −0,22 | −0,59 |
| Nakit | −0,64 | −0,57 | −0,21 | −0,18 |

Sayılar duyarlılık koşusundaki 50.000 TL'lik, birbirinden ayrı
pencerelerde pasif sepete göre ortalama net getiri farkı, yüzde puan.
Takvim dilimlerinde 12, 24 ve 21 fiyatlı pencere var. 3 yıllık Ridge'in
likit evrende **+0,15** puanlık farkının 6 dönem bloklu eşanlı aralığı
**[−0,34, +0,64]**. On iki karşılaştırmanın tamamı hem 3 hem 6 blokta
sıfırı içeriyor. 2× maliyet ortalama farkların işaretini değiştirmedi.
Örneklemden hisse çıkarmadan aynı tarihler ölçüldü. 3 yıllık likit Ridge
için en kötü dönem içi net düşüş −%25,30, pasifte −%24,78.
Devir yaklaşık %203. Bu devir bir dönemin hem alım hem satışını içerir.
Her dönem sabit sermayeyle sıfırlanır. Birikimli V2 performansı, temettünün
ödeme günündeki nakdi ve intraday stop dolumu bu testte ölçülmedi.

İlk sıkı koşunun 19 döneminde 3 yıllık likit Ridge +0,42 puandı;
daha geniş duyarlılıkta +0,15'e düştü. Genişleyen Ridge hiçbir evrende
ortalama pasifi geçmedi. LambdaRank son dilimde iki evrende de geride.
Sonuç, geniş pencereyle yeniden eğitim veya LambdaRank terfisi için kanıt
vermiyor. Likit evrendeki 3 yıllık Ridge, tarihli üyelikle tekrar sınanabilecek
bir hipotez. [İlk koşu](../reports/historical-window-2026-11-26/bist.json) ·
[57 dönemlik duyarlılık](../reports/historical-window-2026-11-26/bist-observed-features.json)

## Altın

59 olgun tahminde sıfır getiri referansının mutlak hatası 5,54 puan.
2 yıl Ridge 6,25, 3 yıl 5,89, 5 yıl 5,68, genişleyen 5,36,
ayrı ons/kur Ridge 6,10. Genişleyen model 2022'de sıfır referansından
daha yüksek hata verdi (6,53/4,96). 2023–24'te 4,49/5,60 ve 2025
sonrasında 5,61/5,80. Düşük tahmin hatası maliyetli karar üstünlüğüne
dönüşmedi.

| Kol | %3 makasta net TL | %4 makasta net TL | %3 makasta katkısız en büyük düşüş |
|---|---:|---:|---:|
| %100 pasif altın | 1.205.099 | 1.193.522 | −%23,70 |
| %80 altın + %20 nakit | 1.032.119 | 1.022.841 | −%22,51 |
| %80 altın + %20 SMA50 | 1.141.164 | 1.122.807 | −%22,56 |
| %80 altın + %20 3 yıl Ridge | 1.093.726 | 1.025.800 | −%23,04 |
| %80 altın + %20 genişleyen Ridge | 1.061.034 | 1.020.709 | −%23,54 |

4 Ocak 2022–25 Kasım 2026. Her kolda **340.000 TL katkı**, ilk 50.000
TL ve aylık 5.000 TL. SMA50 her iki senaryoda 80/20 nakit kıyasını
geçti ve %100 pasifin altında kaldı. Pasife kayıp yaklaşık 63.935 ve
70.715 TL. Genişleyen Ridge %4 senaryosunda 80/20 nakit kıyasının
da 2.131 TL altında. %3 makasta en iyi Ridge son değerine 3 yıllık,
%4 makasta 2 yıllık pencere ulaştı. Makas varsayımı ekonomik model
sırasını değiştirdi. Bunlar GC=F ve USDTRY'den türeyen, %3–4 makaslı
varsayımsal banka fiyatları. Tarihsel banka performansı için gözlemler
henüz 40 günlük referans aralığıyla sınırlı. [Tahmin ve günlük portföy makbuzu](../reports/historical-window-2026-11-26/gold.json)

## Karar ve tekrar üretim

Arşiv, model davranışını araştırmak için yeterli. BIST'te ilk sorun
ham bar adedi değil, seans ve üyelik kapsamı. Altında asıl açık doğru
tarihsel banka fiyatı ve eşzamanlı spot/kur. İncelenen adayları üretim
kararı yerine ileri deney ve veri tamamlama önceliği için değerlendir.
Önceki toplam deneme sayısı bilinmediği için Deflated Sharpe/PBO
uygulanmadı. Raporlanan BIST aralıkları bu koşudaki 12 karşılaştırma ile
sınırlı. [Deflated Sharpe'ın dayandığı deneme sayısı](https://doi.org/10.3905/jpm.2014.40.5.094)

`BIST_DB` ve `GOLD_DB` bağlı commit'lerin SQL'inden yeni geçici SQLite
olarak hazırlanır. Aşağıdaki örnekte çıktı yolları yeni dosyalar olmalıdır.
BIST duyarlılığı için ilk komuta `--bist-observed-features` ekle ve farklı
çıktı seç. [Çalıştırılabilir kod](../scripts/historical_window_research.py)

```sh
python -m scripts.historical_window_research --market bist --database "$BIST_DB" \
  --asof 2026-11-25 --source-commit c12fe61d05fcbc0d4d1e4a959adf8e3956789f14 \
  --output /tmp/bist-window-2026-11-26.json
python -m scripts.historical_window_research --market gold --database "$GOLD_DB" \
  --asof 2026-11-25 --source-commit 43e998531920a109181de4f3dbc62df2303649f5 \
  --output /tmp/gold-window-2026-11-26.json
```

Üretim kaynakları ve canlı makbuzlar
[BIST arşiv commit'i](https://github.com/Mertsaglm/bist-analiz/commit/c12fe61d05fcbc0d4d1e4a959adf8e3956789f14) ·
[BIST son fiyatlı çevrim](https://github.com/Mertsaglm/bist-analiz/actions/runs/45799662675) ·
[Altın arşiv commit'i](https://github.com/Mertsaglm/gold_tracking_system/commit/43e998531920a109181de4f3dbc62df2303649f5) ·
[Altın fiyatlı çevrim](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/45806612222).
