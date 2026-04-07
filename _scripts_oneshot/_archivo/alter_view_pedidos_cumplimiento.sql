-- ============================================================================
-- ALTER VIEW v_pedidos_cumplimiento
-- Agrega cruce con remitos de compra (compras1/compras2)
-- para calcular cant_recibida cuando pedico1_entregas no se llena
--
-- Cambio: el OUTER APPLY ahora busca en 3 fuentes:
--   1) pedico1_entregas msg01 (ERP nativo)
--   2) pedico1_entregas msg03 (ERP nativo)
--   3) compras1 remitos msg01 (codigo=7, operacion='+', mismo articulo+proveedor)
--   4) compras1 remitos msg03 (idem)
--
-- Ejecutar en: 192.168.2.111 / omicronvt
-- Fecha: 2026-03-09
-- ============================================================================

USE omicronvt;
GO

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
    -- Entregas: combina pedico1_entregas (ERP nativo) + remitos de compra (compras1)
    SELECT
        SUM(pe.cantidad)                    AS cant_recibida,
        MIN(pe.fecha_recepcion)             AS primera_recepcion,
        MAX(pe.fecha_recepcion)             AS ultima_recepcion
    FROM (
        -- Fuente 1: pedico1_entregas msgestion01
        SELECT cantidad, fecha_entrega AS fecha_recepcion
        FROM msgestion01.dbo.pedico1_entregas
        WHERE codigo   = 8
          AND letra    = 'X'
          AND sucursal = ped.sucursal
          AND numero   = ped.numero
          AND orden    = ped.orden
          AND renglon  = ped.renglon

        UNION ALL

        -- Fuente 2: pedico1_entregas msgestion03
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
        -- Cruce por articulo + proveedor + fecha remito >= fecha pedido
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
          AND c2.codigo     = 7          -- remito de compra
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
          AND c2.codigo     = 7          -- remito de compra
          AND c2.fecha_comprobante >= ped.fecha_pedido
    ) pe
) recib;
GO
