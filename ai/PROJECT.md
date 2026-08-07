# PROJECT.md — Projenin Kimliği

> Bir kez yazılır, nadiren değişir.

## Proje Adı
BIST Analiz — hisse analiz ve karar destek sistemi

## Tek Cümlelik Amaç
Borsa İstanbul'da farklı sektörlerden seçilmiş 18 hisseyi düzenli izleyen; nicel
skorlama + LLM yorum katmanıyla gerekçeli, net ve **ölçülebilir** kararlar üreten;
kendi isabetini deterministik olarak takip eden kişisel karar destek sistemi.

## Başarı Kriteri
Klasik anlamda "kâr etmek" DEĞİL — çünkü bu makul sürede kanıtlanamaz (aşağıya bak).
Başarı şu üçü:

1. **Süreç çalışıyor:** veri → gösterge → faktör → plan → journal → çözüm zinciri
   look-ahead sızıntısı olmadan, çökmeden, tekrarlanabilir biçimde işliyor.
2. **Sıralama kalitesi ölçülebiliyor:** dönem-içi IC ~18 ayda anlamlı hale geliyor.
3. **Sistem kendi hakkında dürüst:** yeterli veri yokken "ölçüm yetersiz" diyor,
   erken kenar iddia etmiyor.

## ⚠ Projenin en önemli gerçeği — baştan yazılı

Bu sistem **getiri kenarını makul bir sürede kanıtlayamaz.**

H=20 işlem günü + örtüşmeyen pencere = yılda **~12 bağımsız gözlem**. "18 hisse ×
8 karar = 144 tahmin" yanıltıcıdır: piyasa düşünce 8 stop aynı anda tetiklenir —
bunlar sekiz şapka takmış tek gözlemdir.

Ölçüldü (2026-07-26): en iyi faktörde H=15'te ort=+0.72pp, sd=5.00 →
`gerekli_n = (2×5.00/0.72)² ≈ 193 dönem ≈ 11,5 yıl`. H=21'de ~9 yıl.

Bu yüzden `required_n()` birinci sınıf bir fonksiyondur ve **her değerlendirme
raporunda basılır**. "Ne zaman bilebiliriz?" bir his değil, hesaplanmış bir sayıdır.

## Kapsam (Ne VAR — v1)
- 18 hisselik sabit evren (`universe.yaml`), sektör tavanı 2
- Günlük bar; ana karar ufku **20 işlem günü** (swing)
- 3 faktör + 1 hipotez, kesitsel z-skor, kapılar (sektör nötralizasyonu KAPALI — ölçüldü, zarar veriyor)
- Deterministik plan menüsü (entry/stop/hedef/boyut) — LLM sayı üretmez
- LLM katmanı iki yoldan çalışır: **otonom zincir** (`bist otonom gunluk`,
  ADR #013) ve **IDE içinde manuel** (Claude Code / Codex / Antigravity / Kiro).
  İkisi journal'da ayrı `tool` olarak durur ve ayrı ölçülür.
- HF-01..HF-32 sert hata denetimi — geçmeyen çıktı journal'a giremez
- Değişmez tahmin günlüğü + **deterministik** üçlü bariyer sonuç çözümü
- Ölçüm harness'i: walk-forward, örtüşmeyen pencere, maliyetli, in-sample/OOS
- Yerel CLI + Türkçe markdown rapor
- **Sözleşme testleri:** projenin kendi kuralları (eşik zemini, LLM sınırı,
  kolon↔şema eşliği, doküman tutarlılığı) koşulabilir hale getirildi (#011)

## Kapsam Dışı (Ne YOK — bilerek)
- **İki-AI konsensüs** — 2× maliyet, ölçülmemiş fayda
- **Otomatik emir gönderimi** — sistem asla işlem yapmaz
- **Intraday veri** — 20 günlük ufukta bilgi katkısı ölçülmedi
- **Temel faktörler (F/K, PD/DD, ROE)** — TR temel verisi seyrek + TMS-29 enflasyon
  muhasebesi 2023 sonrası kıyası kırdı. Bu bir varsayım değil, **ölçemediğimiz için bir sınır**.
- **Sayısal haber/duygu skoru** — TR finans haberi büyük ölçüde gürültü; LLM'e prose
  olarak bırakılır, sayıya çevrilmez
- **Sektör nötralizasyonu (varsayılan)** — ölçüldü, kenarı düşürüyor
- **Telegram komut arayüzü** (`/durum`, `/rapor` gibi) — bildirim TEK YÖNLÜ:
  dışarı. Gelen komutları dinlemek sürekli çalışan bir süreç ister; ihtiyaç
  kanıtlanmadan kurulmaz.

## Kısıtlar
- **Bütçe:** ücretsiz-ÖNCELİKLİ. LLM analisti sıralı bir zincirdir; ilk üç
  halka ücretsiz katmanı olan Gemini modelleridir ve günde 1 istek attığımız
  için kota pratikte hiç dolmaz. Ücretli halkalara düşmek İSTİSNA;
  ay tavanı ~$3 (ADR #013 — gerçek paketle ölçüldü). Elle IDE turu (Claude)
  hâlâ mümkün ve bedava; journal ikisini ayrı `tool` olarak kaydeder.
- **Ortam:** macOS, Python 3.12 (poetry). Veri: yfinance + TCMB EVDS (ücretsiz).
- **Araç bağımsızlığı:** hiçbir IDE'nin özel özelliğine bağlanılmaz; girdi/çıktı düz dosya.
- **Veri:** yfinance BIST için tek ücretsiz kaynak. Kırılganlığı testle izlenir,
  ikinci kaynakla değil (gerçek bir kontrol patlayana kadar).

## Teknoloji Yığını
| Katman | Seçim | Karar kaydı |
|---|---|---|
| Dil / ortam | Python 3.12 + poetry | — (gold_tracking_system ile aynı) |
| Fiyat verisi | yfinance (`.IS`) | #002 |
| Makro | TCMB EVDS (gold'dan port) | — |
| Depolama | SQLite + deterministik SQL dump | — (gold deseni) |
| LLM | IDE içinde manuel, düz JSON sözleşmesi | #005 |
| Test | pytest — sözleşme + mekanizma + uçtan uca | #011 |

## Referans projeler
- `../gold_tracking_system/` — aynı kullanıcının üretimdeki quant projesi.
  Ölçüm kültürü, EVDS entegrasyonu, config disiplini ve SQLite dump deseni oradan.
- `~/.claude/skills/_arsiv/bist-coach/` — bu projenin emekli edilmiş öncülü.
