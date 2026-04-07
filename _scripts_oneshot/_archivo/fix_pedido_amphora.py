#!/usr/bin/env python3
"""
fix_pedido_amphora.py — Completa los renglones faltantes del pedido Amphora #1134073
=====================================================================================
El pedido tiene 10 renglones (1,2,6-13) pero faltan 11 (3,4,5,14-21).
Los artículos ya existen todos en msgestion01art.

Renglones existentes:
  1: 361246 KIRKLI MOCHILA NEGRO (2x $44,500)
  2: 361247 CAMELEON RIÑONERA NEGRO (2x $39,500)
  6: 361251 JENIFER CARTERA DOS ASAS TRES DIV NEGRO (2x $49,500)
  7: 361252 JENIFER CARTERA DOS ASAS TRES DIV CAFE (1x $49,500)
  8: 361253 ANGELA CARTERA DOS ASAS TAUPE (1x $44,500)
  9: 361254 CHARLOTE MOCHILA NEGRO (2x $39,500)
  10: 361255 CHARLOTE MOCHILA CAFE OSCURO (1x $39,500)
  11: 361256 CHARLOTE BANDOLERA NEGRO (2x $37,000)
  12: 361257 CHARLOTE BANDOLERA CAFE OSCURO (1x $37,000)
  13: 361258 JULIA CARTERA DOS ASAS NEGRO (2x $39,500)

Renglones faltantes:
  3: CHIARA BANDOLERA NEGRO (2x $39,500) — art no existe, hay que buscarlo o usar existente
  4: BENIN CARTERA PORTA NOTEBOOK NEGRO (2x $54,500) — 361301
  5: INGLATERRA BANDOLERA NEGRO (2x $39,500) — no existe, hay que crear
  14: AMARANTA MOCHILA NEGRO (2x $42,000) — 361300
  15: ELIZA CARTERA DOS ASAS NEGRO (2x $44,500) — 361303
  16: MACARENA MOCHILA NEGRO (1x $42,000) — 361304
  17: MAGDALENA CARTERA DOS ASAS NEGRO (2x $44,500) — 361305
  18: MAGDALENA BANDOLERA NEGRO (2x $39,500) — 361306
  19: MAGDALENA BANDOLERA BLANCO ESPECIAL (1x $39,500) — 361307
  20: MARGARET CARTERA DOS ASAS NEGRO (2x $44,500) — 361308
  21: MARGARET CARTERA DOS ASAS CAFE (2x $44,500) — 361309

pedico1 esta en MSGESTION01 (tabla real, 03 es VIEW).

EJECUTAR EN EL 111:
  py -3 fix_pedido_amphora.py --dry-run
  py -3 fix_pedido_amphora.py --ejecutar
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

# -- DATOS DEL PEDIDO --------------------------------------------------
NUM_PEDIDO = 1134073
BASE = "MSGESTION01"  # tabla real (03 es VIEW)
PROVEEDOR = 44
FECHA = date(2026, 3, 16)

# Renglones a insertar: (renglon, articulo, descripcion, codigo_sinonimo, cantidad, precio)
# Para CHIARA e INGLATERRA que no existen, primero los damos de alta
ITEMS_FALTANTES = [
    # reng, codigo_art, descripcion, barcode, cant, precio
    (3,  None,   "CHIARA BANDOLERA NEGRO",               "040433905201",   2, 39500.00),
    (4,  361301, "BENIN CARTERA PORTA NOTEBOOK NEGRO",    "040424027701",   2, 54500.00),
    (5,  None,   "INGLATERRA BANDOLERA NEGRO",            "040424026901",   2, 39500.00),
    (14, 361300, "AMARANTA MOCHILA NEGRO",                "04042423200001", 2, 42000.00),
    (15, 361303, "ELIZA CARTERA DOS ASAS NEGRO",          "04043423450001", 2, 44500.00),
    (16, 361304, "MACARENA MOCHILA NEGRO",                "04043423500001", 1, 42000.00),
    (17, 361305, "MAGDALENA CARTERA DOS ASAS NEGRO",      "04043423530001", 2, 44500.00),
    (18, 361306, "MAGDALENA BANDOLERA NEGRO",             "04043423550001", 2, 39500.00),
    (19, 361307, "MAGDALENA BANDOLERA BLANCO ESPECIAL",   "04043423550057", 1, 39500.00),
    (20, 361308, "MARGARET CARTERA DOS ASAS NEGRO",       "04043423900001", 2, 44500.00),
    (21, 361309, "MARGARET CARTERA DOS ASAS CAFE",        "04043423900010", 2, 44500.00),
]

SQL_ARTICULO = """
    INSERT INTO msgestion01art.dbo.articulo (
        codigo, codigo_sinonimo,
        descripcion_1, descripcion_5,
        proveedor, marca, grupo, rubro, subrubro,
        precio_4, utilidad_1,
        codigo_objeto_costo,
        estado
    ) VALUES (?, ?, ?, ?, 44, 44, '5', 1, ?, ?, 100, ?, ?)
"""

SQL_DETALLE = """
    INSERT INTO {base}.dbo.pedico1 (
        codigo, letra, sucursal,
        numero, orden, renglon,
        articulo, descripcion, codigo_sinonimo,
        cantidad, precio,
        cuenta, fecha, fecha_entrega,
        estado
    ) VALUES (8, 'X', 1, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'V')
