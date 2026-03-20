"""
Risk Engine — Análisis de riesgo nivel hedge fund.

Módulos:
    - Contribution to VaR (cuánto aporta cada posición al riesgo total)
    - HHI (Herfindahl-Hirschman Index) de concentración
    - Max single-name exposure
    - Stress scenarios (qué pasa si...)
    - Correlation matrix completa
    - Drawdown alerts por posición
    - Risk attribution por asset class
"""
import math
import numpy as np
import pandas as pd
import yfinance as yf
from indicators import TICKER_MAP, _get_price_history, _get_benchmark_returns


# ═══════════════════════════════════════════════════════════════
# CONCENTRATION RISK
# ═══════════════════════════════════════════════════════════════

def calculate_hhi(positions) -> dict:
    """
    Herfindahl-Hirschman Index de concentración.
    HHI = sum(weight_i^2) para todas las posiciones.
    Rango: 0 (infinitamente diversificado) a 10000 (1 sola posición).

    Benchmark:
        < 1500 = bien diversificado
        1500-2500 = moderadamente concentrado
        > 2500 = altamente concentrado
    """
    total = sum(p.get("market_value_usd", 0) for p in positions)
    if total <= 0:
        return {"hhi": 0, "interpretation": "Sin datos", "equivalent_positions": 0}

    weights = [(p.get("market_value_usd", 0) / total * 100) for p in positions]
    hhi = sum(w ** 2 for w in weights)

    # Equivalent number of positions (1/HHI * 10000)
    equiv = 10000 / hhi if hhi > 0 else len(positions)

    if hhi < 1500:
        interp = "Bien diversificado"
    elif hhi < 2500:
        interp = "Moderadamente concentrado"
    else:
        interp = "Altamente concentrado"

    return {
        "hhi": round(hhi, 0),
        "interpretation": interp,
        "equivalent_positions": round(equiv, 1),
    }


def calculate_concentration_metrics(positions) -> dict:
    """Métricas de concentración completas."""
    total = sum(p.get("market_value_usd", 0) for p in positions)
    if total <= 0:
        return {}

    sorted_pos = sorted(positions, key=lambda x: x.get("market_value_usd", 0), reverse=True)

    # Top N concentration
    top1 = sorted_pos[0].get("market_value_usd", 0) / total * 100 if sorted_pos else 0
    top3 = sum(p.get("market_value_usd", 0) for p in sorted_pos[:3]) / total * 100
    top5 = sum(p.get("market_value_usd", 0) for p in sorted_pos[:5]) / total * 100
    top10 = sum(p.get("market_value_usd", 0) for p in sorted_pos[:10]) / total * 100

    # By asset class
    by_class = {}
    for p in positions:
        cls = p.get("asset_class", "Otros")
        by_class[cls] = by_class.get(cls, 0) + p.get("market_value_usd", 0)
    class_weights = {cls: v / total * 100 for cls, v in by_class.items()}
    max_class = max(class_weights.items(), key=lambda x: x[1]) if class_weights else ("", 0)

    # Max single-name
    max_position = sorted_pos[0] if sorted_pos else {}

    hhi = calculate_hhi(positions)

    return {
        "top1_pct": round(top1, 1),
        "top1_ticker": max_position.get("ticker", ""),
        "top3_pct": round(top3, 1),
        "top5_pct": round(top5, 1),
        "top10_pct": round(top10, 1),
        "max_class_name": max_class[0],
        "max_class_pct": round(max_class[1], 1),
        "class_weights": {k: round(v, 1) for k, v in class_weights.items()},
        "hhi": hhi["hhi"],
        "hhi_interpretation": hhi["interpretation"],
        "equivalent_positions": hhi["equivalent_positions"],
        "total_positions": len(positions),
    }


# ═══════════════════════════════════════════════════════════════
# CONTRIBUTION TO VAR
# ═══════════════════════════════════════════════════════════════

