#!/usr/bin/env python3
"""
insertar_wake_inv26.py — Alta artículos + Nota de pedido WAKE Sport INV 26
=============================================================================
Proveedor: 594 (INDUSTRIAS AS S.A.)
Marca: 746 (WAKE)
Empresa: H4 → MSGESTION03

Pedido de calzado invierno 2026:
  69 líneas (distintos modelos × colores × talles)
  ~1465 pares total
  Precio mayorista promedio: $23,500-$28,000/par

Categorías:
  FEMENINO (31 líneas): talles 35-40
  MASCULINO (8 líneas): talles 40-45
  KIDS (30 líneas): talles 22-34

Condiciones: 90 días | Descuento: 20%

EJECUTAR EN EL 111:
  py -3 insertar_wake_inv26.py                ← dry-run
  py -3 insertar_wake_inv26.py --ejecutar     ← escribe en producción
"""

import sys
import os
from datetime import date
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONN_COMPRAS, PROVEEDORES

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════

PROVEEDOR    = 594
DENOMINACION = "INDUSTRIAS AS S.A."
EMPRESA      = "H4"
MARCA        = 746       # WAKE (en tabla marcas)
LINEA        = 2         # Invierno

FECHA_PEDIDO  = date(2026, 3, 13)   # fecha del pedido
FECHA_ENTREGA = date(2026, 6, 15)   # entrega estimada

DESC_PROVEEDOR = 20.0   # Descuento: 20%

# Utilidades estándar WAKE (de config.py)
UTILIDAD_1 = 100    # contado
UTILIDAD_2 = 124    # lista
UTILIDAD_3 = 60     # intermedio
UTILIDAD_4 = 45     # mayorista
FORMULA    = 1

OBSERVACIONES = ("Pedido WAKE Sport INV 2026. "
                 "INDUSTRIAS AS S.A. 69 líneas, ~1465 pares. "
                 "Cond: 90 días, Desc: 20%.")

# ══════════════════════════════════════════════════════════════
# DATOS DE PEDIDO — 69 LÍNEAS DESAGREGADAS
# ══════════════════════════════════════════════════════════════
# Formato: (modelo, color, rango_talles, pxT, pedido_count, precio_mayorista)
#
# pxT = lista de cantidad de pares por talle dentro del rango
# Ejemplo: WKC055 VISON 35-40 pxT=[1,1,3,3,2,2] ped=2
#   T35: 2 pares (1×2), T36: 2 (1×2), T37: 6 (3×2), T38: 6 (3×2), T39: 4 (2×2), T40: 4 (2×2) = 24 pares
#
# Nota: Se guardan como tuplas (modelo, color, talles_secuencia, pedido_count, precio_mayorista)

PEDIDOS_FEMENINO = [
    # (modelo, color, [talles], [pxT], pedido_count, precio)
    ("WKC055", "VISON", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 2, 19500),
    ("WKC055", "NEGRO", ["38","39","40"], [3,3,2], 5, 19500),
    ("WKC055_I26", "TOTAL_BLACK", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 2, 19500),
    ("WKC109_I26", "VISON", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 2, 21000),
    ("WKC109_I26", "NEGRO", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 3, 21000),
    ("WKC114_V26", "TOPO", ["35","36","37","38","39","40"], [1,2,3,3,2,1], 2, 23000),
    ("WKC114_V26", "NEGRO", ["35","36","37","38","39","40"], [1,2,3,3,2,1], 3, 23000),
    ("WKC182_I26", "NEGRO", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 4, 24500),
    ("WKC182_I26", "VISON", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 2, 24500),
    ("WKC207_V26", "BLANCO", ["35","36","37","38","39","40"], [1,2,3,3,2,1], 2, 25000),
    ("WKC255_I26", "BEIGE", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 1, 19500),
    ("WKC255_I26", "NEGRO", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 2, 19500),
    ("WKC255_I26", "AERO", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 2, 19500),
    ("WKC263_I26", "VISON", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 2, 24500),
    ("WKC263_I26", "NEGRO", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 3, 24500),
    ("WKC291_V26", "NEGRO", ["35","36","37","38","39","40"], [1,2,3,3,2,1], 1, 27500),
    ("WKC316_I26", "NEGRO", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 2, 24500),
    ("WKC326_I25", "NEGRO", ["35","36","37","38","39","40"], [1,2,3,3,2,1], 2, 26000),
    ("WKC326_I26", "BLANCO", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 2, 26000),
    ("WKC368_I26", "CHOCOLATE", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 1, 28000),
    ("WKC368_I26", "NEGRO", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 1, 28000),
    ("WKC399_V26", "NEGRO", ["35","36","37","38","39","40"], [1,2,3,3,2,1], 2, 23000),
    ("WKC399_V26", "GRIS", ["35","36","37","38","39","40"], [1,2,3,3,2,1], 1, 23000),
    ("WKC404_V26", "NEGRO", ["35","36","37","38","39","40"], [1,2,3,3,2,1], 1, 27500),
    ("WKC404_V26", "BEIGE", ["35","36","37","38","39","40"], [1,2,3,3,2,1], 1, 27500),
    ("WKC409_V26", "NEGRO", ["35","36","37","38","39","40"], [1,2,3,3,2,1], 1, 25000),
    ("WKC409_V26", "BLANCO", ["35","36","37","38","39","40"], [1,2,3,3,2,1], 1, 25000),
    ("WKC447_I26", "NEGRO", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 3, 24500),
    ("WKC447_I26", "BEIGE", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 1, 24500),
    ("WKC493_I26", "VIOLETA", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 1, 24500),
    ("WKC493_I26", "NEGRO", ["35","36","37","38","39","40"], [1,1,3,3,2,2], 2, 24500),
]

