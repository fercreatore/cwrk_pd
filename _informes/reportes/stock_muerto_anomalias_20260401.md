# Stock Muerto y Anomalias de Datos
## Reporte Ejecutivo — 1 de abril de 2026

---

## Resumen para la direccion

Se identificaron **50 articulos con stock > 5 unidades y CERO ventas en 12 meses**. El capital bruto reportado supera los $4.000M, pero **dos anomalias de datos distorsionan completamente las cifras**. Corregidas las anomalias, el stock muerto real ronda los **$20-25M**, concentrado en GO CZL, LANACUER y HUSH PUPPIES.

La anomalia principal (art. 306188) explica por si sola la cobertura absurda de 11.1x en Deportes. Sin ese articulo, Deportes baja a una cobertura razonable de ~1x.

---

## 1. Anomalias de datos detectadas

### ANOMALIA CRITICA: Articulo 306188 (marca 822, subrubro 10)

| Campo | Valor | Diagnostico |
|-------|-------|-------------|
| precio_costo | $6,976,966.30 /unidad | ERROR. Probablemente se cargo el precio total de un lote como precio unitario |
| stock | 563 unidades | |
| Capital reportado | $3,930,125,117 | Ficticio |
| Ventas 12m | 0 | |

**Impacto**: Este unico articulo infla el stock de Deportes en $3.930M. Al eliminarlo del calculo, el stock de Deportes pasa de $4.622M a ~$692M, y la cobertura baja de 11.1x a ~1.7x, que es alta pero no absurda.

**Hipotesis del error**: El precio_costo fue cargado como precio total de una compra (ej: 563 uds x $12.390 = $6.975.570, cercano al valor registrado). El precio unitario real seria ~$12.390.

**Accion inmediata**: Verificar la factura de compra original y corregir `precio_costo` en la tabla de articulos.

### ANOMALIA CONFIRMADA: GTN (marca 104) — 5 articulos

| Campo | Valor | Diagnostico |
|-------|-------|-------------|
| precio_costo | $2,739,000 /unidad | ERROR. Mismo patron que 306188 |
| stock | 6-10 uds c/u | |
| Capital reportado | ~$101M | Ficticio |
| Ventas 12m | 0 | |
| Antecedente | Margen -238% en matriz BCG | Confirma precio_costo erroneo |

**Correlacion con BCG**: GTN aparecio con margen negativo imposible (-238%) en el analisis de mix de productos. Ambas anomalias tienen la misma causa raiz: `precio_costo` inflado, probablemente cargado como precio total del lote en vez de precio unitario.

**Accion inmediata**: Revisar los 5 articulos GTN con precio > $2M. Dividir por la cantidad de la factura original para obtener el unitario real.

---

## 2. Stock muerto REAL (anomalias excluidas)

### Cuantificacion

Con las anomalias excluidas, el stock muerto real de los ~45 articulos restantes suma aproximadamente:

| Concepto | Capital estimado |
|----------|-----------------|
| GO CZL (marca 17) — ~10 articulos | $5.8M |
| LANACUER (marca 669) — 3 articulos | $2.0M |
| HUSH PUPPIES (marca 765) — 6 articulos | $1.8M |
| TOPPER (marca 314) — 3 articulos | $1.2M |
| Marca 794 — 2 articulos | $934K |
| DISTRINANDO (marca 656) — 1 articulo | $379K |
| Marca 639 — 2 articulos | $720K |
| Marca 671 — 1 articulo | $370K |
| LESEDIFE (marca 42) — 1 articulo | $395K |
| Marca 759 — 1 articulo | $380K |
| Resto (~25 articulos, $250-330K c/u) | ~$7.2M |
| **TOTAL STOCK MUERTO REAL** | **~$21.2M** |

### Concentracion por marca

