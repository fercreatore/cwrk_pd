# ARQUITECTURA: Sistema Vendedor Freelance Omnicanal — H4/Calzalindo

> Versión 1.0 — 6 de marzo de 2026
> Autor: Claude + Fernando Calaianov

---

## 1. ESTADO ACTUAL — QUÉ YA EXISTE

### 1.1 Infraestructura base
| Componente | Estado | Ubicación |
|-----------|--------|-----------|
| SQL Server 2012 (producción) | ✅ Operativo | 192.168.2.111 |
| SQL Server (réplica MCP) | ✅ Operativo | 192.168.2.112 |
| Web2py 2.24.1 + Python 2.7 | ✅ Operativo | 192.168.2.111:8000 |
| App `calzalindo_informes` | ✅ Desplegada | controllers, views, models, deploy.sh |
| Sistema de roles y auth | ✅ Funcional | db_access.py (admin, gerencia, compras, rrhh) |

### 1.2 Módulos funcionales existentes
| Módulo | Controller | Funcionalidades |
|--------|-----------|-----------------|
| **Pedidos y Remitos** | `reportes.py` (70K) | Dashboard KPIs, detalle proveedor, crear remitos (7 tablas), sync cache |
| **Calce Financiero** | `calce_financiero.py` (52K) | Dashboard, detalle por industria, exportar CSV |
| **Productividad** | `informes_productividad.py` (29K) | Dashboard RRHH, vendedor individual, incentivos, estacionalidad, ticket histórico |
| **Admin** | `admin_roles.py` (3.5K) | Gestión de usuarios y roles |
| **Carga de Pedidos** | `paso1-6*.py` (scripts) | Parseo Excel/PDF → INSERT en pedidos (Topper, GTN, genérico) |

### 1.3 Datos disponibles que ya alimentan el sistema
| Dato | Fuente | Acceso |
|------|--------|--------|
| Catálogo de artículos | `msgestion01art.dbo.articulo` (252 cols) | ✅ |
| Ventas por vendedor | `omicronvt.dbo.ventas1_vendedor` | ✅ |
| Sueldos reales | `msgestionC.dbo.moviempl1` | ✅ |
| Stock actual | `msgestionC.dbo.stock` / `omicronvt.dbo.stock_por_codigo` | ✅ |
| Marcas, subrubros, rubros | `msgestionC.dbo.marcas/subrubro/rubros` | ✅ |
| Precios (4 listas) | `articulo.precio_1..4` | ✅ |
| Viajantes (vendedores) | `msgestionC.dbo.viajantes` | ✅ |
| Turnos atendidos | `db5 (MySQL)` | ✅ (con try/except) |
| Fotos de productos | ❌ **NO EXISTE** | Falta módulo |
| Contenido comercial (descripciones redes) | ❌ **NO EXISTE** | Falta módulo |
| Atribución vendedor↔cliente | ❌ **NO EXISTE** | Falta módulo |
| Facturación dual (producto + servicio) | ❌ **NO EXISTE** | Falta módulo |
| Liquidación vendedores freelance | ❌ **NO EXISTE** | Falta módulo |

---

## 2. QUÉ FALTA — GAP ANALYSIS

### MÓDULOS NUEVOS NECESARIOS

