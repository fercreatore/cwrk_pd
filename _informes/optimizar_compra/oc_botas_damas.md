# Optimización Presupuesto OI26 — BOTAS DAMAS
> Rubro 1, Subrubro 15 | Generado: 2026-03-23 21:02
> Fuente: vel_real_articulo (con análisis de quiebre), ventas OI24/OI25, stock actual

---

## Resumen Ejecutivo

| Indicador | Valor |
|-----------|-------|
| Familias analizadas | 124 |
| Pares necesarios (demanda - stock) | 5,603 |
| Inversión total requerida | $198,127,536 |
| Margen bruto proyectado | $198,340,913 |
| ROI promedio | 100% |
| Costo promedio por par | $35,361 |
| Top 30 familias concentran | 35% de pares, 44% de inversión |

### Metodología
1. **Velocidad real** de `omicronvt.dbo.vel_real_articulo` (corregida por quiebre de stock)
2. **Demanda OI26** = promedio ventas OI24+OI25 * factor_quiebre (cap 3x). Si solo hay datos de 1 temporada, se usa esa.
3. **Necesidad** = demanda_OI26 - stock_actual (mínimo 0)
4. **Factor estacional**: BOTAS es categoría **puramente OI** — toda la demanda se concentra en abr-sep. No se aplica factor adicional porque vel_real ya contempla los meses sin venta (quedan como "quebrados" en el factor).
5. **ROI** = (PVP - Costo) / Costo

---

## Top 30 Familias por Potencial de Margen

