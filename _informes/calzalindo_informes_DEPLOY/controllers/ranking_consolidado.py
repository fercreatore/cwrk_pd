# -*- coding: utf-8 -*-
"""
Ranking de Marcas Consolidado — CONTROLLER NUEVO
=================================================
Reescritura completa del módulo informes_consolidados de objetivos-luciano.

Views:
  RC0001 - rank_marcas: Ranking de marcas (compras+ventas+stock por depo)
  RC0002 - rank_productos: Ranking de productos por marca
  RC0003 - producto_curva: Curva de un producto (detalle por talle)
  RC0004 - producto_pedido: Sugerencia de pedido para un producto (NUEVO)
  RC0005 - marca_pedido: Análisis de pedido completo para una marca (NUEVO)
  RC0006 - api_quiebre: API JSON para quiebre de un CSR (NUEVO)

Depende de: models/funciones_ranking.py, models/db_access.py, models/cer.py

Correcciones aplicadas:
  E01: Ventas filtran codigo NOT IN (7,36)
  E02: Quiebre 12 meses
  E03/E04: Stock filtrado por depos_para_informes
  E05: Velocidad real (ajustada por quiebre)
  E06: Factor estacional
  E07: Temporada unificada
  E08: Sin código duplicado/sobreescrito
  E12: Funciones genéricas (sin duplicación)
  E15: Sugerencia de pedido
  E16: Curva mínima por talle
  E17: Precios CER

Autor: Cowork + Claude — Marzo 2026
"""

import json
import pandas as pd
import datetime
from dateutil.relativedelta import relativedelta


# ============================================================================
# RC0001 — RANKING DE MARCAS
# ============================================================================

