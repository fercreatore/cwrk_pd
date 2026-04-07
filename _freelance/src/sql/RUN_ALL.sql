-- ============================================================================
-- SISTEMA VENDEDOR FREELANCE — EJECUCIÓN COMPLETA
-- ============================================================================
--
-- Script maestro que ejecuta en orden:
--   1. 001_crear_tablas_freelance.sql  — Creación de tablas base
--   2. 002_seed_data.sql               — Catálogo comercial (30+ SKUs)
--   3. 003_alta_mati.sql               — Alta de Matías Rodríguez (V755)
--
-- Ejecutar en: omicronvt database
-- Servidor: 192.168.2.111 (producción) o 192.168.2.112 (desarrollo)
--
-- Fecha: 23 de marzo de 2026
--
-- ============================================================================
-- INSTRUCCIONES DE EJECUCIÓN:
-- ============================================================================
--
-- Opción 1 — Desde SQL Server Management Studio:
--   1. Abrir este archivo (RUN_ALL.sql)
--   2. Conectar a omicronvt database
--   3. Ctrl+Shift+E para ejecutar como batch
--
-- Opción 2 — Desde línea de comandos (sqlcmd):
--   sqlcmd -S 192.168.2.111 -U am -P dl -d omicronvt -i RUN_ALL.sql
--
-- Opción 3 — Desde PowerShell:
--   $server = "192.168.2.111"
--   $db = "omicronvt"
--   $user = "am"
--   $pass = "dl"
--   sqlcmd -S $server -U $user -P $pass -d $db -i "C:\cowork_pedidos\_freelance\src\sql\RUN_ALL.sql"
--
-- ============================================================================

USE omicronvt;
GO

PRINT '';
PRINT '╔═══════════════════════════════════════════════════════════════════════════╗';
PRINT '║ SISTEMA VENDEDOR FREELANCE — EJECUCIÓN COMPLETA                          ║';
PRINT '║ Fecha: 23 de marzo de 2026                                               ║';
PRINT '╚═══════════════════════════════════════════════════════════════════════════╝';
PRINT '';
PRINT 'Este script ejecutará en orden:';
PRINT '  1. Creación de tablas base (7 tablas)';
PRINT '  2. Seed data del catálogo comercial (30+ SKUs)';
PRINT '  3. Alta de Matías Rodríguez (viajante_cod=755)';
PRINT '';
PRINT '────────────────────────────────────────────────────────────────────────────';
PRINT '';
GO

-- ════════════════════════════════════════════════════════════════════════════
-- SECCIÓN 1: CREAR TABLAS FREELANCE
-- ════════════════════════════════════════════════════════════════════════════

PRINT '[1/3] Creando tablas del sistema freelance...';
PRINT '';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 1.1 VENDEDOR FREELANCE (extiende viajantes con datos de monotributo/freelance)
-- ────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'vendedor_freelance')
BEGIN
    CREATE TABLE dbo.vendedor_freelance (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        viajante_cod    INT NOT NULL,              -- FK logica → viajantes.codigo
        cuit            VARCHAR(13) NULL,
        razon_social    NVARCHAR(100) NULL,
        categoria_mono  VARCHAR(2) NULL,           -- A, B, C, D, E, F, G, H, I, J, K
        cuota_mono      DECIMAL(12,2) NULL,        -- cuota mensual del monotributo
        fee_pct_std     DECIMAL(5,4) DEFAULT 0.05, -- 5% fee estandar
        fee_pct_premium DECIMAL(5,4) DEFAULT 0.08, -- 8% fee premium
        instagram       VARCHAR(100) NULL,
        whatsapp        VARCHAR(20) NULL,
        codigo_atrib    VARCHAR(10) NOT NULL,       -- codigo unico de atribucion: V569
        canon_mensual   DECIMAL(12,2) DEFAULT 0,   -- alquiler del espacio
        fecha_inicio    DATE NULL,
        activo          BIT DEFAULT 1,
        fecha_alta      DATETIME DEFAULT GETDATE(),
        fecha_modif     DATETIME DEFAULT GETDATE(),
        CONSTRAINT UQ_vf_viajante UNIQUE (viajante_cod),
        CONSTRAINT UQ_vf_codigo   UNIQUE (codigo_atrib)
    );
    PRINT '  ✓ Tabla vendedor_freelance creada';
