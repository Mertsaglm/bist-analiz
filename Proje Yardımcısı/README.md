# Usta — Taşınabilir AI Mühendislik Yardımcısı

Bu klasör, farklı AI kodlama araçlarında (**Claude Code, Cursor, Antigravity,
VS Code eklentileri, Copilot...**) aynı şekilde çalışan kişisel bir
"usta/yol gösteren" sistemidir. Sır şu: her şey düz markdown, hiçbir aracın
özel özelliğine bağımlılık yok.

> Bu şablon **kullanımda test edildi.** BIST Analiz projesi baştan sona bu
> sistemle kuruldu; aşağıdaki her kural gerçek bir hatadan doğdu. Yeni
> maddeler (`/denetle`, doküman çürümesi kuralları, ön kayıt disiplini,
> **kuralı teste devretme**) 2026-07-27'de yapılan bağımsız bir denetimin ve
> onu izleyen "kurallar bizden sonra da yaşasın" turunun sonucudur.
> 7. ve 8. kural ile "kilit mi, süs mü?" adımı 2026-08-12'de eklendi: dışarıdan
> beş bağımsız AI incelemesi + kod/veri kazısı, **doğru yazılmış bir kapının
> sessizce bir seçim filtresine dönüştüğünü** buldu. 9. kural 2026-08-28'de
> eklendi: iki bağımsız dış denetim, şablonun KENDİ kurallarından birinin
> yazılı olduğu hâlde zorlanmadığını ve **o boşluğun başka bir hatayı
> gizlediğini** gösterdi.

## Yapı

```
proje/
├── AGENTS.md                        ← KANONİK dosya: Usta'nın kimliği, kuralları, komutları
├── CLAUDE.md                        ← Claude Code köprüsü (sadece AGENTS.md'ye yönlendirir)
├── GEMINI.md                        ← Antigravity köprüsü (araç-özel ayarlar buraya)
├── .github/copilot-instructions.md  ← Copilot/VS Code köprüsü
├── ai/
│   ├── PROJECT.md                   ← Projenin amacı, kapsamı, kısıtları (nadiren değişir)
│   ├── STATE.md                     ← Durum: bitti / devam / bloklar / sıradaki 3 iş
│   ├── DECISIONS.md                 ← Karar günlüğü (ADR): ne, neden, ne zaman tekrar bak
│   ├── PROFILE.md                   ← Mert'in profili ve kısıtları (projeler arası ORTAK)
│   ├── LESSONS.md                   ← Geçmiş hatalardan dersler (anti-pattern listesi)
│   └── archive/README.md            ← STATE şişince eski içerik buraya
├── docs/                            ← ÖN KAYITLAR: koşudan önce mühürlenir, DEĞİŞTİRİLMEZ
└── Proje Yardımcısı/
    ├── README.md                    ← bu dosya
    └── yeni-proje.sh                ← şablonu yeni bir projeye kopyalar
```

⚠ **Kural dosyaları KÖKTE, script alt klasörde.** Bu ayrım bilinçli: hiçbir IDE
alt klasördeki AGENTS.md'yi okumaz (L-004), ama `yeni-proje.sh` bir araç olduğu
için kökü kalabalıklaştırmasın diye ayrı durur. Script bu yüzden kaynağı kendi
klasörü değil **bir üstü** olarak çözer — bu satır güncellenmediği için script
bir dönem hiç çalışmadı ve kimse fark etmedi (L-002).

**`docs/` neden var:** Bir ölçüm/deney yapmadan önce "neyi değiştiriyorum,
geçme şartı ne" yazılır ve dosyanın sha256'sı alınır. Sonucu gördükten sonra
çıtayı indirmek, ölçüm yapan her projede en kolay ve en pahalı kendini
kandırma yoludur. Ön kayıt onu **imkânsız** kılar.

## Nasıl çalışır?

1. AI aracı projeyi açınca kural dosyasını okur (AGENTS.md'yi doğrudan, ya da
   köprü dosyası üzerinden).
