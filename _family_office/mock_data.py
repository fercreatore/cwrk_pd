"""
Datos mock para el MVP del Family Office Dashboard.
Cuando se conecte IBKR, estos se reemplazan por datos reales via API.
"""
import datetime
import random
import math

# --- PORTFOLIO MOCK ---

POSITIONS = [
    # Equity US
    {"ticker": "VOO", "name": "Vanguard S&P 500 ETF", "asset_class": "Equity US",
     "qty": 45, "avg_cost": 380.00, "current_price": 512.50, "currency": "USD"},
    {"ticker": "QQQ", "name": "Invesco Nasdaq 100 ETF", "asset_class": "Equity US",
     "qty": 20, "avg_cost": 340.00, "current_price": 485.20, "currency": "USD"},
    {"ticker": "AAPL", "name": "Apple Inc.", "asset_class": "Equity US",
     "qty": 30, "avg_cost": 155.00, "current_price": 228.80, "currency": "USD"},
    {"ticker": "MSFT", "name": "Microsoft Corp.", "asset_class": "Equity US",
     "qty": 15, "avg_cost": 310.00, "current_price": 445.60, "currency": "USD"},
    {"ticker": "GOOGL", "name": "Alphabet Inc.", "asset_class": "Equity US",
     "qty": 25, "avg_cost": 125.00, "current_price": 178.30, "currency": "USD"},

    # Equity LATAM / CEDEARs
    {"ticker": "MELI", "name": "MercadoLibre", "asset_class": "Equity LATAM/CEDEARs",
     "qty": 3, "avg_cost": 1250.00, "current_price": 2180.00, "currency": "USD"},
    {"ticker": "GGAL", "name": "Grupo Galicia ADR", "asset_class": "Equity LATAM/CEDEARs",
     "qty": 100, "avg_cost": 28.00, "current_price": 62.50, "currency": "USD"},
    {"ticker": "YPF", "name": "YPF S.A. ADR", "asset_class": "Equity LATAM/CEDEARs",
     "qty": 80, "avg_cost": 15.00, "current_price": 38.90, "currency": "USD"},

    # Bonds / Renta Fija
    {"ticker": "TLT", "name": "iShares 20+ Year Treasury ETF", "asset_class": "Bonds / Renta Fija",
     "qty": 50, "avg_cost": 98.00, "current_price": 91.20, "currency": "USD"},
    {"ticker": "AL30D", "name": "Bono Argentina 2030 (USD)", "asset_class": "Bonds / Renta Fija",
     "qty": 500, "avg_cost": 35.00, "current_price": 72.80, "currency": "USD"},
    {"ticker": "GD35D", "name": "Bono Argentina 2035 (USD)", "asset_class": "Bonds / Renta Fija",
     "qty": 300, "avg_cost": 30.00, "current_price": 65.40, "currency": "USD"},

    # Crypto
    {"ticker": "BTC", "name": "Bitcoin", "asset_class": "Crypto",
     "qty": 0.15, "avg_cost": 42000.00, "current_price": 84500.00, "currency": "USD"},
    {"ticker": "ETH", "name": "Ethereum", "asset_class": "Crypto",
     "qty": 2.0, "avg_cost": 2200.00, "current_price": 3950.00, "currency": "USD"},

    # Alternatives
    {"ticker": "GLD", "name": "SPDR Gold Trust", "asset_class": "Alternatives",
     "qty": 30, "avg_cost": 175.00, "current_price": 268.50, "currency": "USD"},
    {"ticker": "USO", "name": "US Oil Fund", "asset_class": "Alternatives",
     "qty": 40, "avg_cost": 72.00, "current_price": 78.30, "currency": "USD"},
]

CASH_POSITIONS = [
    {"currency": "USD", "amount": 25000.00, "location": "IBKR"},
    {"currency": "USD", "amount": 5000.00, "location": "Banco local"},
    {"currency": "ARS", "amount": 2500000.00, "location": "Banco local"},
]

