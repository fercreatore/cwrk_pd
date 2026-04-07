# Audit: vel_real Calculation — 4 Copies
> Date: 2026-03-25

## Summary

The 4 copies have **significantly drifted**. Copy #1 (app_reposicion.py) was upgraded to a "v3" model with desestacionalizacion, factor de disponibilidad, std_mensual, and ventas_perdidas. The other 3 copies remain on the original simpler algorithm. Additionally, copy #4 (funciones_ranking.py) uses a different function name and processes one CSR at a time instead of batch.

---

## 1. Algorithm Comparison

### Stock Reconstruction (backwards from stock_actual)

All 4 copies use the **same formula**:
```
stock_inicio = stock_fin + ventas - compras
```
And iterate months backwards from today. **No drift here.**

### Quiebre Detection

All 4 copies use:
```
if stock_inicio <= 0: quebrado
```
**No drift here.**

### vel_real Calculation — THIS IS WHERE THEY DIVERGE

| Feature | #1 app_reposicion.py | #2 crear_tabla_vel_real.py | #3 vel_real.py (web2py) | #4 funciones_ranking.py |
|---------|---------------------|---------------------------|------------------------|------------------------|
| **Algorithm version** | v3 (desest + disponibilidad) | v1 (simple) | v1 (simple) | v1 (simple) |
| **vel_real formula** | `(ventas_desest / meses_ok) * factor_disp` | `ventas_ok / meses_ok` | `ventas_ok / meses_ok` | `ventas_ok / meses_ok` |
| **Desestacionalizacion** | YES (divides each month's sales by seasonal factor) | NO | NO | NO |
| **factor_disp (availability correction)** | YES (1.20 if >50% broken, 1.10 if >30%) | NO | NO | NO |
| **100% quiebre fallback** | `vel_ap * 1.15` | `vel_ap` | `vel_ap` | `vel_aparente` |
| **std_mensual** | YES (np.std of ventas_meses_ok) | NO | NO | NO |
| **ventas_perdidas** | YES (2nd pass estimating lost sales) | NO | NO | NO |
| **vel_real_con_perdidas** | YES `(ventas_total + ventas_perdidas) / meses` | NO | NO | NO |
| **vel_base_desest** | YES (returned in results) | NO | NO | NO |
| **factor_disp** | YES (returned in results) | NO | NO | NO |
| **Batch vs single** | Batch (multiple CSRs) | Batch | Batch | **Single CSR** |
| **Data access** | pyodbc via query_df() | pyodbc direct | web2py DAL (dbC.executesql) | web2py DAL (db1.executesql) |

---

## 2. Detailed Differences Per Copy

### Copy #1: `app_reposicion.py::analizar_quiebre_batch()` (line 272)
**THE REFERENCE COPY (most advanced)**

- Uses `factor_estacional_batch()` to get seasonal factors per month
- Accumulates `ventas_desest` by dividing each non-broken month's sales by its seasonal factor
- Applies `factor_disp` (availability correction): 1.20 if >50% broken, 1.10 if >30%, 1.0 otherwise
- 100% quiebre fallback: `vel_ap * 1.15` (not just vel_ap)
- Calculates `std_mensual` via `np.std(ventas_meses_ok)`
- Runs a **second pass** to estimate `ventas_perdidas` for broken months using `vel_base * factor_mes`
- Calculates `vel_real_con_perdidas = (ventas_total + ventas_perdidas) / meses`
- SQL uses `LEFT(a.codigo_sinonimo, 10)` (CSR truncation)
- Returns 12 fields: stock_actual, meses_quebrado, meses_ok, pct_quiebre, vel_aparente, vel_real, vel_base_desest, factor_disp, ventas_total, ventas_ok, std_mensual, ventas_perdidas, vel_real_con_perdidas

### Copy #2: `_scripts_oneshot/crear_tabla_vel_real.py::analizar_quiebre_batch_replica()` (line 90)
**MISSING: desestacionalizacion, factor_disp, std_mensual, ventas_perdidas, vel_real_con_perdidas**

- Simple `vel_real = ventas_ok / meses_ok`
- 100% quiebre fallback: `vel_ap` (no 1.15 multiplier)
- SQL uses `RTRIM(a.codigo_sinonimo)` (full sinonimo, NOT LEFT 10 truncation)
- Returns 5 fields: vel_aparente, vel_real, meses_ok, meses_quebrado, factor_quiebre
- Generated SQL table also has only these 5 data columns + fecha_calculo

### Copy #3: `models/vel_real.py::analizar_quiebre_batch_dal()` (line 37)
**MISSING: desestacionalizacion, factor_disp, std_mensual, ventas_perdidas, vel_real_con_perdidas**

- Simple `vel_real = ventas_ok / meses_ok`
- 100% quiebre fallback: `vel_ap` (no 1.15 multiplier)
- SQL uses `a.codigo_sinonimo` directly (full sinonimo, NOT LEFT 10 truncation)
- Returns 9 fields: stock_actual, meses_quebrado, meses_ok, pct_quiebre, vel_aparente, vel_real, ventas_total, ventas_ok, factor_quiebre
- Has wrapper functions `vel_real_proveedor()` and `vel_real_industria()` that consume the batch results

### Copy #4: `models/funciones_ranking.py::calcular_quiebre_mensual()` (line 469)
**MISSING: desestacionalizacion, factor_disp, std_mensual, ventas_perdidas, vel_real_con_perdidas**

- **NOT a batch function** — processes ONE CSR at a time (performance concern for large sets)
- Simple `vel_real = ventas_con_stock / meses_con_stock`
- 100% quiebre fallback: `vel_aparente` (same as v1)
- Uses different table names: `omicron_ventas1`, `omicron_compras1_remitos` (web2py views) via `db1.executesql`
- SQL filters by `a.codigo_sinonimo='{csr}'` (exact match, not LEFT 10)
- Returns 10 fields: stock_actual, meses_analizados, meses_quebrado, meses_con_stock, pct_quiebre, ventas_total, vel_aparente, vel_real, factor_quiebre, detalle_mensual
- Includes `detalle_mensual` with per-month breakdown (unique to this copy)
- `calcular_pedido_sugerido()` (line 661) consumes this and applies its own factor_estacional on top of vel_real

---

## 3. SQL/Data Access Differences

| Copy | Stock source | Ventas source | Compras source | Sinonimo handling |
|------|-------------|---------------|----------------|-------------------|
| #1 | msgestionC.dbo.stock + LEFT(sinonimo,10) | msgestionC.dbo.ventas1 + LEFT(sinonimo,10) | msgestionC.dbo.compras1 + LEFT(sinonimo,10) | CSR (10 chars) |
| #2 | msgestionC.dbo.stock + RTRIM(sinonimo) | msgestionC.dbo.ventas1 + RTRIM(sinonimo) | msgestionC.dbo.compras1 + RTRIM(sinonimo) | Full sinonimo |
| #3 | msgestionC.dbo.stock + a.codigo_sinonimo | msgestionC.dbo.ventas1 + a.codigo_sinonimo | msgestionC.dbo.compras1 + a.codigo_sinonimo | Full sinonimo |
| #4 | get_stock_actual_csr(csr) | omicron_ventas1 (web2py view) | omicron_compras1_remitos (web2py view) | Exact match |

**Note**: Copy #1 uses LEFT(10) truncation to CSR level, while copies #2 and #3 operate on full codigo_sinonimo. This means they may aggregate differently if there are sinonimos longer than 10 chars with shared prefixes.

---

## 4. Return Field Comparison

| Field | #1 | #2 | #3 | #4 |
|-------|----|----|----|----|
| stock_actual | Y | - | Y | Y |
| meses_quebrado / meses_q | Y | Y | Y | Y |
| meses_ok / meses_con_stock | Y | Y | Y | Y |
| meses_analizados | - | - | - | Y |
| pct_quiebre | Y | - | Y | Y |
| vel_aparente | Y | Y | Y | Y |
| vel_real | Y | Y | Y | Y |
| factor_quiebre | - | Y | Y | Y |
| ventas_total | Y | - | Y | Y |
| ventas_ok | Y | - | Y | - |
| vel_base_desest | **Y** | - | - | - |
| factor_disp | **Y** | - | - | - |
| std_mensual | **Y** | - | - | - |
| ventas_perdidas | **Y** | - | - | - |
| vel_real_con_perdidas | **Y** | - | - | - |
| detalle_mensual | - | - | - | **Y** |

---

## 5. Impact Assessment

| Copy | Where used | Impact of drift |
|------|-----------|-----------------|
| #1 (app_reposicion.py) | Streamlit dashboard, safety stock calc, ABC-XYZ | **Reference** - has the best vel_real estimate |
| #2 (crear_tabla_vel_real.py) | Generates omicronvt.dbo.vel_real_articulo table | **HIGH** - table is consumed by calce_financiero and presupuesto. Uses simple vel_real, so the materialized table underestimates demand for articles with seasonal patterns or high quiebre |
| #3 (vel_real.py) | web2py calce_financiero, vel_real_por_industria_resumen | **MEDIUM** - used as fallback when materialized table doesn't exist. Same underestimation as #2 |
| #4 (funciones_ranking.py) | web2py ranking module, pedido sugerido | **MEDIUM** - single-CSR processing is slow for large sets. However, `calcular_pedido_sugerido()` applies factor_estacional on top, partially compensating for missing desestacionalizacion |

---

## 6. Recommendations

1. **Copies #2, #3, #4 should adopt the v3 algorithm** from copy #1: desestacionalizacion, factor_disp, and the 1.15 fallback for 100% quiebre.

2. **std_mensual and ventas_perdidas** should be added to copy #2 (crear_tabla_vel_real.py) so the materialized table includes them. Copies #3 and #4 can optionally include them.

3. **Copy #2 sinonimo handling**: Currently uses full RTRIM(sinonimo) while copy #1 uses LEFT(10). Should be aligned to whichever is the correct business key (likely LEFT 10 = CSR).

4. **Copy #4 should be converted to batch** or should call `analizar_quiebre_batch_dal()` from vel_real.py instead of reimplementing the loop. The single-CSR approach will be slow for `analizar_marca_para_pedido()` which iterates over all CSRs of a marca.

5. **Add vel_base_desest and factor_disp columns** to the CREATE TABLE in copy #2 so downstream consumers (calce_financiero, presupuesto) can use them.
