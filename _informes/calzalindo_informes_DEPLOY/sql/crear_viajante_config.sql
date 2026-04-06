-- =============================================================================
-- crear_viajante_config.sql
-- Crear tabla viajante_config en omicronvt
-- Ejecutar en servidor 111: py -3 -c "import pyodbc; ..." o via SSMS
-- =============================================================================

USE omicronvt;
GO

-- Crear tabla si no existe
IF NOT EXISTS (
    SELECT 1 FROM sys.tables WHERE name = 'viajante_config' AND schema_id = SCHEMA_ID('dbo')
)
BEGIN
    CREATE TABLE dbo.viajante_config (
        viajante_codigo    INT           NOT NULL,
        nombre             VARCHAR(100)  NOT NULL,
        tipo               VARCHAR(20)   NOT NULL DEFAULT 'individual',
            -- 'individual':  vendedor de piso con usuario propio
            -- 'grupal':      cuenta compartida historica (REFUERZO, etc.)
            -- 'excluido':    no incluir en ningun analisis (directivos, remitos)
            -- 'ml':          operador canal digital (ML, TiendaNube) — benchmark separado, dep 1
            -- 'encargado':   vendedor promovido a encargado de local — excluir del benchmark de
            --                vendedores de piso; su KPI es gestion del local, no venta individual
        auth_user_id       INT           NULL,     -- vinculo con clz_ventas_sql.auth_user
        deposito_principal INT           NULL,
        activo             BIT           NOT NULL DEFAULT 1,
        observaciones      VARCHAR(500)  NULL,
        fecha_alta         DATE          NOT NULL DEFAULT GETDATE(),
        fecha_baja         DATE          NULL,
        CONSTRAINT PK_viajante_config PRIMARY KEY (viajante_codigo),
        CONSTRAINT CK_viajante_config_tipo CHECK (tipo IN ('individual', 'grupal', 'excluido', 'ml', 'encargado'))
    );
    PRINT 'Tabla viajante_config creada.';
END
ELSE
BEGIN
    PRINT 'Tabla viajante_config ya existe — se omite CREATE.';
END
GO

-- =============================================================================
-- Poblar con datos conocidos (INSERT solo si no existe el codigo)
-- =============================================================================

-- Remitos internos — excluir siempre
IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 7)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (7, 'REMITO INTERNO 7', 'excluido', 'Remito interno - excluir siempre');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 36)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (36, 'REMITO INTERNO 36', 'excluido', 'Remito interno - excluir siempre');

-- Dueno — no vendedor
IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 1)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (1, 'Fer Calaianov', 'excluido', 'Duenio - no vendedor');

-- Cuentas grupales
IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 65)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (65, 'ASESORAS CENTRAL', 'grupal', 'Cuenta grupal promotoras dep 0');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 20)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (20, 'REFUERZO 1', 'grupal', 'Cuenta grupal ingresantes');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 21)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (21, 'REFUERZO 2', 'grupal', 'Cuenta grupal ingresantes');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 22)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (22, 'REFUERZO 3', 'grupal', 'Cuenta grupal ingresantes');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 23)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (23, 'REFUERZO 4', 'grupal', 'Cuenta grupal ingresantes');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 24)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (24, 'REFUERZO 5', 'grupal', 'Cuenta grupal ingresantes');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 25)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (25, 'REFUERZO 6', 'grupal', 'Cuenta grupal ingresantes');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 26)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (26, 'REFUERZO 7', 'grupal', 'Cuenta grupal ingresantes');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 28)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (28, 'REFUERZO 9', 'grupal', 'Cuenta grupal ingresantes');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 29)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (29, 'REFUERZO 10', 'grupal', 'Cuenta grupal ingresantes');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 30)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (30, 'REFUERZO 11', 'grupal', 'Cuenta grupal ingresantes');

