#!/usr/bin/env python3
"""
fix_stock_footy_rev.py
======================
REVERSA: Mueve stock de dep 0 → dep 11 para artículos del pedido Footy #1134071.
El fix anterior lo puso en dep 0 por error, el usuario lo quiere en dep 11 con serie vacía.

Para PPX3941: tenía 20 pares pre-existentes en dep 0 (4,5,4,4,3).
Solo mover los 18 que vinieron del pedido, dejar los 20 originales.

Ejecutar en 111: py -3 fix_stock_footy_rev.py [--ejecutar]
"""

import sys
import pyodbc

DRY_RUN = "--ejecutar" not in sys.argv

# Stock original que PPX3941 tenía en dep 0 ANTES del fix (no mover estos)
PPX3941_ORIGINAL_DEP0 = {
    344898: 4,
    344899: 5,
    344900: 4,
    344901: 4,
    344902: 3,
}

# Todos los artículos del pedido Footy #1134071
ARTS_PEDIDO = [
    # AV0455
    360871,360872,360873,360874,360875,360876,360877,
    # FRZ3152
    360797,360798,360799,360800,360801,360802,
    # LT2451
    360807,360808,360809,360810,360811,360812,360813,
    # PFRZ6110
    360803,360804,360805,360806,
    # PPP6123
    360721,360722,360723,360724,
    # PPP6124
    360725,360726,360727,360728,
    # PPX3941 (viejos)
    344898,344899,344900,344901,344902,
    # PPX3953
    360716,360717,360718,360719,360720,
    # PPX5947 (viejos)
    351759,351760,351761,351762,351763,
    # PPX938 (viejos)
    146119,146120,146121,146122,146123,
    # PPX942 (viejos)
    351770,351771,351772,351773,351774,
    # PSP6118
    360859,360860,360861,360862,360863,360864,
    # PSP6119
    360865,360866,360867,360868,360869,360870,
    # PST6113
    360779,360780,360781,360782,360783,360784,
    # PST6115
    360785,360786,360787,360788,360789,360790,
    # PST6116
    360791,360792,360793,360794,360795,360796,
    # PWX3585 (viejos)
    344904,344905,344906,344907,344983,344984,
    # SP0689
    360853,360854,360855,360856,360857,360858,
    # SP3695
    360841,360842,360843,360844,360845,360846,
    # SP3696
    360835,360836,360837,360838,360839,360840,
    # SP3697
    360847,360848,360849,360850,360851,360852,
    # SP5612
    360821,360822,360823,360824,360825,360826,360827,
    # SP5613
    360814,360815,360816,360817,360818,360819,360820,
    # SP5690 (viejos AZUL + nuevos ROJO)
    351752,351753,351754,351755,351756,360828,360829,
    # ST2897
    360742,360743,360744,360745,360746,360747,360748,
    # ST2898
    360735,360736,360737,360738,360739,360740,360741,
    # ST3889
    360755,360756,360757,360758,360759,360760,
    # ST3891
    360749,360750,360751,360752,360753,360754,
    # ST5877
    360761,360762,360763,360764,360765,360766,
    # ST879
    360773,360774,360775,360776,360777,360778,
    # ST881
    360767,360768,360769,360770,360771,360772,
]


def get_stock(cursor, base, articulo, deposito, serie):
    cursor.execute(f"""
        SELECT stock_actual FROM {base}.dbo.stock
        WHERE articulo = ? AND deposito = ? AND serie = ?
    """, articulo, deposito, serie)
    row = cursor.fetchone()
    return row.stock_actual if row else None


def stock_exists(cursor, base, articulo, deposito, serie):
    cursor.execute(f"""
        SELECT 1 FROM {base}.dbo.stock
        WHERE articulo = ? AND deposito = ? AND serie = ?
    """, articulo, deposito, serie)
    return cursor.fetchone() is not None


def update_stock(cursor, base, articulo, deposito, serie, nuevo_valor):
    cursor.execute(f"""
        UPDATE {base}.dbo.stock
        SET stock_actual = ?
        WHERE articulo = ? AND deposito = ? AND serie = ?
    """, nuevo_valor, articulo, deposito, serie)
    return cursor.rowcount


def insert_stock(cursor, base, articulo, deposito, serie, stock):
    cursor.execute(f"""
        INSERT INTO {base}.dbo.stock (articulo, deposito, serie, stock_actual)
        VALUES (?, ?, ?, ?)
    """, articulo, deposito, serie, stock)


def main():
    print("=" * 70)
    print("REVERSA: Mover stock dep 0 → dep 11 — Pedido Footy #1134071")
    print(f"Modo: {'DRY RUN' if DRY_RUN else '*** EJECUTAR ***'}")
    print("=" * 70)

    conn_str = "DRIVER={SQL Server};SERVER=192.168.2.111;UID=am;PWD=dl"
    conn = pyodbc.connect(conn_str, timeout=15)
    cursor = conn.cursor()

    base = "msgestion03"
    serie = " "
    stats = {"movidos": 0, "ppx3941_parcial": 0, "sin_stock": 0}

    for art in ARTS_PEDIDO:
        stock_dep0 = get_stock(cursor, base, art, 0, serie)
        if stock_dep0 is None or stock_dep0 <= 0:
            continue

        # Para PPX3941: dejar el stock original en dep 0
        if art in PPX3941_ORIGINAL_DEP0:
            original = PPX3941_ORIGINAL_DEP0[art]
            a_mover = stock_dep0 - original
            if a_mover <= 0:
                print(f"  SKIP Art {art} (PPX3941): dep0={stock_dep0}, "
                      f"original={original} → nada que mover")
                continue
            nuevo_dep0 = original
            print(f"  PPX3941 Art {art}: dep0={stock_dep0} → "
                  f"dep0={nuevo_dep0} + dep11={a_mover}")
            stats["ppx3941_parcial"] += 1
        else:
            a_mover = stock_dep0
            nuevo_dep0 = 0
            print(f"  XFER Art {art}: dep0={stock_dep0} → dep11={a_mover}")

        if not DRY_RUN:
            # Actualizar dep 0
            update_stock(cursor, base, art, 0, serie, nuevo_dep0)

            # Sumar a dep 11
            stock_dep11 = get_stock(cursor, base, art, 11, serie)
            dep11_exists = stock_exists(cursor, base, art, 11, serie)
            nuevo_dep11 = (stock_dep11 or 0) + a_mover

            if dep11_exists:
                update_stock(cursor, base, art, 11, serie, nuevo_dep11)
            else:
                insert_stock(cursor, base, art, 11, serie, nuevo_dep11)

        stats["movidos"] += 1

    if not DRY_RUN:
        conn.commit()
        print("\n✓ COMMIT OK")

    print(f"\n{'='*70}")
    print(f"RESUMEN:")
    print(f"  Artículos movidos dep 0 → dep 11: {stats['movidos']}")
    print(f"  PPX3941 parcial (dejando original en dep 0): {stats['ppx3941_parcial']}")
    print(f"{'='*70}")

    if DRY_RUN:
        print("\n⚠ DRY RUN — ejecutar con: py -3 fix_stock_footy_rev.py --ejecutar")

    conn.close()


if __name__ == "__main__":
    main()
