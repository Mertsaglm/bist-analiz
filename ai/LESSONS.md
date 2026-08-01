# LESSONS.md — Dersler ve Anti-Pattern'ler

> Geçmiş hatalardan çıkan dersler. Usta bunları bilir ve aynı çukura ikinci
> kez düşülmesine izin vermez. `/ders <olay>` komutuyla yeni ders eklenir.
> Bu dosya projeler arası taşınır — dersler birikir.

---

## L-011 — 2026-08-01 — Denetimde yaşayan ama istemde yazmayan kural, modelden imkânsızı istemektir

**Olay:** İlk otonom turda zincirdeki **altı modelin altısı da** denetimden
düştü. Elle koşulan tur (2026-07-29) ilk denemede geçmişti — ikisi arasındaki
tek fark şuydu: insan analist `audit.py`'yi OKUYABİLİYORDU, model okuyamaz.

Düşme sebepleri, hepsi istemde YAZMAYAN kurallardı:

    HF-26  prose < 80 karakter   → 6/6 modelde. İstem yalnız `<prose>` diyordu,
                                   minimum uzunluğu HİÇ söylemiyordu.
    HF-10  veto_code enum dışı   → izinli kodlar listelenmemişti
    HF-14  plan_sec eşliği       → `selected_plan_id`'nin hangi aksiyona bağlı
                                   olduğu anlatılmamıştı
    HF-20  sinyal↔aksiyon        → boğa sinyali ile `islem_yok` çelişkisi
                                   hiçbir yerde yazmıyordu
    HF-30  açık tahminler        → zorunluluk söylenmemişti

