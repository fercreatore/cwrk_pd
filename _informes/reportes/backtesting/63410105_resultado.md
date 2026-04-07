# Backtesting: 1000105 BLANCO PLANTILLA TOALLA 3,5MM (familia 6341010501)

> Marca: AROLA - SOBRIL SA | Categoria: PLANTILLA
> Stock actual: 24 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2023 |   - |   - |   - |   - |   - |   - |   - |   - |  15 |  61 |  41 |  36 |   153 |
| 2024 |  19 |  20 |  23 |  16 |  24 |  14 |  25 |  27 |  35 |  14 |  22 |  38 |   277 |
| 2025 |  15 |  39 |  25 |  23 |  24 |  20 |  22 |   7 |  10 |   4 |   - |   4 |   193 |
| 2026 |   1 |   4 |   4 |   - |   - |   - |   - |   - |   - |   - |   - |   - |     9 |

**Total historico: 632 pares (2023-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2023 |       15 |           - |
| 2024 |      141 |     +840.0% |
| 2025 |      106 |      -24.8% |

---

## Factor estacional

Calculado sobre 3 anios (2023-2025). Promedio mensual = 17.3 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |        11.3 |      0.655 | Bajo |
| Feb |        19.7 |      1.136 | Normal |
| Mar |        16.0 |      0.925 | Normal |
| Abr |        13.0 |      0.751 | Bajo |
| May |        16.0 |      0.925 | Normal |
| Jun |        11.3 |      0.655 | Bajo |
| Jul |        15.7 |      0.905 | Normal |
| Ago |        11.3 |      0.655 | Bajo |
| Sep |        20.0 |      1.156 | Normal |
| Oct |        26.3 |      1.522 | Temporada alta |
| Nov |        21.0 |      1.213 | Normal |
| Dic |        26.0 |      1.502 | Temporada alta |

**Concentracion OI (abr-sep)**: 42% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |     23 |       0 |                  32 | OK |
| Feb 2024 |     20 |       0 |                  52 | OK |
| Ene 2024 |     19 |       0 |                  71 | OK |
| Dic 2023 |     36 |       0 |                 107 | OK |
| Nov 2023 |     41 |       0 |                 148 | OK |
| Oct 2023 |     61 |       0 |                 209 | OK |
| Sep 2023 |     15 |    1380 |               -1156 | QUEBRADO |
| Ago 2023 |      0 |       0 |               -1156 | QUEBRADO |
| Jul 2023 |      0 |       0 |               -1156 | QUEBRADO |
| Jun 2023 |      0 |       0 |               -1156 | QUEBRADO |
| May 2023 |      0 |       0 |               -1156 | QUEBRADO |
| Abr 2023 |      0 |       0 |               -1156 | QUEBRADO |

- **Meses quebrados: 6 de 12 (50%)**
- vel_aparente = 17.9 pares/mes
- vel_real v3 (desest. + disp.) = **31.0 pares/mes**
- Factor disponibilidad: 1.1

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.75 |                23 |   16 | +46% |
| May |      0.93 |                29 |   24 | +20% |
| Jun |      0.66 |                20 |   14 | +45% |
| Jul |      0.91 |                28 |   25 | +12% |
| Ago |      0.66 |                20 |   27 | -25% |
| Sep |      1.16 |                36 |   35 | +3% |
| **Total** | | **157** | **141** | **+11.3%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 157 | 141 | +11.3% |
| Compras reales | - | 120 | - |
| MAPE mensual | | | **25.0%** |
| Quiebre pre-OI | | | 50% meses |

**Calidad modelo v3: BUENO (15-25%)**

---

## Propuesta de mejora

3. **Tendencia interanual**: CAGR OI = -25% (2024→2025). Producto en baja.

### Timing optimo
Para OI: pedir en **primera quincena de enero** (lead time ~60 dias + colchon 15 dias).