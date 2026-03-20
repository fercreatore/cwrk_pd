# BITÁCORA DE DESARROLLO — Proyecto Integral ERP
## H4 / Calzalindo — cowork_pedidos

> **INSTRUCCIÓN PARA CLAUDE**: Este es el archivo maestro de avance.
> LEER PRIMERO en cada sesión nueva para saber qué se hizo y qué falta.
> AL CERRAR cada sesión, ACTUALIZAR con los cambios realizados.

> Última actualización: 20 de marzo de 2026 — Refresh token ML + revisión facturador TN + batch publish

---

## 20 de marzo de 2026 — Overnight: token ML, facturador TN, batch publish

### 1. refresh_token_ml.py (NUEVO)
Script `multicanal/refresh_token_ml.py` para renovar access_token de ML automáticamente.
Lee `mercadolibre_config.json`, verifica vigencia (TTL 6h, margen 90min), renueva vía OAuth2.
Soporta `--check` y `--force`. Listo para cron cada 5h.

### 2. Revisión facturador_tn.py — Qué falta para modo real

**Estado actual**: dry-run funciona. Tiene modo `--directo` (INSERT ERP) y modo POS 109.

**Payload POS 109 — Verificado OK** (post commit 23a4aa2):
- Campos renombrados según endpoint de Luciano: `nro_doc`, `tipo_doc`, `condicion_iva`, `nombre`, `apellido`, `usuario_tn`, `usuario_tn_nick`, `mi_usuario`, `mi_medio_pago`, `productos`
- `tenant: 'tiendanube'` para distinguir de ML

**Pendientes para pasar a modo real**:
1. **Medio de pago TN**: `mi_medio_pago.id=137` es "MERCADOLIBRE ONLINE API" — crear/asignar uno específico para TiendaNube (ej: "TIENDANUBE ONLINE API") o confirmar con Luciano que se use el mismo
2. **Sucursal/depósito**: `usuario.sucursal=2`, `deposito=0` — validar contra la configuración real del POS 109
3. **Campo telefono**: el payload no envía teléfono del cliente — verificar si el 109 lo requiere
4. **Retry/cola**: no hay reintentos si el 109 falla (timeout 60s, luego error y sigue). Evaluar si implementar cola de reintentos
5. **Webhook TN**: actualmente es polling (busca órdenes cada X tiempo). Para producción considerar webhook de TN para procesamiento en tiempo real
6. **SKUs sin match**: productos sin SKU o sin match en ERP se skipean silenciosamente — en producción alertar al operador
7. **Test end-to-end**: ejecutar `--dry-run` contra TN real y verificar que los payloads se armen correctamente con órdenes reales

**NO es bug**: `operacion='+'` en ventas1 es correcto — MS Gestión usa '+' para facturas de venta; el descuento de stock se hace con UPDATE directo (líneas 744-749).

### 3. Publicación masiva batch en canales.py (NUEVO)
Función `publicar_batch()` en `CanalTiendaNube` y `CanalMercadoLibre` que toma artículos con stock+foto+SKU y publica de a lotes con rate limiting y reporte detallado

---

## RESUMEN EJECUTIVO

Sistema integral de gestión ERP para cadena de calzado en Venado Tuerto (H4 SRL + CALZALINDO).
Incluye: carga automática de pedidos, proyección de compras por temporada, OCR de facturas,
asignación automática de bases (01/03), sincronización Mac↔servidor, y sistema vendedor freelance.

---

## INFRAESTRUCTURA

### Servidores
| Recurso | IP | Hostname | Uso |
|---------|-----|----------|-----|
| **Producción** | 192.168.2.111 | DELL-SVR | SQL Server 2012 RTM, web2py, scripts Python |
| **Réplica/Apps** | 192.168.2.112 | DATASVRW | Réplica SQL, MCP sql-replica, Metabase, FastAPI freelance |
| **Mac (Cowork)** | 192.168.2.58 | MacBook-Pro-de-Fernando | Desarrollo, Cowork, Streamlit |

### Bases de datos
| Base | Contenido |
|------|-----------|
| `msgestion01` | CALZALINDO/ABI (empresa informal) — pedidos, compras, ventas |
| `msgestion03` | H4 SRL (empresa formal) — pedidos, compras, ventas |
| `msgestionC` | VIEWs combinadas (NO insertar acá → error 4406) |
| `msgestion01art` | Artículos compartidos (tabla `articulo`, campo `descripcion_1`) |
| `omicronvt` | Analítica, agrupadores |
| `clz_ventas_sql` | Auth centralizada (tabla `auth_user`) |

