"""
dep4_monitor.py — Monitor de mercaderia frenada en deposito 4 (Marroquineria/Claudia).

Proposito:
    Dep 4 esta EXCLUIDO del solver F1 del motor autorepo, pero necesitamos
    reportes separados para revision humana (Fernando/Mati) sobre capital
    inmovilizado ahi (~$27-30M CER al 11-abr-2026).

    Top item detectado: 1 par de $1.2M con ult compra junio 2005.
    Top subrubros frenados: 1 ($3.4M), 13 ($2.5M), 52 ($2.4M),
    60 ($1.7M), 23 ($1.6M).

Criterio dead stock:
    stock > 0 AND ventas_90d = 0 AND ult_compra > 180 dias

Fecha: 11-abr-2026
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, asdict
from typing import Optional

try:
    import pyodbc  # type: ignore
except ImportError:  # pragma: no cover
    pyodbc = None  # type: ignore

try:
    import pandas as pd  # type: ignore
except ImportError:  # pragma: no cover
    pd = None  # type: ignore

try:
    from config import CONN_COMPRAS  # type: ignore
except Exception:  # pragma: no cover
    CONN_COMPRAS = None  # type: ignore


logger = logging.getLogger(__name__)
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(_h)
    logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class ArticuloFrenado:
    articulo: int
    stock_dep4: int
    ventas_90d_dep4: int
    ult_compra: Optional[str]      # 'YYYY-MM-DD' o None
    dias_sin_compra: int           # DATEDIFF con GETDATE
    costo_cer_unit: float
    capital_inmov: float           # stock * costo_cer
    subrubro: int
    marca: int
    categoria: str = "REVISION"    # 'TRANSFERIBLE' | 'REMATE' | 'REVISION'


# ---------------------------------------------------------------------------
# Clasificacion
# ---------------------------------------------------------------------------


def clasificar_frenado(
    art: ArticuloFrenado,
    subrubros_desaparecidos: Optional[set[int]] = None,
) -> str:
    """
    Categorizacion del articulo frenado:

    - 'REMATE'       : ult_compra > 730 dias (2 anios) O subrubro "desaparecido"
                       (no aparece en ventas cadena ultimos 12m; el set se
                       pasa como parametro opcional desde un DataFrame externo).
    - 'TRANSFERIBLE' : ult_compra < 365 dias AND capital_inmov > 200_000.
    - 'REVISION'     : zona intermedia (todo lo demas).
    """
    subrubros_desaparecidos = subrubros_desaparecidos or set()

    # REMATE tiene prioridad: articulo muerto o rubro muerto
    if art.dias_sin_compra > 730:
        return "REMATE"
    if art.subrubro in subrubros_desaparecidos:
        return "REMATE"

    # TRANSFERIBLE: reciente y con capital significativo
    if art.dias_sin_compra < 365 and art.capital_inmov > 200_000:
        return "TRANSFERIBLE"

    return "REVISION"


# ---------------------------------------------------------------------------
# Query SQL
# ---------------------------------------------------------------------------


_SQL_FRENADOS_DEP4 = """
WITH costos AS (
    SELECT CAST(codigo AS INT) AS articulo, MAX(costo_cer) AS costo_cer
    FROM omicronvt.dbo.compras_por_local
    WHERE ISNUMERIC(codigo) = 1
    GROUP BY codigo
),
ult AS (
    SELECT CAST(codigo AS INT) AS articulo, MAX(ult_compra) AS ult_compra
    FROM omicronvt.dbo.compras_por_local
    WHERE ISNUMERIC(codigo) = 1 AND depo = 4
    GROUP BY codigo
),
v90 AS (
    SELECT articulo, SUM(cantidad) AS ventas_90d
    FROM msgestionC.dbo.ventas1
    WHERE deposito = 4
      AND fecha >= DATEADD(day, -90, GETDATE())
      AND codigo NOT IN (7, 36)
      AND operacion = '+'
    GROUP BY articulo
)
SELECT TOP (?)
    s.articulo,
    s.stock_actual,
    ISNULL(v90.ventas_90d, 0) AS ventas_90d,
    u.ult_compra,
    DATEDIFF(day, u.ult_compra, GETDATE()) AS dias_sin_compra,
    ISNULL(c.costo_cer, 0) AS costo_cer,
    s.stock_actual * ISNULL(c.costo_cer, 0) AS capital_inmov,
    a.subrubro,
    a.marca
FROM msgestionC.dbo.stock s
LEFT JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
LEFT JOIN costos c ON c.articulo = s.articulo
LEFT JOIN ult    u ON u.articulo = s.articulo
LEFT JOIN v90      ON v90.articulo = s.articulo
WHERE s.deposito = 4
  AND s.serie = ' '
  AND s.stock_actual > 0
  AND ISNULL(v90.ventas_90d, 0) = 0
  AND (u.ult_compra IS NULL OR u.ult_compra < DATEADD(day, -180, GETDATE()))
