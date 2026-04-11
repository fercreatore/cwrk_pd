"""
autorepo/costos.py
==================

Módulo de cálculo de costos de transferencia entre depósitos para el motor
de autocompensación inter-depósito (H4 / CALZALINDO).

Propósito
---------
Evaluar si conviene mover pares de stock entre locales, considerando:

  - Costo fijo de armar un remito (depende de la ruta)
  - Costo variable por par (armado, embalaje, etiqueta)
  - Costo de riesgo (porcentaje del precio promedio del par)
  - Beneficio esperado (margen × probabilidad de venta en destino)
  - Canibalización (probabilidad de venta en origen)

Depósitos considerados (todos en Santa Fe):

  0  — Central Venado Tuerto
  2  — Norte
  6  — Cuore / Chovet
  7  — Eva Perón / Melincué
  8  — Junín
  11 — Alternativo / Zapatería VT

Este módulo es puro Python stdlib: sin dependencias externas, sin
Streamlit, sin pyodbc. Pensado para ser llamado desde el motor de
autocompensación (autorepo) y testeado unitariamente.

Fecha: 11-abr-2026
"""

from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Parámetros de costos (ajustables desde config futuro)
# ---------------------------------------------------------------------------
COSTOS_V1: dict = {
    'fijo_remito_central_vt': 8000,            # dep 0 <-> dep 11 (ambos en VT)
    'fijo_remito_satelite': 15000,             # 0/11 -> (2, 6, 7, 8)
    'fijo_remito_satelite_satelite': 25000,    # entre satélites no-VT
    'costo_var_por_par': 500,                  # armado + embalaje + etiqueta
    'riesgo_pct_precio': 0.015,                # 1.5% del precio promedio
    'minimo_pares_satelite': 15,
    'minimo_pares_intermitente': 25,
    'alfa_colchon': 1.30,                      # beneficio/costo >= alfa
    'umbral_p_venta_origen': 0.60,             # P(orig) > 0.6 * P(dest) -> NO mover
}


