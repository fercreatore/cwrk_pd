"""
Facturador TiendaNube → ERP MS Gestión.

Procesa órdenes pagadas de TiendaNube e inserta factura B (ventas2 cabecera +
ventas1 detalle) en el ERP para registrar la venta y descontar stock.

USO:
    # Dry run (solo muestra qué se insertaría)
    python -m multicanal.facturador_tn --dry-run

    # Ejecutar facturación real
    python -m multicanal.facturador_tn

    # Últimos 3 días
    python -m multicanal.facturador_tn --dry-run --dias 3

    # Desde código
    from multicanal.facturador_tn import sincronizar_ordenes_tn
    reporte = sincronizar_ordenes_tn(dry_run=True, dias_atras=7)
"""

import json
import os
import sys
import pyodbc
from datetime import datetime, timedelta

# Agregar raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multicanal.tiendanube import TiendaNubeClient, cargar_config


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

# Parámetros fijos para factura B consumidor final
# Empresa H4 → base msgestion03 (la tabla no tiene columna 'empresa')
CODIGO = 1          # factura
LETRA = 'B'         # consumidor final
SUCURSAL = 1
DEPOSITO = 0        # central, para TN
ESTADO = 'V'
CONDICION_IVA = 'C'  # consumidor final
USUARIO = 'COWORK-TN'

LOG_FILE = os.path.join(os.path.dirname(__file__), 'ordenes_procesadas.json')


# ── Persistencia de órdenes procesadas ──

def cargar_ordenes_procesadas() -> dict:
    """Carga el registro de órdenes ya facturadas."""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f:
            return json.load(f)
    return {}


def guardar_ordenes_procesadas(registro: dict):
    """Persiste el registro de órdenes facturadas."""
    with open(LOG_FILE, 'w') as f:
        json.dump(registro, f, indent=2, default=str)


# ── Conexión ERP ──

def conectar_erp():
    """Abre conexión pyodbc al SQL Server de producción (111) — base msgestion03."""
    return pyodbc.connect(CONN_STRING, timeout=15)


def conectar_erp_art():
    """Abre conexión pyodbc al SQL Server de producción (111) — base articulos."""
    return pyodbc.connect(CONN_STRING_ART, timeout=15)


# ── Consultas ERP ──

