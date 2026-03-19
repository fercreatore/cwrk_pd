"""
Sincronización de precios ERP → TiendaNube.

Lee productos de TN, busca el costo en el ERP por codigo_sinonimo,
calcula el precio correcto según las reglas del canal TN y actualiza
donde haya diferencia.

USO:
    # Dry run (solo muestra cambios sin aplicar)
    python -m multicanal.sync_precios --dry-run

    # Ejecutar sync real
    python -m multicanal.sync_precios

    # Con tolerancia de 5% (ignora diferencias menores)
    python -m multicanal.sync_precios --dry-run --tolerancia 5

    # Desde código
    from multicanal.sync_precios import sincronizar_precios
    reporte = sincronizar_precios(dry_run=True)
"""

import pyodbc
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multicanal.tiendanube import TiendaNubeClient, cargar_config
from multicanal.precios import calcular_precio_canal, cargar_reglas, REGLAS_DEFAULT
from multicanal.sync_stock import obtener_productos_tn


# ── Conexión ERP ──

CONN_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion01art;"
    "UID=am;PWD=dl;"
    "Encrypt=no;"
)

REGLAS_FILE = os.path.join(os.path.dirname(__file__), 'reglas_canales.json')


def conectar_erp():
    return pyodbc.connect(CONN_STRING, timeout=15)


def obtener_costos_erp(conn, codigos_sinonimo: list, cotiz_usd: float = 1170.0) -> dict:
    """
    Dado un listado de SKUs (codigo_sinonimo), devuelve {sku: precio_costo_en_pesos}.
    Convierte automáticamente artículos con moneda=1 (USD) usando cotiz_usd.
    """
    if not codigos_sinonimo:
        return {}

    resultado = {}
    BATCH = 500
    for i in range(0, len(codigos_sinonimo), BATCH):
        lote = codigos_sinonimo[i:i + BATCH]
        placeholders = ",".join(["?"] * len(lote))

        query = f"""
            SELECT codigo_sinonimo, precio_costo, moneda
            FROM msgestion01art.dbo.articulo
            WHERE codigo_sinonimo IN ({placeholders})
              AND codigo_sinonimo <> ''
              AND precio_costo > 0
              AND estado IN ('V', 'U')
        """

        cursor = conn.cursor()
        cursor.execute(query, lote)
        for row in cursor.fetchall():
            sku = row[0].strip() if row[0] else ''
            costo = float(row[1] or 0)
            moneda = int(row[2] or 0)
            if sku and costo > 0:
                # Convertir USD a ARS si moneda=1
                if moneda == 1:
                    costo = costo * cotiz_usd
                resultado[sku] = costo

    return resultado