END
ELSE
    PRINT '  ~ Tabla vendedor_freelance ya existe';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 1.2 FRANJAS DE INCENTIVO (bonus por hora del dia / dia de la semana)
-- ────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'franjas_incentivo')
BEGIN
    CREATE TABLE dbo.franjas_incentivo (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        dia_semana      TINYINT NOT NULL,          -- 1=Lunes, 2=Martes, ..., 6=Sabado, 7=Domingo
        hora_desde      VARCHAR(5) NOT NULL,       -- 'HH:MM' (TIME no soportado bien en 2012)
        hora_hasta      VARCHAR(5) NOT NULL,
        bonus_fee_pct   DECIMAL(5,4) NOT NULL,     -- bonus adicional sobre fee base
        descripcion     VARCHAR(50) NULL
    );

    -- Franjas iniciales: bonus en horas muertas
    INSERT INTO dbo.franjas_incentivo (dia_semana, hora_desde, hora_hasta, bonus_fee_pct, descripcion) VALUES
    -- Lunes a viernes
    (1, '09:00', '12:00', 0.00, 'Lun manana - sin bonus'),
    (1, '12:00', '16:00', 0.02, 'Lun hora muerta +2%'),
    (1, '16:00', '20:00', 0.00, 'Lun tarde - sin bonus'),
    (2, '09:00', '12:00', 0.00, 'Mar manana'),
    (2, '12:00', '16:00', 0.02, 'Mar hora muerta +2%'),
    (2, '16:00', '20:00', 0.00, 'Mar tarde'),
    (3, '09:00', '12:00', 0.00, 'Mie manana'),
    (3, '12:00', '16:00', 0.02, 'Mie hora muerta +2%'),
    (3, '16:00', '20:00', 0.00, 'Mie tarde'),
    (4, '09:00', '12:00', 0.00, 'Jue manana'),
    (4, '12:00', '16:00', 0.02, 'Jue hora muerta +2%'),
    (4, '16:00', '20:00', 0.00, 'Jue tarde'),
    (5, '09:00', '12:00', 0.00, 'Vie manana'),
    (5, '12:00', '16:00', 0.02, 'Vie hora muerta +2%'),
    (5, '16:00', '20:00', 0.00, 'Vie tarde'),
    -- Sabado: todo con bonus (dia dificil de cubrir)
    (6, '09:00', '13:00', 0.01, 'Sab manana +1%'),
    (6, '16:00', '20:00', 0.01, 'Sab tarde +1%');

    PRINT '  ✓ Tabla franjas_incentivo creada con datos iniciales';
END
ELSE
    PRINT '  ~ Tabla franjas_incentivo ya existe';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 1.3 CATALOGO COMERCIAL (fotos + contenido para redes, por SKU base)
-- ────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'catalogo_comercial')
BEGIN
    CREATE TABLE dbo.catalogo_comercial (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        sku_base        VARCHAR(20) NOT NULL,      -- ej: '21872' (primeros 5 chars de descripcion_1)
        titulo_corto    NVARCHAR(100) NULL,        -- "Topper Xforcer Negro"
        descripcion_redes NVARCHAR(500) NULL,      -- texto para Instagram/WA
        hashtags        NVARCHAR(200) NULL,        -- "#zapatillas #topper #running"
        categoria_fee   VARCHAR(10) DEFAULT 'STD', -- STD=fee_pct_std, PREMIUM=fee_pct_premium
        fotos_path      VARCHAR(500) NULL,         -- ruta carpeta de fotos en servidor
        foto_principal  VARCHAR(200) NULL,         -- nombre archivo foto principal
        marca_cod       INT NULL,                  -- FK logica → marcas.codigo
        activo          BIT DEFAULT 1,
        fecha_alta      DATETIME DEFAULT GETDATE(),
        fecha_modif     DATETIME DEFAULT GETDATE()
    );
    CREATE INDEX IX_cat_sku ON dbo.catalogo_comercial(sku_base);
    CREATE INDEX IX_cat_marca ON dbo.catalogo_comercial(marca_cod);
    PRINT '  ✓ Tabla catalogo_comercial creada';