```
┌─────────────────────────────────────────────────────────────────┐
│                    SISTEMA VENDEDOR FREELANCE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ M1: CATÁLOGO │  │ M2: PANEL    │  │ M3: GENERADOR        │  │
│  │  COMERCIAL   │──│  VENDEDOR    │──│  CONTENIDO OMNICANAL │  │
│  │  (fotos +    │  │  (dashboard  │  │  (IG/WA/ML/TN        │  │
│  │   descrip.)  │  │   personal)  │  │   auto-publish)      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────────┴───────────┐  │
│  │ M4: ATRIBU-  │  │ M5: FACTURA- │  │ M6: LIQUIDACIÓN      │  │
│  │  CIÓN Y      │──│  CIÓN DUAL   │──│  Y SETTLEMENT        │  │
│  │  TRACKING    │  │  (H4+vendor) │  │  (mensual)           │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│  ┌──────┴────────────────┴──────────────────────┴───────────┐  │
│  │              M7: DASHBOARD GERENCIAL FREELANCE            │  │
│  │        (KPIs red comercial, rentabilidad, proyección)     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │    M8: SIMULADOR MODELO FREELANCE (Excel actualizado)    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. ESPECIFICACIÓN DE CADA MÓDULO

---

### M1: CATÁLOGO COMERCIAL (fotos + contenido para redes)

**Problema que resuelve:** Hoy el catálogo es solo datos técnicos (SKU, talle, precio). Para publicar en redes sociales, alguien tiene que buscar fotos, escribir descripciones, armar el post manualmente. Esto no escala.

**Solución:** Extender el catálogo con campos comerciales y repositorio de imágenes.

**Tablas nuevas en `omicronvt`:**

```sql
-- Contenido comercial por artículo (agrupado por SKU base, no por talle)
CREATE TABLE omicronvt.dbo.catalogo_comercial (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    sku_base        VARCHAR(20) NOT NULL,      -- ej: '21872' (sin talle)
    titulo_corto    NVARCHAR(100),             -- "Topper Xforcer Negro"
    descripcion_redes NVARCHAR(500),           -- texto para Instagram/WA
    hashtags        NVARCHAR(200),             -- "#zapatillas #topper #running"
    categoria_fee   VARCHAR(10) DEFAULT 'STD', -- STD=5%, PREMIUM=8%
    fotos_path      VARCHAR(500),              -- ruta carpeta de fotos en servidor
    foto_principal  VARCHAR(200),              -- nombre archivo foto principal
    activo          BIT DEFAULT 1,
    fecha_alta      DATETIME DEFAULT GETDATE(),
    fecha_modif     DATETIME DEFAULT GETDATE()
);
CREATE INDEX IX_cat_sku ON omicronvt.dbo.catalogo_comercial(sku_base);
```

**Nota sobre fotos:** Fernando ya está trabajando en carga de datos a partir de fotos. Este módulo se integra con ese flujo — las fotos se guardan en un directorio del servidor (ej: `\\192.168.2.111\fotos_catalogo\{sku_base}\`) y la tabla solo guarda la referencia.

**Controller:** `catalogo_comercial.py`
- `index()` — lista de productos con/sin contenido comercial
- `editar(sku)` — formulario para cargar título, descripción, hashtags, fotos
- `api_catalogo(sku)` — JSON con toda la info comercial (para el panel del vendedor)
- `pendientes()` — productos sin contenido comercial (cola de trabajo)

**Integración con carga de pedidos:** Cuando se carga un pedido nuevo (paso6), si el SKU no tiene entrada en `catalogo_comercial`, se crea automáticamente con datos básicos (título = descripción_1 del artículo, descripción = genérica por marca).

---

### M2: PANEL DEL VENDEDOR (dashboard personal)

**Problema que resuelve:** El vendedor freelance necesita autonomía total: ver su rendimiento, sus clientes, su liquidación, y acceder al catálogo para compartir. Hoy no existe ningún portal orientado al vendedor.

**Tablas nuevas:**

```sql
-- Vendedores freelance (extiende viajantes con datos de monotributo)
CREATE TABLE omicronvt.dbo.vendedor_freelance (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    viajante_cod    INT NOT NULL,              -- FK → viajantes.codigo
    cuit            VARCHAR(13),
    razon_social    NVARCHAR(100),
    categoria_mono  VARCHAR(2),                -- A, B, C, D...
    cuota_mono      DECIMAL(12,2),
    fee_pct_std     DECIMAL(5,4) DEFAULT 0.05, -- 5% estándar
    fee_pct_premium DECIMAL(5,4) DEFAULT 0.08, -- 8% premium
    instagram       VARCHAR(100),
    whatsapp        VARCHAR(20),
    codigo_atrib    VARCHAR(10),               -- código único de atribución: V569
    canon_mensual   DECIMAL(12,2) DEFAULT 0,   -- alquiler del espacio
    fecha_inicio    DATE,
    activo          BIT DEFAULT 1,
    UNIQUE(viajante_cod),
    UNIQUE(codigo_atrib)
);

