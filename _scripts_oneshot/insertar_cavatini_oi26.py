#!/usr/bin/env python3
"""
insertar_cavatini_oi26.py — Alta artículos faltantes + Nota de pedido CAVATINI OI26
====================================================================================
Proveedor: 960 (TECAL Cavatini)
Marca: 1260
Empresa: H4 -> pedido en MSGESTION01.dbo.pedico2/pedico1
Artículos en msgestion01art.dbo.articulo

Secciones:
  HOMBRE:    8 líneas (BORJ, ANGLO, BLAS, ZEN, BASTIAN, BRIAN, PIERO)
  MUJER:    18 líneas (UME, BRENDI, BRUNA, TAMY, ANNET, HENDY, CARMELA, CLORIS, CATY)
  DAMAS XL:  4 líneas (TEXAS, SEATTLE, NASHVILLE, BOSTON)

Protocolo de sinónimo: 12 dígitos = PPP(960) + MMMMM(modelo) + CC(color) + TT(talle)

EJECUTAR EN EL 111:
  py -3 insertar_cavatini_oi26.py               <- dry-run (default)
  py -3 insertar_cavatini_oi26.py --ejecutar     <- escribe en producción
"""

import sys
import os
import pyodbc
import socket
from datetime import date, datetime

# ══════════════════════════════════════════════════════════════════════════════
# CONEXIÓN — auto-detect server vs Mac
# ══════════════════════════════════════════════════════════════════════════════

_hostname = socket.gethostname().upper()
if _hostname in ("DELL-SVR", "DELLSVR"):
    _DRIVER = "SQL Server"
    _SERVIDOR = "localhost"
    _EXTRAS = ""
else:
    _DRIVER = "SQL Server"
    _SERVIDOR = "192.168.2.111"
    _EXTRAS = ""

def get_conn(base):
    return (
        f"DRIVER={{{_DRIVER}}};"
        f"SERVER={_SERVIDOR};"
        f"DATABASE={base};"
        f"UID=am;PWD=dl;"
        f"{_EXTRAS}"
    )

CONN_ART = get_conn("msgestion01art")
CONN_PEDIDOS = get_conn("msgestion01")

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES DE NEGOCIO
# ══════════════════════════════════════════════════════════════════════════════

PROVEEDOR     = 960
DENOMINACION  = "TECAL Cavatini"
MARCA         = 1260
EMPRESA       = "H4"
LINEA         = 2          # Invierno
GRUPO         = "1"        # Cuero (matching existing Cavatini articles)

FECHA_PEDIDO  = "2026-03-20"
FECHA_ENTREGA = "2026-07-01"

OBSERVACIONES = (
    "CAVATINI OI26. TECAL prov 960. "
    "Hombre + Mujer + Damas XL. Invierno 2026. "
    "26 modelos, ~231 pares."
)

CODIGO_PEDIDO   = 8
LETRA_PEDIDO    = "X"
SUCURSAL_PEDIDO = 1

# ── Utilidades y fórmula (copiar de artículos existentes Cavatini) ──
FORMULA    = 1
UTILIDAD_1 = 100   # contado
UTILIDAD_2 = 120   # lista
UTILIDAD_3 = 60    # intermedio
UTILIDAD_4 = 45    # mayorista

# ══════════════════════════════════════════════════════════════════════════════
# MAPEO DE COLORES — confirmado del catálogo
# ══════════════════════════════════════════════════════════════════════════════

COLOR_MAP = {
    "001": ("NEGRO",      "00"),
    "014": ("NATURAL",    "15"),
    "019": ("CHOCOLATE",  "11"),
    "030": ("CASTAGNO",   "11"),  # misma familia marrón
    "034": ("HABANO",     "51"),  # brush off
    "048": ("VISON",      "22"),
    "059": ("LATTE",      "29"),
    "074": ("BRONCE",     "29"),
    "117": ("ANTILOPE",   "22"),  # misma familia visón
    "179": ("ORO CLARO",  "29"),
    "288": ("NUDE",       "25"),
}

# ══════════════════════════════════════════════════════════════════════════════
# SUBRUBRO POR TIPO (del Excel)
# ══════════════════════════════════════════════════════════════════════════════

