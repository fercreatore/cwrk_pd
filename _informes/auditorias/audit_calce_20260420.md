# Auditoría Calce Financiero — 20 de abril de 2026
**Ejecutada automáticamente** | Fuente: SQL Server 192.168.2.111 | Bases: msgestion01 (CLZ), msgestion03 (H4), msgestionC (UNION)

---

## 🔴 CRÍTICO — Acción inmediata requerida

### 1. CHEQUES QUE VENCEN HOY (20-abr)
| Empresa | Proveedor | Importe |
|---------|-----------|---------|
| H4 | Compras y Gastos Varios | $1.500.000 |
| CLZ | TXT Pack | $350.000 |
**Total hoy: $1.850.000** — verificar que están cubiertos antes del cierre bancario.

### 2. VENCIMIENTOS CRÍTICOS SEMANA (21-27 abr) — $19.9M
| Fecha | Proveedor | Importe | Empresa |
|-------|-----------|---------|---------|
| 21-abr | GLOBAL BRANDS S.A | $890.307 | H4 |
| 23-abr | INDUSTRIAS G&D S.A. | $3.542.704 | H4 |
| 23-abr | INDUSTRIAS G&D S.A. | $3.000.000 | H4 |
| 24-abr | DISTRINANDO DEPORTES | $5.000.000 | H4 |
| 24-abr | BAGUNZA SA | $3.000.000 | H4 |
| 27-abr | VICBOR SRL | $4.000.000 | H4 |
| 27-abr | KALIF - ALEX SPORT | $2.000.000 | CLZ |

⚠️ Pico del 23-abr: G&D concentra $6.54M en un solo día.
⚠️ Hay registros con importe_pesos=0 para G&D y BAGUNZA en ordpag1 — revisar si son renglones duplicados o cheques sin importe grabado.

### 3. DEUDA VENCIDA HUÉRFANA (>180 días sin cancelar) — CLZ
Estas facturas llevan meses vencidas sin movimiento en cuenta corriente. Riesgo legal y contable.

| Proveedor | Saldo pendiente | Días vencido | Alerta |
|-----------|----------------|--------------|--------|
| WABRO S.A. | $9.023.345 | **877 días** (nov-2023) | 🔴 Muy antiguo |
| LANNOT SA | $4.021.159 | 200 días | 🔴 |
| El Dante S.A. | $2.520.180 | **786 días** (feb-2024) | 🔴 |
| BEREL-K | $1.767.900 | 269 días | 🔴 |
| INTERNATIONAL BRANDS | $1.539.521 | **1.274 días** (oct-2022) | 🔴 Prescripción |
| MAQUEIRAS SHOES | $1.276.500 | **742 días** | 🔴 |
| SUELAS LEAL S.A. | $1.228.880 | 223 días | 🔴 |
| PIRA SRL | $1.055.700 + $852.915 | 206-280 días | 🔴 |
| ALMACEN DE MODA | $942.877 + $791.794 + $762.300 | 597-625 días | 🔴 |
| FIORDO 1 SA | $888.050 | **892 días** | 🔴 |

**Acción requerida**: revisar con administración si estas deudas están en disputa, fueron saldadas por otro medio, o corresponde un ajuste/baja contable. INTERNATIONAL BRANDS lleva 3.5 años — posible prescripción.

### 4. CAÍDA DE VENTAS YoY SOSTENIDA — 3 MESES CONSECUTIVOS
| Mes | 2025 | 2026 | Variación |
|-----|------|------|-----------|
| Enero | $483.7M | $389.9M | **-19%** |
| Febrero | $572.5M | $480.3M | **-16%** |
| Marzo | $463.2M | $364.5M | **-21%** |
| Abril (parcial) | $435.5M completo | $301.7M (≈20 días) | tendencia -30% |

Tres meses consecutivos con caída del 16-21% vs año anterior. Abril proyecta continuar la tendencia. **Esto afecta directamente la capacidad de pago de los $98.5M comprometidos en cheques a 30 días.**

---

## 🟡 ATENCIÓN — Monitorear

