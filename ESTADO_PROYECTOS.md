# ESTADO DE PROYECTOS — H4 / Calzalindo
## Archivo maestro para sesiones Cowork

> **INSTRUCCIÓN PARA CLAUDE**: Leer este archivo PRIMERO en cada sesión nueva.
> Luego leer el archivo de detalle del proyecto que el usuario quiera trabajar.
> Al CERRAR cada sesión, actualizar este archivo con los cambios.

> Última actualización: 9 de marzo de 2026

---

## PROYECTOS ACTIVOS

### 1. 🟡 SISTEMA VENDEDOR FREELANCE
- **Objetivo**: Sistema omnicanal para vendedores freelance con atribución, liquidación, panel personal y dashboard gerencial
- **Stack**: FastAPI + Python 3.14 + pyodbc + ODBC Driver 17 + SQL Server
- **Arquitectura**: App en .112:8001 → DB en .111. Convive con web2py en .111:8000
- **Estado**: Código corregido y listo para deploy. NO deployado al .112 todavía.
- **Fixes aplicados (23-mar-2026)**:
  - [x] Auth thread-safe con threading.Lock en sesiones
  - [x] Auth checks en todos los endpoints de vendedor (admin ve todo, vendedor solo lo suyo)
  - [x] Credenciales MySQL movidas a config.py (ya no hardcodeadas en auth.py)
  - [x] Templates robustos para data vacía (home, panel_vendedor, admin_dashboard)
  - [x] SQL seed: 30 productos catálogo comercial (`sql/002_seed_data.sql`)
  - [x] Alta Mati: viajante 755 RODRIGUEZ MATIAS como V755 (`sql/003_alta_mati.sql`)
  - [x] Script maestro SQL: `sql/RUN_ALL.sql` (tablas + seed + alta Mati)
  - [x] Deploy scripts: `deploy_todo.sh`, `start_freelance.bat`, `install_service.bat`
- **Para deployar (desde Mac)**:
  1. `cd ~/Desktop/cowork_pedidos/_freelance/src && bash deploy_todo.sh`
  2. En .111 SSMS: ejecutar `C:\cowork_pedidos\_freelance\src\sql\RUN_ALL.sql` en omicronvt
  3. En .112: `cd C:\calzalindo_freelance && start_freelance.bat`
  4. Probar login con fcalaianov@calzalindo.com.ar
  5. Probar panel vendedor con código V755 (Mati)
- **Qué falta módulos**:
  - [ ] M1: Catálogo Comercial — CRUD listo, seed 30 productos listos, falta deploy
  - [ ] M3: Generador Contenido Omnicanal (IG/WA/ML/TN templates)
  - [ ] M5: Facturación Dual (borradores factura C)
  - [ ] APIs externas: Tiendanube, WhatsApp Business, Instagram Graph, Facebook
  - [x] Configurar uvicorn como servicio Windows en .112 — `install_service.bat` con NSSM
- **Archivos clave**: `_freelance/src/` (toda la carpeta)
- **Detalle**: leer `_freelance/ARQUITECTURA_SISTEMA_VENDEDOR_FREELANCE.md`
- **Correr**: en .112: `cd C:\calzalindo_freelance && start_freelance.bat`

### 2. 🟡 CARGA AUTOMÁTICA DE PEDIDOS + PROYECCIÓN
- **Objetivo**: Cargar notas de pedido/facturas desde PDF → SQL Server + proyección de compras
- **Estado**: Pipeline funcionando, KNU GTN insertado en producción, sync Mac↔111 operativo
- **Logros recientes**:
  - [x] Pedido KNU GTN confirmado e insertado en producción (124 pares, $2.7M)
  - [x] Análisis supplier→base: 359 proveedores clasificados (SOLO_01/SOLO_03/SPLIT)
  - [x] Descubrimiento: pedico1/pedico2 compartidas entre bases
  - [x] Sync Mac↔111 funcionando (mount SMB + watcher automático)
  - [x] Proyección temporada GTN: pedido 2 meses 656 pares, $14.68M
  - [x] OCR Distrinando funcionando
  - [x] Análisis CARMEL RINGO con ajuste por quiebre: 30 pares CANELA T41-44, $1.13M
  - [x] `insertar_carmel_ringo.py` creado y verificado
  - [x] RINGO (Souter 561) agregado a config.py como proveedor
- **Qué falta para cerrar**:
  - [x] ⚡ Pedido CARMEL RINGO insertado en producción — #134069, 30 pares, $1.13M
  - [ ] Ejecutar `crear_tabla_asignacion.py` en 111 (tabla proveedor→base)
  - [ ] Ejecutar `fix_capas_2_y_3.sql` en 111 (sistema 3 capas de talles)
  - [ ] Probar INSERT FLEXAGON ENERGY TR 4 por la app Streamlit
  - [ ] Confirmar que `descuento_1` se grabe con bonificación de factura
  - [ ] Insertar resto del pedido GTN (~530 pares pendientes de los 656)
  - [ ] Fix cabecera OCR fitz (cosmético)
- **Archivos clave**: `app_carga.py`, `ocr_factura.py`, `config.py`, `paso4_insertar_pedido.py`
- **Detalle**: leer `BITACORA_DESARROLLO.md`
- **Correr app**: `cd ~/Desktop/cowork_pedidos && streamlit run app_carga.py`
- **Sync**: `sudo ~/Desktop/cowork_pedidos/_sync_tools/watch_sync.sh &`

