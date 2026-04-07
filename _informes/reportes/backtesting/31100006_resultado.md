# Backtesting: 06-045 BLANCO/FUCSIA SANDALIA NAUTICA 2 ABROJOS CO (familia 3110000601)

> Marca: SOFT | Categoria: SANDALIA
> Stock actual: 196 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2016 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   - |   - |  14 |    14 |
| 2017 |  10 |   6 |   1 |   - |   - |   - |   - |   - |   - |   - |  14 |  25 |    56 |
| 2018 |  23 |   6 |   - |   - |   - |   - |   - |   - |   - |   5 |  38 |  56 |   124 |
| 2019 |  17 |   8 |   - |   - |   - |   - |   - |   - |   1 |  33 |  74 |  85 |   218 |
| 2020 |  21 |   5 |   - |   - |   - |   - |   - |   - |   5 |  20 | 205 | 118 |   374 |
| 2021 |  30 |  17 |   3 |   - |   - |   - |   - |   - |   6 |  32 |  77 | 135 |   300 |
| 2022 |  32 |   6 |   - |   - |   - |   - |   - |   - |   1 |  18 |  58 |  42 |   157 |
| 2023 |   2 |   - |   - |   - |   - |   - |   - |   - |   - |   2 |  91 |  72 |   167 |
| 2024 |  17 |  12 |   1 |   - |   - |   - |   - |   - |  32 |  82 |  52 |  48 |   244 |
| 2025 |  23 |  10 |   2 |   - |   - |   - |   - |   - |   8 |  28 |  14 |  55 |   140 |
| 2026 |  22 |   9 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   - |    31 |

**Total historico: 1825 pares (2016-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2019 |        1 |           - |
| 2020 |        5 |     +400.0% |
| 2021 |        6 |      +20.0% |
| 2022 |        1 |      -83.3% |
| 2024 |       32 |    +3100.0% |
| 2025 |        8 |      -75.0% |

---

## Factor estacional

Calculado sobre 4 anios (2022-2025). Promedio mensual = 14.8 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |        18.5 |      1.254 | Normal |
| Feb |         7.0 |      0.475 | Bajo |
| Mar |         0.8 |      0.051 | Valle |
| Abr |         0.0 |      0.000 | Valle |
| May |         0.0 |      0.000 | Valle |
| Jun |         0.0 |      0.000 | Valle |
| Jul |         0.0 |      0.000 | Valle |
| Ago |         0.0 |      0.000 | Valle |
| Sep |        10.2 |      0.695 | Bajo |
| Oct |        32.5 |      2.203 | **PICO** |
| Nov |        53.8 |      3.644 | **PICO** |
| Dic |        54.2 |      3.678 | **PICO** |

**Concentracion OI (abr-sep)**: 6% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      1 |       0 |                -366 | QUEBRADO |
| Feb 2024 |     12 |       0 |                -354 | QUEBRADO |
| Ene 2024 |     17 |      48 |                -385 | QUEBRADO |
| Dic 2023 |     72 |     264 |                -577 | QUEBRADO |
| Nov 2023 |     91 |     156 |                -642 | QUEBRADO |
| Oct 2023 |      2 |       0 |                -640 | QUEBRADO |
| Sep 2023 |      0 |     156 |                -796 | QUEBRADO |
| Ago 2023 |      0 |       0 |                -796 | QUEBRADO |
| Jul 2023 |      0 |       0 |                -796 | QUEBRADO |
| Jun 2023 |      0 |       0 |                -796 | QUEBRADO |
| May 2023 |      0 |       0 |                -796 | QUEBRADO |
| Abr 2023 |      0 |       0 |                -796 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 16.2 pares/mes
- vel_real v3 (desest. + disp.) = **22.4 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.00 |                 0 |    0 | - |
| May |      0.00 |                 0 |    0 | - |
| Jun |      0.00 |                 0 |    0 | - |
| Jul |      0.00 |                 0 |    0 | - |
| Ago |      0.00 |                 0 |    0 | - |
| Sep |      0.69 |                16 |   32 | -51% |
| **Total** | | **16** | **32** | **-50.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 16 | 32 | -50.0% |
| Compras reales | - | 300 | - |
| MAPE mensual | | | **51.2%** |
| Quiebre pre-OI | | | 100% meses |

**Calidad modelo v3: POBRE (>40%)**

---

## Propuesta de mejora

1. **Quiebre cronico (100%)**: Priorizar reposicion urgente. La vel_real se calcula con pocos meses de datos.
2. **MAPE alto (51%)**: Revisar si hay redistribucion intra-temporada o si el producto tiene tendencia fuerte (CAGR).
3. **Tendencia interanual**: CAGR OI = -75% (2024→2025). Producto en baja.

### Timing optimo
Para OI: pedir en **primera quincena de enero** (lead time ~60 dias + colchon 15 dias).