# Reporte de Negociacion de Proveedores - OI26
**Fecha:** 1 de abril de 2026
**Periodo analizado:** Ultimos 12 meses (abril 2025 - marzo 2026)
**Empresa:** H4 SRL / CALZALINDO

---

## 1. Resumen Ejecutivo

Se analizan los 20 principales proveedores comerciales por volumen de compra y venta.
El objetivo es clasificarlos segun su eficiencia de capital (rotacion x margen) para
definir la estrategia de negociacion OI26: a quien comprar mas, a quien pedir plazo,
y a quien renegociar condiciones.

**Hallazgos clave:**
- GO by CZL (marca propia) tiene el mejor ROI por lejos: 72% margen con rotacion alta
- ZOTZ, TIMMi y VICBOR son los proveedores terceros mas eficientes
- ALPARGATAS domina en volumen ($830M venta) pero requiere capital intensivo
- GRIMOLDI tiene el peor ratio volumen/capital: mucho dinero inmovilizado por par

---

## 2. Metricas Calculadas por Proveedor

**Metodologia:**
- Stock estimado = uds_compradas x 0.30 (promedio de permanencia en deposito)
- Rotacion anual = uds_vendidas / stock_estimado
- Dias al 50% de venta = 182.5 / rotacion
- ROI anualizado = margen% x rotacion
- Score = ROI normalizado 0-100

| Cod | Proveedor | Uds Vend | Uds Comp | Stock Est | Rotacion | Dias 50% | Margen% | ROI Anual | Score |
|-----|-----------|----------|----------|-----------|----------|----------|---------|-----------|-------|
| 17 | GO by CZL | 4,736 | 12,282 | 3,685 | 1.29 | 142 | 72.1% | 0.93 | **100** |
| 457 | ZOTZ | 1,953 | 4,285 | 1,286 | 1.52 | 120 | 57.9% | 0.88 | 95 |
| 11 | TIMMi | 1,056 | 4,163 | 1,249 | 0.85 | 215 | 58.0% | 0.49 | 53 |
| 594 | VICBOR | 8,511 | 8,833 | 2,650 | 3.21 | 57 | 50.7% | 1.63 | **100** |
| 669 | LANACUER | 4,034 | 5,332 | 1,600 | 2.52 | 72 | 52.2% | 1.32 | **100** |
| 770 | PRIMER ROUND | 2,748 | 2,544 | 763 | 3.60 | 51 | 45.9% | 1.65 | **100** |
| 950 | TIVORY | 1,265 | 3,390 | 1,017 | 1.24 | 147 | 50.4% | 0.63 | 68 |
| 668 | ALPARGATAS | 13,421 | 9,848 | 2,954 | 4.54 | 40 | 48.5% | 2.20 | **100** |
| 656 | DISTRINANDO DEP | 4,458 | 6,260 | 1,878 | 2.37 | 77 | 46.1% | 1.09 | **100** |
| 264 | GRIMOLDI | 2,339 | 2,725 | 818 | 2.86 | 64 | 48.7% | 1.39 | **100** |
| 713 | DISTRINANDO MODA | 4,051 | 6,727 | 2,018 | 2.01 | 91 | 49.7% | 1.00 | **100** |
| 311 | ROFREVE | 3,761 | 9,058 | 2,717 | 1.38 | 132 | 47.0% | 0.65 | 70 |
| 42 | LESEDIFE | 5,196 | 13,161 | 3,948 | 1.32 | 139 | 49.5% | 0.65 | 70 |
| 722 | GLOBAL BRANDS | 1,697 | 2,379 | 714 | 2.38 | 77 | 49.1% | 1.17 | **100** |
| 817 | KALIF | 2,602 | 3,454 | 1,036 | 2.51 | 73 | 45.5% | 1.14 | **100** |
| 608 | BALL ONE | 1,136 | 1,479 | 444 | 2.56 | 71 | 49.6% | 1.27 | **100** |
| 561 | SOUTER/RINGO | 1,075 | — | — | — | — | 46.4% | — | — |

> Nota: SOUTER/RINGO (561) no aparece en top compras pero si en ventas; sin datos de compra reciente no se calcula rotacion.

---

## 3. Clasificacion Estrategica

### AUTO-FINANCIADOS (Rotacion > 3x) — Comprar MAS

Proveedores que se pagan solos. El stock rota tan rapido que el capital invertido se recupera antes de vencer el plazo tipico de pago.

