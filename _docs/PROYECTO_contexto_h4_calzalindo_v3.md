# PROYECTO H4 / CALZALINDO - Contexto Unificado (v3)

> Actualizado: 5 de marzo de 2026
> Fuente: diagrama ER + exploración de réplicas + SP y queries existentes + desarrollo web app

---

## 1. NEGOCIO

- Empresa de calzado, marroquinería, indumentaria, cosmética y deportes
- Dos razones sociales sobre el mismo negocio físico:
  - **CALZALINDO**: venta omitida (informal/off-books) — renombrada a **ABI** en interfaces web
  - **H4**: todo facturado (formal)
- Las compras se registran en ambas empresas con artículos diferentes pero misma mercadería física
- **Los pedidos se duplican** en ambas empresas (mismos proveedores, mismos artículos). Filtrar por `empresa = 'CALZALINDO'` para evitar doble conteo.
- Ubicación: Venado Tuerto, Santa Fe, Argentina

---

## 2. ARQUITECTURA DE SERVIDORES

### 192.168.2.111 — Servidor Web / Producción

- **SQL Server 2012 RTM** (11.0.2100.60), compatibility_level = 110
- ⚠️ **NO soporta TRY_CAST** (requiere SP1/11.0.3000+). Usar ISNUMERIC + CAST.
- msgestion01, msgestion03, msgestionC (compat level 90), msgestion01art (compat level 90), omicronvt (compat level 110) — todas en este servidor
- **Web2py 2.24.1** sobre Python 2.7.14, Rocket server en puerto 8000
- App: `calzalindo_informes` — dashboard de pedidos, remitos, recupero, calce financiero

### 192.168.2.112 — Réplica / Metabase

- Mismas bases replicadas (msgestion01, msgestion03, msgestionC, msgestion01art, omicronvt)
- **MCP sql-replica** apunta aquí (a msgestionC, accede a otras bases cross-database)
- Réplicas Metabase: msgestionC (ID 12), msgestion01art (ID 13), omicronvt (ID 14), msgestion01 (ID 11)
- ⚠️ Los cambios en .112 NO afectan la web (que lee de .111). Para que tomen efecto hay que aplicar en .111.

### Bases de datos

| Base | Contenido | Nota |
|------|-----------|------|
| **msgestionC** | Base operativa consolidada. ~1200 tablas. Muchas son **VISTAS** que hacen UNION de msgestion01 + msgestion03 con campo `empresa` derivado. | NO insertar en vistas (error 4406) |
| **msgestion01** | Base real de CALZALINDO. Sin campo `empresa`. | Insertar aquí para ABI |
| **msgestion03** | Base real de H4. Sin campo `empresa`. | Insertar aquí para H4 |
| **msgestion01art** | Maestro de artículos compartido. articulo (252 campos), marcas, subrubros, rubros, lineas. | Compartido entre ambas empresas |
| **omicronvt** | Base analítica/auxiliar. Vistas, caches, tablas t_*, stock histórico. ~69 tablas. | Web2py lee de aquí para dashboards |

### Convenciones de acceso
- **Web2py (producción)**: `db_omicronvt` → omicronvt en .111
- **MCP sql-replica**: → msgestionC en .112 (acceso cross-database a todas las bases)
- **Consultas Metabase**: usar réplicas en .112
- **DDL (ALTER VIEW, CREATE SP)**: ejecutar en .111 via SSMS

---

## 3. APP WEB — calzalindo_informes

### Estructura de archivos (deploy en .111)

```
calzalindo_informes_DEPLOY/
├── controllers/
│   ├── reportes.py          # Pedidos, remitos, recupero, negociación (~1780 líneas)
│   ├── calce_financiero.py  # Calce financiero
│   ├── agrupadores.py       # Agrupadores
│   └── admin_roles.py       # Admin roles
├── models/
│   └── db_access.py         # Control de acceso por roles
├── views/
│   └── reportes/
│       ├── pedidos.html          # Dashboard KPIs + tabla proveedores
│       ├── pedidos_detalle.html  # Detalle por proveedor + UI remitos
│       ├── recupero.html
│       └── ...
├── sql/
│   ├── agregar_columnas_vista.sql  # Vista + cache + SP de pedidos
│   └── diagnostico_vista.sql       # Script diagnóstico para .111
└── deploy.sh                       # Deploy via SMB
```

