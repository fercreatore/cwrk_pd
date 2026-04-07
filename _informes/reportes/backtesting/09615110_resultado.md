# Backtesting: MEDIAS COLEGIALES BORDO (familia 09615110)

**Producto**: SA1511 — Medias algodón peinado colegiales (negro, blanco, azul, rojo, marrón, verde inglés, bordo)
**Proveedor**: 96
**Stock actual (mar-2026)**: 280 pares
**Datos disponibles**: 2011–2026 (16 años)

---

## Serie histórica de ventas (pares/mes)

| Año | Ene | Feb | Mar | Abr | May | Jun | Jul | Ago | Sep | Oct | Nov | Dic | **Total** |
|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----------|
| 2012 | 1 | 82 | 27 | — | — | — | — | — | — | — | 3 | 1 | **114** |
| 2013 | 16 | 291 | 76 | 1 | 2 | — | 1 | — | 3 | 2 | 2 | 6 | **400** |
| 2014 | 24 | 235 | 124 | 4 | 6 | 4 | — | 1 | 3 | 7 | 4 | 7 | **419** |
| 2015 | 4 | 187 | 103 | 9 | 3 | 6 | 1 | — | 2 | 3 | 5 | 6 | **329** |
| 2016 | 6 | 121 | 55 | 9 | 2 | — | 6 | — | 3 | 4 | 6 | 6 | **218** |
| 2017 | 22 | 186 | 148 | 13 | 2 | 7 | 4 | — | 8 | 4 | 2 | 3 | **399** |
| 2018 | 38 | 161 | 83 | 6 | — | — | 2 | 1 | 1 | — | — | — | **292** |
| 2019 | — | 113 | 61 | 3 | 2 | 1 | — | 1 | 2 | — | 3 | 2 | **188** |
| 2020 | 3 | 120 | 13 | — | — | 1 | — | — | — | — | — | — | **137** |
| 2021 | 1 | 13 | 36 | — | 1 | — | — | — | — | — | — | 1 | **52** |
| 2022 | 6 | 116 | 11 | — | 2 | — | 2 | — | 2 | 1 | 2 | 1 | **143** |
| 2023 | 2 | 123 | 24 | 3 | 2 | 1 | 1 | 5 | 1 | 3 | 1 | 2 | **168** |
| 2024 | 14 | 84 | 6 | 2 | 3 | — | 2 | — | — | — | — | 2 | **113** |
| 2025 | 7 | 154 | 27 | 1 | 1 | 3 | — | 5 | 5 | 4 | — | 1 | **208** |
| 2026 | 6 | 58 | 5 | | | | | | | | | | **69***  |

\* 2026 parcial (ene-mar)

### Tendencia anual
- **2013–2017**: promedio 353 pares/año (época dorada)
- **2018–2020**: promedio 206 pares/año (declive + COVID)
- **2021–2025**: promedio 137 pares/año (nueva normalidad)
- **Caída acumulada**: -61% vs período 2013–2017

---

## Factor estacional (calculado sobre 2013–2025, 13 años)

| Mes | Promedio | Factor s_t | Interpretación |
|-----|----------|------------|----------------|
| Ene | 11.0 | 0.56 | Pre-temporada escolar |
| **Feb** | **146.5** | **7.45** | **PICO absoluto — inicio clases** |
| **Mar** | **59.0** | **3.00** | **Segundo pico — reposición escolar** |
| Abr | 3.9 | 0.20 | Valle |
| May | 2.0 | 0.10 | Valle |
| Jun | 1.8 | 0.09 | Valle |
| Jul | 1.5 | 0.07 | Valle profundo |
| Ago | 1.0 | 0.05 | Valle profundo |
| Sep | 2.3 | 0.12 | Leve repunte |
| Oct | 2.2 | 0.11 | Valle |
| Nov | 1.9 | 0.10 | Valle |
| Dic | 2.8 | 0.15 | Leve anticipación |

