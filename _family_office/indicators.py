"""
Indicadores de portfolio para el Family Office Dashboard.

Indicadores por posición:
    - ROI %: retorno sobre inversión (si tenemos costo)
    - Beta: sensibilidad al mercado (vs SPY)
    - RSI (14d): sobrecompra (>70) / sobreventa (<30)
    - Volatilidad anualizada
    - Drawdown actual desde máximo 6m

Indicadores agregados del portfolio:
    - Sharpe Ratio (anualizado)
    - Beta del portfolio (ponderado)
    - VaR 95% (Value at Risk diario)
    - Volatilidad del portfolio
    - Correlación promedio entre posiciones
    - Sortino Ratio
"""
import math
import numpy as np
import pandas as pd
import yfinance as yf
from functools import lru_cache

# Mapeo de tickers CEDEAR/AR → ticker Yahoo Finance
# CEDEARs en Argentina terminan en C/D pero el subyacente es el ticker US
TICKER_MAP = {
    # CEDEARs → US ticker
    "NVDA": "NVDA", "NVDAC": "NVDA",
    "MELI": "MELI", "MELIC": "MELI",
    "MSTR": "MSTR", "MSTRC": "MSTR",
    "AMZN": "AMZN",
    "AVGO": "AVGO",
    "GLOBC": "GLOB", "GLOB": "GLOB",
    "MRKC": "MRK", "MRK": "MRK",
    "SPYC": "SPY", "SPY": "SPY",
    "IBIT": "IBIT",
    "BITFC": "BITF", "BITF": "BITF",
    "RBLX": "RBLX",
    "INTC": "INTC",
    "RGTI": "RGTI",
    "XLE": "XLE",
    "NU": "NU",
    "VIST": "VIST",
    "IBB": "IBB",
    "BIOXC": "BIOX",
    "OKLOC": "OKLO",
    # CEDEARs — targets para 20% anual
    "ASML": "ASML", "ASMLC": "ASML",  # Monopolio litografía EUV
    "TSM": "TSM", "TSMC": "TSM",      # TSMC — fabrica todos los chips
    "GOOGL": "GOOGL", "GOOGLC": "GOOGL",
    "GOOG": "GOOGL",
    "META": "META", "METAC": "META",
    "MSFT": "MSFT", "MSFTC": "MSFT",
    "AAPL": "AAPL", "AAPLC": "AAPL",
    "AMZNC": "AMZN",
    "V": "V", "VC": "V",              # Visa — monopolio pagos
    "LLY": "LLY", "LLYC": "LLY",     # Eli Lilly — GLP-1
    "COST": "COST",                    # Costco — defensive growth
    "UBER": "UBER",                    # Uber — mobility + delivery
    "NFLX": "NFLX",                    # Netflix
    "AMD": "AMD", "AMDC": "AMD",      # AMD — AI chips #2
    "PLTR": "PLTR",                    # Palantir — AI/data
    "SNOW": "SNOW",                    # Snowflake — data cloud
    "CRWD": "CRWD",                    # CrowdStrike — cybersecurity
    "PANW": "PANW",                    # Palo Alto — cybersecurity
    # Acciones argentinas (Yahoo usa .BA)
    "TGNO4": "TGNO4.BA",
    "TRAN": "TRAN.BA",
    "AUSO": "AUSO.BA",
    "TECO2": "TECO2.BA",
    "DGCU2": "DGCU2.BA",
    "GGAL": "GGAL",       # ADR en NYSE
    "YPF": "YPF",         # ADR en NYSE
    "PAMP": "PAM",         # ADR en NYSE
    "BBAR": "BBAR",        # ADR en NYSE
    "SUPV": "SUPV",        # ADR en NYSE
    "CEPU": "CEPU",        # ADR en NYSE
    "LOMA": "LOMA",        # ADR en NYSE
    "TXAR": "TXAR.BA",
    "ALUA": "ALUA.BA",
    "COME": "COME.BA",
    "EDN": "EDN.BA",
    "VALO": "VALO.BA",
    "BYMA": "BYMA.BA",
    # Crypto directo
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "VET": "VET-USD",
    "TRX": "TRX-USD",
    "VTHO": "VTHO-USD",
    # Bonos y FCI — no tienen ticker en Yahoo
    # Se marcan como None y se saltean
}

BENCHMARK = "SPY"
RISK_FREE_ANNUAL = 0.045  # 4.5% USD risk-free (T-bills)


@lru_cache(maxsize=1)
def _get_benchmark_returns(period="6mo"):
    """Descarga retornos diarios del benchmark."""
    data = yf.download(BENCHMARK, period=period, interval="1d", progress=False)
    if data.empty:
        return pd.Series(dtype=float)
    close = data["Close"].squeeze()
    return close.pct_change().dropna()


def _get_price_history(yahoo_ticker, period="6mo"):
    """Descarga historial de precios de un ticker."""
    try:
        data = yf.download(yahoo_ticker, period=period, interval="1d", progress=False)
        if data.empty:
            return None
        close = data["Close"].squeeze()
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        return close
    except Exception:
        return None


