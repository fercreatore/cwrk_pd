#!/usr/bin/env python3
"""
fix_view_pedidos_cumplimiento.py
================================
Corrige la view v_pedidos_cumplimiento en omicronvt.

PROBLEMA: El OUTER APPLY suma pedico1_entregas + compras1 remitos,
pero el remito crea AMBOS registros, duplicando el conteo de entregas.

FIX: Prioridad con fallback.
  - Si pedico1_entregas tiene datos para ese renglon → usar esos (es mas preciso)
  - Si NO tiene entregas → fallback a compras1 remitos (pedidos viejos)
  Asi nunca se duplica.

Uso:
    py -3 fix_view_pedidos_cumplimiento.py          # dry-run
    py -3 fix_view_pedidos_cumplimiento.py --ejecutar
"""
import sys
import pyodbc

DRY_RUN = '--ejecutar' not in sys.argv

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
-- Fuente A: pedico1_entregas (precisa, por renglon)
OUTER APPLY (
    SELECT
        SUM(pe.cantidad)        AS cant_recibida,
        MIN(pe.fecha_recepcion) AS primera_recepcion,
        MAX(pe.fecha_recepcion) AS ultima_recepcion
    FROM (
        SELECT cantidad, fecha_entrega AS fecha_recepcion
        FROM msgestion01.dbo.pedico1_entregas
        WHERE codigo = 8 AND letra = 'X'
          AND sucursal = ped.sucursal AND numero = ped.numero
          AND orden = ped.orden AND renglon = ped.renglon
        UNION ALL
        SELECT cantidad, fecha_entrega AS fecha_recepcion
        FROM msgestion03.dbo.pedico1_entregas
        WHERE codigo = 8 AND letra = 'X'
          AND sucursal = ped.sucursal AND numero = ped.numero
          AND orden = ped.orden AND renglon = ped.renglon
    ) pe
) entregas
-- Fuente B: compras1 remitos (fallback para pedidos sin entregas)
OUTER APPLY (
    SELECT
        SUM(pe.cantidad)        AS cant_recibida,
        MIN(pe.fecha_recepcion) AS primera_recepcion,
        MAX(pe.fecha_recepcion) AS ultima_recepcion
    FROM (
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
) remitos
-- PRIORIDAD: si hay entregas usar entregas, si no fallback a remitos
CROSS APPLY (
    SELECT
        CASE WHEN ISNULL(entregas.cant_recibida, 0) > 0
             THEN entregas.cant_recibida
             ELSE ISNULL(remitos.cant_recibida, 0)
        END AS cant_recibida,
        CASE WHEN ISNULL(entregas.cant_recibida, 0) > 0
             THEN entregas.primera_recepcion
             ELSE remitos.primera_recepcion
        END AS primera_recepcion,
        CASE WHEN ISNULL(entregas.cant_recibida, 0) > 0
             THEN entregas.ultima_recepcion
             ELSE remitos.ultima_recepcion
        END AS ultima_recepcion
) recib
"""

# Tambien actualizar la cache despues
REFRESH_CACHE_SQL = """
TRUNCATE TABLE omicronvt.dbo.pedidos_cumplimiento_cache;
INSERT INTO omicronvt.dbo.pedidos_cumplimiento_cache
SELECT * FROM omicronvt.dbo.v_pedidos_cumplimiento;
"""

def main():
    if DRY_RUN:
        print("=" * 60)
        print("DRY-RUN — No se ejecuta nada")
        print("=" * 60)
        print()
        print("Se va a:")
        print("  1. ALTER VIEW v_pedidos_cumplimiento (quitar compras1 del OUTER APPLY)")
        print("  2. TRUNCATE + INSERT pedidos_cumplimiento_cache")
        print()
        print("Ejecutar con: py -3 fix_view_pedidos_cumplimiento.py --ejecutar")
        return

    conn = pyodbc.connect(
        'DRIVER={SQL Server};SERVER=192.168.2.111;DATABASE=omicronvt;UID=am;PWD=dl',
        autocommit=True  # ALTER VIEW requiere autocommit
    )
    cursor = conn.cursor()

    print("=" * 60)
    print("PASO 1: ALTER VIEW v_pedidos_cumplimiento")
    print("=" * 60)
    cursor.execute(ALTER_VIEW_SQL)
    print("  VIEW alterada OK")

    print()
    print("=" * 60)
    print("PASO 2: Refrescar cache")
    print("=" * 60)
    # Ejecutar TRUNCATE y INSERT por separado
    cursor.execute("TRUNCATE TABLE omicronvt.dbo.pedidos_cumplimiento_cache")
    print("  TRUNCATE OK")
    cursor.execute("""
        INSERT INTO omicronvt.dbo.pedidos_cumplimiento_cache
        SELECT * FROM omicronvt.dbo.v_pedidos_cumplimiento
    """)
    print(f"  INSERT OK — {cursor.rowcount} filas")

    cursor.close()
    conn.close()
    print()
    print("=== COMPLETADO ===")


if __name__ == '__main__':
    main()