def sincronizar_precios(dry_run: bool = True, tolerancia_pct: float = 2.0,
                        cotiz_usd: float = 1170.0) -> dict:
    """
    Flujo principal de sincronización de precios.

    1. Lee productos de TN con sus variantes y SKUs
    2. Busca el costo de cada SKU en el ERP
    3. Calcula el precio correcto según regla del canal tiendanube
    4. Actualiza donde la diferencia supere la tolerancia

    Args:
        dry_run: Si True, solo muestra cambios sin aplicar.
        tolerancia_pct: Porcentaje mínimo de diferencia para actualizar (default 2%).
    """
    modo = "DRY RUN" if dry_run else "SYNC REAL"
    print(f"\n{'='*60}")
    print(f"  SYNC PRECIOS ERP → TiendaNube [{modo}]")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Tolerancia: {tolerancia_pct}%")
    print(f"  Cotización USD: ${cotiz_usd:,.0f}")
    print(f"{'='*60}\n")

    # --- Cargar regla de pricing para TN ---
    reglas = cargar_reglas(REGLAS_FILE)
    regla_tn = reglas.get('tiendanube')
    if not regla_tn:
        regla_tn = REGLAS_DEFAULT.get('tiendanube')
    if not regla_tn:
        print("ERROR: No hay regla de pricing para tiendanube.")
        return {'error': 'Sin regla tiendanube'}

    print(f"  Regla TN: comisión {regla_tn.comision*100:.1f}% + pago {regla_tn.comision_pago*100:.1f}% "
          f"| margen obj {regla_tn.margen_objetivo*100:.0f}%\n")

    # --- Inicializar cliente TN ---
    config = cargar_config()
    if not config.get('store_id') or not config.get('access_token'):
        print("ERROR: No hay config de TiendaNube.")
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
    variantes = []  # (product_id, variant_id, sku, nombre, precio_tn)
    sin_sku = 0

    for prod in productos:
        product_id = prod['id']
        nombre = prod.get('name', {})
        nombre_es = nombre.get('es', '') if isinstance(nombre, dict) else str(nombre)

        for var in prod.get('variants', []):
            sku = (var.get('sku') or '').strip()
            if not sku:
                sin_sku += 1
                continue
            variant_id = var['id']
            precio_tn = float(var.get('price', 0) or 0)
            variantes.append((product_id, variant_id, sku, nombre_es, precio_tn))

    skus_unicos = list(set(v[2] for v in variantes))
    print(f"       {len(variantes)} variantes con SKU ({len(skus_unicos)} únicos)")
    print(f"       {sin_sku} variantes sin SKU (ignoradas)\n")

    if not variantes:
        return {
            'total_productos': len(productos),
            'total_variantes': 0,
            'actualizados': [],
            'errores': [],
        }

    # --- 3. Obtener costos del ERP ---
    print("[3/4] Consultando costos en ERP...")
    conn = conectar_erp()
    try:
        costos_erp = obtener_costos_erp(conn, skus_unicos, cotiz_usd=cotiz_usd)
    finally:
        conn.close()

    print(f"       {len(costos_erp)} SKUs con costo en ERP")
    no_encontrados = [s for s in skus_unicos if s not in costos_erp]
    if no_encontrados:
        print(f"       {len(no_encontrados)} SKUs sin costo en ERP:")
        for s in no_encontrados[:10]:
            print(f"         - {s}")
        if len(no_encontrados) > 10:
            print(f"         ... y {len(no_encontrados) - 10} más")
    print()

    # --- 4. Comparar y actualizar ---
    print(f"[4/4] Comparando precios y {'mostrando cambios' if dry_run else 'actualizando TN'}...")
    actualizados = []
    errores = []
    sin_cambio = 0

    for product_id, variant_id, sku, nombre, precio_tn in variantes:
        if sku not in costos_erp:
            continue

        costo = costos_erp[sku]
        resultado = calcular_precio_canal(costo, regla_tn)
        if 'error' in resultado:
            continue

        precio_correcto = resultado['precio_venta']

        # Verificar si la diferencia supera la tolerancia
        if precio_tn > 0:
            diff_pct = abs(precio_correcto - precio_tn) / precio_tn * 100
        else:
            diff_pct = 100.0

        if diff_pct <= tolerancia_pct:
            sin_cambio += 1
            continue

        cambio = {
            'product_id': product_id,
            'variant_id': variant_id,
            'sku': sku,
            'nombre': nombre,
            'costo_erp': costo,
            'precio_tn_anterior': precio_tn,
            'precio_correcto': precio_correcto,
            'diferencia_pct': round(diff_pct, 1),
            'margen_real': resultado['margen_real'],
        }

        if dry_run:
            direccion = "↑" if precio_correcto > precio_tn else "↓"
            print(f"  [DRY] {sku:20s} | {nombre[:25]:25s} | "
                  f"${precio_tn:>10,.0f} {direccion} ${precio_correcto:>10,.0f} "
                  f"({diff_pct:+.1f}%) | margen {resultado['margen_real']}%")
            actualizados.append(cambio)
        else:
            try:
                client.actualizar_variante(product_id, variant_id, precio=precio_correcto)
                print(f"  [OK]  {sku:20s} | ${precio_tn:,.0f} → ${precio_correcto:,.0f}")
                actualizados.append(cambio)
            except Exception as e:
                error_msg = f"Error actualizando precio {sku}: {e}"
                print(f"  [ERR] {error_msg}")
                errores.append(error_msg)

    # --- Resumen ---
    print(f"\n{'='*60}")
    print(f"  RESUMEN {'(DRY RUN — nada se modificó)' if dry_run else ''}")
    print(f"{'='*60}")
    print(f"  Productos TN:         {len(productos)}")
    print(f"  Variantes con SKU:    {len(variantes)}")
    print(f"  SKUs con costo ERP:   {len(costos_erp)}")
    print(f"  Dentro de tolerancia: {sin_cambio}")
    print(f"  Actualizados:         {len(actualizados)}")
    if errores:
        print(f"  Errores:              {len(errores)}")

    if actualizados:
        subidas = sum(1 for a in actualizados if a['precio_correcto'] > a['precio_tn_anterior'])
        bajadas = len(actualizados) - subidas
        print(f"  Subidas de precio:    {subidas}")
        print(f"  Bajadas de precio:    {bajadas}")

    print(f"{'='*60}\n")

    return {
        'total_productos': len(productos),
        'total_variantes': len(variantes),
        'skus_con_costo': len(costos_erp),
        'sin_cambio': sin_cambio,
        'actualizados': actualizados,
        'errores': errores,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Sync precios ERP → TiendaNube')
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='Solo mostrar cambios sin aplicar')
    parser.add_argument('--tolerancia', type=float, default=2.0,
                        help='Porcentaje mínimo de diferencia para actualizar (default: 2%%)')
    parser.add_argument('--cotiz-usd', type=float, default=1170.0,
                        help='Cotización USD para artículos importados (default: 1170)')
    args = parser.parse_args()

    reporte = sincronizar_precios(dry_run=args.dry_run, tolerancia_pct=args.tolerancia,
                                  cotiz_usd=args.cotiz_usd)

    if reporte.get('error'):
        sys.exit(1)
    if reporte.get('errores'):
        sys.exit(2)
    sys.exit(0)