def rank_marcas():
    """
    Ranking de marcas: compras + ventas + stock, con distribución por depósito.
    FIX E01: Ventas excluyen codigo 7 Y 36.
    FIX E03: Stock filtrado por DEPOS_INFORMES.
    """
    _requiere_acceso()

    data = data_graf = desde = hasta = clxs = ""

    form = SQLFORM.factory(
        Field('desde', 'date', requires=IS_DATE()),
        Field('hasta', 'date', requires=IS_DATE()),
        Field('c_desde', 'date', label='Compras desde', requires=IS_EMPTY_OR(IS_DATE())),
        Field('c_hasta', 'date', label='Compras hasta', requires=IS_EMPTY_OR(IS_DATE())),
        Field('linea', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'lineas.codigo', '%(descripcion)s', multiple=True))),
        Field('marca', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'marcas.codigo', '%(descripcion)s', multiple=True))),
        Field('rubro', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'rubros.codigo', '%(descripcion)s', multiple=True))),
        Field('subrubro', requires=IS_EMPTY_OR(IS_IN_DB(db1, 'subrubro.codigo', '%(descripcion)s', multiple=True))),
        Field('agrupador_marca', requires=IS_EMPTY_OR(IS_IN_DB(db_omicronvt, 'agrupador_marca', '%(nombre)s'))),
        Field('agrupador_subrubro', requires=IS_EMPTY_OR(IS_IN_DB(db_omicronvt, 'agrupador_subrubro', '%(nombre)s'))),
        Field('agrupador_rubro', requires=IS_EMPTY_OR(IS_IN_DB(db_omicronvt, 'agrupador_rubro', '%(nombre)s'))),
        Field('sinonimo', 'string', label='Código sinónimo'),
        Field('descripcion', 'string', label='Descripción'),
    )

    if form.process().accepted:
        desde = form.vars.desde
        hasta = form.vars.hasta
        c_desde = form.vars.c_desde or desde
        c_hasta = form.vars.c_hasta or hasta

        # Parsear filtros
        filtros = _parsear_filtros_form(form)

        # Guardar params en session para sub-informes
        session.ranking_vars = {
            'desde': str(desde), 'hasta': str(hasta),
            'c_desde': str(c_desde), 'c_hasta': str(c_hasta),
            'filtros': filtros
        }

        # Queries
        ventas = get_ventas_por_marca(desde, hasta, **filtros)
        compras = get_compras_por_marca(c_desde, c_hasta, **filtros)
        stock = get_stock_por_marca(**filtros)

        # DataFrames
        dfv = pd.DataFrame(ventas) if ventas else pd.DataFrame()
        dfc = pd.DataFrame(compras) if compras else pd.DataFrame()
        dfs = pd.DataFrame(stock) if stock else pd.DataFrame()

        if not dfv.empty:
            dfv['cant'] = dfv['cant'].astype(float)
            dfv['total_vent'] = dfv['total_vent'].astype(float)
            dfv['costo_vent'] = dfv['costo_vent'].astype(float)

            # Totales por marca (all depos)
            dfv_total = dfv.groupby(['marca', 'descripcion']).agg({
                'cant': 'sum', 'total_vent': 'sum', 'costo_vent': 'sum'
            }).reset_index()
            dfv_total.columns = ['marca', 'descripcion', 'cantidad_v', 'total_v', 'costo_v']

            # Distribución por depo
            dfv_total_gral = dfv.groupby('marca')['cant'].sum()
            dfv_depo = dfv.pivot_table(index='marca', columns='deposito',
                                        values='cant', aggfunc='sum').fillna(0)
            for col in dfv_depo.columns:
                pct_col = 'pct_d%s' % int(col)
                dfv_depo[pct_col] = (dfv_depo[col] / dfv_total_gral * 100).round(1)
            dfv_depo = dfv_depo.reset_index()

        if not dfc.empty:
            dfc['cant'] = dfc['cant'].astype(float)
            dfc['total_comp'] = dfc['total_comp'].astype(float).fillna(0)
            dfc['total_devs'] = dfc['total_devs'].astype(float).fillna(0)
            dfc['neto_c'] = dfc['total_comp'] - dfc['total_devs']
            dfc_total = dfc.rename(columns={'cant': 'cantidad_c'})

        # Merge
        if not dfv.empty and not dfc.empty:
            merged = pd.merge(dfv_total, dfc_total[['marca', 'cantidad_c', 'neto_c']],
                              on='marca', how='outer').fillna(0)
        elif not dfv.empty:
            merged = dfv_total.copy()
            merged['cantidad_c'] = 0
            merged['neto_c'] = 0
        elif not dfc.empty:
            merged = dfc_total[['marca', 'descripcion', 'cantidad_c', 'neto_c']].copy()
            merged['cantidad_v'] = 0
            merged['total_v'] = 0
            merged['costo_v'] = 0
        else:
            merged = pd.DataFrame()

        if not merged.empty:
            # Rentabilidad
            merged['rent'] = merged.apply(
                lambda r: round((r['total_v'] - r['costo_v']) / r['total_v'] * 100, 1)
                if r['total_v'] > 0 else 0, axis=1)

            # Stock total por marca
            if not dfs.empty:
                dfs['stock'] = dfs['stock'].astype(float)
                stock_total = dfs.groupby('marca')['stock'].sum().reset_index()
                merged = pd.merge(merged, stock_total, on='marca', how='left').fillna(0)
            else:
                merged['stock'] = 0

            data = merged.to_json(orient='records')

            # Columnas para Tabulator
            clxs = (
                "{formatter:'rownum'},"
                "{title:'Marca', field:'descripcion', sorter:'string', headerFilter:true},"
                "{title:'Cant.V', field:'cantidad_v', sorter:'number', topCalc:'sum'},"
                "{title:'$Ventas', field:'total_v', sorter:'number', topCalc:'sum', "
                " formatter:'money', formatterParams:{precision:0}},"
                "{title:'Rent%', field:'rent', sorter:'number'},"
                "{title:'Cant.C', field:'cantidad_c', sorter:'number', topCalc:'sum'},"
                "{title:'$Compras', field:'neto_c', sorter:'number', topCalc:'sum', "
                " formatter:'money', formatterParams:{precision:0}},"
                "{title:'Stock', field:'stock', sorter:'number', topCalc:'sum'},"
            )

    return dict(
        id_informe='RC0001', form=form, data=data, clxs=clxs,
        desde=desde, hasta=hasta
    )


# ============================================================================
# RC0002 — RANKING DE PRODUCTOS POR MARCA
# ============================================================================

