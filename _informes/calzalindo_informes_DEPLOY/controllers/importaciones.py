# -*- coding: utf-8 -*-
"""
controllers/importaciones.py
App: calzalindo_informes
Python 2.7 / web2py 2.24.1

Rutas:
    /calzalindo_informes/importaciones/simulador          (FORWARD: FOB → costo)
    /calzalindo_informes/importaciones/simulador_inverso  (REVERSE: precio venta → FOB max)
"""

import sys
import os

# Agregar modules al path para importar import_cost
_mod_path = os.path.join(request.folder, 'modules')
if _mod_path not in sys.path:
    sys.path.insert(0, _mod_path)

from import_cost import (
    calcular_logistica_unitaria,
    calcular_costo_importacion,
    calcular_precios_venta,
    calcular_fob_maximo,
    ALICUOTAS,
)


def simulador():
    """
    FORWARD — FOB origen → costo económico / financiero ARS → precios de venta

    GET  -> formulario vacío
    POST -> calcula y devuelve el desglose completo
    """
    _requiere_acceso('informes_gerencia', 'informes_admin', 'informes_compras')

    resultado   = None
    precios     = None
    error       = None

    if request.post_vars:
        try:
            # ── Inputs del formulario ──────────────────────────────
            fob_real    = float(request.post_vars.fob_real    or 0)
            fob_aduana  = float(request.post_vars.fob_aduana  or 0)
            tc          = float(request.post_vars.tipo_cambio or 0)

            # Logistica: ingresar total del contenedor o directamente unitaria
            modo_log = request.post_vars.modo_logistica or 'unitaria'

            if modo_log == 'contenedor':
                flete_mar  = float(request.post_vars.flete_maritimo  or 0)
                flete_int  = float(request.post_vars.flete_interno   or 0)
                despacho   = float(request.post_vars.despachante     or 0)
                fob_total  = float(request.post_vars.fob_total_contenedor or 0)

                if fob_total <= 0:
                    raise ValueError("FOB total del contenedor debe ser mayor a 0")

                logistica_u = calcular_logistica_unitaria(
                    flete_maritimo          = flete_mar,
                    flete_interno           = flete_int,
                    despachante             = despacho,
                    valor_fob_aduana_total  = fob_total,
                    fob_aduana_producto     = fob_aduana,
                )
            else:
                logistica_u = float(request.post_vars.logistica_unitaria or 0)

            if tc <= 0:
                raise ValueError("El tipo de cambio debe ser mayor a 0")
            if fob_aduana <= 0:
                raise ValueError("El FOB aduana debe ser mayor a 0")

            # ── Calcular ───────────────────────────────────────────
            resultado = calcular_costo_importacion(
                fob_real           = fob_real,
                fob_aduana         = fob_aduana,
                logistica_unitaria = logistica_u,
                tipo_cambio        = tc,
            )

            # ── Precios de venta (opcionales) ──────────────────────
            margenes = {}
            for nivel in ['contado', 'lista', 'intermedio', 'mayorista']:
                v = request.post_vars.get('margen_' + nivel, '').strip()
                if v:
                    margenes[nivel] = float(v)

            if margenes:
                iibb_v = request.post_vars.get('iibb_pct', '').strip()
                iibb_pct = float(iibb_v) / 100 if iibb_v else ALICUOTAS['iibb_santa_fe']
                precios = calcular_precios_venta(
                    resultado['costo_economico_ars'], margenes, iibb_pct=iibb_pct
                )

        except Exception as e:
            error = u'Error al calcular: {}'.format(unicode(str(e), 'utf-8', errors='replace'))

    return dict(
        resultado = resultado,
        precios   = precios,
        error     = error,
        post_vars = request.post_vars,
    )


def simulador_inverso():
    """
    REVERSE — Precio de venta objetivo ARS → FOB máximo pagable en USD

    Responde a la pregunta: "Si quiero vender a $X con Y% de margen,
    ¿cuánto puedo pagar en origen?"

    GET  -> formulario vacío
    POST -> calcula FOB máximo y desglose
    """
    _requiere_acceso('informes_gerencia', 'informes_admin', 'informes_compras')

    resultado = None
    error     = None

    if request.post_vars:
        try:
            precio_venta = float(request.post_vars.precio_venta_ars or 0)
            margen_pct   = float(request.post_vars.margen_pct       or 0)
            tc           = float(request.post_vars.tipo_cambio      or 0)

            if precio_venta <= 0:
                raise ValueError("El precio de venta debe ser mayor a 0")
            if tc <= 0:
                raise ValueError("El tipo de cambio debe ser mayor a 0")

            logistica_u = float(request.post_vars.logistica_unitaria_usd or 0)
            flete_pct   = float(request.post_vars.flete_pct or 0) / 100
            seguro_pct  = float(request.post_vars.seguro_pct or 0) / 100

            iibb_v   = request.post_vars.get('iibb_pct', '').strip()
            iibb_pct = float(iibb_v) / 100 if iibb_v else ALICUOTAS['iibb_santa_fe']

            resultado = calcular_fob_maximo(
                precio_venta_ars       = precio_venta,
                margen_pct             = margen_pct,
                tipo_cambio            = tc,
                logistica_unitaria_usd = logistica_u,
                flete_pct              = flete_pct,
                seguro_pct             = seguro_pct,
                iibb_pct               = iibb_pct,
            )

        except Exception as e:
            error = u'Error al calcular: {}'.format(unicode(str(e), 'utf-8', errors='replace'))

    return dict(
        resultado = resultado,
        error     = error,
        post_vars = request.post_vars,
        alicuotas = ALICUOTAS,
    )
