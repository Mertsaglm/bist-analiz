# DECISIONS.md — Karar Günlüğü (ADR)

> Yalnızca ÖNEMLİ kararlar: mimari, araç, yaklaşım seçimleri.
> Her karar "neden"i ve "tekrar gözden geçirme koşulu" ile kaydedilir.
> En yeni karar en üste.

---

## #013 — 2026-08-01 — Faz 8: otonom koşu, ücretsiz-öncelikli model zinciri, Telegram

**Bağlam:** v1 boru hattı çalışıyordu ama her adım elle tetikleniyordu. İlk
gerçek LLM turu (2026-07-29) bunun bedelini gösterdi: README'nin günlük akışında
`bist gosterge` yoktu, akış harfiyen izlendi ve **boş ama şeklen geçerli** bir
paket üretildi (0 skorlanan isim, 0 plan, rejim paydası 0 — sıfır hata koduyla,
L-009). Elle koşulan bir zincirde bir adımın unutulması kaçınılmazdır; çözüm
adımı hatırlamak değil, **akışı tek komuta indirmek.**

### Karar A — LLM analist katmanı otomatiğe bağlanıyor

Faz 8 planındaki ilk taslak "LLM elle kalsın, otomasyon deterministik katmanı
koşsun" diyordu; gerekçe PROJECT.md'deki *"ücretsiz kalmalı, LLM API maliyeti
YOK"* kısıtıydı. Ölçüm bu kısıtın artık gereksiz olduğunu gösterdi:

    GERÇEK paket ölçüldü (2026-07-29): girdi ~10.0K token · çıktı ~8.2K token
    (ilk tahminim ~50-60K'ydı — 5 kat şişik, ölçmeden konuşmuşum)

Gemini tarafında ücretsiz katmanı olan üç model var ve günde **1 istek**
atıyoruz; ücretsiz kota pratikte hiç dolmaz. Ücretli halkalara düşmek istisna
olacak; her gün en pahalı halkaya düşülse bile ay maliyeti **~$2.6**.

**PROJECT.md kısıtı revize edildi:** "LLM API maliyeti YOK" → "ücretsiz-öncelikli
zincir; ücretli halkalara düşüş istisna, ay tavanı ~$3".

### Karar B — Zincir sırası

    1. gemini-3.5-flash        ÜCRETSİZ · Google'ın "en akıllı" flash'ı
    2. gemini-3.6-flash        ÜCRETSİZ · kardeş model, ayrı kota kovası
    3. gemini-2.5-pro          ÜCRETSİZ · Pro sınıfı, FARKLI nesil
    4. gemini-3.1-pro-preview  ücretli ~$0.12/tur · en güçlü Gemini
    5. gpt-5.6-luna            ücretli ~$0.012/tur
    6. gpt-5-mini              ücretli ~$0.019/tur

Gerekçeler:
- **3.5 önce, 3.6 sonra.** 3.6 daha yeni ama Google onu *"hızı zekayla
  dengeleyen"* diye tanımlıyor; 3.5 ise *"en akıllı model"*. Fiyat da bunu
  doğruluyor (çıkış $9.00 vs $7.50). Günde 1 istek atıyoruz — hız umurumuzda
  değil, yargı kalitesi her şey. ⚠ Bu bir doküman-dili çıkarımı, benchmark
  değil; kesin cevabı `degerlendir --tool` verecek.
- **3. sırada bilerek FARKLI NESİL.** 1-2 birden düşerse sorun aile geneli
  demektir ve kardeş model kurtarmaz. 2.5-pro bağımsız bir aile ve hâlâ bedava.
  (İlk taslakta Pro'yu hiç değerlendirmemiştim; hata zinciri **kota bolluğuna**
  göre kurmaktı — oysa kota bizim için hiç kısıt değil.)
- **OpenAI DAİMA sonda** (kullanıcı kuralı) ve ucuzdan pahalıya.
- `gemini-3.1-pro-preview` 4. sırada: ücretsiz katmanı yok, o yüzden üç bedava
  halkanın arkasında; ama luna'dan 10× pahalı olmasına rağmen en güçlü Gemini
  ve model karakteri tercihi Gemini.

### Karar C — "Cevap verememek" HF denetimini de kapsar

Zincir, hata sınıfını ayırt etmez: kota, 5xx, zaman aşımı, geçersiz JSON ve
**`bist denetle` sert hatası** aynı kefede. Yani model şemaya uyan JSON üretse
bile HF-01..31'den geçemezse "cevap vermedi" sayılır ve sıradaki denenir.
Denetim, zincirin bir halkası gibi çalışır.

**`tool` alanını KOD yazar.** Model kendi kimliğini yanlış beyan ederse
(ya da iskeletteki `"<araç>"` yer tutucusunu bırakırsa) `degerlendir --tool`
o turu bulamaz ve ölçüm sessizce eksik kalır. Modelin kendisi hakkındaki
beyanına güvenilmez.

**Ara halkalarda tekrar YOK.** Arkasında beş yedek varken aynı modele ısrar
etmek zaman kaybı; yalnız son halkada tekrar denenir.

### Karar D — Hata sınıflandırması (gold `daily_job` deseni)

Her adım kendi try/except'inde koşar ve hiçbiri diğerini kesmez — ama gold'da
bunun bedeli yaşandı: altı adım da istisnayı yutunca iş HER ZAMAN yeşil bitiyor
ve bir modül günlerce bozuk kalıyordu (L-002). O yüzden yutmak yetmez,
sınıflandırmak gerekir:

    KRITIK_ADIMLAR = ("veri", "gosterge", "saglik", "rapor")   → çıkış 1
    diğerleri (haber, analist, coz, paket)                      → çıkış 0, rapora yazılır

`analist` bilerek kritik DEĞİL: zincirin tamamı düşse bile o günün plan
geometrisi ve risk çerçevesi tek başına değerlidir.

**Sağlık kapısı gerçek bir kapıdır:** KRİTİK dönerse paket üretilmez, analiz
edilmez, rapor yazılmaz. Bayat göstergeyle üretilen paket boş ama şeklen
geçerlidir (L-009) ve onu analiz etmek bu projenin en pahalı hata sınıfıdır.

### Karar E — Arşiv repoya giriyor (gitignore ters çevrildi)

Actions her koşuda veritabanını sıfırdan kurar (`bist db restore`); arşiv
repoda değilse sistemin hafızası yoktur. `data/`, `reports/` ve `llm/` artık
izlenir; istisna yalnız ikili `.db` dosyaları.

**Uygulama sırasında çıkan sürpriz:** dump 52,3 MB çıktı (plandaki varsayım
15 MB'dı) — GitHub'ın 50 MB uyarı eşiğinin üstünde ve her gün commit'lenecek.
Ölçüldü: `bars_daily` 48,6 MB ve her satır kendi `INSERT INTO ... VALUES`
başlığını taşıyordu → **16,7 MB saf tekrar**. Çok satırlı INSERT'e geçildi
(`dbdump.SATIR_KUME`): **52,3 → 32,9 MB**. Satır başına bir satır kuralı
korundu — diff'lenebilirlik bu dosyanın varlık sebebi ve onu boyut için feda
etmek `.db`'yi doğrudan commit'lemekten farksız olurdu.

### Ölçüm: iyimserlik artık tartışma değil, veri

Kullanıcının Gemini şikâyeti (fazla iyimser, yanlış yöne sürüklüyor) bu
mimaride ölçülebilir bir soruya dönüşüyor: journal `tool` alanı model
kimliğini taşır, `bist degerlendir --tool <model>` her modelin veto değerini
ve isabetini AYRI ölçer. İyimser model veriyle yakalanır ve zincirden
düşürülür. Elle atılan Claude turları da aynı potada kıyaslanır — yani
"hangi model daha iyi analist" sorusunu sistem kendisi cevaplayacak.

**Yapısal olarak zaten kapalı olanlar:** HF-17 (uydurma sayı), HF-22 (skorsuz
isme strong_buy), HF-25 (risk-off'ta risk_artir). Fine-tuning gerekmiyor;
OpenAI zaten platformu kapatıyor.

### Zorlanan sözleşmeler (yeni testler)

    zincir ⊆ llm.enums.tool          → ayrışırsa otonom turlar ölçümde kaybolur
    ücretsizler ücretlilerden önce   → sıra bozulursa her gün para ödenir
    gemini-2.5-* thinkingLevel ALMAZ → gönderilirse 400, halka HER ZAMAN düşer
    workflow secret'ları ⊆ set_secrets.SECRETS
    workflow'daki her `src.cli <komut>` gerçekten var
    commit adımı `if: always()`      → düşen koşuda bile veri commit'lenir
    yazılabilir her config yolu testte geçici dizine taşınır

### İLK CANLI KOŞU (2026-08-01) — iki düzeltme doğurdu

Zincir mekanik olarak kusursuz çalıştı: altı halka sırayla denendi, doğru
sınıflandırıldı, analist kritik olmadığı için rapor yine üretildi. Ama **hiçbir
model denetimden geçemedi** — ve sebep modellerde değildi:

1. **İstem, denetimin zorladığı kuralların çoğunu söylemiyordu** (L-011).
   HF-26 (prose < 80 karakter) altı modelin ALTISINDA da patladı; istem
   minimum uzunluğu hiç yazmıyordu. Aynı şekilde veto_code enum'u,
   `selected_plan_id`↔`plan_sec` eşliği, sinyal↔aksiyon çelişkisi ve açık
   tahmin zorunluluğu da yazılı değildi. `render_prompt` sözleşmeyle
   hizalandı (eşikler config'ten, gömülmeden) + temkin kalibrasyon bloğu
   eklendi. Sonuç: **ilk halka ilk denemede geçti.**
2. **Çıktı token tavanı açıkça verilmiyordu.** `gemini-3.5-flash`'ın JSON'u
   17.000 karakterde sessizce kesildi ve hata "geçersiz JSON" diye göründü —
   yani en iyi halka bir biçim kazası yüzünden kaybedildi. `llm.maks_cikti_token`
   eklendi ve iki sağlayıcıya da gönderildiği teste kilitlendi.

Düzeltmeler sonrası ilk tam otonom tur: **18 tahmin** journal'a yazıldı
(run `2026-07-30-gemini-3.6-flash-1`), rapor üretildi, Telegram özeti gitti.

Ayrıca gözlendi: `gemini-2.5-pro` ve `gemini-3.1-pro-preview` ücretsiz katmanda
**429** döndü — Pro modellerin kotası Flash'lardan sıkı. Zincir bunu yutup
ilerlediği için sorun olmadı; ama 3-4. halkaların pratikte "yedek" değil
"nadiren erişilebilir" olduğu akılda tutulmalı.

**Tekrar gözden geçir:** (a) 3 ay sonra model başına veto değeri/isabet ölçülüp
zincir sırası VERİYLE yeniden kurulmalı; (b) `gemini-3.1-pro-preview` preview —
emekli olursa zincir yumuşak düşer ama haftalık rapor fark ettirir;
(c) Gemini ücretsiz kota koşulları değişirse ay tavanı yeniden hesaplanmalı;
(d) private repo Actions dakikası ~200-250 dk/ay bekleniyor (limit 2000) —
sınıra yaklaşılırsa `test.yml` yalnız PR'da koşacak şekilde daraltılır.

---

## #012 — 2026-07-29 — İşlem takvimi İKİ kaynaktan türetilir: endeks barı VEYA hisse çokluğu

**Bağlam:** İlk gerçek LLM turundan sonra `pytest` kırmızıya döndü:
`test_2026_takvimi_tatil_listesiyle_birebir`, 2026-07-24 ve 2026-07-28'i
"tatil listesinde olmayan kapalı hafta içi gün" diye raporladı. Test doğruydu,
veri yanlıştı: yfinance o iki günü **XU100, XU030 ve XBANK'in üçünde birden**
atlamış; oysa evrendeki 70 hissenin hepsi o günler işlem görmüştü.

Test daha önce yeşildi çünkü veri boşluktan ÖNCE bitiyordu (`son_bar`
2026-07-23). Taze veri gelince boşluk sınırın soluna düştü ve görünür oldu —
yani hata yeni doğmadı, **yeni ölçülebilir hale geldi.**

Asıl bulgu daha derindi: çelişki kendi kodumuzun içindeydi.

    calendar_bist.is_trading_day  → "endeks barı yok  ⇒ borsa kapalıydı"  (otoriter)
    prices.purge_phantom_bars     → "endeks barı yok ama hisse barı gerçek" (142 bar KORUNDU)

İki modül aynı olgu hakkında **zıt varsayım** taşıyordu ve hiçbir test bu
çelişkiyi görmüyordu. Üstelik `calendar_bist` docstring'i ölçülmüş bir iddia
sunuyordu (*"eksik 9 gün holidays_tr.yaml ile BİREBİR aynı"*) — o ölçüm dar bir
pencerede doğruydu ve genelleştirilemezdi. §8'in "yorum bir iddiadır" kuralının
tam örneği.

**Ölçüm (2015-2026, gerçek veri) — ayrımda gri bölge yok:**

    endeks barı YOK ama hisse barı VAR    → 10 gün, hepsinde 67-70 hisse
    holidays_tr.yaml'deki gerçek tatiller → 12 gün, hepsinde  0 hisse

0 ile 67 arasında hiçbir gözlem yok. Ayrım keyfi değil, ölçülmüş bir uçurum.

**Seçenekler:**
- A) Boşluk geçicidir, birkaç gün sonra yeniden çek → **ELENDİ**: taze çekimde
  de yok, üstelik üç endekste birden. Sistematik, geçici değil.
- B) İstisna listesi tut (`holidays_tr.yaml` dışında ayrı bir "endeks boşluğu"
  listesi) → elle bakım, sessizce bayatlar; L-002'nin tam olarak yasakladığı
  şey ("elle bir kere çalıştırılan" bakım).
- C) **Takvimi iki kaynağın BİRLEŞİMİNDEN türet:** endeks barı VEYA
  `takvim.min_hisse_bari_seans_icin` (=10) kadar hisse barı.

**Karar: C.** Eşik, ölçülen uçurumun ortasında duruyor — sınırında değil.
Döngüsellik yok: `purge_phantom_bars` hayalet barı elerken üç koşulu birden
arıyor (o=h=l=c **ve** v=0 **ve** endeks barı yok), dolayısıyla gerçek seansın
barları purge'den sağ çıkıyor ve gerçek tatilin barları eleniyor. İki modül
artık aynı şeyi söylüyor.

**Etki (uçtan uca koşuldu, §11 tuzak #1):**
- 2026-07-24 ve 2026-07-28 artık seans günü; otoriter gün sayısı 2891 → 2901.
- **Bugünkü 18 tahminin bariyeri DEĞİŞMEDİ** (2026-08-26) — ileri hesap tatil
  dosyasından gidiyor, boşluktan etkilenmiyor.
- Geçmişte **1 replay kaydı kaydı**: `asof 2024-12-18` bariyeri 2025-01-17 →
  2025-01-16. O tahmin eski (bir gün geniş) bariyerle çözülmüştü. İfşa edildi,
  düzeltilmedi — replay'i yeniden koşmak journal'ı yeniden yazar, bu ayrı bir
  karar (STATE Backlog).

**Regresyon kilidi:** `test_calendar.py::test_endeks_barsiz_ama_hisseli_gun_SEANS_SAYILIR`
— iki yönlü: (a) endeks boşluğu olan günler seans SAYILIR, (b) gerçek tatiller
seans SAYILMAZ. Tek yönlü bir test eşiği 0'a çekerek de geçilebilirdi.

**Tekrar gözden geçir:** İkinci bir veri kaynağı eklenirse, ya da bir gün
kısmi seans (borsa açık ama 10'dan az isim işlem gördü) gerçekleşirse eşik
yeniden ölçülmeli. `bist saglik`'e bu durumu izleyen bir kontrol eklemek
Backlog'da.

---

## #011 — 2026-07-27 — Kuralları teste devret: proje kendi disiplinini kendi zorlar

**Bağlam:** Claude Code aboneliği bitiyor. Projeye bundan sonra daha zayıf
modeller (ya da aylar sonra bu bağlamı unutmuş biri) dokunacak. Somut soru şu:
*bu projenin kurallarını hatırlayan kimse kalmadığında ne olur?*

Cevap acıydı: kuralların neredeyse tamamı **yorumda yazılıydı, hiçbir yerde
zorlanmıyordu.** Bir model `zayif_n_esigi`'ni 15'ten 5'e çekse, `min_rr_t1`'i
1.2 yapsa, `outcomes` tablosuna bir kolon eklese ya da rejim politikasının
yönünü ters çevirse — suite yeşil kalırdı. Bu, denetimde bulunan hata sınıfının
tam olarak aynısı: **doğru görünen ama karşılığı olmayan savunma.**

**Seçenekler:**
- A) Dokümanı güçlendir (AGENTS.md'ye "şunu yapma" maddeleri ekle)
  → sıfır maliyet, sıfır zorlama. Okuyan uyar, okumayan uymaz.
- B) Kapsamı artır (satır kapsaması hedefi koy)
  → yanlış metrik: kapsam "kod çalıştı" der, "kural tutuyor" demez.
- C) **Kuralları koşulabilir sözleşmelere çevir** → üç katmanlı test mimarisi.

**Karar:** C.

    Sözleşme   — kodun VARSAYDIĞI yapı ayakta mı? (`tests/test_sozlesme.py`)
    Mekanizma  — doğru seriden/paydadan mı besleniyor? (modül başına)
    Uçtan uca  — zincir gerçekten koşuyor mu? (`tests/test_uctan_uca.py`)

Sıfır testi olan on üç modül kapsandı (`cli`, `report`, `indicators`, `factors`,
`regime`, `macro`, `universe`, `llm_io`, `diagnose`, `replay`, `sources/yf`,
`sources/evds`, `logging_setup`).

**Neden bu üçlü:** Bu projede bulunan en pahalı hatalar tek modülde değil,
**modüller arası varsayımda** çıktı — ve hepsi birim testlerinden geçiyordu
(paket faktör skorunu taşımıyordu, kalite kaydı eksikken dört tüketici de
"sorun yok" okuyordu, kalite kapısı sıkılaşınca replay'in tamamı elenmişti).
Bu sınıfı yakalayan tek şey uçtan uca kurulumdur; ama uçtan uca test de yapının
kaymasını görmez — onu sözleşme katmanı tutar.

**İki yapısal karar:**

1. **Eşikler artık zemine sahip.** `zayif_n_esigi ≥ 15`, `min_anlamli_fark_puan
   ≥ 1.0`, `min_rr_t1 ≥ 1.5`, `islem_maliyeti ≥ 0.30`, beyaz liste tavanı ≤ 31,
   ve rejim politikasının defansiflik yönü monoton. Gevşetmek isteyen bir testi
   de değiştirmek zorunda — yani karar GÖRÜNÜR olur.
   *Bu bir yasak değil, bir sürtünme:* ön kayıt disiplininin (§`docs/`) günlük
   hayattaki karşılığı.
2. **Doküman tutarlılığı makineye devredildi.** Belgelerdeki her `bist <komut>`,
   `config.<blok>.<anahtar>` atfı, dosya yolu ve `HF-xx` kodu koda karşı
   doğrulanıyor; ön kayıt mührünün sha256'sı testle korunuyor.

**Yan ürün — üç gerçek kırılganlık test yazarken çıktı** (üçü de düzeltildi):
`diagnose.verdict`'te sıfıra bölme; `diagnose.run`'da `0.0 or -1e9` tuzağı
(etkisi sıfır olan kol en kötü kol gibi sıralanıyordu); `ic_uygun` için None
koruması yokluğu (`ic_tum`'da vardı — savunma simetriğinde atlanmıştı).

**Ayrıca `pytest` yan etkisiz hale getirildi.** Ölçüldü: `cfg` fixture'ı yalnız
veritabanını geçici dizine yönlendiriyordu; `llm_in_dir`/`llm_out_dir`/
`reports_dir` GERÇEK repoyu gösteriyordu ve `write_bundle` çağıran bir test
kullanıcının klasörüne dosya bırakıyordu. Artık hem yazılan her yol geçici, hem
de gerçek veritabanına yazılabilir bağlantı açan test hata veriyor.

**Tekrar gözden geçir:**
- Bir eşik zemini gerçek bir işi engelliyorsa — o zaman zemin yanlıştır, ama
  değişikliğin gerekçesi ADR'ye yazılır ve test aynı commit'te güncellenir.
- Faz 8'de (GitHub Actions) suite CI'da koşacak; koşu süresi anlamlı biçimde
  büyürse pahalı ölçüm testleri (`test_report`, `test_diagnose`) ayrı bir
  markere alınır.
- Yeni bir tablo/kolon eklenirse `KOLON_SOZLESMESI` listesine de eklenmeli;
  eklenmezse test o tabloyu hiç görmez (kapsam sessizce daralır).

---

## #010 — 2026-07-27 — Denetim sonrası dört karar; ve KAP'ın sessiz kırpması

**Bağlam:** #009'un düzeltmeleri dört açık soru bıraktı. Dördü de burada
karara bağlandı; biri yol boyunca yeni bir veri kaynağı tuzağı ortaya çıkardı.

### 1. Replay yeniden koşuldu ✅

Journal'daki 28 kayıt, doğrulanmış İKİ hatası olan kodla üretilmişti (R:R'ı
şişiren kümeleme + karşı-olgu diye `ret_pct`'in kopyası). Tutmak, her gelecek
değerlendirmede iki uyumsuz kod sürümünü karıştırmak olurdu. Veri sentetik
(vekil analist) ve `reset` yalnız `tool='replay'`'e dokunuyor.
**Sonuç:** 20 tahmin, tetiklenmeme %35.0 (önce %46.4), boyutlandırma
karşı-olgusu −0.22pp (t=−2.51) — **ilk kez sıfırdan farklı**.

### 2. `min_rr_t1` DEĞİŞTİRİLMEDİ ✅

Dürüst seviyelerle 18 isimden 4'ü çıtayı geçiyor (önce 9). Değiştirmedim:
(a) plan SAYISI bir kalite metriği değil — ADR #008'e göre kenar iddiası yok;
(b) eldeki tek kanıt yeni ayarın LEHİNE (tetiklenmeme %46→%35, yani daha az
ama daha GERÇEKLEŞEBİLİR plan); (c) sonucu görüp çıta indirmek bu projede
yasaklanmış tek hareket.
**Ön kayıt yazıldı:** `docs/on-kayit-seviye-02.md` — tetikleyici koşullar ve
geçme şartı SONUÇ GÖRÜLMEDEN sabitlendi. O koşullar oluşmadan koşulmaz.

### 3. KAP geçmişi 90 gün — ve yol boyunca bir tuzak bulundu ⚠

Karar: 90 gün. Gerekçe: haber katmanının değeri İLERİYE dönük (karar anında
veto); geçmiş KAP'ın hiçbir tüketicisi yok, hiçbir ölçüm onu okumuyor, pakette
hisse başına zaten `limit=8` var.

**Ama uygulanırken ölçüldü ki KAP GENİŞ PENCEREYİ SESSİZCE KIRPIYOR:**

```
 7 gün istendi →  931 kayıt, 07-20…07-27   tam
14 gün istendi → 1578 kayıt, 07-13…07-27   tam
21 gün istendi → 1578 kayıt, 07-13…07-27   ⚠ KIRPILDI
90 gün istendi → 1578 kayıt, 07-13…07-27   ⚠ KIRPILDI
(2026-05-01…05-10 birebir döndü → `fromDate` ÇALIŞIYOR, sorun genişlik.)
```

Yani tek istekle 90 gün istemek 76 gününü **hata vermeden** kaybetmekti —
`evds.fetch_series_chunked`'in aştığı tuzağın aynısı, başka kaynakta.

Çözüm iki aşamalı oldu, ikincisi de ölçümden doğdu:
1. Aralık `parca_gun` (7) dilimlere bölündü → 209 → 1753 bildirim.
2. Ama Mayıs (bilanço sezonu) haftası **2000 kayıtla tavanı aştı**: bildirim
   hacmi MEVSİMLİK, sabit dilim genişliği kırılgan. → Doyan dilim kendini
   **ikiye bölüyor** (`cek()` özyinelemeli). Tek gün bile doyarsa itiraf
   ediliyor, sessiz kalınmıyor.
   **Sonuç:** 1837 bildirim, 70 ticker, 2026-04-28…07-27, sıfır boşluk.

Ayrıca bir yanlış alarm düzeltildi: "dilimin ilk günü boş" kırpılma DEĞİLDİR
(tatil olabilir). Ölçüt artık "yanıt kayıt tavanına dayandı".

### 4. `bist degerlendir` kaynak ayrımı ✅

Katı red fazla sert, sessiz karıştırma ise #009'un düzelttiği hata sınıfı.
**Karar:** tek kaynak varsa koş ve HANGİSİ olduğunu bas; birden çok kaynak
varsa DUR ve listeyle birlikte `--tool` iste (`KaynakKarisik`, çıkış kodu 2).
`replay` VEKİL bir analisttir; alfası gerçek LLM kayıtlarıyla aynı potaya
girmez.

**Tekrar gözden geçir:** (a) `on-kayit-seviye-02.md`'deki tetikleyicilerden
biri oluşursa o tur koşulur; (b) KAP dilim bölme derinliği 6'yı aşarsa
(tek gün bile doyuyorsa) sayfalama (pagination) desteği araştırılmalı.

---

## #009 — 2026-07-27 — Payda birinci sınıf çıktıdır; "veri yok" ile "sorun yok" hiçbir yerde aynı değere düşmez

**Bağlam:** Bağımsız bir denetim (salt-okunur, gerçek veriyle) bir kritik ve
beş yüksek şiddetli bulgu çıkardı. Hepsinin ortak imzası aynıydı: kod doğru,
veri sessizce dar ya da bayat, çıktı hâlâ "geçerli" görünüyor. Ayrıntı
`ai/LESSONS.md` L-007'de; en somut ikisi:

- Canlı evrende bildirimi olan 14 hissenin 8'inde **47 KAP bildirimi**
  pakete hiç girmiyordu (haber penceresi `created_utc`'ye dayanıyordu).
- Rejim, 67 isimlik evren yerine **16 isimle** hesaplanan %31 genişlikle
  `risk-off` diyor ve nakdi %90'a çıkarıyordu — XU100 SMA200'ünün %9.7
  üstündeyken.

**Karar — üç kural, kodda zorlanır:**

1. **Payda çıktının parçasıdır.** Oran/sıralama/yüzdelik üreten her fonksiyon
   paydayı da döndürür ve pakete yazar: `kesit.{istenen, skorlanan, uygun}`,
   `rejim.{genislik_n, genislik_istenen_n}`. Payda beklenenin %80'inin altına
   düşerse `log.warning`.
2. **Bilinmeyen, olumluya çevrilmez.** Kalite kaydı yoksa `ok=False,
   "kalite değerlendirilmedi"`; KAP çekilemediyse `haber_taramasi.ok=False`
   ve çıkış kodu ≠0. "Boş liste" ile "bakılmadı" ayrı alanlarda taşınır.
3. **Zaman referansı ANALİZ GÜNÜDÜR, duvar saati değil.** Journal'a ne zaman
   yazıldığı hiçbir filtreye girmez; `asof` girer. Dış kaynaktan gelen her
   damga yerel saatiyle birlikte alınır ve tek yerde UTC'ye çevrilir.

**Ayrıca kabul edilen sınırlar (gizlenmiyor, yazılıyor):**

- **HF-17 küçük tamsayı ve yuvarlak yüzdelere karşı geçirgen.** Ölçüldü:
  −50..+50 tamsayıların %56'sı izinli, iki ondalıklı uydurma fiyatların %0.5'i.
  Beyaz listeler bilinçli; sınır README + `config.denetim` yorumunda yazılı.
  `format_report` artık "temiz" derken bu sınırı da basıyor.
- **R:R planlar arasında kıyaslanabilir değil.** Hedef sabit, eşitsizlik girişi
  aşağı iterek/stop'u daraltarak sağlanıyor; ölçüldü, planların %46'sı hiç
  tetiklenmiyor. `rr_secim` + `elenen_adaylar` alanlarıyla görünür kılındı.
  Bu bir düzeltme DEĞİL, bir ifşadır — mekanizmayı değiştirmek ön kayıt ister.

**Düzeltmeler sonrası CANLI ÖLÇÜM (2026-07-27, gerçek veri):**

| ölçüm | önce | sonra |
|---|---|---|
| pakete giren KAP bildirimi | 12 | **45** (AKBNK/GARAN/EKGYO 0→8) |
| kesitsel skor evreni | 16 isim | **67** (uygun 10 → 27) |
| piyasa genişliği paydası | 16 | **67** (%31.25 → %32.84) |
| rejim etiketi | risk-off | **risk-off** — eşik yine aşılmadı |
| replay tetiklenmeme oranı | %46.4 | **%35.0** |
| boyutlandırma karşı-olgusu | tanım gereği 0 | **−0.22pp, t=−2.51** |

Rejim etiketinin değişmemesi, endişenin yersiz olduğunu göstermez: karar
16 isimlik bir paydayla veriliyordu ve doğru cevaba **şans eseri** denk geldi.

**Beklenmeyen bulgu — küme düzeltmesi R:R'ı düşürdü.** `levels._cluster`
tek-bağlantı zinciri, toleransın **2.9-16.2 KATI** arasında yayılan kümeler
üretiyordu. Asıl zarar hedefin uydurulması değil, **R:R'ın ŞİŞMESİYDİ**:
geniş zincir fiyatın hemen üstündeki gerçek direnci yutup kümenin ortalamasını
yukarı taşıyor, planlayıcı da "en yakın direnç" diye o uzak ortalamayı alıyordu.

    TCELL  fiyat 103.70 → en yakın direnç 116.30 (eski) / 103.92 (yeni)  −3.6×ATR
    SISE   fiyat  43.42 →                   47.83 /  44.20              −2.8×ATR
    PETKM  fiyat  22.02 →                   24.35 /  22.12              −2.6×ATR

Yani `min_rr_t1 ≥ 1.5` çıtası, olmayan bir mesafeyle aşılıyordu. Düzeltme
sonrası 18 canlı isimden yalnız 4'ü çıtayı geçiyor (önce 9). **Eşik
DEĞİŞTİRİLMEDİ** — sonucu görüp gevşetmek bu projede yasaklanmış tek hareket
(`docs/on-kayit-revizyon-01.md` §5). Karar ön kayıt bekliyor.

**Tekrar gözden geçir:** (a) gerçek LLM kayıtları N≥15'e ulaşınca
`sizing_counterfactual` artık gerçek bir sayı ürettiği için rejim
boyutlandırması İLK KEZ ölçülebilir olacak; (b) `min_rr_t1` / `min_dokunus` /
`kumeleme_atr_carpani` üçlüsü ön kayıtlı tek bir turda birlikte ölçülmeli.

---

## #008 — 2026-07-26 — Teşhis + ön kayıtlı revizyon turu #1 GEÇMEDİ → proje yeniden çerçeveleniyor

**Bağlam:** #007'de kapı kapandı. Üç farklı öneri geldi; değerlendirilip şu yol
seçildi: önce **teşhis** (revizyon turu SAYILMAZ), sonra teşhisin işaret ettiği
**tek** ön kayıtlı revizyon turu, başarısızlıkta ikinci tur yok.

### Teşhis — ayrışma bir bug DEĞİL, kapının kendisi

| Ölçüm | popülasyon | IC | t |
|---|---|---|---|
| `ic_tum` | kapısız tüm kesit | 0.042 | **2.42** |
| `ic_uygun` | SMA200 kapısından geçen havuz | 0.009 | **0.20** |

Sıralama bilgisinin **%79'u kapıda kayboluyor.** Enstrüman sağlam: seçim yönü
tutarlılığı %96; sentetik testlerde mükemmel momentumda IC≈1, ters sinyalde IC≈−1.

Atıf (referans −0.86pp'den tek-kol sapmalar): H=42 **+2.11pp** · SMA200 kapısı
kapalı **+1.15pp** · genişlik %50 +0.75pp · evren 18 +0.59pp · maliyet %0 +0.30pp.

IC ufukla **monoton** artıyor ve t(IC) beş ufkun hepsinde ≥2.2 —
tek şanslı hücre değil, doz-cevap ilişkisi:
H=5: 0.024 (t=2.88) · H=10: 0.027 (2.28) · H=20: 0.042 (2.42) ·
H=42: 0.065 (2.61) · H=63: 0.064 (2.21).

Ayrıca bulunan kurulum hatası: `high52_min_ufuk_gun=21` ve ana ufuk H=20 idi →
**en güçlü faktörün ağırlığı sıfırlanmıştı** (`high52_prox`: IC 0.059 t=3.38).

### Ön kayıtlı revizyon turu #1 — ve sonucu

Ön kayıt koşudan ÖNCE yazılıp mühürlendi: `docs/on-kayit-revizyon-01.md`,
sha256 `6677c296…`. İki değişiklik: SMA200 kapısı skorlama yolundan çıkar
(likidite+veri kapıları kalır) · ana ufuk H=42.

**Sonuç (OOS): N=21, Δ=+0.81pp, t=0.89 → `kenar yok`.**
Çıta |Δ|≥1.0pp idi. **GEÇMEDİ.**

Yön düzeldi (referans OOS −1.12pp → +0.81pp, yani +1.93pp iyileşme) ama ön
kayıttaki çıtaya ulaşmadı.

### Baştan çıkarıcı hücre — ve neden ona UYULMUYOR

Aynı koşuda `high52_prox` tek başına OOS'ta **+1.61pp (t=1.81), IC 0.113
(t=2.42)** → `zayıf kanıt: +1.6p` verdi. Çıtayı geçen tek satır bu.

**Bu satıra göre karar VERİLMİYOR.** Sebep: 34 karşılaştırmanın içinden sonucu
gördükten sonra en iyi hücreyi seçmek, ön kaydın engellemek için yazıldığı şeyin
ta kendisidir. Ön kayıtlı konfigürasyon birleşik skordu ve o geçmedi.
`high52_prox` **gelecekte ön kayıtlı bir tur için hipotez** olarak Backlog'a
yazıldı — bugünün kararına girmiyor.

**Karar:** Proje **yeniden çerçeveleniyor.** Sistem "izleme + risk disiplini +
haber/veto aracı" olarak tamamlanır: kenar iddia etmez, seviyeleri planlama
geometrisi olarak sunar. Faz 3-6 **yine kurulur** — değişen tek şey çıktının DİLİ.

**Neden bu doğru karar:** ölçüm harness'i tam da bunun için LLM katmanından önce
kuruldu ve iki turda üç kez kendi kendini düzeltti (dönem düşürme yanlılığı,
işarete kör kapı, işarete kör tanı fonksiyonu). Sistem bugün kendi hakkında
abartılı konuşamıyor — ürünün asıl değeri bu.

**Tekrar gözden geçir:** (a) 2+ yıl daha veri biriktikten sonra OOS N artar ve
aynı ön kayıt tekrar koşulabilir; (b) `high52_prox` için ayrı ve ön kayıtlı bir
tur; (c) evren 67'den BIST-100 tamamına genişletilirse kesitsel dağılım artar.
Üçü de YENİ ön kayıt ister — bu turun sonucu yeniden yorumlanmaz.

---

## #007 — 2026-07-26 — Faz 2 KAPISI KAPALI: mevcut faktör seti bu evrende pozitif kenar üretmiyor

**Bağlam:** Plan, LLM katmanına yatırım yapmadan önce faktörlerin ölçülebilir bir
kenarı olup olmadığını sormayı şart koşuyordu: *"OOS'ta hiçbir faktör EW tabanına
göre 'zayıf kanıt' seviyesine ulaşmıyorsa DUR."*

### Ölçüm kurulumu
67 hisselik ölçüm evreni, 2015-01 … 2026-07 (2.889 bar), H=20 işlem günü,
örtüşmeyen pencere, giriş t+1, %0.30 gidiş-dönüş maliyet, OOS bölme 2023-01-01,
116 dönem ölçüldü (15 dönem atlandı, raporlandı).

### Sonuç — kapı KAPALI

| | alfa vs EW | t | IC(tüm kesit) | t(IC) | hüküm |
|---|---|---|---|---|---|
| birleşik, tam | −0.86pp | −1.85 | 0.042 | 2.42 | kenar yok |
| birleşik, in-sample | −1.00pp | −1.50 | 0.043 | 1.98 | kenar yok |
| birleşik, **OOS** | −1.12pp | −1.76 | 0.049 | 1.76 | **zayıf kanıt: −1.1p** |

OOS'ta POZİTİF `zayıf kanıt` üreten faktör YOK. `mom_6_1`, `mom_12_1` ve
`birleşik` ters yönde kanıt üretiyor: seçtikleri isimler tabanın ALTINDA kalıyor.

### Yol boyunca bulunan İKİ HARNESS HATASI (ikisi de sonucu değiştirdi)

1. **Dönem düşürme = rejim seçme yanlılığı.** İlk sürüm `uygun < top_n` olan
   dönemleri atlıyordu. Ölçüldü: 131 dönemin **62'si** düşüyordu ve düşenler
   2016-2019 ile 2024-2025'in TAMAMI — yani ölçüm yalnız geniş boğa
   dönemlerinde yapılıyordu. Düzeltme: dönem atılmaz, portföy küçülür;
   atlananlar raporlanır.
2. **İşarete kör kapı.** `edge_verdict` bir BÜYÜKLÜK hükmüdür (|fark|). Kapı
   yalnız hükme baktığı için `mom_12_1` (−1.47pp, t=−2.64) kapıyı **AÇIYORDU** —
   güvenilir biçimde kaybettiren bir faktör "kanıt" sayılıyordu. Düzeltme: kapı
   pozitif işaret şartı arar; negatif kanıt ayrı ve değerli bulgu olarak raporlanır.
   Regresyon testi: `tests/test_backtest.py::TestKapiIsareti`.

### Üç ek bulgu (hepsi eyleme dönük)

- **Kapılar ZARAR veriyor:** kapılı −0.86pp (t=−1.85) vs kapısız +0.29pp (t=1.17).
  SMA200 kapısı sıralamadan ÖNCE elediği için skorun ayırt edeceği aralığı
  daraltıyor; kalan havuzda momentum sıralaması tersine dönüyor.
- **16 isimlik evrende ölçüm yapılamıyor:** dar evrende hiçbir faktör t>1.6
  üretemedi; 67 isme çıkınca IC t'leri 2.0-3.4'e yükseldi. Plan bunu baştan
  söylüyordu ("işlem evreni ≠ ölçüm evreni") — ilk uygulamada atlanmıştı.
- **IC ile alfa ayrışıyor:** IC(tüm kesit) tutarlı biçimde POZİTİF
  (0.035-0.059, t 2.0-3.4) ama dar seçimin alfası negatif. Yani zayıf bir
  sıralama bilgisi VAR, seçim onu getiriye çeviremiyor.

**Karar:** Faz 3-6'ya **geçilmiyor**. Plan gereği durup seçenekler Mert'e sunuluyor.

**Neden bu bir başarısızlık değil:** ölçüm harness'i tam da bunun için, LLM
katmanından ÖNCE inşa edildi. Faz 3-6 önce yapılsaydı bu bilgi haftalar sonra
ve çok daha pahalıya gelecekti. *"Sayıların küçülmesi dürüstlüğün büyümesidir."*

**Tekrar gözden geçir:** Ön kayıtlı (pre-registered) sınırlı bir revizyon turu
sonrası — ölçümün İŞARET ETTİĞİ üç değişiklik: (1) SMA200 kapısını kaldır,
(2) H=42 ufkunu ana ufuk yap, (3) kısa vadeli tersine dönüş işaretini test et.
Turun kaç varyant içerdiği ÖNCEDEN yazılır ve `bonferroni_note` uygulanır;
aksi halde "geçene kadar deneme" veri madenciliğidir.

---

## #006 — 2026-07-26 — Yahoo BIST tatillerinde HAYALET bar üretiyor; ayıklama ölçütü üç koşulun birleşimi

**Bağlam:** Veri kalite kapısı ilk çalıştırmada tüm 19 ticker'da aynı `bayat kapanış = 3`
değerini verdi. Aynı sayının her isimde çıkması sistematik bir iz — araştırıldı.

**Bulgu:** Yahoo, borsanın KAPALI olduğu günlerde de bar döndürüyor: hacim 0,
`o=h=l=c=önceki kapanış`. Kurban Bayramı 2026-05-27/28/29 (holidays_tr.yaml'de
tam gün tatil):

```
2026-05-26  o 297.50  h 298.00  l 295.25  c 296.75  v 11.744.557
2026-05-27  o 296.75  h 296.75  l 296.75  c 296.75  v 0     ← hayalet
2026-05-28  o 296.75  h 296.75  l 296.75  c 296.75  v 0     ← hayalet
2026-05-29  o 296.75  h 296.75  l 296.75  c 296.75  v 0     ← hayalet
```

Zararı sessiz ve yaygın: ATR bastırılır, volatilite olduğundan düşük ölçülür,
RSI/ADX bozulur, zaman bariyeri 4 güne kadar kayar.

**Kritik ikinci bulgu:** `XU100.IS` bu hatadan ETKİLENMİYOR — 2026'nın hiçbir
tatilinde endeks barı yok. Yani "geçmiş takvimi endeks barlarından türet" kararı
(#—, `calendar_bist.py`) hem doğru hem de ayıklama için otoriter ölçüt sağlıyor.

**Seçenekler:**
- A) `v=0` olan barları sil → SASA'nın 113 gerçek seans günü de silinirdi
- B) `o=h=l=c` olan barları sil → gerçek işlem durdurma günleri silinirdi
- C) Endekste barı olmayan günleri sil → endeksin kendi boşlukları gerçek barları silerdi
- D) Üçünün BİRLEŞİMİ

**Karar:** D — `o=h=l=c` **VE** `v=0` **VE** o gün endekste bar yok.
Ölçüm bu birleşimin kesinliğini doğruluyor (19 ticker × ~2946 bar):

| | satır | sonuç |
|---|---|---|
| Üç koşul birlikte | **841** | silindi — tamamı gerçekten tatil günü |
| Endekste yok ama bar gerçek | 142 | KORUNDU (endeksin kendi boşlukları) |
| Gerçek seansta düz + sıfır hacim | 63 | KORUNDU (ASELS 13, KCHOL 15 — işlem durdurma) |

Yalnız (C) kullanılsaydı 142, yalnız (A)+(B) kullanılsaydı 63 gerçek bar silinirdi.

Endeksin son barından SONRASINA dokunulmaz: endeks bir gün gecikebilir ve o
penceredeki hisse barları gerçektir (doğrulandı — THYAO 2026-07-24, hacim 23,4mn).

**Doğrulama:** ayıklama sonrası sıfır-hacim oranı 18 ticker'da %1.2 → **%0.0**,
bayat kapanış 3 → 1. SASA %45.2'de kaldı (onun sıfır hacimleri GERÇEK seans
günlerinde — kapı onu doğru olarak elemeye devam ediyor).

**Neden ayıklama boru hattının içinde:** `backfill()` ve `daily()` sonunda otomatik
çağrılıyor, ayrı bir `bist veri temizle` komutuna bırakılmadı — LESSONS L-002
("elle bir kere çalıştırılan script'ler sessizce donar").

**Tekrar gözden geçir:** Yahoo bu davranışı düzeltirse ayıklama 0 satır siler ve
zararsız hale gelir; kaldırmaya gerek yok. `tests/test_prices.py` tatil günlerinde
bar olmadığını doğruluyor — regresyon olursa CI söyler.

---

## #005 — 2026-07-26 — LLM hesaplanabilir hiçbir sayıyı üretmez

**Bağlam:** Finans odaklı LLM sistemlerinde en büyük problem yanlış tahmin değil,
uydurulmuş sayıyla özgüvenli konuşmak. "Hedef 324 TL civarı makul" cümlesi hiçbir
hesaba dayanmadan yazılabilir ve okuyan bunu hesaplanmış sanır.

**Seçenekler:**
- A) Prompt'ta "uydurma" de → prompt disiplini, zorlanamaz, sessizce ihlal edilir
- B) Çıktı şemasında fiyat alanı olmasın → yapısal sızıntıyı durdurur, prose sızıntısını DURDURMAZ
- C) B + prose'daki her sayısal token'ı bundle'a karşı doğrula (HF-17)

