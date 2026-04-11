"""
autorepo/routing.py — Routing y validación de depósitos para autocompensación H4/CALZALINDO.

Propósito
---------
Mapear depósitos físicos a empresas (H4 / CALZALINDO) y bases SQL
(MSGESTION03 / MSGESTION01), validar rutas origen→destino del motor
de autocompensación inter-depósito (fase F1) y filtrar arcs candidatos
según compatibilidad de rubros por local.

Contexto
--------
- Stock compartido en msgestionC.dbo.stock (vista UNION).
- Base pedidos (pedico1/pedico2) es compartida; la diferenciación
  por empresa ocurre al facturar (compras2).
- movistoc1/movistoc2 se asume SEPARADAS por base (hipótesis a
  validar mediante script SQL aparte).

Alcance F1 (core físico activo):
    0  Central VT
    2  Norte
    6  Cuore / Chovet
    7  Eva Perón / Melincué
    8  Junín / Alcorta
    11 Alternativo / Zapatería VT

Excluidos F1:
    1  Canal Digital (ML+TN)
    4  Marroquinería / Claudia (solo monitoreado, reporte frenado)

Virtuales (nunca entran al solver):
    9, 10, 198, 199

Fecha: 11-abr-2026
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Constantes públicas
# ---------------------------------------------------------------------------

DEPOS_AUTOREPO_F1: Tuple[int, ...] = (0, 2, 6, 7, 8, 11)
"""Depósitos que entran al solver de autocompensación F1."""

DEPOS_EXCLUIDOS_F1: Tuple[int, ...] = (1, 4)
"""Depósitos fuera del alcance F1: canal digital (1) y marroquinería (4)."""

DEPOS_MONITOREADOS: Tuple[int, ...] = (4,)
"""Depósitos con reporte frenado pero NO entran al solver."""

DEPOS_VIRTUALES: Tuple[int, ...] = (10, 198, 199)
"""Depósitos virtuales — NUNCA participan en autocompensación."""


DEPOSITO_NOMBRE: Dict[int, str] = {
    0: 'Central VT',
    1: 'Canal Digital (ML+TN)',
    2: 'Norte',
    4: 'Marroquinería / Claudia',
    6: 'Cuore / Chovet',
    7: 'Eva Perón / Melincué',
    8: 'Junín / Alcorta',
    9: 'Tokyo Express',
    11: 'Alternativo / Zapatería VT',
}


DEPOSITO_EMPRESA_DEFAULT: Dict[int, str] = {
    0: 'H4',            # Central: mayor parte del stock H4
    2: 'CALZALINDO',
    6: 'CALZALINDO',
    7: 'CALZALINDO',
    8: 'CALZALINDO',
    11: 'CALZALINDO',   # Alternativo / zapatería es CLZ
}
"""Empresa conceptual por defecto de cada depósito.

