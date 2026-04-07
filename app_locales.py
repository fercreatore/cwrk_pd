# -*- coding: utf-8 -*-
"""
APP LOCALES — Modelo de rentabilidad y presupuesto de compra por local.
Vinculada a calzalindo_informes.

Fuentes:
- Ventas: msgestionC.dbo.ventas1 (deposito, codigo 1+3, neto=total_item/1.21)
- Gastos: msgestionC.dbo.co_movact (sector=deposito, cuentas 4/5)
- Sueldos: msgestion01.dbo.moviempl1 (cod_mov 8,10,30,31)
- Transferencias: msgestionC.dbo.t_sucursales_transferencias_mes_valorizadas
- NO usar ventas1_vendedor (solo 1/3 de la venta real)

Ejecutar: streamlit run app_locales.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import pyodbc
import config  # conexion SQL

st.set_page_config(page_title="Modelo Locales — H4/CLZ", layout="wide", page_icon="🏪")

DEPOSITOS = {
    0: 'Central', 2: 'Norte', 6: 'Cuore', 7: 'Eva Peron',
    8: 'Junin', 9: 'Tokyo Express', 4: 'Claudia',
    26: 'Suc 26', 28: 'Suc 28', 30: 'Suc 30', 31: 'Suc 31',
    32: 'Suc 32', 33: 'Suc 33', 35: 'Suc 35', 38: 'Suc 38', 39: 'Suc 39',
}

DEPS_ACTIVOS = [0, 2, 6, 7, 8, 26, 28, 30, 31, 32, 33, 35, 38, 39]


@st.cache_data(ttl=3600)
def get_ventas_por_local():
    """Ventas netas por deposito/mes desde msgestionC.dbo.ventas1"""
    conn = pyodbc.connect(config.get_conn_string(config.BD_COMPRAS))
    sql = """
        SELECT deposito, CONVERT(VARCHAR(7), fecha, 120) AS mes,
               SUM(CASE WHEN operacion='+' THEN total_item/1.21 WHEN operacion='-' THEN -total_item/1.21 END) AS venta_neta,
               SUM(CASE WHEN operacion='+' THEN precio_costo WHEN operacion='-' THEN -precio_costo END) AS costo,
               SUM(CASE WHEN operacion='+' THEN total_item/1.21 WHEN operacion='-' THEN -total_item/1.21 END)
               - SUM(CASE WHEN operacion='+' THEN precio_costo WHEN operacion='-' THEN -precio_costo END) AS margen,
               SUM(CASE WHEN operacion='+' THEN cantidad WHEN operacion='-' THEN -cantidad END) AS pares
        FROM ventas1
        WHERE fecha >= '2025-01-01' AND codigo IN (1,3)
        GROUP BY deposito, CONVERT(VARCHAR(7), fecha, 120)
        ORDER BY deposito, mes
    """
    df = pd.read_sql(sql, conn)
    df['pct_margen'] = np.where(df['venta_neta'] > 0, df['margen'] / df['venta_neta'] * 100, 0)
    return df


@st.cache_data(ttl=3600)
def get_transferencias():
    """Transferencias entre locales (pares y costo CER) por sucursal/mes"""
    conn = pyodbc.connect(config.get_conn_string(config.BD_COMPRAS))
    sql = """
        SELECT sucursal, mes, entrada, entrada_costo_cer, salida, salida_costo_cer,
               neto, neto_costo_cer
        FROM t_sucursales_transferencias_mes_valorizadas
        WHERE mes >= '2025-01' AND mes <= '2026-12'
        ORDER BY sucursal, mes
    """
    df = pd.read_sql(sql, conn)
    df['sucursal'] = df['sucursal'].astype(int)
    return df


@st.cache_data(ttl=3600)
def get_gastos_contables():
    """Gastos de co_movact por sector (deposito) y mes"""
    conn = pyodbc.connect(config.get_conn_string(config.BD_COMPRAS))
    sql = """
        SELECT sector, CONVERT(VARCHAR(7), fecha, 120) AS mes,
               SUM(debe) - SUM(haber) AS gasto_neto
        FROM co_movact
        WHERE fecha >= '2025-01-01' AND LEFT(cuenta, 1) IN ('4','5')
        GROUP BY sector, CONVERT(VARCHAR(7), fecha, 120)
        ORDER BY sector, mes
    """
    df = pd.read_sql(sql, conn)
    return df


@st.cache_data(ttl=3600)
def get_sueldos_por_deposito():
    """Sueldos reales por deposito/mes (cruzando viajantes que venden en cada deposito)"""
    conn = pyodbc.connect(config.get_conn_string(config.BD_COMPRAS))
    # Primero mapear viajante -> deposito principal (donde mas vende)
    sql_map = """
        SELECT viajante, deposito,
               ROW_NUMBER() OVER (PARTITION BY viajante ORDER BY SUM(CASE WHEN operacion='+' THEN total_item ELSE 0 END) DESC) AS rn
        FROM ventas1
        WHERE fecha >= '2025-10-01' AND codigo IN (1,3) AND viajante > 0
        GROUP BY viajante, deposito
    """
    # Sueldos
    sql_sueldos = """
        SELECT m.numero_cuenta AS viajante,
               CONVERT(VARCHAR(7), m.fecha_contable, 120) AS mes,
               SUM(m.importe) AS haberes
        FROM msgestion01.dbo.moviempl1 m
        WHERE m.codigo_movimiento IN (8, 10, 30, 31)
          AND m.fecha_contable >= '2025-01-01'
        GROUP BY m.numero_cuenta, CONVERT(VARCHAR(7), m.fecha_contable, 120)
    """
    try:
        df_map = pd.read_sql(sql_map, conn)
        df_map = df_map[df_map['rn'] == 1][['viajante', 'deposito']]
        df_sueldos = pd.read_sql(sql_sueldos, conn)
        df = df_sueldos.merge(df_map, on='viajante', how='inner')
        result = df.groupby(['deposito', 'mes']).agg(
            total_sueldos=('haberes', 'sum'),
            empleados=('viajante', 'nunique')
        ).reset_index()
        return result
    except Exception as e:
        st.warning(f"Error sueldos: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_piramide_precios(deposito):
    """Piramide de precios para un deposito"""
    conn = pyodbc.connect(config.get_conn_string(config.BD_COMPRAS))
    sql = f"""
        SELECT
          CASE
            WHEN total_item/1.21 < 20000 THEN '1-Entrada (<$20k)'
            WHEN total_item/1.21 < 40000 THEN '2-Medio ($20-40k)'
            WHEN total_item/1.21 < 70000 THEN '3-Medio-Alto ($40-70k)'
            WHEN total_item/1.21 < 120000 THEN '4-Premium ($70-120k)'
            ELSE '5-Lujo (>$120k)'
          END AS segmento,
          SUM(CASE WHEN operacion='+' THEN 1 ELSE -1 END) AS pares,
          SUM(CASE WHEN operacion='+' THEN total_item/1.21 ELSE -total_item/1.21 END) AS venta_neta,
          SUM(CASE WHEN operacion='+' THEN total_item/1.21-precio_costo ELSE -(total_item/1.21-precio_costo) END) AS margen
        FROM ventas1
        WHERE deposito = {deposito} AND fecha >= '2025-10-01' AND codigo IN (1,3)
        GROUP BY
          CASE
            WHEN total_item/1.21 < 20000 THEN '1-Entrada (<$20k)'
            WHEN total_item/1.21 < 40000 THEN '2-Medio ($20-40k)'
            WHEN total_item/1.21 < 70000 THEN '3-Medio-Alto ($40-70k)'
            WHEN total_item/1.21 < 120000 THEN '4-Premium ($70-120k)'
            ELSE '5-Lujo (>$120k)'
          END
        ORDER BY segmento
    """
    df = pd.read_sql(sql, conn)
    df['pct_margen'] = np.where(df['venta_neta'] > 0, df['margen'] / df['venta_neta'] * 100, 0)
    df['pct_venta'] = df['venta_neta'] / df['venta_neta'].sum() * 100
    df['pct_pares'] = df['pares'] / df['pares'].sum() * 100
    return df


@st.cache_data(ttl=3600)
def get_marcas_por_deposito(deposito):
    """Top marcas para un deposito"""
    conn = pyodbc.connect(config.get_conn_string(config.BD_COMPRAS))
    sql = f"""
        SELECT TOP 20 a.marca, m.descripcion AS marca_nombre,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END) AS pares,
               SUM(CASE WHEN v.operacion='+' THEN v.total_item/1.21 WHEN v.operacion='-' THEN -v.total_item/1.21 END) AS venta_neta,
               SUM(CASE WHEN v.operacion='+' THEN v.total_item/1.21 WHEN v.operacion='-' THEN -v.total_item/1.21 END)
               - SUM(CASE WHEN v.operacion='+' THEN v.precio_costo WHEN v.operacion='-' THEN -v.precio_costo END) AS margen,
               CASE WHEN SUM(CASE WHEN v.operacion='+' THEN v.total_item/1.21 WHEN v.operacion='-' THEN -v.total_item/1.21 END) > 0
                    THEN (SUM(CASE WHEN v.operacion='+' THEN v.total_item/1.21 WHEN v.operacion='-' THEN -v.total_item/1.21 END)
                         - SUM(CASE WHEN v.operacion='+' THEN v.precio_costo WHEN v.operacion='-' THEN -v.precio_costo END))
                         * 100.0 / SUM(CASE WHEN v.operacion='+' THEN v.total_item/1.21 WHEN v.operacion='-' THEN -v.total_item/1.21 END)
                    ELSE 0 END AS pct_margen
        FROM ventas1 v
        JOIN articulo a ON a.codigo = v.articulo
        JOIN marcas m ON m.codigo = a.marca
        WHERE v.deposito = {deposito} AND v.fecha >= '2025-10-01' AND v.codigo IN (1,3)
          AND a.marca NOT IN (1316, 1317, 1158, 436)
        GROUP BY a.marca, m.descripcion
        HAVING SUM(CASE WHEN v.operacion='+' THEN v.total_item/1.21 WHEN v.operacion='-' THEN -v.total_item/1.21 END) > 100000
        ORDER BY venta_neta DESC
    """
    try:
        return pd.read_sql(sql, conn)
    except:
        return pd.DataFrame()


def calcular_presupuesto_optimo(df_ventas_local):
    """
    Modelo de presupuesto optimo de compra por local.
    Presupuesto = CMV promedio mensual * factor_estacional * factor_crecimiento
    CMV = costo de mercaderia vendida = lo que necesitas reponer
    """
    if df_ventas_local.empty:
        return pd.DataFrame()

    df = df_ventas_local.copy()
    df['mes_num'] = pd.to_datetime(df['mes'] + '-01')
    df['month'] = df['mes_num'].dt.month

    # CMV promedio ultimos 12 meses
    cmv_prom = df['costo'].mean()

    # Factor estacional por mes (basado en data real)
    estacional = df.groupby('month')['costo'].mean()
    if cmv_prom > 0:
        factor_est = estacional / cmv_prom
    else:
        factor_est = pd.Series([1.0] * 12, index=range(1, 13))

    # Presupuesto optimo = CMV promedio * factor estacional
    presupuesto = pd.DataFrame({
        'mes': range(1, 13),
        'mes_nombre': ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                       'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
        'cmv_historico': [estacional.get(m, cmv_prom) for m in range(1, 13)],
        'factor_estacional': [factor_est.get(m, 1.0) for m in range(1, 13)],
        'presupuesto_compra': [cmv_prom * factor_est.get(m, 1.0) for m in range(1, 13)],
    })
    presupuesto['presupuesto_pares'] = presupuesto['presupuesto_compra'] / (cmv_prom / df['pares'].mean()) if df['pares'].mean() > 0 else 0

    return presupuesto


def formato_m(valor):
    """Formato millones"""
    if abs(valor) >= 1e6:
        return f"${valor/1e6:.1f}M"
    elif abs(valor) >= 1e3:
        return f"${valor/1e3:.0f}k"
    return f"${valor:.0f}"


# ============================================================
# INTERFAZ
# ============================================================

st.title("🏪 Modelo de Locales — Rentabilidad y Presupuesto")
st.caption("Fuente: msgestionC.dbo.ventas1 (deposito, cod 1+3, neto sin IVA) | co_movact | moviempl1")

# Cargar datos
with st.spinner("Cargando datos..."):
    df_ventas = get_ventas_por_local()
    df_transfer = get_transferencias()
    df_gastos = get_gastos_contables()
    df_sueldos = get_sueldos_por_deposito()

# =============================================================
# TAB 1: RANKING DE LOCALES
# =============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Ranking Locales", "🏪 Detalle Local", "📦 Presupuesto Compra", "📈 Piramide & Marcas", "🔍 Control Stock"])

with tab1:
    st.header("Ranking de Locales")

    # Resumen por local
    deps_en_data = [d for d in DEPS_ACTIVOS if d in df_ventas['deposito'].values]
    resumen = []
    for dep in deps_en_data:
        dv = df_ventas[df_ventas['deposito'] == dep]
        nombre = DEPOSITOS.get(dep, f'Dep {dep}')
        vta_total = dv['venta_neta'].sum()
        margen_total = dv['margen'].sum()
        costo_total = dv['costo'].sum()
        pares_total = dv['pares'].sum()
        meses = len(dv)
        vta_prom = vta_total / meses if meses > 0 else 0
        margen_prom = margen_total / meses if meses > 0 else 0
        pct_mg = margen_total / vta_total * 100 if vta_total > 0 else 0

        # Sueldos
        ds = df_sueldos[df_sueldos['deposito'] == dep] if not df_sueldos.empty else pd.DataFrame()
        sueldos_total = ds['total_sueldos'].sum() if not ds.empty else 0
        sueldos_prom = sueldos_total / len(ds) if not ds.empty and len(ds) > 0 else 0

        # Gastos contables
        dg = df_gastos[df_gastos['sector'] == dep]
        gastos_total = dg['gasto_neto'].sum() if not dg.empty else 0
        gastos_prom = gastos_total / len(dg) if not dg.empty and len(dg) > 0 else 0

        resultado = margen_prom - sueldos_prom - gastos_prom
        gasto_personal_pct = sueldos_prom / vta_prom * 100 if vta_prom > 0 else 0

        resumen.append({
            'Local': nombre,
            'Deposito': dep,
            'Vta neta prom/mes': vta_prom,
            'Margen prom/mes': margen_prom,
            '%Margen': pct_mg,
            'Sueldos prom/mes': sueldos_prom,
            'Gastos prom/mes': gastos_prom,
            'Resultado prom/mes': resultado,
            '%Personal/Vta': gasto_personal_pct,
            'Pares prom/mes': pares_total / meses if meses > 0 else 0,
            'CMV prom/mes': costo_total / meses if meses > 0 else 0,
        })

    df_resumen = pd.DataFrame(resumen).sort_values('Vta neta prom/mes', ascending=False)

    # KPIs globales
    c1, c2, c3, c4 = st.columns(4)
    total_vta = df_resumen['Vta neta prom/mes'].sum()
    total_margen = df_resumen['Margen prom/mes'].sum()
    total_sueldos = df_resumen['Sueldos prom/mes'].sum()
    total_resultado = df_resumen['Resultado prom/mes'].sum()
    c1.metric("Venta neta total/mes", formato_m(total_vta))
    c2.metric("Margen total/mes", formato_m(total_margen))
    c3.metric("Sueldos total/mes", formato_m(total_sueldos))
    c4.metric("Resultado total/mes", formato_m(total_resultado),
              delta=f"{total_resultado/total_margen*100:.0f}% del margen" if total_margen > 0 else "")

    # Tabla ranking
    st.dataframe(
        df_resumen[['Local', 'Vta neta prom/mes', 'Margen prom/mes', '%Margen',
                     'Sueldos prom/mes', 'Gastos prom/mes', 'Resultado prom/mes',
                     '%Personal/Vta', 'Pares prom/mes', 'CMV prom/mes']].style.format({
            'Vta neta prom/mes': '${:,.0f}',
            'Margen prom/mes': '${:,.0f}',
            '%Margen': '{:.1f}%',
            'Sueldos prom/mes': '${:,.0f}',
            'Gastos prom/mes': '${:,.0f}',
            'Resultado prom/mes': '${:,.0f}',
            '%Personal/Vta': '{:.1f}%',
            'Pares prom/mes': '{:,.0f}',
            'CMV prom/mes': '${:,.0f}',
        }),
        use_container_width=True, hide_index=True
    )

    # Chart comparativo
    fig = px.bar(df_resumen, x='Local', y=['Margen prom/mes', 'Sueldos prom/mes', 'Gastos prom/mes'],
                 barmode='group', title='Margen vs Costos por Local (promedio mensual)')
    st.plotly_chart(fig, use_container_width=True)


with tab2:
    st.header("Detalle por Local")
    dep_sel = st.selectbox("Selecciona local", options=deps_en_data,
                           format_func=lambda x: DEPOSITOS.get(x, f'Dep {x}'))

    dv = df_ventas[df_ventas['deposito'] == dep_sel].copy()
    dv['mes_dt'] = pd.to_datetime(dv['mes'] + '-01')
    dv = dv.sort_values('mes_dt')

    if not dv.empty:
        st.subheader(f"{DEPOSITOS.get(dep_sel, dep_sel)} — Evolucion mensual")

        # Merge con sueldos y gastos
        ds = df_sueldos[df_sueldos['deposito'] == dep_sel] if not df_sueldos.empty else pd.DataFrame(columns=['mes', 'total_sueldos', 'empleados'])
        dg = df_gastos[df_gastos['sector'] == dep_sel]

        df_local = dv.merge(ds[['mes', 'total_sueldos', 'empleados']], on='mes', how='left')
        df_local = df_local.merge(dg[['mes', 'gasto_neto']], on='mes', how='left')
        df_local['total_sueldos'] = df_local['total_sueldos'].fillna(0)
        df_local['gasto_neto'] = df_local['gasto_neto'].fillna(0)
        df_local['empleados'] = df_local['empleados'].fillna(0)
        df_local['resultado'] = df_local['margen'] - df_local['total_sueldos'] - df_local['gasto_neto']

        # KPIs
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Venta prom/mes", formato_m(df_local['venta_neta'].mean()))
        c2.metric("Margen prom", f"{df_local['pct_margen'].mean():.1f}%")
        c3.metric("CMV prom/mes", formato_m(df_local['costo'].mean()))
        c4.metric("Sueldos prom/mes", formato_m(df_local['total_sueldos'].mean()))
        c5.metric("Resultado prom/mes", formato_m(df_local['resultado'].mean()))

        # Tabla
        st.dataframe(
            df_local[['mes', 'venta_neta', 'costo', 'margen', 'pct_margen', 'pares',
                       'total_sueldos', 'empleados', 'gasto_neto', 'resultado']].rename(columns={
                'venta_neta': 'Venta neta', 'costo': 'CMV', 'margen': 'Margen',
                'pct_margen': '%Mg', 'pares': 'Pares', 'total_sueldos': 'Sueldos',
                'empleados': 'Empl', 'gasto_neto': 'Gastos', 'resultado': 'Resultado'
            }).style.format({
                'Venta neta': '${:,.0f}', 'CMV': '${:,.0f}', 'Margen': '${:,.0f}',
                '%Mg': '{:.1f}%', 'Pares': '{:,.0f}', 'Sueldos': '${:,.0f}',
                'Empl': '{:.0f}', 'Gastos': '${:,.0f}', 'Resultado': '${:,.0f}',
            }),
            use_container_width=True, hide_index=True
        )

        # Chart
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_local['mes'], y=df_local['margen'], name='Margen', marker_color='#27ae60'))
        fig.add_trace(go.Bar(x=df_local['mes'], y=-df_local['total_sueldos'], name='Sueldos', marker_color='#e74c3c'))
        fig.add_trace(go.Bar(x=df_local['mes'], y=-df_local['gasto_neto'], name='Gastos', marker_color='#f39c12'))
        fig.add_trace(go.Scatter(x=df_local['mes'], y=df_local['resultado'], name='Resultado',
                                  line=dict(color='#2c3e50', width=3)))
        fig.update_layout(title=f"P&L {DEPOSITOS.get(dep_sel, dep_sel)}", barmode='relative', height=400)
        st.plotly_chart(fig, use_container_width=True)

        # Transferencias
        dt = df_transfer[df_transfer['sucursal'] == dep_sel]
        if not dt.empty:
            st.subheader("Transferencias (entrada/salida pares)")
            st.dataframe(
                dt[['mes', 'entrada', 'salida', 'neto', 'neto_costo_cer']].rename(columns={
                    'entrada': 'Entrada pares', 'salida': 'Salida pares',
                    'neto': 'Neto pares', 'neto_costo_cer': 'Neto costo CER'
                }).style.format({
                    'Entrada pares': '{:,.0f}', 'Salida pares': '{:,.0f}',
                    'Neto pares': '{:,.0f}', 'Neto costo CER': '${:,.0f}',
                }),
                use_container_width=True, hide_index=True
            )


with tab3:
    st.header("📦 Presupuesto Optimo de Compra por Local")
    st.caption("Basado en CMV historico * estacionalidad. El CMV (costo de mercaderia vendida) define cuanto hay que reponer.")

    dep_pres = st.selectbox("Local para presupuesto", options=deps_en_data,
                            format_func=lambda x: DEPOSITOS.get(x, f'Dep {x}'), key='dep_pres')

    dv_pres = df_ventas[df_ventas['deposito'] == dep_pres]
    presupuesto = calcular_presupuesto_optimo(dv_pres)

    if not presupuesto.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("CMV promedio mensual", formato_m(presupuesto['cmv_historico'].mean()))
        c2.metric("Presupuesto anual compra", formato_m(presupuesto['presupuesto_compra'].sum()))
        c3.metric("Pares estimados/anio", f"{presupuesto['presupuesto_pares'].sum():,.0f}")

        st.dataframe(
            presupuesto[['mes_nombre', 'cmv_historico', 'factor_estacional',
                          'presupuesto_compra', 'presupuesto_pares']].rename(columns={
                'mes_nombre': 'Mes', 'cmv_historico': 'CMV historico',
                'factor_estacional': 'Factor est.', 'presupuesto_compra': 'Presupuesto $',
                'presupuesto_pares': 'Pres. pares'
            }).style.format({
                'CMV historico': '${:,.0f}', 'Factor est.': '{:.2f}',
                'Presupuesto $': '${:,.0f}', 'Pres. pares': '{:,.0f}',
            }),
            use_container_width=True, hide_index=True
        )

        fig = px.bar(presupuesto, x='mes_nombre', y='presupuesto_compra',
                     title=f"Presupuesto de compra mensual — {DEPOSITOS.get(dep_pres, dep_pres)}",
                     labels={'presupuesto_compra': 'Presupuesto $', 'mes_nombre': 'Mes'})
        fig.add_scatter(x=presupuesto['mes_nombre'], y=presupuesto['cmv_historico'],
                        name='CMV historico', line=dict(color='red', dash='dash'))
        st.plotly_chart(fig, use_container_width=True)

        # Comparar todos los locales
        st.subheader("Comparativa presupuesto todos los locales")
        comp = []
        for dep in deps_en_data:
            dv_c = df_ventas[df_ventas['deposito'] == dep]
            if dv_c.empty:
                continue
            cmv_prom = dv_c['costo'].mean()
            vta_prom = dv_c['venta_neta'].mean()
            mg_prom = dv_c['margen'].mean()
            comp.append({
                'Local': DEPOSITOS.get(dep, f'Dep {dep}'),
                'CMV prom/mes': cmv_prom,
                'Presupuesto anual': cmv_prom * 12,
                'Venta prom/mes': vta_prom,
                'Margen prom/mes': mg_prom,
                'Rotacion (vta/cmv)': vta_prom / cmv_prom if cmv_prom > 0 else 0,
            })
        df_comp = pd.DataFrame(comp).sort_values('CMV prom/mes', ascending=False)
        st.dataframe(
            df_comp.style.format({
                'CMV prom/mes': '${:,.0f}', 'Presupuesto anual': '${:,.0f}',
                'Venta prom/mes': '${:,.0f}', 'Margen prom/mes': '${:,.0f}',
                'Rotacion (vta/cmv)': '{:.2f}x',
            }),
            use_container_width=True, hide_index=True
        )


with tab4:
    st.header("📈 Piramide de Precios & Marcas")

    dep_pir = st.selectbox("Local", options=deps_en_data,
                           format_func=lambda x: DEPOSITOS.get(x, f'Dep {x}'), key='dep_pir')

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Piramide de precios")
        df_pir = get_piramide_precios(dep_pir)
        if not df_pir.empty:
            st.dataframe(
                df_pir[['segmento', 'pares', 'pct_pares', 'venta_neta', 'pct_venta', 'margen', 'pct_margen']].rename(columns={
                    'segmento': 'Segmento', 'pares': 'Pares', 'pct_pares': '% Pares',
                    'venta_neta': 'Venta neta', 'pct_venta': '% Venta',
                    'margen': 'Margen', 'pct_margen': '% Margen'
                }).style.format({
                    'Pares': '{:,.0f}', '% Pares': '{:.1f}%',
                    'Venta neta': '${:,.0f}', '% Venta': '{:.1f}%',
                    'Margen': '${:,.0f}', '% Margen': '{:.1f}%',
                }),
                use_container_width=True, hide_index=True
            )

            fig = px.bar(df_pir, x='segmento', y='venta_neta', color='pct_margen',
                         color_continuous_scale='RdYlGn', title='Venta por segmento de precio',
                         labels={'venta_neta': 'Venta neta', 'pct_margen': '% Margen'})
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Top marcas")
        df_marc = get_marcas_por_deposito(dep_pir)
        if not df_marc.empty:
            st.dataframe(
                df_marc[['marca_nombre', 'pares', 'venta_neta', 'margen', 'pct_margen']].rename(columns={
                    'marca_nombre': 'Marca', 'pares': 'Pares', 'venta_neta': 'Venta neta',
                    'margen': 'Margen', 'pct_margen': '% Margen'
                }).style.format({
                    'Pares': '{:,.0f}', 'Venta neta': '${:,.0f}',
                    'Margen': '${:,.0f}', '% Margen': '{:.1f}%',
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No hay datos de marcas para este deposito")


# =============================================================
# TAB 5: CONTROL DE STOCK — RECONCILIACION
# =============================================================
with tab5:
    st.header("Control de Stock — Reconciliacion de Inventario")
    st.markdown("Cruza stock actual, ventas, transferencias y discrepancias POS por deposito.")

    @st.cache_data(ttl=3600)
    def get_stock_por_deposito():
        conn = pyodbc.connect(config.get_conn_string(config.BD_COMPRAS))
        sql = """
            SELECT s.deposito,
                   SUM(CASE WHEN s.stock_actual > 0 THEN s.stock_actual ELSE 0 END) AS positivo,
                   SUM(CASE WHEN s.stock_actual < 0 THEN s.stock_actual ELSE 0 END) AS negativo,
                   SUM(s.stock_actual) AS neto,
                   COUNT(DISTINCT s.articulo) AS articulos,
                   CAST(SUM(s.stock_actual * a.precio_costo) AS BIGINT) AS costo_neto,
                   CAST(SUM(CASE WHEN s.stock_actual > 0 THEN s.stock_actual * a.precio_costo ELSE 0 END) AS BIGINT) AS costo_positivo,
                   CAST(SUM(CASE WHEN s.stock_actual < 0 THEN s.stock_actual * a.precio_costo ELSE 0 END) AS BIGINT) AS costo_negativo
            FROM msgestionC.dbo.stock s
            JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
            WHERE s.stock_actual <> 0
            GROUP BY s.deposito
        """
        df = pd.read_sql(sql, conn)
        conn.close()
        return df

    @st.cache_data(ttl=3600)
    def get_transferencias_6m():
        conn = pyodbc.connect(config.get_conn_string(config.BD_COMPRAS))
        sql = """
            SELECT m.deposito,
                   SUM(CASE WHEN m.operacion='+' THEN m.cantidad ELSE 0 END) AS transf_entrada,
                   SUM(CASE WHEN m.operacion='-' THEN m.cantidad ELSE 0 END) AS transf_salida
            FROM msgestion01.dbo.movi_stock m
            WHERE m.codigo_comprobante = 87 AND m.fecha >= DATEADD(month, -6, GETDATE())
            GROUP BY m.deposito
        """
        df = pd.read_sql(sql, conn)
        conn.close()
        return df

    @st.cache_data(ttl=3600)
    def get_dep199_por_marca_top():
        conn = pyodbc.connect(config.get_conn_string(config.BD_COMPRAS))
        sql = """
            SELECT TOP 20 a.marca, m.descripcion AS marca_desc,
                   COUNT(DISTINCT s.articulo) AS articulos,
                   SUM(s.stock_actual) AS unidades,
                   CAST(SUM(s.stock_actual * a.precio_costo) AS BIGINT) AS costo
            FROM msgestionC.dbo.stock s
            JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
            LEFT JOIN msgestion03.dbo.marcas m ON m.codigo = a.marca
            WHERE s.deposito = 199 AND s.stock_actual > 0
            GROUP BY a.marca, m.descripcion
            ORDER BY SUM(s.stock_actual * a.precio_costo) DESC
        """
        df = pd.read_sql(sql, conn)
        conn.close()
        return df

    @st.cache_data(ttl=3600)
    def get_dep199_por_origen_6m():
        conn = pyodbc.connect(config.get_conn_string(config.BD_COMPRAS))
        sql = """
            SELECT m.sucursal_comprobante AS origen,
                   SUM(CASE WHEN m.operacion='+' THEN m.cantidad ELSE 0 END) AS pares_entrada,
                   COUNT(CASE WHEN m.operacion='+' THEN 1 END) AS movs_entrada
            FROM msgestion01.dbo.movi_stock m
            WHERE m.deposito = 199 AND m.codigo_comprobante = 87
              AND m.fecha >= DATEADD(month, -6, GETDATE())
            GROUP BY m.sucursal_comprobante
        """
        df = pd.read_sql(sql, conn)
        conn.close()
        return df

    @st.cache_data(ttl=3600)
    def get_dep199_mensual():
        conn = pyodbc.connect(config.get_conn_string(config.BD_COMPRAS))
        sql = """
            SELECT CONVERT(VARCHAR(7), m.fecha, 120) AS mes,
                   SUM(CASE WHEN m.operacion='+' THEN m.cantidad ELSE 0 END) AS entrada,
                   SUM(CASE WHEN m.operacion='-' THEN m.cantidad ELSE 0 END) AS salida
            FROM msgestion01.dbo.movi_stock m
            WHERE m.deposito = 199 AND m.codigo_comprobante IN (87, 22)
              AND m.fecha >= '2024-01-01'
              AND m.cantidad < 100000
            GROUP BY CONVERT(VARCHAR(7), m.fecha, 120)
        """
        df = pd.read_sql(sql, conn)
        conn.close()
        return df

    dep_names_ctrl = {
        0: 'Central', 1: 'Glam/ML', 2: 'Norte', 3: 'Outlet', 4: 'Murphy (Claudia)',
        5: 'Externo', 6: 'Cuore', 7: 'Eva Peron', 8: 'Junin', 9: 'Tokyo',
        10: 'Asesoras (transito)', 11: 'Alternativo/Zapateria', 12: 'Mayorista',
        13: 'Dep 13 (?)', 14: 'Rural', 15: 'Junin GO (cerrado)', 16: 'Chanar Ladeado',
        198: 'Transito/Distribucion', 199: 'Discrepancias POS', 100: 'Dep 100', 202: 'Dep 202'
    }

    try:
        df_stock = get_stock_por_deposito()
        df_transf = get_transferencias_6m()
        df_199_marcas = get_dep199_por_marca_top()
        df_199_origen = get_dep199_por_origen_6m()
        df_199_mes = get_dep199_mensual()

        # --- KPIs ---
        dep199 = df_stock[df_stock['deposito'] == 199]
        total_stock_costo = df_stock['costo_neto'].sum()
        dep199_costo = int(dep199['costo_neto'].iloc[0]) if len(dep199) > 0 else 0
        dep199_unidades = int(dep199['neto'].iloc[0]) if len(dep199) > 0 else 0
        dep199_pct = dep199_costo / total_stock_costo * 100 if total_stock_costo > 0 else 0

        total_negativo = int(df_stock['negativo'].sum())
        total_negativo_costo = int(df_stock['costo_negativo'].sum())
        deps_con_negativo = len(df_stock[df_stock['negativo'] < -1])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Dep 199 (discrepancias)", f"{dep199_unidades:,.0f} pares",
                     delta=f"${dep199_costo:,.0f} costo", delta_color="inverse")
        col2.metric("% del stock total", f"{dep199_pct:.1f}%",
                     delta="del costo total en limbo")
        col3.metric("Stock negativo total", f"{total_negativo:,.0f} pares",
                     delta=f"${total_negativo_costo:,.0f} costo", delta_color="inverse")
        col4.metric("Deps con negativos", f"{deps_con_negativo}",
                     delta=f"de {len(df_stock)} depositos")

        # --- TABLA: Estado por deposito ---
        st.subheader("Estado de stock por deposito")

        df_ctrl = df_stock.copy()
        df_ctrl = df_ctrl.merge(df_transf, on='deposito', how='left').fillna(0)
        df_ctrl['local'] = df_ctrl['deposito'].map(dep_names_ctrl).fillna('Dep ' + df_ctrl['deposito'].astype(str))
        df_ctrl['transf_neto'] = df_ctrl['transf_entrada'] - df_ctrl['transf_salida']
        df_ctrl = df_ctrl.sort_values('costo_neto', ascending=False)

        deps_validos = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 198, 199]
        df_ctrl_show = df_ctrl[df_ctrl['deposito'].isin(deps_validos)]

        df_basura = df_ctrl[~df_ctrl['deposito'].isin(deps_validos)]
        if len(df_basura) > 0:
            st.warning(f"Depositos basura: {', '.join(str(d) for d in df_basura['deposito'].tolist())} "
                       f"({int(df_basura['neto'].sum())} pares, ${int(df_basura['costo_neto'].sum()):,.0f}). Errores de carga.")

        st.dataframe(
            df_ctrl_show[['local', 'positivo', 'negativo', 'neto', 'articulos',
                          'costo_neto', 'transf_entrada', 'transf_salida', 'transf_neto']].rename(columns={
                'local': 'Local', 'positivo': 'Stock +', 'negativo': 'Stock -', 'neto': 'Neto',
                'articulos': 'SKUs', 'costo_neto': 'Costo $', 'transf_entrada': 'Transf IN 6m',
                'transf_salida': 'Transf OUT 6m', 'transf_neto': 'Neto transf'
            }).style.format({
                'Stock +': '{:,.0f}', 'Stock -': '{:,.0f}', 'Neto': '{:,.0f}', 'SKUs': '{:,.0f}',
                'Costo $': '${:,.0f}', 'Transf IN 6m': '{:,.0f}', 'Transf OUT 6m': '{:,.0f}', 'Neto transf': '{:,.0f}'
            }),
            use_container_width=True, hide_index=True
        )

        st.markdown("""
        **Como leer:**
        - **Stock -**: pares negativos = se vendio mercaderia que no se registro de entrada
        - **Neto transf**: positivo = recibe mas. Negativo = envia mas (dep 11 = almacen, dep 199 = acumula)
        - **Dep 198**: transito/distribucion, alta rotacion, debe estar cerca de 0
        - **Dep 199**: discrepancias POS, crece ~1500 pares/mes, se limpia con NIE masiva
        """)

        # --- DEP 199: DETALLE ---
        st.subheader("Dep 199 — Discrepancias POS")
        c199_1, c199_2 = st.columns(2)

        with c199_1:
            st.markdown("**Marcas mas afectadas**")
            if len(df_199_marcas) > 0:
                st.dataframe(
                    df_199_marcas.rename(columns={
                        'marca_desc': 'Marca', 'articulos': 'SKUs', 'unidades': 'Pares', 'costo': 'Costo $'
                    })[['Marca', 'SKUs', 'Pares', 'Costo $']].style.format({
                        'Pares': '{:,.0f}', 'Costo $': '${:,.0f}', 'SKUs': '{:,.0f}'
                    }),
                    use_container_width=True, hide_index=True
                )

        with c199_2:
            st.markdown("**Origen de discrepancias (ult 6m)**")
            if len(df_199_origen) > 0:
                df_199_origen['local'] = df_199_origen['origen'].map(dep_names_ctrl).fillna('?')
                df_199_origen = df_199_origen.sort_values('pares_entrada', ascending=False)
                st.dataframe(
                    df_199_origen[['local', 'pares_entrada', 'movs_entrada']].rename(columns={
                        'local': 'Local origen', 'pares_entrada': 'Pares a 199', 'movs_entrada': 'Movimientos'
                    }).style.format({'Pares a 199': '{:,.0f}', 'Movimientos': '{:,.0f}'}),
                    use_container_width=True, hide_index=True
                )

        # --- GRAFICO EVOLUCION DEP 199 ---
        if len(df_199_mes) > 0:
            st.markdown("**Evolucion mensual dep 199**")
            df_199_mes = df_199_mes.sort_values('mes')
            df_199_mes['neto'] = df_199_mes['entrada'] - df_199_mes['salida']
            fig_199 = go.Figure()
            fig_199.add_trace(go.Bar(x=df_199_mes['mes'], y=df_199_mes['entrada'], name='Entrada', marker_color='#e74c3c'))
            fig_199.add_trace(go.Bar(x=df_199_mes['mes'], y=-df_199_mes['salida'], name='Salida (NIE/recupero)', marker_color='#27ae60'))
            fig_199.add_trace(go.Scatter(x=df_199_mes['mes'], y=df_199_mes['neto'], name='Neto', line=dict(color='#2c3e50', width=2)))
            fig_199.update_layout(barmode='relative', height=300, margin=dict(t=30, b=30),
                                  legend=dict(orientation='h', y=1.1))
            st.plotly_chart(fig_199, use_container_width=True)

        # --- DEPOSITOS CON STOCK NEGATIVO ---
        st.subheader("Depositos con stock negativo")
        df_neg = df_ctrl_show[df_ctrl_show['negativo'] < -1].sort_values('negativo')
        if len(df_neg) > 0:
            for _, row in df_neg.iterrows():
                pct_neg = abs(row['negativo']) / (row['positivo'] + abs(row['negativo'])) * 100 if row['positivo'] > 0 else 100
                color = "🔴" if pct_neg > 5 else "🟡" if pct_neg > 2 else "🟢"
                st.markdown(f"{color} **{row['local']}**: {int(row['negativo']):,} pares negativos "
                            f"({pct_neg:.1f}%). Costo: ${int(row['costo_negativo']):,.0f}")
        else:
            st.success("Sin stock negativo significativo")

        st.markdown("""
        ---
        **Diagnostico dep 199 (mar 2026):**
        - 79% productos ACTIVOS (vendidos en 2025+), no stock viejo
        - NO es robo: talles uniformes 6-9%, items baratos predominan
        - Error sistemico: POS genera transferencia auto (cod 87-P) cuando conteo != sistema
        - POS-CS180 = terminal movil mas problematica (18k pares historicos)
        - Central genera 40% de discrepancias
        - Solo 2 limpiezas masivas: jun-2023 y abr-2025
        - Solo SST y SS recuperan stock (cuello de botella)
        """)

    except Exception as e:
        st.error(f"Error cargando control stock: {e}")

st.divider()
st.caption("H4 SRL / CALZALINDO — Modelo de Locales v1.0 — Generado automaticamente")
