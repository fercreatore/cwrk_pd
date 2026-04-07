# -*- coding: utf-8 -*-
"""
INTELIGENCIA COMERCIAL - Controller
====================================
BCG Matrix, Proveedores ROI, Stock Muerto.
Usa: dbC (msgestionC), db1 (msgestion01art), db_omicronvt (omicronvt)
"""

import json
import decimal
import datetime
import math

# Python 2/3 compatibility
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

def _median(values):
    """Calculate median from a list of numbers."""
    s = sorted(v for v in values if v is not None)
    if not s:
        return 0
    mid = len(s) // 2
    if len(s) % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2.0
    return s[mid]


# =============================================================================
# CONTROLLERS
# =============================================================================

def stock_muerto():
    """Stock muerto agrupado por modelo (sinonimo-4), formato zapatero con curva de talles."""
    _requiere_acceso()

    def _fetch():
        # Traer articulos con stock sin ventas 12m, con talle y color
        sql = """
        SELECT s_agg.articulo, a.descripcion_1,
               LTRIM(RTRIM(ISNULL(a.codigo_sinonimo,''))) as sinonimo,
               a.descripcion_5 as talle, a.descripcion_2 as color_desc,
               a.marca as cod_marca, m.descripcion as nombre_marca,
               a.rubro as cod_rubro, r.descripcion as nombre_rubro,
               a.precio_costo,
               s_agg.stock_total
        FROM (SELECT s.articulo, SUM(s.stock_actual) as stock_total
              FROM msgestionC.dbo.stock s WITH (NOLOCK)
              WHERE s.deposito IN (0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)
              GROUP BY s.articulo HAVING SUM(s.stock_actual) > 0) s_agg
        JOIN msgestion01art.dbo.articulo a WITH (NOLOCK) ON a.codigo = s_agg.articulo
        LEFT JOIN msgestionC.dbo.marcas m WITH (NOLOCK) ON m.codigo = a.marca
        LEFT JOIN msgestionC.dbo.rubros r WITH (NOLOCK) ON r.codigo = a.rubro
        LEFT JOIN (SELECT DISTINCT v.articulo FROM msgestionC.dbo.ventas1 v WITH (NOLOCK)
                   WHERE v.codigo NOT IN (7,36) AND v.cantidad > 0
                   AND v.fecha >= DATEADD(MONTH, -12, GETDATE())) vtas ON vtas.articulo = s_agg.articulo
        WHERE vtas.articulo IS NULL AND a.marca NOT IN (1316,1317,1158,436)
        ORDER BY a.marca, LTRIM(RTRIM(a.codigo_sinonimo))
        """
        rows = dbC.executesql(sql, as_dict=True)

        # Agrupar por modelo (sinonimo menos ultimos 4 chars) + color
        from collections import OrderedDict
        modelos = OrderedDict()

        for r in rows:
            r = _fix_row(r)
            d = {k: _clean(v) for k, v in r.items()}
            sin = str(d.get('sinonimo', '')).strip()
            if len(sin) < 5:
                modelo_key = sin or str(d.get('articulo', ''))
            else:
                modelo_key = sin[:-4]

            marca = (d.get('nombre_marca') or '').strip()
            color = (d.get('color_desc') or '').strip()
            talle = str(d.get('talle') or '00').strip()
            stock = float(d.get('stock_total') or 0)
            costo = float(d.get('precio_costo') or 0)
            desc = (d.get('descripcion_1') or '').strip()
            rubro = (d.get('nombre_rubro') or '').strip()

            group_key = '%s|%s' % (modelo_key, color)

            if group_key not in modelos:
                modelos[group_key] = {
                    'modelo': modelo_key,
                    'descripcion': desc,
                    'marca': marca,
                    'rubro': rubro,
                    'color': color,
                    'precio_costo': costo,
                    'talles': {},
                    'stock_total': 0,
                    'capital': 0,
                }
            m = modelos[group_key]
            m['talles'][talle] = m['talles'].get(talle, 0) + stock
            m['stock_total'] += stock
            m['capital'] += stock * costo
            # Actualizar precio si es mayor (por si hay variaciones)
            if costo > m['precio_costo']:
                m['precio_costo'] = costo

        # Convertir a lista, filtrar stock_total > 5
        result = []
        for gk, m in modelos.items():
            if m['stock_total'] < 5:
                continue
            m['capital'] = round(m['capital'], 0)
            m['alerta'] = 'PRECIO ANOMALO' if m['precio_costo'] > 500000 else ''
            # Ordenar talles para curva zapatero
            talles_ordenados = sorted(m['talles'].items(), key=lambda x: _talle_sort(x[0]))
            m['curva'] = [{'talle': t, 'stock': int(s)} for t, s in talles_ordenados]
            m['talles_str'] = ' | '.join(['%s:%d' % (t, int(s)) for t, s in talles_ordenados])
            result.append(m)

        result.sort(key=lambda x: x['capital'], reverse=True)
        return result[:300]

    data = cache.ram('stock_muerto_v5', _fetch, 3600)

    total_modelos = len(data)
    total_pares = sum(r.get('stock_total', 0) for r in data)
    capital_total = sum(r.get('capital', 0) or 0 for r in data)
    anomalias = sum(1 for r in data if r.get('alerta'))

    return dict(
        data_json=json.dumps(data, ensure_ascii=False),
        total_modelos=total_modelos,
        total_pares=int(total_pares),
        capital_total=capital_total,
        anomalias=anomalias,
    )