İstem sözleşmeyle hizalandıktan sonra (eşikler config'ten okunarak, gömülmeden)
**ilk halka ilk denemede geçti.** Yani modeller yetersiz değildi; kurallar
görünmezdi.

**Ders:** Bir sözleşmenin iki tarafı vardır — ZORLAYAN (denetim) ve UYMASI
İSTENEN (analist). Bu ikisi ayrı dosyalarda yaşadığı için sessizce ayrışırlar
ve ayrışmanın faturası "model kötü" diye okunur. Kuralı yalnız zorlayıcı
tarafa yazmak, sınavı öğrencinin görmediği bir müfredattan yapmaktır.
Aynı asimetrinin ikinci hâli aynı gün çıktı: çıktı token tavanı AÇIKÇA
verilmediği için sağlayıcının varsayılanına düşüldü ve JSON 17.000 karakterde
sessizce kesildi — hata "geçersiz JSON" diye göründü, sebebi görünmedi.

**Kural:** Bir denetim/doğrulama kuralı eklerken sor: *"bu kurala uyması
beklenen taraf onu NEREDEN öğrenecek?"* Cevap "kodu okuyarak" ise kural
görünmez demektir; istemde (ya da arayüzde) açıkça yaz — ve eşiği koda
gömme, tek kaynaktan (config) oku ki eşik değişince metin de değişsin.
İkinci soru: *"bu değeri açıkça vermezsem kim karar verir?"* Cevap
"sağlayıcının varsayılanı" ise, o varsayılan bir gün sessizce aleyhine çalışır.

---

## L-010 — 2026-08-01 — Kontroller birbirini doğruluyorsa hiçbiri dış dünyaya bakmıyordur

**Olay:** Faz 8'de otonom koşu kurulurken `bist saglik` incelendi. Sekiz
kontrolün üçü (gösterge kapsaması, gösterge tazeliği, kalite kapısı)
`MAX(bars_daily.date)` ile karşılaştırma yapıyordu. Yani **referans noktası
verinin kendisiydi.** Barlar bayatlarsa `asof` da bayatlar, gösterge ve kalite
ona uyumlu kalır — ve üç kontrol birden **TEMİZ** der.

Gerçek koşuda görüldü: cuma barı gelmemişti, sistem perşembe verisiyle
çalışıyordu ve sağlık kontrolü ✓ basıyordu. Otomasyonda karşılığı şu olurdu:
veri gelmediği her gün DÜNKÜ rapor bugünmüş gibi Telegram'a düşer, hiçbir
uyarı çıkmaz.

**Ders:** Bir kontrol kümesi kendi içinde tutarlıysa bu, sistemin doğru
çalıştığını GÖSTERMEZ — yalnız kontrollerin aynı kaynağa baktığını gösterir.
L-007 "payda"yı sormayı öğretmişti; bu onun bir üst katmanı: **referans
noktasını sor.** İç tutarlılık ölçen kontroller, dış dünyayla bağı kopmuş bir
sistemi mutlulukla onaylar.

**Kural:** Bir sağlık/doğrulama kontrolü yazarken sor: *"bu neyle
karşılaştırıyor — verinin kendisiyle mi, dışarıdaki bir gerçekle mi?"*
Kontrol kümesinde EN AZ BİR tanesi dış referansa (takvim, duvar saati, bağımsız
kaynak) bakmalı; hepsi içeriye bakıyorsa küme bir yankı odasıdır. Ve o dış
referansı yazarken zaman kaynağını AÇIKÇA belirt (AGENTS.md §11 madde 6) —
testler o referansı dondurabilmeli, yoksa suite takvim ilerledikçe kayar.

---

## L-009 — 2026-07-29 — Belgelenen AKIŞ da bir iddiadır: eksik adım boş ama "geçerli" çıktı üretir

**Olay:** İlk gerçek LLM turunda README'nin "Günlük akış" bölümü harfiyen
izlendi: `veri gunluk → haber cek → gunluk`. Üretilen paket **yapısal olarak
geçerliydi ama tamamen boştu**: 67 istenen isimden **0'ı skorlandı**, toplam
**0 plan**, her hissenin faktör skoru `None`, rejim genişliği paydası `0`.
Rejim yine de bir etiket bastı — `transition` — ve o etiket sıfır paydadan
geliyordu. Hiçbir komut hata vermedi, çıkış kodları temizdi.

Sebep: `bist veri gunluk` kalite kapısını **otomatik koşuyor** ama
`bist gosterge`'yi koşmuyor. README'nin günlük akışında `gosterge` **hiç
geçmiyor**; yalnız "Kurulum (bir kez)" bölümünde var ve yanındaki not
"evren her değiştiğinde TEKRAR koş" diyor. Oysa her yeni bar yeni bir
`indicator_daily` satırı gerektirir — yani gerçek koşul "evren değişince"
değil, **"her gün"**. Belgedeki koşul, kodun gerçek ihtiyacından dardı.

`bist saglik` bu bozulmayı KRİTİK olarak yakalıyor (gösterge tazeliği). Ama
README onu "Her şeyden önce" diye sunuyor; `veri gunluk`'tan ÖNCE koşulduğunda
henüz görecek bir bayatlık yoktur ve temiz rapor verir. Yani doğru kontrol,
belgelenen sırada yanlış anda koşuyordu.

**Ders:** Bir eksik adım her zaman hata fırlatmaz — çoğu zaman **boş ama
şeklen geçerli** bir çıktı üretir ve zincirin geri kalanı onu sorunsuz işler.
L-007'nin ("kod doğru, veri sessizce dar") akış düzeyindeki kardeşi bu:
burada dar olan veri değil, **belgelenen prosedürdü**. Ayrıca bir otomasyon
asimetrisi vardı: aynı komut kalite kapısını otomatik koşup göstergeyi
koşmuyordu — L-008'in "simetriğini ara" kuralı tam da buraya bakıyordu.

**Kural:** Bir akış belgelendiğinde iki soru sorulur: (a) bu adımların
tamamı gerçekten yeterli mi — akışı **taze bir günde uçtan uca koşarak**
doğrula, adımları okuyarak değil; (b) bir adım atlanırsa ne olur — hata mı
verir, yoksa boş ama geçerli çıktı mı üretir? İkincisi ise ya adımı otomatiğe
bağla ya da atlanmasını **kapı** hâline getir. Ve bir ön-uçuş kontrolünü
belgelerken **hangi andan sonra** koşulacağını yaz: yanlış anda koşan doğru
kontrol, olmayan kontroldür.

---

## L-008 — 2026-07-27 — Bir düzeltmeyi tek çağrı yerinde yapmak, kuralı uygulamak DEĞİLDİR

**Olay:** Kapsamlı bir test turu yazılırken, daha önce "kapatıldı" sayılmış üç
savunmanın **simetriğinin açık kaldığı** görüldü. Üçü de aynı kalıp:

1. `real_con` fixture'ı salt-okunur yapılmıştı (pytest kullanıcının
   veritabanını değiştiriyordu). Ama düzeltme TEK ÇAĞRI YERİNDEYDİ — yeni bir
   testin aynı tuzağa düşmesini engelleyen hiçbir şey yoktu.
