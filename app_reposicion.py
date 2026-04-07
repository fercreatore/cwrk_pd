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

# ── FIX SSL: DEBE ir ANTES de importar pyodbc ──
# OpenSSL 3.x rechaza TLS 1.0 que usa SQL Server 2012
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
    _os.environ["OPENSSL_CONF"] = _ssl_conf  # forzar, no setdefault

import streamlit as st
import pandas as pd
import numpy as np
import pyodbc
import json
import os
import io
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

# Estacionalidad real (pares/mes promedio 2023-2026, % vs promedio mensual ~11,958)
ESTACIONALIDAD_MENSUAL = {
    1: 0.88, 2: 1.04, 3: 0.74, 4: 0.73, 5: 0.93, 6: 1.05,
    7: 0.98, 8: 0.92, 9: 0.93, 10: 1.22, 11: 1.04, 12: 1.51,
}
PARES_PROMEDIO_MENSUAL = 11958
PARES_TOTAL_ANUAL = 143500
# Ratio C/V modelo nuevo: 75% → se está drenando stock
RATIO_CV_NUEVO = 0.75

CONN_REPLICA = get_conn_string("msgestionC")

# Nichos de producto predefinidos para análisis estacional
NICHOS_PREDEFINIDOS = {
    'COMUNION': {
        'nombre': 'Comunión / Confirmación',
        'subrubros': (17, 18),  # GUILLERMINA, CHATA
        'color': '%BLANC%',
        'rubros': (1, 5),  # DAMAS, NIÑAS
        'temporada_esperada': (9, 10, 11, 12),  # Sep-Dic
        'marcas_clave': ['GOFFO', 'BEBS', 'RED GREEN', 'ENONA DE DELI'],
        'talle_rango': (27, 40),
        'edad_target': '6-15 años (niñas) + damas jóvenes',
        'estacionalidad': {9: 1.62, 10: 2.31, 11: 2.08, 12: 1.15,
                          1: 0.38, 2: 0.46, 3: 0.62, 4: 0.54,
                          5: 0.54, 6: 0.46, 7: 0.38, 8: 0.46},
    },
    'OFICINA_HOMBRE': {
        'nombre': 'Hombre Oficina / Trabajo',
        'subrubros': (20, 52, 40),  # ZAPATO VESTIR, CASUAL, NAUTICO
        'color': None,  # todos los colores
        'rubros': (3,),  # HOMBRES
        'temporada_esperada': (10, 11, 12),  # Oct-Dic (regalos+fiestas)
        'talle_rango': (39, 46),
        'talle_pico': (41, 42),  # 17% cada uno
        'edad_target': '25-55 años',
        'demanda_anual_pares': 5494,
        'estacionalidad': {1: 0.66, 2: 0.86, 3: 0.88, 4: 0.78,
                          5: 0.82, 6: 1.02, 7: 0.85, 8: 0.88,
                          9: 0.99, 10: 1.24, 11: 1.36, 12: 1.66},
        'curva_talles_pct': {39: 7.5, 40: 11.5, 41: 16.5, 42: 17.0,
                            43: 15.3, 44: 10.3, 45: 4.6, 46: 0.9},
    },
    'ADOLESCENTE_ESCUELA': {
        'nombre': 'Adolescente Escuela (13-18 años)',
        'subrubros': (49, 48, 40, 52),  # TRAINING, TENNIS, NAUTICO, CASUAL
        'color': None,
        'rubros': (4, 5),  # NIÑOS, NIÑAS
        'temporada_esperada': (2, 3, 7, 8),  # Feb-Mar (inicio clases) + Jul-Ago (2do cuatri)
        'talle_rango': (33, 42),
        'talle_pico': (33, 34),  # 33.7% + 31.3% = 65% en solo 2 talles
        'edad_target': '10-16 años',
        'demanda_anual_pares': 2410,
        'estacionalidad': {1: 0.56, 2: 2.36, 3: 0.96, 4: 0.73,
                          5: 0.90, 6: 0.76, 7: 0.91, 8: 1.07,
                          9: 0.85, 10: 0.77, 11: 0.57, 12: 0.65},
        'curva_talles_pct': {33: 33.7, 34: 31.3, 35: 12.0, 36: 9.1,
                            37: 7.0, 38: 3.5, 39: 1.7, 40: 1.5},
    },
    'COLEGIO_PRIMARIA': {
        'nombre': 'Colegio Primaria (6-12 años)',
        'subrubros': (49, 48, 40),  # TRAINING, TENNIS, NAUTICO
        'color': None,
        'rubros': (4, 5),  # NIÑOS, NIÑAS
        'temporada_esperada': (2, 3),  # Feb-Mar inicio clases
        'talle_rango': (27, 34),
        'edad_target': '6-12 años',
    },
    'VERANO': {
        'nombre': 'Verano (Ojotas/Sandalias/Zuecos)',
        'subrubros': (11, 12, 13),  # OJOTAS, SANDALIAS, ZUECOS
        'color': None,
        'rubros': (1, 3, 4, 5),  # todos
        'temporada_esperada': (11, 12, 1, 2, 3),  # Nov-Mar
    },
    'INVIERNO': {
        'nombre': 'Invierno (Botas/Borcegos)',
        'subrubros': (14, 15),  # BORCEGOS, BOTAS
        'color': None,
        'rubros': (1, 3, 4, 5),
        'temporada_esperada': (4, 5, 6, 7, 8),  # Abr-Ago
    },
    'DEPORTES_RUNNING': {
        'nombre': 'Running / Training Adulto',
        'subrubros': (47, 49),  # RUNNING, TRAINING
        'color': None,
        'rubros': (1, 3),  # DAMAS, HOMBRES
        'temporada_esperada': (),  # plano todo el año
        'talle_pico': (41, 42),  # hombres; damas: 37, 38
    },
    'PANTUFLAS': {
        'nombre': 'Pantuflas / Chinelas',
        'subrubros': (60, 37),  # PANTUFLA, FRANCISCANA/CHINELA
        'color': None,
        'rubros': (1, 3, 4, 5),
        'temporada_esperada': (4, 5, 6, 7),  # Abr-Jul
        'picos_regalo': {6: 'Día del Padre', 10: 'Día de la Madre', 12: 'Navidad'},
    },
    'GRADUACION_FIESTAS': {
        'nombre': 'Graduación y Fiestas',
        'subrubros': (20, 12, 17),  # VESTIR, SANDALIAS, GUILLERMINA
        'color': None,
        'rubros': (1, 3, 5),  # DAMAS, HOMBRES, NIÑAS
        'temporada_esperada': (11, 12),  # Nov-Dic
    },
}

# ============================================================================
# LEAD TIMES POR PROVEEDOR (días desde pedido hasta recepción)
# ============================================================================
LEAD_TIMES = {
    220: 15,   # MASKOTA SRL — JIT real (entrega muy rápida)
    104: 21,   # GTN — folclore / campus
    11:  30,   # TIMMIS
    457: 30,   # ZOTZ
    594: 45,   # VICBOR/ATOMIK
    641: 21,   # FLOYD medias
    860: 30,   # DISTRIGROUP/JOHN FOOS
    118: 30,   # EL FARAÓN
    656: 45,   # DISTRINANDO/REEBOK
    561: 30,   # SOUTER/RINGO
    614: 45,   # CALZADOS BLANCO/DIADORA
    668: 45,   # ALPARGATAS/TOPPER
    722: 45,   # GLOBAL BRANDS/OLYMPIKUS
}
LEAD_TIME_DEFAULT = 45  # Para proveedores no configurados

# ============================================================================
# TEMPORADA DE COMPRA POR SUBRUBRO
# Comprar = 2-3 meses ANTES de la temporada de venta
# ============================================================================
SUBRUBRO_TEMPORADA = {
    # VERANO (vender Oct-Mar, comprar Jul-Sep)
    11: {'nombre': 'OJOTAS', 'venta': (10, 11, 12, 1, 2, 3), 'compra': (7, 8, 9)},
    12: {'nombre': 'SANDALIAS', 'venta': (10, 11, 12, 1, 2, 3), 'compra': (7, 8, 9)},
    13: {'nombre': 'ZUECOS', 'venta': (10, 11, 12, 1, 2, 3), 'compra': (7, 8, 9)},
    37: {'nombre': 'FRANCISCANA', 'venta': (10, 11, 12, 1, 2, 3), 'compra': (8, 9, 10)},

    # INVIERNO (vender Abr-Ago, comprar Ene-Mar)
    15: {'nombre': 'BOTAS', 'venta': (4, 5, 6, 7, 8), 'compra': (1, 2, 3)},
    14: {'nombre': 'BORCEGOS', 'venta': (4, 5, 6, 7, 8), 'compra': (1, 2, 3)},
    60: {'nombre': 'PANTUFLA', 'venta': (4, 5, 6, 7, 8), 'compra': (2, 3, 4)},
    6:  {'nombre': 'CHINELA', 'venta': (5, 6, 7, 8), 'compra': (3, 4, 5)},

    # ESCOLAR (vender Feb-Mar, comprar Nov-Ene)
    40: {'nombre': 'NAUTICO', 'venta': (2, 3, 4), 'compra': (11, 12, 1)},

    # COMUNION (vender Sep-Dic, comprar Jun-Ago)
    17: {'nombre': 'GUILLERMINA', 'venta': (9, 10, 11, 12), 'compra': (6, 7, 8)},
    18: {'nombre': 'CHATA', 'venta': (9, 10, 11, 12), 'compra': (6, 7, 8)},

    # TODO EL AÑO (siempre comprar)
    49: {'nombre': 'ZAPATILLA TRAINING', 'venta': tuple(range(1, 13)), 'compra': tuple(range(1, 13))},
    47: {'nombre': 'ZAPATILLA RUNNING', 'venta': tuple(range(1, 13)), 'compra': tuple(range(1, 13))},
    48: {'nombre': 'ZAPATILLA TENNIS', 'venta': tuple(range(1, 13)), 'compra': tuple(range(1, 13))},
    51: {'nombre': 'ZAPATILLA OUTDOOR', 'venta': tuple(range(1, 13)), 'compra': tuple(range(1, 13))},
    52: {'nombre': 'ZAPATILLA CASUAL', 'venta': tuple(range(1, 13)), 'compra': tuple(range(1, 13))},
    55: {'nombre': 'ZAPATILLA SNEAKERS', 'venta': tuple(range(1, 13)), 'compra': tuple(range(1, 13))},
    20: {'nombre': 'ZAPATO DE VESTIR', 'venta': tuple(range(1, 13)), 'compra': tuple(range(1, 13))},
    29: {'nombre': 'MEDIAS', 'venta': tuple(range(1, 13)), 'compra': tuple(range(1, 13))},
}


def es_temporada_compra(subrubro, mes_actual=None):
    """
    Determines if now is the right time to BUY (not sell) products in this subrubro.
    Buying happens 2-3 months BEFORE the selling season.

    Returns: dict {comprar_ahora: bool, temporada_venta: str, meses_pico: list, razon: str}
    """
    from datetime import datetime
    if mes_actual is None:
        mes_actual = datetime.now().month

    nombres_mes = {
        1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
    }

    if subrubro not in SUBRUBRO_TEMPORADA:
        return {
            'comprar_ahora': True,
            'temporada_venta': 'Todo el año',
            'meses_pico': list(range(1, 13)),
            'razon': 'Subrubro sin estacionalidad definida - compra permanente'
        }

    info = SUBRUBRO_TEMPORADA[subrubro]
    meses_compra = info['compra']
    meses_venta = info['venta']
    comprar_ahora = mes_actual in meses_compra

    temporada_venta_str = '-'.join(
        nombres_mes[m] for m in (meses_venta[0], meses_venta[-1])
    )

    if comprar_ahora:
        razon = (
            f"{info['nombre']}: ventana de compra activa "
            f"({', '.join(nombres_mes[m] for m in meses_compra)}). "
            f"Venta pico {temporada_venta_str}."
        )
    else:
        razon = (
            f"{info['nombre']}: fuera de ventana de compra. "
            f"Comprar en {', '.join(nombres_mes[m] for m in meses_compra)}, "
            f"venta pico {temporada_venta_str}."
        )

    return {
        'comprar_ahora': comprar_ahora,
        'temporada_venta': temporada_venta_str,
        'meses_pico': list(meses_venta),
        'razon': razon
    }


# ============================================================================
# CALIBRACIÓN BACKTESTING (36 familias testeadas, 23-24 mar 2026)
# factor_correccion: si el modelo subestimó 41%, correccion = 1.41
# confianza: alta = error < 15%, media = 15-50%, baja = > 50%
# ============================================================================
BACKTESTING_CALIBRACION = {
    # VERANO — modelo subestima sistemáticamente
    '65611016': {'nombre': 'CROCBAND C11016', 'tipo': 'verano', 'correccion': 1.41, 'confianza': 'media', 'error_pct': -41},
    '65610998': {'nombre': 'CROCBAND KIDS', 'tipo': 'verano', 'correccion': 1.80, 'confianza': 'baja', 'error_pct': -80},
    '08727000': {'nombre': 'ZUECO 270 HOMBRE', 'tipo': 'verano', 'correccion': 1.43, 'confianza': 'media', 'error_pct': -43},
    '23649500': {'nombre': 'ALPARGATA REFORZADA', 'tipo': 'verano', 'correccion': 1.16, 'confianza': 'media', 'error_pct': -16},
    # INVIERNO — modelo acierta bien
    '11855000': {'nombre': 'HORNITO 0055', 'tipo': 'invierno', 'correccion': 1.0, 'confianza': 'alta', 'error_pct': 2.7},
    '63471130': {'nombre': 'IMPERMEABILIZANTE', 'tipo': 'invierno', 'correccion': 0.52, 'confianza': 'media', 'error_pct': 90},
    '457260PU': {'nombre': '260PU FOLCLORE', 'tipo': 'invierno', 'correccion': 1.90, 'confianza': 'baja', 'error_pct': -90},
    '01100350': {'nombre': '349 FOLCLORE', 'tipo': 'invierno', 'correccion': 1.0, 'confianza': 'alta', 'error_pct': 0},
    # PERENNE — buenos resultados
    '66821872': {'nombre': 'TOPPER X FORCER', 'tipo': 'perenne', 'correccion': 1.0, 'confianza': 'alta', 'error_pct': 9.7},
    '66829701': {'nombre': 'TIE BREAK III', 'tipo': 'perenne', 'correccion': 0.54, 'confianza': 'baja', 'error_pct': 117},
    # ESCOLAR — sobrecompra
    '64171000': {'nombre': 'MEDIAS COLEGIALES', 'tipo': 'escolar', 'correccion': 0.67, 'confianza': 'media', 'error_pct': 200},
    '09615110': {'nombre': 'MEDIAS COL BORDO', 'tipo': 'escolar', 'correccion': 0.77, 'confianza': 'media', 'error_pct': 29},
    # MEDIAS — modelo subestima (100% quiebre en muchos talles)
    '51511101': {'nombre': 'SOQUETE DAMA LISO', 'tipo': 'perenne', 'correccion': 2.0, 'confianza': 'baja', 'error_pct': -100},
    '51500102': {'nombre': 'SOQUETE HOMBRE LISO', 'tipo': 'perenne', 'correccion': 2.0, 'confianza': 'baja', 'error_pct': -100},
}

# Factores de corrección promedio por tipo (para familias sin backtesting)
CORRECCION_TIPO_DEFAULT = {
    'verano': 1.45,    # promedio de Crocs+Zueco+Alpargata
    'invierno': 1.0,   # Hornito acierta bien
    'perenne': 1.0,    # Topper acierta bien
    'escolar': 0.72,   # tiende a sobrecomprar
}

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
    """Crea una conexión nueva a SQL Server. Configura OpenSSL legacy si es necesario."""
    # Asegurar OpenSSL legacy para Mac + SQL Server 2012
    if os.path.exists(OPENSSL_LEGACY_CNF) and 'OPENSSL_CONF' not in os.environ:
        os.environ['OPENSSL_CONF'] = OPENSSL_LEGACY_CNF
    try:
        return pyodbc.connect(CONN_COMPRAS, timeout=20)
    except Exception:
        try:
            return pyodbc.connect(CONN_REPLICA, timeout=20)
        except Exception as e:
            st.error(f"⚠️ No se pudo conectar a SQL Server. Verificá VPN/red. Error: {e}")
            raise


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

    # 1. Stock actual por codigo_sinonimo (LEFT 10 para matchear CSR truncado)
    sql_stock = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               ISNULL(SUM(s.stock_actual), 0) AS stock
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        WHERE LEFT(a.codigo_sinonimo, 10) IN ({filtro})
          AND s.deposito IN {DEPOS_SQL}
        GROUP BY LEFT(a.codigo_sinonimo, 10)
    """
    df_stock = query_df(sql_stock)
    stock_dict = {}
    for _, r in df_stock.iterrows():
        stock_dict[r['csr'].strip()] = float(r['stock'])

    # 2. Ventas mensuales por codigo_sinonimo (LEFT 10)
    sql_ventas = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND LEFT(a.codigo_sinonimo, 10) IN ({filtro})
          AND v.fecha >= '{desde}'
        GROUP BY LEFT(a.codigo_sinonimo, 10), YEAR(v.fecha), MONTH(v.fecha)
    """
    df_ventas = query_df(sql_ventas)

    # 3. Compras mensuales por codigo_sinonimo
    sql_compras = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(rc.cantidad) AS cant,
               YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes
        FROM msgestionC.dbo.compras1 rc
        JOIN msgestion01art.dbo.articulo a ON rc.articulo = a.codigo
        WHERE rc.operacion = '+'
          AND LEFT(a.codigo_sinonimo, 10) IN ({filtro})
          AND rc.fecha >= '{desde}'
        GROUP BY LEFT(a.codigo_sinonimo, 10), YEAR(rc.fecha), MONTH(rc.fecha)
    """
    df_compras = query_df(sql_compras)

    # Organizar ventas y compras en dicts
    ventas_by_cs = {}
    for _, r in df_ventas.iterrows():
        cs = r['csr'].strip()
        if cs not in ventas_by_cs:
            ventas_by_cs[cs] = {}
        ventas_by_cs[cs][(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    compras_by_cs = {}
    for _, r in df_compras.iterrows():
        cs = r['csr'].strip()
        if cs not in compras_by_cs:
            compras_by_cs[cs] = {}
        compras_by_cs[cs][(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    # Lista de meses hacia atrás
    meses_lista = []
    cursor = hoy.replace(day=1)
    for _ in range(meses):
        meses_lista.append((cursor.year, cursor.month))
        cursor -= relativedelta(months=1)

    # Pre-calcular factores estacionales para desestacionalizar
    factores_est = factor_estacional_batch(codigos_sinonimo)

    # Reconstruir quiebre para cada codigo_sinonimo
    resultados = {}
    for cs in codigos_sinonimo:
        stock_actual = stock_dict.get(cs, 0)
        v_dict = ventas_by_cs.get(cs, {})
        c_dict = compras_by_cs.get(cs, {})
        f_est = factores_est.get(cs, {m: 1.0 for m in range(1, 13)})

        stock_fin = stock_actual
        meses_q = 0
        meses_ok = 0
        ventas_total = 0
        ventas_ok = 0
        ventas_desest = 0  # ventas desestacionalizadas (meses OK)
        ventas_meses_ok = []  # para calcular std_mensual

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
                ventas_meses_ok.append(v)
                # Desestacionalizar: dividir ventas por factor del mes
                s_t = max(f_est.get(mes, 1.0), 0.1)
                ventas_desest += v / s_t

            stock_fin = stock_inicio

        vel_ap = ventas_total / max(meses, 1)

        # vel_real v3: desestacionalizada + corrección disponibilidad
        pct_q = meses_q / max(meses, 1)
        if meses_ok > 0:
            vel_base = ventas_desest / meses_ok
        elif ventas_total > 0:
            # Quiebre 100%: fallback vel_aparente × 1.15
            vel_base = vel_ap * 1.15
        else:
            vel_base = 0

        # Factor corrección por disponibilidad (demanda latente reprimida)
        if pct_q > 0.5:
            factor_disp = 1.20
        elif pct_q > 0.3:
            factor_disp = 1.10
        else:
            factor_disp = 1.0

        vel_real = vel_base * factor_disp

        # Desvío estándar mensual (solo meses no quebrados)
        std_mes = float(np.std(ventas_meses_ok)) if ventas_meses_ok else 0.0

        # ── Estimación de ventas perdidas (segundo pase) ──
        # Para cada mes quebrado, estimar cuánto se habría vendido
        # usando vel_base ajustada por estacionalidad del mes
        ventas_perdidas = 0
        if meses_ok > 0 and vel_base > 0:
            stock_fin2 = stock_actual
            for anio, mes in meses_lista:
                v = v_dict.get((anio, mes), 0)
                c = c_dict.get((anio, mes), 0)
                stock_inicio_check = stock_fin2 + v - c
                if stock_inicio_check <= 0:
                    # Mes quebrado → estimar ventas esperadas
                    factor_mes = max(f_est.get(mes, 1.0), 0.1)
                    ventas_esperadas = vel_base * factor_mes
                    ventas_perdidas += max(0, ventas_esperadas - v)
                stock_fin2 = stock_inicio_check

        resultados[cs] = {
            'stock_actual': stock_actual,
            'meses_quebrado': meses_q,
            'meses_ok': meses_ok,
            'pct_quiebre': round(pct_q * 100, 1),
            'vel_aparente': round(vel_ap, 2),
            'vel_real': round(vel_real, 2),
            'vel_base_desest': round(vel_base, 2),
            'factor_disp': factor_disp,
            'ventas_total': ventas_total,
            'ventas_ok': ventas_ok,
            'std_mensual': round(std_mes, 2),
            'ventas_perdidas': round(ventas_perdidas),
            'vel_real_con_perdidas': round((ventas_total + ventas_perdidas) / max(meses, 1), 2),
        }

    return resultados


# ============================================================================
# SAFETY STOCK (stock de seguridad + punto de reorden)
# ============================================================================

def calcular_safety_stock(vel_mensual, std_mensual, lead_time_dias=30, service_level=0.95):
    """
    Calcula stock de seguridad usando distribución normal.

    Args:
        vel_mensual: velocidad promedio mensual (pares/mes)
        std_mensual: desvío estándar mensual
        lead_time_dias: días de lead time del proveedor
        service_level: nivel de servicio deseado (0.95 = 95%)

    Returns: dict {safety_stock, reorder_point, z_score}
    """
    try:
        from scipy.stats import norm
        z = norm.ppf(service_level)
    except ImportError:
        # Fallback: z-scores comunes sin scipy
        _z_table = {0.90: 1.28, 0.95: 1.65, 0.975: 1.96, 0.99: 2.33}
        z = _z_table.get(service_level, 1.65)

    lt_meses = lead_time_dias / 30.0
    safety = z * std_mensual * (lt_meses ** 0.5)
    rop = vel_mensual * lt_meses + safety
    return {
        'safety_stock': round(max(safety, 0)),
        'reorder_point': round(max(rop, 0)),
        'z_score': round(z, 2),
    }


# ============================================================================
# MOTOR DE DECISIÓN JIT (Just In Time)
# ============================================================================

def calcular_decision_reposicion(df_articulos: pd.DataFrame, proveedor: int,
                                  horizonte_dias: int = 90,
                                  nivel_servicio: float = 0.95,
                                  factores_est: dict = None) -> pd.DataFrame:
    """
    Motor de decisión JIT por artículo con ajuste estacional forward-looking.

    Dado un DataFrame con stock_actual y vel_real (pares/mes), calcula:
      - si hay que pedir hoy
      - cuánto pedir
      - nivel de urgencia (ROJO / AMARILLO / VERDE / SIN_DEMANDA)

    Fórmulas:
      vel_diaria       = vel_real / 30
      factor_est       = avg(factores del período de venta) / factor_mes_actual
                         → corrige vel_real (desestacionalizada) al ritmo proyectado
      vel_diaria_proj  = vel_diaria * factor_est  (usada para punto_reorden y cantidad)
      dias_stock       = stock_actual / vel_diaria  (ritmo ACTUAL, no proyectado)
      safety_stock     = z * sqrt(lead_time * vel_diaria_proj)   (Poisson)
      punto_reorden    = vel_diaria_proj * lead_time + safety_stock
      necesita_pedido  = stock_actual <= punto_reorden  AND  vel_diaria > 0
      cantidad_sugerida = max(0, vel_diaria_proj * horizonte_dias + safety_stock - stock_actual)
      urgencia:
        ROJO     → dias_stock < lead_time          (quiebre antes de recibir)
        AMARILLO → dias_stock < lead_time * 2      (hay que pedir YA)
        VERDE    → dias_stock >= lead_time * 2
        SIN_DEMANDA → vel_diaria = 0

    Args:
        df_articulos: DataFrame con columnas stock_actual, vel_real, codigo_sinonimo
        proveedor: código de proveedor (para lookup en LEAD_TIMES)
        horizonte_dias: días de cobertura objetivo al comprar
        nivel_servicio: 0.85-0.99
        factores_est: dict {codigo_sinonimo: {mes: factor}} de factor_estacional_batch.
                      Si None, usa ESTACIONALIDAD_MENSUAL como fallback global.

    Returns:
        DataFrame con columnas adicionales de decisión JIT (incluye factor_est)
    """
    try:
        from scipy import stats as scipy_stats
        z = float(scipy_stats.norm.ppf(nivel_servicio))
    except Exception:
        _z_fallback = {0.85: 1.04, 0.90: 1.28, 0.95: 1.65, 0.99: 2.33}
        z = _z_fallback.get(nivel_servicio, 1.65)

    lead_time = LEAD_TIMES.get(proveedor, LEAD_TIME_DEFAULT)

    df = df_articulos.copy()

    # Velocidad diaria — preferir vel_real_con_perdidas si existe
    vel_col = 'vel_real_con_perdidas' if 'vel_real_con_perdidas' in df.columns else 'vel_real'
    df['vel_diaria'] = df[vel_col].fillna(0) / 30.0

    # ── Ajuste estacional forward-looking ──────────────────────────────────────
    # vel_real es una tasa desestacionalizada (ritmo "plano" promedio anual).
    # Para comprar hoy para vender en el período futuro, necesitamos proyectar
    # la velocidad real de ese período, no la del mes actual.
    #
    # factor_est = avg_factor_periodo_venta / factor_mes_actual
    # Si compro en marzo (factor 0.74) para vender en junio (factor 1.05):
    #   factor_est = 1.05 / 0.74 = 1.42  → comprar 42% más de lo que el ritmo actual sugiere
    hoy = date.today()
    inicio_venta = hoy + relativedelta(days=lead_time)
    fin_venta    = hoy + relativedelta(days=lead_time + horizonte_dias)

    # Lista de meses cubiertos por el período de venta
    meses_venta = []
    cur = inicio_venta.replace(day=1)
    while cur <= fin_venta.replace(day=1):
        meses_venta.append(cur.month)
        cur += relativedelta(months=1)
    if not meses_venta:
        meses_venta = [hoy.month]

    def _factor_ajuste_para(csr: str) -> float:
        """Factor de ajuste estacional para el CSR dado."""
        if factores_est and csr in factores_est:
            factors = factores_est[csr]
        else:
            factors = ESTACIONALIDAD_MENSUAL
        f_actual  = factors.get(hoy.month, 1.0) or 1.0
        f_forward = sum(factors.get(m, 1.0) for m in meses_venta) / len(meses_venta)
        return f_forward / f_actual if f_actual > 0 else 1.0

    csr_col = 'codigo_sinonimo' if 'codigo_sinonimo' in df.columns else None
    if csr_col:
        df['factor_est'] = df[csr_col].apply(_factor_ajuste_para)
    else:
        # sin CSR: usar factor global por mes actual → mes forward
        f_actual  = ESTACIONALIDAD_MENSUAL.get(hoy.month, 1.0) or 1.0
        f_forward = sum(ESTACIONALIDAD_MENSUAL.get(m, 1.0) for m in meses_venta) / len(meses_venta)
        df['factor_est'] = f_forward / f_actual if f_actual > 0 else 1.0

    # Velocidad proyectada (forward-looking) — usada en punto_reorden y cantidad
    df['vel_diaria_proj'] = df['vel_diaria'] * df['factor_est']
    # ──────────────────────────────────────────────────────────────────────────

    # Días de stock actuales (al ritmo ACTUAL, no proyectado)
    df['dias_stock'] = np.where(
        df['vel_diaria'] > 0,
        df['stock_actual'] / df['vel_diaria'],
        np.inf
    )

    df['lead_time'] = lead_time

    # Safety stock (Poisson) — usa vel proyectada
    df['safety_stock'] = np.ceil(
        z * np.sqrt(lead_time * df['vel_diaria_proj'].clip(lower=0.01))
    ).astype(int)

    # Punto de reorden — usa vel proyectada
    df['punto_reorden'] = np.ceil(
        df['vel_diaria_proj'] * lead_time + df['safety_stock']
    ).astype(int)

    # Necesita pedido hoy
    df['necesita_pedido'] = (
        (df['stock_actual'] <= df['punto_reorden']) &
        (df['vel_diaria'] > 0)
    )

    # Cantidad sugerida para cubrir el horizonte — usa vel proyectada
    objetivo = df['vel_diaria_proj'] * horizonte_dias + df['safety_stock']
    df['cantidad_sugerida'] = np.maximum(
        0, np.ceil(objetivo - df['stock_actual'])
    ).astype(int)

    # Urgencia semáforo (basada en días stock al ritmo actual)
    def _urgencia(row):
        if row['vel_diaria'] <= 0:
            return 'SIN_DEMANDA'
        if row['dias_stock'] < row['lead_time']:
            return 'ROJO'       # Quiebre antes de recibir — pedir URGENTE
        if row['dias_stock'] < row['lead_time'] * 2:
            return 'AMARILLO'   # Ventana estrecha — pedir YA
        return 'VERDE'

    df['urgencia'] = df.apply(_urgencia, axis=1)

    # Días hasta stockout (cap en 999 para visualización)
    df['dias_hasta_stockout'] = (
        df['dias_stock'].clip(upper=999).round(0).astype(int)
    )

    return df


@st.cache_data(ttl=1800)  # 30 min — stock cambia más seguido que vel_real
def cargar_stock_proveedor(proveedor_id: int) -> pd.DataFrame:
    """
    Carga stock actual + velocidad real para todos los artículos de un proveedor.

    Joins:
      - msgestionC.dbo.articulo (estado='V', proveedor=X)
      - msgestionC.dbo.stock    (suma depósitos principales)
      - omicronvt.dbo.vel_real_articulo (por código sinónimo 10 dígitos)

    Returns: DataFrame con columnas:
        codigo, codigo_sinonimo, descripcion, precio_venta,
        stock_actual, vel_real, vel_real_con_perdidas, pct_quiebre, meses_quebrado
    """
    sql = f"""
    SELECT
        a.codigo,
        RTRIM(ISNULL(a.codigo_sinonimo, ''))   AS codigo_sinonimo,
        RTRIM(ISNULL(a.descripcion_1, ''))     AS descripcion,
        ISNULL(a.precio_fabrica, 0)            AS precio_venta,
        a.subrubro,
        ISNULL(SUM(s.stock_actual), 0)         AS stock_actual,
        ISNULL(vr.vel_real, 0)                 AS vel_real,
        ISNULL(vr.vel_real, 0)                 AS vel_real_con_perdidas,
        ISNULL(1.0 - (CAST(vr.meses_con_stock AS FLOAT)
            / NULLIF(vr.meses_con_stock + vr.meses_quebrado, 0)), 0) AS pct_quiebre,
        ISNULL(vr.meses_quebrado, 0)           AS meses_quebrado
    FROM msgestionC.dbo.articulo a
    LEFT JOIN msgestionC.dbo.stock s
        ON s.articulo = a.codigo
        AND s.deposito IN {DEPOS_SQL}
    LEFT JOIN omicronvt.dbo.vel_real_articulo vr
        ON vr.codigo = RTRIM(a.codigo_sinonimo)
    WHERE a.proveedor = {proveedor_id}
      AND a.estado = 'V'
      AND ISNULL(a.codigo_sinonimo, '') != ''
    GROUP BY
        a.codigo, a.codigo_sinonimo, a.descripcion_1, a.precio_fabrica, a.subrubro,
        vr.vel_real, vr.meses_con_stock, vr.meses_quebrado
    HAVING ISNULL(SUM(s.stock_actual), 0) > 0 OR ISNULL(vr.vel_real, 0) > 0
    """
    return query_df(sql)


# ============================================================================
# CLASIFICACIÓN ABC-XYZ
# ============================================================================

@st.cache_data(ttl=3600)
def clasificar_abc_xyz():
    """
    Clasifica todos los productos activos en ABC (contribución revenue) x XYZ (predictibilidad).
    Returns: DataFrame with columns [csr, descripcion, abc, xyz, abc_xyz, revenue_12m, meses_con_venta]
    """
    sql = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               MIN(RTRIM(a.descripcion_1)) AS descripcion,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad * v.precio
                        WHEN v.operacion='-' THEN -v.cantidad * v.precio ELSE 0 END) AS revenue_12m,
               COUNT(DISTINCT MONTH(v.fecha)) AS meses_con_venta
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND v.fecha >= DATEADD(year, -1, GETDATE())
          AND a.estado = 'V'
          AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
          AND LEN(a.codigo_sinonimo) >= 10
        GROUP BY LEFT(a.codigo_sinonimo, 10)
        HAVING SUM(CASE WHEN v.operacion='+' THEN v.cantidad * v.precio
                       WHEN v.operacion='-' THEN -v.cantidad * v.precio ELSE 0 END) > 0
    """
    df = query_df(sql)
    if df.empty:
        return df

    # ABC: cumulative revenue share
    df = df.sort_values('revenue_12m', ascending=False)
    df['revenue_cum_pct'] = df['revenue_12m'].cumsum() / df['revenue_12m'].sum()
    df['abc'] = pd.cut(df['revenue_cum_pct'], bins=[0, 0.8, 0.95, 1.0], labels=['A', 'B', 'C'])

    # XYZ: meses_con_venta como proxy de regularidad
    # CV proxy: sells every month = X, 6-11 months = Y, <6 = Z
    df['xyz'] = df['meses_con_venta'].apply(
        lambda m: 'X' if m >= 10 else ('Y' if m >= 6 else 'Z')
    )

    df['abc_xyz'] = df['abc'].astype(str) + df['xyz'].astype(str)

    return df[['csr', 'descripcion', 'abc', 'xyz', 'abc_xyz', 'revenue_12m', 'meses_con_venta']]


