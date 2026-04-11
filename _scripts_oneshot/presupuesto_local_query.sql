-- =====================================================================
-- presupuesto_local_query.sql
-- Propósito: Calcular presupuesto mensual sugerido de compras por local,
--            usando MMA-1 (mismo mes año anterior) corregido por factor
--            YoY de los últimos 3 meses cerrados de la cadena.
--            Fuente: omicronvt.dbo.compras_por_local
-- Fecha:     11-abr-2026
-- Autor:     Claude (vibrant-goldwasser worktree)
--
-- LÓGICA:
--   1. MMA-1 por local = compras_cer en el mismo mes del año anterior.
--   2. Factor_YoY cadena = SUM(costo_cer últimos 3 meses cerrados)
--                          / SUM(costo_cer mismos 3 meses del año -1)
--   3. Share_local = MMA-1[local] / SUM(MMA-1 cadena)
--   4. Presupuesto_sugerido = MMA-1[local] * Factor_YoY
--   5. Exclusión pandemia: 2020-03, 2020-04, 2020-05, 2021-06
--   6. Filtrar deps core: 0, 2, 6, 7, 8, 11
--
-- PARÁMETROS:
--   @mes_target   VARCHAR(7)   -- 'YYYY-MM' del mes a presupuestar (ej '2026-05')
--   @deps_csv     VARCHAR(100) -- CSV de deps (ej '0,2,6,7,8,11') o 'all' = default core
--
-- OUTPUT:
--   deposito | mma1 | factor_yoy | share | presupuesto_sugerido
--
-- Cómo ejecutar:
--   - Editar los SET de @mes_target y @deps_csv abajo.
--   - Ejecutar en SSMS contra 192.168.2.111 / omicronvt.
--   - sqlcmd -S 192.168.2.111 -U am -P dl -d omicronvt -i presupuesto_local_query.sql
--
-- SQL Server 2012 RTM: NO usar TRY_CAST. Usar ISNUMERIC + CAST.
-- =====================================================================

USE omicronvt;
GO

SET NOCOUNT ON;

-- ---------- PARÁMETROS (editar antes de ejecutar) ----------
DECLARE @mes_target VARCHAR(7) = '2026-05';        -- YYYY-MM
DECLARE @deps_csv   VARCHAR(100) = 'all';          -- 'all' o CSV '0,2,6,7,8,11'

-- ---------- DERIVADOS ----------
DECLARE @mes_anio_ant VARCHAR(7);   -- MMA-1 (mismo mes año anterior)
DECLARE @mes_num   INT  = CAST(SUBSTRING(@mes_target, 6, 2) AS INT);
DECLARE @anio_num  INT  = CAST(SUBSTRING(@mes_target, 1, 4) AS INT);

SET @mes_anio_ant = CAST((@anio_num - 1) AS VARCHAR(4)) + '-'
                  + RIGHT('00' + CAST(@mes_num AS VARCHAR(2)), 2);

-- Últimos 3 meses cerrados relativos al mes target:
-- si @mes_target = 2026-05 → meses cerrados 2026-02, 2026-03, 2026-04
-- y año anterior correspondiente 2025-02, 2025-03, 2025-04.
DECLARE @m1_act VARCHAR(7), @m2_act VARCHAR(7), @m3_act VARCHAR(7);
DECLARE @m1_ant VARCHAR(7), @m2_ant VARCHAR(7), @m3_ant VARCHAR(7);

-- Mes target como primer día de mes
DECLARE @fecha_target DATE = CAST(@mes_target + '-01' AS DATE);

SET @m1_act = CONVERT(VARCHAR(7), DATEADD(month, -3, @fecha_target), 120);
SET @m2_act = CONVERT(VARCHAR(7), DATEADD(month, -2, @fecha_target), 120);
SET @m3_act = CONVERT(VARCHAR(7), DATEADD(month, -1, @fecha_target), 120);

SET @m1_ant = CONVERT(VARCHAR(7), DATEADD(month, -15, @fecha_target), 120);
SET @m2_ant = CONVERT(VARCHAR(7), DATEADD(month, -14, @fecha_target), 120);
SET @m3_ant = CONVERT(VARCHAR(7), DATEADD(month, -13, @fecha_target), 120);

PRINT '============================================================';
PRINT 'Presupuesto por local';
PRINT '  mes_target     = ' + @mes_target;
PRINT '  mes_anio_ant   = ' + @mes_anio_ant;
PRINT '  ventana actual = ' + @m1_act + ', ' + @m2_act + ', ' + @m3_act;
PRINT '  ventana ant-1  = ' + @m1_ant + ', ' + @m2_ant + ', ' + @m3_ant;
PRINT '  deps_csv       = ' + @deps_csv;
PRINT '============================================================';