PEDIDOS_MASCULINO = [
    ("WKC265_V26", "AZUL", ["40","41","42","43","44","45"], [1,2,3,3,2,1], 2, 24000),
    ("WKC265_V26", "NEGRO", ["40","41","42","43","44","45"], [1,2,3,3,2,1], 2, 24000),
    ("WKC265_V26", "GRIS", ["40","41","42","43","44","45"], [1,2,3,3,2,1], 1, 24000),
    ("WKC307_I26", "GRIS", ["40","41","42","43","44","45"], [1,2,3,3,2,1], 2, 24500),
    ("WKC307_I26", "VERDE", ["40","41","42","43","44","45"], [1,2,3,3,2,1], 1, 24500),
    ("WKC307_I26", "NEGRO", ["40","41","42","43","44","45"], [1,2,3,3,2,1], 3, 24500),
    ("WKC332_I25", "NEGRO", ["40","41","42","43","44","45"], [1,2,3,3,2,1], 2, 20000),
    ("WKC332_I25", "GRIS", ["40","41","42","43","44","45"], [1,2,3,3,2,1], 1, 20000),
]

PEDIDOS_KIDS = [
    # KIDS se divide en grupos por rango de talle
    ("WKC272", "LILA", ["22","23","24","25","26","27"], [2,2,2,2,2,2], 1, 23000),
    ("WKC272_I26", "CREMA", ["22","23","24","25","26","27"], [2,2,2,3,3,3], 2, 23000),
    ("WKC272_I26", "NEGRO", ["22","23","24","25","26","27"], [2,2,2,3,3,3], 2, 23000),
    ("WKC272_I26", "AZUL", ["22","23","24","25","26","27"], [2,2,2,3,3,3], 2, 23000),
    ("WKC273_I26", "PURPURA", ["22","23","24","25","26","27"], [2,2,2,3,3,3], 1, 23000),
    ("WKC273_I26", "VERDE", ["22","23","24","25","26","27"], [2,2,2,3,3,3], 1, 23000),
    ("WKC273_I26", "NEGRO", ["22","23","24","25","26","27"], [2,2,2,3,3,3], 2, 23000),
    ("WKC284_I26", "NEGRO", ["28","29","30","31","32","33","34"], [2,2,2,3,2,2,2], 1, 25000),
    ("WKC284_I26", "NUDE", ["28","29","30","31","32","33","34"], [2,2,2,3,2,2,2], 1, 25000),
    ("WKC378_V26", "NEGRO", ["22","23","24","25","26","27"], [2,2,2,3,3,3], 2, 22000),
    ("WKC378_V26", "ROSA", ["22","23","24","25","26","27"], [2,2,2,3,3,3], 2, 22000),
    ("WKC378_V26", "AZUL", ["22","23","24","25","26","27"], [2,2,2,3,3,3], 2, 22000),
    ("WKC412_I26", "NEGRO", ["24","25","26","27","28","29","30"], [1,1,2,2,2,2,2], 1, 25000),
    ("WKC412_I26", "BLANCO", ["24","25","26","27","28","29","30"], [1,1,2,2,2,2,2], 1, 25000),
    ("WKC413_I26", "VERDE", ["24","25","26","27","28","29","30"], [1,1,2,2,2,2,2], 1, 25000),
    ("WKC413_I26", "GRIS", ["24","25","26","27","28","29","30"], [1,1,2,2,2,2,2], 1, 25000),
    ("WKC413_I26", "NEGRO", ["24","25","26","27","28","29","30"], [1,1,2,2,2,2,2], 2, 25000),
    ("WKC428_I26", "PETROLEO", ["22","23","24","25","26","27"], [2,2,2,3,3,3], 2, 23000),
    ("WKC428_I26", "CREMA", ["22","23","24","25","26","27"], [2,2,2,3,3,3], 2, 23000),
    ("WKC428_I26", "AERO", ["22","23","24","25","26","27"], [2,2,2,3,3,3], 1, 23000),
    ("WKC431_I26", "AZUL", ["24","25","26","27","28","29","30"], [1,1,2,2,2,2,2], 2, 25000),
    ("WKC431_I26", "ROSA", ["24","25","26","27","28","29","30"], [1,1,2,2,2,2,2], 2, 25000),
    ("WKC431_I26", "NEGRO", ["24","25","26","27","28","29","30"], [1,1,2,2,2,2,2], 2, 25000),
    ("WKC432_I26", "NEGRO", ["28","29","30","31","32","33","34"], [2,2,2,3,2,2,2], 1, 25000),
    ("WKC432_I26", "LAVANDA", ["28","29","30","31","32","33","34"], [2,2,2,3,2,2,2], 1, 25000),
    ("WKC433_I26", "NEGRO", ["28","29","30","31","32","33","34"], [2,2,2,3,2,2,2], 1, 25000),
    ("WKC433_I26", "VIOLETA", ["28","29","30","31","32","33","34"], [2,2,2,3,2,2,2], 1, 25000),
    ("WKC496_I26", "TOPO", ["29","30","31","32","33","34"], [2,2,2,2,2,2], 1, 24000),
    ("WKC496_I26", "NEGRO", ["29","30","31","32","33","34"], [2,2,2,2,2,2], 1, 24000),
    ("WKC496_I26", "ROSA", ["29","30","31","32","33","34"], [2,2,2,2,2,2], 1, 24000),
]

