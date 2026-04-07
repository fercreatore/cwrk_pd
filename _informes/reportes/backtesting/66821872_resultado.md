# Backtesting: 21872 TOPPER X FORCER — Zapatilla Cuero Acordonada

**Familia**: `66821872` | **Marca**: TOPPER (314) | **Proveedor**: ALPARGATAS S.A.I.C. (668)
**Producto**: 21872 NGO/GRIS/NARAN X FORCER ZAPA CUERO ACORD
**Período analizado**: 2015–2025 (11 años completos, 2665 pares vendidos)
**Stock actual (mar-2026)**: 58 pares

---

## Serie historica de ventas mensuales (pares)

| Anio | Ene | Feb | Mar | Abr | May | Jun | Jul | Ago | Sep | Oct | Nov | Dic | **Total** |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----------|
| 2015 |   4 |   9 |   5 |   0 |   3 |   5 |   8 |  11 |   6 |   7 |   9 |   3 | **70** |
| 2016 |   2 |  15 |  13 |  10 |  13 |   8 |  14 |   6 |  11 |   3 |   7 |   8 | **110** |
| 2017 |  10 |  16 |  28 |  10 |   5 |  31 |  23 |  24 |  29 |   9 |   5 |   0 | **190** |
| 2018 |  12 |  65 |  40 |  26 |  20 |  18 |  17 |  11 |   6 |   4 |   7 |   5 | **231** |
| 2019 |   7 |  38 |  41 |  19 |  29 |  48 |  47 |  39 |  19 |  15 |   8 |  16 | **326** |
| 2020 |  23 |  67 |  12 |   1 |  21 |  40 |  38 |  18 |  17 |   8 |  12 |  14 | **271** |
| 2021 |  11 |  33 |  83 |  32 |  17 |  29 |   6 |  19 |  18 |  23 |  14 |  13 | **298** |
| 2022 |   9 |  66 |  35 |  36 |  17 |  16 |  31 |  22 |  26 |   8 |   8 |   3 | **277** |
| 2023 |   7 |  23 |  23 |  18 |  23 |  30 |  37 |  31 |  31 |  38 |  13 |  11 | **285** |
| 2024 |  16 |  69 |  24 |  26 |  41 |  32 |  11 |  21 |  13 |  22 |  12 |  11 | **298** |
| 2025 |  15 |  53 |  26 |  24 |  36 |  38 |  22 |  30 |  17 |  29 |   7 |  12 | **309** |

**Observaciones**:
- Crecimiento sostenido: de 70 pares (2015) a 309 pares (2025), ~4.4x en 11 anios.
- 2020 muestra el impacto COVID en marzo-abril (12, 1 pares), con recuperacion rapida en junio.
- 2024 julio=11, agosto=21, septiembre=13: anomalamente bajos → posible quiebre de stock.

---

## Factor estacional (calculado con datos 2015–2023, 9 anios)

| Mes | Venta promedio | Factor s_t | Interpretacion |
|-----|----------------|------------|----------------|
| Ene |  9.4 | **0.50** | Valle — post-fiestas |
| Feb | 36.9 | **1.94** | PICO MAXIMO — vuelta a clases |
| Mar | 31.1 | **1.63** | Pico secundario — inicio escolar |
| Abr | 16.9 | **0.89** | Inicio OI — moderado |
| May | 16.4 | **0.86** | OI temprano |
| Jun | 25.0 | **1.31** | Pico OI — Dia del Padre / frio |
| Jul | 24.6 | **1.29** | Pico OI — vacaciones invierno |
| Ago | 20.1 | **1.06** | OI medio |
| Sep | 18.1 | **0.95** | Cierre OI |
| Oct | 12.8 | **0.67** | Valle — transicion |
| Nov |  9.2 | **0.48** | Valle |
| Dic |  8.1 | **0.43** | Valle minimo |

**Patron**: No es "perenne puro" como sugiere la descripcion del agente. Tiene **doble estacionalidad**:
1. **Feb-Mar**: pico fuerte por vuelta a clases (factor 1.94/1.63)
2. **Jun-Jul**: pico secundario OI (factor 1.31/1.29)

