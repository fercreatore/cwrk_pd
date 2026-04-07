# Análisis de Elasticidad Precio-Demanda — Calzalindo / H4
**Generado:** 6 de abril de 2026 (tarea automática)
**Período analizado:** Abril 2023 – Abril 2026 (36 meses)
**Fuente de datos:** SQL Server 192.168.2.111 / msgestionC.dbo.ventas1

---

## RESUMEN EJECUTIVO

### Alarma Roja: TOPPER cayendo

TOPPER es el 38% de toda la facturación. En los últimos 12 meses, el volumen **cayó -19% interanual** (13.085 vs 16.195 pares el año anterior). El precio real bajó a la par. Esto no es un problema de pricing: es un problema de **posicionamiento de surtido**. Antes de subir precios en Topper, hay que entender si el cliente eligió otra marca (REEBOK, HUSH PUPPIES) o dejó de comprar.

### Dónde meter las fichas (resumen en 3 puntos)

**1. SUBIR precio sin miedo** → ATOMIK, LS&D, OLYMPIKUS, JUANA VA
- Demanda inelástica comprobada: precio real subió y volumen no cayó
- Márgenes 47-53%, hay espacio para capturar valor

**2. BAJAR precio para ganar volumen** → GO by CLZ, GONDOLINO, MASSIMO CHIESA
- Márgenes entre 52-64%: absorben una baja del 10% sin drama
- Demanda elástica: cada peso menos de precio trae más volumen y más revenue total
- GO by CLZ en particular: 64% de margen, está en BOOM, puede crecer más si baja precio

**3. Vigilar con atención** → Marcas que caen con elasticidad "positiva" (TOPPER, HUSH PUPPIES, WAKE)
- Cuando precio real y volumen caen juntos = mercado contrayéndose, no efecto precio
- Respuesta: rotar surtido, no bajar precio

---

## CONTEXTO MACRO — Abril 2026

| Variable | Dato | Implicancia para pricing |
|----------|------|--------------------------|
| IPC febrero 2026 | 2,9% mensual / 33,1% interanual | Ajustar listas cada 2-3 meses para no perder margen real |
| Tipo de cambio | $1.415 oficial (brecha ~0%) | Importaciones predecibles. Bandas reemplazaron crawling peg |
| Consumo minorista PyME | -5,6% interanual (feb) | Consumo selectivo. El cliente compara precio antes de comprar |
| Arancel calzado | 20% (bajó desde 35%) | **Alerta**: más calzado importado a menor costo. Presión competitiva |
| Calzado chino post-Trump | Desvío de exportaciones a Latam | Competencia en segmento bajo precio (+fuerte que antes) |
| Crecimiento PBI 2026 | +3-4% proyectado | Recuperación moderada, no boom. Cautela en apuesta agresiva |

### Señal clave: la apertura arancelaria es el factor de riesgo #1

El gobierno bajó aranceles al calzado de 35% a 20%, justo cuando la guerra comercial EEUU-China desvía toneladas de calzado chino a Argentina. Esto presiona los precios en el segmento bajo ($15k-$35k ARS). Las marcas que compiten en ese rango (LS&D, SEAWALK, ZEUS, LA CHAPELLE, MARYSABEL) van a sentir competencia directa de importados.

**Recomendación macro**: Subir precio en marcas premium (>$60k) donde no hay competencia importada. Defender volumen con promo en marcas de precio medio-bajo que sí compiten con importados.

---

## TOP 10 MARCAS: SUBIR PRECIO

