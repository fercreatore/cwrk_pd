# Estado del Modulo Calce Financiero - Auditoria 1 de abril de 2026

## 1. Resumen Ejecutivo

Se auditaron 10 tablas analiticas del modulo calce financiero en `omicronvt` (192.168.2.111).
El dashboard (`calce_financiero.py`) tiene **fallbacks correctos** para todas las tablas opcionales:
usa `try/except` con `pass` o listas vacias cuando una tabla no existe.

**NOTA**: La verificacion directa via MCP sql-replica fue denegada en esta sesion.
El estado de las tablas se infiere del CLAUDE.md (que confirma explicitamente que `vel_real_articulo`
NO existe en produccion al 23-mar) y del codigo fuente. Se recomienda verificar ejecutando
las queries SELECT TOP 3 manualmente en SSMS o sqlcmd.

---

## 2. Estado de Tablas Analiticas

| # | Tabla | SQL de creacion | Estado estimado | Dependencias | Notas |
|---|-------|-----------------|-----------------|--------------|-------|
| 1 | `pedidos_cumplimiento_cache` | `crear_cache_pedidos.sql` | **EXISTE** (1235 filas, ver CLAUDE.md) | `v_pedidos_cumplimiento` (vista) | Cache de la vista. SP `sp_sync_pedidos` para refrescar. |
| 2 | `map_subrubro_industria` | `agregar_industrias.sql` | **EXISTE** (referenciada por multiples SPs que ya corren) | Ninguna | Mapping subrubro -> industria. Datos iniciales + 4 adiciones. |
| 3 | `t_presupuesto_industria` | `crear_presupuesto_industria.sql` | **INCIERTO** - dashboard hace try/except y dice "NO EXISTE (normal si no se corrio el SQL)" | `t_periodos_industria`, `vel_real_articulo`, `pedidos_cumplimiento_cache`, `map_subrubro_industria` | SP `sp_calcular_presupuesto`. |
| 4 | `t_periodos_industria` | `crear_presupuesto_industria.sql` (parte 1) | **INCIERTO** - creada por mismo script que t_presupuesto_industria | Ninguna | 6 industrias x INVIERNO 2026. IF NOT EXISTS protege datos. |
| 5 | `t_tendencia_facturacion` | `ajuste_tendencia_presupuesto.sql` | **INCIERTO** - dashboard hace try/except | `map_subrubro_industria` | Facturacion mensual 2024/2025/2026, ratios YoY, estacionalidad 5 anios. |
| 6 | `vel_real_articulo` | `_scripts_oneshot/crear_tabla_vel_real.sql` + `.py` | **NO EXISTE** (confirmado CLAUDE.md 23-mar) | Datos generados por `crear_tabla_vel_real.py` | ~2400 INSERTs generados pero nunca ejecutados. Script `.py` listo. |
| 7 | `t_roi_proveedor` | `crear_calce_avanzado.sql` (MEJORA 2) | **INCIERTO** - dashboard referencia via `db_analitica` (112) | `map_subrubro_industria`, `t_recupero_inversion` | ROI = margen% x rotacion. Score de compra 0-100. |
| 8 | `t_roi_proveedor_temporada` | `crear_calce_avanzado.sql` (MEJORA 2b) | **INCIERTO** | `t_roi_proveedor`, `t_periodos_industria` | Isotipos (proveedores en 2+ temporadas) para benchmark. |
| 9 | `t_capital_trabajo_mensual` | `crear_calce_avanzado.sql` (MEJORA 3) | **INCIERTO** | `t_tendencia_facturacion`, `pedidos_cumplimiento_cache` | Curva de necesidad de capital mar-ago. |
| 10 | `t_enriquecedores_calce` | `crear_calce_avanzado.sql` (MEJORA 4) | **INCIERTO** | `map_subrubro_industria`, `pedidos_cumplimiento_cache` | Margen, concentracion riesgo, stock muerto 90d/180d. |

