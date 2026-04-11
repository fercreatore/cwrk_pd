# CLAUDE.md — Fuente Única de Verdad
## Proyecto Integral ERP — H4 / CALZALINDO
> Última actualización: 30 de marzo de 2026

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

### Infraestructura Externa (Guille) — 200.58.109.125

Servidor VPS administrado por Guille. Corre servicios orientados al cliente final.

- **PostgreSQL** (puerto 5432):
  - `clz_productos` — Catálogo productos normalizado, embeddings pgvector, imágenes. Sync parcial desde ERP (ETL externo). **Fuente de datos para multicanal/ sync stock/precios**
  - `clz_clientes` — Tracking bot Linda (conversaciones, búsquedas, aprendizajes)
- **MySQL** (puerto 3306):
  - `clz_ventas` — Terceros (réplica parcial ERP) + programa puntos "Calzalindo Pasos"
- **Servicios**:
  - **calzalindo-admin** (Node.js, :3000) — Panel admin catálogo, sync TN
  - **clz-bot** (Python/FastAPI, :8000) — Bot "Linda" ventas WhatsApp (GPT-4o + pgvector)
  - **Chatwoot** — chat.calzalindo.com.ar — Inbox omnicanal WhatsApp/web
  - **n8n** — n8n.calzalindo.com.ar — Automatizaciones + hosting imágenes productos
- **MCP postgres-clz**: Configurado, apunta a clz_productos
- **Credenciales**: En `.env` de cada proyecto (NO en config.py del ERP)

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

## ESTADO REAL — 11 de abril de 2026

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
| multicanal/pg_productos.py | ✅ Creado | Lectura stock/precios desde PG, tracking publicaciones SQLite |
| sync_stock.py mejorado | ✅ Listo | --fuente pg/erp, --depositos param, --despublicar |
| sync_precios.py mejorado | ✅ Listo | --fuente pg/erp, precio_oferta/promotional_price |
| tiendanube.py mejorado | ✅ Listo | eliminar_producto(), crear_imagen(), precio_oferta |

### ✅ Pedidos insertados en producción

| Pedido | Fecha | Script | Pares | Monto | Empresa |
|--------|-------|--------|-------|-------|---------|
| KNU GTN | 7 mar | `insertar_knu_gtn.py` | 124 | $2,728,000 | CALZALINDO |
| CARMEL RINGO #134069 | 9 mar | `insertar_carmel_ringo.py` | 30 | $1,130,100 | H4 |
| DIADORA #1134068 | 12 mar | `insertar_diadora.py` | 48 | — | H4 |
| ATOMIK RUNFLEX #1134069 | 12 mar | `insertar_atomik_runflex.py` | 120 | — | H4 |
| Timmis Folclore Ent1 #1134086 | 25-26 mar | `insertar_timmis_folclore_ent1.py` | 143 | $3,470,000 | CALZALINDO |
| Zotz Folclore #1134087 | 25-26 mar | `insertar_timmis_folclore_ent1.py` | 132 | $3,200,000 | CALZALINDO |
| GO CZL Folclore #1134088 | 25-26 mar | `insertar_timmis_folclore_ent1.py` | 133 | $3,230,000 | CALZALINDO |
| **Total Folclore OI26** | | | **408** | **$9,890,000** | **CALZALINDO** |

### ✅ Deployado noche del 25-mar-2026

| Componente | Estado | Detalles |
|-----------|--------|----------|
| `vel_real_articulo` (omicronvt) | ✅ **46,794 filas en producción** | Ejecutado desde Mac via pyodbc, SQL del 23-mar |
| `proveedor_asignacion_base` (omicronvt) | ✅ **1,238 proveedores** | 1,090 H4 + 148 CALZALINDO, con overrides manuales |
| `fix_capas_2_y_3` (msgestion01) | ✅ **aliases_talles: 58, regla_talle_subrubro: 57** | Sistema 3 capas de talles completo |
| calce_financiero.py + ranking (vel_real) | ✅ Deployado | `./deploy.sh web2py` |
| Scripts + pipeline + oneshot | ✅ Deployado (2x) | Incluye fix descuento en paso4 |
| Fix `descuento_reng1/reng2` en paso4 | ✅ Aplicado | INSERT pedico1 ahora graba descuento proveedor + bonificación factura |
| `construir_sinonimo()` Reebok | ✅ Ya funciona | Maneja prefijos RBK, códigos largos, últimos 5 dígitos |

### PEDIDOS INVIERNO 2026 — Estado al 30-mar

| Proveedor | Prov# | Pares | Monto s/IVA | Estado |
|-----------|-------|-------|-------------|--------|
| Floyd (medias, docenas) | 641 | 4,908 (409 doc) | $7.37M | ❌ Pendiente INSERT |
| Atomik/VICBOR | 594 | 1,078 | $45.5M | ❌ Pendiente INSERT |
| El Faraón | 118 | 828 | — | ❌ Pendiente INSERT |
| DasLuz | — | 197 | $2.97M | ❌ Pendiente INSERT |
| Action Team | — | 103 | $2.6M | ❌ Pendiente INSERT |
| John Foos (Distrigroup) | 860 | 88 | $4.2M | ❌ Pendiente INSERT |
| Escorpio | — | 60 | $515K | ❌ Pendiente INSERT |
| GTN Campus Negro | 104 | 26 | $572K | ❌ Pendiente INSERT |
| **Subtotal pendientes** | | **~7,288** | **~$63.7M** | |
| OLK/Olympikus (Global Brands) | 722 | 504 | — | ⏳ Esperar confirmación Cecchini |

