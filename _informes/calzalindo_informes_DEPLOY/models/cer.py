# -*- coding: utf-8 -*-
"""
Ajuste por CER (Coeficiente de Estabilización de Referencia).
Usa función SQL omicronvt.dbo.AjustarPorCer para actualizar montos por inflación.
"""
import datetime

def fx_AjustarPorCer(monto, fecha):
    if isinstance(fecha, str):
        fecha = datetime.datetime.strptime(fecha, '%Y-%m-%d').date()
    fecha = request.now.date() if fecha > request.now.date() else fecha
    try:
        t_sql = "SELECT omicronvt.dbo.AjustarPorCer(%s,'%s')" % (monto, fecha)
        q = db_omicronvt.executesql(t_sql)
        res = q[0][0] if q[0][0] > 0 else monto
    except:
        res = monto
    return res