El stock es físicamente compartido entre bases pero el negocio dominante
del local define la base preferida para facturación/auditoría.
"""


DEPOSITO_RUBROS_EXCLUIDOS: Dict[int, Set[int]] = {
    # Depósito 4 (Marroquinería): no entra en F1, pero si se incluyera sólo
    # acepta rubro 8 (carteras). Pendiente de ajuste con Fernando.
    # 4: {1, 2, 3, 4, 5, 6, 7},
}
"""Rubros NO comercializables por depósito. Vacío = acepta todos los rubros."""


_EMPRESA_A_BASE: Dict[str, str] = {
    'H4': 'MSGESTION03',
    'CALZALINDO': 'MSGESTION01',
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Ruta:
    """Resultado de validar una ruta origen→destino para autocompensación."""
    origen: int
    destino: int
    base_origen: str
    base_destino: str
    empresa_origen: str
    empresa_destino: str
    cross_empresa: bool
    valida: bool
    motivo_invalidez: Optional[str]


# ---------------------------------------------------------------------------
# Helpers de mapping
# ---------------------------------------------------------------------------

def base_de_empresa(empresa: str) -> str:
    """Traduce nombre de empresa a base SQL.

    'H4'          -> 'MSGESTION03'
    'CALZALINDO'  -> 'MSGESTION01'
    Otro valor    -> ValueError
    """
    if empresa not in _EMPRESA_A_BASE:
        raise ValueError(
            f"Empresa desconocida: {empresa!r}. Valores válidos: {list(_EMPRESA_A_BASE)}"
        )
    return _EMPRESA_A_BASE[empresa]


def empresa_de_deposito(deposito: int) -> str:
    """Retorna la empresa default de un depósito.

    Fallback 'CALZALINDO' si el depósito no está mapeado explícitamente.
    """
    return DEPOSITO_EMPRESA_DEFAULT.get(deposito, 'CALZALINDO')


def nombre_deposito(deposito: int) -> str:
    """Retorna nombre legible del depósito. Fallback 'Depósito {N}'."""
    return DEPOSITO_NOMBRE.get(deposito, f'Depósito {deposito}')


def es_deposito_activo_f1(deposito: int) -> bool:
    """True si el depósito entra al solver de F1 (0, 2, 6, 7, 8, 11)."""
    return deposito in DEPOS_AUTOREPO_F1


def es_deposito_monitoreado(deposito: int) -> bool:
    """True si el depósito se monitorea pero NO entra al solver (ej: dep 4)."""
    return deposito in DEPOS_MONITOREADOS


# ---------------------------------------------------------------------------
# Validación de rutas
# ---------------------------------------------------------------------------

def validar_ruta(origen: int, destino: int) -> Ruta:
    """Valida una ruta origen→destino y devuelve un dataclass Ruta poblado.

    Reglas de invalidez (evaluadas en orden):
      1. origen == destino            → motivo 'mismo_deposito'
      2. cualquiera en virtuales      → motivo 'deposito_virtual'
      3. cualquiera fuera de F1       → motivo 'fuera_alcance_f1'

    Si todas pasan, `valida=True` y `motivo_invalidez=None`.
    """
    empresa_origen = empresa_de_deposito(origen)
    empresa_destino = empresa_de_deposito(destino)
    base_origen = base_de_empresa(empresa_origen)
    base_destino = base_de_empresa(empresa_destino)
    cross_empresa = empresa_origen != empresa_destino

    motivo: Optional[str] = None

    if origen == destino:
        motivo = 'mismo_deposito'
    elif origen in DEPOS_VIRTUALES or destino in DEPOS_VIRTUALES:
        motivo = 'deposito_virtual'
    elif origen not in DEPOS_AUTOREPO_F1 or destino not in DEPOS_AUTOREPO_F1:
        motivo = 'fuera_alcance_f1'

    return Ruta(
        origen=origen,
        destino=destino,
        base_origen=base_origen,
        base_destino=base_destino,
        empresa_origen=empresa_origen,
        empresa_destino=empresa_destino,
        cross_empresa=cross_empresa,
        valida=motivo is None,
        motivo_invalidez=motivo,
    )


# ---------------------------------------------------------------------------
# Filtros por rubro
# ---------------------------------------------------------------------------

def rubro_permitido_en_deposito(deposito: int, rubro: int) -> bool:
    """True si el rubro es comercializable en ese depósito.

    Lee `DEPOSITO_RUBROS_EXCLUIDOS`. Si el depósito no está en el dict,
    se considera que acepta todos los rubros.
    """
    excluidos = DEPOSITO_RUBROS_EXCLUIDOS.get(deposito)
    if not excluidos:
        return True
    return rubro not in excluidos


def filtrar_arcs_por_rubro(
    arcs: List[tuple],
    articulo_rubro: Dict[int, int],
) -> List[tuple]:
    """Filtra arcs cuyo destino NO admite el rubro del artículo.

    Parámetros
    ----------
    arcs : list de tuplas
        Cada tupla debe tener al menos (articulo, origen, destino, ...).
        Los elementos después del destino se preservan sin tocar.
    articulo_rubro : dict {articulo: rubro}
        Mapa artículo → rubro. Si falta el artículo se asume rubro permitido
        (no se filtra por precaución).

    Retorna
    -------
    Lista filtrada preservando el orden original.
    """
    out: List[tuple] = []
    for arc in arcs:
        if len(arc) < 3:
            # Arc malformado: lo dejamos pasar, no es responsabilidad del routing
            out.append(arc)
            continue
        articulo, _origen, destino = arc[0], arc[1], arc[2]
        rubro = articulo_rubro.get(articulo)
        if rubro is None:
            # Sin info de rubro → no filtramos
            out.append(arc)
            continue
        if rubro_permitido_en_deposito(destino, rubro):
            out.append(arc)
        # else: descartado
    return out


# ---------------------------------------------------------------------------
# Smoke-test / ejemplos
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== autorepo.routing — smoke test ===")
    print(f"DEPOS_AUTOREPO_F1     = {DEPOS_AUTOREPO_F1}")
    print(f"DEPOS_EXCLUIDOS_F1    = {DEPOS_EXCLUIDOS_F1}")
    print(f"DEPOS_MONITOREADOS    = {DEPOS_MONITOREADOS}")
    print(f"DEPOS_VIRTUALES       = {DEPOS_VIRTUALES}")
    print()

    print("--- validar_ruta(0, 8) [Central VT → Junín, cross-empresa] ---")
    r1 = validar_ruta(0, 8)
    print(r1)
    print()

    print("--- validar_ruta(4, 8) [dep 4 fuera de F1] ---")
    r2 = validar_ruta(4, 8)
    print(r2)
    print()

    print("--- validar_ruta(0, 1) [canal digital excluido F1] ---")
    r3 = validar_ruta(0, 1)
    print(r3)
    print()

    print("--- validar_ruta(2, 2) [mismo depósito] ---")
    r4 = validar_ruta(2, 2)
    print(r4)
    print()

    print("--- empresa_de_deposito(11) ---")
    print(empresa_de_deposito(11))
    print()

    print("--- base_de_empresa('H4') / base_de_empresa('CALZALINDO') ---")
    print(base_de_empresa('H4'), base_de_empresa('CALZALINDO'))
    print()

    print("--- filtrar_arcs_por_rubro([(100, 0, 8)], {100: 3}) ---")
    arcs_filtrados = filtrar_arcs_por_rubro([(100, 0, 8)], {100: 3})
    print(arcs_filtrados)
    print()

    print("--- nombre_deposito(6) / nombre_deposito(999) ---")
    print(nombre_deposito(6), "|", nombre_deposito(999))
