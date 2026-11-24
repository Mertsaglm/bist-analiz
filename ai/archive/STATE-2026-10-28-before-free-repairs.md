# Mevcut durum

**Güncelleme:** 2026-10-28
**Aktif iş:** Tekrarlayan Actions/mail hataları salt-okunur incelendi;
rapor hazır, düzeltmeler kullanıcı onayını bekliyor. BIST ödeme/harcama engeliyle
çalışmıyor; son V2 çevrim 2026-10-23 13:17 TR. Altın çalışıyor; geniş makas
veri arızası diye sınıflanıyor. Ortak deney T0 hâlâ kapalı; BIMAS geçmiş düzeltmesi ayrı.

## Tamamlananlar

- 2026-10-02 AI talimatlarındaki genel yönlendirmeler ve tekrarlar ayıklandı;
  arşive konuya göre başvurma kuralı ortak talimatla eşitlendi. Kritik denetim,
  izolasyon ve proje sınırları korundu; 41 doküman testi geçti. Oturum başlangıcıyla
  dosya eşliği kod/veri/ön kayıt/derslerin korunmasını doğruladı. Ayrıntı ADR #034.
- 2026-10-01 AI talimatları sadeleştirildi; köprü öncelikleri tekleştirildi,
  V1 kapsamı arşive taşındı. Doküman testleri ve kapsam kontrolü geçti;
  kod/veri değişmedi. Ayrıntı ADR #034.
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

- Altın ortak çekirdekle eşitlendi; bekleyen yeni hesabı gerçek arşiv kopyasında sınandı.
- İki suite'te HTTP/curl ağ yasağı zorlandı; sızıntıyı örten eksik mock'lar düzeltildi.

## Kanıt ve dürüst durum

- 2026-10-28 denetimi: 2833 koşu metadatası, seçili loglar ve üretim arşivleri
  incelendi. BIST yedek artifact kotası, TMSN 2026-10-22 OHLC ihlali, iki piyasada
  kaynak kesintileri ve altın makas/veri alarmı ayrıştı. 14 mevcut davranış testi
  geçti; bu üretim sağlığı değildir. Kod/veri/ödeme değişmedi. Ayrıntı ve DoD:
  `docs/HATA-DENETIMI-2026-10-28.md`, `reports/actions-2026-10-28/evidence.json`.
- 2026-10-28 ek inceleme: GitHub maili 23 Ekim'de 2.000 ücretsiz Actions dakikasının,
  5 Ekim'de 0,5 GB depolamanın %100'üne ulaşıldığını doğruladı. Ödeme/bütçe ayrıntısı
  yetki nedeniyle bilinmiyor. Vercel son yayın READY ve ana sayfa 200; kullanım/log
  yetkisi ve parolalı panel sınanamadı, Vercel kotası iddia edilemez. Ayrıntı raporda.
- Kapanış telafisi kök nedeni yeniden üretilmedi. Bu açık çözülmüş kabul edilmez.
  Aşağıdaki eski ölçümler tarihlidir.
- 2026-10-02 11:43 TR incelemesi: üretimde 73/73 hisse kapanışı eksik,
  33/33 karar `VERİ BEKLENİYOR`; #328 yeşil koşu atlanmıştı. Aynı kodla
  üretim SQL'inin geçici kopyası 73/73 kapanışı tamamladı; üretim toparlanması
  ve kök neden henüz doğrulanmadı. `reports/actions-2026-10-02/README.md`.
- Denetim: `docs/URETIM-DENETIM-2026-09-30.md`.
- Düzeltme: `docs/DUZELTMELER-2026-09-30.md`.
- Makbuzlar: `reports/duzeltmeler-2026-09-30/README.md`.
- Önceki ölçümler ve yayın öncesi kanıt: `ai/archive/STATE-2026-10-01-evidence.md`.
- 2026-10-01 üretim Telegram defterinde BIST için 32, altın için 33 başarılı bildirim
  makbuzu var. Vercel paneli HTTP 200, yetkisiz durum API'si HTTP 401 verdi;
  parolalı veri görünümü henüz sınanmadı.
- Eski veri sınavı 2026-10-01'de yeniden koştu: altın raporu birebir aynı;
  BIST'e sonradan eklenen dört test satırı ayrı makbuzda saklandı.
- Yayın sonrası [BIST koşusu](https://github.com/Mertsaglm/bist-analiz/actions/runs/36901914212)
  başarılı fakat seans dışı atlandı. [Altın koşusu](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/36901918911)
  başarılı; Telegram `message_id: 320`. Vercel'in üç statik dosyası yeni sürümle eş.

## Sıradaki 3 İş

1. Denetim raporundaki çözüm kapsamını ve BIST Billing/yedek seçeneğini Mert'le kesinleştir.
   DoD: kod, veri onarımı, saklama ve olası maliyet için açık yetki sınırları belli.
2. Onaylanan makas/veri, kaynak tanısı, OHLC ve kapanış telafisi işlerini uygula.
   DoD: tetikleyici davranış testleri; doğrulanmış veri onarımı; kalite/risk kapıları korunur.
3. Onaylı yayından sonra gerçek taze çevrim, Telegram ve harici yedek geri dönüşünü doğrula.
   DoD: atlanmamış üretim çevrimi ve defter eşliği; sonra ayrı kararla ortak ileri T0 ve panel.

## Takvim

| Tarih | İş | Durum |
|---|---|---|
| 2026-09-25 | BIST revizyonunun yayınlanması | Önceki konuşma ve üretimle doğrulandı |
| 2026-09-30 | Üretim denetimi ve yerel düzeltmeler | Tamam; kod 2026-10-01 yayımlandı, BIMAS veri düzeltmesi ayrı |
| 2026-10-01 | Kod yayını ve ilk canlı çevrim | Altın katkı/Telegram geçti; BIST seans dışı atlandı, T0 kapalı |

## Backlog / açık sınırlar

- D-01 BIMAS geçmiş karne düzeltmesi üretime uygulanmadı; altın yeni ana hesap
  2026-10-01'de açıldı. İki yeni deneyin ortak T0 kapısı kapalıdır.
- Yerel SQL ve tarihli kopya provaları canlı fiyat/defter eşliği sayılmaz;
  ilk seans içi yeni kod koşusunda tekrar doğrulanmalıdır.
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
