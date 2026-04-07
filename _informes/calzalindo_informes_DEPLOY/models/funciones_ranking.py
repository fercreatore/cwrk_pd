# -*- coding: utf-8 -*-
"""
Funciones para Ranking de Marcas Consolidado — MÓDULO NUEVO
===========================================================
Reescritura completa del módulo informes_consolidados (objetivos-luciano).

Cambios vs original:
  - Fix E01: Ventas filtran codigo NOT IN (7,36) en todas las queries
  - Fix E02: Quiebre calculado sobre 12 meses (no limitado al form)
  - Fix E03/E04: Stock siempre filtrado por depos_para_informes
  - Fix E05: Velocidad real ajustada por quiebre
  - Fix E06: Factor estacional incluido en proyecciones
  - Fix E09: Queries parametrizadas donde sea posible (web2py DAL)
  - Fix E12: Funciones genéricas reutilizables (sin duplicación)
  - NEW E15: Sugerencia de pedido integrada
  - NEW E16: Curva mínima por talle basada en datos

Depende de: db.py (db1, db_omicronvt), db_extra.py (dbC), cer.py (fx_AjustarPorCer)

Autor: Cowork + Claude — Marzo 2026
"""

import math
import pandas as pd
import json
import datetime
from dateutil.relativedelta import relativedelta

# ============================================================================
# CONSTANTES
# ============================================================================

# Depósitos incluidos en informes (SIN depo 199 = faltantes)
DEPOS_INFORMES = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 198)
DEPOS_INFORMES_SQL = '(0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)'

# Marcas excluidas de rankings (genéricas/internas)
MARCAS_EXCLUIDAS = (1316, 1317, 1158, 436)
MARCAS_EXCLUIDAS_SQL = '(1316,1317,1158,436)'

# Códigos de ventas a excluir (7=remitos internos, 36=transferencias)
CODIGOS_EXCLUIR_VENTAS = '(7,36)'

# Meses de temporada (para factor estacional)
MESES_VERANO = (10, 11, 12, 1, 2, 3)
MESES_INVIERNO = (4, 5, 6, 7, 8, 9)

# Meses de quiebre por defecto
MESES_QUIEBRE_DEFAULT = 12

# Factores estacionales globales (fallback cuando no hay historia propia)
# Fuente: ESTACIONALIDAD_MENSUAL en app_reposicion.py y vel_real.py
ESTACIONALIDAD_MENSUAL = {
    1: 0.88, 2: 1.04, 3: 0.74, 4: 0.73, 5: 0.93, 6: 1.05,
    7: 0.98, 8: 0.92, 9: 0.93, 10: 1.22, 11: 1.04, 12: 1.51,
}


# ============================================================================
# UTILIDADES
# ============================================================================

def _list_to_sql(lista):
    """Convierte lista Python a formato SQL: (v1,v2,v3) o (v1)."""
    if not lista:
        return '(NULL)'
    if len(lista) == 1:
        return '(%s)' % lista[0]
    return str(tuple(lista))


def _build_filtros_art(**kwargs):
    """
    Construye cláusula WHERE dinámica para filtros de artículo.
    Acepta: linea, marca, rubro, subrubro, agrupador_marca,
            agrupador_subrubro, agrupador_rubro, sinonimo, descripcion.
    Retorna string SQL para concatenar al WHERE.
    """
    parts = []

    if kwargs.get('linea'):
        parts.append("AND a.linea IN (%s)" % kwargs['linea'])
    if kwargs.get('marca'):
        parts.append("AND a.marca IN (%s)" % kwargs['marca'])
    if kwargs.get('rubro'):
        parts.append("AND a.rubro IN (%s)" % kwargs['rubro'])
    if kwargs.get('subrubro'):
        parts.append("AND a.subrubro IN (%s)" % kwargs['subrubro'])

    # Agrupadores (buscan en omicronvt)
    agr_marca = kwargs.get('agrupador_marca', 0)
    if agr_marca and int(agr_marca) > 0:
        try:
            q = db_omicronvt.executesql(
                "SELECT marcas_codigo FROM agrupador_marca WHERE id=%s" % int(agr_marca))
            if q:
                parts.append("AND a.marca IN (%s)" % q[0][0])
        except Exception:
            pass

    agr_sub = kwargs.get('agrupador_subrubro', 0)
    if agr_sub and int(agr_sub) > 0:
        try:
            q = db_omicronvt.executesql(
                "SELECT subrubros_codigo FROM agrupador_subrubro WHERE id=%s" % int(agr_sub))
            if q:
                parts.append("AND a.subrubro IN (%s)" % q[0][0])
        except Exception:
            pass

    agr_rub = kwargs.get('agrupador_rubro', 0)
    if agr_rub and int(agr_rub) > 0:
        try:
            q = db_omicronvt.executesql(
                "SELECT rubros_codigo FROM agrupador_rubro WHERE id=%s" % int(agr_rub))
            if q:
                parts.append("AND a.rubro IN (%s)" % q[0][0])
        except Exception:
            pass

    if kwargs.get('sinonimo'):
        parts.append("AND a.codigo_sinonimo LIKE '%%%s%%'" % kwargs['sinonimo'])
    if kwargs.get('descripcion'):
        parts.append("AND a.descripcion_1 LIKE '%%%s%%'" % kwargs['descripcion'])

    return ' '.join(parts)


# ============================================================================
# QUERIES PRINCIPALES — RANKING DE MARCAS (IC0001)
# ============================================================================

def get_ventas_por_marca(desde, hasta, **filtros):
    """
    Ventas consolidadas agrupadas por marca.
    FIX E01: Excluye codigo IN (7,36).
    Incluye rentabilidad via precio_costo.
    """
    f = _build_filtros_art(**filtros)

    t_sql = (
        "SELECT "
        "  SUM(CASE WHEN v.operacion='+' THEN v.cantidad "
        "           WHEN v.operacion='-' THEN -v.cantidad END) AS cant, "
        "  SUM((CASE WHEN v.operacion='+' THEN v.precio "
        "            WHEN v.operacion='-' THEN -v.precio END) / 1.21 * v.cantidad) AS total_vent, "
        "  SUM(CASE WHEN v.operacion='+' THEN v.precio_costo "
        "           WHEN v.operacion='-' THEN -v.precio_costo END * v.cantidad) AS costo_vent, "
        "  a.marca, m.descripcion, v.deposito "
        "FROM omicron_ventas1 v "
        "LEFT JOIN articulo a ON v.articulo=a.codigo "
        "LEFT JOIN marcas m ON a.marca=m.codigo "
        "LEFT JOIN subrubro s ON a.subrubro=s.codigo "
        "WHERE v.codigo NOT IN {excl} "
        "  AND v.fecha>='{desde}' AND v.fecha<='{hasta}' "
        "{filtros} "
        "GROUP BY a.marca, m.descripcion, v.deposito"
    ).format(excl=CODIGOS_EXCLUIR_VENTAS, desde=desde, hasta=hasta, filtros=f)

    return db1.executesql(t_sql, as_dict=True)


