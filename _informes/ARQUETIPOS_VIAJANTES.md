# Arquetipos y Limpieza de Outliers — Benchmark Viajantes H4/Calzalindo
> Generado: 2026-04-05
> Fuente: benchmark_viajantes.py + PUESTOS_ESTANDARIZADOS.md + ventas1 2022-2025
> 130 viajantes evaluados en el benchmark raw. Post-limpieza: ~90-95 viajantes válidos.

---

## PARTE 1 — Exclusiones del Benchmark

### 1.1 Exclusiones Estructurales (no son vendedores de piso)

Estos códigos **deben excluirse siempre** del benchmark. No representan vendedores individuales ni tienen sentido compararlos con el resto del equipo.

| Código | Nombre | Categoría | Razón de exclusión | Recomendación |
|--------|--------|-----------|-------------------|---------------|
| 7 | (remito interno) | Remito interno | Comprobante contable, no vendedor | **EXCLUIR** — ya excluido en SQL |
| 36 | (remito interno) | Remito interno | Comprobante contable, no vendedor | **EXCLUIR** — ya excluido en SQL |
| 1 | Fernando Calaianov | Dueño / Director | No es vendedor de piso. Aparece con ventas propias o transferencias de gerencia | **EXCLUIR** — agregar al filtro |
| 4 | Guille Calaianov | Infraestructura | Rol operativo no comercial | **EXCLUIR** — agregar al filtro |
| 9 | Tamara Calaianov | Ventas/RRHH | Rol gerencial, no de piso. Puede tener ventas esporádicas propias | **SEPARAR** — analizar aparte si tiene volumen, no incluir en ranking de piso |
| 50 | Leo Calaianov | Familiar / directivo | Familiar de la dirección, no vendedor de piso regular | **SEPARAR** — analizar aparte |
| 323 | Patricia Calaianov | Familiar / directivo | Familiar de la dirección, no vendedor de piso regular | **SEPARAR** — analizar aparte |
| 740 | Luciano Lanthier | Sistemas / informes | Maneja web2py/informes, no es vendedor comercial activo | **EXCLUIR** |
| 755 | Mati Rodriguez | Compras Deportes | Rol de comprador, no vendedor de piso | **EXCLUIR** |
| 1136 | Gonzalo Bernardi | Asistente Depósito | Operativo logístico, no vendedor | **EXCLUIR** |
| 1148 | Emanuel Cisneros | Operaciones | Rol operativo, no vendedor de piso | **EXCLUIR** |

### 1.2 Cuentas Grupales Históricas (REFUERZO)

Estos códigos fueron cuentas colectivas usadas históricamente para ingresar ventas de refuerzo o ingresantes sin código propio. **No representan una persona individual**.

| Código | Nombre probable | Razón de exclusión | Recomendación |
|--------|-----------------|--------------------|---------------|
| 20 | REFUERZO / Ingresante | Cuenta grupal histórica — múltiples personas bajo un mismo código | **EXCLUIR** del benchmark individual |
| 21 | REFUERZO / Ingresante | Idem | **EXCLUIR** |
| 22 | REFUERZO / Ingresante | Idem | **EXCLUIR** |
| 23 | REFUERZO / Ingresante | Idem | **EXCLUIR** |
| 24 | REFUERZO / Ingresante | Idem | **EXCLUIR** |
| 25 | REFUERZO / Ingresante | Idem | **EXCLUIR** |
| 26 | REFUERZO / Ingresante | Idem | **EXCLUIR** |
| 28 | REFUERZO / Ingresante | Idem | **EXCLUIR** |
| 29 | REFUERZO / Ingresante | Idem | **EXCLUIR** |
| 30 | REFUERZO / Ingresante | Idem | **EXCLUIR** |

> Nota: El rango 20-30 puede incluir también CUENTAS DE REFUERZO de locales específicos (ej: "REFUERZO CUORE", "REFUERZO NORTE"). Todos tienen la misma lógica: son cuentas transitorias, no representan una carrera individual. Incluirlos distorsiona el benchmark porque pueden tener meses de venta muy alta (evento puntual) seguidos de silencio total.

### 1.3 Cuenta Grupal Activa (ASESORAS CENTRAL)

