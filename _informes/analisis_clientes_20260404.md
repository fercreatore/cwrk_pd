# Analisis de Base de Clientes — Calzalindo / H4
> Fecha: 4 de abril de 2026
> Periodo analizado: ultimos 24 meses (abril 2024 - abril 2026)
> Fuente: msgestionC.dbo.ventas1 + msgestion01art.dbo.articulo
> Filtros: excluidos codigos 7,36 (remitos internos), marcas gastos (1316,1317,1158,436), cantidad>0

---

## 1. RESUMEN EJECUTIVO

| Metrica | Valor |
|---------|-------|
| Clientes unicos (con cuenta) | 49,294 |
| Ventas anonimas (cuenta=NULL) | $1,978M (43,798 pares) — 18.1% del total |
| Venta total 24 meses | $10,900M |
| Pares total 24 meses | 343,187 |
| Ticket promedio mediana | $55,650 |
| Pares por cliente mediana | 3 |

### Hallazgos Clave

1. **La venta esta hiper-concentrada**: el 1.4% de los clientes (695) genera el 16.2% de la facturacion. El top 24% (Champions) genera el 57% del revenue.
2. **48.7% de los clientes NO compro en mas de 1 anio** (23,999 cuentas), pero representan $2,085M (23.4%) — son ventas historicas que se perdieron.
3. **La cuenta "SIN CAMBIO, SIN GARANTIA" (41065967) es un comodin POS** con $343M en 24 meses (22,989 pares), presente en TODOS los locales. No es un cliente real.
4. **Se identificaron ~45 cuentas empleado** con $43.7M en ventas (descuento empleado).
5. **La familia Calaianov tiene 10 cuentas** sumando $37.7M — son compras familiares/propietarios.
6. **"CLZ PREMIOS" (41062275)** es una cuenta de premios/canjes con $16.4M, 1,362 pares.

---

## 2. CUENTAS A EXCLUIR DEL ANALISIS COMERCIAL

### 2.1 Cuentas Especiales / Internas

| Cuenta | Nombre | Venta 24m | Pares | Motivo |
|--------|--------|-----------|-------|--------|
| 41065967 | SIN CAMBIO, SIN GARANTIA | $342,955,000 | 22,989 | Comodin POS — cambios sin ticket |
| 41062275 | CLZ, PREMIOS | $16,383,000 | 1,362 | Canjes de premios/puntos |
| NULL | (anonimo) | $1,977,789,000 | 43,798 | Ventas sin identificacion |

### 2.2 Empleados Identificados (tag "emp" en nombre)

Se encontraron **52 cuentas con tag (emp)/(empleado)/(empl)** en la denominacion del cliente. De estas, 38 tuvieron ventas en los ultimos 24 meses:

| Cuenta | Nombre | Venta 24m | Pares | Dias |
|--------|--------|-----------|-------|------|
| 24582288 | GIBELLI GIANA (emp) | $6,940,000 | 278 | 99 |
| 7213 | DAMARIO LUZ (emp) | $5,735,000 | 301 | 126 |
| 18032136 | Rodriguez Camila Mariel (emp) | $4,759,000 | 275 | 96 |
| 19900356 | LOPEZ MARIANA* (emp) | $4,521,000 | 167 | 79 |
| 24573941 | DITURO FLORENCIA (emp) | $3,136,000 | 109 | 54 |
| 41094863 | SUARES AGUSTINA (empleada) | $2,286,000 | 122 | 56 |
| 24588063 | ARANCIBIA NEREA (emp) | $2,112,000 | 125 | 60 |
| 19900876 | PEDOTTA MAILEN (emp) | $2,005,000 | 185 | 48 |
| 41095289 | REYES, ROCIO MARISOL (empl) | $1,875,000 | 101 | 49 |
| ... y 29 mas | | | | |
| **TOTAL EMPLEADOS** | | **$43,680,000** | **2,200** | |

**Observacion**: Las empleadas top compran en promedio ~$1.4M/anio con alta frecuencia (100+ dias). Esto representa un beneficio laboral significativo.

