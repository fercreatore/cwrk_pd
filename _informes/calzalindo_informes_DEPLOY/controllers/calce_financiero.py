# -*- coding: utf-8 -*-
"""
CALCE FINANCIERO POR INDUSTRIA - Controller
============================================
Integra: Notas de Pedido (compromisos) + Recupero (ventas) + Compras/Stock
para modelar el calce de pagos contra ventas por industria.

Tabla principal: v_calce_industria (vista sugerida) o queries directos.
Usa: db_omicronvt (MSSQL omicronvt), db1 (MSSQL msgestion01)

Copiar en: applications/calzalindo_informes/controllers/calce_financiero.py
(o en calzalindo_objetivos_v2/controllers/ si se integra al sistema existente)
"""

import json
import decimal
import datetime
import traceback

# =============================================================================
# HELPERS
# =============================================================================

def _fix_encoding(val):
    """
    Corrige strings con encoding roto (mojibake) de SQL Server.
    Cuando pyodbc lee UTF-8 almacenado en varchar, interpreta los bytes
    como latin-1, produciendo unicode roto (ej: u'CosmÃ©tica' en vez de u'Cosmética').
    Fix: re-encode a latin-1 (recupera bytes originales) y decode como UTF-8.
    """
    if isinstance(val, unicode):
        try:
            return val.encode('latin-1').decode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            return val
    if isinstance(val, str):
        try:
            return val.decode('utf-8')
        except (UnicodeDecodeError, UnicodeEncodeError):
            return val.decode('latin-1')
    return val

def _fix_row(row):
    """Aplica _fix_encoding a todos los valores string de un dict."""
    return {k: _fix_encoding(v) if isinstance(v, (str, unicode)) else v
            for k, v in row.items()}

def _clean(val):
    """Limpia valores para JSON: Decimal→float, date→str, fix encoding."""
    if isinstance(val, decimal.Decimal):
        return float(val)
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    if isinstance(val, (str, unicode)):
        return _fix_encoding(val)
    if val is None:
        return 0
    return val

def _url_safe(val):
    """Codifica unicode a UTF-8 para uso en URL(vars=...). NO usar para display."""
    if isinstance(val, unicode):
        return val.encode('utf-8')
    return val or ''

def _html(val):
    """
    Convierte string a HTML entities para chars no-ASCII.
    Esto es inmune a cualquier problema de encoding en web2py/Python 2.7/Windows
    porque el output es 100% ASCII.
    Ej: u'Cosmética' -> XML('Cosm&#233;tica')
    """
    val = _fix_encoding(val) if isinstance(val, (str, unicode)) else val
    if isinstance(val, unicode):
        parts = []
        for c in val:
            if ord(c) > 127:
                parts.append('&#%d;' % ord(c))
            else:
                parts.append(c)
        return XML(''.join(parts))
    if isinstance(val, str):
        try:
            return _html(val.decode('utf-8'))
        except:
            return _html(val.decode('latin-1'))
    return val or ''

def _fmt_moneda(val):
    """Formatea número como moneda AR."""
    try:
        return "$ {:,.0f}".format(float(val or 0)).replace(",", ".")
    except:
        return "$ 0"

def _where_industria(industria='', proveedor='', temporada=''):
    """WHERE dinámico para filtros comunes."""
    parts = ["1=1"]
    if industria:
        parts.append("industria = '{}'".format(industria.replace("'", "''")))
    if proveedor:
        parts.append("proveedor_nombre LIKE '%{}%'".format(proveedor.replace("'", "''")))
    if temporada:
        parts.append("temporada_tipo = '{}'".format(temporada.replace("'", "''")))
    return " AND ".join(parts)


# =============================================================================
# DASHBOARD PRINCIPAL - CALCE FINANCIERO
# =============================================================================

def diagnostico():
    """
    Endpoint de diagnostico: prueba conexiones DB y existencia de tablas.
    Acceder en: /calzalindo_informes/calce_financiero/diagnostico
    """
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    checks = []

    # Test 1: db_omicronvt
    try:
        r = db_omicronvt.executesql("SELECT 1 AS ok", as_dict=True)
        checks.append(('db_omicronvt conexion', 'OK', ''))
    except Exception as e:
        checks.append(('db_omicronvt conexion', 'FALLO', str(e)))

    # Test 2: pedidos_cumplimiento_cache
    try:
        r = db_omicronvt.executesql("SELECT TOP 1 * FROM pedidos_cumplimiento_cache", as_dict=True)
        cols = list(r[0].keys()) if r else ['(tabla vacia)']
        checks.append(('pedidos_cumplimiento_cache', 'OK - %d columnas' % len(cols), ', '.join(sorted(cols)[:15])))
    except Exception as e:
        checks.append(('pedidos_cumplimiento_cache', 'FALLO', str(e)))

    # Test 3: t_recupero_inversion
    try:
        r = db_omicronvt.executesql("SELECT TOP 1 * FROM t_recupero_inversion", as_dict=True)
        checks.append(('t_recupero_inversion', 'OK', '%d filas ejemplo' % len(r)))
    except Exception as e:
        checks.append(('t_recupero_inversion', 'FALLO', str(e)))

    # Test 4: t_presupuesto_industria
    try:
        r = db_omicronvt.executesql("SELECT TOP 1 * FROM t_presupuesto_industria", as_dict=True)
        checks.append(('t_presupuesto_industria', 'OK', ''))
    except Exception as e:
        checks.append(('t_presupuesto_industria', 'NO EXISTE (normal si no se corrio el SQL)', str(e)[:100]))

    # Test 5: columnas nuevas en cache
    try:
        r = db_omicronvt.executesql("SELECT TOP 1 rubro_desc, grupo_desc, linea_desc FROM pedidos_cumplimiento_cache", as_dict=True)
        checks.append(('columnas rubro/grupo/linea en cache', 'OK', ''))
    except Exception as e:
        checks.append(('columnas rubro/grupo/linea en cache', 'NO EXISTEN (normal si no se corrio el SQL)', str(e)[:100]))

    # Test 6: columna marca
    try:
        r = db_omicronvt.executesql("SELECT TOP 1 marca FROM pedidos_cumplimiento_cache", as_dict=True)
        checks.append(('columna marca en cache', 'OK', ''))
    except Exception as e:
        checks.append(('columna marca en cache', 'FALLO', str(e)[:100]))

    # Test 7: auth
    try:
        checks.append(('auth.user', 'OK' if auth.user else 'NO LOGUEADO', str(auth.user.id) if auth.user else ''))
    except Exception as e:
        checks.append(('auth.user', 'FALLO', str(e)))

    html_out = '<html><head><title>Diagnostico Calce Financiero</title></head><body>'
    html_out += '<h2>Diagnostico - Calce Financiero</h2>'
    html_out += '<table border="1" cellpadding="5" style="border-collapse:collapse;">'
    html_out += '<tr><th>Check</th><th>Estado</th><th>Detalle</th></tr>'
    for name, status, detail in checks:
        color = '#d4edda' if 'OK' in status else '#f8d7da' if 'FALLO' in status else '#fff3cd'
        html_out += '<tr style="background:%s"><td>%s</td><td>%s</td><td style="font-size:11px;">%s</td></tr>' % (color, name, status, detail)
    html_out += '</table>'
    html_out += '<br><a href="%s">Volver al Dashboard</a>' % URL('calce_financiero', 'dashboard')
    html_out += '</body></html>'
    return html_out


