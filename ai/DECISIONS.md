# DECISIONS.md — Karar Günlüğü (ADR)

> Yalnızca ÖNEMLİ kararlar: mimari, araç, yaklaşım seçimleri.
> Her karar "neden"i ve "tekrar gözden geçirme koşulu" ile kaydedilir.
> En yeni karar en üste.

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
