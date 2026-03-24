# Backtesting: 102L C/S SOQUETE LISO HOMBRE (familia 5150010251)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 24 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |  29 | 193 |  95 |  77 |  58 |  36 | 380 |  33 |  28 |   929 |
| 2025 |   7 |   6 |   8 | 140 |  79 | 363 |  63 |  19 | 178 |  99 |   8 |   3 |   973 |
| 2026 |   9 | 206 |  16 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   231 |

**Total historico: 2133 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      488 |           - |
| 2025 |      842 |      +72.5% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 79.2 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |         3.5 |      0.044 | Valle |
| Feb |         3.0 |      0.038 | Valle |
| Mar |         4.0 |      0.050 | Valle |
| Abr |        84.5 |      1.066 | Normal |
| May |       136.0 |      1.716 | Temporada alta |
| Jun |       229.0 |      2.890 | **PICO** |
| Jul |        70.0 |      0.883 | Normal |
| Ago |        38.5 |      0.486 | Bajo |
| Sep |       107.0 |      1.350 | Normal |
| Oct |       239.5 |      3.022 | **PICO** |
| Nov |        20.5 |      0.259 | Valle |
| Dic |        15.5 |      0.196 | Valle |

**Concentracion OI (abr-sep)**: 70% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |               -2163 | QUEBRADO |
| Feb 2024 |      0 |       0 |               -2163 | QUEBRADO |
| Ene 2024 |      0 |       0 |               -2163 | QUEBRADO |
| Dic 2023 |      0 |       0 |               -2163 | QUEBRADO |
| Nov 2023 |      0 |       0 |               -2163 | QUEBRADO |
| Oct 2023 |      0 |       0 |               -2163 | QUEBRADO |
| Sep 2023 |      0 |       0 |               -2163 | QUEBRADO |
| Ago 2023 |      0 |       0 |               -2163 | QUEBRADO |
| Jul 2023 |      0 |       0 |               -2163 | QUEBRADO |
| Jun 2023 |      0 |       0 |               -2163 | QUEBRADO |
| May 2023 |      0 |       0 |               -2163 | QUEBRADO |
| Abr 2023 |      0 |       0 |               -2163 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 0.0 pares/mes
- vel_real v3 (desest. + disp.) = **0.0 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      1.07 |                 0 |   29 | -100% |
| May |      1.72 |                 0 |  193 | -100% |
| Jun |      2.89 |                 0 |   95 | -100% |
| Jul |      0.88 |                 0 |   77 | -100% |
| Ago |      0.49 |                 0 |   58 | -100% |
| Sep |      1.35 |                 0 |   36 | -100% |
| **Total** | | **0** | **488** | **-100.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 488 | -100.0% |
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