END
ELSE
    PRINT '  ~ Tabla catalogo_comercial ya existe';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 1.4 VENTA ATRIBUCION (tracking de que vendedor genero cada venta)
-- ────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'venta_atribucion')
BEGIN
    CREATE TABLE dbo.venta_atribucion (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        -- Referencia a la venta en el ERP
        empresa         VARCHAR(10) NULL,
        vta_codigo      INT NULL,
        vta_letra       CHAR(1) NULL,
        vta_sucursal    INT NULL,
        vta_numero      INT NULL,
        vta_orden       INT NULL,
        -- Atribucion
        vendedor_id     INT NOT NULL,              -- FK → vendedor_freelance.id
        canal_origen    VARCHAR(20) NOT NULL,       -- INSTAGRAM, WHATSAPP, PRESENCIAL, ML, WEB, TIKTOK
        link_usado      VARCHAR(200) NULL,
        fecha           DATETIME DEFAULT GETDATE(),
        hora_venta      VARCHAR(5) NULL,           -- 'HH:MM' para calcular franja
        -- Montos
        monto_producto  DECIMAL(14,2) NULL,        -- total facturado H4 (producto)
        cant_pares      INT NULL,
        -- Fee calculado
        fee_pct_base    DECIMAL(5,4) NULL,         -- % base (STD o PREMIUM)
        bonus_franja    DECIMAL(5,4) DEFAULT 0,    -- bonus por franja horaria
        fee_pct_total   DECIMAL(5,4) NULL,         -- base + bonus
        fee_monto       DECIMAL(12,2) NULL,        -- monto_producto * fee_pct_total
        -- Estado
        estado_factura  VARCHAR(10) DEFAULT 'PEND', -- PEND, BORRADOR, EMITIDO, PAGADO
        factura_cae     VARCHAR(20) NULL,
        fecha_emision   DATETIME NULL
    );
    CREATE INDEX IX_atrib_vendedor ON dbo.venta_atribucion(vendedor_id);
    CREATE INDEX IX_atrib_fecha ON dbo.venta_atribucion(fecha);
    CREATE INDEX IX_atrib_estado ON dbo.venta_atribucion(estado_factura);
    CREATE INDEX IX_atrib_venta ON dbo.venta_atribucion(empresa, vta_codigo, vta_letra, vta_sucursal, vta_numero, vta_orden);
    PRINT '  ✓ Tabla venta_atribucion creada';
END
ELSE
    PRINT '  ~ Tabla venta_atribucion ya existe';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 1.5 CLIENTE VENDEDOR (CRM minimo del vendedor)
-- ────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'cliente_vendedor')
BEGIN
    CREATE TABLE dbo.cliente_vendedor (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        vendedor_id     INT NOT NULL,              -- FK → vendedor_freelance.id
        cliente_nombre  NVARCHAR(100) NULL,
        cliente_tel     VARCHAR(20) NULL,
        cliente_ig      VARCHAR(50) NULL,
        cliente_email   VARCHAR(100) NULL,
        primera_compra  DATE NULL,
        ultima_compra   DATE NULL,
        total_compras   INT DEFAULT 0,
        total_monto     DECIMAL(14,2) DEFAULT 0,
        notas           NVARCHAR(500) NULL,
        fecha_alta      DATETIME DEFAULT GETDATE()
    );
    CREATE INDEX IX_cliv_vendedor ON dbo.cliente_vendedor(vendedor_id);
    PRINT '  ✓ Tabla cliente_vendedor creada';
END
ELSE
    PRINT '  ~ Tabla cliente_vendedor ya existe';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 1.6 CONTENIDO GENERADO (posts listos para compartir por vendedor)
