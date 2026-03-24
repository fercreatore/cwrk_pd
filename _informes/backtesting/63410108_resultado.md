# Backtesting: 1000108 BLANCO PLANTILLA TOALLA C/ARCO 3,5MM (familia 6341010801)

> Marca: AROLA - SOBRIL SA | Categoria: PLANTILLA
> Stock actual: 89 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2023 |   - |   - |   - |   - |   - |   - |   - |   - |  10 |  36 |  41 |  27 |   114 |
| 2024 |  21 |  21 |  17 |  36 |  31 |  24 |  28 |  19 |  20 |  35 |  13 |  27 |   292 |
| 2025 |  13 |  20 |  25 |  16 |  17 |   7 |  14 |  14 |  15 |   3 |   2 |   2 |   148 |
| 2026 |   3 |  14 |   4 |   - |   - |   - |   - |   - |   - |   - |   - |   - |    21 |

**Total historico: 575 pares (2023-2026)**

### Ventas OI (abr-sep) por anio

| Anio | OI pares | vs anterior |
|------|----------|-------------|
| 2023 |       10 |           - |
| 2024 |      158 |    +1480.0% |
| 2025 |       83 |      -47.5% |

---

## Factor estacional

Calculado sobre 3 anios (2023-2025). Promedio mensual = 15.4 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |        11.3 |      0.736 | Bajo |
| Feb |        13.7 |      0.888 | Normal |
| Mar |        14.0 |      0.910 | Normal |
| Abr |        17.3 |      1.126 | Normal |
| May |        16.0 |      1.040 | Normal |
| Jun |        10.3 |      0.671 | Bajo |
| Jul |        14.0 |      0.910 | Normal |
| Ago |        11.0 |      0.715 | Bajo |
| Sep |        15.0 |      0.975 | Normal |
| Oct |        24.7 |      1.603 | Temporada alta |
| Nov |        18.7 |      1.213 | Normal |
| Dic |        18.7 |      1.213 | Normal |

**Concentracion OI (abr-sep)**: 45% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |     17 |       0 |                  28 | OK |
| Feb 2024 |     21 |       0 |                  49 | OK |
| Ene 2024 |     21 |       0 |                  70 | OK |
| Dic 2023 |     27 |       0 |                  97 | OK |
| Nov 2023 |     41 |       0 |                 138 | OK |
| Oct 2023 |     36 |       0 |                 174 | OK |
| Sep 2023 |     10 |     912 |                -728 | QUEBRADO |
| Ago 2023 |      0 |       0 |                -728 | QUEBRADO |
| Jul 2023 |      0 |       0 |                -728 | QUEBRADO |
| Jun 2023 |      0 |       0 |                -728 | QUEBRADO |
| May 2023 |      0 |       0 |                -728 | QUEBRADO |
| Abr 2023 |      0 |       0 |                -728 | QUEBRADO |

- **Meses quebrados: 6 de 12 (50%)**
- vel_aparente = 14.4 pares/mes
- vel_real v3 (desest. + disp.) = **27.4 pares/mes**
- Factor disponibilidad: 1.1

---

## Simulacion OI2024

### Proyeccion con modelo v3

| Mes | Factor s_t | Demanda proyectada | Real | Error |
|-----|-----------|-------------------|------|-------|
| Abr |      1.13 |                31 |   36 | -14% |
| May |      1.04 |                28 |   31 | -8% |
| Jun |      0.67 |                18 |   24 | -23% |
| Jul |      0.91 |                25 |   28 | -11% |
| Ago |      0.71 |                20 |   19 | +3% |
| Sep |      0.97 |                27 |   20 | +34% |
| **Total** | | **149** | **158** | **-5.7%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 149 | 158 | -5.7% |
| Compras reales | - | 72 | - |
| MAPE mensual | | | **15.6%** |
| Quiebre pre-OI | | | 50% meses |

**Calidad modelo v3: BUENO (15-25%)**

---

## Propuesta de mejora

3. **Tendencia interanual**: CAGR OI = -47% (2024→2025). Producto en baja.

### Timing optimo
Para OI: pedir en **primera quincena de enero** (lead time ~60 dias + colchon 15 dias).