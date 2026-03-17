"""
Facturador MercadoLibre → ERP MS Gestión.

Procesa ventas de MercadoLibre (depósito 1) e inserta factura B
(ventas2 cabecera + ventas1 detalle) en el ERP para registrar la venta.

Las ventas de ML se identifican en el ERP por:
  - deposito = 1 (asignado a ML)
  - usuario = 'COWORK-ML'

USO:
    # Dry run (solo muestra qué se insertaría)
    python -m multicanal.facturador_ml --dry-run

    # Ejecutar facturación real
    python -m multicanal.facturador_ml

    # Últimos 3 días
    python -m multicanal.facturador_ml --dry-run --dias 3

    # Desde código
    from multicanal.facturador_ml import sincronizar_ordenes_ml
    reporte = sincronizar_ordenes_ml(dry_run=True, dias_atras=7)

PREREQUISITOS:
    - Token de MercadoLibre válido (OAuth2, se vence cada 6 horas)
    - Configurar credenciales en mercadolibre_config.json
"""

import json
import os
import sys
import requests
import pyodbc
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Constantes ERP ──

CONN_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion03;"
    "UID=am;PWD=dl;"
    "Encrypt=no;"
)

CONN_STRING_ART = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion01art;"
    "UID=am;PWD=dl;"
    "Encrypt=no;"
)

# Parámetros fijos para factura B consumidor final — depósito 1 (ML)
CODIGO = 1          # factura
LETRA = 'B'         # consumidor final
SUCURSAL = 1
DEPOSITO = 1        # depósito 1 = MercadoLibre
ESTADO = 'V'
CONDICION_IVA = 'C'  # consumidor final
USUARIO = 'COWORK-ML'

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'mercadolibre_config.json')
LOG_FILE = os.path.join(os.path.dirname(__file__), 'ordenes_ml_procesadas.json')

ML_API_BASE = 'https://api.mercadolibre.com'


# ── Config ──

