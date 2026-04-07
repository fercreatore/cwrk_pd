#!/usr/bin/env python3
"""
fix_piccadilly_catag.py
========================
Corrige la visibilidad de artículos Piccadilly en catag (eVirtual).

Problema: Los artículos insertados por nuestro script tienen el campo
`stock` = NULL en msgestion01art.dbo.articulo. La app catag filtra por
stock = 'S' (flag "maneja stock"). Los artículos cargados por el ERP
tienen stock = 'S', los nuestros no.

Solución: UPDATE articulo SET stock = 'S' para todos los Piccadilly
insertados por nosotros (codigo 360570-360677, marca 656).

La cadena de vistas es:
  catag app → omicron_web_articulo_stock → web_stock → stock_v
  stock_v = UNION de msgestion01.dbo.stock + msgestion03.dbo.stock
  (o sea las vistas YA ven ambas bases, el stock en base03 está bien)

Uso:
    py -3 fix_piccadilly_catag.py --dry-run     # Solo muestra qué haría
    py -3 fix_piccadilly_catag.py --ejecutar     # Ejecuta el UPDATE
"""

import sys
import pyodbc

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
)

# Rango de artículos Piccadilly insertados por nuestro script
CODIGO_DESDE = 360570
CODIGO_HASTA = 360677
MARCA = 656  # PICCADILLY


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ('--dry-run', '--ejecutar'):
        print("Uso: py -3 fix_piccadilly_catag.py --dry-run|--ejecutar")
        sys.exit(1)

    dry_run = sys.argv[1] == '--dry-run'
    modo = "DRY-RUN" if dry_run else "EJECUTAR"
    print(f"\n{'='*70}")
    print(f"  FIX PICCADILLY CATAG: SET stock='S' — {modo}")
    print(f"{'='*70}")
    print(f"  Rango: {CODIGO_DESDE} - {CODIGO_HASTA} (marca={MARCA})")
    print(f"  Acción: UPDATE articulo SET stock = 'S'")
    print(f"  Objetivo: Hacer visibles en catag (eVirtual)")
    print(f"{'='*70}\n")

    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    # 1. Mostrar artículos afectados
    cursor.execute("""
        SELECT a.codigo, a.descripcion_1, a.stock, a.codigo_sinonimo
        FROM msgestion01art.dbo.articulo a
        WHERE a.codigo BETWEEN ? AND ?
          AND a.marca = ?
          AND (a.stock IS NULL OR a.stock <> 'S')
        ORDER BY a.codigo
    """, CODIGO_DESDE, CODIGO_HASTA, MARCA)

    rows = cursor.fetchall()
    if not rows:
        print("  ✓ Todos los artículos ya tienen stock='S'. Nada que hacer.")
        conn.close()
        return

    print(f"--- ARTÍCULOS CON stock != 'S' ({len(rows)} artículos) ---")
    for r in rows:
        stock_val = repr(r.stock) if r.stock is not None else 'NULL'
        print(f"  Art {r.codigo}: {r.descripcion_1[:45]:45s} stock={stock_val} sin={r.codigo_sinonimo}")

    # 2. Ejecutar
    if dry_run:
        print(f"\n--- DRY-RUN ---")
        print(f"  Se haría: UPDATE msgestion01art.dbo.articulo")
        print(f"            SET stock = 'S'")
        print(f"            WHERE codigo BETWEEN {CODIGO_DESDE} AND {CODIGO_HASTA}")
        print(f"            AND marca = {MARCA}")
        print(f"            AND (stock IS NULL OR stock <> 'S')")
        print(f"  Artículos afectados: {len(rows)}")
    else:
        print(f"\n--- EJECUTANDO UPDATE ---")
        cursor.execute("""
            UPDATE msgestion01art.dbo.articulo
            SET stock = 'S'
            WHERE codigo BETWEEN ? AND ?
              AND marca = ?
              AND (stock IS NULL OR stock <> 'S')
        """, CODIGO_DESDE, CODIGO_HASTA, MARCA)

        afectados = cursor.rowcount
        conn.commit()
        print(f"  ✓ UPDATE ejecutado: {afectados} artículos actualizados")

        # 3. Verificación
        print(f"\n--- VERIFICACIÓN ---")
        cursor.execute("""
            SELECT COUNT(*) as total_ok
            FROM msgestion01art.dbo.articulo
            WHERE codigo BETWEEN ? AND ?
              AND marca = ?
              AND stock = 'S'
        """, CODIGO_DESDE, CODIGO_HASTA, MARCA)
        total_ok = cursor.fetchone().total_ok

        cursor.execute("""
            SELECT COUNT(*) as total
            FROM msgestion01art.dbo.articulo
            WHERE codigo BETWEEN ? AND ?
              AND marca = ?
        """, CODIGO_DESDE, CODIGO_HASTA, MARCA)
        total = cursor.fetchone().total

        print(f"  Artículos con stock='S': {total_ok}/{total}")
        if total_ok == total:
            print(f"  ✓ TODOS los artículos Piccadilly tienen stock='S'")
        else:
            print(f"  ⚠️ Quedan {total - total_ok} sin el flag")

    conn.close()
    print(f"\n{'='*70}")
    print(f"  {'DRY-RUN completado' if dry_run else 'FIX APLICADO'}")
    if dry_run:
        print(f"  Ejecutar con --ejecutar para aplicar cambios")
    else:
        print(f"  Los artículos deberían ser visibles en catag ahora.")
        print(f"  Probá buscar por marca PICCADILLY en catag.")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
