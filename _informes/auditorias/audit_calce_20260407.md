# AUDITORÍA CALCE FINANCIERO — H4 / CALZALINDO
**Fecha**: 7 de abril de 2026
**Fuente**: msgestionC (UNION ALL), msgestion01art, omicronvt
**Generado por**: Claude Code (tarea programada)

---

## RESUMEN EJECUTIVO

| Indicador | Valor | Estado |
|-----------|-------|--------|
| Cheques vencimiento próximos 30 días | **~$64.6M** | 🔴 CRÍTICO |
| Semana más comprometida (17-abr) | **$33.1M** | 🔴 CRÍTICO |
| Remitos sin facturar >60 días | **~$120M+** (44 proveedores) | 🟡 ATENCIÓN |
| Remitos más grandes sin facturar | ALPARGATAS $19.7M (87 días) | 🟡 ATENCIÓN |
| Proveedores con saldo negativo (nos deben) | 20+ cuentas | 🟡 ATENCIÓN |
| Facturas vencidas sin cancelar (2020+) | 20+ filas desde $13K | 🟢 Montos bajos |

---

## 🔴 SECCIÓN 1 — CRÍTICO: CALENDARIO DE PAGOS PRÓXIMOS 30 DÍAS

### Cheques y órdenes de pago con vencimiento desde hoy

**Total comprometido: ~$64.6M en 30 días**

| Fecha | Proveedor | Monto | Tipo | Urgencia |
|-------|-----------|-------|------|----------|
| 10-abr | TIVORY TRADING CO S.A. | **$2.99M** (7 items) | Mix | 🔴 3 días |
| 13-abr | RIMON CASSIS E HIJOS SA | $959K | Cheque | 🔴 6 días |
| 14-abr | DER KEVORKIAN HNOS SH | $707K | Cheque | 🔴 7 días |
| 17-abr | DISTRINANDO S.A. | **$14.48M** | ECheque | 🔴 10 días |
| 17-abr | VICBOR SRL | **$17.24M** (5 pagos) | Mix | 🔴 10 días |
| 17-abr | CALZADOS FERLI S.A. | $1.39M | ECheque | 🔴 10 días |
| 23-abr | INDUSTRIAS G&D (STORKMAN) | **$12.99M** (4 pagos) | ECheque | 🟡 16 días |
| 24-abr | DISTRINANDO S.A. | $8.36M | ECheque | 🟡 17 días |
| 24-abr | BAGUNZA SA | $2.14M | Mix | 🟡 17 días |
| 30-abr | BALL ONE S.R.L | $3.67M (7 pagos) | Mix | 🟡 23 días |

### ⚡ SEMANA CRÍTICA: 17 de abril = $33.1M en UN SOLO DÍA

- DISTRINANDO: $14.48M (echeque banco 285)
- VICBOR: $17.24M distribuido en 5 cuotas
- FERLI: $1.39M

> **Acción requerida**: Confirmar disponibilidad bancaria para el 17-abr con antelación. Es el pico de pago de la temporada.

### Detalle TIVORY (10-abr, 3 días)
Total: ~$2.99M incluyendo `$2,723,952` (pago principal) + 6 cuotas menores.

---

## 🟡 SECCIÓN 2 — REMITOS SIN FACTURAR (>60 días)

**44 proveedores externos con remitos sin factura. Total estimado: ~$120M**

### Top remitos sin facturar por monto

