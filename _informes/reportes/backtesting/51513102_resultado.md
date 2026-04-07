# Backtesting: 102D C/S SOQUETE DEPORTIVO HOMBRE (familia 5151310251)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 127 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |   3 | 100 |  99 |  55 |  95 |  84 |  16 |   5 |   4 |   461 |
| 2025 |   - |   5 |  14 | 188 |  33 | 253 | 100 | 100 |  18 |   2 |   6 |   6 |   725 |
| 2026 |   2 |   1 | 114 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   117 |

**Total historico: 1303 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      436 |           - |
| 2025 |      692 |      +58.7% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 49.4 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |         0.0 |      0.000 | Valle |
| Feb |         2.5 |      0.051 | Valle |
| Mar |         7.0 |      0.142 | Valle |
| Abr |        95.5 |      1.933 | Temporada alta |
| May |        66.5 |      1.346 | Normal |
| Jun |       176.0 |      3.562 | **PICO** |
| Jul |        77.5 |      1.568 | Temporada alta |
| Ago |        97.5 |      1.973 | Temporada alta |
| Sep |        51.0 |      1.032 | Normal |
| Oct |         9.0 |      0.182 | Valle |
| Nov |         5.5 |      0.111 | Valle |
| Dic |         5.0 |      0.101 | Valle |

**Concentracion OI (abr-sep)**: 95% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |               -1450 | QUEBRADO |
| Feb 2024 |      0 |       0 |               -1450 | QUEBRADO |
| Ene 2024 |      0 |       0 |               -1450 | QUEBRADO |
| Dic 2023 |      0 |       0 |               -1450 | QUEBRADO |
| Nov 2023 |      0 |       0 |               -1450 | QUEBRADO |
| Oct 2023 |      0 |       0 |               -1450 | QUEBRADO |
| Sep 2023 |      0 |       0 |               -1450 | QUEBRADO |
| Ago 2023 |      0 |       0 |               -1450 | QUEBRADO |
| Jul 2023 |      0 |       0 |               -1450 | QUEBRADO |
| Jun 2023 |      0 |       0 |               -1450 | QUEBRADO |
| May 2023 |      0 |       0 |               -1450 | QUEBRADO |
| Abr 2023 |      0 |       0 |               -1450 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 0.0 pares/mes
- vel_real v3 (desest. + disp.) = **0.0 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      1.93 |                 0 |    3 | -100% |
| May |      1.35 |                 0 |  100 | -100% |
| Jun |      3.56 |                 0 |   99 | -100% |
| Jul |      1.57 |                 0 |   55 | -100% |
| Ago |      1.97 |                 0 |   95 | -100% |
| Sep |      1.03 |                 0 |   84 | -100% |
| **Total** | | **0** | **436** | **-100.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 436 | -100.0% |
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