def calculate_component_var(positions, confidence=0.95, period="6mo") -> dict:
    """
    Component VaR — cuánto contribuye cada posición al VaR total.

    Método: Marginal VaR × peso de la posición.
    Component VaR_i = weight_i × cov(r_i, r_portfolio) / sigma_portfolio × z_score

    Retorna dict con:
        - portfolio_var_pct: VaR total del portfolio (%)
        - portfolio_var_usd: VaR en USD
        - components: lista de {ticker, weight, component_var_pct, component_var_usd, pct_of_total_var}
    """
    total = sum(p.get("market_value_usd", 0) for p in positions)
    if total <= 0:
        return {"portfolio_var_pct": 0, "portfolio_var_usd": 0, "components": []}

    # Recolectar retornos
    returns_dict = {}
    weights_dict = {}
    for p in positions:
        ticker = p["ticker"]
        yahoo = TICKER_MAP.get(ticker)
        if not yahoo:
            continue
        prices = _get_price_history(yahoo, period=period)
        if prices is not None and len(prices) > 20:
            returns_dict[ticker] = prices.pct_change().dropna()
            weights_dict[ticker] = p.get("market_value_usd", 0) / total

    if len(returns_dict) < 2:
        return {"portfolio_var_pct": 0, "portfolio_var_usd": 0, "components": []}

    # Alinear
    df_ret = pd.DataFrame(returns_dict).dropna()
    if len(df_ret) < 20:
        return {"portfolio_var_pct": 0, "portfolio_var_usd": 0, "components": []}

    tickers = list(df_ret.columns)
    weights = np.array([weights_dict.get(t, 0) for t in tickers])
    weights = weights / weights.sum()  # normalizar

    # Covariance matrix
    cov_matrix = df_ret.cov().values * 252  # annualized

    # Portfolio variance y volatility
    port_var = weights @ cov_matrix @ weights
    port_vol = math.sqrt(port_var)

    # Z-score para 95% confidence
    from scipy.stats import norm
    z = norm.ppf(1 - confidence)

    portfolio_var_pct = round(z * port_vol * 100 / math.sqrt(252), 2)  # daily
    portfolio_var_usd = round(total * portfolio_var_pct / 100, 0)

    # Component VaR
    # marginal_var_i = (cov_matrix @ weights)[i] / port_vol
    # component_var_i = weight_i × marginal_var_i × z
    marginal_var = (cov_matrix @ weights) / port_vol
    component_vars = weights * marginal_var * z / math.sqrt(252)

    components = []
    for i, ticker in enumerate(tickers):
        comp_var_pct = round(component_vars[i] * 100, 2)
        comp_var_usd = round(total * comp_var_pct / 100, 0)
        pct_of_total = round(comp_var_pct / portfolio_var_pct * 100, 1) if portfolio_var_pct != 0 else 0

        components.append({
            "ticker": ticker,
            "weight_pct": round(weights[i] * 100, 1),
            "component_var_pct": comp_var_pct,
            "component_var_usd": comp_var_usd,
            "pct_of_total_var": pct_of_total,
        })

    # Sort by absolute contribution (most risky first)
    components.sort(key=lambda x: abs(x["component_var_pct"]), reverse=True)

    return {
        "portfolio_var_pct": portfolio_var_pct,
        "portfolio_var_usd": portfolio_var_usd,
        "portfolio_vol_annual": round(port_vol * 100, 1),
        "components": components,
    }


# ═══════════════════════════════════════════════════════════════
# CORRELATION MATRIX
# ═══════════════════════════════════════════════════════════════

def calculate_correlation_matrix(positions, period="6mo") -> dict:
    """
    Correlation matrix completa entre posiciones.
    Retorna DataFrame de correlaciones y métricas de diversificación.
    """
    returns_dict = {}
    for p in positions:
        ticker = p["ticker"]
        yahoo = TICKER_MAP.get(ticker)
        if not yahoo:
            continue
        prices = _get_price_history(yahoo, period=period)
        if prices is not None and len(prices) > 20:
            returns_dict[ticker] = prices.pct_change().dropna()

    if len(returns_dict) < 2:
        return {"matrix": pd.DataFrame(), "avg_correlation": None, "max_pair": None, "min_pair": None}

    df_ret = pd.DataFrame(returns_dict).dropna()
    corr = df_ret.corr()

    # Stats
    n = len(corr)
    mask = np.ones((n, n), dtype=bool)
    np.fill_diagonal(mask, False)
    off_diag = corr.values[mask]

    avg_corr = round(float(np.mean(off_diag)), 2)

    # Max and min pairs
    max_val = -1
    min_val = 1
    max_pair = ("", "")
    min_pair = ("", "")
    for i in range(n):
        for j in range(i + 1, n):
            val = corr.iloc[i, j]
            if val > max_val:
                max_val = val
                max_pair = (corr.index[i], corr.columns[j])
            if val < min_val:
                min_val = val
                min_pair = (corr.index[i], corr.columns[j])

    return {
        "matrix": corr,
        "avg_correlation": avg_corr,
        "max_pair": {"tickers": max_pair, "correlation": round(max_val, 2)},
        "min_pair": {"tickers": min_pair, "correlation": round(min_val, 2)},
        "diversification_score": round((1 - avg_corr) * 100, 0),  # 0=idénticos, 100=descorrelacionados
    }


