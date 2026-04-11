"""
autorepo/scoring.py
-------------------
Módulo de scoring compuesto 0-100 por tripla (articulo, origen, destino)
para el motor de autocompensación inter-depósito H4 / CALZALINDO.

Propósito
~~~~~~~~~
Calcular la prioridad que el solver MILP asignará a cada arco candidato
de movimiento de stock entre depósitos. El score combina 8 señales
normalizadas y aplica:

  * Gate estacional (EST < 0.3 → score 0)
  * Penalización drag (hasta 40 pts si rompe la curva del origen)
  * Gate de aceptación (score ≥ 55 y pares ≥ 3)

Fórmula (plan agente 3, 11-abr-2026):

    SCORE = 100 · EST · [
        0.25·DOS_dest
      + 0.18·V_dest
      + 0.15·EXC_orig
      + 0.12·AFF
      + 0.10·ABCXYZ
      + 0.08·MRG
      + 0.07·EDAD
      + 0.05·(1 - riesgo_curva)
    ] − PENAL_drag

Referencia: docs del agente 3 del proyecto autorepo H4/CALZALINDO.
Fecha: 11-abr-2026.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# scipy es opcional - si no está, chi2 retorna fallback "True para todos"
try:
    from scipy.stats import chi2_contingency  # type: ignore
    _HAS_SCIPY = True
except Exception:  # pragma: no cover
    _HAS_SCIPY = False


# ---------------------------------------------------------------------------
# Constantes del scoring
# ---------------------------------------------------------------------------

ABCXYZ_SCORE: dict[str, float] = {
    'AX': 1.00, 'AY': 0.85, 'AZ': 0.60,
    'BX': 0.80, 'BY': 0.65, 'BZ': 0.35,
    'CX': 0.50, 'CY': 0.25, 'CZ': 0.10,
}

# Pesos de cada componente (deben sumar 1.0)
PESO_DOS_DEST = 0.25
PESO_V_DEST = 0.18
PESO_EXC_ORIG = 0.15
PESO_AFF = 0.12
PESO_ABCXYZ = 0.10
PESO_MRG = 0.08
PESO_EDAD = 0.07
PESO_RIESGO_CURVA = 0.05

# Gates
EST_MINIMO = 0.3           # debajo de esto el arco se apaga
SCORE_MIN_ACEPTACION = 55.0
PARES_MIN_ARCO = 3
PENAL_DRAG_MAX_DEFAULT = 40.0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class InputScore:
    """Entrada para calcular el score de una tripla (articulo, origen, destino)."""
    articulo: int
    origen: int
    destino: int
    stock_origen: int
    stock_destino: int
    vel_origen_dia: float
    vel_destino_dia: float
    p95_vel_categoria: float        # para normalizar V_dest
    abcxyz_clase: str               # 'AX','BY',...
    margen_pct: float               # 0-100
    afinidad_marca_local: float     # 0-1 (lift capeado)
    dias_stock_origen: int
    factor_estacional: float        # 0-1
    riesgo_drag: float              # 0-1 (de curva_talles)


@dataclass
class ResultadoScore:
    """Resultado del scoring para un arco."""
    articulo: int
    origen: int
    destino: int
    score: float                          # 0-100 (ya con penalización)
    componentes: dict[str, float] = field(default_factory=dict)
    bruto: float = 0.0                    # antes de restar penal_drag
    penal_drag: float = 0.0
    aceptable: bool = False               # score >= SCORE_MIN_ACEPTACION


# ---------------------------------------------------------------------------
# Helpers de normalización
# ---------------------------------------------------------------------------

def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _dos_dest(stock_dest: int, vel_dest: float) -> float:
    """Days-of-stock destino → urgencia. 1 = roto."""
    denom = max(vel_dest * 30.0, 1.0)
    return _clamp(1.0 - (stock_dest / denom))


def _v_dest_norm(vel_dest: float, p95_vel: float) -> float:
    """Velocidad destino normalizada por p95 de la categoría."""
    if p95_vel <= 0:
        return 0.0
    return _clamp(vel_dest / p95_vel)


def _exc_origen(stock_orig: int, vel_orig: float) -> float:
    """Exceso en origen: >60 días coverage empieza a contar, satura en 180."""
    vel = max(vel_orig, 0.01)
    coverage = stock_orig / vel
    return _clamp((coverage - 60.0) / 120.0)


def _mrg_norm(margen_pct: float) -> float:
    """Margen normalizado: 0% → 0, 60%+ → 1."""
    return _clamp(max(margen_pct, 0.0) / 60.0)


def _edad_norm(dias_stock_origen: int) -> float:
    """Edad del stock: 180+ días → 1."""
    return _clamp(dias_stock_origen / 180.0)


def _abcxyz_lookup(clase: str) -> float:
    return ABCXYZ_SCORE.get(clase.upper().strip(), 0.10)


# ---------------------------------------------------------------------------
# Score principal
# ---------------------------------------------------------------------------

def calcular_score(
    inp: InputScore,
    penal_drag_max: float = PENAL_DRAG_MAX_DEFAULT,
) -> ResultadoScore:
    """
    Aplica la fórmula compuesta del plan (agente 3).

    Pasos:
      1. Normaliza las 8 señales 0-1.
      2. Suma ponderada × EST × 100 = bruto.
      3. Resta penal_drag = riesgo_drag * penal_drag_max.
      4. Gate EST < 0.3 → score = 0.
      5. Flag aceptable si score ≥ SCORE_MIN_ACEPTACION.
    """
    # Normalizaciones
    dos_dest = _dos_dest(inp.stock_destino, inp.vel_destino_dia)
    v_dest = _v_dest_norm(inp.vel_destino_dia, inp.p95_vel_categoria)
    exc_orig = _exc_origen(inp.stock_origen, inp.vel_origen_dia)
    aff = _clamp(inp.afinidad_marca_local)
    abcxyz = _abcxyz_lookup(inp.abcxyz_clase)
    mrg = _mrg_norm(inp.margen_pct)
    edad = _edad_norm(inp.dias_stock_origen)
    est = _clamp(inp.factor_estacional)
    riesgo = _clamp(inp.riesgo_drag)
    curva_ok = 1.0 - riesgo

    componentes = {
        'DOS_dest': dos_dest,
        'V_dest': v_dest,
        'EXC_orig': exc_orig,
        'AFF': aff,
        'ABCXYZ': abcxyz,
        'MRG': mrg,
        'EDAD': edad,
        'curva_ok': curva_ok,
        'EST': est,
        'riesgo_drag': riesgo,
    }

    # Gate estacional duro
    if est < EST_MINIMO:
        return ResultadoScore(
            articulo=inp.articulo,
            origen=inp.origen,
            destino=inp.destino,
            score=0.0,
            componentes=componentes,
            bruto=0.0,
            penal_drag=0.0,
            aceptable=False,
        )

    # Suma ponderada
    suma = (
        PESO_DOS_DEST * dos_dest
        + PESO_V_DEST * v_dest
        + PESO_EXC_ORIG * exc_orig
        + PESO_AFF * aff
        + PESO_ABCXYZ * abcxyz
        + PESO_MRG * mrg
        + PESO_EDAD * edad
        + PESO_RIESGO_CURVA * curva_ok
    )

    bruto = 100.0 * est * suma
    penal = riesgo * penal_drag_max
    score = max(0.0, bruto - penal)

    return ResultadoScore(
        articulo=inp.articulo,
        origen=inp.origen,
        destino=inp.destino,
        score=score,
        componentes=componentes,
        bruto=bruto,
        penal_drag=penal,
        aceptable=(score >= SCORE_MIN_ACEPTACION),
    )


# ---------------------------------------------------------------------------
# Filtros de aceptación
# ---------------------------------------------------------------------------

def filtrar_arcos_aceptables(
    scores: list[ResultadoScore],
    min_score: float = SCORE_MIN_ACEPTACION,
    min_pares: int = PARES_MIN_ARCO,
    pares_por_arco: Optional[dict[tuple, int]] = None,
) -> list[ResultadoScore]:
    """
    Descarta arcos con score < min_score o con pares < min_pares.

    `pares_por_arco` es un dict opcional {(articulo, origen, destino): pares}.
    Si no se pasa, el filtro de pares se omite.
    """
    out: list[ResultadoScore] = []
    for r in scores:
        if r.score < min_score:
            continue
        if pares_por_arco is not None:
            key = (r.articulo, r.origen, r.destino)
            if pares_por_arco.get(key, 0) < min_pares:
                continue
        out.append(r)
    return out


# ---------------------------------------------------------------------------
# Afinidad marca-local
# ---------------------------------------------------------------------------

def afinidad_marca_local_lift(
    ventas_marca_local: int,
    ventas_local_total: int,
    ventas_marca_global: int,
    ventas_global_total: int,
) -> float:
    """
    Lift marca-local:

        lift = (ventas_marca_local/ventas_local_total)
             / (ventas_marca_global/ventas_global_total)

    AFF = min(lift / 2, 1.0)

    Retorna 0.5 (neutro) si cualquier denominador es 0.
    """
    if ventas_local_total <= 0 or ventas_global_total <= 0:
        return 0.5
    share_local = ventas_marca_local / ventas_local_total
    share_global = ventas_marca_global / ventas_global_total
    if share_global <= 0:
        return 0.5
    lift = share_local / share_global
    return min(lift / 2.0, 1.0)


def chi2_marca_local_significativo(
    tabla_contingencia: dict[tuple[int, int], int],
    p_threshold: float = 0.05,
    min_n: int = 30,
) -> dict[int, bool]:
    """
    Chi-cuadrado sobre tabla marca × local.

    Recibe un dict {(marca, local): ventas}. Para cada marca, arma su fila
    contra las demás (marginal total del local sin esa marca) y corre
    chi2_contingency. Marca como significativa si p < p_threshold y
    total de ventas de la marca ≥ min_n.

    Fallback: si scipy.stats no está disponible, retorna todos True
    (no filtra nada, preservando toda la señal de lift).
    """
    # Agregados
    marcas: set[int] = set()
    locales: set[int] = set()
    for (m, l), _ in tabla_contingencia.items():
        marcas.add(m)
        locales.add(l)

    locales_list = sorted(locales)

    # Totales por local
    total_por_local: dict[int, int] = {l: 0 for l in locales_list}
    total_por_marca: dict[int, int] = {m: 0 for m in marcas}
    for (m, l), v in tabla_contingencia.items():
        total_por_local[l] += v
        total_por_marca[m] += v

    resultado: dict[int, bool] = {}

    if not _HAS_SCIPY:
        # fallback: no filtro, todos pasan
        for m in marcas:
            resultado[m] = True
        return resultado

    for m in marcas:
        if total_por_marca[m] < min_n:
            resultado[m] = False
            continue

        fila_marca = [tabla_contingencia.get((m, l), 0) for l in locales_list]
        fila_otras = [
            total_por_local[l] - tabla_contingencia.get((m, l), 0)
            for l in locales_list
        ]

        # chi2 requiere al menos 2 columnas con algún valor
        if sum(fila_marca) == 0 or sum(fila_otras) == 0:
            resultado[m] = False
            continue

        try:
            tabla = [fila_marca, fila_otras]
            _, p, _, _ = chi2_contingency(tabla)
            resultado[m] = bool(p < p_threshold)
        except Exception:
            resultado[m] = False

    return resultado


# ---------------------------------------------------------------------------
# Demo / smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 1) Arc urgente claro: destino roto, origen con exceso, temporada activa
    inp1 = InputScore(
        articulo=100, origen=0, destino=8,
        stock_origen=40, stock_destino=1,
        vel_origen_dia=0.2, vel_destino_dia=1.5,
        p95_vel_categoria=2.0,
        abcxyz_clase='AX',
        margen_pct=45,
        afinidad_marca_local=0.8,
        dias_stock_origen=120,
        factor_estacional=1.0,
        riesgo_drag=0.0,
    )
    r1 = calcular_score(inp1)
    print(f"Caso urgente: score={r1.score:.1f} aceptable={r1.aceptable}")
    print(f"  componentes: { {k: round(v, 3) for k, v in r1.componentes.items()} }")

    # 2) Fuera de temporada → score=0
    inp2 = InputScore(**{**inp1.__dict__, 'factor_estacional': 0.1})
    r2 = calcular_score(inp2)
    print(f"Fuera temp: score={r2.score:.1f}")  # esperado 0

    # 3) Rompe curva origen → penalizado
    inp3 = InputScore(**{**inp1.__dict__, 'riesgo_drag': 1.0})
    r3 = calcular_score(inp3)
    print(f"Drag: score={r3.score:.1f} penal={r3.penal_drag}")
