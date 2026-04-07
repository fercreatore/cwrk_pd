# DIAGNOSTICO INTEGRAL — Sistema Multicanal + Reposicion
## H4 / CALZALINDO — 31 de marzo de 2026
> Resultado de 10 agentes de investigacion y auditoria ejecutados en paralelo

---

## RESUMEN EJECUTIVO

El sistema construido (app_reposicion + app_multicanal + pipeline pedidos) **esta mas avanzado que el 95% de las zapaterias medianas en Argentina**. El analisis de quiebre de stock es una feature que tools enterprise como Onebeat cobran miles de dolares.

Sin embargo, tiene gaps criticos que impiden que sea una herramienta de decision comercial completa:
- app_multicanal es una herramienta de pricing/config, no de inteligencia comercial
- app_reposicion tiene la logica pero no conecta con el calendario estacional ni con OTB
- El motor de precios ignora costos reales (IIBB, envio fijo, devoluciones, IVA s/comisiones)

---

## PRIORIDAD 1 — CRITICO (hacer ya)

### 1.1 Armar Pedido no usa curva corregida por quiebre
**Archivo**: app_reposicion.py linea 7447
**Problema**: Distribuye talles por ventas brutas, ignorando la correccion de quiebre que es el core del sistema
**Fix**: Reemplazar `pct = t['ventas_12m'] / ventas_total` por output de `curva_talles_real()`
**Impacto**: El fix mas importante de todo el sistema

### 1.2 Safety stock inconsistente (Poisson vs Normal)
**Archivo**: app_reposicion.py lineas 691-694 (JIT) vs 611-621 (standalone)
**Problema**: JIT usa sqrt(lead_time * vel_diaria) [Poisson], standalone usa z * std_empirico [Normal]. Se contradicen.
**Fix**: Unificar en Normal con std empirico (ya calculado en analizar_quiebre_batch)

### 1.3 CALZALINDO invisible en app_multicanal
**Archivo**: app_multicanal.py lineas 184-190
**Problema**: Solo consulta msgestion03 (H4). La mitad del negocio no aparece.
**Fix**: Usar msgestionC (consolidada) o UNION ALL de ambas bases

### 1.4 Formula de margen inconsistente en la misma pagina
**Archivo**: app_multicanal.py lineas 366 vs 404
**Problema**: Una seccion usa precio/1.21 (neto), otra usa precio directo (con IVA)
**Fix**: Unificar todo a precio neto (sin IVA)

### 1.5 IIBB no modelado en motor de precios
**Archivo**: multicanal/precios.py
**Problema**: ~3.6% de IIBB aplica a TODAS las ventas. No esta en ningun canal.
**Fix**: Agregar `iibb_pct` a ReglaCanal, aplicar en formula

---

## PRIORIDAD 2 — IMPORTANTE (hacer esta semana)

### 2.1 Sin senales de demanda en app_multicanal
**Problema**: Cero deteccion de velocidad, aceleracion, tendencias. El dashboard muestra comisiones, no estado del negocio.
**Fix**: Agregar vel_real_articulo como fuente, calcular dias de stock, flags de reorden

### 2.2 Envio modelado como % en vez de costo fijo
**Archivo**: multicanal/precios.py, reglas_canales.json
**Problema**: 4% es correcto para zapas de $50K pero incorrecto para $15K (deberia ser ~10%)
**Fix**: Agregar `envio_fijo` a ReglaCanal (ej: $4,000 ML, $3,000 TN)

### 2.3 Devoluciones no modeladas
**Problema**: ML calzado tiene 5-8% de returns. Cada devolucion cuesta envio ida+vuelta.
**Fix**: Agregar `devolucion_pct` a ReglaCanal (ej: 2% blended para ML)

### 2.4 XYZ usa proxy incorrecto
**Archivo**: app_reposicion.py lineas 815-817
**Problema**: Usa meses_con_venta en vez de coeficiente de variacion (CV = std/mean)
**Fix**: Calcular CV real de ventas mensuales

### 2.5 Bug de redondeo en precios
**Archivo**: multicanal/precios.py linea 161
**Problema**: Si precio cae exacto en multiplo de 100, baja $100 perdiendo margen
**Fix**: Agregar guard `if precio_redondeado < precio_con_recargo: precio_redondeado += regla.redondeo`

### 2.6 Race condition en SQLite dedup facturador
**Archivo**: multicanal/facturador_tn.py lineas 142-176
**Problema**: TOCTOU — dos instancias pueden procesar la misma orden
**Fix**: Usar INSERT OR IGNORE + check rowcount en una sola transaccion

### 2.7 USD historico aplica tipo de cambio actual
**Archivo**: app_multicanal.py linea 170
**Problema**: Aplica cotizacion de hoy a ventas de hace 12 meses
**Fix**: Mostrar warning, o usar costo historico en pesos para meses pasados

---

## PRIORIDAD 3 — MODULOS NUEVOS (plan de desarrollo)

### 3.1 Modulo OTB (Open-to-Buy)
**Que es**: Presupuesto por categoria/temporada. Antes de comprar, saber cuanto PODES gastar.
**Formula**: OTB = Ventas_plan + Markdowns + Stock_fin_deseado - Stock_actual - Pedidos_pendientes
**Datos necesarios**: Todos disponibles en ERP (ventas1, compras1, stock, pedico1/2)
**Prioridad**: ALTA — conecta reposicion con disciplina financiera

