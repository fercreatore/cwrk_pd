-- fix_t_articulos_last_audit.sql
-- Agrega columnas faltantes a t_articulos_last_audit (omicronvt, servidor 111)
-- La tabla tiene 53,347 filas con datos de ultima auditoria por articulo+deposito
-- pero NO tiene el resultado (cantidad_diferencia) que viene de Stock_Auditorias_Movims (112)
--
-- Ejecutar en: 192.168.2.111 / omicronvt
-- SQL Server 2012 RTM (NO usar TRY_CAST)
-- Fecha: 2026-04-03

USE omicronvt;
GO

-- 1. Agregar cantidad_diferencia: resultado numerico de la auditoria
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.t_articulos_last_audit')
      AND name = 'cantidad_diferencia'
)
BEGIN
    ALTER TABLE dbo.t_articulos_last_audit ADD cantidad_diferencia INT NULL;
    PRINT 'Columna cantidad_diferencia agregada.';
END
ELSE
    PRINT 'Columna cantidad_diferencia ya existe.';
GO

-- 2. Agregar resultado_auditoria: OK, DIFERENCIA, PENDIENTE
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.t_articulos_last_audit')
      AND name = 'resultado_auditoria'
)
BEGIN
    ALTER TABLE dbo.t_articulos_last_audit ADD resultado_auditoria VARCHAR(20) NULL;
    PRINT 'Columna resultado_auditoria agregada.';
END
ELSE
    PRINT 'Columna resultado_auditoria ya existe.';
GO

-- 3. Agregar deposito_auditado: el deposito especifico (no el macro)
IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.t_articulos_last_audit')
      AND name = 'deposito_auditado'
)
BEGIN
    ALTER TABLE dbo.t_articulos_last_audit ADD deposito_auditado INT NULL;
    PRINT 'Columna deposito_auditado agregada.';
END
ELSE
    PRINT 'Columna deposito_auditado ya existe.';
GO

-- 4. Indices para busqueda rapida
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.t_articulos_last_audit')
      AND name = 'IX_last_audit_fecha'
)
BEGIN
    CREATE INDEX IX_last_audit_fecha
        ON dbo.t_articulos_last_audit (fecha DESC);
    PRINT 'Indice IX_last_audit_fecha creado.';
END
ELSE
    PRINT 'Indice IX_last_audit_fecha ya existe.';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.t_articulos_last_audit')
      AND name = 'IX_last_audit_resultado'
)
BEGIN
    CREATE INDEX IX_last_audit_resultado
        ON dbo.t_articulos_last_audit (resultado_auditoria);
    PRINT 'Indice IX_last_audit_resultado creado.';
END
ELSE
    PRINT 'Indice IX_last_audit_resultado ya existe.';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.t_articulos_last_audit')
      AND name = 'IX_last_audit_codigo_depo'
)
BEGIN
    CREATE INDEX IX_last_audit_codigo_depo
        ON dbo.t_articulos_last_audit (codigo, depo_macro);
    PRINT 'Indice IX_last_audit_codigo_depo creado.';
END
ELSE
    PRINT 'Indice IX_last_audit_codigo_depo ya existe.';
GO

PRINT '== fix_t_articulos_last_audit.sql completado ==';
GO
