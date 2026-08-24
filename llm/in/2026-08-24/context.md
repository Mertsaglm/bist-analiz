# Analiz Paketi — 2026-08-24

> ⚠ Ölçülen kenar yok (ADR #008). Bu seviyeler planlama geometrisidir, yön iddiası değildir.

**bundle_sha:** `e320ce48ec27eb7f249c2178eaa6fd543d235ea528eadedb47bf6b144236377f` — çıktına BİREBİR kopyala.

## Piyasa rejimi: **transition**

- XU100 SMA200 farkı: 9.97%
- Genişlik (SMA50 üstü): 38.81%
- Politika: nakit %55, maks 4 pozisyon, sektör başına maks 2

- Makro: politika_faizi=37.00, tufe_bayat_tarih=2025-12-01, enf_bek_12ay=23.69, mevduat_1yil_brut=46.46, mevduat_1yil_net=39.49, usdtry=47.97, reel_net_mevduat=12.77

## Evren (18 hisse)

### AKBNK · banka
Kapanış **72.1** (3.44% günlük) · 52h 53.05–93.50
RSI 61.19 · ATR 2.32 (3.22%) · ADX 15.17 · SMA20 67.34 / SMA50 71.06 / SMA200 72.84
🛑 **AKTİF VETO** (önceki koşulardan, süresi dolmadı): `rejim_uyumsuz` (2026-08-21 → 2026-08-28, 4 işlem günü kaldı)
📌 Açık tahmin: avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), hold (bariyer None), avoid (bariyer None), avoid (bariyer None), hold (bariyer None), avoid (bariyer None), avoid (bariyer None)

| plan_id | tür | giriş | stop | T1 (R:R brüt/net) | boyut% |
|---|---|---|---|---|---|
| `AKBNK-2026-08-24-A` | dogrudan | 71.7–72.1 | 67.45 | 82.9 (2.32/2.17) | 10.0 |
| `AKBNK-2026-08-24-B` | sma20_geri_cekilme | 66.65–68.05 | 63.4 | 82.9 (3.19/3.02) | 9.51 |
| `AKBNK-2026-08-24-C` | destek_retest | 71.45–72.1 | 67.45 | 82.9 (2.32/2.17) | 10.0 |

_R:R'ın ikinci değeri %0.3 gidiş-dönüş maliyeti düşülmüş hâlidir. **Kapı brüt değere uygulanır** (ön kayıt: docs/on-kayit-seviye-02.md); net değer bilgi içindir ve gerçekte eline geçecek olan odur._

### ASELS · savunma
Kapanış **399.75** (-0.87% günlük) · 52h 168.70–450.00
RSI 60.71 · ATR 15.95 (3.99%) · ADX 21.51 · SMA20 369.82 / SMA50 372.38 / SMA200 321.97
📌 Açık tahmin: hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), accumulate (bariyer 2026-09-14), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None)

| plan_id | tür | giriş | stop | T1 (R:R brüt/net) | boyut% |
|---|---|---|---|---|---|
| `ASELS-2026-08-24-A` | dogrudan | 397.75–399.75 | 367.75 | 450.0 (1.57/1.48) | 8.12 |
| `ASELS-2026-08-24-B` | sma20_geri_cekilme | 366.0–373.75 | 341.75 | 450.0 (2.38/2.27) | 7.59 |
| `ASELS-2026-08-24-C` | destek_retest | 388.75–396.75 | 364.75 | 450.0 (1.66/1.57) | 8.06 |

_R:R'ın ikinci değeri %0.3 gidiş-dönüş maliyeti düşülmüş hâlidir. **Kapı brüt değere uygulanır** (ön kayıt: docs/on-kayit-seviye-02.md); net değer bilgi içindir ve gerçekte eline geçecek olan odur._

### ASTOR · elektrik_ekipman
Kapanış **341.25** (1.64% günlük) · 52h 88.20–385.75
RSI 59.80 · ATR 16.72 (4.90%) · ADX 17.73 · SMA20 314.66 / SMA50 306.49 / SMA200 214.24
🛑 **AKTİF VETO** (önceki koşulardan, süresi dolmadı): `rejim_uyumsuz` (2026-08-21 → 2026-08-28, 4 işlem günü kaldı)
📌 Açık tahmin: avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), hold (bariyer None), avoid (bariyer None), avoid (bariyer None), hold (bariyer None), avoid (bariyer None), avoid (bariyer None)

| plan_id | tür | giriş | stop | T1 (R:R brüt/net) | boyut% |
|---|---|---|---|---|---|
| `ASTOR-2026-08-24-A` | sma20_geri_cekilme | 311.5–318.0 | 284.5 | 385.75 (2.02/1.94) | 3.09 |
| `ASTOR-2026-08-24-B` | destek_retest | 309.5–316.0 | 282.5 | 385.75 (2.08/2.0) | 3.07 |

