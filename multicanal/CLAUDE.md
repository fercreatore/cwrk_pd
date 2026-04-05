# CLAUDE.md — multicanal/

## QUÉ HACE
Módulo omnicanal: publicación de productos, sincronización de stock/precios, y facturación automática de ventas desde TiendaNube y MercadoLibre hacia el ERP (MS Gestión).

**Owner**: Fernando.

---

## ARCHIVOS CLAVE

| Archivo | Función |
|---------|---------|
| `canales.py` | Clases base + wrappers API (TN, ML, Meta). Publicación batch con rate limiting |
| `tiendanube.py` | Cliente API TiendaNube (productos, órdenes, store info) |
| `precios.py` | Motor de pricing: costo + comisión + margen → precio por canal |
| `facturador_tn.py` | Órdenes pagadas TN → POST al POS 109 (NO insert directo). SQLite anti-duplicados + log errores |
| `facturador_ml.py` | Ventas ML → INSERT ventas2/ventas1 (tipo B). Dedup con SQLite |
| `sync_stock.py` | Stock ERP → TiendaNube (depósitos 0+1) |
| `sync_stock_ml.py` | Stock ERP → MercadoLibre (multiget API) |
| `sync_precios.py` | Precios ERP → TN (tolerancia <2% ignora) |
| `sync_precios_ml.py` | Precios ERP → ML (premium/clásica) |
| `refresh_token_ml.py` | Auto-refresh OAuth2 ML cada 5h |
| `imagenes.py` | Fotos desde PostgreSQL (`clz_productos`), URLs públicas VPS |
| `reglas_canales.json` | Reglas de pricing por canal (comisión, margen, redondeo) |
| `watcher_estado_web.py` | Publica automáticamente en TN artículos con estado_web='A' |
| `whatsapp_catalogo.py` | Envío de catálogo por WhatsApp (Meta Cloud API + Chatwoot) |
| `publicar_freelance.py` | Genera mensajes WA para vendedores freelance (foto+precio+link) |
| `pg_productos.py` | Queries a PostgreSQL `clz_productos`: stock por depósito, precios (precio + precio_oferta), variantes. Usado por sync_stock y sync_precios como fuente PG |
| `publicaciones.db` | SQLite: registro de publicaciones en TN (watcher) |

---

## CREDENCIALES (NO commitear)

- `tiendanube_config.json` — store_id + access_token
- `mercadolibre_config.json` — access_token, refresh_token, user_id
- SQL Server 111: `am` / `dl`
- PostgreSQL (200.58.109.125): `clz_productos`

---

## CÓMO SE USA

```bash
# Facturar órdenes TN (dry-run)
python -m multicanal.facturador_tn --dry-run

# Solo ABI/CALZALINDO
python -m multicanal.facturador_tn --dry-run --empresa ABI

# Sync stock (PG default, depósitos 0+1)
python -m multicanal.sync_stock --dry-run

# Sync stock con depósitos específicos
python -m multicanal.sync_stock --dry-run --depositos 0,1,2,6,7,8

# Sync stock desde ERP (fallback)
python -m multicanal.sync_stock --dry-run --fuente erp

# Despublicar producto de TN
python -m multicanal.sync_stock --despublicar 12345678

# Sync precios (PG default, incluye precio_oferta)
python -m multicanal.sync_precios --dry-run

# Sync precios desde ERP
python -m multicanal.sync_precios --dry-run --fuente erp

# Refresh token ML
python -m multicanal.refresh_token_ml

# Publicar producto nuevo en TN (dry-run)
python -c "from multicanal.canales import publicar_producto_nuevo; publicar_producto_nuevo('272220004835', dry_run=True)"

# Watcher: publicar automáticamente artículos con estado_web='A'
python -m multicanal.watcher_estado_web --dry-run
python -m multicanal.watcher_estado_web --csr 272220004835 --dry-run
python -m multicanal.watcher_estado_web --loop  # cada 10 min

# WhatsApp catálogo: enviar producto por WA
python -m multicanal.whatsapp_catalogo --csr 272220004835 --preview
python -m multicanal.whatsapp_catalogo --csr 272220004835 --telefono 5493462672330

# Freelance: generar mensaje para vendedor
python -m multicanal.publicar_freelance --csr 272220004835
python -m multicanal.publicar_freelance --csr 272220004835 --enviar 5493462672330
```

---

## Fuentes de datos