| # | Familia | Nombre | OI24 | OI25 | VelReal | FQ | Stk | Demanda | Necesidad | Costo/par | PVP | Inversión | Margen | Mg% |
|---|---------|--------|------|------|---------|-----|-----|---------|-----------|-----------|-----|-----------|--------|-----|
| 1 | 2250 | 2250 T/GOND 2 CIERRES COST | 37 | 48 | 10.5 | 3.7 | 17 | 128 | 110 | $57,047 | $113,581 | $6,303,680 | $6,218,740 | 49.8% |
| 2 | 735031 | 735031 BOTA BAJA 1 CIERRE DE | 0 | 32 | 15.7 | 6.4 | 1 | 96 | 95 | $50,000 | $99,999 | $4,749,952 | $4,749,905 | 50.0% |
| 3 | BETHANY | BETHANY BOTA CORTA 2 CIERRES | 0 | 49 | 9.5 | 2.0 | 18 | 100 | 82 | $48,047 | $103,650 | $3,946,628 | $4,559,446 | 53.6% |
| 4 | SNOWY | SNOWY  PANTUBOTA CORTA INT P | 0 | 36 | 10.6 | 4.3 | 3 | 108 | 105 | $39,900 | $79,800 | $4,189,500 | $4,189,500 | 50.0% |
| 5 | AGOSTINA | AGOSTINA  BOTA CAÑA ALTA DET | 0 | 16 | 4.4 | 3.3 | 4 | 48 | 44 | $82,604 | $165,208 | $3,634,576 | $3,634,576 | 50.0% |
| 6 | JOYCE | JOYCE BOTA T/ SEP 1 CIERRE D | 0 | 33 | 7.9 | 4.0 | 2 | 99 | 97 | $36,441 | $72,882 | $3,534,777 | $3,534,777 | 50.0% |
| 7 | MEGAN | MEGAN BOTA T/S FOLIA DET TAL | 0 | 25 | 8.6 | 5.1 | 3 | 75 | 72 | $48,990 | $97,980 | $3,527,280 | $3,527,280 | 50.0% |
| 8 | FINI | FINI BOTA T/S DOBLE CIERRE  | 0 | 18 | 8.4 | 6.1 | 0 | 54 | 54 | $58,800 | $117,600 | $3,175,200 | $3,175,200 | 50.0% |
| 9 | MERA | MERA  BOTA T/SEP 2 CIERRES | 0 | 23 | 6.9 | 3.6 | 1 | 69 | 68 | $43,925 | $87,850 | $2,986,900 | $2,986,900 | 50.0% |
| 10 | MEI | MEI NEGRO BOTA TEX DET COSTU | 0 | 21 | 6.2 | 3.9 | 1 | 63 | 62 | $47,990 | $95,980 | $2,975,380 | $2,975,380 | 50.0% |
| 11 | JANET | JANET BOTA T/GOND DET TALON  | 0 | 26 | 12.2 | 6.0 | 0 | 78 | 78 | $37,950 | $75,900 | $2,960,100 | $2,960,100 | 50.0% |
| 12 | 588 | 588 BOTA TEXANA 1 CIERR C/MA | 0 | 46 | 9.3 | 2.1 | 5 | 97 | 92 | $31,900 | $63,788 | $2,937,301 | $2,933,696 | 50.0% |
| 13 | RAVEN |  RAVEN BOTA TEX DET TACHA | 0 | 20 | 5.5 | 3.1 | 3 | 60 | 57 | $49,950 | $99,900 | $2,847,150 | $2,847,150 | 50.0% |
| 14 | 590 | 590 BOTA TEX C/ALTA T/S FOLI | 0 | 32 | 7.0 | 2.8 | 4 | 89 | 85 | $32,900 | $65,800 | $2,793,312 | $2,796,500 | 50.0% |
| 15 | TERRA | TERRA  BOTA BAJA DET HEBILLA | 0 | 30 | 5.1 | 2.1 | 5 | 63 | 58 | $46,500 | $93,000 | $2,684,306 | $2,697,000 | 50.0% |
| 16 | ALBERTA | ALBERTA  BOTA DET DE COST | 0 | 16 | 5.0 | 4.2 | 9 | 48 | 39 | $65,213 | $130,426 | $2,543,307 | $2,543,307 | 50.0% |
| 17 | HAPRA | HAPRAIA BOTA 2 CIERR REPTIL | 13 | 11 | 6.6 | 7.9 | 2 | 36 | 34 | $70,427 | $145,020 | $2,394,507 | $2,536,162 | 51.4% |
| 18 | ELBERTA | ELBERTA BOTA 1 CIERRE DET HE | 0 | 34 | 4.5 | 1.5 | 12 | 52 | 40 | $56,952 | $119,900 | $2,272,998 | $2,517,920 | 52.5% |
| 19 | IRMA | IRMA BOTA MONT C/ALTA DET CO | 0 | 27 | 7.8 | 4.3 | 2 | 81 | 79 | $32,490 | $64,238 | $2,566,710 | $2,508,092 | 49.4% |
| 20 | 300 | 300 BOTA BAJA 2 CIERRE DET C | 0 | 39 | 12.8 | 4.4 | 0 | 117 | 117 | $17,500 | $38,500 | $2,047,500 | $2,457,000 | 54.5% |
| 21 | JADIA | JADIA BOTA T/GOND DET TALON  | 0 | 22 | 8.2 | 5.0 | 2 | 66 | 64 | $37,950 | $75,900 | $2,428,800 | $2,428,800 | 50.0% |
| 22 | ROGER | ROGER BOTA CORT 2 CIERR COST | 11 | 19 | 6.3 | 5.2 | 2 | 45 | 43 | $56,390 | $112,780 | $2,424,770 | $2,424,770 | 50.0% |
| 23 | RANDA | RANDA BOTA TEXANA C/MEDIA DE | 0 | 18 | 5.2 | 2.7 | 1 | 49 | 48 | $49,950 | $99,900 | $2,377,620 | $2,397,600 | 50.0% |
| 24 | ALEXIA | ALEXIA BOTA DET CIERRE/GAMUZ | 0 | 12 | 5.0 | 5.0 | 0 | 36 | 36 | $65,213 | $130,426 | $2,347,668 | $2,347,668 | 50.0% |
| 25 | 861 | 861 PANTU PELU DET BOTON | 114 | 119 | 11.0 | 1.6 | 102 | 190 | 88 | $26,225 | $52,500 | $2,295,881 | $2,312,200 | 50.0% |
| 26 | LPALM | LPALMAR BOTA T/SEP COMB REPT | 8 | 18 | 5.3 | 5.3 | 0 | 39 | 39 | $58,820 | $117,640 | $2,293,980 | $2,293,980 | 50.0% |
| 27 | 405BLANCO | 405 BOTA TEXANA CORTA DET BO | 0 | 0 | 4.0 | 8.0 | 6 | 72 | 66 | $28,500 | $62,700 | $1,881,000 | $2,257,200 | 54.5% |
| 28 | MIRAGE | MIRAGE BOTA C/ALTA DET HEBEI | 0 | 15 | 5.5 | 3.8 | 0 | 45 | 45 | $49,800 | $99,600 | $2,241,000 | $2,241,000 | 50.0% |
| 29 | CATHERINE | CATHERINE BOTA T/SEP DET TAL | 0 | 11 | 5.9 | 7.3 | 1 | 33 | 32 | $69,561 | $139,122 | $2,225,952 | $2,225,952 | 50.0% |
| 30 | 603 | 603  BOTA T/SEP CAÑA LARGA D | 0 | 20 | 6.5 | 3.6 | 3 | 60 | 57 | $38,350 | $76,700 | $2,185,950 | $2,185,950 | 50.0% |

