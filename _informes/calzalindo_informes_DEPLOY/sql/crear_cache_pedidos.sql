-- ============================================================
-- EJECUTAR EN: 192.168.2.111 (servidor web2py / produccion)
-- BASE: omicronvt
-- ============================================================
USE omicronvt;
GO

-- 1. Crear tabla cache (estructura identica a la vista)
SELECT TOP 0 *
INTO dbo.pedidos_cumplimiento_cache
FROM dbo.v_pedidos_cumplimiento;
GO

-- 2. Poblar con datos actuales
INSERT INTO dbo.pedidos_cumplimiento_cache
SELECT * FROM dbo.v_pedidos_cumplimiento;
GO

-- 3. Indices para acelerar queries
CREATE NONCLUSTERED INDEX IX_cache_proveedor
    ON dbo.pedidos_cumplimiento_cache (cod_proveedor, proveedor);

CREATE NONCLUSTERED INDEX IX_cache_estado
    ON dbo.pedidos_cumplimiento_cache (estado_cumplimiento);

CREATE NONCLUSTERED INDEX IX_cache_alerta
    ON dbo.pedidos_cumplimiento_cache (alerta_vencimiento)
    INCLUDE (proveedor, articulo, cant_pedida, cant_pendiente, monto_pendiente);
GO

-- 4. SP para refrescar la cache (lo llama el boton "Actualizar datos")
CREATE PROCEDURE dbo.sp_sync_pedidos
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        TRUNCATE TABLE dbo.pedidos_cumplimiento_cache;

        INSERT INTO dbo.pedidos_cumplimiento_cache
        SELECT * FROM dbo.v_pedidos_cumplimiento;

        SELECT @@ROWCOUNT AS filas_actualizadas;
    END TRY
    BEGIN CATCH
        DECLARE @msg NVARCHAR(4000) = ERROR_MESSAGE();
        RAISERROR(@msg, 16, 1);
    END CATCH
END;
GO

PRINT 'OK - Tabla cache creada, datos cargados, SP listo.';
GO