"""

TALLE_MAP = {
    "BANDOLERA": "02",
    "MOCHILA": "03",
    "CARTERA": "04",
    "PORTA NOTEBOOK": "05",
}

SUBRUBRO_MAP = {
    "MOCHILA": 25,
    "BANDOLERA": 39,
    "CARTERA": 18,
    "PORTA NOTEBOOK": 18,
}

def detectar_talle(desc):
    d = desc.upper()
    if "PORTA NOTEBOOK" in d:
        return "05"
    for k, v in TALLE_MAP.items():
        if k in d:
            return v
    return ""

def detectar_subrubro(desc):
    d = desc.upper()
    if "PORTA NOTEBOOK" in d:
        return 18
    for k, v in SUBRUBRO_MAP.items():
        if k in d:
            return v
    return 0


def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]
    dry_run = modo != "--ejecutar"

    print(f"\n{'='*60}")
    print(f"FIX PEDIDO AMPHORA #{NUM_PEDIDO}")
    print(f"{'='*60}")
    print(f"  Base:     {BASE}")
    print(f"  Servidor: {SERVIDOR}")
    print(f"  Modo:     {'DRY-RUN' if dry_run else 'PRODUCCION'}")
    print(f"{'='*60}")

    # Items que necesitan alta de articulo
    items_sin_art = [(r, d, bc, c, p) for r, art, d, bc, c, p in ITEMS_FALTANTES if art is None]
    items_con_art = [(r, art, d, bc, c, p) for r, art, d, bc, c, p in ITEMS_FALTANTES if art is not None]

    print(f"\n  Articulos a crear: {len(items_sin_art)}")
    for r, d, bc, c, p in items_sin_art:
        print(f"    Reng {r:2d}: {d} (barcode {bc})")

    print(f"\n  Renglones a insertar (art existente): {len(items_con_art)}")
    for r, art, d, bc, c, p in items_con_art:
        print(f"    Reng {r:2d}: [{art}] {d} x{c} @ ${p:,.0f}")

    total_uds = sum(c for _, _, _, _, c, _ in ITEMS_FALTANTES)
    total_monto = sum(c * p for _, _, _, _, c, p in ITEMS_FALTANTES)
    print(f"\n  Total: {len(ITEMS_FALTANTES)} renglones, {total_uds} uds, ${total_monto:,.0f}")

    if dry_run:
        print(f"\n  [DRY RUN] No se escribio nada.")
        print(f"  Para ejecutar: py -3 fix_pedido_amphora.py --ejecutar")
        # Test conexion
        try:
            with pyodbc.connect(get_conn("msgestionC"), timeout=5) as conn:
                conn.cursor().execute("SELECT 1")
                print(f"  Conexion OK")
        except Exception as e:
            print(f"  Conexion ERROR: {e}")
        return

    # EJECUTAR
    confirmacion = input(f"\n  Insertar {len(ITEMS_FALTANTES)} renglones en pedido #{NUM_PEDIDO}? (s/N): ").strip().lower()
    if confirmacion != "s":
        print("  Cancelado.")
        sys.exit(0)

    conn = pyodbc.connect(get_conn(BASE), timeout=10, autocommit=False)
    cursor = conn.cursor()

    try:
        # 1. Crear articulos faltantes
        if items_sin_art:
            cursor.execute("SELECT ISNULL(MAX(codigo), 0) FROM msgestion01art.dbo.articulo")
            next_cod = int(cursor.fetchone()[0]) + 1
            print(f"\n  Creando articulos desde codigo {next_cod}...")

        art_nuevos = {}
        for r, desc, bc, cant, precio in items_sin_art:
            codigo = next_cod
            next_cod += 1
            talle = detectar_talle(desc)
            subrubro = detectar_subrubro(desc)
            cod_obj = desc.split()[0].upper()[:30]
            cursor.execute(SQL_ARTICULO, (
                codigo, bc,
                desc, talle,
                subrubro,
                precio, cod_obj, 'V',
            ))
            art_nuevos[r] = codigo
            print(f"    [{codigo}] {desc} (subrubro={subrubro})")

        # 2. Insertar renglones en pedico1
        print(f"\n  Insertando renglones en pedico1...")
        for reng, art, desc, bc, cant, precio in ITEMS_FALTANTES:
            if art is None:
                art = art_nuevos[reng]
            cursor.execute(SQL_DETALLE.format(base=BASE), (
                NUM_PEDIDO, reng,
                art, desc, bc,
                cant, precio,
                PROVEEDOR,
                FECHA, FECHA,
            ))
            print(f"    Reng {reng:2d}: [{art}] {desc} x{cant}")

        conn.commit()

        print(f"\n{'='*60}")
        print(f"  PEDIDO #{NUM_PEDIDO} COMPLETADO")
        print(f"  {len(ITEMS_FALTANTES)} renglones insertados")
        if art_nuevos:
            print(f"  {len(art_nuevos)} articulos creados: {list(art_nuevos.values())}")
        print(f"{'='*60}")

        # Verificar
        cursor.execute(f"""
            SELECT COUNT(*), SUM(cantidad)
            FROM {BASE}.dbo.pedico1
            WHERE numero = {NUM_PEDIDO} AND codigo = 8
        """)
        check = cursor.fetchone()
        print(f"\n  Verificacion: {check[0]} renglones, {check[1]} pares (debe ser 21 renglones, 36 pares)")

    except Exception as e:
        conn.rollback()
        print(f"\n  ERROR — ROLLBACK: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
