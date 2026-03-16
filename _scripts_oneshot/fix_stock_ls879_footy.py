#!/usr/bin/env python3
"""
fix_stock_ls879_footy.py
========================
Corrige stock fantasma de LS879 BLANCO AZUL ZAPATILLA COLEGIAL SKATE 1 ABROJO (FOOTY)
Artículos 360773-360778, talles 25-30, dep 11, stock=2 sin compras que lo respalden.

Uso:
    py -3 fix_stock_ls879_footy.py --dry-run     # Solo muestra qué haría
    py -3 fix_stock_ls879_footy.py --ejecutar     # Ejecuta el UPDATE
"""

import sys
import pyodbc

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
)

# Artículos con stock fantasma
ARTICULOS = [360773, 360774, 360775, 360776, 360777, 360778]
DEPOSITO = 11

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('--dry-run', '--ejecutar'):
        print("Uso: py -3 fix_stock_ls879_footy.py --dry-run|--ejecutar")
        sys.exit(1)

    dry_run = sys.argv[1] == '--dry-run'
    modo = "DRY-RUN" if dry_run else "EJECUTAR"
    print(f"\n{'='*60}")
    print(f"  FIX STOCK FANTASMA LS879 FOOTY — {modo}")
    print(f"{'='*60}")
    print(f"  Artículos: {ARTICULOS[0]}-{ARTICULOS[-1]} (6 arts, talles 25-30)")
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
        print("  No se encontró stock para estos artículos en dep 11. Ya está limpio.")
        conn.close()
        return

    for r in rows:
        print(f"  Art {r.articulo} dep {r.deposito}: stock_actual = {r.stock_actual}")

    # 2. Verificar que NO hay compras (doble check)
    cursor.execute(f"""
        SELECT COUNT(*) as cnt
        FROM msgestion03.dbo.compras1 c
        WHERE c.articulo IN ({placeholders})
    """, ARTICULOS)
    cnt_compras = cursor.fetchone().cnt

    if cnt_compras > 0:
        print(f"\n  ⚠️ ATENCION: Se encontraron {cnt_compras} registros en compras1!")
        print("  Esto NO debería pasar. Abortando por seguridad.")
        conn.close()
        sys.exit(1)
    else:
        print(f"\n  ✓ Confirmado: 0 registros en compras1 (stock es fantasma)")

    # 3. Ejecutar fix
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

        # 4. Verificar resultado
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
