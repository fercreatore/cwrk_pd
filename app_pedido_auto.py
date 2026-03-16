#!/usr/bin/env python3
"""
app_pedido_auto.py — Pedido Automático con INSERT y Email
==========================================================
Streamlit app que:
1. Elige proveedor/marca
2. Analiza quiebre + estacionalidad + velocidad real
3. Muestra pedido sugerido editable
4. Botón INSERT → escribe pedico2+pedico1 en producción (111)
5. Botón ENVIAR → manda email al proveedor
6. Log de seguimiento de pedidos

EJECUTAR:
  streamlit run app_pedido_auto.py

Autor: Cowork + Claude — Marzo 2026
"""

import streamlit as st
import pandas as pd
import pyodbc
import json
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from config import (
    CONN_COMPRAS, CONN_ARTICULOS, PROVEEDORES,
    EMPRESA_DEFAULT, calcular_precios, get_conn_string
)
from proveedores_db import obtener_pricing_proveedor, listar_proveedores_activos


def _resolver_proveedor(proveedor_id):
    """Busca proveedor en config.py primero, luego en BD."""
    prov = PROVEEDORES.get(proveedor_id)
    if prov:
        return prov
    try:
        import pyodbc
        pricing = obtener_pricing_proveedor(proveedor_id)
        conn_tmp = pyodbc.connect(CONN_COMPRAS, timeout=10)
        cur = conn_tmp.cursor()
        cur.execute(
            "SELECT denominacion, cuit, condicion_iva, zona "
            "FROM msgestionC.dbo.proveedores WHERE numero = ?", proveedor_id)
        row = cur.fetchone()
        conn_tmp.close()
        if row:
            prov = {
                "nombre": (row.denominacion or "").strip(),
                "cuit": (row.cuit or "").strip().replace("-", ""),
                "condicion_iva": (row.condicion_iva or "I").strip(),
                "zona": row.zona or 0,
            }
            prov.update(pricing)
            return prov
    except Exception:
        pass
    return {}

# ============================================================================
# CONSTANTES
# ============================================================================

DEPOS_INFORMES = (0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)
DEPOS_SQL = '(0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)'
EXCL_VENTAS = '(7,36)'
LOG_FILE = os.path.join(os.path.dirname(__file__), 'pedidos_log.json')

# Conexiones
CONN_REPLICA = get_conn_string("msgestionC")  # para análisis

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Pedido Automático",
    page_icon="📦",
    layout="wide"
)

# ============================================================================
# DATABASE HELPERS
# ============================================================================

@st.cache_resource
def get_conn_analisis():
    """Conexión a réplica/producción para análisis (SELECT)."""
    try:
        return pyodbc.connect(CONN_COMPRAS, timeout=10)
    except:
        return pyodbc.connect(CONN_REPLICA, timeout=10)

def query_df(sql, conn=None):
    """Ejecuta query y retorna DataFrame."""
    c = conn or get_conn_analisis()
    try:
        return pd.read_sql(sql, c)
    except Exception as e:
        st.error(f"Error SQL: {e}")
        return pd.DataFrame()


# ============================================================================
# ANÁLISIS DE QUIEBRE
# ============================================================================

