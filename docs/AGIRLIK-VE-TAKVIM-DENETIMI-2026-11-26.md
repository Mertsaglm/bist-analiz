# 26 Kasım takip denetimi

25 Kasım kapanışıyla sabitlenen SQL arşivleri ve önceki deney makbuzları
kullanıldı. Yeni deney yerel ve keşif amaçlıdır.
[Ön kayıt](AGIRLIK-VE-TAKVIM-ON-KAYIT-2026-11-26.md) ·
[Çalıştırılabilir kod](../scripts/historical_followup.py) ·
[Satır bazlı makbuz](../reports/historical-window-2026-11-26/followup.json)

## Beş denetim sorusu

1. Pasife göre BIST farkı **50.000 TL toplam portföyün** getiri
   farkıdır. %80 aynı sepet, %20 farklı kullanım. Likit Ridge +0,1507
   yüzde puan ortalama fark, dönem başına yaklaşık 75 TL.
2. Önceki koşuda BIST'te 2 evren × 6 aktif politika × 2 maliyet
   = 24 aktif sonuç hücresi. Altında 6 × 2 makas = 12. Toplam **36 aktif
   hücre**, nakit ve pasif referanslarla **48**. BIST özellik duyarlılığı
   aynı tasarımın 24 aktif hücresini tekrarladı. Duyarlılık dahil 60
   aktif ve 80 toplam rapor hücresi var. Birbirine bağlı koşular
   bağımsız deneme sayısı olarak yorumlanmaz. Takip koşusu yedi
   Ridge özelliği/ağırlık birleşimi, sıfır referansı, üç önceden
   belirlenmiş eşli fark ve iki makasta 14 aktif ekonomik hücre içerir.
3. Ocak 2022 başlangıcı ilk ön kayıtta bulunuyor. Beş takvim yılı
   adayına önceki fiyat ve özellik ısınması bırakıp iki piyasada ortak
   bir başlangıç sağlıyor. Takvim dilimleri rejim sınıflandırması yerine
   sabit tarih gruplarıdır. 2022 başındaki ilk altın icrası 4 Ocak.
4. Altın SMA50 hesabında iki makasta da iki defter bölümü toplamı
   **113 alış ve 8 satış**. Bunlar tekil işlem günü sayısı değildir.
   Devir %3 makasta %253,64, %4'te %249,81. Payda ortalama hesap değeri,
   dönem yaklaşık beş yıl. Taktik dilim kapanışların %80,81'inde
   altındaydı. En büyük düşüş %3 makasta SMA50 −%22,56, pasif −%23,70.
5. BIST üretiminde 200 **sembol barı** kuralı ve sembol barıyla
   hesaplanan 20 bar vadesi var. Aşağıdaki veri üzerinde iki etki ayrı ölçüldü.

## Altın ağırlık ablasyonu

Üretim ana Ridge'i genişleyen geçmişi ve eşit ağırlığı kullanır.
126 seans yarı ömrü ayrı adaylarda kullanılır. T0'ın ons/kur özellikli
adayı, ons ve kuru ayrı ayrı tahmin edip toplayan önceki araştırma
kolundan farklıdır. T0 adayı gram getirisini doğrudan tahmin eder.
[Ana eğitim](../advisor/learning.py) · [Canlı aday ayarı](../advisor/candidates.py) ·
[T0 aday eğitimi](../advisor/specialized.py)

| Aynı 59 olgun tarihte | Eşit ağırlık MAE | 126 yarı ömür MAE | Fark, yüzde puan |
|---|---:|---:|---:|
| Genişleyen, temel özellikler | 5,36 | 6,69 | +1,33 |
| Son 756 eğitim tarihi, temel özellikler | 5,85 | 6,65 | +0,81 |
| Son 756, T0 ons/kur özellikleri | 5,98 | 6,77 | +0,79 |

Sıfır tahmini 5,54. Ayrı canlı araştırma adayı recent-20-v1 aynı
tarihlerde 6,59. 6 dönem blok aralıkları sırasıyla [0,20, 2,72],
[0,04, 1,85] ve [−0,02, 1,89]. Bunlar daha önce görülmüş tarihsel
örnekleme koşullu, tek tek tanısal aralıklardır. Model ayarlarıyla
yeniden oluşturulan tahminler kullanıldı. Tarihsel canlı dosyalar ve
kalibrasyon düzeltmesi yeniden oynatılmadı.

