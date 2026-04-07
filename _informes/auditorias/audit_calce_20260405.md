# Auditoria Calce Financiero — 5 de Abril 2026

## 1. ANOMALIAS EN DEUDA

### 🔴 CRITICO: 10 proveedores con saldo NEGATIVO (nos deben dinero)

| Proveedor | Saldo a favor |
|-----------|--------------|
| KALIF - ALEX SPORT | $33.3M |
| DISTRINANDO DEPORTES | $23.7M |
| TECAL Cavatini | $19.5M |
| GRIMOLDI | $13.7M |
| DISTRINANDO MODA | $12.9M |
| A NATION | $9.3M |
| MARIO INNOVA | $7.5M |
| TXT Pack | $6.3M |
| Compras y Gastos Varios | $4.5M |
| COMPRANDO EN GRUPO | $4.2M |

**Total a favor: ~$135M** — Estos proveedores tienen mas pagos que facturas en su CC. Puede ser:
- Anticipos no aplicados
- NC pendientes de imputar
- Error de carga en el ERP

**ACCION**: Revisar con Contabilidad si son saldos reales o errores de imputacion. KALIF ($33M) y DISTRINANDO ($23.7M+$12.9M = $36.6M) son los mas urgentes.

---

## 2. RECUPERO INVERSION

### 🔴 CRITICO: 15 proveedores con dias_50 > 120 (muy lentos para vender)

| Proveedor | Industria | Dias 50% | ROI% | % Vend al Pago | Brecha | Inversion |
|-----------|-----------|----------|------|----------------|--------|-----------|
| ALPARGATAS | Mixto_Zap_Dep | 124d | 138% | 28% | -71d | $79.9M |
| ALPARGATAS | Indumentaria | 136d | 140% | 33% | -86d | $27.4M |
| CALZADOS BLANCO (Diadora) | Deportes | 137d | 127% | 43% | -37d | $16.8M |
| DEPORTEGUI | Deportes | 130d | 129% | 11% | -75d | $11.7M |
| Souter (RINGO) | Mixto_Zap_Dep | 195d | 83% | 0% | -153d | $11.0M |
| ALFA CALZADOS | Mixto_Zap_Dep | 175d | 99% | 0% | -63d | $9.6M |
| A NATION | Deportes | 168d | 95% | 0% | -117d | $9.2M |
| El Dante | Deportes | 168d | 102% | 30% | -88d | $8.2M |
| Grupo Inversia | Mixto_Zap_Dep | 138d | 131% | 0% | -79d | $8.2M |
| DISTRINANDO MODA | Deportes | 121d | 148% | 34% | -18d | $7.7M |

**HALLAZGOS CLAVE**:
- **ALPARGATAS** es el caso mas critico: $107M invertidos, 124-136 dias para vender la mitad. Brecha -71 a -86 dias = pagamos MUCHO antes de recuperar.
- **SOUTER (RINGO)**: 195 dias al 50%, 0% vendido al pago, brecha -153d. El peor calce financiero del portfolio.
- **Proveedores con 0% vendido al pago**: Souter, Alfa, A Nation, Inversia, Cirene, HEY DAY — esto significa que al momento de pagar la factura, NO vendimos nada todavia. Capital 100% propio.

### 🟡 ATENCION: Proveedores con ROI < 100%
- Souter 83%, A NATION 95%, HEY DAY 84%, ALFA 99% — estos no solo tardan en venderse, sino que el margen no compensa la inmovilizacion.

---

## 3. CHEQUES Y PAGOS

### 🔴 CRITICO: $87.4M en cheques abril (44 cheques)

| Mes | Total | Cheques |
|-----|-------|---------|
| Abr-26 | $87.4M | 44 |
| May-26 | $94.3M | 49 |
| Jun-26 | $70.5M | 29 |
| Jul-26 | $32.9M | 9 |
| Ago-26 | $1.8M | 1 |

