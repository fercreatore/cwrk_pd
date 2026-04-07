# Backtesting: 104 C/S SOQUETE KIDS T.3 (familia 5151104351)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 1 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |   - |  51 |  35 |  20 |  72 |  24 | 119 |  76 |  93 |   490 |
| 2025 |  21 | 100 |  75 |   4 |  15 |   - |   3 |   2 | 117 |  96 |  10 |  89 |   532 |
| 2026 |  35 |  43 |  19 |   - |   - |   - |   - |   - |   - |   - |   - |   - |    97 |

**Total historico: 1119 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      202 |           - |
| 2025 |      141 |      -30.2% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 42.6 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |        10.5 |      0.247 | Valle |
| Feb |        50.0 |      1.174 | Normal |
| Mar |        37.5 |      0.881 | Normal |
| Abr |         2.0 |      0.047 | Valle |
| May |        33.0 |      0.775 | Bajo |
| Jun |        17.5 |      0.411 | Bajo |
| Jul |        11.5 |      0.270 | Valle |
| Ago |        37.0 |      0.869 | Normal |
| Sep |        70.5 |      1.656 | Temporada alta |
| Oct |       107.5 |      2.524 | **PICO** |
| Nov |        43.0 |      1.010 | Normal |
| Dic |        91.0 |      2.137 | **PICO** |

**Concentracion OI (abr-sep)**: 34% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |                -920 | QUEBRADO |
| Feb 2024 |      0 |       0 |                -920 | QUEBRADO |
| Ene 2024 |      0 |       0 |                -920 | QUEBRADO |
| Dic 2023 |      0 |       0 |                -920 | QUEBRADO |
| Nov 2023 |      0 |       0 |                -920 | QUEBRADO |
| Oct 2023 |      0 |       0 |                -920 | QUEBRADO |
| Sep 2023 |      0 |       0 |                -920 | QUEBRADO |
| Ago 2023 |      0 |       0 |                -920 | QUEBRADO |
| Jul 2023 |      0 |       0 |                -920 | QUEBRADO |
| Jun 2023 |      0 |       0 |                -920 | QUEBRADO |
| May 2023 |      0 |       0 |                -920 | QUEBRADO |
| Abr 2023 |      0 |       0 |                -920 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 0.0 pares/mes
- vel_real v3 (desest. + disp.) = **0.0 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.05 |                 0 |    0 | - |
| May |      0.78 |                 0 |   51 | -100% |
| Jun |      0.41 |                 0 |   35 | -100% |
| Jul |      0.27 |                 0 |   20 | -100% |
| Ago |      0.87 |                 0 |   72 | -100% |
| Sep |      1.66 |                 0 |   24 | -100% |
| **Total** | | **0** | **202** | **-100.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 202 | -100.0% |
| Compras reales | - | 1440 | - |
| MAPE mensual | | | **100.0%** |
| Quiebre pre-OI | | | 100% meses |

**Calidad modelo v3: POBRE (>40%)**

---

## Propuesta de mejora

1. **Quiebre cronico (100%)**: Priorizar reposicion urgente. La vel_real se calcula con pocos meses de datos.
2. **MAPE alto (100%)**: Revisar si hay redistribucion intra-temporada o si el producto tiene tendencia fuerte (CAGR).

### Timing optimo
Para OI: pedir en **primera quincena de enero** (lead time ~60 dias + colchon 15 dias).