2. Usta oturum başında `ai/` dosyalarını okur → "nerede kalmıştık" sorusu hiç doğmaz.
3. Oturum sonunda (`/kapat`) STATE.md güncellenir → bir sonraki oturum, hangi
   araçta olursa olsun, kaldığı yerden devam eder.

## Komutlar

Bunlar gerçek slash komutu değil, AGENTS.md içinde tanımlı **sözleşmeler** —
bu yüzden her araçta çalışırlar. Sohbete yazman yeterli:

| Komut | Ne yapar |
|---|---|
| `/baslat` | Oturumu açar: durumu okur, bugün için iş önerir (dosyalar boşsa önce keşfe geçer) |
| `/tanis` | Tanışma + proje keşfi: Usta sorular sorar, PROFILE.md ve PROJECT.md'yi kendisi doldurur |
| `/durum` | Neler bitti, neler kaldı, sıradaki 3 iş |
| `/karar <konu>` | Seçenekleri tartışır, kararı gerekçesiyle DECISIONS.md'ye işler |
| `/plan <hedef>` | Hedefi milestone'lara ve 1-2 saatlik görevlere böler |
| `/kapat` | Oturumda yapılanları STATE.md'ye yazar, kapanış özeti verir |
| `/ders <olay>` | Yaşanan bir hatadan ders çıkarıp LESSONS.md'ye ekler |
| `/ogret <konu>` | Konuyu sade, benzetmeli, öğretici şekilde anlatır |
| **`/denetle`** | Projeyi DIŞ göz gibi denetler: kod ↔ doküman ↔ config ↔ **verinin gerçek içeriği**. Önce raporlar, sonra düzeltir |

### `/denetle` neden ayrı bir ritüel?

Gerçek bir denetimde bulunan **kritik hataların hepsinde kod DOĞRUYDU.**
Bozulan şey kodun varsaydığı VERİ DURUMUYDU ve hiçbiri hata fırlatmıyordu:

- Bir tablo 70 satır bekliyordu, 19 vardı → oranlar sessizce 16 isim üzerinden
  hesaplanıyor, çıktı hâlâ "geçerli" görünüyordu.
- Bir filtre "son analizden bu yana" diyordu ama duvar saatini kullanıyordu →
  47 gerçek kayıt sessizce gizlendi.
- Bir kalite kapısı tam tarih eşleşmesi arıyordu → veri bir gün ilerleyince
  kapı kapandı ve dört tüketici de "kayıt yok"u "sorun yok" okudu.

Bunların hiçbiri kod okuyarak görülemez. `/denetle` bu yüzden **veritabanının
gerçek içeriğine bakmakla başlar.** Ayrıntılı protokol: AGENTS.md bölüm 11.

## Şablonun taşıdığı dokuz sert kural

Bunlar AGENTS.md'de yazılı ve her projeye taşınır:

**1. Payda birinci sınıf çıktıdır.** Bir oran/sıralama/yüzdelik üreten her
fonksiyon paydayı da döndürsün ve çıktıya yazsın. "%31 genişlik" ile "5/16 =
%31 genişlik" farklı iki cümledir; ikincisi yanlış olduğunda fark edilir.

**2. "Veri yok" asla "sorun yok"a çevrilmez.** Eksik kaydın varsayılanı
olumsuz olsun. Bir dış kaynak hatası boş listeye düşüyorsa, çağıran taraf
"bugün haber yok" ile "kaynağa ulaşılamadı"yı ayırt EDEMEZ.

**3. Yorum bir iddiadır.** "Şu kolon şunu ölçer" yazdığında, o iddianın kodda
karşılığı olduğunu doğrula. Denetimde bulunan en pahalı yanılgılar kod hatası
değil, **doğru görünen ama karşılığı olmayan yorumlardı** — üç ayrı dosya bir
ölçümün yapıldığını söylüyordu, ölçüm hiç yapılmıyordu.

