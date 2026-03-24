# Backtesting: 022 C/S SOQUETE INVISIBLE LISO (familia 5151102251)

> Marca: ELEMENTO | Categoria: MEDIAS
> Stock actual: 5 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2024 |   - |   - |   - |   - |  64 | 125 |  61 |  89 | 173 | 226 |   1 |   8 |   747 |
| 2025 |   3 |  13 |   - |   - |   - |   1 |   1 |   - |   3 | 190 |  38 | 229 |   478 |
| 2026 |  16 |   1 |   - |   - |   - |   - |   - |   - |   - |   - |   - |   - |    17 |

**Total historico: 1242 pares (2024-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2024 |      512 |           - |
| 2025 |        5 |      -99.0% |

---

## Factor estacional

Calculado sobre 2 anios (2024-2025). Promedio mensual = 51.0 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |         1.5 |      0.029 | Valle |
| Feb |         6.5 |      0.127 | Valle |
| Mar |         0.0 |      0.000 | Valle |
| Abr |         0.0 |      0.000 | Valle |
| May |        32.0 |      0.627 | Bajo |
| Jun |        63.0 |      1.234 | Normal |
| Jul |        31.0 |      0.607 | Bajo |
| Ago |        44.5 |      0.872 | Normal |
| Sep |        88.0 |      1.724 | Temporada alta |
| Oct |       208.0 |      4.075 | **PICO** |
| Nov |        19.5 |      0.382 | Bajo |
| Dic |       118.5 |      2.322 | **PICO** |

**Concentracion OI (abr-sep)**: 42% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |                -913 | QUEBRADO |
| Feb 2024 |      0 |       0 |                -913 | QUEBRADO |
| Ene 2024 |      0 |       0 |                -913 | QUEBRADO |
| Dic 2023 |      0 |       0 |                -913 | QUEBRADO |
| Nov 2023 |      0 |       0 |                -913 | QUEBRADO |
| Oct 2023 |      0 |       0 |                -913 | QUEBRADO |
| Sep 2023 |      0 |       0 |                -913 | QUEBRADO |
| Ago 2023 |      0 |       0 |                -913 | QUEBRADO |
| Jul 2023 |      0 |       0 |                -913 | QUEBRADO |
| Jun 2023 |      0 |       0 |                -913 | QUEBRADO |
| May 2023 |      0 |       0 |                -913 | QUEBRADO |
| Abr 2023 |      0 |       0 |                -913 | QUEBRADO |

- **Meses quebrados: 12 de 12 (100%)**
- vel_aparente = 0.0 pares/mes
- vel_real v3 (desest. + disp.) = **0.0 pares/mes**
- Factor disponibilidad: 1.2

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      0.00 |                 0 |    0 | - |
| May |      0.63 |                 0 |   64 | -100% |
| Jun |      1.23 |                 0 |  125 | -100% |
| Jul |      0.61 |                 0 |   61 | -100% |
| Ago |      0.87 |                 0 |   89 | -100% |
| Sep |      1.72 |                 0 |  173 | -100% |
| **Total** | | **0** | **512** | **-100.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 512 | -100.0% |
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