**Karar:** C. Python deterministik bir **plan menüsü** üretir (entry/stop/hedef/boyut);
LLM yalnızca `plan_id` seçer, enum verir, prose yazar. Çıktı şemasında fiyat/hedef/
stop/boyut/sayısal güven alanı **yoktur**. Ayrıca HF-17: prose'daki her sayısal token
`allowed_numeric_tokens(bundle)` içinde olmalı.

**Neden:** Halüsinasyonu prompt disiplini yerine **tip sistemi + denetim** ile
imkânsız kılmak. Asıl hata modu yapısal değil, metinsel — HF-17 taşıyıcı koldur.

**Yan karar — sterillik riski:** Sadece "A mı B mi" seçen ajan, seçtiğini
rasyonalize eden değersiz metin yazar. Üç panzehir: (1) gerçek **veto hakkı** +
zorunlu `veto_code`, (2) zorunlu **yanlışlayıcı** ("5 işlem gününde hangi gözlem bu
tezi çürütür?"), (3) `evaluate.llm_contribution()` — LLM sıralamasının IC'si vs saf
skorun IC'si. 40 dönem sonra fark ≤0 ise LLM veto+haber görevine indirilir.

**Tekrar gözden geçir:** `llm_contribution` 40 dönemde pozitif çıkarsa LLM'e daha
fazla serbestlik verilebilir. Veto değeri negatif çıkarsa veto kapatılır.

---

## #004 — 2026-07-26 — İki ayrı öğrenme döngüsü; hızlı döngünün metriği dönem-içi IC

**Bağlam:** "Sistem kendi hatalarından öğrensin" isteği doğru ama naif uygulaması
felaket: canlı journal yılda ~12 **bağımsız** gözlem üretir. Bu örneklemde faktör
ağırlığı optimize etmek gürültüye overfit etmektir.

**Seçenekler:**
- A) Tek döngü, canlı journal ağırlıkları da kalibre etsin → overfit, garantili
- B) İki döngü: yavaş (backtest) ağırlığı, hızlı (journal) kalibrasyonu kalibre etsin
- C) B, ama hızlı döngünün metriği **güven kalibrasyonu (Brier)** olsun
- D) B, ama hızlı döngünün metriği **dönem-içi IC** olsun

