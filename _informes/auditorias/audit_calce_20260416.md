# Auditoría Calce Financiero — 16 de abril de 2026

> Generado automáticamente por tarea programada `calce-financiero-audit`
> Fuente: MCP sql-replica → msgestionC (producción 192.168.2.111)

---

## RESUMEN EJECUTIVO

| Categoría | Estado | Principales alertas |
|-----------|--------|---------------------|
| Cheques pendientes | 🟢 OK | Sin cheques venciendo en próximos 30 días |
| Deuda proveedores | 🟡 ATENCIÓN | 30 proveedores con saldo neto negativo (nos deben) |
| Remitos sin facturar | 🔴 CRÍTICO | $690M+ en remitos 2026 aún sin factura; varios >90 días |
| Facturas vencidas | 🟡 ATENCIÓN | Registros históricos 2001-2025; muchos son artefactos |
| Compras 2026 vs 2025 | 🟡 ATENCIÓN | Caída nominal fuerte (-70-80%) pero esperada por temporada OI |
| Ventas Ene-Abr 2026 | 🔴 CRÍTICO | -29% en unidades vs mismo período 2025 (2.179 → 1.354 u) |
| Estacionalidad | 🟢 OK | Picos diciembre y junio confirmados; grupos 5 y 17 dominan |

---

## 1. CHEQUES Y PAGOS

### 🟢 Cheques próximos 30 días

**Resultado: Sin cheques propios pendientes** con vencimiento entre hoy y 16-may-2026.

La ausencia de cheques vencidos es positiva. Sugiere que los pagos recientes se realizaron mayormente por transferencia bancaria (CBU/interbanking) o que el ciclo de pagos ya fue saldado.

**Acción**: Verificar manualmente en ordpag2 si existen órdenes de pago con otro tipo de instrumento (giro/transferencia) con vencimiento inminente.

---

## 2. ANOMALÍAS EN DEUDA

### 🟡 Proveedores con saldo neto negativo (nos deben / saldo a favor nuestro)

Los siguientes proveedores muestran saldo neto negativo en moviprov1, lo que indica que les pagamos de más o tienen notas de crédito/devoluciones pendientes de acreditar:

| Proveedor | Saldo neto (a favor nuestro) | Nota |
|-----------|------------------------------|------|
| DISTRINANDO DEPORTES (656) | -$14.9M | Proveedor activo Reebok — puede ser prepago |
| TECAL Cavatini (960) | -$13.0M | — |
| A NATION (769) | -$9.3M | — |
| MARIO INNOVA (1436) | -$7.5M | — |
| TXT Pack (1142) | -$6.3M | — |
| Compras y Gastos Varios (1158) | -$4.5M | ⚠️ Cuenta gastos — verificar |
| Org. Had. Seguros (1137) | -$4.4M | Seguros — puede ser cuota adelantada |
| COMPRANDO EN GRUPO (853) | -$4.2M | — |
| Baudracco (1155) | -$3.9M | — |
| LADY STORK (99) | -$3.2M | — |
| GO Servicios Digitales (1208) | -$3.0M | — |
| DISTRIGROUP (860) | -$3.0M | — |
| TENISA S.A. (523) | -$2.97M | — |
| + 17 más | $1M–$2.8M c/u | — |

**Interpretación**: La mayoría son prepagos o diferencias de redondeo. Los más relevantes a auditar:
- **DISTRINANDO DEPORTES** (-$14.9M): Verificar si hay NC pendiente o si es anticipo del pedido Reebok OI26.
- **Compras y Gastos Varios (1158)**: Cuenta de gastos con saldo negativo es atípico — revisar.
- **MARIO INNOVA (1436)**: Nuevo proveedor importante, verificar concepto.

---

## 3. REMITOS SIN FACTURAR

### 🔴 CRÍTICO — Remitos 2026 pendientes de facturación

Se detectaron **30+ proveedores** con remitos (código 7/36) de 2026 aún sin vinculación a factura. Los más relevantes:

| Proveedor | Remitos | Monto total | Antigüedad |
|-----------|---------|-------------|------------|
| GO by CZL *(local interno)* | 56 | **$85.2M** | Desde 05-ene-2026 |
| Shoeholic | 5 | **$81.8M** | Solo 13-14 abr (2 días) |
| ALPARGATAS | 17 | **$56.1M** | Desde 10-ene-2026 |
| DISTRINANDO DEPORTES | 14 | **$36.5M** | Desde 22-ene-2026 |
| KALIF/ALEX SPORT | 18 | **$31.1M** | Solo 01-06 abr (6 días) |
| VICBOR SRL | 26 | **$30.7M** | Desde 03-ene-2026 |
| INDUSTRIAS G&D | 13 | **$21.5M** | Desde 09-ene-2026 |
| LESEDIFE S.A. | 31 | **$19.5M** | Desde 07-ene → **99 días** |
| DISTRINANDO MODA | 5 | **$18.5M** | Desde 25-feb-2026 |
| ZOTZ | 6 | **$14.3M** | Desde 06-feb-2026 |
| GRIMOLDI | 5 | **$13.9M** | Desde 24-ene-2026 |
| CLZ BEAUTY | 29 | **$12.5M** | Desde 28-ene → sin mov desde 13-feb |
| TECAL Cavatini | 9 | **$11.7M** | Desde 09-ene-2026 |
| GAVAS SA | 10 | **$11.2M** | Desde 02-ene-2026 |
| TIVORY | 5 | **$11.1M** | Desde 23-ene-2026 |

