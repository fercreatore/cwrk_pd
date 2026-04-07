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
# Defaults — se sobreescriben desde tabla omicronvt.dbo.config_incentivos si existe
BANDAS_MARGEN_DEFAULT = [
    (0.55, 0.07, 'Elite'),
    (0.50, 0.055, 'Excelente'),
    (0.45, 0.04, 'Muy Bueno'),
    (0.40, 0.025, 'Bueno'),
    (0.35, 0.015, 'Aceptable'),
    (0.00, 0.00, 'Insuficiente'),
]

FACTOR_ESTACIONAL_DEFAULT = {
    1: 0.9, 2: 1.0, 3: 1.3, 4: 1.2, 5: 1.1, 6: 1.0,
    7: 1.0, 8: 1.1, 9: 1.2, 10: 0.9, 11: 0.9, 12: 0.8
}

BONUS_PRODUCTIVIDAD_DEFAULT = [
    (10.0, 0.02), (7.0, 0.015), (5.0, 0.01), (3.0, 0.005)
]

DEPOSITOS = {
    0: 'Central', 1: 'Glam', 2: 'Norte', 4: 'Marroquineria',
    6: 'Cuore', 7: 'Eva Peron', 8: 'Junin', 9: 'Tokyo Express',
    15: 'Junin GO'
}

# ─── FACTORES COSTO LABORAL (3 ESCENARIOS) ───────────────────────────
# Escenario 1: Blanqueado ideal (CCT 130/75 completo)
#   +16% jubilación + 2% PAMI + 6% OS patronal + 2.5% ART + 0.5% Seg.Vida
#   + 8.33% SAC + 8.33% vacaciones proporcionales = +58.33%
FACTOR_BLANQUEADO = 1.5833

# Escenario 2: Realidad contable
#   Ratio leyes sociales / sueldos medido en co_movact_v abr-dic 2025 ≈ 12%
#   (5012100 Leyes Sociales / 501200x Sueldos comercialización)
FACTOR_REAL_CONTABLE = 1.12

# Escenario 3: Freelance — fee sobre venta mensual
# Breakeven vendedor: fee_indif = sueldo_neto / vta_mensual ≈ 0.80/productividad
# Breakeven H4 vs blanqueado: fee = 1.5833/productividad
# 8% es el punto donde H4 gana ≥ realidad contable para la mayoría de los vendedores
FEE_FREELANCE = 0.08

# Sucursales agrupadas por deposito para comparativo
SUCURSALES = {
    0: 'Central 263', 1: 'Glam', 2: 'Norte', 4: 'Marroquineria',
    6: 'Cuore', 7: 'Eva Peron', 8: 'Junin', 9: 'Tokyo Express',
    15: 'Junin GO'
}


def _cargar_config_incentivos():
    """Intenta cargar bandas/factores desde omicronvt.dbo.config_incentivos.
    Si la tabla no existe o falla, usa defaults."""
    global BANDAS_MARGEN, FACTOR_ESTACIONAL, BONUS_PRODUCTIVIDAD
    try:
        rows = db_omicronvt.executesql(
            "SELECT tipo, umbral, valor, nombre FROM config_incentivos ORDER BY tipo, umbral DESC",
            as_dict=True
        )
        if rows:
            bandas = []
            factores = {}
            bonus = []
            for r in rows:
                if r['tipo'] == 'BANDA':
                    bandas.append((float(r['umbral']), float(r['valor']), r['nombre']))
                elif r['tipo'] == 'FACTOR_EST':
                    factores[int(r['umbral'])] = float(r['valor'])
                elif r['tipo'] == 'BONUS_PROD':
                    bonus.append((float(r['umbral']), float(r['valor'])))
            if bandas:
                BANDAS_MARGEN = bandas
            if factores:
                FACTOR_ESTACIONAL = factores
            if bonus:
                BONUS_PRODUCTIVIDAD = bonus
            return True
    except:
        pass
    BANDAS_MARGEN = BANDAS_MARGEN_DEFAULT
    FACTOR_ESTACIONAL = FACTOR_ESTACIONAL_DEFAULT
    BONUS_PRODUCTIVIDAD = BONUS_PRODUCTIVIDAD_DEFAULT
    return False

