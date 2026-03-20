# -*- coding: utf-8 -*-
"""
Módulo de publicación multicanal (standalone, sin web2py).

Canales:
  - MercadoLibre (API REST directa)
  - Tienda Nube  (API REST directa)
  - Meta Catalog (Graph API) → Facebook + Instagram + WhatsApp

Uso:
    from multicanal.canales import CanalTiendaNube
    canal = CanalTiendaNube(token='xxx', store_id='123')
    canal.publicar_producto({...})


    from multicanal.canales import publicar_producto_nuevo
    resultado = publicar_producto_nuevo('272220004835', dry_run=True)
"""
import json
import logging
import os
import time
import requests

logger = logging.getLogger('multicanal.canales')

# Rate limiting por canal (requests por segundo)
RATE_LIMITS = {
    'tiendanube': 2.0,   # TN permite ~2 req/s
    'mercadolibre': 1.0,  # ML es más estricto
    'meta': 5.0,
}


class CanalBase:
    """Interfaz base para todos los canales."""
    nombre = 'base'

    def publicar_producto(self, producto):
        raise NotImplementedError

    def actualizar_precio(self, id_externo, precio):
        raise NotImplementedError

    def actualizar_stock(self, id_externo, stock):
        raise NotImplementedError

    def pausar(self, id_externo):
        raise NotImplementedError

    def obtener_producto(self, id_externo):
        raise NotImplementedError

    def publicar_batch(self, productos, batch_size=10, dry_run=False):
        """
        Publica una lista de productos de a lotes con rate limiting.

        Args:
            productos: lista de dicts con al menos {sku, nombre, precio, stock, imagenes}
            batch_size: cantidad de productos por lote
            dry_run: si True, solo simula sin hacer requests

        Returns:
            dict con {ok: [...], errores: [...], total, publicados, fallidos}
        """
        rate = RATE_LIMITS.get(self.nombre, 1.0)
        delay = 1.0 / rate

        resultados_ok = []
        resultados_err = []

        for i in range(0, len(productos), batch_size):
            lote = productos[i:i + batch_size]
            lote_num = (i // batch_size) + 1
            total_lotes = (len(productos) + batch_size - 1) // batch_size
            logger.info("Lote %d/%d (%d productos)", lote_num, total_lotes, len(lote))

            for producto in lote:
                sku = producto.get('sku', '?')

                # Validar campos mínimos
                if not producto.get('sku') or not producto.get('nombre'):
                    resultados_err.append({'sku': sku, 'error': 'Faltan campos obligatorios (sku/nombre)'})
                    continue
                if not producto.get('imagenes'):
                    resultados_err.append({'sku': sku, 'error': 'Sin imágenes'})
                    continue
                if producto.get('stock', 0) <= 0:
                    resultados_err.append({'sku': sku, 'error': 'Stock <= 0'})
                    continue

                if dry_run:
                    resultados_ok.append({
                        'sku': sku,
                        'nombre': producto['nombre'],
                        'precio': producto.get('precio', 0),
                        'stock': producto.get('stock', 0),
                        'dry_run': True,
                    })
                    continue

                try:
                    resultado = self.publicar_producto(producto)
                    if resultado.get('ok'):
                        resultados_ok.append({
                            'sku': sku,
                            'id_externo': resultado.get('id_externo', ''),
                            'url': resultado.get('url', ''),
                        })
                    else:
                        resultados_err.append({
                            'sku': sku,
                            'error': resultado.get('error', 'Error desconocido'),
                            'status_code': resultado.get('status_code'),
                        })
                except Exception as e:
                    resultados_err.append({'sku': sku, 'error': str(e)})

                time.sleep(delay)

        reporte = {
            'total': len(productos),
            'publicados': len(resultados_ok),
            'fallidos': len(resultados_err),
            'ok': resultados_ok,
            'errores': resultados_err,
        }

        logger.info("Batch terminado: %d/%d publicados, %d errores",
                     reporte['publicados'], reporte['total'], reporte['fallidos'])

        return reporte


class CanalTiendaNube(CanalBase):
    """
    API docs: https://tiendanube.github.io/api-documentation/resources/product
    """
    nombre = 'tiendanube'
    API_BASE = 'https://api.tiendanube.com/v1'

    def __init__(self, token, store_id):
        self.token = token
        self.store_id = store_id
        self.headers = {
            'Authentication': 'bearer %s' % token,
            'User-Agent': 'CLZ Multicanal (calzalindo)',
            'Content-Type': 'application/json',
        }

    def _url(self, recurso):
        return '%s/%s/%s' % (self.API_BASE, self.store_id, recurso)

    def publicar_producto(self, producto):
        data = {
            'name': {'es': producto.get('nombre', '')},
            'description': {'es': producto.get('descripcion', '')},
            'published': True,
            'variants': [{
                'price': producto.get('precio', 0),
                'stock': producto.get('stock', 0),
                'sku': producto.get('sku', ''),
            }],
        }
        if producto.get('imagenes'):
            data['images'] = [{'src': url} for url in producto['imagenes']]

        r = requests.post(self._url('products'), json=data, headers=self.headers)
        if r.status_code in (200, 201):
            resp = r.json()
            return {'ok': True, 'id_externo': str(resp.get('id', '')), 'url': resp.get('canonical_url', ''), 'detalle': resp}
        return {'ok': False, 'error': r.text, 'status_code': r.status_code}

    def actualizar_precio(self, id_externo, precio, variante_id=None):
        if variante_id:
            url = self._url('products/%s/variants/%s' % (id_externo, variante_id))
            r = requests.put(url, json={'price': str(precio)}, headers=self.headers)
        else:
            url = self._url('products/%s' % id_externo)
            r = requests.put(url, json={'variants': [{'price': str(precio)}]}, headers=self.headers)
        return {'ok': r.status_code == 200, 'detalle': r.text}

    def actualizar_stock(self, id_externo, stock, variante_id=None):
        if variante_id:
            url = self._url('products/%s/variants/%s' % (id_externo, variante_id))
            r = requests.put(url, json={'stock': stock}, headers=self.headers)
        else:
            url = self._url('products/%s' % id_externo)
            r = requests.put(url, json={'variants': [{'stock': stock}]}, headers=self.headers)
        return {'ok': r.status_code == 200, 'detalle': r.text}

    def pausar(self, id_externo):
        r = requests.put(self._url('products/%s' % id_externo), json={'published': False}, headers=self.headers)
        return {'ok': r.status_code == 200}

    def obtener_producto(self, id_externo):
        r = requests.get(self._url('products/%s' % id_externo), headers=self.headers)
        if r.status_code == 200:
            return {'ok': True, 'producto': r.json()}
        return {'ok': False, 'error': r.text}

    def listar_productos(self, page=1, per_page=30):
        r = requests.get(self._url('products?page=%d&per_page=%d' % (page, per_page)), headers=self.headers)
        if r.status_code == 200:
            return {'ok': True, 'productos': r.json()}
        return {'ok': False, 'error': r.text}


class CanalMeta(CanalBase):
    """
    Meta Commerce Catalog → Facebook Shop + Instagram Shopping + WhatsApp Catalog.
    API docs: https://developers.facebook.com/docs/marketing-api/catalog/
    """
    nombre = 'meta'
    GRAPH_URL = 'https://graph.facebook.com/v22.0'

    def __init__(self, token, catalog_id):
        self.token = token
        self.catalog_id = catalog_id

    def _headers(self):
        return {'Authorization': 'Bearer %s' % self.token}

    def publicar_producto(self, producto):
        precio_centavos = int(producto.get('precio', 0) * 100)
        data = {
            'retailer_id': producto.get('sku', ''),
            'name': producto.get('nombre', ''),
            'description': producto.get('descripcion', ''),
            'price': '%d' % precio_centavos,
            'currency': producto.get('moneda', 'ARS'),
            'availability': 'in stock' if producto.get('stock', 0) > 0 else 'out of stock',
            'brand': producto.get('marca', 'Calzalindo'),
            'url': producto.get('url_producto', ''),
            'image_url': producto.get('url_imagen', ''),
        }
        r = requests.post('%s/%s/products' % (self.GRAPH_URL, self.catalog_id), data=data, headers=self._headers())
        if r.status_code in (200, 201):
            resp = r.json()
            return {'ok': True, 'id_externo': str(resp.get('id', '')), 'url': '', 'detalle': resp}
        return {'ok': False, 'error': r.text, 'status_code': r.status_code}

    def actualizar_precio(self, id_externo, precio):
        precio_centavos = int(precio * 100)
        r = requests.post('%s/%s' % (self.GRAPH_URL, id_externo),
                          data={'price': '%d' % precio_centavos, 'currency': 'ARS'}, headers=self._headers())
        return {'ok': r.status_code == 200, 'detalle': r.text}

    def actualizar_stock(self, id_externo, stock):
        disponibilidad = 'in stock' if stock > 0 else 'out of stock'
        r = requests.post('%s/%s' % (self.GRAPH_URL, id_externo),
                          data={'availability': disponibilidad}, headers=self._headers())
        return {'ok': r.status_code == 200, 'detalle': r.text}

    def pausar(self, id_externo):
        return self.actualizar_stock(id_externo, 0)

    def obtener_producto(self, id_externo):
        r = requests.get('%s/%s' % (self.GRAPH_URL, id_externo),
                         params={'fields': 'id,name,price,availability,image_url'}, headers=self._headers())
        if r.status_code == 200:
            return {'ok': True, 'producto': r.json()}
        return {'ok': False, 'error': r.text}


class CanalMercadoLibre(CanalBase):
    """MercadoLibre API."""
    nombre = 'mercadolibre'

    def __init__(self, token, user_id):
        self.token = token
        self.user_id = user_id

    def _headers(self):
        return {'Authorization': 'Bearer %s' % self.token, 'Content-Type': 'application/json'}

    def publicar_producto(self, producto):
        data = {
            'title': producto.get('titulo', producto.get('nombre', '')),
            'category_id': producto.get('categoria', ''),
            'price': producto.get('precio', 0),
            'currency_id': 'ARS',
            'available_quantity': producto.get('stock', 1),
            'condition': 'new',
            'listing_type_id': producto.get('tipo_publicacion', 'gold_special'),
            'pictures': [{'source': url} for url in producto.get('imagenes', [])],
        }
        if producto.get('sku'):
            data['seller_custom_field'] = producto['sku']
        if producto.get('atributos'):
            data['attributes'] = producto['atributos']

        r = requests.post('https://api.mercadolibre.com/items', json=data, headers=self._headers())
        if r.status_code in (200, 201):
            resp = r.json()
            return {'ok': True, 'id_externo': resp.get('id', ''), 'url': resp.get('permalink', ''), 'detalle': resp}
        return {'ok': False, 'error': r.text, 'status_code': r.status_code}

    def actualizar_precio(self, id_externo, precio):
        r = requests.put('https://api.mercadolibre.com/items/%s' % id_externo,
                         json={'price': precio}, headers=self._headers())
        return {'ok': r.status_code == 200, 'detalle': r.text}

    def actualizar_stock(self, id_externo, stock):
        r = requests.put('https://api.mercadolibre.com/items/%s' % id_externo,
                         json={'available_quantity': stock}, headers=self._headers())
        return {'ok': r.status_code == 200, 'detalle': r.text}

    def pausar(self, id_externo):
        r = requests.put('https://api.mercadolibre.com/items/%s' % id_externo,
                         json={'status': 'paused'}, headers=self._headers())
        return {'ok': r.status_code == 200}

    def reactivar(self, id_externo):
        r = requests.put('https://api.mercadolibre.com/items/%s' % id_externo,
                         json={'status': 'active'}, headers=self._headers())
        return {'ok': r.status_code == 200}

    def obtener_producto(self, id_externo):
        r = requests.get('https://api.mercadolibre.com/items/%s' % id_externo, headers=self._headers())
        if r.status_code == 200:
            return {'ok': True, 'producto': r.json()}
        return {'ok': False, 'error': r.text}

    def listar_productos(self, status='active', offset=0, limit=50):
        """Lista publicaciones del vendedor."""
        r = requests.get(
            'https://api.mercadolibre.com/users/%s/items/search' % self.user_id,
            params={'status': status, 'offset': offset, 'limit': limit},
            headers=self._headers(),
        )
        if r.status_code == 200:
            return {'ok': True, 'items': r.json().get('results', []), 'total': r.json().get('paging', {}).get('total', 0)}
        return {'ok': False, 'error': r.text}


# ── Publicación de producto nuevo (orquestador) ──

# Conexión a producción 111 (SELECT para consultas de artículos)
# NOTA: réplica 112 no tiene usuario am/dl configurado
_ERP_CONN_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion01art;"
    "UID=am;PWD=dl;"
    "Encrypt=no;"
)


