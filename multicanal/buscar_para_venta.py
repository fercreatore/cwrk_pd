"""
Herramienta rápida de búsqueda para atención al cliente por WhatsApp.

Dado un código, sinónimo o descripción:
1. Busca el artículo en ERP
2. Muestra stock por talle y depósito
3. Si no hay stock en el talle pedido → busca sustitutos
4. Para cada resultado: foto (n8n) + link TN (si existe)
5. Genera mensaje listo para WhatsApp

USO:
    # Buscar por sinónimo/código parcial
    python -m multicanal.buscar_para_venta --codigo 84119 --talle 38

    # Buscar por descripción
    python -m multicanal.buscar_para_venta --desc "pantufla rosa cerrada" --talle 38

    # Solo sustitutos
    python -m multicanal.buscar_para_venta --codigo 84119 --talle 38 --sustitutos

    # Generar mensaje WhatsApp
    python -m multicanal.buscar_para_venta --codigo 84119 --talle 38 --whatsapp
"""

import argparse
import os
import sqlite3
import psycopg2
import pyodbc

from multicanal.imagenes import PG_CONN_STRING, IMAGE_BASE_URL

# SQL Server ERP (réplica 111 via MCP o directo)
ERP_CONN_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;DATABASE=msgestionC;"
    "UID=am;PWD=dl;TrustServerCertificate=yes"
)

MAPPING_DB = os.path.join(os.path.dirname(__file__), 'tn_mapping.db')
TN_BASE_URL = "https://www.calzalindo.com.ar/productos"


def _erp_conn():
    return pyodbc.connect(ERP_CONN_STRING)


def _pg_conn():
    return psycopg2.connect(PG_CONN_STRING)


def buscar_articulo(codigo=None, descripcion=None, limit=20):
    """Busca artículos en ERP por código parcial o descripción."""
    conn = _erp_conn()
    cur = conn.cursor()

    if codigo:
        cur.execute("""
            SELECT TOP (?) a.codigo, a.codigo_sinonimo, a.descripcion_1,
                   a.descripcion_4 as color, a.descripcion_5 as talle,
                   a.precio_1, a.precio_costo, a.marca, a.subrubro, a.rubro,
                   a.estado
            FROM msgestion01art.dbo.articulo a
            WHERE (a.codigo_sinonimo LIKE ? OR a.descripcion_1 LIKE ?)
            AND a.estado = 'V'
            ORDER BY a.descripcion_1
        """, (limit, f'%{codigo}%', f'%{codigo}%'))
    elif descripcion:
        # Split words and build AND condition
        words = descripcion.strip().split()
        where_parts = []
        params = [limit]
        for w in words:
            where_parts.append("a.descripcion_1 LIKE ?")
            params.append(f'%{w}%')
        where_clause = " AND ".join(where_parts)
        cur.execute(f"""
            SELECT TOP (?) a.codigo, a.codigo_sinonimo, a.descripcion_1,
                   a.descripcion_4 as color, a.descripcion_5 as talle,
                   a.precio_1, a.precio_costo, a.marca, a.subrubro, a.rubro,
                   a.estado
            FROM msgestion01art.dbo.articulo a
            WHERE {where_clause}
            AND a.estado = 'V'
            ORDER BY a.descripcion_1
        """, params)
    else:
        return []

    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()
    return rows


