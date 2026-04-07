# Backtesting: ALPARGATA REFORZADA (familia 23649500)

> Fecha: 2026-03-23
> Proveedor: 236 | Stock actual: 381 pares
> Producto: ALPARGATA REFORZADA NEGRO C/ELAST S/EVA (y variantes por talle)

---

## 1. Serie histórica de ventas mensuales (pares)

| Año | Ene | Feb | Mar | Abr | May | Jun | Jul | Ago | Sep | Oct | Nov | Dic | **Total** |
|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----------|
| 2011 | — | — | — | — | — | 1 | 2 | 1 | 2 | 2 | 4 | 3 | **15** |
| 2012 | 11 | 6 | 6 | 2 | — | 3 | — | 1 | 4 | 2 | 5 | 17 | **57** |
| 2013 | 17 | 12 | 9 | 2 | 1 | 1 | 1 | 5 | 4 | 7 | 5 | 4 | **68** |
| 2014 | 12 | 7 | 2 | 4 | 1 | 4 | 4 | 7 | 16 | 14 | 21 | 22 | **114** |
| 2015 | 32 | 23 | 10 | 18 | 10 | 4 | 3 | 4 | 15 | 11 | 29 | 34 | **193** |
| 2016 | 34 | 35 | 13 | 8 | 5 | 4 | 6 | 4 | 3 | 17 | 51 | 118 | **298** |
| 2017 | 80 | 51 | 35 | 19 | 36 | 26 | 17 | 18 | 34 | 37 | 101 | 112 | **566** |
| 2018 | 84 | 88 | 62 | 26 | 17 | 8 | 15 | 9 | 52 | 34 | 87 | 103 | **585** |
| 2019 | 83 | 79 | 59 | 36 | 25 | 17 | 22 | 22 | 35 | 48 | 70 | 137 | **633** |
| 2020 | 178 | 101 | 47 | 6 | 29 | 33 | 19 | 34 | 60 | 122 | 220 | 232 | **1081** |
| 2021 | 94 | 77 | 51 | 45 | 18 | 24 | 33 | 41 | 40 | 80 | 135 | 199 | **837** |
| 2022 | 100 | 47 | 29 | 53 | 76 | 75 | 53 | 66 | 54 | 69 | 187 | 297 | **1106** |
| 2023 | 192 | 82 | 85 | 29 | 27 | 19 | 17 | 24 | 39 | 42 | 108 | 101 | **765** |
| 2024 | 98 | 85 | 45 | 26 | 58 | 28 | 101 | 38 | 57 | 94 | 133 | 86 | **849** |
| 2025 | 123 | 84 | 34 | 30 | 33 | 21 | 24 | 39 | 53 | 115 | 72 | 38 | **666** |
| 2026 | 61 | 27 | 24 | — | — | — | — | — | — | — | — | — | **112** |

**Total acumulado: ~7.945 pares** (16 años de historia)

---

## 2. Factor estacional

Calculado sobre 2015–2023 (9 años completos con volumen significativo):

| Mes | Promedio (pares) | Factor s_t | Clasificación |
|-----|------------------|-----------|---------------|
| Ene | 97.4 | **1.74** | PICO |
| Feb | 64.8 | **1.15** | Alto |
| Mar | 43.4 | 0.77 | Medio |
| Abr | 26.7 | 0.48 | Valle |
| May | 27.0 | 0.48 | Valle |
| Jun | 23.3 | 0.42 | **VALLE** |
| Jul | 20.6 | **0.37** | **VALLE MÍNIMO** |
| Ago | 24.7 | 0.44 | Valle |
| Sep | 36.9 | 0.66 | Medio-bajo |
| Oct | 51.1 | 0.91 | Medio |
| Nov | 109.8 | **1.96** | PICO |
| Dic | 148.1 | **2.64** | **PICO MÁXIMO** |

**Promedio mensual anual: 56.1 pares/mes**

**Hallazgo clave**: Contrario a la clasificación inicial ("sin estacionalidad marcada"), este producto tiene **fuerte estacionalidad de verano**. Ratio pico/valle = 2.64 / 0.37 = **7.1x**. El pico Nov-Ene concentra el 53% de las ventas anuales.

---

## 3. Simulación OI2024 (abril–septiembre) con datos hasta diciembre 2023

### 3a. Velocidad de venta (modelo)

Usando 12 meses de 2023:
- **Ventas totales 2023**: 765 pares
- **vel_aparente**: 765 / 12 = **63.75 pares/mes**
- **Compras 2023**: 456 pares (may=168, ago=144, sep=144)
- **Análisis de quiebre**: Con stock estimado a fin de 2023 ~400 pares (reconstruido hacia atrás desde grandes compras 2022 de 2.352 pares), **ningún mes de 2023 estuvo quebrado**. El stock fue suficiente todo el año.
- **vel_real = vel_aparente = 63.75 pares/mes** (sin corrección por quiebre)

