# Değerlendirme Raporu — 2026-09-06

> Bu bir karar destek aracıdır, yatırım tavsiyesi değildir. Kişisel ve deneysel kullanım içindir. Ölçülen kenar zayıftır ve istatistiksel olarak doğrulanması yıllar alır (bkz. required_n).

Kaynak: `gemini-3.5-flash` · yılda ~13 bağımsız dönem üretiliyor

## Ana metrikler

| Metrik | N | değer | t | gerekli N | **HÜKÜM** |
|---|---|---|---|---|---|
| Eşleştirilmiş alfa (vs EW) | 4 | 8.02pp | 1.85 | 5 | **ölçüm yetersiz (N=4)** |
| ↳ **örtüşme ayıklanmış** | 4 | 8.02pp | 1.85 | — | **ölçüm yetersiz (N=4)** |
| ↳ karar başına (girmeyenler 0) | 4 | 8.02pp | — | — | — |
| Dönem-içi IC (tüm kesit) | 0 | — | — | — | **ölçüm yok** |
| LLM katkısı (IC farkı) | 0 | — | — | — | **ölçüm yok** |

`gerekli N` = t=2'ye ulaşmak için gereken **bağımsız dönem** sayısı. Yıla çevirmek için 13'e böl.

XU100'e göre alfa 7.67pp — **karar için kullanılmaz**, sermaye-ağırlık eğilimi içerir (ADR #002).

## Uygulanabilirlik (en hızlı ölçülen)

- **Slippage** (planlanan giriş vs gerçekleşen dolum): ort -0.087% · N=4
- **Tetiklenmeme oranı:** %0.0 (0/4 plan hiç dolmadı)

## Sonuç ve hata dağılımı

| Sonuç | n |   | Hata etiketi | n |
|---|---|---|---|---|
| hedef | 3 |  | hedef | 3 |
| stop | 1 |  | hizli_stop | 1 |

## Güven kalibrasyonu (Brier)

Brier skoru: 0.2500 · N=4 · **ölçüm yetersiz (N=4)**

| Güven | n | iddia edilen | gerçekleşen |
|---|---|---|---|
| orta | 4 | 0.50 | 0.75 |

> Kova başına ~30-50 çözülmüş tahmin gerekir; bu 2+ yıl demektir.

## Rejim boyutlandırması işe yarıyor mu?

Portföy katkısı farkı: -0.634pp · N=4 · t=-2.97 · **ölçüm yetersiz (N=4)**

> Birim: portföy yüzde PUANI (hisse getirisi değil). Pozitif = rejimin kırptığı pozisyonlar zarar etmiş (boyutlandırma işe yaramış); negatif = kırpılanlar kazanmış (boyutlandırma kenar yiyor). Referans boyut: `risk.maks_pozisyon_pct`.

_Bu satır uzun süre TANIM GEREĞİ sıfırdı (`ret_pct_equal_size` kolonu `ret_pct`'in kopyasıydı), yani rejim katmanı ölçülüyor görünüp hiç ölçülmüyordu — 2026-07-27 denetiminde düzeltildi (ADR #009)._

## Veto — analistin en ölçülebilir katkısı

- Veto sayısı: **94** — {'rejim_uyumsuz': 86, 'tez_zayif': 8} · ufku dolan ve ÖLÇÜLEN: 0

| | ortalama plansız alfa |
|---|---|
| Vetolananlar | — |
| Seçilenler | — |
| **Fark** | **—** — ölçüm yok |

> Birim: yüzde puan, PLANSIZ ileri getiri (H=ana_ufuk_gun), EW tabana göre. **Fark POZİTİFSE veto ZARAR veriyor** — elenen isimler seçilenleri geçmiş demektir. Vetolananların planı açılmadığı için ikisi de plansız ölçülür; aksi hâlde farklı ölçekler kıyaslanırdı.

_Bu satır 2026-08-16'ya kadar TANIM GEREĞİ boştu: kaynak sorgusu `outcomes` ile INNER JOIN yapıyordu ve veto edilen tahminin planı açılmadığı için outcome'u da yoktu — yani ölçüm kendi konusunu eliyordu. 17 veto varken karne `0` diyordu (2026-08-15 denetimi)._

---

### Bu raporun okunma kuralları

- **`ölçüm yetersiz` bir sonuçtur, bir eksiklik değil.** Yanındaki büyük yüzde bir bulgu DEĞİLDİR.
- **Hüküm daima eşit-ağırlık evrene göre.** XU100 satırı bilgi içindir.
- **En güçlü ifade `zayıf kanıt`tır.** Bu sistemde "doğrulandı" YOKTUR.
- Ağırlıklar bu rapordan DEĞİŞMEZ — o yavaş döngünün işi (ADR #004).
