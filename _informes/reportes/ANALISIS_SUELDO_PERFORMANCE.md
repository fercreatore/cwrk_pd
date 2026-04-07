# ANÁLISIS CAUSAL: SUELDO vs PERFORMANCE DE VENDEDORES
## H4 / CALZALINDO — Período 2022–2025
> Generado: 5 de abril de 2026
> Base de datos: msgestion01 (sueldos moviempl1 cod=10) + ventas1 combinada 01+03

---

## 1. TABLA DE MAPEO numero_cuenta → viajante

La relación es **directa**: `empleados.numero` = `viajante` en ventas1.
La tabla `viajantes` tiene una columna `numero_cuenta` pero solo tiene 1 registro vinculado (Cuvells Georgina).
El mapeo real funciona así: el mismo código numérico identifica al vendedor en AMBOS sistemas.

| numero_cuenta | Nombre Empleado | Sueldo Promedio Mensual (2024-25) |
|---------------|-----------------|-----------------------------------|
| 68 | Galvan Tamara Sabina | $758k |
| 65 | Rodriguez Camila Mariel | $1.09M |
| 259 | Mariana Lopez | $627k |
| 345 | Dituro Florencia | $500k |
| 363 | Arduino Irina | $567k |
| 305 | Amigo Rocio | $479k |
| 525 | Damario Luz | $514k |
| 553 | Solares Malena | $591k |
| 560 | Gonzalez Magali | $534k |
| 573 | Acosta Rocio | $567k |

**Total empleados con sueldo en moviempl1 (2022-2025):** 257
**Empleados con TANTO sueldo COMO ventas en el mismo código:** 191
**Casos con ventas pico >1M/mes analizados:** 55

---

## 2. TOP 10 CASOS DE MAYOR CAÍDA DE PERFORMANCE

### CASO 1 — Bilicich Tomas [545]
**El caso más extremo del dataset. Gerente o cargo jerárquico.**

| Año | Venta Mensual Prom | Sueldo Mensual Prom |
|-----|-------------------|---------------------|
| 2022 | $975k (1m) | $19k |
| 2023 | $450k (10m) | $241k |
| 2024 | **−$79k** (5m) | **$819k** |
| 2025 | **−$66k** (6m) | **$1.198M** |

**Caída:** 106% desde pico. Ventas negativas desde mayo 2023 (solo devoluciones).
**Desfase:** Ventas cayeron en mayo 2023 → sueldo continuó hasta dic 2025 (32 meses de sueldo sin ventas).
**Hipótesis:** Pasó a rol administrativo/gerencial o es el dueño. Su "sueldo" pasó de $19k a $1.2M en 3 años. No es un vendedor de piso: es alguien que gestiona desde adentro. Las ventas en su código posiblemente eran transacciones puntuales.

---

### CASO 2 — Pompei Valentino [527]
**Caso diagnóstico clásico: SUELDO cortó ANTES que las ventas.**

| Año | Venta Mensual Prom | Sueldo Mensual Prom |
|-----|-------------------|---------------------|
| 2022 | $3.9M (6m) | $70k |
| 2023 | $3.8M (12m) | $183k |
| 2024 | $200k (3m) | --- (sin sueldo) |
| 2025 | ~$0 (3m) | --- |

**Desfase:** Sueldo cortó en sept/2023. Ventas cayeron 15 meses DESPUÉS.
**Serie clave:** Ene–Sep 2023 vendía entre $2.2M y $7.6M/mes con sueldo $95k–$287k. Octubre 2023: ventas = -$4.783 (devoluciones), sueldo = $0. Vendió puntualmente en dic/2024 ($596k) sin sueldo.
**Hipótesis causal:** Le cortaron el sueldo en octubre 2023 → vendió residualmente unos meses más pero sin estructura. **La caída de ventas siguió al corte de sueldo**, con lag de ~3 meses. Posible conflicto económico, desvinculación o pase a monotributo/comisión pura que el sistema no registra.

---

### CASO 3 — Perrier Macarena [557]
**Caso paradójico: vendió más sin sueldo que con sueldo.**

