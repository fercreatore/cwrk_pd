# Investigacion: Plataformas Tecnologicas para Social Selling
> Fecha: 3 de abril de 2026
> Contexto: Calzalindo quiere armar plataforma para vendedores independientes via WA/IG

---

## 1. PANORAMA DEL MERCADO

### Social Commerce global
- US social commerce supero USD 100B en 2026, creciendo ~30% interanual
- Social commerce representa >7% del retail total
- Tendencia: compra completa sin salir de la red social (discovery -> checkout in-app)

### LatAm especificamente
- Mercado social commerce LatAm: USD 14.6B en 2025, proyectado USD 27.9B para 2030 (CAGR 13.8%)
- Argentina: e-commerce alcanzo USD 19B en 2025 (+24% YoY)
- WhatsApp y Facebook Marketplace son los canales informales dominantes en Argentina
- Solo 38% de argentinos probaron social commerce (oportunidad enorme)

### Modelo Meesho (India) — caso de estudio clave
- Fundada 2015. Conecta proveedores -> revendedores -> consumidores
- Revendedores (mayoria mujeres) eligen productos, agregan markup, comparten por WhatsApp/IG/FB
- SIN inversion del revendedor: no maneja stock ni logistica
- Meesho cobra 0% comision a revendedores desde 2022 (monetiza por logistica propia — Valmo)
- Escala: 100M+ revendedores en India
- **Relevancia para Calzalindo**: modelo identico al que queremos. Diferencia: Meesho es marketplace multi-proveedor, nosotros somos single-brand/multi-marca

---

## 2. PLATAFORMAS SaaS EVALUADAS

### A) WhatsApp Commerce (venta directa por WA)

| Plataforma | Precio | Features clave | Sirve para Calzalindo? |
|-----------|--------|----------------|----------------------|
| **SleekFlow** | Desde USD 149/mes (Premium USD 349/mes) | AI agents, catalogo en WA, carrito en chat, pagos in-chat, multi-agente, CRM, integraciones Shopify/HubSpot | **PARCIALMENTE** — excelente para WA commerce pero no tiene modulo de revendedores/comisiones |
| **charles** (Berlin) | Pricing custom (estimado >USD 500/mes) | WhatsApp newsletters, venta en chat, integracion Shopify/Salesforce | **NO** — enfocado en Europa, pricing alto, sin modulo reseller |
| **WhatsApp Business Platform (API directa)** | Cobro por mensaje enviado (varies por pais) | Catalogo, mensajes template, automatizacion | **YA LO TIENEN** via Chatwoot. Base necesaria pero no resuelve el modulo vendedor |

**Veredicto WA Commerce**: Calzalindo ya tiene Chatwoot con WA Cloud API. SleekFlow podria agregar valor en AI y catalogo in-chat, pero no resuelve el core: gestion de vendedores freelance con comisiones.

---

### B) Brand Ambassador / Embajadores de Marca

| Plataforma | Precio | Features clave | Sirve para Calzalindo? |
|-----------|--------|----------------|----------------------|
| **Brandbassador** | USD 500-3000/mes | Misiones gamificadas, codigos descuento trackeo, comisiones, app movil, integracion Shopify | **PARCIALMENTE** — tiene el concepto de misiones y comisiones, pero orientado a awareness/contenido mas que a venta directa |
| **SocialLadder** | USD 5000-50000/mes (enterprise) | Comunidad de embajadores, campus programs, American Eagle lo usa | **NO** — muy caro, orientado a marcas DTC grandes de USA |
| **Aspire** | Similar rango enterprise | Base 10M influencers, CRM, UGC, pagos automaticos | **NO** — orientado a influencer marketing, no a revendedores |
| **BrandChamp** | Desde ~USD 250/mes | Ambassador management, referral tracking, rewards | **PARCIALMENTE** — mas accesible, pero sigue orientado a USA/Shopify |

**Veredicto Ambassadors**: Estas plataformas gestionan "embajadores" que generan contenido y awareness, NO vendedores que toman pedidos y cobran comision por venta. El modelo Calzalindo es mas transaccional. Ademas, pricing en USD es prohibitivo para una pyme de Venado Tuerto.

