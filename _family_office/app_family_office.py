"""
Family Office Dashboard — MVP con datos reales de CSV
Ejecutar: cd _family_office && streamlit run app_family_office.py
Puerto asignado: 8506 (ver PUERTOS.md en raíz del proyecto)
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from csv_parser import load_all_portfolios, DOLAR_MEP
from config_fo import TARGET_ALLOCATION, REBALANCE_THRESHOLD_PCT, MAX_DRAWDOWN_ALERT, MAX_CONCENTRATION_TOP5, CASH_DEPLOY_ALERT

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
    .metric-card {
        background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
        border-radius: 12px; padding: 20px; text-align: center;
        border: 1px solid #3d3d5c;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #e0e0e0; }
    .metric-label { font-size: 0.85rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
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
    st.markdown("""
    **Formato esperado (Cocos Capital):**
    - Descargá la tenencia desde Cocos como CSV
    - Poné el archivo en `_family_office/data/`
    - Nombre sugerido: `portfolio_cocos_nombre.csv`
    """)
    if load_errors:
        for e in load_errors:
            st.warning(e)
    st.stop()

# Convertir a DataFrame
df = pd.DataFrame(positions)
df_cash = pd.DataFrame(cash_list) if cash_list else pd.DataFrame(columns=["currency", "amount", "source", "owner"])

# Totales
total_usd = df["market_value_usd"].sum()
total_ars = df["market_value_ars"].sum()

# Cash total en USD
cash_usd = 0
if len(df_cash) > 0:
    for _, c in df_cash.iterrows():
        if c["currency"] == "USD":
            cash_usd += c["amount"]
        elif c["currency"] == "ARS":
            cash_usd += c["amount"] / DOLAR_MEP

portfolio_total_usd = total_usd + cash_usd
cash_pct = (cash_usd / portfolio_total_usd * 100) if portfolio_total_usd > 0 else 0

# Peso de cada posición
df["weight"] = df["market_value_usd"] / portfolio_total_usd * 100

# Allocation por asset class
alloc = df.groupby("asset_class")["market_value_usd"].sum()
alloc_pct = (alloc / portfolio_total_usd * 100).to_dict()

# Top 5 concentración
df_sorted = df.sort_values("market_value_usd", ascending=False)
top5_weight = df_sorted.head(5)["weight"].sum()

# Owners
owners = df["owner"].unique().tolist()

# ============================================================
# SIDEBAR — Filtros
# ============================================================
with st.sidebar:
    st.markdown("### Filtros")
    selected_owners = st.multiselect("Miembros", owners, default=owners)
    st.markdown("---")
    st.markdown(f"**Dólar MEP**: ${DOLAR_MEP:,.0f}")
    st.caption("Editá DOLAR_MEP en csv_parser.py o conectá API de Cocos")
    st.markdown("---")
    if load_errors:
        st.markdown("### Avisos")
        for e in load_errors:
            st.warning(e)

# Filtrar por owner
if selected_owners:
    df_filtered = df[df["owner"].isin(selected_owners)]
else:
    df_filtered = df

total_filtered_usd = df_filtered["market_value_usd"].sum()

# ============================================================
# HEADER
# ============================================================
st.markdown("## Family Office Dashboard")
st.caption(f"Datos de: {', '.join(df['source'].unique())} | {len(positions)} posiciones | {len(owners)} miembros")

# ============================================================
# FILA 1: KPIs
# ============================================================
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
    # Posición más grande
    if len(df_sorted) > 0:
        biggest = df_sorted.iloc[0]
        st.metric("Mayor Posición", biggest["ticker"], f"{biggest['weight']:.1f}%")

# ============================================================
# FILA 2: ALERTAS + ALLOCATION
# ============================================================
st.markdown("---")
col_alerts, col_alloc = st.columns([1, 2])

with col_alerts:
    st.markdown("### Alertas")
    alerts = []

    # Cash alto
    if cash_pct > CASH_DEPLOY_ALERT:
        alerts.append(f"**Cash alto**: {cash_pct:.1f}% — considerar deployar")

    # Concentración
    if top5_weight > MAX_CONCENTRATION_TOP5:
        top5_names = ", ".join(df_sorted.head(5)["ticker"].tolist())
        alerts.append(f"**Concentración**: top 5 ({top5_names}) = {top5_weight:.1f}%")

    # Rebalanceo vs targets
    for cls, target in TARGET_ALLOCATION.items():
        actual = alloc_pct.get(cls, 0)
        diff = actual - target
        if abs(diff) > REBALANCE_THRESHOLD_PCT:
            direction = "sobreexpuesto" if diff > 0 else "subexpuesto"
            alerts.append(f"**{cls}**: {direction} ({actual:.1f}% vs target {target}%)")

    # Clases que no están en el target pero tienen posiciones
    for cls in alloc_pct:
        if cls not in TARGET_ALLOCATION and alloc_pct[cls] > 5:
            alerts.append(f'<div class="info-box">**{cls}**: {alloc_pct[cls]:.1f}% — no tiene target definido</div>')

    if alerts:
        for a in alerts:
            if "info-box" in a:
                st.markdown(a, unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-box">{a}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ok-box">Sin alertas activas</div>', unsafe_allow_html=True)

with col_alloc:
    st.markdown("### Asset Allocation")

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

# ============================================================
# FILA 3: DONUT COMPOSICIÓN + POR MIEMBRO
# ============================================================
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
        # Si hay un solo miembro, mostrar top posiciones
        top_positions = df_sorted.head(8)
        fig_top = go.Figure(data=[go.Bar(
            x=top_positions["ticker"],
            y=top_positions["market_value_usd"],
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

# ============================================================
# FILA 4: EXPOSICIÓN CAMBIARIA
# ============================================================
st.markdown("---")
col_fx, col_by_class = st.columns([1, 2])

with col_fx:
    st.markdown("### Exposición Cambiaria")

    # Posiciones en ARS vs USD
    usd_direct = df[df["currency_original"] == "USD"]["market_value_usd"].sum()
    ars_in_usd = df[df["currency_original"] == "ARS"]["market_value_usd"].sum()

    # CEDEARs cotizan en ARS pero son dólares subyacentes
    cedear_usd = df[df["asset_class"] == "CEDEARs"]["market_value_usd"].sum()
    bonos_usd = df[df["asset_class"] == "Bonos Soberanos AR"]["market_value_usd"].sum()

    # Exposure real: CEDEARs + bonos USD + FCI USD + cash USD = dolarizado
    # Acciones AR = peso
    acciones_ar = df[df["asset_class"] == "Acciones AR"]["market_value_usd"].sum()
    fci_ars = df[(df["asset_class"] == "FCI / Money Market") & (df["currency_original"] == "ARS")]["market_value_usd"].sum()
    fci_usd = df[(df["asset_class"] == "FCI / Money Market") & (df["currency_original"] == "USD")]["market_value_usd"].sum()

    dolarizado = cedear_usd + bonos_usd + fci_usd + usd_direct + cash_usd
    pesificado = acciones_ar + fci_ars

    total_exposure = dolarizado + pesificado
    if total_exposure > 0:
        fx_data = pd.DataFrame([
            {"Exposición": "Dolarizado", "US$": dolarizado, "%": dolarizado/total_exposure*100},
            {"Exposición": "Pesificado", "US$": pesificado, "%": pesificado/total_exposure*100},
        ])
        fx_data["US$"] = fx_data["US$"].apply(lambda x: f"${x:,.0f}")
        fx_data["%"] = fx_data["%"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(fx_data, use_container_width=True, hide_index=True)

    st.markdown(f"**Dólar MEP**: ${DOLAR_MEP:,.0f}")
    st.caption("CEDEARs y bonos en USD se consideran dolarizados")

with col_by_class:
    st.markdown("### Detalle por Clase de Activo")
    class_summary = df.groupby("asset_class").agg(
        Posiciones=("ticker", "count"),
        Total_USD=("market_value_usd", "sum"),
        Total_ARS=("market_value_ars", "sum"),
    ).sort_values("Total_USD", ascending=False).reset_index()
    class_summary["Peso %"] = (class_summary["Total_USD"] / portfolio_total_usd * 100).round(1)
    class_summary["Total_USD"] = class_summary["Total_USD"].apply(lambda x: f"US$ {x:,.0f}")
    class_summary["Total_ARS"] = class_summary["Total_ARS"].apply(lambda x: f"$ {x:,.0f}")
    class_summary.columns = ["Clase", "Pos.", "Total USD", "Total ARS", "Peso %"]
    st.dataframe(class_summary, use_container_width=True, hide_index=True)

# ============================================================
# FILA 5: POSICIONES DETALLE
# ============================================================
st.markdown("---")
st.markdown("### Todas las Posiciones")

df_display = df_filtered.sort_values("market_value_usd", ascending=False)[[
    "owner", "ticker", "name", "asset_class", "qty", "current_price_ars",
    "current_price_usd", "market_value_ars", "market_value_usd", "weight", "source"
]].copy()

df_display.columns = [
    "Miembro", "Ticker", "Nombre", "Clase", "Cant.",
    "Precio ARS", "Precio USD", "Valor ARS", "Valor USD", "Peso %", "Broker"
]

# Formatear
df_display["Precio ARS"] = df_display["Precio ARS"].apply(lambda x: f"$ {x:,.0f}")
df_display["Precio USD"] = df_display["Precio USD"].apply(lambda x: f"US$ {x:,.2f}")
df_display["Valor ARS"] = df_display["Valor ARS"].apply(lambda x: f"$ {x:,.0f}")
df_display["Valor USD"] = df_display["Valor USD"].apply(lambda x: f"US$ {x:,.0f}")
df_display["Peso %"] = df_display["Peso %"].apply(lambda x: f"{x:.1f}%")

st.dataframe(df_display, use_container_width=True, hide_index=True, height=500)

# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption(f"Family Office v0.2 — Datos reales de CSV | {len(positions)} posiciones | Dólar MEP: ${DOLAR_MEP:,.0f}")
st.caption("Para actualizar: descargá nuevos CSV de tenencia y reemplazá en _family_office/data/")
