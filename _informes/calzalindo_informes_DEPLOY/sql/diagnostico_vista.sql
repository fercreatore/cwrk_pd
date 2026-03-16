-- ============================================================
-- DIAGNOSTICO: por que falla el ALTER VIEW en este servidor
-- Ejecutar en SSMS conectado a 192.168.2.111
-- ============================================================
USE omicronvt;
GO

-- 1) Identificar servidor y version
PRINT '=== SERVIDOR ==='
PRINT @@SERVERNAME + ' / ' + @@VERSION
PRINT 'Compatibility level omicronvt: ' + CAST((SELECT compatibility_level FROM sys.databases WHERE name = 'omicronvt') AS VARCHAR)
GO

-- 2) Verificar que estamos en .111
PRINT ''
PRINT '=== VERIFICAR IP ==='
DECLARE @ip VARCHAR(50)
SELECT @ip = local_net_address FROM sys.dm_exec_connections WHERE session_id = @@SPID
PRINT 'IP local: ' + ISNULL(@ip, '(null - verificar permisos)')
GO

-- 3) Verificar existencia de bases referenciadas
PRINT ''
PRINT '=== BASES DE DATOS ==='
IF DB_ID('msgestionC') IS NOT NULL PRINT 'msgestionC: OK (id=' + CAST(DB_ID('msgestionC') AS VARCHAR) + ')'
ELSE PRINT 'msgestionC: NO EXISTE'

IF DB_ID('msgestion01') IS NOT NULL PRINT 'msgestion01: OK (id=' + CAST(DB_ID('msgestion01') AS VARCHAR) + ')'
ELSE PRINT 'msgestion01: NO EXISTE <<<< PROBLEMA!'

IF DB_ID('msgestion03') IS NOT NULL PRINT 'msgestion03: OK (id=' + CAST(DB_ID('msgestion03') AS VARCHAR) + ')'
ELSE PRINT 'msgestion03: NO EXISTE <<<< PROBLEMA!'

IF DB_ID('msgestion01art') IS NOT NULL PRINT 'msgestion01art: OK (id=' + CAST(DB_ID('msgestion01art') AS VARCHAR) + ')'
ELSE PRINT 'msgestion01art: NO EXISTE'
GO

-- 4) Verificar tablas especificas
PRINT ''
PRINT '=== TABLAS CRITICAS ==='

-- pedico1_entregas en msgestion01
IF OBJECT_ID('msgestion01.dbo.pedico1_entregas') IS NOT NULL
    PRINT 'msgestion01.dbo.pedico1_entregas: OK'
ELSE
    PRINT 'msgestion01.dbo.pedico1_entregas: NO EXISTE <<<< PROBLEMA!'

-- pedico1_entregas en msgestion03
IF OBJECT_ID('msgestion03.dbo.pedico1_entregas') IS NOT NULL
    PRINT 'msgestion03.dbo.pedico1_entregas: OK'
ELSE
    PRINT 'msgestion03.dbo.pedico1_entregas: NO EXISTE <<<< PROBLEMA!'

-- rubros en msgestionC
IF OBJECT_ID('msgestionC.dbo.rubros') IS NOT NULL
    PRINT 'msgestionC.dbo.rubros: OK'
ELSE
    PRINT 'msgestionC.dbo.rubros: NO EXISTE <<<< PROBLEMA!'

-- grupos en msgestionC
IF OBJECT_ID('msgestionC.dbo.grupos') IS NOT NULL
    PRINT 'msgestionC.dbo.grupos: OK'
ELSE
    PRINT 'msgestionC.dbo.grupos: NO EXISTE <<<< PROBLEMA!'

-- lineas en msgestionC
IF OBJECT_ID('msgestionC.dbo.lineas') IS NOT NULL
    PRINT 'msgestionC.dbo.lineas: OK'
ELSE
    PRINT 'msgestionC.dbo.lineas: NO EXISTE <<<< PROBLEMA!'