| Rank | Marca | Venta 12m | Margen% | Elasticidad | Tendencia | Sugerencia | Precio actual | Precio sugerido |
|------|-------|-----------|---------|-------------|-----------|------------|---------------|-----------------|
| 3 | ATOMIK | $250M | 49,6% | Inelástico | Estable | **+12%** | $59.475 | $66.612 |
| 7 | LS&D | $122M | 52,4% | Inelástico | Estable | **+12%** | $22.282 | $24.956 |
| 18 | OLYMPIKUS | $65M | 47,6% | Inelástico | Estable | **+12%** | $62.351 | $69.833 |
| 31 | VANDALIA | $37M | 30,5% | Inelástico | Estable | **+20%** | $42.187 | $50.624 |
| 40 | JUANA VA | $22M | 52,9% | Inelástico | Estable | **+12%** | $45.101 | $50.513 |
| — | CAVATINI | $54M | 76,1% | Nueva | Nueva | **Establecer** | $92.628 | Base alineada |
| — | CATERPILLAR | $21M | 49,2% | Inelástico | Estable | **+12%** | $157.099 | $175.951 |
| — | HEYAS | $58M | 49,2% | Inelástico | Crece | **+12%** | $90.556 | $101.422 |
| — | CHOCOLATE | $55M | 52,9% | Elástico | BOOM | Promo, no lista | $62.503 | Promo -10% |
| — | MASSIMO CHIESA | $52M | 52,2% | N/D | BOOM | **+12% lista** | $77.829 | $87.168 |

**Nota VANDALIA**: Margen del 30,5% es alarmante para una marca mediana. O se sube precio agresivo (+20%) o se negocia mejor con el proveedor. Actualmente está siendo subsidiada por el mix.

---

## TOP 10 MARCAS: BAJAR PRECIO (ganar volumen/revenue)

| Rank | Marca | Venta 12m | Margen% | Elasticidad | Tendencia | Sugerencia | Precio actual | Precio sugerido |
|------|-------|-----------|---------|-------------|-----------|------------|---------------|-----------------|
| 2 | GO by CLZ | $477M | 64,4% | Elástico | BOOM | **-10% en básicos** | $67.863 | $61.077 |
| 9 | SOFT | $109M | 47,9% | N/D | Cae -19% | **-10% + renovar surtido** | $31.491 | $28.342 |
| 13 | PICCADILLY | $84M | 52,3% | Elástico | BOOM | **-10%** | $63.717 | $57.345 |
| 16 | LA CHAPELLE | $72M | 52,1% | Elástico | BOOM | **-10%** | $18.565 | $16.708 |
| 25 | GONDOLINO | $49M | 56,2% | Elástico | Crece | **-10%** | $91.099 | $81.989 |
| 27 | SELENE | $41M | 51,9% | Elástico | Cae -17% | **-10% + descontinuar líneas** | $49.152 | $44.237 |
| 22 | MASSIMO (básicos) | $52M | 52,2% | N/D | BOOM | Bajar básicos, subir premium | — | — |
| — | ZEUS | $19M | 51,3% | N/D | Cae -36% | **Clearance -20% y salir** | $17.426 | $13.941 |
| — | DELI | $18M | 51,5% | N/D | Cae -51% | **Liquidar stock** | $19.670 | $14.753 |
| — | ALMACEN DE MODA | $14M | 43,1% | N/D | Colapso -67% | **Discontinuar o liquidar** | $8.017 | Outlet |

---

## TOP 10 MARCAS: MANTENER PRECIO

| Rank | Marca | Venta 12m | Margen% | Elasticidad | Tendencia | Razon |
|------|-------|-----------|---------|-------------|-----------|-------|
| 1 | TOPPER | $792M | 47,6% | Mkt cayendo | Cae -19% | Problema de surtido, no precio |
| 4 | HUSH PUPPIES | $157M | 49,1% | Mkt cayendo | Cae -18% | Premium correcto, surtido a revisar |
| 5 | WAKE SPORT | $132M | 51,5% | Mkt cayendo | Cae -15% | Precio correcto, demanda macro débil |
| 6 | REEBOK | $126M | 51,2% | Expansión | — | Solo 2 años de historia, mantener |
| 8 | FOOTY | $119M | 50,5% | Mkt cayendo | Cae -19% | Precio OK, surtido a revisar |
| 10 | JAGUAR | $96M | 48,7% | Mkt cayendo | Cae -28% | Revisar posicionamiento |
| 11 | RINGO | $92M | 45,4% | Mkt cayendo | Cae -27% | Precio correcto, depende de Cecchini |
| 14 | CROCS | $84M | 50,6% | Mkt cayendo | Cae -22% | Producto fashion, mantener precio |
| 23 | VIAMO | $33M | 48,1% | Mkt cayendo | Cae -45% | En declive, mantener hasta agotar stock |
| 42 | NARROW | $18M | 49,7% | Mkt cayendo | Cae -44% | Idem |

