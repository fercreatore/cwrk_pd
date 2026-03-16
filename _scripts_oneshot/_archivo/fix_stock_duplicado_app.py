#!/usr/bin/env python3
"""
fix_stock_duplicado_app.py
==========================
Corrige stock duplicado en TODOS los articulos cargados por nuestra app.
Bug: remito_crear hacia UPDATE/INSERT stock manual + movi_stock (que el ERP
tambien procesa) = 2x stock.

Afectados: 128 articulos con serie 2603xxxx en msgestion03.dbo.stock
(Piccadilly, Footy, Conhaque — todos cargados por la app en marzo 2026)

Fix: recalcula stock_actual desde compras1 (fuente de verdad).

Uso:
    py -3 fix_stock_duplicado_app.py              # dry-run
    py -3 fix_stock_duplicado_app.py --ejecutar
"""
import sys
import pyodbc

DRY_RUN = '--ejecutar' not in sys.argv

def main():
    conn = pyodbc.connect(
        'DRIVER={SQL Server};SERVER=192.168.2.111;DATABASE=msgestion03;UID=am;PWD=dl'
    )
    cursor = conn.cursor()

    print("=" * 60)
    print("FIX STOCK DUPLICADO — TODOS LOS ARTICULOS APP")
    print("=" * 60)
    if DRY_RUN:
        print("*** DRY-RUN — no se modifica nada ***\n")

    # Buscar todos los articulos con serie 2603xxxx en stock
    cursor.execute("""
        SELECT s.articulo, s.deposito, s.stock_actual, RTRIM(s.serie) AS serie
        FROM msgestion03.dbo.stock s
        WHERE s.serie LIKE '2603%' AND LEN(RTRIM(s.serie)) = 8
        ORDER BY s.articulo
    """)
    rows = cursor.fetchall()

    total = 0
    corregidos = 0
    ya_ok = 0

    for row in rows:
        art = int(row[0])
        dep = int(row[1])
        stock_actual = int(row[2])
        serie = row[3].strip()

        # Stock real desde compras1
        cursor.execute("""
            SELECT ISNULL(SUM(
                CASE WHEN operacion='+' THEN CAST(cantidad AS INT)
                     WHEN operacion='-' THEN -CAST(cantidad AS INT)
                     ELSE 0 END
            ), 0) FROM msgestion03.dbo.compras1 WHERE articulo = ?
        """, art)
        stock_real = int(cursor.fetchone()[0])

        total += 1
        if stock_actual == stock_real:
            ya_ok += 1
            continue

        print("  Art {:>6d} dep {:>2d} serie {}: {} -> {}".format(
            art, dep, serie, stock_actual, stock_real))

        if not DRY_RUN:
            cursor.execute("""
                UPDATE msgestion03.dbo.stock
                SET stock_actual = ?, stock_unidades = ?
                WHERE deposito = ? AND articulo = ? AND serie = ?
            """, stock_real, stock_real, dep, art, serie)
            corregidos += 1

    print()
    print("Total articulos: {}".format(total))
    print("Ya correctos:    {}".format(ya_ok))
    print("A corregir:      {}".format(total - ya_ok))

    if not DRY_RUN:
        conn.commit()
        print("Corregidos:      {}".format(corregidos))
        print("\n=== COMMIT OK ===")
    else:
        print("\n=== Ejecutar con --ejecutar para aplicar ===")

    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()