# Combinar todos los pedidos
TODOS_PEDIDOS = PEDIDOS_FEMENINO + PEDIDOS_MASCULINO + PEDIDOS_KIDS


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def generar_sinonimo(modelo, color, talle):
    """
    Genera codigo_sinonimo de 12 chars, formato WAKE estándar:
    594 + modelo_num (5 dígitos) + color (2 dígitos) + talle (2 dígitos)

    Ejemplo: WKC055 VISON T35 → 594055??35
    """
    # Extraer parte numérica del modelo
    nums = re.findall(r'\d+', modelo)
    modelo_num = int("".join(nums)) if nums else 0
    modelo_str = f"{modelo_num:05d}"[-5:]   # últimos 5 dígitos

    # Código de color (simplificado: usar primeras letras)
    color_map = {
        "NEGRO": "01", "BLANCO": "02", "GRIS": "03", "BEIGE": "04", "TOPO": "05",
        "AZUL": "06", "VERDE": "07", "ROSA": "08", "AERO": "09", "VIOLETA": "10",
        "CHOCOLATE": "11", "CREMA": "12", "LAVANDA": "13", "PETROLEO": "14",
        "TOTAL_BLACK": "15", "PURPURA": "16", "LILA": "17", "NUDE": "18",
    }
    cc = color_map.get(color.upper().strip(), "00")

    # Talle (2 dígitos)
    tt = f"{int(talle):02d}"

    return f"594{modelo_str}{cc}{tt}"


# ── Cache de tipos de calzado por modelo base ────────────────
_TIPO_CACHE = {}  # modelo_base → "PANCHA C/DIRECTO COMB", etc.

