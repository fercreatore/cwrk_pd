# Estructura de Base de Datos - Remitos de Compra

## Resumen

Crear un remito de compra (ingreso cod=7 o devolucion cod=36) requiere escribir en **7 tablas**
distribuidas en hasta **3 bases de datos** segun el destino (Calzalindo o H4).

## Bases de datos

| Base | Servidor | Rol |
|------|----------|-----|
| **msgestionC** | .112 | Base central. Tiene campo `empresa` en compras1/compras2 ('CALZALINDO' o 'H4'). NO tiene comprasr. |
| **msgestion01** | .112 | Base Calzalindo. NO tiene campo `empresa`. Alimenta `omicronvt.dbo.stock_por_codigo` via vista `stock_v`. |
| **msgestion03** | .112 | Base H4. NO tiene campo `empresa`. Alimenta `omicronvt.dbo.stock_por_codigo` via vista `stock_v`. |
| **omicronvt** | .111 | Base de reportes/vistas. `stock_por_codigo` es VIEW que lee de msgestion01.stock_v (UNION msgestion01+msgestion03). |

## Tablas afectadas por destino (INSERT directo, NO en vistas)

### Items destinados a Calzalindo (ABI) → escribir en msgestion01
1. `msgestion01.dbo.compras2` (cabecera)
2. `msgestion01.dbo.compras1` (renglones)
3. `msgestion01.dbo.comprasr` (extension remito - transporte/flete)
4. `msgestion01.dbo.movi_stock` (movimiento de stock)
5. `msgestion01.dbo.stock` (stock actual: serie YYMM + serie resumen ' ')
6. `msgestion01.dbo.pedico1_entregas` (vinculacion con pedido - cantidades entregadas)
7. `msgestion01.dbo.pedico1` (UPDATE campo cantidad_entregada / monto_entregado)

### Items destinados a H4 → escribir en msgestion03
1. `msgestion03.dbo.compras2` (cabecera)
2. `msgestion03.dbo.compras1` (renglones)
3. `msgestion03.dbo.comprasr` (extension remito)
4. `msgestion03.dbo.movi_stock` (movimiento de stock)
5. `msgestion03.dbo.stock` (stock actual: serie YYMM + serie resumen ' ')
6. `msgestion03.dbo.pedico1_entregas` (vinculacion con pedido)
7. `msgestion03.dbo.pedico1` (UPDATE campo cantidad_entregada / monto_entregado)

Las vistas en msgestionC reflejan automaticamente los datos de ambas bases.

## Tablas detalle

### compras2 (cabecera del comprobante)
- **PK**: empresa + codigo + letra + sucursal + numero + orden (msgestionC)
- **PK**: codigo + letra + sucursal + numero + orden (msgestion01/03, sin empresa)
- Campos clave: deposito, cuenta, denominacion, fecha_comprobante, concepto_gravado, monto_general, estado_stock='S', estado='V'

### compras1 (renglones/lineas)
- **PK**: empresa + codigo + letra + sucursal + numero + orden + renglon (msgestionC)
- **PK**: codigo + letra + sucursal + numero + orden + renglon (msgestion01/03)
- Campos clave: articulo, descripcion, precio, cantidad, deposito, operacion('+'/'-'), serie(YYMM)

### comprasr (extension remito - datos de transporte)
- **Solo en msgestion01 y msgestion03** (msgestionC tiene la tabla pero 0 registros)
- **PK**: codigo + letra + sucursal + numero + orden
- Campos usados: fecha_vencimiento=fecha remito, precio_financiado='S', sin_valor_declarado='N', direccion=del proveedor
- Casi todos los campos de transporte quedan en 0/vacio

### movi_stock (movimientos de stock - sistema compras)
- Un registro por articulo por comprobante
- Campos clave: deposito, articulo, fecha=GETDATE(), codigo_comprobante=tipo, letra_comprobante='R',
  sucursal_comprobante, numero_comprobante, orden, operacion('+'/'-'), cantidad, precio, cuenta,
  sistema=7, serie=YYMM, unidades=1, fecha_contable=fecha remito, fecha_proceso=GETDATE(), usuario(2 chars)
- **NOTA**: movi_stock es para compras (sistema=7). movistoc1/movistoc2 son para notas de ingreso/egreso interno.

### stock (stock actual)
- **PK**: deposito + articulo + serie
- Se actualizan 2 filas por articulo:
  - Fila con serie=YYMM: stock_actual += cantidad (ingreso) o -= cantidad (devolucion)
  - Fila resumen con serie=' ': idem