### Credenciales
| Servicio | Usuario | Contraseña | Notas |
|----------|---------|------------|-------|
| SQL Server (pyodbc) | `am` | `dl` | SQL auth, ambos servidores |
| SMB Windows (111) | `administrador` | `cagr$2011` (minúscula c) | Para mount_smbfs desde Mac |

### Conexión IMPORTANTE — MCP sql-replica
**El tool `mcp__sql-replica__execute_sql_query` conecta a la RÉPLICA (112), NO a producción (111).**
Solo sirve para SELECT. Cualquier INSERT/UPDATE va por Python en el 111 directamente.

### Python en el 111
- `python` → Python 2.7 (NO USAR)
- `py -3` → Python 3.13 (CORRECTO)
- Carpeta scripts: `C:\cowork_pedidos\`

### Sincronización Mac ↔ 111
- Mount SMB: `sudo mount_smbfs '//administrador:cagr$2011@192.168.2.111/c$/cowork_pedidos' /Volumes/cowork_111`
- Watcher automático: `sudo ~/Desktop/cowork_pedidos/watch_sync.sh &` (detecta cambios cada 3s, rsync automático)
- Stop watcher: `~/Desktop/cowork_pedidos/watch_sync.sh stop`
- Sync manual: `sudo ~/Desktop/cowork_pedidos/sync_to_111.sh`
- Archivos sync: `*.py, *.md, *.sql, *.xlsx`

---

## ESTADO ACTUAL POR MÓDULO

### ✅ Pipeline Carga de Pedidos (pasos 1-6)
- Verificación BD → búsqueda artículo → período → INSERT pedido → parseo Excel → flujo completo
- `paso4_insertar_pedido.py`: routing automático empresa→base
  - `get_tabla_base("pedico2", "CALZALINDO")` → `MSGESTION01.dbo.pedico2`
  - `get_tabla_base("pedico2", "H4")` → `MSGESTION03.dbo.pedico2`
- Modos: `--dry-run` y `--ejecutar`

### ✅ Pedido KNU GTN — INSERTADO EN PRODUCCIÓN
- 3 colores confirmados, 124 pares, $2,728,000 a $22,000/par
- Pedido insertado exitosamente via `insertar_knu_gtn.py` en el 111
- Detalle:
  - KNU Negro/Blanco (104KNUSK00): 68 pares, talles 34-44
  - KNU Negro/Ngo/Bco (104KNUSK10): 34 pares, talles 35-43
  - KNU Gris/Blanco (104KNUSK13): 22 pares, talles 35-44 (sin 41)
- Convenciones pedico2: codigo=8, letra='X', sucursal=1, estado='V'
- Numero/orden: MAX+1 auto-incremental

### ✅ App Streamlit OCR (app_carga.py)
- Upload PDF → OCR → detección proveedor → previsualización precios → inserción
- OCR Distrinando y Wake funcionando (fitz + pdfplumber)
- Proveedores dinámicos desde DB (`proveedores_db.py`)

### ✅ Análisis Proveedor → Base (01 vs 03)
- **HALLAZGO CLAVE**: pedico1/pedico2 son COMPARTIDAS — idénticos registros en ambas bases
- La diferenciación entre empresas ocurre a nivel FACTURA (compras2), NO pedido
- 359 proveedores analizados desde compras2:
  - 77 SOLO_01 | 189 SOLO_03 | 93 en AMBAS bases
  - Clasificación: SOLO_01, MAYORIA_01 (≥65%), SPLIT (35-65%), MAYORIA_03, SOLO_03
- Tabla `compras2`: usar `monto_general` y `concepto_gravado` (NO existe `importe_neto`)
- GTN (proveedor 104): 100% base 01 ($58M, 51 facturas, zero en 03)
- Script creado: `crear_tabla_asignacion.py` — crea `MSGESTION01.dbo.proveedor_asignacion_base`
- SQL alternativo: `CREATE_proveedor_asignacion_base.sql` (359 INSERTs hardcoded)
- **PENDIENTE**: ejecutar `crear_tabla_asignacion.py` en el 111

### ✅ Proyección de Compras por Temporada
- Stored procedure: `SP_ProyeccionCompras_Temporada.sql`
- Análisis completo catálogo GTN: 23 modelos, stock coverage, velocidad de venta
- Pedido híbrido (humano + AI): 1,188 pares
- Pedido 2 meses: 656 pares, $14.68M (`Pedido_GTN_2026_2MESES.xlsx`)

### ✅ Sincronización Mac ↔ 111
- `sync_to_111.sh` — rsync manual (requiere sudo)
- `watch_sync.sh` — watcher automático con polling cada 3s
- `com.cowork.sync-watcher.plist` — LaunchAgent (opcional, para auto-start al login)
- `sync_from_mac.bat` — alternativa Windows (robocopy pull desde Mac)

### ⚠️ Parcial
- **Cabecera OCR fitz**: Total/Subtotal/IVA = $0.00 con PyMuPDF (cosmético, funciona con pdfplumber)
- **Bonificación factura**: se muestra en app pero falta confirmar que `descuento_1` se grabe bien al INSERT
- **Tabla proveedor_asignacion_base**: SQL listo, NO ejecutado aún en producción

### ❌ Pendiente — App Carga (para que funcione punta a punta)
1. **Fix `construir_sinonimo()` en `paso8_carga_factura.py`**: hoy recibe `RBK1100033358` pero necesita armar `656` + `codigo_objeto_costo`(5 chars) + `color`(2) + `talle`(2). Buscar codigo_objeto_costo en artículos existentes del mismo producto, si no hay → pedir al usuario 5 letras en UI.
2. **Agregar colores Reebok a `COLORES_CONOCIDOS`** en `paso8_carga_factura.py`: AZUL/BLANCO→05, y los existentes (BLANCO/CELESTE→01, NEGRO/NEGRO/GRIS→10, GRIS/NEGRO/LILA→13, GRIS/NEGRO/ROSA→13, BEIGE/BEIGE→15, GRIS/GRIS/AP→39).
3. **Poblar `articulo_proveedor`** al crear artículo nuevo: INSERT con `codigo_art_prov = RBK...` para vincular código proveedor con artículo interno (usado para actualizar precios por lista).
4. **Campo en UI** para `codigo_objeto_costo` (5 chars) cuando es artículo completamente nuevo sin referencia en DB.
5. **Probar verificación** de artículos con sinónimo correcto.
6. **Probar INSERT completo** FLEXAGON ENERGY TR 4 AZUL/BLANCO por la app.

### ❌ Pendiente — Otros
- Ejecutar `crear_tabla_asignacion.py` en 111 (crear tabla proveedor→base)
- Ejecutar `fix_capas_2_y_3.sql` en 111 (sistema 3 capas de talles)
- Pedido GTN completo: solo 124 de 656 pares insertados (faltan ~20 modelos)

---

## ARCHIVOS PRINCIPALES

### Scripts Python (ejecutar en 111 con `py -3`)
| Archivo | Función |
|---------|---------|
| `config.py` | Conexión SQL Server + configuración 5 proveedores (Alpargatas 668, GTN 104, Wake 594, Distrinando 656, RINGO/Souter 561) |
| `paso1_verificar_bd.py` | Verificar conexión y estructura tablas |
| `paso2_buscar_articulo.py` | Búsqueda/alta de artículo en `articulo` |
| `paso3_calcular_periodo.py` | Cálculo período OI/PV/H1/H2 |
| `paso4_insertar_pedido.py` | INSERT en pedico2 + pedico1 (con routing empresa→base) |
| `paso5_parsear_excel.py` | Parseo Excel/CSV genérico |
| `paso5b_parsear_topper.py` | Parseo específico Topper |
| `paso6_flujo_completo.py` | Orquestador pasos 1-5 |
| `paso7_buscar_imagenes.py` | Búsqueda imágenes de producto |
| `paso7_reconstruir_colores.py` | Reconstruir info de colores |
| `paso8_carga_factura.py` | Carga factura (usado por app Streamlit) |
| `app_carga.py` | App Streamlit: UI carga facturas (correr en Mac) |
| `ocr_factura.py` | Parser OCR: extrae datos de PDFs |
| `proveedores_db.py` | Proveedores dinámicos desde DB |
| `insertar_knu_gtn.py` | Inserción específica KNU/GTN (YA EJECUTADO) |
| `insertar_carmel_ringo.py` | ✅ EJECUTADO — CARMEL CANELA Souter/RINGO — pedido #134069, 30 pares |
| `insertar_diadora.py` | ✅ EJECUTADO — Diadora Calzados Blanco — pedido #1134068, 48 pares |
| `fix_marca_diadora.py` | ✅ EJECUTADO — Fix marca 614→675, grupo 5→15 para 20 arts Diadora |
| `insertar_atomik_runflex.py` | ✅ EJECUTADO — Atomik RUNFLEX VICBOR — pedido #1134069, 120 pares |
| `crear_tabla_asignacion.py` | Crear tabla proveedor_asignacion_base |
| `verificar_e_insertar_111.py` | Verificación e inserción en producción |
| `alta_masiva_faltantes.py` | Alta masiva artículos faltantes |

### Scripts de Sincronización
| Archivo | Función |
|---------|---------|
| `sync_to_111.sh` | Sync manual Mac→111 via SMB (rsync) |
| `watch_sync.sh` | Watcher automático: detecta cambios, sync al 111 |
| `sync_from_mac.bat` | Alternativa: Windows pull desde Mac (robocopy) |
| `com.cowork.sync-watcher.plist` | LaunchAgent para auto-start |

### Documentación
| Archivo | Contenido |
|---------|-----------|
| `BITACORA_DESARROLLO.md` | **ESTE ARCHIVO** — historial completo |
| `ESTADO_PROYECTOS.md` | Estado de TODOS los proyectos (no solo pedidos) |
| `INSTRUCCIONES_COWORK.md` | Guía paso a paso para pipeline de pedidos |
| `PROYECTO_contexto_h4_calzalindo_v3.md` | Contexto de negocio y DB |
| `ARQUITECTURA_SISTEMA_VENDEDOR_FREELANCE.md` | Arquitectura sistema freelance |

### SQL y Datos
| Archivo | Contenido |
|---------|-----------|
| `INSERT_Pedido_KNU_GTN_CONFIRMADO.sql` | SQL referencia KNU (ya insertado via Python) |
| `CREATE_proveedor_asignacion_base.sql` | 359 INSERTs supplier→base mapping |
| `insertar_wkc215_en_111.sql` | Insert Wake específico |

---

## HISTORIAL DE CAMBIOS

### 15 de marzo de 2026 — Mejoras app_carga.py: proveedor auto-detect + UX

**Mejoras UX en app_carga.py (3 cambios pedidos por el usuario)**:

1. **Link corregido en app_h4.py**: El botón "Carga Facturas" apuntaba al puerto 8502 (el mismo dashboard). Corregido a `http://192.168.2.112:8503` donde corre `app_carga.py`.