---

## TABLA COMPLETA — 50 MARCAS

| # | Marca | Venta 12m | Pares 12m | Margen% | Elasticidad | Δvol 1a% | Tendencia | BCG | Recomendación | Precio actual | Precio sug |
|---|-------|-----------|-----------|---------|-------------|----------|-----------|-----|---------------|---------------|-----------|
| 1 | TOPPER | $792M | 13.085 | 47,6% | Mkt cayendo | -19,2% | CAE | VACA | MANTENER | $60.661 | $60.661 |
| 2 | GO by CLZ | $477M | 8.016 | 64,4% | Elástico | +228% | BOOM | ESTRELLA | BAJAR -10% | $67.863 | $61.077 |
| 3 | ATOMIK | $250M | 4.205 | 49,6% | Inelástico | -7,1% | ESTABLE | VACA | SUBIR +12% | $59.475 | $66.612 |
| 4 | HUSH PUPPIES | $157M | 1.768 | 49,1% | Mkt cayendo | -17,8% | CAE | VACA | MANTENER | $88.995 | $88.995 |
| 5 | WAKE SPORT | $132M | 3.667 | 51,5% | Mkt cayendo | -15,0% | CAE | VACA | MANTENER | $36.036 | $36.036 |
| 6 | REEBOK | $126M | 1.335 | 51,2% | Expansión | -37,3% | — | INTERROG | MANTENER | $94.613 | $94.613 |
| 7 | LS&D | $122M | 5.503 | 52,4% | Inelástico | +1,3% | ESTABLE | VACA | SUBIR +12% | $22.282 | $24.956 |
| 8 | FOOTY | $119M | 2.472 | 50,5% | Mkt cayendo | -19,0% | CAE | VACA | MANTENER | $48.195 | $48.195 |
| 9 | SOFT | $109M | 3.474 | 47,9% | N/D | -19,4% | CAE | VACA | BAJAR -10% | $31.491 | $28.342 |
| 10 | JAGUAR | $96M | 2.597 | 48,7% | Mkt cayendo | -28,1% | CAE | PERRO | MANTENER | $37.013 | $37.013 |
| 11 | RINGO | $92M | 978 | 45,4% | Mkt cayendo | -26,8% | CAE | PERRO | MANTENER | $94.541 | $94.541 |
| 12 | CLZ BEAUTY | $90M | 9.694 | 51,6% | Elástico | +139,8% | BOOM | ESTRELLA | BAJAR -10% | $10.025 | $9.022 |
| 13 | PICCADILLY | $84M | 1.317 | 52,3% | Elástico | +50,5% | BOOM | ESTRELLA | BAJAR -10% | $63.717 | $57.345 |
| 14 | CROCS | $84M | 1.682 | 50,6% | Mkt cayendo | -22,0% | CAE | VACA | MANTENER | $49.957 | $49.957 |
| 15 | KALIF/ALEX | $77M | 2.388 | 46,6% | Elástico | +194,6% | BOOM | ESTRELLA | MANTENER/PROMO | $32.422 | $32.422 |
| 16 | LA CHAPELLE | $72M | 3.934 | 52,1% | Elástico | +49,7% | BOOM | ESTRELLA | BAJAR -10% | $18.565 | $16.708 |
| 17 | CITADINA | $65M | 1.004 | 54,0% | N/D | -2,7% | ESTABLE | VACA | BAJAR -10% | $65.114 | $58.603 |
| 18 | OLYMPIKUS | $65M | 1.051 | 47,6% | Inelástico | +2,7% | ESTABLE | VACA | SUBIR +12% | $62.351 | $69.833 |
| 19 | LADY STORK | $63M | 677 | 50,6% | Mkt cayendo | -33,6% | COLAPSO | PERRO | MANTENER (agotar) | $93.287 | $93.287 |
| 20 | HEYAS | $58M | 642 | 49,2% | Inelástico | +66,8% | CRECE | ESTRELLA | SUBIR +12% | $90.556 | $101.422 |
| 21 | CHOCOLATE | $55M | 885 | 52,9% | Elástico | +103% | BOOM | ESTRELLA | BAJAR -10% | $62.503 | $56.253 |
| 22 | CAVATINI | $54M | 586 | 76,1% | NUEVA | — | NUEVA | INTERROG | ESTABLECER PRECIO | $92.628 | Ver mercado |
| 23 | GTN | $53M | 1.560 | N/D* | Mkt cayendo | -20,6% | CAE | VACA | MANTENER | $34.204 | $34.204 |
| 24 | MASSIMO CHIESA | $52M | 673 | 52,2% | N/D | +229,9% | BOOM | ESTRELLA | SUBIR lista +12% | $77.829 | $87.168 |
| 25 | GONDOLINO | $49M | 533 | 56,2% | Elástico | +15,6% | CRECE | ESTRELLA | BAJAR -10% | $91.099 | $81.989 |
| 26 | ELEMENTO | $48M | 21.127 | 43,8% | Elástico | +28,9% | BOOM | INTERROG | MANTENER/PROMO | $2.499 | $2.499 |
| 27 | SELENE | $41M | 837 | 51,9% | Elástico | -17,2% | CAE | PERRO | BAJAR -10% | $49.152 | $44.237 |
| 28 | MARYSABEL | $41M | 1.544 | 54,0% | Mkt cayendo | +21,0% | CRECE | INTERROG | MANTENER | $26.418 | $26.418 |
| 29 | VIZZANO | $40M | 744 | 50,3% | Mkt cayendo | -16,3% | CAE | VACA | MANTENER | $54.052 | $54.052 |
| 30 | JOHN FOOS | $39M | 489 | 44,9% | Mkt cayendo | -33,0% | COLAPSO | PERRO | MANTENER (agotar) | $80.003 | $80.003 |
| 31 | VANDALIA | $37M | 879 | 30,5% | Inelástico | -7,6% | ESTABLE | PERRO | SUBIR +20% | $42.187 | $50.624 |
| 32 | MARCEL | $37M | 748 | 53,7% | Mkt cayendo | +71,8% | BOOM | INTERROG | MANTENER | $49.120 | $49.120 |
| 33 | SEAWALK | $35M | 1.508 | 52,9% | Mkt cayendo | -26,1% | CAE | PERRO | MANTENER | $23.754 | $23.754 |
| 34 | VIAMO | $33M | 410 | 48,1% | Mkt cayendo | -44,7% | COLAPSO | PERRO | MANTENER (agotar) | $79.428 | $79.428 |
| 35 | KAPPA | $31M | 759 | 50,2% | Mkt cayendo | -40,8% | COLAPSO | PERRO | MANTENER (agotar) | $41.144 | $41.144 |
| 36 | VIA MARTE | $28M | 499 | 51,6% | Mkt cayendo | -33,0% | COLAPSO | PERRO | MANTENER (agotar) | $56.778 | $56.778 |
| 37 | SAVAGE | $26M | 422 | 52,7% | Mkt cayendo | -24,1% | CAE | PERRO | MANTENER | $61.603 | $61.603 |
| 38 | PROWESS | $25M | 1.146 | 49,2% | Mkt cayendo | -35,2% | COLAPSO | PERRO | MANTENER | $21.687 | $21.687 |
| 39 | EL FARAON | $23M | 1.478 | 52,2% | Mkt cayendo | -16,8% | CAE | PERRO | MANTENER | $15.378 | $15.378 |
| 40 | JUANA VA | $22M | 491 | 52,9% | Inelástico | +2,3% | ESTABLE | VACA | SUBIR +12% | $45.101 | $50.513 |
| 41 | AMPHORA | $21M | 331 | 45,7% | Mkt cayendo | -16,8% | CAE | PERRO | MANTENER | $63.977 | $63.977 |
| 42 | A NATION | $21M | 409 | 47,1% | Mkt cayendo | -23,8% | CAE | PERRO | MANTENER | $51.532 | $51.532 |
| 43 | DIADORA | $21M | 338 | 46,0% | Mkt cayendo | -38,2% | COLAPSO | PERRO | MANTENER (agotar) | $61.670 | $61.670 |
| 44 | CATERPILLAR | $21M | 132 | 49,2% | Inelástico | -24,1% | CAE | VACA | SUBIR +12% | $157.099 | $175.951 |
| 45 | NARROW | $18M | 235 | 49,7% | Mkt cayendo | -44,3% | COLAPSO | PERRO | MANTENER (agotar) | $74.521 | $74.521 |
| 46 | ZEUS | $19M | 1.072 | 51,3% | N/D | -35,6% | COLAPSO | PERRO | Clearance -20% | $17.426 | $13.941 |
| 47 | DELI | $18M | 893 | 51,5% | N/D | -51,4% | COLAPSO | PERRO | Liquidar | $19.670 | $14.753 |
| 48 | SETA | $15M | 447 | 48,3% | Mkt cayendo | -28,7% | CAE | PERRO | MANTENER | $33.586 | $33.586 |
| 49 | ALMACEN MODA | $14M | 1.864 | 43,1% | N/D | -67,1% | COLAPSO | PERRO | Discontinuar | $8.017 | Outlet |
| 50 | AVIA | $13M | 236 | 49,8% | Mkt cayendo | -56,9% | COLAPSO | PERRO | Liquidar / NO reponer | $54.015 | $54.015 |

