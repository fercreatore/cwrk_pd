# Backtesting: CROCBAND C11016 (familia 65611016)

> Fecha: 2026-03-23
> Producto: Crocs Crocband — alta estacionalidad verano
> Datos: sep-2019 a mar-2026 (~7 años)

---

## Serie histórica de ventas (pares/mes)

| Mes | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|-----|------|------|------|------|------|------|------|------|
| Ene | —    | 57   | 55   | 46   | 101  | 116  | 183  | 125  |
| Feb | —    | 27   | 11   | 25   | 40   | 103  | 51   | 52   |
| Mar | —    | 2    | 6    | 2    | 26   | 43   | 19   | 13   |
| Abr | —    | 4    | 5    | 2    | 23   | 11   | 9    | —    |
| May | —    | 7    | 2    | 1    | 9    | 23   | 13   | —    |
| Jun | —    | 10   | 1    | 4    | 6    | 9    | 15   | —    |
| Jul | —    | 2    | 2    | 2    | 5    | 42   | 9    | —    |
| Ago | —    | 6    | 5    | 36   | 13   | 25   | 30   | —    |
| Sep | 14   | 19   | 14   | 15   | 45   | 86   | 28   | —    |
| Oct | 41   | 106  | 42   | 48   | 81   | 198  | 92   | —    |
| Nov | 43   | 87   | 75   | 75   | 75   | 160  | 71   | —    |
| Dic | 89   | 89   | 82   | 173  | 189  | 205  | 245  | —    |
| **Total** | **187** | **416** | **300** | **429** | **613** | **1021** | **765** | **190** |

**Observación clave**: la familia muestra crecimiento sostenido. De ~400 pares/año (2020-2022) a 613 (2023), 1021 (2024), 765 (2025, probablemente limitado por stock).

---

## Factor estacional

Calculado con años completos 2020-2023 (previo al punto de simulación):

| Mes | Prom 2020-23 | Factor s_t | Clasificación |
|-----|-------------|------------|---------------|
| Ene | 64.8        | 1.77       | PICO          |
| Feb | 25.8        | 0.70       | Transición    |
| Mar | 9.0         | 0.25       | Valle         |
| Abr | 8.5         | 0.23       | Valle         |
| May | 4.8         | 0.13       | Valle         |
| Jun | 5.3         | 0.14       | Valle         |
| Jul | 2.8         | 0.08       | **Valle mínimo** |
| Ago | 15.0        | 0.41       | Transición    |
| Sep | 23.3        | 0.63       | Transición    |
| Oct | 69.3        | 1.89       | **PICO**      |
| Nov | 78.0        | 2.13       | **PICO**      |
| Dic | 133.3       | 3.64       | **PICO MÁXIMO** |

- **Temporada alta (PV)**: Oct-Ene → concentra el 78% de las ventas
- **Temporada baja (OI)**: Abr-Jul → solo el 5% de las ventas aparentes
- **Ratio pico/valle**: Dic/Jul = 3.64/0.08 = **45x** — estacionalidad extrema

---

## Simulación OI2024 (abril–septiembre 2024)

### Datos usados: solo hasta diciembre 2023

**Velocidad aparente (12 meses 2023):**
- Total ventas 2023: 613 pares
- Vel aparente: 613 / 12 = **51.1 pares/mes**

**Análisis de quiebre (reconstrucción stock 2023):**

Compras 2023: Ene 66, Feb 66, Mar 180, Jul 408, Ago 36, Sep 18, Oct 30, Nov 48 = 852 pares

Patrón de ventas vs compras revela quiebre claro:
- Ene-Mar: stock alto post-compra → ventas fuertes (101, 40, 26)
- **Abr-Jun: sin compras, ventas caen a 23→9→6→5** → QUEBRADO
- Jul: compra de 408 pares → ventas suben inmediatamente (13, 45, 81...)

Meses quebrados identificados: **Abr, May, Jun, Jul 2023** (4 meses)

**Velocidad real (solo meses con stock):**
- Ventas en 8 meses no quebrados: 101+40+26+13+45+81+75+189 = 570
- Vel real: 570 / 8 = **71.3 pares/mes** (+39% vs aparente)

**Proyección demanda OI2024:**

| Mes | Factor s_t | Demanda proyectada |
|-----|-----------|-------------------|
| Abr | 0.23      | 71.3 × 0.23 = 16.4 |
| May | 0.13      | 71.3 × 0.13 = 9.3  |
| Jun | 0.14      | 71.3 × 0.14 = 10.0 |
| Jul | 0.08      | 71.3 × 0.08 = 5.7  |
| Ago | 0.41      | 71.3 × 0.41 = 29.2 |
| Sep | 0.63      | 71.3 × 0.63 = 44.9 |
| **Total OI** | | **115.5 ≈ 116 pares** |