# ═══════════════════════════════════════════════════════════════
# STRESS SCENARIOS
# ═══════════════════════════════════════════════════════════════

STRESS_SCENARIOS = {
    "dolar_30pct": {
        "name": "Devaluación 30%",
        "description": "El dólar sube 30% (MEP pasa de ~$1200 a ~$1560)",
        "shocks": {
            "Bonos Soberanos AR": -8,    # bonos hard-dollar caen por riesgo país
            "FCI / Money Market": -2,     # FCI USD casi neutro, ARS pierde
            "CEDEARs": +25,              # suben en ARS por efecto dólar
            "Acciones AR": -15,           # caen en USD
            "Crypto": +5,                # levemente positivo (dolarizado)
        },
    },
    "milei_pierde": {
        "name": "Crisis política (cambio de gobierno)",
        "description": "Milei pierde poder, vuelve el populismo",
        "shocks": {
            "Bonos Soberanos AR": -35,
            "FCI / Money Market": -10,
            "CEDEARs": -5,
            "Acciones AR": -40,
            "Crypto": -10,
        },
    },
    "btc_crash_40": {
        "name": "BTC crash -40%",
        "description": "Bitcoin cae 40% desde niveles actuales",
        "shocks": {
            "Bonos Soberanos AR": 0,
            "FCI / Money Market": 0,
            "CEDEARs": -5,               # tech correlacionado
            "Acciones AR": 0,
            "Crypto": -40,
        },
    },
    "recesion_global": {
        "name": "Recesión global 2008-style",
        "description": "S&P500 -30%, emergentes -40%, credit freeze",
        "shocks": {
            "Bonos Soberanos AR": -25,
            "FCI / Money Market": -5,
            "CEDEARs": -30,
            "Acciones AR": -45,
            "Crypto": -50,
        },
    },
    "argentina_upgrade": {
        "name": "Argentina investment grade",
        "description": "Riesgo país < 300bp, entra a MSCI Emergentes",
        "shocks": {
            "Bonos Soberanos AR": +40,
            "FCI / Money Market": +5,
            "CEDEARs": +15,
            "Acciones AR": +60,
            "Crypto": +5,
        },
    },
    "fed_cuts_aggressive": {
        "name": "Fed baja tasas agresivamente",
        "description": "Fed funds de 5% a 3% en 6 meses",
        "shocks": {
            "Bonos Soberanos AR": +15,
            "FCI / Money Market": -3,     # money market rinde menos
            "CEDEARs": +20,
            "Acciones AR": +25,
            "Crypto": +30,
        },
    },
}


