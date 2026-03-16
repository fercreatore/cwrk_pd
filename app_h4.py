#!/usr/bin/env python3
"""
app_h4.py — Sistema Integrado H4 / Calzalindo
================================================
App unificada: Reposición Inteligente + Carga de Facturas

Modelo Waterfall ROI con presupuesto como driver.
Velocidad real corregida por quiebre de stock.
Plotly interactivo + custom CSS premium.

EJECUTAR:
  streamlit run app_h4.py --server.port 8502

Autor: Cowork + Claude — Marzo 2026
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pyodbc
import json
import os
import sys
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

sys.path.insert(0, os.path.dirname(__file__))

from config import (
    CONN_COMPRAS, CONN_ARTICULOS, PROVEEDORES,
    EMPRESA_DEFAULT, calcular_precios, get_conn_string
)
from proveedores_db import obtener_pricing_proveedor, listar_proveedores_activos

# ============================================================================
# CONSTANTES
# ============================================================================

DEPOS_SQL = '(0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)'
EXCL_VENTAS = '(7,36)'
VENTANAS_DIAS = [15, 30, 45, 60]
MESES_HISTORIA = 12
LOG_FILE = os.path.join(os.path.dirname(__file__), 'pedidos_log.json')
MESES_NOMBRES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']

# Lead time por proveedor (días estimados desde que pedís hasta que llega)
LEAD_TIMES = {
    668: 45,   # ALPARGATAS — despacho lento, mucha burocracia
    104: 15,   # GTN — rápido, Venado Tuerto
    594: 30,   # INDUSTRIAS AS (WAKE/ATOMIK) — estándar
    656: 30,   # DISTRINANDO (REEBOK) — estándar
    561: 20,   # SOUTER (RINGO/CARMEL) — relativamente rápido
    236: 20,   # CONFORTABLE — rápido
    42:  30,   # LESEDIFE — estándar
    614: 25,   # CALZADOS BLANCO (DIADORA) — medio
    713: 30,   # DISTRINANDO MODA — estándar
    950: 40,   # TIVORY — lento
    457: 25,   # ZOTZ — medio
    118: 20,   # EL FARAON — rápido
    28:  15,   # MARYSABEL — rápido
    217: 25,   # PALUBEL — medio
}
LEAD_TIME_DEFAULT = 30  # si no está configurado

# Paleta
C_BRAND   = '#0066FF'
C_BRAND_L = '#3388FF'
C_RED     = '#EF4444'
C_AMBER   = '#F59E0B'
C_GREEN   = '#10B981'
C_SLATE   = '#64748B'
C_BG      = '#0F172A'
C_CARD    = '#1E293B'
C_SURFACE = '#334155'

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="H4 · Sistema Integrado",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# THEME CSS
# ============================================================================

st.markdown("""
<style>
    /* ── Global ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    .stApp { font-family: 'Inter', sans-serif; }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown { color: #CBD5E1; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 { color: #F1F5F9 !important; }

    /* ── KPI Cards ── */
    .kpi-row { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
    .kpi-card {
        flex: 1; min-width: 160px; padding: 18px 20px; border-radius: 14px;
        background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
        border: 1px solid rgba(255,255,255,0.06);
        box-shadow: 0 4px 24px rgba(0,0,0,0.12);
        position: relative; overflow: hidden;
    }
    .kpi-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    }
    .kpi-card.blue::before { background: linear-gradient(90deg, #0066FF, #3388FF); }
    .kpi-card.red::before { background: linear-gradient(90deg, #EF4444, #F87171); }
    .kpi-card.amber::before { background: linear-gradient(90deg, #F59E0B, #FBBF24); }
    .kpi-card.green::before { background: linear-gradient(90deg, #10B981, #34D399); }
    .kpi-card.purple::before { background: linear-gradient(90deg, #8B5CF6, #A78BFA); }

    .kpi-label { font-size: 11px; font-weight: 600; text-transform: uppercase;
                 letter-spacing: 0.8px; color: #94A3B8; margin-bottom: 6px; }
    .kpi-value { font-size: 28px; font-weight: 800; color: #F1F5F9; line-height: 1.1; }
    .kpi-sub { font-size: 12px; color: #64748B; margin-top: 4px; }

    /* ── Semáforo badges ── */
    .badge { display: inline-block; padding: 3px 10px; border-radius: 20px;
             font-size: 11px; font-weight: 700; letter-spacing: 0.5px; }
    .badge-red { background: rgba(239,68,68,0.15); color: #EF4444; }
    .badge-amber { background: rgba(245,158,11,0.15); color: #F59E0B; }
    .badge-green { background: rgba(16,185,129,0.15); color: #10B981; }

    /* ── Section headers ── */
    .section-title {
        font-size: 13px; font-weight: 700; text-transform: uppercase;
        letter-spacing: 1.2px; color: #64748B; margin: 28px 0 14px 0;
        padding-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.06);
    }

    /* ── Data tables ── */
    .stDataFrame { border-radius: 12px; overflow: hidden; }

    /* ── Nav pills ── */
    .nav-container { display: flex; gap: 6px; margin-bottom: 24px;
                     padding: 4px; background: #1E293B; border-radius: 12px;
                     border: 1px solid rgba(255,255,255,0.06); }
    .nav-pill { padding: 10px 20px; border-radius: 8px; font-size: 13px;
                font-weight: 600; color: #94A3B8; cursor: pointer;
                transition: all 0.2s; text-align: center; flex: 1; }
    .nav-pill.active { background: #0066FF; color: white;
                       box-shadow: 0 2px 12px rgba(0,102,255,0.3); }

    /* ── Waterfall projection cards ── */
    .wf-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 16px 0; }
    .wf-card { padding: 16px; border-radius: 12px; text-align: center;
               border: 1px solid rgba(255,255,255,0.06);
               background: linear-gradient(135deg, #1E293B 0%, #334155 100%); }
    .wf-card.rojo { border-left: 3px solid #EF4444; }
    .wf-card.amarillo { border-left: 3px solid #F59E0B; }
    .wf-card.verde { border-left: 3px solid #10B981; }
    .wf-days { font-size: 12px; font-weight: 700; color: #94A3B8;
               text-transform: uppercase; letter-spacing: 0.8px; }
    .wf-stock { font-size: 24px; font-weight: 800; margin: 8px 0 4px; }
    .wf-stock.neg { color: #EF4444; }
    .wf-stock.low { color: #F59E0B; }
    .wf-stock.ok { color: #10B981; }
    .wf-detail { font-size: 11px; color: #64748B; }

    /* ── Presupuesto progress ── */
    .budget-bar { background: #1E293B; border-radius: 8px; height: 24px;
                  overflow: hidden; margin: 8px 0; border: 1px solid rgba(255,255,255,0.06); }
    .budget-fill { height: 100%; border-radius: 8px;
                   background: linear-gradient(90deg, #0066FF, #3388FF);
                   transition: width 0.5s ease; }

    /* ── Hide Streamlit defaults ── */
    #MainMenu { visibility: hidden; }
    header { visibility: hidden; }
    footer { visibility: hidden; }
    .block-container { padding-top: 1rem; }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# HTML COMPONENT HELPERS
# ============================================================================

def kpi_card(label, value, sub="", color="blue"):
    return f"""
    <div class="kpi-card {color}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>"""

def kpi_row(cards_html):
    return f'<div class="kpi-row">{"".join(cards_html)}</div>'

def badge(text, tipo="green"):
    return f'<span class="badge badge-{tipo}">{text}</span>'

def section_title(text):
    return f'<div class="section-title">{text}</div>'

def wf_card_html(dias, stock_proy, ventas_proy, status):
    color_class = status
    stock_class = "neg" if stock_proy <= 0 else ("low" if status == "amarillo" else "ok")
    sign = "" if stock_proy < 0 else ""
    return f"""
    <div class="wf-card {color_class}">
        <div class="wf-days">{dias} días</div>
        <div class="wf-stock {stock_class}">{sign}{stock_proy:.0f}</div>
        <div class="wf-detail">-{ventas_proy:.0f} vendidos</div>
    </div>"""


# ============================================================================
# DATABASE
# ============================================================================

@st.cache_resource
def get_conn():
    try:
        return pyodbc.connect(CONN_COMPRAS, timeout=15)
    except:
        return pyodbc.connect(get_conn_string("msgestionC"), timeout=15)

def query_df(sql, conn=None):
    c = conn or get_conn()
    try:
        return pd.read_sql(sql, c)
    except Exception as e:
        st.error(f"Error SQL: {e}")
        return pd.DataFrame()


# ============================================================================
# DATA FUNCTIONS (from app_reposicion.py — unchanged logic)
# ============================================================================

def analizar_quiebre_batch(codigos_sinonimo, meses=MESES_HISTORIA):
    """
    Analiza quiebre para múltiples CSR (10 chars) en batch.
    IMPORTANTE: codigos_sinonimo son los primeros 10 chars (CSR nivel modelo).
    Usa LEFT(codigo_sinonimo, 10) para agrupar todos los talles de un modelo.
    """
    if not codigos_sinonimo:
        return {}

    hoy = date.today()
    desde = (hoy - relativedelta(months=meses)).replace(day=1)
    filtro = ",".join(f"'{c}'" for c in codigos_sinonimo)

    # Usar LEFT(codigo_sinonimo, 10) para matchear CSR de 10 chars
    sql_stock = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr, ISNULL(SUM(s.stock_actual), 0) AS stock
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        WHERE LEFT(a.codigo_sinonimo, 10) IN ({filtro}) AND s.deposito IN {DEPOS_SQL}
        GROUP BY LEFT(a.codigo_sinonimo, 10)
    """
    df_stock = query_df(sql_stock)
    stock_dict = {r['csr'].strip(): float(r['stock']) for _, r in df_stock.iterrows()}

    sql_ventas = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS} AND LEFT(a.codigo_sinonimo, 10) IN ({filtro}) AND v.fecha >= '{desde}'
        GROUP BY LEFT(a.codigo_sinonimo, 10), YEAR(v.fecha), MONTH(v.fecha)
    """
    df_ventas = query_df(sql_ventas)

    sql_compras = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr, SUM(rc.cantidad) AS cant,
               YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes
        FROM msgestionC.dbo.compras1 rc
        JOIN msgestion01art.dbo.articulo a ON rc.articulo = a.codigo
        WHERE rc.operacion = '+' AND LEFT(a.codigo_sinonimo, 10) IN ({filtro}) AND rc.fecha >= '{desde}'
        GROUP BY LEFT(a.codigo_sinonimo, 10), YEAR(rc.fecha), MONTH(rc.fecha)
    """
    df_compras = query_df(sql_compras)

    ventas_by_cs, compras_by_cs = {}, {}
    for _, r in df_ventas.iterrows():
        cs = r['csr'].strip()
        ventas_by_cs.setdefault(cs, {})[(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)
    for _, r in df_compras.iterrows():
        cs = r['csr'].strip()
        compras_by_cs.setdefault(cs, {})[(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    meses_lista = []
    cursor = hoy.replace(day=1)
    for _ in range(meses):
        meses_lista.append((cursor.year, cursor.month))
        cursor -= relativedelta(months=1)

    resultados = {}
    for cs in codigos_sinonimo:
        stock_actual = stock_dict.get(cs, 0)
        v_dict = ventas_by_cs.get(cs, {})
        c_dict = compras_by_cs.get(cs, {})
        stock_fin = stock_actual
        meses_q = meses_ok = ventas_total = ventas_ok = 0

        for anio, mes in meses_lista:
            v = v_dict.get((anio, mes), 0)
            c = c_dict.get((anio, mes), 0)
            stock_inicio = stock_fin + v - c
            ventas_total += v
            if stock_inicio <= 0:
                meses_q += 1
            else:
                meses_ok += 1
                ventas_ok += v
            stock_fin = stock_inicio

        vel_ap = ventas_total / max(meses, 1)
        vel_real = ventas_ok / max(meses_ok, 1) if meses_ok > 0 else vel_ap

        resultados[cs] = {
            'stock_actual': stock_actual, 'meses_quebrado': meses_q, 'meses_ok': meses_ok,
            'pct_quiebre': round(meses_q / max(meses, 1) * 100, 1),
            'vel_aparente': round(vel_ap, 2), 'vel_real': round(vel_real, 2),
            'ventas_total': ventas_total, 'ventas_ok': ventas_ok,
        }
    return resultados


def factor_estacional_batch(codigos_sinonimo, anios=3):
    if not codigos_sinonimo:
        return {}
    desde = (date.today() - relativedelta(years=anios)).replace(month=1, day=1)
    filtro = ",".join(f"'{c}'" for c in codigos_sinonimo)
    sql = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               MONTH(v.fecha) AS mes
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS} AND LEFT(a.codigo_sinonimo, 10) IN ({filtro}) AND v.fecha >= '{desde}'
        GROUP BY LEFT(a.codigo_sinonimo, 10), MONTH(v.fecha)
    """
    df = query_df(sql)
    resultados = {}
    for cs in codigos_sinonimo:
        df_cs = df[df['csr'].str.strip() == cs] if not df.empty else pd.DataFrame()
        if df_cs.empty:
            resultados[cs] = {m: 1.0 for m in range(1, 13)}
            continue
        ventas_mes = {int(r['mes']): float(r['cant'] or 0) for _, r in df_cs.iterrows()}
        media = sum(ventas_mes.values()) / max(len(ventas_mes), 1)
        resultados[cs] = {m: round(ventas_mes.get(m, media) / media, 3) if media > 0 else 1.0
                          for m in range(1, 13)}
    return resultados


@st.cache_data(ttl=120)
def obtener_pendientes():
    sql = f"""
        SELECT p1.articulo, a.codigo_sinonimo,
               SUM(p1.cantidad) AS cant_pendiente, SUM(p1.cantidad * p1.precio) AS monto_pendiente,
               p2.cuenta, RTRIM(ISNULL(p2.denominacion,'')) AS proveedor
        FROM msgestionC.dbo.pedico2 p2
        JOIN msgestionC.dbo.pedico1 p1 ON p1.empresa=p2.empresa AND p1.numero=p2.numero AND p1.codigo=p2.codigo
        JOIN msgestion01art.dbo.articulo a ON a.codigo = p1.articulo
        WHERE p2.codigo=8 AND p2.estado='V'
        GROUP BY p1.articulo, a.codigo_sinonimo, p2.cuenta, p2.denominacion
    """
    return query_df(sql)

def pendientes_por_sinonimo(df_pend):
    """Agrupa pendientes por CSR (10 chars) para matchear con los productos."""
    if df_pend.empty:
        return {}
    df_pend = df_pend.copy()
    df_pend['csr'] = df_pend['codigo_sinonimo'].str.strip().str[:10]
    return df_pend.groupby('csr').agg(
        cant_pendiente=('cant_pendiente', 'sum'), monto_pendiente=('monto_pendiente', 'sum')
    ).to_dict('index')


def obtener_precios_venta_batch(codigos_sinonimo):
    if not codigos_sinonimo:
        return {}
    filtro = ",".join(f"'{c}'" for c in codigos_sinonimo)
    sql = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(v.monto_facturado) / NULLIF(SUM(
                 CASE WHEN v.operacion='+' THEN v.cantidad WHEN v.operacion='-' THEN -v.cantidad END), 0) AS pv
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS} AND LEFT(a.codigo_sinonimo, 10) IN ({filtro})
          AND v.fecha >= DATEADD(month, -6, GETDATE()) AND v.monto_facturado > 0
        GROUP BY LEFT(a.codigo_sinonimo, 10)
    """
    df = query_df(sql)
    return {r['csr'].strip(): round(float(r['pv']), 2) for _, r in df.iterrows() if r['pv']}


@st.cache_data(ttl=300)
def cargar_resumen_marcas():
    desde = (date.today() - relativedelta(months=12)).replace(day=1)
    sql = f"""
        SELECT a.marca, a.proveedor,
               SUM(ISNULL(s.stk, 0)) AS stock_total, SUM(ISNULL(v.vtas, 0)) AS ventas_12m,
               COUNT(DISTINCT LEFT(a.codigo_sinonimo, 10)) AS productos
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN (SELECT articulo, SUM(stock_actual) AS stk FROM msgestionC.dbo.stock
                   WHERE deposito IN {DEPOS_SQL} GROUP BY articulo) s ON s.articulo = a.codigo
        LEFT JOIN (SELECT articulo, SUM(CASE WHEN operacion='+' THEN cantidad
                   WHEN operacion='-' THEN -cantidad END) AS vtas FROM msgestionC.dbo.ventas1
                   WHERE codigo NOT IN {EXCL_VENTAS} AND fecha >= '{desde}' GROUP BY articulo) v ON v.articulo = a.codigo
        WHERE a.estado = 'V' AND LEN(a.codigo_sinonimo) >= 10
          AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
          AND (ISNULL(s.stk, 0) > 0 OR ISNULL(v.vtas, 0) > 0)
        GROUP BY a.marca, a.proveedor
    """
    return query_df(sql)


@st.cache_data(ttl=300)
def cargar_productos_filtrado(marca_codigo=None, proveedor_num=None):
    desde = (date.today() - relativedelta(months=12)).replace(day=1)
    where_extra = ""
    if marca_codigo:
        where_extra = f"AND a.marca = {int(marca_codigo)}"
    elif proveedor_num:
        where_extra = f"AND a.proveedor = {int(proveedor_num)}"

    sql = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               MAX(RTRIM(ISNULL(a.descripcion_1,''))) AS descripcion,
               MAX(a.marca) AS marca, MAX(a.proveedor) AS proveedor,
               MAX(a.subrubro) AS subrubro, MAX(a.precio_fabrica) AS precio_fabrica,
               SUM(ISNULL(s.stk, 0)) AS stock_total, SUM(ISNULL(v.vtas, 0)) AS ventas_12m
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN (SELECT articulo, SUM(stock_actual) AS stk FROM msgestionC.dbo.stock
                   WHERE deposito IN {DEPOS_SQL} GROUP BY articulo) s ON s.articulo = a.codigo
        LEFT JOIN (SELECT articulo, SUM(CASE WHEN operacion='+' THEN cantidad
                   WHEN operacion='-' THEN -cantidad END) AS vtas FROM msgestionC.dbo.ventas1
                   WHERE codigo NOT IN {EXCL_VENTAS} AND fecha >= '{desde}' GROUP BY articulo) v ON v.articulo = a.codigo
        WHERE a.estado = 'V' {where_extra}
          AND LEN(a.codigo_sinonimo) >= 10 AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
          AND (ISNULL(s.stk, 0) > 0 OR ISNULL(v.vtas, 0) > 0)
        GROUP BY LEFT(a.codigo_sinonimo, 10)
    """
    df = query_df(sql)
    if df.empty:
        return df
    df['csr'] = df['csr'].str.strip()
    df['descripcion'] = df['descripcion'].str.strip()
    df['stock_total'] = df['stock_total'].astype(float)
    df['ventas_12m'] = df['ventas_12m'].astype(float)
    return df


@st.cache_data(ttl=600)
def cargar_marcas_dict():
    sql = "SELECT codigo, RTRIM(ISNULL(descripcion,'')) AS d FROM msgestion01art.dbo.marcas"
    df = query_df(sql)
    return {int(r['codigo']): (r['d'] or '').strip() for _, r in df.iterrows()} if not df.empty else {}

@st.cache_data(ttl=600)
def cargar_proveedores_dict():
    sql = "SELECT numero, RTRIM(ISNULL(denominacion,'')) AS n FROM msgestionC.dbo.proveedores WHERE motivo_baja='A'"
    df = query_df(sql)
    return {int(r['numero']): (r['n'] or '').strip() for _, r in df.iterrows()} if not df.empty else {}


# ============================================================================
# PROJECTION FUNCTIONS
# ============================================================================

def proyectar_waterfall(vel_diaria, stock_disponible, factores_est, ventanas=VENTANAS_DIAS):
    hoy = date.today()
    resultado = []
    for dias in ventanas:
        ventas_ventana = sum(vel_diaria * factores_est.get((hoy + timedelta(days=d)).month, 1.0)
                            for d in range(dias))
        stock_proj = stock_disponible - ventas_ventana
        status = 'rojo' if stock_proj <= 0 else ('amarillo' if stock_proj < ventas_ventana * 0.3 else 'verde')
        resultado.append({'dias': dias, 'ventas_proy': round(ventas_ventana, 1),
                          'stock_proy': round(stock_proj, 1), 'status': status})
    return resultado


def calcular_dias_cobertura(vel_diaria, stock_disponible, factores_est, max_dias=120):
    if vel_diaria <= 0:
        return max_dias
    hoy, stock = date.today(), stock_disponible
    for d in range(1, max_dias + 1):
        stock -= vel_diaria * factores_est.get((hoy + timedelta(days=d)).month, 1.0)
        if stock <= 0:
            return d
    return max_dias


def calcular_roi(precio_costo, precio_venta, vel_diaria, factores_est, cantidad_pedir, stock_disponible):
    if precio_costo <= 0 or cantidad_pedir <= 0 or vel_diaria <= 0:
        return {'dias_recupero': 999, 'roi_60d': 0, 'inversion': 0, 'margen_pct': 0}
    inversion = precio_costo * cantidad_pedir
    if precio_venta <= 0:
        precio_venta = precio_costo * 2
    margen_u = precio_venta - precio_costo
    hoy = date.today()
    ingreso_acum, dias_recupero = 0, 999
    for d in range(1, 121):
        factor = factores_est.get((hoy + timedelta(days=d)).month, 1.0)
        ingreso_acum += vel_diaria * factor * margen_u
        if ingreso_acum >= inversion and dias_recupero == 999:
            dias_recupero = d
    venta_60d = sum(vel_diaria * factores_est.get((hoy + timedelta(days=d)).month, 1.0) for d in range(1, 61))
    ingreso_60d = min(venta_60d, cantidad_pedir) * precio_venta
    roi_60d = ((ingreso_60d - inversion) / inversion * 100) if inversion > 0 else 0
    return {'dias_recupero': dias_recupero, 'roi_60d': round(roi_60d, 1),
            'inversion': round(inversion, 0), 'margen_pct': round(margen_u / precio_venta * 100, 1)}


# ============================================================================
# PLOTLY CHARTS
# ============================================================================

def chart_waterfall(wf_data, stock_hoy):
    """Waterfall chart real con barras cascada."""
    labels = ['Stock actual'] + [f'{w["dias"]}d ventas' for w in wf_data]
    values = [-w['ventas_proy'] for w in wf_data]
    measures = ['absolute'] + ['relative'] * len(wf_data)

    fig = go.Figure(go.Waterfall(
        x=labels, y=[stock_hoy] + values,
        measure=measures,
        connector=dict(line=dict(color='rgba(100,116,139,0.3)', width=1)),
        decreasing=dict(marker=dict(color=C_RED, line=dict(color=C_RED, width=0))),
        increasing=dict(marker=dict(color=C_GREEN, line=dict(color=C_GREEN, width=0))),
        totals=dict(marker=dict(color=C_BRAND, line=dict(color=C_BRAND, width=0))),
        textposition='outside',
        text=[f'{stock_hoy:.0f}'] + [f'{v:.0f}' for v in values],
        textfont=dict(size=11, color='#94A3B8'),
    ))
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', color='#94A3B8'),
        margin=dict(l=20, r=20, t=30, b=20), height=320,
        yaxis=dict(gridcolor='rgba(100,116,139,0.1)', zeroline=True,
                   zerolinecolor='rgba(239,68,68,0.5)', zerolinewidth=2),
        xaxis=dict(showgrid=False),
        showlegend=False,
    )
    return fig


def chart_estacionalidad(factores_est):
    """Heatmap de estacionalidad."""
    valores = [factores_est.get(m, 1.0) for m in range(1, 13)]
    mes_actual = date.today().month

    colors = []
    for i, v in enumerate(valores):
        if v < 0.5: colors.append(C_RED)
        elif v < 0.8: colors.append(C_AMBER)
        elif v < 1.2: colors.append(C_GREEN)
        else: colors.append(C_BRAND)

    fig = go.Figure(go.Bar(
        x=MESES_NOMBRES, y=valores,
        marker=dict(color=colors, line=dict(width=0)),
        text=[f'{v:.2f}' for v in valores],
        textposition='outside', textfont=dict(size=10, color='#94A3B8'),
    ))
    # Marcar mes actual
    fig.add_vline(x=mes_actual - 1, line=dict(color='white', width=1, dash='dot'),
                  annotation=dict(text='HOY', font=dict(size=10, color='white')))
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', color='#94A3B8'),
        margin=dict(l=20, r=20, t=10, b=20), height=200,
        yaxis=dict(gridcolor='rgba(100,116,139,0.1)', showgrid=True),
        xaxis=dict(showgrid=False), showlegend=False,
    )
    return fig


def chart_cobertura_gauge(dias_cob, max_dias=90):
    """Gauge de cobertura de stock."""
    color = C_RED if dias_cob < 15 else (C_AMBER if dias_cob < 30 else C_GREEN)
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=dias_cob,
        number=dict(suffix=" días", font=dict(size=36, color='#F1F5F9')),
        gauge=dict(
            axis=dict(range=[0, max_dias], tickcolor='#64748B',
                      tickfont=dict(color='#64748B')),
            bar=dict(color=color),
            bgcolor='#1E293B',
            bordercolor='rgba(255,255,255,0.06)',
            steps=[
                dict(range=[0, 15], color='rgba(239,68,68,0.1)'),
                dict(range=[15, 30], color='rgba(245,158,11,0.1)'),
                dict(range=[30, max_dias], color='rgba(16,185,129,0.1)'),
            ],
            threshold=dict(line=dict(color=C_RED, width=2), value=15),
        ),
    ))
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', color='#94A3B8'),
        margin=dict(l=30, r=30, t=30, b=10), height=220,
    )
    return fig


def chart_roi_ranking(df_ranking, presupuesto):
    """Treemap de inversión por producto coloreado por ROI."""
    if df_ranking.empty:
        return go.Figure()

    dentro = df_ranking[df_ranking['dentro_presupuesto']].head(30)
    if dentro.empty:
        return go.Figure()

    fig = px.treemap(
        dentro, path=['proveedor', 'descripcion'], values='inversion',
        color='dias_recupero', color_continuous_scale=['#10B981', '#F59E0B', '#EF4444'],
        range_color=[0, 90],
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', color='#94A3B8'),
        margin=dict(l=5, r=5, t=5, b=5), height=400,
        coloraxis_colorbar=dict(
            title=dict(text='Días recupero', font=dict(color='#94A3B8')),
            tickfont=dict(color='#94A3B8'),
        ),
    )
    return fig


def chart_urgencia_donut(df_f):
    """Donut chart de urgencia."""
    counts = df_f['urgencia'].value_counts()
    labels = counts.index.tolist()
    values = counts.values.tolist()
    color_map = {'CRITICO': C_RED, 'BAJO': C_AMBER, 'MEDIO': C_SLATE, 'OK': C_GREEN}
    colors = [color_map.get(l, C_SLATE) for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.65, marker=dict(colors=colors, line=dict(width=0)),
        textinfo='label+value', textfont=dict(size=11),
    ))
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter', color='#94A3B8'),
        margin=dict(l=5, r=5, t=5, b=5), height=260,
        showlegend=False,
    )
    return fig


# ============================================================================
# LOG
# ============================================================================

def guardar_log(entry):
    log = cargar_log()
    log.append(entry)
    with open(LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2, default=str)

def cargar_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    return []


# ============================================================================
# PAGES
# ============================================================================

def page_dashboard(df_f, marcas_dict, provs_dict, presupuesto):
    """Dashboard principal con KPIs y resumen."""
    df_f = df_f.copy()
    df_f['vel_mes'] = df_f['ventas_12m'] / 12
    df_f['vel_dia'] = df_f['vel_mes'] / 30
    df_f['dias_stock'] = np.where(df_f['vel_dia'] > 0, df_f['stock_total'] / df_f['vel_dia'], 999)
    df_f['urgencia'] = pd.cut(df_f['dias_stock'], bins=[-1, 15, 30, 60, 9999],
                              labels=['CRITICO', 'BAJO', 'MEDIO', 'OK'])

    criticos = int((df_f['urgencia'] == 'CRITICO').sum())
    bajos = int((df_f['urgencia'] == 'BAJO').sum())
    stock_t = int(df_f['stock_total'].sum())
    ventas_t = int(df_f['ventas_12m'].sum())

    # KPIs
    st.markdown(kpi_row([
        kpi_card("Productos", str(len(df_f)), "en selección actual", "blue"),
        kpi_card("Críticos", str(criticos), "menos de 15 días", "red"),
        kpi_card("Bajos", str(bajos), "15-30 días stock", "amber"),
        kpi_card("Stock total", f"{stock_t:,}", "pares en depósitos", "green"),
        kpi_card("Ventas 12m", f"{ventas_t:,}", "pares vendidos", "purple"),
    ]), unsafe_allow_html=True)

    # Layout: donut + top urgentes
    col_left, col_right = st.columns([1, 3])

    with col_left:
        st.markdown(section_title("Distribución urgencia"), unsafe_allow_html=True)
        st.plotly_chart(chart_urgencia_donut(df_f), use_container_width=True)

    with col_right:
        st.markdown(section_title("Top 25 — Mayor urgencia"), unsafe_allow_html=True)
        df_top = df_f.nsmallest(25, 'dias_stock')[
            ['descripcion', 'marca_desc', 'prov_nombre', 'stock_total',
             'ventas_12m', 'vel_mes', 'dias_stock', 'urgencia']
        ].copy()
        df_top['dias_stock'] = df_top['dias_stock'].round(0).astype(int)
        df_top['vel_mes'] = df_top['vel_mes'].round(1)

        st.dataframe(
            df_top, use_container_width=True, hide_index=True, height=360,
            column_config={
                'descripcion': st.column_config.TextColumn('Producto', width=220),
                'marca_desc': 'Marca', 'prov_nombre': 'Proveedor',
                'stock_total': st.column_config.NumberColumn('Stock', format="%d"),
                'ventas_12m': st.column_config.NumberColumn('Vtas 12m', format="%d"),
                'vel_mes': st.column_config.NumberColumn('Vel/mes', format="%.1f"),
                'dias_stock': st.column_config.NumberColumn('Días', format="%d"),
                'urgencia': 'Urgencia',
            },
        )

    # Resumen por marca
    st.markdown(section_title("Resumen por marca / proveedor"), unsafe_allow_html=True)
    resumen = df_f.groupby('marca_desc').agg(
        productos=('csr', 'count'), stock=('stock_total', 'sum'), ventas=('ventas_12m', 'sum'),
        criticos=('urgencia', lambda x: (x == 'CRITICO').sum()),
        bajos=('urgencia', lambda x: (x == 'BAJO').sum()),
    ).reset_index().sort_values('criticos', ascending=False)
    resumen['dias_prom'] = np.where(resumen['ventas'] > 0,
                                     (resumen['stock'] / (resumen['ventas'] / 365)).round(0), 999)
    st.dataframe(resumen, use_container_width=True, hide_index=True, height=300,
                 column_config={
                     'marca_desc': 'Marca', 'productos': 'Prods',
                     'stock': st.column_config.NumberColumn('Stock', format="%d"),
                     'ventas': st.column_config.NumberColumn('Ventas 12m', format="%d"),
                     'criticos': st.column_config.NumberColumn('Críticos', format="%d"),
                     'bajos': st.column_config.NumberColumn('Bajos', format="%d"),
                     'dias_prom': st.column_config.NumberColumn('Días stock', format="%d"),
                 })


def page_waterfall(df_f, lead_time=30):
    """Análisis waterfall detallado por producto."""
    df_sorted = df_f.copy()
    df_sorted['vel_dia'] = df_sorted['ventas_12m'] / 365
    df_sorted['dias_stock'] = np.where(df_sorted['vel_dia'] > 0,
                                        df_sorted['stock_total'] / df_sorted['vel_dia'], 999)
    df_sorted = df_sorted.sort_values('dias_stock')

    opciones = df_sorted.apply(
        lambda r: f"{r['descripcion'][:45]}  ·  Stock:{int(r['stock_total'])}  ·  Vtas:{int(r['ventas_12m'])}",
        axis=1).tolist()
    csrs = df_sorted['csr'].tolist()

    if not opciones:
        st.info("No hay productos para analizar.")
        return

    idx = st.selectbox(
        "Seleccionar producto",
        range(len(opciones)), format_func=lambda i: opciones[i], key="wf_sel",
        help="Productos ordenados por urgencia (menos stock primero). "
             "Stock negativo = ya debemos más de lo que tenemos."
    )
    csr_sel = csrs[idx]

    if st.button("⚡ Analizar", type="primary", key="btn_wf_go"):
        with st.spinner("Calculando quiebre + estacionalidad..."):
            q = analizar_quiebre_batch([csr_sel]).get(csr_sel, {})
            f_est = factor_estacional_batch([csr_sel]).get(csr_sel, {m: 1.0 for m in range(1, 13)})
            df_pend = obtener_pendientes()
            pend = pendientes_por_sinonimo(df_pend)
            cant_pend = pend.get(csr_sel, {}).get('cant_pendiente', 0)
            pv = obtener_precios_venta_batch([csr_sel]).get(csr_sel, 0)
            stock_actual = q.get('stock_actual', 0)
            vel_real = q.get('vel_real', 0)
            vel_diaria = vel_real / 30
            stock_disp = stock_actual + cant_pend

            # Waterfall con ventanas que arrancan DESPUÉS del lead time
            # Lógica: si pido hoy, llega en `lead_time` días.
            # Necesito saber cuánto stock tengo cuando llegue el pedido.
            ventanas_lt = [lead_time, lead_time + 15, lead_time + 30, lead_time + 60]
            wf = proyectar_waterfall(vel_diaria, stock_disp, f_est, ventanas=ventanas_lt)
            dias_cob = calcular_dias_cobertura(vel_diaria, stock_disp, f_est)

            # Necesidad: cubrir desde que llega el pedido (lead_time) hasta lead_time + 60
            hoy = date.today()
            nec_total = sum(vel_diaria * f_est.get((hoy + timedelta(days=d)).month, 1.0)
                            for d in range(lead_time + 60))
            pedir_sugerido = max(0, round(nec_total - stock_disp))

            st.session_state['wf_result'] = {
                'csr': csr_sel, 'q': q, 'f_est': f_est, 'wf': wf,
                'dias_cob': dias_cob, 'stock_disp': stock_disp,
                'cant_pend': cant_pend, 'vel_diaria': vel_diaria, 'pv': pv,
                'lead_time': lead_time, 'pedir_sugerido': pedir_sugerido,
                'ventanas_lt': ventanas_lt,
            }

    if 'wf_result' in st.session_state and st.session_state['wf_result'].get('csr') == csr_sel:
        data = st.session_state['wf_result']
        q, wf = data['q'], data['wf']
        lt = data.get('lead_time', lead_time)

        # KPIs
        st.markdown(kpi_row([
            kpi_card("Velocidad real", f"{q.get('vel_real', 0):.1f}",
                     "pares/mes (corregida por quiebre)", "blue"),
            kpi_card("Quiebre", f"{q.get('pct_quiebre', 0):.0f}%",
                     f"{q.get('meses_quebrado',0)} de {MESES_HISTORIA} meses sin stock",
                     "red" if q.get('pct_quiebre', 0) > 50 else "amber"),
            kpi_card("Stock disponible", f"{data['stock_disp']:.0f}",
                     f"depósitos {q.get('stock_actual',0):.0f} + pedido pendiente {data['cant_pend']:.0f}",
                     "green" if data['stock_disp'] > 0 else "red"),
            kpi_card("Cobertura", f"{data['dias_cob']}d",
                     "días hasta agotar stock al ritmo actual", "purple"),
        ]), unsafe_allow_html=True)

        # Sugerencia de pedido
        pedir = data.get('pedir_sugerido', 0)
        if pedir > 0:
            fecha_llegada = (date.today() + timedelta(days=lt)).strftime('%d/%m')
            st.markdown(f"""
            <div class="kpi-card amber" style="margin: 12px 0;">
                <div class="kpi-label">SUGERENCIA DE PEDIDO</div>
                <div class="kpi-value">{pedir} pares</div>
                <div class="kpi-sub">
                    Si pedís hoy, llega aprox. el <b>{fecha_llegada}</b> (lead time {lt}d).
                    Cubre demanda hasta {lt + 60} días con estacionalidad.
                </div>
            </div>""", unsafe_allow_html=True)

        # Waterfall cards — muestran stock en cada punto temporal
        st.markdown(section_title(
            f"Proyección de stock (lead time {lt}d + ventanas)"
        ), unsafe_allow_html=True)
        st.caption(f"Columna 1 = stock cuando llega el pedido ({lt}d). "
                   f"Las siguientes muestran cuánto queda después.")

        vlt = data.get('ventanas_lt', VENTANAS_DIAS)
        cards = "".join(
            wf_card_html(f"{vlt[i]}",  w['stock_proy'], w['ventas_proy'], w['status'])
            for i, w in enumerate(wf)
        )
        st.markdown(f'<div class="wf-grid">{cards}</div>', unsafe_allow_html=True)

        # Charts side by side
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown(section_title("Cascada de stock"), unsafe_allow_html=True)
            st.plotly_chart(chart_waterfall(wf, data['stock_disp']), use_container_width=True)
        with col2:
            st.markdown(section_title("Cobertura"), unsafe_allow_html=True)
            st.plotly_chart(chart_cobertura_gauge(data['dias_cob']), use_container_width=True)

        # Estacionalidad con explicación
        st.markdown(section_title("Estacionalidad — cómo varía la demanda en el año"), unsafe_allow_html=True)
        st.caption("Factor > 1.0 = meses de alta demanda. Factor < 1.0 = meses flojos. "
                   "La proyección waterfall usa estos factores día a día.")
        st.plotly_chart(chart_estacionalidad(data['f_est']), use_container_width=True)


def page_optimizar(df_f, presupuesto, provs_dict, lead_time=30):
    """Optimizador de presupuesto con ranking ROI."""
    min_ventas_roi = st.number_input("Ventas mínimas para analizar", value=10, min_value=1, key="min_vtas_roi")

    if st.button("🚀 Calcular ranking ROI", type="primary", key="btn_roi"):
        with st.spinner("Analizando quiebre + ROI de todos los productos..."):
            df_roi = df_f[df_f['ventas_12m'] >= min_ventas_roi].copy()
            df_roi['vel_dia'] = df_roi['ventas_12m'] / 365
            df_roi['dias_stock'] = np.where(df_roi['vel_dia'] > 0, df_roi['stock_total'] / df_roi['vel_dia'], 999)
            if len(df_roi) > 200:
                df_roi = df_roi.nsmallest(200, 'dias_stock')

            csrs = df_roi['csr'].tolist()
            quiebres = analizar_quiebre_batch(csrs)
            factores_all = factor_estacional_batch(csrs)
            precios_v = obtener_precios_venta_batch(csrs)
            pend_dict = pendientes_por_sinonimo(obtener_pendientes())

            rows = []
            for _, prod in df_roi.iterrows():
                csr = prod['csr']
                q = quiebres.get(csr, {})
                f_est = factores_all.get(csr, {m: 1.0 for m in range(1, 13)})
                vel_real = q.get('vel_real', 0)
                vel_d = vel_real / 30
                stock_a = q.get('stock_actual', prod['stock_total'])
                cant_p = pend_dict.get(csr, {}).get('cant_pendiente', 0)
                stock_d = stock_a + cant_p
                dias_cob = calcular_dias_cobertura(vel_d, stock_d, f_est)

                hoy = date.today()
                nec = sum(vel_d * f_est.get((hoy + timedelta(days=d)).month, 1.0) for d in range(lead_time + 60))
                pedir = max(0, round(nec - stock_d))
                if pedir <= 0:
                    continue

                pc = float(prod['precio_fabrica'] or 0)
                if pc <= 0:
                    continue
                pv = precios_v.get(csr, pc * 2)
                roi = calcular_roi(pc, pv, vel_d, f_est, pedir, stock_d)

                rows.append({
                    'csr': csr, 'descripcion': prod['descripcion'][:45],
                    'marca': prod.get('marca_desc', ''), 'proveedor': prod.get('prov_nombre', ''),
                    'stock': int(stock_a), 'pendiente': int(cant_p),
                    'vel_real': round(vel_real, 1), 'quiebre': q.get('pct_quiebre', 0),
                    'dias_cob': dias_cob, 'pedir': pedir, 'precio_costo': round(pc, 0),
                    'inversion': roi['inversion'], 'dias_recupero': roi['dias_recupero'],
                    'roi_60d': roi['roi_60d'], 'margen': roi['margen_pct'],
                })

            if rows:
                df_rank = pd.DataFrame(rows).sort_values('dias_recupero')
                df_rank['acum_inversion'] = df_rank['inversion'].cumsum()
                df_rank['dentro_presupuesto'] = df_rank['acum_inversion'] <= presupuesto
                st.session_state['df_ranking'] = df_rank

    if 'df_ranking' in st.session_state:
        df_rank = st.session_state['df_ranking']
        dentro = df_rank[df_rank['dentro_presupuesto']]
        fuera = df_rank[~df_rank['dentro_presupuesto']]

        inv_total = dentro['inversion'].sum()
        pct_usado = min(inv_total / presupuesto * 100, 100) if presupuesto > 0 else 0

        st.markdown(kpi_row([
            kpi_card("Productos", str(len(dentro)), "dentro del presupuesto", "blue"),
            kpi_card("Inversión", f"${inv_total:,.0f}", f"de ${presupuesto:,.0f}", "green"),
            kpi_card("Pares", f"{int(dentro['pedir'].sum()):,}", "a pedir", "purple"),
            kpi_card("Recupero prom", f"{dentro['dias_recupero'].mean():.0f}d" if len(dentro) else "N/A",
                     "promedio ponderado", "amber"),
        ]), unsafe_allow_html=True)

        # Budget bar
        st.markdown(f"""
        <div style="margin: 8px 0;">
            <div style="display:flex; justify-content:space-between; font-size:12px; color:#94A3B8;">
                <span>Presupuesto usado</span><span>{pct_usado:.0f}%</span>
            </div>
            <div class="budget-bar"><div class="budget-fill" style="width:{pct_usado}%"></div></div>
        </div>""", unsafe_allow_html=True)

        # Treemap
        st.markdown(section_title("Mapa de inversión (color = días recupero)"), unsafe_allow_html=True)
        st.plotly_chart(chart_roi_ranking(df_rank, presupuesto), use_container_width=True)

        # Tabla
        st.markdown(section_title(f"Ranking — {len(dentro)} productos dentro del presupuesto"), unsafe_allow_html=True)
        st.dataframe(
            dentro.drop(columns=['acum_inversion', 'dentro_presupuesto', 'csr']),
            use_container_width=True, hide_index=True, height=400,
            column_config={
                'descripcion': st.column_config.TextColumn('Producto', width=180),
                'marca': 'Marca', 'proveedor': 'Proveedor',
                'stock': st.column_config.NumberColumn('Stock', format="%d"),
                'pendiente': st.column_config.NumberColumn('Pend.', format="%d"),
                'vel_real': st.column_config.NumberColumn('Vel/mes', format="%.1f"),
                'quiebre': st.column_config.NumberColumn('Quiebre%', format="%.0f%%"),
                'dias_cob': st.column_config.NumberColumn('Cob.', format="%d"),
                'pedir': st.column_config.NumberColumn('Pedir', format="%d"),
                'precio_costo': st.column_config.NumberColumn('P.Costo', format="$%.0f"),
                'inversion': st.column_config.NumberColumn('Inversión', format="$%.0f"),
                'dias_recupero': st.column_config.NumberColumn('Recup.', format="%d d"),
                'roi_60d': st.column_config.NumberColumn('ROI 60d', format="%.1f%%"),
                'margen': st.column_config.NumberColumn('Margen', format="%.1f%%"),
            })

        if len(fuera) > 0:
            with st.expander(f"Fuera del presupuesto ({len(fuera)} productos)"):
                st.dataframe(fuera.drop(columns=['acum_inversion', 'dentro_presupuesto', 'csr']),
                             use_container_width=True, hide_index=True)


def page_carga():
    """Embebe la funcionalidad de carga de facturas."""
    st.markdown(section_title("Carga de facturas"), unsafe_allow_html=True)
    st.info("La funcionalidad de carga está disponible en `app_carga.py` (puerto 8503).")
    st.markdown(f"""
    <div class="kpi-card blue" style="max-width:400px;">
        <div class="kpi-label">Acceso rápido</div>
        <div class="kpi-value" style="font-size:16px;">
            <a href="http://192.168.2.112:8503" target="_blank" style="color:#3388FF; text-decoration:none;">
                Abrir Carga de Comprobantes →
            </a>
        </div>
        <div class="kpi-sub">Puerto 8503 en el mismo servidor</div>
    </div>
    """, unsafe_allow_html=True)


def page_historial():
    """Historial de pedidos."""
    log = cargar_log()
    if not log:
        st.info("No hay pedidos registrados todavía.")
        return

    df_log = pd.DataFrame(log).sort_values('fecha', ascending=False)
    st.dataframe(df_log, use_container_width=True, hide_index=True,
                 column_config={
                     'monto': st.column_config.NumberColumn(format="$%.0f"),
                     'presupuesto': st.column_config.NumberColumn(format="$%.0f"),
                 })


# ============================================================================
# MAIN
# ============================================================================

def main():
    # ── Sidebar ──
    st.sidebar.markdown("""
    <div style="text-align:center; padding: 16px 0 8px;">
        <div style="font-size:28px; font-weight:800; color:#F1F5F9;">⚡ H4</div>
        <div style="font-size:11px; color:#64748B; letter-spacing:2px; text-transform:uppercase;">
            Sistema Integrado
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.divider()

    pagina = st.sidebar.radio(
        "Navegación",
        ["📊 Dashboard", "🌊 Waterfall", "💰 Optimizar", "📄 Carga Facturas", "📋 Historial"],
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    st.sidebar.markdown('<div class="section-title">FILTROS</div>', unsafe_allow_html=True)

    marcas_dict = cargar_marcas_dict()
    provs_dict = cargar_proveedores_dict()

    with st.spinner(""):
        df_resumen = cargar_resumen_marcas()

    if df_resumen.empty:
        st.warning("Sin datos.")
        return

    df_resumen['marca_desc'] = df_resumen['marca'].map(
        lambda x: marcas_dict.get(int(x), f"#{int(x)}") if pd.notna(x) else "?")
    df_resumen['prov_nombre'] = df_resumen['proveedor'].map(
        lambda x: provs_dict.get(int(x), f"#{int(x)}") if pd.notna(x) else "?")

    # Búsqueda por nombre
    busqueda = st.sidebar.text_input(
        "Buscar marca o proveedor",
        placeholder="Ej: topper, ringo, alpargatas...",
        help="Escribí parte del nombre. Filtra marcas y proveedores que coincidan.",
        key="buscar_nombre"
    ).strip().upper()

    modo = st.sidebar.radio("Filtrar por", ["Marca", "Proveedor"], horizontal=True, label_visibility="collapsed")

    if modo == "Marca":
        top = df_resumen.groupby(['marca', 'marca_desc']).agg(
            ventas=('ventas_12m', 'sum')).reset_index().sort_values('ventas', ascending=False)
        top = top[top['ventas'] > 10]
        if busqueda:
            top = top[top['marca_desc'].str.upper().str.contains(busqueda, na=False)]
        if top.empty:
            st.sidebar.warning(f"No hay marcas con '{busqueda}'")
            return
        opts = top.apply(lambda r: f"{r['marca_desc']}  ({int(r['ventas'])} vtas/año)", axis=1).tolist()
        codes = top['marca'].tolist()
        sel = st.sidebar.selectbox("Marca", range(len(opts)), format_func=lambda i: opts[i], key="f_marca",
                                    help="Ventas anuales entre paréntesis. Mayor venta = más relevante.")
        marca_sel = int(codes[sel])
        prov_principal = int(df_resumen[df_resumen['marca'] == marca_sel].iloc[0]['proveedor'])
        df_f = cargar_productos_filtrado(marca_codigo=marca_sel)
    else:
        top = df_resumen.groupby(['proveedor', 'prov_nombre']).agg(
            ventas=('ventas_12m', 'sum')).reset_index().sort_values('ventas', ascending=False)
        top = top[top['ventas'] > 10]
        if busqueda:
            top = top[top['prov_nombre'].str.upper().str.contains(busqueda, na=False)]
        if top.empty:
            st.sidebar.warning(f"No hay proveedores con '{busqueda}'")
            return
        opts = top.apply(lambda r: f"{r['prov_nombre']}  ({int(r['ventas'])} vtas/año)", axis=1).tolist()
        codes = top['proveedor'].tolist()
        sel = st.sidebar.selectbox("Proveedor", range(len(opts)), format_func=lambda i: opts[i], key="f_prov",
                                    help="Razón social del proveedor. Ventas anuales entre paréntesis.")
        prov_principal = int(codes[sel])
        df_f = cargar_productos_filtrado(proveedor_num=prov_principal)

    # Lead time del proveedor seleccionado
    lead_time = LEAD_TIMES.get(prov_principal, LEAD_TIME_DEFAULT)
    prov_nombre_sel = provs_dict.get(prov_principal, f"#{prov_principal}")

    st.sidebar.divider()
    st.sidebar.markdown('<div class="section-title">PARÁMETROS</div>', unsafe_allow_html=True)

    lead_time = st.sidebar.number_input(
        f"Lead time — {prov_nombre_sel[:20]}",
        value=lead_time, min_value=1, max_value=120, step=5,
        help="Días desde que hacés el pedido hasta que llega la mercadería. "
             "Cambia cuánto necesitás pedir: si tarda 45 días, tenés que cubrir stock "
             "para los próximos 45 + 60 días.",
        key="lead_time"
    )

    min_v = st.sidebar.slider(
        "Ventas mínimas 12m", 0, 100, 5, key="min_v",
        help="Filtrar productos con pocas ventas. "
             "Un producto con menos de 5 ventas al año probablemente no vale la pena reponer."
    )

    presupuesto = st.sidebar.number_input(
        "Presupuesto ($)", value=5_000_000, step=500_000, format="%d",
        help="Cuánta plata tenés disponible para comprar. "
             "El optimizador ordena los productos por velocidad de recupero "
             "y te dice cuáles comprar primero para maximizar el retorno."
    )

    if df_f.empty:
        st.info("Sin productos.")
        return

    df_f['marca_desc'] = df_f['marca'].map(lambda x: marcas_dict.get(int(x), f"#{int(x)}") if pd.notna(x) else "?")
    df_f['prov_nombre'] = df_f['proveedor'].map(lambda x: provs_dict.get(int(x), f"#{int(x)}") if pd.notna(x) else "?")
    df_f = df_f[df_f['ventas_12m'] >= min_v]

    if df_f.empty:
        st.info("Sin productos con esos filtros.")
        return

    st.sidebar.caption(f"{len(df_f)} productos")

    # ── Router ──
    if "Dashboard" in pagina:
        page_dashboard(df_f, marcas_dict, provs_dict, presupuesto)
    elif "Waterfall" in pagina:
        page_waterfall(df_f, lead_time)
    elif "Optimizar" in pagina:
        page_optimizar(df_f, presupuesto, provs_dict, lead_time)
    elif "Carga" in pagina:
        page_carga()
    elif "Historial" in pagina:
        page_historial()


if __name__ == "__main__":
    main()
