"""
Lanzador centralizado de apps — H4 / CALZALINDO
Ejecutar: streamlit run app_launcher.py --server.port 8500 --server.address 0.0.0.0
"""
import streamlit as st
import subprocess
import os

st.set_page_config(page_title="H4/CLZ — Apps", page_icon="🚀", layout="wide")

APPS = [
    {
        'nombre': '🏪 Modelo de Locales',
        'archivo': 'app_locales.py',
        'puerto': 8504,
        'desc': 'Rentabilidad por local, P&L, presupuesto compra, piramide, industria/subrubro, Real vs Ley',
        'estado': 'activo',
        'owner': 'Fernando',
    },
    {
        'nombre': '📦 Carga Facturas/Pedidos',
        'archivo': 'app_carga.py',
        'puerto': 8501,
        'desc': 'OCR de facturas PDF, carga de pedidos, auto-deteccion proveedor',
        'estado': 'activo',
        'owner': 'Mati',
    },
    {
        'nombre': '🔄 Reposicion con Quiebre',
        'archivo': 'app_reposicion.py',
        'puerto': 8502,
        'desc': 'Analisis de quiebre de stock, velocidad real, GMROI, rotacion, curva talles',
        'estado': 'activo',
        'owner': 'Fernando',
    },
    {
        'nombre': '📊 Dashboard H4',
        'archivo': 'app_h4.py',
        'puerto': 8503,
        'desc': 'Dashboard principal H4 SRL',
        'estado': 'activo',
        'owner': 'Fernando',
    },
    {
        'nombre': '🛒 Multicanal TN/ML',
        'archivo': 'app_multicanal.py',
        'puerto': 8505,
        'desc': 'TiendaNube + MercadoLibre: stock sync, facturador, publicacion',
        'estado': 'desarrollo',
        'owner': 'Fernando',
    },
    {
        'nombre': '🤖 Pedido Automatico',
        'archivo': 'app_pedido_auto.py',
        'puerto': 8506,
        'desc': 'Generacion automatica de pedidos de compra basado en proyeccion',
        'estado': 'desarrollo',
        'owner': 'Mati',
    },
    {
        'nombre': '📈 Market Intelligence',
        'archivo': 'market_intelligence/app_market.py',
        'puerto': 8507,
        'desc': 'Analisis de mercado, competencia, pricing',
        'estado': 'desarrollo',
        'owner': 'Fernando',
    },
    {
        'nombre': '💰 Family Office',
        'archivo': '_family_office/app_family_office.py',
        'puerto': 8508,
        'desc': 'Gestion financiera familiar',
        'estado': 'desarrollo',
        'owner': 'Fernando',
    },
]

# Web2py (no streamlit)
WEB2PY = [
    {
        'nombre': '📋 Calzalindo Informes',
        'url': 'http://192.168.2.111/calzalindo_informes',
        'desc': 'Calce financiero, Ranking, Productividad, Ticket Historico, Poder Adquisitivo (PPA), Pedidos, Remitos',
        'estado': 'produccion',
        'owner': 'Fernando',
    },
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

st.title("🚀 H4 / CALZALINDO — Centro de Apps")
st.caption("Lanzador centralizado de todas las aplicaciones del proyecto")

# Estado de apps
col_act, col_dev, col_prod = st.columns(3)
activos = [a for a in APPS if a['estado'] == 'activo']
desarrollo = [a for a in APPS if a['estado'] == 'desarrollo']
col_act.metric("Apps activas", len(activos))
col_dev.metric("En desarrollo", len(desarrollo))
col_prod.metric("Web2py (produccion)", len(WEB2PY))

st.divider()

# Streamlit apps
st.header("Streamlit Apps")
for app in APPS:
    with st.container():
        cols = st.columns([3, 1, 1, 1])
        estado_icon = "🟢" if app['estado'] == 'activo' else "🟡"
        cols[0].markdown(f"### {app['nombre']} {estado_icon}")
        cols[0].caption(f"{app['desc']} — Owner: **{app['owner']}**")
        cols[1].code(f":{app['puerto']}", language=None)

        archivo_path = os.path.join(BASE_DIR, app['archivo'])
        existe = os.path.exists(archivo_path)

        if existe:
            if cols[2].button(f"▶️ Lanzar", key=f"launch_{app['puerto']}"):
                cmd = f"cd {BASE_DIR} && streamlit run {app['archivo']} --server.port {app['puerto']} --server.address 0.0.0.0 &"
                subprocess.Popen(cmd, shell=True)
                st.success(f"Lanzado en http://0.0.0.0:{app['puerto']}")
            cols[3].link_button("🔗 Abrir", f"http://192.168.3.71:{app['puerto']}")
        else:
            cols[2].warning("No existe")

st.divider()

# Web2py
st.header("Web2py (Produccion — 192.168.2.111)")
for w in WEB2PY:
    cols = st.columns([3, 1])
    cols[0].markdown(f"### {w['nombre']} 🟢")
    cols[0].caption(w['desc'])
    cols[1].link_button("🔗 Abrir", w['url'])

st.divider()

# Puertos en uso
st.header("Quick Reference")
st.code("""
PUERTOS:
  8500  Launcher (este)
  8501  Carga Facturas
  8502  Reposicion
  8503  Dashboard H4
  8504  Modelo Locales
  8505  Multicanal
  8506  Pedido Auto
  8507  Market Intel
  8508  Family Office

WEB2PY:
  http://192.168.2.111/calzalindo_informes  (produccion)

DEPLOY:
  cd ~/Desktop/cowork_pedidos/_sync_tools
  ./deploy.sh web2py     # calzalindo_informes
  ./deploy.sh scripts    # pipeline pedidos
  ./deploy.sh todo       # ambos
""", language="bash")