---

## Asignación Óptima en 4 Tranches (M/M/M/M)

Distribución por urgencia: stock bajo + velocidad alta + factor quiebre alto → comprar primero.

### Tranche 1 — MARZO (Urgente: stock crítico, alta velocidad)
- **Pares**: 1,631
- **Inversión**: $59,892,586
- **Margen bruto esperado**: $58,420,834
- **ROI**: 98%
- **Familias**: 38

| Familia | Nombre | OI24 | OI25 | VelReal | FQ | Stk | Dem | Nec | Costo | PVP | Inversión | Mg% |
|---------|--------|------|------|---------|-----|-----|-----|-----|-------|-----|-----------|-----|
| 735031 | 735031 BOTA BAJA 1 CIERRE DET  | 0 | 32 | 15.7 | 6.4 | 1 | 96 | 95 | $50,000 | $99,999 | $4,749,952 | 50.0% |
| FINI | FINI BOTA T/S DOBLE CIERRE  | 0 | 18 | 8.4 | 6.1 | 0 | 54 | 54 | $58,800 | $117,600 | $3,175,200 | 50.0% |
| JANET | JANET BOTA T/GOND DET TALON RE | 0 | 26 | 12.2 | 6.0 | 0 | 78 | 78 | $37,950 | $75,900 | $2,960,100 | 50.0% |
| HAPRA | HAPRAIA BOTA 2 CIERR REPTIL | 13 | 11 | 6.6 | 7.9 | 2 | 36 | 34 | $70,427 | $145,020 | $2,394,507 | 51.4% |
| 300 | 300 BOTA BAJA 2 CIERRE DET COS | 0 | 39 | 12.8 | 4.4 | 0 | 117 | 117 | $17,500 | $38,500 | $2,047,500 | 54.5% |
| ALEXIA | ALEXIA BOTA DET CIERRE/GAMUZA | 0 | 12 | 5.0 | 5.0 | 0 | 36 | 36 | $65,213 | $130,426 | $2,347,668 | 50.0% |
| LPALM | LPALMAR BOTA T/SEP COMB REPTIL | 8 | 18 | 5.3 | 5.3 | 0 | 39 | 39 | $58,820 | $117,640 | $2,293,980 | 50.0% |
| MIRAGE | MIRAGE BOTA C/ALTA DET HEBEILL | 0 | 15 | 5.5 | 3.8 | 0 | 45 | 45 | $49,800 | $99,600 | $2,241,000 | 50.0% |
| CATHERINE | CATHERINE BOTA T/SEP DET TALON | 0 | 11 | 5.9 | 7.3 | 1 | 33 | 32 | $69,561 | $139,122 | $2,225,952 | 50.0% |
| 655872 | HAY655872 PETIT  PANTUBOTA COR | 0 | 15 | 6.0 | 7.0 | 0 | 45 | 45 | $55,000 | $100,100 | $2,475,000 | 45.1% |
| VIVIAN | VIVIAN BOTA 1 CIERR DET CINTO | 0 | 14 | 7.5 | 7.3 | 0 | 42 | 42 | $46,990 | $90,597 | $1,973,580 | 48.1% |
| 117106 | 117106 BOTA T/GOND DET COST HE | 0 | 12 | 5.8 | 6.8 | 0 | 36 | 36 | $50,000 | $99,999 | $1,799,982 | 50.0% |
| KIMMY | KIMMY BOTA C/ALTA DET HEBILLA  | 0 | 12 | 4.5 | 4.9 | 0 | 36 | 36 | $49,950 | $99,900 | $1,798,200 | 50.0% |
| LIBRE | LIBRE BOTA TEX ABIERT DET CINT | 11 | 9 | 5.0 | 8.1 | 0 | 30 | 30 | $57,728 | $116,009 | $1,731,836 | 50.2% |
| 3610 |  3610 BOTA BAJA 1 CIERRE DET T | 0 | 24 | 10.2 | 5.8 | 2 | 72 | 70 | $24,130 | $48,260 | $1,689,100 | 50.0% |
| ... | *23 familias más* | | | | | | | 842 | | | $23,989,029 | |