**4. Yeşil test, doğrulanmış gerçek değil; kayda geçmiş bir inançtır.**
`tick_size(1000) == 1.00` testi aylarca yeşil kaldı — ölçünce doğru cevabın
2.50 olduğu görüldü. Test bir VARSAYIMI sabitliyordu. Bir varsayımı test
ederken yanına **"bu ölçüldü mü, ne zaman?"** yaz; ölçülmediyse test onu
korumaya değil, görünür kılmaya yarasın.

**5. Dış kaynağın sınırını ölç, tahmin etme.** "90 gün iste" dedik, kaynak
14 gün döndürdü — hata vermeden. Bir API'den geniş bir aralık isterken
**döneni istenene karşı doğrula**; doymuşsa böl. Sabit bir dilim boyutu
seçmek de yetmez: hacim mevsimlik olabilir, doymayı gözleyip tepki ver.

**6. Yorum bir niyettir, test bir sözleşmedir.** Yukarıdaki beş kural da dahil,
yalnızca yorumda duran bir kuralın ömrü **onu hatırlayan kişinin ömrü kadardır**
— ve o kişi çoğu zaman sen olmayacaksın (farklı bir model, farklı bir araç, ya
da aylar sonraki sen). Bir kural yazdıktan sonra sor: *bunu koşulabilir hale
getirebilir miyim?* "Bu eşik düşürülmemeli" bir dilek; `assert esik >= 15` bir
sözleşme — eşiği değiştirmeyi yasaklamaz, **görünür** kılar. Ayrıntı:
AGENTS.md bölüm 12.

**7. Bir ORAN kapısı, payı sınırsızsa kalite ölçmez — SEÇİM yapar.**
Gerçek vaka: `R:R = hedef_mesafesi / stop_mesafesi` ve kapı `R:R ≥ 1.5`.
Payda (`stop`) bir bantla sınırlıydı, pay (`hedef`) serbestti — ve hedef "en
yakın seviye" seçiliyordu. Sonuç: kapı sessizce *"yalnız üstünde ~3 birim
boşluk olan adaylara izin ver"* kuralına dönüştü. Kimse böyle bir karar
vermedi, hiçbir yerde yazmıyordu ve **evrenin %83'ü her gün eleniyordu.**

Daha pahalısı: o kapı, gözlemi de üreten mekanizmayı besliyordu. Gürültü
bandındaki bir hedef, sonuç çözücüsünde **rastgele bir "başarı" kaydı** üretir
— yani yanlılık yalnız neyin seçildiğine değil, **karnenin ne dediğine** de
bulaşır.

> Kural: bir oran/eşik yazdığında sor — **payın ve paydanın kendi sınırları var
> mı?** Biri serbestse bir kalite ölçüsü değil, bir filtre yazmışsındır.
> Ve bir tarafa mesafe/aralık koruması koyduysan **simetriğini hemen ara**
> (5. kuralın oran hâli). Ayrıntı: AGENTS.md bölüm 12b.

**8. "Ve"yle birleştirilmiş bir gerekçe, hangi koşulun düştüğünü GİZLER.**
Bir kapı *"A + B kurallarını **birlikte** sağlayamadı"* diyordu. Teknik olarak
doğruydu; ölçünce elenen 15 vakanın **15'inde de A geçiyordu** — öldüren tek
şey B'ydi. "Birlikte" kelimesi haftalarca herkesi yanlış yere baktırdı.

> Kural: birleşik bir koşulun ihlalini raporlarken **hangi bileşenin** düştüğünü
> yaz — metinden türetme, bir **sınıf kodu** koy ve testi metne değil koda
> baktır. Ve tanı verisini yalnız başarı yolunda saklama: sor, *"bu bilgi en
> çok ne zaman lazım — işler yürürken mi, durduğunda mı?"*

