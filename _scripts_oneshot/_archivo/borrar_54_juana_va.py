#!/usr/bin/env python3
"""
borrar_54_juana_va.py — Elimina los 54 artículos mal creados el 13/03/2026
con proveedor 838 (PEPPERS) que debían ser 938 (Juana Va).

Verificado: 0 referencias en ventas1, compras1, stock, pedico1.
Se pueden borrar sin riesgo.

EJECUTAR EN: 192.168.2.111 (producción)
COMANDO:     py -3 borrar_54_juana_va.py
MODO:        DRY RUN por defecto. Pasar --ejecutar para borrar.
"""

import sys
import pyodbc

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion01art;"
    "UID=am;PWD=dl;"
    "TrustServerCertificate=yes"
)

EJECUTAR = "--ejecutar" in sys.argv


def main():
    print("=" * 60)
    print(f"BORRAR 54 ARTS JUANA VA (prov 838) — {'EJECUTAR' if EJECUTAR else 'DRY RUN'}")
    print("=" * 60)

    conn = pyodbc.connect(CONN_STR, timeout=30)
    cursor = conn.cursor()

    # Mostrar lo que se va a borrar
    cursor.execute("""
        SELECT codigo, codigo_sinonimo, descripcion_1, descripcion_4
        FROM articulo
        WHERE fecha_alta >= '2026-03-13' AND fecha_alta < '2026-03-14'
          AND proveedor = 838
        ORDER BY codigo
    """)
    rows = cursor.fetchall()

    if not rows:
        print("\nNo se encontraron artículos. Ya fueron borrados?")
        conn.close()
        return

    print(f"\n{len(rows)} artículos a eliminar:\n")
    print(f"{'Codigo':<8} {'Sinonimo':<14} {'Desc1':<30} {'Color'}")
    print("-" * 70)
    for r in rows:
        print(f"{r[0]:<8} {r[1].strip():<14} {r[2].strip():<30} {r[3].strip()}")

    codigos = [r[0] for r in rows]
    rango = f"{min(codigos)} a {max(codigos)}"
    print(f"\nRango de códigos: {rango}")

    if not EJECUTAR:
        print(f"\n⚠️  DRY RUN — No se borró nada.")
        print(f"    Para borrar: py -3 borrar_54_juana_va.py --ejecutar")
        conn.close()
        return

    # Verificación de seguridad: confirmar que no hay referencias
    cursor.execute("""
        SELECT
            (SELECT COUNT(*) FROM msgestionC.dbo.ventas1 WHERE articulo BETWEEN ? AND ?) AS ventas,
            (SELECT COUNT(*) FROM msgestionC.dbo.compras1 WHERE articulo BETWEEN ? AND ?) AS compras,
            (SELECT COUNT(*) FROM msgestionC.dbo.stock WHERE articulo BETWEEN ? AND ?) AS stock,
            (SELECT COUNT(*) FROM msgestionC.dbo.pedico1 WHERE articulo BETWEEN ? AND ?) AS pedidos
    """, min(codigos), max(codigos), min(codigos), max(codigos),
         min(codigos), max(codigos), min(codigos), max(codigos))
    ref = cursor.fetchone()

    if any(ref):
        print(f"\n❌ ABORTADO — Se encontraron referencias:")
        print(f"   Ventas: {ref[0]}, Compras: {ref[1]}, Stock: {ref[2]}, Pedidos: {ref[3]}")
        conn.close()
        return

    # Borrar
    cursor.execute("""
        DELETE FROM articulo
        WHERE fecha_alta >= '2026-03-13' AND fecha_alta < '2026-03-14'
          AND proveedor = 838
    """)
    borrados = cursor.rowcount
    conn.commit()

    print(f"\n✅ {borrados} artículos eliminados.")

    # Verificación
    cursor.execute("SELECT COUNT(*) FROM articulo WHERE proveedor = 838 AND fecha_alta >= '2026-03-13'")
    quedan = cursor.fetchone()[0]
    print(f"   Verificación: quedan {quedan} artículos con prov=838 del 13/03 (esperado: 0)")

    conn.close()


if __name__ == "__main__":
    main()
