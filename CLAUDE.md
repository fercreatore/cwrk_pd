# CLAUDE.md — Instrucciones de Proyecto
## Carga Automática de Pedidos + Proyección de Compras — H4 / CALZALINDO

> **LEER PRIMERO**. Luego leer `BITACORA_DESARROLLO.md` para el historial completo.
> Este archivo tiene todo lo necesario para retomar sin preguntar.

---

## QUÉ ES ESTE PROYECTO

Sistema para cargar notas de pedido de compra en el ERP MS Gestión de una cadena de calzado en Venado Tuerto.
Dos razones sociales: **H4 SRL** (formal, base msgestion03) y **CALZALINDO/ABI** (informal, base msgestion01).
Artículos compartidos en `msgestion01art.dbo.articulo`.

Pipeline: análisis de ventas/stock/quiebre → proyección de compras → generación de script Python → ejecución en servidor producción → INSERT en pedico2 (cabecera) + pedico1 (detalle).

También: app Streamlit para OCR de facturas PDF, sistema de talles 3 capas, mapping proveedor→base.

---

## INFRAESTRUCTURA

### Servidores
- **192.168.2.111 (DELL-SVR)** — Producción. SQL Server 2012 RTM. INSERT/UPDATE acá.
  - Python: `py -3` → 3.13 ✅ | `python` → 2.7 ❌
  - Scripts: `C:\cowork_pedidos\`
  - SQL Server 2012 RTM: **NO soporta TRY_CAST** → usar ISNUMERIC + CAST
- **192.168.2.112 (DATASVRW)** — Réplica. MCP sql-replica conecta ACÁ (solo SELECT).
- **Mac local** — Desarrollo. Streamlit, Cowork.

### Credenciales
- SQL Server (pyodbc): `am` / `dl`
- SMB Windows: `administrador` / `cagr$2011`

### Conexión MCP
**`sql-replica`** → `@bytebase/dbhub` apuntando a **192.168.2.111** (producción), base `msgestionC`.
- Requiere `OPENSSL_CONF=/tmp/openssl_legacy.cnf` (OpenSSL 3.x no permite TLS 1.0 de SQL Server 2012)
- `config.py` crea el archivo automáticamente al importarse si no existe
- Usar solo para SELECT. INSERT va por Python en el 111 directamente.

**⚠️ Pendientes de conexión**:
- **112 (réplica)**: el usuario `am/dl` no existe en el 112 — pendiente averiguar credenciales
- **Metabase**: no está corriendo ni en localhost:3000 ni en 112:3000 — pendiente configurar

### Sincronización Mac ↔ 111
**⚠️ NUNCA hacer rsync completo de la carpeta** — son 700MB+ de Excel/ZIP/PDF que no van al server.
Usar SIEMPRE `deploy.sh` que filtra solo código (.py, .sql, .json, .md, .txt, .sh):

```bash
cd ~/Desktop/cowork_pedidos/_sync_tools

# Deploy estándar (scripts pipeline + oneshot)
./deploy.sh scripts

# Ver qué se copiaría sin copiar nada
./deploy.sh dryrun

# Copiar UN archivo pesado puntual
./deploy.sh archivo _excel_pedidos/Pedido.xlsx