2. Aynı fixture veritabanını geçici dizine yönlendiriyordu ama
   `llm_in_dir`/`llm_out_dir`/`reports_dir`'i yönlendirmiyordu. Sonuç: paket
   üreten her test kullanıcının repo'suna klasör bırakıyordu — ölçüldü,
   `llm/in/<tarih>/` gerçekten oluşuyordu.
3. `diagnose.verdict` `ic_tum` için None koruması yazmıştı, simetriği olan
   `ic_uygun` için yazmamıştı. Üstelik erişilebilir bir durumdu: kapılı havuz
   her dönem 3 isimden aza düşerse tam da "kapı bilgiyi yok ediyor" tanısının
   metni `TypeError` ile patlıyordu.

Aynı turda ikinci bir sınıf daha çıktı: **kural yorumda yazılı, hiçbir yerde
zorlanmıyor.** `zayif_n_esigi`'ni 15'ten 5'e çekmek, `min_rr_t1`'i indirmek,
rejim politikasının yönünü ters çevirmek — hiçbiri testi kırmıyordu. Oysa
bunların hepsi projenin yazılı kararlarıydı.

**Ders:** Bir hatayı düzeltmek iki ayrı iştir ve ikincisi genellikle atlanır:
(a) bu çağrı yerini düzelt, (b) **aynı hatanın bir daha yapılamayacağı yeri**
düzelt. Yalnız (a) yapıldığında kural, onu hatırlayan kişinin ömrü kadar yaşar.
Bu proje için o ömür artık ölçülebilir biçimde kısa: bağlamı taşımayan bir
model ya da aylar sonraki sen.

Ve şu ayrım net: **yorum bir niyettir, test bir zorlamadır.** "Bu eşik
düşürülmemeli" cümlesi bir dilek; `assert esik >= 15` bir sözleşme.

**Kural:** Bir savunma yazdıktan sonra üç soruyu sor:
- **Simetriği var mı?** (`ic_tum` korunduysa `ic_uygun` de korunmalı; `db`
  yönlendirildiyse `reports_dir` de.) Aynı kalıbın diğer örneklerini ARA.
- **Bir sonraki kişi bunu bilmeden bozabilir mi?** Bozabiliyorsa savunma
  değil, not almışsın demektir.