-- ────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'contenido_generado')
BEGIN
    CREATE TABLE dbo.contenido_generado (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        sku_base        VARCHAR(20) NOT NULL,
        vendedor_id     INT NOT NULL,              -- FK → vendedor_freelance.id
        canal           VARCHAR(20) NOT NULL,      -- INSTAGRAM, WHATSAPP, ML, TN
        contenido_texto NVARCHAR(MAX) NULL,
        contenido_imagen VARCHAR(200) NULL,        -- path imagen generada
        link_atribucion VARCHAR(200) NULL,         -- h4calzados.com/p/21872?v=569
        estado          VARCHAR(10) DEFAULT 'LISTO', -- LISTO, COMPARTIDO, EXPIRADO
        fecha_gen       DATETIME DEFAULT GETDATE(),
        fecha_compart   DATETIME NULL
    );
    CREATE INDEX IX_cont_vendedor ON dbo.contenido_generado(vendedor_id, estado);
    CREATE INDEX IX_cont_sku ON dbo.contenido_generado(sku_base);
    PRINT '  ✓ Tabla contenido_generado creada';
END
ELSE
    PRINT '  ~ Tabla contenido_generado ya existe';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 1.7 LIQUIDACION VENDEDOR (cierre mensual)
-- ────────────────────────────────────────────────────────────────────────────
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'liquidacion_vendedor')
BEGIN
    CREATE TABLE dbo.liquidacion_vendedor (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        vendedor_id     INT NOT NULL,
        periodo_anio    INT NOT NULL,
        periodo_mes     INT NOT NULL,
        -- Totales de ventas
        ventas_producto DECIMAL(14,2) DEFAULT 0,   -- total facturado H4 por sus ventas
        cant_operaciones INT DEFAULT 0,
        cant_pares      INT DEFAULT 0,
        -- Fee
        total_fee_base  DECIMAL(14,2) DEFAULT 0,   -- suma de fees base
        total_bonus     DECIMAL(14,2) DEFAULT 0,   -- suma de bonus por franja
        total_fee       DECIMAL(14,2) DEFAULT 0,   -- fee_base + bonus
        -- Deducciones
        canon_espacio   DECIMAL(14,2) DEFAULT 0,
        cuota_mono      DECIMAL(14,2) DEFAULT 0,
        -- Neto
        neto_estimado   DECIMAL(14,2) DEFAULT 0,   -- total_fee - canon - cuota_mono
        -- Control
        estado          VARCHAR(10) DEFAULT 'BORR', -- BORR, CERRADA, APROBADA, PAGADA
        fecha_cierre    DATETIME NULL,
        fecha_aprobacion DATETIME NULL,
        fecha_pago      DATETIME NULL,
        observaciones   NVARCHAR(500) NULL,
        CONSTRAINT UQ_liq_periodo UNIQUE (vendedor_id, periodo_anio, periodo_mes)
    );
    CREATE INDEX IX_liq_vendedor ON dbo.liquidacion_vendedor(vendedor_id);
    CREATE INDEX IX_liq_periodo ON dbo.liquidacion_vendedor(periodo_anio, periodo_mes);
    PRINT '  ✓ Tabla liquidacion_vendedor creada';
END
ELSE
    PRINT '  ~ Tabla liquidacion_vendedor ya existe';
GO

PRINT '';
PRINT '────────────────────────────────────────────────────────────────────────────';
PRINT '';

-- ════════════════════════════════════════════════════════════════════════════
-- SECCIÓN 2: SEED DATA - CATÁLOGO COMERCIAL
-- ════════════════════════════════════════════════════════════════════════════

PRINT '[2/3] Insertando seed data (catálogo comercial 30+ SKUs)...';
PRINT '';
GO