- Si no existe la fila, se inserta

## Vista stock_por_codigo (omicronvt)
- Es VIEW, no tabla - se calcula sola
- Definicion: SELECT deposito, articulo, SUM(stock_actual) FROM msgestion01.dbo.stock_v GROUP BY deposito, articulo
- stock_v es UNION de msgestion01.dbo.stock (CALZALINDO) + msgestion03.dbo.stock (H4)

## Numeracion
- sucursal = punto de venta del remito del proveedor
- numero = numero del remito del proveedor
- orden = auto-incrementa dentro del mismo sucursal+numero (para duplicados)
- renglon = secuencial dentro del comprobante (1, 2, 3...)
- serie = YYMM (ej: '2603' = marzo 2026)

## Codigos de comprobantes de compras (compras2.codigo)

| Codigo | Tipo | Afecta | Descripcion |
|--------|------|--------|-------------|
| **7** | Remito de Ingreso | Stock + Pedidos pendientes | Ingresa mercaderia. Suma stock, resta pendientes. |
| **36** | Remito de Devolucion | Stock + Pedidos pendientes | Devuelve mercaderia. Resta stock, suma pendientes. |
| **1** | Factura de Compra | Cuenta corriente (dinero) | Comprobante contable. NO afecta stock ni pedidos. |
| **3** | Nota de Credito | Cuenta corriente (dinero) | Comprobante contable. NO afecta stock ni pedidos. |

**Importante**: Los codigos 1 y 3 son movimientos de DINERO (cuenta corriente del proveedor).
Los codigos 7 y 36 son movimientos de MERCADERIA (stock fisico y descuento de pendientes de pedidos).

## Vistas en msgestionC (NO son tablas reales)

Las siguientes tablas en msgestionC son **VISTAS** (UNION de msgestion01 + msgestion03 con campo empresa derivado):
- `msgestionC.dbo.compras2` = VIEW: `'CALZALINDO' as empresa, * FROM msgestion01.dbo.compras2 UNION 'H4' as empresa, * FROM msgestion03.dbo.compras2`
- `msgestionC.dbo.compras1` = VIEW (idem patron)
- `msgestionC.dbo.movi_stock` = VIEW (idem patron)
- `msgestionC.dbo.stock` = VIEW (idem patron)
- `msgestionC.dbo.comprasr` = BASE TABLE (real, pero tiene 0 registros)

**Consecuencia**: NO se puede insertar en las vistas de msgestionC (error 4406 "derived or constant field").
Se inserta SOLO en la base real: msgestion01 (ABI) o msgestion03 (H4). Las vistas reflejan los datos automaticamente.

## Pedidos y cumplimiento

- Tablas de pedidos: `msgestionC.dbo.pedico2` (cabecera) y `msgestionC.dbo.pedico1` (lineas) — son tablas reales, NO vistas.
- **Vinculacion remito-pedido**: `pedico1_entregas` (tabla nativa del ERP en msgestion01 y msgestion03).
  - PK: codigo(8) + letra(X) + sucursal + numero + orden + renglon
  - Campos: articulo, cantidad, deposito, fecha_entrega
  - Al crear remito desde la web, se inserta un registro por articulo por base (ABI en msgestion01, H4 en msgestion03).
  - Tambien se actualiza `pedico1.cantidad_entregada` y `pedico1.monto_entregado` (acumuladores).
- **Pedidos duplicados**: Los pedidos existen identicos en CALZALINDO y H4. La vista filtra solo CALZALINDO para evitar doble conteo.
- Vista de cumplimiento: `omicronvt.dbo.v_pedidos_cumplimiento` usa `pedico1_entregas` (ambas bases) para calcular cant_recibida.
- Cache: `omicronvt.dbo.pedidos_cumplimiento_cache` — copia materializada de la vista, se refresca via SP `sp_sync_pedidos`.
- El SP se invoca desde la web (boton "Actualizar datos") y tambien despues de crear un remito.
- **Nombres**: CLZ fue renombrado a ABI en toda la interfaz web.

## Tablas que NO se tocan al crear remitos
- movistoc1/movistoc2: son para notas de ingreso/egreso interno (cod 87, 22)
- stock_online: vacia, no se usa
- movi_stock_entrada/salida: vacias, no se usan
- omicron_web_articulo_*: vacias, no se usan en msgestion01art
