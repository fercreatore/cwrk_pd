# Reporte Reposición · 2026-04-11 (Sábado)

**Análisis top 30 CSRs × 15 proveedores | Método: quiebre reconstruido + velocidad real + factor estacional mayo | Target: cobertura 60 días**

## Resumen ejecutivo

- **236** líneas con demanda (de 450 CSRs analizadas)
- **5,063** pares/unidades a reponer · **$24.628.977** s/IVA (precio costo)
- **Waterfall 60d**:
  - 🔴 **CRÍTICO** (<15d): 85 líneas · 3,891 un · $14.090.378
  - 🟠 **URGENTE** (15-30d): 31 líneas · 677 un · $7.125.358
  - 🟡 **ATENCIÓN** (30-45d): 22 líneas · 424 un · $2.963.165
  - 🔵 **PLANIFICAR** (45-60d): 18 líneas · 71 un · $450.076

**Supuestos metodológicos**:
- Stock reconstruido mes-a-mes hacia atrás desde stock actual: `stock_inicio_m = stock_fin_m + ventas_m − compras_m`
- Meses con `stock_inicio ≤ 0` excluidos del promedio (quiebre → subestimaría la demanda real)
- `vel_real` = media de ventas sólo en meses no-quebrados (últimos 12 meses completos hasta mar-26)
- Factor estacional **mayo** calculado a nivel proveedor (3 años, 36 meses) = ventas(mayo) / ventas(promedio mensual total)
- `vel_ajustada = vel_real × f_estacional(mayo)` → `cobertura_días = stock / (vel_ajustada / 30)`
- `compra_sugerida = max(0, vel_ajustada/30 × 60 − stock_actual)`
- Stocks negativos (compra POS cód 95) tratados literalmente (incrementan la compra)
- Lead-time implícito: pedido hoy → recepción mayo; por eso se usa factor estacional de mayo

## Factores estacionales mayo (por proveedor)

| Prov | Nombre | f(may) | Interpretación |
|---|---|---|---|
| 515 | ELEMENTO MEDIAS | 1.28 | pico mayo (invierno temprano) |
| 668 | ALPARGATAS/TOPPER | 0.98 | mayo similar al promedio |
| 594 | VICBOR (Atomik/Wake/Footy) | 0.83 | mayo similar al promedio |
| 713 | DISTRINANDO MODA (Picadilly) | 0.30 | valle mayo (tempor./stock-out datos limitados) |
| 641 | FLOYD MEDIAS | 1.07 | mayo similar al promedio |
| 656 | DISTRINANDO DEP (Reebok) | 0.50 | valle mayo (tempor./stock-out datos limitados) |
| 328 | ALMACEN DE MODA (accesorios) | 0.72 | mayo similar al promedio |
| 42 | LESEDIFE (Unicross/Amayra) | 0.84 | mayo similar al promedio |
| 17 | GO BY CZL (marca propia) | 0.91 | mayo similar al promedio |
| 311 | ROFREVE/SOFT | 0.79 | mayo similar al promedio |
| 87 | COMPUESTOS DE EVA (Plumitas) | 0.32 | valle mayo (tempor./stock-out datos limitados) |
| 669 | LANACUER/LA CHAPELLE | 1.29 | pico mayo (invierno temprano) |
| 770 | PRIMER ROUND (Jaguar) | 0.88 | mayo similar al promedio |
| 264 | GRIMOLDI (Hush Puppies/Merrell) | 0.87 | mayo similar al promedio |
| 664 | RIMON CASSIS | 0.30 | valle mayo (tempor./stock-out datos limitados) |

> Observación: varios proveedores tienen f<0.5 (P87, P664, P713, P656) porque mayo cae fuera de la estación alta O porque los datos del mismo mes previo año están contaminados por quiebre severo. Tratar con cautela esos ajustes a la baja.

## 🔴 CRÍTICO (cobertura < 15 días) · 85 líneas · 3,891 un · $14.090.378

*Ordenado por costo de compra descendente. Estas líneas deben pedirse YA (ideal: salir pedido esta semana).*

