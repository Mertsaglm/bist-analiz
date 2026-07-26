# BIST Analiz

Borsa İstanbul'da 18 hisseyi izleyen, nicel skorlama + LLM yorum katmanıyla gerekçeli
kararlar üreten ve **kendi isabetini deterministik olarak ölçen** kişisel karar destek sistemi.

> ⚠️ Bu bir karar destek aracıdır, **yatırım tavsiyesi değildir**. Kişisel ve deneysel
> kullanım içindir. Ölçülen kenar zayıftır ve istatistiksel olarak doğrulanması yıllar
> alır (bkz. `required_n`).

---

## Önce şunu oku: bu sistem kâr ettiğini kanıtlayamaz

H=20 işlem günü + örtüşmeyen pencere = yılda **~12 bağımsız gözlem**. "18 hisse × 8 karar
= 144 tahmin" yanıltıcı: piyasa düşünce 8 stop aynı anda tetiklenir — sekiz şapka takmış
tek gözlem.

Ölçüldü (2026-07-26, canlı veri): en iyi faktörde H=15'te `ort=+0.72pp, sd=5.00` →

```
gerekli_n = (2 × 5.00 / 0.72)² ≈ 193 dönem ≈ 11,5 yıl
```

Bu yüzden sistem **erken kenar iddia etmez**. `bist degerlendir` ilk ~18 ay
`ölçüm yetersiz (N=…)` yazacak ve `required_n`'i basacak. Erken kenar iddia ederse
**kod yalan söylüyordur** — bunu sabitleyen bir test var.

Sistemin 2 yılda gerçekten ölçebildikleri: sürecin çalıştığı, **sıralama kalitesi (IC)**,
uygulama slippage'ı, hata taksonomisi, ve felaket senaryosunun tespiti.

## Ölçülmüş tasarım kararları

Aşağıdakiler tahmin değil, ölçüm. Ayrıntı: `ai/DECISIONS.md`.

| Bulgu | Sonuç |
|---|---|
| Eşit-ağırlık sepet vs XU100: **+0.36pp/15g, t=2.89** — sıfır beceriyle | Birincil taban **eşit-ağırlık evren**; XU100 yalnız iletişim için (#002) |
| Sektör nötralizasyonu 6-1 mom t'sini **1.86 → 0.62** yapıyor | Varsayılan **kapalı**; sektör kontrolü planlayıcıda kısıt (#003) |
| H=5'te kenar **sıfır** (−0.01pp, t=−0.05, N=485); H=21'de t=2.07 | Zaman bariyeri **20 gün**; "1 hafta" çerçevesi kalıcı `ölçülen kenar yok` etiketli |
| Alt kuyruk (−1.03pp) üst kuyruğun **1.8 katı** | Rapor **"hangisini azalt"** ile başlar, "ne al" ile değil |
| yfinance temettü/bölünme düzeltmesi **çalışıyor**; gerçek kusur SASA **%23.2 sıfır hacim** | İkinci veri kaynağı yok; **kayıt bazlı kalite kapısı** + fixture testi (L-005) |
| Maliyet kenarın ~1/3'ünü yiyor | Her ölçüm maliyet duyarlılığıyla raporlanır |

## Mimari

```
Fiyat + Makro + KAP  →  Göstergeler (dondurulmuş, versiyonlu)
                              ↓
                     Faktörler (kesitsel z, kapılar)
                              ↓
                  Plan Menüsü (DETERMİNİSTİK — entry/stop/hedef/boyut)
                              ↓
                    LLM (enum seç + prose yaz + VETO)
                              ↓
                    Denetim (HF-01..HF-30) ── başarısız → journal'a giremez
                              ↓
                  Journal (değişmez)  →  Resolver (üçlü bariyer, KOD)
                              ↓
              Değerlendirme (IC, eşleştirilmiş alfa, LLM katkısı)
```

**Tek sert kural: LLM hesaplanabilir hiçbir sayıyı üretmez.** Çıktı şemasında fiyat /
hedef / stop / boyut / sayısal güven alanı **yoktur**; LLM `plan_id` seçer, enum verir,
prose yazar. Ayrıca HF-17 prose'daki her sayısal token'ı girdi paketine karşı doğrular —
asıl hata modu yapısal değil, metinsel ("hedef 324 TL civarı makul").

**İki ayrı öğrenme döngüsü:**
- **Yavaş** (yılda 1-2, elle): 10 yıl walk-forward backtest → faktör ağırlıkları
- **Hızlı** (her değerlendirme): canlı journal → ağırlığa **asla dokunmaz**; dönem-içi IC,
  veto değeri, LLM katkısı, slippage, boyutlandırma karşı-olgusu, hata taksonomisi

## Kurulum

```bash
poetry install
cp .env.example .env   # EVDS_API_KEY doldur (opsiyonel; yoksa makro satırları gizlenir)
```

## Kullanım

```bash
poetry run bist veri backfill        # 18 ticker × 10 yıl + endeksler + kur
poetry run bist veri kalite          # ticker bazlı kalite raporu
poetry run bist backtest             # ÖLÇÜM — hüküm satırını oku
poetry run bist replay --start 2024-01-01 --end 2026-06-30   # LLM'siz tam boru hattı
poetry run bist gunluk               # llm/in/<tarih>/ paketini yazar
# → IDE'de prompt'u çalıştır, llm/out/<tarih>/analysis.json kaydet
poetry run bist denetle              # HF-01..HF-30
poetry run bist kaydet               # journal'a yaz
poetry run bist coz                  # açık tahminleri çöz (üçlü bariyer)
poetry run bist degerlendir          # IC, required_n, hüküm
poetry run bist rapor                # Türkçe markdown
```

## Proje yapısı

```
config.yaml       TÜM eşik/oran/URL — koda sabit gömülmez
universe.yaml     18 hisse + sektör + tier + canlı ölçülmüş metrikler
holidays_tr.yaml  YALNIZCA gelecek tarihler (geçmiş takvim XU100 barlarından türetilir)

AGENTS.md         AI yardımcı ("Usta") kanonik kuralları — araçtan bağımsız
CLAUDE.md · GEMINI.md · .github/copilot-instructions.md    IDE köprüleri
ai/               proje hafızası: PROJECT · STATE · DECISIONS · LESSONS · PROFILE

src/              veri → gösterge → faktör → plan → LLM sınırı → journal → ölçüm
tests/            pytest; her HF koduna bir test, her ölçüm değişmezine bir test
llm/in            LLM girdi paketi (izlenir)    llm/out  LLM çıktısı (izlenmez)
data/             SQLite + deterministik SQL dump (dump izlenir, .db izlenmez)
```

## Ölçüm kültürü

`gold_tracking_system`'den taşındı ve burada da geçerli:

- **Doğrulama harness'i sunumdan ÖNCE inşa edilir.** Ölçüm raporun dilini belirler — tersi değil.
- **Zayıf N, büyük farkı EZER.** En güçlü ifade "zayıf kanıt"tır; `edge_verdict`'te
  "doğrulandı" dalı **yoktur**.
- **Bilgi mutlak değerde değil, koşulsuz tabandan FARKTA.**
- **Örtüşmeyen pencere + taban çizgisi** olmadan her "üstünlük" sahtedir.
- **Verisi gelmeyen gösterge paydadan düşer** — uydurma yapılmaz.
- *"Sayıların küçülmesi dürüstlüğün büyümesidir."*
