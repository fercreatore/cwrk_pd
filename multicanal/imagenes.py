"""
Módulo de imágenes — consulta fotos del producto en PostgreSQL (VPS clz_productos)
y genera URLs públicas para publicar en TiendaNube / MercadoLibre.

La tabla producto_imagenes tiene:
  - cod_familia: primeros 8 chars del SKU base (agrupa talles)
  - producto_base: 10 chars (modelo+color)
  - path_relativo: ej "2/2722200048"
  - archivo_final: ej "2722200048-01.jpeg"
  - estado: 'activo'

Las imágenes se sirven vía HTTPS desde el VPS:
  https://n8n.calzalindo.com.ar/imagenes/{path_relativo}/{archivo_final}

USO:
    from multicanal.imagenes import buscar_imagenes_producto, urls_producto, url_publica

    # Buscar fotos de un SKU
    fotos = buscar_imagenes_producto('2722200048')

    # Obtener URLs públicas
    urls = urls_producto('2722200048')
    # ['https://n8n.calzalindo.com.ar/imagenes/2/2722200048/2722200048-01.jpeg', ...]

    # Para TiendaNube: publicar con URLs de imagen
    from multicanal.imagenes import imagenes_para_tn
    images_payload = imagenes_para_tn('2722200048')
    # [{'src': 'https://n8n.calzalindo.com.ar/imagenes/2/...'}, ...]
"""

import os
import base64
import psycopg2

PG_CONN_STRING = "postgresql://guille:Martes13%23@200.58.109.125:5432/clz_productos"

# URL base pública de imágenes en el VPS (servidas via n8n/nginx)
IMAGE_BASE_URL = os.environ.get('CLZ_IMAGE_URL', 'https://n8n.calzalindo.com.ar/imagenes')


def _get_pg_conn():
    return psycopg2.connect(PG_CONN_STRING)


def buscar_imagenes_producto(sku_o_codigo: str, solo_activas: bool = True) -> list:
    """
    Busca imágenes en producto_imagenes por producto_base o cod_familia.

    Args:
        sku_o_codigo: SKU base (10 chars) o cod_familia (8 chars) o codigo_sinonimo (12 chars)

    Returns:
        Lista de dicts con info de cada imagen, ordenadas por nro_imagen.
    """
    conn = _get_pg_conn()
    try:
        cur = conn.cursor()

        # Normalizar: si es codigo_sinonimo de 12 chars, usar primeros 10 como producto_base
        buscar = sku_o_codigo.strip()
        if len(buscar) >= 10:
            producto_base = buscar[:10]
        else:
            producto_base = buscar

        where_estado = "AND estado = 'activo'" if solo_activas else ""

        # Buscar por producto_base primero
        cur.execute(f"""
            SELECT id, cod_familia, producto_base, nro_imagen,
                   archivo_origen, path_relativo, archivo_final, ext, estado
            FROM producto_imagenes
            WHERE producto_base = %s {where_estado}
            ORDER BY nro_imagen
        """, (producto_base,))
        rows = cur.fetchall()

        # Si no encontró, buscar por cod_familia (primeros 8 chars)
        if not rows:
            cod_familia = buscar[:8]
            cur.execute(f"""
                SELECT id, cod_familia, producto_base, nro_imagen,
                       archivo_origen, path_relativo, archivo_final, ext, estado
                FROM producto_imagenes
                WHERE cod_familia = %s {where_estado}
                ORDER BY producto_base, nro_imagen
            """, (cod_familia,))
            rows = cur.fetchall()

        cols = ['id', 'cod_familia', 'producto_base', 'nro_imagen',
                'archivo_origen', 'path_relativo', 'archivo_final', 'ext', 'estado']

        resultado = []
        for row in rows:
            d = dict(zip(cols, row))
            d['path_completo'] = f"{d['path_relativo']}/{d['archivo_final']}"
            resultado.append(d)

        return resultado
    finally:
        conn.close()


