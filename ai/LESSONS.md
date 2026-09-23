# LESSONS.md — Dersler ve Anti-Pattern'ler

> Geçmiş hatalardan çıkan dersler. Usta bunları bilir ve aynı çukura ikinci
> kez düşülmesine izin vermez. `/ders <olay>` komutuyla yeni ders eklenir.
> Bu dosya projeler arası taşınır — dersler birikir.

---

## L-031 — 2026-09-23 — Üretici yeşilken tüketici eksik kapanışla karar verebilir

**Anti-pattern:** Akşam işi bugünün yarım barını doğru biçimde dışlıyor, fakat
ertesi sabah V2 önceki günün tam barını yenilemeden eski geçmişi kullanıyor.
Beş günlük yaş toleransı ve görünür uyarı, yeni alımı durdurmuyordu.

**Düzeltme:** Tüketici kendi kararından önce beklenen tam tarihi doğrular;
eksikse geçici arşivde yeniler ve yalnız tam sonucu atomik yayımlar. Başarısız
yenilemede eski arşiv korunur, yeni alım kapanır, mevcut stop açık kalır.
Gölge model karnesi de eski kapanıştan yeni tahmin kaydedemez.

**Kilit:** Gerçek SQL kopyasında eski/yeni kapanışla tam çevrim; başarısız ve
gelecek tarihli yenilemede bayt eşliği; iki piyasada yeni alım/stop testi.

---

## L-030 — 2026-09-22 — Bir kez doğru olmak, son durumun doğru teslim edildiğini göstermez

**Anti-pattern:** Gün içinde geçmiş bir makbuz varsa iyileşmeyi yeniden göndermemek;
son mevcut fiyatı başka haftanın gerçekleşmesi saymak; fiyatı kaybolan varlığı
beklenen evrenden de düşürmek. Üçü de eksikliği sessizce başarıya çevirir.

**Düzeltme:** Son gönderilen durumla karşılaştır, gerçekleşmeyi mühürlü zamana bağla,
paydayı gözlenen satırdan bağımsız kur. Öğrenme vadesini kararla birlikte kaydet;
ayar değişikliği eski sınavı değiştirmesin. Eksik veri normal sonuç değildir.

**Kilit:** A→hata→A gönderim testi; doğru gün/eksik gün/tekrar import; kayıp tarihsel
sembolle tam çevrim ve gölge stopu. Yeni korumanın eski kodda kırmızıya döndüğünü
sına. Salt test başarısı yetmez: gerçek arşiv, muhasebe, karar tekrarı ve geri dönüş
birlikte doğrulanır. Kanıt: `reports/URETIM-DENETIMI-2026-09-22.md`.

---

## L-029 — 2026-09-17 — Cron sıklığı, zaman garantisi değildir

**2026-09-23 durum notu:** Aşağıdaki yerel `launchd` tercihi o tarihteki
tasarımdır; bu Mac'te kurulu runner doğrulanmadı. Güncel üretim kararı
ADR #026: nominal GitHub cron yedeği ve ayrı boşluk gözlemi, zaman garantisi yok.

**Anti-pattern:** Saatlik bir piyasa çevrimini GitHub Actions `schedule` ile
çalıştırıp cron ifadesinin çalışma sıklığını garanti ettiğini varsaymak.

**Düzeltme:** 2026-09-16 üretim kanıtında işlerin çoğu hiç başlamadı; geç
başlayan koşu seans dışına düştü. Seans içi V2 çevrimi, Mac uyanıkken `launchd`
ile 10 dakikada bir yürütülür; GitHub bağımsız teslim/gözcü yedeği kalır.
Nöbetçiyi yeşile zorlamak yerine eksikliği görünür tutmak zorunludur.

**Kilit:** `ops/advisor_local_runner.sh` temiz olmayan ağaçta koşmaz, önce
fast-forward günceller, hata arşivini de teslim eder; iki LaunchAgent plist'i
`plutil -lint` ile doğrulanır.

---

## L-028 — 2026-09-16 — Koruyucu çıkışın kapısını ayrı sına

**Anti-pattern:** Eski analizle yeni alımı engelleyen şartın mevcut stopu da
engellemesi; bayat kotasyonun güncel servet/risk bütçesi sayılması. Bir testin
geçmesi, hatalı eski uygulamayı gerçekten yakaladığını tek başına göstermez.

**Düzeltme:** Girdi fiyat güvenilirliği ve yeni fırsat için analiz yeterliliği
ayrıldı. Bayat değerleme bilinmiyor olarak taşındı. Stop testi geçici kopyada
eski analiz kilidi geri konularak sınandı: beklenen SAT yerine VERİ BEKLENİYOR
üretildi ve test kırmızıya döndü. İki repo ve ortak mekanizma birlikte korundu.

**Ek ders:** Gerçek günlük fiyatlarla simülasyon, tam %3 makasın float hatasıyla
sınırı aştığını ortaya çıkardı. Ondalık karşılaştırma ve ihmal edilebilir sayısal
tolerans eklendi; eşik üstündeki gerçek fiyat farkını reddeden sınır testi kondu.

**Kilitler:** `tests/test_advisor_safety.py`, `tests/test_advisor_measurement.py`,
`tests/test_advisor_operations.py`. Test verisi gerçek data/advisor'a yazamaz;
simülasyon ve geri dönüş yalnız geçici dizinlerde sınanır.

---

## L-027 — 2026-09-15 — Karar, muhasebe ve teslim aynı doğruluk sınırını paylaşır

**Olay.** Revizyonda tek başına doğru görünen parçaların birleşiminde sorunlar çıktı:
BIST ölçüm evreni filtresi canlı izlenen iki hisseyi düşürüyordu; analizden sonra yükselen
fiyat eski hedefe göre yeniden kazanç gibi sayılabiliyordu; alış masrafı küçük tutarda risk
bütçesini aşabiliyordu. Push retry döngüsünün son komutu başarılıysa kayıt teslim edilmeden
workflow yeşil kalabiliyordu. Mobilde tablo genişliği bütün sayfayı taşırıyordu.

**Ders.** Test, gerçek para akışını ve teslim sırasını kurmalı: al → aynı koşuyu tekrarla →
yeniden aç → sat → aylık katkı. Sadece karar etiketini kontrol etmek yeterli değil.
Katkıları kâr sayma; al-tut getirisini de aynı şekilde hesapla. Ekran geçmişi kırpıldı diye
getiri hesabı yeniden başlamamalı. Kaynak kapsamı, modelin eğitim uygunluğundan ayrıdır.

