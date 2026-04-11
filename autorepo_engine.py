"""
autorepo_engine.py
==================

Motor CLI principal de autocompensación inter-depósito H4 / CALZALINDO.

Entry point para corridas por cron (schedule_autorepo_111.bat) en el
servidor 111. Orquesta:

    extract SQL → clasificar estados → presupuesto → decisor → persistir

Modos
-----
  --modo urgente      Solo QUIEBRE_CRITICO → SOBRESTOCK/DEAD_STOCK
  --modo rebalanceo   QUIEBRE+ALERTA → SOBRESTOCK/DEAD_STOCK (default)
  --modo auditoria    Revisa propuestas del mes anterior, calcula KPIs

Flags
-----
  --dry-run               NO escribe propuestas (default: True)
  --ejecutar-propuestas   Persiste en omicronvt.dbo.autorepo_propuestas
                          (anula --dry-run)
  --mes-target YYYY-MM    Mes objetivo presupuesto (default: mes actual)
  --solo-deps 0,2,8       Lista CSV de depósitos (default: DEPOS_AUTOREPO_F1)
  --log-level INFO        DEBUG | INFO | WARN | ERROR
  --forzar-greedy         Salta OR-Tools, usa greedy directo

Salida
------
  0  OK
  1  Error (conexión, extract, persistencia, etc)
  2  Lock ocupado (ya hay una corrida en curso <30 min)

Fecha: 11-abr-2026
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# Paths y constantes locales
# ---------------------------------------------------------------------------

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_AUTOREPO_DIR = os.path.join(_THIS_DIR, 'autorepo')
_LOGS_DIR = os.path.join(_AUTOREPO_DIR, 'logs')
_LOCK_PATH = os.path.join(_AUTOREPO_DIR, '.lock')
_ALERTAS_PATH = os.path.join(_AUTOREPO_DIR, 'alertas.txt')
_LOCK_STALE_MINUTES = 30

# Marcas gasto que siempre excluimos de queries comerciales
EXCL_MARCAS_GASTOS = '(1316,1317,1158,436)'

# Logger global del engine
logger = logging.getLogger('autorepo_engine')


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='autorepo_engine',
        description='Motor autocompensación inter-depósito H4/CALZALINDO',
    )
    p.add_argument(
        '--modo',
        choices=['urgente', 'rebalanceo', 'auditoria'],
        default='rebalanceo',
        help='Modo de operación (default: rebalanceo)',
    )
    p.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='No persiste propuestas (default: True)',
    )
    p.add_argument(
        '--ejecutar-propuestas',
        action='store_true',
        help='Persiste propuestas en omicronvt (anula --dry-run)',
    )
    p.add_argument(
        '--mes-target',
        default=None,
        help='YYYY-MM, default = mes actual',
    )
    p.add_argument(
        '--solo-deps',
        default=None,
        help='CSV de depósitos a usar (default: DEPOS_AUTOREPO_F1)',
    )
    p.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARN', 'ERROR'],
    )
    p.add_argument(
        '--forzar-greedy',
        action='store_true',
        help='No usar OR-Tools, ir directo a greedy',
    )
    return p


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _setup_logging(log_level: str, modo: str) -> logging.Logger:
    """Configura logger a archivo + consola. Idempotente."""
    try:
        os.makedirs(_LOGS_DIR, exist_ok=True)
    except OSError:
        # Si no podemos crear el dir, al menos logueamos a consola
        pass

    level = getattr(logging, log_level.upper(), logging.INFO)
    # WARN no existe como constante en logging, mapeamos a WARNING
    if log_level.upper() == 'WARN':
        level = logging.WARNING

    root = logging.getLogger()
    root.setLevel(level)

    # Limpiar handlers previos (relevante si se importa desde test)
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # Consola
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # Archivo (si el dir existe)
    if os.path.isdir(_LOGS_DIR):
        ts = datetime.now().strftime('%Y%m%d')
        log_path = os.path.join(_LOGS_DIR, f'autorepo_{modo}_{ts}.log')
        try:
            fh = logging.FileHandler(log_path, encoding='utf-8')
            fh.setLevel(level)
            fh.setFormatter(fmt)
            root.addHandler(fh)
        except OSError:
            pass

    logger.setLevel(level)
    return logger


# ---------------------------------------------------------------------------
# Lock file
# ---------------------------------------------------------------------------


def _acquire_lock(lock_path: str) -> bool:
    """Toma el lock. Retorna True si lo adquirió, False si está ocupado fresco.

    Si el lock existe pero es stale (>_LOCK_STALE_MINUTES), lo sobrescribe.
    """
    try:
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    except OSError:
        pass

    if os.path.exists(lock_path):
        try:
            mtime = os.path.getmtime(lock_path)
            age_min = (datetime.now().timestamp() - mtime) / 60.0
        except OSError:
            age_min = 0.0

        if age_min < _LOCK_STALE_MINUTES:
            logger.error(
                "Lock ocupado (%.1f min < %d min). Otra corrida en curso.",
                age_min,
                _LOCK_STALE_MINUTES,
            )
            return False
        else:
            logger.warning(
                "Lock stale (%.1f min > %d min). Sobrescribiendo.",
                age_min,
                _LOCK_STALE_MINUTES,
            )

    try:
        with open(lock_path, 'w', encoding='utf-8') as f:
            f.write(f'pid={os.getpid()}\n')
            f.write(f'started={datetime.now().isoformat()}\n')
    except OSError as e:
        logger.error("No pude crear lock file %s: %s", lock_path, e)
        return False

    return True


def _release_lock(lock_path: str) -> None:
    try:
        if os.path.exists(lock_path):
            os.remove(lock_path)
    except OSError as e:
        logger.warning("No pude liberar lock %s: %s", lock_path, e)


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------


def _escribir_alerta(razon: str) -> None:
    """Graba una línea en autorepo/alertas.txt. Silencioso si falla."""
    try:
        os.makedirs(os.path.dirname(_ALERTAS_PATH), exist_ok=True)
        with open(_ALERTAS_PATH, 'a', encoding='utf-8') as f:
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f'[{ts}] {razon}\n')
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Extract: stock + velocidades + datos articulo
# ---------------------------------------------------------------------------


def _connect(conn_string: str):
    """Intenta conectar con pyodbc. Retorna conn o lanza excepción."""
    import pyodbc  # import local: puede no estar instalado en laptops dev
    return pyodbc.connect(conn_string, timeout=15)


def _extract_stock_y_velocidades(
    deps: list[int],
    conn_string: str,
) -> tuple[list, dict]:
    """
    Extrae estados pre-clasificados y datos de artículo.

    Retorna:
      estados_raw: list[dict] con keys:
        articulo, deposito, stock_actual, pares_90d, vel_diaria,
        dias_sin_venta, dias_sin_compra
      articulos_set: set[int] con todos los articulos que tocamos
    """
    deps_csv = ','.join(str(d) for d in deps)
    logger.info("Extract: stock+ventas deps=%s", deps_csv)

    # Query combinada: stock por (art, depo) + ventas 90d + dias sin venta/compra
    # Excluimos comprobantes de remitos (7, 36) y marcas de gasto.
    sql_stock_ventas = f"""
        WITH stock AS (
            SELECT articulo, deposito, SUM(stock_actual) AS stock_actual
            FROM msgestionC.dbo.stock
            WHERE serie = ' '
              AND deposito IN ({deps_csv})
            GROUP BY articulo, deposito
        ),
        ventas90 AS (
            SELECT v.articulo, v.deposito,
                   SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                            WHEN v.operacion='-' THEN -v.cantidad
                            ELSE 0 END) AS pares_90d,
                   MAX(v.fecha) AS ultima_venta
            FROM msgestionC.dbo.ventas1 v
            WHERE v.fecha >= DATEADD(day, -90, GETDATE())
              AND v.deposito IN ({deps_csv})
              AND v.codigo NOT IN (7, 36)
            GROUP BY v.articulo, v.deposito
        ),
        ultima_compra AS (
            SELECT articulo, MAX(fecha) AS ultima_compra
            FROM msgestionC.dbo.compras1
            WHERE operacion = '+'
              AND fecha >= DATEADD(year, -2, GETDATE())
            GROUP BY articulo
        )
        SELECT s.articulo,
               s.deposito,
               s.stock_actual,
               ISNULL(v.pares_90d, 0)                           AS pares_90d,
               CAST(ISNULL(v.pares_90d, 0) AS FLOAT) / 90.0     AS vel_diaria,
               CASE WHEN v.ultima_venta IS NULL THEN 999
                    ELSE DATEDIFF(day, v.ultima_venta, GETDATE()) END AS dias_sin_venta,
               CASE WHEN uc.ultima_compra IS NULL THEN 999
                    ELSE DATEDIFF(day, uc.ultima_compra, GETDATE()) END AS dias_sin_compra
        FROM stock s
        LEFT JOIN ventas90 v
               ON v.articulo = s.articulo AND v.deposito = s.deposito
        LEFT JOIN ultima_compra uc
               ON uc.articulo = s.articulo
        WHERE s.stock_actual > 0 OR v.pares_90d > 0
    """

    estados_raw: list[dict] = []
    articulos_set: set[int] = set()

    with _connect(conn_string) as cn:
        cur = cn.cursor()
        cur.execute(sql_stock_ventas)
        for row in cur.fetchall():
            art = int(row[0])
            estados_raw.append({
                'articulo': art,
                'deposito': int(row[1]),
                'stock_actual': int(row[2] or 0),
                'pares_90d': int(row[3] or 0),
                'vel_diaria': float(row[4] or 0.0),
                'dias_sin_venta': int(row[5] or 999),
                'dias_sin_compra': int(row[6] or 999),
            })
            articulos_set.add(art)

    logger.info(
        "Extract: %d filas (art,depo), %d articulos únicos",
        len(estados_raw),
        len(articulos_set),
    )
    return estados_raw, articulos_set


def _extract_datos_articulo(
    articulos: set[int],
    conn_string: str,
) -> dict:
    """
    Trae datos maestros del artículo: subrubro, rubro, marca, precio_costo, margen.
    Retorna dict[articulo] -> dict.

    Excluye marcas de gasto (EXCL_MARCAS_GASTOS).
    """
    if not articulos:
        return {}

    # Batchear IN si son muchos (SQL Server limita ~2100 params por query).
    articulos_list = list(articulos)
    BATCH = 1500

    out: dict = {}

    with _connect(conn_string) as cn:
        cur = cn.cursor()
        for i in range(0, len(articulos_list), BATCH):
            chunk = articulos_list[i:i + BATCH]
            in_clause = ','.join(str(a) for a in chunk)
            sql = f"""
                SELECT a.codigo AS articulo,
                       a.subrubro,
                       a.rubro,
                       a.marca,
                       ISNULL(a.precio_costo, 0)  AS precio_costo,
                       ISNULL(a.utilidad_1, 0)    AS margen_pct
                FROM msgestion01art.dbo.articulo a
                WHERE a.codigo IN ({in_clause})
                  AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
            """
            cur.execute(sql)
            for row in cur.fetchall():
                art = int(row[0])
                out[art] = {
                    'articulo': art,
                    'subrubro': int(row[1] or 0),
                    'rubro': int(row[2] or 0),
                    'marca': int(row[3] or 0),
                    'precio_costo': float(row[4] or 0.0),
                    'margen_pct': float(row[5] or 0.0),
                }

    logger.info("Extract: datos maestros de %d articulos", len(out))
    return out


def _extract_p95_vel_por_subrubro(conn_string: str) -> dict:
    """
    P95 de velocidad diaria por subrubro (ventas 90d / 90).
    Usado por el scoring para normalizar v_dest.

    Retorna dict[subrubro] -> p95_vel_diaria.
    """
    # SQL Server 2012 RTM con compat 100 no soporta PERCENTILE_CONT.
    # Traemos todas las velocidades por (subrubro, articulo) y calculamos
    # el percentil 95 en Python.
    sql = f"""
        SELECT a.subrubro,
               CAST(SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                             WHEN v.operacion='-' THEN -v.cantidad
                             ELSE 0 END) AS FLOAT) / 90.0 AS vel
        FROM msgestionC.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.fecha >= DATEADD(day, -90, GETDATE())
          AND v.codigo NOT IN (7, 36)
          AND a.marca NOT IN {EXCL_MARCAS_GASTOS}
        GROUP BY a.subrubro, v.articulo
        HAVING SUM(CASE WHEN v.operacion='+' THEN v.cantidad
                        WHEN v.operacion='-' THEN -v.cantidad
                        ELSE 0 END) > 0
    """

    from collections import defaultdict
    vels_por_sub: dict = defaultdict(list)
    try:
        with _connect(conn_string) as cn:
            cur = cn.cursor()
            cur.execute(sql)
            for row in cur.fetchall():
                sub = int(row[0] or 0)
                vel = float(row[1] or 0.0)
                if vel > 0:
                    vels_por_sub[sub].append(vel)
    except Exception as e:  # noqa: BLE001
        logger.warning("p95_vel_por_subrubro falló (%s); usando dict vacío", e)
        return {}

    out: dict = {}
    for sub, vels in vels_por_sub.items():
        if not vels:
            continue
        vels.sort()
        idx = int(round(0.95 * (len(vels) - 1)))
        out[sub] = vels[idx]

    logger.info("Extract: p95_vel para %d subrubros", len(out))
    return out


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------


def _persistir_propuestas(
    propuestas: list,
    tipo: str,
    conn_string: str,
    dry_run: bool,
) -> int:
    """
    Inserta propuestas en omicronvt.dbo.autorepo_propuestas + _det.
    Retorna N propuestas insertadas.

    Si dry_run=True → NO escribe nada, solo cuenta cuántas hubiera escrito.
    """
    if not propuestas:
        logger.info("Persistencia: 0 propuestas a insertar")
        return 0

    if dry_run:
        logger.info(
            "Persistencia DRY-RUN: %d propuestas NO insertadas (usar --ejecutar-propuestas)",
            len(propuestas),
        )
        return 0

    # Import local para poder importar config solo cuando hace falta
    try:
        from config import DEPOSITO_EMPRESA
    except Exception:
        DEPOSITO_EMPRESA = {}

    sql_cab = """
        INSERT INTO omicronvt.dbo.autorepo_propuestas
            (fecha_corrida, tipo, base_destino, deposito_emisor, deposito_receptor,
             estado, total_pares, total_costo_cer, score_promedio,
             beneficio_esperado, costo_transferencia)
        OUTPUT INSERTED.id
        VALUES (GETDATE(), ?, ?, ?, ?, 'PENDIENTE', ?, ?, ?, ?, ?)
    """

    sql_det = """
        INSERT INTO omicronvt.dbo.autorepo_propuestas_det
            (propuesta_id, articulo, cantidad, precio_costo, score, motivo)
        VALUES (?, ?, ?, ?, ?, ?)
    """

    insertadas = 0
    with _connect(conn_string) as cn:
        cur = cn.cursor()
        for p in propuestas:
            empresa = DEPOSITO_EMPRESA.get(p.destino)
            base_destino = None
            if empresa == 'H4':
                base_destino = 'MSGESTION03'
            elif empresa == 'CALZALINDO':
                base_destino = 'MSGESTION01'

            cur.execute(
                sql_cab,
                tipo.upper(),
                base_destino,
                int(p.origen),
                int(p.destino),
                int(p.total_pares),
                float(p.total_costo_cer),
                float(p.score_promedio),
                float(p.beneficio_esperado),
                float(p.costo_transferencia),
            )
            prop_id = cur.fetchone()[0]

            for ln in p.lineas:
                cur.execute(
                    sql_det,
                    int(prop_id),
                    int(ln.articulo),
                    int(ln.cantidad),
                    float(ln.precio_costo),
                    float(ln.score),
                    ln.motivo[:50] if ln.motivo else None,
                )

            insertadas += 1

        cn.commit()

    logger.info("Persistencia: %d propuestas insertadas (tipo=%s)", insertadas, tipo)
    return insertadas


# ---------------------------------------------------------------------------
# Pipeline: clasificar + decidir
# ---------------------------------------------------------------------------


def _clasificar_estados(
    estados_raw: list,
    datos_art: dict,
) -> list:
    """
    Invoca autorepo.umbrales.clasificar_stock para cada fila raw.
    Filtra articulos sin datos maestros.

    Default de ABCXYZ: 'BX' (mix medio, alta predictibilidad).
    """
    from autorepo.umbrales import clasificar_stock

    out = []
    skipped = 0
    for r in estados_raw:
        art = r['articulo']
        d = datos_art.get(art)
        if not d:
            skipped += 1
            continue

        # ABCXYZ default: 'BX' (mix medio). Si tenemos una copia del clasificador
        # real la podemos enchufar después.
        abcxyz = 'BX'

        estado = clasificar_stock(
            articulo=art,
            deposito=r['deposito'],
            stock_actual=r['stock_actual'],
            vel_diaria=r['vel_diaria'],
            abcxyz_clase=abcxyz,
            subrubro=d['subrubro'],
            temporada_activa=True,  # TODO: enchufar SUBRUBRO_TEMPORADA
            dias_sin_venta=r['dias_sin_venta'],
            dias_sin_compra=r['dias_sin_compra'],
        )
        out.append(estado)

    if skipped:
        logger.warning(
            "Clasificar: %d filas sin datos maestros descartadas (de gasto o inexistentes)",
            skipped,
        )
    logger.info("Clasificar: %d estados procesados", len(out))
    return out


def _construir_datos_articulo_para_decisor(datos_art: dict) -> dict:
    """
    Convierte dict[art] -> dict simple en dict[art] -> DatosArticulo.
    Usa defaults razonables para campos que el extract no trae.
    """
    from autorepo.decisor import DatosArticulo

    out = {}
    for art, d in datos_art.items():
        out[art] = DatosArticulo(
            articulo=art,
            subrubro=d['subrubro'],
            rubro=d['rubro'],
            marca=d['marca'],
            precio_costo=d['precio_costo'],
            margen_pct=d['margen_pct'],
            abcxyz_clase='BX',
            factor_estacional=1.0,
            afinidad_local={},
            curva_ideal_subrubro={},
            stock_origen_por_talle={},
            talle_objeto=None,
        )
    return out


# ---------------------------------------------------------------------------
# Modo: urgente / rebalanceo
# ---------------------------------------------------------------------------


def _run_standard(args, modo: str) -> int:
    """Ejecuta una corrida 'urgente' o 'rebalanceo' (misma pipeline)."""
    try:
        from config import CONN_COMPRAS, DEPOS_AUTOREPO_F1
    except Exception as e:
        logger.error("No pude importar config: %s", e)
        _escribir_alerta(f"import config falló: {e}")
        return 1

    # Deps a usar
    if args.solo_deps:
        try:
            deps = [int(d.strip()) for d in args.solo_deps.split(',') if d.strip()]
        except ValueError as e:
            logger.error("--solo-deps inválido: %s", e)
            return 1
    else:
        deps = list(DEPOS_AUTOREPO_F1)

    if not deps:
        logger.error("Lista de depósitos vacía")
        return 1

    # Mes target (para presupuesto)
    mes_target = args.mes_target
    if not mes_target:
        now = datetime.now()
        mes_target = f"{now.year:04d}-{now.month:02d}"

    logger.info(
        "run_standard: modo=%s deps=%s mes_target=%s forzar_greedy=%s",
        modo, deps, mes_target, args.forzar_greedy,
    )

    # 1) Extract stock + velocidades
    try:
        estados_raw, articulos_set = _extract_stock_y_velocidades(
            deps=deps, conn_string=CONN_COMPRAS,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("Extract stock/velocidades falló: %s", e)
        logger.debug("Traceback: %s", traceback.format_exc())
        _escribir_alerta(f"extract stock falló: {e}")
        return 1

    if not estados_raw:
        logger.warning("Extract: 0 filas. Nada para clasificar. Salida OK.")
        return 0

    # 2) Extract datos maestros
    try:
        datos_art = _extract_datos_articulo(articulos_set, CONN_COMPRAS)
    except Exception as e:  # noqa: BLE001
        logger.error("Extract datos articulo falló: %s", e)
        logger.debug("Traceback: %s", traceback.format_exc())
        _escribir_alerta(f"extract articulos falló: {e}")
        return 1

    if not datos_art:
        logger.warning("Extract: 0 datos de articulo (todos de gasto?). Salida OK.")
        return 0

    # 3) p95 vel por subrubro
    try:
        p95 = _extract_p95_vel_por_subrubro(CONN_COMPRAS)
    except Exception as e:  # noqa: BLE001
        logger.warning("p95 falló (%s); usando dict vacío", e)
        p95 = {}

    # 4) Clasificar estados
    estados = _clasificar_estados(estados_raw, datos_art)
    if not estados:
        logger.warning("Clasificar: 0 estados válidos. Salida OK.")
        return 0

    # 5) Presupuesto por depósito
    try:
        from autorepo.presupuesto import calcular_presupuestos
        presupuestos = calcular_presupuestos(
            mes_target=mes_target,
            deps=tuple(deps),
            conn_string=CONN_COMPRAS,
        )
        presup_destino = {
            p.depo: (p.presupuesto_ajustado or p.presupuesto_sugerido or 0.0)
            for p in presupuestos
        }
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "calcular_presupuestos falló (%s); usando presupuesto inf por depo",
            e,
        )
        presup_destino = {d: 1e12 for d in deps}

    logger.info("Presupuesto destino: %s", {k: round(v, 0) for k, v in presup_destino.items()})

    # 6) Decidir
    try:
        from autorepo.decisor import decidir
    except Exception as e:
        logger.error("Import autorepo.decisor falló: %s", e)
        _escribir_alerta(f"import decisor falló: {e}")
        return 1

    datos_decisor = _construir_datos_articulo_para_decisor(datos_art)

    try:
        resultado = decidir(
            estados=estados,
            datos_art=datos_decisor,
            presupuesto_destino=presup_destino,
            p95_vel_por_subrubro=p95,
            modo=modo.upper(),
            usar_greedy=bool(args.forzar_greedy),
        )
    except Exception as e:  # noqa: BLE001
        logger.error("decidir() falló: %s", e)
        logger.debug("Traceback: %s", traceback.format_exc())
        _escribir_alerta(f"decidir falló: {e}")
        return 1

    logger.info(
        "Decisor: solver=%s tiempo=%dms arcos_eval=%d arcos_score=%d propuestas=%d",
        resultado.solver_usado,
        resultado.tiempo_ms,
        resultado.arcs_evaluados,
        resultado.arcs_con_score_valido,
        len(resultado.propuestas),
    )

    # 7) Persistir (o dry-run)
    dry_run = not bool(args.ejecutar_propuestas)
    try:
        n = _persistir_propuestas(
            propuestas=resultado.propuestas,
            tipo=modo,
            conn_string=CONN_COMPRAS,
            dry_run=dry_run,
        )
    except Exception as e:  # noqa: BLE001
        logger.error("Persistir propuestas falló: %s", e)
        logger.debug("Traceback: %s", traceback.format_exc())
        _escribir_alerta(f"persistir falló: {e}")
        return 1

    logger.info(
        "run_standard OK: modo=%s propuestas=%d %s",
        modo, len(resultado.propuestas),
        "(insertadas)" if not dry_run else "(dry-run)",
    )
    _ = n  # silencia unused
    return 0


def _run_urgente(args) -> int:
    return _run_standard(args, modo='urgente')


def _run_rebalanceo(args) -> int:
    return _run_standard(args, modo='rebalanceo')


# ---------------------------------------------------------------------------
# Modo: auditoria
# ---------------------------------------------------------------------------


def _run_auditoria(args) -> int:
    """
    Audita propuestas del mes anterior: KPI VRPM + tasa aceptación.
    NO genera propuestas nuevas ni modifica UMBRALES_V1 — solo loguea.
    """
    try:
        from config import CONN_COMPRAS
    except Exception as e:
        logger.error("No pude importar config: %s", e)
        _escribir_alerta(f"import config falló: {e}")
        return 1

    # Ventana: mes anterior al actual
    hoy = datetime.now()
    primer_dia_mes = hoy.replace(day=1)
    fin_mes_ant = primer_dia_mes - timedelta(days=1)
    inicio_mes_ant = fin_mes_ant.replace(day=1)

    logger.info(
        "Auditoria: ventana %s → %s",
        inicio_mes_ant.strftime('%Y-%m-%d'),
        fin_mes_ant.strftime('%Y-%m-%d'),
    )

    sql_resumen = """
        SELECT
            p.estado,
            COUNT(*)                  AS n_propuestas,
            SUM(p.total_pares)        AS pares,
            SUM(p.total_costo_cer)    AS costo,
            AVG(CAST(p.score_promedio AS FLOAT))  AS score_prom
        FROM omicronvt.dbo.autorepo_propuestas p
        WHERE p.fecha_corrida >= ?
          AND p.fecha_corrida <  ?
        GROUP BY p.estado
    """

    try:
        with _connect(CONN_COMPRAS) as cn:
            cur = cn.cursor()
            cur.execute(
                sql_resumen,
                inicio_mes_ant,
                primer_dia_mes,
            )
            rows = cur.fetchall()
    except Exception as e:  # noqa: BLE001
        logger.error("Auditoria query falló: %s", e)
        logger.debug("Traceback: %s", traceback.format_exc())
        _escribir_alerta(f"auditoria falló: {e}")
        return 1

    if not rows:
        logger.warning("Auditoria: sin propuestas en el mes anterior")
        return 0

    total = 0
    aprob = 0
    for estado, n, pares, costo, score in rows:
        logger.info(
            "  %s: n=%s pares=%s costo=%s score_prom=%s",
            estado, n, pares, costo, score,
        )
        total += int(n or 0)
        if (estado or '').upper() in ('APROBADA', 'EJECUTADA'):
            aprob += int(n or 0)

    tasa_ok = (aprob / total) if total else 0.0
    logger.info(
        "Auditoria resumen: total=%d aprobadas=%d tasa_aceptacion=%.2f%%",
        total, aprob, tasa_ok * 100,
    )

    # Sugerencias de recalibración (placeholder)
    if tasa_ok < 0.5:
        logger.warning(
            "Tasa aceptación < 50%%: considerar subir SCORE_MIN_ACEPTACION o "
            "ajustar umbrales sobrestock"
        )
    elif tasa_ok > 0.9:
        logger.info(
            "Tasa aceptación > 90%%: el motor está bien calibrado; podríamos "
            "relajar umbrales para capturar más casos"
        )
    else:
        logger.info("Tasa aceptación en rango aceptable 50-90%%")

    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # --ejecutar-propuestas anula --dry-run
    if args.ejecutar_propuestas:
        args.dry_run = False

    modo = args.modo.lower()
    _setup_logging(args.log_level, modo)

    logger.info(
        "=" * 60,
    )
    logger.info(
        "autorepo_engine start: modo=%s dry_run=%s mes=%s",
        modo, args.dry_run, args.mes_target,
    )
    logger.info(
        "=" * 60,
    )

    # Lock (para urgente/rebalanceo; auditoria tampoco pasa nada si lockea)
    if not _acquire_lock(_LOCK_PATH):
        _escribir_alerta(f"lock ocupado modo={modo}")
        return 2

    exit_code = 1
    try:
        if modo == 'urgente':
            exit_code = _run_urgente(args)
        elif modo == 'rebalanceo':
            exit_code = _run_rebalanceo(args)
        elif modo == 'auditoria':
            exit_code = _run_auditoria(args)
        else:
            logger.error("Modo desconocido: %s", modo)
            exit_code = 1
    except KeyboardInterrupt:
        logger.warning("Interrumpido por usuario")
        exit_code = 1
    except Exception as e:  # noqa: BLE001
        logger.error("Error no capturado en main: %s", e)
        logger.debug("Traceback: %s", traceback.format_exc())
        _escribir_alerta(f"error no capturado modo={modo}: {e}")
        exit_code = 1
    finally:
        _release_lock(_LOCK_PATH)
        logger.info("autorepo_engine end: exit=%d", exit_code)

    if exit_code != 0:
        _escribir_alerta(f"exit_code={exit_code} modo={modo}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
