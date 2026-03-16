#!/usr/bin/env python3
"""
poblar_asignacion.py
Version simplificada de crear_tabla_asignacion.py
sin problemas de comentarios SQL ni imports.

EJECUTAR EN EL 111:
  cd C:\cowork_pedidos && set PYTHONPATH=C:\cowork_pedidos && py -3 _scripts_oneshot\poblar_asignacion.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyodbc
from config import CONN_COMPRAS

def main():
    conn = pyodbc.connect(CONN_COMPRAS, timeout=15)
    cur = conn.cursor()

    # 1. DROP + CREATE
    print("  1. Recreando tabla...")
    cur.execute("IF OBJECT_ID('MSGESTION01.dbo.proveedor_asignacion_base','U') IS NOT NULL DROP TABLE MSGESTION01.dbo.proveedor_asignacion_base")
    conn.commit()

    cur.execute("""
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
    print("     Tabla creada OK")

    # 2. SOLO_01
    print("  2. Insertando proveedores SOLO base 01...")
    cur.execute("""
    INSERT INTO MSGESTION01.dbo.proveedor_asignacion_base
        (cuit, cuenta_01, cuenta_03, denominacion, tipo_asignacion, pct_base_01, pct_base_03, total_facturado, cant_facturas_01, cant_facturas_03)
    SELECT
        LTRIM(RTRIM(c01.numero_cuit)),
        c01.cuenta, NULL, c01.denominacion, 'SOLO_01',
        100.0, 0.0, c01.total_monto, c01.cant_fc, 0
    FROM (
        SELECT cuenta, denominacion, numero_cuit, COUNT(*) as cant_fc, SUM(monto_general) as total_monto
        FROM MSGESTION01.dbo.compras2
        WHERE fecha_comprobante >= '2024-01-01' AND fecha_comprobante <= GETDATE()
          AND codigo IN (1,2) AND estado = 'V'
          AND LEN(LTRIM(RTRIM(ISNULL(numero_cuit,'')))) > 5
        GROUP BY cuenta, denominacion, numero_cuit
    ) c01
    WHERE NOT EXISTS (
        SELECT 1 FROM (
            SELECT numero_cuit
            FROM MSGESTION03.dbo.compras2
            WHERE fecha_comprobante >= '2024-01-01' AND fecha_comprobante <= GETDATE()
              AND codigo IN (1,2) AND estado = 'V'
              AND LEN(LTRIM(RTRIM(ISNULL(numero_cuit,'')))) > 5
            GROUP BY numero_cuit
        ) c03 WHERE LTRIM(RTRIM(c03.numero_cuit)) = LTRIM(RTRIM(c01.numero_cuit))
    )
    """)
    n1 = cur.rowcount
    conn.commit()
    print(f"     {n1} proveedores SOLO_01")

    # 3. SOLO_03
    print("  3. Insertando proveedores SOLO base 03...")
    cur.execute("""
    INSERT INTO MSGESTION01.dbo.proveedor_asignacion_base
        (cuit, cuenta_01, cuenta_03, denominacion, tipo_asignacion, pct_base_01, pct_base_03, total_facturado, cant_facturas_01, cant_facturas_03)
    SELECT
        LTRIM(RTRIM(c03.numero_cuit)),
        NULL, c03.cuenta, c03.denominacion, 'SOLO_03',
        0.0, 100.0, c03.total_monto, 0, c03.cant_fc
    FROM (
        SELECT cuenta, denominacion, numero_cuit, COUNT(*) as cant_fc, SUM(monto_general) as total_monto
        FROM MSGESTION03.dbo.compras2
        WHERE fecha_comprobante >= '2024-01-01' AND fecha_comprobante <= GETDATE()
          AND codigo IN (1,2) AND estado = 'V'
          AND LEN(LTRIM(RTRIM(ISNULL(numero_cuit,'')))) > 5
        GROUP BY cuenta, denominacion, numero_cuit
    ) c03
    WHERE NOT EXISTS (
        SELECT 1 FROM (
            SELECT numero_cuit
            FROM MSGESTION01.dbo.compras2
            WHERE fecha_comprobante >= '2024-01-01' AND fecha_comprobante <= GETDATE()
              AND codigo IN (1,2) AND estado = 'V'
              AND LEN(LTRIM(RTRIM(ISNULL(numero_cuit,'')))) > 5
            GROUP BY numero_cuit
        ) c01 WHERE LTRIM(RTRIM(c01.numero_cuit)) = LTRIM(RTRIM(c03.numero_cuit))
    )
    """)
    n2 = cur.rowcount
    conn.commit()
    print(f"     {n2} proveedores SOLO_03")

    # 4. AMBAS BASES (split)
    print("  4. Insertando proveedores en AMBAS bases...")
    cur.execute("""
    INSERT INTO MSGESTION01.dbo.proveedor_asignacion_base
        (cuit, cuenta_01, cuenta_03, denominacion, tipo_asignacion, pct_base_01, pct_base_03, total_facturado, cant_facturas_01, cant_facturas_03)
    SELECT
        LTRIM(RTRIM(c01.numero_cuit)),
        c01.cuenta, c03.cuenta, c01.denominacion,
        CASE
            WHEN CAST(c01.total_monto AS FLOAT) / NULLIF(CAST(c01.total_monto + c03.total_monto AS FLOAT), 0) * 100 >= 95 THEN 'SOLO_01'
            WHEN CAST(c01.total_monto AS FLOAT) / NULLIF(CAST(c01.total_monto + c03.total_monto AS FLOAT), 0) * 100 >= 65 THEN 'MAYORIA_01'
            WHEN CAST(c01.total_monto AS FLOAT) / NULLIF(CAST(c01.total_monto + c03.total_monto AS FLOAT), 0) * 100 >= 35 THEN 'SPLIT'
            WHEN CAST(c01.total_monto AS FLOAT) / NULLIF(CAST(c01.total_monto + c03.total_monto AS FLOAT), 0) * 100 >= 5  THEN 'MAYORIA_03'
            ELSE 'SOLO_03'
        END,
        ROUND(CAST(c01.total_monto AS FLOAT) / NULLIF(CAST(c01.total_monto + c03.total_monto AS FLOAT), 0) * 100, 1),
        ROUND(CAST(c03.total_monto AS FLOAT) / NULLIF(CAST(c01.total_monto + c03.total_monto AS FLOAT), 0) * 100, 1),
        c01.total_monto + c03.total_monto,
        c01.cant_fc, c03.cant_fc
    FROM (
        SELECT cuenta, denominacion, numero_cuit, COUNT(*) as cant_fc, SUM(monto_general) as total_monto
        FROM MSGESTION01.dbo.compras2
        WHERE fecha_comprobante >= '2024-01-01' AND fecha_comprobante <= GETDATE()
          AND codigo IN (1,2) AND estado = 'V'
          AND LEN(LTRIM(RTRIM(ISNULL(numero_cuit,'')))) > 5
        GROUP BY cuenta, denominacion, numero_cuit
    ) c01
    INNER JOIN (
        SELECT cuenta, denominacion, numero_cuit, COUNT(*) as cant_fc, SUM(monto_general) as total_monto
        FROM MSGESTION03.dbo.compras2
        WHERE fecha_comprobante >= '2024-01-01' AND fecha_comprobante <= GETDATE()
          AND codigo IN (1,2) AND estado = 'V'
          AND LEN(LTRIM(RTRIM(ISNULL(numero_cuit,'')))) > 5
        GROUP BY cuenta, denominacion, numero_cuit
    ) c03 ON LTRIM(RTRIM(c01.numero_cuit)) = LTRIM(RTRIM(c03.numero_cuit))
    """)
    n3 = cur.rowcount
    conn.commit()
    print(f"     {n3} proveedores AMBAS")

    # 5. Resumen
    cur.execute("""
        SELECT tipo_asignacion, COUNT(*) as cant, AVG(pct_base_01) as prom_pct01
        FROM MSGESTION01.dbo.proveedor_asignacion_base
        GROUP BY tipo_asignacion ORDER BY prom_pct01 DESC
    """)
    print(f"\n  {'TIPO':<15} {'CANT':>5} {'%01 PROM':>8}")
    print(f"  {'-'*30}")
    for row in cur.fetchall():
        print(f"  {row[0]:<15} {row[1]:>5} {row[2]:>7.1f}%")

    cur.execute("SELECT COUNT(*) FROM MSGESTION01.dbo.proveedor_asignacion_base")
    total = cur.fetchone()[0]
    print(f"\n  TOTAL: {total} proveedores mapeados")
    conn.close()

if __name__ == "__main__":
    main()