-- =============================================================================
-- Canal digital (dep 1) — ML + TiendaNube — benchmark separado
-- =============================================================================
IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 545)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, deposito_principal, observaciones)
    VALUES (545, 'Bilicich Tomas', 'ml', 1, 'Responsable canal digital (ML+TN). No es vendedor de piso. Evaluar por GMV, fulfillment, unidades, no por ticket presencial.');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 585)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, deposito_principal, observaciones)
    VALUES (585, 'Berri M.Belen', 'ml', 1, 'Operadora canal digital dep 1 (ML+TN). Equipo: Bilicich + Berri.');

-- =============================================================================
-- Encargados de local y personal no comercial (roles internos)
-- =============================================================================
-- Galvan Tamara: promovida a supervisora de todos los locales (inc. Junin).
-- KPI: gestion de equipo, conversion de local, stock — NO venta individual.
IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 68)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (68, 'Galvan Tamara', 'encargado', 'Supervisora de todos los locales. Monitorea dep 0, 8 y resto. KPI: gestion equipo, conversion local, stock. No evaluar por venta individual.');
ELSE
    UPDATE dbo.viajante_config
    SET observaciones = 'Supervisora de todos los locales. Monitorea dep 0, 8 y resto. KPI: gestion equipo, conversion local, stock. No evaluar por venta individual.'
    WHERE viajante_codigo = 68;

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 259)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (259, 'Mariana Lopez', 'excluido', 'Encargada de compras — rol administrativo, no vendedora de piso.');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 632)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (632, 'LUCIA GARCIA', 'excluido', 'Comunicacion Junin — rol no comercial.');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 711)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (711, 'reyes rocio', 'excluido', 'Redes y comunicaciones dep 0 (equipo Lucrecia) — rol no comercial.');

IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 305)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, observaciones)
    VALUES (305, 'Rocio Amigo', 'excluido', 'Comunicaciones (equipo Lucrecia) — rol no comercial.');

-- Juan Ignacio Ramirez: compras, usaba usuario stock@calzalindo.com.ar hasta ene-2025
-- dep 12 es su deposito operativo (no es un local de venta al publico)
IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 12)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, deposito_principal, observaciones)
    VALUES (12, 'Juan Ignacio Ramirez', 'excluido', 12, 'Compras. Usuario stock@calzalindo.com.ar hasta ene-2025. Dep 12 = deposito operativo interno.');

-- Aguirre Evelyn: ex-encargada dep 8 (Junin). Se fue abril 2026.
-- Estaba estudiando, performance cayo antes de la salida.
IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 595)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, deposito_principal, activo, fecha_baja, observaciones)
    VALUES (595, 'Aguirre Evelyn', 'encargado', 8, 0, '2026-04-01', 'Ex-encargada dep 8 (Junin). Salio apr-2026. Estaba estudiando, performance cayo antes de la salida. Reemplazada por supervision de Galvan.');

-- Rocio Garay: encargada de central dep 0. Gestiona pedidos entrantes de la app (estanteria virtual / app 109).
-- No es vendedora de piso — su funcion es operativa/gestion.
IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 707)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, deposito_principal, observaciones)
    VALUES (707, 'Garay Rocio Celeste', 'encargado', 0, 'Encargada de central dep 0. Gestiona pedidos de la app (estanteria virtual / app 109). Rol operativo, no vendedora de piso.');

-- Torancio Romina: vende en dep 10 (Murphy) Y coordina red de asesoras freelance.
-- Doble rol: incluir en benchmark freelance dep 10, pero sus numeros mezclan venta propia + efecto red.
IF NOT EXISTS (SELECT 1 FROM dbo.viajante_config WHERE viajante_codigo = 586)
    INSERT INTO dbo.viajante_config (viajante_codigo, nombre, tipo, deposito_principal, observaciones)
    VALUES (586, 'Torancio Romina', 'individual', 10, 'Dep 10 (Murphy). Vende + coordina red de asesoras freelance. Doble rol: sus numeros mezclan venta propia y efecto de coordinacion. Incluir en benchmark freelance dep 10, no en benchmark piso.');

GO

SELECT viajante_codigo, nombre, tipo, deposito_principal, activo, observaciones
FROM dbo.viajante_config
ORDER BY tipo, viajante_codigo;