| Código | Nombre | Razón de exclusión | Recomendación |
|--------|--------|--------------------|---------------|
| 65 | ASESORAS CENTRAL | Cuenta de facturación grupal para promotoras del local Central. $243M (2024) + $159M (2025). No es una persona — es un pool. | **EXCLUIR** del benchmark individual. Analizar aparte como "productividad colectiva dep 0" si se necesita. |

### 1.4 Operadores de Depósito 1 (Mercado Libre / Glam) — No vendedores de piso

El depósito 1 (Glam / ML) opera con una lógica diferente: es canal digital/outlet. Los "viajantes" asignados a ese depósito son operadores que registran ventas online, no vendedores de atención al público.

**Nota sobre Berri:** El código exacto de Berri no está en la documentación disponible pero su búsqueda es: viajante cuyo depósito principal (≥60% venta) sea el depósito 1, con perfil de volumen alto y consistencia baja típica de ML (picos por campañas).

| Código | Nombre | Razón de exclusión | Recomendación |
|--------|--------|--------------------|---------------|
| 545 | Bilicich Tomas | Operador ML/Glam — su venta es de canal digital, no de piso | **EXCLUIR** del benchmark de vendedores de piso. Crear benchmark separado para operadores ML si se necesita. |
| Berri (buscar) | Berri | Idem Bilicich — depósito 1 como principal | **EXCLUIR** del benchmark de piso. Identificar con: `WHERE deposito_principal = 1` en el CSV exportado. |

> Regla general: Cualquier viajante con `deposito_principal = 1` y `pct_dep_principal > 0.60` debe ser tratado como operador digital, no como vendedor de piso. El benchmark ya excluye el depósito 1 del cómputo del score, pero si el viajante casi exclusivamente vende en dep 1, su score resultará artificialmente bajo o irreal (pocos meses "activos" en depósitos de piso).

### 1.5 Outliers Estadísticos a Detectar y Tratar

Estas categorías no se pueden hardcodear sin correr el benchmark, pero se documentan los umbrales para revisión manual del CSV exportado.

#### A. Venta mensual > P99 del grupo (posibles cuentas de transferencia)

**Umbral:** Venta real mensual > 2.5x la mediana de su depósito principal.

| Sospechosos identificados | Código | Razón |
|---------------------------|--------|-------|
| Celina Ayas | 496 | $26M/mes — outlier significativo sobre el P90 del grupo. Verificar si es venta de piso real o incluye transferencias de stock entre locales. |
| ALMA PANIAGUA | 1106 | $22M/mes — segundo outlier. Relativamente nuevo (código alto). Verificar consistencia histórica y si tiene meses de venta que correspondan a carga masiva o traspaso. |
| valentina castillo | 502 | $21M/mes — tercer outlier. Verificar depósito y si hay meses con volumen anómalo. |

> Acción: si el Z-score de venta (`z_venta_mensual_real`) es > 3.0 dentro de su depósito, marcar como "outlier verificar" antes de incluir en el benchmark. No excluir automáticamente — puede ser una vendedora genuinamente excepcional.

#### B. Margen anómalo (< 30% o > 65%)

**Razón:** Margen < 30% sugiere error de carga de precio costo (artículos con costo=0 o inflado). Margen > 65% también puede ser error o mix de productos atípico (solo accesorios/marroquinería con markup alto).

**Acción en el script:** Agregar flag `flag_margen_anomalo = True` si `pct_margen < 30 OR pct_margen > 65`. No excluir automáticamente — mostrar advertencia en el output.

#### C. Viajantes activos solo 1-3 meses

El script ya filtra ≥ 6 meses activos para incluir en el benchmark (`viajantes_validos`). Los que quedan fuera de este filtro son ingresantes recientes, temporales de temporada alta, o cuentas de refuerzo que escaparon al filtro hardcodeado.

**Acción:** Listarlos en una sección separada "Viajantes en período de evaluación" en el output. No incluirlos en el score ni en los percentiles.

#### D. Pares por ticket > 10

**Razón:** Un ticket con 10+ pares es probable error de carga (cantidad=10 en lugar de 1), compra institucional (colegio, club), o carga de kit/lote. Distorsiona el KPI de productividad individual.

**Umbral:** `pares_por_ticket > 10` → marcar como "verificar". `pares_por_ticket > 20` → excluir de ese KPI (usar `np.nan` en el campo para ese viajante específico, no excluirlo del benchmark completo).

#### E. Viajantes con venta exclusivamente en un mes puntual

