# -*- coding: utf-8 -*-
"""
Envío de catálogo de productos vía WhatsApp (Meta Cloud API + Chatwoot).

Genera mensajes con foto + precio + link TN para compartir productos
por WhatsApp Business. Usa la infraestructura de Chatwoot (chat.calzalindo.com.ar)
y Meta WhatsApp Cloud API.

Funciones principales:
  - enviar_catalogo_whatsapp(csrs, telefono): envía catálogo completo a un número
  - generar_mensaje_producto(csr): genera texto con foto+precio para un producto
  - enviar_producto_whatsapp(csr, telefono): envía un producto individual

USO:
    # Generar mensaje para un producto (sin enviar)
    python -m multicanal.whatsapp_catalogo --csr 272220004835 --preview

    # Enviar catálogo a un número
    python -m multicanal.whatsapp_catalogo --csr 272220004835,272220004836 --telefono 5493462672330

    # Generar catálogo para múltiples productos
    python -m multicanal.whatsapp_catalogo --estado-web A --preview --limit 5

PREREQUISITOS:
    - Meta WhatsApp Cloud API token vigente
    - Template aprobado en Meta Business (o usar envío dentro de ventana 24hs)
    - Chatwoot corriendo en chat.calzalindo.com.ar
"""

import json
import os
import ssl
import sys
import time
import urllib.request
import urllib.error
import pyodbc
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multicanal.imagenes import get_imagen_articulo, urls_producto
from multicanal.precios import calcular_precio_canal, cargar_reglas, REGLAS_DEFAULT

# ── Config ──

# SSL fix para macOS
try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()
    SSL_CTX.check_hostname = False
    SSL_CTX.verify_mode = ssl.CERT_NONE

# Chatwoot
CHATWOOT_URL = "https://chat.calzalindo.com.ar"
CHATWOOT_TOKEN = "zvQpseDYDoeqJpwM41GCb1LP"
CHATWOOT_ACCOUNT = 3
CHATWOOT_INBOX_ID = 9  # CALZLINDO 7436 (WhatsApp Cloud)

# Meta WhatsApp Cloud API
META_PHONE_NUMBER_ID = "1046697335188691"
META_ACCESS_TOKEN = "EAAT9fQyZAdWYBQ4qolDqcaRYaTT8tZAZBAMxHm2bwfhZAFLCDqkKEWNCXgQjlLGdUGJae0T1LY5rvVKh40uQLqQEgPXta1ssn1fWosn0BRynxrgf4k8BBwLH3D1Pk3klIlGbsILmPquDWCKUeCIkS6ra3rlhhEred73rbDb2TwrMm5z9x9U3hfUPxFG3KVPRdgZDZD"
META_GRAPH_URL = "https://graph.facebook.com/v21.0"

# ERP
ERP_CONN_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion01art;"
    "UID=am;PWD=dl;"
    "Encrypt=no;"
)

REGLAS_FILE = os.path.join(os.path.dirname(__file__), 'reglas_canales.json')

# Rate limiting
DELAY_ENTRE_MENSAJES = 5  # segundos entre mensajes dentro de ventana 24hs


# ── Consultas ERP ──

def _obtener_datos_producto(csr: str) -> dict:
    """Obtiene datos de un artículo del ERP por codigo_sinonimo."""
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


