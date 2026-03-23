#!/usr/bin/env python3
"""
app_reposicion.py — Reposición Inteligente con Waterfall ROI
=============================================================
Dashboard global de reposición de stock para H4/CALZALINDO.

Modelo:
  1. Velocidad REAL corregida por quiebre de stock
  2. Estacionalidad mensual (3 años historia)
  3. Proyección waterfall a 15/30/45/60 días
  4. Pedidos pendientes como stock en tránsito (se descuentan)
  5. Ranking por ROI: ¿en cuántos días recupero la inversión?
  6. Presupuesto como driver → optimizador que sugiere qué comprar primero

EJECUTAR:
  streamlit run app_reposicion.py --server.port 8503

Autor: Cowork + Claude — Marzo 2026
"""

import streamlit as st
import pandas as pd
import numpy as np
import pyodbc
import json
import os
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from config import (
    CONN_COMPRAS, CONN_ARTICULOS, PROVEEDORES,
    EMPRESA_DEFAULT, calcular_precios, get_conn_string
)
from proveedores_db import obtener_pricing_proveedor, listar_proveedores_activos

# PostgreSQL para embeddings (detección de sustitutos)
PG_CONN_STRING = "postgresql://guille:Martes13%23@200.58.109.125:5432/clz_productos"

# ============================================================================
# CONSTANTES
# ============================================================================

DEPOS_INFORMES = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 198)
DEPOS_SQL = '(0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)'
EXCL_VENTAS = '(7,36)'
EXCL_MARCAS_GASTOS = '(1316,1317,1158,436)'  # marcas de gastos, no mercadería
VENTANAS_DIAS = [15, 30, 45, 60]
MESES_HISTORIA = 12  # para quiebre
MESES_ESTACIONALIDAD = 36  # 3 años
LOG_FILE = os.path.join(os.path.dirname(__file__), 'pedidos_log.json')

CONN_REPLICA = get_conn_string("msgestionC")

# Conexión directa al 112 para pedidos ERP (con fix SSL legacy)
OPENSSL_LEGACY_CNF = os.path.join(os.path.dirname(__file__), '_scripts_oneshot', 'openssl_legacy.cnf')
_DRIVER_MAC = "ODBC Driver 17 for SQL Server"

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Reposición Inteligente",
    page_icon="🔄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CSS CUSTOM
# ============================================================================

