# STATE.md — Mevcut Durum

> Usta her oturumun başında bu dosyayı okur, sonunda günceller.
> KISA TUT: ~100 satırı aşınca eskiyi `ai/archive/STATE-YYYY-MM.md`'ye taşı.

**Son güncelleme:** 2026-08-15
**Aktif milestone:** **Faz 11 KAPANDI** (ADR **#018** · L-019/020).
Beş bağımsız dış inceleme + kod/DB kazısı: `min_rr_t1` kapısı, hedef tarafında
mesafe koruması olmadığı için sessizce bir **seçim filtresine** dönüşmüştü.
Görünürlük paketi + kural düzeltmesi. Canlı evrende plan üretilen isim
**3 → 8**. Suite **1231 → 1251**.

## 🚨 ŞU AN — dallar AYRIŞTI, düzeltme CANLIDA DEĞİL

**Zincir dört gün kendi başına koştu** (08-11 … 08-14) — Faz 10'un DoD'si
karşılandı, kilit gerçekten açık. Ama **Faz 11'in dört commit'i yerelde**
(`ahead 4, behind 4`): bulut o günlerde eski kodla koştu (08-14 banner'ı hâlâ
`6/9`, `min_hedef_uzakligi_atr` yok). ADR #018'in "3 → 8 isim" etkisi hiçbir
canlı raporda **görünmedi.** → Sıradaki İş #1.

## ✅ Tamamlananlar

**Faz 11 — gizli hedef filtresi** (2026-08-12) — ADR **#018** · L-019/020

`min_rr_t1` kalite kapısı sanılıyordu; T1 "en yakın direnç" seçildiği ve hedef
tarafında mesafe koruması olmadığı için fiilen **"üstünde ~3 ATR boşluk olan
isim" seçim filtresine** dönüşmüştü (elenen 15 ismin 15'inde de stop bandı
geçiyordu). `min_hedef_uzakligi_atr: 1.5` + görünürlük paketi + rejim
tetikleyicisi + `bist degerlendir` çok-kaynak. Canlı: **3 → 8 isim, kayıp 0.**
Ayrıntı: `ai/archive/STATE-2026-08.md` · `reports/olcum_hedef_mesafe_2026-08-12.md`.

**Faz 10 — kilitlenme ve denetim izi** (2026-08-11) — ADR **#017** · L-016/17/18.
Sistem dört işlem günü sessizce ölüydü: bir GÖZLEM kontrolü, gözlediği sürecin
ÜRÜNÜNE bakıp o süreci durduruyordu → kilit kalıcı. KAPI↔GÖZLEM ayrımı,
heartbeat (şema v10), dışarıdan nöbetçi, çıktı mührü (v11).
Ayrıntı: `ai/archive/STATE-2026-08.md`.

**Faz 9 — karar anı katmanı** (2026-08-07) — ADR #015, #016 · L-012/13/14/15.
Dış repo incelemesinin 10 maddesi uygulandı. Rapor:
`reports/repo-inceleme-2026-08-07.md`.