# Mapeo modelo → tipo (del Excel, hardcodeado)
MODELO_TIPO = {
    # HOMBRE
    "BORJ":      ("ZAPAT SC",    21),  # zapato vestir/clásico
    "ANGLO":     ("ZAPAT V",     21),
    "BLAS":      ("ZAPAT B",     21),
    "ZEN":       ("CASUAL SC",   20),  # casual
    "BASTIAN":   ("CASUAL B",    20),
    "BRIAN":     ("CASUAL",      20),
    "PIERO":     ("MOCA",         7),  # mocasín
    # MUJER
    "UME":       ("ZAPA N",      55),  # zapatilla
    "BRENDI":    ("ZAPA NTRAL",  55),
    "BRUNA":     ("ZAPA ORO",    55),
    "TAMY":      ("ZAPA N",      55),
    "ANNET":     ("PANCHA B",    35),  # pancha
    "HENDY":     ("BOTA",        15),  # bota
    "CARMELA":   ("ZAPAT SC",    21),
    "CLORIS":    ("BOTA",        15),
    "CATY":      ("CASUAL SC",   20),
    # DAMAS XL
    "TEXAS":     ("BOTA",        15),
    "SEATTLE":   ("BOTA",        15),
    "NASHVILLE": ("BOTA",        15),
    "BOSTON":     ("CASUAL",      20),
}

# Modelo → codigo_objeto_costo (6 dígitos del catálogo)
MODELO_COD_OBJ = {
    "BORJ":      "705212",
    "ANGLO":     "703871",
    "BLAS":      "703980",
    "ZEN":       "703873",
    "BASTIAN":   "866152",
    "BRIAN":     "866151",
    "PIERO":     "703574",
    "UME":       "392502",
    "BRENDI":    "391314",
    "BRUNA":     "392510",
    "TAMY":      "392501",
    "ANNET":     "823211",
    "HENDY":     "412655",
    "CARMELA":   "423190",
    "CLORIS":    "524353",
    "CATY":      "504101",
    # DAMAS XL — se buscarán por nombre en BD, no se conoce código a priori
}

# ══════════════════════════════════════════════════════════════════════════════
# DATOS DEL PEDIDO — HARDCODEADOS DEL EXCEL
# ══════════════════════════════════════════════════════════════════════════════
# Formato: (modelo, codigo_objeto_costo, color_code, {talle: cantidad}, precio)

PEDIDO_HOMBRE = [
    ("BORJ",    "705212", "001", {"40":1,"41":2,"42":2,"43":2,"44":2,"45":1}, 76818),
    ("ANGLO",   "703871", "001", {"40":1,"41":1,"42":2,"43":2,"44":2,"45":1,"46":1}, 79545),
    ("ANGLO",   "703871", "019", {"41":2,"42":2,"44":1,"45":1,"46":1}, 79545),
    ("BLAS",    "703980", "001", {"42":2,"43":2,"44":2}, 70455),
    ("ZEN",     "703873", "001", {"41":2,"42":2,"43":2}, 79545),
    ("BASTIAN", "866152", "034", {"41":2,"42":2,"43":2,"44":2}, 79549),
    ("BRIAN",   "866151", "001", {"41":2,"42":2,"43":2,"44":2}, 79545),
    ("PIERO",   "703574", "001", {"40":1,"41":2,"42":2,"43":2,"44":2,"45":1}, 81364),
]

PEDIDO_MUJER = [
    ("UME",     "392502", "001", {"37":1,"38":2,"39":2,"40":2,"41":1}, 75000),
    ("UME",     "392502", "059", {"37":1,"38":2,"39":2,"40":2,"41":1}, 75000),
    ("BRENDI",  "391314", "001", {"37":1,"38":2,"39":2,"40":2,"41":1}, 70455),
    ("BRENDI",  "391314", "014", {"37":1,"38":2,"39":2,"40":2,"41":1}, 70455),
    ("BRUNA",   "392510", "001", {"37":1,"38":2,"39":2,"40":2,"41":1}, 75000),
    ("BRUNA",   "392510", "179", {"37":1,"38":2,"39":2,"40":2,"41":1}, 75000),
    ("TAMY",    "392501", "001", {"37":1,"38":2,"39":2,"40":2,"41":1}, 75000),
    ("TAMY",    "392501", "074", {"37":1,"38":2,"39":2,"40":2,"41":1}, 75000),
    ("ANNET",   "823211", "001", {"36":1,"37":2,"38":2,"39":2,"40":1}, 56818),
    ("ANNET",   "823211", "288", {"36":1,"37":2,"38":2,"39":2,"40":1}, 56818),
    ("HENDY",   "412655", "001", {"37":1,"38":2,"39":2,"40":2,"41":1}, 79545),
    ("HENDY",   "412655", "117", {"37":1,"38":2,"39":2,"40":2,"41":1}, 79545),
    ("CARMELA", "423190", "001", {"38":2,"39":2,"40":2}, 88636),
    ("CARMELA", "423190", "030", {"38":2,"39":2,"40":2}, 88636),
    ("CLORIS",  "524353", "001", {"37":1,"38":2,"39":2,"40":2,"41":1}, 85909),
    ("CLORIS",  "524353", "117", {"37":1,"38":2,"39":2,"40":2,"41":1}, 85909),
    ("CATY",    "504101", "001", {"37":1,"38":2,"39":2,"40":2,"41":1}, 79545),
    ("CATY",    "504101", "048", {"37":1,"38":2,"39":2,"40":2,"41":1}, 79545),
]