def guardar_config(access_token: str, user_id: str, refresh_token: str = ''):
    """Guarda credenciales de ML."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump({
            'access_token': access_token,
            'user_id': user_id,
            'refresh_token': refresh_token,
            'updated_at': datetime.now().isoformat(),
        }, f, indent=2)


def cargar_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


# ── Persistencia de órdenes procesadas ──

def cargar_ordenes_procesadas() -> dict:
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            return json.load(f)
    return {}


def guardar_ordenes_procesadas(registro: dict):
    with open(LOG_FILE, 'w') as f:
        json.dump(registro, f, indent=2, default=str)


# ── Cliente ML ──

def _ml_get(endpoint: str, token: str, params: dict = None) -> dict:
    """GET request a la API de MercadoLibre."""
    headers = {'Authorization': f'Bearer {token}'}
    r = requests.get(f'{ML_API_BASE}{endpoint}', headers=headers,
                     params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def obtener_ordenes_ml(token: str, user_id: str, dias_atras: int = 7) -> list:
    """
    Obtiene órdenes de ML con estado 'paid' de los últimos N días.
    Pagina automáticamente.
    """
    fecha_min = (datetime.now() - timedelta(days=dias_atras)).strftime('%Y-%m-%dT00:00:00.000-00:00')
    todas = []
    offset = 0
    limit = 50

    while True:
        data = _ml_get(
            f'/orders/search',
            token,
            params={
                'seller': user_id,
                'order.status': 'paid',
                'order.date_created.from': fecha_min,
                'sort': 'date_desc',
                'offset': offset,
                'limit': limit,
            }
        )
        results = data.get('results', [])
        todas.extend(results)

        total = data.get('paging', {}).get('total', 0)
        offset += limit
        if offset >= total or not results:
            break

    return todas


def extraer_skus_de_orden(orden: dict) -> list:
    """
    Extrae items de una orden de ML con SKU (seller_custom_field o seller_sku).
    """
    items = []
    for item in orden.get('order_items', []):
        ml_item = item.get('item', {})
        sku = (ml_item.get('seller_custom_field') or
               ml_item.get('seller_sku') or '').strip()
        items.append({
            'sku': sku,
            'titulo': ml_item.get('title', ''),
            'cantidad': item.get('quantity', 0),
            'precio': float(item.get('unit_price', 0)),
            'item_id': ml_item.get('id', ''),
        })
    return items


# ── Conexiones ERP ──

def conectar_erp():
    return pyodbc.connect(CONN_STRING, timeout=15)


def conectar_erp_art():
    return pyodbc.connect(CONN_STRING_ART, timeout=15)


def buscar_articulos_por_sku(conn_art, skus: list) -> dict:
    """Busca artículos en el ERP por codigo_sinonimo. Retorna {sku: {codigo, descripcion, precio_costo}}."""
    if not skus:
        return {}

    resultado = {}
    BATCH = 500
    for i in range(0, len(skus), BATCH):
        lote = skus[i:i + BATCH]
        placeholders = ",".join(["?"] * len(lote))
        query = f"""
            SELECT codigo, descripcion_1, precio_costo, codigo_sinonimo
            FROM msgestion01art.dbo.articulo
            WHERE codigo_sinonimo IN ({placeholders})
              AND codigo_sinonimo <> ''
        """
        cursor = conn_art.cursor()
        cursor.execute(query, lote)
        for row in cursor.fetchall():
            sku = row[3].strip() if row[3] else ''
            if sku:
                resultado[sku] = {
                    'codigo': int(row[0]),
                    'descripcion': (row[1] or '').strip(),
                    'precio_costo': float(row[2] or 0),
                    'codigo_sinonimo': sku,
                }
    return resultado


# ── Números de factura ──

def obtener_siguiente_numero(conn) -> int:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ISNULL(MAX(numero), 0) + 1
        FROM msgestion03.dbo.ventas2
        WHERE codigo = ? AND letra = ? AND sucursal = ?
    """, CODIGO, LETRA, SUCURSAL)
    return int(cursor.fetchone()[0])