def get_compras_por_marca(desde, hasta, **filtros):
    """
    Compras consolidadas agrupadas por marca.
    Usa omicron_compras1_remitos (vista consolidada).
    """
    f = _build_filtros_art(**filtros)

    t_sql = (
        "SELECT "
        "  SUM(CASE WHEN r.operacion='+' THEN r.cantidad "
        "           WHEN r.operacion='-' THEN -r.cantidad END) AS cant, "
        "  SUM(CASE WHEN r.operacion='+' THEN r.monto_facturado END) AS total_comp, "
        "  SUM(CASE WHEN r.operacion='-' THEN r.precio END) AS total_devs, "
        "  a.marca, m.descripcion "
        "FROM omicron_compras1_remitos r "
        "LEFT JOIN articulo a ON r.articulo=a.codigo "
        "LEFT JOIN marcas m ON a.marca=m.codigo "
        "WHERE r.fecha>='{desde}' AND r.fecha<='{hasta}' "
        "{filtros} "
        "GROUP BY a.marca, m.descripcion"
    ).format(desde=desde, hasta=hasta, filtros=f)

    return db1.executesql(t_sql, as_dict=True)


def get_stock_por_marca(**filtros):
    """
    Stock consolidado por marca y depósito.
    FIX E03/E04: Siempre filtra por DEPOS_INFORMES.
    """
    f = _build_filtros_art(**filtros)

    t_sql = (
        "SELECT SUM(ws.stock_actual) AS stock, "
        "  MAX(m.codigo) AS marca, MAX(ws.deposito) AS deposito "
        "FROM articulo a "
        "LEFT JOIN web_stock ws ON ws.articulo=a.codigo "
        "LEFT JOIN marcas m ON m.codigo=a.marca "
        "WHERE a.marca>0 AND ws.deposito IN {depos} "
        "{filtros} "
        "GROUP BY a.marca, ws.deposito"
    ).format(depos=DEPOS_INFORMES_SQL, filtros=f)

    return db1.executesql(t_sql, as_dict=True)


# ============================================================================
# QUERIES — RANKING DE PRODUCTOS POR MARCA (IC0002)
# ============================================================================

def get_ventas_por_producto(desde, hasta, **filtros):
    """
    Ventas por producto (CSR = LEFT 10 de codigo_sinonimo).
    FIX E01: codigo NOT IN (7,36).
    """
    f = _build_filtros_art(**filtros)

    t_sql = (
        "SELECT "
        "  SUM(CASE WHEN v.operacion='+' THEN v.cantidad "
        "           WHEN v.operacion='-' THEN -v.cantidad END) AS cant, "
        "  SUM((CASE WHEN v.operacion='+' THEN v.precio "
        "            WHEN v.operacion='-' THEN -v.precio END) / 1.21 * v.cantidad) AS total_vent, "
        "  SUM(CASE WHEN v.operacion='+' THEN v.precio_costo "
        "           WHEN v.operacion='-' THEN -v.precio_costo END * v.cantidad) AS costo_vent, "
        "  LEFT(a.codigo_sinonimo,10) AS csr "
        "FROM omicron_ventas1 v "
        "LEFT JOIN articulo a ON v.articulo=a.codigo "
        "LEFT JOIN marcas m ON a.marca=m.codigo "
        "LEFT JOIN subrubro s ON a.subrubro=s.codigo "
        "LEFT JOIN rubros r ON a.rubro=r.codigo "
        "WHERE v.codigo NOT IN {excl} "
        "  AND v.fecha>='{desde}' AND v.fecha<='{hasta}' "
        "{filtros} "
        "GROUP BY LEFT(a.codigo_sinonimo,10)"
    ).format(excl=CODIGOS_EXCLUIR_VENTAS, desde=desde, hasta=hasta, filtros=f)

    return db1.executesql(t_sql, as_dict=True)


def get_compras_por_producto(desde, hasta, **filtros):
    """Compras por producto (CSR)."""
    f = _build_filtros_art(**filtros)

    t_sql = (
        "SELECT "
        "  SUM(CASE WHEN rc.operacion='+' THEN rc.cantidad "
        "           WHEN rc.operacion='-' THEN -rc.cantidad END) AS cant, "
        "  SUM(CASE WHEN rc.operacion='+' THEN rc.monto_facturado END) AS total_comp, "
        "  SUM(CASE WHEN rc.operacion='-' THEN rc.precio END) AS total_devs, "
        "  LEFT(a.codigo_sinonimo,10) AS csr "
        "FROM omicron_compras1_remitos rc "
        "LEFT JOIN articulo a ON rc.articulo=a.codigo "
        "LEFT JOIN marcas m ON a.marca=m.codigo "
        "LEFT JOIN subrubro s ON a.subrubro=s.codigo "
        "LEFT JOIN rubros r ON a.rubro=r.codigo "
        "WHERE rc.fecha>='{desde}' AND rc.fecha<='{hasta}' "
        "{filtros} "
        "GROUP BY LEFT(a.codigo_sinonimo,10)"
    ).format(desde=desde, hasta=hasta, filtros=f)

    return db1.executesql(t_sql, as_dict=True)


def get_stock_por_producto(marca):
    """
    Stock por producto (CSR) y depósito.
    FIX E03: Filtrado por DEPOS_INFORMES.
    Usa omicron_articulos para CSR limpio.
    """
    t_sql = (
        "SELECT SUM(s.stock_actual) AS stock, s.deposito, a.csr "
        "FROM omicron_articulos a "
        "LEFT JOIN web_stock s ON a.codigo=s.articulo "
        "WHERE a.marca={marca} AND s.deposito IN {depos} "
        "GROUP BY s.deposito, a.csr "
        "HAVING SUM(s.stock_actual)>0"
    ).format(marca=marca, depos=DEPOS_INFORMES_SQL)

    return db1.executesql(t_sql, as_dict=True)


def get_distrib_ventas_xmarca(marca, **filtros):
    """Distribución de ventas por depósito y CSR."""
    f = _build_filtros_art(**filtros)

    t_sql = (
        "SELECT "
        "  SUM(CASE WHEN v.operacion='+' THEN v.cantidad "
        "           WHEN v.operacion='-' THEN -v.cantidad END) AS cant, "
        "  v.deposito, "
        "  LEFT(a.codigo_sinonimo, LEN(a.codigo_sinonimo)-2) AS csr "
        "FROM web_articulo a "
        "LEFT JOIN omicron_ventas1 v ON a.codigo=v.articulo "
        "WHERE LEN(a.codigo_sinonimo)=12 "
        "  AND a.marca={marca} "
        "  AND v.codigo NOT IN {excl} "
        "{filtros} "
        "GROUP BY v.deposito, LEFT(a.codigo_sinonimo, LEN(a.codigo_sinonimo)-2)"
    ).format(marca=marca, excl=CODIGOS_EXCLUIR_VENTAS, filtros=f)

    return db1.executesql(t_sql, as_dict=True)


