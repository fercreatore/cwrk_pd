# -*- coding: utf-8 -*-
"""
Capa de acceso a datos para el Task Manager.

Todas las operaciones SQL contra omicronvt.dbo.tareas_equipo
y tablas relacionadas.
"""

import logging
from datetime import datetime
from typing import Optional

import pyodbc

try:
    from .config import SQL_CONN_STRING, semana_actual
except ImportError:
    from config import SQL_CONN_STRING, semana_actual

logger = logging.getLogger("task_manager.db")


def _get_conn():
    """Obtiene conexion a SQL Server."""
    return pyodbc.connect(SQL_CONN_STRING, timeout=15)


# ── INSERT ──

def crear_tarea(
    titulo: str,
    responsable_nombre: str,
    responsable_wa: str = None,
    responsable_chatwoot_id: int = None,
    asignado_por: str = "Fernando",
    deadline: datetime = None,
    prioridad: str = "P1",
    area: str = None,
    canal_entrega: str = None,
    resultado_esperado: str = None,
    mensaje_original: str = None,
) -> int:
    """
    Inserta una tarea nueva y retorna el ID generado.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO omicronvt.dbo.tareas_equipo (
                titulo, responsable_nombre, responsable_wa,
                responsable_chatwoot_id, asignado_por, deadline,
                prioridad, area, canal_entrega, resultado_esperado,
                semana_asignacion, mensaje_original
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            titulo, responsable_nombre, responsable_wa,
            responsable_chatwoot_id, asignado_por, deadline,
            prioridad, area, canal_entrega, resultado_esperado,
            semana_actual(), mensaje_original,
        ))
        # Obtener el ID recien insertado
        cursor.execute("SELECT SCOPE_IDENTITY()")
        row = cursor.fetchone()
        tarea_id = int(row[0])
        conn.commit()

        # Log en historial
        _log_historial(cursor, tarea_id, None, "ASIGNADA", "Tarea creada", asignado_por)
        conn.commit()

        logger.info(f"Tarea #{tarea_id} creada: {titulo} -> {responsable_nombre}")
        return tarea_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── UPDATE ──

def actualizar_estado(
    tarea_id: int,
    nuevo_estado: str,
    notas: str = None,
    porcentaje: int = None,
    motivo_bloqueo: str = None,
    autor: str = None,
) -> bool:
    """
    Actualiza el estado de una tarea.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()

        # Obtener estado actual
        cursor.execute(
            "SELECT estado FROM omicronvt.dbo.tareas_equipo WHERE id = ?",
            (tarea_id,)
        )
        row = cursor.fetchone()
        if not row:
            logger.warning(f"Tarea #{tarea_id} no encontrada")
            return False

        estado_anterior = row[0]

        # Construir UPDATE
        sets = ["estado = ?", "fecha_ultima_actualizacion = GETDATE()"]
        params = [nuevo_estado]

        if notas:
            # Append a notas_avance
            sets.append(
                "notas_avance = CASE WHEN notas_avance IS NULL "
                "THEN ? ELSE notas_avance + CHAR(10) + ? END"
            )
            timestamp = datetime.now().strftime("%d/%m %H:%M")
            nota_con_ts = f"[{timestamp}] {notas}"
            params.extend([nota_con_ts, nota_con_ts])

        if porcentaje is not None:
            sets.append("porcentaje_avance = ?")
            params.append(porcentaje)

        if motivo_bloqueo:
            sets.append("motivo_bloqueo = ?")
            params.append(motivo_bloqueo)

        if nuevo_estado == "COMPLETA":
            sets.append("fecha_completada = GETDATE()")
            sets.append("porcentaje_avance = 100")

        params.append(tarea_id)

        sql = f"UPDATE omicronvt.dbo.tareas_equipo SET {', '.join(sets)} WHERE id = ?"
        cursor.execute(sql, params)

        # Log en historial
        _log_historial(cursor, tarea_id, estado_anterior, nuevo_estado, notas, autor)

        conn.commit()
        logger.info(f"Tarea #{tarea_id}: {estado_anterior} -> {nuevo_estado}")
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _log_historial(cursor, tarea_id, estado_anterior, estado_nuevo, notas, autor):
    """Inserta un registro en tareas_historial."""
    try:
        cursor.execute("""
            INSERT INTO omicronvt.dbo.tareas_historial
                (tarea_id, estado_anterior, estado_nuevo, notas, autor)
            VALUES (?, ?, ?, ?, ?)
        """, (tarea_id, estado_anterior, estado_nuevo, notas, autor))
    except Exception:
        logger.exception("Error insertando historial")


# ── QUERIES ──