def _obtener_productos_estado_web(estado_web='A', limit=20) -> list:
    """Obtiene artículos con estado_web dado, agrupados por producto_base."""
    conn = pyodbc.connect(ERP_CONN_STRING, timeout=15)
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT TOP {int(limit)}
                   a.codigo, a.descripcion_1, a.precio_costo, a.precio_venta,
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
            WHERE a.estado_web = ?
              AND a.codigo_sinonimo IS NOT NULL
              AND a.codigo_sinonimo <> ''
              AND a.estado IN ('V', 'U')
              AND a.precio_venta > 0
            ORDER BY a.codigo DESC
        """, (estado_web,))

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                'codigo': int(row[0]),
                'descripcion': (row[1] or '').strip(),
                'precio_costo': float(row[2] or 0),
                'precio_venta': float(row[3] or 0),
                'codigo_sinonimo': (row[4] or '').strip(),
                'moneda': int(row[5] or 0),
                'marca': int(row[6] or 0),
                'marca_nombre': (row[7] or '').strip(),
                'stock': int(row[8] or 0),
            })
        return resultado
    finally:
        conn.close()


# ── Generación de mensajes ──

def generar_mensaje_producto(csr: str, incluir_link_tn=True) -> dict:
    """
    Genera un mensaje de WhatsApp para un producto.

    Retorna dict con:
        - texto: mensaje formateado
        - imagen_url: URL de la foto principal (o '' si no tiene)
        - producto: datos del ERP
        - precio_tn: precio calculado para TN/web
    """
    producto = _obtener_datos_producto(csr)
    if not producto:
        return {'ok': False, 'error': f'Producto no encontrado: {csr}'}

    # Calcular precio
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
    except Exception:
        imagen_url = ''

    # Generar texto
    nombre = producto['descripcion']
    marca = producto['marca_nombre']
    stock = max(producto['stock'], 0)

    lineas = []
    if marca:
        lineas.append(f"*{marca}*")
    lineas.append(f"*{nombre}*")
    lineas.append("")
    lineas.append(f"Precio: *${precio:,.0f}*")

    if stock > 0:
        if stock <= 3:
            lineas.append(f"Stock: {stock} (ultimas unidades)")
        else:
            lineas.append("Disponible con envio")
    else:
        lineas.append("Consultanos disponibilidad")

    lineas.append("")
    lineas.append("Envio gratis | Factura A y B")

    if incluir_link_tn:
        lineas.append("")
        lineas.append("Compra online: calzalindo.com.ar")

    texto = "\n".join(lineas)

    return {
        'ok': True,
        'texto': texto,
        'imagen_url': imagen_url,
        'producto': producto,
        'precio': precio,
    }


def generar_catalogo(csrs: list) -> list:
    """
    Genera mensajes para una lista de CSRs.
    Retorna lista de dicts con texto + imagen de cada producto.
    """
    resultado = []
    for csr in csrs:
        msg = generar_mensaje_producto(csr)
        resultado.append(msg)
    return resultado


# ── Envío via Meta WhatsApp Cloud API ──

def _enviar_mensaje_texto(telefono: str, texto: str) -> tuple:
    """Envía un mensaje de texto via Meta WhatsApp Cloud API."""
    url = f"{META_GRAPH_URL}/{META_PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": texto},
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Authorization": f"Bearer {META_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            msg_id = result.get("messages", [{}])[0].get("id", "?")
            return True, f"OK id={msg_id[:30]}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return False, f"HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return False, str(e)


def _enviar_imagen(telefono: str, imagen_url: str, caption: str = "") -> tuple:
    """Envía una imagen via Meta WhatsApp Cloud API."""
    url = f"{META_GRAPH_URL}/{META_PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "image",
        "image": {
            "link": imagen_url,
        },
    }
    if caption:
        payload["image"]["caption"] = caption

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Authorization": f"Bearer {META_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            msg_id = result.get("messages", [{}])[0].get("id", "?")
            return True, f"OK id={msg_id[:30]}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return False, f"HTTP {e.code}: {body[:200]}"
    except Exception as e:
        return False, str(e)


def enviar_producto_whatsapp(csr: str, telefono: str, dry_run=True) -> dict:
    """
    Envía un producto por WhatsApp: foto con caption (precio + info).

    NOTA: Requiere ventana de 24hs abierta con el destinatario
    (el contacto debe haber escrito primero), o usar template aprobado.
    """
    msg = generar_mensaje_producto(csr)
    if not msg.get('ok'):
        return msg

    resultado = {
        'ok': True,
        'dry_run': dry_run,
        'csr': csr,
        'telefono': telefono,
        'texto': msg['texto'],
        'imagen_url': msg['imagen_url'],
    }

    if dry_run:
        return resultado

    # Enviar imagen con caption si hay foto, sino solo texto
    if msg['imagen_url']:
        ok, detalle = _enviar_imagen(telefono, msg['imagen_url'], msg['texto'])
    else:
        ok, detalle = _enviar_mensaje_texto(telefono, msg['texto'])

    resultado['enviado'] = ok
    resultado['detalle'] = detalle
    return resultado


def enviar_catalogo_whatsapp(csrs: list, telefono: str, dry_run=True) -> dict:
    """
    Envía un catálogo de productos por WhatsApp.

    Envía cada producto como un mensaje individual (foto + caption).
    Incluye delay entre mensajes para respetar rate limits.

    Args:
        csrs: lista de codigo_sinonimo
        telefono: número destino (formato internacional sin +)
        dry_run: si True, solo genera mensajes sin enviar
    """
    modo = "DRY RUN" if dry_run else "ENVÍO REAL"
    print(f"\n{'='*60}")
    print(f"  CATÁLOGO WHATSAPP [{modo}]")
    print(f"  Destino: {telefono}")
    print(f"  Productos: {len(csrs)}")
    print(f"{'='*60}\n")

    enviados = 0
    fallidos = 0
    resultados = []

    for i, csr in enumerate(csrs):
        print(f"[{i+1}/{len(csrs)}] CSR: {csr}")
        res = enviar_producto_whatsapp(csr, telefono, dry_run=dry_run)
        resultados.append(res)

        if not res.get('ok'):
            print(f"  [ERR] {res.get('error')}")
            fallidos += 1
            continue

        if dry_run:
            print(f"  [DRY] {res['texto'][:60]}...")
            if res['imagen_url']:
                print(f"        Foto: {res['imagen_url'][:60]}...")
            enviados += 1
        else:
            if res.get('enviado'):
                print(f"  [OK]  {res['detalle']}")
                enviados += 1
            else:
                print(f"  [ERR] {res['detalle']}")
                fallidos += 1

            # Rate limit
            if i < len(csrs) - 1:
                time.sleep(DELAY_ENTRE_MENSAJES)

    print(f"\n{'='*60}")
    print(f"  RESUMEN: {enviados} enviados, {fallidos} fallidos")
    print(f"{'='*60}\n")

    return {
        'enviados': enviados,
        'fallidos': fallidos,
        'resultados': resultados,
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Catálogo WhatsApp — enviar productos por WA')
    parser.add_argument('--csr', type=str,
                        help='CSR(s) separados por coma')
    parser.add_argument('--telefono', type=str,
                        help='Número destino (formato: 5493462672330)')
    parser.add_argument('--preview', action='store_true', default=False,
                        help='Solo mostrar mensaje sin enviar')
    parser.add_argument('--estado-web', type=str, default=None,
                        help='Obtener productos por estado_web (ej: A)')
    parser.add_argument('--limit', type=int, default=5,
                        help='Límite de productos para --estado-web')
    args = parser.parse_args()

    if args.csr:
        csrs = [c.strip() for c in args.csr.split(',')]
    elif args.estado_web:
        productos = _obtener_productos_estado_web(args.estado_web, args.limit)
        csrs = [p['codigo_sinonimo'] for p in productos]
        print(f"Obtenidos {len(csrs)} productos con estado_web='{args.estado_web}'")
    else:
        print("Usar --csr o --estado-web para especificar productos")
        sys.exit(1)

    if args.preview or not args.telefono:
        # Preview mode
        for csr in csrs:
            msg = generar_mensaje_producto(csr)
            print(f"\n{'─'*40}")
            print(f"CSR: {csr}")
            if msg.get('ok'):
                print(f"Imagen: {msg['imagen_url'] or '(sin foto)'}")
                print(f"Precio: ${msg['precio']:,.0f}")
                print(f"\n{msg['texto']}")
            else:
                print(f"ERROR: {msg.get('error')}")
    else:
        enviar_catalogo_whatsapp(csrs, args.telefono, dry_run=False)
