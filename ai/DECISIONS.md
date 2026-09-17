# DECISIONS.md — Karar Günlüğü (ADR)

> Yalnızca ÖNEMLİ kararlar: mimari, araç, yaklaşım seçimleri.
> Her karar "neden"i ve "tekrar gözden geçirme koşulu" ile kaydedilir.
> En yeni karar en üste.

---

## #024 — 2026-09-17 — Seans içi V2, GitHub cron değil yerel uyanık runner ile çalışır

**Bağlam:** 2026-09-16'da GitHub Actions, iki repodaki saatlik `portfolio.yml`
tetiklemelerinin çoğunu hiç başlatmadı. Başlatılan geç iş işlem penceresi dışına
sarktı; salt-okur nöbetçi doğru olarak `missed_cycle` ile kırmızıya döndü.

**Karar:** Mert'in macOS'unda `launchd`, V2 çevrimini yalnız işlem penceresinde
10 dakikada bir çalıştırır. Her koşu önce `main`i fast-forward günceller, yalnız
temiz çalışma ağacında devam eder, sonra defter ve Telegram makbuzunu ayrı
commit/push ile teslim eder. GitHub Actions üretim yedeği, recovery ve bağımsız
gözcü olarak kalır; yerel runner eksikliği gizlemez.

**Neden:** V2'nin işlem kapısı seans içi kotasyon ister; kapanış-sonrası tek
günlük koşu yeni işlemi sistematik olarak `VERİ BEKLENİYOR`a düşürür. GitHub
cron ise saatlik zaman garantisi vermez. Mac uyanıkken `launchd` bu dar zaman
gereksinimi için daha güvenilir ve ilave ücret gerektirmeyen tek mevcut ortamdır.

**Sınır:** Mac kapalı veya uykudaysa yerel süreç de koşamaz. Bu fiziksel sınır
gözcü ile görünür kalır; kesintisiz garanti gerekirse bir sonraki seçenek sürekli
haricî runner'dır.

**Tekrar gözden geçir:** Mac'in seans saatlerinde düzenli kapalı kaldığı veya
üç işlem gününde teslim aralıkları 10 dakika + çevrim süresini aştığı ölçülürse.

---

## #023 — 2026-09-16 — Üç öncelik grubu, koruyucu karar ve ölçülebilir sonuç

**Bağlam:** Kullanıcı 25 öneriyi dört öncelik grubuna ayırıp ilk üç grubun
uygulanmasını istedi. Önceki 25/26 bakım maddeleri tekleştirildi; 8+7+7+3 dağılımı.

**Seçenekler:** Bağımsız yeni sistem/paket açmak bakım ve yayın parçalarını artırır.
Mevcut iki projede ortak karar motoru ve checksum manifesti, mevcut işletimi korur.

**Karar:** İlk 22 madde iki projeye yerelde uygulandı. Koruyucu çıkış analiz
kalitesinden ayrılır; güncel fiyat şartı korunur. Eski fiyat yeni risk bütçesi
üretmez. Başarı kanıtı örtüşmeyen dönemlerle ölçülür. Sabit/günlük model ayrı
sanallarda karşılaştırılır; otomatik terfi yoktur. Tam portföy geçmiş deneyi
araştırmadır; güncel evren/düzeltilmiş fiyat/banka makası sınırları açıkça yazılır.
Yedek/nöbetçi ayrı salt-okur workflow'lardır; onarım kapısı değildir.

**Bedel:** Kod kopyaları manifest eşliği gerektirir. Bağımlılık yükseltmesi iki
suite ve kilit güncellemesi ister. Mühürlü karar kodları ve modeller arşivi büyütür.
Tarihsel üyelik, gerçek masraf ve temettü ödeme kanıtı dış kaynak gerektirir.

**Tekrar gözden geçir:** Bağımsız sanal dönemler yeterli olduğunda risk/model
seçimini; arşiv büyüdüğünde saklama politikasını; doğrulanmış tarihsel veri
edinildiğinde geçmiş deneyinin varsayımlarını yeniden değerlendir.

**Kapsam dışı:** Panelden ayar, gerçek işlem günlüğü, etkileşimli senaryo ekranı.
Commit/push/deploy ve gerçek mesaj bu yerel çalışma sırasında yapılmadı.
Ayrıntı: `docs/IYILESTIRME-2026-09-16.md`, `reports/IYILESTIRME-2026-09-16.md`.

---

## #022 — 2026-09-15 — Ayrı sanal defter, ortak panel ve ölçülen öğrenme

**Bağlam.** Kullanıcı iki projeyi revize etmeyi, her birine aylık 5.000 TL sanal bütçe,
İş Bankası referansı, anlaşılır kararlar ve web/Telegram takibi eklemeyi istedi.
Eski BIST karnesi seçilmiş planlardan türetiliyordu; altında iki yönlü sanal defter yoktu.

**Seçenekler.** A) Veri toplayıcıları dahil sıfırdan yazmak: mevcut arşiv ve operasyonu
koparma riski. B) Mevcut veri/ayrıntılı rapor hattını koruyup sürümlü karar ve muhasebe
hattı eklemek: geçiş geri alınabilir, yeni performans eski sonuçlara karışmaz.

**Karar.** B seçildi. İki depoda bağımsız `advisor/` çalışır, `dashboard/` ortak görünüm
sunar. JSONL olay defteri hash zinciri, dosya kilidi, atomik kayıt ve idempotent anahtarlarla
korunur. SQL arşivi geçici DB'ye açılır; eski DB'ye migration veya geçmiş karar değişikliği yok.
Ayrı `portfolio.yml` V2'nin tek yazarıdır. Telegram, GitHub'a kalıcı kayıt sonrası gönderilir;
push denemeleri tükenince iş hata verir. Eski anahtarlar ve veri kaynakları korunur.