def unificar_proveedores(proveedores_list):
    """
    Given a list of proveedor numbers that supply the same product family,
    returns a merged view of their articles grouped by LEFT(codigo_sinonimo, 10).
    Used for products like Go Dance where Timmis (11) and Zotz (457) supply the same shoes.

    Returns: dict mapping CSR -> list of proveedor numbers
    """
    filtro_prov = ",".join(str(p) for p in proveedores_list)
    sql = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               a.proveedor,
               COUNT(DISTINCT a.codigo) as skus
        FROM msgestion01art.dbo.articulo a
        WHERE a.proveedor IN ({filtro_prov})
          AND a.estado = 'V'
          AND LEN(a.codigo_sinonimo) >= 10
        GROUP BY LEFT(a.codigo_sinonimo, 10), a.proveedor
    """
    df = query_df(sql)
    result = {}
    for _, r in df.iterrows():
        csr = r['csr'].strip()
        if csr not in result:
            result[csr] = []
        result[csr].append(int(r['proveedor']))
    return result


# ============================================================================
# VEL_REAL DESDE TABLA MATERIALIZADA (omicronvt)
# ============================================================================

@st.cache_data(ttl=7200)
def obtener_vel_real_tabla(codigos_csr):
    """
    Obtiene vel_real pre-calculada de omicronvt.dbo.vel_real_articulo.
    Agrega por CSR (LEFT 10) sumando vel_real de todos los talles.
    Retorna dict {csr: {vel_real, vel_aparente, pct_quiebre, meses_quebrado}}.
    """
    if not codigos_csr:
        return {}

    filtro = ",".join(f"'{c}'" for c in codigos_csr)
    sql = f"""
        SELECT LEFT(codigo, 10) AS csr,
               SUM(vel_real) AS vel_real,
               SUM(vel_aparente) AS vel_aparente,
               AVG(factor_quiebre) AS factor_quiebre,
               MAX(meses_quebrado) AS meses_quebrado,
               MAX(meses_con_stock) + MAX(meses_quebrado) AS meses_total
        FROM omicronvt.dbo.vel_real_articulo
        WHERE LEFT(codigo, 10) IN ({filtro})
        GROUP BY LEFT(codigo, 10)
    """
    df = query_df(sql)
    if df.empty:
        return {}

    resultados = {}
    for _, r in df.iterrows():
        csr = r['csr'].strip()
        meses_total = max(int(r['meses_total'] or 12), 1)
        meses_q = int(r['meses_quebrado'] or 0)
        pct_q = meses_q / meses_total
        vel_raw = float(r['vel_real'] or 0)
        vel_ap = float(r['vel_aparente'] or 0)

        # Quiebre 100%: fallback vel_aparente × 1.15
        if vel_raw == 0 and vel_ap > 0 and pct_q > 0.75:
            vel_raw = vel_ap * 1.15

        # Factor corrección por disponibilidad
        if pct_q > 0.5:
            factor_disp = 1.20
        elif pct_q > 0.3:
            factor_disp = 1.10
        else:
            factor_disp = 1.0

        resultados[csr] = {
            'vel_real': round(vel_raw * factor_disp, 2),
            'vel_aparente': round(vel_ap, 2),
            'pct_quiebre': round(pct_q * 100, 1),
            'meses_quebrado': meses_q,
            'factor_disp': factor_disp,
        }
    return resultados


# ============================================================================
# ESTACIONALIDAD
# ============================================================================

def factor_estacional_batch(codigos_sinonimo, anios=3):
    """Calcula factores estacionales en batch. Retorna dict {cs: {mes: factor}}."""
    if not codigos_sinonimo:
        return {}
    # Delegate to cached version with hashable tuple key
    return _factor_estacional_batch_cached(tuple(sorted(set(codigos_sinonimo))), anios)


@st.cache_data(ttl=3600)
def _factor_estacional_batch_cached(codigos_sinonimo, anios=3):
    """Cached implementation of factor_estacional_batch."""

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

        # Fallback: si los factores son planos, usar estacionalidad del subrubro
        factors = resultados[cs]
        is_flat = all(0.8 <= v <= 1.2 for v in factors.values())
        if is_flat:
            sql_sub = f"SELECT TOP 1 subrubro FROM msgestion01art.dbo.articulo WHERE RTRIM(LEFT(codigo_sinonimo, 10)) = '{cs}' AND estado = 'V'"
            df_sub = query_df(sql_sub)
            if not df_sub.empty:
                sub_cod = int(df_sub.iloc[0]['subrubro'])
                sub_factors = factor_estacional_subrubro(sub_cod)
                # Solo usar factores subrubro si muestran estacionalidad real
                if not all(0.8 <= v <= 1.2 for v in sub_factors.values()):
                    resultados[cs] = sub_factors

    return resultados


@st.cache_data(ttl=3600)
def factor_estacional_subrubro(subrubro_cod, anios=3):
    """Calcula factores estacionales a nivel subrubro (todas las marcas/proveedores).
    Usado como fallback cuando un producto individual no tiene suficiente historia."""
    desde = (date.today() - relativedelta(years=anios)).replace(month=1, day=1)
    sql = f"""
        SELECT MONTH(v.fecha) AS mes,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad ELSE 0 END) AS cant
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.subrubro = {subrubro_cod}
          AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
          AND v.fecha >= '{desde}'
        GROUP BY MONTH(v.fecha)
    """
    df = query_df(sql)
    if df.empty:
        return {m: 1.0 for m in range(1, 13)}

    ventas_mes = {}
    for _, r in df.iterrows():
        ventas_mes[int(r['mes'])] = float(r['cant'] or 0)

    media = sum(ventas_mes.values()) / max(len(ventas_mes), 1)
    if media <= 0:
        return {m: 1.0 for m in range(1, 13)}

    return {m: round(ventas_mes.get(m, media) / media, 3) for m in range(1, 13)}


# ============================================================================
# ANOMALÍAS DE STOCK (remitos eliminados, errores auditoría)
# ============================================================================

@st.cache_data(ttl=7200)
def detectar_anomalias_stock(codigos_sinonimo):
    """
    Detecta anomalías de stock por artículo: remitos eliminados, stock negativo.
    Retorna dict {csr: {ok: bool, nivel: 'OK'|'REVISAR'|'IRREAL', anomalias: [str]}}
    """
    if not codigos_sinonimo:
        return {}

    desde = (date.today() - relativedelta(months=12)).replace(day=1)
    filtro = ",".join(f"'{c}'" for c in codigos_sinonimo)

    # Entradas (remitos código 7) y salidas (código 95 POS) por depósito
    sql_mov = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               v.deposito,
               SUM(CASE WHEN v.codigo = 7 AND v.operacion = '+' THEN v.cantidad ELSE 0 END) AS entradas_remito,
               SUM(CASE WHEN v.codigo = 95 AND v.operacion = '-' THEN v.cantidad ELSE 0 END) AS salidas_pos
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo IN (7, 95)
          AND LEFT(a.codigo_sinonimo, 10) IN ({filtro})
          AND v.fecha >= '{desde}'
        GROUP BY LEFT(a.codigo_sinonimo, 10), v.deposito
    """

    # Stock actual por depósito
    sql_stk = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               s.deposito,
               SUM(s.stock_actual) AS stock_dep
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON s.articulo = a.codigo
        WHERE LEFT(a.codigo_sinonimo, 10) IN ({filtro})
          AND s.deposito IN {DEPOS_SQL}
        GROUP BY LEFT(a.codigo_sinonimo, 10), s.deposito
    """

    df_mov = query_df(sql_mov)
    df_stk = query_df(sql_stk)

    resultados = {}
    for csr in codigos_sinonimo:
        anomalias = []

        # Check remito eliminado: salidas > entradas en algún depósito
        if not df_mov.empty:
            df_c = df_mov[df_mov['csr'].str.strip() == csr]
            for _, r in df_c.iterrows():
                if r['salidas_pos'] > r['entradas_remito'] and r['entradas_remito'] > 0:
                    anomalias.append(f"REMITO_ELIMINADO dep={int(r['deposito'])}")

        # Check stock negativo en depósito principal
        if not df_stk.empty:
            df_s = df_stk[(df_stk['csr'].str.strip() == csr) & (df_stk['deposito'] == 1)]
            for _, r in df_s.iterrows():
                if r['stock_dep'] < -5:
                    anomalias.append(f"ERROR_AUDITORIA dep=1 stk={int(r['stock_dep'])}")

        if not anomalias:
            resultados[csr] = {'ok': True, 'nivel': 'OK', 'anomalias': []}
        elif any('ERROR_AUDITORIA' in a for a in anomalias):
            resultados[csr] = {'ok': False, 'nivel': 'IRREAL', 'anomalias': anomalias}
        else:
            resultados[csr] = {'ok': False, 'nivel': 'REVISAR', 'anomalias': anomalias}

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
    """Conexión directa al 112 (réplica) para consultas de lectura."""
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


# omicronvt = analítica en 111, NO réplica (112 la sobreescribe cada noche
# perdiendo los INSERTs en vel_real_articulo y otras tablas propias)
def _conn_111(base):
    """Conexión directa al 111 (producción) para bases analíticas como omicronvt."""
    old_val = os.environ.get('OPENSSL_CONF')
    if os.path.exists(OPENSSL_LEGACY_CNF):
        os.environ['OPENSSL_CONF'] = OPENSSL_LEGACY_CNF
    try:
        conn_str = (
            f"DRIVER={{{_DRIVER_MAC}}};"
            f"SERVER=192.168.2.111;"
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
    df_top['fecha_quiebre'] = hoy + pd.to_timedelta(df_top['dias_stock'].clip(None, 999), unit='D')

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

@st.cache_data(ttl=7200)
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
# DISTRIBUCIÓN DE COLOR (Agente 3 — Reposición v3)
# ============================================================================

COLOR_KEYWORDS = {
    'NEGRO': ['NEGRO', 'BLACK', 'PRETO', 'CHUMBO'],
    'GRIS': ['GRIS', 'GREY', 'PLOMO', 'STEEL', 'CINZA'],
    'AZUL': ['AZUL', 'BLUE', 'MARINO', 'MARINHO', 'PETROLEO'],
    'BLANCO': ['BLANCO', 'WHITE', 'BRANCO'],
    'ROSA': ['ROSA', 'PINK', 'FUCSIA'],
    'BEIGE': ['BEIGE', 'ARENA', 'ARENITO', 'ALGODAO', 'MARFIL'],
    'ROJO': ['ROJO', 'RED', 'BORDO', 'VERMELHO'],
    'VERDE': ['VERDE', 'GREEN'],
}


def _clasificar_color(descripcion: str) -> str:
    """Clasifica un color desde descripcion_1 usando keyword matching."""
    desc_upper = (descripcion or '').upper()
    for color, keywords in COLOR_KEYWORDS.items():
        for kw in keywords:
            if kw in desc_upper:
                return color
    return 'OTRO'


@st.cache_data(ttl=3600)
def distribucion_color(proveedor_num: int, rubro: int, mes_inicio: int, mes_fin: int) -> list[dict]:
    """
    Peso porcentual de ventas por color para un proveedor x género.

    Clasifica colores desde descripcion_1 del artículo usando keyword matching
    en Python (no SQL CASE).

    Args:
        proveedor_num: número de proveedor en msgestion01art.dbo.articulo
        rubro: código de rubro (1=DAMAS, 3=HOMBRES, etc.)
        mes_inicio: mes inicio período (ej: 3 = marzo)
        mes_fin: mes fin período (ej: 6 = junio)

    Returns:
        Lista de dicts ordenada por pares desc:
        [{'color': 'NEGRO', 'pares': 144, 'pct': 0.56}, ...]
    """
    # Período de referencia = mismo rango del año anterior
    hoy = date.today()
    anio_ref = hoy.year - 1
    fecha_inicio = f'{anio_ref}-{mes_inicio:02d}-01'
    if mes_fin == 12:
        fecha_fin = f'{anio_ref + 1}-01-01'
    else:
        fecha_fin = f'{anio_ref}-{mes_fin + 1:02d}-01'

    sql = f"""
        SELECT a.descripcion_1,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad
                        ELSE 0 END) AS pares
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.proveedor = {int(proveedor_num)}
          AND a.rubro = {int(rubro)}
          AND v.fecha >= '{fecha_inicio}' AND v.fecha < '{fecha_fin}'
        GROUP BY a.descripcion_1
    """
    df = query_df(sql)
    if df.empty:
        return []

    # Clasificar color en Python
    df['color'] = df['descripcion_1'].apply(_clasificar_color)
    df['pares'] = pd.to_numeric(df['pares'], errors='coerce').fillna(0).astype(int)

    # Agrupar por color
    agrupado = df.groupby('color')['pares'].sum().reset_index()
    total = agrupado['pares'].sum()
    if total <= 0:
        return []

    agrupado['pct'] = (agrupado['pares'] / total).round(4)
    agrupado = agrupado.sort_values('pares', ascending=False)

    return agrupado.to_dict('records')


# ============================================================================
# ANÁLISIS GLOBAL: carga todos los productos activos con stock o ventas
# ============================================================================

@st.cache_data(ttl=7200)
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


@st.cache_data(ttl=7200)
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
               MAX(a.rubro) AS rubro,
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


@st.cache_data(ttl=7200)
def cargar_productos_por_proveedor(proveedor_num):
    """Carga productos de UN proveedor."""
    desde = (date.today() - relativedelta(months=12)).replace(day=1)
    sql = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               MAX(a.descripcion_1) AS descripcion,
               MAX(a.marca) AS marca,
               MAX(a.proveedor) AS proveedor,
               MAX(a.rubro) AS rubro,
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


@st.cache_data(ttl=7200)
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


@st.cache_data(ttl=7200)
def cargar_proveedores_dict():
    """Dict de proveedores: {numero: denominacion}."""
    sql = "SELECT numero, RTRIM(ISNULL(denominacion,'')) AS nombre FROM msgestionC.dbo.proveedores WHERE motivo_baja='A'"
    df = query_df(sql)
    return {int(r['numero']): (r['nombre'] or '').strip() for _, r in df.iterrows()} if not df.empty else {}


# ============================================================================
# PRESUPUESTO EN PARES (Agente 1)
# ============================================================================

@st.cache_data(ttl=3600)
def presupuesto_pares(proveedor_num: int, mes_inicio: int, mes_fin: int) -> dict:
    """
    Presupuesto = pares vendidos del mismo proveedor en el mismo período del año anterior.

    Args:
        proveedor_num: número de proveedor en msgestion01.dbo.proveedores
        mes_inicio: mes inicio período destino (ej: 3 = marzo)
        mes_fin: mes fin período destino (ej: 6 = junio)

    Returns:
        {
            'total_pares': int,
            'por_mes': {3: 165, 4: 92, 5: 114, 6: 104},
            'articulos_distintos': int,
            'periodo_ref': '2025-03 a 2025-06'
        }
    """
    hoy = date.today()
    anio_ref = hoy.year - 1

    # Calcular fechas del período de referencia (mismo período, año anterior)
    if mes_inicio <= mes_fin:
        # Período normal (ej: marzo a junio)
        fecha_inicio = date(anio_ref, mes_inicio, 1)
        fecha_fin_dt = date(anio_ref, mes_fin, 1) + relativedelta(months=1)
    else:
        # Período cruzando año (ej: octubre a febrero)
        fecha_inicio = date(anio_ref - 1, mes_inicio, 1)
        fecha_fin_dt = date(anio_ref, mes_fin, 1) + relativedelta(months=1)

    periodo_ref = f"{fecha_inicio.strftime('%Y-%m')} a {(fecha_fin_dt - timedelta(days=1)).strftime('%Y-%m')}"

    sql = f"""
        SELECT MONTH(v.fecha) AS mes,
               SUM(v.cantidad) AS pares,
               COUNT(DISTINCT v.articulo) AS arts
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.proveedor = {proveedor_num}
          AND v.fecha >= '{fecha_inicio.strftime('%Y%m%d')}'
          AND v.fecha < '{fecha_fin_dt.strftime('%Y%m%d')}'
        GROUP BY MONTH(v.fecha)
    """
    df = query_df(sql)

    if df.empty:
        return {
            'total_pares': 0,
            'total_pares_ajustado': 0,
            'factor_ajuste': 1.0,
            'por_mes': {},
            'por_mes_ajustado': {},
            'articulos_distintos': 0,
            'periodo_ref': periodo_ref,
        }

    por_mes = {int(r['mes']): int(r['pares']) for _, r in df.iterrows()}
    total_pares = int(df['pares'].sum())
    articulos_distintos = int(df['arts'].sum())

    # arts por mes puede tener duplicados entre meses, obtener el global
    sql_arts = f"""
        SELECT COUNT(DISTINCT v.articulo) AS arts_total
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.proveedor = {proveedor_num}
          AND v.fecha >= '{fecha_inicio.strftime('%Y%m%d')}'
          AND v.fecha < '{fecha_fin_dt.strftime('%Y%m%d')}'
    """
    df_arts = query_df(sql_arts)
    if not df_arts.empty and 'arts_total' in df_arts.columns:
        articulos_distintos = int(df_arts.iloc[0]['arts_total'])

    # Ajuste estacional: escalar pares por ratio factor_destino / factor_compra
    # Si compramos en marzo (factor 0.74) para vender en junio (factor 1.05),
    # el ajuste es 1.05/0.74 = 1.42x → necesitamos comprar más de lo que
    # el ritmo actual de ventas sugiere.
    factor_compra = ESTACIONALIDAD_MENSUAL.get(hoy.month, 1.0)
    por_mes_ajustado = {}
    for mes, pares in por_mes.items():
        factor_destino = ESTACIONALIDAD_MENSUAL.get(mes, 1.0)
        ratio = factor_destino / factor_compra if factor_compra > 0 else 1.0
        por_mes_ajustado[mes] = int(round(pares * ratio))

    total_pares_ajustado = sum(por_mes_ajustado.values())
    factor_ajuste = total_pares_ajustado / total_pares if total_pares > 0 else 1.0

    return {
        'total_pares': total_pares,
        'total_pares_ajustado': total_pares_ajustado,
        'factor_ajuste': factor_ajuste,
        'por_mes': por_mes,
        'por_mes_ajustado': por_mes_ajustado,
        'articulos_distintos': articulos_distintos,
        'periodo_ref': periodo_ref,
    }


# ============================================================================
# DISTRIBUCIÓN POR GÉNERO (Agente 2)
# ============================================================================

@st.cache_data(ttl=3600)
def distribucion_genero(proveedor_num: int, mes_inicio: int, mes_fin: int) -> dict:
    """
    Peso porcentual de ventas por género (rubro) para un proveedor,
    basado en el mismo período del año anterior.

    Args:
        proveedor_num: número de proveedor en tabla proveedores
        mes_inicio: mes inicio período destino (ej: 3 = marzo)
        mes_fin: mes fin período destino (ej: 6 = junio)

    Returns:
        {
            1: {'nombre': 'DAMAS', 'pares': 209, 'pct': 0.44},
            3: {'nombre': 'HOMBRES', 'pares': 256, 'pct': 0.54},
            4: {'nombre': 'NIÑOS', 'pares': 10, 'pct': 0.02}
        }
    """
    hoy = date.today()
    anio_ref = hoy.year - 1

    # Calcular fechas del período de referencia (mismo período, año anterior)
    if mes_inicio <= mes_fin:
        fecha_inicio = date(anio_ref, mes_inicio, 1)
        fecha_fin_dt = date(anio_ref, mes_fin, 1) + relativedelta(months=1)
    else:
        # Período cruzando año (ej: octubre a febrero)
        fecha_inicio = date(anio_ref - 1, mes_inicio, 1)
        fecha_fin_dt = date(anio_ref, mes_fin, 1) + relativedelta(months=1)

    sql = f"""
        SELECT a.rubro, SUM(v.cantidad) AS pares
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.proveedor = {proveedor_num}
          AND v.fecha >= '{fecha_inicio.strftime('%Y%m%d')}'
          AND v.fecha < '{fecha_fin_dt.strftime('%Y%m%d')}'
        GROUP BY a.rubro
    """
    df = query_df(sql)
    if df.empty:
        return {}

    total = int(df['pares'].sum())
    if total == 0:
        return {}

    result = {}
    for _, row in df.iterrows():
        rubro = int(row['rubro'])
        pares = int(row['pares'])
        result[rubro] = {
            'nombre': RUBRO_GENERO.get(rubro, f'RUBRO_{rubro}'),
            'pares': pares,
            'pct': round(pares / total, 4),
        }
    return result


# ============================================================================
# PRECIO TECHO (Agente 4 — percentiles precio_fabrica artículos vendidos)
# ============================================================================

@st.cache_data(ttl=3600)
def precio_techo(proveedor_num: int, rubro: int, percentil: int = 90) -> dict:
    """
    Calcula el percentil del precio_fabrica de artículos VENDIDOS (no de catálogo).

    Solo incluye artículos con al menos 1 venta en los últimos 12 meses.
    No incluye artículos muertos del catálogo.

    Args:
        proveedor_num: número de proveedor en msgestion01art.dbo.articulo
        rubro: rubro (1=DAMAS, 3=HOMBRES, 4=NIÑOS, etc.)
        percentil: percentil principal a calcular (default 90)

    Returns:
        {
            'p50': 40540.0,
            'p75': 43243.0,
            'p90': 48648.0,
            'max': 108000.0,
            'articulos_analizados': 156
        }
    """
    desde = (date.today() - relativedelta(months=12)).replace(day=1)

    # Traer precio_fabrica de artículos que tuvieron al menos 1 venta
    # en los últimos 12 meses para este proveedor x rubro
    sql = f"""
        SELECT DISTINCT a.codigo, a.precio_fabrica
        FROM msgestion01art.dbo.articulo a
        JOIN msgestionC.dbo.ventas1 v ON v.articulo = a.codigo
        WHERE a.proveedor = {int(proveedor_num)}
          AND a.rubro = {int(rubro)}
          AND v.codigo NOT IN {EXCL_VENTAS}
          AND v.fecha >= '{desde}'
          AND a.precio_fabrica > 0
    """
    df = query_df(sql)

    if df.empty:
        return {
            'p50': 0.0,
            'p75': 0.0,
            'p90': 0.0,
            'max': 0.0,
            'articulos_analizados': 0,
        }

    precios = df['precio_fabrica'].astype(float).values

    return {
        'p50': round(float(np.percentile(precios, 50)), 2),
        'p75': round(float(np.percentile(precios, 75)), 2),
        'p90': round(float(np.percentile(precios, percentil)), 2),
        'max': round(float(np.max(precios)), 2),
        'articulos_analizados': len(precios),
    }


# ============================================================================
# CURVA DE TALLES REAL (Agente 5)
# ============================================================================

@st.cache_data(ttl=3600)
def curva_talles_real(proveedor_num: int, rubro: int, meses: int = 12) -> dict:
    """
    Curva de demanda real por talle individual para un proveedor x genero,
    corregida por quiebre de stock a nivel articulo (cada articulo = 1 talle).

    El talle se obtiene de descripcion_5 en la tabla articulo.

    Args:
        proveedor_num: numero de proveedor
        rubro: codigo de rubro (1=DAMAS, 3=HOMBRES, etc.)
        meses: meses de historia a analizar (default 12)

    Returns:
        {
            'curva': {'37': {'pares': 57, 'pct': 0.12}, ...},
            'total_pares': 475,
            'talle_pico': '38'
        }

    NOTA sobre correccion por quiebre:
        Se reconstruye stock mes a mes hacia atras POR ARTICULO (cada articulo
        representa un talle individual). Si un articulo tuvo stock_inicio <= 0
        en un mes, ese mes se marca como quebrado y sus ventas NO se cuentan
        para la velocidad. Luego se agrupa por talle (descripcion_5) sumando
        las velocidades reales de todos los articulos de ese talle.
        Esto corrige la subestimacion que ocurre cuando un talle estuvo sin
        stock durante varios meses (ej: talle 46 quebrado 11 de 12 meses).
    """
    hoy = date.today()
    desde = (hoy - relativedelta(months=meses)).replace(day=1)

    # 1. Obtener articulos del proveedor+rubro con su talle (descripcion_5)
    sql_arts = f"""
        SELECT a.codigo,
               RTRIM(ISNULL(a.descripcion_5, '')) AS talle
        FROM msgestion01art.dbo.articulo a
        WHERE a.proveedor = {int(proveedor_num)}
          AND a.rubro = {int(rubro)}
          AND a.estado = 'V'
          AND RTRIM(ISNULL(a.descripcion_5, '')) <> ''
    """
    df_arts = query_df(sql_arts)
    if df_arts.empty:
        return {'curva': {}, 'total_pares': 0, 'talle_pico': ''}

    df_arts['talle'] = df_arts['talle'].str.strip()
    df_arts = df_arts[df_arts['talle'] != '']
    if df_arts.empty:
        return {'curva': {}, 'total_pares': 0, 'talle_pico': ''}

    codigos = df_arts['codigo'].tolist()
    talle_por_codigo = dict(zip(df_arts['codigo'], df_arts['talle']))

    # Construir filtro IN
    filtro = ",".join(f"'{c}'" for c in codigos)

    # 2. Stock actual por articulo
    sql_stock = f"""
        SELECT s.articulo,
               SUM(s.stock_actual) AS stock
        FROM msgestionC.dbo.stock s
        WHERE s.articulo IN ({filtro})
          AND s.deposito IN {DEPOS_SQL}
        GROUP BY s.articulo
    """
    df_stock = query_df(sql_stock)
    stock_por_art = {}
    for _, r in df_stock.iterrows():
        art = r['articulo'].strip() if isinstance(r['articulo'], str) else r['articulo']
        stock_por_art[art] = float(r['stock'])

    # 3. Ventas mensuales por articulo
    sql_ventas = f"""
        SELECT v.articulo,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes
        FROM msgestionC.dbo.ventas1 v
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND v.articulo IN ({filtro})
          AND v.fecha >= '{desde}'
        GROUP BY v.articulo, YEAR(v.fecha), MONTH(v.fecha)
    """
    df_ventas = query_df(sql_ventas)

    ventas_by_art = {}
    for _, r in df_ventas.iterrows():
        art = r['articulo'].strip() if isinstance(r['articulo'], str) else r['articulo']
        if art not in ventas_by_art:
            ventas_by_art[art] = {}
        ventas_by_art[art][(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    # 4. Compras mensuales por articulo
    sql_compras = f"""
        SELECT rc.articulo,
               SUM(rc.cantidad) AS cant,
               YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes
        FROM msgestionC.dbo.compras1 rc
        WHERE rc.operacion = '+'
          AND rc.articulo IN ({filtro})
          AND rc.fecha >= '{desde}'
        GROUP BY rc.articulo, YEAR(rc.fecha), MONTH(rc.fecha)
    """
    df_compras = query_df(sql_compras)

    compras_by_art = {}
    for _, r in df_compras.iterrows():
        art = r['articulo'].strip() if isinstance(r['articulo'], str) else r['articulo']
        if art not in compras_by_art:
            compras_by_art[art] = {}
        compras_by_art[art][(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    # 5. Lista de meses hacia atras
    meses_lista = []
    cursor_dt = hoy.replace(day=1)
    for _ in range(meses):
        meses_lista.append((cursor_dt.year, cursor_dt.month))
        cursor_dt -= relativedelta(months=1)

    # 6. Reconstruir quiebre por articulo y acumular vel_real por talle
    vel_real_por_talle = {}  # talle -> sum of vel_real across articles

    for cod in codigos:
        talle = talle_por_codigo.get(cod, '')
        if not talle:
            continue

        stock_actual = stock_por_art.get(cod, 0)
        v_dict = ventas_by_art.get(cod, {})
        c_dict = compras_by_art.get(cod, {})

        stock_fin = stock_actual
        meses_ok = 0
        ventas_ok = 0

        for anio, mes in meses_lista:
            v = v_dict.get((anio, mes), 0)
            c = c_dict.get((anio, mes), 0)
            stock_inicio = stock_fin + v - c

            if stock_inicio > 0:
                meses_ok += 1
                ventas_ok += v

            stock_fin = stock_inicio

        # Velocidad real mensual para este articulo
        if meses_ok > 0:
            vel_real_art = ventas_ok / meses_ok
        else:
            # 100% quebrado: fallback a velocidad aparente x 1.15
            ventas_total = sum(v_dict.values())
            vel_real_art = (ventas_total / max(meses, 1)) * 1.15 if ventas_total > 0 else 0

        if talle not in vel_real_por_talle:
            vel_real_por_talle[talle] = 0.0
        vel_real_por_talle[talle] += vel_real_art * meses  # pares estimados en el periodo

    # 7. Construir curva
    total_pares = sum(vel_real_por_talle.values())
    if total_pares <= 0:
        return {'curva': {}, 'total_pares': 0, 'talle_pico': ''}

    curva = {}
    talle_pico = ''
    max_pares = 0
    for talle in sorted(vel_real_por_talle.keys(), key=lambda t: (
        float(t) if t.replace('.', '', 1).replace(',', '', 1).isdigit() else float('inf'), t
    )):
        pares = vel_real_por_talle[talle]
        pct = pares / total_pares if total_pares > 0 else 0
        curva[talle] = {
            'pares': round(pares),
            'pct': round(pct, 4),
        }
        if pares > max_pares:
            max_pares = pares
            talle_pico = talle

    return {
        'curva': curva,
        'total_pares': round(total_pares),
        'talle_pico': talle_pico,
    }


# ============================================================================
# CURVA IDEAL DE STOCK POR TALLE (reusable)
# ============================================================================

@st.cache_data(ttl=3600)
def calcular_curva_ideal(csr_list, dias_cobertura=90, proveedores=None):
    """
    Calcula la curva ideal de stock por talle para un grupo de modelos (CSRs).

    Args:
        csr_list: list of LEFT(codigo_sinonimo, 10) values
        dias_cobertura: target days of stock coverage (default 90)
        proveedores: optional list of proveedor numbers to filter

    Returns: DataFrame with columns:
        talle, vtas_12m, vel_mes, stock, ideal, pedir, cob_dias, estado

    The function uses CTEs to avoid the stock multiplication bug.
    """
    if not csr_list:
        return pd.DataFrame()

    # Build CSR filter
    csr_filter = ",".join(f"'{str(c).strip()}'" for c in csr_list)

    # Optional proveedor filter
    prov_filter = ""
    if proveedores:
        prov_in = ",".join(str(int(p)) for p in proveedores)
        prov_filter = f"AND a.proveedor IN ({prov_in})"

    sql = f"""
        WITH vtas AS (
            SELECT CAST(RTRIM(a.descripcion_5) AS INT) AS talle,
                   SUM(CASE WHEN v.operacion = '+' THEN v.cantidad
                            WHEN v.operacion = '-' THEN -v.cantidad
                            ELSE 0 END) AS pares_12m
            FROM msgestionC.dbo.ventas1 v
            JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
            WHERE LEFT(a.codigo_sinonimo, 10) IN ({csr_filter})
              AND v.codigo NOT IN {EXCL_VENTAS}
              AND v.fecha >= DATEADD(year, -1, GETDATE())
              AND ISNUMERIC(RTRIM(a.descripcion_5)) = 1
              AND RTRIM(ISNULL(a.descripcion_5, '')) <> ''
              {prov_filter}
            GROUP BY CAST(RTRIM(a.descripcion_5) AS INT)
        ),
        stk AS (
            SELECT CAST(RTRIM(a.descripcion_5) AS INT) AS talle,
                   SUM(s.stock_actual) AS stock
            FROM msgestion01art.dbo.articulo a
            JOIN msgestionC.dbo.stock s ON s.articulo = a.codigo
            WHERE LEFT(a.codigo_sinonimo, 10) IN ({csr_filter})
              AND s.deposito IN {DEPOS_SQL}
              AND ISNUMERIC(RTRIM(a.descripcion_5)) = 1
              AND RTRIM(ISNULL(a.descripcion_5, '')) <> ''
              {prov_filter}
            GROUP BY CAST(RTRIM(a.descripcion_5) AS INT)
        )
        SELECT v.talle,
               v.pares_12m,
               ISNULL(s.stock, 0) AS stock
        FROM vtas v
        LEFT JOIN stk s ON s.talle = v.talle
        ORDER BY v.talle
    """
    df = query_df(sql)
    if df.empty:
        return pd.DataFrame()

    # Calculate derived columns
    df['vel_mes'] = df['pares_12m'] / 12.0
    df['ideal'] = (df['vel_mes'] * (dias_cobertura / 30.0)).round(0).astype(int)
    df['pedir'] = (df['ideal'] - df['stock']).clip(lower=0).astype(int)
    df['cob_dias'] = df.apply(
        lambda r: round(r['stock'] / (r['vel_mes'] / 30.0), 0) if r['vel_mes'] > 0 else 9999,
        axis=1
    ).astype(int)

    def _estado(cob):
        if cob == 0:
            return 'SIN STOCK'
        if cob < 30:
            return 'CRITICO'
        if cob < 60:
            return 'BAJO'
        if cob < 120:
            return 'MEDIO'
        return 'OK'

    df['estado'] = df['cob_dias'].apply(_estado)

    # Rename for clarity
    df = df.rename(columns={'pares_12m': 'vtas_12m'})
    return df[['talle', 'vtas_12m', 'vel_mes', 'stock', 'ideal', 'pedir', 'cob_dias', 'estado']]


def calcular_pedido_modelo(csr_list, dias_cobertura=90, proveedores=None):
    """
    Returns a pivot table: rows=modelo (CSR), columns=talle, values=pedir.
    Plus a summary row with totals.

    Args:
        csr_list: list of LEFT(codigo_sinonimo, 10) values
        dias_cobertura: target days of stock coverage (default 90)
        proveedores: optional list of proveedor numbers to filter

    Returns: DataFrame pivot with modelo rows, talle columns, pedir values.
             Last row is 'TOTAL'.
    """
    if not csr_list:
        return pd.DataFrame()

    # Build CSR filter
    csr_filter = ",".join(f"'{str(c).strip()}'" for c in csr_list)

    # Optional proveedor filter
    prov_filter = ""
    if proveedores:
        prov_in = ",".join(str(int(p)) for p in proveedores)
        prov_filter = f"AND a.proveedor IN ({prov_in})"

    sql = f"""
        WITH vtas AS (
            SELECT LEFT(a.codigo_sinonimo, 10) AS modelo,
                   CAST(RTRIM(a.descripcion_5) AS INT) AS talle,
                   SUM(CASE WHEN v.operacion = '+' THEN v.cantidad
                            WHEN v.operacion = '-' THEN -v.cantidad
                            ELSE 0 END) AS pares_12m
            FROM msgestionC.dbo.ventas1 v
            JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
            WHERE LEFT(a.codigo_sinonimo, 10) IN ({csr_filter})
              AND v.codigo NOT IN {EXCL_VENTAS}
              AND v.fecha >= DATEADD(year, -1, GETDATE())
              AND ISNUMERIC(RTRIM(a.descripcion_5)) = 1
              AND RTRIM(ISNULL(a.descripcion_5, '')) <> ''
              {prov_filter}
            GROUP BY LEFT(a.codigo_sinonimo, 10), CAST(RTRIM(a.descripcion_5) AS INT)
        ),
        stk AS (
            SELECT LEFT(a.codigo_sinonimo, 10) AS modelo,
                   CAST(RTRIM(a.descripcion_5) AS INT) AS talle,
                   SUM(s.stock_actual) AS stock
            FROM msgestion01art.dbo.articulo a
            JOIN msgestionC.dbo.stock s ON s.articulo = a.codigo
            WHERE LEFT(a.codigo_sinonimo, 10) IN ({csr_filter})
              AND s.deposito IN {DEPOS_SQL}
              AND ISNUMERIC(RTRIM(a.descripcion_5)) = 1
              AND RTRIM(ISNULL(a.descripcion_5, '')) <> ''
              {prov_filter}
            GROUP BY LEFT(a.codigo_sinonimo, 10), CAST(RTRIM(a.descripcion_5) AS INT)
        )
        SELECT v.modelo, v.talle, v.pares_12m, ISNULL(s.stock, 0) AS stock
        FROM vtas v
        LEFT JOIN stk s ON s.modelo = v.modelo AND s.talle = v.talle
        ORDER BY v.modelo, v.talle
    """
    df = query_df(sql)
    if df.empty:
        return pd.DataFrame()

    # Calculate pedir per modelo+talle
    df['vel_mes'] = df['pares_12m'] / 12.0
    df['ideal'] = (df['vel_mes'] * (dias_cobertura / 30.0)).round(0).astype(int)
    df['pedir'] = (df['ideal'] - df['stock']).clip(lower=0).astype(int)

    # Pivot: rows=modelo, columns=talle, values=pedir
    pivot = df.pivot_table(
        index='modelo', columns='talle', values='pedir',
        aggfunc='sum', fill_value=0
    )

    # Sort columns numerically
    pivot = pivot[sorted(pivot.columns)]

    # Add total row and column
    pivot.loc['TOTAL'] = pivot.sum()
    pivot['TOTAL'] = pivot.sum(axis=1)

    return pivot.astype(int)


# ============================================================================
# ESCASEZ CRONICA POR TALLE (Agente 6)
# ============================================================================

@st.cache_data(ttl=3600)
def talles_escasez_cronica(rubro: int, subrubro: int = None, umbral_quiebre: float = 0.7) -> list:
    """
    Detecta talles que historicamente siempre estan en falta.
    Un talle tiene escasez cronica si estuvo quebrado > umbral_quiebre % de los meses analizados.

    Reconstruye stock mes a mes hacia atras (misma logica que analizar_quiebre_batch)
    pero agrupando por talle (descripcion_5) en vez de por codigo_sinonimo.

    Args:
        rubro: codigo de rubro (1=DAMAS, 3=HOMBRES, 4=NINOS, etc.)
        subrubro: codigo de subrubro (opcional, si None analiza todo el rubro)
        umbral_quiebre: fraccion minima de meses quebrados para considerar escasez cronica (default 0.7)

    Returns: [
        {'talle': '46', 'meses_quebrado': 11, 'meses_total': 12, 'pct_quiebre': 0.92},
        {'talle': '47', 'meses_quebrado': 10, 'meses_total': 12, 'pct_quiebre': 0.83},
        {'talle': '48', 'meses_quebrado': 12, 'meses_total': 12, 'pct_quiebre': 1.00},
    ]
    """
    meses = MESES_HISTORIA
    hoy = date.today()
    desde = (hoy - relativedelta(months=meses)).replace(day=1)
    desde_str = desde.strftime('%Y%m%d')

    # Filtro subrubro opcional
    filtro_sub = f"AND a.subrubro = {subrubro}" if subrubro is not None else ""

    # 1. Obtener articulos del rubro (y opcionalmente subrubro) con su talle
    sql_arts = f"""
        SELECT a.codigo, RTRIM(ISNULL(a.descripcion_5, '')) AS talle
        FROM msgestion01art.dbo.articulo a
        WHERE a.rubro = {rubro}
          {filtro_sub}
          AND a.estado = 'A'
          AND RTRIM(ISNULL(a.descripcion_5, '')) <> ''
    """
    df_arts = query_df(sql_arts)
    if df_arts.empty:
        return []

    # Mapeo articulo -> talle
    art_talle = {}
    for _, r in df_arts.iterrows():
        cod = r['codigo']
        art_key = cod.strip() if isinstance(cod, str) else str(cod).strip()
        art_talle[art_key] = r['talle'].strip()

    talles_unicos = sorted(set(art_talle.values()))
    if not talles_unicos:
        return []

    # Procesar en chunks para no superar limite de SQL Server IN clause
    codigos_list = list(art_talle.keys())
    CHUNK_SIZE = 500
    stock_by_talle = {}
    ventas_by_talle = {}   # {talle: {(anio, mes): cant}}
    compras_by_talle = {}  # {talle: {(anio, mes): cant}}

    for i in range(0, len(codigos_list), CHUNK_SIZE):
        chunk = codigos_list[i:i + CHUNK_SIZE]
        filtro_arts = ",".join(f"'{c}'" for c in chunk)

        # 2. Stock actual por articulo -> sumar por talle
        sql_stock = f"""
            SELECT s.articulo, ISNULL(SUM(s.stock_actual), 0) AS stock
            FROM msgestionC.dbo.stock s
            WHERE s.articulo IN ({filtro_arts})
              AND s.deposito IN {DEPOS_SQL}
            GROUP BY s.articulo
        """
        df_stock = query_df(sql_stock)
        for _, r in df_stock.iterrows():
            art_key = r['articulo'].strip() if isinstance(r['articulo'], str) else str(r['articulo']).strip()
            talle = art_talle.get(art_key)
            if talle:
                stock_by_talle[talle] = stock_by_talle.get(talle, 0) + float(r['stock'])

        # 3. Ventas mensuales por articulo -> sumar por talle
        sql_ventas = f"""
            SELECT v.articulo,
                   SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                            WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
                   YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes
            FROM msgestionC.dbo.ventas1 v
            WHERE v.codigo NOT IN {EXCL_VENTAS}
              AND v.articulo IN ({filtro_arts})
              AND v.fecha >= '{desde_str}'
            GROUP BY v.articulo, YEAR(v.fecha), MONTH(v.fecha)
        """
        df_ventas = query_df(sql_ventas)
        for _, r in df_ventas.iterrows():
            art_key = r['articulo'].strip() if isinstance(r['articulo'], str) else str(r['articulo']).strip()
            talle = art_talle.get(art_key)
            if talle:
                if talle not in ventas_by_talle:
                    ventas_by_talle[talle] = {}
                key = (int(r['anio']), int(r['mes']))
                ventas_by_talle[talle][key] = ventas_by_talle[talle].get(key, 0) + float(r['cant'] or 0)

        # 4. Compras mensuales por articulo -> sumar por talle
        sql_compras = f"""
            SELECT rc.articulo,
                   SUM(rc.cantidad) AS cant,
                   YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes
            FROM msgestionC.dbo.compras1 rc
            WHERE rc.operacion = '+'
              AND rc.articulo IN ({filtro_arts})
              AND rc.fecha >= '{desde_str}'
            GROUP BY rc.articulo, YEAR(rc.fecha), MONTH(rc.fecha)
        """
        df_compras = query_df(sql_compras)
        for _, r in df_compras.iterrows():
            art_key = r['articulo'].strip() if isinstance(r['articulo'], str) else str(r['articulo']).strip()
            talle = art_talle.get(art_key)
            if talle:
                if talle not in compras_by_talle:
                    compras_by_talle[talle] = {}
                key = (int(r['anio']), int(r['mes']))
                compras_by_talle[talle][key] = compras_by_talle[talle].get(key, 0) + float(r['cant'] or 0)

    # 5. Lista de meses hacia atras (del mas reciente al mas antiguo)
    meses_lista = []
    cursor_dt = hoy.replace(day=1)
    for _ in range(meses):
        meses_lista.append((cursor_dt.year, cursor_dt.month))
        cursor_dt -= relativedelta(months=1)

    # 6. Reconstruir stock mes a mes hacia atras para cada talle
    resultados = []
    for talle in talles_unicos:
        stock_actual = stock_by_talle.get(talle, 0)
        v_dict = ventas_by_talle.get(talle, {})
        c_dict = compras_by_talle.get(talle, {})

        stock_fin = stock_actual
        meses_q = 0

        for anio, mes in meses_lista:
            v = v_dict.get((anio, mes), 0)
            c = c_dict.get((anio, mes), 0)
            # Reconstruir: stock_inicio = stock_fin + ventas - compras
            stock_inicio = stock_fin + v - c

            if stock_inicio <= 0:
                meses_q += 1

            stock_fin = stock_inicio

        pct_q = meses_q / max(meses, 1)

        # Solo incluir talles que superan el umbral de escasez cronica
        if pct_q >= umbral_quiebre:
            resultados.append({
                'talle': talle,
                'meses_quebrado': meses_q,
                'meses_total': meses,
                'pct_quiebre': round(pct_q, 2),
            })

    # Ordenar por pct_quiebre descendente, luego por talle
    resultados.sort(key=lambda x: (-x['pct_quiebre'], x['talle']))
    return resultados


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
                 cantidad_pedir, stock_disponible, dias_pago=30):
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

    # Recupero efectivo: descontar días de financiación del proveedor
    dias_recupero_efectivo = max(dias_recupero - dias_pago, 0) if dias_recupero < 999 else 999

    return {
        'dias_recupero': dias_recupero,
        'dias_recupero_efectivo': dias_recupero_efectivo,
        'dias_pago': dias_pago,
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

@st.cache_data(ttl=7200)
def cargar_subrubro_desc():
    """Carga descripciones de subrubro desde msgestion01."""
    sql = "SELECT codigo, RTRIM(descripcion) AS desc1 FROM msgestion01.dbo.subrubro"
    df = query_df(sql)
    return {int(r['codigo']): (r['desc1'] or '').strip() for _, r in df.iterrows()} if not df.empty else {}


RUBRO_GENERO = {1: 'DAMAS', 3: 'HOMBRES', 4: 'NIÑOS', 5: 'NIÑAS', 6: 'UNISEX'}


@st.cache_data(ttl=7200)
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


@st.cache_data(ttl=7200)
def calcular_alertas_talles(categorias_filtro=None, marca_id=None, proveedor_id=None):
    """
    Calcula talles críticos por categoría con quiebre por talle.
    OPTIMIZADO: si recibe categorias_filtro (lista de (rubro, subrubro)), solo consulta esas.
    Si recibe marca_id o proveedor_id, filtra artículos por marca/proveedor.
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
    # Filtro por categorías específicas (rubro, subrubro)
    if categorias_filtro:
        pares = [f"(a.rubro={r} AND a.subrubro={s})" for r, s in categorias_filtro]
        calzado_filter += " AND (" + " OR ".join(pares) + ")"
    # Filtro por marca
    if marca_id:
        calzado_filter += f" AND a.marca = {int(marca_id)}"
    # Filtro por proveedor
    if proveedor_id:
        calzado_filter += f" AND a.proveedor = {int(proveedor_id)}"

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