-- Topper (marca_cod = 314)
IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '21872')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('21872', 'Topper X Forcer Negro', 'Zapatilla de running ultraligera Topper X Forcer. Diseño exclusivo con suela reactiva de última generación. Perfecta para entrenamientos intensos y competencias.', '#topper #running #zapatillas #deportes #velocidad', 'STD', 314, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '21873')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('21873', 'Topper X Forcer Blanco', 'Topper X Forcer en blanco puro. Máxima comodidad con tecnología air mesh transpirable. Ideal para running y actividades deportivas diarias.', '#topper #white #running #zapatillas #confort', 'STD', 314, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '21874')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('21874', 'Topper Reborn LT', 'Topper Reborn LT con amortiguación premium. Peso ultra reducido para deportistas que buscan velocidad sin sacrificar soporte. Rebote energético garantizado.', '#topper #running #lightweight #reborn #velocidad', 'PREMIUM', 314, 1);
END

-- Reebok (marca_cod = 513)
IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '10210')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('10210', 'Reebok Nano X3 Gris', 'Reebok Nano X3 gris especial para crossfit. Suela Flexweave de máxima adherencia. Perfecta para entrenamientos de alta intensidad y competencias.', '#reebok #nanox3 #crossfit #fitness #entrenamiento', 'PREMIUM', 513, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '10211')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('10211', 'Reebok Nano X3 Negro', 'Reebok Nano X3 en negro total. Construcción robusta con refuerzos en puntos críticos. La opción premium para crossfiteros serios.', '#reebok #nanox3 #crossfit #negro #gym', 'PREMIUM', 513, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '10212')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('10212', 'Reebok Energylux Negro', 'Reebok Energylux con tecnología DMX foam para máxima comodidad. Ideal para correr o caminar todo el día sin cansancio en los pies.', '#reebok #energylux #comfort #running #everyday', 'STD', 513, 1);
END

-- Diadora (marca_cod = 675)
IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '15630')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('15630', 'Diadora Flamingo Violeta', 'Diadora Flamingo en violeta intenso. Zapatilla versátil para tenis y actividades casual-sport. Comodidad todo el día con estilo moderno.', '#diadora #flamingo #tenis #violeta #deportivo', 'STD', 675, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '15631')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('15631', 'Diadora Flamingo Rosa', 'Diadora Flamingo en rosa pastel. Perfecto para tenis o uso casual con un toque deportivo femenino. Ligero y muy cómodo.', '#diadora #flamingo #rosa #tenis #femenino', 'STD', 675, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '15632')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('15632', 'Diadora Robin Blanco', 'Diadora Robin blanco inmaculado. Zapatilla elegante y versátil para cualquier ocasión. Suela antideslizante y refuerzo superior en piel.', '#diadora #robin #blanco #elegante #casual', 'STD', 675, 1);
END

-- VICBOR / ATOMIK (marca_cod = 594)
IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '22140')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('22140', 'Atomik Runflex Negro', 'Atomik Runflex diseño deportivo. Zapatilla de running con flexibilidad premium en suela. Excelente relación precio-rendimiento.', '#atomik #runflex #running #negro #deportes', 'STD', 594, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '22141')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('22141', 'Atomik Runflex Gris', 'Atomik Runflex gris combinado. Running moderno con amortiguación balanceada. Ideal para entrenamientos regulares y competencias cortas.', '#atomik #runflex #gris #running #entreno', 'STD', 594, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '22142')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('22142', 'Atomik Wake Azul', 'Atomik Wake azul exclusivo. Zapatilla multiusos con diseño casual-deportivo. Excelente para usar en la ciudad y en deportes recreativos.', '#atomik #wake #azul #casual #multiuso', 'STD', 594, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '22143')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('22143', 'Atomik Wake Rojo', 'Atomik Wake rojo fuego. Zapatilla versátil y cómoda para cualquier actividad. Color atrevido y diseño moderno.', '#atomik #wake #rojo #casual #trendy', 'STD', 594, 1);
END

-- RINGO / Souter (marca_cod = 294)
IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '30510')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('30510', 'Carmel Ringo Café', 'Carmel Ringo color café chocolate. Comodidad premium con diseño elegante para uso casual y profesional. Cuero natural y suave.', '#ringo #carmel #cafe #confort #elegante', 'STD', 294, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '30511')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('30511', 'Carmel Ringo Negro', 'Carmel Ringo negro clásico. Zapatilla deportiva con soporte ortopédico. Perfecta para caminar todo el día sin fatiga.', '#ringo #carmel #negro #comfort #casual', 'STD', 294, 1);
END

