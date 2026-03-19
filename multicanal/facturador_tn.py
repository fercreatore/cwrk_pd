"""
Facturador TiendaNube → ERP MS Gestión.

Procesa órdenes pagadas de TiendaNube e inserta factura B (ventas2 cabecera +
ventas1 detalle) en el ERP para registrar la venta y descontar stock.

Soporta múltiples tiendas/empresas:
  - H4       → INSERT en msgestion03  (default)
  - ABI      → INSERT en msgestion01  (CALZALINDO)

Lectura de artículos siempre desde msgestion01art (compartida).

USO:
    # Dry run (solo muestra qué se insertaría)
    python -m multicanal.facturador_tn --dry-run

    # Facturar para ABI/CALZALINDO
    python -m multicanal.facturador_tn --dry-run --empresa ABI

    # Tienda específica
    python -m multicanal.facturador_tn --dry-run --tienda otra_tienda

    # Desde código
    from multicanal.facturador_tn import sincronizar_ordenes_tn
    reporte = sincronizar_ordenes_tn(dry_run=True, dias_atras=7, empresa='ABI')
"""

import json
import os
import sys
import pyodbc
import requests
from datetime import datetime, timedelta

# Agregar raíz al path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multicanal.tiendanube import TiendaNubeClient, cargar_config


# ── Routing empresa → base de datos ──

BASES_POR_EMPRESA = {
    'H4':         'msgestion03',
    'ABI':        'msgestion01',
    'CALZALINDO': 'msgestion01',
}

def _base_para_empresa(empresa: str) -> str:
    """Retorna la base de datos destino según la empresa."""
    empresa_upper = empresa.upper()
    base = BASES_POR_EMPRESA.get(empresa_upper)
    if not base:
        raise ValueError(f"Empresa '{empresa}' no configurada. Opciones: {list(BASES_POR_EMPRESA.keys())}")
    return base


def _conn_string(base: str) -> str:
    """Connection string para una base de datos dada."""
    return (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=192.168.2.111;"
        f"DATABASE={base};"
        "UID=am;PWD=dl;"
        "Encrypt=no;"
    )

CONN_STRING_ART = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.112;"
    "DATABASE=msgestion01art;"
    "UID=am;PWD=dl;"
    "Encrypt=no;"
)


# ── Parámetros fijos factura B ──

CODIGO = 1          # factura
LETRA = 'B'         # consumidor final
SUCURSAL = 1
DEPOSITO = 0        # central, para TN
ESTADO = 'V'
CONDICION_IVA = 'C'  # consumidor final
USUARIO = 'COWORK-TN'

LOG_FILE = os.path.join(os.path.dirname(__file__), 'ordenes_procesadas.json')

# ── Config POS 109 ──
# Endpoint del sistema del 109 para registrar ventas
POS_109_URL = 'https://192.168.2.109/clz_ventas/api/tiendanube_gen_remito'
POS_109_USUARIO = {'id': 2, 'sucursal': 1}   # Dep. VENTAS ML 1
POS_109_MEDIO_PAGO = {'id': 137}              # MERCADOLIBRE ONLINE API

# ── Multi-tienda TN ──
# Archivo principal = tiendanube_config.json (default)
# Tiendas adicionales = tiendanube_config_{nombre}.json

def cargar_config_tienda(nombre_tienda: str = None) -> dict:
    """Carga config de una tienda TN. None = default."""
    if nombre_tienda:
        config_file = os.path.join(os.path.dirname(__file__),
                                    f'tiendanube_config_{nombre_tienda}.json')
    else:
        config_file = os.path.join(os.path.dirname(__file__), 'tiendanube_config.json')
    if os.path.exists(config_file):
        with open(config_file) as f:
            return json.load(f)
    return {}


def guardar_config_tienda(store_id: str, access_token: str, nombre_tienda: str = None,
                           empresa: str = 'H4'):
    """Guarda config de una tienda TN."""
    if nombre_tienda:
        config_file = os.path.join(os.path.dirname(__file__),
                                    f'tiendanube_config_{nombre_tienda}.json')
    else:
        config_file = os.path.join(os.path.dirname(__file__), 'tiendanube_config.json')
    with open(config_file, 'w') as f:
        json.dump({
            'store_id': store_id,
            'access_token': access_token,
            'empresa': empresa,
            'nombre': nombre_tienda or 'default',
        }, f, indent=2)


