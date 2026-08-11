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

## 🛑 Ölçüm sonucu: kenar bulunamadı — sistem yeniden çerçevelendi

Faz 2'de kurulan ölçüm harness'i, kendi faktör setimizi kendi evrenimizde ölçtü
ve **kapı kapandı** (ADR #007, #008):

| | alfa vs eşit-ağırlık | t | IC (tüm kesit) | t |
|---|---|---|---|---|
| birleşik skor, tam dönem | −0.86pp | −1.85 | 0.042 | 2.42 |
| birleşik skor, **OOS** | −1.12pp | −1.76 | 0.049 | 1.76 |

Teşhis, ayrışmanın bir kurgu hatası olmadığını gösterdi: **sıralama bilgisinin
%79'u SMA200 kapısında kayboluyor** (`ic_tum` 0.042 → `ic_uygun` 0.009).
Teşhisin işaret ettiği tek ön kayıtlı revizyon turu (SMA200 kapısını kaldır +
ufuk H=42) koşuldu — `docs/on-kayit-revizyon-01.md`, sha `6677c296…`, koşudan
**önce** mühürlendi. Sonuç: **OOS N=21, Δ=+0.81pp, t=0.89 → `kenar yok`**.
Çıta |Δ|≥1.0pp idi. İkinci tur yapılmadı.

Aynı koşuda `high52_prox` tek başına OOS'ta +1.61pp (t=1.81) verdi — 34
karşılaştırmanın çıtayı geçen tek satırı. **Buna göre karar verilmedi**;
sonucu görüp en iyi hücreyi seçmek, ön kaydın engellemek için yazıldığı şey.
Backlog'da ayrı bir tur hipotezi olarak duruyor.

**Bu yüzden sistem "izleme + risk disiplini + haber/veto aracı"dır.**
Kenar iddia etmez. Seviyeleri **planlama geometrisi** olarak sunar: fiyatın
nereye gideceğini söylemez, girişin/stop'un/hedefin nereye konacağını söyler.
Her plan ve her rapor bu ibareyi taşır.

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
Fiyat + Makro + KAP (bildirim + BEKLENEN bildirim)
                              ↓
              Kalite kapısı (kayıt bazlı, fail-closed)
                              ↓
                     Göstergeler (dondurulmuş, versiyonlu)
                              ↓
                     Faktörler (kesitsel z, kapılar)
                              ↓
      Plan Menüsü (DETERMİNİSTİK — entry/stop/hedef/boyut/net R:R)
      ├─ kilitli hisse → plan YOK        ├─ ex-tarih → plan YOK
                              ↓
                    LLM (enum seç + prose yaz + VETO)
                              ↓
                    Denetim (HF-01..HF-32) ── başarısız → journal'a giremez
                              ↓
                  Journal (değişmez)  →  Resolver (üçlü bariyer, KOD)
                              ↓
              Değerlendirme (IC, eşleştirilmiş alfa, LLM katkısı)

Rapor §0  ←  SIRALI EYLEM LİSTESİ (uygulanabilirlik + risk sırası, ADR #015)
```

**İki sert kural.**

1. **LLM hesaplanabilir hiçbir sayıyı üretmez.** Çıktı şemasında fiyat /
hedef / stop / boyut / sayısal güven alanı **yoktur**; LLM `plan_id` seçer, enum verir,
prose yazar. Ayrıca HF-17 prose'daki her sayısal token'ı girdi paketine karşı doğrular —
asıl hata modu yapısal değil, metinsel ("hedef 324 TL civarı makul").

2. **Deterministik katman bir TAVANDIR** (ADR #015, HF-32). Model aşağı inebilir
   (veto, `izle`, `islem_yok`) ama yukarı çıkamaz: sistem bir ismin verisine
   güvenmediği ya da hisse o gün tavana/tabana kilitli olduğu için plan bile
   üretmediyse, orada en fazla `hold` denebilir.

**Rapor §0 — sıralı eylem listesi.** Rapor tek bir sıralı liste ile başlar:
bugün ne yapılabilir, hangi sırayla, neyi riske ederek. ⚠ Sıra bir **getiri**
sırası DEĞİLDİR — uygulanabilirlik ve risk sırasıdır (ADR #015). Ölçülen kenar
yok; sıralamanın bir yön bildiği iddiası da yok. Skor üretilmez, sıralama
sözlükbilimseldir.

**İki ayrı öğrenme döngüsü:**
- **Yavaş** (yılda 1-2, elle): tüm geçmişle walk-forward backtest → faktör ağırlıkları
  (`sources.yf.backfill_start`'tan bugüne; sayı config'te, burada değil)
- **Hızlı** (her değerlendirme): canlı journal → ağırlığa **asla dokunmaz**; dönem-içi IC,
  veto değeri, LLM katkısı, slippage, boyutlandırma karşı-olgusu, hata taksonomisi

## Kurulum

```bash
poetry install
cp .env.example .env   # EVDS_API_KEY doldur (opsiyonel; yoksa makro satırları gizlenir)
```

## Kullanım

**Kurulum (bir kez):**

```bash
poetry run bist veri backfill        # 70 ticker × ~11 yıl (2015→) + endeksler + kur
poetry run bist gosterge             # göstergeleri hesapla ve dondur — TÜM 70 ticker
poetry run bist veri kalite          # ticker bazlı kalite kapısı
```

> ⚠ `bist gosterge`'yi evren her değiştiğinde TEKRAR koş. `indicator_daily`
> eksik kalırsa kesitsel `yuzdelik` ve piyasa genişliği sessizce daralır —
> pakette artık `kesit` ve `rejim.genislik_n` alanları paydayı gösterir.

**Günlük akış — tek komut (Faz 8):**

```bash
poetry run bist otonom gunluk
```

Sırayla: **heartbeat** → takvim kapısı (işlem günü değilse çıkar) →
`veri gunluk` → **`gosterge`** → **`makro gunluk`** → `haber cek` →
`saglik` (KRİTİK ise DURUR) → paket → **analist zinciri** → `coz` →
rapor + Telegram özeti.
Çıkış kodu: `0` başarılı · `1` KRİTİK adım düştü.

> ⚠ `gosterge` bu akışın İÇİNDE. Eskiden yalnız kurulum bölümündeydi ve
> günlük akışta hiç geçmiyordu; sonuç, her gün **boş ama şeklen geçerli**
> bir paketti (0 skorlanan isim, 0 plan — sıfır hata koduyla). Bkz. L-009.
>
> ⚠ `makro gunluk` de 2026-08-11'e kadar akışta YOKTU: EVDS yalnız elle
> koşulunca tazeleniyordu ve TÜFE serisi sekiz ay donmuş hâlde pakete
> giriyordu. Aynı ders, ikinci kez (L-002).

### Kapı KİMİN durduğuna karar verir — iki sınıf kontrol

`saglik`'in bulguları iki sınıfa ayrılır ve **yalnız birincisi koşuyu durdurur**:

| Sınıf | Soru | Şiddet | Örnek |
|---|---|---|---|
| **KAPI** | Bugünkü VERİYE güvenilir mi? | KRİTİK olabilir | bar tazeliği · gösterge kapsaması · **yarım bar** |
| **GÖZLEM** | Sistem SÜREÇ olarak sağlıklı mı? | en fazla UYARI | atlanan koşu · analizsiz gün · açık plan · çıktı mührü |

Ayrımın sebebi bir kilitlenme (**L-016**): "atlanan koşu" kontrolü
`MAX(predictions.asof)`e bakıp KRİTİK dönüyordu, ama `predictions` kapının
ARKASINDA yazılır. 2026-08-06'da runner işi almayınca kapı kapandı ve **bir
daha açılamadı** — açılması için gereken tahmin kapının arkasındaydı. Sistem
dört işlem günü veri çekti, commit attı, sıfır analiz üretti.

Kural: **kapıyı yalnız KOŞUNUN KENDİSİNİN düzeltebileceği şeyler kapatır.**
Gözlem kontrollerinin şiddeti `saglik.ekle_gozlem` içinde yapısal olarak
tavanlanır; davranışsal kilidi `tests/test_saglik.py::TestKapiKendiCiktisinaBakmaz`.

Adımları elle koşmak istersen hepsi ayrı ayrı da var:

```bash
poetry run bist veri gunluk          # fiyat + hayalet bar ayıklama + kalite kapısı
poetry run bist gosterge             # HER YENİ BAR için gerekli
poetry run bist haber cek            # KAP bildirim + BEKLENEN bildirim takvimi
                                     # çıkış: 0 temiz · 1 aralık atlandı · 2 hata
                                     # (takvim kırpık/çekilemedi de 1 döndürür)
poetry run bist gunluk               # llm/in/<tarih>/ paketini yazar
# → IDE'de llm/in/<tarih>/prompt.md çalıştır, llm/out/<tarih>/analysis.json kaydet
poetry run bist denetle              # HF-01..HF-32 — geçmeyen journal'a giremez
poetry run bist kaydet               # journal'a yaz
poetry run bist rapor                # §0 sıralı eylem listesi + AZALT + tez + VETO
```

## Otonom koşu — Actions + model zinciri + Telegram

Analist artık sıralı bir model zinciri (`config.llm.zincir`, ADR #013).
Sıra ücretsizden ücretliye; bir model cevap veremezse sıradakine geçilir.
**"Cevap verememek" HF denetimini de kapsar** — şemaya uyan ama `bist denetle`
sert hatası veren çıktı da reddedilir ve sıradaki model denenir.

`tool` alanını **kod** yazar, model değil: modelin kendi kimliği hakkındaki
beyanına güvenilirse `bist degerlendir --tool` yanlış kayıtları toplar.

```bash
poetry run bist bildir --test        # Telegram hattı ayakta mı?
poetry run bist otonom haftalik      # araç BAŞINA değerlendirme + haftalık özet
poetry run bist otonom nobetci       # bugün koşu oldu mu? — çıkış 1 = sessizlik
```

Workflow'lar `.github/workflows/` altında: `gunluk.yml` (hafta içi),
`haftalik.yml` (pazar), `nobetci.yml` (hafta içi, günlükten ~3 saat sonra),
`test.yml` (her push **ve günlük cron**). Secret'lar
`python scripts/set_secrets.py <pat_dosyasi>` ile yüklenir.

> ⚠ `test.yml`'in cron'u kozmetik değil: otonom iş `main`'e `GITHUB_TOKEN` ile
> push eder ve GitHub o push'larda workflow TETİKLEMEZ. Kod günlerce
> değişmezse suite hiç koşmaz (gözlendi: 2026-08-07'den 08-11'e kadar).

**Nöbetçi neden AYRI bir iş:** L-015'in kendi cümlesi — *bir süreç kendi
yokluğunu haber veremez.* 2026-08-06'da günlük iş runner alamadı ve HİÇ
BAŞLAMADI; o gün ne rapor ne uyarı çıktı. Çözüm sürecin İÇİNE konulunca
(L-015) sistem kilitlendi (L-016). Nöbetçi ayrı zamanlamayla, ayrı bir runner
talebiyle koşar, **salt-okurdur** ve yalnız söyler — hiçbir şeyi düzeltmez.

> ⚠ **Actions repoya commit atar.** Yerel kopyan sessizce geride kalır;
> çalışmadan önce `git pull` (LESSONS L-001). Ayrıca cron 5-30 dk gecikebilir —
> "saat 19:35'te gelir" diye bekleme.

**Periyodik:**

```bash
poetry run bist coz                  # açık tahminleri çöz (üçlü bariyer)
poetry run bist degerlendir          # IC, required_n, hüküm (kaynak karışıksa --tool ister)
poetry run bist backtest             # yavaş döngü — ölçüm harness'i
poetry run bist teshis               # kayıp atıfı (revizyon turu DEĞİL)
poetry run bist seviye               # seviye yakınlığının yön üstünlüğü — ölçüm
```

**Her şeyden önce — sessiz bozulma taraması:**

```bash
poetry run bist saglik               # 0 temiz · 1 uyarı · 2 KRİTİK
```

Gösterge kapsaması/tazeliği, kalite kapısı, haber katmanı sağlığı, tick
ızgarası, journal kaynak karışıklığı ve şema sürümünü tek seferde kontrol
eder. 2026-07-27 denetiminin ürettiği risk listesi elle koşulacak SQL'ler
olarak bırakılmadı — koşulmayan kontrol, olmayan kontroldür.

> `bist degerlendir` kaynak ayrımını kendisi yapar: journal'da tek araç varsa
> onu seçer ve raporun `Kaynak:` satırına yazar; **birden çok araç varsa DURUR**
> ve `--tool` ister (çıkış kodu 2). `replay` VEKİL bir analisttir; alfası
> gerçek LLM kayıtlarıyla aynı potaya girmez.

**Geliştirme / doğrulama:**

```bash
poetry run bist replay --start 2024-01-01 --end 2026-06-30   # LLM'siz tam boru hattı
poetry run bist plan THYAO           # tek hisse için plan menüsü
poetry run bist portfoy ekle THYAO 100 312.5
poetry run bist revizyon             # ön kayıtlı revizyon turu #1 (mühürlü)
poetry run pytest                    # tüm suite (sayı basılır — README'ye gömülmez)
```

> `pytest`in yan etkisi YOKTUR: gerçek `data/bist.db`'ye yazılabilir bağlantı
> açan bir test hata verir, üretilen paket/rapor dosyaları geçici dizine gider.
> Bu bir konvansiyon değil, `tests/conftest.py`'de zorlanan bir kural.

## Regresyona karşı zırh — kuralları insan değil test hatırlar

Bu projedeki kuralların çoğu bir hatadan doğdu ve doğal ömrü kısa: kuralı yazan
kişi unutur, projeye sonradan dokunan (insan ya da model) hiç bilmez. Bu yüzden
kurallar **koşulabilir hale getirildi.** Test katmanları üç ayrı soru sorar:

| Katman | Soru | Ne engeller |
|---|---|---|
| **Sözleşme** (`tests/test_sozlesme.py`) | Kodun VARSAYDIĞI yapı ayakta mı? | `*_COLS` listesi ↔ şema ayrışması, LLM sınırı kümelerinin kayması, **eşiklerin sessizce gevşetilmesi**, katman disiplini |
| **Mekanizma** (modül başına) | Doğru seriden / doğru paydadan mı besleniyor? | `c` ↔ `c_tr` karışması, eksik faktörün "nötr oy" sayılması, paydanın sessizce düşmesi |
| **Uçtan uca** (`tests/test_uctan_uca.py`) | Zincir gerçekten koşuyor mu? | Modüller arası varsayım kırılması — birim testleri yeşilken hattın durması |

Somut olarak artık **config'ten sessizce gevşetilemeyen** şeyler var:
`olcum.zayif_n_esigi`, `olcum.min_anlamli_fark_puan`, `planlayici.min_rr_t1`,
`risk.islem_maliyeti_gidis_donus_pct`, `denetim.sayisal_beyaz_liste_tamsayi_maks`
ve rejim politikasının defansiflik yönü. Bunları değiştirmek isteyen bir testi
de değiştirmek zorunda — yani karar **görünür** olur, config düzenlemesi olarak
geçmez.

Doküman tutarlılığı da makineye devredildi (`tests/test_dokuman.py`):
belgelerdeki her `bist <komut>`, her `config.<blok>.<anahtar>` atfı, her dosya
yolu ve her `HF-xx` kodu gerçekten var mı diye kontrol edilir. Ön kayıt mührü
(`docs/on-kayit-revizyon-01.md`'nin sha256'sı) de testle korunur — belge
sonradan düzenlenirse suite kırmızıya döner.

Ayrıca `pytest` artık **yan etkisiz**: gerçek veritabanına yazılabilir bağlantı
açan bir test hata verir, üretilen paket/rapor dosyaları geçici dizine gider.

## Denetimin bilinen sınırları

Bunlar gizlenmiyor çünkü gizlenen sınır, olmayan bir garantiye dönüşür:

- **HF-17 küçük tamsayılara ve yuvarlak yüzdelere karşı geçirgendir.** İzinli
  küme paketteki her sayı + `config.denetim` beyaz listeleri (0-31 arası
  tamsayılar, yıllar, `ek_izinli_sayilar`). Ölçüldü (2026-07-27, gerçek paket):
  −50..+50 tamsayıların **%56'sı** izinli, ama iki ondalıklı uydurma fiyatların
  yalnız **%0.5'i** geçiyor. Yani tasarlandığı hata modunda (*"hedef 324.75 TL"*)
  çalışıyor, prose'un doğal kaydında (*"%20 potansiyel"*) çalışmıyor.
- **R:R planlar arasında kıyaslanabilir değildir.** Hedef sabittir; eşitsizlik
  girişi aşağı iterek ya da stop'u daraltarak sağlanır. `rr_secim` ve
  `elenen_adaylar` alanları bunu görünür kılar; replay'de planların **%46'sı
  hiç tetiklenmedi**.
- **`bist degerlendir` şu an yalnız replay verisi görüyor** — gerçek LLM
  kayıtları henüz yok.
- **KAP geniş pencereyi sessizce kırpıyor.** Ölçüldü (2026-07-27): 90 gün
  istendiğinde 14 gün dönüyor, hata vermeden. Bu yüzden çekim dilimleniyor ve
  doyan dilim kendini ikiye bölüyor; tek gün bile doyarsa `bist haber cek`
  ATLANAN ARALIK basar ve 1 döner. `evds` aynı tuzağı aynı çözümle aşıyor.

## Proje yapısı

```
config.yaml       TÜM eşik/oran/URL — koda sabit gömülmez
universe.yaml     18 canlı hisse + 67 ölçüm evreni (canlı ölçülmüş metriklerle)
holidays_tr.yaml  YALNIZCA gelecek tarihler (geçmiş takvim barlardan türetilir)

AGENTS.md         AI yardımcı ("Usta") kanonik kuralları — araçtan bağımsız
CLAUDE.md · GEMINI.md · .github/copilot-instructions.md    IDE köprüleri
ai/               proje hafızası: PROJECT · STATE · DECISIONS · LESSONS · PROFILE

src/              veri → gösterge → faktör → plan → LLM sınırı → journal → ölçüm
tests/            pytest; sözleşme + mekanizma + uçtan uca (bkz. "Regresyona karşı zırh")
scripts/          set_secrets.py — .env anahtarlarını Actions secret'ına yükler
.github/workflows/  gunluk · haftalik · test

llm/              LLM girdi paketi ve çıktısı — İZLENİR
data/             deterministik SQL dump İZLENİR; ikili `.db` gitignore'da
reports/          üretilen raporlar — İZLENİR
docs/             ön kayıtlar (koşudan önce mühürlenmiş, değiştirilmez)
```

> **Arşiv politikası (Faz 8'de tersine çevrildi).** `data/`, `reports/` ve
> `llm/` artık izlenir. Sebep: Actions her koşuda veritabanını sıfırdan kurar
> (`bist db restore`) — arşiv repoda değilse sistemin hafızası yoktur.
> Tahminlerin ve sonuçların git geçmişinde durması ayrıca "bu tahmin ne zaman,
> hangi girdiyle üretildi?" sorusunu sonradan düzenlenemez biçimde cevaplar.
> Yalnız ikili `.db` dışarıda: diff'lenmez ve dump'tan yeniden kurulur.

## Ölçüm kültürü

`gold_tracking_system`'den taşındı ve burada da geçerli:

- **Doğrulama harness'i sunumdan ÖNCE inşa edilir.** Ölçüm raporun dilini belirler — tersi değil.
- **Zayıf N, büyük farkı EZER.** En güçlü ifade "zayıf kanıt"tır; `edge_verdict`'te
  "doğrulandı" dalı **yoktur**.
- **Bilgi mutlak değerde değil, koşulsuz tabandan FARKTA.**
- **Örtüşmeyen pencere + taban çizgisi** olmadan her "üstünlük" sahtedir.
- **Verisi gelmeyen gösterge paydadan düşer** — uydurma yapılmaz.
- *"Sayıların küçülmesi dürüstlüğün büyümesidir."*
