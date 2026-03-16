-- =============================================================
-- FIX: sp_refrescar_recupero_inversion
-- BUG: Calculaba hitos (d50, d75, etc.) por artículo × factura
--      en vez de por artículo × periodo. Esto subestimaba los
--      días de recupero para proveedores con muchas facturas
--      por artículo (ej: SARANG TONGSANG cosmética).
-- FIX: Agregar paso 2B que consolida compras por artículo ×
--      proveedor × periodo ANTES de calcular hitos.
-- FECHA: 11/mar/2026
-- =============================================================

ALTER PROCEDURE dbo.sp_refrescar_recupero_inversion
    @fecha_desde DATE = '2024-03-01',
    @fecha_hasta DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @inicio DATETIME = GETDATE();
    PRINT 'Inicio: ' + CONVERT(VARCHAR, @inicio, 120);

    IF @fecha_hasta IS NULL SET @fecha_hasta = CAST(GETDATE() AS DATE);

    -- =====================================================
    -- PASO 1: Mapeo industrias
    -- =====================================================
    IF OBJECT_ID('tempdb..#Industria') IS NOT NULL DROP TABLE #Industria;
    CREATE TABLE #Industria (subrubro INT PRIMARY KEY, industria VARCHAR(20));
    INSERT INTO #Industria VALUES
        (1,'Zapatería'),(2,'Zapatería'),(3,'Zapatería'),(4,'Zapatería'),
        (5,'Zapatería'),(6,'Zapatería'),(7,'Zapatería'),(8,'Zapatería'),
        (9,'Zapatería'),(11,'Zapatería'),(12,'Zapatería'),(13,'Zapatería'),
        (14,'Zapatería'),(15,'Zapatería'),(16,'Zapatería'),(17,'Zapatería'),
        (20,'Zapatería'),(21,'Zapatería'),(34,'Zapatería'),(35,'Zapatería'),
        (37,'Zapatería'),(38,'Zapatería'),(40,'Zapatería'),(41,'Zapatería'),
        (42,'Zapatería'),(43,'Zapatería'),(44,'Zapatería'),
        (10,'Deportes'),(19,'Deportes'),(22,'Deportes'),(33,'Deportes'),
        (45,'Deportes'),(47,'Deportes'),(48,'Deportes'),(49,'Deportes'),
        (50,'Deportes'),(51,'Deportes'),(53,'Deportes'),(54,'Deportes'),
        (59,'Deportes'),
        (52,'Mixto_Zap_Dep'),(55,'Mixto_Zap_Dep'),
        (18,'Marroquinería'),(24,'Marroquinería'),(25,'Marroquinería'),
        (26,'Marroquinería'),(30,'Marroquinería'),(31,'Marroquinería'),
        (39,'Marroquinería'),(58,'Marroquinería'),
        (23,'Indumentaria'),(46,'Indumentaria'),(57,'Indumentaria'),
        (61,'Indumentaria'),(62,'Indumentaria'),(63,'Indumentaria'),
        (27,'Cosmética'),(28,'Cosmética'),(29,'Cosmética'),(32,'Cosmética');

    PRINT 'Paso 1 OK - Industrias cargadas';

    -- =====================================================
    -- PASO 2: Compras netas (por artículo × factura)
    -- =====================================================
    IF OBJECT_ID('tempdb..#CompraBase') IS NOT NULL DROP TABLE #CompraBase;
    SELECT
        c2.cuenta                       AS proveedor,
        RTRIM(c2.denominacion)          AS nombre_proveedor,
        c2.fecha_comprobante            AS fecha_compra,
        DATEADD(DAY,
            -((DATEPART(WEEKDAY, c2.fecha_comprobante) + @@DATEFIRST - 2) % 7),
            c2.fecha_comprobante
        )                               AS fecha_foto,
        c1.articulo,
        COALESCE(ind.industria, 'Sin clasificar') AS industria,
        CASE
            WHEN COALESCE(ind.industria,'') IN ('Deportes','Mixto_Zap_Dep') THEN
                CASE WHEN MONTH(c2.fecha_comprobante) BETWEEN 1 AND 6
                     THEN CAST(YEAR(c2.fecha_comprobante) AS VARCHAR)+'-H1'
                     ELSE CAST(YEAR(c2.fecha_comprobante) AS VARCHAR)+'-H2' END
            ELSE
                CASE WHEN MONTH(c2.fecha_comprobante) BETWEEN 3 AND 8
                     THEN CAST(YEAR(c2.fecha_comprobante) AS VARCHAR)+'-OI'
                     WHEN MONTH(c2.fecha_comprobante) >= 9
                     THEN CAST(YEAR(c2.fecha_comprobante) AS VARCHAR)+'-PV'
                     ELSE CAST(YEAR(c2.fecha_comprobante)-1 AS VARCHAR)+'-PV' END
        END                             AS periodo,
        SUM(CASE WHEN c2.codigo=1 THEN c1.cantidad
                 WHEN c2.codigo=3 THEN -c1.cantidad ELSE 0 END) AS qty,
        SUM(CASE WHEN c2.codigo=1 THEN c1.cantidad*c1.precio
                 WHEN c2.codigo=3 THEN -c1.cantidad*c1.precio ELSE 0 END) AS costo
    INTO #CompraBase
    FROM msgestionC.dbo.compras2 c2
    JOIN msgestionC.dbo.compras1 c1
        ON  c1.empresa  = c2.empresa AND c1.codigo = c2.codigo
        AND c1.letra    = c2.letra   AND c1.sucursal = c2.sucursal
        AND c1.numero   = c2.numero  AND c1.orden = c2.orden
    JOIN msgestionC.dbo.articulo a ON c1.articulo = a.codigo
    LEFT JOIN #Industria ind ON a.subrubro = ind.subrubro
    WHERE c2.fecha_comprobante >= @fecha_desde
      AND c2.fecha_comprobante <  @fecha_hasta
      AND c2.codigo IN (1, 3)
      AND c1.cantidad > 0
      AND a.subrubro IS NOT NULL AND a.subrubro > 0
      AND COALESCE(ind.industria, 'Sin clasificar') <> 'Sin clasificar'
    GROUP BY
        c2.cuenta, RTRIM(c2.denominacion), c2.fecha_comprobante,
        DATEADD(DAY, -((DATEPART(WEEKDAY, c2.fecha_comprobante)+@@DATEFIRST-2)%7), c2.fecha_comprobante),
        c1.articulo, COALESCE(ind.industria,'Sin clasificar'),
        CASE
            WHEN COALESCE(ind.industria,'') IN ('Deportes','Mixto_Zap_Dep') THEN
                CASE WHEN MONTH(c2.fecha_comprobante) BETWEEN 1 AND 6
                     THEN CAST(YEAR(c2.fecha_comprobante) AS VARCHAR)+'-H1'
                     ELSE CAST(YEAR(c2.fecha_comprobante) AS VARCHAR)+'-H2' END
            ELSE
                CASE WHEN MONTH(c2.fecha_comprobante) BETWEEN 3 AND 8
                     THEN CAST(YEAR(c2.fecha_comprobante) AS VARCHAR)+'-OI'
                     WHEN MONTH(c2.fecha_comprobante) >= 9
                     THEN CAST(YEAR(c2.fecha_comprobante) AS VARCHAR)+'-PV'
                     ELSE CAST(YEAR(c2.fecha_comprobante)-1 AS VARCHAR)+'-PV' END END
    HAVING SUM(CASE WHEN c2.codigo=1 THEN c1.cantidad
                    WHEN c2.codigo=3 THEN -c1.cantidad ELSE 0 END) > 0;

    PRINT 'Paso 2 OK - Compras detalle: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' filas - '
          + CAST(DATEDIFF(SECOND, @inicio, GETDATE()) AS VARCHAR) + 's';

    -- =====================================================
    -- PASO 2B (NUEVO): Consolidar por artículo × proveedor × periodo
    -- Este es el fix principal. En vez de calcular hitos por
    -- factura individual, consolidamos todo el artículo en la
    -- temporada para que d50 = 50% del TOTAL comprado.
    -- =====================================================
    IF OBJECT_ID('tempdb..#CompraConsolidada') IS NOT NULL DROP TABLE #CompraConsolidada;
    SELECT
        proveedor,
        nombre_proveedor,
        industria,
        periodo,
        articulo,
        MIN(fecha_compra) AS fecha_compra,       -- primera compra del artículo en la temporada
        MIN(fecha_foto)   AS fecha_foto,          -- foto semanal de la primera compra
        SUM(qty)          AS qty,                 -- TOTAL comprado en toda la temporada
        SUM(costo)        AS costo                -- TOTAL costo en toda la temporada
    INTO #CompraConsolidada
    FROM #CompraBase
    GROUP BY proveedor, nombre_proveedor, industria, periodo, articulo;

    CREATE INDEX IX_cc_art ON #CompraConsolidada (articulo);
    CREATE INDEX IX_cc_prov ON #CompraConsolidada (proveedor, periodo);

    PRINT 'Paso 2B OK - Compras consolidadas: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' filas - '
          + CAST(DATEDIFF(SECOND, @inicio, GETDATE()) AS VARCHAR) + 's';

    -- =====================================================
    -- PASO 3: Stock previo (foto semanal)
    -- =====================================================
    IF OBJECT_ID('tempdb..#StockFoto') IS NOT NULL DROP TABLE #StockFoto;
    SELECT sh.codigo AS articulo, sh.fecha AS fecha_foto, sh.stock AS sp
    INTO #StockFoto
    FROM omicronvt.dbo.stock_historico_semanal sh
    WHERE sh.codigo IN (SELECT DISTINCT articulo FROM #CompraConsolidada);

    CREATE INDEX IX_sf ON #StockFoto (articulo, fecha_foto);

    PRINT 'Paso 3 OK - Stock foto: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' filas - '
          + CAST(DATEDIFF(SECOND, @inicio, GETDATE()) AS VARCHAR) + 's';

    -- =====================================================
    -- PASO 4: Ventas acumuladas
    -- =====================================================
    IF OBJECT_ID('tempdb..#VentasDiarias') IS NOT NULL DROP TABLE #VentasDiarias;
    SELECT v.articulo, v.fecha, SUM(v.cantidad) AS qv
    INTO #VentasDiarias
    FROM msgestionC.dbo.ventas1 v
    WHERE v.articulo IN (SELECT DISTINCT articulo FROM #CompraConsolidada)
      AND v.fecha >= @fecha_desde AND v.cantidad > 0
    GROUP BY v.articulo, v.fecha;

    CREATE INDEX IX_vd ON #VentasDiarias (articulo, fecha);

    IF OBJECT_ID('tempdb..#VentasAcum') IS NOT NULL DROP TABLE #VentasAcum;
    SELECT articulo, fecha,
        SUM(qv) OVER (PARTITION BY articulo ORDER BY fecha ROWS UNBOUNDED PRECEDING) AS acum
    INTO #VentasAcum
    FROM #VentasDiarias;

    CREATE INDEX IX_va ON #VentasAcum (articulo, fecha);

    PRINT 'Paso 4 OK - Ventas acum: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' filas - '
          + CAST(DATEDIFF(SECOND, @inicio, GETDATE()) AS VARCHAR) + 's';

    -- =====================================================
    -- PASO 5: Hitos de recupero
    -- FIX: Ahora usa #CompraConsolidada (1 fila por artículo
    --      × periodo) en vez de #CompraBase (1 fila por factura).
    --      Así d50 = días para vender 50% del TOTAL de la temporada.
    -- =====================================================
    IF OBJECT_ID('tempdb..#Hitos') IS NOT NULL DROP TABLE #Hitos;
    SELECT
        c.proveedor, c.nombre_proveedor, c.industria, c.periodo,
        c.articulo, c.fecha_compra, c.qty, c.costo,
        ISNULL(sf.sp, 0) AS sp,
        DATEDIFF(DAY, c.fecha_compra, GETDATE()) AS dias_vida,
        DATEDIFF(DAY, c.fecha_compra,
            MIN(CASE WHEN va.acum > ISNULL(sf.sp,0) THEN va.fecha END)) AS d1ra,
        DATEDIFF(DAY, c.fecha_compra,
            MIN(CASE WHEN va.acum >= ISNULL(sf.sp,0)+0.50*c.qty THEN va.fecha END)) AS d50,
        DATEDIFF(DAY, c.fecha_compra,
            MIN(CASE WHEN va.acum >= ISNULL(sf.sp,0)+0.75*c.qty THEN va.fecha END)) AS d75,
        DATEDIFF(DAY, c.fecha_compra,
            MIN(CASE WHEN va.acum >= ISNULL(sf.sp,0)+0.90*c.qty THEN va.fecha END)) AS d90,
        DATEDIFF(DAY, c.fecha_compra,
            MIN(CASE WHEN va.acum >= ISNULL(sf.sp,0)+1.00*c.qty THEN va.fecha END)) AS d100,
        CASE
            WHEN ISNULL(MAX(va.acum),0) <= ISNULL(sf.sp,0) THEN 0.0
            WHEN ISNULL(MAX(va.acum),0) >= ISNULL(sf.sp,0)+c.qty THEN 100.0
            ELSE ROUND(100.0*(ISNULL(MAX(va.acum),0)-ISNULL(sf.sp,0))/c.qty, 1)
        END AS pct
    INTO #Hitos
    FROM #CompraConsolidada c  -- <<< CAMBIO: era #CompraBase
    LEFT JOIN #StockFoto sf ON sf.articulo = c.articulo AND sf.fecha_foto = c.fecha_foto
    LEFT JOIN #VentasAcum va ON va.articulo = c.articulo AND va.fecha >= c.fecha_compra
    GROUP BY c.proveedor, c.nombre_proveedor, c.industria, c.periodo,
             c.articulo, c.fecha_compra, c.qty, c.costo, sf.sp;

    PRINT 'Paso 5 OK - Hitos: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' filas - '
          + CAST(DATEDIFF(SECOND, @inicio, GETDATE()) AS VARCHAR) + 's';

    -- =====================================================
    -- PASO 6: Plazos de pago  *** CORREGIDO 26/feb/2026 ***
    -- =====================================================
    IF OBJECT_ID('tempdb..#Pagos') IS NOT NULL DROP TABLE #Pagos;
    SELECT
        c2.cuenta AS proveedor,
        CASE WHEN MONTH(p.fecha_factura) BETWEEN 1 AND 6
             THEN CAST(YEAR(p.fecha_factura) AS VARCHAR)+'-H1'
             ELSE CAST(YEAR(p.fecha_factura) AS VARCHAR)+'-H2'
        END AS semestre,
        COUNT(DISTINCT CAST(p.empresa AS VARCHAR)+'-'+CAST(p.sucursal AS VARCHAR)+'-'+CAST(p.numero AS VARCHAR)) AS cant_facturas,
        ROUND(AVG(DATEDIFF(DAY, p.fecha_factura, p.fecha_vencimiento)*1.0), 0) AS plazo_credito,
        ROUND(
            SUM(CASE WHEN p.fecha_registro_pago > '2000-01-01'
                     THEN p.plazo_impacto_real_dias * p.monto_pago END) * 1.0
            / NULLIF(SUM(CASE WHEN p.fecha_registro_pago > '2000-01-01'
                              THEN p.monto_pago END), 0)
        , 0) AS plazo_pago_real
    INTO #Pagos
    FROM omicronvt.dbo.compras2_pagos1_plazos p
    JOIN msgestionC.dbo.compras2 c2
        ON  RTRIM(p.proveedor) = RTRIM(c2.denominacion)
        AND p.empresa = c2.empresa AND p.letra = c2.letra
        AND p.sucursal = c2.sucursal AND p.numero = c2.numero
    WHERE p.fecha_factura >= @fecha_desde
    GROUP BY c2.cuenta,
        CASE WHEN MONTH(p.fecha_factura) BETWEEN 1 AND 6
             THEN CAST(YEAR(p.fecha_factura) AS VARCHAR)+'-H1'
             ELSE CAST(YEAR(p.fecha_factura) AS VARCHAR)+'-H2' END;

    PRINT 'Paso 6 OK - Pagos: ' + CAST(@@ROWCOUNT AS VARCHAR) + ' filas - '
          + CAST(DATEDIFF(SECOND, @inicio, GETDATE()) AS VARCHAR) + 's';

    -- =====================================================
    -- PASO 7: Agregar y cargar tabla final
    -- =====================================================
    TRUNCATE TABLE dbo.t_recupero_inversion;

    INSERT INTO dbo.t_recupero_inversion (
        proveedor_id, proveedor_nombre, industria, periodo, anio, temporada_tipo,
        cant_articulos, total_unidades, total_costo_compra,
        dias_1ra_venta, dias_50, dias_75, dias_90, dias_100,
        plazo_recupero_proy, pct_vendido, estado,
        primera_compra, ultima_compra,
        cant_facturas_pago, plazo_credito_prom, plazo_pago_real_prom,
        brecha_pago_vs_rec50, brecha_pago_vs_rec75, brecha_pago_vs_rec100,
        pct_vendido_al_pago, costo_inmovilizado_dia
    )
    SELECT
        h.proveedor,
        h.nombre_proveedor,
        h.industria,
        h.periodo,
        CAST(LEFT(h.periodo, 4) AS INT),
        RIGHT(h.periodo, 2),

        COUNT(DISTINCT h.articulo),
        SUM(h.qty),
        ROUND(SUM(h.costo), 0),

        -- Hitos ponderados por costo
        ROUND(SUM(CASE WHEN h.d1ra>=0 THEN h.d1ra*h.costo END)*1.0
            / NULLIF(SUM(CASE WHEN h.d1ra>=0 THEN h.costo END),0), 0),
        ROUND(SUM(CASE WHEN h.d50>=0 THEN h.d50*h.costo END)*1.0
            / NULLIF(SUM(CASE WHEN h.d50>=0 THEN h.costo END),0), 0),
        ROUND(SUM(CASE WHEN h.d75>=0 THEN h.d75*h.costo END)*1.0
            / NULLIF(SUM(CASE WHEN h.d75>=0 THEN h.costo END),0), 0),
        ROUND(SUM(CASE WHEN h.d90>=0 THEN h.d90*h.costo END)*1.0
            / NULLIF(SUM(CASE WHEN h.d90>=0 THEN h.costo END),0), 0),
        ROUND(SUM(CASE WHEN h.d100>=0 THEN h.d100*h.costo END)*1.0
            / NULLIF(SUM(CASE WHEN h.d100>=0 THEN h.costo END),0), 0),

        -- Plazo recupero proyectado
        ROUND(SUM(
            CASE
                WHEN h.pct >= 100 AND h.d100 >= 0 THEN h.d100 * h.costo
                WHEN h.pct > 0 THEN (h.dias_vida / (h.pct / 100.0)) * h.costo
                ELSE h.dias_vida * 2.0 * h.costo
            END) * 1.0 / NULLIF(SUM(h.costo), 0), 0),

        ROUND(SUM(h.pct * h.costo) / NULLIF(SUM(h.costo),0), 1),
        CASE WHEN SUM(h.pct*h.costo)/NULLIF(SUM(h.costo),0) >= 90
             THEN 'CERRADA' ELSE 'EN CURSO' END,

        MIN(h.fecha_compra),
        MAX(h.fecha_compra),

        -- Pagos
        MAX(pg.cant_facturas),
        MAX(pg.plazo_credito),
        MAX(pg.plazo_pago_real),

        -- Brechas
        MAX(pg.plazo_pago_real) - ROUND(SUM(CASE WHEN h.d50>=0 THEN h.d50*h.costo END)*1.0
            / NULLIF(SUM(CASE WHEN h.d50>=0 THEN h.costo END),0), 0),
        MAX(pg.plazo_pago_real) - ROUND(SUM(CASE WHEN h.d75>=0 THEN h.d75*h.costo END)*1.0
            / NULLIF(SUM(CASE WHEN h.d75>=0 THEN h.costo END),0), 0),
        MAX(pg.plazo_pago_real) - ROUND(SUM(
            CASE
                WHEN h.pct >= 100 AND h.d100 >= 0 THEN h.d100*h.costo
                WHEN h.pct > 0 THEN (h.dias_vida/(h.pct/100.0))*h.costo
                ELSE h.dias_vida*2.0*h.costo
            END)*1.0 / NULLIF(SUM(h.costo),0), 0),

        -- % vendido al pago
        CASE
            WHEN MAX(pg.plazo_pago_real) IS NULL THEN NULL
            WHEN ROUND(SUM(CASE WHEN h.d1ra>=0 THEN h.d1ra*h.costo END)*1.0
                / NULLIF(SUM(CASE WHEN h.d1ra>=0 THEN h.costo END),0), 0)
                > MAX(pg.plazo_pago_real) THEN 0
            WHEN ROUND(SUM(CASE WHEN h.d50>=0 THEN h.d50*h.costo END)*1.0
                / NULLIF(SUM(CASE WHEN h.d50>=0 THEN h.costo END),0), 0)
                >= MAX(pg.plazo_pago_real)
                THEN ROUND(50.0 * MAX(pg.plazo_pago_real)
                    / NULLIF(ROUND(SUM(CASE WHEN h.d50>=0 THEN h.d50*h.costo END)*1.0
                        / NULLIF(SUM(CASE WHEN h.d50>=0 THEN h.costo END),0), 0), 0), 1)
            WHEN ROUND(SUM(CASE WHEN h.d100>=0 THEN h.d100*h.costo END)*1.0
                / NULLIF(SUM(CASE WHEN h.d100>=0 THEN h.costo END),0), 0)
                <= MAX(pg.plazo_pago_real) THEN 100
            ELSE ROUND(SUM(h.pct*h.costo)/NULLIF(SUM(h.costo),0), 1)
        END,

        -- Costo inmovilizado x dia
        CASE
            WHEN MAX(pg.plazo_pago_real) IS NULL THEN NULL
            ELSE ROUND(
                SUM(h.costo)
                * (1.0 - ISNULL(SUM(h.pct*h.costo)/NULLIF(SUM(h.costo),0)/100.0, 0))
                * ABS(MAX(pg.plazo_pago_real) - ROUND(SUM(
                    CASE
                        WHEN h.pct >= 100 AND h.d100 >= 0 THEN h.d100*h.costo
                        WHEN h.pct > 0 THEN (h.dias_vida/(h.pct/100.0))*h.costo
                        ELSE h.dias_vida*2.0*h.costo
                    END)*1.0 / NULLIF(SUM(h.costo),0), 0))
            , 0)
        END

    FROM #Hitos h
    LEFT JOIN #Pagos pg
        ON  pg.proveedor = h.proveedor
        AND pg.semestre = CAST(LEFT(h.periodo,4) AS VARCHAR)
            + '-' + CASE WHEN MONTH(h.fecha_compra) BETWEEN 1 AND 6 THEN 'H1' ELSE 'H2' END
    GROUP BY h.proveedor, h.nombre_proveedor, h.industria, h.periodo;

    DECLARE @filas INT = @@ROWCOUNT;

    -- Cleanup
    DROP TABLE #Industria, #CompraBase, #CompraConsolidada, #StockFoto, #VentasDiarias, #VentasAcum, #Hitos, #Pagos;

    PRINT '========================================';
    PRINT 'COMPLETADO: ' + CAST(@filas AS VARCHAR) + ' filas insertadas';
    PRINT 'Tiempo total: ' + CAST(DATEDIFF(SECOND, @inicio, GETDATE()) AS VARCHAR) + ' segundos';
    PRINT '========================================';
END;