### 2.3 Familia Calaianov (propietarios)

| Cuenta | Nombre | Venta 24m | Pares | Dias |
|--------|--------|-----------|-------|------|
| 2129 | Calaianov Leonardo | $13,584,000 | 380 | 110 |
| 6601 | Calaianov Fernando Matias | $11,664,000 | 395 | 140 |
| 7836 | Calaianov Tamara | $7,511,000 | 272 | 113 |
| 18030705 | Calaianov Guillermo | $4,684,000 | 103 | 45 |
| 2801 | Calaianov Patricia | $259,000 | 9 | 5 |
| 1995 | Calaianov Fernando Lujan | (sin ventas 24m) | | |
| 19992188 | Calaianov Elizabeth | (sin ventas 24m) | | |
| 410627565 | CALAIANOV, CLAUDIO | (sin ventas 24m) | | |
| 410643544 | CALAIANOV, LUCRECIA | (sin ventas 24m) | | |
| 41066963 | SUCESION DE CALAIANOV F.L. | (sin ventas 24m) | | |
| **TOTAL CALAIANOV** | | **$37,702,000** | **1,159** | |

### 2.4 Resumen Exclusiones

| Grupo | Cuentas | Venta | % del Total |
|-------|---------|-------|-------------|
| SIN CAMBIO (POS) | 1 | $343M | 3.1% |
| Ventas anonimas | 1 | $1,978M | 18.1% |
| Empleados | 38 | $44M | 0.4% |
| Familia Calaianov | 5 activos | $38M | 0.3% |
| CLZ PREMIOS | 1 | $16M | 0.2% |
| **TOTAL EXCLUIDO** | **46** | **$2,419M** | **22.2%** |

**Venta real de clientes genuinos: ~$8,481M en 24 meses.**

---

## 3. DISTRIBUCION ESTADISTICA (clientes reales, sin exclusiones)

### 3.1 Venta Total por Cliente

| Percentil | Monto |
|-----------|-------|
| P10 | $26,315 |
| P25 (Q1) | $50,433 |
| P50 (Mediana) | $92,983 |
| P75 (Q3) | $200,000 |
| P90 | $387,122 |
| P95 | $556,540 |
| P99 | $1,041,533 |
| Media | $180,999 |
| Max | $46,148,562 |

### 3.2 IQR y Outliers

- IQR = Q3 - Q1 = $200,000 - $50,433 = **$149,567**
- Upper fence (Q3 + 1.5*IQR) = **$424,351**
- High outliers: **4,179 clientes** (8.5%) por encima del fence
- Estos 4,179 representan la mayor parte de la facturacion

### 3.3 Pares por Cliente

| Percentil | Pares |
|-----------|-------|
| P10 | 1 |
| P25 | 1 |
| P50 | 3 |
| P75 | 6 |
| P90 | 12 |
| P95 | 18 |
| P99 | 35 |

**Interpretacion**: El cliente tipico compra 3 pares en 2 anios. El 75% compra 6 o menos. Solo el top 5% compra mas de 18 pares.

### 3.4 Ticket Promedio por Visita

| Percentil | Ticket |
|-----------|--------|
| P10 | $21,052 |
| P25 | $35,599 |
| P50 | $55,650 |
| P75 | $80,132 |
| P90 | $108,740 |
| P95 | $132,999 |

---

## 4. SEGMENTACION POR FRECUENCIA

| Frecuencia (dias con compra) | Clientes | % Clientes | Venta | % Venta |
|------------------------------|----------|------------|-------|---------|
| 1 visita | 23,485 | 47.6% | $1,445M | 16.2% |
| 2-3 visitas | 15,140 | 30.7% | $2,250M | 25.2% |
| 4-6 visitas | 7,080 | 14.4% | $2,149M | 24.1% |
| 7-12 visitas | 2,894 | 5.9% | $1,635M | 18.3% |
| 12+ visitas | 695 | 1.4% | $1,443M | 16.2% |