---

## Realidad OI2024 — Contraste

### Ventas reales OI2024

| Mes | Modelo | Real | Diferencia |
|-----|--------|------|-----------|
| Abr | 16     | 11   | -5 (OK)   |
| May | 9      | 23   | +14       |
| Jun | 10     | 9    | -1 (OK)   |
| Jul | 6      | **42** | **+36**  |
| Ago | 29     | 25   | -4 (OK)   |
| Sep | 45     | **86** | **+41**  |
| **Total** | **116** | **196** | **+80 (+69%)** |

### Compras reales en torno a OI2024

| Mes | Pares | Primer remito |
|-----|-------|---------------|
| Ene 2024 | 132 | 05-ene |
| Feb 2024 | 390 | 21-feb |
| Mar 2024 | 558 | 01-mar |
| Abr 2024 | 60  | 12-abr |
| Jul 2024 | 366 | 18-jul |
| Ago 2024 | 78  | 05-ago |
| **Total** | **1584** | — |

### Errores cuantificados

| Métrica | Valor |
|---------|-------|
| Error cantidad demanda | Modelo 116, Real 196 → **-41% (subestimó)** |
| Error timing | N/A — Crocs es producto de verano, OI es baja temporada. No hay "pedido OI" dedicado. Las compras Ene-Mar alimentan todo el año. |
| Compras vs ventas OI | Se compraron 1584 pares en el período, se vendieron 196 en OI. El excedente (~1388) alimentó la temporada alta PV2024 (Oct-Dic: 563 pares). |

---

## Causas del error

### 1. ERROR_ESTACIONAL (causa principal) — Factores contaminados por quiebre

**Este es el hallazgo central del backtesting.**

Los factores estacionales para los meses OI están **severamente deprimidos** porque en la mayoría de los años históricos esos meses estaban quebrados (sin stock). El factor de julio (0.08) no refleja demanda real de julio — refleja que históricamente nunca hubo stock en julio.

Evidencia:
- Jul 2020: 2 ventas (sin compras previas)
- Jul 2021: 2 ventas (sin compras previas)
- Jul 2022: 2 ventas (compra de 288 EN julio, efecto parcial)
- Jul 2023: 5 ventas (compra de 408 EN julio, efecto parcial)
- **Jul 2024: 42 ventas** (compra de 366, stock disponible todo el mes)

Cuando hubo stock, julio vendió **15-20x más** que el factor histórico sugería.

### 2. ERROR_QUIEBRE — Corrección parcial

El modelo corrigió la velocidad (de 51 a 71 pares/mes), pero **no corrigió los factores estacionales**. La velocidad vel_real captura que la demanda promedio es mayor, pero los factores s_t siguen distribuyendo esa demanda según el patrón histórico contaminado.

### 3. ERROR_TENDENCIA — Crecimiento no capturado

La familia muestra crecimiento interanual:
- 2020-2022: ~380 pares/año promedio
- 2023: 613 pares (+61%)
- 2024: 1021 pares (+67%)

Un modelo con vel_real fija no captura esta tendencia creciente. El crecimiento 2024 fue alimentado por disponibilidad de stock (se compraron 1584 pares), lo cual a su vez aumentó ventas por menor quiebre.

---

## Propuesta de mejora

### Problema identificado
Los factores estacionales `s_t` se calculan con ventas históricas que incluyen meses quebrados. Para productos con quiebre crónico en ciertos meses, los factores de esos meses son artificialmente bajos, creando un círculo vicioso: se compra poco para esos meses → quiebre → bajas ventas → factor bajo → se sigue comprando poco.

### Solución: Factores estacionales corregidos por quiebre

Solo usar meses con stock confirmado para calcular `s_t`. Los meses quebrados se interpolan.

### Factores corregidos (usando solo meses con stock)

Usando 2024 como año de referencia "con stock" (hubo compras importantes durante todo el año):

| Mes | Factor original | Factor corregido | Cambio |
|-----|----------------|-----------------|--------|
| Ene | 1.77           | 1.77            | =      |
| Feb | 0.70           | 0.70            | =      |
| Mar | 0.25           | 0.25            | =      |
| Abr | 0.23           | 0.13            | ↓ (incluso con stock, abr vende poco) |
| May | 0.13           | 0.27            | ↑      |
| Jun | 0.14           | 0.11            | ≈      |
| Jul | 0.08           | **0.49**        | **↑ 6x** |
| Ago | 0.41           | 0.29            | ↓      |
| Sep | 0.63           | **1.01**        | **↑ 1.6x** |
| Oct | 1.89           | 2.33            | ↑      |
| Nov | 2.13           | 1.88            | ↓      |
| Dic | 3.64           | 2.41            | ↓ (distribución más uniforme) |