| Proveedor | Empresa | Remitos | Monto | Días | Alerta |
|-----------|---------|---------|-------|------|--------|
| ALPARGATAS S.A.I.C. (668) | H4 | 3 | **$19.67M** | 87 | 🔴 CRÍTICO |
| VICBOR SRL (594) | H4 | 11 | $12.96M | 94 | 🟡 |
| LESEDIFE S.A. (42) | H4 | 8 | $8.41M | 90 | 🟡 |
| CLZ BEAUTY (990) | CALZALINDO | 18 | $7.76M | 69 | ℹ️ interno |
| PRIMER ROUND SRL (770) | H4 | 5 | $6.71M | 71 | 🟡 |
| INDUSTRIAS G&D S.A. (100) | H4 | 1 | **$5.44M** | 88 | 🔴 1 solo remito |
| DISTRINANDO (656) | H4 | 3 | $4.93M | 75 | 🟡 |
| TIMMi/NEW SHOES (11) | CALZALINDO | 8 | $4.88M | 94 | 🟡 |
| GAVAS SA (794) | CALZALINDO | 5 | $4.24M | 95 | 🟡 |
| GRIMOLDI (264) | H4 | 1 | $3.29M | 73 | 🟡 |
| ROFREVE (311) | H4+CLZ | 3 | $3.08M | 67 | 🟡 |
| DISTRIGROUP SRL (860) | H4 | 1 | $2.39M | 95 | 🟡 |
| EVAPLAS (209) | H4 | 1 | $2.37M | 90 | 🟡 |

### ⚠️ ALPARGATAS — Caso prioritario
- 3 remitos desde 10 de enero ($19.67M total, 87 días sin facturar)
- Es el 2do mayor proveedor 2026 con $48.6M en facturas ya emitidas
- Posible: facturas en tránsito, condición de pago especial temporada, o retención administrativa
- **Acción**: Confirmar con Mati si se están recibiendo las facturas físicas de Alpargatas

### ⚠️ INDUSTRIAS G&D — 1 remito de $5.44M desde enero 9
- Un solo remito de $5.44M sin facturar (88 días)
- El mismo proveedor tiene $12.99M en cheques venciendo el 23-abr
- Si el remito no está facturado, el pago del 23-abr podría estar descalzado
- **Acción**: Verificar si existe la factura correspondiente a ese remito #37944

---

## 🟡 SECCIÓN 3 — ANOMALÍAS EN CUENTAS PROVEEDOR (SALDO NEGATIVO)

Proveedores con saldo neto negativo en moviprov1 (fórmula: facturas - pagos aplicados):

> Saldo negativo puede indicar: (a) créditos/NC acumulados, (b) pagos anticipados, (c) contabilización errónea.

| Proveedor | Saldo | Observación |
|-----------|-------|-------------|
| 817 (desconocido) | **-$33.3M** | Investigar — monto muy alto |
| 656 DISTRINANDO | -$23.7M | Tiene cheques próximos por $22.8M — ver nota |
| 960 TECAL Cavatini | -$19.5M | También tiene remitos sin facturar |
| 264 GRIMOLDI | -$13.7M | Tiene remito sin facturar $3.29M |
| 713 (desconocido) | -$12.9M | Investigar |
| 769 (desconocido) | -$9.3M | Investigar |
| 1436 (desconocido) | -$7.5M | Investigar |
| 1142 (desconocido) | -$6.3M | Investigar |
| 1158 | -$4.5M | ⚠️ EXCLUIR — es cuenta gastos (en EXCL_MARCAS_GASTOS) |

### ⚠️ Caso DISTRINANDO (656)
Paradoja detectada:
- Saldo negativo de -$23.7M (presuntamente tenemos un crédito con ellos)
- Pero emitimos cheques de $14.48M (17-abr) + $8.36M (24-abr) = $22.84M
- Compras facturadas 2026: $36M (6 facturas, última feb-26)
- Remitos sin facturar: $4.93M

Hipótesis más probable: el saldo negativo es de NC/devoluciones de temporadas anteriores (PV25/OI25) que ya están absorbidas en los nuevos cheques de OI26. Sin embargo, si los créditos NO están siendo descontados, **estaríamos pagando de más ~$23.7M**.

**Acción urgente**: Verificar con contabilidad si los -$23.7M representan NC activas o ya imputadas.

---

## 🟡 SECCIÓN 4 — COMPRAS 2026: ESTRUCTURA Y ANOMALÍAS

