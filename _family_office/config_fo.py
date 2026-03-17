"""
Configuración del Family Office Dashboard
"""

# Target allocation (%) — ajustar según perfil de riesgo familiar
TARGET_ALLOCATION = {
    "Equity US": 35,
    "Equity LATAM/CEDEARs": 10,
    "Bonds / Renta Fija": 25,
    "Cash / Money Market": 15,
    "Crypto": 5,
    "Alternatives": 10,
}

# Alertas de rebalanceo
REBALANCE_THRESHOLD_PCT = 5  # alerta si desvío > 5% del target

# Risk
MAX_DRAWDOWN_ALERT = -15  # % — alerta si una posición cae más de esto desde su pico
MAX_CONCENTRATION_TOP5 = 40  # % — alerta si top 5 posiciones > 40% del portfolio

# Cash
CASH_DEPLOY_ALERT = 20  # % — si cash > 20%, señal de que hay que invertir

# Monedas relevantes
CURRENCIES = ["USD", "ARS", "EUR", "BRL"]

# IBKR config (para cuando se conecte la API real)
IBKR_CONFIG = {
    "host": "127.0.0.1",
    "port": 7497,  # 7497=paper, 7496=live
    "client_id": 1,
}