**9. Yazılı ama zorlanmayan bir kural yalnız kendisi düşmez — KÖR EDER.**
Gerçek vaka: şablonun kendi listesinde *"testler dış servislere dokunmamalı"*
yazıyordu ve zorlanmıyordu. Bir test tek bir dış çağrıyı mock'luyor, komut ise
iki tane yapıyordu. Görünen zarar küçüktü (test sonucu ağ durumuna bağlı).

Görünmeyen zarar büyüktü: yasak konulunca **ikinci** bir test düştü ve ortaya
şu çıktı — bir kaynağı kapatan config anahtarı, o kaynağın ikinci kod yolunu
kapatmıyordu. Kapatma anahtarı kapatmıyordu. Hata aylardır oradaydı ve
**yeşil bir suite tarafından örtülüyordu**: çağrı ağa erişebildiği için
başarılı dönüyor, başarılı dönen çağrı da hatayı görünmez kılıyordu.

> Kural: bir sızıntıyı kapattığında **arkasından ne çıktığına bak.** "Kuralı
> zorlar hale getirdim, suite hâlâ yeşil" yeterli bir sonuç değildir; asıl
> soru **zorlama açılınca ne kırmızıya döndüğü**dür. Ve bir kapatma anahtarı
> yazdıysan onu kaynağın SINIRINA koy (çağrı yerine değil) ve **kapattığını
> test et** — "kapalı" ile "çekilemedi" ayrı sonuçlardır.
> Ayrıntı: AGENTS.md bölüm 12c.

## Kuralı nasıl teste devredersin? (dile bağlı değil)