-- Configuración de franja horaria → bonificación
CREATE TABLE omicronvt.dbo.franjas_incentivo (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    dia_semana      TINYINT,                   -- 1=Lun, 7=Dom
    hora_desde      TIME,
    hora_hasta      TIME,
    bonus_fee_pct   DECIMAL(5,4),              -- bonus adicional sobre fee
    descripcion     VARCHAR(50)
);
```

**Controller:** `panel_vendedor.py`
- `index()` — Dashboard personal: ventas hoy/semana/mes, ranking, gráfico evolución
- `catalogo()` — Catálogo con botón "Compartir" (genera contenido personalizado)
- `clientes()` — Mis clientes recurrentes (de la atribución)
- `liquidacion()` — Mi liquidación del mes (detalle de cada venta + fee)
- `perfil()` — Mis datos, monotributo, proyección vs tope categoría
- `ranking()` — Ranking general (gamificación)

**Auth:** Nuevo rol `informes_vendedor` — el vendedor solo ve SU panel, no el de otros. El `viajante_cod` se vincula al `auth_user` en el login.

**Vista (HTML):** Diseño mobile-first (el vendedor usa el celular). Responsive, con botones grandes para compartir en redes.

---

### M3: GENERADOR DE CONTENIDO OMNICANAL

**Problema que resuelve:** Cargar el dato una sola vez y que se publique en todos los canales. Hoy hay que hacer todo manual.

**Flujo:**

```
MS Gestión (artículo)
    ↓ [auto-sync]
catalogo_comercial (fotos + descripciones)
    ↓ [generador]
┌────────────────────────────────────────────────┐
│  Para cada vendedor activo:                     │
│                                                 │
│  📱 Instagram → imagen con precio + link V569   │
│  💬 WhatsApp → mensaje + foto + link V569       │
│  🛒 MercadoLibre → publicación con atribución   │
│  🌐 Tiendanube → ficha de producto              │
│  📋 Catálogo PDF → para imprimir en local       │
└────────────────────────────────────────────────┘
```

**Tablas nuevas:**

```sql
-- Cola de contenido generado (cada vez que se publica un producto nuevo)
CREATE TABLE omicronvt.dbo.contenido_generado (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    sku_base        VARCHAR(20),
    vendedor_id     INT,                       -- FK → vendedor_freelance.id
    canal           VARCHAR(20),               -- INSTAGRAM, WHATSAPP, ML, TN
    contenido_texto NVARCHAR(MAX),             -- texto generado
    contenido_imagen VARCHAR(200),             -- path imagen generada
    link_atribucion VARCHAR(200),              -- h4calzados.com/p/21872?v=569
    estado          VARCHAR(10) DEFAULT 'LISTO', -- LISTO, COMPARTIDO, EXPIRADO
    fecha_gen       DATETIME DEFAULT GETDATE(),
    fecha_compart   DATETIME NULL
);
```

**Controller:** `contenido_omnicanal.py`
- `generar_batch()` — genera contenido para todos los vendedores activos de productos nuevos
- `api_contenido_vendedor(cod)` — JSON con contenido listo para compartir
- `preview(sku, vendedor)` — preview del post de Instagram/WA
- `marcar_compartido(id)` — el vendedor marca que ya lo publicó

**Generación de imágenes:** Usar Pillow (Python) para superponer precio y link del vendedor sobre la foto del producto. Template por marca (Topper, GTN, etc.).

**APIs externas (fase 2):**
- **MercadoLibre API** → publicar/actualizar stock automáticamente
- **Tiendanube API** → sync catálogo
- **WhatsApp Business API** → enviar catálogo a lista de contactos del vendedor
- **Instagram Graph API** → publicar stories/feed programado

---

### M4: ATRIBUCIÓN Y TRACKING

**Problema que resuelve:** Saber qué vendedor generó cada venta. Hoy `ventas1.viajante` existe pero no diferencia si el cliente vino por redes del vendedor, por la puerta, o por MercadoLibre.

**Tablas nuevas:**

```sql
-- Atribución de ventas a vendedores freelance
CREATE TABLE omicronvt.dbo.venta_atribucion (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    -- Referencia a la venta en el ERP
    empresa         VARCHAR(10),
    codigo          INT,
    letra           CHAR(1),
    sucursal        INT,
    numero          INT,
    orden           INT,
    -- Atribución
    vendedor_id     INT,                       -- FK → vendedor_freelance.id
    canal_origen    VARCHAR(20),               -- INSTAGRAM, WHATSAPP, PRESENCIAL, ML, WEB
    link_usado      VARCHAR(200),              -- el link que trajo al cliente
    fecha           DATETIME DEFAULT GETDATE(),
    -- Fee calculado
    fee_pct         DECIMAL(5,4),              -- % aplicado
    fee_monto       DECIMAL(12,2),             -- monto del fee
    bonus_franja    DECIMAL(5,4) DEFAULT 0,    -- bonus por franja horaria
    estado_factura  VARCHAR(10) DEFAULT 'PEND' -- PEND, FACTURADO, PAGADO
);
CREATE INDEX IX_atrib_vendedor ON omicronvt.dbo.venta_atribucion(vendedor_id);
CREATE INDEX IX_atrib_fecha ON omicronvt.dbo.venta_atribucion(fecha);

