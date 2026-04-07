-- ============================================================================
-- SISTEMA VENDEDOR FREELANCE — FASE 3: Alta de Matías Rodríguez
-- Ejecutar en: omicronvt database
-- Fecha: 23 de marzo de 2026
--
-- Inserta a Matías Rodríguez (viajante_cod=755) en vendedor_freelance
-- con valores configurados para monotributo categoría D.
-- ============================================================================

USE omicronvt;
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 1. ALTA MATÍAS RODRÍGUEZ - Viajante código 755
-- ────────────────────────────────────────────────────────────────────────────

IF NOT EXISTS (SELECT 1 FROM dbo.vendedor_freelance WHERE viajante_cod = 755)
BEGIN
    INSERT INTO dbo.vendedor_freelance (
        viajante_cod,
        categoria_mono,
        cuota_mono,
        fee_pct_std,
        fee_pct_premium,
        codigo_atrib,
        canon_mensual,
        fecha_inicio,
        activo,
        cuit,
        razon_social,
        instagram,
        whatsapp
    )
    VALUES (
        755,                    -- viajante_cod
        'D',                    -- categoria_mono (default)
        72414.00,               -- cuota_mono
        0.05,                   -- fee_pct_std (5%)
        0.08,                   -- fee_pct_premium (8%)
        'V755',                 -- codigo_atrib
        0.00,                   -- canon_mensual
        GETDATE(),              -- fecha_inicio
        1,                      -- activo
        NULL,                   -- cuit (pendiente de confirmación)
        NULL,                   -- razon_social (pendiente)
        NULL,                   -- instagram (pendiente)
        NULL                    -- whatsapp (pendiente)
    );
    PRINT 'Matías Rodríguez (V755) insertado en vendedor_freelance OK';
END
ELSE
BEGIN
    PRINT 'Matías Rodríguez (V755) ya existe en vendedor_freelance';
END
GO

-- ────────────────────────────────────────────────────────────────────────────
-- Resumen
-- ────────────────────────────────────────────────────────────────────────────

PRINT '';
PRINT '═══════════════════════════════════════════════════════';
PRINT ' ALTA MATÍAS RODRÍGUEZ - COMPLETADA';
PRINT '═══════════════════════════════════════════════════════';
PRINT '';

SELECT
    id,
    viajante_cod,
    codigo_atrib,
    categoria_mono,
    cuota_mono,
    fee_pct_std,
    fee_pct_premium,
    canon_mensual,
    fecha_inicio,
    activo
FROM dbo.vendedor_freelance
WHERE viajante_cod = 755;

PRINT '';
PRINT 'Próximos pasos:';
PRINT '1. Confirmar CUIT y Razón Social de Matías';
PRINT '2. Agregar Instagram y WhatsApp si están disponibles';
PRINT '3. Crear catálogo de productos específico para Matías';
PRINT '';
GO
