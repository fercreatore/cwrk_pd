"""
Sincronización de stock ERP (SQL Server) → TiendaNube.

Lee todos los productos de TN, busca el artículo correspondiente en el ERP
por codigo_sinonimo, obtiene stock real (depósitos 0 y 1) y actualiza TN
cuando hay diferencia.

USO:
    # Dry run (solo muestra cambios sin aplicar)
    python -m multicanal.sync_stock --dry-run

    # Ejecutar sync real
    python -m multicanal.sync_stock

    # Desde código
    from multicanal.sync_stock import sincronizar_stock
    reporte = sincronizar_stock(dry_run=True)
"""

import pyodbc
import sys
import os
from datetime import datetime

# Agregar raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multicanal.tiendanube import TiendaNubeClient, cargar_config


# ── Conexión ERP ──

CONN_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion01art;"
    "UID=am;PWD=dl;"
    "Encrypt=no;"
)


def conectar_erp():
    """Abre conexión pyodbc al SQL Server de producción (111)."""
    return pyodbc.connect(CONN_STRING, timeout=15)


def obtener_stock_erp(conn, codigos_sinonimo: list) -> dict:
    """
    Dado un listado de SKUs (codigo_sinonimo), devuelve un dict {sku: stock_total}.

    Hace JOIN articulo (por codigo_sinonimo) con stock (por articulo=codigo),
    filtrando depósito IN (0, 1) y sumando stock_actual.

    SKUs que no existen en el ERP no aparecen en el resultado.
    """
    if not codigos_sinonimo:
        return {}

    resultado = {}

    # Procesar en lotes de 500 para no exceder límite de parámetros SQL
    BATCH = 500
    for i in range(0, len(codigos_sinonimo), BATCH):
        lote = codigos_sinonimo[i:i + BATCH]
        placeholders = ",".join(["?"] * len(lote))

        query = f"""
            SELECT
                a.codigo_sinonimo,
                ISNULL(SUM(s.stock_actual), 0) AS stock_total
            FROM msgestion01art.dbo.articulo a
            LEFT JOIN msgestionC.dbo.stock s
                ON s.articulo = a.codigo
                AND s.deposito IN (0, 1)
            WHERE a.codigo_sinonimo IN ({placeholders})
              AND a.codigo_sinonimo <> ''
            GROUP BY a.codigo_sinonimo
        """

        cursor = conn.cursor()
        cursor.execute(query, lote)
        for row in cursor.fetchall():
            sku = row[0].strip() if row[0] else ''
            stock = int(row[1])
            if sku:
                resultado[sku] = stock

    return resultado


def obtener_productos_tn(client: TiendaNubeClient, max_pages: int = 200) -> list:
    """
    Pagina por TODOS los productos de TiendaNube.
    Retorna lista completa de productos con sus variantes.
    """
    todos = []
    for page in range(1, max_pages + 1):
        print(f"  Leyendo productos TN — página {page}...")
        lote = client.listar_productos(page=page, per_page=50)
        if not lote:
            break
        todos.extend(lote)
        if len(lote) < 50:
            break
    return todos


