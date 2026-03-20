"""
Módulo de imágenes — consulta fotos del producto en PostgreSQL (VPS clz_productos)
y genera URLs o descarga binarios para publicar en TiendaNube / MercadoLibre.

La tabla producto_imagenes tiene:
  - cod_familia: primeros 8 chars del SKU base (agrupa talles)
  - producto_base: 10 chars (modelo+color)
  - path_relativo: ej "2/2722200048"
  - archivo_final: ej "2722200048-01.jpeg"
  - estado: 'activo'

Como las imágenes no están expuestas por HTTP, este módulo las lee
directamente como bytes desde el filesystem del VPS via SSH/SFTP
o las sirve como base64 para upload directo a las APIs.

USO:
    from multicanal.imagenes import buscar_imagenes_producto, obtener_imagen_bytes

    # Buscar fotos de un SKU
    fotos = buscar_imagenes_producto('2722200048')
    # [{'archivo_final': '2722200048-01.jpeg', 'path': '2/2722200048/2722200048-01.jpeg', ...}]

    # Para TiendaNube: subir imagen directo via API
    from multicanal.imagenes import subir_imagen_a_tn
    subir_imagen_a_tn(client, product_id, fotos[0])
"""

import os
import base64
import psycopg2

PG_CONN_STRING = "postgresql://guille:Martes13%23@200.58.109.125:5432/clz_productos"

# URL base para servir imágenes por HTTP.
# Configurar después de instalar nginx en el VPS con nginx_imagenes.conf
# Ejemplo: "https://calzalindo.com.ar/img" o "http://200.58.109.125:8088/img"
IMAGE_BASE_URL = os.environ.get('CLZ_IMAGE_URL', 'http://200.58.109.125:8088/img')


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


def obtener_imagen_base64(imagen: dict) -> str:
    """
    Lee la imagen original del filesystem del VPS y la convierte a base64.
    Requiere que el archivo exista en el path de imágenes del VPS.

    NOTA: Esta función solo funciona si se ejecuta en el VPS o si hay
    acceso al filesystem montado. Para uso remoto, usar la versión SSH.
    """
    # Path en el VPS: /var/www/imagenes/{path_relativo}/{archivo_final}
    # Ajustar según donde estén montadas las imágenes
    posibles_bases = [
        '/var/www/imagenes',
        '/var/www/html/imagenes',
        '/home/guille/imagenes',
        '/opt/imagenes',
    ]

    path_rel = imagen['path_completo']
    for base_path in posibles_bases:
        full_path = os.path.join(base_path, path_rel)
        if os.path.exists(full_path):
            with open(full_path, 'rb') as f:
                data = f.read()
            return base64.b64encode(data).decode('utf-8')

    return None


def subir_imagen_a_tn(client, product_id: int, imagen: dict) -> dict:
    """
    Sube una imagen del catálogo PostgreSQL a un producto de TiendaNube.

    TiendaNube acepta:
    - src: URL pública de la imagen
    - attachment: base64 encoded image

    Como no hay URL pública, intentamos base64. Si no se puede leer
    el archivo, retorna error.
    """
    b64 = obtener_imagen_base64(imagen)
    if not b64:
        return {'ok': False, 'error': f"No se pudo leer {imagen['path_completo']}"}

    ext = imagen.get('ext', '.jpeg').lstrip('.')
    data = {
        'images': [{
            'attachment': b64,
            'filename': imagen['archivo_final'],
        }]
    }

    try:
        result = client.actualizar_producto(product_id, data)
        return {'ok': True, 'detalle': result}
    except Exception as e:
        return {'ok': False, 'error': str(e)}
