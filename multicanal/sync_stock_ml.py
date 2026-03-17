"""
Sincronización de stock ERP → MercadoLibre.

Lee publicaciones activas de ML, busca el artículo correspondiente en el ERP
por seller_custom_field (SKU) → codigo_sinonimo, obtiene stock real
(depósitos 0 y 1) y actualiza ML cuando hay diferencia.

USO:
    # Dry run
    python -m multicanal.sync_stock_ml --dry-run

    # Ejecutar sync real
    python -m multicanal.sync_stock_ml

    # Desde código
    from multicanal.sync_stock_ml import sincronizar_stock_ml
    reporte = sincronizar_stock_ml(dry_run=True)
"""

import sys
import os
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multicanal.facturador_ml import cargar_config, ML_API_BASE, _ml_get
from multicanal.sync_stock import conectar_erp, obtener_stock_erp


def obtener_items_activos(token: str, user_id: str, max_items: int = 1000) -> list:
    """
    Obtiene listado de items activos del vendedor en ML.
    Retorna lista de dicts con id, title, available_quantity, seller_custom_field.
    """
    # Primero obtener IDs
    items_ids = []
    offset = 0
    limit = 50

    while offset < max_items:
        data = _ml_get(
            f'/users/{user_id}/items/search',
            token,
            params={'status': 'active', 'offset': offset, 'limit': limit}
        )
        ids = data.get('results', [])
        items_ids.extend(ids)
        total = data.get('paging', {}).get('total', 0)
        offset += limit
        if offset >= total or not ids:
            break

    if not items_ids:
        return []

    # Obtener detalles en lotes de 20 (límite ML multiget)
    items = []
    BATCH = 20
    headers = {'Authorization': f'Bearer {token}'}

    for i in range(0, len(items_ids), BATCH):
        lote_ids = items_ids[i:i + BATCH]
        ids_str = ','.join(lote_ids)
        r = requests.get(
            f'{ML_API_BASE}/items',
            headers=headers,
            params={'ids': ids_str, 'attributes': 'id,title,available_quantity,seller_custom_field,variations'},
            timeout=30,
        )
        r.raise_for_status()
        for item_resp in r.json():
            body = item_resp.get('body', item_resp)
            if body.get('error'):
                continue

            sku = (body.get('seller_custom_field') or '').strip()
            items.append({
                'id': body['id'],
                'title': body.get('title', ''),
                'available_quantity': body.get('available_quantity', 0),
                'sku': sku,
                'variations': body.get('variations', []),
            })

    return items


