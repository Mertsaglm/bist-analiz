# STATE.md — Mevcut Durum

> Usta her oturumun başında bu dosyayı okur, sonunda günceller.
> KISA TUT: ~100 satırı aşınca eskiyi `ai/archive/STATE-YYYY-MM.md`'ye taşı.

**Son güncelleme:** 2026-09-02
**Aktif milestone:** **Faz 13** — iki bağımsız dış denetimin (2026-08-25 GPT,
2026-08-28 Claude) uygulama turu. Kayıt bütünlüğü + görünürlük katmanı kapandı;
ölçüm/karar gerektiren maddeler Mert'e taşındı. Suite **1299 → 1325**,
ve suite artık **hermetik** (ağ yasak). Yeni: ADR **#020**, L-024/025,
AGENTS **§12c**.

## ✅ Tamamlananlar

**Faz 13 — denetim uygulaması (14 madde)** (2026-08-28) — ADR #020 · L-024/025.
Kayıt bütünlüğü, görünürlük, hermetik suite, CI'da gerçek veri.
Ayrıntı: `ai/archive/STATE-2026-08.md`.

**Faz 12 — denetim düzeltmeleri + kâğıt portföy** (2026-08-16) — ADR #019 · L-021/22/23.
**Faz 11 — gizli hedef filtresi** (2026-08-12) — ADR #018 · L-019/020.
**Faz 10 — kilitlenme ve denetim izi** (2026-08-11) — ADR #017 · L-016/17/18.
**Faz 9 — karar anı katmanı** (2026-08-07) — ADR #015, #016 · L-012/13/14/15.
**Faz 8 — otonom koşu** (2026-08-01) — ADR #013, L-010/011.
**Faz 0-7 + denetim** (2026-07-26 … 07-29) — `ai/archive/STATE-2026-07.md`.

## 🔨 Devam Edenler

**Faz 14 — gecikmeye dayanıklı zaman çıpası** (2026-09-02) — ADR **#021** · L-026.
Kod + testler HAZIR, `denetim-2026-08-28` dalında; **PR #1 hâlâ AÇIK.**

| # | İş | Kanıt |
|---|---|---|
| 1 | **Koşunun günü = analiz ettiği seans** | `otonom.gunluk` artık `last_closed_session()`ten okuyor. 08-28 (Cuma) slotu Cumartesiye taşınıp koşunun TAMAMI atlanmıştı. |
| 2 | **Gözcünün sorusu takvime bağlandı** | "Kapanmış son seanstan BERİ koşu başladı mı?" Dört gerçek olay üretim dump'ında yeniden oynatıldı: 08-26 🔴→🟢, 08-28 🟢→🔴, 08-29 🟢→🔴, 09-01 🔴→🟢. |
| 3 | **`analizsiz` bulgusu artık KIRMIZI** | 08-28T03:51Z'de gözcü doğru bulguyu buldu, çıkış 0 döndü, GitHub maili çıkmadı. |
| 4 | **`journal.son_kosu_zamana_gore`** | "En son ne zaman koştum?" etiketten değil saatten okunur. |


## 🧱 Bloklar / Bekleyenler
- **Mert'in kararını bekleyen 5 madde** — aşağıdaki "Karar bekleyenler".
- 🔴 **PR #1 (`denetim-2026-08-28`) 2026-08-28'den beri AÇIK.** `main` bu
  yüzden ADR #020'nin (aynı gün iki kez analiz) kapısını TAŞIMIYOR ve Faz 14
  düzeltmeleri de o dalda. Otonom koşu `main`'den kostuğu için düzeltmelerin
  hiçbiri üretimde DEĞİL. Merge edilene kadar her gecikmiş koşu aynı riski
  taşıyor.