### 3.2 WSSI/MSSI (Weekly/Monthly Sales & Stock Intake)
**Que es**: Tracker semanal de ventas vs plan por categoria
**Falta**: El PLAN. Propuesta: usar vel_real * factor_estacional como plan automatico
**UI**: Heatmap de semanas x subrubros, verde/amarillo/rojo vs plan

### 3.3 Calendario estacional con deteccion automatica
**Las 4 fases**: Pre-temporada (compra) → Temporada alta (venta) → Liquidacion → Entretiempo
**Deteccion**: Week-over-week growth >+20% por 3 semanas = temporada arrancando
**Impacto**: El waterfall y ROI optimizer deberian ajustar horizonte segun fase

### 3.4 Sell-through tracker con triggers de markdown
**Targets**: Week 4 <25% → markdown. Week 8 <35% → agresivo. Week 12 <55% → liquidacion.
**Dato clave Dic = 1.51x promedio**: aguinaldo + fiestas hacen diciembre el mes pico absoluto

### 3.5 Estimacion velocidad producto nuevo
**Funcion**: `estimar_velocidad_producto_nuevo(subrubro, marca, precio, genero)`
**Metodo**: Mediana de vel_real de productos similares (mismo subrubro+marca+rango precio)
**Impacto**: Resuelve el cold-start de productos sin historia

### 3.6 Precio de mercado (Buy Box ML)
**Problema**: El motor solo sabe cost-up, no sabe a cuanto vende la competencia
**Fix**: Input de precio_mercado por producto, flag cuando nuestro precio > mercado
**Fuente**: Nubimetrics ($15-40K/mes) o scraping ML API

---

## ESTRATEGIA DE PRICING MULTICANAL (recomendacion consolidada)

### Modelo recomendado: Ancla de mercado + cascada por canal

```
ML Premium = precio de mercado (ancla)
TiendaBNA  = ML * 0.95
TiendaNube = ML * 0.90-0.92
Local      = TN (mismo precio)
Instagram  = Local (con promos flash al 85%)
```

### Comisiones reales 2026 (calzado, Santa Fe, RI)

| Canal | Comision | IVA s/com | Envio | IIBB | Otros | Total no-recuperable |
|-------|----------|-----------|-------|------|-------|---------------------|
| ML Premium | 15.5% | 3.3% | ~4% fijo | 2.5% | - | ~20-21% |
| ML Clasica | 13% | 2.7% | buyer pays | 2.5% | - | ~16-18% |
| TN + Pago Nube 14d | 3.49%+IVA=4.2% | incl | ~3% | 2.5% | - | ~9-10% |
| TN + MercadoPago | 1%+4.39%+IVA=6.3% | incl | ~3% | 2.5% | - | ~12% |
| TiendaBNA | 8%+IVA=9.7% | incl | ~3% | 2.5% | - | ~15% |
| Instagram (transfer) | 0% | - | - | 2.5% | - | ~3% |
| Local (tarjeta) | 2-3% | - | - | 2.5% | - | ~5% |

### Margenes objetivo por canal

| Canal | Margen bruto target | Markup minimo |
|-------|--------------------|--------------|
| ML Premium | 15-25% | 2.5x |
| ML + 6 cuotas s/i | 5-15% | 3.0x |
| TN | 30-40% | 2.0x |
| Local | 50-60% | 1.8x |
| Instagram | 45-55% | 1.8x |

---

## CORRECCIONES A SUBRUBRO_TEMPORADA

Segun datos reales de ventas:

| Subrubro | Config actual | Realidad (datos) | Accion |
|----------|--------------|-----------------|--------|
| CHINELA (6) | Invierno | Dual: pico Dic 1880 + invierno 248 | Recodificar year-round |
| NAUTICO (40) | Escolar | Dual: escolar Feb + verano Nov-Dic | Agregar PV |
| OUTDOOR (51) | Year-round | Sesgo invernal claro May-Jul | Agregar peso OI |
| ZAP VESTIR (20) | Year-round | Ramp Sep-Nov (fiestas) | OK pero agregar nota |

---

## DATOS CLAVE VENADO TUERTO

- **Diciembre = 21,550 pares** (pico absoluto, 1.51x promedio)
- **Octubre = 17,430 pares** (#2, arranca PV fuerte)
- **Valle = Marzo-Abril** (~11,300 pares)
- **Sandalias ratio peak/trough = 315:1** (mas estacional que todo)
- **Heladas**: fines abril a septiembre. 2 semanas mas que Buenos Aires.
- **Escolar (Feb-Mar)**: unica razon por la que febrero supera a enero

---

## PROXIMO PASO INMEDIATO

1. Fix critico: curva de talles en Armar Pedido (app_reposicion.py:7447)
2. Fix critico: unificar safety stock Poisson/Normal
3. Fix critico: CALZALINDO visible en multicanal
4. Agregar IIBB al motor de precios
5. Agregar envio fijo + devoluciones al motor de precios
6. Disenar modulo OTB como Tab 11 de app_reposicion
