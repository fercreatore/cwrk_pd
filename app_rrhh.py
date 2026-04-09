#!/usr/bin/env python3
"""
app_rrhh.py — Dashboard RRHH Calzalindo
=========================================
Módulos:
  1. Nómina y Sueldos
  2. Productividad y Incentivos Vendedores
  3. Reclutamiento (pipeline)
  4. Overview Ejecutivo

EJECUTAR:
  streamlit run app_rrhh.py --server.port 8507

Autor: Cowork + Claude — Abril 2026
"""

# ── FIX SSL: DEBE ir ANTES de importar pyodbc ──
import os as _os
import platform as _platform
if _platform.system() != "Windows":
    _ssl_conf = "/tmp/openssl_legacy.cnf"
    if not _os.path.exists(_ssl_conf):
        with open(_ssl_conf, "w") as _f:
            _f.write(
                "openssl_conf = openssl_init\n"
                "[openssl_init]\nssl_conf = ssl_sect\n"
                "[ssl_sect]\nsystem_default = system_default_sect\n"
                "[system_default_sect]\n"
                "MinProtocol = TLSv1\nCipherString = DEFAULT@SECLEVEL=0\n"
            )
    _os.environ["OPENSSL_CONF"] = _ssl_conf

import streamlit as st
import pandas as pd
import numpy as np
import pyodbc
import json
import os
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from config import get_conn_string, CONN_COMPRAS, CONN_ARTICULOS

# ============================================================================
# CONSTANTES
# ============================================================================
CONN_ANALITICA = get_conn_string("omicronvt")
CONN_ERP01 = get_conn_string("msgestion01")

# Depósitos = Locales
DEPOSITOS = {
    0: "Central",
    1: "Glam",
    2: "Norte",
    4: "Marroquinería",
    6: "Cuore/Chovet",
    7: "Eva Perón",
    8: "Junín/Alcorta",
    10: "Alternativo",
}

# Marcas gastos (excluir de ventas)
MARCAS_GASTOS = (1316, 1317, 1158, 436)

# Códigos movimiento sueldos
# 10 = sueldo bruto, 7 = deducciones, 11 = aportes, 6 = adelantos, 12 = otros
COD_SUELDO_BRUTO = (10,)
COD_SUELDO_TODOS = (6, 7, 10, 11, 12)

# IPC mensual (hardcoded — actualizar periódicamente)
IPC_MENSUAL = {
    "2025-04": 3.4, "2025-05": 3.7, "2025-06": 2.7,
    "2025-07": 2.4, "2025-08": 3.5, "2025-09": 3.5,
    "2025-10": 2.7, "2025-11": 2.4, "2025-12": 2.5,
    "2026-01": 2.2, "2026-02": 2.4, "2026-03": 3.7,
}

# Perfiles de puesto conocidos
PERFILES = {
    1136: {"nombre": "Gonzalo Bernardi", "puesto": "Asistente Depósito Jr"},
    1148: {"nombre": "Emanuel Cisneros", "puesto": "Asistente Depósito Jr"},
    # Mariana - buscar por nombre
    68:   {"nombre": "Tamara Galván", "puesto": "Ventas y RRHH"},
    117:  {"nombre": "Maite Giménez", "puesto": "RRHH"},
    1152: {"nombre": "Fabiola Texeira", "puesto": "Community Manager"},
}

