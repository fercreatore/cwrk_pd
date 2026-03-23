# Backtesting: IMPERMEABILIZANTE 7113 (familia 63471130)

> Fecha: 2026-03-23
> Período analizado: jun 2017 — mar 2026
> Total histórico: ~2184 pares vendidos

---

## Serie histórica de ventas mensuales

| Mes | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|-----|------|------|------|------|------|------|------|------|------|------|
| Ene |   -  |    4 |    3 |   -  |    3 |   -  |    8 |    5 |   17 |   10 |
| Feb |   -  |    9 |   -  |   -  |    9 |   19 |   14 |   19 |   31 |   22 |
| Mar |   -  |    9 |    1 |   -  |   15 |    7 |    3 |   22 |   45 |   27 |
| Abr |   -  |    9 |    1 |   -  |   20 |    2 |   27 |   24 |   71 |   -  |
| May |   -  |   15 |   -  |   -  |   35 |   55 |   58 |   49 |   87 |   -  |
| Jun |   27 |    1 |   -  |   -  |   13 |   50 |   32 |   54 |  122 |   -  |
| Jul |   24 |    5 |   -  |   -  |    1 |   23 |   70 |   72 |  109 |   -  |
| Ago |   45 |   28 |   -  |   -  |   12 |   63 |   14 |   34 |   41 |   -  |
| Sep |   15 |   30 |   -  |    1 |   23 |   48 |   20 |   33 |   18 |   -  |
| Oct |   12 |   13 |   -  |    5 |   34 |   11 |   24 |   20 |   51 |   -  |
| Nov |    9 |   20 |   -  |    4 |   10 |    6 |   14 |   36 |   20 |   -  |
| Dic |    7 |    7 |   -  |    6 |    1 |   23 |    9 |   31 |   28 |   -  |
| **TOTAL** | **139** | **150** | **5** | **16** | **176** | **307** | **293** | **399** | **640** | **59** |

**Observaciones**:
- 2019 y 2020 prácticamente sin ventas (crisis/COVID + quiebre de stock total)
- Tendencia de crecimiento acelerado: 176→307→293→399→640
- 2025 muestra un salto del 60% vs 2024, probablemente por mejor abastecimiento

---

## Factor estacional

Calculado sobre años completos con actividad: 2018, 2021, 2022, 2023, 2024, 2025.
Promedio mensual global: **27.3 pares**.

| Mes | Promedio | Factor | Clasificación |
|-----|----------|--------|---------------|
| Ene |      6.2 |   0.23 | VALLE |
| Feb |     16.8 |   0.62 | Bajo |
| Mar |     16.8 |   0.62 | Bajo |
| Abr |     25.5 |   0.93 | Normal |
| May |     49.8 |   1.83 | **PICO** |
| Jun |     45.3 |   1.66 | **PICO** |
| Jul |     46.7 |   1.71 | **PICO** |
| Ago |     32.0 |   1.17 | Alto |
| Sep |     28.7 |   1.05 | Normal |
| Oct |     25.5 |   0.93 | Normal |
| Nov |     17.7 |   0.65 | Bajo |
| Dic |     16.5 |   0.60 | Bajo |

**Perfil**: Producto con estacionalidad otoño-invierno (pico mayo-julio), coherente con impermeabilizante. Valle fuerte en enero.

---

## Simulación OI2024 vs Realidad

### Inputs del modelo (datos hasta dic 2023)

| Métrica | Valor |
|---------|-------|
| Vel aparente (ventas 2023 / 12) | 24.4 pares/mes |
| Meses quebrados 2023 | **12/12 (100%)** |
| Vel real (sin quiebre) | **0.0 pares/mes** |
| Stock inicio OI2024 (reconstruido) | **-1,097 pares** |

### Resultado del modelo

| Métrica | Modelo | Realidad | Error |
|---------|--------|----------|-------|
| Demanda OI2024 (abr-sep) | **0 pares** | 266 pares | **-100%** |
| Compra recomendada | 1,097 pares (reponer stock negativo) | 576 pares | +90.5% |
| Timing pedido | Marzo 2024 | Abril 2024 | ~0 meses |

### Detalle mensual OI2024

| Mes | Modelo | Real | Error |
|-----|--------|------|-------|
| Abr |      0 |   24 |   -24 |
| May |      0 |   49 |   -49 |
| Jun |      0 |   54 |   -54 |
| Jul |      0 |   72 |   -72 |
| Ago |      0 |   34 |   -34 |
| Sep |      0 |   33 |   -33 |

### Compras reales 2024

| Mes | Compras |
|-----|---------|
| Ene |      36 |
| Feb |      36 |
| Abr |     120 |
| May |     120 |
| Jun |     168 |
| Ago |      96 |
| Sep |      72 |
| Oct |      72 |
| Dic |      72 |
| **Total** | **792** |

---

## Causas del error

### ERROR_QUIEBRE: CRÍTICO — El modelo colapsa completamente

La reconstrucción de stock hacia atrás genera stock **perpetuamente negativo** desde 2021 hasta enero 2026. Esto marca TODOS los meses como "QUEBRADO", resultando en `vel_real = 0`.

**Causa raíz**: La reconstrucción acumula un déficit enorme porque:
1. La familia tiene muchos SKUs (talles, colores) con movimientos cruzados
2. Existen ajustes de inventario, devoluciones y movimientos internos NO capturados en `compras1 WHERE operacion='+'`
3. El stock real nunca fue -1,097 — el local siempre tuvo mercadería en góndola

**Consecuencia**: El modelo produce vel_real=0 y demanda=0, que es absurdo para un producto que vendió 293 pares en 2023.

### ERROR_CANTIDAD: ALTO (+90.5%)