### Deploy
```bash
bash ~/Downloads/calzalindo_informes_DEPLOY/deploy.sh
```

### Endpoints principales (reportes.py)

| Función | Ruta | Descripción |
|---------|------|-------------|
| `pedidos()` | /reportes/pedidos | Dashboard. Lee `pedidos_cumplimiento_cache`. Agrega por proveedor en Python. KPIs, tabla proveedores, vencidas, antigüedad. |
| `pedidos_detalle()` | /reportes/pedidos_detalle?proveedor=X | Drill-down por proveedor. Detalle por línea de pedido. |
| `remito_crear()` | /reportes/remito_crear (POST) | Crea remito. Inserta en compras2, compras1, comprasr, movi_stock, stock (por base), pedico1_entregas, y actualiza pedico1. Luego llama sp_sync_pedidos. |
| `sync_pedidos()` | /reportes/sync_pedidos (AJAX) | Ejecuta `EXEC omicronvt.dbo.sp_sync_pedidos`. Botón "Actualizar datos". |
| `recupero()` | /reportes/recupero | Recupero de inversión |
| `negociacion_plazos()` | /reportes/negociacion_plazos | Negociación de plazos de pago |

### Roles de acceso

| Rol | Acceso |
|-----|--------|
| `informes_admin` | Todo + gestionar usuarios |
| `informes_gerencia` | Calce, Negociación, Recupero Hist/Live, Pedidos |
| `informes_compras` | Pedidos, Recupero Live, Agrupadores, Remitos |

### Roles heredados del sistema viejo
- `admins` / `ges_admin` → `informes_admin`
- `finanzas` / `gestion` → `informes_gerencia`
- `ges_pagos` → `informes_compras`

---

## 4. SISTEMA DE PEDIDOS Y CUMPLIMIENTO

### Vista: `omicronvt.dbo.v_pedidos_cumplimiento`

Cruza pedidos (pedico2/pedico1) con entregas (pedico1_entregas de ambas bases) para calcular cumplimiento.

**Columnas de la vista actual:**
cod_proveedor, proveedor, fecha_pedido, tipo_comprobante, letra, sucursal, numero, orden, renglon, articulo, descripcion, marca, industria, cod_rubro, rubro_desc, cod_subrubro, subrubro_desc, cod_grupo, grupo_desc, cod_linea, linea_desc, cant_pedida, cant_recibida, cant_pendiente, estado_cumplimiento (COMPLETO/PARCIAL/PENDIENTE), pct_cumplido, precio_unitario, monto_pedido, monto_pendiente, dias_desde_pedido, fecha_entrega, alerta_vencimiento (VENCIDO/NULL), primera_recepcion, ultima_recepcion, estado_pedido, estado_linea

**Características clave:**
- Filtra `WHERE p2.empresa = 'CALZALINDO'` (evita duplicados)
- Ya NO tiene columna `empresa` en el output
- Usa `pedico1_entregas` (UNION msgestion01 + msgestion03) para cant_recibida, vinculado por sucursal+numero+orden+renglon
- Usa ISNUMERIC + CAST para a.grupo (no TRY_CAST — incompatible con SQL Server 2012 RTM)
- LEFT JOINs a rubros, grupos, lineas, marcas (todas vistas en msgestionC)

### Cache: `omicronvt.dbo.pedidos_cumplimiento_cache`

Copia materializada de la vista. El controller lee de la cache, no de la vista directamente.

- Se refresca via `EXEC omicronvt.dbo.sp_sync_pedidos`
- Índices: IX_cache_proveedor, IX_cache_estado, IX_cache_alerta, IX_cache_industria, IX_cache_fecha, IX_cache_rubro, IX_cache_linea
- ~560 filas (con filtro CALZALINDO), ~69 pedidos únicos

### Tablas de pedidos