### Tablas adicionales referenciadas pero no listadas en la solicitud

| Tabla | Referenciada en | Estado |
|-------|----------------|--------|
| `t_recupero_inversion` | dashboard BLOQUE 2 (diagnostico la prueba) | Probablemente EXISTE (diagnostico() la chequea) |
| `t_flujo_caja_semanal` | dashboard BLOQUE 8 | Creada por `crear_calce_avanzado.sql` (MEJORA 1) |
| `t_roi_temporada_media` | `crear_calce_avanzado.sql` | Tabla resumen de isotipos |

---

## 3. Verificacion Manual Requerida

Ejecutar estas queries en SSMS o sqlcmd conectado al 111 para completar la auditoria:

```sql
-- Verificar existencia y conteo de filas
USE omicronvt;

SELECT 't_presupuesto_industria' AS tabla, COUNT(*) AS filas, MAX(fecha_calculo) AS ultima_fecha FROM dbo.t_presupuesto_industria;
SELECT 't_periodos_industria' AS tabla, COUNT(*) AS filas FROM dbo.t_periodos_industria;
SELECT 't_tendencia_facturacion' AS tabla, COUNT(*) AS filas, MAX(fecha_calculo) AS ultima_fecha FROM dbo.t_tendencia_facturacion;
SELECT 'vel_real_articulo' AS tabla, COUNT(*) AS filas, MAX(fecha_calculo) AS ultima_fecha FROM dbo.vel_real_articulo;
SELECT 't_roi_proveedor' AS tabla, COUNT(*) AS filas, MAX(fecha_calculo) AS ultima_fecha FROM dbo.t_roi_proveedor;
SELECT 't_roi_proveedor_temporada' AS tabla, COUNT(*) AS filas, MAX(fecha_calculo) AS ultima_fecha FROM dbo.t_roi_proveedor_temporada;
SELECT 't_capital_trabajo_mensual' AS tabla, COUNT(*) AS filas, MAX(fecha_calculo) AS ultima_fecha FROM dbo.t_capital_trabajo_mensual;
SELECT 't_enriquecedores_calce' AS tabla, COUNT(*) AS filas, MAX(fecha_calculo) AS ultima_fecha FROM dbo.t_enriquecedores_calce;
SELECT 'pedidos_cumplimiento_cache' AS tabla, COUNT(*) AS filas FROM dbo.pedidos_cumplimiento_cache;
SELECT 'map_subrubro_industria' AS tabla, COUNT(*) AS filas FROM dbo.map_subrubro_industria;
SELECT 't_recupero_inversion' AS tabla, COUNT(*) AS filas FROM dbo.t_recupero_inversion;
SELECT 't_flujo_caja_semanal' AS tabla, COUNT(*) AS filas, MAX(fecha_calculo) AS ultima_fecha FROM dbo.t_flujo_caja_semanal;
```

---

## 4. Audit de Fallbacks en dashboard()

El controller `calce_financiero.py` maneja la ausencia de tablas de forma **correcta** en todos los bloques:

| Bloque | Tabla(s) usada(s) | Fallback | Correcto? |
|--------|-------------------|----------|-----------|
| 1: Compromisos | `pedidos_cumplimiento_cache` | `try/except -> compromisos = []` | SI |
| 2: Recupero | `t_recupero_inversion` | `try/except -> recupero = []` | SI |
| 2b: Recupero Real | `vel_real_articulo` + `t_recupero_inversion` | `try/except -> recupero_real = []`, luego fallback a `vel_real_por_industria_resumen()` | SI (doble fallback) |
| 3: KPIs Globales | `pedidos_cumplimiento_cache`, `t_recupero_inversion` | `try/except -> kpi_comp = {}, kpi_rec = {}` | SI |
| 4: Remitos | `compras2` (via dbC) | `try/except -> pass` | SI |
| 5: Presion | `t_recupero_inversion` | `try/except -> proveedores_presion = []` | SI |
| 6: Vencimientos | `pedidos_cumplimiento_cache` | `try/except -> vencimientos = []` | SI |
| 7: Presupuesto | `t_presupuesto_industria` | `try/except -> pass (presupuesto = [])` | SI |
| 7b: Tendencia | `t_tendencia_facturacion` | `try/except -> pass (tendencia_mensual = {})` | SI |
| 8: Flujo Caja | `t_flujo_caja_semanal` (via db_analitica) | `if _db_cfo: try/except -> pass` | SI |
| 9: ROI Proveedor | `t_roi_proveedor`, `t_roi_proveedor_temporada` | `if _db_cfo: try/except -> pass` | SI |
| diagnostico() | Todas las tablas clave | Muestra OK/FALLO/NO EXISTE por cada una | SI |

