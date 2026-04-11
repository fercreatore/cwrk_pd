"""autorepo.umbrales — Clasificación de estado operativo de stock.

Propósito
---------
Para cada combinación (artículo, depósito), determinar el estado operativo
del stock (QUIEBRE_CRITICO / ALERTA / OK / SOBRESTOCK / DEAD_STOCK) y los
umbrales aplicables para decidir transferencias inter-depósito.

Esta capa es PURA LÓGICA: no ejecuta queries SQL ni depende de Streamlit /
pyodbc. Las queries de velocidad, stock y compras viven en otro módulo y
alimentan estas funciones como parámetros.

Fecha: 11-abr-2026
Referencia: plan agente 4 — sistema de reposición automática inter-depósito.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

try:
    from scipy.stats import norm, poisson  # type: ignore
    _HAS_SCIPY = True
except Exception:  # pragma: no cover - fallback si no hay scipy
    _HAS_SCIPY = False


Estado = Literal['QUIEBRE_CRITICO', 'ALERTA', 'OK', 'SOBRESTOCK', 'DEAD_STOCK']


UMBRALES_V1 = {
    'sobrestock_temp_activa_dias': 75,
    'sobrestock_temp_inactiva_dias': 45,
    'sobrestock_basicos_dias': 90,
    'sobrestock_clase_c_dias': 120,
    'quiebre_critico_dias': 7,
    'quiebre_alerta_dias': 14,
    'lead_time_interno_dias': 2,
    'service_level_AX': 0.97,
    'service_level_AZ': 0.98,
    'service_level_C': 0.90,
    'dead_stock_dias_sin_venta': 90,
    'dead_stock_dias_sin_compra': 180,
    'quiebre_nuevo_ratio': 0.66,
}


# Subrubros considerados "básicos" (commodity, baja estacionalidad).
# Por ahora lista conservadora: medias y ojotas. Ampliar según se validen más.
SUBRUBROS_BASICOS = {
    # Placeholder: ajustar con los códigos reales cuando se confirmen contra
    # la tabla de subrubros del ERP. Mantener como set de int.
}


@dataclass
class EstadoStock:
    """Resultado de clasificar un (artículo, depósito)."""

    articulo: int
    deposito: int
    stock_actual: int
    vel_diaria: float        # velocidad real corregida (sin meses quebrados)
    dias_cobertura: float
    estado: Estado
    safety_stock: int
    abcxyz_clase: str        # 'AX','AY','BZ', etc.
    subrubro: int
    temporada_activa: bool
    dias_sin_venta: int
    dias_sin_compra: int


# ---------------------------------------------------------------------------
# Safety stock
# ---------------------------------------------------------------------------

# Tabla de z_alpha para fallback (normal approximation).
_Z_FALLBACK = {
    0.90: 1.28,
    0.95: 1.645,
    0.97: 1.88,
    0.98: 2.05,
    0.99: 2.33,
}


def _z_from_service_level(service_level: float) -> float:
    """Retorna z_alpha para un nivel de servicio dado.

    Usa scipy.stats.norm.ppf si está disponible; si no, la tabla fallback
    con el valor más cercano por debajo/igual.
    """
    if _HAS_SCIPY:
        return float(norm.ppf(service_level))
    # Fallback: buscar el valor tabulado más cercano.
    if service_level in _Z_FALLBACK:
        return _Z_FALLBACK[service_level]
    # Interpolación simple: tomar el más próximo.
    keys = sorted(_Z_FALLBACK.keys())
    closest = min(keys, key=lambda k: abs(k - service_level))
    return _Z_FALLBACK[closest]


def safety_stock_poisson(
    vel_diaria: float,
    lead_time_dias: int,
    service_level: float,
) -> int:
    """Safety stock vía distribución Poisson.

    Para calzado el CV de demanda es moderado, asumimos Poisson (var = mean).
    Si scipy está disponible usamos la inversa exacta (poisson.ppf); si no,
    aproximación normal: ss = ceil(z * sqrt(lambda)), con lambda = vel*lead.
    """
    if vel_diaria <= 0 or lead_time_dias <= 0:
        return 0

    lambda_lt = vel_diaria * lead_time_dias  # demanda esperada durante lead time

    if _HAS_SCIPY:
        # Punto de reorden = ppf(service_level) sobre Poisson(lambda_lt).
        # Safety stock = punto de reorden - demanda media.
        reorder_point = float(poisson.ppf(service_level, lambda_lt))
        ss = max(0.0, reorder_point - lambda_lt)
        return int(math.ceil(ss))

    # Fallback normal: ss = z * sqrt(lambda_lt)
    z = _z_from_service_level(service_level)
    ss = z * math.sqrt(lambda_lt)
    return int(math.ceil(ss))


def _service_level_for_class(abcxyz_clase: str) -> float:
    """Nivel de servicio según segmentación ABC×XYZ."""
    clase = (abcxyz_clase or '').upper().strip()
    if clase.startswith('C'):
        return UMBRALES_V1['service_level_C']
    # Clase A y B: diferenciar por X/Y/Z.
    # AX = alta importancia + baja variabilidad → 0.97
    # AZ = alta importancia + alta variabilidad → 0.98 (protegerse más)
    if clase.endswith('Z'):
        return UMBRALES_V1['service_level_AZ']
    return UMBRALES_V1['service_level_AX']


# ---------------------------------------------------------------------------
# Clasificación principal
# ---------------------------------------------------------------------------


def _es_basico(subrubro: int) -> bool:
    return subrubro in SUBRUBROS_BASICOS


def _umbral_sobrestock_dias(
    abcxyz_clase: str,
    subrubro: int,
    temporada_activa: bool,
) -> int:
    """Retorna el umbral (en días de cobertura) por encima del cual consideramos
    sobrestock, según el tipo de producto y la temporada."""
    clase = (abcxyz_clase or '').upper().strip()

    # Clase C: tolerancia más alta porque son productos de cola larga.
    if clase.startswith('C'):
        return UMBRALES_V1['sobrestock_clase_c_dias']

    # Básicos (medias, ojotas, commodity): 90 días.
    if _es_basico(subrubro):
        return UMBRALES_V1['sobrestock_basicos_dias']

    # Temporada activa vs inactiva: distinta tolerancia.
    if temporada_activa:
        return UMBRALES_V1['sobrestock_temp_activa_dias']
    return UMBRALES_V1['sobrestock_temp_inactiva_dias']


def clasificar_stock(
    articulo: int,
    deposito: int,
    stock_actual: int,
    vel_diaria: float,
    abcxyz_clase: str,
    subrubro: int,
    temporada_activa: bool,
    dias_sin_venta: int,
    dias_sin_compra: int,
    std_diaria: float = 0.0,
) -> EstadoStock:
    """Retorna el estado del stock para ese (artículo, depósito).

    Reglas (plan agente 4):
      1. dias_cobertura = stock / max(vel, 0.001)
      2. QUIEBRE_CRITICO si cobertura < 7 días.
      3. ALERTA si 7 <= cobertura < 14.
      4. DEAD_STOCK si dias_sin_venta>90 y dias_sin_compra>180 y stock>0.
      5. SOBRESTOCK si cobertura > umbral según (clase, básico, temporada).
      6. Si vel_diaria==0 → SOBRESTOCK si stock>0, OK si stock=0.
      7. Resto: OK.
    """
    service_level = _service_level_for_class(abcxyz_clase)
    ss = safety_stock_poisson(
        vel_diaria=vel_diaria,
        lead_time_dias=UMBRALES_V1['lead_time_interno_dias'],
        service_level=service_level,
    )

    # Caso especial: sin velocidad de venta.
    if vel_diaria <= 0:
        # Aún así puede ser dead stock si llevamos mucho sin vender y sin comprar.
        if (stock_actual > 0
                and dias_sin_venta > UMBRALES_V1['dead_stock_dias_sin_venta']
                and dias_sin_compra > UMBRALES_V1['dead_stock_dias_sin_compra']):
            estado: Estado = 'DEAD_STOCK'
        elif stock_actual > 0:
            estado = 'SOBRESTOCK'
        else:
            estado = 'OK'
        dias_cob = float('inf') if stock_actual > 0 else 0.0
        return EstadoStock(
            articulo=articulo,
            deposito=deposito,
            stock_actual=stock_actual,
            vel_diaria=vel_diaria,
            dias_cobertura=dias_cob,
            estado=estado,
            safety_stock=ss,
            abcxyz_clase=abcxyz_clase,
            subrubro=subrubro,
            temporada_activa=temporada_activa,
            dias_sin_venta=dias_sin_venta,
            dias_sin_compra=dias_sin_compra,
        )

    dias_cobertura = stock_actual / max(vel_diaria, 0.001)

    # Dead stock tiene prioridad sobre sobrestock si cumple la doble condición.
    if (stock_actual > 0
            and dias_sin_venta > UMBRALES_V1['dead_stock_dias_sin_venta']
            and dias_sin_compra > UMBRALES_V1['dead_stock_dias_sin_compra']):
        estado = 'DEAD_STOCK'
    elif dias_cobertura < UMBRALES_V1['quiebre_critico_dias']:
        estado = 'QUIEBRE_CRITICO'
    elif dias_cobertura < UMBRALES_V1['quiebre_alerta_dias']:
        estado = 'ALERTA'
    else:
        umbral_sobre = _umbral_sobrestock_dias(
            abcxyz_clase, subrubro, temporada_activa
        )
        if dias_cobertura > umbral_sobre:
            estado = 'SOBRESTOCK'
        else:
            estado = 'OK'

    return EstadoStock(
        articulo=articulo,
        deposito=deposito,
        stock_actual=stock_actual,
        vel_diaria=vel_diaria,
        dias_cobertura=dias_cobertura,
        estado=estado,
        safety_stock=ss,
        abcxyz_clase=abcxyz_clase,
        subrubro=subrubro,
        temporada_activa=temporada_activa,
        dias_sin_venta=dias_sin_venta,
        dias_sin_compra=dias_sin_compra,
    )


# ---------------------------------------------------------------------------
# Escasez crónica
# ---------------------------------------------------------------------------


def es_escasez_cronica(
    articulo: int,
    meses_quebrados_12m: int,
    meses_quebrados_3m: int,
) -> bool:
    """True si el artículo está crónicamente roto y NO vale la pena alertar.

    Regla (plan agente 4):
      - >75% de quiebre histórico en 12 meses (>= 9 meses quebrados de 12).
      - AND el quiebre NO es reciente: ratio 3m/12m < 0.66.

    Es decir: si viene quebrado desde hace rato Y los últimos 3 meses no
    concentran el daño, asumimos que es un producto con oferta estructural
    limitada — alertarlo genera ruido.
    """
    # Validación defensiva.
    if meses_quebrados_12m < 0 or meses_quebrados_3m < 0:
        return False

    # <75% no es crónico.
    if meses_quebrados_12m < 9:  # 9/12 = 0.75
        return False

    # Si todos los meses del último trimestre vienen quebrados y sólo eso,
    # puede ser un quiebre NUEVO — no crónico.
    if meses_quebrados_12m <= 0:
        return False

    # Ratio: qué proporción del quiebre histórico está concentrado en los
    # últimos 3 meses. Si >=0.66, el quiebre es reciente → NO lo marcamos
    # como crónico, sí alertamos.
    ratio_reciente = meses_quebrados_3m / meses_quebrados_12m
    return ratio_reciente < UMBRALES_V1['quiebre_nuevo_ratio']


# ---------------------------------------------------------------------------
# Demo / smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("UMBRALES_V1:", UMBRALES_V1)
    print()

    # Ejemplo 1: Quiebre crítico
    e1 = clasificar_stock(
        articulo=12345,
        deposito=8,
        stock_actual=2,
        vel_diaria=1.5,           # 1.33 días de cobertura
        abcxyz_clase='AX',
        subrubro=15,
        temporada_activa=True,
        dias_sin_venta=1,
        dias_sin_compra=30,
    )
    print("Ej1 (quiebre crítico):", e1)
    print()

    # Ejemplo 2: Sobrestock en temporada inactiva
    e2 = clasificar_stock(
        articulo=67890,
        deposito=8,
        stock_actual=200,
        vel_diaria=2.0,           # 100 días de cobertura, temp inactiva → sobrestock
        abcxyz_clase='BY',
        subrubro=20,
        temporada_activa=False,
        dias_sin_venta=5,
        dias_sin_compra=60,
    )
    print("Ej2 (sobrestock temp inactiva):", e2)
    print()

    # Ejemplo 3: Dead stock
    e3 = clasificar_stock(
        articulo=99999,
        deposito=8,
        stock_actual=10,
        vel_diaria=0.0,
        abcxyz_clase='CZ',
        subrubro=30,
        temporada_activa=False,
        dias_sin_venta=120,
        dias_sin_compra=240,
    )
    print("Ej3 (dead stock):", e3)
    print()

    # Bonus: escasez crónica
    # Caso A: quebrado 11 de 12 meses y solo 1 de los últimos 3 — ratio 1/11=0.09
    # < 0.66 → crónico, no alertar.
    print("escasez cronica (11/12 hist, 1/3 reciente):",
          es_escasez_cronica(1, 11, 1))
    # Caso B: quebrado 9 de 12 meses pero los 3 últimos vienen quebrados
    # ratio 3/9=0.33 < 0.66 → sigue siendo crónico (el daño no se concentra en 3m)
    print("escasez cronica (9/12 hist, 3/3 reciente):",
          es_escasez_cronica(1, 9, 3))
    # Caso C: quebrado 4 de 12 meses → <75%, no crónico.
    print("escasez cronica (4/12 hist, 3/3 reciente):",
          es_escasez_cronica(1, 4, 3))
