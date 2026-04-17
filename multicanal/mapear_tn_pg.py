"""
Mapeo masivo TiendaNube → PostgreSQL (clz_productos).

Recorre TODOS los productos de TN, extrae SKUs de variantes,
matchea contra producto_variantes.codigo_sinonimo en PG,
y graba tiendanube_product_id + tiendanube_slug en tabla productos.

USO:
    python -m multicanal.mapear_tn_pg --dry-run     # preview
    python -m multicanal.mapear_tn_pg               # ejecutar
    python -m multicanal.mapear_tn_pg --stats        # solo stats sin modificar
"""

import argparse
import os
import sqlite3
import time
import psycopg2
from multicanal.tiendanube import TiendaNubeClient, cargar_config
from multicanal.imagenes import PG_CONN_STRING

# SQLite local para el mapping (no requiere permisos en PG)
MAPPING_DB = os.path.join(os.path.dirname(__file__), 'tn_mapping.db')


def asegurar_tabla_mapping():
    """Crea tabla tn_mapping en SQLite local."""
    conn = sqlite3.connect(MAPPING_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tn_mapping (
            pg_producto_id INTEGER,
            pg_familia_id TEXT,
            tiendanube_product_id INTEGER NOT NULL,
            tiendanube_slug TEXT,
            tiendanube_nombre TEXT,
            matched_sku TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (tiendanube_product_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tn_mapping_pg_id
        ON tn_mapping(pg_producto_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_tn_mapping_familia
        ON tn_mapping(pg_familia_id)
    """)
    conn.commit()
    conn.close()
    print(f"  SQLite mapping: {MAPPING_DB}\n")


def cargar_mapa_variantes_pg(conn):
    """Carga mapeo codigo_sinonimo → producto_id desde PG."""
    cur = conn.cursor()
    cur.execute("""
        SELECT pv.codigo_sinonimo, p.id, p.familia_id
        FROM producto_variantes pv
        JOIN productos p ON p.id = pv.producto_id
        WHERE pv.codigo_sinonimo IS NOT NULL
        AND pv.codigo_sinonimo != ''
    """)
    # Un codigo_sinonimo puede aparecer en varias variantes del mismo producto
    mapa = {}  # codigo_sinonimo → (producto_id, familia_id)
    for csr, prod_id, familia_id in cur.fetchall():
        csr_clean = csr.strip()
        if csr_clean:
            mapa[csr_clean] = (prod_id, familia_id)
    cur.close()
    return mapa


def paginar_productos_tn(client, max_pages=500):
    """Itera TODOS los productos de TN con paginación."""
    page = 1
    total = 0
    while page <= max_pages:
        try:
            prods = client.listar_productos(page=page, per_page=200)
        except Exception as e:
            print(f"  Error página {page}: {e}")
            break

        if not prods:
            break

        total += len(prods)
        yield from prods

        if len(prods) < 200:
            break

        page += 1
        time.sleep(0.5)  # rate limit TN: 2 req/s

    print(f"  Total productos leídos de TN: {total}")


def extraer_skus_producto(prod_tn):
    """Extrae todos los SKUs únicos de las variantes de un producto TN."""
    skus = set()
    for v in prod_tn.get('variants', []):
        sku = (v.get('sku') or '').strip()
        if sku:
            skus.add(sku)
    return skus


def extraer_slug(prod_tn):
    """Extrae el slug/handle del producto TN."""
    handle = prod_tn.get('handle', {})
    if isinstance(handle, dict):
        return handle.get('es', '') or handle.get('en', '') or ''
    return str(handle or '')


def mapear(dry_run=True, stats_only=False):
    """Ejecuta el mapeo masivo."""
    print(f"\n{'='*60}")
    print(f"  MAPEO MASIVO TiendaNube → PostgreSQL")
    print(f"  {'[DRY RUN]' if dry_run else '[REAL]'}")
    print(f"{'='*60}\n")

    # --- 1. Conexión PG ---
    print("[1/4] Conectando a PostgreSQL...")
    pg_conn = psycopg2.connect(PG_CONN_STRING)

    if not stats_only:
        print("[2/4] Asegurando tabla tn_mapping (SQLite local)...")
        asegurar_tabla_mapping()
    else:
        print("[2/4] (stats only, skip)")

    # --- 2. Cargar mapa PG ---
    print("[3/4] Cargando mapa de variantes PG (codigo_sinonimo → producto_id)...")
    mapa_pg = cargar_mapa_variantes_pg(pg_conn)
    print(f"  {len(mapa_pg):,} variantes con codigo_sinonimo en PG\n")

    # --- 3. Conexión TN ---
    print("[4/4] Recorriendo productos TiendaNube...\n")
    cfg = cargar_config()
    if not cfg.get('store_id') or not cfg.get('access_token'):
        print("  ERROR: No se encontró tiendanube_config.json")
        pg_conn.close()
        return

    client = TiendaNubeClient(
        store_id=cfg['store_id'],
        access_token=cfg['access_token']
    )

    # --- 4. Mapear ---
    matcheados = []
    sin_match_pg = []
    sin_sku_tn = []
    errores = []

    for prod_tn in paginar_productos_tn(client):
        tn_id = prod_tn.get('id')
        slug = extraer_slug(prod_tn)
        nombre = prod_tn.get('name', {})
        if isinstance(nombre, dict):
            nombre = nombre.get('es', '') or ''

        skus = extraer_skus_producto(prod_tn)

        if not skus:
            sin_sku_tn.append({'tn_id': tn_id, 'nombre': nombre, 'slug': slug})
            continue

        # Buscar match en PG
        pg_producto_id = None
        pg_familia_id = None
        matched_sku = None
        for sku in skus:
            if sku in mapa_pg:
                pg_producto_id, pg_familia_id = mapa_pg[sku]
                matched_sku = sku
                break

        if pg_producto_id:
            matcheados.append({
                'tn_id': tn_id,
                'pg_id': pg_producto_id,
                'familia_id': pg_familia_id,
                'slug': slug,
                'nombre': nombre,
                'sku': matched_sku,
            })
        else:
            sin_match_pg.append({
                'tn_id': tn_id,
                'nombre': nombre,
                'slug': slug,
                'skus': list(skus)[:3],
            })

    # --- 5. Aplicar mapeo ---
    print(f"\n{'='*60}")
    print(f"  RESULTADOS")
    print(f"{'='*60}")
    print(f"  Matcheados:     {len(matcheados):,}")
    print(f"  Sin match en PG: {len(sin_match_pg):,}")
    print(f"  Sin SKU en TN:  {len(sin_sku_tn):,}")
    print()

    if stats_only:
        _print_samples(matcheados, sin_match_pg, sin_sku_tn)
        pg_conn.close()
        return {
            'matcheados': len(matcheados),
            'sin_match_pg': len(sin_match_pg),
            'sin_sku_tn': len(sin_sku_tn),
        }

    if dry_run:
        print("[DRY RUN] Se actualizarían estos productos en PG:\n")
        for m in matcheados[:20]:
            print(f"  PG #{m['pg_id']} ← TN #{m['tn_id']} | {m['slug'][:50]} | {m['nombre'][:40]}")
        if len(matcheados) > 20:
            print(f"  ... y {len(matcheados) - 20} más")
    else:
        print("Aplicando mapeo a SQLite (tn_mapping.db)...")
        sq_conn = sqlite3.connect(MAPPING_DB)
        actualizados = 0
        for m in matcheados:
            try:
                sq_conn.execute("""
                    INSERT INTO tn_mapping (pg_producto_id, pg_familia_id, tiendanube_product_id,
                                            tiendanube_slug, tiendanube_nombre, matched_sku, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT (tiendanube_product_id) DO UPDATE SET
                        pg_producto_id = excluded.pg_producto_id,
                        pg_familia_id = excluded.pg_familia_id,
                        tiendanube_slug = excluded.tiendanube_slug,
                        tiendanube_nombre = excluded.tiendanube_nombre,
                        matched_sku = excluded.matched_sku,
                        updated_at = datetime('now')
                """, (m['pg_id'], m.get('familia_id', ''), m['tn_id'], m['slug'],
                      m['nombre'], m['sku']))
                actualizados += 1
            except Exception as e:
                errores.append({'pg_id': m['pg_id'], 'error': str(e)})

        sq_conn.commit()
        sq_conn.close()
        print(f"  Actualizados: {actualizados:,}")
        if errores:
            print(f"  Errores: {len(errores)}")
            for e in errores[:5]:
                print(f"    PG #{e['pg_id']}: {e['error']}")

    _print_samples(matcheados, sin_match_pg, sin_sku_tn)
    pg_conn.close()

    return {
        'matcheados': len(matcheados),
        'sin_match_pg': len(sin_match_pg),
        'sin_sku_tn': len(sin_sku_tn),
        'errores': len(errores),
    }


def _print_samples(matcheados, sin_match_pg, sin_sku_tn):
    """Imprime muestras de cada categoría."""
    if sin_match_pg:
        print(f"\n  Ejemplos sin match en PG (primeros 10):")
        for s in sin_match_pg[:10]:
            print(f"    TN #{s['tn_id']} | {s['nombre'][:45]} | SKUs: {s['skus']}")

    if sin_sku_tn:
        print(f"\n  Ejemplos sin SKU en TN (primeros 10):")
        for s in sin_sku_tn[:10]:
            print(f"    TN #{s['tn_id']} | {s['nombre'][:45]} | slug: {s['slug'][:30]}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Mapeo masivo TiendaNube → PostgreSQL')
    parser.add_argument('--dry-run', action='store_true', help='Preview sin modificar PG')
    parser.add_argument('--stats', action='store_true', help='Solo estadísticas')
    args = parser.parse_args()

    mapear(dry_run=args.dry_run, stats_only=args.stats)
