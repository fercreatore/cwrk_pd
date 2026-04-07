# Backtesting: 401 MEDIA 1/3 DAMA ESTAMPA (familia 5151040151)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 150 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |   - |  43 |  69 |  93 |  16 |  13 |   4 |   - |  25 |   263 |
| 2025 |  13 |  81 |  90 |  14 |  12 |  11 | 358 |  79 |  30 |   5 |   1 |   - |   694 |
| 2026 |   1 |   2 | 103 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   106 |

**Total historico: 1063 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      234 |           - |
| 2025 |      504 |     +115.4% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 39.9 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |         6.5 |      0.163 | Valle |
| Feb |        40.5 |      1.016 | Normal |
| Mar |        45.0 |      1.129 | Normal |
| Abr |         7.0 |      0.176 | Valle |
| May |        27.5 |      0.690 | Bajo |
| Jun |        40.0 |      1.003 | Normal |
| Jul |       225.5 |      5.655 | **PICO** |
| Ago |        47.5 |      1.191 | Normal |
| Sep |        21.5 |      0.539 | Bajo |
| Oct |         4.5 |      0.113 | Valle |
| Nov |         0.5 |      0.013 | Valle |
| Dic |        12.5 |      0.313 | Bajo |

**Concentracion OI (abr-sep)**: 77% de las ventas anuales.

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
| Abr |      0.18 |                 0 |    0 | - |
| May |      0.69 |                 0 |   43 | -100% |
| Jun |      1.00 |                 0 |   69 | -100% |
| Jul |      5.66 |                 0 |   93 | -100% |
| Ago |      1.19 |                 0 |   16 | -100% |
| Sep |      0.54 |                 0 |   13 | -100% |
| **Total** | | **0** | **234** | **-100.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 234 | -100.0% |
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