# Deploy completo (scripts + web2py)
./deploy.sh todo
```

`deploy.sh` monta el SMB automáticamente si no está montado.
Para montar manualmente: `sudo mount_smbfs '//administrador:cagr$2011@192.168.2.111/c$/cowork_pedidos' /Volumes/cowork_111`
También existe `_sync_tools/watch_sync.sh` (watcher automático polling 3s) — requiere sudo.

---

## BASES DE DATOS

| Base | Contenido | INSERT? |
|------|-----------|---------|
| `msgestion01` | CALZALINDO — pedidos, compras, ventas | ✅ Si empresa=CALZALINDO |
| `msgestion03` | H4 SRL — pedidos, compras, ventas | ✅ Si empresa=H4 |
| `msgestionC` | VIEWs combinadas UNION ALL | ❌ NUNCA (error 4406) |
| `msgestion01art` | Artículos compartidos (`articulo`, PK=`codigo`) | ✅ Para alta artículos |
| `omicronvt` | Analítica, agrupadores | Solo SELECT |
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

---

## PROVEEDORES CONFIGURADOS (config.py)

| # | Proveedor | Empresa | Marca | Notas |
|---|-----------|---------|-------|-------|
| 668 | ALPARGATAS S.A.I.C. | (default H4) | TOPPER 314 | desc 6%, util1 98.9% |
| 104 | "EL GITANO" - GTN | CALZALINDO | GTN 104 | 100% base 01 |
| 594 | INDUSTRIAS AS S.A. | (default H4) | WAKE 746 | desc 20% |
| 656 | DISTRINANDO DEPORTES | (default H4) | REEBOK 513 | desc viene en factura |
| 561 | Souter S.A. (RINGO) | H4 | CARMEL 294 | sin descuento |

---

## REGLA CLAVE: ANÁLISIS DE QUIEBRE DE STOCK

**EL USUARIO INSISTE**: Siempre que se calcule velocidad de venta para proyectar compras, PRIMERO analizar el quiebre.

### Método
1. Obtener `stock_actual` de `msgestionC.dbo.stock` para los artículos
2. Obtener ventas mensuales de `ventas1` (excluir codigo 7,36) últimos 3 años
3. Obtener compras mensuales de `compras1` (operacion='+') últimos 3 años
4. Reconstruir stock mes a mes HACIA ATRÁS desde el stock actual:
   - `stock_mes_anterior = stock_mes + ventas_mes - compras_mes`
5. Mes con `stock_inicio <= 0` → **QUEBRADO**
6. Velocidad REAL = ventas solo de meses NO quebrados / cantidad de meses NO quebrados
7. La velocidad aparente (total ventas / total meses) SUBESTIMA la demanda real

### Ejemplo CARMEL CANELA T42
- Velocidad aparente: ~2 pares/mes
- Quebrado: 34/39 meses (87%!)
- Velocidad REAL (cuando hay stock): **10.8 pares/mes**
- Factor invierno: 22% → velocidad invierno: 2.4/mes

---

## PEDIDOS INSERTADOS Y PENDIENTES

### ✅ KNU GTN — INSERTADO (7 mar 2026)
- Script: `insertar_knu_gtn.py`
- 3 colores, 29 renglones, 124 pares, $2,728,000 @ $22,000/par
- Empresa: CALZALINDO → MSGESTION01

### ✅ CARMEL RINGO — INSERTADO (pedido #134069, 9 mar 2026)
- Script: `insertar_carmel_ringo.py`
- Empresa: H4 → MSGESTION03
- Proveedor: 561 Souter S.A.
- Color: CANELA (top seller 37%)
- 8 renglones (4 talles × 2 modelos), 30 pares, $1,130,100

| Modelo | T41 | T42 | T43 | T44 | Total | Precio |
|--------|-----|-----|-----|-----|-------|--------|
| CARMEL 03 (DET TALON) | 1 | 9 | 8 | 1 | 19 | $34,700 |
| CARMEL 04 (DET CUELLO) | 1 | 4 | 3 | 3 | 11 | $42,800 |

Artículos:
```
CARMEL 03 CANELA: 249885(T41), 249886(T42), 249887(T43), 249888(T44) — $34,700
CARMEL 04 CANELA: 249907(T41), 249908(T42), 249909(T43), 249910(T44) — $42,800
```

Verificación: `SELECT * FROM msgestionC.dbo.pedico1 WHERE numero = 134069 AND empresa = 'H4'` → 8 renglones OK

### ✅ DIADORA (Calzados Blanco) — INSERTADO (pedido #1134068, 12 mar 2026)
- Script: `insertar_diadora.py` + `fix_marca_diadora.py` (corrigió marca/grupo)
- Empresa: H4 → MSGESTION03
- Proveedor: 614 (CALZADOS BLANCO S.A.), Marca: 675 (DIADORA)
- Factura A 0023-00062015, Remito 0024-00066200
- 4 modelos × 5 talles = 20 artículos (360527-360546), 48 pares
- Bonif factura: 5%

| Modelo | Ref | Color | Talles | Pares | Precio |
|--------|-----|-------|--------|-------|--------|
| CONSTANZA | 2116 | NEGRO/NEGRO/PINK | 37-41 | 12 | $36,841.57 |
| PROTON | 2669 | NEGRO/AZUL/CORAL | 36-40 | 12 | $36,841.57 |
| CHRONOS | 2684 | NEGRO/CORAL | 36-40 | 12 | $39,999.47 |
| RIVER | 2690 | NEGRO/PINK | 36-40 | 12 | $31,578.42 |

### ✅ ATOMIK RUNFLEX (VICBOR SRL) — INSERTADO (pedido #1134069, 12 mar 2026)
- Script: `insertar_atomik_runflex.py`
- Empresa: H4 → MSGESTION03
- Proveedor: 594 (VICBOR SRL), Marca: 594 (ATOMIK)
- 2 Facturas: A 00043-00188989 (09/03) + A 00043-00189020 (10/03)
- 4 colores × talles = 23 artículos (360547-360569), 120 pares
- Precio: $54,000, Desc: 50.05% + bonif 6% = 53.05% combinado → costo $25,353

| Color | Tipo | Talles | Pares |
|-------|------|--------|-------|
| CREMA | MUJ | 35-40 | 24 |
| TOPO | HOM | 41-45 | 24 |
| MENTA | MUJ | 35-40 | 24 |
| NEGRO | MUJ | 35-40 | 48 |

### ⚠️ GTN Resto — PENDIENTE
- Del pedido 2 meses (656 pares), solo 124 insertados
- Faltan ~530 pares, ~20 modelos más

---

## PENDIENTES TÉCNICOS

1. Ejecutar `crear_tabla_asignacion.py` en 111 (tabla proveedor→base, 359 registros)
2. Ejecutar `fix_capas_2_y_3.sql` en 111 (sistema 3 capas de talles)
3. Fix `construir_sinonimo()` en `paso8_carga_factura.py` para Reebok
4. Probar INSERT FLEXAGON ENERGY TR 4 por app Streamlit
5. Confirmar que `descuento_1` se grabe con bonificación de factura

---

## ESTRUCTURA DE CARPETAS (reorganizada 9 mar 2026)

```
cowork_pedidos/
├── CLAUDE.md, ESTADO_PROYECTOS.md, BITACORA_DESARROLLO.md  ← docs maestros
├── INSTRUCCIONES_COWORK.md                                  ← guía pipeline
├── paso*.py, config.py, app_carga.py, ocr_factura.py, etc.  ← PIPELINE CORE (raíz)
├── requirements.txt                                         ← dependencias Python
├── tests/                                                   ← tests pedidos
├── .streamlit/                                              ← config Streamlit
├── _scripts_oneshot/                                        ← scripts inserción puntuales
│   ├── insertar_knu_gtn.py, insertar_carmel_ringo.py, insertar_confortable.py
│   ├── set_minimo_confortable.py, alta_masiva_faltantes.py
│   ├── verificar_e_insertar_111.py, crear_tabla_asignacion.py
├── _excel_pedidos/                                          ← Excel/docs de referencia pedidos
│   ├── Pedido GTN.xlsx, TOPPER CALZADO COMPLETO.xlsx
│   └── TOPPER PEDIDO CALZADO COMPLETO.docx
├── valijas/                                                 ← proyecto valijas GO
├── _freelance/                                              ← sistema vendedor freelance
│   ├── src/ (ex calzalindo_freelance/)
│   ├── ARQUITECTURA_SISTEMA_VENDEDOR_FREELANCE.md
│   └── Proyecto vendedor freelance vs empleado de comercio/
├── _informes/                                               ← productividad, objetivos, deploy
│   ├── calzalindo_informes_DEPLOY/
│   ├── objetivos-luciano/
│   ├── importacion/
│   ├── views/, models_deploy/
│   ├── *.xlsx (productividad, ranking, estacionalidad)
│   └── DEPLOY_PRODUCTIVIDAD.md, deploy_productividad.sh
├── _tiendanube/                                             ← web, SEO, conversión
│   ├── DIAGNOSTICO_CONVERSION_WEB.md
│   ├── DESCRIPCIONES_PRODUCTO_STARFLEX.md
│   └── tiendanube_IMPORTAR.csv
├── _sync_tools/                                             ← sync Mac↔111, deploy scripts
│   ├── sync_to_111.sh, watch_sync.sh, sync_from_mac.bat
│   ├── iniciar_carga.sh, instalar_server.bat
│   └── com.cowork.sync-watcher.plist
├── _docs/                                                   ← docs de referencia general
│   ├── PROYECTO_contexto_h4_calzalindo_v3.md
│   └── INSTRUCCIONES_PYODBC.md
└── _archivo/                                                ← histórico / no activo
    ├── Archivo.zip, BITACORA_PROYECTO_CALZALINDO.docx
    ├── charla_insert_notas.rtfd/
    ├── resultado_paso1.txt, insertar_wkc215_en_111.sql