def stock_por_talle(codigo_sinonimo_base, talle=None):
    """Dado un código base (sin talle), busca stock de todos los talles."""
    # El base es los primeros 10 chars del sinónimo (sin talle)
    base = codigo_sinonimo_base[:10] if len(codigo_sinonimo_base) >= 10 else codigo_sinonimo_base

    conn = _erp_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT a.codigo, a.codigo_sinonimo, a.descripcion_1,
               a.descripcion_4 as color, a.descripcion_5 as talle,
               a.precio_1, a.marca, a.subrubro,
               ISNULL((SELECT SUM(s.stock_actual) FROM msgestionC.dbo.stock s
                        WHERE s.articulo = a.codigo AND s.stock_actual > 0), 0) as stock_total
        FROM msgestion01art.dbo.articulo a
        WHERE a.codigo_sinonimo LIKE ?
        AND a.estado = 'V'
        ORDER BY a.descripcion_5
    """, (f'{base}%',))

    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()

    if talle:
        return [r for r in rows if str(r['talle']).strip() == str(talle)]
    return rows


def buscar_sustitutos(subrubro, rubro, talle, precio_ref, marca=None, limit=15):
    """Busca sustitutos: mismo subrubro, con stock en el talle pedido, rango de precio similar."""
    conn = _erp_conn()
    cur = conn.cursor()

    precio_ref = float(precio_ref or 0)
    if precio_ref == 0:
        precio_min = 0
        precio_max = 999999999
    else:
        precio_min = precio_ref * 0.5
        precio_max = precio_ref * 1.5

    cur.execute("""
        SELECT TOP (?) a.codigo, a.codigo_sinonimo, a.descripcion_1,
               a.descripcion_4 as color, a.descripcion_5 as talle,
               a.precio_1, a.marca, a.subrubro,
               (SELECT SUM(s.stock_actual) FROM msgestionC.dbo.stock s
                WHERE s.articulo = a.codigo AND s.stock_actual > 0) as stock_total
        FROM msgestion01art.dbo.articulo a
        WHERE a.subrubro = ? AND a.rubro = ?
        AND a.descripcion_5 = ?
        AND a.estado = 'V'
        AND a.precio_1 BETWEEN ? AND ?
        AND EXISTS (SELECT 1 FROM msgestionC.dbo.stock s
                    WHERE s.articulo = a.codigo AND s.stock_actual > 0)
        ORDER BY
            CASE WHEN a.marca = ? THEN 0 ELSE 1 END,
            ABS(a.precio_1 - ?)
    """, (limit, subrubro, rubro, str(talle), precio_min, precio_max,
          marca or 0, precio_ref))

    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    conn.close()
    return rows


def obtener_imagen_url(codigo_sinonimo):
    """Busca imagen en PG y devuelve URL pública de n8n."""
    try:
        conn = _pg_conn()
        cur = conn.cursor()
        # producto_base = primeros 10 chars
        producto_base = codigo_sinonimo[:10] if len(codigo_sinonimo) >= 10 else codigo_sinonimo
        cur.execute("""
            SELECT path_relativo, archivo_final
            FROM producto_imagenes
            WHERE producto_base = %s AND estado = 'activo'
            ORDER BY nro_imagen
            LIMIT 1
        """, (producto_base,))
        row = cur.fetchone()
        conn.close()
        if row:
            return f"{IMAGE_BASE_URL}/{row[0]}/{row[1]}"
    except Exception:
        pass

    # Fallback: buscar por familia (primeros 8 chars)
    try:
        conn = _pg_conn()
        cur = conn.cursor()
        familia = codigo_sinonimo[:8]
        cur.execute("""
            SELECT path_relativo, archivo_final
            FROM producto_imagenes
            WHERE cod_familia = %s AND estado = 'activo'
            ORDER BY nro_imagen
            LIMIT 1
        """, (familia,))
        row = cur.fetchone()
        conn.close()
        if row:
            return f"{IMAGE_BASE_URL}/{row[0]}/{row[1]}"
    except Exception:
        pass

    return None


def obtener_link_tn(pg_producto_id=None, familia_id=None):
    """Busca link TN en el mapping SQLite."""
    if not os.path.exists(MAPPING_DB):
        return None

    conn = sqlite3.connect(MAPPING_DB)

    if pg_producto_id:
        row = conn.execute(
            "SELECT tiendanube_slug FROM tn_mapping WHERE pg_producto_id = ?",
            (pg_producto_id,)
        ).fetchone()
        if row and row[0]:
            conn.close()
            return f"{TN_BASE_URL}/{row[0]}"

    if familia_id:
        row = conn.execute(
            "SELECT tiendanube_slug FROM tn_mapping WHERE pg_familia_id = ?",
            (familia_id,)
        ).fetchone()
        if row and row[0]:
            conn.close()
            return f"{TN_BASE_URL}/{row[0]}"

    conn.close()
    return None


def obtener_pg_producto_id(codigo_sinonimo):
    """Busca el producto_id en PG por codigo_sinonimo."""
    try:
        conn = _pg_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT p.id, p.familia_id
            FROM producto_variantes pv
            JOIN productos p ON p.id = pv.producto_id
            WHERE pv.codigo_sinonimo = %s
            LIMIT 1
        """, (codigo_sinonimo,))
        row = cur.fetchone()
        conn.close()
        if row:
            return row[0], row[1]
    except Exception:
        pass
    return None, None