def analizar_quiebre(codigo_sinonimo, meses=12):
    """Calcula quiebre mensual reconstruyendo stock hacia atrás."""
    hoy = date.today()
    desde = (hoy - relativedelta(months=meses)).replace(day=1)

    # Stock actual
    sql_stock = f"""
        SELECT ISNULL(SUM(s.stock_actual),0) AS stock
        FROM stock s
        LEFT JOIN articulo a ON a.codigo=s.articulo
        WHERE a.codigo_sinonimo='{codigo_sinonimo}'
        AND s.deposito IN {DEPOS_SQL}
    """
    df_s = query_df(sql_stock)
    stock_actual = float(df_s['stock'].iloc[0]) if not df_s.empty else 0

    # Ventas mensuales
    sql_v = f"""
        SELECT SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes
        FROM ventas1 v
        LEFT JOIN articulo a ON v.articulo=a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.codigo_sinonimo='{codigo_sinonimo}'
          AND v.fecha>='{desde}'
        GROUP BY YEAR(v.fecha), MONTH(v.fecha)
    """
    df_v = query_df(sql_v)
    ventas_dict = {}
    for _, r in df_v.iterrows():
        ventas_dict[(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    # Compras mensuales
    sql_c = f"""
        SELECT SUM(rc.cantidad) AS cant,
               YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes
        FROM compras1 rc
        LEFT JOIN articulo a ON rc.articulo=a.codigo
        WHERE rc.operacion='+'
          AND a.codigo_sinonimo='{codigo_sinonimo}'
          AND rc.fecha>='{desde}'
        GROUP BY YEAR(rc.fecha), MONTH(rc.fecha)
    """
    df_c = query_df(sql_c)
    compras_dict = {}
    for _, r in df_c.iterrows():
        compras_dict[(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    # Reconstruir hacia atrás
    meses_lista = []
    cursor = hoy.replace(day=1)
    for _ in range(meses):
        meses_lista.append((cursor.year, cursor.month))
        cursor -= relativedelta(months=1)

    detalle = []
    stock_fin = stock_actual
    for anio, mes in meses_lista:
        v = ventas_dict.get((anio, mes), 0)
        c = compras_dict.get((anio, mes), 0)
        stock_inicio = stock_fin + v - c
        detalle.append({
            'periodo': f'{anio}-{mes:02d}',
            'ventas': v, 'compras': c,
            'stock_inicio': stock_inicio, 'stock_fin': stock_fin,
            'quebrado': stock_inicio <= 0
        })
        stock_fin = stock_inicio

    meses_q = sum(1 for d in detalle if d['quebrado'])
    meses_ok = len(detalle) - meses_q
    ventas_total = sum(d['ventas'] for d in detalle)
    ventas_ok = sum(d['ventas'] for d in detalle if not d['quebrado'])

    vel_ap = ventas_total / max(len(detalle), 1)
    vel_real = ventas_ok / max(meses_ok, 1) if meses_ok > 0 else vel_ap

    return {
        'stock_actual': stock_actual,
        'meses_quebrado': meses_q,
        'meses_ok': meses_ok,
        'pct_quiebre': round(meses_q / max(len(detalle), 1) * 100, 1),
        'vel_aparente': round(vel_ap, 2),
        'vel_real': round(vel_real, 2),
        'ventas_total': ventas_total,
        'detalle': list(reversed(detalle))
    }


def factor_estacional(codigo_sinonimo, anios=3):
    """Factor estacional por mes (3 años de historia)."""
    desde = (date.today() - relativedelta(years=anios)).replace(month=1, day=1)
    sql = f"""
        SELECT SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes
        FROM ventas1 v
        LEFT JOIN articulo a ON v.articulo=a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.codigo_sinonimo='{codigo_sinonimo}'
          AND v.fecha>='{desde}'
        GROUP BY YEAR(v.fecha), MONTH(v.fecha)
    """
    df = query_df(sql)
    if df.empty:
        return {m: 1.0 for m in range(1, 13)}

    df['cant'] = df['cant'].astype(float)
    prom = df.groupby('mes')['cant'].mean()
    media = prom.mean() if prom.mean() > 0 else 1
    return {m: round(prom.get(m, media) / media, 3) for m in range(1, 13)}


# ============================================================================
# ANÁLISIS COMPLETO DE MARCA
# ============================================================================

@st.cache_data(ttl=300)
def analizar_marca(marca_codigo, cobertura_meses=3):
    """Analiza todos los productos de una marca para pedido."""
    desde = (date.today() - relativedelta(months=12)).replace(day=1)

    # Productos con stock o ventas
    sql_prod = f"""
        SELECT DISTINCT LEFT(a.codigo_sinonimo, 10) AS csr,
               MAX(a.descripcion_1) AS descripcion
        FROM articulo a
        WHERE a.marca={marca_codigo}
          AND LEN(a.codigo_sinonimo) >= 10
          AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
        GROUP BY LEFT(a.codigo_sinonimo, 10)
    """
    df_prod = query_df(sql_prod)
    if df_prod.empty:
        return pd.DataFrame()

    resultados = []
    for _, p in df_prod.iterrows():
        csr = p['csr']

        # Obtener todos los talles
        sql_talles = f"""
            SELECT a.codigo_sinonimo, a.descripcion_5 AS talle,
                   a.codigo AS cod_articulo,
                   ISNULL((SELECT SUM(s.stock_actual) FROM stock s
                           WHERE s.articulo=a.codigo
                           AND s.deposito IN {DEPOS_SQL}), 0) AS stock_actual
            FROM articulo a
            WHERE a.codigo_sinonimo LIKE '{csr}%'
              AND LEN(a.codigo_sinonimo) > 10
            ORDER BY a.descripcion_5
        """
        df_talles = query_df(sql_talles)

        if df_talles.empty:
            continue

        # Stock total del CSR
        stock_total = df_talles['stock_actual'].sum()
        if stock_total <= 0:
            # Verificar si hay ventas recientes
            sql_check = f"""
                SELECT COUNT(*) AS n FROM ventas1 v
                LEFT JOIN articulo a ON v.articulo=a.codigo
                WHERE a.codigo_sinonimo LIKE '{csr}%'
                  AND v.fecha>='{desde}' AND v.codigo NOT IN {EXCL_VENTAS}
            """
            df_check = query_df(sql_check)
            if df_check.empty or df_check['n'].iloc[0] == 0:
                continue

        # Ventas por talle últimos 12 meses
        sql_vtas = f"""
            SELECT a.codigo_sinonimo, a.descripcion_5 AS talle,
                   SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                            WHEN v.operacion='-' THEN -v.cantidad END) AS ventas
            FROM ventas1 v
            LEFT JOIN articulo a ON v.articulo=a.codigo
            WHERE a.codigo_sinonimo LIKE '{csr}%'
              AND v.fecha>='{desde}' AND v.codigo NOT IN {EXCL_VENTAS}
            GROUP BY a.codigo_sinonimo, a.descripcion_5
        """
        df_vtas = query_df(sql_vtas)

        # Merge talles + ventas
        df_t = pd.merge(df_talles, df_vtas, on=['codigo_sinonimo', 'talle'], how='left').fillna(0)
        df_t['ventas'] = df_t['ventas'].astype(float)

        ventas_total_csr = df_t['ventas'].sum()
        if ventas_total_csr <= 0:
            continue

        # Quiebre por talle más vendido (representativo)
        top_talle = df_t.sort_values('ventas', ascending=False).iloc[0]['codigo_sinonimo']
        quiebre = analizar_quiebre(top_talle, meses=12)

        # Factor estacional
        factores = factor_estacional(top_talle)
        mes_actual = date.today().month
        factor_prom = sum(factores.get((mes_actual + i - 1) % 12 + 1, 1.0)
                          for i in range(cobertura_meses)) / cobertura_meses

        vel_ajustada = quiebre['vel_real'] * factor_prom

        # Último precio de compra
        sql_precio = f"""
            SELECT TOP 1 rc.monto_facturado / NULLIF(rc.cantidad, 0) AS precio_unit
            FROM compras1 rc
            LEFT JOIN articulo a ON rc.articulo=a.codigo
            WHERE a.codigo_sinonimo LIKE '{csr}%'
              AND rc.operacion='+' AND rc.cantidad > 0
            ORDER BY rc.fecha DESC
        """
        df_precio = query_df(sql_precio)
        precio = float(df_precio['precio_unit'].iloc[0]) if not df_precio.empty else 0

        # Calcular pedido
        necesidad = vel_ajustada * cobertura_meses
        pedir = max(0, round(necesidad - stock_total))

        # Distribución por talle
        for _, t in df_t.iterrows():
            pct = (t['ventas'] / ventas_total_csr * 100) if ventas_total_csr > 0 else 0
            pedir_talle = max(0, round(pedir * pct / 100)) if pedir > 0 else 0

            resultados.append({
                'csr': csr,
                'descripcion': p['descripcion'],
                'codigo_sinonimo': t['codigo_sinonimo'],
                'talle': t['talle'],
                'cod_articulo': int(t['cod_articulo']),
                'stock': int(t['stock_actual']),
                'ventas_12m': int(t['ventas']),
                'pct_talle': round(pct, 1),
                'vel_real': quiebre['vel_real'],
                'pct_quiebre': quiebre['pct_quiebre'],
                'factor_est': round(factor_prom, 2),
                'vel_ajustada': round(vel_ajustada, 2),
                'precio': round(precio, 0),
                'pedir': pedir_talle,
            })

    df_result = pd.DataFrame(resultados)
    if not df_result.empty:
        df_result['monto'] = df_result['pedir'] * df_result['precio']
    return df_result


# ============================================================================
# INSERT EN PRODUCCIÓN
# ============================================================================

def insertar_pedido_produccion(proveedor_id, empresa, renglones_df, observaciones="",
                                fecha_entrega=None):
    """Inserta pedido en producción (111) usando paso4."""
    from paso4_insertar_pedido import insertar_pedido

    prov = _resolver_proveedor(proveedor_id)
    fecha_hoy = date.today()

    cabecera = {
        "empresa": empresa,
        "cuenta": proveedor_id,
        "denominacion": prov["nombre"],
        "fecha_comprobante": fecha_hoy,
        "fecha_entrega": fecha_entrega or (fecha_hoy + timedelta(days=30)),
        "observaciones": observaciones,
    }

    renglones = []
    for _, r in renglones_df.iterrows():
        if r['pedir'] > 0:
            renglones.append({
                "articulo": int(r['cod_articulo']),
                "descripcion": str(r['descripcion'])[:80] + " " + str(r['talle']),
                "codigo_sinonimo": str(r['codigo_sinonimo']),
                "cantidad": int(r['pedir']),
                "precio": float(r['precio']),
            })

    if not renglones:
        return None, "No hay renglones con cantidad > 0"

    numero = insertar_pedido(cabecera, renglones, dry_run=False)
    return numero, f"Pedido #{numero} insertado OK" if numero else "Error al insertar"


# ============================================================================
# EMAIL AL PROVEEDOR
# ============================================================================

def enviar_email_proveedor(proveedor_id, numero_pedido, renglones_df, email_destino):
    """Envía email con detalle del pedido al proveedor."""
    prov = _resolver_proveedor(proveedor_id)

    # Armar tabla HTML
    filas = ""
    total_pares = 0
    total_monto = 0
    for _, r in renglones_df[renglones_df['pedir'] > 0].iterrows():
        monto = r['pedir'] * r['precio']
        filas += f"<tr><td>{r['descripcion']}</td><td>{r['talle']}</td>"
        filas += f"<td style='text-align:center'>{int(r['pedir'])}</td>"
        filas += f"<td style='text-align:right'>${r['precio']:,.0f}</td>"
        filas += f"<td style='text-align:right'>${monto:,.0f}</td></tr>"
        total_pares += int(r['pedir'])
        total_monto += monto

    html = f"""
    <html><body>
    <p>Estimado proveedor,</p>
    <p>Adjuntamos nota de pedido <b>#{numero_pedido}</b> de <b>H4 SRL / CALZALINDO</b>.</p>
    <table border='1' cellpadding='5' cellspacing='0' style='border-collapse:collapse; font-family:Arial; font-size:12px'>
    <tr style='background:#333; color:white'>
        <th>Producto</th><th>Talle</th><th>Cant.</th><th>Precio</th><th>Subtotal</th>
    </tr>
    {filas}
    <tr style='font-weight:bold; background:#f0f0f0'>
        <td colspan='2'>TOTAL</td>
        <td style='text-align:center'>{total_pares}</td>
        <td></td>
        <td style='text-align:right'>${total_monto:,.0f}</td>
    </tr>
    </table>
    <p>Favor confirmar recepción y plazo de entrega.</p>
    <p>Saludos,<br>Compras — H4 SRL / CALZALINDO</p>
    </body></html>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f'Nota de Pedido #{numero_pedido} — H4/CALZALINDO'
    msg['From'] = 'compras@calzalindo.com'  # CONFIGURAR
    msg['To'] = email_destino
    msg.attach(MIMEText(html, 'html'))

    try:
        # CONFIGURAR SMTP
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login('compras@calzalindo.com', 'APP_PASSWORD')  # CONFIGURAR
            server.send_message(msg)
        return True, "Email enviado OK"
    except Exception as e:
        return False, f"Error enviando email: {e}"


# ============================================================================
# LOG DE SEGUIMIENTO
# ============================================================================

def guardar_log(entry):
    """Guarda entrada en el log de pedidos."""
    log = cargar_log()
    log.append(entry)
    with open(LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2, default=str)

def cargar_log():
    """Carga log de pedidos."""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    return []


# ============================================================================
# UI PRINCIPAL
# ============================================================================

def main():
    st.title("📦 Pedido Automático")
    st.caption("Análisis de quiebre → Pedido sugerido → INSERT → Email proveedor")

    # Sidebar: elegir proveedor
    st.sidebar.header("Configuración")

    # Combinar proveedores de config.py + BD dinámica
    proveedores_lista = {v['nombre']: k for k, v in PROVEEDORES.items()}
    try:
        provs_bd = listar_proveedores_activos()
        for num, p in provs_bd.items():
            if num not in PROVEEDORES and p["nombre"] not in proveedores_lista:
                proveedores_lista[p["nombre"]] = num
    except Exception:
        pass
    prov_nombre = st.sidebar.selectbox("Proveedor / Marca", sorted(proveedores_lista.keys()))
    prov_id = proveedores_lista[prov_nombre]
    prov = _resolver_proveedor(prov_id)

    marca = prov['marca']
    empresa = prov.get('empresa', EMPRESA_DEFAULT)

    cobertura = st.sidebar.slider("Cobertura (meses)", 1, 6, 3)
    fecha_entrega = st.sidebar.date_input("Fecha entrega estimada",
                                           date.today() + timedelta(days=30))

    # Tabs
    tab_pedido, tab_seguimiento = st.tabs(["🛒 Pedido", "📋 Seguimiento"])

    with tab_pedido:
        # Botón analizar
        if st.button("🔍 Analizar marca", type="primary", use_container_width=True):
            with st.spinner(f"Analizando {prov_nombre} (marca {marca})..."):
                st.session_state['df_pedido'] = analizar_marca(marca, cobertura)
                st.session_state['analisis_ok'] = True

        if st.session_state.get('analisis_ok') and 'df_pedido' in st.session_state:
            df = st.session_state['df_pedido'].copy()

            if df.empty:
                st.warning("No se encontraron productos con datos suficientes.")
                return

            # Resumen
            total_pedir = int(df['pedir'].sum())
            total_monto = df['monto'].sum()
            productos = df['csr'].nunique()
            talles = len(df[df['pedir'] > 0])
            quiebre_prom = df.groupby('csr')['pct_quiebre'].first().mean()

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Productos", productos)
            c2.metric("Pares a pedir", total_pedir)
            c3.metric("Monto total", f"${total_monto:,.0f}")
            c4.metric("Talles con pedido", talles)
            c5.metric("Quiebre prom.", f"{quiebre_prom:.0f}%")

            st.divider()

            # Tabla editable
            st.subheader("Pedido sugerido — editá las cantidades")

            # Agrupar por producto para mostrar mejor
            for csr in df['csr'].unique():
                df_csr = df[df['csr'] == csr].copy()
                desc = df_csr.iloc[0]['descripcion']
                vel = df_csr.iloc[0]['vel_real']
                quiebre = df_csr.iloc[0]['pct_quiebre']
                factor = df_csr.iloc[0]['factor_est']

                total_pedir_csr = int(df_csr['pedir'].sum())
                if total_pedir_csr == 0:
                    continue

                with st.expander(
                    f"**{desc}** — {total_pedir_csr} pares | "
                    f"Vel real: {vel}/mes | Quiebre: {quiebre}% | "
                    f"Factor est.: {factor}",
                    expanded=True
                ):
                    # Editable dataframe
                    cols_mostrar = ['talle', 'stock', 'ventas_12m', 'pct_talle',
                                    'precio', 'pedir']
                    df_edit = st.data_editor(
                        df_csr[cols_mostrar].reset_index(drop=True),
                        column_config={
                            'talle': st.column_config.TextColumn('Talle', disabled=True),
                            'stock': st.column_config.NumberColumn('Stock', disabled=True),
                            'ventas_12m': st.column_config.NumberColumn('Vtas 12m', disabled=True),
                            'pct_talle': st.column_config.NumberColumn('% Talle', disabled=True,
                                                                        format="%.1f%%"),
                            'precio': st.column_config.NumberColumn('Precio', disabled=True,
                                                                     format="$%.0f"),
                            'pedir': st.column_config.NumberColumn('PEDIR', min_value=0,
                                                                    max_value=999),
                        },
                        key=f"edit_{csr}",
                        use_container_width=True,
                        hide_index=True,
                    )

                    # Actualizar cantidades editadas
                    if df_edit is not None:
                        mask = df['csr'] == csr
                        df.loc[mask, 'pedir'] = df_edit['pedir'].values
                        df.loc[mask, 'monto'] = df_edit['pedir'].values * df.loc[mask, 'precio'].values

            # Guardar cambios
            st.session_state['df_pedido'] = df

            # Recalcular totales después de edición
            total_pedir = int(df['pedir'].sum())
            total_monto = df['monto'].sum()

            st.divider()

            # Resumen final
            st.subheader(f"Total: {total_pedir} pares — ${total_monto:,.0f}")

            # Observaciones
            obs = st.text_area("Observaciones para el pedido",
                               f"Pedido automático {prov_nombre}. "
                               f"Cobertura {cobertura} meses. "
                               f"Análisis con quiebre 12m + estacionalidad.",
                               key="obs_pedido")

            st.divider()

            # BOTONES DE ACCIÓN
            col_insert, col_email = st.columns(2)

            with col_insert:
                st.markdown("### 💾 Insertar nota de pedido")
                if total_pedir == 0:
                    st.info("No hay pares para pedir.")
                else:
                    if st.button("⚡ INSERTAR EN ERP", type="primary",
                                 use_container_width=True):
                        with st.spinner("Insertando pedido en producción..."):
                            try:
                                numero, msg = insertar_pedido_produccion(
                                    prov_id, empresa, df, obs, fecha_entrega)
                                if numero:
                                    st.success(f"✅ {msg}")
                                    st.session_state['ultimo_pedido'] = numero

                                    # Log
                                    guardar_log({
                                        'fecha': str(datetime.now()),
                                        'numero': numero,
                                        'proveedor': prov_nombre,
                                        'prov_id': prov_id,
                                        'empresa': empresa,
                                        'pares': total_pedir,
                                        'monto': total_monto,
                                        'estado': 'insertado',
                                        'email_enviado': False,
                                        'confirmado': False,
                                    })

                                    st.balloons()
                                else:
                                    st.error(f"❌ {msg}")
                            except Exception as e:
                                st.error(f"❌ Error: {e}")

            with col_email:
                st.markdown("### 📧 Enviar al proveedor")
                email_prov = st.text_input("Email del proveedor",
                                            key="email_prov",
                                            placeholder="ventas@proveedor.com")

                numero_pedido = st.session_state.get('ultimo_pedido', '---')

                if st.button("📤 ENVIAR EMAIL", use_container_width=True,
                             disabled=not email_prov or numero_pedido == '---'):
                    with st.spinner("Enviando email..."):
                        ok, msg = enviar_email_proveedor(
                            prov_id, numero_pedido, df, email_prov)
                        if ok:
                            st.success(f"✅ {msg}")
                            # Actualizar log
                            log = cargar_log()
                            for entry in reversed(log):
                                if entry.get('numero') == numero_pedido:
                                    entry['email_enviado'] = True
                                    entry['email_destino'] = email_prov
                                    entry['email_fecha'] = str(datetime.now())
                                    break
                            with open(LOG_FILE, 'w') as f:
                                json.dump(log, f, indent=2, default=str)
                        else:
                            st.error(f"❌ {msg}")
                            st.info("Podés copiar la tabla y pegarla en un email manualmente.")

    # TAB SEGUIMIENTO
    with tab_seguimiento:
        st.subheader("📋 Historial de pedidos")

        log = cargar_log()
        if not log:
            st.info("Todavía no hay pedidos registrados.")
        else:
            df_log = pd.DataFrame(log)
            df_log = df_log.sort_values('fecha', ascending=False)

            # Indicadores
            total_pedidos = len(df_log)
            pendientes = len(df_log[df_log['confirmado'] == False])
            enviados = len(df_log[df_log['email_enviado'] == True])

            c1, c2, c3 = st.columns(3)
            c1.metric("Total pedidos", total_pedidos)
            c2.metric("Emails enviados", enviados)
            c3.metric("Pendientes confirmación", pendientes)

            # Tabla
            cols_log = ['fecha', 'numero', 'proveedor', 'empresa', 'pares',
                        'monto', 'estado', 'email_enviado', 'confirmado']
            cols_disponibles = [c for c in cols_log if c in df_log.columns]

            st.dataframe(
                df_log[cols_disponibles],
                column_config={
                    'monto': st.column_config.NumberColumn(format="$%.0f"),
                    'email_enviado': st.column_config.CheckboxColumn("Email"),
                    'confirmado': st.column_config.CheckboxColumn("Confirmado"),
                },
                use_container_width=True,
                hide_index=True
            )

            # Marcar como confirmado
            st.divider()
            pedidos_pendientes = df_log[df_log['confirmado'] == False]['numero'].tolist()
            if pedidos_pendientes:
                confirmar = st.selectbox("Marcar como confirmado:", pedidos_pendientes)
                if st.button("✅ Confirmar recepción"):
                    for entry in log:
                        if entry.get('numero') == confirmar:
                            entry['confirmado'] = True
                            entry['fecha_confirmacion'] = str(datetime.now())
                    with open(LOG_FILE, 'w') as f:
                        json.dump(log, f, indent=2, default=str)
                    st.success(f"Pedido #{confirmar} marcado como confirmado.")
                    st.rerun()


if __name__ == "__main__":
    main()