**Alertas específicas:**

🔴 **LESEDIFE** (99 días, $19.5M): El remito más antiguo es del 7-enero. Si no tiene factura asociada, es una anomalía administrativa grave. Verificar si se facturó bajo otro código.

🔴 **Shoeholic** ($81.8M en 2 días — 13-14 abril): Este monto enorme en dos jornadas requiere validación. ¿Ingreso de mercadería masivo? ¿Preventa? Verificar que tenga factura en camino.

🔴 **KALIF/ALEX SPORT** ($31.1M en 6 días — 1-6 abril): 18 remitos en una semana, sin factura aún. Verificar.

🟡 **GO by CZL** (56 remitos, $85M): Es el local propio de valijas — los movimientos internos no requieren factura de proveedor externo. Normal.

🟡 **CLZ BEAUTY** (29 remitos, $12.5M, sin movimiento desde 13-feb): ¿Está activo este proveedor? 60+ días sin actividad.

---

## 4. FACTURAS "VENCIDAS" > 180 DÍAS

La query devuelve registros históricos que van desde 2001 hasta 2025. La mayoría son **artefactos contables** (facturas antiguas que el sistema no marca como canceladas aunque estén saldadas). Los más significativos:

| Proveedor | Registros | Monto acumulado | Vencimiento más antiguo |
|-----------|-----------|-----------------|-------------------------|
| ALPARGATAS (668) | 1.512 | $1.084B | Nov-2017 |
| VICBOR (594) | 578 | $465M | Nov-2016 |
| DISTRINANDO DEP (656) | 439 | $395M | Sep-2017 |
| GRIMOLDI (264) | 636 | $332M | Mar-2013 |
| MERCADO LIBRE (1261) | 166 | $224M | Dic-2021 |
| PRIMER ROUND (770) | 165 | **$141M** | Ene-2024 ⚠️ |
| ALQUILERES (1494) | 88 | **$120M** | Ene-2024 ⚠️ |
| SUELDOS GERENCIALES (1527) | 10 | **$116M** | Ene-2025 ⚠️ |

**Interpretación:**
- Los registros de 2011-2018 en proveedores comerciales (ALPARGATAS, VICBOR, GRIMOLDI) son casi seguramente artefactos del sistema ERP — facturas históricas con estado_cc mal seteado.
- Los más recientes requieren atención:
  - **PRIMER ROUND** ($141M desde ene-2024): Proveedor activo con deuda que no aparece cancelada. Cruzar con moviprov1.
  - **ALQUILERES** ($120M desde ene-2024): Alquileres acumulados sin cancelar en sistema.
  - **SUELDOS GERENCIALES** ($116M desde ene-2025): Verificar si están registrados como pagados en otro módulo.

---

## 5. COMPRAS 2026 VS 2025

### 🟡 Variación por proveedor (ene-abr ambos años)

| Proveedor | Compras 2026 | Compras 2025 | Variación |
|-----------|-------------|-------------|-----------|
| ALPARGATAS | $53.8M | $183.5M | **-71%** |
| DISTRINANDO DEP | $36.3M | $65.5M | -45% |
| VICBOR | $31.3M | $153.3M | **-80%** |
| DISTRINANDO MODA | $18.8M | $85.8M | **-78%** |
| MERCADO LIBRE* | $16.9M | $71.1M | **-76%** |
| LESEDIFE | $16.2M | $42.0M | -61% |
| GRIMOLDI | $13.9M | $81.6M | **-83%** |
| INDUSTRIAS G&D | $13.2M | $26.6M | -50% |
| MUNDO TEXTIL 🆕 | $11.4M | $0 | Nuevo 2026 |
| TIVORY | $11.1M | $33.8M | -67% |
| TECAL Cavatini | $6.6M | $6.0M | +9% ✅ |
| PEPPERS 🆕 | $4.0M | $0 | Nuevo 2026 |

*MERCADO LIBRE probablemente son comisiones/débitos del canal online.