# ── Persistencia de órdenes procesadas (SQLite) ──

SQLITE_DB = os.path.join(os.path.dirname(__file__), 'ordenes_procesadas.db')

def _init_sqlite():
    """Crea la tabla si no existe."""
    import sqlite3
    conn = sqlite3.connect(SQLITE_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ordenes (
            order_id TEXT PRIMARY KEY,
            order_number INTEGER,
            tienda TEXT DEFAULT 'default',
            fecha_orden TEXT,
            cliente TEXT,
            total REAL,
            renglones INTEGER,
            payload TEXT,
            respuesta_109 TEXT,
            fecha_proceso TEXT,
            estado TEXT DEFAULT 'OK'
        )
    """)
    conn.commit()
    return conn


def orden_ya_procesada(order_id: str, tienda: str = 'default') -> bool:
    """Verifica si una orden ya fue enviada al 109. CRITICO: evita duplicados."""
    import sqlite3
    conn = sqlite3.connect(SQLITE_DB)
    _init_sqlite_if_needed(conn)
    cursor = conn.execute(
        "SELECT 1 FROM ordenes WHERE order_id = ? AND tienda = ?",
        (str(order_id), tienda)
    )
    existe = cursor.fetchone() is not None
    conn.close()
    return existe


def registrar_orden_procesada(order_id, order_number, tienda, fecha_orden,
                               cliente, total, renglones, payload, respuesta_109):
    """Registra una orden como procesada en SQLite."""
    import sqlite3
    conn = sqlite3.connect(SQLITE_DB)
    _init_sqlite_if_needed(conn)
    conn.execute("""
        INSERT OR REPLACE INTO ordenes
        (order_id, order_number, tienda, fecha_orden, cliente, total,
         renglones, payload, respuesta_109, fecha_proceso, estado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(order_id), int(order_number), tienda, fecha_orden,
        cliente, float(total), int(renglones),
        json.dumps(payload, ensure_ascii=False, default=str),
        json.dumps(respuesta_109, ensure_ascii=False, default=str),
        datetime.now().isoformat(),
        'OK',
    ))
    conn.commit()
    conn.close()


def listar_ordenes_procesadas(tienda: str = 'default', limit: int = 50) -> list:
    """Lista las últimas órdenes procesadas."""
    import sqlite3
    conn = sqlite3.connect(SQLITE_DB)
    _init_sqlite_if_needed(conn)
    cursor = conn.execute("""
        SELECT order_id, order_number, fecha_orden, cliente, total, estado, fecha_proceso
        FROM ordenes WHERE tienda = ?
        ORDER BY fecha_proceso DESC LIMIT ?
    """, (tienda, limit))
    rows = [dict(zip(['order_id', 'order_number', 'fecha_orden', 'cliente',
                       'total', 'estado', 'fecha_proceso'], r)) for r in cursor.fetchall()]
    conn.close()
    return rows


def _init_sqlite_if_needed(conn):
    """Crea tabla si no existe (idempotente)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ordenes (
            order_id TEXT PRIMARY KEY,
            order_number INTEGER,
            tienda TEXT DEFAULT 'default',
            fecha_orden TEXT,
            cliente TEXT,
            total REAL,
            renglones INTEGER,
            payload TEXT,
            respuesta_109 TEXT,
            fecha_proceso TEXT,
            estado TEXT DEFAULT 'OK'
        )
    """)


# ── Conexión ERP ──

def conectar_erp(empresa: str = 'H4'):
    """Abre conexión pyodbc al SQL Server — base según empresa."""
    base = _base_para_empresa(empresa)
    return pyodbc.connect(_conn_string(base), timeout=15)


def conectar_erp_art():
    """Abre conexión pyodbc al SQL Server — base artículos (compartida)."""
    return pyodbc.connect(CONN_STRING_ART, timeout=15)


# ── Consultas ERP ──