| Prov | CSR | Descripción | Stock | Vel aj/m | Cob(d) | Quiebre | Compra | Costo | $/u |
|---|---|---|---:|---:|---:|:-:|---:|---:|---:|
| 668 | 6682832119 | 28322 TIE BREAK II KIDS BLANCO/ROSA | 13 | 28 | 13.8 | 10/12 | 44 | $1.346.928 | $30.612 |
| 656 | 656G003800 | ENERGEN RUN 3 NEGRO/BLANCO/GRIS | 1 | 14 | 2.1 | 11/12 | 28 | $895.748 | $31.991 |
| 515 | 5151140451 | 404 MEDIA 1/3 ESTAMPA T.3 | 275 | 601 | 13.7 | 11/12 | 927 | $873.234 | $942 |
| 594 | 594OHIO001 | OHIO BLANCO ZAPA DEP ABROJO | 6 | 18 | 10.0 | 10/12 | 30 | $760.620 | $25.354 |
| 594 | 594BLUSH25 | BLUSH NUDE ZUECO PLAYERO | 0 | 18 | 0.0 | 8/12 | 35 | $709.555 | $20.273 |
| 515 | 5151310251 | 102D C/S SOQUETE DEPORTIVO HOMBRE | 55 | 324 | 5.1 | 11/12 | 593 | $668.311 | $1.127 |
| 515 | 5150010251 | 102L C/S SOQUETE LISO HOMBRE | 14 | 247 | 1.7 | 10/12 | 479 | $539.833 | $1.127 |
| 594 | 594ASAND00 | SAND NEGRO ZUECO PLAYERO FAJA | 1 | 11 | 2.6 | 6/12 | 22 | $446.006 | $20.273 |
| 594 | 594WKC7210 | WKC072 NEGRO/NEGRO ZAPA DEP | 3 | 14 | 6.6 | 9/12 | 24 | $441.600 | $18.400 |
| 594 | 594TFEEL00 | RESTFEEL NEGRO CHINELA FAJA | 1 | 9 | 3.5 | 7/12 | 16 | $373.152 | $23.322 |
| 669 | 6692780251 | 12UO7802 VALIJA CARRY ON 20" | 1 | 5 | 6.1 | 7/12 | 9 | $306.000 | $34.000 |
| 594 | 594BLUSH00 | BLUSH NEGRO ZUECO PLAYERO | -5 | 14 | -10.9 | 10/12 | 33 | $301.785 | $9.145 |
| 594 | 5940031600 | WKC316 NEGRO ZAPA DEP TEJIDA | 0 | 6 | 0.0 | 8/12 | 13 | $254.800 | $19.600 |
| 515 | 5151105451 | 105 C/S SOQUETE KIDS T.4 | 5 | 110 | 1.4 | 7/12 | 216 | $240.408 | $1.113 |
| 713 | 713174CN12 | 1174 CAFE/NEGRO ZAPA TREKKING | 1 | 12 | 2.4 | 11/12 | 24 | $239.976 | $9.999 |
| 515 | 5151240151 | 401R MEDIA 1/3 DAMA RAYADO | 15 | 84 | 5.4 | 6/12 | 152 | $230.128 | $1.514 |
| 594 | 594WK26900 | WKC269 NEGRO ZAPA DEP | 0 | 8 | 0.0 | 8/12 | 15 | $228.000 | $15.200 |
| 656 | 6562543402 | C205434 CROCBAND PLATFORM AZUL/BLANCO | 1 | 4 | 7.7 | 3/12 | 7 | $223.930 | $31.990 |
| 515 | 5151105551 | 105 C/S SOQUETE KIDS T.5 | 17 | 105 | 4.8 | 7/12 | 194 | $215.922 | $1.113 |
| 311 | 3110SF6000 | SF60 NEGRO OJOTA MODA DET GLITTER | 3 | 11 | 8.3 | 7/12 | 19 | $210.026 | $11.054 |
| 515 | 5151040251 | 402L MEDIA 1/3 HOMBRE LISA | 19 | 69 | 8.3 | 6/12 | 118 | $205.438 | $1.741 |
| 669 | 6695084751 | 34UM5084 BUFANDA SURTIDA | 0 | 17 | 0.0 | 10/12 | 33 | $203.115 | $6.155 |
| 713 | 7132024500 | 20245-09 NEGRO SAND TACO SEP | 0 | 4 | 0.0 | 9/12 | 7 | $192.493 | $27.499 |
| 311 | 3110SF6020 | SF60 PLATA OJOTA MODA DET GLITTER | 2 | 8 | 7.4 | 7/12 | 14 | $154.756 | $11.054 |
| 641 | 6416100051 | 61 SURTIDOS SOQUETE CORTO ESTAMPADO | 35 | 92 | 11.4 | 10/12 | 150 | $153.150 | $1.021 |
| 641 | 641CL09051 | CL09 C/S MEDIA VESTIR LISA | 23 | 71 | 9.7 | 11/12 | 119 | $145.656 | $1.224 |
| 311 | 3110SF6012 | SF60 BLANCO OJOTA MODA DET GLITTER | 4 | 9 | 13.7 | 7/12 | 13 | $143.702 | $11.054 |
| 42 | 0428140212 | 68.1402 MOCHILA INFLUENCER 17" PRINT | -3 | 7 | -13.3 | 8/12 | 17 | $143.667 | $8.451 |
| 713 | 7132111511 | 121-1-15 MARRON SANDALIA BAJA | 1 | 2 | 12.0 | 9/12 | 4 | $139.996 | $34.999 |
| 656 | 6562543413 | C205434 CROCBAND PLATFORM GRIS/ROSA | 0 | 2 | 0.0 | 12/12 | 4 | $127.960 | $31.990 |
| 264 | 2646000200 | HZN 660002 WINNIE NEGRO ZAPA DEP | 0 | 1 | 0.0 | 12/12 | 2 | $125.000 | $62.500 |
| 328 | 328PROPO11 | PRODUCTO EN PROMO x7MIL | 0 | 6 | 0.0 | 1/12 | 11 | $121.000 | $11.000 |
| 264 | 2645500815 | HZYP 655008 COMPETITION BEIGE ZAPA DEP | 0 | 1 | 0.0 | 12/12 | 2 | $120.000 | $60.000 |
| 264 | 2645510800 | HZN 655108 COMPETITION NEGRO ZAPA DEP | 0 | 1 | 0.0 | 12/12 | 2 | $120.000 | $60.000 |
| 17 | 017WS06601 | WS066 HIELO/PLATA ZAPA DEP AC FITNESS | 0 | 2 | 0.0 | 12/12 | 4 | $119.996 | $29.999 |
| 264 | 2645520206 | HZQ 655002 WINNIE ZAPA DEP ACORD | 0 | 1 | 0.0 | 12/12 | 2 | $110.000 | $55.000 |
| 264 | 2645501615 | HZY 655016 PARK BEIGE ZAPA TREKK | 0 | 1 | 0.0 | 12/12 | 2 | $110.000 | $55.000 |
| 264 | 2646452600 | HZN 645261 AVILA NEGRO ZAPA URB | 0 | 1 | 0.0 | 12/12 | 2 | $105.000 | $52.500 |
| 656 | 656NANX310 | NANO X3 NEGRO/BLANCO ZAPA CROSSFIT | 0 | 1 | 0.0 | 12/12 | 3 | $103.971 | $34.657 |
| 264 | 2645535100 | HZNP655351 SENSE NEGRO ZAPA DEP | 0 | 1 | 0.0 | 12/12 | 2 | $99.000 | $49.500 |
| 669 | 6696513751 | 16UM6513 ALMOHADA DE VIAJE | 1 | 6 | 4.9 | 5/12 | 11 | $96.789 | $8.799 |
| 264 | 2646017228 | CSE 660172 NODA CELESTE SANDALIA NAUTICA | 0 | 1 | 0.0 | 12/12 | 2 | $95.000 | $47.500 |
| 515 | 5151104351 | 104 C/S SOQUETE KIDS T.3 | -1 | 46 | -0.6 | 12/12 | 94 | $92.966 | $989 |
| 594 | 594KC18200 | WKC182 NEGRO ZAPA DEP | 0 | 2 | 0.0 | 12/12 | 5 | $92.000 | $18.400 |
| 669 | 6696514751 | 16UM6514 ALMOHADA DE VIAJE | 0 | 5 | 0.0 | 5/12 | 10 | $87.990 | $8.799 |
| 515 | 5154052051 | 405 MEDIA 1/3 ESTAMPA T.4 | 0 | 31 | 0.0 | 12/12 | 62 | $84.630 | $1.365 |
| 656 | 6562297215 | C202972 SANTA CRUZ CLEAN CUT KHAKI | 0 | 1 | 0.0 | 12/12 | 2 | $72.406 | $36.203 |
| 42 | 0426250600 | 62.506 CINTO UNICROSS DENIM | 0 | 6 | 0.0 | 9/12 | 12 | $71.880 | $5.990 |
| 42 | 042B112651 | 62.B1126 BILLETERA UNICROSS C/DIVISIONES COMB | 0 | 6 | 0.0 | 7/12 | 12 | $70.092 | $5.841 |
| 713 | 7131211100 | 0121-1-1 NEGRO SANDALIA BAJA | -1 | 1 | -48.0 | 12/12 | 2 | $69.998 | $34.999 |
| 770 | 7700432110 | 4321 NEGRO/BLANCO/CARAMELO ZAPA URB | 0 | 2 | 0.0 | 12/12 | 3 | $67.842 | $22.614 |
| 515 | 515101D151 | 101D SOQUETE DAMA DEPORTIVO | -1 | 26 | -1.2 | 12/12 | 53 | $63.865 | $1.205 |
| 515 | 5150110251 | 102R C/S SOQUETE RAYADO HOMBRE | 4 | 29 | 4.1 | 10/12 | 55 | $61.985 | $1.127 |
| 42 | 042B112551 | 62.B1125 BILLETERA C/DIVISION UNICROSS | 0 | 5 | 0.0 | 8/12 | 10 | $58.410 | $5.841 |
| 311 | 3112720014 | RA27200 NEGRO/GRIS/VERDE ZAPA DEP | 0 | 2 | 0.0 | 12/12 | 3 | $50.178 | $16.726 |
| 311 | 3112720000 | RA27200 NEGRO/NEGRO/ROJO ZAPA DEP | 0 | 2 | 0.0 | 12/12 | 3 | $50.178 | $16.726 |
| 311 | 3112720009 | RA27200 NEGRO/AZUL/NARANJA ZAPA DEP | 0 | 2 | 0.0 | 12/12 | 3 | $50.178 | $16.726 |
| 669 | 6696518751 | 16UM6518 ALMOHADA DE VIAJE | 0 | 4 | 0.0 | 12/12 | 7 | $49.273 | $7.039 |
| 669 | 6696515751 | 16UM6515 ALMOHADA DE VIAJE | 0 | 4 | 0.0 | 12/12 | 7 | $44.793 | $6.399 |
| 641 | 6411412051 | 1412 C/S SOQUETE TOBILLERA HOMBRE | -1 | 15 | -2.0 | 12/12 | 31 | $40.145 | $1.295 |
| 669 | 6695093751 | 34UM5093 BUFANDA SURTIDA | -1 | 3 | -11.7 | 12/12 | 6 | $37.254 | $6.209 |
| 713 | 7136217001 | 5262-1-70 PERLA SANDALIA | 0 | 1 | 0.0 | 12/12 | 1 | $34.999 | $34.999 |
| 713 | 7131510115 | 0015-10-1 BEIGE SANDALIA | 0 | 1 | 0.0 | 12/12 | 1 | $34.999 | $34.999 |
| 42 | 0427180951 | 67.X1809 BOTELLA TERMICA AMAYRA 500ML | 0 | 2 | 0.0 | 12/12 | 3 | $32.913 | $10.971 |
| 42 | 0427181151 | 67.X1811 BOTELLA TERMICA AMAYRA 500ML | 0 | 2 | 0.0 | 12/12 | 3 | $29.403 | $9.801 |
| 42 | 042H721651 | 67.H7216.1 BROCHE PARA PELO AMAYRA | 0 | 6 | 0.0 | 11/12 | 12 | $27.972 | $2.331 |
| 713 | 7132450901 | 20245-09 BLANCO SANDALIA T/SEP | 0 | 1 | 0.0 | 12/12 | 1 | $27.499 | $27.499 |
| 664 | 6641883315 | 18833 GREICE SOFT PAPETE HUESO SANDALIA | 0 | 0 | 0.0 | 12/12 | 1 | $26.990 | $26.990 |
| 669 | 6696563751 | 16UM6563 CINTO DE DAMA | 0 | 3 | 0.0 | 12/12 | 5 | $18.395 | $3.679 |
| 669 | 6696565751 | 16UM6565 CINTO DE DAMA | 0 | 3 | 0.0 | 12/12 | 5 | $17.195 | $3.439 |
| 664 | 6641253100 | 12531 LYON THONG AD NEGRO/CARAMELO | 0 | 1 | 0.0 | 12/12 | 1 | $16.990 | $16.990 |
| 664 | 6641253102 | 12531 LYON THONG AD AZUL OJOTA | 0 | 0 | 0.0 | 12/12 | 1 | $16.990 | $16.990 |
| 664 | 664ANGRA19 | ANGRA ROSA CHINELA FAJA | 0 | 0 | 0.0 | 12/12 | 1 | $16.945 | $16.945 |
| 669 | 6694124751 | 34UM4124 PAÑUELO SEDA | 1 | 4 | 7.2 | 4/12 | 7 | $16.793 | $2.399 |
| 42 | 042H720851 | 67.H7208.1 BROCHE PARA PELO AMAYRA | 0 | 3 | 0.0 | 10/12 | 6 | $14.526 | $2.421 |
| 42 | 0426752400 | 67.524 CINTO MUJER AMAYRA LISO | 0 | 2 | 0.0 | 12/12 | 3 | $13.743 | $4.581 |
| 669 | 6696572751 | 16UM6572 CINTO DE DAMA | 0 | 3 | 0.0 | 12/12 | 5 | $12.795 | $2.559 |
| 42 | 0422622651 | 62.T6226 SURTIDOS GUANTES MOTO UNICROSS | 0 | 2 | 0.0 | 12/12 | 3 | $12.123 | $4.041 |
| 328 | 990CAPOK51 | CARTAS POKEMON | 0 | 12 | 0.0 | 9/12 | 24 | $12.000 | $500 |
| 42 | 0429645751 | 67.B964 BILLETERA CH 2 CIERRE DET COST | 0 | 2 | 0.0 | 12/12 | 3 | $11.853 | $3.951 |
| 17 | 0171150513 | 505 GRIS PANTALON COLEGIAL C/BOLSILLOS | 0 | 3 | 0.0 | 12/12 | 6 | $10.116 | $1.686 |
| 328 | 3280602000 | MEDIA MARRON CAPIBARA | 0 | 3 | 0.0 | 12/12 | 6 | $7.650 | $1.275 |
| 713 | 7132727500 | 27275 HOY SLIDE NEGRO CHINELA | 0 | 1 | 0.0 | 12/12 | 1 | $7.649 | $7.649 |
| 669 | 6692292351 | 342292 GUANTE TEJIDO GRUESO | 0 | 3 | 0.0 | 12/12 | 6 | $7.284 | $1.214 |
| 42 | 042H720451 | 67.H7204.1 BROCHE PARA PELO AMAYRA | 0 | 1 | 0.0 | 11/12 | 2 | $4.842 | $2.421 |