-- Clientes del vendedor (CRM mínimo)
CREATE TABLE omicronvt.dbo.cliente_vendedor (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    vendedor_id     INT,
    cliente_nombre  NVARCHAR(100),
    cliente_tel     VARCHAR(20),
    cliente_ig      VARCHAR(50),
    primera_compra  DATE,
    ultima_compra   DATE,
    total_compras   INT DEFAULT 0,
    total_monto     DECIMAL(14,2) DEFAULT 0,
    notas           NVARCHAR(500)
);
```

**Flujo de atribución:**

1. **Venta presencial con vendedor identificado**: Al registrar la venta en el ERP, el campo `viajante` ya identifica al vendedor. Un trigger o SP crea automáticamente el registro en `venta_atribucion`.

2. **Venta por link (web/redes)**: El link `h4calzados.com/p/21872?v=569` registra en el sitio la atribución. Cuando se concreta la venta en el ERP, se cruza.

3. **Venta por WhatsApp**: El vendedor registra en su panel "venta atribuida" antes o después del cierre. Se vincula al comprobante del ERP.

**Controller:** Integrado en `panel_vendedor.py` y en `liquidacion.py`.

---

### M5: FACTURACIÓN DUAL

**Problema que resuelve:** Cada venta genera dos facturas: H4 por el producto, vendedor por el servicio. Hoy no existe esta lógica.

**Modelo de facturación (el que diseñamos):**

```
CLIENTE compra $80.000 en producto + $5.600 en servicio (7%)

  Factura H4 → Cliente:    $80.000 (producto, por cuenta y orden)
  Factura Vendedor → Cliente: $5.600 (servicio de asesoramiento, monotributo C)

  El cliente paga el producto a H4 y el servicio al vendedor.
```

**El fee se calcula automáticamente:**

```
fee = producto × fee_pct × (1 + bonus_franja)

Donde:
  fee_pct = 5% (STD) o 8% (PREMIUM) según categoría del producto
  bonus_franja = 0% a 3% según franja horaria de la venta
