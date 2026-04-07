-- ============================================================
-- FIX: Consolidar stock de series no-vacias a serie=' '
-- Base: msgestion01 (CALZALINDO)
-- Fecha: 2026-04-02
--
-- Problema: remitos ingresaron stock en serie YYMM (ej '2603')
-- pero ventas/POS descuentan de serie=' '. Resultado: stock
-- "invisible" en series YYMM y negativos en serie blanco.
--
-- Este script:
--   1. Suma stock de series <> ' ' a la fila serie=' '
--   2. Pone en 0 las filas de series <> ' '
--   3. NO borra filas (el ERP puede necesitarlas)
--   4. Corre todo en transaccion con ROLLBACK si algo falla
--
-- EJECUTAR EN: 192.168.2.111, base msgestion01
-- ============================================================

USE msgestion01
GO

BEGIN TRANSACTION

-- ============================================================
-- PASO 1: Preview - ver que se va a tocar
-- ============================================================
PRINT '=== PREVIEW: filas con serie <> espacio y stock <> 0 ==='

SELECT s.articulo, s.deposito, s.serie, s.stock_actual, s.stock_unidades,
       ISNULL(sb.stock_actual, 0) AS stock_blanco_antes,
       ISNULL(sb.stock_actual, 0) + s.stock_actual AS stock_blanco_despues,
       CASE WHEN sb.articulo IS NULL THEN 'NO EXISTE - CREAR' ELSE 'EXISTE - SUMAR' END AS accion
FROM dbo.stock s
LEFT JOIN dbo.stock sb ON sb.articulo = s.articulo
                       AND sb.deposito = s.deposito
                       AND sb.serie = ' '
WHERE s.serie <> ' ' AND s.stock_actual <> 0
ORDER BY ABS(s.stock_actual) DESC

PRINT ''
PRINT '=== Total filas a consolidar: ==='
SELECT COUNT(*) AS filas, SUM(stock_actual) AS unidades_total
FROM dbo.stock WHERE serie <> ' ' AND stock_actual <> 0

-- ============================================================
-- PASO 2A: Crear filas serie=' ' donde no existen
-- (para articulos que SOLO tienen stock en serie YYMM)
-- ============================================================
PRINT ''
PRINT '=== PASO 2A: Creando filas serie=espacio faltantes ==='

INSERT INTO dbo.stock (deposito, articulo, serie, stock_actual, stock_unidades)
SELECT s.deposito, s.articulo, ' ', 0, 0
FROM dbo.stock s
WHERE s.serie <> ' ' AND s.stock_actual <> 0
AND NOT EXISTS (
    SELECT 1 FROM dbo.stock sb
    WHERE sb.articulo = s.articulo
      AND sb.deposito = s.deposito
      AND sb.serie = ' '
)
GROUP BY s.deposito, s.articulo

PRINT 'Filas serie=espacio creadas: ' + CAST(@@ROWCOUNT AS VARCHAR)

-- ============================================================
-- PASO 2B: Sumar stock de series <> ' ' a serie=' '
-- ============================================================
PRINT ''
PRINT '=== PASO 2B: Sumando stock a serie=espacio ==='

UPDATE sb
SET sb.stock_actual = sb.stock_actual + totales.suma_stock,
    sb.stock_unidades = sb.stock_unidades + totales.suma_unidades
FROM dbo.stock sb
JOIN (
    SELECT articulo, deposito,
           SUM(stock_actual) AS suma_stock,
           SUM(stock_unidades) AS suma_unidades
    FROM dbo.stock
    WHERE serie <> ' ' AND stock_actual <> 0
    GROUP BY articulo, deposito
) totales ON totales.articulo = sb.articulo
          AND totales.deposito = sb.deposito
WHERE sb.serie = ' '

PRINT 'Filas serie=espacio actualizadas: ' + CAST(@@ROWCOUNT AS VARCHAR)

-- ============================================================
-- PASO 2C: Poner en 0 las filas de series no vacias
-- ============================================================
PRINT ''
PRINT '=== PASO 2C: Poniendo en 0 filas de series no-vacias ==='

UPDATE dbo.stock
SET stock_actual = 0, stock_unidades = 0
WHERE serie <> ' ' AND stock_actual <> 0

PRINT 'Filas serie<>espacio puestas en 0: ' + CAST(@@ROWCOUNT AS VARCHAR)

-- ============================================================
-- PASO 3: Verificacion post-fix
-- ============================================================
PRINT ''
PRINT '=== VERIFICACION: articulos clave post-fix ==='

-- GO DANCE
SELECT 'GO DANCE' AS grupo, articulo, deposito, serie, stock_actual
FROM dbo.stock
WHERE articulo BETWEEN 360093 AND 360102
ORDER BY articulo, deposito, serie

-- PANTUFLON
SELECT 'PANTUFLON' AS grupo, articulo, deposito, serie, stock_actual
FROM dbo.stock
WHERE articulo BETWEEN 360141 AND 360160
ORDER BY articulo, deposito, serie

-- Verificar que no queden series con stock
PRINT ''
PRINT '=== Filas con serie <> espacio y stock <> 0 (debe ser 0): ==='
SELECT COUNT(*) AS filas_restantes
FROM dbo.stock WHERE serie <> ' ' AND stock_actual <> 0

-- ============================================================
-- PASO 4: COMMIT o ROLLBACK
-- ============================================================
-- Revisar los resultados arriba. Si todo bien:
-- COMMIT
-- Si algo esta mal:
-- ROLLBACK

PRINT ''
PRINT '=== REVISAR RESULTADOS Y EJECUTAR COMMIT O ROLLBACK ==='
