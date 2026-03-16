#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_stock_series_footy.py
=========================
Restaura stock con serie "26030001" para los 31 artículos viejos
que fueron reasignados del remito R #12867.

El fix_duplicados_footy.py borró el stock (con serie) de los códigos nuevos
pero no lo recreó en los códigos viejos. Este script lo hace.

Ejecutar en 111 con: py -3 fix_stock_series_footy.py
"""

import pyodbc

CONN_STR = "DRIVER={SQL Server};SERVER=192.168.2.111;UID=am;PWD=dl"

SERIE = "26030001"
DEPOSITO = 11
FECHA_REMITO = "2026-03-12 17:21:49"  # Misma fecha que los otros arts del remito

# Artículo viejo → cantidad del remito R 12867
STOCK_REMITO = {
    # PPX3941 LILA — talles 22-26
    344898: 3,  # T22
    344899: 4,  # T23
    344900: 4,  # T24
    344901: 4,  # T25
    344902: 3,  # T26
    # PPX938 ROSA — talles 22-26
    146119: 2,  # T22
    146120: 3,  # T23
    146121: 3,  # T24
    146122: 2,  # T25
    146123: 2,  # T26
    # PPX942 ROSA — talles 22-26
    351770: 2,  # T22
    351771: 3,  # T23
    351772: 3,  # T24
    351773: 2,  # T25
    351774: 2,  # T26
    # PPX5947 ROSA — talles 22-26
    351759: 2,  # T22
    351760: 3,  # T23
    351761: 3,  # T24
    351762: 2,  # T25
    351763: 2,  # T26
    # PWX3585 GRIS — talles 23-28
    344904: 3,  # T23
    344905: 3,  # T24
    344906: 3,  # T25
    344907: 3,  # T26
    344983: 3,  # T27
    344984: 3,  # T28
    # SP5690 ROJO — talles 26-30
    351752: 2,  # T26
    351753: 2,  # T27
    351754: 2,  # T28
    351755: 1,  # T29
    351756: 1,  # T30
}


def main():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    print("=" * 60)
    print("FIX STOCK SERIES FOOTY — Serie 26030001")
    print("=" * 60)

    # ── PASO 1: Verificar estado actual ──
    print("\n── PASO 1: Verificar qué artículos ya tienen serie 26030001 ──")
    arts = list(STOCK_REMITO.keys())
    cursor.execute("""
        SELECT articulo, stock_actual FROM MSGESTION03.dbo.stock
        WHERE deposito = ? AND serie = ? AND articulo IN ({})
    """.format(",".join("?" * len(arts))),
        [DEPOSITO, SERIE] + arts)

    ya_tienen = {r.articulo: r.stock_actual for r in cursor.fetchall()}
    print(f"  Ya tienen serie {SERIE}: {len(ya_tienen)} de {len(STOCK_REMITO)}")

    # ── PASO 2: INSERT stock con serie para los que faltan ──
    print(f"\n── PASO 2: INSERT stock con serie {SERIE} ──")
    insertados = 0
    skipped = 0
    for articulo, cantidad in STOCK_REMITO.items():
        if articulo in ya_tienen:
            print(f"  SKIP {articulo}: ya tiene serie {SERIE} con stock={ya_tienen[articulo]}")
            skipped += 1
            continue

        cursor.execute("""
            INSERT INTO MSGESTION03.dbo.stock
            (deposito, articulo, stock_actual, stock_unidades, serie, fecha_hora)
            VALUES (?, ?, ?, ?, ?, ?)
        """, DEPOSITO, articulo, cantidad, cantidad, SERIE, FECHA_REMITO)
        insertados += 1
        print(f"  INSERT {articulo}: stock={cantidad}, serie={SERIE}")

    print(f"\nInsertados: {insertados} | Skipped: {skipped}")

    # ── COMMIT ──
    conn.commit()
    print("\n✓ COMMIT OK")

    # ── PASO 3: Verificación ──
    print(f"\n── PASO 3: Verificación ──")
    cursor.execute("""
        SELECT s.articulo, s.stock_actual, s.serie
        FROM MSGESTION03.dbo.stock s
        WHERE s.deposito = ? AND s.serie = ? AND s.articulo IN ({})
        ORDER BY s.articulo
    """.format(",".join("?" * len(arts))),
        [DEPOSITO, SERIE] + arts)

    ok = 0
    for r in cursor.fetchall():
        esperado = STOCK_REMITO[r.articulo]
        match = "✓" if r.stock_actual == esperado else "✗"
        if r.stock_actual == esperado:
            ok += 1
        print(f"  {match} Art {r.articulo}: stock={r.stock_actual} (esperado {esperado})")

    if ok == len(STOCK_REMITO):
        print(f"\n✅ STOCK SERIES COMPLETO — {ok}/{len(STOCK_REMITO)} OK")
    else:
        print(f"\n⚠️ REVISAR — {ok}/{len(STOCK_REMITO)} OK")

    conn.close()


if __name__ == "__main__":
    main()