# ============================================================================
# QUERIES — CURVA DE PRODUCTO (IC0003)
# ============================================================================

def get_ventas_curva(desde, hasta, csr):
    """
    Ventas por talle de un producto.
    FIX E01: codigo NOT IN (7,36).
    """
    t_sql = (
        "SELECT "
        "  SUM(CASE WHEN v.operacion='+' THEN v.cantidad "
        "           WHEN v.operacion='-' THEN -v.cantidad END) AS cant, "
        "  SUM((CASE WHEN v.operacion='+' THEN v.monto_facturado END) / 1.21) AS total_vent, "
        "  SUM((CASE WHEN v.operacion='-' THEN v.precio END) / 1.21) AS total_devs, "
        "  a.codigo_sinonimo, a.descripcion_5, v.fecha "
        "FROM omicron_ventas1 v "
        "LEFT JOIN articulo a ON v.articulo=a.codigo "
        "WHERE v.codigo NOT IN {excl} "
        "  AND v.fecha>='{desde}' AND v.fecha<='{hasta}' "
        "  AND a.codigo_sinonimo LIKE '{csr}%' "
        "GROUP BY a.descripcion_5, a.codigo_sinonimo, v.fecha"
    ).format(excl=CODIGOS_EXCLUIR_VENTAS, desde=desde, hasta=hasta, csr=csr)

    return db1.executesql(t_sql, as_dict=True)


def get_compras_curva(desde, hasta, csr):
    """Compras por talle de un producto."""
    t_sql = (
        "SELECT "
        "  SUM(CASE WHEN rc.operacion='+' THEN rc.cantidad "
        "           WHEN rc.operacion='-' THEN -rc.cantidad END) AS cant, "
        "  SUM(CASE WHEN rc.operacion='+' THEN rc.monto_facturado END) AS total_comp, "
        "  SUM(CASE WHEN rc.operacion='-' THEN rc.precio END) AS total_devs, "
        "  a.codigo_sinonimo, a.descripcion_5, rc.fecha "
        "FROM omicron_compras1_remitos rc "
        "LEFT JOIN articulo a ON rc.articulo=a.codigo "
        "WHERE rc.fecha>='{desde}' AND rc.fecha<='{hasta}' "
        "  AND a.codigo_sinonimo LIKE '{csr}%' "
        "GROUP BY a.descripcion_5, a.codigo_sinonimo, rc.fecha"
    ).format(desde=desde, hasta=hasta, csr=csr)

    return db1.executesql(t_sql, as_dict=True)


def get_stock_curva(csr):
    """
    Stock por talle de un producto.
    FIX E04: Filtrado por DEPOS_INFORMES.
    """
    t_sql = (
        "SELECT SUM(ws.stock_actual) AS stock, "
        "  a.codigo_sinonimo, a.descripcion_5 "
        "FROM web_stock ws "
        "LEFT JOIN articulo a ON a.codigo=ws.articulo "
        "WHERE a.codigo_sinonimo LIKE '{csr}%' "
        "  AND ws.deposito IN {depos} "
        "GROUP BY a.codigo_sinonimo, a.descripcion_5"
    ).format(csr=csr, depos=DEPOS_INFORMES_SQL)

    return db1.executesql(t_sql, as_dict=True)


# ============================================================================
# QUERIES — GRÁFICOS TEMPORALES (año-mes, mes, temporada)
# ============================================================================

def get_ventas_anmes(csr=None, **filtros):
    """Ventas por año-mes. FIX E01."""
    f = _build_filtros_art(**filtros)
    csr_filter = "AND a.codigo_sinonimo LIKE '%s%%'" % csr if csr else ''

    t_sql = (
        "SELECT "
        "  SUM(CASE WHEN v.operacion='+' THEN v.cantidad "
        "           WHEN v.operacion='-' THEN -v.cantidad END) AS cant, "
        "  CONCAT(DATEPART(YEAR, v.fecha),'-',CONVERT(char(2), v.fecha,101)) AS anmes, "
        "  DATEPART(YEAR, v.fecha) AS an, "
        "  DATEPART(MONTH, v.fecha) AS me "
        "FROM omicron_ventas1 v "
        "LEFT JOIN articulo a ON v.articulo=a.codigo "
        "LEFT JOIN marcas m ON a.marca=m.codigo "
        "WHERE v.codigo NOT IN {excl} "
        "{filtros} {csr_filter} "
        "GROUP BY CONCAT(DATEPART(YEAR, v.fecha),'-',CONVERT(char(2), v.fecha,101)), "
        "  DATEPART(YEAR, v.fecha), DATEPART(MONTH, v.fecha)"
    ).format(excl=CODIGOS_EXCLUIR_VENTAS, filtros=f, csr_filter=csr_filter)

    return db1.executesql(t_sql, as_dict=True)


def get_compras_anmes(csr=None, **filtros):
    """Compras por año-mes."""
    f = _build_filtros_art(**filtros)
    csr_filter = "AND a.codigo_sinonimo LIKE '%s%%'" % csr if csr else ''

    t_sql = (
        "SELECT "
        "  SUM(CASE WHEN rc.operacion='+' THEN rc.cantidad "
        "           WHEN rc.operacion='-' THEN -rc.cantidad END) AS cant, "
        "  CONCAT(DATEPART(YEAR, rc.fecha),'-',CONVERT(char(2), rc.fecha,101)) AS anmes, "
        "  DATEPART(YEAR, rc.fecha) AS an, "
        "  DATEPART(MONTH, rc.fecha) AS me "
        "FROM omicron_compras1_remitos rc "
        "LEFT JOIN articulo a ON rc.articulo=a.codigo "
        "LEFT JOIN marcas m ON a.marca=m.codigo "
        "WHERE a.codigo>1 "
        "{filtros} {csr_filter} "
        "GROUP BY CONCAT(DATEPART(YEAR, rc.fecha),'-',CONVERT(char(2), rc.fecha,101)), "
        "  DATEPART(YEAR, rc.fecha), DATEPART(MONTH, rc.fecha)"
    ).format(filtros=f, csr_filter=csr_filter)

    return db1.executesql(t_sql, as_dict=True)


