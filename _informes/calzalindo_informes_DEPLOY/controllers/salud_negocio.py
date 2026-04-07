# -*- coding: utf-8 -*-
"""
SALUD DEL NEGOCIO - Controller
================================
Dashboard KPI, Clientes, Sucursales.
Usa: dbC (msgestionC), db1 (msgestion01art)
"""

import json
import decimal
import datetime

try:
    unicode
except NameError:
    unicode = str

# =============================================================================
# HELPERS
# =============================================================================

def _fix_encoding(val):
    if isinstance(val, unicode):
        try:
            return val.encode('latin-1').decode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            return val
    if isinstance(val, bytes):
        try:
            return val.decode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            return val.decode('latin-1')
    return val

def _fix_row(row):
    return {k: _fix_encoding(v) if isinstance(v, (str, unicode)) else v
            for k, v in row.items()}

def _clean(val):
    if isinstance(val, decimal.Decimal):
        return float(val)
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    if isinstance(val, (str, unicode)):
        return _fix_encoding(val)
    if val is None:
        return 0
    return val

# =============================================================================
# DASHBOARD
# =============================================================================

def dashboard():
    """Dashboard principal: KPIs YTD + trend mensual + alertas."""
    _requiere_acceso()

    anio = datetime.datetime.now().year
    anio_ant = anio - 1

    def _fetch():
        # KPIs YTD current year
        sql_ytd = """
        SELECT SUM(v.total_item) as venta_ytd, SUM(v.precio_costo*v.cantidad) as costo_ytd,
               SUM(v.cantidad) as pares_ytd, COUNT(DISTINCT v.cuenta) as clientes_ytd
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.fecha >= '{anio}-01-01' AND v.fecha < '{anio_sig}-01-01'
          AND v.codigo NOT IN (7,36) AND a.marca NOT IN (1316,1317,1158,436) AND v.cantidad > 0
        """.format(anio=anio, anio_sig=anio + 1)
        kpi_rows = dbC.executesql(sql_ytd, as_dict=True)
        kpis = {k: _clean(v) for k, v in _fix_row(kpi_rows[0]).items()} if kpi_rows else {}

        # KPIs same period last year
        sql_ant = """
        SELECT SUM(v.total_item) as venta_ytd, SUM(v.precio_costo*v.cantidad) as costo_ytd,
               SUM(v.cantidad) as pares_ytd, COUNT(DISTINCT v.cuenta) as clientes_ytd
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.fecha >= '{anio_ant}-01-01' AND v.fecha < '{anio_ant}-{mes:02d}-{dia:02d}'
          AND v.codigo NOT IN (7,36) AND a.marca NOT IN (1316,1317,1158,436) AND v.cantidad > 0
        """.format(anio_ant=anio_ant, mes=datetime.datetime.now().month, dia=datetime.datetime.now().day)
        ant_rows = dbC.executesql(sql_ant, as_dict=True)
        kpis_ant = {k: _clean(v) for k, v in _fix_row(ant_rows[0]).items()} if ant_rows else {}

        # Trend mensual 3 anios
        sql_trend = """
        SELECT YEAR(v.fecha) as anio, MONTH(v.fecha) as mes,
               SUM(v.total_item) as venta, SUM(v.cantidad) as uds,
               COUNT(DISTINCT v.cuenta) as clientes
        FROM msgestionC.dbo.ventas1 v
        WHERE v.fecha >= DATEADD(YEAR, -3, GETDATE()) AND v.codigo NOT IN (7,36) AND v.cantidad > 0
        GROUP BY YEAR(v.fecha), MONTH(v.fecha) ORDER BY YEAR(v.fecha), MONTH(v.fecha)
        """
        trend_rows = dbC.executesql(sql_trend, as_dict=True)
        trend = [{k: _clean(v) for k, v in _fix_row(r).items()} for r in trend_rows]

        # Alertas: locales bajo margen
        sql_alertas = """
        SELECT TOP 5 v.deposito, SUM(v.total_item) as venta,
               CASE WHEN SUM(v.total_item)>0 THEN (SUM(v.total_item)-SUM(v.precio_costo*v.cantidad))*100.0/SUM(v.total_item) ELSE 0 END as margen_pct
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.fecha >= DATEADD(MONTH, -3, GETDATE()) AND v.codigo NOT IN (7,36)
          AND a.marca NOT IN (1316,1317,1158,436) AND v.cantidad > 0
        GROUP BY v.deposito
        HAVING CASE WHEN SUM(v.total_item)>0 THEN (SUM(v.total_item)-SUM(v.precio_costo*v.cantidad))*100.0/SUM(v.total_item) ELSE 0 END < 35
        ORDER BY margen_pct ASC
        """
        try:
            alerta_rows = dbC.executesql(sql_alertas, as_dict=True)
            alertas = [{k: _clean(v) for k, v in _fix_row(r).items()} for r in alerta_rows]
        except Exception:
            alertas = []

        return kpis, kpis_ant, trend, alertas

    kpis, kpis_ant, trend, alertas = cache.ram('salud_dashboard_v2', _fetch, 600)

    # Calculate YoY deltas
    venta_ytd = kpis.get('venta_ytd', 0) or 0
    venta_ant = kpis_ant.get('venta_ytd', 0) or 1
    margen_ytd = ((venta_ytd - (kpis.get('costo_ytd', 0) or 0)) * 100.0 / venta_ytd) if venta_ytd > 0 else 0
    costo_ant = kpis_ant.get('costo_ytd', 0) or 0
    margen_ant = ((venta_ant - costo_ant) * 100.0 / venta_ant) if venta_ant > 0 else 0
    pares_ytd = kpis.get('pares_ytd', 0) or 0
    clientes_ytd = kpis.get('clientes_ytd', 0) or 0
    ticket_prom = venta_ytd / clientes_ytd if clientes_ytd > 0 else 0

    delta_venta = ((venta_ytd - venta_ant) * 100.0 / venta_ant) if venta_ant > 0 else 0
    delta_margen = margen_ytd - margen_ant
    pares_ant = kpis_ant.get('pares_ytd', 0) or 1
    delta_pares = ((pares_ytd - pares_ant) * 100.0 / pares_ant) if pares_ant > 0 else 0

    return dict(
        venta_ytd=venta_ytd,
        margen_ytd=round(margen_ytd, 1),
        clientes_ytd=clientes_ytd,
        ticket_prom=round(ticket_prom, 0),
        delta_venta=round(delta_venta, 1),
        delta_margen=round(delta_margen, 1),
        delta_pares=round(delta_pares, 1),
        trend_json=json.dumps(trend),
        alertas_json=json.dumps(alertas),
        anio=anio,
    )