```

**Tabla de referencia para el vendedor:**

```sql
-- Borrador de factura C para el vendedor
CREATE TABLE omicronvt.dbo.factura_servicio_borrador (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    vendedor_id     INT,
    atribucion_id   INT,                       -- FK → venta_atribucion.id
    cliente_nombre  NVARCHAR(100),
    cliente_cuit    VARCHAR(13),
    concepto        NVARCHAR(200) DEFAULT 'Servicio de asesoramiento comercial',
    monto           DECIMAL(12,2),
    fecha           DATE,
    estado          VARCHAR(10) DEFAULT 'BORRADOR', -- BORRADOR, EMITIDO, ANULADO
    cae             VARCHAR(20) NULL,           -- lo completa el vendedor post-emisión
    fecha_emision   DATETIME NULL
);
```

**No reemplaza a ARCA:** H4 no emite la factura C del vendedor. Le genera un borrador con los datos para que el vendedor emita desde la app de ARCA/factura electrónica en su celular. El vendedor marca "emitido" y opcionalmente carga el CAE.

---

### M6: LIQUIDACIÓN Y SETTLEMENT

**Problema que resuelve:** Al cierre del mes, cada vendedor necesita saber: cuánto vendió, cuánto facturó en servicios, cuánto es su canon, cuánto le corresponde de monotributo, y cuál es su neto.

**Tabla nueva:**

```sql
CREATE TABLE omicronvt.dbo.liquidacion_vendedor (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    vendedor_id     INT,
    periodo_anio    INT,
    periodo_mes     INT,
    -- Totales
    ventas_producto DECIMAL(14,2),             -- total facturado H4 por sus ventas
    cant_operaciones INT,
    cant_pares      INT,
    -- Fee
    total_fee       DECIMAL(14,2),             -- suma de fees del mes
    total_bonus     DECIMAL(14,2),             -- bonus por franja horaria
    -- Deducciones
    canon_espacio   DECIMAL(14,2),
    cuota_mono      DECIMAL(14,2),
    -- Neto
    neto_estimado   DECIMAL(14,2),             -- fee + bonus - canon - cuota_mono
    -- Control
    estado          VARCHAR(10) DEFAULT 'BORR', -- BORR, CERRADA, PAGADA
    fecha_cierre    DATETIME NULL,
    fecha_pago      DATETIME NULL,
    UNIQUE(vendedor_id, periodo_anio, periodo_mes)
);
```

**Controller:** `liquidacion.py`
- `generar_mes(anio, mes)` — procesa todas las ventas atribuidas, calcula fees, genera liquidaciones
- `detalle(vendedor_id, anio, mes)` — detalle de la liquidación de un vendedor
- `aprobar(id)` — gerencia aprueba la liquidación
- `resumen()` — vista gerencial: todas las liquidaciones del mes

**Resumen diario por WhatsApp (fase 2):** SP que se ejecuta cada noche y genera un mensaje por vendedor con su resumen del día. Se envía vía WhatsApp Business API o se muestra en el panel.

---

### M7: DASHBOARD GERENCIAL FREELANCE

**Problema que resuelve:** Fernando necesita ver de un vistazo cómo funciona la red de vendedores freelance.

**Controller:** `gerencial_freelance.py`
- `dashboard()` — KPIs globales de la red:
  - Total vendedores activos
  - Ventas totales del mes (producto + servicio)
  - Ahorro vs modelo empleado (cálculo en tiempo real)
  - Ranking de vendedores por venta, por fee, por clientes nuevos
  - Canales: % ventas por Instagram / WhatsApp / Presencial / ML
  - Proyección mensual
  - Alertas: vendedores cerca del tope de monotributo, vendedores inactivos

**Permisos:** Solo `informes_admin` e `informes_gerencia`.

---

### M8: SIMULADOR ACTUALIZADO

**Problema que resuelve:** El Excel `CLZ_Modelo_Vendedor_Freelance.xlsx` existente modela el esquema anterior (vendedor factura a H4). Hay que actualizarlo al esquema nuevo (vendedor factura al cliente).

**Cambios clave:**
- El fee no sale de H4 → sale del bolsillo del cliente
- H4 no paga fee al vendedor → solo cobra el producto
- El ahorro de H4 es total: no paga cargas sociales, no paga sueldo, solo le vende producto al cliente (ganancia = margen del producto)
- El vendedor gana: fee directo del cliente + su operación es 100% transparente

---

## 4. PRIORIDAD DE IMPLEMENTACIÓN

### Fase 1 — Fundamentos (semanas 1-2)
1. **M4: Atribución** — Crear tablas, SP que vincula `ventas1.viajante` con atribución automática
2. **Vendedor Freelance (tabla)** — Dar de alta los primeros vendedores piloto
3. **M2: Panel del Vendedor (básico)** — Dashboard con ventas propias y ranking

### Fase 2 — Catálogo y Contenido (semanas 3-4)
4. **M1: Catálogo Comercial** — Tabla + interface de carga de fotos y descripciones
5. **M3: Generador de Contenido (básico)** — Templates de WhatsApp e Instagram por vendedor

### Fase 3 — Facturación y Liquidación (semanas 5-6)
6. **M5: Facturación Dual** — Borradores de factura C
7. **M6: Liquidación** — Cierre mensual con detalle

### Fase 4 — Gerencial y Omnicanal (semanas 7-8)
8. **M7: Dashboard Gerencial** — Vista completa de la red
9. **M3 (avanzado)** — APIs a MercadoLibre, Tiendanube, WhatsApp Business
10. **M8: Simulador** — Excel actualizado con modelo final

---

## 5. STACK TECNOLÓGICO

### Opción A: Seguir con web2py 2.24.1 + Python 2.7 (pragmática)
**Ventaja:** Todo lo existente funciona, deploy probado, no hay migración.
**Desventaja:** Python 2.7 está muerto. Librerías nuevas (Pillow, APIs de ML/IG) no soportan Py2.7. No hay websockets para notificaciones en tiempo real.

### Opción B: Módulo nuevo en Python 3 + FastAPI (recomendada)
**Ventaja:** Moderno, async, APIs REST nativas, websockets, compatible con todas las librerías actuales.
**Convivencia:** El módulo nuevo corre en un puerto diferente (ej: 8001) en el mismo servidor .111. Lee las mismas bases SQL Server. Los módulos existentes (pedidos, calce, productividad) siguen en web2py sin tocar.

```
192.168.2.111
├── :8000 → web2py (calzalindo_informes) — módulos existentes
└── :8001 → FastAPI (calzalindo_freelance) — módulos nuevos M1-M7
             ├── /api/v1/vendedor/     → Panel vendedor (JSON)
             ├── /api/v1/catalogo/     → Catálogo comercial (JSON)
             ├── /api/v1/contenido/    → Generador contenido (JSON)
             ├── /api/v1/atribucion/   → Tracking (JSON)
             ├── /api/v1/liquidacion/  → Settlement (JSON)
             ├── /panel/               → Frontend vendedor (HTML/JS)
             └── /admin/               → Dashboard gerencial (HTML/JS)
