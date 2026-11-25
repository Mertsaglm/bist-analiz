# Üretim denetimi sonrası düzeltmeler — 2026-09-30

> **Tarihsel kesit:** Bu belgedeki ölçüm ve yayın durumu yazıldığı tarihin kesitidir.
> Güncel üretim ve açık işler için [ai/STATE.md](../ai/STATE.md) ile
> [2026-10-01 deney durumuna](PORTFOY-DENEYI-2026-10-01.md) bakın.

2026-09-30'da yerel düzenlemeler tamamlanmış, yayın bekliyordu. Kod
2026-10-01'de yayımlandı; BIMAS geçmiş üretim kaydı düzeltmesi ayrı ve bekliyor.
Kaynak denetim: `docs/URETIM-DENETIM-2026-09-30.md`.
Kanıt paketi: `reports/duzeltmeler-2026-09-30/README.md`.

## Bulguların karşılığı

| Bulgu | Düzenleme | Doğrulama / kalan sınır |
|---|---|---|
| D-01 | Günlük V1 hattı karar/resolver öncesi kurumsal işlemi yeniler; kaynak arızası boş takvim sayılamaz. | Gerçek 73 hisse sorgusu başarılı. Geçmiş yanlış BIMAS başarısı için mühürlü plan hazır; üretime uygulanmadı. |
| D-02 | Portföy öncesi hisse/endeks bazında eksik kapanış telafisi; başarılı alt küme saklanır. | Geçici SQL'de 73 eksik kapanış tamamlandı; 32 veri engeli 1'e düştü. SASA sıfır hacimli olduğundan korunuyor. |
| D-03 | Altının bekleyen 50.000 TL hesap ve dört aday düzenlemesi, güncel ortak çekirdekle doğrulandı. | Eski 5.000 TL deftere dokunmadan yeni hesap başlatıldı; yalnız geçici kopyada. Yayın gerekli. |
| D-04 | Kapanış yenilemesi son tamamlanan seansı kullanır. | Gece yarısı, hafta sonu, yarım gün; değerleme var, yeni dolum yok. |
| D-05 | BIST cron ve yerel gözlem penceresi genişletildi; SQL yazarları kayıpsız bekleme kuyruğunu paylaşır. | Yapı sözleşmesi geçti. Dış scheduler ayarı ve gerçekleşmiş 15 dakika ritmi henüz doğrulanmadı. |
| D-06 | Tavana gelen KAP takvim sorgusu tarih aralıklarına bölünür; tek gün bile kırpıksa/alt sorgu düşerse başarısızdır. | Gerçek kaynakta 2006 ham kayıt; evrenden 63 isim için 192 kayıt geçici DB'ye yazıldı. |
| D-07 | Audit aktif hesap yolunu izler, eski/aday defterleri de tarar; ücret borcunu bağımsız hesaplar. | Gerçek arşivlerde muhasebe, hash, model ve yedek doğrulamaları. Kapanış kipi ve tarihli üyelik de kopyaya taşınır. |
| D-08 | Proje hafızası gerçek yayın durumuna göre yenilendi. | BIST eski revizyonu yayımlanmıştı; bu düzeltmeler ve altın yeni hesap yayını henüz yapılmadı. |

## Karne düzeltmesinin kapsamı

Yeni kaynak taramasında SQL'de bulunmayan 18 kurumsal olay çıktı; yakın dönemdeki
BIMAS, DOAS, TAVHL, TUPRS yanında yeni sembollerin eski olayları da var. Sağlayıcının
12 mevcut değer farkı ayrı kaydedildi; çoğu kayan nokta farkı, EREGL 2008 temettüsü
ise maddi bir kaynak revizyonudur. Mühürlü plan yalnız eksik 18 olayı ekler;
mevcut çelişkili tutarı ezmeyi reddeder. Otomatik fiyat/kurumsal kaynak senkronu
ayrıca güncel sağlayıcı değerlerini saklar; geçmişte bilinen sürüm iddiası yoktur.

Arşivdeki 47 sonuç yeniden değerlendirildi. Yalnız `2026-09-15-BIMAS-1`, yanlış
`hedef` / net %8.0591 kaydından `iptal_kurumsal` durumuna geçiyor; getiri ve başarı
alanları boşalıyor. Önceki satır plan içinde korunuyor; resolver sürümü değişiyor.
Uygulama yalnız DB kopyasında yapıldı ve ikinci uygulama ek değişiklik üretmedi.
Salt-okur kaynak DB'nin SHA-256 değeri değişmedi.

