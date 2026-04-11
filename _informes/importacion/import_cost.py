# -*- coding: utf-8 -*-
"""
import_cost.py — Calculadora de costo de importación de calzado.
Usado por: controllers/importaciones.py (web2py) y scripts directos.

Dirección:
  FORWARD  — calcular_costo_importacion(fob_real, fob_aduana, logistica, tc)
             FOB origen → costo económico / financiero en ARS
  REVERSE  — calcular_fob_maximo(precio_venta_ars, margen_pct, tc, ...)
             Precio venta ARS + margen → FOB máximo pagable en USD

Empresa: RI (Responsable Inscripto) — IVA y percepciones son crédito fiscal
         → no integran costo económico (sí el financiero/desembolso).
Régimen: importación definitiva, calzado, Argentina.
"""

import math

# ─────────────────────────────────────────────────────────────
# Alícuotas vigentes (Argentina — calzado RI)
# ─────────────────────────────────────────────────────────────
ALICUOTAS = {
    # Derechos aduaneros (NO recuperables — van al costo)
    "derecho_importacion":    0.20,   # 20% sobre CIF aduana
    "tasa_estadistica":       0.03,   # 3% sobre CIF aduana

    # Impuestos que la empresa RI recupera como crédito fiscal
    "iva":                    0.21,   # 21% sobre base gravada
    "percepcion_iva":         0.20,   # 20% sobre base gravada (RG 2937)
    "percepcion_ganancias":   0.06,   # 6% sobre base gravada (no bienes de uso)

    # IIBB Santa Fe — grava la venta, no la importación
    "iibb_santa_fe":          0.035,  # 3.5% sobre precio venta

    # Logística por defecto (solo para estimaciones — preferir dato real)
    "flete_pct_default":      0.10,   # ~10% del FOB
    "seguro_pct_default":     0.01,   # ~1% del FOB
}


# ─────────────────────────────────────────────────────────────
# 1. Prorrateo de logística de contenedor → unitario
# ─────────────────────────────────────────────────────────────
def calcular_logistica_unitaria(flete_maritimo, flete_interno, despachante,
                                valor_fob_aduana_total, fob_aduana_producto):
    """
    Prorratea los costos de logística del contenedor al SKU individual
    según su participación en el FOB aduana total del contenedor.

    Parámetros (todos en USD):
        flete_maritimo       — flete marítimo total del contenedor
        flete_interno        — flete interno (port → depósito)
        despachante          — honorarios del despachante de aduana
        valor_fob_aduana_total  — FOB aduana total del contenedor
        fob_aduana_producto  — FOB aduana declarado del producto/SKU

    Retorna:
        float — logística unitaria en USD para este SKU
    """
    if valor_fob_aduana_total <= 0:
        raise ValueError("valor_fob_aduana_total debe ser mayor a 0")
    total_log = flete_maritimo + flete_interno + despachante
    share = fob_aduana_producto / valor_fob_aduana_total
    return total_log * share