```

## ARCHIVOS PRINCIPALES (proyecto pedidos — raíz)

### Pipeline core (raíz, ejecutar en 111 con `py -3`)
| Archivo | Estado |
|---------|--------|
| `paso4_insertar_pedido.py` | ✅ Core: INSERT pedico2+pedico1 con routing empresa→base |
| `config.py` | ✅ 5 proveedores configurados + `calcular_precios()` |

### Scripts one-shot (`_scripts_oneshot/`, ejecutar en 111)
| Archivo | Estado |
|---------|--------|
| `insertar_knu_gtn.py` | ✅ EJECUTADO — 124 pares GTN |
| `insertar_carmel_ringo.py` | ✅ EJECUTADO — pedido #134069, 30 pares CARMEL CANELA |
| `insertar_diadora.py` | ✅ EJECUTADO — 20 arts Diadora, pedido #1134068, 48 pares |
| `fix_marca_diadora.py` | ✅ EJECUTADO — fix marca 614→675, grupo 5→15 |
| `insertar_atomik_runflex.py` | ✅ EJECUTADO — 23 arts RUNFLEX, pedido #1134069, 120 pares |
| `insertar_confortable.py` | En proceso |
| `crear_tabla_asignacion.py` | Pendiente ejecutar |

### App y OCR
| Archivo | Función |
|---------|---------|
| `app_carga.py` | Streamlit UI — correr en Mac con `streamlit run app_carga.py` |
| `ocr_factura.py` | Parser OCR PDFs (fitz + pdfplumber) |
| `proveedores_db.py` | Proveedores dinámicos desde DB |
| `paso8_carga_factura.py` | Carga factura (backend de app Streamlit) |

### Pipeline completo
`paso1_verificar_bd.py` → `paso2_buscar_articulo.py` → `paso3_calcular_periodo.py` → `paso4_insertar_pedido.py` → `paso5_parsear_excel.py` → `paso6_flujo_completo.py`

### Documentación
- `BITACORA_DESARROLLO.md` — historial detallado de cambios por fecha
- `ESTADO_PROYECTOS.md` — estado alto nivel de TODOS los proyectos (no solo pedidos)
- `INSTRUCCIONES_COWORK.md` — guía paso a paso pipeline

---

## CÓMO ARRANCAR UNA SESIÓN NUEVA

1. Leer este archivo (CLAUDE.md)
2. Si necesitás historial detallado → leer `BITACORA_DESARROLLO.md`
3. Si el usuario quiere trabajar otro proyecto → leer `ESTADO_PROYECTOS.md`
4. **NO reescribir .py sin leerlos primero** — los fixes de OCR, sync, etc. ya están aplicados
5. INSERT solo via Python en el 111 (NUNCA via MCP sql-replica)
6. Toda consulta SELECT va por MCP sql-replica (réplica 112)
7. Para proyección de compras: SIEMPRE hacer análisis de quiebre antes de calcular velocidad