def _consultar_articulo_erp(codigo_sinonimo: str) -> dict:
    """
    Busca un artículo en la réplica (112) por codigo_sinonimo.
    Retorna dict con datos del artículo o None si no existe.
    """
    import pyodbc
    conn = pyodbc.connect(_ERP_CONN_STRING, timeout=15)
    try:
        cursor = conn.cursor()

        # Buscar artículo
        cursor.execute("""
            SELECT a.codigo, a.descripcion_1, a.precio_costo, a.precio_venta,
                   a.codigo_sinonimo, a.codigo_barra, a.moneda,
                   a.grupo, a.marca, a.estado,
                   m.denominacion AS marca_nombre
            FROM msgestion01art.dbo.articulo a
            LEFT JOIN msgestion01art.dbo.marca m ON m.codigo = a.marca
            WHERE a.codigo_sinonimo = ?
              AND a.codigo_sinonimo <> ''
        """, (codigo_sinonimo,))
        row = cursor.fetchone()
        if not row:
            return None

        articulo = {
            'codigo': int(row[0]),
            'descripcion': (row[1] or '').strip(),
            'precio_costo': float(row[2] or 0),
            'precio_venta': float(row[3] or 0),
            'codigo_sinonimo': (row[4] or '').strip(),
            'codigo_barra': (row[5] or '').strip() if row[5] else '',
            'moneda': int(row[6] or 0),
            'grupo': int(row[7] or 0),
            'marca': int(row[8] or 0),
            'estado': (row[9] or '').strip(),
            'marca_nombre': (row[10] or '').strip(),
        }

        # Obtener stock (depósitos 0 y 1)
        cursor.execute("""
            SELECT ISNULL(SUM(s.stock_actual), 0)
            FROM msgestionC.dbo.stock s
            WHERE s.articulo = ? AND s.deposito IN (0, 1)
        """, (articulo['codigo'],))
        stock_row = cursor.fetchone()
        articulo['stock'] = int(stock_row[0]) if stock_row else 0

        return articulo
    finally:
        conn.close()