def rank_productos():
    """
    Ranking de productos por marca con stock por depo, gráficos y quiebre.
    FIX E01, E03, E05, E06, E08, E12.
    """
    _requiere_acceso()

    marca = request.args(0)
    if not marca:
        redirect(URL('ranking_consolidado', 'rank_marcas'))

    marca = int(marca)
    sv = session.ranking_vars or {}
    desde = sv.get('desde', str(datetime.date.today() - relativedelta(months=6)))
    hasta = sv.get('hasta', str(datetime.date.today()))
    c_desde = sv.get('c_desde', desde)
    c_hasta = sv.get('c_hasta', hasta)
    filtros = sv.get('filtros', {})
    filtros['marca'] = marca

    # Queries
    ventas = get_ventas_por_producto(desde, hasta, **filtros)
    compras = get_compras_por_producto(c_desde, c_hasta, **filtros)
    stock_data = get_stock_por_producto(marca)
    distrib = get_distrib_ventas_xmarca(marca, **filtros)

    # DataFrames
    dfv = pd.DataFrame(ventas) if ventas else pd.DataFrame(columns=['cant', 'csr'])
    dfc = pd.DataFrame(compras) if compras else pd.DataFrame(columns=['cant', 'csr'])
    dfs = pd.DataFrame(stock_data) if stock_data else pd.DataFrame(columns=['stock', 'deposito', 'csr'])

    if not dfv.empty:
        dfv['cant'] = dfv['cant'].astype(float)
    if not dfc.empty:
        dfc['cant'] = dfc['cant'].astype(float)
        dfc['total_comp'] = dfc['total_comp'].astype(float).fillna(0)
        dfc['total_devs'] = dfc['total_devs'].astype(float).fillna(0)

    # Merge ventas + compras
    merged = pd.merge(
        dfv.rename(columns={'cant': 'cantidad_v'}),
        dfc.rename(columns={'cant': 'cantidad_c'}),
        on='csr', how='outer'
    ).fillna(0)

    if not merged.empty:
        # Stock total por CSR
        if not dfs.empty:
            dfs['stock'] = dfs['stock'].astype(float)
            stock_total = dfs.groupby('csr')['stock'].sum().reset_index()
            merged = pd.merge(merged, stock_total, on='csr', how='left').fillna(0)

            # Stock por depo (pivot)
            stock_depo = dfs.pivot_table(index='csr', columns='deposito',
                                          values='stock', aggfunc='sum').fillna(0)
            stock_depo.columns = ['stk_d%s' % int(c) for c in stock_depo.columns]
            stock_depo = stock_depo.reset_index()
            merged = pd.merge(merged, stock_depo, on='csr', how='left').fillna(0)
        else:
            merged['stock'] = 0

        # Agregar descripciones, imágenes, numeración
        merged['descripcion'] = merged['csr'].apply(
            lambda c: _get_descripcion_csr(c))
        merged['imagen'] = merged['csr'].apply(
            lambda c: get_imagen_mini_safe(c))
        merged['numeracion'] = merged['csr'].apply(
            lambda c: get_numeracion_csr(c))

        # vel_real por CSR (batch, usa vel_real.py auto-loaded como model)
        try:
            csrs_list = merged['csr'].tolist()
            quiebres = analizar_quiebre_batch_dal(csrs_list)
            merged['vel_real'] = merged['csr'].apply(
                lambda c: quiebres.get(c, {}).get('vel_real', 0))
            merged['vel_aparente'] = merged['csr'].apply(
                lambda c: quiebres.get(c, {}).get('vel_aparente', 0))
            merged['factor_quiebre'] = merged['csr'].apply(
                lambda c: quiebres.get(c, {}).get('factor_quiebre', 1.0))
            merged['pct_quiebre'] = merged['csr'].apply(
                lambda c: quiebres.get(c, {}).get('pct_quiebre', 0))
            # Marcar sub-comprados (factor_quiebre > 2x)
            merged['alerta_quiebre'] = merged['factor_quiebre'].apply(
                lambda f: 'SUB-COMPRADO %.1fx' % f if f >= 2.0 else '')
            # Reordenar por vel_real descendente
            merged = merged.sort_values('vel_real', ascending=False).reset_index(drop=True)
        except Exception:
            merged['vel_real'] = 0
            merged['vel_aparente'] = 0
            merged['factor_quiebre'] = 1.0
            merged['pct_quiebre'] = 0
            merged['alerta_quiebre'] = ''

        data = merged.to_json(orient='records')
    else:
        data = '[]'

    # Guardar CSR info en session para producto_curva
    session.ranking_marca = marca
    session.ranking_fechas = {
        'desde': desde, 'hasta': hasta, 'c_desde': c_desde, 'c_hasta': c_hasta
    }

    # Gráficos
    ventas_am = get_ventas_anmes(**filtros)
    compras_am = get_compras_anmes(**filtros)

    hc_graf1 = build_series_anmes(ventas_am, compras_am)
    hc_graf2 = build_series_mensual(ventas_am, compras_am)
    hc_graf3 = build_series_temporada(ventas_am, compras_am)
    hc_graf4 = build_ponderado_generico(c_desde, c_hasta, desde, hasta,
                                         'subrubro', 'subrubro', **filtros)
    hc_graf5 = build_ponderado_generico(c_desde, c_hasta, desde, hasta,
                                         'rubro', 'rubros', **filtros)

    # Nombre de marca
    try:
        marca_nombre = db1.executesql(
            "SELECT descripcion FROM marcas WHERE codigo=%s" % marca)[0][0]
    except Exception:
        marca_nombre = 'Marca %s' % marca

    return dict(
        id_informe='RC0002', data=data, marca=marca_nombre, cod_marca=marca,
        hc_graf1=hc_graf1, hc_graf2=hc_graf2, hc_graf3=hc_graf3,
        hc_graf4=hc_graf4, hc_graf5=hc_graf5,
        desde=desde, hasta=hasta
    )


