# Workflow del Comprador (Mati Rodriguez) -- Auditoria y Propuesta
> Fecha: 1 de abril de 2026
> Scope: Pipeline de notas de pedido + herramientas de decision + seguimiento

---

## 1. DIAGRAMA DEL WORKFLOW ACTUAL

```
DECISION DE COMPRA
==================

  [Ranking web2py]              [app_reposicion.py]
  rank_marcas (RC0001)          Streamlit en Mac
  rank_productos (RC0002)       quiebre + vel_real
  producto_curva (RC0003)       GMROI, Rotacion
       |                              |
       v                              v
  Mati mira el ranking      Mati analiza reposicion
  en el browser (111)        en Streamlit (Mac local)
       |                              |
       +----------+-------------------+
                  |
                  v
         DECISION MENTAL
    "Necesito X pares de marca Y"
                  |
     +------------+------------+
     |                         |
     v                         v
  OPCION A (manual)        OPCION B (app_pedido_auto.py)
  Arma Excel a mano        Streamlit en Mac
  con SKUs y cantidades     Analiza marca completa
     |                      Edita cantidades sugeridas
     v                      Boton INSERT
  paso5_parsear_excel       Boton ENVIAR email
  paso6_flujo_completo           |
  (CLI en servidor 111)          v
     |                      pedico2+pedico1 en produccion
     v
  pedico2+pedico1
  en produccion


SEGUIMIENTO
===========

  [reportes.pedidos()]          [app_pedido_auto.py]
  web2py en produccion (111)    tab Seguimiento (Mac)
  Dashboard con KPIs:           Log JSON local:
   - lineas pedidas/recibidas    - fecha, monto, pares
   - vencidas                    - email enviado?
   - antiguedad                  - confirmado?
   - por proveedor/industria
       |                              |
       v                              v
  Mati revisa cumplimiento     Mati marca "confirmado"
  en browser                   en la app

  (SIN CONEXION DIRECTA ENTRE AMBOS)


ENVIO AL PROVEEDOR
==================

  Opcion A: Email manual (copiar datos a mano)
  Opcion B: app_pedido_auto.py boton EMAIL (SMTP no configurado)
  Opcion C: WhatsApp manual (screenshot o texto pegado)
```

---

## 2. COMPONENTES AUDITADOS

### 2.1 Pipeline CLI (paso1 a paso6)

| Archivo | Funcion | Estado |
|---------|---------|--------|
| paso1_verificar_bd.py | Verifica conexion y estructura de tablas | OK, diagnostico |
| paso2_buscar_articulo.py | Busca articulo por codigo/descripcion/SAP, alta | OK, robusto |
| paso3_calcular_periodo.py | Calcula OI/PV o H1/H2 segun industria | OK, con tests |
| paso4_insertar_pedido.py | INSERT pedico2+pedico1 con routing empresa | OK, transaccional |
| paso5_parsear_excel.py | Lee Excel/CSV, normaliza columnas | OK, flexible |
| paso6_flujo_completo.py | Orquesta todo: parse + buscar + periodo + insert | OK, CLI |

**Observaciones del pipeline CLI:**
- Requiere ejecucion en terminal (no es self-service para Mati)
- paso6 tiene input() interactivo para alta de articulos nuevos
- No hay validacion de presupuesto antes de insertar
- No hay preview de monto total antes de confirmar
- El routing empresa se resuelve pero depende de config.py hardcodeado

### 2.2 app_pedido_auto.py (Streamlit)

**Funcionalidades:**
- Seleccion de proveedor (config.py + BD dinamica via proveedores_db.py)
- Analisis de marca completo: quiebre 12 meses + estacionalidad + vel_real
- Pedido sugerido editable (data_editor por producto/talle)
- Boton INSERT en ERP (usa paso4)
- Boton ENVIAR EMAIL (SMTP no configurado)
- Tab de seguimiento con log JSON local
- Cobertura configurable (1-6 meses)

**Estado:** Funcional en Mac, NO requiere deploy al 111.

### 2.3 Web2py: reportes.pedidos()

