# -*- coding: utf-8 -*-
"""
Motor de precios por canal — v2 con desglose completo de costos.

Cada canal tiene:
  - comision: % que cobra la plataforma (ej: ML 15.5%, TN 0-1%)
  - comision_pago: % que cobra el procesador de pagos (ej: Pago Nube 3.49%, MP 4.39%)
  - iva_comision: % de IVA sobre las comisiones (21% en Argentina)
  - envio_pct: % estimado de costo de envío sobre precio neto (ej: ML ~4%)
  - retenciones_pct: % de retenciones fiscales (IIBB, IVA ret, Ganancias)
  - iva: % de IVA del producto (21%)
  - margen_objetivo: % de margen neto deseado DESPUÉS de todos los costos
  - recargo: % de recargo adicional (cuotas sin interés)
  - redondeo: a cuánto redondear (ej: 100 → $xx.999)
  - precio_minimo: piso por canal

Fórmula (v2):
  El precio de venta INCLUYE IVA 21%. El costo es NETO.

  precio_neto = precio_venta / 1.21
  costo_comisiones = precio_neto × (comision + comision_pago) × (1 + iva_comision)
  costo_envio = precio_neto × envio_pct
  retenciones = precio_neto × retenciones_pct  (a cuenta, recuperable)

  ganancia_neta = precio_neto - costo - costo_comisiones - costo_envio
  ganancia_real = ganancia_neta - retenciones  (lo que queda en mano)

  Para calcular el precio de venta dado un margen objetivo:
  precio_neto = costo / (1 - margen - comision_efectiva - envio_pct)
  donde comision_efectiva = (comision + comision_pago) × (1 + iva_comision)
  precio_venta = precio_neto × 1.21
"""
import math
import json
from dataclasses import dataclass, field, asdict, fields
from typing import Optional


@dataclass
class ReglaCanal:
    """Regla de pricing para un canal de venta."""
    canal: str
    descripcion: str = ''
    comision: float = 0.0          # % comisión plataforma (0.155 = 15.5%)
    comision_pago: float = 0.0     # % comisión procesador pago
    iva_comision: float = 0.21     # % IVA sobre las comisiones (21%)
    envio_pct: float = 0.0         # % estimado costo envío sobre precio neto
    retenciones_pct: float = 0.0   # % retenciones fiscales (IIBB, IVA ret, Ganancias)
    iva: float = 0.21              # % IVA del producto
    margen_objetivo: float = 0.40  # % margen neto deseado
    recargo: float = 0.0           # % recargo adicional (cuotas, etc)
    redondeo: int = 100            # redondear al múltiplo (100 → $xx.999)
    precio_minimo: float = 0.0     # piso de precio
    activo: bool = True
    notas: str = ''


