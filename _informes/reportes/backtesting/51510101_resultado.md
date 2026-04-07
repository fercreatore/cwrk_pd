# Backtesting: 101 C/S SOQUETE DAMA ESTAMPADO (familia 5151010151)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 4 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |   9 | 119 |  58 |  26 |  17 |  79 | 316 |  31 |  49 |   704 |
| 2025 |   6 |   3 |  12 |   - |   - |   - |   - |   1 | 188 | 150 |  73 |  24 |   457 |
| 2026 |  24 |  23 |   1 |   - |   - |   - |   - |   - |   - |   - |   - |   - |    48 |

**Total historico: 1209 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      308 |           - |
| 2025 |      189 |      -38.6% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 48.4 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |         3.0 |      0.062 | Valle |
| Feb |         1.5 |      0.031 | Valle |
| Mar |         6.0 |      0.124 | Valle |
| Abr |         4.5 |      0.093 | Valle |
| May |        59.5 |      1.230 | Normal |
| Jun |        29.0 |      0.599 | Bajo |
| Jul |        13.0 |      0.269 | Valle |
| Ago |         9.0 |      0.186 | Valle |
| Sep |       133.5 |      2.760 | **PICO** |
| Oct |       233.0 |      4.817 | **PICO** |
| Nov |        52.0 |      1.075 | Normal |
| Dic |        36.5 |      0.755 | Bajo |

**Concentracion OI (abr-sep)**: 43% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |               -1187 | QUEBRADO |
| Feb 2024 |      0 |       0 |               -1187 | QUEBRADO |
| Ene 2024 |      0 |       0 |               -1187 | QUEBRADO |
| Dic 2023 |      0 |       0 |               -1187 | QUEBRADO |
| Nov 2023 |      0 |       0 |               -1187 | QUEBRADO |
| Oct 2023 |      0 |       0 |               -1187 | QUEBRADO |
| Sep 2023 |      0 |       0 |               -1187 | QUEBRADO |
| Ago 2023 |      0 |       0 |               -1187 | QUEBRADO |
| Jul 2023 |      0 |       0 |               -1187 | QUEBRADO |
| Jun 2023 |      0 |       0 |               -1187 | QUEBRADO |
| May 2023 |      0 |       0 |               -1187 | QUEBRADO |
| Abr 2023 |      0 |       0 |               -1187 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 0.0 pares/mes
- vel_real v3 (desest. + disp.) = **0.0 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.09 |                 0 |    9 | -100% |
| May |      1.23 |                 0 |  119 | -100% |
| Jun |      0.60 |                 0 |   58 | -100% |
| Jul |      0.27 |                 0 |   26 | -100% |
| Ago |      0.19 |                 0 |   17 | -100% |
| Sep |      2.76 |                 0 |   79 | -100% |
| **Total** | | **0** | **308** | **-100.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 308 | -100.0% |
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