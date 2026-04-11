-- =====================================================================
-- crear_tablas_autorepo.sql
-- Propósito: Crear tablas para el sistema AUTOREPO (reposición
--            automática inter-sucursal). Cabecera + detalle de propuestas.
-- Fecha:     11-abr-2026
-- Autor:     Claude (vibrant-goldwasser worktree)
--
-- Tablas creadas (en omicronvt.dbo):
--   - autorepo_propuestas      (cabecera de corridas)
--   - autorepo_propuestas_det  (detalle artículo × cantidad)
--
-- Cómo ejecutar (desde servidor 111 producción):
--   sqlcmd -S 192.168.2.111 -U am -P dl -i crear_tablas_autorepo.sql
-- o desde SSMS conectado a msgestionC/omicronvt.
--
-- SQL Server 2012 RTM: NO usar TRY_CAST.
-- IDEMPOTENTE: usa IF NOT EXISTS, seguro re-ejecutar.
-- =====================================================================

USE omicronvt;
GO

-- ---------------------------------------------------------------------
-- Tabla 1: Cabecera de propuestas de reposición
-- ---------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'autorepo_propuestas')
BEGIN
    CREATE TABLE omicronvt.dbo.autorepo_propuestas (
        id                    INT IDENTITY(1,1) PRIMARY KEY,
        fecha_corrida         DATETIME       NOT NULL DEFAULT GETDATE(),
        tipo                  VARCHAR(20)    NOT NULL,             -- 'URGENTE' | 'REBALANCEO'
        base_destino          VARCHAR(15)    NULL,                 -- MSGESTION01 | MSGESTION03 | NULL
        deposito_emisor       INT            NOT NULL,
        deposito_receptor     INT            NOT NULL,
        estado                VARCHAR(15)    NOT NULL DEFAULT 'PENDIENTE', -- PENDIENTE|APROBADA|EJECUTADA|RECHAZADA|CANCELADA
        total_pares           INT            NOT NULL,
        total_costo_cer       DECIMAL(18,2)  NOT NULL,
        score_promedio        DECIMAL(5,2)   NULL,
        beneficio_esperado    DECIMAL(18,2)  NULL,
        costo_transferencia   DECIMAL(18,2)  NULL,
        motivo_rechazo        VARCHAR(255)   NULL,
        movistoc_numero       INT            NULL,
        movistoc_sucursal     INT            NULL,
        usuario_aprobador     VARCHAR(30)    NULL,
        fecha_aprobacion      DATETIME       NULL
    );

    CREATE INDEX idx_autorepo_estado_fecha
        ON omicronvt.dbo.autorepo_propuestas(estado, fecha_corrida DESC);

    CREATE INDEX idx_autorepo_deps
        ON omicronvt.dbo.autorepo_propuestas(deposito_emisor, deposito_receptor);

    PRINT 'Tabla autorepo_propuestas creada con 2 índices.';
END
ELSE
BEGIN
    PRINT 'Tabla autorepo_propuestas ya existe. Omitido.';
END
GO

-- ---------------------------------------------------------------------
-- Tabla 2: Detalle de propuestas (renglones artículo × cantidad)
-- ---------------------------------------------------------------------
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'autorepo_propuestas_det')
BEGIN
    CREATE TABLE omicronvt.dbo.autorepo_propuestas_det (
        id                      INT IDENTITY(1,1) PRIMARY KEY,
        propuesta_id            INT            NOT NULL,
        articulo                INT            NOT NULL,
        cantidad                INT            NOT NULL,
        precio_costo            DECIMAL(18,2)  NOT NULL,
        score                   DECIMAL(5,2)   NULL,
        vel_origen              DECIMAL(10,4)  NULL,
        vel_destino             DECIMAL(10,4)  NULL,
        dias_cobertura_origen   DECIMAL(8,1)   NULL,
        dias_cobertura_destino  DECIMAL(8,1)   NULL,
        motivo                  VARCHAR(50)    NULL,               -- QUIEBRE_INMINENTE|SOBRESTOCK|DEAD_STOCK_REUTIL|DRAG_EFFECT
        CONSTRAINT fk_autorepo_det_prop
            FOREIGN KEY (propuesta_id)
            REFERENCES omicronvt.dbo.autorepo_propuestas(id)
    );

    CREATE INDEX idx_autorepo_det_prop
        ON omicronvt.dbo.autorepo_propuestas_det(propuesta_id);

    CREATE INDEX idx_autorepo_det_art
        ON omicronvt.dbo.autorepo_propuestas_det(articulo);

    PRINT 'Tabla autorepo_propuestas_det creada con FK + 2 índices.';
END
ELSE
BEGIN
    PRINT 'Tabla autorepo_propuestas_det ya existe. Omitido.';
END
GO

PRINT '================================================================';
PRINT 'crear_tablas_autorepo.sql ejecutado OK.';
PRINT '================================================================';
GO
