# 2026-09-30 denetim kanıt paketi

Ana rapor: `docs/URETIM-DENETIM-2026-09-30.md`.
Bu paket özel proje verisinden üretilmiştir; dışarıya gönderilmedi.

## Sabit kaynaklar

- BIST: `Mertsaglm/bist-analiz@59e26644d61b15a2a7b3d9ed175aa2f3683fcfbd`
- Altın: `Mertsaglm/gold_tracking_system@d4db91e052dc9e68630fb0b950bf74062b29d213`

GitHub tarball'ları geçici dizine indirildi; üretim kaynakları değiştirilmedi.
JSON'lardaki `/tmp/bist-audit-20260930/` yolları deneyin yapıldığı konumu kaydeder;
bu büyük arşivler bu kanıt paketinin parçası değildir. Yeniden çalışma için aynı
SHA'lardan arşiv edinilmeli. Tekrar üretim gününde dış sağlayıcı yanıtı değişebilir;
`provider-probe.json` yalnız 2026-09-30 gözlemidir.

## İçerik

- `findings-reproduction.json`, `corporate-counterfactual.json`: eksik BIMAS olayı,
  saklanan/yeniden çözülen sonuç; ilk dosyada tazelik ve 1 Ekim bellek senaryosu da var.
- `bist-inventory.json`, `gold-inventory.json`: tablo envanteri, bağımsız muhasebe,
  tüm defterler, günlük çevrim kapsamı, tüm kapsül mühürleri.
- `bist-runtime.json`, `gold-runtime.json`: seçilmiş replay'ler, model yeniden fit,
  tekrar cycle, geçici backup/restore ve gece yarısı kapanış deneyi.
- `workflow-runs.json`: incelenen sabit koşu listesi; tüm GitHub metadata'sı değil.
- `workflow-failures.json`: sekiz başarısız portföy koşusunun ilgili log satırları.
- `daily-evidence.txt`: KAP tavanı için günlük log kesiti.
- `old-audit.log`: yeni hesapta mevcut audit komutunun hatası.
- `*-tests.log`, `bist-gitignore-recheck.log`, `dashboard-checks.log`: test kayıtları.
- `provider-probe.json`: üretim SQL'ini değiştirmeden alınan sağlayıcı cevabı.
- `manifest.json`: dosya SHA-256 listesi; üretim olay defterinin mührü değildir.

## Çalıştırma

Python ortamında projenin runtime/test bağımlılıkları bulunmalı. Kapsül replay'i
mühürlenmiş proje kodunu çalıştırır; yalnız bu incelenmiş sabit arşivleri kullanın.
`PY` mutlak Python yolu, `EVIDENCE` bu klasörün mutlak yolu, `ARCHIVE` açılmış sabit
kaynak dizini, `OUTPUT` yeni/geçici çıktı dizini olarak seçilir. BIST ve altın için
ilgili arşivi ayrı kullanın. İncelenen katsayı runtime'ı numpy 2.5.1/pandas 2.3.3.

```sh
cd "$ARCHIVE"
"$PY" "$EVIDENCE/inspect_archive.py" "$ARCHIVE" "$OUTPUT"
"$PY" "$EVIDENCE/verify_runtime.py" "$ARCHIVE" "$OUTPUT"
```

İlk script SQL dump'ını geçici restore eder; bağımsız muhasebeyi ve kapsül
hash'lerini denetler. İkinci script ilk çıktının `*-inventory.json` dosyasını
okur; seçilmiş kapsülleri yeniden çalıştırır, modeli fit eder, ağ kapalı tam
cycle'ları ve backup/restore'u ayrı geçici dizinlerde sınar. Sonraki run'larda
geçici yollar/zaman damgaları doğal olarak farklı olabilir; karşılaştırılan
şey hesap, model toleransı, karar ve hash tutarlılığıdır.

Yalnız BIST için küçük davranış kanıtı:

```sh
cd "$ARCHIVE"
"$PY" "$EVIDENCE/reproduce_findings.py" "$ARCHIVE"
```

Bu script mevcut resolver'ı kullanır; üretim SQL'ini veya defteri kaydetmez.
BIMAS sonucu önceden düzeltilmiş daha yeni bir arşivde eski-hata assertion'ı
geçmez; bu yüzden sabit SHA önemlidir. 1 Ekim deneyi yalnız mevcut config ve
arşivle bellek simülasyonudur; gerçek gelecek koşu veya banka ekstresi değildir.

## Test sınırları

BIST tarball tam suite logu `.git` eksikliğinden tek hata içerir. Geçici arşive
Git metadata'sı eklenerek yalnız o test tekrar koşuldu ve geçti; tekrar logu
ayrıdır. Altın tarball suite'inde 40 test CLI/Git ortamı nedeniyle atlandı;
atlananlar geçilmiş sayılmadı. Dashboard ayrıca test ve syntax kontrolünden geçti.
Tüm kapsüller hash açısından sınandı; yalnız 21 örnek tam replay edildi.
