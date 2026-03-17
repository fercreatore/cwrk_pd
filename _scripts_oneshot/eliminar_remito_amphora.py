#!/usr/bin/env python3
# eliminar_remito_amphora.py
# Elimina el remito de Amphora AW26 que se cargo antes de recibir mercaderia
# Remito: R 5000-78194 orden 1 en MSGESTION03
# Pedido: #1134073 (pedico1 en MSGESTION01, visible via VIEW en 03)
#
# EJECUTAR EN 111:
#   py -3 eliminar_remito_amphora.py --dry-run     <- solo muestra
#   py -3 eliminar_remito_amphora.py --ejecutar    <- borra

import sys
import pyodbc
import socket

_hostname = socket.gethostname().upper()
if _hostname in ("DELL-SVR", "DELLSVR"):
    SERVIDOR = "localhost"
    DRIVER = "ODBC Driver 17 for SQL Server"
    EXTRAS = ""
else:
    SERVIDOR = "192.168.2.111"
    DRIVER = "ODBC Driver 18 for SQL Server"
    EXTRAS = "TrustServerCertificate=yes;Encrypt=no;"

CONN = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVIDOR};"
    f"DATABASE=msgestionC;"
    f"UID=am;PWD=dl;"
    f"{EXTRAS}"
)

# Remito
REM_COD = 7
REM_LET = 'R'
REM_SUC = 5000
REM_NUM = 78194
REM_ORD = 1

# Pedido
PED_COD = 8
PED_LET = 'X'
PED_SUC = 1
PED_NUM = 1134073