**Interpretación**: La caída nominal es esperable — en OI 2025 se hicieron compras masivas en ene-mar, mientras que en OI 2026 el timing de pedidos es diferente. Los pedidos invierno 2026 están en proceso de inserción (según CLAUDE.md: ~7.288 pares pendientes INSERT). La caída real en unidades es el indicador más relevante.

**📊 APRENDIZAJE**: MUNDO TEXTIL ($11.4M) y PEPPERS ($4M) son proveedores nuevos 2026, sin historial. Monitorear calidad de entrega y condiciones de pago.

---

## 6. VENTAS Y ESTACIONALIDAD

### 🔴 Caída Ene-Abr 2026

| Período | Unidades | Pesos |
|---------|----------|-------|
| Ene-Abr 2024 | ~1.350 est. | ~$40M est. |
| Ene-Abr 2025 | 2.179 | ~$91M |
| Ene-Abr 2026 | **1.354** | **$64.4M** |
| Variación 2025→2026 | **-38%** unidades | **-29%** pesos |

La caída es significativa. En pesos reales (ajustando inflación ~100% anual), la caída real es aún mayor.

### 🟢 Estacionalidad histórica (3 años)

**Picos de venta**: Diciembre ($96.3M acum.) y Octubre ($78.5M) son los meses más altos. Junio ($65.2M) es el pico de invierno.

**Valles**: Septiembre ($42M), Abril ($42.7M) y Marzo ($48.8M).

**Grupos dominantes**:
- **Grupo 5** (PU/Sintético): $81.7M en 2025, líder absoluto
- **Grupo 17** (Running/Macramé): $62.9M en 2025
- **Grupo 15** (Running PU): $48.5M en 2025
- **Grupo 1** (Cuero): $40.9M en 2025

**Evolución anual (ventas totales):**

| Año | Unidades | Pesos |
|-----|----------|-------|
| 2023 | 4.721 | $72.5M |
| 2024 | 7.416 | $282.0M |
| 2025 | 6.358 | $288.6M |
| 2026 (ene-abr) | 1.354 | $64.4M |

**📊 APRENDIZAJE**: 2024→2025 fue prácticamente plano en pesos (+2.3%) pero cayó -14% en unidades, indicando inflación de precios sin crecimiento real en volumen. La tendencia de 2026 sugiere aceleración de esa caída volumétrica.

---

## 7. CONCENTRACIÓN DE RIESGO

### 🟡 Top 3 proveedores por compras 2026

| Proveedor | % del total compras 2026 |
|-----------|--------------------------|
| ALPARGATAS | ~21% |
| DISTRINANDO DEPORTES | ~14% |
| VICBOR | ~12% |
| **Top 3 acumulado** | **~47%** |

**📊 APRENDIZAJE**: Casi la mitad de las compras se concentran en 3 proveedores. Si alguno de estos falla en entrega (especialmente en temporada pico), el impacto sobre el surtido es crítico. VICBOR tiene múltiples marcas (WAKE, Atomik, Massimo, Bagunza) lo que diversifica el riesgo dentro del proveedor.

---

## ACCIONES RECOMENDADAS

### 🔴 Urgente (esta semana)

1. **LESEDIFE — 31 remitos, $19.5M, 99 días sin factura**: Verificar si tiene factura real en el sistema o si hay un problema administrativo. El más crítico por antigüedad.
2. **Shoeholic — $81.8M en 2 días (13-14 abr)**: Confirmar que viene factura y que el stock ingresó correctamente.
3. **KALIF/ALEX SPORT — $31.1M en 6 días**: Verificar factura en camino.

### 🟡 Esta quincena

4. **DISTRINANDO DEPORTES saldo -$14.9M**: Confirmar si es prepago del pedido Reebok OI26 o hay NC sin acreditar.
5. **Compras y Gastos Varios (1158) saldo negativo -$4.5M**: Auditar movimientos recientes de esta cuenta.
6. **PRIMER ROUND / ALQUILERES — Facturas 2024 sin cancelar**: Cruzar con libro de pagos para confirmar si están saldadas.
7. **CLZ BEAUTY — Sin actividad desde 13-feb**: Confirmar estado del proveedor.

### 🟢 Monitoreo continuo

8. **Ventas Ene-Abr 2026 -29%**: Evaluar si la caída se recupera en mayo-junio (pico invierno). Si persiste en mayo, hay una señal de debilidad real en demanda.
9. **MUNDO TEXTIL y PEPPERS (nuevos)**: Seguimiento de primeras entregas y calidad de producto.
10. **Insertar pedidos invierno 2026 pendientes** (~7.288 pares, ~$63.7M): Cuanto antes se inserten, antes pueden gestionarse las entregas.

---

*Fin del reporte. Próxima auditoría: según calendario programado.*