def _obtener_tipo_modelo(modelo):
    """
    Busca en la BD el tipo de calzado del modelo base (sin sufijo _I26/_V26).
    Ej: WKC055_I26 → busca WKC055 → devuelve "PANCHA C/DIRECTO COMB"
    """
    import pyodbc
    # Extraer modelo base (sin _I26, _V26, _I25, etc.)
    modelo_base = re.sub(r'_[IV]\d{2}$', '', modelo)

    if modelo_base in _TIPO_CACHE:
        return _TIPO_CACHE[modelo_base]

    tipo = ""
    try:
        conn = pyodbc.connect(CONN_COMPRAS, timeout=10)
        cursor = conn.cursor()
        # Buscar una desc1 existente del modelo base que tenga tipo (más de solo modelo+color)
        cursor.execute("""
            SELECT TOP 1 RTRIM(descripcion_1)
            FROM msgestion01art.dbo.articulo
            WHERE descripcion_1 LIKE ? AND marca = 746 AND estado = 'V'
              AND LEN(RTRIM(descripcion_1)) > ?
            ORDER BY codigo DESC
        """, [f"{modelo_base} %", len(modelo_base) + 10])
        row = cursor.fetchone()
        conn.close()

        if row:
            desc_existente = row[0]
            # Extraer la parte después de "MODELO COLOR " → tipo
            # Formato: "WKC055 NEGRO PANCHA C/DIRECTO COMB"
            partes = desc_existente.split()
            if len(partes) >= 3:
                # partes[0]=modelo, partes[1]=color, resto=tipo
                tipo = " ".join(partes[2:])
    except Exception:
        pass

    _TIPO_CACHE[modelo_base] = tipo
    return tipo


def construir_desc1(modelo, color):
    """
    desc1: MODELO COLOR TIPO_CALZADO (max 60 chars).
    Busca el tipo del modelo base en BD. Si no encuentra, usa "ZAPA DEP" (default WAKE Sport).
    Ej: WKC055_I26 NEGRO → WKC055_I26 NEGRO PANCHA C/DIRECTO COMB
    """
    tipo = _obtener_tipo_modelo(modelo)
    if not tipo:
        tipo = "ZAPA DEP"  # default para modelos nuevos WAKE Sport
    return f"{modelo} {color} {tipo}"[:60]


def construir_desc3(modelo):
    """desc3: MODELO TIPO (sin color), max 40 chars."""
    tipo = _obtener_tipo_modelo(modelo)
    if not tipo:
        tipo = "ZAPA DEP"
    return f"{modelo} {tipo}"[:40]


def get_rubro_grupo_subrubro(talles_str):
    """
    Determina rubro, grupo y subrubro según el rango de talles.

    Retorna (rubro, grupo, subrubro):
      rubro: 1=DAMAS, 3=HOMBRES, 4=NIÑOS, 5=NIÑAS, 6=UNISEX
      grupo: "2"=tela, "15"=sintético, etc. (copiar de existente WAKE)
      subrubro: 49=Zapatillas, 55=Sneakers, etc.
    """
    # Parsear rango de talles
    min_talle = min(int(t) for t in talles_str) if talles_str else 0
    max_talle = max(int(t) for t in talles_str) if talles_str else 0

    # Clasificar por rango (basado en distribución real de WAKE en BD)
    if max_talle <= 27:
        # KIDS DAMAS (22-27)
        return 5, "15", 49  # rubro=NIÑAS, grupo=15 (sintético), subrubro=Zapatillas
    elif min_talle >= 28 and max_talle <= 34:
        # KIDS (28-34)
        return 4, "17", 49  # rubro=NIÑOS, grupo=17 (textil), subrubro=Zapatillas
    elif min_talle >= 35 and max_talle <= 40:
        # FEMENINO ADULTO
        return 1, "17", 49  # rubro=DAMAS, grupo=17 (textil), subrubro=Zapatillas
    elif min_talle >= 40 and max_talle <= 45:
        # MASCULINO ADULTO
        return 3, "17", 49  # rubro=HOMBRES, grupo=17 (textil), subrubro=Zapatillas
    else:
        # Default
        return 6, "15", 49  # UNISEX


# ══════════════════════════════════════════════════════════════
# CONVERSIÓN QWERTY: letras → número de arriba en el teclado
# ══════════════════════════════════════════════════════════════
QWERTY_MAP = {
    'q': '1', 'w': '2', 'e': '3', 'r': '4', 't': '5',
    'y': '6', 'u': '7', 'i': '8', 'o': '9', 'p': '0',
    'a': '1', 's': '2', 'd': '3', 'f': '4', 'g': '5',
    'h': '6', 'j': '7', 'k': '8', 'l': '9',
    'z': '1', 'x': '2', 'c': '3', 'v': '4', 'b': '5',
    'n': '6', 'm': '7',
}

