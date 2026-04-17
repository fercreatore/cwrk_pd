# Auditoría Calce Financiero — 09/04/2026
> Generado automáticamente por tarea programada `calce-financiero-audit`
> Base: msgestionC (UNION H4 + CALZALINDO), MCP sql-replica (solo SELECT)

---

## RESUMEN EJECUTIVO

| Semáforo | Área | Hallazgo Principal |
|----------|------|--------------------|
| 🔴 CRÍTICO | Cheques urgentes | $27.3M vencen en 7 días, pico $19.9M el 17/04 |
| 🔴 CRÍTICO | Remitos sin facturar | $340M+ en compras 2026 sin factura (estado_cc null) |
| 🟡 ATENCIÓN | Saldos negativos proveedores | KALIF $33.3M, DISTRINANDO DEPORTES $23.7M, TECAL $19.5M "nos deben" |
| 🟡 ATENCIÓN | Concentración cheques 30 días | $92.8M comprometidos — DISTRINANDO MODA+VICBOR+DEP > $138M |
| 🟡 ATENCIÓN | Facturas 2021 sin cancelar | Posibles asientos migración con fechas incorrectas |
| 🟢 OK | Deuda huérfana | Sin proveedores >$5M con deuda y sin compras en 6 meses |
| 🟢 OK | Actividad reciente | Última venta registrada: 08/04/2026 |

---

## 1. ANOMALÍAS EN DEUDA

### 1.1 Proveedores con saldo neto negativo (nos deben / overpago)

> Interpretación: saldo negativo = les pagamos MÁS de lo que facturaron. Puede deberse a remitos recibidos aún no facturados.

| Proveedor | # | Saldo (nos deben) | Remitos pend. 2026 | Diferencia |
|-----------|---|------------------|--------------------|------------|
| KALIF - ALEX SPORT | 817 | **$33.3M** | $31.1M (18 remitos) | ~$2.2M sin explicar |
| DISTRINANDO DEPORTES | 656 | **$23.7M** | $36.5M (14 remitos) | Cuadra (remitos > saldo) |
| TECAL Cavatini | 960 | **$19.5M** | $9.2M (7 remitos) | **~$10.3M sin explicar** |
| GRIMOLDI | 264 | $13.7M | $13.9M (5 remitos) | OK (cuadra) |
| DISTRINANDO MODA | 713 | $12.9M | $18.5M (5 remitos) | OK |
| A NATION | 769 | $9.3M | — | 🔴 Sin remitos visibles |
| MARIO INNOVA | 1436 | $7.5M | — | 🔴 Sin remitos visibles |
| TXT Pack | 1142 | $6.3M | — | Cuadra con cheques pendientes |
| COMPRANDO EN GRUPO | 853 | $4.2M | — | Verificar |
| Baudracco | 1155 | $3.9M | — | Verificar |
| Org. Had. Seguros | 1137 | $3.3M | — | Probable pago adelantado póliza |
| LADY STORK | 99 | $3.2M | — | Verificar |
| GO Servicios Digitales | 1208 | $3.0M | — | Verificar |
| TENISA S.A. | 523 | $3.0M | — | Verificar |
| MERCADO LIBRE | 1261 | $2.6M | — | Posible devolución/cobro |
| RAPICUOTAS | 1497 | $2.2M | — | Verificar |
| DISTRIGROUP | 860 | $2.0M | — | Verificar |

**🔴 Casos críticos para verificar:** TECAL ($10.3M sin remitos que lo expliquen), A NATION ($9.3M sin actividad visible), MARIO INNOVA ($7.5M sin actividad visible).

**Nota metodológica:** 1158 "Compras y Gastos Varios" aparece con saldo -$4.5M pero es cuenta catch-all (gastos), excluida del análisis comercial.

### 1.2 Deuda huérfana (>$5M sin compras en 6 meses)

🟢 **Sin resultados.** Ningún proveedor con saldo deudor >$5M tiene más de 6 meses sin compras.

### 1.3 Facturas con vencimiento >180 días sin cancelar

> ⚠️ Muchas filas muestran `fecha_vencimiento` en 2021 con `fecha_comprobante` en 2024 — anomalía de carga (vencimiento anterior a emisión). Probables asientos de migración. Las fechas de vencimiento = `fecha_comprobante` sugieren facturas de pago inmediato cargadas masivamente.

