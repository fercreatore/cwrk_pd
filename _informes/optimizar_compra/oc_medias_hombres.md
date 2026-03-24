# Optimizacion Presupuesto OI26 — MEDIAS HOMBRES (rubro=3, subrubro=29)
> Generado: 23 de marzo de 2026
> Fuente: msgestionC (ventas1/compras1/stock), msgestion01art (articulo)

---

## Metodologia

1. **Familias**: agrupadas por `LEFT(codigo_sinonimo, 8)`
2. **Ventas OI**: abril-septiembre de cada ano (6 meses OI)
3. **Analisis de quiebre**: reconstruccion de stock mes a mes hacia atras (abr-2025 a mar-2026). Meses con stock inicio <= 0 marcados como QUEBRADOS y excluidos del calculo de velocidad
4. **vel_real**: ventas solo de meses NO quebrados / cant meses NO quebrados (nota: tabla `omicronvt.dbo.vel_real_articulo` NO existe en produccion, calculo manual)
5. **Factor crecimiento OI25 vs OI24**: 1.20x conservador (mediana observada en familias sanas ~1.3-1.6x)
6. **Demanda OI26** = vel_real_OI_mensual x 6 meses x 1.20
7. **Necesidad** = demanda_OI26 - stock_actual (si < 0, no se compra)
8. **ROI** = (precio_venta - costo) / costo (el factor `necesidad` se cancela en numerador/denominador)

---

## Analisis de Quiebre por Familia (TOP 15)

| Familia | Descripcion | Meses quebrados OI25 | Efecto |
|---------|-------------|---------------------|--------|
| 51500102 | Soquete Liso Hombre | Jul(63u), Ago(19u) suprimidos | vel_real 190/mes vs aparente 140/mes |
| 51513102 | Soquete Deportivo Hombre | Sep(18u) suprimido | vel_real 140/mes vs aparente 116/mes |
| 51510402 | Media 1/3 Lisa | Jul(0), Ago(0) QUEBRADO total | **vel_real 117/mes vs aparente 64/mes (+83%)** |
| 51511950 | Media 1/2 Cana Estampa | Jun(1u) QUEBRADO | vel_real 60/mes vs aparente 51/mes |
| 51501023 | Soquete x3 Pack | Ago(6), Sep(1) QUEBRADO | **vel_real 66/mes vs aparente 26/mes (+154%)** |
| 64114180 | Media Termica Lisa | Ago(11), Sep(0) QUEBRADO | **vel_real 31/mes vs aparente 23/mes (+39%)** |
| 641GO440 | Soq Dep Dual Power | Abr(1), May(6), Jun(0) QUEBRADO | **vel_real 27/mes vs aparente 15/mes (+80%)** |
| 641CL090 | Media Vestir Lisa Soft | Abr(0), May(0) sin stock | vel_real 41/mes (desde Jun) |
| 51511402 | Media 1/3 Estampa | Sin quiebre significativo | vel_real = aparente 104/mes |
| 51511912 | Media 1/2 Cana Lisa | Sin quiebre significativo | vel_real = aparente 87/mes |
| 64114140 | Soquete Corto Liso | Sin quiebre significativo | vel_real = aparente 44/mes |
| 64114120 | Soq Tobillera Hombre | Leve Jul(14) | vel_real ~37/mes |
| 641GO470 | Media 1/4 Invencible | Sin quiebre OI | vel_real = aparente 26/mes |
| 641GO444 | Soq Dep Foot Boost | Sin quiebre OI | vel_real = aparente 25/mes |
| 641GO410 | Soq Dep Ultimate Float | Sin quiebre OI | vel_real = aparente 19/mes |

---

## Ranking por ROI y Asignacion Optima

### TIER 1 — ROI ~164% (margen alto, prioridad maxima)

