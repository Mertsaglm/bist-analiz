# Yerel denetim eki: getiri farkları ve sanal alım/satış kolları — 2026-09-25

> **Tarihsel kesit:** Bu belgedeki ölçüm ve yayın durumu yazıldığı tarihin kesitidir.
> Güncel üretim ve açık işler için [ai/STATE.md](../ai/STATE.md) ile
> [2026-10-01 deney durumuna](PORTFOY-DENEYI-2026-10-01.md) bakın.

Bu ek `docs/YEREL-DENETIM-2026-09-25.md` içindeki iki açık kanıt boşluğunu
inceler. İşlemler yereldir; banka/borsa bağlantısı, commit, push ve deploy yoktur.
Tarihsel getiriler yatırım üstünlüğü kanıtı değildir.

## 1. Eski ve yeni getirinin bileşenleri

Girdi, iki depodaki `reports/KARSILASTIRMA-2026-09-25.json` ile
`reports/archive/pre-audit-2026-09-25/KARSILASTIRMA-2026-09-25.json` dosyalarıdır.
Başlangıç 2025-09-01, bitiş 2026-09-24, son gözlenen fiyat 2026-09-22;
son bölüm 2026-06-01'de başlar. Yüzdeler katkılar hariç portföy getirisidir;
farklar **yüzde puandır**.

`scripts/audit_correction_components.py` şu eski davranışları yalnız bellek
içindeki fonksiyon kopyalarında açıp kapattı:

- **2025 takvimi:** 2025 yılı/tatilleri kaldırıldı; eski sürümde henüz olmayan
  `require_coverage` reddi bu karşı olgu için geçici olarak kaldırıldı.
- **Altın gün içi dolumu:** gerçek OHLC olmayan GRAM için eski stop/hedef kolu
  geçici olarak açıldı.
- **BIST veri kapsamı:** DSTKF ve TRALT satırları geçici veri çerçevesinden
  çıkarıldı. Bu çerçevenin hash'i eski rapordaki `10192255902222799050`
  değeriyle, güncel çerçeve `7600910552333773863` ile birebir eşleşti.
- **Saklama ücreti:** tatilde başlayan çeyreğe önceki bilinen seans değerini
  taşıyan yeni satırlar geçici olarak kaldırıldı.
- **Sıfır hacim:** eski dolum izni geçici olarak açıldı.

Altın veri hash'i eski ve yeni raporda aynı: `10081320150936271241`.
Eski/yeni kod hash'leri sırasıyla `c73e777a1c0531409586a76e2330539771eaa67fef850072ded49add6563620d`
ve `841f75118fa6aff2df856226b06fbc45f6d09647174fc7ca0700d32d6f8666e1`.
Her yöntem için eski ve güncel getiri/dolum sayıları arşiv raporlarıyla
`1e-8` toleransında yeniden üretilemezse denetim script'i hata verir.

### Altın: tüm 13 yöntem

Tam dört kombinasyonun makbuzu: `reports/DUZELTME-ETKI-ALTIN-2026-09-25.json`.

| Yöntem / dönem | Eski | Yeni | Değişim | Etkiyi üreten anahtar |
|---|---:|---:|---:|---|
| `sma50` geliştirme | -0,162431 | +10,091625 | +10,254056 | 2025 takvimi |
| `sma50` son bölüm | +1,918838 | +1,921938 | +0,003100 | 2025 takviminin sonraki portföy yolu |
| `recency` geliştirme | -1,410144 | -2,380478 | -0,970333 | Hayali gün içi dolumun kaldırılması |
| `recency` son bölüm | -4,099717 | -2,548057 | +1,551659 | Hayali gün içi dolumun kaldırılması |

`sma50` için eski takvimle 2025'te 84 gün veri engeline takıldı; ilk alım
2026-01-02 idi. Yeni takvimde ilk alım 2025-09-02; iki koşuda da toplam
9 dolum var ama işlem yolu ve yatırımda kalınan dönem değişti. Gün içi dolum
anahtarı `sma50` getirisini değiştirmedi. Bu nedenle 10,254 puanlık sıçrama
sayısal olarak takvime atfedilebilir.

`recency` ilk alımı 2026-05-14'te yaptı; 2025 takvim anahtarı getirisini
değiştirmedi. Eski gün içi varsayımı 7, güncel günlük referans mantığı 5 dolum
üretti. `adaptive`, `without_pullback`, `without_short_momentum` ve
`without_volatility` satırlarının iki dönemdeki NAV serileri `recency` ile
aynı; karşı olgu makbuzunda da aynı fark yeniden üretildi. `window` ve
`without_relative_breadth` geliştirme farkı da gün içi dolumdan geliyor.
`short`, `pullback`, `pullback_without_shape`, `control`, `regime_none` dört
kombinasyonda da sıfır dolum ve sıfır getiri verdi.

### BIST: etkileşimi gösteren ana üç satır

Tam beş durumun makbuzu: `reports/DUZELTME-ETKI-BIST-2026-09-25.json`.
İlk dört durumda güncel saklama ve sıfır hacim kuralı kullanıldı; “hepsi eski”
durumunda bu iki davranış da geri alındı.

