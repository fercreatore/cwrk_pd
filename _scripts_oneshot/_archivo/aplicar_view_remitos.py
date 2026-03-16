#!/usr/bin/env python3
"""
aplicar_view_remitos.py
========================
Modifica la vista v_pedidos_cumplimiento en omicronvt para que
cruce remitos de compra (compras1/compras2) con notas de pedido,
ademas de pedico1_entregas (fuente original).

Luego ejecuta sp_sync_pedidos para refrescar la cache.

Ejecutar en 192.168.2.111:
    py -3 aplicar_view_remitos.py --ejecutar

Modo seguro (solo muestra SQL):
    py -3 aplicar_view_remitos.py --dry-run
"""

import argparse
import pyodbc
import sys

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=omicronvt;"
    "UID=am;PWD=dl"
)

ALTER_VIEW_SQL = """
ALTER VIEW dbo.v_pedidos_cumplimiento
AS
SELECT
    ped.cod_proveedor,
    ped.proveedor,
    ped.fecha_pedido,
    ped.tipo_comprobante,
    ped.letra,
    ped.sucursal,
    ped.numero,
    ped.orden,
    ped.renglon,
    ped.articulo,
    ped.descripcion,
    ped.marca,
    ped.industria,
    ped.cod_rubro,
    ped.rubro_desc,
    ped.cod_subrubro,
    ped.subrubro_desc,
    ped.cod_grupo,
    ped.grupo_desc,
    ped.cod_linea,
    ped.linea_desc,

    ped.cant_pedida,
    ISNULL(recib.cant_recibida, 0)          AS cant_recibida,
    ped.cant_pedida
        - ISNULL(recib.cant_recibida, 0)    AS cant_pendiente,

    CASE
        WHEN ISNULL(recib.cant_recibida, 0) >= ped.cant_pedida THEN 'COMPLETO'
        WHEN ISNULL(recib.cant_recibida, 0) > 0                THEN 'PARCIAL'
        ELSE 'PENDIENTE'
    END                                     AS estado_cumplimiento,

    CASE
        WHEN ped.cant_pedida = 0 THEN 0
        ELSE ROUND(
            ISNULL(recib.cant_recibida, 0) * 100.0
            / ped.cant_pedida, 1)
    END                                     AS pct_cumplido,

    ped.precio_unitario,
    ped.cant_pedida * ped.precio_unitario    AS monto_pedido,
    (ped.cant_pedida
        - ISNULL(recib.cant_recibida, 0))
     * ped.precio_unitario                   AS monto_pendiente,

    DATEDIFF(DAY, ped.fecha_pedido, GETDATE()) AS dias_desde_pedido,
    ped.fecha_entrega,
    CASE
        WHEN ped.fecha_entrega IS NOT NULL
         AND ped.fecha_entrega < GETDATE()
         AND ISNULL(recib.cant_recibida, 0) < ped.cant_pedida
            THEN 'VENCIDO'
        ELSE NULL
    END                                     AS alerta_vencimiento,
    recib.primera_recepcion,
    recib.ultima_recepcion,
    ped.estado_pedido,
    ped.estado_linea

FROM (
    SELECT
        p2.cuenta                           AS cod_proveedor,
        RTRIM(p2.denominacion)              AS proveedor,
        p2.fecha_comprobante                AS fecha_pedido,
        p2.codigo                           AS tipo_comprobante,
        p2.letra,
        p2.sucursal,
        p2.numero,
        p2.orden,
        p2.estado                           AS estado_pedido,
        p1.renglon,
        p1.articulo,
        a.descripcion_1                     AS descripcion,
        m.descripcion                       AS marca,
        ind.industria,
        a.rubro                             AS cod_rubro,
        r.descripcion                       AS rubro_desc,
        a.subrubro                          AS cod_subrubro,
        sr.descripcion                      AS subrubro_desc,
        CASE WHEN ISNUMERIC(a.grupo) = 1
             THEN CAST(a.grupo AS INT)
             ELSE 0
        END                                 AS cod_grupo,
        g.descripcion                       AS grupo_desc,
        a.linea                             AS cod_linea,
        l.descripcion                       AS linea_desc,
        p1.cantidad                         AS cant_pedida,
        p1.precio                           AS precio_unitario,
        p1.fecha_entrega,
        p1.estado                           AS estado_linea
    FROM msgestionC.dbo.pedico1 p1
    JOIN msgestionC.dbo.pedico2 p2
        ON  p1.empresa  = p2.empresa
        AND p1.codigo   = p2.codigo
        AND p1.letra    = p2.letra
        AND p1.sucursal = p2.sucursal
        AND p1.numero   = p2.numero
        AND p1.orden    = p2.orden
    JOIN msgestion01art.dbo.articulo a
        ON p1.articulo = a.codigo
    LEFT JOIN msgestionC.dbo.marcas m
        ON a.marca = m.codigo
    LEFT JOIN omicronvt.dbo.map_subrubro_industria ind
        ON a.subrubro = ind.subrubro
    LEFT JOIN msgestionC.dbo.subrubro sr
        ON a.subrubro = sr.codigo
    LEFT JOIN msgestionC.dbo.rubros r
        ON a.rubro = r.codigo
    LEFT JOIN msgestionC.dbo.grupos g
        ON CASE WHEN ISNUMERIC(a.grupo) = 1
                THEN CAST(a.grupo AS INT)
                ELSE -1
           END = g.codigo
    LEFT JOIN msgestionC.dbo.lineas l
        ON a.linea = l.codigo
    WHERE p2.empresa = 'CALZALINDO'
      AND a.subrubro > 0
      AND p1.articulo > 0
) ped
OUTER APPLY (
    SELECT
        SUM(pe.cantidad)                    AS cant_recibida,
        MIN(pe.fecha_recepcion)             AS primera_recepcion,
        MAX(pe.fecha_recepcion)             AS ultima_recepcion
    FROM (
        -- Fuente 1: pedico1_entregas msgestion01 (ERP nativo)
        SELECT cantidad, fecha_entrega AS fecha_recepcion
        FROM msgestion01.dbo.pedico1_entregas
        WHERE codigo   = 8
          AND letra    = 'X'
          AND sucursal = ped.sucursal
          AND numero   = ped.numero
          AND orden    = ped.orden
          AND renglon  = ped.renglon

        UNION ALL

        -- Fuente 2: pedico1_entregas msgestion03 (ERP nativo)
        SELECT cantidad, fecha_entrega AS fecha_recepcion
        FROM msgestion03.dbo.pedico1_entregas
        WHERE codigo   = 8
          AND letra    = 'X'
          AND sucursal = ped.sucursal
          AND numero   = ped.numero
          AND orden    = ped.orden
          AND renglon  = ped.renglon

        UNION ALL

        -- Fuente 3: remitos de compra msgestion01 (codigo=7, operacion='+')
        SELECT c1.cantidad, c2.fecha_comprobante AS fecha_recepcion
        FROM msgestion01.dbo.compras1 c1
        JOIN msgestion01.dbo.compras2 c2
            ON  c1.codigo   = c2.codigo
            AND c1.letra    = c2.letra
            AND c1.sucursal = c2.sucursal
            AND c1.numero   = c2.numero
        WHERE c1.articulo   = ped.articulo
          AND c2.cuenta     = ped.cod_proveedor
          AND c1.operacion  = '+'
          AND c2.codigo     = 7
          AND c2.fecha_comprobante >= ped.fecha_pedido

        UNION ALL

        -- Fuente 4: remitos de compra msgestion03 (codigo=7, operacion='+')
        SELECT c1.cantidad, c2.fecha_comprobante AS fecha_recepcion
        FROM msgestion03.dbo.compras1 c1
        JOIN msgestion03.dbo.compras2 c2
            ON  c1.codigo   = c2.codigo
            AND c1.letra    = c2.letra
            AND c1.sucursal = c2.sucursal
            AND c1.numero   = c2.numero
        WHERE c1.articulo   = ped.articulo
          AND c2.cuenta     = ped.cod_proveedor
          AND c1.operacion  = '+'
          AND c2.codigo     = 7
          AND c2.fecha_comprobante >= ped.fecha_pedido
    ) pe
) recib
"""