| # | Familia | Descripcion | OI24 | OI25 | vel_real_OI | Demanda OI26 | Stock | Necesidad | Costo/u | Inversion | ROI% |
|---|---------|-------------|------|------|-------------|-------------|-------|-----------|---------|-----------|------|
| 1 | 51501102 | Soq Rayado Hombre | 231 | 263 | 263 | 316 | 25 | 291 | $1,127 | $327,957 | 164% |
| 2 | 51513102 | Soq Deportivo Hombre | 442 | 698 | 838* | 1,006 | 127 | 879 | $1,128 | $991,512 | 164% |
| 3 | 51500102 | Soq Liso Hombre | 496 | 842 | 842 | 1,010 | 190 | 820 | $1,128 | $924,960 | 164% |
| 4 | 51511912 | Media 1/2 Cana Lisa | 178 | 519 | 519 | 623 | 181 | 442 | $1,557 | $688,194 | 164% |
| 5 | 51511402 | Media 1/3 Estampa | 265 | 623 | 623 | 748 | 237 | 511 | $1,452 | $741,972 | 164% |
| | | | | | | **Subtotal TIER 1** | | **2,943** | | **$3,674,595** | |

*\* vel_real ajustada por quiebre Sep*

### TIER 2 — ROI ~120% (margen estandar, alta rotacion)

| # | Familia | Descripcion | OI24 | OI25 | vel_real_OI | Demanda OI26 | Stock | Necesidad | Costo/u | Inversion | ROI% |
|---|---------|-------------|------|------|-------------|-------------|-------|-----------|---------|-----------|------|
| 6 | 51510402 | Media 1/3 Lisa | 399 | 385 | 704* | 845 | 43 | 802 | $1,742 | $1,397,084 | 120% |
| 7 | 51511950 | Media 1/2 Estampa | 232 | 303 | 362* | 435 | 41 | 394 | $1,868 | $735,992 | 120% |
| 8 | 51501023 | Soquete x3 Pack | 88 | 153 | 396* | 475 | 157 | 318 | $3,856 | $1,226,208 | 120% |
| 9 | 51511953 | Soq Alto Liso | 327 | 238 | 282 | 282 | 15 | 267 | $1,481 | $395,427 | 120% |
| 10 | 64114140 | Soq Corto Liso | 238 | 262 | 262 | 314 | 109 | 205 | $1,175 | $240,875 | 120% |
| 11 | 64114120 | Soq Tobillera | 167 | 205 | 224* | 269 | 65 | 204 | $1,231 | $251,124 | 120% |
| 12 | 641GO440 | Soq Dual Power | 56 | 88 | 162* | 194 | 39 | 155 | $1,251 | $193,905 | 120% |
| 13 | 641CL090 | Vestir Lisa Soft | 5 | 162 | 162 | 194 | 40 | 154 | $1,224 | $188,496 | 120% |
| 14 | 64114180 | Media Termica Lisa | 42 | 136 | 188* | 225 | 77 | 148 | $2,349 | $347,652 | 120% |
| 15 | 641GO444 | Soq Foot Boost | 71 | 149 | 149 | 179 | 60 | 119 | $1,251 | $148,869 | 120% |
| 16 | 64114200 | Media Casual 2 Rayas | 39 | 108 | 108 | 130 | 21 | 109 | $1,625 | $177,125 | 120% |
| 17 | 641GO410 | Soq Ultimate Float | 39 | 113 | 113 | 136 | 39 | 97 | $1,251 | $121,347 | 120% |
| 18 | 641GO470 | Media Invencible | 103 | 158 | 158 | 190 | 103 | 87 | $1,710 | $148,770 | 120% |
| 19 | 641GO481 | Media Prolite Crew | 20 | 73 | 73 | 88 | 15 | 73 | $2,120 | $154,760 | 98% |
| 20 | 64114080 | Media Toalla c/Puno | 0 | 105 | 105 | 126 | 61 | 65 | $2,111 | $137,215 | 120% |
| | | | | | | **Subtotal TIER 2** | | **3,242** | | **$5,864,849** | |

*\* vel_real ajustada por quiebre — demanda real significativamente mayor a la aparente*

### TIER 3 — Complementarios (menor volumen)

