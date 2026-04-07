# AUDITORÍA CALCE FINANCIERO — 06/04/2026

> Ejecutada automáticamente. Base: msgestionC (productivo 111). Excluye marcas gastos: 1316, 1317, 1158, 436.

---

## 🔴 CRÍTICO

### 1. REMITOS SIN FACTURAR CON MÁS DE 60 DÍAS

Estos remitos tienen stock impactado pero sin factura asociada. Son riesgo contable y de cuentas a pagar.

| Proveedor | Remito # | Monto | Fecha | Días pendiente |
|-----------|----------|-------|-------|----------------|
| ADORATTA (760) | 62516 | $1,469,225 | 2025-04-05 | **366 días** |
| ADORATTA (760) | 62518 | $1,253,760 | 2025-04-05 | **366 días** |
| ADORATTA (760) | 62517 | $1,095,990 | 2025-04-05 | **366 días** |
| ADORATTA (760) | 62519 | $741,440 | 2025-04-05 | **366 días** |
| ADORATTA (760) | 62527 | $126,880 | 2025-04-05 | **366 días** |
| TREZAP SRL (940) | 21 | $448,800 | 2025-04-07 | **364 días** |
| VICBOR SRL (594) | 168725 | $3,318,149 | 2025-06-13 | **297 días** |
| VICBOR SRL (594) | 167393 | $654,646 | 2025-06-20 | **290 días** |
| HEYAS (684) | 37251 | $311,700 | 2025-11-06 | 151 días |
| MATIAS SUBIRADA (955) | 6625 | $240,000 | 2026-01-03 | 93 días |

**Total expuesto: ~$9.66M sin factura**. ADORATTA acumula 5 remitos por $4.69M desde hace exactamente un año. VICBOR tiene $3.97M en dos remitos de mediados de 2025.

**Acción**: Verificar con Mati si ADORATTA y TREZAP son proveedores activos o si esos remitos son error. VICBOR requiere factura urgente.

---

### 2. CAÍDA REAL DE VENTAS Q1-2026 vs Q1-2025 (ALARMANTE)

Comparación enero–abril año a año (mismo período):

| Grupo | Unidades 2025 | Unidades 2026 | Variación | $ 2025 | $ 2026 | Var $ |
|-------|---------------|---------------|-----------|--------|--------|-------|
| 5 (PU/Sint) | 14,349 | 8,812 | **-39%** | $519M | $364M | -30% |
| 17 (Deportivo) | 20,622 | 16,015 | **-22%** | $459M | $289M | -37% |
| 15 (Running/Macramé) | 5,406 | 2,537 | **-53%** | $297M | $155M | -48% |
| 1 (Cuero) | 3,841 | 2,724 | **-29%** | $255M | $201M | -21% |
| 2 (Informal) | 3,292 | 1,617 | **-51%** | $84M | $53M | -37% |
| 4 (Premium) | 1,094 | 767 | **-30%** | $47M | $29M | -38% |
| 11 (Niños) | 2,452 | 1,559 | **-36%** | $38M | $32M | -15% |
| 39 (Accesorios/Tela) | 2,619 | 1,587 | **-39%** | $69M | $54M | -21% |

**Todos los grupos caen en unidades**. Los más preocupantes:
- **Grupo 15 (Running)**: -53% unidades con caída del 48% nominal → probable efecto combinado de fin de temporada verano + impacto precios. Con pedidos OI26 ya comprometidos, esto es señal de alerta de sobrecompra.
- **Grupo 17 (Deportivo)**: -37% nominal. El ticket promedio de este grupo es **plano o en caída nominal** (ene-2025 $25,600 → abr-2026 $24,500) — única categoría con **deflación nominal de precios de venta**, lo que implica caída real del 40-50%.
- **Grupo 2 (Informal)**: -51% unidades.

---

### 3. PROVEEDORES CON SALDO ACREEDOR SIGNIFICATIVO (nos deben)

Los saldos negativos en moviprov1 indican que el proveedor tiene deuda con nosotros (pagamos de más, devoluciones no acreditadas, etc.):

| Proveedor | Saldo a nuestro favor |
|-----------|-----------------------|
| KALIF - ALEX SPORT (817) | **$33.3M** |
| DISTRINANDO DEPORTES (656) | **$23.7M** |
| TECAL Cavatini (960) | **$19.5M** |
| GRIMOLDI (264) | **$13.7M** |
| DISTRINANDO MODA (713) | **$12.9M** |
| A NATION (769) | $9.3M |
| MARIO INNOVA (1436) | $7.5M |
| TXT Pack (1142) | $6.3M |
| COMPRANDO EN GRUPO (853) | $4.2M |
| BAUDRACCO (1155) | $3.9M |

