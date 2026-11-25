# Mevcut durum

**Güncelleme:** 2026-10-29
**Aktif iş:** Kodlar iki uzak main'e yayımlandı; Gold CI ve gerçek operasyon
  yedeği/geri dönüşü geçti, Vercel production READY. Mert iki somut iş için
  “sen tercih et” yetkisi verdi: TMSN tek bar onarımı üretime uygulandı;
  12 eski BIST artifact silindi, son bulut yedeği ve 13 yerel kopya korundu.
  BIST runner öncesi ödeme/harcama engeli sürüyor. Ücretli servis/limit açılmadı.
  Piyasa açık taze çevrim kabulü ve ortak deney T0 henüz yok.

## Tamamlananlar

- 2026-10-29 eski girdisiz dispatch gerçek GitHub koşusunda runner almadan
  atlandı (40899224420); fiyat/defter adımı çalışmadı, makbuz raporda.

- 2026-10-29: TMSN kaynakla doğrulanan düşük fiyatı 50,00'a onarıldı
  (`4101882`); tek SQL satırı/düşük+ingestion değişti, dört mevcut
  OHLC testi geçti ve uzak blob test edilen SQL ile eşleşti. Eski karar/defter aynı.
  12 eski artifact 933.906.756 byte temizlendi; 336.038.973 byte son bulut yedeği
  ve 13 doğrulanmış yerel kopya korundu. Somut iki soruya “sen tercih et” yetkisi.

- 2026-10-29 yayın: `8d91c6f`; BIST runner öncesi engel; Vercel READY.
  `reports/duzeltmeler-2026-10-29/publication.json` güncel makbuzdur.
  Yerel kirli çalışma ağacı/branch reset veya rebase edilmedi; önceden değişmiş
  belgeler yayına katılmadı. Sonraki yayında eski yerel SQL kullanılmamalı.

- 2026-10-29: makas/veri ayrımı, güvenli kaynak tanısı/sınırlı retry, ortak parçalı
  v2 kapsül ve kapsamı etiketli operasyon yedeği iki depoda yerel olarak tamamlandı.
  BIST saatlik ve eski girdisiz dış dispatch kapalı; V1 LLM kapalı, veri nöbeti açık.
  BIST OHLC ve V1/V2 yarım gün kapanış simetrisi düzeltildi. Gold ritmi korunur.
  %3 eşik, stop, eski defter/kanıt ve üretim SQL'si korunur. Ayrıntı/kanıt sınırları:
  `docs/DUZELTMELER-2026-10-29.md`; ADR #035.

- Önceki deney/AI talimat işleri ve tarihli ölçümler yayın sonrası arşivde korunur.
- İki suite'te HTTP/curl ağ yasağı zorlandı; sızıntıyı örten eksik mock'lar düzeltildi.

## Kanıt ve dürüst durum

- 2026-10-29 Gold gerçek operasyon yedeği 2.207.264 byte; GitHub ve yerel
  boş dizin geri dönüşü geçti. Kapsül geçmişi kapsam dışı, Git'te korunur.

- 2026-10-29: BIST tam suite 1503; Gold tam suite 1026 geçti/9 atlandı. Son hata
  yedeği/workflow/doküman hedef kümeleri BIST 55, Gold 56 geçti; makbuzlar raporda.
  37 ortak modül eşit. Sabit gerçek girdide BIST 33 karar değişmedi; Gold yalnız
  makas sınıfı değişti; iki tarafta yeni dolum 0. Canlı kabul değildir.
- 13 artifact yerelde digest/CRC ile korundu; önceki denetimde asıllar duruyordu,
  2026-10-29 onaylı temizlik sonrası bulutta yalnız son başarılı yedek kaldı.
  2 Ekim son başarılı harici yedeği 1130 dosya ve muhasebe eşliğiyle geri döndü.

- 2026-10-28 denetimi/mailler ücretsiz dakika ve artifact kotası doluluğunu
  doğruladı; ayrıntı `docs/HATA-DENETIMI-2026-10-28.md` ve önceki durum arşivinde.
- Yarım gün hatası tekrarlandı; erken Ekim telafi kayıplarının tüm kök nedeni
  hâlâ doğrulanmadı. Bu açık çözülmüş kabul edilmez.
  Aşağıdaki eski ölçümler tarihlidir.
- Eski 73/73 kapanış kaybı, önceki canlı yayın ve arşiv provaları
  `ai/archive/STATE-2026-10-28-before-free-repairs.md` içinde korunur.
  Yeni yarım gün düzeltmesi o tarihsel kayıpların tamamının kanıtı değildir.

## Sıradaki 3 İş

1. GitHub ücretsiz hak/ödeme engeli kalkınca BIST'in gerçek taze çevrimini kabul et.
   DoD: runner başlamış, beklenen kapanış/evren tamam, eski defter eş ve Telegram
   makbuzu var. Temizlik dakika iade etmez; ücret/harcama limiti artırılmaz.
2. Yeni BIST operasyon yedeğini gerçek runner'da oluşturup geri dönüşünü doğrula.
   DoD: kapsam etiketli küçük artifact, muhasebe eşliği ve ücretsiz bütçe ölçümü;
   mevcut 336 MB bulut yedeği kabul kanıtı çıkmadan ayrıca silinmez.
3. Piyasa açık yeni kodla iki piyasa kabulünden sonra ortak ileri T0'ı ayrı değerlendir.
   DoD: taze veri ve bağımsız hesap/masraf eşliği; otomatik T0/aday terfisi yok.

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

Önceki durumun tam kesiti: `ai/archive/STATE-2026-10-28-before-free-repairs.md`.

Yayın sonrası tam kesit: `ai/archive/STATE-2026-10-29-after-publication.md`.
