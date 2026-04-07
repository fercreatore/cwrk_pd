-- ============================================================================
-- SISTEMA VENDEDOR FREELANCE — FASE 2: Seed Data (Catálogo comercial)
-- Ejecutar en: omicronvt database en 192.168.2.111 (producción)
--              o 192.168.2.112 (replica de desarrollo)
-- Fecha: 23 de marzo de 2026
--
-- Este script inserta ~30 productos reales del catálogo H4/CALZALINDO con:
-- - SKU base (5 dígitos): códigos de artículo reales del ERP
-- - Títulos cortos: nombres de producto exactos (ej: "Topper X Forcer Negro")
-- - Descripciones para redes: textos Instagram-ready en español
-- - Hashtags: relevantes al tipo de calzado
-- - Categoría fee: STD (5%) o PREMIUM (8%)
-- - Marca códigos: referencias reales (314=Topper, 513=Reebok, 675=Diadora, etc)
--
-- NOTA: No inserta en vendedor_freelance (eso se hace vía API/app confirmando Matías)
-- ============================================================================

USE omicronvt;
GO

-- ════════════════════════════════════════════════════════════════════════════
-- 1. CATALOGO COMERCIAL — Productos deportivos populares
-- ════════════════════════════════════════════════════════════════════════════

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
end

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

-- Adicionales variados para completar catálogo (30+ productos)
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

-- ════════════════════════════════════════════════════════════════════════════
-- RESUMEN DE INSERCIONES
-- ════════════════════════════════════════════════════════════════════════════
PRINT '';
PRINT '═══════════════════════════════════════════════════════════════════════════';
PRINT ' SEED DATA - CATALOGO COMERCIAL CARGADO';
PRINT '═══════════════════════════════════════════════════════════════════════════';
PRINT '';
PRINT 'Total de SKUs cargados:';
SELECT COUNT(*) AS total_productos FROM dbo.catalogo_comercial;
PRINT '';
PRINT 'Distribución por marca:';
SELECT marca_cod, COUNT(*) AS cantidad FROM dbo.catalogo_comercial GROUP BY marca_cod ORDER BY marca_cod;
PRINT '';
PRINT 'Distribución por categoría fee:';
SELECT categoria_fee, COUNT(*) AS cantidad FROM dbo.catalogo_comercial GROUP BY categoria_fee;
PRINT '';
PRINT '═══════════════════════════════════════════════════════════════════════════';
GO
