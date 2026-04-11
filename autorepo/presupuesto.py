"""
autorepo/presupuesto.py

Deriva el presupuesto mensual de reposición por depósito para el motor
de autocompensación H4 / CALZALINDO.

Método híbrido: MMA-1 (mismo mes del año anterior por depo) × factor_yoy
(crecimiento cadena últimos 3 meses vs mismos 3 meses del año anterior) ×
share_local (participación histórica del depo). Trabaja siempre sobre
`costo_cer` (ya ajustado por CER) de `omicronvt.dbo.compras_por_local`.

Excluye meses de pandemia y outliers (MAD robust, k=3.0).

Fecha: 11-abr-2026
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import pandas as pd

# ── Config / conexión ────────────────────────────────────────────────────────
try:
    # config.py vive en la raíz del repo
    _REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)
    from config import CONN_COMPRAS  # noqa: E402
except Exception:  # pragma: no cover - fallback cuando no hay config disponible
    CONN_COMPRAS = os.environ.get("CONN_COMPRAS_AUTOREPO", "")

log = logging.getLogger(__name__)

# ── Constantes ───────────────────────────────────────────────────────────────
MESES_PANDEMIA_EXCLUIDOS: tuple[str, ...] = (
    "2020-03",
    "2020-04",
    "2020-05",
    "2021-06",
)

DEPOS_DEFAULT: tuple[int, ...] = (0, 2, 6, 7, 8, 11)


# ── Dataclass pública ────────────────────────────────────────────────────────
@dataclass
class PresupuestoLocal:
    depo: int
    mes_target: str  # 'YYYY-MM'
    mma1_costo_cer: float  # mismo mes año anterior (post limpieza)
    factor_yoy: float  # multiplicador cadena
    share_local: float  # 0-1
    presupuesto_sugerido: float
    presupuesto_ajustado: Optional[float] = None  # post-normalización top-down
    n_meses_hist: int = 0  # meses con data para ese depo (indicador confianza)

    def __str__(self) -> str:  # pragma: no cover - cosmético
        aj = (
            f"{self.presupuesto_ajustado:>14,.0f}"
            if self.presupuesto_ajustado is not None
            else " " * 14
        )
        return (
            f"depo={self.depo:>3} mes={self.mes_target} "
            f"MMA1={self.mma1_costo_cer:>14,.0f} "
            f"yoy={self.factor_yoy:>6.3f} "
            f"share={self.share_local:>6.3f} "
            f"sugerido={self.presupuesto_sugerido:>14,.0f} "
            f"ajustado={aj} "
            f"n={self.n_meses_hist}"
        )


# ── Helpers de fecha ─────────────────────────────────────────────────────────
def _parse_mes(mes_str: str) -> tuple[int, int]:
    anio, mes = mes_str.split("-")
    return int(anio), int(mes)


def _fmt_mes(anio: int, mes: int) -> str:
    return f"{anio:04d}-{mes:02d}"


def _restar_meses(mes_str: str, n: int) -> str:
    anio, mes = _parse_mes(mes_str)
    total = anio * 12 + (mes - 1) - n
    na, nm = divmod(total, 12)
    return _fmt_mes(na, nm + 1)


def _mismo_mes_anio_anterior(mes_str: str) -> str:
    anio, mes = _parse_mes(mes_str)
    return _fmt_mes(anio - 1, mes)


def _ultimos_3_meses_cerrados(mes_target: str) -> list[str]:
    """Devuelve los 3 meses completos anteriores a mes_target."""
    return [_restar_meses(mes_target, i) for i in (1, 2, 3)]


# ── Limpieza estadística ─────────────────────────────────────────────────────
def _excluir_outliers_mad(serie: pd.Series, k: float = 3.0) -> pd.Series:
    """Excluye outliers via MAD robust.

    Drop rows where |v - median| > k × MAD. Si MAD == 0 retorna la serie tal cual.
    """
    if serie.empty:
        return serie
    s = serie.dropna().astype(float)
    if s.empty:
        return s
    median = s.median()
    mad = (s - median).abs().median()
    if mad == 0 or pd.isna(mad):
        return s
    mask = (s - median).abs() <= k * mad
    return s[mask]


# ── Query principal ──────────────────────────────────────────────────────────
def _fetch_compras_por_local(
    mes_target: str,
    conn_string: str,
    deps: tuple[int, ...] = DEPOS_DEFAULT,
) -> pd.DataFrame:
    """Baja compras_por_local desde mes_target-24m hasta mes_target,
    excluye pandemia, agrupa por (depo, mes) con SUM(cant * costo_cer).

    Returns
    -------
    DataFrame con columnas: depo (int), mes (str 'YYYY-MM'), monto_cer (float)
    """
    import pyodbc

    mes_desde = _restar_meses(mes_target, 24)
    mes_hasta = mes_target

    placeholders_deps = ",".join(str(int(d)) for d in deps)
    placeholders_pand = ",".join(f"'{m}'" for m in MESES_PANDEMIA_EXCLUIDOS)

    # SQL Server 2012 RTM → ISNUMERIC en lugar de TRY_CAST.
    # ABS(cant * costo_cer) porque depósitos virtuales (ej. depo 11 "central")
    # almacenan cant con signo negativo al enviar mercadería a sucursales.
    # Para presupuesto de reposición nos interesa magnitud, no dirección.
    sql = f"""
        SELECT depo,
               mes,
               SUM(ABS(CAST(cant AS float) * CAST(costo_cer AS float))) AS monto_cer
        FROM omicronvt.dbo.compras_por_local
        WHERE ISNUMERIC(codigo) = 1
          AND mes >= ?
          AND mes <= ?
          AND mes NOT IN ({placeholders_pand})
          AND depo IN ({placeholders_deps})
          AND costo_cer IS NOT NULL
        GROUP BY depo, mes
        ORDER BY depo, mes
    """

    log.debug("Conectando a SQL Server para fetch compras_por_local [%s..%s]",
              mes_desde, mes_hasta)
    with pyodbc.connect(conn_string) as cn:
        cur = cn.cursor()
        cur.execute(sql, mes_desde, mes_hasta)
        rows = cur.fetchall()

    if rows:
        df = pd.DataFrame(
            [(int(r[0]), str(r[1]), float(r[2])) for r in rows],
            columns=["depo", "mes", "monto_cer"],
        )
    else:
        df = pd.DataFrame(columns=["depo", "mes", "monto_cer"])

    log.info("compras_por_local: %d filas (%d depos, rango %s..%s)",
             len(df), df["depo"].nunique() if not df.empty else 0,
             mes_desde, mes_hasta)
    return df


# ── Factor YoY cadena ────────────────────────────────────────────────────────
def _calcular_factor_yoy(df: pd.DataFrame, mes_target: str) -> float:
    """Factor multiplicador cadena:

        sum(monto_cer últimos 3 meses cerrados antes de mes_target)
      / sum(monto_cer mismos 3 meses del año anterior)

    Si denominador es 0 / NaN o no hay datos → 1.0 (sin ajuste).
    """
    if df is None or df.empty:
        return 1.0

    meses_recientes = _ultimos_3_meses_cerrados(mes_target)
    meses_yoy = [_mismo_mes_anio_anterior(m) for m in meses_recientes]

    num = df.loc[df["mes"].isin(meses_recientes), "monto_cer"].sum()
    den = df.loc[df["mes"].isin(meses_yoy), "monto_cer"].sum()

    if den is None or pd.isna(den) or den == 0:
        log.warning(
            "factor_yoy: denominador 0 o NaN para meses %s — usando 1.0",
            meses_yoy,
        )
        return 1.0

    factor = float(num) / float(den)
    # Sanity clamp razonable — evita explosiones por un mes atípico
    if factor <= 0 or pd.isna(factor):
        return 1.0
    log.info("factor_yoy=%.4f (num=%.0f, den=%.0f, meses=%s vs %s)",
             factor, num, den, meses_recientes, meses_yoy)
    return factor


# ── Cálculo MMA-1 por depósito (limpio de outliers) ──────────────────────────
def _calcular_mma1_por_depo(
    df: pd.DataFrame,
    mes_target: str,
    deps: tuple[int, ...],
) -> dict[int, tuple[float, int]]:
    """Para cada depo calcula el monto del mismo mes del año anterior.

    Antes de tomarlo, la serie mensual del depo se filtra por MAD robust;
    si el mes exacto (año-1) quedó afuera por outlier, se usa el promedio
    de la serie limpia como mejor proxy. Si la serie limpia está vacía,
    retorna 0.0.

    Returns dict[depo] -> (mma1_costo_cer, n_meses_hist)
    """
    mes_yoy = _mismo_mes_anio_anterior(mes_target)
    result: dict[int, tuple[float, int]] = {}

    for depo in deps:
        sub = df.loc[df["depo"] == depo].copy()
        n_hist = int(sub["mes"].nunique()) if not sub.empty else 0

        if sub.empty:
            result[depo] = (0.0, 0)
            continue

        # Filtrado MAD sobre la serie histórica del depo
        serie_idx = sub.set_index("mes")["monto_cer"].astype(float)
        serie_limpia = _excluir_outliers_mad(serie_idx, k=3.0)

        if serie_limpia.empty:
            result[depo] = (0.0, n_hist)
            continue

        if mes_yoy in serie_limpia.index:
            mma1 = float(serie_limpia.loc[mes_yoy])
        else:
            # mes exacto no está (o fue outlier) → proxy: promedio serie limpia
            mma1 = float(serie_limpia.mean())
            log.info(
                "depo=%d: mes_yoy=%s no disponible (o outlier) → usando "
                "promedio serie limpia = %.0f",
                depo, mes_yoy, mma1,
            )

        result[depo] = (mma1, n_hist)

    return result


# ── API pública ──────────────────────────────────────────────────────────────
def calcular_presupuestos(
    mes_target: str,
    deps: tuple[int, ...] = DEPOS_DEFAULT,
    conn_string: Optional[str] = None,
    total_cadena_override: Optional[float] = None,
) -> list[PresupuestoLocal]:
    """Calcula presupuesto de reposición por depósito para ``mes_target``.

    Parameters
    ----------
    mes_target : str
        Mes objetivo en formato 'YYYY-MM'.
    deps : tuple[int, ...]
        Depósitos a considerar. Default: (0, 2, 6, 7, 8, 11).
    conn_string : Optional[str]
        Connection string pyodbc. Si None → usa ``config.CONN_COMPRAS``.
    total_cadena_override : Optional[float]
        Si Fernando fija un total de cadena (p. ej. limitado por caja),
        se normaliza ``presupuesto_ajustado = share_local × total_cadena_override``.
        Si None, ``presupuesto_ajustado = presupuesto_sugerido``.

    Returns
    -------
    list[PresupuestoLocal]
    """
    if conn_string is None:
        conn_string = CONN_COMPRAS
    if not conn_string:
        raise RuntimeError(
            "calcular_presupuestos: no se pudo resolver connection string. "
            "Definí config.CONN_COMPRAS o la env CONN_COMPRAS_AUTOREPO."
        )

    df = _fetch_compras_por_local(mes_target, conn_string, deps=deps)

    factor_yoy = _calcular_factor_yoy(df, mes_target)
    mma1_por_depo = _calcular_mma1_por_depo(df, mes_target, deps)

    total_mma1 = sum(v[0] for v in mma1_por_depo.values())

    # Build PresupuestoLocal list (pass 1: sugerido + share)
    presupuestos: list[PresupuestoLocal] = []
    for depo in deps:
        mma1, n_hist = mma1_por_depo.get(depo, (0.0, 0))
        share = (mma1 / total_mma1) if total_mma1 > 0 else 0.0
        sugerido = mma1 * factor_yoy

        presupuestos.append(
            PresupuestoLocal(
                depo=depo,
                mes_target=mes_target,
                mma1_costo_cer=round(mma1, 2),
                factor_yoy=round(factor_yoy, 4),
                share_local=round(share, 4),
                presupuesto_sugerido=round(sugerido, 2),
                presupuesto_ajustado=None,
                n_meses_hist=n_hist,
            )
        )

    # Pass 2: ajustado (normalización top-down o identidad)
    if total_cadena_override is not None and total_cadena_override > 0:
        for p in presupuestos:
            p.presupuesto_ajustado = round(
                p.share_local * float(total_cadena_override), 2
            )
    else:
        for p in presupuestos:
            p.presupuesto_ajustado = p.presupuesto_sugerido

    log.info(
        "calcular_presupuestos %s: %d depos, total_mma1=%.0f, "
        "factor_yoy=%.4f, total_sugerido=%.0f",
        mes_target,
        len(presupuestos),
        total_mma1,
        factor_yoy,
        sum(p.presupuesto_sugerido for p in presupuestos),
    )
    return presupuestos


# ── Helper para imprimir como tabla ──────────────────────────────────────────
def _imprimir_tabla(presupuestos: list[PresupuestoLocal]) -> None:
    if not presupuestos:
        print("(sin presupuestos)")
        return

    cols = (
        "depo", "mes", "MMA1_cer", "yoy", "share", "sugerido", "ajustado", "n"
    )
    widths = (5, 9, 16, 8, 8, 16, 16, 5)
    header = " ".join(c.rjust(w) for c, w in zip(cols, widths))
    print(header)
    print("-" * len(header))

    total_sug = 0.0
    total_aj = 0.0
    for p in presupuestos:
        aj = p.presupuesto_ajustado if p.presupuesto_ajustado is not None else 0.0
        total_sug += p.presupuesto_sugerido
        total_aj += aj
        row = " ".join(
            v.rjust(w)
            for v, w in zip(
                (
                    str(p.depo),
                    p.mes_target,
                    f"{p.mma1_costo_cer:,.0f}",
                    f"{p.factor_yoy:.3f}",
                    f"{p.share_local:.3f}",
                    f"{p.presupuesto_sugerido:,.0f}",
                    f"{aj:,.0f}",
                    str(p.n_meses_hist),
                ),
                widths,
            )
        )
        print(row)

    print("-" * len(header))
    print(
        " ".join(
            v.rjust(w)
            for v, w in zip(
                (
                    "TOT",
                    "",
                    "",
                    "",
                    "",
                    f"{total_sug:,.0f}",
                    f"{total_aj:,.0f}",
                    "",
                ),
                widths,
            )
        )
    )


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        presupuestos = calcular_presupuestos("2026-05")
        _imprimir_tabla(presupuestos)
    except Exception as exc:  # pragma: no cover - solo uso CLI
        log.warning(
            "No se pudo calcular presupuestos (probablemente sin conexión al 111): %s",
            exc,
        )
        print(
            "[WARN] calcular_presupuestos('2026-05') falló — "
            "revisar conectividad al 192.168.2.111 / config.CONN_COMPRAS."
        )
