# STATE.md — Mevcut Durum

> Usta her oturumun başında bu dosyayı okur, sonunda günceller.
> KISA TUT: ~100 satırı aşınca eskiyi `ai/archive/STATE-YYYY-MM.md`'ye taşı.

**Son güncelleme:** 2026-08-12
**Aktif milestone:** **Faz 11 KAPANDI** (ADR **#018** · L-019/020).
Beş bağımsız dış inceleme + kod/DB kazısı: `min_rr_t1` kapısı, hedef tarafında
mesafe koruması olmadığı için sessizce bir **seçim filtresine** dönüşmüştü.
Görünürlük paketi + kural düzeltmesi. Canlı evrende plan üretilen isim
**3 → 8**. Suite **1231 → 1244**.

## ✅ Tamamlananlar

**Faz 11 — gizli hedef filtresi** (2026-08-12) — ADR **#018** · L-019/020

`min_rr_t1` bir kalite kapısı sanılıyordu; T1 "en yakın direnç" seçildiği ve
hedef tarafında mesafe koruması olmadığı için fiilen **"üstünde ~3 ATR boşluk
olan isim" seçim filtresine** dönüşmüştü. Elenen 15 ismin **15'inde de stop
bandı geçiyordu** — öldüren tek şey R:R'dı.

`min_hedef_uzakligi_atr: 1.5` (`stop_atr_bandi` alt sınırından türetildi, sonuca
bakılmadan sabitlendi) + görünürlük paketi. **Canlı: plan üretilen isim 3 → 8,
kaybedilen plan 0.** Alfa 4.27→4.00pp → +4.27pp geometriden gelmiyormuş.
Ayrıca: rejim **tetikleyicisi** rapora yazılıyor (politika değişmedi) ve
`bist degerlendir` artık `--tool`suz koşunca **tüm kaynakları ayrı ayrı**
basıyor — canlı analistler (gemini-3.6-flash N=3, claude-code N=1) ilk kez
görünür oldu; eskiden komut çıkış kodu 2 ile duruyordu.
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

1. **Zincirin KENDİ BAŞINA iki gün koştuğunu gör.** Kilit açıldı ama kanıtı
   elle koşulmuş tek bir tur. DoD: 2026-08-12 ve 08-13 akşamları `gunluk.yml`
   yeşil bitiyor, Telegram'a rapor düşüyor, ve `bist saglik` "atlanan koşu"
   satırı ✓ basıyor (bugün "heartbeat boş" diyor — ikinci koşudan sonra
   gerçek karşılaştırma başlar). Elle iş yok, cron yapacak.
2. **Zincirin KENDİ BAŞINA koştuğunu gör.** ADR #018 canlı hattı değiştirdi
   ama kanıtı elle koşulmuş turlar. DoD: 2026-08-13 akşamı `gunluk.yml` yeşil
   bitiyor, Telegram'a rapor düşüyor, plan menüsü 3'ten fazla isim taşıyor ve
   `bist saglik` "atlanan koşu" satırı ✓ basıyor. Elle iş yok, cron yapacak.
3. **Replay'in +4.27pp'sinin KALAN açıklaması: limitli giriş.** ADR #018
   ölçümü "geometri filtresinden gelmiyor"u eledi (örneklem %60 büyüdü,
   ortalama ~4pp'de kaldı). Geriye limitli giriş avantajı kaldı. DoD:
   `backtest`'e "t+1 açılışta piyasa emri" varyantı eklenip aynı dönemlerde
   koşuluyor; fark bir satır olarak `reports/olcum_*.md`'ye giriyor.
   **Ön kayıt gerekmez** — mevcut bir sayının kaynağını ayrıştırıyor.

## 📦 Backlog (şimdi değil, unutma da)
- **Veto değeri ölçümü** — vetolananların PLANSIZ ileri getirisi izlenmeli
  (canlı: veto edilenler seçilenleri +5.76pp geçti, n=6 anekdot). İŞ 3'ten
  sonra: canlı karne görünmeden veto karnesi de görünmez.
- **Rejim OR/AND asimetrisi** — risk-on iki koşul ister (AND), risk-off birine
  yeter (OR): 16 risk-off etiketinin **14'ü** genişlikten, XU100 SMA200'ün
  ÜSTÜNDEYKEN. ADR #018'in etkisini ayırmak için dokunulmadı. Önce rapor
  tetikleyiciyi yazsın (`risk-off (tetikleyen: genişlik %28.4 ≤ 35 · XU100
  +%6.32)`), sonra tartışılsın.
- **`levels_daily` birikmiyor** — `dbdump.py` tabloyu dump'tan hariç tutuyor,
  `gunluk.yml` her koşuda DB'yi dump'tan kuruyor → yalnız son koşu kalıyor.
  `planner.py`'ın "seviyeler dondurulur" iddiası kodda karşılıksız (§8).
  Hafifletici: hedef dayanağı `plan_options.payload` içinde.
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
- **`falsifier` toplanıyor ama HİÇ sınanmıyor.** `journal.py` dışında kodda
  hiçbir yerde okunmuyor; bazıları mantıken ters (`avoid` için "düşerse tez
  çürür"). Otomatik yön kontrolü BİLEREK yazılmadı: naif metin araması kendi
  yorumunu yakalar (L-012). Ya anlamlı bir HF kuralı ya da alanın kaldırılması.
- **Analist katmanının katkısı ~sıfır ölçüldü** (canlı 90 tahmin): sinyal,
  deterministik yüzdeliğin monoton fonksiyonu (avoid 10.5 → accumulate 77.4).
  ADR #013'ün "hangi model daha iyi" ölçümü artık araç başına veri topluyor.
- **`bist portfoy ekle` kullanılmıyor** → kontenjan ve "azalt" bölümü kör.
  Rapor ve `bist saglik` artık bunu her gün yazıyor.
- **Net R:R kapıya alınsın mı?** 58 planın 19'u (%33) elenirdi. `min_rr_t1`
  `docs/on-kayit-seviye-02.md` §4'ün parametresi → **ön kayıt ister**.
- **`high52_prox` hipotezi** — OOS'ta +1.61pp (t=1.81), IC 0.113 (t=2.42):
  34 karşılaştırmada çıtayı geçen TEK satır. Sonucu görüp seçmek p-hacking →
  AYRI ve ön kayıtlı tur hak ediyor.
- **R:R'ın seçimle sağlanması** (#009): `docs/on-kayit-seviye-02.md` HAZIR
  ama koşulmadı.
- **Ekonomik takvim (TCMB/TÜFE)** ve **ikinci fiyat kaynağı kıyası** —
  repo incelemesinin #11 ve #12'si, ölçüm bekliyor.
- **Dump churn** — ölü koşular bile günde ~2.100 satır oynatıyor
  (`SATIR_KUME=500`). Repo 17,6 MB; acil değil, bir yıl sonra konuşulur.
- **KAP dilim bölme derinliği** — beklenen-bildirim ucunun tavanı 2000;
  45 günlük pencere 1863 kayıt veriyor, kırpılırsa SAKLANMIYOR.
- **Model zinciri sırası VERİYLE kurulmalı** (#013) — araç başına ölçüm
  2026-08-11'de fiilen başladı (replay 20 · gemini-3.6-flash 3 · claude-code 1).
