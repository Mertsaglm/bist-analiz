# BIST ve Altın hata denetimi — 2026-10-28

> Ekim 2026 çalışma kesiti. Sonraki üretim ve açık işler [STATE](../ai/STATE.md) ile [24 Kasım denetiminde](DENETIM-2026-11-24.md).

Bu çalışma teşhistir. Mert'in talebi gereği kod, üretim verisi, workflow,
ödeme ayarı ve repo görünürlüğü değiştirilmedi. Düzeltme için kullanıcı onayı bekleniyor.
Yerel rapor ve hafıza kayıtları güncellendi; mevcut yerel değişiklikler korundu.

## Sonuç

Bütün bildirimleri geliştirme döneminin olağan gürültüsü saymak yanlış.
BIST bugün fiilen durmuş; altın çalışıyor fakat hem gerçek kaynak hataları hem
yanlış sınıflandırılmış makas alarmları var. Yalnız maili kapatmak çözüm olmaz.

| GitHub oluşturma tarihi, UTC | BIST başarısız / toplam | Altın başarısız / toplam |
|---|---:|---:|
| 2026-09-01–30 | 41 / 421 | 9 / 567 |
| 2026-10-01–28 | 258 / 845 | 57 / 1000 |

Toplam 2833 ayrı koşunun metadatası sayıldı. 20 başarısız koşunun job/log/annotation
ayrıntısı ve ek iki BIST koşusu incelendi. Her başarısız koşunun bütün logları
incelenmedi; tablo kök nedenlerin tam dağılımı değildir. Tek arıza çok sayıda koşuyu
kırmızıya çevirebilir. Yeşil koşu da veri, karar veya Telegram teslimi kanıtı değildir.
Ekim sayımı 28 Ekim 14:45:42 UTC'deki son koşuya kadar alınan API kesitidir.
Altının 1000 sonuç API sınırı, ay iki parçaya bölünerek ayrıca kontrol edildi.

Gmail'de 1–30 Eylül UTC aralığına yönelik sorgu 54 bildirim döndürdü;
yeniden denemeler de mail üretir. Okunan 1 Eylül BIST nöbetçi, 30 Eylül BIST portföy,
28 Ekim BIST portföy ve altın nöbetçi mailleri aynı Actions run ID'lerine bağlı.
Mail bağımsız ikinci bir arıza değildir. Özel mail içeriği rapora kopyalanmadı.

## 1. P1 — BIST job'ları ödeme/harcama engeliyle başlamıyor — DOĞRULANDI