@st.cache_data(ttl=7200)
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

@st.cache_data(ttl=7200)
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

    # Cobertura con velocidad real (fix NaN/inf)
    df['vel_diaria'] = df['vel_real'] / 30
    cob_raw = df['stock'] / df['vel_diaria'].replace(0, np.nan)
    df['cob_dias'] = cob_raw.fillna(9999).clip(None, 9999).astype(int)
    # Escasez crónica: quebrado > 75% de los meses
    df['escasez_cronica'] = df['pct_quiebre'] >= 75

    def estado_talle(row):
        if row.get('escasez_cronica', False):
            return 'ESCASEZ'
        if row['cob_dias'] >= 9999:
            return 'SIN VENTA'
        if row['cob_dias'] < 30:
            return 'CRITICO'
        if row['cob_dias'] < 60:
            return 'BAJO'
        if row['cob_dias'] < 120:
            return 'MEDIO'
        return 'OK'

    df['urgencia'] = df.apply(estado_talle, axis=1)
    # Caso especial: tiene demanda pero 0 stock = CRITICO
    df.loc[(df['vtas_12m'] > 0) & (df['stock'] == 0) & (~df['escasez_cronica']), 'urgencia'] = 'CRITICO'
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

@st.cache_data(ttl=7200)
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
    df['vel_norm'] = df['vel_mensual'] / max(df['vel_mensual'].quantile(0.95), 1)
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