st.markdown("""
<style>
    .semaforo-rojo { background-color: #ff4b4b; color: white; padding: 4px 12px;
                     border-radius: 12px; font-weight: bold; text-align: center; }
    .semaforo-amarillo { background-color: #ffa726; color: white; padding: 4px 12px;
                         border-radius: 12px; font-weight: bold; text-align: center; }
    .semaforo-verde { background-color: #66bb6a; color: white; padding: 4px 12px;
                      border-radius: 12px; font-weight: bold; text-align: center; }
    .kpi-box { background: #f8f9fa; border-radius: 8px; padding: 16px;
               border-left: 4px solid #1976d2; margin-bottom: 8px; }
    .waterfall-header { font-size: 13px; font-weight: 600; color: #555; }
    div[data-testid="stMetric"] { background: #1e1e2e; border: 1px solid #444; border-radius: 8px; padding: 12px; }
    div[data-testid="stMetric"] label { color: #b0b0b0 !important; font-size: 13px !important; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #ffffff !important; font-size: 28px !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATABASE HELPERS
# ============================================================================

def _crear_conexion():
    """Crea una conexión nueva a SQL Server."""
    try:
        return pyodbc.connect(CONN_COMPRAS, timeout=15)
    except Exception:
        return pyodbc.connect(CONN_REPLICA, timeout=15)


def get_conn(force_new=False):
    """Conexión a SQL Server con reconexión automática si se cayó."""
    if force_new or 'sql_conn' not in st.session_state:
        st.session_state['sql_conn'] = _crear_conexion()
    else:
        # Verificar que la conexión sigue viva
        try:
            st.session_state['sql_conn'].execute("SELECT 1")
        except Exception:
            try:
                st.session_state['sql_conn'].close()
            except Exception:
                pass
            st.session_state['sql_conn'] = _crear_conexion()
    return st.session_state['sql_conn']


def query_df(sql, conn=None):
    """Ejecuta query y retorna DataFrame. Reintenta con conexión nueva si falla."""
    c = conn or get_conn()
    try:
        return pd.read_sql(sql, c)
    except Exception as e:
        err_str = str(e)
        # Communication link failure o conexión cerrada → reintentar con conexión nueva
        if '08S01' in err_str or 'Communication link' in err_str or 'closed' in err_str.lower():
            try:
                c_new = get_conn(force_new=True)
                return pd.read_sql(sql, c_new)
            except Exception as e2:
                st.error(f"Error SQL (reintento): {e2}")
                return pd.DataFrame()
        st.error(f"Error SQL: {e}")
        return pd.DataFrame()


# ============================================================================
# ANÁLISIS DE QUIEBRE (core del sistema)
# ============================================================================

def analizar_quiebre_batch(codigos_sinonimo, meses=MESES_HISTORIA):
    """
    Analiza quiebre para MÚLTIPLES codigo_sinonimo en batch.
    Retorna dict {codigo_sinonimo: {stock_actual, meses_quebrado, vel_real, vel_aparente, ...}}
    """
    if not codigos_sinonimo:
        return {}

    hoy = date.today()
    desde = (hoy - relativedelta(months=meses)).replace(day=1)

    # Construir filtro IN
    filtro = ",".join(f"'{c}'" for c in codigos_sinonimo)

    # 1. Stock actual por codigo_sinonimo
    sql_stock = f"""
        SELECT a.codigo_sinonimo,
               ISNULL(SUM(s.stock_actual), 0) AS stock
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        WHERE a.codigo_sinonimo IN ({filtro})
          AND s.deposito IN {DEPOS_SQL}
        GROUP BY a.codigo_sinonimo
    """
    df_stock = query_df(sql_stock)
    stock_dict = {}
    for _, r in df_stock.iterrows():
        stock_dict[r['codigo_sinonimo'].strip()] = float(r['stock'])

    # 2. Ventas mensuales por codigo_sinonimo
    sql_ventas = f"""
        SELECT a.codigo_sinonimo,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.codigo_sinonimo IN ({filtro})
          AND v.fecha >= '{desde}'
        GROUP BY a.codigo_sinonimo, YEAR(v.fecha), MONTH(v.fecha)
    """
    df_ventas = query_df(sql_ventas)

    # 3. Compras mensuales por codigo_sinonimo
    sql_compras = f"""
        SELECT a.codigo_sinonimo,
               SUM(rc.cantidad) AS cant,
               YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes
        FROM msgestionC.dbo.compras1 rc
        JOIN msgestion01art.dbo.articulo a ON rc.articulo = a.codigo
        WHERE rc.operacion = '+'
          AND a.codigo_sinonimo IN ({filtro})
          AND rc.fecha >= '{desde}'
        GROUP BY a.codigo_sinonimo, YEAR(rc.fecha), MONTH(rc.fecha)
    """
    df_compras = query_df(sql_compras)

    # Organizar ventas y compras en dicts
    ventas_by_cs = {}
    for _, r in df_ventas.iterrows():
        cs = r['codigo_sinonimo'].strip()
        if cs not in ventas_by_cs:
            ventas_by_cs[cs] = {}
        ventas_by_cs[cs][(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    compras_by_cs = {}
    for _, r in df_compras.iterrows():
        cs = r['codigo_sinonimo'].strip()
        if cs not in compras_by_cs:
            compras_by_cs[cs] = {}
        compras_by_cs[cs][(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    # Lista de meses hacia atrás
    meses_lista = []
    cursor = hoy.replace(day=1)
    for _ in range(meses):
        meses_lista.append((cursor.year, cursor.month))
        cursor -= relativedelta(months=1)

    # Reconstruir quiebre para cada codigo_sinonimo
    resultados = {}
    for cs in codigos_sinonimo:
        stock_actual = stock_dict.get(cs, 0)
        v_dict = ventas_by_cs.get(cs, {})
        c_dict = compras_by_cs.get(cs, {})

        stock_fin = stock_actual
        meses_q = 0
        meses_ok = 0
        ventas_total = 0
        ventas_ok = 0

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
            'stock_actual': stock_actual,
            'meses_quebrado': meses_q,
            'meses_ok': meses_ok,
            'pct_quiebre': round(meses_q / max(meses, 1) * 100, 1),
            'vel_aparente': round(vel_ap, 2),
            'vel_real': round(vel_real, 2),
            'ventas_total': ventas_total,
            'ventas_ok': ventas_ok,
        }

    return resultados


# ============================================================================
# ESTACIONALIDAD
# ============================================================================

def factor_estacional_batch(codigos_sinonimo, anios=3):
    """Calcula factores estacionales en batch. Retorna dict {cs: {mes: factor}}."""
    if not codigos_sinonimo:
        return {}

    desde = (date.today() - relativedelta(years=anios)).replace(month=1, day=1)
    filtro = ",".join(f"'{c}'" for c in codigos_sinonimo)

    sql = f"""
        SELECT a.codigo_sinonimo,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               MONTH(v.fecha) AS mes
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.codigo_sinonimo IN ({filtro})
          AND v.fecha >= '{desde}'
        GROUP BY a.codigo_sinonimo, MONTH(v.fecha)
    """
    df = query_df(sql)
    if df.empty:
        return {cs: {m: 1.0 for m in range(1, 13)} for cs in codigos_sinonimo}

    resultados = {}
    for cs in codigos_sinonimo:
        df_cs = df[df['codigo_sinonimo'].str.strip() == cs]
        if df_cs.empty:
            resultados[cs] = {m: 1.0 for m in range(1, 13)}
            continue

        ventas_mes = {}
        for _, r in df_cs.iterrows():
            ventas_mes[int(r['mes'])] = float(r['cant'] or 0)

        media = sum(ventas_mes.values()) / max(len(ventas_mes), 1)
        if media <= 0:
            resultados[cs] = {m: 1.0 for m in range(1, 13)}
        else:
            resultados[cs] = {m: round(ventas_mes.get(m, media) / media, 3)
                              for m in range(1, 13)}

    return resultados


# ============================================================================
# PEDIDOS PENDIENTES (stock en tránsito)
# ============================================================================

@st.cache_data(ttl=120)
def obtener_pendientes():
    """Obtiene todos los pedidos pendientes (estado V) como stock en tránsito."""
    sql = f"""
        SELECT p1.articulo, a.codigo_sinonimo,
               SUM(p1.cantidad) AS cant_pendiente,
               SUM(p1.cantidad * p1.precio) AS monto_pendiente,
               p2.cuenta, RTRIM(p2.denominacion) AS proveedor
        FROM msgestionC.dbo.pedico2 p2
        JOIN msgestionC.dbo.pedico1 p1
             ON p1.empresa = p2.empresa AND p1.numero = p2.numero AND p1.codigo = p2.codigo
        JOIN msgestion01art.dbo.articulo a ON a.codigo = p1.articulo
        WHERE p2.codigo = 8 AND p2.estado = 'V'
        GROUP BY p1.articulo, a.codigo_sinonimo, p2.cuenta, p2.denominacion
    """
    return query_df(sql)


def pendientes_por_sinonimo(df_pend):
    """Agrupa pendientes por codigo_sinonimo."""
    if df_pend.empty:
        return {}
    df_pend['codigo_sinonimo'] = df_pend['codigo_sinonimo'].str.strip()
    grp = df_pend.groupby('codigo_sinonimo').agg(
        cant_pendiente=('cant_pendiente', 'sum'),
        monto_pendiente=('monto_pendiente', 'sum')
    ).to_dict('index')
    return grp


# ============================================================================
# PEDIDOS ERP (cruce con Top 30)
# ============================================================================

def _conn_112(base):
    """Conexión directa al 112 con fix SSL legacy para consultas de pedidos."""
    old_val = os.environ.get('OPENSSL_CONF')
    if os.path.exists(OPENSSL_LEGACY_CNF):
        os.environ['OPENSSL_CONF'] = OPENSSL_LEGACY_CNF
    try:
        conn_str = (
            f"DRIVER={{{_DRIVER_MAC}}};"
            f"SERVER=192.168.2.112;"
            f"DATABASE={base};"
            f"UID=am;PWD=dl;"
            f"Connection Timeout=15;"
            f"TrustServerCertificate=yes;Encrypt=no;"
        )
        return pyodbc.connect(conn_str, timeout=15)
    finally:
        if old_val is None:
            os.environ.pop('OPENSSL_CONF', None)
        else:
            os.environ['OPENSSL_CONF'] = old_val


@st.cache_data(ttl=120)
def obtener_pedidos_erp():
    """
    Consulta pedidos cargados (pedico2+pedico1) en ambas bases del ERP.
    Retorna DataFrame con: csr (10 dígitos), cant_pedida, fecha_entrega,
    proveedor (denominacion), estado, empresa.
    """
    sql_template = """
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(p1.cantidad) AS cant_pedida,
               MAX(p1.fecha_entrega) AS fecha_entrega,
               RTRIM(p2.denominacion) AS proveedor,
               p2.estado,
               '{empresa}' AS empresa
        FROM {base}.dbo.pedico2 p2
        JOIN {base}.dbo.pedico1 p1
             ON p1.empresa = p2.empresa AND p1.numero = p2.numero AND p1.codigo = p2.codigo
        JOIN msgestion01art.dbo.articulo a ON a.codigo = p1.articulo
        WHERE p2.codigo = 8
          AND LEN(a.codigo_sinonimo) >= 10
        GROUP BY LEFT(a.codigo_sinonimo, 10), p2.denominacion, p2.estado
    """
    queries = [
        (sql_template.format(base='MSGESTION01', empresa='CALZALINDO'), 'msgestion01'),
        (sql_template.format(base='MSGESTION03', empresa='H4'), 'msgestion03'),
    ]

    frames = []
    # Intentar primero por 112, fallback a conexión existente
    for sql, base in queries:
        try:
            conn_112 = _conn_112(base)
            df = pd.read_sql(sql, conn_112)
            conn_112.close()
        except Exception:
            # Fallback: usar msgestionC con la conexión existente
            sql_c = sql.replace(f'{base.upper()}.dbo.pedico2', 'msgestionC.dbo.pedico2')
            sql_c = sql_c.replace(f'{base.upper()}.dbo.pedico1', 'msgestionC.dbo.pedico1')
            df = query_df(sql_c)
        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame(columns=['csr', 'cant_pedida', 'fecha_entrega',
                                     'proveedor', 'estado', 'empresa'])
    df_all = pd.concat(frames, ignore_index=True)
    df_all['csr'] = df_all['csr'].str.strip()
    return df_all


def cruzar_pedidos_top(df_top, df_pedidos):
    """
    Cruza Top 30 urgentes con pedidos ERP.
    Agrega columnas: Pedido, Cant. Pedida, Fecha Entrega, Alerta (semáforo).
    """
    if df_pedidos.empty:
        df_top['Pedido'] = 'No'
        df_top['Cant. Pedida'] = 0
        df_top['Fecha Entrega'] = None
        df_top['Alerta'] = '🔴'
        return df_top

    # Solo pedidos vigentes (estado V = pendiente)
    df_vig = df_pedidos[df_pedidos['estado'] == 'V'].copy()

    # Agrupar por CSR: sumar cantidad, tomar fecha_entrega más próxima
    if df_vig.empty:
        ped_agg = pd.DataFrame(columns=['csr', 'cant_pedida', 'fecha_entrega'])
    else:
        ped_agg = df_vig.groupby('csr').agg(
            cant_pedida=('cant_pedida', 'sum'),
            fecha_entrega=('fecha_entrega', 'min')  # la más próxima
        ).reset_index()

    # Merge
    df_top = df_top.merge(ped_agg, on='csr', how='left')
    df_top['Pedido'] = np.where(df_top['cant_pedida'].fillna(0) > 0, 'Si', 'No')
    df_top['Cant. Pedida'] = df_top['cant_pedida'].fillna(0).astype(int)

    # Fecha de quiebre proyectada = hoy + dias_stock
    hoy = pd.Timestamp(date.today())
    df_top['fecha_quiebre'] = hoy + pd.to_timedelta(df_top['dias_stock'].clip(upper=999), unit='D')

    # Convertir fecha_entrega a datetime
    df_top['Fecha Entrega'] = pd.to_datetime(df_top['fecha_entrega'], errors='coerce')

    # Alerta semáforo
    def calcular_alerta(row):
        if row['Pedido'] == 'No':
            return '🔴'  # sin pedido
        fe = row['Fecha Entrega']
        fq = row['fecha_quiebre']
        if pd.isna(fe):
            return '🔴'
        # Margen: diferencia entre entrega y quiebre
        margen = (fq - fe).days
        if margen > 15:
            return '🟢'  # llega bien antes del quiebre
        elif margen >= 0:
            return '🟡'  # llega cerca
        else:
            return '🔴'  # llega tarde

    df_top['Alerta'] = df_top.apply(calcular_alerta, axis=1)

    # Limpiar columnas auxiliares
    df_top.drop(columns=['cant_pedida', 'fecha_entrega', 'fecha_quiebre'], inplace=True, errors='ignore')

    return df_top


# ============================================================================
# PRECIOS DE VENTA (para cálculo ROI)
# ============================================================================

def obtener_precios_venta_batch(codigos_sinonimo):
    """Obtiene precio promedio de venta ponderado por cantidad, últimos 6 meses."""
    if not codigos_sinonimo:
        return {}
    filtro = ",".join(f"'{c}'" for c in codigos_sinonimo)
    sql = f"""
        SELECT a.codigo_sinonimo,
               SUM(v.monto_facturado) / NULLIF(SUM(
                 CASE WHEN v.operacion='+' THEN v.cantidad
                      WHEN v.operacion='-' THEN -v.cantidad END), 0) AS precio_venta_prom
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.codigo_sinonimo IN ({filtro})
          AND v.fecha >= DATEADD(month, -6, GETDATE())
          AND v.monto_facturado > 0
        GROUP BY a.codigo_sinonimo
    """
    df = query_df(sql)
    result = {}
    for _, r in df.iterrows():
        cs = r['codigo_sinonimo'].strip()
        pv = float(r['precio_venta_prom']) if r['precio_venta_prom'] else 0
        result[cs] = round(pv, 2)
    return result


# ============================================================================
# ANÁLISIS GLOBAL: carga todos los productos activos con stock o ventas
# ============================================================================

@st.cache_data(ttl=300)
def cargar_resumen_marcas():
    """
    Resumen rápido por marca: stock total, ventas 12m, cant productos.
    Query liviana para el overview.
    """
    desde = (date.today() - relativedelta(months=12)).replace(day=1)
    sql = f"""
        SELECT a.marca, a.proveedor,
               SUM(ISNULL(s.stk, 0)) AS stock_total,
               SUM(ISNULL(v.vtas, 0)) AS ventas_12m,
               COUNT(DISTINCT LEFT(a.codigo_sinonimo, 10)) AS productos
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stk
            FROM msgestionC.dbo.stock
            WHERE deposito IN {DEPOS_SQL}
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        LEFT JOIN (
            SELECT articulo,
                   SUM(CASE WHEN operacion='+' THEN cantidad
                            WHEN operacion='-' THEN -cantidad END) AS vtas
            FROM msgestionC.dbo.ventas1
            WHERE codigo NOT IN {EXCL_VENTAS} AND fecha >= '{desde}'
            GROUP BY articulo
        ) v ON v.articulo = a.codigo
        WHERE a.estado = 'V'
          AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
          AND LEN(a.codigo_sinonimo) >= 10
          AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
          AND (ISNULL(s.stk, 0) > 0 OR ISNULL(v.vtas, 0) > 0)
        GROUP BY a.marca, a.proveedor
    """
    return query_df(sql)


@st.cache_data(ttl=300)
def cargar_productos_por_marca(marca_codigo):
    """
    Carga productos (CSR nivel 10) de UNA marca con stock o ventas 12m.
    Mucho más rápido que cargar todo de golpe.
    """
    desde = (date.today() - relativedelta(months=12)).replace(day=1)
    sql = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               MAX(a.descripcion_1) AS descripcion,
               MAX(a.marca) AS marca,
               MAX(a.proveedor) AS proveedor,
               MAX(a.subrubro) AS subrubro,
               MAX(a.precio_fabrica) AS precio_fabrica,
               SUM(ISNULL(s.stk, 0)) AS stock_total,
               SUM(ISNULL(v.vtas, 0)) AS ventas_12m
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stk
            FROM msgestionC.dbo.stock
            WHERE deposito IN {DEPOS_SQL}
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        LEFT JOIN (
            SELECT articulo,
                   SUM(CASE WHEN operacion='+' THEN cantidad
                            WHEN operacion='-' THEN -cantidad END) AS vtas
            FROM msgestionC.dbo.ventas1
            WHERE codigo NOT IN {EXCL_VENTAS} AND fecha >= '{desde}'
            GROUP BY articulo
        ) v ON v.articulo = a.codigo
        WHERE a.estado = 'V' AND a.marca = {int(marca_codigo)}
          AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
          AND LEN(a.codigo_sinonimo) >= 10
          AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
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


@st.cache_data(ttl=300)
def cargar_productos_por_proveedor(proveedor_num):
    """Carga productos de UN proveedor."""
    desde = (date.today() - relativedelta(months=12)).replace(day=1)
    sql = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               MAX(a.descripcion_1) AS descripcion,
               MAX(a.marca) AS marca,
               MAX(a.proveedor) AS proveedor,
               MAX(a.subrubro) AS subrubro,
               MAX(a.precio_fabrica) AS precio_fabrica,
               SUM(ISNULL(s.stk, 0)) AS stock_total,
               SUM(ISNULL(v.vtas, 0)) AS ventas_12m
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stk
            FROM msgestionC.dbo.stock
            WHERE deposito IN {DEPOS_SQL}
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        LEFT JOIN (
            SELECT articulo,
                   SUM(CASE WHEN operacion='+' THEN cantidad
                            WHEN operacion='-' THEN -cantidad END) AS vtas
            FROM msgestionC.dbo.ventas1
            WHERE codigo NOT IN {EXCL_VENTAS} AND fecha >= '{desde}'
            GROUP BY articulo
        ) v ON v.articulo = a.codigo
        WHERE a.estado = 'V' AND a.proveedor = {int(proveedor_num)}
          AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
          AND LEN(a.codigo_sinonimo) >= 10
          AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
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
    """Dict de marcas: {codigo: descripcion}.
    Usa msgestionC.dbo.marcas (836 registros) — NO msgestion01art que está vacía."""
    sql = "SELECT codigo, RTRIM(ISNULL(descripcion,'')) AS desc1 FROM msgestionC.dbo.marcas"
    df = query_df(sql)
    if df.empty:
        return {}
    result = {}
    for _, r in df.iterrows():
        cod = int(r['codigo'])
        desc = (r['desc1'] or '').strip()
        result[cod] = desc if desc else f"Marca {cod}"
    return result


@st.cache_data(ttl=600)
def cargar_proveedores_dict():
    """Dict de proveedores: {numero: denominacion}."""
    sql = "SELECT numero, RTRIM(ISNULL(denominacion,'')) AS nombre FROM msgestionC.dbo.proveedores WHERE motivo_baja='A'"
    df = query_df(sql)
    return {int(r['numero']): (r['nombre'] or '').strip() for _, r in df.iterrows()} if not df.empty else {}


# ============================================================================
# PROYECCIÓN WATERFALL
# ============================================================================

def proyectar_waterfall(vel_diaria, stock_disponible, factores_est, ventanas=VENTANAS_DIAS):
    """
    Proyecta stock a futuro en ventanas de días.

    vel_diaria: velocidad real diaria ajustada (sin estacionalidad, ya corregida por quiebre)
    stock_disponible: stock_actual + pendientes
    factores_est: dict {mes: factor}
    ventanas: [15, 30, 45, 60]

    Retorna: [
        {dias: 15, stock_proyectado: X, ventas_proyectadas: Y, status: 'rojo/amarillo/verde'},
        ...
    ]
    """
    hoy = date.today()
    resultado = []

    for dias in ventanas:
        # Calcular ventas proyectadas en la ventana
        ventas_ventana = 0
        for d in range(dias):
            fecha = hoy + timedelta(days=d)
            mes = fecha.month
            factor = factores_est.get(mes, 1.0)
            ventas_ventana += vel_diaria * factor

        stock_proj = stock_disponible - ventas_ventana

        # Semáforo
        if stock_proj <= 0:
            status = 'rojo'
        elif stock_proj < ventas_ventana * 0.3:  # menos de 30% de margen
            status = 'amarillo'
        else:
            status = 'verde'

        resultado.append({
            'dias': dias,
            'ventas_proy': round(ventas_ventana, 1),
            'stock_proy': round(stock_proj, 1),
            'status': status,
        })

    return resultado


def calcular_dias_cobertura(vel_diaria, stock_disponible, factores_est, max_dias=120):
    """Calcula en cuántos días se agota el stock."""
    if vel_diaria <= 0:
        return max_dias  # no se vende → cobertura infinita

    hoy = date.today()
    stock_restante = stock_disponible

    for d in range(1, max_dias + 1):
        fecha = hoy + timedelta(days=d)
        factor = factores_est.get(fecha.month, 1.0)
        stock_restante -= vel_diaria * factor
        if stock_restante <= 0:
            return d

    return max_dias


def calcular_roi(precio_costo, precio_venta, vel_diaria, factores_est,
                 cantidad_pedir, stock_disponible):
    """
    Calcula ROI y días de recupero de inversión.

    Lógica:
    - Inversión = precio_costo × cantidad_pedir
    - Venta diaria proyectada = vel_diaria × factor_estacional
    - Margen diario = venta_diaria × (precio_venta - precio_costo) / precio_venta
    - Días recupero = Inversión / margen_diario
    - ROI = (venta_60d - inversión) / inversión × 100
    """
    if precio_costo <= 0 or cantidad_pedir <= 0 or vel_diaria <= 0:
        return {'dias_recupero': 999, 'roi_60d': 0, 'inversion': 0, 'margen_pct': 0}

    inversion = precio_costo * cantidad_pedir

    if precio_venta <= 0:
        precio_venta = precio_costo * 2  # fallback 100% markup

    margen_unitario = precio_venta - precio_costo
    margen_pct = margen_unitario / precio_venta * 100

    # Ventas proyectadas a 60 días con estacionalidad
    hoy = date.today()
    venta_acum = 0
    ingreso_acum = 0
    dias_recupero = 999

    stock_nuevo = stock_disponible + cantidad_pedir

    for d in range(1, 121):  # hasta 120 días
        fecha = hoy + timedelta(days=d)
        factor = factores_est.get(fecha.month, 1.0)
        venta_dia = min(vel_diaria * factor, stock_nuevo - venta_acum)
        if venta_dia <= 0:
            break

        venta_acum += venta_dia
        ingreso_acum += venta_dia * margen_unitario

        if ingreso_acum >= inversion and dias_recupero == 999:
            dias_recupero = d

    # ROI a 60 días
    venta_60d = 0
    for d in range(1, 61):
        fecha = hoy + timedelta(days=d)
        factor = factores_est.get(fecha.month, 1.0)
        venta_60d += vel_diaria * factor

    ingreso_60d = min(venta_60d, cantidad_pedir) * precio_venta
    roi_60d = ((ingreso_60d - inversion) / inversion * 100) if inversion > 0 else 0

    return {
        'dias_recupero': dias_recupero,
        'roi_60d': round(roi_60d, 1),
        'inversion': round(inversion, 0),
        'margen_pct': round(margen_pct, 1),
        'ingreso_60d': round(ingreso_60d, 0),
    }


# ============================================================================
# ANÁLISIS COMPLETO POR PRODUCTO
# ============================================================================

def analizar_producto_detalle(csr, df_pendientes):
    """
    Análisis completo de un CSR: talles, quiebre, waterfall, ROI.
    """
    # Obtener talles
    sql = f"""
        SELECT a.codigo, a.codigo_sinonimo, a.descripcion_1, a.descripcion_5 AS talle,
               a.precio_fabrica, a.descuento, a.proveedor, a.marca,
               ISNULL((SELECT SUM(s.stock_actual) FROM msgestionC.dbo.stock s
                       WHERE s.articulo = a.codigo AND s.deposito IN {DEPOS_SQL}), 0) AS stock_actual
        FROM msgestion01art.dbo.articulo a
        WHERE a.codigo_sinonimo LIKE '{csr}%'
          AND LEN(a.codigo_sinonimo) > 10
          AND a.estado = 'V'
        ORDER BY a.descripcion_5
    """
    df_talles = query_df(sql)
    if df_talles.empty:
        return pd.DataFrame()

    # Ventas últimos 12 meses por talle
    desde = (date.today() - relativedelta(months=12)).replace(day=1)
    sql_v = f"""
        SELECT a.codigo_sinonimo, a.descripcion_5 AS talle,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS ventas_12m
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE a.codigo_sinonimo LIKE '{csr}%'
          AND v.fecha >= '{desde}' AND v.codigo NOT IN {EXCL_VENTAS}
        GROUP BY a.codigo_sinonimo, a.descripcion_5
    """
    df_v = query_df(sql_v)

    # Merge
    df_talles['codigo_sinonimo'] = df_talles['codigo_sinonimo'].str.strip()
    if not df_v.empty:
        df_v['codigo_sinonimo'] = df_v['codigo_sinonimo'].str.strip()
        df_talles = pd.merge(df_talles, df_v[['codigo_sinonimo', 'ventas_12m']],
                             on='codigo_sinonimo', how='left')
    else:
        df_talles['ventas_12m'] = 0

    df_talles['ventas_12m'] = df_talles['ventas_12m'].fillna(0).astype(float)
    df_talles['stock_actual'] = df_talles['stock_actual'].astype(float)

    # Pendientes por talle
    pend_dict = pendientes_por_sinonimo(df_pendientes)
    df_talles['pendiente'] = df_talles['codigo_sinonimo'].map(
        lambda x: pend_dict.get(x, {}).get('cant_pendiente', 0)
    )

    return df_talles


# ============================================================================
# INSERTAR PEDIDO EN ERP
# ============================================================================

def insertar_pedido_produccion(proveedor_id, empresa, renglones_df,
                                observaciones="", fecha_entrega=None):
    """Inserta pedido en producción usando paso4."""
    from paso4_insertar_pedido import insertar_pedido

    prov = PROVEEDORES.get(proveedor_id, {})
    if not prov:
        try:
            provs_bd = listar_proveedores_activos()
            prov = provs_bd.get(proveedor_id, {})
            if prov:
                pricing = obtener_pricing_proveedor(proveedor_id)
                prov.update(pricing)
        except Exception:
            pass

    nombre = prov.get("nombre", f"Proveedor #{proveedor_id}")
    fecha_hoy = date.today()

    cabecera = {
        "empresa": empresa,
        "cuenta": proveedor_id,
        "denominacion": nombre,
        "fecha_comprobante": fecha_hoy,
        "fecha_entrega": fecha_entrega or (fecha_hoy + timedelta(days=30)),
        "observaciones": observaciones,
    }

    renglones = []
    for _, r in renglones_df.iterrows():
        qty = int(r.get('pedir', 0))
        if qty > 0:
            renglones.append({
                "articulo": int(r['codigo']),
                "descripcion": str(r['descripcion_1'])[:60] + " " + str(r.get('talle', '')),
                "codigo_sinonimo": str(r['codigo_sinonimo']),
                "cantidad": qty,
                "precio": float(r.get('precio_fabrica', 0)),
            })

    if not renglones:
        return None, "No hay renglones con cantidad > 0"

    try:
        numero = insertar_pedido(cabecera, renglones, dry_run=False)
    except Exception as e:
        return None, f"Error al insertar: {e}"

    if numero:
        return numero, f"Pedido #{numero} insertado — {len(renglones)} renglones en {empresa}"
    return None, "Error desconocido al insertar pedido"


# ============================================================================
# LOG
# ============================================================================

# ============================================================================
# V2: MAPA DE SURTIDO POR CATEGORÍA
# ============================================================================

SUBRUBRO_DESC = {}  # se carga lazy

@st.cache_data(ttl=600)
def cargar_subrubro_desc():
    """Carga descripciones de subrubro desde msgestion01."""
    sql = "SELECT codigo, RTRIM(descripcion) AS desc1 FROM msgestion01.dbo.subrubro"
    df = query_df(sql)
    return {int(r['codigo']): (r['desc1'] or '').strip() for _, r in df.iterrows()} if not df.empty else {}


RUBRO_GENERO = {1: 'DAMAS', 3: 'HOMBRES', 4: 'NIÑOS', 5: 'NIÑAS', 6: 'UNISEX'}


@st.cache_data(ttl=300)
def cargar_mapa_surtido():
    """
    Mapa de surtido: demanda, stock y cobertura por género × categoría (subrubro).
    Incluye pirámide de precios (3 franjas por categoría).
    """
    desde = (date.today() - relativedelta(months=12)).replace(day=1)
    sql = f"""
        SELECT
            a.rubro AS genero_cod,
            a.subrubro AS sub_cod,
            COUNT(DISTINCT LEFT(a.codigo_sinonimo, 10)) AS modelos,
            SUM(ISNULL(s.stk, 0)) AS stock_total,
            SUM(ISNULL(v.vtas, 0)) AS ventas_12m,
            MIN(CASE WHEN a.precio_fabrica > 0 THEN a.precio_fabrica END) AS precio_min,
            MAX(a.precio_fabrica) AS precio_max,
            AVG(CASE WHEN a.precio_fabrica > 0 THEN a.precio_fabrica END) AS precio_avg
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stk
            FROM msgestionC.dbo.stock WHERE deposito IN {DEPOS_SQL}
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        LEFT JOIN (
            SELECT articulo,
                   SUM(CASE WHEN operacion='+' THEN cantidad
                            WHEN operacion='-' THEN -cantidad END) AS vtas
            FROM msgestionC.dbo.ventas1
            WHERE codigo NOT IN {EXCL_VENTAS} AND fecha >= '{desde}'
            GROUP BY articulo
        ) v ON v.articulo = a.codigo
        WHERE a.estado = 'V'
          AND a.rubro IN (1,3,4,5,6)
          AND a.subrubro IS NOT NULL AND a.subrubro > 0
          AND LEN(a.codigo_sinonimo) >= 10
          AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
          AND (ISNULL(s.stk, 0) > 0 OR ISNULL(v.vtas, 0) > 0)
        GROUP BY a.rubro, a.subrubro
        HAVING SUM(ISNULL(v.vtas, 0)) > 0
    """
    df = query_df(sql)
    if df.empty:
        return df

    df['genero'] = df['genero_cod'].map(RUBRO_GENERO).fillna('OTRO')
    sub_desc = cargar_subrubro_desc()
    df['categoria'] = df['sub_cod'].map(sub_desc).fillna('?')
    df['vel_diaria'] = df['ventas_12m'] / 365
    df['cobertura_dias'] = np.where(
        df['vel_diaria'] > 0,
        df['stock_total'] / df['vel_diaria'],
        999
    ).astype(int)
    df['urgencia'] = pd.cut(
        df['cobertura_dias'],
        bins=[-1, 30, 60, 120, 9999],
        labels=['CRITICO', 'BAJO', 'MEDIO', 'OK']
    )
    return df.sort_values('ventas_12m', ascending=False)


@st.cache_data(ttl=300)
def calcular_alertas_talles():
    """
    Calcula talles críticos para TODAS las categorías con quiebre por talle.
    Solo categorías tipo CALZADO (excluye accesorios, indumentaria).
    Retorna dict: (genero_cod, sub_cod) → list of {'talle', 'stock', 'vtas_12m', 'cob_dias'}
    Y un DataFrame resumen: genero_cod, sub_cod, talles_criticos (int), detalle (str)
    """
    meses = MESES_HISTORIA
    hoy = date.today()
    desde = (hoy - relativedelta(months=meses)).replace(day=1)

    calzado_filter = """
        a.estado = 'V' AND a.rubro IN (1,3,4,5,6)
          AND RTRIM(a.descripcion_5) LIKE '[0-9][0-9]'
          AND CASE WHEN RTRIM(a.descripcion_5) LIKE '[0-9][0-9]'
                   THEN CAST(a.descripcion_5 AS INT) END BETWEEN 17 AND 50
    """
    talle_key = "CAST(a.rubro AS VARCHAR) + '_' + CAST(a.subrubro AS VARCHAR) + '_' + RTRIM(a.descripcion_5)"

    # 1. Stock actual + ventas totales
    sql_base = f"""
        SELECT a.rubro AS genero_cod, a.subrubro AS sub_cod,
            RTRIM(a.descripcion_5) AS talle,
            COUNT(DISTINCT a.codigo) AS modelos,
            SUM(ISNULL(s.stk, 0)) AS stock,
            SUM(ISNULL(v.vtas, 0)) AS vtas_12m
        FROM msgestion01art.dbo.articulo a
        INNER JOIN msgestion01.dbo.regla_talle_subrubro rt
            ON rt.codigo_subrubro = a.subrubro AND rt.tipo_talle = 'CALZADO'
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stk
            FROM msgestionC.dbo.stock WHERE deposito IN {DEPOS_SQL}
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        LEFT JOIN (
            SELECT articulo,
                   SUM(CASE WHEN operacion='+' THEN cantidad
                            WHEN operacion='-' THEN -cantidad END) AS vtas
            FROM msgestionC.dbo.ventas1
            WHERE codigo NOT IN {EXCL_VENTAS} AND fecha >= '{desde}'
            GROUP BY articulo
        ) v ON v.articulo = a.codigo
        WHERE {calzado_filter}
          AND (ISNULL(s.stk, 0) > 0 OR ISNULL(v.vtas, 0) > 0)
        GROUP BY a.rubro, a.subrubro, RTRIM(a.descripcion_5)
        HAVING SUM(ISNULL(v.vtas, 0)) > 0
    """
    df = query_df(sql_base)
    if df.empty:
        return pd.DataFrame(), {}

    # 2. Ventas mensuales por talle-categoría
    sql_vtas_mes = f"""
        SELECT {talle_key} AS tkey,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS} AND {calzado_filter} AND v.fecha >= '{desde}'
        GROUP BY {talle_key}, YEAR(v.fecha), MONTH(v.fecha)
    """
    df_vtas_mes = query_df(sql_vtas_mes)

    # 3. Compras mensuales por talle-categoría
    sql_comp_mes = f"""
        SELECT {talle_key} AS tkey,
               SUM(rc.cantidad) AS cant,
               YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes
        FROM msgestionC.dbo.compras1 rc
        JOIN msgestion01art.dbo.articulo a ON rc.articulo = a.codigo
        WHERE rc.operacion = '+' AND {calzado_filter} AND rc.fecha >= '{desde}'
        GROUP BY {talle_key}, YEAR(rc.fecha), MONTH(rc.fecha)
    """
    df_comp_mes = query_df(sql_comp_mes)

    # Organizar en dicts
    vtas_dict = {}
    for _, r in df_vtas_mes.iterrows():
        tk = r['tkey'].strip() if r['tkey'] else ''
        if not tk:
            continue
        vtas_dict.setdefault(tk, {})[(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    comp_dict = {}
    for _, r in df_comp_mes.iterrows():
        tk = r['tkey'].strip() if r['tkey'] else ''
        if not tk:
            continue
        comp_dict.setdefault(tk, {})[(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    # Lista de meses hacia atrás
    meses_lista = []
    cursor = hoy.replace(day=1)
    for _ in range(meses):
        meses_lista.append((cursor.year, cursor.month))
        cursor -= relativedelta(months=1)

    # Reconstruir quiebre por talle y calcular cobertura
    df['talle_num'] = pd.to_numeric(df['talle'], errors='coerce')

    cob_list = []
    for _, row in df.iterrows():
        talle_val = row['talle'].strip() if row['talle'] else ''
        if not talle_val:
            cob_list.append(0)
            continue
        tkey = f"{int(row['genero_cod'])}_{int(row['sub_cod'])}_{talle_val}"
        stock_actual = float(row['stock'])
        v_d = vtas_dict.get(tkey, {})
        c_d = comp_dict.get(tkey, {})

        stock_fin = stock_actual
        meses_q = 0
        meses_ok = 0
        ventas_ok = 0

        for anio, mes in meses_lista:
            v = v_d.get((anio, mes), 0)
            c = c_d.get((anio, mes), 0)
            stock_inicio = stock_fin + v - c
            if stock_inicio <= 0:
                meses_q += 1
            else:
                meses_ok += 1
                ventas_ok += v
            stock_fin = stock_inicio

        vel_real = ventas_ok / max(meses_ok, 1) if meses_ok > 0 else float(row['vtas_12m']) / max(meses, 1)
        vel_diaria = vel_real / 30
        if vel_diaria > 0:
            cob = int(stock_actual / vel_diaria)
        elif stock_actual > 0:
            cob = 9999
        else:
            cob = 0
        cob_list.append(cob)

    df['cob_dias'] = cob_list
    # Crítico: cob < 30 días O stock 0 con demanda
    df['es_critico'] = (df['cob_dias'] <= 30) | ((df['vtas_12m'] > 0) & (df['stock'] == 0))

    # Construir resumen por categoría
    criticos = df[df['es_critico']].copy()
    detalle_dict = {}
    rows = []
    for (g, s), grp in criticos.groupby(['genero_cod', 'sub_cod']):
        talles_str = ", ".join(grp.sort_values('talle_num')['talle'].tolist())
        detalle_dict[(int(g), int(s))] = grp.sort_values('talle_num').to_dict('records')
        rows.append({
            'genero_cod': int(g), 'sub_cod': int(s),
            'talles_criticos': len(grp), 'talles_detalle': talles_str
        })

    df_resumen = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=['genero_cod', 'sub_cod', 'talles_criticos', 'talles_detalle'])
    return df_resumen, detalle_dict


@st.cache_data(ttl=300)
def cargar_piramide_precios(genero_cod, subrubro_cod):
    """
    Pirámide de precios: divide modelos de una categoría en 3 franjas
    (económica, media, premium) y muestra stock/demanda de cada una.
    """
    desde = (date.today() - relativedelta(months=12)).replace(day=1)
    sql = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               MAX(a.descripcion_1) AS descripcion,
               MAX(a.marca) AS marca,
               MAX(a.proveedor) AS proveedor,
               MAX(a.precio_fabrica) AS precio_fabrica,
               SUM(ISNULL(s.stk, 0)) AS stock_total,
               SUM(ISNULL(v.vtas, 0)) AS ventas_12m
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stk
            FROM msgestionC.dbo.stock WHERE deposito IN {DEPOS_SQL}
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        LEFT JOIN (
            SELECT articulo,
                   SUM(CASE WHEN operacion='+' THEN cantidad
                            WHEN operacion='-' THEN -cantidad END) AS vtas
            FROM msgestionC.dbo.ventas1
            WHERE codigo NOT IN {EXCL_VENTAS} AND fecha >= '{desde}'
            GROUP BY articulo
        ) v ON v.articulo = a.codigo
        WHERE a.estado = 'V' AND a.rubro = {genero_cod} AND a.subrubro = {subrubro_cod}
          AND LEN(a.codigo_sinonimo) >= 10
          AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
          AND a.precio_fabrica > 0
          AND (ISNULL(s.stk, 0) > 0 OR ISNULL(v.vtas, 0) > 0)
        GROUP BY LEFT(a.codigo_sinonimo, 10)
    """
    df = query_df(sql)
    if df.empty:
        return df, {}

    df['csr'] = df['csr'].str.strip()
    df['descripcion'] = df['descripcion'].str.strip()
    df['stock_total'] = df['stock_total'].astype(float)
    df['ventas_12m'] = df['ventas_12m'].astype(float)
    df['precio_fabrica'] = df['precio_fabrica'].astype(float)

    # Dividir en 3 franjas por percentiles
    try:
        df['franja'] = pd.qcut(df['precio_fabrica'], q=3,
                                labels=['ECONOMICA', 'MEDIA', 'PREMIUM'],
                                duplicates='drop')
    except ValueError:
        df['franja'] = 'UNICA'

    # Resumen por franja
    resumen = df.groupby('franja', observed=True).agg(
        modelos=('csr', 'count'),
        stock=('stock_total', 'sum'),
        ventas=('ventas_12m', 'sum'),
        precio_min=('precio_fabrica', 'min'),
        precio_max=('precio_fabrica', 'max'),
    ).to_dict('index')

    # Agregar cobertura a cada franja
    for franja, datos in resumen.items():
        vel = datos['ventas'] / 365 if datos['ventas'] > 0 else 0
        datos['cobertura_dias'] = int(datos['stock'] / vel) if vel > 0 else 999

    return df, resumen