```

### Opción C: Migrar todo a plataforma moderna (ideal pero costosa)
**Stack:** Next.js + Prisma + PostgreSQL (o seguir con SQL Server) + Vercel/Railway.
**Ventaja:** El sistema de gestión más moderno del planeta, literalmente.
**Desventaja:** Migración masiva, riesgo alto, meses de trabajo. No recomendado como primer paso.

### **RECOMENDACIÓN: Opción B.**
Arrancar con FastAPI en Python 3 para los módulos nuevos. Convive con web2py. Cuando los módulos nuevos estén estables, migrar gradualmente los módulos viejos de web2py a FastAPI.

---

## 6. MODELO DE DATOS — DIAGRAMA ENTIDAD-RELACIÓN

```
┌─────────────────────┐         ┌─────────────────────┐
│ viajantes (existente)│         │ articulo (existente) │
│ • codigo (PK)       │         │ • codigo (PK)        │
│ • descripcion       │         │ • descripcion_1      │
│ • porcentaje        │         │ • precio_1..4        │
│ • estado            │         │ • marca, subrubro    │
└────────┬────────────┘         └────────┬────────────┘
         │ 1:1                           │ N:1
         ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│ vendedor_freelance   │         │ catalogo_comercial   │
│  (NUEVO)             │         │  (NUEVO)             │
│ • viajante_cod (FK)  │         │ • sku_base           │
│ • cuit, razon_social │         │ • titulo_corto       │
│ • categoria_mono     │         │ • descripcion_redes  │
│ • fee_pct_std/prem   │         │ • hashtags           │
│ • instagram, whatsapp│         │ • fotos_path         │
│ • codigo_atrib (V569)│         │ • categoria_fee      │
└────────┬────────────┘         └────────┬────────────┘
         │                               │
         │ 1:N                           │ 1:N
         ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│ venta_atribucion     │         │ contenido_generado   │
