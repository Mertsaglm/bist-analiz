# Ölçüm — hedef mesafe eşiği (`min_hedef_uzakligi_atr`) · 2026-08-12

> Bu bir karar destek aracıdır, yatırım tavsiyesi değildir. Ölçülen kenar
> zayıftır ve istatistiksel olarak doğrulanması yıllar alır (bkz. `required_n`).

**Bu bir KENAR deneyi değil, KAPSAMA deneyidir.** ADR #007/#008 kapıyı kapattı
ve bu ölçüm o kararı sorgulamıyor. Sorulan tek soru: plan geometrisi hangi
isimleri, hangi gerekçeyle eliyor?

## Neden koşuldu

`src/planner.py` T1'i **en yakın direnç** olarak seçiyor ve R:R kapısı ona
uygulanıyordu. Giriş tarafında mesafe koruması vardı
(`maks_giris_uzakligi_atr: 3.0`), hedef tarafında **yoktu**.

Aritmetik: stop ≈ 2×ATR, giriş ≈ fiyat → `R:R ≈ T1_uzaklık / 2`. Yani 1.5
kapısını geçmek için en yakın direncin ~3 ATR yukarıda olması gerekiyordu.
Huni teşhisi (2026-08-10, 18 canlı isim):

- 15 isim elendi; **15/15'inde stop bandı geçti** — öldüren tek şey R:R'dı
- elenenlerin en yakın direnç medyanı **0.36 ATR** (min 0.05 = fiyatın %0.02 üstü)
- 2026-07-24'ten beri üretilen **49 planın hepsinde** T1 ≥ 2.44 ATR
- **31/49 planda** T1 kaynağı "52 hafta zirvesi" → üstte hiç pivot yoktu

Kapı, kimsenin karar vermediği bir **"üstünde ~3 ATR boşluk olan isim"
filtresine** dönüşmüştü. L-008'in imzası: koruma bir tarafa yazılmış,
simetriği yazılmamış.

## Eşik nereden geldi — ve ne zaman sabitlendi

`min_hedef_uzakligi_atr = 1.5`, `stop_atr_bandi`'nın **alt sınırından**
türetildi: stop tabanı 1.5×ATR çünkü günlük salınımın içinde kalan bir bariyer
gürültüyle tetiklenir. Aynı argüman hedef için de geçerlidir — üstelik daha ağır
sonuçla: gürültü bandındaki bir T1, üçlü bariyer resolver'ında **rastgele bir
`hedef` çözümü** üretir ve karnenin kendisini kirletir.