def sincronizar_stock(dry_run: bool = True) -> dict:
    """
    Flujo principal de sincronización.

    1. Lee todos los productos de TN con sus variantes y SKUs
    2. Para cada SKU, busca el stock en el ERP
    3. Compara y actualiza donde haya diferencia

    Args:
        dry_run: Si True, solo muestra cambios sin aplicar.

    Returns:
        dict con claves:
            - total_productos: cantidad de productos leídos de TN
            - total_variantes: cantidad de variantes con SKU
            - sin_sku: variantes sin SKU (no se pueden vincular)
            - encontrados_erp: SKUs encontrados en el ERP
            - no_encontrados_erp: SKUs no encontrados en el ERP
            - sin_cambio: variantes donde stock coincide
            - actualizados: lista de dicts con detalle de cada cambio
            - errores: lista de errores durante actualización
    """
    modo = "DRY RUN" if dry_run else "SYNC REAL"
    print(f"\n{'='*60}")
    print(f"  SYNC STOCK ERP → TiendaNube [{modo}]")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # --- Inicializar cliente TN ---
    config = cargar_config()
    if not config.get('store_id') or not config.get('access_token'):
        print("ERROR: No hay config de TiendaNube. Ejecutar guardar_config() primero.")
        return {'error': 'Sin config TiendaNube'}

    client = TiendaNubeClient(
        store_id=config['store_id'],
        access_token=config['access_token'],
    )

    # --- 1. Leer productos TN ---
    print("[1/4] Leyendo productos de TiendaNube...")
    productos = obtener_productos_tn(client)
    print(f"       {len(productos)} productos leídos.\n")

    # --- 2. Extraer variantes con SKU ---
    print("[2/4] Extrayendo variantes con SKU...")
    variantes_con_sku = []  # (product_id, variant_id, sku, nombre_producto, stock_tn)
    sin_sku_count = 0

    for prod in productos:
        product_id = prod['id']
        nombre = prod.get('name', {})
        nombre_es = nombre.get('es', '') if isinstance(nombre, dict) else str(nombre)

        for var in prod.get('variants', []):
            sku = (var.get('sku') or '').strip()
            if not sku:
                sin_sku_count += 1
                continue
            variant_id = var['id']
            stock_tn = var.get('stock', 0) or 0
            variantes_con_sku.append((product_id, variant_id, sku, nombre_es, stock_tn))

    skus_unicos = list(set(v[2] for v in variantes_con_sku))
    print(f"       {len(variantes_con_sku)} variantes con SKU ({len(skus_unicos)} SKUs únicos)")
    print(f"       {sin_sku_count} variantes sin SKU (ignoradas)\n")

    if not variantes_con_sku:
        print("No hay variantes con SKU para sincronizar.")
        return {
            'total_productos': len(productos),
            'total_variantes': 0,
            'sin_sku': sin_sku_count,
            'encontrados_erp': 0,
            'no_encontrados_erp': 0,
            'sin_cambio': 0,
            'actualizados': [],
            'errores': [],
        }

    # --- 3. Obtener stock del ERP ---
    print("[3/4] Consultando stock en ERP (SQL Server 111)...")
    conn = conectar_erp()
    try:
        stock_erp = obtener_stock_erp(conn, skus_unicos)
    finally:
        conn.close()

    encontrados = len(stock_erp)
    no_encontrados_skus = [s for s in skus_unicos if s not in stock_erp]
    print(f"       {encontrados} SKUs encontrados en ERP")
    if no_encontrados_skus:
        print(f"       {len(no_encontrados_skus)} SKUs NO encontrados en ERP:")
        for s in no_encontrados_skus[:20]:
            print(f"         - {s}")
        if len(no_encontrados_skus) > 20:
            print(f"         ... y {len(no_encontrados_skus) - 20} más")
    print()

    # --- 4. Comparar y actualizar ---
    print(f"[4/4] Comparando stock y {'mostrando cambios' if dry_run else 'actualizando TN'}...")
    actualizados = []
    errores = []
    sin_cambio = 0

    for product_id, variant_id, sku, nombre, stock_tn in variantes_con_sku:
        if sku not in stock_erp:
            continue

        stock_real = stock_erp[sku]
        # Stock negativo en ERP → 0 en TN
        stock_nuevo = max(stock_real, 0)

        if stock_nuevo == stock_tn:
            sin_cambio += 1
            continue

        cambio = {
            'product_id': product_id,
            'variant_id': variant_id,
            'sku': sku,
            'nombre': nombre,
            'stock_tn_anterior': stock_tn,
            'stock_erp': stock_real,
            'stock_nuevo': stock_nuevo,
        }

        if dry_run:
            print(f"  [DRY] {sku:20s} | {nombre[:30]:30s} | TN:{stock_tn:4d} → ERP:{stock_nuevo:4d}")
            actualizados.append(cambio)
        else:
            try:
                client.actualizar_variante(product_id, variant_id, stock=stock_nuevo)
                print(f"  [OK]  {sku:20s} | {nombre[:30]:30s} | TN:{stock_tn:4d} → ERP:{stock_nuevo:4d}")
                actualizados.append(cambio)
            except Exception as e:
                error_msg = f"Error actualizando {sku} (prod={product_id}, var={variant_id}): {e}"
                print(f"  [ERR] {error_msg}")
                errores.append(error_msg)

    # --- Resumen ---
    print(f"\n{'='*60}")
    print(f"  RESUMEN {'(DRY RUN — nada se modificó)' if dry_run else ''}")
    print(f"{'='*60}")
    print(f"  Productos TN:        {len(productos)}")
    print(f"  Variantes con SKU:   {len(variantes_con_sku)}")
    print(f"  Variantes sin SKU:   {sin_sku_count}")
    print(f"  SKUs en ERP:         {encontrados}")
    print(f"  SKUs no en ERP:      {len(no_encontrados_skus)}")
    print(f"  Sin cambio:          {sin_cambio}")
    print(f"  Actualizados:        {len(actualizados)}")
    if errores:
        print(f"  Errores:             {len(errores)}")
    print(f"{'='*60}\n")

    return {
        'total_productos': len(productos),
        'total_variantes': len(variantes_con_sku),
        'sin_sku': sin_sku_count,
        'encontrados_erp': encontrados,
        'no_encontrados_erp': len(no_encontrados_skus),
        'sin_cambio': sin_cambio,
        'actualizados': actualizados,
        'errores': errores,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Sync stock ERP → TiendaNube')
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='Solo mostrar cambios sin aplicar (default: False)')
    args = parser.parse_args()

    reporte = sincronizar_stock(dry_run=args.dry_run)

    if reporte.get('error'):
        sys.exit(1)
    if reporte.get('errores'):
        sys.exit(2)
    sys.exit(0)