%3 makasta genişleyen temel modelde ağırlık son net değeri 1.061.034
TL'den 1.080.436 TL'ye çıkardı, %4 makasta 1.020.709 TL'den 1.011.262
TL'ye indirdi. T0 ons/kur özellikli modelde %3 makasta iki ayar
yakın kaldı, %4 makasta ağırlıkla son değer yaklaşık 10.845 TL düştü.
Bütün kollar iki senaryoda da %100 pasifin gerisinde. Bu portföy
önceki sabit makaslı araştırma vekilidir, tam T0 işlem politikası
ve gerçek tarihsel İş Bankası replay'i kapsam dışıdır.

## BIST gösterge etkisi ve çok yıllı replay kapsamı

| Likit 30, 3 yıllık Ridge | Pasife göre fark |
|---|---:|
| İlk yöntem, aynı 19 tarih | +0,4231 puan |
| Gözlenen bar yöntemi, aynı 19 tarih | +0,3055 puan |
| Gözlenen bar yöntemi, ek 38 tarih | +0,0734 puan |
| Gözlenen bar yöntemi, birleşik 57 tarih | +0,1507 puan |

İlk düşüş −0,1176 puan veri işleme değişikliğiyle, ilave −0,1547
puan tarih kapsamının genişlemesiyle ilişkili. Evren değişince işaret
değişebildiği için +0,15'i üst sınır diye yorumlamak için dayanak yok.

**Üretim özellik yolunda doğrulandı.** Takvime boş satır ekleyen ilk
araştırma yönteminde 9 Nisan’dan itibaren 200 seans boyunca 24/30
uygun özellik kapsamına ulaşılamadı. SQL'deki sembol barlarıyla çalışan
üretim özellik yolunda aynı eşiğe **200 seansın 199’unda** ulaşıldı.
9 Nisan kapanışının kendisinde güncel ve kaliteli giriş girdisi
**0/30**. Sonraki uygun bar kalite ve tazelik koşullarını yeniden
sağlayabilir. Bu ölçüm, bugünkü 30 üyeye uygulanan tarihsel veri yolu
provasıdır. Tarihsel canlı karar veya dolum sayısı değildir.

