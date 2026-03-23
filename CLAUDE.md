# CLAUDE.md — Fuente Única de Verdad
## Proyecto Integral ERP — H4 / CALZALINDO
> Última actualización: 23 de marzo de 2026

> **LEER PRIMERO**. Este archivo tiene todo lo necesario para retomar sin preguntar.
> Si el usuario quiere trabajar otro proyecto → leer `ESTADO_PROYECTOS.md`

---

## QUÉ ES ESTE PROYECTO

Sistema para cargar notas de pedido de compra en el ERP MS Gestión de una cadena de calzado en Venado Tuerto.
Dos razones sociales: **H4 SRL** (formal, base msgestion03) y **CALZALINDO/ABI** (informal, base msgestion01).
Artículos compartidos en `msgestion01art.dbo.articulo`.

Pipeline: análisis de ventas/stock/quiebre → proyección de compras → generación de script Python → ejecución en servidor producción → INSERT en pedico2 (cabecera) + pedico1 (detalle).

También: app Streamlit para OCR de facturas PDF, app reposición con quiebre, sistema de talles 3 capas, mapping proveedor→base, sistema de informes web2py (calce financiero, ranking, presupuesto).

---

## INFRAESTRUCTURA

### Servidores
- **192.168.2.111 (DELL-SVR)** — Producción. SQL Server 2012 RTM. INSERT/UPDATE acá.
  - Python: `py -3` → 3.13 ✅ | `python` → 2.7 ❌
  - Scripts: `C:\cowork_pedidos\`
  - Web2py: `C:\web2py_src\applications\calzalindo_informes\`
  - SQL Server 2012 RTM: **NO soporta TRY_CAST** → usar ISNUMERIC + CAST
- **192.168.2.112 (DATASVRW)** — Réplica/Apps. MCP sql-replica conecta ACÁ (solo SELECT).
  - Python 3.14: `C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe`
  - FastAPI freelance: `C:\calzalindo_freelance\` en :8001
  - ODBC Driver 17 instalado, pyodbc funciona ✅ (pymssql NO)
- **Mac local** — Desarrollo. Streamlit, Cowork.

### Credenciales
- SQL Server (pyodbc): `am` / `dl`
- SMB Windows: `administrador` / `cagr$2011`

### Conexión MCP
**`sql-replica`** → `@bytebase/dbhub` apuntando a **192.168.2.111** (producción), base `msgestionC`.
- Requiere `OPENSSL_CONF=/tmp/openssl_legacy.cnf` (OpenSSL 3.x no permite TLS 1.0 de SQL Server 2012)
- `config.py` crea el archivo automáticamente al importarse si no existe
- Usar solo para SELECT. INSERT va por Python en el 111 directamente.

### Sincronización Mac ↔ 111
**⚠️ NUNCA hacer rsync completo de la carpeta** — son 700MB+ de Excel/ZIP/PDF que no van al server.
Usar SIEMPRE `deploy.sh` que filtra solo código (.py, .sql, .json, .md, .txt, .sh):

```bash
cd ~/Desktop/cowork_pedidos/_sync_tools