SYNC_CACHE_SQL = "EXEC omicronvt.dbo.sp_sync_pedidos"

VERIFY_SQL = """
SELECT estado_cumplimiento, COUNT(*) as lineas, SUM(cant_pedida) as pedido,
       SUM(cant_recibida) as recibido, SUM(cant_pendiente) as pendiente
FROM omicronvt.dbo.pedidos_cumplimiento_cache
WHERE cod_proveedor = 561
GROUP BY estado_cumplimiento
ORDER BY estado_cumplimiento
"""


def main():
    parser = argparse.ArgumentParser(description="Aplica ALTER VIEW + sync cache pedidos")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--dry-run", action="store_true", help="Solo muestra SQL, no ejecuta")
    group.add_argument("--ejecutar", action="store_true", help="Ejecuta en produccion")
    args = parser.parse_args()

    if args.dry_run:
        print("=" * 60)
        print("DRY RUN — SQL que se ejecutaria:")
        print("=" * 60)
        print("\n--- PASO 1: ALTER VIEW ---")
        print(ALTER_VIEW_SQL[:200] + "\n... (vista completa en alter_view_pedidos_cumplimiento.sql)")
        print("\n--- PASO 2: SYNC CACHE ---")
        print(SYNC_CACHE_SQL)
        print("\n--- PASO 3: VERIFICACION ---")
        print(VERIFY_SQL)
        print("\nPara ejecutar: py -3 aplicar_view_remitos.py --ejecutar")
        return

    # --- EJECUTAR ---
    print("Conectando a 192.168.2.111 / omicronvt ...")
    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()

    # Paso 1: ALTER VIEW
    print("\n[PASO 1] ALTER VIEW dbo.v_pedidos_cumplimiento ...")
    try:
        cursor.execute(ALTER_VIEW_SQL)
        print("  OK — Vista modificada.")
    except pyodbc.Error as e:
        print(f"  ERROR: {e}")
        conn.close()
        sys.exit(1)

    # Paso 2: Sync cache
    print("\n[PASO 2] EXEC sp_sync_pedidos (refrescar cache) ...")
    try:
        cursor.execute(SYNC_CACHE_SQL)
        row = cursor.fetchone()
        if row:
            print(f"  OK — {row[0]} filas actualizadas en cache.")
        else:
            print("  OK — Cache refrescada.")
    except pyodbc.Error as e:
        print(f"  ERROR: {e}")
        conn.close()
        sys.exit(1)

    # Paso 3: Verificar resultado para Souter
    print("\n[PASO 3] Verificacion — Souter S.A. (561):")
    try:
        cursor.execute(VERIFY_SQL)
        rows = cursor.fetchall()
        print(f"  {'Estado':<15} {'Lineas':>8} {'Pedido':>8} {'Recibido':>10} {'Pendiente':>10}")
        print("  " + "-" * 55)
        for r in rows:
            print(f"  {r[0]:<15} {r[1]:>8} {r[2]:>8} {r[3]:>10} {r[4]:>10}")
    except pyodbc.Error as e:
        print(f"  ERROR verificacion: {e}")

    conn.close()
    print("\nListo. Recarga el reporte en calzalindo_informes.")


if __name__ == "__main__":
    main()
