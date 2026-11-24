# Yayın sonucu — 2026-10-29

> Tarihli kanıt kaydı. Sonraki kesit [24 Kasım denetiminde](DENETIM-2026-11-24.md).

Mert'in “Gerekli gördüğün her şeyi yap” onayıyla iki kod paketi üretim main'lerine
yayımlandı. Önceden kirli kullanıcı belgeleri ve eski yerel SQL yayına karışmadı.
Mevcut yerel checkout'lar reset/rebase edilmedi; uzak yayın makbuzları korunuyor.
Ücretli servis, ücretli runner veya harcama limiti açılmadı. Hesabın önceki
fatura/borcu için yetkili Billing ekranı doğrulaması yapılamadı; sıfır fatura
veya kota engelinin kendiliğinden kalkacağı garanti edilmez.

| Alan | Kanıtlanan sonuç |
|---|---|
| BIST kodu | [8d91c6f](https://github.com/Mertsaglm/bist-analiz/commit/8d91c6f17d7e0294055edf002de6eb1fc87a27a6), 40 dosya; SQL/defter değişmedi |
| Altın kodu | [9829c43](https://github.com/Mertsaglm/gold_tracking_system/commit/9829c43d972960a48a615269a8bee83b73c3180d), 21 dosya; eş zamanlı yeni kayıtlar korundu |
| Altın CI | [Testler başarılı](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/40894955558) |
| BIST CI | [Runner başlamadan başarısız](https://github.com/Mertsaglm/bist-analiz/actions/runs/40895209572); iki job'da da 0 adım, runner adı boş |
| BIST engeli | GitHub annotation: “The job was not started because recent account payments have failed or your spending limit needs to be increased.” Limit veya ödeme ayarı değiştirilmedi |
| Vercel | `dpl_2gLTnGGjtvKPPWUWUrXngcw6RSL1`, production READY; BIST 8d91c6f kaynağı; [panel](https://birikim-paneli.vercel.app/) HTTP 200, parolasız API 401 |
| Gerçek altın operasyon yedeği | [40896431707 başarılı](https://github.com/Mertsaglm/gold_tracking_system/actions/runs/40896431707), artifact 2.207.264 byte; GitHub ve yerel boş dizinde 111 dosya/defter muhasebesi geri döndü |

Operasyon yedeği tarihsel replay kapsüllerini kapsamaz; geçmiş Git'te korunur.
Bu sınır ZIP içinde de etiketlidir. Altın yedeği `data/backup/operations-2026-10-29/`
altında gitignore kapsamında yerelde saklanır. Gerçek emir, deney T0
ve bütçe değişikliği yapılmadı. Yeni kodla piyasa açık taze çevrim kabulü henüz yok;
CI ve kapalı seans koşusu bunun yerine geçmez.

## Tamamlanan veri onarımı ve depolama temizliği

Mert, bu iki ayrı somut soruya “sen tercih et” yanıtıyla karar yetkisi verdi.
Tercih güvenli ve doğrulanmış işlemleri uygulamak oldu.

- TMSN 2026-10-22 düşük fiyatı kaynaktan 50,00 olarak doğrulanıp üretime
  uygulandı: [onarım commit'i](https://github.com/Mertsaglm/bist-analiz/commit/410188284bf54a0d5b1078ddfb4637e1477df495). Yalnız düşük fiyat ve
  ingestion zamanı, tek SQL satırında değişti. Başka SQL satırı, eski karar
  veya işlem defteri değişmedi. Üretimdeki yeni Git blob'u test edilen SQL ile
  birebir eşleşiyor; dört mevcut OHLC veri testi geçti. Orijinal SQL korundu.
  Kaynağın ayrıca verdiği 18 lot hacim revizyonu uygulanmadı; normal yenilemeye
  bırakıldı. Önbellek göstergeleri ve mühürlü kararlar geriye dönük yazılmadı.
- 12 eski BIST artifact kalıcı silindi: 933.906.756 byte. En son başarılı
  336.038.973 byte bulut yedeği ve 13 yerel kopya korundu. Silmeden önce bütün
  yerel ZIP'ler yeniden hash/CRC ve GitHub digest'iyle doğrulandı. İşlemden sonra
  bulut envanteri tek korunan yedeği doğruladı. Kullanılmış dakika geri gelmedi.

İlk otomatik onay reddinden sonra bu iki özel işlem için kullanıcıdan somut
karar yetkisi geldi; o yetkiyle uygulandı. Bekleyen onay yok. Ücret/limit ayarı
değişmedi. BIST'in ödeme/harcama engeli ile taze gerçek çevrim kabulü hâlâ açık.

Makbuzlar: `reports/duzeltmeler-2026-10-29/tmsn-repair-result.json`,
`reports/duzeltmeler-2026-10-29/artifact-cleanup-result.json`,
`reports/duzeltmeler-2026-10-29/publication.json`.

## Gerçek eski tetikleme sınaması

Girdisiz eski dispatch biçimi yeni kodda [40899224420](https://github.com/Mertsaglm/bist-analiz/actions/runs/40899224420)
koşusunda `skipped` oldu; job'da runner adı boş, adım sayısı 0. Maliyet kısıtı
kaynak metniyle sınırlı kalmadı, gerçek GitHub davranışıyla doğrulandı.
Bu sınama saatlik gerçek çalışma için tükenmiş ücretsiz dakikaları geri getirmez.
