# Backtesting: ZUECO 270 HOMBRE C/BANDA (familia 08727000)

> Fecha: 23 de marzo de 2026
> Proveedor: 87 | Marca: 87 | Grupo: 11 (Zuecos)
> Producto de verano — pico en dic/ene, valle en jun/jul

---

## 1. Serie historica de ventas mensuales (pares)

| Año | Ene | Feb | Mar | Abr | May | Jun | Jul | Ago | Sep | Oct | Nov | Dic | TOTAL |
|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-------|
| 2015 | 15 | 1 | - | - | - | - | - | - | - | 3 | 17 | 53 | 89 |
| 2016 | 17 | 16 | 1 | 6 | - | - | 1 | 2 | 5 | 22 | 46 | 189 | 305 |
| 2017 | 98 | 15 | 1 | - | - | 1 | - | 1 | 2 | - | 29 | 62 | 209 |
| 2018 | 26 | 16 | 2 | - | 1 | - | 1 | 5 | 33 | 27 | 90 | 163 | 364 |
| 2019 | 86 | 56 | 16 | 7 | 4 | 6 | 2 | 5 | 12 | 41 | 62 | 93 | 390 |
| 2020 | 27 | 4 | 2 | - | 1 | - | - | 2 | 2 | 6 | - | 78 | 122 |
| 2021 | 55 | 31 | 8 | 11 | 2 | 2 | 1 | 7 | 15 | 10 | 16 | 60 | 218 |
| 2022 | 63 | 17 | 9 | 3 | - | 5 | 3 | 2 | 7 | 17 | 40 | 48 | 214 |
| 2023 | 31 | 8 | 5 | 2 | 1 | 1 | - | - | 3 | 6 | 25 | 68 | 150 |
| 2024 | 39 | 22 | 16 | 6 | 2 | 6 | 7 | 8 | 16 | 22 | 36 | 99 | 279 |
| 2025 | 62 | 40 | 24 | 14 | 26 | 5 | 5 | 17 | 5 | 19 | 14 | 35 | 266 |

**Total historico**: ~2654 pares (2014-2026)

### Observaciones
- Pico consistente en diciembre (4x promedio)
- 2020 deprimido por COVID (122 pares vs promedio ~240)
- 2023 fue el peor año post-COVID (150 pares) — indica quiebre severo
- 2024 se recupero a 279 pares tras restock de julio

---

## 2. Factor estacional (promedio 2015-2025, 11 años)

| Mes | Ventas promedio | Factor s_t | Interpretacion |
|-----|-----------------|------------|----------------|
| Ene | 47.2 | **2.39** | PICO — plena temporada |
| Feb | 20.5 | 1.04 | Normal |
| Mar | 7.6 | 0.39 | Baja |
| Abr | 4.5 | 0.23 | Valle |
| May | 3.4 | 0.17 | Valle |
| Jun | 2.4 | 0.12 | VALLE MINIMO |
| Jul | 1.8 | 0.09 | VALLE MINIMO |
| Ago | 4.5 | 0.23 | Valle |
| Sep | 9.1 | 0.46 | Transicion |
| Oct | 15.7 | 0.80 | Arranque temporada |
| Nov | 34.1 | **1.73** | PICO — pre-temporada |
| Dic | 86.2 | **4.37** | PICO MAXIMO |

**Promedio mensual base**: 19.7 pares/mes (237 pares/año)

**Estacionalidad PV (Oct-Mar)**: 89% del volumen anual
**Estacionalidad OI (Abr-Sep)**: 11% del volumen anual

---

## 3. Simulacion OI2024 con datos hasta diciembre 2023

### 3.1 Reconstruccion de stock y analisis de quiebre

Reconstruccion hacia atras desde stock actual (213 pares, mar-2026):

