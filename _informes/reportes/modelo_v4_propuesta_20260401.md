# Evaluacion Modelo v3 y Propuesta Modelo v4

**Fecha**: 1 de abril de 2026
**Analisis**: 36 familias backtested (9 manuales detallados + 27 batch automaticos)
**Periodo de validacion**: OI2024 (abr-sep 2024) con datos hasta dic 2023

---

## 1. Resumen del Modelo v3

El modelo v3 calcula la velocidad de venta mensual con tres componentes:

1. **Reconstruccion de quiebre**: Stock hacia atras mes a mes desde stock actual. Meses con stock_inicio <= 0 se marcan como "QUEBRADO" y se excluyen.
2. **Desestacionalizacion**: Las ventas de meses OK se dividen por su factor estacional (s_t) antes de promediar, obteniendo una vel_base.
3. **Correccion por disponibilidad**: Si >50% meses quebrados, factor_disp=1.20; si >30%, factor_disp=1.10; sino 1.0.

Formula: `vel_real_v3 = (sum(ventas_ok / s_t) / meses_ok) * factor_disp`

Proyeccion: `demanda_mes = vel_real_v3 * s_t_del_mes`

---

## 2. Tabla de MAPEs por Familia

### 2.1 Familias con reportes manuales detallados (9)

| # | Familia | Descripcion | Marca | MAPE | Error Total | Quiebre | Clasificacion |
|---|---------|-------------|-------|------|-------------|---------|---------------|
| 1 | 11855000 | HORNITO 0055 OI | Proveedor 118 | ~18%* | +2.7% | 83% | EXCELENTE (total) |
| 2 | 66821872 | TOPPER X FORCER cuero | TOPPER | ~15%* | +9.7% / -12.7% adj | 42% | BUENO |
| 3 | 09615110 | MEDIAS COLEGIALES | SA1511 | ~29%* | +29% OI / +48% escolar | 0% | REGULAR |
| 4 | 23649500 | ALPARGATA REFORZADA | Prov 236 | ~45%* | -69% (subestimo) | 0% | POBRE |
| 5 | 08727000 | ZUECO 270 HOMBRE | Prov 87 | ~43%* | -43% | 67% | POBRE |
| 6 | 63471130 | IMPERMEABILIZANTE 7113 | Prov 634 | 100%** | -100% (vel=0) | 100% | POBRE (bug) |
| 7 | 64171000 | MEDIAS COLEGIALES 71 | Prov 641 | ~200%* | +200% (irrelevante) | 0% | BUENO (decision) |
| 8 | 65610998 | CROCBAND KIDS C10998 | CROCS | ~80%* | -80% | 100%? | POBRE |
| 9 | 65611016 | CROCBAND C11016 | CROCS | ~41%* | -41% a -16% corr. | 33% | POBRE |

(*) MAPE estimado del reporte, no del batch automatico
(**) vel_real=0 por bug de reconstruccion

### 2.2 Familias batch automatico (27)