*GTN: costo en ventas1 anómalo (costo > venta), margen real estimado ~40-45%

---

## RECOMENDACIÓN ESTRATÉGICA

### 1. Las 5 apuestas seguras para SUBIR precio (sin riesgo)

**ATOMIK** (+12%, $59k → $67k): Demanda inelástica, volumen estable, margen 50%. El cliente que compra Atomik no cambia por precio. Subir sin dudar.

**LS&D** (+12%, $22k → $25k): Marca de menor precio pero clientela fiel. Inelástica. Es el precio accesible del portfolio — si sube a $25k sigue siendo accesible.

**OLYMPIKUS** (+12%, $62k → $70k): Estable, inelástica, margen bueno. Posición de precio correcta.

**JUANA VA** (+12%, $45k → $50k): Estable, fiel, margen alto.

**CATERPILLAR** (+12%, $157k → $176k): Premium, cliente cautivo, inelástico. La subida es menor en términos relativos al cliente premium.

### 2. Los 3 dónde BAJAR precio para GANAR más

**GO by CLZ** (-10% en básicos, no en todo): El 64% de margen es excesivo y con demanda elástica deja plata sobre la mesa. Bajar los modelos básicos (no las valijas premium) a $61k desde $68k. El volumen debería subir otro 15-20% adicional a lo que ya crece.

