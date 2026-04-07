# -*- coding: utf-8 -*-
"""
Task Manager — FastAPI app principal.

Endpoints:
  POST /webhook/chatwoot  — Recibe eventos de Chatwoot
  GET  /tareas            — Lista tareas (con filtros)
  GET  /tareas/{id}       — Detalle de una tarea
  POST /tareas            — Crear tarea manualmente (API)
  PATCH /tareas/{id}      — Actualizar estado
  POST /checkpoint        — Disparar checkpoint miercoles manualmente
  POST /cierre            — Disparar cierre viernes manualmente
  GET  /health            — Healthcheck

USO:
  # Desarrollo local
  uvicorn task_manager.main:app --host 0.0.0.0 --port 8002 --reload

  # Produccion (en 112)
  C:\\...\\python.exe -m uvicorn task_manager.main:app --host 0.0.0.0 --port 8002
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

try:
    from .chatwoot_webhook import procesar_webhook
    from .scheduler import generar_checkpoint_miercoles, generar_cierre_viernes
    from . import db
    from .config import WEBHOOK_SECRET
except ImportError:
    from chatwoot_webhook import procesar_webhook
    from scheduler import generar_checkpoint_miercoles, generar_cierre_viernes
    import db
    from config import WEBHOOK_SECRET

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("task_manager")

# App
app = FastAPI(
    title="Task Manager H4/CALZALINDO",
    description="Chatbot WhatsApp para gestion de tareas del equipo",
    version="1.0.0",
)


# ── Modelos Pydantic ──

class TareaCreate(BaseModel):
    titulo: str
    responsable_nombre: str
    responsable_wa: Optional[str] = None
    deadline: Optional[str] = None  # formato YYYY-MM-DD
    prioridad: Optional[str] = "P1"
    area: Optional[str] = None
    canal_entrega: Optional[str] = None
    resultado_esperado: Optional[str] = None


class TareaUpdate(BaseModel):
    estado: Optional[str] = None
    notas: Optional[str] = None
    porcentaje: Optional[int] = None
    motivo_bloqueo: Optional[str] = None


# ── Endpoints ──

@app.get("/health")
async def health():
    """Healthcheck."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/webhook/chatwoot")
async def webhook_chatwoot(request: Request):
    """
    Recibe eventos de Chatwoot y los procesa.

    Configurar en Chatwoot:
      Settings > Integrations > Webhooks
      URL: http://192.168.2.112:8002/webhook/chatwoot
      Events: message_created
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    logger.info(f"Webhook recibido: event={payload.get('event')}")

    resultado = procesar_webhook(payload, dry_run=False)
    return JSONResponse(content=resultado)


@app.get("/tareas")
async def listar_tareas(
    responsable: Optional[str] = Query(None, description="Filtrar por nombre"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    semana: Optional[str] = Query(None, description="Filtrar por semana (2026-W14)"),
    solo_activas: bool = Query(True, description="Excluir COMPLETA/CANCELADA"),
):
    """Lista tareas con filtros opcionales."""
    if responsable:
        tareas = db.tareas_persona(responsable, solo_activas=solo_activas)
    elif estado == "VENCIDAS":
        tareas = db.tareas_vencidas()
    else:
        tareas = db.tareas_pendientes(semana=semana)

    return {"count": len(tareas), "tareas": tareas}


@app.get("/tareas/{tarea_id}")
async def detalle_tarea(tarea_id: int):
    """Detalle de una tarea por ID."""
    # Query directa ya que no tenemos un get_by_id dedicado
    import pyodbc
    try:
        from .config import SQL_CONN_STRING
    except ImportError:
        from config import SQL_CONN_STRING
    conn = pyodbc.connect(SQL_CONN_STRING, timeout=15)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, titulo, descripcion, responsable_nombre,
                   responsable_wa, deadline, prioridad, estado, area,
                   canal_entrega, resultado_esperado, notas_avance,
                   motivo_bloqueo, porcentaje_avance,
                   fecha_creacion, fecha_completada, semana_asignacion
            FROM omicronvt.dbo.tareas_equipo WHERE id = ?
        """, (tarea_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(404, "Tarea no encontrada")

        return {
            "id": row[0],
            "titulo": row[1],
            "descripcion": row[2],
            "responsable_nombre": row[3],
            "responsable_wa": row[4],
            "deadline": str(row[5]) if row[5] else None,
            "prioridad": row[6],
            "estado": row[7],
            "area": row[8],
            "canal_entrega": row[9],
            "resultado_esperado": row[10],
            "notas_avance": row[11],
            "motivo_bloqueo": row[12],
            "porcentaje_avance": row[13],
            "fecha_creacion": str(row[14]) if row[14] else None,
            "fecha_completada": str(row[15]) if row[15] else None,
            "semana_asignacion": row[16],
        }
    finally:
        conn.close()


@app.post("/tareas")
async def crear_tarea_api(tarea: TareaCreate):
    """Crea una tarea via API (sin pasar por WhatsApp)."""
    deadline = None
    if tarea.deadline:
        try:
            deadline = datetime.strptime(tarea.deadline, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, "Formato de fecha invalido. Usar YYYY-MM-DD")

    tarea_id = db.crear_tarea(
        titulo=tarea.titulo,
        responsable_nombre=tarea.responsable_nombre,
        responsable_wa=tarea.responsable_wa,
        deadline=deadline,
        prioridad=tarea.prioridad or "P1",
        area=tarea.area,
        canal_entrega=tarea.canal_entrega,
        resultado_esperado=tarea.resultado_esperado,
    )

    return {"ok": True, "tarea_id": tarea_id}


@app.patch("/tareas/{tarea_id}")
async def actualizar_tarea_api(tarea_id: int, update: TareaUpdate):
    """Actualiza el estado de una tarea via API."""
    if not update.estado:
        raise HTTPException(400, "Se requiere campo 'estado'")

    estados_validos = {"ASIGNADA", "EN_PROGRESO", "BLOQUEADA", "COMPLETA", "CANCELADA"}
    if update.estado not in estados_validos:
        raise HTTPException(400, f"Estado invalido. Opciones: {estados_validos}")

    ok = db.actualizar_estado(
        tarea_id=tarea_id,
        nuevo_estado=update.estado,
        notas=update.notas,
        porcentaje=update.porcentaje,
        motivo_bloqueo=update.motivo_bloqueo,
        autor="API",
    )

    if not ok:
        raise HTTPException(404, "Tarea no encontrada")

    return {"ok": True, "tarea_id": tarea_id, "nuevo_estado": update.estado}


@app.get("/resumen")
async def resumen(semana: Optional[str] = Query(None)):
    """Resumen semanal."""
    return db.resumen_semana(semana)


@app.post("/checkpoint")
async def disparar_checkpoint(dry_run: bool = Query(True)):
    """
    Dispara checkpoint miercoles manualmente.
    Usar dry_run=false para enviar realmente.
    """
    resultados = generar_checkpoint_miercoles(dry_run=dry_run)
    return {
        "tipo": "CHECKPOINT_MIE",
        "dry_run": dry_run,
        "enviados": sum(1 for r in resultados if r.get("enviado")),
        "total": len(resultados),
        "detalle": resultados,
    }


@app.post("/cierre")
async def disparar_cierre(dry_run: bool = Query(True)):
    """
    Dispara cierre viernes manualmente.
    Usar dry_run=false para enviar realmente.
    """
    resultado = generar_cierre_viernes(dry_run=dry_run)
    return {
        "tipo": "CIERRE_VIE",
        "dry_run": dry_run,
        "resultado": resultado,
    }