def sinonimo_a_barras(sinonimo):
    """Convierte codigo_sinonimo a codigo_barra numérico.
    Las letras se reemplazan por el número de arriba en teclado QWERTY.
    Los dígitos quedan igual."""
    return "".join(QWERTY_MAP.get(c.lower(), c) for c in sinonimo)


# ══════════════════════════════════════════════════════════════
# FASE 1: BÚSQUEDA Y ALTA DE ARTÍCULOS
# ══════════════════════════════════════════════════════════════

def buscar_articulo_existente(modelo, color, talle, dry_run=True):
    """
    Busca si un artículo con (modelo, color, talle) ya existe en la BD.
    Búsqueda: descripcion_1 LIKE 'modelo color%' AND descripcion_5 = talle AND marca = 746

    Retorna: código del artículo si existe, None si no existe
    """
    import pyodbc
    try:
        conn = pyodbc.connect(CONN_COMPRAS, timeout=10)
        cursor = conn.cursor()

        # Buscar por descripción y talle (tolerante con sufijos como _I26, _V26)
        desc_pattern = f"{modelo.split('_')[0]} {color}"  # solo la parte base del modelo

        cursor.execute(
            """SELECT TOP 1 codigo FROM msgestion01art.dbo.articulo
               WHERE descripcion_1 LIKE ?
                 AND descripcion_5 = ?
                 AND marca = 746
            """,
            [f"{desc_pattern}%", talle]
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return row[0]
        return None
    except Exception as e:
        print(f"  ⚠️  Error buscando artículo {modelo} {color} T{talle}: {e}")
        return None


def crear_articulo(modelo, color, talle, precio, talles_rango=None, dry_run=True):
    """
    Crea un nuevo artículo en msgestion01art.dbo.articulo.

    talles_rango: lista completa de talles de la línea (para clasificar rubro correcto)
    Retorna: (codigo_nuevo, True) si creado, (codigo_existente, False) si ya existe
    """
    import pyodbc

    # Verificar si ya existe
    codigo_existente = buscar_articulo_existente(modelo, color, talle, dry_run=dry_run)
    if codigo_existente:
        return codigo_existente, False

    if dry_run:
        # En dry-run, asignar un código ficticio negativo
        return -(hash((modelo, color, talle)) % 100000), True

    # En ejecución real, obtener MAX(codigo) + 1 e insertar
    try:
        conn = pyodbc.connect(CONN_COMPRAS, timeout=10)
        cursor = conn.cursor()

        # Obtener próximo código
        cursor.execute("SELECT ISNULL(MAX(codigo), 0) + 1 FROM msgestion01art.dbo.articulo")
        nuevo_codigo = cursor.fetchone()[0]

        # Determinar rubro, grupo, subrubro por el rango completo de talles de la línea
        rubro, grupo, subrubro = get_rubro_grupo_subrubro(talles_rango or [talle])

        desc1 = construir_desc1(modelo, color)
        desc3 = construir_desc3(modelo)
        desc4 = color
        desc5 = talle
        sinonimo = generar_sinonimo(modelo, color, talle)

        # codigo_barra = sinonimo convertido a numérico (QWERTY)
        codigo_barra = sinonimo_a_barras(sinonimo)

        # Calcular precios
        precio_costo = round(precio * (1 - DESC_PROVEEDOR / 100), 2)
        precio_1 = round(precio_costo * (1 + UTILIDAD_1 / 100), 2)
        precio_2 = round(precio_costo * (1 + UTILIDAD_2 / 100), 2)
        precio_3 = round(precio_costo * (1 + UTILIDAD_3 / 100), 2)
        precio_4 = round(precio_costo * (1 + UTILIDAD_4 / 100), 2)

        # INSERT
        cursor.execute("""
            INSERT INTO msgestion01art.dbo.articulo (
                codigo,
                descripcion_1, descripcion_3, descripcion_4, descripcion_5,
                codigo_sinonimo, codigo_barra,
                subrubro, marca, linea, rubro, grupo,
                proveedor,
                precio_fabrica, descuento, descuento_1, descuento_2,
                precio_costo, precio_sugerido,
                utilidad_1, utilidad_2, utilidad_3, utilidad_4,
                precio_1, precio_2, precio_3, precio_4,
                formula, moneda,
                stock,
                estado
            ) VALUES (?, ?, ?, ?, ?,  ?, ?, ?, ?, ?, ?, ?,  ?, ?, ?, ?,  ?, ?,  ?, ?, ?, ?,  ?, ?, ?, ?, ?, ?,  ?,  ?)
        """, [
            nuevo_codigo,
            desc1, desc3, desc4, desc5,
            sinonimo, codigo_barra,
            subrubro, MARCA, LINEA, rubro, int(grupo),
            PROVEEDOR,
            precio, DESC_PROVEEDOR, 0, 0,
            precio_costo, round(precio_costo, 2),
            UTILIDAD_1, UTILIDAD_2, UTILIDAD_3, UTILIDAD_4,
            precio_1, precio_2, precio_3, precio_4,
            FORMULA, 0,
            "S",
            "V"
        ])

        conn.commit()
        conn.close()

        return nuevo_codigo, True
    except Exception as e:
        print(f"  ❌ Error creando artículo {modelo} {color} T{talle}: {e}")
        return None, False


def fase1_procesar_articulos(dry_run=True):
    """
    Para cada (modelo, color, talle), busca o crea el artículo.
    Retorna dict: (modelo, color, talle) → codigo_articulo
    """
    modo = "DRY RUN" if dry_run else "EJECUCIÓN REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 1: BÚSQUEDA / ALTA ARTÍCULOS WAKE INV 26 — {modo}")
    print(f"{'='*70}")

    articulos_map = {}  # (modelo, color, talle) → codigo
    encontrados = 0
    creados = 0
    errores = 0

    for modelo, color, talles_list, pxT_list, ped_count, precio in TODOS_PEDIDOS:
        print(f"\n  {modelo} {color} {talles_list[0]}-{talles_list[-1]} @ ${precio:,}")

        for talle in talles_list:
            key = (modelo, color, talle)

            # Buscar o crear (pasar rango completo para clasificar rubro)
            codigo, es_nuevo = crear_articulo(modelo, color, talle, precio, talles_rango=talles_list, dry_run=dry_run)

            if codigo:
                articulos_map[key] = codigo
                if es_nuevo:
                    print(f"    T{talle}: CREADO código {codigo}")
                    creados += 1
                else:
                    print(f"    T{talle}: existe código {codigo}")
                    encontrados += 1
            else:
                print(f"    T{talle}: ❌ ERROR")
                errores += 1

    print(f"\n  Resumen Fase 1:")
    print(f"    Encontrados: {encontrados}")
    print(f"    Creados: {creados}")
    print(f"    Errores: {errores}")
    print(f"    Total: {encontrados + creados + errores}")

    return articulos_map