**Kilit.** `tests/test_advisor_flow.py` al/sat zincirini, fiyat hareketini iki kez saymamayı,
katkıyı ve başarısız push çıkışını sınar. `tests/test_advisor_v2.py` muhasebe, makas, kalite,
öğrenme ve bildirim sınırlarını sınar. Mobil 390 px görünümde sayfa genişliği de ölçüldü.
Üretim SQL'ini salt okunur açan ayrı deney, yerel eski binary DB'ye güvenilmesini engelledi.

---

## L-026 — 2026-09-02 — Zamanlanmış bir işin GÜNÜ, başladığı an değildir

**Olay — nöbetçi tam ters çalışıyordu.** Gelen GitHub arıza maillerinin
tamamı (2026-08-26, 2026-09-01) `Nobetci` işindendi ve **hiçbiri gerçek
arıza değildi.** Aynı hafta gerçek iki arıza ise HİÇ mail üretmedi.

| An (UTC) | Gerçekte olan | Gözcünün dediği |
|---|---|---|
| 08-26 22:27 | günlük iş 18:21'de sorunsuz bitti | 🔴 "bugün koşu KAYDI YOK" → mail |
| 08-28 03:51 | **08-27 seansı analiz edilmemiş** | 🟢 yeşil, mail YOK (satır yalnız Telegram'a düştü) |
| 08-29 02:25 | **Cuma seansı analiz edilmemiş** | 🟢 "koşu beklenmiyor" — tamamen sustu |
| 09-01 21:58 | günlük iş 19:32'de sorunsuz bitti | 🔴 "bugün koşu KAYDI YOK" → mail |

**Tek kök sebep.** "Bu koşu hangi gün için?" sorusunun cevabı işin BAŞLAMA
SAATİNDEN okunuyordu (`util.bugun_tr()`). GitHub cron gecikir — bu repoda
ölçüldü: 8,5 saat. Gecikme TR gece yarısını aşınca etiket bir gün kayar:

```
günlük iş  19:32Z  →  TR 22:32, 1 Eylül  →  heartbeat "2026-09-01"
gözcü      21:58Z  →  TR 00:58, 2 Eylül  →  soru      "2026-09-02"
                                             cevap: kayıt yok → 🔴
```

**Aynı kayma üç yerde birden hasar verdi:**

* **Etiket kayboldu.** `otonom_kosu`da 2026-08-27 ve 2026-08-31 için KAYIT
  YOK, 2026-09-01 için İKİ kayıt var. "Hangi gün koştum?" artık journal'dan
  okunamıyor.
* **Bir koşunun TAMAMI yendi.** 08-28 (Cuma) slotu 08-29T00:39Z'de koştu;
  etiket Cumartesi oldu, takvim kapısı "işlem günü değil" deyip her adımı
  atladı. Cuma seansı o gün hiç analiz edilmedi.
* **İki seans analizsiz geçti** (08-27 ve 08-31) ve bunu söyleyen tek satır
  çıkışı 0 döndürdüğü için GitHub bildirim kanalı hiç çalışmadı.

**En rahatsız edici kısım.** ADR #020 (08-28) tam bu olayın *bir yüzünü*
düzeltti: "aynı gün iki kez analiz edilmez". Teşhis doğruydu ama `asof`la
sınırlı kaldı — koşunun KİMLİĞİ hâlâ duvar saatindeydi. L-016'nın kardeşi:
*doğru teşhis, eksik yere uygulandı.*

**Ders.** Zamanlanmış bir iş için "bugün" diye bir şey yoktur; **slot**
vardır. Duvar saati, işin ne zaman başladığını söyler — hangi iş olduğunu
değil. Gecikme kontrolümüzde değildir, ama gecikmeye DAYANIKLI bir referans
seçmek bizim elimizdedir.

**Kural.** Zamanlanmış bir işte gün, dış dünyanın bir olgusundan türetilir:
* günlük koşu → `cal.last_closed_session()` (analiz ettiği seans),
* gözcü → *"kapanmış son seanstan BERİ koşu başladı mı?"* — takvim + saat,
  takvim GÜNÜ değil.

`date.today()`, `bugun_tr()`, `local_today()` bu soruların cevabı DEĞİLDİR.

**Kilitler.** `test_GECE_YARISINI_ASAN_gozcu_YANLIS_ALARM_VERMEZ`,
`test_CUMARTESIYE_TASAN_gozcu_SUSMAZ`,
`test_ANALIZSIZ_seans_isi_KIRMIZIYA_cevirir`,
`test_GECIKEN_kosu_HAFTA_SONUNA_tasinca_CUMAYI_analiz_eder`. Dördü de gerçek
olayın saatiyle kurulu; soru duvar saatine dönerse dördü birden kırılır.
Ayrıca dört olay üretim dump'ı üzerinde yeniden oynatıldı: kırmızı/yeşil
dağılımı tam TERS döndü.

**Kardeş ders:** aynı kök sebep `gold_tracking_system`'de de vardı ve orada
bir raporu KAYBETTİRDİ (gold L-021). İki proje aynı çukura ayrı ayrı düştü.

---

## L-025 — 2026-08-28 — Testin ağa çıkabilmesi, arkasındaki hatayı GİZLER

**Olay.** `test_temiz_cekim_0` yalnız `news.sync`'i mock'luyordu; ama
`cli.cmd_haber` aynı komutta ikinci bir dış çağrı daha yapıyor
(`news.sync_beklenen`) ve o mock'suzdu. Test gerçek KAP'a bağlanıyordu.
Ağı olan makinede yeşil, olmayanda kırmızı — yani testin sonucu neyi
kanıtladığına değil, **ağ durumuna** bağlıydı.

Sızıntı kapatılınca (`conftest.ag_yasak`) **iki** test düştü ve ikincisi çok
daha ciddiydi: `test_kap_kapaliysa_0`. Ölçülen çıktı şuydu —

```
KAP kapalı (config.sources.kap.enabled)
⚠ beklenen bildirim takvimi: ConnectionError: ... kap.org.tr
```

`sources.kap.enabled=False` iken bile KAP'a çıkılıyordu: `kap.fetch_beklenen`
yalnız kendi alt anahtarına (`beklenen_bildirim.enabled`) bakıyor, **ANA
ANAHTARI hiç okumuyordu.** Yani kapatma anahtarı kapatmıyordu — ve KAP düştüğü
için katmanı kapatan kullanıcı, kapattığını sanarak aynı hatayı almaya devam
ederdi.

**Kök sebep.** Testin ağa erişebilmesi, o çağrının BAŞARILI dönmesini
sağlıyordu; başarılı dönen bir çağrı da hatayı görünmez kılıyordu. Yeşil test,
"bu komut izole" inancını kayda geçirmişti (AGENTS §11 tuzak 4) ve o inanç
yanlıştı.

**Anti-pattern.** Bir testte tek bir dış sınırı mock'layıp "izole ettim"
saymak. Komutun kaç dış sınırı olduğunu SAYMADAN izolasyon iddia edilemez.

**Kural.**
1. Testlerde ağ **varsayılan olarak yasaktır**, tek tek mock'lanarak değil
   suite genelinde (`conftest.ag_yasak`). Gerçekten gereken test
   `@pytest.mark.ag_gerekli` ile İŞARETLENİR — işaret görünürdür, sızıntı değil.
2. Bir kapatma anahtarı yazdığında **kaynağın sınırına** koy, çağrı yerine
   değil: orada hiçbir çağıran atlayamaz (§11 tuzak 5).
3. "Kapalı" ile "çekilemedi" ayrı sonuçlardır (L-003) ve ayrı çıkış kodları
   hak ederler; birini diğerinin kovasına atmak, kullanıcıya var olmayan bir
   arıza gösterir.
4. Bir sızıntıyı kapattığında **arkasından ne çıktığına bak** — sızıntı
   genellikle tek başına durmaz, bir şeyi örtüyordur.

---

## L-024 — 2026-08-28 — Bir sayacın PAYDASI, saydığı şeyi kapsamayan bir kümeyse metrik sessizce yalan söyler

**Olay.** İki ayrı sayaç, aynı sınıf hatayla, aynı hafta yakalandı.

| Sayaç | Ne diyordu | Gerçek |
|---|---|---|
| `evaluate.araclar()` | `{replay: 20, gemini-3.6-flash: 3, claude-code: 2}` | `gemini-3.5-flash` **252 tahmin, 79 veto** — listede HİÇ YOK |
| koşu günlüğü "açık" | `337 açık` ve her seans +18 | Gerçek açık plan **17**; 320'si `time_barrier_date` NULL, yani hiç çözülemez |

Birincisinin bedeli: son üç haftanın BÜTÜN kararlarını veren model haftalık
değerlendirmeye yapısal olarak giremiyordu (`outcomes` ile INNER JOIN).
`reports/degerlendirme_gemini-3.5-flash_*.md` diye bir dosya yoktu ve 08-16 ile
08-23 Telegram özetleri **birebir aynıydı**. Kullanıcının kendi sohbetinde
günlük mesajlar her gün `🤖 gemini-3.5-flash` yazıyor, haftalık özet o modeli
hiç anmıyordu. ADR #013'ün temel vaadi — *"hangi model daha iyi analist
sorusunu sistem kendisi cevaplayacak"* — bu JOIN yüzünden imkânsızdı: yeni bir
modele geçilince o model ilk sonucu çözülene kadar (≈1 ay) görünmez oluyordu.

İkincisinin bedeli: açık plan sayısı 17'den 40'a fırlasa 337'nin içinde
görünmezdi. Aynı gün `saglik` doğru sayıyı ("17 açık plan") basıyordu — yani
**iki kanal aynı olguyu bir mertebe farkla söylüyordu.**

**Kök sebep.** L-023 tam bu hatayı `veto_value` ve `llm_contribution` için
düzeltmişti; **araç sayımına uygulanmadı** — üstelik aynı dosyanın 40 satır
yukarısında. L-008'in "simetriğini ara" kuralının dördüncü tekrarı.

**Anti-pattern.** Bir düzeltmeyi onu tetikleyen çağrı yerine uygulayıp
bitmiş saymak. Ve: iki farklı olguyu ("çözülebilir açık" / "karar kaydı",
"tahmin" / "çözülmüş tahmin") tek sayaçta toplamak.

**Kural.**
1. Bir sayaç yazarken sor: **saydığım küme, ölçmek istediğim olguyu kapsıyor
   mu?** JOIN'ler kapsamı sessizce daraltır ve hata fırlatmaz.
2. İki kanal aynı olguyu basıyorsa **eşliği bir test zorlasın** (L-022 madde 2).
   `saglik` ile `evaluate` bu turda tam olarak bu testle bağlandı.
3. Bir sayı "her gün artıyor ve hiç azalmıyorsa" o bir sayaç değil bir
   birikimdir — neyin izlenmek istendiğini ayrı bas.
4. Bir sayının ANLAMI değişince **etiketini de değiştir**: "20 çözülmüş karar"
   ile "252 tahmin" aynı kelimeyi paylaşamaz (AGENTS §8 — yorum bir iddiadır).

---

## L-023 — 2026-08-16 — Bir ölçüm, KAYNAK SORGUSUNDA kendi konusunu eleyebilir

**Olay.** Üç ölçüm birden "henüz veri yok" gibi görünüyordu; gerçekte üçü de
**hiç dolmayacaktı.**

| Ölçüm | Ne diyordu | Neden hiç dolmayacaktı |
|---|---|---|
| `veto_value` | `veto_sayisi: 0` | Kaynak `outcomes` ile INNER JOIN. Veto edilenin `plan_id`'si NULL → plan açılmaz → outcome yazılmaz → satır JOIN'de düşer. `predictions`'ta **17 veto** vardı. |
| `llm_contribution` | `n=0, "ölçüm yok"` | Kesit çözülmüş tahminlerden kuruluyor, dönem başına **≥3 isim** isteniyordu. Sistem dönem başına en fazla **2** plan seçer (`maks_pozisyon` risk-off'ta 2). Eşik yapısal olarak geçilemezdi. |
| `fwd_ret_20d` | 24/24 NULL | `_outcome` kolonu `None` kuruyordu, **hiçbir kod yolu yazmıyordu.** Şema yorumu "IC için" diyordu ve yanlış yeri gösteriyordu. |

Üçü de aylarca raporda durdu. `veto_value` için en acı ayrıntı: günlük rapor
her gün *"veto analistin en ölçülebilir katkısı"* başlığını basıyordu.

**Kök sebep.** Bir ölçümün PAYDASI, ölçtüğü olguyla aynı tabloya bağlanmıştı.
Veto edilen bir karar, tanımı gereği sonuç ÜRETMEZ — o yüzden sonuç tablosuna
bakan bir sorgu onu asla göremez. "Payda görünür olmalı" (L-007, AGENTS §11/2)
kuralının bir adım öncesi: **paydanın ölçülen olguyu KAPSADIĞINI doğrula.**

**Anti-pattern.** Sıfır dönen bir metriği "veri birikince dolar" diye kabul
etmek. Sıfırın iki sebebi vardır ve ayırt edilmeden geçilmemeli:
*henüz olmadı* mı, yoksa *hiç olmayacak* mı?

**Kural.**
1. Bir ölçüm sıfır/boş dönüyorsa **elle bir örnek üret** ve dolup dolmadığını
   gör. Dolmuyorsa sorun veride değil, sorgudadır.
2. Eşikleri sistemin ÜRETİM KAPASİTESİNE karşı sına: "dönem başına ≥3 isim"
   isteyen bir metrik, dönem başına 2 üreten bir sistemde bir ölçüm değil
   **süs**tür. Eşiği yazarken sor: *bu sayı bu sistemde ulaşılabilir mi?*
3. Bir metrik "bunu ayrıca izlemeli" diye not düşüyorsa (bu vakada `veto_value`
   tam olarak öyle yazıyordu), o not bir TODO değil bir **arıza raporudur**.
4. Bir kolonu şemaya eklerken **yazan kod yolunu da göster.** Yazarı olmayan
   kolon, yorumu ne kadar doğru olursa olsun NULL kalır (§11/4).

**Yan bulgu — bayrak yerine ölçüm.** Yarım barla üretilmiş koşuyu işaretlemek
için bir kolon eklenebilirdi; eklenmedi. `close_at_asof` ile `bars_daily.c`
zaten karşılaştırılabiliyordu. **Bayrak unutulabilir ya da yanlış yazılabilir;
yeniden hesaplanan bir ölçüm her zaman gerçeği söyler.** Bir durumu kaydetmeden
önce sor: bu, mevcut veriden TÜRETİLEBİLİR mi?

---

## L-022 — 2026-08-15 — Alınıp OKUNMAYAN bir parametre, hiç almamaktan daha tehlikelidir

**Olay.** Günlük raporun en üstündeki eylem listesi, 2026-08-14'te
"🟢 **KCHOL** — GİR — plan bugün tetiklenebilir, **engel yok**" yazdı. Aynı
raporun §2'si ve aynı günün Telegram özeti aynı isim için "plan_reddet ·
VETO `rejim_uyumsuz`" diyordu. Rapor hem kendi içinde hem kanallar arasında
çelişti — üstelik en çok okunan bölümde.

**Kök sebep — iki katman.** `eylem.siralama` `analiz` parametresini alıyordu,
`an = {a["ticker"]: a ...}` sözlüğünü kuruyordu, hatta döngünün içinde
`a = an.get(t)` satırı bile vardı. Ama `a` yalnız **`holdings` dalında**
okunuyordu ve portföy boştu. Elde olmayan isimler için okunan tek veto kaynağı
`e["aktif_vetolar"]` idi — o da paket üretilirken (zincir adım 7) hesaplanır,
analist adım 8'de koşar. Yani bugünkü veto o listede **yapısal olarak**
bulunamazdı; ancak ertesi gün "yürürlükte" diye görünüyordu.

**Neden fark edilmedi.** Kod okuyan herkes — insan ya da model — `analiz`
parametresini ve `a = an.get(t)` satırını görüp "analist dikkate alınıyor"
sonucuna varıyordu. İmza doğruydu, bağlantı yoktu. `test_eylem.py`'de
"aktif veto girişi geri iter" testi VARDI; kapsadığı şey **önceki günün**
vetosuydu, bugünkününki değil.

**Anti-pattern.** Bir fonksiyona veri geçirip o dalda kullanmamak. Boş bir
sözlükte gezinen bir `.get()`, okuyucuya bağlantı KURULMUŞ izlenimi verir;
`None` sessizdir ve hiçbir yerde patlamaz.

**Kural.**
1. Bir parametreyi aldığın her dalda ya kullan ya da o dalda **kullanılmadığını
   yaz.** "Alıp bir dalda kullanmak" bir uygulama değil, yarım uygulamadır
   (L-008'in imza düzeyindeki hâli).
2. **İki kanal aynı olguyu basıyorsa ikisini tek testte karşılaştır.** Burada
   Telegram doğru, markdown yanlıştı ve haftalarca kimse yan yana koymadı.
3. Bir düzeltmenin kilidini "çıktı değişti mi" diye kur, "beklenen çıktı geldi
   mi" diye değil: `siralama(analiz=veto) != siralama(analiz=None)`. Eski kodda
   bu iki çağrı **birebir aynı** sonucu veriyordu — asıl kanıt budur.
4. Zamanlama sor: bu veri, onu okuyan koddan **önce mi** üretiliyor? Paket
   adım 7'de, analist adım 8'de. Sıra yanlışsa bağlantı imkânsızdır ve hiçbir
   dize düzeltmesi onu kurtarmaz.

---

## L-021 — 2026-08-15 — Bir dersi ÜÇÜNCÜ kez öğrenmek: tek tabloyu bağlamak, bağlanmamışları ARAMAK değildir

**Olay.** `index_daily` 2026-08-06'da dondu; `bars_daily` 08-14'e geldi. Beş
işlem günü boyunca `regime_daily`'nin dört girdisinden **üçü** (XU100/SMA200
farkı, XU100 volatilitesi, USDTRY volatilitesi) bit bit aynı yazıldı —
`xu100_vs_sma200_pct = 6.3198532722`, beş gün üst üste. `alpha_vs_xu100`
NULL'a düştü. Hiçbir hata, hiçbir uyarı, hiçbir kırmızı koşu.

**Kök sebep.** `prices.daily` yalnız HİSSE barlarını çeker. Endeksi çeken
`prices.sync_indices`'in tek çağrı yeri `cli.cmd_veri` idi — yani `index_daily`
ancak Mert elle `bist veri gunluk` koştuğunda tazeleniyordu. **Bu L-002'nin
birebir tekrarıdır ve üçüncü tekrarıdır:**

| # | tarih | donan tablo | nasıl bulundu |
|---|---|---|---|
| 1 | 2026-07-24 | `history_daily` | elle export incelemesi |
| 2 | 2026-08-11 | `evds_daily` (TÜFE) | denetim |
| 3 | 2026-08-15 | `index_daily` | denetim |

**Asıl ders bu değil.** L-002 zaten yazılıydı ve doğruydu. İkinci tekrarda
`macro.daily` zincire eklendi, `_evds_tazelik` sağlık kontrolü yazıldı, README'ye
"aynı ders, ikinci kez" notu düşüldü. **Ve `sync_indices` 30 satır ötede,
aynı dosyada, bağlanmadan bırakıldı.** Yani ders uygulandı ama yalnız onu
tetikleyen tabloya.

**Anti-pattern.** Bir sınıf hatayı, onu fark ettiren örnek üzerinde düzeltip
kapatmak. L-008 "simetriğini ara" der; burada aranması gereken şey bir
simetrik değil, **bir SAYIMDI.**

**Kural.**
1. L-002 tetiklendiğinde tek tablo düzeltilmez: **yazılabilir tüm tabloları
   listele** ve her biri için "bunu kim, hangi adımda besliyor?" sorusunu
   cevapla. Cevabı "elle" olan her satır ya bağlanır ya STATE'e yazılır.
2. Bu soru **koşulabilir**: tablo → besleyen adım eşlemesini bir teste devret;
   eşlemede yeri olmayan yeni bir tablo eklemek suite'i kırsın (AGENTS §12.2).
3. Tazelik kontrolü, besleme adımıyla **birlikte** yazılır. Burada besleme yoktu
   ve kontrol de yoktu; ikisi aynı boşluğun iki yüzüydü.
4. Bir donmayı yakalayan en ucuz sinyal **bit bit aynı sayıdır.** Ardışık
   günlerde `6.3198532722` görürsen bu bir değer değil, bir arıza kaydıdır.

**Sınıflandırma notu (L-017 ile ilişki).** Endeks çekme adımı `KRITIK_ADIMLAR`'a
konmadı — tek koşuluk bir yfinance arızası fiyat tarafını öldürmemeli. Ama
`saglik._index_tazelik` bir **KAPI**'dır ve 2 seanstan sonra koşuyu durdurur;
yani adım fiilen "2 seans toleranslı kritik" sınıfındadır. L-017 gereği bu
devralma gizlenmedi, hem `otonom.gunluk` adım 2b'nin hem kontrolün yorumunda
yazılı.

---

## L-020 — 2026-08-12 — Bir gerekçe cümlesi "ve"yle birleşirse, hangi koşulun düştüğünü GİZLER

**Olay.** Plan üretilemeyen isimler tek bir cümle alıyordu: *"N giriş bandı
denendi; hiçbiri stop∈[1.5,4.0]×ATR **+** R:R≥1.5 kurallarını **birlikte**
sağlayamadı."* Cümle teknik olarak doğruydu. Ama 2026-08-12 huni teşhisi
gösterdi ki elenen 15 ismin **15'inde de stop bandı geçiyordu** — öldüren tek
şey R:R'dı. "Birlikte" kelimesi okuyanı ATR ayarına baktırıyordu ve haftalarca
kimse asıl sebebi görmedi.

**Kök sebep.** Birleşik bir koşulun ihlali, hangi bileşenin düştüğünü
söylemeden raporlanmıştı. Üstelik bunu söyleyebilecek veri VARDI: `elenen`
listesi her bant/stop kombinasyonunun neden düştüğünü tutuyordu — ama yalnız
BAŞARILI planlara iliştiriliyordu (`PlanOption.elenen_adaylar`), başarısızlıkta
çöpe gidiyordu. Yani teşhis detayı, tam ihtiyaç duyulan anda siliniyordu.

**Anti-pattern.** Bir kapı birden çok koşulu "ve" ile birleştiriyorsa, ihlal
mesajını da birleşik yazmak. Ve tanı verisini yalnız BAŞARI yolunda saklamak.

**Kural.**
1. Birleşik kapının ihlalini raporlarken **hangi bileşenin** düştüğünü yaz.
   Metinden türetme — sınıf kodu koy (`hedef_yakin` / `stop_bandi` /
   `rr_yetersiz`) ve testi metne değil KODA baktır (L-012).
2. Tanı verisi başarısızlık yolunda da dönmeli. Sor: *"bu bilgi en çok ne
   zaman lazım — işler yürürken mi, durduğunda mı?"*
3. Bir sınıf kümesi eklediğinde etiket sözlüğüyle eşliğini teste devret
   (§12.2); aksi halde yeni bir sınıf sessizce görünmez kalır.

---

## L-019 — 2026-08-12 — Girdisine mesafe koruması olmayan bir eşik, sessizce bir SEÇİM FİLTRESİNE dönüşür

**Olay.** `min_rr_t1: 1.5` bir kalite kapısı olarak yazılmıştı. Ama T1 "en yakın
direnç" seçiliyordu ve hedef tarafında mesafe koruması yoktu. Stop ≈ 2×ATR ve
giriş ≈ fiyat iken `R:R ≈ T1_uzaklık / 2` olduğundan, kapı fiilen şu kurala
dönüştü: **"yalnız üstünde ~3 ATR boşluk olan isimlere plan üret."** Kimse böyle
bir karar vermedi, hiçbir yerde yazmıyordu, ölçülmemişti.

Ölçüldü: üretilen 49 planın **hepsinde** T1 ≥ 2.44 ATR ve **31'inde** kaynak
"52 hafta zirvesi" — yani plan üretilen isimlerin çoğunda üstte hiç pivot
yoktu. Elenen 15 ismin en yakın direnç medyanı ise **0.36 ATR**: fiyatın
neredeyse üstünde duran, hedef değil gürültü olan seviyeler.

**Kök sebep.** Giriş tarafında mesafe koruması vardı
(`maks_giris_uzakligi_atr`, EUPWR artefaktından doğmuş); hedef tarafına
yazılmamıştı. L-008'in ("tek çağrı yerini düzeltmek kuralı uygulamak DEĞİLDİR")
bir yıl sonraki tekrarı — bu sefer aynı dosyanın içinde, 15 satır arayla.

**Neden pahalı.** İki katmanı birden bozuyordu:
- **Üretim:** evrenin %83'ü sessizce eleniyor, her gün aynı 4-5 isim dönüyordu.
- **ÖLÇÜM:** gürültü bandındaki bir T1, üçlü bariyer resolver'ında **rastgele
  bir `hedef` çözümü** üretir. Yani filtre yalnız neyin planlandığını değil,
  **karnenin ne dediğini** de eğiyordu.

**Anti-pattern.** Bir eşiği, kendisi sınırsız olan bir büyüklüğün oranına
uygulamak. `R:R = hedef_mesafesi / stop_mesafesi` — payda `stop_atr_bandi` ile
sınırlıyken pay serbestse, eşik payı ölçmeyi bırakır ve **payın kaynağını
seçmeye** başlar.

**Kural.**
1. Bir oran kapısı yazdığında sor: **payın ve paydanın kendi sınırları var mı?**
   Biri serbestse kapı bir kalite ölçüsü değil, bir seçim filtresidir.
2. Bir tarafa mesafe/aralık koruması yazdığında **simetriğini hemen ara** —
   "aynı büyüklüğün öbür ucu neresi?" (L-008'in oran hâli).
3. Bir kapı, gözlemi de üreten bir mekanizmayı besliyorsa (burada: plan →
   resolver → `outcomes`), o kapının yanlılığı **ölçüme de bulaşır**. Kapı
   değişikliğini yalnız üretim sayısıyla değil, **sonuç dağılımıyla** da ölç.
4. Filtreyi aday havuzunun **tabanına** uygula, kırpmadan SONRA değil:
   `en_yakın_3` alıp sonra elemek, dördüncü geçerli adayı hiç görmeden yok eder.

---

## L-018 — 2026-08-11 — Tarihe bağlı bir dosya yolu, kanıt değil GÖRÜŞTÜR

**Olay.** `llm_runs.output_path` "bu tahmini üreten analist çıktısı şu
dosyadadır" diyordu. 2026-07-30 için DOĞRU DEĞİLDİ: journal
`gemini-3.6-flash` diyor, `output_path`in gösterdiği dosya
`gemini-3.5-flash`'a ait ve TUPRS'ta hem `signal` (hold vs accumulate) hem
seçilen plan (A vs B) farklı. Üstelik TUPRS o pencerenin en önemli ismiydi —
iki kez hedefi vurdu ve tüm pozitif katkı ondan geldi.

**Mekanizma.** Çıktı `llm/out/<asof>/analysis.json` yoluna yazılıyordu ve yol
yalnız TARİHE bağlıydı. 2026-08-01'de asof 2026-07-30 için ÜÇ koşu atıldı.
Biri 3.6-flash ile geçip journal'a yazdı. Sonrakinde 3.5-flash denetimden
geçti ve **dosyayı yazdı**, ama journal'a kayıt adımı düştü. Dosya, kendisini
sahiplenmeyen bir koşuya ait kaldı ve önceki koşunun kanıtı diye orada durdu.

**Ders.** Bir kaydın gösterdiği dosya, o kayıttan BAĞIMSIZ olarak
değişebiliyorsa, o dosya kanıt değildir. İki şey gerekir ve ikisi de:
(a) yol kayda özel olmalı (`<run_id>.json`), (b) içerik mühürlenmeli
(`output_sha`). Ve bu, L-008'in "simetriğini ara" kuralının tam örneğidir:
GİRDİ `bundle_sha` ile mühürlüydü ve HF-02 bunu zorluyordu; **çıktının
mührü hiç yazılmamıştı.** Bir savunma kurduğunda sor: bunun aynısı akışın
öbür ucunda da olmalı mıydı?

**Kural:** çıktıyı yazan adım ile onu journal'a bağlayan adım ayrıysa,
aradaki boşlukta dosya sahipsiz kalır. Mühür o boşluğu kapatır.

---

## L-017 — 2026-08-11 — Kritik olmayan bir adım, başka bir kontrolün girdisi olduğu anda kritik olur

**Olay.** ADR #013 bilinçli bir karar vermişti: `analist` KRİTİK adım DEĞİL.
Gerekçe yazılıydı — *"zincirin tamamı düşse bile o gün üretilen plan
geometrisi ve risk çerçevesi tek başına değerlidir."* `otonom.KRITIK_ADIMLAR`
listesinde `analist` yoktu ve bu doğruydu.

Sonra L-015'in kontrolü eklendi ve `MAX(predictions.asof)`e baktı.
`predictions` yalnız analist başarılı olunca yazılır. Yani: **analistin iki
gün üst üste düşmesi, artık deterministik katmanı da öldürüyordu.** Hiçbir
yerde yazılı olmayan bir bağ, yazılı bir kararı sessizce iptal etti.

Aynı sınıf ikinci bir kapı daha açmıştı: `--analistsiz` bayrağıyla atılan bir
koşu hiç tahmin yazmaz, yani sistemi ertesi güne zehirli bırakırdı.

**Ders:** yeni bir kontrol eklerken sorulacak soru "bu kontrol doğru mu?"
değil, **"bu kontrol hangi adımın ÇIKTISINA bakıyor ve o adım düşebilir
mi?"**. Düşebiliyorsa, o adımın kritiklik sınıfını devralmış olursun —
üstelik kimseye söylemeden.

**Kural:** bir kontrolün girdisi, o kontrolün şiddetinden daha düşük
güvenilirlikte bir adımdan geliyorsa, kontrol o adımın sınıfını AŞAMAZ.

---

## L-016 — 2026-08-11 — Bir gözlemci, gözlediği sürecin ÜRÜNÜNE bakıp o süreci durduramaz

**Olay — dört işlem günü süren tam sessizlik.** 2026-08-06'da GitHub runner
günlük işi almadı (L-015'teki olay). Ertesi gün L-015'in çözümü devreye girdi
ve sistemi **kilitledi**:

```
_atlanan_kosu:  fark = takvim(MAX(predictions.asof) → son bar)
                fark >= 2  →  KRİTİK
otonom.gunluk:  KRİTİK varsa adım 4'te DUR (5,6,7,8 hiç koşmaz)
predictions'a yazan yer: adım 6 — yani KAPININ ARKASINDA
```

`MAX(asof)` yalnız kapının arkasında büyür; kapı ise o sayı büyümediği için
kapalı kalır. Fark her işlem günü 1 arttı: 2 → 3 → 4 → … Sistem veri çekmeye
ve commit atmaya devam etti, **sıfır analiz üretti** ve her gün aynı 🛑
mesajını gönderdi. Bu bir gecikme değil, mutlak kilitlenmeydi.

**En rahatsız edici kısım.** L-015'in kendi cümlesi şuydu: *"bir süreç kendi
yokluğunu haber veremez."* O cümlenin doğru sonucu "çözüm sürecin DIŞINDA
olmalı"ydı. Çözüm yine sürecin İÇİNE kondu — ve bu sefer süreci öldürdü.
Doğru teşhis, yanlış yere uygulandı.

**Testler neden görmedi.** 1193 test yeşildi. `test_saglik` "atlanan koşu
bulgusu üretiliyor mu"yu sınıyordu; `test_uctan_uca`nın 30 senaryosunun hepsi
TEMİZ bir başlangıç durumundan koşuyordu. *"Bir önceki seans atlanmışken
zincir bugün tamamlanıyor mu?"* diye soran tek bir test yoktu.
AGENTS.md §12'nin üçüncü katmanı
(modüller arası varsayım kırılması) tam olarak burayı tarif ediyor.

**Ders / kural.** Kontroller iki sınıfa ayrılır ve karıştırılamaz:

| Sınıf | Soru | Şiddet tavanı |
|---|---|---|
| **KAPI** | Bugünkü VERİYE güvenilir mi? | KRİTİK olabilir |
| **GÖZLEM** | Sistem SÜREÇ olarak sağlıklı mı? | en fazla UYARI |

Ayırt edici test tek cümle: **"bu bulguyu, bu koşunun kendisi düzeltebilir
mi?"** Evetse kapı olabilir (bayat bar → veri adımı çeker). Hayırsa gözlemdir
ve durdurma yetkisi YOKTUR.

**Uygulanışı — yorum değil, yapı:**
* `saglik.ekle_gozlem` şiddeti UYARI'da TAVANLAR; gözlem kontrolü ne
  döndürürse döndürsün kapıyı kapatamaz.
* Sayaç `otonom_kosu` heartbeat'inden okunur ve o kayıt koşunun EN BAŞINDA,
  kapıdan (hatta takvim kapısından) önce yazılır.
* Gerçek nöbetçi DIŞARIDA: `.github/workflows/nobetci.yml` — ayrı iş, ayrı
  zamanlama, ayrı runner talebi, salt-okur.
* Davranışsal kilit: `TestKapiKendiCiktisinaBakmaz` (journal'ın yaşı kapı
  kümesini değiştiremez, 0..30 gün parametrik) +
  `test_ATLANMIS_gunden_sonra_zincir_UCTAN_UCA_TAMAMLANIR`. Eski hata geri
  konarak DOĞRULANDI: 7 test kırmızıya döndü.

---

## L-015 — 2026-08-07 — Bir süreç kendi YOKLUĞUNU haber veremez

**Olay:** 2026-08-06'daki planlı otonom koşu GitHub tarafında düştü:
*"The job was not acquired by Runner of type hosted even after multiple
attempts."* İş 15 dakika kuyrukta bekledi ve HİÇ BAŞLAMADI.

Sonuç şuydu: `otonom.py` koşmadı → sağlık kontrolü koşmadı → Telegram
bildirimi ÇIKMADI. Kullanıcı açısından o gün **tamamen sessizdi**. Ne rapor
geldi, ne uyarı, ne hata. Fark edilmesi yalnızca `git log`'da eksik bir
commit'e gözle rastlamaya kalmıştı — ve bu, ancak başka bir iş için oraya
bakıldığı için oldu.

Kod kusursuzdu. Zincirin her halkası doğruydu. Bozulan şey zincirin
KOŞMAMASIYDI ve zincirin içindeki hiçbir kontrol bunu göremezdi.

**Ders:** L-010 "kontroller birbirini doğruluyorsa hiçbiri dış dünyaya
bakmıyordur" demişti. Bu onun bir üst katmanı: **bildirim mekanizması,
gözlediği sürecin İÇİNDE yaşıyorsa, o sürecin hiç çalışmamasını asla
bildiremez.** Bir sağlık kontrolü ne kadar iyi olursa olsun, koşmadığı gün
sıfır değerlidir; ve tam olarak koşmadığı günler en çok ihtiyaç duyulan
günlerdir.

Bu, "sessiz bozulma"nın en saf hâli: burada bozulan veri de değil, kontrol
de değil — **olayın kendisi hiç gerçekleşmedi** ve yokluğun bıraktığı iz
yalnızca başka bir şeyin eksikliği.

**Kural:** Zamanlanmış her iş için sor: *"bu iş HİÇ çalışmazsa bunu kim, ne
zaman fark eder?"* Cevap "işin kendisi" ise cevap yoktur. Tespit, bir SONRAKİ
koşanın GERİYE bakmasıyla kurulur: son başarılı çıktının damgası ile beklenen
takvim arasındaki fark. Bu kontrol dışarıdan elle de koşulabilmelidir
(`bist saglik` → "atlanan koşu"), yoksa aynı tuzağa bir kat daha girilir.
Ve şiddet kademeli olmalı: tek seferlik altyapı arızası olağandır, üst üste
iki gün değildir.

---

## L-014 — 2026-08-07 — Kalite kapısının PENCERESİ, kapının kendisi kadar önemlidir

**Olay:** Dış repo incelemesinden çıkan "bedelsiz kapsaması ölçülsün" maddesi
koşuldu. Beklenen sonuç "yfinance bedelsizleri kaçırıyor mu?" idi ve cevabı
HAYIR çıktı — 8 bedelsiz doğru oranlarla kayıtlı. Ama tarama yolda başka bir
şey buldu: **CCOLA'nın 2024-08-01 barı −%90.7.**

`corporate_actions`'ta kayıt VARDI (2024-08-13, oran 11.0) ama iki şey bozuktu:
tarih 12 gün kaymıştı ve seri geriye düzeltilmemişti (2024-07-31 kapanışı hâlâ
846 TL, ertesi gün 78.27). Aynı taramada üç vaka daha çıktı: TSPOR +%94.6,
AYGAZ +%72.5, HEKTS −%64.8 — hiçbirinin kaydı yok. Dördü de `in_measure=1`,
yani faktör ağırlıklarını kalibre eden panelde.

**Asıl mesele bunların var olması değil, GÖRÜNMEZ olmasıydı.** Kalite kapısı
(`_quality_row`) yalnız **son 252 bara** bakıyor. 2024-08-01 bugün o pencerenin
dışında; tablo `unexplained_jump=0` yazıyor ve isim "temiz" görünüyor. Yani
kapı bir zamanlar ateşlemiş olabilir, ama bugün soruyu sorduğunda cevap
"sorun yok". Bozuk bar hâlâ orada ve `backtest` hâlâ onu okuyor.

**Ders:** Kayan pencereli bir kontrol, pencerenin GERİSİNDE kalan bozulmayı
onaylamış olur. Bu L-007'nin ("veri sessizce dar") zaman eksenindeki hâli:
veri dar değil, **kontrolün görüş alanı** dar. Ve fark edilmesi daha zor,
çünkü kontrol yeşil yanar.

Ayrıca: `unexplained_jump` "bu sıçramanın kaydı var mı?" diye sorup kayıt
varsa affediyordu. CCOLA'nın kaydı vardı. Doğru soru daha güçlüydü ve kayıttan
bağımsızdı: **±%10 marjlı bir piyasada −%50'lik bar hiçbir gerekçeyle meşru
değildir.**

**Kural:** Pencerelenmiş her kontrolün yanına, aynı olguyu **TÜM GEÇMİŞTE**
tarayan kalıcı bir kontrol koy (`saglik.duzeltilmemis_kurumsal_tara`). Ve bir
kontrol yazarken sor: *"bunu bir kaydın varlığı affedebilir mi? Affetmemeli
olduğu bir durum var mı?"* Kaydın varlığı bir açıklamadır, bir aklama değil.

---

## L-013 — 2026-08-07 — Kısmi örnekten genelleme: "en son 8 kayda baktım" bir ölçüm değildir

**Olay:** `index_daily`'de 54 OHLC tutarsızlığı bulundu, hepsi USDTRY'de. En
son 8 ihlale bakıldı, sapmalar %0.0009–%0.06 arasındaydı ve koda şu yazıldı:
*"sapma ≤ %0.06, Yahoo'nun bilinen FX kusuru, zararsız."* Sonra o iddiayı
sabitlemek için yazılan test **hemen düştü**: gerçek maksimum **%1.796**.

Tam dağılım bakılınca ortaya bambaşka bir şey çıktı: medyan %0.0068 (gerçekten
gürültü) ama kuyruk gerçek ve AÇIKLANABİLİR — 2021-03-22 (TCMB başkanının
görevden alınmasının ardından TL boşluklu açtı) ve 2024-01-01 / 2023-12-25
(tatil, donuk kotasyon). Yani "gürültü" değil, **medyanı gürültü, kuyruğu olay**
olan bir dağılım. İki farklı olgu, tek kelimeye sıkıştırılmıştı (L-003).

**Ders:** `ORDER BY date DESC LIMIT 8` bir örnektir, bir dağılım değil. En yeni
kayıtlar sistematik olarak en sıradan olanlardır — çünkü olağanüstü olaylar
geçmişte birikir. Bu yüzden "son N kayda baktım, hepsi küçük" cümlesi, tam da
aradığın şeyi (uç değerleri) dışarıda bırakan bir örnekleme yöntemidir.

**Kural:** Bir veri kusuru hakkında büyüklük iddiası yazacaksan **min, medyan,
maksimum ve eşik üstü sayımı** birlikte çıkar. Ve o iddiayı teste çevirirken
MAKSİMUMA eşik koyma — maksimum çoğu zaman geçmişte donmuş tek bir olaydır ve
ona eşik koymak geçmişi test etmektir. Dağılımın ŞEKLİNİ test et (medyan,
oran), tepe noktasını değil.

---

## L-012 — 2026-08-07 — Kendi yorumunu greplemek: naif metin araması yalancı tanıktır

**Olay:** `min_rr_t1` kapısının brüt R:R'a uygulandığını sabitlemek için bir
sözleşme testi yazıldı:

    kaynak = inspect.getsource(planner.build_options)
    i = kaynak.index('min_rr_t1')
    pencere = kaynak[i-300 : i+200]
    assert 'hedefler[0]["rr"]' in pencere

Test düştü. Sebep koddaki bir hata değildi: `min_rr_t1` ifadesinin İLK geçtiği
yer, aynı commit'te yazılmış bir **yorum satırıydı** ("nete geçmek `min_rr_t1`'i
fiilen 1.5 → ~1.60 yükseltir"). Yani test, kodu değil kendi açıklamamı okudu.

Aynı gün ikinci kez tekrarladı: `expected_disclosures` hata mesajı, var
olmayan bir `haber` alt komutuna yönlendiriyordu (çekim aslında mevcut bir alt
komutun içine katlanmıştı) ve doküman tutarlılık testi onu yakaladı. İkisinin
ortak yanı: **metin, koddan daha hızlı çoğalır.**

Üçüncü kez de bu dersi YAZARKEN oldu: yukarıdaki paragraf ilk hâlinde o
olmayan komutu birebir alıntılıyordu ve aynı test yine düştü — çünkü bir test
alıntılanan hatayı gerçek atıftan ayırt edemez. Ders metni bile kurala tabidir.

**Ders:** AGENTS.md §11'in kapatma tuzağı #2'si ("kontrol listesini kodla
doğrula, gözle değil; ama naif metin araması kendi yorumlarını yakalar") bu
projede teorik bir uyarı değil — iki kez, aynı oturumda gerçekleşti. Bir
kuralı kaynak metnine bakarak zorlamak meşrudur, ama metin **yorumlardan
arındırılmadan** değil.

**Kural:** Kaynak metnine bakan her testte önce yorum satırlarını SOY
(`if not l.strip().startswith("#")`), sonra ara. Ve mümkünse metin yerine
DAVRANIŞ test et: "brütü geçip neti geçemeyen bir plan üretiliyor mu?" sorusu
grep'ten hem daha sağlam hem daha anlamlıdır.

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
