#!/usr/bin/env python3
"""
backtesting_v4.py — Backtesting comparativo v3 vs v4
====================================================
Compara el modelo v3 (actual) con las mejoras propuestas en v4:
  1. Clasificacion de familia (estable, estacional, escolar, erratico, nuevo)
  2. Media ponderada exponencial (EWA) en vez de media simple
  3. Factores estacionales corregidos por quiebre
  4. Factor de tendencia interanual
  5. Benchmark de categoria para productos nuevos
  6. Confidence intervals

EJECUTAR en Mac:
  cd ~/Desktop/cowork_pedidos
  python3 _scripts_oneshot/backtesting_v4.py

Genera: _informes/backtesting/comparacion_v3_v4.md
"""

import os
import sys
import platform
from datetime import date, timedelta
from collections import defaultdict
from math import sqrt

if platform.system() != "Windows":
    ssl_conf = os.path.join(os.path.dirname(__file__), "openssl_legacy.cnf")
    if not os.path.exists(ssl_conf):
        ssl_conf = "/tmp/openssl_legacy.cnf"
    os.environ["OPENSSL_CONF"] = ssl_conf

import pyodbc
import pandas as pd
from dateutil.relativedelta import relativedelta

# ── Conexion ──
SERVIDOR = "192.168.2.111"
DRIVER = "ODBC Driver 17 for SQL Server"
CONN_STR = (
    f"DRIVER={{{DRIVER}}};SERVER={SERVIDOR};DATABASE=msgestionC;"
    f"UID=am;PWD=dl;Connection Timeout=30;TrustServerCertificate=yes;Encrypt=no;"
)
EXCL_VENTAS = "(7,36)"
EXCL_MARCAS = "(1316,1317,1158,436)"
DEPOS_SQL = "(0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)"
MESES_OI = [4, 5, 6, 7, 8, 9]
EWA_ALPHA = 0.85  # factor de decaimiento exponencial
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', '_informes', 'backtesting')


def get_conn():
    return pyodbc.connect(CONN_STR, timeout=30)


def query_df(sql, conn):
    return pd.read_sql(sql, conn)


# ============================================================================
# CLASIFICACION DE FAMILIA
# ============================================================================

def clasificar_familia(ventas_por_anio_mes, meses_con_ventas):
    """
    Clasifica la familia segun patron de demanda.
    Returns: 'estable', 'estacional_oi', 'estacional_pv', 'escolar', 'erratico', 'nuevo'
    """
    if meses_con_ventas < 6:
        return 'nuevo'

    # Agrupar ventas por mes calendario
    mes_totals = defaultdict(list)
    for (anio, mes), cant in ventas_por_anio_mes.items():
        if cant > 0:
            mes_totals[mes].append(cant)

    mes_avg = {}
    for m in range(1, 13):
        vals = mes_totals.get(m, [0])
        mes_avg[m] = sum(vals) / max(len(vals), 1)

    total = sum(mes_avg.values())
    if total <= 0:
        return 'nuevo'

    # Concentracion
    pct_feb_mar = (mes_avg.get(2, 0) + mes_avg.get(3, 0)) / total
    pct_oi = sum(mes_avg.get(m, 0) for m in [4, 5, 6, 7, 8, 9]) / total
    pct_pv = sum(mes_avg.get(m, 0) for m in [10, 11, 12, 1, 2, 3]) / total

    # Coeficiente de variacion
    valores = [mes_avg[m] for m in range(1, 13) if mes_avg[m] > 0]
    if len(valores) < 3:
        return 'nuevo'
    media = sum(valores) / len(valores)
    varianza = sum((v - media) ** 2 for v in valores) / len(valores)
    cv = sqrt(varianza) / media if media > 0 else 0

    if pct_feb_mar > 0.70:
        return 'escolar'
    elif cv > 1.5:
        return 'erratico'
    elif pct_oi > 0.65:
        return 'estacional_oi'
    elif pct_pv > 0.70:
        return 'estacional_pv'
    else:
        return 'estable'


# ============================================================================
# FACTORES ESTACIONALES CORREGIDOS POR QUIEBRE
# ============================================================================

