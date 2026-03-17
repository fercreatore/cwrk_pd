# paso8_carga_factura.py
# Módulo core de carga de facturas para operadores.
#
# Flujo:
#   1. Operador ingresa datos de factura (proveedor, artículos, cantidades, precios)
#   2. Sistema busca artículos existentes por sinónimo/código de barra
#   3. Si no existen → los crea automáticamente (mismo mecanismo que paso2)
#   4. Crea nota de pedido o remito según corresponda
#   5. Asocia fotos si las hay
#
# Reglas de pricing:
#   - precio_fabrica = precio unitario de la factura
#   - descuento_1 = descuento comercial de la factura (negociado por vendedor)
#   - descuento = descuento estándar del proveedor (de config.py)
#   - precio_costo = precio_fabrica × (1 - descuento/100)
#   - precio_N = precio_costo × (1 + utilidad_N/100)
#
# EJECUTAR: python paso8_carga_factura.py (modo CLI)
#           O usar desde app_carga.py (interfaz Streamlit)

import os
import sys
import json
import logging
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
from typing import Optional

# ── Imports del proyecto ─────────────────────────────────────────
# Se importan dinámicamente para permitir testing sin pyodbc
def _importar_proyecto():
    """Importa módulos del proyecto. Retorna True si están disponibles."""
    try:
        import pyodbc
        from config import (CONN_COMPRAS, CONN_ARTICULOS, PROVEEDORES,
                            calcular_precios, BD_ARTICULOS, BD_COMPRAS, BD_BASE_H4)
        return True
    except ImportError as e:
        logging.warning(f"Módulos del proyecto no disponibles: {e}")
        return False


# ── Normalización de talles (3 capas) ──
# Se importa lazy para no fallar si las tablas no existen aún
_resolver_talle_ok = False
try:
    from resolver_talle import talle_para_sinonimo as _tps, talle_para_descripcion_5 as _tpd5
    _resolver_talle_ok = True
except ImportError:
    logging.info("resolver_talle no disponible — usando manejo de talles legacy")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("carga_factura")


# ══════════════════════════════════════════════════════════════════
# MODELOS DE DATOS
# ══════════════════════════════════════════════════════════════════

@dataclass
class LineaFactura:
    """Una línea/item de la factura."""
    modelo: str                    # ej: "WKC215"
    descripcion: str               # ej: "WKC215 V26 MOD.YOUTH NEGRO"
    color: str                     # ej: "NEGRO"
    talle: str                     # ej: "31" (un talle específico)
    cantidad: int                  # cantidad de pares
    precio_unitario: float         # precio por unidad en factura = precio_fabrica
    descuento_comercial: float = 0 # % descuento comercial del vendedor → descuento_1
    codigo_barra_fabricante: str = ""  # código de barra del fabricante
    codigo_producto: str = ""      # código del artículo según el proveedor (ej: "RBK-HP6003")
    descripcion_1: str = ""        # descripción completa para DB (ej: "FLEXAGON ENERGY TR 4 AZUL...")
    descripcion_3: str = ""        # descripción corta etiqueta (26 chars)
    subtotal: float = 0            # calculado
    # Campos que se completan durante el procesamiento
    codigo_articulo: int = 0       # código en msgestion01art.dbo.articulo
    codigo_sinonimo: str = ""      # sinónimo del artículo
    articulo_existente: bool = False  # si ya existía en la base
    articulo_creado: bool = False     # si se creó durante este proceso

    def __post_init__(self):
        if self.subtotal == 0:
            self.subtotal = self.cantidad * self.precio_unitario


@dataclass
class Factura:
    """Datos completos de una factura de proveedor."""
    proveedor_id: int              # código del proveedor (ej: 594 = Wake)
    proveedor_nombre: str = ""     # nombre del proveedor
    marca_id: int = 0              # código de marca (ej: 746 = Wake)
    numero_factura: str = ""       # número de factura/remito
    fecha: date = None             # fecha de la factura
    tipo_comprobante: str = "FC"   # FC=Factura, RM=Remito, NP=Nota de Pedido
    lineas: list = field(default_factory=list)  # lista de LineaFactura
    observaciones: str = ""
    # Campos de imagen
    imagen_factura: str = ""       # ruta a la imagen de la factura escaneada
    imagenes_productos: dict = field(default_factory=dict)  # {modelo: [rutas]}

    def __post_init__(self):
        if self.fecha is None:
            self.fecha = date.today()

    @property
    def total(self) -> float:
        return sum(l.subtotal for l in self.lineas)

    @property
    def total_pares(self) -> int:
        return sum(l.cantidad for l in self.lineas)

    def agregar_curva(self, modelo: str, descripcion: str, color: str,
                      talles: list[str], cantidades: list[int],
                      precio_unitario: float, descuento_comercial: float = 0,
                      codigo_barra_fabricante: str = "",
                      codigo_producto: str = "",
                      descripcion_1: str = "", descripcion_3: str = ""):
        """
        Agrega una curva de talles (múltiples líneas del mismo modelo/color).

        Args:
            talles: ["31", "32", "33", "34", "35", "36"]
            cantidades: [2, 3, 3, 3, 2, 2]  (curva de talles)
            codigo_producto: código del artículo según el proveedor (ej: "RBK-HP6003")
            descripcion_1: descripción larga para la DB
        """
        for talle, cant in zip(talles, cantidades):
            if cant > 0:
                self.lineas.append(LineaFactura(
                    modelo=modelo,
                    descripcion=descripcion,
                    color=color,
                    talle=talle,
                    cantidad=cant,
                    precio_unitario=precio_unitario,
                    descuento_comercial=descuento_comercial,
                    codigo_barra_fabricante=codigo_barra_fabricante,
                    codigo_producto=codigo_producto,
                    descripcion_1=descripcion_1,
                    descripcion_3=descripcion_3,
                ))


# ══════════════════════════════════════════════════════════════════
# MAPEO DE MARCAS Y PREFIJOS
# ══════════════════════════════════════════════════════════════════