### Tranche 2 — ABRIL (Core sellers)
- **Pares**: 1,505
- **Inversión**: $58,411,816
- **Margen bruto esperado**: $57,518,132
- **ROI**: 98%
- **Familias**: 31

| Familia | Nombre | OI24 | OI25 | VelReal | FQ | Stk | Dem | Nec | Costo | PVP | Inversión | Mg% |
|---------|--------|------|------|---------|-----|-----|-----|-----|-------|-----|-----------|-----|
| SNOWY | SNOWY  PANTUBOTA CORTA INT PEL | 0 | 36 | 10.6 | 4.3 | 3 | 108 | 105 | $39,900 | $79,800 | $4,189,500 | 50.0% |
| JOYCE | JOYCE BOTA T/ SEP 1 CIERRE DET | 0 | 33 | 7.9 | 4.0 | 2 | 99 | 97 | $36,441 | $72,882 | $3,534,777 | 50.0% |
| MEGAN | MEGAN BOTA T/S FOLIA DET TALON | 0 | 25 | 8.6 | 5.1 | 3 | 75 | 72 | $48,990 | $97,980 | $3,527,280 | 50.0% |
| MERA | MERA  BOTA T/SEP 2 CIERRES | 0 | 23 | 6.9 | 3.6 | 1 | 69 | 68 | $43,925 | $87,850 | $2,986,900 | 50.0% |
| MEI | MEI NEGRO BOTA TEX DET COSTURA | 0 | 21 | 6.2 | 3.9 | 1 | 63 | 62 | $47,990 | $95,980 | $2,975,380 | 50.0% |
| IRMA | IRMA BOTA MONT C/ALTA DET COST | 0 | 27 | 7.8 | 4.3 | 2 | 81 | 79 | $32,490 | $64,238 | $2,566,710 | 49.4% |
| JADIA | JADIA BOTA T/GOND DET TALON RE | 0 | 22 | 8.2 | 5.0 | 2 | 66 | 64 | $37,950 | $75,900 | $2,428,800 | 50.0% |
| ROGER | ROGER BOTA CORT 2 CIERR COST | 11 | 19 | 6.3 | 5.2 | 2 | 45 | 43 | $56,390 | $112,780 | $2,424,770 | 50.0% |
| RANDA | RANDA BOTA TEXANA C/MEDIA DET  | 0 | 18 | 5.2 | 2.7 | 1 | 49 | 48 | $49,950 | $99,900 | $2,377,620 | 50.0% |
| 603 | 603  BOTA T/SEP CAÑA LARGA DET | 0 | 20 | 6.5 | 3.6 | 3 | 60 | 57 | $38,350 | $76,700 | $2,185,950 | 50.0% |
| TEMPUS | TEMPUS  BOTA T/SEP DET ELASTIC | 0 | 15 | 5.2 | 4.5 | 1 | 45 | 44 | $46,500 | $93,000 | $2,046,000 | 50.0% |
| 1315 | 1315  BOTA TEX CLASICA DET CIE | 0 | 31 | 8.6 | 3.6 | 1 | 93 | 92 | $22,000 | $44,000 | $2,024,000 | 50.0% |
| 0701 | 070 BOTA 1 CIERRE C/MANGA DET  | 0 | 22 | 5.0 | 2.5 | 1 | 56 | 55 | $29,500 | $64,900 | $1,612,470 | 54.5% |
| ISA | ISA BOTA BAJA DET PULSERA  | 0 | 21 | 5.6 | 3.3 | 2 | 63 | 61 | $31,490 | $62,980 | $1,920,890 | 50.0% |
| LUCY | LUCY BOTA T/FINO DET CORTE | 0 | 11 | 5.2 | 4.7 | 2 | 33 | 31 | $60,865 | $121,730 | $1,886,815 | 50.0% |
| ... | *16 familias más* | | | | | | | 527 | | | $19,723,954 | |


### Tranche 3 — MAYO (Complemento de surtido)
- **Pares**: 1,482
- **Inversión**: $51,772,392
- **Margen bruto esperado**: $52,268,507
- **ROI**: 101%
- **Familias**: 31