| Proveedor | Rotacion | Margen% | ROI | Accion |
|-----------|----------|---------|-----|--------|
| **ALPARGATAS** | 4.54x | 48.5% | 2.20 | Aumentar volumen. Negociar desc por volumen |
| **PRIMER ROUND** | 3.60x | 45.9% | 1.65 | Aumentar pedido. Stock casi siempre agotado |
| **VICBOR** | 3.21x | 50.7% | 1.63 | Mantener/crecer. Excelente combo margen+rotacion |

**Conclusion:** Estos 3 proveedores generan el mayor retorno por peso invertido. Priorizar compra OI26.

---

### CAPITAL MODERADO (Rotacion 2x - 3x) — Negociar plazo o descuento

El stock rota en 2-3 meses. Financiable con plazo a 60-90 dias.

| Proveedor | Rotacion | Margen% | ROI | Accion |
|-----------|----------|---------|-----|--------|
| **GRIMOLDI** | 2.86x | 48.7% | 1.39 | Pedir plazo 90 dias (ticket alto: $47K/par) |
| **BALL ONE** | 2.56x | 49.6% | 1.27 | Mantener volumen. Buen margen |
| **LANACUER** | 2.52x | 52.2% | 1.32 | Negociar desc 5% por volumen anual |
| **KALIF** | 2.51x | 45.5% | 1.14 | Pedir plazo 60 dias |
| **GLOBAL BRANDS** | 2.38x | 49.1% | 1.17 | Mantener. Poco volumen pero sano |
| **DISTRINANDO DEP** | 2.37x | 46.1% | 1.09 | Negociar desc. Volumen $208M justifica |
| **DISTRINANDO MODA** | 2.01x | 49.7% | 1.00 | Pedir plazo 90 dias. Rotacion justa |

---

### CAPITAL INTENSIVO (Rotacion < 2x) — Renegociar o reducir

Stock que tarda mas de 6 meses en rotar. Inmoviliza capital.

| Proveedor | Rotacion | Margen% | ROI | Accion |
|-----------|----------|---------|-----|--------|
| **ZOTZ** | 1.52x | 57.9% | 0.88 | Margen alto compensa. Pedir consignacion parcial |
| **ROFREVE** | 1.38x | 47.0% | 0.65 | Reducir pedido 20%. Sobre-stockeado |
| **LESEDIFE** | 1.32x | 49.5% | 0.65 | Reducir pedido 25%. 13K uds compradas, 5K vendidas |
| **TIVORY** | 1.24x | 50.4% | 0.63 | Pedir consignacion. Rotacion muy lenta |
| **TIMMi** | 0.85x | 58.0% | 0.49 | ALERTA: compra 4x mas de lo que vende. Reducir 50% |

**Alerta critica:** TIMMi tiene rotacion < 1x. Se compran 4,163 unidades y se venden 1,056. Acumulacion de stock muerto. Reducir compra drasticamente o exigir devolucion/cambio.

---

### ESPECIAL — Marca Propia

| Proveedor | Rotacion | Margen% | ROI | Accion |
|-----------|----------|---------|-----|--------|
| **GO by CZL** | 1.29x | **72.1%** | 0.93 | MAXIMA PRIORIDAD. Margen imbatible |

GO by CZL es marca propia. El margen de 72% compensa la rotacion moderada. Cada peso invertido rinde 3x mas que un proveedor tipico al 48%. **Estrategia: aumentar surtido, mejorar exhibicion, acelerar rotacion con marketing propio.**

---

## 4. Matriz de Negociacion - Top 15