# ============================================================================
# V2: ANÁLISIS POR TALLE (drill-down dentro de categoría)
# ============================================================================

@st.cache_data(ttl=300)
def cargar_talles_categoria(genero_cod, subrubro_cod):
    """
    Análisis por talle individual dentro de una categoría (género × subrubro).
    Usa descripcion_5 como talle principal, últimos 2 del sinónimo como fallback.
    Velocidad corregida por quiebre a nivel talle (reconstrucción de stock mes a mes).
    Retorna DataFrame con: talle, modelos, stock, ventas_12m, vel_real, pct_quiebre,
                           cobertura_dias, urgencia.
    """
    meses = MESES_HISTORIA
    hoy = date.today()
    desde = (hoy - relativedelta(months=meses)).replace(day=1)

    talle_expr = """COALESCE(
            NULLIF(RTRIM(a.descripcion_5), ''),
            CASE WHEN ISNUMERIC(RIGHT(RTRIM(a.codigo_sinonimo), 2)) = 1
                 THEN RIGHT(RTRIM(a.codigo_sinonimo), 2) END
        )"""

    # 1. Stock actual + modelos + ventas totales por talle
    sql_base = f"""
        SELECT {talle_expr} AS talle,
            COUNT(DISTINCT a.codigo) AS modelos,
            SUM(ISNULL(s.stk, 0)) AS stock,
            SUM(ISNULL(v.vtas, 0)) AS vtas_12m
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stk
            FROM msgestionC.dbo.stock WHERE deposito IN {DEPOS_SQL}
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        LEFT JOIN (
            SELECT articulo,
                   SUM(CASE WHEN operacion='+' THEN cantidad
                            WHEN operacion='-' THEN -cantidad END) AS vtas
            FROM msgestionC.dbo.ventas1
            WHERE codigo NOT IN {EXCL_VENTAS} AND fecha >= '{desde}'
            GROUP BY articulo
        ) v ON v.articulo = a.codigo
        WHERE a.estado = 'V'
          AND a.rubro = {genero_cod} AND a.subrubro = {subrubro_cod}
          AND (ISNULL(s.stk, 0) > 0 OR ISNULL(v.vtas, 0) > 0)
        GROUP BY {talle_expr}
        HAVING {talle_expr} IS NOT NULL
    """
    df = query_df(sql_base)
    if df.empty:
        return df

    # 2. Ventas mensuales por talle (para reconstruir quiebre)
    sql_vtas_mes = f"""
        SELECT {talle_expr} AS talle,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.estado = 'V' AND a.rubro = {genero_cod} AND a.subrubro = {subrubro_cod}
          AND v.fecha >= '{desde}'
        GROUP BY {talle_expr}, YEAR(v.fecha), MONTH(v.fecha)
        HAVING {talle_expr} IS NOT NULL
    """
    df_vtas_mes = query_df(sql_vtas_mes)

    # 3. Compras mensuales por talle
    sql_comp_mes = f"""
        SELECT {talle_expr} AS talle,
               SUM(rc.cantidad) AS cant,
               YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes
        FROM msgestionC.dbo.compras1 rc
        JOIN msgestion01art.dbo.articulo a ON rc.articulo = a.codigo
        WHERE rc.operacion = '+'
          AND a.estado = 'V' AND a.rubro = {genero_cod} AND a.subrubro = {subrubro_cod}
          AND rc.fecha >= '{desde}'
        GROUP BY {talle_expr}, YEAR(rc.fecha), MONTH(rc.fecha)
        HAVING {talle_expr} IS NOT NULL
    """
    df_comp_mes = query_df(sql_comp_mes)

    # Organizar ventas y compras en dicts por talle
    vtas_dict = {}  # {talle: {(anio,mes): cant}}
    for _, r in df_vtas_mes.iterrows():
        t = r['talle'].strip() if r['talle'] else ''
        vtas_dict.setdefault(t, {})[(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    comp_dict = {}
    for _, r in df_comp_mes.iterrows():
        t = r['talle'].strip() if r['talle'] else ''
        comp_dict.setdefault(t, {})[(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    # Lista de meses hacia atrás
    meses_lista = []
    cursor = hoy.replace(day=1)
    for _ in range(meses):
        meses_lista.append((cursor.year, cursor.month))
        cursor -= relativedelta(months=1)

    # Reconstruir quiebre por talle
    vel_reales = {}
    pct_quiebres = {}
    for _, row in df.iterrows():
        talle = row['talle'].strip() if row['talle'] else ''
        stock_actual = float(row['stock'])
        v_d = vtas_dict.get(talle, {})
        c_d = comp_dict.get(talle, {})

        stock_fin = stock_actual
        meses_q = 0
        meses_ok = 0
        ventas_ok = 0

        for anio, mes in meses_lista:
            v = v_d.get((anio, mes), 0)
            c = c_d.get((anio, mes), 0)
            stock_inicio = stock_fin + v - c

            if stock_inicio <= 0:
                meses_q += 1
            else:
                meses_ok += 1
                ventas_ok += v

            stock_fin = stock_inicio

        vel_real = ventas_ok / max(meses_ok, 1) if meses_ok > 0 else float(row['vtas_12m']) / max(meses, 1)
        vel_reales[talle] = round(vel_real, 2)
        pct_quiebres[talle] = round(meses_q / max(meses, 1) * 100, 1)

    df['talle'] = df['talle'].fillna('').str.strip()
    df['vel_real'] = df['talle'].map(vel_reales).fillna(0)
    df['pct_quiebre'] = df['talle'].map(pct_quiebres).fillna(0)

    # Intentar ordenar numéricamente
    df['talle_num'] = pd.to_numeric(df['talle'], errors='coerce')
    df = df.sort_values('talle_num', na_position='last').drop(columns='talle_num')

    # Cobertura con velocidad real
    df['vel_diaria'] = df['vel_real'] / 30
    cob_raw = np.where(
        df['vel_diaria'] > 0,
        df['stock'] / df['vel_diaria'],
        np.where(df['stock'] > 0, 9999, 0)
    )
    df['cob_dias'] = np.nan_to_num(cob_raw, nan=0, posinf=9999, neginf=0).astype(int)
    df['urgencia'] = df['cob_dias'].apply(
        lambda d: 'CRITICO' if d <= 30 else ('BAJO' if d <= 60 else ('MEDIO' if d <= 120 else 'OK'))
    )
    # Caso especial: tiene demanda pero 0 stock = CRITICO
    df.loc[(df['vtas_12m'] > 0) & (df['stock'] == 0), 'urgencia'] = 'CRITICO'
    df.loc[(df['vtas_12m'] > 0) & (df['stock'] == 0), 'cob_dias'] = 0

    return df.drop(columns='vel_diaria').reset_index(drop=True)


# ============================================================================
# V2: DETECCIÓN DE SUSTITUTOS (embeddings PostgreSQL)
# ============================================================================

def get_pg_conn():
    """Conexión a PostgreSQL para embeddings."""
    try:
        import psycopg2
        return psycopg2.connect(PG_CONN_STRING)
    except Exception as e:
        st.warning(f"Sin conexión a PostgreSQL (sustitutos no disponibles): {e}")
        return None


def buscar_sustitutos_embedding(codigo_mg, subrubro_cod, top_n=5):
    """
    Dado un artículo (por codigo de MS Gestión), busca los top_n más similares
    en la misma categoría (subrubro) usando embeddings.

    Link: producto_variantes.codigo_mg → productos.id (via producto_id)
    """
    conn = get_pg_conn()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        # Encontrar el producto_id via variante
        cur.execute("""
            SELECT DISTINCT p.id
            FROM producto_variantes pv
            JOIN productos p ON p.id = pv.producto_id
            WHERE pv.codigo_mg = %s AND p.embedding IS NOT NULL
            LIMIT 1
        """, (codigo_mg,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return []

        prod_id = row[0]

        # Buscar sustitutos en el mismo subrubro
        cur.execute("""
            SELECT p.id, p.nombre, p.familia_id, p.activo,
                   1 - (p.embedding <=> ref.embedding) AS similitud
            FROM productos p, productos ref
            WHERE ref.id = %s
              AND p.id != ref.id
              AND p.embedding IS NOT NULL
              AND p.subrubro_id = (SELECT id FROM prod_subrubros WHERE codigo_mg = %s LIMIT 1)
              AND p.activo = true
            ORDER BY p.embedding <=> ref.embedding
            LIMIT %s
        """, (prod_id, subrubro_cod, top_n))

        resultados = []
        for r in cur.fetchall():
            # Obtener un codigo_mg de las variantes de este producto
            cur.execute(
                "SELECT codigo_mg FROM producto_variantes WHERE producto_id = %s AND codigo_mg IS NOT NULL LIMIT 1",
                (r[0],)
            )
            var = cur.fetchone()
            cod_mg = var[0] if var else None

            resultados.append({
                'pg_id': r[0],
                'nombre': r[1],
                'familia_id': r[2],
                'activo': r[3],
                'similitud': round(r[4], 4),
                'codigo_mg': cod_mg,
            })

        conn.close()
        return resultados
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        return []


def buscar_sustitutos_activos_con_stock(codigo_mg, subrubro_cod):
    """
    Busca sustitutos por embedding Y verifica si tienen stock en SQL Server.
    Retorna solo los que tienen stock > 0.
    """
    sustitutos = buscar_sustitutos_embedding(codigo_mg, subrubro_cod)
    if not sustitutos:
        return []

    codigos = [s['codigo_mg'] for s in sustitutos if s['codigo_mg']]
    if not codigos:
        return []

    filtro = ",".join(str(c) for c in codigos)
    sql = f"""
        SELECT a.codigo, RTRIM(a.descripcion_1) AS desc1,
               a.precio_fabrica,
               ISNULL(SUM(s.stock_actual), 0) AS stock
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN msgestionC.dbo.stock s ON s.articulo = a.codigo AND s.deposito IN {DEPOS_SQL}
        WHERE a.codigo IN ({filtro}) AND a.estado = 'V'
        GROUP BY a.codigo, a.descripcion_1, a.precio_fabrica
        HAVING ISNULL(SUM(s.stock_actual), 0) > 0
    """
    df = query_df(sql)

    resultado = []
    for s in sustitutos:
        if not s['codigo_mg']:
            continue
        match = df[df['codigo'] == s['codigo_mg']]
        if not match.empty:
            r = match.iloc[0]
            s['stock'] = int(r['stock'])
            s['precio_fabrica'] = float(r['precio_fabrica'] or 0)
            s['desc_mg'] = r['desc1']
            resultado.append(s)

    return resultado


# ============================================================================
# DETECTOR DE TENDENCIA EMERGENTE
# ============================================================================

@st.cache_data(ttl=600)
def detectar_tendencias_emergentes():
    """
    Detecta productos que están naciendo fuertes.
    Criterios:
      - Primera venta hace menos de 6 meses O aceleración explosiva
      - Ventas crecientes mes a mes (pendiente positiva)
      - Velocidad actual > promedio de su categoría

    Retorna DataFrame rankeado por "momentum" (score compuesto).
    """
    hoy = date.today()
    hace_12 = (hoy - relativedelta(months=12)).replace(day=1)
    hace_6 = (hoy - relativedelta(months=6)).replace(day=1)
    hace_3 = (hoy - relativedelta(months=3)).replace(day=1)

    sql = f"""
        SELECT
            LEFT(a.codigo_sinonimo, 10) AS csr,
            MAX(a.descripcion_1) AS descripcion,
            MAX(a.marca) AS marca,
            MAX(a.proveedor) AS proveedor,
            MAX(a.subrubro) AS subrubro,
            MAX(a.rubro) AS rubro,
            MAX(a.precio_fabrica) AS precio_fabrica,
            MIN(v.fecha) AS primera_venta,
            SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                     WHEN v.operacion='-' THEN -v.cantidad END) AS vtas_total,
            SUM(CASE WHEN v.fecha < '{hace_6}'
                THEN (CASE WHEN v.operacion='+' THEN v.cantidad
                           WHEN v.operacion='-' THEN -v.cantidad END)
                ELSE 0 END) AS vtas_s1,
            SUM(CASE WHEN v.fecha >= '{hace_6}' AND v.fecha < '{hace_3}'
                THEN (CASE WHEN v.operacion='+' THEN v.cantidad
                           WHEN v.operacion='-' THEN -v.cantidad END)
                ELSE 0 END) AS vtas_q3,
            SUM(CASE WHEN v.fecha >= '{hace_3}'
                THEN (CASE WHEN v.operacion='+' THEN v.cantidad
                           WHEN v.operacion='-' THEN -v.cantidad END)
                ELSE 0 END) AS vtas_q4,
            ISNULL((
                SELECT SUM(s.stock_actual)
                FROM msgestionC.dbo.stock s
                JOIN msgestion01art.dbo.articulo a2 ON a2.codigo = s.articulo
                WHERE LEFT(a2.codigo_sinonimo, 10) = LEFT(a.codigo_sinonimo, 10)
                  AND s.deposito IN {DEPOS_SQL}
            ), 0) AS stock_actual
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND v.fecha >= '{hace_12}'
          AND a.estado = 'V'
          AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
          AND LEN(a.codigo_sinonimo) >= 10
          AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
        GROUP BY LEFT(a.codigo_sinonimo, 10)
        HAVING SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) > 3
    """
    df = query_df(sql)
    if df.empty:
        return df

    df['csr'] = df['csr'].str.strip()
    df['descripcion'] = df['descripcion'].str.strip()
    for c in ['vtas_total', 'vtas_s1', 'vtas_q3', 'vtas_q4', 'stock_actual', 'precio_fabrica']:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # ── Métricas de momentum ──

    # 1. Aceleración: Q4 vs Q3 (últimos 3 meses vs anteriores 3)
    df['aceleracion'] = np.where(
        df['vtas_q3'] > 0,
        ((df['vtas_q4'] - df['vtas_q3']) / df['vtas_q3'] * 100).round(1),
        np.where(df['vtas_q4'] > 0, 500, 0)  # producto nuevo sin historia
    )

    # 2. Es "nuevo"? primera venta en últimos 6 meses
    df['primera_venta'] = pd.to_datetime(df['primera_venta'])
    df['es_nuevo'] = df['primera_venta'] >= pd.Timestamp(hace_6)

    # 3. Concentración reciente: % de ventas totales que ocurrió en Q4
    df['pct_reciente'] = np.where(
        df['vtas_total'] > 0,
        (df['vtas_q4'] / df['vtas_total'] * 100).round(1),
        0
    )

    # 4. Velocidad mensual actual (Q4 = últimos 3 meses)
    df['vel_mensual'] = (df['vtas_q4'] / 3).round(1)

    # 5. Cobertura con velocidad actual
    df['dias_stock'] = np.where(
        df['vel_mensual'] > 0,
        (df['stock_actual'] / (df['vel_mensual'] / 30)).round(0),
        np.where(df['stock_actual'] > 0, 999, 0)
    )

    # 6. Score compuesto de momentum
    # Pesa: aceleración (40%), concentración reciente (30%), novedad (20%), velocidad (10%)
    df['aceleracion_norm'] = df['aceleracion'].clip(-100, 500) / 500
    df['pct_reciente_norm'] = df['pct_reciente'] / 100
    df['vel_norm'] = df['vel_mensual'] / df['vel_mensual'].quantile(0.95).clip(lower=1)
    df['vel_norm'] = df['vel_norm'].clip(0, 1)

    df['momentum'] = (
        df['aceleracion_norm'] * 0.4 +
        df['pct_reciente_norm'] * 0.3 +
        df['es_nuevo'].astype(float) * 0.2 +
        df['vel_norm'] * 0.1
    ).round(3)

    # Filtrar: solo los que realmente están creciendo
    df_emergentes = df[
        (df['aceleracion'] > 20) &  # acelerando >20%
        (df['vtas_q4'] >= 3) &  # mínimo 3 pares en Q4
        (df['pct_reciente'] >= 30)  # al menos 30% de ventas son recientes
    ].copy()

    df_emergentes = df_emergentes.sort_values('momentum', ascending=False)

    # Agregar nombres
    df_emergentes['genero'] = df_emergentes['rubro'].map(RUBRO_GENERO).fillna('?')

    return df_emergentes


@st.cache_data(ttl=600)
def velocidad_promedio_por_categoria():
    """Velocidad promedio mensual por rubro × subrubro (benchmark)."""
    desde = (date.today() - relativedelta(months=3)).replace(day=1)
    sql = f"""
        SELECT a.rubro, a.subrubro,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) / 3.0 AS vel_prom_cat
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS} AND v.fecha >= '{desde}'
          AND a.estado = 'V' AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
        GROUP BY a.rubro, a.subrubro
    """
    df = query_df(sql)
    if df.empty:
        return {}
    # Contar productos por categoría para sacar promedio por producto
    sql_count = f"""
        SELECT a.rubro, a.subrubro, COUNT(DISTINCT LEFT(a.codigo_sinonimo, 10)) AS n_prods
        FROM msgestion01art.dbo.articulo a
        WHERE a.estado = 'V' AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
          AND LEN(a.codigo_sinonimo) >= 10
        GROUP BY a.rubro, a.subrubro
    """
    df_n = query_df(sql_count)
    if df_n.empty:
        return {}

    merged = df.merge(df_n, on=['rubro', 'subrubro'], how='left')
    merged['vel_por_prod'] = merged['vel_prom_cat'] / merged['n_prods'].clip(lower=1)
    return {(int(r['rubro']), int(r['subrubro'])): round(float(r['vel_por_prod']), 2)
            for _, r in merged.iterrows()}


# ============================================================================
# CURVA DE TALLE IDEAL (reverse-engineered from 3 years of sales)
# ============================================================================

@st.cache_data(ttl=600)
def calcular_curva_talle_ideal(anios=3):
    """
    Reconstruye la distribución de talles REAL del mercado
    a partir de 3 años de ventas, por género × subrubro.
    Retorna DataFrame con: genero, subrubro, talle, pct_demanda (la curva ideal).
    """
    desde = (date.today() - relativedelta(years=anios)).replace(month=1, day=1)
    sql = f"""
        SELECT
            a.rubro AS genero_cod,
            a.subrubro AS sub_cod,
            RTRIM(a.descripcion_5) AS talle,
            SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                     WHEN v.operacion='-' THEN -v.cantidad END) AS vtas
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND v.fecha >= '{desde}'
          AND a.estado = 'V'
          AND a.rubro IN (1,3,4,5,6)
          AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
          AND RTRIM(a.descripcion_5) <> ''
          AND RTRIM(a.descripcion_5) LIKE '[0-9][0-9]'
          AND CASE WHEN RTRIM(a.descripcion_5) LIKE '[0-9][0-9]'
                   THEN CAST(a.descripcion_5 AS INT) END BETWEEN 17 AND 50
        GROUP BY a.rubro, a.subrubro, RTRIM(a.descripcion_5)
        HAVING SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) > 0
    """
    df = query_df(sql)
    if df.empty:
        return df

    df['talle_num'] = pd.to_numeric(df['talle'].str.replace(',', '.'), errors='coerce')
    df = df.dropna(subset=['talle_num'])
    df['vtas'] = df['vtas'].astype(float)

    # Calcular % por categoría
    totales = df.groupby(['genero_cod', 'sub_cod'])['vtas'].transform('sum')
    df['pct_demanda'] = (df['vtas'] / totales * 100).round(2)

    df['genero'] = df['genero_cod'].map(RUBRO_GENERO).fillna('OTRO')
    return df.sort_values(['genero_cod', 'sub_cod', 'talle_num'])


@st.cache_data(ttl=600)
def calcular_stock_por_talle():
    """
    Distribución ACTUAL de stock por género × subrubro × talle.
    Para comparar contra la curva ideal.
    """
    sql = f"""
        SELECT
            a.rubro AS genero_cod,
            a.subrubro AS sub_cod,
            RTRIM(a.descripcion_5) AS talle,
            SUM(ISNULL(s.stock_actual, 0)) AS stock
        FROM msgestion01art.dbo.articulo a
        JOIN msgestionC.dbo.stock s ON s.articulo = a.codigo
        WHERE s.deposito IN {DEPOS_SQL}
          AND a.estado = 'V'
          AND a.rubro IN (1,3,4,5,6)
          AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
          AND RTRIM(a.descripcion_5) <> ''
          AND RTRIM(a.descripcion_5) LIKE '[0-9][0-9]'
          AND CASE WHEN RTRIM(a.descripcion_5) LIKE '[0-9][0-9]'
                   THEN CAST(a.descripcion_5 AS INT) END BETWEEN 17 AND 50
        GROUP BY a.rubro, a.subrubro, RTRIM(a.descripcion_5)
        HAVING SUM(ISNULL(s.stock_actual, 0)) > 0
    """
    df = query_df(sql)
    if df.empty:
        return df

    df['talle_num'] = pd.to_numeric(df['talle'].str.replace(',', '.'), errors='coerce')
    df = df.dropna(subset=['talle_num'])
    df['stock'] = df['stock'].astype(float)

    totales = df.groupby(['genero_cod', 'sub_cod'])['stock'].transform('sum')
    df['pct_stock'] = (df['stock'] / totales * 100).round(2)
    return df


# ============================================================================
# CURVA IDEAL DESDE LÓGICA OMICRON (producto, marca+subrubro, ventas x mes)
# ============================================================================

@st.cache_data(ttl=600)
def calcular_curva_ideal_producto(csr, desde=None, hasta=None):
    """
    Curva ideal de talles para UN producto (CSR = 10 dígitos del sinónimo).
    Lógica omicron hc_graf3: porcent = vendidos_talle / total * 100
                             comprar = round(porcent / min(porcent>0), 0)
    Retorna DataFrame: nro (talle), vendidos, porcent, comprar
    """
    if desde is None:
        desde = (date.today() - relativedelta(years=3)).replace(month=1, day=1)
    if hasta is None:
        hasta = date.today()

    sql = f"""
        SELECT RTRIM(a.descripcion_5) AS nro,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS vendidos
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND LEFT(a.codigo_sinonimo, 10) = '{csr}'
          AND v.fecha >= '{desde}' AND v.fecha <= '{hasta}'
          AND RTRIM(a.descripcion_5) <> ''
        GROUP BY RTRIM(a.descripcion_5)
        HAVING SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) > 0
    """
    df = query_df(sql)
    if df.empty:
        return df

    df['nro'] = pd.to_numeric(df['nro'].str.replace(',', '.'), errors='coerce')
    df = df.dropna(subset=['nro'])
    df['vendidos'] = df['vendidos'].astype(float)
    df['porcent'] = (df['vendidos'] / df['vendidos'].sum() * 100).round(2)
    min_pos = df.loc[df['porcent'] > 0, 'porcent'].min()
    df['comprar'] = (df['porcent'] / min_pos).round(0).astype(int) if min_pos > 0 else 1
    return df.sort_values('nro')


@st.cache_data(ttl=600)
def calcular_curva_ideal_subrubro(marca, subrubro, desde=None, hasta=None):
    """
    Curva ideal de talles para TODOS los artículos de una marca+subrubro.
    Lógica omicron hc_graf4: usa todos los arts del mismo marca+subrubro.
    Ideal para productos nuevos sin historial (ej: Olympikus).
    Retorna DataFrame: nro (talle), vendidos, porcent, comprar
    """
    if desde is None:
        desde = (date.today() - relativedelta(years=3)).replace(month=1, day=1)
    if hasta is None:
        hasta = date.today()

    sql = f"""
        SELECT RTRIM(a.descripcion_5) AS nro,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS vendidos
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.marca = {marca} AND a.subrubro = {subrubro}
          AND v.fecha >= '{desde}' AND v.fecha <= '{hasta}'
          AND RTRIM(a.descripcion_5) <> ''
        GROUP BY RTRIM(a.descripcion_5)
        HAVING SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) > 0
    """
    df = query_df(sql)
    if df.empty:
        return df

    df['nro'] = pd.to_numeric(df['nro'].str.replace(',', '.'), errors='coerce')
    df = df.dropna(subset=['nro'])
    df['vendidos'] = df['vendidos'].astype(float)
    df['porcent'] = (df['vendidos'] / df['vendidos'].sum() * 100).round(2)
    min_pos = df.loc[df['porcent'] > 0, 'porcent'].min()
    df['comprar'] = (df['porcent'] / min_pos).round(0).astype(int) if min_pos > 0 else 1
    return df.sort_values('nro')


@st.cache_data(ttl=600)
def calcular_ventas_por_mes(marca=None, subrubro=None, csr=None, desde=None, hasta=None):
    """
    Ventas mensuales con promedio ponderado por años con data (lógica PID-223).
    Parámetros: csr (10 dígitos) O marca+subrubro.
    Retorna DataFrame: mes, vendidos, promedio_mensual
    """
    if desde is None:
        desde = (date.today() - relativedelta(years=3)).replace(month=1, day=1)
    if hasta is None:
        hasta = date.today()

    filtros = ""
    if csr:
        filtros += f" AND LEFT(a.codigo_sinonimo, 10) = '{csr}'"
    if marca:
        filtros += f" AND a.marca = {marca}"
    if subrubro:
        filtros += f" AND a.subrubro = {subrubro}"

    # PID-223: inner group by year-month, outer group by month with COUNT for avg
    sql = f"""
        SELECT CAST(SUM(i.items) AS INT) AS vendidos,
               i.mes AS mes,
               CAST(SUM(i.items) / COUNT(i.yeames) AS INT) AS promedio_mensual
        FROM (
            SELECT SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                            WHEN v.operacion='-' THEN -v.cantidad END) AS items,
                   CONCAT(YEAR(v.fecha), '-', MONTH(v.fecha)) AS yeames,
                   MONTH(v.fecha) AS mes
            FROM msgestionC.dbo.ventas1 v
            JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
            WHERE v.codigo NOT IN {EXCL_VENTAS}
              AND v.fecha >= '{desde}' AND v.fecha <= '{hasta}'
              {filtros}
            GROUP BY CONCAT(YEAR(v.fecha), '-', MONTH(v.fecha)), MONTH(v.fecha)
        ) i
        GROUP BY i.mes
    """
    df = query_df(sql)
    if df.empty:
        return df

    df['mes'] = df['mes'].astype(int)
    df['vendidos'] = df['vendidos'].astype(float)
    df['promedio_mensual'] = df['promedio_mensual'].astype(float)
    return df.sort_values('mes')


# ============================================================================
# DETECTOR DE CANIBALIZACIÓN POR EMBEDDING
# ============================================================================

@st.cache_data(ttl=600)
def obtener_ventas_semestrales():
    """
    Ventas por CSR (modelo) en dos semestres: S1 (hace 12-6 meses) y S2 (últimos 6 meses).
    Para detectar tendencia (subió o bajó).
    """
    hoy = date.today()
    hace_12 = (hoy - relativedelta(months=12)).replace(day=1)
    hace_6 = (hoy - relativedelta(months=6)).replace(day=1)

    sql = f"""
        SELECT
            LEFT(a.codigo_sinonimo, 10) AS csr,
            MAX(a.descripcion_1) AS descripcion,
            MAX(a.marca) AS marca,
            MAX(a.proveedor) AS proveedor,
            MAX(a.subrubro) AS subrubro,
            SUM(CASE WHEN v.fecha < '{hace_6}'
                THEN (CASE WHEN v.operacion='+' THEN v.cantidad
                           WHEN v.operacion='-' THEN -v.cantidad END)
                ELSE 0 END) AS vtas_s1,
            SUM(CASE WHEN v.fecha >= '{hace_6}'
                THEN (CASE WHEN v.operacion='+' THEN v.cantidad
                           WHEN v.operacion='-' THEN -v.cantidad END)
                ELSE 0 END) AS vtas_s2
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND v.fecha >= '{hace_12}'
          AND a.estado = 'V'
          AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
          AND LEN(a.codigo_sinonimo) >= 10
          AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
        GROUP BY LEFT(a.codigo_sinonimo, 10)
        HAVING SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) > 5
    """
    df = query_df(sql)
    if df.empty:
        return df

    df['csr'] = df['csr'].str.strip()
    df['descripcion'] = df['descripcion'].str.strip()
    df['vtas_s1'] = df['vtas_s1'].astype(float)
    df['vtas_s2'] = df['vtas_s2'].astype(float)
    df['delta_pct'] = np.where(
        df['vtas_s1'] > 0,
        ((df['vtas_s2'] - df['vtas_s1']) / df['vtas_s1'] * 100).round(1),
        np.where(df['vtas_s2'] > 0, 999, 0)  # nuevo producto
    )
    df['tendencia'] = np.where(df['delta_pct'] > 20, 'SUBE',
                      np.where(df['delta_pct'] < -20, 'BAJA', 'ESTABLE'))
    return df


def detectar_canibalizacion_embedding(csr_victima, subrubro_cod, df_ventas_sem):
    """
    Para un producto que BAJA, busca sustitutos por embedding que SUBEN.
    Eso es canibalización: un producto nuevo se comió al viejo.
    """
    # Obtener un codigo MG del CSR
    sql_cod = f"""
        SELECT TOP 1 a.codigo FROM msgestion01art.dbo.articulo a
        WHERE LEFT(a.codigo_sinonimo, 10) = '{csr_victima}' AND a.estado = 'V'
    """
    df_cod = query_df(sql_cod)
    if df_cod.empty:
        return []

    codigo_mg = int(df_cod.iloc[0]['codigo'])

    # Buscar similares por embedding
    sustitutos = buscar_sustitutos_embedding(codigo_mg, subrubro_cod, top_n=10)
    if not sustitutos:
        return []

    # Obtener CSR de cada sustituto
    codigos_sust = [s['codigo_mg'] for s in sustitutos if s['codigo_mg']]
    if not codigos_sust:
        return []

    filtro = ",".join(str(c) for c in codigos_sust)
    sql_csr = f"""
        SELECT a.codigo, LEFT(a.codigo_sinonimo, 10) AS csr
        FROM msgestion01art.dbo.articulo a
        WHERE a.codigo IN ({filtro})
    """
    df_csr = query_df(sql_csr)

    resultados = []
    for s in sustitutos:
        if not s['codigo_mg']:
            continue
        match_csr = df_csr[df_csr['codigo'] == s['codigo_mg']]
        if match_csr.empty:
            continue

        csr_sust = match_csr.iloc[0]['csr'].strip()
        # Buscar ventas semestrales de este sustituto
        match_ventas = df_ventas_sem[df_ventas_sem['csr'] == csr_sust]
        if match_ventas.empty:
            continue

        v = match_ventas.iloc[0]
        es_canibalizacion = v['tendencia'] == 'SUBE'

        resultados.append({
            'nombre': s['nombre'],
            'similitud': s['similitud'],
            'csr': csr_sust,
            'descripcion': v['descripcion'],
            'vtas_s1': int(v['vtas_s1']),
            'vtas_s2': int(v['vtas_s2']),
            'delta_pct': float(v['delta_pct']),
            'tendencia': v['tendencia'],
            'canibalizacion': es_canibalizacion,
        })

    # Ordenar: canibalización primero, luego por similitud
    resultados.sort(key=lambda x: (-x['canibalizacion'], -x['similitud']))
    return resultados


@st.cache_data(ttl=600)
def escaneo_canibalizacion_masivo(top_n=50):
    """
    Escaneo automático: busca TODOS los productos que bajaron >30%
    y para cada uno verifica si hay un sustituto similar que subió.
    Retorna lista de pares (víctima, caníbal, similitud, deltas).
    """
    df_sem = obtener_ventas_semestrales()
    if df_sem.empty:
        return pd.DataFrame()

    # Productos que bajan fuerte (>30%) con ventas significativas
    victimas = df_sem[
        (df_sem['tendencia'] == 'BAJA') &
        (df_sem['delta_pct'] < -30) &
        (df_sem['vtas_s1'] >= 10)  # mínimo 10 pares en S1
    ].nsmallest(top_n, 'delta_pct')

    if victimas.empty:
        return pd.DataFrame()

    # Para cada víctima, obtener un codigo MG
    csrs_victimas = victimas['csr'].tolist()
    filtro = ",".join(f"'{c}'" for c in csrs_victimas)
    sql_codigos = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               MIN(a.codigo) AS codigo_mg,
               MIN(a.subrubro) AS subrubro
        FROM msgestion01art.dbo.articulo a
        WHERE LEFT(a.codigo_sinonimo, 10) IN ({filtro}) AND a.estado = 'V'
        GROUP BY LEFT(a.codigo_sinonimo, 10)
    """
    df_codigos = query_df(sql_codigos)
    if df_codigos.empty:
        return pd.DataFrame()

    df_codigos['csr'] = df_codigos['csr'].str.strip()

    # Productos que suben (candidatos caníbal)
    candidatos_sube = df_sem[df_sem['tendencia'] == 'SUBE'].copy()

    pares = []
    conn_pg = get_pg_conn()
    if not conn_pg:
        return pd.DataFrame()

    try:
        cur = conn_pg.cursor()
        for _, vic in victimas.iterrows():
            csr_v = vic['csr']
            match_cod = df_codigos[df_codigos['csr'] == csr_v]
            if match_cod.empty:
                continue

            codigo_mg = int(match_cod.iloc[0]['codigo_mg'])
            subrubro = int(match_cod.iloc[0]['subrubro'])

            # Buscar producto en PG
            cur.execute("""
                SELECT DISTINCT p.id
                FROM producto_variantes pv
                JOIN productos p ON p.id = pv.producto_id
                WHERE pv.codigo_mg = %s AND p.embedding IS NOT NULL
                LIMIT 1
            """, (codigo_mg,))
            row = cur.fetchone()
            if not row:
                continue

            prod_id = row[0]

            # Buscar similares
            cur.execute("""
                SELECT p.id, p.nombre,
                       1 - (p.embedding <=> ref.embedding) AS similitud
                FROM productos p, productos ref
                WHERE ref.id = %s AND p.id != ref.id
                  AND p.embedding IS NOT NULL AND p.activo = true
                ORDER BY p.embedding <=> ref.embedding
                LIMIT 8
            """, (prod_id,))

            for r in cur.fetchall():
                # Obtener codigo_mg del sustituto
                cur.execute(
                    "SELECT codigo_mg FROM producto_variantes WHERE producto_id = %s AND codigo_mg IS NOT NULL LIMIT 1",
                    (r[0],)
                )
                var = cur.fetchone()
                if not var:
                    continue
                cod_sust = var[0]

                # Buscar CSR del sustituto
                sql_csr_s = f"""
                    SELECT LEFT(a.codigo_sinonimo, 10) AS csr
                    FROM msgestion01art.dbo.articulo a WHERE a.codigo = {cod_sust}
                """
                df_csr_s = query_df(sql_csr_s)
                if df_csr_s.empty:
                    continue

                csr_s = df_csr_s.iloc[0]['csr'].strip()

                # Buscar en candidatos que suben
                match_sube = candidatos_sube[candidatos_sube['csr'] == csr_s]
                if match_sube.empty:
                    continue

                can = match_sube.iloc[0]
                pares.append({
                    'victima': vic['descripcion'][:45],
                    'victima_csr': csr_v,
                    'victima_s1': int(vic['vtas_s1']),
                    'victima_s2': int(vic['vtas_s2']),
                    'victima_delta': float(vic['delta_pct']),
                    'canibal': can['descripcion'][:45],
                    'canibal_csr': csr_s,
                    'canibal_s1': int(can['vtas_s1']),
                    'canibal_s2': int(can['vtas_s2']),
                    'canibal_delta': float(can['delta_pct']),
                    'similitud': round(r[2], 3),
                })

        conn_pg.close()
    except Exception as e:
        try:
            conn_pg.close()
        except Exception:
            pass
        st.warning(f"Error en escaneo de canibalización: {e}")
        return pd.DataFrame()

    if not pares:
        return pd.DataFrame()

    df_pares = pd.DataFrame(pares)
    df_pares = df_pares.sort_values('similitud', ascending=False)
    # Deduplicar: un caníbal puede aparecer para varias víctimas
    df_pares = df_pares.drop_duplicates(subset=['victima_csr', 'canibal_csr'])
    return df_pares


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
# SIMULADOR DE RECUPERO DE INVERSIÓN
# ============================================================================

def simular_recupero_pedido(lineas_pedido):
    """
    Simula el recupero de inversión para un pedido de compra.

    lineas_pedido: list of dict con keys:
        codigo_sinonimo (CSR 10 o 12 dígitos), cantidad, precio_costo
        Opcionalmente: descripcion, talle

    Retorna dict con:
        - lineas: list of dict con métricas por línea
        - totales: dict con inversión, ingreso, margen, días promedio
    """
    if not lineas_pedido:
        return {'lineas': [], 'totales': {}}

    # Obtener CSRs únicos (nivel producto = 10 primeros dígitos)
    csrs_10 = list(set(l.get('codigo_sinonimo', '')[:10] for l in lineas_pedido))
    csrs_10 = [c for c in csrs_10 if len(c) >= 10]

    if not csrs_10:
        return {'lineas': [], 'totales': {}}

    # Batch: quiebre + precios venta
    quiebres = analizar_quiebre_batch(csrs_10)
    precios_venta = obtener_precios_venta_batch(csrs_10)
    factores_all = factor_estacional_batch(csrs_10)

    resultados = []
    for linea in lineas_pedido:
        cs = linea.get('codigo_sinonimo', '')
        csr_10 = cs[:10] if len(cs) >= 10 else cs
        cantidad = float(linea.get('cantidad', 0))
        precio_costo = float(linea.get('precio_costo', 0))

        if cantidad <= 0 or precio_costo <= 0:
            continue

        q = quiebres.get(csr_10, {})
        vel_real_mes = q.get('vel_real', 0)
        vel_diaria = vel_real_mes / 30
        pct_quiebre = q.get('pct_quiebre', 0)

        pv = precios_venta.get(csr_10, 0)
        if pv <= 0:
            pv = precio_costo * 2  # fallback

        # Días para vender todo el lote
        if vel_diaria > 0:
            dias_vender = cantidad / vel_diaria
        else:
            dias_vender = 9999

        inversion = cantidad * precio_costo
        ingreso_esperado = cantidad * pv
        margen = ingreso_esperado - inversion
        margen_pct = (margen / inversion * 100) if inversion > 0 else 0

        # Días recupero = inversión / (ingreso diario)
        # con estacionalidad: simular día a día
        f_est = factores_all.get(csr_10, {m: 1.0 for m in range(1, 13)})
        ingreso_acum = 0.0
        dias_recupero = 9999
        hoy = date.today()
        for d in range(min(int(dias_vender) + 1, 730)):
            fecha = hoy + timedelta(days=d)
            factor = f_est.get(fecha.month, 1.0)
            ingreso_dia = vel_diaria * factor * pv
            ingreso_acum += ingreso_dia
            if ingreso_acum >= inversion:
                dias_recupero = d + 1
                break

        if dias_recupero < 60:
            semaforo = 'verde'
        elif dias_recupero <= 120:
            semaforo = 'amarillo'
        else:
            semaforo = 'rojo'

        resultados.append({
            'codigo_sinonimo': cs,
            'descripcion': linea.get('descripcion', ''),
            'talle': linea.get('talle', ''),
            'cantidad': int(cantidad),
            'precio_costo': round(precio_costo, 0),
            'precio_venta': round(pv, 0),
            'vel_real_mes': round(vel_real_mes, 1),
            'pct_quiebre': round(pct_quiebre, 0),
            'dias_vender': min(round(dias_vender, 0), 9999),
            'inversion': round(inversion, 0),
            'ingreso_esperado': round(ingreso_esperado, 0),
            'margen': round(margen, 0),
            'margen_pct': round(margen_pct, 1),
            'dias_recupero': dias_recupero,
            'semaforo': semaforo,
        })

    if not resultados:
        return {'lineas': [], 'totales': {}}

    # Totales
    total_inversion = sum(r['inversion'] for r in resultados)
    total_ingreso = sum(r['ingreso_esperado'] for r in resultados)
    total_margen = sum(r['margen'] for r in resultados)
    # Días recupero promedio ponderado por inversión
    dias_ponderado = sum(r['dias_recupero'] * r['inversion'] for r in resultados)
    dias_prom = round(dias_ponderado / total_inversion) if total_inversion > 0 else 0
    margen_prom_pct = round(total_margen / total_inversion * 100, 1) if total_inversion > 0 else 0

    totales = {
        'inversion': total_inversion,
        'ingreso_esperado': total_ingreso,
        'margen': total_margen,
        'margen_pct': margen_prom_pct,
        'dias_recupero_prom': dias_prom,
        'pares': sum(r['cantidad'] for r in resultados),
        'lineas': len(resultados),
    }

    return {'lineas': resultados, 'totales': totales}


# ============================================================================
# UI: DASHBOARD GLOBAL
# ============================================================================

def render_semaforo(status):
    if status == 'rojo':
        return '<span class="semaforo-rojo">SIN STOCK</span>'
    elif status == 'amarillo':
        return '<span class="semaforo-amarillo">BAJO</span>'
    return '<span class="semaforo-verde">OK</span>'


def render_dashboard():
    """Pantalla principal: dashboard global con todos los productos."""

    st.title("🔄 Reposición Inteligente")
    st.caption("Waterfall ROI · Presupuesto como driver · Velocidad real con quiebre")

    # ── SIDEBAR ──
    st.sidebar.header("Filtros")

    marcas_dict = cargar_marcas_dict()
    provs_dict = cargar_proveedores_dict()

    # Resumen por marca (query rápida)
    with st.spinner("Cargando resumen..."):
        df_resumen = cargar_resumen_marcas()

    if df_resumen.empty:
        st.warning("No se encontraron productos con stock o ventas recientes.")
        return

    # Enriquecer resumen con nombres
    df_resumen['marca_desc'] = df_resumen['marca'].map(
        lambda x: marcas_dict.get(int(x), f"#{int(x)}") if pd.notna(x) else "Sin marca"
    )
    df_resumen['prov_nombre'] = df_resumen['proveedor'].map(
        lambda x: provs_dict.get(int(x), f"#{int(x)}") if pd.notna(x) else "Sin prov"
    )

    # Filtros sidebar: selección de marca O proveedor para drill-down
    modo_filtro = st.sidebar.radio("Filtrar por", ["Marca", "Proveedor"], horizontal=True)

    # Reset filtro opuesto al cambiar de modo (evita índice stale que apunta a marca/prov incorrecta)
    prev_modo = st.session_state.get('_modo_filtro_prev', None)
    if prev_modo is not None and prev_modo != modo_filtro:
        if modo_filtro == "Marca" and 'marca_filtro' in st.session_state:
            st.session_state['marca_filtro'] = 0
        elif modo_filtro == "Proveedor" and 'prov_filtro' in st.session_state:
            st.session_state['prov_filtro'] = 0
    st.session_state['_modo_filtro_prev'] = modo_filtro

    if modo_filtro == "Marca":
        # Top marcas por ventas
        top_marcas = df_resumen.groupby(['marca', 'marca_desc']).agg(
            ventas=('ventas_12m', 'sum'), stock=('stock_total', 'sum'), prods=('productos', 'sum')
        ).reset_index().sort_values('ventas', ascending=False)
        top_marcas = top_marcas[top_marcas['ventas'] > 10]

        opciones_marca = ["— Seleccionar marca —"] + top_marcas.apply(
            lambda r: f"{r['marca_desc']} ({int(r['ventas'])} vtas)", axis=1
        ).values.tolist()
        codigos_marca = [None] + top_marcas['marca'].tolist()

        sel_idx = st.sidebar.selectbox("Marca", range(len(opciones_marca)),
                                        format_func=lambda i: opciones_marca[i],
                                        key="marca_filtro")

        # Bounds check: clamp index if list changed (e.g., cache expired)
        if sel_idx >= len(codigos_marca):
            sel_idx = 0

        if sel_idx == 0:
            st.info("Seleccioná una marca en el sidebar para ver los productos.")
            return
        marca_sel_codigo = int(codigos_marca[sel_idx])

        with st.spinner(f"Cargando productos de {opciones_marca[sel_idx].split(' (')[0]}..."):
            df_f = cargar_productos_por_marca(marca_sel_codigo)
    else:
        # Top proveedores por ventas
        top_provs = df_resumen.groupby(['proveedor', 'prov_nombre']).agg(
            ventas=('ventas_12m', 'sum'), stock=('stock_total', 'sum'), prods=('productos', 'sum')
        ).reset_index().sort_values('ventas', ascending=False)
        top_provs = top_provs[top_provs['ventas'] > 10]

        opciones_prov = ["— Seleccionar proveedor —"] + top_provs.apply(
            lambda r: f"{r['prov_nombre']} ({int(r['ventas'])} vtas)", axis=1
        ).values.tolist()
        codigos_prov = [None] + top_provs['proveedor'].tolist()

        sel_idx_p = st.sidebar.selectbox("Proveedor", range(len(opciones_prov)),
                                          format_func=lambda i: opciones_prov[i],
                                          key="prov_filtro")

        # Bounds check: clamp index if list changed
        if sel_idx_p >= len(codigos_prov):
            sel_idx_p = 0

        if sel_idx_p == 0:
            st.info("Seleccioná un proveedor en el sidebar para ver los productos.")
            return
        prov_sel_codigo = int(codigos_prov[sel_idx_p])

        with st.spinner(f"Cargando productos de {opciones_prov[sel_idx_p].split(' (')[0]}..."):
            df_f = cargar_productos_por_proveedor(prov_sel_codigo)

    min_ventas = st.sidebar.number_input("Ventas mínimas 12m", value=5, min_value=0)

    presupuesto = st.sidebar.number_input(
        "Presupuesto disponible ($)", value=5_000_000, step=500_000,
        format="%d", help="El optimizador sugiere qué comprar primero dentro de este presupuesto"
    )

    if df_f.empty:
        st.info("No hay productos con los filtros seleccionados.")
        return

    # Enriquecer productos
    df_f['marca_desc'] = df_f['marca'].map(
        lambda x: marcas_dict.get(int(x), f"#{int(x)}") if pd.notna(x) else "Sin marca"
    )
    df_f['prov_nombre'] = df_f['proveedor'].map(
        lambda x: provs_dict.get(int(x), f"#{int(x)}") if pd.notna(x) else "Sin prov"
    )

    # Aplicar filtro de ventas mínimas
    df_f = df_f[df_f['ventas_12m'] >= min_ventas]

    if df_f.empty:
        st.info("No hay productos con los filtros seleccionados.")
        return

    st.sidebar.markdown(f"**{len(df_f)} productos**")

    # ── TABS ──
    (tab_surtido, tab_dashboard, tab_waterfall, tab_optimizar,
     tab_curva, tab_canibal, tab_emergentes, tab_pedido, tab_historial) = st.tabs([
        "🗺️ Mapa Surtido", "📊 Dashboard", "🌊 Waterfall", "💰 Optimizar Compra",
        "👟 Curva Talle", "🔬 Canibalización", "🚀 Emergentes",
        "🛒 Armar Pedido", "📋 Historial"
    ])

    # ══════════════════════════════════════════════════════════════
    # TAB 0: MAPA DE SURTIDO POR CATEGORÍA (V2)
    # ══════════════════════════════════════════════════════════════
    with tab_surtido:
        st.subheader("Mapa de Surtido por Categoria")
        st.caption("Cobertura por genero x subrubro. Rojo = menos de 30 dias. Drill-down a piramide de precios y sustitutos.")

        with st.spinner("Cargando mapa de surtido..."):
            df_mapa = cargar_mapa_surtido()
            df_alertas_talles, detalle_talles_dict = calcular_alertas_talles()

        if df_mapa.empty:
            st.warning("No se pudo cargar el mapa de surtido.")
        else:
            # Merge talles críticos al mapa
            if not df_alertas_talles.empty:
                df_mapa = df_mapa.merge(
                    df_alertas_talles[['genero_cod', 'sub_cod', 'talles_criticos', 'talles_detalle']],
                    on=['genero_cod', 'sub_cod'], how='left'
                )
            else:
                df_mapa['talles_criticos'] = 0
                df_mapa['talles_detalle'] = ''
            df_mapa['talles_criticos'] = df_mapa['talles_criticos'].fillna(0).astype(int)
            df_mapa['talles_detalle'] = df_mapa['talles_detalle'].fillna('')

            # ── PANEL DE ALERTAS: talles críticos ──
            alertas_activas = df_mapa[df_mapa['talles_criticos'] > 0].sort_values(
                'talles_criticos', ascending=False)
            if not alertas_activas.empty:
                total_talles_crit = int(alertas_activas['talles_criticos'].sum())
                st.error(f"⚠️ **{total_talles_crit} talles críticos** en {len(alertas_activas)} categorías — stock 0 con demanda o menos de 30 días")
                with st.expander(f"Ver detalle de {total_talles_crit} talles críticos", expanded=False):
                    for _, row in alertas_activas.head(15).iterrows():
                        st.markdown(
                            f"**{row['genero']} > {row['categoria']}** — "
                            f"Talles: `{row['talles_detalle']}` "
                            f"(cat. cob: {row['cobertura_dias']}d = {row['urgencia']})"
                        )

            # KPIs globales del surtido
            c1, c2, c3, c4 = st.columns(4)
            criticos_cat = len(df_mapa[df_mapa['urgencia'] == 'CRITICO'])
            bajos_cat = len(df_mapa[df_mapa['urgencia'] == 'BAJO'])
            total_talles_crit_all = int(df_mapa['talles_criticos'].sum())
            c1.metric("Categorias activas", len(df_mapa))
            c2.metric("Cat. CRITICAS (<30d)", criticos_cat)
            c3.metric("Talles criticos", total_talles_crit_all)
            c4.metric("Stock total (pares)", f"{int(df_mapa['stock_total'].sum()):,}")

            st.divider()

            # Filtros
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                generos_disp = sorted(df_mapa['genero'].unique())
                genero_filtro = st.multiselect("Filtrar genero", generos_disp,
                                                default=generos_disp, key="surtido_genero")
            df_vis = df_mapa[df_mapa['genero'].isin(genero_filtro)].copy()
            with fc2:
                cats_disp = sorted(df_vis['categoria'].unique())
                cat_filtro = st.multiselect("Filtrar categoria", cats_disp,
                                             default=cats_disp, key="surtido_cat")
            df_vis = df_vis[df_vis['categoria'].isin(cat_filtro)].copy()
            with fc3:
                urgencias_disp = sorted(df_vis['urgencia'].dropna().unique())
                urg_filtro = st.multiselect("Filtrar urgencia", urgencias_disp,
                                             default=urgencias_disp, key="surtido_urg")
            df_vis = df_vis[df_vis['urgencia'].isin(urg_filtro)].copy()

            # Checkbox: solo categorías con talles críticos
            solo_con_alerta = st.checkbox("Solo categorias con talles criticos", value=False, key="solo_alerta")
            if solo_con_alerta:
                df_vis = df_vis[df_vis['talles_criticos'] > 0].copy()

            # Tabla principal
            st.dataframe(
                df_vis[['genero', 'categoria', 'modelos', 'stock_total', 'ventas_12m',
                        'cobertura_dias', 'urgencia', 'talles_criticos', 'talles_detalle',
                        'precio_min', 'precio_max']],
                column_config={
                    'genero': st.column_config.TextColumn('Genero', width=90),
                    'categoria': st.column_config.TextColumn('Categoria', width=150),
                    'modelos': st.column_config.NumberColumn('Modelos', format="%d"),
                    'stock_total': st.column_config.NumberColumn('Stock', format="%d"),
                    'ventas_12m': st.column_config.NumberColumn('Vtas 12m', format="%d"),
                    'cobertura_dias': st.column_config.NumberColumn('Cob. dias', format="%d"),
                    'urgencia': 'Urgencia',
                    'talles_criticos': st.column_config.NumberColumn('T.Crit', format="%d",
                        help="Talles con menos de 30 dias de cobertura o sin stock"),
                    'talles_detalle': st.column_config.TextColumn('Talles sin stock',
                        width=180),
                    'precio_min': st.column_config.NumberColumn('P.Min', format="$%.0f"),
                    'precio_max': st.column_config.NumberColumn('P.Max', format="$%.0f"),
                },
                use_container_width=True, hide_index=True,
            )

            st.divider()

            # ── DRILL-DOWN: selección de categoría ──
            st.subheader("Drill-down por categoria")

            opciones_cat = df_vis.apply(
                lambda r: f"{r['genero']} > {r['categoria']} ({int(r['ventas_12m'])} vtas, cob {r['cobertura_dias']}d)",
                axis=1
            ).values.tolist()

            if opciones_cat:
                idx_cat = st.selectbox("Categoria", range(len(opciones_cat)),
                                        format_func=lambda i: opciones_cat[i],
                                        key="piramide_cat")
                row_cat = df_vis.iloc[idx_cat]
                genero_sel = int(row_cat['genero_cod'])
                sub_sel = int(row_cat['sub_cod'])

                # ── ANÁLISIS POR TALLE ──
                st.markdown("#### Cobertura por talle")
                st.caption("Cada talle individual con su semaforo. Rojo = stock 0 con demanda o menos de 30 dias.")

                with st.spinner("Cargando talles..."):
                    df_talles = cargar_talles_categoria(genero_sel, sub_sel)

                if not df_talles.empty:
                    # Semáforo visual rápido en columnas
                    criticos_t = df_talles[df_talles['urgencia'] == 'CRITICO']
                    bajos_t = df_talles[df_talles['urgencia'] == 'BAJO']
                    tc1, tc2, tc3 = st.columns(3)
                    tc1.metric("Talles criticos", len(criticos_t))
                    tc2.metric("Talles bajos", len(bajos_t))
                    tc3.metric("Total talles", len(df_talles))

                    if not criticos_t.empty:
                        talles_crit_str = ", ".join(criticos_t['talle'].tolist())
                        st.error(f"TALLES SIN COBERTURA: {talles_crit_str}")

                    # Tabla de talles
                    def color_urgencia(val):
                        colors = {'CRITICO': 'background-color: #ff4b4b; color: white',
                                  'BAJO': 'background-color: #ffa726; color: white',
                                  'MEDIO': 'background-color: #ffee58; color: black',
                                  'OK': 'background-color: #66bb6a; color: white'}
                        return colors.get(val, '')

                    st.dataframe(
                        df_talles[['talle', 'modelos', 'stock', 'vtas_12m', 'vel_real',
                                   'pct_quiebre', 'cob_dias', 'urgencia']].style.applymap(
                            color_urgencia, subset=['urgencia']
                        ),
                        column_config={
                            'talle': st.column_config.TextColumn('Talle', width=60),
                            'modelos': st.column_config.NumberColumn('Modelos', format="%d"),
                            'stock': st.column_config.NumberColumn('Stock', format="%d"),
                            'vtas_12m': st.column_config.NumberColumn('Vtas 12m', format="%d"),
                            'vel_real': st.column_config.NumberColumn('Vel real/mes', format="%.1f"),
                            'pct_quiebre': st.column_config.NumberColumn('Quiebre%', format="%.0f%%"),
                            'cob_dias': st.column_config.NumberColumn('Cob. dias', format="%d"),
                            'urgencia': 'Urgencia',
                        },
                        use_container_width=True, hide_index=True,
                    )
                else:
                    st.info("Sin datos de talle para esta categoria.")

                st.divider()

                # ── CURVA IDEAL DEL SUBRUBRO (lógica omicron) ──
                st.markdown("#### Curva ideal de talles (subrubro)")
                st.caption("Cuantos pares de cada talle por cada 12 comprados, basado en 3 anios de ventas de toda la marca+subrubro. "
                           "Util para productos nuevos sin historial propio.")

                # Obtener marca predominante de la categoría
                sql_marca_pred = f"""
                    SELECT TOP 1 a.marca, m.descripcion AS marca_desc,
                           COUNT(*) AS cnt
                    FROM msgestion01art.dbo.articulo a
                    JOIN msgestion01art.dbo.marcas m ON a.marca = m.codigo
                    WHERE a.rubro = {genero_sel} AND a.subrubro = {sub_sel}
                      AND a.estado = 'V' AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
                    GROUP BY a.marca, m.descripcion
                    ORDER BY cnt DESC
                """
                df_marca_pred = query_df(sql_marca_pred)
                if not df_marca_pred.empty:
                    marca_pred = int(df_marca_pred.iloc[0]['marca'])
                    marca_desc = df_marca_pred.iloc[0]['marca_desc'].strip()

                    df_curva_sub = calcular_curva_ideal_subrubro(marca_pred, sub_sel)
                    if not df_curva_sub.empty:
                        st.markdown(f"**Marca: {marca_desc}** | Subrubro: {sub_sel}")

                        # Merge curva ideal con tabla de talles si existe
                        if not df_talles.empty:
                            df_talles_curva = df_talles[['talle', 'stock', 'vtas_12m', 'cob_dias', 'urgencia']].copy()
                            df_talles_curva['talle_num'] = pd.to_numeric(
                                df_talles_curva['talle'].str.replace(',', '.'), errors='coerce')
                            merged_curva = pd.merge(
                                df_talles_curva,
                                df_curva_sub[['nro', 'porcent', 'comprar']].rename(
                                    columns={'nro': 'talle_num', 'comprar': 'curva_ideal'}),
                                on='talle_num', how='outer'
                            ).fillna(0).sort_values('talle_num')
                            merged_curva['curva_ideal'] = merged_curva['curva_ideal'].astype(int)

                            st.dataframe(
                                merged_curva[['talle', 'stock', 'vtas_12m', 'cob_dias', 'urgencia',
                                              'porcent', 'curva_ideal']],
                                column_config={
                                    'talle': st.column_config.TextColumn('Talle', width=60),
                                    'stock': st.column_config.NumberColumn('Stock', format="%d"),
                                    'vtas_12m': st.column_config.NumberColumn('Vtas 12m', format="%d"),
                                    'cob_dias': st.column_config.NumberColumn('Cob. dias', format="%d"),
                                    'urgencia': 'Urgencia',
                                    'porcent': st.column_config.NumberColumn('% Curva', format="%.1f%%"),
                                    'curva_ideal': st.column_config.NumberColumn('x12 pares',
                                        format="%d", help="Pares de este talle por cada 12 comprados"),
                                },
                                use_container_width=True, hide_index=True,
                            )
                        else:
                            # Solo mostrar la curva
                            st.dataframe(
                                df_curva_sub[['nro', 'vendidos', 'porcent', 'comprar']],
                                column_config={
                                    'nro': st.column_config.NumberColumn('Talle'),
                                    'vendidos': st.column_config.NumberColumn('Vendidos 3a', format="%d"),
                                    'porcent': st.column_config.NumberColumn('% Curva', format="%.1f%%"),
                                    'comprar': st.column_config.NumberColumn('x12 pares', format="%d"),
                                },
                                use_container_width=True, hide_index=True,
                            )
                    else:
                        st.info("Sin ventas suficientes en este subrubro para calcular curva ideal.")
                else:
                    st.info("No se encontro marca predominante para esta categoria.")

                st.divider()

                # ── PIRÁMIDE DE PRECIOS ──
                st.markdown("#### Piramide de precios")

                if st.button("Analizar piramide + sustitutos", type="primary", key="btn_piramide"):
                    with st.spinner("Cargando piramide de precios..."):
                        df_pir, resumen_franjas = cargar_piramide_precios(genero_sel, sub_sel)

                        if df_pir.empty:
                            st.info("No hay datos suficientes para esta categoria.")
                        else:
                            st.session_state['piramide_data'] = {
                                'df': df_pir, 'resumen': resumen_franjas,
                                'genero_cod': genero_sel, 'sub_cod': sub_sel,
                                'cat_nombre': f"{row_cat['genero']} > {row_cat['categoria']}"
                            }

                # Mostrar pirámide si hay datos
                if 'piramide_data' in st.session_state:
                    pdata = st.session_state['piramide_data']
                    df_pir = pdata['df']
                    resumen_franjas = pdata['resumen']

                    st.markdown(f"#### {pdata['cat_nombre']}")

                    # Semáforo por franja
                    cols_fr = st.columns(len(resumen_franjas))
                    for i, (franja, datos) in enumerate(resumen_franjas.items()):
                        cob = datos['cobertura_dias']
                        if cob < 30:
                            color = "🔴"
                            estado = "CRITICO"
                        elif cob < 60:
                            color = "🟡"
                            estado = "BAJO"
                        else:
                            color = "🟢"
                            estado = "OK"

                        with cols_fr[i]:
                            st.markdown(f"**{franja}** {color}")
                            st.markdown(f"${datos['precio_min']:,.0f} - ${datos['precio_max']:,.0f}")
                            st.metric("Cobertura", f"{cob} dias")
                            st.caption(f"{datos['modelos']} modelos | {int(datos['stock'])} stock | {int(datos['ventas'])} vtas")

                    st.divider()

                    # Tabla detallada por modelo
                    marcas_d = cargar_marcas_dict()
                    df_pir['marca_desc'] = df_pir['marca'].map(
                        lambda x: marcas_d.get(int(x), f"#{int(x)}") if pd.notna(x) else "?"
                    )
                    df_pir['vel_dia'] = df_pir['ventas_12m'] / 365
                    df_pir['cob_dias'] = np.where(
                        df_pir['vel_dia'] > 0,
                        df_pir['stock_total'] / df_pir['vel_dia'],
                        999
                    ).astype(int)

                    st.dataframe(
                        df_pir[['descripcion', 'marca_desc', 'franja', 'precio_fabrica',
                                'stock_total', 'ventas_12m', 'cob_dias']].sort_values('cob_dias'),
                        column_config={
                            'descripcion': st.column_config.TextColumn('Producto', width=250),
                            'marca_desc': 'Marca',
                            'franja': 'Franja',
                            'precio_fabrica': st.column_config.NumberColumn('Precio', format="$%.0f"),
                            'stock_total': st.column_config.NumberColumn('Stock', format="%d"),
                            'ventas_12m': st.column_config.NumberColumn('Vtas 12m', format="%d"),
                            'cob_dias': st.column_config.NumberColumn('Cob. dias', format="%d"),
                        },
                        use_container_width=True, hide_index=True,
                    )

                    # ── Sustitutos por embedding ──
                    st.divider()
                    st.subheader("Deteccion de sustitutos (IA)")
                    st.caption("Selecciona un modelo para buscar sustitutos similares por embedding")

                    # Mostrar solo los más urgentes (baja cobertura)
                    df_urgentes = df_pir[df_pir['cob_dias'] < 60].sort_values('cob_dias')
                    if df_urgentes.empty:
                        st.success("Todos los modelos de esta categoria tienen buena cobertura (>60 dias).")
                    else:
                        opciones_sust = df_urgentes.apply(
                            lambda r: f"{r['descripcion'][:45]} | {r['marca_desc']} | Stock:{int(r['stock_total'])} | Cob:{r['cob_dias']}d",
                            axis=1
                        ).values.tolist()
                        codigos_sust = df_urgentes['csr'].tolist()

                        idx_sust = st.selectbox("Modelo urgente", range(len(opciones_sust)),
                                                 format_func=lambda i: opciones_sust[i],
                                                 key="sust_modelo")

                        if st.button("Buscar sustitutos", key="btn_sust"):
                            csr_sust = codigos_sust[idx_sust]
                            # Obtener un codigo MG del CSR
                            sql_cod = f"""
                                SELECT TOP 1 a.codigo FROM msgestion01art.dbo.articulo a
                                WHERE LEFT(a.codigo_sinonimo, 10) = '{csr_sust}'
                                  AND a.estado = 'V'
                            """
                            df_cod = query_df(sql_cod)
                            if not df_cod.empty:
                                codigo_mg = int(df_cod.iloc[0]['codigo'])
                                with st.spinner("Buscando sustitutos por embedding..."):
                                    sust = buscar_sustitutos_activos_con_stock(
                                        codigo_mg, pdata['sub_cod']
                                    )
                                    if sust:
                                        st.markdown("**Sustitutos activos con stock:**")
                                        df_sust = pd.DataFrame(sust)
                                        st.dataframe(
                                            df_sust[['desc_mg', 'similitud', 'stock', 'precio_fabrica']],
                                            column_config={
                                                'desc_mg': st.column_config.TextColumn('Sustituto', width=280),
                                                'similitud': st.column_config.NumberColumn('Similitud', format="%.2f"),
                                                'stock': st.column_config.NumberColumn('Stock', format="%d"),
                                                'precio_fabrica': st.column_config.NumberColumn('Precio', format="$%.0f"),
                                            },
                                            use_container_width=True, hide_index=True,
                                        )

                                        # Veredicto
                                        st.info(
                                            f"Hay {len(sust)} sustitutos activos con stock. "
                                            f"Antes de reponer este modelo, evalua si los sustitutos cubren la demanda."
                                        )
                                    else:
                                        st.warning(
                                            "No se encontraron sustitutos activos con stock. "
                                            "Este modelo necesita reposicion."
                                        )
                            else:
                                st.error("No se encontro el codigo del producto.")

    # ══════════════════════════════════════════════════════════════
    # TAB 1: DASHBOARD GLOBAL
    # ══════════════════════════════════════════════════════════════
    with tab_dashboard:
        # Velocidad REAL corregida por quiebre de stock
        with st.spinner("Calculando velocidad real (quiebre)..."):
            csrs_dash = df_f['csr'].tolist()
            quiebres_dash = analizar_quiebre_batch(csrs_dash)
            df_f['vel_mes'] = df_f['csr'].map(
                lambda c: quiebres_dash.get(c, {}).get('vel_real', 0)
            )
            df_f['pct_quiebre'] = df_f['csr'].map(
                lambda c: quiebres_dash.get(c, {}).get('pct_quiebre', 0)
            )
        df_f['vel_dia'] = df_f['vel_mes'] / 30
        df_f['dias_stock'] = np.where(
            df_f['vel_dia'] > 0,
            df_f['stock_total'] / df_f['vel_dia'],
            999
        )
        df_f['urgencia'] = pd.cut(
            df_f['dias_stock'],
            bins=[-1, 15, 30, 60, 999],
            labels=['CRITICO', 'BAJO', 'MEDIO', 'OK']
        )

        # GMROI y Rotación
        precios_venta_dash = obtener_precios_venta_batch(csrs_dash)
        df_f['precio_costo'] = df_f['precio_fabrica'].fillna(0).astype(float)
        df_f['precio_venta'] = df_f['csr'].map(
            lambda c: precios_venta_dash.get(c, 0)
        )
        # Fallback: si no hay precio venta, estimar x2
        df_f.loc[df_f['precio_venta'] <= 0, 'precio_venta'] = df_f.loc[
            df_f['precio_venta'] <= 0, 'precio_costo'] * 2

        # stock_costo = stock_actual * precio_costo
        df_f['stock_costo'] = df_f['stock_total'] * df_f['precio_costo']
        # ventas_costo_12m = ventas_12m * precio_costo
        df_f['ventas_costo_12m'] = df_f['ventas_12m'] * df_f['precio_costo']
        # margen_bruto_anual = vel_real * 12 * (precio_venta - precio_costo)
        df_f['margen_bruto_anual'] = df_f['vel_mes'] * 12 * (df_f['precio_venta'] - df_f['precio_costo'])

        # GMROI = margen_bruto_anual / stock_promedio_costo
        df_f['gmroi'] = np.where(
            df_f['stock_costo'] > 0,
            df_f['margen_bruto_anual'] / df_f['stock_costo'],
            0
        )
        # Rotación = ventas_costo_12m / stock_promedio_costo
        df_f['rotacion'] = np.where(
            df_f['stock_costo'] > 0,
            df_f['ventas_costo_12m'] / df_f['stock_costo'],
            0
        )

        # KPIs globales
        c1, c2, c3, c4, c5 = st.columns(5)
        criticos = len(df_f[df_f['urgencia'] == 'CRITICO'])
        bajos = len(df_f[df_f['urgencia'] == 'BAJO'])
        c1.metric("Productos filtrados", len(df_f))
        c2.metric("CRITICOS (<15d)", criticos)
        c3.metric("BAJOS (15-30d)", bajos)
        c4.metric("Stock total (pares)", f"{int(df_f['stock_total'].sum()):,}")
        c5.metric("Ventas 12m (pares)", f"{int(df_f['ventas_12m'].sum()):,}")

        st.divider()

        # Resumen rápido de la selección
        st.subheader("Resumen de la selección")

        resumen_data = df_f.groupby('marca_desc').agg(
            productos=('csr', 'count'),
            stock=('stock_total', 'sum'),
            ventas=('ventas_12m', 'sum'),
            vel_real_sum=('vel_mes', 'sum'),
            criticos=('urgencia', lambda x: (x == 'CRITICO').sum()),
            bajos=('urgencia', lambda x: (x == 'BAJO').sum()),
        ).reset_index().sort_values('criticos', ascending=False)

        resumen_data['dias_prom'] = np.where(
            resumen_data['vel_real_sum'] > 0,
            (resumen_data['stock'] / (resumen_data['vel_real_sum'] / 30)).round(0),
            999
        )

        st.dataframe(
            resumen_data,
            column_config={
                'marca_desc': st.column_config.TextColumn('Marca'),
                'productos': st.column_config.NumberColumn('Productos'),
                'stock': st.column_config.NumberColumn('Stock', format="%d"),
                'ventas': st.column_config.NumberColumn('Ventas 12m', format="%d"),
                'criticos': st.column_config.NumberColumn('Criticos', format="%d"),
                'bajos': st.column_config.NumberColumn('Bajos', format="%d"),
                'dias_prom': st.column_config.NumberColumn('Dias Stock', format="%d"),
            },
            use_container_width=True, hide_index=True,
        )

        st.divider()

        # Top productos más urgentes
        st.subheader("Top 30 — Productos más urgentes")

        # Cruce con pedidos ERP
        with st.spinner("Consultando pedidos en ERP..."):
            df_pedidos_erp = obtener_pedidos_erp()

        df_top = df_f.nsmallest(30, 'dias_stock')[
            ['csr', 'descripcion', 'marca_desc', 'prov_nombre', 'stock_total',
             'ventas_12m', 'vel_mes', 'pct_quiebre', 'dias_stock', 'urgencia',
             'gmroi', 'rotacion']
        ].copy()
        df_top['dias_stock'] = df_top['dias_stock'].round(0).astype(int)
        df_top['vel_mes'] = df_top['vel_mes'].round(1)

        # Cruzar con pedidos
        df_top = cruzar_pedidos_top(df_top, df_pedidos_erp)

        # Guardar en session para tab Armar Pedido
        st.session_state['df_top_pedidos'] = df_top
        st.session_state['df_pedidos_erp'] = df_pedidos_erp

        # Filtro: Solo sin pedido
        solo_sin_pedido = st.checkbox("Solo sin pedido", value=False, key="filtro_sin_pedido")
        if solo_sin_pedido:
            df_top = df_top[df_top['Pedido'] == 'No']

        # KPIs de pedidos
        n_con = len(df_top[df_top['Pedido'] == 'Si'])
        n_sin = len(df_top[df_top['Pedido'] == 'No'])
        n_rojo = len(df_top[df_top['Alerta'] == '🔴'])
        cp1, cp2, cp3 = st.columns(3)
        cp1.metric("Con pedido", n_con)
        cp2.metric("Sin pedido", n_sin)
        cp3.metric("Alerta roja", n_rojo)

        st.dataframe(
            df_top.drop(columns=['csr']),
            column_config={
                'descripcion': st.column_config.TextColumn('Producto', width=200),
                'marca_desc': 'Marca',
                'prov_nombre': 'Proveedor',
                'stock_total': st.column_config.NumberColumn('Stock', format="%d"),
                'ventas_12m': st.column_config.NumberColumn('Vtas 12m', format="%d"),
                'vel_mes': st.column_config.NumberColumn('Vel real/mes', format="%.1f"),
                'pct_quiebre': st.column_config.NumberColumn('Quiebre%', format="%.0f%%"),
                'dias_stock': st.column_config.NumberColumn('Dias', format="%d"),
                'urgencia': 'Urgencia',
                'gmroi': st.column_config.NumberColumn('GMROI', format="%.1f",
                    help="Margen bruto anual / stock a costo. >1 = rentable"),
                'rotacion': st.column_config.NumberColumn('Rotación', format="%.1f",
                    help="Ventas a costo 12m / stock a costo. >4 = alta rotación"),
                'Pedido': st.column_config.TextColumn('Pedido', width=60),
                'Cant. Pedida': st.column_config.NumberColumn('Cant. Pedida', format="%d"),
                'Fecha Entrega': st.column_config.DateColumn('Fecha Entrega', format="DD/MM/YYYY"),
                'Alerta': st.column_config.TextColumn('Alerta', width=50,
                    help="🟢 llega antes del quiebre | 🟡 llega cerca | 🔴 llega tarde o sin pedido"),
            },
            use_container_width=True, hide_index=True,
        )

    # ══════════════════════════════════════════════════════════════
    # TAB 2: WATERFALL DETALLADO
    # ══════════════════════════════════════════════════════════════
    with tab_waterfall:
        st.subheader("🌊 Proyección Waterfall por Producto")
        st.caption("Seleccioná un producto para ver la proyección a 15/30/45/60 días con quiebre real")

        # Selector de producto
        df_f_sorted = df_f.sort_values('dias_stock')
        opciones = df_f_sorted.apply(
            lambda r: f"{r['descripcion'][:50]} | {r['marca_desc']} | Stock:{int(r['stock_total'])} | Vtas:{int(r['ventas_12m'])}",
            axis=1
        ).values.tolist()
        csrs = df_f_sorted['csr'].tolist()

        if not opciones:
            st.info("No hay productos para analizar.")
        else:
            idx = st.selectbox("Producto", range(len(opciones)),
                               format_func=lambda i: opciones[i],
                               key="wf_producto")
            csr_sel = csrs[idx]

            if st.button("🔍 Analizar waterfall", type="primary", key="btn_wf"):
                with st.spinner("Analizando quiebre + estacionalidad..."):
                    # Quiebre
                    quiebre = analizar_quiebre_batch([csr_sel])
                    q = quiebre.get(csr_sel, {})

                    # Estacionalidad
                    factores = factor_estacional_batch([csr_sel])
                    f_est = factores.get(csr_sel, {m: 1.0 for m in range(1, 13)})

                    # Pendientes
                    df_pend = obtener_pendientes()
                    pend = pendientes_por_sinonimo(df_pend)
                    cant_pend = pend.get(csr_sel, {}).get('cant_pendiente', 0)

                    # Precios
                    precios_v = obtener_precios_venta_batch([csr_sel])
                    precio_venta = precios_v.get(csr_sel, 0)

                    stock_actual = q.get('stock_actual', 0)
                    vel_real = q.get('vel_real', 0)
                    vel_diaria = vel_real / 30

                    stock_disponible = stock_actual + cant_pend

                    # Waterfall
                    wf = proyectar_waterfall(vel_diaria, stock_disponible, f_est)
                    dias_cob = calcular_dias_cobertura(vel_diaria, stock_disponible, f_est)

                    # Guardar en session
                    st.session_state['wf_data'] = {
                        'csr': csr_sel, 'quiebre': q, 'factores': f_est,
                        'waterfall': wf, 'dias_cobertura': dias_cob,
                        'stock_disponible': stock_disponible, 'cant_pend': cant_pend,
                        'vel_diaria': vel_diaria, 'precio_venta': precio_venta,
                    }

            # Mostrar resultados
            if 'wf_data' in st.session_state and st.session_state['wf_data'].get('csr') == csr_sel:
                data = st.session_state['wf_data']
                q = data['quiebre']
                wf = data['waterfall']

                # KPIs
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Vel real / mes", f"{q.get('vel_real', 0):.1f} pares")
                col2.metric("Quiebre", f"{q.get('pct_quiebre', 0):.0f}%",
                            help="% de meses sin stock")
                col3.metric("Stock disponible", f"{data['stock_disponible']:.0f}",
                            help=f"Stock: {q.get('stock_actual',0):.0f} + Pendiente: {data['cant_pend']:.0f}")
                col4.metric("Cobertura", f"{data['dias_cobertura']} días")

                st.divider()

                # Waterfall visual
                st.markdown("#### Proyección de stock")
                cols = st.columns(4)
                for i, w in enumerate(wf):
                    with cols[i]:
                        status_html = render_semaforo(w['status'])
                        st.markdown(f"**{w['dias']} días**", unsafe_allow_html=True)
                        st.markdown(status_html, unsafe_allow_html=True)
                        st.metric(f"Stock en {w['dias']}d",
                                  f"{w['stock_proy']:.0f}",
                                  delta=f"-{w['ventas_proy']:.0f} vendidos")

                # Gráfico waterfall
                st.divider()
                df_wf = pd.DataFrame(wf)
                df_wf['label'] = df_wf['dias'].astype(str) + 'd'

                # Agregar punto 0 (hoy)
                df_chart = pd.DataFrame([
                    {'label': 'Hoy', 'stock_proy': data['stock_disponible'], 'dias': 0}
                ])
                df_chart = pd.concat([df_chart, df_wf[['label', 'stock_proy', 'dias']]])
                df_chart = df_chart.set_index('label')

                st.area_chart(df_chart['stock_proy'], color='#1976d2')

                # Tabla de estacionalidad
                st.divider()
                st.markdown("#### Factores de estacionalidad")
                meses_nombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                                 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
                f_est = data['factores']
                cols_e = st.columns(12)
                for i in range(12):
                    factor = f_est.get(i + 1, 1.0)
                    color = "🔴" if factor < 0.5 else ("🟡" if factor < 0.8 else "🟢")
                    cols_e[i].markdown(f"**{meses_nombres[i]}**\n\n{color} {factor:.2f}")

    # ══════════════════════════════════════════════════════════════
    # TAB 3: OPTIMIZADOR DE PRESUPUESTO
    # ══════════════════════════════════════════════════════════════
    with tab_optimizar:
        st.subheader("💰 Optimizador de Compras por ROI")
        st.caption(f"Presupuesto: **${presupuesto:,.0f}** — Ranking por días de recupero de inversión")

        if st.button("🚀 Calcular ranking ROI", type="primary", key="btn_roi"):
            with st.spinner("Calculando quiebre, estacionalidad y ROI para todos los productos..."):
                # Limitar a productos con ventas significativas
                df_roi = df_f[df_f['ventas_12m'] >= max(min_ventas, 5)].copy()

                if len(df_roi) > 200:
                    df_roi = df_roi.nsmallest(200, 'dias_stock')

                csrs_list = df_roi['csr'].tolist()

                # Batch analysis
                quiebres = analizar_quiebre_batch(csrs_list)
                factores_all = factor_estacional_batch(csrs_list)
                precios_v = obtener_precios_venta_batch(csrs_list)
                df_pend = obtener_pendientes()
                pend_dict = pendientes_por_sinonimo(df_pend)

                rows = []
                for _, prod in df_roi.iterrows():
                    csr = prod['csr']
                    q = quiebres.get(csr, {})
                    f_est = factores_all.get(csr, {m: 1.0 for m in range(1, 13)})

                    vel_real = q.get('vel_real', 0)
                    vel_diaria = vel_real / 30
                    stock_actual = q.get('stock_actual', prod['stock_total'])
                    cant_pend = pend_dict.get(csr, {}).get('cant_pendiente', 0)
                    stock_disp = stock_actual + cant_pend

                    # Cobertura actual
                    dias_cob = calcular_dias_cobertura(vel_diaria, stock_disp, f_est)

                    # Necesidad: cubrir 60 días
                    necesidad_60d = 0
                    hoy = date.today()
                    for d in range(60):
                        fecha = hoy + timedelta(days=d)
                        necesidad_60d += vel_diaria * f_est.get(fecha.month, 1.0)

                    pedir = max(0, round(necesidad_60d - stock_disp))

                    if pedir <= 0:
                        continue

                    precio_costo = float(prod['precio_fabrica'] or 0)
                    if precio_costo <= 0:
                        continue

                    precio_venta = precios_v.get(csr, precio_costo * 2)

                    roi = calcular_roi(precio_costo, precio_venta, vel_diaria, f_est,
                                       pedir, stock_disp)

                    rows.append({
                        'csr': csr,
                        'descripcion': prod['descripcion'][:50],
                        'marca': prod['marca_desc'],
                        'proveedor': prod['prov_nombre'],
                        'stock': int(stock_actual),
                        'pendiente': int(cant_pend),
                        'vel_real': round(vel_real, 1),
                        'quiebre': q.get('pct_quiebre', 0),
                        'dias_cob': dias_cob,
                        'pedir': pedir,
                        'precio_costo': round(precio_costo, 0),
                        'inversion': roi['inversion'],
                        'dias_recupero': roi['dias_recupero'],
                        'roi_60d': roi['roi_60d'],
                        'margen': roi['margen_pct'],
                    })

                if not rows:
                    st.info("No se encontraron productos que necesiten reposición.")
                else:
                    df_ranking = pd.DataFrame(rows)
                    df_ranking = df_ranking.sort_values('dias_recupero')

                    # Optimización de presupuesto (greedy por ROI)
                    df_ranking['acum_inversion'] = df_ranking['inversion'].cumsum()
                    df_ranking['dentro_presupuesto'] = df_ranking['acum_inversion'] <= presupuesto

                    st.session_state['df_ranking'] = df_ranking

        # Mostrar ranking
        if 'df_ranking' in st.session_state:
            df_ranking = st.session_state['df_ranking']

            dentro = df_ranking[df_ranking['dentro_presupuesto']]
            fuera = df_ranking[~df_ranking['dentro_presupuesto']]

            # KPIs del presupuesto
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Productos a comprar", len(dentro))
            c2.metric("Inversión total", f"${dentro['inversion'].sum():,.0f}")
            c3.metric("Pares a pedir", f"{int(dentro['pedir'].sum()):,}")
            c4.metric("Recupero prom.", f"{dentro['dias_recupero'].mean():.0f} días"
                       if len(dentro) > 0 else "N/A")

            st.divider()

            st.markdown("#### Dentro del presupuesto")
            st.dataframe(
                dentro.drop(columns=['acum_inversion', 'dentro_presupuesto', 'csr']),
                column_config={
                    'descripcion': st.column_config.TextColumn('Producto', width=200),
                    'marca': 'Marca',
                    'proveedor': 'Proveedor',
                    'stock': st.column_config.NumberColumn('Stock', format="%d"),
                    'pendiente': st.column_config.NumberColumn('Pend.', format="%d"),
                    'vel_real': st.column_config.NumberColumn('Vel/mes', format="%.1f"),
                    'quiebre': st.column_config.NumberColumn('Quiebre%', format="%.0f%%"),
                    'dias_cob': st.column_config.NumberColumn('Cob. días', format="%d"),
                    'pedir': st.column_config.NumberColumn('Pedir', format="%d"),
                    'precio_costo': st.column_config.NumberColumn('P.Costo', format="$%.0f"),
                    'inversion': st.column_config.NumberColumn('Inversión', format="$%.0f"),
                    'dias_recupero': st.column_config.NumberColumn('Recup. días', format="%d"),
                    'roi_60d': st.column_config.NumberColumn('ROI 60d', format="%.1f%%"),
                    'margen': st.column_config.NumberColumn('Margen%', format="%.1f%%"),
                },
                use_container_width=True, hide_index=True,
            )

            if len(fuera) > 0:
                with st.expander(f"Fuera del presupuesto ({len(fuera)} productos)"):
                    st.dataframe(
                        fuera.drop(columns=['acum_inversion', 'dentro_presupuesto', 'csr']),
                        use_container_width=True, hide_index=True,
                    )

    # ══════════════════════════════════════════════════════════════
    # TAB: CURVA DE TALLE IDEAL
    # ══════════════════════════════════════════════════════════════
    with tab_curva:
        st.subheader("Curva de Talle Ideal vs Stock Real")
        st.caption("3 anios de ventas revelan la distribucion de talles que tu mercado REALMENTE pide. Compara contra lo que tenes en stock.")

        if st.button("Calcular curva de talle", type="primary", key="btn_curva"):
            with st.spinner("Analizando 3 anios de ventas por talle..."):
                df_curva = calcular_curva_talle_ideal(anios=3)
                df_stock_t = calcular_stock_por_talle()
                sub_desc = cargar_subrubro_desc()
                if not df_curva.empty:
                    st.session_state['curva_data'] = {
                        'demanda': df_curva, 'stock': df_stock_t, 'sub_desc': sub_desc
                    }

        if 'curva_data' in st.session_state:
            cdata = st.session_state['curva_data']
            df_dem = cdata['demanda']
            df_stk = cdata['stock']
            sub_desc = cdata['sub_desc']

            # Selector de categoría
            df_dem['categoria'] = df_dem['sub_cod'].map(sub_desc).fillna('?')
            combos = df_dem.groupby(['genero_cod', 'genero', 'sub_cod', 'categoria']).agg(
                vtas_total=('vtas', 'sum')
            ).reset_index().sort_values('vtas_total', ascending=False)
            combos = combos[combos['vtas_total'] >= 50]

            opciones_curva = combos.apply(
                lambda r: f"{r['genero']} > {r['categoria']} ({int(r['vtas_total'])} pares vendidos)",
                axis=1
            ).values.tolist()

            if not opciones_curva:
                st.warning("No hay categorias con suficientes ventas.")
            else:
                idx_c = st.selectbox("Categoria", range(len(opciones_curva)),
                                      format_func=lambda i: opciones_curva[i],
                                      key="curva_cat_sel")
                row_c = combos.iloc[idx_c]
                g_sel = int(row_c['genero_cod'])
                s_sel = int(row_c['sub_cod'])

                # Filtrar demanda y stock para esta categoría
                dem_cat = df_dem[(df_dem['genero_cod'] == g_sel) & (df_dem['sub_cod'] == s_sel)].copy()
                dem_cat = dem_cat.sort_values('talle_num')

                stk_cat = pd.DataFrame()
                if not df_stk.empty:
                    stk_cat = df_stk[(df_stk['genero_cod'] == g_sel) & (df_stk['sub_cod'] == s_sel)].copy()

                # Merge demanda + stock
                if not stk_cat.empty:
                    merged = pd.merge(
                        dem_cat[['talle', 'talle_num', 'vtas', 'pct_demanda']],
                        stk_cat[['talle', 'stock', 'pct_stock']],
                        on='talle', how='outer'
                    ).fillna(0)
                else:
                    merged = dem_cat[['talle', 'talle_num', 'vtas', 'pct_demanda']].copy()
                    merged['stock'] = 0
                    merged['pct_stock'] = 0

                merged = merged.sort_values('talle_num')

                # KPIs
                kc1, kc2, kc3 = st.columns(3)
                kc1.metric("Talles activos", len(merged[merged['vtas'] > 0]))
                talle_top = merged.loc[merged['pct_demanda'].idxmax(), 'talle'] if not merged.empty else '?'
                kc2.metric("Talle mas vendido", talle_top)
                # Gap máximo
                merged['gap'] = merged['pct_demanda'] - merged['pct_stock']
                if not merged.empty:
                    max_gap_row = merged.loc[merged['gap'].idxmax()]
                    kc3.metric("Mayor deficit de stock",
                               f"Talle {max_gap_row['talle']}",
                               delta=f"{max_gap_row['gap']:+.1f}pp")

                st.divider()

                # Gráfico de barras comparativo
                st.markdown("#### Demanda vs Stock (% de distribucion)")
                chart_data = merged[['talle', 'pct_demanda', 'pct_stock']].set_index('talle')
                chart_data.columns = ['% Demanda (ideal)', '% Stock (real)']
                st.bar_chart(chart_data, color=['#1976d2', '#ff7043'])

                st.divider()

                # Tabla detallada
                st.markdown("#### Detalle por talle")
                merged['gap_visual'] = merged['gap'].apply(
                    lambda g: f"+{g:.1f}" if g > 0 else f"{g:.1f}"
                )
                merged['status'] = merged['gap'].apply(
                    lambda g: 'FALTA STOCK' if g > 5 else ('EXCESO' if g < -5 else 'OK')
                )

                st.dataframe(
                    merged[['talle', 'vtas', 'pct_demanda', 'stock', 'pct_stock', 'gap', 'status']],
                    column_config={
                        'talle': st.column_config.TextColumn('Talle', width=60),
                        'vtas': st.column_config.NumberColumn('Ventas 3a', format="%d"),
                        'pct_demanda': st.column_config.NumberColumn('% Demanda', format="%.1f%%"),
                        'stock': st.column_config.NumberColumn('Stock', format="%d"),
                        'pct_stock': st.column_config.NumberColumn('% Stock', format="%.1f%%"),
                        'gap': st.column_config.NumberColumn('Gap (pp)', format="%+.1f"),
                        'status': 'Status',
                    },
                    use_container_width=True, hide_index=True,
                )

                st.divider()

                # Recomendación
                falta = merged[merged['gap'] > 3].sort_values('gap', ascending=False)
                exceso = merged[merged['gap'] < -3].sort_values('gap')
                if not falta.empty:
                    talles_falta = ", ".join(falta['talle'].tolist())
                    st.error(f"DEFICIT: Talles {talles_falta} — tu stock esta por debajo de la demanda real. Priorizar en proxima compra.")
                if not exceso.empty:
                    talles_exceso = ", ".join(exceso['talle'].tolist())
                    st.warning(f"EXCESO: Talles {talles_exceso} — tenes mas stock del que el mercado pide. Evaluar liquidar o redistribuir.")
                if falta.empty and exceso.empty:
                    st.success("Tu distribucion de stock esta alineada con la demanda. Bien.")

    # ══════════════════════════════════════════════════════════════
    # TAB: CANIBALIZACIÓN POR EMBEDDING
    # ══════════════════════════════════════════════════════════════
    with tab_canibal:
        st.subheader("Detector de Canibalizacion")
        st.caption("Productos que BAJAN mientras un sustituto similar SUBE = canibalizacion. "
                   "No es quiebre, es el mercado moviéndose. Ahi es donde tenes que ir.")

        modo_canibal = st.radio("Modo", ["Escaneo automatico", "Analizar producto puntual"],
                                 horizontal=True, key="modo_canibal")

        if modo_canibal == "Escaneo automatico":
            st.markdown("Busca automaticamente pares victima-canibal en todo el catalogo. "
                        "Requiere conexion a PostgreSQL (embeddings).")

            if st.button("Escanear canibalizacion", type="primary", key="btn_scan_canibal"):
                with st.spinner("Analizando tendencias + embeddings... (puede tardar 1-2 min)"):
                    df_pares = escaneo_canibalizacion_masivo(top_n=30)
                    st.session_state['canib_pares'] = df_pares

            if 'canib_pares' in st.session_state:
                df_pares = st.session_state['canib_pares']
                if df_pares.empty:
                    st.info("No se detectaron pares de canibalizacion (puede ser por falta de conexion a PostgreSQL "
                            "o porque no hay productos con patron victima-canibal claro).")
                else:
                    st.success(f"Se detectaron **{len(df_pares)} pares** de posible canibalizacion.")

                    ck1, ck2 = st.columns(2)
                    ck1.metric("Pares detectados", len(df_pares))
                    pares_perdidos = int(df_pares['victima_s1'].sum() - df_pares['victima_s2'].sum())
                    ck2.metric("Pares vendidos perdidos (victimas)", f"{pares_perdidos:,}")

                    st.divider()

                    st.dataframe(
                        df_pares,
                        column_config={
                            'victima': st.column_config.TextColumn('Victima (baja)', width=200),
                            'victima_s1': st.column_config.NumberColumn('Vtas S1', format="%d",
                                help="Ventas hace 12-6 meses"),
                            'victima_s2': st.column_config.NumberColumn('Vtas S2', format="%d",
                                help="Ventas ultimos 6 meses"),
                            'victima_delta': st.column_config.NumberColumn('Delta%', format="%.0f%%"),
                            'canibal': st.column_config.TextColumn('Canibal (sube)', width=200),
                            'canibal_s1': st.column_config.NumberColumn('Vtas S1', format="%d"),
                            'canibal_s2': st.column_config.NumberColumn('Vtas S2', format="%d"),
                            'canibal_delta': st.column_config.NumberColumn('Delta%', format="%.0f%%"),
                            'similitud': st.column_config.NumberColumn('Similitud', format="%.2f"),
                            'victima_csr': None,  # ocultar
                            'canibal_csr': None,
                        },
                        use_container_width=True, hide_index=True,
                    )

                    st.divider()
                    st.markdown("#### Que significa esto")
                    st.markdown(
                        "- **Victima baja + Canibal sube + Similitud alta** = el mercado esta migrando de un producto a otro\n"
                        "- **Accion**: NO reponer la victima. Reponer el canibal (es lo que el mercado quiere)\n"
                        "- **Similitud > 0.85** = practicamente el mismo producto (distinto color/modelo)\n"
                        "- **Similitud 0.70-0.85** = misma categoria, compiten por el mismo cliente\n"
                        "- Si la victima tiene stock alto y el canibal stock bajo = **oportunidad de liquidacion + reposicion**"
                    )

        else:  # Analizar producto puntual
            st.markdown("Selecciona un producto para ver si tiene canibales o victimas.")

            with st.spinner("Cargando tendencias..."):
                df_sem = obtener_ventas_semestrales()

            if df_sem.empty:
                st.warning("No se pudieron cargar las ventas semestrales.")
            else:
                # Mostrar productos que bajan
                df_bajan = df_sem[df_sem['tendencia'] == 'BAJA'].sort_values('delta_pct')
                marcas_d = cargar_marcas_dict()
                df_bajan['marca_desc'] = df_bajan['marca'].map(
                    lambda x: marcas_d.get(int(x), f"#{int(x)}") if pd.notna(x) else "?"
                )

                opciones_vic = df_bajan.head(100).apply(
                    lambda r: f"{r['descripcion'][:40]} | {r['marca_desc']} | S1:{int(r['vtas_s1'])} S2:{int(r['vtas_s2'])} ({r['delta_pct']:+.0f}%)",
                    axis=1
                ).values.tolist()

                if not opciones_vic:
                    st.info("No hay productos con tendencia bajista.")
                else:
                    idx_vic = st.selectbox("Producto (bajando)", range(len(opciones_vic)),
                                            format_func=lambda i: opciones_vic[i],
                                            key="vic_sel")
                    vic_row = df_bajan.iloc[idx_vic]

                    if st.button("Buscar canibales", type="primary", key="btn_canibal_puntual"):
                        with st.spinner("Buscando por embedding..."):
                            resultados = detectar_canibalizacion_embedding(
                                vic_row['csr'], int(vic_row['subrubro']), df_sem
                            )
                            st.session_state['canibal_puntual'] = {
                                'victima': vic_row, 'resultados': resultados
                            }

                    if 'canibal_puntual' in st.session_state:
                        cp = st.session_state['canibal_puntual']
                        vic = cp['victima']
                        res = cp['resultados']

                        st.markdown(f"**Victima**: {vic['descripcion']} — "
                                    f"S1: {int(vic['vtas_s1'])} → S2: {int(vic['vtas_s2'])} "
                                    f"({vic['delta_pct']:+.0f}%)")

                        if not res:
                            st.info("No se encontraron canibales por embedding. "
                                    "La caida puede ser por quiebre de stock o estacionalidad, no canibalizacion.")
                        else:
                            canibales = [r for r in res if r['canibalizacion']]
                            no_canib = [r for r in res if not r['canibalizacion']]

                            if canibales:
                                st.error(f"CANIBALIZACION DETECTADA — {len(canibales)} productos similares subiendo")
                                df_can = pd.DataFrame(canibales)
                                st.dataframe(
                                    df_can[['descripcion', 'similitud', 'vtas_s1', 'vtas_s2',
                                            'delta_pct', 'tendencia']],
                                    column_config={
                                        'descripcion': st.column_config.TextColumn('Canibal', width=250),
                                        'similitud': st.column_config.NumberColumn('Similitud', format="%.2f"),
                                        'vtas_s1': st.column_config.NumberColumn('Vtas S1', format="%d"),
                                        'vtas_s2': st.column_config.NumberColumn('Vtas S2', format="%d"),
                                        'delta_pct': st.column_config.NumberColumn('Delta%', format="%.0f%%"),
                                        'tendencia': 'Tendencia',
                                    },
                                    use_container_width=True, hide_index=True,
                                )
                                st.markdown("**Recomendacion**: No reponer la victima. "
                                            "Redirigir presupuesto al canibal.")
                            else:
                                st.success("No hay canibalizacion. Los sustitutos similares tambien bajan o estan estables.")

                            if no_canib:
                                with st.expander(f"Sustitutos sin canibalizacion ({len(no_canib)})"):
                                    st.dataframe(pd.DataFrame(no_canib)[
                                        ['descripcion', 'similitud', 'vtas_s1', 'vtas_s2', 'delta_pct', 'tendencia']
                                    ], use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════
    # TAB: TENDENCIAS EMERGENTES
    # ══════════════════════════════════════════════════════════════
    with tab_emergentes:
        st.subheader("Tendencias Emergentes")
        st.caption("Productos que estan naciendo fuertes o acelerando. "
                   "La senal temprana de hacia donde va tu mercado.")

        if st.button("Detectar tendencias", type="primary", key="btn_emergentes"):
            with st.spinner("Analizando velocidad, aceleracion y novedad..."):
                df_emerg = detectar_tendencias_emergentes()
                vel_cat = velocidad_promedio_por_categoria()
                marcas_d2 = cargar_marcas_dict()
                provs_d2 = cargar_proveedores_dict()
                sub_d2 = cargar_subrubro_desc()
                st.session_state['emergentes_data'] = {
                    'df': df_emerg, 'vel_cat': vel_cat,
                    'marcas': marcas_d2, 'provs': provs_d2, 'subs': sub_d2
                }

        if 'emergentes_data' in st.session_state:
            edata = st.session_state['emergentes_data']
            df_e = edata['df']
            vel_cat = edata['vel_cat']
            marcas_d2 = edata['marcas']
            provs_d2 = edata['provs']
            sub_d2 = edata['subs']

            if df_e.empty:
                st.info("No se detectaron tendencias emergentes claras en este momento.")
            else:
                # Enriquecer
                df_e['marca_desc'] = df_e['marca'].map(
                    lambda x: marcas_d2.get(int(x), f"#{int(x)}") if pd.notna(x) else "?"
                )
                df_e['prov_nombre'] = df_e['proveedor'].map(
                    lambda x: provs_d2.get(int(x), f"#{int(x)}") if pd.notna(x) else "?"
                )
                df_e['categoria'] = df_e['subrubro'].map(
                    lambda x: sub_d2.get(int(x), '?') if pd.notna(x) else '?'
                )

                # Benchmark: es más rápido que su categoría?
                df_e['vel_cat_prom'] = df_e.apply(
                    lambda r: vel_cat.get((int(r['rubro']), int(r['subrubro'])), 0)
                    if pd.notna(r['rubro']) and pd.notna(r['subrubro']) else 0,
                    axis=1
                )
                df_e['vs_categoria'] = np.where(
                    df_e['vel_cat_prom'] > 0,
                    (df_e['vel_mensual'] / df_e['vel_cat_prom']).round(1),
                    0
                )
                df_e['supera_cat'] = df_e['vs_categoria'] > 2  # vende >2x que el promedio

                # KPIs
                ek1, ek2, ek3, ek4 = st.columns(4)
                ek1.metric("Productos emergentes", len(df_e))
                nuevos = len(df_e[df_e['es_nuevo']])
                ek2.metric("Productos nuevos (<6m)", nuevos)
                acelerando = len(df_e[df_e['aceleracion'] > 100])
                ek3.metric("Aceleracion >100%", acelerando)
                superan = len(df_e[df_e['supera_cat']])
                ek4.metric("Superan 2x su categoria", superan)

                st.divider()

                # Clasificación
                st.markdown("#### Clasificacion de tendencias")
                st.markdown(
                    "- **ESTRELLA**: Nuevo + acelerando + supera su categoria = **comprar agresivo**\n"
                    "- **COHETE**: No es nuevo pero aceleracion explosiva (>100%) = **aumentar reposicion**\n"
                    "- **PROMESA**: Creciendo sostenido, todavia no exploto = **monitorear y preparar stock**"
                )

                df_e['clasificacion'] = 'PROMESA'
                df_e.loc[df_e['aceleracion'] > 100, 'clasificacion'] = 'COHETE'
                df_e.loc[df_e['es_nuevo'] & (df_e['aceleracion'] > 50) & df_e['supera_cat'],
                         'clasificacion'] = 'ESTRELLA'

                # Alerta de stock bajo en emergentes
                sin_stock = df_e[(df_e['dias_stock'] < 30) & (df_e['vel_mensual'] > 2)]
                if not sin_stock.empty:
                    productos_alerta = ", ".join(sin_stock.head(5)['descripcion'].str[:30].tolist())
                    st.error(f"ALERTA: {len(sin_stock)} emergentes con menos de 30 dias de stock: {productos_alerta}...")

                st.divider()

                # Filtros
                ef1, ef2 = st.columns(2)
                with ef1:
                    clasif_disp = sorted(df_e['clasificacion'].unique())
                    clasif_sel = st.multiselect("Clasificacion", clasif_disp,
                                                 default=clasif_disp, key="emerg_clasif")
                with ef2:
                    generos_e = sorted(df_e['genero'].unique())
                    genero_e_sel = st.multiselect("Genero", generos_e,
                                                    default=generos_e, key="emerg_genero")

                df_vis_e = df_e[
                    df_e['clasificacion'].isin(clasif_sel) &
                    df_e['genero'].isin(genero_e_sel)
                ].copy()

                # Tabla principal
                st.dataframe(
                    df_vis_e[['clasificacion', 'descripcion', 'marca_desc', 'genero', 'categoria',
                              'vel_mensual', 'aceleracion', 'vtas_q3', 'vtas_q4',
                              'stock_actual', 'dias_stock', 'vs_categoria', 'momentum']].head(80),
                    column_config={
                        'clasificacion': st.column_config.TextColumn('Tipo', width=90),
                        'descripcion': st.column_config.TextColumn('Producto', width=220),
                        'marca_desc': 'Marca',
                        'genero': st.column_config.TextColumn('Gen.', width=70),
                        'categoria': st.column_config.TextColumn('Cat.', width=100),
                        'vel_mensual': st.column_config.NumberColumn('Vel/mes', format="%.1f",
                            help="Velocidad mensual actual (ultimos 3 meses)"),
                        'aceleracion': st.column_config.NumberColumn('Acelerac.%', format="%.0f%%",
                            help="Crecimiento Q4 vs Q3"),
                        'vtas_q3': st.column_config.NumberColumn('Q3', format="%d",
                            help="Ventas hace 6-3 meses"),
                        'vtas_q4': st.column_config.NumberColumn('Q4', format="%d",
                            help="Ventas ultimos 3 meses"),
                        'stock_actual': st.column_config.NumberColumn('Stock', format="%d"),
                        'dias_stock': st.column_config.NumberColumn('Dias', format="%d"),
                        'vs_categoria': st.column_config.NumberColumn('vs Cat.', format="%.1fx",
                            help="Cuantas veces mas rapido que el promedio de su categoria"),
                        'momentum': st.column_config.ProgressColumn('Momentum', min_value=0, max_value=1,
                            format="%.2f"),
                    },
                    use_container_width=True, hide_index=True,
                )

                st.divider()

                # Resumen por marca: qué marcas están generando emergentes?
                st.markdown("#### Marcas con mas emergentes")
                resumen_marca = df_e.groupby('marca_desc').agg(
                    emergentes=('csr', 'count'),
                    estrellas=('clasificacion', lambda x: (x == 'ESTRELLA').sum()),
                    cohetes=('clasificacion', lambda x: (x == 'COHETE').sum()),
                    vel_total=('vel_mensual', 'sum'),
                    momentum_prom=('momentum', 'mean'),
                ).reset_index().sort_values('emergentes', ascending=False)

                st.dataframe(
                    resumen_marca.head(20),
                    column_config={
                        'marca_desc': 'Marca',
                        'emergentes': st.column_config.NumberColumn('Emergentes', format="%d"),
                        'estrellas': st.column_config.NumberColumn('Estrellas', format="%d"),
                        'cohetes': st.column_config.NumberColumn('Cohetes', format="%d"),
                        'vel_total': st.column_config.NumberColumn('Vel total/mes', format="%.0f"),
                        'momentum_prom': st.column_config.NumberColumn('Momentum prom', format="%.2f"),
                    },
                    use_container_width=True, hide_index=True,
                )

                st.divider()

                # Insight final
                st.markdown("#### La senal")
                top3 = df_e.head(3)
                for _, t in top3.iterrows():
                    emoji = {'ESTRELLA': '⭐', 'COHETE': '🚀', 'PROMESA': '📈'}.get(t['clasificacion'], '')
                    stock_warn = " ⚠️ STOCK BAJO" if t['dias_stock'] < 30 else ""
                    st.markdown(
                        f"{emoji} **{t['descripcion'][:50]}** ({t['marca_desc']}) — "
                        f"Vel: {t['vel_mensual']:.0f}/mes, Acelerac: {t['aceleracion']:+.0f}%, "
                        f"vs cat: {t['vs_categoria']:.1f}x, Stock: {int(t['stock_actual'])} "
                        f"({int(t['dias_stock'])}d){stock_warn}"
                    )

    # ══════════════════════════════════════════════════════════════
    # TAB 4: ARMAR PEDIDO
    # ══════════════════════════════════════════════════════════════
    with tab_pedido:
        st.subheader("🛒 Armar y enviar pedido")

        # Resumen: urgentes sin pedido vs con pedido
        if 'df_top_pedidos' in st.session_state:
            df_tp = st.session_state['df_top_pedidos']
            con_pedido = df_tp[df_tp['Pedido'] == 'Si']
            sin_pedido = df_tp[df_tp['Pedido'] == 'No']

            st.markdown("#### Resumen pedidos ERP vs urgentes")
            rp1, rp2 = st.columns(2)
            with rp1:
                st.metric("Urgentes SIN pedido", len(sin_pedido))
                if not sin_pedido.empty:
                    st.caption("Requieren acción inmediata:")
                    for _, r in sin_pedido.head(10).iterrows():
                        st.markdown(
                            f"- 🔴 **{r['descripcion'][:40]}** — "
                            f"Stock: {int(r['stock_total'])}, "
                            f"Vel: {r['vel_mes']:.1f}/mes, "
                            f"Dias: {int(r['dias_stock'])}"
                        )
            with rp2:
                st.metric("Urgentes CON pedido en camino", len(con_pedido))
                if not con_pedido.empty:
                    for _, r in con_pedido.head(10).iterrows():
                        fe_str = r['Fecha Entrega'].strftime('%d/%m') if pd.notna(r['Fecha Entrega']) else '?'
                        st.markdown(
                            f"- {r['Alerta']} **{r['descripcion'][:40]}** — "
                            f"Pedido: {int(r['Cant. Pedida'])} un., "
                            f"Entrega: {fe_str}"
                        )
            st.divider()

        subtab_simular, subtab_roi = st.tabs(["📊 Simulador de Recupero", "⚡ Pedido desde ROI"])

        # ── SUBTAB: SIMULADOR DE RECUPERO ──
        with subtab_simular:
            st.markdown("#### Simulador de recupero de inversión")
            st.caption("Cargá las líneas del pedido para simular cuántos días tarda en recuperarse la inversión.")

            # Input: tabla editable
            if 'sim_pedido_df' not in st.session_state:
                st.session_state['sim_pedido_df'] = pd.DataFrame([
                    {'marca': '', 'subrubro': '', 'talle': '', 'cantidad': 0,
                     'precio_costo': 0.0, 'codigo_sinonimo': ''}
                ])

            st.markdown("**Opción 1**: Cargá manualmente las líneas")

            sim_df = st.data_editor(
                st.session_state['sim_pedido_df'],
                column_config={
                    'marca': st.column_config.TextColumn('Marca', width=100),
                    'subrubro': st.column_config.TextColumn('Subrubro', width=100),
                    'talle': st.column_config.TextColumn('Talle', width=60),
                    'cantidad': st.column_config.NumberColumn('Cantidad', min_value=0, max_value=9999),
                    'precio_costo': st.column_config.NumberColumn('Precio Costo', format="$%.0f",
                                                                   min_value=0),
                    'codigo_sinonimo': st.column_config.TextColumn('Cod. Sinónimo',
                        width=140, help="CSR 10-12 dígitos del artículo"),
                },
                num_rows="dynamic",
                use_container_width=True, hide_index=True,
                key="sim_editor"
            )
            st.session_state['sim_pedido_df'] = sim_df

            st.divider()

            st.markdown("**Opción 2**: Cargá desde el pedido ya armado (tab Pedido desde ROI)")
            if 'df_talles_pedido' in st.session_state:
                if st.button("📥 Importar desde pedido armado", key="btn_import_pedido"):
                    df_tp_imp = st.session_state['df_talles_pedido'].copy()
                    df_tp_imp = df_tp_imp[df_tp_imp['pedir'] > 0]
                    if not df_tp_imp.empty:
                        st.session_state['sim_pedido_df'] = pd.DataFrame([{
                            'marca': '',
                            'subrubro': '',
                            'talle': str(r.get('talle', '')),
                            'cantidad': int(r['pedir']),
                            'precio_costo': float(r.get('precio_fabrica', 0)),
                            'codigo_sinonimo': str(r.get('codigo_sinonimo', r.get('csr', ''))),
                        } for _, r in df_tp_imp.iterrows()])
                        st.rerun()

            st.divider()

            # Botón simular
            lineas_validas = sim_df[(sim_df['cantidad'] > 0) & (sim_df['precio_costo'] > 0)
                                    & (sim_df['codigo_sinonimo'].str.len() >= 10)]

            if st.button("🔍 Simular recupero", type="primary", key="btn_simular_recupero",
                         disabled=lineas_validas.empty):
                with st.spinner("Calculando quiebre, estacionalidad y recupero..."):
                    lineas_input = [{
                        'codigo_sinonimo': (r['codigo_sinonimo'] or '').strip(),
                        'cantidad': r['cantidad'],
                        'precio_costo': r['precio_costo'],
                        'descripcion': f"{r['marca'] or ''} {r['subrubro'] or ''}".strip(),
                        'talle': r['talle'],
                    } for _, r in lineas_validas.iterrows()]

                    resultado = simular_recupero_pedido(lineas_input)
                    st.session_state['sim_resultado'] = resultado

            # Mostrar resultados
            if 'sim_resultado' in st.session_state and st.session_state['sim_resultado']['lineas']:
                resultado = st.session_state['sim_resultado']
                tot = resultado['totales']
                lineas = resultado['lineas']

                # Semáforo global
                if tot['dias_recupero_prom'] < 60:
                    sem_emoji = "🟢"
                    sem_text = "EXCELENTE"
                elif tot['dias_recupero_prom'] <= 120:
                    sem_emoji = "🟡"
                    sem_text = "MODERADO"
                else:
                    sem_emoji = "🔴"
                    sem_text = "LENTO"

                st.markdown(f"### {sem_emoji} Recupero: {tot['dias_recupero_prom']} días — {sem_text}")

                # KPIs
                k1, k2, k3, k4, k5 = st.columns(5)
                k1.metric("Inversión total", f"${tot['inversion']:,.0f}")
                k2.metric("Ingreso esperado", f"${tot['ingreso_esperado']:,.0f}")
                k3.metric("Margen total", f"${tot['margen']:,.0f}")
                k4.metric("Margen %", f"{tot['margen_pct']:.1f}%")
                k5.metric("Pares", f"{tot['pares']:,}")

                st.divider()

                # Tabla por línea
                df_sim = pd.DataFrame(lineas)
                # Emoji semáforo
                df_sim['sem'] = df_sim['semaforo'].map(
                    {'verde': '🟢', 'amarillo': '🟡', 'rojo': '🔴'})

                st.dataframe(
                    df_sim[['sem', 'descripcion', 'talle', 'cantidad', 'precio_costo',
                            'precio_venta', 'vel_real_mes', 'pct_quiebre',
                            'dias_vender', 'dias_recupero', 'inversion',
                            'ingreso_esperado', 'margen', 'margen_pct']],
                    column_config={
                        'sem': st.column_config.TextColumn('', width=30),
                        'descripcion': st.column_config.TextColumn('Producto', width=150),
                        'talle': st.column_config.TextColumn('Talle', width=50),
                        'cantidad': st.column_config.NumberColumn('Cant', format="%d"),
                        'precio_costo': st.column_config.NumberColumn('P.Costo', format="$%.0f"),
                        'precio_venta': st.column_config.NumberColumn('P.Venta', format="$%.0f"),
                        'vel_real_mes': st.column_config.NumberColumn('Vel/mes', format="%.1f"),
                        'pct_quiebre': st.column_config.NumberColumn('Quiebre%', format="%.0f%%"),
                        'dias_vender': st.column_config.NumberColumn('Días vender', format="%.0f"),
                        'dias_recupero': st.column_config.NumberColumn('Días recup.', format="%d"),
                        'inversion': st.column_config.NumberColumn('Inversión', format="$%.0f"),
                        'ingreso_esperado': st.column_config.NumberColumn('Ingreso', format="$%.0f"),
                        'margen': st.column_config.NumberColumn('Margen $', format="$%.0f"),
                        'margen_pct': st.column_config.NumberColumn('Margen%', format="%.1f%%"),
                    },
                    use_container_width=True, hide_index=True,
                )

                # Gráfico de barras: días de recupero por línea
                st.divider()
                st.markdown("#### Días de recupero por línea")
                df_chart = df_sim[df_sim['dias_recupero'] < 9999].copy()
                if not df_chart.empty:
                    df_chart['label'] = df_chart.apply(
                        lambda r: f"{r['descripcion'][:20]} T{r['talle']}" if r['talle'] else r['descripcion'][:25],
                        axis=1
                    )
                    chart_data = df_chart.set_index('label')['dias_recupero']
                    st.bar_chart(chart_data, color='#1976d2')

                    # Líneas de referencia en texto
                    st.caption("🟢 < 60 días | 🟡 60-120 días | 🔴 > 120 días")

        # ── SUBTAB: PEDIDO DESDE ROI ──
        with subtab_roi:
            if 'df_ranking' not in st.session_state:
                st.info("Primero calculá el ranking ROI en la pestaña 'Optimizar Compra'.")
            else:
                df_rank = st.session_state['df_ranking']
                dentro = df_rank[df_rank['dentro_presupuesto']].copy()

                if dentro.empty:
                    st.warning("No hay productos dentro del presupuesto.")
                else:
                    # Agrupar por proveedor
                    provs = dentro['proveedor'].unique()
                    prov_pedido = st.selectbox("Proveedor para el pedido", sorted(provs),
                                               key="prov_pedido_sel")

                    df_prov = dentro[dentro['proveedor'] == prov_pedido].copy()

                    st.markdown(f"**{len(df_prov)} productos** — "
                                f"**{int(df_prov['pedir'].sum())} pares** — "
                                f"**${df_prov['inversion'].sum():,.0f}**")

                    # Para cada producto, cargar talles
                    if st.button("📋 Cargar detalle por talle", type="primary", key="btn_talles"):
                        with st.spinner("Cargando talles..."):
                            df_pend = obtener_pendientes()
                            all_talles = []
                            for _, prod in df_prov.iterrows():
                                df_t = analizar_producto_detalle(prod['csr'], df_pend)
                                if not df_t.empty:
                                    ventas_total = df_t['ventas_12m'].sum()
                                    for _, t in df_t.iterrows():
                                        pct = t['ventas_12m'] / ventas_total * 100 if ventas_total > 0 else 0
                                        pedir_talle = max(0, round(prod['pedir'] * pct / 100))
                                        all_talles.append({
                                            'csr': prod['csr'],
                                            'descripcion_1': prod['descripcion'],
                                            'codigo': int(t['codigo']),
                                            'codigo_sinonimo': t['codigo_sinonimo'],
                                            'talle': t.get('talle', ''),
                                            'stock': int(t['stock_actual']),
                                            'pendiente': int(t.get('pendiente', 0)),
                                            'ventas_12m': int(t['ventas_12m']),
                                            'pct': round(pct, 1),
                                            'precio_fabrica': float(t.get('precio_fabrica', 0)),
                                            'pedir': pedir_talle,
                                        })

                            if all_talles:
                                st.session_state['df_talles_pedido'] = pd.DataFrame(all_talles)

                    # Editar cantidades
                    if 'df_talles_pedido' in st.session_state:
                        df_tp = st.session_state['df_talles_pedido'].copy()

                        st.divider()
                        st.markdown("#### Editá las cantidades por talle")

                        df_edit = st.data_editor(
                            df_tp[['descripcion_1', 'talle', 'stock', 'pendiente',
                                   'ventas_12m', 'pct', 'precio_fabrica', 'pedir']],
                            column_config={
                                'descripcion_1': st.column_config.TextColumn('Producto', disabled=True, width=200),
                                'talle': st.column_config.TextColumn('Talle', disabled=True),
                                'stock': st.column_config.NumberColumn('Stock', disabled=True),
                                'pendiente': st.column_config.NumberColumn('Pend.', disabled=True),
                                'ventas_12m': st.column_config.NumberColumn('Vtas 12m', disabled=True),
                                'pct': st.column_config.NumberColumn('% Talle', disabled=True, format="%.1f%%"),
                                'precio_fabrica': st.column_config.NumberColumn('Precio', disabled=True, format="$%.0f"),
                                'pedir': st.column_config.NumberColumn('PEDIR', min_value=0, max_value=999),
                            },
                            use_container_width=True, hide_index=True,
                            key="edit_talles"
                        )

                        # Actualizar cantidades
                        df_tp['pedir'] = df_edit['pedir'].values

                        total_pares = int(df_tp['pedir'].sum())
                        total_monto = (df_tp['pedir'] * df_tp['precio_fabrica']).sum()

                        st.markdown(f"### Total: {total_pares} pares — ${total_monto:,.0f}")

                        # Observaciones
                        empresa = st.selectbox("Empresa", ["H4", "CALZALINDO"], key="empresa_sel")
                        fecha_ent = st.date_input("Fecha entrega", date.today() + timedelta(days=30),
                                                  key="fecha_ent")
                        obs = st.text_area("Observaciones",
                                           f"Pedido automático reposición inteligente. "
                                           f"Presupuesto ${presupuesto:,.0f}. "
                                           f"Análisis waterfall 60d + quiebre + ROI.",
                                           key="obs_pedido")

                        st.divider()

                        # Buscar proveedor ID
                        prov_id = None
                        for num, p in provs_dict.items():
                            if p.strip() == prov_pedido.strip():
                                prov_id = num
                                break

                        col_ins, col_email = st.columns(2)

                        with col_ins:
                            if total_pares > 0 and prov_id:
                                # Paso 1: resumen y confirmación
                                renglones_activos = df_tp[df_tp['pedir'] > 0]
                                st.info(
                                    f"**Resumen pedido**\n\n"
                                    f"- Proveedor: **{prov_pedido}** (#{prov_id})\n"
                                    f"- Empresa: **{empresa}**\n"
                                    f"- Renglones: **{len(renglones_activos)}**\n"
                                    f"- Total pares: **{total_pares}**\n"
                                    f"- Monto: **${total_monto:,.0f}**\n"
                                    f"- Entrega: **{fecha_ent}**"
                                )

                                confirmar = st.checkbox(
                                    "Confirmo que los datos son correctos — insertar en produccion",
                                    key="chk_confirmar_insert")

                                if st.button("⚡ INSERTAR EN ERP", type="primary",
                                             use_container_width=True, key="btn_insert",
                                             disabled=not confirmar):
                                    with st.spinner(
                                        f"Insertando {total_pares} pares en "
                                        f"{empresa} para {prov_pedido}..."
                                    ):
                                        try:
                                            numero, msg = insertar_pedido_produccion(
                                                prov_id, empresa, df_tp, obs, fecha_ent)
                                            if numero:
                                                st.success(f"✅ {msg}")
                                                st.session_state['ultimo_pedido'] = numero
                                                guardar_log({
                                                    'fecha': str(datetime.now()),
                                                    'numero': numero,
                                                    'proveedor': prov_pedido,
                                                    'prov_id': prov_id,
                                                    'empresa': empresa,
                                                    'pares': total_pares,
                                                    'monto': total_monto,
                                                    'presupuesto': presupuesto,
                                                    'estado': 'insertado',
                                                    'email_enviado': False,
                                                    'confirmado': False,
                                                })
                                                st.balloons()
                                            else:
                                                st.error(f"❌ {msg}")
                                        except Exception as e:
                                            st.error(f"❌ Error: {e}")
                            else:
                                st.info("No hay pares para pedir o proveedor no encontrado.")

                        with col_email:
                            st.markdown("#### 📧 Email proveedor")
                            email_dest = st.text_input("Email", key="email_prov",
                                                        placeholder="ventas@proveedor.com")
                            num_ped = st.session_state.get('ultimo_pedido', '---')

                            if st.button("📤 ENVIAR EMAIL", use_container_width=True,
                                         disabled=not email_dest or num_ped == '---',
                                         key="btn_email"):
                                from app_pedido_auto import enviar_email_proveedor
                                ok, msg = enviar_email_proveedor(prov_id, num_ped, df_tp, email_dest)
                                if ok:
                                    st.success(f"✅ {msg}")
                                else:
                                    st.error(f"❌ {msg}")

    # ══════════════════════════════════════════════════════════════
    # TAB 5: HISTORIAL
    # ══════════════════════════════════════════════════════════════
    with tab_historial:
        st.subheader("📋 Historial de pedidos")
        log = cargar_log()
        if not log:
            st.info("No hay pedidos registrados todavía.")
        else:
            df_log = pd.DataFrame(log).sort_values('fecha', ascending=False)
            st.dataframe(
                df_log,
                column_config={
                    'monto': st.column_config.NumberColumn(format="$%.0f"),
                    'presupuesto': st.column_config.NumberColumn(format="$%.0f"),
                    'email_enviado': st.column_config.CheckboxColumn("Email"),
                    'confirmado': st.column_config.CheckboxColumn("Confirmado"),
                },
                use_container_width=True, hide_index=True,
            )

            # Marcar como confirmado
            pendientes = [e for e in log if not e.get('confirmado', False)]
            if pendientes:
                nums = [e.get('numero') for e in pendientes if e.get('numero')]
                if nums:
                    confirmar = st.selectbox("Marcar como confirmado:", nums, key="confirm_sel")
                    if st.button("✅ Confirmar recepción", key="btn_confirm"):
                        for entry in log:
                            if entry.get('numero') == confirmar:
                                entry['confirmado'] = True
                                entry['fecha_confirmacion'] = str(datetime.now())
                        with open(LOG_FILE, 'w') as f:
                            json.dump(log, f, indent=2, default=str)
                        st.success(f"Pedido #{confirmar} confirmado.")
                        st.rerun()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    render_dashboard()
