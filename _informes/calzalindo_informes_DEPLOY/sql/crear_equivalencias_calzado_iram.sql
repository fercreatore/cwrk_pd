-- =============================================================
-- TABLA MAESTRA DE EQUIVALENCIAS DE TALLES
-- EJECUTAR EN: 192.168.2.111 (DELL-SVR / produccion)
-- BASE: msgestion01
--
-- Fuente: Tabla operativa interna basada en la lógica del
--         sistema AR (IRAM 8604:2020 - largo del pie).
--         NO es transcripción literal de la norma IRAM.
--         Armada para ecommerce / ERP / marketplaces / guía de talles.
--
-- NOTA sobre conversiones US vs proveedores:
--   Esta tabla (IRAM): AR = US_hombre + 31 | AR = US_mujer + 29.5
--   Reebok/Distrinando:  AR = US_hombre + 32 | AR = US_mujer + 30
--   Diferencia de ~1 talle. Para inserción de artículos Reebok
--   se sigue usando la conversión del proveedor (ocr_factura.py).
--   Esta tabla es la referencia para guía de talles al consumidor.
--
-- Fecha: 2026-03-07
-- =============================================================

USE msgestion01;
GO

-- =============================================================
-- 1. TABLA ESPECIFICA: equivalencias_talles_calzado
--    Tabla desnormalizada con todas las equivalencias por fila
-- =============================================================

IF OBJECT_ID('dbo.equivalencias_talles_calzado', 'U') IS NOT NULL
    DROP TABLE dbo.equivalencias_talles_calzado;
GO

CREATE TABLE dbo.equivalencias_talles_calzado (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    talle_ar          DECIMAL(4,1) NOT NULL,
    largo_pie_cm      DECIMAL(4,1) NOT NULL,
    mondopoint_mm     INT NOT NULL,
    talle_eu          DECIMAL(4,1) NULL,
    talle_br          DECIMAL(4,1) NULL,
    talle_uk          DECIMAL(4,1) NULL,
    talle_us_hombre   DECIMAL(4,1) NULL,
    talle_us_mujer    DECIMAL(4,1) NULL,
    orden             INT NOT NULL,
    observaciones     VARCHAR(100) NULL
);
GO

CREATE UNIQUE INDEX UX_equiv_talles_calzado_ar
    ON dbo.equivalencias_talles_calzado (talle_ar);
CREATE INDEX IX_equiv_talles_calzado_cm
    ON dbo.equivalencias_talles_calzado (largo_pie_cm);
GO

