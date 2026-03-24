# Backtesting: 260PU NEGRO ZAPATO FOLCLORE CLASICO T/SEP (familia 457260PU00)

> Marca: GO by CLZ | Categoria: CASUAL
> Stock actual: 62 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2023 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   - |   - |   5 |     5 |
| 2024 |   5 |   2 |  12 |  23 |   9 |  12 |  23 |  14 |  32 |  46 |  20 |   3 |   201 |
| 2025 |  20 |   4 |  18 |  22 |  37 |  46 |  60 |  77 |  58 |  57 |  46 |   8 |   453 |
| 2026 |  21 |  20 |  29 |   - |   - |   - |   - |   - |   - |   - |   - |   - |    70 |

**Total historico: 729 pares (2023-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      113 |           - |
| 2025 |      300 |     +165.5% |

---

## Factor estacional

Calculado sobre 3 anios (2023-2025). Promedio mensual = 18.3 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |         8.3 |      0.455 | Bajo |
| Feb |         2.0 |      0.109 | Valle |
| Mar |        10.0 |      0.546 | Bajo |
| Abr |        15.0 |      0.819 | Normal |
| May |        15.3 |      0.838 | Normal |
| Jun |        19.3 |      1.056 | Normal |
| Jul |        27.7 |      1.511 | Temporada alta |
| Ago |        30.3 |      1.657 | Temporada alta |
| Sep |        30.0 |      1.639 | Temporada alta |
| Oct |        34.3 |      1.876 | Temporada alta |
| Nov |        22.0 |      1.202 | Normal |
| Dic |         5.3 |      0.291 | Valle |

**Concentracion OI (abr-sep)**: 63% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |     12 |       0 |                -625 | QUEBRADO |
| Feb 2024 |      2 |       0 |                -623 | QUEBRADO |
| Ene 2024 |      5 |      96 |                -714 | QUEBRADO |
| Dic 2023 |      5 |       0 |                -709 | QUEBRADO |
| Nov 2023 |      0 |      24 |                -733 | QUEBRADO |
| Oct 2023 |      0 |       0 |                -733 | QUEBRADO |
| Sep 2023 |      0 |       0 |                -733 | QUEBRADO |
| Ago 2023 |      0 |       0 |                -733 | QUEBRADO |
| Jul 2023 |      0 |       0 |                -733 | QUEBRADO |
| Jun 2023 |      0 |       0 |                -733 | QUEBRADO |
| May 2023 |      0 |       0 |                -733 | QUEBRADO |
| Abr 2023 |      0 |       0 |                -733 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 2.0 pares/mes
- vel_real v3 (desest. + disp.) = **2.8 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.82 |                 2 |   23 | -90% |
| May |      0.84 |                 2 |    9 | -74% |
| Jun |      1.06 |                 3 |   12 | -76% |
| Jul |      1.51 |                 4 |   23 | -82% |
| Ago |      1.66 |                 5 |   14 | -67% |
| Sep |      1.64 |                 4 |   32 | -86% |
| **Total** | | **21** | **113** | **-81.4%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 21 | 113 | -81.4% |
| Compras reales | - | 277 | - |
| MAPE mensual | | | **79.2%** |
| Quiebre pre-OI | | | 100% meses |

**Calidad modelo v3: POBRE (>40%)**

---

## Propuesta de mejora

1. **Quiebre cronico (100%)**: Priorizar reposicion urgente. La vel_real se calcula con pocos meses de datos.
2. **MAPE alto (79%)**: Revisar si hay redistribucion intra-temporada o si el producto tiene tendencia fuerte (CAGR).

### Timing optimo
Para OI: pedir en **primera quincena de enero** (lead time ~60 dias + colchon 15 dias).