## 🟠 URGENTE (cobertura 15-30 días) · 31 líneas · 677 un · $7.125.358

*Pedir en los próximos 7-10 días para evitar stock-out antes de fin de mes.*

| Prov | CSR | Descripción | Stock | Vel aj/m | Cob(d) | Quiebre | Compra | Costo | $/u |
|---|---|---|---:|---:|---:|:-:|---:|---:|---:|
| 668 | 6682357900 | 23579 X FORCER KIDS VELCRO | 20 | 25 | 23.6 | 10/12 | 31 | $1.273.108 | $41.068 |
| 17 | 0171402651 | SDL4026 OXFORD MOCHILA 2 CIERRES P/NOTEBOOK 18" | 29 | 38 | 23.1 | 8/12 | 46 | $1.056.942 | $22.977 |
| 656 | 656N133813 | ENERGEN RUN 3 GRIS/AZUL/LIMA | 13 | 17 | 23.0 | 11/12 | 21 | $671.811 | $31.991 |
| 656 | 656ASSIC00 | NANO CLASSIC CORE NEGRO/BLANCO/GRIS | 8 | 11 | 21.9 | 11/12 | 14 | $485.198 | $34.657 |
| 17 | 4570026022 | 260PU GALLETITA ZAPATO FOLCLORE CLASICO | 8 | 14 | 17.4 | 12/12 | 20 | $474.000 | $23.700 |
| 713 | 713174NR00 | 1174 NEGRO/ROJO ZAPA TREKKING | 33 | 37 | 27.0 | 11/12 | 40 | $399.960 | $9.999 |
| 713 | 7131211515 | 121-1-5 BEIGE SANDALIA BAJA | 4 | 7 | 17.4 | 8/12 | 10 | $349.990 | $34.999 |
| 515 | 5151020151 | 201 MEDIA DAMA LISA SURTIDO | 211 | 228 | 27.8 | 11/12 | 245 | $331.485 | $1.353 |
| 17 | 017DANCE01 | GO DANCE BLANCO/BLANCO ZAPA DANZA | 3 | 6 | 16.3 | 0/12 | 8 | $240.000 | $30.000 |
| 264 | 2646440919 | HJY 640409 MISHA 2.0 ROSA/ORO PANCHA | 2 | 3 | 19.1 | 7/12 | 4 | $230.000 | $57.500 |
| 594 | 594WK11400 | WKC114 NEGRO ZAPA DEP TEJIDA | 7 | 9 | 24.0 | 10/12 | 11 | $202.400 | $18.400 |
| 594 | 594BLUSH14 | BLUSH VERDE ZUECO PLAYERO | 5 | 7 | 21.4 | 7/12 | 9 | $182.457 | $20.273 |
| 17 | 017CMFLL51 | CAMISETA $4.999 M/CORTA | 29 | 37 | 23.7 | 10/12 | 44 | $110.000 | $2.500 |
| 594 | 594WK25500 | WKC255 NEGRO PANCHA | 4 | 6 | 21.1 | 6/12 | 7 | $109.200 | $15.600 |
| 311 | 311SB08006 | SB080 INDIGO OJOTA CONFORT | 4 | 6 | 19.7 | 6/12 | 8 | $107.776 | $13.472 |
| 311 | 311SB09002 | SB090 AZUL/CELESTE OJOTA CONFORT | 5 | 7 | 20.2 | 9/12 | 10 | $96.100 | $9.610 |
| 42 | 0420600351 | 91.0600003 CARPETA N3 GAME START C/CIERRE | 6 | 8 | 21.3 | 9/12 | 11 | $90.981 | $8.271 |
| 713 | 7138003325 | 238003-3 NUDE ZUECO | 2 | 3 | 21.3 | 7/12 | 4 | $76.676 | $19.169 |
| 264 | 2645502002 | HZAP55020 BENTON AZUL ZAPA TREKK | 1 | 2 | 18.0 | 1/12 | 2 | $73.172 | $36.586 |
| 264 | 2645502800 | HXAP55028 PIPA NEGRO ZAPA ACORD | 1 | 1 | 22.2 | 1/12 | 2 | $73.172 | $36.586 |
| 770 | 7700431701 | 4317 BLANCO/ROSA ZAPA URB | 2 | 3 | 23.4 | 0/12 | 3 | $65.181 | $21.727 |
| 664 | 7222973202 | NASSAU AZUL/GRIS/VERDE OJOTA | 2 | 3 | 21.1 | 6/12 | 4 | $64.864 | $16.216 |
| 664 | 7222973213 | NASSAU GRIS/NEGRO OJOTA | 2 | 3 | 21.2 | 5/12 | 4 | $64.864 | $16.216 |
| 713 | 7135710310 | 571003 NEGRO/NEGRO SANDALIA | 1 | 2 | 17.1 | 6/12 | 2 | $61.778 | $30.889 |
| 264 | 2646351300 | HZN 650234 BLED NEGRO ZAPA DEP | 1 | 1 | 24.3 | 0/12 | 1 | $57.143 | $57.143 |
| 641 | 641MJ08051 | MJ8 C/S SOQUETE DAMA LISO | 42 | 45 | 27.9 | 12/12 | 48 | $48.816 | $1.017 |
| 664 | 6648325800 | 83258 SLIDE UNISEX NEGRO CHINELA | 3 | 4 | 23.5 | 8/12 | 5 | $47.495 | $9.499 |
| 641 | 6411414051 | 1414 C/S SOQUETE CORTO LISO | 30 | 32 | 27.8 | 12/12 | 35 | $41.090 | $1.174 |
| 515 | 5151110151 | 101L C/S SOQUETE DAMA LISO | 10 | 15 | 19.5 | 10/12 | 21 | $21.084 | $1.004 |
| 42 | 042P603551 | 67.P6035 PARAGUAS CORTO MANUAL AMAYRA 21" | 2 | 2 | 25.1 | 0/12 | 3 | $14.283 | $4.761 |
| 328 | 328WD10000 | MEDIA BLANCA CAPIBARA | 2 | 3 | 20.1 | 3/12 | 4 | $4.332 | $1.083 |