def buscar_articulos_por_sku(conn_art, skus: list) -> dict:
    """
    Dado un listado de SKUs, busca en articulo por codigo_sinonimo.
    Si no encuentra, busca por codigo_barra como fallback.
    Retorna dict {sku_original: {codigo, descripcion, precio_costo, codigo_sinonimo}}.
    """
    if not skus:
        return {}

    resultado = {}
    BATCH = 500
    for i in range(0, len(skus), BATCH):
        lote = skus[i:i + BATCH]
        placeholders = ",".join(["?"] * len(lote))

        # Buscar por codigo_sinonimo primero
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

        # Fallback: buscar los que no se encontraron por codigo_barra
        no_encontrados = [s for s in lote if s not in resultado]
        if no_encontrados:
            placeholders2 = ",".join(["?"] * len(no_encontrados))
            query2 = f"""
                SELECT
                    codigo,
                    descripcion_1,
                    precio_costo,
                    codigo_sinonimo,
                    codigo_barra
                FROM msgestion01art.dbo.articulo
                WHERE codigo_barra IN ({placeholders2})
            """
            cursor.execute(query2, no_encontrados)
            for row in cursor.fetchall():
                barra = str(row[4]).strip() if row[4] else ''
                sinonimo = row[3].strip() if row[3] else ''
                if barra and barra not in resultado:
                    resultado[barra] = {
                        'codigo': int(row[0]),
                        'descripcion': (row[1] or '').strip(),
                        'precio_costo': float(row[2] or 0),
                        'codigo_sinonimo': sinonimo or barra,
                    }

    return resultado


def obtener_siguiente_numero(conn, base: str) -> int:
    """Obtiene el siguiente número de factura (MAX+1)."""
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT ISNULL(MAX(numero), 0) + 1
        FROM {base}.dbo.ventas2
        WHERE codigo = ?
          AND letra = ?
          AND sucursal = ?
    """, CODIGO, LETRA, SUCURSAL)
    row = cursor.fetchone()
    return int(row[0])


def obtener_siguiente_orden(conn, base: str, fecha_comprobante: str) -> int:
    """Obtiene la siguiente orden para la fecha dada (MAX+1 del día)."""
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT ISNULL(MAX(orden), 0) + 1
        FROM {base}.dbo.ventas2
        WHERE codigo = ?
          AND letra = ?
          AND sucursal = ?
          AND CONVERT(date, fecha_comprobante) = CONVERT(date, ?)
    """, CODIGO, LETRA, SUCURSAL, fecha_comprobante)
    row = cursor.fetchone()
    return int(row[0])


# ── Alta de cliente ──