**Değer koşudan ÖNCE sabitlendi ve çıktıya bakılarak değiştirilmedi.** Ön kayıt
yazılmadı çünkü ortada bir kenar iddiası yok (ADR #008) — bu bir tanım sorusu,
tıpkı `min_dokunus`, `pivot_k` ve `maks_giris_uzakligi_atr` gibi.

3.0 seçilmedi: 2×ATR stop ile R:R'ı otomatik ≥1.5 yapar ve `min_rr_t1`'i
dekoratif bir kapıya çevirirdi — kazara oluşmuş filtreyi bilerek kodlamak olurdu.

## Kurulum

Aynı dönemler, iki replay koşusu, iki ayrı DB kopyası (kullanıcının verisine
dokunulmadı; iki koşu birbirinin kaydını kirletmedi).

`start=2024-01-01 · end=2026-06-30 · top_n=3 · adım=20 işlem günü · 30 dönem`

## Sonuçlar

### Kapsama (karar veren metrikler)

| Metrik | eşik 0 (bugün) | eşik 1.5 | |
|---|---|---|---|
| replay dönemi (tahmin üreten) | 16 | 17 | |
| üretilen plan | 25 | **29** | +%16 |
| tahmin | 20 | **25** | +%25 |
| farklı ticker (replay, top-3) | 8 | 8 | değişmedi — aşağıya bak |
| T1 kaynağı "52h zirvesi" | 17/25 (%68) | 18/29 (%62) | −6pp |
| T1 uzaklık medyanı | 3.20 ATR | 3.62 ATR | |
| **kaybedilen plan** | — | **0** | |

⚠ **"farklı ticker 8→8" yanıltıcı okunabilir.** Replay dönem başına yalnız
top-3 ismi analiz eder (`top_n=3`), yani ticker çeşitliliği zaten seçimle
tavanlanmıştır — bu satır kuralın çeşitlilik etkisini ÖLÇMEZ. Canlı evrende
(18 ismin hepsi denenir) etki çok daha büyük; aşağıdaki canlı kesit bunu
gösteriyor.

### Canlı kesit — 2026-08-10, 18 isim (asıl çeşitlilik ölçümü)

| | eşik 0 | eşik 1.5 |
|---|---|---|
| plan üretilen isim | **3** | **8** |
| plan üretilemeyen | 15 | 10 |

```
eşik 0.0 → EREGL, EUPWR, KRDMD
eşik 1.5 → ASTOR, BIMAS, EREGL, EUPWR, FROTO, KCHOL, KRDMD, PETKM
```

Mevcut üç ismin planı **byte'ı byte'ına aynı kaldı** (EREGL T1 41.04 / R:R 1.79,
EUPWR 107.90 / 1.76, KRDMD 47.00 / 2.01) — monoton zararsızlık isim düzeyinde de
doğrulandı. Gelen beş isim beş ayrı sektörden (elektrik ekipman, perakende,
otomotiv, holding, petrokimya) ve üçünün hedefi gerçek pivot, 52h zirvesi değil.

**"Her gün aynı 4-5 isim" örüntüsünün ana sebebi buymuş.** Elenen isimlerin
gerekçesi de artık dürüst: AKBNK eskiden `R:R 0.08` ile eleniyordu (fiyatın
%0.02 üstündeki bir pivot yüzünden); şimdi gerçek hedefle `R:R 1.01` — hâlâ
eleniyor ama **doğru sebeple**.

**Kaybedilen plan = 0 ölçüldü, varsayılmadı.** İki DB'nin `plan_options`
kümeleri `(asof, ticker)` düzeyinde karşılaştırıldı: kesişim tam, 8 plan
eklendi, **hiçbiri düşmedi**. Bu, kuralın analitik olarak monoton zararsız
olmasıyla tutarlı — yeni T1 ≥ eski T1 ve R:R T1'de monoton artan, giriş ile
stop değişmiyor.

### Yan etkiler (izlenen, karar vermeyen)

| Sonuç | eşik 0 | eşik 1.5 |
|---|---|---|
| `giris_olmadi` | 7 | **4** |
| `hedef` | 4 | 6 |
| `stop` | 4 | 5 |
| `sure` | 5 | **10** |
| **tetiklenmeme oranı** | %35 (7/20) | **%16 (4/25)** |

İki hareket de gerçek ve ikisi de aynı mekanizmadan geliyor:

**Tetiklenmeme yarıya indi.** Beklenmiyordu ve sebebi şu: R:R eşitsizliği
eskiden **girişi aşağı iterek** çözülüyordu (`destek_retest` → `above_zone` →
plan bir geri çekilmeye bağlı). Hedef uzaklaşınca eşitsizlik **hedef tarafından**
çözülüyor ve `dogrudan` bandı yetiyor. Raporun kendi uyarısı ("hedef sabittir,
eşitsizlik girişi aşağı iterek sağlanır") bu değişiklikle zayıflıyor.

**`sure` iki katına çıktı (5 → 10).** Hedef uzaklaştıkça daha çok pozisyon 20
günlük zaman bariyerine kadar taşınıyor. İsabet oranı (`hedef` / girilen) %30.8
→ %28.6 — pratikte yatay. Bu, kuralın bilinen bedeli ve **kaydedilmiştir**;
eşik bu sayıya bakılarak oynatılmadı.

### Alfa — SADECE RAPORLANIR

| | eşik 0 | eşik 1.5 |
|---|---|---|
| N | 13 | 21 |
| ortalama | +4.27pp | +4.00pp |
| t | 2.19 | **2.13** |
| sd | 7.03 | **8.60** |
| `gerekli_n` | 11 | **19** |
| hüküm | ölçüm yetersiz (N=13) | zayıf kanıt: +4.0p |

> ⚠ **HÜKÜM DEĞİŞİMİ BİR BULGU DEĞİLDİR.** `edge_verdict` önce `n < weak_n`
> bakar; `olcum.zayif_n_esigi = 15`. N 13'ten 21'e çıkınca bu **idari eşik**
> aşıldı ve hüküm "ölçüm yetersiz"ten "zayıf kanıt"a döndü. Kanıtın kendisi
> güçlenmedi — **tam tersine hepsi hafifçe kötüleşti**: ortalama düştü
> (4.27→4.00), t düştü (2.19→2.13), dağılım genişledi (7.03→8.60), gerekli N
> neredeyse iki katına çıktı (11→19). Etiketin yukarı gitmesi yalnız örneklem
> sayısının bir sayaç eşiğini geçmesindendir.
>
> Ayrıca iki sütun **farklı örneklemlerdir** (13 ⊂ 21), bir öncesi/sonrası
> karşılaştırması değildir. Ve replay **VEKİL** bir analist kullanır; gerçek
> analizle aynı potaya girmez (`evaluate.kaynak_sec`).

**Bu ölçümden çıkarılamayacak sonuç:** "düzeltme kenar üretti". Çıkarılabilecek
sonuç: **+4.27pp, geometri filtresinin bir ürünü DEĞİLDİ** — filtre gevşetilip
örneklem %60 büyütüldüğünde ortalama ~4pp'de kaldı. Bu, STATE'teki Sıradaki İş
#2'ye ("replay'in +4.27pp'si geometriden mi geliyor?") kısmi bir cevaptır:
**geometriden gelmiyor.** Kalan aday açıklama limitli girişten kaynaklanan
geometri avantajıdır ve o ayrı bir tur ister.

## Karar

Karar kuralı koşudan önce yazılmıştı: *eşik çıktıya bakılarak değiştirilmez;
kapsama metrikleri beklendiği gibi hareket ediyorsa 1.5 canlıya alınır.*

**1.5 canlıya alındı.** Gerekçe: hiçbir plan kaybedilmedi (ölçüldü, 0), kapsama
arttı (+%16 plan, +%25 tahmin), tetiklenmeme yarıdan fazla düştü, ve elenme
gerekçesi artık "R:R yetmedi" yerine doğru sınıfla (`hedef_yakin`) raporlanıyor.

## Ne DÜZELMEDİ — açıkça

**1. Rejim tavanı yerinde duruyor.** Menü 3'ten 8 isme çıktı ama risk-off'ta
maks **2 pozisyon** ve boyut ×0.4. Yani Telegram özetinde yine 2 isim
görülebilir; genişleyen şey **analistin seçim havuzu**, günlük öneri sayısı
değil. Bu bir başarısızlık değil, ayrı bir konu (rejim OR/AND asimetrisi —
16 risk-off etiketinin 14'ü genişlik tek başına tetiklemiş, XU100 SMA200'ün
üstündeyken). Bu turda **bilerek dokunulmadı**: aynı anda değiştirilirse hangi
değişikliğin ne yaptığı ayrılamaz.

**2. 52 hafta zirvesine bağımlılık yüksek kaldı.** Canlı kesitte 8 planın
5'inde T1 kaynağı 52h zirvesi. Eşik bu oranı bir miktar düşürdü (replay'de
%68→%62) ama yapısal sebep duruyor: bazı isimlerde üstte gerçekten uzak pivot
yok. `zirveye_yakin` ve `hedef_yok` sınıfları artık bunu isim isim gösteriyor.

**3. İsabet oranı bedeli var.** `sure` payı iki katına çıktı. Şimdilik `hedef`
payı da arttığı için net etki nötr; ama izlenmesi gereken bir eğilim
(ADR #018'in "tekrar gözden geçir" koşulu).

Bu raporun iddiası şudur: **gizli filtre görünür oldu, gevşetilmesi hiçbir plan
kaybettirmedi ve canlı evrende çeşitliliği 3'ten 8'e çıkardı.** Kenar iddiası
yoktur ve bu ölçüm ADR #007/#008'in hükmüne dokunmaz.

---

### Bu raporun okunma kuralları

- **`ölçüm yetersiz` bir sonuçtur, bir eksiklik değil.** Yanındaki büyük yüzde
  bir bulgu DEĞİLDİR.
- **En güçlü ifade `zayıf kanıt`tır.** Bu sistemde "doğrulandı" YOKTUR.
- Alfa bu raporda bir **gözlemdir**, karar kriteri değildir.
- Üretilebilirlik: `min_hedef_uzakligi_atr` 0 ve 1.5 ile
  `bist replay --start 2024-01-01 --end 2026-06-30 --top 3`.