**Faz 8 — otonom koşu** (2026-08-01) — ADR #013, L-010/011.
**Faz 0-7 + denetim** (2026-07-26 … 07-29) — `ai/archive/STATE-2026-07.md`.
Özet: **ölçüm kapısı KAPALI** (#007), ön kayıtlı revizyon GEÇMEDİ (#008) →
sistem "izleme + risk disiplini + haber/veto". Kurallar teste devredildi (#011).

## 🔨 Devam Edenler
- _(yok)_

## 🧱 Bloklar / Bekleyenler
- _(yok)_

## 🎯 Sıradaki 3 İş

1. **Faz 11'i canlıya al ve doğrula.** Yukarıdaki 🚨 bölümü. Dört commit
   yerelde, bulut eski kodla koşuyor. DoD: `git pull --rebase` → suite yeşil →
   `git push`; sonraki otonom koşunun raporunda **plan üretilen isim > 3** ve
   `above_zone` banner'ı `X/Y (Z aday içinden gösterilen)` biçiminde.
   ⚠ Rebase sonrası suite'i koşmadan push etme: dört otonom commit `data/`
   dump'ını değiştirdi, çakışma sessiz olabilir.
2. **Portföy kaydını başlat** — sistemin SANA bağımlı olduğu tek yer.
   `holdings` boş olduğu sürece raporun en savunulabilir bölümü ("Elindekiler
   — azaltma adayları") ve kontenjan hesabı KÖR. Rapor bunu her gün yazıyor;
   yazması çözmüyor. DoD: `bist portfoy ekle <HİSSE> <adet> <maliyet>` ile en
   az bir pozisyon girildi ve günlük raporun §1'i "Portföyde kayıtlı pozisyon
   yok" demeyi bıraktı. (Pozisyon yoksa bile bu bir karardır — o zaman
   Backlog'a "portföy bilerek boş" diye yaz ve raporun uyarısını sustur.)
3. **Replay'in +4.27pp'sinin KALAN açıklaması: limitli giriş.** ADR #018
   ölçümü "geometri filtresinden gelmiyor"u eledi (örneklem %60 büyüdü,
   ortalama ~4pp'de kaldı). Geriye limitli giriş avantajı kaldı. DoD:
   `backtest`'e "t+1 açılışta piyasa emri" varyantı eklenip aynı dönemlerde
   koşuluyor; fark bir satır olarak `reports/olcum_*.md`'ye giriyor.
   **Ön kayıt gerekmez** — mevcut bir sayının kaynağını ayrıştırıyor.

## 📦 Backlog (şimdi değil, unutma da)
- **Veto değeri ölçümü** — vetolananların PLANSIZ ileri getirisi izlenmeli
  (canlı: vetolananlar seçilenleri +5.76pp geçti, n=6 anekdot).
- **Rejim OR/AND asimetrisi** — risk-off tek koşula (genişlik) yeter ve 16
  etiketin 14'ü öyle geldi, XU100 SMA200'ün ÜSTÜNDEYKEN. Tetikleyici artık
  raporda yazılı (Faz 11); politikanın kendisi tartışılmayı bekliyor.
- **`levels_daily` birikmiyor** — dump'tan hariç + her koşuda DB yeniden
  kuruluyor → yalnız son koşu kalıyor. `planner.py`'ın "seviyeler dondurulur"
  iddiası kodda karşılıksız (§8). Hedef dayanağı `plan_options.payload`'ta.
- **`high52_prox` ↔ hedef filtresi gerilimi** — zirveye yakın isim faktörde iyi
  skorlarken plan üretemiyor. ADR #018 bunu yaratmadı, `zirveye_yakin`
  sınıfıyla görünür kıldı.
- **Ölçüm şablonundan düşen "ters yönde kanıt" uyarısı** —
  `olcum_2026-07-26.md` basıyor, `olcum_2026-08-07.md` basmıyor; aynı
  negatif/anlamlı `mom_12_1` bulgusu dururken. Şablon regresyonu.
- **TÜFE serisi ÖLDÜ** — `TP.FE.OKTG01` son gözlem 2025-12-01 (253 gün).
  Tazelik kontrolü artık bunu her gün basıyor ve değer pakete girmiyor.
  Yapılacak: EVDS'de serinin yeni kodunu bul (TÜİK 2026 baz revizyonu
  olabilir) ve `config.sources.evds.series.tufe`'yi güncelle.
- **`falsifier` toplanıyor ama HİÇ sınanmıyor** — `journal.py` dışında hiçbir
  yerde okunmuyor, bazıları mantıken ters. Otomatik yön kontrolü BİLEREK
  yazılmadı (naif metin araması kendi yorumunu yakalar, L-012). Ya anlamlı bir
  HF kuralı ya da alanın kaldırılması.
- **Analist katkısı ~sıfır ölçüldü** (canlı 90 tahmin): sinyal, deterministik
  yüzdeliğin monoton fonksiyonu. ADR #013'ün "hangi model daha iyi" ölçümü
  araç başına veri topluyor (replay 20 · gemini-3.6-flash 3 · claude-code 1) —
  hepsi hâlâ "ölçüm yetersiz".
- **Net R:R kapıya alınsın mı?** 58 planın 19'u (%33) elenirdi. `min_rr_t1`
  `docs/on-kayit-seviye-02.md` §4'ün parametresi → **ön kayıt ister**.
- **`high52_prox` hipotezi** — OOS'ta +1.61pp (t=1.81), IC 0.113 (t=2.42):
  34 karşılaştırmada çıtayı geçen TEK satır. Sonucu görüp seçmek p-hacking →
  AYRI ve ön kayıtlı tur hak ediyor.
- **R:R'ın seçimle sağlanması** (#009): `docs/on-kayit-seviye-02.md` HAZIR
  ama koşulmadı.
- **Ekonomik takvim (TCMB/TÜFE)** ve **ikinci fiyat kaynağı kıyası** —
  repo incelemesinin #11 ve #12'si, ölçüm bekliyor.
- **Dump churn** — ölü koşular bile günde ~2.100 satır oynatıyor; acil değil.
- **KAP dilim bölme derinliği** — beklenen-bildirim ucunun tavanı 2000;
  45 günlük pencere 1863 kayıt veriyor, kırpılırsa SAKLANMIYOR.