Buna karşılık eğitim hedefi takvimle kayabiliyor. Üretimle aynı
özellik yolunda 192.958 uygun ve tarih eşlenebilir etiketin **1.160**'ı
ortak piyasa vadesinden farklı. 9 Nisan’la kesişen 1.440 etiketin
**1.140**'ı kaydı. Örnek AKBNK 12 Mart 2024 sinyalinin 20. piyasa
seansı 9 Nisan iken sembol barı hedefi 15 Nisan. Bu, yeni hedef sürümü
ve eski mühürlere dokunmadan bir davranış sınavı gerektirir.
[Ham arşiv çağrısı](../advisor/service.py) · [Bar tabanlı özellik ve hedef](../advisor/learning.py) ·
[Resmî yarım seans kaydı](https://www.borsaistanbul.com/files/pay-piyasasi-2024-yili-tatil-tablosu.pdf)

2022–25 Kasım 2026 arasında arşiv takvimindeki **1.227** seansın
**43’ünde** zamanında bilinen 30 üyelik proje kaydı mevcut. Bu
43 seansın 9’unda SASA fiyat/hacim girdisi uygun değil. Geçmiş dönemlere
ait resmî değişiklik ilanları var. Uzun, aylık katkılı V2 tekrarı
için ilanlardan dönem içi değişiklikler, tam sepet, ham lot/fiyat ve
kurumsal işlemlerin ödeme tarihi zinciri kurulmalı. Bu turda çok yıllı
V2 ekonomik sonuç üretilmedi.
[Borsa İstanbul 2022 ilk çeyrek değişiklikleri](https://borsaistanbul.com/duyuru/12771/2022-yili-birinci-uc-aylik-donemi-icin-bist-pay-endeksleri-kapsaminda-yer-alacak-paylarda-degisiklik-yapilmistir) ·
[Endeks duyuruları](https://www.borsaistanbul.com/endeksler/endeks-duyurulari) ·
[DataStore](https://www.borsaistanbul.com/veriler/gecmise-donuk-veri-satisi)

İş Yatırım'ın tarihsel yanıtında 9 Nisan 2024 için AKBNK, THYAO
ve SASA kapanış ve pozitif işlem tutarı var. SASA'nın yukarıdaki
dokuz gününün tamamında da fiyat ve işlem tutarı geldi. Örnek
AKBNK ham kapanış 56,70 TL ve işlem tutarı 1.527.223.611 TL.
İncelenen yanıt açılış ve lot hacmi vermediği için mevcut OHLCV
şemasına ve replay'e aktarılmadı. [Sorgular ve satır makbuzu](../reports/historical-window-2026-11-26/isyatirim-source-check.json)

Altında bağımsız referans için LBMA geçmiş tablosu erişim
koşullarına bağlı. TCMB USDTRY, gün içi gözlemlerin 15.30'da
ilan edilen ortalamasıdır. Bu iki veri eşzamanlı fiyat olarak
kullanılamaz. İş Bankası ve mevcut sağlayıcının kamuya açık
güncel alış/satış sayfaları var. Sağlayıcının İş Bankası tarihsel
seri adresi bu denetimde HTTP 403 döndürdü. Çok yıllık iki taraflı
banka kotasyonu doğrulanamadı.
[LBMA erişim koşulları](https://www.lbma.org.uk/articles/lbma-benchmark-prices-data-tables-are-moving) ·
[TCMB yöntem ve saat](https://www.tcmb.gov.tr/wps/wcm/connect/EN/TCMB%2BEN/Main%2BMenu/Core%2BFunctions/Exchange%2BRate%2BPolicy/Foreign%2BExchange%2Band%2BBanknotes%2BMarkets/Indicative%2BExchange%2BRates) ·
[İş Bankası fiyat bilgisi](https://www.isbank.com.tr/fiyatlar-ve-oranlar)

## Ortak T0

26 Kasım İstanbul kesitinde son yayımlanmış fiyatlı makbuzlar BIST
14.17 ve altın 14.31. İkisinin kaynak analizi 25 Kasım ve görünen ortak
hesap sayısı sıfır. İki main ayarında tarih 27 Kasım. Doğrulama anında
yayımlanan SQL blob'ları araştırma kopyalarıyla aynıydı.
[BIST fiyatlı çevrim](https://github.com/Mertsaglm/bist-analiz/actions/runs/45808968949) ·
[Altın fiyatlı çevrim](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/45811243780)

İlk kabul için BIST 26 Kasım kapanışı ve 30/30 uygun çekirdek
kotasyonu gerekir. Altın 25 Kasım teorik kapanışı ve yeni İş Bankası
GRAM kotasyonunu, çekirdek için %4 makas sınırında kullanır. İki piyasada
beşer sözleşme ve kol başına 50.000 TL katkı, ilk uygun farklı
kotasyondaki dolum zinciri ve tekrar çalıştırmada çift kayıt oluşmaması
kontrol edilir. 5.000 TL aylık katkı sözleşmede doğrulanır. Telegram
teslimi ayrıdır. İleri momentum kendi hesabında sürer. Beşinci model kolu,
önceden ilan edilen karşılaştırmayı tamamlamak üzere kalır. SMA50
için kanıt bağımsız bir ileri aday hipotezini destekler.
[T0 kabul ve ekonomik sözleşme](PORTFOY-DENEYI-2026-10-01.md)

Tekrar üretim için önceki raporda tarif edilen arşiv kopyalarıyla:

```sh
python -m scripts.historical_followup --bist-db "$BIST_DB" \
  --gold-db "$GOLD_DB" --gold-config "$GOLD_CONFIG" \
  --output /tmp/historical-followup-2026-11-26.json
```

## Yayın doğrulaması

26 Kasım güncel main kopyasında 1.584 test geçti, 19 test atlandı.
Doküman bağlantıları geçti. BIST 25 Kasım SQL kopyasında, 26 Kasım
tarihli varsayımsal kotasyonlarla beş kol açıldı ve çekirdek 30
pozisyon aldı. Olay defteri ve bağımsız muhasebe mutabakatı, yedekten
okuma ve aynı kotasyonla tekrar kontrolü geçti. 27 Kasım canlı
açılışının kabulü ayrıca ölçülür.
[Geçici defter makbuzu](../reports/historical-window-2026-11-26/pre-t0-smoke.json)