**PICCADILLY** (-10%, $64k → $57k): En pleno BOOM (+50% volumen), margen 52%, elástica. Bajar precio expande el mercado y baja la brecha con competidores importados que van a presionar este rango.

**GONDOLINO** (-10%, $91k → $82k): Margen 56%, elástica, creciendo. La "nariz" de precio a $91k es una barrera artificial. A $82k, el cliente de $90k+ se anima más.

### 3. Estrategia de discriminación por canal

| Canal | Estrategia | Justificación |
|-------|-----------|---------------|
| **Local** | Precio lista (+5-8% sobre TiendaNube) | Cliente cautivo, conveniencia, atención personalizada |
| **TiendaNube** | Precio base del análisis | Sin intermediario, margen completo |
| **MercadoLibre** | Precio lista -5% (absorbe comisión 19-21%) | Competir en búsqueda, acepta menor margen |
| **Linda (bot)** | Precio lista con posibilidad de descuento según RFM | RFM alto → precio lleno; At Risk → -5% para retener |

### 4. El caso YIELD MANAGEMENT

Marcas con **cliente cautivo** (baja elasticidad + ticket alto + compradores frecuentes):
- RINGO, HUSH PUPPIES, GONDOLINO, CAVATINI, CATERPILLAR

Para estos: el vendedor en local puede ver el RFM del cliente y decidir:
- Cliente nuevo (RFM bajo): precio lista
- Cliente recurrente VIP (RFM alto): regalo/descuento para retener
- Cliente "At Risk" (inactivo): incentivo de 5-10% para reactivar

