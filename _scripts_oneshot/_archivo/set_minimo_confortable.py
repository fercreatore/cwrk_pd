# set_minimo_confortable.py
# Actualiza "Se pide por" (campo paquete_pedido) en artículos CONFORTABLE (proveedor 236)
# EVA (sinónimo 236495%): paquete_pedido = 6
# PVC (sinónimo 236007%): paquete_pedido = 3
#
# EJECUTAR EN EL 111:
#   py -3 set_minimo_confortable.py --dry-run
#   py -3 set_minimo_confortable.py --ejecutar

import sys
import pyodbc

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion01art;"
    "UID=am;PWD=dl"
)

SQL_UPDATE_EVA = """
UPDATE dbo.articulo
SET paquete_pedido = 6
WHERE proveedor = 236
  AND estado = 'V'
  AND codigo_sinonimo LIKE '236495%'
  AND (paquete_pedido IS NULL OR paquete_pedido <> 6)
"""

SQL_UPDATE_PVC = """
UPDATE dbo.articulo
SET paquete_pedido = 3
WHERE proveedor = 236
  AND estado = 'V'
  AND codigo_sinonimo LIKE '236007%'
  AND (paquete_pedido IS NULL OR paquete_pedido <> 3)
"""

SQL_CHECK = """
SELECT
    CASE WHEN codigo_sinonimo LIKE '236495%' THEN 'EVA' ELSE 'PVC' END as familia,
    paquete_pedido,
    COUNT(*) as registros
FROM dbo.articulo
WHERE proveedor = 236
  AND estado = 'V'
  AND (codigo_sinonimo LIKE '236495%' OR codigo_sinonimo LIKE '236007%')
GROUP BY
    CASE WHEN codigo_sinonimo LIKE '236495%' THEN 'EVA' ELSE 'PVC' END,
    paquete_pedido
ORDER BY familia, paquete_pedido
"""

def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]

    dry_run = modo != "--ejecutar"

    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    # Estado actual
    print("ESTADO ACTUAL:")
    cursor.execute(SQL_CHECK)
    for row in cursor.fetchall():
        print(f"  {row.familia}: paquete_pedido = {row.paquete_pedido} ({row.registros} registros)")

    if dry_run:
        print("\n--- DRY RUN: no se actualiza nada ---")
        print("Se actualizarian:")
        print("  EVA (236495%): paquete_pedido -> 6  (77 articulos)")
        print("  PVC (236007%): paquete_pedido -> 3  (47 articulos)")
        conn.close()
        return

    # Ejecutar
    print("\nActualizando EVA -> paquete_pedido = 6 ...")
    cursor.execute(SQL_UPDATE_EVA)
    eva_rows = cursor.rowcount
    print(f"  {eva_rows} registros actualizados")

    print("Actualizando PVC -> paquete_pedido = 3 ...")
    cursor.execute(SQL_UPDATE_PVC)
    pvc_rows = cursor.rowcount
    print(f"  {pvc_rows} registros actualizados")

    conn.commit()
    print(f"\nCOMMIT OK - {eva_rows + pvc_rows} registros totales")

    # Verificar
    print("\nESTADO FINAL:")
    cursor.execute(SQL_CHECK)
    for row in cursor.fetchall():
        print(f"  {row.familia}: paquete_pedido = {row.paquete_pedido} ({row.registros} registros)")

    conn.close()

if __name__ == "__main__":
    main()