# ══════════════════════════════════════════════════════════════
# FASE 2: INSERTAR NOTA DE PEDIDO
# ══════════════════════════════════════════════════════════════

def fase2_insertar_pedido(articulos_map, dry_run=True):
    """Inserta la nota de pedido con todos los renglones."""
    from paso4_insertar_pedido import insertar_pedido

    modo = "DRY RUN" if dry_run else "EJECUCIÓN REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 2: NOTA DE PEDIDO WAKE INV 26 — {modo}")
    print(f"{'='*70}")

    # Anti-duplicado
    if not dry_run:
        import pyodbc as _pyo
        try:
            _c = _pyo.connect(CONN_COMPRAS, timeout=10)
            _cur = _c.cursor()
            _cur.execute(
                "SELECT numero FROM MSGESTION03.dbo.pedico2 "
                "WHERE codigo=8 AND cuenta=594 AND observaciones LIKE '%WAKE Sport INV 2026%'"
            )
            _dup = _cur.fetchone()
            _c.close()
            if _dup:
                print(f"  ⚠️  YA EXISTE pedido WAKE INV 2026 → #{_dup[0]}")
                print(f"  → SALTANDO para evitar duplicado")
                return _dup[0]
        except Exception as e:
            print(f"  ⚠️  Error verificando duplicado: {e}")

    cabecera = {
        "empresa":           EMPRESA,
        "cuenta":            PROVEEDOR,
        "denominacion":      DENOMINACION,
        "fecha_comprobante": FECHA_PEDIDO,
        "fecha_entrega":     FECHA_ENTREGA,
        "observaciones":     OBSERVACIONES,
    }

    renglones = []
    total_pares = 0

    for modelo, color, talles_list, pxT_list, ped_count, precio in TODOS_PEDIDOS:
        for talle, pares_talle in zip(talles_list, pxT_list):
            key = (modelo, color, talle)
            codigo = articulos_map.get(key)

            if not codigo:
                print(f"  ⚠️  Sin código para {modelo} {color} T{talle} — saltando")
                continue

            # Cantidad = pedido_count × pares_por_talle
            cantidad = ped_count * pares_talle

            desc = construir_desc1(modelo, color)

            renglones.append({
                "articulo":        codigo if codigo > 0 else 0,
                "descripcion":     desc[:60],
                "codigo_sinonimo": "",
                "cantidad":        cantidad,
                "precio":          precio,
            })

            total_pares += cantidad

    total_bruto = sum(r["cantidad"] * r["precio"] for r in renglones)

    print(f"  Renglones: {len(renglones)}")
    print(f"  Total pares: {total_pares}")
    print(f"  Total bruto: ${total_bruto:,.0f}")

    if renglones:
        try:
            num = insertar_pedido(cabecera, renglones, dry_run=dry_run)
            print(f"  → Pedido WAKE: número {num}")
            return num
        except Exception as e:
            print(f"  ❌ Error insertando pedido: {e}")
            return None
    else:
        print(f"  ⚠️  No hay renglones para insertar")
        return None


