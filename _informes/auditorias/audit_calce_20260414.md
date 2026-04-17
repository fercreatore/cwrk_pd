# Auditoría Calce Financiero — 14 de abril de 2026

**Generado automáticamente por tarea programada `calce-financiero-audit`**
**Bases consultadas:** msgestionC (vistas UNION ALL), msgestion01 (CLZ), msgestion03 (H4), msgestion01art (artículos)
**Exclusiones:** marcas gastos 1316, 1317, 1158, 436

---

## 1. ANOMALÍAS EN DEUDA

### 🔴 CRÍTICO — Saldos negativos de alto valor (el proveedor nos debe)

Los siguientes proveedores muestran saldo neto favorable a nuestra empresa (nos deben dinero o hay pagos en exceso):

| Proveedor | Cod | Saldo a favor nuestro |
|-----------|-----|----------------------:|
| KALIF - ALEX SPORT | 817 | **$33.304.732** |
| DISTRINANDO DEPORTES S.A. | 656 | **$14.916.063** |
| TECAL Cavatini | 960 | **$12.988.380** |
| A NATION | 769 | $9.332.908 |
| MARIO INNOVA | 1436 | $7.456.060 |
| TXT Pack | 1142 | $6.288.000 |
| Organización Had. Seguros Generales | 1137 | $4.404.336 |
| COMPRANDO EN GRUPO | 853 | $4.230.977 |
| Baudracco | 1155 | $3.857.806 |
| LADY STORK | 99 | $3.242.477 |

**Acción requerida para los 3 primeros:**

- **KALIF (817) — $33.3M**: Tiene además $10M en cheques a vencer en los próximos 30 días (5 cheques, primero el 27-abr). El saldo negativo + cheques pendientes sugiere **netting parcial o error de imputación** — verificar si hay notas de crédito sin aplicar o pagos duplicados.
- **DISTRINANDO DEPORTES (656) — $14.9M negativo + $13.3M en cheques próximos**: El saldo negativo casi se cancela con los cheques pendientes. Revisar si los cheques corresponden a facturas nuevas o si hay cruce de cuentas. Hay 2 cheques urgentes esta semana (16-abr $3.4M y 17-abr $4.9M).
- **TECAL (960) — $12.9M negativo + $6.5M cheque el 12-may**: Similar a KALIF — cruce de cuentas pendiente.

### 🟢 OK — Deuda huérfana
No se encontraron proveedores con deuda > $5M sin compras en los últimos 6 meses. Toda la deuda significativa tiene actividad reciente.

### 🟡 ATENCIÓN — Saldos negativos menores con naturaleza mixta
Los siguientes merecen revisión pero no son urgentes:
- **GO Servicios Digitales (1208) — $3M**: Servicio, no calzado. Revisar si hay facturas pendientes de recibir.
- **MERCADO LIBRE (1261) — $2.5M**: Canal de venta. Puede ser saldo acumulado de comisiones. Verificar liquidaciones pendientes.
- **RAPICUOTAS (1497) — $2.2M**: Confirmar naturaleza del saldo.
- **DISTRIGROUP (860) — $2M**: Proveedor de John Foos (prov 860, pedido OI26 pendiente INSERT de 88 pares $4.2M). El saldo negativo puede estar relacionado.

---

## 2. RECUPERO DE INVERSIÓN

### 📊 APRENDIZAJE — Top 20 proveedores por inversión en 2026

