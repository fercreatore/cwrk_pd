# SPEC: Task Manager via Chatbot WhatsApp
> Fecha: 1 de abril de 2026
> Autor: Claude + Fernando Calaianov
> Estado: Implementado, pendiente deploy

---

## 1. OBJETIVO

Automatizar la gestion de tareas del equipo H4/CALZALINDO (8 personas) reemplazando el sistema manual basado en AGENDA.md + mensajes WA individuales. El chatbot recibe mensajes por WhatsApp via Chatwoot, los parsea, y gestiona tareas en SQL Server.

---

## 2. ARQUITECTURA

```
WhatsApp Cloud API (Meta)
        |
        v
Chatwoot (chat.calzalindo.com.ar, account 3, inbox 9)
        |  webhook POST /webhook/chatwoot
        v
FastAPI (192.168.2.112:8002)  <-- task_manager/main.py
        |
        v
SQL Server 111 (omicronvt.dbo.tareas_equipo + tareas_historial)
```

### Componentes

| Componente | Archivo | Funcion |
|-----------|---------|---------|
| Schema SQL | `task_manager/schema.sql` | 3 tablas: tareas_equipo, tareas_historial, tareas_checkpoint_log |
| Config | `task_manager/config.py` | Equipo (8 personas), tokens, conexion SQL |
| Parser | `task_manager/parser.py` | Regex para espanol argentino, clasifica mensajes en 4 tipos |
| DB | `task_manager/db.py` | Capa de datos: CRUD tareas + queries |
| Chatwoot Client | `task_manager/chatwoot_client.py` | Envio de mensajes via API Chatwoot |
| Webhook | `task_manager/chatwoot_webhook.py` | Logica de procesamiento de mensajes entrantes |
| Scheduler | `task_manager/scheduler.py` | Checkpoint miercoles + cierre viernes + notificaciones |
| App | `task_manager/main.py` | FastAPI con 9 endpoints |

---

## 3. SCHEMA SQL

### tareas_equipo (tabla principal)
- `id` INT IDENTITY PK
- `titulo` VARCHAR(200) NOT NULL
- `descripcion` VARCHAR(MAX)
- `responsable_nombre` VARCHAR(100) NOT NULL
- `responsable_wa` VARCHAR(20) -- telefono
- `responsable_chatwoot_id` INT
- `asignado_por` VARCHAR(100) DEFAULT 'Fernando'
- `fecha_creacion` DATETIME DEFAULT GETDATE()
- `deadline` DATE
- `prioridad` VARCHAR(5) CHECK (P0, P1, P2, P3)
- `estado` VARCHAR(20) CHECK (ASIGNADA, EN_PROGRESO, BLOQUEADA, COMPLETA, CANCELADA)
- `area` VARCHAR(50)
- `canal_entrega` VARCHAR(100)
- `resultado_esperado` VARCHAR(MAX)
- `notas_avance` VARCHAR(MAX) -- append de updates con timestamp
- `motivo_bloqueo` VARCHAR(500)
- `porcentaje_avance` INT CHECK (0-100)
- `fecha_ultima_actualizacion` DATETIME
- `fecha_completada` DATETIME
- `semana_asignacion` VARCHAR(20) -- '2026-W14'
- `mensaje_original` VARCHAR(MAX) -- auditoria

Mejoras sobre el schema propuesto:
- Agregado `porcentaje_avance` para tracking granular
- Agregado `motivo_bloqueo` separado de notas
- Agregado `mensaje_original` para debug
- Agregada tabla `tareas_historial` para log de cambios
- Agregada tabla `tareas_checkpoint_log` para auditar envios automaticos

### tareas_historial (log de cambios)
- `id` INT IDENTITY PK
- `tarea_id` INT (FK logica)
- `estado_anterior` / `estado_nuevo` VARCHAR(20)
- `notas` VARCHAR(500)
- `autor` VARCHAR(100)
- `fecha` DATETIME

### tareas_checkpoint_log (auditoria de envios)
- `id` INT IDENTITY PK
- `tipo` VARCHAR(20) -- CHECKPOINT_MIE, CIERRE_VIE
- `semana` VARCHAR(20)
- `destinatario` VARCHAR(100)
- `mensaje_enviado` VARCHAR(MAX)
- `fecha` DATETIME
- `ok` BIT

---

## 4. FLUJOS

### A) Crear tarea

Fernando envia por WA:
```
Mati: [TAREA] Stock Reebok [PARA] mie 2-abr [QUE] Planilla talles/cantidades [ENTREGAR] Excel por WA
```

1. Chatwoot recibe mensaje -> webhook a FastAPI
2. Parser detecta tipo=CREAR_TAREA, extrae campos
3. Verifica que remitente es admin (Fernando)
4. INSERT en tareas_equipo
5. Confirma a Fernando: "Tarea #123 creada y asignada a Mati Rodriguez"
6. Notifica a Mati: "Nueva tarea: Stock Reebok..."

Tambien acepta formato flexible:
```
Mati: Stock Reebok para miercoles
```

### B) Update de estado

Responsable responde:
- "listo" / "hecho" / "terminado" / "ya esta" / "100%" -> COMPLETA
- "70%" / "avance 50%" / "voy por el 80%" -> EN_PROGRESO con porcentaje
- "avanzando" / "estoy en eso" / "voy bien" -> EN_PROGRESO generico
- "bloqueado: falta precio" / "no puedo: necesito datos" -> BLOQUEADA

1. Parser detecta tipo=UPDATE_ESTADO
2. Busca persona por telefono del remitente
3. Busca la tarea activa mas urgente de esa persona
4. UPDATE estado + log en historial
5. Confirma al remitente
6. Si COMPLETA o BLOQUEADA -> notifica a Fernando

### C) Consultas

