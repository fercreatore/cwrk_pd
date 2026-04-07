# Integración Alertas de Auditoría al Insight Diario
## Especificación técnica — 3 de abril de 2026

---

## 1. Query Q7 — Artículos que necesitan auditoría urgente

Esta query se agrega al SKILL.md del insight-diario como Q7, después de Q6 (clientes morosos).

```sql
-- Q7 — Artículos stock muerto sin auditar (urgentes para Gonzalo)
SELECT TOP 10
  sm.articulo,
  a.codigo_sinonimo as csr,
  a.descripcion_1 as descripcion,
  a.marca as cod_marca,
  a.precio_costo,
  sm.stock_total,
  sm.stock_total * ISNULL(a.precio_costo, 0) as valor_stock,
  la.fecha as ultima_auditoria,
  CASE WHEN la.fecha IS NULL THEN 'NUNCA'
       WHEN DATEDIFF(DAY, la.fecha, GETDATE()) > 180 THEN 'VENCIDA'
       WHEN DATEDIFF(DAY, la.fecha, GETDATE()) > 90 THEN 'PENDIENTE'
       ELSE 'OK' END as estado_auditoria
FROM (
  SELECT s.articulo, SUM(s.stock_actual) as stock_total
  FROM msgestionC.dbo.stock s
  WHERE s.deposito IN (0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)
  GROUP BY s.articulo
  HAVING SUM(s.stock_actual) > 5
) sm
JOIN msgestion01art.dbo.articulo a ON a.codigo = sm.articulo
LEFT JOIN omicronvt.dbo.t_articulos_last_audit la
  ON la.codigo = sm.articulo AND la.depo_macro = 0
LEFT JOIN (
  SELECT DISTINCT v.articulo
  FROM msgestionC.dbo.ventas1 v
  WHERE v.codigo NOT IN (7,36)
    AND v.cantidad > 0
    AND v.fecha >= DATEADD(MONTH, -12, GETDATE())
) vtas ON vtas.articulo = sm.articulo
WHERE vtas.articulo IS NULL
  AND a.marca NOT IN (1316, 1317, 1158, 436)
  AND (la.fecha IS NULL OR DATEDIFF(DAY, la.fecha, GETDATE()) > 90)
  AND sm.stock_total * ISNULL(a.precio_costo, 0) > 200000
ORDER BY sm.stock_total * ISNULL(a.precio_costo, 0) DESC
```

## 2. Query Q7b — Resumen de estado de auditorías (contexto)

Esta query da el panorama general para decidir si incluir el bullet o no.

```sql
-- Q7b — Resumen estado auditorías stock muerto
SELECT
  SUM(CASE WHEN la.fecha IS NULL THEN 1 ELSE 0 END) as nunca_auditado,
  SUM(CASE WHEN la.fecha IS NOT NULL AND DATEDIFF(DAY, la.fecha, GETDATE()) > 180 THEN 1 ELSE 0 END) as vencida_180d,
  SUM(CASE WHEN la.fecha IS NOT NULL AND DATEDIFF(DAY, la.fecha, GETDATE()) BETWEEN 91 AND 180 THEN 1 ELSE 0 END) as pendiente_90d,
  SUM(CASE WHEN la.fecha IS NOT NULL AND DATEDIFF(DAY, la.fecha, GETDATE()) <= 90 THEN 1 ELSE 0 END) as ok_reciente,
  COUNT(*) as total_arts_muertos,
  SUM(sm.stock_total * ISNULL(a.precio_costo, 0)) as valor_total_muerto
FROM (
  SELECT s.articulo, SUM(s.stock_actual) as stock_total
  FROM msgestionC.dbo.stock s
  WHERE s.deposito IN (0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)
  GROUP BY s.articulo
  HAVING SUM(s.stock_actual) > 5
) sm
JOIN msgestion01art.dbo.articulo a ON a.codigo = sm.articulo
LEFT JOIN omicronvt.dbo.t_articulos_last_audit la
  ON la.codigo = sm.articulo AND la.depo_macro = 0
LEFT JOIN (
  SELECT DISTINCT v.articulo
  FROM msgestionC.dbo.ventas1 v
  WHERE v.codigo NOT IN (7,36)
    AND v.cantidad > 0
    AND v.fecha >= DATEADD(MONTH, -12, GETDATE())
) vtas ON vtas.articulo = sm.articulo
WHERE vtas.articulo IS NULL
  AND a.marca NOT IN (1316, 1317, 1158, 436)
```