**Karar:** D.
- **Yavaş döngü:** 10 yıl × geniş evren walk-forward → faktör ağırlıkları. Yılda 1-2, **elle**.
- **Hızlı döngü:** canlı journal → ağırlığa **asla dokunmaz**. Ölçtüğü: dönem-içi IC,
  veto değeri, LLM katkısı, slippage, boyutlandırma karşı-olgusu, hata taksonomisi.

**Neden:** Brier için 3 kova × 30-50 olay = 100-150 çözülmüş tahmin gerekir ve
olaylar çapraz korelasyonludur (risk-off ayı hepsini birden çözer) — yani tek rejimi
ölçersin. Dönem-içi IC ise: her dönem 18 ismin **tamamını** kullanır (~6× bilgi),
**eşleştirilmiş** tasarımdır (piyasa faktörü tam sadeleşir; sd 15-20 → 5-6). 18 isimle
se(IC) ≈ 1/√17 ≈ 0.24; 40 dönemde se(ortalama) ≈ 0.038 → IC=0.08 t≈2.1 ile görülür.
**~18 ay**, "asla" değil. Brier kalır ama ikincildir ve 2 yıl "ölçüm yetersiz" der.

**Tekrar gözden geçir:** Karar sıklığı haftalıktan sıklaşırsa veya evren büyürse
IC'nin se'si düşer, süre kısalır — yeniden hesapla (`required_n`).