- "estado mati" -> tareas de Mati
- "pendientes" -> todas las no completadas
- "vencidas" -> pasadas de deadline
- "mis tareas" -> tareas del remitente
- "resumen" -> resumen semanal

### D) Checkpoint miercoles (automatico o manual)

POST /checkpoint?dry_run=false (cron cada mie 10:00)

Para cada persona con tareas activas:
```
Checkpoint mitad de semana

Hola Mati, tus tareas esta semana:

1. hourglass Stock Reebok (mie 02/04)
2. runner Vans pedido (jue 03/04)

Contesta con:
- listo = terminada
- 70% = avance parcial
- bloqueado: [motivo] = trabada
```

### E) Cierre viernes (automatico o manual)

POST /cierre?dry_run=false (cron cada vie 17:00)

Envia a Fernando:
```
Cierre semana 2026-W14

Completadas: 8/12 (67%)
Bloqueadas: 2
Pendientes: 2

Detalle por persona:
check Mati Rodriguez: 4/6 completadas
clipboard Gonzalo Bernardi: 0/1 completadas
   warning 1 bloqueadas
```

---

## 5. PARSER — VARIANTES SOPORTADAS

### Completado
listo, hecho, terminado, ya esta, completado, done, ready, ok, entregado, ya lo hice, ya mande, ya envie, 100%

### En progreso
avance X%, voy por el X%, estoy en X%, progreso X%, llevo X%, X% (solo numero), avanzando, estoy en eso, voy bien, arrancando, empece, casi listo

### Bloqueado
bloqueado, trabado, no puedo, falta X, necesito X, dependo de X, esperando X, no tengo X

### Consultas
estado X, como va X, que tiene X, tareas de X, pendientes, vencidas, atrasadas, resumen, dashboard, mis tareas, que tengo, lo mio

### Crear tarea
Formato formal: `Nombre: [TAREA] X [PARA] Y [QUE] Z [ENTREGAR] W`
Formato flex: `Nombre: descripcion para dia`

### Fechas soportadas
hoy, manana, mie 2-abr, miercoles 2 de abril, vie, viernes, 2/4, abril

---

## 6. API REST

| Metodo | Endpoint | Auth | Descripcion |
|--------|----------|------|-------------|
| GET | /health | - | Healthcheck |
| POST | /webhook/chatwoot | Chatwoot | Webhook mensajes entrantes |
| GET | /tareas | - | Lista con filtros (responsable, estado, semana) |
| GET | /tareas/{id} | - | Detalle tarea |
| POST | /tareas | - | Crear tarea via API |
| PATCH | /tareas/{id} | - | Actualizar estado via API |
| GET | /resumen | - | Resumen semanal |
| POST | /checkpoint | - | Disparar checkpoint (dry_run=true default) |
| POST | /cierre | - | Disparar cierre (dry_run=true default) |

---

## 7. DEPLOY

### Paso 1: Ejecutar schema.sql en 111
```sql
-- En SQL Server Management Studio o sqlcmd
USE omicronvt;
-- Copiar y ejecutar schema.sql
```

### Paso 2: Deploy codigo al 112
```bash
cd ~/Desktop/cowork_pedidos/_sync_tools
# Agregar task_manager/ al deploy.sh o copiar manualmente
scp -r ../task_manager administrador@192.168.2.112:C:/cowork_pedidos/task_manager/
```

### Paso 3: Instalar dependencias en 112
```bash
C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe -m pip install fastapi uvicorn pyodbc pydantic
```

### Paso 4: Correr servidor
```bash
C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe -m uvicorn task_manager.main:app --host 0.0.0.0 --port 8002
```

### Paso 5: Configurar webhook Chatwoot
- chat.calzalindo.com.ar > Settings > Integrations > Webhooks
- URL: http://192.168.2.112:8002/webhook/chatwoot
- Events: message_created

### Paso 6: Configurar cron checkpoints
```
# En 112 (Task Scheduler de Windows o cron WSL)
# Miercoles 10:00
0 10 * * 3 curl -X POST http://localhost:8002/checkpoint?dry_run=false
# Viernes 17:00
0 17 * * 5 curl -X POST http://localhost:8002/cierre?dry_run=false
```

---

## 8. CONEXION CON SISTEMA EXISTENTE

- **AGENDA.md**: Este sistema reemplaza la gestion manual. AGENDA.md pasa a ser un documento de referencia/resumen, no la fuente de verdad.
- **Chatwoot**: Usa la misma instancia y inbox que whatsapp_catalogo.py (inbox 9, account 3).
- **SQL Server**: Tablas nuevas en omicronvt (mismo patron que vendedor_freelance).
- **FastAPI**: Puerto 8002, convive con freelance en 8001.
- **Deploy**: Usar deploy.sh existente o copiar manualmente.

---

## 9. LIMITACIONES Y MEJORAS FUTURAS

### Limitaciones actuales
- Si una persona tiene multiples tareas activas y responde "listo", se marca la mas urgente (por prioridad y deadline). No hay forma de especificar cual.
- No hay autenticacion en los endpoints REST (solo webhook tiene validacion de Chatwoot).
- El parser es regex puro, no usa NLP. Mensajes ambiguos se clasifican como DESCONOCIDO.

### Mejoras posibles
- **Seleccion de tarea**: Agregar "listo #123" para especificar tarea por ID
- **Recordatorios**: Envio automatico 24hs antes del deadline
- **Dashboard web**: Pagina HTML con kanban visual (integrar en web2py o FastAPI)
- **Integracion con AGENDA.md**: Auto-generar AGENDA.md desde la DB cada semana
- **Metricas**: Tiempo promedio de completado, % cumplimiento por persona
- **NLP avanzado**: Usar LLM para parseo de mensajes ambiguos
