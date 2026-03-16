-- ============================================================
-- EJECUTAR EN: 192.168.2.111 (servidor web2py / produccion)
-- BASE: omicronvt
-- CREA: t_presupuesto_industria
-- LOGICA: Presupuesto = venta a costo del anio anterior
--         en el mismo periodo, por industria.
--         El "periodo" se define por industria en la tabla
--         t_periodos_industria (configurable).
-- ============================================================
USE omicronvt;
GO

-- ---------------------------------------------------------------
-- 1. Tabla de periodos por industria (configurable)
--    Define que meses del anio corresponden a cada temporada
--    para cada industria. Esto permite que el presupuesto
--    se calcule sobre el periodo correcto.
-- ---------------------------------------------------------------
IF OBJECT_ID('dbo.t_periodos_industria', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.t_periodos_industria (
        industria       VARCHAR(100) NOT NULL,
        temporada       VARCHAR(50)  NOT NULL,  -- ej: 'INVIERNO 2026', 'VERANO 2026/27'
        mes_desde       INT          NOT NULL,  -- 1-12
        mes_hasta       INT          NOT NULL,  -- 1-12
        anio_base       INT          NOT NULL,  -- anio de referencia para presupuesto (ej: 2025)
        activo          BIT          DEFAULT 1,
        PRIMARY KEY (industria, temporada)
    );

    -- Datos iniciales: temporada invierno 2026
    -- Presupuesto basado en venta del mismo periodo de 2025
    INSERT INTO dbo.t_periodos_industria (industria, temporada, mes_desde, mes_hasta, anio_base) VALUES
    ('Zapateria',       'INVIERNO 2026', 3, 8, 2025),
    ('Cosmetica',       'INVIERNO 2026', 3, 8, 2025),
    ('Marroquineria',   'INVIERNO 2026', 3, 8, 2025),
    ('Deportes',        'INVIERNO 2026', 3, 8, 2025),
    ('Mixto_Zap_Dep',   'INVIERNO 2026', 3, 8, 2025),
    ('Bijouterie',      'INVIERNO 2026', 3, 8, 2025);

    PRINT 'Tabla t_periodos_industria creada con datos iniciales.';
    PRINT 'IMPORTANTE: Ajustar mes_desde y mes_hasta por industria segun corresponda.';
END;
GO

-- ---------------------------------------------------------------
-- 2. Tabla de presupuesto por industria (materializada)
-- ---------------------------------------------------------------
IF OBJECT_ID('dbo.t_presupuesto_industria', 'U') IS NOT NULL
    DROP TABLE dbo.t_presupuesto_industria;
GO

CREATE TABLE dbo.t_presupuesto_industria (
    industria               VARCHAR(100) NOT NULL,
    temporada               VARCHAR(50)  NOT NULL,
    -- Presupuesto (= venta anio anterior mismo periodo)
    presupuesto_costo       DECIMAL(18,2) DEFAULT 0,  -- venta a costo
    presupuesto_unidades    INT           DEFAULT 0,
    -- Comprometido (= pedidos actuales en el periodo)
    comprometido_costo      DECIMAL(18,2) DEFAULT 0,
    comprometido_unidades   INT           DEFAULT 0,
    -- Calculados
    disponible_costo        DECIMAL(18,2) DEFAULT 0,  -- presupuesto - comprometido
    pct_ejecutado           DECIMAL(5,1)  DEFAULT 0,  -- comprometido / presupuesto * 100
    -- Metadata
    fecha_calculo           DATETIME      DEFAULT GETDATE(),
    PRIMARY KEY (industria, temporada)
);
GO

-- ---------------------------------------------------------------
-- 3. SP para recalcular presupuesto
-- ---------------------------------------------------------------
IF OBJECT_ID('dbo.sp_calcular_presupuesto', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_calcular_presupuesto;
GO

CREATE PROCEDURE dbo.sp_calcular_presupuesto
    @temporada VARCHAR(50) = NULL  -- si NULL, recalcula todas las activas
AS
BEGIN
    SET NOCOUNT ON;

    -- Limpiar datos anteriores
    IF @temporada IS NOT NULL
        DELETE FROM dbo.t_presupuesto_industria WHERE temporada = @temporada;
    ELSE
        DELETE FROM dbo.t_presupuesto_industria
        WHERE temporada IN (SELECT temporada FROM dbo.t_periodos_industria WHERE activo = 1);

    -- Calcular presupuesto (venta anio base) y comprometido (pedidos actuales)
    INSERT INTO dbo.t_presupuesto_industria
        (industria, temporada, presupuesto_costo, presupuesto_unidades,
         comprometido_costo, comprometido_unidades,
         disponible_costo, pct_ejecutado)
    SELECT
        p.industria,
        p.temporada,
        ISNULL(vta.venta_costo, 0)      AS presupuesto_costo,
        ISNULL(vta.unidades_vendidas, 0) AS presupuesto_unidades,
        ISNULL(ped.monto_comprometido, 0) AS comprometido_costo,
        ISNULL(ped.unidades_pedidas, 0)   AS comprometido_unidades,
        ISNULL(vta.venta_costo, 0) - ISNULL(ped.monto_comprometido, 0) AS disponible_costo,
        CASE WHEN ISNULL(vta.venta_costo, 0) = 0 THEN 0
             ELSE ROUND(ISNULL(ped.monto_comprometido, 0) * 100.0 / vta.venta_costo, 1)
        END AS pct_ejecutado
    FROM dbo.t_periodos_industria p
    -- Venta del anio base en el mismo periodo
    LEFT JOIN (
        SELECT
            ind.industria,
            SUM(CASE
                WHEN v.codigo IN (1,6,21,61) THEN v.precio_costo * v.cantidad
                WHEN v.codigo IN (3,8,23,63) THEN -v.precio_costo * v.cantidad
                ELSE 0
            END) AS venta_costo,
            SUM(CASE
                WHEN v.codigo IN (1,6,21,61) THEN v.cantidad
                WHEN v.codigo IN (3,8,23,63) THEN -v.cantidad
                ELSE 0
            END) AS unidades_vendidas
        FROM msgestion01.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        LEFT JOIN omicronvt.dbo.map_subrubro_industria ind ON a.subrubro = ind.subrubro
        WHERE v.codigo IN (1,3,6,8,21,23,61,63)
          AND ind.industria IS NOT NULL
        GROUP BY ind.industria, YEAR(v.fecha), MONTH(v.fecha)
        -- Nota: el filtro de periodo se aplica abajo
    ) vta_raw ON 1=0  -- placeholder, se reemplaza abajo
    -- Usar subquery correlacionada para el periodo correcto
    OUTER APPLY (
        SELECT
            SUM(CASE
                WHEN v.codigo IN (1,6,21,61) THEN v.precio_costo * v.cantidad
                WHEN v.codigo IN (3,8,23,63) THEN -v.precio_costo * v.cantidad
                ELSE 0
            END) AS venta_costo,
            SUM(CASE
                WHEN v.codigo IN (1,6,21,61) THEN v.cantidad
                WHEN v.codigo IN (3,8,23,63) THEN -v.cantidad
                ELSE 0
            END) AS unidades_vendidas
        FROM msgestion01.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        LEFT JOIN omicronvt.dbo.map_subrubro_industria ind ON a.subrubro = ind.subrubro
        WHERE v.codigo IN (1,3,6,8,21,23,61,63)
          AND ind.industria = p.industria
          AND YEAR(v.fecha) = p.anio_base
          AND MONTH(v.fecha) BETWEEN p.mes_desde AND p.mes_hasta
    ) vta
    -- Pedidos actuales (2do semestre 2025+)
    OUTER APPLY (
        SELECT
            SUM(c.monto_pedido) AS monto_comprometido,
            SUM(c.cant_pedida)  AS unidades_pedidas
        FROM dbo.pedidos_cumplimiento_cache c
        WHERE c.industria = p.industria
          AND c.fecha_pedido >= '2025-07-01'
    ) ped
    WHERE p.activo = 1
      AND (@temporada IS NULL OR p.temporada = @temporada);

    PRINT 'Presupuesto recalculado OK.';
END;
GO

-- Ejecutar calculo inicial
EXEC dbo.sp_calcular_presupuesto;
GO

PRINT 'OK - Tabla t_presupuesto_industria creada y calculada.';
PRINT 'Para recalcular: EXEC sp_calcular_presupuesto';
PRINT 'Para ajustar periodos: UPDATE t_periodos_industria SET mes_desde=X, mes_hasta=Y WHERE industria=...';
GO
