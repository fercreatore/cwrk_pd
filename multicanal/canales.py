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
"""
import json
import logging
import requests

logger = logging.getLogger('multicanal.canales')


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
        else:
            url = self._url('products/%s' % id_externo)
        r = requests.put(url, json={'variants': [{'price': precio}]}, headers=self.headers)
        return {'ok': r.status_code == 200, 'detalle': r.text}

    def actualizar_stock(self, id_externo, stock, variante_id=None):
        if variante_id:
            url = self._url('products/%s/variants/%s' % (id_externo, variante_id))
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

    def obtener_producto(self, id_externo):
        r = requests.get('https://api.mercadolibre.com/items/%s' % id_externo, headers=self._headers())
        if r.status_code == 200:
            return {'ok': True, 'producto': r.json()}
        return {'ok': False, 'error': r.text}
