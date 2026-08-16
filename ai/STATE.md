# STATE.md — Mevcut Durum

> Usta her oturumun başında bu dosyayı okur, sonunda günceller.
> KISA TUT: ~100 satırı aşınca eskiyi `ai/archive/STATE-YYYY-MM.md`'ye taşı.

**Son güncelleme:** 2026-08-16
**Aktif milestone:** **Faz 12 — denetim düzeltmeleri** (bağımsız denetim
2026-08-15). Üç kritik + beş yüksek bulgu; ilk üçü kapandı, ölçüm hattı sırada.
Suite **1251 → 1263**.

## ✅ Tamamlananlar

**Faz 12 · ilk üç iş** (2026-08-16) — L-021/022

1. **Faz 11 canlıya alındı.** Rebase temiz (yerel commit'ler `data/`'ya
   dokunmuyordu), suite yeşil, push edildi. Doğrulandı: 08-14 kesitinde
   `min_hedef_uzakligi_atr` 0→1.5 plan üretilen ismi **5 → 9**, sektörü
   **3 → 7** yapıyor, kayıp 0.
2. **Endeks zincire bağlandı** (L-021). `index_daily` 08-06'da donmuştu,
   `bars_daily` 08-14'teydi: `sync_indices` otonom zincirde HİÇ yoktu —
   L-002'nin **üçüncü** tekrarı. Rejimin dört girdisinden üçü beş gün bit bit
   aynı yazılmıştı. Artık adım 2b'de çekiliyor + `saglik._index_tazelik`
   **KAPI** kontrolü (2 seans toleranslı, `_evds_tazelik`'in simetriği).
3. **Eylem listesi bugünkü vetoyu okuyor** (L-022). 08-14 raporu
   "🟢 KCHOL — GİR — engel yok" derken analist aynı isme veto koymuştu;
   `siralama` `analiz`'i alıp elde-olmayan dalda hiç okumuyordu. Gerçek 08-14
   paketiyle uçtan uca doğrulandı: "YENİ GİRİŞ" bölümü kayboldu, beş isim de
   gerekçeli BEKLE'ye düştü.

Üç düzeltmenin de kilidi **eski hata geri konarak** sınandı (6 test kırmızıya
döndü, geri alınca yeşil).

**Faz 11 — gizli hedef filtresi** (2026-08-12) — ADR **#018** · L-019/020.
**Faz 10 — kilitlenme ve denetim izi** (2026-08-11) — ADR **#017** · L-016/17/18.
**Faz 9 — karar anı katmanı** (2026-08-07) — ADR #015, #016 · L-012/13/14/15.
**Faz 8 — otonom koşu** (2026-08-01) — ADR #013, L-010/011.
**Faz 0-7 + denetim** (2026-07-26 … 07-29) — `ai/archive/STATE-2026-07.md`.
Özet: **ölçüm kapısı KAPALI** (#007), ön kayıtlı revizyon GEÇMEDİ (#008) →
sistem "izleme + risk disiplini + haber/veto". Kurallar teste devredildi (#011).

## 🔨 Devam Edenler
- _(yok)_

## 🧱 Bloklar / Bekleyenler
- _(yok)_

## 🎯 Sıradaki 3 İş

1. **Ölçüm hattını onar — tek iş, üç bulgu.** Üçü de aynı kolona dayanıyor:
   (a) `resolver` `fwd_ret_20d` / `fwd_alpha_20d_ew`'yi HİÇ doldurmuyor
   (24/24 NULL) ama şema yorumu "IC için" diyor; (b) `evaluate.llm_contribution`
   dönem başına ≥3 **çözülmüş** isim istiyor, sistem 2 üretiyor → yapısal
   olarak asla dolmayacak (üç kaynakta da `n=0`); (c) `evaluate.veto_value`
   vetolananları `outcomes` INNER JOIN'inde eliyor → 17 veto var, karne `0` diyor.
   DoD: `bist degerlendir` çıktısında `llm_katkisi.n > 0` **ve**
   `veto_sayisi = 17`; kesit `outcomes`'a değil `predictions`'a dayanıyor.

2. **Kâğıt portföy — sistem kendi kararlarını KENDİ takip etsin.**
   Mert'in kararı (2026-08-16): *"portföy şu an tamamen boş; proje kendisini
   bana kanıtlamalı. Başlangıç olarak proje gerçek zamanlı alım satım yapıyormuş
   gibi bu portföyü kullanmalı, kayıtlarını almalı."* Yani `holdings` artık
   Mert'in gerçek pozisyonu değil, **sistemin simüle portföyü**.
   Bu K-3/O-10'u da çözer: kontenjan kör olmaktan çıkar, KRDMD'nin altı üst üste
   girişi (harfiyen uygulansa tek isimde ~%29, rejim tavanı %20) mekanik olarak
   engellenir.
   ⚠ Tasarım soruları önce cevaplanmalı: başlangıç sermayesi? `plan_sec` →
   otomatik pozisyon mu, yoksa yalnız TETİKLENDİĞİNDE mi? çıkış `outcomes`'tan
   mı sürülecek? PROJECT.md'nin "sistem asla işlem yapmaz" maddesiyle çelişmez
   (emir yok, kayıt var) ama **kapsam eklemesidir** — ADR gerektirir.
   DoD: bir ADR + `bist portfoy` simüle modu + günlük raporun §1'i gerçek
   pozisyon basıyor.

3. **Örtüşme-ayıklanmış alfa + IC dönem seti.** Canlı karne aynı işlemi iki kez
   sayıyor: `2026-07-30-TUPRS-1` ve `2026-08-03-TUPRS-1` aynı giriş (08-04),
   aynı çıkış (08-06). Ham ortalama **+2.25pp (n=4)**, örtüşme ayıklanınca
   **−0.90pp (n=3)**. Ayrıca `information_coefficient` dönemleri **çözülmüş**
   tahminlerden alıyor → IC dönem seti sonuç-koşullu (10 karar gününün 4'ü).
   DoD: `paired_alpha` üçüncü sayıyı (`n_bagimsiz`, tekilleştirme
   `(ticker, entry_date, exit_date)`) basıyor; IC dönemleri `predictions.asof`.

## 📦 Backlog (şimdi değil, unutma da)
- **Telegram haftalık IC satırı hiç basılmıyor** — `otonom.py:389` `ic.get("n")`
  okuyor, `stats.ic_summary` `n_donem` döndürüyor. `.get` sessiz; `report.py:465`
  doğru anahtarı kullanıyor. Beş dakikalık düzeltme + yapı eşliği testi (§12.2).
- **Tetiklenmeyen planların bedeli ölçülmüyor** — 20 replay sonucunun 7'si (%35)
  paydadan tamamen düşüyor. Ölçüldü (2026-08-15): tetiklenmeyenlerin plansız
  H=20 alfası **+6.93pp**, tetiklenenlerin **+5.08pp** → fark **+1.85pp**.
  Yani limitli giriş bir avantaj değil **kaçırma yanlılığı** olabilir; eski
  "Sıradaki İş #3"ün (t+1 açılış varyantı) cevabına ucuz ipucu. Ön kayıt gerekmez.
- **2026-07-29'un 18 tahmini YARIM BARLA üretildi** — `close_at_asof` 18/18
  sapıyor (ort %1.21, hepsi aynı yönde); `llm_runs.created_utc` 10:38 UTC, seans
  açıktı. Yarım bar kapısı 08-11'de eklendi ama kayıt journal'da duruyor ve
  `claude-code`'un TEK canlı karne satırı o koşudan. Silme yok — bayrak + ayrı
  raporlama.
- **Analist katkısı üç bağımsız yoldan da ~sıfır** (2026-08-15 ölçümü): sinyal
  `pct`'nin monoton fonksiyonu; 162 ardışık gün çiftinin %93'ünde karar
  değişmiyor; 68 `avoid`'in 63'ü zaten `sma200_alti` kapısından düşmüş isimlere.
  Maliyet düşük (~$3/ay) → acil değil, ama "ölçülmüyor" ile "katkı yok" ayrı
  cümleler ve şu an karışıyorlar (bkz. Sıradaki İş #1).
- **Rejim OR/AND asimetrisi** — risk-off tek koşula (genişlik) yeter; 2026-07-24'ten
  beri 11 koşunun 11'i risk-off ve XU100 SMA200'ün DAİMA üstünde (+5.7…+9.7%).
  Aynı 15 işlem gününde ölçüm evreni −1.48% → duruş pahalıya patlamadı, ama
  politika tartışılmayı bekliyor.
- **`levels_daily` birikmiyor** — dump'tan hariç + her koşuda DB yeniden kuruluyor.
- **`high52_prox` ↔ hedef filtresi gerilimi** — `zirveye_yakin` sınıfıyla görünür.
- **Ölçüm şablonundan düşen "ters yönde kanıt" uyarısı** — şablon regresyonu.
- **TÜFE serisi ÖLDÜ** — `TP.FE.OKTG01` son gözlem 2025-12-01 (258 gün).
  EVDS'de yeni seri kodunu bul (TÜİK 2026 baz revizyonu olabilir).
- **`falsifier` toplanıyor ama HİÇ sınanmıyor** — ya anlamlı bir HF kuralı ya da
  alanın kaldırılması.
- **Net R:R kapıya alınsın mı?** 58 planın 19'u (%33) elenirdi → **ön kayıt ister**.
- **`high52_prox` hipotezi** — OOS +1.61pp (t=1.81), IC 0.113 (t=2.42); sonucu
  görüp seçmek p-hacking → AYRI ve ön kayıtlı tur.
- **R:R'ın seçimle sağlanması** (#009): `docs/on-kayit-seviye-02.md` HAZIR, koşulmadı.
- **Ekonomik takvim (TCMB/TÜFE)** ve **ikinci fiyat kaynağı kıyası** — ölçüm bekliyor.
- **Dump churn** — ölü koşular bile günde ~2.100 satır oynatıyor; acil değil.
- **KAP dilim bölme derinliği** — beklenen-bildirim ucu tavan 2000; 45 günlük
  pencere 1863 kayıt veriyor, kırpılırsa SAKLANMIYOR.
