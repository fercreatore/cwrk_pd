# -*- coding: utf-8 -*-
"""
Generador de mensajes para vendedores freelance.

Dado un codigo_sinonimo, genera un mensaje WhatsApp listo para que
el vendedor lo reenvíe a sus clientes desde su celular.

Incluye:
  - Foto del producto (URL pública)
  - Nombre + marca
  - Precio de venta (calculado con margen freelance)
  - Link a TiendaNube
  - Texto copiable para reenviar

El vendedor no necesita saber el precio de costo ni tener acceso al ERP.
Solo recibe el mensaje armado y lo reenvía.

USO:
    # Ver mensaje para un producto
    python -m multicanal.publicar_freelance --csr 272220004835

    # Generar catálogo para múltiples productos
    python -m multicanal.publicar_freelance --csr 272220004835,272220004836

    # Generar para todos los estado_web='A'
    python -m multicanal.publicar_freelance --estado-web A --limit 10

    # Enviar al vendedor por WhatsApp
    python -m multicanal.publicar_freelance --csr 272220004835 --enviar 5493462672330
"""

import json
import os
import sys
import pyodbc
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multicanal.imagenes import get_imagen_articulo, urls_producto
from multicanal.precios import calcular_precio_canal, cargar_reglas, REGLAS_DEFAULT

# ── Config ──

ERP_CONN_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion01art;"
    "UID=am;PWD=dl;"
    "Encrypt=no;"
)

REGLAS_FILE = os.path.join(os.path.dirname(__file__), 'reglas_canales.json')

# URL base de la tienda online
TIENDA_URL = "https://calzalindo.com.ar"


# ── Consultas ERP ──

def _obtener_producto(csr: str) -> dict:
    """Obtiene datos de un artículo del ERP."""
    conn = pyodbc.connect(ERP_CONN_STRING, timeout=15)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.codigo, a.descripcion_1, a.precio_costo, a.precio_venta,
                   a.codigo_sinonimo, a.moneda, a.marca,
                   m.denominacion AS marca_nombre,
                   ISNULL(s.stock_total, 0) AS stock
            FROM msgestion01art.dbo.articulo a
            LEFT JOIN msgestion01art.dbo.marca m ON m.codigo = a.marca
            LEFT JOIN (
                SELECT articulo, SUM(stock_actual) AS stock_total
                FROM msgestionC.dbo.stock
                WHERE deposito IN (0, 1)
                GROUP BY articulo
            ) s ON s.articulo = a.codigo
            WHERE a.codigo_sinonimo = ?
              AND a.estado IN ('V', 'U')
        """, (csr,))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'codigo': int(row[0]),
            'descripcion': (row[1] or '').strip(),
            'precio_costo': float(row[2] or 0),
            'precio_venta': float(row[3] or 0),
            'codigo_sinonimo': (row[4] or '').strip(),
            'moneda': int(row[5] or 0),
            'marca': int(row[6] or 0),
            'marca_nombre': (row[7] or '').strip(),
            'stock': int(row[8] or 0),
        }
    finally:
        conn.close()


def _obtener_talles_modelo(csr: str) -> list:
    """Obtiene todos los talles disponibles de un modelo."""
    if len(csr) < 10:
        return []

    producto_base = csr[:10]
    conn = pyodbc.connect(ERP_CONN_STRING, timeout=15)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.codigo_sinonimo,
                   ISNULL(s.stock_total, 0) AS stock
            FROM msgestion01art.dbo.articulo a
            LEFT JOIN (
                SELECT articulo, SUM(stock_actual) AS stock_total
                FROM msgestionC.dbo.stock
                WHERE deposito IN (0, 1)
                GROUP BY articulo
            ) s ON s.articulo = a.codigo
            WHERE a.codigo_sinonimo LIKE ? + '%'
              AND a.estado IN ('V', 'U')
            ORDER BY a.codigo_sinonimo
        """, (producto_base,))

        talles = []
        for row in cursor.fetchall():
            full_csr = (row[0] or '').strip()
            stock = int(row[1] or 0)
            talle = full_csr[10:] if len(full_csr) > 10 else ''
            if stock > 0 and talle:
                talles.append(talle)
        return talles
    finally:
        conn.close()


# ── Generación de mensajes ──