2. **Default tipo comprobante → Nota de Pedido (NP)**: Cambiado `tipo_default = 2` para que arranque en "Nota de Pedido" en vez de "Factura". Hace menos daño si se equivocan.

3. **Selector de proveedor arranca vacío + auto-detección desde archivo**:
   - Selectbox con `index=None, placeholder="Seleccionar proveedor..."` — no pre-selecciona ninguno
   - Mensaje informativo en sidebar: "Cargá un archivo para detectar el proveedor automáticamente"
   - Guard en botones Verificar/Procesar: muestra error si no hay proveedor seleccionado
   - **Auto-detección al subir Excel** (dos estrategias en cascada):
     a. **Por nombre de archivo**: usa `detectar_proveedor_por_texto(filename)` que busca en índice de `denominacion`, `nombre_fantasia` y marcas. Ej: "PEDIDO JUANA VA.xlsx" → matchea "JUANA VA" en fantasia del proveedor 938 (55.COM Grupo)
     b. **Por códigos de artículo**: nueva función `_detectar_proveedor_por_articulos(codigos)` busca los modelos del Excel en `msgestion01art.dbo.articulo` (por `descripcion_1` y `codigo`) y retorna el proveedor con más hits
   - Si detecta, setea `prov_detectado` y muestra en sidebar con badge verde

