# Backtesting: CROCBAND KIDS C10998 (familia 65610998)

> Fecha: 2026-03-23
> Período de datos: sep-2019 a mar-2026 (7 años)
> Total histórico: ~2,264 pares vendidos

---

## Serie histórica de ventas mensuales

| Año  | Ene | Feb | Mar | Abr | May | Jun | Jul | Ago | Sep | Oct | Nov | Dic | **Total** |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----------|
| 2019 |  —  |  —  |  —  |  —  |  —  |  —  |  —  |  —  |   5 |  15 |  26 |  27 |    **73** |
| 2020 |   4 |   3 |   1 |   1 |   0 |   0 |   0 |   4 |   3 |  22 |  36 |  12 |    **86** |
| 2021 |   8 |   0 |   2 |   0 |   0 |   0 |   3 |   2 |  11 |  22 |  49 |  49 |   **146** |
| 2022 |  30 |   6 |   0 |   0 |   1 |   2 |   6 |   9 |  14 |  30 |  62 |  89 |   **249** |
| 2023 |  48 |  24 |  11 |   7 |   3 |   2 |   2 |   7 |  23 |  70 |  46 |  94 |   **337** |
| 2024 | 100 |  73 |  41 |  22 |   7 |   6 |  26 |  45 |  95 | 252 |  94 |  71 |   **832** |
| 2025 |  40 |  18 |   9 |   1 |   2 |   2 |  10 |   9 |  37 |  96 |  93 | 153 |   **470** |
| 2026 |  38 |  25 |   8 |  —  |  —  |  —  |  —  |  —  |  —  |  —  |  —  |  —  |    **71** |

### Observaciones clave
- **Crecimiento explosivo**: de 86 pares (2020) a 832 pares (2024) = **~10x en 4 años**.
- Tasa de crecimiento interanual: 1.70x (20→21), 1.71x (21→22), 1.35x (22→23), **2.47x** (23→24), 0.57x (24→25).
- 2024 fue un año atípico con 252 pares solo en octubre (posible efecto promoción o nuevo punto de venta).
- 2025 volvió a un nivel más cercano a la tendencia (~470 pares).

---

## Factor estacional

Calculado con datos 2020-2023 (4 años completos previos a la simulación):

| Mes | Ventas promedio | Factor s_t | Caracterización |
|-----|-----------------|------------|-----------------|
| Ene |          22.5   |   **1.32** | Temporada alta  |
| Feb |           8.3   |     0.48   | Bajando         |
| Mar |           3.5   |     0.21   | Fuera de temp.  |
| Abr |           2.0   |     0.12   | Valle           |
| May |           1.0   |     0.06   | Valle mínimo    |
| Jun |           1.0   |     0.06   | Valle mínimo    |
| Jul |           2.8   |     0.16   | Valle           |
| Ago |           5.5   |     0.32   | Inicio repunte  |
| Sep |          12.8   |     0.75   | Repunte fuerte  |
| Oct |          36.0   |   **2.11** | Pico            |
| Nov |          48.3   |   **2.83** | Pico máximo     |
| Dic |          61.0   |   **3.58** | Pico máximo     |

**Promedio mensual global (2020-2023): 17.0 pares/mes**

Producto de **alta estacionalidad verano**: el 85% de las ventas se concentran en Sep-Ene.

---

## Simulación OI2024 (abril-septiembre 2024)

### Inputs del modelo (datos hasta dic-2023)

| Variable | Valor | Método |
|----------|-------|--------|
| Ventas últimos 12 meses (2023) | 337 pares | Suma ene-dic 2023 |
| vel_aparente | 28.1 pares/mes | 337/12 |
| vel_real (con quiebre) | ~28.1 pares/mes | Sin quiebre detectado en 2023 (*) |
| Σ factores OI (abr-sep) | 1.47 | 0.12+0.06+0.06+0.16+0.32+0.75 |

(*) En 2023 hubo 968 pares de compras vs 337 ventas — acumulación fuerte de stock, sin indicios de quiebre.

### Proyección del modelo

```
Demanda_OI2024 = vel_real × Σ(s_t para abr-sep)
                = 28.1 × 1.47
                = 41 pares
```

| Mes  | Factor s_t | Demanda proyectada |
|------|------------|-------------------|
| Abr  |     0.12   |          3 pares  |
| May  |     0.06   |          2 pares  |
| Jun  |     0.06   |          2 pares  |
| Jul  |     0.16   |          4 pares  |
| Ago  |     0.32   |          9 pares  |
| Sep  |     0.75   |         21 pares  |
| **Total** |    |       **41 pares** |

### Realidad OI2024