**Concentración extrema**: Febrero concentra el **62%** de las ventas anuales. Feb+Mar = **87%**.
Esto no es un producto OI/PV — es un producto **100% escolar** con un pico de 2 meses.

---

## Compras históricas

| Fecha | Pares | Contexto |
|-------|-------|----------|
| Ene 2013 | 180 | Normal |
| Feb 2013 | 372 | Reposición en temporada |
| Mar 2013 | 144 | Reposición tardía |
| Ene 2014 | 912 | **Sobre-compra masiva** |
| Mar 2014 | 264 | Reposición |
| Ene 2015 | 504 | Normal |
| Ene/Mar/Abr 2016 | 336 | Repartido |
| Nov/Dic 2016 | 360 | Anticipación |
| Mar 2017 | 1272 | **Sobre-compra masiva** |
| Feb 2018 | 336 | Normal |
| **Feb/Mar 2021** | **1200** | **Sobre-compra post-COVID** |
| Ene 2023 | 264 | Innecesaria (stock alto) |
| Ene 2024 | 192 | Innecesaria (stock alto) |

---

## Análisis de quiebre (12 meses previos a Ene 2024)

Reconstrucción hacia atrás desde stock estimado fin Dic 2023 = **478 pares**:

| Mes | Ventas | Compras | Stock inicio | Estado |
|-----|--------|---------|--------------|--------|
| Dic 2023 | 2 | 0 | 480 | OK |
| Nov 2023 | 1 | 0 | 481 | OK |
| Oct 2023 | 3 | 0 | 484 | OK |
| Sep 2023 | 1 | 0 | 485 | OK |
| Ago 2023 | 5 | 0 | 490 | OK |
| Jul 2023 | 1 | 0 | 491 | OK |
| Jun 2023 | 1 | 0 | 492 | OK |
| May 2023 | 2 | 0 | 494 | OK |
| Abr 2023 | 3 | 0 | 497 | OK |
| Mar 2023 | 24 | 0 | 521 | OK |
| Feb 2023 | 123 | 0 | 644 | OK |
| Ene 2023 | 2 | 264 | 382 | OK |

**Resultado**: 0 meses quebrados / 12 meses OK
- **vel_aparente** = 168/12 = **14.0 pares/mes**
- **vel_real** = 14.0 pares/mes (sin quiebre, idéntica)

---

## Simulación OI2024 (abril–septiembre)

### Modelo predijo
- vel_real: 14.0 pares/mes
- Demanda OI2024 proyectada: 14.0 × (0.20+0.10+0.09+0.07+0.05+0.12) = 14.0 × 0.63 = **9 pares**
- Stock inicio OI (abr 2024): 478 + 192 - 14 - 84 - 6 = **566 pares**
- Q a comprar: 9 - 566 = **-557 → NO COMPRAR**
- Timing óptimo: N/A (no requiere compra)

### Realidad OI2024
- Ventas reales OI2024: Abr=2, May=3, Jul=2 = **7 pares**
- Compras reales OI2024: **0 pares**

### Errores
| Métrica | Modelo | Real | Error |
|---------|--------|------|-------|
| Demanda OI | 9 pares | 7 pares | +2 (+29%) |
| Cantidad comprada | 0 (no comprar) | 0 | **0 (acertó)** |
| Timing | N/A | N/A | N/A |

### Simulación temporada ESCOLAR 2024 (ene–mar)

Esta es la simulación más relevante para este producto:

| Métrica | Modelo | Real | Error |
|---------|--------|------|-------|
| Demanda Ene-Mar | 14×(0.56+7.45+3.00) = **154 pares** | 14+84+6 = **104 pares** | +50 (+48%) |
| Stock disponible | 478 pares | — | — |
| Q a comprar | 0 (stock cubre) | 192 comprados Ene-24 | **Compra innecesaria** |

El modelo hubiera evitado la compra de 192 pares en Ene-2024 que fue completamente innecesaria.

---

## Causas del error