## 3. Formato del bullet de auditoría

### Cuando Q7 devuelve resultados (hay artículos urgentes):

En el bloque de WhatsApp (los 3 bullets):
```
🔍 *AUDITORÍA* X arts sin auditar ($Ym valor). Gonzalo: priorizar [MARCA] [descripción] ($Zk)
```

En el .md detallado, agregar sección:
```
## AUDITORÍA DE STOCK MUERTO

X artículos con stock > 5 uds, 0 ventas en 12 meses, sin auditar y valor > $200K.
Valor total inmovilizado: $Ym. Gonzalo debe priorizar:

| # | Artículo | Descripción | Marca | Stock | Valor | Última auditoría |
|---|----------|-------------|-------|-------|-------|-----------------|
| 1 | ... | ... | MARCA | Xu | $Xk | NUNCA |
```

### Cuando Q7 NO devuelve resultados:
No incluir el bullet de auditoría. No agregar ruido al insight.

### Lógica de selección del bullet (cuando compite con otros):

El bullet de auditoría es prioridad media (nivel amarillo). Solo aparece como uno de los 3 bullets si:
- Hay al menos 3 artículos urgentes, O
- El valor total sin auditar supera $5M

Si no alcanza para entrar en los 3 bullets principales, agregarlo como nota al final del bloque de flujo de caja.

## 4. Ejemplo con datos reales

Basado en el reporte stock_muerto_anomalias del 1-abr-2026 (excluyendo anomalías de datos ya identificadas: art 306188 y 5 GTN con precio_costo erróneo):

**Bullet para WhatsApp:**
```
🔍 *AUDITORÍA* ~45 arts sin auditar ($21M valor). Gonzalo: priorizar GO by CZL en depósito central ($5.8M)
```

**Detalle para el .md:**
```
## AUDITORÍA DE STOCK MUERTO

45 artículos con stock > 5 uds, 0 ventas en 12 meses, sin auditar.
Valor total inmovilizado: ~$21.2M (excluye anomalías precio_costo).
Gonzalo: priorizar las siguientes marcas:

| # | Marca | Arts | Valor | Acción sugerida |
|---|-------|------|-------|-----------------|
| 1 | GO by CZL | ~10 | $5.8M | Verificar si están exhibidos |
| 2 | LANACUER | 3 | $2.0M | Candidato a devolución |
| 3 | HUSH PUPPIES | 6 | $1.8M | Revisar talles extremos |
| 4 | TOPPER | 3 | $1.2M | Rack de liquidación |
| 5 | LESEDIFE | 1 | $395K | Liquidar |
```

## 5. Mapping de marcas (para resolución de nombres en Q7)

Incluir en el SKILL.md actualizado. Las marcas más comunes en stock muerto:

| Código | Nombre para el insight |
|--------|----------------------|
| 314 | TOPPER |
| 17 | GO by CZL |
| 594 | ATOMIK/WAKE |
| 264 | GRIMOLDI |
| 513 | REEBOK |
| 104 | GTN |
| 656 | DISTRINANDO DEP |
| 990 | CLZ BEAUTY |
| 669 | LANACUER |
| 608 | BALL ONE |
| 817 | KALIF |
| 770 | PRIMER ROUND |
| 294 | CARMEL |
| 311 | ROFREVE |
| 42 | LESEDIFE |
| 515 | ELEMENTO |
| 746 | PICCADILLY |
| 139 | HUSH PUPPIES |
| 75 | CROCS |
| 744 | HAVAIANAS |
| 883 | SAUCONY |
| 765 | HUSH PUPPIES |
| 794 | (verificar nombre) |
| 639 | (verificar nombre) |
| 671 | (verificar nombre) |
| 822 | (verificar nombre — art 306188, anomalía) |

## 6. Instrucciones para actualizar la scheduled task

### Paso a paso:

1. **Actualizar el SKILL.md** del insight-diario agregando Q7 y Q7b al PASO 1.

