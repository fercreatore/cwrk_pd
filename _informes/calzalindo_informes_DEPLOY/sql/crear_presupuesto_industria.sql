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
    -- Presupuesto ajustado por quiebre (vel_real)
    -- Ej CARMEL CANELA: vel_aparente 2/mes, vel_real 10.8/mes → factor 5.4x
    -- presupuesto_ajustado = presupuesto_costo * factor_quiebre_industria
    vel_aparente_industria  DECIMAL(10,2) DEFAULT 0,  -- promedio vel_aparente de la industria
    vel_real_industria      DECIMAL(10,2) DEFAULT 0,  -- promedio vel_real de la industria
    factor_quiebre_industria DECIMAL(8,3) DEFAULT 1.0, -- vel_real / vel_aparente
    presupuesto_ajustado    DECIMAL(18,2) DEFAULT 0,  -- presupuesto_costo * factor_quiebre
    -- Comprometido (= pedidos actuales en el periodo)
    comprometido_costo      DECIMAL(18,2) DEFAULT 0,
    comprometido_unidades   INT           DEFAULT 0,
    -- Calculados
    disponible_costo        DECIMAL(18,2) DEFAULT 0,  -- presupuesto - comprometido
    disponible_ajustado     DECIMAL(18,2) DEFAULT 0,  -- presupuesto_ajustado - comprometido
    pct_ejecutado           DECIMAL(5,1)  DEFAULT 0,  -- comprometido / presupuesto * 100
    pct_ejecutado_ajustado  DECIMAL(5,1)  DEFAULT 0,  -- comprometido / presupuesto_ajustado * 100
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
         vel_aparente_industria, vel_real_industria, factor_quiebre_industria,
         presupuesto_ajustado,
         comprometido_costo, comprometido_unidades,
         disponible_costo, disponible_ajustado,
         pct_ejecutado, pct_ejecutado_ajustado)
    SELECT
        p.industria,
        p.temporada,
        ISNULL(vta.venta_costo, 0)      AS presupuesto_costo,
        ISNULL(vta.unidades_vendidas, 0) AS presupuesto_unidades,
        -- Velocidad real vs aparente por industria (desde vel_real_articulo)
        ISNULL(vr.vel_ap_avg, 0)         AS vel_aparente_industria,
        ISNULL(vr.vel_real_avg, 0)       AS vel_real_industria,
        ISNULL(vr.factor_avg, 1.0)       AS factor_quiebre_industria,
        -- Presupuesto ajustado = presupuesto * factor_quiebre
        -- Si factor=1.5 y presupuesto=1M → demanda real era 1.5M (subestimada por quiebre)
        ROUND(ISNULL(vta.venta_costo, 0) * ISNULL(vr.factor_avg, 1.0), 2) AS presupuesto_ajustado,
        ISNULL(ped.monto_comprometido, 0) AS comprometido_costo,
        ISNULL(ped.unidades_pedidas, 0)   AS comprometido_unidades,
        ISNULL(vta.venta_costo, 0) - ISNULL(ped.monto_comprometido, 0) AS disponible_costo,
        ROUND(ISNULL(vta.venta_costo, 0) * ISNULL(vr.factor_avg, 1.0), 2)
            - ISNULL(ped.monto_comprometido, 0) AS disponible_ajustado,
        CASE WHEN ISNULL(vta.venta_costo, 0) = 0 THEN 0
             ELSE ROUND(ISNULL(ped.monto_comprometido, 0) * 100.0 / vta.venta_costo, 1)
        END AS pct_ejecutado,
        CASE WHEN ISNULL(vta.venta_costo, 0) * ISNULL(vr.factor_avg, 1.0) = 0 THEN 0
             ELSE ROUND(ISNULL(ped.monto_comprometido, 0) * 100.0
                        / (vta.venta_costo * ISNULL(vr.factor_avg, 1.0)), 1)
        END AS pct_ejecutado_ajustado
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
          AND (
              (p.mes_desde <= p.mes_hasta AND MONTH(v.fecha) BETWEEN p.mes_desde AND p.mes_hasta)
              OR
              (p.mes_desde > p.mes_hasta AND (MONTH(v.fecha) >= p.mes_desde OR MONTH(v.fecha) <= p.mes_hasta))
          )
    ) vta
    -- Factor de quiebre promedio por industria (desde vel_real_articulo)
    OUTER APPLY (
        SELECT
            AVG(vra.vel_aparente)   AS vel_ap_avg,
            AVG(vra.vel_real)       AS vel_real_avg,
            CASE WHEN AVG(vra.vel_aparente) > 0
                 THEN AVG(vra.vel_real) / AVG(vra.vel_aparente)
                 ELSE 1.0
            END AS factor_avg
        FROM omicronvt.dbo.vel_real_articulo vra
        JOIN msgestion01art.dbo.articulo a ON a.codigo_sinonimo = vra.codigo
        LEFT JOIN omicronvt.dbo.map_subrubro_industria ind ON a.subrubro = ind.subrubro
        WHERE ind.industria = p.industria
          AND vra.vel_aparente > 0  -- solo artículos con ventas
    ) vr
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

-- ============================================================
-- DOCUMENTACIÓN: presupuesto_actual vs presupuesto_ajustado
-- ============================================================
-- Ejemplo CARMEL CANELA T42 (caso extremo pero real):
--   vel_aparente = 2 pares/mes (subestimada: incluye meses quebrados con 0 ventas)
--   vel_real     = 10.8 pares/mes (solo meses donde hubo stock)
--   factor_quiebre = 5.4x
--   Quebrado 34 de 39 meses (87%!)
--
-- IMPACTO EN PRESUPUESTO:
--   presupuesto_costo    = $100,000 (basado en ventas reales del año pasado)
--   presupuesto_ajustado = $540,000 (lo que DEBERÍA haber vendido sin quiebre)
--   → El presupuesto "normal" SUBESTIMA la demanda real en 440%
--   → Si comprometemos solo contra el presupuesto normal, quedamos cortos
--
-- CUÁNDO USAR CADA UNO:
--   presupuesto_costo     → planificación financiera conservadora, flujo de caja
--   presupuesto_ajustado  → planificación de compras, objetivo de venta real
--   pct_ejecutado         → ejecución vs lo que vendimos el año pasado
--   pct_ejecutado_ajustado → ejecución vs lo que PODRÍAMOS haber vendido
--
-- DEPENDENCIA: requiere tabla omicronvt.dbo.vel_real_articulo
--   generada por: _scripts_oneshot/crear_tabla_vel_real.py
--   Si la tabla no existe, factor_quiebre = 1.0 (sin ajuste, backwards compatible)
GO