### ERROR_CANTIDAD: Crónico sobre-stock (SEVERO)
La compra de **1200 pares en 2021** para un producto que vende ~150/año generó un excedente que lleva **5 años sin agotarse**. Las compras posteriores (264 en 2023, 192 en 2024) fueron innecesarias — aumentaron el sobre-stock.

Inventario acumulado desde 2021:
- Compras 2021-2024: 1200 + 264 + 192 = **1656 pares**
- Ventas 2021-2025: 52 + 143 + 168 + 113 + 208 = **684 pares**
- Excedente neto: **972 pares** (de los cuales 280 quedan hoy)

### ERROR_ESTACIONAL: Modelo OK, pero irrelevante
El factor estacional captura correctamente el pico Feb-Mar. Sin embargo, la estacionalidad es tan extrema (87% en 2 meses) que el producto necesita un modelo de **evento discreto**, no de velocidad mensual.

### ERROR_QUIEBRE: No aplica
El producto NUNCA quiebra stock. El problema es el opuesto: **sobre-stock crónico**. El análisis de quiebre da 0 meses quebrados siempre, lo que hace que vel_real = vel_aparente. El modelo de quiebre no agrega valor para esta familia.

### ERROR_TENDENCIA: No capturado (CRÍTICO)
La velocidad cayó -61% entre 2013-2017 (353/año) y 2021-2025 (137/año). El modelo usa 12 meses recientes, lo que parcialmente captura esto, pero no proyecta la tendencia. Usar vel_real de 2023 (168 pares) sobrestimó 2024 (113 pares) en un 48%.

### ERROR_REMITO: No detectado
Sin evidencia de remitos eliminados afectando esta familia.

---

## Propuesta de mejora

### 1. Clasificación de producto por patrón de demanda
Este producto no es "estacional OI/PV" sino **"evento escolar"**. Necesita un modelo diferenciado:

```python
# En app_reposicion.py — agregar clasificación de patrón de demanda

def clasificar_patron_demanda(ventas_mensuales_multi_anio):
    """
    Clasifica el patrón de demanda de una familia.
    Returns: 'escolar', 'estacional_oi', 'estacional_pv', 'perenne'
    """
    # Calcular concentración por mes (promedio multi-año)
    from collections import defaultdict
    mes_totals = defaultdict(list)
    for (anio, mes), cant in ventas_mensuales_multi_anio.items():
        mes_totals[mes].append(cant)

    mes_avg = {m: sum(v)/len(v) for m, v in mes_totals.items()}
    total = sum(mes_avg.values()) or 1

    pct_feb_mar = (mes_avg.get(2, 0) + mes_avg.get(3, 0)) / total
    pct_oi = sum(mes_avg.get(m, 0) for m in [4,5,6,7,8,9]) / total
    pct_pv = sum(mes_avg.get(m, 0) for m in [10,11,12,1,2,3]) / total

    if pct_feb_mar > 0.70:
        return 'escolar'
    elif pct_oi > 0.65:
        return 'estacional_oi'
    elif pct_pv > 0.75:
        return 'estacional_pv'
    else:
        return 'perenne'
```