# Prefijos de sinónimo → código de marca
PREFIJO_MARCA = {
    "WK": 746,   # Wake
    "TP": 314,   # Topper
    "AT": 794,   # Atomik
    "RBK": 513,  # Reebok (Distrinando)
    # Agregar más según necesidad
}

# Marca → prefijo proveedor en sinónimo
MARCA_PREFIJO_PROVEEDOR = {
    746: "594",   # Wake → proveedor 594
    314: "668",   # Topper → proveedor 668
    513: "656",   # Reebok → proveedor 656 (Distrinando)
    # Agregar más
}

# Marca → mapeo de código barra (letras → números)
MARCA_BARRA_MAP = {
    746: {"WK": "28"},   # Wake: WK → 28 en código de barra
    314: {},              # Topper: código de barra = sinónimo numérico directo
    513: {},              # Reebok: sin mapeo especial
}


def detectar_marca(modelo: str) -> int:
    """Detecta la marca a partir del prefijo del modelo."""
    modelo_upper = modelo.upper().strip()
    for prefijo, marca_id in PREFIJO_MARCA.items():
        if modelo_upper.startswith(prefijo):
            return marca_id
    return 0  # desconocida


def buscar_codigo_objeto_costo(descripcion_producto: str, proveedor: int = 0) -> str | None:
    """
    Busca los 5 chars del sinónimo (posiciones 4-8, o sea [3:8]) en artículos existentes
    que matcheen la descripción del producto.
    Ej: 'FLEXAGON ENERGY TR 4 AZUL/BLANCO' → sinónimo '656ZAZUL02XX' → retorna 'ZAZUL'
    Retorna el código de 5 chars o None si no hay match.
    """
    import pyodbc
    from config import CONN_COMPRAS

    # Limpiar: sacar color y sufijos, dejar solo el nombre del modelo
    desc_clean = descripcion_producto.upper().strip()
    # Sacar todo después de la primera palabra de color común
    for corte in ["NEGRO", "BLANCO", "GRIS", "AZUL", "ROJO", "BEIGE", "ROSA",
                  "NUDE", "CELESTE", "LILA", "VERDE", "MARRON", "ZAPA", "ZAPATILLA"]:
        idx = desc_clean.find(corte)
        if idx > 5:
            desc_clean = desc_clean[:idx].strip()
            break

    if len(desc_clean) < 5:
        return None

    # Extraer los 5 chars del sinónimo (posiciones 4-8) de artículos existentes
    sql = """
        SELECT TOP 1 SUBSTRING(codigo_sinonimo, 4, 5) AS cod5
        FROM msgestion01art.dbo.articulo
        WHERE descripcion_1 LIKE ? AND proveedor = ?
              AND LEN(RTRIM(codigo_sinonimo)) >= 12
        ORDER BY codigo DESC
    """
    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, f"%{desc_clean}%", proveedor)
            row = cursor.fetchone()
            if row and row[0]:
                return row[0].strip()
    except Exception as e:
        log.warning(f"Error buscando codigo_objeto_costo para '{desc_clean}': {e}")
    return None


def buscar_color_code_existente(descripcion_producto: str, color: str, proveedor: int = 0) -> str | None:
    """
    Busca el código de color (2 dígitos, posiciones 9-10 del sinónimo) en artículos
    existentes del mismo modelo y color.
    Color puede ser 'AZUL/BLANCO' → busca con 'AZUL' (primera parte antes de /).
    """
    import pyodbc
    from config import CONN_COMPRAS

    # Limpiar descripcion: sacar colores y sufijos
    desc_clean = descripcion_producto.upper().strip()
    for corte in ["NEGRO", "BLANCO", "GRIS", "AZUL", "ROJO", "BEIGE", "ROSA",
                  "NUDE", "CELESTE", "LILA", "VERDE", "MARRON", "ZAPA", "ZAPATILLA"]:
        idx = desc_clean.find(corte)
        if idx > 5:
            desc_clean = desc_clean[:idx].strip()
            break

    # Color principal: primera parte antes de /
    color_principal = color.split("/")[0].strip() if "/" in color else color.strip()

    sql = """
        SELECT TOP 1 SUBSTRING(codigo_sinonimo, 9, 2) AS color_code
        FROM msgestion01art.dbo.articulo
        WHERE descripcion_1 LIKE ? AND descripcion_4 LIKE ?
              AND proveedor = ? AND LEN(RTRIM(codigo_sinonimo)) >= 12
        ORDER BY codigo DESC
    """
    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, f"%{desc_clean}%", f"%{color_principal}%", proveedor)
            row = cursor.fetchone()
            if row and row[0]:
                return row[0].strip()
    except Exception as e:
        log.warning(f"Error buscando color_code: {e}")
    return None


