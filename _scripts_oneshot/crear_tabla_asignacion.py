# crear_tabla_asignacion.py
# Crea la tabla proveedor_asignacion_base en MSGESTION01
# y la puebla con el analisis de facturacion 2024-2026
#
# EJECUTAR EN EL 111:
#   cd C:\cowork_pedidos && set PYTHONPATH=C:\cowork_pedidos && py -3 _scripts_oneshot\crear_tabla_asignacion.py --ejecutar

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyodbc
from config import CONN_COMPRAS


def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]

    dry_run = modo != "--ejecutar"

    if dry_run:
        print("\n[DRY RUN] Se ejecutarian los siguientes pasos:")
        print("  1. DROP + CREATE TABLE proveedor_asignacion_base")
        print("  2. INSERT proveedores SOLO_01")
        print("  3. INSERT proveedores SOLO_03")
        print("  4. INSERT proveedores AMBAS (con % split)")
        print("\n  Ningun dato fue escrito.")
        print("\n  Para ejecutar:")
        print("  cd C:\\cowork_pedidos && set PYTHONPATH=C:\\cowork_pedidos && py -3 _scripts_oneshot\\crear_tabla_asignacion.py --ejecutar")
        return

    print("\nCreando tabla proveedor_asignacion_base...")
    confirmacion = input("Confirmar? (s/N): ").strip().lower()
    if confirmacion != "s":
        print("Cancelado.")
        return

    try:
        conn = pyodbc.connect(CONN_COMPRAS, timeout=15)
        cursor = conn.cursor()

        # 1. DROP + CREATE
        print("  Paso 1: DROP + CREATE TABLE...")
        cursor.execute("""
            IF OBJECT_ID('MSGESTION01.dbo.proveedor_asignacion_base','U') IS NOT NULL
                DROP TABLE MSGESTION01.dbo.proveedor_asignacion_base
        """)
        conn.commit()

        cursor.execute("""
            CREATE TABLE MSGESTION01.dbo.proveedor_asignacion_base (
                cuit                VARCHAR(15)     NOT NULL,
                cuenta_01           NUMERIC         NULL,
                cuenta_03           NUMERIC         NULL,
                denominacion        VARCHAR(100)    NOT NULL,
                tipo_asignacion     VARCHAR(20)     NOT NULL,
                pct_base_01         NUMERIC(5,1)    NOT NULL,
                pct_base_03         NUMERIC(5,1)    NOT NULL,
                total_facturado     NUMERIC(18,2)   NULL,
                cant_facturas_01    NUMERIC         NULL,
                cant_facturas_03    NUMERIC         NULL,
                fecha_calculo       DATETIME        DEFAULT GETDATE(),
                observaciones       VARCHAR(500)    NULL,
                CONSTRAINT PK_proveedor_asignacion PRIMARY KEY (cuit)
            )
        """)
        conn.commit()
        print("     OK")

        # 2. Proveedores SOLO en base 01
        print("  Paso 2: INSERT SOLO_01...")
        cursor.execute("""
            INSERT INTO MSGESTION01.dbo.proveedor_asignacion_base
                (cuit, cuenta_01, cuenta_03, denominacion, tipo_asignacion,
                 pct_base_01, pct_base_03, total_facturado, cant_facturas_01, cant_facturas_03)
            SELECT
                LTRIM(RTRIM(c01.numero_cuit)),
                MAX(c01.cuenta),
                NULL,
                MAX(c01.denominacion),
                'SOLO_01',
                100.0, 0.0,
                SUM(c01.monto_general),
                COUNT(*),
                0
            FROM MSGESTION01.dbo.compras2 c01
            WHERE c01.fecha_comprobante >= '2024-01-01' AND c01.fecha_comprobante <= GETDATE()
              AND c01.codigo IN (1,2) AND c01.estado = 'V'
              AND LEN(LTRIM(RTRIM(ISNULL(c01.numero_cuit,'')))) > 5
              AND NOT EXISTS (
                  SELECT 1 FROM MSGESTION03.dbo.compras2 c03
                  WHERE c03.fecha_comprobante >= '2024-01-01' AND c03.fecha_comprobante <= GETDATE()
                    AND c03.codigo IN (1,2) AND c03.estado = 'V'
                    AND LTRIM(RTRIM(c03.numero_cuit)) = LTRIM(RTRIM(c01.numero_cuit))
              )
            GROUP BY LTRIM(RTRIM(c01.numero_cuit))
        """)
        n1 = cursor.rowcount
        conn.commit()
        print(f"     {n1} proveedores")

        # 3. Proveedores SOLO en base 03
        print("  Paso 3: INSERT SOLO_03...")
        cursor.execute("""
            INSERT INTO MSGESTION01.dbo.proveedor_asignacion_base
                (cuit, cuenta_01, cuenta_03, denominacion, tipo_asignacion,
                 pct_base_01, pct_base_03, total_facturado, cant_facturas_01, cant_facturas_03)
            SELECT
                LTRIM(RTRIM(c03.numero_cuit)),
                NULL,
                MAX(c03.cuenta),
                MAX(c03.denominacion),
                'SOLO_03',
                0.0, 100.0,
                SUM(c03.monto_general),
                0,
                COUNT(*)
            FROM MSGESTION03.dbo.compras2 c03
            WHERE c03.fecha_comprobante >= '2024-01-01' AND c03.fecha_comprobante <= GETDATE()
              AND c03.codigo IN (1,2) AND c03.estado = 'V'
              AND LEN(LTRIM(RTRIM(ISNULL(c03.numero_cuit,'')))) > 5
              AND NOT EXISTS (
                  SELECT 1 FROM MSGESTION01.dbo.compras2 c01
                  WHERE c01.fecha_comprobante >= '2024-01-01' AND c01.fecha_comprobante <= GETDATE()
                    AND c01.codigo IN (1,2) AND c01.estado = 'V'
                    AND LTRIM(RTRIM(c01.numero_cuit)) = LTRIM(RTRIM(c03.numero_cuit))
              )
            GROUP BY LTRIM(RTRIM(c03.numero_cuit))
        """)
        n2 = cursor.rowcount
        conn.commit()
        print(f"     {n2} proveedores")

        # 4. Proveedores en AMBAS bases (con split %)
        print("  Paso 4: INSERT AMBAS...")
        cursor.execute("""
            INSERT INTO MSGESTION01.dbo.proveedor_asignacion_base
                (cuit, cuenta_01, cuenta_03, denominacion, tipo_asignacion,
                 pct_base_01, pct_base_03, total_facturado, cant_facturas_01, cant_facturas_03)
            SELECT
                t.cuit,
                t.cuenta_01,
                t.cuenta_03,
                t.denominacion,
                CASE
                    WHEN t.pct01 >= 95 THEN 'SOLO_01'
                    WHEN t.pct01 >= 65 THEN 'MAYORIA_01'
                    WHEN t.pct01 >= 35 THEN 'SPLIT'
                    WHEN t.pct01 >= 5  THEN 'MAYORIA_03'
                    ELSE 'SOLO_03'
                END,
                t.pct01,
                100.0 - t.pct01,
                t.total_01 + t.total_03,
                t.fc_01,
                t.fc_03
            FROM (
                SELECT
                    LTRIM(RTRIM(b01.cuit)) AS cuit,
                    b01.cuenta AS cuenta_01,
                    b03.cuenta AS cuenta_03,
                    b01.denominacion,
                    b01.total_monto AS total_01,
                    b03.total_monto AS total_03,
                    b01.cant_fc AS fc_01,
                    b03.cant_fc AS fc_03,
                    ROUND(CAST(b01.total_monto AS FLOAT)
                          / NULLIF(CAST(b01.total_monto + b03.total_monto AS FLOAT), 0) * 100, 1) AS pct01
                FROM (
                    SELECT LTRIM(RTRIM(numero_cuit)) AS cuit,
                           MAX(cuenta) AS cuenta, MAX(denominacion) AS denominacion,
                           COUNT(*) AS cant_fc, SUM(monto_general) AS total_monto
                    FROM MSGESTION01.dbo.compras2
                    WHERE fecha_comprobante >= '2024-01-01' AND fecha_comprobante <= GETDATE()
                      AND codigo IN (1,2) AND estado = 'V'
                      AND LEN(LTRIM(RTRIM(ISNULL(numero_cuit,'')))) > 5
                    GROUP BY LTRIM(RTRIM(numero_cuit))
                ) b01
                INNER JOIN (
                    SELECT LTRIM(RTRIM(numero_cuit)) AS cuit,
                           MAX(cuenta) AS cuenta, MAX(denominacion) AS denominacion,
                           COUNT(*) AS cant_fc, SUM(monto_general) AS total_monto
                    FROM MSGESTION03.dbo.compras2
                    WHERE fecha_comprobante >= '2024-01-01' AND fecha_comprobante <= GETDATE()
                      AND codigo IN (1,2) AND estado = 'V'
                      AND LEN(LTRIM(RTRIM(ISNULL(numero_cuit,'')))) > 5
                    GROUP BY LTRIM(RTRIM(numero_cuit))
                ) b03 ON b01.cuit = b03.cuit
            ) t
        """)
        n3 = cursor.rowcount
        conn.commit()
        print(f"     {n3} proveedores")

        # 5. Resumen
        cursor.execute("""
            SELECT tipo_asignacion, COUNT(*) as cant, AVG(pct_base_01) as prom_pct01
            FROM MSGESTION01.dbo.proveedor_asignacion_base
            GROUP BY tipo_asignacion ORDER BY prom_pct01 DESC
        """)
        print(f"\n  {'TIPO':<15} {'CANT':>5} {'%01 PROM':>8}")
        print(f"  {'-'*30}")
        for row in cursor.fetchall():
            print(f"  {row[0]:<15} {row[1]:>5} {row[2]:>7.1f}%")

        cursor.execute("SELECT COUNT(*) FROM MSGESTION01.dbo.proveedor_asignacion_base")
        total = cursor.fetchone()[0]
        print(f"\n  TOTAL: {total} proveedores mapeados")

        conn.close()

    except Exception as e:
        import traceback
        print(f"\n  ERROR: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