def run_stress_test(positions, scenario_key) -> dict:
    """
    Corre un stress test sobre el portfolio.

    Retorna:
        - scenario: nombre y descripción
        - current_total_usd: total actual
        - stressed_total_usd: total post-shock
        - pnl_usd: ganancia/pérdida
        - pnl_pct: % cambio
        - by_class: detalle por asset class
    """
    scenario = STRESS_SCENARIOS.get(scenario_key)
    if not scenario:
        return {"error": f"Escenario '{scenario_key}' no encontrado"}

    total = sum(p.get("market_value_usd", 0) for p in positions)
    if total <= 0:
        return {"error": "Portfolio vacío"}

    # Agrupar por clase
    by_class = {}
    for p in positions:
        cls = p.get("asset_class", "Otros")
        by_class[cls] = by_class.get(cls, 0) + p.get("market_value_usd", 0)

    # Aplicar shocks
    stressed_by_class = {}
    for cls, value in by_class.items():
        shock_pct = scenario["shocks"].get(cls, 0)
        stressed_value = value * (1 + shock_pct / 100)
        stressed_by_class[cls] = {
            "current_usd": round(value, 0),
            "shock_pct": shock_pct,
            "stressed_usd": round(stressed_value, 0),
            "pnl_usd": round(stressed_value - value, 0),
        }

    stressed_total = sum(v["stressed_usd"] for v in stressed_by_class.values())
    pnl = stressed_total - total
    pnl_pct = (pnl / total * 100) if total > 0 else 0

    return {
        "scenario_key": scenario_key,
        "scenario_name": scenario["name"],
        "scenario_desc": scenario["description"],
        "current_total_usd": round(total, 0),
        "stressed_total_usd": round(stressed_total, 0),
        "pnl_usd": round(pnl, 0),
        "pnl_pct": round(pnl_pct, 1),
        "by_class": stressed_by_class,
    }


def run_all_stress_tests(positions) -> list:
    """Corre todos los escenarios de stress."""
    results = []
    for key in STRESS_SCENARIOS:
        results.append(run_stress_test(positions, key))
    return results


# ═══════════════════════════════════════════════════════════════
# DRAWDOWN ALERTS
# ═══════════════════════════════════════════════════════════════

def check_drawdown_alerts(positions, max_dd_pct=-15) -> list:
    """
    Revisa cada posición por drawdown excesivo.
    Retorna lista de alertas para posiciones que superan el umbral.
    """
    alerts = []
    for p in positions:
        ticker = p["ticker"]
        yahoo = TICKER_MAP.get(ticker)
        if not yahoo:
            continue
        prices = _get_price_history(yahoo, period="6mo")
        if prices is None or len(prices) < 20:
            continue

        peak = prices.max()
        current = prices.iloc[-1]
        dd = (current / peak - 1) * 100

        if dd < max_dd_pct:
            alerts.append({
                "ticker": ticker,
                "drawdown_pct": round(dd, 1),
                "peak_price": round(float(peak), 2),
                "current_price": round(float(current), 2),
                "value_usd": p.get("market_value_usd", 0),
                "weight_pct": p.get("weight", 0),
                "severity": "CRITICAL" if dd < max_dd_pct * 1.5 else "WARNING",
            })

    alerts.sort(key=lambda x: x["drawdown_pct"])
    return alerts


# ═══════════════════════════════════════════════════════════════
# RISK ATTRIBUTION BY CLASS
# ═══════════════════════════════════════════════════════════════

def calculate_risk_attribution(positions, period="6mo") -> dict:
    """
    Cuánto del riesgo total viene de cada asset class.
    Usa volatilidad ponderada por peso.
    """
    total = sum(p.get("market_value_usd", 0) for p in positions)
    if total <= 0:
        return {}

    # Calcular vol por clase
    by_class = {}
    for p in positions:
        cls = p.get("asset_class", "Otros")
        if cls not in by_class:
            by_class[cls] = {"value": 0, "vols": [], "weights": []}
        by_class[cls]["value"] += p.get("market_value_usd", 0)

        yahoo = TICKER_MAP.get(p["ticker"])
        if yahoo:
            prices = _get_price_history(yahoo, period=period)
            if prices is not None and len(prices) > 20:
                vol = float(prices.pct_change().dropna().std() * math.sqrt(252))
                weight = p.get("market_value_usd", 0) / total
                by_class[cls]["vols"].append(vol)
                by_class[cls]["weights"].append(weight)

    # Risk contribution = weight × volatility (simplificado, ignora correlaciones intra-clase)
    risk_contribs = {}
    total_risk = 0
    for cls, data in by_class.items():
        class_weight = data["value"] / total
        if data["vols"]:
            avg_vol = np.average(data["vols"], weights=data["weights"]) if data["weights"] else np.mean(data["vols"])
        else:
            avg_vol = 0
        risk_contrib = class_weight * avg_vol
        total_risk += risk_contrib
        risk_contribs[cls] = {
            "weight_pct": round(class_weight * 100, 1),
            "avg_vol_annual": round(avg_vol * 100, 1),
            "risk_contribution": risk_contrib,
        }

    # Normalizar a % del total
    for cls in risk_contribs:
        rc = risk_contribs[cls]["risk_contribution"]
        risk_contribs[cls]["risk_pct_of_total"] = round(rc / total_risk * 100, 1) if total_risk > 0 else 0

    return {
        "by_class": risk_contribs,
        "total_portfolio_risk": round(total_risk * 100, 1),
    }


