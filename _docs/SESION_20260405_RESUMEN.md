# SESION 5 ABRIL 2026 — RESUMEN COMPLETO

## Lo que se construyo

### 1. Task Manager (COMPLETO)
- `AGENDA.md` con 27 tareas, 8 personas, metodologia delegacion
- `_sync_tools/task_manager/meta_whatsapp.py` — envio WA via Meta API
- `_sync_tools/task_manager/task_notifier.py` — lee agenda, genera mensajes por persona
- `_sync_tools/task_manager/webhook_responder.py` — bot que responde "tareas"
- Tarea programada matutina L-V 8:30 (plan diario + WA)
- Tarea programada viernes 17:00 (cierre semanal)
- Telefonos: Fer 672330, Mati 508491, Mariana 317470, Gonza 317553, Ema 317342, Tamara 677067, Guille 610216, Lucia 637251
- Contactos Chatwoot: Mariana #465, Gonza #466, Emanuel #467, Lucia #468, Mati #484

### 2. Deploy web2py al 111
- **Productividad**: dashboard, vendedor, estacionalidad, incentivos, ticket_historico
- **Nuevo: Comparativo Sucursales** con grafico Highcharts
- **Nuevo: Alertas vendedores** bajo rendimiento (API JSON)
- **Nuevo: Config bandas** (admin, lee de tabla si existe)
- **BCG Matrix**: nombres de marca (no codigos), grafico centrado sin outliers, filtros tabla sincronizan con grafico
- **Stock Muerto**: formato zapatero (curva talles), agrupado por modelo (sin-4), marca/rubro con nombre
- **Proveedores ROI**: sin cambios (ya tenia nombres)
- **db_access.py**: permisos nuevos (sucursales, alertas, config, freelance_modelo, viajante_admin, salud_negocio)
- **menu.py**: agregados Comparativo Sucursales, Ticket Historico. Pestaña "UA:2-4-26"
- **APIs con auth**: api_productividad y api_estacionalidad ahora requieren login