def buscar_imagenes_por_skus(skus: list) -> dict:
    """
    Busca imágenes para múltiples SKUs de una vez.
    Retorna {sku: [imagenes]} agrupado por los primeros 10 chars del SKU.
    """
    if not skus:
        return {}

    conn = _get_pg_conn()
    try:
        cur = conn.cursor()

        # Agrupar SKUs por producto_base (primeros 10 chars)
        producto_bases = list(set(s.strip()[:10] for s in skus if len(s.strip()) >= 10))
        if not producto_bases:
            return {}

        placeholders = ','.join(['%s'] * len(producto_bases))
        cur.execute(f"""
            SELECT id, cod_familia, producto_base, nro_imagen,
                   archivo_origen, path_relativo, archivo_final, ext, estado
            FROM producto_imagenes
            WHERE producto_base IN ({placeholders})
              AND estado = 'activo'
            ORDER BY producto_base, nro_imagen
        """, producto_bases)

        cols = ['id', 'cod_familia', 'producto_base', 'nro_imagen',
                'archivo_origen', 'path_relativo', 'archivo_final', 'ext', 'estado']

        resultado = {}
        for row in cur.fetchall():
            d = dict(zip(cols, row))
            d['path_completo'] = f"{d['path_relativo']}/{d['archivo_final']}"
            key = d['producto_base']
            if key not in resultado:
                resultado[key] = []
            resultado[key].append(d)

        # Mapear cada SKU original a su producto_base
        final = {}
        for sku in skus:
            base = sku.strip()[:10]
            if base in resultado:
                final[sku] = resultado[base]

        return final
    finally:
        conn.close()


def contar_imagenes_totales() -> dict:
    """Estadísticas globales de imágenes."""
    conn = _get_pg_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                COUNT(*) AS total,
                COUNT(DISTINCT producto_base) AS productos,
                COUNT(DISTINCT cod_familia) AS familias,
                COUNT(*) FILTER (WHERE estado = 'activo') AS activas
            FROM producto_imagenes
        """)
        row = cur.fetchone()
        return {
            'total_imagenes': row[0],
            'productos_con_foto': row[1],
            'familias_con_foto': row[2],
            'activas': row[3],
        }
    finally:
        conn.close()


def url_publica(imagen: dict) -> str:
    """Genera la URL pública de la imagen (requiere nginx configurado en el VPS)."""
    return f"{IMAGE_BASE_URL}/{imagen['path_completo']}"


def urls_producto(sku: str) -> list:
    """Retorna lista de URLs públicas de todas las fotos de un SKU."""
    fotos = buscar_imagenes_producto(sku)
    return [url_publica(f) for f in fotos]


def imagenes_para_tn(sku: str) -> list:
    """
    Retorna lista de dicts con formato TiendaNube para el campo 'images'
    al crear/actualizar un producto.

    TiendaNube acepta: [{'src': 'https://...'}]

    Args:
        sku: codigo_sinonimo o producto_base

    Returns:
        [{'src': 'https://n8n.calzalindo.com.ar/imagenes/2/272.../272...-01.jpeg'}, ...]
    """
    fotos = buscar_imagenes_producto(sku)
    return [{'src': url_publica(f)} for f in fotos]


def imagenes_para_ml(sku: str) -> list:
    """
    Retorna lista de dicts con formato MercadoLibre para el campo 'pictures'.

    ML acepta: [{'source': 'https://...'}]
    """
    fotos = buscar_imagenes_producto(sku)
    return [{'source': url_publica(f)} for f in fotos]


def subir_imagen_a_tn(client, product_id: int, imagen: dict) -> dict:
    """
    Sube una imagen a un producto existente de TiendaNube usando URL pública.

    TiendaNube acepta:
    - src: URL pública de la imagen (preferido)
    - attachment: base64 encoded image (fallback)
    """
    url = url_publica(imagen)
    data = {
        'images': [{'src': url}]
    }

    try:
        result = client.actualizar_producto(product_id, data)
        return {'ok': True, 'url': url, 'detalle': result}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'url': url}
