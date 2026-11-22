# Değerlendirme Raporu — 2026-11-22

> Bu bir karar destek aracıdır, yatırım tavsiyesi değildir. Kişisel ve deneysel kullanım içindir. Ölçülen kenar zayıftır ve istatistiksel olarak doğrulanması yıllar alır (bkz. required_n).

Kaynak: `gemini-3.6-flash` · yılda ~13 bağımsız dönem üretiliyor

## Ana metrikler

| Metrik | N | değer | t | gerekli N | **HÜKÜM** |
|---|---|---|---|---|---|
| Eşleştirilmiş alfa (vs EW) | 7 | 5.36pp | 1.65 | 11 | **ölçüm yetersiz (N=7)** |
| ↳ **örtüşme ayıklanmış** | 6 | 4.30pp | 1.19 | — | **ölçüm yetersiz (N=6)** |
| ↳ karar başına (girmeyenler 0) | 7 | 5.36pp | — | — | — |
| Dönem-içi IC (tüm kesit) | 6 | 0.122 | 2.17 | 6 | **ölçüm yetersiz (N=6)** |
| LLM katkısı (IC farkı) | 5 | 0.272 | 1.76 | 7 | **ölçüm yetersiz (N=5)** |

`gerekli N` = t=2'ye ulaşmak için gereken **bağımsız dönem** sayısı. Yıla çevirmek için 13'e böl.

> ⚠ **1 kayıt örtüşüyor**: aynı isim art arda seçilince AYNI İŞLEM birden çok satır olur ve bağımsız gözlem gibi sayılır. Ölçüldü (2026-08-15): `TUPRS` iki ayrı tahminden aynı gün girip aynı gün çıkmıştı. Örtüşen gözlem yalnız ortalamayı değil `t`'yi de ŞİŞİRİR — hüküm daima **örtüşme ayıklanmış** satıra göre okunmalı.

XU100'e göre alfa 5.97pp — **karar için kullanılmaz**, sermaye-ağırlık eğilimi içerir (ADR #002).

## Uygulanabilirlik (en hızlı ölçülen)

- **Slippage** (planlanan giriş vs gerçekleşen dolum): ort -0.085% · N=7
- **Tetiklenmeme oranı:** %0.0 (0/7 plan hiç dolmadı)

## Sonuç ve hata dağılımı

| Sonuç | n |   | Hata etiketi | n |
|---|---|---|---|---|
| hedef | 4 |  | hedef | 4 |
| stop | 3 |  | hizli_stop | 2 |
|  |  |  | stop | 1 |

## Güven kalibrasyonu (Brier)

Brier skoru: 0.2500 · N=7 · **ölçüm yetersiz (N=7)**

| Güven | n | iddia edilen | gerçekleşen |
|---|---|---|---|
| orta | 7 | 0.50 | 0.57 |

> Kova başına ~30-50 çözülmüş tahmin gerekir; bu 2+ yıl demektir.

## Rejim boyutlandırması işe yarıyor mu?

Portföy katkısı farkı: -0.301pp · N=7 · t=-1.64 · **ölçüm yetersiz (N=7)**

> Birim: portföy yüzde PUANI (hisse getirisi değil). Pozitif = rejimin kırptığı pozisyonlar zarar etmiş (boyutlandırma işe yaramış); negatif = kırpılanlar kazanmış (boyutlandırma kenar yiyor). Referans boyut: `risk.maks_pozisyon_pct`.

_Bu satır uzun süre TANIM GEREĞİ sıfırdı (`ret_pct_equal_size` kolonu `ret_pct`'in kopyasıydı), yani rejim katmanı ölçülüyor görünüp hiç ölçülmüyordu — 2026-07-27 denetiminde düzeltildi (ADR #009)._

## Veto — analistin en ölçülebilir katkısı

- Veto sayısı: **27** — {'rejim_uyumsuz': 18, 'tez_zayif': 7, 'veri_supheli': 1, 'haber_riski': 1} · ufku dolan ve ÖLÇÜLEN: 27

| | ortalama plansız alfa |
|---|---|
| Vetolananlar | -1.10pp |
| Seçilenler | 13.72pp |
| **Fark** | **-14.83pp** — ölçüm yetersiz (N=7) |

> Birim: yüzde puan, PLANSIZ ileri getiri (H=ana_ufuk_gun), EW tabana göre. **Fark POZİTİFSE veto ZARAR veriyor** — elenen isimler seçilenleri geçmiş demektir. Vetolananların planı açılmadığı için ikisi de plansız ölçülür; aksi hâlde farklı ölçekler kıyaslanırdı.

_Bu satır 2026-08-16'ya kadar TANIM GEREĞİ boştu: kaynak sorgusu `outcomes` ile INNER JOIN yapıyordu ve veto edilen tahminin planı açılmadığı için outcome'u da yoktu — yani ölçüm kendi konusunu eliyordu. 17 veto varken karne `0` diyordu (2026-08-15 denetimi)._

---

### Bu raporun okunma kuralları

- **`ölçüm yetersiz` bir sonuçtur, bir eksiklik değil.** Yanındaki büyük yüzde bir bulgu DEĞİLDİR.
- **Hüküm daima eşit-ağırlık evrene göre.** XU100 satırı bilgi içindir.
- **En güçlü ifade `zayıf kanıt`tır.** Bu sistemde "doğrulandı" YOKTUR.
- Ağırlıklar bu rapordan DEĞİŞMEZ — o yavaş döngünün işi (ADR #004).
