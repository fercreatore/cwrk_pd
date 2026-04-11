"""
autorepo/curva_talles.py
========================
Cálculo y comparación de curvas de talles por (local × subrubro × temporada)
para el motor de autocompensación H4 / CALZALINDO.

Detecta si un local tiene una curva sesgada (ej: Junín vende más 42-43,
Melincué más 39-40) y penaliza transferencias que rompen la curva del
origen (drag effect).

Herramientas:
- Curva real por local × subrubro (vía SQL, con fallback vacío si falla).
- Curva global del subrubro (para shrinkage).
- Shrinkage James-Stein hacia el prior global (λ = n / (n + k)).
- Distancia Wasserstein 1D sobre talles ordenados.
- Completeness de un stock respecto a una curva ideal.
- Riesgo de drag effect al transferir un talle puntual.

Fecha: 11-abr-2026
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import pyodbc

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CurvaLocal:
    deposito: int
    subrubro: int
    temporada: str                         # 'OI' | 'PV' | 'TODO'
    distribucion: dict[int, float]         # {talle: pct 0-1}, suma 1.0
    n_pares_base: int                      # cantidad de pares usados para calcular
    confianza: float                       # 0-1 (basada en n_pares_base via shrinkage)


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------


def _normalizar(distribucion: dict[int, float]) -> dict[int, float]:
    """Normaliza un dict {talle: valor} a que sume 1.0. Devuelve {} si total<=0."""
    total = sum(distribucion.values())
    if total <= 0:
        return {}
    return {int(t): float(v) / total for t, v in distribucion.items()}


def _filtro_temporada_sql(temporada: str) -> str:
    """
    Devuelve un fragmento WHERE para filtrar por temporada.
    OI = abril-septiembre (meses 4-9)
    PV = octubre-marzo (meses 10-12, 1-3)
    TODO = sin filtro.
    """
    temporada = (temporada or "TODO").upper()
    if temporada == "OI":
        return " AND MONTH(v.fecha) BETWEEN 4 AND 9 "
    if temporada == "PV":
        return " AND (MONTH(v.fecha) >= 10 OR MONTH(v.fecha) <= 3) "
    return ""


def _conectar(conn_string: Optional[str]) -> Optional[pyodbc.Connection]:
    """Intenta abrir una conexión. Si falla, loggea y devuelve None."""
    if not conn_string:
        logger.warning("curva_talles: conn_string vacío, no se puede consultar SQL")
        return None
    try:
        return pyodbc.connect(conn_string, timeout=10)
    except Exception as exc:  # noqa: BLE001
        logger.warning("curva_talles: error conectando a SQL: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Queries de curvas
# ---------------------------------------------------------------------------


def curva_local_subrubro(
    deposito: int,
    subrubro: int,
    temporada: str = "TODO",
    meses_hist: int = 12,
    conn_string: Optional[str] = None,
) -> CurvaLocal:
    """
    Calcula la curva real de talles vendidos en (local × subrubro × temporada)
    con shrinkage jerárquico hacia la curva global del subrubro.

    SQL base (adaptar según esquema real de ventas1):

        SELECT a.talle, SUM(v.cantidad) AS pares
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.fecha >= DATEADD(month, -{meses_hist}, GETDATE())
          AND v.deposito = {deposito}
          AND a.subrubro = {subrubro}
          AND v.codigo NOT IN (7, 36)
          AND v.operacion = '+'
        GROUP BY a.talle

    NOTA: revisar si existe columna 'talle' en ventas1 (probablemente no) —
    típicamente se llega via JOIN con articulo.talle. Si el esquema local
    usa otra tabla (ej: msgestion01art.dbo.articulo_talle), adaptar el JOIN.
    """
    empty = CurvaLocal(
        deposito=deposito,
        subrubro=subrubro,
        temporada=temporada,
        distribucion={},
        n_pares_base=0,
        confianza=0.0,
    )

    conn = _conectar(conn_string)
    if conn is None:
        return empty

    sql = f"""
        SELECT CAST(a.talle AS INT) AS talle, SUM(v.cantidad) AS pares
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.fecha >= DATEADD(month, -{int(meses_hist)}, GETDATE())
          AND v.deposito = {int(deposito)}
          AND a.subrubro = {int(subrubro)}
          AND v.codigo NOT IN (7, 36)
          AND v.operacion = '+'
          AND ISNUMERIC(a.talle) = 1
          {_filtro_temporada_sql(temporada)}
        GROUP BY CAST(a.talle AS INT)
        ORDER BY talle
    """

    try:
        df = pd.read_sql(sql, conn)
    except Exception as exc:  # noqa: BLE001
        logger.warning("curva_talles: error en query local: %s", exc)
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass
        return empty
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass

    if df.empty:
        return empty

    bruto = {int(row["talle"]): float(row["pares"]) for _, row in df.iterrows()}
    n_total = int(sum(bruto.values()))
    distribucion_local = _normalizar(bruto)

    # Shrinkage hacia curva global del subrubro (prior) para estabilidad.
    prior = curva_global_subrubro(
        subrubro=subrubro,
        temporada=temporada,
        meses_hist=meses_hist,
        conn_string=conn_string,
    )
    if prior:
        mezcla = shrinkage_james_stein(
            curva_local=distribucion_local,
            curva_prior=prior,
            n_local=n_total,
            k=100.0,
        )
    else:
        mezcla = distribucion_local

    confianza = min(1.0, n_total / 50.0) if n_total < 50 else 1.0

    return CurvaLocal(
        deposito=deposito,
        subrubro=subrubro,
        temporada=temporada,
        distribucion=mezcla,
        n_pares_base=n_total,
        confianza=confianza,
    )


def curva_global_subrubro(
    subrubro: int,
    temporada: str = "TODO",
    meses_hist: int = 12,
    conn_string: Optional[str] = None,
) -> dict[int, float]:
    """Curva agregada de toda la cadena (para shrinkage). Dict vacío si falla."""
    conn = _conectar(conn_string)
    if conn is None:
        return {}

    sql = f"""
        SELECT CAST(a.talle AS INT) AS talle, SUM(v.cantidad) AS pares
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.fecha >= DATEADD(month, -{int(meses_hist)}, GETDATE())
          AND a.subrubro = {int(subrubro)}
          AND v.codigo NOT IN (7, 36)
          AND v.operacion = '+'
          AND ISNUMERIC(a.talle) = 1
          {_filtro_temporada_sql(temporada)}
        GROUP BY CAST(a.talle AS INT)
        ORDER BY talle
    """

    try:
        df = pd.read_sql(sql, conn)
    except Exception as exc:  # noqa: BLE001
        logger.warning("curva_talles: error en query global: %s", exc)
        return {}
    finally:
        try:
            conn.close()
        except Exception:  # noqa: BLE001
            pass

    if df.empty:
        return {}

    bruto = {int(row["talle"]): float(row["pares"]) for _, row in df.iterrows()}
    return _normalizar(bruto)


# ---------------------------------------------------------------------------
# Shrinkage / distancias / completitud
# ---------------------------------------------------------------------------


def shrinkage_james_stein(
    curva_local: dict[int, float],
    curva_prior: dict[int, float],
    n_local: int,
    k: float = 100.0,
) -> dict[int, float]:
    """
    λ = n / (n + k). Si n << k, domina el prior.
    Retorna mezcla {talle: pct} con ambas llaves, suma=1.0.
    """
    if not curva_local and not curva_prior:
        return {}
    if not curva_local:
        return _normalizar(dict(curva_prior))
    if not curva_prior:
        return _normalizar(dict(curva_local))

    n = max(int(n_local), 0)
    lam = n / (n + float(k)) if (n + k) > 0 else 0.0

    todos_talles = set(curva_local.keys()) | set(curva_prior.keys())
    mezcla: dict[int, float] = {}
    for t in todos_talles:
        pl = curva_local.get(t, 0.0)
        pp = curva_prior.get(t, 0.0)
        mezcla[int(t)] = lam * pl + (1.0 - lam) * pp

    return _normalizar(mezcla)


def wasserstein_1d(curva_a: dict[int, float], curva_b: dict[int, float]) -> float:
    """
    Earth Mover's Distance 1D sobre talles ordenados.
    W = sum(|F_a(t) - F_b(t)|) sobre unión de talles.
    Retorna distancia en 'talles promedio'.
    """
    if not curva_a or not curva_b:
        return 0.0

    a = _normalizar(dict(curva_a))
    b = _normalizar(dict(curva_b))
    if not a or not b:
        return 0.0

    talles = sorted(set(a.keys()) | set(b.keys()))
    fa = 0.0
    fb = 0.0
    total = 0.0
    for t in talles:
        fa += a.get(t, 0.0)
        fb += b.get(t, 0.0)
        total += abs(fa - fb)
    return float(total)


def completeness(
    stock_por_talle: dict[int, int],
    curva_ideal: dict[int, float],
    umbral_pct: float = 0.05,
) -> float:
    """
    Porcentaje de la curva ideal cubierta (talles con stock>0 ponderados por su
    % ideal). Un talle cuenta como "cubierto" si stock > 0 Y su % en curva
    ideal > umbral_pct. Retorna 0-1.
    """
    if not curva_ideal:
        return 0.0

    ideal = _normalizar(dict(curva_ideal))
    if not ideal:
        return 0.0

    peso_relevante = 0.0
    peso_cubierto = 0.0
    for t, pct in ideal.items():
        if pct <= umbral_pct:
            continue
        peso_relevante += pct
        if int(stock_por_talle.get(int(t), 0)) > 0:
            peso_cubierto += pct

    if peso_relevante <= 0:
        return 0.0
    return float(peso_cubierto / peso_relevante)


def riesgo_drag_effect(
    stock_origen_por_talle: dict[int, int],
    curva_ideal: dict[int, float],
    talle_transferido: int,
    cantidad_transferida: int,
) -> float:
    """
    Calcula el riesgo de romper la curva del origen al transferir.

    - Si post-transferencia, completeness pasa de >= 0.8 a < 0.6 → 1.0
    - Si stock_origen_total >= 12 y completeness cae >20 pts → 0.5
    - Sino → 0.0
    """
    if not stock_origen_por_talle or not curva_ideal or cantidad_transferida <= 0:
        return 0.0

    stock_pre = {int(t): int(q) for t, q in stock_origen_por_talle.items()}
    total_pre = sum(stock_pre.values())

    comp_pre = completeness(stock_pre, curva_ideal)

    stock_post = dict(stock_pre)
    actual = stock_post.get(int(talle_transferido), 0)
    nuevo = max(0, actual - int(cantidad_transferida))
    stock_post[int(talle_transferido)] = nuevo

    comp_post = completeness(stock_post, curva_ideal)

    # Regla 1: ruptura severa (de saludable >=0.8 a crítico <0.6).
    if comp_pre >= 0.8 and comp_post < 0.6:
        return 1.0

    # Regla 2: stock con volumen mínimo y caída >20 pts.
    if total_pre >= 12 and (comp_pre - comp_post) > 0.20:
        return 0.5

    return 0.0


# ---------------------------------------------------------------------------
# Comparación alto nivel
# ---------------------------------------------------------------------------


def comparar_curvas_locales(
    deposito_a: int,
    deposito_b: int,
    subrubro: int,
    conn_string: Optional[str] = None,
) -> tuple[float, dict, dict]:
    """
    Retorna (wasserstein_distance, curva_a, curva_b).
    Las curvas vienen shrinkeadas hacia el global del subrubro.
    """
    ca = curva_local_subrubro(
        deposito=deposito_a,
        subrubro=subrubro,
        temporada="TODO",
        conn_string=conn_string,
    )
    cb = curva_local_subrubro(
        deposito=deposito_b,
        subrubro=subrubro,
        temporada="TODO",
        conn_string=conn_string,
    )
    w = wasserstein_1d(ca.distribucion, cb.distribucion)
    return w, ca.distribucion, cb.distribucion


# ---------------------------------------------------------------------------
# Main (ejemplos hardcoded, NO requieren SQL)
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    # Wasserstein Junín vs Melincué
    curva_junin = {39: 0.05, 40: 0.10, 41: 0.18, 42: 0.28, 43: 0.22, 44: 0.12, 45: 0.05}
    curva_melincue = {37: 0.08, 38: 0.15, 39: 0.25, 40: 0.28, 41: 0.15, 42: 0.06, 43: 0.03}
    w = wasserstein_1d(curva_junin, curva_melincue)
    print(f"Wasserstein Junín vs Melincué: {w:.2f} talles")

    # Shrinkage con n pequeño
    local_pocos = {42: 0.5, 43: 0.5}
    global_ref = {40: 0.1, 41: 0.2, 42: 0.3, 43: 0.2, 44: 0.15, 45: 0.05}
    mezcla = shrinkage_james_stein(local_pocos, global_ref, n_local=10, k=100)
    mezcla_fmt = {t: round(v, 4) for t, v in sorted(mezcla.items())}
    print(f"Shrinkage (n=10, k=100): {mezcla_fmt}")

    # Drag effect
    stock_origen = {40: 2, 41: 3, 42: 8, 43: 4, 44: 2}
    ideal = {40: 0.1, 41: 0.2, 42: 0.3, 43: 0.25, 44: 0.15}
    print(
        f"Riesgo drag al transferir 5x42: "
        f"{riesgo_drag_effect(stock_origen, ideal, 42, 5)}"
    )