Bu sınav resolver'ın ikinci kusurunu ortaya çıkardı: 1 Eylül'de stop ile kapanan
TAVHL, 22 Eylül temettüsü yüzünden iptal ediliyordu. Artık olaylar bar sırasıyla
işlenir; pozisyon kapandıktan sonraki olay sonucu silemez. Böylece geçerli kayıp
karneden çıkarılmadı. Eski hata geri konunca regresyon testi kırılıyor.

Plan üretmek ve açıkça seçilmiş **DB kopyasında** uygulamak için:

```bash
python scripts/repair_corporate_outcomes.py --database /tmp/inceleme.db --actions /tmp/kurumsal.json --output /tmp/plan.json
python scripts/repair_corporate_outcomes.py --database /tmp/inceleme.db --apply-plan /tmp/plan.json --output /tmp/makbuz.json
```

Üretim arşivi ilerlediğinde eski planı zorla uygulama: plan satır eşliğini kontrol
eder ve değişmiş sonuçta durur. Yayın öncesi güncel üretim kopyasında tekrar planla,
önceki/sonraki farkı koru, SQL integrity ve tek kayıt etkisini tekrar doğrula.

## Zincir ve test kanıtı

2026-09-30 ölçümü: BIST **1459 geçti**; altın **998 geçti, 8 atlandı**.
Atlanan testler geçti sayılmaz. Her iki panelde **10 test geçti**; ortak çekirdekte
**33 dosyanın** hash eşliği doğrulandı. Sayılar tarihli makbuzdur; güncel değer için:

```bash
.venv/bin/python -m pytest -q -rs
npm --prefix dashboard test
.venv/bin/python scripts/advisor_manifest.py --peer ../gold_tracking_system
```

Altın testleri kendi checkout'unda çalıştırılır. HTTP ve curl_cffi ağ çağrıları
iki suite'te de uygulamanın `except Exception` bloğuyla yutulamayacak biçimde yasak.
Bu zorlama BIST CLI/otonom ve altın panel testlerinde eksik dış kaynak mock'larını
ortaya çıkardı; ilgili testler tüm dış girdilerini açıkça taklit ediyor.

Geçici BIST zincirinde analiz 29 Eylül'e ulaştı: 22 `no_edge`, 9 `reward_risk`,
1 SASA `data_block`. Bu sonuç sabit 29 Eylül kapanışına aittir; 30 Eylül
kapanışını kullanan gece yarısı simülasyonunda analiz sorun listesi boştur.
İki aynı çevrim muhasebeyi değiştirmedi; dört aday oluştu.
Gece yarısına taşınan kapanış değerleme yaptı. Altın yeni hesapta 50.000 TL ve dört
aday üretildi. İki piyasada eski defter hash'i ve yedekten dönüş eşliği korundu.
Bunlar gerçek emir veya canlı yatırım başarısı değildir.

Altı bağımsız hata geri koyma sınavı kırmızıya döndü: kurumsal adımı kaldırma,
erken kapanan işlemi iptal etme, KAP kırpılması, eski audit, yanlış gece yarısı
tarihi ve kapanış telafisini kaldırma. Kırmızı sonuçlar kanıt paketindedir.

## Yayın ve açık dış sınırlar

- Commit/push/deploy yapılmadı; üretim SQL'i, gerçek defter ve Telegram değişmedi.
- BIST ve altın değişiklikleri birlikte yayımlanmalı; hesap bütçeleri/sürümleri
  ilk güncel çevrimde karşılaştırılmalı. Altında 25 Eylül'den kalan yerel revizyon
  bu yayın kapsamının parçasıdır; yalnız son birkaç dosyayı göndermek yeterli değil.
- SQL yazan işler `repo-commit`, `cancel-in-progress: false`, `queue: max` kullanır.
  Varsayılan tek bekleyen kuralının günlük işi iptal etmesini önlemek için maksimum
  kuyruk seçildi; sıradan çıkan iş güncel `main` dalını okur. GitHub bunun en fazla
  100 bekleyen çalıştırmayı tuttuğunu belirtir; sıra baskısı ve gecikme izlenmeli.
  Kaynak: https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency
- GitHub cron kesin saat garantisi vermez. Dış 15 dakika tetikleyicisinin erişimi
  bilinmediğinden o servis değiştirilmedi; D-05'in canlı ritim kısmı açık.
- SASA'nın 29 Eylül dahil sıfır hacimli barları kaynaktan geliyor; bar değerlemede korunuyor fakat
  yeni işlem için geçerli sayılmıyor. Hacim uydurulmadı veya kalite kapısı gevşetilmedi.
- Önceki hatalı rapor/Telegram mesajları geriye dönük silinmez. Onaylı karne
  uygulamasından sonra güncel rapor yeniden üretilmeli; geçmiş kayıt kanıt kalır.
