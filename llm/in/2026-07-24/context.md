# Analiz Paketi — 2026-07-24

> ⚠ Ölçülen kenar yok (ADR #008). Bu seviyeler planlama geometrisidir, yön iddiası değildir.

**bundle_sha:** `7c98b97b76b461c94e9192188122129e85b0d6c3e18256c89790045d92dbbf94` — çıktına BİREBİR kopyala.

## Piyasa rejimi: **risk-off**

- XU100 SMA200 farkı: 9.70%
- Genişlik (SMA50 üstü): 32.84%
- Politika: nakit %90, maks 2 pozisyon, sektör başına maks 2

- Makro: **veri yok** (EVDS anahtarı girilmemiş) — bu satırlar uydurulmaz, gizlenir.

## Evren (18 hisse)

### AKBNK · banka
Kapanış **67.6** (0.82% günlük) · 52h 53.05–93.50
RSI 38.72 · ATR 2.13 (3.16%) · ADX 25.50 · SMA20 71.21 / SMA50 71.25 / SMA200 71.85

**KAP bildirimleri** (son analizden bu yana):
- `kap-1636133` · 2026-07-23 13:42 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — Yurtdışı Piyasalara Tahvil İhracı
- `kap-1636014` · 2026-07-23 11:21 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — Yurtdışı Piyasalara Tahvil İhracı
- `kap-1636013` · 2026-07-23 11:20 · önem: orta — İhraç Tavanına İlişkin Bildirim — Yurt İçi Borçlanma Aracı İhracı İçin Genel Müdürlüğe Yetki Verilmesi
- `kap-1636011` · 2026-07-23 11:20 · önem: orta — İhraç Tavanına İlişkin Bildirim — Yurt İçi Borçlanma Aracı İhracı İçin Genel Müdürlüğe Yetki Verilmesi
- `kap-1636010` · 2026-07-23 11:20 · önem: orta — İhraç Tavanına İlişkin Bildirim — Yurt İçi Borçlanma Aracı İhracı İçin Genel Müdürlüğe Yetki Verilmesi
- `kap-1635742` · 2026-07-22 13:17 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1634988` · 2026-07-20 13:54 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — US00971YAL48 ISIN Kodlu Tahvilin Kupon Ödemesi
- `kap-1634987` · 2026-07-20 13:53 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — XS2842188687 ISIN Kodlu Tahvilin Kupon Ödemesi

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### ASELS · savunma
Kapanış **380.25** (1.06% günlük) · 52h 167.00–450.00
RSI 53.70 · ATR 16.57 (4.36%) · ADX 15.91 · SMA20 367.80 / SMA50 381.45 / SMA200 304.99

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
| `ASELS-2026-07-24-A` | destek_retest | 349.75–357.0 | 323.75 | 412.0 (1.65) | 4.29 |

### ASTOR · elektrik_ekipman
Kapanış **297.0** (-3.26% günlük) · 52h 88.20–385.75
RSI 47.65 · ATR 17.54 (5.91%) · ADX 12.77 · SMA20 303.75 / SMA50 310.42 / SMA200 191.23

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
Kapanış **380.25** (-2.62% günlük) · 52h 241.62–425.00
RSI 49.42 · ATR 12.30 (3.23%) · ADX 20.26 · SMA20 377.64 / SMA50 381.93 / SMA200 330.37

**KAP bildirimleri** (son analizden bu yana):
- `kap-1636648` · 2026-07-24 15:48 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 24 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri
- `kap-1636283` · 2026-07-23 16:33 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 23 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri
- `kap-1635533` · 2026-07-21 17:32 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 21 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri
- `kap-1634671` · 2026-07-17 16:49 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 17 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri
- `kap-1632922` · 2026-07-13 16:16 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 13 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri
- `kap-1632046` · 2026-07-10 15:39 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 10 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri
- `kap-1631306` · 2026-07-09 17:00 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 9 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri
- `kap-1630125` · 2026-07-08 17:20 · önem: yuksek — Payların Geri Alınmasına İlişkin Bildirim — 8 Temmuz 2026 Tarihli Pay Geri Alım İşlemleri

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 3 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### EKGYO · gyo
Kapanış **18.62** (-2.87% günlük) · 52h 17.62–27.12
RSI 33.27 · ATR 0.69 (3.72%) · ADX 14.08 · SMA20 20.48 / SMA50 20.36 / SMA200 20.99

**KAP bildirimleri** (son analizden bu yana):
- `kap-1636545` · 2026-07-24 14:00 · önem: orta — Özel Durum Açıklaması (Genel) — İstanbul Eyüpsultan Göktürk 1. Etap Kesin Kabulü
- `kap-1636005` · 2026-07-23 10:57 · önem: orta — Özel Durum Açıklaması (Genel) — Konya Meram 2. Etap İhale İlanı
- `kap-1635773` · 2026-07-22 14:04 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1635409` · 2026-07-21 13:36 · önem: orta — Özel Durum Açıklaması (Genel) — İstanbul Esenler Atışalanı Kuzey 1. Etap İhalesi 2. Oturum Tarihi
- `kap-1635406` · 2026-07-21 13:35 · önem: yuksek — Özel Durum Açıklaması (Genel) — Ankara Gölbaşı Taşpınar Sözleşme İmzalanması
- `kap-1634714` · 2026-07-17 19:30 · önem: orta — Özel Durum Açıklaması (Genel) — Damla Kent Projesi Gayrimenkul Sertifikası İnşaat İlerlemesi ve Asli Edim Gerçekleşmeleri
- `kap-1634713` · 2026-07-17 19:30 · önem: orta — Değerleme Raporu — Damla Kent Gayrimenkul Değerleme Raporu
- `kap-1634712` · 2026-07-17 18:06 · önem: orta — Özel Durum Açıklaması (Genel) — 2026 2. Çeyrek Satış Raporu

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### ENKAI · insaat
Kapanış **88.8** (-1.28% günlük) · 52h 65.55–114.30
RSI 41.62 · ATR 2.40 (2.70%) · ADX 21.63 · SMA20 90.78 / SMA50 94.12 / SMA200 89.06

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
Kapanış **43.28** (-2.08% günlük) · 52h 23.46–45.10
RSI 58.24 · ATR 1.65 (3.81%) · ADX 26.98 · SMA20 41.65 / SMA50 40.37 / SMA200 30.96

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
Kapanış **100.4** (2.08% günlük) · 52h 25.50–108.60
RSI 61.31 · ATR 5.91 (5.89%) · ADX 30.30 · SMA20 89.45 / SMA50 84.56 / SMA200 47.93

**KAP bildirimleri** (son analizden bu yana):
- `kap-1632310` · 2026-07-13 07:34 · önem: orta — İhale Süreci / Sonucu — İhale Sonucu Hakkında
- `kap-1621602` · 2026-06-29 15:11 · önem: yuksek — Esas Sözleşme — Güncel Esas Sözleşme Hak.
- `kap-1621159` · 2026-06-26 15:02 · önem: orta — Bağımsız Denetim Kuruluşunun Belirlenmesi — Bağımsız Denetim Kuruluşunun Tescili
- `kap-1621154` · 2026-06-26 14:54 · önem: yuksek — Kayıtlı Sermaye Tavanı İşlemlerine İlişkin Bildirim — Kayıtlı Sermaye Tavanı Esas Sözleşme Madde Tadilinin Tescili Hakkında
- `kap-1621146` · 2026-06-26 14:49 · önem: orta — Genel Kurul İşlemlerine İlişkin Bildirim — 2025 Yılı Olağan Genel Kurul Kararlarının Tescili Hakkında
- `kap-1619903` · 2026-06-23 15:11 · önem: orta — Özel Durum Açıklaması (Genel) — Kurumsal yatırımcılara hızlandırılmış talep toplama yöntemiyle yapılan satışın takasının tamamlanması
- `kap-1618962` · 2026-06-19 11:12 · önem: orta — İhale Süreci / Sonucu — İhale Sonucu Hakkında
- `kap-1618961` · 2026-06-19 11:11 · önem: orta — Kayıtlı Sermaye Tavanı İşlemlerine İlişkin Bildirim — Kayıtlı Sermaye Tavan Artırımı İçin Genel Kurul Onayı Hakkında

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `EUPWR-2026-07-24-A` | sma20_geri_cekilme | 88.55–90.35 | 78.5 | 108.6 (1.54) | 1.52 |

### FROTO · otomotiv
Kapanış **79.0** (-0.50% günlük) · 52h 78.45–135.40
RSI 34.17 · ATR 2.04 (2.58%) · ADX 40.61 · SMA20 82.58 / SMA50 86.25 / SMA200 98.45

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
Kapanış **126.0** (0.80% günlük) · 52h 115.40–169.70
RSI 39.24 · ATR 3.39 (2.69%) · ADX 20.48 · SMA20 130.92 / SMA50 131.84 / SMA200 138.02

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
Kapanış **197.6** (-0.30% günlük) · 52h 146.00–229.10
RSI 53.37 · ATR 5.18 (2.62%) · ADX 21.31 · SMA20 194.14 / SMA50 193.96 / SMA200 188.57

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
Kapanış **42.2** (0.09% günlük) · 52h 23.50–47.00
RSI 56.72 · ATR 1.80 (4.27%) · ADX 19.16 · SMA20 40.22 / SMA50 40.34 / SMA200 32.15

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
| `KRDMD-2026-07-24-A` | sma20_geri_cekilme | 39.8–40.64 | 37.02 | 47.0 (1.76) | 4.49 |

### PETKM · kimya
Kapanış **22.02** (-2.39% günlük) · 52h 16.12–28.06
RSI 59.54 · ATR 0.86 (3.92%) · ADX 26.96 · SMA20 20.10 / SMA50 21.29 / SMA200 19.31

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
_Plan yok: 3 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### SISE · cam_sanayi
Kapanış **43.42** (-0.60% günlük) · 52h 32.44–54.10
RSI 45.89 · ATR 1.31 (3.01%) · ADX 16.34 · SMA20 43.83 / SMA50 45.27 / SMA200 42.34

**KAP bildirimleri** (son analizden bu yana):
- `kap-1635667` · 2026-07-22 10:15 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1618334` · 2026-06-17 15:30 · önem: orta — Özel Durum Açıklaması (Genel) — Mersin Tarsus Kaplamalı Cam Hattı Yatırımının Tamamlanması
- `kap-1615630` · 2026-06-10 05:59 · önem: orta — Özel Durum Açıklaması (Genel) — Süresi İçinde Kaydileştirilmeyen Paylarla İlgili Yatırımcı Tazmin Merkezi Başvuruları Hakkında Duyuru
- `kap-1614642` · 2026-06-08 13:02 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1613678` · 2026-06-05 11:38 · önem: orta — Özel Durum Açıklaması (Genel) — Yönetici Sorumluluk Sigortası
- `kap-1611022` · 2026-05-25 12:28 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1610722` · 2026-05-22 15:32 · önem: orta — Özel Durum Açıklaması (Genel) — ABD Stockton Liman Projesinin Sonlandırılması
- `kap-1610703` · 2026-05-22 15:23 · önem: dusuk — Sürdürülebilirlik Raporu — TSRS Uyumlu 2025 Sürdürülebilirlik Raporu

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### TAVHL · ulasim
Kapanış **259.5** (0.10% günlük) · 52h 217.60–369.00
RSI 42.08 · ATR 9.46 (3.65%) · ADX 15.18 · SMA20 271.01 / SMA50 270.62 / SMA200 291.11

**KAP bildirimleri** (son analizden bu yana):
- `kap-1632386` · 2026-07-13 09:27 · önem: orta — Özel Durum Açıklaması (Genel) — Yatırımcı Bülteni (Haziran 2026)
- `kap-1630730` · 2026-07-09 12:13 · önem: orta — Finansal Takvim — 2026 İkinci Çeyrek Finansal Takvimi
- `kap-1615275` · 2026-06-09 10:55 · önem: orta — Özel Durum Açıklaması (Genel) — Yatırımcı Bülteni (Mayıs 2026)
- `kap-1614665` · 2026-06-08 13:06 · önem: orta — İhale Süreci / Sonucu — Kuveyt Uluslararası Havalimanı Terminal 2 İşletme ve Bakım Hizmeti İhalesi
- `kap-1614251` · 2026-06-08 07:12 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — Yurt Dışı Tahvil 5. Kupon Ödemesi
- `kap-1606680` · 2026-05-13 11:13 · önem: dusuk — TSRS Uyumlu Sürdürülebilirlik Raporu — 2025 Raporu
- `kap-1604678` · 2026-05-11 13:21 · önem: orta — Özel Durum Açıklaması (Genel) — Yatırımcı Bülteni (Nisan 2026)

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### TCELL · telekom
Kapanış **103.7** (-1.24% günlük) · 52h 87.05–129.60
RSI 39.87 · ATR 3.43 (3.31%) · ADX 14.63 · SMA20 108.35 / SMA50 109.18 / SMA200 106.94

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
Kapanış **312.0** (-0.24% günlük) · 52h 262.75–355.50
RSI 40.85 · ATR 8.84 (2.83%) · ADX 19.94 · SMA20 330.09 / SMA50 315.59 / SMA200 300.56

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
Kapanış **304.25** (-3.26% günlük) · 52h 159.20–320.25
RSI 74.50 · ATR 9.41 (3.09%) · ADX 50.97 · SMA20 267.37 / SMA50 249.50 / SMA200 226.81

**KAP bildirimleri** (son analizden bu yana):
- `kap-1635135` · 2026-07-20 15:16 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — TRSTPRS72614 ISIN Kodlu Tahvilin 8. Kupon Ödemesi ve İtfası
- `kap-1634755` · 2026-07-20 05:25 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — TRSTPRS72614 ISIN Kodlu Tahvilin 8. Kupon Faiz Oranının Belirlenmesi
- `kap-1632022` · 2026-07-10 15:16 · önem: orta — Finansal Takvim — 2026 2. Çeyrek Finansal Takvim
- `kap-1617405` · 2026-06-15 15:16 · önem: orta — Özel Durum Açıklaması (Genel) — Süresi İçinde Kaydileştirilmeyen Paylara İlişkin Yatırımcı Tazmin Merkezi Başvuruları Hakkında Açıklama
- `kap-1605173` · 2026-05-11 15:22 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — TRSTPRS82613 ISIN Kodlu Tahvilin 7. Kupon Ödemesi
- `kap-1603965` · 2026-05-11 05:24 · önem: orta — Pay Dışında Sermaye Piyasası Aracı İşlemlerine İlişkin Bildirim (Faiz İçeren) — TRSTPRS82613 ISIN Kodlu Tahvilin 7. Kupon Faiz Oranının Belirlenmesi
- `kap-1603566` · 2026-05-08 15:15 · önem: orta — Şirket Genel Bilgi Formu
- `kap-1603560` · 2026-05-08 15:15 · önem: orta — Özel Durum Açıklaması (Genel) — Yatırımcı İlişkileri ve Kurumsal Risk Grup Direktörü Ataması

_Önem etiketi HEURİSTİKTİR, ölçülmedi; hiçbir hesaba girmez._

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `TUPRS-2026-07-24-A` | destek_retest | 277.25–283.0 | 264.0 | 320.25 (1.96) | 5.96 |
