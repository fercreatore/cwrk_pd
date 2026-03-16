-- =============================================================================
-- AJUSTE DE PRESUPUESTO POR TENDENCIA DE FACTURACION
-- Calzalindo H4 - Calce Financiero
-- Ejecutar en: 192.168.2.111 -> omicronvt
-- Fecha: 2026-03-05
--
-- INCLUYE:
--   - Factor de tendencia por costo Y por unidades (sin distorsion de inflacion)
--   - Indice de estacionalidad historico (5 anios) para proyeccion anual
--   - Descomposicion precio/volumen
--   - Proyeccion anual de unidades desde YTD
-- =============================================================================

-- =============================================
-- PARTE 0: Tabla de tendencia mensual
-- =============================================
IF EXISTS (SELECT * FROM sys.tables WHERE name = 't_tendencia_facturacion')
    DROP TABLE t_tendencia_facturacion
GO

CREATE TABLE t_tendencia_facturacion (
    industria           VARCHAR(50)    NOT NULL,
    mes                 INT            NOT NULL,
    -- Facturacion a costo
    facturacion_2024    DECIMAL(18,2)  DEFAULT 0,
    facturacion_2025    DECIMAL(18,2)  DEFAULT 0,
    facturacion_2026    DECIMAL(18,2)  DEFAULT 0,
    -- Unidades vendidas
    unidades_2024       INT            DEFAULT 0,
    unidades_2025       INT            DEFAULT 0,
    unidades_2026       INT            DEFAULT 0,
    -- Ticket promedio (costo por unidad)
    ticket_2024         DECIMAL(18,2)  DEFAULT 0,
    ticket_2025         DECIMAL(18,2)  DEFAULT 0,
    ticket_2026         DECIMAL(18,2)  DEFAULT 0,
    -- Ratios YoY
    ratio_26v25         DECIMAL(8,4)   DEFAULT 0,   -- costo
    ratio_uds_26v25     DECIMAL(8,4)   DEFAULT 0,   -- unidades (sin inflacion)
    ratio_ticket_26v25  DECIMAL(8,4)   DEFAULT 0,   -- precio unitario
    -- Estacionalidad (% de uds anuales que representa este mes, prom 5 anios)
    idx_estacionalidad  DECIMAL(8,4)   DEFAULT 0,
    -- Estado
    mes_completo_2026   BIT            DEFAULT 0,
    fecha_calculo       DATETIME       DEFAULT GETDATE(),
    PRIMARY KEY (industria, mes)
)
PRINT 'Tabla t_tendencia_facturacion creada.'
GO

-- =============================================
-- PARTE 1: Agregar columnas de ajuste a t_presupuesto_industria
-- =============================================
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('t_presupuesto_industria') AND name = 'factor_tendencia')
BEGIN
    ALTER TABLE t_presupuesto_industria ADD factor_tendencia DECIMAL(8,4) DEFAULT 1.0
    ALTER TABLE t_presupuesto_industria ADD presupuesto_ajustado DECIMAL(18,2) DEFAULT 0
    ALTER TABLE t_presupuesto_industria ADD meses_evaluados INT DEFAULT 0
    ALTER TABLE t_presupuesto_industria ADD tendencia_desc VARCHAR(200) DEFAULT ''
    ALTER TABLE t_presupuesto_industria ADD disponible_ajustado DECIMAL(18,2) DEFAULT 0
    PRINT 'Columnas basicas de ajuste agregadas.'
END

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('t_presupuesto_industria') AND name = 'factor_tendencia_uds')
BEGIN
    ALTER TABLE t_presupuesto_industria ADD factor_tendencia_uds DECIMAL(8,4) DEFAULT 1.0
    ALTER TABLE t_presupuesto_industria ADD presupuesto_uds_ajustado INT DEFAULT 0
    ALTER TABLE t_presupuesto_industria ADD var_ticket_prom DECIMAL(8,2) DEFAULT 0
    ALTER TABLE t_presupuesto_industria ADD uds_ytd_2026 INT DEFAULT 0
    ALTER TABLE t_presupuesto_industria ADD uds_ytd_2025 INT DEFAULT 0
    ALTER TABLE t_presupuesto_industria ADD uds_proy_anual_2026 INT DEFAULT 0
    ALTER TABLE t_presupuesto_industria ADD diagnostico VARCHAR(300) DEFAULT ''
    PRINT 'Columnas avanzadas (uds, proyeccion, diagnostico) agregadas.'