| # | Proveedor | Monto Comprado 2026 | Pares | Ticket Prom/par |
|---|-----------|--------------------:|------:|----------------:|
| 1 | GO by CZL (17) | $164.259.517 | 11.062 | $14.849 |
| 2 | ALPARGATAS (668) | $109.901.669 | 2.926 | $37.559 |
| 3 | DISTRINANDO DEPORTES (656) | $93.297.761 | 2.288 | $40.775 |
| 4 | VICBOR SRL (594) | $76.083.675 | 2.338 | $32.542 |
| 5 | DISTRINANDO MODA (713) | $42.859.428 | 1.200 | $35.716 |
| 6 | LESEDIFE (42) | $40.726.020 | 3.560 | $11.440 |
| 7 | TIMMi/NEW SHOES (11) | $33.221.218 | 1.849 | $17.967 |
| 8 | KALIF/ALEX SPORT (817) | $31.608.180 | 1.383 | $22.855 |
| 9 | CLZ BEAUTY (990) | $29.133.400 | 5.019 | $5.805 |
| 10 | GRIMOLDI (264) | $27.774.642 | 388 | $71.585 |
| 11 | ZOTZ (457) | $23.566.024 | 1.241 | $18.989 |
| 12 | SARANG TONGSANG (515) | $23.408.984 | 15.000 | $1.561 |
| 13 | GAVAS SA (794) | $23.017.341 | 695 | $33.125 |
| 14 | PRIMER ROUND (770) | $22.597.197 | 1.076 | $20.999 |
| 15 | TIVORY TRADING (950) | $22.195.656 | 1.038 | $21.383 |
| 16 | TECAL Cavatini (960) | $18.701.526 | 284 | $65.849 |
| 17 | Souter/RINGO (561) | $18.198.594 | 316 | $57.590 |
| 18 | INDUSTRIAS G&D (100) | $16.488.600 | 828 | $19.913 |
| 19 | CALZADOS BLANCO/DIADORA (614) | $16.145.480 | 432 | $37.374 |
| 20 | BALL ONE (608) | $15.564.170 | 323 | $48.186 |

**Observaciones:**
- **GO by CZL (17)** lidera con $164M — es proveedor interno (GO BY CLZ), confirmar que no genera distorsión en análisis de márgenes.
- **SARANG TONGSANG (515)** tiene precio/par extremadamente bajo ($1.561) — verificar si es medias/accesorios o error de imputación.
- **GRIMOLDI (264)** y **TECAL (960)** y **Souter/RINGO (561)** tienen precio/par muy alto ($71K, $65K, $57K) — consistente con calzado premium/cuero de alta gama.
- Análisis de días para recuperar el 50% de la inversión no pudo calcularse con los datos disponibles (requiere cruzar fechas de compra con curva de ventas por artículo específico).

---

## 3. CHEQUES Y PAGOS

### 🔴 CRÍTICO — Vencimientos urgentes próximos 7 días

**Total comprometido semana 14-21 abril: ~$34.4M**

| Fecha | Proveedor | Importe | OP# |
|-------|-----------|--------:|-----|
| **15-abr (mañana)** | DISTRINANDO MODA (713) | $5.000.000 | 6485 |
| **16-abr** | DISTRINANDO DEPORTES (656) | $3.400.000 | 6592 |
| **16-abr** | GRIMOLDI (264) | $3.551.460 | 6722 |
| **17-abr** | DISTRINANDO DEPORTES (656) | $4.902.976 | 6678 |
| **17-abr** | CALZADOS GUNAR (780) | $4.337.993 | 6593 |
| **17-abr** | CALZADOS FERLI (693) | $4.300.000 | 6595 |
| **17-abr** | VICBOR SRL (594) | $6.319.657 | 6471 |
| **20-abr** | Compras y Gastos (1158) | $1.500.000 | 6482 |
| **20-abr** | TXT Pack (1142) | $350.000 | 263583 |
| **21-abr** | GLOBAL BRANDS (722) | $890.307 | 6576 |

> ⚠️ El jueves 17 de abril vencen $19.8M en un solo día (VICBOR + GUNAR + FERLI + DISTRINANDO DEPORTES).

### 🟡 ATENCIÓN — Compromisos próximos 30 días (hasta 14-may)

**Total top 20 proveedores: ~$101.2M comprometidos**

| Proveedor | Cant Cheques | Total | Primer Vto |
|-----------|-------------|------:|-----------|
| DISTRINANDO MODA (713) | 10 | $17.688.771 | **15-abr** |
| VICBOR SRL (594) | 9 | $15.619.657 | **17-abr** |
| DISTRINANDO DEPORTES (656) | 3 | $13.302.976 | **16-abr** |
| KALIF/ALEX SPORT (817) | 5 | $10.000.000 | 27-abr |
| INDUSTRIAS G&D (100) | 4 | $6.542.704 | 23-abr (todos mismo día) |
| TECAL Cavatini (960) | 1 | $6.500.000 | 12-may |
| CALZADOS GUNAR (780) | 1 | $4.337.993 | **17-abr** |
| CALZADOS FERLI (693) | 1 | $4.300.000 | **17-abr** |
| BALL ONE (608) | 7 | $3.672.056 | 30-abr (todos mismo día) |
| GRIMOLDI (264) | 1 | $3.551.460 | **16-abr** |