@st.cache_data(ttl=7200)
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
    merged['n_prods'] = merged['n_prods'].fillna(1).clip(1)
    merged['vel_por_prod'] = merged['vel_prom_cat'] / merged['n_prods']
    return {(int(r['rubro']), int(r['subrubro'])): round(float(r['vel_por_prod']), 2)
            for _, r in merged.iterrows()
            if pd.notna(r['vel_por_prod']) and pd.notna(r['rubro']) and pd.notna(r['subrubro'])}


# ============================================================================
# CURVA DE TALLE IDEAL (reverse-engineered from 3 years of sales)
# ============================================================================

@st.cache_data(ttl=7200)
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


@st.cache_data(ttl=7200)
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

@st.cache_data(ttl=7200)
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


@st.cache_data(ttl=7200)
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


@st.cache_data(ttl=7200)
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

@st.cache_data(ttl=7200)
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


@st.cache_data(ttl=7200)
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
# ANÁLISIS DE NICHO DE PRODUCTO
# ============================================================================

@st.cache_data(ttl=3600)
def analizar_nicho_producto(subrubros, color_keyword, rubros=(1, 5), anios_historia=4):
    """
    Analiza un nicho de producto (ej: comunión=guillermina/chata blanca niñas/damas)
    y retorna estacionalidad, curva de talles, proveedores, y mejor momento histórico.

    Args:
        subrubros: tuple de códigos subrubro (ej: (17, 18) para guillermina+chata)
        color_keyword: string para filtrar en descripcion_1 (ej: '%BLANC%')
        rubros: tuple de códigos rubro (ej: (1, 5) para damas+niñas)
        anios_historia: años hacia atrás para analizar

    Returns: dict with keys:
        - estacionalidad: {mes: {pares_promedio, factor}}
        - curva_talles: {talle: {pares_total, pct, stock_hoy, estado}}
        - proveedores: [{proveedor, nombre, pares_total, pares_temporada, pct_temporada}]
        - mejor_momento: {anio, mes_compra, pares_comprados, vtas_temporada_siguiente, ratio}
        - temporada: {meses_pico: list, pct_concentracion: float}
        - resumen: {demanda_anual, demanda_temporada, stock_total, cobertura_temporada_dias}
    """
    subrubros_sql = '(' + ','.join(str(int(s)) for s in subrubros) + ')'
    rubros_sql = '(' + ','.join(str(int(r)) for r in rubros) + ')'

    # ── 1. ESTACIONALIDAD ──
    sql_estac = f"""
        SELECT MONTH(v.fecha) AS mes,
               YEAR(v.fecha) AS anio,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad
                        ELSE 0 END) AS pares
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.subrubro IN {subrubros_sql}
          AND a.rubro IN {rubros_sql}
          AND a.descripcion_1 LIKE '{color_keyword}'
          AND v.fecha >= DATEADD(year, -{int(anios_historia)}, GETDATE())
        GROUP BY YEAR(v.fecha), MONTH(v.fecha)
    """
    df_estac = query_df(sql_estac)

    estacionalidad = {}
    if not df_estac.empty:
        df_estac['pares'] = pd.to_numeric(df_estac['pares'], errors='coerce').fillna(0)
        n_anios = df_estac['anio'].nunique()
        n_anios = max(n_anios, 1)
        por_mes = df_estac.groupby('mes')['pares'].sum().reindex(range(1, 13), fill_value=0)
        promedio_mensual = por_mes.values.mean()
        promedio_mensual = max(promedio_mensual, 0.001)  # avoid div/0
        for mes in range(1, 13):
            pares_total = por_mes.get(mes, 0)
            pares_prom = round(pares_total / n_anios, 1)
            factor = round(pares_total / promedio_mensual, 2)
            estacionalidad[mes] = {'pares_promedio': pares_prom, 'factor': factor}

    # ── 2. TEMPORADA (auto-detect picos) ──
    factor_umbral = 1.3
    meses_pico = [m for m, v in estacionalidad.items() if v['factor'] > factor_umbral]
    total_anual = sum(v['pares_promedio'] for v in estacionalidad.values())
    total_temporada = sum(estacionalidad[m]['pares_promedio'] for m in meses_pico) if meses_pico else 0
    pct_concentracion = round(total_temporada / max(total_anual, 0.001), 4)
    temporada = {'meses_pico': meses_pico, 'pct_concentracion': pct_concentracion}

    # ── 3. CURVA DE TALLES ──
    sql_talles = f"""
        SELECT CAST(a.descripcion_5 AS INT) AS talle,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad
                        ELSE 0 END) AS pares
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.subrubro IN {subrubros_sql}
          AND a.rubro IN {rubros_sql}
          AND a.descripcion_1 LIKE '{color_keyword}'
          AND ISNUMERIC(a.descripcion_5) = 1
          AND v.fecha >= DATEADD(year, -{int(anios_historia)}, GETDATE())
        GROUP BY CAST(a.descripcion_5 AS INT)
    """
    df_talles = query_df(sql_talles)

    # Stock actual por talle
    sql_stock_talle = f"""
        SELECT CAST(a.descripcion_5 AS INT) AS talle,
               ISNULL(SUM(s.stock_actual), 0) AS stock_hoy
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        WHERE a.subrubro IN {subrubros_sql}
          AND a.rubro IN {rubros_sql}
          AND a.descripcion_1 LIKE '{color_keyword}'
          AND ISNUMERIC(a.descripcion_5) = 1
          AND s.deposito IN {DEPOS_SQL}
        GROUP BY CAST(a.descripcion_5 AS INT)
    """
    df_stock_talle = query_df(sql_stock_talle)

    curva_talles = {}
    if not df_talles.empty:
        df_talles['pares'] = pd.to_numeric(df_talles['pares'], errors='coerce').fillna(0)
        df_talles['talle'] = pd.to_numeric(df_talles['talle'], errors='coerce')
        df_talles = df_talles.dropna(subset=['talle'])
        df_talles['talle'] = df_talles['talle'].astype(int)
        total_pares = df_talles['pares'].sum()
        total_pares = max(total_pares, 1)

        stock_map = {}
        if not df_stock_talle.empty:
            df_stock_talle['talle'] = pd.to_numeric(df_stock_talle['talle'], errors='coerce')
            df_stock_talle = df_stock_talle.dropna(subset=['talle'])
            df_stock_talle['talle'] = df_stock_talle['talle'].astype(int)
            stock_map = dict(zip(df_stock_talle['talle'], df_stock_talle['stock_hoy'].fillna(0)))

        # Velocidad diaria en temporada para clasificar estado
        vel_temporada_diaria = 0
        if meses_pico and total_anual > 0:
            dias_temporada = len(meses_pico) * 30
            vel_temporada_diaria = total_temporada / max(dias_temporada, 1)

        for _, row in df_talles.iterrows():
            t = int(row['talle'])
            pares = float(row['pares'])
            pct = round(pares / total_pares, 4)
            stk = float(stock_map.get(t, 0))
            # Estado basado en cobertura en temporada
            vel_talle_diaria = vel_temporada_diaria * pct
            if vel_talle_diaria > 0:
                cobertura_dias = stk / vel_talle_diaria
            else:
                cobertura_dias = 999
            if cobertura_dias < 30:
                estado = 'CRITICO'
            elif cobertura_dias < 60:
                estado = 'BAJO'
            else:
                estado = 'OK'
            curva_talles[t] = {
                'pares_total': round(pares),
                'pct': pct,
                'stock_hoy': round(stk),
                'estado': estado,
            }

    # ── 4. PROVEEDORES RANKING ──
    meses_pico_sql = '(' + ','.join(str(m) for m in meses_pico) + ')' if meses_pico else '(0)'
    sql_prov = f"""
        SELECT a.proveedor,
               p.denominacion AS nombre,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad
                        ELSE 0 END) AS pares_total,
               SUM(CASE WHEN MONTH(v.fecha) IN {meses_pico_sql}
                        THEN (CASE WHEN v.operacion='+' THEN v.cantidad
                                   WHEN v.operacion='-' THEN -v.cantidad
                                   ELSE 0 END)
                        ELSE 0 END) AS pares_temporada
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        JOIN msgestion01.dbo.proveedores p ON p.codigo = a.proveedor
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.subrubro IN {subrubros_sql}
          AND a.rubro IN {rubros_sql}
          AND a.descripcion_1 LIKE '{color_keyword}'
          AND v.fecha >= DATEADD(year, -{int(anios_historia)}, GETDATE())
        GROUP BY a.proveedor, p.denominacion
        HAVING SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad
                        ELSE 0 END) > 0
    """
    df_prov = query_df(sql_prov)

    proveedores = []
    if not df_prov.empty:
        df_prov['pares_total'] = pd.to_numeric(df_prov['pares_total'], errors='coerce').fillna(0)
        df_prov['pares_temporada'] = pd.to_numeric(df_prov['pares_temporada'], errors='coerce').fillna(0)
        total_temp = df_prov['pares_temporada'].sum()
        total_temp = max(total_temp, 1)
        df_prov = df_prov.sort_values('pares_total', ascending=False)
        for _, row in df_prov.iterrows():
            proveedores.append({
                'proveedor': int(row['proveedor']),
                'nombre': str(row['nombre']).strip(),
                'pares_total': round(float(row['pares_total'])),
                'pares_temporada': round(float(row['pares_temporada'])),
                'pct_temporada': round(float(row['pares_temporada']) / total_temp, 4),
            })

    # ── 5. MEJOR MOMENTO (compras vs ventas por año) ──
    sql_compras_hist = f"""
        SELECT YEAR(c2.fecha_comprobante) AS anio,
               MONTH(c2.fecha_comprobante) AS mes,
               SUM(c1.cantidad) AS pares_comprados
        FROM msgestionC.dbo.compras1 c1
        JOIN msgestionC.dbo.compras2 c2
          ON c1.codigo = c2.codigo AND c1.numero = c2.numero
         AND c1.letra = c2.letra AND c1.sucursal = c2.sucursal
        JOIN msgestion01art.dbo.articulo a ON a.codigo = c1.articulo
        WHERE c1.operacion = '+'
          AND a.subrubro IN {subrubros_sql}
          AND a.rubro IN {rubros_sql}
          AND a.descripcion_1 LIKE '{color_keyword}'
          AND c2.fecha_comprobante >= DATEADD(year, -{int(anios_historia)}, GETDATE())
        GROUP BY YEAR(c2.fecha_comprobante), MONTH(c2.fecha_comprobante)
    """
    df_compras_hist = query_df(sql_compras_hist)

    sql_ventas_hist = f"""
        SELECT YEAR(v.fecha) AS anio,
               MONTH(v.fecha) AS mes,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad
                        ELSE 0 END) AS pares
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.subrubro IN {subrubros_sql}
          AND a.rubro IN {rubros_sql}
          AND a.descripcion_1 LIKE '{color_keyword}'
          AND v.fecha >= DATEADD(year, -{int(anios_historia)}, GETDATE())
        GROUP BY YEAR(v.fecha), MONTH(v.fecha)
    """
    df_ventas_hist = query_df(sql_ventas_hist)

    mejor_momento = {'anio': None, 'mes_compra': None, 'pares_comprados': 0,
                     'vtas_temporada_siguiente': 0, 'ratio': 0}
    if not df_compras_hist.empty and not df_ventas_hist.empty and meses_pico:
        df_compras_hist['pares_comprados'] = pd.to_numeric(
            df_compras_hist['pares_comprados'], errors='coerce').fillna(0)
        df_ventas_hist['pares'] = pd.to_numeric(
            df_ventas_hist['pares'], errors='coerce').fillna(0)

        # Build ventas lookup: {(anio, mes): pares}
        vtas_lookup = {}
        for _, row in df_ventas_hist.iterrows():
            vtas_lookup[(int(row['anio']), int(row['mes']))] = float(row['pares'])

        # For each year, find month with max compras, then sum temporada ventas
        compras_by_year = df_compras_hist.groupby('anio').apply(
            lambda g: g.loc[g['pares_comprados'].idxmax()]).reset_index(drop=True)

        best_ratio = 0
        for _, row in compras_by_year.iterrows():
            anio = int(row['anio'])
            mes_c = int(row['mes'])
            pares_c = float(row['pares_comprados'])
            if pares_c <= 0:
                continue
            # Temporada ventas: same year if compra before temporada, else next year
            vtas_temp = sum(vtas_lookup.get((anio, m), 0) for m in meses_pico)
            ratio = vtas_temp / pares_c if pares_c > 0 else 0
            if ratio > best_ratio:
                best_ratio = ratio
                mejor_momento = {
                    'anio': anio,
                    'mes_compra': mes_c,
                    'pares_comprados': round(pares_c),
                    'vtas_temporada_siguiente': round(vtas_temp),
                    'ratio': round(ratio, 2),
                }

    # ── 6. RESUMEN ──
    # Stock total actual del nicho
    sql_stock_total = f"""
        SELECT ISNULL(SUM(s.stock_actual), 0) AS stock_total
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        WHERE a.subrubro IN {subrubros_sql}
          AND a.rubro IN {rubros_sql}
          AND a.descripcion_1 LIKE '{color_keyword}'
          AND s.deposito IN {DEPOS_SQL}
    """
    df_stk = query_df(sql_stock_total)
    stock_total = 0
    if not df_stk.empty:
        stock_total = float(pd.to_numeric(df_stk['stock_total'].iloc[0], errors='coerce') or 0)

    demanda_anual = round(total_anual)
    demanda_temporada = round(total_temporada)
    dias_temporada = len(meses_pico) * 30 if meses_pico else 1
    vel_diaria_temp = demanda_temporada / max(dias_temporada, 1)
    cobertura_dias = round(stock_total / max(vel_diaria_temp, 0.001), 1)

    resumen = {
        'demanda_anual': demanda_anual,
        'demanda_temporada': demanda_temporada,
        'stock_total': round(stock_total),
        'cobertura_temporada_dias': cobertura_dias,
    }

    return {
        'estacionalidad': estacionalidad,
        'curva_talles': curva_talles,
        'proveedores': proveedores,
        'mejor_momento': mejor_momento,
        'temporada': temporada,
        'resumen': resumen,
    }


# ============================================================================
# UI: DASHBOARD GLOBAL
# ============================================================================

def render_semaforo(status):
    if status == 'rojo':
        return '<span class="semaforo-rojo">SIN STOCK</span>'
    elif status == 'amarillo':
        return '<span class="semaforo-amarillo">BAJO</span>'
    return '<span class="semaforo-verde">OK</span>'


@st.cache_data(ttl=3600)
def proyectar_entregas_mensuales(pedir_total, vel_mensual, stock_actual, f_est,
                                  mes_inicio, n_entregas=6):
    """
    Distribuye un pedido total en N entregas mensuales.
    Cada entrega cubre la demanda del mes siguiente, ponderada por estacionalidad.

    Returns: list of dicts [{mes, entrega_pares, stock_proyectado, demanda_mes}]
    """
    plan = []
    stock = stock_actual

    # Calculate demand per delivery month
    demandas = []
    for i in range(n_entregas):
        mes = ((mes_inicio - 1 + i) % 12) + 1
        demanda = vel_mensual * f_est.get(mes, 1.0)
        demandas.append({'mes': mes, 'demanda': demanda})

    total_demanda = sum(d['demanda'] for d in demandas)
    if total_demanda <= 0:
        return []

    # Distribute pedir_total proportionally to demand
    for d in demandas:
        entrega = round(pedir_total * d['demanda'] / total_demanda)
        stock = stock + entrega - d['demanda']
        plan.append({
            'mes': d['mes'],
            'entrega_pares': entrega,
            'demanda_mes': round(d['demanda']),
            'stock_proyectado': round(stock),
        })

    return plan


# ============================================================================
# DETECCIÓN DE NICHOS DESCUBIERTOS
# ============================================================================

@st.cache_data(ttl=7200)
def detectar_nichos_descubiertos(min_vtas=10, max_cob_dias=30, solo_post_2020=True):
    """
    Detecta nichos de producto con demanda real pero sin stock ni pedidos pendientes.

    Filters:
    - solo_post_2020: solo artículos con al menos 1 compra después de 2020 (excluye merma/muertos)
    - min_vtas: mínimo pares vendidos en 12m para considerar que hay demanda
    - max_cob_dias: máximo días de cobertura (stock+pedidos) para considerar descubierto

    Returns: DataFrame with columns:
        genero, categoria, marca, marca_cod, proveedor, modelos, pares_12m,
        vel_mes, stock, pedido, disponible, cob_dias, ppp_costo,
        es_temporada (bool: si el producto es de temporada actual basado en NICHOS_PREDEFINIDOS),
        urgencia (CRITICO/BAJO/MEDIO/OK)
    """
    desde = (date.today() - relativedelta(months=12)).replace(day=1).strftime('%Y%m%d')

    filtro_post2020 = ""
    if solo_post_2020:
        filtro_post2020 = """
            JOIN (
                SELECT DISTINCT c1.articulo
                FROM msgestionC.dbo.compras1 c1
                JOIN msgestionC.dbo.compras2 c2 ON c2.codigo = c1.codigo
                    AND c2.letra = c1.letra AND c2.sucursal = c1.sucursal
                    AND c2.numero = c1.numero
                WHERE c2.fecha_comprobante >= '20200101' AND c1.operacion = '+'
            ) act ON act.articulo = a.codigo
        """

    sql = f"""
        WITH ventas_agg AS (
            SELECT
                a.rubro,
                a.subrubro,
                a.marca,
                a.proveedor,
                COUNT(DISTINCT LEFT(a.codigo_sinonimo, 10)) AS modelos,
                SUM(CASE WHEN v.operacion = '+' THEN v.cantidad
                         WHEN v.operacion = '-' THEN -v.cantidad ELSE 0 END) AS pares_12m,
                AVG(CASE WHEN a.precio_fabrica > 0 THEN a.precio_fabrica END) AS ppp_costo
            FROM msgestion01art.dbo.articulo a
            JOIN msgestionC.dbo.ventas1 v ON v.articulo = a.codigo
            {filtro_post2020}
            WHERE v.codigo NOT IN {EXCL_VENTAS}
              AND v.fecha >= '{desde}'
              AND a.estado = 'V'
              AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
              AND a.rubro IN (1, 3, 4, 5, 6)
              AND a.subrubro IS NOT NULL AND a.subrubro > 0
              AND LEN(a.codigo_sinonimo) >= 10
            GROUP BY a.rubro, a.subrubro, a.marca, a.proveedor
            HAVING SUM(CASE WHEN v.operacion = '+' THEN v.cantidad
                            WHEN v.operacion = '-' THEN -v.cantidad ELSE 0 END) >= {min_vtas}
        ),
        stock_agg AS (
            SELECT
                a.rubro, a.subrubro, a.marca, a.proveedor,
                SUM(s.stock_actual) AS stock
            FROM msgestionC.dbo.stock s
            JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
            WHERE s.deposito IN {DEPOS_SQL}
              AND a.estado = 'V'
              AND a.rubro IN (1, 3, 4, 5, 6)
              AND a.subrubro IS NOT NULL AND a.subrubro > 0
            GROUP BY a.rubro, a.subrubro, a.marca, a.proveedor
        ),
        pedidos_agg AS (
            SELECT
                a.rubro, a.subrubro, a.marca, a.proveedor,
                SUM(p1.cantidad) AS pedido
            FROM msgestionC.dbo.pedico1 p1
            JOIN msgestionC.dbo.pedico2 p2 ON p2.codigo = p1.codigo
                AND p2.letra = p1.letra AND p2.sucursal = p1.sucursal
                AND p2.numero = p1.numero
            JOIN msgestion01art.dbo.articulo a ON a.codigo = p1.articulo
            WHERE p2.estado = 'V' AND p2.codigo = 8
              AND a.rubro IN (1, 3, 4, 5, 6)
              AND a.subrubro IS NOT NULL AND a.subrubro > 0
            GROUP BY a.rubro, a.subrubro, a.marca, a.proveedor
        )
        SELECT
            va.rubro,
            va.subrubro,
            va.marca AS marca_cod,
            va.proveedor AS proveedor_cod,
            va.modelos,
            va.pares_12m,
            CAST(va.pares_12m AS FLOAT) / 12.0 AS vel_mes,
            ISNULL(sa.stock, 0) AS stock,
            ISNULL(pa.pedido, 0) AS pedido,
            ISNULL(sa.stock, 0) + ISNULL(pa.pedido, 0) AS disponible,
            CASE WHEN va.pares_12m > 0
                 THEN CAST((ISNULL(sa.stock, 0) + ISNULL(pa.pedido, 0)) AS FLOAT)
                      / (CAST(va.pares_12m AS FLOAT) / 365.0)
                 ELSE 999 END AS cob_dias,
            ISNULL(va.ppp_costo, 0) AS ppp_costo
        FROM ventas_agg va
        LEFT JOIN stock_agg sa ON sa.rubro = va.rubro AND sa.subrubro = va.subrubro
            AND sa.marca = va.marca AND sa.proveedor = va.proveedor
        LEFT JOIN pedidos_agg pa ON pa.rubro = va.rubro AND pa.subrubro = va.subrubro
            AND pa.marca = va.marca AND pa.proveedor = va.proveedor
        WHERE CASE WHEN va.pares_12m > 0
                   THEN CAST((ISNULL(sa.stock, 0) + ISNULL(pa.pedido, 0)) AS FLOAT)
                        / (CAST(va.pares_12m AS FLOAT) / 365.0)
                   ELSE 999 END < {max_cob_dias}
        ORDER BY va.pares_12m DESC
    """
    df = query_df(sql)
    if df.empty:
        return df

    # Map descriptions
    sub_desc = cargar_subrubro_desc()
    marcas_dict = cargar_marcas_dict()
    prov_dict = cargar_proveedores_dict()

    df['genero'] = df['rubro'].map(RUBRO_GENERO).fillna('OTRO')
    df['categoria'] = df['subrubro'].map(sub_desc).fillna('?')
    df['marca'] = df['marca_cod'].apply(
        lambda c: marcas_dict.get(int(c), f'M{c}') if pd.notna(c) else '?')
    df['proveedor'] = df['proveedor_cod'].apply(
        lambda c: prov_dict.get(int(c), f'P{c}') if pd.notna(c) else '?')

    # Temporada: check if current month falls within any NICHO's temporada_esperada
    # that matches this row's rubro/subrubro
    mes_actual = date.today().month

    def _es_temporada(row):
        for nicho in NICHOS_PREDEFINIDOS.values():
            rubros_nicho = nicho.get('rubros', ())
            subs_nicho = nicho.get('subrubros', ())
            temp = nicho.get('temporada_esperada', ())
            if not temp:
                continue
            r = int(row['rubro']) if pd.notna(row['rubro']) else 0
            s = int(row['subrubro']) if pd.notna(row['subrubro']) else 0
            if r in rubros_nicho and s in subs_nicho and mes_actual in temp:
                return True
        return False

    df['es_temporada'] = df.apply(_es_temporada, axis=1)

    # Urgencia
    df['cob_dias'] = df['cob_dias'].round(0).astype(int)
    df['urgencia'] = df['cob_dias'].apply(
        lambda d: 'CRITICO' if d == 0 else ('BAJO' if d < 15 else ('MEDIO' if d < 30 else 'OK'))
    )

    cols = ['genero', 'categoria', 'marca', 'marca_cod', 'proveedor', 'proveedor_cod',
            'modelos', 'pares_12m', 'vel_mes', 'stock', 'pedido', 'disponible',
            'cob_dias', 'ppp_costo', 'es_temporada', 'urgencia']
    return df[cols].sort_values(['urgencia', 'pares_12m'], ascending=[True, False])