def tareas_persona(nombre: str, solo_activas: bool = True) -> list:
    """
    Obtiene tareas de una persona.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        sql = """
            SELECT id, titulo, deadline, prioridad, estado,
                   porcentaje_avance, motivo_bloqueo, canal_entrega,
                   resultado_esperado
            FROM omicronvt.dbo.tareas_equipo
            WHERE responsable_nombre LIKE ?
        """
        params = [f"%{nombre}%"]

        if solo_activas:
            sql += " AND estado NOT IN ('COMPLETA', 'CANCELADA')"

        sql += " ORDER BY prioridad, deadline"
        cursor.execute(sql, params)

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                "id": row[0],
                "titulo": row[1],
                "deadline": row[2],
                "prioridad": row[3],
                "estado": row[4],
                "porcentaje": row[5],
                "motivo_bloqueo": row[6],
                "canal_entrega": row[7],
                "resultado_esperado": row[8],
            })
        return resultado
    finally:
        conn.close()


def tareas_pendientes(semana: str = None) -> list:
    """Obtiene todas las tareas no completadas/canceladas."""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        sql = """
            SELECT id, titulo, responsable_nombre, deadline, prioridad,
                   estado, porcentaje_avance, motivo_bloqueo, area
            FROM omicronvt.dbo.tareas_equipo
            WHERE estado NOT IN ('COMPLETA', 'CANCELADA')
        """
        params = []
        if semana:
            sql += " AND semana_asignacion = ?"
            params.append(semana)

        sql += " ORDER BY prioridad, deadline, responsable_nombre"
        cursor.execute(sql, params)

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                "id": row[0],
                "titulo": row[1],
                "responsable": row[2],
                "deadline": row[3],
                "prioridad": row[4],
                "estado": row[5],
                "porcentaje": row[6],
                "motivo_bloqueo": row[7],
                "area": row[8],
            })
        return resultado
    finally:
        conn.close()


def tareas_vencidas() -> list:
    """Obtiene tareas cuyo deadline ya paso y no estan completas."""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, titulo, responsable_nombre, deadline, prioridad,
                   estado, porcentaje_avance
            FROM omicronvt.dbo.tareas_equipo
            WHERE estado NOT IN ('COMPLETA', 'CANCELADA')
              AND deadline < CAST(GETDATE() AS DATE)
            ORDER BY deadline, prioridad
        """)

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                "id": row[0],
                "titulo": row[1],
                "responsable": row[2],
                "deadline": row[3],
                "prioridad": row[4],
                "estado": row[5],
                "porcentaje": row[6],
            })
        return resultado
    finally:
        conn.close()


def resumen_semana(semana: str = None) -> dict:
    """
    Genera resumen de la semana.
    Retorna dict con totales y detalle por persona.
    """
    if not semana:
        semana = semana_actual()

    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT responsable_nombre, estado, COUNT(*) as cnt
            FROM omicronvt.dbo.tareas_equipo
            WHERE semana_asignacion = ?
            GROUP BY responsable_nombre, estado
            ORDER BY responsable_nombre
        """, (semana,))

        por_persona = {}
        totales = {"total": 0, "completas": 0, "pendientes": 0, "bloqueadas": 0}

        for row in cursor.fetchall():
            nombre = row[0]
            estado = row[1]
            cnt = row[2]

            if nombre not in por_persona:
                por_persona[nombre] = {
                    "total": 0, "completas": 0, "pendientes": 0, "bloqueadas": 0
                }

            por_persona[nombre]["total"] += cnt
            totales["total"] += cnt

            if estado == "COMPLETA":
                por_persona[nombre]["completas"] += cnt
                totales["completas"] += cnt
            elif estado == "BLOQUEADA":
                por_persona[nombre]["bloqueadas"] += cnt
                totales["bloqueadas"] += cnt
            else:
                por_persona[nombre]["pendientes"] += cnt
                totales["pendientes"] += cnt

        return {
            "semana": semana,
            "totales": totales,
            "por_persona": por_persona,
        }
    finally:
        conn.close()


def tarea_activa_de_persona(nombre: str) -> Optional[dict]:
    """
    Obtiene la tarea activa mas urgente de una persona.
    Usada cuando un responsable envia un update sin especificar tarea.
    """
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1 id, titulo, deadline, prioridad, estado,
                   porcentaje_avance
            FROM omicronvt.dbo.tareas_equipo
            WHERE responsable_nombre LIKE ?
              AND estado IN ('ASIGNADA', 'EN_PROGRESO', 'BLOQUEADA')
            ORDER BY
                CASE prioridad WHEN 'P0' THEN 0 WHEN 'P1' THEN 1
                     WHEN 'P2' THEN 2 ELSE 3 END,
                deadline
        """, (f"%{nombre}%",))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": row[0],
            "titulo": row[1],
            "deadline": row[2],
            "prioridad": row[3],
            "estado": row[4],
            "porcentaje": row[5],
        }
    finally:
        conn.close()


def personas_con_tareas_activas() -> list:
    """Retorna lista de nombres con tareas activas y sus telefonos."""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT responsable_nombre, responsable_wa
            FROM omicronvt.dbo.tareas_equipo
            WHERE estado IN ('ASIGNADA', 'EN_PROGRESO', 'BLOQUEADA')
        """)
        return [{"nombre": row[0], "wa": row[1]} for row in cursor.fetchall()]
    finally:
        conn.close()