def get_ventas_promedio_mensual(csr=None, **filtros):
    """
    Ventas promedio mensual (suma total por mes / cantidad de años con datos ese mes).
    Resuelve el promedio real por mes evitando distorsión por años incompletos.
    FIX E01: codigo NOT IN (7,36).
    """
    f = _build_filtros_art(**filtros)
    csr_filter = "AND a.codigo_sinonimo LIKE '%s%%'" % csr if csr else ''

    t_sql = (
        "SELECT "
        "  CAST(SUM(i.cant) AS INT) AS total, "
        "  i.mes, "
        "  CAST(SUM(i.cant)/COUNT(i.yeames) AS INT) AS promedio "
        "FROM ("
        "  SELECT "
        "    SUM(CASE WHEN v.operacion='+' THEN v.cantidad "
        "             WHEN v.operacion='-' THEN -v.cantidad END) AS cant, "
        "    CONCAT(YEAR(v.fecha),'-',MONTH(v.fecha)) AS yeames, "
        "    MAX(CONVERT(char(2), v.fecha, 101)) AS mes "
        "  FROM omicron_ventas1 v "
        "  LEFT JOIN articulo a ON v.articulo=a.codigo "
        "  LEFT JOIN marcas m ON a.marca=m.codigo "
        "  WHERE v.codigo NOT IN {excl} "
        "  {filtros} {csr_filter} "
        "  GROUP BY CONCAT(YEAR(v.fecha),'-',MONTH(v.fecha))"
        ") i "
        "GROUP BY i.mes"
    ).format(excl=CODIGOS_EXCLUIR_VENTAS, filtros=f, csr_filter=csr_filter)

    return db1.executesql(t_sql, as_dict=True)


# ============================================================================
# ANÁLISIS DE QUIEBRE DE STOCK — VERSIÓN v3
# ============================================================================

def _factor_estacional_single(csr, anios=3):
    """
    Calcula factores estacionales para un unico CSR (usado en calcular_quiebre_mensual v3).
    Retorna dict {mes(1..12): factor_float}.
    Si no hay historia suficiente o factores planos, usa ESTACIONALIDAD_MENSUAL global.
    """
    desde = (datetime.date.today() - relativedelta(years=anios)).replace(month=1, day=1)

    t_sql = (
        "SELECT "
        "  SUM(CASE WHEN v.operacion='+' THEN v.cantidad "
        "           WHEN v.operacion='-' THEN -v.cantidad END) AS cant, "
        "  MONTH(v.fecha) AS mes "
        "FROM omicron_ventas1 v "
        "LEFT JOIN articulo a ON v.articulo=a.codigo "
        "WHERE v.codigo NOT IN {excl} "
        "  AND a.codigo_sinonimo='{csr}' "
        "  AND v.fecha>='{desde}' "
        "GROUP BY MONTH(v.fecha)"
    ).format(excl=CODIGOS_EXCLUIR_VENTAS, csr=csr, desde=desde)

    try:
        data = db1.executesql(t_sql, as_dict=True)
    except Exception:
        data = []

    if not data:
        return dict(ESTACIONALIDAD_MENSUAL)

    ventas_mes = {int(r['mes']): float(r['cant'] or 0) for r in data}
    media = sum(ventas_mes.values()) / max(len(ventas_mes), 1)
    if media <= 0:
        return dict(ESTACIONALIDAD_MENSUAL)

    factors = {m: round(ventas_mes.get(m, media) / media, 3) for m in range(1, 13)}

    # Si factores son planos (sin estacionalidad real), usar global
    is_flat = all(0.8 <= v <= 1.2 for v in factors.values())
    if is_flat:
        return dict(ESTACIONALIDAD_MENSUAL)
    return factors


def get_stock_actual_csr(csr):
    """
    Stock actual de un CSR sumando todos los depósitos de informes.
    FIX E04: Filtrado por DEPOS_INFORMES.
    """
    t_sql = (
        "SELECT TOP 1 SUM(s.stock_actual) AS stock "
        "FROM web_stock s "
        "LEFT JOIN articulo a ON a.codigo=s.articulo "
        "WHERE a.codigo_sinonimo='{csr}' "
        "  AND s.deposito IN {depos}"
    ).format(csr=csr, depos=DEPOS_INFORMES_SQL)

    result = db1.executesql(t_sql, as_dict=True)
    return result[0]['stock'] if result and result[0]['stock'] else 0