**Insight critico**: Casi la mitad (47.6%) de los clientes identificados compro UNA SOLA VEZ en 2 anios. Sin embargo, generan solo 16% del revenue. El negocio depende del 22% que vuelve 4+ veces (58.6% del revenue).

---

## 5. SEGMENTACION POR RECENCIA

| Ultima compra | Clientes | % Clientes | Venta Acumulada | % Venta |
|---------------|----------|------------|-----------------|---------|
| Ultimos 30 dias | 2,596 | 5.3% | $1,482M | 16.6% |
| 31-60 dias | 3,439 | 7.0% | $1,190M | 13.3% |
| 61-90 dias | 2,369 | 4.8% | $667M | 7.5% |
| 91-180 dias | 8,139 | 16.5% | $1,880M | 21.1% |
| 181-365 dias | 8,752 | 17.8% | $1,618M | 18.1% |
| Mas de 1 anio | 23,999 | 48.7% | $2,085M | 23.4% |

**Clientes activos (compra en ultimos 365 dias): 25,295 (51.3%)**
**Clientes dormidos (>365 dias): 23,999 (48.7%)**

---

## 6. ANALISIS RFM (Recency, Frequency, Monetary)

Scoring 1-5 por quintiles. Segmentos definidos por combinacion R/F/M.

| Segmento | Clientes | % Clientes | Revenue | % Revenue | Ticket Promedio |
|----------|----------|------------|---------|-----------|-----------------|
| **Champions** | 11,936 | 24.2% | $4,849M | 57.2% | $406,213 |
| **Loyal Customers** | 9,096 | 18.5% | $1,698M | 20.0% | $186,720 |
| **At Risk** | 5,279 | 10.7% | $840M | 9.9% | $159,122 |
| **Lost** | 13,298 | 27.0% | $639M | 7.5% | $48,032 |
| New Customers | 3,362 | 6.8% | $153M | 1.8% | $45,559 |
| About to Sleep | 3,038 | 6.2% | $136M | 1.6% | $44,715 |
| Potential Loyalists | 2,119 | 4.3% | $111M | 1.3% | $52,557 |
| Need Attention | 733 | 1.5% | $44M | 0.5% | $59,583 |

### Interpretacion RFM

- **Champions (24.2%)**: Compran seguido, hace poco, y mucho. Son el corazon del negocio con $4,849M (57%). Ticket promedio 8x mayor que Lost.
- **Loyal Customers (18.5%)**: Buenos clientes regulares. $186K promedio. Potencial para subir a Champions con incentivos.
- **At Risk (10.7%)**: Antes compraban mucho y seguido pero hace rato que no vienen. $840M en riesgo. **PRIORIDAD #1 para WhatsApp reactivacion.**
- **Lost (27.0%)**: La cuarta parte de la base. Compraron poco y hace mucho. Baja probabilidad de retorno organico.
- **New Customers (6.8%)**: Compraron recientemente pero pocas veces. Clave para convertirlos en Loyals.

### CLV (Customer Lifetime Value) Estimado a 3 Anios

| Segmento | CLV 3 anios promedio | Gasto mensual promedio |
|----------|---------------------|----------------------|
| Champions | $609,320 | $16,926 |
| Loyal Customers | $280,081 | $7,780 |
| At Risk | $238,683 | $6,630 |

---

## 7. RENDIMIENTO POR LOCAL (deposito)

| Dep | Local | Clientes | Venta 24m | Pares | Ticket Avg |
|-----|-------|----------|-----------|-------|------------|
| 0 | Central VT | 26,299 | $5,135M | 172,372 | $31,068 |
| 1 | Glam / MercadoLibre | 7,326 | $1,522M | 22,214 | $68,895 |
| 8 | Junin | 5,359 | $1,314M | 33,957 | $38,780 |
| 6 | Cuore / Chovet | 6,309 | $671M | 19,889 | $34,130 |
| 2 | Norte | 5,364 | $626M | 26,861 | $23,618 |
| 7 | Eva Peron | 4,874 | $537M | 23,448 | $23,161 |
| 9 | Tokyo Express | 5,324 | $483M | 21,247 | $22,932 |
| 15 | (nuevo) | 866 | $181M | 5,341 | $33,990 |
| 10 | (deposito 10) | 393 | $166M | 7,017 | $26,300 |
| 4 | Marroquineria | 692 | $163M | 6,675 | $24,543 |