def generar_mensaje_freelance(csr: str) -> dict:
    """
    Genera un mensaje WhatsApp listo para que un vendedor freelance
    lo reenvíe a sus clientes.

    El mensaje NO incluye precio de costo ni información interna.
    Solo datos públicos: nombre, marca, precio venta, talles, foto, link.

    Returns:
        dict con:
            - texto: mensaje formateado con emojis para WA
            - imagen_url: URL de la foto principal
            - producto: datos del ERP (para uso interno)
            - precio: precio de venta calculado
            - talles: lista de talles disponibles
    """
    producto = _obtener_producto(csr)
    if not producto:
        return {'ok': False, 'error': f'Producto no encontrado: {csr}'}

    # Calcular precio (usar regla tiendanube = mismo precio que web)
    reglas = cargar_reglas(REGLAS_FILE)
    regla_tn = reglas.get('tiendanube', REGLAS_DEFAULT.get('tiendanube'))

    costo = producto['precio_costo']
    if producto['moneda'] == 1:
        costo = costo * 1170.0

    precio_calc = calcular_precio_canal(costo, regla_tn)
    precio = precio_calc.get('precio_venta', producto['precio_venta'])

    # Imagen
    try:
        imagen_url = get_imagen_articulo(csr)
        todas_urls = urls_producto(csr)
    except Exception:
        imagen_url = ''
        todas_urls = []

    # Talles disponibles
    talles = _obtener_talles_modelo(csr)

    # Generar mensaje
    nombre = producto['descripcion']
    marca = producto['marca_nombre']

    lineas = []

    # Header con marca
    if marca:
        lineas.append(f"*{marca}*")

    # Nombre del producto
    lineas.append(f"*{nombre}*")
    lineas.append("")

    # Precio
    lineas.append(f"*${precio:,.0f}*")
    lineas.append("")

    # Talles disponibles
    if talles:
        lineas.append(f"Talles: {' | '.join(talles)}")
        lineas.append("")

    # Info de envío
    lineas.append("Envio gratis a todo el pais")
    lineas.append("Factura A y B")
    lineas.append("")

    # Link
    lineas.append(f"Ver mas en {TIENDA_URL}")

    texto = "\n".join(lineas)

    return {
        'ok': True,
        'texto': texto,
        'imagen_url': imagen_url,
        'todas_imagenes': todas_urls,
        'producto': producto,
        'precio': precio,
        'talles': talles,
    }


def generar_catalogo_freelance(csrs: list) -> list:
    """Genera mensajes para múltiples productos."""
    return [generar_mensaje_freelance(csr) for csr in csrs]


def enviar_a_vendedor(csr: str, telefono: str, dry_run=True) -> dict:
    """
    Envía el mensaje del producto al vendedor freelance por WhatsApp.

    Usa Meta Cloud API para enviar foto + texto.
    El vendedor luego reenvía desde su celular.
    """
    msg = generar_mensaje_freelance(csr)
    if not msg.get('ok'):
        return msg

    if dry_run:
        return {
            'ok': True,
            'dry_run': True,
            'csr': csr,
            'telefono': telefono,
            'texto': msg['texto'],
            'imagen_url': msg['imagen_url'],
        }

    # Importar función de envío de whatsapp_catalogo
    from multicanal.whatsapp_catalogo import _enviar_imagen, _enviar_mensaje_texto

    if msg['imagen_url']:
        ok, detalle = _enviar_imagen(telefono, msg['imagen_url'], msg['texto'])
    else:
        ok, detalle = _enviar_mensaje_texto(telefono, msg['texto'])

    return {
        'ok': ok,
        'dry_run': False,
        'csr': csr,
        'telefono': telefono,
        'detalle': detalle,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Generador de mensajes para vendedores freelance')
    parser.add_argument('--csr', type=str,
                        help='CSR(s) separados por coma')
    parser.add_argument('--estado-web', type=str, default=None,
                        help='Obtener productos por estado_web')
    parser.add_argument('--limit', type=int, default=10,
                        help='Límite de productos')
    parser.add_argument('--enviar', type=str, default=None,
                        help='Enviar al vendedor (número WA)')
    args = parser.parse_args()

    if args.csr:
        csrs = [c.strip() for c in args.csr.split(',')]
    elif args.estado_web:
        from multicanal.whatsapp_catalogo import _obtener_productos_estado_web
        productos = _obtener_productos_estado_web(args.estado_web, args.limit)
        csrs = [p['codigo_sinonimo'] for p in productos]
        print(f"Obtenidos {len(csrs)} productos con estado_web='{args.estado_web}'")
    else:
        print("Usar --csr o --estado-web")
        sys.exit(1)

    for csr in csrs:
        msg = generar_mensaje_freelance(csr)

        print(f"\n{'='*50}")
        print(f"CSR: {csr}")

        if not msg.get('ok'):
            print(f"ERROR: {msg.get('error')}")
            continue

        print(f"Imagen: {msg['imagen_url'] or '(sin foto)'}")
        print(f"Precio: ${msg['precio']:,.0f}")
        if msg['talles']:
            print(f"Talles: {', '.join(msg['talles'])}")
        print(f"{'─'*50}")
        print(msg['texto'])
        print(f"{'='*50}")

        if args.enviar:
            res = enviar_a_vendedor(csr, args.enviar, dry_run=False)
            if res.get('ok'):
                print(f"  Enviado: {res.get('detalle')}")
            else:
                print(f"  Error: {res.get('detalle', res.get('error'))}")
