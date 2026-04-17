# TAREA: Crear y enviar template WhatsApp — Campaña ALITA

## Contexto
Necesitamos crear un template de WhatsApp aprobado por Meta para lanzar una campaña
a 416 clientes que compraron calzado ALITA (marca=13 en articulo) en los últimos 5 años.

El CSV con los contactos ya está generado:
`_excel_pedidos/campana_alita_20260417_limpio.csv`
(416 contactos, columna `telefono_wa` en formato `549346XXXXXXXX`)

---

## Paso 1 — Levantar los modelos actuales: stock + pedidos de temporada

Conectate al SQL Server (111 o 112 vía pyodbc) y corré estas dos queries:

### 1a — Stock actual de ALITA (ingresos recientes)
```sql
SELECT DISTINCT
    a.descripcion_1,
    SUM(s.stock_actual) AS stock_total,
    a.precio_1
FROM msgestion01art.dbo.articulo a
INNER JOIN msgestionC.dbo.stock s ON s.articulo = a.codigo
INNER JOIN msgestionC.dbo.compras1 c ON c.articulo = a.codigo AND c.operacion = '+'
WHERE a.marca = 13
  AND s.stock_actual > 0
  AND c.fecha >= DATEADD(month, -3, GETDATE())
GROUP BY a.descripcion_1, a.precio_1
ORDER BY stock_total DESC
```

### 1b — Pedidos de temporada OI2026 ya cargados (pedico1/pedico2)
Buscar los pedidos de proveedor ALITA que ya están en el sistema,
porque puede haber modelos pedidos que todavía no llegaron pero que
se van a recibir próximamente y conviene mencionarlos en la campaña.

```sql
-- Pedidos de temporada con artículos ALITA (marca=13)
SELECT DISTINCT
    a.descripcion_1,
    SUM(p.cantidad) AS pares_pedidos,
    a.precio_1,
    MAX(p2.fecha) AS fecha_pedido
FROM msgestion01.dbo.pedico1 p
INNER JOIN msgestion01.dbo.pedico2 p2 ON p2.numero = p.numero AND p2.sucursal = p.sucursal
INNER JOIN msgestion01art.dbo.articulo a ON a.codigo = p.articulo
WHERE a.marca = 13
  AND p2.estado = 'V'
  AND p2.fecha >= DATEADD(month, -6, GETDATE())
GROUP BY a.descripcion_1, a.precio_1
ORDER BY pares_pedidos DESC
```

> Si el proveedor está en base msgestion03 (H4), cambiar msgestion01 → msgestion03.

Unificá ambos resultados para tener la foto completa:
**modelos en stock ahora + modelos que vienen en camino.**

Con eso confirmamos qué modelos mostrar en el template.

---

## Paso 2 — Armar el template para Meta

El template tiene que seguir el formato de la WhatsApp Business API.
Nombre sugerido: `alita_nuevos_ingresos` (sin espacios, minúsculas)
Categoría: MARKETING | Idioma: es

Estructura:
- **Header**: IMAGE (el usuario va a proveer la foto)
- **Body**: texto con variable {{1}} para el nombre del cliente
- **Footer**: "Calzalindo · Venado Tuerto"
- **Botón**: Quick Reply "Quiero verlos"

Redactá el body con los modelos reales que devuelva la query del paso 1.

---

## Paso 3 — Enviar a Meta vía API

Usá el token WABA que está en el .env de clz-bot o en n8n.
El endpoint es:

```
POST https://graph.facebook.com/v19.0/{WABA_ID}/message_templates
Authorization: Bearer {TOKEN}
Content-Type: application/json
```

Body del request:
```json
{
  "name": "alita_nuevos_ingresos",
  "category": "MARKETING",
  "language": "es",
  "components": [
    {
      "type": "HEADER",
      "format": "IMAGE",
      "example": { "header_handle": ["SUBIR_IMAGEN_AQUI"] }
    },
    {
      "type": "BODY",
      "text": "COMPLETAR_CON_PASO_2",
      "example": { "body_text": [["Fernando"]] }
    },
    {
      "type": "FOOTER",
      "text": "Calzalindo · Venado Tuerto"
    },
    {
      "type": "BUTTONS",
      "buttons": [
        { "type": "QUICK_REPLY", "text": "Quiero verlos" }
      ]
    }
  ]
}
```

Para el header con imagen: primero hay que subir la imagen al Media API de Meta
y obtener el `header_handle`. Si no tenés imagen todavía, podés crear el template
como TEXT header y después editarlo.

---

## Paso 4 — Alternativa manual (si no tenés el token)

Abrí: https://business.facebook.com → WhatsApp Manager → Plantillas de mensajes → Crear
y cargá los campos del Paso 2 a mano.

---

## Archivos relevantes
- CSV contactos: `_excel_pedidos/campana_alita_20260417_limpio.csv`
- Config conexión SQL: `config.py`
- Referencia n8n/WABAs: `~/.claude/projects/.../memory/reference_n8n_mcp.md`
- Credenciales: en `.env` de `C:\calzalindo_freelance\` en el 112

---

## Lo que NO hace falta investigar (ya sabemos)
- Marca ALITA = código 13 en campo `marca` de `msgestion01art.dbo.articulo`
- Últimos ingresos: 3 abril 2026 — Mocasín negro 8082, Mocasín visón 8087,
  Mocasín negro 8086, Bota negra 5182 — precios $90k-$110k
- 416 clientes ya están en el CSV listos para importar en bot.calzalindo.com.ar/campanas