│  (NUEVO)             │         │  (NUEVO)             │
│ • vendedor_id (FK)   │         │ • sku_base (FK)      │
│ • empresa, codigo... │         │ • vendedor_id (FK)   │
│ • canal_origen       │         │ • canal (IG/WA/ML)   │
│ • fee_pct, fee_monto │         │ • contenido_texto    │
│ • estado_factura     │         │ • link_atribucion    │
└────────┬────────────┘         └──────────────────────┘
         │
         │ N:1
         ▼
┌─────────────────────┐
│ liquidacion_vendedor │
│  (NUEVO)             │
│ • vendedor_id (FK)   │
│ • periodo anio/mes   │
│ • total_fee          │
│ • canon_espacio      │
│ • cuota_mono         │
│ • neto_estimado      │
│ • estado             │
└──────────────────────┘
```

---

## 7. FLUJO OPERATIVO DIARIO COMPLETO

```
                    ╔═══════════════════════════╗
                    ║  08:00 — CARGA DE NOVEDAD ║
                    ╚═════════════╤═════════════╝
                                  │
                    ┌─────────────▼─────────────┐
                    │ Encargado carga producto   │
                    │ en MS Gestión + saca fotos │
                    │ → INSERT en articulo       │
                    │ → Upload fotos al servidor │
                    └─────────────┬─────────────┘
                                  │ [trigger/SP auto]
                    ┌─────────────▼─────────────┐
                    │ catalogo_comercial se crea │
                    │ con datos básicos + fotos  │
                    │ → genera contenido para    │
                    │   cada vendedor activo     │
                    └─────────────┬─────────────┘
                                  │ [notificación]
                    ┌─────────────▼─────────────┐
                    │ Vendedores reciben aviso:  │
                    │ "Nuevo producto disponible" │
                    │ Abren panel → "Compartir"  │
                    └─────────────┬─────────────┘
                                  │
               ┌──────────────────┼──────────────────┐
               ▼                  ▼                  ▼
        ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
        │  Instagram   │   │  WhatsApp    │   │ MercadoLibre│
        │  Story/Feed  │   │  Catálogo    │   │ Publicación │
        │  con V569    │   │  con V569    │   │ con V569    │
        └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
               │                 │                  │
               └────────┬────────┘──────────────────┘
                        │ [cliente contacta al vendedor]
                        ▼
              ┌──────────────────────┐
              │ VENTA EN EL LOCAL     │
              │ • Vendedor asesora    │
              │ • Sistema registra:   │
              │   viajante = V569     │
              │   canal = INSTAGRAM   │
              └──────────┬───────────┘
                         │ [al cerrar la venta]
              ┌──────────▼───────────┐
              │ FACTURACIÓN DUAL      │
              │                       │
              │ ► H4 → Cliente:       │
              │   Factura producto    │
              │   $80.000             │
              │                       │
              │ ► Vendedor → Cliente: │
              │   Factura servicio    │
              │   $5.600 (7%)         │
              │   (borrador auto)     │
              └──────────┬───────────┘
                         │
              ┌──────────▼───────────┐
              │ ATRIBUCIÓN REGISTRADA │
              │ • venta_atribucion    │
              │ • fee calculado       │
              │ • canal: INSTAGRAM    │
              └──────────┬───────────┘
                         │ [fin del día]
              ┌──────────▼───────────┐
              │ RESUMEN DIARIO        │
              │ "Hoy vendiste 8 pares │
              │  Fee total: $44.800   │
              │  Ranking: #2 del día" │
              └──────────┬───────────┘
                         │ [fin del mes]
              ┌──────────▼───────────┐
              │ LIQUIDACIÓN MENSUAL   │
              │ • Total fee: $890.000 │
              │ • Canon: $50.000      │
              │ • Mono: $72.414       │
              │ • Neto: $767.586      │
              └──────────────────────┘
