"""
Cliente API Tienda Nube — Independiente, sin dependencias externas más allá de requests.

Docs API: https://tiendanube.github.io/api-documentation/
Auth: Bearer token (access_token de app instalada)
Base URL: https://api.tiendanube.com/v1/{store_id}/

USO:
    from multicanal.tiendanube import TiendaNubeClient
    tn = TiendaNubeClient(store_id='12345', access_token='abc...')
    productos = tn.listar_productos(limit=50)
    ordenes = tn.listar_ordenes(status='paid')
"""

import json
import os
import time
import requests
from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Config persistente ──
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'tiendanube_config.json')


def guardar_config(store_id: str, access_token: str):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'store_id': store_id, 'access_token': access_token}, f)


def cargar_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


@dataclass
class TiendaNubeClient:
    store_id: str
    access_token: str
    base_url: str = ''
    user_agent: str = 'Calzalindo Multicanal/1.0'
    _session: requests.Session = field(default_factory=requests.Session, repr=False)

    def __post_init__(self):
        self.base_url = f'https://api.tiendanube.com/v1/{self.store_id}'
        self._session.headers.update({
            'Authentication': f'bearer {self.access_token}',
            'User-Agent': self.user_agent,
            'Content-Type': 'application/json',
        })

    def _handle_rate_limit(self, r):
        """Si la respuesta es 429, espera el tiempo indicado por Retry-After."""
        if r.status_code == 429:
            retry = int(r.headers.get('Retry-After', 5))
            time.sleep(retry)
            return True
        return False

    def _get(self, endpoint: str, params: dict = None) -> dict | list:
        url = f'{self.base_url}/{endpoint}'
        r = self._session.get(url, params=params, timeout=30)
        if self._handle_rate_limit(r):
            r = self._session.get(url, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, endpoint: str, data: dict) -> dict:
        url = f'{self.base_url}/{endpoint}'
        r = self._session.post(url, json=data, timeout=30)
        if self._handle_rate_limit(r):
            r = self._session.post(url, json=data, timeout=30)
        r.raise_for_status()
        return r.json()

    def _put(self, endpoint: str, data: dict) -> dict:
        url = f'{self.base_url}/{endpoint}'
        r = self._session.put(url, json=data, timeout=30)
        if self._handle_rate_limit(r):
            r = self._session.put(url, json=data, timeout=30)
        r.raise_for_status()
        return r.json()

    # ── Tienda info ──
    def info_tienda(self) -> dict:
        return self._get('store')

    # ── Productos ──
    def listar_productos(self, page: int = 1, per_page: int = 50,
                         since_id: int = None, created_at_min: str = None) -> list:
        params = {'page': page, 'per_page': per_page}
        if since_id:
            params['since_id'] = since_id
        if created_at_min:
            params['created_at_min'] = created_at_min
        return self._get('products', params)

    def obtener_producto(self, product_id: int) -> dict:
        return self._get(f'products/{product_id}')

    def crear_producto(self, nombre: str, variantes: list, **kwargs) -> dict:
        """
        Crea producto en TN.
        variantes: [{'price': '90000', 'stock': 10, 'sku': 'ABC123', 'values': [{'es': 'Negro'}, {'es': '42'}]}]
        kwargs: description, handle, categories, images, etc.
        """
        data = {
            'name': {'es': nombre},
            'variants': variantes,
        }
        if 'descripcion' in kwargs:
            data['description'] = {'es': kwargs.pop('descripcion')}
        data.update(kwargs)
        return self._post('products', data)

    def actualizar_producto(self, product_id: int, data: dict) -> dict:
        return self._put(f'products/{product_id}', data)

    def actualizar_variante(self, product_id: int, variant_id: int,
                            precio: float = None, stock: int = None) -> dict:
        data = {}
        if precio is not None:
            data['price'] = str(precio)
        if stock is not None:
            data['stock'] = stock
        return self._put(f'products/{product_id}/variants/{variant_id}', data)

    # ── Órdenes ──
    def listar_ordenes(self, page: int = 1, per_page: int = 50,
                       status: str = None, payment_status: str = None,
                       created_at_min: str = None, created_at_max: str = None) -> list:
        params = {'page': page, 'per_page': per_page}
        if status:
            params['status'] = status
        if payment_status:
            params['payment_status'] = payment_status
        if created_at_min:
            params['created_at_min'] = created_at_min
        if created_at_max:
            params['created_at_max'] = created_at_max
        return self._get('orders', params)

    def obtener_orden(self, order_id: int) -> dict:
        return self._get(f'orders/{order_id}')

    def listar_todas_ordenes(self, status: str = None, payment_status: str = None,
                              created_at_min: str = None, max_pages: int = 20) -> list:
        """Pagina automáticamente hasta traer todas las órdenes."""
        todas = []
        for page in range(1, max_pages + 1):
            lote = self.listar_ordenes(
                page=page, per_page=50, status=status,
                payment_status=payment_status, created_at_min=created_at_min
            )
            if not lote:
                break
            todas.extend(lote)
            if len(lote) < 50:
                break
        return todas

    # ── Categorías ──
    def listar_categorias(self) -> list:
        return self._get('categories')

    # ── Webhooks ──
    def listar_webhooks(self) -> list:
        return self._get('webhooks')

    def crear_webhook(self, event: str, url: str) -> dict:
        """
        Events: order/created, order/paid, order/fulfilled,
                product/created, product/updated, product/deleted
        """
        return self._post('webhooks', {'event': event, 'url': url})

    # ── Helpers para vincular con ERP ──
    def mapear_sku_a_erp(self, ordenes: list) -> list:
        """
        Extrae SKU de cada línea de orden para vincular con articulo.codigo_sinonimo del ERP.
        Retorna lista de dicts: [{order_id, sku, quantity, price, variant_id, product_id}]
        """
        lineas = []
        for orden in ordenes:
            for item in orden.get('products', []):
                lineas.append({
                    'order_id': orden['id'],
                    'order_number': orden.get('number'),
                    'fecha': orden.get('created_at', '')[:10],
                    'estado_pago': orden.get('payment_status'),
                    'sku': item.get('sku', ''),
                    'nombre': item.get('name', ''),
                    'cantidad': item.get('quantity', 0),
                    'precio': float(item.get('price', 0)),
                    'variant_id': item.get('variant_id'),
                    'product_id': item.get('product_id'),
                })
        return lineas