**Finansal davranış.** Başlangıç/aylık katkı her hesapta 5.000 TL varsayıldı; açılmış hesabın
bütçe geçmişi sessizce değiştirilemez. Banka alış/satış yönü, komisyon/vergi/kayma, nakit ve
risk sınırları uygulanır. Eksik/tarihi belirsiz fiyatla yeni işlem yok. Koruyucu satışlar
makas büyüdü diye engellenmez. Resmî Fed takviminde yakın karar varsa yeni risk yarılanır.

**Öğrenme.** Sabit özellikli ridge modeli yalnız geçmişte olgunlaşmış etiketlerle eğitilir.
Örtüşmeyen dönemler, sabit tahmin referansı ve maliyet stresiyle sınanır. Üstünlük bugün
kanıtlanmadı; küçük sanal deneme ve olgunlaşmış sonuçlarla en fazla 2 puan yanlılık düzeltmesi
kullanılır. Eski LLM anlatımı tek başına sayısal alım/satım yaptıramaz.

**Sınırlar.** Doğrudan kişisel İşCep kotasyonu yok. BIST gecikmeli son fiyat, altında bankaya
özgü ikincil kaynak var. Tarihsel banka makası ve temettü ödeme tarihi doğrulanamıyor;
alacak nakit sayılmaz. Bunlar panelde ve rehberde yazılıdır.

**Yayın.** Bu ADR yerel uygulama kararını kaydeder; commit/push/deploy onayı değildir.

**Tekrar gözden geçir:** doğrudan banka API'si sağlanırsa, kişisel tarife değişirse veya
bağımsız sanal sonuçlar modelin al-tut karşısındaki başarısını değiştirdiğinde.

---

## #021 — 2026-09-02 — Zamanlanmış işin günü SLOT'tan okunur; gözcünün sorusu takvime bağlandı

**Bağlam.** ADR #017 nöbetçiyi koşunun dışına çıkardı ve doğru yaptı. Ama
gözcünün SORUSU duvar saatinde kaldı: *"bugün (TR takvim günü) koşu kaydı
var mı?"*. GitHub cron gecikmesi bu soruyu iki yönde birden bozdu (L-026):
gözcü 2026-08-26 ve 09-01'de yanlış alarm verip mail attı, 08-28 ve
08-29'da ise gerçek arızada sustu. Ayrıca aynı kayma günlük işin kendi
etiketini de kaydırdı: 08-27 ve 08-31 için heartbeat YOK, 09-01 için İKİ
tane var ve 08-28 Cuma koşusu Cumartesiye taşındığı için tamamen atlandı.

**Karar. Zamanlanmış bir işin günü, dış dünyanın bir olgusundan türetilir.**

| Ne | Eski referans | Yeni referans |
|---|---|---|
| `otonom.gunluk` koşu günü | `bugun_tr()` — işin başlama anı | `cal.last_closed_session()` — analiz ettiği seans |
| Gözcünün "koşu oldu mu?" | `tarih_tr == bugun_tr` | `son_kosu.baslangic_utc >= session_close_utc(son seans)` |
| Gözcünün "analiz oldu mu?" | (aynı) takvim | (aynı) takvim — değişmedi |

Böylece **koşunun KİMLİĞİ ile ÜRÜNÜ aynı günü gösterir**: `asof` zaten
kapanmış seansa bağlıydı, artık `tarih_tr` de öyle. Cumartesiye taşan Cuma
koşusu Cuma'yı analiz eder; gece yarısını aşan gözcü yine dünün seansını
sorar.

**Şiddet de düzeltildi.** `analizsiz` bulgusu artık çıkışı 1 yapar. Eskiden
yalnız `sessiz` yapıyordu ve "seans analizsiz kaldı" satırı Actions'ta YEŞİL
kalıyordu — yani gözcünün BULDUĞU arıza, GitHub bildirim kanalına hiç
ulaşmıyordu (ölçüldü: 2026-08-28T03:51Z). İki kanal, tek olay.

**Reddedilen alternatifler.**
* *"Cron'u erkene al / gecikme payını büyüt"* → gecikme GitHub tarafında ve
  ölçülen dağılımı 25 dk ile 8,5 saat arasında. Pay ne kadar büyütülse bir
  kuyruk hep dışarıda kalır; üstelik pay büyütmek gözcüyü geciktirir.