```
GO CZL (17)     ████████████████████████████  27%  ($5.8M)
Resto (<$330K)  ██████████████████████████████████  34%  ($7.2M)
LANACUER (669)  █████████  10%  ($2.0M)
HUSH PUPPIES    ████████  9%  ($1.8M)
TOPPER (314)    ██████  6%  ($1.2M)
Marca 794       ████  4%  ($934K)
Otros           ████████  10%  ($3.3M)
```

---

## 3. Diagnostico por marca

### GO CZL (marca 17) — $5.8M inmovilizados, 10+ articulos

- **Margen reportado**: 66% (dato de la matriz BCG)
- **Precio_costo**: $8.500 a $60.000 (rango razonable para calzado)
- **Stock**: 10 a 60 unidades por articulo

**Pregunta clave**: Estos articulos tienen 66% de margen y CERO ventas. Hay dos explicaciones posibles:
1. **Articulos nuevos sin exhibir**: Ingresaron al stock pero nunca se pusieron en gondola/vidriera. Si es asi, no es stock muerto sino stock sin rotacion por falta de exhibicion.
2. **Modelos discontinuados**: Quedaron en deposito sin reposicion ni exhibicion.

**Accion**: Verificar fecha de ultima compra. Si la compra fue reciente (ultimos 3 meses), son articulos nuevos que necesitan exhibicion urgente. Si la compra es antigua (> 6 meses), son candidatos a liquidacion.

### LANACUER (marca 669) — $2.0M, 3 articulos

- Articulos 362111, 362112, 362122
- Stock: 24-48 unidades
- Precios: $14.000-$25.000

Marca de cuero/marroquineria. Tres articulos con stock significativo y cero movimiento. Candidatos directos a liquidacion o devolucion al proveedor.

### HUSH PUPPIES (marca 765) — $1.8M, 6 articulos

- 12 unidades cada uno
- Precios: $21.000-$31.000

Marca reconocida con buen margen historico. Seis articulos parados sugieren un problema de talles o modelos fuera de temporada. Verificar si son talles extremos (muy chicos o muy grandes) que no rotan en Venado Tuerto.

### TOPPER (marca 314) — $1.2M, 3 articulos

- Articulos 359116, 359117, 208464
- 208464 tiene precio $31.618 y 12 unidades — puede ser un modelo viejo

TOPPER rota bien en general (es proveedor activo con pedidos recientes). Estos 3 articulos son probablemente modelos discontinuados de temporadas anteriores.

---

## 4. Impacto en indicadores por industria (corregido)

### Antes y despues de corregir anomalias

| Industria | Stock reportado | Stock corregido | Venta OI25 | Cobertura real |
|-----------|----------------|----------------|------------|----------------|
| Deportes | $4,622M | ~$692M* | $416M | 1.7x |
| Zapateria | $398M | $398M | $284M | 1.4x |
| Mixto | $215M | $215M | $238M | 0.9x |
| Marroquineria | $125M | $125M | $85M | 1.5x |
| Indumentaria | $61M | $61M | $84M | 0.7x |
| Cosmetica | $49M | $49M | $26M | 1.9x |

*Correccion: se restan $3.930M del art 306188. Si GTN tambien es Deportes, restar ~$101M adicionales.

**Conclusion**: Deportes NO tiene un problema de sobrestock catastrofico. El indicador de 11.1x era un artefacto del error de datos en art 306188. La cobertura real de 1.7x es alta pero manejable, especialmente considerando que incluye stock de temporada.

Las industrias con cobertura preocupante real son:
- **Cosmetica** (1.9x): stock para casi 2 temporadas con $26M de venta
- **Deportes** (1.7x): alta pero explicable por estacionalidad
- **Marroquineria** (1.5x): moderadamente alta

---

## 5. Plan de accion priorizado

### URGENTE (esta semana)

| # | Accion | Responsable | Impacto |
|---|--------|-------------|---------|
| 1 | **Corregir precio_costo art 306188** | Sistemas/Mati | Elimina $3.930M ficticios de reportes |
| 2 | **Corregir precio_costo 5 arts GTN** | Sistemas/Mati | Elimina $101M ficticios + arregla margen BCG |
| 3 | **Auditar precio_costo > $500.000** | Sistemas | Detectar otros articulos con el mismo error |