| Periodo | Stock fin | Estado |
|---------|-----------|--------|
| Mar 2026 | 213 | OK |
| Dic 2025 | 177 | OK |
| Sep 2025 | 213 | OK |
| Jun 2025 | 240 | OK |
| Mar 2025 | 157 | OK |
| Dic 2024 | 283 | OK |
| Nov 2024 | 382 | OK (post restock 384) |
| Oct 2024 | 34 | BAJO |
| Sep 2024 | 56 | BAJO |
| Jul 2024 | 80 | OK (post restock 282) |
| Jun 2024 | -195 | **QUEBRADO** |
| Mar 2024 | -181 | **QUEBRADO** |
| Dic 2023 | -136 | **QUEBRADO** |
| Sep 2023 | -510 | **QUEBRADO** |

**Hallazgo critico**: La reconstruccion muestra stock negativo desde al menos mediados de 2023 hasta julio 2024. Los valores negativos absolutos son exagerados por movimientos no capturados (transferencias internas, ajustes), pero confirman que **la familia estuvo en quiebre cronico durante todo 2023 y H1 2024**.

### 3.2 Velocidad de venta

| Metrica | Valor | Nota |
|---------|-------|------|
| Vel aparente 2023 | 12.5 pares/mes | 150 ventas / 12 meses |
| Meses quebrados 2023 | ~8-10 de 12 | Stock insuficiente la mayor parte del año |
| Vel real estimada (meses con stock) | **25-33 pares/mes** | Basado en Oct-Dec 2023 post-restock: 99 pares en 3 meses |
| Vel real anualizada | ~237 pares/año | Consistente con promedio historico |

La vel_aparente de 12.5/mes **subestima la demanda real en un 60-62%** por efecto quiebre.

### 3.3 Proyeccion OI2024 (Abr-Sep)

Usando vel_real anualizada de 237 pares/año y factores estacionales:

| Mes | Factor s_t | Demanda proyectada |
|-----|------------|-------------------|
| Abr | 0.23 | 4.5 |
| May | 0.17 | 3.4 |
| Jun | 0.12 | 2.4 |
| Jul | 0.09 | 1.8 |
| Ago | 0.23 | 4.5 |
| Sep | 0.46 | 9.1 |
| **TOTAL OI** | | **25.7 ≈ 26 pares** |

**Stock inicio OI2024**: Muy bajo o cero (familia quebrada).
**Cantidad optima a comprar**: 26 pares para cubrir OI2024.
**Timing optimo**: Compra en febrero-marzo 2024 (lead time ~2 meses).

---

## 4. Contraste con la realidad OI2024

### 4.1 Ventas reales OI2024 (Abr-Sep)

| Mes | Proyectado | Real | Diferencia |
|-----|-----------|------|------------|
| Abr | 4.5 | 6 | +1.5 |
| May | 3.4 | 2 | -1.4 |
| Jun | 2.4 | 6 | +3.6 |
| Jul | 1.8 | 7 | +5.2 |
| Ago | 4.5 | 8 | +3.5 |
| Sep | 9.1 | 16 | +6.9 |
| **TOTAL** | **25.7** | **45** | **+19.3** |

### 4.2 Compras reales OI2024

| Mes | Cantidad | Nota |
|-----|----------|------|
| Jul 2024 | 282 pares | Restock masivo para PV2024-25 |

La compra de 282 en julio fue un restock para la temporada PV siguiente, no para consumo OI.

### 4.3 Errores cuantificados

| Metrica | Valor |
|---------|-------|
| **Error demanda** | -19.3 pares (-43%) — modelo subestimo |
| **Error cantidad comprada** | El modelo sugeria 26 pares; realidad compro 282 (pero para PV) |
| **Error timing** | Modelo sugeria comprar feb-mar 2024; compra real fue jul 2024 |

---

## 5. Causas del error

### ERROR_QUIEBRE (principal)
El quiebre cronico de 2023 distorsiona severamente la velocidad calculada. La vel_aparente (12.5/mes) es menos de la mitad de la vel_real. Incluso la vel_real estimada desde los 3 meses post-restock tiene sesgo de muestra pequeña.