@st.cache_data(ttl=7200)
def detectar_nichos_por_subrubro(min_vtas=20, max_cob_dias=30):
    """Same as detectar_nichos_descubiertos but grouped by rubro x subrubro only,
    showing total demand vs total coverage."""
    desde = (date.today() - relativedelta(months=12)).replace(day=1).strftime('%Y%m%d')

    sql = f"""
        WITH ventas_sub AS (
            SELECT
                a.rubro,
                a.subrubro,
                COUNT(DISTINCT LEFT(a.codigo_sinonimo, 10)) AS modelos,
                COUNT(DISTINCT a.marca) AS marcas,
                COUNT(DISTINCT a.proveedor) AS proveedores,
                SUM(CASE WHEN v.operacion = '+' THEN v.cantidad
                         WHEN v.operacion = '-' THEN -v.cantidad ELSE 0 END) AS pares_12m,
                AVG(CASE WHEN a.precio_fabrica > 0 THEN a.precio_fabrica END) AS ppp_costo
            FROM msgestion01art.dbo.articulo a
            JOIN msgestionC.dbo.ventas1 v ON v.articulo = a.codigo
            WHERE v.codigo NOT IN {EXCL_VENTAS}
              AND v.fecha >= '{desde}'
              AND a.estado = 'V'
              AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
              AND a.rubro IN (1, 3, 4, 5, 6)
              AND a.subrubro IS NOT NULL AND a.subrubro > 0
              AND LEN(a.codigo_sinonimo) >= 10
            GROUP BY a.rubro, a.subrubro
            HAVING SUM(CASE WHEN v.operacion = '+' THEN v.cantidad
                            WHEN v.operacion = '-' THEN -v.cantidad ELSE 0 END) >= {min_vtas}
        ),
        stock_sub AS (
            SELECT
                a.rubro, a.subrubro,
                SUM(s.stock_actual) AS stock
            FROM msgestionC.dbo.stock s
            JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
            WHERE s.deposito IN {DEPOS_SQL}
              AND a.estado = 'V'
              AND a.rubro IN (1, 3, 4, 5, 6)
              AND a.subrubro IS NOT NULL AND a.subrubro > 0
            GROUP BY a.rubro, a.subrubro
        ),
        pedidos_sub AS (
            SELECT
                a.rubro, a.subrubro,
                SUM(p1.cantidad) AS pedido
            FROM msgestionC.dbo.pedico1 p1
            JOIN msgestionC.dbo.pedico2 p2 ON p2.codigo = p1.codigo
                AND p2.letra = p1.letra AND p2.sucursal = p1.sucursal
                AND p2.numero = p1.numero
            JOIN msgestion01art.dbo.articulo a ON a.codigo = p1.articulo
            WHERE p2.estado = 'V' AND p2.codigo = 8
              AND a.rubro IN (1, 3, 4, 5, 6)
              AND a.subrubro IS NOT NULL AND a.subrubro > 0
            GROUP BY a.rubro, a.subrubro
        )
        SELECT
            vs.rubro,
            vs.subrubro,
            vs.modelos,
            vs.marcas,
            vs.proveedores,
            vs.pares_12m,
            CAST(vs.pares_12m AS FLOAT) / 12.0 AS vel_mes,
            ISNULL(ss.stock, 0) AS stock,
            ISNULL(ps.pedido, 0) AS pedido,
            ISNULL(ss.stock, 0) + ISNULL(ps.pedido, 0) AS disponible,
            CASE WHEN vs.pares_12m > 0
                 THEN CAST((ISNULL(ss.stock, 0) + ISNULL(ps.pedido, 0)) AS FLOAT)
                      / (CAST(vs.pares_12m AS FLOAT) / 365.0)
                 ELSE 999 END AS cob_dias,
            ISNULL(vs.ppp_costo, 0) AS ppp_costo
        FROM ventas_sub vs
        LEFT JOIN stock_sub ss ON ss.rubro = vs.rubro AND ss.subrubro = vs.subrubro
        LEFT JOIN pedidos_sub ps ON ps.rubro = vs.rubro AND ps.subrubro = vs.subrubro
        WHERE CASE WHEN vs.pares_12m > 0
                   THEN CAST((ISNULL(ss.stock, 0) + ISNULL(ps.pedido, 0)) AS FLOAT)
                        / (CAST(vs.pares_12m AS FLOAT) / 365.0)
                   ELSE 999 END < {max_cob_dias}
        ORDER BY vs.pares_12m DESC
    """
    df = query_df(sql)
    if df.empty:
        return df

    sub_desc = cargar_subrubro_desc()
    df['genero'] = df['rubro'].map(RUBRO_GENERO).fillna('OTRO')
    df['categoria'] = df['subrubro'].map(sub_desc).fillna('?')

    # Temporada flag
    mes_actual = date.today().month

    def _es_temporada_sub(row):
        for nicho in NICHOS_PREDEFINIDOS.values():
            rubros_nicho = nicho.get('rubros', ())
            subs_nicho = nicho.get('subrubros', ())
            temp = nicho.get('temporada_esperada', ())
            if not temp:
                continue
            r = int(row['rubro']) if pd.notna(row['rubro']) else 0
            s = int(row['subrubro']) if pd.notna(row['subrubro']) else 0
            if r in rubros_nicho and s in subs_nicho and mes_actual in temp:
                return True
        return False

    df['es_temporada'] = df.apply(_es_temporada_sub, axis=1)

    df['cob_dias'] = df['cob_dias'].round(0).astype(int)
    df['urgencia'] = df['cob_dias'].apply(
        lambda d: 'CRITICO' if d == 0 else ('BAJO' if d < 15 else ('MEDIO' if d < 30 else 'OK'))
    )

    cols = ['genero', 'categoria', 'modelos', 'marcas', 'proveedores',
            'pares_12m', 'vel_mes', 'stock', 'pedido', 'disponible',
            'cob_dias', 'ppp_costo', 'es_temporada', 'urgencia']
    return df[cols].sort_values(['urgencia', 'pares_12m'], ascending=[True, False])


