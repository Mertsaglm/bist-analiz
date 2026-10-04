# Değerlendirme Raporu — 2026-10-04

> Bu bir karar destek aracıdır, yatırım tavsiyesi değildir. Kişisel ve deneysel kullanım içindir. Ölçülen kenar zayıftır ve istatistiksel olarak doğrulanması yıllar alır (bkz. required_n).

Kaynak: `gemini-3.5-flash` · yılda ~13 bağımsız dönem üretiliyor

## Ana metrikler

| Metrik | N | değer | t | gerekli N | **HÜKÜM** |
|---|---|---|---|---|---|
| Eşleştirilmiş alfa (vs EW) | 12 | 1.94pp | 0.89 | 61 | **ölçüm yetersiz (N=12)** |
| ↳ **örtüşme ayıklanmış** | 12 | 1.94pp | 0.89 | — | **ölçüm yetersiz (N=12)** |
| ↳ karar başına (girmeyenler 0) | 17 | 1.37pp | — | — | — |
| Dönem-içi IC (tüm kesit) | 15 | 0.095 | 4.09 | 4 | **zayıf kanıt: IC=+0.095** |
| LLM katkısı (IC farkı) | 14 | -0.015 | -0.27 | 787 | **ölçüm yetersiz (N=14)** |

`gerekli N` = t=2'ye ulaşmak için gereken **bağımsız dönem** sayısı. Yıla çevirmek için 13'e böl.

XU100'e göre alfa 3.72pp — **karar için kullanılmaz**, sermaye-ağırlık eğilimi içerir (ADR #002).

## Uygulanabilirlik (en hızlı ölçülen)

- **Slippage** (planlanan giriş vs gerçekleşen dolum): ort -0.058% · N=12
- **Tetiklenmeme oranı:** %29.4 (5/17 plan hiç dolmadı)

**Kaçırdıklarımız ne yaptı?** (plansız ileri getiri, EW tabana göre)

| | N | ortalama |
|---|---|---|
| Tetiklenmeyen planlar | 5 | -1.62pp |
| Tetiklenen planlar | 9 | 1.16pp |
| **Fark** | | **-2.78pp** — ölçüm yetersiz (N=5) |

> Birim: yüzde puan, PLANSIZ ileri getiri. **Fark POZİTİFSE kaçırdıklarımız girdiklerimizden iyi gitmiş** — yani limitli giriş bir avantaj değil, bir SEÇİM YANLILIĞI olabilir ve karne bunu göremez (`giris_olmadi` paydadan düşer).

## Sonuç ve hata dağılımı

| Sonuç | n |   | Hata etiketi | n |
|---|---|---|---|---|
| stop | 6 |  | tetiklenmedi | 5 |
| giris_olmadi | 5 |  | hedef | 4 |
| hedef | 4 |  | stop | 4 |
| sure | 2 |  | sure_negatif | 2 |
|  |  |  | hizli_stop | 2 |

## Güven kalibrasyonu (Brier)

Brier skoru: 0.2524 · N=12 · **ölçüm yetersiz (N=12)**

| Güven | n | iddia edilen | gerçekleşen |
|---|---|---|---|
| orta | 10 | 0.50 | 0.30 |
| dusuk | 2 | 0.38 | 0.50 |

> Kova başına ~30-50 çözülmüş tahmin gerekir; bu 2+ yıl demektir.

## Rejim boyutlandırması işe yarıyor mu?

Portföy katkısı farkı: -0.161pp · N=12 · t=-1.32 · **ölçüm yetersiz (N=12)**

> Birim: portföy yüzde PUANI (hisse getirisi değil). Pozitif = rejimin kırptığı pozisyonlar zarar etmiş (boyutlandırma işe yaramış); negatif = kırpılanlar kazanmış (boyutlandırma kenar yiyor). Referans boyut: `risk.maks_pozisyon_pct`.

_Bu satır uzun süre TANIM GEREĞİ sıfırdı (`ret_pct_equal_size` kolonu `ret_pct`'in kopyasıydı), yani rejim katmanı ölçülüyor görünüp hiç ölçülmüyordu — 2026-07-27 denetiminde düzeltildi (ADR #009)._

## Veto — analistin en ölçülebilir katkısı

- Veto sayısı: **135** — {'rejim_uyumsuz': 113, 'tez_zayif': 17, 'veri_supheli': 5} · ufku dolan ve ÖLÇÜLEN: 94

| | ortalama plansız alfa |
|---|---|
| Vetolananlar | -5.68pp |
| Seçilenler | 0.15pp |
| **Fark** | **-5.83pp** — ölçüm yetersiz (N=14) |

> Birim: yüzde puan, PLANSIZ ileri getiri (H=ana_ufuk_gun), EW tabana göre. **Fark POZİTİFSE veto ZARAR veriyor** — elenen isimler seçilenleri geçmiş demektir. Vetolananların planı açılmadığı için ikisi de plansız ölçülür; aksi hâlde farklı ölçekler kıyaslanırdı.

_Bu satır 2026-08-16'ya kadar TANIM GEREĞİ boştu: kaynak sorgusu `outcomes` ile INNER JOIN yapıyordu ve veto edilen tahminin planı açılmadığı için outcome'u da yoktu — yani ölçüm kendi konusunu eliyordu. 17 veto varken karne `0` diyordu (2026-08-15 denetimi)._

---

### Bu raporun okunma kuralları

- **`ölçüm yetersiz` bir sonuçtur, bir eksiklik değil.** Yanındaki büyük yüzde bir bulgu DEĞİLDİR.
- **Hüküm daima eşit-ağırlık evrene göre.** XU100 satırı bilgi içindir.
- **En güçlü ifade `zayıf kanıt`tır.** Bu sistemde "doğrulandı" YOKTUR.
- Ağırlıklar bu rapordan DEĞİŞMEZ — o yavaş döngünün işi (ADR #004).
