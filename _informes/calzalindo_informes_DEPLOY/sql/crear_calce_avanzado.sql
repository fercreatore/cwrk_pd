-- =============================================================================
-- CALCE FINANCIERO AVANZADO - 4 Mejoras para Decision de Compra
-- Calzalindo H4 - Dashboard CFO
-- Ejecutar en: 192.168.2.112 (DATASVRW replica) -> omicronvt
-- Fecha: 2026-03-15
--
-- MEJORAS:
--   1. Flujo de Caja Semanal Proyectado (pagos vs cobranzas)
--   2. ROI por Proveedor / Ranking de Compra
--   3. Capital de Trabajo Mensual con Estacionalidad
--   4. Datos Enriquecedores (margen, concentracion, stock muerto)
-- =============================================================================
USE omicronvt;
GO

-- #############################################################################
-- MEJORA 1: FLUJO DE CAJA SEMANAL PROYECTADO
-- Timeline 12 semanas: pagos comprometidos (OPs) vs cobranzas estimadas
-- #############################################################################

IF OBJECT_ID('dbo.t_flujo_caja_semanal', 'U') IS NOT NULL
    DROP TABLE dbo.t_flujo_caja_semanal;
GO

CREATE TABLE dbo.t_flujo_caja_semanal (
    semana_numero       INT            NOT NULL,  -- 1 a 12
    semana_inicio       DATE           NOT NULL,
    semana_fin          DATE           NOT NULL,
    -- Egresos (pagos a proveedores)
    pagos_ops           DECIMAL(18,2)  DEFAULT 0,  -- OPs con vencimiento en esta semana
    pagos_cheques       DECIMAL(18,2)  DEFAULT 0,  -- cheques diferidos por vencer
    pagos_total         DECIMAL(18,2)  DEFAULT 0,
    cant_ops            INT            DEFAULT 0,
    cant_proveedores    INT            DEFAULT 0,
    -- Ingresos estimados (cobranzas por ventas)
    cobranza_estimada   DECIMAL(18,2)  DEFAULT 0,  -- basada en run rate + estacionalidad
    cobranza_costo      DECIMAL(18,2)  DEFAULT 0,  -- a costo (para comparar con pagos a costo)
    -- Balance
    balance_semanal     DECIMAL(18,2)  DEFAULT 0,  -- cobranza - pagos
    balance_acumulado   DECIMAL(18,2)  DEFAULT 0,  -- running total
    -- Metadata
    fecha_calculo       DATETIME       DEFAULT GETDATE(),
    PRIMARY KEY (semana_numero)
);
GO

-- #############################################################################
-- MEJORA 2: ROI POR PROVEEDOR / RANKING DE COMPRA
-- Score = (margen_bruto% x rotacion_anualizada) para priorizar compras
-- #############################################################################

IF OBJECT_ID('dbo.t_roi_proveedor', 'U') IS NOT NULL
    DROP TABLE dbo.t_roi_proveedor;
GO

CREATE TABLE dbo.t_roi_proveedor (
    proveedor_id        INT            NOT NULL,
    proveedor_nombre    VARCHAR(200)   NOT NULL,
    industria           VARCHAR(100)   NOT NULL,
    -- Margen
    margen_bruto_pct    DECIMAL(8,2)   DEFAULT 0,  -- (precio_venta - costo) / precio_venta * 100
    venta_total         DECIMAL(18,2)  DEFAULT 0,  -- venta a precio ultimos 12 meses
    costo_total         DECIMAL(18,2)  DEFAULT 0,  -- venta a costo ultimos 12 meses
    unidades_vendidas   INT            DEFAULT 0,
    -- Rotacion
    dias_50             INT            DEFAULT 0,  -- de t_recupero_inversion
    dias_75             INT            DEFAULT 0,
    rotacion_anual      DECIMAL(8,2)   DEFAULT 0,  -- 365 / dias_50
    -- ROI
    roi_anualizado      DECIMAL(8,2)   DEFAULT 0,  -- margen% x rotacion_anual
    roi_por_peso        DECIMAL(8,4)   DEFAULT 0,  -- roi / 100 (retorno por cada peso invertido)
    -- Calce
    plazo_pago          INT            DEFAULT 0,
    brecha              INT            DEFAULT 0,  -- plazo_pago - dias_50
    pct_vendido_al_pago DECIMAL(8,2)   DEFAULT 0,
    -- Score final (normalizado 0-100)
    score_compra        DECIMAL(8,2)   DEFAULT 0,
    ranking             INT            DEFAULT 0,
    recomendacion       VARCHAR(200)   DEFAULT '',
    -- Metadata
    fecha_calculo       DATETIME       DEFAULT GETDATE(),
    PRIMARY KEY (proveedor_id, industria)
);
GO