def _talle_sort(talle):
    """Ordena talles: numerico primero (17-50), luego letras (XS,S,M,L,XL,XXL)."""
    letras = {'XXS': 0, 'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6, 'XXXL': 7}
    t = str(talle).strip().upper()
    if t in letras:
        return (1, letras[t])
    try:
        return (0, float(t))
    except (ValueError, TypeError):
        return (2, 0)


def bcg_matrix():
    """Matriz BCG por marca: margen vs rotacion."""
    _requiere_acceso()

    def _fetch():
        # Query 1: Ventas 12m por marca (con nombre)
        sql_ventas = """
        SELECT a.marca as cod_marca, m.descripcion as nombre_marca, SUM(v.cantidad) as uds_12m,
               SUM(v.total_item) as venta_total,
               SUM(v.precio_costo * v.cantidad) as costo_total,
               CASE WHEN SUM(v.total_item)>0 THEN (SUM(v.total_item)-SUM(v.precio_costo*v.cantidad))*100.0/SUM(v.total_item) ELSE 0 END as margen_pct
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        LEFT JOIN msgestionC.dbo.marcas m ON m.codigo = a.marca
        WHERE v.fecha >= DATEADD(MONTH, -12, GETDATE())
          AND v.codigo NOT IN (7, 36) AND a.marca NOT IN (1316,1317,1158,436) AND v.cantidad > 0
        GROUP BY a.marca, m.descripcion HAVING SUM(v.total_item) > 2000000
        ORDER BY SUM(v.total_item) DESC
        """
        ventas = dbC.executesql(sql_ventas, as_dict=True)

        # Query 2: Stock por marca
        sql_stock = """
        SELECT a.marca, SUM(s.stock_actual) as stock_total
        FROM msgestionC.dbo.stock s JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        WHERE s.deposito IN (0,1,2,3,4,5,6,7,8,9,11,12,14,15,198) AND a.marca NOT IN (1316,1317,1158,436)
        GROUP BY a.marca
        """
        stock_rows = dbC.executesql(sql_stock, as_dict=True)
        stock_map = {}
        for sr in stock_rows:
            sr = _fix_row(sr)
            stock_map[sr['marca']] = float(sr.get('stock_total') or 0)

        # Query 3: factor quiebre por marca (optional)
        quiebre_map = {}
        try:
            sql_quiebre = """
            SELECT a.marca, AVG(vra.factor_quiebre) as factor_quiebre_prom
            FROM omicronvt.dbo.vel_real_articulo vra
            JOIN msgestion01art.dbo.articulo a ON a.codigo_sinonimo = vra.codigo
            GROUP BY a.marca
            """
            quiebre_rows = db_omicronvt.executesql(sql_quiebre, as_dict=True)
            for qr in quiebre_rows:
                qr = _fix_row(qr)
                quiebre_map[qr['marca']] = float(qr.get('factor_quiebre_prom') or 0)
        except Exception:
            pass

        # Merge
        result = []
        margenes = []
        rotaciones = []
        for row in ventas:
            row = _fix_row(row)
            d = {k: _clean(v) for k, v in row.items()}
            marca = d['cod_marca']
            d['marca'] = (d.get('nombre_marca') or 'Marca %s' % marca).strip()
            stock = stock_map.get(marca, 0)
            d['stock_total'] = stock
            d['rotacion'] = d['uds_12m'] / stock if stock > 0 else 99.0
            d['factor_quiebre'] = round(quiebre_map.get(marca, 0), 2)

            # Exclude anomalous margins (e.g. GTN-like)
            if d.get('margen_pct', 0) < -50:
                continue

            margenes.append(d['margen_pct'])
            rotaciones.append(d['rotacion'])
            result.append(d)

        med_margen = _median(margenes)
        med_rotacion = _median(rotaciones)

        for d in result:
            m = d.get('margen_pct', 0)
            r = d.get('rotacion', 0)
            if m >= med_margen and r >= med_rotacion:
                d['clasificacion'] = 'ESTRELLA'
            elif m >= med_margen and r < med_rotacion:
                d['clasificacion'] = 'VACA'
            elif m < med_margen and r >= med_rotacion:
                d['clasificacion'] = 'INTERROGACION'
            else:
                d['clasificacion'] = 'PERRO'

        return result, med_margen, med_rotacion

    cached = cache.ram('bcg_matrix_v2', _fetch, 3600)
    data, med_margen, med_rotacion = cached

    return dict(
        data_json=json.dumps(data),
        mediana_margen=round(med_margen, 1),
        mediana_rotacion=round(med_rotacion, 2),
    )


def proveedores_roi():
    """ROI por proveedor: compras vs ventas 12m."""
    _requiere_acceso()

    # Proveedores de gastos a excluir
    PROVEEDORES_EXCLUIR = (1158, 1527, 1494, 1261, 908)

    def _fetch():
        # Query 1: Compras 12m
        sql_compras = """
        SELECT TOP 30 c2.cuenta as cod_proveedor, c2.denominacion as proveedor,
               SUM(c1.cantidad) as uds_compradas, SUM(c1.cantidad * c1.precio) as monto_compra
        FROM msgestionC.dbo.compras2 c2
        JOIN msgestionC.dbo.compras1 c1 ON c1.codigo=c2.codigo AND c1.letra=c2.letra AND c1.sucursal=c2.sucursal AND c1.numero=c2.numero AND c1.orden=c2.orden
        WHERE c2.fecha_comprobante >= DATEADD(MONTH, -12, GETDATE()) AND c1.operacion='+'
        GROUP BY c2.cuenta, c2.denominacion ORDER BY SUM(c1.cantidad * c1.precio) DESC
        """
        compras = dbC.executesql(sql_compras, as_dict=True)

        # Query 2: Ventas por proveedor
        sql_ventas = """
        SELECT a.proveedor as cod_proveedor, SUM(v.cantidad) as uds_vendidas,
               SUM(v.total_item) as venta_total, SUM(v.precio_costo * v.cantidad) as costo_venta,
               CASE WHEN SUM(v.total_item)>0 THEN (SUM(v.total_item)-SUM(v.precio_costo*v.cantidad))*100.0/SUM(v.total_item) ELSE 0 END as margen_pct
        FROM msgestionC.dbo.ventas1 v JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.fecha >= DATEADD(MONTH, -12, GETDATE()) AND v.codigo NOT IN (7,36) AND a.marca NOT IN (1316,1317,1158,436) AND v.cantidad > 0
        GROUP BY a.proveedor HAVING SUM(v.total_item) > 500000 ORDER BY SUM(v.total_item) DESC
        """
        ventas = dbC.executesql(sql_ventas, as_dict=True)
        venta_map = {}
        for vr in ventas:
            vr = _fix_row(vr)
            venta_map[vr['cod_proveedor']] = {k: _clean(v) for k, v in vr.items()}

        result = []
        for row in compras:
            row = _fix_row(row)
            d = {k: _clean(v) for k, v in row.items()}
            cod = d['cod_proveedor']

            if cod in PROVEEDORES_EXCLUIR:
                continue

            v = venta_map.get(cod, {})
            d['uds_vendidas'] = v.get('uds_vendidas', 0)
            d['venta_total'] = v.get('venta_total', 0)
            d['margen_pct'] = round(v.get('margen_pct', 0), 1)
            d['costo_venta'] = v.get('costo_venta', 0)

            monto = d.get('monto_compra', 0) or 1
            d['rotacion'] = round(d['uds_vendidas'] / max(d['uds_compradas'], 1), 2) if d.get('uds_compradas') else 0
            d['roi'] = round((d['venta_total'] - monto) * 100.0 / monto, 1) if monto > 0 else 0

            if d['roi'] >= 100:
                d['clasificacion'] = 'AUTO-FINANCIADO'
            elif d['roi'] >= 30:
                d['clasificacion'] = 'MODERADO'
            else:
                d['clasificacion'] = 'INTENSIVO'

            result.append(d)

        return result

    data = cache.ram('proveedores_roi_data', _fetch, 3600)

    total_compras = sum(r.get('monto_compra', 0) or 0 for r in data)
    roi_prom = sum(r.get('roi', 0) for r in data) / max(len(data), 1)
    auto_fin = sum(1 for r in data if r.get('clasificacion') == 'AUTO-FINANCIADO')

    return dict(
        data_json=json.dumps(data),
        total_compras=total_compras,
        roi_promedio=round(roi_prom, 1),
        auto_financiados=auto_fin,
    )