def _buscar_variantes_por_modelo(codigo_sinonimo: str) -> list:
    """
    Busca todas las variantes (talles) de un modelo.
    Un modelo comparte los primeros 10 chars del codigo_sinonimo (producto_base).
    Los últimos 2 chars son el talle.
    """
    import pyodbc
    if len(codigo_sinonimo) < 10:
        return []

    producto_base = codigo_sinonimo[:10]
    conn = pyodbc.connect(_REPLICA_CONN_STRING, timeout=15)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.codigo, a.descripcion_1, a.precio_costo, a.precio_venta,
                   a.codigo_sinonimo, a.estado,
                   ISNULL(s.stock_total, 0) AS stock
            FROM msgestion01art.dbo.articulo a
            LEFT JOIN (
                SELECT articulo, SUM(stock_actual) AS stock_total
                FROM msgestionC.dbo.stock
                WHERE deposito IN (0, 1)
                GROUP BY articulo
            ) s ON s.articulo = a.codigo
            WHERE a.codigo_sinonimo LIKE ? + '%'
              AND a.codigo_sinonimo <> ''
              AND a.estado IN ('V', 'U')
            ORDER BY a.codigo_sinonimo
        """, (producto_base,))

        variantes = []
        for row in cursor.fetchall():
            csr = (row[4] or '').strip()
            talle_code = csr[10:] if len(csr) > 10 else ''
            variantes.append({
                'codigo': int(row[0]),
                'descripcion': (row[1] or '').strip(),
                'precio_costo': float(row[2] or 0),
                'precio_venta': float(row[3] or 0),
                'codigo_sinonimo': csr,
                'estado': (row[5] or '').strip(),
                'stock': int(row[6]),
                'talle_code': talle_code,
            })
        return variantes
    finally:
        conn.close()


def publicar_producto_nuevo(codigo_sinonimo: str, dry_run: bool = True,
                             empresa: str = 'H4') -> dict:
    """
    Publica un producto nuevo en TiendaNube.

    Orquesta todo el flujo:
    1. Busca datos del artículo en réplica 112
    2. Busca variantes (talles) del mismo modelo
    3. Obtiene URLs de imágenes desde PostgreSQL (VPS)
    4. Calcula precio TN según reglas del canal
    5. Arma payload TN
    6. DRY RUN: muestra el payload sin ejecutar

    Args:
        codigo_sinonimo: CSR del artículo (12 chars: PPP+AAAAA+CC+TT)
        dry_run: Si True, solo muestra payload sin publicar
        empresa: 'H4' o 'CALZALINDO'

    Returns:
        dict con payload armado y resultado de publicación

    USO:
        from multicanal.canales import publicar_producto_nuevo
        resultado = publicar_producto_nuevo('272220004835', dry_run=True)
    """
    from multicanal.precios import calcular_precio_canal, cargar_reglas, REGLAS_DEFAULT
    from multicanal.imagenes import imagenes_para_tn, urls_producto
    from multicanal.tiendanube import TiendaNubeClient, cargar_config

    print(f"\n{'='*60}")
    print(f"  PUBLICAR PRODUCTO EN TIENDANUBE {'[DRY RUN]' if dry_run else '[REAL]'}")
    print(f"  CSR: {codigo_sinonimo}")
    print(f"{'='*60}\n")

    # --- 1. Buscar artículo en ERP ---
    print("[1/5] Buscando artículo en ERP (111)...")
    articulo = _consultar_articulo_erp(codigo_sinonimo)
    if not articulo:
        print(f"  ERROR: No se encontró artículo con codigo_sinonimo = '{codigo_sinonimo}'")
        return {'ok': False, 'error': f'Artículo no encontrado: {codigo_sinonimo}'}

    print(f"  Código ERP:  {articulo['codigo']}")
    print(f"  Descripción: {articulo['descripcion']}")
    print(f"  Marca:       {articulo['marca_nombre']} ({articulo['marca']})")
    print(f"  Costo:       ${articulo['precio_costo']:,.0f}")
    print(f"  PV ERP:      ${articulo['precio_venta']:,.0f}")
    print(f"  Stock:       {articulo['stock']}")
    print(f"  Estado:      {articulo['estado']}")
    print(f"  Moneda:      {'USD' if articulo['moneda'] == 1 else 'ARS'}")
    print()

    # --- 2. Buscar variantes (talles) ---
    print("[2/5] Buscando variantes (talles) del modelo...")
    variantes = _buscar_variantes_por_modelo(codigo_sinonimo)
    print(f"  {len(variantes)} variantes encontradas:")
    for v in variantes:
        estado_icon = 'OK' if v['stock'] > 0 else '--'
        print(f"    [{estado_icon}] {v['codigo_sinonimo']} | {v['descripcion'][:40]:40s} | "
              f"stock:{v['stock']:3d} | ${v['precio_costo']:,.0f}")
    print()

    # --- 3. Obtener imágenes ---
    print("[3/5] Buscando imágenes en PostgreSQL (VPS)...")
    try:
        imagenes_tn = imagenes_para_tn(codigo_sinonimo)
        urls = urls_producto(codigo_sinonimo)
        print(f"  {len(imagenes_tn)} imágenes encontradas:")
        for u in urls:
            print(f"    {u}")
    except Exception as e:
        imagenes_tn = []
        urls = []
        print(f"  WARN: No se pudo conectar a PostgreSQL: {e}")
        print(f"  (el producto se puede publicar sin imágenes y agregarlas después)")
    print()

    # --- 4. Calcular precio ---
    print("[4/5] Calculando precio para canal TiendaNube...")
    reglas_file = os.path.join(os.path.dirname(__file__), 'reglas_canales.json')
    reglas = cargar_reglas(reglas_file)
    regla_tn = reglas.get('tiendanube', REGLAS_DEFAULT.get('tiendanube'))

    costo = articulo['precio_costo']
    if articulo['moneda'] == 1:
        cotiz_usd = 1170.0  # TODO: parametrizar
        costo = costo * cotiz_usd
        print(f"  Artículo en USD — costo convertido: ${costo:,.0f} (cotiz ${cotiz_usd:,.0f})")

    precio_calc = calcular_precio_canal(costo, regla_tn)
    if 'error' in precio_calc:
        print(f"  ERROR calculando precio: {precio_calc['error']}")
        return {'ok': False, 'error': precio_calc['error']}

    precio_tn = precio_calc['precio_venta']
    print(f"  Costo:         ${costo:,.0f}")
    print(f"  Precio TN:     ${precio_tn:,.0f}")
    print(f"  Margen real:   {precio_calc['margen_real']}%")
    print(f"  Comisión tot:  {precio_calc['comision_total_pct']}%")
    print(f"  Ganancia neta: ${precio_calc['ganancia_neta']:,.0f}")
    print()

    # --- 5. Armar payload TN ---
    print("[5/5] Armando payload TiendaNube...")

    # Nombre del producto (sin talle, usar descripción del modelo)
    nombre_producto = articulo['descripcion']
    # Limpiar talle del nombre si está incluido
    for suffix in [' T' + codigo_sinonimo[-2:], ' ' + codigo_sinonimo[-2:]]:
        if nombre_producto.endswith(suffix):
            nombre_producto = nombre_producto[:-len(suffix)]

    # Armar variantes TN (una por talle)
    variantes_tn = []
    stock_total = 0
    for v in variantes:
        stock_var = max(v['stock'], 0)
        stock_total += stock_var
        variante_tn = {
            'price': str(precio_tn),
            'stock': stock_var,
            'sku': v['codigo_sinonimo'],
        }
        # Si hay talle, agregarlo como atributo de variante
        if v['talle_code']:
            variante_tn['values'] = [{'es': f"Talle {v['talle_code']}"}]
        variantes_tn.append(variante_tn)

    payload = {
        'name': {'es': nombre_producto},
        'published': True,
        'variants': variantes_tn,
    }

    if imagenes_tn:
        payload['images'] = imagenes_tn

    # Diagnóstico de campos
    campos_faltantes = []
    if not imagenes_tn:
        campos_faltantes.append('images (sin fotos en PostgreSQL)')
    if stock_total <= 0:
        campos_faltantes.append('stock (todas las variantes en 0)')
    if not nombre_producto:
        campos_faltantes.append('name (descripción vacía en ERP)')

    print(f"\n  PAYLOAD TIENDANUBE:")
    print(f"  {json.dumps(payload, indent=2, ensure_ascii=False)}")

    if campos_faltantes:
        print(f"\n  CAMPOS FALTANTES O PROBLEMÁTICOS:")
        for c in campos_faltantes:
            print(f"    - {c}")

    resultado = {
        'ok': True,
        'dry_run': dry_run,
        'articulo_erp': articulo,
        'variantes': len(variantes_tn),
        'stock_total': stock_total,
        'precio_tn': precio_tn,
        'imagenes': len(imagenes_tn),
        'campos_faltantes': campos_faltantes,
        'payload': payload,
    }

    if not dry_run:
        # Publicar en TN
        config = cargar_config()
        if not config.get('store_id') or not config.get('access_token'):
            print("\n  ERROR: No hay config de TiendaNube.")
            resultado['ok'] = False
            resultado['error'] = 'Sin config TiendaNube'
            return resultado

        client = TiendaNubeClient(
            store_id=config['store_id'],
            access_token=config['access_token'],
        )
        try:
            resp = client.crear_producto(
                nombre=nombre_producto,
                variantes=variantes_tn,
                images=imagenes_tn if imagenes_tn else None,
            )
            resultado['respuesta_tn'] = resp
            resultado['product_id'] = resp.get('id')
            print(f"\n  PUBLICADO OK — product_id: {resp.get('id')}")
            print(f"  URL: {resp.get('canonical_url', 'N/A')}")
        except Exception as e:
            resultado['ok'] = False
            resultado['error'] = str(e)
            print(f"\n  ERROR publicando: {e}")
    else:
        print(f"\n  [DRY RUN] No se publicó. Quitar dry_run=True para publicar.")

    print(f"\n{'='*60}\n")
    return resultado
