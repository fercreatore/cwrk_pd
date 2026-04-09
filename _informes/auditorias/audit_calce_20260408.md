# AUDITORÍA CALCE FINANCIERO — H4 / CALZALINDO
**Fecha:** 2026-04-08  
**Fuente:** msgestionC (producción 111) via MCP sql-replica  
**Generado:** automaticamente por tarea programada `calce-financiero-audit`

---

## RESUMEN EJECUTIVO

| Nivel | Cantidad |
|-------|----------|
| 🔴 CRÍTICO | 4 |
| 🟡 ATENCIÓN | 7 |
| 🟢 OK | 3 |
| 📊 APRENDIZAJE | 5 |

**Total comprometido en cheques próximos 30 días: ~$92.4M**  
**Cheques urgentes (próximos 7 días): ~$16.8M**

---

## 1. ANOMALÍAS EN DEUDA

### 🔴 CRÍTICO — Shoeholic deuda huérfana $35.1M

Proveedor 2 (Shoeholic) tiene saldo deudor de **$35,099,321** y su **última compra fue septiembre 2025** (~7 meses sin actividad).
Esto es deuda en libros sin compras activas — riesgo de que sea una obligación olvidada o proveedor inactivo.
**Acción requerida:** Verificar si hay NC pendientes, si la deuda es válida o requiere gestión de cobro/regularización.

### 🟡 ATENCIÓN — Saldos negativos (nos deben) por $128M en 20 proveedores

Proveedores donde el saldo neto es negativo (ellos nos deben o tenemos créditos a favor):

| Proveedor | Código | Saldo a nuestro favor |
|-----------|--------|----------------------|
| KALIF - ALEX SPORT | 817 | $33,304,732 |
| DISTRINANDO DEPORTES | 656 | $23,702,939 |
| TECAL Cavatini | 960 | $19,500,000 |
| GRIMOLDI | 264 | $13,666,932 |
| DISTRINANDO MODA | 713 | $12,863,537 |
| A NATION | 769 | $9,332,908 |
| MARIO INNOVA | 1436 | $7,456,060 |
| TXT Pack | 1142 | $6,288,000 |
| COMPRANDO EN GRUPO | 853 | $4,230,977 |
| Baudracco | 1155 | $3,857,806 |
| HAD. Seguros | 1137 | $3,302,036 |
| LADY STORK | 99 | $3,242,477 |
| GO Servicios Digitales | 1208 | $3,004,585 |
| TENISA S.A. | 523 | $2,967,800 |
| MERCADO LIBRE | 1261 | $2,555,853 |
| EDEN energía | 1201 | $2,358,159 |
| RAPICUOTAS | 1497 | $2,240,889 |
| FERNANDA | 1457 | $2,000,000 |
| DISTRIGROUP | 860 | $1,999,961 |

> Nota: DISTRINANDO DEPORTES (656) es proveedor activo con compras en 2025 ($150M). El saldo negativo puede ser por NC aplicadas o pagos adelantados. Igual requiere verificación.
> Nota: COMPRAS Y GASTOS VARIOS (1158) con -$4.5M es cuenta interna de gastos — normal pero verificar.

### 🟡 ATENCIÓN — Facturas "fantasma" vencidas desde 2015-2019

Se detectan 30+ facturas con vencimiento entre 2015 y 2019, montos pequeños ($1K–$127K), de proveedores como PAW, TAMANGO, GEUX, CUBRITAS, Roberto Gentile SA, etc. La deuda histórica más relevante:
- Roberto Gentile SA (1161): $127K (mar-2019) + $111K (mar-2019)
- Alquileres Cala (1166): $84K (ene-2019)

Estas son probablemente deudas irecuperables contabilizadas. **Acción:** Evaluar si corresponde una pasada contable de baja (NC o regularización).

---

## 2. RECUPERO DE INVERSIÓN

### 🔴 CRÍTICO — ALPARGATAS cayó -61% en compras (2024→2025)

