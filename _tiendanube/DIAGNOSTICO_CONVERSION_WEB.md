# DIAGNÓSTICO DE CONVERSIÓN WEB — Calzalindo.com.ar

> Fecha: 7 de marzo de 2026
> Contexto: Campaña Google Ads activa, tráfico llegando, 0 conversiones
> Integrado con: ARQUITECTURA_SISTEMA_VENDEDOR_FREELANCE.md + PROYECTO_contexto_h4_calzalindo_v3.md

---

## 1. RESUMEN EJECUTIVO

**El anuncio funciona. La web no convierte.**

| Métrica | Valor | Diagnóstico |
|---------|-------|-------------|
| Impresiones | 1,681 | ✅ Hay visibilidad |
| Clics | 108 | ✅ La gente hace clic (interés real) |
| CTR | 6.42% | ✅ Muy bueno (benchmark búsqueda: 3-5%) |
| CPC promedio | ARS$49.96 | ✅ Razonable |
| Costo total | ARS$5,395.17 | — |
| **Conversiones** | **0.00** | ❌ **PROBLEMA CRÍTICO** |
| Tasa de conversión | 0% | ❌ Benchmark ecommerce AR: 1-3% |
| Presupuesto diario | ARS$10,000 | — |

**Conclusión**: El tráfico es de calidad (CTR alto = búsqueda con intención). El 100% de la pérdida ocurre entre el clic y la compra. Hay que arreglar la página de producto y el flujo de checkout.

---

## 2. PROBLEMAS DETECTADOS EN LA PÁGINA DE PRODUCTO

### 2.1 🔴 CRÍTICOS (matan la conversión)

#### A. Envío gratis inalcanzable: $99,999
- El producto cuesta $31,199
- Para envío gratis necesitás comprar **3 zapatillas o más**
- **Nadie compra 3 pares de zapatillas outdoor en una primera compra online**
- En Argentina, el costo de envío es el motivo #1 de abandono de carrito
- **ACCIÓN**: Bajar el umbral a $30,000 (o idealmente envío gratis en todo) o absorber el envío en el precio

#### B. Cero confianza / Cero prueba social
- No hay reviews ni calificaciones
- No hay "X personas compraron este producto"
- No hay testimonios
- No hay fotos de clientes usando el producto
- La marca "Starflex" es desconocida — nadie confía en gastar $31K en algo que no conoce sin al menos ver que otros lo compraron
- **ACCIÓN**: Implementar reviews en Tiendanube (app Opiniones o similar), agregar badge de garantía, mostrar cantidad vendida

#### C. No hay botón de WhatsApp prominente
- En Argentina, el 70%+ de las consultas pre-compra van por WhatsApp
- El teléfono está perdido en el footer (5493462676300)
- No hay un botón flotante "Consultá por WhatsApp" al lado del producto
- **ACCIÓN**: Agregar botón flotante de WhatsApp con mensaje pre-armado: "Hola! Vi las Starflex 1174 en la web y quiero consultar"

#### D. Email de Gmail: calzalindoml@gmail.com
- Transmite informalidad y desconfianza
- Tenés hosting propio (vps-1820241-x.dattaweb.com) con panel de email
- **ACCIÓN**: Usar info@calzalindo.com.ar o ventas@calzalindo.com.ar (ya tenés cPanel de email abierto)

### 2.2 🟡 IMPORTANTES (reducen conversión)

#### E. Descripción técnica sin gancho emocional
**Lo que dice la página:**
> "Capellada compuesto en mesh de doble densidad y materiales sintéticos cosido a la base. Entresuela con tecnología Superaction en EVA..."

**Lo que debería decir:**
> "Ideal para trekking, senderismo y caminatas al aire libre. Pisada amortiguada que protege tus rodillas en terrenos irregulares. Plantilla con memoria que se adapta a tu pie. Liviana, transpirable y con agarre antideslizante."
>
> **Especificaciones técnicas:** [la info actual]

- El comprador no sabe qué es "mesh de doble densidad" ni le importa
- Quiere saber: ¿para qué sirve? ¿es cómoda? ¿me la banco en la montaña?
- **ACCIÓN**: Reescribir descripción con beneficios primero, specs después

#### F. Sin guía de talles
- Solo dice "Talle: 40 41 42 43 44"
- ¿Calzan grande o chico? ¿Es talle argentino o europeo?
- La incertidumbre del talle es el motivo #2 de no-compra en calzado online
- **ACCIÓN**: Agregar tabla de correspondencia y consejo ("Si estás entre dos talles, pedí el más grande")

#### G. Cuotas solo con DÉBITO
- "Cuotas SIN interés con DÉBITO" — esto es confuso y limitante
- La mayoría de la gente busca cuotas con TARJETA DE CRÉDITO
- Si no ofrecés cuotas con crédito, perdés un % enorme del mercado
- **ACCIÓN**: Revisar la integración de pagos en Tiendanube, habilitar Mercado Pago con cuotas de crédito