_R:R'ın ikinci değeri %0.3 gidiş-dönüş maliyeti düşülmüş hâlidir. **Kapı brüt değere uygulanır** (ön kayıt: docs/on-kayit-seviye-02.md); net değer bilgi içindir ve gerçekte eline geçecek olan odur._

### BIMAS · perakende
Kapanış **412.25** (-1.02% günlük) · 52h 241.62–425.00
RSI 61.76 · ATR 12.01 (2.91%) · ADX 24.05 · SMA20 390.21 / SMA50 383.78 / SMA200 342.63
📌 Açık tahmin: buy (bariyer 2026-08-26), buy (bariyer None), buy (bariyer None), buy (bariyer 2026-09-01), hold (bariyer None), hold (bariyer None), hold (bariyer None), buy (bariyer None), hold (bariyer None), hold (bariyer None), buy (bariyer 2026-09-14), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None)
_Plan yok: üstteki seviyelerin hepsi hedef eşiğinin içinde (gereken ≥1.5 ATR): 425.00 (+1.06 ATR)_

### EKGYO · gyo
Kapanış **20.72** (6.53% günlük) · 52h 17.47–27.12
RSI 68.32 · ATR 0.64 (3.10%) · ADX 25.34 · SMA20 18.51 / SMA50 19.84 / SMA200 20.89
🛑 **AKTİF VETO** (önceki koşulardan, süresi dolmadı): `rejim_uyumsuz` (2026-08-21 → 2026-08-28, 4 işlem günü kaldı)
📌 Açık tahmin: avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), hold (bariyer None), avoid (bariyer None), avoid (bariyer None)
_Plan yok: 2 giriş bandı denendi; brüt R:R hiçbir kombinasyonda ≥1.5 olmadı (stop bandı geçti)_

### ENKAI · insaat
Kapanış **82.95** (-0.36% günlük) · 52h 65.55–114.30
RSI 40.39 · ATR 2.48 (2.99%) · ADX 32.08 · SMA20 85.34 / SMA50 88.89 / SMA200 90.41
📌 Açık tahmin: hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None)
_Plan yok: 2 giriş bandı denendi; brüt R:R hiçbir kombinasyonda ≥1.5 olmadı (stop bandı geçti)_

### EREGL · demir_celik
Kapanış **38.18** (0.10% günlük) · 52h 23.46–45.10
RSI 42.52 · ATR 1.30 (3.40%) · ADX 22.63 · SMA20 39.55 / SMA50 40.55 / SMA200 32.23
🛑 **AKTİF VETO** (önceki koşulardan, süresi dolmadı): `rejim_uyumsuz` (2026-08-21 → 2026-08-28, 4 işlem günü kaldı)
📌 Açık tahmin: accumulate (bariyer None), accumulate (bariyer None), accumulate (bariyer None), accumulate (bariyer None), hold (bariyer None), accumulate (bariyer 2026-09-07), accumulate (bariyer 2026-09-08), accumulate (bariyer 2026-09-09), accumulate (bariyer 2026-09-10), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), avoid (bariyer None), avoid (bariyer None)

| plan_id | tür | giriş | stop | T1 (R:R brüt/net) | boyut% |
|---|---|---|---|---|---|
| `EREGL-2026-08-24-A` | destek_retest | 34.56–35.28 | 32.68 | 41.04 (2.22/2.09) | 8.82 |

_R:R'ın ikinci değeri %0.3 gidiş-dönüş maliyeti düşülmüş hâlidir. **Kapı brüt değere uygulanır** (ön kayıt: docs/on-kayit-seviye-02.md); net değer bilgi içindir ve gerçekte eline geçecek olan odur._

### EUPWR · elektrik_ekipman
Kapanış **93.2** (0.22% günlük) · 52h 25.50–108.60
RSI 52.48 · ATR 4.23 (4.54%) · ADX 23.36 · SMA20 91.20 / SMA50 90.61 / SMA200 54.71
🛑 **AKTİF VETO** (önceki koşulardan, süresi dolmadı): `rejim_uyumsuz` (2026-08-21 → 2026-08-28, 4 işlem günü kaldı)
📌 Açık tahmin: hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), avoid (bariyer None), avoid (bariyer None)

