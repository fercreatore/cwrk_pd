-- =============================================================
-- FIX: Ejecutar capas 2 y 3 que no corrieron por error de sintaxis
-- EJECUTAR EN: 192.168.2.111 - BASE: msgestion01
-- (La capa 1 ya quedó OK)
-- =============================================================

USE msgestion01;
GO

-- =============================================================
-- CAPA 2: TABLA DE ALIASES
-- =============================================================

IF OBJECT_ID('dbo.aliases_talles', 'U') IS NOT NULL
    DROP TABLE dbo.aliases_talles;
GO

CREATE TABLE dbo.aliases_talles (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    tipo_talle      VARCHAR(30)  NOT NULL,
    alias           VARCHAR(30)  NOT NULL,
    talle_resuelto  VARCHAR(30)  NOT NULL,
    observaciones   VARCHAR(100) NULL
);
GO

CREATE UNIQUE INDEX UX_aliases_tipo_alias
    ON dbo.aliases_talles (tipo_talle, alias);
GO

-- Typos y caracteres basura
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', '38Ç',  '38', 'typo con caracter basura'),
('CALZADO', '38.',  '38', 'punto suelto'),
('CALZADO', '39.',  '39', 'punto suelto'),
('CALZADO', '40.',  '40', 'punto suelto'),
('CALZADO', '35.0', '35', 'decimal innecesario'),
('CALZADO', '36.0', '36', 'decimal innecesario'),
('CALZADO', '37.0', '37', 'decimal innecesario'),
('CALZADO', '38.0', '38', 'decimal innecesario'),
('CALZADO', '39.0', '39', 'decimal innecesario'),
('CALZADO', '40.0', '40', 'decimal innecesario'),
('CALZADO', '41.0', '41', 'decimal innecesario'),
('CALZADO', '42.0', '42', 'decimal innecesario'),
('CALZADO', '43.0', '43', 'decimal innecesario'),
('CALZADO', '44.0', '44', 'decimal innecesario'),
('CALZADO', '45.0', '45', 'decimal innecesario');

-- Talles dobles (se toma el menor)
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', '35/36',         '35', 'talle doble -> menor'),
('CALZADO', '37/38',         '37', 'talle doble -> menor'),
('CALZADO', '39/40',         '39', 'talle doble -> menor'),
('CALZADO', '41/42',         '41', 'talle doble -> menor'),
('CALZADO', '43/44',         '43', 'talle doble -> menor'),
('CALZADO', '38/39/40/41',   '38', 'rango amplio -> menor');

-- Ojotas fraccionadas (válidas)
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', '0/1', '0/1', 'ojota fraccionada'),
('CALZADO', '1/2', '1/2', 'ojota fraccionada'),
('CALZADO', '2/3', '2/3', 'ojota fraccionada'),
('CALZADO', '3/4', '3/4', 'ojota fraccionada'),
('CALZADO', '4/5', '4/5', 'ojota fraccionada'),
('CALZADO', '5/6', '5/6', 'ojota fraccionada'),
('CALZADO', '6/7', '6/7', 'ojota fraccionada'),
('CALZADO', '7/8', '7/8', 'ojota fraccionada'),
('CALZADO', '8/9', '8/9', 'ojota fraccionada'),
('CALZADO', '9/0', '9/0', 'ojota fraccionada');

-- Formato proveedor US
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', 'M4',   '35',   'US mujer 4 -> AR 35'),
('CALZADO', 'M5',   '36',   'US mujer 5 -> AR 36'),
('CALZADO', 'M6',   '37',   'US mujer 6 -> AR 37'),
('CALZADO', 'M7',   '38',   'US mujer 7 -> AR 38'),
('CALZADO', 'M8',   '39',   'US mujer 8 -> AR 39'),
('CALZADO', 'M9',   '40',   'US mujer 9 -> AR 40'),
('CALZADO', 'M10',  '41',   'US mujer 10 -> AR 41'),
('CALZADO', 'W5',   '35',   'Women 5 -> AR 35'),
('CALZADO', 'W6',   '36',   'Women 6 -> AR 36'),
('CALZADO', 'W7',   '37',   'Women 7 -> AR 37'),
('CALZADO', 'W8',   '38',   'Women 8 -> AR 38'),
('CALZADO', 'W9',   '39',   'Women 9 -> AR 39'),
('CALZADO', 'W10',  '40',   'Women 10 -> AR 40'),
('CALZADO', 'M4/W6','36',   'Combo M4/W6 -> AR 36');