END
ELSE
    PRINT 'Columnas avanzadas ya existen.'
GO

-- =============================================
-- PARTE 2: SP para calcular tendencia de facturacion
-- =============================================
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_calcular_tendencia')
    DROP PROCEDURE sp_calcular_tendencia
GO

CREATE PROCEDURE sp_calcular_tendencia
AS
BEGIN
    SET NOCOUNT ON

    -- -----------------------------------------------
    -- Paso 1: Llenar tendencia mensual por industria
    -- -----------------------------------------------
    TRUNCATE TABLE t_tendencia_facturacion

    INSERT INTO t_tendencia_facturacion (industria, mes)
    SELECT ind.industria, m.mes
    FROM (SELECT DISTINCT industria FROM map_subrubro_industria) ind
    CROSS JOIN (
        SELECT 1 AS mes UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
        UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8
        UNION SELECT 9 UNION SELECT 10 UNION SELECT 11 UNION SELECT 12
    ) m

    -- Facturacion 2024
    UPDATE t SET
        facturacion_2024 = ISNULL(x.total_costo, 0),
        unidades_2024 = ISNULL(x.total_uds, 0),
        ticket_2024 = CASE WHEN ISNULL(x.total_uds, 0) > 0
                           THEN ISNULL(x.total_costo, 0) / x.total_uds ELSE 0 END
    FROM t_tendencia_facturacion t
    JOIN (
        SELECT ind.industria, MONTH(v2.fecha_comprobante) AS mes,
               SUM(v1.cantidad * v1.precio_costo) AS total_costo,
               SUM(v1.cantidad) AS total_uds
        FROM msgestionC.dbo.ventas1 v1
        JOIN msgestionC.dbo.ventas2 v2
            ON v1.empresa = v2.empresa AND v1.codigo = v2.codigo
           AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
           AND v1.numero = v2.numero AND v1.orden = v2.orden
        JOIN msgestion01art.dbo.articulo a ON v1.articulo = a.codigo
        JOIN map_subrubro_industria ind ON a.subrubro = ind.subrubro
        WHERE v2.codigo = 1 AND YEAR(v2.fecha_comprobante) = 2024 AND a.subrubro > 0
        GROUP BY ind.industria, MONTH(v2.fecha_comprobante)
    ) x ON t.industria = x.industria AND t.mes = x.mes

    -- Facturacion 2025
    UPDATE t SET
        facturacion_2025 = ISNULL(x.total_costo, 0),
        unidades_2025 = ISNULL(x.total_uds, 0),
        ticket_2025 = CASE WHEN ISNULL(x.total_uds, 0) > 0
                           THEN ISNULL(x.total_costo, 0) / x.total_uds ELSE 0 END
    FROM t_tendencia_facturacion t
    JOIN (
        SELECT ind.industria, MONTH(v2.fecha_comprobante) AS mes,
               SUM(v1.cantidad * v1.precio_costo) AS total_costo,
               SUM(v1.cantidad) AS total_uds
        FROM msgestionC.dbo.ventas1 v1
        JOIN msgestionC.dbo.ventas2 v2
            ON v1.empresa = v2.empresa AND v1.codigo = v2.codigo
           AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
           AND v1.numero = v2.numero AND v1.orden = v2.orden
        JOIN msgestion01art.dbo.articulo a ON v1.articulo = a.codigo
        JOIN map_subrubro_industria ind ON a.subrubro = ind.subrubro
        WHERE v2.codigo = 1 AND YEAR(v2.fecha_comprobante) = 2025 AND a.subrubro > 0
        GROUP BY ind.industria, MONTH(v2.fecha_comprobante)
    ) x ON t.industria = x.industria AND t.mes = x.mes

    -- Facturacion 2026
    UPDATE t SET
        facturacion_2026 = ISNULL(x.total_costo, 0),
        unidades_2026 = ISNULL(x.total_uds, 0),
        ticket_2026 = CASE WHEN ISNULL(x.total_uds, 0) > 0
                           THEN ISNULL(x.total_costo, 0) / x.total_uds ELSE 0 END
    FROM t_tendencia_facturacion t
    JOIN (
        SELECT ind.industria, MONTH(v2.fecha_comprobante) AS mes,
               SUM(v1.cantidad * v1.precio_costo) AS total_costo,
               SUM(v1.cantidad) AS total_uds
        FROM msgestionC.dbo.ventas1 v1
        JOIN msgestionC.dbo.ventas2 v2
            ON v1.empresa = v2.empresa AND v1.codigo = v2.codigo
           AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
           AND v1.numero = v2.numero AND v1.orden = v2.orden
        JOIN msgestion01art.dbo.articulo a ON v1.articulo = a.codigo
        JOIN map_subrubro_industria ind ON a.subrubro = ind.subrubro
        WHERE v2.codigo = 1 AND YEAR(v2.fecha_comprobante) = 2026 AND a.subrubro > 0
        GROUP BY ind.industria, MONTH(v2.fecha_comprobante)
    ) x ON t.industria = x.industria AND t.mes = x.mes

    -- -----------------------------------------------
    -- Paso 2: Ratios YoY (costo, unidades, ticket)
    -- -----------------------------------------------
    UPDATE t_tendencia_facturacion SET
        ratio_26v25 = CASE WHEN facturacion_2025 > 0
                           THEN CAST(facturacion_2026 AS DECIMAL(18,4)) / facturacion_2025
                           ELSE 0 END,
        ratio_uds_26v25 = CASE WHEN unidades_2025 > 0
                               THEN CAST(unidades_2026 AS DECIMAL(18,4)) / unidades_2025
                               ELSE 0 END,
        ratio_ticket_26v25 = CASE WHEN ticket_2025 > 0 AND ticket_2026 > 0
                                  THEN ticket_2026 / ticket_2025
                                  ELSE 0 END

    -- -----------------------------------------------
    -- Paso 3: Indice de estacionalidad (5 anios, 2021-2025)
    -- % de uds anuales que cada mes representa, promediado
    -- -----------------------------------------------
    UPDATE t SET
        idx_estacionalidad = ISNULL(e.idx, 0)
    FROM t_tendencia_facturacion t
    LEFT JOIN (
        SELECT x.industria, x.mes, AVG(x.pct_anual) AS idx
        FROM (
            SELECT ind.industria,
                   MONTH(v2.fecha_comprobante) AS mes,
                   YEAR(v2.fecha_comprobante) AS anio,
                   SUM(v1.cantidad) * 100.0 /
                       NULLIF(SUM(SUM(v1.cantidad)) OVER (
                           PARTITION BY ind.industria, YEAR(v2.fecha_comprobante)
                       ), 0) AS pct_anual
            FROM msgestionC.dbo.ventas1 v1
            JOIN msgestionC.dbo.ventas2 v2
                ON v1.empresa = v2.empresa AND v1.codigo = v2.codigo
               AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
               AND v1.numero = v2.numero AND v1.orden = v2.orden
            JOIN msgestion01art.dbo.articulo a ON v1.articulo = a.codigo
            JOIN map_subrubro_industria ind ON a.subrubro = ind.subrubro
            WHERE v2.codigo = 1 AND a.subrubro > 0
              AND YEAR(v2.fecha_comprobante) BETWEEN 2021 AND 2025
            GROUP BY ind.industria, YEAR(v2.fecha_comprobante), MONTH(v2.fecha_comprobante)
        ) x
        GROUP BY x.industria, x.mes
    ) e ON t.industria = e.industria AND t.mes = e.mes

    -- -----------------------------------------------
    -- Paso 4: Marcar meses completos de 2026
    -- -----------------------------------------------
    UPDATE t_tendencia_facturacion SET
        mes_completo_2026 = CASE
            WHEN mes < MONTH(GETDATE()) AND unidades_2026 > 0 THEN 1
            ELSE 0
        END

    -- -----------------------------------------------
    -- Paso 5: Factores de ajuste en t_presupuesto_industria
    -- Factor COSTO: promedio ratio_26v25 de meses completos
    -- Factor UNIDADES: promedio ratio_uds_26v25 (sin inflacion!)
    -- -----------------------------------------------

    -- Primero: intentar con meses de la temporada
    UPDATE p SET
        factor_tendencia = ISNULL(x.factor_costo, 1.0),
        factor_tendencia_uds = ISNULL(x.factor_uds, 1.0),
        meses_evaluados = ISNULL(x.meses, 0),
        presupuesto_ajustado = p.presupuesto_costo * ISNULL(x.factor_costo, 1.0),
        presupuesto_uds_ajustado = CAST(p.presupuesto_unidades * ISNULL(x.factor_uds, 1.0) AS INT),
        disponible_ajustado = p.presupuesto_costo * ISNULL(x.factor_costo, 1.0) - p.comprometido_costo,
        var_ticket_prom = ISNULL((x.factor_costo / NULLIF(x.factor_uds, 0) - 1) * 100, 0),
        tendencia_desc = CASE
            WHEN ISNULL(x.factor_uds, 1.0) >= 1.05 THEN 'SUBE'
            WHEN ISNULL(x.factor_uds, 1.0) >= 0.95 THEN 'ESTABLE'
            WHEN ISNULL(x.factor_uds, 1.0) >= 0.80 THEN 'BAJA'
            ELSE 'CAIDA_FUERTE'
        END,
        fecha_calculo = GETDATE()
    FROM t_presupuesto_industria p
    OUTER APPLY (
        SELECT
            AVG(t.ratio_26v25) AS factor_costo,
            AVG(t.ratio_uds_26v25) AS factor_uds,
            COUNT(*) AS meses
        FROM t_tendencia_facturacion t
        JOIN t_periodos_industria per
            ON t.industria = per.industria
           AND p.temporada = per.temporada
           AND p.industria = per.industria
        WHERE t.industria = p.industria
          AND t.mes_completo_2026 = 1
          AND t.ratio_uds_26v25 > 0
          AND (
              (per.mes_desde <= per.mes_hasta AND t.mes BETWEEN per.mes_desde AND per.mes_hasta)
              OR
              (per.mes_desde > per.mes_hasta AND (t.mes >= per.mes_desde OR t.mes <= per.mes_hasta))
          )
        HAVING COUNT(*) > 0
    ) x

    -- Fallback: usar todos los meses completos si no hay de la temporada
    UPDATE p SET
        factor_tendencia = ISNULL(x.factor_costo, 1.0),
        factor_tendencia_uds = ISNULL(x.factor_uds, 1.0),
        meses_evaluados = ISNULL(x.meses, 0),
        presupuesto_ajustado = p.presupuesto_costo * ISNULL(x.factor_costo, 1.0),
        presupuesto_uds_ajustado = CAST(p.presupuesto_unidades * ISNULL(x.factor_uds, 1.0) AS INT),
        disponible_ajustado = p.presupuesto_costo * ISNULL(x.factor_costo, 1.0) - p.comprometido_costo,
        var_ticket_prom = ISNULL((x.factor_costo / NULLIF(x.factor_uds, 0) - 1) * 100, 0),
        tendencia_desc = CASE
            WHEN ISNULL(x.factor_uds, 1.0) >= 1.05 THEN 'SUBE'
            WHEN ISNULL(x.factor_uds, 1.0) >= 0.95 THEN 'ESTABLE'
            WHEN ISNULL(x.factor_uds, 1.0) >= 0.80 THEN 'BAJA'
            ELSE 'CAIDA_FUERTE'
        END + ' (global)',
        fecha_calculo = GETDATE()
    FROM t_presupuesto_industria p
    OUTER APPLY (
        SELECT
            AVG(t.ratio_26v25) AS factor_costo,
            AVG(t.ratio_uds_26v25) AS factor_uds,
            COUNT(*) AS meses
        FROM t_tendencia_facturacion t
        WHERE t.industria = p.industria
          AND t.mes_completo_2026 = 1
          AND t.ratio_uds_26v25 > 0
        HAVING COUNT(*) > 0
    ) x
    WHERE p.meses_evaluados = 0

    -- -----------------------------------------------
    -- Paso 6: YTD unidades y proyeccion anual
    -- Proyeccion = uds_ytd / sum(idx_estacionalidad de meses completos) * 100
    -- -----------------------------------------------
    UPDATE p SET
        uds_ytd_2026 = ISNULL(ytd26.uds, 0),
        uds_ytd_2025 = ISNULL(ytd25.uds, 0),
        uds_proy_anual_2026 = CASE
            WHEN ISNULL(idx.sum_idx, 0) > 0
            THEN CAST(ISNULL(ytd26.uds, 0) * 100.0 / idx.sum_idx AS INT)
            ELSE 0 END
    FROM t_presupuesto_industria p
    -- YTD 2026 (meses completos)
    OUTER APPLY (
        SELECT SUM(unidades_2026) AS uds
        FROM t_tendencia_facturacion t
        WHERE t.industria = p.industria AND t.mes_completo_2026 = 1
    ) ytd26
    -- YTD 2025 mismos meses
    OUTER APPLY (
        SELECT SUM(unidades_2025) AS uds
        FROM t_tendencia_facturacion t
        WHERE t.industria = p.industria AND t.mes_completo_2026 = 1
    ) ytd25
    -- Sum de indice de estacionalidad de meses completos
    OUTER APPLY (
        SELECT SUM(idx_estacionalidad) AS sum_idx
        FROM t_tendencia_facturacion t
        WHERE t.industria = p.industria AND t.mes_completo_2026 = 1
    ) idx

    -- -----------------------------------------------
    -- Paso 7: Diagnostico textual
    -- -----------------------------------------------
    UPDATE p SET
        diagnostico = CASE
            WHEN factor_tendencia_uds < 0.70 THEN
                'ALERTA: Uds caen ' + CAST(CAST((1-factor_tendencia_uds)*100 AS INT) AS VARCHAR)
                + '%. '
                + CASE WHEN var_ticket_prom > 15 THEN 'Ticket sube ' + CAST(CAST(var_ticket_prom AS INT) AS VARCHAR) + '% (inflacion enmascara caida).'
                       WHEN var_ticket_prom < -10 THEN 'Ticket tambien cae ' + CAST(CAST(ABS(var_ticket_prom) AS INT) AS VARCHAR) + '% (doble problema).'
                       ELSE 'Ticket estable.' END
            WHEN factor_tendencia_uds < 0.85 THEN
                'Uds bajan ' + CAST(CAST((1-factor_tendencia_uds)*100 AS INT) AS VARCHAR)
                + '%. '
                + CASE WHEN var_ticket_prom > 15 THEN 'Compensado parcial por ticket +' + CAST(CAST(var_ticket_prom AS INT) AS VARCHAR) + '%.'
                       ELSE 'Ticket estable.' END
            WHEN factor_tendencia_uds >= 1.05 THEN
                'Uds suben +' + CAST(CAST((factor_tendencia_uds-1)*100 AS INT) AS VARCHAR)
                + '%. '
                + CASE WHEN var_ticket_prom < -10 THEN 'Pero ticket cae ' + CAST(CAST(ABS(var_ticket_prom) AS INT) AS VARCHAR) + '% (mix mas barato?).'
                       ELSE 'Crecimiento real.' END
            ELSE 'Volumen estable. '
                + CASE WHEN var_ticket_prom > 15 THEN 'Ticket sube ' + CAST(CAST(var_ticket_prom AS INT) AS VARCHAR) + '%.'
                       WHEN var_ticket_prom < -10 THEN 'Ticket baja ' + CAST(CAST(ABS(var_ticket_prom) AS INT) AS VARCHAR) + '%.'
                       ELSE '' END
        END
    FROM t_presupuesto_industria p

    PRINT 'Tendencia calculada OK.'

    -- Mostrar resultado
    SELECT industria, temporada,
           presupuesto_costo, factor_tendencia, presupuesto_ajustado,
           factor_tendencia_uds, presupuesto_unidades, presupuesto_uds_ajustado,
           var_ticket_prom,
           uds_ytd_2026, uds_ytd_2025, uds_proy_anual_2026,
           comprometido_costo, disponible_ajustado,
           meses_evaluados, tendencia_desc, diagnostico
    FROM t_presupuesto_industria
    ORDER BY presupuesto_costo DESC
