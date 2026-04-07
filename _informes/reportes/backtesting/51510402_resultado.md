# Backtesting: 402L MEDIA 1/3 HOMBRE LISA (familia 5151040251)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 21 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |   - |   - |  39 | 172 | 113 |  59 |  37 |  12 |  16 |   448 |
| 2025 |  12 |  18 |   1 |  40 | 171 |  23 |  10 |   - | 141 | 223 |  25 |  24 |   688 |
| 2026 |  44 |   5 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   - |    49 |

**Total historico: 1185 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      383 |           - |
| 2025 |      385 |       +0.5% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 47.3 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |         6.0 |      0.127 | Valle |
| Feb |         9.0 |      0.190 | Valle |
| Mar |         0.5 |      0.011 | Valle |
| Abr |        20.0 |      0.423 | Bajo |
| May |        85.5 |      1.806 | Temporada alta |
| Jun |        31.0 |      0.655 | Bajo |
| Jul |        91.0 |      1.923 | Temporada alta |
| Ago |        56.5 |      1.194 | Normal |
| Sep |       100.0 |      2.113 | **PICO** |
| Oct |       130.0 |      2.746 | **PICO** |
| Nov |        18.5 |      0.391 | Bajo |
| Dic |        20.0 |      0.423 | Bajo |

**Concentracion OI (abr-sep)**: 68% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |               -1194 | QUEBRADO |
| Feb 2024 |      0 |       0 |               -1194 | QUEBRADO |
| Ene 2024 |      0 |       0 |               -1194 | QUEBRADO |
| Dic 2023 |      0 |       0 |               -1194 | QUEBRADO |
| Nov 2023 |      0 |       0 |               -1194 | QUEBRADO |
| Oct 2023 |      0 |       0 |               -1194 | QUEBRADO |
| Sep 2023 |      0 |       0 |               -1194 | QUEBRADO |
| Ago 2023 |      0 |       0 |               -1194 | QUEBRADO |
| Jul 2023 |      0 |       0 |               -1194 | QUEBRADO |
| Jun 2023 |      0 |       0 |               -1194 | QUEBRADO |
| May 2023 |      0 |       0 |               -1194 | QUEBRADO |
| Abr 2023 |      0 |       0 |               -1194 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 0.0 pares/mes
- vel_real v3 (desest. + disp.) = **0.0 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.42 |                 0 |    0 | - |
| May |      1.81 |                 0 |    0 | - |
| Jun |      0.66 |                 0 |   39 | -100% |
| Jul |      1.92 |                 0 |  172 | -100% |
| Ago |      1.19 |                 0 |  113 | -100% |
| Sep |      2.11 |                 0 |   59 | -100% |
| **Total** | | **0** | **383** | **-100.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 383 | -100.0% |
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