# ============================================================================
# STREAMLIT CONFIG
# ============================================================================
st.set_page_config(
    page_title="RRHH — Calzalindo",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Dark theme CSS
st.markdown("""
<style>
    .stApp { background-color: #0f0f1a; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; }
    [data-testid="stMetricDelta"] { font-size: 0.9rem; }
    .medal-gold { color: #fbbf24; font-size: 2rem; }
    .medal-silver { color: #94a3b8; font-size: 2rem; }
    .medal-bronze { color: #cd7f32; font-size: 2rem; }
    div[data-testid="stDataFrame"] { border: 1px solid rgba(99,102,241,0.2); border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# DATABASE — conexión fresh cada query (SQL Server 2012 corta idle)
# ============================================================================
def _connect(conn_str):
    """Abre conexión fresca. No cachear: SQL Server corta idle."""
    return pyodbc.connect(conn_str, timeout=15)


@st.cache_data(ttl=300, show_spinner="Consultando SQL Server...")
def query_df(sql, conn_str=CONN_COMPRAS):
    """Execute SQL and return DataFrame. Cached 5 min."""
    try:
        conn = _connect(conn_str)
        df = pd.read_sql(sql, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error SQL: {e}")
        return pd.DataFrame()


def exec_sql(sql, params=None, conn_str=CONN_ANALITICA):
    """Execute INSERT/UPDATE on omicronvt."""
    try:
        conn = _connect(conn_str)
        c = conn.cursor()
        if params:
            c.execute(sql, params)
        else:
            c.execute(sql)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error SQL: {e}")
        return False


# ============================================================================
# DATA LOADERS
# ============================================================================

@st.cache_data(ttl=300)
def load_viajantes():
    return query_df("""
        SELECT codigo, descripcion, porcentaje
        FROM msgestionC.dbo.viajantes
        ORDER BY codigo
    """)


@st.cache_data(ttl=300)
def load_ventas_vendedor(dias=30):
    """Ventas por vendedor en los últimos N días."""
    return query_df(f"""
        SELECT v.viajante, vj.descripcion as vendedor, v.deposito,
            v.total_item, v.cantidad, v.cuenta, v.fecha, v.operacion,
            v.codigo
        FROM msgestionC.dbo.ventas1 v WITH (NOLOCK)
        LEFT JOIN msgestionC.dbo.viajantes vj ON v.viajante = vj.codigo
        WHERE v.codigo IN (1,3)
            AND v.viajante NOT IN (7, 36)
            AND v.fecha >= DATEADD(DAY, -{dias}, GETDATE())
    """)


@st.cache_data(ttl=300)
def load_ventas_periodo(fecha_desde, fecha_hasta):
    """Ventas en un rango de fechas."""
    return query_df(f"""
        SELECT v.viajante, vj.descripcion as vendedor, v.deposito,
            v.total_item, v.cantidad, v.cuenta, v.fecha, v.operacion,
            v.codigo
        FROM msgestionC.dbo.ventas1 v WITH (NOLOCK)
        LEFT JOIN msgestionC.dbo.viajantes vj ON v.viajante = vj.codigo
        WHERE v.codigo IN (1,3)
            AND v.viajante NOT IN (7, 36)
            AND v.fecha >= '{fecha_desde}'
            AND v.fecha < '{fecha_hasta}'
    """)


@st.cache_data(ttl=600)
def load_ventas_mensual_vendedores(meses=6):
    """Ventas mensuales por vendedor, últimos N meses."""
    return query_df(f"""
        SELECT v.viajante, vj.descripcion as vendedor, v.deposito,
            YEAR(v.fecha) as anio, MONTH(v.fecha) as mes,
            SUM(CASE WHEN v.operacion='+' THEN v.total_item ELSE -v.total_item END) as facturacion,
            SUM(CASE WHEN v.operacion='+' THEN v.cantidad ELSE -v.cantidad END) as pares,
            COUNT(DISTINCT v.cuenta) as clientes,
            COUNT(DISTINCT CAST(v.fecha AS DATE)) as dias_trabajados
        FROM msgestionC.dbo.ventas1 v WITH (NOLOCK)
        LEFT JOIN msgestionC.dbo.viajantes vj ON v.viajante = vj.codigo
        WHERE v.codigo IN (1,3)
            AND v.viajante NOT IN (7, 36)
            AND v.fecha >= DATEADD(MONTH, -{meses}, GETDATE())
        GROUP BY v.viajante, vj.descripcion, v.deposito,
                 YEAR(v.fecha), MONTH(v.fecha)
    """)


@st.cache_data(ttl=600)
def load_empleados():
    return query_df("""
        SELECT numero, denominacion, fecha_ingreso, fecha_nacimiento,
               cuil, zona, motivo_baja, fecha_baja
        FROM msgestion01.dbo.empleados
        ORDER BY numero
    """, CONN_ERP01)


@st.cache_data(ttl=600)
def load_sueldos_mensual(meses=12):
    return query_df(f"""
        SELECT numero_cuenta, fecha_contable, codigo_movimiento,
               importe, operacion
        FROM msgestion01.dbo.moviempl1
        WHERE fecha_contable >= DATEADD(MONTH, -{meses}, GETDATE())
    """, CONN_ERP01)


# ============================================================================
# HELPERS
# ============================================================================

def dep_nombre(dep):
    try:
        return DEPOSITOS.get(int(dep), f"Dep {dep}") if dep is not None and not pd.isna(dep) else "?"
    except (ValueError, TypeError):
        return "?"


def _get_activos(df_emp):
    """Filtra empleados activos (motivo_baja != 'B')."""
    if df_emp.empty or "motivo_baja" not in df_emp.columns:
        return pd.DataFrame()
    return df_emp[
        (df_emp["motivo_baja"] != "B") | (df_emp["motivo_baja"].isna())
    ].copy()


def calcular_ranking(df_ventas):
    """Calcula ranking de vendedores desde DataFrame de ventas."""
    if df_ventas.empty:
        return pd.DataFrame()

    df = df_ventas.copy()
    # Aplicar signo
    df["facturacion"] = df.apply(
        lambda r: r["total_item"] if r["operacion"] == "+" else -r["total_item"], axis=1
    )
    df["pares_neto"] = df.apply(
        lambda r: r["cantidad"] if r["operacion"] == "+" else -r["cantidad"], axis=1
    )

    # Tickets = comprobantes únicos (facturas)
    tickets = df[df["operacion"] == "+"].groupby("viajante").agg(
        tickets=("cuenta", "count")
    ).reset_index()

    ranking = df.groupby(["viajante", "vendedor", "deposito"]).agg(
        facturacion=("facturacion", "sum"),
        pares=("pares_neto", "sum"),
        clientes=("cuenta", "nunique"),
    ).reset_index()

    ranking = ranking.merge(tickets, on="viajante", how="left")
    ranking["tickets"] = ranking["tickets"].fillna(0).astype(int)
    ranking["ticket_prom"] = (ranking["facturacion"] / ranking["tickets"].replace(0, 1)).round(0)
    ranking["local"] = ranking["deposito"].apply(dep_nombre)
    ranking = ranking.sort_values("facturacion", ascending=False).reset_index(drop=True)
    ranking.index = ranking.index + 1  # Start from 1

    return ranking


def formato_moneda(valor):
    if pd.isna(valor) or valor == 0:
        return "$0"
    if abs(valor) >= 1_000_000:
        return f"${valor/1_000_000:,.1f}M"
    if abs(valor) >= 1_000:
        return f"${valor/1_000:,.0f}K"
    return f"${valor:,.0f}"


# ============================================================================
# MÓDULO 2: PRODUCTIVIDAD Y INCENTIVOS VENDEDORES
# ============================================================================

def render_productividad():
    st.header("📊 Productividad y Incentivos — Vendedores")

    # ── Configuración en sidebar ──
    with st.sidebar:
        st.subheader("⚙️ Configuración")
        dias = st.selectbox("Período", [7, 15, 30, 60], index=2,
                           format_func=lambda x: f"Últimos {x} días")

        st.divider()
        st.subheader("🎯 Metas mensuales")
        meta_facturacion = st.number_input("Meta facturación ($)", value=15_000_000,
                                           step=1_000_000, format="%d")
        meta_pares = st.number_input("Meta pares", value=400, step=50)
        meta_ticket = st.number_input("Meta ticket promedio ($)", value=30_000,
                                      step=5_000, format="%d")
        pct_bonus = st.number_input("Bonus por superar meta (%)", value=2.0,
                                    step=0.5, min_value=0.0, max_value=20.0)

        st.divider()
        st.subheader("🏪 Filtro por local")
        filtro_dep = st.multiselect(
            "Locales", options=list(DEPOSITOS.keys()),
            format_func=dep_nombre, default=list(DEPOSITOS.keys())
        )

    # ── Cargar datos ──
    df_ventas = load_ventas_vendedor(dias)
    if df_ventas.empty:
        st.warning("Sin datos de ventas en el período seleccionado.")
        return

    # Filtrar por depósito
    if filtro_dep:
        df_ventas = df_ventas[df_ventas["deposito"].isin(filtro_dep)]

    ranking = calcular_ranking(df_ventas)
    if ranking.empty:
        st.warning("Sin datos para los filtros seleccionados.")
        return

    # ── Sub-tabs ──
    tab_rank, tab_comp, tab_evol, tab_incent, tab_simul = st.tabs([
        "🏆 Ranking", "📈 Comparativo", "📉 Evolución", "🎯 Incentivos", "🧮 Simulador"
    ])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB: RANKING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_rank:
        # KPIs globales
        total_fact = ranking["facturacion"].sum()
        total_pares = ranking["pares"].sum()
        total_tickets = ranking["tickets"].sum()
        ticket_prom_global = total_fact / total_tickets if total_tickets > 0 else 0
        n_vendedores = len(ranking[ranking["facturacion"] > 0])

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Facturación", formato_moneda(total_fact))
        c2.metric("Pares vendidos", f"{int(total_pares):,}")
        c3.metric("Tickets", f"{int(total_tickets):,}")
        c4.metric("Ticket promedio", formato_moneda(ticket_prom_global))
        c5.metric("Vendedores activos", n_vendedores)

        st.divider()

        # 🥇🥈🥉 Top 3
        top3 = ranking.head(3)
        if len(top3) >= 3:
            medals = ["🥇", "🥈", "🥉"]
            cols = st.columns(3)
            for i, (_, row) in enumerate(top3.iterrows()):
                with cols[i]:
                    st.markdown(f"### {medals[i]} {row['vendedor']}")
                    st.markdown(f"**{row['local']}**")
                    st.metric("Facturación", formato_moneda(row["facturacion"]))
                    st.metric("Pares", f"{int(row['pares']):,}")
                    st.metric("Ticket prom.", formato_moneda(row["ticket_prom"]))

        st.divider()

        # Ranking completo
        st.subheader("Ranking completo")

        # Selector de ordenamiento
        sort_by = st.selectbox("Ordenar por", ["facturacion", "pares", "ticket_prom", "clientes"],
                              format_func=lambda x: {
                                  "facturacion": "Facturación",
                                  "pares": "Pares vendidos",
                                  "ticket_prom": "Ticket promedio",
                                  "clientes": "Clientes atendidos",
                              }[x])

        ranking_sorted = ranking.sort_values(sort_by, ascending=False).reset_index(drop=True)
        ranking_sorted.index = ranking_sorted.index + 1

        display_cols = ["vendedor", "local", "facturacion", "pares", "tickets",
                       "ticket_prom", "clientes"]
        df_display = ranking_sorted[display_cols].copy()
        df_display.columns = ["Vendedor", "Local", "Facturación", "Pares", "Tickets",
                            "Ticket Prom.", "Clientes"]

        st.dataframe(
            df_display.style.format({
                "Facturación": "${:,.0f}",
                "Ticket Prom.": "${:,.0f}",
                "Pares": "{:,.0f}",
            }),
            use_container_width=True,
            height=min(600, 35 * len(df_display) + 38),
        )

        # Facturación por local
        st.subheader("Facturación por local")
        fact_local = ranking.groupby("local")["facturacion"].sum().sort_values(ascending=False)
        import plotly.express as px
        fig = px.bar(
            x=fact_local.index, y=fact_local.values,
            labels={"x": "Local", "y": "Facturación"},
            color=fact_local.values,
            color_continuous_scale="Viridis",
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB: COMPARATIVO
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_comp:
        st.subheader("Comparativo: Mes actual vs Anterior vs Mismo mes año anterior")

        hoy = date.today()
        # Mes actual (hasta hoy)
        inicio_mes = hoy.replace(day=1)
        # Mes anterior
        inicio_mes_ant = (inicio_mes - timedelta(days=1)).replace(day=1)
        fin_mes_ant = inicio_mes - timedelta(days=1)
        # Mismo mes año anterior
        inicio_yoy = inicio_mes.replace(year=hoy.year - 1)
        fin_yoy = hoy.replace(year=hoy.year - 1)

        df_actual = load_ventas_periodo(inicio_mes.isoformat(), (hoy + timedelta(days=1)).isoformat())
        df_anterior = load_ventas_periodo(inicio_mes_ant.isoformat(), inicio_mes.isoformat())
        df_yoy = load_ventas_periodo(inicio_yoy.isoformat(), (fin_yoy + timedelta(days=1)).isoformat())

        if filtro_dep:
            df_actual = df_actual[df_actual["deposito"].isin(filtro_dep)]
            df_anterior = df_anterior[df_anterior["deposito"].isin(filtro_dep)]
            df_yoy = df_yoy[df_yoy["deposito"].isin(filtro_dep)]

        rank_actual = calcular_ranking(df_actual)
        rank_anterior = calcular_ranking(df_anterior)
        rank_yoy = calcular_ranking(df_yoy)

        # Métricas globales comparativas
        def _totales(r):
            if r.empty:
                return 0, 0, 0
            return r["facturacion"].sum(), r["pares"].sum(), r["tickets"].sum()

        fact_a, pares_a, tick_a = _totales(rank_actual)
        fact_ant, pares_ant, tick_ant = _totales(rank_anterior)
        fact_yoy, pares_yoy, tick_yoy = _totales(rank_yoy)

        # Días transcurridos para proyección
        dias_mes = hoy.day
        dias_mes_completo = (inicio_mes + relativedelta(months=1) - timedelta(days=1)).day

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"**Mes actual** ({inicio_mes.strftime('%b %Y')}, {dias_mes} días)")
            st.metric("Facturación", formato_moneda(fact_a),
                      delta=f"{(fact_a/fact_ant-1)*100:+.0f}% vs ant." if fact_ant > 0 else None)
            st.metric("Pares", f"{int(pares_a):,}",
                      delta=f"{(pares_a/pares_ant-1)*100:+.0f}% vs ant." if pares_ant > 0 else None)
            if dias_mes > 0:
                proyeccion = fact_a / dias_mes * dias_mes_completo
                st.caption(f"Proyección mes: {formato_moneda(proyeccion)}")

        with c2:
            st.markdown(f"**Mes anterior** ({inicio_mes_ant.strftime('%b %Y')})")
            st.metric("Facturación", formato_moneda(fact_ant))
            st.metric("Pares", f"{int(pares_ant):,}")

        with c3:
            st.markdown(f"**Mismo mes {hoy.year-1}** ({inicio_yoy.strftime('%b %Y')}, {dias_mes}d)")
            st.metric("Facturación", formato_moneda(fact_yoy),
                      delta=f"{(fact_a/fact_yoy-1)*100:+.0f}% YoY" if fact_yoy > 0 else None)
            st.metric("Pares", f"{int(pares_yoy):,}",
                      delta=f"{(pares_a/pares_yoy-1)*100:+.0f}% YoY" if pares_yoy > 0 else None)

        st.divider()

        # Tabla comparativa por vendedor
        if not rank_actual.empty:
            comp = rank_actual[["viajante", "vendedor", "local", "facturacion", "pares", "ticket_prom"]].copy()
            comp.columns = ["viajante", "Vendedor", "Local", "Fact. Actual", "Pares Actual", "Ticket Actual"]

            if not rank_anterior.empty:
                ant = rank_anterior[["viajante", "facturacion", "pares"]].copy()
                ant.columns = ["viajante", "Fact. Anterior", "Pares Anterior"]
                comp = comp.merge(ant, on="viajante", how="left")
                comp["Var. %"] = ((comp["Fact. Actual"] / comp["Fact. Anterior"].replace(0, np.nan) - 1) * 100).round(0)
            else:
                comp["Fact. Anterior"] = 0
                comp["Pares Anterior"] = 0
                comp["Var. %"] = None

            comp = comp.sort_values("Fact. Actual", ascending=False)
            display = comp.drop(columns=["viajante"])

            st.dataframe(
                display.style.format({
                    "Fact. Actual": "${:,.0f}",
                    "Fact. Anterior": "${:,.0f}",
                    "Ticket Actual": "${:,.0f}",
                    "Var. %": "{:+.0f}%",
                    "Pares Actual": "{:.0f}",
                    "Pares Anterior": "{:.0f}",
                }).applymap(
                    lambda v: "color: #34d399" if isinstance(v, (int, float)) and v > 0
                    else ("color: #f87171" if isinstance(v, (int, float)) and v < 0 else ""),
                    subset=["Var. %"]
                ),
                use_container_width=True,
                height=min(600, 35 * len(display) + 38),
            )

        # Mayor crecimiento
        if not rank_actual.empty and not rank_anterior.empty:
            st.subheader("🚀 Mayor crecimiento mes a mes")
            growth = rank_actual[["viajante", "vendedor", "local", "facturacion"]].merge(
                rank_anterior[["viajante", "facturacion"]],
                on="viajante", suffixes=("_act", "_ant")
            )
            growth = growth[growth["facturacion_ant"] > 1_000_000]  # Solo con base mínima
            growth["crecimiento"] = ((growth["facturacion_act"] / growth["facturacion_ant"] - 1) * 100).round(0)
            growth = growth.sort_values("crecimiento", ascending=False).head(5)

            if not growth.empty:
                for _, row in growth.iterrows():
                    st.markdown(
                        f"**{row['vendedor']}** ({row['local']}): "
                        f"{formato_moneda(row['facturacion_ant'])} → {formato_moneda(row['facturacion_act'])} "
                        f"(**{row['crecimiento']:+.0f}%**)"
                    )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB: EVOLUCIÓN
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_evol:
        st.subheader("Evolución mensual por vendedor")

        df_mensual = load_ventas_mensual_vendedores(meses=6)
        if df_mensual.empty:
            st.warning("Sin datos mensuales.")
        else:
            if filtro_dep:
                df_mensual = df_mensual[df_mensual["deposito"].isin(filtro_dep)]

            # Agrupar por vendedor y mes (un vendedor puede vender en varios locales)
            df_evol = df_mensual.groupby(["viajante", "vendedor", "anio", "mes"]).agg(
                facturacion=("facturacion", "sum"),
                pares=("pares", "sum"),
                clientes=("clientes", "sum"),
            ).reset_index()

            df_evol["periodo"] = df_evol.apply(
                lambda r: f"{int(r['anio'])}-{int(r['mes']):02d}", axis=1
            )

            # Top N vendedores por facturación total para no saturar el gráfico
            top_n = st.slider("Top N vendedores", 5, 25, 10)
            top_vendedores = df_evol.groupby("vendedor")["facturacion"].sum().nlargest(top_n).index.tolist()
            df_plot = df_evol[df_evol["vendedor"].isin(top_vendedores)]

            metrica = st.radio("Métrica", ["facturacion", "pares", "clientes"],
                             format_func=lambda x: {"facturacion": "Facturación", "pares": "Pares", "clientes": "Clientes"}[x],
                             horizontal=True)

            import plotly.express as px
            fig = px.line(
                df_plot, x="periodo", y=metrica, color="vendedor",
                markers=True,
                labels={"periodo": "Mes", metrica: metrica.title(), "vendedor": "Vendedor"},
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", y=-0.2),
                height=500,
            )
            st.plotly_chart(fig, use_container_width=True)

            # Tabla resumen mensual
            st.subheader("Resumen mensual")
            pivot = df_evol.pivot_table(
                index="vendedor", columns="periodo", values="facturacion",
                aggfunc="sum", fill_value=0
            )
            pivot["TOTAL"] = pivot.sum(axis=1)
            pivot = pivot.sort_values("TOTAL", ascending=False).head(top_n)

            st.dataframe(
                pivot.style.format("${:,.0f}"),
                use_container_width=True,
            )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB: INCENTIVOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_incent:
        st.subheader("🎯 Sistema de Incentivos")

        st.info(f"**Metas configuradas:** Facturación ${meta_facturacion:,.0f} | "
                f"Pares {meta_pares} | Ticket ${meta_ticket:,.0f} | "
                f"Bonus {pct_bonus}% sobre facturación excedente")

        # Usar mes actual para incentivos
        hoy = date.today()
        inicio_mes = hoy.replace(day=1)
        df_mes = load_ventas_periodo(inicio_mes.isoformat(), (hoy + timedelta(days=1)).isoformat())
        if filtro_dep:
            df_mes = df_mes[df_mes["deposito"].isin(filtro_dep)]

        rank_mes = calcular_ranking(df_mes)
        if rank_mes.empty:
            st.warning("Sin datos para el mes actual.")
        else:
            # Proyección a fin de mes
            dias_transcurridos = hoy.day
            dias_mes_total = (inicio_mes + relativedelta(months=1) - timedelta(days=1)).day
            factor_proy = dias_mes_total / dias_transcurridos if dias_transcurridos > 0 else 1

            incentivos = rank_mes[["viajante", "vendedor", "local", "facturacion", "pares", "ticket_prom"]].copy()
            incentivos["fact_proyectada"] = (incentivos["facturacion"] * factor_proy).round(0)
            incentivos["pares_proyectados"] = (incentivos["pares"] * factor_proy).round(0)

            # Cumplimiento
            incentivos["cumpl_fact"] = (incentivos["fact_proyectada"] / meta_facturacion * 100).round(0)
            incentivos["cumpl_pares"] = (incentivos["pares_proyectados"] / meta_pares * 100).round(0)
            incentivos["cumpl_ticket"] = (incentivos["ticket_prom"] / meta_ticket * 100).round(0)

            # Bonus
            incentivos["excedente"] = (incentivos["fact_proyectada"] - meta_facturacion).clip(lower=0)
            incentivos["bonus"] = (incentivos["excedente"] * pct_bonus / 100).round(0)

            # Status
            def _status(row):
                if row["cumpl_fact"] >= 100 and row["cumpl_pares"] >= 100:
                    return "✅ Supera"
                elif row["cumpl_fact"] >= 80:
                    return "🟡 En camino"
                else:
                    return "🔴 Bajo meta"
            incentivos["status"] = incentivos.apply(_status, axis=1)

            # Alertas: bajo 80%
            bajo_meta = incentivos[incentivos["cumpl_fact"] < 80]
            if not bajo_meta.empty:
                st.warning(f"⚠️ {len(bajo_meta)} vendedores por debajo del 80% de la meta")
                for _, row in bajo_meta.iterrows():
                    st.markdown(f"  - **{row['vendedor']}** ({row['local']}): {row['cumpl_fact']:.0f}% de meta")

            st.divider()

            # Tabla incentivos
            display = incentivos[["vendedor", "local", "facturacion", "fact_proyectada",
                                 "cumpl_fact", "pares", "pares_proyectados", "cumpl_pares",
                                 "ticket_prom", "cumpl_ticket", "bonus", "status"]].copy()
            display.columns = ["Vendedor", "Local", "Fact. Real", "Fact. Proy.",
                             "% Meta Fact", "Pares", "Pares Proy.", "% Meta Pares",
                             "Ticket", "% Meta Ticket", "Bonus $", "Status"]

            st.dataframe(
                display.style.format({
                    "Fact. Real": "${:,.0f}",
                    "Fact. Proy.": "${:,.0f}",
                    "% Meta Fact": "{:.0f}%",
                    "Pares": "{:.0f}",
                    "Pares Proy.": "{:.0f}",
                    "% Meta Pares": "{:.0f}%",
                    "Ticket": "${:,.0f}",
                    "% Meta Ticket": "{:.0f}%",
                    "Bonus $": "${:,.0f}",
                }).applymap(
                    lambda v: "background-color: rgba(239,68,68,0.2)" if isinstance(v, str) and "🔴" in v
                    else ("background-color: rgba(52,211,153,0.2)" if isinstance(v, str) and "✅" in v else ""),
                    subset=["Status"]
                ),
                use_container_width=True,
                height=min(600, 35 * len(display) + 38),
            )

            # Resumen bonus
            total_bonus = incentivos["bonus"].sum()
            n_con_bonus = len(incentivos[incentivos["bonus"] > 0])
            st.metric("Total bonus proyectado", formato_moneda(total_bonus),
                     delta=f"{n_con_bonus} vendedores con bonus")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB: SIMULADOR
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_simul:
        st.subheader("🧮 Simulador de bonus")
        st.caption("¿Si un vendedor vende X pares más, cuánto cobra de bonus?")

        col1, col2 = st.columns(2)
        with col1:
            # Seleccionar vendedor
            if not ranking.empty:
                vendedor_opts = ranking[["viajante", "vendedor"]].drop_duplicates()
                vendedor_sel = st.selectbox(
                    "Vendedor",
                    vendedor_opts["viajante"].tolist(),
                    format_func=lambda x: vendedor_opts[vendedor_opts["viajante"] == x]["vendedor"].iloc[0]
                )

                # Datos actuales del vendedor en el mes
                hoy = date.today()
                inicio_mes = hoy.replace(day=1)
                df_mes = load_ventas_periodo(inicio_mes.isoformat(), (hoy + timedelta(days=1)).isoformat())
                vend_data = df_mes[df_mes["viajante"] == vendedor_sel]
                vend_rank = calcular_ranking(vend_data)

                if not vend_rank.empty:
                    fact_actual = vend_rank["facturacion"].iloc[0]
                    pares_actual = int(vend_rank["pares"].iloc[0])
                    ticket_actual = vend_rank["ticket_prom"].iloc[0]
                else:
                    fact_actual = 0
                    pares_actual = 0
                    ticket_actual = 0

                st.metric("Facturación actual (mes)", formato_moneda(fact_actual))
                st.metric("Pares actual (mes)", f"{pares_actual:,}")

        with col2:
            pares_extra = st.number_input("Pares adicionales", value=100, step=10)
            ticket_sim = st.number_input("Ticket promedio estimado ($)",
                                        value=int(ticket_actual) if ticket_actual > 0 else 30000,
                                        step=5000)

            fact_extra = pares_extra * ticket_sim
            fact_simulada = fact_actual + fact_extra

            # Proyectar al mes
            dias_transcurridos = hoy.day
            dias_mes_total = (inicio_mes + relativedelta(months=1) - timedelta(days=1)).day
            dias_restantes = dias_mes_total - dias_transcurridos
            # Si los pares extra se venden en los días restantes
            fact_proyectada = fact_actual / max(dias_transcurridos, 1) * dias_mes_total + fact_extra

            excedente = max(0, fact_proyectada - meta_facturacion)
            bonus = excedente * pct_bonus / 100

            st.divider()
            st.metric("Facturación proyectada", formato_moneda(fact_proyectada))
            st.metric("Excedente sobre meta", formato_moneda(excedente))
            st.metric("💰 Bonus estimado", formato_moneda(bonus),
                     delta=f"+{pares_extra} pares a ${ticket_sim:,.0f}")

            if fact_proyectada < meta_facturacion:
                faltante = meta_facturacion - fact_proyectada
                pares_faltantes = faltante / ticket_sim if ticket_sim > 0 else 0
                st.warning(f"Faltan {formato_moneda(faltante)} para llegar a la meta "
                          f"(~{pares_faltantes:.0f} pares más)")


# ============================================================================
# MÓDULO 1: NÓMINA Y SUELDOS
# ============================================================================

def render_nomina():
    st.header("💰 Nómina y Sueldos")

    df_emp = load_empleados()
    df_sueldos = load_sueldos_mensual(meses=12)

    if df_emp.empty:
        st.warning("Sin datos de empleados. Verificá la conexión a SQL Server.")
        return

    activos = _get_activos(df_emp)
    if activos.empty:
        st.warning("Sin empleados activos.")
        return

    tab_lista, tab_sueldos, tab_alertas, tab_costo = st.tabs([
        "👥 Empleados", "📊 Sueldos", "🔔 Alertas", "💵 Costo laboral"
    ])

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB: LISTA EMPLEADOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_lista:
        st.subheader(f"Empleados activos: {len(activos)}")

        hoy = date.today()
        activos_display = activos.copy()

        # Calcular antigüedad
        activos_display["antiguedad"] = activos_display["fecha_ingreso"].apply(
            lambda fi: f"{(hoy - fi.date()).days // 365}a {((hoy - fi.date()).days % 365) // 30}m"
            if pd.notna(fi) else "?"
        )

        # Calcular edad
        activos_display["edad"] = activos_display["fecha_nacimiento"].apply(
            lambda fn: f"{(hoy - fn.date()).days // 365}" if pd.notna(fn) else "?"
        )

        activos_display["local"] = activos_display["zona"].apply(dep_nombre)

        display = activos_display[["numero", "denominacion", "local", "antiguedad", "edad",
                                   "cuil", "fecha_ingreso"]].copy()
        display.columns = ["#", "Nombre", "Local", "Antigüedad", "Edad", "CUIL", "Ingreso"]
        display = display.sort_values("Nombre")

        st.dataframe(display, use_container_width=True,
                    height=min(600, 35 * len(display) + 38))

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB: SUELDOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_sueldos:
        if df_sueldos.empty:
            st.warning("Sin datos de sueldos.")
        else:
            # Total bruto por mes
            brutos = df_sueldos[df_sueldos["codigo_movimiento"].isin(COD_SUELDO_BRUTO)].copy()
            brutos["mes"] = pd.to_datetime(brutos["fecha_contable"]).dt.to_period("M").astype(str)
            mensual = brutos.groupby("mes")["importe"].sum().reset_index()
            mensual.columns = ["Mes", "Total Bruto"]

            import plotly.express as px
            fig = px.bar(
                mensual, x="Mes", y="Total Bruto",
                labels={"Total Bruto": "Sueldo Bruto Total ($)"},
                color_discrete_sequence=["#6366f1"],
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Comparativo vs IPC
            st.subheader("Sueldo bruto vs Inflación (IPC)")
            if len(mensual) >= 2:
                mensual_sorted = mensual.sort_values("Mes")
                mensual_sorted["Var. Sueldo %"] = mensual_sorted["Total Bruto"].pct_change() * 100
                mensual_sorted["IPC %"] = mensual_sorted["Mes"].map(IPC_MENSUAL)

                fig2 = px.line(
                    mensual_sorted, x="Mes",
                    y=["Var. Sueldo %", "IPC %"],
                    markers=True,
                    labels={"value": "%", "variable": ""},
                )
                fig2.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", y=-0.2),
                )
                st.plotly_chart(fig2, use_container_width=True)

            # Historial por empleado
            st.subheader("Historial por empleado")
            emp_sel = st.selectbox(
                "Empleado",
                activos["numero"].tolist(),
                format_func=lambda x: activos[activos["numero"] == x]["denominacion"].iloc[0]
            )

            hist = df_sueldos[df_sueldos["numero_cuenta"] == emp_sel].copy()
            if hist.empty:
                st.info("Sin movimientos de sueldo para este empleado.")
            else:
                hist["fecha"] = pd.to_datetime(hist["fecha_contable"]).dt.strftime("%Y-%m-%d")
                hist_display = hist[["fecha", "codigo_movimiento", "importe", "operacion"]].copy()
                hist_display.columns = ["Fecha", "Código", "Importe", "Op"]
                st.dataframe(
                    hist_display.style.format({"Importe": "${:,.0f}"}),
                    use_container_width=True,
                )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB: ALERTAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_alertas:
        hoy = date.today()

        # Aniversarios próximos 30 días
        st.subheader("🎂 Aniversarios de ingreso (próximos 30 días)")
        aniv = activos[activos["fecha_ingreso"].notna()].copy()
        if not aniv.empty:
            aniv["aniv_este_anio"] = aniv["fecha_ingreso"].apply(
                lambda fi: fi.replace(year=hoy.year).date() if pd.notna(fi) else None
            )
            aniv["dias_para_aniv"] = aniv["aniv_este_anio"].apply(
                lambda a: (a - hoy).days if a else 999
            )
            # Si ya pasó, calcular para el año que viene
            aniv.loc[aniv["dias_para_aniv"] < 0, "aniv_este_anio"] = aniv.loc[
                aniv["dias_para_aniv"] < 0, "fecha_ingreso"
            ].apply(lambda fi: fi.replace(year=hoy.year + 1).date())
            aniv["dias_para_aniv"] = aniv["aniv_este_anio"].apply(
                lambda a: (a - hoy).days if a else 999
            )

            prox_aniv = aniv[aniv["dias_para_aniv"].between(0, 30)].sort_values("dias_para_aniv")
            if not prox_aniv.empty:
                for _, row in prox_aniv.iterrows():
                    anios = hoy.year - row["fecha_ingreso"].year
                    st.markdown(
                        f"🎉 **{row['denominacion']}** — "
                        f"{row['aniv_este_anio'].strftime('%d/%m')} "
                        f"(cumple **{anios} años** en la empresa, "
                        f"en {int(row['dias_para_aniv'])} días)"
                    )
            else:
                st.info("Sin aniversarios en los próximos 30 días.")

        # Cumpleaños próximos 30 días
        st.subheader("🎂 Cumpleaños (próximos 30 días)")
        cumple = activos[activos["fecha_nacimiento"].notna()].copy()
        if not cumple.empty:
            cumple["cumple_este_anio"] = cumple["fecha_nacimiento"].apply(
                lambda fn: fn.replace(year=hoy.year).date() if pd.notna(fn) else None
            )
            cumple["dias_para_cumple"] = cumple["cumple_este_anio"].apply(
                lambda c: (c - hoy).days if c else 999
            )
            cumple.loc[cumple["dias_para_cumple"] < 0, "cumple_este_anio"] = cumple.loc[
                cumple["dias_para_cumple"] < 0, "fecha_nacimiento"
            ].apply(lambda fn: fn.replace(year=hoy.year + 1).date())
            cumple["dias_para_cumple"] = cumple["cumple_este_anio"].apply(
                lambda c: (c - hoy).days if c else 999
            )

            prox_cumple = cumple[cumple["dias_para_cumple"].between(0, 30)].sort_values("dias_para_cumple")
            if not prox_cumple.empty:
                for _, row in prox_cumple.iterrows():
                    edad = hoy.year - row["fecha_nacimiento"].year
                    st.markdown(
                        f"🎂 **{row['denominacion']}** — "
                        f"{row['cumple_este_anio'].strftime('%d/%m')} "
                        f"(cumple **{edad} años**, "
                        f"en {int(row['dias_para_cumple'])} días)"
                    )
            else:
                st.info("Sin cumpleaños en los próximos 30 días.")

        # Sin pago último mes
        st.subheader("⚠️ Empleados sin pago en el último mes")
        if not df_sueldos.empty:
            ultimo_mes = (hoy - timedelta(days=30))
            recientes = df_sueldos[
                (pd.to_datetime(df_sueldos["fecha_contable"]) >= pd.Timestamp(ultimo_mes)) &
                (df_sueldos["codigo_movimiento"].isin(COD_SUELDO_BRUTO))
            ]
            con_pago = set(recientes["numero_cuenta"].unique())
            sin_pago = activos[~activos["numero"].isin(con_pago)]

            if not sin_pago.empty:
                st.warning(f"{len(sin_pago)} empleados activos sin registro de pago en los últimos 30 días")
                for _, row in sin_pago.iterrows():
                    st.markdown(f"  - #{int(row['numero'])} **{row['denominacion']}**")
            else:
                st.success("Todos los empleados tienen pagos registrados.")
        else:
            st.info("Sin datos de sueldos para verificar.")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB: COSTO LABORAL POR LOCAL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_costo:
        st.subheader("Costo laboral por local")

        if df_sueldos.empty:
            st.warning("Sin datos de sueldos.")
        else:
            # Sueldos por zona (zona del empleado = depósito = local)
            brutos = df_sueldos[df_sueldos["codigo_movimiento"].isin(COD_SUELDO_BRUTO)].copy()
            brutos = brutos.merge(
                activos[["numero", "zona"]],
                left_on="numero_cuenta", right_on="numero", how="left"
            )
            brutos["mes"] = pd.to_datetime(brutos["fecha_contable"]).dt.to_period("M").astype(str)

            # Último mes con datos
            ultimo_mes = brutos["mes"].max()
            brutos_ult = brutos[brutos["mes"] == ultimo_mes]

            costo_local = brutos_ult.groupby("zona").agg(
                total=("importe", "sum"),
                empleados=("numero_cuenta", "nunique"),
            ).reset_index()
            costo_local["local"] = costo_local["zona"].apply(dep_nombre)
            costo_local["costo_promedio"] = (costo_local["total"] / costo_local["empleados"]).round(0)
            costo_local = costo_local.sort_values("total", ascending=False)

            st.caption(f"Datos de: {ultimo_mes}")

            import plotly.express as px
            fig = px.bar(
                costo_local, x="local", y="total", text="empleados",
                labels={"total": "Costo Laboral ($)", "local": "Local", "empleados": "Empleados"},
                color_discrete_sequence=["#a78bfa"],
            )
            fig.update_traces(texttemplate="%{text} emp", textposition="outside")
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Tabla
            display = costo_local[["local", "empleados", "total", "costo_promedio"]].copy()
            display.columns = ["Local", "Empleados", "Costo Total", "Costo Promedio"]
            st.dataframe(
                display.style.format({"Costo Total": "${:,.0f}", "Costo Promedio": "${:,.0f}"}),
                use_container_width=True,
            )


# ============================================================================
# MÓDULO 3: RECLUTAMIENTO
# ============================================================================

PIPELINE_ESTADOS = ["recibido", "entrevista", "prueba", "oferta", "contratado", "rechazado"]
PIPELINE_COLORES = {
    "recibido": "#94a3b8",
    "entrevista": "#6366f1",
    "prueba": "#a78bfa",
    "oferta": "#fbbf24",
    "contratado": "#34d399",
    "rechazado": "#f87171",
}
FUENTES = ["WhatsApp", "Referido", "Aviso local", "Instagram", "Walk-in", "Otra"]


def _ensure_reclutamiento_tables():
    """Crea tablas de reclutamiento en omicronvt si no existen."""
    try:
        conn = _connect(CONN_ANALITICA)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return False
    c = conn.cursor()
    try:
        c.execute("""
        IF OBJECT_ID('omicronvt.dbo.rrhh_vacantes', 'U') IS NULL
        CREATE TABLE omicronvt.dbo.rrhh_vacantes (
            id              INT IDENTITY(1,1) PRIMARY KEY,
            puesto          NVARCHAR(100),
            local_dep       INT,
            estado          NVARCHAR(20) DEFAULT 'abierta',
            fecha_apertura  DATE DEFAULT GETDATE(),
            fecha_cierre    DATE NULL,
            requisitos      NVARCHAR(500),
            salario_ofrecido DECIMAL(18,2) NULL,
            notas           NVARCHAR(500)
        )
        """)
        c.execute("""
        IF OBJECT_ID('omicronvt.dbo.rrhh_candidatos', 'U') IS NULL
        CREATE TABLE omicronvt.dbo.rrhh_candidatos (
            id              INT IDENTITY(1,1) PRIMARY KEY,
            vacante_id      INT,
            nombre          NVARCHAR(150),
            telefono        NVARCHAR(30),
            email           NVARCHAR(100),
            cv_recibido     DATE DEFAULT GETDATE(),
            estado          NVARCHAR(20) DEFAULT 'recibido',
            notas           NVARCHAR(500),
            fuente          NVARCHAR(50),
            fecha_update    DATETIME DEFAULT GETDATE()
        )
        """)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error creando tablas: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return False


def render_reclutamiento():
    st.header("📋 Reclutamiento")

    _ensure_reclutamiento_tables()

    tab_pipeline, tab_vacantes, tab_candidatos, tab_metricas = st.tabs([
        "🔄 Pipeline", "📄 Vacantes", "👤 Candidatos", "📊 Métricas"
    ])

    # ── Cargar datos ──
    vacantes = query_df("SELECT * FROM omicronvt.dbo.rrhh_vacantes ORDER BY fecha_apertura DESC",
                       CONN_ANALITICA)
    candidatos = query_df("SELECT * FROM omicronvt.dbo.rrhh_candidatos ORDER BY cv_recibido DESC",
                         CONN_ANALITICA)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB: PIPELINE VISUAL
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_pipeline:
        st.subheader("Pipeline de Reclutamiento")

        if candidatos.empty:
            st.info("Sin candidatos cargados. Agregá candidatos en la pestaña 'Candidatos'.")
        else:
            # Filtro por vacante
            if not vacantes.empty:
                vac_opts = [0] + vacantes["id"].tolist()
                vac_sel = st.selectbox(
                    "Filtrar por vacante",
                    vac_opts,
                    format_func=lambda x: "Todas" if x == 0 else
                        f"{vacantes[vacantes['id']==x]['puesto'].iloc[0]} — {dep_nombre(vacantes[vacantes['id']==x]['local_dep'].iloc[0])}"
                )
                if vac_sel > 0:
                    candidatos_filt = candidatos[candidatos["vacante_id"] == vac_sel]
                else:
                    candidatos_filt = candidatos
            else:
                candidatos_filt = candidatos

            # Pipeline columns
            cols = st.columns(len(PIPELINE_ESTADOS))
            for i, estado in enumerate(PIPELINE_ESTADOS):
                with cols[i]:
                    en_estado = candidatos_filt[candidatos_filt["estado"] == estado]
                    color = PIPELINE_COLORES[estado]
                    st.markdown(
                        f"<div style='background:{color}20; border-left:4px solid {color}; "
                        f"padding:8px; border-radius:4px; margin-bottom:8px;'>"
                        f"<b>{estado.upper()}</b> ({len(en_estado)})</div>",
                        unsafe_allow_html=True
                    )
                    for _, cand in en_estado.iterrows():
                        st.markdown(
                            f"**{cand['nombre']}**  \n"
                            f"📱 {cand['telefono'] or '?'}  \n"
                            f"📥 {cand['fuente'] or '?'}  \n"
                            f"_{cand['cv_recibido']}_"
                        )
                        # Mover estado
                        new_estado = st.selectbox(
                            "Mover a", PIPELINE_ESTADOS,
                            index=PIPELINE_ESTADOS.index(estado),
                            key=f"move_{cand['id']}",
                        )
                        if new_estado != estado:
                            exec_sql(
                                "UPDATE omicronvt.dbo.rrhh_candidatos SET estado=?, fecha_update=GETDATE() WHERE id=?",
                                (new_estado, int(cand["id"]))
                            )
                            st.rerun()
                        st.divider()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB: VACANTES
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_vacantes:
        st.subheader("Gestión de Vacantes")

        # Formulario nueva vacante
        with st.expander("➕ Nueva vacante", expanded=vacantes.empty):
            with st.form("nueva_vacante"):
                c1, c2 = st.columns(2)
                puesto = c1.text_input("Puesto")
                local = c2.selectbox("Local", list(DEPOSITOS.keys()), format_func=dep_nombre)
                requisitos = st.text_area("Requisitos")
                salario = st.number_input("Salario ofrecido ($)", value=0, step=100000)
                notas_vac = st.text_input("Notas")

                if st.form_submit_button("Crear vacante"):
                    if puesto:
                        exec_sql(
                            """INSERT INTO omicronvt.dbo.rrhh_vacantes
                            (puesto, local_dep, requisitos, salario_ofrecido, notas)
                            VALUES (?, ?, ?, ?, ?)""",
                            (puesto, int(local), requisitos, salario if salario > 0 else None, notas_vac)
                        )
                        st.success(f"Vacante '{puesto}' creada")
                        st.cache_data.clear()
                        st.rerun()

        # Lista vacantes
        if not vacantes.empty:
            for _, vac in vacantes.iterrows():
                estado_icon = "🟢" if vac["estado"] == "abierta" else "🔴"
                n_cand = len(candidatos[candidatos["vacante_id"] == vac["id"]]) if not candidatos.empty else 0
                with st.expander(f"{estado_icon} {vac['puesto']} — {dep_nombre(vac['local_dep'])} ({n_cand} candidatos)"):
                    st.markdown(f"**Apertura:** {vac['fecha_apertura']}")
                    if vac["requisitos"]:
                        st.markdown(f"**Requisitos:** {vac['requisitos']}")
                    if vac["salario_ofrecido"]:
                        st.markdown(f"**Salario:** ${float(vac['salario_ofrecido']):,.0f}")
                    if vac["notas"]:
                        st.markdown(f"**Notas:** {vac['notas']}")

                    c1, c2 = st.columns(2)
                    nuevo_estado = c1.selectbox(
                        "Estado", ["abierta", "cerrada", "pausada"],
                        index=["abierta", "cerrada", "pausada"].index(vac["estado"])
                        if vac["estado"] in ["abierta", "cerrada", "pausada"] else 0,
                        key=f"vac_estado_{vac['id']}"
                    )
                    if nuevo_estado != vac["estado"]:
                        fecha_cierre = "GETDATE()" if nuevo_estado == "cerrada" else "NULL"
                        exec_sql(
                            f"UPDATE omicronvt.dbo.rrhh_vacantes SET estado=?, fecha_cierre={fecha_cierre} WHERE id=?",
                            (nuevo_estado, int(vac["id"]))
                        )
                        st.rerun()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB: CANDIDATOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_candidatos:
        st.subheader("Cargar candidato")

        with st.form("nuevo_candidato"):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre completo")
            telefono = c2.text_input("Teléfono")

            c3, c4 = st.columns(2)
            email = c3.text_input("Email (opcional)")
            fuente = c4.selectbox("Fuente", FUENTES)

            # Vacante
            if not vacantes.empty:
                vac_abiertas = vacantes[vacantes["estado"] == "abierta"]
                if not vac_abiertas.empty:
                    vacante_id = st.selectbox(
                        "Vacante",
                        vac_abiertas["id"].tolist(),
                        format_func=lambda x: f"{vac_abiertas[vac_abiertas['id']==x]['puesto'].iloc[0]} — {dep_nombre(vac_abiertas[vac_abiertas['id']==x]['local_dep'].iloc[0])}"
                    )
                else:
                    vacante_id = None
                    st.info("No hay vacantes abiertas.")
            else:
                vacante_id = None
                st.info("Crea una vacante primero.")

            notas_cand = st.text_area("Notas")

            if st.form_submit_button("Agregar candidato"):
                if nombre and vacante_id:
                    exec_sql(
                        """INSERT INTO omicronvt.dbo.rrhh_candidatos
                        (vacante_id, nombre, telefono, email, fuente, notas)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                        (int(vacante_id), nombre, telefono, email, fuente, notas_cand)
                    )
                    st.success(f"Candidato '{nombre}' agregado")
                    st.cache_data.clear()
                    st.rerun()
                elif not nombre:
                    st.warning("Ingresá el nombre del candidato.")

        # Lista candidatos
        if not candidatos.empty:
            st.divider()
            st.subheader("Candidatos registrados")
            display = candidatos[["nombre", "telefono", "email", "fuente", "estado",
                                 "cv_recibido", "vacante_id"]].copy()
            if not vacantes.empty:
                display = display.merge(
                    vacantes[["id", "puesto"]], left_on="vacante_id", right_on="id", how="left"
                )
                display = display.drop(columns=["id", "vacante_id"])
                display = display.rename(columns={"puesto": "Vacante"})
            display.columns = [c.replace("_", " ").title() for c in display.columns]
            st.dataframe(display, use_container_width=True)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TAB: MÉTRICAS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    with tab_metricas:
        st.subheader("Métricas de reclutamiento")

        if candidatos.empty or vacantes.empty:
            st.info("Cargá vacantes y candidatos para ver métricas.")
        else:
            # Días promedio para cubrir
            cerradas = vacantes[vacantes["estado"] == "cerrada"]
            if not cerradas.empty and "fecha_cierre" in cerradas.columns:
                cerradas_valid = cerradas[cerradas["fecha_cierre"].notna()]
                if not cerradas_valid.empty:
                    dias_promedio = (
                        pd.to_datetime(cerradas_valid["fecha_cierre"]) -
                        pd.to_datetime(cerradas_valid["fecha_apertura"])
                    ).dt.days.mean()
                    st.metric("Días promedio para cubrir vacante", f"{dias_promedio:.0f}")

            # Tasa de conversión por etapa
            st.subheader("Conversión por etapa")
            total_cand = len(candidatos)
            for estado in PIPELINE_ESTADOS:
                n = len(candidatos[candidatos["estado"] == estado])
                pct = n / total_cand * 100 if total_cand > 0 else 0
                color = PIPELINE_COLORES[estado]
                st.markdown(
                    f"<div style='display:flex; align-items:center; margin:4px 0;'>"
                    f"<div style='width:120px; font-weight:bold;'>{estado}</div>"
                    f"<div style='flex:1; background:#1e1e2e; border-radius:4px; height:24px;'>"
                    f"<div style='width:{pct}%; background:{color}; height:24px; border-radius:4px; "
                    f"display:flex; align-items:center; padding-left:8px; color:white; font-size:12px;'>"
                    f"{n} ({pct:.0f}%)</div></div></div>",
                    unsafe_allow_html=True
                )

            # Por fuente
            st.subheader("Candidatos por fuente")
            fuentes_count = candidatos["fuente"].value_counts()
            if not fuentes_count.empty:
                import plotly.express as px
                fig = px.pie(
                    values=fuentes_count.values,
                    names=fuentes_count.index,
                    hole=0.4,
                    color_discrete_sequence=["#6366f1", "#a78bfa", "#34d399", "#fbbf24", "#f87171", "#94a3b8"],
                )
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# MÓDULO 4: OVERVIEW EJECUTIVO
# ============================================================================

def render_overview():
    st.header("📊 Overview Ejecutivo")

    df_emp = load_empleados()
    df_sueldos = load_sueldos_mensual(meses=12)

    if df_emp.empty:
        st.warning("Sin datos de empleados. Verificá la conexión a SQL Server.")
        return

    activos = _get_activos(df_emp)
    bajas = df_emp[df_emp["motivo_baja"] == "B"].copy() if "motivo_baja" in df_emp.columns else pd.DataFrame()

    hoy = date.today()

    # ── KPIs principales ──
    c1, c2, c3, c4, c5 = st.columns(5)

    # Headcount
    c1.metric("Headcount", len(activos))

    # Headcount por local
    headcount_local = activos["zona"].apply(dep_nombre).value_counts()

    # Antigüedad promedio
    con_ingreso = activos[activos["fecha_ingreso"].notna()]
    if not con_ingreso.empty:
        antig_dias = (pd.Timestamp(hoy) - pd.to_datetime(con_ingreso["fecha_ingreso"])).dt.days.mean()
        c2.metric("Antigüedad promedio", f"{antig_dias/365:.1f} años")
    else:
        c2.metric("Antigüedad promedio", "?")

    # Costo laboral último mes
    costo_total = 0
    if not df_sueldos.empty and "codigo_movimiento" in df_sueldos.columns:
        brutos = df_sueldos[df_sueldos["codigo_movimiento"].isin(COD_SUELDO_BRUTO)]
        if not brutos.empty:
            ultimo_mes = pd.to_datetime(brutos["fecha_contable"]).dt.to_period("M").max()
            brutos_ult = brutos[pd.to_datetime(brutos["fecha_contable"]).dt.to_period("M") == ultimo_mes]
            costo_total = float(brutos_ult["importe"].sum())
            c3.metric("Costo laboral (último mes)", formato_moneda(costo_total))

    # Ventas último mes (para ratio)
    df_ventas_30d = load_ventas_vendedor(30)
    if not df_ventas_30d.empty:
        fact_30d = df_ventas_30d.apply(
            lambda r: r["total_item"] if r["operacion"] == "+" else -r["total_item"], axis=1
        ).sum()

        if costo_total > 0:
            ratio = float(costo_total) / float(fact_30d) * 100 if fact_30d > 0 else 0
            c4.metric("Costo/Facturación", f"{ratio:.1f}%")

            # Ratio vendedor/facturación
            ratio_prod = float(fact_30d) / float(costo_total) if costo_total > 0 else 0
            c5.metric("$ ventas / $ sueldo", f"{ratio_prod:.1f}x")

    st.divider()

    # ── Headcount por local ──
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Headcount por local")
        import plotly.express as px
        fig = px.bar(
            x=headcount_local.index, y=headcount_local.values,
            labels={"x": "Local", "y": "Empleados"},
            color_discrete_sequence=["#6366f1"],
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Turnover últimos 12 meses")
        # Altas = empleados con fecha_ingreso en últimos 12m
        hace_12m = hoy - timedelta(days=365)
        altas = len(con_ingreso[pd.to_datetime(con_ingreso["fecha_ingreso"]).dt.date >= hace_12m])

        # Bajas = empleados con fecha_baja en últimos 12m
        bajas_con_fecha = bajas[bajas["fecha_baja"].notna()]
        if not bajas_con_fecha.empty:
            bajas_12m = len(bajas_con_fecha[pd.to_datetime(bajas_con_fecha["fecha_baja"]).dt.date >= hace_12m])
        else:
            bajas_12m = 0

        turnover = bajas_12m / len(activos) * 100 if len(activos) > 0 else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Altas", altas)
        m2.metric("Bajas", bajas_12m)
        m3.metric("Turnover", f"{turnover:.0f}%")

        # Timeline simple
        st.caption("Nota: muchos empleados no tienen fecha_ingreso cargada en el ERP.")


# ============================================================================
# MAIN
# ============================================================================

def main():
    st.title("👥 RRHH — Calzalindo")

    tab_prod, tab_nomina, tab_reclu, tab_overview = st.tabs([
        "📊 Productividad", "💰 Nómina", "📋 Reclutamiento", "📈 Overview"
    ])

    with tab_prod:
        render_productividad()

    with tab_nomina:
        render_nomina()

    with tab_reclu:
        render_reclutamiento()

    with tab_overview:
        render_overview()


if __name__ == "__main__":
    main()