./deploy.sh scripts    # Pipeline + oneshot scripts
./deploy.sh web2py     # calzalindo_informes → web2py en 111
./deploy.sh todo       # scripts + web2py
./deploy.sh dryrun     # Ver qué se copiaría
./deploy.sh archivo _excel_pedidos/Pedido.xlsx  # Archivo puntual
```

`deploy.sh` monta el SMB automáticamente si no está montado.
Mount manual: `sudo mount_smbfs '//administrador:cagr$2011@192.168.2.111/c$/cowork_pedidos' /Volumes/cowork_111`

### VPN auto-reconnect
LaunchAgent cada 30s verifica VPN L2TP y reconecta leyendo secreto IPSec de Keychain.
- Instalar: `bash _sync_tools/instalar_vpn_daemon.sh`
- Log: `tail -f /tmp/vpn-reconectar.log`

---

## BASES DE DATOS

| Base | Contenido | INSERT? |
|------|-----------|---------|
| `msgestion01` | CALZALINDO — pedidos, compras, ventas | ✅ Si empresa=CALZALINDO |
| `msgestion03` | H4 SRL — pedidos, compras, ventas | ✅ Si empresa=H4 |
| `msgestionC` | VIEWs combinadas UNION ALL | ❌ NUNCA (error 4406) |
| `msgestion01art` | Artículos compartidos (`articulo`, PK=`codigo`) | ✅ Para alta artículos |
| `omicronvt` | Analítica, agrupadores, vel_real_articulo | ✅ Para tablas analíticas |
| `clz_ventas_sql` | Auth (tabla `auth_user`) | Solo para auth |

### Campos que confunden
- Artículos: PK es `codigo` (NO `numero`, NO `articulo`)
- Stock: campo `stock_actual` (NO `cantidad`) en `msgestionC.dbo.stock`
- Proveedor: campo `denominacion` (NO `nombre_proveedor`)
- Compras2: `monto_general` y `concepto_gravado` (NO existe `importe_neto`)
- Ventas: EXCLUIR siempre codigo 7 y 36 (remitos internos)

---

## CONVENCIONES DE PEDIDO (pedico2 / pedico1)

- `codigo=8, letra='X', sucursal=1, estado='V', usuario='COWORK'`
- `numero` y `orden`: MAX+1 auto-incremental (se calcula al insertar)
- pedico1/pedico2 son **COMPARTIDAS** entre msgestion01 y msgestion03
- La diferenciación por empresa ocurre al facturar (compras2), no en el pedido
- Routing: `get_tabla_base("pedico2", "H4")` → `MSGESTION03.dbo.pedico2`
- Routing: `get_tabla_base("pedico2", "CALZALINDO")` → `MSGESTION01.dbo.pedico2`
- **LECCIÓN CRÍTICA**: DELETE de pedico en una base borra de AMBAS (son compartidas). Nunca borrar para "limpiar duplicados".

---

## PROVEEDORES CONFIGURADOS (config.py)

| # | Proveedor | Empresa | Marca | Notas |
|---|-----------|---------|-------|-------|
| 668 | ALPARGATAS S.A.I.C. | (default H4) | TOPPER 314 | desc 6%, util1 98.9% |
| 104 | "EL GITANO" - GTN | CALZALINDO | GTN 104 | 100% base 01 |
| 594 | VICBOR SRL | (default H4) | Multi-marca | WAKE desc 20%, Atomik var, Massimo 10%, Bagunza 6% |
| 656 | DISTRINANDO DEPORTES | (default H4) | REEBOK 513 | desc viene en factura |
| 561 | Souter S.A. (RINGO) | H4 | CARMEL 294 | sin descuento |
| 614 | CALZADOS BLANCO S.A. | H4 | DIADORA 675 | 97% base 03 |

---

## REGLA CLAVE: ANÁLISIS DE QUIEBRE DE STOCK

**EL USUARIO INSISTE**: Siempre que se calcule velocidad de venta para proyectar compras, PRIMERO analizar el quiebre.

### Método
1. Obtener `stock_actual` de `msgestionC.dbo.stock` para los artículos
2. Obtener ventas mensuales de `ventas1` (excluir codigo 7,36) últimos 12 meses
3. Obtener compras mensuales de `compras1` (operacion='+') últimos 12 meses
4. Reconstruir stock mes a mes HACIA ATRÁS desde el stock actual:
   - `stock_mes_anterior = stock_mes + ventas_mes - compras_mes`
5. Mes con `stock_inicio <= 0` → **QUEBRADO**
6. Velocidad REAL = ventas solo de meses NO quebrados / cantidad de meses NO quebrados
7. La velocidad aparente (total ventas / total meses) SUBESTIMA la demanda real

### Implementaciones (4 copias de la misma lógica)
| Ubicación | Tech | Uso |
|-----------|------|-----|
| `app_reposicion.py::analizar_quiebre_batch()` | pyodbc | Streamlit real-time |
| `_scripts_oneshot/crear_tabla_vel_real.py` | pyodbc | Genera tabla materializada |
| `calzalindo_informes_DEPLOY/models/vel_real.py` | web2py DAL | Controllers web2py |
| `calzalindo_informes_DEPLOY/models/funciones_ranking.py` | web2py DAL | Ranking module |

---

## ESTADO REAL — 23 de marzo de 2026

### ✅ Deployado y funcionando en producción (111)

| Componente | Estado | Notas |
|-----------|--------|-------|
| Pipeline pedidos (paso1-6) | ✅ Funcionando | INSERT pedico2+pedico1 con routing |
| config.py (6 proveedores) | ✅ Funcionando | Alpargatas, GTN, VICBOR, Distrinando, Souter, Calzados Blanco |
| Web2py calzalindo_informes | ✅ Deployado | calce_financiero, ranking, reportes, remitos |
| Vista v_pedidos_cumplimiento | ✅ Aplicada | 1235 filas en cache |
| Serie secuencial YYMM0001 | ✅ En reportes.py | Serie condicional: YYMM si CLZ, ' ' si H4 |
| UPSERT pedico1_entregas | ✅ Aplicado | IF EXISTS/UPDATE/ELSE/INSERT |
| Fix stock serie cleanup | ✅ Ejecutado | Remito WB, valijas, series '2603' |

### ✅ Pedidos insertados en producción

| Pedido | Fecha | Script | Pares | Monto | Empresa |
|--------|-------|--------|-------|-------|---------|
| KNU GTN | 7 mar | `insertar_knu_gtn.py` | 124 | $2,728,000 | CALZALINDO |
| CARMEL RINGO #134069 | 9 mar | `insertar_carmel_ringo.py` | 30 | $1,130,100 | H4 |
| DIADORA #1134068 | 12 mar | `insertar_diadora.py` | 48 | — | H4 |
| ATOMIK RUNFLEX #1134069 | 12 mar | `insertar_atomik_runflex.py` | 120 | — | H4 |

### ⚠️ Desarrollado en Mac, NO deployado al 111

| Componente | Estado | Acción necesaria |
|-----------|--------|------------------|
| `vel_real_articulo` (tabla omicronvt) | SQL generado 21-mar (`vel_real_articulo_20260321.sql`, ~2400 INSERTs) | Ejecutar SQL en 111. **Verificado: tabla NO existe en producción** |
| calce_financiero.py (vel_real) | Código listo, hace try/except si tabla no existe | `./deploy.sh web2py` |
| ranking_consolidado.py (vel_real) | Código listo, fallback a DAL si tabla no existe | `./deploy.sh web2py` |
| crear_presupuesto_industria.sql | Usa vel_real_articulo con OUTER APPLY + ISNULL fallback | Ejecutar en 111 |
| app_reposicion.py v2 | vel_real en dashboard, GMROI, Rotación, curva talles corregida | Corre en Mac, no requiere deploy |
| Tests app_reposicion (`_tests/`) | 40/40 PASS (21-mar) | Corren en Mac |
| Curva ideal omicron → app_reposicion | 3 funciones extraídas de omicron_informes_controller | En Mac |
| Auto-detección proveedor en app_carga | Por nombre archivo + por códigos artículo | `./deploy.sh scripts` |
| crear_tabla_vel_real.py | Script generador, listo | `./deploy.sh scripts` + ejecutar en 111 |

### ❌ Pendiente de desarrollo/ejecución

| Tarea | Detalle |
|-------|---------|
| `crear_tabla_asignacion.py` | Crear `proveedor_asignacion_base` (359 registros) en 111 |
| `fix_capas_2_y_3.sql` | Sistema 3 capas de talles — ejecutar en 111 |
| Fix `construir_sinonimo()` | En `paso8_carga_factura.py` para Reebok (sinónimo 12 dígitos) |
| Probar INSERT FLEXAGON | FLEXAGON ENERGY TR 4 por app Streamlit end-to-end |
| Confirmar `descuento_1` | Que se grabe con bonificación de factura |
| GTN Resto | ~530 pares pendientes de los 656 del pedido 2 meses |
| `recrear_diadora_1134068.py` | Restaurar pedido Diadora si fue borrado por incidente DELETE |
| Facturador TN modo real | Medio pago TN, sucursal/depósito, webhook, SKUs sin match |

---

## REGLAS DE NEGOCIO

1. **Empresas**: H4 SRL (formal, base 03) y CALZALINDO/ABI (informal, base 01). Artículos compartidos en msgestion01art.
2. **Pedidos compartidos**: pedico1/pedico2 son idénticas en ambas bases. La asignación empresa se hace al facturar (compras2).
3. **Routing inserción**: usar tabla `proveedor_asignacion_base` (cuando se cree) o lógica en config.py por ahora.
4. **Descuentos**: `descuento` = proveedor fijo; `descuento_1` = bonificación factura; `descuento_2` = otro. Desc combinado: `1 - (1 - desc_linea/100) × (1 - desc_bonif/100)`.
5. **Talles Reebok**: US + 32 = AR hombres (US 8 = AR 40). Enteros solamente para running/training.
6. **Períodos**: Zapatería usa OI/PV; Deportes usa H1/H2.
7. **Remitos código 7 y 36**: EXCLUIR siempre de ventas.
8. **INSERT**: NUNCA en vistas de msgestionC (error 4406). Directo a msgestion01 o msgestion03.
9. **SQL Server 2012 RTM**: NO soporta TRY_CAST. Usar ISNUMERIC + CAST.
10. **ANÁLISIS DE QUIEBRE (OBLIGATORIO)**: SIEMPRE reconstruir stock mes a mes hacia atrás. Meses con stock=0 al inicio → "QUEBRADO", NO contar en velocidad.
11. **Running = MACRAME**: grupo="15", NUNCA grupo="5" (PU/Sintético).
12. **Marca ≠ Proveedor**: Buscar siempre el código real en tabla `marcas`. Ej: Diadora=675 (no 614), Atomik=594.
13. **Stock negativo CLZ**: Causado por comprobante código 95 "SOLICITUD A DEPOSITO" (usuario POS). Existe solo en CLZ, activo desde ago-2020. El consolidado (msgestionC) compensa correctamente.
14. **Serie remitos**: H4 usa serie=' '. CALZALINDO usa serie=YYMM ('2603'). Stock total = SUM(todas las series).

---

## ESTRUCTURA DE CARPETAS

```
cowork_pedidos/
├── CLAUDE.md                          ← ESTE ARCHIVO (fuente única de verdad)
├── ESTADO_PROYECTOS.md                ← estado alto nivel TODOS los proyectos
├── INSTRUCCIONES_COWORK.md            ← guía paso a paso pipeline
├── paso*.py, config.py, app_*.py      ← PIPELINE CORE (raíz)
├── requirements.txt
├── tests/                             ← tests pipeline
├── _tests/                            ← tests app_reposicion (40 tests)
├── _scripts_oneshot/                  ← scripts inserción/fix puntuales
├── _excel_pedidos/                    ← Excel/docs de referencia
├── _informes/
│   ├── calzalindo_informes_DEPLOY/    ← web2py (controllers, models, views, sql)
│   ├── objetivos-luciano/
│   └── *.xlsx (productividad, ranking)
├── _tiendanube/                       ← web, SEO, conversión
├── _sync_tools/                       ← deploy.sh, watch_sync.sh, VPN daemon
├── _freelance/                        ← sistema vendedor freelance
├── _docs/                             ← docs referencia
├── _archivo/                          ← histórico / no activo
├── multicanal/                        ← TiendaNube, ML, facturador, canales
├── valijas/                           ← proyecto valijas GO
└── clz_wpu/                           ← web push notifications
```

### Archivos clave

| Archivo | Función |
|---------|---------|
| `config.py` | Conexión SQL + 6 proveedores + `calcular_precios()` |
| `paso4_insertar_pedido.py` | INSERT pedico2+pedico1 con routing empresa→base |
| `app_carga.py` | Streamlit: carga facturas/pedidos con OCR |
| `app_reposicion.py` | Streamlit: reposición con quiebre, waterfall, GMROI |
| `app_h4.py` | Streamlit: dashboard principal H4 |
| `ocr_factura.py` | Parser OCR PDFs (fitz + pdfplumber) |
| `_sync_tools/deploy.sh` | Deploy Mac→111 (scripts y/o web2py) |

---

## CÓMO ARRANCAR UNA SESIÓN NUEVA

1. Leer este archivo (CLAUDE.md)
2. Si el usuario quiere trabajar otro proyecto → leer `ESTADO_PROYECTOS.md`
3. **NO reescribir .py sin leerlos primero** — los fixes ya están aplicados
4. INSERT solo via Python en el 111 (NUNCA via MCP sql-replica)
5. Toda consulta SELECT va por MCP sql-replica
6. Para proyección de compras: SIEMPRE hacer análisis de quiebre antes de calcular velocidad

---

## HISTORIAL DE CAMBIOS (resumen)

| Fecha | Qué se hizo |
|-------|------------|
| 21 mar | Testing automático app_reposicion: 3 suites, 40 tests, runner con reporte |
| 20 mar | Modelo reposición v2: fix vel_real en dashboard, GMROI, Rotación, curva talles con quiebre |
| 20 mar | Curva ideal extraída de omicron → app_reposicion (3 funciones) |
| 20 mar | VPN L2TP auto-reconnect daemon + fix secreto IPSec |
| 20 mar | Overnight: refresh_token_ml.py, facturador_tn.py revisado, publicar_batch() |
| 15 mar | App_carga: auto-detección proveedor por archivo y por códigos artículo |
| 14 mar | Diagnóstico stock negativo CLZ (código 95/POS), análisis outdoor escasez |
| 12 mar | DIADORA 48p + ATOMIK RUNFLEX 120p insertados. Fix marca Diadora. Incidente DELETE pedico |
| 12 mar | Mejoras UI pedidos: sinónimo/talle en detalle, filtros, serie YYMM, UPSERT entregas |
| 10 mar | Fix serie/stock en remito_crear(). Vista v_pedidos_cumplimiento aplicada |
| 9 mar | CARMEL RINGO 30p insertado. Análisis quiebre devastador (87% quebrado) |
| 7 mar | KNU GTN 124p insertado. Análisis supplier→base (359 proveedores). Sync Mac↔111 |
| 5-6 mar | Sistema de talles 3 capas (fix_capas_2_y_3.sql — NO ejecutado) |
| Previo | Pipeline pasos 1-6, OCR, proyección GTN, deploy web2py base |

> Detalle completo de sesiones anteriores: `_archivo/BITACORA_DESARROLLO.md`