2. **Actualizar la lógica del PASO 2** para que incluya:
   - Si Q7 devuelve filas: evaluar si entra como bullet (>= 3 arts o valor > $5M)
   - Resolver cod_marca a nombre usando el mapping existente
   - El artículo con mayor valor_stock de Q7 es el que se menciona en el bullet

3. **Agregar al PASO 3** la regla de formato:
   - Si hay alerta de auditoría y es suficientemente relevante, puede reemplazar al bullet verde (positivo) o agregarse como línea extra bajo el bloque de flujo

4. **Texto a agregar al SKILL.md** (sección Q7, después de Q6):

```
Q7 — Artículos stock muerto sin auditar (para Gonzalo):
[pegar la query Q7 de la sección 1 de este documento]

Q7b — Resumen estado auditorías:
[pegar la query Q7b de la sección 2 de este documento]

REGLA AUDITORÍA:
- Si Q7 devuelve resultados (>= 3 arts O valor > $5M): incluir bullet 🔍
- Formato: 🔍 *AUDITORÍA* X arts sin auditar ($Ym valor). Gonzalo: priorizar [MARCA_NOMBRE] [descripcion] ($Zk)
- SIEMPRE usar NOMBRE de marca (del mapping), NUNCA código numérico
- Si Q7 no devuelve resultados: no incluir bullet de auditoría
- EXCLUIR artículos con precio_costo > $500.000 (anomalías de datos conocidas)
- En el .md detallado: agregar tabla completa de Q7 con marcas resueltas
```

5. **Ejecutar la actualización** via herramienta `update_scheduled_task`:
   - taskId: `insight-diario`
   - prompt: [el SKILL.md completo actualizado]

### Filtro de anomalías de datos

Agregar a Q7 este filtro adicional para excluir artículos con precio_costo absurdo:
```sql
AND a.precio_costo < 500000
```

Esto excluye automáticamente el art 306188 ($6.9M/ud) y los 5 GTN ($2.7M/ud) que son errores de carga conocidos.

### Query Q7 final (con filtro anomalías):

```sql
SELECT TOP 10
  sm.articulo, a.codigo_sinonimo as csr, a.descripcion_1 as descripcion,
  a.marca as cod_marca, a.precio_costo,
  sm.stock_total, sm.stock_total * ISNULL(a.precio_costo, 0) as valor_stock,
  la.fecha as ultima_auditoria,
  CASE WHEN la.fecha IS NULL THEN 'NUNCA'
       WHEN DATEDIFF(DAY, la.fecha, GETDATE()) > 180 THEN 'VENCIDA'
       WHEN DATEDIFF(DAY, la.fecha, GETDATE()) > 90 THEN 'PENDIENTE'
       ELSE 'OK' END as estado_auditoria
FROM (
  SELECT s.articulo, SUM(s.stock_actual) as stock_total
  FROM msgestionC.dbo.stock s
  WHERE s.deposito IN (0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)
  GROUP BY s.articulo
  HAVING SUM(s.stock_actual) > 5
) sm
JOIN msgestion01art.dbo.articulo a ON a.codigo = sm.articulo
LEFT JOIN omicronvt.dbo.t_articulos_last_audit la
  ON la.codigo = sm.articulo AND la.depo_macro = 0
LEFT JOIN (
  SELECT DISTINCT v.articulo
  FROM msgestionC.dbo.ventas1 v
  WHERE v.codigo NOT IN (7,36)
    AND v.cantidad > 0
    AND v.fecha >= DATEADD(MONTH, -12, GETDATE())
) vtas ON vtas.articulo = sm.articulo
WHERE vtas.articulo IS NULL
  AND a.marca NOT IN (1316, 1317, 1158, 436)
  AND a.precio_costo < 500000
  AND (la.fecha IS NULL OR DATEDIFF(DAY, la.fecha, GETDATE()) > 90)
  AND sm.stock_total * ISNULL(a.precio_costo, 0) > 200000
ORDER BY sm.stock_total * ISNULL(a.precio_costo, 0) DESC
```

---

*Generado el 3 de abril de 2026. Listo para integrar al scheduled task insight-diario.*