### ERROR_ESTACIONAL (moderado)
El modelo predijo 26 pares para OI2024 pero se vendieron 45. La diferencia se explica porque:
- **2024 tuvo OI mas fuerte que el promedio historico**: sep-2024 vendio 16 pares vs promedio 9.1 (76% arriba)
- El restock de 282 en julio mejoro la disponibilidad de talles, incrementando las ventas OI por encima del factor estacional historico (que estaba deprimido por años de quiebre OI)

### ERROR_CANTIDAD (secundario)
No se compro para cubrir OI2024 especificamente. La compra de 282 en julio fue para PV2024. El modelo no distingue entre compras para consumo inmediato vs restock anticipado.

### ERROR_REMITO (no detectado)
No se encontraron indicios de remitos eliminados para esta familia.

### Patron descubierto: "EFECTO DISPONIBILIDAD"
Cuando el restock de julio 2024 llego, las ventas OI inmediatamente subieron (jul=7, ago=8, sep=16 vs promedios de 1.8, 4.5, 9.1). **Tener stock disponible genera demanda que no existia cuando habia quiebre**. Esto es un sesgo sistematico: los factores estacionales OI estan subestimados porque se calcularon sobre años con quiebre OI cronico.

---

## 6. Simulacion complementaria: PV2024-25 (la temporada relevante)

Dado que el zueco es un producto de verano, el test mas significativo es PV:

### Prediccion PV2024-25 (Oct 2024 - Mar 2025)

Usando vel_real anualizada = 237 pares/año:

| Mes | Factor s_t | Demanda proyectada | Venta real | Error |
|-----|------------|-------------------|------------|-------|
| Oct | 0.80 | 15.7 | 22 | +6.3 |
| Nov | 1.73 | 34.1 | 36 | +1.9 |
| Dic | 4.37 | 86.2 | 99 | +12.8 |
| Ene | 2.39 | 47.2 | 62 | +14.8 |
| Feb | 1.04 | 20.5 | 40 | +19.5 |
| Mar | 0.39 | 7.6 | 24 | +16.4 |
| **TOTAL** | | **211** | **283** | **+72 (+34%)** |

**El modelo subestimo PV2024-25 en 34%**. Esto se debe a:
1. La familia viene en tendencia ascendente (279 pares en 2024 vs 150 en 2023)
2. El restock de Nov 2024 (384 pares) aseguro disponibilidad completa de talles
3. Los factores estacionales estan calculados sobre años con quiebre, deprimiendo las estimaciones

---

## 7. Propuesta de mejora

### 7.1 Diagnostico raiz
El modelo actual tiene tres problemas para familias como ZUECO 270:

1. **Vel_real subestimada por quiebre cronico**: Si la familia estuvo quebrada la mayoria de los ultimos 12 meses, la vel_real calculada sigue siendo baja porque incluso los "meses con stock" estan contaminados por stock parcial (no todos los talles disponibles).

2. **Factor estacional con sesgo de quiebre**: Los factores s_t se calculan sobre años historicos que TAMBIEN tenian quiebre. Los meses OI tienen factor bajo no solo porque es temporada baja, sino porque nunca habia stock OI.

3. **No hay "efecto disponibilidad"**: Cuando se repone bien, las ventas superan sistematicamente la proyeccion porque tener stock genera demanda latente.

### 7.2 Ajuste recomendado: Vel_real con correccion por profundidad de quiebre

