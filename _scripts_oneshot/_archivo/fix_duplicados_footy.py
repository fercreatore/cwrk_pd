#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_duplicados_footy.py
=======================
Corrige artículos duplicados FOOTY en pedido #1134071.
6 modelos tienen artículos viejos (ya existían) y nuevos (creados por error).
Incluye viejos con proveedor=139 (FOOTY viejo) y proveedor=950 (TIVORY).

Acciones:
1. UPDATE pedico1: reasigna renglones del pedido a los códigos viejos
2. DELETE artículos nuevos duplicados de msgestion01art.dbo.articulo
3. DELETE stock entries de los artículos nuevos duplicados

Ejecutar en 111 con: py -3 fix_duplicados_footy.py
"""

import pyodbc

CONN_STR = "DRIVER={SQL Server};SERVER=192.168.2.111;UID=am;PWD=dl"
PEDIDO_NUM = 1134071

# Mapeo: código_nuevo → código_viejo (mismo modelo+talle)
MAPEO = {
    # PPX3941 LILA — talles 22-26 (viejos con prov=139)
    360696: 344898,  # T22
    360697: 344899,  # T23
    360698: 344900,  # T24
    360699: 344901,  # T25
    360700: 344902,  # T26
    # PPX938 ROSA — talles 22-26 (viejos con prov=139)
    360701: 146119,  # T22
    360702: 146120,  # T23
    360703: 146121,  # T24
    360704: 146122,  # T25
    360705: 146123,  # T26
    # PPX942 ROSA — talles 22-26 (viejos con prov=139)
    360706: 351770,  # T22
    360707: 351771,  # T23
    360708: 351772,  # T24
    360709: 351773,  # T25
    360710: 351774,  # T26
    # PPX5947 ROSA — talles 22-26 (viejos con prov=139)
    360711: 351759,  # T22
    360712: 351760,  # T23
    360713: 351761,  # T24
    360714: 351762,  # T25
    360715: 351763,  # T26
    # PWX3585 GRIS — talles 23-28 (viejos con prov=139)
    360729: 344904,  # T23
    360730: 344905,  # T24
    360731: 344906,  # T25
    360732: 344907,  # T26
    360733: 344983,  # T27
    360734: 344984,  # T28
    # SP5690 ROJO — talles 26-30 (viejos con prov=950)
    360830: 351752,  # T26
    360831: 351753,  # T27
    360832: 351754,  # T28
    360833: 351755,  # T29
    360834: 351756,  # T30
}

CODIGOS_NUEVOS = list(MAPEO.keys())


def main():
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    print("=" * 60)
    print("FIX DUPLICADOS FOOTY — Pedido #1134071")
    print("=" * 60)

    # ── PASO 1: Verificar estado actual del pedido ──
    print("\n── PASO 1: Verificar renglones afectados ──")
    cursor.execute("""
        SELECT renglon, articulo, descripcion, cantidad
        FROM MSGESTION03.dbo.pedico1
        WHERE numero = ? AND codigo = 8 AND articulo IN ({})
    """.format(",".join("?" * len(CODIGOS_NUEVOS))),
        [PEDIDO_NUM] + CODIGOS_NUEVOS)

    renglones = cursor.fetchall()
    EXPECTED = len(MAPEO)  # 31 renglones
    print(f"Renglones a reasignar: {len(renglones)} (esperados: {EXPECTED})")
    if len(renglones) != EXPECTED:
        print(f"AVISO: Se esperaban {EXPECTED} renglones, hay {len(renglones)}. Continuando igual...")
        # No abortamos — puede que el fix ya se haya corrido parcialmente

    for r in renglones:
        nuevo = r.articulo
        viejo = MAPEO[nuevo]
        print(f"  Renglón {r.renglon}: {nuevo} → {viejo} | {r.descripcion} | qty={r.cantidad}")

    # ── PASO 2: UPDATE pedico1 — reasignar artículos ──
    print("\n── PASO 2: UPDATE pedico1 — reasignar a códigos viejos ──")
    updates_ok = 0
    for cod_nuevo, cod_viejo in MAPEO.items():
        cursor.execute("""
            UPDATE MSGESTION03.dbo.pedico1
            SET articulo = ?
            WHERE numero = ? AND codigo = 8 AND articulo = ?
        """, cod_viejo, PEDIDO_NUM, cod_nuevo)
        if cursor.rowcount > 0:
            updates_ok += cursor.rowcount
            print(f"  OK: {cod_nuevo} → {cod_viejo} ({cursor.rowcount} renglón)")
        else:
            print(f"  SKIP: {cod_nuevo} — no encontrado en pedido")

    print(f"Total renglones actualizados: {updates_ok}")

    # ── PASO 3: DELETE stock de artículos duplicados ──
    print("\n── PASO 3: DELETE stock de artículos duplicados ──")
    for base in ["MSGESTION01", "MSGESTION03"]:
        cursor.execute("""
            DELETE FROM {}.dbo.stock WHERE articulo IN ({})
        """.format(base, ",".join("?" * len(CODIGOS_NUEVOS))),
            CODIGOS_NUEVOS)
        print(f"  {base}.dbo.stock: {cursor.rowcount} registros eliminados")

    # ── PASO 4: DELETE artículos duplicados ──
    print("\n── PASO 4: DELETE artículos duplicados de msgestion01art ──")
    cursor.execute("""
        DELETE FROM msgestion01art.dbo.articulo WHERE codigo IN ({})
    """.format(",".join("?" * len(CODIGOS_NUEVOS))),
        CODIGOS_NUEVOS)
    print(f"  Artículos eliminados: {cursor.rowcount}")

    # ── COMMIT ──
    conn.commit()
    print("\n✓ COMMIT OK")

    # ── PASO 5: Verificación final ──
    print("\n── PASO 5: Verificación ──")

    # Verificar que no quedan códigos nuevos en el pedido
    cursor.execute("""
        SELECT COUNT(*) FROM MSGESTION03.dbo.pedico1
        WHERE numero = ? AND codigo = 8 AND articulo IN ({})
    """.format(",".join("?" * len(CODIGOS_NUEVOS))),
        [PEDIDO_NUM] + CODIGOS_NUEVOS)
    restantes = cursor.fetchone()[0]
    print(f"  Códigos nuevos en pedido: {restantes} (debe ser 0)")

    # Verificar que los viejos están en el pedido
    codigos_viejos = list(MAPEO.values())
    cursor.execute("""
        SELECT COUNT(*) FROM MSGESTION03.dbo.pedico1
        WHERE numero = ? AND codigo = 8 AND articulo IN ({})
    """.format(",".join("?" * len(codigos_viejos))),
        [PEDIDO_NUM] + codigos_viejos)
    viejos_ok = cursor.fetchone()[0]
    print(f"  Códigos viejos en pedido: {viejos_ok} (debe ser {EXPECTED})")

    # Verificar que los duplicados ya no existen
    cursor.execute("""
        SELECT COUNT(*) FROM msgestion01art.dbo.articulo
        WHERE codigo IN ({})
    """.format(",".join("?" * len(CODIGOS_NUEVOS))),
        CODIGOS_NUEVOS)
    arts_restantes = cursor.fetchone()[0]
    print(f"  Artículos duplicados restantes: {arts_restantes} (debe ser 0)")

    # Totales del pedido
    cursor.execute("""
        SELECT COUNT(*) as renglones, SUM(cantidad) as pares, SUM(cantidad * precio) as monto
        FROM MSGESTION03.dbo.pedico1
        WHERE numero = ? AND codigo = 8
    """, PEDIDO_NUM)
    row = cursor.fetchone()
    print(f"  Pedido #1134071: {row.renglones} renglones, {row.pares} pares, ${row.monto:,.0f}")

    if restantes == 0 and viejos_ok == EXPECTED and arts_restantes == 0:
        print("\n✅ FIX COMPLETO — Todo correcto")
    else:
        print("\n⚠️ REVISAR — Alguna verificación no pasó")

    conn.close()


if __name__ == "__main__":
    main()