**Funcionalidades:**
- Dashboard con KPIs: pedidos, lineas, pares pedidos/recibidos/pendientes, monto
- Vista por proveedor agrupada con marcas, industria, % cumplimiento
- Alertas de vencimiento (VENCIDO)
- Antiguedad de pedidos por rangos
- Top 20 vencidas
- Filtros por industria, proveedor, estado
- Auto-sync cada 10 min via sp_sync_pedidos

**Dependencia:** Tabla pedidos_cumplimiento_cache en omicronvt (materializada por SP).

### 2.4 Web2py: ranking_consolidado

**Funcionalidades:**
- RC0001 rank_marcas: ranking con vel_real, factor_quiebre, alerta SUB-COMPRADO
- RC0002 rank_productos: drill-down por marca con quiebre por CSR
- RC0003 producto_curva: detalle por talle, vel_ajustada, cobertura
- RC0004 producto_pedido: sugerencia de pedido para 1 CSR
- RC0005 marca_pedido: pedido completo para una marca
- RC0006 api_quiebre: API JSON

**Nota critica:** RC0004 y RC0005 generan sugerencias pero NO tienen boton para materializar el pedido. Solo muestran datos.

### 2.5 Calce financiero

- Controller existe pero NO tiene funcion de presupuesto disponible por industria.
- Cruza pedidos + recupero + compras/stock a nivel de industria.
- No hay forma de que Mati vea cuanto presupuesto queda antes de armar un pedido.

---

## 3. FRICCIONES IDENTIFICADAS

### CRITICAS (impacto alto, frecuencia alta)

| # | Friccion | Descripcion | Impacto |
|---|----------|-------------|---------|
| F1 | Dos herramientas desconectadas para decision | Mati debe alternar entre web2py (ranking en 111) y Streamlit (reposicion en Mac) para decidir que comprar. No hay flujo unificado. | Duplicacion de esfuerzo, riesgo de inconsistencia |
| F2 | Sin presupuesto visible antes de comprar | No existe dashboard que muestre "presupuesto disponible por industria" antes de armar un pedido. Mati compra sin saber si se pasa del budget. | Riesgo financiero, re-trabajo si se pasa |
| F3 | Gap ranking -> pedido en web2py | RC0004/RC0005 calculan sugerencia de pedido con quiebre pero NO tienen boton INSERT ni envio. Es solo lectura. Mati ve la sugerencia y tiene que pasar los datos a mano. | Friccion principal, error de transcripcion |

### ALTAS (impacto medio-alto)

| # | Friccion | Descripcion | Impacto |
|---|----------|-------------|---------|
| F4 | Email al proveedor no funciona | SMTP en app_pedido_auto.py tiene credenciales placeholder (APP_PASSWORD). Mati tiene que copiar datos y pegar en email/WA manualmente. | Perdida de tiempo, 5-10 min por pedido |
| F5 | Log de seguimiento duplicado | app_pedido_auto.py usa JSON local en Mac. reportes.pedidos() usa tabla en SQL Server. Son sistemas independientes sin cruce. | Seguimiento inconsistente |
| F6 | Flujo CLI requiere developer | paso6_flujo_completo.py es CLI puro. Mati no puede usarlo sin asistencia tecnica. Solo app_pedido_auto.py es self-service. | Dependencia de Fernando/dev |

### MEDIAS (impacto medio)

| # | Friccion | Descripcion | Impacto |
|---|----------|-------------|---------|
| F7 | Sin validacion de duplicados | No hay check si ya existe un pedido activo al mismo proveedor por los mismos articulos. Riesgo de doble pedido. | Stock excesivo, capital atado |
| F8 | Sin confirmacion de proveedor integrada | La confirmacion del proveedor se maneja off-system (email, WA, llamada). El "confirmado" en el log es manual. | Falta trazabilidad |
| F9 | vel_real_articulo no deployada en produccion | La tabla materializada no existe en 111. Web2py hace fallback a calculo on-the-fly (lento) o devuelve 0. | Ranking incompleto en produccion |
| F10 | Proveedores no configurados = pricing ciego | Solo 8 proveedores en config.py. Para los demas, proveedores_db.py intenta inferir pero sin utilidades definidas. | Precios incorrectos en pedido |