| plan_id | tür | giriş | stop | T1 (R:R brüt/net) | boyut% |
|---|---|---|---|---|---|
| `EUPWR-2026-08-24-A` | dogrudan | 92.7–93.2 | 84.7 | 107.9 (1.73/1.64) | 3.56 |
| `EUPWR-2026-08-24-B` | sma20_geri_cekilme | 90.25–92.15 | 83.65 | 107.9 (1.85/1.76) | 3.52 |
| `EUPWR-2026-08-24-C` | destek_retest | 87.65–89.45 | 80.95 | 107.9 (2.17/2.07) | 3.42 |

_R:R'ın ikinci değeri %0.3 gidiş-dönüş maliyeti düşülmüş hâlidir. **Kapı brüt değere uygulanır** (ön kayıt: docs/on-kayit-seviye-02.md); net değer bilgi içindir ve gerçekte eline geçecek olan odur._

### FROTO · otomotiv
Kapanış **80.1** (-0.12% günlük) · 52h 75.05–135.40
RSI 49.77 · ATR 1.94 (2.43%) · ADX 28.13 · SMA20 78.96 / SMA50 82.27 / SMA200 96.66
🛑 **AKTİF VETO** (önceki koşulardan, süresi dolmadı): `rejim_uyumsuz` (2026-08-21 → 2026-08-28, 4 işlem günü kaldı)
📌 Açık tahmin: avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), hold (bariyer None), avoid (bariyer None), avoid (bariyer None)

| plan_id | tür | giriş | stop | T1 (R:R brüt/net) | boyut% |
|---|---|---|---|---|---|
| `FROTO-2026-08-24-A` | dogrudan | 79.65–80.1 | 76.2 | 86.05 (1.53/1.38) | 10.0 |
| `FROTO-2026-08-24-B` | sma20_geri_cekilme | 78.15–79.75 | 75.85 | 86.05 (1.62/1.46) | 10.0 |
| `FROTO-2026-08-24-C` | destek_retest | 78.75–80.1 | 76.2 | 86.05 (1.53/1.38) | 10.0 |

_R:R'ın ikinci değeri %0.3 gidiş-dönüş maliyeti düşülmüş hâlidir. **Kapı brüt değere uygulanır** (ön kayıt: docs/on-kayit-seviye-02.md); net değer bilgi içindir ve gerçekte eline geçecek olan odur._

### GARAN · banka
Kapanış **131.6** (1.31% günlük) · 52h 115.40–169.70
RSI 54.95 · ATR 3.58 (2.72%) · ADX 14.73 · SMA20 128.51 / SMA50 131.76 / SMA200 138.08
📌 Açık tahmin: avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), hold (bariyer None), avoid (bariyer None), hold (bariyer None)
_Plan yok: 3 giriş bandı denendi; brüt R:R hiçbir kombinasyonda ≥1.5 olmadı (stop bandı geçti)_

### KCHOL · holding
Kapanış **218.8** (-1.62% günlük) · 52h 146.00–229.10
RSI 64.59 · ATR 6.41 (2.93%) · ADX 26.61 · SMA20 203.97 / SMA50 198.47 / SMA200 192.70
🛑 **AKTİF VETO** (önceki koşulardan, süresi dolmadı): `rejim_uyumsuz` (2026-08-20 → 2026-08-27, 3 işlem günü kaldı)
📌 Açık tahmin: hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), avoid (bariyer None), hold (bariyer None)

| plan_id | tür | giriş | stop | T1 (R:R brüt/net) | boyut% |
|---|---|---|---|---|---|
| `KCHOL-2026-08-24-A` | sma20_geri_cekilme | 201.9–206.1 | 193.2 | 229.2 (1.79/1.66) | 10.0 |

_R:R'ın ikinci değeri %0.3 gidiş-dönüş maliyeti düşülmüş hâlidir. **Kapı brüt değere uygulanır** (ön kayıt: docs/on-kayit-seviye-02.md); net değer bilgi içindir ve gerçekte eline geçecek olan odur._

### KRDMD · demir_celik
Kapanış **45.2** (0.49% günlük) · 52h 23.50–47.00
RSI 60.92 · ATR 1.94 (4.29%) · ADX 20.96 · SMA20 42.35 / SMA50 41.15 / SMA200 33.80
🛑 **AKTİF VETO** (önceki koşulardan, süresi dolmadı): `rejim_uyumsuz` (2026-08-19 → 2026-08-26, 2 işlem günü kaldı)
📌 Açık tahmin: buy (bariyer 2026-08-27), buy (bariyer 2026-08-31), buy (bariyer 2026-09-01), buy (bariyer 2026-09-07), buy (bariyer 2026-09-08), buy (bariyer 2026-09-09), buy (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None)
_Plan yok: üstteki seviyelerin hepsi hedef eşiğinin içinde (gereken ≥1.5 ATR): 47.00 (+0.93 ATR)_