# Cargar al iniciar
_config_desde_db = _cargar_config_incentivos()


# ─── HELPERS ─────────────────────────────────────────────────────────
def _timer():
    """Retorna dict para medir tiempos de queries"""
    return {'_start': time.time(), '_steps': []}


def _parse_date(val, fallback):
    """Parsea una fecha en formato YYYY-MM-DD. Si falla, retorna fallback."""
    try:
        return datetime.datetime.strptime(val, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return fallback

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


def _query_cargas_sociales_global(desde, hasta):
    """Suma total de cargas sociales registradas en contabilidad (co_movact_v).
    Cuentas: 5012100 Leyes Sociales Comerc, 5012200 Cuota Sindical, 5020500 Leyes Soc Admin.
    Retorna dict con sueldos_contables, cargas_contables, total_contable."""
    sql = """
        SELECT
            SUM(CASE WHEN cuenta IN ('5012000','5012001','5012002','5020400') THEN debe ELSE 0 END) AS sueldos,
            SUM(CASE WHEN cuenta IN ('5012100','5020500') THEN debe ELSE 0 END) AS leyes_sociales,
            SUM(CASE WHEN cuenta = '5012200' THEN debe ELSE 0 END) AS cuota_sindical
        FROM co_movact_v
        WHERE cuenta IN ('5012000','5012001','5012002','5012100','5012200','5020400','5020500')
          AND fecha >= '%s' AND fecha <= '%s'
    """ % (desde, hasta)
    try:
        rows = _sql_mssql(dbC, sql)
        if rows:
            r = rows[0]
            sueldos = float(r['sueldos'] or 0)
            cargas = float(r['leyes_sociales'] or 0) + float(r['cuota_sindical'] or 0)
            return {'sueldos': sueldos, 'cargas': cargas, 'total': sueldos + cargas}
    except:
        pass
    return {'sueldos': 0, 'cargas': 0, 'total': 0}


def _query_sueldos(desde, hasta):
    """Sueldos promedio por vendedor desde moviempl1.
    Usa msgestion01.dbo.moviempl1 con codigo_movimiento=10 (sueldo bruto).
    Codigo 10 = bruto, 7 = neto, 11 = retenciones. Se usa 10 para costo real al empleador.
    """
    sql = """
        SELECT SUM(m.importe) / (DATEDIFF(month, MIN(m.fecha_contable), MAX(m.fecha_contable)) + 1) AS sueldo,
               m.numero_cuenta
        FROM msgestion01.dbo.moviempl1 m
        WHERE m.codigo_movimiento = 10
          AND m.fecha_contable >= '%s'
          AND m.fecha_contable <= '%s'
        GROUP BY m.numero_cuenta
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
    d_desde = _parse_date(request.vars.get('desde'), hace_6m)
    d_hasta = _parse_date(request.vars.get('hasta'), hoy)
    if d_desde > d_hasta:
        d_desde, d_hasta = d_hasta, d_desde
    desde = d_desde.strftime('%Y-%m-%d')
    hasta = d_hasta.strftime('%Y-%m-%d')

    # Calcular meses en el periodo para mensualizar venta
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

        # ── 3 escenarios de costo laboral ──
        costo_blanqueado  = sueldo * FACTOR_BLANQUEADO   if sueldo > 0 else 0
        costo_real        = sueldo * FACTOR_REAL_CONTABLE if sueldo > 0 else 0
        costo_freelance   = vta_mensual * FEE_FREELANCE
        ahorro_freelance  = costo_blanqueado - costo_freelance   # ahorro potencial vs blanqueado
        brecha_informalidad = costo_blanqueado - costo_real      # lo que "falta" declarar
        # fee_indif: fee mínimo para que el vendedor no gane menos que su sueldo neto actual
        # sueldo_neto ≈ sueldo * 0.83 (17% retenciones) → fee_indif = sueldo_neto / vta_mensual
        fee_indif = (sueldo * 0.83) / vta_mensual if vta_mensual > 0 and sueldo > 0 else None
        # fee_h4_break: fee donde H4 iguala lo que paga hoy (costo_real)
        fee_h4_break = costo_real / vta_mensual if vta_mensual > 0 and sueldo > 0 else None

        rows.append(dict(
            codigo=cod,
            nombre=nombre,
            sueldo=sueldo,
            venta=vta,
            vta_mensual=vta_mensual,
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
            # escenarios costo laboral
            costo_blanqueado=costo_blanqueado,
            costo_real=costo_real,
            costo_freelance=costo_freelance,
            ahorro_freelance=ahorro_freelance,
            brecha_informalidad=brecha_informalidad,
            fee_indif=fee_indif,
            fee_h4_break=fee_h4_break,
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

    # KPIs de costo laboral — 3 escenarios (solo vendedores con sueldo registrado)
    rows_con_sueldo = [r for r in rows if r['sueldo'] > 0]
    total_costo_blanqueado  = sum(r['costo_blanqueado']  for r in rows_con_sueldo)
    total_costo_real        = sum(r['costo_real']        for r in rows_con_sueldo)
    total_costo_freelance   = sum(r['costo_freelance']   for r in rows_con_sueldo)
    total_ahorro_freelance  = total_costo_blanqueado - total_costo_freelance
    total_brecha_informal   = total_costo_blanqueado - total_costo_real

    # Datos reales de contabilidad para contexto (co_movact_v)
    cargas_contables = _query_cargas_sociales_global(desde, hasta)
    _tick(t, 'cargas_contables')

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
        # 3 escenarios costo laboral
        total_costo_blanqueado=total_costo_blanqueado,
        total_costo_real=total_costo_real,
        total_costo_freelance=total_costo_freelance,
        total_ahorro_freelance=total_ahorro_freelance,
        total_brecha_informal=total_brecha_informal,
        cargas_contables=cargas_contables,
        factor_blanqueado=FACTOR_BLANQUEADO,
        factor_real=FACTOR_REAL_CONTABLE,
        fee_freelance=FEE_FREELANCE,
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


# ─── COMPARATIVO SUCURSALES ──────────────────────────────────────────
def sucursales():
    """Comparativo de productividad entre sucursales/depositos"""
    _requiere_acceso()
    t = _timer()

    hoy = request.now.date()
    hace_6m = hoy - datetime.timedelta(days=180)
    desde = request.vars.get('desde', hace_6m.strftime('%Y-%m-%d'))
    hasta = request.vars.get('hasta', hoy.strftime('%Y-%m-%d'))

    d_desde = datetime.datetime.strptime(desde, '%Y-%m-%d').date()
    d_hasta = datetime.datetime.strptime(hasta, '%Y-%m-%d').date()
    meses_periodo = max(1, (d_hasta.year - d_desde.year) * 12 + d_hasta.month - d_desde.month + 1)

    # Ventas por sucursal (deposito de ventas1_vendedor)
    sql = """
        SELECT deposito,
               SUM(total_item * cantidad) AS venta,
               SUM(precio_costo * cantidad) AS costo,
               SUM(cantidad) AS pares,
               (COUNT(DISTINCT(CASE WHEN codigo=1 THEN numero END))
                - COUNT(DISTINCT(CASE WHEN codigo=3 THEN numero END))) AS tickets,
               COUNT(DISTINCT viajante) AS vendedores
        FROM ventas1_vendedor
        WHERE fecha >= '%s' AND fecha <= '%s'
        GROUP BY deposito
        ORDER BY SUM(total_item * cantidad) DESC
    """ % (desde, hasta)
    rows = _sql_mssql(db_omicronvt, sql)
    _tick(t, 'ventas_sucursal')

    # Sueldos por deposito (necesitamos mapear viajante → deposito)
    # Por ahora usar promedio global
    sueldos = _query_sueldos(desde, hasta)
    sueldo_promedio = sum(sueldos.values()) / max(len(sueldos), 1) if sueldos else 0
    _tick(t, 'sueldos')

    sucursales_data = []
    total_venta_global = sum(float(r['venta'] or 0) for r in rows)

    for r in rows:
        dep = r['deposito']
        vta = float(r['venta'] or 0)
        costo = float(r['costo'] or 0)
        pares = float(r['pares'] or 0)
        tix = int(r['tickets'] or 0)
        vendedores = int(r['vendedores'] or 0)
        margen = vta - costo
        pct_margen = margen / vta if vta > 0 else 0
        vta_mensual = vta / meses_periodo
        ticket_prom = vta / tix if tix > 0 else 0
        pares_ticket = pares / tix if tix > 0 else 0
        participacion = vta / total_venta_global if total_venta_global > 0 else 0

        sucursales_data.append(dict(
            deposito=dep,
            nombre=SUCURSALES.get(dep, 'Dep %s' % dep),
            venta=vta,
            venta_mensual=vta_mensual,
            costo=costo,
            margen=margen,
            pct_margen=pct_margen,
            pares=pares,
            tickets=tix,
            ticket_prom=ticket_prom,
            pares_ticket=pares_ticket,
            vendedores=vendedores,
            participacion=participacion,
        ))
    _tick(t, 'procesamiento')

    # Chart data
    chart_json = json.dumps([{
        'name': s['nombre'],
        'venta': round(s['venta_mensual']),
        'margen': round(s['pct_margen'] * 100, 1),
        'tickets': s['tickets'],
    } for s in sucursales_data], ensure_ascii=False)

    return dict(
        sucursales=sucursales_data,
        desde=desde,
        hasta=hasta,
        chart_json=chart_json,
        timing=t['_steps'],
        es_admin=_es_admin(),
        puede_ver=_puede_ver,
        roles=_roles_usuario(),
    )


# ─── ALERTAS VENDEDORES ─────────────────────────────────────────────
def alertas():
    """Vendedores con rendimiento bajo 2+ meses consecutivos.
    Retorna JSON para integrar con WhatsApp task_manager."""
    _requiere_acceso()

    hoy = request.now.date()
    hace_3m = hoy - datetime.timedelta(days=90)
    desde = hace_3m.strftime('%Y-%m-%d')
    hasta = hoy.strftime('%Y-%m-%d')

    viajantes = _query_viajantes()
    sueldos = _query_sueldos(desde, hasta)
    mensual = _query_ventas_mensual(desde, hasta)

    # Agrupar por vendedor
    por_vendedor = defaultdict(list)
    for r in mensual:
        por_vendedor[r['viajante']].append(r)

    alertas_list = []
    for cod, meses in por_vendedor.items():
        if cod == 0 or cod not in sueldos:
            continue
        sueldo = sueldos[cod]
        if sueldo == 0:
            continue

        meses_bajo = 0
        for m in sorted(meses, key=lambda x: (x['anio'], x['mes'])):
            vta = float(m['valor'] or 0)
            costo = float(m['costo'] or 0)
            pct_margen = (vta - costo) / vta if vta > 0 else 0
            prod = vta / sueldo if sueldo > 0 else 0

            if prod < 2.0 or pct_margen < 0.35:
                meses_bajo += 1
            else:
                meses_bajo = 0

        if meses_bajo >= 2:
            nombre = viajantes.get(cod, 'Viajante %s' % cod)
            alertas_list.append(dict(
                codigo=cod,
                nombre=nombre,
                meses_bajo=meses_bajo,
                ultimo_margen=round(pct_margen * 100, 1),
                ultima_prod=round(prod, 1),
            ))

    alertas_list.sort(key=lambda x: x['meses_bajo'], reverse=True)
    return response.json(dict(alertas=alertas_list, total=len(alertas_list)))


# ─── MODELO FREELANCE ("UBER DEL CALZADO") ───────────────────────────
# Vendedores Central que NO son convertibles a freelance (depositeros/logística)
# Son costo de infraestructura, no de venta atribuible. Llenar con códigos reales.
DEPOSITEROS_CENTRAL = []  # ej: [12, 47] — códigos viajante de los 2 depositeros

# Fee H4 objetivo: 8% (equilibrio entre ahorro para H4 y retribución para el vendedor)
FEE_OBJETIVO = FEE_FREELANCE   # mismo que el global (0.08)

# Mínimo de venta mensual para ser candidato a freelance (filtro de ruido)
VTA_MINIMA_FREELANCE = 500000


def _query_ventas_por_viajante_deposito(desde, hasta):
    """Ventas totales por viajante+deposito. Permite asignar deposito_principal."""
    sql = """
        SELECT
            viajante,
            deposito,
            SUM(total_item * cantidad)   AS venta_total,
            SUM(precio_costo * cantidad) AS costo_total,
            COUNT(DISTINCT(CASE WHEN codigo=1 THEN numero END))
            - COUNT(DISTINCT(CASE WHEN codigo=3 THEN numero END)) AS tickets
        FROM ventas1_vendedor
        WHERE fecha >= '%s' AND fecha <= '%s'
        GROUP BY viajante, deposito
    """ % (desde, hasta)
    return _sql_mssql(db_omicronvt, sql)


def freelance_modelo():
    """Modelo de conversión freelance ('Uber del calzado') por local y vendedor."""
    _requiere_acceso()
    t = _timer()

    hoy = request.now.date()
    hace_6m = hoy - datetime.timedelta(days=180)
    d_desde = _parse_date(request.vars.get('desde'), hace_6m)
    d_hasta = _parse_date(request.vars.get('hasta'), hoy)
    if d_desde > d_hasta:
        d_desde, d_hasta = d_hasta, d_desde
    desde = d_desde.strftime('%Y-%m-%d')
    hasta  = d_hasta.strftime('%Y-%m-%d')
    meses_periodo = max(1, (d_hasta.year - d_desde.year) * 12 + d_hasta.month - d_desde.month + 1)

    viajantes = _query_viajantes()
    _tick(t, 'viajantes')

    sueldos = _query_sueldos(desde, hasta)
    _tick(t, 'sueldos')

    ventas_raw = _query_ventas_por_viajante_deposito(desde, hasta)
    _tick(t, 'ventas_deposito')

    # Agrupar por viajante: sumar ventas y asignar deposito_principal (el de mayor venta)
    from collections import defaultdict
    por_viajante = defaultdict(lambda: {'venta': 0, 'costo': 0, 'tickets': 0, 'dep_max': 0, 'vta_dep_max': 0})
    for r in ventas_raw:
        cod = r['viajante']
        if not cod:
            continue
        vta = float(r['venta_total'] or 0)
        costo = float(r['costo_total'] or 0)
        tix = int(r['tickets'] or 0)
        dep = r['deposito']
        d = por_viajante[cod]
        d['venta'] += vta
        d['costo'] += costo
        d['tickets'] += tix
        if vta > d['vta_dep_max']:
            d['vta_dep_max'] = vta
            d['dep_max'] = dep

    vendedores = []
    for cod, d in por_viajante.items():
        vta_total = d['venta']
        if vta_total < VTA_MINIMA_FREELANCE * meses_periodo:
            continue
        nombre = viajantes.get(cod, 'Viajante %s' % cod)
        dep = d['dep_max']
        sueldo = sueldos.get(cod, 0)
        costo_total = d['costo']
        tickets = d['tickets']
        margen = vta_total - costo_total
        pct_margen = margen / vta_total if vta_total > 0 else 0
        vta_mensual = vta_total / meses_periodo
        productividad = vta_mensual / sueldo if sueldo > 0 else None

        # Costos laborales
        costo_blanqueado = sueldo * FACTOR_BLANQUEADO if sueldo > 0 else 0
        costo_real       = sueldo * FACTOR_REAL_CONTABLE if sueldo > 0 else 0
        costo_freelance  = vta_mensual * FEE_OBJETIVO

        # Fee de indiferencia del vendedor (a partir del cual no pierde)
        # sueldo_neto ≈ sueldo * 0.83 (retenciones ≈ 17%)
        fee_indif_v = (sueldo * 0.83) / vta_mensual if vta_mensual > 0 and sueldo > 0 else None
        # Fee de equilibrio H4 (igual a costo_real actual)
        fee_h4_eq    = costo_real / vta_mensual if vta_mensual > 0 and sueldo > 0 else None

        # ¿Es candidato a freelance?
        # Central: depositeros excluidos. Todos los demás: sí.
        es_depositero = (dep == 0 and cod in DEPOSITEROS_CENTRAL)
        convertible = not es_depositero

        # Diagnóstico
        if not sueldo:
            diagnostico = 'sin_sueldo'  # ya informal / monotributista / part-time
        elif fee_indif_v and fee_indif_v < FEE_OBJETIVO:
            diagnostico = 'favorable'   # vendedor gana más, H4 ahorra
        elif fee_indif_v and fee_indif_v <= FEE_OBJETIVO * 1.25:
            diagnostico = 'neutro'      # requiere negociación
        else:
            diagnostico = 'dificil'     # vendedor pierde demasiado al fee objetivo

        ahorro_h4 = costo_blanqueado - costo_freelance
        ahorro_vs_real = costo_real - costo_freelance

        vendedores.append(dict(
            codigo=cod,
            nombre=nombre,
            deposito=dep,
            deposito_nombre=DEPOSITOS.get(dep, 'Dep %s' % dep),
            sueldo=sueldo,
            vta_total=vta_total,
            vta_mensual=vta_mensual,
            costo=costo_total,
            margen=margen,
            pct_margen=pct_margen,
            tickets=tickets,
            productividad=productividad,
            costo_blanqueado=costo_blanqueado,
            costo_real=costo_real,
            costo_freelance=costo_freelance,
            ahorro_h4=ahorro_h4,
            ahorro_vs_real=ahorro_vs_real,
            fee_indif=fee_indif_v,
            fee_h4_eq=fee_h4_eq,
            convertible=convertible,
            es_depositero=es_depositero,
            diagnostico=diagnostico,
        ))

    # Ordenar: por deposito luego por vta_mensual desc
    vendedores.sort(key=lambda x: (x['deposito'], -x['vta_mensual']))
    _tick(t, 'procesamiento')

    # Agrupar por depósito para resumen
    resumen_deposito = {}
    for v in vendedores:
        dep = v['deposito']
        if dep not in resumen_deposito:
            resumen_deposito[dep] = dict(
                deposito=dep,
                nombre=DEPOSITOS.get(dep, 'Dep %s' % dep),
                vendedores=0, convertibles=0,
                vta_mensual=0, costo_blanqueado=0, costo_real=0, costo_freelance=0,
                ahorro_h4=0, ahorro_vs_real=0,
                sin_sueldo=0,
            )
        rd = resumen_deposito[dep]
        rd['vendedores'] += 1
        if v['convertible']:
            rd['convertibles'] += 1
        rd['vta_mensual'] += v['vta_mensual']
        rd['costo_blanqueado'] += v['costo_blanqueado']
        rd['costo_real'] += v['costo_real']
        rd['costo_freelance'] += v['costo_freelance']
        rd['ahorro_h4'] += v['ahorro_h4']
        rd['ahorro_vs_real'] += v['ahorro_vs_real']
        if v['diagnostico'] == 'sin_sueldo':
            rd['sin_sueldo'] += 1

    depositos_resumen = sorted(resumen_deposito.values(), key=lambda x: -x['vta_mensual'])

    # KPIs globales solo sobre convertibles
    convertibles = [v for v in vendedores if v['convertible']]
    total_ahorro_h4    = sum(v['ahorro_h4'] for v in convertibles)
    total_ahorro_real  = sum(v['ahorro_vs_real'] for v in convertibles)
    total_costo_free   = sum(v['costo_freelance'] for v in convertibles)
    total_vta_mensual  = sum(v['vta_mensual'] for v in convertibles)
    n_favorable = len([v for v in convertibles if v['diagnostico'] == 'favorable'])
    n_neutro    = len([v for v in convertibles if v['diagnostico'] == 'neutro'])
    n_dificil   = len([v for v in convertibles if v['diagnostico'] == 'dificil'])
    n_sin_sueldo= len([v for v in convertibles if v['diagnostico'] == 'sin_sueldo'])

    return dict(
        vendedores=vendedores,
        depositos_resumen=depositos_resumen,
        desde=desde,
        hasta=hasta,
        meses_periodo=meses_periodo,
        fee_objetivo=FEE_OBJETIVO,
        factor_blanqueado=FACTOR_BLANQUEADO,
        factor_real=FACTOR_REAL_CONTABLE,
        total_convertibles=len(convertibles),
        total_depositeros=len([v for v in vendedores if v['es_depositero']]),
        total_ahorro_h4=total_ahorro_h4,
        total_ahorro_real=total_ahorro_real,
        total_costo_free=total_costo_free,
        total_vta_mensual=total_vta_mensual,
        n_favorable=n_favorable,
        n_neutro=n_neutro,
        n_dificil=n_dificil,
        n_sin_sueldo=n_sin_sueldo,
        depositos=DEPOSITOS,
        timing=t['_steps'],
        es_admin=_es_admin(),
        puede_ver=_puede_ver,
        roles=_roles_usuario(),
    )


# ─── ADMIN CONFIG INCENTIVOS ────────────────────────────────────────
def config():
    """Pantalla para editar bandas, factores y bonus (solo admin)"""
    if not _es_admin():
        session.flash = 'Solo administradores pueden editar la configuracion'
        redirect(URL('informes_productividad', 'dashboard'))

    return dict(
        bandas=BANDAS_MARGEN,
        factor_estacional=FACTOR_ESTACIONAL,
        bonus_productividad=BONUS_PRODUCTIVIDAD,
        config_desde_db=_config_desde_db,
        es_admin=_es_admin(),
        puede_ver=_puede_ver,
        roles=_roles_usuario(),
    )


# ─── API JSON (para charts) ──────────────────────────────────────────
def api_productividad():
    """JSON con datos de productividad para Highcharts"""
    if not auth.user:
        return response.json({'error': 'No autorizado'})
    hoy = request.now.date()
    hace_6m = hoy - datetime.timedelta(days=180)
    d_desde = _parse_date(request.vars.get('desde'), hace_6m)
    d_hasta = _parse_date(request.vars.get('hasta'), hoy)
    desde = d_desde.strftime('%Y-%m-%d')
    hasta = d_hasta.strftime('%Y-%m-%d')

    # Meses en el periodo
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
    if not auth.user:
        return response.json({'error': 'No autorizado'})
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


# =============================================================================
# VIAJANTE ADMIN — administracion de viajante_config
# Solo accesible por informes_admin
# URL: /calzalindo_informes/informes_productividad/viajante_admin
# =============================================================================

def viajante_admin():
    """
    Vista de administracion de viajante_config en omicronvt.
    Permite listar, editar tipo/observaciones/activo y vincular auth_user_id.
    Solo informes_admin.
    """
    _requiere_acceso()

    mensaje = None
    error = None

    # ----------------------------------------------------------------
    # POST: guardar cambios de una fila
    # ----------------------------------------------------------------
    if request.vars.get('accion') == 'guardar':
        try:
            cod = int(request.vars.get('viajante_codigo', 0))
            tipo = request.vars.get('tipo', 'individual')
            obs  = (request.vars.get('observaciones') or '').strip()
            activo_str = request.vars.get('activo', '1')
            activo = 1 if activo_str == '1' else 0
            auth_uid = request.vars.get('auth_user_id') or None
            if auth_uid:
                auth_uid = int(auth_uid)
            dep = request.vars.get('deposito_principal') or None
            if dep:
                dep = int(dep)

            if tipo not in ('individual', 'grupal', 'excluido', 'ml'):
                raise ValueError(u'Tipo invalido: %s' % tipo)

            # Armar SQL de update dinamico
            obs_escaped = obs.replace("'", "''")
            fecha_baja_sql = 'NULL' if activo == 1 else 'GETDATE()'
            auth_uid_sql   = str(auth_uid) if auth_uid else 'NULL'
            dep_sql        = str(dep)       if dep      else 'NULL'

            sql_upd = u"""
                UPDATE omicronvt.dbo.viajante_config
                SET tipo = '%s',
                    observaciones = '%s',
                    activo = %d,
                    auth_user_id = %s,
                    deposito_principal = %s,
                    fecha_baja = %s
                WHERE viajante_codigo = %d
            """ % (tipo, obs_escaped, activo, auth_uid_sql, dep_sql, fecha_baja_sql, cod)

            db_omicronvt.executesql(sql_upd)
            db_omicronvt.commit()
            mensaje = u'Viajante %d actualizado correctamente.' % cod

        except Exception as ex:
            db_omicronvt.rollback()
            error = u'Error al guardar: %s' % str(ex)

    # ----------------------------------------------------------------
    # Filtros GET
    # ----------------------------------------------------------------
    filtro_tipo   = request.vars.get('ftipo', '')
    filtro_activo = request.vars.get('factivo', '')

    where_parts = []
    if filtro_tipo:
        where_parts.append(u"tipo = '%s'" % filtro_tipo)
    if filtro_activo in ('0', '1'):
        where_parts.append(u"activo = %s" % filtro_activo)

    where_sql = (u'WHERE ' + u' AND '.join(where_parts)) if where_parts else u''

    sql_lista = u"""
        SELECT viajante_codigo, nombre, tipo, auth_user_id,
               deposito_principal, activo, observaciones,
               fecha_alta, fecha_baja
        FROM omicronvt.dbo.viajante_config WITH (NOLOCK)
        %s
        ORDER BY tipo, viajante_codigo
    """ % where_sql

    try:
        viajantes = _sql_mssql(db_omicronvt, sql_lista)
    except Exception as ex:
        viajantes = []
        error = u'No se pudo leer viajante_config. Ejecuta crear_viajante_config.sql primero. (%s)' % str(ex)

    # ----------------------------------------------------------------
    # Lista de usuarios del sistema para el dropdown
    # ----------------------------------------------------------------
    try:
        usuarios = db_autenticacion(db_autenticacion.auth_user).select(
            db_autenticacion.auth_user.id,
            db_autenticacion.auth_user.first_name,
            db_autenticacion.auth_user.last_name,
            db_autenticacion.auth_user.email,
            orderby=db_autenticacion.auth_user.first_name
        )
    except Exception:
        usuarios = []

    # Mapa deposito para mostrar nombre
    dep_nombres = {
        0: u'Central', 1: u'Glam', 2: u'Norte', 4: u'Marroquineria',
        6: u'Cuore', 7: u'Eva Peron', 8: u'Junin', 9: u'Tokyo Express',
        15: u'Junin GO',
    }

    tipos_disponibles = ['individual', 'grupal', 'excluido', 'ml']

    return dict(
        viajantes=viajantes,
        usuarios=usuarios,
        dep_nombres=dep_nombres,
        tipos_disponibles=tipos_disponibles,
        filtro_tipo=filtro_tipo,
        filtro_activo=filtro_activo,
        mensaje=mensaje,
        error=error,
    )