- **Kuralı koşulabilir hale getirebilir miyim?** Getirebiliyorsan getir —
  eşik zeminleri, kolon↔şema eşliği ve doküman atıfları bu şekilde
  teste devredildi (ADR #011).

---

## L-007 — 2026-07-27 — Kod doğru, VERİ sessizce dar: paydayı yazmayan her oran yalan söyleyebilir

**Olay:** Bağımsız bir denetim, birbirinden habersiz görünen ama aynı sınıftan
olan dört hata buldu. Dördünde de kod doğruydu; bozulan şey kodun VARSAYDIĞI
veri durumuydu ve hiçbiri hata fırlatmıyordu:

1. **Haber katmanı kör.** Paket, "son analizden bu yana çıkan haberler"i
   `MAX(created_utc)` ile belirliyordu. `created_utc` kaydın DİSKE YAZILDIĞI
   andır. `bist replay` 2024-2026'yı tek seferde yazınca her hissenin
   damgası "şimdi" oldu ve `published_utc > since` hiçbir şeyi geçirmedi.
   Bildirimi olan 14 hissenin 8'inde **47 gerçek KAP bildirimi** gizlendi —
   üstelik ADR #008 sonrası haber/veto sistemin kalan ana ürünü.
2. **Kesit 67 yerine 16 isim.** `bist gosterge` Faz 1'de 19 ticker için
   koşulmuştu; Faz 2'de ölçüm evreni 67'ye çıktı ama göstergeler yeniden
   hesaplanmadı (backtest onlara ihtiyaç duymuyor, kimse fark etmedi).
   `factors._panel` ve `regime.breadth` `indicator_daily`'ye JOIN atıyor;
   eksik ticker sessizce satır üretmiyor. Sonuç: `pct=100` "67'de birinci"
   değil "10'da birinci" demekti — ve **rejim 5/16 = %31 genişlikle risk-off**
   dedi, XU100 SMA200'ünün %9.7 ÜSTÜNDEYKEN. Nakit önerisi %90'a çıktı.
3. **Kalite kapısı sessizce kapanıyor.** `quality_map` TAM TARİH eşleşmesi
   arıyordu; `assess_quality` ise yalnız elle koşuyordu. Fiyat bir gün
   ilerleyince sorgu boş döndü ve dört tüketicinin dördü de "kayıt yok"u
   "sorun yok" diye okudu — paket `veri_kalitesi: ok=true` yazdı.
4. **HF-22 evrenin %44'ünde ölü.** `yuzdelik` yalnız kapıdan geçen isimlerde
   dolar; kontrol `if pct is not None and pct < esik` diyordu. Yani sıralama
   koruması tam da kapının ELEDİĞİ isimlerde atlanıyordu.

**Ders:** Bu projede en pahalı hata sınıfı mantık hatası değil, **"kod doğru
ama veri sessizce dar/bayat"**. Ortak imza şu: bir oran ya da sıralama
üretiliyor, PAYDASI hiçbir yerde yazmıyor, ve payda düştüğünde çıktı hâlâ
"geçerli" görünüyor. `edge_verdict` disiplini paya uygulanmış ama paydaya hiç
uygulanmamıştı. Ayrıca L-002 ("elle çalıştırılan script donar") doğru
çıkarılmış ama YENİ tablolara uygulanmamıştı — ders bir kere öğrenilip
bırakılmıyor, her yeni veri kaynağında tekrar sorulması gerekiyor.

**Kural:** Bir oran, sıralama ya da yüzdelik üreten her fonksiyon **paydayı da
döndürsün ve çıktıya yazsın** (`kesit.istenen/skorlanan`, `rejim.genislik_n`).
Payda beklenenin %80'inin altına düşerse `log.warning`. "Kayıt yok" durumu
ASLA "sorun yok"a çevrilmesin — varsayılan `ok=False, "değerlendirilmedi"`
olsun. Ve yeni bir tablo/kaynak eklerken üç soruyu birlikte sor:
(a) bunu kim, ne sıklıkla besliyor? (b) beslenmezse ÇIKTI nasıl görünür?
(c) o görünüm "veri yok" ile "sorun yok"u ayırt ediyor mu?

---

## L-006 — 2026-07-27 — Büyüklüğe bakıp anlamlılığa bakmamak; ve "kapı" fonksiyonlarının işaret körlüğü

**Olay:** Tek bir oturumda AYNI kalıp DÖRT kez tekrarladı ve dördü de sistemi
kendi lehine yanıltıyordu:

1. `edge_verdict` bir BÜYÜKLÜK hükmü (|fark| ≥ eşik). Faz 2'nin kapı mantığı
   yalnız hükme bakıyordu → `mom_12_1` (−1.47pp, t=−2.64) kapıyı **AÇTI**.
   Güvenilir biçimde KAYBETTİREN bir faktör "kanıt" sayıldı.
2. `diagnose.verdict` `ic_uygun > 0` diye kontrol ediyordu → IC=0.009 (t=0.20),
   yani düpedüz sıfır, "pozitif" sayılıp yanlış tanı üretti.
3. `ic_summary` IC hükmünü de `edge_verdict`e veriyordu → IC=0.057 / t=1.46
   "zayıf kanıt" ilan edildi. IC için mutlak büyüklük anlamlı bir eşik DEĞİL.
4. `llm_io._varyantlar` sayı biçimlerini YUVARLAYARAK üretiyordu → prose'daki
   uydurma "47.3", "47" varyantını doğurup pakette 47.00 varsa HF-17'yi atladı.

**Ders:** Bir eşik fonksiyonu yazarken iki soruyu AYRI sormak gerekiyor:
"fark yeterince BÜYÜK mü?" ve "fark yeterince GÜVENİLİR mi (işaret + anlamlılık)?".
Birini diğerinin yerine kullanmak, sonuç lehimize olduğunda fark edilmez —
çünkü çıktı "iyi" görünür. Bu, bu projede tek başına en tehlikeli hata sınıfı:
sistemin kendini kandırmasını sağlar ve kandırmayı fark edecek kimse yoktur.

**Kural:** Bir "kapı"/"hüküm" fonksiyonu yazarken üçünü de açıkça yaz ve
TESTİNİ KOY: (a) N yeterli mi, (b) İŞARET doğru yönde mi, (c) fark ANLAMLI mı.
Farklı birimler (yüzde puan, korelasyon, olasılık) farklı eşik türü ister —
bir birimde çalışan `edge_verdict`i başka birime taşıma. Ayrıca: bir denetim
kuralı yazarken "bunu nasıl atlatırdım?" diye sor ve o kaçış yolunu teste çevir.

---

## L-005 — 2026-07-26 — "Bilinen sorun" bilgisi bayatlar; inancı fixture testine çevir

**Olay:** BIST veri kaynağı araştırmasında iki "bilinen sorun" bulundu: yfinance'in
`.IS` hisselerinde temettü düzeltmesi yapmadığı (GitHub issue #1788) ve XU100'ün
2020 bölen değişiminde bozuk olduğu. Mimari bu iki inanç üzerine kurulmak üzereydi
(ikinci veri kaynağı + ağır kurumsal işlem katmanı). Ölçülünce **ikisi de bugün
geçerli değildi**: TUPRS 2025-03-28 temettüsünde ham getiri −%2.95, düzeltilmiş
+%2.67 — düzeltme çalışıyor. XU100 sürekli. Gerçek kusur bambaşka yerdeydi ve
araştırmada hiç geçmiyordu: SASA'nın 505 barının 117'sinde hacim sıfır (%23.2).

**Ders:** Bir kütüphane/veri kaynağı hakkındaki "bilinen sorun" kaydı **tarihlidir**
— issue kapanmış, kaynak düzelmiş olabilir. Üstelik bu inançlar üzerine kurulan
mimari (ikinci kaynak, ağır düzeltme katmanı) hem pahalı hem gereksizdi. Asıl
kusurlar genellikle genel değil, **kayıt bazlı** (ticker-spesifik) ve ancak
kendi verine bakınca görünür.

**Kural:** Veri kaynağı davranışına dair her varsayımı, mimariye koymadan önce
(a) canlı veriyle ölç, (b) **fixture testine çevir** ki kaynak regresyona giderse
CI söylesin. "İnternette şöyle yazıyor" bir tasarım girdisi değil, doğrulanacak
bir hipotezdir. Ayrıca genel kusur aramak yerine **kayıt bazlı kalite kapısı** kur.

---

## L-004 — 2026-07-24 — Kural dosyaları alt klasörde çalışmaz

**Olay:** Usta sistemi `Proje Yardımcısı/` alt klasörüne kopyalanmıştı. Hiçbir
IDE alt klasördeki AGENTS.md/CLAUDE.md'yi otomatik okumadığı için sistem atıl
kaldı — hata vermiyor, sadece sessizce devreye girmiyordu.

**Ders:** Araç konvansiyonuna bağlı dosyaların (kural, config, manifest) YERİ
işlevin parçasıdır. Yanlış yerdeki doğru dosya = yok hükmünde.

**Kural:** Kural/köprü dosyalarını daima proje köküne koy; kurduktan sonra
"gerçekten yükleniyor mu?" diye test et (`/durum` yazıp STATE.md'yi okuyor mu),
dosyanın varlığını görmek yeterli değil.

---

## L-003 — 2026-07-24 — Metrik değişince "sistem bozuldu" sanılır; taban çizgisini ölç

**Olay:** "Kapsama %16'dan %62'ye çıktı, arşiv düzensiz çalışıyor, kesinti
545 dk" diye bir arıza iddiası geldi. Ölçünce ham toplama hızının 07-08'den
beri sabit olduğu (medyan 13 kayıt/gün) görüldü — değişen tek şey metriğin
PAYDASI'ydı (07-21 kalibrasyon commit'i). Ayrıca "545 dk kesinti" altyapı
arızası değil, kaynağın boş dönmesiydi.

**Ders:** Bir sağlık metriğindeki sıçrama, çoğu zaman sistemin değil ÖLÇÜMÜN
değiştiğini gösterir. Rapor çıktısındaki yüzdelere bakıp arıza teşhisi koyma;
altındaki HAM sayıya (kaç kayıt/gün) ve metrik formülünün ne zaman
değiştiğine (git log) bak.

**Kural:** "X bozuldu" iddiasında önce ham taban çizgisini zaman serisi olarak
çıkar; sonra metrik tanımının değiştiği commit'i ara. İkisi de temizse iddia
düşer. Ayrıca: iki farklı olguyu benzer kelimelerle raporlama ("kesinti" vs
"boşluk") — okuyanı yanıltır, yanlış alarm üretir.

---

## L-002 — 2026-07-24 — "Elle bir kere çalıştırılan" script'ler sessizce donar

**Olay:** `history_daily` tablosu yalnızca elle çalıştırılan bir backfill
script'i (`src/history.py`) tarafından yazılıyordu, otomatik günlük pipeline'a
hiç bağlı değildi. 17 gün boyunca donuk kaldı ve bunu fark eden hiçbir alarm
yoktu — botun kendi mesajları (ATR(75) tekrarı) tek işaretti, onu da elle
export inceleyince gördük.

**Ders:** "Bir kere elle çalıştırdım, gerisi otomatik" varsayımı yanlıştır —
o script otomatik pipeline'a bağlı DEĞİLSE, üretilen veri günün birinde donar
ve hiçbir hata fırlatmaz (sessiz bozulma). Bir tabloyu/dosyayı besleyen HER
script'in ya otomatik pipeline'a bağlı olduğunu ya da neden bağlı olmadığını
(gerçekten tek seferlik mi?) doğrula.

**Kural:** Yeni bir veri kaynağı/tablo eklenince sor: "Bunu kim, ne sıklıkla
güncelliyor?" Cevap "kimse / elle" ise ya otomatiğe bağla ya da STATE.md'ye
"manuel bakım gerekir" diye açıkça yaz.

---

## L-001 — 2026-07-24 — Yerel repo üretimin gerisinde kalır

**Olay:** Denetimde yerel checkout'a bakıldı; veri 21 Tem'de "durmuş" göründü.
Aslında GitHub Actions kesintisiz commit'liyordu (40 commit ileride); yerel
kopya pull edilmemişti.

**Ders:** Actions'ın otomatik commit attığı projelerde yerel kopya sürekli
geride kalır; yerel duruma bakıp "sistem durdu" sonucu yanlış olur.

**Kural:** Proje sağlığını denetlemeden önce daima `git fetch` + yerel/uzak fark
kontrolü (`git rev-list --count HEAD..origin/main`) yap. Yerel eskiyse önce
`origin/main`'e bak, sonra konuş.

<!-- Yeni ders şablonu:

## L-NNN — Kısa başlık

**Olay:** Ne oldu?

**Ders:** Genelleştirilmiş çıkarım.

**Kural:** Usta bundan sonra somut olarak ne yapacak/soracak?
-->
