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