| Proveedor | Compras 2024 | Compras 2025 | Variación |
|-----------|-------------|-------------|-----------|
| ALPARGATAS (668) | $1,094M | $426M | **-61%** |
| DISTRINANDO DEPORTES (656) | $488M | $150M | **-69%** |
| TIVORY (950) | $219M | $76M | **-65%** |
| PRIMER ROUND (770) | $187M | $73M | **-61%** |
| GRIMOLDI (264) | $339M | $200M | **-41%** |
| VICBOR (594) | $490M | $342M | **-30%** |
| Souter/RINGO (561) | $118M | $74M | **-37%** |
| CALZADOS BLANCO (614) | $125M | $99M | **-21%** |

Los top 4 representan una caída acumulada de **~$1,280M** vs 2024. Es la mayor señal de ajuste de inventario/capital de los últimos años. Puede ser intencional (menor deuda temporada), pero exige verificar que no sea falta de stock/oferta.

### 🟢 OK — Proveedores en expansión (diversificación saludable)

| Proveedor | Compras 2024 | Compras 2025 | Variación |
|-----------|-------------|-------------|-----------|
| DISTRINANDO MODA (713) | $142M | $195M | +37% |
| LESEDIFE (42) | $90M | $189M | **+111%** |
| GLOBAL BRANDS/OLK (722) | $99M | $144M | +44% |
| ZOTZ (457) | $30M | $91M | **+204%** |
| CLZ BEAUTY (990) | $24M | $78M | **+231%** |
| LANACUER (669) | $42M | $71M | +69% |

Diversificación positiva — nuevas marcas ganando peso. ZOTZ y CLZ BEAUTY (medias) son casos de éxito.

### 🟡 ATENCIÓN — Shoeholic: $127M comprado en 2025, sin compras desde sep-2025

Proveedor relativamente nuevo (no tenía compras en 2024), facturó $127M en 5 facturas en 2025. Última compra sep-2025. Tiene deuda pendiente $35M. **Verificar** estado de relación y si hay mercadería pendiente de entregar.

### 🟡 ATENCIÓN — BANCO NACION: $92M en compras (era $3M en 2024)

Aumento de 3,106% sugiere financiamiento significativo con BNA. Verificar tasas y condiciones en el contexto de fin de temporada invierno 2025.

### 🔴 CRÍTICO — Reebok (marca 513) cayó -41% en pares

Marca 513 (Reebok/DISTRINANDO DEPORTES): 
- 2024: $138M, 1,934 pares  
- 2025: $104M, 1,134 pares → **-41% en pares**

Dado que DISTRINANDO DEPORTES tuvo una caída del -69% en compras y actualmente tiene saldo negativo (-$23.7M), esto sugiere que se redujo fuertemente la exposición a Reebok. Verificar si fue decisión o problema de oferta/quiebre.

---

## 3. CHEQUES Y PAGOS

### 🔴 CRÍTICO — $16.8M a pagar en 7 días (10-15 de abril)

| Fecha | Proveedor | Importe | Tipo |
|-------|-----------|---------|------|
| 10-abr | TIVORY TRADING (950) | $2,453,039 | ECheq |
| 10-abr | Compras y Gastos Varios | $1,500,000 | Interno |
| 13-abr | DISTRINANDO MODA (713) | $7,000,000 | ECheq |
| 13-abr | DISTRINANDO MODA (713) | $479,540 ×3 | Cheques |
| 13-abr | DISTRINANDO DEPORTES (656) | $161,320 ×6 | Cheques |
| 13-abr | TXT Pack (1142) | $350,000 | Interno |
| 13-abr | RIMON CASSIS (664) | $479,540 ×2 | Cheques |
| 13-abr | PIANINO SRL (983) | $479,540 | Cheque |
| 14-abr | CALZADOS GUNAR (780) | $77K + $98K + $185K | Cheques |
| 14-abr | Gondolino (57) | $255K + $451K | Cheques |
| 15-abr | DISTRINANDO MODA (713) | $5,000,000 | ECheq |

**Total aproximado días 10-15 abr: ~$16.8M**

### 🟡 ATENCIÓN — Total próximos 30 días: ~$92.4M

