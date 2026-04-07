# Backtesting: 105 C/S SOQUETE KIDS T.5 (familia 5151105551)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 41 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |   - | 115 |  82 |  12 |  17 |   5 |   7 |   2 |   9 |   249 |
| 2025 |  18 | 299 | 133 |   5 |  14 |   - |   1 |   3 | 141 | 126 | 160 | 160 |  1060 |
| 2026 |  65 |  15 |   7 |   - |   - |   - |   - |   - |   - |   - |   - |   - |    87 |

**Total historico: 1396 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      231 |           - |
| 2025 |      164 |      -29.0% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 54.5 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |         9.0 |      0.165 | Valle |
| Feb |       149.5 |      2.741 | **PICO** |
| Mar |        66.5 |      1.219 | Normal |
| Abr |         2.5 |      0.046 | Valle |
| May |        64.5 |      1.183 | Normal |
| Jun |        41.0 |      0.752 | Bajo |
| Jul |         6.5 |      0.119 | Valle |
| Ago |        10.0 |      0.183 | Valle |
| Sep |        73.0 |      1.338 | Normal |
| Oct |        66.5 |      1.219 | Normal |
| Nov |        81.0 |      1.485 | Normal |
| Dic |        84.5 |      1.549 | Temporada alta |

**Concentracion OI (abr-sep)**: 30% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |               -1203 | QUEBRADO |
| Feb 2024 |      0 |       0 |               -1203 | QUEBRADO |
| Ene 2024 |      0 |       0 |               -1203 | QUEBRADO |
| Dic 2023 |      0 |       0 |               -1203 | QUEBRADO |
| Nov 2023 |      0 |       0 |               -1203 | QUEBRADO |
| Oct 2023 |      0 |       0 |               -1203 | QUEBRADO |
| Sep 2023 |      0 |       0 |               -1203 | QUEBRADO |
| Ago 2023 |      0 |       0 |               -1203 | QUEBRADO |
| Jul 2023 |      0 |       0 |               -1203 | QUEBRADO |
| Jun 2023 |      0 |       0 |               -1203 | QUEBRADO |
| May 2023 |      0 |       0 |               -1203 | QUEBRADO |
| Abr 2023 |      0 |       0 |               -1203 | QUEBRADO |

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
| May |      1.18 |                 0 |  115 | -100% |
| Jun |      0.75 |                 0 |   82 | -100% |
| Jul |      0.12 |                 0 |   12 | -100% |
| Ago |      0.18 |                 0 |   17 | -100% |
| Sep |      1.34 |                 0 |    5 | -100% |
| **Total** | | **0** | **231** | **-100.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 231 | -100.0% |
| Compras reales | - | 480 | - |
| MAPE mensual | | | **100.0%** |
| Quiebre pre-OI | | | 100% meses |

**Calidad modelo v3: POBRE (>40%)**

---

## Propuesta de mejora

1. **Quiebre cronico (100%)**: Priorizar reposicion urgente. La vel_real se calcula con pocos meses de datos.
2. **MAPE alto (100%)**: Revisar si hay redistribucion intra-temporada o si el producto tiene tendencia fuerte (CAGR).

### Timing optimo
Para OI: pedir en **primera quincena de enero** (lead time ~60 dias + colchon 15 dias).