**Notas imputación**: Floyd cuenta en DOCENAS (×12). Atomik usa códigos alfa VICBOR que matchean sinónimos ERP. Escorpio usa talles dobles (23/24, 25/26, etc.).

### ❌ Pendiente de desarrollo/ejecución

| Tarea | Detalle |
|-------|---------|
| Motor autocompensación inter-depósito | F1 completa en Mac (no deployada al 111) — módulos autorepo/ + SQL scripts + tests. Pendiente: crear tablas en 111, shadow mode 2 semanas, calibración |
| GTN Campus Negro | 26 pares, prov 104, msgestion01 — script en preparación |
| Pedidos invierno 2026 | 7 proveedores, ~7,288 pares — ver tabla arriba |
| OLK/Olympikus | 504 pares — esperar confirmación Cecchini (proveedor GLOBAL BRANDS prov 722) |
| Vel_real sync | Actualizar copias #2/#3/#4 al algoritmo v3 (7 gaps documentados en AUDIT_VEL_REAL_20260325.md) |
| Presupuesto industria | crear_presupuesto_industria.sql — usa vel_real_articulo (tabla existe, 46,794 filas) |
| Sprint 1 reposición | Motor decisión unificado + auto-INSERT desde UI + botón "Confirmar Pedido" |
| Sprint 2 | Catálogo auto-parse + sync 4 copias vel_real + deploy al 112 |
| Sprint 3 | Macro variables (BCRA/INDEC APIs) + Holt-Winters para ítems A/B |
| Sprint 4 | Feedback loop auto-calibración |
| Sprint 5 | Conector XL (app.xl.com.ar) |
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
├── autorepo/                          ← motor de autocompensación inter-depósito (F1 solo sugiere)
└── clz_wpu/                           ← web push notifications
```

### Archivos clave

| Archivo | Función |
|---------|---------|
| `config.py` | Conexión SQL + 6 proveedores + `calcular_precios()` |
| `paso4_insertar_pedido.py` | INSERT pedico2+pedico1 con routing empresa→base |
| `app_carga.py` | Streamlit: carga facturas/pedidos con OCR |
| `app_reposicion.py` | Streamlit: reposición con quiebre, waterfall, GMROI (10 tabs) |
| `app_h4.py` | Streamlit: dashboard principal H4 |
| `ocr_factura.py` | Parser OCR PDFs (fitz + pdfplumber) |
| `_sync_tools/deploy.sh` | Deploy Mac→111 (scripts y/o web2py) |

### app_reposicion.py — Tabs (10)

1. Mapa Surtido
2. Dashboard
3. Waterfall
4. Optimizar Compra (ROI engine)
5. Curva Talle
6. Canibalización
7. Emergentes
8. Nichos
9. Armar Pedido
10. Historial

### app_reposicion.py — Constantes clave

| Constante | Descripción |
|-----------|-------------|
| `PG_CONN_STRING` | PostgreSQL pgvector para embeddings de sustitutos |
| `RUBRO_GENERO` | Mapping rubro → género (H/M/N/U) |
| `EXCL_MARCAS_GASTOS` | `'(1316,1317,1158,436)'` — excluir de todas las queries comerciales |
| `SUBRUBRO_TEMPORADA` | Mapping 20 subrubros → ventana compra/venta OI/PV |
| `NICHOS_PREDEFINIDOS` | Nichos estacionales predefinidos (COMUNION, etc.) |
| `BACKTESTING_CALIBRACION` | Parámetros calibración demanda |
| `ESTACIONALIDAD_MENSUAL` | Factores estacionales mensuales por subrubro |

### app_reposicion.py — Funciones principales (al 30-mar)

| Función | Descripción |
|---------|-------------|
| `cargar_subrubro_desc()` | Descripción de subrubros |
| `cargar_mapa_surtido()` | Mapa completo artículo→subrubro→temporada |
| `cargar_piramide_precios()` | Distribución de precios por segmento |
| `get_pg_conn()` | Conexión PostgreSQL |
| `buscar_sustitutos_embedding()` | Sustitutos via pgvector cosine similarity |
| `buscar_sustitutos_activos_con_stock()` | Sustitutos con stock real |
| `presupuesto_pares()` | Presupuesto auto del mismo período año anterior |
| `distribucion_genero()` | Split H/M/N por subrubro |
| `distribucion_color()` | Distribución colores del catálogo |
| `precio_techo()` | P90 de precios vendidos en el período |
| `curva_talles_real()` | Curva real de ventas por talle |
| `talles_escasez_cronica()` | Talles que siempre faltan (≥2 años) |
| `calcular_curva_ideal()` | Curva ideal de compra por talle |
| `calcular_pedido_modelo()` | Pedido modelo respetando curva ideal |
| `calcular_safety_stock()` | Safety stock Poisson + nivel de servicio |
| `clasificar_abc_xyz()` | Segmentación ABC (ingresos) × XYZ (regularidad) |
| `proyectar_entregas_mensuales()` | Cashflow de entregas por mes |
| `unificar_proveedores()` | Agrupa ventas de mismo producto/distinto proveedor |
| `analizar_nicho_producto()` | Análisis de un nicho específico |
| `detectar_nichos_descubiertos()` | Nichos con demanda pero sin oferta |
| `detectar_nichos_por_subrubro()` | Nichos por subrubro × temporada |
| `es_temporada_compra()` | Bool: ¿es momento de comprar este subrubro? |
| `factor_estacional_subrubro()` | Factor de ajuste estacional por subrubro |

---

## CÓMO ARRANCAR UNA SESIÓN NUEVA

1. Leer este archivo (CLAUDE.md)
2. Si el usuario quiere trabajar otro proyecto → leer `ESTADO_PROYECTOS.md`
3. **NO reescribir .py sin leerlos primero** — los fixes ya están aplicados
4. INSERT solo via Python en el 111 (NUNCA via MCP sql-replica)
5. Toda consulta SELECT va por MCP sql-replica (si disponible) o pyodbc directo
6. Para proyección de compras: SIEMPRE hacer análisis de quiebre antes de calcular velocidad

---

## SI CORRÉS EN EL SERVIDOR 112 (CLAUDE CODE)

Cuando Claude Code corre en `C:\cowork_pedidos\` del 112 (DATASVRW):

### Entorno
- **Python**: `C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe` (3.14)
- **pyodbc**: Funciona con ODBC Driver 17. pymssql NO.
- **Working dir**: `C:\cowork_pedidos\`
- **Streamlit apps**: corren acá (app_carga.py en :8503, app_h4.py en :8502)

### Conexión SQL directa (sin MCP)
El 112 tiene acceso pyodbc a AMBOS servidores:
```python
# Al 111 (producción) — para INSERT y SELECT
import pyodbc
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;DATABASE=msgestionC;"
    "UID=am;PWD=dl;TrustServerCertificate=yes"
)

