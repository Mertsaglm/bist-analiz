# 17–18 Kasım 2026 denetimi ve yayın özeti

- 18 Kasım paketinde işletim rehberi, regresyon testleri ve ortak manifest
  yayımlandı. GitHub CI'da 1.508 Python testi geçti, atlanan yok. Panel
  derlemesi geçti. [GitHub CI](https://github.com/Mertsaglm/bist-analiz/actions/runs/44192357422)
- BIST USDTRY 22 Ekim'de durmuştu. Tarihsel tek bozuk satır tüm batch'i
  reddediyordu. V1 ve V2 tüketicilerinde sağlam satırlar ilerler, retler
  ayrı görünür ve beklenen kapanış eksikse koşu başarısız kalır.
- Gerçek Yahoo çekimi yalnız geçici üretim kopyasında yapıldı. 18 bozuk
  kaynak tarihi ayrıldı, beş endeks/kur 17 Kasım'a ulaştı.
- Kapanış değerlemesindeki yanlış veri/saat tanısı iki ortak motorda
  düzeltildi. Bayat fiyat engeli ve dolum yasağı davranış testinde korundu.
- Yerel testte BIST 1.508 geçti, altın 1.025 geçti ve 12 atlandı. Ortak 37
  modül eşti. 17 Kasım SQL kesitinde BIST 208.982 bar ve 73 sembol, altın
  2.640 tarihti. Bütünlük kontrolü geçti.
- 26 fold ve 126 tarih offline sınavında BIST LightGBM Rank IC 0,1213,
  Ridge −0,0120. Altın ons/kur ek özellikleri MAE’yi artırdı. Üretim terfisi
  yapılmadı.

[Ayrıntılı denetim](../../docs/DENETIM-2026-11-17.md)