### Top 20 proveedores por monto facturado 2026 (enero-abr 7)

| # | Proveedor | Empresa | Monto | Facturas | Última |
|---|-----------|---------|-------|----------|--------|
| 1 | GO by CZL (17) | CALZALINDO | $75.3M | 14 | 18-mar |
| 2 | ALPARGATAS (668) | H4 | $48.6M | 8 | 26-feb |
| 3 | DISTRINANDO (656) | H4 | $36M | 6 | 25-feb |
| 4 | VICBOR SRL (594) | H4 | $20.9M | 14 | 28-feb |
| 5 | MERCADO LIBRE (1261) | H4 | $19.6M | 9 | 23-feb |
| 6 | LESEDIFE (42) | H4 | $15.2M | 13 | 17-feb |
| 7 | ALQUILERES (1494) | CLZ | $14.8M | 8 | 01-feb |
| 8 | MUNDO TEXTIL (1523) | H4 | $14.1M | 6 | 11-feb |
| 9 | SUELDOS GERENCIALES (1527) | CLZ | **$13.8M** | 1 | 31-ene |
| 10 | TIVORY (950) | H4 | $13.4M | 5 | 18-mar |
| 11 | CLZ BEAUTY (990) | CLZ | $12.9M | 3 | 18-mar |
| 12 | PRIMER ROUND (770) | H4 | $11.6M | 12 | 26-feb |
| 13 | GAVAS SA (794) | CLZ | $11.2M | 6 | 18-mar |
| 14 | Capacitación Laboral (1235) | CLZ | $8.9M | 3 | 31-mar |
| 15 | ZOTZ (457) | CLZ | $8.8M | 3 | 17-mar |
| 16 | BANCO MACRO (1368) | H4 | **$8.8M** | 1 | 31-ene |
| 17 | INDUSTRIAS G&D (100) | H4 | $8.7M | 5 | 28-feb |
| 18 | TIMMi (11) | CLZ | $8.5M | 10 | 20-mar |
| 19 | Mortarini Ana A y B (433) | CLZ | $6.7M | 3 | 01-mar |
| 20 | MELI DOG (1260) | H4 | $6.6M | 3 | 10-feb |

### 📊 Observaciones estructura de compras

**1. GO by CZL $75.3M — movimiento interno**
- Es el "mayor proveedor" pero es el depósito propio GO by CZL (dep 11)
- Los compras2 código 1 de proveedor 17 representan transferencias entre empresas, no compras de terceros
- Monto extraordinariamente alto: equivale al 60% de las compras reales externas
- **Aprendizaje**: La estructura de depósito consignado CLZ→GO es costosa. Cada par tiene ~2.5x de movimientos contables.

**2. BANCO MACRO $8.8M — 1 factura enero**
- Probable cuota de préstamo institucional o línea de crédito bancaria
- Gasto financiero real que impacta resultado

**3. SUELDOS GERENCIALES $13.8M — 1 factura enero**
- Cargado como "compra" — formato contable de H4/CLZ para sueldos fuera de convenio
- Monto alto pero esperado

**4. MERCADO LIBRE $19.6M en comisiones/fees**
- Es el 5to "proveedor" real. Refleja el tamaño del canal ML.
- 9 facturas de comisiones → implica ~$2.2M/mes de costos ML

---

## 🟡 SECCIÓN 5 — FACTURAS VENCIDAS SIN CANCELAR (>180 días)

Se detectaron 20+ registros en moviprov1 con vencimiento entre 2020-2021, `importe_pesos - importe_can_pesos > $10K`:

- Proveedor 807: $48K (ene-2020) — 6 años sin cancelar
- Proveedor 834: $195K en 2 facturas (jul+oct 2020)
- Proveedor 857: $120K (mar-2021)
- Proveedor 209 (EVAPLAS): $30K parcialmente cancelado (dic-2020)
- Varios otros entre $13K-$104K