---

## 4. WORKFLOW PROPUESTO

```
WORKFLOW MEJORADO (propuesta)
=============================

  PASO 1: DIAGNOSTICO (donde Mati arranca)
  =========================================

  [web2py: ranking_consolidado/rank_marcas]
     Ranking con vel_real + factor_quiebre + alerta SUB-COMPRADO
     + NUEVO: columna "Presupuesto disp." por industria
     + NUEVO: indicador visual de marcas con pedido activo
           |
           v
     Click en marca con quiebre alto
           |
           v
  [web2py: rank_productos]
     Productos ordenados por vel_real, con stock y quiebre
     + NUEVO: boton "Armar pedido" por marca (link a marca_pedido)
           |
           v

  PASO 2: ARMADO DEL PEDIDO (self-service)
  =========================================

  [web2py: marca_pedido MEJORADO]   o   [app_pedido_auto.py]
     Sugerencia por talle                 Streamlit (ya funciona)
     + NUEVO: tabla editable (JS)         Tabla editable
     + NUEVO: validacion presupuesto      Sin presupuesto (por ahora)
     + NUEVO: check duplicados            Sin check duplicados
     + NUEVO: boton CONFIRMAR PEDIDO
           |
           v

  PASO 3: INSERT + ENVIO (un click)
  ==================================

     Boton INSERT -> paso4_insertar_pedido()
     + NUEVO: genera PDF/HTML de nota de pedido
     + NUEVO: boton ENVIAR (email O WhatsApp API)
     + NUEVO: log en SQL (no JSON local)
           |
           v

  PASO 4: SEGUIMIENTO UNIFICADO
  ==============================

  [web2py: reportes/pedidos MEJORADO]
     Dashboard actual +
     + NUEVO: columna "email enviado", "confirmado por proveedor"
     + NUEVO: alerta "sin respuesta > 3 dias"
     + NUEVO: link directo al detalle del pedido
```

---

## 5. PLAN DE IMPLEMENTACION PRIORIZADO

### Fase 1: Quick wins (1-2 dias cada uno)

| # | Mejora | Que hacer | Esfuerzo | Impacto | Resuelve |
|---|--------|-----------|----------|---------|----------|
| M1 | Deploy vel_real_articulo | Ejecutar vel_real_articulo_20260321.sql en 111. Ya esta generado. | 0.5 dia | Alto | F9 |
| M2 | Configurar SMTP real | Configurar credenciales email en app_pedido_auto.py (Gmail app password o SMTP propio) | 0.5 dia | Alto | F4 |
| M3 | Boton "Armar pedido" en rank_productos | En RC0002, agregar link a marca_pedido/{cod_marca}?cobertura=3 como boton visible | 1 dia | Alto | F3 parcial |
| M4 | Presupuesto simple en ranking | Query de compras acumuladas vs presupuesto por industria (tabla manual o agrupador). Mostrar como KPI en rank_marcas. | 1.5 dias | Alto | F2 parcial |

### Fase 2: Integracion (3-5 dias)

| # | Mejora | Que hacer | Esfuerzo | Impacto | Resuelve |
|---|--------|-----------|----------|---------|----------|
| M5 | INSERT desde web2py marca_pedido | Agregar form editable + boton INSERT en RC0005. Requiere POST handler que llame paso4 (via API o pyodbc directo). | 3 dias | Critico | F3, F6 |
| M6 | Log unificado en SQL | Crear tabla pedidos_log en omicronvt con campos: numero, proveedor, fecha, pares, monto, email_enviado, confirmado, usuario. Migrar log JSON. Ambos sistemas escriben ahi. | 2 dias | Alto | F5 |
| M7 | Check duplicados pre-insert | En paso4 o en UI, verificar si existe pedido activo (estado='V') al mismo proveedor con articulos solapados. Warning si >50% overlap. | 1 dia | Medio | F7 |

