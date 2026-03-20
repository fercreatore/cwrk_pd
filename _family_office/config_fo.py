"""
Configuración del Family Office Dashboard
"""

# Target allocation (%) — Objetivo: 20% anual USD, agresivo, con liquidez para dips
# Actualizado: marzo 2026 — rotación de FCI a CEDEARs para subir rendimiento
TARGET_ALLOCATION = {
    "Bonos Soberanos AR": 30,    # Hard-dollar (GD35/AE38/AL41) + BONCER (TX28/TX31) → 10% carry
    "FCI / Money Market": 8,     # COCOUSDPA solo — liquidez mínima para deployar en dips
    "CEDEARs": 37,               # ASML, TSM, NVDA, GOOGL, META, V, LLY → motor de 20%+
    "Acciones AR": 13,           # Post-crash Merval: TGNO4, AUSO, TRAN, GGAL, YPF
    "Crypto": 12,                # BTC directo + MSTR/IBIT → apuesta asimétrica
}

# Watchlist de CEDEARs target para 20% anual — diversificado por sector
CEDEAR_WATCHLIST = {
    # Tier 1: Sobrevendidos HOY (RSI < 35) — comprar YA
    "TSM":   {"sector": "Semiconductores", "tesis": "Fabrica chips NVDA/AAPL/AMD. RSI 33, +93% 1Y", "tier": 1},
    "META":  {"sector": "Tech/Ads",        "tesis": "PE 26, cash machine, -20% 6m. AI infra", "tier": 1},
    "V":     {"sector": "Pagos",           "tesis": "Monopolio pagos, RSI 16 extremo. Defensive", "tier": 1},
    "LLY":   {"sector": "Pharma",          "tesis": "GLP-1 (Ozempic rival), RSI 18. Mega trend", "tier": 1},
    "AAPL":  {"sector": "Tech/Consumer",   "tesis": "RSI 26, ecosystem 2B devices. Raro verla tan baja", "tier": 1},
    # Tier 2: Buenos precios, buen momentum
    "ASML":  {"sector": "Semiconductores", "tesis": "Monopolio EUV, +88% 1Y, pullback sano", "tier": 2},
    "GOOGL": {"sector": "Tech/AI",         "tesis": "PE 28 más barata big tech. AI + search + cloud", "tier": 2},
    "NVDA":  {"sector": "Semiconductores", "tesis": "Ya tenés — mantener, no agregar mucho más", "tier": 2},
    # Tier 3: Para armar después
    "AMZN":  {"sector": "Tech/Cloud",      "tesis": "AWS + retail. Momentum tibio hoy", "tier": 3},
    "MELI":  {"sector": "LATAM/Fintech",   "tesis": "-32% 6m, recovery play. Alto riesgo LatAm", "tier": 3},
    "AVGO":  {"sector": "Semiconductores", "tesis": "Networking AI, PE 63 caro. Esperar dip", "tier": 3},
}

# Aporte mensual en ARS
APORTE_MENSUAL_ARS = 1_000_000

# Alertas de rebalanceo
REBALANCE_THRESHOLD_PCT = 5  # alerta si desvío > 5% del target

# Risk
MAX_DRAWDOWN_ALERT = -15  # % — alerta si una posición cae más de esto desde su pico
MAX_CONCENTRATION_TOP5 = 40  # % — alerta si top 5 posiciones > 40% del portfolio

# Cash
CASH_DEPLOY_ALERT = 20  # % — si cash > 20%, señal de que hay que invertir

# Monedas relevantes
CURRENCIES = ["USD", "ARS", "EUR", "BRL"]

# Risk limits (hedge fund-grade)
MAX_SINGLE_NAME_PCT = 25     # ninguna posición > 25% del portfolio
HHI_ALERT_THRESHOLD = 2500   # alerta si HHI > 2500 (altamente concentrado)
MAX_CLASS_PCT = 45            # ninguna asset class > 45%
VAR_95_DAILY_LIMIT = -3.0    # VaR 95% diario máximo aceptable (%)

# Cross-analysis: umbrales para señales cruzadas
CROSS_ANALYSIS = {
    "vix_alto": 25,           # VIX > 25 = miedo
    "vix_panico": 30,         # VIX > 30 = pánico (oportunidad contrarian)
    "dxy_fuerte": 3,          # DXY +3% 6m = USD fuerte
    "sp_sobrevendido": 35,    # S&P RSI < 35
    "brecha_baja": 8,         # brecha < 8% = ventana de dolarización
    "brecha_alta": 20,        # brecha > 20% = presión devaluatoria
    "rp_bajo": 600,           # RP < 600bp = zona favorable
    "rp_alto": 800,           # RP > 800bp = stress
}

# IBKR config (para cuando se conecte la API real)
IBKR_CONFIG = {
    "host": "127.0.0.1",
    "port": 7497,  # 7497=paper, 7496=live
    "client_id": 1,
}