# Reglas por defecto (actualizadas marzo 2026)
REGLAS_DEFAULT = {
    'mercadolibre_premium': ReglaCanal(
        canal='mercadolibre_premium',
        descripcion='MercadoLibre Premium — Santa Fe',
        comision=0.155, comision_pago=0.0,
        iva_comision=0.21, envio_pct=0.04, retenciones_pct=0.04,
        margen_objetivo=0.25, redondeo=100,
        notas='Calzado/Deporte: ~15.5% + IVA s/comisión. Envío gratis >$33k (~4%). Retenciones ~4%.',
    ),
    'mercadolibre_clasica': ReglaCanal(
        canal='mercadolibre_clasica',
        descripcion='MercadoLibre Clásica — Santa Fe',
        comision=0.13, comision_pago=0.0,
        iva_comision=0.21, envio_pct=0.0, retenciones_pct=0.04,
        margen_objetivo=0.25, redondeo=100,
        notas='Calzado/Deporte: ~13% + IVA s/comisión. Envío lo paga comprador. Retenciones ~4%.',
    ),
    'tiendanube_pagonube': ReglaCanal(
        canal='tiendanube_pagonube',
        descripcion='Tienda Nube + Pago Nube (14 días)',
        comision=0.0, comision_pago=0.0349,
        iva_comision=0.21, envio_pct=0.0, retenciones_pct=0.03,
        margen_objetivo=0.30, redondeo=100,
        notas='Plan Esencial. Con Pago Nube: 0% TN + 3.49% PN + IVA. Envío comprador.',
    ),
    'tiendanube_mp': ReglaCanal(
        canal='tiendanube_mp',
        descripcion='Tienda Nube + MercadoPago (10 días)',
        comision=0.01, comision_pago=0.0439,
        iva_comision=0.21, envio_pct=0.0, retenciones_pct=0.03,
        margen_objetivo=0.30, redondeo=100,
        notas='Plan Esencial: 1% TN + 4.39% MP + IVA. Envío comprador.',
    ),
    'tiendabna': ReglaCanal(
        canal='tiendabna',
        descripcion='TiendaBNA — Banco Nación',
        comision=0.08, comision_pago=0.0,
        iva_comision=0.21, envio_pct=0.03, retenciones_pct=0.0,
        margen_objetivo=0.25, redondeo=100, activo=False,
        notas='8% + IVA. Envío obligatorio a todo el país (~3%). 24 cuotas s/interés.',
    ),
    'meta': ReglaCanal(
        canal='meta',
        descripcion='Facebook + Instagram + WhatsApp',
        comision=0.0, comision_pago=0.035,
        iva_comision=0.21, envio_pct=0.0, retenciones_pct=0.0,
        margen_objetivo=0.35, redondeo=100,
        notas='Sin comisión plataforma. Pago transferencia (~0%) o MP (~3.5% + IVA).',
    ),
    'local': ReglaCanal(
        canal='local',
        descripcion='Venta en mostrador / local',
        comision=0.0, comision_pago=0.0,
        iva_comision=0.21, envio_pct=0.0, retenciones_pct=0.0,
        margen_objetivo=0.40, redondeo=100,
        notas='Precio de lista del ERP. Sin comisiones.',
    ),
}