| Mes  | Ventas reales | Compras reales |
|------|---------------|----------------|
| Abr  |          22   |          108   |
| May  |           7   |            0   |
| Jun  |           6   |            0   |
| Jul  |          26   |          126   |
| Ago  |          45   |           54   |
| Sep  |          95   |           96   |
| **Total** | **201** |      **384**   |

Compras adicionales pre-OI (feb-mar 2024): 96 + 216 = **312 pares**
Total comprado para la temporada: 312 + 384 = **696 pares**

---

## Error cuantificado

| Métrica | Modelo | Realidad | Error | % Error |
|---------|--------|----------|-------|---------|
| **Demanda OI2024** | 41 pares | 201 pares | **-160 pares** | **-80%** |
| **Cantidad compra** | ~41 pares | 696 pares | **-655 pares** | **-94%** |
| **Timing pedido** | ~feb 2024 | feb 2024 | **0 meses** | **OK** |

### Desglose mensual del error de demanda

| Mes | Proyectado | Real | Error |
|-----|-----------|------|-------|
| Abr |         3 |   22 |   -19 |
| May |         2 |    7 |    -5 |
| Jun |         2 |    6 |    -4 |
| Jul |         4 |   26 |   -22 |
| Ago |         9 |   45 |   -36 |
| Sep |        21 |   95 |   -74 |

El error crece dramáticamente en los meses de repunte (jul-sep), confirmando que el modelo subestima la aceleración estacional en un contexto de crecimiento.

---

## Causas del error

### 1. ERROR_CANTIDAD: CRÍTICO (-80%)
El modelo predice 41 pares, la realidad fue 201. Subestimación masiva.

### 2. ERROR_ESTACIONAL: MODERADO
Los factores estacionales calculados con datos 2020-2023 son correctos en forma (el perfil estacional es consistente) pero están calculados sobre una base absoluta baja. Al aplicarlos sobre una velocidad que no captura el crecimiento, el resultado se aplasta.

### 3. ERROR de TENDENCIA: CAUSA RAÍZ
La familia crece consistentemente:
- CAGR 2020-2023: **(337/86)^(1/3) - 1 = 57% anual**
- El modelo vel_real asume demanda estacionaria (sin tendencia)
- Con crecimiento del 57%, la vel_real de 28.1 debería ajustarse a **~44 pares/mes** para 2024
- Incluso con ese ajuste: 44 × 1.47 = **65 pares** (vs 201 reales)
- El crecimiento real 2023→2024 fue de **147%**, un outlier

### 4. ERROR_QUIEBRE: INDETERMINADO
La reconstrucción de stock hacia atrás da valores negativos (-116 al fin de 2023), probablemente por ajustes de inventario o transferencias (código 95) no capturadas en compras1. Esto impide un análisis de quiebre confiable.

Sin embargo, las ventas muy bajas en OI de años anteriores (2020: 9 pares abr-sep, 2021: 5 pares, 2022: 18 pares) podrían estar parcialmente explicadas por quiebre de stock en esos meses — lo cual deprimiría artificialmente los factores estacionales de la temporada baja.

### 5. ERROR_TIMING: NINGUNO
La compra real comenzó en febrero 2024, que coincide con lo que el modelo hubiera recomendado (~2 meses antes del inicio de OI). El timing fue correcto.

### 6. ERROR_REMITO: NO EVALUABLE
No se detectaron anomalías específicas de remitos eliminados para esta familia.

---

## Propuesta de mejora

### Diagnóstico
El modelo actual (`analizar_quiebre_batch` en `app_reposicion.py`) calcula `vel_real` como ventas de meses no quebrados dividido por la cantidad de esos meses. **No tiene componente de tendencia.** Para familias con crecimiento >20% anual, esto genera subestimaciones sistemáticas.

### Mejoras recomendadas

#### 1. Incorporar factor de crecimiento interanual (CAGR)
Comparar ventas del último año vs el anterior para detectar tendencia. Aplicar como multiplicador a la velocidad.

#### 2. Ponderar años recientes más fuertemente en el factor estacional
En lugar de promediar todos los años por igual, usar ponderación exponencial (ej: último año peso 4, penúltimo peso 2, anterior peso 1).

#### 3. Clasificar familias por comportamiento
- **Estacionario**: crecimiento < 10% → usar vel_real sin ajuste
- **Crecimiento moderado**: 10-30% → aplicar CAGR × 0.7 (conservador)
- **Crecimiento explosivo**: >30% → aplicar CAGR × 0.5 + flag de revisión manual

### Código Python del ajuste recomendado