---

### C) Referral / Afiliados

| Plataforma | Precio | Features clave | Sirve para Calzalindo? |
|-----------|--------|----------------|----------------------|
| **ReferralCandy** | Desde ~USD 59/mes | Links de referido, rewards automaticos, ROI 1220% promedio, 30K merchants | **NO** — es referral puro (cliente refiere cliente), no vendedor dedicado |
| **Friendbuy** | Enterprise pricing | Referral + loyalty, Shopify Plus | **NO** — mismo concepto, mas caro |
| **Yotpo** | Varies | Referrals + reviews + loyalty integrado | **NO** — ecosistema Shopify-centrico |

**Veredicto Referral**: Modelo equivocado. Referral = un cliente recomienda a otro y gana recompensa. Calzalindo necesita vendedores activos que manejan catalogo, toman pedidos, y cobran comision recurrente.

---

### D) Clones de Meesho / White-label Reseller

| Proveedor | Precio estimado | Que ofrecen |
|-----------|----------------|-------------|
| **AppDupe** (India) | USD 5K-25K one-time | App reseller white-label: panel admin, panel supplier, app reseller, catalogo, markup, logistica |
| **TurnkeyTown** (India) | Similar rango | Clon Meesho llave en mano |
| **Next Big Technology** | Similar | Desarrollo custom basado en template |

**Veredicto Clones Meesho**: Interesante conceptualmente pero problematico en la practica:
- Son empresas de India, soporte en ingles, timezone incompatible
- Stack tecnologico desconocido (probablemente React Native + Node)
- NO se integran con SQL Server / ERP MS Gestion
- Requieren adaptacion a medios de pago argentinos (MercadoPago, transferencia)
- El costo real con customizacion probablemente supere USD 30-50K

---

## 3. PLATAFORMAS LATAM RELEVANTES

No se encontraron plataformas SaaS especificas para social selling/resellers en Argentina. El mercado LatAm esta dominado por:

- **Mercado Libre**: marketplace tradicional, no social selling
- **WhatsApp informal**: miles de pymes venden por WA sin plataforma formal
- **TiendaNube/VTEX**: e-commerce propio, no tienen modulo reseller

La ausencia de competencia SaaS en este nicho para LatAm es significativa — es tanto una oportunidad como una senial de que el mercado aun no la demanda masivamente.

---

## 4. ANALISIS BUILD vs BUY

### Lo que Calzalindo YA tiene construido:

| Componente | Estado | Reemplazable por SaaS? |
|-----------|--------|----------------------|
| SQL Server con stock/precios/articulos en tiempo real | Produccion | NO — es el core del negocio |
| FastAPI en 112 (`calzalindo_freelance`) | En desarrollo | Es lo que estamos construyendo |
| Chatwoot con WA Cloud API | Produccion | SI, pero ya funciona y es gratis/open-source |
| Web2py informes | Produccion | NO — reporteria custom del negocio |
| Pipeline pedidos (paso1-6) | Produccion | NO — logica de negocio critica |
| OCR facturas | Produccion | NO relevante para freelance |

### Que necesita el modulo freelance que NINGUN SaaS resuelve:

1. **Consulta de stock en tiempo real** contra SQL Server (talles, colores, depositos)
2. **Precios con logica de descuento compleja** (desc proveedor + bonificacion + markup vendedor)
3. **Generacion de pedido en ERP** (INSERT en pedico2/pedico1 con routing empresa)
4. **Comisiones sobre venta real facturada** (no sobre click o referido)
5. **Catalogo dinamico** que refleje stock real (no vender lo que no hay)
6. **Integracion con medios de pago argentinos** (MercadoPago, transferencia, efectivo)
7. **Operacion en pesos argentinos** con inflacion (precios cambian frecuentemente)

### Matriz de decision:

