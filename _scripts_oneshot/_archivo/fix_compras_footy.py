#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_compras_footy.py
====================
Corrige el remito R #12867 (TIVORY/FOOTY 12/03/2026) que referencia
artículos nuevos ya eliminados por fix_duplicados_footy.py.

Acciones:
1. UPDATE compras1: reasigna artículos del remito a códigos viejos
2. UPDATE stock: restaura stock para PPX938 (146119-146123) que quedó en 0

Ejecutar en 111 con: py -3 fix_compras_footy.py
"""

import pyodbc

CONN_STR = "DRIVER={SQL Server};SERVER=192.168.2.111;UID=am;PWD=dl"

# Remito a corregir
REMITO_NUM = 12867
REMITO_LETRA = 'R'
REMITO_CODIGO = 7
REMITO_SUCURSAL = 1

# Mismo mapeo que fix_duplicados_footy.py: nuevo → viejo
MAPEO = {
    # PPX3941 LILA — talles 22-26
    360696: 344898, 360697: 344899, 360698: 344900, 360699: 344901, 360700: 344902,
    # PPX938 ROSA — talles 22-26
    360701: 146119, 360702: 146120, 360703: 146121, 360704: 146122, 360705: 146123,
    # PPX942 ROSA — talles 22-26
    360706: 351770, 360707: 351771, 360708: 351772, 360709: 351773, 360710: 351774,
    # PPX5947 ROSA — talles 22-26
    360711: 351759, 360712: 351760, 360713: 351761, 360714: 351762, 360715: 351763,
    # PWX3585 GRIS — talles 23-28
    360729: 344904, 360730: 344905, 360731: 344906, 360732: 344907, 360733: 344983, 360734: 344984,
    # SP5690 ROJO — talles 26-30
    360830: 351752, 360831: 351753, 360832: 351754, 360833: 351755, 360834: 351756,
}

# Cantidades del remito para restaurar stock de PPX938 (los únicos en 0)
STOCK_PPX938 = {
    146119: 2,  # T22
    146120: 3,  # T23
    146121: 3,  # T24
    146122: 2,  # T25
    146123: 2,  # T26
}

DEPOSITO = 11  # Depósito principal


def main():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    print("=" * 60)
    print("FIX COMPRAS FOOTY — Remito R #12867")
    print("=" * 60)

    codigos_nuevos = list(MAPEO.keys())

    # ── PASO 1: Verificar estado actual del remito ──
    print("\n── PASO 1: Verificar renglones afectados en compras1 ──")
    cursor.execute("""
        SELECT renglon, articulo, descripcion, cantidad
        FROM MSGESTION03.dbo.compras1
        WHERE numero = ? AND letra = ? AND codigo = ? AND sucursal = ?
        AND articulo IN ({})
    """.format(",".join("?" * len(codigos_nuevos))),
        [REMITO_NUM, REMITO_LETRA, REMITO_CODIGO, REMITO_SUCURSAL] + codigos_nuevos)

    renglones = cursor.fetchall()
    print(f"Renglones con códigos nuevos: {len(renglones)}")

    if len(renglones) == 0:
        print("No hay renglones con códigos nuevos — ya fue corregido o no aplica.")
        conn.close()
        return

    for r in renglones:
        viejo = MAPEO.get(r.articulo, "???")
        print(f"  Renglón {r.renglon}: {r.articulo} → {viejo} | {r.descripcion} | qty={r.cantidad}")

    # ── PASO 2: UPDATE compras1 — reasignar artículos ──
    print("\n── PASO 2: UPDATE compras1 — reasignar a códigos viejos ──")
    updates_ok = 0
    for cod_nuevo, cod_viejo in MAPEO.items():
        cursor.execute("""
            UPDATE MSGESTION03.dbo.compras1
            SET articulo = ?
            WHERE numero = ? AND letra = ? AND codigo = ? AND sucursal = ?
            AND articulo = ?
        """, cod_viejo, REMITO_NUM, REMITO_LETRA, REMITO_CODIGO, REMITO_SUCURSAL, cod_nuevo)
        if cursor.rowcount > 0:
            updates_ok += cursor.rowcount
            print(f"  OK: {cod_nuevo} → {cod_viejo}")

    print(f"Total renglones actualizados: {updates_ok}")

    # ── PASO 3: Restaurar stock PPX938 ──
    print("\n── PASO 3: Restaurar stock PPX938 (deposito {}) ──".format(DEPOSITO))
    for articulo, cantidad in STOCK_PPX938.items():
        # Verificar stock actual
        cursor.execute("""
            SELECT stock_actual FROM MSGESTION03.dbo.stock
            WHERE articulo = ? AND deposito = ?
        """, articulo, DEPOSITO)
        row = cursor.fetchone()

        if row is None:
            # No existe registro de stock — crear
            cursor.execute("""
                INSERT INTO MSGESTION03.dbo.stock (articulo, deposito, stock_actual)
                VALUES (?, ?, ?)
            """, articulo, DEPOSITO, cantidad)
            print(f"  INSERT {articulo}: stock={cantidad} (no existía)")
        elif row.stock_actual == 0:
            cursor.execute("""
                UPDATE MSGESTION03.dbo.stock
                SET stock_actual = stock_actual + ?
                WHERE articulo = ? AND deposito = ?
            """, cantidad, articulo, DEPOSITO)
            print(f"  UPDATE {articulo}: 0 → {cantidad}")
        else:
            print(f"  SKIP {articulo}: ya tiene stock={row.stock_actual} (no toco)")

    # ── COMMIT ──
    conn.commit()
    print("\n✓ COMMIT OK")

    # ── PASO 4: Verificación ──
    print("\n── PASO 4: Verificación ──")

    # Verificar que no quedan códigos nuevos en compras1
    cursor.execute("""
        SELECT COUNT(*) FROM MSGESTION03.dbo.compras1
        WHERE numero = ? AND letra = ? AND codigo = ? AND sucursal = ?
        AND articulo IN ({})
    """.format(",".join("?" * len(codigos_nuevos))),
        [REMITO_NUM, REMITO_LETRA, REMITO_CODIGO, REMITO_SUCURSAL] + codigos_nuevos)
    restantes = cursor.fetchone()[0]
    print(f"  Códigos nuevos en remito: {restantes} (debe ser 0)")

    # Verificar stock PPX938
    for articulo, esperado in STOCK_PPX938.items():
        cursor.execute("""
            SELECT stock_actual FROM MSGESTION03.dbo.stock
            WHERE articulo = ? AND deposito = ?
        """, articulo, DEPOSITO)
        row = cursor.fetchone()
        actual = row.stock_actual if row else 0
        ok = "✓" if actual >= esperado else "✗"
        print(f"  {ok} Stock {articulo}: {actual} (esperado >= {esperado})")

    if restantes == 0:
        print("\n✅ FIX COMPRAS COMPLETO")
    else:
        print("\n⚠️ REVISAR — Quedan códigos nuevos en compras1")

    conn.close()


if __name__ == "__main__":
    main()
