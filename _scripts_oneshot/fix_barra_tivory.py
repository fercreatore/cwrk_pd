#!/usr/bin/env python3
"""
fix_barra_tivory.py
Popula codigo_barra para artículos de Tivory (proveedor 950) que no lo tienen.
Los sinónimos nuevos son 100% numéricos (ej: 950039531922),
así que codigo_barra = CAST(codigo_sinonimo AS BIGINT).

Ejecutar en 111: py -3 fix_barra_tivory.py [--ejecutar]
"""

import sys
import pyodbc

DRY_RUN = "--ejecutar" not in sys.argv

CONN = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion01art;"
    "UID=am;PWD=dl;"
    "Connection Timeout=15"
)

def main():
    print("=" * 60)
    print("FIX CODIGO_BARRA — TIVORY (proveedor 950)")
    print(f"Modo: {'DRY RUN (sin cambios)' if DRY_RUN else 'EJECUTAR'}")
    print("=" * 60)

    conn = pyodbc.connect(CONN, timeout=15)
    cursor = conn.cursor()

    # Buscar artículos de Tivory sin codigo_barra con sinónimo numérico
    cursor.execute("""
        SELECT codigo, codigo_sinonimo, descripcion_1
        FROM msgestion01art.dbo.articulo
        WHERE proveedor = 950
          AND (codigo_barra IS NULL OR codigo_barra = 0)
          AND codigo_sinonimo IS NOT NULL
          AND RTRIM(codigo_sinonimo) != ''
          AND ISNUMERIC(RTRIM(codigo_sinonimo)) = 1
        ORDER BY codigo
    """)

    rows = cursor.fetchall()
    print(f"\nArtículos sin barra con sinónimo numérico: {rows.__len__()}")

    if not rows:
        print("No hay artículos para actualizar.")
        conn.close()
        return

    actualizados = 0
    errores = 0

    for row in rows:
        codigo = row.codigo
        sinonimo = row.codigo_sinonimo.strip()
        desc = row.descripcion_1.strip()[:50] if row.descripcion_1 else ""

        try:
            barra = int(sinonimo)
        except ValueError:
            print(f"  SKIP {codigo}: sinónimo '{sinonimo}' no es numérico")
            errores += 1
            continue

        if DRY_RUN:
            print(f"  [DRY] Art {codigo:>7} | {desc:50} | barra → {barra}")
        else:
            cursor.execute("""
                UPDATE msgestion01art.dbo.articulo
                SET codigo_barra = ?
                WHERE codigo = ?
            """, barra, codigo)
            print(f"  OK   Art {codigo:>7} | {desc:50} | barra = {barra}")

        actualizados += 1

    if not DRY_RUN:
        conn.commit()

    print(f"\n{'='*60}")
    print(f"Actualizados: {actualizados}")
    print(f"Errores: {errores}")
    if DRY_RUN:
        print("\n⚠ DRY RUN — ejecutar con: py -3 fix_barra_tivory.py --ejecutar")

    conn.close()


if __name__ == "__main__":
    main()
