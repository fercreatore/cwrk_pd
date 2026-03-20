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
| `imagenes.py` | Fotos desde PostgreSQL (`clz_productos`) en base64 |
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

## DEPENDENCIAS

requests, pyodbc, psycopg2, json, os, time, datetime