**Total saldos acreedores comerciales: ~$134M** (excluyendo gastos/cta 1158).

Los más llamativos: KALIF ($33M) y TECAL Cavatini ($19.5M) son montos muy elevados para el tamaño habitual de esas operaciones. Recomiendo verificar si corresponden a acreditaciones pendientes, notas de crédito no procesadas, o errores de imputación.

---

## 🟡 ATENCIÓN

### 4. SALDOS DEUDORES ALTOS (nuestra deuda a proveedores)

| Proveedor | Nuestra deuda |
|-----------|---------------|
| Shoeholic (2) | **$35.1M** — última compra: nov-2025 (143 días) |
| ALPARGATAS (668) | $24.7M — activo, última compra: feb-2026 |
| PRIMER ROUND SRL (770) | $10.6M — activo |
| SARANG TONGSANG SRL (515) | $7.9M |
| GAVAS SA (794) | $7.3M |
| FOUR WITCH DISTRIBUIDORA (671) | $6.3M |
| BALL ONE SRL (608) | $5.0M |

**Shoeholic** ($35.1M) sin compras desde hace 143 días es el caso más relevante. Puede ser proveedor estacional, pero el monto es el mayor de todos. Verificar si hay facturas pendientes de procesar.

---

### 5. REMITOS 2026 AÚN PENDIENTES

| Proveedor | Monto | Días pendiente |
|-----------|-------|----------------|
| GO by CZL (17) | $874,000 | 56 días |
| TIMMi (NEW SHOES) (11) | $711,000 | 19 días |
| VICBOR SRL (594) | $304,104 | 41 días |
| MATIAS SUBIRADA (955) | $240,000 | 93 días |

GO by CZL lleva 56 días → ya pasa el umbral de 30 días. Es intercompany, verificar estado.

---

### 6. TICKET PROMEDIO — GRUPO 17 EN DEFLACIÓN NOMINAL

| Grupo | Ene-2025 | Abr-2026 | Variación nominal |
|-------|----------|----------|-------------------|
| 1 (Cuero) | $62,435 | $83,276 | **+33%** ✓ |
| 5 (PU/Sint) | $31,171 | $47,464 | **+52%** ✓ |
| 4 (Premium) | $37,598 | $49,992 | **+33%** ✓ |
| 15 (Running) | $56,918 | $57,251 | **+0.6%** ⚠️ |
| 39 (Accesorios) | $27,509 | $35,556 | **+29%** ✓ |
| 17 (Deportivo) | $25,587 | $24,557 | **-4%** 🔴 |
| 11 (Niños) | $14,497 | $19,526 | **+35%** ✓ |
| 2 (Informal) | $23,023 | $33,893 | **+47%** ✓ |

**Grupo 17**: único con ticket nominal decreciente. Con inflación minorista del 60-80% interanual, esto implica una caída real del precio de venta del orden del 35-45%. Posibles causas: liquidaciones de stock verano, mezcla de producto más barata, o presión competitiva en deportivos.

**Grupo 15 (Running)**: ticket casi plano nominalmente. Considerando que es el grupo con mayor caída en unidades (-53%), la combinación es preocupante.

---

### 7. FACTURAS MUY ANTIGUAS SIN CANCELAR (ruido histórico)

La mayoría de las facturas con vencimiento > 180 días son de 2010-2011 (proveedores inactivos como ABIEL, Ferechian, Acolflex). Montos pequeños ($26 a $16,345). No representan riesgo financiero real pero generan ruido en reportes. Se recomienda una limpieza contable puntual.

Excepción: cuenta 1158 ("Compras y Gastos Varios") con vencimiento en 2001 y comprobante de 2019 — claramente un error de carga de fecha.

---

### 8. GRIMOLDI — SIN COMPRAS HACE 74 DÍAS + SALDO ACREEDOR $13.7M

GRIMOLDI aparece en el top 5 de proveedores por compras 2025-2026 ($121.8M, 64 facturas) pero lleva 74 días sin nueva compra y tiene un saldo acreedor de $13.7M a nuestro favor. Puede indicar transición de temporada (fin PV26, inicio OI26 no iniciada), o una negociación en curso. Monitorear.

---

### 9. GLOBAL BRANDS (OLK/VANS) — 109 DÍAS SIN COMPRA

GLOBAL BRANDS (722) figura como 12° proveedor con $76.1M en 2025-2026 pero sin facturas desde el 18-dic-2025 (109 días). En línea con lo conocido sobre OLK/Olympikus pendiente de confirmación Cecchini.

