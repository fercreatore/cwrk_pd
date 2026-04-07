# INSIGHT DIARIO — Mie 2 de Abril 2026

## 3 COSAS PARA HOY

🔴 **MARCA 75: 1 PAR EN STOCK, vende 24/mes** — Cobertura 1.2 días. Facturó $11.7M en 12 meses. Está muerta en vidriera. Pedirle a Mati que reponga HOY.

🟡 **552 LINEAS DE PEDIDO VENCIDAS ($129M pendientes, 3,399 pares)** — Proveedores que no entregan. Revisar top 5 vencidos con Mariana y reclamar. Plata comprometida que no se convierte en stock.

🟢 **AYER: $7.66M en ventas, 237 pares, 88 clientes** — Miércoles semana pasada fue feriado (0 ventas), no es comparable. Pero el ritmo diario está en línea con Q1 (~$12.8M/día promedio descontando feriados).

---

## CICLO FINANCIERO COMPLETO — Foto de hoy

```
╔══════════════════════════════════════════════════════════════╗
║                    CICLO DEL CAPITAL                         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  PROVEEDORES ──compras──> STOCK ──ventas──> CLIENTES         ║
║  Les debemos              Lo tenemos        Nos deben        ║
║  $1,347M                  ~$850M            $361M            ║
║  (267 provs)              (real)            (20 ctas)        ║
║                                                              ║
║       │                      │                    │          ║
║       ▼                      ▼                    ▼          ║
║  PAGOS                   ROTACION              COBROS        ║
║  A programar             Dias cobertura        Tarjetas +    ║
║  según plazo             varía por marca       Cta cte +     ║
║                                                Efectivo      ║
║                                                              ║
║  ◄────────── CAPITAL DE TRABAJO = $1,836M ──────────────►    ║
║  (lo que debemos + lo invertido en stock - lo que nos deben) ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

### Números clave del ciclo:

| Concepto | Monto | Detalle |
|----------|-------|---------|
| **Deuda a proveedores** | $1,347M | 267 proveedores con saldo |
| **Stock invertido** | ~$850M | Excluyendo anomalía art 306188 |
| **Clientes nos deben** | $361M | 20 cuentas con saldo |
| **Pedidos pendientes recibir** | $129M | 552 líneas vencidas |
| **Capital de trabajo neto** | ~$1,836M | Proveedores + stock - cobros |

### La pregunta que importa:

**¿La plata que entra (ventas + cobros) alcanza para cubrir la plata que sale (pagos a proveedores)?**

- Vendés ~$12.8M/día → ~$384M/mes
- Margen bruto ~48% → ~$184M/mes de ganancia bruta
- Deuda proveedores $1,347M ÷ $384M/mes = **3.5 meses para pagar todo** (si no comprás más)

### Tablas del ERP disponibles para el ciclo:

| Tabla | Qué tiene | Para qué |
|-------|-----------|----------|
| `moviclie1` | Cta cte clientes (facturas, NC, cobros) | Saber quién nos debe y cuánto |
| `moviclie2` | Aplicaciones/cancelaciones | Matcheo factura vs pago |
| `moviprov1` | Cta cte proveedores (facturas, OP, pagos) | Saber cuánto debemos y a quién |
| `moviprov2` | Aplicaciones/cancelaciones | Matcheo factura vs pago |
| `tarjetas_cartera` | Cupones tarjeta pendientes | Plata en camino (VISA, MC, etc) |
| `tarjetas_acreditacion` | Liquidaciones de tarjetas | Cuándo cobra realmente |
| `cheques` | Cheques emitidos/recibidos | Cheques en cartera |
| `saldos_d_caja` | Caja diaria por sucursal | Efectivo disponible |
| `detalle_caja` | Movimientos de caja | Apertura/cierre/retiros |
| `co_flujo_fondo` | Flujo de fondos | Si está cargado, es oro |
| `compras2` | Facturas de compra | Vencimientos a pagar |
| `pedidos_cumplimiento_cache` | Pedidos a proveedores | Compromisos futuros |

---

## FLUJO DE CAJA RÁPIDO

```
═══════════════════════════════════════════════════════
           LO QUE SALE (pagos a proveedores)
═══════════════════════════════════════════════════════
  VENCIDO (ya debería estar pago):  $567M  ← 201 provs
  Esta semana:                       $11M  ← 5 provs
  Próximos 15 días:                   $8M  ← 3 provs
  Próximos 30 días:                  $38M  ← 11 provs
  Más de 30 días:                    $19M  ← 3 provs
  ─────────────────────────────────────────
  TOTAL COMPROMETIDO:               $643M

═══════════════════════════════════════════════════════
           LO QUE ENTRA (cobros de clientes)
═══════════════════════════════════════════════════════
  Ventas diarias promedio:          $12.8M/día
  Clientes nos deben (cta cte):      $4.7M  ← 3 ctas
  (la mayoría cobra contado/tarjeta, poco en cta cte)
═══════════════════════════════════════════════════════
```

### Top 5 proveedores con más deuda:

| Proveedor | Deuda | Vence desde | Comprobantes |
|-----------|-------|-------------|-------------|
| DISTRINANDO MODA | $52.3M | nov-2025 | 11 |
| MERCADO LIBRE | $50.6M | ene-2024 (!) | 33 |
| Shoeholic | $35.1M | jul-2025 | 2 |
| KUNSHAN | $30.2M | feb-2025 | 1 |
| ALPARGATAS | $25.4M | mar-2026 | 6 |

### Anomalías detectadas en pagos:

🔴 **ML vence desde ene-2024** — 33 comprobantes sin cancelar hace 15 meses. ¿Son comisiones impagas o error de imputación? Verificar con Mariana.

🔴 **$567M vencidos** a 201 proveedores — Es el 88% de toda la deuda. Si es real, hay un problema serio de caja. Si es acumulación de comprobantes viejos mal cancelados, hay que limpiar la cta cte.

🟡 **DISTRINANDO MODA $52M** — Proveedor activo, vence desde nov-2025. Son 5 meses de atraso.

### Clientes morosos (cta cte):

| Cliente | Deuda | Desde |
|---------|-------|-------|
| Cta 41070187 | $2.5M | may-2024 |
| Cta 11007 | $1.7M | jun-2024 |
| Cta 24581905 | $523K | may-2024 |

Total clientes morosos: $4.7M — Bajo relativo al negocio, pero los 3 llevan +10 meses sin pagar.

---

### Diagnóstico del ciclo:

```
ENTRADA SEMANAL:  ~$64M (5 días × $12.8M/día)
SALIDA SEMANAL:   ~$57M (pagos semanales promedio si se normaliza)
MARGEN SEMANAL:   +$7M (la caja alcanza, pero ajustada)

⚠️  Los $567M "vencidos" necesitan auditoría:
    - Si son reales → hay default con proveedores
    - Si son errores de imputación → limpiar moviprov
    - Probablemente mix: algunos reales + muchos mal cancelados
```

---

*Generado: 2 de abril 2026, 13:00 — Agente insight-diario (test run)*
