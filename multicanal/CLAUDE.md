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
| `facturador_tn.py` | Órdenes pagadas TN → INSERT ventas2/ventas1 (tipo B). Soporta H4 y ABI |
| `facturador_ml.py` | Ventas ML → INSERT ventas2/ventas1 (tipo B). Dedup con SQLite |
| `sync_stock.py` | Stock ERP → TiendaNube (depósitos 0+1) |
| `sync_stock_ml.py` | Stock ERP → MercadoLibre (multiget API) |
| `sync_precios.py` | Precios ERP → TN (tolerancia <2% ignora) |
| `sync_precios_ml.py` | Precios ERP → ML (premium/clásica) |
| `refresh_token_ml.py` | Auto-refresh OAuth2 ML cada 5h |
| `imagenes.py` | Fotos desde PostgreSQL (`clz_productos`), URLs públicas VPS |
| `reglas_canales.json` | Reglas de pricing por canal (comisión, margen, redondeo) |

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

# Sync stock TN
python -m multicanal.sync_stock --dry-run

# Refresh token ML
python -m multicanal.refresh_token_ml

# Publicar producto nuevo en TN (dry-run)
python -c "from multicanal.canales import publicar_producto_nuevo; publicar_producto_nuevo('272220004835', dry_run=True)"
```

---

## CONEXIÓN CON PROYECTO PRINCIPAL

- Comparte acceso a `msgestion01` (CALZALINDO), `msgestion03` (H4), `msgestion01art` (artículos)
- Usa mismo patrón de routing `get_tabla_base(tabla, empresa)`
- Lee stock de `msgestionC.dbo.stock`
- INSERT va directo al 111 via pyodbc (igual que pipeline de pedidos)

## QUÉ NO TOCAR

- `ordenes_procesadas.json` / `ordenes_procesadas.db` — logs de idempotencia, no borrar
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

- **TiendaNube**: Header `Authentication: bearer {token}` (NO `Authorization`) — verificado 2026-03-20
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