**Estado**: Montos pequeños en términos absolutos. Probablemente proveedores discontinuados o deudas en disputa. Requiere limpieza contable eventual pero no es urgente.

---

## 🟢 SECCIÓN 6 — PATRONES HISTÓRICOS

### Concentración de proveedores
Top 3 proveedores de calzado real (excl. internos y gastos):
1. ALPARGATAS: $48.6M → **~22% del total**
2. DISTRINANDO (Reebok): $36M → **~16%**
3. VICBOR (Atomik/Wake/Massimo): $20.9M → **~10%**

Top 3 concentran ~48% de las compras de producto. **Riesgo de concentración moderado** — ruptura con cualquiera de los 3 afecta significativamente el mix.

### Análisis DISTRINANDO (Reebok) — proveedor crítico
- Mayor monto individual en cheques próximos ($22.8M en 2 pagos)
- Tiene saldo negativo en cuentas (-$23.7M)
- Mayor % de compras (16% del total)
- **Riesgo**: si la relación se deteriora, impacto directo en línea deportiva H4

### Calendario pagos vs. ingresos OI26
La concentración de pagos en semana del 17-abr coincide con el inicio de temporada OI26. Es estructural: se paga PV26 mientras llega OI26. El riesgo es que las ventas OI26 no fluyan lo suficientemente rápido para cubrir los pagos de PV26.

---

## 📊 SECCIÓN 7 — APRENDIZAJES

1. **El modelo de pago de H4 es 100% echeques/cheques diferidos (banco 285)**. No hay pagos en efectivo visibles. El banco 285 es probablemente el banco principal (posiblemente Macro, dada la factura de $8.8M).

2. **Remitos sin facturar son sistémicos, no una anomalía**. 44 proveedores tienen remitos sin facturar con >60 días. Esto es la norma de la zapatería argentina: los fabricantes entregan en enero-febrero y facturan a 60-90 días. Sin embargo, ALPARGATAS ($19.7M) con 87 días es inusualmente largo para una empresa tan grande.

3. **CLZ BEAUTY y GO by CZL son entidades internas** que inflan los números de compras. En un análisis de proveedores externos, el ranking real empieza en ALPARGATAS.

4. **DISTRINANDO aparece en múltiples alertas simultáneas** (saldo negativo, remitos sin facturar, cheques máximos del mes). Es el proveedor que requiere mayor seguimiento financiero.

5. **MUNDO TEXTIL $14.1M** como 8vo proveedor es interesante — podría ser indumentaria complementaria (remeras, etc.) que está ganando peso en el mix.

---

## ✅ ACCIONES RECOMENDADAS

### Esta semana (antes del 17-abr)
- [ ] **Confirmar fondos bancarios** para cubrir $33.1M del 17-abr (DISTRINANDO $14.5M + VICBOR $17.2M + FERLI $1.4M)
- [ ] **TIVORY**: confirmar pago de $2.99M para el 10-abr (3 días)
- [ ] **Investigar proveedor 817**: -$33.3M es el mayor saldo negativo del sistema — quién es y si hay crédito real

### Esta semana — Remitos
- [ ] **ALPARGATAS $19.7M**: consultar a Mati si llegaron las facturas físicas (3 remitos enero, 87 días)
- [ ] **G&D Storkman remito #37944** ($5.44M, 88 días): corroborar que haya factura antes del pago del 23-abr

### Este mes — Contabilidad
- [ ] **DISTRINANDO crédito -$23.7M**: verificar si está reflejado en los cheques del 17/24-abr o es un crédito pendiente de aplicar
- [ ] **TECAL Cavatini -$19.5M**: mismo análisis — ¿hay NC no aplicadas?
- [ ] Limpiar facturas vencidas desde 2020 (proveedores 807, 834, 857, etc.)

---

*Auditoría ejecutada automáticamente por Claude Code — tarea programada `calce-financiero-audit`*
*Próxima ejecución: automática según schedule configurado*
*Datos al: 7 de abril de 2026*