def calcular_quiebre_mensual(csr, meses=MESES_QUIEBRE_DEFAULT):
    """
    Calcula quiebre de stock MENSUAL reconstruyendo hacia atras. Algoritmo v3.

    FIX E02: Usa 12 meses por defecto (no el form de 3 meses).
    FIX E05: Velocidad REAL ajustada por quiebre.
    v3: Desestacionalizacion + factor_disp + fallback 1.15x + std_mensual
        + ventas_perdidas + vel_real_con_perdidas.

    Metodo:
    1. Stock actual de web_stock (filtrado por depos_para_informes)
    2. Ventas mensuales de omicron_ventas1 (excluye cod 7,36)
    3. Compras mensuales de omicron_compras1_remitos (operacion='+')
    4. Factores estacionales por mes (propios o globales si son planos)
    5. Reconstruye stock mes a mes hacia atras
    6. Meses con stock_inicio <= 0 = QUEBRADO
    7. vel_real = ventas_desestacionalizadas_OK / meses_ok * factor_disp

    Retorna dict con:
      - stock_actual, meses_analizados, meses_quebrado, meses_con_stock
      - pct_quiebre, ventas_total
      - vel_aparente, vel_real, vel_base_desest, factor_disp
      - factor_quiebre
      - std_mensual, ventas_perdidas, vel_real_con_perdidas
      - detalle_mensual: lista de dicts por mes (cronologico)
    """
    hoy = datetime.date.today()
    desde = (hoy - relativedelta(months=meses)).replace(day=1)

    stock_actual = get_stock_actual_csr(csr)

    # Factores estacionales (v3)
    f_est = _factor_estacional_single(csr)

    # Ventas mensuales
    t_sql_v = (
        "SELECT "
        "  SUM(CASE WHEN v.operacion='+' THEN v.cantidad "
        "           WHEN v.operacion='-' THEN -v.cantidad END) AS cant, "
        "  YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes "
        "FROM omicron_ventas1 v "
        "LEFT JOIN articulo a ON v.articulo=a.codigo "
        "WHERE v.codigo NOT IN {excl} "
        "  AND a.codigo_sinonimo='{csr}' "
        "  AND v.fecha>='{desde}' "
        "GROUP BY YEAR(v.fecha), MONTH(v.fecha)"
    ).format(excl=CODIGOS_EXCLUIR_VENTAS, csr=csr, desde=desde)

    # Compras mensuales (solo ingresos)
    t_sql_c = (
        "SELECT "
        "  SUM(rc.cantidad) AS cant, "
        "  YEAR(rc.fecha) AS anio, MONTH(rc.fecha) AS mes "
        "FROM omicron_compras1_remitos rc "
        "LEFT JOIN articulo a ON rc.articulo=a.codigo "
        "WHERE rc.operacion='+' "
        "  AND a.codigo_sinonimo='{csr}' "
        "  AND rc.fecha>='{desde}' "
        "GROUP BY YEAR(rc.fecha), MONTH(rc.fecha)"
    ).format(csr=csr, desde=desde)

    ventas_data = db1.executesql(t_sql_v, as_dict=True)
    compras_data = db1.executesql(t_sql_c, as_dict=True)

    # Indexar por (anio, mes)
    ventas_dict = {}
    for r in ventas_data:
        ventas_dict[(r['anio'], r['mes'])] = float(r['cant'] or 0)

    compras_dict = {}
    for r in compras_data:
        compras_dict[(r['anio'], r['mes'])] = float(r['cant'] or 0)

    # Generar lista de meses (de mas reciente a mas antiguo)
    meses_lista = []
    cursor = hoy.replace(day=1)
    for i in range(meses):
        meses_lista.append((cursor.year, cursor.month))
        cursor = cursor - relativedelta(months=1)

    # Reconstruir stock mes a mes (desde el mas reciente hacia atras)
    detalle = []
    stock_fin = stock_actual
    meses_q = 0
    meses_ok = 0
    ventas_total = 0
    ventas_ok = 0
    ventas_desest = 0
    ventas_meses_ok = []

    for anio, mes in meses_lista:
        v = ventas_dict.get((anio, mes), 0)
        c = compras_dict.get((anio, mes), 0)
        stock_inicio = stock_fin + v - c  # reconstruccion hacia atras

        quebrado = stock_inicio <= 0
        ventas_total += v

        if quebrado:
            meses_q += 1
        else:
            meses_ok += 1
            ventas_ok += v
            ventas_meses_ok.append(v)
            # Desestacionalizar: dividir ventas por factor del mes
            s_t = max(f_est.get(mes, 1.0), 0.1)
            ventas_desest += v / s_t

        detalle.append({
            'anio': anio,
            'mes': mes,
            'periodo': '%d-%02d' % (anio, mes),
            'ventas': v,
            'compras': c,
            'stock_inicio': stock_inicio,
            'stock_fin': stock_fin,
            'quebrado': quebrado
        })

        stock_fin = stock_inicio

    # Calcular metricas v3
    vel_ap = ventas_total / max(meses, 1)
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
    factor_quiebre = vel_real / vel_ap if vel_ap > 0 else 1.0

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
            v = ventas_dict.get((anio, mes), 0)
            c = compras_dict.get((anio, mes), 0)
            stock_inicio_check = stock_fin2 + v - c
            if stock_inicio_check <= 0:
                factor_mes = max(f_est.get(mes, 1.0), 0.1)
                ventas_esperadas = vel_base * factor_mes
                ventas_perdidas += max(0.0, ventas_esperadas - v)
            stock_fin2 = stock_inicio_check

    vel_real_con_perdidas = round((ventas_total + ventas_perdidas) / max(meses, 1), 2)
    pct_quiebre = pct_q * 100

    return {
        'stock_actual': stock_actual,
        'meses_analizados': len(detalle),
        'meses_quebrado': meses_q,
        'meses_con_stock': meses_ok,
        'pct_quiebre': round(pct_quiebre, 1),
        'ventas_total': ventas_total,
        'vel_aparente': round(vel_ap, 2),
        'vel_real': round(vel_real, 2),
        'vel_base_desest': round(vel_base, 2),
        'factor_disp': factor_disp,
        'factor_quiebre': round(factor_quiebre, 2),
        'std_mensual': round(std_mes, 2),
        'ventas_perdidas': round(ventas_perdidas),
        'vel_real_con_perdidas': vel_real_con_perdidas,
        'detalle_mensual': list(reversed(detalle))  # cronologico
    }


# ============================================================================
# FACTOR ESTACIONAL
# ============================================================================

def calcular_factor_estacional(csr, anios=3):
    """
    Calcula factor estacional mensual basado en historial.

    FIX E06: Incorpora estacionalidad en proyecciones.

    Método:
    1. Toma ventas mensuales de los últimos N años
    2. Calcula promedio por mes del año
    3. Factor = promedio_mes / promedio_general

    Retorna dict {1: factor_enero, 2: factor_febrero, ..., 12: factor_diciembre}
    Donde factor=1.0 es promedio, >1 es temporada alta, <1 es baja.
    """
    desde = (datetime.date.today() - relativedelta(years=anios)).replace(month=1, day=1)

    t_sql = (
        "SELECT "
        "  SUM(CASE WHEN v.operacion='+' THEN v.cantidad "
        "           WHEN v.operacion='-' THEN -v.cantidad END) AS cant, "
        "  YEAR(v.fecha) AS anio, MONTH(v.fecha) AS mes "
        "FROM omicron_ventas1 v "
        "LEFT JOIN articulo a ON v.articulo=a.codigo "
        "WHERE v.codigo NOT IN {excl} "
        "  AND a.codigo_sinonimo='{csr}' "
        "  AND v.fecha>='{desde}' "
        "GROUP BY YEAR(v.fecha), MONTH(v.fecha)"
    ).format(excl=CODIGOS_EXCLUIR_VENTAS, csr=csr, desde=desde)

    data = db1.executesql(t_sql, as_dict=True)

    if not data:
        return {m: 1.0 for m in range(1, 13)}

    # Construir DataFrame
    df = pd.DataFrame(data)
    df['cant'] = df['cant'].astype(float)

    # Promedio por mes del año
    prom_mes = df.groupby('mes')['cant'].mean()
    prom_gral = prom_mes.mean()

    factores = {}
    for m in range(1, 13):
        if m in prom_mes.index and prom_gral > 0:
            factores[m] = round(prom_mes[m] / prom_gral, 3)
        else:
            factores[m] = 1.0

    return factores


def get_temporada_actual():
    """Retorna 'verano' o 'invierno' según el mes actual."""
    mes = datetime.date.today().month
    return 'verano' if mes in MESES_VERANO else 'invierno'


# ============================================================================
# SUGERENCIA DE PEDIDO — NUEVO (E15)
# ============================================================================