| Proveedor | Cheques | Total |
|-----------|---------|-------|
| DISTRINANDO MODA (713) | 7 | $18,532,354 |
| DISTRINANDO DEPORTES (656) | 9 | $14,270,897 |
| VICBOR (594) | 3 | $12,969,657 |
| KALIF - ALEX SPORT (817) | 4 | $8,000,000 |
| INDUSTRIAS G&D (100) | 2 | $6,542,704 |
| CALZADOS GUNAR (780) | 4 | $4,698,336 |
| CALZADOS FERLI (693) | 1 | $4,300,000 |
| BALL ONE (608) | 1 | $3,672,056 |
| GRIMOLDI (264) | 1 | $3,551,460 |
| BAGUNZA (963) | 1 | $3,000,000 |
| (otros 10 proveedores) | — | ~$12,900,000 |
| **TOTAL** | **~34** | **~$92.4M** |

### 🟡 ATENCIÓN — DISTRINANDO DEPORTES: 9 cheques + saldo negativo $23.7M

Este proveedor tiene simultáneamente:
1. 9 cheques pendientes por $14.3M (próximos 30 días)
2. Saldo negativo de -$23.7M (tenemos crédito a favor)

Esto es contradictorio. Antes de emitir los cheques, **verificar si el saldo negativo aplica como compensación** o si son cuentas separadas (NC no aplicadas).

---

## 4. REMITOS SIN FACTURAR

### 🟡 ATENCIÓN — 4 remitos de 2026 sin facturar

| Proveedor | Remito | Fecha | Monto | Días sin factura |
|-----------|--------|-------|-------|-----------------|
| MATIAS SUBIRADA (955) - Remeras | R-36/6625 | 03-ene-2026 | $240,000 | **95 días** 🔴 |
| GO by CZL (17) | R-1/23456 | 09-feb-2026 | $874,000 | 58 días |
| VICBOR (594) | R-43/188196 | 24-feb-2026 | $304,104 | 43 días |
| TIMMi NEW SHOES (11) | R-2/64431 | 18-mar-2026 | $711,000 | 21 días |

El remito de Subirada (remeras) lleva **95 días sin facturar** — es una anomalía administrativa seria. El de GO by CZL (58 días) también preocupa dado que es cuenta interna (¿depósito?).

**Acción:** Contactar proveedores para regularizar. El de Subirada puede ser un remito en disputa o simplemente olvidado.

---

## 5. VENTAS Y ESTACIONALIDAD

### 🟢 OK — Diciembre 2025 fue el pico histórico observado

Rubro 1 (Calzado mujer/principal): $354M y 9,317 pares  
Rubro 3 (Deportivo/running): $192M y 5,407 pares  
Total diciembre: ~$675M — el mes más alto del período analizado.

### 📊 APRENDIZAJE — Febrero 2026: rubro 4 explotó (+240% vs ene)

| Mes | Rubro 4 pares | Rubro 4 $ |
|-----|--------------|-----------|
| Enero 2026 | 1,273 | $31.5M |
| Febrero 2026 | 4,183 | $94.2M | ← +229% |
| Marzo 2026 | 1,884 | $35.2M |

El salto del rubro 4 en febrero es inusual (probablemente folclore/comunión). Verificar si es quiebre registrado como venta en una sola factura o temporada puntual. Rubro 6 también saltó de $13M a $41M ese mes.

### 📊 APRENDIZAJE — Estacionalidad rubro 1 (calzado principal)

```
Abr-25: $151M | May: $235M | Jun: $223M | Jul: $249M | Ago: $192M
Sep: $190M | Oct: $318M | Nov: $244M | Dic: $354M
Ene-26: $180M | Feb: $136M | Mar: $163M | Abr (parcial): $43M
```

Pico claro en **octubre y diciembre**. Caída natural en ene-feb. Marzo ya recupera. El piso de verano (ene-feb) es ~$136-180M nominales.

---

## 6. MARCAS — TENDENCIAS 2023→2025

### 📊 APRENDIZAJE — Top 30 marcas por ventas 2025

