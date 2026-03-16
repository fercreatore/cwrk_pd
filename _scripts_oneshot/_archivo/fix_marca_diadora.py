#!/usr/bin/env python3
"""
fix_marca_diadora.py — Corrige marca y grupo de artículos Diadora
==================================================================
Los 20 artículos Diadora (360527-360546) se crearon con:
  - marca=614 (proveedor) → debe ser marca=675 (DIADORA)
  - grupo='5' (PU)        → debe ser grupo='15' (MACRAME)

EJECUTAR EN EL 111:
  py -3 fix_marca_diadora.py                ← dry-run
  py -3 fix_marca_diadora.py --ejecutar     ← escribe en producción
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONN_COMPRAS

CODIGO_DESDE = 360527
CODIGO_HASTA = 360546

# Correcciones a aplicar
MARCA_NUEVA = 675      # DIADORA
GRUPO_NUEVO = "15"     # MACRAME


def main():
    import pyodbc
    dry_run = "--ejecutar" not in sys.argv

    if dry_run:
        print("=" * 60)
        print("  MODO DRY-RUN — No se escribe nada")
        print("  Agregar --ejecutar para escribir de verdad")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  ⚠️  EJECUCIÓN REAL")
        print("=" * 60)

    conn = pyodbc.connect(CONN_COMPRAS)
    cursor = conn.cursor()

    # Verificar estado actual
    cursor.execute(
        "SELECT codigo, descripcion_1, marca, grupo "
        "FROM msgestion01art.dbo.articulo "
        "WHERE codigo BETWEEN ? AND ? ORDER BY codigo",
        CODIGO_DESDE, CODIGO_HASTA
    )
    rows = cursor.fetchall()

    print(f"\n  Artículos encontrados: {len(rows)}")
    for r in rows:
        marca_ok = r.marca == MARCA_NUEVA
        grupo_ok = str(r.grupo).strip() == GRUPO_NUEVO
        estado_m = "✅" if marca_ok else f"❌ marca={r.marca}"
        estado_g = "✅" if grupo_ok else f"❌ grupo={r.grupo}"
        print(f"    {r.codigo} | {r.descripcion_1[:45]} | marca:{estado_m} | grupo:{estado_g}")

    a_corregir = sum(1 for r in rows if r.marca != MARCA_NUEVA or str(r.grupo).strip() != GRUPO_NUEVO)

    if a_corregir == 0:
        print(f"\n  ✅ Todos los artículos ya tienen marca=675 (DIADORA) y grupo=15 (MACRAME)")
        conn.close()
        return

    print(f"\n  A corregir: {a_corregir} artículos")
    print(f"    marca → {MARCA_NUEVA} (DIADORA)")
    print(f"    grupo → {GRUPO_NUEVO} (MACRAME)")

    if not dry_run:
        cursor.execute(
            "UPDATE msgestion01art.dbo.articulo "
            "SET marca = ?, grupo = ? "
            "WHERE codigo BETWEEN ? AND ?",
            MARCA_NUEVA, GRUPO_NUEVO, CODIGO_DESDE, CODIGO_HASTA
        )
        affected = cursor.rowcount
        conn.commit()
        print(f"\n  → UPDATE ejecutado: {affected} registros actualizados")

        # Verificar
        cursor.execute(
            "SELECT COUNT(*) FROM msgestion01art.dbo.articulo "
            "WHERE codigo BETWEEN ? AND ? AND marca = ? AND grupo = ?",
            CODIGO_DESDE, CODIGO_HASTA, MARCA_NUEVA, GRUPO_NUEVO
        )
        ok = cursor.fetchone()[0]
        print(f"  → Verificación: {ok}/20 artículos con marca=675 grupo=15")
    else:
        print(f"\n  → DRY-RUN: se haría UPDATE de {a_corregir} artículos")

    conn.close()
    print(f"\n{'='*60}")
    print(f"  {'DRY-RUN completado' if dry_run else 'FIX completado'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