def alta_cliente_tn(conn, orden: dict, base: str = 'msgestion03') -> int:
    """
    Crea un cliente en la tabla clientes a partir de datos de orden TN.
    Si ya existe (por DNI o denominacion), retorna su numero.
    Retorna el numero de cliente creado/existente.

    NO vincula a ventas2.cuenta (queda NULL, como hace el POS).
    """
    cursor = conn.cursor()

    customer = orden.get('customer', {})
    nombre = (customer.get('name') or '').strip()
    email = (customer.get('email') or '').strip()
    telefono = (customer.get('phone') or '').strip()
    dni_str = (customer.get('identification') or '').strip().lstrip('0')

    # Armar denominacion formato APELLIDO, NOMBRE
    partes = nombre.split(' ', 1)
    if len(partes) == 2:
        denominacion = f"{partes[1].upper()}, {partes[0].upper()}"
        nombres = partes[0]
        apellidos = partes[1]
    else:
        denominacion = nombre.upper()
        nombres = nombre
        apellidos = ''

    # Dirección de facturación
    billing_addr = orden.get('billing_address') or ''
    billing_num = orden.get('billing_number') or ''
    billing_loc = orden.get('billing_locality') or ''
    billing_city = orden.get('billing_city') or ''
    if isinstance(billing_addr, dict):
        # Formato viejo de API
        billing_addr = billing_addr.get('address', '')
    direccion_parts = [p for p in [billing_addr, billing_num, billing_loc, billing_city] if p]
    direccion = ', '.join(direccion_parts)[:80]

    cp_str = orden.get('billing_zipcode') or '0'
    try:
        codigo_postal = int(cp_str)
    except (ValueError, TypeError):
        codigo_postal = 0

    # DNI numérico
    try:
        dni_num = int(dni_str) if dni_str else 0
    except (ValueError, TypeError):
        dni_num = 0

    # Verificar si ya existe por DNI o denominacion
    if dni_num > 0:
        cursor.execute(f"""
            SELECT numero, denominacion FROM {base}.dbo.clientes
            WHERE nume_documento = ?
        """, dni_num)
    else:
        cursor.execute(f"""
            SELECT numero, denominacion FROM {base}.dbo.clientes
            WHERE denominacion = ?
        """, denominacion)

    existente = cursor.fetchone()
    if existente:
        return int(existente[0])

    # Obtener siguiente numero
    cursor.execute(f"SELECT ISNULL(MAX(numero), 0) + 1 FROM {base}.dbo.clientes")
    nuevo_numero = cursor.fetchone()[0]

    # TN order info para observaciones_facturacion
    tn_id = customer.get('id', '')
    tn_order = orden.get('number', '')
    obs_fact = f"TN-ID:{tn_id}, TN-ORDER:{tn_order}"

    cursor.execute(f"""
        INSERT INTO {base}.dbo.clientes (
            numero, denominacion, direccion, codigo_postal,
            telefonos, condicion_iva, cuit,
            tipo_documento, nume_documento,
            tipo_comercio, usuario, observaciones,
            fecha_ingreso, e_mail,
            apellidos, nombres,
            observaciones_facturacion
        ) VALUES (
            ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            GETDATE(), ?,
            ?, ?,
            ?
        )
    """,
        nuevo_numero,
        denominacion[:80],
        direccion,
        codigo_postal,
        telefono[:30] if telefono else None,
        'C',            # consumidor final
        '',             # sin CUIT
        96,             # tipo_documento = DNI
        dni_num,
        2,              # tipo_comercio (como POS-API-ML)
        'COWORK-TN',
        'TIENDANUBE-COWORK',
        email[:50] if email else None,
        apellidos[:30],
        nombres[:30],
        obs_fact[:50],
    )

    return int(nuevo_numero)


# ── Registro en POS 109 ──

def construir_payload_109(orden: dict, articulos_erp: dict) -> dict:
    """
    Arma el JSON que espera el sistema del 109 para registrar una venta.
    """
    customer = orden.get('customer', {})
    nombre_raw = (customer.get('name') or '').strip()
    partes = nombre_raw.split(' ', 1)
    nombre = partes[0] if partes else ''
    apellido = partes[1] if len(partes) > 1 else ''

    dni_str = (customer.get('identification') or '').strip()
    email = (customer.get('email') or '').strip()
    tn_id = str(customer.get('id', ''))

    # Dirección
    billing_addr = orden.get('billing_address') or ''
    billing_num = orden.get('billing_number') or ''
    billing_loc = orden.get('billing_locality') or ''
    billing_city = orden.get('billing_city') or ''
    if isinstance(billing_addr, dict):
        billing_addr = billing_addr.get('address', '')
    direccion_parts = [p for p in [billing_addr, billing_num, billing_loc, billing_city] if p]
    direccion = ', '.join(direccion_parts)

    cod_postal = orden.get('billing_zipcode') or '0'

    # Productos
    productos = []
    for item in orden.get('products', []):
        sku = (item.get('sku') or '').strip()
        if not sku:
            continue
        art = articulos_erp.get(sku)
        if not art:
            continue
        productos.append({
            'sku': sku,
            'cantidad': int(item.get('quantity', 0)),
            'precio': float(item.get('price', 0)),
        })

    payload = {
        'pack_id': str(orden.get('id', '')),
        'nro_doc': dni_str,
        'tipo_doc': 96,
        'tipo_doc_descrip': 'DNI',
        'condicion_iva': 'C',
        'nombre': nombre,
        'apellido': apellido,
        'usuario_ml': tn_id,
        'usuario_ml_nick': email,
        'direccion': direccion,
        'cod_postal': str(cod_postal),
        'tenant': 'tiendanube',
        'mi_usuario': POS_109_USUARIO,
        'mi_medio_pago': POS_109_MEDIO_PAGO,
        'productos': productos,
    }

    return payload


