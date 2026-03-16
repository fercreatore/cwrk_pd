-- ============================================================
-- EJECUTAR EN: 192.168.2.111 (servidor web2py / produccion)
-- BASE: omicronvt
-- Agrega subrubros faltantes a map_subrubro_industria
-- ============================================================
USE omicronvt;
GO

INSERT INTO dbo.map_subrubro_industria (subrubro, industria) VALUES
(60, 'Zapatería'),       -- PANTUFLA
(64, 'Ferretero'),       -- ZAPATO DE TRABAJO
(65, 'Ferretero'),       -- BOTA DE LLUVIA
(68, 'Marroquinería');   -- VALIJAS
-- 67 (PROMO FIN DE TEMPORADA) se deja sin clasificar
GO

-- Refrescar la cache
EXEC dbo.sp_sync_pedidos;
GO

PRINT 'OK - Industrias agregadas y cache actualizada.';
GO
