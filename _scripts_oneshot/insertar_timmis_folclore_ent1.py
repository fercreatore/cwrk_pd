#!/usr/bin/env python3
"""
Insertar pedido TIMMIS - Folclore Entrega 1 (120 pares, contado)
Proveedor: 11 (TIMMi NEW SHOES)
Fecha: 25/03/2026
Criterio: curva ideal 90 días por talle, primera de 3 entregas
"""
import pyodbc
from datetime import date

CONN = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;DATABASE=msgestion01;"
    "UID=am;PWD=dl;TrustServerCertificate=yes;Encrypt=no"
)

NUMERO = 1134086
PROVEEDOR = 11
FECHA = date.today().strftime('%Y%m%d')

# Entrega 1: ~1/3 del total por modelo
# (codigo_articulo, cantidad, precio_fabrica, descripcion)
DETALLE = [
    # 349 Negro - 27 pares (prov 11, csr 0110035000)
    (348854, 2, 23700, '349 NGO T35'),
    (348855, 6, 23700, '349 NGO T36'),
    (348856, 5, 23700, '349 NGO T37'),
    (348857, 7, 23700, '349 NGO T38'),
    (348858, 4, 23700, '349 NGO T39'),
    (348859, 3, 23700, '349 NGO T40'),
    # 349 Beige - 5 pares (prov 11, csr 0110035015)
    (349063, 2, 22999.9, '349 BGE T38'),
    (349064, 2, 22999.9, '349 BGE T39'),
    (349065, 1, 22999.9, '349 BGE T40'),
    # 259PU Negro - 14 pares (prov 17, csr 0110026000)
    (349238, 1, 23700, '259PU NGO T35'),
    (349239, 5, 23700, '259PU NGO T36'),
    (349240, 8, 23700, '259PU NGO T37'),  # 5 del 260 + 3 del 259
    (349241, 9, 23700, '259PU NGO T38'),  # 5 del 260 + 4 del 259
    (349242, 8, 23700, '259PU NGO T39'),  # 5 del 260 + 3 del 259
    (349243, 6, 23700, '259PU NGO T40'),  # 4 del 260 + 2 del 259
    # 259PU Beige - 14 pares (prov 11, csr 0110025915)
    (350844, 2, 23700, '259PU BGE T37'),
    (350845, 5, 23700, '259PU BGE T38'),
    (350846, 4, 23700, '259PU BGE T39'),
    (350847, 3, 23700, '259PU BGE T40'),
    # 260PU Negro Zotz - 23 pares (prov 457, csr 457260PU00)
    (307822, 4, 26000, '260PU NGO T36'),
    (307823, 5, 26000, '260PU NGO T37'),
    (307824, 5, 26000, '260PU NGO T38'),
    (307825, 5, 26000, '260PU NGO T39'),
    (307826, 4, 26000, '260PU NGO T40'),
    # 260PU Galletita - 15 pares (prov 17, csr 4570026022)
    (346942, 1, 23000, '260 GALL T35'),
    (346943, 2, 23000, '260 GALL T36'),
    (346944, 4, 23000, '260 GALL T37'),
    (346945, 4, 23000, '260 GALL T38'),
    (346946, 2, 23000, '260 GALL T39'),
    (346947, 1, 23000, '260 GALL T40'),
    (346948, 1, 23000, '260 GALL T41'),
    # 350PU Negro - 10 pares (prov 457, csr 457350PU00)
    (320835, 2, 26000, '350PU NGO T35'),
    (320836, 2, 26000, '350PU NGO T36'),
    (320837, 1, 26000, '350PU NGO T37'),
    (320838, 1, 26000, '350PU NGO T38'),
    (320839, 2, 26000, '350PU NGO T39'),
    (320840, 1, 26000, '350PU NGO T40'),
    (330135, 1, 26000, '350PU NGO T41'),
    # 350/S Negro - 8 pares (prov 457, csr 4570350S00)
    (331989, 1, 26000, '350S NGO T35'),
    (331990, 1, 26000, '350S NGO T36'),
    (331991, 2, 26000, '350S NGO T37'),
    (331992, 1, 26000, '350S NGO T38'),
    (331993, 2, 26000, '350S NGO T39'),
    (331994, 1, 26000, '350S NGO T40'),
    # 350 Galletita - 4 pares (prov 457, csr 4570035022)
    (346950, 1, 23000, '350 GALL T36'),
    (346951, 1, 23000, '350 GALL T37'),
    (346953, 1, 23000, '350 GALL T39'),
    (346954, 1, 23000, '350 GALL T40'),
]

# Filtrar cantidad > 0
DETALLE = [(cod, qty, pf, desc) for cod, qty, pf, desc in DETALLE if qty > 0]


def main():
    conn = pyodbc.connect(CONN, timeout=15)
    cur = conn.cursor()

    # Verificar que el número no exista
    cur.execute("""
        SELECT COUNT(*) FROM pedico2
        WHERE codigo=8 AND letra='X' AND sucursal=1 AND numero=?
    """, NUMERO)
    if cur.fetchone()[0] > 0:
        print(f"ERROR: Pedido {NUMERO} ya existe!")
        conn.close()
        return

    total_pares = sum(qty for _, qty, _, _ in DETALLE)
    monto_total = sum(qty * pf for _, qty, pf, _ in DETALLE)

    print(f"Pedido #{NUMERO} - TIMMIS Folclore Ent.1")
    print(f"  Pares: {total_pares}")
    print(f"  Monto: ${monto_total:,.0f}")
    print(f"  Líneas: {len(DETALLE)}")
    print()

    for cod, qty, pf, desc in DETALLE:
        print(f"  {desc:20s}  x{qty:2d}  ${pf:,.0f}")

    resp = input("\n¿Confirmar INSERT? (S/N): ")
    if resp.strip().upper() != 'S':
        print("Cancelado.")
        conn.close()
        return

    # INSERT pedico2 (cabecera)
    cur.execute("""
        INSERT INTO pedico2 (
            codigo, numero, letra, sucursal, estado, usuario,
            auxiliar, fecha, monto_general, observaciones
        ) VALUES (
            8, ?, 'X', 1, 'V', 'COWORK',
            ?, ?, ?, 'FOLCLORE ENT1 CONTADO - TIMMIS - COWORK 25MAR'
        )
    """, NUMERO, PROVEEDOR, FECHA, monto_total)

    # INSERT pedico1 (detalle)
    for orden, (cod_art, qty, precio, _) in enumerate(DETALLE, 1):
        cur.execute("""
            INSERT INTO pedico1 (
                codigo, numero, letra, sucursal, orden,
                articulo, cantidad, precio, descuento, descuento_1
            ) VALUES (
                8, ?, 'X', 1, ?,
                ?, ?, ?, 0, 0
            )
        """, NUMERO, orden, cod_art, qty, precio)

    conn.commit()
    print(f"\n✅ Pedido {NUMERO} insertado: {total_pares} pares, ${monto_total:,.0f}")
    conn.close()


if __name__ == '__main__':
    main()