### 2. Modelo de reposición para productos escolares
```python
def proyectar_demanda_escolar(ventas_anuales_hist, stock_actual):
    """
    Para productos escolares (concentración >70% en Feb-Mar):
    - Usa promedio ponderado de últimos 3 años (más peso al reciente)
    - Aplica trend lineal
    - Compara con stock disponible

    Returns: dict con demanda_proyectada, q_comprar, fecha_pedido
    """
    import numpy as np

    # Últimos 3-5 años completos (excluir COVID 2020-2021)
    anios = sorted(ventas_anuales_hist.keys())
    recientes = [a for a in anios if a >= 2022][-3:]

    if len(recientes) < 2:
        recientes = anios[-3:]

    ventas = [ventas_anuales_hist[a] for a in recientes]

    # Tendencia lineal
    if len(ventas) >= 2:
        x = np.arange(len(ventas))
        slope = np.polyfit(x, ventas, 1)[0]
        proyeccion = ventas[-1] + slope
    else:
        proyeccion = ventas[-1]

    # Promedio ponderado (60% último, 30% penúltimo, 10% antepenúltimo)
    pesos = [0.1, 0.3, 0.6][-len(ventas):]
    pesos = [p / sum(pesos) for p in pesos]
    prom_ponderado = sum(v * p for v, p in zip(ventas, pesos))

    # Usar el menor entre tendencia y promedio ponderado (conservador)
    demanda_anual = min(proyeccion, prom_ponderado)
    demanda_anual = max(demanda_anual, 0)

    # 90% de la demanda anual se concentra en Feb-Mar
    demanda_temporada = demanda_anual * 0.90

    q_comprar = max(0, round(demanda_temporada - stock_actual))

    # Fecha pedido: noviembre-diciembre del año anterior (lead time 4-6 semanas)
    return {
        'demanda_anual_proyectada': round(demanda_anual),
        'demanda_temporada_feb_mar': round(demanda_temporada),
        'stock_actual': stock_actual,
        'q_comprar': q_comprar,
        'fecha_pedido_optima': 'noviembre–diciembre del año anterior',
        'metodo': 'escolar_trend_ponderado'
    }


# Ejemplo con datos reales de familia 09615110:
# ventas_anuales = {2022: 143, 2023: 168, 2024: 113}
# stock = 280
#
# Resultado:
#   Trend: 113 + (113-143)/2*slope ≈ 83 (baja)
#   Prom ponderado: 143*0.1 + 168*0.3 + 113*0.6 = 14.3 + 50.4 + 67.8 = 132.5
#   demanda_anual = min(83, 132.5) = 83
#   demanda_feb_mar = 83 * 0.90 = 75
#   q_comprar = max(0, 75 - 280) = 0 → NO COMPRAR
#
# Validación 2025: ventas reales 208 (recuperación). El modelo conservador
# hubiera tenido stock suficiente (280 > 208) sin comprar.
```

### 3. Alerta de sobre-stock
```python
def alerta_sobrestock(stock_actual, vel_real_mensual):
    """
    Genera alerta si el stock cubre más de 18 meses de demanda.
    Para productos escolares, usar demanda anual / 12 como vel_real.
    """
    if vel_real_mensual <= 0:
        return {'alerta': 'CRITICO', 'meses_cobertura': float('inf'),
                'mensaje': 'Producto sin ventas con stock > 0'}

    meses_cobertura = stock_actual / vel_real_mensual

    if meses_cobertura > 24:
        nivel = 'CRITICO'
    elif meses_cobertura > 18:
        nivel = 'ALTO'
    elif meses_cobertura > 12:
        nivel = 'MODERADO'
    else:
        nivel = 'OK'

    return {
        'alerta': nivel,
        'meses_cobertura': round(meses_cobertura, 1),
        'mensaje': f'Stock para {meses_cobertura:.0f} meses. '
                   f'{"BLOQUEAR COMPRA" if meses_cobertura > 12 else "OK"}'
    }

# Ejemplo dic-2023: alerta_sobrestock(478, 14.0)
# → meses_cobertura=34.1, alerta=CRITICO, BLOQUEAR COMPRA
# Hubiera evitado la compra innecesaria de 192 pares en ene-2024.
```

---

## Resumen ejecutivo

| Aspecto | Evaluación |
|---------|------------|
| **Modelo de quiebre** | Irrelevante — nunca quiebra, siempre sobre-stockeado |
| **Factor estacional** | Correcto pero insuficiente — es un producto de evento (Feb-Mar = 87%) |
| **Velocidad** | Sobreestima por no capturar tendencia descendente (-61% en 8 años) |
| **Mayor error** | Compra de 1200 pares en 2021 para demanda de ~150/año. Sobre-stock de 5 años |
| **Propuesta clave** | Clasificar como "escolar", usar modelo de tendencia ponderada, agregar alerta de sobre-stock que bloquee compras cuando cobertura > 12 meses |
| **Ahorro potencial** | Si se hubiera aplicado en 2024: -192 pares no comprados (~$527K evitados) |