Şablon Python'a bağlı değil; aşağıdaki dört sınıf her projede karşılığı olan
şeylerdir. Test aracı ne olursa olsun (pytest, vitest, `bats`, hatta bir
`make check` script'i) mantık aynı:

| Sınıf | Ne yapar | Neyi engeller |
|---|---|---|
| **Eşik zemini** | Kararlaştırılmış eşiklerin altına inilemez | Sonucu görüp çıtayı indirmek |
| **Yapı eşliği** | Koddaki alan/kolon listesi ↔ şema birebir | Bir alanın kayıp sessizce yanlış yere yazılması |
| **Doküman ↔ kod** | Belgelerdeki her komut/anahtar/dosya yolu gerçekten var mı | Ölü referans, bayat komut adı |
| **Yan etkisizlik** | Testler gerçek veriye/çıktı klasörüne dokunmaz | Test koşmanın kullanıcı verisini değiştirmesi |

Ve testleri **üç ayrı soruya** böl — birini diğerinin yerine koyma:

- **Sözleşme:** kodun VARSAYDIĞI yapı ayakta mı?
- **Mekanizma:** doğru girdiden / doğru paydadan mı besleniyor?
- **Uçtan uca:** zincir gerçekten koşuyor mu?

Üçüncüsü en pahalı hataların yeridir: her modül kendi başına doğrudur, kırılan
şey **aralarındaki varsayımdır** — ve birim testleri onu görmez.

⚠ Hedef kapsam yüzdesi değil. Kapsam "kod çalıştı" der, "kural tutuyor" demez.
Her satırı değil, **her KURALI** test et.

### Yazdığın test bir KİLİT mi, yoksa SÜS mü?

Bir testin yeşil olması, koruduğunu sandığın şeyi koruduğunu **göstermez.**
Tek geçerli doğrulama şudur:

> **Eski hatayı geri koy. Test kırmızıya dönüyor mu?**
> Dönmüyorsa o test bir kilit değil, bir süstür — sil ya da düzelt.

Bu adım pahalı değil (30 saniye) ve atlanınca sessizce boşa çalışırsın.
Tek bir oturumda **iki kez** yaşandı:

- Bir kural iki yere yazıldı (üretim + doğrulama). Doğrulama tarafındaki
  kopya silindi → **suite yeşil kaldı.** Yani ikinci uygulama hiç
  korunmuyordu; "L-008'i uyguladım" demek yanlış olurdu.
- Bir hesaplama fonksiyonu test edilmişti ama **raporun onu bastığı** test
  edilmemişti. Rapor satırı silindi → **suite yeşil kaldı.** Fonksiyon doğru
  çalışıp çıktı hiç görünmeyebilirdi.

Genel kalıp: **üreten kodu test etmek, gösteren kodu test etmez.** İkisi ayrı
sözleşmedir ve ikisi de kırılabilir.

## Denetim düzeltirken düşülen beş tuzak

Denetim raporu yazmak kolay; düzeltmeleri kapatmak asıl iş. Bunların hepsi
gerçekte yaşandı ve AGENTS.md bölüm 11'de yazılı:

1. **Düzeltme yeni hata doğurur.** Bir kapıyı sıkılaştırmak, o kapıyı
   kullanan başka bir hattın tamamını eledi (0 çıktı). Her düzeltmeden sonra
   ETKİLENEN HATTI uçtan uca koş — test yeşil diye geçme.
2. **Kontrol listesini kodla doğrula.** "Yaptım" demek yetmez. Ama naif metin
   araması **kendi yorumlarını yakalar**: koda mı yoruma mı baktığını ayır.
3. **Yeni ölçüm yeni bulgu doğurur.** Bir kararı uygularken çıkan sürprizi
   "kapsam dışı" diye geçme — asıl bulgu o olabilir.
4. **Eski testler eski varsayımı korur.** Düzeltme sonrası kırmızıya dönen
   test, çoğu zaman düzeltmenin yanlış olduğunu değil, **testin yanlış
   olduğunu** gösterir. Hangisi olduğuna ölçerek karar ver.
5. **Tek çağrı yerini düzeltmek kuralı uygulamak değildir — simetriğini ara.**
   Bir fixture salt-okunur yapıldı ama aynı hatanın bir sonraki testte
   tekrarlanmasını engelleyen hiçbir şey yoktu; bir alan için None koruması
   yazıldı, simetriği olan alan için yazılmadı. Düzeltme iki iştir:
   (a) bu çağrı yerini kapat, (b) **aynı hatanın bir daha yapılamayacağı yeri**
   kapat.

## 🔍 Sen neyi kontrol edeceksin? (şablonu kullanan insan olarak)

Usta işi yapar; senin işin **onun doğru işi yaptığını doğrulamak.** Aşağıdakiler
araçtan ve projeden bağımsızdır.

### Her oturumun sonunda — 1 dakika

- [ ] **`ai/STATE.md` gerçekten güncellendi mi?** "Sıradaki 3 İş" hâlâ geçerli
      mi, yoksa biri çoktan bitmiş de listede mi duruyor? Tamamlanmış bir işi
      listede bırakmak, bir sonraki oturumu yanlış işe başlatır.
- [ ] **Elde tutulur BİR şey var mı?** Çalışan bir parça, doğrulanmış bir
      varsayım, dolmuş bir dosya. Sadece konuşulmuş bir oturum, kaybedilmiş
      bir oturumdur.
- [ ] **Bir karar alındıysa `DECISIONS.md`'ye girdi mi?** Bir hata yaşandıysa
      `LESSONS.md`'ye?

### Usta bir iş "bitti" dediğinde — 2 dakika

- [ ] **Testler yeşil mi, yoksa iş bitti mi?** İkisi aynı şey değil.
      "Etkilenen hattı uçtan uca koştum" dedi mi? (Yeşil suite, hattın
      durduğunu görmez — en pahalı hatalar tam orada.)
- [ ] **Yeni test bir KİLİT mi?** "Eski hatayı geri koydum, kırmızıya döndü"
      cümlesini duydun mu? Duymadıysan sor.
- [ ] **Sayı verdiyse nereden geldiğini söyledi mi?** "%40 daha iyi" bir iddia;
      "30 dönemde 25→29, kaybedilen 0, küme farkıyla doğrulandı" bir ölçüm.
- [ ] **Kendi hatasını düzeltti mi, örttü mü?** İyi bir tur, sonunda "şunu
      yanlış yazmışım, düzelttim" cümlesi içerir.

### Ayda bir — 10 dakika

- [ ] Usta'ya **`/denetle`** yaz. Kendi yazdığı koda dışarıdan baktırmak, en
      ucuz kalite kontrolüdür.
- [ ] **Dokümanların hâlâ doğru olduğunu sor.** Kod her gün değişir, README
      değişmez; "doğru görünen ama karşılığı olmayan cümle" bu projede bulunan
      en pahalı hata sınıfıydı.
- [ ] **Backlog'a bak.** Orada üç aydır duran bir madde ya artık gereksizdir ya
      da aslında acildir — ikisi de bir karardır, "unutuldu" bir karar değildir.

### Usta'ya güvenme, doğrulat

Bunlar kibarlık değil, yöntem: bir AI asistanı **emin olmadığında da akıcı
konuşur.** Şu üç soru neredeyse bedavadır ve çok şey yakalar:

1. *"Bunu ölçtün mü, yoksa okuyup mu çıkardın?"*
2. *"Bu testi eski hatayı geri koyarak denedin mi?"*
3. *"Bunun aynısı başka nerede olmalıydı?"* (5. kural — simetriğini ara)

## Yeni projeye başlarken

```bash
cd "Proje Yardımcısı"
./yeni-proje.sh ~/Desktop/YeniProjem
```

Script kural dosyalarını **köke** kopyalar, `PROJECT.md`'yi BOŞ ŞABLON olarak
kurar ve STATE'i sıfırlar. Sonunda ürettiği her dosyayı tek tek doğrular:
eksik dosya, boş dosya ya da AGENTS.md'ye yönlenmeyen bir köprü bulursa
**durur** — çünkü sessiz eksik kopya, kural sisteminin hiç devreye girmemesi
demektir ve kendiliğinden hata vermez.

Sonra tek yapman gereken:

1. Yeni klasörü AI aracında açıp `/baslat` yazmak.
2. Gerisi Usta'da: PROJECT.md boş olduğunu görür, sana proje fikrini sorar,
   turlar halinde sorularla projeyi anlar, anladığını sana onaylatır ve
   PROJECT.md'yi **kendisi doldurur**. Sen sadece anlatırsın.

`ai/PROFILE.md` ve `ai/LESSONS.md` projeler arası ortaktır — bir yerde
güncellediğinde bu şablona da geri taşı, tek doğruluk kaynağı burası olsun.

## Araç uyumluluğu notları

- **Claude Code:** CLAUDE.md'yi otomatik okur → AGENTS.md'ye yönlenir.
- **Cursor:** AGENTS.md'yi doğrudan okur (eski .cursorrules'a gerek yok).
- **Antigravity:** AGENTS.md'yi okur; çakışmada GEMINI.md öncelikli olduğu
  için araca özel ayarlar GEMINI.md'ye yazılır.
- **VS Code (Copilot):** `.github/copilot-instructions.md` → AGENTS.md'ye yönlenir.
- **Cline / Continue / Roo:** AGENTS.md'yi okuyabilir; okumazsa ilk mesajda
  "AGENTS.md'yi oku ve uygula" yazman yeterli.

Her araçta geçerli son çare: sohbetin ilk mesajına şunu yaz →
**"AGENTS.md'yi oku ve oradaki kurallara göre çalış."**

⚠ **Kural dosyaları KÖKTE durmalı.** Hiçbir IDE alt klasördeki AGENTS.md'yi
otomatik okumaz; yanlış yerdeki doğru dosya yok hükmündedir ve hata da
vermez, sadece sessizce devreye girmez (LESSONS L-004). Kurduktan sonra
`/durum` yazıp gerçekten yüklendiğini **test et** — dosyanın varlığını görmek
yeterli değil.