-- GTN / El Gitano (marca_cod = 104)
IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '11005')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('11005', 'El Gitano GTN Blanco', 'El Gitano GTN blanco puro. Zapatilla clásica de tenis con excelente comodidad. La marca favorita de los argentinos.', '#gitano #gtn #blanco #tenis #clasico', 'STD', 104, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '11006')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('11006', 'El Gitano GTN Gris', 'El Gitano GTN gris deportivo. Zapatilla versátil para tenis, running o uso casual. Comodidad garantizada con diseño atemporal.', '#gitano #gtn #gris #deportivo #casual', 'STD', 104, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '11007')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('11007', 'El Gitano GTN Negro', 'El Gitano GTN negro total. Zapatilla de tenis profesional con soporte lateral reforzado. Elegancia y deportividad en un solo modelo.', '#gitano #gtn #negro #tenis #profesional', 'STD', 104, 1);
END

-- Distrinando / Reebok (marca_cod = 513)
IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '18520')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('18520', 'Reebok Club C Blanco', 'Reebok Club C clásico en blanco. Zapatilla icónica de tenis con diseño retro moderno. Comodidad premium para uso casual y deportivo.', '#reebok #clubc #blanco #retro #casual', 'STD', 513, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '18521')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('18521', 'Reebok Club C Negro', 'Reebok Club C negro total. Versión monocromática del clásico. Zapatilla versátil que combina con todo.', '#reebok #clubc #negro #classic #allblack', 'STD', 513, 1);
END

-- Alpargatas / Topper (marca_cod = 314)
IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '25890')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('25890', 'Topper Zapatilla Lona Blanca', 'Topper clásico en lona blanca. Ligero y transpirable para verano. Ideal para los fans del estilo retro y casual.', '#topper #lona #blanco #retro #verano', 'STD', 314, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '25891')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('25891', 'Topper Zapatilla Lona Negra', 'Topper clásico en lona negra. La opción monocromática del favorito de varias generaciones. Comodidad casual garantizada.', '#topper #lona #negro #casual #clasico', 'STD', 314, 1);
END

-- Adicionales variados para completar catálogo
IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '20001')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('20001', 'Topper Sprinter Plus Rojo', 'Topper Sprinter Plus rojo intenso. Running performance con suela reactiva. Velocidad sin compromiso de comodidad.', '#topper #sprinter #rojo #running #velocidad', 'PREMIUM', 314, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '20002')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('20002', 'Reebok Nano X3 Blanco', 'Reebok Nano X3 blanco puro. Crossfit de nivel profesional con máxima estabilidad. La elección de atletas serios.', '#reebok #nanox3 #blanco #crossfit #elite', 'PREMIUM', 513, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '20003')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('20003', 'Diadora Robin Gris', 'Diadora Robin gris moderno. Zapatilla versátil con excelente comodidad para todo el día. Diseño elegante y actual.', '#diadora #robin #gris #casual #confort', 'STD', 675, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '20004')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('20004', 'Atomik Jump X Verde', 'Atomik Jump X verde deportivo. Zapatilla de basquet con amortiguación lateral. Ideal para juegos casuales y entrenamientos.', '#atomik #jump #basquet #verde #deportes', 'STD', 594, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '20005')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('20005', 'Carmel Ringo Marrón', 'Carmel Ringo marrón caramelo. Cuero premium con soporte ortopédico. Elegancia y comodidad para los que valoran la calidad.', '#ringo #carmel #marron #elegante #premium', 'STD', 294, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '20006')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('20006', 'El Gitano GTN Azul', 'El Gitano GTN azul celeste. Tenis deportivo con diseño juvenil. Comodidad y estilo para el día a día.', '#gitano #gtn #azul #tenis #casual', 'STD', 104, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '20007')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('20007', 'Reebok Energylux Blanco', 'Reebok Energylux blanco clásico. Running diario con máxima amortiguación. Confort premium para deportistas constantes.', '#reebok #energylux #blanco #running #comfort', 'STD', 513, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '20008')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('20008', 'Topper Fusion Tech Naranja', 'Topper Fusion Tech naranja llamativo. Running moderno con tecnología mesh de nueva generación. Ligereza y transpirabilidad sin igual.', '#topper #fusion #naranja #running #tech', 'PREMIUM', 314, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '20009')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('20009', 'Diadora Flamingo Blanco', 'Diadora Flamingo blanco limpio. Zapatilla de tenis femenina con diseño moderno. Ligereza y estabilidad para cualquier movimiento.', '#diadora #flamingo #blanco #tenis #femenino', 'STD', 675, 1);
END