INSERT INTO dbo.equivalencias_talles_calzado
(talle_ar, largo_pie_cm, mondopoint_mm, talle_eu, talle_br, talle_uk, talle_us_hombre, talle_us_mujer, orden, observaciones)
VALUES
(34.0, 21.6, 216, 34.0, 32.0, 2.0,  3.0,  4.5,  340, 'base operativa'),
(34.5, 22.1, 221, 34.5, 32.5, 2.5,  3.5,  5.0,  345, 'base operativa'),
(35.0, 22.5, 225, 35.0, 33.0, 3.0,  4.0,  5.5,  350, 'base operativa'),
(35.5, 22.9, 229, 35.5, 33.5, 3.5,  4.5,  6.0,  355, 'base operativa'),
(36.0, 23.3, 233, 36.0, 34.0, 4.0,  5.0,  6.5,  360, 'base operativa'),
(36.5, 23.8, 238, 36.5, 34.5, 4.5,  5.5,  7.0,  365, 'base operativa'),
(37.0, 24.2, 242, 37.0, 35.0, 5.0,  6.0,  7.5,  370, 'base operativa'),
(37.5, 24.6, 246, 37.5, 35.5, 5.5,  6.5,  8.0,  375, 'base operativa'),
(38.0, 25.0, 250, 38.0, 36.0, 6.0,  7.0,  8.5,  380, 'base operativa'),
(38.5, 25.5, 255, 38.5, 36.5, 6.5,  7.5,  9.0,  385, 'base operativa'),
(39.0, 25.9, 259, 39.0, 37.0, 7.0,  8.0,  9.5,  390, 'base operativa'),
(39.5, 26.3, 263, 39.5, 37.5, 7.5,  8.5,  10.0, 395, 'base operativa'),
(40.0, 26.7, 267, 40.0, 38.0, 8.0,  9.0,  10.5, 400, 'base operativa'),
(40.5, 27.1, 271, 40.5, 38.5, 8.5,  9.5,  11.0, 405, 'base operativa'),
(41.0, 27.6, 276, 41.0, 39.0, 9.0,  10.0, 11.5, 410, 'base operativa'),
(41.5, 28.0, 280, 41.5, 39.5, 9.5,  10.5, 12.0, 415, 'base operativa'),
(42.0, 28.4, 284, 42.0, 40.0, 10.0, 11.0, 12.5, 420, 'base operativa'),
(42.5, 28.8, 288, 42.5, 40.5, 10.5, 11.5, 13.0, 425, 'base operativa'),
(43.0, 29.3, 293, 43.0, 41.0, 11.0, 12.0, 13.5, 430, 'base operativa'),
(43.5, 29.7, 297, 43.5, 41.5, 11.5, 12.5, 14.0, 435, 'base operativa'),
(44.0, 30.1, 301, 44.0, 42.0, 12.0, 13.0, 14.5, 440, 'base operativa'),
(44.5, 30.5, 305, 44.5, 42.5, 12.5, 13.5, 15.0, 445, 'base operativa'),
(45.0, 31.0, 310, 45.0, 43.0, 13.0, 14.0, 15.5, 450, 'base operativa'),
(45.5, 31.4, 314, 45.5, 43.5, 13.5, 14.5, 16.0, 455, 'base operativa'),
(46.0, 31.8, 318, 46.0, 44.0, 14.0, 15.0, 16.5, 460, 'base operativa');

PRINT '1. equivalencias_talles_calzado: 25 registros (AR 34-46 c/medio punto)';
GO

-- =============================================================
-- 2. TABLA MAESTRA: equivalencias_talles (nueva versión)
--    Diseñada para escalar: CALZADO hoy, mañana INDUMENTARIA,
--    VALIJAS, CINTURONES, etc.
--
--    ATENCION: La tabla vieja tiene 72 registros con otro schema
--    (tipo_talle_id, talle_valor, talla_cm, pais_origen).
--    La renombramos a _OLD para no perder datos.
-- =============================================================

-- Backup de la tabla vieja si existe con el schema anterior
IF OBJECT_ID('dbo.equivalencias_talles', 'U') IS NOT NULL
   AND EXISTS (
       SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
       WHERE TABLE_NAME = 'equivalencias_talles'
         AND COLUMN_NAME = 'tipo_talle_id'  -- columna del schema viejo
   )
BEGIN
    -- Renombrar la vieja
    IF OBJECT_ID('dbo.equivalencias_talles_OLD', 'U') IS NOT NULL
        DROP TABLE dbo.equivalencias_talles_OLD;
    EXEC sp_rename 'dbo.equivalencias_talles', 'equivalencias_talles_OLD';
    PRINT '2a. Tabla vieja renombrada a equivalencias_talles_OLD (72 registros preservados)';
END
GO

