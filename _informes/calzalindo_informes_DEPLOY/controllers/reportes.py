# -*- coding: utf-8 -*-
"""
REPORTES ANALÍTICOS - Controller
Genera reportes de Notas de Pedido y Recupero de Inversión.
Usa db_omicronvt (definido en models/db.py) para ejecutar SQL contra omicronvt.
"""
# =============================================================================
# HELPERS
# =============================================================================
def _uvar(val):
    """Python 2.7: decodifica un var de request a unicode.
    request.vars puede devolver str con bytes UTF-8 cuando el query string
    tiene caracteres como É, Ñ, etc. (ej: proveedor=SOXPIGU%C3%89+S.A.)
    pyodbc requiere unicode puro, no bytes no-ASCII.
    """
    if val is None:
        return u''
    if isinstance(val, str):
        return val.decode('utf-8', errors='replace')
    return val


def _ejecutar_sql(sql, as_dict=True):
    """Ejecuta SQL contra omicronvt y devuelve lista de dicts o tuplas.
    Usa READ UNCOMMITTED para evitar bloqueos por locks (equivale a NOLOCK).
    """
    db_omicronvt.executesql("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    rows = db_omicronvt.executesql(sql, as_dict=as_dict)
    return rows

def _filtro_where(filtros):
    """
    Recibe dict de filtros del request.vars y devuelve cláusula WHERE.
    Solo agrega condiciones para filtros con valor.
    """
    condiciones = []
    for campo, valor in filtros.items():
        if valor and valor.strip():
            valor_limpio = valor.strip().replace("'", "''")
            if campo.endswith('_like'):
                campo_real = campo.replace('_like', '')
                condiciones.append("{} LIKE '%{}%'".format(campo_real, valor_limpio))
            else:
                condiciones.append("{} = '{}'".format(campo, valor_limpio))
    return " AND ".join(condiciones)

def _url_safe(val):
    """Encodea unicode a UTF-8 para usar en URL(vars=...).
    Python 2.7 urllib.urlencode falla con unicode (ej: SOXPIGUÉ S.A.)
    """
    if val is None:
        return ''
    if isinstance(val, unicode):
        return val.encode('utf-8')
    return str(val)

def _formato_moneda(valor):
    """Formatea un número como moneda argentina."""
    if valor is None:
        return "$ 0"
    try:
        return "$ {:,.0f}".format(float(valor)).replace(",", ".")
    except:
        return "$ 0"

# =============================================================================
# SYNC DE DATOS (fuerza refresco desde produccion antes de ver reporte)
# =============================================================================
def sync_pedidos():
    """Llama al SP que sincroniza datos de pedidos desde produccion a replica.
    Requiere que el DBA haya creado sp_sync_pedidos en omicronvt.
    Se llama via AJAX antes de cargar el dashboard.
    """
    _requiere_acceso()
    import json
    try:
        db_omicronvt.executesql("EXEC omicronvt.dbo.sp_sync_pedidos")
        db_omicronvt.commit()
        return json.dumps(dict(ok=True, msg='Datos actualizados'))
    except Exception as e:
        return json.dumps(dict(ok=False, msg=str(e)))

# =============================================================================
# NOTAS DE PEDIDO
# =============================================================================
def pedidos():
    """Dashboard principal de Notas de Pedido.
    OPTIMIZADO v3: UNA sola query a la vista, toda la agregacion en Python.
    La vista v_pedidos_cumplimiento hace joins cross-database costosos;
    expandirla 1 vez en lugar de 5 reduce el tiempo ~80%.
    """
    _requiere_acceso()
    from datetime import datetime, date
    import time as _time
    _t0 = _time.time()

    # Auto-sync: refrescar cache cada 10 minutos automaticamente
    def _do_sync():
        db_omicronvt.executesql("EXEC omicronvt.dbo.sp_sync_pedidos")
        db_omicronvt.commit()
        return True
    try:
        cache.ram('pedidos_sync', _do_sync, time_expire=600)
    except:
        pass  # si falla el sync, usar cache vieja

    industria = request.vars.industria or ''
    proveedor = _uvar(request.vars.proveedor)
    estado = request.vars.estado or ''

    where_parts = ["1=1"]
    if industria:
        where_parts.append("industria = '{}'".format(industria.replace("'", "''")))
    if proveedor:
        where_parts.append("proveedor LIKE '%{}%'".format(proveedor.replace("'", "''")))
    if estado:
        where_parts.append("estado_cumplimiento = '{}'".format(estado.replace("'", "''")))

    where_clause = " AND ".join(where_parts)

    # ---------------------------------------------------------------
    # UNA SOLA QUERY: traemos todas las filas con las columnas necesarias
    # ---------------------------------------------------------------
    sql = """
    SELECT
        cod_proveedor, proveedor,
        ISNULL(industria, 'Sin clasificar') AS industria,
        ISNULL(marca, '') AS marca,
        articulo, descripcion,
        cant_pedida, cant_recibida, cant_pendiente,
        estado_cumplimiento,
        monto_pedido, monto_pendiente,
        fecha_pedido, fecha_entrega,
        dias_desde_pedido, alerta_vencimiento,
        sucursal, numero
    FROM pedidos_cumplimiento_cache
    WHERE {}
    """.format(where_clause)
    rows = _ejecutar_sql(sql)

    # ---------------------------------------------------------------
    # PYTHON: calculamos todo desde las filas crudas
    # ---------------------------------------------------------------
    hoy = date.today()

    # -- KPIs --
    pedidos_set = set()
    total_lineas = 0
    sum_pedida = 0
    sum_recibida = 0
    sum_pendiente = 0
    sum_monto = 0
    sum_monto_pend = 0
    lineas_vencidas = 0

    # -- Para proveedores agrupados --
    prov_data = {}   # key = (cod_proveedor, proveedor, industria)

    # -- Para vencidas (top 20) --
    lista_vencidas = []

    # -- Para antiguedad --
    rangos_ant = {
        '0-7 dias': {'lineas': 0, 'unidades': 0, 'monto': 0, 'min_dias': 0},
        '8-15 dias': {'lineas': 0, 'unidades': 0, 'monto': 0, 'min_dias': 8},
        '16-30 dias': {'lineas': 0, 'unidades': 0, 'monto': 0, 'min_dias': 16},
        '31-60 dias': {'lineas': 0, 'unidades': 0, 'monto': 0, 'min_dias': 31},
        '61-90 dias': {'lineas': 0, 'unidades': 0, 'monto': 0, 'min_dias': 61},
        'Mas de 90': {'lineas': 0, 'unidades': 0, 'monto': 0, 'min_dias': 91},
    }

    # -- Filtros --
    _industrias_set = set()
    _proveedores_set = set()
    _estados_set = set()

    for r in rows:
        cp = r.get('cant_pedida', 0) or 0
        cr = r.get('cant_recibida', 0) or 0
        cpend = r.get('cant_pendiente', 0) or 0
        mp = r.get('monto_pedido', 0) or 0
        mpend = r.get('monto_pendiente', 0) or 0
        alerta = r.get('alerta_vencimiento', '')
        est = r.get('estado_cumplimiento', '')
        dias = r.get('dias_desde_pedido', 0) or 0
        prov_nom = r.get('proveedor', '')
        ind = r.get('industria', 'Sin clasificar')
        cod_prov = r.get('cod_proveedor', '')

        # KPIs
        suc = r.get('sucursal', '')
        num = r.get('numero', '')
        pedidos_set.add('{}-{}'.format(suc, num))
        total_lineas += 1
        sum_pedida += cp
        sum_recibida += cr
        sum_pendiente += cpend
        sum_monto += mp
        sum_monto_pend += mpend
        if alerta == 'VENCIDO':
            lineas_vencidas += 1

        # Proveedores agrupados
        pkey = (cod_prov, prov_nom, ind)
        if pkey not in prov_data:
            prov_data[pkey] = {
                'proveedor': prov_nom,
                'industria': ind,
                'arts': set(),
                'marcas': set(),
                'pedido': 0, 'recibido': 0, 'pendiente': 0,
                'monto_total': 0, 'monto_pendiente': 0,
                'vencidas': 0
            }
        pd = prov_data[pkey]
        pd['arts'].add(r.get('articulo', ''))
        marca_val = r.get('marca', '')
        if marca_val:
            pd['marcas'].add(marca_val)
        pd['pedido'] += cp
        pd['recibido'] += cr
        pd['pendiente'] += cpend
        pd['monto_total'] += mp
        pd['monto_pendiente'] += mpend
        if alerta == 'VENCIDO':
            pd['vencidas'] += 1

        # Vencidas (candidatas para top 20)
        if alerta == 'VENCIDO':
            fe = r.get('fecha_entrega', None)
            if fe:
                try:
                    if hasattr(fe, 'date'):
                        dias_venc = (hoy - fe.date()).days
                    elif isinstance(fe, date):
                        dias_venc = (hoy - fe).days
                    else:
                        dias_venc = dias
                except:
                    dias_venc = dias
            else:
                dias_venc = dias
            lista_vencidas.append({
                'proveedor': prov_nom,
                'articulo': r.get('articulo', ''),
                'descripcion': r.get('descripcion', ''),
                'cant_pedida': cp,
                'cant_pendiente': cpend,
                'fecha_pedido': r.get('fecha_pedido', ''),
                'fecha_entrega': fe,
                'dias_vencido': dias_venc,
                'monto_pendiente': mpend
            })

        # Antiguedad (solo pendientes/parciales)
        if est in ('PENDIENTE', 'PARCIAL'):
            if dias <= 7:
                rango = '0-7 dias'
            elif dias <= 15:
                rango = '8-15 dias'
            elif dias <= 30:
                rango = '16-30 dias'
            elif dias <= 60:
                rango = '31-60 dias'
            elif dias <= 90:
                rango = '61-90 dias'
            else:
                rango = 'Mas de 90'
            rangos_ant[rango]['lineas'] += 1
            rangos_ant[rango]['unidades'] += cpend
            rangos_ant[rango]['monto'] += mpend

        # Filtros
        if ind:
            _industrias_set.add(ind)
        if prov_nom:
            _proveedores_set.add(prov_nom)
        if est:
            _estados_set.add(est)

    # -- Armar KPI dict --
    pct_cumpl = round(float(sum_recibida) * 100.0 / float(sum_pedida), 1) if sum_pedida else 0
    kpi = {
        'total_pedidos': len(pedidos_set),
        'total_lineas': total_lineas,
        'unidades_pedidas': sum_pedida,
        'unidades_recibidas': sum_recibida,
        'unidades_pendientes': sum_pendiente,
        'pct_cumplimiento': pct_cumpl,
        'monto_total': sum_monto,
        'monto_pendiente': sum_monto_pend,
        'lineas_vencidas': lineas_vencidas
    }

    # -- Armar lista de proveedores (ordenados por monto pendiente DESC) --
    proveedores_list = []
    for pkey, pd in prov_data.items():
        ped = pd['pedido']
        rec = pd['recibido']
        pct = round(float(rec) * 100.0 / float(ped), 1) if ped else 0
        if rec >= ped:
            semaforo = 'COMPLETO'
        elif ped > 0 and float(rec) / float(ped) >= 0.75:
            semaforo = 'CASI COMPLETO'
        elif rec > 0:
            semaforo = 'PARCIAL'
        else:
            semaforo = 'SIN RECIBIR'
        proveedores_list.append({
            'proveedor': pd['proveedor'],
            'industria': pd['industria'],
            'marca': ', '.join(sorted(pd['marcas'])) if pd['marcas'] else '',
            'articulos': len(pd['arts']),
            'pedido': ped,
            'recibido': rec,
            'pendiente': pd['pendiente'],
            'pct_cumplido': pct,
            'monto_total': pd['monto_total'],
            'monto_pendiente': pd['monto_pendiente'],
            'vencidas': pd['vencidas'],
            'semaforo': semaforo
        })
    proveedores_list.sort(key=lambda x: x['monto_pendiente'], reverse=True)

    # -- Top 20 vencidas --
    lista_vencidas.sort(key=lambda x: x['dias_vencido'], reverse=True)
    vencidas = lista_vencidas[:20]

    # -- Antiguedad (solo rangos con datos, ordenados por min_dias) --
    orden_rangos = ['0-7 dias', '8-15 dias', '16-30 dias', '31-60 dias', '61-90 dias', 'Mas de 90']
    antiguedad = []
    for rango in orden_rangos:
        d = rangos_ant[rango]
        if d['lineas'] > 0:
            antiguedad.append({
                'rango': rango,
                'lineas': d['lineas'],
                'unidades': d['unidades'],
                'monto': d['monto']
            })

    _elapsed = round(_time.time() - _t0, 2)

    return dict(
        kpi=kpi,
        proveedores=proveedores_list,
        vencidas=vencidas,
        antiguedad=antiguedad,
        industrias=sorted(_industrias_set),
        proveedores_lista=sorted(_proveedores_set),
        estados=sorted(_estados_set),
        filtro_industria=industria,
        filtro_proveedor=proveedor,
        filtro_estado=estado,
        formato_moneda=_formato_moneda,
        url_safe=_url_safe,
        elapsed=_elapsed
    )

def pedidos_detalle():
    """Drill-down: detalle de artículos de un proveedor específico."""
    _requiere_acceso()

    proveedor = _uvar(request.vars.proveedor)
    if not proveedor:
        redirect(URL('reportes', 'pedidos'))

    sql = u"""
    SELECT
        CAST(p.numero AS INT) AS nota_pedido,
        CAST(p.sucursal AS INT) AS ped_sucursal,
        CAST(p.orden AS INT) AS ped_orden,
        CAST(p.renglon AS INT) AS ped_renglon,
        p.articulo, p.descripcion, p.marca, p.subrubro_desc,
        ISNULL(RTRIM(a.descripcion_5), '') AS talle,
        ISNULL(RTRIM(a.codigo_sinonimo), '') AS sinonimo,
        CAST(p.cant_pedida AS INT) AS cant_pedida,
        CAST(p.cant_recibida AS INT) AS cant_recibida,
        CAST(p.cant_pendiente AS INT) AS cant_pendiente,
        p.estado_cumplimiento,
        CAST(ROUND(p.pct_cumplido, 0) AS INT) AS pct_cumplido,
        ROUND(p.precio_unitario, 0) AS precio_unitario,
        ROUND(p.monto_pedido, 0) AS monto_pedido,
        ROUND(p.monto_pendiente, 0) AS monto_pendiente,
        p.fecha_pedido, p.fecha_entrega,
        CAST(p.dias_desde_pedido AS INT) AS dias_desde_pedido,
        p.alerta_vencimiento
    FROM pedidos_cumplimiento_cache p
    LEFT JOIN msgestion01art.dbo.articulo a ON p.articulo = a.codigo
    WHERE p.proveedor LIKE '%{}%'
    ORDER BY ISNULL(RTRIM(a.codigo_sinonimo), ''), ISNULL(RTRIM(a.descripcion_5), ''), p.numero
    """.format(proveedor.replace("'", "''"))

    detalle = _ejecutar_sql(sql)

    # Buscar cuenta del proveedor en msgestionC para remitos
    cuenta_proveedor = 0
    denominacion_proveedor = proveedor
    try:
        sql_prov = """
        SELECT TOP 1 numero AS cuenta, RTRIM(denominacion) AS denominacion
        FROM msgestionC.dbo.proveedores
        WHERE denominacion LIKE '%{}%'
        ORDER BY denominacion
        """.format(proveedor.replace("'", "''"))
        prov_rows = _ejecutar_sql(sql_prov)
        if prov_rows:
            cuenta_proveedor = int(prov_rows[0].get('cuenta', 0))
            denominacion_proveedor = prov_rows[0].get('denominacion', proveedor)
    except:
        pass

    puede_remito = _tiene_acceso('reportes.remito_crear')
    usuario_admin = _es_admin()

    return dict(
        proveedor=proveedor,
        detalle=detalle,
        formato_moneda=_formato_moneda,
        cuenta_proveedor=cuenta_proveedor,
        denominacion_proveedor=denominacion_proveedor,
        puede_remito=puede_remito,
        usuario_admin=usuario_admin
    )

# =============================================================================
# RECUPERO FINANCIERO (LIVE - moviprov2)
# =============================================================================
# Concepto: dias entre la OP (fecha_vencimiento) y el golpe efectivo bancario
# (fecha_cancelacion) en moviprov2. Positivo = diferido. Negativo = vencido.

# Subquery para marca principal del proveedor (la marca con mas articulos)
_MARCA_PPAL_SUB = """
(
    SELECT proveedor, marca AS marca_cod, marca_desc,
        ROW_NUMBER() OVER (PARTITION BY proveedor ORDER BY cant DESC) as rn
    FROM (
        SELECT a.proveedor, a.marca, RTRIM(mc.descripcion) AS marca_desc, COUNT(*) as cant
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN msgestionC.dbo.marcas mc ON a.marca = mc.codigo
        WHERE a.rubro NOT IN (14)
        GROUP BY a.proveedor, a.marca, RTRIM(mc.descripcion)
    ) x
) marca_ppal
"""

def _recupero_where(fecha_desde='', fecha_hasta='', proveedor='', marca=''):
    """WHERE base para queries de recupero financiero."""
    parts = [
        "m.codigo_movimiento = 2",
        "m.fecha_cancelacion IS NOT NULL",
        "m.importe_can_pesos > 0"
    ]
    if fecha_desde:
        parts.append("m.fecha_vencimiento >= '{}'".format(fecha_desde.replace("'", "''")))
    else:
        parts.append("m.fecha_vencimiento >= '2025-01-01'")
    if fecha_hasta:
        parts.append("m.fecha_cancelacion < '{}'".format(fecha_hasta.replace("'", "''")))
    else:
        parts.append("m.fecha_cancelacion < '2027-01-01'")
    if proveedor:
        parts.append("RTRIM(p.denominacion) LIKE '%{}%'".format(proveedor.replace("'", "''")))
    if marca:
        parts.append("marca_ppal.marca_desc LIKE '%{}%'".format(marca.replace("'", "''")))
    return " AND ".join(parts)


def recupero():
    """Dashboard de Recupero Financiero - datos LIVE de moviprov2."""
    _requiere_acceso()

    fecha_desde = request.vars.fecha_desde or ''
    fecha_hasta = request.vars.fecha_hasta or ''
    proveedor = _uvar(request.vars.proveedor)
    marca = _uvar(request.vars.marca)
    vista = request.vars.vista or 'mes'  # mes | proveedor | marca

    where = _recupero_where(fecha_desde, fecha_hasta, proveedor, marca)

    # --- KPIs GLOBALES ---
    sql_kpis = """
    SELECT
        COUNT(*) AS cant_ops,
        COUNT(DISTINCT m.numero_cuenta) AS proveedores,
        SUM(m.importe_can_pesos) AS total_importe,
        AVG(DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento)) AS dias_recupero_promedio,
        CASE WHEN SUM(m.importe_can_pesos) > 0
            THEN SUM(CAST(m.importe_can_pesos AS FLOAT) * DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento))
                 / SUM(CAST(m.importe_can_pesos AS FLOAT))
            ELSE 0
        END AS dias_recupero_ponderado,
        SUM(CASE WHEN DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento) >= 0
            THEN m.importe_can_pesos ELSE 0 END) AS importe_diferido,
        SUM(CASE WHEN DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento) < 0
            THEN m.importe_can_pesos ELSE 0 END) AS importe_vencido
    FROM msgestionC.dbo.moviprov2 m
    LEFT JOIN msgestionC.dbo.proveedores p ON m.numero_cuenta = p.numero
    LEFT JOIN {marca_sub} ON m.numero_cuenta = marca_ppal.proveedor AND marca_ppal.rn = 1
    WHERE {where}
    """.format(marca_sub=_MARCA_PPAL_SUB, where=where)

    kpis = _ejecutar_sql(sql_kpis)
    kpi = kpis[0] if kpis else {}

    # --- DATOS SEGUN VISTA ---
    datos = []
    if vista == 'mes':
        sql = """
        SELECT
            FORMAT(m.fecha_vencimiento, 'yyyy-MM') AS agrupador,
            COUNT(*) AS cant_ops,
            COUNT(DISTINCT m.numero_cuenta) AS proveedores,
            SUM(m.importe_can_pesos) AS total_importe,
            AVG(DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento)) AS dias_recupero_promedio,
            CASE WHEN SUM(m.importe_can_pesos) > 0
                THEN SUM(CAST(m.importe_can_pesos AS FLOAT) * DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento))
                     / SUM(CAST(m.importe_can_pesos AS FLOAT))
                ELSE 0
            END AS dias_recupero_ponderado,
            MIN(DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento)) AS min_dias,
            MAX(DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento)) AS max_dias
        FROM msgestionC.dbo.moviprov2 m
        LEFT JOIN msgestionC.dbo.proveedores p ON m.numero_cuenta = p.numero
        LEFT JOIN {marca_sub} ON m.numero_cuenta = marca_ppal.proveedor AND marca_ppal.rn = 1
        WHERE {where}
        GROUP BY FORMAT(m.fecha_vencimiento, 'yyyy-MM')
        ORDER BY FORMAT(m.fecha_vencimiento, 'yyyy-MM') DESC
        """.format(marca_sub=_MARCA_PPAL_SUB, where=where)
        datos = _ejecutar_sql(sql)

    elif vista == 'proveedor':
        sql = """
        SELECT TOP 50
            RTRIM(p.denominacion) AS agrupador,
            m.numero_cuenta AS cod,
            COUNT(*) AS cant_ops,
            SUM(m.importe_can_pesos) AS total_importe,
            AVG(DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento)) AS dias_recupero_promedio,
            CASE WHEN SUM(m.importe_can_pesos) > 0
                THEN SUM(CAST(m.importe_can_pesos AS FLOAT) * DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento))
                     / SUM(CAST(m.importe_can_pesos AS FLOAT))
                ELSE 0
            END AS dias_recupero_ponderado,
            MIN(DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento)) AS min_dias,
            MAX(DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento)) AS max_dias,
            ISNULL(marca_ppal.marca_desc, '?') AS marca_ppal
        FROM msgestionC.dbo.moviprov2 m
        LEFT JOIN msgestionC.dbo.proveedores p ON m.numero_cuenta = p.numero
        LEFT JOIN {marca_sub} ON m.numero_cuenta = marca_ppal.proveedor AND marca_ppal.rn = 1
        WHERE {where}
        GROUP BY m.numero_cuenta, RTRIM(p.denominacion), marca_ppal.marca_desc
        ORDER BY SUM(m.importe_can_pesos) DESC
        """.format(marca_sub=_MARCA_PPAL_SUB, where=where)
        datos = _ejecutar_sql(sql)

    elif vista == 'marca':
        sql = """
        SELECT TOP 50
            ISNULL(marca_ppal.marca_desc, 'SIN MARCA') AS agrupador,
            marca_ppal.marca_cod AS cod,
            COUNT(*) AS cant_ops,
            COUNT(DISTINCT m.numero_cuenta) AS proveedores,
            SUM(m.importe_can_pesos) AS total_importe,
            AVG(DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento)) AS dias_recupero_promedio,
            CASE WHEN SUM(m.importe_can_pesos) > 0
                THEN SUM(CAST(m.importe_can_pesos AS FLOAT) * DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento))
                     / SUM(CAST(m.importe_can_pesos AS FLOAT))
                ELSE 0
            END AS dias_recupero_ponderado,
            MIN(DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento)) AS min_dias,
            MAX(DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento)) AS max_dias
        FROM msgestionC.dbo.moviprov2 m
        LEFT JOIN msgestionC.dbo.proveedores p ON m.numero_cuenta = p.numero
        LEFT JOIN {marca_sub} ON m.numero_cuenta = marca_ppal.proveedor AND marca_ppal.rn = 1
        WHERE {where}
            AND marca_ppal.marca_desc IS NOT NULL
        GROUP BY marca_ppal.marca_cod, marca_ppal.marca_desc
        ORDER BY SUM(m.importe_can_pesos) DESC
        """.format(marca_sub=_MARCA_PPAL_SUB, where=where)
        datos = _ejecutar_sql(sql)

    import decimal as _dec
    datos_clean = []
    for r in datos:
        clean = {}
        for k, v in r.items():
            if isinstance(v, _dec.Decimal):
                # cod de proveedor/marca: mantener como entero para URLs limpias
                if k == 'cod':
                    clean[k] = int(v)
                else:
                    clean[k] = float(v)
            elif hasattr(v, 'isoformat'):
                clean[k] = v.isoformat()
            elif v is None:
                clean[k] = 0
            elif isinstance(v, unicode):
                clean[k] = v.encode('utf-8')
            else:
                clean[k] = v
        datos_clean.append(clean)

    return dict(
        kpi=kpi,
        datos=datos_clean,
        vista=vista,
        filtro_fecha_desde=fecha_desde,
        filtro_fecha_hasta=fecha_hasta,
        filtro_proveedor=proveedor,
        filtro_marca=marca,
        formato_moneda=_formato_moneda,
    )


def recupero_detalle():
    """Drill-down: OPs individuales de un proveedor."""
    _requiere_acceso()

    proveedor_cod = request.vars.cod or ''
    proveedor_nombre = request.vars.nombre or ''
    fecha_desde = request.vars.fecha_desde or '2025-01-01'

    if not proveedor_cod:
        redirect(URL('reportes', 'recupero'))

    # Tolerar cod con decimales (ej: "668.0" → 668)
    try:
        proveedor_cod_int = int(float(proveedor_cod))
    except (ValueError, TypeError):
        redirect(URL('reportes', 'recupero'))

    sql = """
    SELECT
        m.numero_cuenta AS proveedor_cod,
        RTRIM(p.denominacion) AS proveedor,
        m.numero_comprobante AS nro_op,
        m.sucursal_comprobante AS sucursal,
        m.fecha_vencimiento AS fecha_op,
        m.fecha_cancelacion AS fecha_golpe_efectivo,
        DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento) AS dias_recupero,
        m.importe_can_pesos AS importe,
        m.importe_can_pesos * DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento) AS importe_x_dias
    FROM msgestionC.dbo.moviprov2 m
    LEFT JOIN msgestionC.dbo.proveedores p ON m.numero_cuenta = p.numero
    WHERE m.codigo_movimiento = 2
        AND m.fecha_cancelacion IS NOT NULL
        AND m.importe_can_pesos > 0
        AND m.numero_cuenta = {cod}
        AND m.fecha_vencimiento >= '{desde}'
    ORDER BY m.fecha_vencimiento DESC
    """.format(
        cod=proveedor_cod_int,
        desde=fecha_desde.replace("'", "''")
    )

    ops = _ejecutar_sql(sql)

    # Stock actual de este proveedor
    sql_stock = """
    SELECT
        ISNULL(RTRIM(mc.descripcion), '?') AS marca,
        COUNT(DISTINCT s.articulo) AS articulos,
        SUM(s.stock_actual) AS stock_total
    FROM omicronvt.dbo.stock_por_codigo s
    JOIN msgestion01art.dbo.articulo a ON s.articulo = a.codigo
    LEFT JOIN msgestionC.dbo.marcas mc ON a.marca = mc.codigo
    WHERE a.proveedor = {cod}
        AND s.stock_actual > 0
        AND s.deposito != 199
    GROUP BY RTRIM(mc.descripcion)
    ORDER BY SUM(s.stock_actual) DESC
    """.format(cod=proveedor_cod_int)

    stock = _ejecutar_sql(sql_stock)

    import decimal as _dec
    ops_clean = []
    for r in ops:
        clean = {}
        for k, v in r.items():
            if isinstance(v, _dec.Decimal):
                clean[k] = float(v)
            elif hasattr(v, 'isoformat'):
                clean[k] = v.isoformat()
            elif v is None:
                clean[k] = 0
            elif isinstance(v, unicode):
                clean[k] = v.encode('utf-8')
            else:
                clean[k] = v
        ops_clean.append(clean)

    stock_clean = []
    for r in stock:
        clean = {}
        for k, v in r.items():
            if isinstance(v, _dec.Decimal):
                clean[k] = float(v)
            elif v is None:
                clean[k] = 0
            elif isinstance(v, unicode):
                clean[k] = v.encode('utf-8')
            else:
                clean[k] = v
        stock_clean.append(clean)

    return dict(
        proveedor_cod=proveedor_cod,
        proveedor_nombre=proveedor_nombre,
        ops=ops_clean,
        stock=stock_clean,
        formato_moneda=_formato_moneda,
    )


def recupero_csv():
    """Exporta datos de recupero como CSV."""
    _requiere_acceso()
    import csv, io

    fecha_desde = request.vars.fecha_desde or ''
    fecha_hasta = request.vars.fecha_hasta or ''
    proveedor = _uvar(request.vars.proveedor)
    marca = _uvar(request.vars.marca)
    tipo = request.vars.tipo or 'detalle'

    where = _recupero_where(fecha_desde, fecha_hasta, proveedor, marca)

    if tipo == 'detalle':
        sql = """
        SELECT
            m.numero_cuenta AS proveedor_cod,
            RTRIM(p.denominacion) AS proveedor,
            ISNULL(marca_ppal.marca_desc, '?') AS marca,
            m.numero_comprobante AS nro_op,
            m.sucursal_comprobante AS sucursal,
            m.fecha_vencimiento AS fecha_op,
            m.fecha_cancelacion AS fecha_golpe_efectivo,
            DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento) AS dias_recupero,
            m.importe_can_pesos AS importe
        FROM msgestionC.dbo.moviprov2 m
        LEFT JOIN msgestionC.dbo.proveedores p ON m.numero_cuenta = p.numero
        LEFT JOIN {marca_sub} ON m.numero_cuenta = marca_ppal.proveedor AND marca_ppal.rn = 1
        WHERE {where}
        ORDER BY m.fecha_vencimiento DESC
        """.format(marca_sub=_MARCA_PPAL_SUB, where=where)
    else:
        sql = """
        SELECT
            RTRIM(p.denominacion) AS proveedor,
            ISNULL(marca_ppal.marca_desc, '?') AS marca,
            COUNT(*) AS cant_ops,
            SUM(m.importe_can_pesos) AS total_pagado,
            AVG(DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento)) AS dias_prom,
            CASE WHEN SUM(m.importe_can_pesos) > 0
                THEN SUM(CAST(m.importe_can_pesos AS FLOAT) * DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento))
                     / SUM(CAST(m.importe_can_pesos AS FLOAT))
                ELSE 0
            END AS dias_ponderado,
            MIN(DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento)) AS min_dias,
            MAX(DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento)) AS max_dias
        FROM msgestionC.dbo.moviprov2 m
        LEFT JOIN msgestionC.dbo.proveedores p ON m.numero_cuenta = p.numero
        LEFT JOIN {marca_sub} ON m.numero_cuenta = marca_ppal.proveedor AND marca_ppal.rn = 1
        WHERE {where}
        GROUP BY m.numero_cuenta, RTRIM(p.denominacion), marca_ppal.marca_desc
        ORDER BY SUM(m.importe_can_pesos) DESC
        """.format(marca_sub=_MARCA_PPAL_SUB, where=where)

    data = _ejecutar_sql(sql)

    output = io.BytesIO()
    if data:
        import decimal as _dec
        fieldnames = list(data[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=b';')
        writer.writeheader()
        for row in data:
            clean_row = {}
            for k, v in row.items():
                if isinstance(v, _dec.Decimal):
                    val = float(v)
                elif hasattr(v, 'isoformat'):
                    val = v.isoformat()
                elif v is None:
                    val = 0
                else:
                    val = v
                if isinstance(val, unicode):
                    clean_row[k] = val.encode('utf-8')
                elif isinstance(val, str):
                    clean_row[k] = val
                else:
                    clean_row[k] = str(val)
            writer.writerow(clean_row)

    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=recupero_%s_%s.csv' % (
        tipo, request.now.strftime('%Y-%m-%d'))
    return b'\xef\xbb\xbf' + output.getvalue()


# =============================================================================
# RECUPERO INVERSION (tabla precalculada t_recupero_inversion)
# =============================================================================

def recupero_inversion():
    """Dashboard de Recupero de Inversion - datos de t_recupero_inversion."""
    _requiere_acceso()

    industria = request.vars.industria or ''
    anio = request.vars.anio or ''
    temporada = request.vars.temporada or ''
    estado = request.vars.estado or ''
    proveedor = _uvar(request.vars.proveedor)

    where_parts = ["1=1"]
    if industria:
        where_parts.append("industria = '{}'".format(industria.replace("'", "''")))
    if anio:
        where_parts.append("anio = {}".format(int(anio)))
    if temporada:
        where_parts.append("temporada_tipo = '{}'".format(temporada.replace("'", "''")))
    if estado:
        where_parts.append("estado = '{}'".format(estado.replace("'", "''")))
    if proveedor:
        where_parts.append("proveedor_nombre LIKE '%{}%'".format(proveedor.replace("'", "''")))
    where_clause = " AND ".join(where_parts)

    sql_kpis = """
    SELECT
        ISNULL(SUM(total_costo_compra), 0) AS inversion_total,
        ISNULL(AVG(CAST(dias_50 AS FLOAT)), 0) AS dias_prom_50,
        ISNULL(AVG(pct_vendido), 0) AS pct_vendido_prom,
        SUM(CASE WHEN estado = 'PRESION' THEN 1 ELSE 0 END) AS proveedores_presion,
        ISNULL(AVG(brecha_pago_vs_rec50), 0) AS brecha_promedio,
        ISNULL(AVG(pct_vendido_al_pago), 0) AS pct_vendido_al_pago_prom,
        COUNT(*) AS total_registros
    FROM t_recupero_inversion
    WHERE {}
    """.format(where_clause)
    kpis = _ejecutar_sql(sql_kpis)
    kpi = kpis[0] if kpis else {}

    sql_ranking = """
    SELECT
        proveedor_nombre, industria, periodo,
        total_costo_compra, dias_50, dias_75,
        plazo_pago_real_prom, pct_vendido_al_pago,
        brecha_pago_vs_rec50, estado, pct_vendido
    FROM t_recupero_inversion
    WHERE {}
    ORDER BY pct_vendido_al_pago ASC, total_costo_compra DESC
    """.format(where_clause)
    ranking = _ejecutar_sql(sql_ranking)

    sql_industria = """
    SELECT
        industria,
        COUNT(*) AS registros,
        SUM(total_costo_compra) AS inversion,
        AVG(CAST(dias_50 AS FLOAT)) AS dias_prom_50,
        AVG(CAST(dias_75 AS FLOAT)) AS dias_prom_75,
        AVG(pct_vendido) AS pct_vendido_prom,
        AVG(pct_vendido_al_pago) AS pct_vendido_al_pago_prom
    FROM t_recupero_inversion
    WHERE {}
    GROUP BY industria
    ORDER BY AVG(CAST(dias_50 AS FLOAT))
    """.format(where_clause)
    por_industria = _ejecutar_sql(sql_industria)

    industrias = _ejecutar_sql(
        "SELECT DISTINCT industria AS v FROM t_recupero_inversion ORDER BY 1")
    anios = _ejecutar_sql(
        "SELECT DISTINCT anio AS v FROM t_recupero_inversion ORDER BY 1 DESC")
    temporadas = _ejecutar_sql(
        "SELECT DISTINCT temporada_tipo AS v FROM t_recupero_inversion ORDER BY 1")
    estados_list = _ejecutar_sql(
        "SELECT DISTINCT estado AS v FROM t_recupero_inversion ORDER BY 1")

    import decimal as _dec
    def _limpiar(rows):
        out = []
        for r in rows:
            c = {}
            for k, v in r.items():
                if isinstance(v, _dec.Decimal):
                    c[k] = float(v)
                elif hasattr(v, 'isoformat'):
                    c[k] = v.isoformat()
                elif v is None:
                    c[k] = 0
                elif isinstance(v, unicode):
                    c[k] = v.encode('utf-8')
                else:
                    c[k] = v
            out.append(c)
        return out

    return dict(
        kpi=kpi,
        ranking=_limpiar(ranking),
        por_industria=_limpiar(por_industria),
        industrias=[r['v'] for r in industrias if r.get('v')],
        anios=[str(r['v']) for r in anios if r.get('v')],
        temporadas=[r['v'] for r in temporadas if r.get('v')],
        estados=[r['v'] for r in estados_list if r.get('v')],
        filtro_industria=industria,
        filtro_anio=anio,
        filtro_temporada=temporada,
        filtro_estado=estado,
        filtro_proveedor=proveedor,
        formato_moneda=_formato_moneda
    )


def recupero_inversion_detalle():
    """Drill-down: temporadas de un proveedor en t_recupero_inversion."""
    _requiere_acceso()

    proveedor = _uvar(request.vars.proveedor)
    if not proveedor:
        redirect(URL('reportes', 'recupero_inversion'))

    sql = """
    SELECT *
    FROM t_recupero_inversion
    WHERE proveedor_nombre LIKE '%{}%'
    ORDER BY anio DESC, temporada_tipo
    """.format(proveedor.replace("'", "''"))
    detalle = _ejecutar_sql(sql)

    import decimal as _dec
    detalle_clean = []
    for r in detalle:
        c = {}
        for k, v in r.items():
            if isinstance(v, _dec.Decimal):
                c[k] = float(v)
            elif hasattr(v, 'isoformat'):
                c[k] = v.isoformat()
            elif v is None:
                c[k] = 0
            elif isinstance(v, unicode):
                c[k] = v.encode('utf-8')
            else:
                c[k] = v
        detalle_clean.append(c)

    return dict(
        proveedor=proveedor,
        detalle=detalle_clean,
        formato_moneda=_formato_moneda
    )


def recupero_inversion_movimientos():
    """Drill-down nivel 2: detalle artículo × movimientos para un proveedor+periodo."""
    _requiere_acceso()
    import decimal as _dec

    proveedor = _uvar(request.vars.proveedor)
    periodo = request.vars.periodo or ''
    if not proveedor or not periodo:
        redirect(URL('reportes', 'recupero_inversion'))

    prov_safe = proveedor.replace("'", "''")
    per_safe = periodo.replace("'", "''")

    # --- Resumen de t_recupero_inversion ---
    sql_summary = """
    SELECT * FROM t_recupero_inversion
    WHERE proveedor_nombre LIKE '%{prov}%' AND periodo = '{per}'
    """.format(prov=prov_safe, per=per_safe)
    summary_rows = _ejecutar_sql(sql_summary)
    summary = summary_rows[0] if summary_rows else {}

    # --- Determinar rango de fechas del periodo ---
    # Parsear periodo: YYYY-OI, YYYY-PV, YYYY-H1, YYYY-H2
    per_parts = periodo.split('-')
    if len(per_parts) != 2:
        redirect(URL('reportes', 'recupero_inversion'))
    anio = int(per_parts[0])
    temp = per_parts[1]

    if temp == 'OI':
        fecha_desde = "'{}-03-01'".format(anio)
        fecha_hasta = "'{}-09-01'".format(anio)
    elif temp == 'PV':
        fecha_desde = "'{}-09-01'".format(anio - 1)
        fecha_hasta = "'{}-03-01'".format(anio)
    elif temp == 'H1':
        fecha_desde = "'{}-01-01'".format(anio)
        fecha_hasta = "'{}-07-01'".format(anio)
    elif temp == 'H2':
        fecha_desde = "'{}-07-01'".format(anio)
        fecha_hasta = "'{}-01-01'".format(anio + 1)
    else:
        redirect(URL('reportes', 'recupero_inversion'))

    # --- Q1: Artículos comprados (consolidados por articulo) ---
    sql_articulos = """
    SELECT
        c1.articulo,
        MAX(COALESCE(a.descripcion_1, a.descripcion_3, a.descripcion_5, '')) AS descripcion,
        MAX(a.marca) AS marca,
        SUM(CASE WHEN c2.codigo=1 THEN c1.cantidad
                 WHEN c2.codigo=3 THEN -c1.cantidad ELSE 0 END) AS qty,
        SUM(CASE WHEN c2.codigo=1 THEN c1.cantidad*c1.precio
                 WHEN c2.codigo=3 THEN -c1.cantidad*c1.precio ELSE 0 END) AS costo,
        MIN(c2.fecha_comprobante) AS fecha_primera,
        MAX(c2.fecha_comprobante) AS fecha_ultima
    FROM msgestionC.dbo.compras2 c2
    JOIN msgestionC.dbo.compras1 c1
        ON c1.empresa = c2.empresa AND c1.codigo = c2.codigo
        AND c1.letra = c2.letra AND c1.sucursal = c2.sucursal
        AND c1.numero = c2.numero AND c1.orden = c2.orden
    JOIN msgestion01art.dbo.articulo a ON c1.articulo = a.codigo
    WHERE RTRIM(c2.denominacion) LIKE '%{prov}%'
      AND c2.fecha_comprobante >= {fd}
      AND c2.fecha_comprobante < {fh}
      AND c2.codigo IN (1, 3)
      AND c1.cantidad > 0
    GROUP BY c1.articulo
    HAVING SUM(CASE WHEN c2.codigo=1 THEN c1.cantidad
                    WHEN c2.codigo=3 THEN -c1.cantidad ELSE 0 END) > 0
    ORDER BY costo DESC
    """.format(prov=prov_safe, fd=fecha_desde, fh=fecha_hasta)
    articulos_raw = _ejecutar_sql(sql_articulos)

    if not articulos_raw:
        return dict(
            proveedor=proveedor, periodo=periodo, summary={},
            articulos=[], movimientos_json='{}', formato_moneda=_formato_moneda
        )

    # Lista de codigos para las queries siguientes
    codigos = [str(r['articulo']) for r in articulos_raw]
    codigos_in = ','.join(codigos)

    # --- Q2: Stock al momento de compra (foto semanal mas cercana) ---
    # Tomamos la foto de la semana de la primera compra del periodo
    fecha_ref = min(r['fecha_primera'] for r in articulos_raw)
    fecha_ref_str = fecha_ref.strftime('%Y-%m-%d') if hasattr(fecha_ref, 'strftime') else str(fecha_ref)[:10]
    sql_stock_ini = """
    SELECT sh.codigo AS articulo, sh.stock AS stock_inicio
    FROM omicronvt.dbo.stock_historico_semanal sh
    WHERE sh.codigo IN ({cods})
      AND sh.fecha = (
          SELECT MAX(s2.fecha) FROM omicronvt.dbo.stock_historico_semanal s2
          WHERE s2.codigo = sh.codigo AND s2.fecha <= '{fref}'
      )
    """.format(cods=codigos_in, fref=fecha_ref_str)
    stock_ini_raw = _ejecutar_sql(sql_stock_ini)
    stock_ini_map = {}
    for r in stock_ini_raw:
        stock_ini_map[r['articulo']] = int(r.get('stock_inicio', 0) or 0)

    # --- Q3: Ventas acumuladas (para FIFO/hitos por articulo) ---
    sql_ventas_acum = """
    SELECT v.articulo, CAST(v.fecha AS DATE) AS fecha,
        SUM(v.cantidad) AS qty_dia,
        SUM(SUM(v.cantidad)) OVER (PARTITION BY v.articulo ORDER BY CAST(v.fecha AS DATE)
            ROWS UNBOUNDED PRECEDING) AS acum
    FROM msgestionC.dbo.ventas1 v
    WHERE v.articulo IN ({cods})
      AND v.fecha >= {fd}
      AND v.cantidad > 0
      AND v.codigo NOT IN (7, 36)
    GROUP BY v.articulo, CAST(v.fecha AS DATE)
    ORDER BY v.articulo, CAST(v.fecha AS DATE)
    """.format(cods=codigos_in, fd=fecha_desde)
    ventas_acum_raw = _ejecutar_sql(sql_ventas_acum)

    # Organizar ventas acumuladas por articulo
    ventas_por_art = {}
    for r in ventas_acum_raw:
        cod = r['articulo']
        if cod not in ventas_por_art:
            ventas_por_art[cod] = []
        ventas_por_art[cod].append({
            'fecha': r['fecha'],
            'acum': int(r.get('acum', 0) or 0)
        })

    # --- Q4: Movimientos mensuales (compras y ventas) ---
    import datetime as _dt
    hoy_str = _dt.date.today().strftime('%Y-%m-%d')
    sql_mov = """
    SELECT
        COALESCE(x.articulo, y.articulo) AS articulo,
        COALESCE(x.mes, y.mes) AS mes,
        ISNULL(x.qty_comprada, 0) AS qty_comprada,
        ISNULL(x.costo_compra, 0) AS costo_compra,
        ISNULL(y.qty_vendida, 0) AS qty_vendida
    FROM (
        SELECT c1.articulo,
            DATEFROMPARTS(YEAR(c2.fecha_comprobante), MONTH(c2.fecha_comprobante), 1) AS mes,
            SUM(CASE WHEN c2.codigo=1 THEN c1.cantidad ELSE -c1.cantidad END) AS qty_comprada,
            SUM(CASE WHEN c2.codigo=1 THEN c1.cantidad*c1.precio ELSE -c1.cantidad*c1.precio END) AS costo_compra
        FROM msgestionC.dbo.compras2 c2
        JOIN msgestionC.dbo.compras1 c1
            ON c1.empresa = c2.empresa AND c1.codigo = c2.codigo
            AND c1.letra = c2.letra AND c1.sucursal = c2.sucursal
            AND c1.numero = c2.numero AND c1.orden = c2.orden
        WHERE RTRIM(c2.denominacion) LIKE '%{prov}%'
          AND c2.fecha_comprobante >= {fd} AND c2.fecha_comprobante < '{hoy}'
          AND c2.codigo IN (1, 3) AND c1.cantidad > 0
          AND c1.articulo IN ({cods})
        GROUP BY c1.articulo, DATEFROMPARTS(YEAR(c2.fecha_comprobante), MONTH(c2.fecha_comprobante), 1)
    ) x
    FULL OUTER JOIN (
        SELECT v.articulo,
            DATEFROMPARTS(YEAR(v.fecha), MONTH(v.fecha), 1) AS mes,
            SUM(v.cantidad) AS qty_vendida
        FROM msgestionC.dbo.ventas1 v
        WHERE v.articulo IN ({cods})
          AND v.fecha >= {fd} AND v.fecha < '{hoy}'
          AND v.cantidad > 0 AND v.codigo NOT IN (7, 36)
        GROUP BY v.articulo, DATEFROMPARTS(YEAR(v.fecha), MONTH(v.fecha), 1)
    ) y ON x.articulo = y.articulo AND x.mes = y.mes
    ORDER BY COALESCE(x.articulo, y.articulo), COALESCE(x.mes, y.mes)
    """.format(prov=prov_safe, fd=fecha_desde, hoy=hoy_str, cods=codigos_in)
    mov_raw = _ejecutar_sql(sql_mov)

    # --- Q5: Stock actual ---
    sql_stock_act = """
    SELECT articulo, SUM(stock_actual) AS stock_actual
    FROM msgestionC.dbo.stock
    WHERE articulo IN ({cods})
    GROUP BY articulo
    """.format(cods=codigos_in)
    stock_act_raw = _ejecutar_sql(sql_stock_act)
    stock_act_map = {}
    for r in stock_act_raw:
        stock_act_map[r['articulo']] = int(r.get('stock_actual', 0) or 0)

    # --- Procesar articulos: calcular hitos FIFO ---
    articulos = []
    for r in articulos_raw:
        cod = r['articulo']
        qty = int(r.get('qty', 0) or 0)
        costo = float(r.get('costo', 0) or 0)
        sp = stock_ini_map.get(cod, 0)
        precio_prom = round(costo / qty, 0) if qty > 0 else 0

        # Calcular hitos desde ventas acumuladas
        d50 = d75 = d100 = None
        va_list = ventas_por_art.get(cod, [])
        total_vendido = va_list[-1]['acum'] if va_list else 0
        pct_vendido = 0
        if qty > 0 and total_vendido > sp:
            pct_vendido = min(100.0, round(100.0 * (total_vendido - sp) / qty, 1))

        fecha_compra = r.get('fecha_primera')
        for va in va_list:
            if d50 is None and va['acum'] >= sp + 0.50 * qty:
                d50 = (va['fecha'] - fecha_compra).days if hasattr(va['fecha'], 'days') or hasattr(fecha_compra, 'days') else None
                try:
                    d50 = (va['fecha'] - fecha_compra).days
                except:
                    d50 = None
            if d75 is None and va['acum'] >= sp + 0.75 * qty:
                try:
                    d75 = (va['fecha'] - fecha_compra).days
                except:
                    d75 = None
            if d100 is None and va['acum'] >= sp + 1.00 * qty:
                try:
                    d100 = (va['fecha'] - fecha_compra).days
                except:
                    d100 = None

        articulos.append({
            'codigo': cod,
            'descripcion': r.get('descripcion', '') if not isinstance(r.get('descripcion', ''), unicode) else r.get('descripcion', '').encode('utf-8'),
            'marca': r.get('marca', '') if not isinstance(r.get('marca', ''), unicode) else r.get('marca', '').encode('utf-8'),
            'qty': qty,
            'costo': costo,
            'precio_prom': precio_prom,
            'stock_inicio': sp,
            'd50': d50,
            'd75': d75,
            'd100': d100,
            'pct_vendido': pct_vendido,
            'stock_actual': stock_act_map.get(cod, 0),
        })

    # --- Organizar movimientos mensuales por articulo ---
    # Reconstruir stock mes a mes hacia atras desde stock actual
    mov_by_art = {}
    for r in mov_raw:
        cod = r.get('articulo', 0)
        if not cod:
            continue
        cod_str = str(int(cod))  # JSON keys deben ser string
        if cod_str not in mov_by_art:
            mov_by_art[cod_str] = []
        mov_by_art[cod_str].append({
            'mes': r['mes'].isoformat()[:7] if hasattr(r['mes'], 'isoformat') else str(r['mes'])[:7],
            'compras': int(r.get('qty_comprada', 0) or 0),
            'costo_compra': float(r.get('costo_compra', 0) or 0),
            'ventas': int(r.get('qty_vendida', 0) or 0),
        })

    # Reconstruir stock hacia atras
    for cod_str in mov_by_art:
        movs = sorted(mov_by_art[cod_str], key=lambda x: x['mes'])
        cod_int = int(cod_str)
        current_stk = stock_act_map.get(cod_int, 0)
        # Ir de atras hacia adelante para calcular stock_fin de cada mes
        for i in range(len(movs) - 1, -1, -1):
            movs[i]['stock_fin'] = current_stk
            current_stk = current_stk + movs[i]['ventas'] - movs[i]['compras']
            movs[i]['stock_inicio'] = current_stk

    # Serializar movimientos a JSON para el JS del template
    import json as _json
    mov_json = _json.dumps(mov_by_art)

    # Limpiar summary
    summary_clean = {}
    for k, v in summary.items():
        if isinstance(v, _dec.Decimal):
            summary_clean[k] = float(v)
        elif hasattr(v, 'isoformat'):
            summary_clean[k] = v.isoformat()
        elif v is None:
            summary_clean[k] = 0
        elif isinstance(v, unicode):
            summary_clean[k] = v.encode('utf-8')
        else:
            summary_clean[k] = v

    return dict(
        proveedor=proveedor,
        periodo=periodo,
        summary=summary_clean,
        articulos=articulos,
        movimientos_json=mov_json,
        formato_moneda=_formato_moneda
    )


# =============================================================================
# NEGOCIACION DE PLAZOS (CFO + Comprador)
# =============================================================================

def negociacion_plazos():
    """Reporte para CFO y comprador: negociacion de plazos.
    Combina pagos live (moviprov2) + stock actual + historico (t_recupero_inversion).
    Vistas: proveedor | marca | rubro | subrubro | familia | industria
    """
    _requiere_acceso()

    vista = request.vars.vista or 'proveedor'
    fecha_desde = request.vars.fecha_desde or '2025-01-01'
    fecha_hasta = request.vars.fecha_hasta or ''
    prov_filtro = _uvar(request.vars.proveedor)
    marca_filtro = _uvar(request.vars.marca)
    industria_filtro = request.vars.industria or ''
    rubro_filtro = request.vars.rubro or ''

    # --- WHERE moviprov2 ---
    wm = [
        "m.codigo_movimiento = 2",
        "m.fecha_cancelacion IS NOT NULL",
        "m.importe_can_pesos > 0",
        "m.fecha_vencimiento >= '{}'".format(fecha_desde.replace("'", "''"))
    ]
    if fecha_hasta:
        wm.append("m.fecha_cancelacion < '{}'".format(fecha_hasta.replace("'", "''")))
    if prov_filtro:
        wm.append("RTRIM(p.denominacion) LIKE '%{}%'".format(prov_filtro.replace("'", "''")))
    wm_str = " AND ".join(wm)

    # --- WHERE stock ---
    ws = ["s.stock_actual > 0", "s.deposito != 199"]
    if prov_filtro:
        ws.append("RTRIM(prov.denominacion) LIKE '%{}%'".format(prov_filtro.replace("'", "''")))
    if marca_filtro:
        ws.append("RTRIM(mc.descripcion) LIKE '%{}%'".format(marca_filtro.replace("'", "''")))
    if rubro_filtro:
        ws.append("RTRIM(ru.descripcion) LIKE '%{}%'".format(rubro_filtro.replace("'", "''")))
    ws_str = " AND ".join(ws)

    # ===== KPIs GLOBALES =====
    sql_kpi = """
    SELECT
        COUNT(*) AS cant_ops,
        COUNT(DISTINCT m.numero_cuenta) AS proveedores,
        SUM(m.importe_can_pesos) AS total_pagado,
        CASE WHEN SUM(m.importe_can_pesos) > 0
            THEN ROUND(SUM(CAST(m.importe_can_pesos AS FLOAT)
                 * DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento))
                 / SUM(CAST(m.importe_can_pesos AS FLOAT)), 1)
            ELSE 0 END AS dias_ponderado_global,
        SUM(CASE WHEN DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento) >= 0
            THEN m.importe_can_pesos ELSE 0 END) AS imp_diferido,
        SUM(CASE WHEN DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento) < 0
            THEN m.importe_can_pesos ELSE 0 END) AS imp_vencido
    FROM msgestionC.dbo.moviprov2 m
    LEFT JOIN msgestionC.dbo.proveedores p ON m.numero_cuenta = p.numero
    WHERE {w}
    """.format(w=wm_str)
    kpis = _ejecutar_sql(sql_kpi)
    kpi = kpis[0] if kpis else {}

    sql_kpi_stk = """
    SELECT
        COUNT(DISTINCT a.codigo) AS articulos_stock,
        SUM(s.stock_actual) AS stock_unidades,
        SUM(CAST(s.stock_actual AS FLOAT) * ISNULL(a.precio_costo, 0)) AS stock_valorizado
    FROM omicronvt.dbo.stock_por_codigo s
    JOIN msgestion01art.dbo.articulo a ON s.articulo = a.codigo
    LEFT JOIN msgestionC.dbo.proveedores prov ON a.proveedor = prov.numero
    LEFT JOIN msgestionC.dbo.marcas mc ON a.marca = mc.codigo
    LEFT JOIN msgestion01art.dbo.rubros ru ON a.rubro = ru.codigo
    WHERE {w}
    """.format(w=ws_str)
    kpi_stk = _ejecutar_sql(sql_kpi_stk)
    kpi_stk = kpi_stk[0] if kpi_stk else {}

    import decimal as _dec

    def _limpiar_row(r):
        c = {}
        for k, v in r.items():
            if isinstance(v, _dec.Decimal):
                c[k] = float(v)
            elif hasattr(v, 'isoformat'):
                c[k] = v.isoformat()
            elif v is None:
                c[k] = 0
            elif isinstance(v, unicode):
                c[k] = v.encode('utf-8')
            else:
                c[k] = v
        return c

    # ===== DATOS SEGUN VISTA =====
    datos = []

    if vista == 'proveedor':
        sql_rec = """
        SELECT TOP 100
            RTRIM(p.denominacion) AS agrupador,
            m.numero_cuenta AS cod,
            COUNT(*) AS cant_ops,
            SUM(m.importe_can_pesos) AS total_pagado,
            CASE WHEN SUM(m.importe_can_pesos) > 0
                THEN ROUND(SUM(CAST(m.importe_can_pesos AS FLOAT)
                     * DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento))
                     / SUM(CAST(m.importe_can_pesos AS FLOAT)), 1)
                ELSE 0 END AS dias_recupero,
            SUM(CASE WHEN DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento) >= 0
                THEN m.importe_can_pesos ELSE 0 END) AS imp_diferido,
            SUM(CASE WHEN DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento) < 0
                THEN m.importe_can_pesos ELSE 0 END) AS imp_vencido,
            ISNULL(marca_ppal.marca_desc, '?') AS marca_ppal
        FROM msgestionC.dbo.moviprov2 m
        LEFT JOIN msgestionC.dbo.proveedores p ON m.numero_cuenta = p.numero
        LEFT JOIN {ms} ON m.numero_cuenta = marca_ppal.proveedor AND marca_ppal.rn = 1
        WHERE {w}
        GROUP BY m.numero_cuenta, RTRIM(p.denominacion), marca_ppal.marca_desc
        ORDER BY SUM(m.importe_can_pesos) DESC
        """.format(ms=_MARCA_PPAL_SUB, w=wm_str)
        raw_rec = _ejecutar_sql(sql_rec)

        # Stock por proveedor
        sql_stk = """
        SELECT
            a.proveedor AS cod,
            COUNT(DISTINCT a.codigo) AS articulos_stock,
            SUM(s.stock_actual) AS stock_unidades,
            SUM(CAST(s.stock_actual AS FLOAT) * ISNULL(a.precio_costo, 0)) AS stock_valorizado
        FROM omicronvt.dbo.stock_por_codigo s
        JOIN msgestion01art.dbo.articulo a ON s.articulo = a.codigo
        WHERE s.stock_actual > 0 AND s.deposito != 199
        GROUP BY a.proveedor
        """
        stk_rows = _ejecutar_sql(sql_stk)
        stk_map = {}
        for sr in stk_rows:
            stk_map[sr['cod']] = sr

        # Historico t_recupero_inversion
        tri_map = {}
        try:
            sql_tri = """
            SELECT
                proveedor_nombre,
                AVG(CAST(dias_50 AS FLOAT)) AS dias_50,
                AVG(CAST(dias_75 AS FLOAT)) AS dias_75,
                AVG(pct_vendido) AS pct_vendido,
                AVG(pct_vendido_al_pago) AS pct_vendido_al_pago,
                AVG(brecha_pago_vs_rec50) AS brecha,
                AVG(plazo_pago_real_prom) AS plazo_pago
            FROM t_recupero_inversion
            GROUP BY proveedor_nombre
            """
            tri_rows = _ejecutar_sql(sql_tri)
            for tr in tri_rows:
                nm = tr.get('proveedor_nombre', '')
                if isinstance(nm, unicode):
                    nm = nm.encode('utf-8')
                if nm:
                    tri_map[nm.strip()] = tr
        except:
            pass

        # Merge
        for r in raw_rec:
            row = _limpiar_row(r)
            cod = r.get('cod', 0)
            st = stk_map.get(cod, {})
            row['articulos_stock'] = int(st.get('articulos_stock', 0) or 0)
            row['stock_unidades'] = int(st.get('stock_unidades', 0) or 0)
            row['stock_valorizado'] = float(st.get('stock_valorizado', 0) or 0)

            agr = row.get('agrupador', '')
            if isinstance(agr, bytes):
                agr = agr.strip()
            else:
                agr = str(agr).strip()
            tri = tri_map.get(agr, {})
            row['dias_50'] = round(float(tri.get('dias_50', 0) or 0), 0)
            row['dias_75'] = round(float(tri.get('dias_75', 0) or 0), 0)
            row['pct_vendido'] = round(float(tri.get('pct_vendido', 0) or 0), 1)
            row['pct_vendido_al_pago'] = round(float(tri.get('pct_vendido_al_pago', 0) or 0), 1)
            row['brecha'] = round(float(tri.get('brecha', 0) or 0), 0)
            row['plazo_pago'] = round(float(tri.get('plazo_pago', 0) or 0), 0)

            dias_rec = float(row.get('dias_recupero', 0))
            d50 = row['dias_50']
            if d50 > 0:
                row['plazo_sugerido'] = int(max(d50, dias_rec) + 7)
            elif dias_rec != 0:
                row['plazo_sugerido'] = int(abs(dias_rec) + 15)
            else:
                row['plazo_sugerido'] = 0

            pva = row['pct_vendido_al_pago']
            if pva >= 75:
                row['semaforo'] = 'CALZADO'
            elif pva >= 50:
                row['semaforo'] = 'AJUSTADO'
            elif dias_rec < 0:
                row['semaforo'] = 'VENCIDO'
            elif row['brecha'] > 15:
                row['semaforo'] = 'PRESION'
            elif row['total_pagado'] > 0:
                row['semaforo'] = 'OK'
            else:
                row['semaforo'] = 'SIN DATOS'

            datos.append(row)

    elif vista == 'marca':
        sql = """
        SELECT TOP 80
            ISNULL(RTRIM(mc.descripcion), 'SIN MARCA') AS agrupador,
            a.marca AS cod,
            COUNT(DISTINCT a.proveedor) AS cant_proveedores,
            COUNT(DISTINCT a.codigo) AS cant_articulos,
            SUM(s.stock_actual) AS stock_unidades,
            SUM(CAST(s.stock_actual AS FLOAT) * ISNULL(a.precio_costo, 0)) AS stock_valorizado
        FROM omicronvt.dbo.stock_por_codigo s
        JOIN msgestion01art.dbo.articulo a ON s.articulo = a.codigo
        LEFT JOIN msgestionC.dbo.marcas mc ON a.marca = mc.codigo
        LEFT JOIN msgestionC.dbo.proveedores prov ON a.proveedor = prov.numero
        LEFT JOIN msgestion01art.dbo.rubros ru ON a.rubro = ru.codigo
        WHERE {w}
        GROUP BY a.marca, RTRIM(mc.descripcion)
        ORDER BY SUM(CAST(s.stock_actual AS FLOAT) * ISNULL(a.precio_costo, 0)) DESC
        """.format(w=ws_str)
        datos = [_limpiar_row(r) for r in _ejecutar_sql(sql)]

    elif vista == 'rubro':
        sql = """
        SELECT
            ISNULL(RTRIM(ru.descripcion), 'SIN RUBRO') AS agrupador,
            a.rubro AS cod,
            COUNT(DISTINCT a.proveedor) AS cant_proveedores,
            COUNT(DISTINCT a.marca) AS cant_marcas,
            COUNT(DISTINCT a.codigo) AS cant_articulos,
            SUM(s.stock_actual) AS stock_unidades,
            SUM(CAST(s.stock_actual AS FLOAT) * ISNULL(a.precio_costo, 0)) AS stock_valorizado
        FROM omicronvt.dbo.stock_por_codigo s
        JOIN msgestion01art.dbo.articulo a ON s.articulo = a.codigo
        LEFT JOIN msgestion01art.dbo.rubros ru ON a.rubro = ru.codigo
        LEFT JOIN msgestionC.dbo.proveedores prov ON a.proveedor = prov.numero
        LEFT JOIN msgestionC.dbo.marcas mc ON a.marca = mc.codigo
        WHERE {w}
        GROUP BY a.rubro, RTRIM(ru.descripcion)
        ORDER BY SUM(CAST(s.stock_actual AS FLOAT) * ISNULL(a.precio_costo, 0)) DESC
        """.format(w=ws_str)
        datos = [_limpiar_row(r) for r in _ejecutar_sql(sql)]

    elif vista == 'subrubro':
        sql = """
        SELECT TOP 80
            ISNULL(RTRIM(sr.descripcion), 'SIN SUBRUBRO') AS agrupador,
            a.subrubro AS cod,
            ISNULL(RTRIM(ru.descripcion), '?') AS rubro_desc,
            COUNT(DISTINCT a.proveedor) AS cant_proveedores,
            COUNT(DISTINCT a.codigo) AS cant_articulos,
            SUM(s.stock_actual) AS stock_unidades,
            SUM(CAST(s.stock_actual AS FLOAT) * ISNULL(a.precio_costo, 0)) AS stock_valorizado
        FROM omicronvt.dbo.stock_por_codigo s
        JOIN msgestion01art.dbo.articulo a ON s.articulo = a.codigo
        LEFT JOIN msgestion01art.dbo.subrubro sr ON a.subrubro = sr.codigo
        LEFT JOIN msgestion01art.dbo.rubros ru ON a.rubro = ru.codigo
        LEFT JOIN msgestionC.dbo.proveedores prov ON a.proveedor = prov.numero
        LEFT JOIN msgestionC.dbo.marcas mc ON a.marca = mc.codigo
        WHERE {w}
        GROUP BY a.subrubro, RTRIM(sr.descripcion), a.rubro, RTRIM(ru.descripcion)
        ORDER BY SUM(CAST(s.stock_actual AS FLOAT) * ISNULL(a.precio_costo, 0)) DESC
        """.format(w=ws_str)
        datos = [_limpiar_row(r) for r in _ejecutar_sql(sql)]

    elif vista == 'familia':
        sql = """
        SELECT TOP 100
            LEFT(a.codigo, LEN(a.codigo) - 4) AS agrupador,
            LEFT(a.codigo, LEN(a.codigo) - 4) AS cod,
            MIN(RTRIM(a.descripcion)) AS descripcion_ej,
            MIN(RTRIM(mc.descripcion)) AS marca_desc,
            MIN(RTRIM(ru.descripcion)) AS rubro_desc,
            MIN(RTRIM(sr.descripcion)) AS subrubro_desc,
            COUNT(DISTINCT a.codigo) AS talles,
            COUNT(DISTINCT a.proveedor) AS cant_proveedores,
            SUM(s.stock_actual) AS stock_unidades,
            SUM(CAST(s.stock_actual AS FLOAT) * ISNULL(a.precio_costo, 0)) AS stock_valorizado
        FROM omicronvt.dbo.stock_por_codigo s
        JOIN msgestion01art.dbo.articulo a ON s.articulo = a.codigo
        LEFT JOIN msgestionC.dbo.marcas mc ON a.marca = mc.codigo
        LEFT JOIN msgestion01art.dbo.rubros ru ON a.rubro = ru.codigo
        LEFT JOIN msgestion01art.dbo.subrubro sr ON a.subrubro = sr.codigo
        LEFT JOIN msgestionC.dbo.proveedores prov ON a.proveedor = prov.numero
        WHERE {w}
        GROUP BY LEFT(a.codigo, LEN(a.codigo) - 4)
        ORDER BY SUM(CAST(s.stock_actual AS FLOAT) * ISNULL(a.precio_costo, 0)) DESC
        """.format(w=ws_str)
        datos = [_limpiar_row(r) for r in _ejecutar_sql(sql)]

    elif vista == 'industria':
        wi = ["1=1"]
        if industria_filtro:
            wi.append("industria = '{}'".format(industria_filtro.replace("'", "''")))
        if prov_filtro:
            wi.append("proveedor_nombre LIKE '%{}%'".format(prov_filtro.replace("'", "''")))
        wi_str = " AND ".join(wi)

        sql = """
        SELECT
            industria AS agrupador, industria AS cod,
            COUNT(*) AS registros,
            SUM(total_costo_compra) AS inversion,
            AVG(CAST(dias_50 AS FLOAT)) AS dias_50,
            AVG(CAST(dias_75 AS FLOAT)) AS dias_75,
            AVG(pct_vendido) AS pct_vendido,
            AVG(pct_vendido_al_pago) AS pct_vendido_al_pago,
            AVG(brecha_pago_vs_rec50) AS brecha,
            AVG(plazo_pago_real_prom) AS plazo_pago,
            SUM(CASE WHEN estado = 'PRESION' THEN 1 ELSE 0 END) AS presion,
            SUM(CASE WHEN estado = 'OK' THEN 1 ELSE 0 END) AS ok
        FROM t_recupero_inversion
        WHERE {w}
        GROUP BY industria
        ORDER BY AVG(CAST(dias_50 AS FLOAT))
        """.format(w=wi_str)
        datos = [_limpiar_row(r) for r in _ejecutar_sql(sql)]

    # Opciones para filtros
    try:
        industrias = [r['v'] for r in _ejecutar_sql(
            "SELECT DISTINCT industria AS v FROM t_recupero_inversion ORDER BY 1") if r.get('v')]
    except:
        industrias = []
    try:
        rubros = [r['v'] for r in _ejecutar_sql(
            "SELECT DISTINCT RTRIM(descripcion) AS v FROM msgestion01art.dbo.rubros ORDER BY 1") if r.get('v')]
    except:
        rubros = []

    return dict(
        kpi=kpi,
        kpi_stk=kpi_stk,
        datos=datos,
        vista=vista,
        filtro_fecha_desde=fecha_desde,
        filtro_fecha_hasta=fecha_hasta or '',
        filtro_proveedor=prov_filtro,
        filtro_marca=marca_filtro,
        filtro_industria=industria_filtro,
        filtro_rubro=rubro_filtro,
        industrias=industrias,
        rubros=rubros,
        formato_moneda=_formato_moneda,
    )


def negociacion_csv():
    """Exporta datos de negociacion como CSV."""
    _requiere_acceso()
    import csv, io

    vista = request.vars.vista or 'proveedor'
    fecha_desde = request.vars.fecha_desde or '2025-01-01'
    fecha_hasta = request.vars.fecha_hasta or ''
    prov_filtro = _uvar(request.vars.proveedor)
    marca_filtro = _uvar(request.vars.marca)

    wm = [
        "m.codigo_movimiento = 2",
        "m.fecha_cancelacion IS NOT NULL",
        "m.importe_can_pesos > 0",
        "m.fecha_vencimiento >= '{}'".format(fecha_desde.replace("'", "''"))
    ]
    if fecha_hasta:
        wm.append("m.fecha_cancelacion < '{}'".format(fecha_hasta.replace("'", "''")))
    if prov_filtro:
        wm.append("RTRIM(p.denominacion) LIKE '%{}%'".format(prov_filtro.replace("'", "''")))
    wm_str = " AND ".join(wm)

    sql = """
    SELECT
        RTRIM(p.denominacion) AS proveedor,
        m.numero_cuenta AS cod_proveedor,
        ISNULL(marca_ppal.marca_desc, '?') AS marca_principal,
        COUNT(*) AS cant_ops,
        SUM(m.importe_can_pesos) AS total_pagado,
        CASE WHEN SUM(m.importe_can_pesos) > 0
            THEN ROUND(SUM(CAST(m.importe_can_pesos AS FLOAT)
                 * DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento))
                 / SUM(CAST(m.importe_can_pesos AS FLOAT)), 1)
            ELSE 0 END AS dias_recupero_ponderado,
        SUM(CASE WHEN DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento) >= 0
            THEN m.importe_can_pesos ELSE 0 END) AS imp_diferido,
        SUM(CASE WHEN DATEDIFF(DAY, m.fecha_cancelacion, m.fecha_vencimiento) < 0
            THEN m.importe_can_pesos ELSE 0 END) AS imp_vencido
    FROM msgestionC.dbo.moviprov2 m
    LEFT JOIN msgestionC.dbo.proveedores p ON m.numero_cuenta = p.numero
    LEFT JOIN {ms} ON m.numero_cuenta = marca_ppal.proveedor AND marca_ppal.rn = 1
    WHERE {w}
    GROUP BY m.numero_cuenta, RTRIM(p.denominacion), marca_ppal.marca_desc
    ORDER BY SUM(m.importe_can_pesos) DESC
    """.format(ms=_MARCA_PPAL_SUB, w=wm_str)

    data = _ejecutar_sql(sql)
    import decimal as _dec
    output = io.BytesIO()
    if data:
        fieldnames = list(data[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=b';')
        writer.writeheader()
        for row in data:
            cr = {}
            for k, v in row.items():
                if isinstance(v, _dec.Decimal):
                    val = float(v)
                elif hasattr(v, 'isoformat'):
                    val = v.isoformat()
                elif v is None:
                    val = 0
                else:
                    val = v
                if isinstance(val, unicode):
                    cr[k] = val.encode('utf-8')
                elif isinstance(val, str):
                    cr[k] = val
                else:
                    cr[k] = str(val)
            writer.writerow(cr)

    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename=negociacion_%s_%s.csv' % (
        vista, request.now.strftime('%Y-%m-%d'))
    return b'\xef\xbb\xbf' + output.getvalue()


# =============================================================================
# REMITOS DE COMPRA (Ingreso cod=7, Devolucion cod=36)
# =============================================================================

def _ejecutar_sql_gestionC(sql, as_dict=True):
    """Ejecuta SQL contra msgestionC via cross-database desde omicronvt."""
    db_omicronvt.executesql("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    return db_omicronvt.executesql(sql, as_dict=as_dict)


# =============================================================================
# APROBACIÓN PRESUPUESTARIA DE PEDIDOS
# =============================================================================

def _aprobacion_pedidos(numeros=None):
    """Devuelve dict {numero: {estado, monto_aprobado, usuario_aprobacion, notas, fecha_resolucion}}
    para una lista de numeros de pedido (o todos si numeros=None)."""
    if numeros:
        lista = ','.join(str(int(n)) for n in numeros)
        where = 'WHERE numero IN ({})'.format(lista)
    else:
        where = ''
    sql = "SELECT numero, estado, monto_aprobado, usuario_aprobacion, notas, fecha_resolucion FROM omicronvt.dbo.pedido_aprobacion {}".format(where)
    rows = db_omicronvt.executesql(sql, as_dict=True)
    return {int(r['numero']): r for r in rows}


def _registrar_aprobacion(numero):
    """Inserta registro PENDIENTE si el pedido no tiene aprobación aún."""
    db_omicronvt.executesql("""
    IF NOT EXISTS (SELECT 1 FROM omicronvt.dbo.pedido_aprobacion WHERE numero={n})
        INSERT INTO omicronvt.dbo.pedido_aprobacion (numero, estado, fecha_solicitud)
        VALUES ({n}, 'PENDIENTE', GETDATE())
    """.format(n=int(numero)))
    db_omicronvt.commit()


def pedido_aprobar():
    """POST: Aprueba, rechaza o deja pendiente un pedido.
    Params JSON: numero, accion ('APROBADO'|'RECHAZADO'|'PENDIENTE'),
                 monto_aprobado (opcional), notas (opcional).
    Requiere rol finanzas o admin.
    """
    _requiere_acceso()
    import json

    if not (_es_admin() or _tiene_acceso('reportes.pedido_aprobar')):
        return json.dumps(dict(ok=False, msg='Sin permisos de finanzas'))

    try:
        body = json.loads(request.body.read())
    except:
        return json.dumps(dict(ok=False, msg='JSON invalido'))

    numero = int(body.get('numero', 0))
    accion = body.get('accion', '').upper()
    monto  = body.get('monto_aprobado', None)
    notas  = (body.get('notas', '') or '')[:2000]

    if not numero:
        return json.dumps(dict(ok=False, msg='Falta numero de pedido'))
    if accion not in ('APROBADO', 'RECHAZADO', 'PENDIENTE'):
        return json.dumps(dict(ok=False, msg='Accion invalida'))

    usuario = auth.user.email if auth.user and auth.user.email else 'WEB'
    monto_sql = str(round(float(monto), 2)) if monto is not None else 'NULL'
    fecha_res = 'GETDATE()' if accion != 'PENDIENTE' else 'NULL'

    db_omicronvt.executesql("""
    MERGE omicronvt.dbo.pedido_aprobacion AS t
    USING (SELECT {n} AS numero) AS s ON t.numero = s.numero
    WHEN MATCHED THEN UPDATE SET
        estado              = '{est}',
        monto_aprobado      = {monto},
        fecha_resolucion    = {fres},
        usuario_aprobacion  = '{usr}',
        notas               = '{notas}'
    WHEN NOT MATCHED THEN INSERT (numero, estado, monto_aprobado, fecha_solicitud, fecha_resolucion, usuario_aprobacion, notas)
        VALUES ({n}, '{est}', {monto}, GETDATE(), {fres}, '{usr}', '{notas}');
    """.format(
        n=numero, est=accion, monto=monto_sql, fres=fecha_res,
        usr=usuario.replace("'", "''"),
        notas=notas.replace("'", "''")
    ))
    db_omicronvt.commit()

    return json.dumps(dict(ok=True, estado=accion, numero=numero))


def pedidos_aprobacion():
    """Vista de finanzas: lista de pedidos COWORK con estado aprobación.
    Permite aprobar/rechazar desde la UI."""
    _requiere_acceso()
    import json

    # Todos los pedidos COWORK vigentes con su aprobación
    sql = """
    SELECT
        p2.numero, p2.sucursal, p2.cuenta, p2.denominacion AS proveedor,
        p2.fecha_comprobante,
        COUNT(p1.orden) AS renglones,
        SUM(p1.cantidad) AS pares,
        SUM(p1.cantidad * p1.precio) AS monto_total,
        pa.estado AS estado_aprob,
        pa.monto_aprobado,
        pa.usuario_aprobacion,
        pa.notas,
        pa.fecha_resolucion
    FROM msgestion01.dbo.pedico2 p2
    LEFT JOIN msgestion01.dbo.pedico1 p1 ON p1.numero = p2.numero
    LEFT JOIN omicronvt.dbo.pedido_aprobacion pa ON pa.numero = p2.numero
    WHERE p2.usuario = 'COWORK' AND p2.estado = 'V'
    GROUP BY p2.numero, p2.sucursal, p2.cuenta, p2.denominacion,
             p2.fecha_comprobante, pa.estado, pa.monto_aprobado,
             pa.usuario_aprobacion, pa.notas, pa.fecha_resolucion
    ORDER BY pa.estado ASC, p2.fecha_comprobante DESC
    """
    pedidos_raw = db_omicronvt.executesql(sql, as_dict=True)

    pedidos = []
    for r in pedidos_raw:
        monto = float(r.get('monto_total') or 0)
        monto_ap = float(r.get('monto_aprobado') or 0) if r.get('monto_aprobado') else None
        est = r.get('estado_aprob') or 'PENDIENTE'
        pedidos.append({
            'numero':       int(r['numero']),
            'sucursal':     int(r.get('sucursal') or 0),
            'proveedor':    r.get('proveedor', ''),
            'fecha':        r.get('fecha_comprobante', ''),
            'renglones':    int(r.get('renglones') or 0),
            'pares':        int(r.get('pares') or 0),
            'monto_total':  monto,
            'estado_aprob': est,
            'monto_aprobado': monto_ap,
            'usuario_aprobacion': r.get('usuario_aprobacion', ''),
            'notas':        r.get('notas', ''),
            'fecha_resolucion': r.get('fecha_resolucion', ''),
            'pct_aprobado': round(monto_ap / monto * 100, 0) if monto_ap and monto else None,
        })

    es_finanzas = _es_admin() or _tiene_acceso('reportes.pedido_aprobar')
    resumen = {
        'total':     len(pedidos),
        'pendiente': sum(1 for p in pedidos if p['estado_aprob'] == 'PENDIENTE'),
        'aprobado':  sum(1 for p in pedidos if p['estado_aprob'] == 'APROBADO'),
        'rechazado': sum(1 for p in pedidos if p['estado_aprob'] == 'RECHAZADO'),
        'monto_pendiente': sum(p['monto_total'] for p in pedidos if p['estado_aprob'] == 'PENDIENTE'),
        'monto_aprobado':  sum(p['monto_total'] for p in pedidos if p['estado_aprob'] == 'APROBADO'),
    }

    return dict(
        pedidos=pedidos,
        resumen=resumen,
        es_finanzas=es_finanzas,
        formato_moneda=_formato_moneda,
    )


def remito_datos_proveedor():
    """AJAX: Busca datos del proveedor por nombre (para autocompletar).
    Devuelve: numero (cuenta), denominacion, cuit, condicion_iva, zona, provincia.
    """
    _requiere_acceso()
    import json
    nombre = request.vars.nombre or ''
    if len(nombre) < 2:
        return json.dumps(dict(ok=False, msg='Nombre muy corto'))

    nombre_safe = nombre.replace("'", "''")
    sql = """
    SELECT TOP 10
        numero AS cuenta, RTRIM(denominacion) AS denominacion,
        RTRIM(ISNULL(cuit,'')) AS cuit,
        RTRIM(ISNULL(condicion_iva,'I')) AS condicion_iva,
        ISNULL(zona, 1) AS zona
    FROM msgestionC.dbo.proveedores
    WHERE denominacion LIKE '%{q}%'
    ORDER BY denominacion
    """.format(q=nombre_safe)

    try:
        rows = _ejecutar_sql_gestionC(sql)
        data = []
        for r in rows:
            data.append(dict(
                cuenta=int(r['cuenta']) if r['cuenta'] else 0,
                denominacion=r['denominacion'] or '',
                cuit=r['cuit'] or '',
                condicion_iva=r['condicion_iva'] or 'I',
                zona=int(r['zona']) if r['zona'] else 1,
            ))
        return json.dumps(dict(ok=True, proveedores=data))
    except Exception as e:
        return json.dumps(dict(ok=False, msg=str(e)))


def remito_ultimo_numero():
    """AJAX: Devuelve el ultimo numero de remito del proveedor para auto-incrementar.
    Busca en compras2 el MAX(numero) para la cuenta dada, y devuelve numero+1.
    """
    _requiere_acceso()
    import json
    cuenta = int(request.vars.cuenta or 0)
    if not cuenta:
        return json.dumps(dict(ok=False, msg='Falta cuenta'))

    sql = """
    SELECT ISNULL(MAX(numero), 0) AS ultimo
    FROM msgestionC.dbo.compras2
    WHERE cuenta = {cta} AND codigo IN (7, 36) AND letra = 'R'
    """.format(cta=cuenta)

    try:
        rows = _ejecutar_sql_gestionC(sql)
        ultimo = int(rows[0]['ultimo']) if rows else 0
        return json.dumps(dict(ok=True, ultimo=ultimo, siguiente=ultimo + 1))
    except Exception as e:
        return json.dumps(dict(ok=False, msg=str(e)))


def remito_crear():
    """POST: Crea un remito de compra (ingreso=7 o devolucion=36).
    Inserta cabecera en compras2 y renglones en compras1.

    Params (POST JSON):
      tipo: 7 (ingreso) o 36 (devolucion)
      sucursal_pv: punto de venta del remito del proveedor
      numero_remito: numero del remito del proveedor
      deposito: deposito destino
      cuenta: numero de proveedor
      fecha: fecha del comprobante (YYYY-MM-DD)
      items: [ {articulo, descripcion, cantidad, precio}, ... ]
    """
    _requiere_acceso()
    import json
    from datetime import datetime

    try:
        # Parsear body JSON
        body = json.loads(request.body.read())
    except:
        return json.dumps(dict(ok=False, msg='JSON invalido'))

    tipo = int(body.get('tipo', 7))
    if tipo not in (7, 36):
        return json.dumps(dict(ok=False, msg='Tipo debe ser 7 (ingreso) o 36 (devolucion)'))

    sucursal_pv = int(body.get('sucursal_pv', 0))
    numero_remito = int(body.get('numero_remito', 0))
    deposito = int(body.get('deposito', 0))
    cuenta = int(body.get('cuenta', 0))
    fecha = body.get('fecha', datetime.now().strftime('%Y-%m-%d'))
    items = body.get('items', [])

    if not cuenta:
        return json.dumps(dict(ok=False, msg='Falta proveedor (cuenta)'))
    if not items:
        return json.dumps(dict(ok=False, msg='No hay items para el remito'))
    if not numero_remito:
        return json.dumps(dict(ok=False, msg='Falta numero de remito'))

    # ---- CONTROL PRESUPUESTARIO ----
    # Verificar aprobación de CADA pedido referenciado en los items
    # Si algún pedido está RECHAZADO o PENDIENTE, bloquear el remito
    numeros_pedido = set()
    for it in items:
        pn = int(it.get('ped_numero', 0) or 0)
        if pn:
            numeros_pedido.add(pn)

    if numeros_pedido:
        aprobaciones = _aprobacion_pedidos(numeros_pedido)
        bloqueados = []
        for num_ped in numeros_pedido:
            ap = aprobaciones.get(num_ped)
            if not ap:
                # Sin registro → crear como PENDIENTE y bloquear
                _registrar_aprobacion(num_ped)
                bloqueados.append('Pedido #{} sin aprobación presupuestaria'.format(num_ped))
            elif ap['estado'] == 'RECHAZADO':
                bloqueados.append('Pedido #{} RECHAZADO por finanzas: {}'.format(
                    num_ped, ap.get('notas', '') or 'sin notas'))
            elif ap['estado'] == 'PENDIENTE':
                bloqueados.append('Pedido #{} pendiente de aprobación presupuestaria'.format(num_ped))
            # APROBADO → verificar monto si tiene límite parcial
            elif ap['estado'] == 'APROBADO' and ap.get('monto_aprobado'):
                # Calcular monto de este pedido en los items
                monto_items_ped = sum(
                    float(it.get('precio', 0)) * float(it.get('cant_clz', 0) or 0) +
                    float(it.get('precio', 0)) * float(it.get('cant_h4', 0) or 0)
                    for it in items if int(it.get('ped_numero', 0) or 0) == num_ped
                )
                if monto_items_ped > float(ap['monto_aprobado']):
                    bloqueados.append('Pedido #{} supera monto aprobado (${:,.0f} > ${:,.0f})'.format(
                        num_ped, monto_items_ped, float(ap['monto_aprobado'])))
        if bloqueados:
            return json.dumps(dict(ok=False, msg=' | '.join(bloqueados), bloqueado_presupuesto=True))

    # Obtener datos del proveedor
    sql_prov = """
    SELECT TOP 1
        RTRIM(denominacion) AS denominacion,
        RTRIM(ISNULL(cuit,'')) AS cuit,
        RTRIM(ISNULL(condicion_iva,'I')) AS condicion_iva,
        ISNULL(zona, 1) AS zona,
        RTRIM(ISNULL(direccion,'')) AS direccion
    FROM msgestionC.dbo.proveedores
    WHERE numero = {c}
    """.format(c=cuenta)
    prov = _ejecutar_sql_gestionC(sql_prov)
    if not prov:
        return json.dumps(dict(ok=False, msg='Proveedor no encontrado'))
    prov = prov[0]

    operacion = '+' if tipo == 7 else '-'
    serie = ''  # Serie vacia — se implementará con codigo de barras
    usuario = auth.user.email[:10] if auth.user and auth.user.email else 'WEB'
    usr_movi = 'WB'  # 2 chars para movi_stock

    # Separar items por destino: cada item trae cant_clz y cant_h4
    # ABI -> msgestionC(empresa=CALZALINDO) + msgestion01
    # H4  -> msgestionC(empresa=H4) + msgestion03
    items_clz = []
    items_h4 = []
    for it in items:
        cc = int(it.get('cant_clz', 0) or 0)
        ch = int(it.get('cant_h4', 0) or 0)
        ped_info = dict(ped_sucursal=int(it.get('ped_sucursal',0) or 0),
                        ped_numero=int(it.get('ped_numero',0) or 0),
                        ped_orden=int(it.get('ped_orden',0) or 0),
                        ped_renglon=int(it.get('ped_renglon',0) or 0))
        if cc > 0:
            items_clz.append(dict(articulo=it.get('articulo'), descripcion=it.get('descripcion',''),
                                  precio=it.get('precio',0), cantidad=cc, **ped_info))
        if ch > 0:
            items_h4.append(dict(articulo=it.get('articulo'), descripcion=it.get('descripcion',''),
                                 precio=it.get('precio',0), cantidad=ch, **ped_info))

    if not items_clz and not items_h4:
        return json.dumps(dict(ok=False, msg='Todos los items tienen cantidad 0'))

    # Config por destino: (empresa_msgestionC, base_secundaria, lista_items)
    destinos = []
    if items_clz:
        destinos.append(('CALZALINDO', 'msgestion01', items_clz))
    if items_h4:
        destinos.append(('H4', 'msgestion03', items_h4))

    signo_stock = 1 if tipo == 7 else -1  # ingreso suma, devolucion resta

    try:
        for empresa, base, dest_items in destinos:
            # ---- ORDEN POR EMPRESA ----
            # Calcular next_orden dentro del loop para que cada empresa
            # obtenga su propio orden (evita duplicados en vista msgestionC)
            sql_orden = """
            SELECT ISNULL(MAX(orden), 0) + 1 AS next_orden
            FROM {b}.dbo.compras2
            WHERE codigo = {cod}
              AND letra = 'R' AND sucursal = {suc} AND numero = {num}
            """.format(b=base, cod=tipo, suc=sucursal_pv, num=numero_remito)
            next_orden = int(db_omicronvt.executesql(sql_orden, as_dict=True)[0]['next_orden'])

            # Calcular total para esta cabecera
            total_monto = 0.0
            for it in dest_items:
                total_monto += float(it.get('precio', 0)) * float(it.get('cantidad', 0))

            # msgestionC.dbo.compras2/compras1/movi_stock/stock son VISTAS (UNION de 01+03)
            # Se inserta SOLO en la base real: msgestion01 (CLZ) o msgestion03 (H4)

            # ---- INSERT compras2 (cabecera) ----
            cols_c2 = "codigo, letra, sucursal, numero, orden, \
deposito, cuenta, cuenta_cc, denominacion, \
fecha_comprobante, fecha_proceso, fecha_contable, \
concepto_gravado, concepto_no_gravado, monto_general, \
estado_stock, estado, zona, condicion_iva, numero_cuit, \
contabiliza, consignacion, venta_anticipada, \
moneda, sistema_cc, sistema_cuenta, \
fecha_vencimiento, fecha_hora, \
usuario, usuario_creacion, host_creacion"

            vals_c2 = "{cod}, 'R', {suc}, {num}, {ord}, \
{dep}, {cta}, {cta}, '{denom}', \
'{fecha}', '{fecha}', '{fecha}', \
{gravado}, 0, {general}, \
'S', 'V', {zona}, '{iva}', '{cuit}', \
'N', '1 ', 'N', \
0, 2, 2, \
'{fecha}', GETDATE(), \
'{usr}', '{usr}', 'INFORMES-WEB'".format(
                cod=tipo, suc=sucursal_pv, num=numero_remito, ord=next_orden,
                dep=deposito, cta=cuenta,
                denom=prov['denominacion'].replace("'", "''"),
                fecha=fecha,
                gravado=round(total_monto, 2),
                general=round(total_monto, 2),
                zona=prov['zona'],
                iva=prov['condicion_iva'],
                cuit=prov['cuit'],
                usr=usuario.replace("'", "''"))

            sql_c2 = "INSERT INTO {b}.dbo.compras2 ({c}) VALUES ({v})".format(
                b=base, c=cols_c2, v=vals_c2)
            db_omicronvt.executesql(sql_c2)

            # ---- INSERT comprasr (extension remito) ----
            dir_prov = (prov.get('direccion') or '').replace("'", "''")[:100]
            sql_cr = """
            INSERT INTO {b}.dbo.comprasr (
                codigo, letra, sucursal, numero, orden,
                cupones, bultos, fecha_vencimiento,
                precio_financiado, sin_valor_declarado, direccion,
                sector, kg, cod_postal_trans, codigo_redespacho,
                cod_postal_redespacho, campo, valor_declarado,
                ENTREGADOR2, ENTREGADOR3, origen, destino,
                cp_transporte, km_flete, tarifa_flete, importe_flete,
                recorrido_codpos, dest_codpos, rem_codpos
            ) VALUES (
                {cod}, 'R', {suc}, {num}, {ord},
                0, 0, '{fecha}',
                'S', 'N', '{dir}',
                0, 0, 0, 0,
                0, 0, 0,
                0, 0, 0, 0,
                0, 0, 0, 0,
                0, 0, 0
            )
            """.format(
                b=base,
                cod=tipo, suc=sucursal_pv, num=numero_remito, ord=next_orden,
                fecha=fecha, dir=dir_prov
            )
            db_omicronvt.executesql(sql_cr)

            # ---- INSERT compras1 (renglones) ----
            for idx, it in enumerate(dest_items, start=1):
                cant = float(it.get('cantidad', 0))
                precio = float(it.get('precio', 0))
                monto = round(precio * cant, 2)
                art = int(it.get('articulo', 0))
                desc = (it.get('descripcion', '') or '')[:60].replace("'", "''")

                cols_c1 = "codigo, letra, sucursal, numero, orden, renglon, \
articulo, descripcion, precio, cantidad, deposito, \
estado_stock, estado, operacion, fecha, cuenta, \
calificacion, condicion_iva, consignacion, \
cantidad_entregada, monto_entregado, \
cantidad_devuelta, cantidad_pagada, \
monto_devuelto, monto_pagado, \
unidades, cantidad_original, serie, \
venta_anticipada, financiacion_general, \
fecha_hora, usuario_creacion, host_creacion"

                vals_c1 = "{cod}, 'R', {suc}, {num}, {ord}, {reng}, \
{art}, '{desc}', {precio}, {cant}, {dep}, \
'S', 'V', '{op}', '{fecha}', {cta}, \
'G', '{iva}', '1 ', \
{cant_ent}, {monto_ent}, \
0, 0, \
0, 0, \
{unid}, {cant_orig}, '{serie}', \
'N', 0, \
GETDATE(), '{usr}', 'INFORMES-WEB'".format(
                    cod=tipo, suc=sucursal_pv, num=numero_remito, ord=next_orden,
                    reng=idx, art=art, desc=desc, precio=round(precio, 2),
                    cant=int(cant), dep=deposito,
                    op=operacion, fecha=fecha, cta=cuenta,
                    iva=prov['condicion_iva'],
                    cant_ent=int(cant), monto_ent=monto,
                    unid=int(cant), cant_orig=int(cant),
                    serie=serie,
                    usr=usuario.replace("'", "''"))

                sql_c1 = "INSERT INTO {b}.dbo.compras1 ({c}) VALUES ({v})".format(
                    b=base, c=cols_c1, v=vals_c1)
                db_omicronvt.executesql(sql_c1)

            # ---- INSERT movi_stock ----
            for idx, it in enumerate(dest_items, start=1):
                cant = float(it.get('cantidad', 0))
                precio = float(it.get('precio', 0))
                art = int(it.get('articulo', 0))

                sql_ms = """
                INSERT INTO {b}.dbo.movi_stock (
                    deposito, articulo, fecha,
                    codigo_comprobante, letra_comprobante,
                    sucursal_comprobante, numero_comprobante, orden,
                    operacion, cantidad, precio, cuenta,
                    vta_anticipada, sistema, serie,
                    unidades, fecha_contable, fecha_proceso, usuario
                ) VALUES (
                    {dep}, {art}, GETDATE(),
                    {cod}, 'R',
                    {suc}, {num}, {ord},
                    '{op}', {cant}, {precio}, {cta},
                    'N', 7, '{serie}',
                    {unid}, '{fecha}', GETDATE(), '{usr}'
                )
                """.format(
                    b=base,
                    dep=deposito, art=art,
                    cod=tipo, suc=sucursal_pv, num=numero_remito, ord=next_orden,
                    op=operacion, cant=int(cant), precio=round(precio, 2),
                    cta=cuenta, serie=serie, fecha=fecha, usr=usr_movi,
                    unid=int(cant)
                )
                db_omicronvt.executesql(sql_ms)

            # ---- UPDATE stock (serie=' ') ----
            # El ERP NO actualiza stock desde INSERTs SQL directos.
            # Actualizamos manualmente SOLO serie=' ' (la fila consolidada).
            # Bug 13-mar-2026 era doble escritura ('2603' + ' ') — aquí solo ' '.
            for it in dest_items:
                cant = float(it.get('cantidad', 0))
                art = int(it.get('articulo', 0))
                sql_stock = """
                MERGE {b}.dbo.stock AS t
                USING (SELECT {dep} AS deposito, {art} AS articulo) AS s
                  ON t.deposito = s.deposito AND t.articulo = s.articulo AND t.serie = ' '
                WHEN MATCHED THEN
                    UPDATE SET t.stock_actual = t.stock_actual + ({cant} * {signo})
                WHEN NOT MATCHED THEN
                    INSERT (deposito, articulo, serie, stock_actual)
                    VALUES ({dep}, {art}, ' ', {cant} * {signo});
                """.format(
                    b=base, dep=deposito, art=art,
                    cant=int(cant), signo=signo_stock
                )
                db_omicronvt.executesql(sql_stock)

        # ---- INSERT pedico1_entregas + UPDATE pedico1.cantidad_entregada ----
        # El pedido existe en AMBAS bases (msgestion01 y msgestion03) con datos identicos.
        # Hay que actualizar en AMBAS para que la cache de pendientes se sincronice bien.
        # Cada item trae la cantidad TOTAL entregada (cant_clz + cant_h4 sumadas por articulo).
        _ambas_bases = ['msgestion01', 'msgestion03']

        # Consolidar entregas por articulo (un item puede estar en CLZ y H4)
        _entregas_por_renglon = {}
        for empresa, base, dest_items in destinos:
            for it in dest_items:
                ps = int(it.get('ped_sucursal', 0))
                pn = int(it.get('ped_numero', 0))
                po = int(it.get('ped_orden', 0))
                pr = int(it.get('ped_renglon', 0))
                if ps == 0 and pn == 0:
                    continue
                key = (ps, pn, po, pr)
                if key not in _entregas_por_renglon:
                    _entregas_por_renglon[key] = dict(
                        articulo=int(it.get('articulo', 0)),
                        precio=float(it.get('precio', 0)),
                        cantidad=0)
                _entregas_por_renglon[key]['cantidad'] += int(it.get('cantidad', 0))

        for (ps, pn, po, pr), info in _entregas_por_renglon.items():
            cant_ent = info['cantidad']
            monto_ent = round(info['precio'] * cant_ent, 2)
            art = info['articulo']

            for b in _ambas_bases:
                # UPSERT pedico1_entregas (si ya hay entrega parcial, acumular)
                sql_pe = """
                IF EXISTS (SELECT 1 FROM {b}.dbo.pedico1_entregas
                           WHERE codigo=8 AND letra='X'
                             AND sucursal={ps} AND numero={pn}
                             AND orden={po} AND renglon={pr})
                    UPDATE {b}.dbo.pedico1_entregas
                    SET cantidad = ISNULL(cantidad, 0) + {cant},
                        fecha_entrega = '{fecha}'
                    WHERE codigo=8 AND letra='X'
                      AND sucursal={ps} AND numero={pn}
                      AND orden={po} AND renglon={pr}
                ELSE
                    INSERT INTO {b}.dbo.pedico1_entregas (
                        codigo, letra, sucursal, numero, orden,
                        renglon, articulo, cantidad, deposito, fecha_entrega
                    ) VALUES (
                        8, 'X', {ps}, {pn}, {po},
                        {pr}, {art}, {cant}, {dep}, '{fecha}'
                    )
                """.format(b=b, ps=ps, pn=pn, po=po, pr=pr,
                           art=art, cant=cant_ent,
                           dep=deposito, fecha=fecha)
                db_omicronvt.executesql(sql_pe)

                # UPDATE pedico1.cantidad_entregada (acumular)
                sql_upd = """
                UPDATE {b}.dbo.pedico1
                SET cantidad_entregada = ISNULL(cantidad_entregada, 0) + {cant},
                    monto_entregado = ISNULL(monto_entregado, 0) + {monto}
                WHERE codigo = 8 AND letra = 'X'
                  AND sucursal = {ps} AND numero = {pn}
                  AND orden = {po} AND renglon = {pr}
                """.format(b=b, cant=cant_ent, monto=monto_ent,
                           ps=ps, pn=pn, po=po, pr=pr)
                db_omicronvt.executesql(sql_upd)

        db_omicronvt.commit()

        # Refrescar cache de pedidos para que se actualicen los pendientes
        try:
            db_omicronvt.executesql("EXEC omicronvt.dbo.sp_sync_pedidos")
            db_omicronvt.commit()
        except:
            pass  # Si falla el sync no es critico, el remito ya se creo

        # Mensaje con detalle del reparto
        msg_parts = []
        if items_clz:
            msg_parts.append('{} ABI'.format(len(items_clz)))
        if items_h4:
            msg_parts.append('{} H4'.format(len(items_h4)))
        reparto = ' (' + ' + '.join(msg_parts) + ')' if len(msg_parts) > 1 else ''

        # Recopilar ordenes usadas para el mensaje
        ordenes_usadas = []
        for empresa, base, dest_items in destinos:
            sql_o = """SELECT ISNULL(MAX(orden), 0) AS ult_orden
            FROM {b}.dbo.compras2
            WHERE codigo={cod} AND letra='R' AND sucursal={suc} AND numero={num}
            """.format(b=base, cod=tipo, suc=sucursal_pv, num=numero_remito)
            rs = db_omicronvt.executesql(sql_o, as_dict=True)
            if rs:
                ordenes_usadas.append(int(rs[0]['ult_orden']))

        orden_txt = '/'.join(str(o) for o in ordenes_usadas) if ordenes_usadas else '?'

        return json.dumps(dict(
            ok=True,
            msg='Remito creado: R {}-{} orden {} ({} items{})'.format(
                sucursal_pv, numero_remito, orden_txt, len(items), reparto),
            tipo=tipo,
            sucursal=sucursal_pv,
            numero=numero_remito,
            orden=ordenes_usadas[0] if ordenes_usadas else 1
        ))

    except Exception as e:
        import traceback
        return json.dumps(dict(ok=False, msg=str(e), trace=traceback.format_exc()))


def remito_eliminar():
    """POST: Elimina un remito de compra creado desde la web (usuario WB).
    Revierte stock, borra movi_stock, compras1, comprasr, compras2,
    pedico1_entregas y descuenta pedico1.cantidad_entregada.

    Params (POST JSON):
      codigo:   7 (ingreso) o 36 (devolucion)
      sucursal: sucursal del remito
      numero:   numero del remito
      orden:    orden del remito
    """
    _requiere_acceso()
    import json

    try:
        body = json.loads(request.body.read())
    except:
        return json.dumps(dict(ok=False, msg='JSON invalido'))

    codigo = int(body.get('codigo', 0))
    sucursal = int(body.get('sucursal', 0))
    numero = int(body.get('numero', 0))
    orden = int(body.get('orden', 0))

    if not all([codigo, sucursal, numero, orden]):
        return json.dumps(dict(ok=False, msg='Faltan datos: codigo, sucursal, numero, orden'))
    if codigo not in (7, 36):
        return json.dumps(dict(ok=False, msg='Codigo debe ser 7 (ingreso) o 36 (devolucion)'))

    # Buscar en que base(s) existe el remito
    bases_a_revisar = [
        ('CALZALINDO', 'msgestion01'),
        ('H4', 'msgestion03'),
    ]

    signo_reversa = -1 if codigo == 7 else 1  # ingreso restamos, devolucion sumamos

    encontrado = False
    items_borrados = 0

    try:
        for empresa, base in bases_a_revisar:
            # Verificar que exista la cabecera en esta base
            sql_check = """
            SELECT COUNT(*) AS n FROM {b}.dbo.compras2
            WHERE codigo={cod} AND letra='R'
              AND sucursal={suc} AND numero={num} AND orden={ord}
            """.format(b=base, cod=codigo, suc=sucursal, num=numero, ord=orden)
            row = _ejecutar_sql(sql_check, as_dict=True)
            if not row or int(row[0]['n']) == 0:
                continue

            encontrado = True

            # 1. Leer items de compras1 para saber que revertir en stock
            sql_items = """
            SELECT articulo, cantidad, deposito, serie
            FROM {b}.dbo.compras1
            WHERE codigo={cod} AND letra='R'
              AND sucursal={suc} AND numero={num} AND orden={ord}
            """.format(b=base, cod=codigo, suc=sucursal, num=numero, ord=orden)
            items = _ejecutar_sql(sql_items, as_dict=True)
            items_borrados += len(items)

            # 2. Revertir stock por cada item
            for it in items:
                art = int(it['articulo'])
                cant = int(it['cantidad'])
                dep = int(it['deposito'])
                serie_item = it['serie'] if it['serie'] and it['serie'].strip() else ' '
                delta = cant * signo_reversa

                sql_stk = """
                UPDATE {b}.dbo.stock
                SET stock_actual = stock_actual + {delta},
                    stock_unidades = stock_unidades + {delta}
                WHERE deposito={dep} AND articulo={art} AND serie='{serie}'
                """.format(b=base, dep=dep, art=art, delta=delta, serie=serie_item)
                db_omicronvt.executesql(sql_stk)

            # 3. Revertir pedico1_entregas y pedico1.cantidad_entregada
            #    Buscar movi_stock para obtener los datos del pedido vinculado
            sql_pe = """
            SELECT pe.renglon, pe.articulo, pe.cantidad,
                   pe.codigo, pe.letra, pe.sucursal, pe.numero, pe.orden
            FROM {b}.dbo.pedico1_entregas pe
            WHERE pe.fecha_entrega IN (
                SELECT CAST(c2.fecha_comprobante AS DATE)
                FROM {b}.dbo.compras2 c2
                WHERE c2.codigo={cod} AND c2.letra='R'
                  AND c2.sucursal={suc} AND c2.numero={num} AND c2.orden={ord}
            )
            AND pe.articulo IN (
                SELECT c1.articulo FROM {b}.dbo.compras1 c1
                WHERE c1.codigo={cod} AND c1.letra='R'
                  AND c1.sucursal={suc} AND c1.numero={num} AND c1.orden={ord}
            )
            AND pe.deposito IN (
                SELECT c1.deposito FROM {b}.dbo.compras1 c1
                WHERE c1.codigo={cod} AND c1.letra='R'
                  AND c1.sucursal={suc} AND c1.numero={num} AND c1.orden={ord}
            )
            """.format(b=base, cod=codigo, suc=sucursal, num=numero, ord=orden)

            try:
                pe_rows = _ejecutar_sql(sql_pe, as_dict=True)
                # Revertir pedico1 en AMBAS bases (el pedido existe en ambas)
                for pe in pe_rows:
                    pe_cant = int(pe['cantidad'])
                    for rev_base in ['msgestion01', 'msgestion03']:
                        sql_upd_ped = """
                        UPDATE {b}.dbo.pedico1
                        SET cantidad_entregada = ISNULL(cantidad_entregada, 0) - {cant},
                            monto_entregado = CASE
                                WHEN ISNULL(monto_entregado, 0) > 0
                                THEN monto_entregado - (precio * {cant})
                                ELSE 0 END
                        WHERE codigo = {pcod} AND letra = '{pletra}'
                          AND sucursal = {psuc} AND numero = {pnum}
                          AND orden = {pord} AND renglon = {preng}
                        """.format(b=rev_base,
                                   cant=pe_cant,
                                   pcod=int(pe['codigo']),
                                   pletra=pe['letra'].strip(),
                                   psuc=int(pe['sucursal']),
                                   pnum=int(pe['numero']),
                                   pord=int(pe['orden']),
                                   preng=int(pe['renglon']))
                        db_omicronvt.executesql(sql_upd_ped)

                # Borrar pedico1_entregas en AMBAS bases
                for del_base in ['msgestion01', 'msgestion03']:
                    sql_del_pe = """
                    DELETE FROM {b}.dbo.pedico1_entregas
                    WHERE fecha_entrega IN (
                        SELECT CAST(c2.fecha_comprobante AS DATE)
                        FROM {base_remito}.dbo.compras2 c2
                        WHERE c2.codigo={cod} AND c2.letra='R'
                          AND c2.sucursal={suc} AND c2.numero={num} AND c2.orden={ord}
                    )
                    AND articulo IN (
                        SELECT c1.articulo FROM {base_remito}.dbo.compras1 c1
                        WHERE c1.codigo={cod} AND c1.letra='R'
                          AND c1.sucursal={suc} AND c1.numero={num} AND c1.orden={ord}
                    )
                    AND deposito IN (
                        SELECT c1.deposito FROM {base_remito}.dbo.compras1 c1
                        WHERE c1.codigo={cod} AND c1.letra='R'
                          AND c1.sucursal={suc} AND c1.numero={num} AND c1.orden={ord}
                    )
                    """.format(b=del_base, base_remito=base,
                               cod=codigo, suc=sucursal, num=numero, ord=orden)
                    db_omicronvt.executesql(sql_del_pe)
            except:
                pass  # Si no habia entregas vinculadas, no es critico

            # 4. DELETE movi_stock
            sql_del_ms = """
            DELETE FROM {b}.dbo.movi_stock
            WHERE codigo_comprobante={cod} AND letra_comprobante='R'
              AND sucursal_comprobante={suc} AND numero_comprobante={num}
              AND orden={ord}
            """.format(b=base, cod=codigo, suc=sucursal, num=numero, ord=orden)
            db_omicronvt.executesql(sql_del_ms)

            # 5. DELETE compras1 (renglones)
            sql_del_c1 = """
            DELETE FROM {b}.dbo.compras1
            WHERE codigo={cod} AND letra='R'
              AND sucursal={suc} AND numero={num} AND orden={ord}
            """.format(b=base, cod=codigo, suc=sucursal, num=numero, ord=orden)
            db_omicronvt.executesql(sql_del_c1)

            # 6. DELETE comprasr (extension)
            sql_del_cr = """
            DELETE FROM {b}.dbo.comprasr
            WHERE codigo={cod} AND letra='R'
              AND sucursal={suc} AND numero={num} AND orden={ord}
            """.format(b=base, cod=codigo, suc=sucursal, num=numero, ord=orden)
            db_omicronvt.executesql(sql_del_cr)

            # 7. DELETE compras2 (cabecera)
            sql_del_c2 = """
            DELETE FROM {b}.dbo.compras2
            WHERE codigo={cod} AND letra='R'
              AND sucursal={suc} AND numero={num} AND orden={ord}
            """.format(b=base, cod=codigo, suc=sucursal, num=numero, ord=orden)
            db_omicronvt.executesql(sql_del_c2)

        if not encontrado:
            return json.dumps(dict(ok=False,
                msg='Remito R {}-{} orden {} (cod {}) no encontrado'.format(
                    sucursal, numero, orden, codigo)))

        db_omicronvt.commit()

        # Refrescar cache de pedidos
        try:
            db_omicronvt.executesql("EXEC omicronvt.dbo.sp_sync_pedidos")
            db_omicronvt.commit()
        except:
            pass

        return json.dumps(dict(
            ok=True,
            msg='Remito eliminado: R {}-{} orden {} ({} items revertidos)'.format(
                sucursal, numero, orden, items_borrados)
        ))

    except Exception as e:
        import traceback
        return json.dumps(dict(ok=False, msg=str(e), trace=traceback.format_exc()))