---

## #003 — 2026-07-26 — Sektör nötralizasyonu VARSAYILAN KAPALI (ölçüldü)

**Bağlam:** Kesitsel faktör skorlamasında sektör nötralizasyonu standart pratiktir.
Uygulamadan önce ölçüldü.

**Ölçüm** (2016-2026, eşit-ağırlık tabana göre, %0.30 maliyet):

| Faktör | Ham z | Sektör-nötr |
|---|---|---|
| 12-1 momentum | t=1.82, ort +0.94 | t=1.52, ort +0.63 |
| 6-1 momentum | t=1.86, ort +0.85 | **t=0.62**, ort +0.22 |

Nötralizasyon sd'yi düşürüyor (6.51→5.30) ama ortalamayı daha sert kesiyor.

**Karar:** `sektor_notr: false`. Kod yolu duruyor, varsayılan kapalı. Sektör kontrolü
skorlama katmanından **kısıt katmanına** taşındı: planlayıcıda "sektör başına maks 2".

**Neden:** BIST'te sektör momentumu **sinyalin kendisi** — bankalar tek blok hareket
eder ve "bankalar çalışıyor" gerçek bilgidir. Nötralize etmek onu çöpe atıyor.
ABD büyük-sermaye alışkanlığı; buraya transfer olmuyor.