## 🟡 ATENCIÓN (cobertura 30-45 días) · 22 líneas · 424 un · $2.963.165 · mostrando top 22

*Incluir en el pedido planificado junto con CRÍTICO+URGENTE para aprovechar gastos de envío.*

| Prov | CSR | Descripción | Stock | Vel aj/m | Cob(d) | Quiebre | Compra | Costo | $/u |
|---|---|---|---:|---:|---:|:-:|---:|---:|---:|
| 668 | 6684430000 | 026443 FAST 2.0 NEGRO/ORO | 16 | 15 | 32.8 | 11/12 | 13 | $567.866 | $43.682 |
| 17 | 017DANCE00 | GO DANCE NEGRO/ORO ZAPA DANZA | 16 | 16 | 30.6 | 0/12 | 15 | $450.000 | $30.000 |
| 668 | 6685236913 | 52369 STANCE 3 NEGRO/GRIS | 12 | 11 | 31.8 | 7/12 | 11 | $436.260 | $39.660 |
| 264 | 2643193400 | CALDRONE NEGRO/BLANCO ZAPA ACORD COMB | 4 | 3 | 34.4 | 10/12 | 3 | $264.705 | $88.235 |
| 515 | 5151140251 | 402E MEDIA 1/3 HOMBRE ESTAMPA | 180 | 177 | 30.4 | 10/12 | 175 | $253.925 | $1.451 |
| 668 | 6682620602 | 26206 STRONG PACE III AZUL/GRIS | 8 | 7 | 36.0 | 0/12 | 5 | $150.550 | $30.110 |
| 264 | 2641502102 | HJA 150021 FRANCIS AZUL MOCASIN SLIP ON | 3 | 3 | 31.7 | 8/12 | 3 | $148.500 | $49.500 |
| 264 | 2646430900 | HJN 640309 MISHA 2.0 NEGRO PANCHA | 4 | 3 | 38.2 | 7/12 | 2 | $115.000 | $57.500 |
| 264 | 2646423400 | HGN 640234 HATRIA NEGRO GUILLERMINA DEP | 2 | 2 | 31.3 | 7/12 | 2 | $109.000 | $54.500 |
| 515 | 5151140151 | 401 MEDIA 1/3 DAMA LISA | 92 | 84 | 32.8 | 12/12 | 76 | $95.836 | $1.261 |
| 770 | 7700431513 | 4315 GRIS/NEGRO/AQUA ZAPA URB | 8 | 6 | 43.7 | 8/12 | 3 | $78.534 | $26.178 |
| 515 | 5151040151 | 401 MEDIA 1/3 DAMA ESTAMPA | 92 | 70 | 39.3 | 12/12 | 49 | $61.789 | $1.261 |
| 770 | 7700431510 | 4315 NEGRO/COBRE ZAPA URB | 5 | 3 | 44.5 | 6/12 | 2 | $52.356 | $26.178 |
| 594 | 594WKC5500 | WKC055 NEGRO PANCHA | 10 | 7 | 45.0 | 6/12 | 3 | $46.800 | $15.600 |
| 713 | 7138003100 | 238003-1 NEGRO ZUECO | 5 | 3 | 43.1 | 7/12 | 2 | $38.338 | $19.169 |
| 641 | 6415900051 | 59 SURTIDOS MEDIA CASUAL ESTAMPADA | 51 | 36 | 42.1 | 12/12 | 22 | $27.126 | $1.233 |
| 641 | 641MJ06051 | MJ6 SURTIDOS SOQUETE DAMA ESTAMPADO | 35 | 27 | 39.1 | 12/12 | 19 | $19.323 | $1.017 |
| 641 | 641MJ18051 | MJ18 SURTIDOS SOQUETE INVISIBLE | 33 | 24 | 41.9 | 11/12 | 14 | $18.956 | $1.354 |
| 264 | 2645607400 | HDA 256074 470 NEGRO SOQUETE LISO | 4 | 3 | 37.0 | 5/12 | 2 | $10.900 | $5.450 |
| 42 | 042T402151 | 67.T4021 BUFANDA COMB DET FLECO AMAYRA | 2 | 2 | 35.5 | 1/12 | 1 | $7.641 | $7.641 |
| 42 | 042B113051 | 62.B1130 BILLETERA UNICROSS C/DIVISIONES DET PIC | 3 | 2 | 44.4 | 2/12 | 1 | $5.841 | $5.841 |
| 669 | 6691232415 | 34UC2324 GORRA CAP | 2 | 2 | 35.0 | 9/12 | 1 | $3.919 | $3.919 |