| Proveedor | # | Monto | Vto. | Días vencida | Observación |
|-----------|---|-------|------|-------------|-------------|
| Telecom Argentina | 438 | $51.5K | ago-2021 | 1,694 | Asiento migración |
| DOLO JAZMIN/INDRA | 855 | $292K | oct-2021 | 1,647 | Asiento migración |
| Grupo Inversia | 572 | $250K | oct-2021 | 1,647 | Asiento migración |
| VICBOR SRL | 594 | **$1.84M** | oct-2021 | 1,639 | 🟡 Verificar con VICBOR |
| Escorpión | 120 | **$1.65M** | oct-2021 | 1,635 | 🟡 Verificar |
| RIMON CASSIS | 664 | $729K | feb-2023 | 1,155 | 🟡 Posible real |
| CALZADOS BLANCO | 614 | **$5.4M** | ene-2024 | 826 | 🟡 Monto significativo |

**Acción recomendada:** Revisar VICBOR $1.84M, Escorpión $1.65M y CALZADOS BLANCO $5.4M con contador para determinar si son deudas reales o asientos de conversión.

---

## 2. RECUPERO DE INVERSIÓN

### 2.1 Limitación detectada — dato para mejora del sistema

🔴 **El campo `ventas1.cuenta_proveedor` está sin poblar (0 de 207,734 registros en 2025-2026).**

Esto impide calcular automáticamente el ROI por proveedor (% vendido / capital invertido). La vinculación ventas→proveedor requiere ir via `ventas1.articulo → articulo.proveedor`, lo cual no se implementó en esta versión del audit.

### 2.2 Inversión por proveedor OI2026 (jul-2025 a la fecha)

| Proveedor | Total comprado (s/IVA) | Notas |
|-----------|----------------------|-------|
| ALPARGATAS S.A.I.C. | **$143.5M** | Mayor inversión |
| VICBOR SRL | $82.3M | |
| DISTRINANDO MODA | $76.7M | |
| Shoeholic | $68.5M | ¿Intercompany? Verificar |
| DISTRINANDO DEPORTES | $54.1M | |
| GRIMOLDI | $44.5M | |
| MERCADO LIBRE | $42.9M | ¿Comisiones/cargos ML? |
| LESEDIFE S.A. | $38.4M | |
| TIVORY TRADING | $29.6M | |
| INDUSTRIAS G&D | $21.5M | |
| PRIMER ROUND | $21.3M | |
| GLOBAL BRANDS | $20.6M | Reebok/OLK |
| VERSATO | $20.2M | |
| ROFREVE | $18.3M | |

**📊 APRENDIZAJE:** Shoeholic (cuenta 2) con $68.5M en "compras" es anómalo — puede ser una cuenta de transferencia interna entre razones sociales. Similar a GO BY CZL (cuenta 17) en remitos. Requiere clasificación.

---

## 3. CHEQUES Y PAGOS

### 3.1 URGENTE — Cheques vencen en 7 días (10-16 abril 2026)

| Fecha | Beneficiario | Cheque | Monto |
|-------|-------------|--------|-------|
| **10/04 HOY** | TIVORY TRADING CO S.A. | 63660896 | **$2,453,039** |
| 10/04 | Compras y Gastos Varios | 314 | $1,500,000 |
| 13/04 | **DISTRINANDO MODA** | 64598174 | **$7,000,000** |
| 13/04 | DISTRINANDO MODA | 563335/565131/574151 | $1,438,621 (3 ch.) |
| 13/04 | DISTRINANDO DEPORTES | 553187/90/86/14/74/02 | $967,921 (6 ch.) |
| 13/04 | TXT Pack | 9411622 | $350,000 |
| 13/04 | PIANINO SRL | 570649 | $479,540 |
| 13/04 | RIMON CASSIS | 561551/574150 | $959,081 (2 ch.) |
| 14/04 | Gondolino | 565129/568898 | $706,756 (2 ch.) |
| 14/04 | CALZADOS GUNAR | 553216/18/97 | $360,343 (3 ch.) |
| 14/04 | DISTRINANDO MODA | 568899 | $93,733 |
| **15/04** | **DISTRINANDO MODA** | 63712064 | **$5,000,000** |
| **16/04** | **DISTRINANDO DEPORTES** | 64598534 | **$3,400,000** |

**Total próximos 7 días: ~$24.7M**

### 3.2 Calendario cheques próximos 30 días

