# CLAUDE.md — market_intelligence/

## QUÉ HACE
Sistema de inteligencia de mercado para evaluar oportunidades de importación. Combina scraping de MercadoLibre, Google Trends, cálculo de costos landed, y auditoría digital de competidores. Dashboard Streamlit con 8 tabs.

---

## ARCHIVOS CLAVE

| Archivo | Función |
|---------|---------|
| `app_market.py` | Streamlit UI (8 tabs): scan ML, comparar categorías, dashboard cruzado, redes, web audit, competidores, exportar, historial |
| `ml_scraper.py` | Scraper de MercadoLibre AR — precios, marcas, envío, descuentos |
| `analyzer.py` | Cálculo costos importación (FOB → landed ARS), análisis precio, segmentación (económico/medio/premium) |
| `cross_analysis.py` | Motor de agregación: ML + Trends + costos + competidores → score compuesto (0-100) |
| `trends.py` | Google Trends — factores estacionales, proyección demanda 90 días |
| `instagram.py` | Auditoría perfil público IG (followers, posts, bio) |
| `facebook.py` | Auditoría página FB (likes, followers, categoría, rating) |
| `whatsapp.py` | Check WhatsApp Business (catálogo, nombre, descripción) |
| `website_audit.py` | Auditoría técnica web: SSL, SEO, mobile, ecommerce |
| `skills.py` | Orquestador de auditoría multicanal unificada |
| `enviar_whatsapp_cerraduras.py` | Envío masivo WA para cerraduras GO via Chatwoot (Meta Cloud API) |

---

## DATA

Carpeta `data/` con ~60 JSON históricos de scans (valijas, calzado, cerraduras, etc.). Son datos de referencia para tracking de evolución de precios.

---

## ALGORITMOS CLAVE

- **HHI** (Herfindahl-Hirschman): concentración de marcas (0=fragmentado, 1=monopolio)
- **Cuadrantes**: ESTRELLA (alto margen + mercado grande), NICHO RENTABLE, VOLUMEN, DESCARTE
- **Breakeven**: margen mínimo 25% para viabilidad
- **Seasonal adjustment**: factor Google Trends (1.2x+ = importar ahora)

---

## CÓMO SE USA

```bash
streamlit run market_intelligence/app_market.py
```

```python
from market_intelligence import MLScraper, CrossAnalyzer
scraper = MLScraper()
items = scraper.search("valijas de viaje", pages=2)

ca = CrossAnalyzer(exchange_rate=1250)
result = ca.full_cross_analysis(query="valijas carry on", landed_cost_usd=12)
```

---

## CONEXIÓN CON PROYECTO PRINCIPAL

**Independiente** — no accede a SQL Server ni al ERP. Usa solo APIs públicas (MercadoLibre, Google Trends, redes sociales). Sirve como herramienta de investigación pre-compra: evaluar viabilidad antes de generar pedidos.

## QUÉ NO TOCAR

- `data/*.json` — histórico de scans, no borrar (se usa para tracking evolución)
- Rate limits de Google Trends (3 retries con backoff)

## DEPENDENCIAS

beautifulsoup4, pandas, pytrends, requests, lxml, streamlit, plotly