**Indicador:** `meses_activos <= 2` (ya capturado por el filtro de 6 meses), pero también: `consistencia < 0.1` con `meses_activos >= 6` indica alguien con 1-2 meses de venta muy alta y el resto nula. Probable cuenta de evento/temporada o carga retroactiva.

---

## PARTE 2 — Arquetipos / Estereotipos de Viajantes

### Metodología

Los arquetipos se definen sobre el universo de viajantes válidos post-limpieza (~90-95 personas). Las dimensiones clave son:

1. **Volumen mensual real** (en pesos dic-2025): alto / medio / bajo
   - Alto: > $8M/mes (aprox P75 del grupo completo)
   - Medio: $3M - $8M/mes
   - Bajo: < $3M/mes

2. **Perfil industria** (% venta en Deportes vs Zapatería+Mixto):
   - Deportes puro: ≥ 60% Deportes
   - Zapatería pura: ≥ 60% Zapatería
   - Mixto: 40-60% en ambos, o con componente Mixto_Zap_Dep significativo

3. **Consistencia** (1 - coef_variación sobre meses activos):
   - Alta: > 0.70 (muy regular mes a mes)
   - Media: 0.45 - 0.70
   - Baja: < 0.45 (muy variable, picos y valles)

4. **Rubro dominante**: damas / hombres / niños / mixto-género

5. **Tendencia** (slope regresión últimos 12 meses):
   - Creciente: slope > +200,000 $/mes
   - Estable: ±200,000 $/mes
   - Decreciente: slope < -200,000 $/mes

---

### Arquetipo 1: "Estrella Deportes" — El Motor del Local

**Descripción:** Vendedora de alto volumen en locales con fuerte perfil deportivo (dep 0 Central, dep 7, dep 2 Norte). Domina calzado running/training/basketball. Ticket alto, pares por ticket moderado-bajo (cliente compra 1 par de valor). Muy consistente. Tendencia estable o ligeramente creciente.

**Umbrales:**
- Volumen: > $10M/mes real
- Industria: ≥ 55% Deportes
- Consistencia: > 0.65
- Rubro: hombres > 40% o mix equilibrado
- Tendencia: estable o creciente

**Viajantes que encajan:**
| Código | Nombre | Dep | Perfil Industria | Notas |
|--------|--------|-----|-----------------|-------|
| 633 | NELI ADRIANA | 0 Central | 63% Deportes | Deportes 1 Central. $502M en 2024+2025. La referencia del arquetipo. |
| 514 | Nerea Arancibia | 0 Central | 53% Deportes | Deportes 2 Central. $482M en 2024+2025. Muy próxima al arquetipo. |
| 345 | Florencia Dituro | 0 + 9 | 46% Dep, Mixto | Generalista de alto volumen, podría ser Arquetipo 4 por su perfil mixto |
| 496 | Celina Ayas | — | — | $26M/mes — verificar outlier antes de confirmar arquetipo |
| 732 | RAMIREZ SOLANGE | 2 Norte | 53% Deportes | Volume más bajo que el arquetipo puro, puede ser "Estrella en formación" |

**Tamaño estimado del grupo:** 5-8 viajantes (top performers, ≥ score 80)

---

### Arquetipo 2: "Zapaterista Estable" — Especialista en Calzado de Moda/Vestir

**Descripción:** Vendedora con perfil fuertemente orientado a zapatería (calzado de moda, vestir, sandalias, botas). Alta consistencia. Trabaja principalmente en Cuore (dep 6) o en el ala zapatería de Central. Ticket medio-alto, dominancia damas. Volumen medio a alto en términos reales.

**Umbrales:**
- Volumen: $3M - $12M/mes real
- Industria: ≥ 55% Zapatería (subrubros 1-21, 34-44, 56, 60)
- Consistencia: > 0.60
- Rubro: damas > 50%
- Tendencia: estable (estas vendedoras tienen pico OI y PV marcados pero sin tendencia sostenida)

