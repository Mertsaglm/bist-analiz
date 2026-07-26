# Analiz Paketi — 2026-07-24

> ⚠ Ölçülen kenar yok (ADR #008). Bu seviyeler planlama geometrisidir, yön iddiası değildir.

**bundle_sha:** `fcb8d139b370bb32c8dc67223dccee703e96bd70e01dbc9c1a237bc2a653f45c` — çıktına BİREBİR kopyala.

## Piyasa rejimi: **risk-off**

- XU100 SMA200 farkı: 9.70%
- Genişlik (SMA50 üstü): 31.25%
- Politika: nakit %90, maks 2 pozisyon, sektör başına maks 2

- Makro: **veri yok** (EVDS anahtarı girilmemiş) — bu satırlar uydurulmaz, gizlenir.

## Evren (18 hisse)

### AKBNK · banka
Kapanış **67.6** (0.82% günlük) · 52h 53.05–93.50
RSI 38.72 · ATR 2.13 (3.16%) · ADX 25.50 · SMA20 71.21 / SMA50 71.25 / SMA200 71.85
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### ASELS · savunma
Kapanış **380.25** (1.06% günlük) · 52h 167.00–450.00
RSI 53.70 · ATR 16.57 (4.36%) · ADX 15.91 · SMA20 367.80 / SMA50 381.45 / SMA200 304.99

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `ASELS-2026-07-24-A` | sma20_geri_cekilme | 364.0–371.5 | 346.0 | 412.0 (1.59) | 5.83 |
| `ASELS-2026-07-24-B` | destek_retest | 346.0–353.25 | 320.0 | 412.0 (1.77) | 4.25 |

### ASTOR · elektrik_ekipman
Kapanış **297.0** (-3.26% günlük) · 52h 88.20–385.75
RSI 47.65 · ATR 17.54 (5.91%) · ADX 12.77 · SMA20 303.75 / SMA50 310.42 / SMA200 191.23
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### BIMAS · perakende
Kapanış **380.25** (-2.62% günlük) · 52h 241.62–425.00
RSI 49.42 · ATR 12.30 (3.23%) · ADX 20.26 · SMA20 377.64 / SMA50 381.93 / SMA200 330.37
_Plan yok: 3 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### EKGYO · gyo
Kapanış **18.62** (-2.87% günlük) · 52h 17.62–27.12
RSI 33.27 · ATR 0.69 (3.72%) · ADX 14.08 · SMA20 20.48 / SMA50 20.36 / SMA200 20.99
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### ENKAI · insaat
Kapanış **88.8** (-1.28% günlük) · 52h 65.55–114.30
RSI 41.62 · ATR 2.40 (2.70%) · ADX 21.63 · SMA20 90.78 / SMA50 94.12 / SMA200 89.06
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### EREGL · demir_celik
Kapanış **43.28** (-2.08% günlük) · 52h 23.46–45.10
RSI 58.24 · ATR 1.65 (3.81%) · ADX 26.98 · SMA20 41.65 / SMA50 40.37 / SMA200 30.96
_Plan yok: 3 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### EUPWR · elektrik_ekipman
Kapanış **100.4** (2.08% günlük) · 52h 25.50–108.60
RSI 61.31 · ATR 5.91 (5.89%) · ADX 30.30 · SMA20 89.45 / SMA50 84.56 / SMA200 47.93

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `EUPWR-2026-07-24-A` | sma20_geri_cekilme | 88.55–90.35 | 78.5 | 108.6 (1.54) | 1.52 |

### FROTO · otomotiv
Kapanış **79.0** (-0.50% günlük) · 52h 78.45–135.40
RSI 34.17 · ATR 2.04 (2.58%) · ADX 40.61 · SMA20 82.58 / SMA50 86.25 / SMA200 98.45
_Plan yok: 1 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### GARAN · banka
Kapanış **126.0** (0.80% günlük) · 52h 115.40–169.70
RSI 39.24 · ATR 3.39 (2.69%) · ADX 20.48 · SMA20 130.92 / SMA50 131.84 / SMA200 138.02
_Plan yok: 2 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### KCHOL · holding
Kapanış **197.6** (-0.30% günlük) · 52h 146.00–229.10
RSI 53.37 · ATR 5.18 (2.62%) · ADX 21.31 · SMA20 194.14 / SMA50 193.96 / SMA200 188.57
_Plan yok: 3 giriş bandı denendi; hiçbiri stop∈[1.5, 4.0]×ATR + R:R≥1.5 kurallarını birlikte sağlayamadı_

### KRDMD · demir_celik
Kapanış **42.2** (0.09% günlük) · 52h 23.50–47.00
RSI 56.72 · ATR 1.80 (4.27%) · ADX 19.16 · SMA20 40.22 / SMA50 40.34 / SMA200 32.15

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `KRDMD-2026-07-24-A` | sma20_geri_cekilme | 39.8–40.64 | 37.02 | 47.0 (1.76) | 4.49 |

### PETKM · kimya
Kapanış **22.02** (-2.39% günlük) · 52h 16.12–28.06
RSI 59.54 · ATR 0.86 (3.92%) · ADX 26.96 · SMA20 20.10 / SMA50 21.29 / SMA200 19.31

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `PETKM-2026-07-24-A` | sma20_geri_cekilme | 19.9–20.32 | 18.59 | 24.36 (2.34) | 4.7 |

### SISE · cam_sanayi
Kapanış **43.42** (-0.60% günlük) · 52h 32.44–54.10
RSI 45.89 · ATR 1.31 (3.01%) · ADX 16.34 · SMA20 43.83 / SMA50 45.27 / SMA200 42.34

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `SISE-2026-07-24-A` | dogrudan | 43.2–43.42 | 40.8 | 47.84 (1.69) | 6.63 |
| `SISE-2026-07-24-B` | destek_retest | 40.84–41.68 | 39.06 | 47.84 (2.35) | 6.36 |

### TAVHL · ulasim
Kapanış **259.5** (0.10% günlük) · 52h 217.60–369.00
RSI 42.08 · ATR 9.46 (3.65%) · ADX 15.18 · SMA20 271.01 / SMA50 270.62 / SMA200 291.11

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `TAVHL-2026-07-24-A` | destek_retest | 235.5–240.4 | 221.4 | 270.25 (1.57) | 5.06 |

### TCELL · telekom
Kapanış **103.7** (-1.24% günlük) · 52h 87.05–129.60
RSI 39.87 · ATR 3.43 (3.31%) · ADX 14.63 · SMA20 108.35 / SMA50 109.18 / SMA200 106.94

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `TCELL-2026-07-24-A` | dogrudan | 103.1–103.7 | 96.8 | 116.3 (1.83) | 6.01 |
| `TCELL-2026-07-24-B` | destek_retest | 97.2–99.2 | 92.3 | 116.3 (2.48) | 5.75 |

### THYAO · ulasim
Kapanış **312.0** (-0.24% günlük) · 52h 262.75–355.50
RSI 40.85 · ATR 8.84 (2.83%) · ADX 19.94 · SMA20 330.09 / SMA50 315.59 / SMA200 300.56

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `THYAO-2026-07-24-A` | destek_retest | 286.75–292.75 | 275.0 | 324.75 (1.8) | 6.6 |

### TUPRS · rafineri
Kapanış **304.25** (-3.26% günlük) · 52h 159.20–320.25
RSI 74.50 · ATR 9.41 (3.09%) · ADX 50.97 · SMA20 267.37 / SMA50 249.50 / SMA200 226.81

| plan_id | tür | giriş | stop | T1 (R:R) | boyut% |
|---|---|---|---|---|---|
| `TUPRS-2026-07-24-A` | destek_retest | 277.25–283.0 | 264.0 | 320.25 (1.96) | 5.96 |