**Observacion**: `vel_real.py::vel_real_por_industria_resumen()` tambien tiene try/except para
la lectura de `vel_real_articulo`. Si no existe, retorna `{}` y el caller usa `factor_quiebre=1.0`.

---

## 5. Script SQL Consolidado de Creacion (ordenado por dependencias)

Orden de ejecucion en el 111 (cada script se ejecuta con `sqlcmd -S localhost -d omicronvt -i archivo.sql`):

```
PASO 1 (sin dependencias):
   _scripts_oneshot/crear_tabla_vel_real.sql          -- vel_real_articulo (estructura)
   -> Luego ejecutar: python crear_tabla_vel_real.py   -- genera INSERTs y los ejecuta

PASO 2 (requiere map_subrubro_industria que ya existe):
   sql/crear_presupuesto_industria.sql                 -- t_periodos_industria + t_presupuesto_industria + sp_calcular_presupuesto

PASO 3 (requiere t_presupuesto_industria + t_periodos_industria):
   sql/ajuste_tendencia_presupuesto.sql                -- t_tendencia_facturacion + sp_calcular_tendencia (redefine sp_calcular_presupuesto)

PASO 4 (requiere t_tendencia_facturacion + t_recupero_inversion + map_subrubro_industria):
   sql/crear_calce_avanzado.sql                        -- t_flujo_caja_semanal + t_roi_proveedor + t_roi_proveedor_temporada + t_roi_temporada_media + t_capital_trabajo_mensual + t_enriquecedores_calce + sp_calcular_calce_avanzado

PASO 5 (refrescar todo):
   EXEC sp_calcular_presupuesto;                       -- recalcula presupuesto + tendencia
   EXEC sp_calcular_calce_avanzado;                    -- recalcula las 4 mejoras CFO
   EXEC sp_sync_pedidos;                               -- refresca cache de pedidos
```

### Comando de deploy completo (Mac -> 111)

```bash
cd ~/Desktop/cowork_pedidos/_sync_tools
./deploy.sh scripts    # Sube crear_tabla_vel_real.py al 111
./deploy.sh web2py     # Sube calce_financiero.py + vel_real.py + funciones_ranking.py
```

---

## 6. Gaps para Mix Optimizer

Se analizo que metricas EXISTEN y cuales FALTAN para un optimizador de mix de productos:

### Lo que YA EXISTE

