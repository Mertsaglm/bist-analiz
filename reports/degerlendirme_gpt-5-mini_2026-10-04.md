# Değerlendirme Raporu — 2026-10-04

> Bu bir karar destek aracıdır, yatırım tavsiyesi değildir. Kişisel ve deneysel kullanım içindir. Ölçülen kenar zayıftır ve istatistiksel olarak doğrulanması yıllar alır (bkz. required_n).

Kaynak: `gpt-5-mini` · yılda ~13 bağımsız dönem üretiliyor

## Ana metrikler

| Metrik | N | değer | t | gerekli N | **HÜKÜM** |
|---|---|---|---|---|---|
| Eşleştirilmiş alfa (vs EW) | 2 | 6.15pp | 2.51 | 2 | **ölçüm yetersiz (N=2)** |
| ↳ **örtüşme ayıklanmış** | 2 | 6.15pp | 2.51 | — | **ölçüm yetersiz (N=2)** |
| ↳ karar başına (girmeyenler 0) | 2 | 6.15pp | — | — | — |
| Dönem-içi IC (tüm kesit) | 1 | 0.061 | — | — | **ölçüm yok** |
| LLM katkısı (IC farkı) | 1 | -0.117 | — | — | **ölçüm yok** |

`gerekli N` = t=2'ye ulaşmak için gereken **bağımsız dönem** sayısı. Yıla çevirmek için 13'e böl.

XU100'e göre alfa 4.16pp — **karar için kullanılmaz**, sermaye-ağırlık eğilimi içerir (ADR #002).

## Uygulanabilirlik (en hızlı ölçülen)

- **Slippage** (planlanan giriş vs gerçekleşen dolum): ort -0.032% · N=2
- **Tetiklenmeme oranı:** %0.0 (0/2 plan hiç dolmadı)

## Sonuç ve hata dağılımı

| Sonuç | n |   | Hata etiketi | n |
|---|---|---|---|---|
| sure | 1 |  | sure_pozitif | 1 |
| hedef | 1 |  | hedef | 1 |

## Güven kalibrasyonu (Brier)

Brier skoru: 0.2500 · N=2 · **ölçüm yetersiz (N=2)**

| Güven | n | iddia edilen | gerçekleşen |
|---|---|---|---|
| orta | 2 | 0.50 | 1.00 |

> Kova başına ~30-50 çözülmüş tahmin gerekir; bu 2+ yıl demektir.

## Rejim boyutlandırması işe yarıyor mu?

Portföy katkısı farkı: -0.403pp · N=2 · t=-1.95 · **ölçüm yetersiz (N=2)**

> Birim: portföy yüzde PUANI (hisse getirisi değil). Pozitif = rejimin kırptığı pozisyonlar zarar etmiş (boyutlandırma işe yaramış); negatif = kırpılanlar kazanmış (boyutlandırma kenar yiyor). Referans boyut: `risk.maks_pozisyon_pct`.

_Bu satır uzun süre TANIM GEREĞİ sıfırdı (`ret_pct_equal_size` kolonu `ret_pct`'in kopyasıydı), yani rejim katmanı ölçülüyor görünüp hiç ölçülmüyordu — 2026-07-27 denetiminde düzeltildi (ADR #009)._

## Veto — analistin en ölçülebilir katkısı

- Veto sayısı: **12** — {'rejim_uyumsuz': 9, 'tez_zayif': 3} · ufku dolan ve ÖLÇÜLEN: 0

| | ortalama plansız alfa |
|---|---|
| Vetolananlar | — |
| Seçilenler | 3.10pp |
| **Fark** | **—** — ölçüm yok |

> Birim: yüzde puan, PLANSIZ ileri getiri (H=ana_ufuk_gun), EW tabana göre. **Fark POZİTİFSE veto ZARAR veriyor** — elenen isimler seçilenleri geçmiş demektir. Vetolananların planı açılmadığı için ikisi de plansız ölçülür; aksi hâlde farklı ölçekler kıyaslanırdı.

_Bu satır 2026-08-16'ya kadar TANIM GEREĞİ boştu: kaynak sorgusu `outcomes` ile INNER JOIN yapıyordu ve veto edilen tahminin planı açılmadığı için outcome'u da yoktu — yani ölçüm kendi konusunu eliyordu. 17 veto varken karne `0` diyordu (2026-08-15 denetimi)._

---

### Bu raporun okunma kuralları

- **`ölçüm yetersiz` bir sonuçtur, bir eksiklik değil.** Yanındaki büyük yüzde bir bulgu DEĞİLDİR.
- **Hüküm daima eşit-ağırlık evrene göre.** XU100 satırı bilgi içindir.
- **En güçlü ifade `zayıf kanıt`tır.** Bu sistemde "doğrulandı" YOKTUR.
- Ağırlıklar bu rapordan DEĞİŞMEZ — o yavaş döngünün işi (ADR #004).