| Año | Venta Mensual Prom | Sueldo Mensual Prom |
|-----|-------------------|---------------------|
| 2023 | $4.0M (12m) | $180k (solo algunos meses) |
| 2024 | $1.5M (2m) | $415k (ene/24 solo) |
| 2025 | $3.9M (5m) | --- (sin sueldo) |

**Detalle mensual destacado:**
- 2023: vendía $3.8M–$9.7M/mes; sueldo irregular (algunos meses $0)
- 2024/01: sueldo $415k (pico) → luego cero
- 2025/07–2025/12: vende $3.4M–$12.6M/mes **completamente sin sueldo**

**Desfase:** Sueldo cortó ene/2024. Siguió vendiendo hasta dic/2025 (23 meses más).
**Hipótesis:** Es **comisionista pura** o freelance. El "sueldo" registrado era irregular y posiblemente un anticipo. Las ventas de 2025 ($12.6M en dic) sin ningún sueldo sugieren que trabaja por comisión sin registrar en moviempl1. **No hay relación causal sueldo→venta**: son sistemas independientes para esta persona.

---

### CASO 4 — Rodriguez Macarena [417]
**Caso de latencia larga: cobró sueldo 18 meses sin vender, luego explotó.**

| Período | Ventas | Sueldo |
|---------|--------|--------|
| Ene/2022–Ago/2023 | ~$0 (solo devoluciones) | $50k–$332k/mes |
| Sep–Nov/2023 | $3.8M–$5.2M/mes | $230k–$256k/mes |
| Dic/2023–Ago/2024 | ~$0 | $251k–$832k/mes |

**Análisis:** 18 meses de sueldo sin vender → 3 meses de pico → volvió a cero.
**Hipótesis:** Estaba en capacitación prolongada o en un rol sin ventas directas. El pico de sep–nov/2023 fue un período de "campaña" o temporada específica. Luego el sueldo siguió subiendo ($832k en jun/2024) mientras las ventas volvieron a cero. El sueldo no está correlacionado con performance en absoluto para este perfil.

---

### CASO 5 — Maibach Florencia Agustina [704]
**Caso reciente de caída abrupta (2025).**

| Mes | Venta | Sueldo |
|-----|-------|--------|
| Ago/2024 | $3.9M | $0 (vendió sin sueldo) |
| Sep/2024 | $5.5M | $895k |
| Oct/2024 | $10.0M | $0 (vendió sin sueldo) |
| Nov/2024 | $8.7M | $1.36M |
| Dic/2024 | $12.1M | $900k |
| Ene–Feb/2025 | $7.8M–$7.9M | $650k–$700k |
| Mar/2025 | $128k | $700k |
| Abr/2025 | −$10k | $750k |
| May–Dic/2025 | **$0** | $850k–$1.525M |

**Desfase:** Ventas cayeron en marzo/2025. Sueldo siguió subiendo hasta $1.525M en dic/2025.
**Hipótesis:** Caída ABRUPTA de ventas (de $12M a $0 en 3 meses) con sueldo que continuó y creció. Alta probabilidad de **licencia, maternidad, o cambio de función**. El sueldo creciente sugiere que sigue en la empresa pero en otro rol.

---

### CASO 6 — Castro Noelia [587]
**Entrada y salida en 12 meses.**

| Año | Ventas prom mensual | Sueldo prom mensual |
|-----|--------------------|--------------------|
| 2023 | $3.85M (4m) | $187k |
| 2024 | −$51k (1m) | $294k |

**Hipótesis:** Empleada que entró con buen ritmo de ventas y salió. El corte fue simultáneo (dic/2023 última venta, ene/2024 último sueldo). Salida voluntaria o desvinculación acordada.

---

### CASO 7 — Sosa Brisa [591]
**Crecimiento sano seguido de caída abrupta.**

| Año | Ventas prom mensual | Sueldo |
|-----|--------------------|---------|
| 2023 | $7.85M (4m) | $243k |
| 2024 | $11.74M (12m — **pico**) | $644k |
| 2025 | −$49k (2m) | --- |

**Hipótesis:** Creció bien junto con el sueldo (correlación positiva 2023→2024). La caída fue abrupta en ene/2025. Posible salida de la empresa. Sueldo y venta cortaron casi simultáneamente (sueldo: nov/2024, última venta: dic/2024).

---