**pedico2** (cabecera) — vistas en msgestionC, tablas reales en msgestion01/03
- PK: empresa + codigo(8) + letra(X) + sucursal + numero + orden
- Campos: cuenta (cod_proveedor), denominacion, fecha_comprobante, estado

**pedico1** (líneas) — vistas en msgestionC, tablas reales en msgestion01/03
- PK: empresa + codigo + letra + sucursal + numero + orden + renglon
- Campos: articulo, cantidad, precio, fecha_entrega, estado, cantidad_entregada, monto_entregado

**pedico1_entregas** (entregas contra pedidos) — tablas reales en msgestion01 y msgestion03
- PK: codigo(8) + letra(X) + sucursal + numero + orden + renglon
- Campos: articulo, cantidad, deposito, fecha_entrega
- Se inserta al crear remito desde web
- ⚠️ Históricamente vacía para pedidos nuevos (el ERP desktop no la usaba). Se llena solo desde la web app.

---

## 5. SISTEMA DE REMITOS DE COMPRA

### Crear remito = escribir en 7 tablas por base

Para cada destino (ABI → msgestion01, H4 → msgestion03):

1. `compras2` (cabecera): codigo=7 ingreso, 36 devolución
2. `compras1` (renglones): artículo, cantidad, precio
3. `comprasr` (extensión remito): datos transporte/flete
4. `movi_stock` (movimiento stock): sistema=7
5. `stock` (stock actual): 2 filas por artículo (serie YYMM + serie resumen ' ')
6. `pedico1_entregas` (vinculación pedido)
7. `pedico1` (UPDATE cantidad_entregada y monto_entregado)

### Códigos de comprobantes de compras

| Código | Tipo | Afecta |
|--------|------|--------|
| 7 | Remito de Ingreso | Stock + Pedidos pendientes |
| 36 | Remito de Devolución | Stock + Pedidos pendientes |
| 1 | Factura de Compra | Cuenta corriente (dinero) |
| 3 | Nota de Crédito | Cuenta corriente (dinero) |

### Vistas en msgestionC (NO son tablas reales)

compras2, compras1, movi_stock, stock → son VISTAS (UNION msgestion01 + msgestion03 con empresa derivada). **NO se puede INSERT** (error 4406). Insertar en la base real correspondiente.

comprasr → es BASE TABLE en msgestionC pero tiene 0 registros. Insertar en msgestion01/03.

### Numeración de remitos
- sucursal = punto de venta del remito proveedor
- numero = número del remito proveedor
- orden = auto-incrementa para duplicados
- renglon = secuencial (1, 2, 3...)
- serie = YYMM (ej: '2603' = marzo 2026)

---

## 6. ORDENES DE PAGO (PENDIENTE)

Investigación realizada, implementación postponed. Las OPs (codigo_movimiento=14) tocan múltiples módulos:

| Tabla | Base | Módulo |
|-------|------|--------|
| `moviprov1` | msgestionC | CC Proveedores (63 cols). Campos: numero, cuenta, denominacion, fecha, codigo_movimiento, etc. |
| `moviprov2` | msgestionC | Vencimientos |
| `compras_pagos` | msgestionC | Medios de pago |
| `co_movact` | msgestionC | Contabilidad (63 cols) — la tabla que el usuario llama "movicoact" |
| `co_saldo` | msgestionC | Saldos contables |
| `cheques` / `saldos_d_caja` | msgestionC | Tesorería |

**Decisión**: demasiado complejo/riesgoso para web. Mantener creación de OPs en desktop ERP, solo consulta desde web.

---

## 7. TABLAS CLAVE — ESTRUCTURA

### articulo (msgestion01art, 252 campos)

PK: `codigo`. Campos relevantes:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| codigo | numeric | PK |
| codigo_barra | numeric | Código de barras |
| codigo_sinonimo | varchar(40) | Código alternativo. Últimos 2 dígitos = talle/número |
| descripcion_1 | varchar | Descripción principal |
| grupo | varchar(3) | Grupo del artículo (⚠️ es varchar, puede ser no numérico) |
| linea | numeric | FK → lineas.codigo (temporada) |
| marca | numeric | FK → marcas.codigo |
| rubro | numeric | FK → rubros.codigo |
| subrubro | numeric | FK → subrubro.codigo |
| precio_1 a precio_4 | decimal | Listas de precios |
| proveedor | varchar | Proveedor (texto, no FK numérica) |
| stock | numeric | Stock (puede no ser actual real) |

