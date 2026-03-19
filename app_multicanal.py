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
                'Precio venta': f"${r['precio_venta']:,.0f}",
                'Margen real': f"{r['margen_real']}%",
                'Ganancia $': f"${r['ganancia_neta']:,.0f}",
                'Comisión plat.': f"${r['comision_plataforma']:,.0f}",
                'Comisión pago': f"${r['comision_pago']:,.0f}",
                'Ingreso neto': f"${r['ingreso_neto']:,.0f}",
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
                SUM(v1.cantidad * ({costo_pesos})) as costo_total,
                CASE WHEN SUM(v1.total_item) > 0
                    THEN ROUND((SUM(v1.total_item) - SUM(v1.cantidad * ({costo_pesos}))) / SUM(v1.total_item) * 100, 1)
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
            total_pares = df_mensual['pares'].sum()
            total_costo = df_mensual['costo_total'].sum()
            margen_global = round((total_fact - total_costo) / total_fact * 100, 1) if total_fact > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric('Facturación total', f"${total_fact:,.0f}")
            c2.metric('Pares vendidos', f"{total_pares:,.0f}")
            c3.metric('Margen bruto', f"{margen_global}%")
            c4.metric('Margen neto ML', f"{margen_global - comision_ml*100:.1f}%")

            st.divider()

            # Tabla mensual
            st.subheader('Evolución mensual')
            df_show = df_mensual.copy()
            df_show.columns = ['Mes', 'Facturas', 'Pares', 'Facturación', 'Costo', 'Margen bruto %', 'Margen neto ML %', 'Ticket prom']
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
                        WHEN v1.precio / ({costo_pesos}) < 1.5 THEN '2. BAJO (<1.5x)'
                        WHEN v1.precio / ({costo_pesos}) < 2.0 THEN '3. AJUSTADO (1.5-2x)'
                        WHEN v1.precio / ({costo_pesos}) < 2.5 THEN '4. NORMAL (2-2.5x)'
                        WHEN v1.precio / ({costo_pesos}) < 3.0 THEN '5. BUENO (2.5-3x)'
                        ELSE '6. ALTO (3x+)'
                    END as rango,
                    COUNT(*) as ventas,
                    SUM(v1.cantidad) as pares,
                    SUM(v1.total_item) as facturacion,
                    ROUND(AVG(v1.precio), 0) as pvta_prom,
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
                    WHEN v1.precio / ({costo_pesos}) < 1.5 THEN '2. BAJO (<1.5x)'
                    WHEN v1.precio / ({costo_pesos}) < 2.0 THEN '3. AJUSTADO (1.5-2x)'
                    WHEN v1.precio / ({costo_pesos}) < 2.5 THEN '4. NORMAL (2-2.5x)'
                    WHEN v1.precio / ({costo_pesos}) < 3.0 THEN '5. BUENO (2.5-3x)'
                    ELSE '6. ALTO (3x+)'
                END
                ORDER BY rango
            """
            try:
                df_markup = pd.read_sql(sql_markup, conn)
                df_markup.columns = ['Rango', 'Ventas', 'Pares', 'Facturación', 'Pvta prom', 'Costo prom']
                st.dataframe(df_markup, use_container_width=True, hide_index=True)

                # Alerta de sin costo
                sin_costo = df_markup[df_markup['Rango'] == '1. SIN COSTO']
                if not sin_costo.empty:
                    st.warning(f"**{int(sin_costo.iloc[0]['Pares'])} pares** vendidos SIN COSTO REAL cargado "
                               f"(${sin_costo.iloc[0]['Facturación']:,.0f} facturados). Actualizar precio_costo en el ERP.")

                bajo = df_markup[df_markup['Rango'].isin(['2. BAJO (<1.5x)', '3. AJUSTADO (1.5-2x)'])]
                if not bajo.empty:
                    pares_bajo = int(bajo['Pares'].sum())
                    fact_bajo = bajo['Facturación'].sum()
                    st.warning(f"**{pares_bajo} pares** con markup < 2x (${fact_bajo:,.0f}). "
                               f"Margen neto ML < 34%. Revisar precios.")
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
                    CASE WHEN AVG(v1.precio) > 0
                        THEN ROUND((AVG(v1.precio) - AVG({costo_pesos})) / AVG(v1.precio) * 100, 1)
                        ELSE 0 END as margen_bruto,
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
                                regla_tn = st.session_state.reglas.get('tiendanube', REGLAS_DEFAULT.get('tiendanube'))
                                precio_calc = calcular_precio_canal(costo, regla_tn)
                                precio_sugerido = precio_calc.get('precio_venta', 0)

                                st.info(f"**{art['descripcion_1']} {art.get('descripcion_2','')}** | "
                                        f"Marca: {art.get('marca','-')} | Costo: ${costo:,.0f} | Stock: {stock}")

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
                                                resultado = tn.crear_producto(
                                                    nombre=nombre_pub,
                                                    variantes=[{
                                                        'price': str(precio_pub),
                                                        'stock': stock_pub,
                                                        'sku': sku_pub,
                                                    }],
                                                    descripcion=descripcion_pub,
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
                        reporte = sincronizar_stock(dry_run=dry_run_mode)
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
            tolerancia = st.slider('Tolerancia (%)', 0.0, 10.0, 2.0, 0.5,
                                   help='Ignora diferencias menores a este porcentaje')

            def _ejecutar_sync_precios(dry_run_mode):
                with st.spinner('Sincronizando precios...'):
                    try:
                        from multicanal.sync_precios import sincronizar_precios
                        reporte = sincronizar_precios(dry_run=dry_run_mode, tolerancia_pct=tolerancia)
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
            st.subheader('Facturar órdenes TiendaNube → POS 109')
            st.markdown('Procesa órdenes pagadas de TN y las envía al POS 109 para registro de venta, cliente y stock.')
            col_cfg1, col_cfg2 = st.columns(2)
            with col_cfg1:
                dias_facturar = st.slider('Últimos N días', 1, 30, 7, key='dias_fact')
            with col_cfg2:
                empresa_tn = st.selectbox('Empresa destino', ['H4', 'ABI'], index=0, key='empresa_tn',
                                          help='H4 → msgestion03 | ABI → msgestion01 (CALZALINDO)')

            def _ejecutar_facturacion(dry_run_mode):
                with st.spinner('Procesando órdenes...'):
                    try:
                        from multicanal.facturador_tn import sincronizar_ordenes_tn
                        reporte = sincronizar_ordenes_tn(dry_run=dry_run_mode, dias_atras=dias_facturar,
                                                         empresa=empresa_tn)
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
                                df_fact = pd.DataFrame([{
                                    'Orden TN': p['order_number'],
                                    'Fecha': p['fecha'],
                                    'Cliente': p['cliente'][:25],
                                    'Items': p['renglones'],
                                    'Total': f"${p['total']:,.0f}",
                                } for p in procesadas])
                                st.dataframe(df_fact, use_container_width=True, hide_index=True)

                            if not dry_run_mode and n_proc > 0:
                                total_fact = sum(p['total'] for p in procesadas)
                                st.success(f"{n_proc} órdenes facturadas. Total: ${total_fact:,.0f}")

                            if reporte.get('errores'):
                                for err in reporte['errores']:
                                    st.error(err)
                    except Exception as e:
                        st.error(f'Error: {e}')

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button('Dry run (solo ver)', key='btn_facturar'):
                    _ejecutar_facturacion(dry_run_mode=True)
            with col_btn2:
                confirmar_fact = st.checkbox('Confirmo enviar al POS 109', key='conf_facturar')
                if st.button('Enviar al POS 109', key='btn_facturar_real',
                             type='primary', disabled=not confirmar_fact):
                    _ejecutar_facturacion(dry_run_mode=False)

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
                col_ml1, col_ml2 = st.columns(2)
                with col_ml1:
                    dias_facturar_ml = st.slider('Últimos N días', 1, 30, 7, key='dias_fact_ml')
                with col_ml2:
                    empresa_ml = st.selectbox('Empresa destino', ['H4', 'ABI'], index=0, key='empresa_ml',
                                              help='H4 → msgestion03 | ABI → msgestion01')

                def _ejecutar_facturacion_ml(dry_run_mode):
                    with st.spinner('Procesando órdenes ML...'):
                        try:
                            from multicanal.facturador_ml import sincronizar_ordenes_ml
                            reporte = sincronizar_ordenes_ml(dry_run=dry_run_mode, dias_atras=dias_facturar_ml,
                                                              empresa=empresa_ml)
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
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric(r['canal_desc'], f"${r['precio_venta']:,.0f}")
                        c2.metric('Margen real', f"{r['margen_real']}%")
                        c3.metric('Ganancia $', f"${r['ganancia_neta']:,.0f}")
                        c4.metric('Comisiones $', f"${r['comision_plataforma'] + r['comision_pago']:,.0f}")

                st.divider()
                st.subheader('Comparativa')
                df_comp = pd.DataFrame([{
                    'Canal': r['canal_desc'],
                    'Costo': precio_costo,
                    'Precio venta': r['precio_venta'],
                    'Comisiones %': r['comision_total_pct'],
                    'Comisiones $': r['comision_plataforma'] + r['comision_pago'],
                    'Ingreso neto': r['ingreso_neto'],
                    'Ganancia': r['ganancia_neta'],
                    'Margen %': r['margen_real'],
                } for r in resultados])
                st.dataframe(df_comp, use_container_width=True, hide_index=True)

                # Gráfico de barras
                chart_data = df_comp[['Canal', 'Precio venta', 'Ganancia']].set_index('Canal')
                st.bar_chart(chart_data)
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
            col1, col2, col3 = st.columns(3)
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
    st.title('📦 Catálogo del ERP')
    st.markdown('Artículos activos con precio y stock. Seleccioná uno para ver pricing multicanal.')

    conn = get_db()
    if conn:
        productos = cargar_productos(conn)

        if not productos.empty:
            # Filtros
            col1, col2 = st.columns(2)
            with col1:
                filtro_marca = st.multiselect('Filtrar por marca', sorted(productos['marca'].dropna().unique()))
            with col2:
                filtro_texto = st.text_input('Buscar por descripción')

            df = productos.copy()
            if filtro_marca:
                df = df[df['marca'].isin(filtro_marca)]
            if filtro_texto:
                mask = df.apply(lambda row: filtro_texto.lower() in
                    f"{row.get('descripcion_1','')} {row.get('descripcion_2','')} {row.get('descripcion_3','')}".lower(), axis=1)
                df = df[mask]

            st.dataframe(
                df[['codigo', 'sinonimo', 'codigo_barra', 'descripcion_1', 'descripcion_2', 'marca', 'precio_costo', 'stock_d1', 'stock_h4']],
                use_container_width=True,
                hide_index=True,
            )

            st.divider()

            # Seleccionar artículo para pricing
            st.subheader('Calcular precios multicanal para un artículo')
            codigo_sel = st.selectbox(
                'Seleccionar artículo',
                df['codigo'].tolist(),
                format_func=lambda x: f"{x} — {df[df['codigo']==x].iloc[0]['descripcion_1']} {df[df['codigo']==x].iloc[0].get('descripcion_2','')}"
            )

            if codigo_sel:
                art = df[df['codigo'] == codigo_sel].iloc[0]
                costo = float(art['precio_costo'])

                st.info(f"**{art['descripcion_1']} {art.get('descripcion_2','')}** | "
                        f"Marca: {art.get('marca','-')} | "
                        f"Costo: ${costo:,.0f} | "
                        f"Stock D1: {art['stock_d1']} | Stock H4: {art['stock_h4']}")

                resultados = calcular_todos_los_canales(costo, st.session_state.reglas)
                df_precios = pd.DataFrame([{
                    'Canal': r['canal_descripcion'],
                    'Precio venta': f"${r['precio_venta']:,.0f}",
                    'Margen': f"{r['margen_real']}%",
                    'Ganancia': f"${r['ganancia_neta']:,.0f}",
                    'Comisión total': f"{r['comision_total_pct']}%",
                    'Neto': f"${r['ingreso_neto']:,.0f}",
                } for r in resultados.values() if 'error' not in r])
                st.dataframe(df_precios, use_container_width=True, hide_index=True)
        else:
            st.warning('No se encontraron artículos.')
    else:
        st.error('No hay conexión a SQL Server. Verificá VPN y credenciales.')
