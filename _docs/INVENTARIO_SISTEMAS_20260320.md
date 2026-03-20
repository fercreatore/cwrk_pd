# Inventario de Sistemas — Finanzas, CFO, Presupuesto, Compras & Decisiones Comerciales

> Generado: 20 de marzo de 2026
> Alcance: cowork_pedidos completo — 97 archivos relevantes en 8 sistemas

---

## 1. FAMILY OFFICE (Portfolio Personal)
**`_family_office/`** — Dashboard de inversiones, 12 archivos, **COMPLETO**

| Archivo | Qué hace | Estado |
|---------|----------|--------|
| `app_family_office.py` | Streamlit UI 8 tabs — portfolio dashboard (port 8506) | completo |
| `config_fo.py` | Target allocation (30% Bonos, 37% CEDEARs, 13% Acc AR, 12% Crypto, 8% FCI) | completo |
| `csv_parser.py` | Parser CSV Cocos/IOL + dólar MEP live | completo |
| `broker_iol.py` | IOL REST API connector (OAuth2) | completo |
| `broker_cocos.py` | Cocos Capital connector (TOTP 2FA) | completo |
| `portfolio_live.py` | Agregador multi-broker, normaliza formatos | completo |
| `indicators.py` | ROI%, Beta, RSI(14d), Sharpe, Sortino, VaR 95%, max drawdown | completo |
| `macro.py` | Indicadores globales (VIX, DXY, US10Y) + Argentina (riesgo país, brecha, BCRA) | completo |
| `risk_engine.py` | HHI concentración, stress scenarios, correlation matrix, component VaR | completo |
| `rebalancer.py` | Rebalanceo mensual buy-only para $1M ARS aporte | completo |

---

## 2. MULTICANAL (Pricing + Sync Canales)
**`multicanal/`** — Motor de precios omnicanal, 13 archivos, **COMPLETO**

| Archivo | Qué hace | Estado |
|---------|----------|--------|
| `precios.py` | Motor pricing: `costo / (1 - margen - comision - comision_pago)` | completo |
| `canales.py` | Clases base + wrappers API (TN, ML, Meta) con rate limiting | completo |
| `tiendanube.py` | TiendaNube API client (productos, órdenes, store info) | completo |
| `facturador_tn.py` | Órdenes TN pagadas → INSERT ventas2/ventas1 (tipo B) | completo |
| `facturador_ml.py` | Ventas ML → INSERT ventas, dedup con SQLite | completo |
| `sync_stock.py` | Stock ERP → TiendaNube (depós 0+1) | completo |
| `sync_stock_ml.py` | Stock ERP → MercadoLibre (multiget API) | completo |
| `sync_precios.py` | Precios ERP → TN (tolerancia <2% ignora) | completo |
| `sync_precios_ml.py` | Precios ERP → ML (premium/clásica) | completo |
| `refresh_token_ml.py` | OAuth2 auto-refresh ML cada 5h | completo |
| `reglas_canales.json` | Reglas pricing por canal (ML Premium 16% comisión, TN 2.5%+4.5% MP, etc.) | completo |

---

## 3. REPOSICIÓN INTELIGENTE
**`app_reposicion.py`** (raíz) — Dashboard Streamlit, **COMPLETO con 2 gaps**

| Componente | Qué hace | Estado |
|------------|----------|--------|
| `analizar_quiebre_batch()` | Velocidad REAL corregida por quiebre (gold standard) | completo |
| `proyectar_waterfall()` | Proyección 15/30/45/60 días día a día | completo |
| `calcular_dias_cobertura()` | Cobertura advanced con vel_real + estacionalidad | completo |
| `calcular_roi()` | Días recupero + ROI 60d | completo |
| Dashboard "Meses Stock" | Usa vel_aparente en vez de real → sobreestima cobertura | **incompleto** |
| GMROI | No implementado | **incompleto** |
| Rotación explícita | No calculada | **incompleto** |

---

## 4. CALCE FINANCIERO / CFO DASHBOARD
**`_informes/calzalindo_informes_DEPLOY/`** — Controllers web2py + SQL + HTML, **COMPLETO**

### Controllers (5,540 líneas)

| Archivo | Qué hace | Estado |
|---------|----------|--------|
| `controllers/calce_financiero.py` | Conciliación financiera por industria: comprometido vs vendido, cash flow, recupero | completo |
| `controllers/reportes.py` | Dashboard maestro: KPIs, detalle proveedor, remitos, cache sync | completo |
| `controllers/ranking_consolidado.py` | Ranking productos por margen/velocidad/concentración (HHI) | completo |
| `controllers/informes_productividad.py` | Productividad ventas: dashboard RRHH, vendedor individual, simulador incentivos | completo |

### SQL Analytics (10 archivos)

| Archivo | Qué hace | Estado |
|---------|----------|--------|
| `sql/crear_calce_avanzado.sql` | Cash flow semanal 12 semanas, ROI proveedor, working capital con estacionalidad | completo |
| `sql/crear_presupuesto_industria.sql` | Presupuesto = ventas año anterior al costo mismo período | completo |
| `sql/ajuste_tendencia_presupuesto.sql` | Regresión lineal + índices estacionales para forecasting | completo |
| `sql/fix_capas_2_y_3.sql` | Sistema 3 capas de talles (equivalencias IRAM) | completo |
| `sql/crear_equivalencias_calzado_iram.sql` | Matriz talles AR↔IRAM↔EU↔US | completo |

### HTML Views
13 templates (dashboard, detalle industria, productividad, vendedor, estacionalidad, incentivos, ticket, ranking) — todos **completo**

---