### compras1 (131 campos — DETALLE)

JOIN con compras2 por PK compuesta (empresa, codigo, letra, sucursal, numero, orden).

Campos clave: renglon, articulo, descripcion, precio, cantidad, deposito, operacion('+'/'-'), serie(YYMM), estado_stock, estado_cc, estado, cuenta, precio_unitario, subtotal, precio_fabrica

### compras2 (169 campos — CABECERA)

PK: (empresa, codigo, letra, sucursal, numero, orden)

Campos clave: deposito, cuenta (FK → proveedores.numero), denominacion, fecha_comprobante, monto_general, concepto_gravado, estado, moneda, valor_dolar, observaciones

### ventas1 (151 campos — DETALLE)

**SÍ tiene campo empresa** (varchar 10). Estructura análoga a compras1 con campos de venta: precio_costo, viajante, entregador, descuentos, comisión.

### ventas2 (187 campos — CABECERA)

Estructura análoga a compras2 con campos de cliente.

### stock (12 campos)

PK: deposito + articulo + serie. ~1.1M filas.

Campos: stock_actual, stock_custodia, stock_pendiente, stock_unidades

### Tablas de referencia

| Tabla | PK | Campo nombre | Nota |
|-------|-----|-------------|------|
| marcas | codigo | **descripcion** (NO "nombre") | cuenta → proveedores.numero |
| subrubro | codigo | descripcion | codrubro → rubros.codigo |
| rubros | codigo | descripcion | 1=Damas, 3=Hombres, 6=Unisex... |
| lineas | codigo | descripcion | 1=Verano, 2=Invierno, 3=Pretemporada, 4=Atemporal, 5=Colegial, 6=Seguridad |
| grupos | codigo | descripcion | PVC, CUERO, GOMA EVA, etc. (⚠️ articulo.grupo es varchar) |
| proveedores | numero | denominacion | 171 campos. cuit, condicion_iva, nombre_fantasia |
| deposito | — | — | ⚠️ Tabla vacía. Depósitos se referencian por código numérico |

---

## 8. TABLAS ANALÍTICAS EN OMICRONVT

| Tabla/Vista | Tipo | Filas | Descripción |
|-------------|------|-------|-------------|
| stock_historico_semanal | TABLA | ~22M | Foto stock cada lunes desde mar-2024 |
| stock_historico_mensual | TABLA | — | Foto mensual |
| stock_por_codigo | VISTA | — | Stock actual = UNION msgestion01+msgestion03 |
| compras2_pagos1_plazos | VISTA | — | Compras con plazos de pago (21 cols) |
| agrupador_subrubro / map_subrubro_industria | TABLA | — | Mapeo subrubro → industria |
| t_recupero_inversion | TABLA | ~500 | Proveedor × industria × período. SP: sp_refrescar_recupero_inversion |
| v_pedidos_cumplimiento | VISTA | — | Pedidos cruzados con entregas |
| pedidos_cumplimiento_cache | TABLA | ~560 | Cache materializada. SP: sp_sync_pedidos |

---

## 9. RELACIONES (FKs y JOINs)

```
articulo.codigo ←→ compras1.articulo
articulo.codigo ←→ ventas1.articulo
articulo.codigo ←→ stock.articulo
articulo.codigo ←→ stock_historico_semanal.codigo
articulo.codigo ←→ stock_por_codigo.articulo

articulo.marca → marcas.codigo
articulo.subrubro → subrubro.codigo
articulo.rubro → rubros.codigo
articulo.linea → lineas.codigo
articulo.grupo → grupos.codigo (⚠️ grupo es varchar, grupos.codigo es int — usar ISNUMERIC)

subrubro.codrubro → rubros.codigo
subrubro.codigo → agrupador_subrubro.subrubro

marcas.cuenta → proveedores.numero
compras2.cuenta → proveedores.numero
ventas1.cuenta → clientes.numero

compras1 ↔ compras2: JOIN por (empresa, codigo, letra, sucursal, numero, orden)
ventas1 ↔ ventas2: JOIN por (empresa, codigo, letra, sucursal, numero, orden)
pedico1 ↔ pedico2: JOIN por (empresa, codigo, letra, sucursal, numero, orden)
pedico1_entregas → pedico1: por (codigo, letra, sucursal, numero, orden, renglon)
```

