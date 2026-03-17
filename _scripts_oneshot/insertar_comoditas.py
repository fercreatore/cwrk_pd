#!/usr/bin/env python3
"""
insertar_comoditas.py — Pedido COMODITAS pantuflas Invierno 2026
Self-contained. 468 pares, 5 modelos, 11 colores.

PASO 1: Alta 16 artículos nuevos (1619 y 1246) en msgestion01art
PASO 2: Pedido de compra en MSGESTION01 (pedico2 + pedico1)

Proveedor activo: 776 (CIRENE SA, ex Comoditas SA — 1076 arts)
Empresa: H4

MODELOS EXISTENTES: 598, 1127, 239 (artículos ya en DB)
MODELOS NUEVOS: 1619, 1246 (requieren alta primero)

ANÁLISIS "CAMPEONES":
  1127 = #3 modelo Comoditas (261 pares en 3 años)
  598  = top seller (236 pares, oculto en grupo NULL)
  239  = sólido medio (100 pares)
  1619 = NUEVO sin historial
  1246 = NUEVO sin historial

EJECUTAR EN EL 111:
  py -3 insertar_comoditas.py --dry-run     <- solo muestra
  py -3 insertar_comoditas.py --ejecutar    <- escribe en produccion
"""

import sys
import pyodbc
import socket
from datetime import date, datetime

# -- AUTO-DETECT SERVER vs MAC -----------------------------------------
_hostname = socket.gethostname().upper()
if _hostname in ("DELL-SVR", "DELLSVR"):
    SERVIDOR = "localhost"
    DRIVER = "ODBC Driver 17 for SQL Server"
    EXTRAS = ""
else:
    SERVIDOR = "192.168.2.111"
    DRIVER = "ODBC Driver 18 for SQL Server"
    EXTRAS = "TrustServerCertificate=yes;Encrypt=no;"

def get_conn(base):
    return (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVIDOR};"
        f"DATABASE={base};"
        f"UID=am;PWD=dl;"
        f"{EXTRAS}"
    )

# -- CONSTANTES --------------------------------------------------------
PROVEEDOR = 776          # CIRENE SA (proveedor activo con 1076 arts)
DENOMINACION = "CIRENE SA"
MARCA = 776
BASE_PEDIDO = "MSGESTION01"
FECHA_COMPROBANTE = date(2026, 3, 14)
FECHA_ENTREGA = date(2026, 4, 30)  # ~6 semanas

# ======================================================================
# PARTE 1: ARTÍCULOS NUEVOS (1619 y 1246)
# Códigos desde 361273 (MAX actual: 361272)
# ======================================================================

