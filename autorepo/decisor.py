"""
autorepo/decisor.py
===================

Motor de decisión (MILP + fallback greedy) para autocompensación
inter-depósito H4 / CALZALINDO.

Orquesta el flujo completo de autorepo F1:

    estados (list[EstadoStock])
        → construir_arcos_candidatos  → list[(art, origen, destino)]
        → calcular_scores_arcos       → list[ResultadoScore]  (>= SCORE_MIN_ACEPTACION)
        → resolver_milp_ortools       → dict[(art,o,d) -> cantidad]
            (con fallback greedy si ortools no está disponible)
        → consolidar_propuestas       → list[Propuesta] agrupadas por (origen,destino)

Restricciones del MILP:
    x[i,o,d] ∈ ℤ≥0
    Σ_d x[i,o,d]              <= exceso_origen[i,o]
    Σ_o x[i,o,d]              <= demanda_destino[i,d]
    Σ_i,o precio[i] * x[i,o,d] <= presup_destino[d]
    Objetivo: max Σ score[i,o,d] * x[i,o,d]

El piso mínimo de pares por ruta (central_vt=0, satelite=15, satelite_satelite=25)
se aplica POST-solver en consolidar_propuestas, no dentro del MILP, para no
inflar variables (se marcarían como motivo_descarte='bajo_minimo').

Fecha: 11-abr-2026.
Referencia: plan agente "decisor" del proyecto autorepo H4/CALZALINDO.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from autorepo.scoring import (
    InputScore,
    ResultadoScore,
    calcular_score,
    SCORE_MIN_ACEPTACION,
    PARES_MIN_ARCO,
)
from autorepo.umbrales import EstadoStock
from autorepo.costos import (
    conviene_transferir,
    costo_transferencia,
    tipo_ruta,
    COSTOS_V1,
)
from autorepo.routing import (
    validar_ruta,
    DEPOS_AUTOREPO_F1,
    filtrar_arcs_por_rubro,
)
from autorepo.curva_talles import riesgo_drag_effect


log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses públicas
# ---------------------------------------------------------------------------


@dataclass
class DatosArticulo:
    """Datos auxiliares por artículo necesarios para scoring y costos."""

    articulo: int
    subrubro: int
    rubro: int
    marca: int
    precio_costo: float
    margen_pct: float
    abcxyz_clase: str
    factor_estacional: float                            # 0-1
    afinidad_local: dict[int, float]                    # {deposito: AFF 0-1}
    curva_ideal_subrubro: dict[int, float]              # {talle: pct 0-1}
    stock_origen_por_talle: dict[int, dict[int, int]] = field(default_factory=dict)
    """{deposito: {talle: n}} para el cálculo de drag effect en origen."""
    talle_objeto: Optional[int] = None
    """Talle específico del SKU si el arco es talle-a-talle."""


@dataclass
class LineaPropuesta:
    articulo: int
    cantidad: int
    score: float
    precio_costo: float
    motivo: str  # QUIEBRE_INMINENTE | SOBRESTOCK | DEAD_STOCK_REUTIL


@dataclass
class Propuesta:
    tipo: str  # URGENTE | REBALANCEO
    origen: int
    destino: int
    lineas: list[LineaPropuesta]
    total_pares: int
    total_costo_cer: float           # costo valuado en $ (precio_costo × pares)
    score_promedio: float
    beneficio_esperado: float        # beneficio simple (margen × pares)
    costo_transferencia: float       # costo logístico (fijo + variable + riesgo)
    cumple_minimo: bool
    motivo_descarte: Optional[str] = None


@dataclass
class ResultadoDecisor:
    propuestas: list[Propuesta]
    arcs_evaluados: int
    arcs_con_score_valido: int
    solver_usado: str  # 'ORTOOLS' | 'GREEDY_FALLBACK'
    tiempo_ms: int
    presupuesto_restante: dict[int, float]


# ---------------------------------------------------------------------------
# Paso 1: construir arcos candidatos
# ---------------------------------------------------------------------------


def _exceso_origen(estado: EstadoStock) -> int:
    """Pares excedentes que podemos mover desde origen.

    Aproximación: stock - vel * 60 (queremos dejarle al origen 60 días de
    cobertura como mínimo). Para DEAD_STOCK con vel=0 → todo el stock.
    """
    if estado.estado not in ('SOBRESTOCK', 'DEAD_STOCK'):
        return 0
    if estado.vel_diaria <= 0:
        return max(0, int(estado.stock_actual))
    reserva = estado.vel_diaria * 60.0
    return max(0, int(estado.stock_actual - reserva))


def _demanda_destino(estado: EstadoStock) -> int:
    """Pares faltantes para cubrir 14 días en el destino.

    Aproximación: max(0, vel*14 - stock). Si el destino está en ALERTA o
    QUIEBRE_CRITICO, la demanda es positiva. Para OK o superiores es 0.
    """
    if estado.estado not in ('QUIEBRE_CRITICO', 'ALERTA'):
        return 0
    objetivo = estado.vel_diaria * 14.0
    return max(0, int(round(objetivo - estado.stock_actual)))


def construir_arcos_candidatos(
    estados: list[EstadoStock],
    modo: str = 'REBALANCEO',
) -> list[tuple[int, int, int]]:
    """Genera tuplas (articulo, origen, destino) que pasan los filtros básicos."""
    modo = (modo or 'REBALANCEO').upper()
    estados_dep_f1 = [e for e in estados if e.deposito in DEPOS_AUTOREPO_F1]

    # Indexar por artículo
    por_articulo: dict[int, list[EstadoStock]] = {}
    for e in estados_dep_f1:
        por_articulo.setdefault(e.articulo, []).append(e)

    arcos: list[tuple[int, int, int]] = []
    for articulo, estados_art in por_articulo.items():
        origenes = [e for e in estados_art if e.estado in ('SOBRESTOCK', 'DEAD_STOCK')]
        if not origenes:
            continue

        if modo == 'URGENTE':
            destinos = [e for e in estados_art if e.estado == 'QUIEBRE_CRITICO']
        else:
            destinos = [e for e in estados_art if e.estado in ('QUIEBRE_CRITICO', 'ALERTA')]
        if not destinos:
            continue

        for o in origenes:
            if _exceso_origen(o) <= 0:
                continue
            for d in destinos:
                if o.deposito == d.deposito:
                    continue
                if _demanda_destino(d) <= 0:
                    continue
                ruta = validar_ruta(o.deposito, d.deposito)
                if not ruta.valida:
                    continue
                arcos.append((articulo, o.deposito, d.deposito))

    return arcos


# ---------------------------------------------------------------------------
# Paso 2: calcular scores
# ---------------------------------------------------------------------------


def calcular_scores_arcos(
    arcos: list[tuple[int, int, int]],
    estados_idx: dict[tuple[int, int], EstadoStock],
    datos_art: dict[int, DatosArticulo],
    p95_vel_por_subrubro: dict[int, float],
) -> list[ResultadoScore]:
    """Para cada arco, arma InputScore, calcula score y filtra por aceptable."""
    resultados: list[ResultadoScore] = []

    for articulo, origen, destino in arcos:
        eo = estados_idx.get((articulo, origen))
        ed = estados_idx.get((articulo, destino))
        dat = datos_art.get(articulo)
        if eo is None or ed is None or dat is None:
            continue

        p95 = p95_vel_por_subrubro.get(dat.subrubro, 0.0)
        if p95 <= 0:
            # fallback defensivo: usamos la velocidad del destino
            p95 = max(ed.vel_diaria, 0.01)

        # Riesgo drag: si tenemos stock por talle del origen y un talle
        # objeto, calcular. Si no, 0 (no aplica).
        riesgo = 0.0
        stock_por_talle = dat.stock_origen_por_talle.get(origen) or {}
        if stock_por_talle and dat.curva_ideal_subrubro and dat.talle_objeto:
            # Cantidad sugerida a transferir para evaluar el drag:
            # usamos min(exceso, demanda) como proxy conservador.
            sugerido = min(_exceso_origen(eo), _demanda_destino(ed))
            sugerido = max(1, sugerido)
            try:
                riesgo = riesgo_drag_effect(
                    stock_origen_por_talle=stock_por_talle,
                    curva_ideal=dat.curva_ideal_subrubro,
                    talle_transferido=int(dat.talle_objeto),
                    cantidad_transferida=sugerido,
                )
            except Exception as exc:  # noqa: BLE001
                log.debug("riesgo_drag_effect falló art=%s: %s", articulo, exc)
                riesgo = 0.0

        aff = dat.afinidad_local.get(destino, 0.5)

        dias_stock_orig = int(eo.dias_cobertura) if eo.dias_cobertura != float('inf') else 365

        inp = InputScore(
            articulo=articulo,
            origen=origen,
            destino=destino,
            stock_origen=int(eo.stock_actual),
            stock_destino=int(ed.stock_actual),
            vel_origen_dia=float(eo.vel_diaria),
            vel_destino_dia=float(ed.vel_diaria),
            p95_vel_categoria=float(p95),
            abcxyz_clase=dat.abcxyz_clase,
            margen_pct=float(dat.margen_pct),
            afinidad_marca_local=float(aff),
            dias_stock_origen=dias_stock_orig,
            factor_estacional=float(dat.factor_estacional),
            riesgo_drag=float(riesgo),
        )
        res = calcular_score(inp)

        if res.score >= SCORE_MIN_ACEPTACION:
            resultados.append(res)

    return resultados


# ---------------------------------------------------------------------------
# Paso 3: resolver MILP con OR-Tools
# ---------------------------------------------------------------------------


def resolver_milp_ortools(
    scores: list[ResultadoScore],
    datos_art: dict[int, DatosArticulo],
    estados_idx: dict[tuple[int, int], EstadoStock],
    presupuesto_destino: dict[int, float],
    time_limit_s: int = 60,
) -> tuple[dict[tuple, int], dict[int, float]]:
    """Resuelve el MILP con OR-Tools CBC.

    Retorna (asignacion, presupuesto_restante). Levanta ImportError si
    ortools no está instalado para que el caller pueda hacer fallback.
    """
    from ortools.linear_solver import pywraplp  # noqa: F401  (may raise ImportError)

    solver = pywraplp.Solver.CreateSolver('CBC')
    if solver is None:
        raise RuntimeError("No se pudo instanciar el solver CBC de OR-Tools")

    solver.set_time_limit(int(time_limit_s * 1000))

    # Pre-calcular excesos y demandas
    exceso: dict[tuple[int, int], int] = {}
    demanda: dict[tuple[int, int], int] = {}
    precio: dict[int, float] = {}

    for r in scores:
        key_o = (r.articulo, r.origen)
        key_d = (r.articulo, r.destino)
        if key_o not in exceso:
            eo = estados_idx.get(key_o)
            exceso[key_o] = _exceso_origen(eo) if eo else 0
        if key_d not in demanda:
            ed = estados_idx.get(key_d)
            demanda[key_d] = _demanda_destino(ed) if ed else 0
        if r.articulo not in precio:
            dat = datos_art.get(r.articulo)
            precio[r.articulo] = float(dat.precio_costo) if dat else 0.0

    # Variables x[i,o,d] con ub = min(exceso, demanda)
    x: dict[tuple[int, int, int], object] = {}
    for r in scores:
        key = (r.articulo, r.origen, r.destino)
        if key in x:
            continue
        ub = min(
            exceso.get((r.articulo, r.origen), 0),
            demanda.get((r.articulo, r.destino), 0),
        )
        if ub <= 0:
            continue
        x[key] = solver.IntVar(0, ub, f"x_{r.articulo}_{r.origen}_{r.destino}")

    if not x:
        log.info("MILP: no hay variables viables (ub=0 en todos los arcos)")
        return {}, dict(presupuesto_destino)

    # Restricciones de oferta por (articulo, origen)
    ofertas: dict[tuple[int, int], list] = {}
    for (i, o, d), var in x.items():
        ofertas.setdefault((i, o), []).append(var)
    for (i, o), vars_ in ofertas.items():
        solver.Add(sum(vars_) <= exceso.get((i, o), 0))

    # Restricciones de demanda por (articulo, destino)
    demandas: dict[tuple[int, int], list] = {}
    for (i, o, d), var in x.items():
        demandas.setdefault((i, d), []).append(var)
    for (i, d), vars_ in demandas.items():
        solver.Add(sum(vars_) <= demanda.get((i, d), 0))

    # Restricciones de presupuesto por destino
    presup_vars: dict[int, list] = {}
    for (i, o, d), var in x.items():
        presup_vars.setdefault(d, []).append((precio.get(i, 0.0), var))
    for d, pares in presup_vars.items():
        budget = float(presupuesto_destino.get(d, 0.0))
        if budget <= 0:
            solver.Add(sum(p * v for p, v in pares) <= 0)
        else:
            solver.Add(sum(p * v for p, v in pares) <= budget)

    # Objetivo: max Σ score * x
    score_lookup = {(r.articulo, r.origen, r.destino): r.score for r in scores}
    objective = solver.Objective()
    for key, var in x.items():
        objective.SetCoefficient(var, float(score_lookup.get(key, 0.0)))
    objective.SetMaximization()

    status = solver.Solve()
    if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        log.warning("MILP CBC no convergió (status=%s)", status)
        raise RuntimeError(f"CBC no convergió: status={status}")

    # Extraer resultado
    asignacion: dict[tuple, int] = {}
    gasto_por_dest: dict[int, float] = {}
    for (i, o, d), var in x.items():
        cant = int(round(var.solution_value()))
        if cant > 0:
            asignacion[(i, o, d)] = cant
            gasto_por_dest[d] = gasto_por_dest.get(d, 0.0) + cant * precio.get(i, 0.0)

    restante: dict[int, float] = {}
    for d, budget in presupuesto_destino.items():
        restante[d] = float(budget) - gasto_por_dest.get(d, 0.0)

    return asignacion, restante


# ---------------------------------------------------------------------------
# Paso 3 alt: fallback greedy
# ---------------------------------------------------------------------------


def resolver_greedy(
    scores: list[ResultadoScore],
    datos_art: dict[int, DatosArticulo],
    estados_idx: dict[tuple[int, int], EstadoStock],
    presupuesto_destino: dict[int, float],
) -> tuple[dict[tuple, int], dict[int, float]]:
    """Ordena arcos por score desc y asigna iterativamente respetando:
    oferta, demanda, presupuesto destino. Decrementa los tres al asignar.
    """
    # Estado mutable
    exceso: dict[tuple[int, int], int] = {}
    demanda: dict[tuple[int, int], int] = {}
    for r in scores:
        ko = (r.articulo, r.origen)
        kd = (r.articulo, r.destino)
        if ko not in exceso:
            eo = estados_idx.get(ko)
            exceso[ko] = _exceso_origen(eo) if eo else 0
        if kd not in demanda:
            ed = estados_idx.get(kd)
            demanda[kd] = _demanda_destino(ed) if ed else 0

    presupuesto: dict[int, float] = dict(presupuesto_destino)

    # Orden por score descendente
    scores_ord = sorted(scores, key=lambda r: r.score, reverse=True)

    asignacion: dict[tuple, int] = {}

    for r in scores_ord:
        dat = datos_art.get(r.articulo)
        if dat is None:
            continue
        precio = float(dat.precio_costo)

        disp_orig = exceso.get((r.articulo, r.origen), 0)
        falt_dest = demanda.get((r.articulo, r.destino), 0)
        if disp_orig <= 0 or falt_dest <= 0:
            continue

        pres_d = presupuesto.get(r.destino, 0.0)
        if precio > 0:
            max_por_presup = int(pres_d // precio)
        else:
            max_por_presup = disp_orig

        cant = min(disp_orig, falt_dest, max_por_presup)
        if cant <= 0:
            continue

        asignacion[(r.articulo, r.origen, r.destino)] = (
            asignacion.get((r.articulo, r.origen, r.destino), 0) + cant
        )
        exceso[(r.articulo, r.origen)] = disp_orig - cant
        demanda[(r.articulo, r.destino)] = falt_dest - cant
        presupuesto[r.destino] = pres_d - cant * precio

    return asignacion, presupuesto


# ---------------------------------------------------------------------------
# Paso 4: consolidar propuestas
# ---------------------------------------------------------------------------


def _motivo_linea(estado_origen: Optional[EstadoStock]) -> str:
    if estado_origen is None:
        return 'SOBRESTOCK'
    if estado_origen.estado == 'DEAD_STOCK':
        return 'DEAD_STOCK_REUTIL'
    return 'SOBRESTOCK'


def _minimo_pares_ruta(origen: int, destino: int) -> int:
    ruta = tipo_ruta(origen, destino)
    if ruta == 'central_vt':
        return 0
    if ruta == 'satelite':
        return int(COSTOS_V1['minimo_pares_satelite'])
    if ruta == 'satelite_satelite':
        return int(COSTOS_V1['minimo_pares_intermitente'])
    return 0


def consolidar_propuestas(
    asignacion: dict[tuple, int],
    scores_idx: dict[tuple, ResultadoScore],
    datos_art: dict[int, DatosArticulo],
    estados_idx: dict[tuple[int, int], EstadoStock],
    modo: str,
) -> list[Propuesta]:
    """Agrupa asignaciones en propuestas por (origen, destino) y aplica piso mínimo."""
    modo_tipo = 'URGENTE' if (modo or '').upper() == 'URGENTE' else 'REBALANCEO'

    # Agrupar
    grupos: dict[tuple[int, int], list[LineaPropuesta]] = {}
    for (art, orig, dest), cant in asignacion.items():
        if cant <= 0:
            continue
        dat = datos_art.get(art)
        if dat is None:
            continue
        res = scores_idx.get((art, orig, dest))
        score = float(res.score) if res else 0.0

        eo = estados_idx.get((art, orig))
        motivo = _motivo_linea(eo)

        linea = LineaPropuesta(
            articulo=art,
            cantidad=int(cant),
            score=score,
            precio_costo=float(dat.precio_costo),
            motivo=motivo,
        )
        grupos.setdefault((orig, dest), []).append(linea)

    propuestas: list[Propuesta] = []
    for (orig, dest), lineas in grupos.items():
        total_pares = sum(l.cantidad for l in lineas)
        if total_pares <= 0:
            continue

        total_costo_cer = sum(l.cantidad * l.precio_costo for l in lineas)
        score_prom = (
            sum(l.score * l.cantidad for l in lineas) / total_pares
            if total_pares > 0 else 0.0
        )
        precio_prom = total_costo_cer / total_pares if total_pares > 0 else 0.0

        # Costo logístico
        try:
            ev = costo_transferencia(orig, dest, total_pares, precio_prom)
            costo_log = float(ev.costo_total)
        except Exception as exc:  # noqa: BLE001
            log.debug("costo_transferencia falló %s->%s: %s", orig, dest, exc)
            costo_log = 0.0

        # Beneficio esperado simple: Σ margen_par_estimado * cantidad
        beneficio = 0.0
        for l in lineas:
            dat = datos_art.get(l.articulo)
            if dat is None:
                continue
            margen_par = dat.precio_costo * (dat.margen_pct / 100.0)
            beneficio += margen_par * l.cantidad

        minimo = _minimo_pares_ruta(orig, dest)
        cumple_min = total_pares >= minimo
        motivo_desc: Optional[str] = None if cumple_min else 'bajo_minimo'

        propuestas.append(
            Propuesta(
                tipo=modo_tipo,
                origen=orig,
                destino=dest,
                lineas=sorted(lineas, key=lambda x: x.score, reverse=True),
                total_pares=total_pares,
                total_costo_cer=float(total_costo_cer),
                score_promedio=float(score_prom),
                beneficio_esperado=float(beneficio),
                costo_transferencia=float(costo_log),
                cumple_minimo=cumple_min,
                motivo_descarte=motivo_desc,
            )
        )

    # Ordenar: primero las que cumplen mínimo, luego por score_promedio desc
    propuestas.sort(key=lambda p: (not p.cumple_minimo, -p.score_promedio))
    return propuestas


# ---------------------------------------------------------------------------
# Orquestación
# ---------------------------------------------------------------------------


def decidir(
    estados: list[EstadoStock],
    datos_art: dict[int, DatosArticulo],
    presupuesto_destino: dict[int, float],
    p95_vel_por_subrubro: dict[int, float],
    modo: str = 'REBALANCEO',
    usar_greedy: bool = False,
    time_limit_s: int = 60,
) -> ResultadoDecisor:
    """Orquesta todo el flujo del decisor.

    1. construir_arcos_candidatos
    2. calcular_scores_arcos (descarta < SCORE_MIN_ACEPTACION)
    3. resolver_milp_ortools (o greedy si usar_greedy=True o fallback)
    4. consolidar_propuestas
    """
    t0 = time.time()

    # Indexar estados
    estados_idx: dict[tuple[int, int], EstadoStock] = {
        (e.articulo, e.deposito): e for e in estados
    }

    # 1) arcos
    arcos = construir_arcos_candidatos(estados, modo=modo)

    # Filtro por rubro (si el destino no admite el rubro lo descartamos)
    articulo_rubro = {a: d.rubro for a, d in datos_art.items()}
    arcos_tuplas = filtrar_arcs_por_rubro(arcos, articulo_rubro)
    arcos = [tuple(a[:3]) for a in arcos_tuplas]  # type: ignore[misc]

    total_arcos = len(arcos)
    log.info("decidir: modo=%s arcos_candidatos=%d", modo, total_arcos)

    # 2) scores
    scores = calcular_scores_arcos(
        arcos=arcos,
        estados_idx=estados_idx,
        datos_art=datos_art,
        p95_vel_por_subrubro=p95_vel_por_subrubro,
    )
    arcs_score_valido = len(scores)
    log.info("decidir: arcs con score valido=%d", arcs_score_valido)

    # 3) solver
    solver_usado = 'GREEDY_FALLBACK'
    asignacion: dict[tuple, int] = {}
    presup_restante: dict[int, float] = dict(presupuesto_destino)

    if scores:
        if not usar_greedy:
            try:
                asignacion, presup_restante = resolver_milp_ortools(
                    scores=scores,
                    datos_art=datos_art,
                    estados_idx=estados_idx,
                    presupuesto_destino=presupuesto_destino,
                    time_limit_s=time_limit_s,
                )
                solver_usado = 'ORTOOLS'
            except ImportError:
                log.warning("OR-Tools no instalado, cayendo a greedy")
                asignacion, presup_restante = resolver_greedy(
                    scores=scores,
                    datos_art=datos_art,
                    estados_idx=estados_idx,
                    presupuesto_destino=presupuesto_destino,
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("MILP falló (%s), cayendo a greedy", exc)
                asignacion, presup_restante = resolver_greedy(
                    scores=scores,
                    datos_art=datos_art,
                    estados_idx=estados_idx,
                    presupuesto_destino=presupuesto_destino,
                )
        else:
            asignacion, presup_restante = resolver_greedy(
                scores=scores,
                datos_art=datos_art,
                estados_idx=estados_idx,
                presupuesto_destino=presupuesto_destino,
            )

    # 4) consolidar
    scores_idx: dict[tuple, ResultadoScore] = {
        (r.articulo, r.origen, r.destino): r for r in scores
    }
    propuestas = consolidar_propuestas(
        asignacion=asignacion,
        scores_idx=scores_idx,
        datos_art=datos_art,
        estados_idx=estados_idx,
        modo=modo,
    )

    tiempo_ms = int((time.time() - t0) * 1000)
    return ResultadoDecisor(
        propuestas=propuestas,
        arcs_evaluados=total_arcos,
        arcs_con_score_valido=arcs_score_valido,
        solver_usado=solver_usado,
        tiempo_ms=tiempo_ms,
        presupuesto_restante=presup_restante,
    )


# ---------------------------------------------------------------------------
# Demo sintético
# ---------------------------------------------------------------------------


def _caso_sintetico() -> tuple[
    list[EstadoStock],
    dict[int, DatosArticulo],
    dict[int, float],
    dict[int, float],
]:
    """Construye un caso sintético con 3 artículos y 4 locales en F1."""
    from autorepo.umbrales import clasificar_stock

    locales = [0, 2, 8, 11]  # Central VT, Norte, Junín, Alternativo VT

    # Art 100: Junín quebrado, Central con sobrestock (200 / 0.3 = 666 dias cob)
    # Art 200: Norte alerta, Junín con sobrestock fuerte
    # Art 300: dead stock en Alternativo VT, quiebre en Junín
    layout = {
        100: {
            0:  (200, 0.3, 'AX', 15, True, 2, 20),  # 666d cob -> SOBRESTOCK
            2:  (25, 0.5, 'AX', 15, True, 5, 20),
            8:  (2,  1.5, 'AX', 15, True, 1, 20),   # quiebre critico
            11: (10, 0.3, 'AX', 15, True, 8, 20),
        },
        200: {
            0:  (60, 0.8, 'BY', 20, True, 3, 40),
            2:  (5,  0.8, 'BY', 20, True, 2, 40),   # alerta
            8:  (150, 0.5, 'BY', 20, True, 4, 40),  # 300d -> SOBRESTOCK
            11: (15, 0.4, 'BY', 20, True, 6, 40),
        },
        300: {
            0:  (12, 0.2, 'CZ', 30, False, 40, 200),
            2:  (8,  0.2, 'CZ', 30, False, 35, 200),
            8:  (1,  0.4, 'CZ', 30, False, 2, 200),   # quiebre
            11: (25, 0.0, 'CZ', 30, False, 150, 300),  # dead stock
        },
    }

    estados: list[EstadoStock] = []
    for art, byd in layout.items():
        for dep, (stock, vel, clase, subr, temp, dsv, dsc) in byd.items():
            est = clasificar_stock(
                articulo=art,
                deposito=dep,
                stock_actual=stock,
                vel_diaria=vel,
                abcxyz_clase=clase,
                subrubro=subr,
                temporada_activa=temp,
                dias_sin_venta=dsv,
                dias_sin_compra=dsc,
            )
            estados.append(est)

    datos: dict[int, DatosArticulo] = {
        100: DatosArticulo(
            articulo=100, subrubro=15, rubro=1, marca=594,
            precio_costo=12000.0, margen_pct=50.0,
            abcxyz_clase='AX', factor_estacional=1.0,
            afinidad_local={0: 0.8, 2: 0.7, 8: 0.9, 11: 0.6},
            curva_ideal_subrubro={},
        ),
        200: DatosArticulo(
            articulo=200, subrubro=20, rubro=1, marca=104,
            precio_costo=9000.0, margen_pct=45.0,
            abcxyz_clase='BY', factor_estacional=1.0,
            afinidad_local={0: 0.6, 2: 0.8, 8: 0.6, 11: 0.6},
            curva_ideal_subrubro={},
        ),
        300: DatosArticulo(
            articulo=300, subrubro=30, rubro=2, marca=675,
            precio_costo=6000.0, margen_pct=40.0,
            abcxyz_clase='CZ', factor_estacional=1.0,
            afinidad_local={0: 0.5, 2: 0.5, 8: 0.6, 11: 0.4},
            curva_ideal_subrubro={},
        ),
    }

    presupuesto = {
        0: 500_000.0,
        2: 1_000_000.0,
        8: 2_000_000.0,
        11: 500_000.0,
    }

    # p95 velocidades por subrubro (para normalizar V_dest)
    p95_sub = {15: 2.0, 20: 1.5, 30: 0.6}

    _ = locales
    return estados, datos, presupuesto, p95_sub


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    estados, datos, presupuesto, p95 = _caso_sintetico()

    print("=" * 72)
    print("CASO SINTÉTICO — 3 artículos × 4 locales")
    print("=" * 72)
    for e in estados:
        print(
            f"  art={e.articulo} dep={e.deposito:2d} stock={e.stock_actual:3d} "
            f"vel={e.vel_diaria:.2f} estado={e.estado}"
        )

    print()
    print("--- Corriendo decidir(usar_greedy=True) ---")
    res_g = decidir(
        estados=estados,
        datos_art=datos,
        presupuesto_destino=presupuesto,
        p95_vel_por_subrubro=p95,
        modo='REBALANCEO',
        usar_greedy=True,
    )
    print(
        f"arcs_evaluados={res_g.arcs_evaluados}  "
        f"con_score={res_g.arcs_con_score_valido}  "
        f"solver={res_g.solver_usado}  tiempo={res_g.tiempo_ms}ms"
    )
    for p in res_g.propuestas:
        print(
            f"  [{p.tipo}] {p.origen} -> {p.destino}  pares={p.total_pares}  "
            f"score_prom={p.score_promedio:.1f}  "
            f"costo_cer=${p.total_costo_cer:,.0f}  "
            f"cumple_min={p.cumple_minimo}  motivo={p.motivo_descarte}"
        )
        for l in p.lineas:
            print(
                f"      art={l.articulo} cant={l.cantidad} "
                f"score={l.score:.1f} motivo={l.motivo}"
            )
    print()
    print("Presupuesto restante:", {k: f"${v:,.0f}" for k, v in res_g.presupuesto_restante.items()})
    print(f"TOTAL propuestas greedy: {len(res_g.propuestas)}")

    # También probar MILP si OR-Tools está disponible
    print()
    print("--- Corriendo decidir(MILP si está disponible) ---")
    res_m = decidir(
        estados=estados,
        datos_art=datos,
        presupuesto_destino=presupuesto,
        p95_vel_por_subrubro=p95,
        modo='REBALANCEO',
        usar_greedy=False,
    )
    print(
        f"arcs_evaluados={res_m.arcs_evaluados}  "
        f"con_score={res_m.arcs_con_score_valido}  "
        f"solver={res_m.solver_usado}  tiempo={res_m.tiempo_ms}ms"
    )
    for p in res_m.propuestas:
        print(
            f"  [{p.tipo}] {p.origen} -> {p.destino}  pares={p.total_pares}  "
            f"score_prom={p.score_promedio:.1f}  "
            f"costo_cer=${p.total_costo_cer:,.0f}  "
            f"cumple_min={p.cumple_minimo}  motivo={p.motivo_descarte}"
        )
    print(f"TOTAL propuestas solver principal: {len(res_m.propuestas)}")