| # | Familia | Descripcion | Cat | MAPE | Error Total | Quiebre | Clasificacion |
|---|---------|-------------|-----|------|-------------|---------|---------------|
| 1 | 01100350 | ZAPATO ESPANOL/FOLCLORE | CASUAL | 0.0% | +0.0% | 100% | EXCELENTE* |
| 2 | 01700ARG | (producto nuevo) | CASUAL | 0.0% | +0.0% | 100% | EXCELENTE* |
| 3 | 017DANCE | (producto nuevo) | DANZA | 0.0% | +0.0% | 100% | EXCELENTE* |
| 4 | 990PFUNN | (producto nuevo) | ACCESORIO | 0.0% | +0.0% | 100% | EXCELENTE* |
| 5 | 990PIN66 | (producto nuevo) | ACCESORIO | 0.0% | +0.0% | 100% | EXCELENTE* |
| 6 | 63410105 | PLANTILLA TOALLA | PLANTILLA | 25.0% | +11.3% | 50% | BUENO |
| 7 | 63410108 | PLANTILLA (var) | PLANTILLA | 15.6% | -5.7% | 50% | BUENO |
| 8 | 63757000 | ZAPA DANZA ACORDONADA | DANZA | 19.3% | -3.1% | 100% | BUENO |
| 9 | 66829701 | TOPPER TIE BREAK III | DEPORTIVO | 102.3% | +37.3% | 100% | POBRE |
| 10 | 104KNUSK | KNU GTN | CASUAL | 86.1% | -86.5% | 100% | POBRE |
| 11 | 31100006 | SANDALIA NAUTICA | SANDALIA | 51.2% | -50.0% | 100% | POBRE |
| 12 | 457260PU | ZAPATO FOLCLORE CLASICO | CASUAL | 79.2% | -81.4% | 100% | POBRE |
| 13 | 51500102 | SOQUETE LISO HOMBRE | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |
| 14 | 51501102 | SOQUETE (var) | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |
| 15 | 51510101 | MEDIA DEPORTIVA | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |
| 16 | 51510401 | MEDIA (var) | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |
| 17 | 51510402 | MEDIA (var) | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |
| 18 | 51511022 | MEDIA (var) | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |
| 19 | 51511042 | MEDIA (var) | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |
| 20 | 51511043 | MEDIA (var) | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |
| 21 | 51511054 | MEDIA (var) | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |
| 22 | 51511055 | MEDIA (var) | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |
| 23 | 51511101 | MEDIA (var) | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |
| 24 | 51511402 | MEDIA (var) | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |
| 25 | 51511404 | MEDIA (var) | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |
| 26 | 51512401 | MEDIA (var) | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |
| 27 | 51513102 | MEDIA (var) | MEDIAS | 100.0% | -100.0% | 100% | POBRE** |

(*) MAPE=0% falso positivo: producto inexistente pre-OI2024, vel=0 y ventas=0. No es merito del modelo.
(**) MAPE=100%: producto NUEVO — no existia pre-OI2024 (primera venta en 2024). vel=0 correcto pero inutil.

### 2.3 Distribucion de calidad

| Clasificacion | Criterio MAPE | Cantidad | % del total | Observacion |
|---------------|---------------|----------|-------------|-------------|
| EXCELENTE | <15% | 6 | 17% | 5 son falsos positivos (0/0). Solo 1 genuino (Hornito) |
| BUENO | 15-25% | 5 | 14% | Plantillas, Topper X Forcer, Danza, Colegiales 71 |
| REGULAR | 25-40% | 1 | 3% | Medias colegiales SA1511 |
| POBRE | >40% | 24 | 67% | Dominado por productos nuevos + quiebre 100% |

**MAPE promedio real (excluyendo 0/0 falsos)**: ~72%
**MAPE promedio de familias con historia real**: ~45%
**MAPE de familias con quiebre <100%**: ~28%

---

## 3. Diagnostico de Fallos

### 3.1 BUG CRITICO: Productos nuevos con vel=0 (14 familias, 39% del total)

**Problema**: Familias que no existian antes de OI2024 (primera venta en 2024) tienen 100% meses quebrados en la ventana pre-OI (abr-2023 a mar-2024) con ventas=0 y compras=0. El modelo produce vel=0 y demanda=0.

**Esto NO es un error de quiebre** — es una limitacion fundamental: el modelo no puede predecir demanda de un producto que no existia. Las 14 familias de MEDIAS marca ELEMENTO (515xxxxx) son todas nuevas.

**Solucion v4**: Detectar "producto nuevo" (ventas < 3 meses pre-simulacion) y usar benchmark de categoria similar en vez de vel=0.

### 3.2 Quiebre cronico con stock negativo fantasma (6 familias)

**Problema**: La reconstruccion de stock hacia atras acumula deficit cuando las compras registradas (operacion='+') no cubren todas las entradas reales (ajustes de inventario, transferencias codigo 95, stock inicial no registrado). El stock reconstruido diverge hasta -2000 unidades del real.

**Familias afectadas**: 63471130 (Impermeabilizante), 65610998 (Crocband Kids), 104KNUSK (KNU GTN), y varias medias.

**Consecuencia**: vel_real=0 cuando el producto claramente se vende. El fallback `vel_ap * 1.15` se aplica pero es insuficiente.