IF NOT EXISTS (SELECT 1 FROM dbo.catalogo_comercial WHERE sku_base = '20010')
BEGIN
    INSERT INTO dbo.catalogo_comercial (sku_base, titulo_corto, descripcion_redes, hashtags, categoria_fee, marca_cod, activo)
    VALUES ('20010', 'Atomik Peak Running Amarillo', 'Atomik Peak Running amarillo vibrante. Running de competencia con suela de carbono. Velocidad máxima para atletas comprometidos.', '#atomik #peak #amarillo #running #competencia', 'PREMIUM', 594, 1);
END

PRINT '  ✓ Catálogo comercial insertado (30+ SKUs)';
PRINT '';
PRINT '────────────────────────────────────────────────────────────────────────────';
PRINT '';

-- ════════════════════════════════════════════════════════════════════════════
-- SECCIÓN 3: ALTA DE MATÍAS RODRÍGUEZ
-- ════════════════════════════════════════════════════════════════════════════

PRINT '[3/3] Insertando Matías Rodríguez (V755)...';
PRINT '';
GO

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
        NULL,                   -- cuit (pendiente)
        NULL,                   -- razon_social (pendiente)
        NULL,                   -- instagram (pendiente)
        NULL                    -- whatsapp (pendiente)
    );
    PRINT '  ✓ Matías Rodríguez (V755) insertado exitosamente';
END
ELSE
BEGIN
    PRINT '  ~ Matías Rodríguez (V755) ya existe';
END
GO

PRINT '';
PRINT '────────────────────────────────────────────────────────────────────────────';
PRINT '';

-- ════════════════════════════════════════════════════════════════════════════
-- RESUMEN FINAL
-- ════════════════════════════════════════════════════════════════════════════

PRINT '╔═══════════════════════════════════════════════════════════════════════════╗';
PRINT '║ EJECUCIÓN COMPLETA DEL SISTEMA FREELANCE - RESUMEN                       ║';
PRINT '╚═══════════════════════════════════════════════════════════════════════════╝';
PRINT '';

PRINT 'Tablas creadas:';
SELECT COUNT(*) AS total_tablas FROM sys.tables WHERE type = 'U' AND name LIKE '%freelance%' OR name LIKE '%catalogo%' OR name LIKE '%venta_atribucion%' OR name LIKE '%cliente_vendedor%' OR name LIKE '%contenido_generado%' OR name LIKE '%liquidacion%';

PRINT '';
PRINT 'Catálogo comercial:';
SELECT COUNT(*) AS total_skus, COUNT(DISTINCT marca_cod) AS marcas FROM dbo.catalogo_comercial WHERE activo = 1;

PRINT '';
PRINT 'Vendedores freelance:';
SELECT id, viajante_cod, codigo_atrib, categoria_mono, cuota_mono, activo, fecha_inicio FROM dbo.vendedor_freelance ORDER BY viajante_cod;

PRINT '';
PRINT 'Franjas de incentivo:';
SELECT COUNT(*) AS total_franjas FROM dbo.franjas_incentivo;

PRINT '';
PRINT '═══════════════════════════════════════════════════════════════════════════';
PRINT ' Sistema freelance listo para usar.';
PRINT '═══════════════════════════════════════════════════════════════════════════';
PRINT '';
GO