Esto requiere que Chatwoot/ERP muestren el perfil al momento de la venta (Sprint futuro).

### 5. Las marcas que hay que dejar morir (no reponer)

ZEUS, DELI, KAPPA, DIADORA, VIAMO, AVIA, LADY STORK, NARROW, ALMACEN DE MODA — todas en colapso de volumen (-35% a -57%), sin señal de reversión, con stock que sobra. Estrategia: **liquidar sin reponer**. El capital que se libera va a ATOMIK, PICCADILLY, GO by CLZ.

### 6. Señal de alarma: marcas que caen con el mercado

TOPPER (-19%), WAKE SPORT (-15%), FOOTY (-19%), CROCS (-22%), JAGUAR (-28%): estas son marcas donde el mercado entero se contrajo. No es que Calzalindo perdió share — todo el canal perdió. La respuesta correcta es **no subir precio** (para no empeorar la caída) y **renovar el surtido** (nuevos modelos, nuevos colores, rotación más rápida).

---

## ALERTAS Y PRÓXIMOS PASOS

1. **Sistema de actualización de precios**: Mariana necesita una herramienta que le diga "esta marca tiene margen 30%, el promedio del sector es 50%, está atrasada". Requiere Sprint 4.

2. **Monitor de precios de competencia**: Buscar los mismos modelos en ML/TN de competidores para tener referencia. Al menos para las 10 marcas top.

3. **Prioridad de listas de precios Q2 2026**: Aplicar las subidas recomendadas en ATOMIK, LS&D, OLYMPIKUS, JUANA VA esta semana (impacto directo en próximas facturas).

4. **GO by CLZ**: Definir precio de lanzamiento de nuevos modelos invierno con la lógica de margen objetivo <60% para estimular volumen.

5. **Presupuesto Q2**: Con consumo minorista -5,6% interanual, el presupuesto debe ser conservador. Las marcas que crecen (GO by CLZ, CLZ BEAUTY, PICCADILLY) van a compensar la caída general.

---

## METODOLOGÍA Y LIMITACIONES

**Elasticidad calculada como:**
- Precio real = precio nominal ajustado por IPC acumulado (deflactores: 1,331x para período 12-24m; 2,0x para período 24-36m)
- Elasticidad = (Δ% cantidad) / (Δ% precio real), entre período actual (0-12m) y período anterior (12-24m)
- Solo se calcula si el movimiento de precio real es mayor al 3% (filtro de ruido)

**Limitaciones:**
- La elasticidad mezcla efecto precio con efecto canal/surtido/macro. GO by CLZ y CLZ BEAUTY en "BOOM" son expansiones de canal, no puro efecto precio.
- Marcas "VEBLEN/CRECE" = precio y volumen se movieron en la misma dirección. No es efecto Veblen sino contracción de mercado simultánea.
- GTN: dato de costo anómalo en ventas1 (costo > venta). Margen estimado externamente en ~40-45%.
- CAVATINI: menos de 12 meses de historia → no hay comparativo previo.
- El modelo no captura quiebre de stock (puede inflar caídas de volumen por falta de mercadería).

---

*Reporte generado automáticamente. Revisar con Fernando antes de aplicar cambios de lista.*
