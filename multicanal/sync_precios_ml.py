"""
Sincronización de precios ERP → MercadoLibre.

Lee items activos de ML, busca el costo en el ERP por seller_custom_field (SKU),
calcula el precio correcto según la regla del canal ML y actualiza donde haya
diferencia superior a la tolerancia.

USO:
    python -m multicanal.sync_precios_ml --dry-run
    python -m multicanal.sync_precios_ml --dry-run --tolerancia 5
    python -m multicanal.sync_precios_ml --dry-run --tipo premium
"""

import sys
import os
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multicanal.facturador_ml import cargar_config, ML_API_BASE
from multicanal.sync_stock_ml import obtener_items_activos
from multicanal.sync_precios import conectar_erp, obtener_costos_erp
from multicanal.precios import calcular_precio_canal, cargar_reglas, REGLAS_DEFAULT

REGLAS_FILE = os.path.join(os.path.dirname(__file__), 'reglas_canales.json')


def sincronizar_precios_ml(dry_run: bool = True, tolerancia_pct: float = 2.0,
                            tipo_publicacion: str = 'premium',
                            cotiz_usd: float = 1170.0) -> dict:
    """
    Flujo principal de sincronización de precios ERP → ML.

    Args:
        tipo_publicacion: 'premium' o 'clasica' — determina qué regla de canal usar.
        cotiz_usd: Cotización USD para artículos importados.
    """
    modo = "DRY RUN" if dry_run else "SYNC REAL"
    canal_key = f'mercadolibre_{tipo_publicacion}'
    print(f"\n{'='*60}")
    print(f"  SYNC PRECIOS ERP → MercadoLibre [{modo}]")
    print(f"  Canal: {canal_key}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Tolerancia: {tolerancia_pct}% | USD: ${cotiz_usd:,.0f}")
    print(f"{'='*60}\n")

    # Cargar regla de pricing
    reglas = cargar_reglas(REGLAS_FILE)
    regla_ml = reglas.get(canal_key)
    if not regla_ml:
        regla_ml = REGLAS_DEFAULT.get(canal_key)
    if not regla_ml:
        print(f"ERROR: No hay regla de pricing para {canal_key}.")
        return {'error': f'Sin regla {canal_key}'}

    print(f"  Regla: comisión {regla_ml.comision*100:.0f}% | margen obj {regla_ml.margen_objetivo*100:.0f}%\n")

    # Inicializar ML
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
            return {'error': 'Token ML expirado'}
        raise
    print(f"       {len(items)} items activos.\n")

    # 2. Extraer items con SKU y precio actual
    print("[2/4] Extrayendo items con SKU...")
    # Necesitamos el precio actual — obtenerlo del detalle del item
    items_con_sku = []
    sin_sku = 0

    headers = {'Authorization': f'Bearer {token}'}
    BATCH = 20
    items_ids_con_sku = [(it['id'], it['sku'], it['title']) for it in items if it['sku']]
    sin_sku = len(items) - len(items_ids_con_sku)

    # Obtener precios actuales en lotes
    for i in range(0, len(items_ids_con_sku), BATCH):
        lote = items_ids_con_sku[i:i + BATCH]
        ids_str = ','.join(it[0] for it in lote)
        try:
            r = requests.get(
                f'{ML_API_BASE}/items',
                headers=headers,
                params={'ids': ids_str, 'attributes': 'id,price,seller_custom_field'},
                timeout=30,
            )
            r.raise_for_status()
            precios_map = {}
            for item_resp in r.json():
                body = item_resp.get('body', item_resp)
                if not body.get('error'):
                    precios_map[body['id']] = float(body.get('price', 0))

            for item_id, sku, titulo in lote:
                precio_ml = precios_map.get(item_id, 0)
                items_con_sku.append((item_id, sku, titulo, precio_ml))
        except Exception:
            for item_id, sku, titulo in lote:
                items_con_sku.append((item_id, sku, titulo, 0))

    skus_unicos = list(set(it[1] for it in items_con_sku))
    print(f"       {len(items_con_sku)} items con SKU ({len(skus_unicos)} únicos)")
    print(f"       {sin_sku} items sin SKU (ignorados)\n")

    if not items_con_sku:
        return {'total_items': len(items), 'total_con_sku': 0, 'actualizados': [], 'errores': []}

    # 3. Obtener costos del ERP
    print("[3/4] Consultando costos en ERP...")
    conn = conectar_erp()
    try:
        costos_erp = obtener_costos_erp(conn, skus_unicos, cotiz_usd=cotiz_usd)
    finally:
        conn.close()

    print(f"       {len(costos_erp)} SKUs con costo en ERP\n")

    # 4. Comparar y actualizar
    print(f"[4/4] Comparando precios y {'mostrando cambios' if dry_run else 'actualizando ML'}...")
    actualizados = []
    errores = []
    sin_cambio = 0

    for item_id, sku, titulo, precio_ml in items_con_sku:
        if sku not in costos_erp:
            continue

        costo = costos_erp[sku]
        resultado = calcular_precio_canal(costo, regla_ml)
        if 'error' in resultado:
            continue

        precio_correcto = resultado['precio_venta']

        if precio_ml > 0:
            diff_pct = abs(precio_correcto - precio_ml) / precio_ml * 100
        else:
            diff_pct = 100.0

        if diff_pct <= tolerancia_pct:
            sin_cambio += 1
            continue

        cambio = {
            'item_id': item_id,
            'sku': sku,
            'titulo': titulo,
            'costo_erp': costo,
            'precio_ml_anterior': precio_ml,
            'precio_correcto': precio_correcto,
            'diferencia_pct': round(diff_pct, 1),
            'margen_real': resultado['margen_real'],
        }

        if dry_run:
            direccion = "↑" if precio_correcto > precio_ml else "↓"
            print(f"  [DRY] {sku:20s} | {titulo[:25]:25s} | "
                  f"${precio_ml:>10,.0f} {direccion} ${precio_correcto:>10,.0f} "
                  f"({diff_pct:+.1f}%) | margen {resultado['margen_real']}%")
            actualizados.append(cambio)
        else:
            try:
                r = requests.put(
                    f'{ML_API_BASE}/items/{item_id}',
                    json={'price': precio_correcto},
                    headers=headers,
                    timeout=30,
                )
                r.raise_for_status()
                print(f"  [OK]  {sku:20s} | ${precio_ml:,.0f} → ${precio_correcto:,.0f}")
                actualizados.append(cambio)
            except Exception as e:
                error_msg = f"Error actualizando precio {sku} ({item_id}): {e}"
                print(f"  [ERR] {error_msg}")
                errores.append(error_msg)

    # Resumen
    print(f"\n{'='*60}")
    print(f"  RESUMEN {'(DRY RUN)' if dry_run else ''}")
    print(f"{'='*60}")
    print(f"  Items ML:             {len(items)}")
    print(f"  Items con SKU:        {len(items_con_sku)}")
    print(f"  SKUs con costo ERP:   {len(costos_erp)}")
    print(f"  Dentro de tolerancia: {sin_cambio}")
    print(f"  Actualizados:         {len(actualizados)}")
    if errores:
        print(f"  Errores:              {len(errores)}")
    if actualizados:
        subidas = sum(1 for a in actualizados if a['precio_correcto'] > a['precio_ml_anterior'])
        print(f"  Subidas:              {subidas}")
        print(f"  Bajadas:              {len(actualizados) - subidas}")
    print(f"{'='*60}\n")

    return {
        'total_items': len(items),
        'total_con_sku': len(items_con_sku),
        'skus_con_costo': len(costos_erp),
        'sin_cambio': sin_cambio,
        'actualizados': actualizados,
        'errores': errores,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Sync precios ERP → MercadoLibre')
    parser.add_argument('--dry-run', action='store_true', default=False)
    parser.add_argument('--tolerancia', type=float, default=2.0)
    parser.add_argument('--tipo', type=str, default='premium',
                        help='Tipo publicación: premium o clasica')
    parser.add_argument('--cotiz-usd', type=float, default=1170.0)
    args = parser.parse_args()

    reporte = sincronizar_precios_ml(
        dry_run=args.dry_run, tolerancia_pct=args.tolerancia,
        tipo_publicacion=args.tipo, cotiz_usd=args.cotiz_usd,
    )

    if reporte.get('error'):
        sys.exit(1)
    if reporte.get('errores'):
        sys.exit(2)
    sys.exit(0)
