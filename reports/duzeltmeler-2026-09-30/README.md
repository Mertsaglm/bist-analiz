# Düzeltme kanıtları — 2026-09-30

Bu dizindeki sonuçlar üretimden alınmış sabit arşivlerin geçici kopyalarına aittir.
Üretim defteri/SQL değiştirilmedi. Kaynak kodu ve testler repodadır; deney scriptleri
mutlak `/tmp/bist-fix-20260930` ve `/tmp/bist-audit-20260930` yollarını kullanır.
Tekrar koşarken `docs/URETIM-DENETIM-2026-09-30.md` içindeki sabit arşivleri bu
konumlara hazırlayın; scriptlerin salt-okur kaynak / geçici hedef ayrımını koruyun.
Büyük SQL, DB ve ZIP kopyaları rapor paketine dahil değildir.

- `corporate-live-refresh.json`: 73 hissenin gerçek kaynak taraması; yeni/revize kayıtlar.
- `corporate-plan-full.json`: uygulama öncesi/sonrası satırları mühürlü plan.
- `corporate-apply-copy.json`: sadece DB kopyasına uygulama, tekrar, kaynak hash'i.
- `bist-live-refresh.json`: eksik 73 kapanışın ve endekslerin telafisi.
- `kap-live-refresh.json`: bölünmüş gerçek KAP sorgusu → geçici DB yazımı.
- `*-integration.json`: iki offline çevrim, muhasebe, eski defter ve yedekten dönüş.
- `*-fixed-audit.json`: aktif/eski/aday defter, kapsül, model ve SQL denetimi.
- `sasa-quality.json`: sıfır hacim nedeniyle açık kalan veri kapısının ham girdisi.
- `mutation-results.json` ve `mutation-*.log`: eski hatalar geri konunca kırılan kilitler.
- `*-tests.log`, `*-dashboard.log`: test komutlarının ham sonuçları.

Fiyat telafisi, 30 Eylül 17:46 kesitinin beklenen 29 Eylül kapanışını sabit saatle
sınar; API çağrısı daha sonra yapılmıştır. O saatte sağlayıcıdan alınabildiği iddia
edilmez. Ekim gece yarısı sınavı da gelecekteki canlı koşu değil simülasyondur.