* *"Slot saatini config'e yaz, ondan türet"* (gold'da seçilen yol) → BIST'te
  gereksiz: takvim zaten dış bir olgu veriyor (`last_closed_session`), ikinci
  bir ikiz değer tutmaya gerek yok. Gold'un takvimi bu soruya cevap
  vermediği için orada slot yolu seçildi ve config↔workflow ikizi TESTLE
  bağlandı.
* *"Gözcü hafta sonu hiç koşmasın"* → sorunun kendisi bu: gecikme gözcüyü
  hafta sonuna taşıyor ve tam o an susturuyordu.

**Tekrar gözden geçir:** gecikme 24 SAATİ aşarsa `last_closed_session` bir
sonraki seansa geçer ve gözcü bir günü atlayabilir. Bu yönde hata güvenlidir
(atlanan gün ertesi gün "analizsiz" olarak bağırır) ama gözlenirse ADR açılır.
Bugüne kadar ölçülen en büyük gecikme 8,5 saat.

---

## #020 — 2026-08-28 — Aynı gün iki kez analiz edilemez; ve girdi de çıktı gibi mühürlenir

**Bağlam.** İki bağımsız dış denetim (biri 2026-08-25, biri 08-28) uygulandı.
08-25 raporu 12 işlem günü eski bir kesite bakmıştı; iki "Kritik" bulgusunun
ikisi de o tarihte gerçekti ama bugün kapalı (bkz. "Reddedilenler").

Asıl olay denetimin KENDİSİ sırasında oldu: 2026-08-27'nin planlı koşusu
GitHub'da hiç görünmedi, sonraki koşu 08-28T01:05Z'de başladı (nominal saatten
8,5 saat sapma — **takvim gününü aştı**). O anda `bars_daily` max hâlâ
2026-08-26 idi. Zincir `asof`u `MAX(bars_daily.date)`ten okuduğu için
**zaten analiz edilmiş bir günü yeniden analiz etti.**

Ölçülen hasar:

| | koşu 1 (08-26T18:25Z) | koşu 2 (08-28T01:08Z) |
|---|---|---|
| tahmin | 18 | 18 |
| `plan_sec` | **0** | **2** |
| veto | 10 | 7 |

Aynı piyasa verisi, aynı model, aynı plan menüsü (19 plan / 9 isim, tek ve
aynı) — **18 ismin 12'sinde farklı karar.** `reports/gunluk_2026-08-26.md`
iki gün sonra üzerine yazıldı; o gün journal'a 17 veto girdi.

**Karar 1 — "bu gün zaten analiz edildi" KAPISI, ama DURDURMA değil ATLAMA.**

`otonom.gunluk` adım 8'den önce `predictions`'ta o `asof` için kayıt arar;
varsa analist adımı koşmaz ve koşu `zaten_analiz_edildi` diye işaretlenir.

Sınıflandırma AGENTS §12a ile yapıldı — *"bu bulguyu bu koşunun KENDİSİ
düzeltebilir mi?"* Hayır, o yüzden bu bir **GÖZLEM**tir ve zinciri
durduramaz: veri/gösterge/çözüm/rapor adımları koşmaya devam eder (hepsi
idempotent) ve o günün raporu yine üretilir. Kilitlenemez de: `asof` veriyle
ilerler, veri adımı bundan ÖNCE koşar; yeni bar gelince analist kendiliğinden
döner. Bar hiç akmıyorsa onu `saglik`in "bar tazeliği" ve "atlanan koşu"
kontrolleri bağırır — bu kapı onların işini ÜSTLENMEZ.

**Neden ikinci koşunun kayıtları SİLİNMEDİ.** Journal değişmezdir (ADR #014).
Üstelik o kaza, sistemin hiç sormadığı bir soruyu ölçtü: **analist
tekrarlanabilir mi?** Kayıt kalır; ölçüme girişi ayrıca ele alınır.

**Karar 2 — GİRDİ de run'a özel mühürlenir (`journal.muhurle_girdi`).**

L-018 çıktıyı 2026-08-11'de ezilmez bir kopyaya bağlamış ve aynı turda şunu
yazmıştı: *"bir savunma kurduğunda sor: bunun aynısı akışın öbür ucunda da
olmalı mıydı?"* Girdi tarafına uygulanmadı. `llm/in/<asof>/bundle.json` yalnız
tarihe bağlı kaldı ve 08-26'da ezildi: `llm_runs` birinci koşu için
`bundle_sha 91eedc59…` diyor, **o sha'nın diskte karşılığı yok** (ölçüldü —
diskteki paket ikinci koşuya ait). Yani o analistin neyi gördüğü artık
kanıtlanamaz ve `bundle_sha`ya bakan HF-02 denetimi onu doğrulayamaz.

`bundle.json` "bugün en son hangi paket üretildi?" sorusunun cevabı olarak
yerinde kalır; `<run_id>.json` "bu tahminler neyi görerek doğdu?" sorusunun
ezilemez cevabıdır — `muhurle_cikti`daki ile birebir aynı ayrım.

**Elenen alternatifler.**
(a) *Bar tazeliğini 1 seansta KRİTİK yap* → gerçek bir yfinance gecikmesinde
zinciri gereksiz durdurur ve L-016 kilitlenmesinin sınıfına yaklaşır; ayrıca
asıl boşluğu (çift analiz) kapatmaz.
(b) *İkinci koşunun kayıtlarını sil* → değişmezliği ihlal eder ve elimizdeki
tek tekrarlanabilirlik gözlemini yok eder.
(c) *Cron'u sıkılaştır* → GitHub gecikmesi bizim kontrolümüzde değil.

**Tekrar gözden geçir:** (a) aynı `asof` için birden çok koşu varsa analist
kararlılığı bir METRİĞE dönüştürülmeli ("12/18 isimde farklı") — bugün bir
kaza, olması gereken bir ölçüm; (b) kapı bir kez tetiklendiğinde Telegram
özetinde görünsün mü, yoksa sessiz kalması yeterli mi.

## #019 — 2026-08-16 — Kâğıt portföy: sistem kendi kararlarını KENDİ takip eder; portföy TÜRETİLİR, defter tutulmaz

**Bağlam.** Üç haftadır üretilen hiçbir plan gerçek pozisyona dönüşmedi.
`holdings` boş olduğu için raporun en savunulabilir bölümü ("Elindekiler"),
kontenjan hesabı ve sektör tavanı — üçü de KÖR çalışıyordu. 2026-08-15
denetiminin somut karşılığı: 12 açık planın 6'sı KRDMD ve hepsi tetiklenmişti;
harfiyen uygulansaydı tek isimde ~%29 birikirdi, rejim tavanı toplam %20 iken.

Mert'in kararı (2026-08-16): *"Portföy şu an tamamen boş; proje kendisini bana
kanıtlamalı. Başlangıç olarak proje gerçek zamanlı alım satım yapıyormuş gibi
bu portföyü kullanmalı, kayıtlarını almalı. Ben ilerleyen zamanda
güvenilirliğine karar vereceğim."* Yani `holdings` artık Mert'in pozisyonu
değil, **sistemin kendi karnesi.**

**Karar 1 — portföy bir TÜREV GÖRÜNÜMDÜR, ayrı bir defter değil.**

Yeni tablo yok, yeni gerçek kaynağı yok. Pozisyonlar `predictions` +
`outcomes`'tan kronolojik olarak türetilir. Gerekçe projenin kendi kuralıdır:
`journal.aktif_vetolar` docstring'i *"`predictions` DEĞİŞMEZDİR ve veto oradan
TÜRETİLİR — ayrı bir tablo tutmak aynı gerçeği iki yerde saklamak olurdu ve
ikisi ayrışırdı"* diyor. Portföy için bu argüman birebir geçerli; üstelik
ayrışmanın bedeli daha yüksek olurdu (karne ile portföy farklı sayı basardı).

Yan fayda: simülasyon geriye dönük yeniden koşulabilir ve **denetlenebilir** —
"bu pozisyon neden açıldı?" sorusunun cevabı bir satır kayıt değil, yeniden
üretilebilir bir zincir.

**Karar 2 — pozisyon plan TETİKLENDİĞİNDE açılır, `plan_sec` anında değil.**

Seçenekler:
- A) `plan_sec` günü kapanıştan al → planın kendi geometrisini yok sayar.
  Plan "geri çekilmede al" diyorsa ve fiyat geri çekilmezse yanlış fiyattan
  alınmış olur. Ölçüldü: 12 açık planın 4'ü (EREGL) `above_zone` ve hiç
  tetiklenmedi — A ile hepsi alınırdı.