---

## 🟢 OK

### 10. CHEQUES — SIN VENCIMIENTOS URGENTES

No hay cheques/EC tipo convencional con vencimiento en los próximos 7 ni 30 días. En ordpag1 los instrumentos activos son: tipo "9" ($289M, 84 registros), "I" ($52.7M), "R" ($34.7M), "C" ($15.7M), "E" ($9.5M) — todos correspondientes a vencimientos fuera de la ventana inmediata o ya procesados. **Sin presión de caja a corto plazo por cheques**.

### 11. PROVEEDORES ACTIVOS BIEN DISTRIBUIDOS

Los 5 principales proveedores comerciales en 2025-2026 presentan continuidad operativa:
- ALPARGATAS ($273.7M, activo)
- VICBOR ($207.5M, activo)
- DISTRINANDO DEPORTES ($117.5M, activo)
- DISTRINANDO MODA ($109.2M, activo)
- LESEDIFE ($110.5M, activo, última factura hace 19 días)

No hay señales de corte de suministro en los proveedores core.

### 12. CONCENTRACIÓN GRUPO 1 (CUERO) — ALTA PERO CONOCIDA

Top 3 grupo 1 en compras 2025-2026:
1. ALPARGATAS: $121.7M (~40% del grupo)
2. Souter S.A.: $69.7M (~23%)
3. BALL ONE SRL: $49.8M (~16%)

Concentración del top 3 ≈ 79%. Alta pero es una característica estructural del segmento cuero premium, no un cambio reciente.

---

## 📊 APRENDIZAJE

### A. LA CAÍDA DE UNIDADES ES TRANSVERSAL Y ESTRUCTURAL

En Q1-2026, todos los grupos cayeron en unidades. El efecto "ticket promedio sube nominalmente" compensa parcialmente en pesos pero **no en volumen**. Esto tiene implicaciones directas para los pedidos de invierno: los ~7,288 pares pendientes de inserción fueron proyectados probablemente con velocidades de temporada anterior. Con running cayendo -53% en unidades, conviene revisar especialmente los pedidos de ese segmento antes de ejecutar el INSERT.

### B. GRUPO 17 (DEPORTIVO MASIVO) COMO SEÑAL TEMPRANA DE CONTRACCIÓN

Es el único grupo con deflación nominal de precio de venta. Históricamente, el segmento deportivo masivo es el primero en ajustar precios cuando la demanda cae (alta elasticidad, fácil comparación online). Si esta tendencia continúa en mayo-junio, impactará en el calce de los pedidos Atomik/Floyd/Escorpio que están pendientes de INSERT.

### C. ADORATTA: ¿PROVEEDOR ACTIVO O BAJA NO REGISTRADA?

5 remitos de hace un año exacto ($4.69M total) sin factura es inusual. Puede ser que el proveedor haya cerrado o tenga un conflicto no resuelto. La antigüedad de exactamente 366 días sugiere que fue un lote de fin de temporada OI25 que nunca se facturó correctamente.

### D. SHOEHOLIC ($35.1M DEUDA, SIN COMPRAS 143 DÍAS)

Shoeholic es el 9° proveedor por monto 2025-2026 ($105.9M) con solo 3 facturas. El saldo deudor de $35.1M y la ausencia de actividad desde noviembre sugiere que es un proveedor de grandes órdenes anuales (no frecuente). Verificar si hay facturas de la temporada OI26 en camino.

---

## RESUMEN EJECUTIVO

| Indicador | Valor | Estado |
|-----------|-------|--------|
| Remitos +60 días sin factura | $9.66M (10 registros, riesgo ADORATTA+VICBOR) | 🔴 |
| Caída unidades Q1-2026 vs Q1-2025 | -22% a -53% según grupo | 🔴 |
| Saldos acreedores comerciales (nos deben) | $134M total, KALIF $33M, Distrinando $24M | 🔴 |
| Deflación precio nominal grupo 17 | -4% nominal (=-40% real) | 🟡 |
| Shoeholic deuda $35M sin actividad 143d | Verificar facturas OI26 | 🟡 |
| Grimoldi saldo +$13.7M, sin compras 74d | Transición temporada | 🟡 |
| Cheques vencimiento próximos 30 días | $0 (sin presión inmediata) | 🟢 |
| Proveedores core activos | Todos operativos | 🟢 |

**Fecha de próxima auditoría recomendada**: 13/04/2026 (7 días), con foco en evolución de ADORATTA y seguimiento de caída grupo 15/17.