- 🟡 **İki seans analizsiz kaldı: 2026-08-27 ve 2026-08-31.** `predictions`ta
  o iki `asof` YOK (08-28 → 09-01 atlıyor). **Geriye dönük doldurulmadı** —
  geç üretilen bir kararı canlı karneye yazmak ölçümün anlamını değiştirir
  (ADR #014'ün kardeşi). Mert'in kararı: boş kalsın mı, `kaynak="gec"` gibi
  ayrı bir etiketle mi doldurulsun?
- 🟡 **`otonom_kosu` etiketleri geçmişte kaymış durumda:** 08-27 ve 08-31 için
  kayıt yok, 09-01 için iki kayıt var, 08-29'da `durum='atlandi'` bir hayalet
  kayıt duruyor. Yeni kod ileriye dönük doğru yazıyor; geçmiş kayıtlar
  DÜZELTİLMEDİ (journal değişmezdir — ADR #014).

## 🎯 Sıradaki 3 İş

1. **Bir sonraki koşuyu doğrula — on iki düzeltmenin ilk gerçek sınavı.**
   Bakılacaklar: haftalıkta 5 kaynak + `gemini-3.5-flash` veto 79 satırı ·
   `saglik`te "açık plan" ✓ mü · koşu günlüğü "17 açık plan · 320 karar kaydı"
   diyor mu · §0'da `analist bugün:` satırı · CI'da `skipped 0`.
   ⚠ Yeni kapı ilk kez canlıda sınanacak: bir cron gecikmesi olursa analist
   ATLANMALI, zincir DURMAMALI. DoD: beşi de gözlendi, sapma STATE'e yazıldı.

2. **Karar bekleyen 5 maddeyi Mert'le kapat** (aşağıdaki liste). Üçü ön kayıt
   ister, ikisi karnenin anlamını değiştirir — hiçbiri tek başına uygulanamaz.
   DoD: her madde ya bir ADR'ye ya da Backlog'a bağlandı.

3. **Analist kararlılığı bir METRİĞE dönüşsün** (ADR #020 "tekrar gözden
   geçir" a maddesi). 12/18 bir kazaydı; aynı `asof` için birden çok koşu
   varsa `bist degerlendir` bunu ölçebilmeli. Kapı sayesinde bir daha
   kendiliğinden oluşmayacak — yani ölçüm ancak bilerek kurulursa olur.
   DoD: ya bir metrik ya da "ölçülmeyecek" kararı, gerekçesiyle.

## ⚖️ Karar bekleyenler (Mert'e soruldu, 2026-08-28)

1. **Rejim etiketinin zamanlaması** — 135 örtüşmeyen pencere × 4 faz: rejim vs
   aynı ortalama maruziyetli SABİT portföy farkı ≤ +0.16pp, |t| ≤ 0.90;
   Sharpe 0.47 vs **0.55**. Portföyün getirisini en çok belirleyen kural.
   → ön kayıtlı tur ister.
2. **`high52_min_ufuk_gun: 21` vs üretim ufku 20** — en güçlü faktör canlı
   skordan SIFIR ağırlıkla düşüyor. ADR #008 buna "kurulum hatası" diyor ama
   düzeltmeyi bilerek ön kayda bıraktı. → ön kayıtlı tur ister.
3. **Kâğıt portföye nakit faizi + taban satırları** — portföy +0.59%,
   evren +9.41%, XU100 +9.92%, net mevduat +2.49% (üçü de bağımsız doğrulandı).
   Taban EKLEMEK ifşadır; nakde faiz İŞLEMEK karnenin anlamını değiştirir.
4. **Başlangıç sermayesi 10.000 → ~100.000 TL** — tam sayı yuvarlama pahalı
   isimleri sistematik küçültüyor (BIMAS %7.19 hedef → %3.82 gerçekleşen).
   Karnenin sayılarını değiştirir.
5. **`replay`in ADR #018 sonrası yeniden koşulması** — 20 replay kaydının
   5'inde T1 uzaklığı bugünkü 1.5×ATR eşiğinin altında; haftalığın tek
   N≥13'lük satırı iki kural setinin karışımı.

## 📦 Backlog (şimdi değil, unutma da)
- **Analist katkısı ölçümü ÇALIŞIYOR ama veri bekliyor** — `veto_value`
  her araçta `n_olculen=0`; ilk gerçek sayı ufuklar dolunca (≈2026-09).
- **Kâğıt portföy 20+ kapanmış işleme ulaşınca** TL bazlı değerlendirme
  bölümü (ADR #019 "tekrar gözden geçir" b).
- **Canlı sonuçların 5/5'i MÜHÜRSÜZ koşulardan** — model↔kayıt bağı
  ispatlanamıyor. Yeni kohort mühürlü; eskiye geçmişe dönük sha YAZILMAZ.
- **Bar yeniden yazımı** — 5 dump'ta 42 bar yeniden yazıldı, 3'ü OHLC.
  `ingested_utc` veri değişmese de güncelleniyor → günde ~685 satır sahte
  churn, gerçek düzeltmeler içinde kayboluyor.
- **`llm_runs` yalnız BAŞARILI koşuyu yazıyor** — zincir 08-04'te beşinci
  halkaya düştü, düşen dört modelin HF kodu hiçbir yerde yok.
- **TÜFE serisi ÖLÜ** — `TP.FE.OKTG01` son gözlem 2025-12-01 (270 gün).
- **Survivorship bias büyüklüğü ölçülmedi** — üç yerde ifşa, hiçbir yerde sayı.
- **`levels_daily` birikmiyor** · **`high52_prox` ↔ hedef filtresi gerilimi**
- **Net R:R kapıya alınsın mı?** 58 planın 19'u (%33) elenirdi → ön kayıt ister.
- **R:R'ın seçimle sağlanması** (#009): `docs/on-kayit-seviye-02.md` HAZIR, koşulmadı.
- **KAP dilim bölme derinliği** — kırpılan yanıt SAKLANMIYOR.
