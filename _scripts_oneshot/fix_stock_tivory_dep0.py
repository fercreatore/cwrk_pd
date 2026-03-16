"""
fix_stock_tivory_dep0.py
========================
Limpia stock fantasma en depósitos 0, 6 y 8 de los artículos del remito
Tivory. Todo el stock real está en dep 11 (msgestion03).

El ERP creó registros espurios en msgestion01 al procesar transferencias.
Este script pone en 0 esos registros para que el consolidado refleje
solo lo que hay en dep 11.

PPX3941 también se limpia en base03 dep 0 (20 pares). El usuario confirmó
que todo va al dep 11.

Ejecutar en 192.168.2.111:
  py -3 fix_stock_tivory_dep0.py            # DRY RUN
  py -3 fix_stock_tivory_dep0.py --ejecutar
"""

import pyodbc
import sys

DRY_RUN = "--ejecutar" not in sys.argv

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
)

# Artículos del remito Tivory (pre-existentes con stock disperso)
ARTS_LIMPIAR = {
    # PPX5947 ROSA
    351759, 351760, 351761, 351762, 351763,
    # PPX938 ROSA/LILA
    146119, 146120, 146121, 146122, 146123,
    # PPX942 ROSA/PLATA
    351770, 351771, 351772, 351773, 351774,
    # PWX3585 GRIS
    344904, 344905, 344906, 344907, 344983, 344984,
    # SP5690 AZUL
    351752, 351753, 351754, 351755, 351756,
    # PPX3941 LILA (solo limpiar base01, preservar base03)
    344898, 344899, 344900, 344901, 344902,
}

# Depósitos a limpiar
DEPS_LIMPIAR = [0, 6, 8]


def main():
    if DRY_RUN:
        print("=" * 60)
        print("  DRY RUN — no se modifica nada")
        print("  Usar: py -3 fix_stock_tivory_dep0.py --ejecutar")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  EJECUTANDO EN PRODUCCIÓN")
        print("=" * 60)

    conn = pyodbc.connect(CONN_STR, autocommit=False)
    cur = conn.cursor()

    fixed_01 = 0
    fixed_03 = 0

    # ============================================
    # PARTE 1: Limpiar base01 dep 0, 6, 8
    # ============================================
    print("\n--- PARTE 1: Limpiar msgestion01 dep 0/6/8 ---\n")

    for dep in DEPS_LIMPIAR:
        for art in sorted(ARTS_LIMPIAR):
            cur.execute("""
                SELECT stock_actual FROM msgestion01.dbo.stock
                WHERE deposito = ? AND articulo = ? AND serie = ' '
            """, dep, art)
            row = cur.fetchone()
            if row is None or row.stock_actual == 0:
                continue

            print(f"  base01 dep{dep} art {art}: {row.stock_actual} → 0")
            if not DRY_RUN:
                cur.execute("""
                    UPDATE msgestion01.dbo.stock
                    SET stock_actual = 0
                    WHERE deposito = ? AND articulo = ? AND serie = ' '
                """, dep, art)
            fixed_01 += 1

    # ============================================
    # PARTE 2: Limpiar base03 dep 0 (todos, incluido PPX3941)
    # ============================================
    print("\n--- PARTE 2: Limpiar msgestion03 dep 0 ---\n")

    for art in sorted(ARTS_LIMPIAR):
        cur.execute("""
            SELECT stock_actual FROM msgestion03.dbo.stock
            WHERE deposito = 0 AND articulo = ? AND serie = ' '
        """, art)
        row = cur.fetchone()
        if row is None or row.stock_actual == 0:
            continue

        print(f"  base03 dep0 art {art}: {row.stock_actual} → 0")
        if not DRY_RUN:
            cur.execute("""
                UPDATE msgestion03.dbo.stock
                SET stock_actual = 0
                WHERE deposito = 0 AND articulo = ? AND serie = ' '
            """, art)
        fixed_03 += 1

    # ============================================
    # RESUMEN
    # ============================================
    print(f"\n{'='*60}")
    print(f"  RESUMEN")
    print(f"{'='*60}")
    print(f"  Registros limpiados en base01: {fixed_01}")
    print(f"  Registros limpiados en base03: {fixed_03}")
    print(f"  PPX3941 base03 dep0: también limpiado")

    if not DRY_RUN:
        conn.commit()
        print("\n  COMMIT OK")

        # Verificación
        print(f"\n--- Verificación post-fix ---\n")
        print(f"{'Art':>8} | {'Dep0 01':>8} | {'Dep0 03':>8} | {'Dep11 03':>8} | {'Consol':>7}")
        print("-" * 55)
        for art in sorted(ARTS_LIMPIAR):
            cur.execute("""
                SELECT
                    (SELECT ISNULL(SUM(stock_actual),0) FROM msgestion01.dbo.stock
                     WHERE articulo=? AND serie=' ' AND deposito IN (0,6,8)) AS otros_01,
                    (SELECT ISNULL(stock_actual,0) FROM msgestion03.dbo.stock
                     WHERE deposito=0 AND articulo=? AND serie=' ') AS dep0_03,
                    (SELECT ISNULL(stock_actual,0) FROM msgestion03.dbo.stock
                     WHERE deposito=11 AND articulo=? AND serie=' ') AS dep11_03
            """, art, art, art)
            r = cur.fetchone()
            consol = (r.otros_01 or 0) + (r.dep0_03 or 0) + (r.dep11_03 or 0)
            print(f"{art:>8} | {r.otros_01 or 0:>8} | {r.dep0_03 or 0:>8} | {r.dep11_03 or 0:>8} | {consol:>7}")
    else:
        print("\n  (dry run — nada modificado)")

    cur.close()
    conn.close()
    print("\nFin.")


if __name__ == "__main__":
    main()