# ─────────────────────────────────────────────────────────────
# 2. Forward: FOB → costo ARS
# ─────────────────────────────────────────────────────────────
def calcular_costo_importacion(fob_real, fob_aduana, logistica_unitaria, tipo_cambio):
    """
    FORWARD — Calcula el costo de un zapato importado desde su precio FOB.

    Parámetros (fob_* y logistica en USD):
        fob_real          — lo que se paga al proveedor en origen
        fob_aduana        — valor declarado ante AFIP (>= fob_real)
                            Si fob_real == 0 asume fob_real = fob_aduana (sin dumping)
        logistica_unitaria — flete + seguro + flete interno + despachante, por unidad
        tipo_cambio       — ARS/USD (dólar vendedor BNA)

    Retorna dict con todas las claves que espera views/importaciones/simulador.html:

    Reglas de imputación:
      • CIF aduana = fob_aduana + logistica (base para derechos e impuestos)
      • Derecho importación 20% + Tasa estadística 3% → NO recuperables → van al costo
      • IVA 21% + PercIVA 20% + PercGan 6% → recuperables (RI) → solo costo financiero
      • Costo económico = fob_real + logistica + DI + TE   (lo que "cuesta" el zapato)
      • Costo financiero = económico + IVA + PercIVA + PercGan  (desembolso real)
      • Sobrecosto dumping = (fob_aduana - fob_real) × (DI% + TE%)  (por sub-declarar)
    """
    if tipo_cambio <= 0:
        raise ValueError("tipo_cambio debe ser mayor a 0")
    if fob_aduana <= 0:
        raise ValueError("fob_aduana debe ser mayor a 0")

    # Si fob_real viene en 0, asumir sin dumping
    if fob_real <= 0:
        fob_real = fob_aduana

    d  = ALICUOTAS["derecho_importacion"]
    t  = ALICUOTAS["tasa_estadistica"]
    vi = ALICUOTAS["iva"]
    pi = ALICUOTAS["percepcion_iva"]
    pg = ALICUOTAS["percepcion_ganancias"]

    tc = tipo_cambio

    # Base aduanera (CIF declarado)
    cif_usd = fob_aduana + logistica_unitaria

    # Derechos (base = CIF aduana)
    derecho_usd    = cif_usd * d
    estadistica_usd = cif_usd * t

    # Base IVA (CIF + DI + TE)
    base_iva_usd = cif_usd + derecho_usd + estadistica_usd

    # Impuestos recuperables
    iva_usd          = base_iva_usd * vi
    perc_iva_usd     = base_iva_usd * pi
    perc_gan_usd     = base_iva_usd * pg
    recuperables_usd = iva_usd + perc_iva_usd + perc_gan_usd

    # Costos
    costo_econ_usd = fob_real + logistica_unitaria + derecho_usd + estadistica_usd
    costo_fin_usd  = costo_econ_usd + recuperables_usd

    # Sobrecosto por diferencia FOB real vs FOB aduana ("dumping")
    diff_usd = fob_aduana - fob_real
    sobrecosto_usd = diff_usd * (d + t)
    pct_sobrecosto = (sobrecosto_usd / fob_real * 100) if fob_real > 0 else 0.0

    def _ars(usd):
        return round(usd * tc)

    return {
        # Inputs (clave → esperado por el template)
        "fob_real_usd":               fob_real,
        "fob_aduana_usd":             fob_aduana,
        "logistica_usd":              logistica_unitaria,
        "tipo_cambio":                tc,

        # Desglose en ARS
        "cif_ars":                    _ars(cif_usd),
        "derecho_ars":                _ars(derecho_usd),
        "estadistica_ars":            _ars(estadistica_usd),
        "base_iva_ars":               _ars(base_iva_usd),
        "iva_ars":                    _ars(iva_usd),
        "percepcion_iva_ars":         _ars(perc_iva_usd),
        "percepcion_ganancias_ars":   _ars(perc_gan_usd),
        "recuperables_ars":           _ars(recuperables_usd),
        "costo_financiero_ars":       _ars(costo_fin_usd),
        "costo_economico_ars":        _ars(costo_econ_usd),

        # Sobrecosto dumping
        "diferencial_dumping_usd":    round(diff_usd, 4),
        "sobrecosto_dumping_ars":     _ars(sobrecosto_usd),
        "pct_sobrecosto_sobre_real":  round(pct_sobrecosto, 1),

        # Desglose USD (útil para scripts)
        "cif_usd":                    round(cif_usd, 4),
        "derecho_usd":                round(derecho_usd, 4),
        "estadistica_usd":            round(estadistica_usd, 4),
        "base_iva_usd":               round(base_iva_usd, 4),
        "iva_usd":                    round(iva_usd, 4),
        "perc_iva_usd":               round(perc_iva_usd, 4),
        "perc_gan_usd":               round(perc_gan_usd, 4),
        "costo_economico_usd":        round(costo_econ_usd, 4),
        "costo_financiero_usd":       round(costo_fin_usd, 4),
        "markup_sobre_fob_real":      round(costo_econ_usd / fob_real, 4),
    }


# ─────────────────────────────────────────────────────────────
# 3. Precios de venta desde costo económico
# ─────────────────────────────────────────────────────────────
def calcular_precios_venta(costo_economico_ars, margenes, iibb_pct=None):
    """
    Calcula precios de venta a 4 niveles desde el costo económico.

    Parámetros:
        costo_economico_ars  — costo económico en ARS (sin recuperables)
        margenes             — dict con niveles y % de utilidad, ej:
                               {'contado': 98.9, 'lista': 122.9,
                                'intermedio': 60, 'mayorista': 45}
        iibb_pct             — alícuota IIBB decimal (default: ALICUOTAS["iibb_santa_fe"])

    Fórmula:
        precio = costo_econ × (1 + margen/100) × (1 + iibb_pct)
        → IIBB se toma como carga sobre la venta, no sobre el costo

    Retorna:
        dict {nivel: {'exacto': float, 'redondeado': int}}
        'redondeado' sube al múltiplo de $100 inmediato superior.
    """
    if iibb_pct is None:
        iibb_pct = ALICUOTAS["iibb_santa_fe"]

    resultado = {}
    for nivel, margen in margenes.items():
        exacto = costo_economico_ars * (1 + margen / 100.0) * (1 + iibb_pct)
        redondeado = int(math.ceil(exacto / 100.0) * 100)
        resultado[nivel] = {
            "exacto":     round(exacto, 2),
            "redondeado": redondeado,
        }
    return resultado


