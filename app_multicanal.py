#!/usr/bin/env python3
"""
App Multicanal — Publicación de productos y pricing por canal.
App independiente, no modifica ninguna app existente.

EJECUTAR:
    streamlit run app_multicanal.py --server.port 8505

INSTALAR:
    pip install streamlit pyodbc requests
"""
import os
import sys
import json
import pandas as pd
import requests
import streamlit as st
from datetime import datetime

# OpenSSL legacy config para SQL Server 2012 (no soporta TLS 1.2+)
_openssl_legacy = os.path.join(os.path.dirname(__file__), 'multicanal', 'openssl_legacy.cnf')
if os.path.exists(_openssl_legacy) and 'OPENSSL_CONF' not in os.environ:
    os.environ['OPENSSL_CONF'] = _openssl_legacy

sys.path.insert(0, os.path.dirname(__file__))

from multicanal.precios import (
    ReglaCanal, REGLAS_DEFAULT,
    calcular_precio_canal, calcular_todos_los_canales,
    guardar_reglas, cargar_reglas,
)

# ── Config ──
REGLAS_FILE = os.path.join(os.path.dirname(__file__), 'multicanal', 'reglas_canales.json')

st.set_page_config(
    page_title='Multicanal — Calzalindo',
    page_icon='📡',
    layout='wide',
)


# ── Conexión DB ──
def get_db():
    """Conexión a SQL Server (ERP) — Driver 17 para compatibilidad con SQL Server 2012."""
    import pyodbc
    conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.2.111;DATABASE=msgestion01art;UID=am;PWD=dl;Encrypt=no;"
    conn = st.session_state.get('db_conn')
    # Verificar que la conexión existente siga viva
    if conn is not None:
        try:
            conn.execute("SELECT 1")
        except Exception:
            conn = None
            st.session_state.db_conn = None
    if conn is None:
        try:
            st.session_state.db_conn = pyodbc.connect(conn_str, timeout=10)
        except Exception as e:
            st.error(f"Error conectando a SQL Server: {e}")
            st.session_state.db_conn = None
    return st.session_state.get('db_conn')


@st.cache_data(ttl=300)
def cargar_productos(_conn):
    """Carga artículos del ERP con precio y stock."""
    sql = """
        SELECT TOP 500
            a.codigo, a.codigo_barra, a.codigo_sinonimo as sinonimo,
            a.descripcion_1, a.descripcion_2, a.descripcion_3,
            a.precio_costo,
            m.descripcion as marca,
            ISNULL((SELECT stock_actual FROM msgestion01.dbo.stock
                    WHERE articulo=a.codigo AND deposito=1), 0) as stock_d1,
            ISNULL((SELECT stock_actual FROM msgestion03.dbo.stock
                    WHERE articulo=a.codigo AND deposito=1), 0) as stock_h4
        FROM articulo a
        LEFT JOIN marcas m ON m.codigo=a.marca
        WHERE a.estado IN ('V', 'U')
        AND a.precio_costo > 0
        ORDER BY a.codigo DESC
    """
    try:
        return pd.read_sql(sql, _conn)
    except Exception as e:
        st.error(f"Error leyendo artículos: {e}")
        return pd.DataFrame()


# ── Estado de sesión ──
if 'reglas' not in st.session_state:
    st.session_state.reglas = cargar_reglas(REGLAS_FILE)


# ── Sidebar ──
st.sidebar.title('📡 Multicanal')
pagina = st.sidebar.radio('Navegación', [
    '🏠 Dashboard',
    '📊 Análisis ML',
    '🛒 Tienda Nube',
    '🔄 Sincronización',
    '💰 Simulador de precios',
    '⚙️ Configurar canales',
    '📦 Catálogo ERP',
])