# =============================================================================
# CLIENTES
# =============================================================================

def clientes():
    """Analisis de clientes: trend mensual + por sucursal."""
    _requiere_acceso()

    def _fetch():
        # Clientes unicos mensuales 3 anios
        sql_trend = """
        SELECT YEAR(v.fecha) as anio, MONTH(v.fecha) as mes, COUNT(DISTINCT v.cuenta) as clientes
        FROM msgestionC.dbo.ventas1 v
        WHERE v.fecha >= DATEADD(YEAR, -3, GETDATE()) AND v.codigo NOT IN (7,36) AND v.cantidad > 0
        GROUP BY YEAR(v.fecha), MONTH(v.fecha)
        ORDER BY YEAR(v.fecha), MONTH(v.fecha)
        """
        trend_rows = dbC.executesql(sql_trend, as_dict=True)
        trend = [{k: _clean(v) for k, v in _fix_row(r).items()} for r in trend_rows]

        # Clientes por deposito (local) 12m
        sql_suc = """
        SELECT v.deposito, COUNT(DISTINCT v.cuenta) as clientes,
               SUM(v.total_item) as venta
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.fecha >= DATEADD(MONTH, -12, GETDATE()) AND v.codigo NOT IN (7,36)
          AND a.marca NOT IN (1316,1317,1158,436) AND v.cantidad > 0
        GROUP BY v.deposito
        ORDER BY SUM(v.total_item) DESC
        """
        suc_rows = dbC.executesql(sql_suc, as_dict=True)
        por_suc = []
        for r in suc_rows:
            d = {k: _clean(v) for k, v in _fix_row(r).items()}
            dep = d.get('deposito', 0)
            d['nombre_local'] = NOMBRE_DEPOSITO.get(int(dep) if dep is not None else 0, 'Dep ' + str(dep))
            d['sucursal'] = d['nombre_local']  # backward compat con vista
            por_suc.append(d)

        # Retencion: clientes del mes anterior que tambien compraron mes actual
        sql_ret = """
        SELECT COUNT(DISTINCT v1.cuenta) as retenidos
        FROM msgestionC.dbo.ventas1 v1
        WHERE v1.fecha >= DATEADD(MONTH, -1, CAST(CAST(YEAR(GETDATE()) AS VARCHAR)+'-'+CAST(MONTH(GETDATE()) AS VARCHAR)+'-01' AS DATE))
          AND v1.fecha < CAST(CAST(YEAR(GETDATE()) AS VARCHAR)+'-'+CAST(MONTH(GETDATE()) AS VARCHAR)+'-01' AS DATE)
          AND v1.codigo NOT IN (7,36) AND v1.cantidad > 0
          AND v1.cuenta IN (
              SELECT DISTINCT v2.cuenta FROM msgestionC.dbo.ventas1 v2
              WHERE v2.fecha >= CAST(CAST(YEAR(GETDATE()) AS VARCHAR)+'-'+CAST(MONTH(GETDATE()) AS VARCHAR)+'-01' AS DATE)
                AND v2.codigo NOT IN (7,36) AND v2.cantidad > 0
          )
        """
        sql_tot_ant = """
        SELECT COUNT(DISTINCT v.cuenta) as total_ant
        FROM msgestionC.dbo.ventas1 v
        WHERE v.fecha >= DATEADD(MONTH, -1, CAST(CAST(YEAR(GETDATE()) AS VARCHAR)+'-'+CAST(MONTH(GETDATE()) AS VARCHAR)+'-01' AS DATE))
          AND v.fecha < CAST(CAST(YEAR(GETDATE()) AS VARCHAR)+'-'+CAST(MONTH(GETDATE()) AS VARCHAR)+'-01' AS DATE)
          AND v.codigo NOT IN (7,36) AND v.cantidad > 0
        """
        try:
            ret_rows = dbC.executesql(sql_ret, as_dict=True)
            tot_rows = dbC.executesql(sql_tot_ant, as_dict=True)
            retenidos = _clean(ret_rows[0].get('retenidos', 0)) if ret_rows else 0
            total_ant = _clean(tot_rows[0].get('total_ant', 0)) if tot_rows else 1
            retencion_pct = round(retenidos * 100.0 / max(total_ant, 1), 1)
        except Exception:
            retencion_pct = 0

        return trend, por_suc, retencion_pct

    trend, por_suc, retencion_pct = cache.ram('salud_clientes_v2', _fetch, 3600)

    # Porcentaje de venta por sucursal
    total_venta = sum(r.get('venta', 0) for r in por_suc)
    for r in por_suc:
        r['pct_total'] = round(r.get('venta', 0) * 100.0 / max(total_venta, 1), 1)

    return dict(
        trend_json=json.dumps(trend),
        por_suc_json=json.dumps(por_suc),
        retencion_pct=retencion_pct,
    )