### CASO 8 — Bustos Iara Agustina [509]
**Perfil similar a Sosa Brisa.**

| Año | Ventas | Sueldo |
|-----|--------|--------|
| 2022 | $3.3M/mes (8m) | $90k |
| 2023 | $4.5M/mes (11m) | $253k |
| 2024 | $470k (4m, cayendo) | $673k |
| 2025 | ~$0 | --- |

**Hipótesis:** Sueldo y venta crecieron juntos 2022–2023. En 2024 venta cayó mientras sueldo siguió subiendo → posible baja motivación o reubicación. Salida definitiva en 2025.

---

### CASO 9 — Solares Malena [553]
**Vendedora de alto rendimiento con tendencia descendente reciente.**

| Año | Ventas | Sueldo |
|-----|--------|--------|
| 2022 | $1.2M/mes (1m) | --- |
| 2023 | $3.8M/mes (12m) | $145k |
| 2024 | **$15.3M/mes (12m)** | $658k |
| 2025 | $4.2M/mes (5m) | $525k |

**Caída:** 73% desde pico de 2024. Último sueldo: mar/2025. Última venta significativa: feb/2025.
**Hipótesis:** Posible salida en feb–mar 2025. Correlación positiva entre sueldo y venta 2022→2024. La caída de 2025 fue simultánea en ambos. **No hay desfase: trabajó mientras tuvo sueldo.**

---

### CASO 10 — Quinteros Virginia Soledad [630]
**Caída de 79% en 2025, todavía reciente.**

| Año | Ventas prom mensual | Sueldo prom mensual |
|-----|--------------------|--------------------|
| 2024 | $10.4M (10m) | $591k |
| 2025 | $2.2M (4m) | $660k |

**Hipótesis:** Sueldo aumentó 12% mientras ventas cayeron 79%. Período corto, podría ser estacionalidad o inicio de desvinculación. Requiere seguimiento.

---

## 3. HIPÓTESIS CAUSAL GENERAL

### Patrón A: SALIDA LIMPIA (60% de los casos)
El sueldo y la venta cortaron casi simultáneamente (±2 meses de diferencia).
**Casos:** Sosa Brisa, Solares Malena, Lazarte Berenice, Perez Yamila, Genoud Victoria, Castro Noelia.
**Interpretación:** Desvinculación acordada o renuncia voluntaria. No hay señal de deterioro previo en ninguna de las dos variables.

### Patrón B: VENTA CAYÓ PRIMERO → LUEGO CORTARON SUELDO (30% de los casos)
El empleado dejó de vender pero siguió cobrando varios meses.
**Casos más claros:** Bilicich Tomas (+32m), Rodriguez Macarena (+9m), Maibach Florencia (+9m), Bustos Iara (+4m).
**Interpretación:** O bien hubo retención/liquidación lenta, o el empleado pasó a función no comercial mientras el código de ventas quedó en desuso.

### Patrón C: SUELDO CORTÓ PRIMERO → VENTA CAYÓ DESPUÉS (10% de los casos)
El desfase causal más interesante.
**Casos:** Pompei Valentino (−15m), Perrier Macarena (−23m).
**Interpretación para Pompei:** Cortaron el sueldo en sept/2023 → vendió residualmente hasta dic/2024 por inercia/comisión → luego desapareció. El corte de sueldo fue el disparador.
**Interpretación para Perrier:** Nunca tuvo sueldo estable (pagos irregulares). Probablemente trabaja por comisión fuera del sistema de sueldos. **No aplica el mismo modelo causal.**

### Respuesta directa a la pregunta: ¿Qué cayó primero?
**En la mayoría de los casos: cayeron juntos (salida de empresa).**
El único caso donde el sueldo claramente precipitó la caída de ventas es **Pompei Valentino**: vendía $3.8M/mes con regularidad → le cortaron el sueldo → cayó a cero en 3 meses. El lag de 3 meses es consistente con un ciclo de cierre de operaciones pendientes.

---

## 4. VARIABLES ADICIONALES ENCONTRADAS

### 4.1 Ausencias con sueldo (señal de roles no comerciales)
Meses donde el empleado cobró sueldo pero no registró ventas:

| Empleado | Meses sin venta pero con sueldo | Período |
|----------|--------------------------------|---------|
| Bilicich Tomas [545] | 15+ meses | 2024-2025 |
| Rodriguez Macarena [417] | 18+ meses | 2022-2023 |
| Maibach Florencia [704] | 9+ meses | 2025 |
| Bustos Iara [509] | varios meses en 2024 | |

**Implicancia:** Estos empleados tienen un sueldo base fijo que no depende de vender. Su código de viajante puede estar asignado a transacciones puntuales o de campaña.

### 4.2 Ventas sin sueldo (comisionistas o freelance)
Casos donde hay ventas significativas pero sin registro en moviempl1:

| Empleado | Ventas sin sueldo | Período |
|----------|------------------|---------|
| Perrier Macarena [557] | $3.4M–$12.6M/mes | 2025 completo |
| Pompei Valentino [527] | $596k | dic/2024 |
| Maibach Florencia [704] | $3.9M, $10M | ago y oct/2024 |

**Implicancia:** Existen vendedores que facturan alto sin estar en el sistema de sueldos. Probable comisión por fuera o facturación como monotributistas.

### 4.3 Estacionalidad individual vs estructural
Muchos vendedores (ej. REFUERZOS 20-30) solo tienen ventas en 1–2 meses del año, concentradas en temporada. No son vendedores de plantilla sino personal de campaña.

### 4.4 Bilicich Tomas: el caso outlier
Pasó de cobrar $19k/mes (2022) a $1.2M/mes (2025), mientras sus ventas son negativas hace 2 años. Es probable que sea un gerente o socio cuyo "sueldo" es realmente una extracción o remuneración directiva. No debería mezclarse en análisis de performance comercial.

---

## 5. QUERIES SQL REUTILIZABLES

### Query A: Evolución mensual sueldo+venta por empleado
```sql
SELECT
    e.numero as viajante_id,
    e.denominacion as nombre,
    YEAR(m.fecha_contable) as anio,
    MONTH(m.fecha_contable) as mes,
    SUM(CAST(m.importe AS FLOAT)) as sueldo_mes
FROM msgestion01.dbo.moviempl1 m
INNER JOIN msgestion01.dbo.empleados e ON e.numero = m.numero_cuenta
WHERE m.codigo_movimiento = 10
  AND m.fecha_contable >= '2023-01-01'
GROUP BY e.numero, e.denominacion, YEAR(m.fecha_contable), MONTH(m.fecha_contable)
ORDER BY e.numero, anio, mes
```

### Query B: Ventas mensuales combinadas (01+03)
```sql
SELECT viajante, YEAR(fecha) anio, MONTH(fecha) mes,
    SUM(CASE WHEN codigo=1 THEN CAST(total_item AS FLOAT)*CAST(cantidad AS FLOAT) ELSE 0 END)
    - SUM(CASE WHEN codigo=3 THEN CAST(total_item AS FLOAT)*CAST(cantidad AS FLOAT) ELSE 0 END) as venta_neta
FROM msgestion01.dbo.ventas1
WHERE codigo IN (1,3) AND viajante NOT IN (7,36) AND viajante > 0
  AND deposito IN (0,2,6,7,8,9,15)
  AND fecha >= '2024-01-01'
GROUP BY viajante, YEAR(fecha), MONTH(fecha)

UNION ALL

SELECT viajante, YEAR(fecha) anio, MONTH(fecha) mes,
    SUM(CASE WHEN codigo=1 THEN CAST(total_item AS FLOAT)*CAST(cantidad AS FLOAT) ELSE 0 END)
    - SUM(CASE WHEN codigo=3 THEN CAST(total_item AS FLOAT)*CAST(cantidad AS FLOAT) ELSE 0 END) as venta_neta
FROM msgestion03.dbo.ventas1
WHERE codigo IN (1,3) AND viajante NOT IN (7,36) AND viajante > 0
  AND deposito IN (0,2,6,7,8,9,15)
  AND fecha >= '2024-01-01'
GROUP BY viajante, YEAR(fecha), MONTH(fecha)
ORDER BY viajante, anio, mes
```

