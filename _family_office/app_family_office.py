"""
Family Office Dashboard — MVP con datos reales de CSV
Ejecutar: cd _family_office && streamlit run app_family_office.py
Puerto asignado: 8506 (ver PUERTOS.md en raíz del proyecto)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from csv_parser import load_all_portfolios, get_dolar_mep_live
from config_fo import (
    TARGET_ALLOCATION, REBALANCE_THRESHOLD_PCT, MAX_DRAWDOWN_ALERT,
    MAX_CONCENTRATION_TOP5, CASH_DEPLOY_ALERT, APORTE_MENSUAL_ARS,
    CEDEAR_WATCHLIST,
)
from rebalancer import calculate_rebalance
from indicators import calculate_portfolio_indicators, simulate_what_if, TICKER_MAP
from macro import (
    get_global_indicators, get_liquidity_signal, get_argentina_indicators,
    get_ar_decision_matrix, get_brecha_historica, EVENTOS_ECONOMICOS,
    get_regime_matching, get_macro_thresholds_live, get_threshold_summary,
    get_sentiment_dashboard,
), get_sentiment_dashboard, DATAROMA_SMART_MONEY
from risk_engine import (
    calculate_concentration_metrics, calculate_component_var,
    calculate_correlation_matrix, run_all_stress_tests, run_stress_test,
    check_drawdown_alerts, calculate_risk_attribution, calculate_risk_score,
    STRESS_SCENARIOS,
)

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Family Office",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- CSS ---
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .alert-box {
        background: #2d1b1b; border: 1px solid #ff4444; border-radius: 8px;
        padding: 12px 16px; margin: 4px 0; color: #ff8888;
    }
    .ok-box {
        background: #1b2d1b; border: 1px solid #44ff44; border-radius: 8px;
        padding: 12px 16px; margin: 4px 0; color: #88ff88;
    }
    .info-box {
        background: #1b1b2d; border: 1px solid #4488ff; border-radius: 8px;
        padding: 12px 16px; margin: 4px 0; color: #88aaff;
    }
    .buy-box {
        background: #1b2d2d; border: 1px solid #44dddd; border-radius: 8px;
        padding: 14px 18px; margin: 6px 0; color: #88ffff;
    }
</style>
""", unsafe_allow_html=True)


def format_usd(value):
    if abs(value) >= 1_000_000:
        return f"US$ {value:,.0f}"
    return f"US$ {value:,.2f}"


def format_ars(value):
    if abs(value) >= 1_000_000:
        return f"$ {value/1_000_000:,.1f}M"
    return f"$ {value:,.0f}"


# ============================================================
# CARGAR DATOS REALES
# ============================================================
positions, cash_list, load_errors = load_all_portfolios()

if not positions:
    st.error("No hay datos de portfolio. Poné los CSV de tenencia en `_family_office/data/`")
    if load_errors:
        for e in load_errors:
            st.warning(e)
    st.stop()

df = pd.DataFrame(positions)
df_cash = pd.DataFrame(cash_list) if cash_list else pd.DataFrame(columns=["currency", "amount", "source", "owner"])

total_usd = df["market_value_usd"].sum()
total_ars = df["market_value_ars"].sum()

cash_usd = 0
if len(df_cash) > 0:
    for _, c in df_cash.iterrows():
        if c["currency"] == "USD":
            cash_usd += c["amount"]
        elif c["currency"] == "ARS":
            cash_usd += c["amount"] / get_dolar_mep_live()

portfolio_total_usd = total_usd + cash_usd
cash_pct = (cash_usd / portfolio_total_usd * 100) if portfolio_total_usd > 0 else 0
df["weight"] = df["market_value_usd"] / portfolio_total_usd * 100
alloc = df.groupby("asset_class")["market_value_usd"].sum()
alloc_pct = (alloc / portfolio_total_usd * 100).to_dict()
df_sorted = df.sort_values("market_value_usd", ascending=False)
top5_weight = df_sorted.head(5)["weight"].sum()
owners = df["owner"].unique().tolist()

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### Filtros")
    selected_owners = st.multiselect("Miembros", owners, default=owners)
    st.markdown("---")
    mep_live = get_dolar_mep_live()
    st.markdown(f"**Dólar MEP**: ${mep_live:,.0f} (live)")
    st.markdown("---")
    if load_errors:
        st.markdown("### Avisos")
        for e in load_errors:
            st.warning(e)

if selected_owners:
    df_filtered = df[df["owner"].isin(selected_owners)]
else:
    df_filtered = df

# ============================================================
# TABS
# ============================================================
st.markdown("## Family Office Dashboard")
st.caption(f"Datos de: {', '.join(df['source'].unique())} | {len(positions)} posiciones | {len(owners)} miembros")

tab_overview, tab_macro, tab_sentiment, tab_risk, tab_indicators, tab_rebalance, tab_positions, tab_conclusiones = st.tabs([
    "📊 Overview", "🌎 Macro & Liquidez", "🎰 Sentimiento & Smart Money", "🛡 Risk Engine", "📈 Indicadores & What-If", "⚖️ Rebalanceo", "📋 Posiciones", "🎯 Conclusiones"
])

