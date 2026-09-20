# Değerlendirme Raporu — 2026-09-20

> Bu bir karar destek aracıdır, yatırım tavsiyesi değildir. Kişisel ve deneysel kullanım içindir. Ölçülen kenar zayıftır ve istatistiksel olarak doğrulanması yıllar alır (bkz. required_n).

Kaynak: `gemini-3.5-flash` · yılda ~13 bağımsız dönem üretiliyor

## Ana metrikler

| Metrik | N | değer | t | gerekli N | **HÜKÜM** |
|---|---|---|---|---|---|
| Eşleştirilmiş alfa (vs EW) | 10 | 1.67pp | 0.64 | 98 | **ölçüm yetersiz (N=10)** |
| ↳ **örtüşme ayıklanmış** | 10 | 1.67pp | 0.64 | — | **ölçüm yetersiz (N=10)** |
| ↳ karar başına (girmeyenler 0) | 15 | 1.12pp | — | — | — |
| Dönem-içi IC (tüm kesit) | 9 | 0.032 | 3.80 | 3 | **ölçüm yetersiz (N=9)** |
| LLM katkısı (IC farkı) | 8 | 0.058 | 2.21 | 7 | **ölçüm yetersiz (N=8)** |

`gerekli N` = t=2'ye ulaşmak için gereken **bağımsız dönem** sayısı. Yıla çevirmek için 13'e böl.

XU100'e göre alfa 3.26pp — **karar için kullanılmaz**, sermaye-ağırlık eğilimi içerir (ADR #002).

## Uygulanabilirlik (en hızlı ölçülen)

- **Slippage** (planlanan giriş vs gerçekleşen dolum): ort -0.070% · N=10
- **Tetiklenmeme oranı:** %33.3 (5/15 plan hiç dolmadı)

**Kaçırdıklarımız ne yaptı?** (plansız ileri getiri, EW tabana göre)

| | N | ortalama |
|---|---|---|
| Tetiklenmeyen planlar | 5 | -1.62pp |
| Tetiklenen planlar | 5 | 2.65pp |
| **Fark** | | **-4.27pp** — ölçüm yetersiz (N=5) |

> Birim: yüzde puan, PLANSIZ ileri getiri. **Fark POZİTİFSE kaçırdıklarımız girdiklerimizden iyi gitmiş** — yani limitli giriş bir avantaj değil, bir SEÇİM YANLILIĞI olabilir ve karne bunu göremez (`giris_olmadi` paydadan düşer).

## Sonuç ve hata dağılımı

| Sonuç | n |   | Hata etiketi | n |
|---|---|---|---|---|
| stop | 6 |  | tetiklenmedi | 5 |
| giris_olmadi | 5 |  | stop | 4 |
| hedef | 3 |  | hedef | 3 |
| sure | 1 |  | hizli_stop | 2 |
|  |  |  | sure_negatif | 1 |

## Güven kalibrasyonu (Brier)

Brier skoru: 0.2394 · N=10 · **ölçüm yetersiz (N=10)**

| Güven | n | iddia edilen | gerçekleşen |
|---|---|---|---|
| orta | 9 | 0.50 | 0.33 |
| dusuk | 1 | 0.38 | 0.00 |

> Kova başına ~30-50 çözülmüş tahmin gerekir; bu 2+ yıl demektir.

## Rejim boyutlandırması işe yarıyor mu?

Portföy katkısı farkı: -0.194pp · N=10 · t=-1.35 · **ölçüm yetersiz (N=10)**

> Birim: portföy yüzde PUANI (hisse getirisi değil). Pozitif = rejimin kırptığı pozisyonlar zarar etmiş (boyutlandırma işe yaramış); negatif = kırpılanlar kazanmış (boyutlandırma kenar yiyor). Referans boyut: `risk.maks_pozisyon_pct`.

_Bu satır uzun süre TANIM GEREĞİ sıfırdı (`ret_pct_equal_size` kolonu `ret_pct`'in kopyasıydı), yani rejim katmanı ölçülüyor görünüp hiç ölçülmüyordu — 2026-07-27 denetiminde düzeltildi (ADR #009)._

## Veto — analistin en ölçülebilir katkısı

- Veto sayısı: **135** — {'rejim_uyumsuz': 113, 'tez_zayif': 17, 'veri_supheli': 5} · ufku dolan ve ÖLÇÜLEN: 37

| | ortalama plansız alfa |
|---|---|
| Vetolananlar | -9.63pp |
| Seçilenler | 0.46pp |
| **Fark** | **-10.09pp** — ölçüm yetersiz (N=10) |

> Birim: yüzde puan, PLANSIZ ileri getiri (H=ana_ufuk_gun), EW tabana göre. **Fark POZİTİFSE veto ZARAR veriyor** — elenen isimler seçilenleri geçmiş demektir. Vetolananların planı açılmadığı için ikisi de plansız ölçülür; aksi hâlde farklı ölçekler kıyaslanırdı.

_Bu satır 2026-08-16'ya kadar TANIM GEREĞİ boştu: kaynak sorgusu `outcomes` ile INNER JOIN yapıyordu ve veto edilen tahminin planı açılmadığı için outcome'u da yoktu — yani ölçüm kendi konusunu eliyordu. 17 veto varken karne `0` diyordu (2026-08-15 denetimi)._

---

### Bu raporun okunma kuralları

- **`ölçüm yetersiz` bir sonuçtur, bir eksiklik değil.** Yanındaki büyük yüzde bir bulgu DEĞİLDİR.
- **Hüküm daima eşit-ağırlık evrene göre.** XU100 satırı bilgi içindir.
- **En güçlü ifade `zayıf kanıt`tır.** Bu sistemde "doğrulandı" YOKTUR.
- Ağırlıklar bu rapordan DEĞİŞMEZ — o yavaş döngünün işi (ADR #004).