# ============================================================================
# RC0003 — CURVA DE PRODUCTO (detalle por talle)
# ============================================================================

def producto_curva():
    """
    Detalle de un producto: compras+ventas+stock por talle, con quiebre mejorado.
    FIX E01, E02, E04, E05, E06.
    """
    _requiere_acceso()

    csr = request.args(0)
    if not csr or len(csr) < 10:
        redirect(URL('ranking_consolidado', 'rank_marcas'))

    sv = session.ranking_fechas or {}
    desde = sv.get('desde', str(datetime.date.today() - relativedelta(months=6)))
    hasta = sv.get('hasta', str(datetime.date.today()))
    c_desde = sv.get('c_desde', desde)
    c_hasta = sv.get('c_hasta', hasta)

    # Datos por talle
    ventas = get_ventas_curva(desde, hasta, csr)
    compras = get_compras_curva(c_desde, c_hasta, csr)
    stock_data = get_stock_curva(csr)

    dfv = pd.DataFrame(ventas) if ventas else pd.DataFrame()
    dfc = pd.DataFrame(compras) if compras else pd.DataFrame()
    dfs = pd.DataFrame(stock_data) if stock_data else pd.DataFrame()

    # Agrupar por talle (codigo_sinonimo)
    tabledata = []

    if not dfv.empty:
        dfv['cant'] = dfv['cant'].astype(float)
        dfv_grp = dfv.groupby(['codigo_sinonimo', 'descripcion_5']).agg({
            'cant': 'sum', 'total_vent': 'sum', 'total_devs': 'sum'
        }).reset_index()
    else:
        dfv_grp = pd.DataFrame(columns=['codigo_sinonimo', 'descripcion_5', 'cant'])

    if not dfc.empty:
        dfc['cant'] = dfc['cant'].astype(float)
        dfc_grp = dfc.groupby(['codigo_sinonimo', 'descripcion_5']).agg({
            'cant': 'sum', 'total_comp': 'sum', 'total_devs': 'sum'
        }).reset_index()
    else:
        dfc_grp = pd.DataFrame(columns=['codigo_sinonimo', 'descripcion_5', 'cant'])

    # Merge
    merged = pd.merge(
        dfv_grp.rename(columns={'cant': 'cant_v', 'total_vent': 'total_v', 'total_devs': 'devs_v'}),
        dfc_grp.rename(columns={'cant': 'cant_c', 'total_comp': 'total_c', 'total_devs': 'devs_c'}),
        on=['codigo_sinonimo', 'descripcion_5'], how='outer'
    ).fillna(0)

    # Stock por talle
    if not dfs.empty:
        dfs_dict = {r['codigo_sinonimo']: float(r['stock'] or 0) for _, r in dfs.iterrows()}
    else:
        dfs_dict = {}

    merged['stock_actual'] = merged['codigo_sinonimo'].map(dfs_dict).fillna(0)

    # QUIEBRE MEJORADO por talle (FIX E02)
    for idx, row in merged.iterrows():
        cs = row['codigo_sinonimo']
        try:
            q = calcular_quiebre_mensual(cs, meses=12)
            merged.at[idx, 'veces_quebrado'] = q['meses_quebrado']
            merged.at[idx, 'pct_quiebre'] = q['pct_quiebre']
            merged.at[idx, 'vel_aparente'] = q['vel_aparente']
            merged.at[idx, 'vel_real'] = q['vel_real']
            merged.at[idx, 'stock_inicial'] = q['detalle_mensual'][0]['stock_inicio'] if q['detalle_mensual'] else 0

            # Proyección FIX E05+E06
            factores = calcular_factor_estacional(cs)
            mes_actual = datetime.date.today().month
            factor = factores.get(mes_actual, 1.0)
            merged.at[idx, 'factor_estacional'] = factor
            merged.at[idx, 'vel_ajustada'] = q['vel_real'] * factor

            # Cobertura
            vel_adj = q['vel_real'] * factor
            merged.at[idx, 'cobertura'] = round(
                row['stock_actual'] / vel_adj, 1) if vel_adj > 0 else 999

        except Exception:
            merged.at[idx, 'veces_quebrado'] = 0
            merged.at[idx, 'pct_quiebre'] = 0
            merged.at[idx, 'vel_aparente'] = 0
            merged.at[idx, 'vel_real'] = 0
            merged.at[idx, 'stock_inicial'] = 0
            merged.at[idx, 'factor_estacional'] = 1.0
            merged.at[idx, 'vel_ajustada'] = 0
            merged.at[idx, 'cobertura'] = 999

    # Último precio compra por talle
    merged['ultimo_precio'] = merged['codigo_sinonimo'].apply(
        lambda cs: get_ultimo_precio_compra(cs[:10])['precio_cer'])

    data = merged.to_json(orient='records')

    # Gráficos por talle
    filtros_csr = {'marca': 0, 'linea': None, 'rubro': None, 'subrubro': None,
                   'agrupador_marca': 0, 'agrupador_subrubro': 0, 'agrupador_rubro': 0,
                   'sinonimo': None, 'descripcion': None}
    ventas_am = get_ventas_anmes(csr=csr, **filtros_csr)
    compras_am = get_compras_anmes(csr=csr, **filtros_csr)

    hc_graf1 = build_series_anmes(ventas_am, compras_am)
    hc_graf2 = build_series_mensual(ventas_am, compras_am)
    hc_graf3 = build_series_temporada(ventas_am, compras_am)

    # Curva ideal (% por talle)
    if not merged.empty and merged['cant_v'].sum() > 0:
        total_v = merged['cant_v'].sum()
        curva_ideal = merged[['descripcion_5', 'cant_v']].copy()
        curva_ideal['pct'] = (curva_ideal['cant_v'] / total_v * 100).round(1)
        hc_curva = json.dumps([{
            'name': 'Distribución ideal',
            'data': curva_ideal[['descripcion_5', 'pct']].values.tolist()
        }])
    else:
        hc_curva = '[]'

    # Info del producto
    try:
        info = db1.executesql(
            "SELECT TOP 1 descripcion_1, marca FROM articulo "
            "WHERE codigo_sinonimo LIKE '%s%%'" % csr, as_dict=True)[0]
        descripcion = info['descripcion_1']
    except Exception:
        descripcion = csr

    # Guardar timestamp para link art_comp_vent
    session.informe_000 = [desde, hasta, c_desde, c_hasta]

    return dict(
        id_informe='RC0003', data=data, csr=csr, descripcion=descripcion,
        hc_graf1=hc_graf1, hc_graf2=hc_graf2, hc_graf3=hc_graf3,
        hc_curva=hc_curva, desde=desde, hasta=hasta
    )


