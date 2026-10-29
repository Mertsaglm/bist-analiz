# Sıfır ek ödeme ile hata düzeltmeleri — 2026-10-29

**2026-10-29 üretim veri onarımı eki:** Mert, ayrıntısı sunulan bu onarım için
“sen tercih et” yanıtıyla karar yetkisi verdi. TMSN 2026-10-22 düşük fiyatı,
aynı Yahoo kaynağının güncel cevabıyla 50,0999984741 → 50,00 olarak doğrulandı.
Yalnız bu barın düşük fiyatı ve ingestion zamanı onarılır; SQL'nin diğer
satırları, eski kararlar ve işlem defterleri korunur. Düzeltilmiş RAM kopyasında
dört mevcut OHLC veri testi geçti. Kaynak ayrıca hacimde 18 lot revizyon veriyor;
bu ayrı fark burada uygulanmadı, normal veri yenilemesine bırakıldı.
Önbellekteki göstergeler veya dondurulmuş kararlar geriye dönük yazılmadı;
sonraki normal veri hattı göstergeleri yeniden hesaplar. Aşağıdaki eski TMSN
başarısızlığı yayın öncesi kesittir. Kaynak ve doğrulanmış plan:
`reports/duzeltmeler-2026-10-29/tmsn-repair-plan.json`.


Bu dosya yayın öncesi doğrulama kesitidir. Mert 2026-10-29 tarihinde
commit/push ve gerekli güvenli işlemleri yetkilendirdi. Canlı çalışmanın kabulü
GitHub kota ve gerçek veri kontrollerine bağlıdır. Üretim SQL'si,
defterler, geçmiş kapsüller, hesap bütçeleri ve deney T0 değiştirilmedi.
Kullanıcı ek ödeme yapamayacağını belirtti. Harcama/plan ayarı değiştirilmedi;
özel depo açılmadı ve yeni servis alınmadı.

## Kanıtlanan nedenler ve yapılan değişiklik

| Sorun | Yerel çözüm | Sınır |
|---|---|---|
| GitHub ücretsiz 2.000 dakika ve 0,5 GB artifact hakkı tükendi | BIST saatlik 10:17–19:17 TR; eski girdisiz dış dispatch runner almadan elenir. Gözcü günde iki kez, test takvimi hafta içi | Dolmuş hakkı geri getirmez. Sonraki dönem yeterliliği gerçek dakika ölçümüyle izlenecek |
| Aynı defter/kod her kapsülde, bütün kapsüller her yedekte tekrarlanıyor | Yeni v2 kapsül 256 olaylık mühürlü ortak parçalar/kod kullanır; eski v1 replay korunur. Operasyon yedeği Pzt/Çrş/Cuma, 3 gün saklama. Hata artifact'i bütün muhasebe/model dosyalarını korur, kapsülleri dışarıda tutar | Tam replay geçmişi Git'tedir; operasyon yedeği kapsülleri kapsamaz. Varsayılan tam yerel yedek seçeneği sürer |
| Geçerli GRAM kotasyonunda %14,00656 makas veri arızası sayılıyor | Ayrı BEKLE/spread_limit ve makas kontrolü; veri alarmı yalnız gerçek veri sorununa ayrılır | %3 alım eşiği değişmedi. Mevcut stop çıkışı çalışır |
| Kaynak hatası yalnız Exception adı veriyor | Güvenli HTTP/parser aşaması, status ve en fazla 3 geçici GET denemesi | Kalıcı 4xx tekrarlanmaz; kaynak erişimi veya veri tazeliği garanti edilemez |
| Geçersiz OHLC geçerli eski barı ezebiliyor | Hisse/endeks batch'i yazılmadan finite/pozitif ve düşük–açılış/kapanış–yüksek sınırları doğrulanır. Hatalı sembol diğerlerinin yenilenmesini durdurmaz; telafi geçerli alt kümeyi saklar ve hata tanısıyla başarısız döner | TMSN 22 Ekim geçmiş satırı doğrulanmış yeni kaynak olmadan düzeltilmedi |
| V1 ve V2 yarım gün kapanışı farklı | V1 de yarım gün 12:40 kapanışını kullanır; hisse/endeks temizliği aynı saatle çalışır. Telafi raporu iki cutoff'u kaydeder | Tetikleyici tekrarlandı; erken Ekim kapanış kayıplarının tamamının sebebi olduğu DOĞRULANMADI |
| Ücretli V1 LLM çağrı ihtimali ve kapatınca yanlış nöbetçi alarmı | Günlük workflow daima --analistsiz; ücretli API anahtarları o adıma aktarılmaz. Nöbetçi aynı modda bütün canlı evrenin takvim kapanışını izler | V1 yeni LLM tahmini üretmez; deterministik veri/rapor ve V2 sürer. Diğer eski araştırma komutları otomatik etkinleştirilmedi |
| Her veri commit'inde panel build'i | Vercel ignoreCommand yalnız dashboard değişince build ister | İptal edilen build deployment kotasına yine sayılır; bunu kotayı kaldırmış saymıyoruz |

Saatlik gözlem, sanal stop kontrolünü de seyrekleştirir. Cron kesin zaman veya
kesintisiz fiyat akışı değildir. Bu paket gerçek emir iletmez.

## Gerçek üretim girdisinin geçici kopyasında ölçüm

Makbuz: `reports/duzeltmeler-2026-10-29/measurements.json`.

- Sabitlenmiş son v1 kapsülleri arşivlenmiş kendi koduyla ağsız tekrarlandı:
  BIST 33, altın 1 karar aynı. Girdi dosyalarının SHA256'sı değişmedi.