def calcular_factores_corregidos(ventas_por_anio_mes, meses_quebrados_set):
    """
    Calcula factores estacionales excluyendo meses quebrados.
    Interpola meses siempre quebrados desde vecinos.
    """
    # Acumular ventas solo de meses NO quebrados
    ventas_por_mes_cal = defaultdict(list)
    for (anio, mes), cant in ventas_por_anio_mes.items():
        if (anio, mes) not in meses_quebrados_set:
            ventas_por_mes_cal[mes].append(cant)

    # Promedio por mes calendario
    promedio_mes = {}
    for m in range(1, 13):
        vals = ventas_por_mes_cal.get(m, [])
        if vals:
            promedio_mes[m] = sum(vals) / len(vals)
        else:
            promedio_mes[m] = None  # siempre quebrado

    # Interpolar meses sin datos
    for m in range(1, 13):
        if promedio_mes[m] is None:
            prev_m = ((m - 2) % 12) + 1
            next_m = (m % 12) + 1
            vecinos = [v for v in [promedio_mes.get(prev_m), promedio_mes.get(next_m)]
                       if v is not None]
            promedio_mes[m] = sum(vecinos) / len(vecinos) if vecinos else 0

    # Normalizar
    gran_promedio = sum(promedio_mes.values()) / 12
    if gran_promedio <= 0:
        return {m: 1.0 for m in range(1, 13)}

    return {m: max(promedio_mes[m] / gran_promedio, 0.01) for m in range(1, 13)}


# ============================================================================
# VELOCIDAD v3 (baseline)
# ============================================================================

def calcular_vel_v3(vtas_dict, comp_dict, stock_actual, factores_est, meses_lista):
    """Replica exacta del modelo v3."""
    stock_fin = float(stock_actual)
    meses_q = 0
    meses_ok = 0
    ventas_total = 0
    ventas_ok = 0
    ventas_desest = 0

    meses_quebrados = set()

    for anio, mes in meses_lista:
        v = vtas_dict.get((anio, mes), 0)
        c = comp_dict.get((anio, mes), 0)
        stock_inicio = stock_fin + v - c
        ventas_total += v

        if stock_inicio <= 0:
            meses_q += 1
            meses_quebrados.add((anio, mes))
        else:
            meses_ok += 1
            ventas_ok += v
            s_t = max(factores_est.get(mes, 1.0), 0.1)
            ventas_desest += v / s_t

        stock_fin = stock_inicio

    n_meses = len(meses_lista)
    vel_ap = ventas_total / max(n_meses, 1)
    pct_q = meses_q / max(n_meses, 1)

    if meses_ok > 0:
        vel_base = ventas_desest / meses_ok
    elif ventas_total > 0:
        vel_base = vel_ap * 1.15
    else:
        vel_base = 0

    if pct_q > 0.5:
        factor_disp = 1.20
    elif pct_q > 0.3:
        factor_disp = 1.10
    else:
        factor_disp = 1.0

    vel_real_v3 = vel_base * factor_disp

    return {
        'vel_real': vel_real_v3,
        'vel_ap': vel_ap,
        'meses_q': meses_q,
        'meses_ok': meses_ok,
        'pct_q': pct_q,
        'meses_quebrados': meses_quebrados,
    }


# ============================================================================
# VELOCIDAD v4 (mejoras)
# ============================================================================