-- ---------- RESOLVER LISTA DEPS CORE ----------
DECLARE @deps_core TABLE (dep INT PRIMARY KEY);

IF LOWER(@deps_csv) = 'all'
BEGIN
    INSERT INTO @deps_core (dep) VALUES (0),(2),(6),(7),(8),(11);
END
ELSE
BEGIN
    -- Parsear CSV manualmente (compatible SQL 2012, sin STRING_SPLIT)
    DECLARE @rest VARCHAR(100) = @deps_csv + ',';
    DECLARE @tok  VARCHAR(20);
    DECLARE @pos  INT;

    WHILE LEN(@rest) > 0
    BEGIN
        SET @pos = CHARINDEX(',', @rest);
        IF @pos = 0 BREAK;
        SET @tok = LTRIM(RTRIM(SUBSTRING(@rest, 1, @pos - 1)));
        IF LEN(@tok) > 0 AND ISNUMERIC(@tok) = 1
        BEGIN
            INSERT INTO @deps_core (dep) VALUES (CAST(@tok AS INT));
        END
        SET @rest = SUBSTRING(@rest, @pos + 1, LEN(@rest));
    END
END

-- ---------- EXCLUSIÓN PANDEMIA ----------
DECLARE @excl_pandemia TABLE (mes VARCHAR(7) PRIMARY KEY);
INSERT INTO @excl_pandemia (mes) VALUES ('2020-03'),('2020-04'),('2020-05'),('2021-06');

-- ---------- CÁLCULO ----------
;WITH
mma1_local AS (
    -- MMA-1 por local (mismo mes año anterior)
    SELECT
        cpl.deposito                               AS deposito,
        SUM(CAST(cpl.costo_cer AS DECIMAL(18,2)))  AS mma1
    FROM omicronvt.dbo.compras_por_local cpl
    INNER JOIN @deps_core d ON d.dep = cpl.deposito
    LEFT JOIN @excl_pandemia p ON p.mes = cpl.mes
    WHERE cpl.mes = @mes_anio_ant
      AND p.mes IS NULL
      AND ISNUMERIC(CAST(cpl.costo_cer AS VARCHAR(30))) = 1
    GROUP BY cpl.deposito
),
ventana_actual AS (
    -- SUM cadena últimos 3 meses cerrados
    SELECT
        SUM(CAST(cpl.costo_cer AS DECIMAL(18,2))) AS total_act
    FROM omicronvt.dbo.compras_por_local cpl
    INNER JOIN @deps_core d ON d.dep = cpl.deposito
    LEFT JOIN @excl_pandemia p ON p.mes = cpl.mes
    WHERE cpl.mes IN (@m1_act, @m2_act, @m3_act)
      AND p.mes IS NULL
      AND ISNUMERIC(CAST(cpl.costo_cer AS VARCHAR(30))) = 1
),
ventana_ant AS (
    -- SUM cadena mismos 3 meses año anterior
    SELECT
        SUM(CAST(cpl.costo_cer AS DECIMAL(18,2))) AS total_ant
    FROM omicronvt.dbo.compras_por_local cpl
    INNER JOIN @deps_core d ON d.dep = cpl.deposito
    LEFT JOIN @excl_pandemia p ON p.mes = cpl.mes
    WHERE cpl.mes IN (@m1_ant, @m2_ant, @m3_ant)
      AND p.mes IS NULL
      AND ISNUMERIC(CAST(cpl.costo_cer AS VARCHAR(30))) = 1
),
factor AS (
    SELECT
        CASE
            WHEN va.total_ant IS NULL OR va.total_ant = 0 THEN 1.0
            ELSE CAST(vact.total_act AS DECIMAL(18,4))
               / CAST(va.total_ant   AS DECIMAL(18,4))
        END AS factor_yoy
    FROM ventana_actual vact
    CROSS JOIN ventana_ant va
),
total_mma1 AS (
    SELECT SUM(mma1) AS total FROM mma1_local
)
SELECT
    m.deposito                                                      AS deposito,
    CAST(m.mma1 AS DECIMAL(18,2))                                   AS mma1,
    CAST(f.factor_yoy AS DECIMAL(8,4))                              AS factor_yoy,
    CASE
        WHEN t.total IS NULL OR t.total = 0 THEN 0
        ELSE CAST(m.mma1 / t.total AS DECIMAL(8,4))
    END                                                             AS share,
    CAST(m.mma1 * f.factor_yoy AS DECIMAL(18,2))                    AS presupuesto_sugerido
FROM mma1_local m
CROSS JOIN factor f
CROSS JOIN total_mma1 t
ORDER BY m.deposito;

GO