### 5. COMPROMISO TOTAL CHEQUES 30 DÍAS — $98.5M
| Empresa | Cheques | Total | Vence hasta |
|---------|---------|-------|-------------|
| CLZ | 12 | $15.970.760 | 15-mayo |
| H4 | 55 | $82.494.962 | 20-mayo |
| **TOTAL** | **67** | **$98.465.722** | |

Concentración alta en H4. Los 3 primeros proveedores por cheques en H4:
- VICBOR: 13 cheques → $44.1M
- DISTRINANDO MODA: 14 cheques → $36.4M
- DISTRINANDO DEPORTES: 10 cheques → $35.2M

Solo estos 3 representan $115.7M en obligaciones futuras.

### 6. SALDOS NEGATIVOS ANÓMALOS H4 (ellos nos deben o notas de crédito sin aplicar)
Proveedores con saldo negativo en moviprov1 H4 (deberían pagarnos):
| Proveedor | Saldo a nuestro favor | Nota |
|-----------|----------------------|------|
| DISTRINANDO DEPORTES | $20.375.685 | Contradictorio: también tienen 10 cheques nuestros por $35.2M pendientes |
| A NATION | $9.332.908 | ¿Proveedor activo? |
| MERCADO LIBRE | $6.854.688 | ¿Comisiones pre-pagadas? |
| TECAL Cavatini | $6.690.341 | |
| COMPRANDO EN GRUPO | $4.230.977 | |
| Baudracco | $3.843.806 | |
| GO Servicios Digitales | $3.004.585 | |
| RAPICUOTAS | $2.240.889 | |

DISTRINANDO DEPORTES es el caso más llamativo: nos deben $20.4M según moviprov1 pero a su vez tenemos $35.2M en cheques para pagarles. Puede haber facturación cruzada legítima, pero requiere verificación.

### 7. SALDOS NEGATIVOS CLZ (nos deben) — Algunos son gastos/no-proveedores
| Proveedor | Saldo | Observación |
|-----------|-------|-------------|
| MARIO INNOVA | $7.456.060 | Verificar si fue pagado por otro medio |
| BEREL-K | $4.500.000 | También tiene deuda huérfana $1.77M |
| Org. Had. Seguros | $4.404.336 | Seguros: puede ser anticipo |
| LESEDIFE S.A. | $4.063.546 | En H4 le debemos $7.87M — inconsistencia entre bases |
| TENISA S.A | $2.967.800 | |

### 8. REMITO SIN FACTURAR >60 DÍAS
| Empresa | Proveedor | Monto | Días |
|---------|-----------|-------|------|
| CLZ | MATIAS OSCAR SUBIRADA (REMERAS) | $240.000 | **107 días** |
| CLZ | GO by CZL | $874.000 | 70 días |

GO by CZL (valijas) con $874k sin facturar a 70 días merece seguimiento. El de SUBIRADA con 107 días es un outlier administrativo.

### 9. COMPARACIÓN COMPRAS 2025 vs 2026 — Ritmo acelerado
Top H4 (ene-abr-2026 vs todo 2025):
| Proveedor | 2025 completo | 2026 YTD (≈4 meses) | Ritmo 2026 anualizado |
|-----------|--------------|---------------------|----------------------|
| ALPARGATAS | $225.1M | $68.3M | $205M/año |
| VICBOR | $186.6M | $37.0M | $111M/año (↘) |
| GRIMOLDI | $117.6M | $17.7M | $53M/año (↘↘) |
| DISTRINANDO MODA | $106.3M | $22.2M | $66M/año (↘) |
| DISTRINANDO DEPORTES | $81.4M | $47.9M | **$144M/año (↑↑)** |
| INDUSTRIAS G&D | N/A top | $24.8M | $74M/año (nuevo) |

DISTRINANDO DEPORTES está creciendo fuertemente vs 2025. GRIMOLDI cayó marcadamente.

---

## 🟢 OK — Dentro de parámetros

### 10. DEUDA LEGÍTIMA CON PROVEEDORES COMERCIALES H4
Saldos razonables con los proveedores principales, alineados a volumen de compras:
| Proveedor | Deuda | Compras 2025 |
|-----------|-------|-------------|
| ALPARGATAS | $41.1M | $225M ✓ |
| INDUSTRIAS G&D | $15.3M | (nuevo 2026) ✓ |
| VICBOR | $15.3M | $186M ✓ |
| PRIMER ROUND | $9.8M | $40.6M ✓ |

