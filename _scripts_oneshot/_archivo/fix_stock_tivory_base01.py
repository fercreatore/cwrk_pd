"""
fix_stock_tivory_base01.py
==========================
Los artículos pre-existentes del remito Tivory R 0001-12867 tienen stock
NEGATIVO en msgestion01.dbo.stock dep 11, que se suma al positivo de
msgestion03 y da consolidado incorrecto.

Causa: nuestro script original escribió en msgestion03, pero el ERP cargó
el remito por msgestion01 creando negativos.

Solución: poner en 0 todos los registros negativos de msgestion01.dbo.stock
dep 11 serie ' ' para estos artículos.

Ejecutar en 192.168.2.111:
  py -3 fix_stock_tivory_base01.py            # DRY RUN
  py -3 fix_stock_tivory_base01.py --ejecutar
"""

import pyodbc
import sys

DRY_RUN = "--ejecutar" not in sys.argv

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
)

# Artículos pre-existentes con negativos en msgestion01 dep 11
ARTS_FIX = [
    # PPX3941 LILA
    344898, 344899, 344900, 344901, 344902,
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
]


def main():
    if DRY_RUN:
        print("=" * 60)
        print("  DRY RUN — no se modifica nada")
        print("  Usar: py -3 fix_stock_tivory_base01.py --ejecutar")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  EJECUTANDO EN PRODUCCIÓN")
        print("=" * 60)

    conn = pyodbc.connect(CONN_STR, autocommit=False)
    cur = conn.cursor()

    fixed = 0
    already_ok = 0

    print("\n--- Limpiando negativos en MSGESTION01.dbo.stock dep 11 ---\n")

    for art in ARTS_FIX:
        # Verificar valor actual
        cur.execute("""
            SELECT stock_actual FROM msgestion01.dbo.stock
            WHERE deposito = 11 AND articulo = ? AND serie = ' '
        """, art)
        row = cur.fetchone()

        if row is None:
            print(f"  Art {art}: no existe en msgestion01 dep 11 — OK")
            already_ok += 1
            continue

        current = row.stock_actual

        if current >= 0:
            print(f"  Art {art}: msgestion01 dep11 = {current} — ya OK")
            already_ok += 1
            continue

        # Poner en 0
        print(f"  Art {art}: msgestion01 dep11 = {current} → 0")
        if not DRY_RUN:
            cur.execute("""
                UPDATE msgestion01.dbo.stock
                SET stock_actual = 0
                WHERE deposito = 11 AND articulo = ? AND serie = ' '
            """, art)
        fixed += 1

    # También limpiar serie '26030001' residual en msgestion01
    print("\n--- Limpiando serie '26030001' residual en msgestion01 dep 11 ---\n")
    cleaned_series = 0
    for art in ARTS_FIX:
        cur.execute("""
            SELECT stock_actual FROM msgestion01.dbo.stock
            WHERE deposito = 11 AND articulo = ? AND serie = '26030001'
        """, art)
        row = cur.fetchone()
        if row is not None:
            print(f"  Art {art}: serie 26030001 = {row.stock_actual} → 0")
            if not DRY_RUN:
                cur.execute("""
                    UPDATE msgestion01.dbo.stock
                    SET stock_actual = 0
                    WHERE deposito = 11 AND articulo = ? AND serie = '26030001'
                """, art)
            cleaned_series += 1

    # Verificación: mostrar consolidado esperado
    print(f"\n{'='*60}")
    print(f"  RESUMEN")
    print(f"{'='*60}")
    print(f"  Negativos corregidos a 0: {fixed}")
    print(f"  Ya estaban OK: {already_ok}")
    print(f"  Series 26030001 limpiadas: {cleaned_series}")

    if not DRY_RUN:
        conn.commit()
        print("\n  COMMIT OK")

        # Verificación post-fix
        print(f"\n--- Verificación post-fix (consolidado dep 11) ---\n")
        for art in ARTS_FIX:
            cur.execute("""
                SELECT
                    (SELECT ISNULL(stock_actual,0) FROM msgestion01.dbo.stock
                     WHERE deposito=11 AND articulo=? AND serie=' ') AS base01,
                    (SELECT ISNULL(stock_actual,0) FROM msgestion03.dbo.stock
                     WHERE deposito=11 AND articulo=? AND serie=' ') AS base03
            """, art, art)
            row = cur.fetchone()
            b01 = row.base01 or 0
            b03 = row.base03 or 0
            total = b01 + b03
            status = "OK" if total > 0 else "REVISAR"
            print(f"  Art {art}: 01={b01:>3} + 03={b03:>3} = consol {total:>3}  {status}")
    else:
        print("\n  (dry run — nada modificado)")

    cur.close()
    conn.close()
    print("\nFin.")


if __name__ == "__main__":
    main()
