# -*- coding: utf-8 -*-
import datetime
import time
import json
from collections import defaultdict

"""
CONTROLLER: informes_productividad
Módulo de Productividad e Incentivos para RRHH.
Optimizado: queries batch, NOLOCK, medición de tiempos.

URLs:
  /calzalindo_informes/informes_productividad/dashboard
  /calzalindo_informes/informes_productividad/vendedor/{cod}
  /calzalindo_informes/informes_productividad/incentivos
  /calzalindo_informes/informes_productividad/estacionalidad
  /calzalindo_informes/informes_productividad/ticket_historico
"""

# ─── CONFIG INCENTIVOS ───────────────────────────────────────────────
BANDAS_MARGEN = [
    (0.55, 0.07, 'Elite'),
    (0.50, 0.055, 'Excelente'),
    (0.45, 0.04, 'Muy Bueno'),
    (0.40, 0.025, 'Bueno'),
    (0.35, 0.015, 'Aceptable'),
    (0.00, 0.00, 'Insuficiente'),
]

FACTOR_ESTACIONAL = {
    1: 0.9, 2: 1.0, 3: 1.3, 4: 1.2, 5: 1.1, 6: 1.0,
    7: 1.0, 8: 1.1, 9: 1.2, 10: 0.9, 11: 0.9, 12: 0.8
}

BONUS_PRODUCTIVIDAD = [
    (10.0, 0.02), (7.0, 0.015), (5.0, 0.01), (3.0, 0.005)
]

DEPOSITOS = {
    0: 'Central', 1: 'Glam', 2: 'Norte', 4: 'Marroquineria',
    6: 'Cuore', 7: 'Eva Peron', 8: 'Junin', 9: 'Tokyo Express',
    15: 'Junin GO'
}


# ─── HELPERS ─────────────────────────────────────────────────────────
def _timer():
    """Retorna dict para medir tiempos de queries"""
    return {'_start': time.time(), '_steps': []}

def _tick(t, label):
    """Registra un paso con su tiempo"""
    now = time.time()
    elapsed = now - t['_start']
    t['_steps'].append('%s: %.1fs' % (label, elapsed))
    t['_start'] = now

def _get_comision_banda(pct_margen):
    for umbral, comision, nombre in BANDAS_MARGEN:
        if pct_margen >= umbral:
            return comision, nombre
    return 0.0, 'Sin banda'

def _get_bonus_prod(productividad):
    for umbral, bonus in BONUS_PRODUCTIVIDAD:
        if productividad >= umbral:
            return bonus
    return 0.0


