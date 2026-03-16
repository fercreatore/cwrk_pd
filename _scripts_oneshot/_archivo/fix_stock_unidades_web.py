#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_stock_unidades_web.py
Corrige TODOS los registros afectados por el bug de remito_crear():
  1) movi_stock.unidades = cantidad  (para remitos creados por WB)
  2) stock.stock_unidades = stock_actual  (para articulos PIRA + valijas)

Articulos afectados:
  PIRA SRL #1926645: 196897, 205975, 207777, 207784, 226835, 226836, 248387, 248388
  Valijas GO BY CZL: 359226, 359228, 359230

Ejecutar en 111: py -3 fix_stock_unidades_web.py [--ejecutar]
"""
import sys
import pyodbc

DRY_RUN = '--ejecutar' not in sys.argv

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=master;"
    "UID=am;PWD=dl"
)

# Artículos afectados por el bug
ARTICULOS_PIRA = [196897, 205975, 207777, 207784, 226835, 226836, 248387, 248388]
ARTICULOS_VALIJAS = [359226, 359228, 359230]
TODOS = ARTICULOS_PIRA + ARTICULOS_VALIJAS

def main():
    print("=" * 60)
    print("FIX stock_unidades + movi_stock.unidades — Bug remito web")
    print("Modo:", "DRY RUN (simulacion)" if DRY_RUN else "EJECUTAR (cambios reales)")
    print("=" * 60)

    conn = pyodbc.connect(CONN_STR, autocommit=False)
    cur = conn.cursor()
    total_fixes = 0

    # ---- FIX 1: movi_stock.unidades = cantidad (usuario WB) ----
    print("\n--- FIX 1: movi_stock.unidades = cantidad (usuario WB) ---")
    for base in ['msgestion01', 'msgestion03']:
        sql_check = """
        SELECT articulo, cantidad, unidades, numero_comprobante
        FROM {}.dbo.movi_stock
        WHERE usuario = 'WB'
          AND unidades <> cantidad
        """.format(base)
        cur.execute(sql_check)
        rows = cur.fetchall()
        print("  {}: {} registros a corregir".format(base, len(rows)))
        for r in rows:
            print("    art={} cant={} unid={} comp={} -> unid={}".format(
                r.articulo, r.cantidad, r.unidades, r.numero_comprobante, r.cantidad))

        if not DRY_RUN and rows:
            sql_fix = """
            UPDATE {}.dbo.movi_stock
            SET unidades = cantidad
            WHERE usuario = 'WB'
              AND unidades <> cantidad
            """.format(base)
            cur.execute(sql_fix)
            total_fixes += cur.rowcount
            print("    -> {} registros actualizados".format(cur.rowcount))

    # ---- FIX 2: stock.stock_unidades = stock_actual ----
    print("\n--- FIX 2: stock.stock_unidades = stock_actual ---")
    arts_str = ','.join(str(a) for a in TODOS)
    for base in ['msgestion01', 'msgestion03']:
        sql_check = """
        SELECT deposito, articulo, serie, stock_actual, stock_unidades
        FROM {}.dbo.stock
        WHERE articulo IN ({})
          AND stock_actual <> stock_unidades
        ORDER BY articulo, deposito, serie
        """.format(base, arts_str)
        cur.execute(sql_check)
        rows = cur.fetchall()
        print("  {}: {} registros a corregir".format(base, len(rows)))
        for r in rows:
            print("    dep={} art={} serie='{}' actual={} unid={} -> unid={}".format(
                r.deposito, r.articulo, r.serie.rstrip(), r.stock_actual,
                r.stock_unidades, r.stock_actual))

        if not DRY_RUN and rows:
            sql_fix = """
            UPDATE {}.dbo.stock
            SET stock_unidades = stock_actual
            WHERE articulo IN ({})
              AND stock_actual <> stock_unidades
            """.format(base, arts_str)
            cur.execute(sql_fix)
            total_fixes += cur.rowcount
            print("    -> {} registros actualizados".format(cur.rowcount))

    if DRY_RUN:
        print("\n*** DRY RUN — no se aplicaron cambios ***")
        print("*** Ejecutar con: py -3 fix_stock_unidades_web.py --ejecutar ***")
        conn.rollback()
    else:
        conn.commit()
        print("\n*** {} CAMBIOS APLICADOS ***".format(total_fixes))

    conn.close()

if __name__ == '__main__':
    main()
