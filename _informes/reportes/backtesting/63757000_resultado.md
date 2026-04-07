# Backtesting: GM NEGRO/NEGRO ZAPA DANZA ACORDONADA (familia 6375700000)

> Marca: GO by CLZ | Categoria: DANZA
> Stock actual: 6 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2017 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   - |   1 |   3 |     4 |
| 2018 |   3 |   - |   5 |   5 |   - |   3 |   1 |   3 |   3 |   - |   3 |   - |    26 |
| 2019 |   - |   - |   1 |   1 |   - |   5 |   - |   4 |   1 |   - |   2 |   1 |    15 |
| 2020 |   1 |   - |   2 |   - |   1 |   - |   - |   2 |   - |   - |   1 |   - |     7 |
| 2021 |   - |   1 |   2 |   - |   1 |   - |   3 |   - |   1 |   2 |   1 |   - |    11 |
| 2022 |   - |   - |   1 |   - |   - |   - |   1 |   2 |   - |   1 |   1 |   - |     6 |
| 2023 |   - |   - |   - |   - |  20 |  35 |  83 |  90 |  49 |  90 |  90 |  49 |   506 |
| 2024 |  21 |  25 |  52 |  80 |  63 |  60 |  62 |  97 |  84 | 109 |  75 |  43 |   771 |
| 2025 |  47 |  35 |  38 |  17 |   7 |   - |   1 |   5 |   3 |  11 |  12 |   4 |   180 |
| 2026 |   5 |   3 |   8 |   - |   - |   - |   - |   - |   - |   - |   - |   - |    16 |

**Total historico: 1542 pares (2017-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2018 |       15 |           - |
| 2019 |       11 |      -26.7% |
| 2020 |        3 |      -72.7% |
| 2021 |        5 |      +66.7% |
| 2022 |        3 |      -40.0% |
| 2023 |      277 |    +9133.3% |
| 2024 |      446 |      +61.0% |
| 2025 |       33 |      -92.6% |

---

## Factor estacional

Calculado sobre 4 anios (2022-2025). Promedio mensual = 30.5 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |        17.0 |      0.558 | Bajo |
| Feb |        15.0 |      0.492 | Bajo |
| Mar |        22.8 |      0.746 | Bajo |
| Abr |        24.2 |      0.796 | Bajo |
| May |        22.5 |      0.738 | Bajo |
| Jun |        23.8 |      0.779 | Bajo |
| Jul |        36.8 |      1.206 | Normal |
| Ago |        48.5 |      1.591 | Temporada alta |
| Sep |        34.0 |      1.116 | Normal |
| Oct |        52.8 |      1.731 | Temporada alta |
| Nov |        44.5 |      1.460 | Normal |
| Dic |        24.0 |      0.787 | Bajo |

**Concentracion OI (abr-sep)**: 52% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |     52 |       0 |                -665 | QUEBRADO |
| Feb 2024 |     25 |       0 |                -640 | QUEBRADO |
| Ene 2024 |     21 |     112 |                -731 | QUEBRADO |
| Dic 2023 |     49 |     132 |                -814 | QUEBRADO |
| Nov 2023 |     90 |     156 |                -880 | QUEBRADO |
| Oct 2023 |     90 |     224 |               -1014 | QUEBRADO |
| Sep 2023 |     49 |     146 |               -1111 | QUEBRADO |
| Ago 2023 |     90 |     220 |               -1241 | QUEBRADO |
| Jul 2023 |     83 |     140 |               -1298 | QUEBRADO |
| Jun 2023 |     35 |     202 |               -1465 | QUEBRADO |
| May 2023 |     20 |      42 |               -1487 | QUEBRADO |
| Abr 2023 |      0 |      28 |               -1515 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 50.3 pares/mes
- vel_real v3 (desest. + disp.) = **69.5 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.80 |                55 |   80 | -31% |
| May |      0.74 |                51 |   63 | -19% |
| Jun |      0.78 |                54 |   60 | -10% |
| Jul |      1.21 |                84 |   62 | +35% |
| Ago |      1.59 |               110 |   97 | +14% |
| Sep |      1.12 |                78 |   84 | -8% |
| **Total** | | **432** | **446** | **-3.1%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 432 | 446 | -3.1% |
| Compras reales | - | 1264 | - |
| MAPE mensual | | | **19.3%** |
| Quiebre pre-OI | | | 100% meses |

**Calidad modelo v3: BUENO (15-25%)**

---

## Propuesta de mejora

1. **Quiebre cronico (100%)**: Priorizar reposicion urgente. La vel_real se calcula con pocos meses de datos.
3. **Tendencia interanual**: CAGR OI = -93% (2024→2025). Producto en baja.

### Timing optimo
Para OI: pedir en **primera quincena de enero** (lead time ~60 dias + colchon 15 dias).