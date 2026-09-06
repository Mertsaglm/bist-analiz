# Değerlendirme Raporu — 2026-09-06

> Bu bir karar destek aracıdır, yatırım tavsiyesi değildir. Kişisel ve deneysel kullanım içindir. Ölçülen kenar zayıftır ve istatistiksel olarak doğrulanması yıllar alır (bkz. required_n).

Kaynak: `replay` · yılda ~13 bağımsız dönem üretiliyor

## Ana metrikler

| Metrik | N | değer | t | gerekli N | **HÜKÜM** |
|---|---|---|---|---|---|
| Eşleştirilmiş alfa (vs EW) | 13 | 4.27pp | 2.19 | 11 | **ölçüm yetersiz (N=13)** |
| ↳ **örtüşme ayıklanmış** | 13 | 4.27pp | 2.19 | — | **ölçüm yetersiz (N=13)** |
| ↳ karar başına (girmeyenler 0) | 20 | 2.78pp | — | — | — |
| Dönem-içi IC (tüm kesit) | 16 | 0.069 | 1.59 | 26 | **kenar yok** |
| LLM katkısı (IC farkı) | 0 | — | — | — | **ölçüm yok** |

`gerekli N` = t=2'ye ulaşmak için gereken **bağımsız dönem** sayısı. Yıla çevirmek için 13'e böl.

XU100'e göre alfa 3.77pp — **karar için kullanılmaz**, sermaye-ağırlık eğilimi içerir (ADR #002).

## Uygulanabilirlik (en hızlı ölçülen)

- **Slippage** (planlanan giriş vs gerçekleşen dolum): ort -0.088% · N=13
- **Tetiklenmeme oranı:** %35.0 (7/20 plan hiç dolmadı)

**Kaçırdıklarımız ne yaptı?** (plansız ileri getiri, EW tabana göre)

| | N | ortalama |
|---|---|---|
| Tetiklenmeyen planlar | 7 | 6.93pp |
| Tetiklenen planlar | 13 | 5.08pp |
| **Fark** | | **1.85pp** — ölçüm yetersiz (N=7) |

> Birim: yüzde puan, PLANSIZ ileri getiri. **Fark POZİTİFSE kaçırdıklarımız girdiklerimizden iyi gitmiş** — yani limitli giriş bir avantaj değil, bir SEÇİM YANLILIĞI olabilir ve karne bunu göremez (`giris_olmadi` paydadan düşer).

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

## Veto — analistin en ölçülebilir katkısı

- Veto sayısı: **0**

| | ortalama plansız alfa |
|---|---|
| Vetolananlar | — |
| Seçilenler | 5.73pp |
| **Fark** | **—** — ölçüm yok |

> Birim: yüzde puan, PLANSIZ ileri getiri (H=ana_ufuk_gun), EW tabana göre. **Fark POZİTİFSE veto ZARAR veriyor** — elenen isimler seçilenleri geçmiş demektir. Vetolananların planı açılmadığı için ikisi de plansız ölçülür; aksi hâlde farklı ölçekler kıyaslanırdı.

_Bu satır 2026-08-16'ya kadar TANIM GEREĞİ boştu: kaynak sorgusu `outcomes` ile INNER JOIN yapıyordu ve veto edilen tahminin planı açılmadığı için outcome'u da yoktu — yani ölçüm kendi konusunu eliyordu. 17 veto varken karne `0` diyordu (2026-08-15 denetimi)._

---

### Bu raporun okunma kuralları

- **`ölçüm yetersiz` bir sonuçtur, bir eksiklik değil.** Yanındaki büyük yüzde bir bulgu DEĞİLDİR.
- **Hüküm daima eşit-ağırlık evrene göre.** XU100 satırı bilgi içindir.
- **En güçlü ifade `zayıf kanıt`tır.** Bu sistemde "doğrulandı" YOKTUR.
- Ağırlıklar bu rapordan DEĞİŞMEZ — o yavaş döngünün işi (ADR #004).
