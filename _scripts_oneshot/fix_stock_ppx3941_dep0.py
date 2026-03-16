#!/usr/bin/env python3
"""
fix_stock_ppx3941_dep0.py
=========================
Pone en 0 el stock de PPX3941 BLANCO NEGRO (Tivory) en dep 0.
Artículos 344898-344902, talles 39-43.

Uso:
    py -3 fix_stock_ppx3941_dep0.py --dry-run     # Solo muestra qué haría
    py -3 fix_stock_ppx3941_dep0.py --ejecutar     # Ejecuta el UPDATE
"""

import sys
import pyodbc

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
)

ARTICULOS = [344898, 344899, 344900, 344901, 344902]
DEPOSITO = 0

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('--dry-run', '--ejecutar'):
        print("Uso: py -3 fix_stock_ppx3941_dep0.py --dry-run|--ejecutar")
        sys.exit(1)

    dry_run = sys.argv[1] == '--dry-run'
    modo = "DRY-RUN" if dry_run else "EJECUTAR"
    print(f"\n{'='*60}")
    print(f"  FIX STOCK PPX3941 DEP 0 — {modo}")
    print(f"{'='*60}")
    print(f"  Artículos: {ARTICULOS[0]}-{ARTICULOS[-1]} (5 arts, T39-T43)")
    print(f"  Depósito: {DEPOSITO}")
    print(f"  Acción: SET stock_actual = 0")
    print(f"{'='*60}\n")

    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    # 1. Verificar estado actual
    print("--- ESTADO ACTUAL ---")
    placeholders = ','.join(['?' for _ in ARTICULOS])
    cursor.execute(f"""
        SELECT s.articulo, s.deposito, s.stock_actual
        FROM msgestion03.dbo.stock s
        WHERE s.articulo IN ({placeholders})
          AND s.deposito = ?
        ORDER BY s.articulo
    """, ARTICULOS + [DEPOSITO])

    rows = cursor.fetchall()
    if not rows:
        print("  No se encontró stock para estos artículos en dep 0. Ya está limpio.")
        conn.close()
        return

    total = 0
    for r in rows:
        print(f"  Art {r.articulo} dep {r.deposito}: stock_actual = {r.stock_actual}")
        total += r.stock_actual
    print(f"  Total: {total} pares")

    # 2. Ejecutar fix
    if dry_run:
        print(f"\n--- DRY-RUN: Se haría UPDATE stock SET stock_actual=0 ---")
        print(f"  WHERE articulo IN ({ARTICULOS[0]}..{ARTICULOS[-1]}) AND deposito={DEPOSITO}")
        print(f"  Afectaría {len(rows)} registros")
    else:
        print(f"\n--- EJECUTANDO UPDATE ---")
        cursor.execute(f"""
            UPDATE msgestion03.dbo.stock
            SET stock_actual = 0
            WHERE articulo IN ({placeholders})
              AND deposito = ?
        """, ARTICULOS + [DEPOSITO])
        affected = cursor.rowcount
        conn.commit()
        print(f"  ✓ UPDATE ejecutado: {affected} registros actualizados a stock_actual=0")

        # 3. Verificar resultado
        print(f"\n--- VERIFICACIÓN POST-UPDATE ---")
        cursor.execute(f"""
            SELECT s.articulo, s.deposito, s.stock_actual
            FROM msgestion03.dbo.stock s
            WHERE s.articulo IN ({placeholders})
              AND s.deposito = ?
            ORDER BY s.articulo
        """, ARTICULOS + [DEPOSITO])
        for r in cursor.fetchall():
            estado = "✓" if r.stock_actual == 0 else "✗"
            print(f"  {estado} Art {r.articulo} dep {r.deposito}: stock_actual = {r.stock_actual}")

    conn.close()
    print(f"\n{'='*60}")
    print(f"  {'DRY-RUN completado' if dry_run else 'FIX APLICADO EXITOSAMENTE'}")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
