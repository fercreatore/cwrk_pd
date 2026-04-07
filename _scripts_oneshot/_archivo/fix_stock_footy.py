#!/usr/bin/env python3
"""
fix_stock_footy.py
==================
Corrige problemas de stock en artículos del pedido Footy #1134071.

Problemas detectados:
  A) Artículos nuevos con stock en dep 11 que nunca pasaron a dep 0
  B) PPX938 con stock DUPLICADO en dep 11 (serie ' ' y serie '26030001' iguales)
  C) Artículos viejos con stock nuevo en dep 11 serie '26030001' (real, no dup)

Fix:
  1. Para serie '26030001': si ya existe serie ' ' con stock > 0 en mismo dep+art
     → es DUPLICADO → poner '26030001' en 0
  2. Para serie '26030001': si NO hay serie ' ' con stock > 0
     → es stock REAL → mover a serie ' ' (sumar si existe con 0, crear si no)
  3. Mover stock de dep 11 serie ' ' → dep 0 serie ' '
     (sumar a dep 0 si ya tiene, restar de dep 11)

Ejecutar en 111: py -3 fix_stock_footy.py [--ejecutar]
"""

import sys
import pyodbc

DRY_RUN = "--ejecutar" not in sys.argv

# Artículos del pedido Footy #1134071 — todos
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

# Bases donde operar (msg03 = H4)
BASES = ["msgestion03"]


def get_stock(cursor, base, articulo, deposito, serie):
    """Obtiene stock_actual de un registro específico."""
    cursor.execute(f"""
        SELECT stock_actual FROM {base}.dbo.stock
        WHERE articulo = ? AND deposito = ? AND serie = ?
    """, articulo, deposito, serie)
    row = cursor.fetchone()
    return row.stock_actual if row else None


def stock_exists(cursor, base, articulo, deposito, serie):
    """Verifica si existe el registro de stock (aunque sea 0)."""
    cursor.execute(f"""
        SELECT 1 FROM {base}.dbo.stock
        WHERE articulo = ? AND deposito = ? AND serie = ?
    """, articulo, deposito, serie)
    return cursor.fetchone() is not None


def update_stock(cursor, base, articulo, deposito, serie, nuevo_valor):
    """Actualiza stock_actual."""
    cursor.execute(f"""
        UPDATE {base}.dbo.stock
        SET stock_actual = ?
        WHERE articulo = ? AND deposito = ? AND serie = ?
    """, nuevo_valor, articulo, deposito, serie)
    return cursor.rowcount


def insert_stock(cursor, base, articulo, deposito, serie, stock):
    """Inserta registro de stock si no existe."""
    cursor.execute(f"""
        INSERT INTO {base}.dbo.stock (articulo, deposito, serie, stock_actual)
        VALUES (?, ?, ?, ?)
    """, articulo, deposito, serie, stock)


def main():
    print("=" * 70)
    print("FIX STOCK FOOTY — Pedido #1134071")
    print(f"Modo: {'DRY RUN' if DRY_RUN else '*** EJECUTAR ***'}")
    print("=" * 70)

    conn_str = "DRIVER={SQL Server};SERVER=192.168.2.111;UID=am;PWD=dl"
    conn = pyodbc.connect(conn_str, timeout=15)
    cursor = conn.cursor()

    serie_remito = "26030001"
    serie_normal = " "

    stats = {
        "duplicados_eliminados": 0,
        "series_consolidadas": 0,
        "transferidos_a_dep0": 0,
        "sin_stock": 0,
    }

    for base in BASES:
        print(f"\n{'='*70}")
        print(f"BASE: {base}")
        print(f"{'='*70}")

        # ── FASE 1: Limpiar serie '26030001' ──
        print(f"\n── FASE 1: Consolidar serie '{serie_remito}' ──")

        for art in ARTS_PEDIDO:
            # Buscar stock con serie remito en dep 11
            stock_remito = get_stock(cursor, base, art, 11, serie_remito)
            if stock_remito is None or stock_remito <= 0:
                continue

            # Ver si hay stock en serie normal en dep 11
            stock_normal = get_stock(cursor, base, art, 11, serie_normal)

            if stock_normal is not None and stock_normal > 0:
                # DUPLICADO: ya hay stock en serie normal → eliminar serie remito
                print(f"  DUP  Art {art}: dep11 serie ' '={stock_normal}, "
                      f"serie '{serie_remito}'={stock_remito} → eliminar remito")
                if not DRY_RUN:
                    update_stock(cursor, base, art, 11, serie_remito, 0)
                stats["duplicados_eliminados"] += 1
            else:
                # NO DUPLICADO: stock real → mover a serie normal
                if stock_normal is not None:
                    # Existe registro con 0 → actualizar
                    print(f"  CONS Art {art}: dep11 serie '{serie_remito}'={stock_remito} "
                          f"→ serie ' ' (update)")
                    if not DRY_RUN:
                        update_stock(cursor, base, art, 11, serie_normal, stock_remito)
                        update_stock(cursor, base, art, 11, serie_remito, 0)
                elif stock_exists(cursor, base, art, 11, serie_normal):
                    print(f"  CONS Art {art}: dep11 serie '{serie_remito}'={stock_remito} "
                          f"→ serie ' ' (update from 0)")
                    if not DRY_RUN:
                        update_stock(cursor, base, art, 11, serie_normal, stock_remito)
                        update_stock(cursor, base, art, 11, serie_remito, 0)
                else:
                    # No existe registro → insertar
                    print(f"  CONS Art {art}: dep11 serie '{serie_remito}'={stock_remito} "
                          f"→ serie ' ' (insert)")
                    if not DRY_RUN:
                        insert_stock(cursor, base, art, 11, serie_normal, stock_remito)
                        update_stock(cursor, base, art, 11, serie_remito, 0)
                stats["series_consolidadas"] += 1

        # ── FASE 2: Mover dep 11 → dep 0 ──
        print(f"\n── FASE 2: Transferir dep 11 → dep 0 (serie ' ') ──")

        for art in ARTS_PEDIDO:
            stock_dep11 = get_stock(cursor, base, art, 11, serie_normal)
            if stock_dep11 is None or stock_dep11 <= 0:
                # Sin stock en dep 11
                continue

            stock_dep0 = get_stock(cursor, base, art, 0, serie_normal)
            dep0_exists = stock_exists(cursor, base, art, 0, serie_normal)

            nuevo_dep0 = (stock_dep0 or 0) + stock_dep11

            print(f"  XFER Art {art}: dep11={stock_dep11} → dep0 "
                  f"(era {stock_dep0 or 0}, queda {nuevo_dep0})")

            if not DRY_RUN:
                if dep0_exists:
                    update_stock(cursor, base, art, 0, serie_normal, nuevo_dep0)
                else:
                    insert_stock(cursor, base, art, 0, serie_normal, nuevo_dep0)
                update_stock(cursor, base, art, 11, serie_normal, 0)

            stats["transferidos_a_dep0"] += 1

    if not DRY_RUN:
        conn.commit()
        print("\n✓ COMMIT OK")

    print(f"\n{'='*70}")
    print(f"RESUMEN:")
    print(f"  Duplicados eliminados (serie '26030001'): {stats['duplicados_eliminados']}")
    print(f"  Series consolidadas ('26030001' → ' '): {stats['series_consolidadas']}")
    print(f"  Transferidos dep 11 → dep 0: {stats['transferidos_a_dep0']}")
    print(f"{'='*70}")

    if DRY_RUN:
        print("\n⚠ DRY RUN — ejecutar con: py -3 fix_stock_footy.py --ejecutar")

    conn.close()


if __name__ == "__main__":
    main()