---

## 10. REGLAS DE NEGOCIO

### Compras
- codigo=1 Facturas SUMAN, codigo=3 NC RESTAN, codigo=7/36 Remitos EXCLUIR de $ (duplican facturas)
- Compra neta: `SUM(CASE WHEN c2.codigo = 1 THEN c1.cantidad WHEN c2.codigo = 3 THEN -c1.cantidad ELSE 0 END)`
- Ambas empresas se suman para análisis completo (excepto pedidos donde filtrar CALZALINDO)

### Proveedores "basura"
Filtrar: `subrubro > 0 AND industria <> 'Sin clasificar'`
Excluye: SUELDOS GERENCIALES, ALQUILERES, MERCADO LIBRE, Capacitación Laboral.

### Clasificación de industrias (subrubro → industria)

| Industria | Subrubros |
|-----------|-----------|
| Zapatería | 1-9, 11-17, 20-21, 34-35, 37-38, 40-44 |
| Deportes | 10, 19, 22, 33, 45, 47-51, 53-54, 59 |
| Mixto_Zap_Dep | 52 (Zapatilla Casual), 55 (Sneakers) |
| Marroquinería | 18, 24-26, 30-31, 39, 58 |
| Indumentaria | 23, 46, 57, 61-63 |
| Cosmética | 27-29, 32 |

### Temporadas

| Industria | Período | Meses |
|-----------|---------|-------|
| Zapatería/Marroquinería/Indumentaria/Cosmética | OI (Otoño-Invierno) | Mar-Ago |
| Zapatería/Marroquinería/Indumentaria/Cosmética | PV (Primavera-Verano) | Sep-Feb |
| Deportes/Mixto | H1 (1er semestre) | Ene-Jun |
| Deportes/Mixto | H2 (2do semestre) | Jul-Dic |

---

## 11. LÓGICA FIFO PARA RECUPERO DE INVERSIÓN

Para medir cuánto tarda en venderse una compra, descontar stock previo (FIFO).

**Stock previo**: `stock_historico_semanal` con foto del lunes anterior/igual a fecha de compra.

**Hitos**: dias_1ra_venta (acumulado > stock_previo), dias_50, dias_75, dias_90, dias_100.

**Plazo proyectado**: 100% vendido → d100 real. En curso → proyección lineal. Sin ventas → penaliza × 2.

---

## 12. CONSTRAINTS TÉCNICOS Y LECCIONES

1. **SQL Server 2012 RTM en .111**: NO soporta TRY_CAST, STRING_AGG, CONCAT_WS. Usar ISNUMERIC, STUFF+FOR XML, concatenación con +.
2. **articulo.grupo es varchar(3)**: puede contener valores no numéricos. Siempre usar `CASE WHEN ISNUMERIC(a.grupo) = 1 THEN CAST(a.grupo AS INT) ELSE -1 END` para JOINs con grupos.codigo.
3. **Vistas en msgestionC son read-only**: INSERT da error 4406. Insertar en msgestion01 o msgestion03 directamente.
4. **ALTER VIEW falla silenciosamente**: Si un batch falla, los siguientes batches (separados por GO) siguen ejecutando. Siempre verificar con `SELECT definition FROM sys.sql_modules WHERE object_id = OBJECT_ID('...')`.
5. **Pedidos duplicados**: Cada pedido existe en CALZALINDO y H4. Filtrar `WHERE p2.empresa = 'CALZALINDO'` en vistas/queries de pedidos.
6. **pedico1_entregas vacía para pedidos nuevos**: El ERP desktop no la poblaba. Solo se llena desde la web app al crear remitos.
7. **marcas.descripcion** (NO .nombre): campo se llama `descripcion`.
8. **ventas1 SÍ tiene campo empresa**: corregido en v2.
9. **deposito (tabla) vacía**: depósitos se referencian por código numérico directo.
10. **Deploy via SMB**: `bash ~/Downloads/calzalindo_informes_DEPLOY/deploy.sh`