def calcular_precio_canal(precio_costo: float, regla: ReglaCanal) -> dict:
    """
    Calcula el precio de venta para un canal dado el costo y la regla.

    La fórmula calcula el precio NETO (sin IVA) que genera el margen objetivo
    después de descontar TODOS los costos (comisiones + IVA s/comisiones + envío).
    Luego le agrega IVA 21% para obtener el precio final al público.

    Las retenciones fiscales son "a cuenta" (recuperables) así que NO se incluyen
    en la fórmula de precio, pero sí se informan para calcular el flujo de caja.
    """
    if precio_costo <= 0:
        return {'precio_venta': 0, 'error': 'Costo debe ser > 0'}

    # Comisión efectiva = (comisión plataforma + comisión pago) × (1 + IVA s/comisión)
    comision_bruta = regla.comision + regla.comision_pago
    comision_efectiva = comision_bruta * (1 + regla.iva_comision)

    # Costo total sobre precio neto = comisión efectiva + envío
    costo_total_pct = comision_efectiva + regla.envio_pct

    denominador = 1.0 - regla.margen_objetivo - costo_total_pct

    if denominador <= 0:
        return {
            'precio_venta': 0,
            'error': 'Margen (%.0f%%) + costos (%.1f%%) >= 100%%. Imposible.' % (
                regla.margen_objetivo * 100, costo_total_pct * 100
            )
        }

    # Precio NETO (sin IVA) que genera el margen deseado
    precio_neto = precio_costo / denominador

    # Agregar IVA para precio final al público
    precio_con_iva = precio_neto * (1 + regla.iva)

    # Recargo adicional (cuotas sin interés, etc)
    precio_con_recargo = precio_con_iva * (1 + regla.recargo)

    # Redondeo: al múltiplo más cercano, menos 1 (ej: $67.999)
    if regla.redondeo > 0:
        precio_redondeado = math.ceil(precio_con_recargo / regla.redondeo) * regla.redondeo - 1
    else:
        precio_redondeado = round(precio_con_recargo, 2)

    # Aplicar piso
    if regla.precio_minimo > 0:
        precio_redondeado = max(precio_redondeado, regla.precio_minimo)

    # ── Desglose REAL con precio redondeado ──
    precio_neto_real = precio_redondeado / (1 + regla.iva)

    # Costos en $
    iva_producto = precio_redondeado - precio_neto_real
    comision_plataforma = precio_neto_real * regla.comision
    comision_pago = precio_neto_real * regla.comision_pago
    iva_sobre_comisiones = (comision_plataforma + comision_pago) * regla.iva_comision
    costo_envio = precio_neto_real * regla.envio_pct
    retenciones = precio_neto_real * regla.retenciones_pct

    total_costos_no_recup = comision_plataforma + comision_pago + iva_sobre_comisiones + costo_envio

    # Ganancia neta (antes de retenciones — las retenciones se recuperan)
    ganancia_bruta = precio_neto_real - precio_costo - total_costos_no_recup
    margen_real = ganancia_bruta / precio_neto_real if precio_neto_real > 0 else 0

    # Lo que queda en mano (después de retenciones — flujo de caja)
    en_mano = ganancia_bruta - retenciones
    margen_en_mano = en_mano / precio_neto_real if precio_neto_real > 0 else 0

    return {
        'precio_venta': precio_redondeado,
        'precio_neto': round(precio_neto_real, 2),
        'precio_sin_redondear': round(precio_con_recargo, 2),
        'precio_costo': precio_costo,

        # Márgenes
        'margen_real': round(margen_real * 100, 1),
        'margen_en_mano': round(margen_en_mano * 100, 1),

        # Ganancias en $
        'ganancia_neta': round(ganancia_bruta, 2),
        'en_mano': round(en_mano, 2),

        # Comisiones en %
        'comision_bruta_pct': round(comision_bruta * 100, 1),
        'comision_efectiva_pct': round(comision_efectiva * 100, 1),
        'costo_total_pct': round(costo_total_pct * 100, 1),

        # Comisiones en $
        'comision_plataforma': round(comision_plataforma, 2),
        'comision_pago': round(comision_pago, 2),
        'iva_sobre_comisiones': round(iva_sobre_comisiones, 2),
        'costo_envio': round(costo_envio, 2),
        'retenciones': round(retenciones, 2),
        'total_costos': round(total_costos_no_recup, 2),

        # IVA del producto
        'iva_producto': round(iva_producto, 2),

        # Desglose legible
        'desglose': {
            'costo': precio_costo,
            'precio_neto': round(precio_neto_real, 2),
            'precio_venta_iva': precio_redondeado,
            'iva_producto': f"${iva_producto:,.0f} (21%)",
            'comision_plataforma': f"${comision_plataforma:,.0f} ({regla.comision*100:.1f}%)",
            'comision_pago': f"${comision_pago:,.0f} ({regla.comision_pago*100:.1f}%)",
            'iva_sobre_comisiones': f"${iva_sobre_comisiones:,.0f} (21% s/comisiones)",
            'costo_envio': f"${costo_envio:,.0f} ({regla.envio_pct*100:.1f}%)",
            'retenciones': f"${retenciones:,.0f} ({regla.retenciones_pct*100:.1f}% — recuperable)",
            'total_costos_no_recup': f"${total_costos_no_recup:,.0f}",
            'ganancia_neta': f"${ganancia_bruta:,.0f} ({margen_real*100:.1f}%)",
            'en_mano': f"${en_mano:,.0f} ({margen_en_mano*100:.1f}%)",
            'margen_objetivo': f"{regla.margen_objetivo*100:.0f}%",
            'recargo': f"{regla.recargo*100:.1f}%",
            'redondeo': regla.redondeo,
        }
    }


def calcular_todos_los_canales(precio_costo: float, reglas: dict = None) -> dict:
    """
    Calcula precios para TODOS los canales configurados.
    Retorna dict canal → resultado.
    """
    if reglas is None:
        reglas = REGLAS_DEFAULT

    resultados = {}
    for nombre, regla in reglas.items():
        if regla.activo:
            resultados[nombre] = calcular_precio_canal(precio_costo, regla)
            resultados[nombre]['canal'] = nombre
            resultados[nombre]['canal_descripcion'] = regla.descripcion

    return resultados


def guardar_reglas(reglas: dict, filepath: str):
    """Guarda las reglas a un archivo JSON."""
    data = {k: asdict(v) for k, v in reglas.items()}
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def cargar_reglas(filepath: str) -> dict:
    """Carga reglas desde un archivo JSON. Ignora campos desconocidos."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        valid_fields = {f.name for f in fields(ReglaCanal)}
        result = {}
        for k, v in data.items():
            filtered = {fk: fv for fk, fv in v.items() if fk in valid_fields}
            result[k] = ReglaCanal(**filtered)
        return result
    except FileNotFoundError:
        return REGLAS_DEFAULT.copy()