**Alertas de concentración:**
- **VICBOR (594)**: 9 cheques → posible concentración de riesgo si hay problema de liquidez.
- **DISTRINANDO MODA (713)**: 10 cheques en el período, primer vencimiento mañana.
- **INDUSTRIAS G&D (100)**: 4 cheques todos el 23-abr — concentración en un día.
- **BALL ONE (608)**: 7 cheques todos el 30-abr — concentración en un día.

---

## 4. REMITOS SIN FACTURAR

### 🟢 OK — Sin anomalías
No se encontraron remitos de código 7 o 36 en 2026 sin facturar (fuera de las cuentas de gastos excluidas). El proceso administrativo de facturación parece estar al día.

> Nota técnica: Si hay remitos internos entre depósitos propios, pueden estar en las cuentas 7/36 excluidas (código 95 - SOLICITUD A DEPOSITO en CLZ). Verificar si el análisis debe incluir esas cuentas por separado.

---

## 5. PRESUPUESTO

### 🟡 ATENCIÓN — Sin datos de presupuesto disponibles
No se pudo ejecutar el análisis de ejecución vs presupuesto por rubro porque no se encontró tabla de presupuesto accesible via MCP en este período. Requiere acceso directo a la tabla de presupuesto en omicronvt u otra base de analítica.

**Alternativa sugerida**: Usar ventas del mismo período año anterior como benchmark proxy:

#### Comparación ventas Rubro 1 (Calzado) — Abr 2025 vs Abr 2026 (parcial al 14/4):

| Período | Pares | Monto |
|---------|------:|------:|
| Abr 2025 (completo) | 5.286 | $199.304.107 |
| Abr 2026 (al 14/4) | 2.426 | $97.753.577 |

Abr 2026 al 14/4 lleva el 49% de los pares del mes completo del año anterior — **ritmo normal** considerando que estamos en la mitad del mes.

#### Rubro 3 (Deportivo):

| Período | Pares | Monto |
|---------|------:|------:|
| Abr 2025 (completo) | 3.827 | $130.097.989 |
| Abr 2026 (al 14/4) | 3.270 | $74.627.517 |

Abr 2026 al 14/4 lleva el 85% de los pares del mes del año anterior — **ritmo alto**, posible que termine superando el mes anterior en pares.

---

## 6. PATRONES HISTÓRICOS

### 📊 APRENDIZAJE — Estacionalidad por rubro

#### Rubro 1 (Calzado) — Picos claros
- **Dic** es el mes más fuerte de forma consistente: 2024-dic $342M, 2025-dic $354M
- **Oct** es el segundo pico: 2024-oct $299M, 2025-oct $318M
- **Feb-Mar** es el valle más bajo del año
- **La temporada OI (Jun-Ago)** es moderada — el calzado formal vende parejo todo el año

#### Rubro 3 (Deportivo) — Patrón distinto
- **Jun** es el pico para deportivo: 2024-jun $178M, 2025-jun $225M
- **Dic** también fuerte: $228M 2024, $192M 2025
- **Jul-Ago** cae post-pico junio
- El deportivo tiene **estacionalidad más marcada** que el calzado general

#### Rubro 4 (Running/Zapatillas) — Pico invernal pronunciado
- **Feb** es el pico máximo consistente: 2024-feb $54M, 2025-feb $118M, 2026-feb $94M
- Crece fuertemente año a año en este segmento
- **Abr 2026** ya muestra desaceleración post-pico ($16M parcial)

### 📊 APRENDIZAJE — Concentración de compras por rubro en 2026