def enviar_venta_109(orden: dict, articulos_erp: dict) -> dict:
    """
    Envía la venta al POS del 109 de forma SÍNCRONA.
    Espera la respuesta completa antes de retornar.
    Retorna la respuesta o None si no está configurado.
    """
    if not POS_109_URL:
        return None

    payload = construir_payload_109(orden, articulos_erp)

    if not payload['productos']:
        return {'error': 'Sin productos válidos para 109'}

    try:
        # POST síncrono — espera respuesta completa antes de continuar
        resp = requests.post(POS_109_URL, json=payload, timeout=60, verify=False)
        resp.raise_for_status()
        if resp.headers.get('content-type', '').startswith('application/json'):
            result = resp.json()
        else:
            result = {'status': resp.status_code, 'text': resp.text[:500]}
        return result
    except requests.Timeout:
        return {'error': f'Timeout (60s) al conectar con {POS_109_URL}'}
    except requests.ConnectionError as e:
        return {'error': f'No se pudo conectar al 109: {e}'}
    except requests.HTTPError as e:
        body = ''
        try:
            body = e.response.text[:500]
        except Exception:
            pass
        return {'error': f'HTTP {e.response.status_code}: {body}'}
    except requests.RequestException as e:
        return {'error': str(e)}


# ── Log de errores (SQLite) ──

def registrar_error(order_id, order_number, tienda, error_msg, payload=None):
    """Registra un error en SQLite para auditoría."""
    import sqlite3
    conn = sqlite3.connect(SQLITE_DB)
    _init_sqlite_if_needed(conn)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS errores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            order_number INTEGER,
            tienda TEXT,
            error TEXT,
            payload TEXT,
            fecha TEXT
        )
    """)
    conn.execute("""
        INSERT INTO errores (order_id, order_number, tienda, error, payload, fecha)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        str(order_id), int(order_number), tienda,
        error_msg,
        json.dumps(payload, ensure_ascii=False, default=str) if payload else None,
        datetime.now().isoformat(),
    ))
    conn.commit()
    conn.close()


def listar_errores(tienda: str = 'default', limit: int = 50) -> list:
    """Lista los últimos errores registrados."""
    import sqlite3
    conn = sqlite3.connect(SQLITE_DB)
    try:
        cursor = conn.execute("""
            SELECT order_id, order_number, error, fecha
            FROM errores WHERE tienda = ?
            ORDER BY fecha DESC LIMIT ?
        """, (tienda, limit))
        rows = [dict(zip(['order_id', 'order_number', 'error', 'fecha'], r))
                for r in cursor.fetchall()]
    except sqlite3.OperationalError:
        rows = []  # tabla no existe todavía
    conn.close()
    return rows


# ── Inserción ERP ──

