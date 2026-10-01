# Üretim denetimi — 2026-09-30

**Sonuç: Son düzenlemenin bütün hedefleri üretimde çalışmıyor.** BIST'in yeni sanal hesap ve muhasebe çekirdeği tutarlı; fakat kapanış verisi gecikiyor, gecikmeyi telafi eden hat eksik ve gece yarısından sonraki kapanış tetikleri atlanıyor. Eski V1 karnesinde gerçek bir yanlış başarı kaydı doğrulandı. Ortak panelin altın tarafı hâlâ önceki sürümde.

Bu bir denetim raporudur. Üretim kodu, config, SQL, defter, GitHub workflow ve dağıtım değiştirilmedi. Deneyler geçici kopyalarda veya bellekte yapıldı; Telegram gönderilmedi. Rapor, kanıt dosyaları ve oturum hafızası yerelde kaydedildi.

## İncelenen sürüm ve geçmiş

| Katman | Sabit referans / gözlem |
|---|---|
| BIST yerel kod | `5d8805f`, 2026-09-25 sanal servet/model sınavı revizyonu |
| BIST üretim arşivi | `59e26644d61b15a2a7b3d9ed175aa2f3683fcfbd` |
| BIST snapshot | `2026-09-30T14:46:38.576087+00:00` — İstanbul 17:46 |
| Altın üretim arşivi | `d4db91e052dc9e68630fb0b950bf74062b29d213` |
| Altın snapshot | `2026-09-30T14:31:59+00:00` |
| İş akışı inceleme aralığı | 2026-09-25'ten BIST snapshot'ının alındığı kesite kadar |

`ai/PROJECT.md`, `STATE.md`, `PROFILE.md`, karar/ders kayıtları, 2026-09-15 ve 2026-09-25 raporları; önceki **“Tahmin motorlarını ve kanalları den-”** konuşması ve ilgili önceki inceleme konuşmaları okundu. 2026-09-25 konuşmasının devamında BIST için commit/push yetkisi verilmiş ve `5d8805f` yayımlanmış. STATE bunu yansıtmıyordu. BIST'in `advisor/`, `src/`, dashboard ve workflow kaynakları sabit üretim arşiviyle karşılaştırıldı; kaynak farkı bulunmadı. Altın yerel çalışma ağacında ise 61 değişiklik mevcut; bunlar yayımlanmamış.

Aşağıdaki sayılar **2026-09-30 sabit arşiv ölçümüdür**; gelecekteki canlı durumun garantisi değildir. Denetim her olası girdinin matematiksel doğruluk kanıtı değildir. Kod, test, gerçek veri, gerçek koşu logu ve kontrollü yeniden üretim birlikte kullanıldı.

## Öncelikli bulgular

### D-01 · P1 · V1 kurumsal işlem tablosu beslenmiyor; karne yanlış başarı içeriyor

**Yer:** `src/otonom.py:130`, `src/prices.py:182`, `src/prices.py:226`, `src/cli.py:52`, `src/resolver.py:130`, `advisor/history.py:60`.

Günlük otomasyon fiyat ve endeksi güncelliyor, ancak `sync_actions` çağrısını yapmıyor. Bu çağrı elle kullanılan veri komutunda var. SQL'deki `corporate_actions` tablosunda 1.266 kayıt var, son tarih **2026-07-21**. Tek başına son kayıt tarihi eksiklik kanıtı olmazdı; V2'nin aynı üretim arşivindeki güncel kurumsal işlem cache'i SQL'de olmayan somut olayları içeriyor: BIMAS 2026-09-16, TAVHL 2026-09-22 ve TUPRS 2026-09-30.

**Davranış kanıtı:** `2026-09-15-BIMAS-1` tahmini üretimde `hedef`, `hit=1`, net `ret_pct=8.0591` olarak sonuçlanmış. SQL'in bellek kopyasına yalnız BIMAS'ın 2026-09-16 tarihli 2,5 TL temettü olayı eklendi. Aynı resolver ve aynı fiyatlarla sonuç **`iptal_kurumsal`, `hit=null`, `ret_pct=null`** oldu. Karşı olgu fiyatı/modeli değiştirmiyor; eksik girdiyi tamamlıyor.