# =============================================================================
# SUCURSALES
# =============================================================================

NOMBRE_DEPOSITO = {
    0: 'Central VT', 1: 'Glam/ML', 2: 'Norte', 4: 'Marroquineria',
    5: 'Externo', 6: 'Cuore/Chovet', 7: 'Eva Peron', 8: 'Junin',
    9: 'Tokyo Express', 11: 'Zapateria VT', 15: 'Junin GO (cerrado)',
}

def sucursales():
    """Rentabilidad por sucursal (deposito)."""
    _requiere_acceso()

    def _fetch():
        sql = """
        SELECT v.deposito, SUM(v.cantidad) as uds,
               SUM(v.total_item) as venta, SUM(v.precio_costo*v.cantidad) as costo,
               CASE WHEN SUM(v.total_item)>0 THEN (SUM(v.total_item)-SUM(v.precio_costo*v.cantidad))*100.0/SUM(v.total_item) ELSE 0 END as margen_pct,
               COUNT(DISTINCT v.cuenta) as clientes
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.fecha >= DATEADD(MONTH, -12, GETDATE()) AND v.codigo NOT IN (7,36)
          AND a.marca NOT IN (1316,1317,1158,436) AND v.cantidad > 0
        GROUP BY v.deposito ORDER BY SUM(v.total_item) DESC
        """
        rows = dbC.executesql(sql, as_dict=True)
        result = []
        for r in rows:
            r = _fix_row(r)
            d = {k: _clean(v) for k, v in r.items()}
            dep = d.get('deposito', 0)
            d['nombre_local'] = NOMBRE_DEPOSITO.get(int(dep) if dep is not None else 0, 'Dep ' + str(dep))
            m = d.get('margen_pct', 0)
            d['margen_bruto'] = round(d.get('venta', 0) - d.get('costo', 0), 0)
            if m >= 45:
                d['semaforo'] = 'verde'
            elif m >= 35:
                d['semaforo'] = 'naranja'
            else:
                d['semaforo'] = 'rojo'
            result.append(d)
        return result

    data = cache.ram('salud_sucursales_v2', _fetch, 3600)

    margen_prom = sum(r.get('margen_pct', 0) for r in data) / max(len(data), 1)
    target = 42.0
    bajo_target = sum(1 for r in data if r.get('margen_pct', 0) < 35)

    return dict(
        data_json=json.dumps(data),
        margen_promedio=round(margen_prom, 1),
        target=target,
        bajo_target=bajo_target,
    )