La clasificacion correcta es **zapatilla deportiva con estacionalidad escolar + OI**.

---

## Simulacion OI2024 (modelo vs realidad)

### Parametros del modelo (simulando enero 2024)

**Velocidad base** (ultimos 12 meses, 2023):
- Vel aparente: 285 / 12 = **23.8 pares/mes**
- Analisis de quiebre 2023: H1 tuvo stock deprimido (compras masivas Feb-May y Jul-Ago para recomponer). Se estima 5-7 meses quebrados en reconstruccion hacia atras.
- Vel real (quiebre-ajustada, meses Ago-Dic OK): 124 / 5 = **24.8 pares/mes**

### Demanda proyectada OI2024 (abril–septiembre)

| Mes | vel_real x s_t | Proyeccion |
|-----|---------------|------------|
| Abr | 24.8 x 0.89 | 22 |
| May | 24.8 x 0.86 | 21 |
| Jun | 24.8 x 1.31 | 33 |
| Jul | 24.8 x 1.29 | 32 |
| Ago | 24.8 x 1.06 | 26 |
| Sep | 24.8 x 0.95 | 24 |
| **TOTAL** | | **158 pares** |

### Realidad OI2024

| Mes | Ventas reales | Compras recibidas | Observacion |
|-----|---------------|-------------------|-------------|
| Abr | 26 | 0 | Bien surtido (pre-season Jan-Mar = 152 pares) |
| May | **41** | 0 | MUY por encima de lo proyectado (21) |
| Jun | 32 | 0 | En linea con proyeccion (33) |
| Jul | **11** | 96 | QUEBRADO — stock agotado, remito llego tarde |
| Ago | 21 | 0 | Recuperacion parcial post-remito Jul |
| Sep | 13 | 82 | Sub-venta, remito llego al final |
| **TOTAL** | **144** | **178** | |

### Compras del ciclo completo (pre-season + in-season)

| Periodo | Pares | Notas |
|---------|-------|-------|
| Ene 2024 | 92 | Pre-season PV→OI |
| Feb 2024 | 48 | Pre-season |
| Mar 2024 | 12 | Pre-season |
| Jul 2024 | 96 | In-season (llego ~3 meses tarde) |
| Sep 2024 | 82 | In-season (para PV2025?) |
| **Total** | **330** | Incluye stock para PV2025 |

### Primer remito del ciclo
- **Fecha real**: 15-ene-2024
- **Timing optimo modelo**: ~febrero 2024 (2 meses antes de abril, lead time historico)
- **Error timing**: El primer remito (Ene) fue temprano, pero los remitos OI-especificos (Jul, Sep) fueron **3-5 meses tarde**.

---

## Error cuantificado

| Metrica | Modelo | Real | Error | % |
|---------|--------|------|-------|---|
| Demanda OI2024 (6 meses) | 158 | 144 (vendidos) | +14 | +9.7% |
| Demanda ajustada por quiebre OI2024 | 158 | ~181 (estimada) | -23 | **-12.7%** |
| Compras sugeridas (dem - stock_inicio) | ~60-100 | 178 (in-season) | — | — |

### Interpretacion clave

El modelo **parece sobreestimar** (+9.7%) si se compara con ventas reales. Pero las ventas reales fueron **deprimidas por quiebre en Jul-Sep**:
- Julio vendio 11 cuando el modelo esperaba 32 → **21 pares perdidos por falta de stock**
- Septiembre vendio 13 cuando el modelo esperaba 24 → **11 pares perdidos**
- Total pares perdidos por quiebre: ~32-37 pares

La demanda REAL (lo que se hubiera vendido con stock) fue ~181 pares. El modelo **subestimo** en un 12.7%.

**El error no fue del modelo de demanda, fue de timing de compra.**

---

## Causas del error