---

## 13. OBJETOS CREADOS EN OMICRONVT (.111)

| Objeto | Tipo | Descripción |
|--------|------|-------------|
| v_pedidos_cumplimiento | VISTA | Pedidos × entregas. Filtro CALZALINDO, ISNUMERIC para grupo, OUTER APPLY pedico1_entregas |
| pedidos_cumplimiento_cache | TABLA | Cache materializada ~560 filas, 36 columnas |
| sp_sync_pedidos | SP | TRUNCATE + INSERT INTO cache FROM vista |
| t_recupero_inversion | TABLA | ~500 filas, proveedor × industria × período |
| sp_refrescar_recupero_inversion | SP | Refresco semanal |
| stock_historico_semanal | TABLA | ~22M filas, foto lunes desde mar-2024 |
| stock_historico_mensual | TABLA | Foto mensual |
| compras2_pagos1_plazos | VISTA | Compras con plazos de pago |
| agrupador_subrubro | TABLA | Mapeo subrubro → industria |
| map_subrubro_industria | TABLA | Mapeo subrubro → industria (alias) |

---

## 14. VENDEDORES Y PRODUCTIVIDAD

### Tabla viajantes (maestro de vendedores)

**Ubicación**: msgestionC.dbo.viajantes (también en msgestion01, msgestion03, msgestion01art)

**PK**: `codigo` (numeric). **JOIN**: `ventas1.viajante = viajantes.codigo`

**Columnas clave**: codigo, descripcion (nombre, varchar 30), porcentaje (comisión), porcentaje_2, porcentaje_cobranza, estado (char 1), tipo, email, divisiones_habilitadas

**Hallazgos (5 marzo 2026)**:
- 101 viajantes activos con venta > $100K en últimos 6 meses
- **NO vincula con tabla empleados** — son entidades separadas en el ERP
- Las comisiones configuradas (campo `porcentaje`) no diferencian por margen
- Rango de margen individual: 9% a 65% — dispersión extrema
- Top 5 vendedores concentran ~40% de la facturación total

### Web App existente: calzalindo_objetivos_v2

- URL: `http://192.168.2.111:8000/calzalindo_objetivos_v2/`
- **Informes de efectividad**: `/informes_efectividad/sueldos` (global) y `/informes_efectividad/vendedor_individual_form` (individual)
- Models en: `cowork_pedidos/models/` — scripts Python 2.7 (web2py)
- Funciones clave:
  - `func_informes.py`: compras/ventas por marca, margen bruto, curvas por CSR
  - `func_efectividad.py`: tickets por sucursal
  - `funciones_informes_consolidados.py`: ventas consolidadas con precio_costo, compras consolidadas, stock, gráficos Highcharts
  - `func_stock.py`: stock actual y días quebrado por producto
  - `func_objetivos.py`: lógica de objetivos
- Vista consolidada: `omicron_ventas1` (UNION msgestion01+msgestion03)
- Vista remitos: `omicron_compras1_remitos`
- Variable global: `depos_para_informes` (definida en tablas_db1.py)

---

## 15. ESTADO DE DESARROLLO

### Completado
- [x] Dashboard de pedidos con KPIs, tabla proveedores, vencidas, antigüedad
- [x] Detalle por proveedor con drill-down
- [x] Creación de remitos desde web (7 tablas, ambas bases)
- [x] Vinculación remito↔pedido via pedico1_entregas
- [x] Vista v_pedidos_cumplimiento con filtro CALZALINDO y pedico1_entregas
- [x] Cache materializada + SP de sync
- [x] Columnas rubro, grupo, linea en vista
- [x] Rename CLZ → ABI en toda la interfaz
- [x] Sistema de roles (admin, gerencia, compras)

### Pendiente
- [ ] Órdenes de pago — consulta desde web (creación en desktop)
- [ ] Auto-fill split % por proveedor (ABI/H4)
- [ ] Análisis por talle/número (últimos 2 dígitos de codigo_sinonimo)
- [ ] Flag "compra a destiempo"
- [ ] GMROI como columna adicional
- [ ] Proceso auditoría de stock