| Durum | `control` geliştirme | `sma50` geliştirme | `recency` geliştirme |
|---|---:|---:|---:|
| Hepsi eski, arşivle eş | -0,093071 | +23,099754 | +1,001622 |
| Eski takvim + eski veri; saklama düzeldi | -0,204848 | +22,945694 | +0,889952 |
| Yeni takvim + eski veri | -0,503246 | +7,639848 | +0,581724 |
| Yeni takvim + yeni veri; güncel | -0,813124 | +19,100325 | -2,588203 |

Bu **belirtilmiş sıraya göre** geliştirme farklarının dökümü:

| Yöntem | Saklama düzeltmesi | 2025 takvimi | DSTKF/TRALT geçmişi | Toplam |
|---|---:|---:|---:|---:|
| `control` | -0,111777 | -0,298398 | -0,309878 | -0,720053 |
| `sma50` | -0,154060 | -15,305846 | +11,460477 | -3,999429 |
| `recency` | -0,111670 | -0,308227 | -3,169928 | -3,589825 |

Son bölümde `control` ve `recency` eski veriyle %0'da kalıyor; güncel veri
eklenince sırasıyla %-0,719022 ve %-0,728575 oluyor. `sma50` son bölüm
eski %-4,718184; yalnız saklama düzelince %-4,718929, takvim de açılınca
%-1,744818, geçmiş tamamlanınca %-8,310291. Güncel `sma50` dolumu 143,
eski 59; `control` 22/14 ve `recency` 20/12. Eski uç durumda sıfır hacim
iznini açmak bu üç satırın getiri/dolumunu değiştirmedi.

**Paylar sıra bağımlıdır.** Örneğin `sma50` için DSTKF/TRALT geçmişi eski
takvim açıkken geliştirme getirisini değiştirmiyor; yeni takvim açıkken
+11,460477 puan değiştiriyor. Bu etkileşim yüzünden tek bir doğal “takvim
payı” veya “veri payı” yoktur. Tablodaki sıra ve dört durum birlikte okunmalı.
Eski kaynak ağacının tam kopyası saklanmadı; eski davranışlar denetim script'inde
geri kuruldu. Eski hash ve arşiv çıktılarının yeniden üretilmesi, ölçülen
satırlar için güçlü bir sağlama sağlar; tarihsel banka kotasyonunu kanıtlamaz.

### Diğer büyük BIST farkları

Üç ek büyük farkın beş durumlu karşı olguları
`reports/DUZELTME-ETKI-BIST-EK-2026-09-25.json` içinde saklanır.
Yukarıdaki aynı sırayla:

| Yöntem / dönem | Eski → yeni | Saklama | Takvim | DSTKF/TRALT |
|---|---:|---:|---:|---:|
| `without_relative_breadth` geliştirme | +1,181833 → -2,239630 | -0,111670 | -0,301413 | -3,008379 |
| `without_volatility` geliştirme | +0,001984 → -2,324005 | -0,111690 | -0,300799 | -1,913500 |
| `regime_none` son bölüm | 0,000000 → -2,162804 | 0,000000 | 0,000000 | -2,162804 |

Diğer satırların ham eski/yeni farkı karşılaştırma JSON'larında durur;
bu ek onları tek tek ayrı bir nedene kesin olarak atfetmez.

## 2. Taze kotasyonla sanal alım ve stop/hedef satış kolları

Önceki `reports/YEREL-ZINCIR-2026-09-25.json` yalnız `data_block` yolunu
gösteriyordu. `scripts/verify_paper_fill_cycle.py` gerçek BIST SQL arşivini
geçici SQLite dosyasına kopyaladı. Arşiv 2026-09-22'de bittiği için yalnız
geçici kopyaya TUPRS için 2026-09-24 tarihli kontrollü bar eklendi. Sinyali
ölçmek için kontrollü %+50 sabit model tahmini ve 2026-09-25 10:30/10:35
İstanbul saatli geçerli test kotasyonları kullanıldı. `service.cycle` iki kez,
tekrar dolum olmadığını sınamak için üçüncü kez `offline=True` ile koştu.

Makbuz: `reports/YEREL-EMIR-ZINCIRI-2026-09-25.json`.

| Adım | Ana hesap sonucu |
|---|---|
| İlk kotasyon | `BEKLE / awaiting_next_quote`, dolum yok |
| Beş dakika sonraki yeni kotasyon | `AL / cost_adjusted_opportunity`, TUPRS 11 lot `BUY` |
| Üçüncü çağrı | `TUT`, ikinci dolum yok |

Alım referansı 397,20 TL ask; kayma sonrası sanal dolum fiyatı 397,3986 TL.
İşlem tutarı 4.371,38 TL, ücret 9,31 TL, kalan nakit 45.619,31 TL:
**45.619,31 + 4.371,38 + 9,31 = 50.000,00 TL**. Pozisyon 11 lot,
hesap değerlemesi 49.974,83 TL; ilk anda makas/satış maliyeti nedeniyle
başlangıç sermayesinden düşük. Ana defterde bir giriş niyeti ve tek alım var;
dört aday hesap da çalıştı. SQL arşivi ve mevcut `data/advisor` ağacının SHA-256
özetleri deneme öncesi/sonrası eşleşti. Dış istek ve banka emri yok.

