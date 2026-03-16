#!/usr/bin/env python3
"""
fix_series_stock.py — Consolidar series en blanco en tabla stock
================================================================
Problema: las compras entraron con serie (ej: "26030002", "26030001", "2603")
y las transferencias entre depósitos se hacen con serie en blanco.
Resultado: filas duplicadas por artículo+depósito con distintas series,
stock negativo fantasma, y transferencias que no descuentan del stock real.

Solución: mover TODO el stock a serie=' ' (blanco) para que las
transferencias del ERP funcionen correctamente.

Afecta artículos >= 360000 en ambas bases (msgestion01 y msgestion03).

EJECUTAR EN EL 111:
  py -3 fix_series_stock.py                ← dry-run
  py -3 fix_series_stock.py --ejecutar     ← escribe en producción
"""

import sys
import pyodbc

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
    "Trusted_Connection=no;"
)

BASES = ["msgestion01", "msgestion03"]
MIN_ARTICULO = 360000
SERIE_DESTINO = " "  # serie blanca (un espacio)

DRY_RUN = "--ejecutar" not in sys.argv


def fix_series_en_base(cursor, base, dry_run=True):
    """
    Para una base dada, consolida todas las series != ' ' bajo serie ' '.

    Dos casos:
    A) Ya existe fila (articulo, deposito, serie=' ') en la misma base
       → sumar stock de la serie real a la serie blanca
       → eliminar la fila con serie real
    B) No existe fila con serie=' '
       → simplemente UPDATE serie = ' '
    """
    modo = "DRY-RUN" if dry_run else "EJECUCIÓN"
    print(f"\n{'='*60}")
    print(f"  {base} — {modo}")
    print(f"{'='*60}")

    # Obtener todas las filas con serie != blanco
    cursor.execute(f"""
        SELECT deposito, articulo, serie, stock_actual, stock_unidades
        FROM {base}.dbo.stock
        WHERE articulo >= ?
          AND serie != ' '
          AND serie IS NOT NULL
        ORDER BY articulo, deposito
    """, [MIN_ARTICULO])

    filas_serie = cursor.fetchall()
    print(f"  Filas con serie no-blanca: {len(filas_serie)}")

    if not filas_serie:
        print(f"  Nada que hacer.")
        return 0, 0, 0

    merged = 0
    updated = 0
    deleted = 0
    errores = 0

    for dep, art, serie, stock, stock_u in filas_serie:
        # Verificar si existe fila con serie blanca para mismo art+dep
        cursor.execute(f"""
            SELECT stock_actual, stock_unidades
            FROM {base}.dbo.stock
            WHERE deposito = ? AND articulo = ? AND serie = ' '
        """, [dep, art])

        fila_blanca = cursor.fetchone()

        if fila_blanca:
            # CASO A: ya existe → sumar y borrar
            stock_blanco, stock_u_blanco = fila_blanca
            nuevo_stock = stock_blanco + stock
            nuevo_stock_u = (stock_u_blanco or 0) + (stock_u or 0)

            print(f"  MERGE {art} dep={dep}: serie '{serie}' ({stock}) + "
                  f"serie ' ' ({stock_blanco}) → {nuevo_stock}")

            if not dry_run:
                # Actualizar la fila blanca
                cursor.execute(f"""
                    UPDATE {base}.dbo.stock
                    SET stock_actual = ?, stock_unidades = ?
                    WHERE deposito = ? AND articulo = ? AND serie = ' '
                """, [nuevo_stock, nuevo_stock_u, dep, art])

                # Eliminar la fila con serie real
                cursor.execute(f"""
                    DELETE FROM {base}.dbo.stock
                    WHERE deposito = ? AND articulo = ? AND serie = ?
                """, [dep, art, serie])

            merged += 1
            deleted += 1

        else:
            # CASO B: no existe blanca → update serie
            print(f"  UPDATE {art} dep={dep}: serie '{serie}' → ' '  (stock={stock})")

            if not dry_run:
                cursor.execute(f"""
                    UPDATE {base}.dbo.stock
                    SET serie = ' '
                    WHERE deposito = ? AND articulo = ? AND serie = ?
                """, [dep, art, serie])

            updated += 1

    print(f"\n  Resumen {base}:")
    print(f"    Merged (sumado a blanca + borrado): {merged}")
    print(f"    Updated (serie cambiada a blanco):  {updated}")
    print(f"    Total filas procesadas: {merged + updated}")

    return merged, updated, deleted


def limpiar_stock_cero(cursor, base, dry_run=True):
    """Elimina filas de stock con stock_actual = 0 (basura de transfers fallidos)."""
    cursor.execute(f"""
        SELECT COUNT(*)
        FROM {base}.dbo.stock
        WHERE articulo >= ? AND stock_actual = 0
    """, [MIN_ARTICULO])

    count = cursor.fetchone()[0]

    if count > 0:
        print(f"\n  Limpiando {count} filas con stock=0 en {base}...")
        if not dry_run:
            cursor.execute(f"""
                DELETE FROM {base}.dbo.stock
                WHERE articulo >= ? AND stock_actual = 0
            """, [MIN_ARTICULO])
        print(f"    {'Eliminadas' if not dry_run else 'Se eliminarían'}: {count}")

    return count


def main():
    if DRY_RUN:
        print("=" * 60)
        print("  MODO DRY-RUN — No se escribe nada en la BD")
        print("  Agregar --ejecutar para escribir de verdad")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  ⚠️  MODO EJECUCIÓN REAL — SE VA A ESCRIBIR EN LA BD")
        print("=" * 60)
        resp = input("  Continuar? (si/no): ")
        if resp.lower() not in ("si", "sí", "s", "yes", "y"):
            print("  Cancelado.")
            return

    conn = pyodbc.connect(CONN_STR, timeout=30)
    cursor = conn.cursor()

    total_merged = 0
    total_updated = 0
    total_deleted = 0
    total_cero = 0

    for base in BASES:
        m, u, d = fix_series_en_base(cursor, base, dry_run=DRY_RUN)
        total_merged += m
        total_updated += u
        total_deleted += d

        c = limpiar_stock_cero(cursor, base, dry_run=DRY_RUN)
        total_cero += c

    if not DRY_RUN:
        conn.commit()
        print("\n  ✅ COMMIT realizado")

    conn.close()

    print(f"\n{'='*60}")
    print(f"  RESUMEN TOTAL")
    print(f"{'='*60}")
    print(f"  Merged:   {total_merged}")
    print(f"  Updated:  {total_updated}")
    print(f"  Deleted:  {total_deleted}")
    print(f"  Ceros:    {total_cero}")
    print(f"  Total:    {total_merged + total_updated + total_cero}")
    print(f"\n  {'DRY-RUN completado' if DRY_RUN else 'EJECUCIÓN completada'}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
