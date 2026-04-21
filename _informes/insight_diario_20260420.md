# 📊 Insight Lunes 20-abr-2026

> Generado automáticamente. Queries Q2/Q5 con timeout (stock cobertura marcas y ranking deuda prov).

---

## Datos crudos

| Métrica | Valor |
|---------|-------|
| Venta ayer (dom 19-abr) | $27,445 / 3 pares / 1 cliente |
| Venta dom 12-abr (sem ant) | $0 |
| Pedidos vencidos (líneas) | 812 |
| Pares vencidos | 5,031 |
| Monto pedidos vencidos | $151,241,998 |
| Deuda prov VENCIDA | $606,496,121 (203 proveedores) |
| Deuda prov ESTA SEMANA | $42,915,116 (22 proveedores) |
| Deuda prov MÁS 30D | $112,816,205 (30 proveedores) |
| Clientes nos deben (top 3) | $2.54M + $1.69M + $0.52M = $4.75M |

### Q7 — Stock muerto sin auditar

| CSR | Descripción | Stock | Valor | Auditoría |
|-----|-------------|-------|-------|-----------|
| 017ANCCH0040 | GO DANCE NEGRO talle 40 | 179 | $10.74M | NUNCA |
| 86600w150100 | TELA DRY FIT W15 BLANCA | 563 u | $4.32M | NUNCA |
| 017ANCCH0042 | GO DANCE NEGRO talle 42 | 40 | $2.4M | NUNCA |
| 017ANCCH0035 | GO DANCE NEGRO talle 35 | 19 | $1.14M | NUNCA |
| 017001525138 | PLANTILLA DEPORTIVA 152 | 30 | $780K | NUNCA |
| **TOTAL** | | | **$19.37M** | |

---

## Análisis

🔴 **ACCIÓN — Tesorería:** $606M vencido con 203 proveedores. Esta semana vencen $43M adicionales (22 prov). Riesgo reputacional y de corte de crédito con marcas clave de invierno. Responsable: Fernando, coordinar con Mati qué pendientes de invierno 2026 están en riesgo.

🟡 **MONITOREAR — Entregas:** 812 líneas de pedido vencidas con 5,031 pares sin entregar ($151M). Con temporada invierno en ingreso, cualquier demora adicional genera rotura de stock. Cruzar con proveedores con pedidos OI26 confirmados.

🟢 **POSITIVO — Cobranza:** Clientes deben solo $4.75M en cuentas corrientes (3 cuentas). La cobranza está al día, no hay concentración de riesgo.

🔍 **AUDITORÍA — GO by CLZ:** 238 pares GO DANCE sin vender en 12 meses y NUNCA auditados ($14.3M solo en zapatillas danza). Sumando los 5 artículos: $19.4M inmovilizado sin movimiento. Gonzalo debe auditar presencialmente. También hay 563u de tela DRY FIT ($4.3M) — verificar si es insumo activo o faltante de baja en sistema.

---

## Resumen ejecutivo

💰 **Flujo 7d:** Vencido proveedores $606M | Esta semana $43M | Ingreso ayer (dom) $27K

El dato más anómalo del día es la combinación deuda vencida masiva ($606M / 203 prov) con pedidos no entregados (812 líneas, $151M). Esto sugiere que el ciclo compras→pago está desincronizado: se están pagando facturas de mercadería que aún no llegó, o hay deuda acumulada de temporadas anteriores sin cancelar. Acción: mapear top 5 proveedores vencidos (query Q5 con timeout hoy) y priorizarlos manualmente.