def calculate_rsi(prices, window=14):
    """RSI clásico de Wilder (14 días)."""
    if prices is None or len(prices) < window + 1:
        return None
    delta = prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty and not pd.isna(rsi.iloc[-1]) else None


def calculate_beta(returns, benchmark_returns):
    """Beta = Cov(asset, market) / Var(market)."""
    if returns is None or benchmark_returns is None:
        return None
    # Alinear por fecha
    aligned = pd.concat([returns, benchmark_returns], axis=1, join="inner").dropna()
    if len(aligned) < 20:
        return None
    aligned.columns = ["asset", "benchmark"]
    cov = aligned["asset"].cov(aligned["benchmark"])
    var = aligned["benchmark"].var()
    if var == 0:
        return None
    return round(cov / var, 2)


def calculate_volatility(returns, annualize=True):
    """Volatilidad (desvío estándar de retornos)."""
    if returns is None or len(returns) < 5:
        return None
    vol = returns.std()
    if annualize:
        vol *= math.sqrt(252)
    return round(vol * 100, 1)  # en porcentaje


def calculate_drawdown(prices):
    """Drawdown actual desde el máximo del período."""
    if prices is None or len(prices) < 2:
        return None
    peak = prices.cummax()
    dd = (prices - peak) / peak
    return round(dd.iloc[-1] * 100, 1)


def calculate_position_indicators(ticker, weight=0):
    """
    Calcula todos los indicadores para una posición individual.
    Retorna dict con los indicadores o None si no hay datos.
    """
    yahoo_ticker = TICKER_MAP.get(ticker)
    if not yahoo_ticker:
        return {
            "ticker": ticker,
            "yahoo": None,
            "beta": None,
            "rsi": None,
            "volatility": None,
            "drawdown_6m": None,
            "has_data": False,
        }

    prices = _get_price_history(yahoo_ticker, period="6mo")
    if prices is None or len(prices) < 20:
        return {
            "ticker": ticker,
            "yahoo": yahoo_ticker,
            "beta": None,
            "rsi": None,
            "volatility": None,
            "drawdown_6m": None,
            "has_data": False,
        }

    returns = prices.pct_change().dropna()
    benchmark_returns = _get_benchmark_returns("6mo")

    return {
        "ticker": ticker,
        "yahoo": yahoo_ticker,
        "beta": calculate_beta(returns, benchmark_returns),
        "rsi": round(calculate_rsi(prices), 1) if calculate_rsi(prices) is not None else None,
        "volatility": calculate_volatility(returns),
        "drawdown_6m": calculate_drawdown(prices),
        "has_data": True,
    }


def calculate_portfolio_indicators(positions):
    """
    Calcula indicadores agregados del portfolio.

    positions: lista de dicts con al menos 'ticker', 'market_value_usd', 'weight'

    Retorna dict con:
        - portfolio_beta
        - portfolio_volatility
        - portfolio_sharpe
        - portfolio_sortino
        - var_95 (Value at Risk diario en %)
        - avg_correlation
        - position_indicators: lista de indicadores por posición
    """
    benchmark_returns = _get_benchmark_returns("6mo")

    # Calcular indicadores por posición (solo las que tienen ticker en Yahoo)
    position_indicators = []
    weighted_beta = 0
    total_weight_with_data = 0

    # Recolectar retornos de cada posición para correlación y portfolio vol
    all_returns = {}

    for pos in positions:
        ticker = pos["ticker"]
        weight = pos.get("weight", 0)

        indicators = calculate_position_indicators(ticker, weight)
        indicators["weight"] = weight
        indicators["market_value_usd"] = pos.get("market_value_usd", 0)
        position_indicators.append(indicators)

        if indicators["has_data"] and indicators["beta"] is not None:
            weighted_beta += indicators["beta"] * (weight / 100)
            total_weight_with_data += weight

            yahoo_ticker = TICKER_MAP.get(ticker)
            if yahoo_ticker:
                prices = _get_price_history(yahoo_ticker, period="6mo")
                if prices is not None and len(prices) > 20:
                    all_returns[ticker] = prices.pct_change().dropna()

    # Ajustar beta por el peso que tiene data
    if total_weight_with_data > 0:
        portfolio_beta = round(weighted_beta / (total_weight_with_data / 100), 2)
    else:
        portfolio_beta = None

    # Portfolio volatility y Sharpe usando retornos ponderados
    portfolio_vol = None
    portfolio_sharpe = None
    portfolio_sortino = None
    var_95 = None
    avg_correlation = None

    if len(all_returns) >= 2:
        # Alinear retornos por fecha
        df_returns = pd.DataFrame(all_returns)
        df_returns = df_returns.dropna()

        if len(df_returns) > 20:
            # Pesos normalizados para posiciones con data
            weights_dict = {}
            for pos in positions:
                if pos["ticker"] in all_returns:
                    weights_dict[pos["ticker"]] = pos.get("weight", 0)
            total_w = sum(weights_dict.values())
            if total_w > 0:
                norm_weights = np.array([weights_dict.get(t, 0) / total_w for t in df_returns.columns])

                # Portfolio returns (ponderados)
                portfolio_returns = df_returns.values @ norm_weights

                # Volatilidad anualizada
                portfolio_vol = round(np.std(portfolio_returns) * math.sqrt(252) * 100, 1)

                # Sharpe
                rf_daily = (1 + RISK_FREE_ANNUAL) ** (1/252) - 1
                excess = portfolio_returns - rf_daily
                avg_excess = np.mean(excess)
                std_excess = np.std(excess)
                if std_excess > 0:
                    portfolio_sharpe = round((avg_excess / std_excess) * math.sqrt(252), 2)

                # Sortino (solo downside deviation)
                downside = excess[excess < 0]
                if len(downside) > 0:
                    downside_std = np.std(downside)
                    if downside_std > 0:
                        portfolio_sortino = round((avg_excess / downside_std) * math.sqrt(252), 2)

                # VaR 95% (paramétrico)
                var_95 = round(np.percentile(portfolio_returns, 5) * 100, 2)

            # Correlación promedio entre posiciones
            corr_matrix = df_returns.corr()
            n = len(corr_matrix)
            if n > 1:
                # Promedio de correlaciones off-diagonal
                mask = np.ones((n, n), dtype=bool)
                np.fill_diagonal(mask, False)
                avg_correlation = round(corr_matrix.values[mask].mean(), 2)

    return {
        "portfolio_beta": portfolio_beta,
        "portfolio_volatility": portfolio_vol,
        "portfolio_sharpe": portfolio_sharpe,
        "portfolio_sortino": portfolio_sortino,
        "var_95": var_95,
        "avg_correlation": avg_correlation,
        "position_indicators": position_indicators,
    }


