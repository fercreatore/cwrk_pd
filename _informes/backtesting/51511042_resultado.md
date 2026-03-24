# Backtesting: 104 C/S SOQUETE KIDS T.2 (familia 5151104251)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 22 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |   1 |  49 |  25 |  27 |  79 |  56 |  91 |  53 |  72 |   453 |
| 2025 |  13 | 107 | 151 |   1 |   - |   1 |   1 |   4 | 121 |  69 |  72 |  76 |   616 |
| 2026 |  36 |  53 |  34 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   123 |

**Total historico: 1192 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      237 |           - |
| 2025 |      128 |      -46.0% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 44.5 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |         6.5 |      0.146 | Valle |
| Feb |        53.5 |      1.201 | Normal |
| Mar |        75.5 |      1.695 | Temporada alta |
| Abr |         1.0 |      0.022 | Valle |
| May |        24.5 |      0.550 | Bajo |
| Jun |        13.0 |      0.292 | Valle |
| Jul |        14.0 |      0.314 | Bajo |
| Ago |        41.5 |      0.932 | Normal |
| Sep |        88.5 |      1.987 | Temporada alta |
| Oct |        80.0 |      1.796 | Temporada alta |
| Nov |        62.5 |      1.403 | Normal |
| Dic |        74.0 |      1.661 | Temporada alta |

**Concentracion OI (abr-sep)**: 34% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |               -1186 | QUEBRADO |
| Feb 2024 |      0 |       0 |               -1186 | QUEBRADO |
| Ene 2024 |      0 |       0 |               -1186 | QUEBRADO |
| Dic 2023 |      0 |       0 |               -1186 | QUEBRADO |
| Nov 2023 |      0 |       0 |               -1186 | QUEBRADO |
| Oct 2023 |      0 |       0 |               -1186 | QUEBRADO |
| Sep 2023 |      0 |       0 |               -1186 | QUEBRADO |
| Ago 2023 |      0 |       0 |               -1186 | QUEBRADO |
| Jul 2023 |      0 |       0 |               -1186 | QUEBRADO |
| Jun 2023 |      0 |       0 |               -1186 | QUEBRADO |
| May 2023 |      0 |       0 |               -1186 | QUEBRADO |
| Abr 2023 |      0 |       0 |               -1186 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 0.0 pares/mes
- vel_real v3 (desest. + disp.) = **0.0 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.02 |                 0 |    1 | -100% |
| May |      0.55 |                 0 |   49 | -100% |
| Jun |      0.29 |                 0 |   25 | -100% |
| Jul |      0.31 |                 0 |   27 | -100% |
| Ago |      0.93 |                 0 |   79 | -100% |
| Sep |      1.99 |                 0 |   56 | -100% |
| **Total** | | **0** | **237** | **-100.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 237 | -100.0% |
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