- B) `resolver.entry_fill` mantığıyla, giriş bandına dokunulduğunda → **seçildi.**
- C) Ertesi gün açılıştan piyasa emri → planın limitli giriş tasarımını iptal eder;
  ayrıca bu bir ÖLÇÜM sorusu (STATE Backlog) ve portföyle karıştırılmamalı.

**B'nin belirleyici gerekçesi:** `outcomes` zaten B mantığıyla ölçüyor
(`outcomes.entry_date`). Portföy başka bir mantık kullansaydı portföy ile karne
**aynı işlem için farklı giriş fiyatı** gösterirdi. Aynı fonksiyon çağrılır —
kopya mantık yazılmaz.

**Karar 3 — sermaye 10.000 TL, adet TAM SAYI, boyut plandan gelir.**

`adet = floor(sermaye × position_size_pct / 100 / giris_fiyati)`. Sermaye
kapanan işlemlerin net TL sonucuyla büyür/küçülür (mark-to-market yalnız
raporda). Adet 0 çıkarsa pozisyon **açılmaz** ve sebebi `sermaye_yetersiz`
diye kaydedilir — 10.000 TL'de %1.68'lik bir ASTOR planı 168 TL eder ve
342 TL'lik hisseden 0 adet düşer. Bu gerçek bir kısıttır, gizlenmez.

**Karar 4 — üç kısıt mekanik olarak uygulanır ve REDDİN SEBEBİ yazılır.**

1. **Kontenjan:** açık pozisyon sayısı < rejimin `maks_pozisyon`'u.
2. **Çift isim yok:** aynı ticker açıkken ikinci pozisyon açılmaz. (Piramitleme
   ayrı bir stratejidir ve ölçülmemiştir.) Bu, KRDMD yığılmasını kaynağında keser.
3. **Sektör tavanı:** `rejim.sektor_basi_maks_pozisyon`.

Reddedilen her plan sebebiyle kaydedilir (`kontenjan_dolu` / `isim_zaten_acik` /
`sektor_tavani` / `sermaye_yetersiz`). L-020'nin kuralı: bir kapı reddettiğinde
**hangi bileşenin** düştüğü sınıf koduyla yazılır, metinden türetilmez.

**Karar 5 — kaynak: canlı analist zinciri, `replay` DEĞİL.**

`replay` VEKİL bir analisttir (`evaluate.kaynak_sec`'in koruduğu ayrım). Vekilin
kararlarını portföye almak, sistemin karnesini bir ölçüm aracının çıktısıyla
karıştırmak olurdu. Portföy `tool != 'replay'` tahminleri izler.

**Neden ön kayıt gerekmez.** Bu bir KENAR iddiası değil, mevcut kararların
mekanik sonucu. Hiçbir seçim kuralı değişmiyor: analist neyi seçtiyse o,
planın kendi geometrisiyle, rejimin kendi tavanıyla. Portföy seçime DOKUNMAZ —
yalnız sonucunu sayar. (Sıralama katmanının aynı sınırı için bkz. #015.)

**PROJECT.md ile ilişki.** "Otomatik emir gönderimi — sistem asla işlem yapmaz"
maddesi korunuyor: emir yok, broker yok, para yok. Bu bir **kayıt** katmanıdır.
Kapsama eklenen şey "sistemin kendi kararlarının sonucunu takip etmesi".

**Tekrar gözden geçir:** (a) Mert gerçek pozisyon girmeye başlarsa `holdings`
elle defter olarak geri döner ve kontenjan İKİSİNİN birleşiminden sayılır —
`portfoy.durum` bunu bugünden destekler; (b) simüle portföy 20+ kapanmış işleme
ulaşınca `bist degerlendir`'e TL bazlı bir bölüm eklenir (şu an alfa pp bazlı);
(c) adet-0 reddi sık tekrarlarsa sermaye ya da `position_size_pct` tabanı
tartışılır — o zaman bu bir **parametre** sorusudur ve ön kayıt disiplinine girer.

---

## #018 — 2026-08-12 — Hedefin fiyata en az `1.5×ATR` uzaklıkta olması şartı

**Bağlam.** `bist otonom gunluk` her gün 18 canlı isimden yalnız 2-3'üne plan
üretiyor, hep aynı isimler dönüyordu. Huni teşhisi sebebi buldu: `planner.py`
T1'i **en yakın direnç** olarak seçiyor ve `min_rr_t1` kapısı ona uygulanıyordu.
Giriş tarafında mesafe koruması vardı (`maks_giris_uzakligi_atr`, #EUPWR
vakası), hedef tarafında yoktu.

Aritmetik: stop ≈ 2×ATR, giriş ≈ fiyat → `R:R ≈ T1_uzaklık / 2`. Yani kapıyı
geçmek fiilen "en yakın direnç ≥3 ATR yukarıda olsun" demekti. Ölçüldü
(2026-08-10): elenen 15 ismin **15'inde de stop bandı geçiyordu**, öldüren tek
şey R:R'dı; elenenlerin en yakın direnç medyanı **0.36 ATR**; üretilen 49
planın hepsinde T1 ≥ 2.44 ATR ve 31'inde kaynak "52 hafta zirvesi" (yani üstte
hiç pivot yok). Kapı, kimsenin karar vermediği bir **seçim filtresine**
dönüşmüştü.

**Seçenekler:**
- A) Dokunma, yalnız teşhisi rapora bas → sıfır risk ama darlık kalıcı; üstelik
  ölçülmemiş bir yanlılık bilerek sürdürülmüş olur.