def _sql_mssql(db_conn, sql):
    """Ejecuta SQL en MSSQL con READ UNCOMMITTED (NOLOCK)"""
    db_conn.executesql("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return db_conn.executesql(sql, as_dict=True)


def _query_sueldos(desde, hasta):
    """Sueldos promedio por vendedor desde moviempl1"""
    sql = """
        SELECT SUM(moviempl1.importe) / (DATEDIFF(month, MIN(fecha_contable), MAX(fecha_contable)) + 1) AS sueldo,
               moviempl1.numero_cuenta
        FROM moviempl1
        WHERE moviempl1.codigo_movimiento IN (8, 10, 30, 31)
          AND moviempl1.fecha_contable >= '%s'
          AND moviempl1.fecha_contable <= '%s'
        GROUP BY moviempl1.numero_cuenta
    """ % (desde, hasta)
    rows = _sql_mssql(db1, sql)
    return {r['numero_cuenta']: float(r['sueldo']) for r in rows if r['sueldo']}


def _query_ventas(desde, hasta):
    """Ventas por vendedor desde ventas1_vendedor (omicronvt)"""
    sql = """
        SELECT SUM(total_item * cantidad) AS valor,
               SUM(precio_costo * cantidad) AS costo,
               SUM(cantidad) AS pares,
               (COUNT(DISTINCT(CASE WHEN codigo=1 THEN numero END))
                - COUNT(DISTINCT(CASE WHEN codigo=3 THEN numero END))) AS tkts,
               viajante
        FROM ventas1_vendedor
        WHERE fecha >= '%s' AND fecha <= '%s'
        GROUP BY viajante
    """ % (desde, hasta)
    return _sql_mssql(db_omicronvt, sql)


def _query_ventas_mensual(desde, hasta):
    """Ventas mensuales por vendedor"""
    sql = """
        SELECT SUM(total_item * cantidad) AS valor,
               SUM(precio_costo * cantidad) AS costo,
               SUM(cantidad) AS pares,
               (COUNT(DISTINCT(CASE WHEN codigo=1 THEN numero END))
                - COUNT(DISTINCT(CASE WHEN codigo=3 THEN numero END))) AS tkts,
               viajante,
               MONTH(fecha) AS mes,
               YEAR(fecha) AS anio
        FROM ventas1_vendedor
        WHERE fecha >= '%s' AND fecha <= '%s'
        GROUP BY viajante, MONTH(fecha), YEAR(fecha)
        ORDER BY viajante, YEAR(fecha), MONTH(fecha)
    """ % (desde, hasta)
    return _sql_mssql(db_omicronvt, sql)


def _query_viajantes():
    """Todos los viajantes con nombre"""
    if not dbC:
        return {}
    try:
        sql = "SELECT codigo, descripcion FROM viajantes"
        rows = dbC.executesql(sql, as_dict=True)
        return {r['codigo']: r['descripcion'] for r in rows}
    except:
        return {}


def _query_turnos_batch(desde, hasta):
    """Turnos por vendedor en UNA sola query (batch). Retorna dict {vendedor: count}"""
    if not db5:
        return {}
    try:
        q = db5.executesql(
            "SELECT vendedor, COUNT(nro) AS total FROM turnos "
            "WHERE diaingreso >= '%s' AND diaingreso <= '%s' "
            "GROUP BY vendedor" % (desde, hasta),
            as_dict=True
        )
        return {r['vendedor']: int(r['total'] or 0) for r in q}
    except:
        return {}


def _query_turnos_vendedor_mensual(desde, hasta, viajante):
    """Turnos mensuales de UN vendedor en una sola query. Retorna dict {(anio,mes): count}"""
    if not db5:
        return {}
    try:
        q = db5.executesql(
            "SELECT YEAR(diaingreso) AS anio, MONTH(diaingreso) AS mes, COUNT(nro) AS total "
            "FROM turnos WHERE diaingreso >= '%s' AND diaingreso <= '%s' AND vendedor = %s "
            "GROUP BY YEAR(diaingreso), MONTH(diaingreso)" % (desde, hasta, viajante),
            as_dict=True
        )
        return {(r['anio'], r['mes']): int(r['total'] or 0) for r in q}
    except:
        return {}


# ─── DASHBOARD PRINCIPAL ─────────────────────────────────────────────
def dashboard():
    """Dashboard principal de productividad para RRHH"""
    _requiere_acceso()
    t = _timer()

    hoy = request.now.date()
    hace_6m = hoy - datetime.timedelta(days=180)
    desde = request.vars.get('desde', hace_6m.strftime('%Y-%m-%d'))
    hasta = request.vars.get('hasta', hoy.strftime('%Y-%m-%d'))

    # Calcular meses en el periodo para mensualizar venta
    d_desde = datetime.datetime.strptime(desde, '%Y-%m-%d').date()
    d_hasta = datetime.datetime.strptime(hasta, '%Y-%m-%d').date()
    meses_periodo = max(1, (d_hasta.year - d_desde.year) * 12 + d_hasta.month - d_desde.month + 1)

    viajantes = _query_viajantes()
    _tick(t, 'viajantes')

    sueldos = _query_sueldos(desde, hasta)
    _tick(t, 'sueldos')

    ventas_raw = _query_ventas(desde, hasta)
    _tick(t, 'ventas')

    # UNA sola query para todos los turnos (en vez de N queries)
    turnos_map = _query_turnos_batch(desde, hasta)
    _tick(t, 'turnos_batch')

    rows = []
    for v in ventas_raw:
        cod = v['viajante']
        if not cod or cod == 0:
            continue
        vta = float(v['valor'] or 0)
        costo = float(v['costo'] or 0)
        pares = float(v['pares'] or 0)
        tix = int(v['tkts'] or 0)
        if vta < 10000:
            continue

        nombre = viajantes.get(cod, 'Viajante %s' % cod)
        sueldo = sueldos.get(cod, 0)
        margen = vta - costo
        pct_margen = margen / vta if vta > 0 else 0
        # Productividad = venta MENSUAL / sueldo MENSUAL
        vta_mensual = vta / meses_periodo
        prod = vta_mensual / sueldo if sueldo > 0 else 0
        ppt = pares / tix if tix > 0 else 0
        vta_tix = vta / tix if tix > 0 else 0

        # Incentivos
        pct_com, banda = _get_comision_banda(pct_margen)
        bonus_prod = _get_bonus_prod(prod)
        comision_base = vta * pct_com
        bonus_monto = vta * bonus_prod

        # Turnos (del batch, sin query individual)
        turnos = turnos_map.get(cod, 0)
        conversion = float(tix) / turnos if turnos > 0 else None

        rows.append(dict(
            codigo=cod,
            nombre=nombre,
            sueldo=sueldo,
            venta=vta,
            costo=costo,
            margen=margen,
            pct_margen=pct_margen,
            tickets=tix,
            pares=pares,
            pares_ticket=ppt,
            vta_ticket=vta_tix,
            productividad=prod,
            turnos=turnos,
            conversion=conversion,
            banda=banda,
            pct_comision=pct_com,
            comision_base=comision_base,
            bonus_prod=bonus_prod,
            bonus_monto=bonus_monto,
            total_incentivo=comision_base + bonus_monto,
        ))

    rows.sort(key=lambda x: x['productividad'], reverse=True)
    _tick(t, 'procesamiento')

    # KPIs globales
    total_venta = sum(r['venta'] for r in rows)
    total_sueldo = sum(r['sueldo'] for r in rows if r['sueldo'] > 0)
    total_margen = sum(r['margen'] for r in rows)
    total_incentivo = sum(r['total_incentivo'] for r in rows)
    vendedores_con_sueldo = len([r for r in rows if r['sueldo'] > 0])
    pct_margen_global = total_margen / total_venta if total_venta > 0 else 0
    prod_promedio = (total_venta / meses_periodo) / total_sueldo if total_sueldo > 0 else 0

    estrellas = [r for r in rows if r['sueldo'] > 0 and r['productividad'] >= 5 and r['pct_margen'] >= 0.45]
    revisar = [r for r in rows if r['sueldo'] > 0 and (r['productividad'] < 2 or r['pct_margen'] < 0.35)]

    total_time = time.time() - (t['_start'] - sum(float(s.split(': ')[1].replace('s','')) for s in t['_steps']))

    # Pre-serializar datos del chart como JSON (evita problemas de encoding en template)
    chart_data = []
    for r in rows:
        if r['sueldo'] > 0:
            chart_data.append({
                'x': round(float(r['pct_margen'] * 100), 1),
                'y': round(float(r['productividad']), 1),
                'name': str(r['nombre']),
                'cod': int(r['codigo'])
            })
    chart_json = json.dumps(chart_data, ensure_ascii=False)

    return dict(
        rows=rows,
        desde=desde,
        hasta=hasta,
        total_venta=total_venta,
        total_sueldo=total_sueldo,
        total_margen=total_margen,
        total_incentivo=total_incentivo,
        pct_margen_global=pct_margen_global,
        prod_promedio=prod_promedio,
        vendedores_con_sueldo=vendedores_con_sueldo,
        estrellas=estrellas,
        revisar=revisar,
        depositos=DEPOSITOS,
        bandas=BANDAS_MARGEN,
        chart_json=chart_json,
        timing=t['_steps'],
        es_admin=_es_admin(),
        puede_ver=_puede_ver,
        roles=_roles_usuario(),
    )


# ─── DETALLE VENDEDOR ────────────────────────────────────────────────
def vendedor():
    """Detalle individual con evolucion mensual"""
    _requiere_acceso()
    t = _timer()

    cod_vendedor = int(request.args(0) or 0)
    if cod_vendedor == 0:
        redirect(URL('informes_productividad', 'dashboard'))

    hoy = request.now.date()
    hace_12m = datetime.date(hoy.year - 1, hoy.month, 1)
    desde = hace_12m.strftime('%Y-%m-%d')
    hasta = hoy.strftime('%Y-%m-%d')

    viajantes = _query_viajantes()
    nombre = viajantes.get(cod_vendedor, 'Viajante %s' % cod_vendedor)
    _tick(t, 'viajantes')

    # Sueldos ultimos 6 meses
    desde_sueldo = (hoy - datetime.timedelta(days=180)).strftime('%Y-%m-%d')
    sueldos = _query_sueldos(desde_sueldo, hasta)
    sueldo = sueldos.get(cod_vendedor, 0)
    _tick(t, 'sueldos')

    # Ventas mensuales ultimos 12 meses
    sql_mensual = """
        SELECT SUM(total_item * cantidad) AS valor,
               SUM(precio_costo * cantidad) AS costo,
               SUM(cantidad) AS pares,
               (COUNT(DISTINCT(CASE WHEN codigo=1 THEN numero END))
                - COUNT(DISTINCT(CASE WHEN codigo=3 THEN numero END))) AS tkts,
               MONTH(fecha) AS mes,
               YEAR(fecha) AS anio
        FROM ventas1_vendedor
        WHERE fecha >= '%s' AND fecha <= '%s' AND viajante = %s
        GROUP BY MONTH(fecha), YEAR(fecha)
        ORDER BY YEAR(fecha), MONTH(fecha)
    """ % (desde, hasta, cod_vendedor)
    meses_raw = _sql_mssql(db_omicronvt, sql_mensual)
    _tick(t, 'ventas_mensual')

    # Turnos mensuales en UNA query (en vez de 12)
    turnos_mes = _query_turnos_vendedor_mensual(desde, hasta, cod_vendedor)
    _tick(t, 'turnos_mensual')

    meses = []
    for m in meses_raw:
        vta = float(m['valor'] or 0)
        costo = float(m['costo'] or 0)
        margen = vta - costo
        pct_m = margen / vta if vta > 0 else 0
        tix = int(m['tkts'] or 0)
        pares = float(m['pares'] or 0)
        # Productividad = venta de ESE MES / sueldo mensual
        prod = vta / sueldo if sueldo > 0 else 0
        pct_com, banda = _get_comision_banda(pct_m)
        factor_est = FACTOR_ESTACIONAL.get(m['mes'], 1.0)
        comision_ajustada = vta * pct_com * factor_est

        # CER adjustment
        fecha_mes = '%s-%02d-15' % (m['anio'], m['mes'])
        try:
            vta_cer = fx_AjustarPorCer(vta, fecha_mes)
        except:
            vta_cer = vta

        turnos = turnos_mes.get((m['anio'], m['mes']), 0)

        meses.append(dict(
            mes=m['mes'],
            anio=m['anio'],
            mes_label='%02d/%s' % (m['mes'], m['anio']),
            venta=vta,
            venta_cer=vta_cer,
            costo=costo,
            margen=margen,
            pct_margen=pct_m,
            tickets=tix,
            pares=pares,
            pares_ticket=pares / tix if tix > 0 else 0,
            productividad=prod,
            banda=banda,
            factor_estacional=factor_est,
            comision_ajustada=comision_ajustada,
            turnos=turnos,
            conversion=float(tix) / turnos if turnos > 0 else None,
        ))
    _tick(t, 'procesamiento')

    total_venta = sum(m['venta'] for m in meses)
    total_margen = sum(m['margen'] for m in meses)
    total_incentivo = sum(m['comision_ajustada'] for m in meses)

    return dict(
        cod_vendedor=cod_vendedor,
        nombre=nombre,
        sueldo=sueldo,
        meses=meses,
        total_venta=total_venta,
        total_margen=total_margen,
        total_incentivo=total_incentivo,
        factor_estacional=FACTOR_ESTACIONAL,
        bandas=BANDAS_MARGEN,
        timing=t['_steps'],
        es_admin=_es_admin(),
        puede_ver=_puede_ver,
        roles=_roles_usuario(),
    )


# ─── SIMULADOR DE INCENTIVOS ─────────────────────────────────────────
def incentivos():
    """Simulador de incentivos"""
    _requiere_acceso()

    return dict(
        bandas=BANDAS_MARGEN,
        factor_estacional=FACTOR_ESTACIONAL,
        bonus_productividad=BONUS_PRODUCTIVIDAD,
        depositos=DEPOSITOS,
        es_admin=_es_admin(),
        puede_ver=_puede_ver,
        roles=_roles_usuario(),
    )


# ─── ESTACIONALIDAD ──────────────────────────────────────────────────
def estacionalidad():
    """Analisis de estacionalidad global y por vendedor"""
    _requiere_acceso()
    t = _timer()

    hoy = request.now.date()
    hace_12m = datetime.date(hoy.year - 1, hoy.month, 1)
    desde = hace_12m.strftime('%Y-%m-%d')
    hasta = hoy.strftime('%Y-%m-%d')

    mensual_raw = _query_ventas_mensual(desde, hasta)
    _tick(t, 'ventas_mensual')

    por_mes = defaultdict(lambda: {'venta': 0, 'costo': 0, 'tickets': 0, 'pares': 0})
    for r in mensual_raw:
        key = (r['anio'], r['mes'])
        por_mes[key]['venta'] += float(r['valor'] or 0)
        por_mes[key]['costo'] += float(r['costo'] or 0)
        por_mes[key]['tickets'] += int(r['tkts'] or 0)
        por_mes[key]['pares'] += float(r['pares'] or 0)

    promedio_mensual = sum(d['venta'] for d in por_mes.values()) / max(len(por_mes), 1)

    meses_data = []
    for (anio, mes), d in sorted(por_mes.items()):
        indice = d['venta'] / promedio_mensual if promedio_mensual > 0 else 1
        meses_data.append(dict(
            anio=anio,
            mes=mes,
            label='%02d/%s' % (mes, anio),
            venta=d['venta'],
            costo=d['costo'],
            margen=d['venta'] - d['costo'],
            pct_margen=(d['venta'] - d['costo']) / d['venta'] if d['venta'] > 0 else 0,
            tickets=d['tickets'],
            pares=d['pares'],
            indice_estacional=indice,
            factor_propuesto=FACTOR_ESTACIONAL.get(mes, 1.0),
        ))
    _tick(t, 'procesamiento')

    return dict(
        meses=meses_data,
        promedio_mensual=promedio_mensual,
        factor_estacional=FACTOR_ESTACIONAL,
        timing=t['_steps'],
        es_admin=_es_admin(),
        puede_ver=_puede_ver,
        roles=_roles_usuario(),
    )


# ─── TICKET HISTORICO E INDEXACION ────────────────────────────────────

# Salario Maestranza B - CCT 130/75 Empleados de Comercio
# Datos de paritarias FAECyS. Formato: {(anio, mes): basico_bruto}
# Se usa el valor vigente a inicio de cada mes.
MAESTRANZA_B = {
    # 2015 - Acuerdo abr 2015 (21% s/ 2014)
    (2015, 1): 8200, (2015, 2): 8200, (2015, 3): 8200,
    (2015, 4): 9060, (2015, 5): 9060, (2015, 6): 9340,
    (2015, 7): 9340, (2015, 8): 9340, (2015, 9): 9340,
    (2015, 10): 9920, (2015, 11): 9920, (2015, 12): 9920,
    # 2016 - Acuerdo abr 2016 (31% en 2 tramos)
    (2016, 1): 10580, (2016, 2): 10580, (2016, 3): 10580,
    (2016, 4): 11900, (2016, 5): 11900, (2016, 6): 11900,
    (2016, 7): 11900, (2016, 8): 11900, (2016, 9): 11900,
    (2016, 10): 13000, (2016, 11): 13000, (2016, 12): 13000,
    # 2017 - Acuerdo abr 2017 (22%)
    (2017, 1): 13650, (2017, 2): 13650, (2017, 3): 13650,
    (2017, 4): 14950, (2017, 5): 14950, (2017, 6): 14950,
    (2017, 7): 15300, (2017, 8): 15300, (2017, 9): 15300,
    (2017, 10): 15860, (2017, 11): 15860, (2017, 12): 15860,
    # 2018 - Acuerdo jun 2018 (~25% + revisiones)
    (2018, 1): 16500, (2018, 2): 16500, (2018, 3): 16500,
    (2018, 4): 17500, (2018, 5): 17500, (2018, 6): 18200,
    (2018, 7): 18900, (2018, 8): 18900, (2018, 9): 19600,
    (2018, 10): 20200, (2018, 11): 20200, (2018, 12): 21800,
    # 2019 - Acuerdo may 2019 (~30%)
    (2019, 1): 22500, (2019, 2): 22500, (2019, 3): 22500,
    (2019, 4): 25000, (2019, 5): 26200, (2019, 6): 26200,
    (2019, 7): 27500, (2019, 8): 28800, (2019, 9): 30000,
    (2019, 10): 31000, (2019, 11): 32500, (2019, 12): 34000,
    # 2020 - COVID, DNU + acuerdos parciales
    (2020, 1): 35000, (2020, 2): 35000, (2020, 3): 37000,
    (2020, 4): 37000, (2020, 5): 39000, (2020, 6): 39000,
    (2020, 7): 41000, (2020, 8): 41000, (2020, 9): 43000,
    (2020, 10): 43000, (2020, 11): 45000, (2020, 12): 45000,
    # 2021 - Acuerdo may 2021 (32% NR + incorporaciones)
    (2021, 1): 47000, (2021, 2): 47000, (2021, 3): 49000,
    (2021, 4): 49000, (2021, 5): 51000, (2021, 6): 53000,
    (2021, 7): 55000, (2021, 8): 57000, (2021, 9): 59000,
    (2021, 10): 61000, (2021, 11): 64000, (2021, 12): 67000,
    # 2022 - Acuerdo abr 2022 (59.5% escalonado)
    (2022, 1): 70000, (2022, 2): 73000, (2022, 3): 76000,
    (2022, 4): 92687, (2022, 5): 97934, (2022, 6): 103180,
    (2022, 7): 103180, (2022, 8): 121106, (2022, 9): 129850,
    (2022, 10): 129850, (2022, 11): 139468, (2022, 12): 139468,
    # 2023 - Acuerdos bimestrales
    (2023, 1): 139468, (2023, 2): 157599, (2023, 3): 173202,
    (2023, 4): 173202, (2023, 5): 210000, (2023, 6): 230000,
    (2023, 7): 260000, (2023, 8): 290000, (2023, 9): 330000,
    (2023, 10): 380000, (2023, 11): 430000, (2023, 12): 510000,
    # 2024 - Acuerdos mensuales post-devaluacion
    (2024, 1): 580000, (2024, 2): 660000, (2024, 3): 710000,
    (2024, 4): 745000, (2024, 5): 780000, (2024, 6): 810000,
    (2024, 7): 835000, (2024, 8): 860000, (2024, 9): 880000,
    (2024, 10): 895000, (2024, 11): 898401, (2024, 12): 898401,
    # 2025 - Acuerdos trimestrales
    (2025, 1): 916319, (2025, 2): 916319, (2025, 3): 932000,
    (2025, 4): 960000, (2025, 5): 985000, (2025, 6): 1010000,
    (2025, 7): 1035000, (2025, 8): 1050000, (2025, 9): 1065000,
    (2025, 10): 1078874, (2025, 11): 1100000, (2025, 12): 1130000,
    # 2026
    (2026, 1): 1158852, (2026, 2): 1158852, (2026, 3): 1158852,
}


def ticket_historico():
    """Analisis historico de ticket promedio con indexaciones (CER, Xforcer, Maestranza B)"""
    _requiere_acceso()
    t = _timer()

    # 1) Ticket promedio mensual
    sql_ticket = """
        SELECT YEAR(fecha) AS anio, MONTH(fecha) AS mes,
               SUM(total_item) AS venta_total,
               SUM(cantidad) AS pares,
               COUNT(DISTINCT CAST(sucursal AS VARCHAR) + '-' + letra + '-' + CAST(numero AS VARCHAR)) AS tickets
        FROM ventas1_vendedor
        WHERE fecha >= '2015-01-01' AND cantidad > 0 AND total_item > 0
        GROUP BY YEAR(fecha), MONTH(fecha)
        ORDER BY YEAR(fecha), MONTH(fecha)
    """
    ticket_raw = _sql_mssql(db_omicronvt, sql_ticket)
    _tick(t, 'ticket_promedio')

    # 2) Precio Xforcer 21872 mensual
    sql_xforcer = """
        SELECT YEAR(fecha) AS anio, MONTH(fecha) AS mes,
               AVG(total_item / cantidad) AS precio_promedio,
               SUM(cantidad) AS unidades
        FROM ventas1_vendedor
        WHERE LEFT(descripcion_1, 5) = '21872'
          AND cantidad > 0 AND total_item > 0
          AND fecha >= '2015-01-01'
        GROUP BY YEAR(fecha), MONTH(fecha)
        ORDER BY YEAR(fecha), MONTH(fecha)
    """
    xforcer_raw = _sql_mssql(db_omicronvt, sql_xforcer)
    xforcer_map = {}
    for x in xforcer_raw:
        xforcer_map[(x['anio'], x['mes'])] = float(x['precio_promedio'] or 0)
    _tick(t, 'xforcer_precios')

    # 3) CER - coeficientes en una sola query batch (UNION ALL)
    cer_map = {}
    if ticket_raw:
        # Armar query batch: SELECT fecha, coef UNION ALL ...
        cer_parts = []
        for r in ticket_raw:
            fecha_str = '%s-%02d-15' % (r['anio'], r['mes'])
            cer_parts.append(
                "SELECT %d AS anio, %d AS mes, omicronvt.dbo.AjustarPorCer(1, '%s') AS coef"
                % (r['anio'], r['mes'], fecha_str)
            )
        # SQL Server puede manejar UNION ALL de muchos SELECTs
        cer_sql = ' UNION ALL '.join(cer_parts)
        try:
            cer_rows = _sql_mssql(db_omicronvt, cer_sql)
            for cr in cer_rows:
                cer_map[(int(cr['anio']), int(cr['mes']))] = float(cr['coef']) if cr['coef'] else 1.0
        except:
            # Fallback: si falla batch, intentar uno por uno (mas lento)
            for r in ticket_raw:
                key = (r['anio'], r['mes'])
                try:
                    q = db_omicronvt.executesql(
                        "SELECT omicronvt.dbo.AjustarPorCer(1, '%s-%02d-15')" % (r['anio'], r['mes'])
                    )
                    cer_map[key] = float(q[0][0]) if q and q[0][0] else 1.0
                except:
                    cer_map[key] = 1.0
    _tick(t, 'cer_coeficientes')

    # Valores base para indexar (Ene 2015 = 100)
    base_ticket = None
    base_xforcer = None
    base_salario = None
    base_precio_par = None

    # Armar filas
    filas = []
    ultimo_xforcer = 0  # carry forward si no hay dato un mes
    for r in ticket_raw:
        anio = r['anio']
        mes = r['mes']
        key = (anio, mes)
        vta = float(r['venta_total'] or 0)
        pares = float(r['pares'] or 0)
        tix = int(r['tickets'] or 0)
        ticket_prom = vta / tix if tix > 0 else 0
        precio_par = vta / pares if pares > 0 else 0

        xforcer_precio = xforcer_map.get(key, 0)
        if xforcer_precio > 0:
            ultimo_xforcer = xforcer_precio
        else:
            xforcer_precio = ultimo_xforcer

        salario = MAESTRANZA_B.get(key, 0)
        cer_coef = cer_map.get(key, 1.0)

        # Ticket en CER (deflactado)
        ticket_cer = ticket_prom * cer_coef

        # Cuantos pares de Xforcer compra un ticket
        xforcer_ratio = ticket_prom / xforcer_precio if xforcer_precio > 0 else 0

        # Cuantos tickets para un sueldo
        salario_tickets = salario / ticket_prom if ticket_prom > 0 else 0

        # Bases para indice 100
        if base_ticket is None and ticket_prom > 0:
            base_ticket = ticket_prom
        if base_xforcer is None and xforcer_precio > 0:
            base_xforcer = xforcer_precio
        if base_salario is None and salario > 0:
            base_salario = salario
        if base_precio_par is None and precio_par > 0:
            base_precio_par = precio_par

        filas.append(dict(
            anio=anio, mes=mes,
            label='%02d/%s' % (mes, anio),
            venta_total=vta,
            pares=pares,
            tickets=tix,
            ticket_prom=ticket_prom,
            precio_par=precio_par,
            xforcer_precio=xforcer_precio,
            salario=salario,
            cer_coef=cer_coef,
            ticket_cer=ticket_cer,
            xforcer_ratio=xforcer_ratio,
            salario_tickets=salario_tickets,
            idx_ticket=ticket_prom / base_ticket * 100 if base_ticket else 0,
            idx_xforcer=xforcer_precio / base_xforcer * 100 if base_xforcer else 0,
            idx_salario=salario / base_salario * 100 if base_salario else 0,
            idx_precio_par=precio_par / base_precio_par * 100 if base_precio_par else 0,
            idx_ticket_cer=ticket_cer / (base_ticket * cer_map.get((2015, 1), 1.0)) * 100 if base_ticket else 0,
        ))
    _tick(t, 'procesamiento')

    # Pre-serializar para charts (evita problemas de Decimal en template)
    chart_labels = []
    chart_ticket_cer = []
    chart_idx_ticket = []
    chart_idx_xforcer = []
    chart_idx_salario = []
    chart_xforcer_ratio = []
    chart_salario_tickets = []

    for f in filas:
        chart_labels.append(f['label'])
        chart_ticket_cer.append(round(f['ticket_cer'], 0))
        chart_idx_ticket.append(round(f['idx_ticket'], 1))
        chart_idx_xforcer.append(round(f['idx_xforcer'], 1))
        chart_idx_salario.append(round(f['idx_salario'], 1))
        chart_xforcer_ratio.append(round(f['xforcer_ratio'], 3))
        chart_salario_tickets.append(round(f['salario_tickets'], 1))

    charts_json = json.dumps({
        'labels': chart_labels,
        'ticket_cer': chart_ticket_cer,
        'idx_ticket': chart_idx_ticket,
        'idx_xforcer': chart_idx_xforcer,
        'idx_salario': chart_idx_salario,
        'xforcer_ratio': chart_xforcer_ratio,
        'salario_tickets': chart_salario_tickets,
    }, ensure_ascii=False)

    return dict(
        filas=filas,
        charts_json=charts_json,
        timing=t['_steps'],
        es_admin=_es_admin(),
        puede_ver=_puede_ver,
        roles=_roles_usuario(),
    )


# ─── API JSON (para charts) ──────────────────────────────────────────
def api_productividad():
    """JSON con datos de productividad para Highcharts"""
    hoy = request.now.date()
    hace_6m = hoy - datetime.timedelta(days=180)
    desde = request.vars.get('desde', hace_6m.strftime('%Y-%m-%d'))
    hasta = request.vars.get('hasta', hoy.strftime('%Y-%m-%d'))

    # Meses en el periodo
    d_desde = datetime.datetime.strptime(desde, '%Y-%m-%d').date()
    d_hasta = datetime.datetime.strptime(hasta, '%Y-%m-%d').date()
    meses_p = max(1, (d_hasta.year - d_desde.year) * 12 + d_hasta.month - d_desde.month + 1)

    sueldos = _query_sueldos(desde, hasta)
    ventas_raw = _query_ventas(desde, hasta)
    viajantes = _query_viajantes()

    data = []
    for v in ventas_raw:
        cod = v['viajante']
        if not cod or cod == 0:
            continue
        vta = float(v['valor'] or 0)
        costo = float(v['costo'] or 0)
        sueldo = sueldos.get(cod, 0)
        if sueldo == 0 or vta < 100000:
            continue
        prod = (vta / meses_p) / sueldo
        pct_m = (vta - costo) / vta if vta > 0 else 0
        data.append(dict(
            nombre=viajantes.get(cod, str(cod)),
            codigo=cod,
            productividad=round(prod, 2),
            margen=round(pct_m * 100, 1),
            venta=round(vta),
            sueldo=round(sueldo),
        ))

    data.sort(key=lambda x: x['productividad'], reverse=True)
    return response.json(data)


def api_estacionalidad_vendedor():
    """JSON mensual para un vendedor"""
    cod = int(request.vars.get('cod', 0))
    if cod == 0:
        return response.json([])

    hoy = request.now.date()
    hace_12m = datetime.date(hoy.year - 1, hoy.month, 1)
    sql = """
        SELECT SUM(total_item * cantidad) AS valor,
               SUM(precio_costo * cantidad) AS costo,
               MONTH(fecha) AS mes, YEAR(fecha) AS anio
        FROM ventas1_vendedor
        WHERE fecha >= '%s' AND fecha <= '%s' AND viajante = %s
        GROUP BY MONTH(fecha), YEAR(fecha)
        ORDER BY YEAR(fecha), MONTH(fecha)
    """ % (hace_12m.strftime('%Y-%m-%d'), hoy.strftime('%Y-%m-%d'), cod)
    rows = _sql_mssql(db_omicronvt, sql)

    data = []
    for r in rows:
        vta = float(r['valor'] or 0)
        costo = float(r['costo'] or 0)
        data.append(dict(
            label='%02d/%s' % (r['mes'], r['anio']),
            venta=round(vta),
            margen=round(vta - costo),
            pct_margen=round((vta - costo) / vta * 100, 1) if vta > 0 else 0,
        ))

    return response.json(data)