def simulate_what_if(positions, add_ticker=None, add_amount_usd=0, remove_ticker=None):
    """
    Simula agregar o sacar una posición y recalcula indicadores del portfolio.

    add_ticker: ticker a agregar (ej: "NVDA")
    add_amount_usd: monto en USD a agregar
    remove_ticker: ticker a sacar completamente

    Retorna los mismos indicadores que calculate_portfolio_indicators.
    """
    # Clonar posiciones
    sim_positions = [p.copy() for p in positions]

    # Remover
    if remove_ticker:
        sim_positions = [p for p in sim_positions if p["ticker"] != remove_ticker]

    # Agregar
    if add_ticker and add_amount_usd > 0:
        existing = [p for p in sim_positions if p["ticker"] == add_ticker]
        if existing:
            existing[0]["market_value_usd"] += add_amount_usd
        else:
            sim_positions.append({
                "ticker": add_ticker,
                "market_value_usd": add_amount_usd,
                "name": add_ticker,
                "asset_class": "Simulación",
            })

    # Recalcular pesos
    total = sum(p["market_value_usd"] for p in sim_positions)
    for p in sim_positions:
        p["weight"] = (p["market_value_usd"] / total * 100) if total > 0 else 0

    return calculate_portfolio_indicators(sim_positions)


if __name__ == "__main__":
    # Test rápido con posiciones de ejemplo
    test_positions = [
        {"ticker": "NVDA", "market_value_usd": 12500, "weight": 30},
        {"ticker": "MELI", "market_value_usd": 2000, "weight": 5},
        {"ticker": "MSTR", "market_value_usd": 2700, "weight": 7},
        {"ticker": "IBIT", "market_value_usd": 900, "weight": 2},
        {"ticker": "TGNO4", "market_value_usd": 4100, "weight": 10},
    ]

    print("Calculando indicadores (descargando datos de Yahoo Finance)...")
    result = calculate_portfolio_indicators(test_positions)

    print(f"\n=== PORTFOLIO ===")
    print(f"  Beta: {result['portfolio_beta']}")
    print(f"  Volatilidad: {result['portfolio_volatility']}%")
    print(f"  Sharpe: {result['portfolio_sharpe']}")
    print(f"  Sortino: {result['portfolio_sortino']}")
    print(f"  VaR 95%: {result['var_95']}%")
    print(f"  Correlación promedio: {result['avg_correlation']}")

    print(f"\n=== POR POSICIÓN ===")
    for pi in result["position_indicators"]:
        rsi_str = f"{pi['rsi']}" if pi["rsi"] else "N/A"
        beta_str = f"{pi['beta']}" if pi["beta"] else "N/A"
        vol_str = f"{pi['volatility']}%" if pi["volatility"] else "N/A"
        dd_str = f"{pi['drawdown_6m']}%" if pi["drawdown_6m"] else "N/A"
        print(f"  {pi['ticker']:8s} | Beta: {beta_str:>5s} | RSI: {rsi_str:>5s} | Vol: {vol_str:>6s} | DD: {dd_str:>6s}")