#### H. Sin elementos de urgencia
- No hay indicador de stock ("Quedan 3 unidades")
- No hay oferta por tiempo limitado
- No hay descuento de primera compra
- **ACCIÓN**: Agregar stock visible, banner "10% OFF primera compra con código BIENVENIDO"

#### I. Productos similares más caros generan desconfianza
- Las Starflex cuestan $31,199
- Los Topper al lado cuestan $104,999 (3.4x más)
- El usuario piensa: "¿Por qué esta es tan barata? ¿Será mala?"
- **ACCIÓN**: O subirle el precio percibido con mejor presentación, o mostrar productos de precio similar como "similares"

### 2.3 🟢 MENORES (mejoran la experiencia)

#### J. Menú de navegación vacío
- Las categorías MUJER, HOMBRE, NIÑOS muestran bullets sin texto en las subcategorías
- Esto puede ser un problema de carga o configuración de Tiendanube
- **ACCIÓN**: Verificar que el mega-menú carga correctamente

#### K. Breadcrumb muy profundo
- Inicio > HOMBRE > CALZADO > Outdoor > Producto (5 niveles)
- No es crítico pero agrega complejidad visual
- **ACCIÓN**: Evaluar simplificar a Inicio > Outdoor Hombre > Producto

---

## 3. PROBLEMAS EN GOOGLE ADS

### 3.1 Estructura demasiado básica
- **1 sola campaña**, 1 solo grupo de anuncios
- No hay segmentación por producto, marca, o intención de búsqueda
- Todo el tráfico va al mismo embudo

### 3.2 No hay tracking de conversiones configurado
- CPA objetivo: "—" (no configurado)
- Conversiones: 0.00 — esto puede significar dos cosas:
  1. Nadie compró (probable)
  2. El pixel de conversión no está instalado (verificar)
- **ACCIÓN URGENTE**: Verificar que el tag de conversión de Google Ads esté en la página de "Gracias por tu compra" de Tiendanube

### 3.3 No hay remarketing
- Sin remarketing, perdés al 97% que visitó y no compró
- **ACCIÓN**: Configurar audiencia de remarketing + campaña de Display para re-impactar

### 3.4 Falta segmentación de keywords
- Con 1 solo grupo de anuncios, probablemente todas las keywords van a la misma landing
- Debería haber:
  - Grupo "zapatillas outdoor" → landing categoría outdoor
  - Grupo "zapatillas trekking" → landing categoría outdoor
  - Grupo "zapatillas baratas hombre" → landing con filtro de precio
  - Grupo "starflex zapatillas" → landing de producto específico (si alguien busca la marca)

---

## 4. PLAN DE ACCIÓN — PRIORIZADO

### SEMANA 1: Apagar el incendio (dejar de quemar plata)

| # | Acción | Impacto | Esfuerzo | Responsable |
|---|--------|---------|----------|-------------|
| 1 | Verificar pixel de conversión de Google Ads en Tiendanube | Crítico — sin esto no sabés si vendés | 30 min | Fernando/ads person |
| 2 | Bajar envío gratis a $30,000 (o gratis total en estos productos) | Alto — elimina barrera #1 | 15 min | Tiendanube admin |
| 3 | Agregar botón WhatsApp flotante en toda la web | Alto — captura consultas calientes | 30 min | Tiendanube app |
| 4 | Cambiar email a ventas@calzalindo.com.ar | Medio — profesionaliza | 15 min | cPanel |
| 5 | Reescribir descripción del producto (beneficios + specs) | Alto — conecta con el comprador | 1 hora | Fernando |

### SEMANA 2: Optimizar la experiencia

| # | Acción | Impacto | Esfuerzo |
|---|--------|---------|----------|
| 6 | Agregar guía de talles | Alto | 1 hora |
| 7 | Implementar app de reviews en Tiendanube | Alto | 2 horas |
| 8 | Habilitar cuotas con tarjeta de crédito (Mercado Pago) | Alto | 1 hora |
| 9 | Agregar banner "10% OFF primera compra" con código | Medio | 30 min |
| 10 | Mejorar fotos de producto (contexto de uso, no solo fondo blanco) | Alto | Depende de fotos disponibles |

### SEMANA 3: Optimizar Google Ads

| # | Acción | Impacto | Esfuerzo |
|---|--------|---------|----------|
| 11 | Crear 3-4 grupos de anuncios por tipo de keyword | Alto | 2 horas |
| 12 | Configurar remarketing (Display) | Alto | 1 hora |
| 13 | Agregar extensiones de anuncio (precio, envío, WhatsApp) | Medio | 30 min |
| 14 | Crear landing pages por categoría (no mandar todo al producto) | Alto | 3 horas |
| 15 | Configurar CPA objetivo una vez haya datos de conversión | Alto | 15 min (cuando haya datos) |