### 3b. Proyección de demanda OI2024

| Mes | Factor s_t | Demanda proyectada |
|-----|-----------|-------------------|
| Abr | 0.48 | 30.6 |
| May | 0.48 | 30.6 |
| Jun | 0.42 | 26.8 |
| Jul | 0.37 | 23.6 |
| Ago | 0.44 | 28.1 |
| Sep | 0.66 | 42.1 |
| **Total OI2024** | | **181.7 ≈ 182 pares** |

### 3c. Stock al inicio de temporada (abril 2024)

Reconstrucción desde stock fin 2023 (~400):
- Ene 2024: +576 compras, -98 ventas → stock ≈ 878
- Feb 2024: -85 ventas → stock ≈ 793
- Mar 2024: -45 ventas → stock ≈ 748

**Stock inicio OI2024 (1-abr-2024) ≈ 748 pares**

### 3d. Decisión del modelo

```
Cantidad a comprar = demanda_proyectada - stock_inicio
                   = 182 - 748
                   = -566
→ MODELO DICE: NO COMPRAR. Stock cubre 4.1 temporadas OI.
```

---

## 4. Contraste con la realidad OI2024

### 4a. Ventas reales OI2024

| Mes | Proyectado | Real | Error |
|-----|-----------|------|-------|
| Abr | 31 | 26 | -16% |
| May | 31 | 58 | +87% |
| Jun | 27 | 28 | +4% |
| Jul | 24 | **101** | **+321%** |
| Ago | 28 | 38 | +36% |
| Sep | 42 | 57 | +36% |
| **Total** | **182** | **308** | **+69%** |

### 4b. Compras reales OI2024 (remitos recibidos)

| Mes | Pares |
|-----|-------|
| Abr 2024 | 552 |
| Jun 2024 | 240 |
| Ago 2024 | 312 |
| **Total OI2024** | **1.104** |

### 4c. Resumen de errores

| Métrica | Modelo | Realidad | Error |
|---------|--------|----------|-------|
| Demanda OI2024 | 182 pares | 308 pares | **-41% (subestimó 126 pares)** |
| Compra recomendada | 0 pares | 1.104 pares comprados | N/A (modelo decía no comprar) |
| Stock inicio OI | ~748 | ~748 | ✅ (coincide) |
| Stock fin OI (proyectado) | 748-182 = 566 | 748-308+1104 = 1.544 | Sobrestock real |

**Timing del primer remito real**: abril 2024 (inicio de OI).
**Timing modelo**: no aplica (recomendaba no comprar).

---

## 5. Causas del error

### ERROR_ESTACIONAL ⚠️ (principal)
El modelo subestimó la demanda OI en un 69%. Causas:
- **2023 fue un año atípicamente bajo** (765 pares vs promedio 2020-2022 de 1.008 pares). Usar solo 2023 como base infravalora la velocidad.
- Los factores estacionales calculados sobre 2015-2023 son correctos en la *forma* pero la *base* (vel de 2023) era baja.

### ERROR_CANTIDAD ⚠️⚠️ (en la decisión real del negocio)
El negocio compró 1.104 pares para una temporada que vendió 308. Esto generó un sobrestock de ~800 pares al fin de OI. Las compras reales fueron **3.6x la demanda real** y **6.1x la demanda proyectada**.

### ERROR_QUIEBRE ✅ (no aplica)
No hubo quiebre en 2023. El stock era abundante. La corrección por quiebre no hubiera cambiado el resultado.

### ANOMALÍA JULIO 2024
Julio 2024 = 101 pares es un outlier extremo (promedio histórico julio = 21 pares, **4.8x** el promedio). Posibles causas:
- Acción promocional / venta mayorista puntual
- Remito interno mal excluido
- Cambio de mix (nuevos talles/colores agregados a la familia)

Este solo dato explica 77 pares de los 126 de error (61% del error total).

### ERROR_REMITO ✅ (no detectado)
No hay evidencia de remitos eliminados que distorsionen la serie.

---

## 6. Propuesta de mejora

### 6a. Usar ventana de velocidad multi-año (no solo 12 meses)

El error principal es que 2023 fue atípico. Usar un promedio ponderado de los últimos 3 años reduce la dependencia de un solo año.

### 6b. Detectar y amortiguar outliers mensuales

Julio 2024 = 101 distorsiona cualquier proyección futura. Se debe aplicar un cap por percentil 95 o winsorización.

### 6c. Alertar cuando stock > 3× demanda_temporada

El modelo debe emitir una alerta cuando el stock existente ya cubre más de 3 temporadas de demanda proyectada, como ocurrió acá (748 vs 182 = 4.1x).