def insertar_factura(conn, cabecera: dict, detalles: list, base: str = 'msgestion03',
                     orden_tn: dict = None):
    """
    Inserta ventas2 (cabecera) + ventas1 (detalles) dentro de una transacción.
    Si algo falla, hace rollback completo.

    base: 'msgestion03' (H4) o 'msgestion01' (ABI/CALZALINDO)
    """
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        # --- Alta de cliente TN ---
        if orden_tn:
            alta_cliente_tn(conn, orden_tn, base)

        # --- INSERT ventas2 (cabecera) ---
        cursor.execute(f"""
            INSERT INTO {base}.dbo.ventas2 (
                codigo, letra, sucursal, numero, orden,
                deposito, cuenta, denominacion, cuenta_cc,
                fecha_comprobante, fecha_proceso, fecha_contable,
                fecha_hora, talonario, libro_iva, contabiliza,
                monto_general, importe_neto_ge,
                estado, estado_stock, estado_cc,
                estado_pedidos, condicion_iva, usuario, moneda,
                descuento_general, monto_descuento,
                bonificacion_general, monto_bonificacion,
                iva1, monto_iva1, percepcion,
                zona, provincia, numero_cuit, copias,
                viajante, entregador, calificacion
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
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
            cabecera['fecha_proceso'],  # fecha_hora = mismo que fecha_proceso
            1,                          # talonario = 1 (como POS)
            'N',                        # libro_iva = 'N'
            'N',                        # contabiliza = 'N'
            cabecera['monto_general'],
            cabecera['monto_general'],  # importe_neto_ge = monto total (B sin IVA discriminado)
            cabecera['estado'],
            cabecera['estado_stock'],
            cabecera['estado_cc'],
            cabecera['estado_pedidos'],
            cabecera['condicion_iva'],
            cabecera['usuario'],
            cabecera['moneda'],
            0, 0,  # descuento_general, monto_descuento
            0, 0,  # bonificacion_general, monto_bonificacion
            21, None,  # iva1=21%, monto_iva1=NULL (factura B, IVA incluido)
            0,      # percepcion
            1,      # zona = 1 (como POS)
            'S',    # provincia = 'S' (Santa Fe)
            '00000000000',  # numero_cuit (como POS)
            1,      # copias = 1
            585,    # viajante = 585 (como POS)
            0,      # entregador = 0
            '',     # calificacion = ''
        )

        # --- INSERT ventas1 (detalles) ---
        # NO tiene columna 'empresa'
        for det in detalles:
            cursor.execute(f"""
                INSERT INTO {base}.dbo.ventas1 (
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
            cursor.execute(f"""
                UPDATE {base}.dbo.stock
                SET stock_actual = stock_actual - ?
                WHERE articulo = ? AND deposito = ?
            """, det['cantidad'], det['articulo'], det['deposito'])

        # Marcar estado_stock='V' para evitar doble descuento por batch ERP
        cursor.execute(f"""
            UPDATE {base}.dbo.ventas2
            SET estado_stock = 'V'
            WHERE codigo = ? AND letra = ? AND sucursal = ? AND numero = ? AND orden = ?
        """, cabecera['codigo'], cabecera['letra'], cabecera['sucursal'],
            cabecera['numero'], cabecera['orden'])

        cursor.execute(f"""
            UPDATE {base}.dbo.ventas1
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

    # Nombre del cliente — formato APELLIDO, NOMBRE en mayúsculas (como POS)
    customer = orden.get('customer', {})
    nombre_raw = (customer.get('name') or '').strip()
    if nombre_raw:
        partes = nombre_raw.split(' ', 1)
        if len(partes) == 2:
            nombre_cliente = f"{partes[1].upper()}, {partes[0].upper()}"
        else:
            nombre_cliente = nombre_raw.upper()
    else:
        nombre_cliente = f"TIENDANUBE #{orden.get('number', orden['id'])}"

    # Monto total
    monto_general = float(orden.get('total', 0))

    cabecera = {
        'codigo': CODIGO,
        'letra': LETRA,
        'sucursal': SUCURSAL,
        'numero': numero,
        'orden': orden_dia,
        'deposito': DEPOSITO,
        'cuenta': None,
        'denominacion': nombre_cliente[:100],
        'cuenta_cc': 1,
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

def sincronizar_ordenes_tn(dry_run: bool = True, dias_atras: int = 7,
                           empresa: str = 'H4', nombre_tienda: str = None) -> dict:
    """
    Procesa órdenes pagadas de TiendaNube e inserta facturas B en el ERP.

    Args:
        dry_run: Si True, solo muestra qué se insertaría sin tocar el ERP.
        dias_atras: Cantidad de días hacia atrás para buscar órdenes.
        empresa: 'H4' (msgestion03) o 'ABI' (msgestion01/CALZALINDO).
        nombre_tienda: Nombre de config TN alternativa (None = default).

    Returns:
        dict con resumen de procesamiento.
    """
    base = _base_para_empresa(empresa)
    modo = "DRY RUN" if dry_run else "FACTURACION REAL"
    print(f"\n{'='*60}")
    print(f"  FACTURADOR TiendaNube → ERP [{modo}]")
    print(f"  Empresa: {empresa} → {base}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Buscando órdenes de los últimos {dias_atras} días")
    print(f"{'='*60}\n")

    # --- Inicializar cliente TN ---
    config = cargar_config_tienda(nombre_tienda)
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

    # --- 2. Filtrar ya procesadas (SQLite) ---
    print("[2/5] Filtrando órdenes ya procesadas...")
    tienda = nombre_tienda or 'default'
    ordenes_nuevas = [o for o in ordenes if not orden_ya_procesada(str(o['id']), tienda)]
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
    print(f"[4/5] {'Simulando' if dry_run else 'Enviando al POS 109'}...")

    procesadas = []
    errores = []

    try:
        for orden in ordenes_nuevas:
            order_id = orden['id']
            order_number = orden.get('number', order_id)
            fecha_orden = orden.get('created_at', '')[:10]

            # Armar payload para el 109
            payload = construir_payload_109(orden, articulos_erp)

            if not payload['productos']:
                # Buscar SKUs no encontrados
                skus_no_enc = []
                for item in orden.get('products', []):
                    sku = (item.get('sku') or '').strip()
                    if sku and sku not in articulos_erp:
                        skus_no_enc.append(sku)
                    elif not sku:
                        skus_no_enc.append(f"(sin SKU) {item.get('name', '?')}")
                msg = f"  [SKIP] Orden #{order_number} (TN {order_id}) — sin artículos válidos"
                if skus_no_enc:
                    msg += f" (SKUs no encontrados: {', '.join(skus_no_enc[:5])})"
                print(msg)
                errores.append(f"Orden #{order_number}: sin artículos válidos en ERP")
                continue

            customer = orden.get('customer', {})
            nombre_raw = (customer.get('name') or '').strip()
            total = sum(p['precio'] * p['cantidad'] for p in payload['productos'])
            renglones = len(payload['productos'])

            if dry_run:
                print(f"  [DRY] Orden #{order_number} | {fecha_orden} | {nombre_raw[:25]:25s} | "
                      f"{renglones} items | ${total:,.0f}")
                procesadas.append({
                    'order_id': order_id,
                    'order_number': order_number,
                    'fecha': fecha_orden,
                    'cliente': nombre_raw,
                    'renglones': renglones,
                    'total': total,
                    'payload_109': payload,
                })
            else:
                try:
                    # Enviar al POS 109 — el 109 hace TODO (cliente, factura, stock)
                    resp_109 = enviar_venta_109(orden, articulos_erp)

                    if resp_109 and 'error' in resp_109:
                        raise Exception(f"POS 109: {resp_109['error']}")

                    print(f"  [OK]  Orden #{order_number} → POS 109 | "
                          f"{renglones} items | ${total:,.0f} | {nombre_raw[:25]}")

                    # Registrar como procesada en SQLite (anti-duplicados)
                    registrar_orden_procesada(
                        order_id=order_id,
                        order_number=order_number,
                        tienda=tienda,
                        fecha_orden=fecha_orden,
                        cliente=nombre_raw,
                        total=total,
                        renglones=renglones,
                        payload=payload,
                        respuesta_109=resp_109,
                    )

                    procesadas.append({
                        'order_id': order_id,
                        'order_number': order_number,
                        'fecha': fecha_orden,
                        'cliente': nombre_raw,
                        'renglones': renglones,
                        'total': total,
                    })
                except Exception as e:
                    error_msg = f"Orden #{order_number} (TN {order_id}): {e}"
                    print(f"  [ERR] {error_msg}")
                    errores.append(error_msg)
                    # Registrar error en SQLite para auditoría
                    registrar_error(
                        order_id=order_id,
                        order_number=order_number,
                        tienda=tienda,
                        error_msg=str(e),
                        payload=payload,
                    )

    except Exception as e:
        print(f"\n[ERROR GENERAL] {e}")
        errores.append(str(e))

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
    parser.add_argument('--empresa', type=str, default='H4',
                        help='Empresa destino: H4 (msgestion03) o ABI (msgestion01)')
    parser.add_argument('--tienda', type=str, default=None,
                        help='Nombre de config TN alternativa (default: tiendanube_config.json)')
    args = parser.parse_args()

    reporte = sincronizar_ordenes_tn(
        dry_run=args.dry_run, dias_atras=args.dias,
        empresa=args.empresa, nombre_tienda=args.tienda,
    )

    if reporte.get('error'):
        sys.exit(1)
    if reporte.get('errores'):
        sys.exit(2)
    sys.exit(0)