def enriquecer_producto(art):
    """Agrega imagen URL y link TN a un artículo del ERP."""
    csr = art.get('codigo_sinonimo', '')
    art['imagen_url'] = obtener_imagen_url(csr)
    pg_id, familia_id = obtener_pg_producto_id(csr)
    art['link_tn'] = obtener_link_tn(pg_id, familia_id)
    return art


def generar_mensaje_whatsapp(original, sustitutos):
    """Genera mensaje formateado para WhatsApp."""
    lines = []

    if original:
        art = original
        stock = art.get('stock_total', 0)
        if stock > 0:
            lines.append(f"Tenemos lo que buscás! 😊\n")
            lines.append(f"*{art['descripcion_1'].strip()}*")
            lines.append(f"Talle: {str(art.get('talle', '?')).strip()} | Stock: {int(stock)}")
            lines.append(f"Precio: *${float(art.get('precio_1') or 0):,.0f}*")
            if art.get('link_tn'):
                lines.append(f"👉 {art['link_tn']}")
        else:
            lines.append(f"Ese modelo en ese talle no lo tenemos en stock actualmente 😔")
            if sustitutos:
                lines.append(f"\nPero te conseguimos opciones similares:\n")

    if sustitutos:
        for i, s in enumerate(sustitutos[:5], 1):
            lines.append(f"✅ *Opción {i}: {s['descripcion_1'].strip()}*")
            lines.append(f"   Color: {(s.get('color') or '').strip()} | Talle: {s.get('talle', '?')}")
            lines.append(f"   Precio: *${float(s.get('precio_1') or 0):,.0f}* | Stock: {int(s.get('stock_total') or 0)}")
            if s.get('link_tn'):
                lines.append(f"   👉 {s['link_tn']}")
            if s.get('imagen_url'):
                lines.append(f"   📷 {s['imagen_url']}")
            lines.append("")

    if sustitutos:
        lines.append("Si te interesa alguna, te la separamos! 🙌")

    return "\n".join(lines)