PEDIDO_DAMAS_XL = [
    # (modelo, color_texto, {talle: cantidad}, precio)
    # No tienen codigo_objeto_costo conocido a priori; se buscan por nombre en BD
    ("TEXAS",     "NEGRO", {"40":2,"41":2,"42":2}, 68200),
    ("SEATTLE",   "NEGRO", {"40":2,"41":2,"42":2,"43":2}, 79200),
    ("NASHVILLE", "NEGRO", {"40":2,"41":2,"42":2}, 82500),
    ("BOSTON",     "NEGRO", {"40":2,"41":2,"42":2}, 73700),
]


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def construir_sinonimo(cod_obj, color_code, talle):
    """
    Sinónimo de 12 dígitos: PPP + MMMMM + CC + TT
    PPP = 960 (proveedor)
    MMMMM = código objeto costo (5 dígitos, se toman los últimos 5 si tiene 6)
    CC = color code de COLOR_MAP
    TT = talle (2 dígitos)
    """
    # Tomar los últimos 5 dígitos del código objeto costo
    modelo_str = cod_obj[-5:].zfill(5) if cod_obj else "00000"

    # Color code (2 dígitos)
    if color_code in COLOR_MAP:
        cc = COLOR_MAP[color_code][1]
    else:
        cc = "00"

    tt = str(int(talle)).zfill(2)

    return f"960{modelo_str}{cc}{tt}"


def construir_desc1(modelo, color_name, tipo_str):
    """
    desc1: "CC-CCCC NOMBRE COLOR TIPO"
    Ejemplo: "70-5212 BORJ NEGRO ZAPATO ACORD CONFORT"
    Max 60 chars.
    """
    cod_obj = MODELO_COD_OBJ.get(modelo, "")
    if cod_obj and len(cod_obj) >= 4:
        # Formato NN-NNNN
        prefix = f"{cod_obj[:2]}-{cod_obj[2:]}"
    else:
        prefix = modelo

    desc = f"{prefix} {modelo} {color_name} {tipo_str}"
    return desc[:60].strip()


def construir_desc3(modelo, tipo_str):
    """desc3: nombre corto para etiqueta, max 26 chars."""
    return f"{modelo} {tipo_str}"[:26].strip()


def get_rubro(modelo, talles):
    """Determina rubro según tipo de producto y talles."""
    min_t = min(int(t) for t in talles)
    max_t = max(int(t) for t in talles)

    # Damas XL (talles 40-43 mujer) → rubro 1
    if modelo in ("TEXAS", "SEATTLE", "NASHVILLE", "BOSTON"):
        return 1

    # Hombre: talles >= 40
    if min_t >= 40:
        return 3
    # Mujer: talles <= 41
    return 1


def get_subrubro(modelo):
    """Subrubro desde MODELO_TIPO."""
    info = MODELO_TIPO.get(modelo)
    if info:
        return info[1]
    return 20  # default: casual


# ══════════════════════════════════════════════════════════════════════════════
# FASE 0: CARGAR ARTÍCULOS EXISTENTES
# ══════════════════════════════════════════════════════════════════════════════

def cargar_articulos_cavatini():
    """
    Carga todos los artículos con proveedor=960 de msgestion01art.dbo.articulo.
    Retorna dict: (codigo_objeto_costo_upper, color_upper, talle_upper) → codigo
    y lista raw para búsqueda fuzzy.
    """
    print("\n  Consultando articulos Cavatini (proveedor 960) en BD...")
    conn = pyodbc.connect(CONN_ART, timeout=15)
    cur = conn.cursor()
    cur.execute("""
        SELECT codigo,
               ISNULL(RTRIM(codigo_objeto_costo), ''),
               ISNULL(RTRIM(descripcion_1), ''),
               ISNULL(RTRIM(descripcion_4), ''),
               ISNULL(RTRIM(descripcion_5), '')
        FROM   articulo
        WHERE  proveedor = 960
    """)
    rows = cur.fetchall()
    conn.close()

    arts = {}
    arts_raw = []
    for codigo, cod_obj, desc1, color, talle in rows:
        key = (cod_obj.strip().upper(), color.strip().upper(), talle.strip())
        arts[key] = codigo
        arts_raw.append({
            "codigo": codigo,
            "cod_obj": cod_obj.strip().upper(),
            "desc1": desc1.strip().upper(),
            "color": color.strip().upper(),
            "talle": talle.strip(),
        })

    print(f"  -> {len(arts)} articulos Cavatini en BD")
    return arts, arts_raw