**Verificación detección JUANA VA**:
- Proveedor 938 "55.COM (Grupo)" tiene `nombre_fantasia = "Juana Va"` → detectado correctamente
- Proveedor 979 "JUANA Y SUS HERMANAS SRL" tiene fantasia "LEGION EXTRANJERA" → no confunde
- Proveedor 11 TIMMi tiene fantasia "contacto:juana-Adriana-Marcos" → filtrado por blacklist de contactos
- El índice `_construir_indice_busqueda()` ya cubre los 3 campos: denominacion, nombre_fantasia (split por -/), y marcas

**Archivos modificados**:
- `app_carga.py` — selectbox proveedor, auto-detección Excel, guards botones, nueva función `_detectar_proveedor_por_articulos()`
- `app_h4.py` — link puerto 8502→8503

**Pendiente**: Deploy al 112 con `./deploy.sh scripts` y test con PEDIDO JUANA VA.xlsx

---

### 14 de marzo de 2026 — Diagnóstico Stock Negativo CLZ (código 95 / POS)

**Investigación stock negativo fantasma en msgestion01 (CLZ)**:
- Detectados -293,051 pares negativos en 66,753 filas de stock en CLZ
- 97% concentrado en depósito 0 (Central, -82,489) y depósito 11 (-201,627)
- **CAUSA RAÍZ**: Comprobante código 95 "SOLICITUD A DEPOSITO", generado por usuario POS
- Código 95 existe SOLO en CLZ — H4 tiene cero movimientos de este tipo
- Mecanismo: compras entran por Remito (cod.7) en H4, pero las salidas por venta POS se registran en CLZ vía Solicitud cod.95. CLZ descuenta stock que nunca recibió
- Activo desde agosto 2020, acumula -574,687 pares de déficit. Crece cada año
- El consolidado (msgestionC) compensa correctamente: stock físico cuadra
- Artículo testigo: 296113 GONDOR II NEGRO T43 → H4: +24 compra, CLZ: -22 solicitudes, consolidado: 2 pares (confirmado físicamente)
- Reporte: `diagnostico_stock_negativo_clz.html`

