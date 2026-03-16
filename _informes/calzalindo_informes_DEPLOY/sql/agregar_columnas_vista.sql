-- ============================================================
-- EJECUTAR EN: 192.168.2.111 (servidor web2py / produccion)
-- BASE: omicronvt  (SQL Server 2012 RTM - NO soporta TRY_CAST)
-- FIX: Pedidos solo de CALZALINDO (evita duplicacion ABI+H4)
--      Entregas via pedico1_entregas (vinculacion directa)
--      Columnas nuevas: rubro, grupo, linea
-- ============================================================
USE omicronvt;
GO

-- Primero verificar que el ALTER VIEW pueda correr
-- Si falla, se detiene aqui y NO sigue con el cache
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
        -- grupo es varchar(3), puede tener basura; ISNUMERIC safe para 2012
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
    WHERE p2.empresa = 'CALZALINDO'   -- Solo una empresa (evita duplicacion)
      AND a.subrubro > 0
      AND p1.articulo > 0
) ped
OUTER APPLY (
    -- Entregas registradas directamente contra este renglon del pedido
    -- Usa pedico1_entregas (tabla nativa del ERP) en AMBAS bases
    SELECT
        SUM(pe.cantidad)                    AS cant_recibida,
        MIN(pe.fecha_entrega)               AS primera_recepcion,
        MAX(pe.fecha_entrega)               AS ultima_recepcion
    FROM (
        SELECT cantidad, fecha_entrega
        FROM msgestion01.dbo.pedico1_entregas
        WHERE codigo   = 8
          AND letra    = 'X'
          AND sucursal = ped.sucursal
          AND numero   = ped.numero
          AND orden    = ped.orden
          AND renglon  = ped.renglon
        UNION ALL
        SELECT cantidad, fecha_entrega
        FROM msgestion03.dbo.pedico1_entregas
        WHERE codigo   = 8
          AND letra    = 'X'
          AND sucursal = ped.sucursal
          AND numero   = ped.numero
          AND orden    = ped.orden
          AND renglon  = ped.renglon
    ) pe
) recib;
GO

-- Recrear la cache (DROP + SELECT INTO para agregar columnas nuevas)
IF OBJECT_ID('dbo.pedidos_cumplimiento_cache', 'U') IS NOT NULL
    DROP TABLE dbo.pedidos_cumplimiento_cache;
GO

SELECT *
INTO dbo.pedidos_cumplimiento_cache
FROM dbo.v_pedidos_cumplimiento;
GO

-- Recrear indices
CREATE NONCLUSTERED INDEX IX_cache_proveedor
    ON dbo.pedidos_cumplimiento_cache (cod_proveedor, proveedor);
CREATE NONCLUSTERED INDEX IX_cache_estado
    ON dbo.pedidos_cumplimiento_cache (estado_cumplimiento);
CREATE NONCLUSTERED INDEX IX_cache_alerta
    ON dbo.pedidos_cumplimiento_cache (alerta_vencimiento)
    INCLUDE (monto_pendiente, cod_proveedor);
CREATE NONCLUSTERED INDEX IX_cache_industria
    ON dbo.pedidos_cumplimiento_cache (industria);
CREATE NONCLUSTERED INDEX IX_cache_fecha
    ON dbo.pedidos_cumplimiento_cache (fecha_pedido);
CREATE NONCLUSTERED INDEX IX_cache_rubro
    ON dbo.pedidos_cumplimiento_cache (rubro_desc);
CREATE NONCLUSTERED INDEX IX_cache_linea
    ON dbo.pedidos_cumplimiento_cache (linea_desc);
GO

-- Crear o actualizar el SP de sync
IF OBJECT_ID('dbo.sp_sync_pedidos', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_sync_pedidos;
GO

CREATE PROCEDURE dbo.sp_sync_pedidos
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        TRUNCATE TABLE dbo.pedidos_cumplimiento_cache;
        INSERT INTO dbo.pedidos_cumplimiento_cache
        SELECT * FROM dbo.v_pedidos_cumplimiento;
        SELECT @@ROWCOUNT AS filas_actualizadas;
    END TRY
    BEGIN CATCH
        DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
    END CATCH
END;
GO

PRINT 'OK - Vista usa pedico1_entregas, pedidos solo CALZALINDO, cache+SP recreados.';
GO