### 3. Usuarios / Auth
- Lucia Giordano creada en auth_user #557 (SQL Server 112, clz_ventas_sql)
- Rol finanzas = informes_gerencia
- l@calzalindo.com.ar / lucia2026
- MySQL 109 pendiente (MCP mysql-auth configurado en .mcp.json pero no probado)
- Maitena Spessot (auth #411) ya tiene rol rrhh — acceso productividad OK

### 4. MCPs configurados
- `sql-replica` → 111 msgestionC (ya existia)
- `clz-ventas` → 112 clz_ventas_sql (NUEVO, user meta106)
- `mysql-auth` → 109 clz_ventas_mysql (NUEVO, configurado no probado)

### 5. Stock Muerto — Sistema completo
- `_scripts_oneshot/revaluar_stock_muerto.py` — motor revaluacion con piramide precios
- Piramide: 1243 segmentos marca+rubro con precios de mercado
- BCG: 341 marcas clasificadas
- Filtros: excluye anomalias >$500K, recientes <6m, fantasmas >5 años
- Clasificacion ciclo de vida: 4771 LIQUIDAR / 578 REDUCIR / 8 MANTENER
- 482 articulos FANTASMA detectados (>5 años sin compra, probablemente no existen)
- Excel: `_informes/STOCK_MUERTO_CLASIFICADO.xlsx` (3 pestañas)
- Excel: `_informes/TOPPER_liquidacion.xlsx` (formato zapatero por modelo)
- JSON: `_informes/stock_muerto_revaluado.json`, `stock_muerto_clasificado.json`

### 6. Modelo Ciclo de Vida Productos
- 5 indicadores: volumen, clientes unicos, sucursales, ticket, estacionalidad
- Caso Profesional TOPPER: DECLIVE AVANZADO (no muerto). -60% vol, -65% clientes en 3 años
- Duplicados detectados: 89600 "PROFESIONAL + BLANCO" vs "PROFESIONAL BLANCO" = mismo producto
- Guardado en memoria: feedback_ciclo_vida_productos.md

### 7. Perfiles de puesto guardados
- Gonzalo/Emanuel: Asistente Deposito Jr (carga, conteo, precios segun indicacion)
- Mariana: Asistente Compras Jr (reposicion, faltantes, precios, analisis)
- Mati: Compras Deportes Sr (pipeline ERP, proveedores, Claude)
- Guardado en memoria: reference_perfiles_puesto.md

### 8. Tareas programadas activas
- `revision-matutina`: L-V 8:30, plan diario + WA equipo
- `revision-viernes`: vie 17:00, cierre semanal
- `pricing-elasticidad-analisis`: dom 6-abr 8:00, 50 marcas elasticidad
- `pricing-macro-research`: dom 6-abr 7:30, macro Argentina

## Archivos creados/modificados

### Nuevos
- `_sync_tools/task_manager/meta_whatsapp.py`
- `_sync_tools/task_manager/task_notifier.py`
- `_sync_tools/task_manager/webhook_responder.py`
- `_sync_tools/task_manager/TEMPLATE_META.md`
- `_scripts_oneshot/revaluar_stock_muerto.py`
- `_informes/STOCK_MUERTO_CLASIFICADO.xlsx`
- `_informes/TOPPER_liquidacion.xlsx`
- `_informes/stock_muerto_revaluado.csv/json`
- `_informes/stock_muerto_clasificado.json`
- `_informes/calzalindo_informes_DEPLOY/views/informes_productividad/sucursales.html`
- `_informes/calzalindo_informes_DEPLOY/views/inteligencia_comercial/stock_muerto.html` (reescrito zapatero)
- `AGENDA.md` (reescrito completo)

### Modificados
- `_informes/calzalindo_informes_DEPLOY/controllers/informes_productividad.py` (bandas config, sucursales, alertas, config, auth APIs)
- `_informes/calzalindo_informes_DEPLOY/controllers/inteligencia_comercial.py` (nombres marca, piramide, zapatero, cache keys)
- `_informes/calzalindo_informes_DEPLOY/models/db_access.py` (permisos nuevos)
- `_informes/calzalindo_informes_DEPLOY/views/inteligencia_comercial/bcg_matrix.html` (nombres, filtros sync, outliers)
- `_informes/calzalindo_informes_DEPLOY/views/informes_productividad/dashboard.html` (sin columna Cod)
- `_informes/calzalindo_informes_DEPLOY/views/informes_productividad/vendedor.html` (sin codigo en titulo)
- `.mcp.json` (agregados clz-ventas y mysql-auth)

### Memoria (persistente entre sesiones)
- `feedback_formato_zapatero.md` — curva talles en todas las vistas
- `feedback_ciclo_vida_productos.md` — 5 indicadores muerte producto
- `reference_perfiles_puesto.md` — perfiles Gonza, Ema, Mariana, Mati, Tamara, Fabiola
- `project_equipo.md` — actualizado con telefonos y Chatwoot IDs
- `project_agenda_sistema.md` — actualizado con delegacion v2
- `project_pricing_strategy.md` — brief elasticidad + yield + discriminacion

## Pendiente para proxima sesion

1. **LUNES 7**: Revisar resultados elasticidad + macro (tareas programadas)
2. **LUNES 7**: Fernando aprueba top 20 liquidacion del Excel
3. **LUNES 7**: Aprobar template Meta tareas_dia
4. **SEMANA**: Construir sistema de markup automatico (reemplazar a Mariana)
5. **SEMANA**: Crear usuario Lucia en MySQL 109
6. **SEMANA**: Ejecutar liquidacion (UPDATE ERP + sync TN + brief Fabiola)
7. **ABRIL**: Estrategia pricing por marca con elasticidad
8. **ABRIL**: Yield management / discriminacion precio por cliente en POS