| Familia | Nombre | OI24 | OI25 | VelReal | FQ | Stk | Dem | Nec | Costo | PVP | Inversión | Mg% |
|---------|--------|------|------|---------|-----|-----|-----|-----|-------|-----|-----------|-----|
| 2250 | 2250 T/GOND 2 CIERRES COST | 37 | 48 | 10.5 | 3.7 | 17 | 128 | 110 | $57,047 | $113,581 | $6,303,680 | 49.8% |
| AGOSTINA | AGOSTINA  BOTA CAÑA ALTA DET H | 0 | 16 | 4.4 | 3.3 | 4 | 48 | 44 | $82,604 | $165,208 | $3,634,576 | 50.0% |
| 588 | 588 BOTA TEXANA 1 CIERR C/MANG | 0 | 46 | 9.3 | 2.1 | 5 | 97 | 92 | $31,900 | $63,788 | $2,937,301 | 50.0% |
| RAVEN |  RAVEN BOTA TEX DET TACHA | 0 | 20 | 5.5 | 3.1 | 3 | 60 | 57 | $49,950 | $99,900 | $2,847,150 | 50.0% |
| 590 | 590 BOTA TEX C/ALTA T/S FOLIA  | 0 | 32 | 7.0 | 2.8 | 4 | 89 | 85 | $32,900 | $65,800 | $2,793,312 | 50.0% |
| TERRA | TERRA  BOTA BAJA DET HEBILLA | 0 | 30 | 5.1 | 2.1 | 5 | 63 | 58 | $46,500 | $93,000 | $2,684,306 | 50.0% |
| ALBERTA | ALBERTA  BOTA DET DE COST | 0 | 16 | 5.0 | 4.2 | 9 | 48 | 39 | $65,213 | $130,426 | $2,543,307 | 50.0% |
| 405BLANCO | 405 BOTA TEXANA CORTA DET BORD | 0 | 0 | 4.0 | 8.0 | 6 | 72 | 66 | $28,500 | $62,700 | $1,881,000 | 54.5% |
| 7200 | 7200  BOTA T/SEP DET COSTURA | 0 | 53 | 7.1 | 1.7 | 6 | 93 | 87 | $24,867 | $49,733 | $2,151,033 | 50.0% |
| TEXBOR | 3450 TEXANA 3/4 BORDADA | 0 | 0 | 4.0 | 8.0 | 18 | 72 | 54 | $26,800 | $58,960 | $1,447,200 | 54.5% |
| IBONE | IBONE BOTA T/FOLIA SEP DET HEB | 0 | 19 | 5.2 | 3.5 | 6 | 57 | 51 | $33,490 | $67,275 | $1,707,990 | 50.2% |
| MELISA | MELISA BOTA TEXANA GMZ DET STR | 0 | 10 | 3.1 | 3.3 | 3 | 30 | 27 | $63,474 | $126,948 | $1,713,798 | 50.0% |
| 1330 | 1330 BOTA  1 CIERRE C/MANGA DE | 0 | 23 | 7.5 | 3.8 | 8 | 69 | 61 | $22,647 | $49,833 | $1,381,471 | 54.6% |
| MIGUE | MIGUELA BOTA TEX BAJ COST | 20 | 13 | 5.0 | 5.2 | 11 | 50 | 38 | $43,990 | $84,471 | $1,693,615 | 47.9% |
| KIRST | KIRSTY BOTA T/ SEP 1 CIERRE LA | 0 | 15 | 3.6 | 3.1 | 6 | 45 | 39 | $36,441 | $72,882 | $1,421,199 | 50.0% |
| ... | *16 familias más* | | | | | | | 574 | | | $14,631,454 | |


### Tranche 4 — JUNIO (Reposición mid-season)
- **Pares**: 985
- **Inversión**: $28,050,742
- **Margen bruto esperado**: $30,133,440
- **ROI**: 107%
- **Familias**: 24