# ============================================================
# TAB 1: OVERVIEW
# ============================================================
with tab_overview:
    # KPIs
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Portfolio Total", format_usd(portfolio_total_usd), format_ars(total_ars))
    with col2:
        st.metric("Posiciones", f"{len(df_filtered)}", f"{df_filtered['asset_class'].nunique()} clases")
    with col3:
        st.metric("Cash", f"{cash_pct:.1f}%", format_usd(cash_usd))
    with col4:
        st.metric("Top 5 Concentr.", f"{top5_weight:.1f}%",
                  "Alto" if top5_weight > MAX_CONCENTRATION_TOP5 else "OK",
                  delta_color="inverse" if top5_weight > MAX_CONCENTRATION_TOP5 else "normal")
    with col5:
        if len(df_sorted) > 0:
            biggest = df_sorted.iloc[0]
            st.metric("Mayor Posición", biggest["ticker"], f"{biggest['weight']:.1f}%")

    # Alertas + Allocation
    st.markdown("---")
    col_alerts, col_alloc = st.columns([1, 2])

    with col_alerts:
        st.markdown("### Alertas")
        alerts = []
        if cash_pct > CASH_DEPLOY_ALERT:
            alerts.append(f"**Cash alto**: {cash_pct:.1f}% — considerar deployar")
        if top5_weight > MAX_CONCENTRATION_TOP5:
            top5_names = ", ".join(df_sorted.head(5)["ticker"].tolist())
            alerts.append(f"**Concentración**: top 5 ({top5_names}) = {top5_weight:.1f}%")
        for cls, target in TARGET_ALLOCATION.items():
            actual = alloc_pct.get(cls, 0)
            diff = actual - target
            if abs(diff) > REBALANCE_THRESHOLD_PCT:
                direction = "sobreexpuesto" if diff > 0 else "subexpuesto"
                alerts.append(f"**{cls}**: {direction} ({actual:.1f}% vs target {target}%)")

        if alerts:
            for a in alerts:
                st.markdown(f'<div class="alert-box">{a}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="ok-box">Sin alertas activas</div>', unsafe_allow_html=True)

    with col_alloc:
        st.markdown("### Asset Allocation: Target vs Actual")
        alloc_data = []
        all_classes = set(list(TARGET_ALLOCATION.keys()) + list(alloc_pct.keys()))
        for cls in sorted(all_classes):
            alloc_data.append({
                "Clase": cls,
                "Target %": TARGET_ALLOCATION.get(cls, 0),
                "Actual %": round(alloc_pct.get(cls, 0), 1),
            })
        df_alloc = pd.DataFrame(alloc_data).sort_values("Actual %", ascending=False)

        fig_alloc = go.Figure()
        fig_alloc.add_trace(go.Bar(
            name="Target", x=df_alloc["Clase"], y=df_alloc["Target %"],
            marker_color="#555588", text=df_alloc["Target %"].apply(lambda x: f"{x}%" if x > 0 else ""),
            textposition="outside",
        ))
        fig_alloc.add_trace(go.Bar(
            name="Actual", x=df_alloc["Clase"], y=df_alloc["Actual %"],
            marker_color="#44aaff", text=df_alloc["Actual %"].apply(lambda x: f"{x}%"),
            textposition="outside",
        ))
        fig_alloc.update_layout(
            barmode="group", height=350, margin=dict(t=20, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ccc"),
        )
        max_y = max(df_alloc["Target %"].max(), df_alloc["Actual %"].max(), 10) + 10
        fig_alloc.update_yaxes(range=[0, max_y])
        st.plotly_chart(fig_alloc, use_container_width=True)

    # Donuts
    st.markdown("---")
    col_donut, col_member = st.columns([1, 1])

    with col_donut:
        st.markdown("### Composición por Clase")
        donut_data = pd.DataFrame([
            {"Clase": cls, "US$": val} for cls, val in alloc.items()
        ]).sort_values("US$", ascending=False)

        colors = ["#44aaff", "#ff8844", "#44cc88", "#888888", "#ffcc44", "#cc44ff", "#ff4488", "#88ddff"]
        fig_donut = go.Figure(data=[go.Pie(
            labels=donut_data["Clase"], values=donut_data["US$"],
            hole=0.55, marker=dict(colors=colors[:len(donut_data)]),
            textinfo="label+percent", textfont_size=11,
        )])
        fig_donut.update_layout(
            height=380, margin=dict(t=10, b=10, l=10, r=10),
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ccc"),
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_member:
        st.markdown("### Por Miembro")
        if len(owners) > 1:
            member_data = df.groupby("owner")["market_value_usd"].sum().reset_index()
            member_data.columns = ["Miembro", "US$"]
            fig_member = go.Figure(data=[go.Pie(
                labels=member_data["Miembro"], values=member_data["US$"],
                hole=0.55, marker=dict(colors=["#44aaff", "#ff8844", "#44cc88"]),
                textinfo="label+percent+value", textfont_size=11,
                texttemplate="%{label}<br>%{percent}<br>US$ %{value:,.0f}",
            )])
            fig_member.update_layout(
                height=380, margin=dict(t=10, b=10, l=10, r=10),
                showlegend=False,
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ccc"),
            )
            st.plotly_chart(fig_member, use_container_width=True)
        else:
            top_positions = df_sorted.head(8)
            fig_top = go.Figure(data=[go.Bar(
                x=top_positions["ticker"], y=top_positions["market_value_usd"],
                marker_color="#44aaff",
                text=top_positions["market_value_usd"].apply(lambda x: f"US$ {x:,.0f}"),
                textposition="outside",
            )])
            fig_top.update_layout(
                height=380, margin=dict(t=10, b=40),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ccc"), yaxis_title="US$",
            )
            st.plotly_chart(fig_top, use_container_width=True)

    # Exposición cambiaria + Detalle clase
    st.markdown("---")
    col_fx, col_by_class = st.columns([1, 2])

    with col_fx:
        st.markdown("### Exposición Cambiaria")
        cedear_usd = df[df["asset_class"] == "CEDEARs"]["market_value_usd"].sum()
        bonos_usd = df[df["asset_class"] == "Bonos Soberanos AR"]["market_value_usd"].sum()
        acciones_ar = df[df["asset_class"] == "Acciones AR"]["market_value_usd"].sum()
        fci_ars = df[(df["asset_class"] == "FCI / Money Market") & (df["currency_original"] == "ARS")]["market_value_usd"].sum()
        fci_usd = df[(df["asset_class"] == "FCI / Money Market") & (df["currency_original"] == "USD")]["market_value_usd"].sum()
        crypto_usd = df[df["asset_class"] == "Crypto"]["market_value_usd"].sum()

        dolarizado = cedear_usd + bonos_usd + fci_usd + crypto_usd + cash_usd
        pesificado = acciones_ar + fci_ars

        total_exposure = dolarizado + pesificado
        if total_exposure > 0:
            fx_data = pd.DataFrame([
                {"Exposición": "Dolarizado", "US$": f"${dolarizado:,.0f}", "%": f"{dolarizado/total_exposure*100:.1f}%"},
                {"Exposición": "Pesificado", "US$": f"${pesificado:,.0f}", "%": f"{pesificado/total_exposure*100:.1f}%"},
            ])
            st.dataframe(fx_data, use_container_width=True, hide_index=True)
            st.caption("CEDEARs, bonos USD y crypto se consideran dolarizados")

    with col_by_class:
        st.markdown("### Detalle por Clase de Activo")
        class_summary = df.groupby("asset_class").agg(
            Posiciones=("ticker", "count"),
            Total_USD=("market_value_usd", "sum"),
            Total_ARS=("market_value_ars", "sum"),
        ).sort_values("Total_USD", ascending=False).reset_index()
        class_summary["Peso %"] = (class_summary["Total_USD"] / portfolio_total_usd * 100).round(1)
        class_summary.columns = ["Clase", "Pos.", "Total USD", "Total ARS", "Peso %"]
        st.dataframe(
            class_summary, use_container_width=True, hide_index=True,
            column_config={
                "Total USD": st.column_config.NumberColumn("Total USD", format="US$ %,.0f"),
                "Total ARS": st.column_config.NumberColumn("Total ARS", format="$ %,.0f"),
                "Peso %": st.column_config.NumberColumn("Peso %", format="%.1f%%"),
            },
        )


# ============================================================
# TAB 2: MACRO & LIQUIDEZ GLOBAL
# ============================================================
with tab_macro:
    st.markdown("### Contexto Macro & Liquidez Global")
    st.caption("Datos en tiempo real de Yahoo Finance + BCRA. Se actualizan al recargar.")

    # Cachear datos macro
    @st.cache_data(ttl=1800, show_spinner="Descargando datos macro...")
    def get_macro_data():
        global_data = get_global_indicators()
        ar_data = get_argentina_indicators()
        return global_data, ar_data

    global_data, ar_indicators = get_macro_data()

    # --- SEÑAL DE LIQUIDEZ GLOBAL ---
    signal, score, reasons = get_liquidity_signal(global_data)

    signal_colors = {
        "EXPANSIVA": ("#1b2d1b", "#44ff44", "#88ff88"),
        "CONTRACTIVA": ("#2d1b1b", "#ff4444", "#ff8888"),
        "NEUTRAL": ("#1b1b2d", "#4488ff", "#88aaff"),
    }
    bg, border, text_color = signal_colors.get(signal, signal_colors["NEUTRAL"])

    st.markdown(
        f'<div style="background:{bg}; border:2px solid {border}; border-radius:12px; '
        f'padding:20px; margin:10px 0; text-align:center;">'
        f'<span style="color:{text_color}; font-size:1.5rem; font-weight:700;">'
        f'Liquidez Global: {signal} (score: {score:+d})</span></div>',
        unsafe_allow_html=True,
    )

    if reasons:
        cols_reasons = st.columns(len(reasons))
        for i, reason in enumerate(reasons):
            with cols_reasons[i]:
                st.caption(f"→ {reason}")

    # --- ARGENTINA ---
    st.markdown("---")
    st.markdown("#### Argentina")

    # Agrupar por categoría
    ar_by_cat = {}
    for ind in ar_indicators:
        cat = ind.get("category", "Otros")
        ar_by_cat.setdefault(cat, []).append(ind)

    for cat, inds in ar_by_cat.items():
        st.markdown(f"**{cat}**")
        ar_cols = st.columns(min(len(inds), 5))
        for i, ind in enumerate(inds):
            with ar_cols[i % len(ar_cols)]:
                val = ind["value"]
                if isinstance(val, float):
                    if ind["unit"] == "%":
                        val_str = f"{val:+.1f}%" if "chg" in ind["name"].lower() else f"{val:.1f}%"
                    elif ind["unit"] == "ARS/USD":
                        val_str = f"$ {val:,.0f}"
                    elif ind["unit"] == "USD":
                        val_str = f"US$ {val:.2f}"
                    elif ind["unit"] == "bp":
                        val_str = f"{val:,.0f} bp"
                    else:
                        val_str = f"{val:,.2f}"
                else:
                    val_str = f"{val:,}" if isinstance(val, int) else str(val)
                st.metric(ind["name"], val_str)
                st.caption(ind["interpretation"])

    # --- SEÑALES DE DECISIÓN ---
    st.markdown("---")
    st.markdown("#### Señales para Toma de Decisiones")

    decision_signals = get_ar_decision_matrix(ar_indicators, global_data)
    if decision_signals:
        for name, tipo, desc in decision_signals:
            if tipo == "POSITIVO":
                st.markdown(f'<div class="ok-box"><strong>{name}</strong>: {desc}</div>', unsafe_allow_html=True)
            elif tipo in ("NEGATIVO", "CAUTELA"):
                st.markdown(f'<div class="alert-box"><strong>{name}</strong>: {desc}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="info-box"><strong>{name}</strong>: {desc}</div>', unsafe_allow_html=True)

    # --- BRECHA HISTÓRICA ---
    st.markdown("---")
    st.markdown("#### Brecha Cambiaria Histórica (Blue vs Oficial)")
    st.caption("Fuente: ArgentinaDatos. Eventos económicos anotados.")

    @st.cache_data(ttl=3600, show_spinner="Descargando serie de brecha...")
    def get_brecha_data():
        return get_brecha_historica()

    df_brecha = get_brecha_data()

    if not df_brecha.empty:
        fig_brecha = go.Figure()

        # Brecha como área
        fig_brecha.add_trace(go.Scatter(
            x=df_brecha["fecha"], y=df_brecha["brecha_pct"],
            mode="lines", name="Brecha Blue/Oficial %",
            line=dict(color="#ff8844", width=1.5),
            fill="tozeroy", fillcolor="rgba(255,136,68,0.15)",
        ))

        # Líneas de referencia
        fig_brecha.add_hline(y=0, line_dash="dot", line_color="#666", line_width=0.5)
        fig_brecha.add_hline(y=30, line_dash="dash", line_color="#ff4444", line_width=0.5,
                             annotation_text="30% (presión)", annotation_position="right")
        fig_brecha.add_hline(y=100, line_dash="dash", line_color="#ff0000", line_width=0.5,
                             annotation_text="100% (crisis)", annotation_position="right")

        # Eventos económicos
        for fecha_str, label in EVENTOS_ECONOMICOS:
            fecha = pd.Timestamp(fecha_str)
            if fecha >= df_brecha["fecha"].min() and fecha <= df_brecha["fecha"].max():
                fig_brecha.add_vline(x=fecha, line_dash="dot", line_color="rgba(150,150,150,0.4)", line_width=0.5)
                fig_brecha.add_annotation(
                    x=fecha, y=1.05, yref="paper",
                    text=label, showarrow=False,
                    font=dict(size=8, color="#aaa"),
                    textangle=-45, xanchor="left",
                )

        fig_brecha.update_layout(
            height=450, margin=dict(t=60, b=40, l=40, r=40),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ccc"),
            xaxis_title="", yaxis_title="Brecha %",
            showlegend=False,
            xaxis=dict(rangeslider=dict(visible=True), type="date"),
        )
        st.plotly_chart(fig_brecha, use_container_width=True)

        # Estadísticas de brecha
        col_b1, col_b2, col_b3, col_b4 = st.columns(4)
        with col_b1:
            st.metric("Brecha Actual", f"{df_brecha['brecha_pct'].iloc[-1]:.1f}%")
        with col_b2:
            brecha_30d = df_brecha.tail(30)
            st.metric("Promedio 30d", f"{brecha_30d['brecha_pct'].mean():.1f}%")
        with col_b3:
            st.metric("Máxima histórica", f"{df_brecha['brecha_pct'].max():.1f}%",
                      df_brecha.loc[df_brecha['brecha_pct'].idxmax(), 'fecha'].strftime('%Y-%m-%d'))
        with col_b4:
            st.metric("Mínima reciente (1Y)", f"{df_brecha.tail(252)['brecha_pct'].min():.1f}%")
    else:
        st.warning("No se pudo cargar la serie histórica de brecha")

    # --- TABLA GLOBAL DETALLADA ---
    st.markdown("---")
    st.markdown("#### Indicadores Globales — Detalle")

    if global_data:
        df_global = pd.DataFrame(global_data)

        # RSI signal
        def rsi_signal(rsi):
            if rsi is None:
                return "—"
            if rsi > 70:
                return "Sobrecompra"
            elif rsi < 30:
                return "Sobreventa"
            return "Neutral"

        df_global["Señal"] = df_global["rsi"].apply(rsi_signal)

        df_show = df_global[[
            "name", "category", "current", "daily_chg", "period_chg",
            "range_pct", "rsi", "Señal"
        ]].copy()
        df_show.columns = [
            "Indicador", "Categoría", "Valor", "Día %", "6m %",
            "Rango 6m %", "RSI", "Señal"
        ]

        st.dataframe(
            df_show,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Valor": st.column_config.NumberColumn("Valor", format="%.2f"),
                "Día %": st.column_config.NumberColumn("Día %", format="%+.2f%%"),
                "6m %": st.column_config.NumberColumn("6m %", format="%+.1f%%"),
                "Rango 6m %": st.column_config.ProgressColumn("Rango 6m", min_value=0, max_value=100, format="%.0f%%"),
                "RSI": st.column_config.NumberColumn("RSI", format="%.1f"),
            },
        )

        # Interpretaciones
        with st.expander("¿Cómo leer estos indicadores?"):
            for g in global_data:
                st.markdown(f"- **{g['name']}**: {g['interpretation']}")
            st.markdown("""
---
**Columnas:**
- **Rango 6m**: Posición relativa entre mínimo (0%) y máximo (100%) de los últimos 6 meses. Si está en 10%, está cerca del piso.
- **RSI**: <30 = sobreventa (oportunidad de compra), >70 = sobrecompra (cautela)
- **6m %**: Cambio acumulado en 6 meses. Contexto de tendencia.
""")

    # --- QUÉ IMPLICA PARA TU PORTFOLIO ---
    st.markdown("---")
    st.markdown("#### Implicancia para tu Portfolio")

    imp_cols = st.columns(3)
    with imp_cols[0]:
        st.markdown("**CEDEARs / Equity**")
        sp500 = next((g for g in global_data if g["ticker"] == "^GSPC"), None)
        vix = next((g for g in global_data if g["ticker"] == "^VIX"), None)
        if sp500 and vix:
            if sp500["rsi"] and sp500["rsi"] < 30:
                st.success(f"S&P500 RSI {sp500['rsi']:.0f} — sobreventa, buen momento para acumular CEDEARs")
            elif vix["current"] > 25:
                st.warning(f"VIX {vix['current']:.0f} alto — comprar de a poco, no todo junto")
            else:
                st.info("Condiciones normales para equity")

    with imp_cols[1]:
        st.markdown("**Bonos Soberanos AR**")
        eem = next((g for g in global_data if g["ticker"] == "EEM"), None)
        brecha = next((i["value"] for i in ar_indicators if "Brecha" in i["name"]), None)
        if eem and brecha is not None:
            if eem["period_chg"] > 0 and brecha < 10:
                st.success("Flujo a emergentes + brecha baja — favorable para bonos AR")
            elif eem["period_chg"] < -5:
                st.warning("Salida de emergentes — cautela con bonos AR")
            else:
                st.info("Contexto neutro para bonos")

    with imp_cols[2]:
        st.markdown("**Crypto**")
        btc = next((g for g in global_data if g["ticker"] == "BTC-USD"), None)
        if btc:
            if btc["rsi"] and btc["rsi"] < 30:
                st.success(f"BTC RSI {btc['rsi']:.0f} — sobreventa, oportunidad")
            elif btc["period_chg"] < -30:
                st.warning(f"BTC -{'%.0f' % abs(btc['period_chg'])}% en 6m — en corrección fuerte")
            else:
                st.info(f"BTC en rango ({btc['range_pct']:.0f}% del rango 6m)")

    # --- CROSS-ANALYSIS: cruce de variables ---
    st.markdown("---")
    st.markdown("#### Cross-Analysis: Cruce de Variables")
    st.caption("Combinaciones de indicadores que generan señales compuestas")

    cross_signals = []

    # Extraer valores para cruce
    _vix = next((g for g in global_data if g["ticker"] == "^VIX"), None)
    _dxy = next((g for g in global_data if g["ticker"] == "DX-Y.NYB"), None)
    _sp500 = next((g for g in global_data if g["ticker"] == "^GSPC"), None)
    _btc = next((g for g in global_data if g["ticker"] == "BTC-USD"), None)
    _gld = next((g for g in global_data if g["ticker"] == "GLD"), None)
    _eem = next((g for g in global_data if g["ticker"] == "EEM"), None)
    _tlt = next((g for g in global_data if g["ticker"] == "TLT"), None)
    _brecha = next((i["value"] for i in ar_indicators if "Brecha MEP" in i["name"]), None)
    _rp = next((i["value"] for i in ar_indicators if "EMBI" in i["name"]), None)

    # 1. VIX alto + S&P sobrevendido = oportunidad contrarian
    if _vix and _sp500 and _vix["current"] > 25 and _sp500.get("rsi") and _sp500["rsi"] < 35:
        cross_signals.append(("buy-box", "OPORTUNIDAD CONTRARIAN",
            f"VIX {_vix['current']:.0f} + S&P RSI {_sp500['rsi']:.0f} — históricamente los mejores puntos de entrada para CEDEARs"))

    # 2. DXY bajando + EEM subiendo = viento de cola emergentes
    if _dxy and _eem and _dxy["period_chg"] < -2 and _eem["period_chg"] > 3:
        cross_signals.append(("ok-box", "VIENTO DE COLA EMERGENTES",
            f"DXY {_dxy['period_chg']:+.1f}% + EEM {_eem['period_chg']:+.1f}% — condiciones óptimas para bonos AR y acciones AR"))

    # 3. DXY subiendo + EEM cayendo = presión sobre AR
    if _dxy and _eem and _dxy["period_chg"] > 3 and _eem["period_chg"] < -3:
        cross_signals.append(("alert-box", "PRESIÓN SOBRE ARGENTINA",
            f"DXY {_dxy['period_chg']:+.1f}% + EEM {_eem['period_chg']:+.1f}% — USD fuerte + salida de emergentes, cautela con activos AR"))

    # 4. Oro subiendo + BTC subiendo = liquidez global expansiva
    if _gld and _btc and _gld["period_chg"] > 10 and _btc["period_chg"] > 10:
        cross_signals.append(("ok-box", "LIQUIDEZ GLOBAL FUERTE",
            f"Oro {_gld['period_chg']:+.1f}% + BTC {_btc['period_chg']:+.1f}% — ambos activos de reserva subiendo, ciclo expansivo"))

    # 5. Oro subiendo + BTC cayendo = flight to safety (risk-off con inflación)
    if _gld and _btc and _gld["period_chg"] > 10 and _btc["period_chg"] < -10:
        cross_signals.append(("alert-box", "FLIGHT TO SAFETY",
            f"Oro {_gld['period_chg']:+.1f}% + BTC {_btc['period_chg']:+.1f}% — rotación a refugio, reducir riesgo"))

    # 6. TLT subiendo + VIX subiendo = recesión fears
    if _tlt and _vix and _tlt["period_chg"] > 5 and _vix["current"] > 22:
        cross_signals.append(("info-box", "SEÑAL RECESIÓN",
            f"TLT (bonos largos) {_tlt['period_chg']:+.1f}% + VIX {_vix['current']:.0f} — mercado priceando recesión, bonos US como refugio"))

    # 7. Brecha baja + riesgo país bajo = ventana de dolarización
    if _brecha is not None and _rp is not None and _brecha < 8 and _rp < 600:
        cross_signals.append(("ok-box", "VENTANA DE DOLARIZACIÓN",
            f"Brecha {_brecha:.1f}% + RP {_rp:.0f}bp — momento óptimo para comprar dólar MEP y bonos hard-dollar"))

    # 8. Brecha subiendo + RP subiendo = alerta Argentina
    if _brecha is not None and _rp is not None and _brecha > 20 and _rp > 700:
        cross_signals.append(("alert-box", "ALERTA ARGENTINA",
            f"Brecha {_brecha:.1f}% + RP {_rp:.0f}bp — stress cambiario + crediticio, refugiarse en USD"))

    # 9. S&P sobrecomprado + VIX muy bajo = complacencia (señal de cautela)
    if _sp500 and _vix and _sp500.get("rsi") and _sp500["rsi"] > 70 and _vix["current"] < 14:
        cross_signals.append(("info-box", "COMPLACENCIA",
            f"S&P RSI {_sp500['rsi']:.0f} + VIX {_vix['current']:.0f} — mercado eufórico, históricamente precede correcciones"))

    # 10. Cruce portfolio: tu allocation vs señales
    bonos_pct = alloc_pct.get("Bonos Soberanos AR", 0)
    crypto_pct = alloc_pct.get("Crypto", 0)
    cedear_pct = alloc_pct.get("CEDEARs", 0)

    if _btc and _btc["period_chg"] < -20 and crypto_pct > 15:
        cross_signals.append(("alert-box", "SOBREEXPOSICIÓN CRYPTO EN CORRECCIÓN",
            f"BTC {_btc['period_chg']:+.1f}% + tu crypto es {crypto_pct:.1f}% del portfolio — considerar reducir"))

    if _rp and _rp > 800 and bonos_pct > 40:
        cross_signals.append(("alert-box", "SOBREEXPOSICIÓN BONOS AR EN STRESS",
            f"RP {_rp:.0f}bp + tus bonos AR son {bonos_pct:.1f}% del portfolio — riesgo concentrado"))

    if cross_signals:
        for box_class, title, desc in cross_signals:
            st.markdown(f'<div class="{box_class}"><strong>{title}</strong>: {desc}</div>', unsafe_allow_html=True)
    else:
        st.info("Sin señales cruzadas activas — mercado en equilibrio relativo.")


# ============================================================
# TAB: SENTIMIENTO & SMART MONEY (Cava style)
# ============================================================
with tab_sentiment:
    st.markdown("### Sentimiento & Smart Money")
    st.caption("Crypto Fear & Greed (contrarian) + DataRoma superinvestors (smart money) — las fuentes que usa José Luis Cava")

    @st.cache_data(ttl=1800, show_spinner="Cargando sentimiento...")
    def _get_sentiment():
        return get_sentiment_dashboard()

    sentiment = _get_sentiment()

    # --- CRYPTO FEAR & GREED ---
    st.markdown("#### Crypto Fear & Greed Index")
    cfg = sentiment.get("crypto_fear_greed")
    if cfg:
        fg_color = "#ff4444" if cfg["value"] <= 25 else "#ffaa00" if cfg["value"] <= 50 else "#44ff44" if cfg["value"] <= 75 else "#ff4444"
        signal_name, signal_type, signal_desc = cfg["signal"]

        col_fg1, col_fg2 = st.columns([1, 2])
        with col_fg1:
            st.markdown(
                f'<div style="background:#1a1a2e;border:3px solid {fg_color};border-radius:16px;padding:30px;text-align:center;">'
                f'<span style="color:{fg_color};font-size:4rem;font-weight:700;">{cfg["value"]}</span><br>'
                f'<span style="color:{fg_color};font-size:1.2rem;">{cfg["classification"].upper()}</span><br>'
                f'<span style="color:#888;font-size:0.9rem;">Racha: {cfg["extreme_fear_streak"]} días en extreme fear</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with col_fg2:
            # Signal box
            sig_box = "buy-box" if signal_type in ("COMPRA CONTRARIAN", "OPORTUNIDAD") else "alert-box" if signal_type in ("VENDER/REDUCIR", "CAUTELA") else "info-box"
            st.markdown(f'<div class="{sig_box}"><strong>{signal_name}</strong>: {signal_desc}</div>', unsafe_allow_html=True)

            # Métricas
            m1, m2, m3 = st.columns(3)
            m1.metric("Promedio 7d", f"{cfg['avg_7d']:.0f}")
            m2.metric("Promedio 30d", f"{cfg['avg_30d']:.0f}")
            m3.metric("Tendencia", cfg["trend"])

            # Mini chart
            if cfg.get("history"):
                fig_fg = go.Figure(data=go.Scatter(
                    y=list(reversed(cfg["history"])), mode="lines+markers",
                    line=dict(color=fg_color, width=2),
                    marker=dict(size=4),
                ))
                fig_fg.add_hline(y=25, line_dash="dash", line_color="#ff4444", line_width=0.5)
                fig_fg.add_hline(y=75, line_dash="dash", line_color="#44ff44", line_width=0.5)
                fig_fg.update_layout(
                    height=180, margin=dict(t=5, b=5, l=30, r=10),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#888"), showlegend=False,
                    yaxis=dict(range=[0, 100]),
                    xaxis=dict(title="Últimos 30 días"),
                )
                st.plotly_chart(fig_fg, use_container_width=True)
    else:
        st.warning("No se pudo cargar el Crypto Fear & Greed Index")

    st.divider()

    # --- DATAROMA SMART MONEY ---
    st.markdown("#### DataRoma — ¿Qué hacen los superinvestors? (Q4 2025)")
    st.caption("82 fondos trackeados. Datos de 13F filings (último: dic 2025). Fuente: dataroma.com")

    sm = sentiment.get("smart_money", DATAROMA_SMART_MONEY)

    # Tabla de buys/sells
    col_sm1, col_sm2 = st.columns([3, 2])

    with col_sm1:
        st.markdown("##### Actividad por ticker — nuestro watchlist")
        sm_rows = []
        for entry in sm["top_buys"]:
            signal_color = {"COMPRA LIMPIA": "#44ff44", "ROTACIÓN": "#ffcc44", "MÁS VENDEN": "#ff8844", "VENTA MASIVA": "#ff4444", "SOLO VENTA": "#ff4444"}.get(entry["signal"], "#888")
            sm_rows.append({
                "Ticker": entry["ticker"],
                "Compran": entry["buyers"],
                "Venden": entry["sellers"],
                "Neto": entry["net"],
                "Señal": entry["signal"],
            })
        df_sm = pd.DataFrame(sm_rows)
        st.dataframe(df_sm, use_container_width=True, hide_index=True,
                     column_config={
                         "Neto": st.column_config.NumberColumn(format="%+d"),
                     })

    with col_sm2:
        st.markdown("##### Lo que manda Buffett")
        for action in sm["buffett_moves"]["buys"]:
            st.markdown(f'<span style="color:#44ff44;">COMPRA</span> {action}', unsafe_allow_html=True)
        for action in sm["buffett_moves"]["sells"]:
            st.markdown(f'<span style="color:#ff4444;">VENDE</span> {action}', unsafe_allow_html=True)
        st.caption(f"Lectura: {sm['buffett_moves']['message']}")

        st.markdown("##### Ackman")
        for action in sm["ackman_moves"]["buys"]:
            st.markdown(f'<span style="color:#44ff44;">COMPRA</span> {action}', unsafe_allow_html=True)
        for action in sm["ackman_moves"]["sells"]:
            st.markdown(f'<span style="color:#ff4444;">VENDE</span> {action}', unsafe_allow_html=True)
        st.caption(f"Lectura: {sm['ackman_moves']['message']}")

    st.divider()

    # --- NEAR 52-WEEK LOWS ---
    st.markdown("##### Holdings de superinvestors cerca de mínimos 52 semanas")
    st.caption("Señal contrarian: si los grandes tienen y está en mínimos, puede ser oportunidad")
    if sm.get("near_52w_low"):
        low_cols = st.columns(len(sm["near_52w_low"]))
        for i, entry in enumerate(sm["near_52w_low"]):
            with low_cols[i]:
                st.metric(entry["ticker"], f"+{entry['pct_above_low']:.1f}%", "del mínimo 52s")

    st.divider()

    # --- CONCLUSIÓN SENTIMIENTO ---
    st.markdown("#### Conclusión Sentimiento")

    conclusions = []

    # Crypto sentiment
    if cfg and cfg["value"] <= 15 and cfg["extreme_fear_streak"] >= 14:
        conclusions.append(("buy-box", "CRYPTO: EXTREME FEAR SOSTENIDO",
            f"F&G={cfg['value']}, {cfg['extreme_fear_streak']} días seguidos. Históricamente es piso. "
            "PERO: el smart money (DataRoma) NO toca crypto. Si entrás, que sea con plan de salida."))
    elif cfg and cfg["value"] <= 25:
        conclusions.append(("info-box", "CRYPTO: MIEDO",
            f"F&G={cfg['value']}. Puede ser oportunidad contrarian pero la tendencia sigue negativa."))

    # Smart money signals
    compras_limpias = [e["ticker"] for e in sm["top_buys"] if e["signal"] == "COMPRA LIMPIA"]
    ventas_masivas = [e["ticker"] for e in sm["top_buys"] if e["signal"] in ("VENTA MASIVA", "SOLO VENTA")]

    if compras_limpias:
        conclusions.append(("ok-box", "SMART MONEY COMPRA (sin venta)",
            f"Solo entran, nadie sale: {', '.join(compras_limpias)}. Estos son los de mayor convicción."))

    if ventas_masivas:
        conclusions.append(("alert-box", "SMART MONEY SALE",
            f"Más venden que compran: {', '.join(ventas_masivas)}. OJO con sobreponderar estos."))

    # Buffett meta-signal
    conclusions.append(("info-box", "BUFFETT SIGNAL",
        "Vendió 77% de Amazon y sigue reduciendo Apple. Está acumulando cash y comprando value/seguros. "
        "Esto históricamente anticipa corrección o recesión. Tener liquidez es clave."))

    for box_class, title, desc in conclusions:
        st.markdown(f'<div class="{box_class}"><strong>{title}</strong>: {desc}</div>', unsafe_allow_html=True)


# ============================================================
# TAB 3: RISK ENGINE
# ============================================================
with tab_risk:
    st.subheader("Risk Engine")

    # --- Risk Score ---
    @st.cache_data(ttl=3600)
    def _cached_risk_data(_positions_hash):
        pos_list = df_filtered.to_dict("records")
        port_ind = calculate_portfolio_indicators(pos_list)
        concentration = calculate_concentration_metrics(pos_list)
        dd_alerts = check_drawdown_alerts(pos_list)
        risk_attr = calculate_risk_attribution(pos_list)
        return port_ind, concentration, dd_alerts, risk_attr

    pos_hash = hash(tuple(sorted([(p["ticker"], p["market_value_usd"]) for _, p in df_filtered.iterrows()])))

    with st.spinner("Calculando riesgo..."):
        try:
            port_ind_risk, concentration, dd_alerts, risk_attr = _cached_risk_data(pos_hash)
        except Exception as e:
            st.error(f"Error calculando riesgo: {e}")
            port_ind_risk = {}
            concentration = {}
            dd_alerts = []
            risk_attr = {}

    # --- KPIs de concentración ---
    if concentration:
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("HHI", f"{concentration.get('hhi', 0):,.0f}",
                   help="< 1500 diversificado, > 2500 concentrado")
        c2.metric("Top 1", f"{concentration.get('top1_pct', 0):.1f}%",
                   help=f"{concentration.get('top1_ticker', '')}")
        c3.metric("Top 5", f"{concentration.get('top5_pct', 0):.1f}%")
        c4.metric("Posiciones equiv.", f"{concentration.get('equivalent_positions', 0):.0f}",
                   help="# efectivo de posiciones (1/HHI)")
        c5.metric("Max clase", f"{concentration.get('max_class_pct', 0):.1f}%",
                   help=concentration.get('max_class_name', ''))

    # --- Risk Score Consolidado (cruza macro + portfolio) ---
    try:
        _g_data_risk = get_global_indicators()
        _, _liq_score_risk, _ = get_liquidity_signal(_g_data_risk)
    except Exception:
        _liq_score_risk = 0

    risk_score_data = calculate_risk_score(
        df_filtered.to_dict("records"), port_ind_risk, macro_score=_liq_score_risk
    )
    rs = risk_score_data["score"]
    rs_color = {"green": "#44ff44", "yellow": "#ffcc44", "orange": "#ff8844", "red": "#ff4444"}.get(risk_score_data["color"], "#888")
    st.markdown(
        f'<div style="background:#1a1a2e;border:2px solid {rs_color};border-radius:12px;padding:20px;margin:10px 0;text-align:center;">'
        f'<span style="color:{rs_color};font-size:2.5rem;font-weight:700;">{rs}/100</span><br>'
        f'<span style="color:{rs_color};font-size:1.2rem;">{risk_score_data["rating"]}</span></div>',
        unsafe_allow_html=True,
    )

    # Detalle de factores
    factor_cols = st.columns(len(risk_score_data["factors"]))
    for i, f in enumerate(risk_score_data["factors"]):
        with factor_cols[i]:
            pct_of_max = f["score"] / f["max"] * 100
            bar_color = "#44ff44" if pct_of_max >= 70 else "#ffcc44" if pct_of_max >= 40 else "#ff4444"
            st.markdown(
                f'<div style="text-align:center;padding:4px;">'
                f'<strong>{f["factor"]}</strong><br>'
                f'<span style="color:{bar_color};font-size:1.3rem;">{f["score"]}/{f["max"]}</span><br>'
                f'<span style="color:#888;font-size:0.75rem;">{f["detail"]}</span></div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # --- Stress Scenarios ---
    st.subheader("Stress Scenarios")
    st.caption("¿Qué pasa con tu portfolio en cada escenario?")

    pos_list = df_filtered.to_dict("records")
    stress_results = run_all_stress_tests(pos_list)

    if stress_results:
        cols = st.columns(3)
        for i, sr in enumerate(stress_results):
            if "error" in sr:
                continue
            with cols[i % 3]:
                color = "#ff4444" if sr["pnl_pct"] < -10 else "#ffaa00" if sr["pnl_pct"] < 0 else "#44ff44"
                st.markdown(f"""
                <div style="background:#1a1a2e;border:1px solid {color};border-radius:10px;padding:14px;margin:6px 0;">
                    <strong>{sr['scenario_name']}</strong><br>
                    <span style="font-size:12px;color:#888">{sr['scenario_desc']}</span><br>
                    <span style="font-size:28px;font-weight:700;color:{color}">{sr['pnl_pct']:+.1f}%</span><br>
                    <span style="color:{color}">US$ {sr['pnl_usd']:+,.0f}</span>
                    <span style="color:#666"> → US$ {sr['stressed_total_usd']:,.0f}</span>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # --- Component VaR ---
    st.subheader("Component VaR — Contribución al riesgo por posición")
    st.caption("¿Cuánto del VaR total aporta cada posición? Identifica las fuentes de riesgo.")

    with st.spinner("Calculando Component VaR..."):
        try:
            cvar = calculate_component_var(pos_list)
            if cvar["portfolio_var_pct"] != 0:
                cv1, cv2, cv3 = st.columns(3)
                cv1.metric("VaR 95% diario", f"{cvar['portfolio_var_pct']:.2f}%",
                           help="Pérdida máxima diaria con 95% de confianza")
                cv2.metric("VaR en USD", f"US$ {abs(cvar['portfolio_var_usd']):,.0f}")
                cv3.metric("Vol anual portfolio", f"{cvar.get('portfolio_vol_annual', 0):.1f}%")

                if cvar["components"]:
                    cvar_rows = []
                    for comp in cvar["components"]:
                        cvar_rows.append({
                            "Ticker": comp["ticker"],
                            "Peso %": comp["weight_pct"],
                            "Component VaR %": comp["component_var_pct"],
                            "VaR USD": comp["component_var_usd"],
                            "% del VaR total": comp["pct_of_total_var"],
                        })
                    df_cvar = pd.DataFrame(cvar_rows)
                    st.dataframe(df_cvar, use_container_width=True, hide_index=True,
                                 column_config={
                                     "Peso %": st.column_config.NumberColumn(format="%.1f%%"),
                                     "Component VaR %": st.column_config.NumberColumn(format="%.2f%%"),
                                     "VaR USD": st.column_config.NumberColumn(format="US$ %,.0f"),
                                     "% del VaR total": st.column_config.NumberColumn(format="%.1f%%"),
                                 })
            else:
                st.info("Datos insuficientes para calcular Component VaR (se necesitan al menos 2 posiciones con data).")
        except Exception as e:
            st.warning(f"Error calculando Component VaR: {e}")

    st.divider()

    # --- Risk Attribution ---
    st.subheader("Risk Attribution por Asset Class")
    st.caption("¿De dónde viene el riesgo? Peso vs contribución al riesgo.")
    if risk_attr and risk_attr.get("by_class"):
        ra_data = []
        for cls, data in risk_attr["by_class"].items():
            ra_data.append({
                "Clase": cls,
                "Peso %": data["weight_pct"],
                "Vol anual %": data["avg_vol_annual"],
                "Risk % del total": data["risk_pct_of_total"],
                "Risk/Peso ratio": round(data["risk_pct_of_total"] / data["weight_pct"], 2) if data["weight_pct"] > 0 else 0,
            })
        df_ra = pd.DataFrame(ra_data).sort_values("Risk % del total", ascending=False)
        st.dataframe(df_ra, use_container_width=True, hide_index=True)

        # Chart comparativo peso vs riesgo
        fig_risk = go.Figure()
        fig_risk.add_trace(go.Bar(name="Peso %", x=df_ra["Clase"], y=df_ra["Peso %"], marker_color="#4488ff"))
        fig_risk.add_trace(go.Bar(name="Risk %", x=df_ra["Clase"], y=df_ra["Risk % del total"], marker_color="#ff4444"))
        fig_risk.update_layout(barmode="group", height=350, margin=dict(t=30, b=30),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig_risk, use_container_width=True)

    st.divider()

    # --- Drawdown Alerts ---
    st.subheader("Drawdown Alerts")
    if dd_alerts:
        for alert in dd_alerts:
            sev_color = "#ff4444" if alert["severity"] == "CRITICAL" else "#ffaa00"
            st.markdown(f"""
            <div style="background:#2d1b1b;border-left:4px solid {sev_color};border-radius:6px;padding:10px 14px;margin:4px 0;">
                <strong style="color:{sev_color}">{alert['severity']}</strong> —
                <strong>{alert['ticker']}</strong>: {alert['drawdown_pct']:.1f}% desde máximo 6m
                (${alert['peak_price']:.2f} → ${alert['current_price']:.2f})
                | Peso: {alert['weight_pct']:.1f}%
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="ok-box">Sin alertas de drawdown. Todas las posiciones dentro de límites.</div>', unsafe_allow_html=True)

    st.divider()

    # --- Correlation Matrix (visual) ---
    st.subheader("Correlation Matrix")
    st.caption("Diversificación real entre posiciones. Azul = descorrelacionado (bueno), Rojo = correlacionado (riesgo)")

    with st.spinner("Calculando correlaciones..."):
        try:
            corr_data = calculate_correlation_matrix(pos_list)
            corr_matrix = corr_data.get("matrix")
            if corr_matrix is not None and not corr_matrix.empty:
                c1, c2, c3 = st.columns(3)
                c1.metric("Correlación promedio", f"{corr_data.get('avg_correlation', 0):.2f}")
                c2.metric("Score diversificación", f"{corr_data.get('diversification_score', 0):.0f}/100")
                max_p = corr_data.get("max_pair", {})
                c3.metric("Par más correlacionado",
                          f"{max_p.get('tickers', ('',''))[0]}/{max_p.get('tickers', ('',''))[1]}",
                          f"ρ={max_p.get('correlation', 0):.2f}")

                # Heatmap
                fig_corr = go.Figure(data=go.Heatmap(
                    z=corr_matrix.values,
                    x=corr_matrix.columns,
                    y=corr_matrix.index,
                    colorscale="RdBu_r",
                    zmid=0,
                    zmin=-1, zmax=1,
                    text=corr_matrix.round(2).values,
                    texttemplate="%{text}",
                    textfont={"size": 10},
                ))
                fig_corr.update_layout(height=500, margin=dict(t=30, b=30))
                st.plotly_chart(fig_corr, use_container_width=True)
            else:
                st.info("No hay suficientes posiciones con datos de precio para calcular correlaciones.")
        except Exception as e:
            st.warning(f"Error calculando correlaciones: {e}")


# ============================================================
# TAB 4: INDICADORES & WHAT-IF
# ============================================================
with tab_indicators:
    st.markdown("### Indicadores del Portfolio")
    st.caption("Datos de mercado via Yahoo Finance (6 meses). Benchmark: S&P 500 (SPY)")

    # Calcular indicadores (cacheado por Streamlit)
    @st.cache_data(ttl=3600, show_spinner="Descargando datos de mercado...")
    def get_indicators(pos_json):
        """Cachea indicadores por 1 hora."""
        import json
        pos_list = json.loads(pos_json)
        return calculate_portfolio_indicators(pos_list)

    # Preparar posiciones para el cálculo
    indicator_positions = []
    for _, row in df.iterrows():
        indicator_positions.append({
            "ticker": row["ticker"],
            "market_value_usd": row["market_value_usd"],
            "weight": row["weight"],
            "name": row["name"],
        })

    import json
    indicators = get_indicators(json.dumps(indicator_positions, default=str))

    # --- KPIs del portfolio ---
    st.markdown("#### Métricas Agregadas")
    kcol1, kcol2, kcol3, kcol4, kcol5, kcol6 = st.columns(6)

    with kcol1:
        beta = indicators["portfolio_beta"]
        beta_label = "Defensivo" if beta and beta < 1 else "Agresivo" if beta and beta > 1.5 else "Moderado"
        st.metric("β Beta", f"{beta:.2f}" if beta else "N/A", beta_label)

    with kcol2:
        vol = indicators["portfolio_volatility"]
        st.metric("σ Volatilidad", f"{vol}%" if vol else "N/A",
                  "Alta" if vol and vol > 30 else "Normal" if vol else None,
                  delta_color="inverse" if vol and vol > 30 else "normal")

    with kcol3:
        sharpe = indicators["portfolio_sharpe"]
        sharpe_label = "Bueno" if sharpe and sharpe > 1 else "Mejorable" if sharpe and sharpe > 0 else "Negativo" if sharpe else None
        st.metric("Sharpe Ratio", f"{sharpe:.2f}" if sharpe else "N/A", sharpe_label)

    with kcol4:
        sortino = indicators["portfolio_sortino"]
        st.metric("Sortino Ratio", f"{sortino:.2f}" if sortino else "N/A",
                  "Bueno" if sortino and sortino > 1 else "Mejorable" if sortino else None)

    with kcol5:
        var95 = indicators["var_95"]
        st.metric("VaR 95% (diario)", f"{var95}%" if var95 else "N/A",
                  f"US$ {portfolio_total_usd * abs(var95)/100:,.0f}" if var95 else None,
                  delta_color="inverse")

    with kcol6:
        corr = indicators["avg_correlation"]
        st.metric("ρ Correlación Prom.", f"{corr:.2f}" if corr else "N/A",
                  "Diversificado" if corr and corr < 0.4 else "Concentrado" if corr and corr > 0.6 else None)

    # Leyenda
    with st.expander("¿Qué significa cada indicador?"):
        st.markdown("""
| Indicador | Qué mide | Bueno | Malo |
|-----------|----------|-------|------|
| **β Beta** | Sensibilidad al S&P500. β=1 se mueve igual, β>1 amplifica | <1.0 (defensivo) | >2.0 (muy agresivo) |
| **σ Volatilidad** | Cuánto varía el portfolio (anualizado) | <20% | >40% |
| **Sharpe** | Retorno por unidad de riesgo | >1.0 | <0 |
| **Sortino** | Como Sharpe pero solo penaliza caídas | >1.0 | <0 |
| **VaR 95%** | Pérdida máxima diaria con 95% confianza | >-2% | <-4% |
| **ρ Correlación** | Qué tan juntas se mueven las posiciones | <0.3 (diversificado) | >0.7 (todo junto) |
| **RSI** | Sobrecompra (>70) / Sobreventa (<30) | 30-70 | <30 o >70 |
""")

    # --- Indicadores por posición ---
    st.markdown("---")
    st.markdown("#### Por Posición")

    pos_ind = indicators["position_indicators"]
    pos_rows = []
    for pi in pos_ind:
        if not pi["has_data"]:
            continue

        # RSI señal
        rsi = pi["rsi"]
        if rsi is not None:
            if rsi > 70:
                rsi_signal = "🔴 Sobrecompra"
            elif rsi < 30:
                rsi_signal = "🟢 Sobreventa"
            else:
                rsi_signal = "⚪ Neutral"
        else:
            rsi_signal = "—"

        pos_rows.append({
            "Ticker": pi["ticker"],
            "Peso %": pi.get("weight", 0),
            "β Beta": pi["beta"],
            "RSI (14d)": rsi,
            "Señal RSI": rsi_signal,
            "Volatilidad %": pi["volatility"],
            "Drawdown 6m %": pi["drawdown_6m"],
        })

    if pos_rows:
        df_ind = pd.DataFrame(pos_rows).sort_values("Peso %", ascending=False)
        st.dataframe(
            df_ind,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Peso %": st.column_config.NumberColumn("Peso %", format="%.1f%%"),
                "β Beta": st.column_config.NumberColumn("β Beta", format="%.2f"),
                "RSI (14d)": st.column_config.NumberColumn("RSI", format="%.1f"),
                "Volatilidad %": st.column_config.NumberColumn("Vol %", format="%.1f%%"),
                "Drawdown 6m %": st.column_config.NumberColumn("DD 6m %", format="%.1f%%"),
            },
        )

    # Posiciones sin data (bonos, FCI)
    no_data = [pi["ticker"] for pi in pos_ind if not pi["has_data"]]
    if no_data:
        st.caption(f"Sin datos de mercado: {', '.join(no_data)} (bonos/FCI no cotizan en Yahoo Finance)")

    # --- WHAT-IF SIMULATOR ---
    st.markdown("---")
    st.markdown("#### What-If: Simular cambios")
    st.caption("Probá qué pasa con los indicadores si agregás o sacás una posición")

    col_sim1, col_sim2 = st.columns(2)

    with col_sim1:
        st.markdown("**Agregar posición**")
        # Tickers disponibles para simular
        available_tickers = sorted([k for k in TICKER_MAP.keys() if TICKER_MAP[k] is not None])
        add_ticker = st.selectbox("Ticker a agregar", ["(ninguno)"] + available_tickers)
        add_amount = st.number_input("Monto USD a agregar", min_value=0, value=0, step=100)

    with col_sim2:
        st.markdown("**Remover posición**")
        current_tickers = sorted(df["ticker"].unique().tolist())
        remove_ticker = st.selectbox("Ticker a remover", ["(ninguno)"] + current_tickers)

    if (add_ticker != "(ninguno)" and add_amount > 0) or remove_ticker != "(ninguno)":
        sim_add = add_ticker if add_ticker != "(ninguno)" else None
        sim_remove = remove_ticker if remove_ticker != "(ninguno)" else None

        with st.spinner("Calculando simulación..."):
            sim_result = simulate_what_if(
                indicator_positions,
                add_ticker=sim_add,
                add_amount_usd=add_amount if sim_add else 0,
                remove_ticker=sim_remove,
            )

        st.markdown("##### Comparación: Actual vs Simulado")

        comp_cols = st.columns(6)
        comparisons = [
            ("β Beta", indicators["portfolio_beta"], sim_result["portfolio_beta"], "%.2f"),
            ("σ Vol %", indicators["portfolio_volatility"], sim_result["portfolio_volatility"], "%.1f"),
            ("Sharpe", indicators["portfolio_sharpe"], sim_result["portfolio_sharpe"], "%.2f"),
            ("Sortino", indicators["portfolio_sortino"], sim_result["portfolio_sortino"], "%.2f"),
            ("VaR 95%", indicators["var_95"], sim_result["var_95"], "%.2f"),
            ("ρ Correl.", indicators["avg_correlation"], sim_result["avg_correlation"], "%.2f"),
        ]

        for i, (label, actual, simulated, fmt) in enumerate(comparisons):
            with comp_cols[i]:
                if actual is not None and simulated is not None:
                    diff = simulated - actual
                    actual_str = fmt % actual
                    sim_str = fmt % simulated
                    # Para VaR y Vol, menor es mejor (invertir delta color)
                    invert = label in ("σ Vol %", "VaR 95%")
                    st.metric(
                        label,
                        sim_str,
                        f"{diff:+.2f} vs actual ({actual_str})",
                        delta_color="inverse" if invert else "normal",
                    )
                else:
                    st.metric(label, "N/A", "Sin datos")


# ============================================================
# TAB 3: REBALANCEO MENSUAL
# ============================================================
with tab_rebalance:
    st.markdown("### Rebalanceo por Contribución Mensual")
    st.caption("No vendemos nada — solo dirigimos las compras nuevas hacia lo subponderado")

    # Inputs ajustables
    col_input1, col_input2, col_input3 = st.columns(3)
    with col_input1:
        aporte_ars = st.number_input(
            "Aporte mensual (ARS)",
            min_value=0, value=APORTE_MENSUAL_ARS, step=100_000,
            format="%d",
        )
    with col_input2:
        dolar_input = st.number_input(
            "Dólar MEP",
            min_value=100.0, value=float(mep_live), step=10.0,
            format="%.0f",
        )
    with col_input3:
        aporte_usd = aporte_ars / dolar_input
        st.metric("Aporte en USD", f"US$ {aporte_usd:,.0f}")

    # Calcular rebalanceo
    result = calculate_rebalance(aporte_ars=aporte_ars, dolar_mep=dolar_input)

    st.markdown("---")

    # Gráfico waterfall: qué comprar
    col_chart, col_detail = st.columns([3, 2])

    with col_chart:
        st.markdown("#### Distribución del aporte")

        rec_data = []
        for cls in sorted(result["recommendation"].keys(),
                          key=lambda x: result["recommendation"][x]["alloc_ars"], reverse=True):
            rec = result["recommendation"][cls]
            if rec["alloc_ars"] > 0:
                rec_data.append({
                    "Clase": cls,
                    "ARS": rec["alloc_ars"],
                    "USD": rec["alloc_usd"],
                    "% aporte": rec["alloc_pct"],
                })

        if rec_data:
            df_rec = pd.DataFrame(rec_data)
            fig_rec = go.Figure(data=[go.Bar(
                x=df_rec["Clase"],
                y=df_rec["ARS"],
                marker_color=["#44aaff", "#ff8844", "#44cc88", "#ffcc44", "#cc44ff"][:len(df_rec)],
                text=df_rec.apply(lambda r: f"${r['ARS']:,.0f}<br>({r['% aporte']:.0f}%)", axis=1),
                textposition="outside",
                textfont_size=12,
            )])
            fig_rec.update_layout(
                height=400, margin=dict(t=20, b=40),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ccc"),
                yaxis_title="ARS $",
            )
            st.plotly_chart(fig_rec, use_container_width=True)

    with col_detail:
        st.markdown("#### Situación por clase")

        detail_rows = []
        for cls in sorted(result["target"].keys(),
                          key=lambda x: result["recommendation"].get(x, {}).get("alloc_ars", 0), reverse=True):
            gap = result["gaps"][cls]
            rec = result["recommendation"][cls]
            detail_rows.append({
                "Clase": cls,
                "Actual": f"{gap['current_pct']:.1f}%",
                "Target": f"{gap['target_pct']}%",
                "Gap": f"{gap['gap_pct']:+.1f}%",
                "Comprar ARS": f"$ {rec['alloc_ars']:,.0f}" if rec['alloc_ars'] > 0 else "—",
                "Post-aporte": f"{rec['post_aporte_pct']:.1f}%",
            })
        df_detail = pd.DataFrame(detail_rows)
        st.dataframe(df_detail, use_container_width=True, hide_index=True, height=250)

    # Sugerencias concretas
    st.markdown("---")
    st.markdown("#### Qué comprar este mes")

    suggestions = {
        "CEDEARs": "**Tier 1 (sobrevendidos)**: TSM, META, V, LLY, AAPL — comprar YA. **Tier 2**: ASML (monopolio EUV), GOOGL (PE 28). NVDA mantener, no agregar",
        "Crypto": "**BTC directo** (cold wallet), **IBIT** (ETF regulado). MSTR solo si querés apalancamiento",
        "Acciones AR": "**TGNO4** (gas, dividendo 13%), **YPF** (proxy Vaca Muerta), **GGAL** (proxy Merval). Post-crash -26% = oportunidad",
        "Bonos Soberanos AR": "**GD35/AE38** (carry ~10% USD), **TX28** (BONCER, cobertura CER)",
        "FCI / Money Market": "**COCOUSDPA** solo — mínima liquidez para oportunidades. Rotar exceso a CEDEARs",
    }

    cols = st.columns(2)
    col_idx = 0
    for cls in sorted(result["recommendation"].keys(),
                      key=lambda x: result["recommendation"][x]["alloc_ars"], reverse=True):
        rec = result["recommendation"][cls]
        if rec["alloc_ars"] < 1000:
            continue

        with cols[col_idx % 2]:
            suggestion = suggestions.get(cls, "")
            st.markdown(
                f'<div class="buy-box">'
                f'<strong>{cls}</strong>: $ {rec["alloc_ars"]:,.0f} ARS (US$ {rec["alloc_usd"]:,.0f})<br>'
                f'{suggestion}'
                f'</div>',
                unsafe_allow_html=True,
            )
        col_idx += 1

    # Proyección a 12 meses
    st.markdown("---")
    st.markdown("#### Proyección: cómo evoluciona la allocation en 12 meses")
    st.caption("Asumiendo aporte constante y precios estáticos (worst case)")

    projection_rows = []
    by_class_usd = {cls: alloc.get(cls, 0) for cls in TARGET_ALLOCATION}
    current_total = portfolio_total_usd

    for month in range(0, 13):
        row = {"Mes": month}
        for cls in TARGET_ALLOCATION:
            pct = (by_class_usd.get(cls, 0) / current_total * 100) if current_total > 0 else 0
            row[cls] = round(pct, 1)
        projection_rows.append(row)

        # Proyectar aporte del mes hacia el target (sin releer CSVs)
        if month < 12:
            new_total = current_total + aporte_usd
            total_needed = 0
            needs = {}
            for cls, target_pct in TARGET_ALLOCATION.items():
                target_usd = new_total * target_pct / 100
                current_usd = by_class_usd.get(cls, 0)
                needed = max(target_usd - current_usd, 0)
                needs[cls] = needed
                total_needed += needed

            for cls in TARGET_ALLOCATION:
                if total_needed > 0:
                    share = needs[cls] / total_needed
                    by_class_usd[cls] = by_class_usd.get(cls, 0) + aporte_usd * share
                else:
                    # Todo sobreponderado — distribuir a la clase más subponderada
                    least_cls = min(TARGET_ALLOCATION, key=lambda c: by_class_usd.get(c, 0) / new_total * 100 - TARGET_ALLOCATION[c])
                    if cls == least_cls:
                        by_class_usd[cls] = by_class_usd.get(cls, 0) + aporte_usd
            current_total = new_total

    df_proj = pd.DataFrame(projection_rows)

    fig_proj = go.Figure()
    colors_proj = ["#44aaff", "#ff8844", "#44cc88", "#ffcc44", "#cc44ff"]
    for i, cls in enumerate(TARGET_ALLOCATION.keys()):
        fig_proj.add_trace(go.Scatter(
            x=df_proj["Mes"], y=df_proj[cls],
            mode="lines+markers", name=cls,
            line=dict(color=colors_proj[i % len(colors_proj)], width=2),
        ))
        # Target line
        fig_proj.add_trace(go.Scatter(
            x=[0, 12], y=[TARGET_ALLOCATION[cls], TARGET_ALLOCATION[cls]],
            mode="lines", name=f"Target {cls}",
            line=dict(color=colors_proj[i % len(colors_proj)], width=1, dash="dot"),
            showlegend=False,
        ))

    fig_proj.update_layout(
        height=400, margin=dict(t=20, b=40),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ccc"),
        xaxis_title="Mes", yaxis_title="Allocation %",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_proj, use_container_width=True)

    total_12m = portfolio_total_usd + (aporte_usd * 12)
    st.caption(f"Portfolio estimado en 12 meses (sin rendimiento): US$ {total_12m:,.0f} | Aporte total: US$ {aporte_usd * 12:,.0f}")

    # --- WATCHLIST CEDEARS LIVE ---
    st.markdown("---")
    st.markdown("#### Watchlist CEDEARs — Señales para 20% anual")
    st.caption("Datos live de Yahoo Finance. Tier 1 = sobrevendidos, comprar YA. Tier 2 = buen precio. Tier 3 = esperar.")

    @st.cache_data(ttl=1800, show_spinner="Descargando datos de watchlist...")
    def _get_watchlist_data():
        import yfinance as yf
        import numpy as np
        rows = []
        for ticker, info in CEDEAR_WATCHLIST.items():
            try:
                hist = yf.download(ticker, period="6mo", interval="1d", progress=False)
                if hist.empty:
                    continue
                close = hist["Close"].squeeze()
                current = float(close.iloc[-1])
                chg_6m = (current / float(close.iloc[0]) - 1) * 100
                # RSI
                delta = close.diff()
                gain = delta.where(delta > 0, 0.0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
                rs = gain / loss.replace(0, np.nan)
                rsi = 100 - (100 / (1 + rs))
                rsi_val = float(rsi.iloc[-1]) if not rsi.empty and not pd.isna(rsi.iloc[-1]) else None
                # Drawdown from peak
                peak = float(close.max())
                dd = (current / peak - 1) * 100
                rows.append({
                    "Tier": info["tier"],
                    "Ticker": ticker,
                    "Sector": info["sector"],
                    "Precio USD": current,
                    "6m %": round(chg_6m, 1),
                    "RSI": round(rsi_val, 0) if rsi_val else None,
                    "DD Peak %": round(dd, 1),
                    "Tesis": info["tesis"],
                })
            except Exception:
                continue
        return rows

    wl_data = _get_watchlist_data()
    if wl_data:
        df_wl = pd.DataFrame(wl_data).sort_values(["Tier", "RSI"], ascending=[True, True])

        # Colorear por tier
        def tier_label(t):
            return {1: "COMPRAR", 2: "ACUMULAR", 3: "ESPERAR"}.get(t, "?")

        df_wl["Señal"] = df_wl["Tier"].apply(tier_label)

        st.dataframe(
            df_wl[["Señal", "Ticker", "Sector", "Precio USD", "6m %", "RSI", "DD Peak %", "Tesis"]],
            use_container_width=True, hide_index=True, height=450,
            column_config={
                "Precio USD": st.column_config.NumberColumn(format="US$ %,.1f"),
                "6m %": st.column_config.NumberColumn(format="%+.1f%%"),
                "RSI": st.column_config.NumberColumn(format="%.0f"),
                "DD Peak %": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )


# ============================================================
# TAB 3: POSICIONES
# ============================================================
with tab_positions:
    st.markdown("### Todas las Posiciones")
    st.caption("Clickeá cualquier encabezado para ordenar. Usá el buscador para filtrar.")

    # Buscador
    col_search, col_class_filter, col_broker_filter = st.columns([2, 1, 1])
    with col_search:
        search = st.text_input("Buscar ticker o nombre", "", placeholder="Ej: NVDA, Mercadolibre, bonos...")
    with col_class_filter:
        class_options = ["Todas"] + sorted(df_filtered["asset_class"].unique().tolist())
        class_filter = st.selectbox("Clase", class_options)
    with col_broker_filter:
        broker_options = ["Todos"] + sorted(df_filtered["source"].unique().tolist())
        broker_filter = st.selectbox("Broker", broker_options)

    # Aplicar filtros
    df_pos = df_filtered.sort_values("market_value_usd", ascending=False).copy()
    if search:
        mask = (
            df_pos["ticker"].str.contains(search, case=False, na=False) |
            df_pos["name"].str.contains(search, case=False, na=False)
        )
        df_pos = df_pos[mask]
    if class_filter != "Todas":
        df_pos = df_pos[df_pos["asset_class"] == class_filter]
    if broker_filter != "Todos":
        df_pos = df_pos[df_pos["source"] == broker_filter]

    # Preparar tabla con números reales (no strings) para que ordene bien
    df_display = df_pos[[
        "owner", "ticker", "name", "asset_class", "qty", "current_price_ars",
        "current_price_usd", "market_value_ars", "market_value_usd", "weight", "source"
    ]].copy()

    df_display.columns = [
        "Miembro", "Ticker", "Nombre", "Clase", "Cant.",
        "Precio ARS", "Precio USD", "Valor ARS", "Valor USD", "Peso %", "Broker"
    ]

    # column_config formatea visualmente pero mantiene el tipo numérico → ordenable
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=600,
        column_config={
            "Precio ARS": st.column_config.NumberColumn("Precio ARS", format="$ %,.0f"),
            "Precio USD": st.column_config.NumberColumn("Precio USD", format="US$ %,.2f"),
            "Valor ARS": st.column_config.NumberColumn("Valor ARS", format="$ %,.0f"),
            "Valor USD": st.column_config.NumberColumn("Valor USD", format="US$ %,.0f"),
            "Peso %": st.column_config.NumberColumn("Peso %", format="%.1f%%"),
            "Cant.": st.column_config.NumberColumn("Cant.", format="%,.2f"),
        },
    )

    st.caption(f"Mostrando {len(df_pos)} de {len(df_filtered)} posiciones")


# ============================================================
# TAB 6: CONCLUSIONES
# ============================================================
with tab_conclusiones:
    st.markdown("### Conclusiones y Acciones Recomendadas")
    st.caption("Síntesis automática basada en todos los datos del dashboard. Se actualiza al recargar.")

    # Recopilar datos necesarios (reutilizar los cacheados de macro tab)
    @st.cache_data(ttl=1800, show_spinner="Analizando datos...")
    def build_conclusions():
        g_data = get_global_indicators()
        ar_data = get_argentina_indicators()
        liq_signal, liq_score, liq_reasons = get_liquidity_signal(g_data)
        ar_signals = get_ar_decision_matrix(ar_data, g_data)
        return g_data, ar_data, liq_signal, liq_score, liq_reasons, ar_signals

    c_global, c_ar, c_liq_signal, c_liq_score, c_liq_reasons, c_ar_signals = build_conclusions()

    # --- CONTEXTO GENERAL ---
    st.markdown("#### 1. Contexto de Mercado")

    # Determinar sentimiento general
    vix_val = next((g["current"] for g in c_global if g["ticker"] == "^VIX"), None)
    dxy_data = next((g for g in c_global if g["ticker"] == "DX-Y.NYB"), None)
    sp500_data = next((g for g in c_global if g["ticker"] == "^GSPC"), None)
    btc_data = next((g for g in c_global if g["ticker"] == "BTC-USD"), None)
    eem_data = next((g for g in c_global if g["ticker"] == "EEM"), None)

    brecha_val = next((i["value"] for i in c_ar if "Brecha" in i["name"]), None)
    rp_val = next((i["value"] for i in c_ar if "EMBI" in i["name"]), None)

    # Contexto global
    ctx_items = []
    if c_liq_signal == "EXPANSIVA":
        ctx_items.append(("Liquidez global EXPANSIVA", "ok-box", "Favorable para activos de riesgo. Buen momento para acumular."))
    elif c_liq_signal == "CONTRACTIVA":
        ctx_items.append(("Liquidez global CONTRACTIVA", "alert-box", "Desfavorable. Mantener cash alto y ser selectivo."))
    else:
        ctx_items.append(("Liquidez global NEUTRAL", "info-box", "Sin señal clara. Operar normalmente con el plan de rebalanceo."))

    if vix_val:
        if vix_val > 30:
            ctx_items.append(("VIX en zona de miedo", "alert-box", f"VIX {vix_val:.0f} — pánico en mercado. Históricamente buen punto de entrada si tenés liquidez."))
        elif vix_val > 20:
            ctx_items.append(("VIX elevado", "info-box", f"VIX {vix_val:.0f} — volatilidad alta. Comprar de a poco, no todo junto."))

    if brecha_val is not None:
        if brecha_val < 5:
            ctx_items.append(("Brecha mínima", "ok-box", f"Brecha {brecha_val:.1f}% — convergencia cambiaria. Excelente momento para dolarizar pesos."))
        elif brecha_val > 30:
            ctx_items.append(("Brecha alta", "alert-box", f"Brecha {brecha_val:.1f}% — presión devaluatoria. Cautela con activos en pesos."))

    if rp_val:
        if rp_val < 500:
            ctx_items.append(("Riesgo país bajo", "ok-box", f"EMBI {rp_val:.0f} bp — Argentina en zona favorable. Bonos AR atractivos."))
        elif rp_val > 800:
            ctx_items.append(("Riesgo país alto", "alert-box", f"EMBI {rp_val:.0f} bp — stress soberano. Reducir exposición a bonos AR."))

    for title, box_class, desc in ctx_items:
        st.markdown(f'<div class="{box_class}"><strong>{title}</strong>: {desc}</div>', unsafe_allow_html=True)

    # --- PORTFOLIO ---
    st.markdown("---")
    st.markdown("#### 2. Estado del Portfolio")

    port_items = []

    # Cash
    if cash_pct > CASH_DEPLOY_ALERT:
        port_items.append(("Cash alto", "alert-box", f"Tenés {cash_pct:.1f}% en cash — considerar deployar en clases subponderadas."))
    elif cash_pct > 10:
        port_items.append(("Cash adecuado", "ok-box", f"{cash_pct:.1f}% en cash — reserva líquida suficiente."))

    # Concentración
    if top5_weight > MAX_CONCENTRATION_TOP5:
        top5_names = ", ".join(df_sorted.head(5)["ticker"].tolist())
        port_items.append(("Concentración alta", "alert-box", f"Top 5 ({top5_names}) = {top5_weight:.1f}% del portfolio. Diversificar."))

    # Desbalances vs target
    for cls, target in TARGET_ALLOCATION.items():
        actual = alloc_pct.get(cls, 0)
        diff = actual - target
        if diff > REBALANCE_THRESHOLD_PCT:
            port_items.append((f"{cls} sobreexpuesto", "info-box", f"Actual {actual:.1f}% vs target {target}% (+{diff:.1f}pp). No vender, pero no comprar más."))
        elif diff < -REBALANCE_THRESHOLD_PCT:
            port_items.append((f"{cls} subexpuesto", "alert-box", f"Actual {actual:.1f}% vs target {target}% ({diff:.1f}pp). Priorizar compras acá."))

    for title, box_class, desc in port_items:
        st.markdown(f'<div class="{box_class}"><strong>{title}</strong>: {desc}</div>', unsafe_allow_html=True)

    if not port_items:
        st.markdown('<div class="ok-box"><strong>Portfolio balanceado</strong>: Dentro de los rangos target.</div>', unsafe_allow_html=True)

    # --- ACCIONES CONCRETAS ---
    st.markdown("---")
    st.markdown("#### 3. Acciones Concretas para Este Mes")

    actions = []

    # Rebalanceo — qué comprar
    result_concl = calculate_rebalance(aporte_ars=APORTE_MENSUAL_ARS, dolar_mep=mep_live)
    for cls in sorted(result_concl["recommendation"].keys(),
                      key=lambda x: result_concl["recommendation"][x]["alloc_ars"], reverse=True):
        rec = result_concl["recommendation"][cls]
        if rec["alloc_ars"] < 5000:
            continue

        # Generar sugerencia específica por clase + contexto macro
        suggestion = ""
        if cls == "CEDEARs":
            if sp500_data and sp500_data.get("rsi") and sp500_data["rsi"] < 35:
                suggestion = "S&P500 sobrevendido — COMPRAR: TSM (RSI 33), META (PE 26), V (RSI 16), LLY (RSI 18). Después ASML y GOOGL."
            elif vix_val and vix_val > 25:
                suggestion = "VIX alto — ir de a poco. Priorizar: V (defensive), LLY (pharma), TSM (semiconductores). ASML y GOOGL en 2do tramo."
            else:
                suggestion = "Armar basket diversificado: TSM + META + V + ASML + GOOGL. NVDA mantener, no sobreponderar."

        elif cls == "Bonos Soberanos AR":
            if rp_val and rp_val < 600:
                suggestion = "Riesgo país bajo — GD35/AE38 atractivos (carry ~10% USD). TX28 BONCER para cobertura CER."
            else:
                suggestion = "Riesgo país moderado — priorizar TX28/TX31 BONCER (CER) sobre hard-dollar."

        elif cls == "Crypto":
            if btc_data and btc_data.get("rsi") and btc_data["rsi"] < 35:
                suggestion = "BTC sobrevendido — COMPRAR BTC directo (cold wallet) o IBIT (ETF). Mejor entry point del año."
            else:
                suggestion = "Mantener BTC. IBIT como vehículo regulado. MSTR solo si querés apalancamiento extra."

        elif cls == "Acciones AR":
            suggestion = "TGNO4 (gas, dividendo 13%), YPF (Vaca Muerta), GGAL (proxy Merval). Post-crash -26% = oportunidad generacional."

        elif cls == "FCI / Money Market":
            suggestion = "COCOUSDPA (FCI USD, liquidez T+1). Mantener como reserva para oportunidades."

        actions.append({
            "clase": cls,
            "ars": rec["alloc_ars"],
            "usd": rec["alloc_usd"],
            "suggestion": suggestion,
        })

    if actions:
        for a in actions:
            st.markdown(
                f'<div class="buy-box">'
                f'<strong>COMPRAR {a["clase"]}</strong>: $ {a["ars"]:,.0f} ARS (US$ {a["usd"]:,.0f})<br>'
                f'{a["suggestion"]}'
                f'</div>',
                unsafe_allow_html=True,
            )

    # --- ALERTAS MACRO ---
    st.markdown("---")
    st.markdown("#### 4. Alertas y Watchlist")

    watchlist = []

    # DXY
    if dxy_data and dxy_data["period_chg"] > 3:
        watchlist.append("**DXY subiendo** — dólar fuerte presiona emergentes. Si sigue, reducir exposición a bonos AR.")
    elif dxy_data and dxy_data["period_chg"] < -3:
        watchlist.append("**DXY bajando** — viento de cola para emergentes y Argentina.")

    # BTC
    if btc_data and btc_data["period_chg"] < -20:
        watchlist.append(f"**BTC en corrección** ({btc_data['period_chg']:+.0f}% 6m) — monitorear para acumular en soporte.")

    # EEM
    if eem_data and eem_data["period_chg"] < -8:
        watchlist.append("**Emergentes cayendo** — posible salida de capitales de Argentina. Cautela con acciones AR.")

    # Riesgo país tendencia
    rp_chg = next((i["value"] for i in c_ar if "30d chg" in i["name"]), None)
    if rp_chg and rp_chg > 10:
        watchlist.append(f"**Riesgo país subiendo** (+{rp_chg:.0f}% 30d) — monitorear de cerca. Puede impactar bonos.")

    if watchlist:
        for w in watchlist:
            st.markdown(f"- {w}")
    else:
        st.markdown("Sin alertas activas. Continuar con el plan de rebalanceo mensual.")

    # --- REGIME MATCHING HISTÓRICO ---
    st.markdown("---")
    st.markdown("#### 5. ¿Cuándo se dio este escenario antes?")
    st.caption("Backtest: buscamos semanas con S&P sobrevendido + VIX alto + oro rally + BTC corrigiendo + emergentes positivos")

    @st.cache_data(ttl=7200, show_spinner="Analizando 10 años de mercado...")
    def _get_regime():
        return get_regime_matching()

    regime = _get_regime()

    if regime and regime.get("matches"):
        st.markdown(f"**{regime['summary']}**")

        # Tabla de matches
        match_rows = []
        for m in regime["matches"]:
            fwd = m.get("forward_returns", {})
            match_rows.append({
                "Fecha": m["date"].strftime("%Y-%m-%d") if hasattr(m["date"], "strftime") else str(m["date"]),
                "S&P RSI": m["sp_rsi"],
                "VIX": m["vix"],
                "Oro 6m%": m.get("gld_6m", "—"),
                "BTC 6m%": m.get("btc_6m", "—"),
                "EEM 6m%": m.get("eem_6m", "—"),
                "Crit.": m["conditions_met"],
                "→ 1m%": fwd.get("1m", "—"),
                "→ 3m%": fwd.get("3m", "—"),
                "→ 6m%": fwd.get("6m", "—"),
                "→ 12m%": fwd.get("12m", "—"),
            })

        df_regime = pd.DataFrame(match_rows)
        st.dataframe(df_regime, use_container_width=True, hide_index=True)

        # Forward return stats
        fwd_stats = regime.get("forward_stats", {})
        if fwd_stats:
            st.markdown("##### Retornos del S&P500 después de escenarios similares")

            stat_cols = st.columns(4)
            for i, (period, label) in enumerate([("1m", "1 Mes"), ("3m", "3 Meses"), ("6m", "6 Meses"), ("12m", "12 Meses")]):
                stats = fwd_stats.get(period, {})
                if stats:
                    with stat_cols[i]:
                        avg = stats["avg"]
                        color = "#44ff44" if avg > 0 else "#ff4444"
                        pos_pct = stats.get("positive_pct", 0)
                        st.markdown(
                            f'<div style="background:#1a1a2e;border:1px solid {color};border-radius:10px;padding:14px;text-align:center;margin:4px 0;">'
                            f'<span style="color:#888;font-size:0.85rem">{label}</span><br>'
                            f'<span style="color:{color};font-size:1.8rem;font-weight:700">{avg:+.1f}%</span><br>'
                            f'<span style="color:#aaa;font-size:0.8rem">Mediana: {stats["median"]:+.1f}%</span><br>'
                            f'<span style="color:#888;font-size:0.75rem">Rango: {stats["min"]:+.1f}% a {stats["max"]:+.1f}%</span><br>'
                            f'<span style="color:#aaa;font-size:0.8rem">Positivo: {pos_pct}% de las veces (n={stats["n"]})</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

            st.markdown("")
            st.info("**Interpretación**: estos son los retornos históricos del S&P500 en los 1/3/6/12 meses POSTERIORES "
                    "a momentos con una combinación de variables similar a la actual. No es predicción, es contexto estadístico.")
    elif regime:
        st.info(regime.get("summary", "Sin datos"))
    else:
        st.warning("No se pudo ejecutar el análisis de regímenes históricos.")

    # --- MACRO THRESHOLDS (estilo Bernstein) ---
    st.markdown("---")
    st.markdown("#### 6. Umbrales Macro — Señales de Shock Económico")
    st.caption("Indicadores que históricamente predijeron crisis. Estilo Bernstein: energía/GDP, Buffett Indicator, CAPE, yield curve, credit spreads.")

    @st.cache_data(ttl=3600, show_spinner="Calculando umbrales macro...")
    def _get_thresholds():
        return get_macro_thresholds_live()

    thresholds = _get_thresholds()

    if thresholds:
        # Semáforo general
        th_signal, th_desc, th_counts = get_threshold_summary(thresholds)
        th_signal_colors = {
            "VÍA LIBRE": "#44ff44", "ATENCIÓN": "#ffcc44",
            "CAUTELA": "#ff8844", "ALERTA ALTA": "#ff4444",
        }
        th_color = th_signal_colors.get(th_signal, "#8888ff")
        st.markdown(
            f'<div style="background:#1a1a2e;border:2px solid {th_color};border-radius:10px;'
            f'padding:14px;text-align:center;margin:8px 0;">'
            f'<span style="color:{th_color};font-size:1.3rem;font-weight:700">'
            f'Semáforo Macro: {th_signal}</span><br>'
            f'<span style="color:#aaa;font-size:0.85rem">{th_desc}</span></div>',
            unsafe_allow_html=True,
        )

        # Cards por indicador
        status_colors = {
            "OK": ("#1b2d1b", "#44ff44"),
            "WARNING": ("#2d2d1b", "#ffcc44"),
            "PELIGRO": ("#2d2d1b", "#ffaa00"),
            "CRISIS": ("#2d1b1b", "#ff4444"),
        }

        # Primera fila: 4 indicadores
        row1 = thresholds[:4]
        row2 = thresholds[4:]

        for row_data in [row1, row2]:
            if not row_data:
                continue
            th_cols = st.columns(len(row_data))
            for i, t in enumerate(row_data):
                with th_cols[i]:
                    val = t.get("current_value")
                    status = t.get("status", "OK")
                    bg, color = status_colors.get(status, ("#1b1b2d", "#8888ff"))

                    if val is not None:
                        if isinstance(val, float) and val == int(val):
                            val_str = f"{int(val)}{t['unit']}"
                        else:
                            val_str = f"{val}{t['unit']}"
                    else:
                        val_str = "N/A"

                    danger = t.get("danger_zone", 0)
                    crisis = t.get("crisis_zone", 0)

                    st.markdown(
                        f'<div style="background:{bg};border:1px solid {color};border-radius:10px;padding:12px;text-align:center;margin:2px 0;">'
                        f'<span style="color:#aaa;font-size:0.65rem">{t["name"]}</span><br>'
                        f'<span style="color:{color};font-size:1.5rem;font-weight:700">{val_str}</span><br>'
                        f'<span style="color:{color};font-size:0.8rem;font-weight:600">{status}</span><br>'
                        f'<span style="color:#555;font-size:0.6rem">Peligro: {danger}{t["unit"]} | Crisis: {crisis}{t["unit"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if t.get("extra"):
                        st.caption(t["extra"])

        # Gráfico de energía/GDP histórico (el de Bernstein)
        energy_t = next((t for t in thresholds if "Energía" in t["name"]), None)
        if energy_t and energy_t.get("history"):
            st.markdown("##### Energía como % del GDP Global (Bernstein)")

            hist_data = energy_t["history"]
            years = [h[0] for h in hist_data]
            values = [h[1] for h in hist_data]
            labels = [h[2] for h in hist_data]

            # Colores por zona
            colors = []
            for v in values:
                if v >= 8.0:
                    colors.append("#ff4444")
                elif v >= 7.0:
                    colors.append("#ffaa00")
                else:
                    colors.append("#44cc88")

            fig_energy = go.Figure()
            fig_energy.add_trace(go.Bar(
                x=[str(y) for y in years], y=values,
                marker_color=colors,
                text=[f"{v}%<br>{l}" for v, l in zip(values, labels)],
                textposition="outside",
                textfont_size=9,
            ))
            fig_energy.add_hline(y=7, line_dash="dash", line_color="#ffaa00", line_width=1,
                                  annotation_text="7% peligro", annotation_position="right")
            fig_energy.add_hline(y=8, line_dash="dash", line_color="#ff4444", line_width=1,
                                  annotation_text="8% crisis", annotation_position="right")

            fig_energy.update_layout(
                height=350, margin=dict(t=30, b=30, l=40, r=40),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ccc"),
                yaxis_title="Fossil Fuel % del GDP",
                showlegend=False,
            )
            st.plotly_chart(fig_energy, use_container_width=True)
            st.caption("Fuente: BP Statistics, Bloomberg, IMF, Bernstein analysis. "
                       "Cada vez que energía superó 7-8% del GDP → shock económico (1973, 1980, 2008, 2022).")

        # Resumen de umbrales
        with st.expander("Interpretación de cada umbral"):
            for t in thresholds:
                st.markdown(f"- **{t['name']}**: {t.get('interpretation', '')}")

    # --- SENTIMENT DASHBOARD ---
    st.markdown("---")
    st.markdown("#### 7. Sentimiento de Mercado")

    @st.cache_data(ttl=1800, show_spinner="Consultando sentimiento...")
    def _get_sentiment():
        return get_sentiment_dashboard()

    sentiment = _get_sentiment()

    if sentiment:
        col_fg, col_sm = st.columns([1, 2])

        # Crypto Fear & Greed
        with col_fg:
            fg = sentiment.get("crypto_fear_greed")
            if fg:
                val = fg["value"]
                classification = fg["classification"]

                # Color por nivel
                if val <= 20:
                    fg_color = "#ff4444"
                elif val <= 40:
                    fg_color = "#ff8844"
                elif val <= 60:
                    fg_color = "#ffcc44"
                elif val <= 80:
                    fg_color = "#88ff44"
                else:
                    fg_color = "#44ff44"

                signal_name, signal_type, signal_desc = fg["signal"]

                st.markdown(
                    f'<div style="background:#1a1a2e;border:2px solid {fg_color};border-radius:12px;padding:18px;text-align:center;margin:4px 0;">'
                    f'<span style="color:#aaa;font-size:0.85rem">Crypto Fear & Greed</span><br>'
                    f'<span style="color:{fg_color};font-size:3rem;font-weight:700">{val}</span><br>'
                    f'<span style="color:{fg_color};font-size:1rem;font-weight:600">{classification}</span><br>'
                    f'<span style="color:#888;font-size:0.75rem">7d avg: {fg["avg_7d"]:.0f} | 30d avg: {fg["avg_30d"]:.0f} | Trend: {fg["trend"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if fg["extreme_fear_streak"] > 0:
                    st.warning(f"{fg['extreme_fear_streak']} dias consecutivos en Extreme Fear")

                # Mini sparkline
                if fg.get("history") and len(fg["history"]) > 5:
                    fig_fg = go.Figure(data=go.Scatter(
                        y=list(reversed(fg["history"])),
                        mode="lines+markers",
                        line=dict(color=fg_color, width=2),
                        marker=dict(size=3),
                    ))
                    fig_fg.add_hline(y=20, line_dash="dot", line_color="#ff4444", line_width=0.5)
                    fig_fg.add_hline(y=80, line_dash="dot", line_color="#44ff44", line_width=0.5)
                    fig_fg.update_layout(
                        height=150, margin=dict(t=5, b=5, l=20, r=20),
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        showlegend=False, xaxis=dict(visible=False),
                        yaxis=dict(range=[0, 100], color="#666"),
                    )
                    st.plotly_chart(fig_fg, use_container_width=True)
                    st.caption(f"Signal: **{signal_type}** — {signal_desc}")

        # Smart Money (DataRoma)
        with col_sm:
            sm = sentiment.get("smart_money")
            if sm:
                st.markdown(f"**Smart Money Tracker** (DataRoma — {sm['last_update']})")

                # Top buys/sells table
                sm_rows = []
                for entry in sm["top_buys"]:
                    signal_color = {
                        "COMPRA LIMPIA": "#44ff44",
                        "ROTACIÓN": "#ffcc44",
                        "MÁS VENDEN": "#ff8844",
                        "VENTA MASIVA": "#ff4444",
                        "SOLO VENTA": "#ff4444",
                    }.get(entry["signal"], "#888")

                    sm_rows.append({
                        "Ticker": entry["ticker"],
                        "Compran": entry["buyers"],
                        "Venden": entry["sellers"],
                        "Neto": entry["net"],
                        "Signal": entry["signal"],
                    })

                df_sm = pd.DataFrame(sm_rows)
                st.dataframe(df_sm, use_container_width=True, hide_index=True, height=300)

                # Buffett y Ackman highlights
                col_buf, col_ack = st.columns(2)
                with col_buf:
                    buf = sm["buffett_moves"]
                    st.markdown(f"**Buffett**: {buf['message']}")
                    st.caption(f"Compra: {', '.join(buf['buys'])}")
                    st.caption(f"Vende: {', '.join(buf['sells'])}")
                with col_ack:
                    ack = sm["ackman_moves"]
                    st.markdown(f"**Ackman**: {ack['message']}")
                    st.caption(f"Compra: {', '.join(ack['buys'])}")
                    st.caption(f"Vende: {', '.join(ack['sells'])}")

                # Near 52w low
                low_tickers = [e["ticker"] for e in sm.get("near_52w_low", [])]
                if low_tickers:
                    st.caption(f"Smart money holdings near 52w low (contrarian): {', '.join(low_tickers)}")

    # --- RESUMEN EJECUTIVO ---
    st.markdown("---")
    st.markdown("#### Resumen Ejecutivo")

    # Score general
    score = 0
    if c_liq_signal == "EXPANSIVA":
        score += 2
    elif c_liq_signal == "CONTRACTIVA":
        score -= 2
    if brecha_val is not None and brecha_val < 10:
        score += 1
    if rp_val and rp_val < 600:
        score += 1
    elif rp_val and rp_val > 800:
        score -= 2
    if vix_val and vix_val > 30:
        score -= 1  # miedo pero oportunidad
    if btc_data and btc_data.get("rsi") and btc_data["rsi"] < 30:
        score += 1

    if score >= 3:
        outlook = "MUY FAVORABLE"
        outlook_color = "#44ff44"
        outlook_desc = "Todas las señales alineadas. Momento óptimo para invertir el aporte completo y considerar aportes extra."
    elif score >= 1:
        outlook = "FAVORABLE"
        outlook_color = "#88ff88"
        outlook_desc = "Condiciones buenas. Invertir el aporte mensual según el plan de rebalanceo."
    elif score >= -1:
        outlook = "NEUTRAL"
        outlook_color = "#8888ff"
        outlook_desc = "Sin señal clara. Mantener el plan de rebalanceo sin cambios."
    else:
        outlook = "CAUTELA"
        outlook_color = "#ff8888"
        outlook_desc = "Señales adversas. Considerar mantener más cash y ser selectivo con las compras."

    st.markdown(
        f'<div style="background:#1a1a2e; border:2px solid {outlook_color}; border-radius:12px; '
        f'padding:24px; text-align:center; margin:10px 0;">'
        f'<span style="color:{outlook_color}; font-size:2rem; font-weight:700;">{outlook}</span><br>'
        f'<span style="color:#ccc; font-size:1.1rem;">{outlook_desc}</span><br>'
        f'<span style="color:#888; font-size:0.9rem;">Score: {score:+d} | '
        f'Liquidez: {c_liq_signal} | '
        f'{"Brecha: " + f"{brecha_val:.1f}%" if brecha_val else ""} | '
        f'{"RP: " + f"{rp_val:.0f}bp" if rp_val else ""}'
        f'</span></div>',
        unsafe_allow_html=True,
    )

    # --- SIMULACIÓN 20% ANUAL ---
    st.markdown("---")
    st.markdown("#### Proyección: 20% anual USD con target allocation")

    target_return = 0.20
    sim_years = [1, 2, 3, 5, 10]
    proj_cols = st.columns(len(sim_years))
    for i, yr in enumerate(sim_years):
        future = portfolio_total_usd * ((1 + target_return) ** yr)
        gain = future - portfolio_total_usd
        # Con aportes mensuales
        monthly = aporte_usd if 'aporte_usd' in dir() else APORTE_MENSUAL_ARS / mep_live
        future_with_aporte = portfolio_total_usd * ((1 + target_return) ** yr)
        for m in range(yr * 12):
            future_with_aporte += monthly * ((1 + target_return) ** ((yr * 12 - m) / 12))
        with proj_cols[i]:
            st.markdown(
                f'<div style="background:#1a1a2e;border:1px solid #44aaff;border-radius:10px;padding:14px;text-align:center;margin:4px 0;">'
                f'<span style="color:#888;font-size:0.8rem">{yr} año{"s" if yr>1 else ""}</span><br>'
                f'<span style="color:#44ff44;font-size:1.5rem;font-weight:700">US$ {future_with_aporte:,.0f}</span><br>'
                f'<span style="color:#888;font-size:0.75rem">Sin aportes: US$ {future:,.0f}</span><br>'
                f'<span style="color:#aaa;font-size:0.7rem">+US$ {future_with_aporte - portfolio_total_usd:,.0f}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
    st.caption(f"Base: US$ {portfolio_total_usd:,.0f} | Aporte: US$ {APORTE_MENSUAL_ARS / mep_live:,.0f}/mes | Target: 20% anual USD")
    st.caption("La cuenta: 30% bonos x10% + 37% CEDEARs x20% + 13% acciones AR x25% + 12% crypto x30% + 8% FCI x2% = ~17-20% ponderado")


# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption(f"Family Office v0.6 — Target 20% USD | {len(positions)} posiciones | Dólar MEP: ${mep_live:,.0f}")
st.caption("Para actualizar: descargá nuevos CSV de tenencia y reemplazá en _family_office/data/")