### PostgreSQL clz_productos (default)
Fuente principal para sync stock y precios. Base `clz_productos` en 200.58.109.125:5432.
- Stock: tabla `producto_variante_stock` (por depósito parametrizable)
- Precios: tabla `producto_variantes` (precio + precio_oferta)
- Conexión: via `PG_CONN_STRING` importado de `imagenes.py`
- Ventaja: misma fuente que calzalindo-admin y clz-bot, evita pisarse

### ERP SQL Server (fallback)
Fuente original, sigue disponible con `--fuente erp`.
- Stock: `msgestionC.dbo.stock` depósitos 0+1
- Precios: `msgestion01art.dbo.articulo.precio_costo` + `precios.py`
- Conexión: pyodbc a 192.168.2.111

---

## Tracking de publicaciones

SQLite `publicaciones.db` tabla `tn_sync`:
- Registra qué productos se publicaron a TN
- Guarda variant_map (mapeo local→TN)
- Timestamps de último sync stock/precio
- Tag `sync:cowork` para identificar origen

---

## CONEXIÓN CON PROYECTO PRINCIPAL

- Comparte acceso a `msgestion01` (CALZALINDO), `msgestion03` (H4), `msgestion01art` (artículos)
- Usa mismo patrón de routing `get_tabla_base(tabla, empresa)`
- Lee stock de `msgestionC.dbo.stock`
- INSERT va directo al 111 via pyodbc (igual que pipeline de pedidos)

## ESTADO_WEB (campo ERP)

El campo `estado_web` en `msgestion01art.dbo.articulo` controla qué se publica:
- `'A'` = Activo para web → **publicar** (10,372 artículos)
- `'V'` = Visible (65,409 artículos) → no publicar por ahora
- `NULL` = sin estado web (283,565 artículos)

El watcher (`watcher_estado_web.py`) consulta estado_web='A' y publica/sincroniza.

## WHATSAPP (Meta Cloud API)

Infraestructura compartida con `market_intelligence/enviar_whatsapp_cerraduras.py`:
- Chatwoot: `chat.calzalindo.com.ar` (account 3, inbox 9)
- Meta Phone Number ID: `1046697335188691`
- Template aprobado: `promo_mejores_clientes` (para contactos sin ventana 24hs)
- Mensajes directos: requieren ventana 24hs abierta (contacto escribió primero)

## QUÉ NO TOCAR

- `ordenes_procesadas.json` / `ordenes_procesadas.db` — logs de idempotencia, no borrar
- `publicaciones.db` — registro de publicaciones TN del watcher, no borrar
- Rate limits hardcodeados (TN: 2 req/s, ML: 1 req/s, Meta: 5 req/s)
- Fórmula de precio en `reglas_canales.json` — validada con Fernando

## IMÁGENES

Las fotos de productos se sirven desde el VPS via HTTPS:
```
https://n8n.calzalindo.com.ar/imagenes/{path_relativo}/{archivo_final}
```

- `imagenes.py` consulta la tabla `producto_imagenes` en PostgreSQL (VPS `clz_productos`)
- `imagenes_para_tn(sku)` → `[{'src': 'https://...'}]` (formato TN)
- `imagenes_para_ml(sku)` → `[{'source': 'https://...'}]` (formato ML)
- `urls_producto(sku)` → lista de URLs string

## AUTH HEADERS

- **TiendaNube**: Header `Authentication: bearer {token}` (NO `Authorization` — TN usa header no estándar, verificado con curl 2026-03-24)
- **MercadoLibre**: Header `Authorization: Bearer {token}` (estándar OAuth2)
- **Meta**: Header `Authorization: Bearer {token}` (estándar OAuth2)

## PUBLICAR PRODUCTO NUEVO

`publicar_producto_nuevo(codigo_sinonimo, dry_run=True)` en `canales.py` orquesta:
1. Busca artículo + variantes (talles) en ERP (111)
2. Obtiene URLs de imágenes desde PostgreSQL
3. Calcula precio TN con reglas de `reglas_canales.json`
4. Arma payload con variantes por talle
5. DRY RUN muestra payload y diagnóstico de campos faltantes

## PENDIENTE: MERCADOLIBRE

Para habilitar ML se necesita:
1. Crear app en developers.mercadolibre.com.ar → obtener client_id + client_secret
2. Flujo OAuth2 manual en browser → obtener access_token + refresh_token
3. Crear `mercadolibre_config.json` con los 5 campos
4. Configurar cron para `refresh_token_ml.py` cada 5h
5. Mapear categorías ML por producto

## DEPENDENCIAS

requests, pyodbc, psycopg2, json, os, time, datetime