def buscar_articulos_por_sku(conn_art, skus: list) -> dict:
    """
    Dado un listado de SKUs, busca en articulo por codigo_sinonimo.
    Retorna dict {sku: {codigo, descripcion, precio_costo, codigo_sinonimo}}.
    """
    if not skus:
        return {}

    resultado = {}
    BATCH = 500
    for i in range(0, len(skus), BATCH):
        lote = skus[i:i + BATCH]
        placeholders = ",".join(["?"] * len(lote))

        query = f"""
            SELECT
                codigo,
                descripcion_1,
                precio_costo,
                codigo_sinonimo
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


def obtener_siguiente_numero(conn) -> int:
    """
    Obtiene el siguiente número de factura (MAX+1) para facturas B suc 1 empresa H4.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ISNULL(MAX(numero), 0) + 1
        FROM msgestion03.dbo.ventas2
        WHERE codigo = ?
          AND letra = ?
          AND sucursal = ?
    """, CODIGO, LETRA, SUCURSAL)
    row = cursor.fetchone()
    return int(row[0])


def obtener_siguiente_orden(conn, fecha_comprobante: str) -> int:
    """
    Obtiene la siguiente orden para la fecha dada (MAX+1 del día).
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ISNULL(MAX(orden), 0) + 1
        FROM msgestion03.dbo.ventas2
        WHERE codigo = ?
          AND letra = ?
          AND sucursal = ?
          AND CONVERT(date, fecha_comprobante) = CONVERT(date, ?)
    """, CODIGO, LETRA, SUCURSAL, fecha_comprobante)
    row = cursor.fetchone()
    return int(row[0])


# ── Inserción ERP ──

def insertar_factura(conn, cabecera: dict, detalles: list):
    """
    Inserta ventas2 (cabecera) + ventas1 (detalles) dentro de una transacción.
    Si algo falla, hace rollback completo.

    cabecera: dict con campos de ventas2
    detalles: lista de dicts con campos de ventas1
    """
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        # --- INSERT ventas2 (cabecera) ---
        # Campos reales de msgestion03.dbo.ventas2 (NO tiene columna 'empresa')
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
            cabecera['codigo'],
            cabecera['letra'],
            cabecera['sucursal'],
            cabecera['numero'],
            cabecera['orden'],
            cabecera['deposito'],
            cabecera['cuenta'],
            cabecera['denominacion'],
            cabecera['cuenta_cc'],
            cabecera['fecha_comprobante'],
            cabecera['fecha_proceso'],
            cabecera['fecha_contable'],
            cabecera['monto_general'],
            cabecera['monto_general'],  # importe_neto_ge = monto total (B sin IVA discriminado)
            0,                          # monto_exento
            cabecera['estado'],
            cabecera['estado_stock'],
            cabecera['estado_cc'],
            cabecera['estado_pedidos'],
            cabecera['condicion_iva'],
            cabecera['usuario'],
            cabecera['moneda'],
            0, 0,  # descuento_general, monto_descuento
            0, 0,  # bonificacion_general, monto_bonificacion
            0, 0,  # financiacion_general, monto_financiacion
            21, None,  # iva1=21%, monto_iva1=NULL (factura B, IVA incluido)
            0,      # percepcion
        )

        # --- INSERT ventas1 (detalles) ---
        # NO tiene columna 'empresa'
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
                det['codigo'],
                det['letra'],
                det['sucursal'],
                det['numero'],
                det['orden'],
                det['renglon'],
                det['articulo'],
                det['descripcion'],
                det['precio'],
                det['cantidad'],
                det['total_item'],
                det['unidades'],
                det['deposito'],
                det['operacion'],
                det['estado'],
                det['estado_stock'],
                det['precio_costo'],
                det['codigo_sinonimo'],
                det['fecha'],
            )

        # --- Descontar stock por cada línea de venta ---
        for det in detalles:
            cursor.execute("""
                UPDATE msgestion03.dbo.stock
                SET stock_actual = stock_actual - ?
                WHERE articulo = ? AND deposito = ?
            """, det['cantidad'], det['articulo'], det['deposito'])

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.autocommit = True


# ── Construir factura desde orden TN ──

def construir_factura(orden: dict, articulos_erp: dict, numero: int, orden_dia: int) -> tuple:
    """
    Arma cabecera (ventas2) y detalles (ventas1) a partir de una orden de TN.

    Args:
        orden: dict de la API TiendaNube
        articulos_erp: dict {sku: {codigo, descripcion, precio_costo, ...}}
        numero: número de factura asignado
        orden_dia: orden secuencial del día

    Returns:
        (cabecera_dict, detalles_list, skus_no_encontrados)
    """
    # Fecha de la orden
    fecha_orden_str = orden.get('created_at', '')[:10]
    try:
        fecha_comprobante = datetime.strptime(fecha_orden_str, '%Y-%m-%d')
    except ValueError:
        fecha_comprobante = datetime.now()

    fecha_proceso = datetime.now()

    # Nombre del cliente
    customer = orden.get('customer', {})
    nombre_cliente = f"{customer.get('name', '')}".strip()
    if not nombre_cliente:
        nombre_cliente = f"TiendaNube #{orden.get('number', orden['id'])}"

    # Monto total
    monto_general = float(orden.get('total', 0))

    cabecera = {
        'codigo': CODIGO,
        'letra': LETRA,
        'sucursal': SUCURSAL,
        'numero': numero,
        'orden': orden_dia,
        'deposito': DEPOSITO,
        'cuenta': 0,
        'denominacion': nombre_cliente[:100],
        'cuenta_cc': 0,
        'fecha_comprobante': fecha_comprobante,
        'fecha_proceso': fecha_proceso,
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

    for item in orden.get('products', []):
        sku = (item.get('sku') or '').strip()
        cantidad = int(item.get('quantity', 0))
        precio = float(item.get('price', 0))

        if not sku:
            skus_no_encontrados.append(f"(sin SKU) {item.get('name', '?')}")
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

    # Recalcular monto_general como suma de detalles (sin incluir envío)
    if detalles:
        cabecera['monto_general'] = round(sum(d['total_item'] for d in detalles), 2)

    return cabecera, detalles, skus_no_encontrados


# ── Flujo principal ──

def sincronizar_ordenes_tn(dry_run: bool = True, dias_atras: int = 7) -> dict:
    """
    Procesa órdenes pagadas de TiendaNube e inserta facturas B en el ERP.

    Args:
        dry_run: Si True, solo muestra qué se insertaría sin tocar el ERP.
        dias_atras: Cantidad de días hacia atrás para buscar órdenes.

    Returns:
        dict con resumen de procesamiento.
    """
    modo = "DRY RUN" if dry_run else "FACTURACION REAL"
    print(f"\n{'='*60}")
    print(f"  FACTURADOR TiendaNube → ERP [{modo}]")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Buscando órdenes de los últimos {dias_atras} días")
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

    # --- 1. Obtener órdenes pagadas ---
    fecha_min = (datetime.now() - timedelta(days=dias_atras)).strftime('%Y-%m-%d')
    print(f"[1/5] Obteniendo órdenes pagadas desde {fecha_min}...")

    ordenes = client.listar_todas_ordenes(
        payment_status='paid',
        created_at_min=fecha_min,
    )
    print(f"       {len(ordenes)} órdenes pagadas encontradas.\n")

    if not ordenes:
        print("No hay órdenes para procesar.")
        return {
            'ordenes_encontradas': 0,
            'ya_procesadas': 0,
            'procesadas': 0,
            'errores': [],
        }

    # --- 2. Filtrar ya procesadas ---
    print("[2/5] Filtrando órdenes ya procesadas...")
    registro = cargar_ordenes_procesadas()
    ordenes_nuevas = [o for o in ordenes if str(o['id']) not in registro]
    print(f"       {len(ordenes) - len(ordenes_nuevas)} ya procesadas, {len(ordenes_nuevas)} nuevas.\n")

    if not ordenes_nuevas:
        print("Todas las órdenes ya fueron procesadas.")
        return {
            'ordenes_encontradas': len(ordenes),
            'ya_procesadas': len(ordenes) - len(ordenes_nuevas),
            'procesadas': 0,
            'errores': [],
        }

    # --- 3. Recolectar SKUs y buscar en ERP ---
    print("[3/5] Mapeando SKUs a artículos del ERP...")
    todos_skus = set()
    for o in ordenes_nuevas:
        for item in o.get('products', []):
            sku = (item.get('sku') or '').strip()
            if sku:
                todos_skus.add(sku)

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
        if len(skus_faltantes) > 15:
            print(f"         ... y {len(skus_faltantes) - 15} más")
    print()

    # --- 4. Procesar cada orden ---
    print(f"[4/5] {'Simulando' if dry_run else 'Insertando'} facturas...")
    conn = conectar_erp() if not dry_run else None

    procesadas = []
    errores = []

    try:
        for orden in ordenes_nuevas:
            order_id = orden['id']
            order_number = orden.get('number', order_id)
            fecha_orden = orden.get('created_at', '')[:10]

            # Obtener número y orden
            if dry_run:
                # En dry run simulamos los números
                numero_factura = 999999
                orden_dia = 99
            else:
                numero_factura = obtener_siguiente_numero(conn)
                orden_dia = obtener_siguiente_orden(conn, fecha_orden)

            cabecera, detalles, skus_no_enc = construir_factura(
                orden, articulos_erp, numero_factura, orden_dia
            )

            if not detalles:
                msg = f"  [SKIP] Orden #{order_number} (TN {order_id}) — sin artículos válidos"
                if skus_no_enc:
                    msg += f" (SKUs no encontrados: {', '.join(skus_no_enc[:5])})"
                print(msg)
                errores.append(f"Orden #{order_number}: sin artículos válidos en ERP")
                continue

            total = cabecera['monto_general']
            renglones = len(detalles)
            cliente = cabecera['denominacion']

            if dry_run:
                print(f"  [DRY] Orden #{order_number} | {fecha_orden} | {cliente[:25]:25s} | "
                      f"{renglones} items | ${total:,.0f}")
                if skus_no_enc:
                    print(f"        SKUs sin match: {', '.join(skus_no_enc[:5])}")
                procesadas.append({
                    'order_id': order_id,
                    'order_number': order_number,
                    'fecha': fecha_orden,
                    'cliente': cliente,
                    'renglones': renglones,
                    'total': total,
                    'skus_no_encontrados': skus_no_enc,
                })
            else:
                try:
                    insertar_factura(conn, cabecera, detalles)
                    print(f"  [OK]  Orden #{order_number} → Factura B {SUCURSAL}-{numero_factura} | "
                          f"{renglones} items | ${total:,.0f} | {cliente[:25]}")
                    if skus_no_enc:
                        print(f"        SKUs sin match (omitidos): {', '.join(skus_no_enc[:5])}")

                    # Registrar como procesada
                    registro[str(order_id)] = {
                        'numero_factura': numero_factura,
                        'orden': orden_dia,
                        'fecha_proceso': datetime.now().isoformat(),
                        'order_number': order_number,
                        'total': total,
                        'renglones': renglones,
                    }
                    guardar_ordenes_procesadas(registro)

                    procesadas.append({
                        'order_id': order_id,
                        'order_number': order_number,
                        'numero_factura': numero_factura,
                        'fecha': fecha_orden,
                        'cliente': cliente,
                        'renglones': renglones,
                        'total': total,
                        'skus_no_encontrados': skus_no_enc,
                    })
                except Exception as e:
                    error_msg = f"Orden #{order_number} (TN {order_id}): {e}"
                    print(f"  [ERR] {error_msg}")
                    errores.append(error_msg)

    finally:
        if conn:
            conn.close()

    # --- 5. Resumen ---
    print(f"\n{'='*60}")
    print(f"  RESUMEN {'(DRY RUN — nada se insertó)' if dry_run else ''}")
    print(f"{'='*60}")
    print(f"  Órdenes TN encontradas:   {len(ordenes)}")
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
    parser = argparse.ArgumentParser(description='Facturar órdenes TiendaNube → ERP MS Gestión')
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='Solo mostrar qué se insertaría (default: False)')
    parser.add_argument('--dias', type=int, default=7,
                        help='Días hacia atrás para buscar órdenes (default: 7)')
    args = parser.parse_args()

    reporte = sincronizar_ordenes_tn(dry_run=args.dry_run, dias_atras=args.dias)

    if reporte.get('error'):
        sys.exit(1)
    if reporte.get('errores'):
        sys.exit(2)
    sys.exit(0)