- B) Çoklu N tara (1.0/1.5/2.0/2.5), sonuca bakıp seç + ön kayıt yaz → sonucu
  görüp parametre seçmek, ön kaydın koruduğu şeyin tam tersi. Üstelik önerilen
  karar kuralları `alfa`ya bağlanıyordu; oysa alfa `backtest.py`'ın ölçtüğü
  faktör alfası DEĞİL, replay'in "ölçüm yetersiz" ilan ettiği sayı.
- C) Eşiği sonuca bakmadan, mevcut bir karardan türeterek sabitle; alfayı yalnız
  raporla → tanım sorusu tanım gibi çözülür.

**Karar:** C. `planlayici.min_hedef_uzakligi_atr: 1.5`. Kural **iki yerde**
zorlanır: üretimde (`build_options` — aday havuzunun tabanı **ve** bant içi
filtre) ve doğrulamada (`validate_option`). Tek yere yazmak L-008'in aynısıdır.

**Neden 1.5:** `stop_atr_bandi`'nın ALT sınırından türetildi. Stop tabanı
1.5×ATR çünkü günlük salınımın içindeki bir bariyer gürültüyle tetiklenir. Aynı
argüman hedef için de geçerlidir ve sonucu daha ağırdır: gürültü bandındaki bir
T1, üçlü bariyer resolver'ında **rastgele bir `hedef` çözümü** üretir — yani
yalnız plan üretimini değil **karneyi** kirletir. 3.0 seçilmedi: 2×ATR stop ile
R:R'ı otomatik ≥1.5 yapar ve `min_rr_t1`'i dekoratif kılardı.

**Neden ön kayıt yazılmadı:** ön kayıt bir KENAR iddiasını korur; burada kenar
iddiası yok (ADR #008) ve `backtest.py` planner'a hiç dokunmadığı için "kenar
yok" hükmü bu değişiklikten etkilenemez. Bu bir tanım sorusudur —
`min_dokunus`, `pivot_k`, `maks_giris_uzakligi_atr` nasıl muhakemeyle
konduysa öyle konur. Değer koşudan ÖNCE sabitlendi ve çıktıya bakılarak
değiştirilmedi.

**Ölçüm** (`reports/olcum_hedef_mesafe_2026-08-12.md`, 30 dönem, iki replay):
plan 25→29, tahmin 20→25, **kaybedilen plan 0** (küme farkıyla doğrulandı),
tetiklenmeme %35→%16, `sure` 5→10 (bedeli, kaydedildi). Alfa 4.27pp→4.00pp,
t 2.19→2.13 — yani **+4.27pp geometri filtresinin ürünü değilmiş.**

**Canlı kesit (2026-08-10, 18 isim): plan üretilen isim 3 → 8.** Mevcut üçün
planı byte'ı byte'ına aynı kaldı; gelen beş isim beş ayrı sektörden. "Her gün
aynı 4-5 isim" örüntüsünün ana sebebi buymuş. (Replay tablosundaki "farklı
ticker 8→8" satırı çeşitliliği ölçmez — replay dönem başına yalnız top-3 ismi
analiz eder, yani zaten seçimle tavanlıdır.)

⚠ Replay hükmü "ölçüm yetersiz"ten "zayıf kanıt"a döndü; bu bir bulgu DEĞİL,
N'in `olcum.zayif_n_esigi = 15` idari eşiğini geçmesidir. Kanıtın kendisi
hafifçe zayıfladı (t, sd, gerekli_n hepsi kötüleşti).

**Tekrar gözden geçir:** (a) `sure` payı büyümeye devam eder ve `hedef` payını
belirgin şekilde yerse — o zaman eşik bir **performans** sorusuna dönüşür ve
yeni bir ön kayıt turu (`docs/on-kayit-seviye-02.md` deseninde, sonucu görmeden
yazılıp mühürlenen karar kuralı) koşulmadan dokunulmaz; (b) bir koşu sıfır plan
üretirse — bu mekanik başarısızlıktır, ön kayıt gerektirmeden onarılır;
(c) `stop_atr_bandi`'nın alt sınırı değişirse eşiğin türetildiği zemin kayar.

---

## #017 — 2026-08-11 — Sağlık kontrolleri İKİYE ayrılır: KAPI ve GÖZLEM

**Bağlam.** Sistem 2026-08-06'dan 08-11'e kadar dört işlem günü boyunca sıfır
analiz üretti. Sebep kod hatası değildi: 1193 test yeşildi, veri her gün
çekildi, commit her gün atıldı. Kırılan şey iki modül arasındaki varsayımdı.

L-015'te eklenen "atlanan koşu" kontrolü `MAX(predictions.asof)`e bakıp fark
≥2 ise KRİTİK dönüyordu. `predictions` ise sağlık kapısının ARKASINDA yazılır
(`otonom.gunluk` adım 6). Kapı bir kez kapanınca — 2026-08-06'da GitHub
runner işi almadı — açılması için gereken şey kapının arkasında kaldı. Fark
her gün 1 arttı ve kilit KALICI oldu (L-016).

**Karar.** `saglik`in bulguları iki sınıfa ayrılır ve **yalnız birincisi
koşuyu durdurabilir:**

| Sınıf | Soru | Şiddet tavanı | Örnek |
|---|---|---|---|
| **KAPI** | Bugünkü VERİYE güvenilir mi? | KRİTİK olabilir | bar tazeliği · gösterge kapsaması · kalite kapısı · **yarım bar** |
| **GÖZLEM** | Sistem SÜREÇ olarak sağlıklı mı? | en fazla UYARI | atlanan koşu · analizsiz gün · açık plan · çıktı mührü |

Ayırt edici test tek cümledir: **"bu bulguyu, bu koşunun KENDİSİ düzeltebilir
mi?"** Bayat bar → veri adımı çeker, evet, kapı olabilir. Üç gün önce atlanmış
bir koşu → bugünkü koşu onu geri getiremez, hayır, gözlemdir.

