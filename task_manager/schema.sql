-- ============================================================================
-- TASK MANAGER EQUIPO — Schema SQL
-- Ejecutar en: omicronvt (192.168.2.111 produccion)
-- Fecha: 1 de abril de 2026
-- ============================================================================

USE omicronvt;
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 1. TAREAS DEL EQUIPO
-- ────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'tareas_equipo')
BEGIN
    CREATE TABLE dbo.tareas_equipo (
        id                      INT IDENTITY(1,1) PRIMARY KEY,
        titulo                  VARCHAR(200) NOT NULL,
        descripcion             VARCHAR(MAX) NULL,
        -- Responsable
        responsable_nombre      VARCHAR(100) NOT NULL,
        responsable_wa          VARCHAR(20) NULL,       -- +5493462XXXXXX
        responsable_chatwoot_id INT NULL,               -- contact_id en Chatwoot
        -- Asignacion
        asignado_por            VARCHAR(100) DEFAULT 'Fernando',
        fecha_creacion          DATETIME DEFAULT GETDATE(),
        deadline                DATE NULL,
        -- Clasificacion
        prioridad               VARCHAR(5) DEFAULT 'P2'
            CHECK (prioridad IN ('P0','P1','P2','P3')),
        estado                  VARCHAR(20) DEFAULT 'ASIGNADA'
            CHECK (estado IN ('ASIGNADA','EN_PROGRESO','BLOQUEADA','COMPLETA','CANCELADA')),
        area                    VARCHAR(50) NULL,
        -- Entrega
        canal_entrega           VARCHAR(100) NULL,      -- "Excel por WA", "mail", "ERP"
        resultado_esperado      VARCHAR(MAX) NULL,
        -- Seguimiento
        notas_avance            VARCHAR(MAX) NULL,      -- append de updates
        motivo_bloqueo          VARCHAR(500) NULL,
        porcentaje_avance       INT DEFAULT 0
            CHECK (porcentaje_avance BETWEEN 0 AND 100),
        -- Timestamps
        fecha_ultima_actualizacion DATETIME NULL,
        fecha_completada        DATETIME NULL,
        -- Contexto semanal
        semana_asignacion       VARCHAR(20) NULL,       -- '2026-W14'
        -- Mensaje original (para debug/auditoria)
        mensaje_original        VARCHAR(MAX) NULL
    );

    CREATE INDEX IX_te_responsable ON dbo.tareas_equipo(responsable_nombre);
    CREATE INDEX IX_te_estado ON dbo.tareas_equipo(estado);
    CREATE INDEX IX_te_deadline ON dbo.tareas_equipo(deadline);
    CREATE INDEX IX_te_semana ON dbo.tareas_equipo(semana_asignacion);
    CREATE INDEX IX_te_prioridad ON dbo.tareas_equipo(prioridad);

    PRINT 'Tabla tareas_equipo creada OK';
END
ELSE
    PRINT 'Tabla tareas_equipo ya existe';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 2. HISTORIAL DE CAMBIOS (log de cada update de estado)
-- ────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'tareas_historial')
BEGIN
    CREATE TABLE dbo.tareas_historial (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        tarea_id        INT NOT NULL,               -- FK logica → tareas_equipo.id
        estado_anterior VARCHAR(20) NULL,
        estado_nuevo    VARCHAR(20) NULL,
        notas           VARCHAR(500) NULL,
        autor           VARCHAR(100) NULL,           -- quien hizo el cambio
        fecha           DATETIME DEFAULT GETDATE()
    );

    CREATE INDEX IX_th_tarea ON dbo.tareas_historial(tarea_id);
    CREATE INDEX IX_th_fecha ON dbo.tareas_historial(fecha);

    PRINT 'Tabla tareas_historial creada OK';
END
ELSE
    PRINT 'Tabla tareas_historial ya existe';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 3. CONFIGURACION DE CHECKPOINTS AUTOMATICOS
-- ────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'tareas_checkpoint_log')
BEGIN
    CREATE TABLE dbo.tareas_checkpoint_log (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        tipo            VARCHAR(20) NOT NULL,       -- 'CHECKPOINT_MIE', 'CIERRE_VIE'
        semana          VARCHAR(20) NOT NULL,       -- '2026-W14'
        destinatario    VARCHAR(100) NULL,
        mensaje_enviado VARCHAR(MAX) NULL,
        fecha           DATETIME DEFAULT GETDATE(),
        ok              BIT DEFAULT 1
    );

    PRINT 'Tabla tareas_checkpoint_log creada OK';
END
ELSE
    PRINT 'Tabla tareas_checkpoint_log ya existe';
GO

PRINT '';
PRINT '===================================================';
PRINT ' TABLAS TASK MANAGER CREADAS';
PRINT '===================================================';
GO
