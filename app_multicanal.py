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
    if 'db_conn' not in st.session_state or st.session_state.db_conn is None:
        import pyodbc
        conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.2.111;DATABASE=msgestion01art;UID=am;PWD=dl;Encrypt=no;"
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
                df[['codigo', 'codigo_barra', 'descripcion_1', 'descripcion_2', 'marca', 'precio_costo', 'stock_d1', 'stock_h4']],
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