**Neden yorum değil YAPI.** Kural yalnız yorumda dursaydı, ömrü onu hatırlayan
kişinin ömrü kadar olurdu (AGENTS.md §12) — ve L-015'i yazan kişi de bu kuralı
biliyordu, yine de ihlal etti. O yüzden:

* `saglik.ekle_gozlem` şiddeti **koda gömülü olarak** UYARI'da tavanlar.
  Bir gözlem kontrolü ileride `return KRITIK, ...` yazsa bile sistem durmaz.
* `GOZLEM_KONTROLLERI` kümesi bir sözleşmedir: sınıflandırılmamış bir kontrol
  `ekle_gozlem` ile eklenemez (RuntimeError).
* Sayaç artık `otonom_kosu` heartbeat'inden okunur; o kayıt koşunun EN
  BAŞINDA, kapıdan önce yazılır. Durdurulan koşu bile "koştum" der.
* Davranışsal kilit: `TestKapiKendiCiktisinaBakmaz` — journal'ın yaşı
  (0..30 gün) kapı kümesini DEĞİŞTİREMEZ. Diferansiyel test, çünkü mutlak
  bir "hiç KRİTİK olmasın" iddiası fixture eksikliklerini de yakalar ve asıl
  soruyu bulanıklaştırır.

**Reddedilen alternatifler.**
* *"Kontrolü UYARI'ya çevirelim, yeter"* → tek çağrı yerini düzeltmek kuralı
  uygulamak DEĞİLDİR (L-008). Bir sonraki kontrol aynı çukura düşerdi.
* *"Kapıyı tamamen kaldıralım"* → kapı gerçek bir işe yarıyor: bayat
  göstergeyle üretilen paket boş ama şeklen geçerlidir (L-009) ve onu analiz
  etmek sistemin en pahalı hata sınıfıdır.
* *"Heartbeat'i `predictions`ten türetelim"* → sorunun ta kendisi.

**Nöbetçi ayrı bir karardır ve bu ADR'nin parçasıdır.** İçerideki hiçbir
kontrol "koşu hiç başlamadı"yı bildiremez. `.github/workflows/nobetci.yml`
ayrı iş, ayrı zamanlama (19:40 UTC), ayrı runner talebi ve **salt-okur**
(`permissions: contents: read`). Bir gözcünün tamir etmeye kalkması hem
gözcülüğü hem tamiri bozar.

**Tekrar gözden geçir:** nöbetçi de runner alamayan bir güne denk gelirse
(ikisi birden düşerse) tamamen dış bir uptime/heartbeat servisi gerekir —
gold projesindeki gibi. Bugün gerekmiyor: iki ayrı işin AYNI gün runner
alamama olasılığı gözlenmedi ve GitHub'ın kendi "workflow failure" bildirimi
üçüncü kanal olarak duruyor. Bir kez daha yaşanırsa bu satır kararı açar.

---

## #016 — 2026-08-07 — Ölçüm paneli: düzeltilmemiş kurumsal işlem GÖZLEMİ düşer, İSİM düşmez

**Bağlam.** ADR #015 turunda yapılan "bedelsiz kapsaması" ölçümü, aranmayan bir
şey buldu: panelde **5 sahte getiri barı** var.

    CCOLA 2024-08-01  −%90.7   (11:1 bölünme; yfinance kaydı 08-13'e yazmış,
                                seriyi geriye DÜZELTMEMİŞ — 07-31 kapanışı 846 TL)
    TSPOR 2025-06-19  +%94.6   (kayıt yok)
    AYGAZ 2022-09-01  +%72.5   (kayıt yok)
    HEKTS 2024-09-09  −%64.8   (kayıt yok)
    HEKTS 2021-04-30  +%44.1   (kayıt var, oran 2.02 — ama fiyat YUKARI gitmiş)

Dördü de `in_measure=1`, **hiçbiri `in_live` değil** → günlük karar hattı temiz.
Ama ADR #007'nin kapıyı kapatan backtest'i bu panelle koştu.

İki mekanizma arızası birden ortaya çıktı:

1. **Kalite kapısı kayan pencereli.** `_quality_row` son 252 bara bakıyor;
   2024-08-01 bugün o pencerenin dışında, tablo `unexplained_jump=0` yazıyor ve
   isim "temiz" görünüyor. Kontrol yeşil yanarken bozulma yerinde duruyor (L-014).
2. **Ölçüm hattında kayıt bazlı kalite kapısı HİÇ YOK.**
   `backtest.eligible_mask`'in "veri" kapısı yalnız *momentum hesaplanabiliyor mu*
   diye soruyor. Yani canlı katman "bu ismin verisine güvenmiyorum" derken ölçüm
   katmanı aynı barları sessizce kullanıyordu — L-008'in "simetriğini ara"
   kuralının tam hedefi.

**Seçenekler ve ÖLÇÜLEN sonuçları** (üçü de gerçek veriyle koşuldu):

| Seçenek | evren | alfa vs EW | t | IC(tüm) | hüküm |
|---|---|---|---|---|---|
| A) Değişiklik yok, ifşa yeter | 67 | −0.861pp | −1.85 | 0.0420 | kenar yok |
| B) 4 ismi `in_measure=0` yap | **63** | −0.946pp | −2.06 | 0.0376 | kenar yok |
| C) **Yalnız KİRLİ GÖZLEMİ düşür** | 67 | −0.920pp | −1.98 | 0.0412 | kenar yok |

**Karar: C.**

**Neden C:**

- **Sorun isimde değil, bir avuç barda.** B, dört ismi tamamen eleyerek ölçüm
  evrenini 67→63'e indiriyor — yani beş bozuk bar yüzünden ~11 yıllık dört
  temiz seriyi çöpe atıyor. C, **tam 5 gözlem** düşürüyor (~2200 gözlem
  yuvasından) ve başka hiçbir şeye dokunmuyor.
