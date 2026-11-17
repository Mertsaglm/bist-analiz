# Mevcut durum

**Güncelleme:** 2026-10-01
**Aktif iş:** İki piyasada yeni kod 2026-10-01'de `main` dalına yayımlandı.
Altın canlı çevrimi ve Telegram teslim makbuzu geçti; BIST ilk yeni koşusu
seans dışı olduğu için atlandı. Ortak deney T0 kapalı (`experiment_start_date: null`);
yeni beş aday hesap henüz canlı işlemedi. BIMAS geçmiş karne düzeltmesi ayrı.

## Tamamlananlar

- Beş ayrı yeni sanal kol, çekirdek/taktik bölüm muhasebesi, kısmi işlem,
  tek saklama ücreti, tarihli BIST30/GRAM çekirdeği ve haftalık taktik kuruldu.
- Sayısal karar izi, ham/kalibre tahmin kimliği, hedef portföy, filtre etkileşimi
  ve ileri ilk görülme haber damgası panel ile birlikte eklendi.
- BIST göreli Ridge ve altın ons/kur Ridge ayrı aday; LightGBM yalnız offline.
  Son offline pencerede yeni modeller lehine üstünlük bulunmadı.
- Eski yerel SQL kopyalarında iki kotasyonlu çevrim, altışar bağımsız defter,
  tekrar ve yedek geçti. BIST 2026-09-24, altın 2026-09-22 kaynaklıydı;
  eksikler deney raporunda, ortak ileri T0 için taze veri kanıtı yok.
- Eksik BIST30 üyeliği ve engelli haftalık satış kilitlendi; yarım kuruşluk
  taktik tutar hatası Decimal ile düzeltildi. Geçmiş/kapalı T0 reddedilir.
- Yeni rapor: `docs/PORTFOY-DENEYI-2026-10-01.md` ve oradaki tarihli makbuzlar.

- Önceki üretim düzeltmeleri: `ai/archive/STATE-2026-10-01-evidence.md`.
- Altın ortak çekirdekle eşitlendi; bekleyen yeni hesabı gerçek arşiv kopyasında sınandı.
- İki suite'te HTTP/curl ağ yasağı zorlandı; sızıntıyı örten eksik mock'lar düzeltildi.

## Kanıt ve dürüst durum

- Denetim: `docs/URETIM-DENETIM-2026-09-30.md`.
- Düzeltme: `docs/DUZELTMELER-2026-09-30.md`.
- Makbuzlar: `reports/duzeltmeler-2026-09-30/README.md`.
- 2026-09-30: BIST 1459 geçti; altın 998 geçti/8 atlandı; iki panelde 10'ar test geçti.
- Altı eski-hata geri koyma denemesi kırmızı; 33 ortak modül hash'i eşit.
- Gerçek 73 hisse kurumsal kaynağı başarılı; 18 eksik olay ve 47 sonuç incelendi.
- Mühürlü plan yalnız BIMAS yanlış başarısını iptal eder; TAVHL geçerli kaybı korunur.
- Plan DB kopyasında uygulandı/tekrarlandı; salt-okur üretim kopyasının hash'i aynı.
- Kapanış telafisi kopyada 73 eksiği tamamladı; 32 veri engeli 1 SASA engeline indi.
- BIST/altın tekrar çevrimleri, kapsül, model refit, muhasebe ve yedekten dönüş geçti.
- API telafisi sonradan alındı; eski saatte erişilebilirlik ve canlı başarı iddiası yok.
- Model üstünlüğü/otomatik terfi yok; nakitte kalmak tek başına başarı değildir.
- 2026-10-01 son paket: BIST 1478, altın 1016 geçti/9 atlandı; paneller 12'şer
  test/build geçti. Son finansal düzeltmenin hedefli testi ve arşiv kopyası
  provaları tekrar geçti; altışar defter bağımsız muhasebeyle uyuştu.
- Güncel üretim SQL'leriyle de beşer aday/altışar defter provası geçti;
  TOASO karşılaştırma yarım kuruşu düzeltilip davranış testine bağlandı.
