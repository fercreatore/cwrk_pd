# CLAUDE.md — _family_office/

## QUÉ HACE
Dashboard Streamlit de gestión de portafolio de inversión personal/familiar. Conecta brokers (IOL, Cocos Capital), calcula indicadores técnicos, riesgo, macro, y rebalanceo. Target: 20% anual sobre cartera diversificada (bonos AR, CEDEARs, acciones AR, crypto, FCI).

**Completamente independiente del ERP y del proyecto de pedidos.**

---

## ARCHIVOS CLAVE

| Archivo | Función |
|---------|---------|
| `app_family_office.py` | Streamlit UI principal (port 8506) |
| `config_fo.py` | Allocación target, watchlist CEDEARs (Tier 1-3), límites riesgo (HHI, max concentración) |
| `csv_parser.py` | Parser CSV de Cocos/IOL + dólar MEP live (ArgentinaDatos API) |
| `broker_iol.py` | Conector IOL REST API (OAuth2 token refresh) |
| `broker_cocos.py` | Conector Cocos Capital via pycocos (TOTP 2FA) |
| `portfolio_live.py` | Agregador multi-broker (normaliza formatos) |
| `indicators.py` | ROI%, Beta, RSI(14d), volatilidad, max drawdown, Sharpe, Sortino, VaR 95% |
| `macro.py` | Indicadores globales (VIX, DXY, US 10Y) + Argentina (riesgo país, brecha, BCRA) |
| `risk_engine.py` | HHI concentración, stress scenarios (recesión, vol spike, crisis USD), correlación |
| `rebalancer.py` | Recomendaciones de asignación para flujo mensual $1M ARS (solo compra, nunca vende) |
| `mock_data.py` | Datos fallback cuando no hay .env configurado |

---

## CREDENCIALES

Archivo `.env` (NO commitear, copiar de `.env.example`):
- `IOL_USER`, `IOL_PASSWORD`
- `COCOS_EMAIL`, `COCOS_PASSWORD`, `COCOS_TOTP_SECRET`

---

## CÓMO SE USA

```bash
cd _family_office
cp .env.example .env  # configurar credenciales
streamlit run app_family_office.py  # → http://localhost:8506
```

---

## CONEXIÓN CON PROYECTO PRINCIPAL

**NINGUNA.** No usa SQL Server, no accede a msgestion, no se sincroniza con el 111. Es un proyecto personal de Fernando dentro del mismo repo por conveniencia.

## QUÉ NO TOCAR

- `data/` — CSV de portfolios reales (datos financieros personales)
- `.env` — credenciales de brokers
- Fórmulas de `risk_engine.py` — validadas contra benchmarks

## DEPENDENCIAS

streamlit, pandas, numpy, plotly, yfinance, requests, python-dotenv, pycocos (opcional)
