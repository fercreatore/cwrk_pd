# Backtesting: 102R C/S SOQUETE RAYADO HOMBRE (familia 5150110251)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 25 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |   7 |  56 |  57 |  26 |  30 |  55 |   7 |   3 | 177 |   418 |
| 2025 |  44 |  12 |   - |   - |   1 |   - |   1 |   - | 257 | 212 |   3 | 177 |   707 |
| 2026 | 234 |  41 |   5 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   280 |

**Total historico: 1405 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      231 |           - |
| 2025 |      259 |      +12.1% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 46.9 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |        22.0 |      0.469 | Bajo |
| Feb |         6.0 |      0.128 | Valle |
| Mar |         0.0 |      0.000 | Valle |
| Abr |         3.5 |      0.075 | Valle |
| May |        28.5 |      0.608 | Bajo |
| Jun |        28.5 |      0.608 | Bajo |
| Jul |        13.5 |      0.288 | Valle |
| Ago |        15.0 |      0.320 | Bajo |
| Sep |       156.0 |      3.328 | **PICO** |
| Oct |       109.5 |      2.336 | **PICO** |
| Nov |         3.0 |      0.064 | Valle |
| Dic |       177.0 |      3.776 | **PICO** |

**Concentracion OI (abr-sep)**: 44% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |               -1210 | QUEBRADO |
| Feb 2024 |      0 |       0 |               -1210 | QUEBRADO |
| Ene 2024 |      0 |       0 |               -1210 | QUEBRADO |
| Dic 2023 |      0 |       0 |               -1210 | QUEBRADO |
| Nov 2023 |      0 |       0 |               -1210 | QUEBRADO |
| Oct 2023 |      0 |       0 |               -1210 | QUEBRADO |
| Sep 2023 |      0 |       0 |               -1210 | QUEBRADO |
| Ago 2023 |      0 |       0 |               -1210 | QUEBRADO |
| Jul 2023 |      0 |       0 |               -1210 | QUEBRADO |
| Jun 2023 |      0 |       0 |               -1210 | QUEBRADO |
| May 2023 |      0 |       0 |               -1210 | QUEBRADO |
| Abr 2023 |      0 |       0 |               -1210 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 0.0 pares/mes
- vel_real v3 (desest. + disp.) = **0.0 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.07 |                 0 |    7 | -100% |
| May |      0.61 |                 0 |   56 | -100% |
| Jun |      0.61 |                 0 |   57 | -100% |
| Jul |      0.29 |                 0 |   26 | -100% |
| Ago |      0.32 |                 0 |   30 | -100% |
| Sep |      3.33 |                 0 |   55 | -100% |
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