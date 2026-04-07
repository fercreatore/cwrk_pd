#!/usr/bin/env python3
"""
fix_amphora_campos.py — Completa TODOS los campos faltantes en arts Amphora nuevos
==================================================================================
Referencia: articulo 361253 (ANGELA TAUPE, bien cargado)

Campos a completar:
  - codigo_sinonimo: 044{cod5}{color2d}{talle2d}
  - descripcion_4: nombre color
  - precio_fabrica, precio_costo: precio de fabrica
  - precio_1 (util 100%), precio_2 (util 124%), precio_3 (util 60%)
  - utilidad_2=124, utilidad_3=60, utilidad_4=45
  - formula=1, alicuota_iva1=21, tipo_iva='G'
  - numero_maximo='S', stock='S', moneda=0
  - fecha_alta, fecha_hora, abm='A', usuario='COWORK'

EJECUTAR EN EL 111:
  py -3 fix_amphora_campos.py --dry-run
  py -3 fix_amphora_campos.py --ejecutar
"""

import sys
import pyodbc
import socket
from datetime import datetime

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

# Utilidades Amphora (de referencia 361253)
UTIL_1 = 100
UTIL_2 = 124
UTIL_3 = 60
UTIL_4 = 45

def precios(pf):
    """Calcula precio_1..4 desde precio_fabrica."""
    pc = pf  # precio_costo = precio_fabrica (sin descuento para Amphora)
    return {
        "pf": pf,
        "pc": pc,
        "p1": round(pc * (1 + UTIL_1 / 100)),
        "p2": round(pc * (1 + UTIL_2 / 100)),
        "p3": round(pc * (1 + UTIL_3 / 100)),
        "p4": round(pc * (1 + UTIL_4 / 100)),
    }

# (codigo, sinonimo, color, precio_fabrica)
FIXES = [
    (361392, "044BENIN0105", "NEGRO",           54500),
    (361393, "044CHIAR0102", "NEGRO",           39500),
    (361394, "044ELIZA0104", "NEGRO",           44500),
    (361395, "044ELIZA0504", "BEIGE",           44500),
    (361396, "044INGLA0102", "NEGRO",           39500),
    (361397, "044MACAR0103", "NEGRO",           42000),
    (361398, "044MACAR1303", "CAFE OSCURO",     42000),
    (361399, "044MAGDA0104", "NEGRO",           44500),
    (361400, "044MAGDA0102", "NEGRO",           39500),
    (361401, "044MAGDA5702", "BLANCO ESPECIAL", 39500),
    (361402, "044MAGGI0104", "NEGRO",           44500),
    (361403, "044MAGGI0504", "BEIGE",           44500),
    (361404, "044MAGGI1304", "CAFE OSCURO",     44500),
    (361405, "044MAIDA0104", "NEGRO",           44500),
    (361406, "044MAIDA0704", "CAMEL",           44500),
    (361407, "044MAIDA1304", "CAFE OSCURO",     44500),
    (361408, "044MARGA0104", "NEGRO",           44500),
    (361409, "044MARGA1004", "CAFE",            44500),
    (361410, "044MARGO0104", "NEGRO",           44500),
    (361411, "044MARGO1304", "CAFE OSCURO",     44500),
]

SQL_UPDATE = """
    UPDATE msgestion01art.dbo.articulo SET
        codigo_sinonimo = ?,
        descripcion_4 = ?,
        precio_fabrica = ?,
        precio_costo = ?,
        precio_1 = ?,
        precio_2 = ?,
        precio_3 = ?,
        precio_4 = ?,
        utilidad_1 = ?,
        utilidad_2 = ?,
        utilidad_3 = ?,
        utilidad_4 = ?,
        formula = 1,
        alicuota_iva1 = 21,
        tipo_iva = 'G',
        numero_maximo = 'S',
        stock = 'S',
        moneda = 0,
        fecha_alta = GETDATE(),
        fecha_hora = GETDATE(),
        fecha_modificacion = GETDATE(),
        abm = 'A',
        usuario = 'COWORK'
    WHERE codigo = ?
"""


def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]
    dry_run = modo != "--ejecutar"

    print(f"\n{'='*70}")
    print(f"FIX AMPHORA — Completar campos faltantes")
    print(f"{'='*70}")
    print(f"  Servidor: {SERVIDOR}")
    print(f"  Modo:     {'DRY-RUN' if dry_run else 'PRODUCCION'}")
    print(f"  Arts:     {len(FIXES)}")
    print(f"  Utils:    1={UTIL_1}% 2={UTIL_2}% 3={UTIL_3}% 4={UTIL_4}%")
    print(f"{'='*70}")

    for cod, sin, color, pf in FIXES:
        p = precios(pf)
        print(f"  [{cod}] {sin} col={color:17s} PF=${pf:,} P1=${p['p1']:,} P2=${p['p2']:,} P3=${p['p3']:,} P4=${p['p4']:,}")

    if dry_run:
        print(f"\n  [DRY RUN] No se escribio nada.")
        return

    conn = pyodbc.connect(get_conn("msgestion01art"), timeout=10, autocommit=False)
    cursor = conn.cursor()

    try:
        for cod, sin, color, pf in FIXES:
            p = precios(pf)
            cursor.execute(SQL_UPDATE, (
                sin, color,
                p["pf"], p["pc"],
                p["p1"], p["p2"], p["p3"], p["p4"],
                UTIL_1, UTIL_2, UTIL_3, UTIL_4,
                cod,
            ))
            if cursor.rowcount != 1:
                print(f"    WARN: [{cod}] rowcount={cursor.rowcount}")

        conn.commit()
        print(f"\n  {len(FIXES)} articulos actualizados OK")

        # Verificar
        print(f"\n  Verificacion:")
        cursor.execute("""
            SELECT codigo, codigo_sinonimo, descripcion_4, precio_fabrica,
                   precio_1, precio_2, precio_3, precio_4,
                   utilidad_1, utilidad_2, utilidad_3, utilidad_4,
                   formula, alicuota_iva1, tipo_iva, numero_maximo, stock
            FROM msgestion01art.dbo.articulo
            WHERE codigo BETWEEN 361392 AND 361411
            ORDER BY codigo
        """)
        for row in cursor.fetchall():
            ok = "OK" if row[2] and row[3] and row[12] == 1 else "FALTA"
            print(f"    [{row[0]}] sin={row[1]} d4={row[2]:17s} PF=${row[3]:,} P1=${row[4]:,} u1={row[8]} u2={row[9]} u3={row[10]} u4={row[11]} f={row[12]} iva={row[13]} {ok}")

    except Exception as e:
        conn.rollback()
        print(f"\n  ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