def dashboard():
    """
    Dashboard integrado de calce financiero por industria.
    Combina: Presupuesto → Comprometido → Recupero → Posición de caja.
    """
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    _requiere_acceso()

    # Leer filtros (fix encoding por si vienen con acentos desde la URL)
    industria = _fix_encoding(request.vars.industria) if request.vars.industria else ''
    temporada = _fix_encoding(request.vars.temporada) if request.vars.temporada else ''
    proveedor = _fix_encoding(request.vars.proveedor) if request.vars.proveedor else ''
    rubro     = _fix_encoding(request.vars.rubro)     if request.vars.rubro     else ''
    subrubro  = _fix_encoding(request.vars.subrubro)  if request.vars.subrubro  else ''
    grupo     = _fix_encoding(request.vars.grupo)     if request.vars.grupo     else ''
    linea     = _fix_encoding(request.vars.linea)     if request.vars.linea     else ''
    marca     = _fix_encoding(request.vars.marca)     if request.vars.marca     else ''

    where_recupero = _where_industria(industria, proveedor, temporada)

    # --- Filtros para pedidos_cumplimiento_cache ---
    # Solo 2do semestre 2025 en adelante (pedidos anteriores son historicos)
    where_pedidos_parts = ["fecha_pedido >= '2025-07-01'"]
    if industria:
        where_pedidos_parts.append("industria = '{}'".format(industria.replace("'", "''")))
    if proveedor:
        where_pedidos_parts.append("proveedor LIKE '%{}%'".format(proveedor.replace("'", "''")))
    if rubro:
        where_pedidos_parts.append("rubro_desc = '{}'".format(rubro.replace("'", "''")))
    if subrubro:
        where_pedidos_parts.append("subrubro_desc = '{}'".format(subrubro.replace("'", "''")))
    if grupo:
        where_pedidos_parts.append("grupo_desc = '{}'".format(grupo.replace("'", "''")))
    if linea:
        where_pedidos_parts.append("linea_desc = '{}'".format(linea.replace("'", "''")))
    if marca:
        where_pedidos_parts.append("marca = '{}'".format(marca.replace("'", "''")))
    where_pedidos = " AND ".join(where_pedidos_parts)

    # =========================================================================
    # BLOQUE 1: COMPROMISOS (Notas de Pedido por industria)
    # =========================================================================
    sql_compromisos = """
    SELECT
        ISNULL(industria, 'Sin clasificar') AS industria,
        COUNT(DISTINCT CAST(sucursal AS VARCHAR) + '-' + CAST(numero AS VARCHAR)) AS pedidos,
        COUNT(DISTINCT cod_proveedor) AS proveedores,
        SUM(monto_pedido) AS monto_comprometido,
        SUM(CASE WHEN estado_cumplimiento = 'COMPLETO' THEN monto_pedido ELSE 0 END) AS monto_recibido,
        SUM(monto_pendiente) AS monto_pendiente_recibir,
        SUM(cant_pedida) AS unidades_pedidas,
        SUM(cant_recibida) AS unidades_recibidas,
        SUM(cant_pendiente) AS unidades_pendientes,
        CASE WHEN SUM(cant_pedida) = 0 THEN 0
             ELSE ROUND(SUM(cant_recibida) * 100.0 / SUM(cant_pedida), 1)
        END AS pct_cumplimiento,
        SUM(CASE WHEN alerta_vencimiento = 'VENCIDO' THEN monto_pendiente ELSE 0 END) AS monto_vencido
    FROM pedidos_cumplimiento_cache
    WHERE {where}
    GROUP BY industria
    ORDER BY SUM(monto_pedido) DESC
    """.format(where=where_pedidos)

    try:
        compromisos = [_fix_row(r) for r in db_omicronvt.executesql(sql_compromisos, as_dict=True)]
    except Exception as e:
        compromisos = []

    # =========================================================================
    # BLOQUE 2: RECUPERO (Velocidad de venta y calce de pagos por industria)
    # =========================================================================
    sql_recupero = """
    SELECT
        industria,
        COUNT(*) AS registros,
        SUM(total_costo_compra) AS inversion_total,
        AVG(CAST(dias_50 AS FLOAT)) AS dias_promedio_50,
        AVG(CAST(dias_75 AS FLOAT)) AS dias_promedio_75,
        AVG(plazo_pago_real_prom) AS plazo_pago_promedio,
        AVG(pct_vendido) AS pct_vendido_promedio,
        AVG(pct_vendido_al_pago) AS pct_vendido_al_pago_prom,
        AVG(brecha_pago_vs_rec50) AS brecha_promedio,
        SUM(CASE WHEN estado = 'PRESION' THEN 1 ELSE 0 END) AS proveedores_presion,
        SUM(CASE WHEN estado = 'OK' THEN 1 ELSE 0 END) AS proveedores_ok
    FROM t_recupero_inversion
    WHERE {where}
    GROUP BY industria
    ORDER BY AVG(CAST(dias_50 AS FLOAT))
    """.format(where=where_recupero)

    try:
        recupero = [_fix_row(r) for r in db_omicronvt.executesql(sql_recupero, as_dict=True)]
    except Exception as e:
        recupero = []

    # =========================================================================
    # BLOQUE 3: KPIs GLOBALES
    # =========================================================================
    sql_kpi_compromisos = """
    SELECT
        ISNULL(SUM(monto_pedido), 0) AS total_comprometido,
        ISNULL(SUM(monto_pendiente), 0) AS total_pendiente_recibir,
        ISNULL(SUM(CASE WHEN alerta_vencimiento = 'VENCIDO' THEN monto_pendiente ELSE 0 END), 0) AS total_vencido,
        COUNT(DISTINCT ISNULL(industria, 'Sin clasificar')) AS industrias_activas
    FROM pedidos_cumplimiento_cache
    WHERE {where}
    """.format(where=where_pedidos)

    try:
        kpi_comp = [_fix_row(r) for r in db_omicronvt.executesql(sql_kpi_compromisos, as_dict=True)]
        kpi_comp = kpi_comp[0] if kpi_comp else {}
    except Exception as e:
        kpi_comp = {}

    sql_kpi_recupero = """
    SELECT
        ISNULL(SUM(total_costo_compra), 0) AS inversion_total,
        ISNULL(AVG(pct_vendido), 0) AS pct_vendido_global,
        ISNULL(AVG(pct_vendido_al_pago), 0) AS pct_vendido_al_pago_global,
        ISNULL(AVG(CAST(dias_50 AS FLOAT)), 0) AS dias_50_global,
        ISNULL(AVG(brecha_pago_vs_rec50), 0) AS brecha_global,
        SUM(CASE WHEN estado = 'PRESION' THEN 1 ELSE 0 END) AS total_presion
    FROM t_recupero_inversion
    WHERE {where}
    """.format(where=where_recupero)

    try:
        kpi_rec = [_fix_row(r) for r in db_omicronvt.executesql(sql_kpi_recupero, as_dict=True)]
        kpi_rec = kpi_rec[0] if kpi_rec else {}
    except Exception as e:
        kpi_rec = {}

    # =========================================================================
    # BLOQUE 4: MATRIZ INTEGRADA (industria × compromisos + recupero)
    # =========================================================================
    # Combinar compromisos y recupero por industria en Python
    matriz = {}
    for c in compromisos:
        ind = c['industria'] or 'Sin clasificar'
        matriz[ind] = {
            'industria': ind,
            'comprometido': float(c.get('monto_comprometido') or 0),
            'recibido': float(c.get('monto_recibido') or 0),
            'pendiente_recibir': float(c.get('monto_pendiente_recibir') or 0),
            'vencido': float(c.get('monto_vencido') or 0),
            'pedidos': c.get('pedidos', 0),
            'proveedores': c.get('proveedores', 0),
            'pct_cumplimiento': float(c.get('pct_cumplimiento') or 0),
            'unidades_pedidas': int(c.get('unidades_pedidas') or 0),
            'unidades_recibidas': int(c.get('unidades_recibidas') or 0),
            # Recupero (se llena abajo)
            'inversion': 0,
            'dias_50': 0,
            'dias_75': 0,
            'plazo_pago': 0,
            'pct_vendido': 0,
            'pct_vendido_al_pago': 0,
            'brecha': 0,
            'proveedores_presion': 0,
            # Calculados
            'semaforo': 'SIN DATOS',
        }

    for r in recupero:
        ind = r['industria'] or 'Sin clasificar'
        if ind not in matriz:
            matriz[ind] = {
                'industria': ind,
                'comprometido': 0, 'recibido': 0, 'pendiente_recibir': 0,
                'vencido': 0, 'pedidos': 0, 'proveedores': 0,
                'pct_cumplimiento': 0, 'unidades_pedidas': 0, 'unidades_recibidas': 0,
                'inversion': 0, 'dias_50': 0, 'dias_75': 0, 'plazo_pago': 0,
                'pct_vendido': 0, 'pct_vendido_al_pago': 0, 'brecha': 0,
                'proveedores_presion': 0, 'semaforo': 'SIN DATOS',
            }
        matriz[ind]['inversion'] = float(r.get('inversion_total') or 0)
        matriz[ind]['dias_50'] = round(float(r.get('dias_promedio_50') or 0), 0)
        matriz[ind]['dias_75'] = round(float(r.get('dias_promedio_75') or 0), 0)
        matriz[ind]['plazo_pago'] = round(float(r.get('plazo_pago_promedio') or 0), 0)
        matriz[ind]['pct_vendido'] = round(float(r.get('pct_vendido_promedio') or 0), 1)
        matriz[ind]['pct_vendido_al_pago'] = round(float(r.get('pct_vendido_al_pago_prom') or 0), 1)
        matriz[ind]['brecha'] = round(float(r.get('brecha_promedio') or 0), 0)
        matriz[ind]['proveedores_presion'] = int(r.get('proveedores_presion') or 0)

    # BLOQUE 4b: REMITOS SIN FACTURAR POR INDUSTRIA (deuda en formación)
    # Remitos de compra (cod 7, 36) - deuda en formación
    # CTE para evitar multiplicación por JOIN con detalle
    remitos_industria = {}
    remitos_viejos = []
    if dbC:
        try:
            sql_remitos_ind = """
            ;WITH remitos_ind AS (
                SELECT
                    c2.empresa, c2.codigo, c2.letra, c2.sucursal, c2.numero, c2.orden,
                    c2.monto_general, c2.fecha_comprobante, c2.cuenta_cc,
                    ISNULL(
                        (SELECT TOP 1 ISNULL(ind.industria, 'Sin clasificar')
                         FROM compras1 c1
                         JOIN msgestion01art.dbo.articulo a ON c1.articulo = a.codigo
                         LEFT JOIN omicronvt.dbo.map_subrubro_industria ind ON a.subrubro = ind.subrubro
                         WHERE c1.empresa = c2.empresa AND c1.codigo = c2.codigo
                           AND c1.letra = c2.letra AND c1.sucursal = c2.sucursal
                           AND c1.numero = c2.numero AND c1.orden = c2.orden
                           AND a.marca NOT IN (1316, 1317, 1158, 436)
                        ), 'Sin clasificar') AS industria
                FROM compras2 c2
                WHERE c2.codigo IN (7, 36)
                  AND c2.estado = 'V'
                  AND c2.fecha_comprobante >= '2026-01-01'
            )
            SELECT industria,
                   COUNT(*) as cant_remitos,
                   COUNT(DISTINCT cuenta_cc) as cant_proveedores,
                   SUM(monto_general) as monto_remitos,
                   AVG(DATEDIFF(DAY, fecha_comprobante, GETDATE())) as dias_promedio
            FROM remitos_ind
            GROUP BY industria
            """
            for r in dbC.executesql(sql_remitos_ind, as_dict=True):
                r = _fix_row(r)
                remitos_industria[r['industria']] = {
                    'monto': float(r.get('monto_remitos') or 0),
                    'cant': int(r.get('cant_remitos') or 0),
                    'proveedores': int(r.get('cant_proveedores') or 0),
                    'dias_promedio': int(r.get('dias_promedio') or 0),
                }
        except:
            pass

        # Remitos viejos (pre-2026) sin facturar — para limpieza
        try:
            sql_remitos_viejos = """
            SELECT TOP 20
                RTRIM(c2.denominacion) as proveedor,
                c2.cuenta_cc as prov_id,
                COUNT(*) as cant_remitos,
                SUM(c2.monto_general) as monto_total,
                MIN(c2.fecha_comprobante) as fecha_min,
                MAX(c2.fecha_comprobante) as fecha_max
            FROM compras2 c2
            WHERE c2.codigo IN (7, 36)
              AND c2.estado = 'V'
              AND c2.fecha_comprobante < '2026-01-01'
              AND c2.fecha_comprobante >= '2024-01-01'
            GROUP BY RTRIM(c2.denominacion), c2.cuenta_cc
            ORDER BY SUM(c2.monto_general) DESC
            """
            remitos_viejos = [_fix_row(r) for r in dbC.executesql(sql_remitos_viejos, as_dict=True)]
        except:
            pass

    # Deuda neta por industria (facturas pendientes de pago)
    # Usa t_roi_proveedor como mapping proveedor→industria (ya existe en omicronvt)
    deuda_industria = {}
    if dbC and db_analitica:
        try:
            sql_deuda_ind = """
            ;WITH saldo_prov AS (
                SELECT numero_cuenta,
                       SUM(CASE WHEN operacion = '+'
                           THEN (importe_pesos - importe_can_pesos)
                           ELSE -(importe_pesos - importe_can_pesos) END) as saldo_neto
                FROM moviprov1
                GROUP BY numero_cuenta
                HAVING SUM(CASE WHEN operacion = '+'
                           THEN (importe_pesos - importe_can_pesos)
                           ELSE -(importe_pesos - importe_can_pesos) END) > 100
            )
            SELECT ISNULL(roi.industria, 'Sin clasificar') as industria,
                   SUM(sp.saldo_neto) as deuda_neta,
                   COUNT(*) as proveedores
            FROM saldo_prov sp
            LEFT JOIN omicronvt.dbo.t_roi_proveedor roi ON sp.numero_cuenta = roi.proveedor_id
            GROUP BY ISNULL(roi.industria, 'Sin clasificar')
            """
            for r in dbC.executesql(sql_deuda_ind, as_dict=True):
                r = _fix_row(r)
                deuda_industria[r['industria']] = float(r.get('deuda_neta') or 0)
        except:
            pass

    # Inyectar remitos y deuda en la matriz
    for ind, m in matriz.items():
        rem = remitos_industria.get(ind, {})
        m['remitos_monto'] = rem.get('monto', 0)
        m['remitos_cant'] = rem.get('cant', 0)
        m['remitos_dias_prom'] = rem.get('dias_promedio', 0)
        m['deuda_neta'] = deuda_industria.get(ind, 0)
        # Fondos comprometidos = pedidos + remitos + deuda
        m['fondos_comprometidos'] = m['comprometido'] + m['remitos_monto'] + m['deuda_neta']
        # Fecha estimada de pago: fecha promedio remito + plazo pago industria
        dias_prom_remito = rem.get('dias_promedio', 0)
        plazo = m.get('plazo_pago', 0)
        dias_para_pago = max(0, plazo - dias_prom_remito)
        m['dias_para_pago'] = dias_para_pago

    # Calcular semáforo por industria
    for ind, m in matriz.items():
        pct_pago = m['pct_vendido_al_pago']
        brecha = m['brecha']
        if pct_pago >= 75:
            m['semaforo'] = 'CALZADO'       # Vendés más de lo que pagás → OK
        elif pct_pago >= 50:
            m['semaforo'] = 'AJUSTADO'       # Vendés la mitad al pagar → cuidado
        elif pct_pago > 0:
            m['semaforo'] = 'PRESION'        # Vendés poco al pagar → presión de caja
        elif m['comprometido'] > 0:
            m['semaforo'] = 'DEFICIT'        # Hay compromisos pero no hay recupero
        else:
            m['semaforo'] = 'SIN DATOS'

    # Ordenar: primero los de presión, luego por monto comprometido
    orden_semaforo = {'DEFICIT': 0, 'PRESION': 1, 'AJUSTADO': 2, 'CALZADO': 3, 'SIN DATOS': 4}
    matriz_lista = sorted(matriz.values(), key=lambda x: (orden_semaforo.get(x['semaforo'], 5), -x['comprometido']))

    # =========================================================================
    # BLOQUE 5: TOP PROVEEDORES EN PRESIÓN
    # =========================================================================
    sql_presion = """
    SELECT TOP 15
        proveedor_nombre,
        industria,
        total_costo_compra,
        dias_50,
        plazo_pago_real_prom,
        pct_vendido_al_pago,
        brecha_pago_vs_rec50,
        estado,
        pct_vendido
    FROM t_recupero_inversion
    WHERE estado = 'PRESION' AND {where}
    ORDER BY total_costo_compra DESC
    """.format(where=where_recupero)

    try:
        proveedores_presion = [_fix_row(r) for r in db_omicronvt.executesql(sql_presion, as_dict=True)]
    except Exception as e:
        proveedores_presion = []

    # =========================================================================
    # BLOQUE 6: VENCIMIENTOS PRÓXIMOS (pedidos vencidos o por vencer)
    # =========================================================================
    sql_vencimientos = """
    SELECT
        CASE
            WHEN DATEDIFF(DAY, GETDATE(), fecha_entrega) < 0 THEN 'VENCIDO'
            WHEN DATEDIFF(DAY, GETDATE(), fecha_entrega) <= 7 THEN 'Esta semana'
            WHEN DATEDIFF(DAY, GETDATE(), fecha_entrega) <= 15 THEN 'Proximos 15 dias'
            WHEN DATEDIFF(DAY, GETDATE(), fecha_entrega) <= 30 THEN 'Proximos 30 dias'
            ELSE 'Mas de 30 dias'
        END AS rango,
        COUNT(DISTINCT CAST(sucursal AS VARCHAR) + '-' + CAST(numero AS VARCHAR)) AS pedidos,
        SUM(monto_pendiente) AS monto,
        COUNT(DISTINCT cod_proveedor) AS proveedores
    FROM pedidos_cumplimiento_cache
    WHERE estado_cumplimiento IN ('PENDIENTE', 'PARCIAL') AND {where}
    GROUP BY
        CASE
            WHEN DATEDIFF(DAY, GETDATE(), fecha_entrega) < 0 THEN 'VENCIDO'
            WHEN DATEDIFF(DAY, GETDATE(), fecha_entrega) <= 7 THEN 'Esta semana'
            WHEN DATEDIFF(DAY, GETDATE(), fecha_entrega) <= 15 THEN 'Proximos 15 dias'
            WHEN DATEDIFF(DAY, GETDATE(), fecha_entrega) <= 30 THEN 'Proximos 30 dias'
            ELSE 'Mas de 30 dias'
        END
    ORDER BY MIN(DATEDIFF(DAY, GETDATE(), fecha_entrega))
    """.format(where=where_pedidos)

    try:
        vencimientos = [_fix_row(r) for r in db_omicronvt.executesql(sql_vencimientos, as_dict=True)]
    except Exception as e:
        vencimientos = []

    # =========================================================================
    # BLOQUE 7: PRESUPUESTO POR INDUSTRIA (con ajuste por tendencia)
    # =========================================================================
    presupuesto = []
    try:
        sql_presupuesto = """
        SELECT industria, temporada,
               presupuesto_costo, presupuesto_unidades,
               comprometido_costo, comprometido_unidades,
               disponible_costo, pct_ejecutado,
               ISNULL(factor_tendencia, 1.0) AS factor_tendencia,
               ISNULL(presupuesto_ajustado, presupuesto_costo) AS presupuesto_ajustado,
               ISNULL(disponible_ajustado, disponible_costo) AS disponible_ajustado,
               ISNULL(meses_evaluados, 0) AS meses_evaluados,
               ISNULL(tendencia_desc, '') AS tendencia_desc,
               ISNULL(factor_tendencia_uds, 1.0) AS factor_tendencia_uds,
               ISNULL(presupuesto_uds_ajustado, presupuesto_unidades) AS presupuesto_uds_ajustado,
               ISNULL(var_ticket_prom, 0) AS var_ticket_prom,
               ISNULL(uds_ytd_2026, 0) AS uds_ytd_2026,
               ISNULL(uds_ytd_2025, 0) AS uds_ytd_2025,
               ISNULL(uds_proy_anual_2026, 0) AS uds_proy_anual_2026,
               ISNULL(diagnostico, '') AS diagnostico
        FROM t_presupuesto_industria
        ORDER BY presupuesto_costo DESC
        """
        presupuesto = [_fix_row(r) for r in db_omicronvt.executesql(sql_presupuesto, as_dict=True)]
    except:
        pass  # tabla aun no existe, se ignora

    # =========================================================================
    # BLOQUE 7b: TENDENCIA MENSUAL (para sparkline en dashboard)
    # =========================================================================
    tendencia_mensual = {}
    try:
        sql_tend = """
        SELECT industria, mes,
               facturacion_2024, facturacion_2025, facturacion_2026,
               unidades_2024, unidades_2025, unidades_2026,
               ticket_2024, ticket_2025, ticket_2026,
               ratio_26v25, ratio_uds_26v25, ratio_ticket_26v25,
               idx_estacionalidad, mes_completo_2026
        FROM t_tendencia_facturacion
        WHERE facturacion_2025 > 0 OR unidades_2025 > 0
        ORDER BY industria, mes
        """
        for r in db_omicronvt.executesql(sql_tend, as_dict=True):
            r = _fix_row(r)
            ind = r['industria']
            if ind not in tendencia_mensual:
                tendencia_mensual[ind] = []
            tendencia_mensual[ind].append({
                'mes': int(r['mes']),
                'f2024': float(r.get('facturacion_2024') or 0),
                'f2025': float(r.get('facturacion_2025') or 0),
                'f2026': float(r.get('facturacion_2026') or 0),
                'u2025': int(r.get('unidades_2025') or 0),
                'u2026': int(r.get('unidades_2026') or 0),
                'tk2025': float(r.get('ticket_2025') or 0),
                'tk2026': float(r.get('ticket_2026') or 0),
                'ratio': float(r.get('ratio_26v25') or 0),
                'ratio_uds': float(r.get('ratio_uds_26v25') or 0),
                'ratio_ticket': float(r.get('ratio_ticket_26v25') or 0),
                'idx_est': float(r.get('idx_estacionalidad') or 0),
                'completo': int(r.get('mes_completo_2026') or 0),
            })
    except:
        pass

    # =========================================================================
    # BLOQUES 8-11: MEJORAS CFO (usan db_analitica = replica 112)
    # Si db_analitica no existe o falla, los paneles no se muestran (graceful)
    # =========================================================================
    _db_cfo = db_analitica if db_analitica else None

    # BLOQUE 8: FLUJO DE CAJA SEMANAL PROYECTADO
    flujo_caja = []
    if _db_cfo:
        try:
            sql_flujo = """
            SELECT semana_numero, semana_inicio, semana_fin,
                   pagos_total, cant_ops, cant_proveedores,
                   cobranza_estimada, cobranza_costo,
                   balance_semanal, balance_acumulado
            FROM t_flujo_caja_semanal
            ORDER BY semana_numero
            """
            flujo_caja = [{k: _clean(v) for k, v in r.items()}
                          for r in _db_cfo.executesql(sql_flujo, as_dict=True)]
        except:
            pass

    # BLOQUE 9: ROI POR PROVEEDOR / RANKING DE COMPRA
    # Soporta: rolling 12 meses (default) o por temporada (si roi_periodo seleccionado)
    roi_proveedores = []
    roi_benchmark = []
    roi_periodos_disponibles = []
    roi_periodo_activo = _fix_encoding(request.vars.roi_periodo) if request.vars.roi_periodo else ''

    if _db_cfo:
        # Obtener periodos disponibles
        try:
            sql_periodos = """
            SELECT DISTINCT periodo, COUNT(*) as proveedores
            FROM t_roi_proveedor_temporada
            GROUP BY periodo
            HAVING COUNT(*) >= 5
            ORDER BY periodo DESC
            """
            roi_periodos_disponibles = [{k: _clean(v) for k, v in r.items()}
                                        for r in _db_cfo.executesql(sql_periodos, as_dict=True)]
        except:
            pass

        try:
            sql_roi_where = "1=1"
            if industria:
                sql_roi_where = "industria = '{}'".format(industria.replace("'", "''"))
            if proveedor:
                sql_roi_where += " AND proveedor_nombre LIKE '%{}%'".format(proveedor.replace("'", "''"))

            if roi_periodo_activo:
                # Por temporada
                sql_roi = """
                SELECT TOP 25
                    proveedor_id, proveedor_nombre, industria,
                    margen_bruto_pct, venta_total, costo_total, unidades_vendidas,
                    dias_50, dias_75, rotacion_anual,
                    roi_anualizado, roi_por_peso,
                    plazo_pago, brecha, pct_vendido_al_pago,
                    score_compra, ranking, recomendacion,
                    es_isotipo, cant_temporadas
                FROM t_roi_proveedor_temporada
                WHERE periodo = '{periodo}' AND {where}
                ORDER BY score_compra DESC
                """.format(periodo=roi_periodo_activo.replace("'", "''"), where=sql_roi_where)
            else:
                # Rolling 12 meses (default)
                sql_roi = """
                SELECT TOP 25
                    proveedor_id, proveedor_nombre, industria,
                    margen_bruto_pct, venta_total, costo_total, unidades_vendidas,
                    dias_50, dias_75, rotacion_anual,
                    roi_anualizado, roi_por_peso,
                    plazo_pago, brecha, pct_vendido_al_pago,
                    score_compra, ranking, recomendacion
                FROM t_roi_proveedor
                WHERE {where}
                ORDER BY score_compra DESC
                """.format(where=sql_roi_where)
            roi_proveedores = [_fix_row(r) for r in _db_cfo.executesql(sql_roi, as_dict=True)]
        except:
            pass

        # Benchmark por temporada (medias con isotipos)
        try:
            sql_bench_where = "industria = 'TODAS'"
            if industria:
                sql_bench_where = "industria = '{}'".format(industria.replace("'", "''"))
            sql_benchmark = """
            SELECT periodo, proveedores, proveedores_isotipo,
                   margen_prom, roi_prom, roi_isotipo_prom,
                   dias_50_prom, brecha_prom, score_prom, score_isotipo_prom
            FROM t_roi_temporada_media
            WHERE {where}
            ORDER BY periodo DESC
            """.format(where=sql_bench_where)
            roi_benchmark = [{k: _clean(v) for k, v in r.items()}
                             for r in _db_cfo.executesql(sql_benchmark, as_dict=True)]
        except:
            pass

    # BLOQUE 10: CAPITAL DE TRABAJO MENSUAL
    capital_trabajo = {}
    if _db_cfo:
        try:
            sql_cap_where = "1=1"
            if industria:
                sql_cap_where = "industria = '{}'".format(industria.replace("'", "''"))
            sql_capital = """
            SELECT industria, mes, mes_nombre, idx_estacionalidad,
                   compras_estimadas, ventas_estimadas, recupero_estimado,
                   capital_neto, capital_acumulado, pico_capital
            FROM t_capital_trabajo_mensual
            WHERE {where}
            ORDER BY industria, mes
            """.format(where=sql_cap_where)
            for r in _db_cfo.executesql(sql_capital, as_dict=True):
                r = _fix_row(r)
                ind = r['industria']
                if ind not in capital_trabajo:
                    capital_trabajo[ind] = []
                capital_trabajo[ind].append({
                    'mes': int(r['mes']),
                    'mes_nombre': r['mes_nombre'],
                    'idx_est': float(r.get('idx_estacionalidad') or 0),
                    'compras': float(r.get('compras_estimadas') or 0),
                    'ventas': float(r.get('ventas_estimadas') or 0),
                    'recupero': float(r.get('recupero_estimado') or 0),
                    'neto': float(r.get('capital_neto') or 0),
                    'acumulado': float(r.get('capital_acumulado') or 0),
                    'pico': int(r.get('pico_capital') or 0),
                })
        except:
            pass

    # BLOQUE 11: DATOS ENRIQUECEDORES (margen, concentracion, stock muerto)
    enriquecedores = {}
    if _db_cfo:
        try:
            sql_enr = """
            SELECT industria, margen_bruto_pct,
                   venta_precio_12m, venta_costo_12m,
                   top1_proveedor, top1_pct, top3_pct, top3_proveedores,
                   nivel_concentracion,
                   stock_muerto_90d_uds, stock_muerto_90d_costo,
                   stock_muerto_180d_uds, stock_muerto_180d_costo
            FROM t_enriquecedores_calce
            ORDER BY venta_precio_12m DESC
            """
            for r in _db_cfo.executesql(sql_enr, as_dict=True):
                r = _fix_row(r)
                enriquecedores[r['industria']] = {k: _clean(v) for k, v in r.items()}
        except:
            pass

    # =========================================================================
    # BLOQUE 12: FUNNEL DE DEUDA COMPLETA
    # Pedidos → Remitos sin facturar → Facturas impagas → Saldo vivo
    # =========================================================================
    funnel_deuda = {}
    deuda_proveedores = []
    if dbC:
        try:
            # Remitos de compra sin facturar (codigo=4, estado_cc='0' o '1')
            sql_remitos = """
            SELECT COUNT(*) as cant,
                   ISNULL(SUM(monto_general), 0) as total
            FROM compras2
            WHERE codigo = 4
              AND estado = 'V'
              AND ISNULL(estado_cc, '0') IN ('0', '1')
              AND fecha_comprobante >= '2025-01-01'
            """
            r_rem = dbC.executesql(sql_remitos, as_dict=True)
            if r_rem:
                funnel_deuda['remitos_sin_facturar'] = float(r_rem[0].get('total') or 0)
                funnel_deuda['remitos_cant'] = int(r_rem[0].get('cant') or 0)

            # Saldo NETO por proveedor (debe - haber real)
            # Resuelve: OP sin vincular a facturas individuales
            # Si un proveedor tiene debe=$50M y haber=$50M, saldo=0 (cancelado)
            sql_saldo_neto = """
            SELECT COUNT(*) as proveedores_con_deuda,
                   ISNULL(SUM(saldo_neto), 0) as saldo_vivo
            FROM (
                SELECT numero_cuenta,
                       SUM(CASE WHEN operacion = '+'
                           THEN (importe_pesos - importe_can_pesos)
                           ELSE -(importe_pesos - importe_can_pesos) END) as saldo_neto
                FROM moviprov1
                GROUP BY numero_cuenta
                HAVING SUM(CASE WHEN operacion = '+'
                           THEN (importe_pesos - importe_can_pesos)
                           ELSE -(importe_pesos - importe_can_pesos) END) > 100
            ) neto
            """
            r_sal = dbC.executesql(sql_saldo_neto, as_dict=True)
            if r_sal:
                funnel_deuda['saldo_vivo'] = float(r_sal[0].get('saldo_vivo') or 0)
                funnel_deuda['facturas_cant'] = int(r_sal[0].get('proveedores_con_deuda') or 0)
                funnel_deuda['facturas_impagas'] = funnel_deuda['saldo_vivo']

            # Top 15 proveedores por saldo NETO (debe - haber)
            sql_deuda_prov = """
            SELECT TOP 15
                p.numero as prov_id,
                RTRIM(p.denominacion) as proveedor,
                SUM(CASE WHEN m.operacion = '+'
                    THEN (m.importe_pesos - m.importe_can_pesos)
                    ELSE -(m.importe_pesos - m.importe_can_pesos) END) as saldo_vivo,
                SUM(CASE WHEN m.operacion = '+' THEN 1 ELSE 0 END) as comprobantes
            FROM moviprov1 m
            JOIN proveedores p ON m.numero_cuenta = p.numero
            GROUP BY p.numero, p.denominacion
            HAVING SUM(CASE WHEN m.operacion = '+'
                        THEN (m.importe_pesos - m.importe_can_pesos)
                        ELSE -(m.importe_pesos - m.importe_can_pesos) END) > 1000
            ORDER BY SUM(CASE WHEN m.operacion = '+'
                        THEN (m.importe_pesos - m.importe_can_pesos)
                        ELSE -(m.importe_pesos - m.importe_can_pesos) END) DESC
            """
            deuda_proveedores = [{k: _clean(v) for k, v in _fix_row(r).items()}
                                 for r in dbC.executesql(sql_deuda_prov, as_dict=True)]
        except:
            pass

    # =========================================================================
    # BLOQUE 13: PAGOS POR MEDIO (ultimos 6 meses)
    # Cheque, Transferencia, Efectivo, NC, etc.
    # =========================================================================
    pagos_por_medio = []
    pagos_recientes = []
    if dbC:
        try:
            sql_pagos_medio = """
            SELECT
                CASE m2.codigo_cancelacion
                    WHEN 1 THEN 'Cheque/Transferencia'
                    WHEN 2 THEN 'OP Compensacion'
                    WHEN 3 THEN 'Nota de Credito'
                    WHEN 4 THEN 'ND Contable'
                    WHEN 14 THEN 'Efectivo'
                    WHEN 15 THEN 'Debito Bancario'
                    ELSE 'Otro (Cod ' + CAST(m2.codigo_cancelacion AS VARCHAR) + ')'
                END as medio_pago,
                m2.codigo_cancelacion as cod_medio,
                COUNT(*) as cant,
                SUM(m2.importe_can_pesos) as total_pagado
            FROM moviprov2 m2
            WHERE m2.fecha_cancelacion >= DATEADD(MONTH, -6, GETDATE())
              AND m2.fecha_cancelacion <= GETDATE()
              AND m2.fecha_cancelacion IS NOT NULL
            GROUP BY m2.codigo_cancelacion
            ORDER BY SUM(m2.importe_can_pesos) DESC
            """
            pagos_por_medio = [{k: _clean(v) for k, v in r.items()}
                               for r in dbC.executesql(sql_pagos_medio, as_dict=True)]
        except:
            pass

        try:
            # Pagos mas recientes (ultimas 4 semanas, por semana)
            # Excluir cheques diferidos a futuro con <= GETDATE()
            sql_pagos_sem = """
            SELECT
                'S' + CAST(DATEPART(ISO_WEEK, m2.fecha_cancelacion) AS VARCHAR) as semana,
                MIN(m2.fecha_cancelacion) as desde,
                MAX(m2.fecha_cancelacion) as hasta,
                COUNT(*) as cant,
                SUM(m2.importe_can_pesos) as total,
                COUNT(DISTINCT m2.numero_cuenta) as proveedores
            FROM moviprov2 m2
            WHERE m2.fecha_cancelacion >= DATEADD(WEEK, -4, GETDATE())
              AND m2.fecha_cancelacion <= GETDATE()
              AND m2.fecha_cancelacion IS NOT NULL
            GROUP BY DATEPART(ISO_WEEK, m2.fecha_cancelacion)
            ORDER BY DATEPART(ISO_WEEK, m2.fecha_cancelacion) DESC
            """
            pagos_recientes = [{k: _clean(v) for k, v in r.items()}
                               for r in dbC.executesql(sql_pagos_sem, as_dict=True)]
        except:
            pass

    # Integrar presupuesto en la matriz
    presup_dict = {p['industria']: p for p in presupuesto}
    for m in matriz_lista:
        ind = m['industria']
        if ind in presup_dict:
            p = presup_dict[ind]
            m['presupuesto'] = float(p.get('presupuesto_costo') or 0)
            # Disponible real = presupuesto - pedidos - remitos sin facturar - deuda neta
            disponible_base = float(p.get('disponible_costo') or 0)  # ya tiene presup - pedidos
            m['disponible'] = disponible_base - m.get('remitos_monto', 0) - m.get('deuda_neta', 0)
            m['pct_ejecutado'] = round(
                m.get('fondos_comprometidos', 0) * 100.0 / m['presupuesto'], 1
            ) if m['presupuesto'] > 0 else 0
            m['factor_tendencia'] = float(p.get('factor_tendencia') or 1.0)
            m['presupuesto_ajustado'] = float(p.get('presupuesto_ajustado') or 0)
            m['disponible_ajustado'] = float(p.get('disponible_ajustado') or 0)
            m['tendencia_desc'] = _fix_encoding(p.get('tendencia_desc', ''))
            m['meses_evaluados'] = int(p.get('meses_evaluados') or 0)
            m['pct_ejecutado_ajustado'] = round(
                m['comprometido'] * 100.0 / m['presupuesto_ajustado'], 1
            ) if m['presupuesto_ajustado'] > 0 else 0
            m['factor_tendencia_uds'] = float(p.get('factor_tendencia_uds') or 1.0)
            m['var_ticket_prom'] = float(p.get('var_ticket_prom') or 0)
            m['uds_ytd_2026'] = int(p.get('uds_ytd_2026') or 0)
            m['uds_ytd_2025'] = int(p.get('uds_ytd_2025') or 0)
            m['uds_proy_anual_2026'] = int(p.get('uds_proy_anual_2026') or 0)
            m['diagnostico'] = _fix_encoding(p.get('diagnostico', ''))
        else:
            m['presupuesto'] = 0
            m['disponible'] = 0
            m['pct_ejecutado'] = 0
            m['factor_tendencia'] = 1.0
            m['presupuesto_ajustado'] = 0
            m['disponible_ajustado'] = 0
            m['tendencia_desc'] = ''
            m['meses_evaluados'] = 0
            m['pct_ejecutado_ajustado'] = 0
            m['factor_tendencia_uds'] = 1.0
            m['var_ticket_prom'] = 0
            m['uds_ytd_2026'] = 0
            m['uds_ytd_2025'] = 0
            m['uds_proy_anual_2026'] = 0
            m['diagnostico'] = ''

    # Opciones para filtros
    try:
        industrias = db_omicronvt.executesql(
            "SELECT DISTINCT ISNULL(industria, 'Sin clasificar') AS v FROM t_recupero_inversion ORDER BY 1",
            as_dict=True)
    except:
        industrias = []
    try:
        temporadas = db_omicronvt.executesql(
            "SELECT DISTINCT temporada_tipo AS v FROM t_recupero_inversion ORDER BY 1",
            as_dict=True)
    except:
        temporadas = []

    # Filtros nuevos: rubro, subrubro, grupo, linea, marca (de la cache de pedidos)
    rubros_list = []
    subrubros_list = []
    grupos_list = []
    lineas_list = []
    marcas_list = []
    try:
        rubros_list = [_fix_encoding(r['v']) for r in db_omicronvt.executesql(
            "SELECT DISTINCT rubro_desc AS v FROM pedidos_cumplimiento_cache WHERE rubro_desc IS NOT NULL AND fecha_pedido >= '2025-07-01' ORDER BY 1",
            as_dict=True)]
        subrubros_list = [_fix_encoding(r['v']) for r in db_omicronvt.executesql(
            "SELECT DISTINCT subrubro_desc AS v FROM pedidos_cumplimiento_cache WHERE subrubro_desc IS NOT NULL AND fecha_pedido >= '2025-07-01' ORDER BY 1",
            as_dict=True)]
        grupos_list = [_fix_encoding(r['v']) for r in db_omicronvt.executesql(
            "SELECT DISTINCT grupo_desc AS v FROM pedidos_cumplimiento_cache WHERE grupo_desc IS NOT NULL AND fecha_pedido >= '2025-07-01' ORDER BY 1",
            as_dict=True)]
        lineas_list = [_fix_encoding(r['v']) for r in db_omicronvt.executesql(
            "SELECT DISTINCT linea_desc AS v FROM pedidos_cumplimiento_cache WHERE linea_desc IS NOT NULL AND fecha_pedido >= '2025-07-01' ORDER BY 1",
            as_dict=True)]
    except:
        pass  # columnas aun no existen en cache
    try:
        marcas_list = [_fix_encoding(r['v']) for r in db_omicronvt.executesql(
            "SELECT DISTINCT marca AS v FROM pedidos_cumplimiento_cache WHERE marca IS NOT NULL AND RTRIM(marca) != '' AND fecha_pedido >= '2025-07-01' ORDER BY 1",
            as_dict=True)]
    except:
        pass

    return dict(
        kpi_comp=kpi_comp,
        kpi_rec=kpi_rec,
        matriz=matriz_lista,
        proveedores_presion=[{k: _clean(v) for k, v in r.items()} for r in proveedores_presion],
        vencimientos=[{k: _clean(v) for k, v in r.items()} for r in vencimientos],
        presupuesto=[{k: _clean(v) for k, v in r.items()} for r in presupuesto],
        tendencia_mensual=tendencia_mensual,
        # Nuevos bloques CFO
        flujo_caja=flujo_caja,
        roi_proveedores=[{k: _clean(v) for k, v in r.items()} for r in roi_proveedores],
        roi_benchmark=roi_benchmark,
        roi_periodos_disponibles=roi_periodos_disponibles,
        roi_periodo_activo=roi_periodo_activo,
        capital_trabajo=capital_trabajo,
        enriquecedores=enriquecedores,
        # Remitos viejos sin facturar (limpieza)
        remitos_viejos=remitos_viejos,
        # Deuda completa + pagos
        funnel_deuda=funnel_deuda,
        deuda_proveedores=deuda_proveedores,
        pagos_por_medio=pagos_por_medio,
        pagos_recientes=pagos_recientes,
        # Filtros
        industrias=[_fix_encoding(r['v']) for r in industrias],
        temporadas=[_fix_encoding(r['v']) for r in temporadas],
        rubros=rubros_list,
        subrubros=subrubros_list,
        grupos=grupos_list,
        lineas=lineas_list,
        marcas=marcas_list,
        url_safe=_url_safe,
        html=_html,
        filtro_industria=industria,
        filtro_temporada=temporada,
        filtro_proveedor=proveedor,
        filtro_rubro=rubro,
        filtro_subrubro=subrubro,
        filtro_grupo=grupo,
        filtro_linea=linea,
        filtro_marca=marca,
        fmt=_fmt_moneda,
    )


