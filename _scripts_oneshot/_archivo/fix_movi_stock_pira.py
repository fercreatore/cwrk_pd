#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_movi_stock_pira.py
Corrige registros de movi_stock y stock creados por la web (usuario WB)
para el remito PIRA SRL #1926645 del 2026-03-05.

Bugs corregidos:
  1) movi_stock.unidades estaba en 1, debe ser = cantidad
  2) stock.stock_unidades estaba desincronizado con stock_actual

Ejecutar en 111: py -3 fix_movi_stock_pira.py [--ejecutar]
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

def main():
    print("=" * 60)
    print("FIX movi_stock + stock — Remito PIRA SRL #1926645")
    print("Modo:", "DRY RUN (simulacion)" if DRY_RUN else "EJECUTAR (cambios reales)")
    print("=" * 60)

    conn = pyodbc.connect(CONN_STR, autocommit=False)
    cur = conn.cursor()

    # ---- FIX 1: movi_stock.unidades = cantidad ----
    print("\n--- FIX 1: movi_stock.unidades = cantidad ---")
    for base in ['msgestion01', 'msgestion03']:
        sql_check = """
        SELECT articulo, cantidad, unidades
        FROM {}.dbo.movi_stock
        WHERE usuario = 'WB'
          AND numero_comprobante = 1926645
          AND codigo_comprobante = 7
          AND unidades <> cantidad
        """.format(base)
        cur.execute(sql_check)
        rows = cur.fetchall()
        print(f"  {base}: {len(rows)} registros con unidades != cantidad")
        for r in rows:
            print(f"    art={r.articulo} cant={r.cantidad} unid={r.unidades} -> unid={r.cantidad}")

        if not DRY_RUN and rows:
            sql_fix = """
            UPDATE {}.dbo.movi_stock
            SET unidades = cantidad
            WHERE usuario = 'WB'
              AND numero_comprobante = 1926645
              AND codigo_comprobante = 7
              AND unidades <> cantidad
            """.format(base)
            cur.execute(sql_fix)
            print(f"    -> {cur.rowcount} registros actualizados")

    # ---- FIX 2: stock.stock_unidades = stock_actual (para los articulos del remito web) ----
    print("\n--- FIX 2: stock.stock_unidades = stock_actual ---")
    # Obtener artículos afectados
    for base in ['msgestion01', 'msgestion03']:
        sql_arts = """
        SELECT DISTINCT articulo
        FROM {}.dbo.movi_stock
        WHERE usuario = 'WB'
          AND numero_comprobante = 1926645
          AND codigo_comprobante = 7
        """.format(base)
        cur.execute(sql_arts)
        articulos = [r.articulo for r in cur.fetchall()]
        print(f"  {base}: {len(articulos)} articulos a verificar")

        for art in articulos:
            sql_stk = """
            SELECT deposito, articulo, serie, stock_actual, stock_unidades
            FROM {}.dbo.stock
            WHERE articulo = {} AND deposito = 11
              AND stock_actual <> stock_unidades
            """.format(base, int(art))
            cur.execute(sql_stk)
            bad = cur.fetchall()
            for b in bad:
                print(f"    art={b.articulo} serie='{b.serie}' actual={b.stock_actual} unidades={b.stock_unidades} -> unidades={b.stock_actual}")

            if not DRY_RUN and bad:
                sql_fix_stk = """
                UPDATE {}.dbo.stock
                SET stock_unidades = stock_actual
                WHERE articulo = {} AND deposito = 11
                  AND stock_actual <> stock_unidades
                """.format(base, int(art))
                cur.execute(sql_fix_stk)
                print(f"    -> {cur.rowcount} filas stock actualizadas")

    if DRY_RUN:
        print("\n*** DRY RUN — no se aplicaron cambios ***")
        print("*** Ejecutar con: py -3 fix_movi_stock_pira.py --ejecutar ***")
        conn.rollback()
    else:
        conn.commit()
        print("\n*** CAMBIOS APLICADOS ***")

    conn.close()

if __name__ == '__main__':
    main()