### 11. REMITOS H4 SIN FACTURAR 2026
Solo 1 remito encontrado: VICBOR $304k a 55 días (dentro del límite de 60 días). Estado OK.

### 12. ESTACIONALIDAD — Patrón histórico confirmado
El patrón bianual se mantiene consistente:
- **Pico 1**: dic (fiestas/verano) — dic-2024 $748M, dic-2025 $720M
- **Pico 2**: oct-nov (primavera) — oct-2024 $594M, oct-2025 $581M
- **Valle 1**: ene-feb (post-verano) — promedio $480-530M
- **Valle 2**: mar-abr (otoño) — promedio $400-460M

La diferencia 2026 vs 2025 en ene-mar (-16 a -21%) excede la variación estacional normal, confirmando que hay un componente real de desaceleración, no solo efecto base.

---

## 📊 APRENDIZAJE — Insights nuevos

### A. LESEDIFE: inconsistencia entre bases
En CLZ (moviprov1 base 01) aparece con saldo -$4.06M (nos deben), mientras en H4 le debemos $7.87M. Dado que es el mismo proveedor físico, esto sugiere que opera con ambas empresas y los saldos son independientes por base. El neto real podría ser positivo ($3.81M a su favor). Verificar consolidado.

### B. Compras CLZ dominadas por intercompany y gastos
El top 2 de CLZ 2026 son:
1. Shoeholic ($81.8M en 1 factura) — ¿es un proveedor externo o intercompany?
2. GO by CZL ($75.3M, 14 facturas) — son las valijas, intercompany

Esto significa que el mayor volumen de compras CLZ son transacciones internas, no mercadería nueva. Para el análisis de margen real hay que netear esto.

### C. MERCADO LIBRE aparece como proveedor con $106.5M en compras 2025 y $29M en 2026 H4
ML está siendo contabilizado en ambas bases como proveedor. Probablemente son las comisiones/logística. Con -$6.85M de saldo negativo en H4 sugiere pagos anticipados o créditos no aplicados con ML.

### D. Banco MACRO como proveedor: $8.8M en 1 factura 2026 (H4)
Los bancos aparecen como proveedores (Macro, Credicoop, BNA en 2025 con $91.6M). Son productos financieros / cuotas de préstamos. Hay que excluirlos de los análisis de margen bruto del negocio.

### E. Tendencia ventas 2026: ajuste real o inflación vs volumen?
Las ventas caen -16 a -21% nominalmente. Dado el contexto inflacionario argentino, una caída nominal sugiere caída en volumen de pares de entre -25 y -35%. Cruzar con vel_real_articulo para confirmación.

---

## RESUMEN EJECUTIVO

| Área | Estado | Monto en riesgo |
|------|--------|-----------------|
| Cheques próx. 30 días | 🟡 Alto pero planificado | $98.5M |
| Deuda vencida huérfana | 🔴 Acción requerida | >$25M acumulado |
| Caída ventas YoY | 🔴 Monitoreo urgente | -$100M+/mes vs año pasado |
| Cheques HOY | 🔴 Inmediato | $1.85M |
| Remitos sin facturar >60d | 🟡 Administrativo | $1.1M |
| Concentración cheques | 🟡 3 proveedores = $115M | Ver nota 5 |

**Próximos pasos sugeridos:**
1. Confirmar cobertura bancaria para HOY y para el 23-abr ($6.54M G&D)
2. Revisar las deudas huérfanas con administración — especialmente WABRO ($9M, 877 días) e INTERNATIONAL BRANDS ($1.5M, 1274 días)
3. Cruzar caída de ventas con vel_real para determinar si es nominal (inflación) o volumétrica
4. Investigar DISTRINANDO DEPORTES: saldo contradictorio (-$20M en moviprov1 vs $35.2M en cheques pendientes)
5. Regularizar remito SUBIRADA REMERAS (107 días sin facturar)

---
*Generado automáticamente el 2026-04-20 por calce-financiero-audit*
*Consultas: msgestion01.dbo.moviprov1, ordpag1, compras2 | msgestion03.dbo.moviprov1, ordpag1, compras2 | msgestionC.dbo.ventas2*
