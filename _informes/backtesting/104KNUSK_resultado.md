# Backtesting: KNU NEGRO/BLANCO ZAPA COMB DET LATERAL (familia 104KNUSK00)

> Marca: GTN | Categoria: CASUAL
> Stock actual: 70 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2023 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   - |   - |   5 |     5 |
| 2024 |  13 |  16 |   5 |  15 |  30 |  30 |  61 |  48 |  24 |  35 |  32 |  40 |   349 |
| 2025 |  31 |  33 |  21 |   8 |  12 |  27 |  20 |  15 |  14 |  22 |  18 |  10 |   231 |
| 2026 |   5 |  21 |   7 |   - |   - |   - |   - |   - |   - |   - |   - |   - |    33 |

**Total historico: 618 pares (2023-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      208 |           - |
| 2025 |       96 |      -53.8% |

---

## Factor estacional

Calculado sobre 3 anios (2023-2025). Promedio mensual = 16.2 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |        14.7 |      0.903 | Normal |
| Feb |        16.3 |      1.005 | Normal |
| Mar |         8.7 |      0.533 | Bajo |
| Abr |         7.7 |      0.472 | Bajo |
| May |        14.0 |      0.862 | Normal |
| Jun |        19.0 |      1.169 | Normal |
| Jul |        27.0 |      1.662 | Temporada alta |
| Ago |        21.0 |      1.292 | Normal |
| Sep |        12.7 |      0.779 | Bajo |
| Oct |        19.0 |      1.169 | Normal |
| Nov |        16.7 |      1.026 | Normal |
| Dic |        18.3 |      1.128 | Normal |

**Concentracion OI (abr-sep)**: 52% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      5 |       0 |                -664 | QUEBRADO |
| Feb 2024 |     16 |       0 |                -648 | QUEBRADO |
| Ene 2024 |     13 |      40 |                -675 | QUEBRADO |
| Dic 2023 |      5 |      56 |                -726 | QUEBRADO |
| Nov 2023 |      0 |       0 |                -726 | QUEBRADO |
| Oct 2023 |      0 |       0 |                -726 | QUEBRADO |
| Sep 2023 |      0 |       0 |                -726 | QUEBRADO |
| Ago 2023 |      0 |       0 |                -726 | QUEBRADO |
| Jul 2023 |      0 |       0 |                -726 | QUEBRADO |
| Jun 2023 |      0 |       0 |                -726 | QUEBRADO |
| May 2023 |      0 |       0 |                -726 | QUEBRADO |
| Abr 2023 |      0 |       0 |                -726 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 3.2 pares/mes
- vel_real v3 (desest. + disp.) = **4.5 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.47 |                 2 |   15 | -86% |
| May |      0.86 |                 4 |   30 | -87% |
| Jun |      1.17 |                 5 |   30 | -83% |
| Jul |      1.66 |                 8 |   61 | -88% |
| Ago |      1.29 |                 6 |   48 | -88% |
| Sep |      0.78 |                 4 |   24 | -85% |
| **Total** | | **28** | **208** | **-86.5%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 28 | 208 | -86.5% |
| Compras reales | - | 682 | - |
| MAPE mensual | | | **86.1%** |
| Quiebre pre-OI | | | 100% meses |

**Calidad modelo v3: POBRE (>40%)**

---

## Propuesta de mejora

1. **Quiebre cronico (100%)**: Priorizar reposicion urgente. La vel_real se calcula con pocos meses de datos.
2. **MAPE alto (86%)**: Revisar si hay redistribucion intra-temporada o si el producto tiene tendencia fuerte (CAGR).

### Timing optimo
Para OI: pedir en **primera quincena de enero** (lead time ~60 dias + colchon 15 dias).