# ============================================================================
# RC0004 — SUGERENCIA DE PEDIDO PARA UN PRODUCTO (NUEVO)
# ============================================================================

def producto_pedido():
    """
    NEW E15+E16: Genera sugerencia de pedido por talle para un CSR.
    """
    _requiere_acceso()

    csr = request.args(0)
    cobertura = int(request.vars.cobertura or 3)

    if not csr or len(csr) < 10:
        return dict(error='CSR inválido')

    # Análisis completo
    pedido = calcular_pedido_sugerido(csr, cobertura_meses=cobertura)

    # Curva mínima por talle
    curva = []
    if pedido['pedir'] > 0:
        curva = calcular_curva_minima(csr, pedido['pedir'])

    # Precio
    precio = get_ultimo_precio_compra(csr)

    # Descripción
    try:
        desc = db1.executesql(
            "SELECT TOP 1 descripcion_1 FROM articulo "
            "WHERE codigo_sinonimo LIKE '%s%%'" % csr)[0][0]
    except Exception:
        desc = csr

    return dict(
        id_informe='RC0004',
        csr=csr,
        descripcion=desc,
        pedido=pedido,
        curva=curva,
        precio=precio,
        monto_total=round(pedido['pedir'] * precio['precio_cer'], 2),
        cobertura_objetivo=cobertura
    )