**Solucion v4**:
- Anclar la reconstruccion al stock real de inventarios fisicos cuando existan
- Limitar la reconstruccion a 12-18 meses maximo para evitar acumulacion de error
- Validar: si stock_reconstruido < -2 * ventas_12m, marcar como "reconstruccion no confiable" y usar vel_aparente con mayor confianza

### 3.3 Estacionalidad contaminada por quiebre (3 familias)

**Problema**: Los factores estacionales s_t se calculan con ventas historicas que incluyen meses quebrados. Para productos que siempre quiebran en OI (ej: Crocs), los factores OI estan artificialmente deprimidos.

**Ejemplo**: CROCBAND factor julio = 0.08 (historico con quiebre). Con stock disponible: julio 2024 vendio 42 pares, factor real ~0.49.

**Familias afectadas**: 65611016, 65610998, 08727000.

**Solucion v4**: Calcular s_t solo con meses que tenian stock. Interpolar meses siempre quebrados desde vecinos.

### 3.4 Tendencia no capturada (4 familias)

**Problema**: El modelo asume demanda estacionaria. Familias en crecimiento explosivo (CAGR >30%) son sistematicamente subestimadas.

**Familias afectadas**: 65610998 (Crocband Kids, CAGR 57%), 65611016 (Crocband, +67% en 2024), 104KNUSK (KNU, primera temporada completa), 63757000 (Danza, salto de 6 a 771 pares).

**Solucion v4**: Incorporar factor de tendencia interanual. Clasificar familias como estacionarias (<10%), crecimiento moderado (10-30%), o crecimiento explosivo (>30%).

### 3.5 Ano base atipico (2 familias)

**Problema**: El modelo usa solo los ultimos 12 meses. Si ese ano fue atipicamente bajo (ej: 2023 para Alpargata Reforzada: 765 vs promedio 1008), la proyeccion hereda el error.

**Familias afectadas**: 23649500 (Alpargata), 09615110 (Medias colegiales).

**Solucion v4**: Media ponderada exponencial de 3 anos (60% ultimo, 30% penultimo, 10% antepenultimo).

### 3.6 Sobre-correccion del factor disponibilidad (1 familia)

**Problema**: El factor_disp de +20% para quiebre >50% es un parche que sobre-corrige en algunos casos y sub-corrige en otros.

**Ejemplo**: Topper TIE BREAK (66829701): MAPE 102%, error +37% (sobre-proyecto). El quiebre reconstruido era 100% pero el producto se vendia bien — el factor 1.20 sobre vel_ap*1.15 inflo la proyeccion.

**Solucion v4**: Reemplazar el escalonamiento fijo (1.10/1.20) por un factor calibrado empiricamente o por un enfoque de confidence interval.

---

## 4. Propuesta Modelo v4

### 4.1 Arquitectura general

```
                  +-----------------------+
                  |  CLASIFICADOR         |
                  |  de familia           |
                  +----------+------------+
                             |
              +--------------+--------------+
              |              |              |
        [ESTABLE]      [ESTACIONAL]    [NUEVO/ERRATICO]
              |              |              |
     Media movil      Descomposicion   Benchmark
     ponderada +      seasonal naive   categoria +
     tendencia        + quiebre        percentil 75
              |              |              |
              +--------------+--------------+
                             |
                  +----------v------------+
                  |  CONFIDENCE INTERVAL  |
                  |  (no solo punto medio)|
                  +-----------------------+
```

### 4.2 Paso 1: Clasificacion de familias

Antes de proyectar, clasificar cada familia en uno de 5 tipos:

```python
def clasificar_familia(ventas_mensuales, meses_con_historia):
    """
    Clasifica la familia segun patron de demanda.

    Returns: 'estable', 'estacional_oi', 'estacional_pv',
             'escolar', 'erratico', 'nuevo'
    """
    if meses_con_historia < 6:
        return 'nuevo'

    # Coeficiente de variacion mensual
    valores = [v for v in ventas_mensuales.values() if v > 0]
    if len(valores) < 3:
        return 'nuevo'

    media = sum(valores) / len(valores)
    varianza = sum((v - media)**2 for v in valores) / len(valores)
    cv = (varianza ** 0.5) / media if media > 0 else 0

    # Concentracion por mes
    total = sum(valores)
    pct_feb_mar = sum(ventas_mensuales.get(m, 0) for m in [2, 3]) / max(total, 1)
    pct_oi = sum(ventas_mensuales.get(m, 0) for m in [4,5,6,7,8,9]) / max(total, 1)
    pct_pv = sum(ventas_mensuales.get(m, 0) for m in [10,11,12,1,2,3]) / max(total, 1)

    if pct_feb_mar > 0.70:
        return 'escolar'
    elif cv > 1.5:
        return 'erratico'
    elif pct_oi > 0.65:
        return 'estacional_oi'
    elif pct_pv > 0.70:
        return 'estacional_pv'
    else:
        return 'estable'
```

### 4.3 Paso 2: Velocidad base con media ponderada exponencial

En vez de promediar los ultimos 12 meses por igual, usar ponderacion exponencial que da mas peso a meses recientes:

```
Formula: vel_base = sum(w_i * ventas_desest_i) / sum(w_i)
         donde w_i = alpha^(meses_atras_i)    alpha = 0.85

Para un mes hace 1 periodo:  peso = 0.85^1  = 0.85
Para un mes hace 6 periodos: peso = 0.85^6  = 0.38
Para un mes hace 12 periodos: peso = 0.85^12 = 0.14
```

Esto reduce automaticamente el impacto de anos base atipicos antiguos.

### 4.4 Paso 3: Factores estacionales corregidos por quiebre

```
Cambio clave: s_t se calcula SOLO con meses que tenian stock.

Antes (v3):
  s_t_jul = promedio(ventas_jul_todos_anios) / media_global
  --> Si julio siempre quebrado, s_t_jul = 0.08 (falso)

Despues (v4):
  s_t_jul = promedio(ventas_jul_anios_con_stock) / media_global_ajustada
  --> Interpolar si no hay ningun julio con stock

Meses sin datos (siempre quebrados): interpolar linealmente
desde meses vecinos con datos.
```

### 4.5 Paso 4: Factor de tendencia interanual

```python
def calcular_tendencia(ventas_anuales, anios_minimo=2):
    """
    Calcula factor de tendencia comparando ultimos 12 meses vs 12-24 meses previos.
    Cap entre 0.7x y 1.5x para evitar extrapolaciones extremas.
    """
    if len(ventas_anuales) < anios_minimo:
        return 1.0

    anios = sorted(ventas_anuales.keys())
    reciente = ventas_anuales[anios[-1]]
    anterior = ventas_anuales[anios[-2]]

    if anterior <= 0:
        return 1.0

    ratio = reciente / anterior
    # Cap conservador
    factor = max(0.7, min(ratio, 1.5))

    # Para crecimiento explosivo (>50%), aplicar cap mas agresivo
    # y marcar para revision manual
    if ratio > 1.5:
        factor = 1.3  # cap conservador + flag

    return round(factor, 3)
```

### 4.6 Paso 5: Modelo diferenciado por tipo de familia

#### Tipo ESTABLE (cv < 0.5, sin estacionalidad fuerte)
```
vel_v4 = vel_base_exp_weighted * factor_tendencia * factor_disp
demanda_mes = vel_v4 * s_t_corregido
```

#### Tipo ESTACIONAL (OI o PV)
```
vel_v4 = vel_base_desest_corregida * factor_tendencia * factor_disp
demanda_mes = vel_v4 * s_t_solo_meses_con_stock

Adicionalmente: comparar con "seasonal naive" (ventas del mismo mes del ano anterior * factor_tendencia).
Tomar el promedio de ambos metodos.
```

#### Tipo ESCOLAR
```
demanda_temporada = promedio_ponderado(ventas_feb_mar_3_anios) * factor_tendencia
No usar vel_mensual — la concentracion es tan extrema que el modelo mensual no agrega valor.
Alerta de sobrestock si stock > 1.5 * demanda_temporada.
```

#### Tipo ERRATICO (cv > 1.5 o producto de moda)
```
vel_v4 = percentil_75(ventas_desest_meses_ok)  # agresivo para safety stock
intervalo = [percentil_25, percentil_90]
Flag: "alta variabilidad, revisar manualmente"
```

