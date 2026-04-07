# PLAN DE ENVÍO MASIVO — OUTLET CALZALINDO ABRIL 2026

## ESTADO DE LA CUENTA WHATSAPP

| Campo | Valor |
|-------|-------|
| Número | +54 9 3462 53-1170 |
| WABA ID | 2155048721625121 |
| Phone Number ID | 1024637650727570 |
| Quality Rating | GREEN |
| Verified Name | Calzalindo |
| Template | `outlet_calzalindo_abril` (APPROVED) |

### 3 números en la WABA (todos GREEN)
- 7436 (chatbot negocio — NO TOCAR)
- 1170 (campañas — USAR ESTE)
- 2031 (n8n legacy)

---

## REGLAS META WHATSAPP BUSINESS API

### Tiers de envío (límite = conversaciones nuevas únicas en 24hs)

| Tier | Límite diario | Cómo subir |
|------|--------------|------------|
| 0 | 250 | Verificar negocio en Meta Business |
| 1 | 1,000 | Usar >50% del límite en 7 días + quality GREEN |
| 2 | 10,000 | Idem, Meta evalúa cada 6hs |
| 3 | 100,000 | Idem |
| 4 | Ilimitado | Enterprise |

**Calzalindo probablemente está en Tier 1 (1,000/día) o Tier 2 (10,000/día).**
No hay forma de consultarlo directo por API. Asumimos Tier 1 (peor caso).

### Reglas para NO ser bloqueado
1. **No enviar más de 1,000 conversaciones nuevas por día** (Tier 1)
2. **Mantener quality GREEN**: si muchos bloquean o reportan spam → baja a YELLOW → RED → ban
3. **Portfolio Pacing (2026)**: Meta frena automáticamente si detecta mala señal. No podemos evitarlo, pero sí mitigarlo con buen contenido
4. **Rate limit técnico**: 80 msg/segundo (no es problema para nosotros)

---

## ESTRATEGIA DE ENVÍO: WARM-UP EN 5 DÍAS

### Objetivo: llegar a 34,389 contactos sin ban

No podemos mandar 34K de golpe. Tenemos que hacer warm-up para subir de tier.

### Calendario

| Día | Fecha | Contactos | Acumulado | Horario | Segmento |
|-----|-------|-----------|-----------|---------|----------|
| 1 | Sáb 5/4 | 500 | 500 | 10:00-12:00 | VT ciudad (3462) más recientes |
| 2 | Dom 6/4 | 500 | 1,000 | 10:00-12:00 | VT ciudad restantes |
| — | Lun 7/4 | 0 (esperar upgrade) | 1,000 | — | Meta evalúa tier → esperamos Tier 2 |
| 3 | Mar 8/4 | 5,000 | 6,000 | 09:00-13:00 | Región (3382, 3468, 236, etc) |
| 4 | Mié 9/4 | 10,000 | 16,000 | 09:00-14:00 | Mix todas las zonas (DÍA 1 OUTLET) |
| 5 | Jue 10/4 | 10,000 | 26,000 | 09:00-14:00 | Restantes |
| 6 | Vie 11/4 | 8,389 | 34,389 | 09:00-13:00 | Últimos + follow-up no respondidos |

### Reglas de batching dentro de cada día

```
POR HORA:    máx 200 mensajes
POR MINUTO:  máx 10 mensajes (1 cada 6 segundos)
PAUSA:       3 minutos de pausa cada 100 mensajes
PAUSA LARGA: 15 minutos de pausa cada 500 mensajes
```

### Monitoreo en tiempo real
Después de cada batch de 100 mensajes, verificar:
- ¿Hubo errores de envío? (API error code)
- ¿Cuántos "delivery failed"? (número no existe en WhatsApp)
- ¿Cuántos bloquearon? (status webhook = "failed" con error 131051)

**Si error rate > 5%** → pausar 1 hora
**Si error rate > 10%** → pausar hasta el día siguiente
**Si quality baja a YELLOW** → STOP inmediato, no enviar más hasta que vuelva a GREEN

---

## SEGMENTACIÓN: ORDEN DE PRIORIDAD

| Prioridad | Segmento | Teléfono empieza con | Cant estimada | Por qué primero |
|-----------|----------|---------------------|---------------|-----------------|
| 1 | VT ciudad | 5493462 | ~18,000 | Clientes locales, más probable que vengan al outlet |
| 2 | Zona regional | 5493468, 5493382 | ~4,000 | Pueblos cercanos (Rufino, Firmat, etc) |
| 3 | Junín/Pergamino | 549236, 549234 | ~8,000 | Sucursal Junín, conocen la marca |
| 4 | CABA/GBA | 54911 | ~2,000 | Clientes web, menos probable que vengan |
| 5 | Resto país | otros | ~2,000 | Último, evaluar si vale la pena |