-- Crear la nueva si no existe
IF OBJECT_ID('dbo.equivalencias_talles', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.equivalencias_talles (
        id                INT IDENTITY(1,1) PRIMARY KEY,
        tipo_talle        VARCHAR(30)  NOT NULL,     -- 'CALZADO', 'INDUMENTARIA', 'CINTURON', 'VALIJA'
        talle_original    VARCHAR(30)  NOT NULL,      -- valor tal cual viene (ej: "41", "41½", "XL", "28")
        talle_normalizado VARCHAR(30)  NOT NULL,      -- valor estandarizado
        largo_pie_cm      DECIMAL(4,1) NULL,          -- solo calzado
        mondopoint_mm     INT          NULL,          -- solo calzado
        talle_eu          DECIMAL(4,1) NULL,          -- solo calzado
        talle_br          DECIMAL(4,1) NULL,          -- solo calzado
        talle_uk          DECIMAL(4,1) NULL,          -- solo calzado
        talle_us_hombre   DECIMAL(4,1) NULL,          -- solo calzado
        talle_us_mujer    DECIMAL(4,1) NULL,          -- solo calzado
        genero_id         INT          NULL,           -- 1=dama, 3=hombre, 4=niño (de rubros)
        orden             INT          NULL,
        fuente            VARCHAR(100) NULL
    );

    CREATE INDEX IX_equiv_talles_tipo ON dbo.equivalencias_talles (tipo_talle, orden);
    CREATE INDEX IX_equiv_talles_original ON dbo.equivalencias_talles (tipo_talle, talle_original);

    PRINT '2b. Tabla maestra equivalencias_talles CREADA (schema nuevo)';
END
ELSE
    PRINT '2b. Tabla maestra equivalencias_talles ya existe con schema nuevo';
GO

-- =============================================================
-- 3. MIGRAR CALZADO a la tabla maestra
-- =============================================================

-- Limpiar calzado existente si hay
DELETE FROM dbo.equivalencias_talles WHERE tipo_talle = 'CALZADO';

INSERT INTO dbo.equivalencias_talles
(
    tipo_talle,
    talle_original,
    talle_normalizado,
    largo_pie_cm,
    mondopoint_mm,
    talle_eu,
    talle_br,
    talle_uk,
    talle_us_hombre,
    talle_us_mujer,
    genero_id,
    orden,
    fuente
)
SELECT
    'CALZADO',
    CAST(talle_ar AS VARCHAR(10)),
    CAST(talle_ar AS VARCHAR(10)),
    largo_pie_cm,
    mondopoint_mm,
    talle_eu,
    talle_br,
    talle_uk,
    talle_us_hombre,
    talle_us_mujer,
    NULL,       -- genero_id NULL porque la fila aplica a todos
    orden,
    'Base operativa armada sobre CIC/IRAM 8604 + equivalencias de mercado'
FROM dbo.equivalencias_talles_calzado;

PRINT '3. Calzado migrado a tabla maestra: 25 registros';
GO

-- =============================================================
-- 4. VERIFICACION
-- =============================================================

PRINT '';
PRINT '========== RESUMEN FINAL ==========';

SELECT tipo_talle, COUNT(*) as registros,
       MIN(talle_original) as talle_min,
       MAX(talle_original) as talle_max
FROM dbo.equivalencias_talles
GROUP BY tipo_talle;

-- Vista rápida de la tabla de calzado
SELECT
    talle_original as AR,
    largo_pie_cm as CM,
    mondopoint_mm as MONDO,
    talle_us_hombre as US_H,
    talle_us_mujer as US_M,
    talle_eu as EU,
    talle_uk as UK
FROM dbo.equivalencias_talles
WHERE tipo_talle = 'CALZADO'
ORDER BY orden;

-- Confirmar que la vieja quedó respaldada
IF OBJECT_ID('dbo.equivalencias_talles_OLD', 'U') IS NOT NULL
    SELECT 'equivalencias_talles_OLD' as backup, COUNT(*) as registros
    FROM dbo.equivalencias_talles_OLD;

PRINT '';
PRINT '=== Capa 1 OK: Maestra + Calzado ===';
GO

-- =============================================================
-- 5. CAPA 2: TABLA DE ALIASES
--    Absorbe la basura real de descripcion_5:
--    "38Ç" → 38, "37/38" → 37, "U" → UNICO, etc.
--    También mapea formatos alternativos de proveedores:
--    "M4" → US mujer 4, "W6" → US mujer 6, etc.
-- =============================================================

IF OBJECT_ID('dbo.aliases_talles', 'U') IS NOT NULL
    DROP TABLE dbo.aliases_talles;
GO

CREATE TABLE dbo.aliases_talles (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    tipo_talle      VARCHAR(30)  NOT NULL,    -- 'CALZADO', 'INDUMENTARIA', etc.
    alias           VARCHAR(30)  NOT NULL,    -- lo que viene en descripcion_5
    talle_resuelto  VARCHAR(30)  NOT NULL,    -- a qué talle normalizado mapea
    observaciones   VARCHAR(100) NULL
);
GO

CREATE UNIQUE INDEX UX_aliases_tipo_alias
    ON dbo.aliases_talles (tipo_talle, alias);
GO

-- ----- CALZADO: typos y caracteres basura -----
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

-- ----- CALZADO: talles dobles (se toma el menor) -----
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', '35/36',         '35', 'talle doble → menor'),
('CALZADO', '37/38',         '37', 'talle doble → menor'),
('CALZADO', '39/40',         '39', 'talle doble → menor'),
('CALZADO', '41/42',         '41', 'talle doble → menor'),
('CALZADO', '43/44',         '43', 'talle doble → menor'),
('CALZADO', '38/39/40/41',   '38', 'rango amplio → menor');

-- ----- CALZADO: ojotas fraccionadas (son válidas, se normalizan) -----
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', '0/1', '0/1', 'ojota fraccionada - válido'),
('CALZADO', '1/2', '1/2', 'ojota fraccionada - válido'),
('CALZADO', '2/3', '2/3', 'ojota fraccionada - válido'),
('CALZADO', '3/4', '3/4', 'ojota fraccionada - válido'),
('CALZADO', '4/5', '4/5', 'ojota fraccionada - válido'),
('CALZADO', '5/6', '5/6', 'ojota fraccionada - válido'),
('CALZADO', '6/7', '6/7', 'ojota fraccionada - válido'),
('CALZADO', '7/8', '7/8', 'ojota fraccionada - válido'),
('CALZADO', '8/9', '8/9', 'ojota fraccionada - válido'),
('CALZADO', '9/0', '9/0', 'ojota fraccionada - válido');

-- ----- CALZADO: formato proveedor US -----
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', 'M4',   '35',   'US mujer 4 → AR 35 (IRAM)'),
('CALZADO', 'M5',   '36',   'US mujer 5 → AR 36'),
('CALZADO', 'M6',   '37',   'US mujer 6 → AR 37'),
('CALZADO', 'M7',   '38',   'US mujer 7 → AR 38'),
('CALZADO', 'M8',   '39',   'US mujer 8 → AR 39'),
('CALZADO', 'M9',   '40',   'US mujer 9 → AR 40'),
('CALZADO', 'M10',  '41',   'US mujer 10 → AR 41'),
('CALZADO', 'W5',   '35',   'Women 5 → AR 35'),
('CALZADO', 'W6',   '36',   'Women 6 → AR 36'),
('CALZADO', 'W7',   '37',   'Women 7 → AR 37'),
('CALZADO', 'W8',   '38',   'Women 8 → AR 38'),
('CALZADO', 'W9',   '39',   'Women 9 → AR 39'),
('CALZADO', 'W10',  '40',   'Women 10 → AR 40'),
('CALZADO', 'M4/W6','36',   'Combo M4/W6 → AR 36 (prioriza mujer)');

-- ----- GENÉRICOS -----
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', 'U',     'UNICO', 'talle único'),
('CALZADO', 'UNICO', 'UNICO', 'talle único normalizado');

-- ----- INDUMENTARIA: para futuro -----
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('INDUMENTARIA', 'XS',    'XS',   'válido'),
('INDUMENTARIA', 'S',     'S',    'válido'),
('INDUMENTARIA', 'M',     'M',    'válido'),
('INDUMENTARIA', 'L',     'L',    'válido'),
('INDUMENTARIA', 'XL',    'XL',   'válido'),
('INDUMENTARIA', 'XXL',   'XXL',  'válido'),
('INDUMENTARIA', 'XXXL',  'XXXL', 'válido'),
('INDUMENTARIA', '2XL',   'XXL',  'alias numérico'),
('INDUMENTARIA', '3XL',   'XXXL', 'alias numérico'),
('INDUMENTARIA', '4XL',   'XXXXL','alias numérico'),
('INDUMENTARIA', 'XXXXXL','XXXXXL','talle especial');

PRINT '5. aliases_talles poblada OK';
GO

-- =============================================================
-- 6. CAPA 3: REGLA POR SUBRUBRO
--    Cada subrubro se asigna a un tipo_talle para saber
--    cómo interpretar descripcion_5.
--    Cruza con agrupadores_subrubros (ya tiene 61 industrias).
-- =============================================================

IF OBJECT_ID('dbo.regla_talle_subrubro', 'U') IS NOT NULL
    DROP TABLE dbo.regla_talle_subrubro;
GO

CREATE TABLE dbo.regla_talle_subrubro (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    codigo_subrubro NUMERIC       NOT NULL,
    tipo_talle      VARCHAR(30)   NOT NULL,   -- 'CALZADO', 'INDUMENTARIA', 'ACCESORIO', 'OJOTA', 'VALIJA', 'CINTO'
    acepta_mp       BIT           DEFAULT 0,  -- 1 si el subrubro puede tener medio punto (½)
    observaciones   VARCHAR(100)  NULL
);
GO

CREATE UNIQUE INDEX UX_regla_talle_sub
    ON dbo.regla_talle_subrubro (codigo_subrubro);
GO

-- Calzado clásico (talles numéricos enteros 34-50)
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

-- Calzado deportivo (acepta medio punto por proveedores internacionales)
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

-- Ojotas/chinelas/zuecos (talles fraccionados 0/1 - 9/0)
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

-- Accesorios sin talle o talle genérico
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
(71, 'ACCESORIO', 0, 'RIÑONERA');

-- Otros
INSERT INTO dbo.regla_talle_subrubro (codigo_subrubro, tipo_talle, acepta_mp, observaciones) VALUES
(58, 'CINTO',  0, 'CINTOS - talle cm cintura'),
(68, 'VALIJA', 0, 'VALIJAS - talle pulgadas'),
(59, 'CALZADO', 0, 'ROLLER/PATIN');

PRINT '6. regla_talle_subrubro: subrubros clasificados OK';
GO

-- =============================================================
-- 7. VERIFICACION FINAL DE LAS 3 CAPAS
-- =============================================================

PRINT '';
PRINT '========== RESUMEN 3 CAPAS ==========';

SELECT 'Capa 1: equivalencias_talles' as capa, tipo_talle, COUNT(*) as registros
FROM dbo.equivalencias_talles
GROUP BY tipo_talle;

SELECT 'Capa 2: aliases_talles' as capa, tipo_talle, COUNT(*) as aliases
FROM dbo.aliases_talles
GROUP BY tipo_talle;

SELECT 'Capa 3: regla_talle_subrubro' as capa, tipo_talle, COUNT(*) as subrubros,
       SUM(CAST(acepta_mp AS INT)) as con_medio_punto
FROM dbo.regla_talle_subrubro
GROUP BY tipo_talle;

-- Subrubros sin clasificar
SELECT s.codigo, s.descripcion as subrubro_sin_regla
FROM dbo.subrubro s
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.regla_talle_subrubro r WHERE r.codigo_subrubro = s.codigo
)
AND s.codigo < 200  -- excluir materiales textiles (200+)
ORDER BY s.codigo;

PRINT '';
PRINT '=== 3 CAPAS COMPLETAS ===';
PRINT 'Capa 1: equivalencias_talles     → tabla maestra multi-tipo';
PRINT 'Capa 2: aliases_talles           → absorbe basura de descripcion_5';
PRINT 'Capa 3: regla_talle_subrubro     → decide cómo interpretar cada subrubro';
PRINT '';
PRINT 'Uso: dado un articulo con subrubro=49, descripcion_5=''38Ç'':';
PRINT '  1. regla_talle_subrubro → tipo_talle=CALZADO, acepta_mp=1';
PRINT '  2. aliases_talles → ''38Ç'' resuelve a ''38''';
PRINT '  3. equivalencias_talles → AR 38 = 25.0cm = US H7 / US M8.5 / EU 38';
GO