- **A yetersiz, çünkü sorun bilgi eksikliği değil mekanizma asimetrisi.** Canlı
  hat bu veriye zaten dokunmuyor; ölçüm hattının dokunması bir tasarım tercihi
  değil, kimsenin fark etmediği bir boşluktu. İfşa etmek onu kapatmaz.
- **−%90.7 bir getiri değildir.** ±%10 marjlı bir piyasada bu bir veri hatasıdır.
  Veri hatasını dışarıda bırakmak bir *yöntem* tercihi değil, girdi hijyenidir —
  eşik ayarlamakla aynı şey değil.

**ÖN KAYIT NEDEN GEREKMİYOR — ve bu gerekçe sınanabilir olsun diye yazılıyor:**

`on-kayit-revizyon-01.md` §5'in yasağı şudur: *sonucu görüp çıtayı indirmek.*
Burada tam tersi oldu — **temizlemek sonucu KÖTÜLEŞTİRDİ** (−0.861 → −0.920pp,
t −1.85 → −1.98). Sonucu iyileştirmeyen bir değişiklik, sonuç kovalama olamaz.
Ayrıca `docs/on-kayit-seviye-02.md` §4'ün yönettiği üç parametrenin
(`min_rr_t1`, `kumeleme_atr_carpani`, `min_dokunus`) hiçbirine dokunulmadı ve
**hiçbir dilimde hüküm değişmedi** (tam / in-sample / OOS → hepsi `kenar yok`,
kapı `[]`). ADR #007'nin sonucu ayakta: mevcut faktör seti bu evrende pozitif
kenar üretmiyor.

Eşik `evren.duzeltilmemis_kurumsal_pct = 35.0` ve UYDURULMADI: gerçek piyasa
ucu ölçüldü (+%22.2 → 2023-02-15 deprem kapanışı sonrası açılış, 25 isim
birden; −%28.3 → 2020-03-12 COVID), en küçük artefakt +%44. Eşik aradaki
boşluğa kondu ve `risk`/`prices`/`backtest` üçü de AYNI anahtardan okuyor.

**Sessiz eleme YOK:** düşürülen gözlem sayısı `n_atlanan.kirli_gozlem` alanında
taşınır ve ölçüm raporunda basılır. Raporda görünmeyen bir eleme, bir sonraki
okuyucu için görünmez bir varsayımdır.

**Veri DÜZELTİLMEDİ, bilerek.** CCOLA'nın 2024-07-31 öncesi barlarını 10.81'e
bölmek "doğru" fiyatı üretirdi ama o fiyat bizim ürettiğimiz bir sayı olurdu.
Bu proje veri uydurmaz; ölçemediğini eler (bkz. `prices.quality_for`).

**Tekrar gözden geçir:** (a) yfinance CCOLA'yı düzeltirse maske kendiliğinden
boşalır, ekstra iş yok. (b) `kirli_gozlem` sayısı 20'yi aşarsa bu artık "birkaç
bozuk bar" değil sistematik bir kaynak sorunudur ve ikinci veri kaynağı kıyası
(STATE Backlog) öne alınır. (c) Canlı evrene böyle bir bar girerse `bist saglik`
KRİTİK basar — o an karar yeniden açılır.

---

## #015 — 2026-08-07 — Günlük rapor tek SIRALI EYLEM listesiyle başlar; sıra bir GETİRİ iddiası değildir

**Bağlam.** Üç dış repo incelendi (Merdiven · borsaci · borsapy, rapor:
`reports/repo-inceleme-2026-08-07.md`). Karar öncesi her boyutta (veri kalitesi,
takvim, kesitsel sıralama, plan geometrisi, denetim, ölçüm, test) bizim proje
açık ara önde çıktı. **Karar ANINDA ise geride:** 34 satırlık karşılaştırmada
9 satırda bizde "—" vardı ve hepsinin ortak imzası aynıydı — *dünyanın durumunu
titizlikle okuyoruz, "şu anda ne yapılabilir"i hiç sormuyoruz.*

Merdiven'in çekirdek fikri şuydu: kararı hisse-hisse değil **fırsat maliyeti**
üzerinden ver — "A'yı satıp B'ye geçmek, gidiş-dönüş maliyeti çıktıktan sonra
hâlâ daha iyi mi?" Bizim `build_menu` 19 hisse için birbirinden habersiz 19 plan
üretiyor; hangisinin önce geldiğini, sermayenin nereye yeteceğini, elde zaten
ne olduğunu HİÇ sormuyor.

Mert'in isteği de buydu: *"hisselerin gidecekleri yönden ne yapacağımı daha net
belirtebilmeli."*

**Seçenekler:**

- **A) Merdiven'in ΔEV'sini birebir al.** Her aday için beklenen getiri hesapla,
  elde tutulanla karşılaştır, maliyeti çıkar, farkı bir tamponla eşikle.
- **B) Sıralama YOK, bugünkü hâl kalsın.** Rapor hisse hisse listelemeye
  devam etsin.
- **C) SIRALI eylem listesi — ama sıra bir UYGULANABİLİRLİK ve RİSK sırası
  olsun, bir getiri sırası DEĞİL.**

**Karar: C.**

**A neden reddedildi — ve bu kararın en önemli cümlesi bu.** ΔEV bir **beklenen
getiri** karşılaştırmasıdır. Bizim beklenen getirimiz **yok** ve olmadığı
ÖLÇÜLDÜ: ADR #007 kapıyı kapattı, PROJECT.md'nin ilk sayfasında
`required_n ≈ 193 dönem ≈ 11,5 yıl` yazıyor. Aynı formülü "EV" diye kurmak,
ölçülmemiş bir kenar iddiasını sisteme **arka kapıdan** sokmak olurdu — üstelik
çıktı çok ikna edici görünürdü. Sıralanmış bir liste, sıralamanın bir şey
BİLDİĞİNİ ima eder. Merdiven'in kendi eşiklerinin tamamı README'sinde
"deneme-yanılma" diye yazılı; biz o formülü ödünç alırken ölçülmemişliğini de
ödünç alırdık.