**Viajantes que encajan:**
| Código | Nombre | Dep | Perfil | Notas |
|--------|--------|-----|--------|-------|
| 700 | ABRIL LABALLEN | 8 Junín | 62% Zapatería | Zapatería 1 Junín. $209M en 2024+2025. Referencia del arquetipo. |
| 573 | Acosta Rocio | 6 Cuore | 53% Zapatería | Zapatería/Mixto 1 Cuore. $191M. Ligeramente más mixta. |
| 628 | GEORGINA LUNA | 6 Cuore | 56% Zapatería | Zapatería/Mixto 2 Cuore. $182M. |
| 1049 | Caterina Veliz | 6 Cuore | 64% Zapatería | Zapatería pura de Cuore. $90M. |
| 1113 | Yamila Negro | 6 Cuore | 68% Zapatería | La más especializada de Cuore en zapatería. $50M (más nueva). |
| 569 | Chiappinotto Carolina | 0 Central | 64% Zapatería | Alta venta en períodos cortos, actualmente esporádica — verificar si sigue activa. |

**Tamaño estimado del grupo:** 8-12 viajantes

---

### Arquetipo 3: "Generalista Mixta Estable" — Todo Terreno del Local

**Descripción:** Vendedora con perfil equilibrado Deportes+Zapatería (40-55% en cada), sin especialización marcada. Atiende todo: el cliente de running, la que busca sandalias, el nene que necesita botines. Vende en locales con mix variado (Junín dep 8+15, Eva Perón dep 7, parte de Central). Consistencia alta, volumen medio a alto.

**Umbrales:**
- Volumen: $3M - $10M/mes real
- Industria: 35-55% Deportes, 35-55% Zapatería (o alta presencia de Mixto_Zap_Dep)
- Consistencia: > 0.55
- Rubro: mix equilibrado (damas 35-55%, hombres 25-40%)
- Tendencia: estable

**Viajantes que encajan:**
| Código | Nombre | Dep | Perfil | Notas |
|--------|--------|-----|--------|-------|
| 758 | Gorosito Florencia | 8+15 Junín | Mixto 36% dep, 53% zap | Mixta 1 Junín. $208M en 2024+2025. |
| 702 | BALMACEDA VALENTINA | 8+15 Junín | Mixto similar | Mixta 2 Junín. $187M. Equipo muy estable. |
| 759 | Pavon Candela | 8+15 Junín | 40% dep, 48% zap | Mixta 3 Junín. $178M. |
| 595 | Aguirre Evelyn | 8+15 Junín | 42% dep, 47% zap | Mixta 5 Junín. $140M. |
| 760 | Gorosito Florencia (bis) | — | — | Ver si es la misma que 758 o diferente |
| 586 | Torancio Romina | 0 Central | 44% dep, 39% zap | Deportes 3 Central. Tira más a mixta que a deportes puro. |
| 602 | Fernandez Micaela | 2 + 7 | 56% dep, 33% zap | Mixta con sesgo deportivo. Multi-depósito. |
| 560 | Gonzalez Magali | 0 + 7 | 38% dep, 47% zap | Mixta con sesgo zapatero. Multi-depósito. |
| 1043 | Cristabla Ballarino | 7 Eva Perón | 57% dep, 24% zap | Mixta-deportiva. $55M, más joven en el equipo. |

**Tamaño estimado del grupo:** 15-20 viajantes (el grupo más numeroso)

---

### Arquetipo 4: "Generalista Voluminosa" — Alto Impacto Transversal

**Descripción:** Similar al Arquetipo 3 en perfil mixto, pero con volumen muy superior a la mediana del grupo. Trabaja en más de un depósito simultáneamente (multi-depósito), o tiene una posición dominante en un local grande (Central). Perfil "de ataque": va donde hay demanda. Difícil de comparar solo con pares de su depósito porque trasciende el local.

**Umbrales:**
- Volumen: > $12M/mes real (por encima del P90 general)
- Industria: Mixto o cualquier perfil
- Depósitos: ≥ 2 depósitos con >20% de venta cada uno, O depósito principal con venta > 2x la mediana del mismo local
- Consistencia: media-alta (> 0.50) — el volumen compensa cierta variabilidad

**Viajantes que encajan:**
| Código | Nombre | Situación | Notas |
|--------|--------|-----------|-------|
| 345 | Florencia Dituro | Dep 0 + dep 9, $430M en 2025 | La referencia del arquetipo. Vende de todo donde hay demanda. Generalista de alto impacto. |
| 496 | Celina Ayas | $26M/mes — verificar outlier | Si el volumen es genuino, encaja aquí. |
| 1106 | ALMA PANIAGUA | $22M/mes | Código alto (ingresante reciente). Verificar meses activos y consistencia antes de confirmar. |
| 502 | valentina castillo | $21M/mes | Verificar depósito principal y consistencia. |