### PETKM · kimya
Kapanış **20.8** (1.07% günlük) · 52h 16.12–28.06
RSI 58.84 · ATR 0.74 (3.56%) · ADX 15.61 · SMA20 19.49 / SMA50 19.82 / SMA200 19.45
🛑 **AKTİF VETO** (önceki koşulardan, süresi dolmadı): `rejim_uyumsuz` (2026-08-21 → 2026-08-28, 4 işlem günü kaldı)
📌 Açık tahmin: hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), avoid (bariyer None)

| plan_id | tür | giriş | stop | T1 (R:R brüt/net) | boyut% |
|---|---|---|---|---|---|
| `PETKM-2026-08-24-A` | sma20_geri_cekilme | 19.29–19.69 | 18.2 | 22.02 (1.56/1.47) | 8.59 |

_R:R'ın ikinci değeri %0.3 gidiş-dönüş maliyeti düşülmüş hâlidir. **Kapı brüt değere uygulanır** (ön kayıt: docs/on-kayit-seviye-02.md); net değer bilgi içindir ve gerçekte eline geçecek olan odur._

### SISE · cam_sanayi
Kapanış **39.74** (-0.40% günlük) · 52h 32.44–54.10
RSI 39.94 · ATR 1.18 (2.97%) · ADX 20.72 · SMA20 40.96 / SMA50 43.01 / SMA200 42.97
📌 Açık tahmin: hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None)
_Plan yok: 2 giriş bandı denendi; brüt R:R hiçbir kombinasyonda ≥1.5 olmadı (stop bandı geçti)_

### TAVHL · ulasim
Kapanış **276.0** (-1.34% günlük) · 52h 217.60–369.00
RSI 50.65 · ATR 8.61 (3.12%) · ADX 7.58 · SMA20 276.36 / SMA50 276.99 / SMA200 294.47
📌 Açık tahmin: avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), hold (bariyer None), avoid (bariyer None), hold (bariyer None)
_Plan yok: 2 giriş bandı denendi; brüt R:R hiçbir kombinasyonda ≥1.5 olmadı (stop bandı geçti)_

### TCELL · telekom
Kapanış **103.1** (-1.15% günlük) · 52h 87.05–129.60
RSI 45.29 · ATR 2.94 (2.85%) · ADX 19.33 · SMA20 103.62 / SMA50 107.17 / SMA200 107.53
📌 Açık tahmin: avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), avoid (bariyer None), hold (bariyer None), avoid (bariyer None), hold (bariyer None)
_Plan yok: 2 giriş bandı denendi; brüt R:R hiçbir kombinasyonda ≥1.5 olmadı (stop bandı geçti)_

### THYAO · ulasim
Kapanış **300.5** (-0.17% günlük) · 52h 262.75–355.50
RSI 39.07 · ATR 7.31 (2.43%) · ADX 17.03 · SMA20 307.91 / SMA50 320.20 / SMA200 301.60
🛑 **AKTİF VETO** (önceki koşulardan, süresi dolmadı): `rejim_uyumsuz` (2026-08-21 → 2026-08-28, 4 işlem günü kaldı)
📌 Açık tahmin: hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), accumulate (bariyer 2026-09-17), avoid (bariyer None)

| plan_id | tür | giriş | stop | T1 (R:R brüt/net) | boyut% |
|---|---|---|---|---|---|
| `THYAO-2026-08-24-A` | dogrudan | 298.75–300.5 | 285.75 | 324.5 (1.63/1.48) | 10.0 |
| `THYAO-2026-08-24-B` | destek_retest | 295.5–300.5 | 285.75 | 324.5 (1.63/1.48) | 10.0 |

_R:R'ın ikinci değeri %0.3 gidiş-dönüş maliyeti düşülmüş hâlidir. **Kapı brüt değere uygulanır** (ön kayıt: docs/on-kayit-seviye-02.md); net değer bilgi içindir ve gerçekte eline geçecek olan odur._

### TUPRS · rafineri
Kapanış **400.5** (-1.54% günlük) · 52h 163.30–407.50
RSI 80.20 · ATR 13.57 (3.39%) · ADX 59.61 · SMA20 339.01 / SMA50 288.64 / SMA200 242.85
🛑 **AKTİF VETO** (önceki koşulardan, süresi dolmadı): `tez_zayif` (2026-08-19 → 2026-08-26, 2 işlem günü kaldı)
📌 Açık tahmin: hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None), hold (bariyer None)
_Plan yok: üstteki seviyelerin hepsi hedef eşiğinin içinde (gereken ≥1.5 ATR): 407.50 (+0.52 ATR)_