# ══════════════════════════════════════════════════
# PÁGINA: Dashboard
# ══════════════════════════════════════════════════
if pagina == '🏠 Dashboard':
    st.title('📡 Panel Multicanal')
    st.markdown('Publicá y sincronizá productos en todos los canales de venta.')

    reglas = st.session_state.reglas
    cols = st.columns(len(reglas))
    for i, (nombre, regla) in enumerate(reglas.items()):
        with cols[i]:
            color = '🟢' if regla.activo else '🔴'
            st.metric(
                label=f"{color} {regla.descripcion}",
                value=f"{regla.comision*100:.0f}% + {regla.comision_pago*100:.1f}%",
                delta=f"Margen obj: {regla.margen_objetivo*100:.0f}%",
            )

    st.divider()

    # Ejemplo rápido de pricing
    st.subheader('Simulación rápida')
    costo_rapido = st.number_input('Precio de costo ($)', value=30000.0, step=1000.0, key='dash_costo')

    if costo_rapido > 0:
        resultados = calcular_todos_los_canales(costo_rapido, reglas)
        df = pd.DataFrame([
            {
                'Canal': r['canal_descripcion'],
                'PVP c/IVA': f"${r['precio_venta']:,.0f}",
                'P.Neto': f"${r['precio_neto']:,.0f}",
                'Margen': f"{r['margen_real']}%",
                'En mano': f"{r['margen_en_mano']}%",
                'Ganancia': f"${r['ganancia_neta']:,.0f}",
                'Comisiones': f"${r['comision_plataforma'] + r['comision_pago']:,.0f}",
                'IVA s/com.': f"${r['iva_sobre_comisiones']:,.0f}",
                'Envío': f"${r['costo_envio']:,.0f}",
                'Retenciones': f"${r['retenciones']:,.0f}",
            }
            for r in resultados.values()
            if 'error' not in r
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════
# PÁGINA: Análisis ML
# ══════════════════════════════════════════════════
elif pagina == '📊 Análisis ML':
    st.title('📊 Análisis de Ventas MercadoLibre')
    st.markdown('Ventas del depósito 1 (ML) — H4 SRL (msgestion03). Datos en vivo del ERP.')

    conn = get_db()
    if conn:
        meses_atras = st.sidebar.slider('Meses de historia', 3, 24, 12)
        comision_ml = st.sidebar.number_input('Comisión ML (%)', value=16.0, step=0.5) / 100
        cotiz_usd = st.sidebar.number_input('Cotización USD ($)', value=1170.0, step=10.0,
                                             help='Para artículos importados con costo en dólares (moneda=1)')
        st.sidebar.caption(f'70 artículos en USD en el ERP. Costo se convierte a $ × {cotiz_usd:,.0f}')

        # Expresión SQL para costo real en pesos (convierte USD si moneda=1)
        costo_pesos = f"CASE WHEN a.moneda = 1 THEN a.precio_costo * {cotiz_usd} ELSE a.precio_costo END"

        # ── Ventas mensuales ──
        sql_mensual = f"""
            SELECT
                FORMAT(v2.fecha_comprobante, 'yyyy-MM') as mes,
                COUNT(DISTINCT CAST(v2.numero AS VARCHAR) + '-' + CAST(v2.sucursal AS VARCHAR)) as facturas,
                SUM(v1.cantidad) as pares,
                SUM(v1.total_item) as facturacion,
                SUM(v1.total_item / 1.21) as facturacion_neta,
                SUM(v1.cantidad * ({costo_pesos})) as costo_total,
                CASE WHEN SUM(v1.total_item) > 0
                    THEN ROUND((SUM(v1.total_item / 1.21) - SUM(v1.cantidad * ({costo_pesos}))) / SUM(v1.total_item / 1.21) * 100, 1)
                    ELSE 0 END as margen_bruto_pct
            FROM msgestion03.dbo.ventas2 v2
            JOIN msgestion03.dbo.ventas1 v1
                ON v1.numero = v2.numero AND v1.codigo = v2.codigo AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
            LEFT JOIN msgestion01art.dbo.articulo a ON a.codigo = v1.articulo
            WHERE v2.codigo NOT IN (7, 36)
            AND v1.deposito = 1
            AND v2.fecha_comprobante >= DATEADD(MONTH, -{meses_atras}, GETDATE())
            AND v1.operacion = '+'
            GROUP BY FORMAT(v2.fecha_comprobante, 'yyyy-MM')
            ORDER BY mes
        """
        try:
            df_mensual = pd.read_sql(sql_mensual, conn)
        except Exception as e:
            st.error(f"Error: {e}")
            df_mensual = pd.DataFrame()

        if not df_mensual.empty:
            df_mensual['margen_neto_ml'] = (df_mensual['margen_bruto_pct'] - comision_ml * 100).round(1)
            df_mensual['ticket_promedio'] = (df_mensual['facturacion'] / df_mensual['pares']).round(0)

            # KPIs
            total_fact = df_mensual['facturacion'].sum()
            total_fact_neto = df_mensual['facturacion_neta'].sum()
            total_pares = df_mensual['pares'].sum()
            total_costo = df_mensual['costo_total'].sum()
            margen_global = round((total_fact_neto - total_costo) / total_fact_neto * 100, 1) if total_fact_neto > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric('Facturación total', f"${total_fact:,.0f}")
            c2.metric('Pares vendidos', f"{total_pares:,.0f}")
            c3.metric('Margen bruto', f"{margen_global}%")
            c4.metric('Margen neto ML', f"{margen_global - comision_ml*100:.1f}%")

            st.divider()

            # Tabla mensual
            st.subheader('Evolución mensual')
            df_show = df_mensual.copy()
            df_show.columns = ['Mes', 'Facturas', 'Pares', 'Facturación', 'Fact. Neta', 'Costo', 'Margen bruto %', 'Margen neto ML %', 'Ticket prom']
            st.dataframe(df_show, use_container_width=True, hide_index=True)

            # Gráficos
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader('Facturación mensual')
                chart_fact = df_mensual[['mes', 'facturacion']].set_index('mes')
                st.bar_chart(chart_fact)
            with col_g2:
                st.subheader('Margen % mensual')
                chart_margen = df_mensual[['mes', 'margen_bruto_pct', 'margen_neto_ml']].set_index('mes')
                chart_margen.columns = ['Bruto', 'Neto ML']
                st.line_chart(chart_margen)

            st.divider()

            # ── Distribución de markup ──
            st.subheader('Distribución de markup')
            sql_markup = f"""
                SELECT
                    CASE
                        WHEN ({costo_pesos}) <= 100 THEN '1. SIN COSTO'
                        WHEN (v1.precio / 1.21) / ({costo_pesos}) < 1.5 THEN '2. BAJO (<1.5x)'
                        WHEN (v1.precio / 1.21) / ({costo_pesos}) < 2.0 THEN '3. AJUSTADO (1.5-2x)'
                        WHEN (v1.precio / 1.21) / ({costo_pesos}) < 2.5 THEN '4. NORMAL (2-2.5x)'
                        WHEN (v1.precio / 1.21) / ({costo_pesos}) < 3.0 THEN '5. BUENO (2.5-3x)'
                        ELSE '6. ALTO (3x+)'
                    END as rango,
                    COUNT(*) as ventas,
                    SUM(v1.cantidad) as pares,
                    SUM(v1.total_item) as facturacion,
                    ROUND(AVG(v1.precio / 1.21), 0) as pvta_neto_prom,
                    ROUND(AVG({costo_pesos}), 0) as costo_prom
                FROM msgestion03.dbo.ventas2 v2
                JOIN msgestion03.dbo.ventas1 v1
                    ON v1.numero = v2.numero AND v1.codigo = v2.codigo AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
                LEFT JOIN msgestion01art.dbo.articulo a ON a.codigo = v1.articulo
                WHERE v2.codigo NOT IN (7, 36) AND v1.deposito = 1
                AND v2.fecha_comprobante >= DATEADD(MONTH, -{meses_atras}, GETDATE())
                AND v1.operacion = '+' AND a.precio_costo > 0
                GROUP BY CASE
                    WHEN ({costo_pesos}) <= 100 THEN '1. SIN COSTO'
                    WHEN (v1.precio / 1.21) / ({costo_pesos}) < 1.5 THEN '2. BAJO (<1.5x)'
                    WHEN (v1.precio / 1.21) / ({costo_pesos}) < 2.0 THEN '3. AJUSTADO (1.5-2x)'
                    WHEN (v1.precio / 1.21) / ({costo_pesos}) < 2.5 THEN '4. NORMAL (2-2.5x)'
                    WHEN (v1.precio / 1.21) / ({costo_pesos}) < 3.0 THEN '5. BUENO (2.5-3x)'
                    ELSE '6. ALTO (3x+)'
                END
                ORDER BY rango
            """
            try:
                df_markup = pd.read_sql(sql_markup, conn)
                df_markup.columns = ['Rango', 'Ventas', 'Pares', 'Facturación', 'Pvta prom', 'Costo prom']
                st.dataframe(df_markup, use_container_width=True, hide_index=True)

                # Alerta de sin costo — con detalle expandible
                sin_costo = df_markup[df_markup['Rango'] == '1. SIN COSTO']
                if not sin_costo.empty:
                    pares_sc = int(sin_costo.iloc[0]['Pares'])
                    fact_sc = sin_costo.iloc[0]['Facturación']
                    with st.expander(f"**{pares_sc} pares** vendidos SIN COSTO REAL (${fact_sc:,.0f} facturados) — click para ver detalle", expanded=False):
                        try:
                            sql_sin_costo = f"""
                                SELECT
                                    v1.articulo as codigo,
                                    a.descripcion_1 as descripcion,
                                    SUM(v1.cantidad) as pares,
                                    SUM(v1.total_item) as facturacion,
                                    ROUND(AVG(v1.precio), 0) as pvta_prom,
                                    ROUND(AVG({costo_pesos}), 0) as costo_cargado
                                FROM msgestion03.dbo.ventas2 v2
                                JOIN msgestion03.dbo.ventas1 v1
                                    ON v1.numero = v2.numero AND v1.codigo = v2.codigo AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
                                LEFT JOIN msgestion01art.dbo.articulo a ON a.codigo = v1.articulo
                                WHERE v2.codigo NOT IN (7, 36) AND v1.deposito = 1
                                AND v2.fecha_comprobante >= DATEADD(MONTH, -{meses_atras}, GETDATE())
                                AND v1.operacion = '+'
                                AND ({costo_pesos}) <= 100
                                GROUP BY v1.articulo, a.descripcion_1
                                ORDER BY SUM(v1.total_item) DESC
                            """
                            df_sc = pd.read_sql(sql_sin_costo, conn)
                            df_sc.columns = ['Código', 'Descripción', 'Pares', 'Facturación', 'Pvta prom', 'Costo cargado']
                            st.dataframe(df_sc, use_container_width=True, hide_index=True)
                            st.caption("Estos artículos tienen precio_costo = 0 o muy bajo en el ERP. Actualizar para calcular rentabilidad real.")
                        except Exception as e:
                            st.error(f"Error cargando detalle sin costo: {e}")

                bajo = df_markup[df_markup['Rango'].isin(['2. BAJO (<1.5x)', '3. AJUSTADO (1.5-2x)'])]
                if not bajo.empty:
                    pares_bajo = int(bajo['Pares'].sum())
                    fact_bajo = bajo['Facturación'].sum()
                    with st.expander(f"**{pares_bajo} pares** con markup < 2x (${fact_bajo:,.0f}) — click para ver detalle", expanded=False):
                        try:
                            sql_bajo_markup = f"""
                                SELECT
                                    v1.articulo as codigo,
                                    a.descripcion_1 as descripcion,
                                    SUM(v1.cantidad) as pares,
                                    SUM(v1.total_item) as facturacion,
                                    ROUND(AVG(v1.precio / 1.21), 0) as pvta_neto,
                                    ROUND(AVG({costo_pesos}), 0) as costo,
                                    ROUND(AVG(v1.precio / 1.21) / NULLIF(AVG({costo_pesos}), 0), 2) as markup_x,
                                    CASE WHEN AVG(v1.precio / 1.21) > 0
                                        THEN ROUND((AVG(v1.precio / 1.21) - AVG({costo_pesos})) / AVG(v1.precio / 1.21) * 100, 1)
                                        ELSE 0 END as margen_pct
                                FROM msgestion03.dbo.ventas2 v2
                                JOIN msgestion03.dbo.ventas1 v1
                                    ON v1.numero = v2.numero AND v1.codigo = v2.codigo AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
                                LEFT JOIN msgestion01art.dbo.articulo a ON a.codigo = v1.articulo
                                WHERE v2.codigo NOT IN (7, 36) AND v1.deposito = 1
                                AND v2.fecha_comprobante >= DATEADD(MONTH, -{meses_atras}, GETDATE())
                                AND v1.operacion = '+' AND ({costo_pesos}) > 100
                                AND (v1.precio / 1.21) / ({costo_pesos}) < 2.0
                                GROUP BY v1.articulo, a.descripcion_1
                                HAVING SUM(v1.cantidad) >= 1
                                ORDER BY SUM(v1.total_item) DESC
                            """
                            df_bajo = pd.read_sql(sql_bajo_markup, conn)
                            df_bajo.columns = ['Código', 'Descripción', 'Pares', 'Facturación', 'Pvta neto', 'Costo', 'Markup x', 'Margen %']
                            st.dataframe(df_bajo, use_container_width=True, hide_index=True)
                            st.caption("Ordenados por facturación (mayor impacto primero). Markup < 2x = margen neto ML probablemente negativo después de comisiones.")
                        except Exception as e:
                            st.error(f"Error cargando detalle bajo markup: {e}")
            except Exception as e:
                st.error(f"Error markup: {e}")

            st.divider()

            # ── TOP productos con peor margen ──
            st.subheader('Productos con menor margen neto ML')
            st.caption(f'Margen neto = margen bruto - {comision_ml*100:.0f}% comisión ML. Solo productos con 10+ pares vendidos.')
            sql_peor = f"""
                SELECT TOP 30
                    v1.articulo as codigo,
                    a.descripcion_1,
                    CASE WHEN a.moneda = 1 THEN 'USD' ELSE '$' END as moneda,
                    SUM(v1.cantidad) as pares,
                    SUM(v1.total_item) as facturacion,
                    ROUND(AVG(v1.precio), 0) as pvta,
                    ROUND(AVG({costo_pesos}), 0) as costo,
                    CASE WHEN AVG(v1.precio / 1.21) > 0
                        THEN ROUND((AVG(v1.precio / 1.21) - AVG({costo_pesos})) / AVG(v1.precio / 1.21) * 100, 1)
                        ELSE 0 END as margen_bruto,
                    CASE WHEN AVG(v1.precio / 1.21) > 0
                        THEN ROUND((AVG(v1.precio / 1.21) - AVG({costo_pesos})) / AVG(v1.precio / 1.21) * 100 - {comision_ml*100}, 1)
                        ELSE 0 END as margen_neto_ml,
                    ROUND(AVG(v1.precio / 1.21) / NULLIF(AVG({costo_pesos}), 0), 2) as markup_x
                FROM msgestion03.dbo.ventas2 v2
                JOIN msgestion03.dbo.ventas1 v1
                    ON v1.numero = v2.numero AND v1.codigo = v2.codigo AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
                LEFT JOIN msgestion01art.dbo.articulo a ON a.codigo = v1.articulo
                WHERE v2.codigo NOT IN (7, 36) AND v1.deposito = 1
                AND v2.fecha_comprobante >= DATEADD(MONTH, -{meses_atras}, GETDATE())
                AND v1.operacion = '+' AND ({costo_pesos}) > 1000
                GROUP BY v1.articulo, a.descripcion_1, CASE WHEN a.moneda = 1 THEN 'USD' ELSE '$' END
                HAVING SUM(v1.cantidad) >= 10
                ORDER BY margen_bruto ASC
            """
            try:
                df_peor = pd.read_sql(sql_peor, conn)
                df_peor.columns = ['Código', 'Descripción', 'Mon', 'Pares', 'Facturación', 'P.Venta', 'Costo $', 'Margen bruto %', 'Margen neto ML %', 'Markup x']
                st.dataframe(df_peor, use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Error: {e}")

            st.divider()

            # ── TOP productos más vendidos ──
            st.subheader('TOP productos más vendidos en ML')
            sql_top = f"""
                SELECT TOP 30
                    v1.articulo as codigo,
                    a.descripcion_1,
                    CASE WHEN a.moneda = 1 THEN 'USD' ELSE '$' END as moneda,
                    SUM(v1.cantidad) as pares,
                    SUM(v1.total_item) as facturacion,
                    ROUND(AVG(v1.precio), 0) as pvta,
                    ROUND(AVG({costo_pesos}), 0) as costo,
                    CASE WHEN AVG(v1.precio) > 0
                        THEN ROUND((AVG(v1.precio) - AVG({costo_pesos})) / AVG(v1.precio) * 100 - {comision_ml*100}, 1)
                        ELSE 0 END as margen_neto_ml,
                    ROUND(AVG(v1.precio) / NULLIF(AVG({costo_pesos}), 0), 2) as markup_x
                FROM msgestion03.dbo.ventas2 v2
                JOIN msgestion03.dbo.ventas1 v1
                    ON v1.numero = v2.numero AND v1.codigo = v2.codigo AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
                LEFT JOIN msgestion01art.dbo.articulo a ON a.codigo = v1.articulo
                WHERE v2.codigo NOT IN (7, 36) AND v1.deposito = 1
                AND v2.fecha_comprobante >= DATEADD(MONTH, -{meses_atras}, GETDATE())
                AND v1.operacion = '+' AND ({costo_pesos}) > 1000
                GROUP BY v1.articulo, a.descripcion_1, CASE WHEN a.moneda = 1 THEN 'USD' ELSE '$' END
                HAVING SUM(v1.cantidad) >= 5
                ORDER BY pares DESC
            """
            try:
                df_top = pd.read_sql(sql_top, conn)
                df_top.columns = ['Código', 'Descripción', 'Mon', 'Pares', 'Facturación', 'P.Venta', 'Costo $', 'Margen neto ML %', 'Markup x']

                # Colorear margen
                st.dataframe(df_top, use_container_width=True, hide_index=True)

                # Resumen
                if not df_top.empty:
                    st.caption(f"TOP 30: {int(df_top['Pares'].sum())} pares, "
                               f"${df_top['Facturación'].sum():,.0f} facturados, "
                               f"margen neto ML promedio: {df_top['Margen neto ML %'].mean():.1f}%")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning('No se encontraron datos de ventas.')
    else:
        st.error('No hay conexión a SQL Server. Verificá VPN y credenciales.')


# ══════════════════════════════════════════════════
# PÁGINA: Tienda Nube
# ══════════════════════════════════════════════════
elif pagina == '🛒 Tienda Nube':
    st.title('🛒 Tienda Nube — Calzalindo')

    from multicanal.tiendanube import TiendaNubeClient, guardar_config, cargar_config

    # Config
    tn_config = cargar_config()
    with st.sidebar.expander('Credenciales TN', expanded=not tn_config):
        tn_store = st.text_input('Store ID', value=tn_config.get('store_id', ''), type='default')
        tn_token = st.text_input('Access Token', value=tn_config.get('access_token', ''), type='password')
        if st.button('Guardar credenciales'):
            if tn_store and tn_token:
                guardar_config(tn_store, tn_token)
                st.success('Guardado')
                st.rerun()

    if tn_store and tn_token:
        try:
            tn = TiendaNubeClient(store_id=tn_store, access_token=tn_token)

            tab_ordenes, tab_productos, tab_publicar, tab_sync = st.tabs(['Ordenes', 'Productos TN', 'Publicar producto', 'Sync ERP'])

            # ── TAB: Órdenes ──
            with tab_ordenes:
                st.subheader('Órdenes recientes')
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    filtro_estado = st.selectbox('Estado pago', ['paid', 'pending', 'all'], index=0)
                with col_f2:
                    dias = st.slider('Últimos N días', 1, 90, 30)

                from datetime import timedelta
                fecha_min = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%dT00:00:00')

                with st.spinner('Consultando Tienda Nube...'):
                    try:
                        ordenes = tn.listar_todas_ordenes(
                            payment_status=filtro_estado if filtro_estado != 'all' else None,
                            created_at_min=fecha_min,
                            max_pages=10,
                        )
                        if ordenes:
                            lineas = tn.mapear_sku_a_erp(ordenes)
                            df_ord = pd.DataFrame(lineas)

                            # KPIs
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric('Órdenes', len(ordenes))
                            c2.metric('Items', len(df_ord))
                            c3.metric('Unidades', int(df_ord['cantidad'].sum()))
                            total_tn = df_ord['precio'].mul(df_ord['cantidad']).sum()
                            c4.metric('Facturación', f"${total_tn:,.0f}")

                            st.dataframe(
                                df_ord[['order_number', 'fecha', 'estado_pago', 'sku', 'nombre', 'cantidad', 'precio']],
                                use_container_width=True, hide_index=True,
                            )

                            # SKUs sin vincular
                            sin_sku = df_ord[df_ord['sku'] == '']
                            if not sin_sku.empty:
                                st.warning(f"**{len(sin_sku)} items SIN SKU** — no se pueden vincular al ERP. "
                                           f"Cargá el SKU en TN (= codigo_sinonimo del ERP).")
                        else:
                            st.info('No hay órdenes en el período.')
                    except requests.exceptions.HTTPError as e:
                        if e.response is not None and e.response.status_code == 401:
                            st.error('Token inválido o expirado. Revisá las credenciales en el sidebar.')
                        else:
                            st.error(f'Error API: {e}')
                    except Exception as e:
                        st.error(f'Error: {e}')

            # ── TAB: Productos TN ──
            with tab_productos:
                st.subheader('Productos publicados en Tienda Nube')
                pagina_tn = st.number_input('Página', value=1, min_value=1, step=1, key='tn_page')

                with st.spinner('Cargando productos...'):
                    try:
                        prods = tn.listar_productos(page=int(pagina_tn), per_page=50)
                        if prods:
                            filas = []
                            for p in prods:
                                nombre = p.get('name', {}).get('es', str(p.get('name', '')))
                                for v in p.get('variants', []):
                                    filas.append({
                                        'ID': p['id'],
                                        'Nombre': nombre,
                                        'SKU': v.get('sku', ''),
                                        'Precio': float(v.get('price', 0)),
                                        'Stock': v.get('stock', 0),
                                        'Variante': ' / '.join(
                                            val.get('es', str(val)) if isinstance(val, dict) else str(val)
                                            for val in v.get('values', [])
                                        ),
                                    })
                            df_prods = pd.DataFrame(filas)
                            st.dataframe(df_prods, use_container_width=True, hide_index=True)
                            st.caption(f'{len(prods)} productos, {len(filas)} variantes')
                        else:
                            st.info('No hay productos en esta página.')
                    except requests.exceptions.HTTPError as e:
                        if e.response is not None and e.response.status_code == 401:
                            st.error('Token inválido. Revisá las credenciales.')
                        else:
                            st.error(f'Error API: {e}')
                    except Exception as e:
                        st.error(f'Error: {e}')

            # ── TAB: Publicar producto ──
            with tab_publicar:
                st.subheader('Publicar producto del ERP en TiendaNube')
                st.markdown('Seleccioná un artículo del ERP para publicarlo en TiendaNube con precio calculado automáticamente.')

                conn_pub = get_db()
                if conn_pub:
                    # Buscar artículos del ERP con stock y sinonimo
                    sql_pub = """
                        SELECT TOP 200 a.codigo, a.codigo_sinonimo, a.descripcion_1, a.descripcion_2,
                            a.precio_costo, a.moneda,
                            m.descripcion as marca,
                            ISNULL((SELECT SUM(stock_actual) FROM msgestionC.dbo.stock
                                    WHERE articulo=a.codigo AND deposito IN (0,1)), 0) as stock_total
                        FROM msgestion01art.dbo.articulo a
                        LEFT JOIN msgestion01art.dbo.marcas m ON m.codigo=a.marca
                        WHERE a.estado IN ('V','U') AND a.precio_costo > 0
                        AND a.codigo_sinonimo IS NOT NULL AND a.codigo_sinonimo <> ''
                        AND ISNULL((SELECT SUM(stock_actual) FROM msgestionC.dbo.stock
                                    WHERE articulo=a.codigo AND deposito IN (0,1)), 0) > 0
                        ORDER BY a.codigo DESC
                    """
                    try:
                        df_pub = pd.read_sql(sql_pub, conn_pub)
                    except Exception as e:
                        st.error(f'Error SQL: {e}')
                        df_pub = pd.DataFrame()

                    if not df_pub.empty:
                        # Filtro de búsqueda
                        buscar = st.text_input('Buscar artículo por descripción o SKU', key='pub_buscar')
                        df_filtrado = df_pub
                        if buscar:
                            mask = df_filtrado.apply(
                                lambda row: buscar.lower() in
                                f"{row.get('descripcion_1','')} {row.get('descripcion_2','')} {row.get('codigo_sinonimo','')}".lower(),
                                axis=1
                            )
                            df_filtrado = df_filtrado[mask]

                        if not df_filtrado.empty:
                            codigo_pub = st.selectbox(
                                'Seleccionar artículo',
                                df_filtrado['codigo'].tolist(),
                                format_func=lambda x: (
                                    f"{x} — {df_filtrado[df_filtrado['codigo']==x].iloc[0]['descripcion_1']} "
                                    f"{df_filtrado[df_filtrado['codigo']==x].iloc[0].get('descripcion_2','')} "
                                    f"(SKU: {df_filtrado[df_filtrado['codigo']==x].iloc[0]['codigo_sinonimo']})"
                                ),
                                key='pub_sel'
                            )

                            if codigo_pub:
                                art = df_filtrado[df_filtrado['codigo'] == codigo_pub].iloc[0]
                                costo = float(art['precio_costo'])
                                stock = int(art['stock_total'])
                                sku = art['codigo_sinonimo']

                                # Calcular precio TN
                                from multicanal.precios import calcular_precio_canal, REGLAS_DEFAULT
                                regla_tn = st.session_state.reglas.get('tiendanube_pagonube') or st.session_state.reglas.get('tiendanube') or REGLAS_DEFAULT.get('tiendanube_pagonube')
                                precio_calc = calcular_precio_canal(costo, regla_tn)
                                precio_sugerido = precio_calc.get('precio_venta', 0)

                                st.info(f"**{art['descripcion_1']} {art.get('descripcion_2','')}** | "
                                        f"Marca: {art.get('marca','-')} | Costo: ${costo:,.0f} | Stock: {stock}")

                                # Buscar fotos en PostgreSQL
                                try:
                                    from multicanal.imagenes import buscar_imagenes_producto, url_publica
                                    fotos_pg = buscar_imagenes_producto(sku)
                                except Exception:
                                    fotos_pg = []

                                if fotos_pg:
                                    st.caption(f'{len(fotos_pg)} foto(s) encontrada(s) en catálogo')
                                    foto_urls = [url_publica(f) for f in fotos_pg[:8]]
                                    for fu in foto_urls:
                                        st.code(fu, language=None)
                                else:
                                    st.warning('Sin fotos en el catálogo para este SKU.')

                                st.divider()
                                col_p1, col_p2 = st.columns(2)

                                with col_p1:
                                    nombre_pub = st.text_input('Nombre del producto',
                                        value=f"{art['descripcion_1']} {art.get('descripcion_2','')}".strip(),
                                        key='pub_nombre')
                                    descripcion_pub = st.text_area('Descripción',
                                        value=f"{art['descripcion_1']} {art.get('descripcion_2','')}",
                                        height=100, key='pub_desc')

                                with col_p2:
                                    precio_pub = st.number_input('Precio de venta ($)',
                                        value=float(precio_sugerido), step=100.0, key='pub_precio')
                                    stock_pub = st.number_input('Stock a publicar',
                                        value=stock, min_value=0, step=1, key='pub_stock')
                                    sku_pub = st.text_input('SKU (codigo_sinonimo)', value=sku, key='pub_sku')

                                if precio_sugerido > 0:
                                    margen = precio_calc.get('margen_real', 0)
                                    ganancia = precio_calc.get('ganancia_neta', 0)
                                    st.caption(f'Precio sugerido: ${precio_sugerido:,.0f} '
                                              f'(margen {margen}%, ganancia ${ganancia:,.0f})')

                                st.divider()
                                if st.button('Publicar en TiendaNube', type='primary', key='btn_publicar'):
                                    if not nombre_pub or not sku_pub:
                                        st.error('Completá nombre y SKU.')
                                    elif precio_pub <= 0:
                                        st.error('El precio debe ser mayor a 0.')
                                    else:
                                        with st.spinner('Publicando en TiendaNube...'):
                                            try:
                                                kwargs_pub = {'descripcion': descripcion_pub}
                                                # Agregar imágenes si hay fotos
                                                if fotos_pg:
                                                    kwargs_pub['images'] = [
                                                        {'src': url_publica(f)}
                                                        for f in fotos_pg[:5]
                                                    ]
                                                resultado = tn.crear_producto(
                                                    nombre=nombre_pub,
                                                    variantes=[{
                                                        'price': str(precio_pub),
                                                        'stock': stock_pub,
                                                        'sku': sku_pub,
                                                    }],
                                                    **kwargs_pub,
                                                )
                                                prod_id = resultado.get('id', '')
                                                url = resultado.get('canonical_url', '')
                                                st.success(f'Producto publicado. ID: {prod_id}')
                                                if url:
                                                    st.markdown(f'[Ver en TiendaNube]({url})')
                                            except requests.exceptions.HTTPError as e:
                                                st.error(f'Error API TiendaNube: {e}')
                                            except Exception as e:
                                                st.error(f'Error: {e}')
                        else:
                            st.info('No se encontraron artículos con ese filtro.')
                    else:
                        st.warning('No hay artículos con stock y SKU en el ERP.')
                else:
                    st.warning('Sin conexión al ERP.')

            # ── TAB: Sync ERP ──
            with tab_sync:
                st.subheader('Vincular productos TN con ERP')
                st.markdown("""
                **Cómo funciona:**
                1. El campo `SKU` en Tienda Nube debe coincidir con `codigo_sinonimo` del ERP
                2. Cuando una orden se paga, el sistema busca el artículo por SKU y baja stock
                3. Los precios se calculan automáticamente con las reglas de canal configuradas
                """)

                conn = get_db()
                if conn:
                    st.markdown('---')
                    st.caption('Artículos del ERP con sinonimo (potencialmente vinculables)')
                    sql_vinc = """
                        SELECT TOP 100 a.codigo, a.codigo_sinonimo, a.descripcion_1,
                            a.precio_costo, a.moneda,
                            ISNULL((SELECT SUM(stock_actual) FROM msgestionC.dbo.stock WHERE articulo=a.codigo), 0) as stock_total
                        FROM msgestion01art.dbo.articulo a
                        WHERE a.estado IN ('V','U') AND a.precio_costo > 0
                        AND a.codigo_sinonimo IS NOT NULL AND a.codigo_sinonimo <> ''
                        AND ISNULL((SELECT SUM(stock_actual) FROM msgestionC.dbo.stock WHERE articulo=a.codigo), 0) > 0
                        ORDER BY a.codigo DESC
                    """
                    try:
                        df_erp = pd.read_sql(sql_vinc, conn)
                        st.dataframe(df_erp, use_container_width=True, hide_index=True)
                        st.caption(f'{len(df_erp)} artículos con stock y sinonimo')
                    except Exception as e:
                        st.error(f'Error SQL: {e}')
                else:
                    st.warning('Sin conexión al ERP.')

        except Exception as e:
            st.error(f'Error inicializando cliente TN: {e}')
    else:
        st.info('Configurá Store ID y Access Token en el sidebar para conectar con Tienda Nube.')
        st.markdown("""
        **Para obtener las credenciales:**
        1. Entrá a [partners.tiendanube.com](https://partners.tiendanube.com)
        2. Creá una app privada (nombre: "Calzalindo Sync")
        3. Permisos: `read_products`, `write_products`, `read_orders`, `write_orders`
        4. Instalala en tu tienda → te da `store_id` + `access_token`
        """)


# ══════════════════════════════════════════════════
# PÁGINA: Sincronización
# ══════════════════════════════════════════════════
elif pagina == '🔄 Sincronización':
    st.title('🔄 Sincronización ERP ↔ Canales')
    st.markdown('Ejecutá la sincronización de stock/precios y facturación automática.')

    from multicanal.tiendanube import cargar_config as tn_cargar_config
    tn_cfg = tn_cargar_config()

    has_tn = bool(tn_cfg.get('store_id') and tn_cfg.get('access_token'))

    from multicanal.facturador_ml import cargar_config as ml_cargar_config
    ml_cfg = ml_cargar_config()
    has_ml = bool(ml_cfg.get('access_token') and ml_cfg.get('user_id'))

    if not has_tn and not has_ml:
        st.warning('Configurá credenciales de TiendaNube o MercadoLibre primero.')
    else:
        tabs_nombres = ['Sync Stock TN', 'Sync Stock ML', 'Sync Precios', 'Facturar TN', 'Facturar ML']
        tab_stock, tab_stock_ml, tab_precios, tab_facturar, tab_facturar_ml = st.tabs(tabs_nombres)

        with tab_stock:
            st.subheader('Stock ERP → TiendaNube')
            st.markdown('Compara el stock real del ERP con lo publicado en TN y actualiza las diferencias.')

            def _ejecutar_sync_stock(dry_run_mode):
                with st.spinner('Sincronizando stock...'):
                    try:
                        from multicanal.sync_stock import sincronizar_stock
                        reporte = sincronizar_stock(dry_run=dry_run_mode, fuente='erp')
                        if reporte.get('error'):
                            st.error(reporte['error'])
                        else:
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric('Productos TN', reporte['total_productos'])
                            c2.metric('Variantes con SKU', reporte['total_variantes'])
                            c3.metric('Sin cambio', reporte['sin_cambio'])
                            c4.metric('Actualizados' if not dry_run_mode else 'A actualizar',
                                      len(reporte['actualizados']))

                            if reporte['actualizados']:
                                df_cambios = pd.DataFrame([{
                                    'SKU': a['sku'],
                                    'Producto': a['nombre'][:30],
                                    'Stock TN': a['stock_tn_anterior'],
                                    'Stock ERP': a['stock_nuevo'],
                                } for a in reporte['actualizados']])
                                st.dataframe(df_cambios, use_container_width=True, hide_index=True)

                            if not dry_run_mode and reporte['actualizados']:
                                st.success(f"{len(reporte['actualizados'])} variantes actualizadas en TiendaNube.")

                            if reporte['errores']:
                                for err in reporte['errores']:
                                    st.error(err)
                    except Exception as e:
                        st.error(f'Error: {e}')

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button('Dry run (solo ver cambios)', key='btn_sync_stock'):
                    _ejecutar_sync_stock(dry_run_mode=True)
            with col_btn2:
                confirmar_stock = st.checkbox('Confirmo que quiero actualizar stock en TN', key='conf_stock')
                if st.button('Ejecutar sync real', key='btn_sync_stock_real',
                             type='primary', disabled=not confirmar_stock):
                    _ejecutar_sync_stock(dry_run_mode=False)

        with tab_stock_ml:
            st.subheader('Stock ERP → MercadoLibre')
            st.markdown('Compara el stock real del ERP con lo publicado en ML y actualiza las diferencias.')

            if not has_ml:
                st.warning('Configurá credenciales de MercadoLibre primero.')
            else:
                def _ejecutar_sync_stock_ml(dry_run_mode):
                    with st.spinner('Sincronizando stock con ML...'):
                        try:
                            from multicanal.sync_stock_ml import sincronizar_stock_ml
                            reporte = sincronizar_stock_ml(dry_run=dry_run_mode)
                            if reporte.get('error'):
                                st.error(reporte['error'])
                            else:
                                c1, c2, c3, c4 = st.columns(4)
                                c1.metric('Items ML', reporte['total_items'])
                                c2.metric('Con SKU', reporte['total_con_sku'])
                                c3.metric('Sin cambio', reporte['sin_cambio'])
                                c4.metric('Actualizados' if not dry_run_mode else 'A actualizar',
                                          len(reporte['actualizados']))

                                if reporte['actualizados']:
                                    df_cambios = pd.DataFrame([{
                                        'SKU': a['sku'],
                                        'Título': a['titulo'][:30],
                                        'Stock ML': a['stock_ml_anterior'],
                                        'Stock ERP': a['stock_nuevo'],
                                    } for a in reporte['actualizados']])
                                    st.dataframe(df_cambios, use_container_width=True, hide_index=True)

                                if not dry_run_mode and reporte['actualizados']:
                                    st.success(f"{len(reporte['actualizados'])} items actualizados en MercadoLibre.")

                                if reporte['errores']:
                                    for err in reporte['errores']:
                                        st.error(err)
                        except Exception as e:
                            st.error(f'Error: {e}')

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button('Dry run (solo ver cambios)', key='btn_sync_stock_ml'):
                        _ejecutar_sync_stock_ml(dry_run_mode=True)
                with col_btn2:
                    confirmar_stock_ml = st.checkbox('Confirmo actualizar stock en ML', key='conf_stock_ml')
                    if st.button('Ejecutar sync real', key='btn_sync_stock_ml_real',
                                 type='primary', disabled=not confirmar_stock_ml):
                        _ejecutar_sync_stock_ml(dry_run_mode=False)

        with tab_precios:
            st.subheader('Precios ERP → TiendaNube')
            st.markdown('Calcula precios desde el costo ERP con la regla del canal TN y actualiza diferencias.')
            col_tol, col_usd = st.columns(2)
            with col_tol:
                tolerancia = st.slider('Tolerancia (%)', 0.0, 10.0, 2.0, 0.5,
                                       help='Ignora diferencias menores a este porcentaje')
            with col_usd:
                cotiz_usd_sync = st.number_input('Cotización USD ($)', value=1170.0, step=10.0,
                                                  key='cotiz_usd_sync',
                                                  help='Para artículos importados con costo en dólares')

            def _ejecutar_sync_precios(dry_run_mode):
                with st.spinner('Sincronizando precios...'):
                    try:
                        from multicanal.sync_precios import sincronizar_precios
                        reporte = sincronizar_precios(dry_run=dry_run_mode, tolerancia_pct=tolerancia,
                                                      cotiz_usd=cotiz_usd_sync, fuente='erp')
                        if reporte.get('error'):
                            st.error(reporte['error'])
                        else:
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric('Productos TN', reporte['total_productos'])
                            c2.metric('SKUs con costo', reporte['skus_con_costo'])
                            c3.metric('Sin cambio', reporte['sin_cambio'])
                            c4.metric('Actualizados' if not dry_run_mode else 'A actualizar',
                                      len(reporte['actualizados']))

                            if reporte['actualizados']:
                                df_precios = pd.DataFrame([{
                                    'SKU': a['sku'],
                                    'Producto': a['nombre'][:25],
                                    'Costo ERP': f"${a['costo_erp']:,.0f}",
                                    'Precio TN actual': f"${a['precio_tn_anterior']:,.0f}",
                                    'Precio correcto': f"${a['precio_correcto']:,.0f}",
                                    'Diferencia': f"{a['diferencia_pct']:+.1f}%",
                                    'Margen': f"{a['margen_real']}%",
                                } for a in reporte['actualizados']])
                                st.dataframe(df_precios, use_container_width=True, hide_index=True)

                            if not dry_run_mode and reporte['actualizados']:
                                st.success(f"{len(reporte['actualizados'])} precios actualizados en TiendaNube.")

                            if reporte['errores']:
                                for err in reporte['errores']:
                                    st.error(err)
                    except Exception as e:
                        st.error(f'Error: {e}')

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button('Dry run (solo ver cambios)', key='btn_sync_precios'):
                    _ejecutar_sync_precios(dry_run_mode=True)
            with col_btn2:
                confirmar_precios = st.checkbox('Confirmo que quiero actualizar precios en TN', key='conf_precios')
                if st.button('Ejecutar sync real', key='btn_sync_precios_real',
                             type='primary', disabled=not confirmar_precios):
                    _ejecutar_sync_precios(dry_run_mode=False)

        with tab_facturar:
            st.subheader('Facturar órdenes TiendaNube → ERP')
            st.markdown('Procesa órdenes pagadas de TN y las envía al POS 109 para registrar la venta y descontar stock en el ERP.')

            # ── Detectar tiendas TN configuradas ──
            import glob as _glob
            _configs_tn = _glob.glob(os.path.join(os.path.dirname(__file__), 'multicanal', 'tiendanube_config*.json'))
            _tiendas_disponibles = []
            for _cf in sorted(_configs_tn):
                _nombre = os.path.basename(_cf).replace('tiendanube_config_', '').replace('tiendanube_config', 'default').replace('.json', '')
                if _nombre == 'default':
                    _nombre = 'Calzalindo'
                _tiendas_disponibles.append(_nombre)
            if not _tiendas_disponibles:
                _tiendas_disponibles = ['Calzalindo']

            # ── Filtros Tier 1 ──
            col_f0, col_f1, col_f2, col_f3 = st.columns(4)
            with col_f0:
                tienda_sel = st.selectbox('Tienda TN', _tiendas_disponibles, key='tienda_tn',
                                           help='Seleccioná la tienda TiendaNube a facturar')
                # Mapear nombre a config
                _nombre_tienda = None if tienda_sel == 'Calzalindo' else tienda_sel.lower()
            with col_f1:
                dias_facturar = st.slider('Últimos N días', 1, 60, 7, key='dias_fact')
            with col_f2:
                empresa_tn = st.selectbox('Empresa destino', ['H4', 'ABI'], index=0, key='empresa_tn',
                                          help='H4 → msgestion03 | ABI → msgestion01 (CALZALINDO)')
            with col_f3:
                modo_facturar = st.selectbox('Modo', ['POS 109', 'Directo ERP'], index=0, key='modo_fact',
                                              help='POS 109: envía al endpoint del 109 (recomendado).')

            # ── Filtros Tier 2 (avanzados) ──
            with st.expander('Filtros avanzados'):
                col_fa1, col_fa2, col_fa3, col_fa4 = st.columns(4)
                with col_fa1:
                    filtro_estado = st.selectbox('Estado', ['Pendientes', 'Ya facturadas', 'Todas'], key='filtro_estado_tn')
                with col_fa2:
                    filtro_monto_min = st.number_input('Monto mínimo $', value=0, step=1000, key='filtro_monto_min')
                with col_fa3:
                    filtro_monto_max = st.number_input('Monto máximo $', value=0, step=1000, key='filtro_monto_max',
                                                        help='0 = sin límite')
                with col_fa4:
                    filtro_buscar = st.text_input('Buscar (cliente, SKU, #orden)', key='filtro_buscar_tn',
                                                   placeholder='ej: Rodolfo, 668296...')

            # ── Cargar órdenes ──
            @st.cache_data(ttl=60, show_spinner='Consultando TiendaNube...')
            def _cargar_ordenes_pendientes(dias, nombre_tienda=None):
                from multicanal.facturador_tn import (
                    orden_ya_procesada, buscar_articulos_por_sku, conectar_erp_art,
                    cargar_config_tienda,
                )
                from multicanal.tiendanube import TiendaNubeClient
                from datetime import datetime, timedelta

                tienda_key = nombre_tienda or 'default'
                cfg = cargar_config_tienda(nombre_tienda)
                if not cfg.get('store_id') or not cfg.get('access_token'):
                    return None, 'Sin config TiendaNube'

                client = TiendaNubeClient(store_id=cfg['store_id'], access_token=cfg['access_token'])
                fecha_min = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
                ordenes = client.listar_todas_ordenes(payment_status='paid', created_at_min=fecha_min)

                todos_skus = set()
                for o in ordenes:
                    for item in o.get('products', []):
                        sku = (item.get('sku') or '').strip()
                        if sku:
                            todos_skus.add(sku)

                articulos_erp = {}
                if todos_skus:
                    try:
                        conn_art = conectar_erp_art()
                        articulos_erp = buscar_articulos_por_sku(conn_art, list(todos_skus))
                        conn_art.close()
                    except Exception:
                        pass

                resultado = []
                for o in ordenes:
                    oid = str(o['id'])
                    ya = orden_ya_procesada(oid, tienda_key)
                    customer = o.get('customer', {})
                    nombre = (customer.get('name') or '').strip()
                    productos = o.get('products', [])
                    items_detalle = []
                    skus_ok = 0
                    skus_fail = 0
                    total = 0
                    for item in productos:
                        sku = (item.get('sku') or '').strip()
                        cant = int(item.get('quantity', 0))
                        precio = float(item.get('price', 0))
                        nombre_prod = (item.get('name') or '').strip()
                        en_erp = sku in articulos_erp
                        if en_erp:
                            skus_ok += 1
                        else:
                            skus_fail += 1
                        items_detalle.append({
                            'sku': sku or '(sin SKU)',
                            'producto': nombre_prod[:40],
                            'cantidad': cant,
                            'precio': precio,
                            'subtotal': round(precio * cant, 2),
                            'en_erp': en_erp,
                        })
                        total += precio * cant

                    # Validación: ¿se puede facturar?
                    facturable = skus_ok > 0  # al menos 1 producto matchea en ERP
                    problema = ''
                    if skus_fail > 0 and skus_ok == 0:
                        problema = 'Sin SKUs en ERP'
                    elif skus_fail > 0:
                        problema = f'{skus_fail} SKU(s) sin match'

                    resultado.append({
                        'order_id': o['id'],
                        'numero': o.get('number', o['id']),
                        'fecha': (o.get('created_at') or '')[:10],
                        'cliente': nombre,
                        'email': (customer.get('email') or ''),
                        'total': round(total, 2),
                        'items': len(productos),
                        'pares': sum(i['cantidad'] for i in items_detalle),
                        'estado_pago': o.get('payment_status', ''),
                        'estado_envio': o.get('shipping_status', ''),
                        'ya_procesada': ya,
                        'facturable': facturable,
                        'problema': problema,
                        'detalle': items_detalle,
                        'orden_raw': o,
                    })

                return resultado, None

            ordenes_preview, err_preview = _cargar_ordenes_pendientes(dias_facturar, _nombre_tienda)

            if err_preview:
                st.warning(err_preview)
            elif ordenes_preview is not None:

                # ── Aplicar filtros ──
                ordenes_filtradas = ordenes_preview.copy()

                if filtro_estado == 'Pendientes':
                    ordenes_filtradas = [o for o in ordenes_filtradas if not o['ya_procesada']]
                elif filtro_estado == 'Ya facturadas':
                    ordenes_filtradas = [o for o in ordenes_filtradas if o['ya_procesada']]

                if filtro_monto_min > 0:
                    ordenes_filtradas = [o for o in ordenes_filtradas if o['total'] >= filtro_monto_min]
                if filtro_monto_max > 0:
                    ordenes_filtradas = [o for o in ordenes_filtradas if o['total'] <= filtro_monto_max]

                if filtro_buscar.strip():
                    q = filtro_buscar.strip().lower()
                    ordenes_filtradas = [o for o in ordenes_filtradas if (
                        q in str(o['numero']).lower() or
                        q in o['cliente'].lower() or
                        q in o['email'].lower() or
                        any(q in i['sku'].lower() for i in o['detalle'])
                    )]

                # ── Métricas ──
                pendientes = [o for o in ordenes_preview if not o['ya_procesada']]
                procesadas_prev = [o for o in ordenes_preview if o['ya_procesada']]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric('Total órdenes', len(ordenes_preview))
                c2.metric('Ya facturadas', len(procesadas_prev))
                c3.metric('Pendientes', len(pendientes))
                c4.metric('Mostrando', len(ordenes_filtradas))

                if ordenes_filtradas:
                    # ── Tabla interactiva con checkboxes ──
                    df_tabla = pd.DataFrame([{
                        'Facturar': not o['ya_procesada'] and o['facturable'],
                        '#': o['numero'],
                        'Fecha': o['fecha'],
                        'Cliente': o['cliente'][:30],
                        'Pares': o['pares'],
                        'Total': o['total'],
                        'Items': o['items'],
                        'Envío': o['estado_envio'] or '-',
                        'ERP': 'OK' if o['facturable'] else 'FALTA',
                        'Estado': 'Facturada' if o['ya_procesada'] else ('Problema' if o['problema'] else 'Pendiente'),
                        'Nota': o['problema'] if o['problema'] else ('Ya procesada' if o['ya_procesada'] else ''),
                    } for o in ordenes_filtradas])

                    # Botones seleccionar/deseleccionar
                    col_sa1, col_sa2, col_sa3 = st.columns([1, 1, 4])
                    with col_sa1:
                        if st.button('Seleccionar facturables', key='btn_sel_all_tn'):
                            st.session_state['tn_select_all'] = True
                    with col_sa2:
                        if st.button('Deseleccionar todos', key='btn_desel_all_tn'):
                            st.session_state['tn_select_all'] = False

                    if st.session_state.get('tn_select_all') is True:
                        df_tabla['Facturar'] = df_tabla.apply(
                            lambda r: r['Estado'] == 'Pendiente' and r['ERP'] == 'OK', axis=1)
                        st.session_state['tn_select_all'] = None
                    elif st.session_state.get('tn_select_all') is False:
                        df_tabla['Facturar'] = False
                        st.session_state['tn_select_all'] = None

                    # Ordenamiento
                    col_sort1, col_sort2 = st.columns([2, 1])
                    with col_sort1:
                        sort_col = st.selectbox('Ordenar por', ['Fecha', 'Total', 'Pares', 'Cliente', '#'],
                                                 key='sort_col_tn', index=0)
                    with col_sort2:
                        sort_dir = st.radio('Orden', ['Desc', 'Asc'], horizontal=True, key='sort_dir_tn')

                    sort_map = {'Fecha': 'Fecha', 'Total': 'Total', 'Pares': 'Pares',
                                'Cliente': 'Cliente', '#': '#'}
                    df_tabla = df_tabla.sort_values(sort_map[sort_col], ascending=(sort_dir == 'Asc'))

                    edited_df = st.data_editor(
                        df_tabla,
                        column_config={
                            'Facturar': st.column_config.CheckboxColumn('Facturar', default=False),
                            'Total': st.column_config.NumberColumn('Total', format='$%,.0f'),
                            'Estado': st.column_config.TextColumn('Estado'),
                        },
                        disabled=['#', 'Fecha', 'Cliente', 'Pares', 'Total', 'Items', 'Envío',
                                  'ERP', 'Estado', 'Nota'],
                        hide_index=True,
                        use_container_width=True,
                        key='editor_ordenes_tn',
                    )

                    # ── Resumen de selección ──
                    seleccionadas = edited_df[edited_df['Facturar'] == True]
                    n_sel = len(seleccionadas)
                    total_sel = seleccionadas['Total'].sum() if n_sel > 0 else 0
                    pares_sel = int(seleccionadas['Pares'].sum()) if n_sel > 0 else 0

                    if n_sel > 0:
                        st.info(f"**{n_sel} orden(es) seleccionadas** — {pares_sel} pares — ${total_sel:,.0f} total")

                    # ── Detalle expandible de cada orden ──
                    with st.expander('Ver detalle de productos por orden'):
                        numeros_sel = set(seleccionadas['#'].tolist()) if n_sel > 0 else set()
                        for o in ordenes_filtradas:
                            if o['numero'] in numeros_sel or not numeros_sel:
                                emoji = 'Facturar' if o['numero'] in numeros_sel else ''
                                st.markdown(f"**#{o['numero']}** — {o['cliente']} — ${o['total']:,.0f} {emoji}")
                                df_det = pd.DataFrame(o['detalle'])
                                df_det['en_erp'] = df_det['en_erp'].map({True: 'OK', False: 'FALTA'})
                                df_det['precio'] = df_det['precio'].apply(lambda x: f"${x:,.0f}")
                                df_det['subtotal'] = df_det['subtotal'].apply(lambda x: f"${x:,.0f}")
                                df_det.columns = ['SKU', 'Producto', 'Cant', 'Precio', 'Subtotal', 'En ERP']
                                st.dataframe(df_det, use_container_width=True, hide_index=True)

                    st.divider()

                    # ── Acciones ──
                    def _facturar_seleccionadas(dry_run_mode):
                        nums_facturar = set(seleccionadas['#'].tolist())
                        ordenes_a_procesar = [o for o in ordenes_filtradas
                                              if o['numero'] in nums_facturar and not o['ya_procesada']]

                        if not ordenes_a_procesar:
                            st.warning('No hay órdenes seleccionadas para facturar.')
                            return

                        usar_directo = modo_facturar == 'Directo ERP'
                        modo_txt = 'DRY RUN' if dry_run_mode else 'REAL'

                        from multicanal.facturador_tn import (
                            construir_payload_109, enviar_venta_109, buscar_articulos_por_sku,
                            conectar_erp_art, registrar_orden_procesada, registrar_error,
                            orden_ya_procesada,
                        )

                        # Buscar artículos ERP para las órdenes seleccionadas
                        todos_skus = set()
                        for o in ordenes_a_procesar:
                            for item in o['orden_raw'].get('products', []):
                                sku = (item.get('sku') or '').strip()
                                if sku:
                                    todos_skus.add(sku)

                        articulos_erp = {}
                        if todos_skus:
                            try:
                                conn_art = conectar_erp_art()
                                articulos_erp = buscar_articulos_por_sku(conn_art, list(todos_skus))
                                conn_art.close()
                            except Exception as e:
                                st.error(f'Error conectando al ERP: {e}')
                                return

                        resultados = []
                        with st.status(f'Procesando {len(ordenes_a_procesar)} órdenes [{modo_txt}]...', expanded=True) as status:
                            for i, o in enumerate(ordenes_a_procesar):
                                orden_raw = o['orden_raw']
                                order_id = str(o['order_id'])
                                order_number = o['numero']

                                # Doble-check dedup
                                if orden_ya_procesada(order_id, (_nombre_tienda or 'default')):
                                    st.write(f"⏭️ #{order_number} — ya procesada, salteo")
                                    continue

                                payload = construir_payload_109(orden_raw, articulos_erp)

                                if not payload['productos']:
                                    st.write(f"⚠️ #{order_number} — sin productos válidos en ERP")
                                    resultados.append({'order': order_number, 'status': 'skip', 'message': 'Sin SKUs en ERP'})
                                    continue

                                total_orden = sum(p['precio'] * p['cantidad'] for p in payload['productos'])
                                renglones = len(payload['productos'])

                                if dry_run_mode:
                                    st.write(f"🔍 #{order_number} — {o['cliente'][:25]} — "
                                             f"{renglones} items — ${total_orden:,.0f}")
                                    resultados.append({'order': order_number, 'status': 'ok',
                                                       'message': f'DRY: ${total_orden:,.0f}'})
                                else:
                                    try:
                                        resp = enviar_venta_109(orden_raw, articulos_erp)
                                        if resp and 'error' in resp:
                                            raise Exception(resp['error'])

                                        registrar_orden_procesada(
                                            order_id=order_id, order_number=order_number,
                                            tienda=(_nombre_tienda or 'default'), fecha_orden=o['fecha'],
                                            cliente=o['cliente'], total=total_orden,
                                            renglones=renglones, payload=payload,
                                            respuesta_109=resp,
                                        )
                                        st.write(f"✅ #{order_number} — {o['cliente'][:25]} — ${total_orden:,.0f}")
                                        resultados.append({'order': order_number, 'status': 'ok',
                                                           'message': f'Facturada ${total_orden:,.0f}'})
                                    except Exception as e:
                                        st.write(f"❌ #{order_number} — {e}")
                                        registrar_error(order_id, order_number, (_nombre_tienda or 'default'), str(e), payload)
                                        resultados.append({'order': order_number, 'status': 'error',
                                                           'message': str(e)})

                            # Resumen final
                            ok = [r for r in resultados if r['status'] == 'ok']
                            errors = [r for r in resultados if r['status'] == 'error']
                            skips = [r for r in resultados if r['status'] == 'skip']

                            if dry_run_mode:
                                total_dry = sum(float(r['message'].replace('DRY: $', '').replace(',', ''))
                                               for r in ok if r['message'].startswith('DRY'))
                                status.update(label=f'DRY RUN: {len(ok)} facturables, ${total_dry:,.0f}', state='complete')
                            elif errors:
                                status.update(label=f'{len(ok)} OK, {len(errors)} errores, {len(skips)} salteos',
                                              state='error')
                            else:
                                status.update(label=f'{len(ok)} órdenes facturadas correctamente', state='complete')

                        if not dry_run_mode and ok:
                            _cargar_ordenes_pendientes.clear()

                        # Retry de errores
                        if errors and not dry_run_mode:
                            st.warning(f'{len(errors)} orden(es) con error:')
                            for e in errors:
                                st.markdown(f"- **#{e['order']}**: {e['message']}")

                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.button('Dry run seleccionadas', key='btn_dry_tn', disabled=n_sel == 0):
                            _facturar_seleccionadas(dry_run_mode=True)
                    with col_btn2:
                        confirmar_fact = st.checkbox(f'Confirmo facturar {n_sel} orden(es)', key='conf_facturar')
                        if st.button('Facturar seleccionadas', key='btn_fact_real_tn',
                                     type='primary', disabled=not confirmar_fact or n_sel == 0):
                            _facturar_seleccionadas(dry_run_mode=False)
                    with col_btn3:
                        if n_sel > 0:
                            csv_export = seleccionadas.to_csv(index=False).encode('utf-8')
                            st.download_button('Exportar CSV', csv_export, 'ordenes_tn.csv', 'text/csv')

                else:
                    st.success('No hay órdenes con esos filtros.')

                # ── Historial facturadas ──
                if procesadas_prev:
                    with st.expander(f'Ya facturadas ({len(procesadas_prev)})'):
                        df_ya = pd.DataFrame([{
                            'Orden': o['numero'],
                            'Fecha': o['fecha'],
                            'Cliente': o['cliente'][:25],
                            'Total': f"${o['total']:,.0f}",
                        } for o in procesadas_prev])
                        st.dataframe(df_ya, use_container_width=True, hide_index=True)

            st.divider()

            # Historial de errores TN
            with st.expander('Historial de errores TN'):
                try:
                    from multicanal.facturador_tn import listar_errores
                    errores_tn = listar_errores(limit=20)
                    if errores_tn:
                        df_err = pd.DataFrame(errores_tn)
                        st.dataframe(df_err, use_container_width=True, hide_index=True)
                    else:
                        st.info('Sin errores registrados.')
                except Exception as e:
                    st.caption(f'No se pudo cargar historial: {e}')

        with tab_facturar_ml:
            st.subheader('Facturar órdenes MercadoLibre → ERP')
            st.markdown('Procesa órdenes pagadas de ML e inserta facturas B en el ERP (depósito 1).')

            # ── Detectar cuentas ML configuradas ──
            try:
                from multicanal.facturador_ml import listar_cuentas_ml, CUENTAS_ML
                _cuentas_ml = listar_cuentas_ml()
                _opciones_ml = []
                for _key, _name, _uid in _cuentas_ml:
                    desc = CUENTAS_ML.get(_name, {}).get('descripcion', _name)
                    _opciones_ml.append(f"{desc} ({_uid})")
                has_ml = len(_cuentas_ml) > 0
            except Exception:
                _cuentas_ml = []
                _opciones_ml = []

            if not has_ml:
                st.warning('Configurá las credenciales de MercadoLibre.')
                st.markdown("""
                **Para configurar:**
                1. Obtener `access_token` de ML (OAuth2)
                2. Obtener `user_id` de tu cuenta vendedor
                3. Guardar en `multicanal/mercadolibre_config.json`:
                ```json
                {"access_token": "APP_USR-...", "user_id": "123456789"}
                ```
                """)
                with st.expander('Configurar credenciales ML'):
                    ml_token = st.text_input('Access Token ML', type='password', key='ml_token')
                    ml_user = st.text_input('User ID ML', key='ml_user')
                    if st.button('Guardar credenciales ML', key='btn_save_ml'):
                        if ml_token and ml_user:
                            from multicanal.facturador_ml import guardar_config as ml_guardar_config
                            ml_guardar_config(ml_token, ml_user)
                            st.success('Credenciales ML guardadas.')
                            st.rerun()
            else:
                col_ml0, col_ml1, col_ml2 = st.columns(3)
                with col_ml0:
                    cuenta_ml_sel = st.selectbox('Cuenta ML', _opciones_ml, key='cuenta_ml_sel')
                    # Mapear selección a account key
                    _idx_ml = _opciones_ml.index(cuenta_ml_sel) if cuenta_ml_sel in _opciones_ml else 0
                    _account_key = _cuentas_ml[_idx_ml][0] if _cuentas_ml else None
                    _account_ml = None if _account_key == 'default' else _account_key
                with col_ml1:
                    dias_facturar_ml = st.slider('Últimos N días', 1, 30, 7, key='dias_fact_ml')
                with col_ml2:
                    # Auto-seleccionar empresa según cuenta
                    _empresa_default = CUENTAS_ML.get(_cuentas_ml[_idx_ml][1] if _cuentas_ml else '', {}).get('empresa', 'H4')
                    _emp_idx = 0 if _empresa_default == 'H4' else 1
                    empresa_ml = st.selectbox('Empresa destino', ['H4', 'ABI'], index=_emp_idx, key='empresa_ml',
                                              help='H4 → msgestion03 | ABI → msgestion01')

                def _ejecutar_facturacion_ml(dry_run_mode):
                    with st.spinner('Procesando órdenes ML...'):
                        try:
                            from multicanal.facturador_ml import sincronizar_ordenes_ml
                            reporte = sincronizar_ordenes_ml(dry_run=dry_run_mode, dias_atras=dias_facturar_ml,
                                                              empresa=empresa_ml, account=_account_ml)
                            if reporte.get('error'):
                                st.error(reporte['error'])
                            else:
                                c1, c2, c3 = st.columns(3)
                                c1.metric('Órdenes encontradas', reporte['ordenes_encontradas'])
                                c2.metric('Ya procesadas', reporte['ya_procesadas'])
                                procesadas = reporte.get('procesadas', [])
                                n_proc = len(procesadas) if isinstance(procesadas, list) else 0
                                c3.metric('Facturadas' if not dry_run_mode else 'Nuevas a facturar', n_proc)

                                if isinstance(procesadas, list) and procesadas:
                                    df_ml = pd.DataFrame([{
                                        'Orden ML': p['order_id'],
                                        'Fecha': p['fecha'],
                                        'Cliente': p['cliente'][:25],
                                        'Items': p['renglones'],
                                        'Total': f"${p['total']:,.0f}",
                                        **({"Factura": f"B {p.get('numero_factura', '-')}"} if not dry_run_mode else {}),
                                    } for p in procesadas])
                                    st.dataframe(df_ml, use_container_width=True, hide_index=True)

                                if not dry_run_mode and n_proc > 0:
                                    total_fact = sum(p['total'] for p in procesadas)
                                    st.success(f"{n_proc} órdenes ML facturadas. Total: ${total_fact:,.0f}")

                                if reporte.get('errores'):
                                    for err in reporte['errores']:
                                        st.error(err)
                        except Exception as e:
                            st.error(f'Error: {e}')

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button('Dry run (solo ver)', key='btn_facturar_ml'):
                        _ejecutar_facturacion_ml(dry_run_mode=True)
                with col_btn2:
                    confirmar_ml = st.checkbox('Confirmo insertar facturas ML en el ERP', key='conf_facturar_ml')
                    if st.button('Facturar real', key='btn_facturar_ml_real',
                                 type='primary', disabled=not confirmar_ml):
                        _ejecutar_facturacion_ml(dry_run_mode=False)

                # Historial de errores ML
                with st.expander('Historial de errores ML'):
                    try:
                        from multicanal.facturador_ml import listar_errores_ml
                        errores_ml = listar_errores_ml(limit=20)
                        if errores_ml:
                            df_err_ml = pd.DataFrame(errores_ml)
                            st.dataframe(df_err_ml, use_container_width=True, hide_index=True)
                        else:
                            st.info('Sin errores registrados.')
                    except Exception as e:
                        st.caption(f'No se pudo cargar historial: {e}')


# ══════════════════════════════════════════════════
# PÁGINA: Simulador de precios
# ══════════════════════════════════════════════════
elif pagina == '💰 Simulador de precios':
    st.title('💰 Simulador de precios por canal')
    st.markdown('Calculá el precio óptimo para cada canal según costo, margen y comisiones.')

    reglas = st.session_state.reglas

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader('Parámetros')
        precio_costo = st.number_input('Precio de costo ($)', value=30000.0, step=500.0, min_value=0.0)
        margen_global = st.slider('Margen objetivo global (%)', 10, 70, 40) / 100.0

        st.markdown('---')
        st.caption('Ajustar margen individual por canal:')
        margenes_custom = {}
        for nombre, regla in reglas.items():
            if regla.activo:
                margenes_custom[nombre] = st.slider(
                    f'{regla.descripcion}',
                    10, 70,
                    int(regla.margen_objetivo * 100),
                    key=f'margen_{nombre}'
                ) / 100.0

    with col2:
        st.subheader('Resultado por canal')

        if precio_costo > 0:
            resultados = []
            for nombre, regla in reglas.items():
                if not regla.activo:
                    continue
                regla_custom = ReglaCanal(
                    canal=regla.canal,
                    descripcion=regla.descripcion,
                    comision=regla.comision,
                    comision_pago=regla.comision_pago,
                    iva_comision=getattr(regla, 'iva_comision', 0.21),
                    envio_pct=getattr(regla, 'envio_pct', 0.0),
                    retenciones_pct=getattr(regla, 'retenciones_pct', 0.0),
                    margen_objetivo=margenes_custom.get(nombre, margen_global),
                    recargo=regla.recargo,
                    redondeo=regla.redondeo,
                )
                res = calcular_precio_canal(precio_costo, regla_custom)
                if 'error' not in res:
                    resultados.append(res | {'canal': nombre, 'canal_desc': regla.descripcion})

            if resultados:
                for r in resultados:
                    with st.container(border=True):
                        c1, c2, c3, c4, c5 = st.columns(5)
                        c1.metric(r['canal_desc'], f"${r['precio_venta']:,.0f}")
                        c2.metric('Margen neto', f"{r['margen_real']}%")
                        c3.metric('En mano', f"{r['margen_en_mano']}%")
                        c4.metric('Ganancia', f"${r['ganancia_neta']:,.0f}")
                        c5.metric('Costos total', f"${r['total_costos']:,.0f}")

                st.divider()
                st.subheader('Comparativa detallada')
                df_comp = pd.DataFrame([{
                    'Canal': r['canal_desc'],
                    'Costo': f"${precio_costo:,.0f}",
                    'PVP c/IVA': f"${r['precio_venta']:,.0f}",
                    'P.Neto': f"${r['precio_neto']:,.0f}",
                    'Comisiones': f"${r['comision_plataforma'] + r['comision_pago']:,.0f}",
                    'IVA s/com.': f"${r['iva_sobre_comisiones']:,.0f}",
                    'Envío': f"${r['costo_envio']:,.0f}",
                    'Retenc.': f"${r['retenciones']:,.0f}",
                    'Ganancia': f"${r['ganancia_neta']:,.0f}",
                    'Margen': f"{r['margen_real']}%",
                    'En mano': f"{r['margen_en_mano']}%",
                } for r in resultados])
                st.dataframe(df_comp, use_container_width=True, hide_index=True)

                # Gráfico de barras
                df_chart = pd.DataFrame([{
                    'Canal': r['canal_desc'],
                    'Ganancia': r['ganancia_neta'],
                    'Costos': r['total_costos'],
                    'Retenciones': r['retenciones'],
                } for r in resultados]).set_index('Canal')
                st.bar_chart(df_chart)
        else:
            st.info('Ingresá un precio de costo mayor a 0.')


# ══════════════════════════════════════════════════
# PÁGINA: Configurar canales
# ══════════════════════════════════════════════════
elif pagina == '⚙️ Configurar canales':
    st.title('⚙️ Configuración de canales')
    st.markdown('Ajustá las comisiones y reglas de pricing para cada canal.')

    reglas = st.session_state.reglas

    for nombre, regla in reglas.items():
        with st.expander(f"{'🟢' if regla.activo else '🔴'} {regla.descripcion}", expanded=regla.activo):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                regla.activo = st.checkbox('Activo', value=regla.activo, key=f'act_{nombre}')
                regla.comision = st.number_input('Comisión plataforma (%)', value=regla.comision * 100,
                                                  step=0.5, key=f'com_{nombre}') / 100
                regla.comision_pago = st.number_input('Comisión pago (%)', value=regla.comision_pago * 100,
                                                       step=0.5, key=f'comp_{nombre}') / 100
            with col2:
                regla.margen_objetivo = st.number_input('Margen objetivo (%)', value=regla.margen_objetivo * 100,
                                                         step=1.0, key=f'mar_{nombre}') / 100
                regla.recargo = st.number_input('Recargo adicional (%)', value=regla.recargo * 100,
                                                 step=0.5, key=f'rec_{nombre}') / 100
                regla.redondeo = st.number_input('Redondeo ($)', value=regla.redondeo,
                                                  step=10, key=f'red_{nombre}')
            with col3:
                iva_com = getattr(regla, 'iva_comision', 0.21)
                envio = getattr(regla, 'envio_pct', 0.0)
                retenc = getattr(regla, 'retenciones_pct', 0.0)
                regla.iva_comision = st.number_input('IVA s/comisiones (%)', value=iva_com * 100,
                                                      step=1.0, key=f'ivac_{nombre}') / 100
                regla.envio_pct = st.number_input('Costo envío (%)', value=envio * 100,
                                                    step=0.5, key=f'env_{nombre}') / 100
                regla.retenciones_pct = st.number_input('Retenciones (%)', value=retenc * 100,
                                                          step=0.5, key=f'ret_{nombre}') / 100
            with col4:
                regla.precio_minimo = st.number_input('Precio mínimo ($)', value=regla.precio_minimo,
                                                       step=1000.0, key=f'min_{nombre}')
                regla.notas = st.text_area('Notas', value=regla.notas, key=f'not_{nombre}', height=80)

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button('💾 Guardar configuración', type='primary'):
            guardar_reglas(reglas, REGLAS_FILE)
            st.success('Configuración guardada en %s' % REGLAS_FILE)
    with col_b:
        if st.button('🔄 Restaurar defaults'):
            st.session_state.reglas = {k: ReglaCanal(**{**v.__dict__}) for k, v in REGLAS_DEFAULT.items()}
            st.rerun()


# ══════════════════════════════════════════════════
# PÁGINA: Catálogo ERP
# ══════════════════════════════════════════════════
elif pagina == '📦 Catálogo ERP':
    st.title('📦 Catálogo del ERP — Buscador de artículos')
    st.markdown('Buscá artículos por cualquier campo y revisá el pricing multicanal con costo actualizado.')

    conn = get_db()
    if conn:
        # ── Cargar listas para filtros (cacheado) ──
        @st.cache_data(ttl=300)
        def _cargar_listas_filtro(_conn):
            marcas = pd.read_sql("SELECT DISTINCT descripcion FROM msgestion01art.dbo.marcas WHERE descripcion IS NOT NULL AND descripcion <> '' ORDER BY descripcion", _conn)
            grupos = pd.read_sql("SELECT DISTINCT descripcion FROM msgestion01art.dbo.grupos WHERE descripcion IS NOT NULL AND descripcion <> '' ORDER BY descripcion", _conn)
            rubros = pd.read_sql("SELECT DISTINCT descripcion FROM msgestion01art.dbo.rubros WHERE descripcion IS NOT NULL AND descripcion <> '' ORDER BY descripcion", _conn)
            proveedores = pd.read_sql("SELECT DISTINCT denominacion FROM msgestion01art.dbo.proveedores WHERE denominacion IS NOT NULL AND denominacion <> '' ORDER BY denominacion", _conn)
            subrubros = pd.read_sql("SELECT DISTINCT subrubro FROM msgestion01art.dbo.articulo WHERE estado IN ('V','U') AND subrubro IS NOT NULL AND subrubro > 0 ORDER BY subrubro", _conn)
            lineas = pd.read_sql("SELECT codigo, descripcion FROM msgestion03.dbo.lineas ORDER BY codigo", _conn)
            return marcas, grupos, rubros, proveedores, subrubros, lineas

        try:
            lst_marcas, lst_grupos, lst_rubros, lst_proveedores, lst_subrubros, lst_lineas = _cargar_listas_filtro(conn)
        except Exception:
            lst_marcas = lst_grupos = lst_rubros = lst_proveedores = lst_subrubros = lst_lineas = pd.DataFrame()

        # ── Buscador ──
        st.subheader('Buscar artículos')
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            busq_texto = st.text_input('Descripción (busca en desc 1, 2 y 3)', placeholder='ej: running, bota, sandalia')
        with col_b2:
            busq_marca = st.multiselect('Marca', lst_marcas['descripcion'].tolist() if not lst_marcas.empty else [])
        with col_b3:
            busq_codigo = st.text_input('Código / Sinónimo / Barra', placeholder='ej: 310611, 668296810035')

        col_b4, col_b5, col_b6 = st.columns(3)
        with col_b4:
            busq_grupo = st.multiselect('Grupo', lst_grupos['descripcion'].tolist() if not lst_grupos.empty else [])
        with col_b5:
            busq_rubro = st.multiselect('Rubro', lst_rubros['descripcion'].tolist() if not lst_rubros.empty else [])
        with col_b6:
            busq_proveedor = st.multiselect('Proveedor', lst_proveedores['denominacion'].tolist() if not lst_proveedores.empty else [])

        col_b7, col_b8, col_b9, col_b10 = st.columns(4)
        with col_b7:
            busq_subrubro = st.multiselect('Subrubro', [int(x) for x in lst_subrubros['subrubro'].tolist()] if not lst_subrubros.empty else [])
        with col_b8:
            linea_opciones = {f"{int(row['codigo'])} - {row['descripcion']}": int(row['codigo']) for _, row in lst_lineas.iterrows()} if not lst_lineas.empty else {}
            busq_linea_labels = st.multiselect('Línea', list(linea_opciones.keys()))
            busq_linea = [linea_opciones[l] for l in busq_linea_labels]
        with col_b9:
            busq_limite = st.number_input('Máx resultados', value=100, min_value=10, max_value=500, step=50)
        with col_b10:
            cotiz_usd_cat = st.number_input('Cotización USD (para costo CER)', value=1170.0, step=10.0, key='cotiz_cat')

        if st.button('Buscar', type='primary', key='btn_buscar_catalogo'):
            # Armar WHERE dinámico
            condiciones = ["a.estado IN ('V', 'U')", "a.precio_costo > 0"]
            params = []

            if busq_texto:
                palabras = busq_texto.strip().split()
                for p in palabras:
                    condiciones.append("(a.descripcion_1 + ' ' + ISNULL(a.descripcion_2,'') + ' ' + ISNULL(a.descripcion_3,'')) LIKE ?")
                    params.append(f'%{p}%')

            if busq_marca:
                placeholders = ",".join(["?"] * len(busq_marca))
                condiciones.append(f"m.descripcion IN ({placeholders})")
                params.extend(busq_marca)

            if busq_codigo:
                cod = busq_codigo.strip()
                condiciones.append("(CAST(a.codigo AS VARCHAR) = ? OR a.codigo_sinonimo LIKE ? OR a.codigo_barra LIKE ?)")
                params.extend([cod, f'%{cod}%', f'%{cod}%'])

            if busq_grupo:
                placeholders = ",".join(["?"] * len(busq_grupo))
                condiciones.append(f"g.descripcion IN ({placeholders})")
                params.extend(busq_grupo)

            if busq_rubro:
                placeholders = ",".join(["?"] * len(busq_rubro))
                condiciones.append(f"r.descripcion IN ({placeholders})")
                params.extend(busq_rubro)

            if busq_proveedor:
                placeholders = ",".join(["?"] * len(busq_proveedor))
                condiciones.append(f"p.denominacion IN ({placeholders})")
                params.extend(busq_proveedor)

            if busq_subrubro:
                placeholders = ",".join(["?"] * len(busq_subrubro))
                condiciones.append(f"a.subrubro IN ({placeholders})")
                params.extend(busq_subrubro)

            if busq_linea:
                placeholders = ",".join(["?"] * len(busq_linea))
                condiciones.append(f"a.linea IN ({placeholders})")
                params.extend(busq_linea)

            where_clause = " AND ".join(condiciones)

            sql_buscar = f"""
                SELECT TOP {int(busq_limite)}
                    a.codigo,
                    a.codigo_sinonimo as sinonimo,
                    a.codigo_barra as barra,
                    a.descripcion_1,
                    ISNULL(a.descripcion_2,'') as descripcion_2,
                    m.descripcion as marca,
                    p.denominacion as proveedor,
                    g.descripcion as grupo,
                    r.descripcion as rubro,
                    a.subrubro,
                    ISNULL(li.descripcion, CAST(a.linea AS VARCHAR)) as linea,
                    a.precio_costo as costo_historico,
                    a.moneda,
                    CASE WHEN a.moneda = 1
                         THEN ROUND(a.precio_costo * {cotiz_usd_cat}, 0)
                         ELSE a.precio_costo END as costo_cer,
                    ISNULL((SELECT SUM(stock_actual) FROM msgestionC.dbo.stock
                            WHERE articulo=a.codigo AND deposito IN (0,1)), 0) as stock_total,
                    ISNULL((SELECT stock_actual FROM msgestion01.dbo.stock
                            WHERE articulo=a.codigo AND deposito=1), 0) as stock_d1,
                    ISNULL((SELECT stock_actual FROM msgestion03.dbo.stock
                            WHERE articulo=a.codigo AND deposito=1), 0) as stock_h4
                FROM msgestion01art.dbo.articulo a
                LEFT JOIN msgestion01art.dbo.marcas m ON m.codigo=a.marca
                LEFT JOIN msgestion01art.dbo.grupos g ON g.codigo=a.grupo
                LEFT JOIN msgestion01art.dbo.rubros r ON r.codigo=a.rubro
                LEFT JOIN msgestion01art.dbo.proveedores p ON p.numero=a.proveedor
                LEFT JOIN msgestion03.dbo.lineas li ON li.codigo=a.linea
                WHERE {where_clause}
                ORDER BY a.codigo DESC
            """

            try:
                df_cat = pd.read_sql(sql_buscar, conn, params=params)
                st.session_state['catalogo_resultado'] = df_cat
            except Exception as e:
                st.error(f"Error en búsqueda: {e}")

        # ── Mostrar resultados ──
        if 'catalogo_resultado' in st.session_state and not st.session_state['catalogo_resultado'].empty:
            df_cat = st.session_state['catalogo_resultado']
            st.success(f"{len(df_cat)} artículos encontrados")

            # Tabla principal
            cols_mostrar = ['codigo', 'sinonimo', 'descripcion_1', 'descripcion_2', 'marca',
                           'proveedor', 'grupo', 'rubro', 'costo_historico', 'moneda', 'costo_cer',
                           'stock_total', 'stock_d1', 'stock_h4']
            cols_disponibles = [c for c in cols_mostrar if c in df_cat.columns]
            st.dataframe(df_cat[cols_disponibles], use_container_width=True, hide_index=True)

            st.divider()

            # ── Pricing multicanal para artículo seleccionado ──
            st.subheader('Pricing multicanal para un artículo')
            opciones = df_cat.apply(
                lambda r: f"{int(r['codigo'])} — {r['descripcion_1']} {r.get('descripcion_2','')} [{r.get('marca','')}]", axis=1
            ).tolist()
            idx_sel = st.selectbox('Seleccionar artículo', range(len(opciones)), format_func=lambda i: opciones[i])

            if idx_sel is not None:
                art = df_cat.iloc[idx_sel]
                costo_hist = float(art['costo_historico'])
                costo_cer = float(art['costo_cer'])
                moneda_txt = 'USD' if art['moneda'] == 1 else 'ARS'

                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.metric('Costo histórico ERP', f"${costo_hist:,.0f} {moneda_txt}")
                with col_c2:
                    st.metric('Costo CER (actualizado)', f"${costo_cer:,.0f} ARS")

                # Permitir ajustar costo manualmente
                costo_usar = st.number_input('Costo a usar para pricing ($)', value=costo_cer, step=500.0, key='costo_pricing')

                st.info(f"**{art['descripcion_1']} {art.get('descripcion_2','')}** | "
                        f"Marca: {art.get('marca','-')} | Proveedor: {art.get('proveedor','-')} | "
                        f"Stock total: {art['stock_total']} (D1: {art['stock_d1']}, H4: {art['stock_h4']})")

                # ── Fotos del producto ──
                sinonimo_art = str(art.get('sinonimo', '')).strip()
                if sinonimo_art and len(sinonimo_art) >= 8:
                    try:
                        from multicanal.imagenes import buscar_imagenes_producto, url_publica
                        fotos = buscar_imagenes_producto(sinonimo_art)
                        if fotos:
                            st.caption(f"{len(fotos)} foto(s) encontrada(s)")
                            cols_foto = st.columns(min(len(fotos), 5))
                            for i, foto in enumerate(fotos[:5]):
                                with cols_foto[i]:
                                    st.image(url_publica(foto), use_container_width=True)
                        else:
                            st.caption("Sin fotos en el catálogo de imágenes")
                    except Exception as e:
                        st.caption(f"Fotos no disponibles: {e}")

                resultados = calcular_todos_los_canales(costo_usar, st.session_state.reglas)
                df_precios = pd.DataFrame([{
                    'Canal': r['canal_descripcion'],
                    'PVP c/IVA': f"${r['precio_venta']:,.0f}",
                    'P.Neto': f"${r['precio_neto']:,.0f}",
                    'Margen': f"{r['margen_real']}%",
                    'En mano': f"{r['margen_en_mano']}%",
                    'Ganancia': f"${r['ganancia_neta']:,.0f}",
                    'Costos': f"${r['total_costos']:,.0f}",
                    'Envío': f"${r['costo_envio']:,.0f}",
                    'Retenc.': f"${r['retenciones']:,.0f}",
                } for r in resultados.values() if 'error' not in r])
                st.dataframe(df_precios, use_container_width=True, hide_index=True)

                # Desglose detallado del canal con más costos (ML Premium)
                ml_prem = resultados.get('mercadolibre_premium')
                if ml_prem and 'error' not in ml_prem:
                    with st.expander('Desglose ML Premium'):
                        for k, v in ml_prem.get('desglose', {}).items():
                            st.text(f"  {k}: {v}")

        elif 'catalogo_resultado' in st.session_state:
            st.warning('No se encontraron artículos con esos filtros.')
    else:
        st.error('No hay conexión a SQL Server. Verificá VPN y credenciales.')