---

## 15. PRODUCTIVIDAD E INCENTIVOS (Sección nueva — 5/3/2026)

### Fuentes de datos descubiertas

| Dato | Tabla/Vista | Base | Notas |
|------|-------------|------|-------|
| Sueldos reales | `moviempl1` | msgestion01 | `codigo_movimiento IN (8,10,30,31)`, campo `numero_cuenta` = viajante codigo |
| Ventas por vendedor | `ventas1_vendedor` | omicronvt | Vista con precio_costo, viajante_descripcion, codigo_sinonimo |
| Turnos atendidos | `turnos` | db5 (MySQL) | No accesible desde réplica SQL Server |
| Objetivos | `objetivos_vendedores_fijos` | web2py SQLite | No accesible desde réplica |

### Fórmulas clave (replicadas del controller `informes_efectividad`)
```
Productividad = venta_periodo / sueldo_promedio_mensual
Participación = venta_vendedor / venta_total × 100
Pares/Ticket = pares / tickets
Conversión = tickets / turnos_atendidos (requiere db5)
```

### Hallazgos de productividad (Sep 2025 – Feb 2026)
- 70 empleados con sueldo en moviempl1
- 51 de esos tienen match con viajantes activos
- 115 viajantes con ventas significativas en el período
- Productividad promedio (con sueldo): ~50x (6 meses venta / 1 mes sueldo)
- Diciembre: mes de mayor venta ($557M), índice estacional 1.48
- Septiembre: mes más bajo ($319M), índice estacional 0.85

### Modelo de incentivos propuesto
- Comisión escalonada por banda de margen (0% para <35%, hasta 7% para >55%)
- Factor estacional: multiplica comisión base (1.3 en meses difíciles, 0.8 en Dic)
- Bonus productividad: adicional para quienes superan 5x productividad
- Margen <35% PROHIBIDO: protección contra ventas destructivas

### Archivos generados
- `PRODUCTIVIDAD_INCENTIVOS_H4.xlsx` — 5 hojas: Productividad, Estacionalidad, Modelo Incentivos, Simulador, Acción Inmediata
- `RANKING_VENDEDORES_H4_CALZALINDO.xlsx` — Ranking original con margen y tickets

### Módulo web2py: informes_productividad (desplegado 5/3/2026)

**App**: `calzalindo_informes` (NO calzalindo_objetivos_v2)
**Deploy**: `calzalindo_informes_DEPLOY/deploy.sh` + reiniciar web2py (controllers nuevos requieren restart)

**Archivos**:
- `controllers/informes_productividad.py` — 4 vistas + 2 APIs JSON
- `views/informes_productividad/` — dashboard, vendedor, incentivos, estacionalidad
- `models/db_access.py` — Rol `informes_rrhh` agregado, permisos para informes_productividad.*
- `models/db_extra.py` — Conexiones dbC (msgestionC) y db5 (MySQL turnos) con try/except
- `models/cer.py` — Función fx_AjustarPorCer para ajuste inflacionario
- `views/layout.html` — Link "Productividad" en navbar

**Sistema de auth**: NO usa `@auth.requires_membership` — usa `_requiere_acceso()` al inicio de cada función + `_puede_ver()` en layout + `_es_admin()`. Definidos en `db_access.py`.

**Roles con acceso a productividad**: informes_admin, informes_gerencia, informes_rrhh
**Roles heredados del sistema viejo**: admins/ges_admin → informes_admin, finanzas/gestion → informes_gerencia

**Optimizaciones (v2)**:
- Queries con READ UNCOMMITTED (NOLOCK) para evitar bloqueos
- Turnos: query batch en vez de N+1 (una query para todos los vendedores)
- dbC y db5 con try/except en model (si falla conexión, queda None, no crashea web2py)
- Sensor de tiempos en cada página (muestra duración de cada query)

**IMPORTANTE**: Al agregar un controller NUEVO hay que reiniciar web2py — el parametric router cachea la lista de controllers al arrancar.