# ---------------------------------------------------------------------------
# Matriz de rutas: (origen, destino) -> tipo_ruta
# ---------------------------------------------------------------------------
TIPO_RUTA: dict = {
    # Ruta interna Venado Tuerto (Central <-> Alternativo/Zapatería VT)
    (0, 11): 'central_vt',
    (11, 0): 'central_vt',

    # Central (0) -> satélites
    (0, 2): 'satelite',
    (0, 6): 'satelite',
    (0, 7): 'satelite',
    (0, 8): 'satelite',

    # Alternativo VT (11) -> satélites
    (11, 2): 'satelite',
    (11, 6): 'satelite',
    (11, 7): 'satelite',
    (11, 8): 'satelite',

    # Satélites -> Central (0)
    (2, 0): 'satelite',
    (6, 0): 'satelite',
    (7, 0): 'satelite',
    (8, 0): 'satelite',

    # Satélites -> Alternativo VT (11)
    (2, 11): 'satelite',
    (6, 11): 'satelite',
    (7, 11): 'satelite',
    (8, 11): 'satelite',

    # Entre satélites (no-VT)
    (2, 6): 'satelite_satelite',
    (2, 7): 'satelite_satelite',
    (2, 8): 'satelite_satelite',
    (6, 2): 'satelite_satelite',
    (6, 7): 'satelite_satelite',
    (6, 8): 'satelite_satelite',
    (7, 2): 'satelite_satelite',
    (7, 6): 'satelite_satelite',
    (7, 8): 'satelite_satelite',
    (8, 2): 'satelite_satelite',
    (8, 6): 'satelite_satelite',
    (8, 7): 'satelite_satelite',
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass
class EvaluacionCosto:
    """Resultado detallado de evaluar el costo de una transferencia."""

    ruta: str                   # 'central_vt' | 'satelite' | 'satelite_satelite'
    pares: int
    precio_promedio_par: float
    fijo: float
    variable: float
    riesgo: float
    costo_total: float
    costo_por_par: float
    minimo_aplicable: int
    cumple_minimo: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def tipo_ruta(origen: int, destino: int) -> Optional[str]:
    """
    Retorna el tipo de ruta entre dos depósitos.

    Args:
        origen: Código del depósito de origen.
        destino: Código del depósito de destino.

    Returns:
        'central_vt' | 'satelite' | 'satelite_satelite' | None
    """
    return TIPO_RUTA.get((origen, destino))


def _fijo_por_ruta(ruta: str) -> float:
    """Retorna el costo fijo de remito para un tipo de ruta."""
    if ruta == 'central_vt':
        return float(COSTOS_V1['fijo_remito_central_vt'])
    if ruta == 'satelite':
        return float(COSTOS_V1['fijo_remito_satelite'])
    if ruta == 'satelite_satelite':
        return float(COSTOS_V1['fijo_remito_satelite_satelite'])
    raise ValueError(f"Ruta desconocida: {ruta!r}")


def _minimo_por_ruta(ruta: str) -> int:
    """
    Retorna el mínimo de pares aplicable para un tipo de ruta.

    - central_vt: sin mínimo (ruta interna diaria VT) -> 0
    - satelite: 15 pares
    - satelite_satelite: 25 pares
    """
    if ruta == 'central_vt':
        return 0
    if ruta == 'satelite':
        return int(COSTOS_V1['minimo_pares_satelite'])
    if ruta == 'satelite_satelite':
        return int(COSTOS_V1['minimo_pares_intermitente'])
    raise ValueError(f"Ruta desconocida: {ruta!r}")


# ---------------------------------------------------------------------------
# Cálculo de costo de transferencia
# ---------------------------------------------------------------------------
def costo_transferencia(
    origen: int,
    destino: int,
    pares: int,
    precio_promedio_par: float,
) -> EvaluacionCosto:
    """
    Calcula el costo total de una transferencia (remito) entre origen y destino.

    Fórmula:
        costo_total = fijo_ruta
                    + (pares * costo_var_por_par)
                    + (pares * precio_promedio_par * riesgo_pct)

        costo_por_par = costo_total / pares

    Args:
        origen: Código del depósito de origen.
        destino: Código del depósito de destino.
        pares: Cantidad de pares a mover (> 0).
        precio_promedio_par: Precio promedio por par (para cálculo de riesgo).

    Returns:
        EvaluacionCosto con el detalle del cálculo.

    Raises:
        ValueError: Si la ruta no existe o si pares <= 0.
    """
    if pares <= 0:
        raise ValueError(f"pares debe ser > 0, recibido: {pares}")

    ruta = tipo_ruta(origen, destino)
    if ruta is None:
        raise ValueError(
            f"Ruta desconocida entre origen={origen} y destino={destino}"
        )

    fijo = _fijo_por_ruta(ruta)
    variable = float(pares) * float(COSTOS_V1['costo_var_por_par'])
    riesgo = float(pares) * float(precio_promedio_par) * float(
        COSTOS_V1['riesgo_pct_precio']
    )
    costo_total = fijo + variable + riesgo
    costo_por_par = costo_total / float(pares)

    minimo = _minimo_por_ruta(ruta)
    cumple_minimo = pares >= minimo

    return EvaluacionCosto(
        ruta=ruta,
        pares=int(pares),
        precio_promedio_par=float(precio_promedio_par),
        fijo=fijo,
        variable=variable,
        riesgo=riesgo,
        costo_total=costo_total,
        costo_por_par=costo_por_par,
        minimo_aplicable=minimo,
        cumple_minimo=cumple_minimo,
    )


# ---------------------------------------------------------------------------
# Beneficio esperado
# ---------------------------------------------------------------------------
def beneficio_esperado(
    margen_par: float,
    prob_venta_destino: float,
    prob_venta_origen: float,
    pares: int,
    horizonte_dias: int = 30,
) -> float:
    """
    Calcula el beneficio esperado de mover 'pares' unidades al destino.

    Modelo:
        beneficio = margen * P(venta_dest) * pares
                  - margen * P(venta_orig) * pares * factor_canibaliz

    El factor de canibalización refleja que, si en origen también podían
    venderse, mover el stock ahí tiene un costo de oportunidad. Se usa un
    factor 1.0 (canibalización total): cada venta que se pierde en origen
    compensa una venta ganada en destino.

    Args:
        margen_par: Margen bruto esperado por par vendido (en $).
        prob_venta_destino: Probabilidad de venta en destino en el horizonte.
        prob_venta_origen: Probabilidad de venta en origen en el horizonte.
        pares: Cantidad de pares a mover.
        horizonte_dias: Horizonte del análisis (informativo, no afecta fórmula
            si las probabilidades ya vienen calculadas a ese horizonte).

    Returns:
        Beneficio esperado en $ (puede ser negativo).
    """
    # horizonte_dias se mantiene como parámetro por consistencia con el motor
    # de autocompensación; las probabilidades se asumen ya calculadas a ese
    # horizonte.
    _ = horizonte_dias

    factor_canibaliz = 1.0
    ganancia_destino = float(margen_par) * float(prob_venta_destino) * float(pares)
    perdida_origen = (
        float(margen_par)
        * float(prob_venta_origen)
        * float(pares)
        * factor_canibaliz
    )
    return ganancia_destino - perdida_origen


# ---------------------------------------------------------------------------
# Decisión conviene / no conviene transferir
# ---------------------------------------------------------------------------
def conviene_transferir(
    origen: int,
    destino: int,
    pares: int,
    precio_promedio_par: float,
    margen_par: float,
    prob_venta_destino: float,
    prob_venta_origen: float,
    horizonte_dias: int = 30,
) -> tuple[bool, str, float, float]:
    """
    Evalúa si conviene mover pares de origen a destino.

    Reglas (en orden de corto-circuito):
      1. Si la ruta no está en TIPO_RUTA -> (False, 'ruta_desconocida', 0, 0)
      2. Si prob_venta_origen > umbral * prob_venta_destino
            -> (False, 'origen_tambien_vende', costo, beneficio)
      3. Si pares < mínimo aplicable de la ruta
            -> (False, 'bajo_minimo', costo, beneficio)
      4. Si beneficio / costo < alfa_colchon
            -> (False, 'beneficio_insuficiente', costo, beneficio)
      5. Todo OK -> (True, 'conviene', costo, beneficio)

    Args:
        origen: Código depósito origen.
        destino: Código depósito destino.
        pares: Pares a mover.
        precio_promedio_par: Precio promedio por par (para cálculo riesgo).
        margen_par: Margen bruto por par vendido.
        prob_venta_destino: Probabilidad de venta en destino al horizonte.
        prob_venta_origen: Probabilidad de venta en origen al horizonte.
        horizonte_dias: Horizonte de análisis en días.

    Returns:
        Tupla (decision, razon, costo_total, beneficio_esperado).
        - decision: True si conviene mover.
        - razon: string con la razón (conviene | bajo_minimo | ...).
        - costo_total: costo total en $ (0 si ruta desconocida).
        - beneficio_esperado: beneficio en $ (0 si ruta desconocida).
    """
    # Regla 1: ruta existente
    ruta = tipo_ruta(origen, destino)
    if ruta is None:
        return (False, 'ruta_desconocida', 0.0, 0.0)

    # Calcular costo y beneficio para devolverlos en cualquier rama posterior
    evaluacion = costo_transferencia(origen, destino, pares, precio_promedio_par)
    costo_total = evaluacion.costo_total
    beneficio = beneficio_esperado(
        margen_par=margen_par,
        prob_venta_destino=prob_venta_destino,
        prob_venta_origen=prob_venta_origen,
        pares=pares,
        horizonte_dias=horizonte_dias,
    )

    # Regla 2: origen también vende bien -> no canibalizar
    umbral = float(COSTOS_V1['umbral_p_venta_origen'])
    if prob_venta_origen > umbral * prob_venta_destino:
        return (False, 'origen_tambien_vende', costo_total, beneficio)

    # Regla 3: mínimo de pares por ruta
    if not evaluacion.cumple_minimo:
        return (False, 'bajo_minimo', costo_total, beneficio)

    # Regla 4: colchón beneficio/costo
    alfa = float(COSTOS_V1['alfa_colchon'])
    if costo_total <= 0:
        # Defensa: no debería pasar, pero evitamos dividir por cero.
        return (False, 'costo_invalido', costo_total, beneficio)
    if (beneficio / costo_total) < alfa:
        return (False, 'beneficio_insuficiente', costo_total, beneficio)

    # Regla 5: todo OK
    return (True, 'conviene', costo_total, beneficio)


# ---------------------------------------------------------------------------
# Demo / casos de ejemplo
# ---------------------------------------------------------------------------
def _fmt_money(x: float) -> str:
    return f"${x:,.0f}"


def _print_decision(
    titulo: str,
    origen: int,
    destino: int,
    pares: int,
    precio_promedio_par: float,
    margen_par: float,
    prob_venta_destino: float,
    prob_venta_origen: float,
) -> None:
    print("=" * 72)
    print(f"CASO: {titulo}")
    print(
        f"  origen={origen}  destino={destino}  pares={pares}  "
        f"precio_prom={_fmt_money(precio_promedio_par)}"
    )
    print(
        f"  margen={_fmt_money(margen_par)}  "
        f"P(venta_dest)={prob_venta_destino:.2f}  "
        f"P(venta_orig)={prob_venta_origen:.2f}"
    )
    ruta = tipo_ruta(origen, destino)
    if ruta is None:
        print("  ruta: DESCONOCIDA")
    else:
        ev = costo_transferencia(origen, destino, pares, precio_promedio_par)
        print(
            f"  ruta={ev.ruta}  fijo={_fmt_money(ev.fijo)}  "
            f"variable={_fmt_money(ev.variable)}  riesgo={_fmt_money(ev.riesgo)}"
        )
        print(
            f"  costo_total={_fmt_money(ev.costo_total)}  "
            f"costo_por_par={_fmt_money(ev.costo_por_par)}  "
            f"minimo={ev.minimo_aplicable}  cumple_minimo={ev.cumple_minimo}"
        )

    decision, razon, costo, beneficio = conviene_transferir(
        origen=origen,
        destino=destino,
        pares=pares,
        precio_promedio_par=precio_promedio_par,
        margen_par=margen_par,
        prob_venta_destino=prob_venta_destino,
        prob_venta_origen=prob_venta_origen,
    )
    ratio = (beneficio / costo) if costo > 0 else 0.0
    print(
        f"  -> decision={decision}  razon={razon}  "
        f"beneficio={_fmt_money(beneficio)}  "
        f"costo={_fmt_money(costo)}  b/c={ratio:.2f}"
    )


if __name__ == "__main__":
    # Caso 1: VT <-> Central, 20 pares (ruta interna, sin mínimo).
    _print_decision(
        titulo="VT interna: Central (0) -> Alternativo VT (11), 20 pares",
        origen=0,
        destino=11,
        pares=20,
        precio_promedio_par=25000,
        margen_par=12000,
        prob_venta_destino=0.70,
        prob_venta_origen=0.20,
    )

    # Caso 2: Central -> Junín, 15 pares (cumple mínimo).
    _print_decision(
        titulo="Central (0) -> Junín (8), 15 pares",
        origen=0,
        destino=8,
        pares=15,
        precio_promedio_par=25000,
        margen_par=12000,
        prob_venta_destino=0.75,
        prob_venta_origen=0.30,
    )

    # Caso 3: Central -> Junín, 10 pares (NO cumple mínimo 15).
    _print_decision(
        titulo="Central (0) -> Junín (8), 10 pares (bajo mínimo)",
        origen=0,
        destino=8,
        pares=10,
        precio_promedio_par=25000,
        margen_par=12000,
        prob_venta_destino=0.75,
        prob_venta_origen=0.30,
    )

    # Caso 4: Junín -> Melincué, 30 pares (satelite <-> satelite, min 25).
    _print_decision(
        titulo="Junín (8) -> Melincué (7), 30 pares",
        origen=8,
        destino=7,
        pares=30,
        precio_promedio_par=22000,
        margen_par=10000,
        prob_venta_destino=0.70,
        prob_venta_origen=0.25,
    )

    # Caso 5: origen que también vende bien (canibalización).
    _print_decision(
        titulo="Central (0) -> Junín (8), 20 pares pero origen también vende",
        origen=0,
        destino=8,
        pares=20,
        precio_promedio_par=25000,
        margen_par=12000,
        prob_venta_destino=0.70,
        prob_venta_origen=0.60,
    )
    print("=" * 72)
