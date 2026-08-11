# Değerlendirme Raporu — 2026-08-11

> Bu bir karar destek aracıdır, yatırım tavsiyesi değildir. Kişisel ve deneysel kullanım içindir. Ölçülen kenar zayıftır ve istatistiksel olarak doğrulanması yıllar alır (bkz. required_n).

Kaynak: `replay` · yılda ~13 bağımsız dönem üretiliyor

## Ana metrikler

| Metrik | N | değer | t | gerekli N | **HÜKÜM** |
|---|---|---|---|---|---|
| Eşleştirilmiş alfa (vs EW) | 13 | 4.27pp | 2.19 | 11 | **ölçüm yetersiz (N=13)** |
| Dönem-içi IC (tüm kesit) | 16 | 0.069 | 1.59 | 26 | **kenar yok** |
| LLM katkısı (IC farkı) | 0 | — | — | — | **ölçüm yok** |

`gerekli N` = t=2'ye ulaşmak için gereken **bağımsız dönem** sayısı. Yıla çevirmek için 13'e böl.

XU100'e göre alfa 3.77pp — **karar için kullanılmaz**, sermaye-ağırlık eğilimi içerir (ADR #002).

## Uygulanabilirlik (en hızlı ölçülen)

- **Slippage** (planlanan giriş vs gerçekleşen dolum): ort -0.088% · N=13
- **Tetiklenmeme oranı:** %35.0 (7/20 plan hiç dolmadı)

## Sonuç ve hata dağılımı

| Sonuç | n |   | Hata etiketi | n |
|---|---|---|---|---|
| giris_olmadi | 7 |  | tetiklenmedi | 7 |
| sure | 5 |  | sure_pozitif | 5 |
| hedef | 4 |  | hedef | 4 |
| stop | 4 |  | stop | 2 |
|  |  |  | hizli_stop | 2 |

## Güven kalibrasyonu (Brier)

Brier skoru: 0.2751 · N=13 · **ölçüm yetersiz (N=13)**

| Güven | n | iddia edilen | gerçekleşen |
|---|---|---|---|
| orta | 7 | 0.50 | 0.71 |
| dusuk | 6 | 0.38 | 0.67 |

> Kova başına ~30-50 çözülmüş tahmin gerekir; bu 2+ yıl demektir.

## Rejim boyutlandırması işe yarıyor mu?

Portföy katkısı farkı: -0.221pp · N=13 · t=-2.51 · **ölçüm yetersiz (N=13)**

> Birim: portföy yüzde PUANI (hisse getirisi değil). Pozitif = rejimin kırptığı pozisyonlar zarar etmiş (boyutlandırma işe yaramış); negatif = kırpılanlar kazanmış (boyutlandırma kenar yiyor). Referans boyut: `risk.maks_pozisyon_pct`.

_Bu satır uzun süre TANIM GEREĞİ sıfırdı (`ret_pct_equal_size` kolonu `ret_pct`'in kopyasıydı), yani rejim katmanı ölçülüyor görünüp hiç ölçülmüyordu — 2026-07-27 denetiminde düzeltildi (ADR #009)._

## Veto

- Veto sayısı: 0
- Seçilenlerin ortalama alfası: 4.27pp
> Veto edilen isimlerin sonraki getirisi ölçülemez — veto edildikleri için plan açılmadı. Ölçüm için vetolananların PLANSIZ ileri getirisi ayrıca izlenmeli (Faz 7 backlog).

---

### Bu raporun okunma kuralları

- **`ölçüm yetersiz` bir sonuçtur, bir eksiklik değil.** Yanındaki büyük yüzde bir bulgu DEĞİLDİR.
- **Hüküm daima eşit-ağırlık evrene göre.** XU100 satırı bilgi içindir.
- **En güçlü ifade `zayıf kanıt`tır.** Bu sistemde "doğrulandı" YOKTUR.
- Ağırlıklar bu rapordan DEĞİŞMEZ — o yavaş döngünün işi (ADR #004).
