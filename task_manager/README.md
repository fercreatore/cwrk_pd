# Task Manager — Chatbot WhatsApp H4/CALZALINDO

Sistema de gestion de tareas del equipo via WhatsApp, usando Chatwoot como middleware.

## Arquitectura

```
WhatsApp (equipo)
    |
    v
Chatwoot (chat.calzalindo.com.ar)
    |  webhook
    v
FastAPI (192.168.2.112:8002)
    |
    v
SQL Server (omicronvt.dbo.tareas_equipo)
```

## Archivos

| Archivo | Funcion |
|---------|---------|
| `schema.sql` | CREATE TABLE + indices. Ejecutar en 111 |
| `config.py` | Equipo, tokens, conexion SQL |
| `parser.py` | Parser de mensajes WA (regex, espanol argentino) |
| `chatwoot_client.py` | Wrapper para enviar mensajes via Chatwoot API |
| `chatwoot_webhook.py` | Logica de procesamiento de mensajes entrantes |
| `db.py` | Capa de acceso a datos (INSERT/UPDATE/SELECT) |
| `scheduler.py` | Checkpoint miercoles + cierre viernes |
| `main.py` | FastAPI app con todos los endpoints |

## Setup

### 1. Crear tablas

Ejecutar `schema.sql` en SQL Server 111 (base omicronvt).

### 2. Configurar webhook en Chatwoot

En chat.calzalindo.com.ar:
- Settings > Integrations > Webhooks
- URL: `http://192.168.2.112:8002/webhook/chatwoot`
- Events: `message_created`

### 3. Correr el servidor

```bash
# En 112
cd C:\cowork_pedidos
C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe -m uvicorn task_manager.main:app --host 0.0.0.0 --port 8002

# Dev local
uvicorn task_manager.main:app --host 0.0.0.0 --port 8002 --reload
```

### 4. Dependencias

```
fastapi
uvicorn
pyodbc
pydantic
```

## Uso via WhatsApp

### Fernando crea tarea (formato formal)

```
Mati: [TAREA] Stock Reebok [PARA] mie 2-abr [QUE] Planilla talles/cantidades [ENTREGAR] Excel por WA
```

### Fernando crea tarea (formato flexible)

```
Mati: Stock Reebok para miercoles
```

### Responsable reporta avance

```
listo          -> COMPLETA
70%            -> EN_PROGRESO (70%)
avanzando      -> EN_PROGRESO
bloqueado: falta precio -> BLOQUEADA
```

### Consultas

```
estado mati     -> tareas de Mati
pendientes      -> todas las pendientes
vencidas        -> tareas pasadas de deadline
mis tareas      -> tareas del remitente
resumen         -> resumen semanal
```

## API REST

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| GET | `/health` | Healthcheck |
| POST | `/webhook/chatwoot` | Webhook Chatwoot |
| GET | `/tareas` | Listar tareas (filtros: responsable, estado, semana) |
| GET | `/tareas/{id}` | Detalle de tarea |
| POST | `/tareas` | Crear tarea via API |
| PATCH | `/tareas/{id}` | Actualizar estado |
| GET | `/resumen` | Resumen semanal |
| POST | `/checkpoint?dry_run=true` | Disparar checkpoint mie |
| POST | `/cierre?dry_run=true` | Disparar cierre vie |

## Checkpoints automaticos

Para automatizar los checkpoints, agregar cron en el servidor 112:

```
# Miercoles 10:00 — checkpoint mitad de semana
0 10 * * 3 curl -X POST http://localhost:8002/checkpoint?dry_run=false

# Viernes 17:00 — cierre semanal
0 17 * * 5 curl -X POST http://localhost:8002/cierre?dry_run=false
```