**Top 5 pagos proximos 30 dias:**
1. DISTRINANDO MODA: $18.5M (7 cheques, 13-30 abr)
2. DISTRINANDO DEPORTES: $14.3M (9 cheques, 13-24 abr)
3. VICBOR: $13.0M (3 cheques, 17 abr - 4 may)
4. INDUSTRIAS G&D (Storkman): $6.5M (2 cheques, 23 abr)
5. KALIF: $6.0M (3 cheques, 27-30 abr)

**Distrinando (Moda+Deportes) concentra $32.8M** en abril — es el 37% del total del mes.

### 🔴 CRITICO: Cheques con fechas IMPOSIBLES
Hay cheques con vencimiento en 2028, 2033, 2170, 2201, 2250, 2400, 2502, 3000, 5000, 6095, 7000, 7300, 9700. Son 15 registros con montos chicos ($725 a $500K) pero fechas basura. Probablemente errores de carga donde se puso el nro de cheque en el campo fecha.

**ACCION**: Limpiar estos registros en ordpag1. No afectan el flujo real pero ensucian los reportes.

---

## 4. REMITOS SIN FACTURAR

Query fallo por nombre de campo `proveedor` — corregir a `numero_cuenta` en proxima ejecucion.

---

## 5. PRESUPUESTO

### 🔴 CRITICO: Cosmetica sobreejecutada

| Industria | Temporada | Presupuesto | Comprometido | Ejecucion | Disponible |
|-----------|-----------|-------------|--------------|-----------|------------|
| Cosmetica | PV | $22.3M | $43.6M | **195%** | -$21.3M |
| Cosmetica | OI | $30.0M | $43.6M | **145%** | -$13.6M |
| Marroquineria | OI | $97.8M | $51.0M | 52% | $46.7M |
| Zapateria | OI | $313.3M | $21.2M | 7% | $292.1M |
| Mixto_Zap_Dep | H2 | $228.9M | $4.0M | 2% | $224.9M |
| Deportes | H1 | $487.9M | $1.8M | **0.4%** | $486.1M |
| Indumentaria | OI | $90.4M | $0 | **0%** | $90.4M |

**Cosmetica**: comprometio el doble del presupuesto. Pero las unidades suben 51% asi que puede estar justificado. El ticket cae 10% — estan vendiendo mix mas barato.

**Deportes/Mixto/Indumentaria**: ejecucion < 2%. Estamos en abril y la temporada OI ya arranco — si no hay pedidos cargados, estos presupuestos estan subejecuados. Puede ser que los pedidos no se cargaron al sistema todavia.

---

## 6. PATRONES / APRENDIZAJES

### 📊 Concentracion DISTRINANDO
Distrinando (Deportes + Moda) representa:
- $36.6M de saldo a favor (nos deben)
- $32.8M en cheques proximos 30 dias
- Y a la vez DISTRINANDO MODA tiene 121 dias al 50%, brecha -18d

Es el proveedor con mayor volumen de operaciones. La relacion financiera es compleja — hay pagos cruzados entre las dos razones sociales.

### 📊 Alpargatas: volumen vs eficiencia
$107M de inversion total, 124-136 dias al 50%. ROI ~138% parece bueno pero la brecha (-71 a -86d) significa que financiamos con capital propio durante 2-3 meses antes de recuperar. A tasa de mercado, eso es un costo implicito significativo.

### 📊 Proveedores "fantasma" con 0% vendido al pago
6 proveedores con 0% vendido al momento del pago y > $5M de inversion. Estos son pure capital propio — la mercaderia llega, se paga, y recien empieza a venderse despues. Candidatos a negociar plazo.

---

## RESUMEN EJECUTIVO

| Indicador | Valor | Estado |
|-----------|-------|--------|
| Saldo a favor proveedores | $135M | 🔴 Revisar |
| Proveedores lentos (>120d) | 15 | 🔴 $240M comprometidos |
| Cheques abril | $87.4M / 44 cheques | 🟡 Concentrado en Distrinando |
| Cheques mayo | $94.3M / 49 cheques | 🟡 Pico del semestre |
| Cosmetica sobreejecutada | 195% del presupuesto | 🔴 Revisar |
| Deportes subejecutado | 0.4% del presupuesto | 🟡 Faltan pedidos? |
| Cheques fecha basura | 15 registros | 🟡 Limpiar |