def buscar_articulo(arts_dict, arts_raw, modelo, cod_obj, color_code, talle):
    """
    Intenta encontrar artículo existente.
    1. Buscar por (cod_obj, color_name, talle) exacto
    2. Para Damas XL, buscar por desc1 LIKE '%MODELO%' + color + talle
    Retorna codigo o None.
    """
    color_name = COLOR_MAP.get(color_code, (color_code, "00"))[0].upper()
    talle_str = str(talle)

    # 1. Exacto por (cod_obj, color, talle)
    key = (cod_obj.upper(), color_name, talle_str)
    if key in arts_dict:
        return arts_dict[key]

    # 2. Fuzzy: buscar por cod_obj + talle, cualquier color que matchee
    candidatos = [a for a in arts_raw
                  if a["cod_obj"] == cod_obj.upper() and a["talle"] == talle_str]

    # Buscar por color parcial
    for a in candidatos:
        if color_name in a["color"] or a["color"] in color_name:
            return a["codigo"]

    # 3. Para NEGRO (001), también probar sin filtro de color si hay un solo candidato negro
    if color_code == "001":
        negros = [a for a in candidatos if "NEGRO" in a["color"] or "NEGR" in a["color"]]
        if len(negros) == 1:
            return negros[0]["codigo"]

    return None


def buscar_damas_xl(arts_raw, modelo, color_texto, talle):
    """
    Busca artículo de DAMAS XL por descripcion_1 LIKE '%MODELO%' con proveedor=960.
    """
    modelo_up = modelo.upper()
    color_up = color_texto.upper()
    talle_str = str(talle)

    for a in arts_raw:
        if modelo_up in a["desc1"] and a["talle"] == talle_str:
            if color_up in a["color"] or color_up in a["desc1"]:
                return a["codigo"]

    # Si solo hay un match por modelo+talle, tomar ese
    cands = [a for a in arts_raw
             if modelo_up in a["desc1"] and a["talle"] == talle_str]
    if len(cands) == 1:
        return cands[0]["codigo"]

    return None


# ══════════════════════════════════════════════════════════════════════════════
# FASE 1: BUSCAR / CREAR ARTÍCULOS
# ══════════════════════════════════════════════════════════════════════════════

def crear_articulo(cursor, modelo, cod_obj, color_code, talle, precio, next_codigo):
    """
    Inserta un artículo nuevo en msgestion01art.dbo.articulo.
    Retorna el código asignado.
    """
    color_name = COLOR_MAP.get(color_code, (color_code, "00"))[0]
    tipo_info = MODELO_TIPO.get(modelo, ("", 20))
    tipo_str = tipo_info[0]
    subrubro = tipo_info[1]
    rubro = get_rubro(modelo, [talle])

    desc1 = construir_desc1(modelo, color_name, tipo_str)
    desc3 = construir_desc3(modelo, tipo_str)
    desc4 = color_name
    desc5 = str(talle)
    sinonimo = construir_sinonimo(cod_obj, color_code, talle)
    codigo_barra = sinonimo  # mismo para Cavatini

    # Precios
    precio_costo = round(precio, 2)   # sin descuento especial en Cavatini
    precio_1 = round(precio_costo * (1 + UTILIDAD_1 / 100), 2)
    precio_2 = round(precio_costo * (1 + UTILIDAD_2 / 100), 2)
    precio_3 = round(precio_costo * (1 + UTILIDAD_3 / 100), 2)
    precio_4 = round(precio_costo * (1 + UTILIDAD_4 / 100), 2)

    cursor.execute("""
        INSERT INTO msgestion01art.dbo.articulo (
            codigo, codigo_sinonimo, codigo_barra,
            descripcion_1, descripcion_3, descripcion_4, descripcion_5,
            codigo_objeto_costo,
            proveedor, marca, rubro, subrubro, grupo, linea,
            precio_fabrica, descuento, descuento_1, descuento_2,
            precio_costo, precio_sugerido,
            utilidad_1, utilidad_2, utilidad_3, utilidad_4,
            precio_1, precio_2, precio_3, precio_4,
            formula, moneda,
            alicuota_iva1, alicuota_iva2, tipo_iva,
            calificacion,
            cuenta_compras, cuenta_ventas, cuenta_com_anti,
            tipo_codigo_barra, numero_maximo, stock, factura_por_total,
            estado, usuario, abm
        ) VALUES (
            ?, ?, ?,
            ?, ?, ?, ?,
            ?,
            ?, ?, ?, ?, ?, ?,
            ?, 0, 0, 0,
            ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, 0,
            21, 10.5, 'G',
            'G',
            '1010601', '4010100', '1010601',
            'C', 'S', 'S', 'N',
            'V', 'COWORK', 'A'
        )
    """, (
        next_codigo, sinonimo, codigo_barra,
        desc1, desc3, desc4, desc5,
        cod_obj,
        PROVEEDOR, MARCA, rubro, subrubro, int(GRUPO), LINEA,
        precio,
        precio_costo, precio_costo,
        UTILIDAD_1, UTILIDAD_2, UTILIDAD_3, UTILIDAD_4,
        precio_1, precio_2, precio_3, precio_4,
        FORMULA,
    ))

    return next_codigo


