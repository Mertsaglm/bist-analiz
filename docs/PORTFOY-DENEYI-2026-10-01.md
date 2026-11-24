# Çekirdek/taktik sanal sınavı — 2026-10-01

Bu paket ana BIST/altın hesaplarının kararını değiştirmez. Ayrı defterlerde aynı
başlangıç ve katkılarla beş kol açar: mevcut politika, %80 çekirdek + %20 nakit,
çekirdek + pasif kalan dilim, çekirdek + mevcut Ridge ve çekirdek + piyasaya özel
Ridge. `advisor/config.json` içindeki `experiment_start_date` iki repoda da
`null` olduğu için **ileri T0 başlamamıştır**. Kod 2026-10-01'de iki `main`
dalına yayımlandı; beş deney hesabının canlı çalışması ayrı bir sonraki adımdır.
BIST ile altın arasında para aktarılmaz.

## Uygulanan sözleşme

- Her yeni kol 50.000 TL başlangıç ve aylık 5.000 TL alır. Çekirdek/taktik
  hesaplar 80/20 ayrı defter bölümleridir; tek BIST saklama ücreti ikiye katlanmaz.
- BIST çekirdeği o gün bilinen 30 üyeyi eşit ağırlık hedefiyle alır; CCOLA/CIMSA
  yalnız taktik havuzundadır. 2026-10-01 DSTKF çıkışı/TRMET girişi tarihli
  üyelikten okunur. Endeks çıkışı ilk uygun sanal kotasyonda izlenir.
- Altın çekirdeği İş Bankası GRAM kotasyonunda düzenli alım yapar. Çekirdek
  model onayı, RSI veya tahmini R:R beklemez; kalite, kotasyon ve bütçe ister.
- Taktik BIST haftalık sıralama, ilk beş giriş/ilk on koruma, isim başına %4
  değer ve %0,2 stop zararı, toplam %20 taktik değer ve beş pozisyon sınırı
  uygular. Aynı sektörden ikiden çok yeni isim açılmaz. Altın taktik bütçesi
  %20, stop zararı %1 ile sınırlıdır. Masraf sonrası giriş eşiği %1'dir.
- Stop ve üyelik çıkışı haftalık yeniden seçim dışında da izlenir. Geçerli
  kotasyon, sonraki fiyat ve aynı kotasyonun tek dolumu zorlanır. Stop fiyat
  boşluğu gerçek gözlenen kotasyondan yürür; geçmiş sentetik gram serisinden
  gün içi dolum türetilmez. Çekirdek piyasa riski stop riskinden ayrı açıklanır.
- Karar izi sayısal kapıları, ham/kalibre tahmini, model/özellik kimliğini,
  hedef portföyü ve son belirleyici kodu saklar. KAP/makro haberinin yayın ve
  **ilk yerel görülme** zamanı ayrı tutulur; ilk görülme eski tarihe yazılmaz.

## Tekrar üretilebilir kontroller

```bash
.venv/bin/python -m pytest -q
npm test --prefix dashboard
npm run build --prefix dashboard
.venv/bin/python scripts/advisor_manifest.py --peer ../gold_tracking_system
.venv/bin/python scripts/portfolio_preflight.py
.venv/bin/python scripts/portfolio_smoke.py
.venv/bin/python scripts/portfolio_research.py --market bist
```

Altın deposunda son komut `--market gold` ile çalıştırılır. Model sınavı yalnız
offline'dır; BIST'te LightGBM için `requirements-research.txt` gerekir.
LightGBM canlı sanal adayın işlem kararına bağlanmaz. Araştırma raporu her sabit
adayı, başarısız bölmeyi, etiket/test tarihlerini ve deneme sınırını saklar.
Üretim SQL kopyasıyla yeniden prova için `portfolio_smoke.py` komutuna
`--archive` ile indirilen dosya, `--output` ile ayrı makbuz yolu verilir;
komut kaynak arşive veya üretim defterine yazmaz. Makbuzdaki
`source_archive_sha256`, aşağıdaki indirme hash'iyle eşleşmelidir.

Tarihli makbuzlar:

- BIST: `reports/portfolio-smoke-bist-2026-09-24.json`,
  `reports/portfolio-model-research-bist-2026-09-24.json` ve aynı kodun
  güncellenmiş yerel SQL ile 2026-10-01 yeniden çalıştırma makbuzu
  `reports/portfolio-model-research-bist-2026-10-01-replay.json`.
- Altın: [eski arşiv provası](https://github.com/Mertsaglm/gold_tracking_system/blob/main/reports/portfolio-smoke-gold-2026-09-22.json)
  ve [model sınavı](https://github.com/Mertsaglm/gold_tracking_system/blob/main/reports/portfolio-model-research-gold-2026-09-22.json).

BIST yerel SQL'nin son kapanışı 2026-09-24'tür. O günde DSTKF ve TRALT barı
bulunmadığı için tarihli kopya provasındaki çekirdek 30 yerine 28 hissede
alım yapmıştır. Altın yerel SQL 2026-09-22'de biter. Test kotasyonları
`historical_assumption` olarak işaretlidir; canlı banka/emir dolumu değildir.
İki arşiv kopyasında beş kol, tekrar finansal olay değişmezliği, altışar
defterin bağımsız nakit/lot mutabakatı ve yedek geri okuması geçti. Taktik
işlem tutarında yarım kuruşu `float` ile çarpmak bir kuruşluk fark
oluşturuyordu; `Decimal` hesap ve regresyon testiyle düzeltildi. Eksik BIST30
üyeliği alımı durdurur; engellenmiş taktik satış haftalık kontrolü tamamlanmış
sayılmaz. Bu, **ortak ileri T0 için taze veri hazır** demek değildir.
2026-10-01'de indirilen üretim SQL'leriyle, orijinal dosyalara yazmadan aynı
prova tekrarlandı. [BIST makbuzu](../reports/portfolio-smoke-bist-production-copy-2026-09-30.json)
2026-09-30 kapanışından sonraki varsayımsal 2026-10-01 çevriminde 32 geçerli
kotasyon, 30 çekirdek pozisyon, beş aday ve altı mutabık defter gösterir.
[Altın makbuzu](https://github.com/Mertsaglm/gold_tracking_system/blob/main/reports/portfolio-smoke-gold-production-copy-2026-09-30.json)
aynı günün tarihli gram kapanışıyla beş aday/altı defter gösterir. İki makbuzda
tekrar işlem ve yedek farkı yoktur; fiyatlar **tarihsel varsayımdır**, canlı
işlem veya ileri performans kanıtı değildir. İlk BIST provası, karşılaştırma
sepetindeki yarım kuruş `float` hatasını yakaladı; `Decimal` düzeltmesi ve
regresyon kilidi sonrası geçti.
2026-10-01 hazır olma kontrolü `ready: false` verdi: bugünkü BIST30 kümesinde
son yerel kaynak gününün TRALT ve TRMET barı eksik, her iki arşiv de beklenen
2026-09-30 kapanışının gerisinde. T0 geçmişe veya tatil gününe konamaz.
Çıkış kodu 2 bilinçli hazır-değil sonucudur. Kontrolün `ready` alanı yalnız
**yerel arşiv/T0** içindir; `production_ready` dış kanıt gelene kadar false'dur.

2026-10-01 salt-okunur [uzak altın durumunda](https://github.com/Mertsaglm/gold_tracking_system/blob/a3437274415c1218c1bca12b301ea88704dd8e5e/data/advisor/latest.json)
14:33 UTC kapsülü 2026-09-30 analizini, 10.000 TL katkıyı, sıfır ana işlem ve
pozisyonu gösterdi. [Uzak altın ayarı](https://github.com/Mertsaglm/gold_tracking_system/blob/a3437274415c1218c1bca12b301ea88704dd8e5e/advisor/config.json)
eski 5.000 TL başlangıçlı sürümdedir; yeni beş kol orada yoktur. GitHub'da
07:02–14:46 UTC arasında 33 `advisor: sanal portfoy` commit'i gözlendi;
en büyük ardışık boşluk 15,3 dakikaydı. Bu gerçekleşen **altın çıktı ritmini**
gösterir; dış tetikleyicinin kimliğini kanıtlamaz. Özel BIST deposu bağlı API'de
404 döndü, fakat mevcut Safari oturumunda salt-okunur açıldı. 2026-10-01
[BIST üretim ayarı](https://github.com/Mertsaglm/bist-analiz/blob/2e64feaf12917757f04ff1f8261c8509277cae7b/advisor/config.json)
50.000 TL başlangıçlı eski ana hesabı taşır; yeni T0/aday modülü yoktur.
[BIST snapshot'ı](https://github.com/Mertsaglm/bist-analiz/blob/2e64feaf12917757f04ff1f8261c8509277cae7b/data/advisor/latest.json)
2026-09-30 analiz tarihini taşır. [Çalışma makbuzu](https://github.com/Mertsaglm/bist-analiz/blob/2e64feaf12917757f04ff1f8261c8509277cae7b/data/advisor/accounts/paper-2026-09-25/run_status.json)
14:46:54 UTC'de `ok=true, skipped=false` der. Görünen 29 BIST portföy commit'i
08:02–14:47 UTC arasında; en büyük ardışık boşluk 17 dakikadır. Bu çıktı
ritmidir, tetikleyicinin kimliği değildir. GitHub CLI kimliği geçersiz kaldı;
güncel iki üretim olay defteri Safari üzerinden salt-okunur kopyalandı.

Sabitlenmiş üretim commit'lerinden iki SQL dökümü Safari ile salt-okunur
indirildi ve yalnız geçici SQLite dosyalarına geri yüklendi:
[BIST SQL](https://github.com/Mertsaglm/bist-analiz/blob/2e64feaf12917757f04ff1f8261c8509277cae7b/data/bist.sql)
SHA-256 `dbe20b128d146580227d989444e179165425f9d8962e896090b4f455b90c0a06`;
73 hissenin 2026-09-30 barı, bu tarihteki 30 BIST30 çekirdek üyesinin de
barı ve beş endeks/kur serisinin 2026-09-30 kaydı mevcut. Yerel BIST SQL
SHA-256 `040bf4603ca2e8351db30f1b3af748b413e65d41726e635ce37564f4e323ff03`.
[Altın SQL](https://github.com/Mertsaglm/gold_tracking_system/blob/a3437274415c1218c1bca12b301ea88704dd8e5e/data/altin.sql)
SHA-256 `61bdc0936a202d6d6db14e47b02d8c4a7205f1835d7815e6bd4593990fa1e480`;
`history_daily` 2026-09-30'a ve GRAM banka tick'i 2026-09-30 20:14 UTC'ye
uzanır; `GC=F`/`TRY=X` OHLC ise 2026-09-29'da biter. Yerel altın SQL
SHA-256 `7e8bc0c8e945b9acf128154bd6c238759c403a8e48324dbfa4da92f3f1a05467`.
Bunlar canlı kopyaların yerelden daha güncel olduğunu doğrular; 2026-10-01
kapanışının tamamlandığını göstermez. [BIST güncel ana hesap
defteri](https://github.com/Mertsaglm/bist-analiz/blob/2e64feaf12917757f04ff1f8261c8509277cae7b/data/advisor/accounts/paper-2026-09-25/events.jsonl)
SHA-256 `9a92a702fa5871d76dee064f02b79818d6daf47d8148d09c80ce3fd38ce67f39`:
7.124 olayın hash zinciri doğrulandı; son olay 2026-10-01 14:46:54 UTC.
Bağımsız muhasebe dört hesapta `Ledger.account` ile eşleşti: ana strateji
55.000 TL nakit ve sıfır pozisyon/işlem; 60 dolum yalnız karşılaştırma
hesabındadır. Kök `data/advisor/events.jsonl` ayrı, eski defterdir; [son
değişim commit'inin](https://github.com/Mertsaglm/bist-analiz/commit/9f4182ffcfca55f0401dde19e2f06c31af430316)
yerel kopyayla eşliği güncel ana hesap için kanıt sayılmaz.
[Altın üretim defteri](https://github.com/Mertsaglm/gold_tracking_system/blob/a3437274415c1218c1bca12b301ea88704dd8e5e/data/advisor/events.jsonl)
SHA-256 `44381f24af599d0c4668dcc5f94bd62ea582ec3befa999770c0aeaaae8805e0c`;
Git blob `ef910da854838ec879f9ddc4804f7eb965972847` ve 1.863 olayın
hash zinciri doğrulandı. Dört hesabın bağımsız muhasebesi eşleşti: ana
strateji 10.000 TL nakit, sıfır pozisyon/işlem. Bunlar üretim defteri
bütünlüğünü gösterir; yeni kodun üretimde çalıştığını göstermez.
Eski **yerel** defterlerde 148 BIST ve 86 altın karar kapsülü, kayıtlı kaynak
kodu ve sabit bağımlılık sürümleriyle yeniden üretildi. Bu kontrol güncel
üretim kapsüllerini kapsamaz. Altın yerel sanal ortamı bu doğrulama sırasında
`pandas==2.3.3` ve `tzdata==2026.3` çalışma zamanı kilidine eşitlendi.

GitHub Actions [BIST manuel tetikleme](https://github.com/Mertsaglm/bist-analiz/actions/runs/36878914856)
ve [planlı yedek koşu](https://github.com/Mertsaglm/bist-analiz/actions/runs/36876377339),
ayrıca [altın manuel tetikleme](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/36878914565)
ve [planlı yedek koşu](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/36877224855)
kayıtlarını gösterir. `workflow_dispatch` kayıtları yaklaşık 15 dakikalık
çıktı ritmiyle uyumludur; dış dispatch hizmetinin kimliğini doğrulamaz.

Offline son 126 test gününde seçilmiş BIST evreni için göreli Ridge Rank IC
ortalaması 0,0084, LightGBM 0,0022'dir; MAE sırasıyla 7,659 ve 7,713
yüzde puandır. Altında temel ve ons/kur Ridge MAE'si 11,619 ve 11,747
yüzde puandır. Bu arşiv sonuçları üstünlük göstermiyor. BIST evreni sonradan
seçilmiştir; arşivin son günü 2026-09-24, üyelik kaydı 2026-09-25'tir.
Hesaplanabilir maliyetli, bağımsız portföy getiri serisi olmadığından DSR
hesaplanmadı. Hiçbir model otomatik terfi etmez.

2026-10-01 yeniden çalıştırmasında altın raporu birebir aynı çıktı. BIST yerel
SQL'si ilk makbuzdan sonra değiştiği için `frame_id` farklılaştı; test satırı
3944'ten 3948'e çıktı. Yeni BIST makbuzunda göreli Ridge Rank IC 0,0063,
LightGBM 0,0017; MAE sırasıyla 7,680 ve 7,733 yüzde puandır. 26 katlamanın
hepsinde eğitim etiketinin bitişi test başlangıcından öncedir. İlk makbuz
korundu; bu iki farklı veri sürümünün sonucu tek sonuç gibi sunulmaz.

## 24 Kasım T0 kontrolü

İki üretim ayarında `experiment_start_date` boş ve beş yeni defter açılmamıştı.
BIST çekirdeğinde 30/30 üyenin kotasyonu alıma uygundu. Altın 1/1 geçerli
fiyat verdi ve yaklaşık %3,38 makas %3 alım sınırını aştı. Ortak başlangıç
için iki otomatik kapanış makbuzu, uygun kotasyon, doğrulanmış takvim,
eş bütçe ve mevcut defter bütünlüğü gerekir. T0 ortak bir gelecek seansında
açılır. İlk katkı ve kotasyon kimlikleri ayrıca doğrulanır.
[24 Kasım kanıtı](DENETIM-2026-11-24.md)

## T0 ve 1 Ekim yayın kaydı

Kod 2026-10-01'de BIST `bee1a1c` ve altın `dddb27c` ile üretim `main`
dalına yayımlandı. [BIST yeni kod koşusu](https://github.com/Mertsaglm/bist-analiz/actions/runs/36901914212)
başarılı fakat seans dışı olduğu için atlandı; eski ana deftere yalnız
`session_check` eklendi, finansal olay sayısı değişmedi.
[Altın yeni kod koşusu](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/36901918911)
başarılıdır: yeni ana hesap 50.000 TL başlangıç ve 5.000 TL Ekim katkısını
ayrı kaydetti, Telegram makbuzu `message_id: 320` taşır. Yeni deneyin
`portfolio_experiments.status` alanı `T0 bekleniyor`, hesap listesi boştur.
Vercel'in üç canlı statik dosyası yayımlanan sürümle eşleşti; parolalı API
görünümü doğrulanmadı.

Ortak T0 için 2026-10-01 kapanış/fiyatları, iki piyasada seans içi atlanmamış
yeni kod çevrimleri, 30 BIST30 üyesi ve GRAM kotasyonu, aktif/eski defter
bütünlüğü yeniden doğrulanmalı. Kopya provasının geçmesi canlı eşlik değildir.
Bu kapılar geçince ortak gelecek işlem günü iki config'e aynı T0 yazılır;
geçmiş hesaplar yeniden ölçeklenmez. 20 seans çalışma, 63/126 seans ekonomik
değerlendirme için ayrı eşiklerdir; erken işlem sayısı üstünlük sayılmaz.
BIMAS geçmiş karne düzeltmesi bu yayına dahil değildir. Geri dönüş yeni adayın
yeni işlemlerini durdurur; eski sanal defter silinmez.


## 24 Kasım araştırma paketi

İlk T0 değerlendirmesinde yalnız çekirdeğin güvenilir fiyatı, tarihli üyelik,
ortak bütçe ve son tamamlanmış kapanış aranır. Çekirdek ve tam pasif kolda
GRAM için %4, ana ve aktif taktik kolda %3 azami makas geçerlidir. Aktif
tahmin, trend ve R:R çekirdeği belirlemez. Taktik model başarısız olduğunda
açık pozisyonun geçerli güncel fiyatla stop kontrolü sürer.

20.10 İstanbul kesitinde 25 Kasım önerisi BIST çekirdeğinde 30/30 ve
altında 1/1 uygun gözlem buldu. İki üretim SQL'i de 23 Kasım'da bitiyor.
Ortak başlangıç için 24 Kasım kapanışı eksik. Tarih ayarı boş.
[Salt okunur T0 makbuzu](../reports/champion-challenger-2026-11-24/t0-preflight.json)
20.20'de gerçek fiyat kaynağıyla geçici BIST arşivi 24 Kasım kapanışına
ulaştı. T0 kontrolü o kopyada 30/30 ile geçti. İki üretim SQL'i için
20.10 sonucu yukarıda. [BIST kapanış telafisi](../reports/champion-challenger-2026-11-24/bist-closing-recovery.json)

Beş kolun kopya provasında katkı, tekrar çalıştırma ve altı defterin
bağımsız mutabakatı geçti. [Prova makbuzu](../reports/champion-challenger-2026-11-24/t0-bist-smoke.json)
[Rapor önizlemesi](../reports/champion-challenger-2026-11-24/weekly-preview.txt)

Bağımsız tarihsel deneyler T0'dan önce çalıştırıldı. Protokol ve
değerlendirme koşulu [karar günlüğünde](../ai/DECISIONS.md).

25 Eylül–23 Kasım aralığı 41 seans ve kol başına 60.000 TL katkı içeriyor.

| Sıralama | Net değer | Katkısız getiri | En büyük düşüş | 1,5× işlem maliyetinde net değer |
|---|---:|---:|---:|---:|
| Göreli Ridge | 52.189,55 TL | −%15,10 | −%18,31 | 52.156,22 TL |
| 120–20 seans momentum | 52.741,68 TL | −%14,24 | −%18,50 | 52.665,74 TL |
| Tam pasif | 52.920,08 TL | −%13,98 | −%18,71 | 52.764,33 TL |

Momentum aynı taktik kurallarla Ridge'i 552,13 TL geçti ve 43,28 TL daha
az işlem ücreti üretti. Pasif her iki maliyet senaryosunda son net değerde
önde. Karar öncesi veriye göre 32 düşen/yüksek, 6 yatay/yüksek,
3 düşen/düşük seans vardı. Yükselen rejim gözlenmedi. Momentum
yatay/yüksek grupta iki referansı geçti. Altı seans, rejim değiştirici
politika için yetersiz. [Normal](../reports/champion-challenger-2026-11-24/bist-momentum-cost-1.json)
· [Maliyet stresi](../reports/champion-challenger-2026-11-24/bist-momentum-cost-1.5.json)

Aynı protokol üretim SQL kopyası üzerinden tekrar çalıştırılabilir.

```sh
python -m scripts.bist_rank_replay --momentum-ablation --asof 2026-11-23 --database /tmp/bist.db --output /tmp/bist-momentum-yeni.json
```
