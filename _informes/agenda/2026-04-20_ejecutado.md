# Ejecutado — Lunes 20 de abril 2026
> Agente ejecutor de agenda — run automático · Post-finde largo (Semana Santa)

---

## TAREAS ENCONTRADAS PARA HOY

| Tipo | Tarea | Fuente |
|------|-------|--------|
| Claude · lunes 8:30 | Generar plan semanal y diario | AGENDA.md — ciclo semanal |
| Claude · automático | Enviar plan diario por WA al equipo | AGENDA.md — lo que Claude ejecuta solo |
| Arrastre | Ejecutar UPDATE precios ERP (pendiente aprobación Fernando) | Arrastre 3 semanas |

---

## EJECUTADO

### ✅ Plan semanal 20-25 abr generado
**Archivo**: `_informes/agenda/2026-04-20_plan_semanal.md`

Contenido:
- Alertas financieras: $606M vencido + $42.9M esta semana
- 4 semanas de arrastre para Mati (Reebok/Vans/Saucony)
- 3 semanas de arrastre para Gonza+Emanuel (top 20 + fantasmas)
- Pendientes de aprobación de Fernando (precios liquidación, brief Fabiola)
- Auditoría GO DANCE Negro: 238 pares/$14.3M sin ventas 12 meses
- Reposición urgente: 100 CSR críticos / $10.9M

### ✅ Mensajes WA generados (listos para copiar)
**Archivo**: `_informes/agenda/2026-04-20_mensajes_wa.md`

Mensajes preparados para: Fernando, Mati, Gonza, Tamara, Mariana.

---

## NO PUDO EJECUTARSE

| Tarea | Razón | Acción requerida |
|-------|-------|-----------------|
| Enviar mensajes WA automáticos | Token Chatwoot expirado (401) — **tercer lunes consecutivo** | Fernando: generar nuevo token en chat.calzalindo.com.ar → Settings → Access Token → actualizar en `valijas/responder_agencias.py` (API_TOKEN) y `valijas/enviar_whatsapp_agencias.py` (CHATWOOT_TOKEN) |
| UPDATE precios ERP | Pendiente aprobación Fernando (arrastra 3 semanas) | Decir "OK ejecutar" en cualquier sesión |
| Sync precios TiendaNube | Depende del UPDATE anterior | Post-aprobación Fernando |

---

## PENDIENTES DE APROBACIÓN DE FERNANDO

| Entregable | Archivo | Semanas arrastradas | Qué hacer |
|-----------|---------|---------------------|-----------|
| Precios liquidación stock viejo | `_informes/agenda/2026-04-08_precios_liquidacion.md` | **3 semanas** | Decir "OK ejecutar" → Claude hace UPDATE ERP |
| Brief Fabiola redes | `_informes/agenda/2026-04-10_brief_fabiola.md` | **2 semanas** | Decir "OK Fabiola" → enviar a CM |

---

## CONTEXTO CLAVE — AL 20-ABR (post Semana Santa)

### Financiero
| Métrica | Valor |
|---------|-------|
| Deuda vencida proveedores | $606.5M (203 prov) |
| Pagos esta semana | $42.9M (22 prov) |
| Pagos +30d | $112.8M (30 prov) |
| Cobranza clientes | $4.75M (bajo riesgo) |
| Venta domingo 19-abr | $27K · 3 pares · 1 cliente |

### Arrastres equipo

| Persona | Tarea más crítica | Semanas |
|---------|-------------------|---------|
| **Mati** | Planillas Reebok/Vans/Saucony | 4 semanas 🔴 |
| **Mati** | Topper running | 3 semanas 🔴 |
| **Gonza** | Conteo 482 fantasmas | 3 semanas 🔴 |
| **Gonza** | Top 20 liquidación físico | 3 semanas 🔴 |
| **Tamara** | Incentivos y productividad | 1 semana 🟡 |
| **Mariana** | Precios (en progreso) | — |

---

## PRÓXIMOS HITOS AUTOMÁTICOS

| Fecha | Evento |
|-------|--------|
| **Mié 22-abr 8:30** | Checkpoint WA equipo (Claude genera) |
| **Vie 25-abr 17:00** | Cierre semanal automático (Claude genera) |

---

*Generado: 2026-04-20 08:30 (automático)*