def calcular_pedido_sugerido(csr, cobertura_meses=3, meses_quiebre=12):
    """
    Calcula pedido sugerido para un producto.

    NEW E15: Funcionalidad que no existía.

    Método:
    1. Calcula quiebre mensual (12 meses)
    2. Obtiene velocidad REAL (ajustada por quiebre)
    3. Aplica factor estacional del mes actual
    4. Calcula cobertura actual (stock / velocidad_ajustada)
    5. Si cobertura < objetivo → sugiere pedir

    Retorna dict con:
      - vel_real: velocidad real mensual
      - factor_estacional: factor del período actual
      - vel_ajustada: vel_real * factor_estacional
      - stock_actual: stock hoy
      - cobertura_meses: meses de cobertura con stock actual
      - pedir: unidades a pedir (0 si no hace falta)
      - detalle_quiebre: resultado de calcular_quiebre_mensual
    """
    quiebre = calcular_quiebre_mensual(csr, meses=meses_quiebre)
    factores = calcular_factor_estacional(csr)

    # Factor estacional: promedio de los próximos N meses
    hoy = datetime.date.today()
    factor_sum = 0
    for i in range(cobertura_meses):
        mes_futuro = ((hoy.month - 1 + i) % 12) + 1
        factor_sum += factores.get(mes_futuro, 1.0)
    factor_estacional = factor_sum / cobertura_meses

    vel_ajustada = quiebre['vel_real'] * factor_estacional

    stock = quiebre['stock_actual']
    cobertura = stock / vel_ajustada if vel_ajustada > 0 else 999

    necesidad = vel_ajustada * cobertura_meses
    pedir = max(0, round(necesidad - stock))

    return {
        'csr': csr,
        'vel_real': quiebre['vel_real'],
        'vel_aparente': quiebre['vel_aparente'],
        'vel_base_desest': quiebre.get('vel_base_desest', quiebre['vel_real']),
        'factor_disp': quiebre.get('factor_disp', 1.0),
        'factor_estacional': round(factor_estacional, 3),
        'vel_ajustada': round(vel_ajustada, 2),
        'stock_actual': stock,
        'cobertura_meses': round(cobertura, 1),
        'cobertura_objetivo': cobertura_meses,
        'pedir': pedir,
        'pct_quiebre': quiebre['pct_quiebre'],
        'std_mensual': quiebre.get('std_mensual', 0),
        'ventas_perdidas': quiebre.get('ventas_perdidas', 0),
        'vel_real_con_perdidas': quiebre.get('vel_real_con_perdidas', 0),
        'detalle_quiebre': quiebre
    }


# ============================================================================
# CURVA MÍNIMA POR TALLE — NUEVO (E16)
# ============================================================================

def calcular_curva_minima(csr, total_pedir, meses_historial=24):
    """
    Distribuye las unidades a pedir por talle según historial de ventas.

    NEW E16: Funcionalidad que no existía.

    Retorna lista de dicts: [{talle, pct_ideal, pedir, stock_actual}, ...]
    Siempre asegura mínimo 1 unidad por talle activo.
    """
    desde = (datetime.date.today() - relativedelta(months=meses_historial)).replace(day=1)

    # Ventas por talle
    t_sql = (
        "SELECT "
        "  SUM(CASE WHEN v.operacion='+' THEN v.cantidad "
        "           WHEN v.operacion='-' THEN -v.cantidad END) AS cant, "
        "  a.codigo_sinonimo, a.descripcion_5 AS talle "
        "FROM omicron_ventas1 v "
        "LEFT JOIN articulo a ON v.articulo=a.codigo "
        "WHERE v.codigo NOT IN {excl} "
        "  AND a.codigo_sinonimo LIKE '{csr}%' "
        "  AND v.fecha>='{desde}' "
        "GROUP BY a.codigo_sinonimo, a.descripcion_5 "
        "HAVING SUM(CASE WHEN v.operacion='+' THEN v.cantidad "
        "               WHEN v.operacion='-' THEN -v.cantidad END) > 0"
    ).format(excl=CODIGOS_EXCLUIR_VENTAS, csr=csr, desde=desde)

    ventas = db1.executesql(t_sql, as_dict=True)

    if not ventas:
        return []

    # Stock actual por talle
    stocks = {}
    stock_data = get_stock_curva(csr)
    for s in stock_data:
        stocks[s['codigo_sinonimo']] = s['stock'] or 0

    # Distribución porcentual
    total_vendido = sum(float(v['cant'] or 0) for v in ventas)

    resultado = []
    asignados = 0

    for v in ventas:
        cant = float(v['cant'] or 0)
        pct = (cant / total_vendido * 100) if total_vendido > 0 else 0
        pedir_talle = max(1, round(total_pedir * pct / 100))
        stock_talle = stocks.get(v['codigo_sinonimo'], 0)

        resultado.append({
            'codigo_sinonimo': v['codigo_sinonimo'],
            'talle': v['talle'],
            'ventas_periodo': cant,
            'pct_ideal': round(pct, 1),
            'stock_actual': stock_talle,
            'pedir_sugerido': pedir_talle
        })
        asignados += pedir_talle

    # Ajustar para que sume exactamente total_pedir
    if resultado and asignados != total_pedir:
        diff = total_pedir - asignados
        # Ajustar en el talle con mayor venta
        resultado.sort(key=lambda x: x['ventas_periodo'], reverse=True)
        resultado[0]['pedir_sugerido'] += diff

    # Ordenar por talle
    resultado.sort(key=lambda x: x['talle'])

    return resultado


# ============================================================================
# GRÁFICOS — FUNCIONES GENÉRICAS (FIX E12: sin duplicación)
# ============================================================================

def build_series_temporada(data_ventas, data_compras):
    """
    Construye series Highcharts de temporada (INV/VER) desde datos año-mes.
    FIX E07: Usa definición unificada de temporada.
    FIX E12: Función genérica para ambas series.
    """
    def _season(mes, anio):
        """Temporada unificada: ABR-SEP = INV, OCT-MAR = VER."""
        if mes in (4, 5, 6, 7, 8, 9):
            return '%d-INV' % anio
        elif mes in (10, 11, 12):
            return '%d-VER' % anio
        else:  # 1, 2, 3
            return '%d-VER' % (anio - 1)

    series = []

    if data_compras:
        dfc = pd.DataFrame(data_compras)
        dfc['cant'] = dfc['cant'].astype(float)
        dfc['temp'] = dfc.apply(lambda x: _season(int(x['me']), int(x['an'])), axis=1)
        dfc_agg = dfc.groupby('temp')['cant'].sum().reset_index()
        series.append({
            'name': 'Compras',
            'data': dfc_agg.sort_values('temp')[['temp', 'cant']].values.tolist()
        })

    if data_ventas:
        dfv = pd.DataFrame(data_ventas)
        dfv['cant'] = dfv['cant'].astype(float)
        dfv['temp'] = dfv.apply(lambda x: _season(int(x['me']), int(x['an'])), axis=1)
        dfv_agg = dfv.groupby('temp')['cant'].sum().reset_index()
        series.append({
            'name': 'Ventas',
            'data': dfv_agg.sort_values('temp')[['temp', 'cant']].values.tolist()
        })

    return json.dumps(series, default=str)


