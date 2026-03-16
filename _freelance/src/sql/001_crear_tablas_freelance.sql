-- ============================================================================
-- SISTEMA VENDEDOR FREELANCE — FASE 1: Tablas base
-- Ejecutar en: omicronvt (primero en .112 replica, luego en .111 produccion)
-- Fecha: 6 de marzo de 2026
-- ============================================================================

USE omicronvt;
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 1. VENDEDOR FREELANCE (extiende viajantes con datos de monotributo/freelance)
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
    PRINT 'Tabla vendedor_freelance creada OK';
END
ELSE
    PRINT 'Tabla vendedor_freelance ya existe';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 2. FRANJAS DE INCENTIVO (bonus por hora del dia / dia de la semana)
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

    PRINT 'Tabla franjas_incentivo creada e inicializada OK';
END
ELSE
    PRINT 'Tabla franjas_incentivo ya existe';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 3. CATALOGO COMERCIAL (fotos + contenido para redes, por SKU base)
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
    PRINT 'Tabla catalogo_comercial creada OK';
END
ELSE
    PRINT 'Tabla catalogo_comercial ya existe';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 4. VENTA ATRIBUCION (tracking de que vendedor genero cada venta)
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
    PRINT 'Tabla venta_atribucion creada OK';
END
ELSE
    PRINT 'Tabla venta_atribucion ya existe';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 5. CLIENTE VENDEDOR (CRM minimo del vendedor)
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
    PRINT 'Tabla cliente_vendedor creada OK';
END
ELSE
    PRINT 'Tabla cliente_vendedor ya existe';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 6. CONTENIDO GENERADO (posts listos para compartir por vendedor)
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
    PRINT 'Tabla contenido_generado creada OK';
END
ELSE
    PRINT 'Tabla contenido_generado ya existe';
GO

-- ────────────────────────────────────────────────────────────────────────────
-- 7. LIQUIDACION VENDEDOR (cierre mensual)
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
    PRINT 'Tabla liquidacion_vendedor creada OK';
END
ELSE
    PRINT 'Tabla liquidacion_vendedor ya existe';
GO

PRINT '';
PRINT '═══════════════════════════════════════════════════';
PRINT ' TODAS LAS TABLAS DEL SISTEMA FREELANCE CREADAS';
PRINT '═══════════════════════════════════════════════════';
GO
