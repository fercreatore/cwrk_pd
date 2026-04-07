# -*- coding: utf-8 -*-
"""
vel_real.py — Velocidad Real corregida por quiebre de stock (algoritmo v3)
==========================================================================
Módulo independiente para calcular vel_real en el contexto web2py (DAL).

Lógica extraída de app_reposicion.py::analizar_quiebre_batch() y adaptada
para funcionar con las conexiones DAL de calzalindo_informes (db1, dbC).

Algoritmo v3 incluye:
  - Desestacionalización mensual (factores calculados por artículo)
  - factor_disp: 1.20x si >50% quiebre, 1.10x si >30%, 1.0 si no
  - Fallback 100% quiebre: vel_aparente * 1.15
  - std_mensual: desvío estándar de meses con stock
  - ventas_perdidas: estimación de ventas en meses quebrados
  - vel_real_con_perdidas: (ventas_total + ventas_perdidas) / meses

Uso desde controllers:
    from vel_real import vel_real_proveedor, vel_real_industria, analizar_quiebre_batch_dal

Depende de: db1 (msgestion01art), dbC (msgestionC), db_omicronvt (omicronvt)
            definidos en models/db.py y models/db_extra.py

Autor: Cowork + Claude — Marzo 2026
"""

import datetime
import math
import pandas as pd
from dateutil.relativedelta import relativedelta

# ============================================================================
# CONSTANTES (mismas que app_reposicion.py y funciones_ranking.py)
# ============================================================================

DEPOS_INFORMES_SQL = '(0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)'
CODIGOS_EXCLUIR_VENTAS = '(7,36)'
MARCAS_EXCLUIDAS_SQL = '(1316,1317,1158,436)'
MESES_QUIEBRE_DEFAULT = 12

# Factores estacionales globales (fallback cuando no hay historia propia)
# Fuente: ESTACIONALIDAD_MENSUAL en app_reposicion.py
ESTACIONALIDAD_MENSUAL = {
    1: 0.88, 2: 1.04, 3: 0.74, 4: 0.73, 5: 0.93, 6: 1.05,
    7: 0.98, 8: 0.92, 9: 0.93, 10: 1.22, 11: 1.04, 12: 1.51,
}


# ============================================================================
# FACTOR ESTACIONAL BATCH v3 (DAL version)
# ============================================================================

def factor_estacional_batch_dal(codigos_sinonimo, anios=3):
    """
    Calcula factores estacionales por articulo en batch. Version DAL para web2py.
    Adaptado de factor_estacional_batch() de crear_tabla_vel_real.py (v3).

    Retorna dict {cs: {mes(1..12): factor_float}}

    Logica:
      - Suma ventas de los ultimos `anios` anios por (codigo_sinonimo, mes)
      - Calcula factor = ventas_mes / media_mensual
      - Si factores son "planos" (todos 0.8-1.2), usa ESTACIONALIDAD_MENSUAL global
      - Si el articulo no tiene historia suficiente, usa ESTACIONALIDAD_MENSUAL global
    """
    if not codigos_sinonimo:
        return {}

    desde = (datetime.date.today() - relativedelta(years=anios)).replace(month=1, day=1)
    filtro = ",".join("'%s'" % c for c in codigos_sinonimo)

    sql = """
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               MONTH(v.fecha) AS mes
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN %s
          AND LEFT(a.codigo_sinonimo, 10) IN (%s)
          AND v.fecha >= '%s'
        GROUP BY LEFT(a.codigo_sinonimo, 10), MONTH(v.fecha)
    """ % (CODIGOS_EXCLUIR_VENTAS, filtro, desde)

    try:
        rows = dbC.executesql(sql, as_dict=True)
    except Exception:
        rows = []

    # Indexar por csr
    ventas_por_cs = {}
    for r in rows:
        cs = (r['csr'] or '').strip()
        mes = int(r['mes'])
        cant = float(r['cant'] or 0)
        if cs not in ventas_por_cs:
            ventas_por_cs[cs] = {}
        ventas_por_cs[cs][mes] = cant

    resultados = {}
    for cs in codigos_sinonimo:
        ventas_mes = ventas_por_cs.get(cs, {})
        if not ventas_mes:
            resultados[cs] = dict(ESTACIONALIDAD_MENSUAL)
            continue

        media = sum(ventas_mes.values()) / max(len(ventas_mes), 1)
        if media <= 0:
            resultados[cs] = dict(ESTACIONALIDAD_MENSUAL)
            continue

        factors = {m: round(ventas_mes.get(m, media) / media, 3) for m in range(1, 13)}

        # Si factores son planos (sin estacionalidad real), usar global
        is_flat = all(0.8 <= v <= 1.2 for v in factors.values())
        if is_flat:
            resultados[cs] = dict(ESTACIONALIDAD_MENSUAL)
        else:
            resultados[cs] = factors

    return resultados