-- Genéricos
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', 'U',     'UNICO', 'talle unico'),
('CALZADO', 'UNICO', 'UNICO', 'talle unico normalizado');

-- Indumentaria
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('INDUMENTARIA', 'XS',    'XS',    'valido'),
('INDUMENTARIA', 'S',     'S',     'valido'),
('INDUMENTARIA', 'M',     'M',     'valido'),
('INDUMENTARIA', 'L',     'L',     'valido'),
('INDUMENTARIA', 'XL',    'XL',    'valido'),
('INDUMENTARIA', 'XXL',   'XXL',   'valido'),
('INDUMENTARIA', 'XXXL',  'XXXL',  'valido'),
('INDUMENTARIA', '2XL',   'XXL',   'alias numerico'),
('INDUMENTARIA', '3XL',   'XXXL',  'alias numerico'),
('INDUMENTARIA', '4XL',   'XXXXL', 'alias numerico'),
('INDUMENTARIA', 'XXXXXL','XXXXXL','talle especial');

PRINT 'Capa 2: aliases_talles OK';
GO

-- =============================================================
-- CAPA 3: REGLA POR SUBRUBRO
-- =============================================================

IF OBJECT_ID('dbo.regla_talle_subrubro', 'U') IS NOT NULL
    DROP TABLE dbo.regla_talle_subrubro;
GO

CREATE TABLE dbo.regla_talle_subrubro (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    codigo_subrubro NUMERIC       NOT NULL,
    tipo_talle      VARCHAR(30)   NOT NULL,
    acepta_mp       BIT           DEFAULT 0,
    observaciones   VARCHAR(100)  NULL
);
GO

CREATE UNIQUE INDEX UX_regla_talle_sub
    ON dbo.regla_talle_subrubro (codigo_subrubro);
GO

-- Calzado clasico (enteros 34-50)
INSERT INTO dbo.regla_talle_subrubro (codigo_subrubro, tipo_talle, acepta_mp, observaciones) VALUES
(1,  'CALZADO', 0, 'ALPARGATAS'),
(2,  'CALZADO', 0, 'BORCEGOS'),
(5,  'CALZADO', 0, 'CHATA'),
(7,  'CALZADO', 0, 'MOCASINES'),
(12, 'CALZADO', 0, 'SANDALIAS'),
(15, 'CALZADO', 0, 'BOTAS'),
(17, 'CALZADO', 0, 'GUILLERMINA'),
(19, 'CALZADO', 1, 'BOTINES TAPON - acepta MP'),
(20, 'CALZADO', 0, 'ZAPATO DE VESTIR'),
(21, 'CALZADO', 0, 'CASUAL'),
(35, 'CALZADO', 0, 'PANCHA'),
(37, 'CALZADO', 0, 'FRANCISCANA'),
(38, 'CALZADO', 0, 'MERREL'),
(40, 'CALZADO', 0, 'NAUTICO'),
(56, 'CALZADO', 0, 'FIESTA'),
(60, 'CALZADO', 0, 'PANTUFLA'),
(64, 'CALZADO', 0, 'ZAPATO DE TRABAJO'),
(65, 'CALZADO', 0, 'BOTA DE LLUVIA');

-- Calzado deportivo (acepta medio punto)
INSERT INTO dbo.regla_talle_subrubro (codigo_subrubro, tipo_talle, acepta_mp, observaciones) VALUES
(45, 'CALZADO', 1, 'BOTINES PISTA'),
(47, 'CALZADO', 1, 'ZAPATILLA RUNNING'),
(48, 'CALZADO', 1, 'ZAPATILLA TENNIS'),
(49, 'CALZADO', 1, 'ZAPATILLA TRAINING'),
(50, 'CALZADO', 1, 'ZAPATILLA BASKET'),
(51, 'CALZADO', 1, 'ZAPATILLA OUTDOOR'),
(52, 'CALZADO', 1, 'ZAPATILLA CASUAL'),
(53, 'CALZADO', 1, 'ZAPATILLA SKATER'),
(54, 'CALZADO', 1, 'BOTIN INDOOR'),
(55, 'CALZADO', 1, 'ZAPATILLA SNEAKERS'),
(69, 'CALZADO', 1, 'ZAPATILLA HOCKEY');

