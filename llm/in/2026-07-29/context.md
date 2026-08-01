# Analiz Paketi — 2026-07-29

> ⚠ Ölçülen kenar yok (ADR #008). Bu seviyeler planlama geometrisidir, yön iddiası değildir.

**bundle_sha:** `d27888b6051e3e686f406baeeeb9ed47e7fad3d5d7d6f030511ab846594ee3dd` — çıktına BİREBİR kopyala.

## Piyasa rejimi: **risk-off**

- XU100 SMA200 farkı: 6.04%
- Genişlik (SMA50 üstü): 32.84%
- Politika: nakit %90, maks 2 pozisyon, sektör başına maks 2

- Makro: **veri yok** (EVDS anahtarı girilmemiş) — bu satırlar uydurulmaz, gizlenir.

## Evren (18 hisse)

### AKBNK · banka
Kapanış **64.9** (-1.37% günlük) · 52h 53.05–93.50
RSI 31.94 · ATR 2.16 (3.32%) · ADX 23.42 · SMA20 69.50 / SMA50 70.79 / SMA200 71.96

**KAP bildirimleri** (son analizden bu yana):
- `kap-1637890` · 2026-07-28 15:17 · önem: orta — Geleceğe Dönük Değerlendirmeler — Geleceğe Yönelik Değerlendirmeler
- `kap-1637888` · 2026-07-28 15:15 · önem: orta — Sorumluluk Beyanı (Konsolide Olmayan) — 30-06-2026 Akbank Konsolide Olmayan Sorumluluk Beyanı
- `kap-1637887` · 2026-07-28 15:15 · önem: orta — Sorumluluk Beyanı (Konsolide) — 30-06-2026 Akbank Konsolide Sorumluluk Beyanı
- `kap-1637885` · 2026-07-28 15:15 · önem: yuksek — Finansal Rapor
- `kap-1637884` · 2026-07-28 15:15 · önem: yuksek — Finansal Rapor
- `kap-1637247` · 2026-07-27 14:46 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — XS3259253618 ISIN Kodlu Yurtdışı Piyasalara İhraç Edilen Tahvilin Kupon Ödemesi
- `kap-1637246` · 2026-07-27 14:46 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — XS3250452565 ISIN Kodlu Yurtdışı Piyasalara İhraç Edilen Tahvilin Kupon Ödemesi
- `kap-1637245` · 2026-07-27 14:46 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — XS3101428756 ISIN Kodlu Yurtdışı Piyasalara İhraç Edilen Tahvilin Kupon Ödemesi

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### ASELS · savunma
Kapanış **360.5** (0.70% günlük) · 52h 167.00–450.00
RSI 46.08 · ATR 15.93 (4.42%) · ADX 13.16 · SMA20 368.55 / SMA50 377.76 / SMA200 307.19

**KAP bildirimleri** (son analizden bu yana):
- `kap-1635301` · 2026-07-21 09:58 · önem: orta — Finansal Takvim — Finansal Takvim
- `kap-1631439` · 2026-07-10 07:53 · önem: yuksek — Yeni İş İlişkisi — Sözleşme İmzalanması
- `kap-1621738` · 2026-06-30 06:22 · önem: orta — Özel Durum Açıklaması (Genel) — Devreye Alınan Yatırımlarımız Hakkında
- `kap-1617528` · 2026-06-16 06:15 · önem: yuksek — Yeni İş İlişkisi — Sözleşme İmzalanması
- `kap-1616972` · 2026-06-15 06:15 · önem: yuksek — Yeni İş İlişkisi — Sözleşme İmzalanması
- `kap-1616715` · 2026-06-12 12:27 · önem: orta — Özel Durum Açıklaması (Genel) — Süresi İçinde Kaydileştirilmeyen Paylarla İlgili Yatırımcı Tazmin Merkezi Başvuruları Hakkında Duyuru
- `kap-1612829` · 2026-06-04 06:15 · önem: yuksek — Yeni İş İlişkisi — Sözleşme İmzalanması
- `kap-1611291` · 2026-06-01 06:17 · önem: yuksek — Yeni İş İlişkisi — Sözleşme İmzalanması

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `ASELS-2026-07-29-A` | dogrudan | 358.5–360.5 | 328.5 | 412.0 (1.61) | 4.51 |
| `ASELS-2026-07-29-B` | destek_retest | 349.75–357.0 | 325.0 | 412.0 (1.72) | 4.46 |

### ASTOR · elektrik_ekipman
Kapanış **282.25** (1.71% günlük) · 52h 88.20–385.75
RSI 43.39 · ATR 17.38 (6.16%) · ADX 14.14 · SMA20 304.02 / SMA50 307.26 / SMA200 194.09

**KAP bildirimleri** (son analizden bu yana):
- `kap-1636211` · 2026-07-23 15:13 · önem: dusuk — Bağımsız Denetim Kuruluşunun Belirlenmesi — Sürdürülebilirlik Güvence Denetimi Kuruluşunun Belirlenmesi Hakkında
- `kap-1635127` · 2026-07-20 15:15 · önem: orta — İhale Süreci / Sonucu — TEİAŞ İhalesi
- `kap-1632417` · 2026-07-13 10:03 · önem: orta — Yeni İş İlişkisi — Yeni İş İlişkisi
- `kap-1627788` · 2026-07-08 07:42 · önem: orta — Yeni İş İlişkisi — Yeni İş İlişkisi
- `kap-1627416` · 2026-07-07 16:01 · önem: yuksek — Kar Payı Dağıtım İşlemlerine İlişkin Bildirim — 2025 Yılı Kar Payı Dağıtımı Hakkında Yönetim Kurulu Teklifi
- `kap-1627415` · 2026-07-07 16:01 · önem: dusuk — Genel Kurul İşlemlerine İlişkin Bildirim — 2025 Yılı Olağan Genel Kurul Toplantı Çağrısı
- `kap-1623500` · 2026-07-03 06:46 · önem: orta — İhale Süreci / Sonucu — TEİAŞ İhalesi
- `kap-1623322` · 2026-07-02 15:38 · önem: orta — Kayıtlı Sermaye Tavanı İşlemlerine İlişkin Bildirim — Kayıtlı Sermaye Tavanı Artırımı ve Geçerlilik Süresinin Uzatılmasına İlişkin T.C. Ticaret Bakanlığı Onayı

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### BIMAS · perakende
Kapanış **390.5** (0.26% günlük) · 52h 241.62–425.00
RSI 54.60 · ATR 11.31 (2.90%) · ADX 19.28 · SMA20 380.26 / SMA50 381.51 / SMA200 331.98

**KAP bildirimleri** (son analizden bu yana):
- `kap-1637993` · 2026-07-28 16:32 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 28 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri
- `kap-1637412` · 2026-07-27 16:26 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 27 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri
- `kap-1636648` · 2026-07-24 15:48 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 24 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri
- `kap-1636283` · 2026-07-23 16:33 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 23 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri
- `kap-1635533` · 2026-07-21 17:32 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 21 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri
- `kap-1634671` · 2026-07-17 16:49 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 17 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri
- `kap-1632922` · 2026-07-13 16:16 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 13 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri
- `kap-1632046` · 2026-07-10 15:39 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 10 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `BIMAS-2026-07-29-A` | dogrudan | 388.5–390.5 | 367.75 | 425.0 (1.52) | 6.87 |
| `BIMAS-2026-07-29-B` | sma20_geri_cekilme | 376.25–384.25 | 361.5 | 425.0 (1.79) | 6.76 |
| `BIMAS-2026-07-29-C` | destek_retest | 383.25–390.5 | 367.75 | 425.0 (1.52) | 6.87 |

### EKGYO · gyo
Kapanış **18.16** (-0.22% günlük) · 52h 17.62–27.12
RSI 31.97 · ATR 0.68 (3.73%) · ADX 20.11 · SMA20 20.12 / SMA50 20.21 / SMA200 20.97

**KAP bildirimleri** (son analizden bu yana):
- `kap-1637307` · 2026-07-27 15:05 · önem: orta — Özel Durum Açıklaması (Genel) — İstanbul Esenler Atışalanı Kuzey 1. Etap 2. Oturum Sonucu
- `kap-1636545` · 2026-07-24 14:00 · önem: orta — Özel Durum Açıklaması (Genel) — İstanbul Eyüpsultan Göktürk 1. Etap Kesin Kabulü
- `kap-1636005` · 2026-07-23 10:57 · önem: orta — Özel Durum Açıklaması (Genel) — Konya Meram 2. Etap İhale İlanı
- `kap-1635773` · 2026-07-22 14:04 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1635409` · 2026-07-21 13:36 · önem: orta — Özel Durum Açıklaması (Genel) — İstanbul Esenler Atışalanı Kuzey 1. Etap İhalesi 2. Oturum Tarihi
- `kap-1635406` · 2026-07-21 13:35 · önem: yuksek — Özel Durum Açıklaması (Genel) — Ankara Gölbaşı Taşpınar Sözleşme İmzalanması
- `kap-1634714` · 2026-07-17 19:30 · önem: orta — Özel Durum Açıklaması (Genel) — Damla Kent Projesi Gayrimenkul Sertifikası İnşaat İlerlemesi ve Asli Edim Gerçekleşmeleri
- `kap-1634713` · 2026-07-17 19:30 · önem: orta — Değerleme Raporu — Damla Kent Gayrimenkul Değerleme Raporu

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### ENKAI · insaat
Kapanış **89.15** (0.45% günlük) · 52h 65.55–114.30
RSI 43.18 · ATR 2.30 (2.58%) · ADX 21.53 · SMA20 90.47 / SMA50 93.29 / SMA200 89.36

**KAP bildirimleri** (son analizden bu yana):
- `kap-1614200` · 2026-06-08 06:28 · önem: orta — Özel Durum Açıklaması (Genel) — Yatırımcı Tazmin Merkezi Başvurularına İlişkin Duyuru
- `kap-1603563` · 2026-05-08 15:15 · önem: yuksek — Kurumsal Yönetim İlkelerine Uyum Derecelendirmesi — Kurumsal Yönetim İlkelerine Uyum Derecelendirmesi Sözleşmesi
- `kap-1603556` · 2026-05-08 15:14 · önem: yuksek — Özel Durum Açıklaması (Genel) — Kâr Payı Avansı Dağıtmama Kararı
- `kap-1603551` · 2026-05-08 15:13 · önem: orta — Sorumluluk Beyanı (Konsolide) — Sorumluluk Beyanı 31.03.2026
- `kap-1603547` · 2026-05-08 15:13 · önem: dusuk — Faaliyet Raporu (Konsolide) — Faaliyet Raporu 31.03.2026
- `kap-1603543` · 2026-05-08 15:12 · önem: yuksek — Finansal Rapor

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### EREGL · demir_celik
Kapanış **43.88** (0.05% günlük) · 52h 23.46–45.10
RSI 60.38 · ATR 1.51 (3.45%) · ADX 30.48 · SMA20 42.01 / SMA50 40.56 / SMA200 31.19

**KAP bildirimleri** (son analizden bu yana):
- `kap-1636318` · 2026-07-24 06:30 · önem: orta — Kurumsal Yönetim İlkelerine Uyum Derecelendirmesi — Kurumsal Yönetim İlkelerine Uyum Derecelendirme Raporu ve Notu
- `kap-1636246` · 2026-07-23 15:31 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — XS2861686041 ISIN Kodlu Tahvilin 4.Kupon Ödemesi
- `kap-1635535` · 2026-07-21 18:30 · önem: orta — Kredi Derecelendirmesi — Moody's Kredi Derecelendirme Notu
- `kap-1614893` · 2026-06-08 15:12 · önem: orta — Özel Durum Açıklaması (Genel) — Yatırımcı Tazmin Merkezi'ne Başvuru Süresi Hakkında Duyuru
- `kap-1610422` · 2026-05-22 12:30 · önem: yuksek — Kurumsal Yönetim İlkelerine Uyum Derecelendirmesi — Kurumsal Yönetim İlkelerine Uyum Derecelendirme Sözleşmesi'nin Yenilenmesi
- `kap-1608801` · 2026-05-19 16:42 · önem: orta — Kredi Derecelendirmesi — Fitch Kredi Derecelendirme Notu
- `kap-1598433` · 2026-04-28 19:37 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1598432` · 2026-04-28 19:37 · önem: yuksek — Özel Durum Açıklaması (Genel) — Tüzel Kişi Yönetim Kurulu Üye Temsilcisi Değişiklikleri ve Yönetim Kurulu Üyelerinin Görev Dağılımı

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 3 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### EUPWR · elektrik_ekipman
Kapanış **86.25** (-2.43% günlük) · 52h 25.50–108.60
RSI 46.17 · ATR 5.98 (6.93%) · ADX 27.84 · SMA20 90.94 / SMA50 86.49 / SMA200 48.89

**KAP bildirimleri** (son analizden bu yana):
- `kap-1637145` · 2026-07-27 13:28 · önem: orta — Özel Durum Açıklaması (Genel) — Bağlı Ortaklığımız Tarafından Stratejik Taşınmaz Edinimi
- `kap-1632310` · 2026-07-13 07:34 · önem: orta — İhale Süreci / Sonucu — İhale Sonucu Hakkında
- `kap-1621602` · 2026-06-29 15:11 · önem: yuksek — Esas Sözleşme — Güncel Esas Sözleşme Hak.
- `kap-1621159` · 2026-06-26 15:02 · önem: orta — Bağımsız Denetim Kuruluşunun Belirlenmesi — Bağımsız Denetim Kuruluşunun Tescili
- `kap-1621154` · 2026-06-26 14:54 · önem: yuksek — Kayıtlı Sermaye Tavanı İşlemlerine İlişkin Bildirim — Kayıtlı Sermaye Tavanı Esas Sözleşme Madde Tadilinin Tescili Hakkında
- `kap-1621146` · 2026-06-26 14:49 · önem: orta — Genel Kurul İşlemlerine İlişkin Bildirim — 2025 Yılı Olağan Genel Kurul Kararlarının Tescili Hakkında
- `kap-1619903` · 2026-06-23 15:11 · önem: orta — Özel Durum Açıklaması (Genel) — Kurumsal yatırımcılara hızlandırılmış talep toplama yöntemiyle yapılan satışın takasının tamamlanması
- `kap-1618962` · 2026-06-19 11:12 · önem: orta — İhale Süreci / Sonucu — İhale Sonucu Hakkında

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `EUPWR-2026-07-29-A` | dogrudan | 85.8–86.25 | 74.25 | 107.9 (1.8) | 1.44 |

### FROTO · otomotiv
Kapanış **77.35** (-0.26% günlük) · 52h 77.20–135.40
RSI 30.64 · ATR 1.93 (2.49%) · ADX 41.99 · SMA20 81.42 / SMA50 85.22 / SMA200 98.17

**KAP bildirimleri** (son analizden bu yana):
- `kap-1632921` · 2026-07-13 16:15 · önem: orta — Finansal Takvim — 2026 2.Çeyrek Finansal Takvim
- `kap-1624116` · 2026-07-03 15:30 · önem: orta — Faaliyetlerin Kısmen veya Tamamen Durdurulması ya da İmkansız Hale Gelmesi — 2026 Yıllık İzin Uygulaması
- `kap-1623398` · 2026-07-02 16:27 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1622206` · 2026-07-01 06:15 · önem: orta — Finansal Duran Varlık Edinimi — Koç Finansman A.Ş. paylarının satın alma işleminin tamamlanması
- `kap-1621199` · 2026-06-26 15:20 · önem: orta — Özel Durum Açıklaması (Genel) — Üst Düzey Organizasyon Değişikliği
- `kap-1617911` · 2026-06-16 17:10 · önem: orta — Özel Durum Açıklaması (Genel) — Süresi İçinde Kaydileştirilmeyen Paylara İlişkin Yatırımcı Tazmin Merkezi Başvuruları Hakkında Açıklama
- `kap-1617463` · 2026-06-15 16:07 · önem: orta — Kurumsal Yönetim İlkelerine Uyum Derecelendirmesi — Kurumsal Yönetim İlkelerine Uyum Derecelendirme Notu
- `kap-1610749` · 2026-05-22 15:40 · önem: orta — Özel Durum Açıklaması (Genel) — Koç Finansman A.Ş Paylarının Satın Alımına İlişkin Rekabet Kurulu Onayı

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 1 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### GARAN · banka
Kapanış **127.0** (-0.31% günlük) · 52h 115.40–169.70
RSI 42.25 · ATR 3.36 (2.65%) · ADX 17.67 · SMA20 129.31 / SMA50 131.41 / SMA200 137.94

**KAP bildirimleri** (son analizden bu yana):
- `kap-1636615` · 2026-07-24 15:10 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — Yurtdışı Piyasalara Tahvil İhracı SPK Onayı
- `kap-1636519` · 2026-07-24 13:24 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — Yurtdışı Piyasalara Tahvil İhracı SPK Onayı
- `kap-1636202` · 2026-07-23 15:10 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — Yurtdışı Piyasalara Tahvil İhracı SPK Onayı
- `kap-1635989` · 2026-07-23 10:12 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — Yurtdışı Piyasalara Tahvil İhracı SPK Onayı / İhraç Türü düzeltimi
- `kap-1635988` · 2026-07-23 10:11 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — Yurtdışı Piyasalara Tahvil İhracı SPK Onayı
- `kap-1635501` · 2026-07-21 15:11 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — Yurtdışı Piyasalara Tahvil İhracı SPK Onayı
- `kap-1635125` · 2026-07-20 15:13 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — Yurtdışı Piyasalara Tahvil İhracı SPK Onayı
- `kap-1634570` · 2026-07-17 15:11 · önem: orta — Özel Durum Açıklaması (Genel) — Tahsili gecikmiş alacak portföy satışı hk.

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### KCHOL · holding
Kapanış **196.1** (0.56% günlük) · 52h 146.00–229.10
RSI 51.29 · ATR 5.28 (2.69%) · ADX 19.36 · SMA20 194.16 / SMA50 193.31 / SMA200 188.98

**KAP bildirimleri** (son analizden bu yana):
- `kap-1634245` · 2026-07-16 15:28 · önem: orta — Finansal Takvim — 2026 2. Çeyrek Finansal Takvim
- `kap-1622205` · 2026-07-01 06:15 · önem: orta — Finansal Duran Varlık Satışı — Koç Finansman A.Ş. paylarının satışı işleminin tamamlanması
- `kap-1616897` · 2026-06-12 15:15 · önem: orta — Özel Durum Açıklaması (Genel) — Süresi İçinde Kaydileştirilmeyen Paylara İlişkin Yatırımcı Tazmin Merkezi Başvuruları Hakkında Açıklama
- `kap-1611273` · 2026-05-29 10:18 · önem: orta — Kredi Derecelendirmesi — Kredi Derecelendirmesi
- `kap-1603641` · 2026-05-08 15:30 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1603638` · 2026-05-08 15:30 · önem: yuksek — Özel Durum Açıklaması (Genel) — Finansal raporların açıklanması
- `kap-1603573` · 2026-05-08 15:16 · önem: orta — Sorumluluk Beyanı (Konsolide) — Sorumluluk Beyanı
- `kap-1603571` · 2026-05-08 15:16 · önem: dusuk — Faaliyet Raporu (Konsolide) — 01.01.2026-31.03.2026 Faaliyet Raporu

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 3 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### KRDMD · demir_celik
Kapanış **42.32** (-0.19% günlük) · 52h 23.50–47.00
RSI 57.01 · ATR 1.66 (3.91%) · ADX 17.80 · SMA20 40.55 / SMA50 40.25 / SMA200 32.38

**KAP bildirimleri** (son analizden bu yana):
- `kap-1636626` · 2026-07-24 15:17 · önem: orta — Özel Durum Açıklaması (Genel) — İhracat Faaliyeti Hk
- `kap-1636624` · 2026-07-24 15:17 · önem: orta — Özel Durum Açıklaması (Genel) — Bilgilendirme
- `kap-1622675` · 2026-07-01 15:13 · önem: orta — Özel Durum Açıklaması (Genel) — İhracat Faaliyeti Hk
- `kap-1622085` · 2026-06-30 15:21 · önem: orta — Özel Durum Açıklaması (Genel) — Süresi İçinde Kaydileştirilmeyen Paylara İlişkin Yatırımcı Tazmin Merkezi Başvuruları Hakkında Açıklama
- `kap-1621229` · 2026-06-26 16:27 · önem: orta — Özel Durum Açıklaması (Genel) — İhracat Faaliyeti Hk
- `kap-1619893` · 2026-06-23 15:05 · önem: yuksek — Özel Durum Açıklaması (Genel) — Amerika Birleşik Devletleri merkezli Amsted Rail Company, Inc. ile Ana Tedarik ve Yeniden Satış Sözleşmesi İmzalanması
- `kap-1619892` · 2026-06-23 15:02 · önem: orta — Özel Durum Açıklaması (Genel) — Satış Duyurusu Hk.
- `kap-1618845` · 2026-06-19 06:38 · önem: orta — Özel Durum Açıklaması (Genel) — İhracat Faaliyeti Hk.

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `KRDMD-2026-07-29-A` | dogrudan | 42.1–42.32 | 39.64 | 47.0 (1.75) | 6.32 |
| `KRDMD-2026-07-29-B` | sma20_geri_cekilme | 40.14–40.96 | 37.64 | 47.0 (1.82) | 4.93 |

### PETKM · kimya
Kapanış **20.06** (-0.99% günlük) · 52h 16.12–28.06
RSI 46.34 · ATR 0.90 (4.49%) · ADX 22.42 · SMA20 20.23 / SMA50 20.90 / SMA200 19.32

**KAP bildirimleri** (son analizden bu yana):
- `kap-1630457` · 2026-07-09 08:22 · önem: orta — Özel Durum Açıklaması (Genel) — Master Plan Hakkında Gelişmeler
- `kap-1625474` · 2026-07-06 16:28 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1625473` · 2026-07-06 16:28 · önem: orta — Özel Durum Açıklaması (Genel) — Yeni atama hakkında
- `kap-1614115` · 2026-06-05 16:26 · önem: orta — Özel Durum Açıklaması (Genel) — Yatırımcı Tazmin Merkezine Başvuru Süresi Hakkında Duyuru
- `kap-1614114` · 2026-06-05 16:26 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1612151` · 2026-06-02 15:16 · önem: yuksek — Özel Durum Açıklaması (Genel) — Kolaylaştırılmış Birleşme Nedeniyle Çoğunluk Doğrudan Hissedar Değişikliği
- `kap-1612150` · 2026-06-02 15:16 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1608927` · 2026-05-20 10:31 · önem: yuksek — Esas Sözleşme — Esas Sözleşme

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### SISE · cam_sanayi
Kapanış **42.32** (-0.47% günlük) · 52h 32.44–54.10
RSI 40.69 · ATR 1.26 (2.97%) · ADX 15.41 · SMA20 43.49 / SMA50 44.74 / SMA200 42.45

**KAP bildirimleri** (son analizden bu yana):
- `kap-1637897` · 2026-07-28 15:19 · önem: orta — Finansal Takvim — 2026 2. Çeyrek Finansal Sonuçlarını Açıklama Tarihi
- `kap-1635667` · 2026-07-22 10:15 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1618334` · 2026-06-17 15:30 · önem: orta — Özel Durum Açıklaması (Genel) — Mersin Tarsus Kaplamalı Cam Hattı Yatırımının Tamamlanması
- `kap-1615630` · 2026-06-10 05:59 · önem: orta — Özel Durum Açıklaması (Genel) — Süresi İçinde Kaydileştirilmeyen Paylarla İlgili Yatırımcı Tazmin Merkezi Başvuruları Hakkında Duyuru
- `kap-1614642` · 2026-06-08 13:02 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1613678` · 2026-06-05 11:38 · önem: orta — Özel Durum Açıklaması (Genel) — Yönetici Sorumluluk Sigortası
- `kap-1611022` · 2026-05-25 12:28 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1610722` · 2026-05-22 15:32 · önem: orta — Özel Durum Açıklaması (Genel) — ABD Stockton Liman Projesinin Sonlandırılması

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### TAVHL · ulasim
Kapanış **273.5** (2.05% günlük) · 52h 217.60–369.00
RSI 53.01 · ATR 9.39 (3.43%) · ADX 13.06 · SMA20 268.86 / SMA50 270.45 / SMA200 291.62

**KAP bildirimleri** (son analizden bu yana):
- `kap-1637985` · 2026-07-28 16:17 · önem: orta — Özel Durum Açıklaması (Genel) — 2026/6A Finansallar Hk.
- `kap-1637984` · 2026-07-28 16:17 · önem: orta — Finansal Duran Varlık Edinimi — Almatı Havalimanı Hisse Alımı
- `kap-1637982` · 2026-07-28 16:15 · önem: orta — Geleceğe Dönük Değerlendirmeler — 2026 Beklentileri
- `kap-1637974` · 2026-07-28 16:05 · önem: orta — Sorumluluk Beyanı (Konsolide) — TAVHL Sorumluluk Beyanı
- `kap-1637971` · 2026-07-28 16:05 · önem: dusuk — Faaliyet Raporu (Konsolide) — TAVHL Faaliyet Raporu
- `kap-1637970` · 2026-07-28 16:04 · önem: yuksek — Finansal Rapor
- `kap-1632386` · 2026-07-13 09:27 · önem: orta — Özel Durum Açıklaması (Genel) — Yatırımcı Bülteni (Haziran 2026)
- `kap-1630730` · 2026-07-09 12:13 · önem: orta — Finansal Takvim — 2026 İkinci Çeyrek Finansal Takvimi

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 3 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### TCELL · telekom
Kapanış **101.9** (0.20% günlük) · 52h 87.05–129.60
RSI 37.41 · ATR 3.19 (3.13%) · ADX 18.91 · SMA20 107.25 / SMA50 108.28 / SMA200 106.98

**KAP bildirimleri** (son analizden bu yana):
- `kap-1636239` · 2026-07-23 15:25 · önem: orta — Finansal Takvim — 2. Çeyrek 2026 Finansal Sonuç Açıklaması Takvimi
- `kap-1620406` · 2026-06-24 16:30 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — TRFTCEL62621 Finansman Bonosu İtfası
- `kap-1620405` · 2026-06-24 16:30 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — TRFTCEL62613 Finansman Bonosu İtfası
- `kap-1620134` · 2026-06-24 10:10 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — Finansman Bonosu İhracı
- `kap-1620133` · 2026-06-24 10:08 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — Finansman Bonosu İhracı
- `kap-1619746` · 2026-06-23 11:28 · önem: orta — İhraç Belgesi — Yurt İçinde Borçlanma Aracı İhracına İlişkin SPK Onayı
- `kap-1619362` · 2026-06-22 13:32 · önem: orta — İhraç Tavanına İlişkin Bildirim — Yurt İçinde Borçlanma Aracı İhracına İlişkin SPK Onayı
- `kap-1619301` · 2026-06-22 10:00 · önem: yuksek — Özel Durum Açıklaması (Genel) — Uzun Vadeli Kredi Sözleşmesine İlişkin Güncelleme

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### THYAO · ulasim
Kapanış **316.75** (-0.71% günlük) · 52h 262.75–355.50
RSI 44.95 · ATR 9.08 (2.87%) · ADX 16.45 · SMA20 328.49 / SMA50 316.30 / SMA200 300.68

**KAP bildirimleri** (son analizden bu yana):
- `kap-1630629` · 2026-07-09 11:19 · önem: orta — Kredi Derecelendirmesi — Fitch Kredi Derecelendirme Notu
- `kap-1629952` · 2026-07-08 16:07 · önem: orta — Özel Durum Açıklaması (Genel) — Haziran 2026 Trafik Sonuçları
- `kap-1622775` · 2026-07-02 06:32 · önem: orta — Kredi Derecelendirmesi — Moody's Kredi Derecelendirme Notu
- `kap-1617478` · 2026-06-15 17:09 · önem: orta — Özel Durum Açıklaması (Genel) — Yeni Hat Açılışı
- `kap-1615692` · 2026-06-10 07:13 · önem: orta — Özel Durum Açıklaması (Genel) — Mayıs 2026 Trafik Sonuçları
- `kap-1615687` · 2026-06-10 07:10 · önem: orta — Özel Durum Açıklaması (Genel) — Süresi İçinde Kaydileştirilmeyen Paylarla İlgili Yatırımcı Tazmin Merkezi Başvuruları Hakkında Duyuru
- `kap-1613157` · 2026-06-04 12:53 · önem: orta — Özel Durum Açıklaması (Genel) — Air Europa Yatırım Süreci Güncellemesi - 5
- `kap-1603784` · 2026-05-08 17:39 · önem: orta — Özel Durum Açıklaması (Genel) — Nisan 2026 Trafik Sonuçları

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### TUPRS · rafineri
Kapanış **300.5** (2.39% günlük) · 52h 159.20–320.25
RSI 67.44 · ATR 9.76 (3.25%) · ADX 48.24 · SMA20 278.38 / SMA50 251.92 / SMA200 228.53

**KAP bildirimleri** (son analizden bu yana):
- `kap-1638082` · 2026-07-29 06:53 · önem: orta — Kredi Derecelendirmesi — Moody's Kredi Derecelendirme Notu
- `kap-1635135` · 2026-07-20 15:16 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — TRSTPRS72614 ISIN Kodlu Tahvilin 8. Kupon Ödemesi ve İtfası
- `kap-1634755` · 2026-07-20 05:25 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — TRSTPRS72614 ISIN Kodlu Tahvilin 8. Kupon Faiz Oranının Belirlenmesi
- `kap-1632022` · 2026-07-10 15:16 · önem: orta — Finansal Takvim — 2026 2. Çeyrek Finansal Takvim
- `kap-1617405` · 2026-06-15 15:16 · önem: orta — Özel Durum Açıklaması (Genel) — Süresi İçinde Kaydileştirilmeyen Paylara İlişkin Yatırımcı Tazmin Merkezi Başvuruları Hakkında Açıklama
- `kap-1605173` · 2026-05-11 15:22 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — TRSTPRS82613 ISIN Kodlu Tahvilin 7. Kupon Ödemesi
- `kap-1603965` · 2026-05-11 05:24 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — TRSTPRS82613 ISIN Kodlu Tahvilin 7. Kupon Faiz Oranının Belirlenmesi
- `kap-1603566` · 2026-05-08 15:15 · önem: orta — Şirket Genel Bilgi Formu

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `TUPRS-2026-07-29-A` | sma20_geri_cekilme | 275.5–281.25 | 261.5 | 320.25 (1.97) | 5.7 |
| `TUPRS-2026-07-29-B` | destek_retest | 278.0–283.75 | 264.0 | 320.25 (1.85) | 5.75 |