# ═══════════════════════════════════════════════════════════════
# SCORING MODEL (señales consolidadas)
# ═══════════════════════════════════════════════════════════════

def calculate_risk_score(positions, portfolio_indicators, macro_score=0) -> dict:
    """
    Score consolidado de riesgo del portfolio (0-100).
    0 = máximo riesgo, 100 = portfolio ideal.

    Factores:
        - Diversificación (HHI) — 25%
        - Drawdown — 20%
        - Volatilidad vs benchmark — 20%
        - Macro context — 20%
        - Sharpe ratio — 15%
    """
    score = 0
    factors = []

    # 1. Diversificación (25 pts)
    hhi = calculate_hhi(positions)
    if hhi["hhi"] < 1000:
        div_score = 25
    elif hhi["hhi"] < 1500:
        div_score = 20
    elif hhi["hhi"] < 2500:
        div_score = 12
    else:
        div_score = 5
    score += div_score
    factors.append({"factor": "Diversificación", "score": div_score, "max": 25,
                     "detail": f"HHI={hhi['hhi']:.0f} ({hhi['interpretation']})"})

    # 2. Drawdown (20 pts)
    dd_alerts = check_drawdown_alerts(positions)
    critical = len([a for a in dd_alerts if a["severity"] == "CRITICAL"])
    warnings = len([a for a in dd_alerts if a["severity"] == "WARNING"])
    if critical == 0 and warnings == 0:
        dd_score = 20
    elif critical == 0:
        dd_score = 15 - warnings
    else:
        dd_score = max(0, 8 - critical * 3)
    score += dd_score
    factors.append({"factor": "Drawdown", "score": dd_score, "max": 20,
                     "detail": f"{critical} críticos, {warnings} warnings"})

    # 3. Volatilidad (20 pts)
    port_vol = portfolio_indicators.get("portfolio_volatility")
    if port_vol is not None:
        if port_vol < 15:
            vol_score = 20
        elif port_vol < 25:
            vol_score = 15
        elif port_vol < 35:
            vol_score = 10
        else:
            vol_score = 5
    else:
        vol_score = 10  # sin data, neutro
    score += vol_score
    factors.append({"factor": "Volatilidad", "score": vol_score, "max": 20,
                     "detail": f"{port_vol}%" if port_vol else "Sin data"})

    # 4. Macro context (20 pts)
    if macro_score >= 2:
        macro_pts = 20
    elif macro_score >= 0:
        macro_pts = 15
    elif macro_score >= -1:
        macro_pts = 10
    else:
        macro_pts = 5
    score += macro_pts
    factors.append({"factor": "Contexto macro", "score": macro_pts, "max": 20,
                     "detail": f"Score liquidez: {macro_score}"})

    # 5. Sharpe (15 pts)
    sharpe = portfolio_indicators.get("portfolio_sharpe")
    if sharpe is not None:
        if sharpe > 1.5:
            sh_score = 15
        elif sharpe > 1.0:
            sh_score = 12
        elif sharpe > 0.5:
            sh_score = 8
        elif sharpe > 0:
            sh_score = 5
        else:
            sh_score = 2
    else:
        sh_score = 7
    score += sh_score
    factors.append({"factor": "Sharpe Ratio", "score": sh_score, "max": 15,
                     "detail": f"{sharpe}" if sharpe else "Sin data"})

    # Interpretar
    if score >= 80:
        rating = "EXCELENTE"
        color = "green"
    elif score >= 65:
        rating = "BUENO"
        color = "green"
    elif score >= 50:
        rating = "ACEPTABLE"
        color = "yellow"
    elif score >= 35:
        rating = "MEJORABLE"
        color = "orange"
    else:
        rating = "RIESGOSO"
        color = "red"

    return {
        "score": score,
        "max_score": 100,
        "rating": rating,
        "color": color,
        "factors": factors,
    }