def main():
    dry_run = '--dry-run' in sys.argv
    ejecutar = '--ejecutar' in sys.argv

    if not dry_run and not ejecutar:
        print("Uso: py -3 eliminar_remito_amphora.py [--dry-run | --ejecutar]")
        return

    print("=" * 60)
    print("  ELIMINAR REMITO AMPHORA AW26")
    print(f"  Remito: R {REM_SUC}-{REM_NUM} orden {REM_ORD} (MSGESTION03)")
    print(f"  Pedido: #{PED_NUM} (MSGESTION01)")
    print(f"  Modo: {'DRY RUN' if dry_run else 'EJECUTAR'}")
    print("=" * 60)

    conn = pyodbc.connect(CONN, timeout=10, autocommit=False)
    cursor = conn.cursor()

    try:
        # 1. Verificar que existe
        cursor.execute("""
            SELECT COUNT(*) FROM msgestion03.dbo.compras2
            WHERE codigo=? AND letra=? AND sucursal=? AND numero=? AND orden=?
        """, (REM_COD, REM_LET, REM_SUC, REM_NUM, REM_ORD))
        if cursor.fetchone()[0] == 0:
            print("\n  El remito NO existe. Nada que hacer.")
            return

        # 2. Contar lo que se va a borrar
        checks = [
            ("msgestion03.dbo.compras1",
             f"codigo={REM_COD} AND letra='{REM_LET}' AND sucursal={REM_SUC} AND numero={REM_NUM} AND orden={REM_ORD}"),
            ("msgestion03.dbo.comprasr",
             f"codigo={REM_COD} AND letra='{REM_LET}' AND sucursal={REM_SUC} AND numero={REM_NUM} AND orden={REM_ORD}"),
            ("msgestion03.dbo.movi_stock",
             f"codigo_comprobante={REM_COD} AND letra_comprobante='{REM_LET}' AND sucursal_comprobante={REM_SUC} AND numero_comprobante={REM_NUM} AND orden={REM_ORD}"),
            ("msgestion01.dbo.pedico1_entregas",
             f"codigo={PED_COD} AND letra='{PED_LET}' AND sucursal={PED_SUC} AND numero={PED_NUM}"),
            ("msgestion03.dbo.pedico1_entregas",
             f"codigo={PED_COD} AND letra='{PED_LET}' AND sucursal={PED_SUC} AND numero={PED_NUM}"),
        ]

        print("\n  Registros a eliminar:")
        for tabla, where in checks:
            cursor.execute(f"SELECT COUNT(*) FROM {tabla} WHERE {where}")
            cnt = cursor.fetchone()[0]
            print(f"    {tabla}: {cnt} filas")

        # Verificar pedico1 (para revertir)
        cursor.execute(f"""
            SELECT COUNT(*) FROM msgestion01.dbo.pedico1
            WHERE codigo={PED_COD} AND letra='{PED_LET}' AND sucursal={PED_SUC} AND numero={PED_NUM}
        """)
        ped_lines = cursor.fetchone()[0]
        print(f"    msgestion01.dbo.pedico1: {ped_lines} lineas a revertir (cantidad_entregada=0)")

        if dry_run:
            print("\n  [DRY RUN] Nada fue modificado.")
            return

        # 3. EJECUTAR eliminacion
        print("\n  Eliminando...")

        # 3a. DELETE movi_stock
        cursor.execute(f"""
            DELETE FROM msgestion03.dbo.movi_stock
            WHERE codigo_comprobante={REM_COD} AND letra_comprobante='{REM_LET}'
              AND sucursal_comprobante={REM_SUC} AND numero_comprobante={REM_NUM} AND orden={REM_ORD}
        """)
        print(f"    movi_stock: {cursor.rowcount} borrados")

        # 3b. DELETE compras1
        cursor.execute(f"""
            DELETE FROM msgestion03.dbo.compras1
            WHERE codigo={REM_COD} AND letra='{REM_LET}'
              AND sucursal={REM_SUC} AND numero={REM_NUM} AND orden={REM_ORD}
        """)
        print(f"    compras1: {cursor.rowcount} borrados")

        # 3c. DELETE comprasr
        cursor.execute(f"""
            DELETE FROM msgestion03.dbo.comprasr
            WHERE codigo={REM_COD} AND letra='{REM_LET}'
              AND sucursal={REM_SUC} AND numero={REM_NUM} AND orden={REM_ORD}
        """)
        print(f"    comprasr: {cursor.rowcount} borrados")

        # 3d. DELETE compras2
        cursor.execute(f"""
            DELETE FROM msgestion03.dbo.compras2
            WHERE codigo={REM_COD} AND letra='{REM_LET}'
              AND sucursal={REM_SUC} AND numero={REM_NUM} AND orden={REM_ORD}
        """)
        print(f"    compras2: {cursor.rowcount} borrados")

        # 3e. DELETE pedico1_entregas en AMBAS bases
        for base in ['msgestion01', 'msgestion03']:
            cursor.execute(f"""
                DELETE FROM {base}.dbo.pedico1_entregas
                WHERE codigo={PED_COD} AND letra='{PED_LET}'
                  AND sucursal={PED_SUC} AND numero={PED_NUM}
            """)
            print(f"    {base}.pedico1_entregas: {cursor.rowcount} borrados")

        # 3f. Revertir pedico1: cantidad_entregada=0, monto_entregado=0
        cursor.execute(f"""
            UPDATE msgestion01.dbo.pedico1
            SET cantidad_entregada = 0, monto_entregado = 0
            WHERE codigo={PED_COD} AND letra='{PED_LET}'
              AND sucursal={PED_SUC} AND numero={PED_NUM}
        """)
        print(f"    pedico1 revertido: {cursor.rowcount} lineas")

        # COMMIT
        conn.commit()
        print(f"\n{'=' * 60}")
        print(f"  COMMIT OK — Remito R {REM_SUC}-{REM_NUM} eliminado")
        print(f"  Pedido #{PED_NUM} queda activo (sin entregas)")
        print(f"{'=' * 60}")

    except Exception as e:
        conn.rollback()
        print(f"\n  !!! ERROR — ROLLBACK !!!")
        print(f"  {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