**Etki:** V1 başarı ve ortalama getiri sayıları bu kayıt bakımından yanlış. Ortak panel V1 sonuçlarını SQL'den okuduğu için yanlışlık görünümde de taşınıyor. Tüm tarihsel sonuçların etki büyüklüğü henüz hesaplanmadı; bir doğrulanmış örnek bütün V1 sonuçları hatalı demek değildir. V2 ayrı kurumsal işlem cache'i ve defteri kullanıyor; V2 için aynı muhasebe hatası saptanmadı.

**Kapanış ölçütü:** Kurumsal işlemleri otomatik veri hattına bağla; “kaynak başarısız” ile “işlem yok” ayrımını koru. Eksik dönemleri doğrulanmış kaynakla tamamla, etkilenen V1 sonuçlarını sürümlü bir düzeltme olarak hesapla. Eksik tabloyla BIMAS örneğinin sahte başarıya dönüşmesini davranış testi engellesin. Tarihsel arşivi sessizce üzerine yazma.

Kanıt: `reports/denetim-2026-09-30/corporate-counterfactual.json` ve `findings-reproduction.json`.

### D-02 · P1 · BIST taze kotasyon alıyor, fakat kapanış analizi iki gündür yetişmiyor

**Yer:** `.github/workflows/gunluk.yml:3`, `.github/workflows/portfolio.yml:38`, `advisor/service.py:137`, `advisor/service.py:231`, `advisor/__main__.py:165`.

2026-09-30 snapshot'ında 32/32 güncel referans fiyatı var; analiz tarihi **2026-09-28**, beklenen kapanış **2026-09-29**. 32 kararın tamamı `data_block`. SASA ayrıca geçmiş fiyat/hacim kalite kontrolünden geçmiyor. 73 hissenin tamamının son SQL barı 2026-09-28; BIST endeksleri de aynı tarihte. USD/TRY 2026-09-29'a ulaşmış.

Yeni hesapta 2026-09-29 ve 2026-09-30 günlerinin her birinde 32 gözlem çevrimi kaydedilmiş, **analiz sorunu olmayan çevrim sayısı sıfır**. Aktif ana defterde yalnız 2026-09-24 ve 2026-09-25 analiz günlerine ait 62 tahmin var; 28/29 Eylül için yeni tahmin üretilemiyor.

Günlük SQL hattı günde tek kez çalışıyor. Gün içindeki `advisor cycle` tarihsel fiyatı SQL arşivinden okuyor; önceki kapanışı tekrar indirmiyor. Gece verisi geç geldiyse ertesi günün sık tetikleri bunu düzeltemiyor. Günlük koşuların GitHub'da yeşil olması, beklenen son kapanışa erişildiğini kanıtlamıyor. V2 nöbetçisi analiz kapsamı ve karar verisi uyarısını gerçekten üretmiş; alarm tamamen sessiz değil.

**Kök neden sınırı:** 30 Eylül denetimi sırasında sağlayıcıdan salt okunur alınan THYAO/XU100 cevabında 29 Eylül barı vardı. Bu, barın önceki geceki koşu anında da bulunduğunu kanıtlamaz. Sağlayıcının geçmişteki eksik yanıtının kesin sebebi doğrulanmadı. Doğrulanan sistem açığı, geç gelen kapanışı telafi eden hattın olmaması.

**Etki:** Sistem döngü çalıştırıyor ama yeni karar/öğrenme örneği üretme görevini yerine getiremiyor. Güvenlik kapısının eski veriyle alımı durdurması doğru; sırf işlem çıksın diye bu kapı gevşetilmemeli. Ana hesabın nakitte kalmasının tamamını model başarısına veya “fırsat yok” durumuna bağlamak yanlış olur.