| # | Familia | Descripcion | Demanda OI26 | Stock | Necesidad | Costo/u | Inversion | ROI% |
|---|---------|-------------|-------------|-------|-----------|---------|-----------|------|
| 21 | 64114230 | Media Lisa 1/3 | 89 | 33 | 56 | $1,466 | $82,096 | 120% |
| 22 | 641GO441 | Soq Air Cross | 86 | 33 | 53 | $1,251 | $66,303 | 120% |
| 23 | 641GO472 | Soq Sporty Camo | 62 | 13 | 49 | $1,458 | $71,442 | 120% |
| 24 | 64114130 | Soq Corto Estampado | 76 | 29 | 47 | $1,224 | $57,528 | 120% |
| 25 | 64114240 | Media Casual 1/3 | 74 | 2 | 72 | $1,472 | $105,984 | 120% |
| | | | **Subtotal TIER 3** | | **277** | | **$383,353** | |

---

## Resumen de Inversion Total

| Tier | Unidades | Inversion | ROI | Descripcion |
|------|----------|-----------|-----|-------------|
| TIER 1 | 2,943 | **$3,674,595** | 164% | Soquetes y medias marca 515 (mayor margen) |
| TIER 2 | 3,242 | **$5,864,849** | 120% | Mix completo alta rotacion |
| TIER 3 | 277 | **$383,353** | 120% | Complementarios |
| **TOTAL** | **6,462** | **$9,922,797** | **~140%** | |

---

## Recomendacion de Asignacion por Presupuesto

> **Nota**: El presupuesto indicado fue "M, M, M y M" (valores no especificados). A continuacion se presenta la asignacion optima por prioridad de ROI.

### Escenario A: Presupuesto $4M
| Prioridad | Familias | Inversion | Pares |
|-----------|----------|-----------|-------|
| 1ro | 51501102 + 51513102 + 51500102 | $2,244,429 | 1,990 |
| 2do | 51511912 + 51511402 | $1,430,166 | 953 |
| Remanente $325k | 64114140 + 641CL090 | $429,371 | 359 |
| **Total** | | **$4,103,966** | **3,302** |

### Escenario B: Presupuesto $6M
Todo TIER 1 ($3.67M) + mejores de TIER 2:
| Prioridad | Familias | Inversion | Pares |
|-----------|----------|-----------|-------|
| TIER 1 completo | 5 familias | $3,674,595 | 2,943 |
| + 51510402 (quiebre masivo) | Media 1/3 Lisa | $1,397,084 | 802 |
| + 51511950 | Media 1/2 Estampa | $735,992 | 394 |
| **Total** | | **$5,807,671** | **4,139** |

### Escenario C: Presupuesto $10M (cobertura total)
TIER 1 + TIER 2 + TIER 3 = $9.9M → 6,462 pares, cobertura completa OI26.

---

## Familias Criticas con Quiebre Severo

Estas familias tienen demanda real MUY superior a la aparente. Subcomprar = perder ventas:

| Familia | Descripcion | vel_aparente/mes | vel_real/mes | Diferencia | Venta perdida OI25 estimada |
|---------|-------------|-----------------|-------------|------------|----------------------------|
| **51510402** | Media 1/3 Lisa | 64 | 117 | **+83%** | ~318 pares |
| **51501023** | Soquete x3 Pack | 26 | 66 | **+154%** | ~240 packs |
| **641GO440** | Soq Dual Power | 15 | 27 | **+80%** | ~72 pares |
| **64114180** | Media Termica | 23 | 31 | **+39%** | ~48 pares |

**Recomendacion**: estas 4 familias deben tener stock garantizado al inicio de OI26 (abr). Comprar ANTES de que arranque la temporada.

---

## Notas Tecnicas

- `vel_real_articulo` de omicronvt NO existe en produccion (pendiente deploy del SQL generado 21-mar)
- Calculo de quiebre realizado manualmente con ventas/compras mensuales abr25-mar26
- Factor estacional OI ya incorporado (datos base son de periodos OI exclusivamente)
- Precios y costos al 23-mar-2026 (pueden variar con listas nuevas de proveedores)
- Excluidas marcas 1316, 1317, 1158, 436 (gastos) y codigos venta 7/36 (remitos internos)
