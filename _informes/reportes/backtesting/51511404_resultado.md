# Backtesting: 404 MEDIA 1/3 ESTAMPA T.3 (familia 5151140451)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 398 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |   - |  69 |  85 | 125 | 123 |  67 |  28 |  19 |  23 |   539 |
| 2025 |   6 |  18 |  22 | 179 | 192 | 469 | 222 |  46 |  23 |   1 |   - |   2 |  1180 |
| 2026 |   3 |   1 | 184 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   188 |

**Total historico: 1907 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      469 |           - |
| 2025 |     1131 |     +141.2% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 71.6 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |         3.0 |      0.042 | Valle |
| Feb |         9.0 |      0.126 | Valle |
| Mar |        11.0 |      0.154 | Valle |
| Abr |        89.5 |      1.250 | Normal |
| May |       130.5 |      1.822 | Temporada alta |
| Jun |       277.0 |      3.867 | **PICO** |
| Jul |       173.5 |      2.422 | **PICO** |
| Ago |        84.5 |      1.180 | Normal |
| Sep |        45.0 |      0.628 | Bajo |
| Oct |        14.5 |      0.202 | Valle |
| Nov |         9.5 |      0.133 | Valle |
| Dic |        12.5 |      0.175 | Valle |

**Concentracion OI (abr-sep)**: 93% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |               -2303 | QUEBRADO |
| Feb 2024 |      0 |       0 |               -2303 | QUEBRADO |
| Ene 2024 |      0 |       0 |               -2303 | QUEBRADO |
| Dic 2023 |      0 |       0 |               -2303 | QUEBRADO |
| Nov 2023 |      0 |       0 |               -2303 | QUEBRADO |
| Oct 2023 |      0 |       0 |               -2303 | QUEBRADO |
| Sep 2023 |      0 |       0 |               -2303 | QUEBRADO |
| Ago 2023 |      0 |       0 |               -2303 | QUEBRADO |
| Jul 2023 |      0 |       0 |               -2303 | QUEBRADO |
| Jun 2023 |      0 |       0 |               -2303 | QUEBRADO |
| May 2023 |      0 |       0 |               -2303 | QUEBRADO |
| Abr 2023 |      0 |       0 |               -2303 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 0.0 pares/mes
- vel_real v3 (desest. + disp.) = **0.0 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      1.25 |                 0 |    0 | - |
| May |      1.82 |                 0 |   69 | -100% |
| Jun |      3.87 |                 0 |   85 | -100% |
| Jul |      2.42 |                 0 |  125 | -100% |
| Ago |      1.18 |                 0 |  123 | -100% |
| Sep |      0.63 |                 0 |   67 | -100% |
| **Total** | | **0** | **469** | **-100.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 469 | -100.0% |
| Compras reales | - | 1152 | - |
| MAPE mensual | | | **100.0%** |
| Quiebre pre-OI | | | 100% meses |

**Calidad modelo v3: POBRE (>40%)**

---

## Propuesta de mejora

1. **Quiebre cronico (100%)**: Priorizar reposicion urgente. La vel_real se calcula con pocos meses de datos.
2. **MAPE alto (100%)**: Revisar si hay redistribucion intra-temporada o si el producto tiene tendencia fuerte (CAGR).

### Timing optimo
Para OI: pedir en **primera quincena de enero** (lead time ~60 dias + colchon 15 dias).