# -*- coding: utf-8 -*-
"""
Motor de precios por canal.

Cada canal tiene:
  - comision: % que cobra la plataforma
  - comision_pago: % que cobra el procesador de pagos (ej: MercadoPago)
  - iva: % de IVA (21% Argentina)
  - margen_objetivo: % de margen neto deseado
  - recargo: % de recargo adicional (ej: cuotas sin interés)
  - redondeo: a cuánto redondear (ej: 100 → $67.999)
  - precio_minimo: piso por canal

Fórmula:
  precio_venta = costo / (1 - margen - comision - comision_pago)
  precio_venta *= (1 + recargo)
  precio_venta = redondear(precio_venta)
"""
import math
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ReglaCanal:
    """Regla de pricing para un canal de venta."""
    canal: str
    descripcion: str = ''
    comision: float = 0.0          # % comisión plataforma (0.16 = 16%)
    comision_pago: float = 0.0     # % comisión procesador pago
    iva: float = 0.21              # % IVA
    margen_objetivo: float = 0.40  # % margen neto deseado
    recargo: float = 0.0           # % recargo adicional (cuotas, etc)
    redondeo: int = 100            # redondear al múltiplo (100 → $xx.999)
    precio_minimo: float = 0.0     # piso de precio
    activo: bool = True
    notas: str = ''


# Reglas por defecto para cada canal
REGLAS_DEFAULT = {
    'mercadolibre_premium': ReglaCanal(
        canal='mercadolibre_premium',
        descripcion='MercadoLibre Premium (gold_pro)',
        comision=0.16,
        comision_pago=0.0,  # ML retiene y paga, no hay comisión MP separada
        margen_objetivo=0.40,
        recargo=0.0,
        redondeo=100,
        notas='Envío gratis incluido en comisión. ML retiene comisión del pago.',
    ),
    'mercadolibre_clasica': ReglaCanal(
        canal='mercadolibre_clasica',
        descripcion='MercadoLibre Clásica (gold_special)',
        comision=0.11,
        comision_pago=0.0,
        margen_objetivo=0.40,
        recargo=0.0,
        redondeo=100,
        notas='Envío a cargo del comprador.',
    ),
    'tiendanube': ReglaCanal(
        canal='tiendanube',
        descripcion='Tienda Nube + MercadoPago',
        comision=0.025,        # 2.5% TN
        comision_pago=0.045,   # 4.5% MercadoPago
        margen_objetivo=0.40,
        recargo=0.0,
        redondeo=100,
        notas='Comisión TN plan básico + MercadoPago.',
    ),
    'meta': ReglaCanal(
        canal='meta',
        descripcion='Facebook + Instagram + WhatsApp',
        comision=0.0,          # Meta no cobra comisión por catálogo
        comision_pago=0.045,   # MercadoPago o transferencia
        margen_objetivo=0.40,
        recargo=0.0,
        redondeo=100,
        notas='Sin comisión de plataforma. Pago por transferencia o MP.',
    ),
    'local': ReglaCanal(
        canal='local',
        descripcion='Venta en mostrador / local',
        comision=0.0,
        comision_pago=0.0,
        margen_objetivo=0.40,
        recargo=0.0,
        redondeo=100,
        notas='Precio de lista del ERP.',
    ),
}


def calcular_precio_canal(precio_costo: float, regla: ReglaCanal) -> dict:
    """
    Calcula el precio de venta para un canal dado el costo y la regla.

    Retorna dict con:
        precio_venta: precio final redondeado
        precio_sin_redondear: precio antes de redondear
        margen_real: margen % real después de comisiones
        ganancia_neta: $ que quedan después de comisiones
        comision_total: % total de comisiones
        desglose: dict con cada componente
    """
    if precio_costo <= 0:
        return {'precio_venta': 0, 'error': 'Costo debe ser > 0'}

    comision_total = regla.comision + regla.comision_pago
    denominador = 1.0 - regla.margen_objetivo - comision_total

    if denominador <= 0:
        return {
            'precio_venta': 0,
            'error': 'Margen (%.0f%%) + comisiones (%.0f%%) >= 100%%. Imposible.' % (
                regla.margen_objetivo * 100, comision_total * 100
            )
        }

    # Precio base
    precio_base = precio_costo / denominador

    # Recargo adicional
    precio_con_recargo = precio_base * (1 + regla.recargo)

    # Redondeo: al múltiplo más cercano, menos 1 (ej: 67.999)
    if regla.redondeo > 0:
        precio_redondeado = math.ceil(precio_con_recargo / regla.redondeo) * regla.redondeo - 1
    else:
        precio_redondeado = round(precio_con_recargo, 2)

    # Aplicar piso
    if regla.precio_minimo > 0:
        precio_redondeado = max(precio_redondeado, regla.precio_minimo)

    # Calcular margen real con el precio redondeado
    ingreso_neto = precio_redondeado * (1 - comision_total)
    ganancia = ingreso_neto - precio_costo
    margen_real = ganancia / precio_redondeado if precio_redondeado > 0 else 0

    return {
        'precio_venta': precio_redondeado,
        'precio_sin_redondear': round(precio_con_recargo, 2),
        'precio_costo': precio_costo,
        'margen_real': round(margen_real * 100, 1),
        'ganancia_neta': round(ganancia, 2),
        'comision_total_pct': round(comision_total * 100, 1),
        'comision_plataforma': round(precio_redondeado * regla.comision, 2),
        'comision_pago': round(precio_redondeado * regla.comision_pago, 2),
        'ingreso_neto': round(ingreso_neto, 2),
        'desglose': {
            'costo': precio_costo,
            'margen_objetivo': '%.0f%%' % (regla.margen_objetivo * 100),
            'comision_plataforma': '%.1f%%' % (regla.comision * 100),
            'comision_pago': '%.1f%%' % (regla.comision_pago * 100),
            'recargo': '%.1f%%' % (regla.recargo * 100),
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
    """Carga reglas desde un archivo JSON."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {k: ReglaCanal(**v) for k, v in data.items()}
    except FileNotFoundError:
        return REGLAS_DEFAULT.copy()
