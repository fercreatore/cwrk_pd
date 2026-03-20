"""
Configuración del Family Office Dashboard
"""

# Target allocation (%) — Objetivo: 15% anual USD, largo plazo, con liquidez para dips
# Aprobado: marzo 2026
TARGET_ALLOCATION = {
    "Bonos Soberanos AR": 35,    # Hard-dollar (GD35/AE38/AL41) + BONCER (TX28/TX31) → 10% carry
    "FCI / Money Market": 15,    # COCOUSDPA + FCI ARS → liquidez para oportunidades
    "CEDEARs": 30,               # NVDA, MELI, growth stocks → motor de 15%+ USD
    "Acciones AR": 10,           # Post-crash Merval, selectivas (TGNO4, AUSO)
    "Crypto": 10,                # MSTR, IBIT, BITFC → apuesta asimétrica
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