-- Ojotas/chinelas/zuecos (fraccionados 0/1 - 9/0)
INSERT INTO dbo.regla_talle_subrubro (codigo_subrubro, tipo_talle, acepta_mp, observaciones) VALUES
(6,  'OJOTA', 0, 'CHINELA'),
(11, 'OJOTA', 0, 'OJOTAS'),
(13, 'OJOTA', 0, 'ZUECOS');

-- Indumentaria
INSERT INTO dbo.regla_talle_subrubro (codigo_subrubro, tipo_talle, acepta_mp, observaciones) VALUES
(23, 'INDUMENTARIA', 0, 'PANTALON'),
(46, 'INDUMENTARIA', 0, 'CAMPERAS'),
(57, 'INDUMENTARIA', 0, 'REMERAS'),
(61, 'INDUMENTARIA', 0, 'BUZO'),
(62, 'INDUMENTARIA', 0, 'CALZA'),
(63, 'INDUMENTARIA', 0, 'MALLA'),
(70, 'INDUMENTARIA', 0, 'BOXER');

-- Accesorios
INSERT INTO dbo.regla_talle_subrubro (codigo_subrubro, tipo_talle, acepta_mp, observaciones) VALUES
(3,  'ACCESORIO', 0, 'MAQUILLAJE'),
(10, 'ACCESORIO', 0, 'ACC. DEPORTIVOS'),
(18, 'ACCESORIO', 0, 'CARTERAS'),
(22, 'ACCESORIO', 0, 'CANILLERA'),
(24, 'ACCESORIO', 0, 'PARAGUAS'),
(25, 'ACCESORIO', 0, 'MOCHILAS'),
(26, 'ACCESORIO', 0, 'BILLETERAS'),
(27, 'ACCESORIO', 0, 'PLANTILLAS'),
(28, 'ACCESORIO', 0, 'CORDONES'),
(29, 'ACCESORIO', 0, 'MEDIAS'),
(30, 'ACCESORIO', 0, 'BOLSOS'),
(32, 'ACCESORIO', 0, 'COSMETICA DE CALZADO'),
(33, 'ACCESORIO', 0, 'PELOTAS'),
(39, 'ACCESORIO', 0, 'ACC. MARRO'),
(71, 'ACCESORIO', 0, 'RINONERA');

-- Otros
INSERT INTO dbo.regla_talle_subrubro (codigo_subrubro, tipo_talle, acepta_mp, observaciones) VALUES
(58, 'CINTO',  0, 'CINTOS - talle cm cintura'),
(68, 'VALIJA', 0, 'VALIJAS - talle pulgadas'),
(59, 'CALZADO', 0, 'ROLLER/PATIN');

PRINT 'Capa 3: regla_talle_subrubro OK';
GO

-- =============================================================
-- VERIFICACION (sin palabras reservadas)
-- =============================================================

PRINT '';
PRINT '========== RESUMEN 3 CAPAS ==========';

SELECT 'equivalencias_talles' as tabla, tipo_talle, COUNT(*) as registros
FROM dbo.equivalencias_talles GROUP BY tipo_talle;

SELECT 'aliases_talles' as tabla, tipo_talle, COUNT(*) as aliases
FROM dbo.aliases_talles GROUP BY tipo_talle;

SELECT 'regla_talle_subrubro' as tabla, tipo_talle, COUNT(*) as subrubros,
       SUM(CAST(acepta_mp AS INT)) as con_medio_punto
FROM dbo.regla_talle_subrubro GROUP BY tipo_talle;

-- Subrubros sin clasificar
SELECT s.codigo, s.descripcion as subrubro_sin_regla
FROM dbo.subrubro s
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.regla_talle_subrubro r WHERE r.codigo_subrubro = s.codigo
)
AND s.codigo < 200
ORDER BY s.codigo;

-- Verificar la vieja quedó respaldada
IF OBJECT_ID('dbo.equivalencias_talles_OLD', 'U') IS NOT NULL
    SELECT 'equivalencias_talles_OLD' as tabla_respaldo, COUNT(*) as registros
    FROM dbo.equivalencias_talles_OLD;

PRINT '';
PRINT '=== 3 CAPAS COMPLETAS ===';
GO