**Tekrar gözden geçir:** Yavaş döngüde OOS'ta nötralizasyon lehine dönerse yeniden aç.

---

## #002 — 2026-07-26 — Birincil taban çizgisi eşit-ağırlık evren, XU100 DEĞİL

**Bağlam:** "XU100'e göre alfa" doğal taban gibi görünüyor. Ölçüldü.

**Ölçüm** (2026-07-26, 29 likit isim, eşit ağırlık, H=15, örtüşmeyen, N=175):
```
Eşit-ağırlık sepet vs XU100:  ort=+0.36pp  med=+0.29pp  kazanma=%60  t=2.89
```
**Sıfır beceriyle** XU100 yeniliyor (t=2.89). XU100 sermaye-ağırlıklı; eşit ağırlık
küçük-büyük eğilimi taşıyor. Geniş evrende bu fark daha da büyüyor (48 isimde +0.60pp).

**Karar:** Birincil taban = **eşit-ağırlık, veri-kalite kapısından geçmiş canlı evren**
(aynı denge tarihleri, aynı maliyet modeli). XU100 raporda kalır ama **yalnız iletişim
amaçlı** ve "sermaye-ağırlık eğilimi içerir" etiketiyle. **Hüküm daima EW'ye göre.**

**Neden:** `gold_tracking_system`'in `measure_edge` konvansiyonu — bilgi mutlak değerde
değil, **koşulsuz tabandan farkta**. Yanlış taban seçmek, sıfır beceriyi kenar diye
raporlamaktır. Bu düzeltme ölçülen kenarı ~1/3 oranında küçültüyor; küçülen sayı
doğru sayıdır.