```

---

## 8. COMPETENCIA: POR QUÉ ESTO ES EL SISTEMA MÁS MODERNO

| Zapatería tradicional | H4 con este sistema |
|----------------------|---------------------|
| Empleados que esperan al que entra | 9+ micro-emprendedores que salen a buscar clientes |
| Un canal: la puerta del local | Omnicanal: IG + WA + ML + TN + presencial por vendedor |
| Catálogo: vidrieras físicas | Catálogo digital × 9 audiencias diferentes |
| Incentivo: sueldo fijo | Incentivo: 100% variable, gana más el que vende más |
| Costo laboral: 43% sobre bruto | Costo laboral: 0% (son freelancers) |
| Datos: registro manual | Datos: atribución automática por canal y vendedor |
| Adaptabilidad: nula | Adaptabilidad: franjas horarias dinámicas por mercado |

**La clave es que los datos se cargan UNA sola vez** (en MS Gestión al recibir mercadería) **y se multiplican por N vendedores × M canales automáticamente.** Cada vendedor es un nodo de distribución humano con sus propias redes y audiencia. Es una red comercial distribuida que escala sin costo fijo.

---

## 9. PRÓXIMO PASO INMEDIATO

Crear las tablas del Fase 1 en `omicronvt` (réplica .112 primero, luego producción .111) y empezar a construir el controller `panel_vendedor.py` como módulo web2py (para arrancar rápido) con migración posterior a FastAPI.

¿SQL para crear las tablas está listo arriba. ¿Arrancamos?

---

## 10. SEÑALES DE MERCADO — BITÁCORA

### 5 de abril de 2026 — Uber apuesta $500M en Argentina

**Fuente:** Nota periodística sobre inversión Uber Argentina (abril 2026)

**Puntos clave:**
- Argentina es **top 5 mundial** en viajes Uber, top 10 en gasto USD. Sobreperforma su peso poblacional.
- **USD 500M de inversión** anunciada + relanzamiento de Uber Eats.
- El CEO elogió a Milei pero tiene incentivo directo: acaba de comprometer 500 palos. No es análisis, es PR.
- La señal real no es el discurso político — es que una empresa de esta escala apuesta en su mercado top 5 con producto nuevo.
- **Dato útil para el modelo freelance:** Uber Eats entra donde ya tienen masa crítica de usuarios. Eso es exactamente la lógica de plataforma: primero volumen, después capas de servicio encima.
- Riesgo que la nota ignora: el contexto macro (cepo en transición, flotación sucia) puede revertirse. Uber lo sabe y lo diversifica con escala.

**Conexión con nuestro modelo:**
Calzalindo ya tiene la masa crítica (15 sucursales, ~3,500 clientes/mes, catálogo de 10K+ artículos). El modelo freelance es la "capa de servicio encima" — vendedores independientes que amplifican el alcance sin carga social del 43%. Si Uber valida que el gig economy funciona en Argentina con $500M, la tesis se refuerza.