def fase1_articulos(dry_run=True):
    """
    Para cada línea del pedido, busca el artículo existente o lo marca para crear.
    Retorna: (renglones, articulos_a_crear, stats)
      renglones: lista de dicts con toda la info para insertar en pedico1
      articulos_a_crear: lista de (modelo, cod_obj, color_code, talle, precio)
    """
    modo = "DRY RUN" if dry_run else "EJECUCION REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 1: BUSQUEDA / ALTA ARTICULOS CAVATINI OI26 -- {modo}")
    print(f"{'='*70}")

    # Cargar existentes
    arts_dict, arts_raw = cargar_articulos_cavatini()

    renglones = []
    articulos_a_crear = []
    encontrados = 0
    faltantes = 0

    def procesar_hombre_mujer(pedido_list, seccion):
        nonlocal encontrados, faltantes
        print(f"\n  --- {seccion} ---")
        for modelo, cod_obj, color_code, curva, precio in pedido_list:
            color_name = COLOR_MAP.get(color_code, (color_code, "00"))[0]
            for talle, cant in sorted(curva.items(), key=lambda x: int(x[0])):
                if cant == 0:
                    continue
                codigo = buscar_articulo(arts_dict, arts_raw, modelo, cod_obj, color_code, talle)
                if codigo:
                    encontrados += 1
                    print(f"    OK  art={int(codigo):6d}  {modelo:<12} {color_name:<15} T{talle}  x{cant}")
                    renglones.append({
                        "articulo": int(codigo),
                        "descripcion": f"{modelo} {color_name} T{talle}"[:60],
                        "codigo_sinonimo": construir_sinonimo(cod_obj, color_code, talle),
                        "cantidad": cant,
                        "precio": float(precio),
                    })
                else:
                    faltantes += 1
                    print(f"    NEW {modelo:<12} {color_name:<15} T{talle}  x{cant}  -> CREAR")
                    articulos_a_crear.append((modelo, cod_obj, color_code, talle, precio, cant))

    procesar_hombre_mujer(PEDIDO_HOMBRE, "HOMBRE")
    procesar_hombre_mujer(PEDIDO_MUJER, "MUJER")

    # Damas XL — búsqueda por nombre
    print(f"\n  --- DAMAS XL ---")
    for modelo, color_texto, curva, precio in PEDIDO_DAMAS_XL:
        for talle, cant in sorted(curva.items(), key=lambda x: int(x[0])):
            if cant == 0:
                continue
            codigo = buscar_damas_xl(arts_raw, modelo, color_texto, talle)
            if codigo:
                encontrados += 1
                print(f"    OK  art={int(codigo):6d}  {modelo:<12} {color_texto:<15} T{talle}  x{cant}")
                # Para Damas XL, sinónimo con color code "001" (NEGRO)
                cod_obj = MODELO_COD_OBJ.get(modelo, "000000")
                renglones.append({
                    "articulo": int(codigo),
                    "descripcion": f"{modelo} {color_texto} T{talle} XL"[:60],
                    "codigo_sinonimo": construir_sinonimo(cod_obj, "001", talle) if cod_obj != "000000" else "",
                    "cantidad": cant,
                    "precio": float(precio),
                })
            else:
                faltantes += 1
                # Intentar buscar cod_obj en BD por nombre
                cod_obj = MODELO_COD_OBJ.get(modelo, "")
                if not cod_obj:
                    # Buscar en arts_raw por nombre
                    for a in arts_raw:
                        if modelo.upper() in a["desc1"]:
                            cod_obj = a["cod_obj"]
                            MODELO_COD_OBJ[modelo] = cod_obj
                            break

                print(f"    NEW {modelo:<12} {color_texto:<15} T{talle}  x{cant}  -> CREAR (cod_obj={cod_obj or '???'})")
                articulos_a_crear.append((modelo, cod_obj or "000000", "001", talle, precio, cant))

    print(f"\n  Resumen Fase 1:")
    print(f"    Encontrados en BD: {encontrados}")
    print(f"    A crear:           {faltantes}")
    print(f"    Total renglones:   {encontrados} (existentes) + {faltantes} (nuevos) = {encontrados + faltantes}")

    return renglones, articulos_a_crear


# ══════════════════════════════════════════════════════════════════════════════
# FASE 2: CREAR ARTÍCULOS FALTANTES
# ══════════════════════════════════════════════════════════════════════════════