### CORTO PLAZO (proximas 2 semanas)

| # | Accion | Detalle |
|---|--------|---------|
| 4 | **Verificar GO CZL en deposito** | Determinar si los 10 articulos estan en gondola o guardados. Si no estan exhibidos, sacarlos YA |
| 5 | **Negociar devolucion LANACUER** | 3 articulos, $2M. Contactar proveedor para cambio o nota de credito |
| 6 | **Analizar talles HUSH PUPPIES** | Si son talles extremos, reubicar a sucursal con demanda o liquidar online |
| 7 | **Separar TOPPER discontinuados** | Los 3 articulos muertos van a rack de liquidacion |

### MEDIANO PLAZO (abril-mayo)

| # | Accion | Detalle |
|---|--------|---------|
| 8 | **Liquidacion agresiva stock muerto** | Meta: recuperar 40-60% del costo ($8-12M de los $21M) |
| 9 | **Implementar alerta automatica** | Query semanal: articulos con stock > 5 y 0 ventas en 90 dias |
| 10 | **Revaluo masivo de costos** | Correr script de deteccion de precio_costo anomalo en toda la base |

### Criterios de priorizacion para liquidacion

Liquidar primero los articulos que cumplan MAS de estos criterios:
1. **Antiguedad > 12 meses** sin venta (ya confirmado para los 50)
2. **Marca sin rotacion general** (no solo el articulo, toda la marca esta parada)
3. **Capital > $500K** por articulo
4. **Sin margen alto** que justifique esperar (excluir GO CZL si son nuevos)
5. **Talles completos** que permitan venta como lote

---

## 6. Recomendaciones estructurales

### Limpieza de datos
- **Regla de validacion**: Ningun `precio_costo` puede exceder $500.000 por unidad sin alerta. Implementar CHECK constraint o trigger en la tabla de articulos.
- **Auditoria trimestral**: Correr query de deteccion de anomalias (precio_costo > percentil 99) cada 3 meses.
- **Precio_costo vs precio_venta**: Si precio_costo > precio_venta, marcar automaticamente para revision.

### Gestion de stock muerto
- **Definicion operativa**: Articulo con stock > 3 y 0 ventas en 180 dias = candidato a liquidacion.
- **Rack de liquidacion permanente**: Espacio fisico dedicado en local con descuento visible (30-50% off).
- **Canal online para liquidacion**: Publicar stock muerto en ML/TiendaNube con descuento agresivo. El costo de oportunidad de tener $21M parados supera ampliamente el margen perdido por liquidar a descuento.

### Proceso de compras
- **Antes de hacer un pedido nuevo**, verificar que no haya stock muerto de la misma marca/subrubro.
- **Compras iniciales conservadoras**: Para marcas nuevas o articulos sin historial, pedir cantidades minimas y reponer solo si hay traccion.

---

## Anexo: Resumen numerico

```
Capital total reportado en stock muerto:     $4,031M (DISTORSIONADO)
  - Anomalia art 306188:                    -$3,930M (error datos)
  - Anomalia GTN (5 arts):                    -$101M (error datos)
  - STOCK MUERTO REAL:                        ~$21.2M

Distribucion del stock muerto real:
  - Top 3 marcas (GO CZL + LANACUER + HP):    $9.6M  (45%)
  - Resto (~35 articulos):                    $11.6M  (55%)

Recupero estimado por liquidacion:
  - Escenario conservador (40% costo):         $8.5M
  - Escenario optimista (60% costo):          $12.7M
```

---

*Generado el 1 de abril de 2026. Datos basados en stock actual y ventas ultimos 12 meses.*
*Proximo paso inmediato: corregir precio_costo de art 306188 y 5 arts GTN.*