# ══════════════════════════════════════════════════════════════
# VERIFICACIÓN
# ══════════════════════════════════════════════════════════════

def verificar_totales():
    """Verifica que los totales del script coincidan con el pedido NP."""
    print(f"\n{'='*70}")
    print(f"  VERIFICACIÓN DE TOTALES")
    print(f"{'='*70}")

    total_pares = 0
    total_bruto = 0
    total_lineas = len(TODOS_PEDIDOS)

    por_categoria = {
        "FEMENINO": {"pares": 0, "bruto": 0},
        "MASCULINO": {"pares": 0, "bruto": 0},
        "KIDS": {"pares": 0, "bruto": 0},
    }

    for categoria, pedidos_cat in [
        ("FEMENINO", PEDIDOS_FEMENINO),
        ("MASCULINO", PEDIDOS_MASCULINO),
        ("KIDS", PEDIDOS_KIDS),
    ]:
        for modelo, color, talles_list, pxT_list, ped_count, precio in pedidos_cat:
            pares_modelo = sum(pxT_list) * ped_count
            bruto_modelo = pares_modelo * precio

            total_pares += pares_modelo
            total_bruto += bruto_modelo

            por_categoria[categoria]["pares"] += pares_modelo
            por_categoria[categoria]["bruto"] += bruto_modelo

    print(f"\n  Por categoría:")
    for cat in ["FEMENINO", "MASCULINO", "KIDS"]:
        d = por_categoria[cat]
        pares = d["pares"]
        bruto = d["bruto"]
        print(f"    {cat:12s}  {pares:>4d} pares  ${bruto:>12,.0f}")

    print(f"\n  Total líneas:    {total_lineas}")
    print(f"  Total pares:     {total_pares}")
    print(f"  Total bruto:     ${total_bruto:,.0f}")

    # Verificar contra objetivos
    PARES_ESPERADO = 1465  # aproximado del NP

    ok_pares = abs(total_pares - PARES_ESPERADO) < 50  # tolerancia ±50

    print(f"\n  Pares:  {total_pares} vs esperado ~{PARES_ESPERADO} → {'OK' if ok_pares else '⚠️  REVISAR'}")

    return True


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    dry_run = "--ejecutar" not in sys.argv

    if dry_run:
        print("=" * 70)
        print("  MODO DRY-RUN — No se escribe nada en la BD")
        print("  Agregar --ejecutar para escribir de verdad")
        print("=" * 70)
    else:
        print("=" * 70)
        print("  ⚠️  MODO EJECUCIÓN REAL — SE VA A ESCRIBIR EN LA BD")
        print("=" * 70)

    # Verificar totales primero
    verificar_totales()

    # Fase 1: Búsqueda / alta de artículos
    articulos_map = fase1_procesar_articulos(dry_run=dry_run)

    # Fase 2: Nota de pedido
    if articulos_map:
        fase2_insertar_pedido(articulos_map, dry_run=dry_run)
    else:
        print("\n  ❌ No se procesaron artículos — no se puede crear pedido")

    print(f"\n{'='*70}")
    print(f"  {'DRY-RUN completado' if dry_run else 'EJECUCIÓN completada'}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