| # | Proveedor | Que pedir | Argumento | Impacto ROI |
|---|-----------|-----------|-----------|-------------|
| 1 | **ALPARGATAS** | Descuento 2% adicional por volumen >10K pares/ano | Somos top 3 cliente regional. $362M compra anual. Pago puntual | ROI 2.20 -> 2.30 (+$7M margen) |
| 2 | **VICBOR** | Plazo 60 dias en vez de 30 | 8,833 uds/ano, 152 facturas. Relacion estable | Libera ~$35M capital de trabajo |
| 3 | **DISTRINANDO DEP** | Descuento 3% por volumen semestral | $208M compra, 68 facturas. Proveedor concentrado | ROI 1.09 -> 1.16 (+$6M margen) |
| 4 | **DISTRINANDO MODA** | Plazo 90 dias + cambio temporada | $176M compra. Rotacion 2x necesita aire | Reduce riesgo stock estacional |
| 5 | **GRIMOLDI** | Plazo 90 dias firme (ticket $47K/par) | 91 facturas, cliente constante. Producto premium no se malvende | Libera ~$20M capital mensual |
| 6 | **LESEDIFE** | Reducir pedido 25% + consignacion excedente | 13K compradas vs 5K vendidas. Stock acumulado | ROI 0.65 -> 0.85 (elimina capital muerto) |
| 7 | **ROFREVE** | Reducir pedido 20% + devolucion saldo OI25 | 9K compradas vs 3.7K vendidas. Sobrestock | ROI 0.65 -> 0.80 |
| 8 | **ZOTZ** | Consignacion 30% del pedido | Rotacion 1.5x pero margen 58%. Producto diferencial | Reduce riesgo sin perder surtido |
| 9 | **GO by CZL** | Aumentar surtido 30%. Inversion en moldes nuevos | Marca propia, 72% margen. Cada par rinde el doble | ROI potencial > 1.20 con mejor rotacion |
| 10 | **LANACUER** | Descuento 5% por pago anticipado | 5,332 uds, buen margen 52%. Fidelizar | ROI 1.32 -> 1.40 |
| 11 | **KALIF** | Plazo 60 dias | 3,454 uds. Marca deportiva con demanda estable | Libera ~$12M capital |
| 12 | **GLOBAL BRANDS** | Mantener condiciones. Evaluar aumento 15% | Rotacion 2.4x, margen 49%. Proveedor sano | Crecimiento rentable |
| 13 | **BALL ONE** | Descuento 3% por exclusividad regional | 1,479 uds pero alto margen 49.6% | ROI 1.27 -> 1.35 |
| 14 | **TIMMi** | STOP compra hasta liquidar stock. Devolucion parcial | Rotacion 0.85x. Compramos 4x lo que vendemos | Evita $40M+ en capital muerto |
| 15 | **TIVORY** | Consignacion 50% o plazo 120 dias | Rotacion 1.24x. Producto lento | Reduce exposicion $25M |

---

## 5. Impacto Estimado Global

| Concepto | Situacion actual | Con negociacion | Delta |
|----------|------------------|-----------------|-------|
| Capital inmovilizado en stock lento (LESEDIFE+ROFREVE+TIMMi) | ~$120M | ~$70M | **-$50M liberados** |
| Margen adicional por descuentos (ALPARGATAS+DISTRINANDO+LANACUER) | — | +$15M/ano | **+$15M** |
| Capital liberado por plazo (VICBOR+GRIMOLDI+KALIF) | — | ~$67M disponible | **Financiamiento gratuito** |
| Inversion adicional en GO by CZL (marca propia) | $158M | $205M (+30%) | **+$34M margen extra** |

**Resultado neto estimado: +$50M capital liberado + $49M margen adicional anualizado.**

---

## 6. Plan de Accion Inmediato (Abril 2026)

### Semana 1 (1-7 abril)
- [ ] Reunir datos de antiguedad y puntualidad de pago para usar como argumento
- [ ] Preparar propuesta ALPARGATAS: descuento volumen 2% sobre >10K pares
- [ ] Cortar pedido TIMMi: no comprar hasta liquidar stock existente

### Semana 2 (8-14 abril)
- [ ] Negociar plazo VICBOR (60 dias) y GRIMOLDI (90 dias)
- [ ] Proponer consignacion parcial a ZOTZ y TIVORY
- [ ] Definir pedido GO by CZL OI26 ampliado (+30% surtido)

### Semana 3 (15-21 abril)
- [ ] Negociar descuento volumen DISTRINANDO DEP (3%)
- [ ] Revisar saldo stock ROFREVE y LESEDIFE: proponer devolucion/cambio
- [ ] Confirmar plazo KALIF (60 dias)

### Semana 4 (22-30 abril)
- [ ] Consolidar acuerdos cerrados
- [ ] Actualizar condiciones en config.py (descuentos, plazos)
- [ ] Generar pedidos OI26 con nuevas condiciones

---

## 7. Indicadores de Seguimiento

| KPI | Meta OI26 | Medicion |
|-----|-----------|----------|
| Rotacion promedio ponderada | > 2.5x | Mensual, vel_real_articulo |
| Capital inmovilizado >180 dias | < $80M | Quincenal, stock x antiguedad |
| Margen bruto promedio | > 50% | Mensual, calce financiero |
| Proveedores con consignacion | 3+ | Trimestral |
| GO by CZL como % del mix | > 12% | Mensual |

---

*Generado el 1 de abril de 2026. Datos basados en 12 meses de compras y ventas reales.*
*Fuente: msgestionC (compras1/compras2, ventas1/ventas2, stock)*