### Dentro de cada segmento: ordenar por recencia
Priorizar clientes que compraron más recientemente (cruzar con `cta_cte_movimientos.fecha`).

---

## AUTO-RESPONDER: FLUJO DE RESPUESTAS

Cuando el cliente toca un botón:

```
"Avisame cuando arranque" → Respuesta + flyer del outlet
"Que va a haber?"         → Lista de categorías + precios + flyer
```

Script: `valijas/responder_agencias.py` (monitor launchd cada 30s)
Flyer: `valijas/imagenes/flyer_outlet_abril.jpg`

### Respuestas adicionales post-interacción
Si después de responder el cliente pregunta algo más:
- "donde queda" / "direccion" / "ubicacion" → Av. Santa Fe 1246, Venado Tuerto + Google Maps link
- "horario" / "hora" → 10:00 a 21:00 del 9 al 12 de abril
- "tarjeta" / "cuotas" / "pago" → Efectivo, débito, crédito. Pagá lo que quieras
- "mayorista" / "por mayor" → Sí, ventas por mayor también. Vení con CUIT

---

## PROTECCIÓN DEL NÚMERO

### Lo que NUNCA hacer
- Mandar más de 1,000 en las primeras 48hs
- Mandar todos el mismo segundo
- Mandar a números que ya bloquearon
- Mandar después de las 21hs o antes de las 8hs
- Ignorar el quality rating

### Lo que SÍ hacer
- Warm-up gradual (500 → 500 → 5K → 10K)
- Pausas naturales entre mensajes (6 segundos mínimo)
- Monitorear quality rating después de cada batch
- Dar opción de opt-out ("Respondé STOP para no recibir más mensajes" en el footer)
- Priorizar clientes recientes (menos probable que reporten spam)
- Separar campañas del chatbot (usar 1170, NO el 7436)

### Métricas a monitorear

| Métrica | Aceptable | Alerta | Stop |
|---------|-----------|--------|------|
| Delivery rate | >95% | 90-95% | <90% |
| Block rate | <2% | 2-5% | >5% |
| Quality rating | GREEN | YELLOW | RED |
| Reply rate | >10% | 5-10% | <5% (revisar mensaje) |

---

## ARCHIVOS DEL SISTEMA

| Archivo | Función |
|---------|---------|
| `valijas/contactos_whatsapp_calzalindo.json` | 34,389 contactos normalizados |
| `valijas/enviar_whatsapp_agencias.py` | Script envío (adaptar para outlet) |
| `valijas/responder_agencias.py` | Auto-responder Chatwoot |
| `valijas/monitor_respuestas.sh` | Monitor launchd cada 30s |
| `valijas/imagenes/flyer_outlet_abril.jpg` | Flyer outlet |
| `valijas/LISTA_AGENCIAS_PROSPECCION.xlsx` | 36 agencias (campaña separada) |

---

## SCRIPT DE ENVÍO: `enviar_outlet_masivo.py`

Pendiente de crear. Debe tener:
- Lectura de `contactos_whatsapp_calzalindo.json`
- Filtro por segmento (VT, regional, etc)
- Rate limiting configurable (default 1 cada 6 seg)
- Pausas automáticas cada 100 y 500 mensajes
- Monitoreo de errores en tiempo real
- Log detallado con timestamps
- Flag `--dryrun` / `--limit N` / `--segmento VT`
- Actualiza JSON marcando enviados para no repetir
- Chequeo de quality rating cada 200 mensajes

---

## TIMELINE RESUMEN

```
Viernes 4/4 (hoy):  Preparar todo, testar, verificar template
Sábado 5/4 10:00:   Batch 1 — 500 contactos VT
Domingo 6/4 10:00:  Batch 2 — 500 contactos VT
Lunes 7/4:          Esperar upgrade tier (Meta evalúa cada 6hs)
Martes 8/4 09:00:   Batch 3 — 5,000 contactos región
Miércoles 9/4 09:00: Batch 4 — 10,000 (DÍA 1 OUTLET)
Jueves 10/4 09:00:  Batch 5 — 10,000
Viernes 11/4 09:00: Batch 6 — 8,389 + follow-ups
Sábado 12/4:        ÚLTIMO DÍA OUTLET
```