NUEVOS_ARTICULOS = [
    # ── 1619 VERDE — PANTUFLA (individual, talles 37-41) ──
    # grupo "36" = mujer individual 36-41 (mismo que 1127)
    {"codigo": 361273, "desc1": "1619 VERDE PANTUFLA P/CERRADA", "desc3": "1619 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "37", "grupo": "36", "cod_sin": "776161902037", "cod_barra": 776161902037, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361274, "desc1": "1619 VERDE PANTUFLA P/CERRADA", "desc3": "1619 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "38", "grupo": "36", "cod_sin": "776161902038", "cod_barra": 776161902038, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361275, "desc1": "1619 VERDE PANTUFLA P/CERRADA", "desc3": "1619 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "39", "grupo": "36", "cod_sin": "776161902039", "cod_barra": 776161902039, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361276, "desc1": "1619 VERDE PANTUFLA P/CERRADA", "desc3": "1619 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "40", "grupo": "36", "cod_sin": "776161902040", "cod_barra": 776161902040, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361277, "desc1": "1619 VERDE PANTUFLA P/CERRADA", "desc3": "1619 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "41", "grupo": "36", "cod_sin": "776161902041", "cod_barra": 776161902041, "cod_obj": "16190", "precio_fab": 11422},

    # ── 1619 GRIS — PANTUFLA (individual, talles 37-41) ──
    {"codigo": 361278, "desc1": "1619 GRIS PANTUFLA P/CERRADA",  "desc3": "1619 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "37", "grupo": "36", "cod_sin": "776161901337", "cod_barra": 776161901337, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361279, "desc1": "1619 GRIS PANTUFLA P/CERRADA",  "desc3": "1619 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "38", "grupo": "36", "cod_sin": "776161901338", "cod_barra": 776161901338, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361280, "desc1": "1619 GRIS PANTUFLA P/CERRADA",  "desc3": "1619 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "39", "grupo": "36", "cod_sin": "776161901339", "cod_barra": 776161901339, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361281, "desc1": "1619 GRIS PANTUFLA P/CERRADA",  "desc3": "1619 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "40", "grupo": "36", "cod_sin": "776161901340", "cod_barra": 776161901340, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361282, "desc1": "1619 GRIS PANTUFLA P/CERRADA",  "desc3": "1619 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "41", "grupo": "36", "cod_sin": "776161901341", "cod_barra": 776161901341, "cod_obj": "16190", "precio_fab": 11422},

    # ── 1246 GRIS — PANTUFLA (binumeral, talles 36/38/40) ──
    # grupo "13" = mujer binumeral (mismo que 598)
    {"codigo": 361283, "desc1": "1246 GRIS PANTUFLA P/CERRADA",  "desc3": "1246 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "36", "grupo": "13", "cod_sin": "776124601336", "cod_barra": 776124601336, "cod_obj": "12460", "precio_fab": 13929},
    {"codigo": 361284, "desc1": "1246 GRIS PANTUFLA P/CERRADA",  "desc3": "1246 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "38", "grupo": "13", "cod_sin": "776124601338", "cod_barra": 776124601338, "cod_obj": "12460", "precio_fab": 13929},
    {"codigo": 361285, "desc1": "1246 GRIS PANTUFLA P/CERRADA",  "desc3": "1246 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "40", "grupo": "13", "cod_sin": "776124601340", "cod_barra": 776124601340, "cod_obj": "12460", "precio_fab": 13929},

    # ── 1246 VERDE — PANTUFLA (binumeral, talles 36/38/40) ──
    {"codigo": 361286, "desc1": "1246 VERDE PANTUFLA P/CERRADA", "desc3": "1246 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "36", "grupo": "13", "cod_sin": "776124602036", "cod_barra": 776124602036, "cod_obj": "12460", "precio_fab": 13929},
    {"codigo": 361287, "desc1": "1246 VERDE PANTUFLA P/CERRADA", "desc3": "1246 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "38", "grupo": "13", "cod_sin": "776124602038", "cod_barra": 776124602038, "cod_obj": "12460", "precio_fab": 13929},
    {"codigo": 361288, "desc1": "1246 VERDE PANTUFLA P/CERRADA", "desc3": "1246 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "40", "grupo": "13", "cod_sin": "776124602040", "cod_barra": 776124602040, "cod_obj": "12460", "precio_fab": 13929},
]


def alta_articulos(cursor, dry_run=True):
    """Da de alta los artículos nuevos (1619 y 1246) en msgestion01art.dbo.articulo."""
    UTIL_1, UTIL_2, UTIL_3, UTIL_4 = 100, 124, 60, 45

    sql = """
        INSERT INTO msgestion01art.dbo.articulo (
            codigo, descripcion_1, descripcion_3, descripcion_4, descripcion_5,
            codigo_barra, codigo_sinonimo, tipo_codigo_barra,
            marca, rubro, subrubro, grupo, proveedor, linea,
            codigo_objeto_costo,
            precio_fabrica, precio_costo, precio_sugerido,
            precio_1, precio_2, precio_3, precio_4,
            utilidad_1, utilidad_2, utilidad_3, utilidad_4,
            alicuota_iva1, alicuota_iva2, tipo_iva,
            formula, calificacion, estado, estado_web,
            descuento, descuento_1, descuento_2, descuento_3, descuento_4,
            flete, porc_flete, porc_recargo, moneda,
            factura_por_total, numero_maximo, stock,
            cuenta_compras, cuenta_ventas, cuenta_vta_anti, cuenta_com_anti,
            usuario, abm, fecha_alta
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, 'C',
            776, 1, 60, ?, 776, 2,
            ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            21, 10.5, 'G',
            1, 'G', 'V', 'V',
            0, 0, 0, 0, 0,
            0, 0, 0, 0,
            'N', 'S', 'S',
            '1010601', '4010100', '4010100', '1010601',
            'COWORK', 'A', GETDATE()
        )
    """

    if dry_run:
        print("\n  [DRY RUN] ALTA DE ARTICULOS NUEVOS:")
        for art in NUEVOS_ARTICULOS:
            print(f"    {art['codigo']}: {art['desc1']} T{art['desc5']} | ${art['precio_fab']:,} | sin={art['cod_sin']}")
        print(f"    Total: {len(NUEVOS_ARTICULOS)} articulos nuevos")
        return True

    # Verificar MAX(codigo) en runtime para evitar colisiones
    cursor.execute("SELECT MAX(codigo) FROM msgestion01art.dbo.articulo")
    max_actual = cursor.fetchone()[0] or 0
    primer_codigo = NUEVOS_ARTICULOS[0]["codigo"]
    if primer_codigo <= max_actual:
        print(f"  !! MAX(codigo) actual = {max_actual}, primer codigo nuevo = {primer_codigo}")
        print(f"  !! Los codigos se van a reasignar automaticamente desde {max_actual + 1}")
        offset = max_actual + 1 - primer_codigo
        for art in NUEVOS_ARTICULOS:
            art["codigo"] = art["codigo"] + offset
        print(f"  !! Nuevos codigos: {NUEVOS_ARTICULOS[0]['codigo']} a {NUEVOS_ARTICULOS[-1]['codigo']}")

    # Verificar que no existan
    codigos = [a["codigo"] for a in NUEVOS_ARTICULOS]
    placeholders = ",".join(["?"] * len(codigos))
    cursor.execute(f"SELECT codigo FROM msgestion01art.dbo.articulo WHERE codigo IN ({placeholders})", codigos)
    existentes = [r[0] for r in cursor.fetchall()]
    if existentes:
        print(f"  !! Articulos ya existentes: {existentes} — saltando alta")
        return True

    for art in NUEVOS_ARTICULOS:
        pf = art["precio_fab"]
        pc = pf  # sin descuento para Comoditas
        p1 = round(pc * (1 + UTIL_1 / 100), 2)
        p2 = round(pc * (1 + UTIL_2 / 100), 2)
        p3 = round(pc * (1 + UTIL_3 / 100), 2)
        p4 = round(pc * (1 + UTIL_4 / 100), 2)

        cursor.execute(sql, (
            art["codigo"], art["desc1"], art["desc3"], art["desc4"], art["desc5"],
            art["cod_barra"], art["cod_sin"],
            art["grupo"],
            art["cod_obj"],
            pf, pc, pc,
            p1, p2, p3, p4,
            UTIL_1, UTIL_2, UTIL_3, UTIL_4,
        ))

    print(f"  OK {len(NUEVOS_ARTICULOS)} articulos nuevos creados ({NUEVOS_ARTICULOS[0]['codigo']}-{NUEVOS_ARTICULOS[-1]['codigo']})")
    return True


# ======================================================================
# PARTE 2: PEDIDO DE COMPRA
# ======================================================================

SQL_PEDIDO_CAB = """
    INSERT INTO {base}.dbo.pedico2 (
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
        8, 'X', 1,
        ?, 1, 0,
        ?, ?,
        ?, ?,
        ?,
        0, 0, 0, 0, 0, 0,
        21, 0, 10.5, 0, 0,
        0, 0,
        'V', 6, 'I', '', 1,
        'N', 'N', 'N', 'N', 'N',
        0, 'COWORK', 0, 2, 0, 0,
        0, 'N', 0, 0, 0,
        ' ', ?, 'N'
    )
"""

SQL_PEDIDO_DET = """
    INSERT INTO {base}.dbo.pedico1 (
        codigo, letra, sucursal,
        numero, orden, renglon,
        articulo, descripcion, codigo_sinonimo,
        cantidad, precio,
        cuenta, fecha, fecha_entrega,
        estado
    ) VALUES (8, 'X', 1, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'V')
"""

# Renglones: (articulo, descripcion, codigo_sinonimo, cantidad, precio)
# Los artículos nuevos (1619, 1246) usan los códigos actualizados
RENGLONES = [
    # ═══ 598 ROSA (binumeral) — 36 pares ═══
    (264863, "598 ROSA PANTUFLA P/CERRADA C/BASE DET BOTON",  "776598001938", 16, 12904),  # T38
    (264864, "598 ROSA PANTUFLA P/CERRADA C/BASE DET BOTON",  "776598001940", 20, 12904),  # T40

    # ═══ 598 GRIS (binumeral) — 36 pares ═══
    (264860, "598 GRIS PANTUFLA P/CERRADA C/BASE DET BOTON",  "776598001338", 16, 12904),  # T38
    (264861, "598 GRIS PANTUFLA P/CERRADA C/BASE DET BOTON",  "776598001340", 20, 12904),  # T40

    # ═══ 598 NEGRO (binumeral) — 36 pares ═══
    (264854, "598 NEGRO PANTUFLA P/CERRADA C/BASE DET BOTON", "776598000038", 16, 12904),  # T38
    (264855, "598 NEGRO PANTUFLA P/CERRADA C/BASE DET BOTON", "776598000040", 20, 12904),  # T40

    # ═══ 1127 AERO (individual) — 36 pares ═══
    (289994, "1127 AERO PANTUFLA P/CERRADA CUE PELUCHE",      "776112700337",  6, 11565),  # T37
    (289995, "1127 AERO PANTUFLA P/CERRADA CUE PELUCHE",      "776112700338",  8, 11565),  # T38
    (289996, "1127 AERO PANTUFLA P/CERRADA CUE PELUCHE",      "776112700339",  8, 11565),  # T39
    (289997, "1127 AERO PANTUFLA P/CERRADA CUE PELUCHE",      "776112700340",  8, 11565),  # T40
    (289998, "1127 AERO PANTUFLA P/CERRADA CUE PELUCHE",      "776112700341",  6, 11565),  # T41

    # ═══ 1127 MANTECA (individual) — 36 pares ═══
    (264908, "1127 MANTECA PANTUFLA P/CERRADA CUE PELUCHE",   "776112701537",  6, 11565),  # T37
    (264909, "1127 MANTECA PANTUFLA P/CERRADA CUE PELUCHE",   "776112701538", 10, 11565),  # T38
    (264910, "1127 MANTECA PANTUFLA P/CERRADA CUE PELUCHE",   "776112701539",  8, 11565),  # T39
    (264911, "1127 MANTECA PANTUFLA P/CERRADA CUE PELUCHE",   "776112701540",  8, 11565),  # T40
    (264912, "1127 MANTECA PANTUFLA P/CERRADA CUE PELUCHE",   "776112701541",  4, 11565),  # T41

    # ═══ 1619 VERDE (individual, NUEVO) — 36 pares ═══
    (361273, "1619 VERDE PANTUFLA P/CERRADA",                 "776161902037",  4, 11422),  # T37
    (361274, "1619 VERDE PANTUFLA P/CERRADA",                 "776161902038",  8, 11422),  # T38
    (361275, "1619 VERDE PANTUFLA P/CERRADA",                 "776161902039", 10, 11422),  # T39
    (361276, "1619 VERDE PANTUFLA P/CERRADA",                 "776161902040", 10, 11422),  # T40
    (361277, "1619 VERDE PANTUFLA P/CERRADA",                 "776161902041",  4, 11422),  # T41

    # ═══ 1619 GRIS (individual, NUEVO) — 36 pares ═══
    (361278, "1619 GRIS PANTUFLA P/CERRADA",                  "776161901337",  4, 11422),  # T37
    (361279, "1619 GRIS PANTUFLA P/CERRADA",                  "776161901338",  8, 11422),  # T38
    (361280, "1619 GRIS PANTUFLA P/CERRADA",                  "776161901339", 10, 11422),  # T39
    (361281, "1619 GRIS PANTUFLA P/CERRADA",                  "776161901340", 10, 11422),  # T40
    (361282, "1619 GRIS PANTUFLA P/CERRADA",                  "776161901341",  4, 11422),  # T41

    # ═══ 1246 GRIS (binumeral, NUEVO) — 36 pares ═══
    (361284, "1246 GRIS PANTUFLA P/CERRADA",                  "776124601338", 16, 13929),  # T38
    (361285, "1246 GRIS PANTUFLA P/CERRADA",                  "776124601340", 20, 13929),  # T40

    # ═══ 1246 VERDE (binumeral, NUEVO) — 36 pares ═══
    (361287, "1246 VERDE PANTUFLA P/CERRADA",                 "776124602038", 16, 13929),  # T38
    (361288, "1246 VERDE PANTUFLA P/CERRADA",                 "776124602040", 20, 13929),  # T40

    # ═══ 239 NEGRO (individual, hombre DUPLICADO) — 72 pares ═══
    (223048, "239 NEGRO PANTUFLA C/PUNTA INT CORDERITO",      "776239000041",  8, 12727),  # T41
    (223049, "239 NEGRO PANTUFLA C/PUNTA INT CORDERITO",      "776239000042", 16, 12727),  # T42
    (223050, "239 NEGRO PANTUFLA C/PUNTA INT CORDERITO",      "776239000043", 16, 12727),  # T43
    (223051, "239 NEGRO PANTUFLA C/PUNTA INT CORDERITO",      "776239000044", 16, 12727),  # T44
    (223052, "239 NEGRO PANTUFLA C/PUNTA INT CORDERITO",      "776239000045", 16, 12727),  # T45

    # ═══ 239 AZUL (individual, hombre DUPLICADO) — 72 pares ═══
    (312186, "239 AZUL PANTUFLA C/PUNTA INT CORDERITO",       "776239000241",  8, 12727),  # T41
    (312187, "239 AZUL PANTUFLA C/PUNTA INT CORDERITO",       "776239000242", 16, 12727),  # T42
    (312188, "239 AZUL PANTUFLA C/PUNTA INT CORDERITO",       "776239000243", 16, 12727),  # T43
    (312189, "239 AZUL PANTUFLA C/PUNTA INT CORDERITO",       "776239000244", 16, 12727),  # T44
    (312190, "239 AZUL PANTUFLA C/PUNTA INT CORDERITO",       "776239000245", 16, 12727),  # T45
]

TOTAL_PARES = sum(r[3] for r in RENGLONES)
TOTAL_MONTO = sum(r[3] * r[4] for r in RENGLONES)


def main():
    EJECUTAR = "--ejecutar" in sys.argv
    DRY_RUN = not EJECUTAR

    print("=" * 65)
    print(f"PEDIDO COMODITAS (CIRENE SA) — Pantuflas Invierno 2026")
    print(f"{'EJECUTAR' if EJECUTAR else 'DRY RUN'}")
    print(f"5 modelos | 11 colores | {len(RENGLONES)} renglones")
    print(f"{TOTAL_PARES} pares | ${TOTAL_MONTO:,.0f} costo total")
    print(f"Servidor: {SERVIDOR}")
    print("=" * 65)

    # Detalle por modelo-color
    modelos = {}
    for art, desc, sin, qty, precio in RENGLONES:
        parts = desc.split()
        key = f"{parts[0]} {parts[1]}"
        modelos.setdefault(key, 0)
        modelos[key] += qty
    for k, v in modelos.items():
        print(f"  {k:40s} {v:>4d} pares")
    print(f"  {'─' * 44}")
    print(f"  {'TOTAL':40s} {TOTAL_PARES:>4d} pares")

    if DRY_RUN:
        # PASO 1: mostrar artículos nuevos
        alta_articulos(None, dry_run=True)

        # PASO 2: mostrar pedido
        print(f"\n  [DRY RUN] PEDIDO:")
        print(f"    {len(RENGLONES)} renglones, {TOTAL_PARES} pares, ${TOTAL_MONTO:,.0f}")
        print(f"    Proveedor: {PROVEEDOR} ({DENOMINACION})")
        print(f"    Entrega: {FECHA_ENTREGA}")
        print(f"\n  DRY RUN — No se inserto nada.")
        print(f"  Para insertar: py -3 insertar_comoditas.py --ejecutar")
        return

    # -- EJECUCION REAL ------------------------------------------------
    confirmacion = input(f"\nInsertar 16 arts nuevos + pedido ({TOTAL_PARES} pares) en {BASE_PEDIDO}? (s/N): ").strip().lower()
    if confirmacion != "s":
        print("Cancelado.")
        sys.exit(0)

    conn = pyodbc.connect(get_conn(BASE_PEDIDO), timeout=30)
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        # PASO 1: Alta artículos nuevos
        print(f"\n--- PASO 1: Alta articulos nuevos ---")
        ok = alta_articulos(cursor, dry_run=False)
        if not ok:
            print("ERROR al crear articulos. Rollback.")
            conn.rollback()
            sys.exit(1)

        # PASO 2: Pedido
        print(f"\n--- PASO 2: Insertar pedido ---")
        cursor.execute(f"SELECT ISNULL(MAX(numero), 0) + 1 FROM {BASE_PEDIDO}.dbo.pedico2 WHERE codigo = 8")
        num_pedido = cursor.fetchone()[0]

        obs = (f"Pedido pantuflas invierno 2026. {TOTAL_PARES} pares. "
               f"5 modelos (598, 1127, 1619, 1246, 239). "
               f"1619 y 1246 modelos nuevos. 239 hombre duplicado x2. "
               f"COWORK {date.today().strftime('%d/%m/%Y')}")

        # Cabecera
        cursor.execute(
            SQL_PEDIDO_CAB.format(base=BASE_PEDIDO),
            num_pedido,
            PROVEEDOR,
            DENOMINACION,
            FECHA_COMPROBANTE,
            FECHA_COMPROBANTE,
            obs,
            PROVEEDOR,
        )
        print(f"  OK Cabecera pedico2 #{num_pedido}")

        # Actualizar codigos de articulos nuevos en RENGLONES si fueron reasignados
        art_map = {a_orig: a_new["codigo"] for a_orig, a_new in
                   zip([361273,361274,361275,361276,361277,361278,361279,361280,361281,361282,361283,361284,361285,361286,361287,361288],
                       NUEVOS_ARTICULOS)}

        # Renglones
        for renglon, (art, desc, sin, qty, precio) in enumerate(RENGLONES, 1):
            art_real = art_map.get(art, art)  # usa codigo reasignado si aplica
            cursor.execute(
                SQL_PEDIDO_DET.format(base=BASE_PEDIDO),
                num_pedido,
                renglon,
                art_real,
                desc,
                sin,
                qty,
                precio,
                PROVEEDOR,
                FECHA_COMPROBANTE,
                FECHA_ENTREGA,
            )

        conn.commit()
        print(f"  OK {len(RENGLONES)} renglones pedico1 insertados")

        # Verificación
        cursor.execute(
            f"SELECT COUNT(*), SUM(cantidad) FROM {BASE_PEDIDO}.dbo.pedico1 "
            f"WHERE numero = ? AND codigo = 8 AND letra = 'X' AND sucursal = 1",
            num_pedido
        )
        row = cursor.fetchone()
        print(f"\n  Verificacion: {row[0]} renglones, {row[1]} pares en pedido #{num_pedido}")

        print(f"\n{'=' * 65}")
        print(f"PEDIDO #{num_pedido} INSERTADO OK — {TOTAL_PARES} pares Comoditas")
        print(f"16 articulos nuevos (1619 + 1246) creados")
        print(f"{'=' * 65}")
        print(f"\nVerificar en SSMS:")
        print(f"  SELECT * FROM msgestionC.dbo.pedico2 WHERE numero = {num_pedido} AND empresa = 'H4'")
        print(f"  SELECT * FROM msgestionC.dbo.pedico1 WHERE numero = {num_pedido} AND empresa = 'H4'")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        conn.rollback()
        print("  Rollback completo.")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