**Análisis Zapatilla Outdoor — Escasez/Abundancia** (iniciado sesión anterior):
- Dashboard `outdoor_escasez_abundancia.html` con curva de talles, ranking marcas
- Datos consolidado: 2,295 vendidos / 1,270 stock = 6.6m cobertura
- TOPPER más crítico (644v/201s = 3.7m), STARFLEX más sobrante (82v/159s = 23.3m)
- T36-T37 ESCASOS, T40-T41 ABUNDANTES

**Consulta rápida**: Último código en `msgestion01art.dbo.articulo` = 361124 (WKC496_I26 ROSA). Próximo disponible: 361125.

---

### 12 de marzo de 2026 (sesión 2) — Mejoras UI pedidos + fix DIADORA

**Vista pedidos_detalle.html — Columnas sinónimo y talle**:
- Agregado campo `codigo_sinonimo` a la query de pedidos_detalle (JOIN con articulo)
- Nueva columna "Sinon." en tabla detalle principal, ordena por sinónimo+talle por defecto
- Esto agrupa automáticamente por modelo/color y ordena talles secuencialmente
- Agregado sinónimo y talle al panel de remito (para facilitar carga y parcialización)
- Sort y filtro funcionan en ambas tablas (detalle y remito)

**Vista pedidos.html — Resumen proveedores mejorado**:
- Agregada columna "Marca" al resumen (recolecta todas las marcas del proveedor)
- Headers ahora son ordenables (click) y filtrables (inputs en fila de filtros)
- Filtros: Proveedor, Industria, Marca (texto), Estado (dropdown)
- JS: funciones sortProv() y filtrarProv() con data-psort

**Serie secuencial YYMM0001**:
- Implementado en remito_crear(): serie = YYMM + secuencial 4 dígitos (ej: 26030001)
- Query MAX(serie) WHERE serie LIKE 'YYMM%' AND LEN=8 para obtener siguiente
- Aplica a todas las empresas (H4 y CALZALINDO)

**UPSERT pedico1_entregas**:
- Cambiado INSERT a IF EXISTS/UPDATE/ELSE/INSERT para evitar PK violation en entregas parciales

**DIADORA pedido #1134068 — INCIDENTE CRÍTICO**:
- Pedido aparecía duplicado en msgestionC (UNION ALL de 01+03)
- Se intentó borrar de msgestion01 con fix_diadora_duplicado.py
- **LECCIÓN CRÍTICA**: pedico1/pedico2 son TABLAS COMPARTIDAS entre ambas bases. DELETE de una borra de AMBAS.
- Pedido se perdió completamente. Script recrear_diadora_1134068.py creado para restaurar.
- Fix aplicado: `fecha_entrega` → `fecha_vencimiento` (columna no existía en pedico2)
- **PENDIENTE**: ejecutar recrear_diadora_1134068.py en 111

---

### 12 de marzo de 2026 — DIADORA + ATOMIK RUNFLEX (altas + pedidos)

**Diadora — Calzados Blanco S.A. (proveedor 614)**:
- Script `insertar_diadora.py`: 20 artículos (360527-360546) + pedido #1134068
- Factura A 0023-00062015, Remito 0024-00066200, 48 pares, 4 modelos
- CONSTANZA 2116, PROTON 2669, CHRONOS 2684, RIVER 2690
- Bonificación 5% de factura (descuento comercial)
- Rubro 1 (DAMAS), Subrubro 47 (Running), Grupo 15 (MACRAME), Línea 2 (Invierno)

**Errores corregidos en Diadora**:
- Marca: se creó con marca=614 (proveedor) → corregido a 675 (DIADORA) via `fix_marca_diadora.py`
- Grupo: se creó con grupo="5" (PU) → corregido a "15" (MACRAME) — TODO lo running es MACRAME
- Fix ejecutado: UPDATE 20 artículos, verificado con SELECT post-update
- config.py actualizado: proveedor 614 marca cambiada de 614 a 675

**Atomik RUNFLEX — VICBOR SRL (proveedor 594)**:
- Script `insertar_atomik_runflex.py`: 23 artículos (360547-360569) + pedido #1134069
- 2 Facturas: A 00043-00188989 (09/03) + A 00043-00189020 (10/03), 120 pares
- 4 colores: CREMA MUJ (24p), TOPO HOM (24p), MENTA MUJ (24p), NEGRO MUJ (48p)
- Precio $54,000, desc combinado 53.05% (línea 50.05% + bonif 6%) → costo $25,353
- Utilidades 120/144/60/45 (tomadas de ENERLITE running existentes del mismo proveedor)
- Marca 594 (ATOMIK), Grupo 15 (MACRAME), Subrubro 47 (Running)