| Metrica | Donde | Granularidad |
|---------|-------|--------------|
| Margen bruto % por proveedor | `t_roi_proveedor.margen_bruto_pct` | Proveedor x Industria |
| Margen bruto % por industria | `t_enriquecedores_calce.margen_bruto_pct` | Industria |
| ROI anualizado por proveedor | `t_roi_proveedor.roi_anualizado` | Proveedor x Industria |
| Score de compra (0-100) | `t_roi_proveedor.score_compra` + ranking | Proveedor x Industria |
| Rotacion anual | `t_roi_proveedor.rotacion_anual` (365/dias_50) | Proveedor x Industria |
| Concentracion de riesgo | `t_enriquecedores_calce.top1_pct`, `top3_pct`, `nivel_concentracion` | Industria |
| Stock muerto (90d, 180d) | `t_enriquecedores_calce.stock_muerto_*` | Industria |
| Presupuesto vs comprometido | `t_presupuesto_industria.*` | Industria x Temporada |
| Factor de quiebre | `vel_real_articulo.factor_quiebre` | Articulo (codigo_sinonimo) |
| Tendencia YoY (costo y uds) | `t_tendencia_facturacion.ratio_*` | Industria x Mes |
| Estacionalidad historica | `t_tendencia_facturacion.idx_estacionalidad` | Industria x Mes |
| Recupero de inversion | `t_recupero_inversion` | Proveedor x Industria |
| Isotipos por temporada | `t_roi_proveedor_temporada.es_isotipo` | Proveedor x Periodo |
| Capital de trabajo mensual | `t_capital_trabajo_mensual` | Industria x Mes |

### Lo que FALTA

| Metrica | Descripcion | Prioridad | Complejidad |
|---------|-------------|-----------|-------------|
| **Analisis ABC/Pareto por marca** | Clasificacion A/B/C por contribucion a ventas (80/15/5). Hoy `funciones_ranking.py` calcula ventas por marca pero NO las clasifica en ABC. | ALTA | BAJA - agregar columna `clasificacion_abc` al ranking existente |
| **Contribution margin absoluto** | Margen $ absoluto (no solo %). Hoy existe `margen_bruto_pct` pero NO margen en $ por proveedor/marca/articulo. Un proveedor con 30% margen y $10M venta importa mas que uno con 60% margen y $100K venta. | ALTA | BAJA - ya tiene `venta_total` y `costo_total` en `t_roi_proveedor`, calcular `margen_$ = venta_total - costo_total` |
| **Matriz BCG (estrellas/vacas/perros)** | Cuadrante crecimiento x participacion. Hoy tiene tendencia YoY (`ratio_uds_26v25`) y ventas por marca, pero NO los cruza en una matriz 2x2. | ALTA | MEDIA - cruzar `t_tendencia_facturacion.ratio_uds_26v25` con participacion de mercado relativa por industria |
| **Simulador what-if de presupuesto** | Hoy el presupuesto es estatico (venta anio anterior x factor). No hay forma de simular "si subo 20% Deportes y bajo 10% Zapateria, cual es el impacto en ROI/capital/calce". | MEDIA | ALTA - requiere frontend interactivo (sliders) + recalculo en tiempo real. El SP `sp_calcular_presupuesto` es batch, no interactivo. |
| **GMROI por articulo/marca** | Gross Margin Return on Investment = (margen bruto $ / stock promedio a costo). Existe en `app_reposicion.py` (Streamlit) pero NO en el modulo web2py. | MEDIA | MEDIA - necesita stock promedio mensual (no solo stock actual) |
| **Curva de ciclo de vida del producto** | Fase de cada producto: Introduccion, Crecimiento, Madurez, Declive. Para decidir recompra vs discontinuar. | MEDIA | MEDIA - analizar tendencia de ventas mensuales por CSR/producto |
| **Elasticidad precio-demanda** | Cuando sube el ticket, bajan las unidades? Hoy `var_ticket_prom` en presupuesto lo sugiere pero no lo cuantifica. | BAJA | ALTA - requiere analisis econometrico con multiples variables |
| **Canibalizacion entre marcas** | Si crece Marca A en un subrubro, decrece Marca B? Para evitar comprar marcas que se comen entre si. | BAJA | ALTA - requiere analisis de correlaciones cruzadas |

---

## 7. Recomendaciones de Proximos Pasos

### Inmediato (esta semana)

1. **Ejecutar vel_real_articulo en produccion**
   - Correr `python crear_tabla_vel_real.py` en el 111 para generar el SQL con datos frescos
   - Ejecutar el SQL generado con `sqlcmd -S localhost -d omicronvt -i vel_real_articulo_YYYYMMDD.sql`
   - Esto desbloquea: presupuesto ajustado, recupero real, factor_quiebre en dashboard