def fase2_crear_articulos(articulos_a_crear, dry_run=True):
    """
    Crea los artículos faltantes y retorna lista de renglones adicionales.
    """
    if not articulos_a_crear:
        print(f"\n  No hay articulos para crear.")
        return []

    modo = "DRY RUN" if dry_run else "EJECUCION REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 2: ALTA DE {len(articulos_a_crear)} ARTICULOS FALTANTES -- {modo}")
    print(f"{'='*70}")

    renglones_nuevos = []

    if dry_run:
        for modelo, cod_obj, color_code, talle, precio, cant in articulos_a_crear:
            color_name = COLOR_MAP.get(color_code, (color_code, "00"))[0]
            sinonimo = construir_sinonimo(cod_obj, color_code, talle)
            desc1 = construir_desc1(modelo, color_name, MODELO_TIPO.get(modelo, ("", 20))[0])
            print(f"    [DRY] {modelo:<12} {color_name:<15} T{talle}  sinonimo={sinonimo}  desc1={desc1}")
            # Placeholder: usar codigo negativo en dry-run
            renglones_nuevos.append({
                "articulo": -(abs(hash((modelo, color_code, talle))) % 900000 + 100000),
                "descripcion": f"{modelo} {color_name} T{talle}"[:60],
                "codigo_sinonimo": sinonimo,
                "cantidad": cant,
                "precio": float(precio),
            })
        print(f"\n  [DRY RUN] Se crearian {len(articulos_a_crear)} articulos. No se escribio nada.")
        return renglones_nuevos

    # EJECUCIÓN REAL: crear artículos en transacción
    conn = pyodbc.connect(CONN_ART, timeout=15)
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        # Obtener MAX(codigo) + 1
        cursor.execute("SELECT ISNULL(MAX(codigo), 0) + 1 FROM msgestion01art.dbo.articulo")
        next_codigo = cursor.fetchone()[0]
        print(f"    Proximo codigo disponible: {next_codigo}")

        creados = 0
        for modelo, cod_obj, color_code, talle, precio, cant in articulos_a_crear:
            color_name = COLOR_MAP.get(color_code, (color_code, "00"))[0]
            codigo = crear_articulo(cursor, modelo, cod_obj, color_code, talle, precio, next_codigo)
            print(f"    CREADO art={codigo}  {modelo} {color_name} T{talle}")

            renglones_nuevos.append({
                "articulo": int(codigo),
                "descripcion": f"{modelo} {color_name} T{talle}"[:60],
                "codigo_sinonimo": construir_sinonimo(cod_obj, color_code, talle),
                "cantidad": cant,
                "precio": float(precio),
            })

            next_codigo += 1
            creados += 1

        conn.commit()
        print(f"\n  OK: {creados} articulos creados (codigos {next_codigo - creados} a {next_codigo - 1})")

    except Exception as e:
        conn.rollback()
        print(f"\n  ERROR creando articulos: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        conn.close()

    return renglones_nuevos


# ══════════════════════════════════════════════════════════════════════════════
# FASE 3: INSERTAR NOTA DE PEDIDO
# ══════════════════════════════════════════════════════════════════════════════

def fase3_insertar_pedido(renglones, dry_run=True):
    """
    Inserta la nota de pedido en MSGESTION01.dbo.pedico2 + pedico1.
    """
    modo = "DRY RUN" if dry_run else "EJECUCION REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 3: NOTA DE PEDIDO CAVATINI OI26 -- {modo}")
    print(f"{'='*70}")

    if not renglones:
        print("  ERROR: No hay renglones para insertar.")
        return None

    total_pares = sum(r["cantidad"] for r in renglones)
    total_bruto = sum(r["cantidad"] * r["precio"] for r in renglones)

    print(f"    Renglones:   {len(renglones)}")
    print(f"    Total pares: {total_pares}")
    print(f"    Total bruto: ${total_bruto:,.0f}")

    tabla_p2 = "MSGESTION01.dbo.pedico2"
    tabla_p1 = "MSGESTION01.dbo.pedico1"

    if dry_run:
        print(f"\n  [DRY RUN] Cabecera -> {tabla_p2}")
        print(f"    empresa    = {EMPRESA}")
        print(f"    cuenta     = {PROVEEDOR} ({DENOMINACION})")
        print(f"    fecha      = {FECHA_PEDIDO}")
        print(f"    entrega    = {FECHA_ENTREGA}")
        print(f"    obs        = {OBSERVACIONES}")
        print(f"\n  [DRY RUN] {len(renglones)} renglones en {tabla_p1}")
        for i, r in enumerate(renglones, 1):
            print(f"    [{i:3d}] art={r['articulo']:>8}  {r['descripcion']:<40}  x{r['cantidad']}  ${r['precio']:,.0f}")
        print(f"\n  [DRY RUN] No se escribio nada.")
        return 999999

    # ── Anti-duplicado ──
    conn_check = pyodbc.connect(CONN_PEDIDOS, timeout=15)
    cur_check = conn_check.cursor()
    cur_check.execute(
        f"SELECT numero FROM {tabla_p2} "
        "WHERE codigo=8 AND cuenta=960 AND observaciones LIKE '%CAVATINI OI26%'"
    )
    dup = cur_check.fetchone()
    conn_check.close()
    if dup:
        print(f"  WARN: YA EXISTE pedido CAVATINI OI26 -> #{dup[0]}. Saltando.")
        return dup[0]

    # ── INSERT ──
    sql_cab = f"""
        INSERT INTO {tabla_p2} (
            codigo, letra, sucursal,
            numero, orden, deposito,
            cuenta, denominacion,
            fecha_comprobante, fecha_proceso,
            observaciones,
            descuento_general, monto_descuento,
            bonificacion_general, monto_bonificacion,
            financiacion_general, monto_financiacion,
            iva1, monto_iva1, iva2, monto_iva2, monto_impuesto,
            importe_neto, monto_exento,
            estado, zona, condicion_iva, numero_cuit, copias,
            cuenta_y_orden, pack, reintegro, cambio, transferencia,
            entregador, usuario, campo, sistema_cc, moneda, sector,
            forma_pago, plan_canje, tipo_vcto_pago, tipo_operacion, tipo_ajuste,
            medio_pago, cuenta_cc, concurso
        ) VALUES (
            ?, ?, ?,
            ?, ?, 0,
            ?, ?,
            ?, GETDATE(),
            ?,
            0, 0, 0, 0, 0, 0,
            21, 0, 10.5, 0, 0,
            0, 0,
            'V', 1, 'I', '30703468515', 1,
            'N', 'N', 'N', 'N', 'N',
            0, 'COWORK', 0, 2, 0, 0,
            0, 'N', 0, 0, 0,
            ' ', ?, 'N'
        )
    """

    sql_det = f"""
        INSERT INTO {tabla_p1} (
            codigo, letra, sucursal,
            numero, orden, renglon,
            articulo, descripcion, codigo_sinonimo,
            cantidad, precio,
            cuenta, fecha, fecha_entrega,
            estado
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'V')
    """

    conn = pyodbc.connect(CONN_PEDIDOS, timeout=15)
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        # Próximo número
        cursor.execute(
            f"SELECT ISNULL(MAX(numero), 0) + 1 FROM {tabla_p2} WHERE codigo = ?",
            CODIGO_PEDIDO
        )
        numero = cursor.fetchone()[0]

        # Próxima orden
        cursor.execute(
            f"SELECT ISNULL(MAX(orden), 0) + 1 FROM {tabla_p2} WHERE codigo = ?",
            CODIGO_PEDIDO
        )
        orden = cursor.fetchone()[0]
        if orden > 99:
            orden = 1

        print(f"    Numero pedido: {numero}, Orden: {orden}")

        # Cabecera
        cursor.execute(sql_cab, (
            CODIGO_PEDIDO, LETRA_PEDIDO, SUCURSAL_PEDIDO,
            numero, orden,
            PROVEEDOR, DENOMINACION,
            FECHA_PEDIDO,
            OBSERVACIONES,
            PROVEEDOR,
        ))

        # Detalle
        for i, r in enumerate(renglones, 1):
            cursor.execute(sql_det, (
                CODIGO_PEDIDO, LETRA_PEDIDO, SUCURSAL_PEDIDO,
                numero, orden, i,
                r["articulo"],
                r["descripcion"],
                r.get("codigo_sinonimo", ""),
                r["cantidad"],
                r["precio"],
                PROVEEDOR,
                FECHA_PEDIDO,
                FECHA_ENTREGA,
            ))

        conn.commit()
        print(f"\n  OK Pedido CAVATINI OI26 insertado.")
        print(f"    Numero={numero}, Orden={orden}")
        print(f"    Renglones={len(renglones)}, Pares={total_pares}")
        print(f"    Total bruto=${total_bruto:,.0f}")
        print(f"\n  Verificar en SSMS:")
        print(f"    SELECT * FROM {tabla_p2} WHERE numero = {numero} AND codigo = 8")
        print(f"    SELECT * FROM {tabla_p1} WHERE numero = {numero} AND codigo = 8")
        return numero

    except Exception as e:
        conn.rollback()
        print(f"\n  ERROR insertando pedido: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# VERIFICACIÓN DE TOTALES
# ══════════════════════════════════════════════════════════════════════════════

def verificar_totales():
    """Calcula y muestra totales del pedido."""
    print(f"\n{'='*70}")
    print(f"  VERIFICACION DE TOTALES")
    print(f"{'='*70}")

    stats = {"HOMBRE": {"pares": 0, "bruto": 0, "lineas": 0},
             "MUJER":  {"pares": 0, "bruto": 0, "lineas": 0},
             "DAMAS XL": {"pares": 0, "bruto": 0, "lineas": 0}}

    for modelo, cod_obj, color_code, curva, precio in PEDIDO_HOMBRE:
        pares = sum(curva.values())
        stats["HOMBRE"]["pares"] += pares
        stats["HOMBRE"]["bruto"] += pares * precio
        stats["HOMBRE"]["lineas"] += 1

    for modelo, cod_obj, color_code, curva, precio in PEDIDO_MUJER:
        pares = sum(curva.values())
        stats["MUJER"]["pares"] += pares
        stats["MUJER"]["bruto"] += pares * precio
        stats["MUJER"]["lineas"] += 1

    for modelo, color, curva, precio in PEDIDO_DAMAS_XL:
        pares = sum(curva.values())
        stats["DAMAS XL"]["pares"] += pares
        stats["DAMAS XL"]["bruto"] += pares * precio
        stats["DAMAS XL"]["lineas"] += 1

    total_pares = 0
    total_bruto = 0
    total_lineas = 0

    print(f"\n  {'Seccion':<12}  {'Lineas':>6}  {'Pares':>6}  {'Bruto':>14}")
    print(f"  {'-'*12}  {'-'*6}  {'-'*6}  {'-'*14}")
    for sec in ["HOMBRE", "MUJER", "DAMAS XL"]:
        d = stats[sec]
        print(f"  {sec:<12}  {d['lineas']:>6}  {d['pares']:>6}  ${d['bruto']:>12,.0f}")
        total_pares += d["pares"]
        total_bruto += d["bruto"]
        total_lineas += d["lineas"]

    print(f"  {'TOTAL':<12}  {total_lineas:>6}  {total_pares:>6}  ${total_bruto:>12,.0f}")

    # Contar renglones individuales (talle×color)
    reng_count = 0
    for _, _, _, curva, _ in PEDIDO_HOMBRE:
        reng_count += sum(1 for v in curva.values() if v > 0)
    for _, _, _, curva, _ in PEDIDO_MUJER:
        reng_count += sum(1 for v in curva.values() if v > 0)
    for _, _, curva, _ in PEDIDO_DAMAS_XL:
        reng_count += sum(1 for v in curva.values() if v > 0)

    print(f"\n  Renglones individuales (talle x color): {reng_count}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    dry_run = "--ejecutar" not in sys.argv

    if dry_run:
        print("=" * 70)
        print("  MODO DRY-RUN -- No se escribe nada en la BD")
        print("  Agregar --ejecutar para escribir de verdad")
        print("=" * 70)
    else:
        print("=" * 70)
        print("  MODO EJECUCION REAL -- SE VA A ESCRIBIR EN LA BD")
        print("=" * 70)
        resp = input("  Confirmar? (s/N): ").strip().lower()
        if resp != "s":
            print("  Cancelado.")
            sys.exit(0)

    print(f"\n  Servidor:    {_SERVIDOR}")
    print(f"  Proveedor:   {PROVEEDOR} ({DENOMINACION})")
    print(f"  Marca:       {MARCA}")
    print(f"  Empresa:     {EMPRESA}")
    print(f"  Fecha:       {FECHA_PEDIDO}")
    print(f"  Entrega:     {FECHA_ENTREGA}")

    # Verificar totales
    verificar_totales()

    # Fase 1: buscar artículos existentes
    renglones_existentes, articulos_a_crear = fase1_articulos(dry_run=dry_run)

    # Fase 2: crear artículos faltantes
    renglones_nuevos = fase2_crear_articulos(articulos_a_crear, dry_run=dry_run)

    # Combinar todos los renglones
    todos_renglones = renglones_existentes + renglones_nuevos

    # Fase 3: insertar pedido
    numero = fase3_insertar_pedido(todos_renglones, dry_run=dry_run)

    # Resumen final
    print(f"\n{'='*70}")
    total_pares = sum(r["cantidad"] for r in todos_renglones)
    total_bruto = sum(r["cantidad"] * r["precio"] for r in todos_renglones)
    print(f"  Resumen final:")
    print(f"    Articulos existentes:  {len(renglones_existentes)}")
    print(f"    Articulos creados:     {len(renglones_nuevos)}")
    print(f"    Total renglones:       {len(todos_renglones)}")
    print(f"    Total pares:           {total_pares}")
    print(f"    Total bruto:           ${total_bruto:,.0f}")
    if numero:
        print(f"    Pedido #:              {numero}")
    print(f"  {'DRY-RUN completado' if dry_run else 'EJECUCION completada'}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
