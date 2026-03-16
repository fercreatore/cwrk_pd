# -*- coding: utf-8 -*-
import datetime
from collections import defaultdict

"""
CONTROLLER: informes_productividad
Nuevo módulo de Productividad e Incentivos para RRHH.
Replica y mejora la lógica de informes_efectividad/sueldos agregando:
  - Modelo de incentivos con bandas de margen
  - Factor estacional
  - Simulador de comisiones
  - Comparativo mensual con estacionalidad

URLs:
  /calzalindo_objetivos_v2/informes_productividad/dashboard        → Vista principal RRHH
  /calzalindo_objetivos_v2/informes_productividad/vendedor/{cod}   → Detalle individual
  /calzalindo_objetivos_v2/informes_productividad/incentivos       → Simulador de incentivos
  /calzalindo_objetivos_v2/informes_productividad/estacionalidad   → Análisis estacional
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
    0: 'Central', 1: 'Glam', 2: 'Norte', 4: 'Marroquinería',
    6: 'Cuore', 7: 'Eva Perón', 8: 'Junín', 9: 'Tokyo Express',
    15: 'Junín GO'
}


def _get_comision_banda(pct_margen):
    """Retorna (pct_comision, nombre_banda) según % margen"""
    for umbral, comision, nombre in BANDAS_MARGEN:
        if pct_margen >= umbral:
            return comision, nombre
    return 0.0, 'Sin banda'


def _get_bonus_prod(productividad):
    """Retorna % bonus según productividad"""
    for umbral, bonus in BONUS_PRODUCTIVIDAD:
        if productividad >= umbral:
            return bonus
    return 0.0


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
    rows = db1.executesql(sql, as_dict=True)
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
    return db_omicronvt.executesql(sql, as_dict=True)


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
    return db_omicronvt.executesql(sql, as_dict=True)


def _query_viajantes():
    """Todos los viajantes con nombre"""
    sql = "SELECT codigo, descripcion FROM viajantes"
    rows = dbC.executesql(sql, as_dict=True)
    return {r['codigo']: r['descripcion'] for r in rows}


def _query_turnos(desde, hasta, viajante):
    """Turnos atendidos por vendedor (MySQL db5)"""
    try:
        q = db5.executesql(
            "SELECT COUNT(nro) FROM turnos WHERE diaingreso >= '%s' AND diaingreso <= '%s' AND vendedor = %s"
            % (desde, hasta, viajante)
        )
        return q[0][0] if q and q[0][0] else 0
    except:
        return 0


# ─── DASHBOARD PRINCIPAL ─────────────────────────────────────────────
@auth.requires_membership('usuarios_nivel_1')
def dashboard():
    """IE-P001: Dashboard principal de productividad para RRHH"""

    hoy = request.now.date()
    hace_6m = hoy - datetime.timedelta(days=180)
    desde = request.vars.get('desde', hace_6m.strftime('%Y-%m-%d'))
    hasta = request.vars.get('hasta', hoy.strftime('%Y-%m-%d'))

    viajantes = _query_viajantes()
    sueldos = _query_sueldos(desde, hasta)
    ventas_raw = _query_ventas(desde, hasta)

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
        prod = vta / sueldo if sueldo > 0 else 0
        ppt = pares / tix if tix > 0 else 0
        vta_tix = vta / tix if tix > 0 else 0

        # Incentivos
        pct_com, banda = _get_comision_banda(pct_margen)
        bonus_prod = _get_bonus_prod(prod)
        comision_base = vta * pct_com
        bonus_monto = vta * bonus_prod

        # Turnos (intentar obtener)
        turnos = _query_turnos(desde, hasta, cod)
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

    # KPIs globales
    total_venta = sum(r['venta'] for r in rows)
    total_sueldo = sum(r['sueldo'] for r in rows if r['sueldo'] > 0)
    total_margen = sum(r['margen'] for r in rows)
    total_incentivo = sum(r['total_incentivo'] for r in rows)
    vendedores_con_sueldo = len([r for r in rows if r['sueldo'] > 0])
    pct_margen_global = total_margen / total_venta if total_venta > 0 else 0
    prod_promedio = total_venta / total_sueldo if total_sueldo > 0 else 0

    # Clasificación
    estrellas = [r for r in rows if r['sueldo'] > 0 and r['productividad'] >= 5 and r['pct_margen'] >= 0.45]
    revisar = [r for r in rows if r['sueldo'] > 0 and (r['productividad'] < 2 or r['pct_margen'] < 0.35)]

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
    )


# ─── DETALLE VENDEDOR ────────────────────────────────────────────────
@auth.requires_membership('usuarios_nivel_1')
def vendedor():
    """IE-P002: Detalle individual con evolución mensual"""

    cod_vendedor = int(request.args(0) or 0)
    if cod_vendedor == 0:
        redirect(URL('dashboard'))

    hoy = request.now.date()
    hace_12m = datetime.date(hoy.year - 1, hoy.month, 1)
    desde = hace_12m.strftime('%Y-%m-%d')
    hasta = hoy.strftime('%Y-%m-%d')

    viajantes = _query_viajantes()
    nombre = viajantes.get(cod_vendedor, 'Viajante %s' % cod_vendedor)

    # Sueldos últimos 6 meses
    desde_sueldo = (hoy - datetime.timedelta(days=180)).strftime('%Y-%m-%d')
    sueldos = _query_sueldos(desde_sueldo, hasta)
    sueldo = sueldos.get(cod_vendedor, 0)

    # Ventas mensuales últimos 12 meses
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
    meses_raw = db_omicronvt.executesql(sql_mensual, as_dict=True)

    meses = []
    for m in meses_raw:
        vta = float(m['valor'] or 0)
        costo = float(m['costo'] or 0)
        margen = vta - costo
        pct_m = margen / vta if vta > 0 else 0
        tix = int(m['tkts'] or 0)
        pares = float(m['pares'] or 0)
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

        turnos = _query_turnos(
            '%s-%02d-01' % (m['anio'], m['mes']),
            '%s-%02d-28' % (m['anio'], m['mes']),
            cod_vendedor
        )

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

    # Totales
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
    )


# ─── SIMULADOR DE INCENTIVOS ─────────────────────────────────────────
@auth.requires_membership('usuarios_nivel_1')
def incentivos():
    """IE-P003: Simulador de incentivos — RRHH puede ajustar bandas"""

    return dict(
        bandas=BANDAS_MARGEN,
        factor_estacional=FACTOR_ESTACIONAL,
        bonus_productividad=BONUS_PRODUCTIVIDAD,
        depositos=DEPOSITOS,
    )


# ─── ESTACIONALIDAD ──────────────────────────────────────────────────
@auth.requires_membership('usuarios_nivel_1')
def estacionalidad():
    """IE-P004: Análisis de estacionalidad global y por vendedor"""

    hoy = request.now.date()
    hace_12m = datetime.date(hoy.year - 1, hoy.month, 1)
    desde = hace_12m.strftime('%Y-%m-%d')
    hasta = hoy.strftime('%Y-%m-%d')

    mensual_raw = _query_ventas_mensual(desde, hasta)

    # Agregar por mes (global)
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

    return dict(
        meses=meses_data,
        promedio_mensual=promedio_mensual,
        factor_estacional=FACTOR_ESTACIONAL,
    )


# ─── API JSON (para charts) ──────────────────────────────────────────
def api_productividad():
    """Retorna JSON con datos de productividad para gráficos Highcharts"""
    hoy = request.now.date()
    hace_6m = hoy - datetime.timedelta(days=180)
    desde = request.vars.get('desde', hace_6m.strftime('%Y-%m-%d'))
    hasta = request.vars.get('hasta', hoy.strftime('%Y-%m-%d'))

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
        prod = vta / sueldo
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
    """JSON mensual para un vendedor específico"""
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
    rows = db_omicronvt.executesql(sql, as_dict=True)

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