2. **Verificar estado real de tablas** (ejecutar queries de la seccion 3 en SSMS)

3. **Ejecutar script consolidado** (seccion 5) para las tablas que no existan

### Corto plazo (1-2 semanas)

4. **Agregar ABC/Pareto a ranking de marcas**
   - En `funciones_ranking.py`, agregar clasificacion ABC a `get_ventas_por_marca()`
   - Columna nueva: `clasificacion_abc` (A=80% acumulado, B=siguiente 15%, C=resto)

5. **Agregar contribution margin absoluto a t_roi_proveedor**
   - `margen_bruto_$ = venta_total - costo_total` (ya tiene los campos, solo falta el calculo)
   - Agregar columna `margen_bruto_absoluto DECIMAL(18,2)` al SP

6. **Crear vista de Matriz BCG**
   - Cruzar crecimiento (ratio_uds_26v25 de tendencia) con participacion (ventas/total ventas industria)
   - Cuadrantes: Estrella (crece + alta participacion), Vaca (estable + alta), Perro (baja + baja), Interrogante (crece + baja)

### Mediano plazo (1 mes)

7. **GMROI en web2py** - Portar logica de `app_reposicion.py` a `funciones_ranking.py`
8. **Simulador what-if** - Probablemente mejor como nueva pagina en Streamlit que como web2py
9. **Ciclo de vida** - Agregar fase (intro/crecimiento/madurez/declive) por CSR basado en tendencia 12 meses

---

## 8. Diagrama de Dependencias entre Tablas

```
map_subrubro_industria (BASE - ya existe)
    |
    +---> t_periodos_industria (configuracion de temporadas)
    |         |
    |         +---> t_presupuesto_industria
    |         |         |
    |         |         +---> t_tendencia_facturacion (ajuste por tendencia)
    |         |
    |         +---> t_roi_proveedor_temporada
    |
    +---> vel_real_articulo (NO EXISTE - ejecutar primero)
    |         |
    |         +---> t_presupuesto_industria (factor_quiebre)
    |         +---> calce_financiero.py BLOQUE 2b (recupero real)
    |         +---> funciones_ranking.py (columna vel_real)
    |
    +---> t_roi_proveedor
    |         |
    |         +---> deuda por industria (dashboard BLOQUE 4b)
    |
    +---> t_enriquecedores_calce
    +---> t_capital_trabajo_mensual
    +---> t_flujo_caja_semanal

pedidos_cumplimiento_cache (ya existe, 1235 filas)
    |
    +---> t_presupuesto_industria (comprometido)
    +---> t_capital_trabajo_mensual (compras estimadas)

t_recupero_inversion (probablemente existe)
    |
    +---> t_roi_proveedor (dias_50, plazo_pago)
    +---> t_flujo_caja_semanal (cobranza estimada)
```

---

## 9. Inventario de SPs

| Stored Procedure | Creado por | Funcion |
|-----------------|------------|---------|
| `sp_calcular_presupuesto` | `ajuste_tendencia_presupuesto.sql` (PARTE 3, redefine el de `crear_presupuesto_industria.sql`) | Calcula presupuesto base + llama `sp_calcular_tendencia` |
| `sp_calcular_tendencia` | `ajuste_tendencia_presupuesto.sql` (PARTE 2) | Facturacion mensual, ratios YoY, estacionalidad, factores de ajuste |
| `sp_calcular_calce_avanzado` | `crear_calce_avanzado.sql` | Flujo de caja + ROI proveedor + capital de trabajo + enriquecedores |
| `sp_sync_pedidos` | `crear_cache_pedidos.sql` | Refresca `pedidos_cumplimiento_cache` desde vista |

---

*Generado: 2026-04-01 por auditoria automatizada*
*Archivos auditados: calce_financiero.py, vel_real.py, funciones_ranking.py, 7 scripts SQL, crear_tabla_vel_real.py*