def sincronizar_stock_ml(dry_run: bool = True) -> dict:
    """
    Flujo principal de sincronización de stock ERP → ML.

    1. Lee items activos de ML con SKU
    2. Busca stock en ERP por codigo_sinonimo
    3. Compara y actualiza donde haya diferencia
    """
    modo = "DRY RUN" if dry_run else "SYNC REAL"
    print(f"\n{'='*60}")
    print(f"  SYNC STOCK ERP → MercadoLibre [{modo}]")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    config = cargar_config()
    if not config.get('access_token') or not config.get('user_id'):
        print("ERROR: No hay config de MercadoLibre.")
        return {'error': 'Sin config MercadoLibre'}

    token = config['access_token']
    user_id = config['user_id']

    # 1. Leer items ML
    print("[1/4] Leyendo items activos de MercadoLibre...")
    try:
        items = obtener_items_activos(token, user_id)
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            print("ERROR: Token de ML expirado.")
            return {'error': 'Token ML expirado'}
        raise
    print(f"       {len(items)} items activos.\n")

    # 2. Extraer items con SKU
    print("[2/4] Extrayendo items con SKU...")
    items_con_sku = [(it['id'], it['sku'], it['title'], it['available_quantity'])
                     for it in items if it['sku']]
    sin_sku = len(items) - len(items_con_sku)
    skus_unicos = list(set(it[1] for it in items_con_sku))
    print(f"       {len(items_con_sku)} items con SKU ({len(skus_unicos)} únicos)")
    print(f"       {sin_sku} items sin SKU (ignorados)\n")

    if not items_con_sku:
        return {
            'total_items': len(items),
            'total_con_sku': 0,
            'sin_sku': sin_sku,
            'encontrados_erp': 0,
            'no_encontrados_erp': 0,
            'sin_cambio': 0,
            'actualizados': [],
            'errores': [],
        }

    # 3. Obtener stock del ERP
    print("[3/4] Consultando stock en ERP...")
    conn = conectar_erp()
    try:
        stock_erp = obtener_stock_erp(conn, skus_unicos)
    finally:
        conn.close()

    encontrados = len(stock_erp)
    no_encontrados = [s for s in skus_unicos if s not in stock_erp]
    print(f"       {encontrados} SKUs encontrados en ERP")
    if no_encontrados:
        print(f"       {len(no_encontrados)} SKUs NO encontrados:")
        for s in no_encontrados[:20]:
            print(f"         - {s}")
    print()

    # 4. Comparar y actualizar
    print(f"[4/4] Comparando stock y {'mostrando cambios' if dry_run else 'actualizando ML'}...")
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    actualizados = []
    errores = []
    sin_cambio = 0

    for item_id, sku, titulo, stock_ml in items_con_sku:
        if sku not in stock_erp:
            continue

        stock_real = stock_erp[sku]
        stock_nuevo = max(stock_real, 0)

        if stock_nuevo == stock_ml:
            sin_cambio += 1
            continue

        cambio = {
            'item_id': item_id,
            'sku': sku,
            'titulo': titulo,
            'stock_ml_anterior': stock_ml,
            'stock_erp': stock_real,
            'stock_nuevo': stock_nuevo,
        }

        if dry_run:
            print(f"  [DRY] {sku:20s} | {titulo[:30]:30s} | ML:{stock_ml:4d} → ERP:{stock_nuevo:4d}")
            actualizados.append(cambio)
        else:
            try:
                r = requests.put(
                    f'{ML_API_BASE}/items/{item_id}',
                    json={'available_quantity': stock_nuevo},
                    headers=headers,
                    timeout=30,
                )
                r.raise_for_status()
                print(f"  [OK]  {sku:20s} | {titulo[:30]:30s} | ML:{stock_ml:4d} → ERP:{stock_nuevo:4d}")
                actualizados.append(cambio)
            except Exception as e:
                error_msg = f"Error actualizando {sku} ({item_id}): {e}"
                print(f"  [ERR] {error_msg}")
                errores.append(error_msg)

    # Resumen
    print(f"\n{'='*60}")
    print(f"  RESUMEN {'(DRY RUN — nada se modificó)' if dry_run else ''}")
    print(f"{'='*60}")
    print(f"  Items ML activos:    {len(items)}")
    print(f"  Items con SKU:       {len(items_con_sku)}")
    print(f"  Items sin SKU:       {sin_sku}")
    print(f"  SKUs en ERP:         {encontrados}")
    print(f"  SKUs no en ERP:      {len(no_encontrados)}")
    print(f"  Sin cambio:          {sin_cambio}")
    print(f"  Actualizados:        {len(actualizados)}")
    if errores:
        print(f"  Errores:             {len(errores)}")
    print(f"{'='*60}\n")

    return {
        'total_items': len(items),
        'total_con_sku': len(items_con_sku),
        'sin_sku': sin_sku,
        'encontrados_erp': encontrados,
        'no_encontrados_erp': len(no_encontrados),
        'sin_cambio': sin_cambio,
        'actualizados': actualizados,
        'errores': errores,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Sync stock ERP → MercadoLibre')
    parser.add_argument('--dry-run', action='store_true', default=False)
    args = parser.parse_args()

    reporte = sincronizar_stock_ml(dry_run=args.dry_run)

    if reporte.get('error'):
        sys.exit(1)
    if reporte.get('errores'):
        sys.exit(2)
    sys.exit(0)