ORDER BY capital_inmov DESC
"""


def _row_to_articulo(row) -> ArticuloFrenado:
    ult_compra_raw = row[3]
    if ult_compra_raw is None:
        ult_compra_str: Optional[str] = None
    else:
        try:
            ult_compra_str = ult_compra_raw.strftime("%Y-%m-%d")
        except AttributeError:
            ult_compra_str = str(ult_compra_raw)[:10]

    try:
        articulo = int(row[0])
    except (TypeError, ValueError):
        articulo = 0

    try:
        stock = int(row[1] or 0)
    except (TypeError, ValueError):
        stock = 0

    try:
        v90 = int(row[2] or 0)
    except (TypeError, ValueError):
        v90 = 0

    try:
        dias = int(row[4]) if row[4] is not None else 99999
    except (TypeError, ValueError):
        dias = 99999

    try:
        costo = float(row[5] or 0.0)
    except (TypeError, ValueError):
        costo = 0.0

    try:
        capital = float(row[6] or 0.0)
    except (TypeError, ValueError):
        capital = 0.0

    try:
        subrubro = int(row[7]) if row[7] is not None else 0
    except (TypeError, ValueError):
        subrubro = 0

    try:
        marca = int(row[8]) if row[8] is not None else 0
    except (TypeError, ValueError):
        marca = 0

    art = ArticuloFrenado(
        articulo=articulo,
        stock_dep4=stock,
        ventas_90d_dep4=v90,
        ult_compra=ult_compra_str,
        dias_sin_compra=dias,
        costo_cer_unit=costo,
        capital_inmov=capital,
        subrubro=subrubro,
        marca=marca,
        categoria="REVISION",
    )
    art.categoria = clasificar_frenado(art)
    return art


def fetch_frenados_dep4(
    conn_string: Optional[str] = None,
    top: int = 500,
) -> list[ArticuloFrenado]:
    """
    Trae los articulos frenados del deposito 4 desde la replica SQL Server 2012.

    Si no hay conexion disponible o falla, retorna lista vacia y loguea
    warning (fallback gracil).
    """
    if pyodbc is None:
        logger.warning("pyodbc no disponible; fetch_frenados_dep4 retorna [].")
        return []

    cs = conn_string or CONN_COMPRAS
    if not cs:
        logger.warning("No hay conn_string (CONN_COMPRAS=None); retorna [].")
        return []

    try:
        with pyodbc.connect(cs, timeout=10) as cn:
            cur = cn.cursor()
            cur.execute(_SQL_FRENADOS_DEP4, int(top))
            rows = cur.fetchall()
    except Exception as e:  # pragma: no cover
        logger.warning("fetch_frenados_dep4 fallo: %s", e)
        return []

    out: list[ArticuloFrenado] = []
    for r in rows:
        try:
            out.append(_row_to_articulo(r))
        except Exception as e:  # pragma: no cover
            logger.warning("row parse fallo: %s", e)
    return out


# ---------------------------------------------------------------------------
# Resumenes
# ---------------------------------------------------------------------------


def resumen_por_subrubro(frenados: list[ArticuloFrenado]):
    """
    Agrupa por subrubro: skus, unidades, capital_inmov_total.
    Retorna un DataFrame ordenado por capital descendente.
    Si pandas no esta disponible, retorna lista de dicts.
    """
    agg: dict[int, dict] = {}
    for a in frenados:
        d = agg.setdefault(
            a.subrubro,
            {"subrubro": a.subrubro, "skus": 0, "unidades": 0, "capital_inmov": 0.0},
        )
        d["skus"] += 1
        d["unidades"] += a.stock_dep4
        d["capital_inmov"] += a.capital_inmov

    filas = sorted(agg.values(), key=lambda x: x["capital_inmov"], reverse=True)

    if pd is None:  # pragma: no cover
        return filas
    return pd.DataFrame(filas)


def resumen_por_categoria(frenados: list[ArticuloFrenado]) -> dict:
    """
    Retorna {'TRANSFERIBLE': {skus, unidades, capital},
             'REMATE': {...},
             'REVISION': {...}}
    """
    base = {
        "TRANSFERIBLE": {"skus": 0, "unidades": 0, "capital": 0.0},
        "REMATE":       {"skus": 0, "unidades": 0, "capital": 0.0},
        "REVISION":     {"skus": 0, "unidades": 0, "capital": 0.0},
    }
    for a in frenados:
        cat = a.categoria if a.categoria in base else "REVISION"
        base[cat]["skus"] += 1
        base[cat]["unidades"] += a.stock_dep4
        base[cat]["capital"] += a.capital_inmov
    return base


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def exportar_csv(frenados: list[ArticuloFrenado], path: str) -> None:
    """
    Exporta la lista a CSV para compartir con Fernando/Mati.
    Usa pandas si esta disponible, sino csv stdlib.
    """
    if not frenados:
        logger.warning("exportar_csv: lista vacia, nada que exportar.")
        return

    rows = [asdict(a) for a in frenados]

    if pd is not None:
        df = pd.DataFrame(rows)
        df.to_csv(path, index=False, encoding="utf-8")
        return

    import csv  # pragma: no cover

    with open(path, "w", newline="", encoding="utf-8") as f:  # pragma: no cover
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Main de prueba
# ---------------------------------------------------------------------------


def _ejemplos_hardcodeados() -> list[ArticuloFrenado]:
    """3 ejemplos para probar clasificacion y resumen cuando no hay DB."""
    ejemplos = [
        ArticuloFrenado(
            articulo=111111,
            stock_dep4=1,
            ventas_90d_dep4=0,
            ult_compra="2005-06-15",
            dias_sin_compra=7600,
            costo_cer_unit=1_200_000.0,
            capital_inmov=1_200_000.0,
            subrubro=1,
            marca=436,
        ),
        ArticuloFrenado(
            articulo=222222,
            stock_dep4=8,
            ventas_90d_dep4=0,
            ult_compra="2025-09-01",
            dias_sin_compra=220,
            costo_cer_unit=35_000.0,
            capital_inmov=280_000.0,
            subrubro=13,
            marca=100,
        ),
        ArticuloFrenado(
            articulo=333333,
            stock_dep4=3,
            ventas_90d_dep4=0,
            ult_compra="2024-12-01",
            dias_sin_compra=495,
            costo_cer_unit=20_000.0,
            capital_inmov=60_000.0,
            subrubro=52,
            marca=200,
        ),
    ]
    for e in ejemplos:
        e.categoria = clasificar_frenado(e)
    return ejemplos


def _fmt_money(v: float) -> str:
    return f"${v:,.0f}"


def _print_top(frenados: list[ArticuloFrenado], n: int = 20) -> None:
    print(f"\n=== TOP {min(n, len(frenados))} frenados dep4 (por capital) ===")
    print(
        f"{'art':>8} {'stock':>6} {'v90':>4} {'dias':>5} "
        f"{'sub':>4} {'mca':>5} {'capital':>15} {'cat':<13} {'ult_compra':<12}"
    )
    for a in frenados[:n]:
        print(
            f"{a.articulo:>8} {a.stock_dep4:>6} {a.ventas_90d_dep4:>4} "
            f"{a.dias_sin_compra:>5} {a.subrubro:>4} {a.marca:>5} "
            f"{_fmt_money(a.capital_inmov):>15} {a.categoria:<13} "
            f"{a.ult_compra or '-':<12}"
        )


def _print_resumen_categoria(frenados: list[ArticuloFrenado]) -> None:
    resumen = resumen_por_categoria(frenados)
    print("\n=== Resumen por categoria ===")
    print(f"{'categoria':<13} {'skus':>6} {'unidades':>10} {'capital':>18}")
    total_cap = 0.0
    for cat, d in resumen.items():
        print(
            f"{cat:<13} {d['skus']:>6} {d['unidades']:>10} "
            f"{_fmt_money(d['capital']):>18}"
        )
        total_cap += d["capital"]
    print(f"{'TOTAL':<13} {'':>6} {'':>10} {_fmt_money(total_cap):>18}")


def main() -> int:
    print("dep4_monitor — monitoreo de mercaderia frenada en deposito 4")
    print(f"CONN_COMPRAS disponible: {bool(CONN_COMPRAS)}")

    frenados: list[ArticuloFrenado] = []
    if CONN_COMPRAS and pyodbc is not None:
        try:
            frenados = fetch_frenados_dep4(top=20)
        except Exception as e:
            logger.warning("fetch fallo: %s", e)
            frenados = []

    if not frenados:
        print("\n[fallback] Sin conexion o sin datos — uso 3 ejemplos hardcodeados.")
        frenados = _ejemplos_hardcodeados()

    _print_top(frenados, n=20)
    _print_resumen_categoria(frenados)

    if pd is not None:
        try:
            df_sub = resumen_por_subrubro(frenados)
            print("\n=== Resumen por subrubro ===")
            print(df_sub.to_string(index=False))
        except Exception as e:  # pragma: no cover
            logger.warning("resumen_por_subrubro fallo: %s", e)

    return 0


if __name__ == "__main__":
    sys.exit(main())