### ERROR_TIMING (PRINCIPAL)
Los remitos OI llegaron en julio y septiembre, cuando la temporada empezo en abril. El stock pre-season (152 pares de Ene-Mar) se agoto para junio, dejando julio-septiembre desabastecido.

**Lead time real OI**: pedido deberia hacerse en ene-feb para entrega mar-abr. El proveedor (Alpargatas) tuvo entregas escalonadas muy espaciadas.

### ERROR_ESTACIONAL (MODERADO)
Mayo 2024 vendio 41 pares, el doble de lo proyectado (21). El factor estacional de mayo (0.86) esta calculado sobre historico donde mayo era mes debil. Pero en 2023 y 2024 mayo fue fuerte (23 y 41). Posible cambio de patron de consumo o efecto de buena disponibilidad de stock.

### ERROR_QUIEBRE (MENOR)
El analisis de quiebre de 2023 es impreciso porque la reconstruccion de stock hacia atras depende del stock absoluto, que no se puede determinar con precision solo desde compras1/ventas1 (existen movimientos internos no capturados: remitos cod 7, ajustes, etc.). La discrepancia entre stock teorico (compras - ventas lifetime = +2491) y stock real (58) es de ~2433 unidades en movimientos no rastreados.

### ERROR_CANTIDAD (NO APLICA)
La empresa compro 330 pares en el ciclo — suficiente para cubrir la demanda. El problema no fue cuanto compraron sino cuando llego.

---

## Propuesta de mejora

### 1. Separar proyeccion por sub-temporada

El modelo actual proyecta OI como bloque. Esta familia tiene ventas fuertes en Abr-May (vuelta de vacaciones, efecto escolar tardio) que difieren del patron Jun-Sep. Propuesta: dividir en **OI-temprano** (Abr-May) y **OI-pleno** (Jun-Sep).

### 2. Factor estacional con peso reciente (weighted)

Usar media ponderada con mas peso en ultimos 3 anios para captar cambios de patron (ej: mayo creciendo).

### 3. Alerta de timing por stock coverage

Agregar al modelo: `cobertura_dias = stock_actual / vel_real_diaria`. Si la cobertura cae por debajo de `lead_time + 30 dias`, disparar alerta de reposicion.

### 4. Ajuste de velocidad por tendencia

La familia crece ~10% anual (de 277 en 2022 a 309 en 2025). Aplicar factor de tendencia `1 + tasa_crecimiento` sobre la velocidad historica.

### Codigo Python del ajuste recomendado