- Uzak altın ana durumunda 14:33 UTC'de 10.000 TL katkı/sıfır işlem; 07:02–14:46
  UTC arasında 33 kayıt, en büyük boşluk 15,3 dk. Özel BIST Safari'de okundu:
  14:46:54 UTC koşusu başarılı, 29 görünür çıktı 08:02–14:47 UTC; en büyük
  boşluk 17 dk. İki uzak SQL salt-okunur geçici kopyada incelendi: BIST30'un
  30/30 barı 2026-09-30'da var; altın tarih/banka tick'i 2026-09-30, ons/kur
  OHLC 2026-09-29. Actions manuel dispatch + planlı yedek gösterir; dış
  dispatch kimliği kanıtlanmadı. SHA ve ayrıntı deney belgesinde.
- Güncel BIST ana hesap defterinde 7.124, altın defterinde 1.863 olayın hash
  zinciri ve dörder hesabın bağımsız muhasebesi doğrulandı. BIST ana hesap
  55.000 TL, altın ana hesap 10.000 TL nakitte; ikisinde de ana işlem yok.
- Üretim Telegram defterinde BIST için 32, altın için 33 başarılı bildirim
  makbuzu var. Vercel paneli HTTP 200, yetkisiz durum API'si HTTP 401 verdi;
  parolalı veri görünümü henüz sınanmadı.
- Eski veri sınavı 2026-10-01'de yeniden koştu: altın raporu birebir aynı;
  BIST'e sonradan eklenen dört test satırı ayrı makbuzda saklandı.
- Yayın sonrası [BIST koşusu](https://github.com/Mertsaglm/bist-analiz/actions/runs/36901914212)
  başarılı fakat seans dışı atlandı. [Altın koşusu](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/36901918911)
  başarılı; Telegram `message_id: 320`. Vercel'in üç statik dosyası yeni sürümle eş.

## Sıradaki 3 İş

1. 2026-10-02 seansında BIST ve altının yeni kodla taze çevrimlerini,
   Telegram makbuzunu ve 2026-10-01 kapanış verisini doğrula.
   DoD: iki piyasada geçerli veri, atlanmamış çevrim ve eski defter eşliği.
2. Koşullar geçince ortak gelecek işlem günü T0'ı iki ayarda sabitle.
   DoD: BIST30 30/30 fiyat, GRAM ve beş ayrı hesap ilk çevrimde mutabık.
3. Parolalı Vercel görünümünü ve 20/63/126 seans değerlendirmesini izle.
   DoD: panel iki yeni hesabı gösterir; sonuçlar pasif kolla maliyet sonrası kıyaslanır.

## Takvim

| Tarih | İş | Durum |
|---|---|---|
| 2026-09-25 | BIST revizyonunun yayınlanması | Önceki konuşma ve üretimle doğrulandı |
| 2026-09-30 | Üretim denetimi ve yerel düzeltmeler | Tamam; yeni yayın bekliyor |
| 2026-10-01 | Katkı, üyelik ve çeyrek ücret geçişi | Kopyada sınandı; canlı koşu doğrulanmadı |

## Backlog / açık sınırlar

- D-01 geçmiş karne planı ve D-03 altın yeni hesap aktivasyonu üretime uygulanmadı.
- GitHub CLI kimliği geçersiz; iki üretim SQL'i Safari'den alınıp geçici DB'de
  incelendi. İki güncel olay defteri de geçici kopyada mutabık; yerel SQL'ler canlı eşlik değil.
- D-05 dış scheduler ve Telegram alıcı teslim/okunması bağımsız doğrulanmadı.
- SASA 29 Eylül barı sıfır hacimli; 30 Eylül kapanışında analiz sorunu yok.
  Eski sıfır hacim kayıtları için doğrulanmış kaynak gerekiyor.
- EREGL 2008 temettü kaynak revizyonu ve eski tutar farkları makbuzda; plana zorla yazılmaz.
- Arşiv büyümesi: kanıtı silmeden saklama politikası ve kuyruk gecikmesi takibi.
- Yeni 5/20 seans sonuçları olgunlaşınca aynı maliyetli kıyas; erken terfi yok.
- Tarihsel banka kotasyonu/emir sırası, kişisel tarife/MKK ve temettü ödeme günü.
- Geçmiş üyelik/fiyat sürümü ve revizyon geçmişli TÜFE sınırları sürüyor.
- 2027 tahmini takvim kayıtları resmi kaynakla doğrulanacak.
- 2026-11-25: altın GC=F roll, bağımsız prim/FRED kapsamı incelemesi.
- V1 ön kayıt: `docs/on-kayit-seviye-02.md`; tetikleyici olmadan çalıştırılmaz.
- Önceki hafıza: `ai/archive/STATE-2026-09-30-production-audit-open.md`.