## 🔵 PLANIFICAR (cobertura 45-60 días) · 18 líneas · 71 un · $450.076 · mostrando top 18

*Revisión fin-de-mes — aún hay margen.*

| Prov | CSR | Descripción | Stock | Vel aj/m | Cob(d) | Quiebre | Compra | Costo | $/u |
|---|---|---|---:|---:|---:|:-:|---:|---:|---:|
| 264 | 264OKLYN00 | BROOKLYN LS NEGRO/BLANCO ZAPA ACORD | 8 | 5 | 45.8 | 10/12 | 2 | $144.386 | $72.193 |
| 17 | 0110026000 | 259PU NEGRO ZAPATO 4.5 FOLCLORE CLASICO T/SEP | 18 | 11 | 49.7 | 11/12 | 4 | $94.800 | $23.700 |
| 515 | 5150010501 | 105 SOQUETE BLANCO COLEGIAL T.5 | 160 | 106 | 45.1 | 11/12 | 53 | $65.561 | $1.237 |
| 770 | 7700807900 | 8079 NEGRO/ORO ZAPA | 10 | 6 | 48.7 | 10/12 | 2 | $32.906 | $16.453 |
| 713 | 7132451000 | 20245-10 NEGRO SANDALIA T/SEP | 3 | 2 | 45.5 | 7/12 | 1 | $28.499 | $28.499 |
| 311 | 3110540000 | 5400 NEGRO PANCHA ELASTANO | 30 | 15 | 58.6 | 9/12 | 1 | $27.260 | $27.260 |
| 17 | 0171453628 | CAMISETA ARG MESSI PUBLICITARIA | 10 | 6 | 47.3 | 10/12 | 3 | $25.497 | $8.499 |
| 42 | 0429159351 | 91.5900003 MOCHILA INFANTIL ANIMALITOS | 6 | 3 | 53.3 | 11/12 | 1 | $8.631 | $8.631 |
| 42 | 0426550351 | 62.503 CINTO UNICROSS DENIM | 3 | 2 | 46.6 | 5/12 | 1 | $6.921 | $6.921 |
| 664 | 6648359700 | 83597 ANATOMIC SHINE FEM NEGRO | 2 | 1 | 45.5 | 7/12 | 1 | $6.299 | $6.299 |
| 328 | 9902264151 | BILLETERA SAKALI DAMA SURTIDA | 14 | 7 | 56.8 | 7/12 | 1 | $5.817 | $5.817 |
| 328 | 9907656051 | SQUISHY PERSONAJES | 8 | 4 | 55.2 | 5/12 | 1 | $3.499 | $3.499 |
| 87 | 0872600013 | 260 GRIS/NARANJA ZUECO DAMA C/BANDA | 2 | 1 | 58.1 | 7/12 | 0 | $0 | $14.249 |
| 264 | 2645502213 | HZGP 555022 FERBY GRIS ZAPA ACORD | 5 | 3 | 55.5 | 2/12 | 0 | $0 | $33.658 |
| 264 | 2646511000 | HZN 650110 ATENEA NEGRO/GRIS ZAPA URB | 2 | 1 | 48.5 | 0/12 | 0 | $0 | $62.500 |
| 656 | 6561099828 | C10998 CROCBAND KIDS CELESTE/ROSA | 8 | 4 | 58.3 | 4/12 | 0 | $0 | $20.687 |
| 668 | 6682620500 | 26205 STRONG PACE III NEGRO/LIMA | 28 | 14 | 59.3 | 8/12 | 0 | $0 | $36.946 |
| 770 | 7700431700 | 4317 NEGRO ZAPA URB | 12 | 6 | 58.5 | 5/12 | 0 | $0 | $21.727 |

