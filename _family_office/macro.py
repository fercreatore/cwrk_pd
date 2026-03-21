"""
Indicadores macro globales y de Argentina.
Fuentes: Yahoo Finance (global), BCRA API (cambiario), APIs públicas.
"""
import requests
import yfinance as yf
import pandas as pd
import numpy as np
from functools import lru_cache
from datetime import datetime, timedelta


# ============================================================
# GLOBAL LIQUIDITY & MARKET INDICATORS (Yahoo Finance)
# ============================================================

GLOBAL_TICKERS = {
    "^VIX": {"name": "VIX (Índice de Miedo)", "category": "Sentimiento",
             "interpretation": "Alto (>25) = miedo, Bajo (<15) = complacencia"},
    "^TNX": {"name": "US 10Y Treasury Yield", "category": "Tasas",
             "interpretation": "Sube = se encarece el crédito, Baja = flight to quality"},
    "DX-Y.NYB": {"name": "DXY (Índice Dólar)", "category": "Liquidez",
                  "interpretation": "Sube = USD fuerte (malo para emergentes), Baja = liquidez global"},
    "GLD": {"name": "Oro (GLD ETF)", "category": "Refugio",
            "interpretation": "Sube = flight to safety / inflación"},
    "BTC-USD": {"name": "Bitcoin", "category": "Liquidez / Risk-on",
                "interpretation": "Sube con liquidez global. Proxy de apetito por riesgo"},
    "^GSPC": {"name": "S&P 500", "category": "Equity Global",
              "interpretation": "Benchmark de renta variable global"},
    "TLT": {"name": "US Bonds 20Y+ (TLT)", "category": "Renta Fija",
            "interpretation": "Sube = tasas bajan. Inversamente correlacionado con acciones"},
    "EEM": {"name": "Emerging Markets ETF", "category": "Emergentes",
            "interpretation": "Sube = flujo hacia emergentes. Correlaciona con Argentina"},
    "HYG": {"name": "High Yield Corp Bonds", "category": "Crédito",
            "interpretation": "Baja = stress crediticio. Leading indicator de recesión"},
}


