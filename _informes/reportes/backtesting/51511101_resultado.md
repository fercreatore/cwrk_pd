# Backtesting: 101L C/S SOQUETE DAMA LISO (familia 5151110151)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 20 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |  21 | 207 |  57 |  85 |  81 |  28 | 393 |  46 |  11 |   929 |
| 2025 |   7 |   6 |   6 |  96 | 144 |   - |   - |   - | 191 | 166 | 312 | 438 |  1366 |
| 2026 | 287 |  13 |   2 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   302 |

**Total historico: 2597 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      479 |           - |
| 2025 |      431 |      -10.0% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 95.6 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |         3.5 |      0.037 | Valle |
| Feb |         3.0 |      0.031 | Valle |
| Mar |         3.0 |      0.031 | Valle |
| Abr |        58.5 |      0.612 | Bajo |
| May |       175.5 |      1.835 | Temporada alta |
| Jun |        28.5 |      0.298 | Valle |
| Jul |        42.5 |      0.444 | Bajo |
| Ago |        40.5 |      0.424 | Bajo |
| Sep |       109.5 |      1.145 | Normal |
| Oct |       279.5 |      2.923 | **PICO** |
| Nov |       179.0 |      1.872 | Temporada alta |
| Dic |       224.5 |      2.348 | **PICO** |

**Concentracion OI (abr-sep)**: 40% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |               -2183 | QUEBRADO |
| Feb 2024 |      0 |       0 |               -2183 | QUEBRADO |
| Ene 2024 |      0 |       0 |               -2183 | QUEBRADO |
| Dic 2023 |      0 |       0 |               -2183 | QUEBRADO |
| Nov 2023 |      0 |       0 |               -2183 | QUEBRADO |
| Oct 2023 |      0 |       0 |               -2183 | QUEBRADO |
| Sep 2023 |      0 |       0 |               -2183 | QUEBRADO |
| Ago 2023 |      0 |       0 |               -2183 | QUEBRADO |
| Jul 2023 |      0 |       0 |               -2183 | QUEBRADO |
| Jun 2023 |      0 |       0 |               -2183 | QUEBRADO |
| May 2023 |      0 |       0 |               -2183 | QUEBRADO |
| Abr 2023 |      0 |       0 |               -2183 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 0.0 pares/mes
- vel_real v3 (desest. + disp.) = **0.0 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.61 |                 0 |   21 | -100% |
| May |      1.83 |                 0 |  207 | -100% |
| Jun |      0.30 |                 0 |   57 | -100% |
| Jul |      0.44 |                 0 |   85 | -100% |
| Ago |      0.42 |                 0 |   81 | -100% |
| Sep |      1.15 |                 0 |   28 | -100% |
| **Total** | | **0** | **479** | **-100.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 479 | -100.0% |
| Compras reales | - | 1920 | - |
| MAPE mensual | | | **100.0%** |
| Quiebre pre-OI | | | 100% meses |

**Calidad modelo v3: POBRE (>40%)**

---

## Propuesta de mejora

1. **Quiebre cronico (100%)**: Priorizar reposicion urgente. La vel_real se calcula con pocos meses de datos.
2. **MAPE alto (100%)**: Revisar si hay redistribucion intra-temporada o si el producto tiene tendencia fuerte (CAGR).

### Timing optimo
Para OI: pedir en **primera quincena de enero** (lead time ~60 dias + colchon 15 dias).