## Desglose por proveedor (CRÍTICO + URGENTE)

| Prov | Nombre | Empresa | Líneas | Unidades | Costo s/IVA |
|---|---|---|---:|---:|---:|
| 594 | VICBOR (Atomik/Wake/Footy) | H4 | 12 | 220 | $4.101.575 |
| 515 | ELEMENTO MEDIAS | CALZALINDO | 13 | 3,209 | $3.629.289 |
| 668 | ALPARGATAS/TOPPER | H4 | 2 | 75 | $2.620.036 |
| 656 | DISTRINANDO DEP (Reebok) | H4 | 7 | 79 | $2.581.024 |
| 17 | GO BY CZL (marca propia) | CALZALINDO | 6 | 128 | $2.011.054 |
| 713 | DISTRINANDO MODA (Picadilly) | H4 | 12 | 97 | $1.636.013 |
| 264 | GRIMOLDI (Hush Puppies/Merrell) | H4 | 12 | 25 | $1.317.487 |
| 669 | LANACUER/LA CHAPELLE | H4 | 12 | 111 | $897.676 |
| 311 | ROFREVE/SOFT | CALZALINDO | 8 | 73 | $862.894 |
| 42 | LESEDIFE (Unicross/Amayra) | CALZALINDO | 14 | 100 | $596.688 |
| 641 | FLOYD MEDIAS | H4 | 5 | 383 | $428.857 |
| 664 | RIMON CASSIS | H4 | 7 | 17 | $255.138 |
| 328 | ALMACEN DE MODA (accesorios) | CALZALINDO | 4 | 45 | $144.982 |
| 770 | PRIMER ROUND (Jaguar) | H4 | 2 | 6 | $133.023 |

