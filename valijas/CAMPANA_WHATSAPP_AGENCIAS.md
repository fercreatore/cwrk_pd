# CAMPANA WHATSAPP — Venta a Agencias de Viaje + Grupos
# Fecha: 19 marzo 2026
# Objetivo: Conseguir 15-20 agencias revendedoras en 2 semanas

---

## PRECIOS ACTUALIZADOS (web calzalindo.com.ar)

| Producto | Lista | Transfer (-20%) | 6 cuotas s/i |
|----------|-------|-----------------|--------------|
| Set x3 GO (18"+19"+21") | $162.499 | $129.999 | 6x $27.083 |
| Cabina 19" individual | $74.999 | $59.999 | 6x $12.499 |
| Mediana 21" individual | $87.499 | $69.999 | 6x $14.583 |
| Carry On 18" individual | $58.749 | $46.999 | 6x $9.791 |

**Costo por set: $45.000**
**Margen bruto por set: $84.999 (transfer) a $117.499 (lista)**

---

## TEMPLATE WHATSAPP (para Meta — primer contacto)

Nombre: `propuesta_agencias_valijas`

```
Hola {{1}}! Soy Fernando de Calzalindo, 35 anios en el negocio. Importamos sets de 3 valijas rigidas marca GO ideales para pasajeros y grupos. Tenemos dos modelos de trabajo para agencias. Te cuento?
```

Footer: `Calzalindo - Venado Tuerto`
Botones: `Si, contame` / `No, gracias`

---

## PASO 1: ARMAR LA LISTA DE AGENCIAS (LISTO — 36 agencias en Excel)

Archivo: `LISTA_AGENCIAS_PROSPECCION.xlsx`
- 8 ALTA prioridad (estudiantil)
- 18 MEDIA prioridad
- 10 NORMAL prioridad

---

## PASO 2: CUANDO RESPONDEN — PRESENTAR LAS 2 OPCIONES

### Mensaje con las dos propuestas:

```
Genial! Te cuento las dos formas de trabajar juntos:

OPCION A — COMISION POR REFERIDO
- Compartis un link o codigo con tus pasajeros
- Ellos compran directo en nuestra web con descuento exclusivo
- Por cada set vendido te transferimos $20.000 de comision
- Nosotros nos encargamos de TODO: atencion, envio, postventa
- Vos no pones plata ni stockeas nada

Ejemplo: un grupo de 30 pasajeros, 10 compran = $200.000 para vos

OPCION B — PRECIO MAYORISTA
- Compras los sets a $95.000 c/u (transferencia)
- Los revendes al precio que quieras
- Margen de $35.000 a $67.000 por set segun tu precio
- Envio gratis desde Venado Tuerto
- Pedido minimo: 5 sets

Ejemplo: compras 10 sets x $95.000 = $950.000
Revendes a $160.000 c/u = $1.600.000
Ganancia: $650.000

Cual te sirve mas? Muchas agencias arrancan con la A para probar y despues pasan a la B cuando ven que se vende.
```

---

## CODIGOS DE DESCUENTO — OPCION A

Para cada agencia se crea un codigo unico en TiendaNube:

| Agencia | Codigo | Descuento | Precio final set | Comision |
|---------|--------|-----------|------------------|----------|
| Travel Rock | TRAVELROCK | 5% | $154.374 / $123.499 transf | $20.000 |
| Flecha | FLECHA | 5% | $154.374 / $123.499 transf | $20.000 |
| (etc) | (NOMBRE) | 5% | $154.374 / $123.499 transf | $20.000 |

**Logica del descuento:**
- El pasajero paga 5% menos que precio web = incentivo real para comprar por la agencia
- Comision $20.000 sale del margen (costo $45.000, venta transfer $123.499 = margen $78.499)
- Margen neto despues de comision: $58.499 por set
- El codigo nos permite trackear que agencia genero la venta

### Como crear codigos en TiendaNube:
1. Admin > Marketing > Cupones de descuento
2. Crear cupon con nombre de la agencia (ej: TRAVELROCK)
3. Tipo: porcentaje, 5%
4. Sin limite de usos
5. Valido para categoria "Valijas"

---

## PRECIOS OPCION B — MAYORISTA

| Cantidad | Precio x set | Precio total | Margen vs reventa $160k |
|----------|-------------|--------------|------------------------|
| 5 sets | $95.000 | $475.000 | $325.000 (68%) |
| 10 sets | $90.000 | $900.000 | $700.000 (78%) |
| 20 sets | $85.000 | $1.700.000 | $1.500.000 (88%) |

---

## PASO 3: FOTOS Y MATERIAL

### Mandar en este orden (5 mensajes separados):

**Mensaje 1 — Foto set Negro** (archivo: 7981DFA3)
```
Set Negro - el mas vendido
```

**Mensaje 2 — Foto set Rosa Gold** (archivo: BE724906)
```
Set Rosa Gold - el favorito de las mujeres
```

**Mensaje 3 — Foto set Rosa** (archivo: 442EA850)
```
Set Rosa - ideal para jovenes
```

**Mensaje 4 — Foto set Rojo** (archivo: 31A6CE80)
```
Set Rojo - el mas elegante
```

**Mensaje 5 — Detalle interior** (archivo: 195644CA)
```
Interior forrado con correas de sujecion y bolsillo. Cierre combinacion numerica.
```

---

## PASO 4: MENSAJE LISTO PARA QUE LA AGENCIA COPIE (Opcion A)

```
Aca te dejo el mensaje listo para que copies y pegues en tu grupo:

---

PROMO EXCLUSIVA PARA EL GRUPO

Set de 3 Valijas Rigidas GO
18" (carry on low cost) + 19" (cabina estandar) + 21" (mediana)

8 ruedas 360 | ABS rigido | Cierre combinacion
Super livianas | Interior forrado

Colores: Negro, Rosa, Rojo, Rosa Gold

PRECIO EXCLUSIVO CON CODIGO: 5% OFF
$154.374 en 6 cuotas sin interes
$123.499 pagando por transferencia

ENVIO GRATIS a todo el pais

Compra aca: calzalindo.com.ar
Usa el codigo: [CODIGO_AGENCIA]

---

Solo tenes que cambiar [CODIGO_AGENCIA] por el codigo que te asignamos.
Adjunta las 4 fotos de los sets que te mandamos.
```

---

## PASO 5: SEGUIMIENTO (MUY IMPORTANTE)

### Dia 1 (hoy): Mandar template a 36 agencias via n8n
### Dia 2: A los que no respondieron, mandar:
```
Hola! Te escribi ayer por el tema de las valijas para tus pasajeros. Viste el mensaje? Si te interesa te mando toda la info. Si no, ningun drama!
```

### Dia 4: A los que respondieron pero no avanzaron:
```
Hola! Como va? Pudiste ver las opciones de trabajo? Si necesitas que te arme algo mas personalizado me avisas. Ya tenemos varias agencias trabajando con nosotros.
```

### Dia 7: A TODOS (interesados + no respondieron):
```
Hola! Te cuento que ya tenemos agencias compartiendo las valijas GO y se estan vendiendo muy bien. Si queres sumarte todavia tenemos stock. Avisame!
```
**(Esto genera FOMO)**

---

## PASO 6: ESCALAR CON REFERIDOS

Cuando una agencia venda 5+ sets:

```
Hola! Ya vendiste [X] sets, genial! Te propongo algo: si me recomendas a otra agencia o coordinador de viaje que quiera sumarse, te doy $5.000 extra por cada uno que se sume y venda.
```

---

## NUMEROS OBJETIVO

| Semana | Agencias contactadas | Agencias activas | Sets vendidos | Facturacion |
|--------|---------------------|-------------------|---------------|-------------|
| Sem 1 | 36 | 5-8 | 10-15 | $1.6M - $2.4M |
| Sem 2 | 30 nuevas | 10-15 | 25-35 | $4M - $5.6M |
| Sem 3 | 20 nuevas + referidos | 15-20 | 40-60 | $6.4M - $9.6M |
| Sem 4 | Referidos | 20+ | 60-80 | $9.6M - $12.8M |

**Meta 30 dias: 135-190 sets = $21M - $30M facturados**

---

## TIPS CLAVE

1. **Mandar entre 10:00 y 12:00** (horario laboral, las agencias estan activas)
2. **No mandar mas de 15 mensajes por batch** (configurado en WF4 de n8n)
3. **Si preguntan si es marca conocida:** "GO es nuestra marca propia importada. Misma fabrica que produce para marcas de primer nivel. Sin el markup del marketing."
4. **Si piden muestra:** "Te mando fotos y video. Si queres ver en persona, estamos en Venado Tuerto o te enviamos 1 set y si no te convence devolvemos la plata."
5. **Si piden mas descuento en Opcion B:** Bajar a $85.000/set solo para 20+ unidades.
6. **NUNCA bajar de $85.000/set** — ese es el piso mayorista.

---

## MENSAJES PARA SITUACIONES ESPECIFICAS

### Si preguntan por garantia:
```
Tienen 6 meses de garantia. Si llega algo fallado lo cambiamos sin costo. Somos Calzalindo, 35 anios en el negocio. No desaparecemos.
```

### Si preguntan si pasa por cabina low cost:
```
Si! La 18" esta disenada para low cost (Flybondi/JetSmart). Medidas: 45x35x25cm, entra perfecto. La 19" va para cabina estandar (Aerolineas/LATAM).
```

### Si preguntan el peso:
```
La 18" pesa 2.1kg, la 19" pesa 2.8kg y la 21" pesa 3.2kg. Super livianas.
```

### Si preguntan por factura:
```
Si, hacemos factura A o B segun necesites. Somos empresa formal, 35 anios.
```

### Si piden precio por unidad (no set):
```
El mejor precio es en set de 3. Sueltas tenemos en la web: 18" a $58.749, 19" a $74.999, 21" a $87.499. El set sale mucho mas conveniente.
```