- [28 Ekim portföy](https://github.com/Mertsaglm/bist-analiz/actions/runs/40709127985):
  job adımı yok, runner atanmamış. GitHub annotation'ı ödeme başarısızlığı veya
  harcama limiti nedeniyle job'un başlamadığını söylüyor.
- [23 Ekim 10:30 UTC örneğinde](https://github.com/Mertsaglm/bist-analiz/actions/runs/39939625653)
  aynı engel var. 28 Ekim test/nöbetçi ve 23 Ekim günlük koşu örneklerinde de aynı.
- Sabit üretim commit'i `117499f40db3e02dadcb3e3b438d16094eb5718e`.
  Son V2 görünümü/aktif defter çevrimi **2026-10-23 13:17:29 TR**, analiz günü
  **2026-10-22**. Üretim SQL'sinde son hisse/endeks günü de 22 Ekim.
- BIST private, altın public. Standart public runner'ın ücretsiz olması, altın
  çalışırken private BIST'in hesap engeline takılabilmesiyle tutarlı.
  [GitHub billing açıklaması](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
- Konum: `.github/workflows/portfolio.yml:26` runner isteği; hata uygulama satırında
  değil, GitHub `.github:1` annotation'ında.

**28 Ekim ek doğrulama:** GitHub'ın 23 Ekim 13:18 TR tarihli maili hesabın aylık
2.000 ücretsiz Actions dakikasının %100'ünün kullanıldığını açıkça bildiriyor.
5 Ekim 11:27 TR tarihli mail de 0,5 GB ücretsiz Actions depolama hakkının %100'üne
ulaşıldığını bildiriyor. Bu, job engeli ve artifact hata zamanlarıyla örtüşüyor.
[Dakika maili](https://mail.google.com/mail/u/0/#all/1a16844d22d80414),
[depolama maili](https://mail.google.com/mail/u/0/#all/1a10b2cc860071b1).

**Bilinmeyen:** Hesabın ek harcama bütçesi veya ödeme yöntemi durumu nedir?
Annotation ödeme hatası ile harcama limitini ayırmıyor. Billing kullanım API'si mevcut yetkiyle 404 ve ek
`user` scope gereksinimi döndürdü; yetki veya ödeme ayarı değiştirilmedi.
Kesin borç, plan, kalan hak veya ay başında otomatik düzeleceği iddia edilemez.

**Öneri:** Önce hesabın Billing ekranında engeli belirle; ardından mevcut bütçede
çalışma sıklığı/kurulum maliyetini azaltma veya açık tavanlı kullanım seçeneğini kararlaştır.
Repo public yapılması ayrı bir kapsam/gizlilik kararıdır; otomatik çözüm değildir.
DoD: runner gerçekten başlar; taze veriyle atlanmamış çevrim, kalıcı defter ve Telegram
makbuzu doğrulanır. Yalnız yeşil workflow yeterli değildir.

## 2. P1 — BIST harici yedek yüklemesi kotaya takılmış — DOĞRULANDI

- [6 Ekim yedeği](https://github.com/Mertsaglm/bist-analiz/actions/runs/37398718244):
  ZIP oluşturma ve recovery-check başarılı, upload-artifact adımı depolama kotasıyla
  başarısız. [23 Ekim hata kurtarma yüklemesinde](https://github.com/Mertsaglm/bist-analiz/actions/runs/39916630808)
  de aynı hata var.
- Listeleme anında **13 süresi dolmamış artifact, toplam 1.269.945.729 bayt** var.
  Son başarılı artifact 2 Ekim 23:54:50 UTC; boyutu **336.038.973 bayt**.
- Günlük tam yedek 90 gün tutuluyor: `.github/workflows/advisor-recovery.yml:26`.
  `advisor/recovery.py:24` tüm uygun arşivleri alıyor;
  `advisor/capsule.py:26` her kapsüle o ana kadarki defterin tamamını koyuyor.
  Bunlar büyümeyi açıklayan mekanizmalar; boyut katkıları ayrı ölçülmedi.
- Git'teki SQL/defterin varlığı bağımsız harici yedeğin güncel olduğunu kanıtlamaz.

**Öneri:** Silmeden önce gerekli artifact'leri indirip checksum ve geri dönüşünü doğrula;
sonra onaylı saklama/temizleme listesi ve büyüklük bütçesi uygula. İleriye dönük
saklama süresini kısalt, kapsül/defter tekrarını replay kanıtını koruyarak azalt.
DoD: yeni yedek yüklenir, boş geçici dizinde bütün defter/hash/nakit eşliği geçer;
ölçülmüş günlük büyüme ayrılan kotada kalır. Saklama süresini değiştirmek mevcut
artifact'leri kendiliğinden temizleyen bir çözüm sayılmaz.

## 3. P1 — Üretim arşivinde tutarsız TMSN barı — DOĞRULANDI

- Gerçek üretim SQL arşivi, proje DB'sine dokunmadan RAM'de açıldı:
  **207.741 hisse barında 1 OHLC ihlali** bulundu.
- TMSN, **2026-10-22**: açılış 51,30; yüksek 53,55; düşük **50,10**;
  kapanış **50,05**. Kapanış günün düşüğünden küçük. Kaynak etiketi yfinance.
- [23 Ekim gerçek test koşusu](https://github.com/Mertsaglm/bist-analiz/actions/runs/39935513959)
  1477 geçti / 2 başarısız: iki test aynı OHLC tutarlılığı sınıfında hata veriyor.
  Konum: `tests/test_prices.py:251`, `tests/test_indicators.py:374`;
  veri giriş yolu `src/prices.py:188`.

**Sınır:** Hangi alanın gerçekte yanlış olduğu ve kaynağın sonradan düzeltip
düzeltmediği DOĞRULANMADI. Bu kayıt nedeniyle yanlış işlem yapıldığı kanıtlanmadı.
Kaynağın sunduğu veriyi sırf test geçsin diye aritmetik olarak düzeltmek kabul edilemez.

**Öneri:** Tarihli güvenilir kaynakla doğru barı doğrula; öncesi/sonrası makbuzuyla
yalnız doğrulanan kaydı onar. Geçersiz yeni barı görünür biçimde karantinaya alan
girdi denetimi ve davranış regresyon testi ekle. DoD: tutarlılık testi geçer,
bozuk örnek reddedilir, eksik veri normal sonuç gibi sunulmaz.

## 4. P2 — Altında geniş makas, veri arızası diye raporlanıyor — DOĞRULANDI

- [28 Ekim nöbetçi](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/40690487498)
  yalnız `decision_data: GRAM` nedeniyle başarısız.
- Aynı commit'in `0cecf90869463693650c96f2a7eb2fd8a1f6ca0e` görünümünde fiyat
  **1/1 geçerli**, kapanış güncel, koşu hatası yok. Karar gerekçesi geniş banka makası.
- Kayıtlı alış 6053,02 / satış 6900,84: kodun hesabıyla `ask/bid−1 = %14,00656`;
  eşik %3. Bu kotasyonun tarihsel banka doğruluğu ayrıca kanıtlanmadı; bunlar
  sistemin kaydettiği rakamlar. `price_problem` aynı anda `None`, `usable` geniş makas döndürüyor.
- Altın aktif hesabının Ekim kararlarında 636 kaydın 59'u veri bekliyor:
  **57 geniş makas, 2 fiyat kaynağı yok**. Bunlar karar kaydı sayılarıdır;
  43 başarısız nöbetçi koşusunun birebir neden dağılımı değildir.
- `advisor/service.py:323` bütün “VERİ BEKLENİYOR” kararlarını aynı kümeye atıyor;
  `advisor/watchdog.py:76` kümeyi veri doğrulama arızası yapıyor.
  `advisor/marketdata.py:178` aslında işlem maliyeti kapısını uyguluyor.
- Sabit üretim defteri/görünümü geçici dizine kopyalanarak nöbetçi ağsız
  yeniden çalıştırıldı; aynı tek `decision_data` bulgusu üretildi.

**Öneri:** Veri eksikliği, geçersiz/bayat kotasyon ve pahalı işlem koşulunu ayrı
sınıf kodlarına ayır; normal maliyet engelini CI arızası yapma. Telegram/panel
“makas nedeniyle yeni alım yok” desin. %3 eşiği ve mevcut koruyucu çıkış davranışı
korunsun. DoD: geniş makasta alım engelli ama veri alarmı yok; gerçek kaynak
yokluğunda alarm var; eski defter de güvenle okunuyor; iki depoda davranış testi geçiyor.

## 5. P2 — Gerçek fiyat kaynağı kesintileri ve yetersiz hata tanısı — DOĞRULANDI

- [30 Eylül BIST](https://github.com/Mertsaglm/bist-analiz/actions/runs/36716911044):
  ConnectionError. [23 Ekim BIST](https://github.com/Mertsaglm/bist-analiz/actions/runs/39916630808):
  ValueError. [22 Ekim altın](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/39763677006):
  ConnectionError. [16 Ekim altın](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/38897571078): ValueError.
- Ekim aktif defterinde BIST'in 581 session_check kaydından 22'sinde kaynak hatası
  var: 10 ValueError, 7 ConnectionError, 4 ReadTimeout, 1 ConnectTimeout.
  Altının 700 kaydından 14'ünde kaynak hatası var: 13 ValueError, 1 ConnectionError.
  Seans dışı atlamalar da bu paydalara dahildir; bunlar kaynak kullanılabilirlik oranı değildir.
- `advisor/marketdata.py:98` tek HTTP denemesi yapıyor;
  `advisor/service.py:219` istisnanın yalnız sınıfını saklıyor.
  Parser'ın hangi kontrolünün bozulduğu veya HTTP bağlamı kayboluyor.

**Bilinmeyen:** ValueError'ın sayfa biçimi, zaman damgası veya ürün doğrulaması
gibi hangi alt nedenden geldiği tarihsel loglardan belirlenemiyor. Kalıcı kaynak
engeli veya site değişikliği kesinleşmiş değil.

**Öneri:** Güvenli sınıf/HTTP durum/parser aşaması tanısı, yalnız geçici ağ hataları
için sınırlı retry/backoff; son başarısızlığı açıkça saklama. Eski fiyatla alım
veya doğrulanmamış alternatif kaynak eklenmesin. DoD: timeout sonrası toparlanma,
kalıcı erişim hatası ve HTML doğrulama hatası ayrı testlerle görünür; ağ izolasyonu korunur.

## 6. P2 — BIST kapanış telafisi geçmişte tekrar tekrar eksik kaldı — DOĞRULANDI

- [2 Ekim örneğinde](https://github.com/Mertsaglm/bist-analiz/actions/runs/36977652250)
  beklenen 1 Ekim kapanışında 73/73 hisse eksik. Logda 73 barın 30 Eylül sınırıyla
  ayıklandığı görülüyor. Yalnız kaynak bağlantısı hatası diyerek açıklanamaz.
- Ekim karar defterinde eksik kapanış nedenli 1248 karar kaydı var; 1, 6, 7, 8, 9,
  13 ve 19 Ekim kapanışları gerekçelerde geçiyor. Son üretim SQL kesitinde bunlar
  tamamlanmış; arızanın o tarihte yaşanmadığı anlamına gelmez.
- Konum: `scripts/refresh_market_history.py:57`, `src/prices.py:192`,
  `src/prices.py:141`, `src/calendar_bist.py:208`.

**Kök neden DOĞRULANMADI:** Beklenen gün ile ayıklama sınırının hangi çalışma
anında/neden ayrıştığı henüz kontrollü olarak yeniden üretilemedi. Aynı SQL'nin
eski yerel kopyasının daha önce tamamlanabilmesi üretim nedenini açıklamaz.

**Öneri:** İki takvimin beklenen kapanışını, kaynak bar tarihlerini ve ayıklama
sınırını aynı koşu kimliğinde kaydet; arıza kesitini geçici kopyada yeniden üret.
Kanıtlandıktan sonra ortak zaman/takvim kuralını düzelt. DoD: eksik önceki
kapanış toparlanır; açık seansın yarım barı sızmaz; endeks/hisse yolları birlikte sınanır.

## Geçmiş hata ile bugünkü açık ayrımı

- [1 Eylül eski BIST nöbetçisi](https://github.com/Mertsaglm/bist-analiz/actions/runs/33563886838)
  TR gece yarısını aşınca “2 Eylül koşusu yok” diyor. Bu eski yanlış alarm,
  L-026'da kayıtlı; güncel `src/otonom.py:639` kapanmış son seansı kullanıyor.
  Yerel davranış testleri geçti. Bugünkü ödeme engeli bu eski hatayla açıklanamaz.
- [19 Eylül altın testi](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/35438723675)
  hafta sonu beklenti bildirimi mock'unda 400 hatasıyla düşmüş. Ekim metadatasında
  altın test koşularının ikisi de başarılı. Eski test hatasının bugün sürdüğü kanıtlanmadı.
- İki üretim yapılandırmasında `experiment_start_date: null`; beş yeni deney kolu
  **başlamamış**. Ana sanal hesaplar çalışmış olsa da planlanan yeni sınavın
  ilerlediği veya başarı ürettiği söylenemez. Konum: `advisor/config.json:65`.

## 28 Ekim — Vercel kısıtlama kontrolü

- `https://birikim-paneli.vercel.app/` HTTP 200, parolasız `/api/status` HTTP 401
  ve `Panel parolası gerekli.` döndürdü. Bu 401 `dashboard/api/status.js:10`
  içindeki uygulama kimlik doğrulamasıyla eşleşir; kota ihlali kanıtı değildir.
- Vercel'de son üretim deployment'ı 23 Ekim 13:18 TR'de oluşmuş, **READY**;
  kaynak commit'i BIST'in son `117499f` commit'i. Listelenen son 100 deployment
  READY, ERROR filtreli sorgu boş. Bu, daha eski tüm yayınların ve gelecekteki
  kotanın sorunsuz olduğunu kanıtlamaz.
- Panel `dashboard/lib/status.mjs:68` üzerinden her iki reponun güncel görünümünü
  GitHub API'den okur. Dolayısıyla BIST veri üretiminin durması ile Vercel'in
  yayını sunması farklı olgulardır; eski deployment tarihi altın verisinin de
  aynı tarihte kaldığını kanıtlamaz.
- Safari paneli açtı ancak parola girilmediğinden yetkili veri görünümü sınanmadı.
  Vercel usage ve runtime log sorguları bu bağlantıya 403 verdi; Safari Vercel
  hesabı giriş ekranına yönlendirdi. Bu 403 inceleme yetkisiyle ilgilidir,
  yayının platformca kısıtlandığı anlamına gelmez. Hesap kotası ve logları
  DOĞRULANMADI; Vercel kullanım sınırına ulaştı iddiası kurulmamalı.

## Önerilen uygulama sırası — henüz onaylanmadı

1. **İşletim engeli:** BIST Billing nedenini kesinleştir; bütçe/çalıştırma seçeneğini
   seç. Harici yedekleri koruyup kota planını belirle. Ödeme, silme, görünürlük
   veya üretim değişikliği ayrıca açık onaya bağlıdır.
2. **Yerel kod paketi:** İki depoda makas/veri sınıfları; güvenli kaynak tanısı ve
   sınırlı retry; bozuk OHLC giriş koruması; kapanış telafisi için yeniden üretim.
   Her değişiklik tetikleyici durumu kapsayan davranış testiyle doğrulansın.
3. **Kontrollü veri onarımı ve yayın:** Doğru TMSN barı doğrulandıktan sonra ayrı
   makbuzla onar; onaylı kodu yayınla. Kod yayını veri onarımını gizlice içermesin.
4. **Üretim kabulü:** Atlanmamış taze çevrim, eski defter/hash/nakit eşliği,
   gerçek Telegram makbuzu, bağımsız yedekten geri dönüş. Sonra ortak ileri T0'ı
   ayrı kararla aç; deneyleri geriye dönük başlamış gibi göstermeyelim.

## Kanıt ve doğrulama sınırı

Kanıt özeti ve yeniden çalıştırılabilir inceleme:
`reports/actions-2026-10-28/evidence.json`, `reports/actions-2026-10-28/verify.py`.
Üretim kaynakları sabit commitlerden okundu; incelenen 18 kod/config/workflow
dosyasının yerel kopyalarıyla eşliği doğrulandı. Veri dosyaları güncel yerel
üretim kopyası olarak kabul edilmedi.

14 mevcut davranış testi geçti: eski nöbetçinin seans mantığı, gözlemcinin
yazmaması/kaçırılan çevrimi görmesi, yedek geri dönüşü, geniş makasta alım
engeli ve koruyucu çıkış, tam eşikte makas aritmetiği. Bu sonuç yeni bir
düzeltmenin uygulandığı veya üretimin sağlıklı olduğu anlamına gelmez.
Tam suite yeniden koşturulmadı. Üretimdeki son gerçek suite sonucu ayrıca yukarıda.
Rapor/hafıza güncellemesi sonrası doküman kontrolleri: BIST 41, altın 43 geçti.
Parolalı panel, alıcı cihazında Telegram teslimi ve yatırım performansı bu denetimde sınanmadı.