| Fecha | Cheques | Total |
|-------|---------|-------|
| 10/04/2026 | 8 | $3,953,039 |
| 13/04/2026 | 14 | $11,195,163 |
| 14/04/2026 | 6 | $1,160,832 |
| 15/04/2026 | 1 | $5,000,000 |
| 16/04/2026 | 2 | $6,951,460 |
| **17/04/2026** | **9** | **$19,860,626** 🔴 PICO |
| 20/04/2026 | 2 | $1,850,000 |
| 21/04/2026 | 1 | $890,307 |
| 23/04/2026 | 4 | $6,542,704 |
| 24/04/2026 | 3 | $8,000,000 |
| 27/04/2026 | 2 | $6,000,000 |
| 29/04/2026 | 1 | $2,000,000 |
| 30/04/2026 | 11 | $13,961,626 |
| 03/05/2026 | 1 | $750,000 |
| 04/05/2026 | 1 | $2,650,000 |
| 08/05/2026 | 1 | $2,000,000 |
| **TOTAL** | **67** | **$92,766,557** |

🔴 **El 17/04 es el día más crítico: $19.86M en 9 cheques.** Verificar disponibilidad de fondos.

### 3.3 Concentración de riesgo por proveedor

| Proveedor | Cheques pendientes | Total comprometido |
|-----------|-------------------|-------------------|
| DISTRINANDO MODA | 20 | $49,982,176 |
| VICBOR SRL | 19 | $50,460,109 |
| DISTRINANDO DEPORTES | 14 | $37,716,024 |
| KALIF - ALEX SPORT | 11 | $25,240,732 |
| CALZADOS FERLI | 10 | $8,645,668 |
| TXT Pack | 9 | $6,288,000 |
| TIVORY TRADING | 9 | $13,263,905 |
| CALZADOS BLANCO | 7 | $1,081,765 |
| BALL ONE | 7 | $3,672,056 |
| INDUSTRIAS G&D | 6 | $15,269,917 |

🔴 **Los 3 top (DIST. MODA + VICBOR + DIST. DEP.) concentran $138.2M = ~67% del total comprometido.**

---

## 4. REMITOS SIN FACTURAR (compras2, código 7, 2026)

> `estado_cc = null` en todos → remitos pendientes de facturación.

| Proveedor | Remitos | Monto total | Días desde 1er remito |
|-----------|---------|------------|----------------------|
| GO by CZL (cuenta 17) | 52 | **$83.7M** | 94 días ⚠️ |
| ALPARGATAS S.A.I.C. | 15 | **$53.8M** | 89 días 🔴 |
| DISTRINANDO DEPORTES | 14 | **$36.5M** | 77 días 🔴 |
| KALIF - ALEX SPORT | 18 | $31.1M | 8 días ✅ |
| VICBOR SRL | 30 | $30.6M | 96 días 🔴 |
| LESEDIFE S.A. | 31 | $19.5M | 92 días 🔴 |
| DISTRINANDO MODA | 5 | $18.5M | 43 días 🟡 |
| ZOTZ | 6 | $14.3M | 62 días 🟡 |
| GRIMOLDI | 5 | $13.9M | 75 días 🔴 |
| CLZ BEAUTY | 29 | $12.5M | 71 días 🟡 |
| GAVAS SA | 10 | $11.2M | 97 días 🔴 |
| TIVORY TRADING | 5 | $11.1M | 76 días 🔴 |
| PRIMER ROUND SRL | 13 | $9.6M | 73 días 🔴 |
| BALL ONE S.R.L. | 11 | $9.3M | 47 días 🟡 |
| Souter S.A. (RINGO) | 5 | $9.3M | 69 días 🟡 |
| TECAL Cavatini | 7 | $9.2M | 90 días 🔴 |
| INDUSTRIAS G&D | 6 | $9.1M | 90 días 🔴 |
| TIMMi (NEW SHOES) | 13 | $8.6M | 96 días 🔴 |
| CALZADOS BLANCO | 4 | $8.1M | 35 días ✅ |
| SARANG TONGSANG | 8 | $8.0M | 84 días 🔴 |

**Observaciones:**
- **GO by CZL (cuenta 17)** con $83.7M y 52 remitos parece ser intercompany (transferencias internas GO BY CLZ). Requiere verificación — si es un canal propio, estos no son deuda a terceros.
- **ALPARGATAS $53.8M con 89 días** — monto muy significativo. ¿Se acordó financiación extendida o las facturas no llegaron?
- **Remitos >90 días** (GAVAS, VICBOR, LESEDIFE, TIMMi, TECAL, INDUSTRIAS G&D): anomalía administrativa que puede indicar que las facturas no están siendo cargadas al sistema.
- Total estimado en remitos pendientes 2026: **>$350M** (incluyendo todos en la tabla).

