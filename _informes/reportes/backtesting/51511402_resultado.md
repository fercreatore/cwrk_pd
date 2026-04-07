# Backtesting: 402E MEDIA 1/3 HOMBRE ESTAMPA (familia 5151140251)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 221 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |   - |  44 |  59 |  25 |  97 |  14 |  87 |  30 |  20 |   376 |
| 2025 |  27 |  20 |   5 |  21 | 204 |  32 |  89 | 141 | 136 |  72 |  35 |  10 |   792 |
| 2026 |  13 |   2 |  38 |   - |   - |   - |   - |   - |   - |   - |   - |   - |    53 |

**Total historico: 1221 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      239 |           - |
| 2025 |      623 |     +160.7% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 48.7 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |        13.5 |      0.277 | Valle |
| Feb |        10.0 |      0.205 | Valle |
| Mar |         2.5 |      0.051 | Valle |
| Abr |        10.5 |      0.216 | Valle |
| May |       124.0 |      2.548 | **PICO** |
| Jun |        45.5 |      0.935 | Normal |
| Jul |        57.0 |      1.171 | Normal |
| Ago |       119.0 |      2.445 | **PICO** |
| Sep |        75.0 |      1.541 | Temporada alta |
| Oct |        79.5 |      1.634 | Temporada alta |
| Nov |        32.5 |      0.668 | Bajo |
| Dic |        15.0 |      0.308 | Bajo |

**Concentracion OI (abr-sep)**: 74% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |               -1438 | QUEBRADO |
| Feb 2024 |      0 |       0 |               -1438 | QUEBRADO |
| Ene 2024 |      0 |       0 |               -1438 | QUEBRADO |
| Dic 2023 |      0 |       0 |               -1438 | QUEBRADO |
| Nov 2023 |      0 |       0 |               -1438 | QUEBRADO |
| Oct 2023 |      0 |       0 |               -1438 | QUEBRADO |
| Sep 2023 |      0 |       0 |               -1438 | QUEBRADO |
| Ago 2023 |      0 |       0 |               -1438 | QUEBRADO |
| Jul 2023 |      0 |       0 |               -1438 | QUEBRADO |
| Jun 2023 |      0 |       0 |               -1438 | QUEBRADO |
| May 2023 |      0 |       0 |               -1438 | QUEBRADO |
| Abr 2023 |      0 |       0 |               -1438 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 0.0 pares/mes
- vel_real v3 (desest. + disp.) = **0.0 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.22 |                 0 |    0 | - |
| May |      2.55 |                 0 |   44 | -100% |
| Jun |      0.94 |                 0 |   59 | -100% |
| Jul |      1.17 |                 0 |   25 | -100% |
| Ago |      2.44 |                 0 |   97 | -100% |
| Sep |      1.54 |                 0 |   14 | -100% |
| **Total** | | **0** | **239** | **-100.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 239 | -100.0% |
| Compras reales | - | 960 | - |
| MAPE mensual | | | **100.0%** |
| Quiebre pre-OI | | | 100% meses |

**Calidad modelo v3: POBRE (>40%)**

---

## Propuesta de mejora

1. **Quiebre cronico (100%)**: Priorizar reposicion urgente. La vel_real se calcula con pocos meses de datos.
2. **MAPE alto (100%)**: Revisar si hay redistribucion intra-temporada o si el producto tiene tendencia fuerte (CAGR).

### Timing optimo
Para OI: pedir en **primera quincena de enero** (lead time ~60 dias + colchon 15 dias).