-- marcas en msgestionC
IF OBJECT_ID('msgestionC.dbo.marcas') IS NOT NULL
    PRINT 'msgestionC.dbo.marcas: OK'
ELSE
    PRINT 'msgestionC.dbo.marcas: NO EXISTE <<<< PROBLEMA (la vista vieja usa msgestion01art.dbo.marcas)!'

-- map_subrubro_industria
IF OBJECT_ID('omicronvt.dbo.map_subrubro_industria') IS NOT NULL
    PRINT 'omicronvt.dbo.map_subrubro_industria: OK'
ELSE
    PRINT 'omicronvt.dbo.map_subrubro_industria: NO EXISTE'
GO

-- 5) Probar ISNUMERIC (deberia funcionar en cualquier version)
PRINT ''
PRINT '=== TEST ISNUMERIC ==='
SELECT 'ISNUMERIC test' AS test,
       ISNUMERIC('123') AS num_ok,
       CASE WHEN ISNUMERIC('123') = 1 THEN CAST('123' AS INT) ELSE -1 END AS cast_ok
GO

-- 6) Intentar el ALTER VIEW con captura de error
PRINT ''
PRINT '=== INTENTANDO ALTER VIEW ==='
BEGIN TRY
    EXEC sp_executesql N'
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
            WHEN ISNULL(recib.cant_recibida, 0) >= ped.cant_pedida THEN ''COMPLETO''
            WHEN ISNULL(recib.cant_recibida, 0) > 0                THEN ''PARCIAL''
            ELSE ''PENDIENTE''
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
                THEN ''VENCIDO''
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
        WHERE p2.empresa = ''CALZALINDO''
          AND a.subrubro > 0
          AND p1.articulo > 0
    ) ped
    OUTER APPLY (
        SELECT
            SUM(pe.cantidad)       AS cant_recibida,
            MIN(pe.fecha_entrega)  AS primera_recepcion,
            MAX(pe.fecha_entrega)  AS ultima_recepcion
        FROM (
            SELECT cantidad, fecha_entrega
            FROM msgestion01.dbo.pedico1_entregas
            WHERE codigo    = 8
              AND letra     = ''X''
              AND sucursal  = ped.sucursal
              AND numero    = ped.numero
              AND orden     = ped.orden
              AND renglon   = ped.renglon
            UNION ALL
            SELECT cantidad, fecha_entrega
            FROM msgestion03.dbo.pedico1_entregas
            WHERE codigo    = 8
              AND letra     = ''X''
              AND sucursal  = ped.sucursal
              AND numero    = ped.numero
              AND orden     = ped.orden
              AND renglon   = ped.renglon
        ) pe
    ) recib
    ';
    PRINT 'ALTER VIEW: EXITO!'
END TRY
BEGIN CATCH
    PRINT '*** ALTER VIEW FALLO ***'
    PRINT 'Error ' + CAST(ERROR_NUMBER() AS VARCHAR) + ': ' + ERROR_MESSAGE()
    PRINT 'Linea: ' + CAST(ERROR_LINE() AS VARCHAR)
END CATCH
GO

-- 7) Verificar si la vista cambio
PRINT ''
PRINT '=== VERIFICACION POST-ALTER ==='
SELECT
    CASE WHEN CHARINDEX('CALZALINDO', definition) > 0 THEN 'SI' ELSE 'NO' END AS tiene_calzalindo,
    CASE WHEN CHARINDEX('pedico1_entregas', definition) > 0 THEN 'SI' ELSE 'NO' END AS usa_pedico1_entregas,
    CASE WHEN CHARINDEX('ISNUMERIC', definition) > 0 THEN 'SI' ELSE 'NO' END AS tiene_isnumeric,
    CASE WHEN CHARINDEX('rubro_desc', definition) > 0 THEN 'SI' ELSE 'NO' END AS tiene_rubro_desc
FROM sys.sql_modules
WHERE object_id = OBJECT_ID('dbo.v_pedidos_cumplimiento')
GO

PRINT ''
PRINT '=== FIN DIAGNOSTICO ==='