### SEMANA 4+: Integrar con el proyecto vendedor freelance

| # | Acción | Conexión proyecto |
|---|--------|--------------------|
| 16 | Conectar catálogo Tiendanube con `catalogo_comercial` (M1) | Los vendedores freelance comparten links con atribución |
| 17 | Implementar links con código de vendedor (?v=569) en Tiendanube | M4: Atribución y Tracking |
| 18 | Generar contenido omnicanal desde las fichas de producto | M3: Generador de Contenido |
| 19 | Dashboard de conversión web en Metabase | Integrar con breakeven dashboard existente |
| 20 | Remarketing segmentado por vendedor/canal | M7: Dashboard Gerencial |

---

## 5. EJEMPLO: CÓMO DEBERÍA VERSE LA PÁGINA DE PRODUCTO

### Antes (actual):
```
Zapatillas Outdoor Starflex 1174 Negro/Rojo
$31.199,00
$24.959,20 con Transferencia o depósito
[foto producto fondo blanco]
Capellada compuesto en mesh de doble densidad y materiales sintéticos cosido a la base...
```

### Después (optimizado):
```
⭐⭐⭐⭐ 4.2 (23 opiniones) | 89 vendidos

Zapatillas Outdoor Starflex 1174 — Negro/Rojo
Para trekking, senderismo y caminatas urbanas

$31.199 ← $38.999 (20% OFF)
$24.959 pagando por transferencia

💳 6 cuotas sin interés de $5.200 con tarjeta de crédito
🚚 ENVÍO GRATIS a todo el país
📦 Llega en 3-5 días hábiles
🔄 30 días de devolución sin costo

[FOTO: persona caminando en montaña con las zapatillas]
[FOTO: detalle de la suela]
[FOTO: plantilla memory foam]
[VIDEO: 15 seg mostrando amortiguación]

AGREGAR AL CARRITO          [💬 Consultar por WhatsApp]

📏 ¿No sabés tu talle? → Ver guía de talles
   Si estás entre dos talles, elegí el más grande.

¿POR QUÉ ELEGIR ESTAS ZAPATILLAS?
✓ Amortiguación EVA que protege tus rodillas en terrenos irregulares
✓ Plantilla con memoria — se adapta a la forma de tu pie
✓ Transpirable: mesh de doble densidad que no acumula calor
✓ Suela antideslizante con agarre en superficies mojadas
✓ Peso liviano: ideal para caminatas largas sin cansarte

ESPECIFICACIONES TÉCNICAS
• Capellada: mesh doble densidad + sintéticos
• Entresuela: EVA Superaction
• Plantilla: Superfoam (memory foam)
• Taco: 3 cm | Plataforma: 1.5 cm

📦 GARANTÍA Calzalindo: Si no te queda, lo cambiamos gratis.
```

---

## 6. CONEXIÓN CON EL ECOSISTEMA CALZALINDO

Este diagnóstico no es solo sobre los anuncios — es sobre construir la máquina de ventas web que conecta con todo lo que ya tenemos:

```
Google Ads (tráfico pago)
    ↓
Página de producto optimizada (ESTE DIAGNÓSTICO)
    ↓
┌─── Compra directa → Tiendanube → ERP (MS Gestión)
│
├─── Consulta WhatsApp → Vendedor freelance (M2/M4)
│    → Atribución por código → Fee calculado
│
└─── No compra → Remarketing → Vuelve
         ↓
    Contenido omnicanal (M3)
    → Instagram del vendedor
    → WhatsApp catálogo
    → Vuelve a la web con link atribuido (?v=569)
```

**La web es el primer eslabón de toda la cadena.** Si no convierte, nada de lo que construyamos después (vendedores freelance, atribución, contenido omnicanal) tiene sentido, porque no hay flujo de clientes entrando al embudo.

---

## 7. MÉTRICAS OBJETIVO (30 días)

| Métrica | Actual | Objetivo semana 2 | Objetivo mes 1 |
|---------|--------|-------------------|-----------------|
| Tasa de conversión web | 0% | 1% | 2-3% |
| Consultas WhatsApp / día | ? | 5 | 15 |
| Costo por conversión | ∞ | < $5,000 | < $3,000 |
| ROAS | 0 | 2x | 5x |
| Conversiones / día | 0 | 1 | 3 |

Con 108 clics/día y 2% de conversión = ~2 ventas/día × $31,199 = $62,398/día de facturación con $5,395 de inversión = **ROAS 11.5x**. El potencial es enorme si arreglamos la página.

---

*Documento integrado al proyecto Calzalindo. Próximo paso: ejecutar acciones de Semana 1.*