**Tamaño estimado del grupo:** 3-6 viajantes (los top del top)

> Nota para el benchmark: estos viajantes necesitan benchmarks separados porque compiten "contra toda la red" más que contra su depósito. El score actual (percentil dentro del depósito) puede subestimarlos si su depósito tiene pocos vendedores, o sobreestimarlos en dep 0 si los compara con el promedio del local más concurrido.

---

### Arquetipo 5: "Sólida en Formación" — Potencial de Crecimiento

**Descripción:** Vendedora activa, con 1-2 años de trayectoria, performance en el rango "Sólido" (score 60-79). Todavía no alcanza el volumen de los arquetipos superiores, pero muestra consistencia creciente y tendencia positiva. Es la cantera natural de las Estrellas.

**Umbrales:**
- Volumen: $2M - $7M/mes real
- Meses activos: ≥ 12 meses (trayectoria suficiente para medir)
- Consistencia: > 0.50
- Tendencia: positiva (slope > 0)
- Score: 60-79 (clasificación "Sólido")

**Viajantes que probablemente encajan (a confirmar con el CSV):**
| Código | Nombre | Dep | Notas |
|--------|--------|-----|-------|
| 1036 | Candela Olguin | 2 Norte | $60M en 2024+25. Activa. Norte tiene menos competencia interna → puede crecer. |
| 1017 | Carla Marcela Gatti | 8 Junín | $112M. Perfil mixto. Sólida pero por debajo de las top de Junín. |
| 1028 | Julieta Pelizzoni | 7 Eva Perón | $32M dep 7. Deportes 1. Joven en el equipo, tendencia a monitorear. |
| 735 | DANIELA FALCON | 9 Tokyo | $139M. Mixta 1 Tokyo. Volumen medio-alto para ese local. |
| 707 | GARAY ROCIO CELESTE | 9 Tokyo | $120M. Mixta 2 Tokyo. |
| 730 | QUINTEROS VIRGINIA | 7 Eva Perón | $119M. Esporádica. Puede haber bajado al arquetipo siguiente. |

**Tamaño estimado del grupo:** 20-28 viajantes (clasificación "Sólido" tiene 38 en el benchmark raw, post-limpieza serán menos)

---

### Arquetipo 6: "Promedio Estacional" — Dependiente de la Temporada

**Descripción:** Vendedora activa pero cuya venta fluctúa fuertemente con la temporada (OI/PV). No logra mantener volumen en los meses valle. Consistencia baja. Puede tener meses muy buenos (liquidación, temporada alta) que inflan el promedio. Score 40-59. Requiere seguimiento individual.

**Umbrales:**
- Volumen: cualquier rango, pero con alta varianza
- Consistencia: < 0.45
- Meses activos: ≥ 6 (pasa el filtro mínimo)
- CV (desviación/media) > 0.60

**Perfil típico:** Zapaterista de Central en períodos de alta moda (OI nuevo, PV nuevo) que luego desaparece en meses de paso. O deportiva que explota en agosto/septiembre (back to school, temporada running) y baja en verano.

**Viajantes probablemente en este arquetipo (score 40-59 = "Promedio"):**
- La mayoría de los 53 viajantes clasificados como "Promedio" en el benchmark caen aquí.
- Ejemplos del dep 0 Central que tuvieron presencia corta: Chiappinotto Carolina (569), Daira Campos (625), Sosa Brisa (591).
- Dep 6 Cuore más nuevas (códigos > 1100) que no tienen aún año completo.

**Tamaño estimado del grupo:** 25-35 viajantes

---

### Arquetipo 7: "En Evaluación / Bajo Rendimiento" — Seguimiento Inmediato

**Descripción:** Viajantes con score < 40 que sí pasan el filtro de 6 meses activos. Pueden ser:
- Ingresantes que no despegaron (3-6 meses con venta muy baja)
- Vendedoras en proceso de desvinculación
- Viajantes asignados a depósitos muy pequeños o de nicho (marroquinería, dep 4)
- Cuentas de refuerzo que no fueron excluidas a tiempo

**Umbrales:**
- Score: < 40 (clasificaciones "En desarrollo" + "Bajo")
- El benchmark raw reporta 21 "En desarrollo" + 10 "Bajo" = 31 casos