```python
def calcular_vel_real_con_tendencia(codigo_sinonimo, meses=24):
    """
    Extiende analizar_quiebre_batch() agregando detección de tendencia.
    Requiere mínimo 24 meses de historia para calcular CAGR.
    """
    from dateutil.relativedelta import relativedelta
    from datetime import date
    import math

    hoy = date.today()
    hace_12 = (hoy - relativedelta(months=12)).replace(day=1)
    hace_24 = (hoy - relativedelta(months=24)).replace(day=1)

    # Obtener ventas de los últimos 24 meses divididos en 2 períodos
    sql = f"""
        SELECT
            CASE WHEN v.fecha >= '{hace_12.strftime('%Y%m%d')}'
                 THEN 'reciente' ELSE 'anterior' END AS periodo,
            SUM(v.cantidad) AS ventas
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE LEFT(a.codigo_sinonimo, 8) = '{codigo_sinonimo}'
          AND v.codigo NOT IN (7, 36)
          AND v.estado = 'V'
          AND v.fecha >= '{hace_24.strftime('%Y%m%d')}'
        GROUP BY CASE WHEN v.fecha >= '{hace_12.strftime('%Y%m%d')}'
                      THEN 'reciente' ELSE 'anterior' END
    """
    df = query_df(sql)

    ventas_reciente = df.loc[df['periodo'] == 'reciente', 'ventas'].sum()
    ventas_anterior = df.loc[df['periodo'] == 'anterior', 'ventas'].sum()

    # Calcular CAGR (tasa de crecimiento anual)
    if ventas_anterior > 0:
        cagr = (ventas_reciente / ventas_anterior) - 1.0  # growth rate
    else:
        cagr = 0.0

    # Clasificar y aplicar factor
    if cagr < 0.10:
        factor_tendencia = 1.0       # Estacionario
        clasificacion = "estacionario"
    elif cagr < 0.30:
        factor_tendencia = 1.0 + cagr * 0.7   # Moderado, conservador
        clasificacion = "crecimiento_moderado"
    else:
        factor_tendencia = 1.0 + cagr * 0.5   # Explosivo, cap conservador
        clasificacion = "crecimiento_explosivo"
        # Cap máximo de 2x para evitar sobrecompra
        factor_tendencia = min(factor_tendencia, 2.0)

    # vel_real viene de analizar_quiebre_batch() existente
    resultado_quiebre = analizar_quiebre_batch([codigo_sinonimo])
    info = resultado_quiebre.get(codigo_sinonimo, {})
    vel_real = info.get('vel_real', 0)

    vel_ajustada = vel_real * factor_tendencia

    return {
        'vel_real_base': vel_real,
        'vel_ajustada': vel_ajustada,
        'cagr': cagr,
        'factor_tendencia': factor_tendencia,
        'clasificacion': clasificacion,
        'ventas_12m_reciente': ventas_reciente,
        'ventas_12m_anterior': ventas_anterior,
    }
```

### Impacto estimado del ajuste

Para CROCBAND KIDS C10998 con datos a dic-2023:
- `vel_real_base` = 28.1 pares/mes
- `cagr` = (337 - 249) / 249 = 0.35 → clasificación: **crecimiento_explosivo**
- `factor_tendencia` = 1.0 + 0.35 × 0.5 = **1.18**
- `vel_ajustada` = 28.1 × 1.18 = **33.2 pares/mes**
- Demanda OI2024 = 33.2 × 1.47 = **49 pares** (vs 41 sin ajuste, vs 201 real)

**El ajuste mejora la predicción un 19% pero sigue lejos de la realidad.** Esto se debe a que el crecimiento 2023→2024 (147%) fue un outlier no predecible. El modelo debería complementarse con:

1. **Input humano**: para familias con crecimiento >50%, solicitar validación al comprador antes de generar pedido.
2. **Revisión mid-season**: re-evaluar la demanda en julio/agosto y hacer pedido de refuerzo si las ventas superan la proyección en >50%.
3. **Historial de compras del proveedor**: si Crocs aumentó su catálogo o bajó precios, eso explica el salto de demanda que ningún modelo puramente endógeno puede captar.

---

## Resumen ejecutivo

| Aspecto | Resultado |
|---------|-----------|
| Producto | CROCBAND KIDS C10998 — sandalia infantil Crocs |
| Estacionalidad | Muy alta (Sep-Ene = 85% de ventas) |
| Tendencia | Crecimiento explosivo (CAGR 57% 2020-2023) |
| Error principal | Subestimación de demanda (-80%) por falta de componente de tendencia |
| Timing | Correcto (feb 2024 modelo ≈ feb 2024 real) |
| Mejora propuesta | `factor_tendencia` basado en CAGR + clasificación de familia + cap de seguridad |
| Limitación | Reconstrucción de stock no confiable para esta familia (ajustes de inventario) |