def render_dashboard():
    """Pantalla principal: dashboard global con todos los productos."""

    st.title("🔄 Reposición Inteligente")
    st.caption("Waterfall ROI · Presupuesto como driver · Velocidad real con quiebre")

    # ── PRECARGA: datos base una sola vez por sesion ──
    if '_base_loaded' not in st.session_state:
        progress = st.progress(0, text="Cargando datos base...")
        st.session_state['marcas_dict'] = cargar_marcas_dict()
        progress.progress(25, text="Cargando proveedores...")
        st.session_state['proveedores_dict'] = cargar_proveedores_dict()
        progress.progress(50, text="Cargando resumen de marcas...")
        st.session_state['df_resumen'] = cargar_resumen_marcas()
        progress.progress(75, text="Cargando subrubros...")
        st.session_state['subrubro_desc'] = cargar_subrubro_desc()
        progress.progress(100, text="Listo.")
        st.session_state['_base_loaded'] = True
        progress.empty()

    marcas_dict = st.session_state['marcas_dict']
    provs_dict = st.session_state['proveedores_dict']

    # ── SIDEBAR ──
    st.sidebar.header("Filtros")

    # Boton para forzar recarga de datos base
    if st.sidebar.button("🔄 Recargar datos", help="Fuerza recarga de marcas, proveedores y resumen"):
        for k in ['_base_loaded', 'marcas_dict', 'proveedores_dict', 'df_resumen',
                   'subrubro_desc', '_dash_computed', '_dash_filter_key']:
            st.session_state.pop(k, None)
        st.cache_data.clear()
        st.rerun()

    df_resumen = st.session_state['df_resumen']

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

        # Reconstituir índice desde código guardado (persiste aunque expire el cache)
        _marca_saved = st.session_state.get('marca_sel_codigo_saved', None)
        _default_idx = 0
        if _marca_saved and _marca_saved in codigos_marca:
            _default_idx = codigos_marca.index(_marca_saved)

        sel_idx = st.sidebar.selectbox("Marca", range(len(opciones_marca)),
                                        format_func=lambda i: opciones_marca[i],
                                        key="marca_filtro",
                                        index=_default_idx)

        # Bounds check
        if sel_idx >= len(codigos_marca):
            sel_idx = 0

        if sel_idx == 0:
            st.info("Seleccioná una marca en el sidebar para ver los productos.")
            return
        marca_sel_codigo = int(codigos_marca[sel_idx])
        st.session_state['marca_sel_codigo_saved'] = marca_sel_codigo

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

    # --- Presupuesto automático basado en data ---
    mes_actual = date.today().month
    horizonte_dias = st.sidebar.number_input(
        "Horizonte de cobertura (días)",
        min_value=30, max_value=365, value=90, step=30,
        help="Período a cubrir. Ej: 210 días = hasta octubre"
    )
    mes_fin_horizonte = ((mes_actual - 1 + horizonte_dias // 30) % 12) + 1

    # Determinar proveedor para presupuesto (funciona en ambos modos: Marca y Proveedor)
    _prov_para_presup = locals().get('prov_sel_codigo')
    if _prov_para_presup is None and not df_f.empty and 'proveedor' in df_f.columns:
        # En modo Marca: usar el proveedor dominante de los productos filtrados
        _mode = df_f['proveedor'].mode()
        _prov_para_presup = int(_mode.iloc[0]) if not _mode.empty else None

    # Calcular presupuesto sugerido desde ventas mismo período año anterior
    pares_base = 0
    pares_ajustado = 0
    if _prov_para_presup is not None:
        try:
            pp = presupuesto_pares(_prov_para_presup, mes_actual, mes_fin_horizonte)
            pares_base = pp.get('total_pares', 0)
            pares_ajustado = pp.get('total_pares_ajustado', pares_base)
        except Exception:
            pass

    # PPP: precio promedio ponderado del proveedor
    ppp = 0
    if not df_f.empty and 'precio_fabrica' in df_f.columns:
        precios_validos = df_f[df_f['precio_fabrica'] > 0]['precio_fabrica']
        if not precios_validos.empty:
            # Ponderar por ventas si disponible
            if 'ventas_12m' in df_f.columns:
                df_ppp = df_f[(df_f['precio_fabrica'] > 0) & (df_f['ventas_12m'] > 0)]
                if not df_ppp.empty:
                    ppp = (df_ppp['precio_fabrica'] * df_ppp['ventas_12m']).sum() / df_ppp['ventas_12m'].sum()
                else:
                    ppp = precios_validos.median()
            else:
                ppp = precios_validos.median()

    # Estimar ventas perdidas por quiebre usando vel_real_con_perdidas
    pares_perdidos = 0
    if not df_f.empty:
        csrs_presup = df_f['csr'].dropna().unique().tolist()
        if csrs_presup:
            try:
                _quiebre_presup = analizar_quiebre_batch(csrs_presup)
                # Sumar diferencia vel_real_con_perdidas - vel_real = ventas perdidas/mes
                for _csr_q, _qdata in _quiebre_presup.items():
                    _vel_perdidas = _qdata.get('vel_real_con_perdidas', 0) - _qdata.get('vel_real', 0)
                    if _vel_perdidas > 0:
                        pares_perdidos += _vel_perdidas
                # Escalar al horizonte
                pares_perdidos = int(pares_perdidos * (horizonte_dias / 30))
            except Exception:
                pass

    presup_base_pesos = int(pares_base * ppp) if ppp > 0 else 0
    presup_ajustado_pesos = int((pares_ajustado + pares_perdidos) * ppp) if ppp > 0 else 0

    st.sidebar.markdown("---")
    st.sidebar.markdown("**📊 Presupuesto sugerido**")
    st.sidebar.metric("Presup. base", f"{pares_base:,} pares")
    st.sidebar.caption(f"${presup_base_pesos:,.0f} (vendidos mismo período)")
    st.sidebar.metric("Presup. ajustado", f"{pares_ajustado + pares_perdidos:,} pares",
                      delta=f"+{pares_perdidos} perdidas" if pares_perdidos > 0 else None)
    st.sidebar.caption(f"${presup_ajustado_pesos:,.0f} (con ventas perdidas por quiebre)")
    st.sidebar.caption(f"PPP (precio de costo): ${ppp:,.0f} | Período: {mes_actual}→{mes_fin_horizonte}")
    st.sidebar.markdown("---")

    presupuesto = st.sidebar.number_input(
        "Presupuesto ($)",
        value=max(presup_ajustado_pesos, 500_000), step=500_000,
        format="%d", help="Ajustá manualmente o usá el sugerido"
    )

    dias_pago = st.sidebar.number_input(
        "Plazo de pago proveedor (días)", value=90, min_value=0, max_value=365, step=30,
        help="Días de financiación (60/90/120/150). Reduce el recupero efectivo de inversión."
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

    # ── GLOBAL SCARCITY SCAN ──
    with st.expander("🚨 Escasez crónica de talles (auto-scan)", expanded=False):
        for rubro_cod, rubro_nombre in RUBRO_GENERO.items():
            if rubro_cod not in (1, 3):  # solo damas y hombres
                continue
            escasez = talles_escasez_cronica(rubro_cod)
            if escasez:
                talles_criticos = [e['talle'] for e in escasez[:10]]
                st.error(f"**{rubro_nombre}**: {len(escasez)} talles con escasez crónica: {', '.join(talles_criticos)}")
            else:
                st.success(f"**{rubro_nombre}**: sin escasez crónica detectada")

    # ── TABS ──
    (tab_surtido, tab_dashboard, tab_waterfall, tab_optimizar,
     tab_curva, tab_canibal, tab_emergentes, tab_pedido, tab_historial,
     tab_nichos) = st.tabs([
        "🗺️ Mapa Surtido", "📊 Dashboard", "🌊 Waterfall", "💰 Optimizar Compra",
        "👟 Curva Talle", "🔬 Canibalización", "🚀 Emergentes",
        "🛒 Armar Pedido", "📋 Historial", "🔍 Nichos"
    ])

    # ══════════════════════════════════════════════════════════════
    # TAB 0: MAPA DE SURTIDO POR CATEGORÍA (V2)
    # ══════════════════════════════════════════════════════════════
    with tab_surtido:
        # CSS fix: métricas visibles en dark mode
        st.markdown("""
<style>
[data-testid="stMetricValue"] { color: #ffffff !important; }
[data-testid="stMetricLabel"] { color: #cccccc !important; }
[data-testid="stMetricDelta"] { color: #00cc00 !important; }
div[data-testid="stMetric"] {
    background-color: rgba(28, 131, 225, 0.1);
    border-radius: 8px;
    padding: 10px 15px;
}
</style>
""", unsafe_allow_html=True)
        st.subheader("Mapa de Surtido por Categoria")
        st.caption("Cobertura por genero x subrubro **de la marca/proveedor seleccionado**. "
                   "Rojo = menos de 30 dias. Drill-down a piramide de precios y sustitutos.")

        # Construir mapa directamente desde df_f (ya filtrado por marca/proveedor)
        sub_desc = st.session_state.get('subrubro_desc') or cargar_subrubro_desc()
        df_mapa = df_f.groupby(
            [df_f['rubro'].fillna(0).astype(int), df_f['subrubro'].fillna(0).astype(int)]
        ).agg(
            modelos=('csr', 'nunique'),
            stock_total=('stock_total', 'sum'),
            ventas_12m=('ventas_12m', 'sum'),
            precio_min=('precio_fabrica', 'min'),
            precio_max=('precio_fabrica', 'max'),
            precio_avg=('precio_fabrica', 'mean'),
        ).reset_index()
        df_mapa.rename(columns={'rubro': 'genero_cod', 'subrubro': 'sub_cod'}, inplace=True)
        df_mapa['genero'] = df_mapa['genero_cod'].map(RUBRO_GENERO).fillna('OTRO')
        df_mapa['categoria'] = df_mapa['sub_cod'].map(sub_desc).fillna('?')
        df_mapa['vel_diaria'] = df_mapa['ventas_12m'] / 365
        df_mapa['cobertura_dias'] = np.where(
            df_mapa['vel_diaria'] > 0,
            df_mapa['stock_total'] / df_mapa['vel_diaria'],
            999
        ).astype(int)
        df_mapa['urgencia'] = pd.cut(
            df_mapa['cobertura_dias'],
            bins=[-1, 30, 60, 120, 9999],
            labels=['CRITICO', 'BAJO', 'MEDIO', 'OK']
        )

        # Factor estacional s_t por categoría
        progress_surtido = st.progress(0, text="Calculando factor estacional...")
        csrs_mapa = df_f['csr'].tolist()
        factores_est_mapa = factor_estacional_batch(csrs_mapa)
        mes_act = date.today().month
        mes_prox = (mes_act % 12) + 1
        df_f['_s_t'] = df_f['csr'].map(
            lambda c: factores_est_mapa.get(c, {}).get(mes_prox, 1.0)
            / max(factores_est_mapa.get(c, {}).get(mes_act, 1.0), 0.1)
        )
        s_t_cat = df_f.groupby(
            [df_f['rubro'].fillna(0).astype(int), df_f['subrubro'].fillna(0).astype(int)]
        )['_s_t'].mean().reset_index()
        s_t_cat.rename(columns={'rubro': 'genero_cod', 'subrubro': 'sub_cod'}, inplace=True)
        df_mapa = df_mapa.merge(s_t_cat, on=['genero_cod', 'sub_cod'], how='left')
        df_mapa['_s_t'] = df_mapa['_s_t'].fillna(1.0).round(2)
        df_mapa['vel_diaria_est'] = df_mapa['vel_diaria'] * df_mapa['_s_t']
        df_mapa['cobertura_est'] = np.where(
            df_mapa['vel_diaria_est'] > 0,
            df_mapa['stock_total'] / df_mapa['vel_diaria_est'],
            999
        ).astype(int)

        progress_surtido.progress(60, text="Cargando alertas de talles...")
        # Solo consultar categorías que ya aparecen en el mapa filtrado (MUCHO más rápido)
        cats_filtro = list(zip(df_mapa['genero_cod'].tolist(), df_mapa['sub_cod'].tolist()))
        # Detectar marca/proveedor seleccionado
        _marca_filtro = locals().get('marca_sel_codigo') if modo_filtro == 'Marca' else None
        _prov_filtro = locals().get('prov_sel_codigo') if modo_filtro == 'Proveedor' else None
        df_alertas_talles, detalle_talles_dict = calcular_alertas_talles(
            categorias_filtro=cats_filtro,
            marca_id=_marca_filtro,
            proveedor_id=_prov_filtro,
        )
        progress_surtido.progress(100, text="Listo.")
        progress_surtido.empty()

        if df_mapa.empty:
            st.warning("No hay categorias con datos para esta marca/proveedor.")
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
                st.error(f"**{total_talles_crit} talles criticos** en {len(alertas_activas)} categorias — stock 0 con demanda o menos de 30 dias")
                with st.expander(f"Ver detalle de {total_talles_crit} talles criticos", expanded=False):
                    for _, row in alertas_activas.head(15).iterrows():
                        st.markdown(
                            f"**{row['genero']} > {row['categoria']}** — "
                            f"Talles: `{row['talles_detalle']}` "
                            f"(cat. cob: {row['cobertura_dias']}d = {row['urgencia']})"
                        )

            # KPIs globales del surtido
            c1, c2, c3, c4, c5 = st.columns(5)
            criticos_cat = len(df_mapa[df_mapa['urgencia'] == 'CRITICO'])
            bajos_cat = len(df_mapa[df_mapa['urgencia'] == 'BAJO'])
            total_talles_crit_all = int(df_mapa['talles_criticos'].sum())
            c1.metric("Categorias activas", len(df_mapa))
            c2.metric("Cat. CRITICAS (<30d)", criticos_cat)
            c3.metric("Talles criticos", total_talles_crit_all)
            c4.metric("Stock total (pares)", f"{int(df_mapa['stock_total'].sum()):,}")
            s_t_prom = df_mapa['_s_t'].mean()
            c5.metric("Factor estacional", f"{s_t_prom:.2f}",
                       delta=f"{(s_t_prom - 1) * 100:+.0f}%" if abs(s_t_prom - 1) > 0.05 else None)

            st.divider()

            # Filtros
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                generos_disp = sorted(df_mapa['genero'].dropna().unique())
                genero_filtro = st.multiselect("Filtrar genero", generos_disp,
                                                default=generos_disp, key="surtido_genero")
            df_vis = df_mapa[df_mapa['genero'].isin(genero_filtro)].copy()
            with fc2:
                cats_disp = sorted(df_vis['categoria'].dropna().unique())
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
                        'cobertura_dias', '_s_t', 'cobertura_est', 'urgencia',
                        'talles_criticos', 'talles_detalle',
                        'precio_min', 'precio_max']],
                column_config={
                    'genero': st.column_config.TextColumn('Genero', width=90),
                    'categoria': st.column_config.TextColumn('Categoria', width=150),
                    'modelos': st.column_config.NumberColumn('Modelos', format="%d"),
                    'stock_total': st.column_config.NumberColumn('Stock', format="%d"),
                    'ventas_12m': st.column_config.NumberColumn('Vtas 12m', format="%d"),
                    'cobertura_dias': st.column_config.NumberColumn('Cob. dias', format="%d"),
                    '_s_t': st.column_config.NumberColumn('s(t)', format="%.2f",
                        help="Factor estacional: >1 = temporada alta, <1 = temporada baja"),
                    'cobertura_est': st.column_config.NumberColumn('Cob.Est', format="%d",
                        help="Cobertura ajustada por factor estacional"),
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
                    # Semáforo visual rápido en columnas (6 estados)
                    escasez_t = df_talles[df_talles['urgencia'] == 'ESCASEZ']
                    criticos_t = df_talles[df_talles['urgencia'] == 'CRITICO']
                    bajos_t = df_talles[df_talles['urgencia'] == 'BAJO']
                    medios_t = df_talles[df_talles['urgencia'] == 'MEDIO']
                    ok_t = df_talles[df_talles['urgencia'] == 'OK']
                    sinventa_t = df_talles[df_talles['urgencia'] == 'SIN VENTA']

                    n_alerta = len(escasez_t) + len(criticos_t)
                    tc1, tc2, tc3, tc4 = st.columns(4)
                    tc1.metric("Escasez cronica", len(escasez_t))
                    tc2.metric("Criticos (<30d)", len(criticos_t))
                    tc3.metric("Bajo (30-60d)", len(bajos_t))
                    tc4.metric("Total talles", len(df_talles))

                    if n_alerta > 0:
                        partes = []
                        if not escasez_t.empty:
                            partes.append(f"ESCASEZ CRONICA: {', '.join(escasez_t['talle'].tolist())}")
                        if not criticos_t.empty:
                            partes.append(f"CRITICOS: {', '.join(criticos_t['talle'].tolist())}")
                        st.error(" | ".join(partes))

                    # Tabla de talles con 6 estados y colores
                    def color_urgencia_talle(val):
                        colors = {
                            'ESCASEZ': 'background-color: #1a1a2e; color: #e0e0e0',
                            'CRITICO': 'background-color: #ff4b4b; color: white',
                            'BAJO': 'background-color: #ffa726; color: white',
                            'MEDIO': 'background-color: #ffee58; color: black',
                            'OK': 'background-color: #66bb6a; color: white',
                            'SIN VENTA': 'background-color: #9e9e9e; color: white',
                        }
                        return colors.get(val, '')

                    # Preparar columna de display para vel_real (dash para escasez/sin venta)
                    df_talles_display = df_talles[['talle', 'modelos', 'stock', 'vtas_12m', 'vel_real',
                                                    'pct_quiebre', 'cob_dias', 'urgencia']].copy()
                    # Cobertura display: 9999 -> mostrar como texto descriptivo
                    df_talles_display['cob_display'] = df_talles_display['cob_dias'].apply(
                        lambda x: '>999' if x >= 9999 else str(x)
                    )

                    st.dataframe(
                        df_talles_display[['talle', 'modelos', 'stock', 'vtas_12m', 'vel_real',
                                           'pct_quiebre', 'cob_dias', 'urgencia']].style.applymap(
                            color_urgencia_talle, subset=['urgencia']
                        ),
                        column_config={
                            'talle': st.column_config.TextColumn('Talle', width=60),
                            'modelos': st.column_config.NumberColumn('Modelos', format="%d"),
                            'stock': st.column_config.NumberColumn('Stock', format="%d"),
                            'vtas_12m': st.column_config.NumberColumn('Vtas 12m', format="%d"),
                            'vel_real': st.column_config.NumberColumn('Vel.Real/mes', format="%.1f"),
                            'pct_quiebre': st.column_config.NumberColumn('Quiebre%', format="%.0f%%"),
                            'cob_dias': st.column_config.NumberColumn('Cob.Dias', format="%d"),
                            'urgencia': 'Estado',
                        },
                        use_container_width=True, hide_index=True,
                    )

                    # Leyenda de estados
                    st.caption(
                        "Estados: **ESCASEZ** = quiebre cronico (>75% meses sin stock) | "
                        "**CRITICO** = <30 dias | **BAJO** = 30-60 dias | "
                        "**MEDIO** = 60-120 dias | **OK** = >120 dias | "
                        "**SIN VENTA** = sin demanda registrada"
                    )
                else:
                    st.info("Sin datos de talle para esta categoria.")

                # ── ANOMALÍAS DE STOCK en esta categoría ──
                df_cat_prods = df_f[
                    (df_f['rubro'] == genero_sel) & (df_f['subrubro'] == sub_sel)
                ]
                if not df_cat_prods.empty:
                    csrs_cat = df_cat_prods['csr'].tolist()
                    anomalias_cat = detectar_anomalias_stock(csrs_cat)
                    hay_anomalias = [c for c, v in anomalias_cat.items() if v.get('anomalias')]
                    if hay_anomalias:
                        st.divider()
                        st.markdown("#### Anomalias de stock detectadas")
                        for csr_a in hay_anomalias:
                            info = anomalias_cat[csr_a]
                            icono = {'IRREAL': '🔴', 'REVISAR': '🟡'}.get(info['nivel'], '🟢')
                            desc = df_cat_prods.loc[df_cat_prods['csr'] == csr_a, 'descripcion']
                            desc_str = desc.iloc[0] if not desc.empty else csr_a
                            st.warning(
                                f"{icono} **{desc_str}** (CSR {csr_a}): "
                                f"{', '.join(info['anomalias'])}"
                            )

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

                    # ── LEVEL 3: DRILL-DOWN INDIVIDUAL POR TALLE (post-pirámide) ──
                    st.divider()
                    st.subheader("Drill-down por talle individual")
                    st.caption(
                        "Detalle de cada talle con cobertura, velocidad real corregida por quiebre "
                        "y deteccion de escasez cronica. Selecciona un talle para ver articulos individuales."
                    )

                    # Reutilizar df_talles que ya se cargo arriba
                    if not df_talles.empty:
                        # Resumen compacto de alertas
                        n_escasez = len(df_talles[df_talles['urgencia'] == 'ESCASEZ'])
                        n_critico = len(df_talles[df_talles['urgencia'] == 'CRITICO'])
                        n_bajo = len(df_talles[df_talles['urgencia'] == 'BAJO'])
                        n_ok = len(df_talles[df_talles['urgencia'].isin(['OK', 'MEDIO'])])

                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Escasez cronica", n_escasez,
                                  delta=f"{n_escasez} talles siempre en falta" if n_escasez > 0 else None,
                                  delta_color="inverse")
                        m2.metric("Criticos", n_critico,
                                  delta=f"<30 dias cobertura" if n_critico > 0 else None,
                                  delta_color="inverse")
                        m3.metric("Bajo stock", n_bajo,
                                  delta="30-60 dias" if n_bajo > 0 else None,
                                  delta_color="inverse")
                        m4.metric("Saludables", n_ok)

                        # Tabla completa con st.dataframe y column_config
                        df_talle_drill = df_talles[['talle', 'stock', 'vtas_12m', 'vel_real',
                                                     'cob_dias', 'urgencia']].copy()
                        df_talle_drill.columns = ['Talle', 'Stock', 'Vtas 12m', 'Vel.Real',
                                                   'Cob.Dias', 'Estado']

                        def color_estado_drill(val):
                            colors = {
                                'ESCASEZ': 'background-color: #1a1a2e; color: #e0e0e0',
                                'CRITICO': 'background-color: #ff4b4b; color: white',
                                'BAJO': 'background-color: #ffa726; color: white',
                                'MEDIO': 'background-color: #ffee58; color: black',
                                'OK': 'background-color: #66bb6a; color: white',
                                'SIN VENTA': 'background-color: #9e9e9e; color: white',
                            }
                            return colors.get(val, '')

                        st.dataframe(
                            df_talle_drill.style.applymap(
                                color_estado_drill, subset=['Estado']
                            ),
                            column_config={
                                'Talle': st.column_config.TextColumn('Talle', width=70),
                                'Stock': st.column_config.NumberColumn('Stock', format="%d"),
                                'Vtas 12m': st.column_config.NumberColumn('Vtas 12m', format="%d"),
                                'Vel.Real': st.column_config.NumberColumn('Vel.Real/mes', format="%.1f",
                                    help="Velocidad real mensual corregida por quiebre"),
                                'Cob.Dias': st.column_config.NumberColumn('Cob.Dias', format="%d",
                                    help="Dias de cobertura = stock / vel.diaria"),
                                'Estado': st.column_config.TextColumn('Estado', width=100),
                            },
                            use_container_width=True, hide_index=True,
                        )

                        # Selectbox para drill-down a articulos individuales de un talle
                        talles_disponibles = df_talles['talle'].tolist()
                        talle_sel = st.selectbox(
                            "Ver articulos de un talle especifico",
                            talles_disponibles,
                            key="drill_talle_sel"
                        )

                        if talle_sel and st.button("Ver articulos del talle", key="btn_drill_talle"):
                            talle_expr_sql = """COALESCE(
                                NULLIF(RTRIM(a.descripcion_5), ''),
                                CASE WHEN ISNUMERIC(RIGHT(RTRIM(a.codigo_sinonimo), 2)) = 1
                                     THEN RIGHT(RTRIM(a.codigo_sinonimo), 2) END
                            )"""
                            sql_arts_talle = f"""
                                SELECT a.codigo, RTRIM(a.descripcion_1) AS descripcion,
                                    RTRIM(a.descripcion_5) AS talle_desc,
                                    a.precio_fabrica,
                                    ISNULL(s.stk, 0) AS stock,
                                    ISNULL(v.vtas, 0) AS ventas_12m
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
                                    WHERE codigo NOT IN {EXCL_VENTAS}
                                      AND fecha >= DATEADD(month, -{MESES_HISTORIA}, GETDATE())
                                    GROUP BY articulo
                                ) v ON v.articulo = a.codigo
                                WHERE a.estado = 'V'
                                  AND a.rubro = {genero_sel} AND a.subrubro = {sub_sel}
                                  AND {talle_expr_sql} = '{talle_sel}'
                                ORDER BY ISNULL(v.vtas, 0) DESC
                            """
                            with st.spinner(f"Cargando articulos talle {talle_sel}..."):
                                df_arts = query_df(sql_arts_talle)

                            if not df_arts.empty:
                                st.markdown(f"**{len(df_arts)} articulos en talle {talle_sel}**")
                                st.dataframe(
                                    df_arts,
                                    column_config={
                                        'codigo': st.column_config.NumberColumn('Codigo', format="%d"),
                                        'descripcion': st.column_config.TextColumn('Producto', width=280),
                                        'talle_desc': st.column_config.TextColumn('Talle', width=60),
                                        'precio_fabrica': st.column_config.NumberColumn('Precio', format="$%.0f"),
                                        'stock': st.column_config.NumberColumn('Stock', format="%d"),
                                        'ventas_12m': st.column_config.NumberColumn('Vtas 12m', format="%d"),
                                    },
                                    use_container_width=True, hide_index=True,
                                )
                            else:
                                st.info(f"No se encontraron articulos activos para talle {talle_sel}.")
                    else:
                        st.info("Sin datos de talle para esta categoria.")

    # ══════════════════════════════════════════════════════════════
    # TAB 1: DASHBOARD GLOBAL
    # ══════════════════════════════════════════════════════════════
    with tab_dashboard:
        # Alerta ratio C/V y factor estacional
        st.warning(
            f"⚠️ **Alerta: ratio Compras/Ventas = {RATIO_CV_NUEVO:.0%}** — "
            f"Se está comprando {(1-RATIO_CV_NUEVO):.0%} menos de lo que se vende. "
            f"Stock se drena sin reposición. Cobertura global engañosa."
        )
        mes_actual_dash = date.today().month
        factor_dash = ESTACIONALIDAD_MENSUAL[mes_actual_dash]
        st.metric(
            "Factor estacional este mes",
            f"{factor_dash:.0%}",
            delta=f"{'valle' if factor_dash < 0.9 else 'pico' if factor_dash > 1.1 else 'normal'}",
        )

        # Clave unica para detectar cambio de filtro (marca/proveedor)
        _dash_filter_key = f"{modo_filtro}_{locals().get('marca_sel_codigo', '')}_{locals().get('prov_sel_codigo', '')}_{min_ventas}"

        # Calcular datos pesados solo si cambio el filtro
        if st.session_state.get('_dash_filter_key') != _dash_filter_key:
            csrs_dash = df_f['csr'].tolist()

            progress_dash = st.progress(0, text="Cargando velocidad real...")
            vel_tabla = obtener_vel_real_tabla(csrs_dash)

            # Fallback: CSRs no encontrados en la tabla
            csrs_sin_tabla = [c for c in csrs_dash if c not in vel_tabla]
            if csrs_sin_tabla:
                progress_dash.progress(15, text=f"Calculando quiebre para {len(csrs_sin_tabla)} productos...")
                quiebres_fallback = analizar_quiebre_batch(csrs_sin_tabla)
            else:
                quiebres_fallback = {}

            quiebres_dash = {**quiebres_fallback, **vel_tabla}

            progress_dash.progress(40, text="Calculando factor estacional...")
            factores_est = factor_estacional_batch(csrs_dash)

            progress_dash.progress(60, text="Detectando anomalias de stock...")
            anomalias_dash = detectar_anomalias_stock(csrs_dash)

            progress_dash.progress(80, text="Calculando GMROI y precios...")
            precios_venta_dash = obtener_precios_venta_batch(csrs_dash)

            progress_dash.progress(100, text="Listo.")
            progress_dash.empty()

            # Guardar en session_state para reutilizar entre tab switches
            st.session_state['_dash_filter_key'] = _dash_filter_key
            st.session_state['_dash_quiebres'] = quiebres_dash
            st.session_state['_dash_factores_est'] = factores_est
            st.session_state['_dash_anomalias'] = anomalias_dash
            st.session_state['_dash_precios_venta'] = precios_venta_dash

        # Recuperar datos cacheados
        quiebres_dash = st.session_state['_dash_quiebres']
        factores_est = st.session_state['_dash_factores_est']
        anomalias_dash = st.session_state['_dash_anomalias']
        precios_venta_dash = st.session_state['_dash_precios_venta']

        df_f['vel_mes'] = df_f['csr'].map(
            lambda c: quiebres_dash.get(c, {}).get('vel_real', 0)
        )
        df_f['pct_quiebre'] = df_f['csr'].map(
            lambda c: quiebres_dash.get(c, {}).get('pct_quiebre', 0)
        )
        mes_actual = date.today().month
        mes_proxima = (mes_actual % 12) + 1  # mes siguiente (lead time ~30d)
        df_f['s_actual'] = df_f['csr'].map(
            lambda c: factores_est.get(c, {}).get(mes_actual, 1.0)
        )
        df_f['s_proxima'] = df_f['csr'].map(
            lambda c: factores_est.get(c, {}).get(mes_proxima, 1.0)
        )
        df_f['temp_pct'] = df_f['s_proxima']
        df_f['vel_ajustada'] = np.where(
            df_f['s_actual'] > 0.1,
            df_f['vel_mes'] * (df_f['s_proxima'] / df_f['s_actual']),
            df_f['vel_mes']
        )

        df_f['vel_dia'] = df_f['vel_ajustada'] / 30
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

        df_f['stock_ok'] = df_f['csr'].map(
            lambda c: anomalias_dash.get(c, {}).get('nivel', 'OK')
        )
        df_f['anomalia_detalle'] = df_f['csr'].map(
            lambda c: ', '.join(anomalias_dash.get(c, {}).get('anomalias', []))
        )

        # GMROI y Rotación
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
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        criticos = len(df_f[df_f['urgencia'] == 'CRITICO'])
        bajos = len(df_f[df_f['urgencia'] == 'BAJO'])
        # Confianza del modelo: % productos con quiebre moderado (<30%)
        n_alta_conf = len(df_f[df_f['pct_quiebre'] < 30])
        pct_conf = round(n_alta_conf / max(len(df_f), 1) * 100)
        c1.metric("Productos filtrados", len(df_f))
        c2.metric("CRITICOS (<15d)", criticos)
        c3.metric("BAJOS (15-30d)", bajos)
        c4.metric("Stock total (pares)", f"{int(df_f['stock_total'].sum()):,}")
        c5.metric("Ventas 12m (pares)", f"{int(df_f['ventas_12m'].sum()):,}")
        c6.metric("Modelo v3", f"{pct_conf}% conf.",
                  help="Modelo v3: desestacionalización + corrección disponibilidad. "
                       "Target MAPE <15%. Confianza = % productos con <30% quiebre")

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
             'ventas_12m', 'vel_mes', 'vel_ajustada', 'temp_pct', 'pct_quiebre',
             'dias_stock', 'urgencia', 'stock_ok', 'gmroi', 'rotacion']
        ].copy()
        df_top['dias_stock'] = df_top['dias_stock'].round(0).astype(int)
        df_top['vel_mes'] = df_top['vel_mes'].round(1)
        df_top['vel_ajustada'] = df_top['vel_ajustada'].round(1)
        df_top['temp_pct'] = df_top['temp_pct'].round(2)
        # Semáforo stock_ok
        stock_ok_map = {'OK': '🟢', 'REVISAR': '🟡', 'IRREAL': '🔴'}
        df_top['stock_ok'] = df_top['stock_ok'].map(stock_ok_map).fillna('🟢')

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
                'vel_ajustada': st.column_config.NumberColumn('Vel ajust.', format="%.1f",
                    help="Vel real ajustada por factor estacional (temporada proxima / actual)"),
                'temp_pct': st.column_config.NumberColumn('Temp%', format="%.2f",
                    help="Factor estacional prox. mes. <0.5 = fuera de temporada (rojo)"),
                'pct_quiebre': st.column_config.NumberColumn('Quiebre%', format="%.0f%%"),
                'dias_stock': st.column_config.NumberColumn('Dias', format="%d"),
                'urgencia': 'Urgencia',
                'stock_ok': st.column_config.TextColumn('Stock OK', width=60,
                    help="🟢 confiable | 🟡 revisar (remito eliminado) | 🔴 irreal (stock negativo)"),
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

        # ── Contacto proveedor (WhatsApp) ──
        _prov_contacto_id = locals().get('prov_sel_codigo') or locals().get('_prov_para_presup')
        if _prov_contacto_id is not None:
            try:
                _sql_prov_tel = f"""
                    SELECT numero, RTRIM(ISNULL(denominacion,'')) AS nombre,
                           RTRIM(ISNULL(telefono,'')) AS tel,
                           RTRIM(ISNULL(telefono_2,'')) AS tel2,
                           RTRIM(ISNULL(celular,'')) AS cel
                    FROM msgestion01.dbo.proveedores
                    WHERE numero = {int(_prov_contacto_id)}
                """
                _df_prov_tel = query_df(_sql_prov_tel)
                if not _df_prov_tel.empty:
                    _row_prov = _df_prov_tel.iloc[0]
                    _prov_nombre_wa = (_row_prov.get('nombre') or '').strip()
                    # Buscar primer teléfono disponible entre cel, tel, tel2
                    _tel_raw = ''
                    for _campo_tel in ['cel', 'tel', 'tel2']:
                        _val = (_row_prov.get(_campo_tel) or '').strip()
                        if _val and len(_val) >= 6:
                            _tel_raw = _val
                            break
                    if _tel_raw:
                        _tel_clean = _tel_raw.replace(' ', '').replace('-', '').replace('+', '').replace('(', '').replace(')', '')
                        if not _tel_clean.startswith('54'):
                            _tel_clean = '54' + _tel_clean
                        _wa_url = f"https://wa.me/{_tel_clean}?text=Hola, necesito hacer un pedido"
                        st.markdown(f"---")
                        st.markdown(f"📱 Contactar proveedor: [{_prov_nombre_wa}]({_wa_url})")
            except Exception:
                pass  # Sin datos de contacto, no mostrar nada

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
                    # vel_real desde tabla materializada (por talle, 12 chars)
                    sql_vr = f"""
                        SELECT v.codigo, v.vel_real, v.vel_aparente,
                               v.meses_quebrado, v.meses_con_stock, v.factor_quiebre
                        FROM omicronvt.dbo.vel_real_articulo v
                        WHERE LEFT(v.codigo, 10) = '{csr_sel}'
                    """
                    df_vr = query_df(sql_vr)

                    # Stock actual excluyendo depósitos 198, 199
                    sql_stk = f"""
                        SELECT ISNULL(SUM(s.stock_actual), 0) AS stock
                        FROM msgestionC.dbo.stock s
                        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
                        WHERE LEFT(a.codigo_sinonimo, 10) = '{csr_sel}'
                          AND s.deposito NOT IN (198, 199)
                    """
                    df_stk = query_df(sql_stk)
                    stock_actual = float(df_stk.iloc[0]['stock']) if not df_stk.empty else 0

                    if not df_vr.empty:
                        # Promedio vel_real ponderado por vel_aparente (proxy de demanda)
                        df_vr['vel_real'] = df_vr['vel_real'].astype(float)
                        df_vr['vel_aparente'] = df_vr['vel_aparente'].astype(float)
                        peso_total = df_vr['vel_aparente'].sum()
                        if peso_total > 0:
                            vel_real = (df_vr['vel_real'] * df_vr['vel_aparente']).sum() / peso_total
                        else:
                            vel_real = df_vr['vel_real'].mean()
                        meses_q = int(df_vr['meses_quebrado'].max())
                        meses_ok = int(df_vr['meses_con_stock'].max())
                        meses_total = max(meses_q + meses_ok, 1)
                        pct_quiebre = round(meses_q / meses_total * 100, 1)
                    else:
                        # Fallback Python
                        quiebre_fb = analizar_quiebre_batch([csr_sel])
                        fb = quiebre_fb.get(csr_sel, {})
                        vel_real = fb.get('vel_real', 0)
                        pct_quiebre = fb.get('pct_quiebre', 0)
                        meses_q = fb.get('meses_quebrado', 0)

                    q = {
                        'stock_actual': stock_actual,
                        'vel_real': round(vel_real, 2),
                        'pct_quiebre': pct_quiebre,
                        'meses_quebrado': meses_q,
                    }

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
        # ==============================================================
        # SECCION 1: Analisis de presupuesto en PARES por proveedor
        # ==============================================================
        st.subheader("Presupuesto en Pares por Proveedor")
        st.caption("Analisis historico: cuantos pares se vendieron en el mismo periodo del anio anterior, "
                   "distribucion por genero, color, precio techo y curva de talles.")

        _provs_opt = cargar_proveedores_dict()
        if _provs_opt:
            _opciones_prov_opt = sorted(
                [(num, nombre) for num, nombre in _provs_opt.items() if nombre],
                key=lambda x: x[1]
            )
            _labels_prov_opt = ["(seleccionar proveedor)"] + [
                f"{nombre} (#{num})" for num, nombre in _opciones_prov_opt
            ]
            _idx_prov_opt = st.selectbox(
                "Proveedor", range(len(_labels_prov_opt)),
                format_func=lambda i: _labels_prov_opt[i],
                key="opt_pares_prov"
            )

            # Periodo destino
            hoy_opt = date.today()
            _mes_cols = st.columns(2)
            with _mes_cols[0]:
                _mes_inicio_opt = st.number_input(
                    "Mes inicio", min_value=1, max_value=12,
                    value=hoy_opt.month, key="opt_pares_mes_ini"
                )
            with _mes_cols[1]:
                _mes_fin_default = min(hoy_opt.month + 3, 12)
                _mes_fin_opt = st.number_input(
                    "Mes fin", min_value=1, max_value=12,
                    value=_mes_fin_default, key="opt_pares_mes_fin"
                )

            if _idx_prov_opt > 0:
                _prov_num_opt = _opciones_prov_opt[_idx_prov_opt - 1][0]
                _prov_nombre_opt = _opciones_prov_opt[_idx_prov_opt - 1][1]

                with st.spinner(f"Calculando presupuesto en pares para {_prov_nombre_opt}..."):
                    # --- KPIs principales ---
                    _pp = presupuesto_pares(_prov_num_opt, int(_mes_inicio_opt), int(_mes_fin_opt))
                    _dg = distribucion_genero(_prov_num_opt, int(_mes_inicio_opt), int(_mes_fin_opt))

                kpi_c1, kpi_c2, kpi_c3 = st.columns(3)
                kpi_c1.metric("Presupuesto", f"{_pp['total_pares']} pares")
                kpi_c2.metric("Articulos distintos", f"{_pp['articulos_distintos']}")
                kpi_c3.metric("Periodo referencia", _pp['periodo_ref'])

                # --- Desglose por mes ---
                if _pp['por_mes']:
                    _meses_nombres = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',
                                      7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}
                    _df_por_mes = pd.DataFrame([
                        {'Mes': _meses_nombres.get(m, str(m)), 'Pares': p}
                        for m, p in sorted(_pp['por_mes'].items())
                    ])
                    st.bar_chart(_df_por_mes, x='Mes', y='Pares', height=250)

                # --- Distribucion por genero ---
                if _dg:
                    st.markdown("#### Distribucion por Genero")
                    _rows_genero = []
                    for rubro_cod, info in sorted(_dg.items()):
                        _rows_genero.append({
                            'Genero': info['nombre'],
                            'Pares': info['pares'],
                            '%': f"{info['pct']*100:.1f}%",
                            'Pares asignados': round(_pp['total_pares'] * info['pct']),
                        })
                    _df_genero = pd.DataFrame(_rows_genero)
                    st.dataframe(_df_genero, use_container_width=True, hide_index=True)

                    # --- Distribucion por color para cada genero ---
                    st.markdown("#### Distribucion por Color")
                    for rubro_cod, info in sorted(_dg.items()):
                        if info['pares'] <= 0:
                            continue
                        _colores = distribucion_color(
                            _prov_num_opt, rubro_cod,
                            int(_mes_inicio_opt), int(_mes_fin_opt)
                        )
                        if _colores:
                            with st.expander(f"{info['nombre']} — {info['pares']} pares"):
                                _df_color = pd.DataFrame(_colores)
                                _df_color['pct'] = _df_color['pct'].apply(lambda x: f"{x*100:.1f}%")
                                _df_color.columns = ['Color', 'Pares', '%']
                                st.dataframe(_df_color, use_container_width=True, hide_index=True)

                    # --- Precio techo por genero ---
                    st.markdown("#### Precio Techo por Genero")
                    _pt_cols = st.columns(len(_dg) if _dg else 1)
                    for i, (rubro_cod, info) in enumerate(sorted(_dg.items())):
                        _pt = precio_techo(_prov_num_opt, rubro_cod)
                        with _pt_cols[i % len(_pt_cols)]:
                            st.markdown(f"**{info['nombre']}**")
                            if _pt['articulos_analizados'] > 0:
                                st.metric(
                                    f"Precio techo P90",
                                    f"${_pt['p90']:,.0f}",
                                    help=f"P50: ${_pt['p50']:,.0f} | P75: ${_pt['p75']:,.0f} | Max: ${_pt['max']:,.0f} | {_pt['articulos_analizados']} arts"
                                )
                            else:
                                st.info("Sin datos de precio")

                    # --- Curva de talles real + escasez cronica ---
                    st.markdown("#### Curva de Talles Real")
                    for rubro_cod, info in sorted(_dg.items()):
                        if info['pares'] <= 0:
                            continue
                        _ct = curva_talles_real(_prov_num_opt, rubro_cod)
                        if not _ct['curva']:
                            continue

                        with st.expander(f"{info['nombre']} — Talle pico: {_ct['talle_pico']} ({_ct['total_pares']} pares)", expanded=True):
                            # Obtener talles con escasez cronica
                            _esc = talles_escasez_cronica(rubro_cod)
                            _talles_escasez = {e['talle'] for e in _esc} if _esc else set()

                            _rows_talle = []
                            for talle, tdata in _ct['curva'].items():
                                _rows_talle.append({
                                    'Talle': talle,
                                    'Pares': tdata['pares'],
                                    '%': round(tdata['pct'] * 100, 1),
                                    'Escasez cronica': 'SI' if talle in _talles_escasez else '',
                                })
                            _df_talles = pd.DataFrame(_rows_talle)

                            # Bar chart de la curva
                            _df_chart = _df_talles[['Talle', 'Pares']].copy()
                            st.bar_chart(_df_chart, x='Talle', y='Pares', height=300,
                                         color='#1f77b4')

                            # Tabla con escasez marcada
                            def _highlight_escasez(row):
                                if row['Escasez cronica'] == 'SI':
                                    return ['background-color: #ff4b4b; color: white'] * len(row)
                                return [''] * len(row)

                            st.dataframe(
                                _df_talles.style.apply(_highlight_escasez, axis=1),
                                use_container_width=True, hide_index=True,
                            )

                            if _talles_escasez:
                                _esc_sorted = sorted(_talles_escasez)
                                st.warning(
                                    f"Talles con escasez cronica (quebrados >70% del tiempo): "
                                    f"{', '.join(_esc_sorted)}"
                                )

                            # --- Curva ideal sugerida: comparador ---
                            _presup_genero_pares = round(_pp['total_pares'] * _dg[rubro_cod]['pct'])
                            if _presup_genero_pares > 0:
                                st.markdown("##### Curva ideal sugerida")
                                st.caption(
                                    f"Distribucion de **{_presup_genero_pares} pares** "
                                    f"(presupuesto {info['nombre']}) segun demanda real. "
                                    f"Talles con escasez cronica tienen minimo 12 pares."
                                )
                                _MINIMO_ESCASEZ = 12
                                _rows_sugerida = []
                                _total_sugerido_sin_override = 0
                                _overrides = 0
                                for talle, tdata in _ct['curva'].items():
                                    pct_dem = tdata['pct']
                                    pares_proporcional = round(_presup_genero_pares * pct_dem)
                                    es_escasez = talle in _talles_escasez
                                    if es_escasez and pares_proporcional < _MINIMO_ESCASEZ:
                                        pares_sugeridos = _MINIMO_ESCASEZ
                                        _overrides += _MINIMO_ESCASEZ - pares_proporcional
                                    else:
                                        pares_sugeridos = pares_proporcional
                                    _total_sugerido_sin_override += pares_proporcional
                                    _rows_sugerida.append({
                                        'Talle': talle,
                                        '% Demanda': f"{pct_dem * 100:.1f}%",
                                        'Pares sugeridos': pares_sugeridos,
                                        'Escasez?': '⚫ SI' if es_escasez else '',
                                    })

                                _df_sugerida = pd.DataFrame(_rows_sugerida)

                                def _highlight_sugerida(row):
                                    if row['Escasez?'] == '⚫ SI':
                                        return ['background-color: #333333; color: white'] * len(row)
                                    return [''] * len(row)

                                st.dataframe(
                                    _df_sugerida.style.apply(_highlight_sugerida, axis=1),
                                    use_container_width=True, hide_index=True,
                                )

                                _total_sugerido = sum(r['Pares sugeridos'] for r in _rows_sugerida)
                                if _overrides > 0:
                                    st.info(
                                        f"Total sugerido: **{_total_sugerido} pares** "
                                        f"(+{_overrides} pares extra por minimo escasez cronica). "
                                        f"Presupuesto genero: {_presup_genero_pares} pares."
                                    )
                                else:
                                    st.info(f"Total sugerido: **{_total_sugerido} pares** (presupuesto: {_presup_genero_pares})")
        else:
            st.warning("No se pudieron cargar proveedores.")

        st.divider()

        # ==============================================================
        # SECCION 2: Optimizador ROI existente
        # ==============================================================
        st.subheader("Optimizador de Compras por ROI")
        st.caption(f"Presupuesto: **${presupuesto:,.0f}** — Ranking por dias de recupero de inversion")

        if st.button("🚀 Calcular ranking ROI", type="primary", key="btn_roi"):
            with st.spinner("Calculando quiebre, estacionalidad y ROI para todos los productos..."):
                # Incluir productos con ventas significativas O stock bajo/critico
                mask_ventas = df_f['ventas_12m'] >= max(min_ventas, 5)
                mask_lowstock = df_f['dias_stock'] < 60
                df_roi = df_f[mask_ventas | mask_lowstock].copy()

                df_roi['dias_stock'] = df_roi['dias_stock'].fillna(9999)
                if len(df_roi) > 500:
                    df_roi = df_roi.nsmallest(500, 'dias_stock')

                csrs_list = df_roi['csr'].tolist()

                # Batch analysis
                quiebres = analizar_quiebre_batch(csrs_list)
                factores_all = factor_estacional_batch(csrs_list)
                precios_v = obtener_precios_venta_batch(csrs_list)
                df_pend = obtener_pendientes()
                pend_dict = pendientes_por_sinonimo(df_pend)

                rows = []
                _debug_vel_pos = 0
                _debug_pedir_pos = 0
                for _, prod in df_roi.iterrows():
                    csr = prod['csr']
                    q = quiebres.get(csr, {})
                    f_est = factores_all.get(csr, {m: 1.0 for m in range(1, 13)})

                    vel_real = q.get('vel_real', 0)
                    vel_aparente = q.get('vel_aparente', vel_real)
                    factor_max = max(f_est.values()) if f_est else 1.0

                    # Use the BETTER of vel_real and vel_aparente as base
                    vel_base = max(vel_real, vel_aparente)
                    if vel_base <= 0:
                        continue  # truly no sales history
                    _debug_vel_pos += 1
                    vel_diaria = vel_base / 30
                    stock_actual = q.get('stock_actual', prod['stock_total'])
                    cant_pend = pend_dict.get(csr, {}).get('cant_pendiente', 0)
                    stock_disp = stock_actual + cant_pend

                    # Cobertura actual
                    dias_cob = calcular_dias_cobertura(vel_diaria, stock_disp, f_est)

                    # Necesidad: cubrir horizonte_dias
                    necesidad_total = 0
                    hoy = date.today()
                    for d in range(horizonte_dias):
                        fecha = hoy + timedelta(days=d)
                        necesidad_total += vel_diaria * f_est.get(fecha.month, 1.0)

                    pedir = max(0, round(necesidad_total - stock_disp))

                    # Mínimo estacional: si el producto pertenece a un nicho y
                    # estamos dentro de 3 meses de su temporada_esperada, forzar
                    # un pedido mínimo para no quedarse sin stock en temporada
                    if pedir <= 0:
                        prod_rubro = int(prod.get('rubro', 0) or 0)
                        prod_sub = int(prod.get('subrubro', 0) or 0)
                        mes_actual = date.today().month
                        meses_3 = [(mes_actual + i) % 12 or 12 for i in range(3)]
                        forzar = False
                        for _nk, nv in NICHOS_PREDEFINIDOS.items():
                            tmp_esp = nv.get('temporada_esperada', ())
                            if not tmp_esp:
                                continue
                            rubros_n = nv.get('rubros', ())
                            subs_n = nv.get('subrubros', ())
                            if prod_rubro in rubros_n and prod_sub in subs_n:
                                if any(m in tmp_esp for m in meses_3):
                                    forzar = True
                                    break
                        if forzar and vel_aparente > 0:
                            pedir = max(pedir, 6)

                    if pedir <= 0:
                        continue
                    _debug_pedir_pos += 1

                    precio_costo = float(prod['precio_fabrica'] or 0)
                    if precio_costo <= 0:
                        continue

                    precio_venta = precios_v.get(csr, precio_costo * 2)

                    roi = calcular_roi(precio_costo, precio_venta, vel_diaria, f_est,
                                       pedir, stock_disp, dias_pago=dias_pago)

                    rows.append({
                        'csr': csr,
                        'descripcion': prod['descripcion'][:50],
                        'marca': prod['marca_desc'],
                        'proveedor': prod['prov_nombre'],
                        'stock': int(stock_actual),
                        'pendiente': int(cant_pend),
                        'vel_real': round(vel_real, 1),
                        'vel_base': vel_base,
                        'f_est': f_est,
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
                    st.warning(
                        f"No se encontraron productos que necesiten reposicion. "
                        f"Debug: {len(df_roi)} productos analizados, "
                        f"{_debug_vel_pos} con velocidad > 0, "
                        f"{_debug_pedir_pos} con pedir > 0."
                    )
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
                dentro.drop(columns=['acum_inversion', 'dentro_presupuesto', 'csr', 'vel_base', 'f_est']),
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
                        fuera.drop(columns=['acum_inversion', 'dentro_presupuesto', 'csr', 'vel_base', 'f_est']),
                        use_container_width=True, hide_index=True,
                    )

            # ── Plan de entregas mensuales ──
            _MESES_NOMBRE = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',
                             7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}
            productos_pedir = dentro[dentro['pedir'] > 0]
            if len(productos_pedir) > 0:
                with st.expander(f"Plan de entregas mensuales ({len(productos_pedir)} productos)", expanded=False):
                    mes_inicio = date.today().month
                    n_entregas = max(1, min(12, horizonte_dias // 30))
                    for _, row in productos_pedir.iterrows():
                        plan = proyectar_entregas_mensuales(
                            pedir_total=row['pedir'],
                            vel_mensual=row['vel_base'],
                            stock_actual=row['stock'],
                            f_est=row['f_est'],
                            mes_inicio=mes_inicio,
                            n_entregas=n_entregas,
                        )
                        if plan:
                            st.markdown(f"**{row['descripcion']}** — Pedir: {row['pedir']} pares")
                            df_plan = pd.DataFrame(plan)
                            df_plan['mes'] = df_plan['mes'].map(_MESES_NOMBRE)
                            st.dataframe(
                                df_plan,
                                column_config={
                                    'mes': 'Mes',
                                    'entrega_pares': st.column_config.NumberColumn('Entrega', format="%d"),
                                    'demanda_mes': st.column_config.NumberColumn('Demanda', format="%d"),
                                    'stock_proyectado': st.column_config.NumberColumn('Stock proy.', format="%d"),
                                },
                                use_container_width=True, hide_index=True,
                            )

        st.divider()

        # ==============================================================
        # SECCION 3: Resumen de Pedido Sugerido
        # ==============================================================
        st.subheader("📋 Resumen de Pedido Sugerido")
        st.caption("Combina presupuesto, distribucion por genero, colores, curva de talles y escasez "
                   "en un pedido concreto editable y descargable.")

        # Solo mostrar si hay un proveedor seleccionado Y presupuesto calculado en SECCION 1
        _show_pedido = (locals().get('_pp') and locals().get('_dg')
                        and locals().get('_idx_prov_opt', 0) > 0)
        if _show_pedido and _pp['total_pares'] > 0:
            _prov_num_ped = _opciones_prov_opt[_idx_prov_opt - 1][0]
            _prov_nombre_ped = _opciones_prov_opt[_idx_prov_opt - 1][1]

            # --- Lookup artículos por rubro+talle (una sola query) ---
            try:
                _sql_arts = f"""
                    SELECT a.rubro,
                           COALESCE(NULLIF(RTRIM(a.descripcion_5),''),
                               CASE WHEN ISNUMERIC(RIGHT(RTRIM(a.codigo_sinonimo),2))=1
                                    THEN RIGHT(RTRIM(a.codigo_sinonimo),2) END) AS talle,
                           RTRIM(a.descripcion_1) AS descripcion,
                           a.codigo_sinonimo
                    FROM msgestion01art.dbo.articulo a
                    WHERE a.proveedor = {_prov_num_ped}
                      AND a.estado = 'V'
                      AND ISNULL(a.codigo_sinonimo,'') != ''
                """
                _df_arts_lookup = query_df(_sql_arts)
                # Agrupar: rubro+talle → lista única de descripciones (sin el talle al final)
                _arts_map = {}
                for _, _r in _df_arts_lookup.iterrows():
                    _key = (int(_r['rubro']) if _r['rubro'] else 0, str(_r['talle'] or ''))
                    # Descripción limpia: quitar último token si es el talle
                    _desc = str(_r['descripcion'] or '').strip()
                    _words = _desc.split()
                    if _words and _words[-1] == str(_r['talle']):
                        _desc = ' '.join(_words[:-1])
                    if _key not in _arts_map:
                        _arts_map[_key] = set()
                    _arts_map[_key].add(_desc)
            except Exception:
                _arts_map = {}

            # --- Tabla resumen por genero ---
            st.markdown("#### Resumen por Genero")
            _resumen_rows = []
            _pedido_detalle_all = []  # para el data_editor y Excel

            for rubro_cod, info in sorted(_dg.items()):
                if info['pares'] <= 0:
                    continue

                pares_genero = round(_pp['total_pares'] * info['pct'])

                # Top 3 colores
                _colores_g = distribucion_color(
                    _prov_num_ped, rubro_cod,
                    int(_mes_inicio_opt), int(_mes_fin_opt)
                )
                top3_colores = ""
                if _colores_g:
                    top3 = _colores_g[:3]
                    top3_colores = ", ".join(
                        f"{c['color']} ({c['pct']*100:.0f}%)" for c in top3
                    )

                # Curva de talles
                _ct_g = curva_talles_real(_prov_num_ped, rubro_cod)
                talle_pico = _ct_g.get('talle_pico', '-')

                # Escasez
                _esc_g = talles_escasez_cronica(rubro_cod)
                talles_esc = ", ".join(sorted(e['talle'] for e in _esc_g)) if _esc_g else "-"
                _talles_esc_set = {e['talle'] for e in _esc_g} if _esc_g else set()

                _resumen_rows.append({
                    'Genero': info['nombre'],
                    'Pares asignados': pares_genero,
                    'Top 3 colores': top3_colores,
                    'Talle pico': talle_pico,
                    'Talles escasez': talles_esc,
                })

                # Construir detalle genero x talle para editor
                _MINIMO_ESCASEZ = 12
                if _ct_g['curva']:
                    for talle, tdata in _ct_g['curva'].items():
                        pares_prop = round(pares_genero * tdata['pct'])
                        es_esc = talle in _talles_esc_set
                        if es_esc and pares_prop < _MINIMO_ESCASEZ:
                            pares_prop = _MINIMO_ESCASEZ
                        _arts_talle = _arts_map.get((rubro_cod, str(talle)), set())
                        _arts_str = ' / '.join(sorted(_arts_talle)[:3]) if _arts_talle else ''
                        _pedido_detalle_all.append({
                            'Articulos': _arts_str,
                            'Genero': info['nombre'],
                            'Rubro': rubro_cod,
                            'Talle': talle,
                            '% Demanda': round(tdata['pct'] * 100, 1),
                            'Pares': pares_prop,
                            'Escasez': 'SI' if es_esc else '',
                        })

            # Mostrar resumen
            _df_resumen = pd.DataFrame(_resumen_rows)
            _total_asignado = _df_resumen['Pares asignados'].sum() if not _df_resumen.empty else 0
            st.dataframe(_df_resumen, use_container_width=True, hide_index=True)
            st.info(f"**Total pares asignados: {_total_asignado}** — Presupuesto pares: {_pp['total_pares']}")

            # --- Data editor para ajuste manual ---
            if _pedido_detalle_all:
                st.markdown("#### Detalle Editable por Talle")
                st.caption("Ajusta los pares por talle. El total se recalcula automaticamente.")

                _df_detalle = pd.DataFrame(_pedido_detalle_all)
                _df_editado = st.data_editor(
                    _df_detalle,
                    column_config={
                        'Articulos': st.column_config.TextColumn('Artículos', disabled=True, width=250),
                        'Genero': st.column_config.TextColumn('Genero', disabled=True, width=90),
                        'Rubro': st.column_config.NumberColumn('Rubro', disabled=True, width=60),
                        'Talle': st.column_config.TextColumn('Talle', disabled=True, width=60),
                        '% Demanda': st.column_config.NumberColumn('% Dem.', disabled=True, format="%.1f%%", width=70),
                        'Pares': st.column_config.NumberColumn('Pares', min_value=0, step=1, width=70),
                        'Escasez': st.column_config.TextColumn('Escasez', disabled=True, width=70),
                    },
                    use_container_width=True, hide_index=True,
                    key="pedido_editor",
                    num_rows="fixed",
                )

                # Running total
                _total_editado = int(_df_editado['Pares'].sum())
                _diff = _total_editado - _pp['total_pares']
                _diff_txt = f"(+{_diff})" if _diff > 0 else f"({_diff})" if _diff < 0 else "(=)"
                _color = "🔴" if abs(_diff) > _pp['total_pares'] * 0.1 else "🟢"
                st.metric(
                    "Total pares editado",
                    f"{_total_editado} pares {_diff_txt}",
                    delta=f"{_diff} vs presupuesto",
                    delta_color="inverse" if _diff > 0 else "normal",
                )

                # --- Boton descargar Excel ---
                st.markdown("#### Descargar Pedido")
                _fecha_pedido = date.today().strftime("%Y-%m-%d")

                # Precio techo por rubro para el resumen
                _precios_resumen = {}
                for rubro_cod, info in sorted(_dg.items()):
                    if info['pares'] > 0:
                        _pt_r = precio_techo(_prov_num_ped, rubro_cod)
                        _precios_resumen[info['nombre']] = _pt_r.get('p90', 0)

                if st.button("📥 Descargar pedido en Excel", type="primary", key="btn_descargar_pedido"):
                    try:
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            # Sheet 1: Resumen
                            resumen_data = {
                                'Campo': [
                                    'Proveedor', 'Codigo proveedor', 'Fecha',
                                    'Presupuesto pares', 'Total pares pedido',
                                    'Condicion de pago', 'Periodo destino',
                                ],
                                'Valor': [
                                    _prov_nombre_ped, _prov_num_ped, _fecha_pedido,
                                    _pp['total_pares'], _total_editado,
                                    f"{dias_pago} dias", f"Mes {int(_mes_inicio_opt)} a {int(_mes_fin_opt)}",
                                ],
                            }
                            # Agregar precios techo
                            for gen_name, p90 in _precios_resumen.items():
                                resumen_data['Campo'].append(f'Precio techo {gen_name}')
                                resumen_data['Valor'].append(f"${p90:,.0f}" if p90 else "Sin datos")

                            pd.DataFrame(resumen_data).to_excel(
                                writer, sheet_name='Resumen', index=False
                            )

                            # Sheet 2: Detalle
                            _df_export = _df_editado[_df_editado['Pares'] > 0].copy()
                            _df_export.to_excel(
                                writer, sheet_name='Detalle', index=False
                            )

                        output.seek(0)
                        st.download_button(
                            label="💾 Guardar archivo",
                            data=output.getvalue(),
                            file_name=f"pedido_{_prov_nombre_ped.replace(' ','_')}_{_fecha_pedido}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_pedido_xlsx",
                        )
                        st.success("Pedido generado correctamente.")
                    except Exception as e:
                        st.error(f"Error generando Excel: {e}")
        else:
            st.info("Selecciona un proveedor y calcula el presupuesto en pares (arriba) para generar el pedido sugerido.")

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
        _hoy = date.today()
        _h6 = (_hoy - relativedelta(months=6)).strftime('%b %Y')
        _h3 = (_hoy - relativedelta(months=3)).strftime('%b %Y')
        _h0 = _hoy.strftime('%b %Y')
        st.caption(
            f"Compara los ultimos 3 meses ({_h3}→{_h0}) vs los 3 anteriores ({_h6}→{_h3}). "
            f"Productos que aceleran = senal temprana de demanda. "
            f"No es ranking de mas vendidos, es lo que esta CRECIENDO."
        )

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
                    clasif_disp = sorted(df_e['clasificacion'].dropna().unique())
                    clasif_sel = st.multiselect("Clasificacion", clasif_disp,
                                                 default=clasif_disp, key="emerg_clasif")
                with ef2:
                    generos_e = sorted(df_e['genero'].dropna().unique())
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
                    dias = int(t['dias_stock']) if pd.notna(t['dias_stock']) else 0
                    stock = int(t['stock_actual']) if pd.notna(t['stock_actual']) else 0
                    stock_warn = " ⚠️ STOCK BAJO" if dias < 30 else ""
                    vel = t['vel_mensual'] if pd.notna(t['vel_mensual']) else 0
                    acel = t['aceleracion'] if pd.notna(t['aceleracion']) else 0
                    vs_c = t['vs_categoria'] if pd.notna(t['vs_categoria']) else 0
                    st.markdown(
                        f"{emoji} **{t['descripcion'][:50]}** ({t['marca_desc']}) — "
                        f"Vel: {vel:.0f}/mes, Acelerac: {acel:+.0f}%, "
                        f"vs cat: {vs_c:.1f}x, Stock: {stock} "
                        f"({dias}d){stock_warn}"
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

        subtab_simular, subtab_roi, subtab_jit = st.tabs([
            "📊 Simulador de Recupero",
            "⚡ Pedido desde ROI",
            "🔄 Reposición JIT",
        ])

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

            # ── CONFIRMAR E INSERTAR (dentro de subtab_simular) ──
            st.divider()
            st.subheader("🛒 Confirmar e Insertar Pedido en ERP")

            # Verificar que hay líneas válidas con codigo_sinonimo
            _sim_actual = st.session_state.get('sim_pedido_df', pd.DataFrame())
            _lineas_insertar = _sim_actual[
                (_sim_actual['cantidad'] > 0)
                & (_sim_actual['precio_costo'] > 0)
                & (_sim_actual.get('codigo_sinonimo', pd.Series(dtype=str)).str.len() >= 10)
            ] if not _sim_actual.empty else pd.DataFrame()

            if _lineas_insertar.empty:
                st.info("💡 Primero cargá el pedido en la tabla de arriba (con codigo_sinonimo de 10+ dígitos) y simulá el recupero.")
            else:
                _total_pares_ins = int(_lineas_insertar['cantidad'].sum())
                _total_monto_ins = float((_lineas_insertar['cantidad'] * _lineas_insertar['precio_costo']).sum())

                _col_ins1, _col_ins2, _col_ins3 = st.columns(3)
                with _col_ins1:
                    # Cargar proveedores para el selectbox
                    try:
                        _provs_dict_ins = cargar_proveedores_dict()
                        _provs_list_ins = sorted(_provs_dict_ins.keys())
                        _provs_labels_ins = [f"{_provs_dict_ins[p]} (#{p})" for p in _provs_list_ins]
                        _prov_ins_idx = st.selectbox(
                            "Proveedor", range(len(_provs_list_ins)),
                            format_func=lambda i: _provs_labels_ins[i],
                            key="sim_prov_ins_sel"
                        )
                        _prov_ins_id = _provs_list_ins[_prov_ins_idx]
                        _prov_ins_nombre = _provs_dict_ins.get(_prov_ins_id, f"#{_prov_ins_id}")
                    except Exception:
                        _prov_ins_id = 0
                        _prov_ins_nombre = "Sin proveedor"
                        st.warning("No se pudieron cargar proveedores.")
                with _col_ins2:
                    _empresa_ins = st.selectbox("Empresa", ["CALZALINDO", "H4"], key="sim_empresa_ins")
                with _col_ins3:
                    _fecha_ent_ins = st.date_input(
                        "Fecha entrega", date.today() + timedelta(days=30), key="sim_fecha_ent_ins"
                    )

                _col_m1, _col_m2 = st.columns(2)
                _col_m1.metric("Total pares", f"{_total_pares_ins:,}")
                _col_m2.metric("Monto s/IVA", f"${_total_monto_ins:,.0f}")

                _obs_ins = st.text_area(
                    "Observaciones",
                    f"Pedido desde simulador de recupero. {_total_pares_ins} pares.",
                    key="sim_obs_ins"
                )

                st.warning(
                    f"Se insertará pedido de **{_total_pares_ins} pares** "
                    f"(${_total_monto_ins:,.0f}) para **{_prov_ins_nombre}** en **{_empresa_ins}**"
                )

                _chk_confirmar_sim = st.checkbox(
                    "Confirmo que los datos son correctos — insertar en producción",
                    key="chk_confirmar_sim"
                )

                if st.button(
                    "⚡ INSERTAR EN ERP",
                    type="primary",
                    use_container_width=True,
                    key="btn_insert_sim",
                    disabled=(not _chk_confirmar_sim or _prov_ins_id == 0)
                ):
                    with st.spinner(f"Resolviendo artículos e insertando {_total_pares_ins} pares..."):
                        try:
                            # Resolver codigo interno desde codigo_sinonimo
                            _csr_list = list(_lineas_insertar['codigo_sinonimo'].unique())
                            _csr_in = ",".join(f"'{c.strip()}'" for c in _csr_list if c)
                            _df_codigos = query_df(f"""
                                SELECT DISTINCT
                                    RTRIM(codigo_sinonimo) AS csr,
                                    codigo,
                                    RTRIM(ISNULL(descripcion_1,'')) AS descripcion_1
                                FROM msgestion01art.dbo.articulo
                                WHERE RTRIM(codigo_sinonimo) IN ({_csr_in})
                                  AND estado = 'V'
                            """)
                            _csr_to_cod = {}
                            _csr_to_desc = {}
                            if not _df_codigos.empty:
                                for _, _rc in _df_codigos.iterrows():
                                    _csr_to_cod[_rc['csr'].strip()] = int(_rc['codigo'])
                                    _csr_to_desc[_rc['csr'].strip()] = str(_rc['descripcion_1']).strip()

                            # Construir DataFrame de renglones en el formato de insertar_pedido_produccion
                            _renglones_rows = []
                            _skipped = []
                            for _, _lr in _lineas_insertar.iterrows():
                                _csr_clean = str(_lr['codigo_sinonimo']).strip()
                                _cod = _csr_to_cod.get(_csr_clean)
                                if not _cod:
                                    _skipped.append(_csr_clean)
                                    continue
                                _desc = _csr_to_desc.get(_csr_clean, '')
                                _talle = str(_lr.get('talle', '')).strip()
                                _renglones_rows.append({
                                    'codigo': _cod,
                                    'codigo_sinonimo': _csr_clean,
                                    'descripcion_1': _desc,
                                    'talle': _talle,
                                    'precio_fabrica': float(_lr['precio_costo']),
                                    'pedir': int(_lr['cantidad']),
                                })

                            if _skipped:
                                st.warning(
                                    f"No se encontraron códigos para {len(_skipped)} CSR: "
                                    + ", ".join(_skipped[:5])
                                )

                            if not _renglones_rows:
                                st.error("No se pudo resolver ningún código de artículo. Verificá los sinónimos.")
                            else:
                                _df_renglones_ins = pd.DataFrame(_renglones_rows)
                                _numero_ins, _msg_ins = insertar_pedido_produccion(
                                    _prov_ins_id,
                                    _empresa_ins,
                                    _df_renglones_ins,
                                    _obs_ins,
                                    _fecha_ent_ins
                                )
                                if _numero_ins:
                                    st.success(f"✅ {_msg_ins}")
                                    guardar_log({
                                        'fecha': str(datetime.now()),
                                        'numero': _numero_ins,
                                        'proveedor': _prov_ins_nombre,
                                        'prov_id': _prov_ins_id,
                                        'empresa': _empresa_ins,
                                        'pares': _total_pares_ins,
                                        'monto': _total_monto_ins,
                                        'presupuesto': _total_monto_ins,
                                        'estado': 'insertado',
                                        'email_enviado': False,
                                        'confirmado': False,
                                    })
                                    st.session_state['ultimo_pedido'] = _numero_ins
                                    st.balloons()
                                else:
                                    st.error(f"❌ {_msg_ins}")
                        except Exception as _e_ins:
                            st.error(f"❌ Error al insertar: {_e_ins}")

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
                    # Proveedores: los del ranking + todos los que entregan esta marca
                    provs_ranking = set(dentro['proveedor'].dropna().unique())
                    # Buscar todos los proveedores que tienen artículos de esta marca
                    try:
                        _marca_actual = dentro['marca'].dropna().iloc[0] if 'marca' in dentro.columns else None
                        if _marca_actual:
                            _provs_marca = query_df(f"""
                                SELECT DISTINCT a.proveedor, p.denominacion
                                FROM msgestion01art.dbo.articulo a
                                JOIN MSGESTION01.dbo.proveedores p ON p.numero = a.proveedor
                                WHERE a.marca = {int(_marca_actual)} AND a.estado = 'V'
                                  AND (SELECT SUM(stock_actual) FROM msgestionC.dbo.stock
                                       WHERE articulo = a.codigo AND deposito IN (0,1)) > 0
                            """)
                            if not _provs_marca.empty:
                                _prov_map = dict(zip(_provs_marca['proveedor'], _provs_marca['denominacion'].str.strip()))
                            else:
                                _prov_map = {}
                        else:
                            _prov_map = {}
                    except Exception:
                        _prov_map = {}

                    # Combinar: proveedores del ranking + proveedores de la marca
                    provs_all = sorted(provs_ranking | set(_prov_map.keys()))
                    _prov_desc = cargar_proveedores_dict()  # {codigo: nombre}
                    _prov_desc.update(_prov_map)
                    provs_labels = [f"{_prov_desc.get(p, '?')} (#{p})" for p in provs_all]

                    sel_prov_idx = st.selectbox("Proveedor para el pedido",
                                                range(len(provs_all)),
                                                format_func=lambda i: provs_labels[i],
                                                key="prov_pedido_sel")
                    prov_pedido = provs_all[sel_prov_idx]

                    # Mostrar TODOS los productos (no filtrar por proveedor del artículo)
                    # El usuario elige a quién comprarle, independiente de cómo esté cargado
                    df_prov = dentro.copy()

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

                        # Export Excel
                        if total_pares > 0:
                            excel_buf = io.BytesIO()
                            with pd.ExcelWriter(excel_buf, engine='openpyxl') as writer:
                                df_tp.to_excel(writer, sheet_name='Pedido', index=False)
                                ws = writer.sheets['Pedido']
                                for col in ws.columns:
                                    max_len = max(len(str(cell.value or '')) for cell in col)
                                    ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)
                            st.download_button(
                                "📥 Descargar pedido Excel",
                                data=excel_buf.getvalue(),
                                file_name=f"pedido_{prov_pedido.replace(' ', '_')}_{date.today().strftime('%Y%m%d')}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )

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

                        # prov_pedido ya es el código numérico del proveedor seleccionado
                        prov_id = int(prov_pedido)
                        prov_pedido_nombre = _prov_desc.get(prov_id, f"Proveedor #{prov_id}")

                        col_ins, col_email = st.columns(2)

                        with col_ins:
                            if total_pares > 0 and prov_id:
                                # Paso 1: resumen y confirmación
                                renglones_activos = df_tp[df_tp['pedir'] > 0]
                                st.info(
                                    f"**Resumen pedido**\n\n"
                                    f"- Proveedor: **{prov_pedido_nombre}** (#{prov_id})\n"
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
                                        f"{empresa} para {prov_pedido_nombre}..."
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
                                                    'proveedor': prov_pedido_nombre,
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

        # ── SUBTAB: REPOSICIÓN JIT ──
        with subtab_jit:
            st.subheader("🔄 Monitor de Reposición JIT")
            st.caption(
                "Dado el stock actual y el lead time del proveedor, "
                "el motor calcula si hay que pedir hoy y cuánto."
            )

            # ── Controles ──
            jit_col1, jit_col2, jit_col3 = st.columns(3)

            with jit_col1:
                # Selectbox con todos los proveedores que tienen lead time configurado
                _prov_dict_jit = cargar_proveedores_dict()
                _jit_opciones = sorted(LEAD_TIMES.keys())
                _jit_labels = [
                    f"{_prov_dict_jit.get(p, '?')} (#{p}) — {LEAD_TIMES[p]}d"
                    for p in _jit_opciones
                ]
                _jit_sel_idx = st.selectbox(
                    "Proveedor",
                    range(len(_jit_opciones)),
                    format_func=lambda i: _jit_labels[i],
                    key="jit_prov_sel",
                )
                jit_proveedor = _jit_opciones[_jit_sel_idx]

            with jit_col2:
                jit_horizonte = st.slider(
                    "Horizonte días", min_value=30, max_value=180,
                    value=90, step=15, key="jit_horizonte"
                )

            with jit_col3:
                jit_nivel_srv = st.select_slider(
                    "Nivel de servicio",
                    options=[0.85, 0.90, 0.95, 0.99],
                    value=0.95,
                    format_func=lambda v: f"{int(v*100)}%",
                    key="jit_nivel_srv",
                )

            # ── Filtro opcional por subrubro ──
            _subr_opts = {
                0: "Todos",
                60: "Pantuflas (60)",
                11: "Zapatillas Running (11)",
                12: "Zapatillas Training (12)",
                13: "Zapatillas Casual (13)",
                20: "Calzado Dama (20)",
                30: "Calzado Niños (30)",
                50: "Ojotas/Chinelas (50)",
                29: "Medias/Soquetes (29)",
            }
            jit_subrubro = st.selectbox(
                "Filtrar subrubro",
                options=list(_subr_opts.keys()),
                format_func=lambda x: _subr_opts[x],
                key="jit_subrubro",
            )

            st.divider()

            # ── Cargar datos ──
            with st.spinner("Cargando stock y velocidades..."):
                df_jit_stock = cargar_stock_proveedor(jit_proveedor)
                if jit_subrubro != 0 and not df_jit_stock.empty and 'subrubro' in df_jit_stock.columns:
                    df_jit_stock = df_jit_stock[df_jit_stock['subrubro'] == jit_subrubro]

            if df_jit_stock.empty:
                st.warning(
                    "No se encontraron artículos activos para este proveedor. "
                    "Verificá que los artículos tengan código sinónimo y estado='V'."
                )
            else:
                # Factores estacionales por artículo — para ajuste forward-looking
                with st.spinner("Calculando estacionalidad por artículo..."):
                    _csrs_jit = df_jit_stock['codigo_sinonimo'].dropna().tolist()
                    _factores_jit = factor_estacional_batch(_csrs_jit) if _csrs_jit else {}

                df_jit = calcular_decision_reposicion(
                    df_jit_stock, jit_proveedor,
                    horizonte_dias=jit_horizonte,
                    nivel_servicio=jit_nivel_srv,
                    factores_est=_factores_jit,
                )

                # ── Métricas resumen ──
                _jit_rojos    = (df_jit['urgencia'] == 'ROJO').sum()
                _jit_amarillos = (df_jit['urgencia'] == 'AMARILLO').sum()
                _jit_verdes   = (df_jit['urgencia'] == 'VERDE').sum()
                _jit_pares    = int(
                    df_jit[df_jit['necesita_pedido']]['cantidad_sugerida'].sum()
                )
                _jit_lead     = LEAD_TIMES.get(jit_proveedor, LEAD_TIME_DEFAULT)

                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("🔴 Urgente (pedir ya)",  _jit_rojos)
                mc2.metric("🟡 Próximamente",        _jit_amarillos)
                mc3.metric("📦 Pares sugeridos",     f"{_jit_pares:,}")
                mc4.metric("⏱ Lead time",            f"{_jit_lead} días")

                st.divider()

                # ── Tabla con artículos que tienen demanda ──
                _df_show_jit = df_jit[df_jit['vel_diaria'] > 0].copy()

                if _df_show_jit.empty:
                    st.info("Todos los artículos de este proveedor tienen velocidad = 0.")
                else:
                    _cols_jit = [
                        'descripcion', 'stock_actual', 'dias_hasta_stockout',
                        'vel_diaria', 'factor_est', 'punto_reorden', 'urgencia', 'cantidad_sugerida',
                    ]
                    # Renombrar para mejor legibilidad
                    _rename_jit = {
                        'descripcion':        'Descripción',
                        'stock_actual':       'Stock',
                        'dias_hasta_stockout': 'Días stock',
                        'vel_diaria':         'Vel/día',
                        'factor_est':         'Factor est.',
                        'punto_reorden':      'Pto. reorden',
                        'urgencia':           'Urgencia',
                        'cantidad_sugerida':  'A pedir',
                    }
                    _df_table_jit = (
                        _df_show_jit[_cols_jit]
                        .rename(columns=_rename_jit)
                        .sort_values('Días stock')
                        .reset_index(drop=True)
                    )

                    # Color-coding por urgencia
                    def _color_urgencia(val):
                        _palette = {
                            'ROJO':     'background-color: #ffcccc; color: #a00',
                            'AMARILLO': 'background-color: #fff3cd; color: #856404',
                            'VERDE':    'background-color: #d4edda; color: #155724',
                        }
                        return _palette.get(val, '')

                    st.dataframe(
                        _df_table_jit.style.applymap(
                            _color_urgencia, subset=['Urgencia']
                        ).format({
                            'Vel/día':      '{:.2f}',
                            'Factor est.':  '{:.2f}x',
                            'Días stock':   '{:,}',
                            'Stock':        '{:,}',
                            'A pedir':      '{:,}',
                            'Pto. reorden': '{:,}',
                        }),
                        use_container_width=True,
                        hide_index=True,
                    )

                    st.caption(
                        f"Total artículos con demanda: {len(_df_table_jit)} | "
                        f"Lead time configurado: {_jit_lead} días | "
                        f"Horizonte objetivo: {jit_horizonte} días"
                    )

                    st.divider()

                    # ── Botón para pasar urgentes a session_state ──
                    _urgentes_jit = df_jit[
                        df_jit['necesita_pedido'] & (df_jit['cantidad_sugerida'] > 0)
                    ]
                    if not _urgentes_jit.empty:
                        if st.button(
                            f"📋 Armar pedido con {len(_urgentes_jit)} SKUs "
                            f"urgentes/amarillos ({int(_urgentes_jit['cantidad_sugerida'].sum())} pares)",
                            type="primary",
                            key="btn_jit_armar_pedido",
                        ):
                            st.session_state['jit_pedido_df'] = _urgentes_jit.copy()
                            st.session_state['jit_pedido_proveedor'] = jit_proveedor
                            st.session_state['jit_pedido_confirmado'] = False
                            st.success(
                                f"Pedido preparado: {len(_urgentes_jit)} SKUs, "
                                f"{int(_urgentes_jit['cantidad_sugerida'].sum())} pares. "
                                "Revisá y confirmá abajo."
                            )
                    else:
                        st.info(
                            "No hay artículos que requieran pedido hoy "
                            f"(stock cubre más de {_jit_lead} días en todos los casos)."
                        )

                    # ── Flujo de confirmación e INSERT en ERP ────────────────
                    if st.session_state.get('jit_pedido_df') is not None:
                        _jit_df_edit = st.session_state['jit_pedido_df']
                        _jit_prov_id = st.session_state.get('jit_pedido_proveedor', jit_proveedor)
                        _jit_prov_cfg = PROVEEDORES.get(_jit_prov_id, {})
                        _jit_prov_nombre = _jit_prov_cfg.get('nombre') or _prov_dict_jit.get(_jit_prov_id, f'Proveedor #{_jit_prov_id}')
                        _jit_empresa_cfg = _jit_prov_cfg.get('empresa', EMPRESA_DEFAULT)

                        st.subheader("✏️ Revisar y ajustar cantidades")

                        # Editor de cantidades
                        _edit_cols = ['descripcion', 'urgencia', 'stock_actual', 'cantidad_sugerida']
                        _edit_cols_exist = [c for c in _edit_cols if c in _jit_df_edit.columns]
                        _df_editable = _jit_df_edit[_edit_cols_exist].copy()
                        _df_editable = _df_editable.rename(columns={
                            'descripcion':       'Descripción',
                            'urgencia':          'Urgencia',
                            'stock_actual':      'Stock actual',
                            'cantidad_sugerida': 'Cantidad a pedir',
                        })

                        _df_edited = st.data_editor(
                            _df_editable,
                            column_config={
                                'Descripción':     st.column_config.TextColumn(disabled=True),
                                'Urgencia':        st.column_config.TextColumn(disabled=True),
                                'Stock actual':    st.column_config.NumberColumn(disabled=True),
                                'Cantidad a pedir': st.column_config.NumberColumn(
                                    min_value=0, step=1, format="%d"
                                ),
                            },
                            hide_index=True,
                            use_container_width=True,
                            key="jit_editor_cantidades",
                        )

                        # Si el proveedor no está en config, pedir empresa manualmente
                        if _jit_empresa_cfg not in ('H4', 'CALZALINDO'):
                            _jit_empresa_sel = st.selectbox(
                                "Empresa destino",
                                options=['H4', 'CALZALINDO'],
                                key="jit_empresa_manual",
                            )
                        else:
                            _jit_empresa_sel = _jit_empresa_cfg

                        _fecha_jit = st.date_input(
                            "Fecha del pedido",
                            value=date.today(),
                            key="jit_fecha_pedido",
                        )
                        _obs_jit = st.text_input(
                            "Observaciones",
                            value=f"Reposicion JIT - {_jit_prov_nombre}",
                            key="jit_obs_pedido",
                        )

                        _pares_editados = int(_df_edited['Cantidad a pedir'].sum())
                        _skus_editados  = int((_df_edited['Cantidad a pedir'] > 0).sum())

                        st.info(
                            f"Proveedor: **{_jit_prov_nombre}** | "
                            f"Empresa: **{_jit_empresa_sel}** | "
                            f"SKUs: **{_skus_editados}** | "
                            f"Pares: **{_pares_editados:,}**"
                        )

                        _col_btn1, _col_btn2 = st.columns([2, 1])
                        with _col_btn1:
                            _btn_confirmar = st.button(
                                f"✅ Confirmar e insertar en ERP ({_pares_editados:,} pares)",
                                type="primary",
                                key="btn_jit_confirmar_erp",
                                disabled=(_pares_editados == 0),
                            )
                        with _col_btn2:
                            if st.button("❌ Cancelar pedido", key="btn_jit_cancelar"):
                                del st.session_state['jit_pedido_df']
                                if 'jit_pedido_proveedor' in st.session_state:
                                    del st.session_state['jit_pedido_proveedor']
                                if 'jit_pedido_confirmado' in st.session_state:
                                    del st.session_state['jit_pedido_confirmado']
                                st.rerun()

                        if _btn_confirmar and _pares_editados > 0:
                            # Construir renglones solo con cantidad > 0
                            _renglones_jit = []
                            _orig_idx = list(_jit_df_edit.index)
                            for _i_row, (_idx, _row_ed) in enumerate(
                                zip(_orig_idx, _df_edited.itertuples())
                            ):
                                _cant = int(getattr(_row_ed, 'Cantidad_a_pedir', 0))
                                if _cant <= 0:
                                    continue
                                _orig_row = _jit_df_edit.loc[_idx]
                                _precio = float(_orig_row.get('precio_venta', 0) if hasattr(_orig_row, 'get') else _orig_row['precio_venta']) if 'precio_venta' in _orig_row.index else 0.0
                                _desc = str(_orig_row.get('descripcion', '') if hasattr(_orig_row, 'get') else _orig_row['descripcion'])[:60]
                                _csr  = str(_orig_row.get('codigo_sinonimo', '') if hasattr(_orig_row, 'get') else _orig_row['codigo_sinonimo'])
                                _cod  = int(_orig_row.get('codigo', 0) if hasattr(_orig_row, 'get') else _orig_row['codigo'])
                                _renglones_jit.append({
                                    'articulo':        _cod,
                                    'descripcion':     _desc,
                                    'codigo_sinonimo': _csr,
                                    'cantidad':        _cant,
                                    'precio':          _precio,
                                    'descuento_reng1': _jit_prov_cfg.get('descuento', 0),
                                    'descuento_reng2': _jit_prov_cfg.get('descuento_1', 0),
                                })

                            _cabecera_jit = {
                                'empresa':            _jit_empresa_sel,
                                'cuenta':             _jit_prov_id,
                                'denominacion':       _jit_prov_nombre,
                                'fecha_comprobante':  _fecha_jit,
                                'observaciones':      _obs_jit,
                            }

                            if not _renglones_jit:
                                st.error("No hay renglones con cantidad > 0 para insertar.")
                            else:
                                try:
                                    import pyodbc as _pyodbc_jit
                                    from config import get_conn_string as _get_cs_jit
                                    from paso4_insertar_pedido import (
                                        insertar_pedido as _insertar_pedido_jit,
                                    )
                                    with st.spinner("Insertando pedido en el ERP..."):
                                        _num_pedido = _insertar_pedido_jit(
                                            _cabecera_jit,
                                            _renglones_jit,
                                            dry_run=False,
                                        )
                                    if _num_pedido:
                                        st.success(
                                            f"Pedido #{_num_pedido} insertado correctamente en "
                                            f"{'MSGESTION01' if _jit_empresa_sel == 'CALZALINDO' else 'MSGESTION03'} "
                                            f"({_skus_editados} SKUs, {_pares_editados:,} pares). "
                                            f"Proveedor: {_jit_prov_nombre}."
                                        )
                                        st.balloons()
                                        # Limpiar session state
                                        del st.session_state['jit_pedido_df']
                                        if 'jit_pedido_proveedor' in st.session_state:
                                            del st.session_state['jit_pedido_proveedor']
                                        st.session_state['jit_pedido_confirmado'] = True
                                    else:
                                        st.error(
                                            "El INSERT no retornó número de pedido. "
                                            "Revisar logs del servidor."
                                        )
                                except Exception as _e_jit:
                                    st.error(f"Error al insertar pedido en ERP: {_e_jit}")

                # ── Detalle completo con filtro de urgencia ──
                with st.expander("Ver detalle completo (todos los artículos)"):
                    _urgencia_filtro = st.multiselect(
                        "Filtrar por urgencia",
                        options=['ROJO', 'AMARILLO', 'VERDE', 'SIN_DEMANDA'],
                        default=['ROJO', 'AMARILLO'],
                        key="jit_filtro_urgencia",
                    )
                    _df_full_jit = df_jit.copy()
                    if _urgencia_filtro:
                        _df_full_jit = _df_full_jit[
                            _df_full_jit['urgencia'].isin(_urgencia_filtro)
                        ]
                    _cols_full = [
                        'descripcion', 'stock_actual', 'vel_diaria',
                        'dias_hasta_stockout', 'safety_stock', 'punto_reorden',
                        'necesita_pedido', 'urgencia', 'cantidad_sugerida',
                        'pct_quiebre', 'meses_quebrado',
                    ]
                    # Solo mostrar columnas que existen
                    _cols_full = [c for c in _cols_full if c in _df_full_jit.columns]
                    st.dataframe(
                        _df_full_jit[_cols_full].sort_values('dias_hasta_stockout'),
                        use_container_width=True,
                        hide_index=True,
                    )

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

    # ══════════════════════════════════════════════════════════════
    # TAB 9: NICHOS DESCUBIERTOS
    # ══════════════════════════════════════════════════════════════
    with tab_nichos:
        st.subheader("Nichos Descubiertos — Demanda sin cobertura")
        st.caption("Categorías con ventas reales pero sin stock ni pedidos. "
                   "Filtro: solo artículos comprados después de 2020.")

        # ── Controles internos (no sidebar global) ──
        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
        with col_ctrl1:
            min_vtas = st.number_input(
                "Ventas mínimas 12m", min_value=1, value=10, step=1,
                key="nichos_min_vtas"
            )
        with col_ctrl2:
            max_cob = st.number_input(
                "Cobertura máxima (días)", min_value=1, value=30, step=5,
                key="nichos_max_cob"
            )
        with col_ctrl3:
            solo_temporada = st.checkbox(
                "Solo temporada actual", value=False,
                key="nichos_solo_temporada"
            )

        # ── Cargar datos ──
        df_nichos = detectar_nichos_descubiertos(
            min_vtas=min_vtas, max_cob_dias=max_cob,
            solo_post_2020=True
        )
        if solo_temporada and not df_nichos.empty and 'es_temporada' in df_nichos.columns:
            df_nichos = df_nichos[df_nichos['es_temporada']]

        if df_nichos.empty:
            st.info("No se encontraron nichos descubiertos con los filtros actuales.")
        else:
            # ── KPI row ──
            total_nichos = len(df_nichos)
            pares_sin_cubrir = int(df_nichos['pares_12m'].sum())
            ppp_promedio = df_nichos['ppp_costo'].mean() if 'ppp_costo' in df_nichos.columns else 0
            inversion_estimada = pares_sin_cubrir * ppp_promedio

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Total nichos descubiertos", f"{total_nichos:,}")
            kpi2.metric("Pares demanda anual sin cubrir", f"{pares_sin_cubrir:,}")
            kpi3.metric("Inversión estimada", f"${inversion_estimada:,.0f}")

            # ── Tabla principal ──
            df_show = df_nichos.sort_values('pares_12m', ascending=False)
            display_cols = [
                'genero', 'categoria', 'marca', 'pares_12m', 'stock',
                'pedido', 'disponible', 'cob_dias', 'ppp_costo', 'urgencia'
            ]
            display_cols = [c for c in display_cols if c in df_show.columns]

            def _color_urgencia(val):
                if val == 'CRITICO':
                    return 'background-color: #ffcccc; color: #990000'
                elif val == 'BAJO':
                    return 'background-color: #fff3cd; color: #856404'
                return ''

            styled = df_show[display_cols].style
            if 'urgencia' in display_cols:
                styled = styled.map(_color_urgencia, subset=['urgencia'])

            st.dataframe(
                styled,
                column_config={
                    'pares_12m': st.column_config.NumberColumn("Pares 12m", format="%d"),
                    'stock': st.column_config.NumberColumn("Stock", format="%d"),
                    'pedido': st.column_config.NumberColumn("Pedido", format="%d"),
                    'disponible': st.column_config.NumberColumn("Disponible", format="%d"),
                    'cob_dias': st.column_config.NumberColumn("Cob.Días", format="%.0f"),
                    'ppp_costo': st.column_config.NumberColumn("PPP Costo", format="$%.0f"),
                },
                use_container_width=True, hide_index=True,
            )

        # ── Vista por subrubro ──
        with st.expander("Vista por subrubro"):
            df_sub = detectar_nichos_por_subrubro(
                min_vtas=min_vtas, max_cob_dias=max_cob
            )
            if solo_temporada and not df_sub.empty and 'es_temporada' in df_sub.columns:
                df_sub = df_sub[df_sub['es_temporada']]
            if df_sub.empty:
                st.info("Sin datos de nichos por subrubro.")
            else:
                st.dataframe(
                    df_sub.sort_values('pares_12m', ascending=False),
                    use_container_width=True, hide_index=True,
                )
                # Bar chart top 20
                top20 = df_sub.nlargest(20, 'pares_12m')
                if not top20.empty:
                    st.bar_chart(
                        top20.set_index('categoria')['pares_12m'],
                        use_container_width=True,
                    )

        # ── Proveedores a contactar ──
        with st.expander("Proveedores a contactar"):
            if df_nichos.empty or 'proveedor_num' not in df_nichos.columns:
                st.info("Sin datos de proveedores para nichos descubiertos.")
            else:
                prov_group = (
                    df_nichos.groupby(['proveedor_num', 'proveedor_nombre'])
                    .agg(
                        total_pares=('pares_12m', 'sum'),
                        categorias=('categoria', lambda x: ', '.join(sorted(x.unique()))),
                        cant_nichos=('categoria', 'count'),
                    )
                    .reset_index()
                    .sort_values('total_pares', ascending=False)
                )
                for _, row in prov_group.iterrows():
                    prov_nombre = row['proveedor_nombre']
                    prov_num = row['proveedor_num']
                    total = int(row['total_pares'])
                    cats = row['categorias']
                    cnt = int(row['cant_nichos'])

                    st.markdown(
                        f"**{prov_nombre}** (#{prov_num}) - "
                        f"{total:,} pares en {cnt} nichos"
                    )
                    st.caption(f"Categorías: {cats}")

                    # Intentar obtener teléfono del proveedor
                    try:
                        tel_sql = (
                            f"SELECT telefono FROM msgestion01.dbo.proveedores "
                            f"WHERE numero = {int(prov_num)}"
                        )
                        df_tel = query_df(tel_sql)
                        if not df_tel.empty and df_tel.iloc[0]['telefono']:
                            tel = str(df_tel.iloc[0]['telefono']).strip()
                            if tel:
                                tel_clean = ''.join(c for c in tel if c.isdigit())
                                if tel_clean:
                                    wa_url = f"https://wa.me/54{tel_clean}"
                                    st.markdown(f"[WhatsApp {tel}]({wa_url})")
                    except Exception:
                        pass  # No phone available

                    st.divider()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    render_dashboard()