# ─────────────────────────────────────────────────────────────
# 4. Reverse: precio venta → FOB máximo
# ─────────────────────────────────────────────────────────────
def calcular_fob_maximo(precio_venta_ars, margen_pct, tipo_cambio,
                        logistica_unitaria_usd=0.0,
                        flete_pct=0.0, seguro_pct=0.0,
                        iibb_pct=None):
    """
    REVERSE — Dado un precio de venta objetivo, calcula el FOB máximo pagable.

    Despeja algebraicamente desde:
        precio_venta = costo_econ_ars × (1 + margen/100) × (1 + iibb)
        costo_econ_ars = costo_econ_usd × TC
        costo_econ_usd = CIF_usd × (1 + d + t)
        CIF_usd = fob × (1 + flete_pct + seguro_pct) + logistica_unitaria_usd

    Asume FOB real = FOB aduana (sin sub-declaración/dumping).
    IVA y percepciones son recuperables (RI) → no integran costo económico.

    Parámetros:
        precio_venta_ars      — precio de venta objetivo en ARS (con IIBB)
        margen_pct            — margen de utilidad deseado (%), ej: 100.0
        tipo_cambio           — ARS/USD
        logistica_unitaria_usd— costo fijo de logística por par en USD
                                (flete marítimo + interno + despachante prorrateados)
                                Usar 0 si se prefiere estimar via flete_pct/seguro_pct
        flete_pct             — flete como fracción del FOB (ej: 0.10 = 10%)
                                Complementa logistica_unitaria_usd si ambos > 0
        seguro_pct            — seguro como fracción del FOB (ej: 0.01 = 1%)
        iibb_pct              — fracción IIBB (default ALICUOTAS["iibb_santa_fe"])

    Retorna dict con:
        fob_maximo_usd        — FOB máximo en USD
        costo_economico_ars   — costo económico implícito en ARS
        costo_economico_usd   — idem en USD
        cif_usd               — CIF calculado en USD
        logistica_total_usd   — logística unitaria usada
        margen_aplicado_pct   — margen usado
        iibb_aplicado_pct     — IIBB usado (%)
        verificacion          — re-corrida forward para validar roundtrip
    """
    if tipo_cambio <= 0:
        raise ValueError("tipo_cambio debe ser mayor a 0")
    if precio_venta_ars <= 0:
        raise ValueError("precio_venta_ars debe ser mayor a 0")
    if margen_pct < 0:
        raise ValueError("margen_pct no puede ser negativo")

    if iibb_pct is None:
        iibb_pct = ALICUOTAS["iibb_santa_fe"]

    d = ALICUOTAS["derecho_importacion"]
    t = ALICUOTAS["tasa_estadistica"]

    # Despejar costo económico desde precio venta
    costo_econ_ars = precio_venta_ars / ((1 + margen_pct / 100.0) * (1 + iibb_pct))
    costo_econ_usd = costo_econ_ars / tipo_cambio

    # Despejar CIF desde costo económico (costo_econ = CIF × (1 + d + t))
    cif_usd = costo_econ_usd / (1.0 + d + t)

    # Despejar FOB desde CIF
    # CIF = fob × (1 + flete + seguro) + logistica_fija
    # → fob = (CIF - logistica_fija) / (1 + flete + seguro)
    denominador = 1.0 + flete_pct + seguro_pct
    fob_maximo_usd = (cif_usd - logistica_unitaria_usd) / denominador

    # Logística total que se asume (fija + variable sobre este FOB)
    logistica_total_usd = logistica_unitaria_usd + fob_maximo_usd * (flete_pct + seguro_pct)

    # Verificación roundtrip (forward con FOB calculado)
    verificacion = None
    if fob_maximo_usd > 0:
        verificacion = calcular_costo_importacion(
            fob_real           = fob_maximo_usd,
            fob_aduana         = fob_maximo_usd,
            logistica_unitaria = logistica_total_usd,
            tipo_cambio        = tipo_cambio,
        )

    return {
        "fob_maximo_usd":       round(fob_maximo_usd, 4),
        "costo_economico_ars":  round(costo_econ_ars, 2),
        "costo_economico_usd":  round(costo_econ_usd, 4),
        "cif_usd":              round(cif_usd, 4),
        "logistica_total_usd":  round(logistica_total_usd, 4),
        "margen_aplicado_pct":  margen_pct,
        "iibb_aplicado_pct":    round(iibb_pct * 100, 2),
        "tipo_cambio":          tipo_cambio,
        "verificacion":         verificacion,
    }