# Al 112 local (réplica) — solo SELECT
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.112;DATABASE=msgestionC;"
    "UID=am;PWD=dl;TrustServerCertificate=yes"
)
```

### Qué podés hacer directo (sin deploy)
- Editar app_carga.py, app_h4.py → los cambios se ven al recargar Streamlit
- Reiniciar Streamlit: buscar el proceso y reiniciar, o pedir al usuario
- Ejecutar scripts INSERT en el 111 via pyodbc
- Ejecutar SQL directo en el 111 (CREATE TABLE, INSERT, UPDATE)
- Correr tests: `py -3 -m pytest tests/`

### Qué NO podés hacer desde el 112
- Tocar web2py (está en el 111 en `C:\web2py_src\`)
- Ejecutar scripts que requieren estar en el 111 (usar pyodbc remoto en su lugar)

### Restart Streamlit
```cmd
:: Ver procesos Streamlit corriendo
tasklist | findstr streamlit
:: O buscar por puerto
netstat -ano | findstr :8503

:: Reiniciar app_carga
cd C:\cowork_pedidos
C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe -m streamlit run app_carga.py --server.port 8503
```

### Deploy web2py al 111 (desde el 112)
Si necesitás actualizar web2py, copiá los archivos via red:
```cmd
copy /Y _informes\calzalindo_informes_DEPLOY\*.py \\192.168.2.111\c$\web2py_src\applications\calzalindo_informes\
```

---

## HISTORIAL DE CAMBIOS (resumen)

| Fecha | Qué se hizo |
|-------|------------|
| 26-30 mar | Pedidos folclore (Timmis/Zotz/GO CZL) insertados: 408p $9.89M msgestion01 (#1134086-88) |
| 26-30 mar | app_reposicion.py: tab Nichos, detector nichos descubiertos, SUBRUBRO_TEMPORADA, EXCL_MARCAS_GASTOS |
| 26-30 mar | app_reposicion.py: ROI optimizer con horizonte configurable, safety stock Poisson, ABC-XYZ |
| 26-30 mar | app_reposicion.py: 10 tabs, pgvector sustitutos, curva talle real con escasez crónica |
| 26-30 mar | Pedidos invierno 2026: 7 proveedores pendientes INSERT (~7,288 pares, ~$63.7M) |
| 26-30 mar | AUDIT vel_real: 7 gaps documentados, plan sync 4 copias (v3 solo en copy #1) |
| 26-30 mar | OLK/Olympikus 504 pares calculados, esperando confirmación Cecchini |
| 23 mar | resolver_talle.py integrado en pipeline (paso2+paso8). aliases_faltantes.sql ejecutado. Mejoras UX app_carga: proveedor auto-detect, selectbox vacío, default NP. Sección Claude Code 112 en CLAUDE.md |
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
