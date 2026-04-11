-- =====================================================================
-- verificar_movistoc_compartidas.sql
-- Propósito: Determinar si las tablas movistoc1 / movistoc2 (movimientos
--            de stock inter-depósito) son COMPARTIDAS entre msgestion01
--            y msgestion03 (como pedico1/pedico2) o son SEPARADAS por
--            base (como ventas1, compras1, etc.).
-- Fecha:     11-abr-2026
-- Autor:     Claude (vibrant-goldwasser worktree)
--
-- INTERPRETACIÓN DE RESULTADOS:
--   - Si COUNT(*) últ 60 días Y MAX(numero) Y las 5 filas sample COINCIDEN
--     en msgestion01.dbo.movistoc2 vs msgestion03.dbo.movistoc2 → COMPARTIDAS.
--     (el INSERT se refleja en ambas bases porque es físicamente la misma tabla,
--      igual que pedico1/pedico2).
--   - Si los conteos o el MAX(numero) DIFIEREN → SEPARADAS por base.
--     (cada empresa mantiene sus propios movimientos, el routing debe
--      resolverse por proveedor/empresa al momento de insertar).
--
-- IMPLICANCIA para AUTOREPO:
--   - Si son COMPARTIDAS: al insertar la transferencia, basta un solo INSERT
--     en cualquier base (el campo empresa/sucursal diferencia).
--   - Si son SEPARADAS: hay que decidir en qué base insertar según emisor/receptor.
--
-- Cómo ejecutar (desde servidor 111 producción):
--   sqlcmd -S 192.168.2.111 -U am -P dl -i verificar_movistoc_compartidas.sql
-- o desde SSMS sobre msgestionC.
--
-- SQL Server 2012 RTM: NO TRY_CAST. Usar ISNUMERIC + CAST si se requiere.
-- =====================================================================

SET NOCOUNT ON;

PRINT '============================================================';
PRINT 'DIAG 1: Conteo de filas últimos 60 días en movistoc2';
PRINT '============================================================';

SELECT
    'msgestion01.dbo.movistoc2' AS tabla,
    COUNT(*)                    AS filas_60d,
    MIN(fecha)                  AS fecha_min,
    MAX(fecha)                  AS fecha_max,
    MAX(numero)                 AS max_numero
FROM msgestion01.dbo.movistoc2
WHERE fecha >= DATEADD(day, -60, GETDATE())

UNION ALL

SELECT
    'msgestion03.dbo.movistoc2' AS tabla,
    COUNT(*)                    AS filas_60d,
    MIN(fecha)                  AS fecha_min,
    MAX(fecha)                  AS fecha_max,
    MAX(numero)                 AS max_numero
FROM msgestion03.dbo.movistoc2
WHERE fecha >= DATEADD(day, -60, GETDATE());

PRINT '';
PRINT '============================================================';
PRINT 'DIAG 2: Conteo total histórico y MAX(numero) global';
PRINT '============================================================';

SELECT
    'msgestion01.dbo.movistoc2' AS tabla,
    COUNT(*)                    AS filas_total,
    MAX(numero)                 AS max_numero_global
FROM msgestion01.dbo.movistoc2

UNION ALL

SELECT
    'msgestion03.dbo.movistoc2' AS tabla,
    COUNT(*)                    AS filas_total,
    MAX(numero)                 AS max_numero_global
FROM msgestion03.dbo.movistoc2;

PRINT '';
PRINT '============================================================';
PRINT 'DIAG 3: Sample 5 últimos registros de cada base';
PRINT '============================================================';

PRINT '-- msgestion01.dbo.movistoc2 (TOP 5 desc) --';
SELECT TOP 5
    numero,
    sucursal,
    fecha,
    deposito,
    deposito_destino,
    codigo,
    letra,
    estado,
    usuario
FROM msgestion01.dbo.movistoc2
ORDER BY numero DESC;

PRINT '-- msgestion03.dbo.movistoc2 (TOP 5 desc) --';
SELECT TOP 5
    numero,
    sucursal,
    fecha,
    deposito,
    deposito_destino,
    codigo,
    letra,
    estado,
    usuario
FROM msgestion03.dbo.movistoc2
ORDER BY numero DESC;

PRINT '';
PRINT '============================================================';
PRINT 'DIAG 4: Conteo + MAX en movistoc1 (detalle)';
PRINT '============================================================';

SELECT
    'msgestion01.dbo.movistoc1' AS tabla,
    COUNT(*)                    AS filas_total,
    MAX(numero)                 AS max_numero
FROM msgestion01.dbo.movistoc1

UNION ALL

SELECT
    'msgestion03.dbo.movistoc1' AS tabla,
    COUNT(*)                    AS filas_total,
    MAX(numero)                 AS max_numero
FROM msgestion03.dbo.movistoc1;

PRINT '';
PRINT '============================================================';
PRINT 'DIAG 5: Diferencia simétrica - buscar renglones que están en una';
PRINT '         base pero no en la otra (misma clave numero+sucursal)';
PRINT '============================================================';

-- Cuenta cuántos (numero, sucursal) del último mes existen en una base
-- y no en la otra. Si son compartidas, ambos conteos = 0.
SELECT
    'en 01 pero no en 03' AS diferencia,
    COUNT(*)              AS cantidad
FROM msgestion01.dbo.movistoc2 a
LEFT JOIN msgestion03.dbo.movistoc2 b
    ON a.numero = b.numero
   AND a.sucursal = b.sucursal
   AND a.codigo = b.codigo
   AND a.letra = b.letra
WHERE a.fecha >= DATEADD(day, -30, GETDATE())
  AND b.numero IS NULL

UNION ALL

SELECT
    'en 03 pero no en 01' AS diferencia,
    COUNT(*)              AS cantidad
FROM msgestion03.dbo.movistoc2 a
LEFT JOIN msgestion01.dbo.movistoc2 b
    ON a.numero = b.numero
   AND a.sucursal = b.sucursal
   AND a.codigo = b.codigo
   AND a.letra = b.letra
WHERE a.fecha >= DATEADD(day, -30, GETDATE())
  AND b.numero IS NULL;

PRINT '';
PRINT '============================================================';
PRINT 'FIN - Interpretación:';
PRINT '  - Si DIAG 5 devuelve 0 en ambas filas Y DIAG 1/2 coinciden';
PRINT '    → movistoc1/2 son COMPARTIDAS (igual que pedico1/2).';
PRINT '  - Si hay diferencias → son SEPARADAS por base.';
PRINT '============================================================';