Cuando vel_real=0, la compra recomendada se basa solo en "reponer" el stock negativo fantasma (1,097 pares), no en demanda proyectada. El número es irrelevante porque se basa en stock ficticio.

### ERROR_ESTACIONAL: NO APLICA

El factor estacional no llega a aplicarse porque vel_real=0 anula toda la proyección.

### ERROR_TIMING: CORRECTO

El timing del modelo (marzo) coincide razonablemente con la realidad (primer remito abril).

### ERROR_REMITO: POSIBLE

No se detectaron remitos eliminados, pero la ausencia de operaciones de ajuste en el dataset de compras contribuye al stock negativo acumulado.

---

## Diagnóstico: Por qué el stock reconstruido es siempre negativo

La familia 63471130 vendió **2,184+ pares** en 10 años, pero el total de compras registradas (`operacion='+'`) es significativamente menor que las ventas totales. Esto indica que existen entradas de mercadería por vías no capturadas:

- Ajustes de inventario positivos
- Transferencias entre depósitos
- Comprobantes con operación distinta de '+'
- Stock inicial no registrado como compra

El algoritmo de reconstrucción hacia atrás acumula este déficit mes a mes, generando un "agujero negro" de stock negativo que invalida completamente el análisis de quiebre.

---

## Propuesta de mejora

### 1. Fallback cuando 100% de meses están quebrados

Si todos los meses del período de análisis son "QUEBRADO" (stock reconstruido ≤ 0), el análisis de quiebre no aporta información útil. En ese caso, usar la **velocidad aparente** como mejor estimador disponible.

### 2. Usar ventana más corta para reconstrucción

En lugar de reconstruir hasta el inicio de los datos, limitar la reconstrucción a los últimos 24 meses. Esto reduce la acumulación de error en la reconstrucción.

### 3. Validar stock reconstruido contra stock real periódico

Si el stock reconstruido diverge significativamente del stock real conocido en algún punto, anclar la reconstrucción a ese punto.

### Código Python del ajuste recomendado

```python
# En app_reposicion.py, dentro de analizar_quiebre_batch() o equivalente:

def calcular_vel_real_con_fallback(ventas_mensuales, stock_reconstruido, meses_analisis=12):
    """
    Calcula velocidad real con análisis de quiebre.
    FALLBACK: si todos los meses están quebrados, usa vel_aparente
    con factor de ajuste por tendencia.
    """
    total_ventas = 0
    meses_ok = 0
    ventas_ok = 0

    for mes_key, ventas in ventas_mensuales.items():
        total_ventas += ventas
        stock_ini = stock_reconstruido.get(mes_key, 0)
        if stock_ini > 0:
            meses_ok += 1
            ventas_ok += ventas

    vel_aparente = total_ventas / meses_analisis if meses_analisis > 0 else 0

    if meses_ok == 0:
        # FALLBACK: 100% quebrado → vel_real no es calculable
        # Usar vel_aparente ajustada por tendencia interanual
        #
        # Justificación: si el stock reconstruido es siempre negativo,
        # la reconstrucción es poco confiable (movimientos no capturados).
        # La vel_aparente subestima, pero es mejor que 0.
        #
        # Factor 1.15 = ajuste conservador por subestimación típica
        # cuando hay quiebre parcial no detectado.
        vel_real = vel_aparente * 1.15
        confianza = "BAJA"
        metodo = "fallback_aparente"
    elif meses_ok < meses_analisis * 0.25:
        # Menos del 25% de meses con stock → vel_real poco confiable
        vel_real_calc = ventas_ok / meses_ok
        vel_real = max(vel_real_calc, vel_aparente)
        confianza = "MEDIA"
        metodo = "blend_max"
    else:
        # Caso normal: suficientes meses con stock
        vel_real = ventas_ok / meses_ok
        confianza = "ALTA"
        metodo = "quiebre_standard"

    return {
        "vel_real": vel_real,
        "vel_aparente": vel_aparente,
        "meses_ok": meses_ok,
        "meses_total": meses_analisis,
        "confianza": confianza,
        "metodo": metodo,
    }


# Ejemplo para familia 63471130 con datos 2023:
# vel_aparente = 24.4 → fallback vel_real = 24.4 * 1.15 = 28.1
# Demanda OI2024 proyectada = 28.1 * (0.93+1.83+1.66+1.71+1.17+1.05) = 28.1 * 8.35 = 234.6
# vs realidad: 266 pares → error: -11.8% (MUCHO mejor que -100%)
```

### Resultado esperado con el fix

| Métrica | Modelo actual | Modelo mejorado | Realidad |
|---------|--------------|-----------------|----------|
| Vel_real | 0.0 | 28.1 (fallback) | ~33.3 (real 2024) |
| Demanda OI2024 | 0 | 235 pares | 266 pares |
| Error demanda | -100% | **-11.8%** | — |
| Confianza | — | BAJA (señalizada) | — |

El error pasa de **-100% (inutilizable)** a **-11.8% (aceptable)**.

---

## Conclusión

La familia IMPERMEABILIZANTE 7113 expone un **bug crítico** del modelo de reposición: cuando la reconstrucción de stock hacia atrás genera stock negativo en todos los meses (por movimientos no capturados en compras1), el análisis de quiebre produce `vel_real=0` y la proyección colapsa a cero.

**Acción inmediata**: implementar el fallback `vel_aparente * 1.15` cuando el 100% de los meses están quebrados, con flag de confianza "BAJA" visible al usuario.

**Acción futura**: investigar por qué las compras registradas (`operacion='+'`) no cubren las ventas históricas — probablemente faltan ajustes de inventario o transferencias en la query.