**Reglas aprendidas**:
- Running = MACRAME (grupo 15), NUNCA PU (grupo 5)
- Proveedor 594 (VICBOR SRL) vende múltiples marcas: WAKE, Atomik, Massimo, Bagunza
- Descuento combinado: `1 - (1 - desc_linea/100) × (1 - desc_bonif/100)`
- Marca ≠ Proveedor: siempre buscar código correcto en tabla `marcas`

---

### 10 de marzo de 2026 — FIX serie/stock en remito_crear() + Vista remitos APLICADA

**DESCUBRIMIENTO CRÍTICO — Las bases usan modelos de serie distintos**:
- **msgestion03 (H4)**: ERP usa serie=' ' para TODO (compras y ventas). No crea series YYMM.
- **msgestion01 (CALZALINDO)**: ERP usa serie=YYMM ('2603') para compras, serie=' ' para ventas. Stock total = SUM(todas las series).
- Documentado en `_docs/SERIE_STOCK_BARCODE.md` para futura implementación de barcode.

**Fix aplicado en reportes.py (`remito_crear()`)**:
- Serie condicional: `serie = YYMM si CALZALINDO, ' ' si H4` (línea 1534)
- `movi_stock.unidades = int(cant)` (= cantidad, como el ERP)
- `stock_unidades` se actualiza junto con `stock_actual`
- Un solo bloque de stock (eliminado doble conteo que actualizaba AMBAS series)
- **PENDIENTE DEPLOY**: verificar que el 111 tenga el reportes.py actualizado

**Limpieza de datos históricos — EJECUTADA en 111**:
- Script `fix_stock_serie_cleanup.py`: limpió datos sucios del código WB viejo
- msg03: remito WB 1926645 (PIRA/CAMILA) — serie cambiada a ' ', doble conteo revertido
- msg03: valijas 359226/28/30 — filas '2603' huérfanas eliminadas, stock_unidades corregido
- msg01: 100 filas serie '2603' — stock_unidades igualado a stock_actual
- Remito PIRA 35309 (ejecutable) NO tocado.

**Vista v_pedidos_cumplimiento — APLICADA en 111**:
- `aplicar_view_remitos.py --ejecutar`: ALTER VIEW + sp_sync_pedidos
- 1235 filas actualizadas en cache
- Souter (561): 69 líneas COMPLETO, 1 PARCIAL, 81 PENDIENTE
- Vista es permanente, aplica a TODOS los proveedores/pedidos

**Remito prueba GO DANCE (342510) — PENDIENTE LIMPIAR**:
- Creado por web con código VIEJO (serie='2603' en msg03, doble conteo)
- Script `fix_go_dance_post_delete.py` listo para correr DESPUÉS de borrar desde ejecutable

---

### 9 de marzo de 2026 — CARMEL RINGO Reposición Invierno

**Análisis CARMEL CANELA con ajuste por quiebre de stock**:
- Producto: mocasín de tela CARMEL (marca RINGO/Souter S.A., proveedor 561)
- Color elegido: CANELA (37% de ventas totales, top seller)
- Talles: solo centrales 41-44 (80% de las ventas)
- Modelos activos: CARMEL 03 (DET TALON) y CARMEL 04 (DET CUELLO)

**Metodología de quiebre (REGLA CLAVE del usuario)**:
- SIEMPRE que se analice velocidad de venta, reconstruir stock mes a mes hacia atrás desde stock actual
- Usar compras1 (operacion='+') y ventas1 (excluir codigo 7,36) para reconstruir
- Un mes con stock=0 al inicio es "QUEBRADO" → no usar en cálculo de velocidad
- Velocidad real = ventas solo de meses CON stock / cantidad de meses CON stock

**Resultados devastadores del quiebre**:
- T42: QUEBRADO 34/39 meses (87%) — vel aparente 2/mes, vel REAL 10.8/mes
- T43: QUEBRADO 34/39 meses (87%) — vel REAL 9.0/mes
- T44: QUEBRADO 31/39 meses (79%) — vel REAL 4.4/mes
- T41: QUEBRADO 13/39 meses (33%) — vel REAL 2.6/mes
- La venta aparentemente baja NO es falta de demanda, es falta de stock

**Factor invierno**: 22% de velocidad alta temporada (derivado de 2023 cuando había stock)