def buscar_para_venta(codigo=None, descripcion=None, talle=None,
                      solo_sustitutos=False, formato_whatsapp=False):
    """Función principal: busca producto, stock, sustitutos, imágenes y links."""

    print(f"\n{'='*60}")
    print(f"  BUSCAR PARA VENTA")
    if codigo:
        print(f"  Código: {codigo}")
    if descripcion:
        print(f"  Descripción: {descripcion}")
    if talle:
        print(f"  Talle: {talle}")
    print(f"{'='*60}\n")

    # --- 1. Buscar artículo ---
    print("[1/4] Buscando artículo en ERP...")
    articulos = buscar_articulo(codigo=codigo, descripcion=descripcion)

    if not articulos:
        print("  No se encontraron artículos.")
        return

    # Agrupar por modelo (primeros 10 chars del sinónimo)
    modelos = {}
    for a in articulos:
        base = a['codigo_sinonimo'][:10] if a.get('codigo_sinonimo') else 'unknown'
        if base not in modelos:
            modelos[base] = a
    print(f"  {len(articulos)} artículos, {len(modelos)} modelos\n")

    # --- 2. Stock del primer modelo ---
    primer_modelo = list(modelos.values())[0]
    csr = primer_modelo.get('codigo_sinonimo', '')
    print(f"[2/4] Stock del modelo: {primer_modelo['descripcion_1'][:50]}")

    talles = stock_por_talle(csr)
    art_buscado = None

    print(f"\n  {'Talle':>5} | {'Stock':>5} | {'Precio':>10} | Color")
    print(f"  {'-'*5} | {'-'*5} | {'-'*10} | {'-'*15}")
    for t in talles:
        t_talle = str(t.get('talle') or '').strip()
        t_stock = int(t.get('stock_total') or 0)
        t_precio = float(t.get('precio_1') or 0)
        t_color = (t.get('color') or '').strip()
        marker = " ◄◄" if t_talle == str(talle) else ""
        print(f"  {t_talle:>5} | {t_stock:>5} | ${t_precio:>9,.0f} | {t_color}{marker}")
        if str(t.get('talle', '')).strip() == str(talle):
            art_buscado = t

    tiene_stock = art_buscado and art_buscado.get('stock_total', 0) > 0

    # --- 3. Enriquecer con imagen y link TN ---
    print(f"\n[3/4] Buscando imágenes y links TN...")
    if art_buscado:
        enriquecer_producto(art_buscado)
        print(f"  Imagen: {art_buscado.get('imagen_url') or '(sin foto)'}")
        print(f"  Link TN: {art_buscado.get('link_tn') or '(no publicado)'}")

    # --- 4. Sustitutos ---
    sustitutos_enriquecidos = []
    if talle and (not tiene_stock or solo_sustitutos):
        print(f"\n[4/4] Buscando sustitutos (subrubro={primer_modelo.get('subrubro')}, talle={talle})...")
        sust = buscar_sustitutos(
            subrubro=primer_modelo.get('subrubro'),
            rubro=primer_modelo.get('rubro'),
            talle=talle,
            precio_ref=primer_modelo.get('precio_1', 0),
            marca=primer_modelo.get('marca'),
        )
        print(f"  {len(sust)} sustitutos encontrados\n")

        for s in sust:
            enriquecer_producto(s)
            sustitutos_enriquecidos.append(s)
            img = "📷" if s.get('imagen_url') else "  "
            tn = "🔗" if s.get('link_tn') else "  "
            print(f"  {img}{tn} {s['descripcion_1'][:45]:45s} | "
                  f"{(s.get('color') or ''):10s} | ${float(s.get('precio_1') or 0):>9,.0f} | "
                  f"stk:{int(s.get('stock_total') or 0)}")
    else:
        print(f"\n[4/4] Producto con stock, no se buscan sustitutos.")

    # --- 5. Mensaje WhatsApp ---
    if formato_whatsapp:
        print(f"\n{'='*60}")
        print(f"  MENSAJE WHATSAPP")
        print(f"{'='*60}\n")
        msg = generar_mensaje_whatsapp(art_buscado, sustitutos_enriquecidos)
        print(msg)

    return {
        'articulo': art_buscado,
        'tiene_stock': tiene_stock,
        'sustitutos': sustitutos_enriquecidos,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Buscar producto para venta por WhatsApp')
    parser.add_argument('--codigo', '-c', help='Código, sinónimo parcial o modelo')
    parser.add_argument('--desc', '-d', help='Descripción (palabras clave)')
    parser.add_argument('--talle', '-t', help='Talle buscado')
    parser.add_argument('--sustitutos', '-s', action='store_true', help='Mostrar sustitutos aunque haya stock')
    parser.add_argument('--whatsapp', '-w', action='store_true', help='Generar mensaje WhatsApp')
    args = parser.parse_args()

    if not args.codigo and not args.desc:
        parser.error("Especificá --codigo o --desc")

    buscar_para_venta(
        codigo=args.codigo,
        descripcion=args.desc,
        talle=args.talle,
        solo_sustitutos=args.sustitutos,
        formato_whatsapp=args.whatsapp,
    )