| Familia | Nombre | OI24 | OI25 | VelReal | FQ | Stk | Dem | Nec | Costo | PVP | Inversión | Mg% |
|---------|--------|------|------|---------|-----|-----|-----|-----|-------|-----|-----------|-----|
| BETHANY | BETHANY BOTA CORTA 2 CIERRES D | 0 | 49 | 9.5 | 2.0 | 18 | 100 | 82 | $48,047 | $103,650 | $3,946,628 | 53.6% |
| ELBERTA | ELBERTA BOTA 1 CIERRE DET HEBI | 0 | 34 | 4.5 | 1.5 | 12 | 52 | 40 | $56,952 | $119,900 | $2,272,998 | 52.5% |
| 861 | 861 PANTU PELU DET BOTON | 114 | 119 | 11.0 | 1.6 | 102 | 190 | 88 | $26,225 | $52,500 | $2,295,881 | 50.0% |
| 1336 | 1336 BOTA TEX CAÑA MEDIA | 0 | 42 | 6.1 | 1.9 | 16 | 80 | 64 | $34,000 | $68,000 | $2,192,999 | 50.0% |
| EV21 | EV21 BOTI T/GON DOS CIER DET C | 13 | 13 | 3.2 | 3.1 | 9 | 39 | 30 | $59,000 | $118,032 | $1,770,000 | 50.0% |
| 405 | 405  BOTA TEXANA CORTA DET BOR | 0 | 0 | 4.0 | 3.2 | 22 | 72 | 50 | $29,250 | $64,350 | $1,462,500 | 54.5% |
| GRATA | GRATA BOTA CIERR REPT ELAST | 27 | 31 | 7.5 | 2.1 | 24 | 61 | 37 | $46,490 | $92,980 | $1,737,950 | 50.0% |
| LUCENA | LUCENA PANTUBOTA C/CORTA PLATA | 0 | 43 | 4.9 | 1.6 | 21 | 70 | 49 | $26,033 | $57,273 | $1,264,148 | 54.5% |
| 320 | 320 BOTA 2 CIERR DET COST | 49 | 54 | 8.0 | 4.2 | 29 | 154 | 126 | $11,590 | $23,416 | $1,454,545 | 50.5% |
| GRECIA | GRECIA BOTA CORTA CIERRE DET T | 0 | 13 | 4.1 | 4.2 | 12 | 39 | 27 | $47,490 | $94,980 | $1,282,230 | 50.0% |
| 00083 | 83 BOTA ALTA MOTO 4 HEB ESTRIB | 12 | 17 | 3.2 | 2.4 | 5 | 35 | 30 | $34,500 | $69,000 | $1,026,199 | 50.0% |
| 0771 | 077 BOTA TEX CORTA ABIERTA DET | 0 | 18 | 3.5 | 2.1 | 6 | 39 | 33 | $23,400 | $53,680 | $760,968 | 56.4% |
| 862 | 862 BOTA 1 CIERRE INT PELUCHE  | 0 | 32 | 4.1 | 1.8 | 22 | 58 | 36 | $26,200 | $52,500 | $932,720 | 50.1% |
| 00866 | 866 BOTA PAÑO 2 CIERRES COST | 12 | 16 | 4.9 | 3.4 | 12 | 42 | 30 | $26,217 | $52,500 | $786,500 | 50.1% |
| 860 | 860 PANTU ALTA DET BOTON | 30 | 72 | 5.0 | 1.2 | 34 | 63 | 29 | $26,250 | $52,500 | $762,530 | 50.0% |
| ... | *9 familias más* | | | | | | | 234 | | | $4,101,946 | |



---

## Análisis de Estacionalidad

BOTAS DAMAS es una categoría **100% Otoño-Invierno**:
- Ventas se concentran en **abril a septiembre**
- Factor estacional efectivo = **1.0** (no hay ventas PV que diluyan)
- El `factor_quiebre` de vel_real_articulo ya captura esto: los meses de primavera/verano donde no hay stock aparecen como "quebrados"
- **Implicancia**: toda la inversión debe estar colocada **antes de abril**. Las compras de marzo son las más críticas.

### Distribución mensual típica de ventas (OI):
| Mes | % aprox ventas OI |
|-----|-------------------|
| Abril | 12% |
| Mayo | 22% |
| Junio | 25% |
| Julio | 20% |
| Agosto | 14% |
| Septiembre | 7% |

---

## Resumen de Inversión por Tranche

| Tranche | Mes | Pares | Inversión | % del Total | ROI |
|---------|-----|-------|-----------|-------------|-----|
| T1 | Marzo | 1,631 | $59,892,586 | 30% | 98% |
| T2 | Abril | 1,505 | $58,411,816 | 29% | 98% |
| T3 | Mayo | 1,482 | $51,772,392 | 26% | 101% |
| T4 | Junio | 985 | $28,050,742 | 14% | 107% |
| **TOTAL** | | **5,603** | **$198,127,536** | **100%** | **100%** |

---

## Notas

- Precios de costo y PVP tomados de `msgestion01art.dbo.articulo` (valores actuales en el ERP)
- Familias con costo < $1,000 fueron excluidas (datos inconsistentes/antiguos)
- Factor quiebre cappeado a 3.0x para evitar proyecciones extremas
- 124 familias activas con necesidad > 0 de un universo de 389 con vel_real
- Marcas no se muestran porque el campo sale NULL en las queries consolidadas (JOIN por ventas)
