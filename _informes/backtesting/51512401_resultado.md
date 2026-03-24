# Backtesting: 401R MEDIA 1/3 DAMA RAYADO (familia 5151240151)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 15 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |   - |   - |  12 | 125 |  77 |   3 |   9 |  29 |  33 |   288 |
| 2025 |  21 |  60 |  69 |  14 | 169 |  77 |   5 |   8 |  99 | 203 | 122 |  45 |   892 |
| 2026 |  13 |   8 |   1 |   - |   - |   - |   - |   - |   - |   - |   - |   - |    22 |

**Total historico: 1202 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      217 |           - |
| 2025 |      372 |      +71.4% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 49.2 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |        10.5 |      0.214 | Valle |
| Feb |        30.0 |      0.610 | Bajo |
| Mar |        34.5 |      0.702 | Bajo |
| Abr |         7.0 |      0.142 | Valle |
| May |        84.5 |      1.719 | Temporada alta |
| Jun |        44.5 |      0.905 | Normal |
| Jul |        65.0 |      1.322 | Normal |
| Ago |        42.5 |      0.864 | Normal |
| Sep |        51.0 |      1.037 | Normal |
| Oct |       106.0 |      2.156 | **PICO** |
| Nov |        75.5 |      1.536 | Temporada alta |
| Dic |        39.0 |      0.793 | Bajo |

**Concentracion OI (abr-sep)**: 50% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |               -1183 | QUEBRADO |
| Feb 2024 |      0 |       0 |               -1183 | QUEBRADO |
| Ene 2024 |      0 |       0 |               -1183 | QUEBRADO |
| Dic 2023 |      0 |       0 |               -1183 | QUEBRADO |
| Nov 2023 |      0 |       0 |               -1183 | QUEBRADO |
| Oct 2023 |      0 |       0 |               -1183 | QUEBRADO |
| Sep 2023 |      0 |       0 |               -1183 | QUEBRADO |
| Ago 2023 |      0 |       0 |               -1183 | QUEBRADO |
| Jul 2023 |      0 |       0 |               -1183 | QUEBRADO |
| Jun 2023 |      0 |       0 |               -1183 | QUEBRADO |
| May 2023 |      0 |       0 |               -1183 | QUEBRADO |
| Abr 2023 |      0 |       0 |               -1183 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 0.0 pares/mes
- vel_real v3 (desest. + disp.) = **0.0 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.14 |                 0 |    0 | - |
| May |      1.72 |                 0 |    0 | - |
| Jun |      0.91 |                 0 |   12 | -100% |
| Jul |      1.32 |                 0 |  125 | -100% |
| Ago |      0.86 |                 0 |   77 | -100% |
| Sep |      1.04 |                 0 |    3 | -100% |
| **Total** | | **0** | **217** | **-100.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 217 | -100.0% |
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