def construir_sinonimo(modelo: str, color_code: str, talle: str,
                       marca_id: int = 0, codigo_objeto_costo: str = "",
                       descripcion: str = "", color: str = "",
                       proveedor: int = 0) -> str:
    """
    Construye el sinónimo GENÉRICO de 12 dígitos:
        {proveedor:3}{codigo_prov:5}{color:2}{talle:2}

    Ejemplo: proveedor=656, cod5="FETR4", color=13(GRIS), talle=40
             → "656FETR41340"

    Prioridad para cod5:
      1. codigo_objeto_costo explícito (del usuario o caller)
      2. Auto-búsqueda en DB: busca artículos existentes del mismo producto/proveedor
      3. Fallback: limpia el modelo (strippea prefijos de marca)

    Formato talle: 2 dígitos. Talles con medio punto (ej: 39.5) → se truncan
    a entero por ahora (problema conocido pendiente de resolver).
    """
    # ── Proveedor: 3 dígitos ──
    prov_str = str(proveedor).zfill(3)[:3]

    # ── Código proveedor (codigo_prov): 5 caracteres ──
    # Prioridad 1: codigo_objeto_costo explícito
    cod_prov = codigo_objeto_costo.strip() if codigo_objeto_costo else ""

    # Prioridad 2: auto-buscar en DB por descripción del producto
    if not cod_prov and proveedor and descripcion:
        try:
            cod_db = buscar_codigo_objeto_costo(descripcion, proveedor)
            if cod_db:
                cod_prov = cod_db
                log.info(f"  cod5 auto-detectado de DB: '{cod_prov}' para '{descripcion[:40]}'")
        except Exception as e:
            log.debug(f"  Auto-búsqueda cod5 falló: {e}")

    # Prioridad 3: fallback — limpiar el modelo
    if not cod_prov:
        mod_clean = modelo.upper().strip()

        # Para Reebok (656) y similares: el modelo viene como "RBK1100033358"
        # (código largo del proveedor), no sirve para 5 chars. Intentar generar
        # un código de 5 chars desde la descripción del producto.
        is_long_ref = False
        for prefix in ["RBK-", "RBK", "WKC", "WK-", "WK"]:
            if mod_clean.startswith(prefix):
                stripped = mod_clean[len(prefix):].replace("-", "").replace(" ", "")
                if len(stripped) > 5:
                    is_long_ref = True  # es un código largo del proveedor
                else:
                    mod_clean = stripped
                break

        if is_long_ref and descripcion:
            # Generar abreviatura de 5 chars desde la descripción
            # Ej: "FLEXAGON ENERGY TR 4" → "FETR4"
            desc_parts = descripcion.upper().split()
            # Tomar primera letra de cada palabra + números
            abbr = ""
            for part in desc_parts:
                part_clean = part.strip("()-/,.")
                if not part_clean:
                    continue
                if part_clean.isdigit():
                    abbr += part_clean
                elif part_clean.isalpha():
                    abbr += part_clean[0]
                else:
                    abbr += part_clean[0]
            cod_prov = abbr[:5] if abbr else mod_clean[:5]
            log.info(f"  cod5 generado desde descripcion: '{cod_prov}' ← '{descripcion[:40]}'")
        elif not is_long_ref:
            cod_prov = mod_clean.replace("-", "").replace(" ", "")
        else:
            # Último recurso: tomar los últimos 5 chars del código largo
            stripped = mod_clean
            for prefix in ["RBK-", "RBK", "WKC", "WK-", "WK"]:
                if stripped.startswith(prefix):
                    stripped = stripped[len(prefix):]
                    break
            cod_prov = stripped.replace("-", "").replace(" ", "")[:5]

    # Pad/truncar a 5 caracteres
    # CONVENCIÓN DB: right-pad con ceros (ljust), NO left-pad (zfill)
    # Ejemplo: modelo "239" → "23900", modelo "1127" → "11270"
    # Esto coincide con los sinónimos existentes en la base.
    cod_prov = cod_prov[:5].ljust(5, "0")

    # ── Color: 2 dígitos ──
    color_str = str(color_code).zfill(2)[:2]

    # ── Talle: 2 dígitos ──
    # Usa resolver_talle (3 capas) si está disponible; fallback legacy si no.
    if _resolver_talle_ok:
        talle_str = _tps(str(talle))
    else:
        # Fallback legacy
        talle_clean = str(talle).strip()
        if "." in talle_clean or "," in talle_clean:
            talle_clean = talle_clean.replace(",", ".")
            try:
                talle_num = int(float(talle_clean))
            except ValueError:
                talle_num = 0
            log.warning(f"Talle con medio punto '{talle}' → truncado a {talle_num}")
        else:
            try:
                talle_num = int(talle_clean)
            except ValueError:
                talle_num = 0
                log.warning(f"Talle no numérico: '{talle}' → 00")
        talle_str = str(talle_num).zfill(2)[:2]

    sinonimo = f"{prov_str}{cod_prov}{color_str}{talle_str}"

    # Validación: debe ser exactamente 12 caracteres
    if len(sinonimo) != 12:
        log.warning(f"Sinónimo generado con largo {len(sinonimo)} "
                    f"(esperado 12): '{sinonimo}' — "
                    f"prov={prov_str} cod={cod_prov} color={color_str} talle={talle_str}")

    return sinonimo


def construir_codigo_barra(sinonimo: str, marca_id: int = 0) -> int:
    """
    Construye el código de barra numérico a partir del sinónimo.
    Reemplaza letras según el mapeo de la marca.
    """
    barra = sinonimo
    map_marca = MARCA_BARRA_MAP.get(marca_id, {})
    for letras, numeros in map_marca.items():
        barra = barra.replace(letras, numeros)

    # Si queda alguna letra, convertir a su valor ASCII
    resultado = ""
    for c in barra:
        if c.isdigit():
            resultado += c
        else:
            resultado += str(ord(c.upper()) - 55)  # A=10, B=11, etc.

    try:
        return int(resultado)
    except ValueError:
        return 0


# ══════════════════════════════════════════════════════════════════
# COLORES — MAPEO Y ASIGNACIÓN
# ══════════════════════════════════════════════════════════════════

# ── Cache de colores desde msgestionC.dbo.colores ──────────────
_COLORES_CACHE = {}  # denominacion.upper() → codigo (str 2 dígitos)
_COLORES_CACHE_LOADED = False