def obtener_siguiente_orden(conn, fecha_comprobante: str) -> int:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ISNULL(MAX(orden), 0) + 1
        FROM msgestion03.dbo.ventas2
        WHERE codigo = ? AND letra = ? AND sucursal = ?
          AND CONVERT(date, fecha_comprobante) = CONVERT(date, ?)
    """, CODIGO, LETRA, SUCURSAL, fecha_comprobante)
    return int(cursor.fetchone()[0])


# ── Inserción ERP ──

def insertar_factura(conn, cabecera: dict, detalles: list):
    """Inserta ventas2 + ventas1 + descuenta stock dentro de una transacción."""
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO msgestion03.dbo.ventas2 (
                codigo, letra, sucursal, numero, orden,
                deposito, cuenta, denominacion, cuenta_cc,
                fecha_comprobante, fecha_proceso, fecha_contable,
                monto_general, importe_neto_ge, monto_exento,
                estado, estado_stock, estado_cc,
                estado_pedidos, condicion_iva, usuario, moneda,
                descuento_general, monto_descuento,
                bonificacion_general, monto_bonificacion,
                financiacion_general, monto_financiacion,
                iva1, monto_iva1, percepcion
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?
            )
        """,
            cabecera['codigo'], cabecera['letra'], cabecera['sucursal'],
            cabecera['numero'], cabecera['orden'],
            cabecera['deposito'], cabecera['cuenta'],
            cabecera['denominacion'], cabecera['cuenta_cc'],
            cabecera['fecha_comprobante'], cabecera['fecha_proceso'],
            cabecera['fecha_contable'],
            cabecera['monto_general'], cabecera['monto_general'], 0,
            cabecera['estado'], cabecera['estado_stock'], cabecera['estado_cc'],
            cabecera['estado_pedidos'], cabecera['condicion_iva'],
            cabecera['usuario'], cabecera['moneda'],
            0, 0,  # descuento
            0, 0,  # bonificacion
            0, 0,  # financiacion
            21, None, 0,  # iva, percepcion
        )

        for det in detalles:
            cursor.execute("""
                INSERT INTO msgestion03.dbo.ventas1 (
                    codigo, letra, sucursal, numero, orden,
                    renglon, articulo, descripcion,
                    precio, cantidad, total_item, unidades, deposito,
                    operacion, estado, estado_stock,
                    precio_costo, codigo_sinonimo, fecha
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?
                )
            """,
                det['codigo'], det['letra'], det['sucursal'],
                det['numero'], det['orden'],
                det['renglon'], det['articulo'], det['descripcion'],
                det['precio'], det['cantidad'], det['total_item'],
                det['unidades'], det['deposito'],
                det['operacion'], det['estado'], det['estado_stock'],
                det['precio_costo'], det['codigo_sinonimo'], det['fecha'],
            )

        # Descontar stock
        for det in detalles:
            cursor.execute("""
                UPDATE msgestion03.dbo.stock
                SET stock_actual = stock_actual - ?
                WHERE articulo = ? AND deposito = ?
            """, det['cantidad'], det['articulo'], det['deposito'])

        # Marcar estado_stock='V' para evitar doble descuento por batch ERP
        cursor.execute("""
            UPDATE msgestion03.dbo.ventas2
            SET estado_stock = 'V'
            WHERE codigo = ? AND letra = ? AND sucursal = ? AND numero = ? AND orden = ?
        """, cabecera['codigo'], cabecera['letra'], cabecera['sucursal'],
            cabecera['numero'], cabecera['orden'])

        cursor.execute("""
            UPDATE msgestion03.dbo.ventas1
            SET estado_stock = 'V'
            WHERE codigo = ? AND letra = ? AND sucursal = ? AND numero = ? AND orden = ?
        """, cabecera['codigo'], cabecera['letra'], cabecera['sucursal'],
            cabecera['numero'], cabecera['orden'])

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.autocommit = True


# ── Construir factura desde orden ML ──

def construir_factura(orden: dict, articulos_erp: dict, numero: int, orden_dia: int) -> tuple:
    """Arma cabecera y detalles desde una orden de ML."""
    fecha_orden_str = orden.get('date_created', '')[:10]
    try:
        fecha_comprobante = datetime.strptime(fecha_orden_str, '%Y-%m-%d')
    except ValueError:
        fecha_comprobante = datetime.now()

    # Nombre comprador
    buyer = orden.get('buyer', {})
    nombre = f"{buyer.get('first_name', '')} {buyer.get('last_name', '')}".strip()
    if not nombre:
        nombre = f"ML #{orden.get('id', '?')}"

    monto_general = float(orden.get('total_amount', 0))

    cabecera = {
        'codigo': CODIGO,
        'letra': LETRA,
        'sucursal': SUCURSAL,
        'numero': numero,
        'orden': orden_dia,
        'deposito': DEPOSITO,
        'cuenta': 0,
        'denominacion': nombre[:100],
        'cuenta_cc': 0,
        'fecha_comprobante': fecha_comprobante,
        'fecha_proceso': datetime.now(),
        'fecha_contable': fecha_comprobante,
        'monto_general': monto_general,
        'estado': ESTADO,
        'estado_stock': 'N',
        'estado_cc': '1',
        'estado_pedidos': 'N',
        'condicion_iva': CONDICION_IVA,
        'usuario': USUARIO,
        'moneda': 0,
    }

    detalles = []
    skus_no_encontrados = []
    renglon = 0

    for ml_item in extraer_skus_de_orden(orden):
        sku = ml_item['sku']
        cantidad = ml_item['cantidad']
        precio = ml_item['precio']

        if not sku:
            skus_no_encontrados.append(f"(sin SKU) {ml_item['titulo'][:40]}")
            continue

        art = articulos_erp.get(sku)
        if not art:
            skus_no_encontrados.append(sku)
            continue

        renglon += 1
        total_item = round(precio * cantidad, 2)
        detalles.append({
            'codigo': CODIGO,
            'letra': LETRA,
            'sucursal': SUCURSAL,
            'numero': numero,
            'orden': orden_dia,
            'renglon': renglon,
            'articulo': art['codigo'],
            'descripcion': art['descripcion'][:50],
            'precio': precio,
            'cantidad': cantidad,
            'total_item': total_item,
            'unidades': 0,
            'deposito': DEPOSITO,
            'operacion': '+',
            'estado': ESTADO,
            'estado_stock': 'N',
            'precio_costo': art['precio_costo'],
            'codigo_sinonimo': sku,
            'fecha': fecha_comprobante,
        })

    if detalles:
        cabecera['monto_general'] = round(sum(d['total_item'] for d in detalles), 2)

    return cabecera, detalles, skus_no_encontrados