| Marca | Código | Ventas 2025 | Var vs 2024 | Pares 2025 |
|-------|--------|-------------|-------------|-----------|
| Topper (Alpargatas) | 314 | $917M | +7% | 15,710 |
| **Marca 17** | 17 | $412M | **+244%** | 5,769 |
| Vicbor/Atomik | 594 | $297M | +58% | 4,995 |
| Grimoldi | 264 | $181M | -8% | 2,050 |
| Marca 746 | 746 | $166M | +68% | 4,931 |
| Marca 139 | 139 | $156M | +63% | 3,159 |
| Lesedife (42) | 42 | $137M | +36% | 6,397 |
| Marca 770 | 770 | $118M | +12% | 3,214 |
| Rofreve (311) | 311 | $114M | +4% | 3,779 |
| Carmel (294) | 294 | $104M | +11% | 1,169 |
| Reebok (513) | 513 | $104M | **-24%** | 1,134 |
| CLZ Beauty | 990 | $81M | **+211%** | 8,465 |
| Lady Stork (99) | 99 | $71M | -12% | 789 |

> **Marca 17** (código coincide con "GO by CZL" como proveedor interno, puede ser marca propia/multimarca). +244% nominal y +146% en pares. Investigar identidad real.
> **Marca 515** (medias/calcetines): $46M, 19,325 pares — el mayor volumen de unidades. Precio ~$2,400/par implica precio muy bajo = medias o accesorios.

### 📊 APRENDIZAJE — Marcas en declive acelerado (volumen pares)

- **Reebok (513)**: -41% en pares (1,934 → 1,134). Reducción intencional post-análisis quiebre.
- **Lady Stork (99)**: -31% en pares (1,138 → 789). Marca en retroceso sostenido.
- **Marca 765**: -30% en pares (2,568 → 1,805). Identificar y revisar estrategia.
- **GTN (104)**: -21% en pares (2,248 → 1,787). Proveedor activo config.py.

### 🔴 CRÍTICO — Alpargatas (314): estancamiento real de pares pese a +$60M nominal

| Año | Ventas ($) | Pares |
|-----|-----------|-------|
| 2023 | $255M | 13,859 |
| 2024 | $857M | 16,050 |
| 2025 | $917M | 15,710 |

El crecimiento de 2024→2025 es solo +7% nominal, pero **los pares BAJARON** de 16,050 a 15,710 (-2%). Esto significa que el crecimiento fue puramente inflacionario. En volumen real, Topper está estancado. Dado que fue el principal proveedor y se compró -61% menos en 2025, hay un ajuste de inventario importante. Verificar si hay quiebre o si fue una decisión táctica.

---

## ACCIONES PRIORITARIAS

### URGENTES (esta semana)

1. **Confirmar fondos para vencimientos 10-13 abr**: TIVORY $2.45M (10-abr) + DISTRINANDO MODA $7M ECheq (13-abr) = $9.45M en los próximos 5 días.
2. **Cruzar saldo -$23.7M DISTRINANDO DEPORTES vs 9 cheques pendientes $14.3M**: Antes del 13-abr confirmar si aplica compensación.
3. **Remito Subirada 95 días**: Contactar a Matias Subirada para que facture el remito R-36/6625 de enero ($240K).

### ESTA SEMANA

4. **Shoeholic $35.1M deuda sin compras**: Verificar si es válida, si hay mercadería pendiente o si corresponde NC/baja.
5. **Remito GO by CZL 58 días** ($874K): Es cuenta interna — confirmar si es un movimiento entre depósitos sin facturar.

### PRÓXIMAS 2 SEMANAS

6. **Evaluar concentración Alpargatas**: Compras cayeron -61%, pares estancados. Definir volumen OI2026.
7. **Baja contable de deudas históricas 2015-2019**: PAW, Tamango, Geux tienen facturas de hace 10 años. Pasada de limpieza contable.
8. **Identificar marcas 17, 746, 770**: Están entre las top 5 de ventas 2025 sin nombre en la tabla `marcas`.

---

*Reporte generado: 2026-04-08 | Próxima auditoría: automática semanal*