| Rubro | Top 3 proveedores | % concentración top 3 |
|-------|-------------------|----------------------:|
| Rubro 1 (Calzado) | GO by CZL + VICBOR + DISTRINANDO MODA | **20.2%** — Diversificado |
| Rubro 3 (Deportivo) | DISTRINANDO DEPORTES + GO by CZL + KALIF | **39.1%** — Moderado |
| Rubro 4 (Running) | ALPARGATAS + VICBOR + LESEDIFE | **51.4%** — Concentrado |
| Rubro 5 (Infantil) | TIVORY + ALPARGATAS + VICBOR | **50.0%** — Concentrado |
| Rubro 6 (Textil) | GO by CZL + ALPARGATAS + MUNDO TEXTIL | **77.6%** — 🔴 MUY CONCENTRADO |

**Observaciones:**
- **Rubro 6 (Textil)**: GO by CZL sola representa el **51%** del rubro. Si hay un problema con este proveedor (corte de línea, quiebre financiero), la exposición es crítica. Verificar que es proveedor interno.
- **Running y Infantil** con 50%+ en top 3 — riesgo moderado si alguno de los tres falla.
- **Calzado general** bien diversificado — saludable.

### 📊 APRENDIZAJE — Tendencias de crecimiento

Comparando **Abr 2024 vs Abr 2025** (períodos completos equivalentes):

| Rubro | Pares Abr24 | Pares Abr25 | Var Pares | Monto Abr24 | Monto Abr25 | Var Monto |
|-------|------------|------------|----------|------------|------------|---------|
| Rubro 1 | 3.905 | 5.286 | +35% | $117M | $199M | +70% |
| Rubro 3 | 2.839 | 3.827 | +35% | $91M | $130M | +43% |
| Rubro 4 | ~900 | ~900 | flat | ~$18M | ~$31M | +72% |

El crecimiento de precios (monto) superó el crecimiento de volumen (pares) en todos los rubros — inflación trasladada a precios de venta. En Rubro 1 el volumen creció 35% lo que indica expansión real del negocio además de la inflación.

---

## RESUMEN EJECUTIVO

### 🔴 CRÍTICO — Acciones inmediatas

1. **Jueves 17-abr: $19.8M vencen en un día** — Confirmar liquidez disponible para VICBOR ($6.3M) + GUNAR ($4.3M) + FERLI ($4.3M) + DISTRINANDO DEPORTES ($4.9M). Si hay tensión de caja, priorizar en ese orden.

2. **KALIF (817) — $33.3M saldo negativo + $10M cheques próximos 30 días**: Requiere conciliación urgente. El saldo negativo indica overpago o notas de crédito sin aplicar. Contactar a KALIF para reconciliar antes de que venzan los próximos cheques.

3. **DISTRINANDO DEPORTES (656) — $14.9M negativo + $13.3M cheques**: Similar a KALIF. Verificar si el saldo negativo ya contempla los cheques en vuelo.

### 🟡 ATENCIÓN — Monitorear esta semana

4. **Mañana 15-abr: $5M DISTRINANDO MODA** — Verificar que el cheque de OP 6485 esté en orden.

5. **Concentración textil en GO by CZL (51%)**: Si es proveedor interno, aclarar el tratamiento contable. Si es externo, evaluar diversificación.

6. **$101.2M comprometidos en cheques próximos 30 días** — Cruzar contra cobranza proyectada para el período para validar calce. La temporada OI empieza a activarse (deportivo fuerte en abril).

### 🟢 OK — Sin acciones requeridas

7. No hay deuda huérfana (todos los proveedores con saldo alto tienen compras recientes).
8. No hay remitos sin facturar del 2026 (proceso administrativo al día).
9. Ritmo de ventas de abril 2026 está en línea con mismo período 2025.

### 📊 APRENDIZAJE — Insights de negocio

10. **Running (Rubro 4) en fuerte crecimiento**: Pico febrero crece año a año ($54M→$118M→$94M aunque este año el pico fue menor). Considerar aumentar stock de running OI para temporada 2027.

11. **Deportivo tiene pico en Junio** — Las compras OI deben estar completamente entregadas antes de Junio para no perder el pico. Checar estado de pedidos VICBOR/DISTRINANDO DEPORTES para ese mes.

12. **Calzado general (Rubro 1) — Octubre y Diciembre son los meses más importantes**. Cualquier quiebre de stock en esos meses tiene el mayor impacto en facturación. Priorizar reposición preventiva en Agosto-Septiembre.

---

*Fin del reporte. Próxima auditoría: 21 de abril de 2026 (tarea programada).*