- Yeni kod aynı BIST girdisinde 33 kararın eylem/kodunu değiştirmedi; yeni dolum 0.
  Altında yalnız GRAM veri bekliyor/data_block → BEKLE/spread_limit oldu; yeni dolum 0.
- Aynı gerçek defter önekli beş kapsül: BIST 33.791.826 → 6.997.193 byte,
  altın 3.188.194 → 700.672 byte. Yaklaşık %79 ve %78 azalma; tüm geçmişin
  veya gelecekteki büyümenin ölçümü değildir.
- Gerçek sabit SQL ve aktif/eski defterin geçici örneğinde operasyon yedeği
  15.802.901 byte, 48 dosya; geri dönüş ve muhasebe eşliği geçti. Örnek üretimdeki
  bütün aday/model dosyalarını kapsamadığından tam güncel üretim yedek boyutu değildir.
- Tutulan 13 GitHub artifact'inin 1.269.945.729 byte'ı yerelde saklandı.
  Her kopya GitHub digest'i ve dış ZIP CRC ile doğrulandı; silinen artifact 0.
  `reports/duzeltmeler-2026-10-29/preservation.json` makbuzdur.
- Son başarılı orijinal harici yedek ayrıca boş geçici dizine geri döndü:
  1.130 dosyanın manifest hash'i, bütün defterler ve dört ana muhasebe hesabı geçti.
  Bu **2 Ekim tarihli yedeğin** kanıtıdır; 23 Ekim güncelliği anlamına gelmez.
  `reports/duzeltmeler-2026-10-29/latest-recovery-drill.json`.

Yerel kopyalar `data/backup/actions-2026-10-28/` içindedir ve gitignore kapsamındadır.
Bu tek Mac kopyası bağımsız uzak arşiv yerine geçmez; buluttaki asıllar korunuyor.

## Test ve üretim kabulü

Güncel test sonuçları `reports/duzeltmeler-2026-10-29/validation.json` içindedir.
Davranış testleri makas/veri ayrımını, stop'u, retry sınırını, eski/yeni replay'i,
ortak parça bozulmasını, yedek kapsamını, OHLC'nin eski veriyi ezmemesini,
yarım günün iki veri yolunu ve kapalı LLM nöbetinin eksik evren alarmını sınar.
Ağ/gerçek veri yazma korumaları gevşetilmedi. İki depoda 37 ortak motor modülü eşittir.
Yerel suite eski yerel DB'yi okur: sabit 23 Ekim üretim SQL'sinin RAM kopyasında
mevcut `TestGercekVerideOhlc` testi TMSN nedeniyle hâlâ başarısızdır.
`reports/duzeltmeler-2026-10-29/production-data-test.json` bunu kaydeder.
Bu satır kaynaktan doğrulanarak onarılmadan üretim CI'ının tamamının yeşil
olacağı iddia edilemez; test veya eşik gevşetilmedi.

## Açık kalanlar ve yayın planı

1. Yerel kod GitHub'da yayımlanmadan üretimde düzelmiş sayılmaz. Ayrı temiz güncel
   checkout'a yalnız incelenen kod/test/doküman yaması uygulanacak; bu eski yerel
   checkout'tan SQL veya defter push edilmeyecek. Önceden değişmiş kullanıcı
   dokümanları bu yayın paketine topluca eklenmeyecek.
2. GitHub ödeme/harcama engeli sürüyor. Kod bunu aşmaz; kota yenilenmesi veya
   yetkili hesap ekranında ücretsiz hakkın açıldığının doğrulanması gerekir.
   Yedek silme daha önce kullanılmış dakikaları geri getirmez. Ücretli bypass yok.
3. Eski artifact'ler ancak ayrı açık silme onayı ve kopya makbuzlarıyla temizlenebilir.
   Mevcut 13 asıl silinmedi; saklama politikasının geçmişe uygulanacağı varsayılmaz.
4. TMSN 2026-10-22 ve BIMAS eski karne veri onarımları ayrı doğrulanmış plan gerektirir.
   Ortak ileri deney T0 hâlâ null; tarih/bütçe uydurulmadı.
5. Yayın sonrası atlanmamış taze gerçek çevrim, doğru seans/evren, defter eşliği,
   Telegram makbuzu ve yeni operasyon yedeğinin geri dönüşü doğrulanacak.
6. Vercel son yayın READY ve ana sayfa 200 idi; kullanım/log yetkisi ve parolalı
   panel kabulü yok. Vercel kısıtlamasının esas arıza olduğuna kanıt bulunmadı;
   bu, bütün kullanım limitlerinin kontrol edildiği anlamına gelmez.

## Son depolama envanteri ve kaynak

2026-10-29 salt-okunur ek envanter: Gold'da 45 artifact, toplam
10.742.396.316 byte; en yeni tek ZIP 672.227.048 byte. Bunlar BIST'teki korunmuş
13 artifact'ten ayrıdır; Gold'un 45 dosyası bu çalışmada yerelde kopyalanmadı
ve iki depoda da buluttan silme yapılmadı. Eski artifact'lerin retention'ı
yeni workflow ayarıyla geriye dönük kısalmaz. Mevcut büyümeyi düzeltmek gelecekteki
yedekleri küçültür; geçmiş depolama birikimini kendiliğinden kaldırmaz.

[GitHub resmi faturalandırma belgesi](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
public standart runner ile private ücretsiz kota ayrımını ve dönemlik dakika /
saatlik biriken depolama hesabını açıklar. Bu hesaptaki gerçekleşmiş
fatura/harcama limiti yetkili Billing ekranı olmadan doğrulanmadı.
2.000 dakika ve 0,5 GB değerleri 2026 Ekim uyarı maillerinin tarihli kanıtıdır;
gelecekteki plan/kota veya sıfır fatura garantisi olarak kullanılmaz.