END
GO

-- =============================================
-- PARTE 3: SP principal (recrea sp_calcular_presupuesto)
-- =============================================
IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'sp_calcular_presupuesto')
    DROP PROCEDURE sp_calcular_presupuesto
GO

CREATE PROCEDURE sp_calcular_presupuesto
AS
BEGIN
    SET NOCOUNT ON

    TRUNCATE TABLE t_presupuesto_industria

    INSERT INTO t_presupuesto_industria (
        industria, temporada, anio_objetivo,
        presupuesto_costo, presupuesto_unidades, cant_articulos_base,
        comprometido_costo, comprometido_unidades, disponible_costo,
        pct_ejecutado, anio_base, fecha_calculo
    )
    SELECT
        per.industria, per.temporada, per.anio_objetivo,
        ISNULL(SUM(v1.cantidad * v1.precio_costo), 0),
        ISNULL(SUM(v1.cantidad), 0),
        COUNT(DISTINCT v1.articulo),
        0, 0, 0, 0,
        per.anio_base, GETDATE()
    FROM t_periodos_industria per
    JOIN map_subrubro_industria ind ON per.industria = ind.industria
    JOIN msgestion01art.dbo.articulo a ON a.subrubro = ind.subrubro AND a.subrubro > 0
    JOIN msgestionC.dbo.ventas1 v1 ON v1.articulo = a.codigo
    JOIN msgestionC.dbo.ventas2 v2
        ON v1.empresa = v2.empresa AND v1.codigo = v2.codigo
       AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
       AND v1.numero = v2.numero AND v1.orden = v2.orden
    WHERE per.activo = 1 AND v2.codigo = 1
      AND YEAR(v2.fecha_comprobante) = per.anio_base
      AND (
          (per.mes_desde <= per.mes_hasta AND MONTH(v2.fecha_comprobante) BETWEEN per.mes_desde AND per.mes_hasta)
          OR
          (per.mes_desde > per.mes_hasta AND (MONTH(v2.fecha_comprobante) >= per.mes_desde OR MONTH(v2.fecha_comprobante) <= per.mes_hasta))
      )
    GROUP BY per.industria, per.temporada, per.anio_objetivo, per.anio_base

    -- Comprometido
    UPDATE p SET
        comprometido_costo = ISNULL(c.total_comp, 0),
        comprometido_unidades = ISNULL(c.total_uds, 0),
        disponible_costo = p.presupuesto_costo - ISNULL(c.total_comp, 0),
        pct_ejecutado = CASE WHEN p.presupuesto_costo > 0
                             THEN ROUND(ISNULL(c.total_comp, 0) * 100.0 / p.presupuesto_costo, 1)
                             ELSE 0 END
    FROM t_presupuesto_industria p
    LEFT JOIN (
        SELECT industria, SUM(monto_pedido) AS total_comp, SUM(cant_pedida) AS total_uds
        FROM pedidos_cumplimiento_cache
        WHERE fecha_pedido >= '2025-07-01'
        GROUP BY industria
    ) c ON p.industria = c.industria

    PRINT 'Presupuesto base calculado. Calculando tendencia...'
    EXEC sp_calcular_tendencia
