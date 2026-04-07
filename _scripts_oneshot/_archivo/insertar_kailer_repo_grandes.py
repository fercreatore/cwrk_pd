#!/usr/bin/env python3
"""
insertar_kailer_repo_grandes.py — Pedido reposición Kailer zapatillas grandes T46-T48
Proveedor: 21 (KAILER SA), Marca: 21, Grupo: 17
Empresa: H4 → MSGESTION03
4 modelos-color × 3 talles × 4 pares = 48 pares

Top sellers por velocidad histórica:
  1. 1021 NEGRO  — 91 vendidos históricamente
  2. 1020 NEGRO  — 75 vendidos
  3. 1020 MARRON — 66 vendidos
  4. 1020 GRIS   — 45 vendidos

EJECUTAR EN EL 111:
  py -3 insertar_kailer_repo_grandes.py --dry-run     <- solo muestra
  py -3 insertar_kailer_repo_grandes.py --ejecutar    <- escribe en produccion
"""

import sys
import pyodbc
import socket
from datetime import date

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
PROVEEDOR = 21
DENOMINACION = "KAILER SA"
MARCA = 21
GRUPO = "17"
FECHA_HOY = date.today()
BASE_PEDIDO = "MSGESTION01"  # pedico2/pedico1 compartidas

# -- ITEMS: (codigo_articulo, sinonimo, descripcion_1, color, talle, precio_costo, cantidad) --
ITEMS = [
    # 1021 NEGRO — top seller (91 vendidos)
    (255259, "021102100046", "1021 NEGRO ZAPA DEP ACORD DET COST", "NEGRO", "46", 14242.40, 4),
    (255260, "021102100047", "1021 NEGRO ZAPA DEP ACORD DET COST", "NEGRO", "47", 14242.40, 4),
    (255261, "021102100048", "1021 NEGRO ZAPA DEP ACORD DET COST", "NEGRO", "48", 14242.40, 4),
    # 1020 NEGRO — 2do (75 vendidos)
    (196604, "021102000046", "1020 NEGRO ZAPA DEPORTIVA ACORDONADA", "NEGRO", "46", 14242.40, 4),
    (196605, "021102000047", "1020 NEGRO ZAPA DEPORTIVA ACORDONADA", "NEGRO", "47", 14242.40, 4),
    (196606, "021102000048", "1020 NEGRO ZAPA DEPORTIVA ACORDONADA", "NEGRO", "48", 14242.40, 4),
    # 1020 MARRON — 3ro (66 vendidos)
    (204847, "021102001146", "1020 MARRON ZAPA DEPORTIVA ACORDONADA", "MARRON", "46", 14242.40, 4),
    (204848, "021102001147", "1020 MARRON ZAPA DEPORTIVA ACORDONADA", "MARRON", "47", 14242.40, 4),
    (204849, "021102001148", "1020 MARRON ZAPA DEPORTIVA ACORDONADA", "MARRON", "48", 14242.40, 4),
    # 1020 GRIS — 4to (45 vendidos)
    (194825, "021102001346", "1020 GRIS ZAPA DEPORTIVA ACORDONADA", "GRIS", "46", 14242.40, 4),
    (194826, "021102001347", "1020 GRIS ZAPA DEPORTIVA ACORDONADA", "GRIS", "47", 14242.40, 4),
    (194827, "021102001348", "1020 GRIS ZAPA DEPORTIVA ACORDONADA", "GRIS", "48", 14242.40, 4),
]

TOTAL_PARES = sum(i[6] for i in ITEMS)
TOTAL_MONTO = sum(i[5] * i[6] for i in ITEMS)

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
        'V', 1, 'I', '', 1,
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


def main():
    EJECUTAR = "--ejecutar" in sys.argv
    DRY_RUN = not EJECUTAR

    print("=" * 65)
    print(f"PEDIDO KAILER ZAPATILLAS GRANDES T46-T48")
    print(f"{'EJECUTAR' if EJECUTAR else 'DRY RUN'}")
    print(f"Top 4 modelos-color por venta | 4 pares/talle | 3 talles")
    print(f"{TOTAL_PARES} pares | ${TOTAL_MONTO:,.0f} costo total")
    print("=" * 65)

    # Mostrar detalle
    print(f"\n{'Modelo':<45} {'Color':<8} {'T':<4} {'Cant':>4} {'Costo':>10}")
    print("-" * 75)
    for art, sin, desc, color, talle, precio, cant in ITEMS:
        print(f"{desc:<45} {color:<8} {talle:<4} {cant:>4} ${precio:>9,.0f}")
    print("-" * 75)
    print(f"{'TOTAL':<59} {TOTAL_PARES:>4} ${TOTAL_MONTO:>9,.0f}")

    if DRY_RUN:
        print(f"\n⚠️  DRY RUN — No se insertó nada.")
        print(f"    Para insertar: py -3 insertar_kailer_repo_grandes.py --ejecutar")
        return

    # Conectar
    conn = pyodbc.connect(get_conn(BASE_PEDIDO), timeout=30)
    cursor = conn.cursor()

    # Obtener siguiente número de pedido
    cursor.execute(f"SELECT ISNULL(MAX(numero), 0) + 1 FROM {BASE_PEDIDO}.dbo.pedico2 WHERE codigo = 8")
    num_pedido = cursor.fetchone()[0]
    print(f"\nNúmero de pedido: {num_pedido}")

    obs = f"REPO KAILER GRANDES T46-48 — {TOTAL_PARES} pares — COWORK {FECHA_HOY.strftime('%d/%m/%Y')}"

    # Insertar cabecera
    cursor.execute(
        SQL_PEDIDO_CAB.format(base=BASE_PEDIDO),
        num_pedido,           # numero
        PROVEEDOR,            # cuenta
        DENOMINACION,         # denominacion
        FECHA_HOY,            # fecha_comprobante
        FECHA_HOY,            # fecha_proceso
        obs,                  # observaciones
        PROVEEDOR,            # cuenta_cc
    )
    print(f"✅ Cabecera pedico2 #{num_pedido} insertada")

    # Insertar renglones
    for renglon, (art, sin, desc, color, talle, precio, cant) in enumerate(ITEMS, 1):
        cursor.execute(
            SQL_PEDIDO_DET.format(base=BASE_PEDIDO),
            num_pedido,       # numero
            renglon,          # renglon
            art,              # articulo
            desc,             # descripcion
            sin,              # codigo_sinonimo
            cant,             # cantidad
            precio,           # precio
            PROVEEDOR,        # cuenta
            FECHA_HOY,        # fecha
            FECHA_HOY,        # fecha_entrega
        )

    conn.commit()
    print(f"✅ {len(ITEMS)} renglones pedico1 insertados")

    # Verificación
    cursor.execute(
        f"SELECT COUNT(*), SUM(cantidad) FROM {BASE_PEDIDO}.dbo.pedico1 "
        f"WHERE numero = ? AND codigo = 8 AND letra = 'X' AND sucursal = 1",
        num_pedido
    )
    row = cursor.fetchone()
    print(f"\n✅ Verificación: {row[0]} renglones, {row[1]} pares en pedido #{num_pedido}")
    print(f"   Empresa: H4 (KAILER SA, proveedor {PROVEEDOR})")

    conn.close()

    print(f"\n{'=' * 65}")
    print(f"PEDIDO #{num_pedido} INSERTADO OK — {TOTAL_PARES} pares Kailer")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()