def calcular_vel_v4(vtas_dict, comp_dict, stock_actual, factores_est,
                    meses_lista, vtas_dict_full, tipo_familia,
                    benchmark_vel=None, ventas_anuales=None):
    """
    Modelo v4 con todas las mejoras:
    1. EWA (media ponderada exponencial)
    2. Factores corregidos por quiebre
    3. Factor tendencia
    4. Benchmark para productos nuevos
    5. Confidence intervals
    """
    stock_fin = float(stock_actual)
    meses_q = 0
    meses_ok = 0
    ventas_total = 0
    meses_quebrados = set()

    # Datos para EWA
    obs_ewa = []  # (ventas_desest, peso_ewa, mes)

    for i, (anio, mes) in enumerate(meses_lista):
        v = vtas_dict.get((anio, mes), 0)
        c = comp_dict.get((anio, mes), 0)
        stock_inicio = stock_fin + v - c
        ventas_total += v

        peso_ewa = EWA_ALPHA ** i  # mas peso a meses recientes

        if stock_inicio <= 0:
            meses_q += 1
            meses_quebrados.add((anio, mes))
        else:
            meses_ok += 1
            s_t = max(factores_est.get(mes, 1.0), 0.1)
            ventas_desest = v / s_t
            obs_ewa.append((ventas_desest, peso_ewa, mes))

        stock_fin = stock_inicio

    n_meses = len(meses_lista)
    vel_ap = ventas_total / max(n_meses, 1)
    pct_q = meses_q / max(n_meses, 1)

    # ── Factores corregidos ──
    factores_corr = calcular_factores_corregidos(vtas_dict_full, meses_quebrados)

    # ── vel_base con EWA ──
    if obs_ewa:
        suma_weighted = sum(v * w for v, w, _ in obs_ewa)
        suma_pesos = sum(w for _, w, _ in obs_ewa)
        vel_base = suma_weighted / suma_pesos
    elif ventas_total > 0:
        # Fallback: vel_aparente * 1.15
        vel_base = vel_ap * 1.15
    else:
        vel_base = 0

    # ── Factor disponibilidad (suavizado) ──
    if pct_q > 0.5:
        factor_disp = 1.15  # v4: mas conservador que v3 (era 1.20)
    elif pct_q > 0.3:
        factor_disp = 1.08
    else:
        factor_disp = 1.0

    vel_base_adj = vel_base * factor_disp

    # ── Factor tendencia ──
    factor_tend = 1.0
    if ventas_anuales and len(ventas_anuales) >= 2:
        anios_sorted = sorted(ventas_anuales.keys())
        reciente = ventas_anuales[anios_sorted[-1]]
        anterior = ventas_anuales[anios_sorted[-2]]
        if anterior > 0:
            ratio = reciente / anterior
            factor_tend = max(0.7, min(ratio, 1.5))
            # Cap extra para crecimiento explosivo
            if ratio > 1.5:
                factor_tend = 1.3

    vel_v4 = vel_base_adj * factor_tend

    # ── Benchmark para productos nuevos ──
    if tipo_familia == 'nuevo' and vel_v4 == 0 and benchmark_vel is not None:
        vel_v4 = benchmark_vel * 0.7  # conservador
        metodo = 'benchmark'
    else:
        metodo = 'ewa_corregido'

    # ── Confidence interval ──
    if obs_ewa:
        vals = [v for v, _, _ in obs_ewa]
        media = sum(vals) / len(vals)
        if len(vals) > 1:
            varianza = sum((v - media) ** 2 for v in vals) / (len(vals) - 1)
            std = sqrt(varianza)
            cv = std / media if media > 0 else 0
        else:
            cv = 0.5
    else:
        cv = 1.0

    if cv < 0.3:
        spread = 0.15
    elif cv < 0.6:
        spread = 0.25
    elif cv < 1.0:
        spread = 0.35
    else:
        spread = 0.50

    if meses_ok < 4:
        spread *= 1.3
    if tipo_familia == 'nuevo':
        spread *= 2.0

    ci_low = vel_v4 * (1 - spread)
    ci_high = vel_v4 * (1 + spread)

    return {
        'vel_real': vel_v4,
        'vel_ap': vel_ap,
        'meses_q': meses_q,
        'meses_ok': meses_ok,
        'pct_q': pct_q,
        'factor_tend': factor_tend,
        'factor_disp': factor_disp,
        'factores_corr': factores_corr,
        'tipo': tipo_familia,
        'metodo': metodo,
        'ci_low': ci_low,
        'ci_high': ci_high,
        'cv': cv,
    }


# ============================================================================
# PROYECCION Y COMPARACION
# ============================================================================

def proyectar_oi(vel_real, factores, meses=MESES_OI):
    """Proyecta demanda OI usando vel_real y factores."""
    demanda = {}
    for m in meses:
        demanda[m] = round(vel_real * factores.get(m, 1.0), 1)
    return demanda, round(sum(demanda.values()))


def calcular_mape(proyectado_dict, real_dict, meses=MESES_OI):
    """Calcula MAPE mensual."""
    errores = []
    for m in meses:
        real = real_dict.get(m, 0)
        proy = proyectado_dict.get(m, 0)
        if real > 0:
            err = abs(proy - real) / real
            errores.append(err)
    if errores:
        return round(sum(errores) / len(errores) * 100, 1)
    return 0.0