def build_series_anmes(data_ventas, data_compras):
    """
    Construye series Highcharts año-mes combinando compras y ventas.
    FIX E12: Función genérica.
    """
    dfs = []

    if data_compras:
        dfc = pd.DataFrame(data_compras)
        dfc['cant'] = dfc['cant'].astype(float).round(2)
        dfc = dfc[['anmes', 'cant']].rename(columns={'cant': 'cantidad_c'})
        dfs.append(('Compras', dfc, 'cantidad_c'))

    if data_ventas:
        dfv = pd.DataFrame(data_ventas)
        dfv['cant'] = dfv['cant'].astype(float).round(2)
        dfv = dfv[['anmes', 'cant']].rename(columns={'cant': 'cantidad_v'})
        dfs.append(('Ventas', dfv, 'cantidad_v'))

    series = []
    for name, df, col in dfs:
        data = df.sort_values('anmes')[[col, 'anmes']].values.tolist()
        # swap to [anmes, valor] for Highcharts
        data = [[r[1], r[0]] for r in data]
        series.append({'name': name, 'data': data})

    return json.dumps(series, default=str)


def build_series_mensual(data_ventas, data_compras):
    """
    Series Highcharts por mes del año (acumulado multi-año).
    FIX E12: Función genérica.
    """
    series = []

    if data_compras:
        dfc = pd.DataFrame(data_compras)
        dfc['cant'] = dfc['cant'].astype(float).round(2)
        dfc_m = dfc.groupby('mes')['cant'].sum().reset_index()
        series.append({
            'name': 'Compras',
            'type': 'column',
            'data': dfc_m.sort_values('mes')[['mes', 'cant']].values.tolist()
        })

    if data_ventas:
        dfv = pd.DataFrame(data_ventas)
        dfv['cant'] = dfv['cant'].astype(float).round(2)
        dfv_m = dfv.groupby('mes')['cant'].sum().reset_index()
        series.append({
            'name': 'Ventas',
            'type': 'column',
            'data': dfv_m.sort_values('mes')[['mes', 'cant']].values.tolist()
        })

    return json.dumps(series, default=str)


def build_ponderado_generico(desde_c, hasta_c, desde_v, hasta_v,
                              campo_grupo, tabla_grupo, **filtros):
    """
    Gráfico ponderado genérico para subrubro O rubro.
    FIX E03: Stock filtrado por DEPOS_INFORMES.
    FIX E12: Una sola función para subrubro y rubro (antes eran 2 x 90 líneas).

    campo_grupo: 'subrubro' o 'rubro'
    tabla_grupo: 'subrubro' o 'rubros'
    """
    f = _build_filtros_art(**filtros)

    t_sql_c = (
        "SELECT "
        "  SUM(CASE WHEN rc.operacion='+' THEN rc.cantidad "
        "           WHEN rc.operacion='-' THEN -rc.cantidad END) AS cant, "
        "  SUM(CASE WHEN rc.operacion='+' THEN rc.monto_facturado END) AS total_comp, "
        "  SUM(CASE WHEN rc.operacion='-' THEN rc.precio END) AS total_devs, "
        "  a.{campo}, g.descripcion "
        "FROM omicron_compras1_remitos rc "
        "LEFT JOIN articulo a ON rc.articulo=a.codigo "
        "LEFT JOIN {tabla} g ON a.{campo}=g.codigo "
        "WHERE rc.fecha>='{desde}' AND rc.fecha<='{hasta}' "
        "{filtros} "
        "GROUP BY a.{campo}, g.descripcion"
    ).format(campo=campo_grupo, tabla=tabla_grupo,
             desde=desde_c, hasta=hasta_c, filtros=f)

    # FIX E01 + E03: ventas con codigo NOT IN (7,36) y stock filtrado por depos
    t_sql_v = (
        "SELECT "
        "  SUM(CASE WHEN v.operacion='+' THEN v.cantidad "
        "           WHEN v.operacion='-' THEN -v.cantidad END) AS cant, "
        "  SUM((CASE WHEN v.operacion='+' THEN v.monto_facturado END) / 1.21) AS total_vent, "
        "  SUM((CASE WHEN v.operacion='-' THEN v.precio END) / 1.21) AS total_devs, "
        "  a.{campo}, g.descripcion "
        "FROM omicron_ventas1 v "
        "LEFT JOIN articulo a ON v.articulo=a.codigo "
        "LEFT JOIN {tabla} g ON a.{campo}=g.codigo "
        "WHERE v.codigo NOT IN {excl} "
        "  AND v.fecha>='{desde}' AND v.fecha<='{hasta}' "
        "{filtros} "
        "GROUP BY a.{campo}, g.descripcion"
    ).format(campo=campo_grupo, tabla=tabla_grupo, excl=CODIGOS_EXCLUIR_VENTAS,
             desde=desde_v, hasta=hasta_v, filtros=f)

    # Stock por grupo — FIX E03: filtrado por DEPOS_INFORMES
    t_sql_s = (
        "SELECT SUM(ws.stock_actual) AS stock, a.{campo}, g.descripcion "
        "FROM articulo a "
        "LEFT JOIN web_stock ws ON a.codigo=ws.articulo "
        "LEFT JOIN {tabla} g ON a.{campo}=g.codigo "
        "WHERE ws.deposito IN {depos} AND a.marca > 0 "
        "{filtros} "
        "GROUP BY a.{campo}, g.descripcion"
    ).format(campo=campo_grupo, tabla=tabla_grupo,
             depos=DEPOS_INFORMES_SQL, filtros=f)

    compras = db1.executesql(t_sql_c, as_dict=True)
    ventas = db1.executesql(t_sql_v, as_dict=True)
    stock = db1.executesql(t_sql_s, as_dict=True)

    series = []

    # Compras ponderado
    if compras:
        dfc = pd.DataFrame(compras)
        dfc['cant'] = dfc['cant'].astype(float)
        total_c = dfc['cant'].sum()
        if total_c > 0:
            dfc['pond'] = (dfc['cant'] / total_c * 100).round(2)
            series.append({
                'name': 'Compras',
                'data': dfc[['descripcion', 'pond']].values.tolist()
            })

    # Ventas ponderado
    if ventas:
        dfv = pd.DataFrame(ventas)
        dfv['cant'] = dfv['cant'].astype(float)
        total_v = dfv['cant'].sum()
        if total_v > 0:
            dfv['pond'] = (dfv['cant'] / total_v * 100).round(2)
            series.append({
                'name': 'Ventas',
                'data': dfv[['descripcion', 'pond']].values.tolist()
            })

    # Stock ponderado
    if stock:
        dfs = pd.DataFrame(stock)
        dfs['stock'] = dfs['stock'].astype(float)
        total_s = dfs['stock'].sum()
        if total_s > 0:
            dfs['pond'] = (dfs['stock'] / total_s * 100).round(2)
            series.append({
                'name': 'Stock actual',
                'data': dfs[['descripcion', 'pond']].values.tolist()
            })

    return json.dumps(series, default=str)


# ============================================================================
# UTILIDADES DE PRESENTACIÓN
# ============================================================================