### Fase 3: Experiencia completa (5-10 dias)

| # | Mejora | Que hacer | Esfuerzo | Impacto | Resuelve |
|---|--------|-----------|----------|---------|----------|
| M8 | Generador PDF nota de pedido | Template HTML/PDF con logo, detalle por talle, condiciones comerciales, numero de pedido. Adjuntar al email. | 3 dias | Medio | F4 mejora |
| M9 | WhatsApp API | Integrar Chatwoot o WA Business API para enviar nota al proveedor. Mati ya usa WA. | 3 dias | Medio | F4 alternativa |
| M10 | Tracking de confirmacion | En reportes/pedidos, agregar estado "Enviado", "Confirmado", "Rechazado". Alerta si >3 dias sin respuesta. Input manual o via respuesta email. | 2 dias | Medio | F8 |
| M11 | Tabla presupuesto por industria | Tabla editable en web2py con presupuesto trimestral por industria. Calce automatico contra compras reales + pedidos pendientes. Semaforo rojo/amarillo/verde. | 5 dias | Alto | F2 completo |

### Fase 4: Automatizacion (opcional, 5+ dias)

| # | Mejora | Que hacer | Esfuerzo | Impacto | Resuelve |
|---|--------|-----------|----------|---------|----------|
| M12 | Pedido sugerido automatico | Scheduled task que analiza quiebre cada semana, genera borrador de pedido para marcas con cobertura < 1 mes. Notifica a Mati por WA. | 5 dias | Medio | Proactivo |
| M13 | Integracion portal proveedor | Si el proveedor tiene portal (ej: Alpargatas B2B), automatizar carga de pedido via scraping o API. | Variable | Bajo | Nicho |

---

## 6. RESUMEN EJECUTIVO

**Estado actual:** El pipeline de notas de pedido esta tecnicamcnte completo (paso1-6 + app_pedido_auto.py). El problema principal NO es la falta de funcionalidad sino la **fragmentacion del flujo**:

1. La decision de compra se toma en web2py (ranking + quiebre) pero la accion de pedido se ejecuta en Streamlit (app_pedido_auto) o CLI (paso6). No hay puente directo.

2. El ranking en web2py ya calcula sugerencias de pedido (RC0004, RC0005) pero son solo lectura. No hay boton para materializar la compra.

3. El seguimiento esta partido entre un JSON local (Streamlit) y una tabla SQL (web2py). Mati no tiene una vista unica de todo.

**Recomendacion:** Empezar por M1 + M2 + M3 (2 dias total) que son quick wins sin riesgo. Luego M5 (INSERT desde web2py) que es la mejora de mayor impacto -- convierte el ranking en una herramienta de compra end-to-end.

**Meta final:** Que Mati pueda, desde un solo browser apuntando al servidor 111:
1. Ver el ranking con quiebre y presupuesto
2. Clickear "Armar pedido" en una marca
3. Editar cantidades sugeridas
4. Insertar en el ERP con un boton
5. Enviar al proveedor con otro boton
6. Hacer seguimiento en el mismo dashboard

Todo en web2py, sin depender de Streamlit en Mac ni CLI en terminal.

---

## 7. NOTAS TECNICAS

- **vel_real_articulo:** SQL ya generado (2400 INSERTs), verificado que la tabla NO existe en produccion. Es bloqueante para que el ranking muestre datos de quiebre reales.
- **Presupuesto:** No existe tabla de presupuesto. Opciones: (a) tabla manual en omicronvt, (b) derivar de historico de compras + % crecimiento objetivo.
- **SMTP:** Configurar con Gmail App Password o con servidor propio. La funcion enviar_email_proveedor() ya esta escrita, solo faltan credenciales.
- **SQL Server 2012:** Recordar que NO soporta TRY_CAST. Cualquier query nueva debe usar ISNUMERIC + CAST.
- **INSERT en web2py:** Requiere conexion de escritura desde web2py al SQL Server. Actualmente web2py usa DAL read-only en algunos modelos. Evaluar si usar pyodbc directo o un endpoint API en el 111.