def _cargar_colores_db():
    """Carga la tabla colores de la BD y construye el cache denominacion→codigo.
    Solo toma el primer codigo para cada denominacion (el más bajo)."""
    global _COLORES_CACHE, _COLORES_CACHE_LOADED
    if _COLORES_CACHE_LOADED:
        return
    try:
        import pyodbc
        from config import CONN_COMPRAS
        sql = """
            SELECT codigo, RTRIM(denominacion) AS denominacion
            FROM msgestionC.dbo.colores
            WHERE denominacion IS NOT NULL AND RTRIM(denominacion) <> ''
            ORDER BY codigo
        """
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for row in cursor.fetchall():
                denom = row[1].strip().upper()
                cod = str(int(row[0])).zfill(2)
                # Tomar solo el primer código por denominacion (el más bajo)
                if denom not in _COLORES_CACHE:
                    _COLORES_CACHE[denom] = cod
        log.info(f"Colores cargados de DB: {len(_COLORES_CACHE)} denominaciones únicas")
    except Exception as e:
        log.warning(f"No se pudo cargar tabla colores de DB: {e}")
        # Fallback mínimo hardcodeado (tabla colores, códigos reales)
        _COLORES_CACHE.update({
            "NEGRO": "00", "BLANCO": "01", "AZUL": "02", "ROJO": "04",
            "MARRON": "11", "CHOCOLATE": "12", "GRIS": "13", "VERDE": "14",
            "BEIGE": "15", "ROSA": "19", "PLATA": "20", "CAMEL": "22",
            "COBRE": "23", "NUDE": "25", "CELESTE": "28", "ORO": "29",
            "BORDO": "30", "AMARILLO": "35", "SUELA": "41", "MULTICOLOR": "51",
            # Reebok colores compuestos conocidos
            "BLANCO/CELESTE": "01", "AZUL/BLANCO": "05",
            "NEGRO/NEGRO/GRIS": "10", "GRIS/NEGRO/LILA": "13",
            "GRIS/NEGRO/ROSA": "13", "BEIGE/BEIGE": "15", "GRIS/GRIS/AP": "39",
            "CREMA": "15", "TOPO": "13", "MENTA": "14",
        })
    _COLORES_CACHE_LOADED = True


def obtener_color_code(color: str, modelo: str = "") -> str:
    """
    Obtiene el código de 2 dígitos para un color, consultando
    la tabla msgestionC.dbo.colores.

    Para colores compuestos (ej: 'NEGRO/BLANCO'), usa el primer componente.
    """
    _cargar_colores_db()
    color_upper = color.upper().strip()

    # 1. Match exacto en la tabla colores
    if color_upper in _COLORES_CACHE:
        return _COLORES_CACHE[color_upper]

    # 2. Para colores compuestos (NEGRO/BLANCO), tomar primer componente
    primer_color = color_upper.split("/")[0].strip()
    if primer_color in _COLORES_CACHE:
        return _COLORES_CACHE[primer_color]

    # 3. Búsqueda parcial: si el color contiene una denominación conocida
    for denom, cod in _COLORES_CACHE.items():
        if denom in color_upper:
            return cod

    log.warning(f"Color no mapeado: '{color}'. Asignando código 00 (NEGRO por defecto).")
    return "00"


# ══════════════════════════════════════════════════════════════════
# BÚSQUEDA Y CREACIÓN DE ARTÍCULOS
# ══════════════════════════════════════════════════════════════════

def buscar_articulo_por_sinonimo(sinonimo: str, proveedor: int = 0,
                                  modelo: str = "", color: str = "",
                                  talle: str = "") -> dict | None:
    """Busca un artículo por sinónimo en la base.

    Si no encuentra por sinónimo exacto, intenta búsqueda fallback
    por proveedor + modelo + color + talle en descripcion_1/descripcion_4.
    Esto resuelve diferencias de padding o convención en sinónimos.
    """
    import pyodbc
    from config import CONN_COMPRAS

    def _row_to_dict(row):
        return {
            "codigo": row[0], "descripcion_1": row[1],
            "codigo_sinonimo": row[2], "color": row[3],
            "talle": row[4], "marca": row[5],
            "precio_fabrica": row[6], "precio_costo": row[7],
            "descuento": row[8], "descuento_1": row[9],
        }

    sql_cols = """codigo, descripcion_1, codigo_sinonimo, descripcion_4,
                  descripcion_5, marca, precio_fabrica, precio_costo,
                  descuento, descuento_1"""

    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()

            # 1. Búsqueda exacta por sinónimo
            cursor.execute(f"""
                SELECT {sql_cols} FROM msgestion01art.dbo.articulo
                WHERE codigo_sinonimo = ?
            """, sinonimo)
            row = cursor.fetchone()
            if row:
                return _row_to_dict(row)

            # 2. Fallback: buscar por proveedor + modelo + color + talle
            #    Busca en descripcion_1 que empiece con el modelo y
            #    descripcion_4 que contenga el color, filtrado por talle
            if proveedor and modelo and color and talle:
                modelo_clean = modelo.strip()
                color_clean = color.strip().split("/")[0]  # primer color
                talle_clean = talle.strip()

                # Buscar artículos del proveedor (o proveedores relacionados)
                # Comoditas puede ser 98 o 776, etc.
                cursor.execute(f"""
                    SELECT {sql_cols} FROM msgestion01art.dbo.articulo
                    WHERE proveedor = ?
                      AND descripcion_1 LIKE ?
                      AND descripcion_4 LIKE ?
                      AND descripcion_5 = ?
                """, proveedor, f"{modelo_clean} %{color_clean}%",
                     f"%{color_clean}%", talle_clean)
                row = cursor.fetchone()
                if row:
                    log.info(f"  Fallback: sinónimo '{sinonimo}' no encontrado, "
                             f"pero hallado por desc: código {row[0]}")
                    return _row_to_dict(row)

                # 3. Último intento: buscar sin filtro de proveedor exacto
                #    (por si hay variación en código de proveedor)
                cursor.execute(f"""
                    SELECT TOP 1 {sql_cols} FROM msgestion01art.dbo.articulo
                    WHERE descripcion_1 LIKE ?
                      AND descripcion_4 LIKE ?
                      AND descripcion_5 = ?
                    ORDER BY codigo DESC
                """, f"{modelo_clean} %{color_clean}%",
                     f"%{color_clean}%", talle_clean)
                row = cursor.fetchone()
                if row:
                    log.info(f"  Fallback amplio: código {row[0]} "
                             f"(prov en DB: distinto al seleccionado {proveedor})")
                    return _row_to_dict(row)

    except Exception as e:
        log.error(f"Error buscando sinónimo {sinonimo}: {e}")
    return None


_TIPO_MODELO_CACHE = {}