# ============================================================================
# RC0005 — ANÁLISIS DE PEDIDO COMPLETO PARA MARCA (NUEVO)
# ============================================================================

def marca_pedido():
    """
    NEW E15: Análisis de pedido completo para todos los productos de una marca.
    """
    _requiere_acceso()

    marca = request.args(0)
    cobertura = int(request.vars.cobertura or 3)

    if not marca:
        redirect(URL('ranking_consolidado', 'rank_marcas'))

    marca = int(marca)

    # Análisis
    resultados = analizar_marca_para_pedido(marca, cobertura_meses=cobertura)

    # Resumen
    total_pedir = sum(r.get('pedir', 0) for r in resultados if 'error' not in r)
    total_monto = sum(r.get('monto_pedir', 0) for r in resultados if 'error' not in r)
    productos_con_quiebre = sum(1 for r in resultados
                                 if 'error' not in r and r.get('pct_quiebre', 0) > 0)
    productos_pedir = sum(1 for r in resultados
                          if 'error' not in r and r.get('pedir', 0) > 0)

    # Nombre de marca
    try:
        marca_nombre = db1.executesql(
            "SELECT descripcion FROM marcas WHERE codigo=%s" % marca)[0][0]
    except Exception:
        marca_nombre = 'Marca %s' % marca

    return dict(
        id_informe='RC0005',
        marca=marca_nombre,
        cod_marca=marca,
        resultados=resultados,
        resumen={
            'total_productos': len(resultados),
            'productos_con_quiebre': productos_con_quiebre,
            'productos_pedir': productos_pedir,
            'total_pedir': total_pedir,
            'total_monto': round(total_monto, 0),
            'cobertura_objetivo': cobertura
        },
        data_json=json.dumps(resultados, default=str)
    )


# ============================================================================
# RC0006 — API JSON PARA QUIEBRE (NUEVO)
# ============================================================================

def api_quiebre():
    """
    API JSON: retorna análisis de quiebre para un CSR.
    Uso: /ranking_consolidado/api_quiebre/2364950002
    """
    _requiere_acceso()

    csr = request.args(0)
    meses = int(request.vars.meses or 12)

    if not csr:
        return response.json({'error': 'CSR requerido'})

    try:
        resultado = calcular_quiebre_mensual(csr, meses=meses)
        return response.json(resultado)
    except Exception as e:
        return response.json({'error': str(e)})


# ============================================================================
# UTILIDADES INTERNAS
# ============================================================================

def _parsear_filtros_form(form):
    """Extrae filtros del form y los convierte al formato esperado por funciones_ranking."""
    filtros = {
        'linea': None, 'marca': None, 'rubro': None, 'subrubro': None,
        'agrupador_marca': 0, 'agrupador_subrubro': 0, 'agrupador_rubro': 0,
        'sinonimo': None, 'descripcion': None
    }

    if form.vars.linea:
        filtros['linea'] = int(form.vars.linea[0]) if len(form.vars.linea) == 1 \
            else ','.join(form.vars.linea)
    if form.vars.marca:
        filtros['marca'] = int(form.vars.marca[0]) if len(form.vars.marca) == 1 \
            else ','.join(form.vars.marca)
    if form.vars.rubro:
        filtros['rubro'] = int(form.vars.rubro[0]) if len(form.vars.rubro) == 1 \
            else ','.join(form.vars.rubro)
    if form.vars.subrubro:
        filtros['subrubro'] = int(form.vars.subrubro[0]) if len(form.vars.subrubro) == 1 \
            else ','.join(form.vars.subrubro)

    if form.vars.agrupador_marca:
        filtros['agrupador_marca'] = int(form.vars.agrupador_marca)
    if form.vars.agrupador_subrubro:
        filtros['agrupador_subrubro'] = int(form.vars.agrupador_subrubro)
    if form.vars.agrupador_rubro:
        filtros['agrupador_rubro'] = int(form.vars.agrupador_rubro)

    if form.vars.sinonimo:
        filtros['sinonimo'] = form.vars.sinonimo
    if form.vars.descripcion:
        filtros['descripcion'] = form.vars.descripcion

    return filtros


def _get_descripcion_csr(csr):
    """Obtiene descripcion_1 para un CSR."""
    try:
        return db1.executesql(
            "SELECT TOP 1 descripcion_1 FROM articulo "
            "WHERE codigo_sinonimo LIKE '%s%%'" % csr
        )[0][0]
    except Exception:
        return csr