**Observaciones**:
- **Central VT** domina con 51% de la clientela y 47% de la venta.
- **Glam/ML** tiene el ticket mas alto ($68,895) — es e-commerce/deportivo premium.
- **Junin** es el 2do local en venta ($1,314M) con buen ticket ($38,780).
- **Norte, Eva Peron y Tokyo** son los locales de barrio con tickets mas bajos (~$23K).

---

## 8. DISTRIBUCION GEOGRAFICA (zonas con venta en ultimos 12m)

| Zona | Clientes | Venta 12m | Posible Localidad |
|------|----------|-----------|-------------------|
| 1 | 8,711 | $1,256M | Venado Tuerto (local) |
| 62 | 78 | $212M | (zona mayorista?) |
| 34 | 1,057 | $156M | Zona regional |
| 26 | 340 | $74M | |
| 0 | 439 | $62M | Sin zona asignada |
| 72 | 296 | $61M | |
| 58 | 207 | $48M | |
| 13 | 67 | $45M | (familia/empleados?) |

**Nota**: Zona 1 (Venado Tuerto) concentra el 73% de los clientes y ~57% de la venta. Zona 62 llama la atencion: solo 78 clientes pero $212M — podria ser una zona de revendedores o mayoristas.

---

## 9. TOP 50 CLIENTES REALES (excluidos internos/empleados/familia)