def _buscar_tipo_modelo_base(modelo_upper: str, marca_id: int) -> str:
    """
    Busca el tipo de calzado del modelo base (sin sufijo _I26/_V26) en la BD.
    Ej: WKC055_I26 → busca WKC055 → devuelve "PANCHA C/DIRECTO COMB"
    """
    import re as _re
    modelo_base = _re.sub(r'_[IV]\d{2}$', '', modelo_upper)

    if modelo_base in _TIPO_MODELO_CACHE:
        return _TIPO_MODELO_CACHE[modelo_base]

    tipo = ""
    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT TOP 1 RTRIM(descripcion_1)
                FROM msgestion01art.dbo.articulo
                WHERE descripcion_1 LIKE ? AND marca = ? AND estado = 'V'
                  AND LEN(RTRIM(descripcion_1)) > ?
                ORDER BY codigo DESC
            """, [f"{modelo_base} %", marca_id, len(modelo_base) + 10])
            row = cursor.fetchone()
            if row:
                partes = row[0].split()
                if len(partes) >= 3:
                    # partes[0]=modelo, partes[1]=color, resto=tipo
                    tipo = " ".join(partes[2:])
    except Exception as e:
        log.warning(f"Error buscando tipo modelo base {modelo_base}: {e}")

    _TIPO_MODELO_CACHE[modelo_base] = tipo
    return tipo


def crear_articulo(linea: LineaFactura, marca_id: int, proveedor_id: int,
                   color_code: str, sinonimo: str) -> int:
    """
    Crea un artículo nuevo en la base de datos.
    Retorna el código asignado, o 0 si falla.

    Pricing:
        precio_fabrica = linea.precio_unitario
        descuento_1 = linea.descuento_comercial (comercial de factura)
        descuento = descuento estándar del proveedor (de config)
        precio_costo = precio_fabrica × (1 - descuento/100)
        precio_N = precio_costo × (1 + utilidad_N/100)
    """
    import pyodbc
    from config import CONN_COMPRAS, PROVEEDORES
    from proveedores_db import buscar_proveedor_por_cuit, obtener_pricing_proveedor

    # 1) Buscar en config.py (overrides manuales)
    prov = PROVEEDORES.get(proveedor_id)
    # 2) Si no está, buscar dinámicamente en la BD
    if not prov:
        log.info(f"Proveedor {proveedor_id} no en config.py, buscando en BD...")
        pricing = obtener_pricing_proveedor(proveedor_id)
        if pricing:
            # Obtener datos básicos del proveedor desde la tabla proveedores
            try:
                conn_tmp = pyodbc.connect(CONN_COMPRAS, timeout=10)
                cur_tmp = conn_tmp.cursor()
                cur_tmp.execute(
                    "SELECT numero, denominacion, cuit, condicion_iva, zona "
                    "FROM msgestionC.dbo.proveedores WHERE numero = ?",
                    proveedor_id)
                row = cur_tmp.fetchone()
                conn_tmp.close()
                if row:
                    prov = {
                        "nombre": row.denominacion.strip() if row.denominacion else "",
                        "cuit": (row.cuit or "").strip().replace("-", ""),
                        "condicion_iva": (row.condicion_iva or "I").strip(),
                        "zona": row.zona or 0,
                    }
                    prov.update(pricing)
                    log.info(f"Proveedor {proveedor_id} encontrado en BD: {prov['nombre']}")
            except Exception as e:
                log.error(f"Error buscando proveedor {proveedor_id} en BD: {e}")
    if not prov:
        log.error(f"Proveedor {proveedor_id} no encontrado ni en config.py ni en BD")
        return 0

    # Calcular precios
    pf = linea.precio_unitario
    desc_estandar = prov["descuento"]
    pc = round(float(pf) * (1 - float(desc_estandar) / 100), 2)

    precios = {
        "precio_fabrica": float(pf),
        "descuento": float(desc_estandar),
        "descuento_1": linea.descuento_comercial,
        "precio_costo": pc,
        "precio_sugerido": pc,
        "precio_1": round(pc * (1 + float(prov["utilidad_1"]) / 100), 2),
        "precio_2": round(pc * (1 + float(prov["utilidad_2"]) / 100), 2),
        "precio_3": round(pc * (1 + float(prov["utilidad_3"]) / 100), 2),
        "precio_4": round(pc * (1 + float(prov["utilidad_4"]) / 100), 2),
    }

    # Código de barra
    codigo_barra = construir_codigo_barra(sinonimo, marca_id)

    # Descripción
    modelo_upper = linea.modelo.upper()
    color_upper = linea.color.upper().strip()

    # Si viene descripcion_1 del OCR (Distrinando), usarla directo
    if linea.descripcion_1 and len(linea.descripcion_1) > 10:
        desc_1 = linea.descripcion_1[:90].strip()
        desc_3 = linea.descripcion_3 if linea.descripcion_3 else desc_1[:26]
    else:
        # Buscar tipo de calzado del modelo base en la BD
        tipo_desc = _buscar_tipo_modelo_base(modelo_upper, marca_id)

        if not tipo_desc:
            # Fallback: detectar por keywords en la descripción del proveedor
            desc_parts = linea.descripcion.upper().split()
            tipo_desc = "ZAPA URB"  # default genérico
            for w in desc_parts:
                if w in ("BORCEGO", "SANDALIA", "OJOTA", "BOTA", "PANCHA",
                         "CHINELA", "MOCASIN", "BOTINETA", "TEXANA", "ZUECO"):
                    tipo_desc = w
                    break

        desc_1 = f"{modelo_upper} {color_upper} {tipo_desc}"
        if "YOUTH" in linea.descripcion.upper() or "V26" in linea.descripcion.upper():
            desc_1 = f"{modelo_upper} V26 {color_upper} {tipo_desc} YOUTH"

        desc_3 = f"{modelo_upper} {tipo_desc}"[:26]
        if "V26" in linea.descripcion.upper():
            desc_3 = f"{modelo_upper} V26 {tipo_desc}"[:26]

    # Obtener nuevo código con MAX+1 y reintentos
    MAX_REINTENTOS = 5
    for intento in range(MAX_REINTENTOS):
        try:
            with pyodbc.connect(CONN_COMPRAS, timeout=15) as conn:
                cursor = conn.cursor()

                # Obtener siguiente código disponible
                cursor.execute("""
                    SELECT MAX(codigo) + 1
                    FROM msgestion01art.dbo.articulo WITH (UPDLOCK)
                """)
                nuevo_codigo = cursor.fetchone()[0] or 1

                # Insertar artículo
                cursor.execute("""
                    INSERT INTO msgestion01art.dbo.articulo (
                        codigo, descripcion_1, descripcion_3, descripcion_4, descripcion_5,
                        codigo_barra, codigo_sinonimo, marca, rubro, subrubro,
                        precio_fabrica, descuento, descuento_1, descuento_2, descuento_3, descuento_4,
                        precio_costo, precio_sugerido,
                        precio_1, precio_2, precio_3, precio_4,
                        utilidad_1, utilidad_2, utilidad_3, utilidad_4,
                        formula, calificacion, factura_por_total, grupo,
                        alicuota_iva1, alicuota_iva2, tipo_iva,
                        cuenta_compras, cuenta_ventas, cuenta_com_anti,
                        linea, estado, proveedor, moneda,
                        numero_maximo, tipo_codigo_barra, stock,
                        codigo_objeto_costo, nomenclador_arba, alicuota_rg5329,
                        fecha_alta, fecha_ult_compra, usuario, abm,
                        fecha_hora, fecha_modificacion
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, 4, 52,
                        ?, ?, ?, 0, 0, 0,
                        ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        1, 'G', 'N', '5',
                        21, 10.5, 'G',
                        '1010601', '4010100', '1010601',
                        1, 'V', ?, 0,
                        'S', 'C', 'S',
                        ?, '', 0,
                        GETDATE(), GETDATE(), 'AM', 'A',
                        GETDATE(), GETDATE()
                    )
                """, (
                    nuevo_codigo, desc_1, desc_3, color_upper,
                    _tpd5(str(linea.talle)) if _resolver_talle_ok else str(linea.talle),
                    codigo_barra, sinonimo, marca_id,
                    precios["precio_fabrica"], precios["descuento"], precios["descuento_1"],
                    precios["precio_costo"], precios["precio_sugerido"],
                    precios["precio_1"], precios["precio_2"],
                    precios["precio_3"], precios["precio_4"],
                    prov["utilidad_1"], prov["utilidad_2"],
                    prov["utilidad_3"], prov["utilidad_4"],
                    proveedor_id,
                    sinonimo[3:8] if len(sinonimo) >= 8 else linea.modelo.upper()[:5],
                ))

                # Insertar articulos_prov (vincula código artículo con proveedor)
                # codigo_proveedor = código del producto según el proveedor (ej: "FLEZAZUL", "LIP26")
                codigo_art_prov = linea.codigo_producto or linea.modelo.upper()[:30]
                try:
                    cursor.execute("""
                        INSERT INTO msgestion01art.dbo.articulos_prov
                            (codigo, proveedor, codigo_proveedor, porc_gan)
                        VALUES (?, ?, ?, NULL)
                    """, (
                        nuevo_codigo, proveedor_id, codigo_art_prov,
                    ))
                except Exception as ap_err:
                    log.warning(f"  No se pudo insertar articulos_prov: {ap_err}")

                conn.commit()
                log.info(f"  Artículo creado: {nuevo_codigo} = {desc_1} (sinónimo: {sinonimo})")
                return nuevo_codigo

        except Exception as e:
            if "PRIMARY KEY" in str(e) or "UNIQUE" in str(e) or "23000" in str(e):
                log.warning(f"  Código {nuevo_codigo} en conflicto (intento {intento+1}), reintentando...")
                continue
            log.error(f"  Error creando artículo: {e}")
            return 0

    log.error(f"  No se pudo crear artículo después de {MAX_REINTENTOS} intentos")
    return 0


# ══════════════════════════════════════════════════════════════════
# PROCESAMIENTO DE FACTURA
# ══════════════════════════════════════════════════════════════════

def procesar_factura(factura: Factura) -> dict:
    """
    Procesa una factura completa:
    1. Para cada línea, busca o crea el artículo
    2. Prepara datos para pedido/remito

    Returns:
        dict con: exitosos, fallidos, articulos_creados, articulos_existentes,
                  lineas_procesadas, errores
    """
    resultado = {
        "exitosos": 0,
        "fallidos": 0,
        "articulos_creados": 0,
        "articulos_existentes": 0,
        "lineas_procesadas": [],
        "errores": [],
    }

    marca_id = factura.marca_id
    if marca_id == 0:
        # Detectar marca de la primera línea
        if factura.lineas:
            marca_id = detectar_marca(factura.lineas[0].modelo)
        if marca_id == 0:
            resultado["errores"].append("No se pudo detectar la marca")
            return resultado

    log.info(f"Procesando factura {factura.numero_factura} - {factura.proveedor_nombre}")
    log.info(f"  {len(factura.lineas)} líneas, {factura.total_pares} pares, total ${factura.total:,.0f}")

    for i, linea in enumerate(factura.lineas):
        log.info(f"\n  [{i+1}/{len(factura.lineas)}] {linea.descripcion} T:{linea.talle} x{linea.cantidad}")

        # Obtener código de color
        color_code = obtener_color_code(linea.color, linea.modelo)

        # Construir sinónimo
        sinonimo = construir_sinonimo(
            linea.modelo, color_code, linea.talle, marca_id,
            descripcion=linea.descripcion_1 or linea.descripcion,
            color=linea.color,
            proveedor=factura.proveedor_id,
        )
        linea.codigo_sinonimo = sinonimo
        log.info(f"    Sinónimo: {sinonimo}")

        # Buscar si ya existe (sinónimo exacto + fallback por descripción)
        existente = buscar_articulo_por_sinonimo(
            sinonimo, proveedor=factura.proveedor_id,
            modelo=linea.modelo, color=linea.color, talle=linea.talle)

        if existente:
            linea.codigo_articulo = existente["codigo"]
            linea.articulo_existente = True
            log.info(f"    Existente: código {existente['codigo']}")

            # Verificar si el precio cambió
            if existente["precio_fabrica"] != linea.precio_unitario:
                log.warning(f"    ⚠ Precio cambió: {existente['precio_fabrica']} → {linea.precio_unitario}")
                # Actualizar precio si cambió
                _actualizar_precio(existente["codigo"], linea, factura.proveedor_id)

            resultado["articulos_existentes"] += 1
            resultado["exitosos"] += 1

        else:
            # Crear artículo nuevo
            log.info(f"    No existe, creando...")
            nuevo_codigo = crear_articulo(
                linea=linea,
                marca_id=marca_id,
                proveedor_id=factura.proveedor_id,
                color_code=color_code,
                sinonimo=sinonimo,
            )
            if nuevo_codigo > 0:
                linea.codigo_articulo = nuevo_codigo
                linea.articulo_creado = True
                resultado["articulos_creados"] += 1
                resultado["exitosos"] += 1
            else:
                resultado["fallidos"] += 1
                resultado["errores"].append(f"No se pudo crear: {linea.descripcion} T:{linea.talle}")

        resultado["lineas_procesadas"].append(asdict(linea))

    log.info(f"\n{'='*50}")
    log.info(f"RESULTADO: {resultado['exitosos']}/{len(factura.lineas)} exitosos")
    log.info(f"  Existentes: {resultado['articulos_existentes']}")
    log.info(f"  Creados: {resultado['articulos_creados']}")
    log.info(f"  Fallidos: {resultado['fallidos']}")

    return resultado


def _actualizar_precio(codigo: int, linea: LineaFactura, proveedor_id: int):
    """Actualiza el precio de un artículo existente si cambió."""
    import pyodbc
    from config import CONN_COMPRAS, PROVEEDORES
    from proveedores_db import obtener_pricing_proveedor

    prov = PROVEEDORES.get(proveedor_id)
    if not prov:
        prov = obtener_pricing_proveedor(proveedor_id)
    desc_estandar = prov.get("descuento", 0)
    pf = linea.precio_unitario
    pc = round(pf * (1 - desc_estandar / 100), 2)

    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE msgestion01art.dbo.articulo SET
                    precio_fabrica = ?,
                    descuento_1 = ?,
                    precio_costo = ?,
                    precio_sugerido = ?,
                    precio_1 = ?,
                    precio_2 = ?,
                    precio_3 = ?,
                    precio_4 = ?,
                    fecha_ult_compra = GETDATE(),
                    fecha_modificacion = GETDATE(),
                    usuario = 'AM',
                    abm = 'M'
                WHERE codigo = ?
            """, (
                pf,
                linea.descuento_comercial,
                pc, pc,
                round(pc * (1 + prov.get("utilidad_1", 0) / 100), 2),
                round(pc * (1 + prov.get("utilidad_2", 0) / 100), 2),
                round(pc * (1 + prov.get("utilidad_3", 0) / 100), 2),
                round(pc * (1 + prov.get("utilidad_4", 0) / 100), 2),
                codigo,
            ))
            conn.commit()
            log.info(f"    Precio actualizado: fabrica={pf}, costo={pc}")
    except Exception as e:
        log.error(f"    Error actualizando precio de {codigo}: {e}")


