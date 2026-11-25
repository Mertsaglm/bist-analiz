# Mevcut durum

## Devir kontrolü — 2026-11-25

25 Kasım 21.56 İstanbul kesitinde GitHub dalları, koşular ve üretim defter görünümleri yeniden doğrulandı.
İnceleme dalının doküman CI'ı iki depoda geçti. Araştırma paketi ve işletim düzeltmeleri 25 Kasım main yayın paketinde. İlk yeni kodlu canlı finansal çevrim ayrı doğrulanır.
Araştırma inceleme dalına gönderildi. [İlk paket `3d035cb`](https://github.com/Mertsaglm/bist-analiz/commit/3d035cb848d78f8e23c28c290e300c32b426ab87).
Üretim kaynağı `main`. Canlı kabul ayrıca ölçülür.

| Konu | Son doğrulanmış durum |
|---|---|
| BIST üretimi | `044e14f` main. 25 Kasım 17.17 V2 33/33, analiz 24 Kasım. 20.59 koşusunda portföy adımı atlandı. [Yazan çevrim](https://github.com/Mertsaglm/bist-analiz/actions/runs/45632089206) |
| Altın üretimi | `e9f670b` main. 25 Kasım 20.12 V2 1/1, analiz ve son teorik SQL 24 Kasım. Standart Telegram ve makbuz adımları geçti; planlı kapanış adımı atlandı. [Çevrim](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/45662069899) |
| Araştırma | Bağımsız momentum 25 Kasım'da başladı. 30/30 sıra, 50.000 TL katkı, 5 strateji ve 30 pasif dolum. 22 Aralık vadesi korunuyor. Ortak T0 kapalı. [İlk gün görünümü](https://github.com/Mertsaglm/bist-analiz/blob/044e14fd12286ee0d94328d5ba16fbd5a228fe10/data/advisor/latest.json) |
| Tahmin araştırması | Ayrı 5/20/60 seans CPU koşusu tamamlandı, BIST 20 seans LambdaRank IC +0,0984, altında sıfır getiri MAE'de üç ufukta önde. 25 Kasım 01.09 yerel gölge, 29/30 hisse, altı sıralayıcı, vade 22 Aralık. [Kanıt](../docs/TAHMIN-ARASTIRMASI-2026-11-25.md) |
| Ek denetim | Tarihli 42 seans replay'inde saf LambdaRank 51.752,75 TL, momentum 52.135,60 TL, pasif 52.634,27 TL. Yeni sözleşme kapsamı ve 5 seans gölge yayın paketinde. [Denetim](../docs/TAHMIN-DENETIMI-2026-11-25.md) |
| Yerel paket | Momentum/pasif hisse ve nakit payı, haftalık ortalama ve gün sayısı, stop ve stres ölçümleri. BIST OHLC reddinde dört ham değer. 25 Kasım main yayın paketinde. Her depoda 5 hedefli test, BIST'te 30 fiyat/telafi testi, 39 ortak modül eş. |
| Veri İzleme | Vercel canlı dosyası doğrulandı. Parolalı oturum, altın otomatik gün sonu makbuzu ve yeni haftalık teslim açık. |
| Kapasite | 24 Kasım aktif artifact: BIST 9 / 496 MB, altın 32 / 6,21 GB. Git defterleri 66,6 / 8,0 MB. BIST örnek günlük koşusu 4 dk 36 sn, V2 telafisi 3 dk 28 sn, CI toplamı 3 dk 48 sn. Hesap faturalama erişimi yok; kalan kota bilinmiyor. |

ARCLK ve SELEC, V1 canlı evreni, V2 izleme evreni ve BIST30 dışında.
Aynı Yahoo istemcisinin sonraki okuması iki barı da doğruladı. Üretimde
reddedilen ilk ham değerler olmadığından kök neden doğrulanmadı.

[BIST V2](https://github.com/Mertsaglm/bist-analiz/actions/runs/45464353034) ·
[BIST CI](https://github.com/Mertsaglm/bist-analiz/actions/runs/45464429266) ·
[Altın çevrimi](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/45463521929) ·
[Altın telafisi](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/45464093885) ·
[Mühürlü momentum](https://github.com/Mertsaglm/bist-analiz/blob/7e19f7e3c369fd9c961f1258fac5efd750e68ca9/reports/champion-challenger-2026-11-24/bist-momentum-forward.json)

Önceki çalışma ve ölçümler [24 Kasım denetiminde](../docs/DENETIM-2026-11-24.md),
[portföy deneyinde](../docs/PORTFOY-DENEYI-2026-10-01.md) ve
[işletim rehberinde](../docs/ISLETIM-2026-11-18.md).

## Açık bulgular ve kanıt sınırı

- BIST girişinde dört ekonomik kapısı ölçülen 14.861 kararın sıfırı
  birlikte geçti. R:R çıkarılırsa 2.130 aday kalıyor. Vade ve kotasyonu
  eşleşen 14 R:R reddinin 11’i masraf sonrası nakdin altında.
- 20 Kasım: BIST 8/9 işlem çevrimi, kapanış Telegram 286 dışa aktarımla
  eşleşti. 21.54 AGHOL veri uyarısı gerçek. Altında 33/33 fiyatlı çevrim var,
  sonuncusu 18.26. Geciken işler hafta sonu sebebiyle atlandı, kapanış yok.
- 23 Kasım: BIST 8/10 çalışan işlem çevrimi, makbuz 298 eksik kapanış.
  24 Kasım kesitinde arşiv toparlandı. Kaynak arızasının nedeni DOĞRULANMADI.
- Canlı parolalı panel, yeni haftalık teslim ve altın V2 kapanış makbuzu açık.
- BIST’te 6 şablon testi, çalışma kopyasında önceden kaldırılmış
  `Proje Yardımcısı/yeni-proje.sh` dosyasını bekliyor. 25 Kasım
  araştırma paketinde 42 hedefli ve 1.545 toplam test geçti.
- CCOLA/HEKTS kırılmaları 40 eğitim etiketini etkiliyor. Offline duyarlılık
  MAE ve Rank IC'yi kayda değer değiştirmedi. Kaynak tarihleri doğrulanacak.
- Altın 2026-11-17 sabah kaynak kimliği hatası, ardından toparlanma doğrulandı;
  başarısız yanıtın gövdesi yok, kök neden DOĞRULANMADI. Kontrol gevşetilmedi.
- Altın dış tetikleyicide 14:45–15:58 UTC boşluğu; nöbetçi doğru alarm üretti.
  Dış scheduler arızasının nedeni DOĞRULANMADI; cron zaman garantisi yok.
- 24 Kasım 20.20: Geçici arşivde gerçek kaynakla 73/73 hisse ve beş
  kur/endeks serisi 24 Kasım'a ulaştı. [Yerel telafi](../reports/champion-challenger-2026-11-24/bist-closing-recovery.json)
- Arşivde 61 eski USDTRY OHLC ihlali; bağımsız kaynak olmadan onarılmadı.
- BIST data/advisor uzak Git ağacı 3.349.042.744 byte; geçmiş silinmedi.
- İki canlı model approved=false, tamamlanmış strateji roundtrip 0.
  Offline sıralama başarısı net portföy üstünlüğü değildir; otomatik T0 yok.

## Sıradaki 3 İş

1. Üretim kapanışlarını ve başlayan momentum kolunu takip et.
   DoD: Son SQL tarihi, fiyat kapsamı, defter ve kapanış makbuzları eşleşir.
2. Yerel ölçüm paketini yayın ve canlı kabul açısından takip et.
   DoD: Eş pasif maruziyet, nakit, stop ve örneklem paydası haftalık görünür.
3. Altın zamanlama, BIST trend/R:R ve yeni sıralama deneylerini bağımsız izle.
   DoD: Ayrı kimlik, eş bütçe, tek politika farkı, ilk uygun çevrim ve
   vadesi gelen gölge tahminlerde kapsam/IC/ilk beş brüt farkı.

## TAKVİM

| Tarih | İş | Kim | Durum |
|---|---|:--:|---|
| 2026-11-20 | İlk günlük Telegram canlı kabulü | 🤖 | BIST geçti, altın eksik |
| 2026-11-25 | GC=F roll, bağımsız prim/FRED kapsamı | 🤖 | Bekliyor |
| 2026-12-01 | Yeni 5 seans yerel BIST gölge vadesi | 🤖 | Bekliyor |
| 2026-12-15 | 32 mühürlü BIST tahmininin vadesi | 🤖 | Bekliyor |
| 2026-12-22 | Bağımsız 30 momentum sırası ve 29 isimlik ML gölge vadesi | 🤖 | Bekliyor |

## SENDE KALANLAR

- 24 Kasım: Mert önceki paket için commit, push ve üretim yayınına onay verdi.
  25 Kasım tahmin araştırması inceleme dalında izlenir. Ortak T0 ve altın V2 kapanış kabulü açık.
- 👤 Mert yayın onayını 2026-11-18 tarihinde verdi.
- 2026-11-19: Mert yayın onayı verdi. Üretim `2764d23` ile güncellendi.
  19 Kasım yeni işletim dönemi başlangıç kesiti. Eski defterler korunuyor.

## Backlog

- D-01 BIMAS tarihsel düzeltme, erken Ekim telafi kayıpları ve kaynak
  revizyonları önceki kayıtta açık; yeni denetim bunları kapatmıyor.
- Geçmiş üyelik, banka kotasyonu/emir sırası, kişisel tarife/MKK, temettü
  ödeme günü ve revizyon geçmişli TÜFE sınırları devam ediyor.
- 2027 tahmini takvim resmi kaynakla doğrulanmalı.
- Ayrıntılı önceki kayıt: `ai/archive/STATE-2026-11-17-before-audit.md`.
- Denetim: `docs/DENETIM-2026-11-17.md`; kanıtlar `reports/denetim-2026-11-17/`.
- V1 ön kayıt: `docs/on-kayit-seviye-02.md`; tetikleyici olmadan çalıştırılmaz.
- İşletim ve kabul rehberi `docs/ISLETIM-2026-11-18.md`.