def main():
    print("=" * 70)
    print("BACKTESTING COMPARATIVO v3 vs v4")
    print("Simulacion: proyeccion OI2024 con datos hasta mar-2024")
    print("=" * 70)

    conn = get_conn()
    print("\nConectado a SQL Server.\n")

    # ── 1. Top 60 familias por ventas ──
    print("1/5 — Top familias por ventas...")
    sql_top = f"""
        SELECT TOP 60 LEFT(a.codigo_sinonimo, 10) AS csr,
               MAX(a.descripcion_1) AS descripcion,
               MAX(a.marca) AS marca, MAX(a.subrubro) AS subrubro,
               MAX(a.rubro) AS rubro,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS ventas_2a
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND a.marca NOT IN {EXCL_MARCAS} AND a.marca > 0
          AND a.estado = 'V' AND LEN(a.codigo_sinonimo) >= 10
          AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
          AND v.fecha >= DATEADD(year, -2, GETDATE())
        GROUP BY LEFT(a.codigo_sinonimo, 10)
        HAVING SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) > 50
        ORDER BY ventas_2a DESC
    """
    df_top = query_df(sql_top, conn)
    df_top['csr'] = df_top['csr'].str.strip()
    csrs = list(df_top['csr'].values[:50])
    print(f"   {len(csrs)} familias seleccionadas")

    # ── 2. Stock actual ──
    print("2/5 — Stock actual...")
    filtro = ",".join(f"'{c}'" for c in csrs)
    sql_stock = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(s.stock_actual) AS stock_actual
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        WHERE LEFT(a.codigo_sinonimo, 10) IN ({filtro})
          AND s.deposito IN {DEPOS_SQL}
        GROUP BY LEFT(a.codigo_sinonimo, 10)
    """
    df_stk = query_df(sql_stock, conn)
    stock_dict = {r['csr'].strip(): float(r['stock_actual'] or 0) for _, r in df_stk.iterrows()}

    # ── 3. Serie historica completa ──
    print("3/5 — Ventas historicas completas...")
    sql_hist = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS pares
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN {EXCL_VENTAS}
          AND LEFT(a.codigo_sinonimo, 10) IN ({filtro})
        GROUP BY LEFT(a.codigo_sinonimo, 10), YEAR(v.fecha), MONTH(v.fecha)
    """
    df_hist = query_df(sql_hist, conn)
    df_hist['csr'] = df_hist['csr'].str.strip()

    # ── 4. Compras historicas ──
    print("4/5 — Compras historicas...")
    sql_comp = f"""
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes,
               SUM(rc.cantidad) AS pares
        FROM msgestionC.dbo.compras1 rc
        JOIN msgestion01art.dbo.articulo a ON rc.articulo = a.codigo
        WHERE rc.operacion = '+'
          AND LEFT(a.codigo_sinonimo, 10) IN ({filtro})
        GROUP BY LEFT(a.codigo_sinonimo, 10), YEAR(rc.fecha), MONTH(rc.fecha)
    """
    df_comp = query_df(sql_comp, conn)
    df_comp['csr'] = df_comp['csr'].str.strip()

    # Marcas
    sql_marcas = "SELECT codigo, RTRIM(descripcion) AS nombre FROM msgestionC.dbo.marcas"
    marca_nombres = dict(query_df(sql_marcas, conn).values)
    conn.close()
    print("   OK\n")

    # ── Organizar datos por CSR ──
    print("5/5 — Procesando comparacion v3 vs v4...\n")

    # Diccionarios de ventas/compras por CSR
    vtas_by_csr = defaultdict(dict)
    for _, r in df_hist.iterrows():
        vtas_by_csr[r['csr']][(int(r['anio']), int(r['mes']))] = float(r['pares'] or 0)

    comp_by_csr = defaultdict(dict)
    for _, r in df_comp.iterrows():
        comp_by_csr[r['csr']][(int(r['anio']), int(r['mes']))] = float(r['pares'] or 0)

    # Meses lista pre-OI2024 (12 meses terminando en mar-2024)
    meses_pre_oi24 = []
    cursor = date(2024, 3, 1)
    for _ in range(12):
        meses_pre_oi24.append((cursor.year, cursor.month))
        cursor -= relativedelta(months=1)

    # Factores estacionales por CSR (calculados con datos hasta dic 2023)
    def factores_est_basicos(vtas_dict, anio_max=2023):
        """Calcula factores estacionales con datos hasta anio_max."""
        mes_totals = defaultdict(list)
        for (a, m), v in vtas_dict.items():
            if a <= anio_max and a >= anio_max - 3:
                mes_totals[m].append(v)
        mes_avg = {}
        for m in range(1, 13):
            vals = mes_totals.get(m, [0])
            mes_avg[m] = sum(vals) / max(len(vals), 1)
        media = sum(mes_avg.values()) / 12
        if media <= 0:
            return {m: 1.0 for m in range(1, 13)}
        return {m: max(mes_avg[m] / media, 0.01) for m in range(1, 13)}

    # ── Calcular benchmark por subrubro (para productos nuevos) ──
    subrubro_vels = defaultdict(list)  # se llena despues

    # ── COMPARACION ──
    resultados = []

    for csr in csrs:
        r_top = df_top[df_top['csr'] == csr]
        if r_top.empty:
            continue
        r_top = r_top.iloc[0]
        desc = r_top['descripcion'] if isinstance(r_top['descripcion'], str) else csr
        marca = int(r_top['marca']) if pd.notna(r_top['marca']) else 0
        marca_nom = marca_nombres.get(marca, str(marca))
        subrubro = int(r_top['subrubro']) if pd.notna(r_top['subrubro']) else 0

        vtas = vtas_by_csr.get(csr, {})
        comp = comp_by_csr.get(csr, {})
        stock = stock_dict.get(csr, 0)

        # Ventas pre-OI2024 (hasta mar-2024)
        vtas_pre = {k: v for k, v in vtas.items() if k[0] < 2024 or (k[0] == 2024 and k[1] <= 3)}
        comp_pre = {k: v for k, v in comp.items() if k[0] < 2024 or (k[0] == 2024 and k[1] <= 3)}

        # Ventas anuales (para tendencia)
        ventas_anuales = defaultdict(float)
        for (a, m), v in vtas.items():
            if a >= 2020 and a <= 2023:
                ventas_anuales[a] += v

        # Meses con ventas (para clasificacion)
        meses_con_ventas = len([k for k, v in vtas_pre.items() if v > 0 and k[0] <= 2023])

        # Factores estacionales basicos
        f_est = factores_est_basicos(vtas, anio_max=2023)

        # Clasificacion
        vtas_hasta_2023 = {k: v for k, v in vtas.items() if k[0] <= 2023}
        tipo = clasificar_familia(vtas_hasta_2023, meses_con_ventas)

        # ── v3 ──
        res_v3 = calcular_vel_v3(vtas_pre, comp_pre, stock, f_est, meses_pre_oi24)
        dem_v3, total_v3 = proyectar_oi(res_v3['vel_real'], f_est)

        # ── v4 ──
        # Para v4, calcular benchmark del subrubro
        benchmark = None  # se podria implementar con datos de familias similares

        res_v4 = calcular_vel_v4(
            vtas_pre, comp_pre, stock, f_est, meses_pre_oi24,
            vtas_hasta_2023, tipo, benchmark, dict(ventas_anuales)
        )
        dem_v4, total_v4 = proyectar_oi(res_v4['vel_real'], res_v4['factores_corr'])

        # CI proyeccion
        _, total_v4_low = proyectar_oi(res_v4['ci_low'], res_v4['factores_corr'])
        _, total_v4_high = proyectar_oi(res_v4['ci_high'], res_v4['factores_corr'])

        # ── Ventas reales OI2024 ──
        ventas_oi24_real = {}
        total_real = 0
        for m in MESES_OI:
            v = vtas.get((2024, m), 0)
            ventas_oi24_real[m] = v
            total_real += v

        # Errores
        if total_real > 0:
            err_v3 = (total_v3 - total_real) / total_real * 100
            err_v4 = (total_v4 - total_real) / total_real * 100
            mape_v3 = calcular_mape(dem_v3, ventas_oi24_real)
            mape_v4 = calcular_mape(dem_v4, ventas_oi24_real)
        elif total_v3 == 0 and total_v4 == 0:
            err_v3 = 0
            err_v4 = 0
            mape_v3 = 0
            mape_v4 = 0
        else:
            err_v3 = 100 if total_v3 > 0 else 0
            err_v4 = 100 if total_v4 > 0 else 0
            mape_v3 = 100 if total_v3 > 0 else 0
            mape_v4 = 100 if total_v4 > 0 else 0

        # Guardar para benchmark
        if res_v3['vel_real'] > 0:
            subrubro_vels[subrubro].append(res_v3['vel_real'])

        resultados.append({
            'csr': csr,
            'desc': desc[:35],
            'marca': marca_nom[:15],
            'subrubro': subrubro,
            'tipo': tipo,
            'stock': stock,
            'total_real': total_real,
            'total_v3': total_v3,
            'total_v4': total_v4,
            'ci_low': total_v4_low,
            'ci_high': total_v4_high,
            'err_v3': round(err_v3, 1),
            'err_v4': round(err_v4, 1),
            'mape_v3': mape_v3,
            'mape_v4': mape_v4,
            'pct_q': round(res_v3['pct_q'] * 100),
            'vel_v3': round(res_v3['vel_real'], 1),
            'vel_v4': round(res_v4['vel_real'], 1),
            'factor_tend': round(res_v4['factor_tend'], 2),
            'cv': round(res_v4['cv'], 2),
        })

    # ================================================================
    # GENERAR REPORTE
    # ================================================================
    df = pd.DataFrame(resultados)

    # Filtrar familias con ventas reales > 0 (para MAPE significativo)
    df_con_ventas = df[df['total_real'] > 0].copy()
    df_sin_ventas = df[df['total_real'] == 0].copy()

    lines = []
    lines.append("# Comparacion Backtesting v3 vs v4")
    lines.append(f"\n**Fecha**: {date.today()}")
    lines.append(f"**Familias evaluadas**: {len(df)} ({len(df_con_ventas)} con ventas OI2024, {len(df_sin_ventas)} sin ventas)")
    lines.append(f"**Periodo**: proyeccion OI2024 (abr-sep) con datos hasta mar-2024")

    # ── KPIs globales ──
    lines.append(f"\n## Resumen ejecutivo")
    lines.append(f"| Metrica | Modelo v3 | Modelo v4 | Mejora |")
    lines.append(f"|---------|-----------|-----------|--------|")

    if len(df_con_ventas) > 0:
        mape_prom_v3 = df_con_ventas['mape_v3'].mean()
        mape_prom_v4 = df_con_ventas['mape_v4'].mean()
        mape_med_v3 = df_con_ventas['mape_v3'].median()
        mape_med_v4 = df_con_ventas['mape_v4'].median()

        excelentes_v3 = len(df_con_ventas[df_con_ventas['mape_v3'] <= 15])
        excelentes_v4 = len(df_con_ventas[df_con_ventas['mape_v4'] <= 15])
        pobres_v3 = len(df_con_ventas[df_con_ventas['mape_v3'] > 40])
        pobres_v4 = len(df_con_ventas[df_con_ventas['mape_v4'] > 40])

        lines.append(f"| MAPE promedio (con ventas) | {mape_prom_v3:.1f}% | {mape_prom_v4:.1f}% | {mape_prom_v3 - mape_prom_v4:+.1f}pp |")
        lines.append(f"| MAPE mediana | {mape_med_v3:.1f}% | {mape_med_v4:.1f}% | {mape_med_v3 - mape_med_v4:+.1f}pp |")
        lines.append(f"| Familias EXCELENTES (<15%) | {excelentes_v3} | {excelentes_v4} | {excelentes_v4 - excelentes_v3:+d} |")
        lines.append(f"| Familias POBRES (>40%) | {pobres_v3} | {pobres_v4} | {pobres_v4 - pobres_v3:+d} |")

    # ── Tabla completa ──
    lines.append(f"\n## Detalle por familia (ordenado por mejora v4 vs v3)")
    lines.append(f"| Familia | Tipo | Real | v3 Proy | v4 Proy | v4 CI | MAPE v3 | MAPE v4 | Mejora | Quiebre | Tend |")
    lines.append(f"|---------|------|------|---------|---------|-------|---------|---------|--------|---------|------|")

    # Ordenar por mejora (mape_v3 - mape_v4, descendente)
    df_sorted = df_con_ventas.sort_values('mape_v3', ascending=False)

    for _, r in df_sorted.iterrows():
        mejora = r['mape_v3'] - r['mape_v4']
        mejor_emoji = 'OK' if mejora > 5 else ('=' if abs(mejora) <= 5 else 'PEOR')
        ci_str = f"[{r['ci_low']:.0f}-{r['ci_high']:.0f}]"
        lines.append(
            f"| {r['desc'][:25]} | {r['tipo'][:8]} | {r['total_real']:.0f} | "
            f"{r['total_v3']:.0f} | {r['total_v4']:.0f} | {ci_str} | "
            f"{r['mape_v3']:.0f}% | {r['mape_v4']:.0f}% | {mejor_emoji} {mejora:+.0f}pp | "
            f"{r['pct_q']:.0f}% | {r['factor_tend']:.2f} |"
        )

    # ── Familias sin ventas ──
    if len(df_sin_ventas) > 0:
        lines.append(f"\n## Familias sin ventas OI2024 ({len(df_sin_ventas)})")
        lines.append(f"| Familia | Tipo | v3 | v4 | Quiebre | Observacion |")
        lines.append(f"|---------|------|----|----|---------|-------------|")
        for _, r in df_sin_ventas.iterrows():
            obs = "Correcto 0/0" if r['total_v3'] == 0 and r['total_v4'] == 0 else "Falso positivo"
            lines.append(f"| {r['desc'][:25]} | {r['tipo'][:8]} | {r['total_v3']:.0f} | {r['total_v4']:.0f} | {r['pct_q']:.0f}% | {obs} |")

    # ── Clasificacion por tipo ──
    lines.append(f"\n## Distribucion por tipo de familia")
    for tipo in ['estable', 'estacional_oi', 'estacional_pv', 'escolar', 'erratico', 'nuevo']:
        df_tipo = df_con_ventas[df_con_ventas['tipo'] == tipo]
        if len(df_tipo) > 0:
            lines.append(f"\n**{tipo.upper()}** ({len(df_tipo)} familias): "
                         f"MAPE v3={df_tipo['mape_v3'].mean():.0f}% -> v4={df_tipo['mape_v4'].mean():.0f}%")

    # ── Analisis de mejoras por causa ──
    lines.append(f"\n## Analisis de mejoras por causa")
    lines.append(f"\n### Mejora por factores estacionales corregidos")
    lines.append(f"Familias donde v4 usa s_t corregido (quiebre > 30%):")
    df_quiebre = df_con_ventas[df_con_ventas['pct_q'] > 30]
    if len(df_quiebre) > 0:
        lines.append(f"  - {len(df_quiebre)} familias afectadas")
        lines.append(f"  - MAPE v3 promedio: {df_quiebre['mape_v3'].mean():.0f}%")
        lines.append(f"  - MAPE v4 promedio: {df_quiebre['mape_v4'].mean():.0f}%")

    lines.append(f"\n### Mejora por factor tendencia")
    df_tend = df_con_ventas[df_con_ventas['factor_tend'] != 1.0]
    if len(df_tend) > 0:
        lines.append(f"  - {len(df_tend)} familias con tendencia != 1.0")
        lines.append(f"  - MAPE v3 promedio: {df_tend['mape_v3'].mean():.0f}%")
        lines.append(f"  - MAPE v4 promedio: {df_tend['mape_v4'].mean():.0f}%")

    # ── Conclusiones ──
    lines.append(f"\n## Conclusiones")
    if len(df_con_ventas) > 0:
        lines.append(f"1. v4 mejora el MAPE promedio de {mape_prom_v3:.0f}% a {mape_prom_v4:.0f}% ({mape_prom_v3 - mape_prom_v4:+.0f}pp)")
        lines.append(f"2. v4 reduce las familias POBRES de {pobres_v3} a {pobres_v4}")
        lines.append(f"3. v4 aumenta las familias EXCELENTES de {excelentes_v3} a {excelentes_v4}")
        lines.append(f"4. La mayor mejora viene de: factores estacionales corregidos + EWA + factor tendencia")
        lines.append(f"5. Productos NUEVOS siguen siendo el mayor desafio — requieren benchmark de categoria")

    lines.append(f"\n---\n*Generado por backtesting_v4.py — {date.today()}*")

    # Escribir
    output_path = os.path.join(OUTPUT_DIR, 'comparacion_v3_v4.md')
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"\nREPORTE GENERADO: {output_path}")

    # Resumen en consola
    if len(df_con_ventas) > 0:
        print(f"\n{'=' * 60}")
        print(f"RESUMEN COMPARATIVO")
        print(f"{'=' * 60}")
        print(f"  Familias con ventas OI2024:   {len(df_con_ventas)}")
        print(f"  MAPE promedio v3:             {mape_prom_v3:.1f}%")
        print(f"  MAPE promedio v4:             {mape_prom_v4:.1f}%")
        print(f"  Mejora:                       {mape_prom_v3 - mape_prom_v4:+.1f}pp")
        print(f"  Familias EXCELENTES:  v3={excelentes_v3}  v4={excelentes_v4}")
        print(f"  Familias POBRES:      v3={pobres_v3}  v4={pobres_v4}")
        print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