**Acción recomendada:** Para RRHH, revisar uno a uno. Los 10 "Bajo" son candidatos a conversación de seguimiento o desvinculación. Los 21 "En desarrollo" merecen plan de desarrollo con metas trimestrales.

---

## PARTE 3 — Resumen de Viajantes por Arquetipo

| Arquetipo | Clasificación Benchmark | Tamaño estimado | Códigos representativos |
|-----------|------------------------|-----------------|------------------------|
| 1: Estrella Deportes | Estrella (≥80) | 5-8 | 633, 514, 732 |
| 2: Zapaterista Estable | Estrella + Sólido | 8-12 | 700, 573, 628, 1049, 1113 |
| 3: Generalista Mixta Estable | Sólido (60-79) | 15-20 | 758, 702, 759, 595, 586, 602, 560 |
| 4: Generalista Voluminosa | Estrella (outlier volumen) | 3-6 | 345, 496, 1106, 502 |
| 5: Sólida en Formación | Sólido con tendencia+ | 20-28 | 1036, 1017, 1028, 735, 707 |
| 6: Promedio Estacional | Promedio (40-59) | 25-35 | 569, 625, 591, códigos > 1050 varios |
| 7: En Evaluación | En desarrollo + Bajo (<40) | 28-32 | ver CSV exportado |

**Total post-limpieza:** ~90-100 viajantes en arquetipos vs 130 evaluados en raw.

---

## PARTE 4 — Recomendaciones para el Script `benchmark_viajantes.py`

### 4.1 Lista de códigos a excluir hardcodeada

Agregar en el script, antes de los filtros de meses activos, las siguientes listas:

```python
# ---------------------------------------------------------------------------
# Exclusiones hardcodeadas — NO son vendedores de piso
# ---------------------------------------------------------------------------

# Remitos internos (ya en el SQL WHERE pero se refuerza por seguridad)
REMITOS_INTERNOS = {7, 36}

# Directivos y personal no comercial
DIRECTIVOS_Y_NO_COMERCIALES = {
    1,    # Fernando Calaianov — dueño/director
    4,    # Guille Calaianov — infraestructura
    9,    # Tamara Calaianov — RRHH/gerencia (analizar aparte si se necesita)
    50,   # Leo Calaianov — familiar directivo
    323,  # Patricia Calaianov — familiar directivo
    740,  # Luciano Lanthier — sistemas/informes
    755,  # Mati Rodriguez — compras, no ventas
    1136, # Gonzalo Bernardi — depósito/logística
    1148, # Emanuel Cisneros — operaciones
}

# Cuentas grupales históricas REFUERZO
CUENTAS_REFUERZO = {20, 21, 22, 23, 24, 25, 26, 28, 29, 30}

# Cuentas grupales activas
CUENTAS_GRUPALES_ACTIVAS = {
    65,   # ASESORAS CENTRAL — pool de promotoras dep 0
}

# Operadores dep 1 (ML/Glam) — no vendedores de piso
# Agregar código de Berri cuando se identifique
OPERADORES_ML = {
    545,  # Bilicich Tomas — operador ML
    # BERRI: identificar corriendo: df_kpi[df_kpi['deposito_principal']==1].index.tolist()
}

# Unión de todos los que se deben excluir del benchmark de vendedores de piso
EXCLUIR_DEL_BENCHMARK = (
    REMITOS_INTERNOS
    | DIRECTIVOS_Y_NO_COMERCIALES
    | CUENTAS_REFUERZO
    | CUENTAS_GRUPALES_ACTIVAS
    | OPERADORES_ML
)
```

Luego en el `main()`, después de calcular `meses_activos`, agregar:

```python
# Aplicar exclusiones estructurales
viajantes_validos = viajantes_validos[
    ~viajantes_validos.isin(EXCLUIR_DEL_BENCHMARK)
]
print(f"  Viajantes excluidos (estructurales): {len(EXCLUIR_DEL_BENCHMARK)}")
print(f"  Viajantes válidos post-exclusión: {len(viajantes_validos)}")
```

### 4.2 Flags de outliers estadísticos (no excluir, sino marcar)

Agregar al DataFrame final antes de exportar:

```python
# Flag: outlier de volumen (Z-score > 3 dentro del depósito)
df_kpi['flag_volumen_outlier'] = df_kpi['z_venta_mensual_real'].abs() > 3.0

# Flag: margen anómalo
df_kpi['flag_margen_anomalo'] = (
    (df_kpi['pct_margen'] < 30) | (df_kpi['pct_margen'] > 65)
)

# Flag: pares/ticket sospechoso
df_kpi['flag_ppt_alto'] = df_kpi['pares_por_ticket'] > 10

# Flag: baja consistencia (dependiente de temporada)
df_kpi['flag_estacional'] = df_kpi['consistencia'] < 0.40
```

### 4.3 Identificar el código de Berri

Correr en el servidor 111 después de generar el CSV:

```python
# Identificar operadores dep 1 no hardcodeados
dep1_heavy = df_kpi[df_kpi['deposito_principal'] == 1]
print("Viajantes con depósito principal = 1 (ML/Glam):")
print(dep1_heavy[['nombre', 'venta_mensual_real', 'meses_activos']].to_string())
```

Agregar los códigos encontrados a `OPERADORES_ML`.

### 4.4 Separar análisis de arquetipos en el output

Agregar al final del `main()` una sección de salida por arquetipo:

```python
# Asignar arquetipo basado en clasificación + industria + consistencia
def asignar_arquetipo(row):
    clasif = row.get('clasificacion', '')
    industria = str(row.get('industria_principal', ''))
    consistencia = row.get('consistencia', 0) or 0
    venta = row.get('venta_mensual_real', 0) or 0

    if clasif == 'Estrella' and venta > 12_000_000:
        return 'Generalista Voluminosa'
    if clasif == 'Estrella' and 'Deporte' in industria:
        return 'Estrella Deportes'
    if clasif in ('Estrella', 'Solido') and 'Zapater' in industria and consistencia > 0.60:
        return 'Zapaterista Estable'
    if clasif == 'Solido' and consistencia > 0.55:
        if row.get('tendencia', 0) > 0:
            return 'Solida en Formacion'
        return 'Generalista Mixta Estable'
    if clasif == 'Promedio':
        return 'Promedio Estacional'
    if clasif in ('En desarrollo', 'Bajo'):
        return 'En Evaluacion'
    return 'Sin clasificar'

df_kpi['arquetipo'] = df_kpi.apply(asignar_arquetipo, axis=1)
```

---

## PARTE 5 — Contexto para Decisiones RRHH

### Viajantes a NO perder (núcleo crítico)

Estos 8-10 viajantes generan desproporcionadamente el resultado de la red. Si se van, el impacto es inmediato y difícil de recuperar:

| Código | Nombre | Por qué es crítico |
|--------|--------|-------------------|
| 345 | Florencia Dituro | Mayor volumen de toda la red. Multi-depósito. Generalista de ataque. |
| 633 | NELI ADRIANA | Deportes 1 Central. Referente del local más grande. |
| 514 | Nerea Arancibia | Deportes 2 Central. Backup natural de Neli. |
| 700 | ABRIL LABALLEN | Mejor zapaterista de Junín. Alta ticket, perfil femenino. |
| 758 | Gorosito Florencia | Mixta 1 Junín. El equipo de Junín es el más estable de la red. |
| 573 | Acosta Rocio | Zapatería/Mixto 1 Cuore. Local más especializado. |
| 628 | GEORGINA LUNA | Zapatería/Mixto 2 Cuore. Par natural de Rocío. |
| 496 | Celina Ayas | $26M/mes si es genuino → verificar y proteger. |

### Puestos vacantes de alto impacto (prioridad de cobertura)

| Puesto | Último titular | Estado | Urgencia |
|--------|---------------|--------|---------|
| Zapatería 1 Central | Chiappinotto Carolina (569) | Esporádica / posible vacante | ALTA |
| Zapatería 2 Central | Daira Campos (625) | Esporádica 2025 | ALTA |
| Deportes 1 Central | NELI ADRIANA (633) | Esporádica (irregular 2026) | MEDIA |
| Deportes/Mixto 2 dep7 | QUINTEROS VIRGINIA (630) | Esporádica 2025 | MEDIA |

---

*Fuentes: benchmark_viajantes.py (lógica y KPIs), PUESTOS_ESTANDARIZADOS.md (depósitos y trayectorias), project_equipo.md (códigos del equipo operativo), ventas1 2022-2025.*
*Datos de clasificación: 130 viajantes evaluados en raw, 8 Estrellas, 38 Sólidos, 53 Promedio, 21 En desarrollo, 10 Bajos.*