**Pedido generado** (`insertar_carmel_ringo.py`):
- Empresa: H4 (compras recientes RINGO son H4, base MSGESTION03)
- CARMEL 03 CANELA: T41=1, T42=9, T43=8, T44=1 → 19 pares @ $34,700
- CARMEL 04 CANELA: T41=1, T42=4, T43=3, T44=3 → 11 pares @ $42,800
- Total: 30 pares, $1,130,100
- Split proporcional basado en ventas 6 meses por modelo
- RINGO agregado a config.py como proveedor 561

**Artículos CARMEL CANELA confirmados**:
```
CARMEL 03 CANELA (561CAR0322): 249885(T41), 249886(T42), 249887(T43), 249888(T44) — precio_fabrica $34,700
CARMEL 04 CANELA (561CAR0422): 249907(T41), 249908(T42), 249909(T43), 249910(T44) — precio_fabrica $42,800
```

**Estado**: ✅ INSERTADO en producción. Pedido #134069, orden 96. Verificado en réplica: 8 renglones OK.
- Sync falla por mount SMB → usuario debe hacer: `sudo mkdir -p /Volumes/cowork_111 && sudo mount_smbfs '//administrador:cagr$2011@192.168.2.111/c$/cowork_pedidos' /Volumes/cowork_111 && sudo rsync -av ~/Desktop/cowork_pedidos/ /Volumes/cowork_111/`
- Luego en 111: `py -3 C:\cowork_pedidos\insertar_carmel_ringo.py --dry-run` y después `--ejecutar`

### 7 de marzo de 2026 (tarde) — KNU GTN + Supplier→Base + Sync

**Pedido KNU GTN confirmado e insertado**:
- Usuario confirmó 3 colores KNU desde screenshot del proveedor
- Primer intento: INSERT fue a la réplica (112) por error — limpiado con DELETE
- Segundo intento: creado `insertar_knu_gtn.py` usando infraestructura paso4
- Ejecutado exitosamente en el 111 con `py -3 insertar_knu_gtn.py --ejecutar`
- 29 renglones, 124 pares, $2,728,000

**Análisis supplier→base completado**:
- Query a compras2 en msgestion01 y msgestion03, cross-reference por CUIT
- Descubrimiento: pedico1/pedico2 son tablas compartidas/espejadas entre bases
- Clasificación de 359 proveedores en 5 categorías
- Creado `crear_tabla_asignacion.py` y `CREATE_proveedor_asignacion_base.sql`
- GTN agregado a config.py como proveedor 104 con empresa="CALZALINDO"

**Ejemplos de distribución supplier→base**:
- GTN (20269920948): 100% base 01
- ALPARGATAS (30500525327): 100% base 03
- LESEDIFE (30661041486): 40% 01 / 60% 03
- LADY STORK (30698783032): 63% 01 / 37% 03
- CALZADOS BLANCO (30707450394): 3% 01 / 97% 03

**Sincronización Mac ↔ 111**:
- SMB mount configurado: `sudo mount_smbfs` con creds de administrador
- `sync_to_111.sh` creado y probado (funciona con sudo)
- `watch_sync.sh` creado: watcher automático con polling 3s + rsync
- Requiere sudo por permisos del mount

**Errores corregidos esta sesión**:
- `mcp__sql-replica` → es RÉPLICA, no producción. No usar para INSERT
- `articulos` → correcto: `articulo`; `descripcion` → correcto: `descripcion_1`
- `importe_neto` no existe en compras2 → usar `monto_general`, `concepto_gravado`
- `python` en 111 → Python 2.7 (NO). Usar `py -3` → Python 3.13

### 7 de marzo de 2026 (mañana) — OCR Distrinando + Proveedores

**Factura procesada**: Factura A 0039-273749, Distrinando, FLEXAGON ENERGY TR 4 AZUL/BLANCO
- RBK1100033358, M12 8/13, 12 pares (US 8-13 → AR 40-45), $67,181.45/u, Bonif 3%

**Bugs resueltos en ocr_factura.py**:
1. "4" de "TR 4" contamina números financieros → filtrar números cortos sin decimal
2. Total regex cruzaba líneas → buscar formato pdfplumber primero
3. Orden columnas diferente fitz vs pdfplumber → clasificación por magnitud
4. Números espurios de "M12 8/13" → limitar a 4 primeros + guard cantidad=0

**Cambios**: Distrinando descuento de 40→0 en config.py (viene en factura). App aplica bonificación en previsualización.

### 5-6 de marzo de 2026 — Sistema de Talles 3 Capas

- Capa 1: `descripcion_5` del artículo (talle AR directo)
- Capa 2: `aliases_talles` — equivalencias US/EU/UK → AR
- Capa 3: `regla_talle_subrubro` — reglas por subrubro
- Script: `calzalindo_informes_DEPLOY/sql/fix_capas_2_y_3.sql` — NO ejecutado

