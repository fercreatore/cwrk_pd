-- ============================================================
-- vel_real_articulo — Velocidad real corregida por quiebre
-- ============================================================
-- Tabla materializada con vel_real para los artículos con ventas
-- en los últimos 12 meses. Usada por:
--   - calce_financiero.py (BLOQUE 2b: recupero real)
--   - ranking_consolidado.py (columna vel_real en RC0002)
--   - presupuesto por industria (factor_quiebre promedio)
--
-- EJECUTAR EN: 192.168.2.111 (producción) con sqlcmd o SSMS
-- Para poblar: ejecutar crear_tabla_vel_real.py en Mac/111
--              python crear_tabla_vel_real.py
--
-- Autor: Cowork + Claude — Marzo 2026
-- ============================================================

USE omicronvt;
GO

-- ============================================================
-- 1. CREATE TABLE
-- ============================================================

IF OBJECT_ID('dbo.vel_real_articulo', 'U') IS NOT NULL
    DROP TABLE dbo.vel_real_articulo;
GO

CREATE TABLE dbo.vel_real_articulo (
    codigo            VARCHAR(20)   NOT NULL,   -- codigo_sinonimo (LEFT 10 o 12)
    vel_aparente      DECIMAL(10,2) NOT NULL,   -- ventas_total / meses_totales
    vel_real          DECIMAL(10,2) NOT NULL,   -- ventas_ok / meses_con_stock
    meses_con_stock   INT           NOT NULL,   -- meses sin quiebre (stock_inicio > 0)
    meses_quebrado    INT           NOT NULL,   -- meses con stock_inicio <= 0
    factor_quiebre    DECIMAL(8,3)  NOT NULL,   -- vel_real / vel_aparente (>1 = sub-comprado)
    fecha_calculo     DATE          NOT NULL,   -- fecha en que se calculó
    CONSTRAINT PK_vel_real_articulo PRIMARY KEY (codigo)
);
GO

-- Índice para JOINs desde calce/presupuesto/ranking
CREATE INDEX IX_vel_real_factor
    ON dbo.vel_real_articulo (codigo)
    INCLUDE (vel_real, factor_quiebre, vel_aparente);
GO

-- ============================================================
-- 2. INSERT: Top 500 artículos por ventas (12 meses)
-- ============================================================
-- NOTA: Este bloque es un template. Los datos reales se generan
-- ejecutando crear_tabla_vel_real.py que calcula el quiebre
-- reconstruyendo stock mes a mes hacia atrás.
--
-- Lógica del cálculo (replicada de app_reposicion.py):
--   1. stock_actual = SUM(stock_actual) de msgestionC.dbo.stock
--   2. Para cada mes (12 meses hacia atrás):
--      stock_inicio = stock_fin + ventas_mes - compras_mes
--      Si stock_inicio <= 0 → mes QUEBRADO
--   3. vel_aparente = ventas_total / 12
--   4. vel_real = ventas_en_meses_ok / meses_ok
--   5. factor_quiebre = vel_real / vel_aparente
--
-- Para insertar los top 500 manualmente desde SQL:
-- (Aproximación: sin reconstrucción de stock, solo ventas/12)
-- La versión Python es más precisa.

;WITH ventas_12m AS (
    SELECT
        RTRIM(a.codigo_sinonimo) AS codigo,
        SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                 WHEN v.operacion='-' THEN -v.cantidad END) AS ventas_total,
        COUNT(DISTINCT CAST(YEAR(v.fecha) AS VARCHAR) + '-' + CAST(MONTH(v.fecha) AS VARCHAR)) AS meses_con_venta
    FROM msgestionC.dbo.ventas1 v
    JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
    WHERE v.codigo NOT IN (7, 36)
      AND v.fecha >= DATEADD(MONTH, -12, GETDATE())
      AND a.codigo_sinonimo IS NOT NULL
      AND a.codigo_sinonimo <> ''
      AND LEN(RTRIM(a.codigo_sinonimo)) >= 5
      AND a.marca NOT IN (1316, 1317, 1158, 436)
    GROUP BY RTRIM(a.codigo_sinonimo)
    HAVING SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                    WHEN v.operacion='-' THEN -v.cantidad END) > 0
),
stock_actual AS (
    SELECT
        RTRIM(a.codigo_sinonimo) AS codigo,
        ISNULL(SUM(s.stock_actual), 0) AS stock
    FROM msgestionC.dbo.stock s
    JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
    WHERE s.deposito IN (0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)
      AND a.codigo_sinonimo IS NOT NULL
      AND LEN(RTRIM(a.codigo_sinonimo)) >= 5
    GROUP BY RTRIM(a.codigo_sinonimo)
),
-- Aproximación SQL del quiebre:
-- meses_con_stock ≈ meses donde hubo ventas (proxy, no reconstrucción real)
-- vel_real ≈ ventas_total / meses_con_venta (solo meses activos)
-- NOTA: La reconstrucción real de stock requiere Python (crear_tabla_vel_real.py)
top500 AS (
    SELECT TOP 500
        v.codigo,
        ROUND(v.ventas_total / 12.0, 2) AS vel_aparente,
        ROUND(v.ventas_total / CAST(NULLIF(v.meses_con_venta, 0) AS FLOAT), 2) AS vel_real,
        v.meses_con_venta AS meses_con_stock,
        12 - v.meses_con_venta AS meses_quebrado,
        ROUND(
            (v.ventas_total / CAST(NULLIF(v.meses_con_venta, 0) AS FLOAT))
            / NULLIF(v.ventas_total / 12.0, 0),
            3
        ) AS factor_quiebre,
        CAST(GETDATE() AS DATE) AS fecha_calculo
    FROM ventas_12m v
    LEFT JOIN stock_actual s ON s.codigo = v.codigo
    WHERE v.ventas_total > 0
    ORDER BY v.ventas_total DESC
)
INSERT INTO dbo.vel_real_articulo
    (codigo, vel_aparente, vel_real, meses_con_stock, meses_quebrado, factor_quiebre, fecha_calculo)
SELECT codigo, vel_aparente, vel_real, meses_con_stock, meses_quebrado, factor_quiebre, fecha_calculo
FROM top500;
GO

PRINT 'vel_real_articulo: top 500 insertados (aproximación SQL)';
PRINT 'Para datos precisos con reconstrucción de stock, ejecutar crear_tabla_vel_real.py';
GO

-- ============================================================
-- 3. Verificación
-- ============================================================
SELECT
    COUNT(*) AS total_registros,
    AVG(factor_quiebre) AS factor_quiebre_promedio,
    SUM(CASE WHEN factor_quiebre >= 2.0 THEN 1 ELSE 0 END) AS sub_comprados_2x,
    SUM(CASE WHEN factor_quiebre >= 3.0 THEN 1 ELSE 0 END) AS sub_comprados_3x,
    MAX(factor_quiebre) AS max_factor
FROM dbo.vel_real_articulo;
GO