-- #############################################################################
-- MEJORA 3: CAPITAL DE TRABAJO MENSUAL CON ESTACIONALIDAD
-- Curva de necesidad de capital mes a mes (mar-ago invierno 2026)
-- #############################################################################

IF OBJECT_ID('dbo.t_capital_trabajo_mensual', 'U') IS NOT NULL
    DROP TABLE dbo.t_capital_trabajo_mensual;
GO

CREATE TABLE dbo.t_capital_trabajo_mensual (
    industria           VARCHAR(100)   NOT NULL,
    mes                 INT            NOT NULL,  -- 3-8 para invierno
    mes_nombre          VARCHAR(20)    NOT NULL,
    -- Estacionalidad
    idx_estacionalidad  DECIMAL(8,4)   DEFAULT 0,  -- % del anual que representa este mes
    -- Capital necesario
    compras_estimadas   DECIMAL(18,2)  DEFAULT 0,  -- comprometido distribuido por estacionalidad
    ventas_estimadas    DECIMAL(18,2)  DEFAULT 0,  -- proyeccion de ventas a costo por mes
    -- Recupero estimado
    recupero_estimado   DECIMAL(18,2)  DEFAULT 0,  -- ventas estimadas ajustadas por dias_50
    -- Balance
    capital_neto        DECIMAL(18,2)  DEFAULT 0,  -- compras - recupero (+ = necesitas capital)
    capital_acumulado   DECIMAL(18,2)  DEFAULT 0,  -- running total de capital inmovilizado
    pico_capital        BIT            DEFAULT 0,  -- 1 si es el mes de mayor inmovilizacion
    -- Metadata
    fecha_calculo       DATETIME       DEFAULT GETDATE(),
    PRIMARY KEY (industria, mes)
);
GO

-- #############################################################################
-- MEJORA 4: DATOS ENRIQUECEDORES
-- Margen por industria, concentracion de riesgo, stock muerto
-- #############################################################################

IF OBJECT_ID('dbo.t_enriquecedores_calce', 'U') IS NOT NULL
    DROP TABLE dbo.t_enriquecedores_calce;
GO

CREATE TABLE dbo.t_enriquecedores_calce (
    industria           VARCHAR(100)   NOT NULL,
    -- Margen bruto
    margen_bruto_pct    DECIMAL(8,2)   DEFAULT 0,
    venta_precio_12m    DECIMAL(18,2)  DEFAULT 0,  -- ultimos 12 meses a precio
    venta_costo_12m     DECIMAL(18,2)  DEFAULT 0,  -- ultimos 12 meses a costo
    -- Concentracion de riesgo
    top1_proveedor      VARCHAR(200)   DEFAULT '',
    top1_pct            DECIMAL(8,2)   DEFAULT 0,  -- % del comprometido total
    top3_pct            DECIMAL(8,2)   DEFAULT 0,  -- % acumulado top 3
    top3_proveedores    VARCHAR(600)   DEFAULT '',  -- nombres separados por coma
    nivel_concentracion VARCHAR(20)    DEFAULT '',  -- ALTO (>70%), MEDIO (50-70%), BAJO (<50%)
    -- Stock sin movimiento
    stock_muerto_90d_uds   INT         DEFAULT 0,  -- articulos sin venta >90 dias con stock>0
    stock_muerto_90d_costo DECIMAL(18,2) DEFAULT 0,
    stock_muerto_180d_uds  INT         DEFAULT 0,
    stock_muerto_180d_costo DECIMAL(18,2) DEFAULT 0,
    -- Metadata
    fecha_calculo       DATETIME       DEFAULT GETDATE(),
    PRIMARY KEY (industria)
);
GO

-- #############################################################################
-- SP PRINCIPAL: CALCULA LAS 4 MEJORAS
-- #############################################################################

IF OBJECT_ID('dbo.sp_calcular_calce_avanzado', 'P') IS NOT NULL
    DROP PROCEDURE dbo.sp_calcular_calce_avanzado;
GO