**B neden reddedildi.** Bugünkü rapor doğru bilgiyi veriyor ama **sıralamıyor**:
19 ayrı başlık, aralarında öncelik yok, sermayenin nereye gideceği yok. Kullanıcı
her gün aynı sentezi kafasında yeniden yapmak zorunda ve sistemin ürettiği
disiplin tam da orada kayboluyor.

**C'nin sözleşmesi — dört madde, hepsi bağlayıcı:**

1. **Sıralama ölçütlerinin HEPSİ deterministik ve ölçülmüş/gözlemlenmiş
   olgulardır:** bugün işlem görebilirlik (limit durumu), bilanço penceresi,
   veri kalitesi, yürürlükteki veto, planın tetiklenebilirliği
   (`entry_zone_status`), riske edilen sermaye, maliyet düşülmüş R:R, rejim
   tavanında kalan kontenjan. **Hiçbiri bir yön tahmini değildir.**
2. **Skor YOK, tek sayı YOK.** Sıralama sözlükbilimsel (lexicographic): önce
   uygulanabilirlik, sonra risk, sonra geometri. Bileşenleri tek bir sayıda
   toplamak, ağırlıklarını uydurmak olurdu — borsaci'nin Buffett skorunda tam
   olarak bu yapılmış ve toplam skor modelin kendi uydurduğu alt skorlardan
   besleniyor.
3. **SEÇİMİ DEĞİŞTİRMEZ.** Liste hangi planların ÜRETİLECEĞİNİ etkilemez;
   yalnız üretilmiş olanları sıraya koyar. Sıralamanın seçime dokunduğu gün
   `docs/on-kayit-seviye-02.md` disiplini devreye girer — o an ön kayıt şart.
4. **Başlığı iddiayı taşır.** Liste "en iyi fırsatlar" DEĞİL, *"bugün
   uygulanabilir işler — uygulanabilirlik ve risk sırasına göre"* diye
   sunulur ve `edge_verdict` dili korunur.

**Neden bu, isteği yine de karşılıyor:** "ne yapacağımı net söyle" cümlesinin
içindeki yedi sorunun hiçbiri yön hakkında değil — bugün işlem görebilir mi,
önünde bilanço var mı, maliyetten sonra hâlâ geçiyor mu, elimdekinin yerine mi
geçiyor, kaç lira riske ediyorum, dünkü veto geçerli mi, sıra ne. Bir
profesyoneli amatörden ayıran şey yönü daha iyi bilmesi değil; uygulanamaz işlem
açmaması, bilanço gününe kör girmemesi, sermayesini sıraya koyması.

**Tekrar gözden geçir:** `bist degerlendir` N ≥ 30 çözülmüş tahmine ulaştığında
"sıralamanın kendisi bir şey biliyor mu" ilk kez sorulabilir hale gelir. O gün
sıra bir getiri iddiasına dönüştürülecekse **ön kayıt şarttır** ve bu ADR o
turun referansıdır.

---

## #014 — 2026-08-01 — Depolama SQLite + git arşivi kalır; Supabase'e geçilmez

**Bağlam:** Mert "veriyi bir yerde tutmak iyi olur" diye Supabase sordu. Asıl
ihtiyaç veritabanı teknolojisi değil, **yedekleme** çıktı — ve o endişe
haklıydı: bu sabaha kadar `data/*.sql` gitignore'daydı, yani veritabanı YALNIZ
Mert'in laptopunda duruyordu. Disk giderse 11 yıllık bar ve tüm tahmin geçmişi
giderdi.

O ihtiyaç ADR #013'te (gitignore ters çevirme) zaten kapandı. **Kanıtlandı**
(2026-08-01, taze klon + `bist db restore`): 197.191 bar (2015-01-02 →
2026-07-30), 56 tahmin (`claude-code` 18 · `gemini-3.6-flash` 18 · `replay` 20),
makro, KAP — hepsi geri geldi.

**Seçenekler:**
- A) Supabase KAYNAK olsun, SQLite kalksın.
- B) SQLite kaynak kalsın, Supabase'e salt-okunur AYNA yazılsın.
- C) **Değişiklik yok** — git arşivi yedek ihtiyacını zaten karşılıyor.

**Karar: C.** Git'in bu projeye özgü iki üstünlüğü Supabase'de yok:

1. **Değiştirilemezlik.** Sistemin tek işi kendi isabetini dürüstçe ölçmek.
   Barındırılan bir tabloda bir tahmin satırını sessizce düzeltebilirsin;
   commit geçmişinde düzeltemezsin — denersen geçmiş ifşa eder. Bu bir lüks
   değil, ÜRÜNÜN KENDİSİ.
2. **Herhangi bir güne dönüş.** "3 ay önce sistem ne diyordu?" sorusu tek
   `git checkout` ile cevaplanıyor. Ücretsiz Supabase'de nokta-zaman geri
   yükleme yok.

Ayrıca: offline çalışma biter; `backtest`/`replay` 197 bin satırı ağdan çekmeye
başlar (saniyeler → dakikalar); ücretsiz proje hareketsizlikte duraklar.

**Maliyet ölçüldü:** 25 modül `sqlite3` kullanıyor · 102 `sqlite3.Connection`
imzası · 104 ham SQL · 29 test dosyası. Üstelik 1079 testin tamamı geçici
SQLite dosyasına dayanıyor; Postgres'e geçince ya CI'a Postgres eklenir ya
testler SQLite'ta kalır — ikincisi *"test ettiğin şey üretimdeki şey değil"*
demek ve bu projenin kovaladığı hata sınıfının ta kendisi.

**Tekrar gözden geçir:** Bu veriyi kullanan bir web/mobil arayüz yazılmasına
karar verilirse **B**'ye geçilir — SQLite kaynak kalır, Supabase salt-okunur
ayna olur. Yedek ve denetlenebilirlik korunur, arayüz veriyi alır. O gün
geldiğinde yarım günlük iş; şimdiden yapmak YAGNI.

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