# ══════════════════════════════════════════════════════════════════
# CREACIÓN DE PEDIDO / REMITO
# ══════════════════════════════════════════════════════════════════

def crear_pedido_desde_factura(factura: Factura, resultado_procesar: dict,
                               tipo: str = "NP") -> dict:
    """
    Crea un pedido o remito a partir de la factura procesada.

    Args:
        factura: datos de la factura
        resultado_procesar: resultado de procesar_factura()
        tipo: "NP" = Nota de Pedido, "RM" = Remito

    Returns:
        dict con: numero_pedido, exitoso, error
    """
    # Importar paso4 para crear pedido
    try:
        from paso4_insertar_pedido import insertar_pedido
        from paso3_calcular_periodo import calcular_periodo
    except ImportError:
        log.error("No se pueden importar paso3/paso4")
        return {"numero_pedido": 0, "exitoso": False, "error": "Módulos no disponibles"}

    # Filtrar solo líneas exitosas
    lineas_ok = [l for l in resultado_procesar["lineas_procesadas"]
                 if l.get("codigo_articulo", 0) > 0]

    if not lineas_ok:
        return {"numero_pedido": 0, "exitoso": False, "error": "No hay líneas procesadas"}

    # Calcular período
    try:
        periodo = calcular_periodo(factura.fecha, subrubro=52)  # 52 = zapatería deportiva
    except Exception as e:
        log.warning(f"Error calculando período: {e}, usando fecha de factura")
        periodo = {"periodo": factura.fecha.strftime("%Y%m"), "entrega": factura.fecha}

    # Armar estructura de pedido
    items_pedido = []
    for linea in lineas_ok:
        items_pedido.append({
            "codigo_articulo": linea["codigo_articulo"],
            "cantidad": linea["cantidad"],
            "precio_unitario": linea["precio_unitario"],
            "descuento_1": linea.get("descuento_comercial", 0),
        })

    pedido_data = {
        "proveedor": factura.proveedor_id,
        "fecha": factura.fecha,
        "tipo": tipo,
        "numero_factura": factura.numero_factura,
        "items": items_pedido,
        "observaciones": factura.observaciones,
    }

    try:
        resultado = insertar_pedido(pedido_data)
        return {
            "numero_pedido": resultado.get("numero", 0),
            "exitoso": resultado.get("ok", False),
            "error": resultado.get("error", ""),
        }
    except Exception as e:
        log.error(f"Error creando pedido: {e}")
        return {"numero_pedido": 0, "exitoso": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════
# PARSEO DE DATOS DE FACTURA
# ══════════════════════════════════════════════════════════════════

def parsear_factura_wake(datos: dict) -> Factura:
    """
    Parsea datos de una factura Wake en formato dict.

    Formato esperado:
    {
        "proveedor_id": 594,
        "numero_factura": "A-0001-00012345",
        "fecha": "2026-03-01",
        "articulos": [
            {
                "modelo": "WKC215",
                "variante": "V26 MOD.YOUTH",
                "color": "NEGRO",
                "talles": ["31", "32", "33", "34", "35", "36"],
                "curva": [2, 3, 3, 3, 2, 2],
                "precio_unitario": 15000,
                "descuento_comercial": 0,
                "codigo_barra": "2621150147910FL"
            }
        ]
    }
    """
    factura = Factura(
        proveedor_id=datos.get("proveedor_id", 594),
        proveedor_nombre=datos.get("proveedor_nombre", "INDUSTRIAS AS S.A."),
        marca_id=datos.get("marca_id", 746),
        numero_factura=datos.get("numero_factura", ""),
        fecha=datetime.strptime(datos["fecha"], "%Y-%m-%d").date() if isinstance(datos.get("fecha"), str) else datos.get("fecha", date.today()),
        tipo_comprobante=datos.get("tipo", "FC"),
    )

    for art in datos.get("articulos", []):
        modelo = art.get("modelo", "")
        variante = art.get("variante", "")
        color = art.get("color", "")
        desc = f"{modelo} {variante} {color}".strip()

        talles = art.get("talles", [])
        curva = art.get("curva", [1] * len(talles))
        precio = art.get("precio_unitario", 0)
        dcto = art.get("descuento_comercial", 0)
        barra = art.get("codigo_barra", "")

        # Para Distrinando/Reebok: variante tiene la descripción larga del OCR
        # codigo_producto viene del modelo (que es el RBK-xxx del proveedor)
        desc_1 = variante if len(variante) > len(modelo) else desc
        codigo_prov = art.get("codigo_producto", modelo)

        factura.agregar_curva(
            modelo=modelo,
            descripcion=desc,
            color=color,
            talles=talles,
            cantidades=curva,
            precio_unitario=precio,
            descuento_comercial=dcto,
            codigo_barra_fabricante=barra,
            codigo_producto=codigo_prov,
            descripcion_1=desc_1,
        )

    return factura


# ══════════════════════════════════════════════════════════════════
# SERIALIZACIÓN (para guardar estado y debugging)
# ══════════════════════════════════════════════════════════════════

def guardar_factura_json(factura: Factura, resultado: dict,
                         carpeta: str = None) -> str:
    """Guarda la factura procesada como JSON para auditoría."""
    if carpeta is None:
        carpeta = os.path.join(os.path.dirname(__file__), "facturas_procesadas")
    os.makedirs(carpeta, exist_ok=True)

    nombre = f"{factura.fecha.isoformat()}_{factura.proveedor_id}_{factura.numero_factura or 'SN'}.json"
    nombre = nombre.replace("/", "-").replace("\\", "-")
    path = os.path.join(carpeta, nombre)

    data = {
        "factura": {
            "proveedor_id": factura.proveedor_id,
            "proveedor_nombre": factura.proveedor_nombre,
            "marca_id": factura.marca_id,
            "numero_factura": factura.numero_factura,
            "fecha": factura.fecha.isoformat(),
            "tipo": factura.tipo_comprobante,
            "total": factura.total,
            "total_pares": factura.total_pares,
        },
        "resultado": resultado,
        "timestamp": datetime.now().isoformat(),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    log.info(f"Factura guardada: {path}")
    return path


# ══════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════

def main():
    """Ejemplo de uso desde CLI."""
    print("=" * 60)
    print("CARGA DE FACTURA — Sistema H4/Calzalindo")
    print("=" * 60)

    # Ejemplo con los datos de la factura Wake que ya procesamos
    datos_factura = {
        "proveedor_id": 594,
        "proveedor_nombre": "INDUSTRIAS AS S.A.",
        "marca_id": 746,
        "numero_factura": "",
        "fecha": "2026-03-06",
        "articulos": [
            {
                "modelo": "WKC215",
                "variante": "V26 MOD.YOUTH",
                "color": "NEGRO",
                "talles": ["31", "32", "33", "34", "35", "36"],
                "curva": [2, 3, 3, 3, 2, 2],
                "precio_unitario": 15000,
                "descuento_comercial": 0,
                "codigo_barra": "2621150147910FL",
            },
            {
                "modelo": "WKC215",
                "variante": "V26 MOD.YOUTH",
                "color": "NUDE",
                "talles": ["31", "32", "33", "34", "35", "36"],
                "curva": [2, 3, 3, 3, 2, 2],
                "precio_unitario": 15000,
                "descuento_comercial": 0,
                "codigo_barra": "2621150147916FL",
            },
        ],
    }

    factura = parsear_factura_wake(datos_factura)
    print(f"\nFactura: {factura.proveedor_nombre}")
    print(f"  Líneas: {len(factura.lineas)}")
    print(f"  Total pares: {factura.total_pares}")
    print(f"  Total $: {factura.total:,.0f}")
    print()

    # Verificar si podemos conectar a la base
    if not _importar_proyecto():
        print("\n⚠ No se puede conectar a la base de datos (pyodbc no disponible)")
        print("Para ejecutar, correr desde el servidor o Mac con pyodbc instalado:")
        print("  python paso8_carga_factura.py")
        print("\nDatos parseados de la factura:")
        for l in factura.lineas:
            print(f"  {l.modelo} {l.color} T:{l.talle} x{l.cantidad} @${l.precio_unitario:,.0f}")
        return

    # Procesar
    resultado = procesar_factura(factura)

    # Guardar
    path_json = guardar_factura_json(factura, resultado)

    print(f"\nResultado guardado en: {path_json}")


if __name__ == "__main__":
    main()