# Tipo de cambio mock
FX_RATES = {
    "USD/ARS": 1180.0,
    "EUR/USD": 1.08,
    "BRL/USD": 0.19,
}


def get_portfolio_value():
    """Calcula el valor total del portfolio en USD."""
    total = 0
    for pos in POSITIONS:
        total += pos["qty"] * pos["current_price"]
    for cash in CASH_POSITIONS:
        if cash["currency"] == "USD":
            total += cash["amount"]
        elif cash["currency"] == "ARS":
            total += cash["amount"] / FX_RATES["USD/ARS"]
    return total


def get_positions_with_metrics():
    """Agrega métricas calculadas a cada posición."""
    portfolio_value = get_portfolio_value()
    results = []
    for pos in POSITIONS:
        market_value = pos["qty"] * pos["current_price"]
        cost_basis = pos["qty"] * pos["avg_cost"]
        pnl = market_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
        weight = (market_value / portfolio_value * 100) if portfolio_value > 0 else 0
        results.append({
            **pos,
            "market_value": market_value,
            "cost_basis": cost_basis,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "weight": weight,
        })
    return results


def get_allocation_actual():
    """Allocation real por asset class."""
    portfolio_value = get_portfolio_value()
    alloc = {}

    for pos in POSITIONS:
        mv = pos["qty"] * pos["current_price"]
        cls = pos["asset_class"]
        alloc[cls] = alloc.get(cls, 0) + mv

    # Cash
    total_cash_usd = 0
    for cash in CASH_POSITIONS:
        if cash["currency"] == "USD":
            total_cash_usd += cash["amount"]
        elif cash["currency"] == "ARS":
            total_cash_usd += cash["amount"] / FX_RATES["USD/ARS"]
    alloc["Cash / Money Market"] = total_cash_usd

    # Convertir a %
    result = {}
    for cls, val in alloc.items():
        result[cls] = round(val / portfolio_value * 100, 1) if portfolio_value > 0 else 0
    return result


def generate_historical_returns(months=12):
    """Genera retornos mensuales mock para calcular Sharpe."""
    random.seed(42)
    returns = []
    base_date = datetime.date(2025, 4, 1)
    for i in range(months):
        d = base_date + datetime.timedelta(days=30 * i)
        # Retorno mensual simulado: media 1.2%, vol 4%
        r = random.gauss(0.012, 0.04)
        returns.append({"date": d, "return": r})
    return returns


def calculate_sharpe(returns, risk_free_annual=0.045):
    """Sharpe ratio anualizado."""
    if not returns:
        return 0
    rf_monthly = (1 + risk_free_annual) ** (1/12) - 1
    excess = [r["return"] - rf_monthly for r in returns]
    avg = sum(excess) / len(excess)
    if len(excess) < 2:
        return 0
    var = sum((x - avg) ** 2 for x in excess) / (len(excess) - 1)
    std = math.sqrt(var)
    if std == 0:
        return 0
    return round((avg / std) * math.sqrt(12), 2)


def generate_portfolio_history(days=365):
    """Genera historia de valor del portfolio para drawdown."""
    random.seed(42)
    history = []
    base = 140000  # valor inicial hace 1 año
    value = base
    start = datetime.date(2025, 3, 15)
    for i in range(days):
        d = start + datetime.timedelta(days=i)
        # Random walk con drift positivo
        change = random.gauss(0.0004, 0.012)
        value *= (1 + change)
        history.append({"date": d, "value": value})
    return history


def calculate_drawdown(history):
    """Calcula drawdown actual y máximo."""
    if not history:
        return 0, 0
    peak = history[0]["value"]
    max_dd = 0
    for h in history:
        if h["value"] > peak:
            peak = h["value"]
        dd = (h["value"] - peak) / peak
        if dd < max_dd:
            max_dd = dd
    current_peak = max(h["value"] for h in history)
    current_dd = (history[-1]["value"] - current_peak) / current_peak
    return round(current_dd * 100, 1), round(max_dd * 100, 1)