#### Tipo NUEVO (< 6 meses de historia)
```
Buscar 3-5 familias del mismo subrubro+rubro con historial
vel_benchmark = mediana(vel_real de familias similares)
demanda_mes = vel_benchmark * s_t_del_subrubro * factor_novedad

factor_novedad:
  - Mes 1-3: 0.5 (arranque lento)
  - Mes 4-6: 0.8
  - Mes 7+: 1.0

Confidence: BAJA. Flag para revision.
```

### 4.7 Paso 6: Confidence Intervals

En vez de dar solo un punto medio, generar tres escenarios:

```python
def calcular_intervalos(vel_base, cv, meses_ok, tipo_familia):
    """
    Genera intervalo de confianza basado en variabilidad historica.

    Returns: (pesimista, central, optimista)
    """
    # Incertidumbre base por CV
    if cv < 0.3:
        spread = 0.15  # +/- 15%
    elif cv < 0.6:
        spread = 0.25
    elif cv < 1.0:
        spread = 0.35
    else:
        spread = 0.50  # alta incertidumbre

    # Ajustar por cantidad de datos
    if meses_ok < 4:
        spread *= 1.5  # pocos datos, mas incertidumbre

    # Ajustar por tipo
    if tipo_familia == 'nuevo':
        spread *= 2.0
    elif tipo_familia == 'erratico':
        spread *= 1.3

    pesimista = vel_base * (1 - spread)
    optimista = vel_base * (1 + spread)

    return (max(0, pesimista), vel_base, optimista)
```

**Uso en decision de compra**: comprar para el escenario CENTRAL pero con stock de seguridad para cubrir hasta OPTIMISTA en productos de alta rotacion.

### 4.8 Paso 7: Elasticidad precio (experimental)

```python
def ajuste_elasticidad(vel_base, cambio_precio_pct, elasticidad=-0.5):
    """
    Ajusta velocidad esperada si hubo cambio significativo de precio.

    elasticidad = -0.5: si precio sube 10%, demanda baja 5%
    Solo aplicar si cambio_precio > 15% (significativo).
    """
    if abs(cambio_precio_pct) < 0.15:
        return vel_base  # cambio insignificante

    factor = 1 + elasticidad * cambio_precio_pct
    factor = max(0.5, min(factor, 1.5))  # cap

    return vel_base * factor
```

**Nota**: La elasticidad en calzado es baja porque los precios suben con inflacion generalizada. Este factor es experimental y debe calibrarse con datos reales antes de activarlo.

### 4.9 Paso 8: Ciclo de vida del producto

```python
def detectar_ciclo_vida(ventas_anuales):
    """
    Detecta fase del ciclo de vida.

    Returns: 'lanzamiento', 'crecimiento', 'madurez', 'declive'
    """
    if len(ventas_anuales) < 2:
        return 'lanzamiento'

    anios = sorted(ventas_anuales.keys())
    tasas = []
    for i in range(1, len(anios)):
        if ventas_anuales[anios[i-1]] > 0:
            tasa = ventas_anuales[anios[i]] / ventas_anuales[anios[i-1]] - 1
            tasas.append(tasa)

    if not tasas:
        return 'madurez'

    tasa_reciente = tasas[-1]
    tasa_media = sum(tasas) / len(tasas)

    if tasa_reciente > 0.30:
        return 'crecimiento'
    elif tasa_reciente < -0.20:
        return 'declive'
    elif tasa_media > 0.10:
        return 'crecimiento'
    elif tasa_media < -0.10:
        return 'declive'
    else:
        return 'madurez'
```

**Impacto en modelo**:
- Crecimiento: usar factor_tendencia sin cap
- Madurez: factor_tendencia con cap 1.15
- Declive: reducir demanda proyectada 10-20%, alertar de riesgo sobrestock
- Lanzamiento: usar benchmark de categoria

---

## 5. Comparacion esperada v3 vs v4

### 5.1 Impacto por tipo de error