## 5. SISTEMA FREELANCE (Comisión + Liquidación)
**`_freelance/`** — Red microemprendedores vs empleados (43% carga social → 5-8% comisión), **INCOMPLETO**

| Archivo | Qué hace | Estado |
|---------|----------|--------|
| `src/api/liquidacion.py` | Liquidación mensual: ventas × fee% - canon - monotributo = neto | completo |
| `src/api/vendedor.py` | Panel vendedor: KPIs, ventas, ranking, catálogo | completo |
| `src/api/gerencial.py` | Dashboard gerencial: KPIs red, ahorro vs empleado, alertas | completo |
| `src/api/atribucion.py` | Atribución venta: vendedor → canal (IG, WA, ML, local) | completo |
| `src/api/catalogo.py` | Productos con metadata social (títulos, hashtags, fotos) | completo |
| `src/main.py` | FastAPI entry point | completo |
| `src/sql/001_crear_tablas_freelance.sql` | 7 tablas en omicronvt | completo |
| `ARQUITECTURA_...md` | Spec completa 623 líneas, 8 módulos | completo |
| `CLZ_Modelo_Vendedor_Freelance.xlsx` | Modelo financiero: ahorro, monotributo, comisiones | completo |
| Generación contenido (Pillow) | Pre-armado para redes | **incompleto** |
| Integración ML/TN/WA API | Sync automático | **incompleto** |
| Auto-sync ventas1_vendedor | Atribución automática | **incompleto** |

---

## 6. MARKET INTELLIGENCE
**`market_intelligence/`** — Scraping ML, Google Trends, auditoría competencia, 12 archivos, **COMPLETO**

| Archivo | Qué hace | Estado |
|---------|----------|--------|
| `app_market.py` | Streamlit 8 tabs: scan ML, comparación categorías, cross-dashboard, auditoría social | completo |
| `ml_scraper.py` | Scraper MercadoLibre AR (precios, marcas, envío, descuentos) | completo |
| `analyzer.py` | Cálculo costos: FOB → landed ARS, segmentación economy/mid/premium | completo |
| `cross_analysis.py` | Motor agregación ML + Trends + costos → score compuesto 0-100 | completo |
| `trends.py` | Google Trends — factores estacionales, proyección 90 días | completo |
| `instagram.py` / `facebook.py` / `whatsapp.py` | Auditoría pública de perfiles sociales | completo |
| `website_audit.py` | Auditoría técnica: SSL, SEO, mobile, ecommerce | completo |
| `enviar_whatsapp_cerraduras.py` | Envío masivo WhatsApp cerraduras GO (Meta Cloud API via Chatwoot) | completo |
| `data/*.json` | ~60 scans históricos (valijas, calzado, cerraduras) | completo |

---

## 7. OBJETIVOS E INCENTIVOS
**`_informes/objetivos-luciano/`** — Metas, KPIs, compensación, **COMPLETO**

| Archivo | Qué hace | Estado |
|---------|----------|--------|
| `models/func_objetivos.py` | Funciones de objetivo: % cumplimiento, cálculo bonus | completo |
| `models/funciones_informes_consolidados.py` | Ranking consolidado, corrección velocidad, ponderación estacional | completo |
| `models/func_efectividad.py` | Métricas efectividad (conversión %, tasa cierre) | completo |
| `models/func_stock.py` | Funciones de stock | completo |
| `controllers/informes_productividad.py` | Dashboard productividad controller | completo |
| `controllers/informes_consolidados.py` | Reportes consolidados controller | completo |

---

## 8. PIPELINE DE COMPRAS (raíz)
**Raíz** — Pipeline pedido→factura, **COMPLETO**

| Archivo | Qué hace | Estado |
|---------|----------|--------|
| `config.py` | 5 proveedores + `calcular_precios()` (costo × utilidades) | completo |
| `paso4_insertar_pedido.py` | INSERT pedico2+pedico1 con routing empresa→base | completo |
| `paso8_carga_factura.py` | Carga factura OCR → actualización costos | completo |
| `paso2_buscar_articulo.py` | Lookup artículo + validación datos maestros | completo |
| `paso5_parsear_excel.py` | Parser Excel pedidos | completo |
| `paso6_flujo_completo.py` | Orquestador pipeline completo | completo |

---

## RESUMEN EJECUTIVO

| Sistema | Archivos | Estado |
|---------|----------|--------|
| Family Office | 12 | **COMPLETO** |
| Multicanal | 13 | **COMPLETO** |
| Reposición | 1 (grande) | **COMPLETO** (faltan GMROI, rotación) |
| Calce Financiero/CFO | 28 | **COMPLETO** |
| Freelance | 14 | **INCOMPLETO** (backend OK, UI/integraciones parcial) |
| Market Intelligence | 12 | **COMPLETO** |
| Objetivos/Incentivos | 11 | **COMPLETO** |
| Pipeline Compras | 6 | **COMPLETO** |

**Total: ~97 archivos relevantes. 7 de 8 sistemas completos. Único incompleto: Freelance (falta UI y sync automático).**

---

## Fórmulas clave implementadas

- **Velocidad real** = ventas meses con stock / cantidad meses con stock (excluye quiebre)
- **Margen bruto %** = (venta - costo) / venta × 100
- **ROI anualizado** = margen% × rotación_anual
- **HHI concentración** = Σ(peso_i²), rango 0-10000
- **Pricing multicanal** = costo / (1 - margen - comisión_canal - comisión_pago)
- **Cash flow 12 sem** = cobranzas estimadas - vencimientos PO comprometidos
- **Presupuesto** = ventas año anterior al costo mismo período + ajuste tendencia
