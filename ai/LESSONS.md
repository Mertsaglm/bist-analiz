# LESSONS.md — Dersler ve Anti-Pattern'ler

> Geçmiş hatalardan çıkan dersler. Usta bunları bilir ve aynı çukura ikinci
> kez düşülmesine izin vermez. `/ders <olay>` komutuyla yeni ders eklenir.
> Bu dosya projeler arası taşınır — dersler birikir.

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