Bu deney **karar → niyet → sanal dolum → nakit/lot/ücret/değerleme**
mekanizmasını doğrular. Tahmin ve bir analiz barı kontrollü olduğu için
güncel piyasa verisiyle modelin gerçekten alım önereceğini veya bankada aynı
fiyattan işlem gerçekleşeceğini göstermez. Eski çevrimdeki `data_block`
makbuzu da gerçek 2026-09-25 veri tazeliği sınırı olarak geçerlidir.

### Alımdan sonra iki ayrı sanal çıkış

2026-09-25 takip kontrolünde ilk makbuzun **yalnız BUY** içerdiği doğrulandı.
Önceden `tests/test_advisor_flow.py` içindeki sentetik tam çevrim testi bir
`SELL` görüyordu; eksik olan, bu denetimin gerçek arşiv kopyasına dayalı
makbuzunda kapanışın gösterilmesiydi.
Alım sonrası geçici hesap iki ayrı dala kopyalandı. Her dalda 10:40 için yeni
kontrollü kotasyon verilip aynı `service.cycle` tekrar çağrıldı. Stop dalında
bid, pozisyonda kayıtlı stopun %1 altına; hedef dalında kayıtlı hedefin %1
üstüne ayarlandı. Hedef dalındaki büyük fiyat sıçraması yalnız koşulu
tetikleyen sentetik girdidir, piyasa hareketi iddiası değildir.

| Dal | Karar → dolum | Dolum fiyatı | Ücret | Kapanış nakdi | Gerçekleşen sonuç |
|---|---|---:|---:|---:|---:|
| Stop | `SAT/stop` → 11 lot `SELL` | 372,251111 TL | 8,72 TL | 49.705,35 TL | −294,65 TL |
| Hedef | `SAT/target` → 11 lot `SELL` | 600,853695 TL | 14,08 TL | 52.214,62 TL | +2.214,62 TL |

İki dalda da pozisyon sıfırlandı, `equity_try` nakde eşitlendi, gerçekleşen
sonuç için `nakit = 50.000 TL + realized` sağlandı ve tamamlanan tur sayısı
bir oldu. Aynı kotasyonla tekrar çağrı ikinci `SELL` üretmedi. Tam karar,
kotasyon, masraf, hesap ve kontrol değerleri güncellenmiş
`reports/YEREL-EMIR-ZINCIRI-2026-09-25.json` dosyasında. Bu sanal referans
dolumudur; gerçek borsa emir defterini veya stop/limit emrinin gerçekleşmesini
kanıtlamaz.

## Yeniden çalıştırma ve test

Altın depo kökünden, o deponun Python ortamıyla:

```bash
PYTHONPATH=. .venv/bin/python '../BIST tahmin/scripts/audit_correction_components.py' \
  --root . --methods control sma50 window recency adaptive without_pullback \
  without_short_momentum without_volatility without_relative_breadth short \
  pullback pullback_without_shape regime_none --output /tmp/altin-etki.json
```

Altın makbuzunun aynı kopyası altın deposunda
`reports/DUZELTME-ETKI-2026-09-25.json` olarak da bulunur. BIST kökünden:

```bash
.venv/bin/python -m scripts.audit_correction_components --root . --methods control sma50 recency --output /tmp/bist-etki.json
.venv/bin/python -m scripts.audit_correction_components --root . --methods without_relative_breadth without_volatility regime_none --output /tmp/bist-etki-ek.json
.venv/bin/python -m scripts.verify_paper_fill_cycle --output /tmp/sanal-dolum.json
.venv/bin/python -m pytest -q tests/test_advisor_revision.py::test_fresh_second_quote_opens_paper_position_and_balances_ledger
.venv/bin/python -m pytest -q
git diff --check
```

Regresyon testi ilk kotasyonda beklemeyi, sonraki taze kotasyonda alımı,
stop ve hedef satışlarını, lot/nakit/ücret/gerçekleşen sonuç eşitliğini ve
tekrar çağrıda ikinci dolum olmamasını kilitler. 2026-09-25'te altın tam
suite ilk yeniden koşuda **995 geçti, 8 atlandı, 2 başarısız** verdi:
`tests/test_dokuman_tutarliligi.py:112,119` güncel `ai/STATE.md` içinde
`TAKVİM`, `SENDE KALANLAR`, `Backlog` ve `Kim` sütunu bekliyordu. STATE
biçimi düzeltilip tam suite tekrar koşuldu: **997 geçti, 8 atlandı**.
Bu iki hata ticaret mantığına ait değildi; önceki 997/8 seviyesi yeniden
sağlandı. Genişletilmiş alım/stop/hedef regresyon testi **1 geçti**; BIST tam
suite **1443 geçti**. Genişletilmiş sanal zincir makbuzu iki ayrı çalıştırmada
bayt bazında eşleşti; iki depoda da `git diff --check` temizdi.