---

## 5. PRESUPUESTO Y EJECUCIÓN

🟡 **No disponible.** La tabla de presupuesto por industria (`crear_presupuesto_industria.sql`) figura como pendiente de desarrollo en CLAUDE.md. Sin tabla de referencia presupuestaria, no se pueden calcular % de ejecución ni detectar sobrecompra/subcompra por industria.

**Acción pendiente:** Ejecutar `crear_presupuesto_industria.sql` para habilitar este control en futuras auditorías.

---

## 6. PATRONES HISTÓRICOS

### 6.1 Estacionalidad y actividad

- **Última venta registrada:** 08/04/2026 (actividad normal en la fecha de auditoría)
- **Volumen ventas1 desde ene-2025:** 207,734 registros de detalle
- Los datos de ventas por marca/rubro son accesibles via `ventas1 JOIN articulo` (campo `articulo` → `articulo.codigo`)

### 6.2 Aprendizaje sobre estructura de datos

📊 **El campo `ventas1.cuenta_proveedor` no está siendo populado** (0/207,734 registros con valor). Esto es limitante para futuras auditorías que requieran cruzar ventas vs. proveedor directamente. La ruta alternativa es: `ventas1.articulo → msgestion01art.dbo.articulo.proveedor`.

### 6.3 Inversión por proveedor — temporada OI2026

Los 5 mayores proveedores por volumen de compra en temporada actual concentran ~$401M:
- ALPARGATAS ($143.5M) + VICBOR ($82.3M) + DISTRINANDO MODA ($76.7M) + DISTRINANDO DEPORTES ($54.1M) + GRIMOLDI ($44.5M) = **$401.1M**

El top 5 representa una concentración de proveedor significativa. Si ALPARGATAS tuviera problemas de abastecimiento, impacto sería $143.5M en stock.

---

## 7. ANOMALÍAS ADICIONALES DETECTADAS

### 7.1 "Shoeholic" (cuenta 2) — $68.5M en compras OI2026
Aparece como el 4to mayor "proveedor" en compras pero no figura en la tabla de proveedores activos del CLAUDE.md. Podría ser:
- Una cuenta de transferencia intercompany (H4 ↔ CALZALINDO)
- Un canal mayorista interno
- Un error de routing

**Acción:** Verificar qué tipo de comprobantes genera cuenta 2 "Shoeholic" y si deben excluirse del análisis de deuda externa.

### 7.2 MELI DOG SRL (FLETES) — $19.5M
$19.5M en "compras" para un proveedor de fletes es muy alto. Verificar si este monto es acumulado real o si incluye cargos recurrentes mal imputados.

### 7.3 Patricia Belgrano 621 — $15.1M
Aparece como proveedor con $15M en compras. Por el nombre parece ser una persona física (posiblemente alquiler). Verificar correcta imputación.

---

## ACCIONES INMEDIATAS RECOMENDADAS

| Prioridad | Acción | Monto involucrado |
|-----------|--------|-------------------|
| 🔴 HOY | Verificar fondos para cheques del 10/04 | $3.95M |
| 🔴 13/04 | DISTRINANDO MODA cheque $7M | $7M |
| 🔴 17/04 | Pico más alto del mes — asegurar liquidez | $19.86M |
| 🟡 Esta semana | Reclamar facturas a ALPARGATAS (89 días, $53.8M sin facturar) | $53.8M |
| 🟡 Esta semana | Reclamar facturas a VICBOR (96 días, $30.6M) | $30.6M |
| 🟡 Esta semana | Investigar TECAL Cavatini: saldo negativo $10.3M sin explicar | $10.3M |
| 🟡 Esta semana | Investigar A NATION: $9.3M saldo negativo sin remitos | $9.3M |
| 🟡 Esta semana | Investigar MARIO INNOVA: $7.5M saldo negativo sin remitos | $7.5M |
| 🟢 Este mes | Ejecutar `crear_presupuesto_industria.sql` | — |
| 🟢 Este mes | Revisar facturas 2021 sin cancelar (VICBOR $1.84M, Escorpión $1.65M, Calzados Blanco $5.4M) | $8.9M |
| 🟢 Este mes | Clasificar "Shoeholic" cuenta 2 y GO BY CZL cuenta 17 como intercompany | $152M+ |

---

*Próxima auditoría programada: 16/04/2026*
*Archivo: `_informes/auditorias/audit_calce_20260409.md`*
