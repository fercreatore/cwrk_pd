#!/usr/bin/env python3
"""
fix_stock_conhaque.py
=====================
Corrige stock duplicado de CONHAQUE CROCO LAURA (arts 360600-360605).
El remito_crear duplicaba stock (movi_stock + UPDATE manual).
Fix: recalcula stock desde compras1.

Uso:
    py -3 fix_stock_conhaque.py              # dry-run
    py -3 fix_stock_conhaque.py --ejecutar
"""
import sys
import pyodbc

DRY_RUN = '--ejecutar' not in sys.argv
ARTS = list(range(360600, 360606))  # 360600 a 360605
BASE = 'msgestion03'
DEPOSITO = 11

def main():
    conn = pyodbc.connect(
        'DRIVER={SQL Server};SERVER=192.168.2.111;DATABASE=msgestion03;UID=am;PWD=dl'
    )
    cursor = conn.cursor()

    print("=" * 60)
    print("FIX STOCK CONHAQUE CROCO LAURA")
    print("=" * 60)
    if DRY_RUN:
        print("*** DRY-RUN — no se modifica nada ***\n")

    for art in ARTS:
        # Cantidad real desde compras1
        cursor.execute("""
            SELECT SUM(CASE WHEN operacion='+' THEN CAST(cantidad AS INT)
                            WHEN operacion='-' THEN -CAST(cantidad AS INT)
                            ELSE 0 END) AS stock_real
            FROM {}.dbo.compras1
            WHERE articulo = {}
        """.format(BASE, art))
        row = cursor.fetchone()
        stock_real = row[0] if row and row[0] else 0

        # Stock actual
        cursor.execute("""
            SELECT stock_actual FROM {}.dbo.stock
            WHERE deposito = {} AND articulo = {}
        """.format(BASE, DEPOSITO, art))
        row = cursor.fetchone()
        stock_actual = int(row[0]) if row and row[0] else 0

        print("  Art {}: stock_actual={}, stock_real={} {}".format(
            art, stock_actual, stock_real,
            "OK" if stock_actual == stock_real else "-> CORREGIR"))

        if stock_actual != stock_real and not DRY_RUN:
            cursor.execute("""
                UPDATE {}.dbo.stock
                SET stock_actual = {}, stock_unidades = {}
                WHERE deposito = {} AND articulo = {}
            """.format(BASE, stock_real, stock_real, DEPOSITO, art))

    if not DRY_RUN:
        conn.commit()
        print("\n=== COMMIT OK ===")
    else:
        print("\n=== Ejecutar con --ejecutar para aplicar ===")

    cursor.close()
    conn.close()

if __name__ == '__main__':
    main()
