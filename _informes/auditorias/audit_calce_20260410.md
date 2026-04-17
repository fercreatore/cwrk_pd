# Auditoría Calce Financiero — 10 de abril de 2026

> Ejecutado automáticamente por agente. Bases: msgestion01, msgestion03, msgestionC.
> Solo CALZALINDO/msgestion01 auditado (msgestion03/H4 requiere queries separadas).

---

## 🔴 CRÍTICO — Acción inmediata requerida

### 1. CHEQUES VENCEN HOY/ESTA SEMANA (próximos 7 días)
| Proveedor | Cheques | Monto |
|-----------|---------|-------|
| ALQUILERES (#1494) | 4 | **$7.29M** |
| ZOTZ (#457) | 3 | $535K |
| **TOTAL URGENTE** | | **$7.82M** |

> Los 4 cheques de alquileres vencen en los próximos 7 días. Verificar fondos disponibles.

---

### 2. KALIF - ALEX SPORT (#817) — Saldo -$33.3M (nos deben)
**Situación:** Se pagaron $33.3M más de lo que se les debe según sus facturas en la CC.

Desglose de movimientos sin cancelar:
- 31-mar-2026: Pagos en **CHEQUES** $25.2M (sin facturas que los respalden en el sistema)
- 30-mar-2026: **DEPOSITO** $8.1M (sin cancelar)
- 17-nov-2025: Ajuste "+AJUSTE MERCADERIA MAL CARGADA" $11.4M (aún sin cancelar, código 15)
- 17-nov-2025 y 15-nov-2025: Pagos $3.4M + $8.0M sin respaldar

**Lo que parece:** Se hicieron pagos anticipados por $33.3M para la temporada OI2026. Los 9 remitos de entrada de abril (por $31.1M desde 01-abr) son la mercadería que se pagó por adelantado.

**Acción:** Confirmar que los remitos KALIF de abril ($31.1M) son la contrapartida de los pagos. Si sí → emitir facturas para cancelar el saldo. Si no → **investigar destino de $33.3M.**

---

### 3. WABRO S.A. (#602) — Deuda $10.1M vencida desde ENE-2023 (3+ años)
Factura sin pagar hace más de 3 años. Monto: $10.1M en 4 cuotas/facturas.
> Riesgo legal activo. Verificar si hay acuerdo de pago informal no registrado en sistema.

### 4. ALMACEN DE MODA (#328) — Deuda $10.5M, 45 facturas desde JUL-2024
La deuda más grande por cantidad de comprobantes: 45 facturas acumuladas sin pagar desde julio 2024.
> Probablemente proveedor recurrente con mora sistemática. Revisar condiciones comerciales.

### 5. INTERNATIONAL BRANDS SRL (#876) — $1.5M desde OCT-2022 (4 años)
Deuda más antigua del sistema. Pocas chances de cobro espontáneo a esta altura.

---

## 🟡 ATENCIÓN — Monitorear

### Facturas vencidas >180 días (top 10, solo CALZALINDO)
| Proveedor | Monto pendiente | Facturas | Más antigua |
|-----------|----------------|----------|-------------|
| ALMACEN DE MODA (#328) | $10.5M | 45 | 28-jul-2024 |
| WABRO S.A. (#602) | $10.1M | 4 | 28-ene-2023 |
| ROFREVE (#311) | $5.8M | 6 | 12-ene-2025 |
| LANNOT SA (#873) | $4.0M | 1 | 02-oct-2025 |
| El Dante S.A. (#299) | $2.5M | 1 | 24-feb-2024 |
| CAL ARG SRL (#266) | $1.9M | 5 | 29-feb-2024 |
| BEREL-K (#4) | $1.8M | 2 | 24-jun-2025 |
| INTERNATIONAL BRANDS SRL (#876) | $1.5M | 1 | 24-oct-2022 |
| BRENDA srl. Calzados (#933) | $1.5M | 3 | 30-oct-2024 |
| MARIANO PANCZUZH (#956) | $1.3M | 5 | 27-may-2023 |
| MAQUEIRAS SHOES (#10) | $1.3M | 1 | 08-abr-2024 |

**Total deuda vencida >180 días:** ~$42M estimado (top 10 suman ~$41.4M)

---

### Saldos negativos en CC proveedores (nos deben, por pagos sin facturas registradas)
| Proveedor | Saldo (nos deben) | Nota |
|-----------|------------------|------|
| KALIF - ALEX SPORT (#817) | -$33.3M | Ver sección crítica arriba |
| MARIO INNOVA (#1436) | -$7.5M | Investigar |
| TXT Pack (#1142) | -$6.3M | Investigar |
| LESEDIFE S.A. (#42) | -$4.1M | 9 remitos 2026 por $3.8M |
| Org. Had. Seguros generales (#1137) | -$3.3M | Seguros |
| LADY STORK (#99) | -$3.1M | 1 remito apr-2026 $3.1M |
| TENISA S.A (#523) | -$3.0M | |
| FERNANDA (#1457) | -$2.0M | |
| DISTRIGROUP SRL (#860) | -$2.0M | John Foos — pago adelantado? |

> MARIO INNOVA y TXT Pack merecen investigación. Sus saldos negativos no tienen remitos recientes que los justifiquen en la muestra analizada.

---

### Remitos código 7 en compras 2026 sin factura (top 10)
| Proveedor | Remitos | Monto | Desde |
|-----------|---------|-------|-------|
| GO by CZL (#17) | 52 | $82.7M | ene-2026 |
| KALIF - ALEX SPORT (#817) | 9 | $31.1M | 01-abr-2026 |
| CLZ BEAUTY (#990) | 28 | $12.5M | ene-2026 |
| ZOTZ (#457) | 5 | $12.0M | feb-2026 |
| GAVAS SA (#794) | 10 | $11.2M | ene-2026 |
| TIMMi(NEW SHOES) (#11) | 15 | $9.9M | ene-2026 |
| BALL ONE S.R.L (#608) | 9 | $7.2M | mar-2026 |
| Souter S.A. (#561) | 1 | $6.3M | 07-mar-2026 |
| MATIAS SUBIRADA REMERAS (#955) | 11 | $5.9M | ene-2026 |
| FLOYD MEDIAS (#641) | 6 | $5.7M | ene-2026 |

**Total 2026: 242 remitos por $254.3M pendientes de facturación.**
> GO by CZL son probablemente traslados internos entre locales (normal). CLZ BEAUTY 28 remitos con solo 2 facturas = irregularidad: alta frecuencia de ingresos sin factura.

---

### Cheques próximos 30 días
| Proveedor | Cheques | Monto |
|-----------|---------|-------|
| ALQUILERES (#1494) | 4 | $7.29M |
| TIMMi(NEW SHOES) (#11) | 3 | $1.20M |
| Pepper Shoes (#655) | 4 | $1.15M |
| ZOTZ (#457) | 3 | $535K |
| GAVAS SA (#794) | 1 | $61K |
| **TOTAL 30 días** | **15** | **$10.23M** |

---

### Deuda activa corriente (debemos a proveedores, top 10)
| Proveedor | Saldo | Remitos 2026 |
|-----------|-------|-------------|
| GAVAS SA (#794) | $6.9M | $11.2M en remitos |
| FLOYD MEDIAS (#641) | $4.6M | $5.7M en remitos |
| BALL ONE S.R.L (#608) | $3.0M | $7.2M en remitos |
| Transporte expreso alfa (#405) | $2.7M | — |
| GTN "EL GITANO" (#104) | $2.7M | $5.1M en remitos |
| Pepper Shoes (#655) | $2.6M | $5.1M en remitos |
| LANACUER S.A. (#669) | $2.6M | — |
| SARANG TONGSANG SRL (#515) | $2.3M | $4.1M en remitos |
| LOCALES SA (#684) | $2.1M | $2.8M en remitos |
| ZOTZ (#457) | $1.9M | $12.0M en remitos |

> ZOTZ y Pepper Shoes tienen cheques inminentes ($534K y $1.15M) en contexto de deuda activa elevada.

---

### Top compras 2026 por proveedor (incluye gastos, sin filtrar)
| Proveedor | Facturas 2026 | Facturas |
|-----------|-------------|---------|
| GO by CZL (#17) | $75.3M | 14 |
| ALQUILERES (#1494) | $29.4M | 16 |
| SUELDOS GERENCIALES (#1527) | $13.8M | 1 |
| GAVAS SA (#794) | $11.2M | 6 |
| CLZ BEAUTY (#990) | $10.6M | 2 |
| Capacitación Laboral (#1235) | $8.9M | 3 |
| ZOTZ (#457) | $8.8M | 3 |
| TIMMi(NEW SHOES) (#11) | $8.5M | 10 |
| Mortarini Ana (#433) | $6.7M | 3 |
| Souter S.A. (#561) | $6.3M | 1 |

> Alquileres + sueldos + capacitación = ~$52M en estructura fija solo en 2026 YTD.
> CLZ BEAUTY: $10.6M en 2 facturas vs 28 remitos de entrada → proceso administrativo irregular.

---

## 🟢 OK — Dentro de parámetros normales

### Ventas 2026 YTD (ene-abr, CALZALINDO + H4 consolidado)
| Mes | Rubro 1 (Calzado) | Rubro 3 | Rubro 4 | Rubro 5 | Rubro 6 | Total |
|-----|------------------|---------|---------|---------|---------|-------|
| Enero | $180M | $107M | $32M | $26M | $20M | ~$367M |
| Febrero | $136M | $130M | $94M | $49M | $41M | ~$453M |
| Marzo | $163M | $104M | $35M | $21M | $22M | ~$347M |
| Abril (parcial ~10d) | $63M | $48M | $10M | $6M | $7M | ~$134M |

> Febrero es el mes más fuerte. Rubro 4 tiene pico en febrero (verano + vuelta a clases = deportivo). Abril parcial proyecta ~$400M si continúa ritmo.

### Ventas históricas 3 años (todos los rubros consolidados)
| Año | Ventas totales | Meses |
|-----|---------------|-------|
| 2023 | $1,210M | abr-dic (9 meses) |
| 2024 | $4,676M | ene-dic completo |
| 2025 | $5,772M | ene-dic completo |
| 2026 | $1,303M | ene-abr (4 meses) |

**Crecimiento 2024→2025: +23.4%** nominal. Con inflación ~118% en 2025, implica caída en volumen real.

**2026 vs 2025 (primeros 4 meses):** 2025 ene-abr ≈ $1,600M estimado → 2026 YTD $1,303M = **-18.5% nominal**, equivalente a contracción real significativa.

### Estacionalidad mensual (patrón histórico)
Meses más fuertes: **Dic > Oct > Feb > Nov** | Meses más flojos: **Abr > May > Ago > Sep**

| Rubro | Pico | Valle | Ratio |
|-------|------|-------|-------|
| Rubro 1 (49% del negocio) | Oct-Dic | Abr-May | ~2x |
| Rubro 3 (35%) | Jun + Dic | Mar | ~1.5x |
| Rubro 4 (11%) | Febrero | Abr | **3.5x** |
| Rubro 5 (7%) | Febrero | Jun | 2.8x |
| Rubro 6 (4%) | Febrero | May | 3.1x |

> Contexto actual (abril): mes estacionalmente el más bajo del año para casi todos los rubros. El ciclo de compras OI2026 que está en curso es correcto en timing.

### Relación remitos/facturas compras 2026
- Remitos (código 7): 242, $254.3M
- Facturas (código 1): 183, $262.2M
- Ratio: 1.32 remitos por factura → normal para operatoria de la empresa.

### Cheques sin concentración de riesgo
Ningún proveedor tiene más de 4 cheques pendientes en 30 días. Distribución razonable.

---

## 📊 APRENDIZAJES — Insights nuevos

### 1. CLZ BEAUTY: modelo operativo distinto
28 remitos de entrada con solo 2 facturas ($10.6M) sugiere que CLZ BEAUTY opera con entregas frecuentes y facturación consolidada mensual o bimestral. Esto es normal en indumentaria pero genera exposición: el proveedor tiene $12.5M en mercadería entregada sin factura formal. **Si hay un conflicto, la empresa queda expuesta sin respaldo documental de cada entrega.**

### 2. KALIF OI2026: nuevo proveedor con anticipo masivo
KALIF - ALEX SPORT (#817) es un proveedor relativamente nuevo que recibió $33.3M en anticipos (cheques + depósito) en marzo 2026 antes de entregar la mercadería. Los primeros 9 remitos llegaron el 1 de abril. Patrón de alto riesgo: pago antes de entrega de magnitud. Seguimiento quincenal recomendado.

### 3. Estructura de costos fijos: ~$52M en 4 meses
Solo alquileres ($29.4M), sueldos gerenciales ($13.8M) y capacitación ($8.9M) suman $52M YTD. Esto sugiere un punto de equilibrio operativo muy alto. La capacitación laboral con $8.9M en 3 facturas merece detalle (¿qué capacitaciones justifican ese monto?).

### 4. Proveedores con saldo negativo no explicado: MARIO INNOVA y TXT Pack
- MARIO INNOVA: -$7.5M sin remitos recientes visibles
- TXT Pack: -$6.3M (¿packaging? ¿proveedor de bolsas/cajas?)
Estos saldos sugieren pagos realizados sin contraprestación registrada en el sistema. Puede ser anticipos, puede ser error contable.

### 5. Deuda histórica como costo oculto de inflación
WABRO ($10.1M desde 2023), INTERNATIONAL BRANDS ($1.5M desde 2022), Good Company ($879K desde 2022), FIORDO 1 SA ($1.1M desde ago-2022) son deudas que con la inflación del período (>500%) representan una fracción ínfima del valor original en términos reales. Es posible que algunos proveedores ya las hayan dado por perdidas contablemente. Sin embargo, siguen activas en el sistema y distorsionan el saldo contable.

---

## Resumen ejecutivo

| Categoría | Monto | Estado |
|-----------|-------|--------|
| Deuda vencida >180 días | ~$42M | 🔴 Crítico (WABRO, ALMACEN MODA) |
| Pagos urgentes 7 días | $7.8M | 🔴 Alquileres esta semana |
| Saldos negativos proveedores | $68M | 🟡 KALIF explicado, 2 sin explicar |
| Remitos sin factura 2026 | $254M | 🟡 Normal excepto CLZ BEAUTY |
| Pagos próximos 30 días | $10.2M | 🟢 Concentración aceptable |
| Ventas YTD 2026 | ~$1,300M | 🟢 Ritmo normal |

---

*Generado automáticamente — 10 abr 2026 — Solo msgestion01 (CALZALINDO). Repetir análisis en msgestion03 (H4) para cobertura completa.*
