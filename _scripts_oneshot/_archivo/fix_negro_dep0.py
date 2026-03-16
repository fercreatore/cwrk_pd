#!/usr/bin/env python3
"""
fix_negro_dep0.py — Corrige el exceso en dep 0 para NEGRO Piccadilly
=====================================================================
El script anterior movió 2 en lugar de 1 para los artículos NEGRO que
aparecían en transferencias de AMBAS bases (msg01 + msg03).

Fix: devolver 1 par de dep 0 → dep 11 en msg03 para 360595-360598.

EJECUTAR EN EL 111:
  py -3 fix_negro_dep0.py              ← dry-run
  py -3 fix_negro_dep0.py --ejecutar   ← escribe
"""

import sys
import pyodbc

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
    "Trusted_Connection=no;"
)

DRY_RUN = "--ejecutar" not in sys.argv

# Artículos que quedaron con dep0=2 cuando debería ser 1
# (NEGRO T37, T38, T39, T40)
ARTS_FIX = [360595, 360596, 360597, 360598]


def main():
    if DRY_RUN:
        print("MODO DRY-RUN — No se escribe nada")
        print("Agregar --ejecutar para aplicar\n")
    else:
        print("⚠️  MODO EJECUCIÓN\n")

    conn = pyodbc.connect(CONN_STR, timeout=30)
    cursor = conn.cursor()

    # Verificar estado actual
    print("Estado actual en msgestion03:")
    for art in ARTS_FIX:
        cursor.execute("""
            SELECT deposito, stock_actual
            FROM msgestion03.dbo.stock
            WHERE articulo = ? AND serie = ' ' AND deposito IN (0, 11)
        """, [art])
        rows = {dep: stk for dep, stk in cursor.fetchall()}
        d0 = rows.get(0, 'N/A')
        d11 = rows.get(11, 'N/A')
        print(f"  {art}: dep0={d0}, dep11={d11}  →  dep0={d0-1 if isinstance(d0,int) else '?'}, dep11={d11+1 if isinstance(d11,int) else '?'}")

    if not DRY_RUN:
        for art in ARTS_FIX:
            # Restar 1 de dep 0
            cursor.execute("""
                UPDATE msgestion03.dbo.stock
                SET stock_actual = stock_actual - 1
                WHERE articulo = ? AND deposito = 0 AND serie = ' '
            """, [art])

            # Sumar 1 a dep 11
            cursor.execute("""
                UPDATE msgestion03.dbo.stock
                SET stock_actual = stock_actual + 1
                WHERE articulo = ? AND deposito = 11 AND serie = ' '
            """, [art])

        conn.commit()
        print(f"\n✅ COMMIT — {len(ARTS_FIX)} artículos corregidos")

        # Verificar
        print("\nEstado post-fix:")
        for art in ARTS_FIX:
            cursor.execute("""
                SELECT deposito, stock_actual
                FROM msgestion03.dbo.stock
                WHERE articulo = ? AND serie = ' ' AND deposito IN (0, 11)
            """, [art])
            rows = {dep: stk for dep, stk in cursor.fetchall()}
            print(f"  {art}: dep0={rows.get(0,'N/A')}, dep11={rows.get(11,'N/A')}")

    conn.close()


if __name__ == "__main__":
    main()