CREATE PROCEDURE dbo.sp_calcular_calce_avanzado
AS
BEGIN
    SET NOCOUNT ON;

    -- =================================================================
    -- MEJORA 1: FLUJO DE CAJA SEMANAL
    -- =================================================================
    TRUNCATE TABLE t_flujo_caja_semanal;

    -- Generar 12 semanas desde hoy
    DECLARE @i INT = 1;
    DECLARE @hoy DATE = CAST(GETDATE() AS DATE);
    -- Inicio de semana actual (lunes)
    DECLARE @lunes DATE = DATEADD(DAY, -(DATEPART(WEEKDAY, @hoy) + 5) % 7, @hoy);

    WHILE @i <= 12
    BEGIN
        INSERT INTO t_flujo_caja_semanal (semana_numero, semana_inicio, semana_fin)
        VALUES (
            @i,
            DATEADD(WEEK, @i - 1, @lunes),
            DATEADD(DAY, 6, DATEADD(WEEK, @i - 1, @lunes))
        );
        SET @i = @i + 1;
    END;

    -- Pagos: OPs con vencimiento en cada semana (de moviprov2)
    -- moviprov2.fecha_vencimiento = cuando vence el cheque/transferencia
    UPDATE f SET
        pagos_ops = ISNULL(x.total_importe, 0),
        pagos_total = ISNULL(x.total_importe, 0),
        cant_ops = ISNULL(x.cant, 0),
        cant_proveedores = ISNULL(x.provs, 0)
    FROM t_flujo_caja_semanal f
    OUTER APPLY (
        SELECT
            SUM(m.importe_can_pesos) AS total_importe,
            COUNT(*) AS cant,
            COUNT(DISTINCT m.numero_cuenta) AS provs
        FROM msgestionC.dbo.moviprov2 m
        WHERE m.fecha_vencimiento BETWEEN f.semana_inicio AND f.semana_fin
          AND m.fecha_cancelacion IS NOT NULL
    ) x;

    -- Cobranza estimada: run rate semanal de ventas (ultimos 60 dias)
    -- a precio (lo que cobra la empresa) y a costo (para comparar con pagos)
    DECLARE @run_rate_precio DECIMAL(18,2);
    DECLARE @run_rate_costo DECIMAL(18,2);
    DECLARE @dias_muestra INT;

    SELECT
        @dias_muestra = DATEDIFF(DAY, MIN(v2.fecha_comprobante), MAX(v2.fecha_comprobante)),
        @run_rate_precio = CASE
            WHEN DATEDIFF(DAY, MIN(v2.fecha_comprobante), MAX(v2.fecha_comprobante)) > 0
            THEN SUM(v1.cantidad * v1.precio) * 7.0 /
                 DATEDIFF(DAY, MIN(v2.fecha_comprobante), MAX(v2.fecha_comprobante))
            ELSE 0 END,
        @run_rate_costo = CASE
            WHEN DATEDIFF(DAY, MIN(v2.fecha_comprobante), MAX(v2.fecha_comprobante)) > 0
            THEN SUM(v1.cantidad * v1.precio_costo) * 7.0 /
                 DATEDIFF(DAY, MIN(v2.fecha_comprobante), MAX(v2.fecha_comprobante))
            ELSE 0 END
    FROM msgestionC.dbo.ventas1 v1
    JOIN msgestionC.dbo.ventas2 v2
        ON v1.empresa = v2.empresa AND v1.codigo = v2.codigo
       AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
       AND v1.numero = v2.numero AND v1.orden = v2.orden
    WHERE v2.codigo IN (1, 6, 21, 61)  -- facturas de venta
      AND v2.fecha_comprobante >= DATEADD(DAY, -60, GETDATE())
      AND v2.fecha_comprobante < CAST(GETDATE() AS DATE);

    -- Ajustar cobranza por estacionalidad mensual (si hay datos)
    -- Usa idx_estacionalidad promedio de todas las industrias
    UPDATE f SET
        cobranza_estimada = ISNULL(@run_rate_precio, 0) *
            CASE WHEN ISNULL(est.factor, 0) > 0 THEN est.factor ELSE 1.0 END,
        cobranza_costo = ISNULL(@run_rate_costo, 0) *
            CASE WHEN ISNULL(est.factor, 0) > 0 THEN est.factor ELSE 1.0 END
    FROM t_flujo_caja_semanal f
    OUTER APPLY (
        -- Factor estacional del mes de esta semana vs mes actual
        SELECT
            CASE WHEN avg_actual > 0
                 THEN avg_semana / avg_actual
                 ELSE 1.0
            END AS factor
        FROM (
            SELECT
                (SELECT AVG(idx_estacionalidad) FROM t_tendencia_facturacion
                 WHERE mes = MONTH(f.semana_inicio) AND idx_estacionalidad > 0) AS avg_semana,
                (SELECT AVG(idx_estacionalidad) FROM t_tendencia_facturacion
                 WHERE mes = MONTH(GETDATE()) AND idx_estacionalidad > 0) AS avg_actual
        ) sub
    ) est;

    -- Balance semanal y acumulado
    UPDATE t_flujo_caja_semanal SET
        balance_semanal = cobranza_estimada - pagos_total;

    -- Balance acumulado (cursor simple)
    DECLARE @bal_acum DECIMAL(18,2) = 0;
    DECLARE @sem INT;
    DECLARE cur_bal CURSOR LOCAL FAST_FORWARD FOR
        SELECT semana_numero FROM t_flujo_caja_semanal ORDER BY semana_numero;
    OPEN cur_bal;
    FETCH NEXT FROM cur_bal INTO @sem;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        SELECT @bal_acum = @bal_acum + balance_semanal FROM t_flujo_caja_semanal WHERE semana_numero = @sem;
        UPDATE t_flujo_caja_semanal SET balance_acumulado = @bal_acum WHERE semana_numero = @sem;
        FETCH NEXT FROM cur_bal INTO @sem;
    END;
    CLOSE cur_bal;
    DEALLOCATE cur_bal;

    UPDATE t_flujo_caja_semanal SET fecha_calculo = GETDATE();

    PRINT 'Flujo de caja semanal calculado OK.';

    -- =================================================================
    -- MEJORA 2: ROI POR PROVEEDOR
    -- =================================================================
    TRUNCATE TABLE t_roi_proveedor;

    -- Ventas por proveedor (ultimos 12 meses) para calcular margen
    INSERT INTO t_roi_proveedor (
        proveedor_id, proveedor_nombre, industria,
        venta_total, costo_total, unidades_vendidas, margen_bruto_pct
    )
    SELECT
        p.numero AS proveedor_id,
        RTRIM(p.denominacion) AS proveedor_nombre,
        ISNULL(ind.industria, 'Sin clasificar') AS industria,
        SUM(v1.cantidad * v1.precio) AS venta_total,
        SUM(v1.cantidad * v1.precio_costo) AS costo_total,
        SUM(v1.cantidad) AS unidades_vendidas,
        CASE WHEN SUM(v1.cantidad * v1.precio) > 0
             THEN ROUND((SUM(v1.cantidad * v1.precio) - SUM(v1.cantidad * v1.precio_costo))
                        * 100.0 / SUM(v1.cantidad * v1.precio), 2)
             ELSE 0
        END AS margen_bruto_pct
    FROM msgestionC.dbo.ventas1 v1
    JOIN msgestionC.dbo.ventas2 v2
        ON v1.empresa = v2.empresa AND v1.codigo = v2.codigo
       AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
       AND v1.numero = v2.numero AND v1.orden = v2.orden
    JOIN msgestion01art.dbo.articulo a ON v1.articulo = a.codigo
    LEFT JOIN msgestionC.dbo.proveedores p ON a.proveedor = p.numero
    LEFT JOIN map_subrubro_industria ind ON a.subrubro = ind.subrubro
    WHERE v2.codigo IN (1, 6, 21, 61)
      AND v2.fecha_comprobante >= DATEADD(MONTH, -12, GETDATE())
      AND a.subrubro > 0
      AND p.numero IS NOT NULL
    GROUP BY p.numero, RTRIM(p.denominacion), ind.industria
    HAVING SUM(v1.cantidad * v1.precio) > 0;

    -- Cruzar con recupero (dias_50, plazo_pago, etc.)
    UPDATE r SET
        dias_50 = ISNULL(rec.d50, 0),
        dias_75 = ISNULL(rec.d75, 0),
        plazo_pago = ISNULL(rec.plazo, 0),
        brecha = ISNULL(rec.brecha, 0),
        pct_vendido_al_pago = ISNULL(rec.pct_pago, 0),
        rotacion_anual = CASE WHEN ISNULL(rec.d50, 0) > 0
                              THEN ROUND(365.0 / rec.d50, 2)
                              ELSE 0 END,
        roi_anualizado = CASE WHEN ISNULL(rec.d50, 0) > 0
                              THEN ROUND(r.margen_bruto_pct * (365.0 / rec.d50), 2)
                              ELSE 0 END,
        roi_por_peso = CASE WHEN ISNULL(rec.d50, 0) > 0
                            THEN ROUND(r.margen_bruto_pct * (365.0 / rec.d50) / 100.0, 4)
                            ELSE 0 END
    FROM t_roi_proveedor r
    OUTER APPLY (
        SELECT
            AVG(CAST(t.dias_50 AS FLOAT)) AS d50,
            AVG(CAST(t.dias_75 AS FLOAT)) AS d75,
            AVG(t.plazo_pago_real_prom) AS plazo,
            AVG(t.brecha_pago_vs_rec50) AS brecha,
            AVG(t.pct_vendido_al_pago) AS pct_pago
        FROM t_recupero_inversion t
        WHERE t.proveedor_id = r.proveedor_id
          AND t.industria = r.industria
    ) rec;

    -- Score de compra (0-100): combina ROI + calce + margen
    -- Normalizar ROI: max 500% anualizado = 100 puntos
    -- Normalizar calce: brecha > 0 suma puntos, < 0 resta
    DECLARE @max_roi DECIMAL(18,2);
    SELECT @max_roi = MAX(roi_anualizado) FROM t_roi_proveedor WHERE roi_anualizado > 0;
    IF @max_roi IS NULL OR @max_roi = 0 SET @max_roi = 1;

    UPDATE t_roi_proveedor SET
        score_compra = ROUND(
            -- 50% peso ROI (normalizado al max)
            (CASE WHEN roi_anualizado > 0 THEN (roi_anualizado / @max_roi) * 50 ELSE 0 END)
            -- 30% peso calce financiero (brecha positiva = bueno)
            + (CASE WHEN brecha >= 30 THEN 30
                    WHEN brecha >= 0  THEN brecha * 1.0
                    WHEN brecha >= -30 THEN brecha * 0.5
                    ELSE -15 END)
            -- 20% peso margen bruto
            + (CASE WHEN margen_bruto_pct >= 60 THEN 20
                    WHEN margen_bruto_pct >= 40 THEN 15
                    WHEN margen_bruto_pct >= 25 THEN 10
                    ELSE margen_bruto_pct * 0.3 END)
        , 1);

    -- Ranking
    ;WITH ranked AS (
        SELECT proveedor_id, industria,
               ROW_NUMBER() OVER (ORDER BY score_compra DESC) AS rn
        FROM t_roi_proveedor
    )
    UPDATE r SET ranking = rn
    FROM t_roi_proveedor r
    JOIN ranked ON r.proveedor_id = ranked.proveedor_id AND r.industria = ranked.industria;

    -- Recomendacion textual
    UPDATE t_roi_proveedor SET
        recomendacion = CASE
            WHEN score_compra >= 70 THEN 'PRIORIZAR: Alta rotacion + buen margen. Comprar con capital del proveedor.'
            WHEN score_compra >= 50 THEN 'COMPRAR: Buen retorno. Negociar plazo si brecha es negativa.'
            WHEN score_compra >= 30 THEN 'EVALUAR: Retorno moderado. Solo si hay presupuesto disponible.'
            WHEN score_compra >= 10 THEN 'POSTERGAR: Bajo retorno o alto riesgo de inmovilizacion.'
            ELSE 'EVITAR: Capital inmovilizado sin retorno adecuado.'
        END,
        fecha_calculo = GETDATE();

    PRINT 'ROI por proveedor calculado OK.';

    -- =================================================================
    -- MEJORA 3: CAPITAL DE TRABAJO MENSUAL
    -- =================================================================
    TRUNCATE TABLE t_capital_trabajo_mensual;

    -- Para cada industria x mes del periodo activo
    INSERT INTO t_capital_trabajo_mensual (
        industria, mes, mes_nombre, idx_estacionalidad,
        compras_estimadas, ventas_estimadas, recupero_estimado,
        capital_neto
    )
    SELECT
        per.industria,
        m.mes,
        CASE m.mes
            WHEN 1 THEN 'Enero' WHEN 2 THEN 'Febrero' WHEN 3 THEN 'Marzo'
            WHEN 4 THEN 'Abril' WHEN 5 THEN 'Mayo' WHEN 6 THEN 'Junio'
            WHEN 7 THEN 'Julio' WHEN 8 THEN 'Agosto' WHEN 9 THEN 'Septiembre'
            WHEN 10 THEN 'Octubre' WHEN 11 THEN 'Noviembre' WHEN 12 THEN 'Diciembre'
        END AS mes_nombre,
        ISNULL(tf.idx_estacionalidad, 0) AS idx_est,
        -- Compras estimadas: comprometido distribuido segun estacionalidad de compra
        -- Simplificacion: distribución uniforme del comprometido en los meses del periodo
        CASE WHEN ISNULL(total_idx.sum_idx, 0) > 0
             THEN ROUND(ISNULL(pres.comprometido_costo, 0) *
                        ISNULL(tf.idx_estacionalidad, 0) / total_idx.sum_idx, 0)
             ELSE 0
        END AS compras_estimadas,
        -- Ventas estimadas: presupuesto (venta anio anterior) x factor tendencia x estacionalidad
        CASE WHEN ISNULL(total_idx.sum_idx, 0) > 0
             THEN ROUND(ISNULL(pres.presupuesto_costo, 0) *
                        ISNULL(pres.factor_tendencia, 1.0) *
                        ISNULL(tf.idx_estacionalidad, 0) / total_idx.sum_idx, 0)
             ELSE 0
        END AS ventas_estimadas,
        -- Recupero: ventas estimadas ajustadas por velocidad de recupero
        -- Si dias_50 = 30 y estamos en mes M, parte de las ventas de M se cobran en M+1
        -- Simplificacion: 70% de la venta se recupera en el mismo mes si dias_50 < 45
        CASE WHEN ISNULL(total_idx.sum_idx, 0) > 0
             THEN ROUND(ISNULL(pres.presupuesto_costo, 0) *
                        ISNULL(pres.factor_tendencia, 1.0) *
                        ISNULL(tf.idx_estacionalidad, 0) / total_idx.sum_idx *
                        CASE WHEN ISNULL(rec.dias_50_prom, 45) <= 30 THEN 0.85
                             WHEN ISNULL(rec.dias_50_prom, 45) <= 45 THEN 0.70
                             WHEN ISNULL(rec.dias_50_prom, 45) <= 60 THEN 0.55
                             ELSE 0.40 END
                  , 0)
             ELSE 0
        END AS recupero_estimado,
        -- Capital neto = compras - recupero (positivo = necesitas poner capital)
        0 AS capital_neto  -- se calcula despues
    FROM t_periodos_industria per
    CROSS JOIN (
        SELECT 1 AS mes UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
        UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8
        UNION SELECT 9 UNION SELECT 10 UNION SELECT 11 UNION SELECT 12
    ) m
    LEFT JOIN t_tendencia_facturacion tf
        ON per.industria = tf.industria AND m.mes = tf.mes
    LEFT JOIN t_presupuesto_industria pres
        ON per.industria = pres.industria AND per.temporada = pres.temporada
    -- Suma total de idx_estacionalidad en el periodo (para distribuir)
    OUTER APPLY (
        SELECT SUM(idx_estacionalidad) AS sum_idx
        FROM t_tendencia_facturacion t2
        WHERE t2.industria = per.industria
          AND (
              (per.mes_desde <= per.mes_hasta AND t2.mes BETWEEN per.mes_desde AND per.mes_hasta)
              OR
              (per.mes_desde > per.mes_hasta AND (t2.mes >= per.mes_desde OR t2.mes <= per.mes_hasta))
          )
    ) total_idx
    -- Dias 50 promedio de la industria (para estimar recupero)
    OUTER APPLY (
        SELECT AVG(CAST(dias_50 AS FLOAT)) AS dias_50_prom
        FROM t_recupero_inversion ri
        WHERE ri.industria = per.industria
    ) rec
    WHERE per.activo = 1
      AND (
          (per.mes_desde <= per.mes_hasta AND m.mes BETWEEN per.mes_desde AND per.mes_hasta)
          OR
          (per.mes_desde > per.mes_hasta AND (m.mes >= per.mes_desde OR m.mes <= per.mes_hasta))
      );

    -- Calcular capital neto
    UPDATE t_capital_trabajo_mensual SET
        capital_neto = compras_estimadas - recupero_estimado;

    -- Capital acumulado (por industria)
    DECLARE @ind VARCHAR(100), @acum DECIMAL(18,2), @m INT;
    DECLARE cur_cap CURSOR LOCAL FAST_FORWARD FOR
        SELECT DISTINCT industria FROM t_capital_trabajo_mensual;
    OPEN cur_cap;
    FETCH NEXT FROM cur_cap INTO @ind;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @acum = 0;
        DECLARE cur_mes CURSOR LOCAL FAST_FORWARD FOR
            SELECT mes FROM t_capital_trabajo_mensual WHERE industria = @ind ORDER BY mes;
        OPEN cur_mes;
        FETCH NEXT FROM cur_mes INTO @m;
        WHILE @@FETCH_STATUS = 0
        BEGIN
            SELECT @acum = @acum + capital_neto
            FROM t_capital_trabajo_mensual WHERE industria = @ind AND mes = @m;
            UPDATE t_capital_trabajo_mensual SET capital_acumulado = @acum
            WHERE industria = @ind AND mes = @m;
            FETCH NEXT FROM cur_mes INTO @m;
        END;
        CLOSE cur_mes;
        DEALLOCATE cur_mes;
        FETCH NEXT FROM cur_cap INTO @ind;
    END;
    CLOSE cur_cap;
    DEALLOCATE cur_cap;

    -- Marcar pico de capital por industria
    UPDATE c SET pico_capital = 1
    FROM t_capital_trabajo_mensual c
    WHERE capital_acumulado = (
        SELECT MAX(capital_acumulado)
        FROM t_capital_trabajo_mensual c2
        WHERE c2.industria = c.industria
    );

    UPDATE t_capital_trabajo_mensual SET fecha_calculo = GETDATE();

    PRINT 'Capital de trabajo mensual calculado OK.';

    -- =================================================================
    -- MEJORA 4: DATOS ENRIQUECEDORES
    -- =================================================================
    TRUNCATE TABLE t_enriquecedores_calce;

    -- Margen bruto por industria (ultimos 12 meses)
    INSERT INTO t_enriquecedores_calce (industria, margen_bruto_pct, venta_precio_12m, venta_costo_12m)
    SELECT
        ISNULL(ind.industria, 'Sin clasificar'),
        CASE WHEN SUM(v1.cantidad * v1.precio) > 0
             THEN ROUND((SUM(v1.cantidad * v1.precio) - SUM(v1.cantidad * v1.precio_costo))
                        * 100.0 / SUM(v1.cantidad * v1.precio), 2)
             ELSE 0 END,
        SUM(v1.cantidad * v1.precio),
        SUM(v1.cantidad * v1.precio_costo)
    FROM msgestionC.dbo.ventas1 v1
    JOIN msgestionC.dbo.ventas2 v2
        ON v1.empresa = v2.empresa AND v1.codigo = v2.codigo
       AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
       AND v1.numero = v2.numero AND v1.orden = v2.orden
    JOIN msgestion01art.dbo.articulo a ON v1.articulo = a.codigo
    LEFT JOIN map_subrubro_industria ind ON a.subrubro = ind.subrubro
    WHERE v2.codigo IN (1, 6, 21, 61)
      AND v2.fecha_comprobante >= DATEADD(MONTH, -12, GETDATE())
      AND a.subrubro > 0
    GROUP BY ind.industria;

    -- Concentracion de riesgo: top 3 proveedores por industria
    -- Basado en monto comprometido en pedidos
    ;WITH prov_rank AS (
        SELECT
            ISNULL(industria, 'Sin clasificar') AS industria,
            proveedor AS proveedor_nombre,
            SUM(monto_pedido) AS monto,
            SUM(SUM(monto_pedido)) OVER (PARTITION BY ISNULL(industria, 'Sin clasificar')) AS total_ind,
            ROW_NUMBER() OVER (
                PARTITION BY ISNULL(industria, 'Sin clasificar')
                ORDER BY SUM(monto_pedido) DESC
            ) AS rn
        FROM pedidos_cumplimiento_cache
        WHERE fecha_pedido >= '2025-07-01'
        GROUP BY industria, proveedor
    )
    UPDATE e SET
        top1_proveedor = ISNULL(t1.proveedor_nombre, ''),
        top1_pct = CASE WHEN ISNULL(t1.total_ind, 0) > 0
                        THEN ROUND(ISNULL(t1.monto, 0) * 100.0 / t1.total_ind, 1) ELSE 0 END,
        top3_pct = ISNULL(t3.pct_acum, 0),
        top3_proveedores = ISNULL(t3.nombres, ''),
        nivel_concentracion = CASE
            WHEN ISNULL(t3.pct_acum, 0) >= 70 THEN 'ALTO'
            WHEN ISNULL(t3.pct_acum, 0) >= 50 THEN 'MEDIO'
            ELSE 'BAJO'
        END
    FROM t_enriquecedores_calce e
    OUTER APPLY (
        SELECT TOP 1 proveedor_nombre, monto, total_ind
        FROM prov_rank pr WHERE pr.industria = e.industria AND rn = 1
    ) t1
    OUTER APPLY (
        SELECT
            SUM(monto) * 100.0 / NULLIF(MAX(total_ind), 0) AS pct_acum,
            -- SQL 2012 no tiene STRING_AGG, usamos FOR XML PATH
            STUFF((
                SELECT ', ' + RTRIM(pr2.proveedor_nombre)
                FROM prov_rank pr2
                WHERE pr2.industria = e.industria AND pr2.rn <= 3
                ORDER BY pr2.rn
                FOR XML PATH(''), TYPE
            ).value('.', 'VARCHAR(600)'), 1, 2, '') AS nombres
        FROM prov_rank pr WHERE pr.industria = e.industria AND rn <= 3
    ) t3;

    -- Stock sin movimiento (>90 y >180 dias)
    -- Articulos con stock > 0 pero sin ventas recientes
    UPDATE e SET
        stock_muerto_90d_uds = ISNULL(sm90.uds, 0),
        stock_muerto_90d_costo = ISNULL(sm90.costo, 0),
        stock_muerto_180d_uds = ISNULL(sm180.uds, 0),
        stock_muerto_180d_costo = ISNULL(sm180.costo, 0)
    FROM t_enriquecedores_calce e
    OUTER APPLY (
        SELECT
            COUNT(DISTINCT s.articulo) AS uds,
            SUM(s.stock_actual * a.precio_costo) AS costo
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON s.articulo = a.codigo
        LEFT JOIN map_subrubro_industria ind ON a.subrubro = ind.subrubro
        WHERE s.stock_actual > 0
          AND ISNULL(ind.industria, 'Sin clasificar') = e.industria
          AND NOT EXISTS (
              SELECT 1 FROM msgestionC.dbo.ventas1 v1
              JOIN msgestionC.dbo.ventas2 v2
                  ON v1.empresa = v2.empresa AND v1.codigo = v2.codigo
                 AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
                 AND v1.numero = v2.numero AND v1.orden = v2.orden
              WHERE v1.articulo = s.articulo
                AND v2.codigo IN (1, 6, 21, 61)
                AND v2.fecha_comprobante >= DATEADD(DAY, -90, GETDATE())
          )
    ) sm90
    OUTER APPLY (
        SELECT
            COUNT(DISTINCT s.articulo) AS uds,
            SUM(s.stock_actual * a.precio_costo) AS costo
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON s.articulo = a.codigo
        LEFT JOIN map_subrubro_industria ind ON a.subrubro = ind.subrubro
        WHERE s.stock_actual > 0
          AND ISNULL(ind.industria, 'Sin clasificar') = e.industria
          AND NOT EXISTS (
              SELECT 1 FROM msgestionC.dbo.ventas1 v1
              JOIN msgestionC.dbo.ventas2 v2
                  ON v1.empresa = v2.empresa AND v1.codigo = v2.codigo
                 AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
                 AND v1.numero = v2.numero AND v1.orden = v2.orden
              WHERE v1.articulo = s.articulo
                AND v2.codigo IN (1, 6, 21, 61)
                AND v2.fecha_comprobante >= DATEADD(DAY, -180, GETDATE())
          )
    ) sm180;

    UPDATE t_enriquecedores_calce SET fecha_calculo = GETDATE();

    PRINT 'Datos enriquecedores calculados OK.';
    PRINT '';
    PRINT '=========================================';
    PRINT '  CALCE AVANZADO - 4 mejoras calculadas';
    PRINT '=========================================';

    -- Mostrar resumen
    SELECT 'FLUJO_CAJA' AS mejora, COUNT(*) AS registros FROM t_flujo_caja_semanal
    UNION ALL
    SELECT 'ROI_PROVEEDOR', COUNT(*) FROM t_roi_proveedor
    UNION ALL
    SELECT 'CAPITAL_TRABAJO', COUNT(*) FROM t_capital_trabajo_mensual
    UNION ALL
    SELECT 'ENRIQUECEDORES', COUNT(*) FROM t_enriquecedores_calce;
END;
GO

-- =============================================
-- EJECUTAR
-- =============================================
EXEC sp_calcular_calce_avanzado;
GO

PRINT '';
PRINT '=============================================';
PRINT '  LISTO! Ejecutar deploy.sh para activar.';
PRINT '  Recalcular: EXEC sp_calcular_calce_avanzado';
PRINT '=============================================';
GO