| Criterio | BUILD (in-house) | BUY (SaaS) |
|---------|-----------------|------------|
| Integracion con ERP/SQL Server | Nativa, directa | Imposible o muy costosa |
| Stock en tiempo real | SI, ya conectado | NO — requiere sync custom |
| Medios de pago AR | MercadoPago API | Stripe (no sirve en AR para esto) |
| Costo mensual | Hosting 112 (ya pagado) | USD 500-3000/mes minimo |
| Costo inicial | Desarrollo ~40-80hs | USD 5K-25K + customizacion |
| Mantenimiento | Fernando/equipo | Dependencia vendor + USD mensuales |
| Flexibilidad | Total | Limitada al SaaS |
| Escalabilidad | Limitada por equipo | Mejor en teoria |
| Time to market | 2-4 semanas (MVP) | 1-2 meses (config + integracion) |

---

## 5. RECOMENDACION: BUILD IN-HOUSE

### Por que construir:

1. **El 80% de la infra ya existe**: SQL Server, FastAPI, Chatwoot, pipeline pedidos
2. **Ningun SaaS se integra con MS Gestion**: el ERP es SQL Server 2012 on-premise, no hay API. Cualquier SaaS requeriria un middleware custom que es tanto trabajo como construir el modulo
3. **Costo prohibitivo en USD**: USD 500-3000/mes en SaaS es inviable para una pyme de calzado en Venado Tuerto. Construir sale el costo de desarrollo (ya amortizado) + hosting (ya pagado)
4. **El diferenciador es la integracion**: stock real, precios reales, pedido real. Un SaaS con catalogo desincronizado no sirve
5. **El modelo Meesho funciona a escala**: pero Meesho empezo construyendo in-house y escalo. No compro un SaaS

### Que tomar de los SaaS evaluados (ideas, no software):

| Idea | De donde | Aplicar en |
|------|----------|-----------|
| Misiones gamificadas | Brandbassador | Vendedor cumple X ventas -> bonus |
| Catalogo en WA con carousel | SleekFlow | Chatwoot + templates WA con imagenes |
| Link de referido con tracking | ReferralCandy | Cada vendedor tiene link unico |
| App movil para vendedor | Brandbassador/Meesho | PWA con catalogo + stock + pedidos |
| Markup del vendedor | Meesho | Vendedor define su margen sobre precio base |
| Zero investment model | Meesho | Vendedor no pone plata, no maneja stock |
| Onboarding automatizado | SocialLadder | Formulario WA -> alta automatica |

### Stack recomendado (build):

```
FastAPI (112) -----> SQL Server (111)
     |                    |
     v                    v
  Chatwoot (WA)    Stock/Precios/Pedidos
     |
     v
  Vendedor (WA / PWA)
     |
     v
  Cliente final
```

### MVP minimo (2-4 semanas):

1. **Catalogo vendedor**: endpoint FastAPI que devuelve productos con stock y precio
2. **Link compartible**: vendedor comparte link con su codigo -> cliente ve producto
3. **Pedido via WA**: cliente confirma por WA, vendedor registra en sistema
4. **Comision**: calculo automatico al facturar (query ventas1 con codigo vendedor)
5. **Dashboard vendedor**: PWA basica con mis ventas, mis comisiones, mi catalogo

---

## 6. FUENTES

### Social Selling General
- Shopify Blog — Best Social Selling Platforms 2026
- TheRetailExec — 16 Best Social Commerce Platforms 2026

### Brand Ambassador
- SocialLadder — Best Brand Ambassador Platforms 2026
- InfluenceFlow — Ambassador Management Software Comparison 2026

### WhatsApp Commerce
- SleekFlow — WhatsApp Business Platform features and pricing
- charles — WhatsApp ecommerce platform
- WhatsApp Business — Official business platform

### Referral Commerce
- ReferralCandy — #1 eCommerce Referral Program Software
- Yotpo — Top 10 Best Referral Marketing Platforms 2026

### LatAm Social Commerce
- FashionUnited — 2026 E-commerce trends in Latin America
- BusinessWire — Latin America Social Commerce Intelligence Report 2025

### Modelo Meesho
- Feedough — Meesho Business Model
- MarkHub24 — Meesho's Social Commerce Business Model
- AppDupe — Meesho Clone App Development

### Build vs Buy
- Brandbassador — Ambassador Marketing Platform features and pricing
- InfluencerMarketingHub — Brandbassador Review and Pricing