# =============================================================================
# DRILL-DOWN POR INDUSTRIA
# =============================================================================

def detalle_industria():
    """
    Vista detallada de una industria: marcas con compromisos, presupuesto y recupero.
    Incluye filtros y datos para ordenar columnas en frontend.
    """
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    _requiere_acceso()

    industria = _fix_encoding(request.vars.industria) if request.vars.industria else ''
    if not industria:
        redirect(URL('calce_financiero', 'dashboard'))

    # --- Leer filtros ---
    proveedor_f  = _fix_encoding(request.vars.proveedor)  if request.vars.proveedor  else ''
    marca_f      = _fix_encoding(request.vars.marca)      if request.vars.marca      else ''
    rubro_f      = _fix_encoding(request.vars.rubro)      if request.vars.rubro      else ''
    subrubro_f   = _fix_encoding(request.vars.subrubro)   if request.vars.subrubro   else ''
    grupo_f      = _fix_encoding(request.vars.grupo)      if request.vars.grupo      else ''
    linea_f      = _fix_encoding(request.vars.linea)      if request.vars.linea      else ''
    temporada_f  = _fix_encoding(request.vars.temporada)  if request.vars.temporada  else ''

    industria_safe = industria.replace("'", "''")

    # --- WHERE dinamico para pedidos ---
    where_parts = [
        "industria = '%s'" % industria_safe,
        "fecha_pedido >= '2025-07-01'"
    ]
    if proveedor_f:
        where_parts.append("proveedor LIKE '%%%s%%'" % proveedor_f.replace("'", "''"))
    if marca_f:
        where_parts.append("RTRIM(marca) = '%s'" % marca_f.replace("'", "''"))
    if rubro_f:
        where_parts.append("rubro_desc = '%s'" % rubro_f.replace("'", "''"))
    if subrubro_f:
        where_parts.append("subrubro_desc = '%s'" % subrubro_f.replace("'", "''"))
    if grupo_f:
        where_parts.append("grupo_desc = '%s'" % grupo_f.replace("'", "''"))
    if linea_f:
        where_parts.append("linea_desc = '%s'" % linea_f.replace("'", "''"))
    where_pedidos = " AND ".join(where_parts)

    # =========================================================================
    # 1. COMPROMISOS POR MARCA (desde cache)
    # =========================================================================
    sql_por_marca = """
    SELECT
        RTRIM(marca) AS marca,
        COUNT(DISTINCT cod_proveedor) AS proveedores,
        COUNT(DISTINCT CAST(sucursal AS VARCHAR) + '-' + CAST(numero AS VARCHAR)) AS pedidos,
        SUM(monto_pedido) AS comprometido,
        SUM(monto_pendiente) AS pendiente,
        SUM(cant_pedida) AS unidades_pedidas,
        SUM(cant_recibida) AS unidades_recibidas,
        CASE WHEN SUM(cant_pedida) = 0 THEN 0
             ELSE ROUND(SUM(cant_recibida) * 100.0 / SUM(cant_pedida), 1)
        END AS pct_cumplimiento,
        SUM(CASE WHEN alerta_vencimiento = 'VENCIDO' THEN monto_pendiente ELSE 0 END) AS monto_vencido,
        SUM(CASE WHEN alerta_vencimiento = 'VENCIDO' THEN 1 ELSE 0 END) AS lineas_vencidas
    FROM pedidos_cumplimiento_cache
    WHERE %s
    GROUP BY RTRIM(marca)
    ORDER BY SUM(monto_pedido) DESC
    """ % where_pedidos

    try:
        marcas_pedidos = [_fix_row(r) for r in db_omicronvt.executesql(sql_por_marca, as_dict=True)]
    except Exception as e:
        marcas_pedidos = []

    # =========================================================================
    # 2. PERIODO ACTIVO (para calcular presupuesto)
    # =========================================================================
    periodo = None
    try:
        if temporada_f:
            # Si el usuario eligio una temporada especifica
            periodo_rows = db_omicronvt.executesql("""
                SELECT TOP 1 anio_base, mes_desde, mes_hasta, temporada, anio_objetivo
                FROM t_periodos_industria
                WHERE industria = '%s' AND activo = 1
                  AND temporada = '%s'
                ORDER BY anio_objetivo DESC
            """ % (industria_safe, temporada_f.replace("'", "''")), as_dict=True)
            if periodo_rows:
                periodo = periodo_rows[0]
        if not periodo:
            # Buscar periodo que contenga el mes actual
            periodo_rows = db_omicronvt.executesql("""
                SELECT TOP 1 anio_base, mes_desde, mes_hasta, temporada, anio_objetivo
                FROM t_periodos_industria
                WHERE industria = '%s' AND activo = 1
                  AND (
                      (mes_desde <= mes_hasta AND MONTH(GETDATE()) BETWEEN mes_desde AND mes_hasta)
                      OR
                      (mes_desde > mes_hasta AND (MONTH(GETDATE()) >= mes_desde OR MONTH(GETDATE()) <= mes_hasta))
                  )
                ORDER BY anio_objetivo DESC
            """ % industria_safe, as_dict=True)
            if periodo_rows:
                periodo = periodo_rows[0]
            else:
                # Fallback: ultimo periodo activo
                periodo_rows = db_omicronvt.executesql("""
                    SELECT TOP 1 anio_base, mes_desde, mes_hasta, temporada, anio_objetivo
                    FROM t_periodos_industria
                    WHERE industria = '%s' AND activo = 1
                    ORDER BY anio_objetivo DESC
                """ % industria_safe, as_dict=True)
                if periodo_rows:
                    periodo = periodo_rows[0]
    except:
        pass

    # =========================================================================
    # 3. PRESUPUESTO POR MARCA (venta a costo del anio base)
    # =========================================================================
    presupuesto_marca = {}
    if periodo:
        mes_desde = int(periodo['mes_desde'])
        mes_hasta = int(periodo['mes_hasta'])
        anio_base = int(periodo['anio_base'])

        if mes_desde <= mes_hasta:
            mes_filter = "MONTH(v2.fecha_comprobante) BETWEEN %d AND %d" % (mes_desde, mes_hasta)
        else:
            mes_filter = "(MONTH(v2.fecha_comprobante) >= %d OR MONTH(v2.fecha_comprobante) <= %d)" % (mes_desde, mes_hasta)

        sql_presup = """
        SELECT
            RTRIM(m.descripcion) AS marca,
            SUM(v1.cantidad * v1.precio_costo) AS presupuesto_costo,
            SUM(v1.cantidad) AS presupuesto_unidades,
            COUNT(DISTINCT v1.articulo) AS articulos_base
        FROM msgestionC.dbo.ventas1 v1
        JOIN msgestionC.dbo.ventas2 v2
            ON v1.empresa = v2.empresa AND v1.codigo = v2.codigo
           AND v1.letra = v2.letra AND v1.sucursal = v2.sucursal
           AND v1.numero = v2.numero AND v1.orden = v2.orden
        JOIN msgestion01art.dbo.articulo a ON v1.articulo = a.codigo
        JOIN msgestionC.dbo.marcas m ON a.marca = m.codigo
        JOIN map_subrubro_industria ind ON a.subrubro = ind.subrubro
        WHERE v2.codigo = 1
          AND YEAR(v2.fecha_comprobante) = %d
          AND ind.industria = '%s'
          AND a.subrubro > 0
          AND a.marca NOT IN (1316, 1317, 1158, 436)
          AND %s
        GROUP BY RTRIM(m.descripcion)
        """ % (anio_base, industria_safe, mes_filter)

        try:
            for r in db_omicronvt.executesql(sql_presup, as_dict=True):
                r = _fix_row(r)
                presupuesto_marca[r['marca']] = r
        except:
            pass

    # =========================================================================
    # 3b. FACTOR DE TENDENCIA (de t_presupuesto_industria)
    # =========================================================================
    factor_tendencia = 1.0
    factor_tendencia_uds = 1.0
    tendencia_desc = ''
    meses_evaluados = 0
    var_ticket_prom = 0
    uds_ytd_2026 = 0
    uds_ytd_2025 = 0
    uds_proy_anual_2026 = 0
    diagnostico = ''
    try:
        if temporada_f:
            sql_factor = """
                SELECT factor_tendencia, factor_tendencia_uds,
                       tendencia_desc, meses_evaluados,
                       var_ticket_prom, uds_ytd_2026, uds_ytd_2025,
                       uds_proy_anual_2026, diagnostico
                FROM t_presupuesto_industria
                WHERE industria = '%s' AND temporada = '%s'
            """ % (industria_safe, temporada_f.replace("'", "''"))
        else:
            sql_factor = """
                SELECT TOP 1 factor_tendencia, factor_tendencia_uds,
                       tendencia_desc, meses_evaluados,
                       var_ticket_prom, uds_ytd_2026, uds_ytd_2025,
                       uds_proy_anual_2026, diagnostico
                FROM t_presupuesto_industria
                WHERE industria = '%s'
                ORDER BY presupuesto_costo DESC
            """ % industria_safe
        factor_rows = db_omicronvt.executesql(sql_factor, as_dict=True)
        if factor_rows:
            fr = factor_rows[0]
            factor_tendencia = float(fr.get('factor_tendencia') or 1.0)
            factor_tendencia_uds = float(fr.get('factor_tendencia_uds') or 1.0)
            tendencia_desc = _fix_encoding(fr.get('tendencia_desc', ''))
            meses_evaluados = int(fr.get('meses_evaluados') or 0)
            var_ticket_prom = float(fr.get('var_ticket_prom') or 0)
            uds_ytd_2026 = int(fr.get('uds_ytd_2026') or 0)
            uds_ytd_2025 = int(fr.get('uds_ytd_2025') or 0)
            uds_proy_anual_2026 = int(fr.get('uds_proy_anual_2026') or 0)
            diagnostico = _fix_encoding(fr.get('diagnostico', ''))
    except:
        pass

    # =========================================================================
    # 3c. TENDENCIA MENSUAL para esta industria
    # =========================================================================
    tendencia_meses = []
    try:
        sql_tend = """
            SELECT mes, facturacion_2024, facturacion_2025, facturacion_2026,
                   unidades_2025, unidades_2026,
                   ticket_2025, ticket_2026,
                   ratio_26v25, ratio_uds_26v25, ratio_ticket_26v25,
                   idx_estacionalidad, mes_completo_2026
            FROM t_tendencia_facturacion
            WHERE industria = '%s' AND (facturacion_2025 > 0 OR unidades_2025 > 0)
            ORDER BY mes
        """ % industria_safe
        for r in db_omicronvt.executesql(sql_tend, as_dict=True):
            tendencia_meses.append({
                'mes': int(r['mes']),
                'f2024': float(r.get('facturacion_2024') or 0),
                'f2025': float(r.get('facturacion_2025') or 0),
                'f2026': float(r.get('facturacion_2026') or 0),
                'ratio': float(r.get('ratio_26v25') or 0),
                'ratio_uds': float(r.get('ratio_uds_26v25') or 0),
                'ratio_ticket': float(r.get('ratio_ticket_26v25') or 0),
                'u2025': int(r.get('unidades_2025') or 0),
                'u2026': int(r.get('unidades_2026') or 0),
                'tk2025': float(r.get('ticket_2025') or 0),
                'tk2026': float(r.get('ticket_2026') or 0),
                'idx_est': float(r.get('idx_estacionalidad') or 0),
                'completo': int(r.get('mes_completo_2026') or 0),
            })
    except:
        pass

    # =========================================================================
    # 4. COMBINAR: marcas con compromisos + presupuesto + ajuste
    # =========================================================================
    marcas_combinadas = []
    marcas_vistas = set()

    for mp in marcas_pedidos:
        m_nombre = _fix_encoding(mp.get('marca', '')) or 'Sin marca'
        m_nombre_clean = m_nombre.strip() if hasattr(m_nombre, 'strip') else m_nombre
        presup = presupuesto_marca.get(m_nombre_clean, {})
        presup_costo = float(presup.get('presupuesto_costo') or 0)
        presup_ajustado = presup_costo * factor_tendencia
        presup_uds = int(presup.get('presupuesto_unidades') or 0)
        presup_uds_ajustado = int(presup_uds * factor_tendencia_uds)
        comprometido = float(mp.get('comprometido') or 0)

        marcas_combinadas.append({
            'marca': m_nombre_clean,
            'proveedores': int(mp.get('proveedores') or 0),
            'pedidos': int(mp.get('pedidos') or 0),
            'comprometido': comprometido,
            'pendiente': float(mp.get('pendiente') or 0),
            'unidades_pedidas': int(mp.get('unidades_pedidas') or 0),
            'unidades_recibidas': int(mp.get('unidades_recibidas') or 0),
            'pct_cumplimiento': float(mp.get('pct_cumplimiento') or 0),
            'monto_vencido': float(mp.get('monto_vencido') or 0),
            'lineas_vencidas': int(mp.get('lineas_vencidas') or 0),
            'presupuesto': presup_costo,
            'presupuesto_ajustado': presup_ajustado,
            'presupuesto_uds': presup_uds,
            'presupuesto_uds_ajustado': presup_uds_ajustado,
            'articulos_base': int(presup.get('articulos_base') or 0),
            'disponible': presup_costo - comprometido,
            'disponible_ajustado': presup_ajustado - comprometido,
            'pct_ejecutado': round(comprometido * 100.0 / presup_costo, 1) if presup_costo > 0 else 0,
            'pct_ejecutado_ajustado': round(comprometido * 100.0 / presup_ajustado, 1) if presup_ajustado > 0 else 0,
        })
        marcas_vistas.add(m_nombre_clean)

    # Agregar marcas que tienen presupuesto pero NO tienen pedidos activos
    for m_nombre, presup in presupuesto_marca.items():
        if m_nombre not in marcas_vistas:
            presup_costo = float(presup.get('presupuesto_costo') or 0)
            if presup_costo < 10000:
                continue
            presup_ajustado = presup_costo * factor_tendencia
            presup_uds = int(presup.get('presupuesto_unidades') or 0)
            presup_uds_ajustado = int(presup_uds * factor_tendencia_uds)
            marcas_combinadas.append({
                'marca': m_nombre,
                'proveedores': 0, 'pedidos': 0,
                'comprometido': 0, 'pendiente': 0,
                'unidades_pedidas': 0, 'unidades_recibidas': 0,
                'pct_cumplimiento': 0, 'monto_vencido': 0, 'lineas_vencidas': 0,
                'presupuesto': presup_costo,
                'presupuesto_ajustado': presup_ajustado,
                'presupuesto_uds': presup_uds,
                'presupuesto_uds_ajustado': presup_uds_ajustado,
                'articulos_base': int(presup.get('articulos_base') or 0),
                'disponible': presup_costo,
                'disponible_ajustado': presup_ajustado,
                'pct_ejecutado': 0,
                'pct_ejecutado_ajustado': 0,
            })

    # =========================================================================
    # 5. PROVEEDORES CON COMPROMISOS (mantiene el detalle original)
    # =========================================================================
    sql_proveedores = """
    SELECT
        cod_proveedor,
        proveedor,
        SUM(monto_pedido) AS comprometido,
        SUM(monto_pendiente) AS pendiente,
        SUM(cant_pedida) AS unidades_pedidas,
        SUM(cant_recibida) AS unidades_recibidas,
        CASE WHEN SUM(cant_pedida) = 0 THEN 0
             ELSE ROUND(SUM(cant_recibida) * 100.0 / SUM(cant_pedida), 1)
        END AS pct_cumplimiento,
        SUM(CASE WHEN alerta_vencimiento = 'VENCIDO' THEN 1 ELSE 0 END) AS lineas_vencidas,
        MIN(fecha_pedido) AS primer_pedido,
        MAX(fecha_entrega) AS ultima_entrega
    FROM pedidos_cumplimiento_cache
    WHERE %s
    GROUP BY cod_proveedor, proveedor
    ORDER BY SUM(monto_pedido) DESC
    """ % where_pedidos

    try:
        proveedores_pedidos = [_fix_row(r) for r in db_omicronvt.executesql(sql_proveedores, as_dict=True)]
    except:
        proveedores_pedidos = []

    # =========================================================================
    # 6. RECUPERO POR PROVEEDOR
    # =========================================================================
    sql_recupero = """
    SELECT
        proveedor_nombre,
        periodo,
        total_costo_compra,
        dias_50,
        dias_75,
        plazo_pago_real_prom,
        pct_vendido,
        pct_vendido_al_pago,
        brecha_pago_vs_rec50,
        estado
    FROM t_recupero_inversion
    WHERE industria = '%s'
    ORDER BY total_costo_compra DESC
    """ % industria_safe

    try:
        recupero_proveedores = [_fix_row(r) for r in db_omicronvt.executesql(sql_recupero, as_dict=True)]
    except:
        recupero_proveedores = []

    # =========================================================================
    # 6b. REMITOS SIN FACTURAR POR PROVEEDOR (esta industria, 2026+)
    # =========================================================================
    remitos_por_proveedor = {}
    if dbC:
        try:
            sql_rem_prov = """
            ;WITH rem_prov AS (
                SELECT
                    c2.cuenta_cc as prov_id,
                    RTRIM(c2.denominacion) as proveedor,
                    c2.monto_general, c2.fecha_comprobante,
                    ISNULL(
                        (SELECT TOP 1 ISNULL(ind.industria, 'Sin clasificar')
                         FROM compras1 c1
                         JOIN msgestion01art.dbo.articulo a ON c1.articulo = a.codigo
                         LEFT JOIN omicronvt.dbo.map_subrubro_industria ind ON a.subrubro = ind.subrubro
                         WHERE c1.empresa = c2.empresa AND c1.codigo = c2.codigo
                           AND c1.letra = c2.letra AND c1.sucursal = c2.sucursal
                           AND c1.numero = c2.numero AND c1.orden = c2.orden
                           AND a.marca NOT IN (1316, 1317, 1158, 436)
                        ), 'Sin clasificar') AS industria
                FROM compras2 c2
                WHERE c2.codigo IN (7, 36) AND c2.estado = 'V'
                  AND c2.fecha_comprobante >= '2026-01-01'
            )
            SELECT prov_id, proveedor,
                   COUNT(*) as cant_remitos,
                   SUM(monto_general) as monto_remitos,
                   AVG(DATEDIFF(DAY, fecha_comprobante, GETDATE())) as dias_promedio
            FROM rem_prov
            WHERE industria = '%s'
            GROUP BY prov_id, proveedor
            """ % industria_safe
            for r in dbC.executesql(sql_rem_prov, as_dict=True):
                r = _fix_row(r)
                pid = str(r.get('prov_id', ''))
                remitos_por_proveedor[pid] = {
                    'monto': float(r.get('monto_remitos') or 0),
                    'cant': int(r.get('cant_remitos') or 0),
                    'dias_promedio': int(r.get('dias_promedio') or 0),
                }
        except:
            pass

    # =========================================================================
    # 6c. DEUDA NETA POR PROVEEDOR (esta industria)
    # =========================================================================
    deuda_por_proveedor = {}
    if dbC:
        try:
            sql_deuda_prov = """
            SELECT sp.numero_cuenta as prov_id, sp.saldo_neto
            FROM (
                SELECT numero_cuenta,
                       SUM(CASE WHEN operacion = '+'
                           THEN (importe_pesos - importe_can_pesos)
                           ELSE -(importe_pesos - importe_can_pesos) END) as saldo_neto
                FROM moviprov1
                GROUP BY numero_cuenta
                HAVING SUM(CASE WHEN operacion = '+'
                           THEN (importe_pesos - importe_can_pesos)
                           ELSE -(importe_pesos - importe_can_pesos) END) > 100
            ) sp
            JOIN omicronvt.dbo.t_roi_proveedor roi
                ON sp.numero_cuenta = roi.proveedor_id
            WHERE roi.industria = '%s'
            """ % industria_safe
            for r in dbC.executesql(sql_deuda_prov, as_dict=True):
                r = _fix_row(r)
                pid = str(r.get('prov_id', ''))
                deuda_por_proveedor[pid] = float(r.get('saldo_neto') or 0)
        except:
            pass

    # Inyectar remitos y deuda en proveedores_pedidos
    for pp in proveedores_pedidos:
        pid = str(pp.get('cod_proveedor', ''))
        rem = remitos_por_proveedor.get(pid, {})
        pp['remitos_monto'] = rem.get('monto', 0)
        pp['remitos_cant'] = rem.get('cant', 0)
        pp['deuda_neta'] = deuda_por_proveedor.get(pid, 0)
        pp['fondos_comprometidos'] = float(pp.get('comprometido', 0)) + pp['remitos_monto'] + pp['deuda_neta']

    # =========================================================================
    # 7. TOTALES DE LA INDUSTRIA (para KPIs arriba)
    # =========================================================================
    total_remitos = sum(pp.get('remitos_monto', 0) for pp in proveedores_pedidos)
    total_deuda = sum(pp.get('deuda_neta', 0) for pp in proveedores_pedidos)
    total_comprometido = sum(m['comprometido'] for m in marcas_combinadas)
    total_fondos = total_comprometido + total_remitos + total_deuda
    total_presupuesto = sum(m['presupuesto'] for m in marcas_combinadas)
    total_presupuesto_ajustado = sum(m['presupuesto_ajustado'] for m in marcas_combinadas)
    total_disponible = total_presupuesto - total_fondos
    total_disponible_ajustado = total_presupuesto_ajustado - total_fondos
    total_pct_ejecutado = round(total_comprometido * 100.0 / total_presupuesto, 1) if total_presupuesto > 0 else 0
    total_pct_ejecutado_ajustado = round(total_comprometido * 100.0 / total_presupuesto_ajustado, 1) if total_presupuesto_ajustado > 0 else 0
    total_vencido = sum(m['monto_vencido'] for m in marcas_combinadas)

    # =========================================================================
    # 8. OPCIONES PARA FILTROS (valores disponibles en esta industria)
    # =========================================================================
    try:
        marcas_list = [_fix_encoding(r['v']) for r in db_omicronvt.executesql(
            "SELECT DISTINCT RTRIM(marca) AS v FROM pedidos_cumplimiento_cache "
            "WHERE industria = '%s' AND marca IS NOT NULL AND RTRIM(marca) != '' "
            "AND fecha_pedido >= '2025-07-01' ORDER BY 1" % industria_safe,
            as_dict=True)]
    except:
        marcas_list = []

    try:
        proveedores_list = [_fix_encoding(r['v']) for r in db_omicronvt.executesql(
            "SELECT DISTINCT proveedor AS v FROM pedidos_cumplimiento_cache "
            "WHERE industria = '%s' AND fecha_pedido >= '2025-07-01' ORDER BY 1" % industria_safe,
            as_dict=True)]
    except:
        proveedores_list = []

    temporadas_list = []
    try:
        temporadas_list = [_fix_encoding(r['v']) for r in db_omicronvt.executesql(
            "SELECT DISTINCT temporada AS v FROM t_periodos_industria "
            "WHERE industria = '%s' AND activo = 1 ORDER BY 1" % industria_safe,
            as_dict=True)]
    except:
        pass

    rubros_list = []
    subrubros_list = []
    grupos_list = []
    lineas_list = []
    try:
        rubros_list = [_fix_encoding(r['v']) for r in db_omicronvt.executesql(
            "SELECT DISTINCT rubro_desc AS v FROM pedidos_cumplimiento_cache "
            "WHERE industria = '%s' AND rubro_desc IS NOT NULL "
            "AND fecha_pedido >= '2025-07-01' ORDER BY 1" % industria_safe,
            as_dict=True)]
        subrubros_list = [_fix_encoding(r['v']) for r in db_omicronvt.executesql(
            "SELECT DISTINCT subrubro_desc AS v FROM pedidos_cumplimiento_cache "
            "WHERE industria = '%s' AND subrubro_desc IS NOT NULL "
            "AND fecha_pedido >= '2025-07-01' ORDER BY 1" % industria_safe,
            as_dict=True)]
        grupos_list = [_fix_encoding(r['v']) for r in db_omicronvt.executesql(
            "SELECT DISTINCT grupo_desc AS v FROM pedidos_cumplimiento_cache "
            "WHERE industria = '%s' AND grupo_desc IS NOT NULL "
            "AND fecha_pedido >= '2025-07-01' ORDER BY 1" % industria_safe,
            as_dict=True)]
        lineas_list = [_fix_encoding(r['v']) for r in db_omicronvt.executesql(
            "SELECT DISTINCT linea_desc AS v FROM pedidos_cumplimiento_cache "
            "WHERE industria = '%s' AND linea_desc IS NOT NULL "
            "AND fecha_pedido >= '2025-07-01' ORDER BY 1" % industria_safe,
            as_dict=True)]
    except:
        pass

    return dict(
        industria=_fix_encoding(industria),
        marcas=marcas_combinadas,
        proveedores_pedidos=[{k: _clean(v) for k, v in r.items()} for r in proveedores_pedidos],
        recupero_proveedores=[{k: _clean(v) for k, v in r.items()} for r in recupero_proveedores],
        total_comprometido=total_comprometido,
        total_remitos=total_remitos,
        total_deuda=total_deuda,
        total_fondos=total_fondos,
        total_presupuesto=total_presupuesto,
        total_presupuesto_ajustado=total_presupuesto_ajustado,
        total_disponible=total_disponible,
        total_disponible_ajustado=total_disponible_ajustado,
        total_pct_ejecutado=total_pct_ejecutado,
        total_pct_ejecutado_ajustado=total_pct_ejecutado_ajustado,
        total_vencido=total_vencido,
        factor_tendencia=factor_tendencia,
        factor_tendencia_uds=factor_tendencia_uds,
        tendencia_desc=tendencia_desc,
        meses_evaluados=meses_evaluados,
        var_ticket_prom=var_ticket_prom,
        uds_ytd_2026=uds_ytd_2026,
        uds_ytd_2025=uds_ytd_2025,
        uds_proy_anual_2026=uds_proy_anual_2026,
        diagnostico=diagnostico,
        tendencia_meses=tendencia_meses,
        periodo=periodo,
        temporadas_list=temporadas_list,
        marcas_list=marcas_list,
        proveedores_list=proveedores_list,
        rubros_list=rubros_list,
        subrubros_list=subrubros_list,
        grupos_list=grupos_list,
        lineas_list=lineas_list,
        filtro_proveedor=proveedor_f,
        filtro_marca=marca_f,
        filtro_rubro=rubro_f,
        filtro_subrubro=subrubro_f,
        filtro_grupo=grupo_f,
        filtro_linea=linea_f,
        filtro_temporada=temporada_f,
        fmt=_fmt_moneda,
        html=_html,
        url_safe=_url_safe,
    )