**Kapanış ölçütü:** Önceki seans verisi gelene kadar sınırları belirlenmiş bir telafi mekanizması; tazelik paydasında beklenen bütün isimler; korunmuş mevcut pozisyon takibi. Eski kapanışla başlayan bir günün yeni veri gelince toparlandığı uçtan uca gösterilmeli. Başarı, yalnız yeşil workflow veya kotasyon sayısı ile ölçülmemeli.

Kanıt: `bist-inventory.json`, `findings-reproduction.json`, `provider-probe.json`; [günlük koşu](https://github.com/Mertsaglm/bist-analiz/actions/runs/36630276524), [V2 nöbetçi](https://github.com/Mertsaglm/bist-analiz/actions/runs/36723198421).

### D-03 · P1 · İki yeni hesap hedefinin altın yarısı üretime çıkmamış

**Yer:** `ai/PROJECT.md:3`, `advisor/config.json:3`, `dashboard/public/insights.js:97`; [üretimdeki altın config, satır 3](https://github.com/Mertsaglm/gold_tracking_system/blob/d4db91e052dc9e68630fb0b950bf74062b29d213/advisor/config.json#L3).

BIST: başlangıç 2026-09-25, 50.000 TL, `paper-2026-09-25`, dört aday hesap. Altın üretimi: başlangıç 2026-09-15, 5.000 TL, eski hesap yapısı; yeni hesap kimliği ve yeni aday kataloğu yok. Yerel altın değişiklikleri üretim kodu değildir.

Canlı panelin JavaScript dosyaları yeni BIST sürümüyle eşleşiyor. Sabit gerçek API verilerini kullanan yerel tarayıcı doğrulamasında BIST 50.000 TL, altın 5.000 TL görünüyor; birleşik maruziyet “İki eşleşen ana hesap bekleniyor” diyor. Kimlik uyuşmazlığında toplam üretmemesi doğru savunma.

**Etki:** “İki ayrı 50.000 TL hesap ve ortak maruziyet” hedefi çalışmıyor. Bu, altın kodunun kendiliğinden geriye gitmesi olarak değil, **yayın kapsamının eksik kalması** olarak sınıflandırıldı. Mevcut altın hesabı kendi eski config'i altında tutarlı.

**Kapanış ölçütü:** Altın yerel kapsamını ayrı gözden geçirip yayın kararıyla tamamla; iki piyasada hesap kimliği/bütçe/başlangıç eşliği, adaylar ve ortak panel sonucu doğrulansın. Eski defter korunsun; eski 5.000 TL hesap yeni hesapmış gibi etiketlenmesin.

### D-04 · P2 · Gece yarısından sonra gelen kapanış yenilemesi atlanıyor

**Yer:** `advisor/service.py:93`–`101`, `.github/workflows/portfolio.yml:41`.

`closing_refresh` kararı, tamamlanan seansın tarihine değil çalışmanın İstanbul takvim tarihine bakıyor. Gece yarısını aşan çağrı ertesi günün kapanışından önce sayılıyor ve `closed` oluyor.

**Kanıt:** Gerçek `workflow_run` kapanış izleri 2026-09-28 22:18 UTC ve 2026-09-29 21:03 UTC'de mesai dışı olarak atlanmış. Geçici tam arşiv kopyasında `cycle(... now=2026-09-29T21:03:58+00:00, closing_refresh=True, offline=True)` sonucu `skipped=true`. Bu saat İstanbul'da 30 Eylül 00:03'tür. Deney bugünkü saate veya ağ durumuna bağlı değil.

**Etki:** Günlük veri hazırlığı geç bitince yeni kapanışın V2 değerleme/öğrenme çevrimi yürümüyor. D-02'deki eksik fiyat indirmeden ayrı bir hata: yalnız kaynak tazeliğini düzeltmek bu atlamayı çözmez.

**Kapanış ölçütü:** Kapanış görevinin ait olduğu seans açık olsun. Normal akşam, gece yarısından sonra, cuma sonrası ve tatil sınırları sınansın; yalnız değerleme yetkisi korunarak yeni hayali alım açılmasın.

Kanıt: `bist-runtime.json` → `midnight_closing_refresh`.

### D-05 · P2 · Gerçek tetikleme ritmi ilan edilen gözlem penceresini kapsamıyor

**Yer:** `advisor/config.json:72`, `.github/workflows/portfolio.yml:9`, `.github/workflows/advisor-watchdog.yml:4`.

Config gözlem penceresini 20:00 İstanbul'a kadar tanımlıyor. Dış dispatch izleri çoğunlukla 10:15–17:45 aralığında. 29 Eylül son gözlem 17:45 civarında; 20:00'a kadar yeni gözlem yok. Geç gelen cron çalışması pencere dışına düşüyor, gece kapanış yenilemesi de D-04 nedeniyle atlanıyor. GitHub cron ilk taraf yedeği var ancak gerçek çalışması ilan edilen sıklığı sağlamamış.

**Etki:** Pencerenin son kısmındaki hareketleri gözlediği söylenemez. 17:45–18:00 pozisyon koruma aralığının tamamı da düzenli gözlemle kapsanmıyor. Kapanış ve ücret matrahının “günün son gözlemi” yaklaşımı açısından izler seyrek kalıyor.

**Kapanış ölçütü:** Tetikleyicinin gerçek saatleri yeni pencerelerle eşleştirilsin; dış gözlemci son beklenen çevrimi defter zamanından kontrol etsin. Gözcü tamir veya işlem yapmasın. Dış scheduler'ın ayar ekranına erişilmedi; yanlış ayarın hangi hizmette olduğu **DOĞRULANMADI**. Kanıt gerçekleşen çağrı ve defter izidir.

Kanıt: `workflow-runs.json`, `bist-inventory.json` → aktif hesap `daily`.

### D-06 · P2 · KAP beklenen bildirim takvimi tavan nedeniyle yenilenemiyor

**Yer:** `src/news.py:167`–`193` ve `src/news.py:224`.

`expected_disclosures` tablosundaki 19 kaydın son çekim zamanı 2026-09-24 20:07 UTC. İncelenen günlük koşularda KAP yanıtı 2.000 kayda dayanıyor; 1.950 koruma sınırı nedeniyle liste kırpık sayılıyor ve eski snapshot tutuluyor. Günlük logda açıkça “BAŞARISIZ ... eski anlık görüntü korunuyor” yazıyor; genel workflow yine başarılı bitiyor.

**Etki:** İleriye dönük olay takvimine güncel/tam veri olarak güvenilemiyor. Bu, bütün KAP haberleri kesildi demek değildir: `disclosures` tablosu 29 Eylül'e kadar güncel. Kırpılmış listeyi tam kabul etmemesi doğru. Sorun veri kapsamının geri kazanılamaması.

**Kapanış ölçütü:** Desteklenen sorgu/pencere/sayfalama yoluyla tamlık kanıtı veya açık bir bilinmiyor durumu. Yalnız tavan eşiğini artırmak çözüm değildir. İlk sayfada bulunmayan bir şirketin “bildirimi yok” sayılmadığı test edilmeli.

Kanıt: `daily-evidence.txt`, `findings-reproduction.json`; [günlük koşu logu](https://github.com/Mertsaglm/bist-analiz/actions/runs/36630276524).

### D-07 · P2 · Mevcut üretim denetim komutu yeni hesap yolunu izlemiyor

**Yer:** `scripts/audit_production.py:31`, `:70`, `:146`–`159`.

Araç hâlâ `data/advisor/events.jsonl` eski defterini açıyor. Kök `latest.json` ise yeni hesabın snapshot'ı. Yeni snapshot hash'i eski defterde bulunamayınca araç `StopIteration` ile sonlanıyor. Sabit gerçek arşivle komut çalıştırılarak doğrulandı; yalnız kaynak metni tespiti değil.

**Etki:** Daha önce güvenilen audit komutu yeni üretimi doğrulayamaz. Bu raporda hesap keşfi yapılarak yedi defter ayrıca sınandı; mevcut komutun başarısızlığı atlanıp “audit geçti” denmedi.

**Kapanış ölçütü:** Config'den aktif hesap yolunu çöz; legacy ve bütün adayları ayrı doğrula. Yeni hesabın kurulmuş olduğu gerçekçi fixture ile komut uçtan uca tamamlanmalı; ücret borcu ve yeni olay türleri bağımsız muhasebeye dahil olmalı.

Kanıt: `old-audit.log`; komut tekrar üretim bölümünde.

### D-08 · P3 · Oturum hafızası yayın durumunda yanlış yönlendiriyordu

Denetim başındaki `ai/STATE.md:3`–`5` BIST'in de yayımlanmadığını söylüyordu. Konuşma devamı, commit ve çalışan üretim bunun aksini gösterdi. Altın hâlâ yayımlanmamış olduğundan “ikisi de yayımlandı” demek de yanlış. Eski STATE arşivlendi; yeni STATE iki durumu ayırıyor. Bu yalnız hafıza düzeltmesidir, üretim düzeltmesi değildir.

## Doğrulanan sağlam parçalar ve ölçüm sınırları

| Alan | Gerçek kontrol | Sonuç / sınır |
|---|---|---|
| Veritabanları | SQL arşivini geçici SQLite'a açma, integrity/foreign-key kontrolü, tablo kapsamı | İkisi de `ok`; FK ihlali yok. Semantik veri eksikleri D-01/D-02/D-06'da |
| Defterler | BIST legacy + yeni ana + dört aday + altın; hash zinciri ve bağımsız nakit/pozisyon hesabı | Yedi defterde mutabakat sağlandı; ücret, borç ve temettü alacağı dahil |
| Snapshot | Defterin snapshot hash'ine kadarki hali ile görünen servet/nakit/katkı/sonuç karşılaştırması | BIST/altın ana snapshot'larında fark yok |
| Kapsüller | BIST 713 + altın 255 dosyanın mühür/hash kontrolü | 968/968 geçti; bu bütün kararları tekrar yürütmek değildir |
| Replay | Her defterden ilk/orta/son mühürlü karar örneklerini kendi koduyla yeniden çalıştırma | 18 BIST + 3 altın, toplam 21 geçti |
| Eğitim | Üretim verisiyle dört BIST ve bir altın Ridge modelini yeniden fit etme | Katsayı farkı en çok yaklaşık `9.4e-13`; tolerans `1e-10` |
| Zaman ayrımı | Eğitim etiket bitişi, test başlangıcı ve model as-of kontrolü | İncelenen modellerde sınırlar tutarlı; sonradan düzeltilen piyasa geçmişi sınırı sürüyor |
| Tekrar çalıştırma | Her iki piyasada tam geçici kopyada iki offline cycle | Dört ana kitap ve BIST aday hesaplarında yinelenen dolum/para değişimi yok |
| Yedek/dönüş | Her iki piyasanın gerçek arşivinden yedek, boş geçici dizine restore | BIST 792, altın 307 dosya; hash ve hesaplar eşleşti |
| Telegram | Son snapshot ile defterdeki teslim makbuzu; hata ve toparlanma kayıtları | İki son snapshot'ın makbuzu eşleşti; kullanıcı cihazında okunma/teslim ayrıca görülmedi |
| Panel | Canlı statik dosyaların kaynak eşliği, API'nin yetkisiz isteği reddetmesi; sabit üretim verisiyle tarayıcı gezinme | API 401; BIST/altın/öğrenme ekranları çalıştı, console error/warn yok. Canlı oturum açılarak uçtan uca API doğrulanmadı |
| 2026-10-01 sınırı | Bellekte iki kez aylık katkı, üyelik değişimi, çeyrek ücret hesabı | Ana katkı bir kez 55.000 TL; TRMET giriyor/DSTKF çıkıyor; 32 izleme ismi. Saklama bekleyen gün yok; benchmark ücreti 120,75 TL. Gerçek 1 Ekim koşusu değildir |

Yeni izleme evreninden çıkmış fakat elde tutulan bir isim fiyat listesinde kalabilir; 1 Ekim'de başarı koşulu körlemesine “tam 32 kotasyon” değildir. İzleme listesi ve mevcut pozisyonların birleşimi kapsanmalıdır.

### Test sonuçları

- BIST yerel tam suite: **1.443 geçti**. Sabit üretim kaynaklarında tam suite: **1.442 geçti, 1 ortam hatası**. Hata GitHub tarball'ında `.git` olmadığı için `git check-ignore` çağrısındaydı; yalnız geçici arşive Git metadata'sı eklenip aynı test yeniden koşuldu ve geçti. Bir uygulama hatası gizlenmedi; ham log ve tekrar kontrol logu saklandı.
- Dashboard: **10 test geçti**, JavaScript syntax/build kontrolleri geçti.
- Altın **yayımlanmış eski sürümünde**: **939 geçti, 40 atlandı**. Atlamaların 7'si kurulu CLI girişi, 33'ü tarball'da Git metadata'sı bulunmaması nedeniyle. Atlananlar başarılı test sayılmadı. Bu sonuç altının yayımlanmamış yeni sürümüne ait değildir.
- Yeşil birim testleri D-01'deki gerçek SQL eksikliğini, D-04'teki geciken gerçek tetiklemeyi veya D-03'teki yayın eksikliğini kanıtlayamaz.

### Koşu başarısızlıkları

İnceleme aralığında BIST'te 162 Actions koşusu: V2 portföy 138 (130 başarılı, 8 başarısız), V2 nöbetçi 7, günlük 3, eski nöbetçi 3, test 7, yedek 3, haftalık 1. **25 Eylül'ün revizyon öncesi saatleri de bu toplamda vardır.**

Sekiz başarısız portföy koşusunun logları ayrı ayrı okundu: banka kaynağında 3 `ValueError`, 2 `ConnectTimeout`, 2 `ConnectionError`; bir koşuda PyPI bağımlılık indirme zaman aşımı, ardından eksik pandas. `ValueError` mesajının ayrıntısı yayımlanmadığından kesin alt sebebi doğrulanmadı. 30 Eylül bağlantı hatasının sonraki koşuda toparlandığı ve hata/toparlanma Telegram makbuzları görüldü. Tekil hata, bütün sistemin durmasıyla aynı şey değildir. Öte yandan 130 yeşil koşu da 130 kullanılabilir analiz anlamına gelmiyor (D-02).

## Modeller ve görünen servet ne söylüyor?

| Model | Tahmin MAE, yüzde puan | Sabit tahmin MAE | Onay |
|---|---:|---:|---|
| BIST ana | 10,7937 | 10,7335 | Hayır |
| Yakın dönem 20 seans | 11,1757 | 10,8013 | Hayır |
| Yakın dönem 5 seans | 4,9222 | 4,8678 | Hayır |
| Geri çekilme 5 seans | 4,9222 | 4,8678 | Hayır |
| Altın mevcut üretim | 5,3012 | 4,8750 | Hayır |

SMA50 fit edilen getiri modeli değildir. İki 5 seans adayının tahmin motoru aynı, işlem kuralı farklı. Mevcut modeller bu ölçümde sabit tahminin hata oranını yenmiyor. Canlı örtüşmeyen sonuç dönemi henüz sıfır; otomatik terfi yapılmaması doğru. MAE ile maliyet sonrası sanal portföy getirisi aynı ölçüm değildir.

BIST yeni ana hesap 50.000 TL nakit, sıfır dolum; aynı bütçeli al-tut 46.727,76 TL (sonuç −3.272,24 TL), nakit 2.801,63 TL, 32 pozisyon ve 17,20 TL temettü alacağı. SMA50 adayı 49.576,01 TL; diğer üç aday 50.000 TL nakit. Altın eski ana hesap 5.000 TL nakit; kendi al-tut hesabı 4.766,60 TL. BIST'in nakitte kalıp düşen al-tutu yenmesi, tek başına modelin öngörü üstünlüğü değildir; veri engellerinin etkisi ayrıca ayrılmalıdır.

## Açık kalan sınırlar ve bakım riskleri

- Güncel yeni sermaye modeli altın üretiminde çalışmadığı için ortak hesabın uçtan uca kabulü yapılamadı.
- Dış scheduler ayarları, gerçek banka işlem tarifesinin kullanıcı hesabına uygulanması, tarihsel banka kotasyonu/emir sırası ve Telegram alıcısının ekranı bağımsız doğrulanmadı.
- BIST `data/advisor` arşivi bu kesitte yaklaşık 197,6 MB. Kapsüller önceki olayları da içeriyor; büyüme saklama/clone/backup maliyetini artıracak. Mevcut yedek testi geçti; şu an bozulmuş yedek bulgusu yok. Saklama politikasını kanıt silmeden ayrıca ele almak gerekir.
- 2027 takvim varsayımları, temettü ödeme günü ve revizyon geçmişli enflasyon verisi önceki kapsam sınırları olarak sürüyor.
- Boş `indicator_daily`, `levels_daily`, `data_quality` tabloları tek başına arıza sayılmadı: ilgili üretim yolu ve yeniden hesaplama davranışı incelendi. Sonuç kaydının/tazeliğin gerçekten gerekli olduğu tablolar ayrı değerlendirildi.

## Önerilen düzeltme sırası ve kabul deneyi

1. **V1 yanlış karne ile V2 veri tazeliği:** D-01 ve D-02. Önce doğru veri akışı, sonra kontrollü tarihsel düzeltme. Yeni veriyle bir günün toparlanmasını göster; mevcut pozisyon korumasını kaybetme.
2. **Seans sonu zinciri:** D-04/D-05 ve yeni hesabı tanıyan audit aracı D-07. Gece yarısını geçen tetik + sonraki sabah + tekrar koşu + yedek geri dönüşünü aynı senaryoda sına.
3. **Yayın kapsamı ve dış veri:** Altın sürüm eşliğini yayın kararıyla tamamla, KAP tamlık sorununu çöz. İki hesapta ortak panel, bildirim makbuzu ve yeni aday defterlerini birlikte doğrula.

Her düzeltmede bir davranış regresyon testi ve etkilenen hattın tam kopyada uçtan uca koşusu gereklidir. Yeni test, eski hatayı geri koyunca kırmızıya dönmelidir. Model eşiğini düşürmek veya rastgele alım ürettirmek bu denetimin önerisi değildir.

## Kanıtı tekrar üretme

Kanıt paketi: `reports/denetim-2026-09-30/README.md`. Sabit arşiv SHA'larıyla yeniden indirilen kopyalar kullanılmalı; hareket eden `main` aynı deney değildir. Mevcut özel GitHub deposuna okuma yetkisi gerekir.

En küçük salt-okur davranış kanıtı:

```sh
.venv/bin/python reports/denetim-2026-09-30/reproduce_findings.py /path/to/extracted-bist-archive
```

Mevcut eski audit aracındaki hatanın kanıtı:

```sh
.venv/bin/python scripts/audit_production.py --root /path/to/extracted-bist-archive --output /tmp/old-audit-result.json
```

İlk komut SQL'i geçici olarak restore eder; karşı olgu yalnız bellek veritabanında, katkı/ücret deneyi yalnız kaydedilmeyen defter nesnesinde yapılır. İkinci komut incelenen sürümde `StopIteration` ile biter. Üretim veri dosyaları değiştirilmez.