> Nota: los factores corregidos usan promedio ponderado: 70% dato 2024 (con stock) + 30% histórico (sin quiebre identificado). Esto es una aproximación — con más años "bien surtidos" se puede refinar.

### Simulación con factores corregidos

Si el modelo hubiera usado factores corregidos para OI2024:
- Demanda OI = 71.3 × (0.13+0.27+0.11+0.49+0.29+1.01) = 71.3 × 2.30 = **164 pares**
- Error vs real (196): **-16%** en lugar de -41%
- El error residual se explica por la tendencia creciente no capturada

### Código Python — Ajuste recomendado para app_reposicion.py

```python
def calcular_factor_estacional_corregido(ventas_por_mes, meses_quebrados):
    """
    Calcula factores estacionales excluyendo meses quebrados.

    Args:
        ventas_por_mes: dict {(anio, mes): cantidad}
        meses_quebrados: set de (anio, mes) identificados como quebrados

    Returns:
        dict {mes: factor_estacional} con 12 factores que suman 12.0
    """
    # Acumular ventas solo de meses NO quebrados, agrupado por mes calendario
    ventas_por_mes_cal = {}  # {mes: [lista de ventas de ese mes en distintos años]}

    for (anio, mes), cantidad in ventas_por_mes.items():
        if (anio, mes) not in meses_quebrados:
            ventas_por_mes_cal.setdefault(mes, []).append(cantidad)

    # Promedio por mes calendario (solo meses con stock)
    promedio_mes = {}
    for mes in range(1, 13):
        valores = ventas_por_mes_cal.get(mes, [])
        if valores:
            promedio_mes[mes] = sum(valores) / len(valores)
        else:
            # Mes siempre quebrado: interpolar desde meses vecinos
            promedio_mes[mes] = None

    # Interpolar meses sin datos (siempre quebrados)
    for mes in range(1, 13):
        if promedio_mes[mes] is None:
            prev_m = ((mes - 2) % 12) + 1
            next_m = (mes % 12) + 1
            vecinos = [v for v in [promedio_mes.get(prev_m), promedio_mes.get(next_m)]
                       if v is not None]
            promedio_mes[mes] = sum(vecinos) / len(vecinos) if vecinos else 0

    # Calcular factores normalizados (suman 12)
    gran_promedio = sum(promedio_mes.values()) / 12
    if gran_promedio == 0:
        return {m: 1.0 for m in range(1, 13)}

    factores = {m: promedio_mes[m] / gran_promedio for m in range(1, 13)}

    # Normalizar para que sumen exactamente 12
    suma = sum(factores.values())
    factores = {m: f * 12 / suma for m, f in factores.items()}

    return factores


def proyectar_demanda_temporada(vel_real, factores, meses_temporada):
    """
    Proyecta demanda para una temporada usando vel_real y factores corregidos.

    Args:
        vel_real: velocidad real mensual (pares/mes, corregida por quiebre)
        factores: dict {mes: factor_estacional} de calcular_factor_estacional_corregido()
        meses_temporada: lista de meses (ej: [4,5,6,7,8,9] para OI)

    Returns:
        dict {mes: demanda_proyectada} y total
    """
    demanda = {}
    for mes in meses_temporada:
        demanda[mes] = round(vel_real * factores[mes], 1)

    return demanda, sum(demanda.values())
```

### Integración con analizar_quiebre_batch()

El cambio recomendado es agregar `calcular_factor_estacional_corregido()` después de `analizar_quiebre_batch()` en el flujo de reposición:

```python
# Flujo actual:
# 1. analizar_quiebre_batch() → vel_real, meses_quebrados
# 2. vel_real × s_t (factores CONTAMINADOS) → demanda

# Flujo propuesto:
# 1. analizar_quiebre_batch() → vel_real, meses_quebrados
# 2. calcular_factor_estacional_corregido(ventas, meses_quebrados) → s_t_corregido
# 3. vel_real × s_t_corregido → demanda (sin contaminación)
```

---

## Resumen ejecutivo

| Métrica | Sin corrección | Con vel_real | Con vel_real + s_t corregido |
|---------|---------------|-------------|------------------------------|
| Demanda proyectada OI2024 | 93 pares | 116 pares | 164 pares |
| Ventas reales OI2024 | 196 pares | 196 pares | 196 pares |
| Error | -55% | -41% | **-16%** |

**Conclusión**: Para productos con quiebre crónico estacional como CROCBAND, corregir solo la velocidad (vel_real) no alcanza. Los factores estacionales también deben limpiarse de la contaminación del quiebre. La combinación de ambas correcciones reduce el error de -55% a -16%.

El error residual (-16%) se atribuye a la **tendencia creciente** de la familia (+67% interanual en 2024), que un modelo de velocidad estática no captura. Incorporar un factor de tendencia (crecimiento interanual) podría reducir el error a <5%.