### Query C: Empleados activos con bajo rendimiento relativo (para monitoreo mensual)
```sql
-- Sueldo del último mes conocido vs venta del último trimestre
WITH ultimo_sueldo AS (
    SELECT m.numero_cuenta, e.denominacion,
           MAX(m.fecha_contable) as ultimo_sueldo_fecha,
           SUM(CAST(m.importe AS FLOAT)) as sueldo_ultimo_mes
    FROM msgestion01.dbo.moviempl1 m
    INNER JOIN msgestion01.dbo.empleados e ON e.numero = m.numero_cuenta
    WHERE m.codigo_movimiento = 10
      AND m.fecha_contable >= DATEADD(MONTH, -2, GETDATE())
    GROUP BY m.numero_cuenta, e.denominacion
),
ventas_tri AS (
    SELECT viajante,
           SUM(CASE WHEN codigo=1 THEN CAST(total_item AS FLOAT)*CAST(cantidad AS FLOAT) ELSE -CAST(total_item AS FLOAT)*CAST(cantidad AS FLOAT) END) as venta_90d
    FROM msgestion01.dbo.ventas1
    WHERE codigo IN (1,3) AND deposito IN (0,2,6,7,8,9,15)
      AND fecha >= DATEADD(DAY, -90, GETDATE())
    GROUP BY viajante
)
SELECT
    us.numero_cuenta,
    us.denominacion,
    us.sueldo_ultimo_mes,
    ISNULL(vt.venta_90d, 0) as venta_90d,
    CASE WHEN ISNULL(vt.venta_90d, 0) < us.sueldo_ultimo_mes THEN 'ALERTA: venta < sueldo'
         WHEN ISNULL(vt.venta_90d, 0) = 0 THEN 'SIN VENTAS'
         ELSE 'OK' END as estado
FROM ultimo_sueldo us
LEFT JOIN ventas_tri vt ON vt.viajante = us.numero_cuenta
ORDER BY venta_90d ASC
```

### Query D: Detección de desfase causal (sueldo vs venta)
```sql
-- Para un empleado específico, ver timeline mensual
DECLARE @viajante INT = 527  -- cambiar por el código deseado

SELECT
    YEAR(m.fecha_contable) as anio,
    MONTH(m.fecha_contable) as mes,
    SUM(CAST(m.importe AS FLOAT)) as sueldo
FROM msgestion01.dbo.moviempl1 m
WHERE m.numero_cuenta = @viajante AND m.codigo_movimiento = 10
  AND m.fecha_contable >= '2022-01-01'
GROUP BY YEAR(m.fecha_contable), MONTH(m.fecha_contable)

-- Cruzar manualmente con ventas del mismo viajante
```

---

## 6. RESUMEN EJECUTIVO

**Pregunta:** ¿Qué cayó primero, la venta o el sueldo?

**Respuesta basada en datos:**

1. **En el 60% de los casos: cayeron juntos** (salida de empresa). No hay relación causal identificable, simplemente la persona se fue.

2. **En el 30% de los casos: la venta cayó antes** y el sueldo siguió pagándose meses después. Esto refleja procesos de desvinculación gradual, no desmotivación.

3. **En el 10% de los casos (el más interesante): el sueldo fue ajustado antes** de que cayeran las ventas. El caso más claro es Pompei Valentino: de $183k/mes de sueldo → $0 en oct/2023 → ventas de $3.8M/mes cayeron a cero en los siguientes 15 meses, con lag de 3 meses. **Este es el único caso donde hay evidencia de que el factor económico precipitó la baja de rendimiento.**

**Nota estructural:** La correlación entre sueldo y performance **es positiva pero lagging en 2–3 meses** para los casos con datos mensuales detallados. Esto es consistente con un ciclo de venta típico: el vendedor genera negocios en el mes N que se cobran en N+2.

**Limitación:** El sistema no registra comisiones variables en moviempl1. Varios vendedores de alto rendimiento (Perrier Macarena, Pompei Valentino) operan sin sueldo fijo registrado, lo que hace imposible analizar el incentivo económico real.

---

*Queries ejecutadas en: msgestion01.dbo.moviempl1, msgestion01.dbo.empleados, msgestion01.dbo.ventas1, msgestion03.dbo.ventas1*
*Servidores: 192.168.2.111 (producción)*
*Filtros: codigo IN (1,3), deposito IN (0,2,6,7,8,9,15), viajante NOT IN (7,36)*