# ============================================================================
# CORE: analizar_quiebre_batch para DAL (web2py)
# ============================================================================

def analizar_quiebre_batch_dal(codigos_sinonimo, meses=MESES_QUIEBRE_DEFAULT):
    """
    Analiza quiebre para MULTIPLES codigo_sinonimo en batch. Algoritmo v3.
    Version DAL: usa dbC (msgestionC) y db1 (msgestion01art).

    Mejoras v3 sobre v1:
      - Desestacionalizacion: ventas de meses OK divididas por factor estacional
      - factor_disp: 1.20 si pct_quiebre>50%, 1.10 si >30%, 1.0 si no
      - Fallback 100% quiebre: vel_aparente * 1.15
      - std_mensual: desvio estandar de ventas en meses con stock
      - ventas_perdidas: estimacion de ventas en meses quebrados
      - vel_real_con_perdidas: (ventas_total + ventas_perdidas) / meses

    Usa LEFT(a.codigo_sinonimo, 10) para alinear con el algoritmo v3.

    Retorna dict {codigo_sinonimo: {
        stock_actual, meses_quebrado, meses_ok, pct_quiebre,
        vel_aparente, vel_real, vel_base_desest, factor_disp,
        ventas_total, ventas_ok, factor_quiebre,
        std_mensual, ventas_perdidas, vel_real_con_perdidas
    }}
    """
    if not codigos_sinonimo:
        return {}

    hoy = datetime.date.today()
    desde = (hoy - relativedelta(months=meses)).replace(day=1)

    filtro = ",".join("'%s'" % c for c in codigos_sinonimo)

    # 1. Stock actual por codigo_sinonimo (LEFT 10 para alinear con v3)
    sql_stock = """
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               ISNULL(SUM(s.stock_actual), 0) AS stock
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        WHERE LEFT(a.codigo_sinonimo, 10) IN (%s)
          AND s.deposito IN %s
        GROUP BY LEFT(a.codigo_sinonimo, 10)
    """ % (filtro, DEPOS_INFORMES_SQL)

    # 2. Ventas mensuales (LEFT 10)
    sql_ventas = """
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad END) AS cant,
               YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON v.articulo = a.codigo
        WHERE v.codigo NOT IN %s
          AND LEFT(a.codigo_sinonimo, 10) IN (%s)
          AND v.fecha >= '%s'
        GROUP BY LEFT(a.codigo_sinonimo, 10), YEAR(v.fecha), MONTH(v.fecha)
    """ % (CODIGOS_EXCLUIR_VENTAS, filtro, desde)

    # 3. Compras mensuales (LEFT 10)
    sql_compras = """
        SELECT LEFT(a.codigo_sinonimo, 10) AS csr,
               SUM(rc.cantidad) AS cant,
               YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes
        FROM msgestionC.dbo.compras1 rc
        JOIN msgestion01art.dbo.articulo a ON rc.articulo = a.codigo
        WHERE rc.operacion = '+'
          AND LEFT(a.codigo_sinonimo, 10) IN (%s)
          AND rc.fecha >= '%s'
        GROUP BY LEFT(a.codigo_sinonimo, 10), YEAR(rc.fecha), MONTH(rc.fecha)
    """ % (filtro, desde)

    # Ejecutar via dbC (conecta a msgestionC con cross-db JOINs)
    try:
        stock_rows = dbC.executesql(sql_stock, as_dict=True)
    except Exception:
        stock_rows = []
    try:
        ventas_rows = dbC.executesql(sql_ventas, as_dict=True)
    except Exception:
        ventas_rows = []
    try:
        compras_rows = dbC.executesql(sql_compras, as_dict=True)
    except Exception:
        compras_rows = []

    # Indexar
    stock_dict = {}
    for r in stock_rows:
        cs = (r['csr'] or '').strip()
        stock_dict[cs] = float(r['stock'] or 0)

    ventas_by_cs = {}
    for r in ventas_rows:
        cs = (r['csr'] or '').strip()
        if cs not in ventas_by_cs:
            ventas_by_cs[cs] = {}
        ventas_by_cs[cs][(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    compras_by_cs = {}
    for r in compras_rows:
        cs = (r['csr'] or '').strip()
        if cs not in compras_by_cs:
            compras_by_cs[cs] = {}
        compras_by_cs[cs][(int(r['anio']), int(r['mes']))] = float(r['cant'] or 0)

    # Lista de meses hacia atras (de mas reciente a mas antiguo)
    meses_lista = []
    cursor = hoy.replace(day=1)
    for _ in range(meses):
        meses_lista.append((cursor.year, cursor.month))
        cursor -= relativedelta(months=1)

    # Pre-calcular factores estacionales para todos los articulos del batch
    factores_est = factor_estacional_batch_dal(codigos_sinonimo)

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
        ventas_desest = 0      # ventas desestacionalizadas (meses OK)
        ventas_meses_ok = []   # para calcular std_mensual

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

        # vel_real v3: desestacionalizada + correccion disponibilidad
        pct_q = meses_q / max(meses, 1)
        if meses_ok > 0:
            vel_base = ventas_desest / meses_ok
        elif ventas_total > 0:
            # Quiebre 100%: fallback vel_aparente x 1.15
            vel_base = vel_ap * 1.15
        else:
            vel_base = 0.0

        # Factor correccion por disponibilidad (demanda latente reprimida)
        if pct_q > 0.5:
            factor_disp = 1.20
        elif pct_q > 0.3:
            factor_disp = 1.10
        else:
            factor_disp = 1.0

        vel_real = vel_base * factor_disp

        # Desvio estandar mensual (solo meses no quebrados)
        if ventas_meses_ok:
            n = len(ventas_meses_ok)
            media_ok = sum(ventas_meses_ok) / n
            std_mes = math.sqrt(sum((x - media_ok) ** 2 for x in ventas_meses_ok) / max(n, 1))
        else:
            std_mes = 0.0

        # Segunda pasada: estimacion de ventas perdidas
        ventas_perdidas = 0.0
        if meses_ok > 0 and vel_base > 0:
            stock_fin2 = stock_actual
            for anio, mes in meses_lista:
                v = v_dict.get((anio, mes), 0)
                c = c_dict.get((anio, mes), 0)
                stock_inicio_check = stock_fin2 + v - c
                if stock_inicio_check <= 0:
                    factor_mes = max(f_est.get(mes, 1.0), 0.1)
                    ventas_esperadas = vel_base * factor_mes
                    ventas_perdidas += max(0.0, ventas_esperadas - v)
                stock_fin2 = stock_inicio_check

        vel_real_con_perdidas = round((ventas_total + ventas_perdidas) / max(meses, 1), 2)
        factor_quiebre = round(vel_real / vel_ap, 3) if vel_ap > 0 else 1.0

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
            'factor_quiebre': round(factor_quiebre, 2),
            'std_mensual': round(std_mes, 2),
            'ventas_perdidas': round(ventas_perdidas),
            'vel_real_con_perdidas': vel_real_con_perdidas,
        }

    return resultados


# ============================================================================
# vel_real_proveedor: vel_real por CSR para un proveedor
# ============================================================================

def vel_real_proveedor(nro_proveedor, meses=MESES_QUIEBRE_DEFAULT):
    """
    Calcula vel_real para todos los productos activos de un proveedor.

    Retorna DataFrame con columnas:
        csr, descripcion, stock_actual, vel_aparente, vel_real,
        factor_quiebre, pct_quiebre, meses_ok, meses_quebrado
    """
    # Obtener CSRs del proveedor con stock o ventas recientes
    desde = (datetime.date.today() - relativedelta(months=meses)).replace(day=1)

    sql_csrs = """
        SELECT DISTINCT LEFT(a.codigo_sinonimo, 10) AS csr,
               MAX(a.descripcion_1) AS descripcion
        FROM msgestion01art.dbo.articulo a
        JOIN msgestionC.dbo.provart pa ON pa.articulo = a.codigo
        WHERE pa.proveedor = %d
          AND LEN(a.codigo_sinonimo) >= 10
          AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
          AND a.marca NOT IN %s
        GROUP BY LEFT(a.codigo_sinonimo, 10)
        HAVING (
            EXISTS (SELECT 1 FROM msgestionC.dbo.stock s
                    JOIN msgestion01art.dbo.articulo a2 ON a2.codigo = s.articulo
                    WHERE LEFT(a2.codigo_sinonimo,10) = LEFT(a.codigo_sinonimo,10)
                      AND s.deposito IN %s AND s.stock_actual > 0)
            OR EXISTS (SELECT 1 FROM msgestionC.dbo.ventas1 v
                       JOIN msgestion01art.dbo.articulo a3 ON a3.codigo = v.articulo
                       WHERE LEFT(a3.codigo_sinonimo,10) = LEFT(a.codigo_sinonimo,10)
                         AND v.fecha >= '%s' AND v.codigo NOT IN %s)
        )
    """ % (nro_proveedor, MARCAS_EXCLUIDAS_SQL, DEPOS_INFORMES_SQL,
           desde, CODIGOS_EXCLUIR_VENTAS)

    try:
        rows = dbC.executesql(sql_csrs, as_dict=True)
    except Exception:
        return pd.DataFrame()

    if not rows:
        return pd.DataFrame()

    csrs = [r['csr'].strip() for r in rows]
    desc_map = {r['csr'].strip(): r['descripcion'] for r in rows}

    # Calcular quiebre en batch
    quiebres = analizar_quiebre_batch_dal(csrs, meses)

    # Armar DataFrame (incluye campos v3)
    data = []
    for cs in csrs:
        q = quiebres.get(cs, {})
        data.append({
            'csr': cs,
            'descripcion': desc_map.get(cs, cs),
            'stock_actual': q.get('stock_actual', 0),
            'vel_aparente': q.get('vel_aparente', 0),
            'vel_real': q.get('vel_real', 0),
            'vel_base_desest': q.get('vel_base_desest', 0),
            'factor_disp': q.get('factor_disp', 1.0),
            'factor_quiebre': q.get('factor_quiebre', 1.0),
            'pct_quiebre': q.get('pct_quiebre', 0),
            'meses_ok': q.get('meses_ok', 0),
            'meses_quebrado': q.get('meses_quebrado', 0),
            'std_mensual': q.get('std_mensual', 0),
            'ventas_perdidas': q.get('ventas_perdidas', 0),
            'vel_real_con_perdidas': q.get('vel_real_con_perdidas', 0),
        })

    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values('vel_real', ascending=False)
    return df


# ============================================================================
# vel_real_industria: vel_real agregado por industria/subrubro
# ============================================================================

def vel_real_industria(subrubro=None, meses=MESES_QUIEBRE_DEFAULT):
    """
    Calcula vel_real agregado por subrubro (o todos si subrubro=None).
    Usa map_subrubro_industria para mapear subrubro → industria.

    Retorna DataFrame con columnas:
        industria, subrubro, subrubro_desc, cant_productos,
        vel_aparente_total, vel_real_total, factor_quiebre_prom,
        pct_quiebre_prom, stock_total
    """
    desde = (datetime.date.today() - relativedelta(months=meses)).replace(day=1)

    where_sub = ""
    if subrubro:
        where_sub = "AND a.subrubro = %s" % int(subrubro)

    sql_csrs = """
        SELECT DISTINCT LEFT(a.codigo_sinonimo, 10) AS csr,
               a.subrubro
        FROM msgestion01art.dbo.articulo a
        WHERE LEN(a.codigo_sinonimo) >= 10
          AND LEFT(a.codigo_sinonimo, 10) <> '0000000000'
          AND a.marca NOT IN %s
          %s
        GROUP BY LEFT(a.codigo_sinonimo, 10), a.subrubro
        HAVING (
            EXISTS (SELECT 1 FROM msgestionC.dbo.stock s
                    JOIN msgestion01art.dbo.articulo a2 ON a2.codigo = s.articulo
                    WHERE LEFT(a2.codigo_sinonimo,10) = LEFT(a.codigo_sinonimo,10)
                      AND s.deposito IN %s AND s.stock_actual > 0)
            OR EXISTS (SELECT 1 FROM msgestionC.dbo.ventas1 v
                       JOIN msgestion01art.dbo.articulo a3 ON a3.codigo = v.articulo
                       WHERE LEFT(a3.codigo_sinonimo,10) = LEFT(a.codigo_sinonimo,10)
                         AND v.fecha >= '%s' AND v.codigo NOT IN %s)
        )
    """ % (MARCAS_EXCLUIDAS_SQL, where_sub, DEPOS_INFORMES_SQL,
           desde, CODIGOS_EXCLUIR_VENTAS)

    try:
        rows = dbC.executesql(sql_csrs, as_dict=True)
    except Exception:
        return pd.DataFrame()

    if not rows:
        return pd.DataFrame()

    csrs = list(set(r['csr'].strip() for r in rows))
    csr_subrubro = {r['csr'].strip(): int(r['subrubro'] or 0) for r in rows}

    # Batch quiebre (en chunks de 200 para no desbordar el IN)
    quiebres = {}
    chunk_size = 200
    for i in range(0, len(csrs), chunk_size):
        chunk = csrs[i:i + chunk_size]
        quiebres.update(analizar_quiebre_batch_dal(chunk, meses))

    # Mapear subrubro → industria
    industria_map = {}
    try:
        ind_rows = db_omicronvt.executesql(
            "SELECT subrubro, industria FROM map_subrubro_industria", as_dict=True)
        for r in ind_rows:
            industria_map[int(r['subrubro'])] = r['industria'] or 'Sin clasificar'
    except Exception:
        pass

    # Descripcion de subrubros
    sub_desc = {}
    try:
        sub_rows = db1.executesql("SELECT codigo, descripcion FROM subrubro", as_dict=True)
        for r in sub_rows:
            sub_desc[int(r['codigo'])] = r['descripcion']
    except Exception:
        pass

    # Agregar por subrubro
    agg = {}
    for cs in csrs:
        sub = csr_subrubro.get(cs, 0)
        q = quiebres.get(cs, {})
        if sub not in agg:
            agg[sub] = {
                'subrubro': sub,
                'subrubro_desc': sub_desc.get(sub, 'Sub %s' % sub),
                'industria': industria_map.get(sub, 'Sin clasificar'),
                'cant_productos': 0,
                'vel_aparente_total': 0,
                'vel_real_total': 0,
                'factor_quiebre_sum': 0,
                'pct_quiebre_sum': 0,
                'stock_total': 0,
            }
        agg[sub]['cant_productos'] += 1
        agg[sub]['vel_aparente_total'] += q.get('vel_aparente', 0)
        agg[sub]['vel_real_total'] += q.get('vel_real', 0)
        agg[sub]['factor_quiebre_sum'] += q.get('factor_quiebre', 1.0)
        agg[sub]['pct_quiebre_sum'] += q.get('pct_quiebre', 0)
        agg[sub]['stock_total'] += q.get('stock_actual', 0)

    # Promediar
    data = []
    for sub, a in agg.items():
        n = a['cant_productos']
        data.append({
            'industria': a['industria'],
            'subrubro': a['subrubro'],
            'subrubro_desc': a['subrubro_desc'],
            'cant_productos': n,
            'vel_aparente_total': round(a['vel_aparente_total'], 2),
            'vel_real_total': round(a['vel_real_total'], 2),
            'factor_quiebre_prom': round(a['factor_quiebre_sum'] / max(n, 1), 2),
            'pct_quiebre_prom': round(a['pct_quiebre_sum'] / max(n, 1), 1),
            'stock_total': a['stock_total'],
        })

    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values('vel_real_total', ascending=False)
    return df


# ============================================================================
# vel_real_por_industria_resumen: factor_quiebre promedio por industria
# ============================================================================

def vel_real_por_industria_resumen(meses=MESES_QUIEBRE_DEFAULT):
    """
    Retorna dict {industria: factor_quiebre_promedio} para uso rápido en calce_financiero.
    Lee de vel_real_articulo si existe, sino calcula on-the-fly con top 50 por industria.
    """
    # Intentar leer de tabla materializada primero
    try:
        sql = """
        SELECT
            ISNULL(ind.industria, 'Sin clasificar') AS industria,
            AVG(vra.factor_quiebre) AS factor_quiebre,
            AVG(vra.vel_aparente) AS vel_aparente_prom,
            AVG(vra.vel_real) AS vel_real_prom,
            COUNT(*) AS articulos
        FROM omicronvt.dbo.vel_real_articulo vra
        JOIN msgestion01art.dbo.articulo a ON a.codigo_sinonimo = vra.codigo
        LEFT JOIN omicronvt.dbo.map_subrubro_industria ind ON a.subrubro = ind.subrubro
        WHERE vra.vel_aparente > 0
        GROUP BY ISNULL(ind.industria, 'Sin clasificar')
        """
        rows = dbC.executesql(sql, as_dict=True)
        if rows:
            return {r['industria']: {
                'factor_quiebre': round(float(r['factor_quiebre'] or 1), 2),
                'vel_aparente_prom': round(float(r['vel_aparente_prom'] or 0), 2),
                'vel_real_prom': round(float(r['vel_real_prom'] or 0), 2),
                'articulos': int(r['articulos'] or 0),
            } for r in rows}
    except Exception:
        pass

    # Fallback: no hay tabla materializada, retornar vacío
    # (el caller usará factor_quiebre=1.0 por defecto)
    return {}
