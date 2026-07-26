# Ön Kayıt — Revizyon Turu #1

**Yazıldığı an:** 2026-07-26, teşhis raporundan SONRA, revizyon koşusundan ÖNCE.
**Dayanak:** `reports/teshis_2026-07-26.md`, `ai/DECISIONS.md #007`

Bu dosya koşudan önce yazıldı ve sonrasında DEĞİŞTİRİLMEYECEK. Sonucu gördükten
sonra kriter gevşetilirse ölçüm değersizdir; bu dosya o gevşetmeyi imkânsız kılar.

---

## 1. Teşhisin söylediği (hipotez buradan geliyor, sezgiden değil)

| Ölçüm | popülasyon | IC | t |
|---|---|---|---|
| `ic_tum` | kapısız tüm kesit | 0.042 | **2.42** |
| `ic_uygun` | SMA200 kapısından geçen havuz | 0.009 | **0.20** |

**Sıralama bilgisinin %79'u kapıda kayboluyor.** Ayrışma bir kurgu hatası değil:
seçim yönü tutarlılığı %96, sentetik testlerde harness mükemmel momentumda IC≈1,
ters sinyalde IC≈−1 üretiyor. Enstrüman sağlam.

Kapısız, tüm kesit, ufka göre (teşhis §3):

| H | N | IC | t(IC) | alfa vs EW | t |
|---|---|---|---|---|---|
| 5 | 525 | 0.024 | 2.88 | −0.10pp | −1.71 |
| 10 | 262 | 0.027 | 2.28 | +0.07pp | 0.62 |
| 20 | 131 | 0.042 | 2.42 | +0.29pp | 1.17 |
| 42 | 62 | 0.065 | 2.61 | +1.60pp | 2.56 |
| 63 | 41 | 0.064 | 2.21 | +1.47pp | 1.78 |

IC ufukla **monoton** artıyor ve t(IC) beş ufkun HEPSİNDE ≥2.2. Tek şanslı hücre
değil, doz-cevap ilişkisi — şansa bağlı olma olasılığı tek hücreye göre çok düşük.

Ayrıca fark edilen kurulum hatası: `config.faktorler.high52_min_ufuk_gun = 21`
ve ana ufuk H=20 idi → **en güçlü faktörün ağırlığı sıfırlanmıştı**
(`high52_prox`: IC 0.059 t=3.38, OOS IC 0.091 t=**2.49** — OOS'ta t>2 tutan tek faktör).

## 2. Hipotez

> Referans kurulumun başarısızlığı sıralama bilgisinin yokluğundan değil,
> uygulamadan kaynaklanıyor: (a) SMA200 kapısı skorun sıralayacağı varyansı
> kesip atıyor, (b) H=20 sinyalin henüz getiriye dönüşmediği ufuk.

## 3. Değişecek olanlar — YALNIZ İKİSİ

1. **SMA200 kapısı skorlama yolundan kaldırılır.** Likidite ve veri-kalitesi
   kapıları KALIR (onlar bilgi değil, uygulanabilirlik kapısı).
2. **Ana ufuk H=20 → H=42.**

İkisi birlikte test ediliyor çünkü BAĞIMSIZ DEĞİLLER: H=42 aynı zamanda
`high52_prox`'un ağırlığını sıfırdan çıkarıyor. Yorumlanabilirlik için tek-kol
OOS katkıları AYRICA raporlanacak.

## 4. Değişmeyecek olanlar — açıkça

- Faktör seti (3+1) ve ağırlıklar: **aynı**
- Maliyet: %0.30 gidiş-dönüş, yalnız seçilen portföye
- Taban çizgisi: eşit-ağırlık uygun evren (XU100 değil)
- Ölçüm evreni: 67 isim · OOS bölme: 2023-01-01
- Seçim genişliği: üst 1/3
- Örtüşmeyen pencere, giriş t+1
- **Kısa vadeli tersine dönüş TEST EDİLMEYECEK.** Bu bir düzeltme değil YENİ
  HİPOTEZ ve teşhis onu desteklemiyor: kısa ufukta IC pozitif (+0.024, t=2.88),
  yani tersine dönüş değil momentum yönünde. Mekanik düzeltmelerle aynı pakete
  konması ikisini de yorumlanamaz kılardı.

## 5. Karar kuralı — SONUCU GÖRMEDEN yazıldı

**Geçme şartı:** OOS'ta, eşit-ağırlık tabana göre alfa **pozitif `zayıf kanıt`**
üretmeli — projenin kendi `edge_verdict` çıtası:

```
N ≥ 15  VE  |Δ| ≥ 1.0pp  VE  işaret POZİTİF
```

`t > 1.65` gibi gevşetilmiş bir eşik **kullanılmayacak**. Başarısızlığı gördükten
sonra çıtayı indirmek, bu projede yasaklanmış tek hareket.

**İkincil (karar vermez, teşhise girer):** OOS `ic_tum` t ≥ 2.0.

## 6. Başarısızlık halinde

İkinci tur **YOK**. Doğrudan yeniden çerçeveleme: sistem "izleme + risk disiplini
+ haber/veto aracı" olarak tamamlanır, kenar iddia etmez, seviyeleri planlama
geometrisi olarak sunar. Faz 3-6 yine kurulur; değişen tek şey çıktının DİLİDİR.

## 7. Çoklu test muhasebesi

Teşhis adımında 24 karşılaştırma yapıldı. Bu tur **1 ön kayıtlı konfigürasyon**
ekliyor. Rapor `bonferroni_note` taşıyacak ve teşhis sayısı ayrıca yazılacak —
"teşhis bedava" gibi davranılmayacak.