## Caveats y limitaciones metodológicas

1. **Alcance**: análisis limitado a top 30 CSRs (por v12m) de cada proveedor. Proveedores con catálogos más largos pueden tener long-tail fuera de este corte.
2. **Descripciones**: tomadas de `articulo.descripcion_1` con `MAX()` por CSR — algunas CSRs con múltiples sub-productos (ej. set valijas 17+19+21") consolidan en una sola descripción representativa.
3. **Precios**: `MAX(precio_costo)` de articulo, no precio de última compra en `compras1`. Puede diferir del costo negociado actual; útil sólo como orden de magnitud.
4. **Estacionalidad**: factor calculado con 36 meses a nivel proveedor. Cuando un proveedor sólo tiene 2 puntos (dos mayos observados) el factor es ruidoso — contraste con la intuición de temporada.
5. **Quiebre severo**: CSRs con 10-12/12 meses quebrados tienen vel_real basada en 0-2 meses, por ende baja confianza. Revisar esos casos antes de validar el número.
6. **Stocks negativos**: reflejan el bug conocido del comprobante 95 POS en base CLZ — la suma entre bases compensa, pero a nivel CSR individual puede distorsionar la cobertura.
7. **Lead-times**: el análisis asume recepción en mayo (f_estacional=mayo). Proveedores con lead-time > 45d deberían usar junio o fragmentar el cálculo — no implementado en esta corrida.
8. **No auto-inserta**: los scripts generados en `_scripts_oneshot/` son BORRADORES. Revisar curvas de talle, negociación y bonificación antes de INSERT.

## Archivos generados

- `_informes/reporte_reposicion_2026-04-11.md` — este reporte
- `_scripts_oneshot/borrador_reposicion_P<prov>_2026-04-11.py` — un script por proveedor con líneas CRÍTICO
- `_scripts_oneshot/analisis_reposicion_2026-04-11.json` — dump completo del análisis (input para otras herramientas)