| # | Cuenta | Nombre | Venta 24m | Pares | Freq | Rec | Segmento |
|---|--------|--------|-----------|-------|------|-----|----------|
| 1 | 18036297 | Bocco Mariel Soledad | $46,149,000 | 1,265 | 56d | 44d | Champions |
| 2 | 15235 | Companiuchi Jose Luis | $38,364,000 | 1,430 | 42d | 48d | Champions |
| 3 | 41086129 | Becerro, Yesica | $33,081,000 | 1,542 | 305d | 1d | Champions |
| 4 | 41088345 | Ambrosetti, Candela | $19,808,000 | 870 | 182d | 2d | Champions |
| 5 | 41070187 | Beron, Elda | $13,489,000 | 854 | 13d | 298d | Loyal |
| 6 | 41062092 | Almiron, Elisa | $11,688,000 | 514 | 202d | 4d | Champions |
| 7 | 41075835 | Saenz, Luciano | $11,052,000 | 532 | 216d | 3d | Champions |
| 8 | 41084149 | Fleitas, Dario Anibal | $9,219,000 | 222 | 12d | 62d | Champions |
| 9 | 41087075 | Gutierrez, Ainalen | $8,978,000 | 301 | 106d | 3d | Champions |
| 10 | 18032048 | Galvan Tamara | $8,502,000 | 382 | 176d | 13d | Champions |
| 11 | 24578119 | Ruggieri, Yamile | $8,258,000 | 565 | 184d | 207d | Champions |
| 12 | 41088665 | Rodriguez, Luisina | $7,427,000 | 353 | 120d | 16d | Champions |
| 13 | 41087199 | Corrales, Caren | $6,905,000 | 316 | 68d | 10d | Champions |
| 14 | 24570631 | Fernandez Abigail Magali | $6,401,000 | 246 | 8d | 372d | Loyal |
| 15 | 18017 | Delmonte Gervacio | $6,297,000 | 254 | 62d | 14d | Champions |
| 16 | 24581145 | Ruiz, Nadia | $5,408,000 | 384 | 131d | 325d | Loyal |
| 17 | 41097869 | Rodriguez Pamela Natali | $5,163,000 | 319 | 125d | 9d | Champions |
| 18 | 24574459 | Marisa Goico | $5,136,000 | 233 | 58d | 18d | Champions |
| 19 | 6598 | Rubies Monica | $4,434,000 | 145 | 60d | 27d | Champions |
| 20 | 1828328 | Long Dani o Martin LT29 | $4,270,000 | 120 | 33d | 8d | Champions |
| 21 | 18031827 | Villa Juan Ignacio | $3,897,000 | 133 | 34d | 18d | Champions |
| 22 | 41076785 | Falcon, Gisela | $3,862,000 | 363 | 121d | 35d | Champions |
| 23 | 19992513 | Delgado Maria Teresa | $3,828,000 | 90 | 11d | 37d | Champions |
| 24 | 19991904 | Paez Magali | $3,822,000 | 77 | 21d | 48d | Champions |
| 25 | 19848911 | Hervot Marcelo (Marchu) | $3,699,000 | 49 | 28d | 1d | Champions |
| 26 | 41091569 | Maibach Florencia Agustina | $3,512,000 | 171 | 57d | 8d | Champions |
| 27 | 41062404 | Guallanes, Kevin | $3,483,000 | 61 | 21d | 31d | Champions |
| 28 | 19900379 | Cordoba Carolina | $3,467,000 | 155 | 70d | 322d | Loyal |
| 29 | 41084639 | Neli Adriana | $3,440,000 | 123 | 78d | 6d | Champions |
| 30 | 24588166 | Minisi, Carolina | $3,335,000 | 98 | 17d | 116d | Champions |
| 31 | 41093706 | Garcia, Jose Luis | $3,329,000 | 263 | 104d | 8d | Champions |
| 32 | 24571230 | Torancio Romina | $3,288,000 | 203 | 85d | 6d | Champions |
| 33 | 19997263 | Garay Rocio Celeste | $3,280,000 | 134 | 82d | 0d | Champions |
| 34 | 41085329 | Perez, Carlos | $3,243,000 | 84 | 30d | 384d | Loyal |
| 35 | 18052213 | Diaz Maria Laura Susana | $3,225,000 | 159 | 31d | 3d | Champions |
| 36 | 9758 | Calvetto Teresa | $3,188,000 | 68 | 22d | 1d | Champions |
| 37 | 41063564 | Gonzalez, Magali | $3,053,000 | 146 | 72d | 13d | Champions |
| 38 | 8706 | Pandrich Carolina | $3,037,000 | 57 | 12d | 100d | Champions |
| 39 | 15592 | Gutierrez Anahi del Valle | $2,987,000 | 81 | 25d | 37d | Champions |
| 40 | 18032279 | Di Prinzio David | $2,971,000 | 103 | 13d | 111d | Champions |
| 41 | 18048049 | Querzola Americo Nicolas | $2,938,000 | 55 | 31d | 6d | Champions |
| 42 | 41085572 | Andrada, Jorgelina | $2,932,000 | 92 | 50d | 15d | Champions |
| 43 | 41081124 | Fernandez Micaela | $2,895,000 | 141 | 60d | 33d | Champions |
| 44 | 18030064 | Polo Melisa | $2,849,000 | 92 | 17d | 49d | Champions |
| 45 | 41079606 | Gonzalez, Giuliana | $2,838,000 | 118 | 66d | 87d | Champions |
| 46 | 2666 | Ortiz Paola | $2,758,000 | 83 | 59d | 91d | Champions |
| 47 | 18049969 | Benitez Elizabet Soledad | $2,748,000 | 90 | 41d | 6d | Champions |
| 48 | 19994166 | Videla Ignacio Martin | $2,678,000 | 96 | 26d | 69d | Champions |
| 49 | 24570484 | Mercanti Carina | $2,671,000 | 95 | 52d | 0d | Champions |
| 50 | (siguiente) | ... | ~$2,600,000 | | | | |

### Observaciones sobre el Top 50

