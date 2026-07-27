# Ön Kayıt — Seviye Parametreleri Turu #2

**Durum:** ⏸ **HENÜZ KOŞULMADI.** Bu dosya, koşulacağı gün çıtanın
indirilemeyeceğini garanti etmek için ÖNCEDEN yazıldı.

**Yazıldığı an:** 2026-07-27, bağımsız denetimin `_cluster` düzeltmesinden
SONRA, herhangi bir parametre denemesinden ÖNCE.
**Dayanak:** `ai/DECISIONS.md` #009, `src/levels.py::_cluster` ölçümü.

---

## 1. Gözlem (hipotez buradan geliyor, rahatsızlıktan değil)

Denetim, `_cluster`'ın tek-bağlantı (single linkage) zinciriyle toleransın
**2.9-16.2 KATI** arasında yayılan kümeler ürettiğini ölçtü. Zarar hedefin
uydurulması değil, **R:R'ın şişmesiydi**: geniş zincir fiyatın hemen
üstündeki gerçek direnci yutup kümenin ortalamasını yukarı taşıyordu.

| ticker | fiyat | en yakın direnç (eski) | (yeni) | fark |
|---|---|---|---|---|
| TCELL | 103.70 | 116.30 | 103.92 | −3.6×ATR |
| SISE | 43.42 | 47.83 | 44.20 | −2.8×ATR |
| PETKM | 22.02 | 24.35 | 22.12 | −2.6×ATR |

Düzeltmeden sonra `min_rr_t1 ≥ 1.5` çıtasını geçen canlı isim **9 → 4**.

**Aynı koşuda ölçülen KARŞI kanıt:** replay'de tetiklenmeme oranı
**%46.4 → %35.0** düştü. Yani yeni seviyeler daha az ama daha
GERÇEKLEŞEBİLİR plan üretiyor.

## 2. Bu tur NEDEN BUGÜN KOŞULMUYOR

Üç sebep, üçü de bu projenin kendi kuralları:

1. **Plan sayısı bir kalite metriği değildir.** ADR #008: kenar iddiası yok,
   planlar "planlama geometrisi". 9 plan 4'ten iyi DEĞİLDİR; hangisinin daha
   iyi olduğunu yalnız sonuç ölçümü söyler.
2. **Eldeki tek kanıt yeni ayarın LEHİNE.** Tetiklenmeme oranı düştü.
   Kanıtın işaret ettiği yönün tersine parametre oynatmak sezgiyle karar
   vermektir.
3. **Sonucu görüp çıta indirmek yasak** (`on-kayit-revizyon-01.md` §5).
   Bugün 4 plan gördüğüm için eşiği düşürmek tam olarak o hareket.

## 3. TETİKLEYİCİ KOŞUL — bu tur ne zaman koşulur

Aşağıdakilerden **en az biri** gerçekleşmeden koşulmaz:

- **(a) Yetersiz kapsama:** Ardışık **20 işlem günü** boyunca canlı evrende
  günlük ortalama **2'den az** geçerli plan üretilirse. (Rejim `maks_pozisyon`
  zaten 2-6 arası; menü sürekli bunun altında kalıyorsa geometri katmanı
  işlevsizdir.) Ölçüm: `bist gunluk` çıktısındaki "plan var" sayısı.
- **(b) Ölçülebilir sonuç:** `bist degerlendir` çözülmüş tahmin sayısı
  **N ≥ 30**'a ulaşırsa — o zaman "hangi eşik daha iyi" sorusu ilk kez
  veriyle cevaplanabilir hale gelir.
- **(c) Evren değişimi:** Canlı evren BIST-100'e genişletilirse (kesitsel
  dağılım ve seviye yoğunluğu değişir).

## 4. Koşulunca DEĞİŞECEK olanlar — YALNIZ ÜÇÜ, BİRLİKTE

Bu üçü **bağımsız değildir**, ayrı ayrı test edilmeleri yorumlanamaz sonuç
üretir (biri gevşerken diğeri sıkışabilir):

| parametre | bugün | denenecek |
|---|---|---|
| `planlayici.min_rr_t1` | 1.5 | {1.2, 1.5, 1.8} |
| `seviyeler.kumeleme_atr_carpani` | 0.5 | {0.35, 0.5, 0.75} |
| `seviyeler.min_dokunus` | 2 | {2, 3} |

Toplam 18 hücre → **çoklu test muhasebesi zorunlu**, `bonferroni_note` basılır.

## 5. DEĞİŞMEYECEK olanlar — açıkça

- `_cluster`'ın küme-genişliği ölçütü (tek-bağlantıya GERİ DÖNÜLMEZ; o bir
  hataydı, bir parametre değil)
- Hedeflerin yalnız gerçek pivot/52h zirvesinden gelmesi
- `stop_atr_bandi` [1.5, 4.0]
- Tick ızgarası zorunluluğu
- Zaman bariyeri H=20
- Kötümser resolver kuralları (aynı gün stop kazanır vb.)

## 6. GEÇME ŞARTI — sonucu görmeden yazıldı

Birincil ölçüt **plan sayısı DEĞİL**, gerçekleşen sonuçtur:

```
Yeni parametre seti, referansa (bugünkü ayar) göre replay'de:
    tetiklenmeme oranını DÜŞÜRMELİ         (Δ ≤ −5 puan)
  VE alfa vs EW'yi KÖTÜLEŞTİRMEMELİ         (Δ ≥ −0.5pp)
  VE N ≥ 15 çözülmüş tahmin üretmeli
```

Üçü birden sağlanmazsa **değişiklik YAPILMAZ.** "Daha çok plan üretti" tek
başına geçme sebebi DEĞİLDİR — daha çok plan, daha çok gürültü de olabilir.

## 7. Başarısızlık halinde

İkinci tur YOK. Bugünkü ayar kalır ve `STATE.md` Backlog'una "ölçüldü,
geçmedi, dokunulmayacak" diye yazılır. Bu, bir sonraki oturumun aynı
rahatsızlıkla aynı turu tekrar denemesini engeller.