# =============================================================================
# AJAX: DATOS PARA GRÁFICOS
# =============================================================================

def ajax_calce_por_industria():
    """
    AJAX: Retorna datos de calce por industria para gráficos.
    Formato: [{industria, comprometido, recuperado, brecha, semaforo}, ...]
    """
    _requiere_acceso()
    where_rec = _where_industria(
        request.vars.industria or '',
        request.vars.proveedor or '',
        request.vars.temporada or ''
    )

    sql = """
    SELECT
        industria,
        SUM(total_costo_compra) AS inversion,
        AVG(pct_vendido) AS pct_vendido,
        AVG(pct_vendido_al_pago) AS pct_al_pago,
        AVG(brecha_pago_vs_rec50) AS brecha
    FROM t_recupero_inversion
    WHERE {where}
    GROUP BY industria
    ORDER BY SUM(total_costo_compra) DESC
    """.format(where=where_rec)

    data = db_omicronvt.executesql(sql, as_dict=True)

    return response.json({
        'data': [{k: _clean(v) for k, v in r.items()} for r in data]
    })


# =============================================================================
# EXPORTAR CSV
# =============================================================================

def exportar_csv():
    """Exporta la matriz de calce como CSV."""
    _requiere_acceso()
    import csv, io

    where_rec = _where_industria(
        request.vars.industria or '',
        request.vars.proveedor or '',
        request.vars.temporada or ''
    )

    sql = """
    SELECT
        industria,
        proveedor_nombre,
        periodo,
        total_costo_compra AS inversion,
        dias_50,
        dias_75,
        plazo_pago_real_prom AS plazo_pago,
        pct_vendido,
        pct_vendido_al_pago,
        brecha_pago_vs_rec50 AS brecha,
        estado
    FROM t_recupero_inversion
    WHERE {where}
    ORDER BY industria, total_costo_compra DESC
    """.format(where=where_rec)

    data = db_omicronvt.executesql(sql, as_dict=True)

    output = io.BytesIO()
    if data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys(), delimiter=b';')
        writer.writeheader()
        for row in data:
            clean_row = {}
            for k, v in row.items():
                val = _clean(v)
                if isinstance(val, unicode):
                    clean_row[k] = val.encode('utf-8')
                elif isinstance(val, str):
                    clean_row[k] = val
                else:
                    clean_row[k] = str(val)
            writer.writerow(clean_row)

    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=calce_financiero_%s.csv' % request.now.strftime('%Y-%m-%d')
    return b'\xef\xbb\xbf' + output.getvalue()