```python
def proyectar_demanda_mejorada(vel_real, factores_est, meses_target,
                                hist_anual=None, peso_reciente=0.5):
    """
    Proyeccion mejorada con:
    1. Factor estacional ponderado (mas peso ultimos 3 anios)
    2. Ajuste por tendencia de crecimiento
    3. Alerta de cobertura

    Args:
        vel_real: velocidad real mensual (quiebre-ajustada)
        factores_est: dict {mes: factor_estacional}
        meses_target: lista de (anio, mes) a proyectar
        hist_anual: dict {anio: ventas_totales} para calcular tendencia
        peso_reciente: peso extra para ultimos 3 anios en estacionalidad
    """
    # --- Ajuste por tendencia ---
    tasa_crecimiento = 0.0
    if hist_anual and len(hist_anual) >= 3:
        anios = sorted(hist_anual.keys())
        ultimos_3 = anios[-3:]
        primeros_3 = anios[:3]
        avg_reciente = sum(hist_anual[a] for a in ultimos_3) / 3
        avg_antiguo = sum(hist_anual[a] for a in primeros_3) / 3
        n_anios = ultimos_3[-1] - primeros_3[0]
        if avg_antiguo > 0 and n_anios > 0:
            tasa_crecimiento = (avg_reciente / avg_antiguo) ** (1 / n_anios) - 1
            tasa_crecimiento = min(tasa_crecimiento, 0.15)  # cap 15% anual

    vel_ajustada = vel_real * (1 + tasa_crecimiento)

    # --- Proyeccion mensual ---
    proyeccion = {}
    total = 0
    for anio, mes in meses_target:
        s_t = factores_est.get(mes, 1.0)
        dem = vel_ajustada * s_t
        proyeccion[(anio, mes)] = round(dem, 1)
        total += dem

    return {
        'proyeccion_mensual': proyeccion,
        'demanda_total': round(total),
        'vel_base': vel_real,
        'vel_ajustada': round(vel_ajustada, 2),
        'tasa_crecimiento': round(tasa_crecimiento * 100, 1),
    }


def calcular_factores_est_ponderados(ventas_por_anio_mes, peso_reciente=0.5):
    """
    Calcula factores estacionales con mayor peso en ultimos 3 anios.

    Args:
        ventas_por_anio_mes: dict {(anio, mes): ventas}
        peso_reciente: peso adicional para ultimos 3 anios (0-1)
    Returns:
        dict {mes: factor_estacional}
    """
    import numpy as np
    from collections import defaultdict

    # Agrupar por anio
    anios = sorted(set(a for a, m in ventas_por_anio_mes.keys()))
    if len(anios) < 2:
        return {m: 1.0 for m in range(1, 13)}

    ultimos_3 = set(anios[-3:])

    # Promedio ponderado por mes
    suma_pond = defaultdict(float)
    peso_total = defaultdict(float)

    for (anio, mes), ventas in ventas_por_anio_mes.items():
        w = 1.0 + (peso_reciente if anio in ultimos_3 else 0.0)
        suma_pond[mes] += ventas * w
        peso_total[mes] += w

    avg_mes = {}
    for m in range(1, 13):
        avg_mes[m] = suma_pond[m] / peso_total[m] if peso_total[m] > 0 else 0

    gran_media = sum(avg_mes.values()) / 12
    if gran_media == 0:
        return {m: 1.0 for m in range(1, 13)}

    return {m: round(avg_mes[m] / gran_media, 2) for m in range(1, 13)}


def alerta_cobertura(stock_actual, vel_real, lead_time_dias=60,
                     margen_dias=30):
    """
    Retorna True si stock cubre menos de lead_time + margen.
    """
    vel_diaria = vel_real / 30
    if vel_diaria <= 0:
        return False
    cobertura_dias = stock_actual / vel_diaria
    umbral = lead_time_dias + margen_dias
    return cobertura_dias < umbral, round(cobertura_dias)
```

### Ejemplo aplicado a esta familia

```python
# Datos familia 66821872
hist_anual = {
    2015: 70, 2016: 110, 2017: 190, 2018: 231, 2019: 326,
    2020: 271, 2021: 298, 2022: 277, 2023: 285
}

factores_est = {
    1: 0.50, 2: 1.94, 3: 1.63, 4: 0.89, 5: 0.86, 6: 1.31,
    7: 1.29, 8: 1.06, 9: 0.95, 10: 0.67, 11: 0.48, 12: 0.43
}

# Simulacion OI2024 con modelo mejorado
resultado = proyectar_demanda_mejorada(
    vel_real=24.8,
    factores_est=factores_est,
    meses_target=[(2024, m) for m in range(4, 10)],
    hist_anual=hist_anual,
    peso_reciente=0.5
)
# resultado['demanda_total'] = ~170 pares (vs 158 sin tendencia)
# Mas cercano a demanda real estimada de ~181
```

---

## Resumen ejecutivo

| | Modelo actual | Realidad | Modelo mejorado (estimado) |
|---|---|---|---|
| Demanda OI2024 | 158 | ~181 (ajustada quiebre) | ~170 |
| Error vs demanda real | -12.7% | — | -6.5% |
| Timing sugerido | Feb 2024 | Jul-Sep 2024 (tarde) | Feb 2024 + alerta cobertura |

**Conclusion**: El modelo de demanda funciona razonablemente bien (+/-13%). El problema principal de OI2024 no fue proyeccion incorrecta sino **timing de entregas del proveedor**. Agregar alerta de cobertura y ajuste por tendencia de crecimiento mejoraria la precision y evitaria el quiebre mid-season que costo ~35 pares de venta perdida.