END
GO

-- =============================================
-- PARTE 4: EJECUTAR
-- =============================================
EXEC sp_calcular_presupuesto
GO

-- =============================================
-- PARTE 5: Verificar
-- =============================================
PRINT '--- TENDENCIA MENSUAL ---'
SELECT industria, mes,
       unidades_2025, unidades_2026, ratio_uds_26v25,
       ticket_2025, ticket_2026, ratio_ticket_26v25,
       idx_estacionalidad, mes_completo_2026
FROM t_tendencia_facturacion
WHERE unidades_2025 > 0
ORDER BY industria, mes
GO

PRINT '--- PRESUPUESTO AJUSTADO ---'
SELECT industria, temporada,
       presupuesto_costo AS presup_$,
       factor_tendencia AS factor_$,
       presupuesto_unidades AS presup_uds,
       factor_tendencia_uds AS factor_uds,
       presupuesto_uds_ajustado AS uds_ajust,
       var_ticket_prom AS var_ticket,
       uds_ytd_2026, uds_ytd_2025,
       uds_proy_anual_2026 AS proy_anual,
       meses_evaluados, tendencia_desc, diagnostico
FROM t_presupuesto_industria
ORDER BY presupuesto_costo DESC
GO

PRINT ''
PRINT '========================================='
PRINT '  LISTO! Ejecutar deploy.sh para activar'
PRINT '========================================='
GO
