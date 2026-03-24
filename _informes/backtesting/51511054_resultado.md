# Backtesting: 105 C/S SOQUETE KIDS T.4 (familia 5151105451)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 14 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |   1 |  66 |  26 |  31 |  71 |  70 | 131 | 110 |  96 |   602 |
| 2025 |  24 |  68 |  43 |   2 |   7 |   - |   - |   - |  59 | 196 | 161 | 153 |   713 |
| 2026 |  80 |  16 |  20 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   116 |

**Total historico: 1431 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      265 |           - |
| 2025 |       68 |      -74.3% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 54.8 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |        12.0 |      0.219 | Valle |
| Feb |        34.0 |      0.621 | Bajo |
| Mar |        21.5 |      0.392 | Bajo |
| Abr |         1.5 |      0.027 | Valle |
| May |        36.5 |      0.666 | Bajo |
| Jun |        13.0 |      0.237 | Valle |
| Jul |        15.5 |      0.283 | Valle |
| Ago |        35.5 |      0.648 | Bajo |
| Sep |        64.5 |      1.177 | Normal |
| Oct |       163.5 |      2.984 | **PICO** |
| Nov |       135.5 |      2.473 | **PICO** |
| Dic |       124.5 |      2.272 | **PICO** |

**Concentracion OI (abr-sep)**: 25% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |               -1195 | QUEBRADO |
| Feb 2024 |      0 |       0 |               -1195 | QUEBRADO |
| Ene 2024 |      0 |       0 |               -1195 | QUEBRADO |
| Dic 2023 |      0 |       0 |               -1195 | QUEBRADO |
| Nov 2023 |      0 |       0 |               -1195 | QUEBRADO |
| Oct 2023 |      0 |       0 |               -1195 | QUEBRADO |
| Sep 2023 |      0 |       0 |               -1195 | QUEBRADO |
| Ago 2023 |      0 |       0 |               -1195 | QUEBRADO |
| Jul 2023 |      0 |       0 |               -1195 | QUEBRADO |
| Jun 2023 |      0 |       0 |               -1195 | QUEBRADO |
| May 2023 |      0 |       0 |               -1195 | QUEBRADO |
| Abr 2023 |      0 |       0 |               -1195 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 0.0 pares/mes
- vel_real v3 (desest. + disp.) = **0.0 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.03 |                 0 |    1 | -100% |
| May |      0.67 |                 0 |   66 | -100% |
| Jun |      0.24 |                 0 |   26 | -100% |
| Jul |      0.28 |                 0 |   31 | -100% |
| Ago |      0.65 |                 0 |   71 | -100% |
| Sep |      1.18 |                 0 |   70 | -100% |
| **Total** | | **0** | **265** | **-100.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 265 | -100.0% |
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