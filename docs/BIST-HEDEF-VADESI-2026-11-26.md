# Öncelikli teknik iş · BIST piyasa seansı hedefi

26 Kasım 2026. `bist-market-session-target-v1` ayrı çevrimdışı adaydır.
Özellikleri ve sinyal evrenini koruyup yalnız öğrenme hedefinin bitişini
ortak piyasa takvimine bağlar. Pozitif hacimli, düzeltmeli kapanış tam
vade gününde yoksa etiket eksik kalır. Aynı hissenin sonraki barına
kaydırılmaz. 5/20/60 seans aynı kuralla ölçülür.

25 Kasım arşivinde 20 seanslık 192.958 uygun mevcut etiketin 1.160'ı
farklı tarihe düşüyordu. 1.101'inde yeni hedef gününün fiyatı bulunabildi.
Bu satırlarda mutlak hedef getiri değişimi ortalama 2,19 yüzde puan.
Yeni kuralla toplam 313 satırın tam vade fiyatı yok. Sonuç etiket
denetimidir. [Çalıştırılabilir deney](../scripts/bist_market_target_audit.py) ·
[Makbuz](../reports/historical-window-2026-11-26/bist-market-session-target-v1.json)

Sonraki deneyde aynı tarihlerde, aynı özellik/maliyet ve olgun eğitim
kesitiyle iki hedefi karşılaştır. Paydası tam fiyatla eşleşen satırları
ve kapsam dışı kalanları açıkça raporla. Veri kesiti, hedef sürümü ve
mühürlü tarih ayrı saklanır. Üretim kararı için eski mühürlerin aynı
şekilde çözülmesi, yeni hedefle uçtan uca davranış testi ve ileri kanıt
gerekir. [İlk denetim](AGIRLIK-VE-TAKVIM-DENETIMI-2026-11-26.md)
