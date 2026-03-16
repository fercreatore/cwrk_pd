-- =============================================================
-- Agregar aliases faltantes descubiertos en datos reales
-- EJECUTAR EN: 192.168.2.111 - BASE: msgestion01
-- Fecha: 14 mar 2026
-- =============================================================

USE msgestion01;
GO

-- Typos con caracter basura (faltaba 40Ç, solo teníamos 38Ç)
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', '40Ç', '40', 'typo con caracter basura');
GO

-- Talles con prefijo T (niños/bebés)
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', 'T.0',  '0',  'prefijo T. para niño'),
('CALZADO', 'T.1',  '1',  'prefijo T. para niño'),
('CALZADO', 'T.2',  '2',  'prefijo T. para niño'),
('CALZADO', 'T.3',  '3',  'prefijo T. para niño'),
('CALZADO', 'T.4',  '4',  'prefijo T. para niño'),
('CALZADO', 'T.5',  '5',  'prefijo T. para niño'),
('CALZADO', 'T.6',  '6',  'prefijo T. para niño'),
('CALZADO', 'T.7',  '7',  'prefijo T. para niño'),
('CALZADO', 'T/2',  '2',  'prefijo T/ para niño'),
('CALZADO', 'T/3',  '3',  'prefijo T/ para niño'),
('CALZADO', 'T/4',  '4',  'prefijo T/ para niño'),
('CALZADO', 'T/5',  '5',  'prefijo T/ para niño');
GO

-- Ojota fraccionada con espacio (9/ 0 → normalizar a 9/0)
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', '9/ 0', '9/0', 'ojota fraccionada con espacio');
GO

-- Indumentaria dobles
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('INDUMENTARIA', 'S/M',     'S',   'talle doble indum -> menor'),
('INDUMENTARIA', 'M/L',     'M',   'talle doble indum -> menor'),
('INDUMENTARIA', 'L/XL',    'L',   'talle doble indum -> menor'),
('INDUMENTARIA', 'XL/XXL',  'XL',  'talle doble indum -> menor'),
('INDUMENTARIA', '2XL/3XL', 'XXL', 'talle doble indum -> menor');
GO

-- Indumentaria con prefijo T
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('INDUMENTARIA', 'T.L',   'L',   'prefijo T. indumentaria'),
('INDUMENTARIA', 'T.M',   'M',   'prefijo T. indumentaria'),
('INDUMENTARIA', 'T.XL',  'XL',  'prefijo T. indumentaria'),
('INDUMENTARIA', 'T.XXL', 'XXL', 'prefijo T. indumentaria'),
('INDUMENTARIA', 'T/U',   'UNICO', 'T/U = talle unico'),
('INDUMENTARIA', 'T.U',   'UNICO', 'T.U = talle unico');
GO

-- Talle único variantes para CALZADO (accesorios también)
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('ACCESORIO', 'U',     'UNICO', 'talle unico accesorio'),
('ACCESORIO', 'UNICO', 'UNICO', 'talle unico accesorio'),
('ACCESORIO', 'T/U',   'UNICO', 'T/U accesorio'),
('ACCESORIO', 'T.U',   'UNICO', 'T.U accesorio'),
('ACCESORIO', 'C/U',   'UNICO', 'C/U = cada uno = unico');
GO

PRINT 'Aliases faltantes agregados OK';
GO

-- Verificar totales
SELECT tipo_talle, COUNT(*) as total_aliases
FROM dbo.aliases_talles
GROUP BY tipo_talle
ORDER BY tipo_talle;
GO