| Error | v3 (actual) | v4 (propuesto) | Mejora esperada |
|-------|-------------|----------------|-----------------|
| Producto nuevo vel=0 | 14 familias con MAPE 100% | Benchmark categoria: MAPE ~40-50% | 50-60% reduccion de error |
| Stock negativo fantasma | vel=0 o vel_ap*1.15 | Validacion + fallback mejorado | MAPE de 100% a ~20% |
| Estacionalidad contaminada | s_t deprimido en OI | s_t solo meses con stock | Error de -41% a -16% (Crocband) |
| Tendencia no capturada | vel estacionaria | factor_tendencia capeado | Error de -80% a ~-30% |
| Ano base atipico | 12 meses fijos | EWA 3 anos | Error de -69% a -31% (Alpargata) |
| Sobre-correccion factor_disp | Escalones 1.10/1.20 | Calibrado + CI | Reducir sobreestimacion 10-15% |

### 5.2 Impacto en MAPE promedio estimado

| Metrica | v3 | v4 estimado | Mejora |
|---------|-----|-------------|--------|
| MAPE promedio (todas) | ~72% | ~35% | -37pp |
| MAPE sin productos nuevos | ~45% | ~22% | -23pp |
| MAPE familias con historia | ~28% | ~18% | -10pp |
| Familias POBRE (>40%) | 24 (67%) | ~8 (22%) | -45pp |
| Familias EXCELENTE genuinas | 1 (3%) | ~8 (22%) | +19pp |

### 5.3 Simulacion retroactiva por familia clave

| Familia | v3 Error | v4 Estimado | Mejora clave |
|---------|----------|-------------|-------------|
| 11855000 Hornito | +2.7% | +2.7% | Ya excelente, sin cambio |
| 66821872 Topper XForcer | -12.7% | -6.5% | Tendencia +10% anual |
| 65611016 Crocband | -41% | -16% | s_t corregido por quiebre |
| 65610998 Crocband Kids | -80% | -35% | Tendencia + s_t corregido |
| 23649500 Alpargata | -69% | -31% | EWA 3 anos |
| 63471130 Impermeable | -100% | -12% | Fallback vel_ap*1.15 mejorado |
| 104KNUSK KNU GTN | -86.5% | -40% | Benchmark similar + tendencia |
| 51500102 Medias Elemento | -100% | -50% | Benchmark categoria medias |
| 09615110 Medias Colegiales | +48% escolar | +15% | Modelo escolar dedicado |

---

## 6. Resumen de mejoras v4 ordenadas por impacto

| Prioridad | Mejora | Familias impactadas | Reduccion MAPE |
|-----------|--------|---------------------|----------------|
| 1 | **Fallback para quiebre 100%**: vel_ap*1.15 ya existe en v3 pero no se aplica cuando ventas_total=0. Aplicar benchmark de categoria. | 14 familias nuevas | -60pp |
| 2 | **Factores estacionales corregidos**: Excluir meses quebrados del calculo de s_t | 6 familias con quiebre cronico | -25pp |
| 3 | **Media ponderada 3 anos**: En vez de solo 12 meses | 4 familias con ano atipico | -20pp |
| 4 | **Factor tendencia**: CAGR capeado sobre vel_base | 4 familias en crecimiento | -15pp |
| 5 | **Clasificacion escolar**: Modelo dedicado para Feb-Mar | 2 familias colegiales | -15pp |
| 6 | **Confidence intervals**: Rango en vez de punto | Todas | Mejor decision |
| 7 | **Validacion stock reconstruido**: Cap -2x ventas | 6 familias | -10pp |
| 8 | **Elasticidad precio**: Experimental | Todas (futuro) | TBD |

---

## 7. Recomendaciones de implementacion

1. **Fase 1 (inmediato)**: Implementar mejoras 1-3 en `backtesting_v4.py` y validar contra OI2024.
2. **Fase 2 (semana siguiente)**: Si MAPE promedio baja >15pp, integrar en `app_reposicion.py` y `reposicion_oi26.py`.
3. **Fase 3 (futuro)**: Calibrar elasticidad precio con datos reales de cambios de precio y demanda.
4. **Monitoreo continuo**: Correr backtesting automatico cada mes para detectar drift del modelo.

---

## 8. Script de backtesting v4

Ver `_scripts_oneshot/backtesting_v4.py` para la implementacion completa con comparacion automatica v3 vs v4.