def get_global_indicators(period="6mo"):
    """Descarga indicadores globales de Yahoo Finance."""
    results = []
    tickers_str = " ".join(GLOBAL_TICKERS.keys())

    try:
        data = yf.download(tickers_str, period=period, interval="1d", progress=False, group_by="ticker")
    except Exception:
        data = pd.DataFrame()

    for ticker, info in GLOBAL_TICKERS.items():
        try:
            if len(GLOBAL_TICKERS) > 1 and ticker in data.columns.get_level_values(0):
                close = data[ticker]["Close"].dropna()
            else:
                close = data["Close"].dropna()

            if close.empty:
                continue

            current = float(close.iloc[-1])
            prev_close = float(close.iloc[-2]) if len(close) > 1 else current
            first = float(close.iloc[0])

            # Cambios
            daily_chg = (current / prev_close - 1) * 100
            period_chg = (current / first - 1) * 100

            # Máximo y mínimo del período
            high = float(close.max())
            low = float(close.min())

            # RSI simplificado
            if len(close) > 14:
                delta = close.diff()
                gain = delta.where(delta > 0, 0.0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
                rs = gain / loss.replace(0, np.nan)
                rsi = 100 - (100 / (1 + rs))
                rsi_val = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None
            else:
                rsi_val = None

            # Posición relativa en rango 6m (0% = mínimo, 100% = máximo)
            if high != low:
                range_pct = (current - low) / (high - low) * 100
            else:
                range_pct = 50

            results.append({
                "ticker": ticker,
                "name": info["name"],
                "category": info["category"],
                "current": current,
                "daily_chg": round(daily_chg, 2),
                "period_chg": round(period_chg, 1),
                "high_6m": high,
                "low_6m": low,
                "range_pct": round(range_pct, 1),
                "rsi": round(rsi_val, 1) if rsi_val else None,
                "interpretation": info["interpretation"],
            })
        except Exception:
            continue

    return results


def get_liquidity_signal(global_data):
    """
    Calcula señal de liquidez global basada en los indicadores.
    Retorna: "EXPANSIVA", "CONTRACTIVA", o "NEUTRAL" con score.
    """
    score = 0
    reasons = []

    for g in global_data:
        if g["ticker"] == "DX-Y.NYB":
            # DXY bajando = liquidez expansiva
            if g["period_chg"] < -2:
                score += 2
                reasons.append("DXY bajando → USD débil, liquidez global")
            elif g["period_chg"] > 3:
                score -= 2
                reasons.append("DXY subiendo → USD fuerte, aprieta emergentes")

        elif g["ticker"] == "^VIX":
            if g["current"] > 25:
                score -= 1
                reasons.append(f"VIX alto ({g['current']:.0f}) → miedo en mercado")
            elif g["current"] < 15:
                score += 1
                reasons.append(f"VIX bajo ({g['current']:.0f}) → complacencia")

        elif g["ticker"] == "^TNX":
            if g["current"] > 4.5:
                score -= 1
                reasons.append(f"US 10Y alto ({g['current']:.2f}%) → crédito caro")
            elif g["current"] < 3.5:
                score += 1
                reasons.append(f"US 10Y bajo ({g['current']:.2f}%) → condiciones laxas")

        elif g["ticker"] == "EEM":
            if g["period_chg"] > 5:
                score += 1
                reasons.append("Emergentes subiendo → flujo favorable")
            elif g["period_chg"] < -5:
                score -= 1
                reasons.append("Emergentes cayendo → risk-off")

        elif g["ticker"] == "HYG":
            if g["period_chg"] < -3:
                score -= 2
                reasons.append("High Yield cayendo → stress crediticio")

        elif g["ticker"] == "BTC-USD":
            if g["period_chg"] > 20:
                score += 1
                reasons.append("BTC subiendo → risk-on / liquidez")
            elif g["period_chg"] < -20:
                score -= 1
                reasons.append("BTC cayendo → risk-off")

    if score >= 2:
        signal = "EXPANSIVA"
    elif score <= -2:
        signal = "CONTRACTIVA"
    else:
        signal = "NEUTRAL"

    return signal, score, reasons


# ============================================================
# ARGENTINA MACRO INDICATORS
# ============================================================

ARGDATA_BASE = "https://api.argentinadatos.com/v1"


def _get_argdata(endpoint):
    """Helper para ArgentinaDatos API."""
    try:
        r = requests.get(f"{ARGDATA_BASE}{endpoint}", timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _get_latest_dollars():
    """Obtiene últimas cotizaciones de todos los tipos de dólar."""
    data = _get_argdata("/cotizaciones/dolares")
    if not data:
        return {}

    # Agrupar por casa y tomar el más reciente
    latest = {}
    for entry in reversed(data):  # reversed porque vienen ordenados por fecha asc
        casa = entry.get("casa", "")
        if casa not in latest:
            latest[casa] = entry
    return latest


def get_argentina_indicators():
    """
    Indicadores macro de Argentina.
    Fuentes: ArgentinaDatos API, Yahoo Finance.
    """
    indicators = []

    # --- DÓLARES (ArgentinaDatos) ---
    dollars = _get_latest_dollars()

    if "oficial" in dollars:
        d = dollars["oficial"]
        indicators.append({
            "name": "Dólar Oficial",
            "value": d.get("venta", 0),
            "unit": "ARS/USD",
            "category": "Cambiario",
            "source": "ArgentinaDatos",
            "interpretation": f"Compra: ${d.get('compra', 0):,.0f} | Venta: ${d.get('venta', 0):,.0f}",
        })

    if "blue" in dollars:
        d = dollars["blue"]
        indicators.append({
            "name": "Dólar Blue",
            "value": d.get("venta", 0),
            "unit": "ARS/USD",
            "category": "Cambiario",
            "source": "ArgentinaDatos",
            "interpretation": f"Compra: ${d.get('compra', 0):,.0f} | Venta: ${d.get('venta', 0):,.0f}",
        })

    # Dólar MEP (desde ArgentinaDatos o calculado)
    if "contadoconliqui" in dollars:
        d = dollars["contadoconliqui"]
        indicators.append({
            "name": "Dólar CCL",
            "value": d.get("venta", 0),
            "unit": "ARS/USD",
            "category": "Cambiario",
            "source": "ArgentinaDatos",
            "interpretation": "Contado con liquidación — referencia para operar CEDEARs",
        })

    # MEP estimado via GGAL ADR
    try:
        ggal_us = yf.download("GGAL", period="5d", interval="1d", progress=False)
        ggal_ar = yf.download("GGAL.BA", period="5d", interval="1d", progress=False)
        if not ggal_us.empty and not ggal_ar.empty:
            us_price = float(ggal_us["Close"].iloc[-1].iloc[0] if isinstance(ggal_us["Close"].iloc[-1], pd.Series) else ggal_us["Close"].iloc[-1])
            ar_price = float(ggal_ar["Close"].iloc[-1].iloc[0] if isinstance(ggal_ar["Close"].iloc[-1], pd.Series) else ggal_ar["Close"].iloc[-1])
            mep_est = ar_price * 10 / us_price
            indicators.append({
                "name": "Dólar MEP (GGAL)",
                "value": round(mep_est, 2),
                "unit": "ARS/USD",
                "category": "Cambiario",
                "source": "Yahoo (calculado)",
                "interpretation": "MEP implícito = GGAL.BA x10 / GGAL ADR",
            })
    except Exception:
        pass

    # --- BRECHA CAMBIARIA ---
    oficial = next((i["value"] for i in indicators if "Oficial" in i["name"]), None)
    mep = next((i["value"] for i in indicators if "MEP" in i["name"]), None)
    blue = next((i["value"] for i in indicators if "Blue" in i["name"]), None)

    if oficial and oficial > 0:
        if mep:
            brecha_mep = (mep / oficial - 1) * 100
            indicators.append({
                "name": "Brecha MEP/Oficial",
                "value": round(brecha_mep, 1),
                "unit": "%",
                "category": "Cambiario",
                "source": "Calculado",
                "interpretation": "<5% convergencia, >20% presión devaluatoria",
            })
        if blue:
            brecha_blue = (blue / oficial - 1) * 100
            indicators.append({
                "name": "Brecha Blue/Oficial",
                "value": round(brecha_blue, 1),
                "unit": "%",
                "category": "Cambiario",
                "source": "Calculado",
                "interpretation": "Proxy de demanda minorista de dólares",
            })

    # --- RIESGO PAÍS (ArgentinaDatos) ---
    rp = _get_argdata("/finanzas/indices/riesgo-pais/ultimo")
    if rp:
        indicators.append({
            "name": "Riesgo País (EMBI)",
            "value": rp.get("valor", 0),
            "unit": "bp",
            "category": "Riesgo",
            "source": "ArgentinaDatos",
            "interpretation": "<400bp investment grade zone, >800bp stress",
        })

    # --- RIESGO PAÍS HISTÓRICO (para tendencia) ---
    rp_hist = _get_argdata("/finanzas/indices/riesgo-pais")
    if rp_hist and len(rp_hist) > 30:
        recent = rp_hist[-30:]  # últimos 30 datos
        rp_30d_ago = recent[0].get("valor", 0)
        rp_now = recent[-1].get("valor", 0)
        if rp_30d_ago > 0:
            rp_chg = ((rp_now / rp_30d_ago) - 1) * 100
            indicators.append({
                "name": "Riesgo País (30d chg)",
                "value": round(rp_chg, 1),
                "unit": "%",
                "category": "Riesgo",
                "source": "ArgentinaDatos",
                "interpretation": f"Hace 30d: {rp_30d_ago} bp → Hoy: {rp_now} bp",
            })

    # --- ARGT ETF (proxy bonos AR en USD) ---
    try:
        argt = yf.download("ARGT", period="6mo", interval="1d", progress=False)
        if not argt.empty:
            argt_close = argt["Close"].squeeze()
            argt_current = float(argt_close.iloc[-1])
            argt_6m = float(argt_close.iloc[0])
            argt_chg = (argt_current / argt_6m - 1) * 100
            indicators.append({
                "name": "ARGT ETF (Bonos AR)",
                "value": round(argt_current, 2),
                "unit": "USD",
                "category": "Riesgo",
                "source": "Yahoo",
                "interpretation": f"ETF bonos AR. 6m: {argt_chg:+.1f}%",
            })
    except Exception:
        pass

    # --- YPF ADR (proxy Merval USD) ---
    try:
        ypf = yf.download("YPF", period="6mo", interval="1d", progress=False)
        if not ypf.empty:
            ypf_close = ypf["Close"].squeeze()
            ypf_current = float(ypf_close.iloc[-1])
            ypf_6m = float(ypf_close.iloc[0])
            ypf_chg = (ypf_current / ypf_6m - 1) * 100
            ypf_high = float(ypf_close.max())
            ypf_dd = (ypf_current / ypf_high - 1) * 100
            indicators.append({
                "name": "YPF ADR (proxy Merval)",
                "value": round(ypf_current, 2),
                "unit": "USD",
                "category": "Equity AR",
                "source": "Yahoo",
                "interpretation": f"6m: {ypf_chg:+.1f}% | DD máx: {ypf_dd:.1f}%",
            })
    except Exception:
        pass

    return indicators


def get_brecha_historica():
    """
    Descarga serie histórica del dólar oficial y blue de ArgentinaDatos
    y calcula la brecha blue/oficial a lo largo del tiempo.
    Retorna DataFrame con columnas: fecha, oficial, blue, brecha_pct
    """
    oficial_data = _get_argdata("/cotizaciones/dolares/oficial")
    blue_data = _get_argdata("/cotizaciones/dolares/blue")

    if not oficial_data or not blue_data:
        return pd.DataFrame()

    # Convertir a DataFrames
    df_of = pd.DataFrame(oficial_data)
    df_bl = pd.DataFrame(blue_data)

    df_of["fecha"] = pd.to_datetime(df_of["fecha"])
    df_bl["fecha"] = pd.to_datetime(df_bl["fecha"])

    # Usar venta como referencia
    df_of = df_of[["fecha", "venta"]].rename(columns={"venta": "oficial"}).dropna()
    df_bl = df_bl[["fecha", "venta"]].rename(columns={"venta": "blue"}).dropna()

    # Merge por fecha
    df = pd.merge(df_of, df_bl, on="fecha", how="inner")
    df = df[df["oficial"] > 0]
    df["brecha_pct"] = (df["blue"] / df["oficial"] - 1) * 100
    df = df.sort_values("fecha").reset_index(drop=True)

    return df


# Eventos económicos relevantes para anotar en el gráfico de brecha
EVENTOS_ECONOMICOS = [
    ("2019-08-11", "PASO 2019\n(Fernández gana)"),
    ("2019-10-27", "Elección\nAlberto F."),
    ("2020-03-20", "Cuarentena\nCOVID-19"),
    ("2020-10-22", "Brecha récord\n(>100%)"),
    ("2021-11-14", "Legislativas\n2021"),
    ("2022-07-02", "Renuncia\nGuzmán"),
    ("2022-07-28", "Asume\nMassa"),
    ("2023-08-13", "PASO 2023\n(Milei gana)"),
    ("2023-10-22", "1ra vuelta\n2023"),
    ("2023-11-19", "Balotaje\nMilei electo"),
    ("2023-12-10", "Asume\nMilei"),
    ("2024-01-15", "Devaluación\na $800"),
    ("2024-07-01", "Brecha baja\n<20%"),
    ("2025-01-15", "Unificación\ncambiaria?"),
]


def get_ar_decision_matrix(ar_indicators, global_data):
    """
    Genera matriz de decisión para Argentina.
    Combina indicadores globales + locales para dar señales.
    """
    signals = []

    # Buscar valores
    brecha = next((i["value"] for i in ar_indicators if "Brecha" in i["name"]), None)
    oficial = next((i["value"] for i in ar_indicators if "Oficial" in i["name"]), None)
    mep = next((i["value"] for i in ar_indicators if "MEP" in i["name"]), None)

    vix = next((g["current"] for g in global_data if g["ticker"] == "^VIX"), None)
    dxy = next((g for g in global_data if g["ticker"] == "DX-Y.NYB"), None)
    eem = next((g for g in global_data if g["ticker"] == "EEM"), None)

    # Señales
    if brecha is not None:
        if brecha < 5:
            signals.append(("Brecha baja", "POSITIVO", f"Brecha {brecha:.1f}% — convergencia cambiaria, buen momento para dolarizar"))
        elif brecha > 30:
            signals.append(("Brecha alta", "NEGATIVO", f"Brecha {brecha:.1f}% — presión devaluatoria, cautela con pesos"))
        else:
            signals.append(("Brecha moderada", "NEUTRAL", f"Brecha {brecha:.1f}% — monitorear"))

    if vix is not None:
        if vix > 30:
            signals.append(("VIX muy alto", "CAUTELA", f"VIX {vix:.0f} — mercado en pánico. Oportunidad de compra si tenés liquidez"))
        elif vix > 20:
            signals.append(("VIX elevado", "ATENCIÓN", f"VIX {vix:.0f} — volatilidad alta, ir de a poco"))

    if dxy is not None:
        if dxy["period_chg"] < -3:
            signals.append(("USD debilitándose", "POSITIVO", "DXY cayendo — favorable para emergentes y Argentina"))
        elif dxy["period_chg"] > 5:
            signals.append(("USD fortaleciéndose", "NEGATIVO", "DXY subiendo — presiona tipo de cambio y bonos AR"))

    if eem is not None:
        if eem["period_chg"] > 5:
            signals.append(("Flujo a emergentes", "POSITIVO", "ETF emergentes subiendo — viento de cola para Argentina"))
        elif eem["period_chg"] < -8:
            signals.append(("Salida de emergentes", "NEGATIVO", "Emergentes cayendo — presión sobre activos AR"))

    return signals


def get_regime_matching():
    """
    Busca en los últimos 10 años cuándo se dio una combinación similar a la actual:
    - S&P500 RSI < 35 (sobrevendido)
    - VIX > 20 (miedo elevado)
    - Oro rally (>15% en 6m)
    - BTC corrección (>-20% en 6m)
    - EEM positivo (>0% en 6m)

    Retorna lista de períodos similares y qué pasó después (forward returns).
    """
    import warnings
    warnings.filterwarnings("ignore")

    try:
        # Descargar 10 años de datos
        tickers = ["^GSPC", "^VIX", "GLD", "BTC-USD", "EEM"]
        data = yf.download(tickers, period="10y", interval="1wk", progress=False, group_by="ticker")
        if data.empty:
            return None

        # Extraer closes
        closes = {}
        for t in tickers:
            try:
                if t in data.columns.get_level_values(0):
                    closes[t] = data[t]["Close"].dropna()
            except Exception:
                pass

        if len(closes) < 4:  # necesitamos al menos S&P, VIX, GLD, BTC
            return None

        # Calcular RSI rolling del S&P500
        sp = closes.get("^GSPC", pd.Series())
        if sp.empty:
            return None

        delta = sp.diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        sp_rsi = 100 - (100 / (1 + rs))

        # VIX
        vix = closes.get("^VIX", pd.Series())

        # Retornos 6m (26 semanas)
        gld = closes.get("GLD", pd.Series())
        btc = closes.get("BTC-USD", pd.Series())
        eem = closes.get("EEM", pd.Series())

        gld_ret_6m = gld.pct_change(26) * 100 if not gld.empty else pd.Series()
        btc_ret_6m = btc.pct_change(26) * 100 if not btc.empty else pd.Series()
        eem_ret_6m = eem.pct_change(26) * 100 if not eem.empty else pd.Series()

        # Retornos forward del S&P (4w, 13w, 26w, 52w)
        sp_fwd_4w = sp.pct_change(-4) * 100  # negativo = forward
        sp_fwd_13w = sp.pct_change(-13) * 100
        sp_fwd_26w = sp.pct_change(-26) * 100
        sp_fwd_52w = sp.pct_change(-52) * 100

        # Buscar semanas que cumplen los criterios (flexibles)
        matches = []
        for date in sp_rsi.index:
            try:
                rsi_val = sp_rsi.get(date)
                vix_val = vix.get(date) if not vix.empty else None
                gld_r = gld_ret_6m.get(date) if not gld_ret_6m.empty else None
                btc_r = btc_ret_6m.get(date) if not btc_ret_6m.empty else None
                eem_r = eem_ret_6m.get(date) if not eem_ret_6m.empty else None

                if any(v is None or (isinstance(v, float) and np.isnan(v)) for v in [rsi_val, vix_val]):
                    continue

                # Criterios (más flexibles para encontrar más matches)
                conditions_met = 0
                if rsi_val < 35:
                    conditions_met += 1
                if vix_val > 20:
                    conditions_met += 1
                if gld_r is not None and not np.isnan(gld_r) and gld_r > 10:
                    conditions_met += 1
                if btc_r is not None and not np.isnan(btc_r) and btc_r < -15:
                    conditions_met += 1
                if eem_r is not None and not np.isnan(eem_r) and eem_r > 0:
                    conditions_met += 1

                if conditions_met >= 4:  # al menos 4 de 5 criterios
                    fwd = {}
                    for label, series in [("1m", sp_fwd_4w), ("3m", sp_fwd_13w),
                                          ("6m", sp_fwd_26w), ("12m", sp_fwd_52w)]:
                        val = series.get(date)
                        if val is not None and not np.isnan(val):
                            fwd[label] = round(float(val), 1)

                    matches.append({
                        "date": date,
                        "sp_rsi": round(float(rsi_val), 1),
                        "vix": round(float(vix_val), 1),
                        "gld_6m": round(float(gld_r), 1) if gld_r is not None and not np.isnan(gld_r) else None,
                        "btc_6m": round(float(btc_r), 1) if btc_r is not None and not np.isnan(btc_r) else None,
                        "eem_6m": round(float(eem_r), 1) if eem_r is not None and not np.isnan(eem_r) else None,
                        "conditions_met": conditions_met,
                        "forward_returns": fwd,
                    })
            except Exception:
                continue

        if not matches:
            return {"matches": [], "summary": "No se encontraron períodos similares en 10 años."}

        # Agrupar matches cercanos (tomar el de mayor score por cada ventana de 8 semanas)
        grouped = []
        last_date = None
        for m in sorted(matches, key=lambda x: x["date"]):
            if last_date is None or (m["date"] - last_date).days > 56:
                grouped.append(m)
                last_date = m["date"]
            elif m["conditions_met"] > grouped[-1]["conditions_met"]:
                grouped[-1] = m
                last_date = m["date"]

        # Calcular estadísticas de forward returns
        fwd_stats = {}
        for period in ["1m", "3m", "6m", "12m"]:
            vals = [m["forward_returns"].get(period) for m in grouped if period in m.get("forward_returns", {})]
            vals = [v for v in vals if v is not None]
            if vals:
                fwd_stats[period] = {
                    "avg": round(np.mean(vals), 1),
                    "median": round(np.median(vals), 1),
                    "min": round(min(vals), 1),
                    "max": round(max(vals), 1),
                    "positive_pct": round(sum(1 for v in vals if v > 0) / len(vals) * 100),
                    "n": len(vals),
                }

        return {
            "matches": grouped,
            "forward_stats": fwd_stats,
            "summary": f"Se encontraron {len(grouped)} períodos similares en los últimos 10 años.",
        }

    except Exception as e:
        return {"matches": [], "summary": f"Error en análisis: {e}"}


# ============================================================
# MACRO THRESHOLDS — Indicadores tipo Bernstein (umbrales históricos)
# ============================================================

# Datos estáticos actualizados periódicamente + live donde sea posible
MACRO_THRESHOLDS = [
    {
        "name": "Energía / GDP",
        "source": "BP/Bernstein/OECD",
        "current_value": 4.5,  # 2025 est, Brent ~$65-70
        "danger_zone": 7.0,
        "crisis_zone": 8.0,
        "unit": "%",
        "history": [
            (1973, 8.0, "Oil Crisis"),
            (1980, 9.0, "Energy Crisis"),
            (1990, 5.5, "Gulf War"),
            (2000, 3.0, "Dot-com"),
            (2008, 8.2, "GFC"),
            (2014, 4.5, "Shale"),
            (2020, 3.2, "COVID"),
            (2022, 8.5, "Rusia"),
            (2025, 4.5, "Hoy"),
        ],
        "interpretation": "Cada vez que energía superó 7-8% del GDP global → shock (1973, 1980, 2008, 2022). "
                          "Hoy ~4.5% — lejos del peligro. Petróleo debería superar US$120 para activar.",
    },
    {
        "name": "Buffett Indicator",
        "source": "GuruFocus/Advisor Perspectives",
        "current_value": 228,  # Feb 2026, 2do más alto de la historia
        "danger_zone": 150,
        "crisis_zone": 200,
        "unit": "%",
        "interpretation": "Market Cap total US / GDP. Media histórica: 85%. "
                          "Dot-com: 140%, GFC: 110%, Dic 2025: 230% (récord). "
                          "Hoy 228% = mercado +168% sobre media → mean reversion implica -40% potencial.",
    },
    {
        "name": "CAPE Shiller",
        "source": "GuruFocus/Multpl",
        "current_value": 38.0,  # Mar 2026, 2do más alto en 155 años
        "danger_zone": 30,
        "crisis_zone": 40,
        "unit": "x",
        "interpretation": "PE ajustado por ciclo (10 años). Media: 17x. "
                          "Dot-com: 44x (récord), Ene 2026: 40.6x. "
                          "Cuando CAPE >30, retorno a 10 años promedia <4% anual.",
    },
    {
        "name": "Yield Curve 10Y-2Y",
        "source": "FRED T10Y2Y",
        "current_value": 0.60,  # Feb 2026
        "danger_zone": 0,
        "crisis_zone": -0.5,
        "unit": "pp",
        "extra_info": "Inversión: Oct 2022 → Dic 2024 (26 meses, una de las más largas). "
                      "Desinversión: Dic 2024. Ventana recesión: Jun 2025 → Dic 2026.",
        "interpretation": "Curva invertida → recesión en 6-24 meses (100% track record desde 1955). "
                          "Se desinvirtió hace 15 meses → ESTAMOS DENTRO de la ventana de recesión.",
    },
    {
        "name": "Sahm Rule",
        "source": "FRED SAHMREALTIME",
        "current_value": 0.27,  # Feb 2026
        "danger_zone": 0.50,
        "crisis_zone": 0.80,
        "unit": "pp",
        "interpretation": "Sube desempleo 3m avg >0.5pp vs mínimo 12m → recesión. "
                          "Triggered en las 11 recesiones post-1950. "
                          "Jul 2024 llegó a 0.53 pero no hubo recesión (soft landing). Hoy 0.27 = OK.",
    },
    {
        "name": "M2 Global",
        "source": "FRED M2SL / MacroMicro",
        "current_value": 4.6,  # YoY growth %
        "danger_zone": -2,  # contracción = peligro
        "crisis_zone": -5,
        "unit": "% YoY",
        "interpretation": "US M2 récord $22.4T (Dic 2025), +4.6% YoY. Mayor suba anual desde 2021. "
                          "M2 en expansión → bullish para activos con ~10 semanas de lag. "
                          "Contracción 2022-23 (1ra desde 1930s) ya se revirtió completamente.",
    },
    {
        "name": "Credit Spreads HY",
        "source": "FRED BAMLH0A0HYM2",
        "current_value": 328,  # bps, Mar 2026
        "danger_zone": 500,
        "crisis_zone": 800,
        "unit": "bp",
        "interpretation": "HY OAS: media 20 años ~490bp. GFC: 2000bp, COVID: 1100bp. "
                          "Hoy 328bp = complacencia. Spreads tight históricamente preceden widening súbito.",
    },
]


def get_macro_thresholds_live():
    """
    Calcula indicadores de umbrales macro.
    Usa datos estáticos actualizados + live de yfinance donde sea posible.
    Retorna lista de dicts con estado actual de cada threshold.
    """
    results = []

    for threshold in MACRO_THRESHOLDS:
        t = threshold.copy()

        val = t.get("current_value")
        danger = t.get("danger_zone", 0)
        crisis = t.get("crisis_zone", 0)

        # Determinar status según la dirección del peligro
        name = t["name"]

        # Indicadores donde MAYOR = peor
        if name in ("Energía / GDP", "Buffett Indicator", "CAPE Shiller",
                     "Sahm Rule", "Credit Spreads HY"):
            if val is not None:
                if val >= crisis:
                    t["status"] = "CRISIS"
                elif val >= danger:
                    t["status"] = "PELIGRO"
                else:
                    t["status"] = "OK"
                t["pct_to_danger"] = round((danger - val) / max(danger, 1) * 100, 0) if val < danger else 0
            else:
                t["status"] = "N/A"

        # Yield Curve: MENOR = peor (inversión)
        elif "Yield Curve" in name:
            if val is not None:
                if val <= crisis:
                    t["status"] = "CRISIS"
                elif val <= danger:
                    t["status"] = "PELIGRO"
                else:
                    # Positiva pero post-inversión = WARNING
                    t["status"] = "WARNING"
                    t["warning_reason"] = "Curva positiva pero en ventana post-inversión (6-24 meses)"
            else:
                t["status"] = "N/A"

        # M2: MENOR = peor (contracción)
        elif "M2" in name:
            if val is not None:
                if val <= crisis:
                    t["status"] = "CRISIS"
                elif val <= danger:
                    t["status"] = "PELIGRO"
                else:
                    t["status"] = "OK"
            else:
                t["status"] = "N/A"

        # Try to get live yield curve data
        if "Yield Curve" in name:
            try:
                tnx = yf.download("^TNX", period="5d", interval="1d", progress=False)
                irx = yf.download("^IRX", period="5d", interval="1d", progress=False)
                if not tnx.empty and not irx.empty:
                    y10 = float(tnx["Close"].squeeze().iloc[-1])
                    y3m = float(irx["Close"].squeeze().iloc[-1])
                    # Estimate 2Y as weighted avg between 3M and 10Y
                    y2_est = y3m * 0.4 + y10 * 0.6  # approx
                    spread = round(y10 - y2_est, 2)
                    t["current_value"] = spread
                    t["extra"] = f"10Y: {y10:.2f}% | 3M: {y3m:.2f}% | Spread est: {spread:+.2f}pp"
                    # Re-evaluate status
                    if spread <= crisis:
                        t["status"] = "CRISIS"
                    elif spread <= danger:
                        t["status"] = "PELIGRO"
                    else:
                        t["status"] = "WARNING"
                        t["warning_reason"] = "Positiva pero en ventana post-inversión"
            except Exception:
                pass

        # Try to get live credit spreads via HYG/LQD
        if "Credit Spreads" in name:
            try:
                hyg = yf.download("HYG", period="6mo", interval="1d", progress=False)
                lqd = yf.download("LQD", period="6mo", interval="1d", progress=False)
                if not hyg.empty and not lqd.empty:
                    hyg_close = hyg["Close"].squeeze()
                    lqd_close = lqd["Close"].squeeze()
                    ratio = hyg_close / lqd_close
                    current_ratio = float(ratio.iloc[-1])
                    ratio_6m = float(ratio.iloc[0])
                    chg = (current_ratio / ratio_6m - 1) * 100
                    t["extra"] = f"HYG/LQD: {current_ratio:.3f} | 6m: {chg:+.1f}%"
            except Exception:
                pass

        results.append(t)

    return results


# Resumen semáforo de todos los umbrales
def get_threshold_summary(thresholds):
    """Genera resumen de semáforo: cuántos en OK/WARNING/PELIGRO/CRISIS."""
    counts = {"OK": 0, "WARNING": 0, "PELIGRO": 0, "CRISIS": 0}
    for t in thresholds:
        s = t.get("status", "N/A")
        if s in counts:
            counts[s] += 1

    red = counts["CRISIS"]
    amber = counts["PELIGRO"] + counts["WARNING"]
    green = counts["OK"]

    if red >= 2:
        signal = "ALERTA ALTA"
        desc = (f"{red} indicadores en crisis, {amber} en warning. "
                "Valuaciones extremas — proteger capital, ser muy selectivo.")
    elif red >= 1 or amber >= 3:
        signal = "CAUTELA"
        desc = (f"{red} crisis, {amber} warning, {green} OK. "
                "Señales mixtas — invertir pero con protección (stops, diversificación).")
    elif amber >= 2:
        signal = "ATENCIÓN"
        desc = (f"{amber} warning, {green} OK. "
                "Condiciones aceptables pero monitorear de cerca.")
    else:
        signal = "VÍA LIBRE"
        desc = f"Todos los indicadores en zona normal. Invertir con el plan."

    return signal, desc, counts


# ============================================================
# SENTIMENT: Crypto Fear & Greed + DataRoma Smart Money
# ============================================================

def get_crypto_fear_greed():
    """
    Crypto Fear & Greed Index de alternative.me.
    0 = Extreme Fear, 100 = Extreme Greed.
    Cava lo usa como contrarian: extreme fear = oportunidad.
    """
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=30&format=json", timeout=10)
        if r.status_code != 200:
            return None
        data = r.json().get("data", [])
        if not data:
            return None

        current = int(data[0]["value"])
        classification = data[0]["value_classification"]

        # Tendencia: promedio últimos 7 vs últimos 30
        values = [int(d["value"]) for d in data]
        avg_7d = sum(values[:7]) / min(len(values), 7)
        avg_30d = sum(values) / len(values)

        # Días consecutivos en extreme fear
        streak = 0
        for d in data:
            if d["value_classification"] == "Extreme Fear":
                streak += 1
            else:
                break

        return {
            "value": current,
            "classification": classification,
            "avg_7d": round(avg_7d, 0),
            "avg_30d": round(avg_30d, 0),
            "extreme_fear_streak": streak,
            "trend": "BAJANDO" if avg_7d < avg_30d else "SUBIENDO",
            "history": values,
            "signal": _crypto_fg_signal(current, streak),
        }
    except Exception:
        return None


def _crypto_fg_signal(value, streak):
    """Señal contrarian basada en Fear & Greed."""
    if value <= 10 and streak >= 7:
        return ("EXTREME FEAR PROLONGADO", "COMPRA CONTRARIAN",
                f"F&G={value}, {streak} días en extreme fear. Históricamente señal de piso.")
    elif value <= 20:
        return ("EXTREME FEAR", "OPORTUNIDAD",
                f"F&G={value}. Mercado en pánico — como dice Cava, 'cuando todos venden, comprá'")
    elif value <= 35:
        return ("FEAR", "ATENCIÓN",
                f"F&G={value}. Miedo pero no pánico. Ir de a poco.")
    elif value <= 55:
        return ("NEUTRAL", "NEUTRAL",
                f"F&G={value}. Sin señal clara.")
    elif value <= 75:
        return ("GREED", "CAUTELA",
                f"F&G={value}. Codicia — no es momento de comprar agresivo.")
    else:
        return ("EXTREME GREED", "VENDER/REDUCIR",
                f"F&G={value}. Euforia — considerar tomar ganancias.")


# DataRoma superinvestors — datos estáticos actualizados por trimestre
# Se actualiza manualmente cada vez que salen los 13F filings (Q4 2025 = último)
DATAROMA_SMART_MONEY = {
    "last_update": "Q4 2025 (dic 2025)",
    "top_buys": [
        {"ticker": "MSFT", "buyers": 16, "sellers": 16, "net": 0, "signal": "ROTACIÓN"},
        {"ticker": "AMZN", "buyers": 11, "sellers": 15, "net": -4, "signal": "MÁS VENDEN"},
        {"ticker": "META", "buyers": 10, "sellers": 18, "net": -8, "signal": "MÁS VENDEN"},
        {"ticker": "V", "buyers": 9, "sellers": 9, "net": 0, "signal": "ROTACIÓN"},
        {"ticker": "TSM", "buyers": 8, "sellers": 9, "net": -1, "signal": "ROTACIÓN"},
        {"ticker": "ASML", "buyers": 4, "sellers": 0, "net": 4, "signal": "COMPRA LIMPIA"},
        {"ticker": "UBER", "buyers": 5, "sellers": 0, "net": 5, "signal": "COMPRA LIMPIA"},
        {"ticker": "MELI", "buyers": 2, "sellers": 0, "net": 2, "signal": "COMPRA LIMPIA"},
        {"ticker": "NVDA", "buyers": 6, "sellers": 6, "net": 0, "signal": "ROTACIÓN"},
        {"ticker": "GOOGL", "buyers": 6, "sellers": 22, "net": -16, "signal": "VENTA MASIVA"},
        {"ticker": "AAPL", "buyers": 0, "sellers": 12, "net": -12, "signal": "SOLO VENTA"},
        {"ticker": "LLY", "buyers": 0, "sellers": 3, "net": -3, "signal": "SOLO VENTA"},
    ],
    "buffett_moves": {
        "buys": ["CVX +6.6%", "CB +9.3%", "DPZ +12%", "NYT (NUEVO)"],
        "sells": ["AMZN -77%", "AAPL -4.3%", "BAC -8.9%"],
        "message": "Vendiendo tech, comprando seguros+energía+value",
    },
    "ackman_moves": {
        "buys": ["META (NUEVO)", "AMZN (+)"],
        "sells": ["BN (reduce)", "UBER (reduce)", "GOOG (reduce)"],
        "message": "Concentra en META y AMZN, sale del resto",
    },
    # Holdings near 52-week lows (señal contrarian)
    "near_52w_low": [
        {"ticker": "V", "pct_above_low": 0.99},
        {"ticker": "FOUR", "pct_above_low": 0.72},
        {"ticker": "KHC", "pct_above_low": 0.65},
        {"ticker": "MU", "pct_above_low": 0.00},
        {"ticker": "DASH", "pct_above_low": 2.48},
        {"ticker": "CPRT", "pct_above_low": 0.99},
        {"ticker": "FISV", "pct_above_low": 2.06},
    ],
}


def get_sentiment_dashboard():
    """
    Combina Crypto Fear & Greed + DataRoma Smart Money en un dashboard de sentimiento.
    """
    crypto_fg = get_crypto_fear_greed()

    return {
        "crypto_fear_greed": crypto_fg,
        "smart_money": DATAROMA_SMART_MONEY,
    }


# ============================================================
# GEOPOLITICAL SCENARIO: Guerra larga vs corta (Iran/Hormuz)
# ============================================================

ENERGY_TICKERS = {"VIST", "YPF", "PAMP", "PAM", "XLE", "CVX"}


def get_geopolitical_scenario():
    """
    Clasifica el escenario geopolítico basado en petróleo, oro, VIX y sector energía.

    GUERRA LARGA: WTI>90 + VIX>25 + XLE outperform >15% YTD
    GUERRA CORTA: WTI<80 + VIX<20 + normalización en curso
    INCIERTO: todo lo demás

    Retorna dict con escenario, confianza %, drivers clave y datos raw.
    """
    import warnings
    warnings.filterwarnings("ignore")

    drivers = {}
    raw = {}

    # --- Fetch datos ---
    try:
        tickers = ["CL=F", "BZ=F", "GLD", "^VIX", "XLE", "^GSPC"]
        data = yf.download(tickers, period="ytd", interval="1d", progress=False, group_by="ticker")
    except Exception:
        return {"scenario": "INCIERTO", "confidence": 0, "drivers": [], "raw": {},
                "error": "No se pudieron descargar datos"}

    def _extract(ticker):
        try:
            if ticker in data.columns.get_level_values(0):
                close = data[ticker]["Close"].dropna().squeeze()
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                return close
        except Exception:
            pass
        return pd.Series(dtype=float)

    wti = _extract("CL=F")
    brent = _extract("BZ=F")
    gld = _extract("GLD")
    vix = _extract("^VIX")
    xle = _extract("XLE")
    sp500 = _extract("^GSPC")

    # --- Valores actuales ---
    wti_now = float(wti.iloc[-1]) if not wti.empty else None
    brent_now = float(brent.iloc[-1]) if not brent.empty else None
    gld_now = float(gld.iloc[-1]) if not gld.empty else None
    vix_now = float(vix.iloc[-1]) if not vix.empty else None

    # YTD returns
    xle_ytd = ((float(xle.iloc[-1]) / float(xle.iloc[0])) - 1) * 100 if len(xle) > 1 else None
    sp_ytd = ((float(sp500.iloc[-1]) / float(sp500.iloc[0])) - 1) * 100 if len(sp500) > 1 else None
    xle_outperform = (xle_ytd - sp_ytd) if xle_ytd is not None and sp_ytd is not None else None
    gld_ytd = ((float(gld.iloc[-1]) / float(gld.iloc[0])) - 1) * 100 if len(gld) > 1 else None

    # Brent-WTI spread (indicador de supply route disruption)
    brent_wti_spread = round(brent_now - wti_now, 2) if brent_now and wti_now else None

    raw = {
        "wti": wti_now, "brent": brent_now, "gld": gld_now, "vix": vix_now,
        "xle_ytd": round(xle_ytd, 1) if xle_ytd else None,
        "sp_ytd": round(sp_ytd, 1) if sp_ytd else None,
        "xle_outperform": round(xle_outperform, 1) if xle_outperform else None,
        "gld_ytd": round(gld_ytd, 1) if gld_ytd else None,
        "brent_wti_spread": brent_wti_spread,
    }

    # --- Clasificación ---
    score_largo = 0  # positivo = guerra larga
    drivers_list = []

    # WTI
    if wti_now is not None:
        drivers["WTI"] = {"value": round(wti_now, 2), "largo": 90, "corto": 80}
        if wti_now > 90:
            score_largo += 2
            drivers_list.append(f"WTI US${wti_now:.0f} > $90 — petróleo en zona de riesgo")
        elif wti_now > 80:
            score_largo += 1
            drivers_list.append(f"WTI US${wti_now:.0f} — elevado pero no en crisis")
        elif wti_now < 70:
            score_largo -= 2
            drivers_list.append(f"WTI US${wti_now:.0f} < $70 — petróleo barato, sin prima de guerra")
        else:
            drivers_list.append(f"WTI US${wti_now:.0f} — zona normal ($70-80)")

    # VIX
    if vix_now is not None:
        drivers["VIX"] = {"value": round(vix_now, 1), "largo": 25, "corto": 20}
        if vix_now > 30:
            score_largo += 2
            drivers_list.append(f"VIX {vix_now:.0f} > 30 — pánico, consistente con escalada")
        elif vix_now > 25:
            score_largo += 1
            drivers_list.append(f"VIX {vix_now:.0f} > 25 — miedo elevado")
        elif vix_now < 18:
            score_largo -= 2
            drivers_list.append(f"VIX {vix_now:.0f} < 18 — complacencia, sin prima de riesgo")
        else:
            score_largo -= 1
            drivers_list.append(f"VIX {vix_now:.0f} — moderado")

    # XLE outperformance
    if xle_outperform is not None:
        drivers["XLE vs S&P"] = {"value": round(xle_outperform, 1), "largo": 15, "corto": 0}
        if xle_outperform > 15:
            score_largo += 2
            drivers_list.append(f"XLE supera S&P en {xle_outperform:+.1f}pp YTD — mercado priceando conflicto")
        elif xle_outperform > 5:
            score_largo += 1
            drivers_list.append(f"XLE supera S&P en {xle_outperform:+.1f}pp YTD — rotación a energía")
        elif xle_outperform < -5:
            score_largo -= 1
            drivers_list.append(f"XLE underperforma S&P en {xle_outperform:+.1f}pp — sin bid por energía")
        else:
            drivers_list.append(f"XLE vs S&P: {xle_outperform:+.1f}pp — neutral")

    # Oro
    if gld_ytd is not None:
        drivers["Oro YTD"] = {"value": round(gld_ytd, 1), "largo": 15, "corto": 5}
        if gld_ytd > 15:
            score_largo += 1
            drivers_list.append(f"Oro {gld_ytd:+.1f}% YTD — flight to safety activo")
        elif gld_ytd > 5:
            drivers_list.append(f"Oro {gld_ytd:+.1f}% YTD — demanda moderada de refugio")
        else:
            score_largo -= 1
            drivers_list.append(f"Oro {gld_ytd:+.1f}% YTD — sin demanda de refugio")

    # Brent-WTI spread (supply route disruption indicator)
    if brent_wti_spread is not None:
        drivers["Brent-WTI Spread"] = {"value": round(brent_wti_spread, 2), "largo": 8, "corto": 3}
        if brent_wti_spread > 8:
            score_largo += 1
            drivers_list.append(f"Spread Brent-WTI US${brent_wti_spread:.1f} > $8 — mercado priceando disruption de rutas")
        elif brent_wti_spread < 3:
            score_largo -= 1
            drivers_list.append(f"Spread Brent-WTI US${brent_wti_spread:.1f} < $3 — sin prima por rutas marítimas")
        else:
            drivers_list.append(f"Spread Brent-WTI US${brent_wti_spread:.1f} — nivel normal")

    # --- Determinar escenario ---
    if score_largo >= 4:
        scenario = "GUERRA LARGA"
        confidence = min(90, 50 + score_largo * 8)
    elif score_largo <= -3:
        scenario = "GUERRA CORTA"
        confidence = min(90, 50 + abs(score_largo) * 8)
    else:
        scenario = "INCIERTO"
        confidence = max(20, 50 - abs(score_largo) * 5)

    return {
        "scenario": scenario,
        "confidence": confidence,
        "score": score_largo,
        "drivers": drivers_list,
        "thresholds": drivers,
        "raw": raw,
    }


def get_energy_exposure(positions):
    """
    Analiza exposición a energía del portfolio.
    Identifica posiciones en VIST, YPF, PAMP, XLE, CVX.
    Calcula correlación con WTI últimos 90d.

    positions: lista de dicts con 'ticker', 'market_value_usd', etc.
    Retorna dict con exposición y correlaciones.
    """
    from indicators import TICKER_MAP, _get_price_history

    total = sum(p.get("market_value_usd", 0) for p in positions)
    if total <= 0:
        return {"energy_positions": [], "total_pct": 0, "ar_pct": 0, "global_pct": 0}

    ar_energy = {"VIST", "YPF", "PAMP", "PAM"}
    global_energy = {"XLE", "CVX"}

    energy_positions = []
    ar_value = 0
    global_value = 0

    # Fetch WTI para correlaciones
    wti_prices = _get_price_history("CL=F", period="3mo")
    wti_returns = wti_prices.pct_change().dropna() if wti_prices is not None and len(wti_prices) > 20 else None

    for p in positions:
        ticker = p["ticker"]
        ticker_upper = ticker.upper()
        yahoo = TICKER_MAP.get(ticker)

        is_energy = (ticker_upper in ENERGY_TICKERS or
                     (yahoo and yahoo.replace(".BA", "") in ENERGY_TICKERS))

        if not is_energy:
            continue

        value = p.get("market_value_usd", 0)
        weight = value / total * 100

        # Clasificar AR vs global
        if ticker_upper in ar_energy or (yahoo and yahoo.replace(".BA", "").upper() in ar_energy):
            ar_value += value
            region = "Argentina"
        else:
            global_value += value
            region = "Global"

        # Correlación con WTI
        corr_wti = None
        if wti_returns is not None and yahoo:
            asset_prices = _get_price_history(yahoo, period="3mo")
            if asset_prices is not None and len(asset_prices) > 20:
                asset_returns = asset_prices.pct_change().dropna()
                aligned = pd.concat([asset_returns, wti_returns], axis=1, join="inner").dropna()
                if len(aligned) > 15:
                    aligned.columns = ["asset", "wti"]
                    corr_wti = round(float(aligned["asset"].corr(aligned["wti"])), 2)

        energy_positions.append({
            "ticker": ticker,
            "name": p.get("name", ticker),
            "value_usd": round(value, 0),
            "weight_pct": round(weight, 1),
            "region": region,
            "corr_wti_90d": corr_wti,
        })

    energy_total = ar_value + global_value

    return {
        "energy_positions": sorted(energy_positions, key=lambda x: x["value_usd"], reverse=True),
        "total_pct": round(energy_total / total * 100, 1) if total > 0 else 0,
        "total_usd": round(energy_total, 0),
        "ar_pct": round(ar_value / total * 100, 1) if total > 0 else 0,
        "ar_usd": round(ar_value, 0),
        "global_pct": round(global_value / total * 100, 1) if total > 0 else 0,
        "global_usd": round(global_value, 0),
    }


if __name__ == "__main__":
    print("=== GLOBAL ===")
    global_data = get_global_indicators()
    for g in global_data:
        rsi_str = f"RSI:{g['rsi']}" if g['rsi'] else ""
        print(f"  {g['name']:30s} {g['current']:>12.2f}  día:{g['daily_chg']:+.2f}%  6m:{g['period_chg']:+.1f}%  rango:{g['range_pct']:.0f}%  {rsi_str}")

    signal, score, reasons = get_liquidity_signal(global_data)
    print(f"\n  Liquidez global: {signal} (score: {score})")
    for r in reasons:
        print(f"    → {r}")

    print("\n=== ARGENTINA ===")
    ar = get_argentina_indicators()
    for i in ar:
        print(f"  {i['name']:30s} {i['value']:>12} {i['unit']:5s}  ({i['source']})")

    print("\n=== SEÑALES ===")
    signals = get_ar_decision_matrix(ar, global_data)
    for name, tipo, desc in signals:
        print(f"  [{tipo:8s}] {name}: {desc}")
