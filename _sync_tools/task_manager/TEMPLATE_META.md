# Template Meta para aprobar — Task Manager

## Template: `tareas_dia`

**Categoria**: UTILITY (mas barato que marketing, ~$0.02 USD)
**Idioma**: es_AR

### Texto del template:

```
Hola {{1}}, estas son tus tareas pendientes. Responde "ok" para confirmar.
```

### Parametros:
- `{{1}}` = nombre de la persona (ej: "Mati", "Gonza")

### Como crear en Meta Business:

1. Ir a https://business.facebook.com/wa/manage/message-templates/
2. Seleccionar la cuenta CALZALINDO (7436)
3. Click "Crear plantilla"
4. Configurar:
   - Nombre: `tareas_dia`
   - Categoria: **Utility**
   - Idioma: Espanol (Argentina)
   - Cuerpo: `Hola {{1}}, estas son tus tareas pendientes. Responde "ok" para confirmar.`
   - No agregar header ni footer ni botones (mantenerlo simple)
5. Enviar para revision

### Tiempo de aprobacion: 24-48hs generalmente

### Como se usa:

Este template se envia 1 vez al dia a cada persona del equipo (8:30 AM).
Cuando la persona responde "ok", se abre ventana de 24hs y el bot
puede mandar el detalle completo de tareas como TEXTO LIBRE (gratis).

**Costo mensual estimado**: $0.02 x 8 personas x 22 dias = $3.52 USD/mes

---

## Template alternativo (si rechazan el anterior):

### `recordatorio_equipo`

```
{{1}}, tenes novedades del equipo. Escribi "tareas" para verlas.
```

Misma logica: 1 parametro, utility, simple.