### 3. 🟡 DEPLOY PRODUCTIVIDAD E INCENTIVOS
- **Objetivo**: Módulo de productividad y objetivos para vendedores en web2py
- **Estado**: Código listo, deploy pendiente
- **Qué falta**: Copiar archivos al server 111, actualizar menu.py
- **Detalle**: leer `_informes/DEPLOY_PRODUCTIVIDAD.md`

### 4. 🟠 CONVERSIÓN WEB — calzalindo.com.ar
- **Objetivo**: Pasar de 0 conversiones a ventas reales con Google Ads
- **Estado**: Campaña Ads activa (6.42% CTR, 0 conversiones). Diagnóstico hecho.
- **Qué falta**: Implementar fixes en la web (CTA, checkout, tracking)
- **Detalle**: leer `_tiendanube/DIAGNOSTICO_CONVERSION_WEB.md`

### 5. 🟢 DESCRIPCIONES STARFLEX (Tiendanube)
- **Objetivo**: Descripciones SEO para productos en Tiendanube
- **Estado**: Textos escritos, falta copiarlos a la plataforma
- **Detalle**: leer `_tiendanube/DESCRIPCIONES_PRODUCTO_STARFLEX.md`

### 6. 🟢 ESTRATEGIA VALIJAS GO
- **Objetivo**: Liquidar 230 sets de valijas en 30 días
- **Estado**: Estrategia armada, falta ejecutar campaña WhatsApp
- **Detalle**: leer `valijas/ESTRATEGIA_VALIJAS_GO.md`

---

## INFRAESTRUCTURA COMPARTIDA

| Recurso | Dirección | Notas |
|---------|-----------|-------|
| SQL Server producción | 192.168.2.111 | INSERT/UPDATE, web2py, auth tables |
| SQL Server réplica/app freelance | 192.168.2.112 | SELECT, MCP, Metabase, FastAPI :8001 |
| Web2py | 192.168.2.111:8000 | Dashboard pedidos/remitos |
| FastAPI Freelance | 192.168.2.112:8001 | Sistema vendedor freelance |
| Streamlit | localhost:8501 | App carga facturas (Mac local) |
| Tiendanube | calzalindo.com.ar | E-commerce |

### Servidores — Detalle

**192.168.2.111 (PRODUCCIÓN)** — Hostname: DELL-SVR
- SQL Server 2012 RTM — ⚠️ NO soporta TRY_CAST
- Python: `py -3` → 3.13 (CORRECTO). `python` → 2.7 (NO USAR)
- Bases: msgestionC, msgestion01, msgestion03, msgestion01art, omicronvt, clz_ventas_sql
- Auth centralizada: `clz_ventas_sql.dbo.auth_user` (hash PBKDF2 web2py)
- Scripts pedidos: `C:\cowork_pedidos\` (sync desde Mac)
- SMB: `//administrador:cagr$2011@192.168.2.111/c$/cowork_pedidos`

**192.168.2.112 (APP FREELANCE)**
- Hostname: DATASVRW
- Windows 10/Server 2019 (build 17763.316)
- Python 3.13 (Program Files) + Python 3.14.3 (AppData\Local — USAR ESTE)
- Python 3.14 path: `C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe`
- ODBC Driver 17 for SQL Server instalado
- pyodbc funciona ✅ — pymssql NO conecta ❌ (error TDS "Adaptive Server connection failed")
- App folder: `C:\calzalindo_freelance\`
- Dependencias instaladas: fastapi, uvicorn, pyodbc, jinja2, pydantic-settings, Pillow

### Credenciales
- **DB**: usuario `am`, pwd `dl` (en `config.py`)
- **Auth users**: tabla `clz_ventas_sql.dbo.auth_user`, hash `pbkdf2(1000,20,sha512)$salt$hash`
- **Salt**: web2py usa el salt como STRING UTF-8 (no bytes.fromhex) — IMPORTANTE para verificación PBKDF2

---

## DECISIONES TÉCNICAS TOMADAS

1. **pyodbc en vez de pymssql** en .112 — pymssql no puede conectar al SQL Server 2012 de .111 (error TDS). pyodbc con ODBC Driver 17 funciona perfecto.
2. **FastAPI en .112, no en .111** — para no afectar producción. DB sigue en .111.
3. **Auth centralizada** — contra `clz_ventas_sql.dbo.auth_user` (las mismas tablas de Luciano/web2py). No crear sistema de auth paralelo.
4. **Modelo freelance**: vendedor factura al CLIENTE (no a H4). Más robusto legalmente.
5. **Fee 5% STD / 8% PREMIUM** con bonus por franja horaria (2% off-peak).

---

## PROTOCOLO DE SESIÓN

### Al iniciar:
1. Leer este archivo (`ESTADO_PROYECTOS.md`)
2. Preguntar al usuario qué proyecto quiere trabajar
3. Leer el archivo de detalle de ese proyecto
4. Retomar desde el último punto pendiente

### Al cerrar:
1. Actualizar los checkboxes de este archivo
2. Actualizar `BITACORA_DESARROLLO.md` si se tocó código
3. Anotar cualquier bug nuevo o decisión tomada

### Si la sesión se corta (se clava / se queda sin contexto):
1. La nueva sesión lee este archivo y retoma
2. NO reescribir archivos .py sin primero verificar qué hay en disco (leer antes de escribir)
3. Los fixes de OCR ya están aplicados — no volver atrás
4. En .112: db.py DEBE usar pyodbc (NO pymssql) — ver sección Decisiones Técnicas