**Tekrar gözden geçir:** Evren kompozisyonu değişirse EW–XU100 farkını yeniden ölç.

---

## #001 — 2026-07-23 — Taşınabilirlik için AGENTS.md standardı + düz markdown hafıza

**Bağlam:** Claude Code aboneliği bitince Cursor, Antigravity, VS Code gibi
farklı araçlara geçilecek. Usta sistemi her araçta aynı şekilde çalışmalı.

**Seçenekler:**
- A) Araca özel özellikler (.claude/commands, .cursorrules...) → güçlü ama her araçta yeniden kurulum gerekir
- B) Tek AGENTS.md + düz markdown hafıza dosyaları → her uyumlu araç okur, kilitlenme yok
- C) Fine-tuning / özel model → pahalı ve gereksiz; sorun davranış+bağlam sorunu, bilgi sorunu değil

**Karar:** B. AGENTS.md kanonik dosya; CLAUDE.md, GEMINI.md ve
copilot-instructions.md yalnızca ona işaret eden köprüler. Komutlar araç
özelliği değil, AGENTS.md içinde "sözleşme" olarak tanımlı.

**Neden:** AGENTS.md araçlar arası fiili standart (Claude Code, Cursor,
Antigravity, Copilot, Codex destekliyor). Düz markdown hiçbir araca bağımlı
değil; git ile taşınır, her yerde okunur.

**Tekrar gözden geçir:** Ana kullanılan araç AGENTS.md desteğini bırakırsa
veya araca özel bir özellik (ör. gerçek slash komutları) ciddi verim farkı
yaratmaya başlarsa.

---

<!-- Yeni karar şablonu:

## #NNN — YYYY-MM-DD — Kısa başlık

**Bağlam:** Hangi sorun/ihtiyaç bu kararı doğurdu?

**Seçenekler:**
- A) ... → artı/eksi
- B) ... → artı/eksi

**Karar:** Seçilen şey.

**Neden:** Hangi kısıta/hedefe dayanarak?

**Tekrar gözden geçir:** Hangi koşul oluşursa bu karar masaya geri gelir?
-->
