#!/usr/bin/env python3
"""
fix_go_dance_post_delete.py — Limpieza de GO DANCE 342510 después de
borrar el remito 11112023 desde el ejecutable del ERP.

CONTEXTO:
El remito se creó con el código WEB viejo que:
- Puso serie='2603' en movi_stock (msg03 debería usar serie=' ')
- Actualizó stock en AMBAS series (doble conteo: '2603' y ' ')
- Puso unidades=1 en movi_stock (debería ser 39)

Cuando el ejecutable borre el remito, va a revertir lo que encuentre
en movi_stock (serie '2603'), pero NO va a tocar la serie ' ' que
nuestro código agregó de más.

Este script limpia lo que el ejecutable NO limpia:
1. Restar 39 de stock serie ' ' dep 11 (el doble conteo del WB)
2. Eliminar/cerar fila serie '2603' si el ejecutable la dejó
3. Fix stock_unidades donde no matchee stock_actual

Ejecutar en 111 con: py -3 fix_go_dance_post_delete.py
EJECUTAR DESPUÉS de borrar el remito desde el ejecutable.
"""
import pyodbc

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=localhost;"
    "UID=am;PWD=dl;"
    "TrustServerCertificate=yes;"
)

ART = 342510  # GO DANCE NEGRO/NEGRO
DEP = 11
CANT_WB = 39  # cantidad del remito WB


def run():
    conn = pyodbc.connect(CONN_STR, autocommit=False)
    cur = conn.cursor()

    print("=" * 60)
    print(f"FIX GO DANCE {ART} — POST BORRADO EJECUTABLE")
    print("=" * 60)

    # Ver estado actual
    print("\n--- Estado actual stock msg03 dep 11 ---")
    cur.execute("""
        SELECT serie, stock_actual, stock_unidades
        FROM msgestion03.dbo.stock
        WHERE articulo = ? AND deposito = ?
        ORDER BY serie
    """, ART, DEP)
    rows = cur.fetchall()
    for serie, stk, stku in rows:
        s = serie.strip() or '(espacio)'
        print(f"  serie '{s}': stock_actual={stk}, stock_unidades={stku}")

    # 1. Restar doble conteo de serie ' '
    print(f"\n--- Restando {CANT_WB} de serie ' ' (doble conteo WB) ---")
    cur.execute("""
        SELECT stock_actual, stock_unidades
        FROM msgestion03.dbo.stock
        WHERE articulo = ? AND deposito = ? AND serie = ' '
    """, ART, DEP)
    row = cur.fetchone()
    if row:
        stk, stku = row
        new_stk = stk - CANT_WB
        print(f"  serie ' ': {stk} -> {new_stk}")
        cur.execute("""
            UPDATE msgestion03.dbo.stock
            SET stock_actual = stock_actual - ?,
                stock_unidades = stock_unidades - ?
            WHERE articulo = ? AND deposito = ? AND serie = ' '
        """, CANT_WB, CANT_WB, ART, DEP)
    else:
        print("  No existe fila serie ' ' — nada que hacer")

    # 2. Limpiar serie '2603' si quedó
    print("\n--- Limpiando serie '2603' residual ---")
    cur.execute("""
        SELECT stock_actual, stock_unidades
        FROM msgestion03.dbo.stock
        WHERE articulo = ? AND deposito = ? AND serie = '2603'
    """, ART, DEP)
    row = cur.fetchone()
    if row:
        stk, stku = row
        if stk == 0:
            print(f"  serie '2603': stock=0 -> DELETE")
            cur.execute("""
                DELETE FROM msgestion03.dbo.stock
                WHERE articulo = ? AND deposito = ? AND serie = '2603'
            """, ART, DEP)
        else:
            print(f"  serie '2603': stock={stk} -> SET 0 (residuo)")
            cur.execute("""
                UPDATE msgestion03.dbo.stock
                SET stock_actual = 0, stock_unidades = 0
                WHERE articulo = ? AND deposito = ? AND serie = '2603'
            """, ART, DEP)
    else:
        print("  No existe fila serie '2603' — ya limpia")

    # 3. Verificar resultado
    print("\n--- Resultado final ---")
    cur.execute("""
        SELECT serie, stock_actual, stock_unidades
        FROM msgestion03.dbo.stock
        WHERE articulo = ? AND deposito = ?
        ORDER BY serie
    """, ART, DEP)
    rows = cur.fetchall()
    for serie, stk, stku in rows:
        s = serie.strip() or '(espacio)'
        ok = "OK" if stk == stku else "WARN: unidades != actual"
        print(f"  serie '{s}': stock_actual={stk}, stock_unidades={stku} {ok}")

    print("\n" + "=" * 60)
    resp = input("Aplicar cambios? (s/n): ").strip().lower()
    if resp == 's':
        conn.commit()
        print("COMMIT OK")
    else:
        conn.rollback()
        print("ROLLBACK")

    cur.close()
    conn.close()


if __name__ == '__main__':
    run()