# ── Flujo principal ──

def sincronizar_ordenes_ml(dry_run: bool = True, dias_atras: int = 7) -> dict:
    """
    Procesa órdenes pagadas de MercadoLibre e inserta facturas B en el ERP.
    """
    modo = "DRY RUN" if dry_run else "FACTURACION REAL"
    print(f"\n{'='*60}")
    print(f"  FACTURADOR MercadoLibre → ERP [{modo}]")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Buscando órdenes de los últimos {dias_atras} días")
    print(f"{'='*60}\n")

    config = cargar_config()
    if not config.get('access_token') or not config.get('user_id'):
        print("ERROR: No hay config de MercadoLibre. Ejecutar guardar_config() primero.")
        return {'error': 'Sin config MercadoLibre'}

    token = config['access_token']
    user_id = config['user_id']

    # 1. Obtener órdenes pagadas
    print(f"[1/5] Obteniendo órdenes pagadas desde ML...")
    try:
        ordenes = obtener_ordenes_ml(token, user_id, dias_atras)
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            print("ERROR: Token de ML expirado o inválido. Renovar access_token.")
            return {'error': 'Token ML expirado'}
        raise
    print(f"       {len(ordenes)} órdenes pagadas encontradas.\n")

    if not ordenes:
        return {'ordenes_encontradas': 0, 'ya_procesadas': 0, 'procesadas': 0, 'errores': []}

    # 2. Filtrar ya procesadas
    print("[2/5] Filtrando órdenes ya procesadas...")
    registro = cargar_ordenes_procesadas()
    ordenes_nuevas = [o for o in ordenes if str(o['id']) not in registro]
    print(f"       {len(ordenes) - len(ordenes_nuevas)} ya procesadas, {len(ordenes_nuevas)} nuevas.\n")

    if not ordenes_nuevas:
        return {
            'ordenes_encontradas': len(ordenes),
            'ya_procesadas': len(ordenes) - len(ordenes_nuevas),
            'procesadas': 0,
            'errores': [],
        }

    # 3. Recolectar SKUs y buscar en ERP
    print("[3/5] Mapeando SKUs a artículos del ERP...")
    todos_skus = set()
    for o in ordenes_nuevas:
        for item in extraer_skus_de_orden(o):
            if item['sku']:
                todos_skus.add(item['sku'])

    conn_art = conectar_erp_art()
    try:
        articulos_erp = buscar_articulos_por_sku(conn_art, list(todos_skus))
    finally:
        conn_art.close()

    print(f"       {len(todos_skus)} SKUs únicos en órdenes")
    print(f"       {len(articulos_erp)} encontrados en ERP")
    skus_faltantes = todos_skus - set(articulos_erp.keys())
    if skus_faltantes:
        print(f"       {len(skus_faltantes)} SKUs NO encontrados:")
        for s in sorted(skus_faltantes)[:15]:
            print(f"         - {s}")
    print()

    # 4. Procesar cada orden
    print(f"[4/5] {'Simulando' if dry_run else 'Insertando'} facturas...")
    conn = conectar_erp() if not dry_run else None

    procesadas = []
    errores = []

    try:
        for orden in ordenes_nuevas:
            order_id = orden['id']
            fecha_orden = orden.get('date_created', '')[:10]

            if dry_run:
                numero_factura = 999999
                orden_dia = 99
            else:
                numero_factura = obtener_siguiente_numero(conn)
                orden_dia = obtener_siguiente_orden(conn, fecha_orden)

            cabecera, detalles, skus_no_enc = construir_factura(
                orden, articulos_erp, numero_factura, orden_dia
            )

            if not detalles:
                msg = f"  [SKIP] Orden ML {order_id} — sin artículos válidos"
                if skus_no_enc:
                    msg += f" (SKUs: {', '.join(skus_no_enc[:5])})"
                print(msg)
                errores.append(f"Orden ML {order_id}: sin artículos válidos en ERP")
                continue

            total = cabecera['monto_general']
            renglones = len(detalles)
            cliente = cabecera['denominacion']

            if dry_run:
                print(f"  [DRY] ML {order_id} | {fecha_orden} | {cliente[:25]:25s} | "
                      f"{renglones} items | ${total:,.0f}")
                procesadas.append({
                    'order_id': order_id,
                    'fecha': fecha_orden,
                    'cliente': cliente,
                    'renglones': renglones,
                    'total': total,
                    'skus_no_encontrados': skus_no_enc,
                })
            else:
                try:
                    insertar_factura(conn, cabecera, detalles)
                    print(f"  [OK]  ML {order_id} → Factura B {SUCURSAL}-{numero_factura} | "
                          f"{renglones} items | ${total:,.0f}")

                    registro[str(order_id)] = {
                        'numero_factura': numero_factura,
                        'orden': orden_dia,
                        'fecha_proceso': datetime.now().isoformat(),
                        'total': total,
                        'renglones': renglones,
                    }
                    guardar_ordenes_procesadas(registro)

                    procesadas.append({
                        'order_id': order_id,
                        'numero_factura': numero_factura,
                        'fecha': fecha_orden,
                        'cliente': cliente,
                        'renglones': renglones,
                        'total': total,
                        'skus_no_encontrados': skus_no_enc,
                    })
                except Exception as e:
                    error_msg = f"Orden ML {order_id}: {e}"
                    print(f"  [ERR] {error_msg}")
                    errores.append(error_msg)
    finally:
        if conn:
            conn.close()

    # 5. Resumen
    print(f"\n{'='*60}")
    print(f"  RESUMEN {'(DRY RUN — nada se insertó)' if dry_run else ''}")
    print(f"{'='*60}")
    print(f"  Órdenes ML encontradas:   {len(ordenes)}")
    print(f"  Ya procesadas:            {len(ordenes) - len(ordenes_nuevas)}")
    print(f"  Nuevas a procesar:        {len(ordenes_nuevas)}")
    print(f"  Facturadas OK:            {len(procesadas)}")
    if errores:
        print(f"  Errores/skipped:          {len(errores)}")
    total_facturado = sum(p['total'] for p in procesadas)
    print(f"  Total facturado:          ${total_facturado:,.0f}")
    print(f"{'='*60}\n")

    return {
        'ordenes_encontradas': len(ordenes),
        'ya_procesadas': len(ordenes) - len(ordenes_nuevas),
        'procesadas': procesadas,
        'errores': errores,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Facturar órdenes MercadoLibre → ERP MS Gestión')
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='Solo mostrar qué se insertaría (default: False)')
    parser.add_argument('--dias', type=int, default=7,
                        help='Días hacia atrás para buscar órdenes (default: 7)')
    args = parser.parse_args()

    reporte = sincronizar_ordenes_ml(dry_run=args.dry_run, dias_atras=args.dias)

    if reporte.get('error'):
        sys.exit(1)
    if reporte.get('errores'):
        sys.exit(2)
    sys.exit(0)
