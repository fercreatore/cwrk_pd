-- ============================================================
-- EJECUTAR EN: 192.168.2.111 (servidor web2py / produccion)
-- BASE: omicronvt
-- FIX: Cambia LEFT JOIN de marcas de msgestion01art a msgestionC
--      (la tabla msgestion01art.dbo.marcas esta vacia)
-- ============================================================
USE omicronvt;
GO

ALTER VIEW dbo.v_pedidos_cumplimiento
AS
SELECT
    ped.empresa,
    ped.cod_proveedor,
    ped.proveedor,
    ped.fecha_pedido,
    ped.tipo_comprobante,
    ped.letra,
    ped.sucursal,
    ped.numero,
    ped.renglon,
    ped.articulo,
    ped.descripcion,
    ped.marca,
    ped.industria,
    ped.cod_subrubro,
    ped.subrubro_desc,

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
        p2.empresa,
        p2.cuenta                           AS cod_proveedor,
        RTRIM(p2.denominacion)              AS proveedor,
        p2.fecha_comprobante                AS fecha_pedido,
        p2.codigo                           AS tipo_comprobante,
        p2.letra,
        p2.sucursal,
        p2.numero,
        p2.estado                           AS estado_pedido,
        p1.renglon,
        p1.articulo,
        a.descripcion_1                     AS descripcion,
        m.descripcion                       AS marca,        -- << FIX: ahora viene de msgestionC
        ind.industria,
        a.subrubro                          AS cod_subrubro,
        sr.descripcion                      AS subrubro_desc,
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
    LEFT JOIN msgestionC.dbo.marcas m       -- << FIX: era msgestion01art.dbo.marcas (vacia)
        ON a.marca = m.codigo
    LEFT JOIN omicronvt.dbo.map_subrubro_industria ind
        ON a.subrubro = ind.subrubro
    LEFT JOIN msgestionC.dbo.subrubro sr
        ON a.subrubro = sr.codigo
    WHERE a.subrubro > 0
      AND p1.articulo > 0
) ped
LEFT JOIN (
    SELECT
        c2.cuenta                           AS cod_proveedor,
        c1.articulo,
        SUM(CASE
            WHEN c2.codigo = 1 THEN c1.cantidad
            WHEN c2.codigo = 3 THEN -c1.cantidad
            ELSE 0
        END)                                AS cant_recibida,
        MIN(c2.fecha_comprobante)           AS primera_recepcion,
        MAX(c2.fecha_comprobante)           AS ultima_recepcion
    FROM msgestionC.dbo.compras1 c1
    JOIN msgestionC.dbo.compras2 c2
        ON  c1.empresa  = c2.empresa
        AND c1.codigo   = c2.codigo
        AND c1.letra    = c2.letra
        AND c1.sucursal = c2.sucursal
        AND c1.numero   = c2.numero
        AND c1.orden    = c2.orden
    WHERE c2.codigo IN (1, 3)
      AND c2.fecha_comprobante >= (
          SELECT MIN(fecha_comprobante)
          FROM msgestionC.dbo.pedico2
      )
    GROUP BY c2.cuenta, c1.articulo
) recib
    ON  recib.cod_proveedor = ped.cod_proveedor
    AND recib.articulo      = ped.articulo;
GO

-- Refrescar la cache con la vista corregida
EXEC dbo.sp_sync_pedidos;
GO

PRINT 'OK - Vista corregida (marcas desde msgestionC) y cache actualizada.';
GO