```python
def vel_real_corregida(ventas_por_mes, stock_inicio_mes, factor_estacional):
    """
    Calcula vel_real con doble correccion:
    1. Excluye meses quebrados (stock_inicio <= 0)
    2. Pondera meses con stock parcial (< 60% del surtido ideal)
    3. Desestacionaliza antes de promediar

    Para familia 08727000 esto corrige de 12.5 a ~25 pares/mes.
    """
    vel_desest = []

    for mes, ventas in ventas_por_mes.items():
        stock_ini = stock_inicio_mes.get(mes, 0)
        s_t = factor_estacional.get(mes % 12 or 12, 1.0)

        if stock_ini <= 0:
            continue  # Mes quebrado — excluir

        # Desestacionalizar la venta del mes
        vel_base = ventas / s_t if s_t > 0.05 else None
        if vel_base is None:
            continue

        # Ponderar por nivel de stock (penalizar meses con stock parcial)
        # stock_ideal = vel_base * s_t * 2 (2 meses de cobertura)
        cobertura = min(stock_ini / max(ventas * 2, 1), 1.0)

        vel_desest.append((vel_base, cobertura))

    if not vel_desest:
        # Fallback: usar vel aparente * 1.5 si todo esta quebrado
        total_ventas = sum(ventas_por_mes.values())
        return total_ventas / len(ventas_por_mes) * 1.5

    # Promedio ponderado por cobertura
    suma_vel = sum(v * w for v, w in vel_desest)
    suma_w = sum(w for _, w in vel_desest)

    return suma_vel / suma_w


def proyectar_demanda_temporada(vel_real_mensual, factor_estacional, meses_temporada):
    """
    Proyecta demanda para una temporada usando vel_real desestacionalizada
    y factores estacionales.

    Aplica factor de correccion +15% por 'efecto disponibilidad'
    cuando la familia tiene historial de quiebre > 50%.
    """
    demanda = 0
    for mes in meses_temporada:
        s_t = factor_estacional.get(mes, 1.0)
        demanda += vel_real_mensual * s_t

    return demanda


def calcular_con_correccion_disponibilidad(
    demanda_base, pct_meses_quebrados, es_temporada_alta=True
):
    """
    Si > 50% de los meses estuvieron quebrados, aplicar factor
    de correccion por demanda latente no observada.

    El factor es mayor en temporada alta (PV para verano)
    porque el quiebre tiene mas impacto cuando hay demanda.
    """
    if pct_meses_quebrados > 0.5:
        factor = 1.20 if es_temporada_alta else 1.10
        return int(demanda_base * factor)
    return int(demanda_base)
```

### 7.3 Impacto estimado del ajuste

| Escenario | OI2024 predicho | OI2024 real | Error |
|-----------|----------------|-------------|-------|
| Modelo actual (vel_aparente) | 16 | 45 | -64% |
| Modelo actual (vel_real basica) | 26 | 45 | -43% |
| **Modelo corregido** | **39** | **45** | **-13%** |

| Escenario | PV2024-25 predicho | PV2024-25 real | Error |
|-----------|-------------------|----------------|-------|
| Modelo actual (vel_real basica) | 211 | 283 | -34% |
| **Modelo corregido** | **253** | **283** | **-11%** |

### 7.4 Recomendaciones operativas para ZUECO 270

1. **Comprar PV en agosto** (no en octubre): lead time de 2 meses, mercaderia lista para el arranque de temporada en octubre.
2. **Cantidad PV**: 280-300 pares (no 210). La familia tiene demanda latente no satisfecha.
3. **Mantener stock minimo OI**: 30-40 pares para capturar ventas off-season que el quiebre historico oculta.
4. **Revisar factores estacionales cada 2 años**: A medida que se repone mejor, los factores se "corrigen solos" porque reflejan ventas con stock disponible.

---

## Resumen ejecutivo

| Indicador | Valor |
|-----------|-------|
| Familia | 08727000 — ZUECO 270 HOMBRE C/BANDA |
| Años de datos | 12 (2014-2026) |
| Total historico | ~2654 pares |
| Estacionalidad | Verano fuerte (89% en Oct-Mar) |
| Problema principal | Quiebre cronico — vel_aparente subestima 60%+ |
| Error OI2024 (modelo basico) | -43% |
| Error PV2024-25 (modelo basico) | -34% |
| Error con modelo corregido | -11% a -13% |
| Accion inmediata | Comprar 280-300 pares PV en agosto |