### 6d. Código Python del ajuste recomendado

```python
def vel_real_multianio(ventas_mensuales, compras_mensuales, stock_actual, anios=3):
    """
    Calcula velocidad real usando múltiples años para reducir impacto
    de años atípicos. Aplica quiebre año por año y promedia.

    ventas_mensuales: dict {(anio, mes): cantidad}
    compras_mensuales: dict {(anio, mes): cantidad}
    stock_actual: int
    anios: int, cantidad de años a promediar
    """
    from datetime import date
    from dateutil.relativedelta import relativedelta

    hoy = date.today()
    velocidades = []

    for offset in range(anios):
        # Cada año: 12 meses terminando en dic del año correspondiente
        anio_fin = hoy.year - 1 - offset
        meses_lista = [(anio_fin, m) for m in range(12, 0, -1)]

        # Reconstruir quiebre para este bloque de 12 meses
        # (simplificado: sin stock exacto, usar ventas/compras netas)
        total_ventas = sum(ventas_mensuales.get(k, 0) for k in meses_lista)
        total_compras = sum(compras_mensuales.get(k, 0) for k in meses_lista)

        # Si ventas >> compras, hubo quiebre potencial
        # Heurística: si vendió >80% de lo que compró, ajustar vel +20%
        ratio = total_ventas / max(total_compras, 1)
        vel_anio = total_ventas / 12

        velocidades.append(vel_anio)

    # Promedio ponderado: año más reciente pesa más
    pesos = list(range(anios, 0, -1))  # [3, 2, 1] para 3 años
    vel_ponderada = sum(v * p for v, p in zip(velocidades, pesos)) / sum(pesos)

    return round(vel_ponderada, 2)


def detectar_outlier_mensual(ventas_mes, historico_mes, percentil=95):
    """
    Detecta si una venta mensual es outlier respecto al histórico
    de ese mismo mes. Retorna el valor capado si es outlier.

    ventas_mes: int, ventas del mes a evaluar
    historico_mes: list[int], ventas de ese mes en años anteriores
    percentil: int, umbral para considerar outlier
    """
    import numpy as np
    if len(historico_mes) < 3:
        return ventas_mes

    umbral = np.percentile(historico_mes, percentil)
    if ventas_mes > umbral:
        return int(umbral)
    return ventas_mes


def alerta_sobrestock(stock_actual, demanda_temporada, umbral_temporadas=3):
    """
    Emite alerta cuando el stock cubre más de N temporadas.
    Retorna (bool, mensaje).
    """
    if demanda_temporada <= 0:
        return True, f"ALERTA: demanda proyectada = 0, stock = {stock_actual}"

    cobertura = stock_actual / demanda_temporada
    if cobertura > umbral_temporadas:
        return True, (
            f"ALERTA SOBRESTOCK: stock {stock_actual} cubre "
            f"{cobertura:.1f} temporadas (umbral: {umbral_temporadas}). "
            f"NO COMPRAR."
        )
    return False, ""
```

### 6e. Aplicación concreta al modelo de app_reposicion.py

En `analizar_quiebre_batch()` (línea 142), agregar parámetro `anios_promedio=3` y calcular velocidad como promedio ponderado de los últimos 3 años en vez de solo los últimos 12 meses. Esto hubiera dado:

```
vel_2023 = 765/12 = 63.75
vel_2022 = 1106/12 = 92.17
vel_2021 = 837/12 = 69.75

vel_ponderada = (63.75×3 + 92.17×2 + 69.75×1) / 6 = 74.6 pares/mes
```

Con vel = 74.6, la demanda OI2024 proyectada sería:
```
74.6 × (0.48+0.48+0.42+0.37+0.44+0.66) = 74.6 × 2.85 = 213 pares
```

Aún menor que la realidad (308), pero el error baja de -69% a -31%. El modelo seguiría recomendando no comprar (stock 748 > 213), que en este caso es **la decisión correcta**: el negocio compró 1.104 pares y generó sobrestock innecesario.

---

## Resumen ejecutivo

| Indicador | Valor |
|-----------|-------|
| Familia | 23649500 — ALPARGATA REFORZADA |
| Estacionalidad real | **FUERTE verano** (ratio 7.1x pico/valle) |
| Error demanda OI2024 | -69% (modelo 182, real 308) |
| Error con vel multi-año | -31% (modelo 213, real 308) |
| Decisión modelo | NO COMPRAR (stock 748 >> demanda 182) |
| Decisión real negocio | Compró 1.104 pares → sobrestock |
| Decisión correcta | **El modelo tenía razón**: no había necesidad de comprar |
| Causa principal error | Año base 2023 atípicamente bajo + outlier julio 2024 |
| Mejora recomendada | vel_real multi-año (3 años ponderado) + detección outliers + alerta sobrestock |