### Sesiones anteriores — Pipeline base + Proyección GTN

- Pipeline pasos 1-6 completo y testeado
- Parser Excel genérico + parser Topper
- Deploy web2py: dashboard pedidos/remitos/recupero
- DELETE movimientos erróneos VALIJA ROJA
- SP_ProyeccionCompras_Temporada.sql
- Análisis KNU GTN: stock coverage, velocidad venta, breakage adjustment
- Comparativo pedido humano vs AI para catálogo GTN
- Pedido híbrido 1,188 pares + pedido 2 meses 656 pares

---

## REGLAS DE NEGOCIO

1. **Empresas**: H4 SRL (formal, base 03) y CALZALINDO/ABI (informal, base 01). Artículos compartidos en msgestion01art.
2. **Pedidos compartidos**: pedico1/pedico2 son idénticas en ambas bases. La asignación empresa se hace al facturar (compras2).
3. **Routing inserción**: usar tabla `proveedor_asignacion_base` (cuando se cree) o lógica en config.py por ahora.
4. **Descuentos**: `descuento` = proveedor fijo; `descuento_1` = bonificación factura; `descuento_2` = otro.
5. **Talles Reebok**: US + 32 = AR hombres (US 8 = AR 40). Enteros solamente para running/training.
6. **Períodos**: Zapatería usa OI/PV; Deportes usa H1/H2.
7. **Remitos código 7 y 36**: EXCLUIR siempre.
8. **INSERT**: NUNCA en vistas de msgestionC (error 4406). Directo a msgestion01 o msgestion03.
9. **SQL Server 2012 RTM**: NO soporta TRY_CAST. Usar ISNUMERIC + CAST.
10. **Precios GTN**: $22,000/par (KNU).
11. **ANÁLISIS DE QUIEBRE (OBLIGATORIO)**: SIEMPRE que se calcule velocidad de venta para proyectar compras, reconstruir stock mes a mes trabajando hacia atrás desde el stock actual. Meses con stock=0 al inicio → "QUEBRADO", NO contar en velocidad. La venta aparente subestima la demanda real cuando hay quiebre frecuente.
12. **Reconstrucción stock**: stock_actual (de `msgestionC.dbo.stock`) - acumular compras1 (operacion='+') + acumular ventas1 (excluir codigo 7,36) mes a mes hacia el pasado.
13. **RINGO/Souter (561)**: empresa H4, base MSGESTION03. marca 294. CARMEL es mocasín de tela, temporada alta Oct-Feb, muerta Abr-Ago.
14. **Campo PK artículos**: `codigo` en `msgestion01art.dbo.articulo` (NO `numero` ni `articulo`).
15. **Stock field**: `stock_actual` en `msgestionC.dbo.stock` (NO `cantidad`).
16. **Running = MACRAME**: Todo lo que es running va en grupo="15" (MACRAME), NUNCA grupo="5" (PU/Sintético).
17. **Marca ≠ Proveedor**: Buscar siempre el código real en `msgestion03.dbo.marcas`. Ej: Diadora=675 (no 614), Atomik=594.
18. **Proveedor 594 multi-marca**: VICBOR SRL vende WAKE (desc 20%), Atomik (desc variable), Massimo (10%), Bagunza (6%). Marca según factura.
19. **Proveedor 614 (Calzados Blanco)**: marca 675 (DIADORA). Empresa H4, base 03. 97% de facturación en base 03.

---

## ARTÍCULOS KNU CONFIRMADOS (referencia)

```
KNU Negro/Blanco (104KNUSK00): 308884(34), 308874(35), 308875(36), 308876(37), 308877(38), 308878(39), 308879(40), 308880(41), 308881(42), 308882(43), 308883(44)
KNU Negro/Ngo/Bco (104KNUSK10): 316676(35), 316677(36), 316678(37), 316679(38), 316680(39), 316681(40), 316682(41), 316683(42), 316684(43)
KNU Gris/Blanco (104KNUSK13): 309409(34), 309410(35), 309411(36), 309412(37), 309413(38), 309414(39), 309415(40), 309416(41), 309417(42), 309418(43), 309419(44)
```

---

## CÓMO CONTINUAR UNA SESIÓN

1. Leer este archivo (`BITACORA_DESARROLLO.md`) — estado técnico completo
2. Leer `ESTADO_PROYECTOS.md` — vista alto nivel de TODOS los proyectos
3. Preguntar al usuario qué quiere trabajar
4. NO reescribir archivos .py sin leerlos primero
5. Los fixes de OCR ya están aplicados — no volver atrás
6. INSERT solo via Python en el 111 (NUNCA via MCP sql-replica)