- **Bocco Mariel Soledad (#1)**: $46M, 1,265 pares. Probable revendedora o compradora institucional.
- **Companiuchi Jose Luis (#2)**: $38M, 1,430 pares. Mismo perfil mayorista.
- **Becerro Yesica (#3)**: $33M, 1,542 pares en 305 DIAS de compra. Compra practicamente todos los dias. Posible empleada no taggeada o revendedora activa.
- **Ambrosetti Candela (#4)**: $19.8M, 870 pares, 182 dias. Similar perfil.
- Los top 4 acumulan $137M y 5,107 pares — son cuentas que merecen atencion personalizada.

---

## 10. CUENTA "SIN CAMBIO, SIN GARANTIA" (41065967) — ANALISIS DETALLADO

Esta cuenta registra $343M y 22,989 pares en 24 meses, presente en TODOS los locales. Es la cuenta comodin para ventas "sin ticket" o cambios. Breakdown por local:

| Deposito | Local | Venta | Pares | Dias |
|----------|-------|-------|-------|------|
| 0 | Central VT | $85.9M | 6,926 | 612 |
| 6 | Cuore/Chovet | $56.9M | 2,766 | 469 |
| 9 | Tokyo Express | $52.1M | 3,518 | 363 |
| 7 | Eva Peron | $41.0M | 3,286 | 538 |
| 2 | Norte | $37.5M | 3,319 | 531 |
| 16 | (dep 16) | $32.1M | 1,527 | 36 |
| 8 | Junin | $18.4M | 799 | 304 |

**Recomendacion**: Esta cuenta deberia tener un procedimiento de limpieza. Los $343M representan clientes reales no identificados — perdida de datos para CRM.

---

## 11. RECOMENDACIONES PARA CAMPANA WHATSAPP

### Prioridad 1: REACTIVACION "At Risk" (5,279 clientes, $840M historico)
- Clientes que antes compraban mucho pero dejaron de venir
- Mensaje: "Te extranamos! Veni a ver las novedades de invierno 2026"
- Incentivo: 10% descuento o 3 cuotas sin interes
- ROI esperado: si se recupera 10%, son ~$84M

### Prioridad 2: UPGRADE "Loyal -> Champions" (9,096 clientes)
- Ya compran regularmente pero con ticket menor
- Mensaje segmentado por ultimo producto comprado
- Cross-sell: "Si te gusto X, te va a encantar Y"
- Incentivo: acceso anticipado a nuevas colecciones

### Prioridad 3: RETENCION Champions (11,936 clientes)
- No arriesgar perderlos. Comunicacion VIP.
- Mensaje: agradecimiento + preview exclusivo temporada
- NO dar descuentos (ya compran al precio completo)

### Prioridad 4: CONVERSION New Customers (3,362 clientes)
- Compraron recientemente pero solo 1-2 veces
- Seguimiento post-compra a los 15 dias
- Mensaje: "Como te fue con tu compra? Tenes 10% en tu proxima visita"
- Objetivo: generar segunda visita (la mas dificil)

### Prioridad 5: RE-ENGAGEMENT Lost (13,298 clientes)
- Baja probabilidad pero volumen alto
- Campana masiva de bajo costo
- Mensaje: "Hace mucho que no te vemos — temporada invierno con 20% off"
- Esperar tasa de apertura baja (<5%)

### Segmentacion por Local
- Enviar ofertas del local mas cercano segun zona
- Zona 1 (VT): centralizar en los 4 locales segun historial
- Zona 34, 72, 58: considerar envio a domicilio o promo e-commerce

### NO contactar
- Empleados (ya tienen su beneficio)
- Familia Calaianov
- Cuenta SIN CAMBIO
- CLZ PREMIOS
- Clientes sin telefono/WhatsApp

---

## 12. METRICAS PARA MONITOREO CONTINUO

| KPI | Valor Actual | Target |
|-----|-------------|--------|
| Clientes activos 365d | 25,295 (51.3%) | >55% |
| Tasa de recompra (2+ visitas en 24m) | 52.4% | >55% |
| Ticket mediana | $55,650 | $60,000 |
| Champions % revenue | 57.2% | Mantener >50% |
| At Risk count | 5,279 | Reducir a <4,000 |
| Lost count | 13,298 | Estabilizar |

---

*Informe generado automaticamente. Datos de msgestionC via pyodbc al 192.168.2.111.*