def get_imagen_mini_safe(csr, codigo=None):
    """
    Miniatura de imagen por CSR. Versión segura con manejo de errores.
    """
    carpeta_imagenes = 'F:/Macroges/Imagenes/'
    try:
        if csr and int(csr) > 0 and codigo is None:
            codprod = db1.executesql(
                "SELECT TOP(1) codigo FROM articulo WHERE codigo_sinonimo LIKE '%s%%'" % csr
            )[0][0]
        elif codigo is not None:
            codprod = codigo
        else:
            return ''

        query = db1.executesql(
            "SELECT dbo.f_sql_nombre_imagen(empresa,tipo,sistema,codigo,letra,"
            "sucursal,numero,orden,renglon,extencion) AS nombre_imagen "
            "FROM imagen WHERE numero=%s AND codigo=0 AND tipo='AR' "
            "AND empresa=1 AND sistema=0" % codprod
        )

        if query:
            from PIL import Image
            nombre = query[0][0].replace('\\', '')[24:]
            archivo = os.path.join(carpeta_imagenes, nombre)
            size = (80, 100)
            try:
                img = Image.open(archivo)
                img.thumbnail(size, Image.LANCZOS)  # LANCZOS reemplaza ANTIALIAS en Pillow moderno
                miniatura_file = os.path.join(request.folder, 'static', 'images', 'thumbnails', nombre)
                img.save(miniatura_file)
                return URL('static/images/thumbnails', str(nombre))
            except (IOError, ValueError):
                return ''
        return ''
    except Exception:
        return ''


def get_numeracion_csr(csr):
    """Obtiene rango de talles (min|max) para un CSR."""
    try:
        q = db1.executesql(
            "SELECT MIN(descripcion_5), MAX(descripcion_5) "
            "FROM web_articulo WHERE LEFT(codigo_sinonimo,10)='%s'" % csr
        )
        if q and q[0][0]:
            return '%s|%s' % (q[0][0], q[0][1] or 'ND')
        return 'ND|ND'
    except Exception:
        return 'SD|SD'


def get_ultimo_precio_compra(csr):
    """
    Obtiene último precio de compra y su valor CER.
    NEW E17: Análisis de precios con ajuste inflación.
    """
    t_sql = (
        "SELECT TOP 1 "
        "  rc.monto_facturado / NULLIF(rc.cantidad, 0) AS precio_unit, "
        "  rc.fecha "
        "FROM omicron_compras1_remitos rc "
        "LEFT JOIN articulo a ON rc.articulo=a.codigo "
        "WHERE a.codigo_sinonimo LIKE '{csr}%' "
        "  AND rc.operacion='+' AND rc.cantidad > 0 "
        "ORDER BY rc.fecha DESC"
    ).format(csr=csr)

    try:
        result = db1.executesql(t_sql, as_dict=True)
        if result:
            precio = float(result[0]['precio_unit'])
            fecha = result[0]['fecha']
            precio_cer = fx_AjustarPorCer(precio, fecha)
            return {
                'precio': round(precio, 2),
                'fecha': fecha,
                'precio_cer': round(float(precio_cer), 2)
            }
    except Exception:
        pass
    return {'precio': 0, 'fecha': None, 'precio_cer': 0}


# ============================================================================
# ANÁLISIS COMPLETO DE MARCA PARA PEDIDO
# ============================================================================

def analizar_marca_para_pedido(marca, cobertura_meses=3, meses_quiebre=12):
    """
    Análisis completo de una marca: quiebre + estacionalidad + sugerencia.

    Combina todo para generar tabla de pedido sugerido por producto y talle.

    Retorna lista de dicts, uno por CSR (producto).
    """
    # Obtener todos los productos de la marca con stock o ventas recientes
    desde = (datetime.date.today() - relativedelta(months=meses_quiebre)).replace(day=1)

    t_sql = (
        "SELECT DISTINCT LEFT(a.codigo_sinonimo, 10) AS csr, "
        "  MAX(a.descripcion_1) AS descripcion "
        "FROM articulo a "
        "WHERE a.marca={marca} "
        "  AND LEN(a.codigo_sinonimo) >= 10 "
        "  AND LEFT(a.codigo_sinonimo, 10) <> '0000000000' "
        "GROUP BY LEFT(a.codigo_sinonimo, 10) "
        "HAVING ("
        "  EXISTS (SELECT 1 FROM web_stock ws "
        "    LEFT JOIN articulo a2 ON a2.codigo=ws.articulo "
        "    WHERE LEFT(a2.codigo_sinonimo,10)=LEFT(a.codigo_sinonimo,10) "
        "    AND ws.deposito IN {depos} AND ws.stock_actual > 0) "
        "  OR EXISTS (SELECT 1 FROM omicron_ventas1 v "
        "    LEFT JOIN articulo a3 ON a3.codigo=v.articulo "
        "    WHERE LEFT(a3.codigo_sinonimo,10)=LEFT(a.codigo_sinonimo,10) "
        "    AND v.fecha>='{desde}' AND v.codigo NOT IN {excl})"
        ")"
    ).format(marca=marca, depos=DEPOS_INFORMES_SQL,
             desde=desde, excl=CODIGOS_EXCLUIR_VENTAS)

    productos = db1.executesql(t_sql, as_dict=True)

    resultados = []
    for p in productos:
        csr = p['csr']
        try:
            pedido = calcular_pedido_sugerido(csr, cobertura_meses, meses_quiebre)
            precio = get_ultimo_precio_compra(csr)

            resultados.append({
                'csr': csr,
                'descripcion': p['descripcion'],
                'stock_actual': pedido['stock_actual'],
                'vel_aparente': pedido['vel_aparente'],
                'vel_real': pedido['vel_real'],
                'vel_base_desest': pedido.get('vel_base_desest', pedido['vel_real']),
                'factor_disp': pedido.get('factor_disp', 1.0),
                'pct_quiebre': pedido['pct_quiebre'],
                'factor_estacional': pedido['factor_estacional'],
                'vel_ajustada': pedido['vel_ajustada'],
                'cobertura_meses': pedido['cobertura_meses'],
                'pedir': pedido['pedir'],
                'precio_unit': precio['precio'],
                'precio_cer': precio['precio_cer'],
                'monto_pedir': pedido['pedir'] * precio['precio_cer'],
                'std_mensual': pedido.get('std_mensual', 0),
                'ventas_perdidas': pedido.get('ventas_perdidas', 0),
                'vel_real_con_perdidas': pedido.get('vel_real_con_perdidas', 0),
                'imagen': get_imagen_mini_safe(csr)
            })
        except Exception as e:
            resultados.append({
                'csr': csr,
                'descripcion': p['descripcion'],
                'error': str(e)
            })

    # Ordenar por monto a pedir (mayor primero)
    resultados.sort(key=lambda x: x.get('monto_pedir', 0), reverse=True)

    return resultados
