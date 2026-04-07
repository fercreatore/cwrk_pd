# Backtesting: 349 NEGRO ZAPATO ESPANOL/FOLCLORE 4,5 CM (familia 0110035000)

> Marca: GO by CLZ | Categoria: CASUAL
> Stock actual: 23 pares (mar-2026)
> Generado automaticamente: 2026-03-24

---

## Serie historica

| Anio |   1 |   2 |   3 |   4 |   5 |   6 |   7 |   8 |   9 |  10 |  11 |  12 | Total |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2025 |   - |   - |   - |   - |   - |   - |   - |  23 |  97 |  98 |  62 |  33 |   313 |
| 2026 |  39 |  23 |  29 |   - |   - |   - |   - |   - |   - |   - |   - |   - |    91 |

**Total historico: 404 pares (2025-2026)**

---

## Factor estacional

Calculado sobre 2 anios (2025-2026). Promedio mensual = 16.8 pares/mes.

| Mes | Prom mensual | Factor s_t | Rol |
|-----|-------------|------------|-----|
| Ene |        19.5 |      1.158 | Normal |
| Feb |        11.5 |      0.683 | Bajo |
| Mar |        14.5 |      0.861 | Normal |
| Abr |         0.0 |      0.000 | Valle |
| May |         0.0 |      0.000 | Valle |
| Jun |         0.0 |      0.000 | Valle |
| Jul |         0.0 |      0.000 | Valle |
| Ago |        11.5 |      0.683 | Bajo |
| Sep |        48.5 |      2.881 | **PICO** |
| Oct |        49.0 |      2.911 | **PICO** |
| Nov |        31.0 |      1.842 | Temporada alta |
| Dic |        16.5 |      0.980 | Normal |

**Concentracion OI (abr-sep)**: 30% de las ventas anuales.

---

## Analisis de quiebre pre-OI2024

| Mes | Ventas | Compras | Stock inicio (rec.) | Estado |
|-----|--------|---------|---------------------|--------|
| Mar 2024 |      0 |       0 |                -423 | QUEBRADO |
| Feb 2024 |      0 |       0 |                -423 | QUEBRADO |
| Ene 2024 |      0 |       0 |                -423 | QUEBRADO |
| Dic 2023 |      0 |       0 |                -423 | QUEBRADO |
| Nov 2023 |      0 |       0 |                -423 | QUEBRADO |
| Oct 2023 |      0 |       0 |                -423 | QUEBRADO |
| Sep 2023 |      0 |       0 |                -423 | QUEBRADO |
| Ago 2023 |      0 |       0 |                -423 | QUEBRADO |
| Jul 2023 |      0 |       0 |                -423 | QUEBRADO |
| Jun 2023 |      0 |       0 |                -423 | QUEBRADO |
| May 2023 |      0 |       0 |                -423 | QUEBRADO |
| Abr 2023 |      0 |       0 |                -423 | QUEBRADO |

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
| May |      0.00 |                 0 |    0 | - |
| Jun |      0.00 |                 0 |    0 | - |
| Jul |      0.00 |                 0 |    0 | - |
| Ago |      0.68 |                 0 |    0 | - |
| Sep |      2.88 |                 0 |    0 | - |
| **Total** | | **0** | **0** | **+0.0%** |

---

## Error cuantificado

| Metrica | Modelo v3 | Real | Error |
|---------|-----------|------|-------|
| Demanda OI2024 | 0 | 0 | +0.0% |
| MAPE mensual | | | **0.0%** |
| Quiebre pre-OI | | | 100% meses |

**Calidad modelo v3: EXCELENTE (<15%)**

---

## Propuesta de mejora

1. **Quiebre cronico (100%)**: Priorizar reposicion urgente. La vel_real se calcula con pocos meses de datos.

### Timing optimo
Para OI: pedir en **primera quincena de enero** (lead time ~60 dias + colchon 15 dias).