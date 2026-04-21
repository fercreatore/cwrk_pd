# Reporte de Reposición — 2026-04-19

**Ventana de análisis**: demanda estacional ajustada para período **abr-may-jun** (mes actual + 2 siguientes).

**Metodología**:
- Top 50 CSR por proveedor (ordenados por ventas últimos 12m).
- `vel_real` desde `omicronvt.dbo.vel_real_articulo` (algoritmo de quiebre v3, corte 2026-03-31) — descarta meses quebrados del cálculo de velocidad.
- Factor estacional por CSR usando 3 años de historia (promedio mes-calendario / media anual).
- `vel_ajustada = vel_real × factor_est_{abr,may,jun}`.
- Clasificación por días de cobertura: `stock_actual / (vel_ajustada/30)`.

## Resumen ejecutivo por urgencia

| Urgencia | Días restantes | # CSR | Pares a pedir | Inversión |
|---|---|---|---|---|
| **CRITICO** | < 15 d | 100 | 3.008 | $ 10.912.003 |
| **URGENTE** | 15-30 d | 49 | 1.558 | $ 5.177.964 |
| **ATENCION** | 30-45 d | 28 | 292 | $ 1.088.438 |
| **PLANIFICAR** | 45-60 d | 37 | 148 | $ 768.713 |
| **TOTAL** | — | **214** | **5.006** | **$ 17.947.118** |

## CRITICO — < 15 d

| Prov | Marca | Modelo / Descripción | CSR | Stock | Vel.real | Factor est. | Vel.aj. | Días rest. | Pedir | Inv. |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 17 | GO by CZL | 702 NEGRO REMERA M/LARGA TERMICA KIDS | `0170070200` | -1 | 0.64 | 0.83 | 0.53 | -56.2 | **2** | $ 1.020 |
| 87 | seawalk | 850/D VERDE/AQUA ZUECO GOMA INTERIOR PEL | `087850D027` | -1 | 2.80 | 1.23 | 3.43 | -8.7 | **8** | $ 45.526 |
| 17 | GO by CZL | 500 GRIS/CLARO JOGGIN FRISADO MELANGE | `0170050030` | -1 | 3.71 | 1.44 | 5.34 | -5.6 | **12** | $ 51.636 |
| 669 | La Chapelle | 34UM5093 BUFANDA SURTIDA | `6695093751` | -1 | 7.50 | 1.12 | 8.40 | -3.6 | **18** | $ 111.764 |
| 515 | ELEMENTO MEDIAS | 952 MEDIA 1/2 CANA HOMBRE ROMBO | `5151195251` | -2 | 20.48 | 1.28 | 26.21 | -2.3 | **54** | $ 89.764 |
| 641 | Gustavo E. Garcia | 1412 C/S SOQUETE TOBILLERA HOMBRE | `6411412051` | -1 | 13.88 | 1.14 | 15.78 | -1.9 | **33** | $ 42.735 |
| 515 | ELEMENTO MEDIAS | 101D SOQUETE DAMA DEPORTIVO | `515101D151` | -1 | 16.14 | 2.28 | 36.84 | -0.8 | **75** | $ 90.389 |
| 515 | ELEMENTO MEDIAS | 405 MEDIA 1/3 ESTAMPA T.5 | `5151140551` | 0 | 13.90 | 3.44 | 47.85 | 0.0 | **96** | $ 131.046 |
| 515 | ELEMENTO MEDIAS | 104 C/S SOQUETE KIDS T.3 | `5151104351` | 0 | 37.79 | 0.50 | 18.75 | 0.0 | **37** | $ 36.597 |
| 669 | La Chapelle | 34UM5084 BUFANDA SURTIDA | `6695084751` | 0 | 14.39 | 1.28 | 18.39 | 0.0 | **37** | $ 227.742 |
| 328 | Almacen de Moda | MEDIA MARRON CAPIBARA | `3280602000` | 0 | 30.00 | 0.56 | 16.80 | 0.0 | **34** | $ 43.350 |
| 328 | Almacen de Moda | ZOQUETE EFECTO PIEL | `328ZOQEP15` | 0 | 21.58 | 0.72 | 15.59 | 0.0 | **31** | $ 36.910 |
| 641 | Gustavo E. Garcia | GO472 MEDIA DEP SPORTY CAMOUFLAGE | `641GO47200` | 0 | 4.82 | 2.58 | 12.43 | 0.0 | **25** | $ 36.450 |
| 594 | Atomik | WKC269 NEGRO ZAPA DEP ACORD TEJIDA | `594WK26900` | 0 | 12.00 | 0.90 | 10.80 | 0.0 | **22** | $ 334.400 |
| 669 | La Chapelle | 342292 GUANTE TEJIDO GRUESO | `6692292351` | 0 | 10.40 | 1.00 | 10.40 | 0.0 | **21** | $ 25.498 |
| 656 | Le Coq / Kappa / C | C205434 CROCBAND PLATFORM CLOG GRIS/ROSA | `6562543413` | 0 | 8.38 | 0.97 | 8.15 | 0.0 | **16** | $ 511.855 |
| 17 | GO by CZL | 505 AZUL PANTALON COLEGIAL C/BOLSILLOS | `0171150502` | 0 | 5.18 | 1.52 | 7.89 | 0.0 | **16** | $ 26.976 |
| 311 | SOFT | RA27200 NEGRO/AZUL/NARANJA ZAPA DEP ACOR | `3112720009` | 0 | 5.76 | 1.25 | 7.20 | 0.0 | **14** | $ 234.171 |
| 311 | SOFT | RA27200 NEGRO/GRIS/VERDE ZAPA DEP ACORD  | `3112720014` | 0 | 5.76 | 1.18 | 6.80 | 0.0 | **14** | $ 234.171 |
| 311 | SOFT | RA27200 NEGRO/NEGRO/ROJO ZAPA DEP ACORD  | `3112720000` | 0 | 4.40 | 1.42 | 6.23 | 0.0 | **12** | $ 200.718 |
| 641 | Gustavo E. Garcia | MJ13 C/S SOQUETE INVISIBLE LISO | `641MJ13051` | 0 | 4.07 | 1.13 | 4.60 | 0.0 | **9** | $ 7.978 |
| 264 | Hush Puppies / Sti | HZN 655108 COMPETITION NEGRO ZAPA DEP AC | `2645510800` | 0 | 3.36 | 1.31 | 4.40 | 0.0 | **9** | $ 540.000 |
| 668 | Topper | 26556 DRIVE 2 AZUL/GRIS ZAPA DEP ACORD D | `6682655602` | 0 | 6.60 | 0.67 | 4.40 | 0.0 | **9** | $ 356.949 |
| 669 | La Chapelle | 16UM6518 ALMOHADA DE VIAJE | `6696518751` | 0 | 4.32 | 1.02 | 4.40 | 0.0 | **9** | $ 63.353 |
| 311 | SOFT | RU4092 NEGRO/BLANCO ZAPA DEP ACORD COMB | `3110409200` | 0 | 2.75 | 1.50 | 4.12 | 0.0 | **8** | $ 131.794 |
| 42 | Marta/Zurley | 62.5115 RINONERA DE HOMBRE UNICROSS | `0422511551` | 0 | 2.67 | 1.50 | 4.00 | 0.0 | **8** | $ 33.048 |
| 515 | ELEMENTO MEDIAS | 104L.3 SOQUETE  T.3 KIDS X3 | `5151043351` | 0 | 5.43 | 0.59 | 3.21 | 0.0 | **6** | $ 5.935 |
| 264 | Hush Puppies / Sti | HZYP655227 SENA BEIGE ZAPA ACORD COMB DE | `2645522715` | 0 | 3.36 | 0.95 | 3.20 | 0.0 | **6** | $ 297.000 |
| 17 | GO by CZL | WS066 HIELO/PLATA ZAPA DEP AC FITNESS | `017WS06601` | 0 | 2.13 | 1.50 | 3.19 | 0.0 | **6** | $ 179.994 |
| 656 | Le Coq / Kappa / C | C202972 SANTA CRUZ CLEAN CUT KHAKI MOCA  | `6562297215` | 0 | 3.80 | 0.79 | 3.00 | 0.0 | **6** | $ 217.219 |
| 594 | Atomik | DREAMS BLANCO/ROSA ZAPA URB DET PICADO A | `594DREAM19` | 0 | 7.20 | 0.39 | 2.80 | 0.0 | **6** | $ 152.128 |
| 264 | Hush Puppies / Sti | HZNP655351 SENSE NEGRO ZAPA DEP ACORD CO | `2645535100` | 0 | 2.14 | 1.29 | 2.75 | 0.0 | **6** | $ 297.000 |
| 515 | ELEMENTO MEDIAS | 108.3 SOQUETE ESTAMPADO BEBE T.0 PACK X3 | `5151080351` | 0 | 2.24 | 1.15 | 2.58 | 0.0 | **5** | $ 9.928 |
| 42 | Marta/Zurley | 67.524 CINTO MUJER AMAYRA LISO | `0426752400` | 0 | 2.93 | 0.88 | 2.56 | 0.0 | **5** | $ 22.905 |
| 594 | Atomik | WKC300 BLANCO/VERDE ZAPA URB COMB DET AB | `594KC30014` | 0 | 3.10 | 0.75 | 2.33 | 0.0 | **5** | $ 76.000 |
| 264 | Hush Puppies / Sti | HZYP 655008 COMPETITION BEIGE ZAPA DEP A | `2645500815` | 0 | 1.33 | 1.67 | 2.22 | 0.0 | **4** | $ 240.000 |
| 594 | Atomik | WKC055 NUDE PANCHA C/DIRECTO COMB | `594WKC5525` | 0 | 2.17 | 1.00 | 2.17 | 0.0 | **4** | $ 54.400 |
| 17 | GO by CZL | CAMPERA NEGRO IMPORTADA PLUMA DET COSTUR | `017LUIMP00` | 0 | 3.60 | 0.56 | 2.00 | 0.0 | **4** | $ 136.000 |
| 42 | Marta/Zurley | 62.506 CINTO UNICROSS DENIM | `0426250600` | 0 | 4.23 | 0.45 | 1.91 | 0.0 | **4** | $ 23.960 |
| 264 | Hush Puppies / Sti | HZSP655251 SENSE LILA ZAPA DEP ACORD COM | `2645525106` | 0 | 2.20 | 0.86 | 1.89 | 0.0 | **4** | $ 198.000 |
| 669 | La Chapelle | 16UM6514 ALMOHADA DE VIAJE | `6696514751` | 0 | 4.80 | 0.38 | 1.83 | 0.0 | **4** | $ 35.197 |
| 669 | La Chapelle | 16UM6515 ALMOHADA DE VIAJE | `6696515751` | 0 | 3.67 | 0.50 | 1.83 | 0.0 | **4** | $ 25.597 |
| 656 | Le Coq / Kappa / C | K132193CW LOGO MASERTA BLANCO ZAPA URB A | `656193CW01` | 0 | 1.32 | 1.28 | 1.69 | 0.0 | **3** | $ 69.820 |
| 264 | Hush Puppies / Sti | HZQ 655002 WINNIE ZAPA DEP ACORD COMB DE | `2645520206` | 0 | 1.17 | 1.33 | 1.56 | 0.0 | **3** | $ 165.000 |
| 770 | Jaguar | 4321 NEGRO/BLANCO/CARAMELO ZAPA URB ACOR | `7700432110` | 0 | 2.58 | 0.59 | 1.52 | 0.0 | **3** | $ 67.843 |
| 311 | SOFT | 6000 AZUL/NARANJA ZAPA DEP TEJIDA ALFORZ | `3110600002` | 0 | 1.27 | 1.13 | 1.43 | 0.0 | **3** | $ 59.123 |
| 264 | Hush Puppies / Sti | HZY 655016 PARK BEIGE ZAPA TREKK AC COMB | `2645501615` | 0 | 1.20 | 1.17 | 1.40 | 0.0 | **3** | $ 165.000 |
| 770 | Jaguar | 4020 BLANCO/ROSA/CELESTE ZAPA DEP ACORD  | `7700402001` | 0 | 1.25 | 1.00 | 1.25 | 0.0 | **2** | $ 45.229 |
| 656 | Le Coq / Kappa / C | ZIG DYNAMICA 5 NEGRO/VIOLETA/AZUL ZAPA D | `656ZGDY500` | 0 | 1.35 | 0.88 | 1.19 | 0.0 | **2** | $ 144.814 |
| 328 | Almacen de Moda | PRODUCTO EN PROMO x10mil | `328PROPO51` | 0 | 1.61 | 0.63 | 1.01 | 0.0 | **2** | $ 1.300 |
| 311 | SOFT | NK5801 NEGRO/ROSA ZAPA DEP AC COMB BASE  | `3110580119` | 0 | 1.00 | 1.00 | 1.00 | 0.0 | **2** | $ 39.869 |
| 311 | SOFT | 10500 CIRUELA ZAPA DEP TEJIDA DET LINEAS | `3111050019` | 0 | 1.00 | 1.00 | 1.00 | 0.0 | **2** | $ 48.876 |
| 264 | Hush Puppies / Sti | HAY655872 PETIT ARENA PANTUBOTA CORTA DE | `2645587222` | 0 | 0.92 | 1.00 | 0.92 | 0.0 | **2** | $ 110.000 |
| 669 | La Chapelle | 16UM6554 CARTERA DE DAMA | `6696554751` | 0 | 1.90 | 0.38 | 0.71 | 0.0 | **1** | $ 15.999 |
| 311 | SOFT | NK5801 BEIGE/BLANCO ZAPA DEP AC COMB BAS | `3110580115` | 0 | 1.24 | 0.54 | 0.67 | 0.0 | **1** | $ 19.935 |
| 664 | Rimon Cassis | 61699 BRASIL II AD AZUL OJOTA LISA | `6646169902` | 0 | 2.24 | 0.30 | 0.67 | 0.0 | **1** | $ 4.799 |
| 264 | Hush Puppies / Sti | RZG 155127 COLORADO SNEAKER LO GRIS ZAPA | `2645512713` | 0 | 1.00 | 0.64 | 0.64 | 0.0 | **1** | $ 89.500 |
| 515 | ELEMENTO MEDIAS | 108.3 SOQUETE ESTAMPADO BEBE T.1 PACK X3 | `5151081351` | 0 | 0.75 | 0.86 | 0.64 | 0.0 | **1** | $ 1.986 |
| 87 | seawalk | 270 KAKHI ZUECO HOMBRE C/BANDA | `0872700011` | 0 | 0.60 | 0.88 | 0.53 | 0.0 | **1** | $ 13.592 |
| 656 | Le Coq / Kappa / C | C10998 CROCBAND KIDS LAVANDA/NEO ZUECO P | `6561099806` | 0 | 0.88 | 0.34 | 0.30 | 0.0 | **1** | $ 21.327 |
| 17 | GO by CZL | CAMISETA ARG PREMIUM DTF C/TEJIDO | `017GPREM01` | 0 | 0.08 | 1.00 | 0.08 | 0.0 | **0** | $ 0 |
| 17 | GO by CZL | CAMISETA ARG NEGRO TELA AFA DRY FIT | `017RODRY00` | 0 | 0.08 | 1.00 | 0.08 | 0.0 | **0** | $ 0 |
| 17 | GO by CZL | CAMISETA RIVER VIOLETA TELA AFA DRY FIT | `017ERVIO62` | 0 | 0.08 | 1.00 | 0.08 | 0.0 | **0** | $ 0 |
| 515 | ELEMENTO MEDIAS | 022 C/S SOQUETE INVISIBLE LISO | `5151102251` | 2 | 84.67 | 0.67 | 56.29 | 1.1 | **111** | $ 122.037 |
| 515 | ELEMENTO MEDIAS | 102L C/S SOQUETE LISO HOMBRE | `5150010251` | 13 | 163.35 | 1.62 | 264.50 | 1.5 | **516** | $ 581.821 |
| 17 | GO by CZL | 505 GRIS PANTALON COLEGIAL C/BOLSILLOS | `0171150513` | 1 | 12.64 | 1.49 | 18.82 | 1.6 | **37** | $ 62.382 |
| 515 | ELEMENTO MEDIAS | 101 C/S SOQUETE DAMA ESTAMPADO | `5151010151` | 5 | 67.51 | 1.05 | 70.69 | 2.1 | **136** | $ 163.906 |
| 641 | Gustavo E. Garcia | MJ13 NEGRO SOQUETE INVISIBLE LISO | `641MJ13N00` | 1 | 16.56 | 0.85 | 14.11 | 2.1 | **27** | $ 25.029 |
| 515 | ELEMENTO MEDIAS | 102R C/S SOQUETE RAYADO HOMBRE | `5150110251` | 3 | 84.30 | 0.49 | 41.08 | 2.2 | **79** | $ 89.053 |
| 515 | ELEMENTO MEDIAS | 102D C/S SOQUETE DEPORTIVO HOMBRE | `5151310251` | 21 | 95.02 | 2.03 | 193.07 | 3.3 | **365** | $ 411.559 |
| 594 | Atomik | WKC182 NEGRO ZAPA DEP AC DET CAPSULA | `594KC18200` | 1 | 6.66 | 1.31 | 8.70 | 3.4 | **16** | $ 294.400 |
| 515 | ELEMENTO MEDIAS | 105 C/S SOQUETE KIDS T.4 | `5151105451` | 3 | 71.49 | 0.34 | 24.41 | 3.7 | **46** | $ 51.237 |
| 641 | Gustavo E. Garcia | 1415 NEGRO SOQUETE INVISIBLE LISO | `6411415000` | 1 | 9.29 | 0.67 | 6.23 | 4.8 | **11** | $ 10.444 |
| 42 | Marta/Zurley | 62.B1125 BILLETERA C/DIVISION UNICROSS | `042B112551` | 1 | 4.90 | 1.25 | 6.13 | 4.9 | **11** | $ 64.251 |
| 42 | Marta/Zurley | 62.B1126 BILLETERA UNICROSS C/DIVISIONES | `042B112651` | 1 | 2.89 | 2.06 | 5.95 | 5.0 | **11** | $ 64.251 |
| 669 | La Chapelle | 34UC2334 GORRO DE PANO | `6691233451` | 1 | 3.03 | 1.92 | 5.82 | 5.2 | **11** | $ 31.671 |
| 515 | ELEMENTO MEDIAS | 401R MEDIA 1/3 DAMA RAYADO | `5151240151` | 12 | 52.47 | 1.29 | 67.92 | 5.3 | **124** | $ 187.772 |
| 42 | Marta/Zurley | 62.B1132 BILLETERA C/DIVISION UNICROSS C | `0421132551` | 1 | 4.22 | 1.30 | 5.50 | 5.5 | **10** | $ 58.410 |
| 669 | La Chapelle | 16UM6513 ALMOHADA DE VIAJE | `6696513751` | 1 | 6.08 | 0.72 | 4.40 | 6.8 | **8** | $ 70.394 |
| 515 | ELEMENTO MEDIAS | 105 C/S SOQUETE KIDS T.5 | `5151105551` | 15 | 79.56 | 0.81 | 64.33 | 7.0 | **114** | $ 126.978 |
| 515 | ELEMENTO MEDIAS | 101L C/S SOQUETE DAMA LISO | `5151110151` | 33 | 144.00 | 0.82 | 118.50 | 8.4 | **204** | $ 204.879 |
| 641 | Gustavo E. Garcia | MJ14 C/S SOQUETE SUPER INVISIBLE | `641MJ14000` | 3 | 4.86 | 2.08 | 10.10 | 8.9 | **17** | $ 13.158 |
| 594 | Atomik | WKC254 NEGRO ZAPA DEP C/CAPS DET MULTI | `594WK25400` | 1 | 3.08 | 0.99 | 3.06 | 9.8 | **5** | $ 78.000 |
| 669 | La Chapelle | 34UM5092 BUFANDA SURTIDA | `6695092751` | 1 | 2.00 | 1.53 | 3.06 | 9.8 | **5** | $ 31.046 |
| 311 | SOFT | RU2872 NEGRO/NARANJA ZAPA DEP ACORD COMB | `3110287209` | 1 | 1.74 | 1.65 | 2.87 | 10.4 | **5** | $ 82.371 |
| 641 | Gustavo E. Garcia | 1420 C/S MEDIA CASUAL 2 RAYAS | `6411420051` | 9 | 16.44 | 1.51 | 24.89 | 10.8 | **41** | $ 66.604 |
| 42 | Marta/Zurley | 67.P6035 PARAGUAS CORTO  MANUAL AMAYRA 2 | `042P603551` | 2 | 2.33 | 2.20 | 5.12 | 11.7 | **8** | $ 38.088 |
| 328 | Almacen de Moda | MEDIA BLANCA CAPIBARA | `328WD10000` | 2 | 5.48 | 0.91 | 4.98 | 12.0 | **8** | $ 8.670 |
| 669 | La Chapelle | 16UM6504 PAÑUELO DE SEDA | `6696650451` | 1 | 3.03 | 0.82 | 2.48 | 12.1 | **4** | $ 9.597 |
| 42 | Marta/Zurley | 62.T6239 SURTIDOS GUANTES UNICROSS LISO | `0422623951` | 1 | 1.92 | 1.27 | 2.45 | 12.3 | **4** | $ 13.284 |
| 42 | Marta/Zurley | 67.T4331 SURTIDOS GUANTE AMAYRA ESTAMP | `0427433151` | 1 | 1.92 | 1.27 | 2.45 | 12.3 | **4** | $ 10.764 |
| 515 | ELEMENTO MEDIAS | 023 SOQUETE INVISIBLE ESTAMPADO | `5151102351` | 7 | 15.01 | 1.13 | 16.98 | 12.4 | **27** | $ 29.685 |
| 17 | GO by CZL | Zapatilla Media Punta Elastizada Badana  | `0171515419` | 2 | 4.00 | 1.19 | 4.75 | 12.6 | **8** | $ 160.000 |
| 264 | Hush Puppies / Sti | HZBP655027 LOIRA BLANCO ZAPA  ACORD COMB | `2645502701` | 2 | 4.80 | 0.92 | 4.40 | 13.6 | **7** | $ 346.500 |
| 264 | Hush Puppies / Sti | HZN 650234 BLED NEGRO ZAPA DEP ACORD DET | `2646351300` | 1 | 1.83 | 1.20 | 2.20 | 13.6 | **3** | $ 171.429 |
| 515 | ELEMENTO MEDIAS | 401 MEDIA 1/3 DAMA LISA | `5151140151` | 72 | 86.02 | 1.79 | 154.34 | 14.0 | **237** | $ 299.066 |
| 264 | Hush Puppies / Sti | HZN 645261 AVILA NEGRO ZAPA URB AC DET T | `2646452600` | 1 | 1.70 | 1.26 | 2.15 | 14.0 | **3** | $ 157.500 |
| 641 | Gustavo E. Garcia | 1414 NEGRO SOQUETE CORTO LISO | `6411414000` | 12 | 16.15 | 1.53 | 24.74 | 14.5 | **37** | $ 43.456 |
| 669 | La Chapelle | 34UM4124 PAÑUELO SEDA | `6694124751` | 1 | 4.04 | 0.51 | 2.06 | 14.5 | **3** | $ 7.198 |
| 669 | La Chapelle | 16UM6519 ALMOHADA DE VIAJE | `6696519751` | 1 | 2.41 | 0.84 | 2.02 | 14.9 | **3** | $ 23.998 |

## URGENTE — 15-30 d

| Prov | Marca | Modelo / Descripción | CSR | Stock | Vel.real | Factor est. | Vel.aj. | Días rest. | Pedir | Inv. |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 594 | Atomik | WKC300 BLANCO/ROSA ZAPA URB COMB DET ABR | `594KC30019` | 1 | 2.42 | 0.81 | 1.95 | 15.4 | **3** | $ 45.600 |
| 770 | Jaguar | 4325 NEGRO/GRIS ZAPA DEP ACORD COMB | `7700432510` | 1 | 2.15 | 0.90 | 1.93 | 15.5 | **3** | $ 64.905 |
| 641 | Gustavo E. Garcia | MJ20 MEDIA CASUAL CAÑA 1/3 ESTAMPA | `641MJ20051` | 7 | 10.46 | 1.28 | 13.44 | 15.6 | **20** | $ 24.120 |
| 264 | Hush Puppies / Sti | HZAP55020 BENTON AZUL ZAPA TREKK CORDON  | `2645502002` | 1 | 1.91 | 1.00 | 1.91 | 15.7 | **3** | $ 109.758 |
| 770 | Jaguar | 4317 BLANCO/ROSA ZAPA URB AC ABROJO DET  | `7700431701` | 2 | 3.67 | 1.03 | 3.80 | 15.8 | **6** | $ 130.367 |
| 515 | ELEMENTO MEDIAS | 202 MEDIA DAMA ESTAMPA SURTIDO | `5151020251` | 31 | 22.28 | 2.62 | 58.44 | 15.9 | **86** | $ 139.704 |
| 328 | Almacen de Moda | CAMPERA NERGO CANELON CON POLAR | `3283163900` | 3 | 7.26 | 0.78 | 5.65 | 15.9 | **8** | $ 152.000 |
| 515 | ELEMENTO MEDIAS | 402L MEDIA 1/3 HOMBRE LISA | `5151040251` | 41 | 56.77 | 1.28 | 72.79 | 16.9 | **105** | $ 182.896 |
| 641 | Gustavo E. Garcia | 1414 C/S SOQUETE CORTO LISO | `6411414051` | 28 | 41.86 | 1.18 | 49.33 | 17.0 | **71** | $ 83.390 |
| 668 | Topper | 25806 EVER 2.0 NEGRO/GRIS/CORAL ZAPA TRE | `6682580600` | 5 | 5.14 | 1.69 | 8.70 | 17.2 | **12** | $ 560.984 |
| 515 | ELEMENTO MEDIAS | 405 MEDIA 1/3 ESTAMPA T.4 | `5154052051` | 21 | 12.34 | 2.91 | 35.93 | 17.5 | **51** | $ 69.618 |
| 515 | ELEMENTO MEDIAS | 404 MEDIA 1/3 ESTAMPA T.3 | `5151140451` | 210 | 165.00 | 2.17 | 358.20 | 17.6 | **506** | $ 476.809 |
| 641 | Gustavo E. Garcia | 1425 MEDIA CASUAL MORLEY ESTAMPADO | `6411425151` | 7 | 12.88 | 0.87 | 11.22 | 18.7 | **15** | $ 22.072 |
| 42 | Marta/Zurley | 67.X1811 BOTELLA TERMICA  AMAYRA 500ML | `0427181151` | 1 | 4.80 | 0.33 | 1.60 | 18.8 | **2** | $ 19.602 |
| 264 | Hush Puppies / Sti | HZY 635034 BLED BEIGE ZAPA DEP ACORD DET | `2646350315` | 1 | 1.27 | 1.26 | 1.60 | 18.8 | **2** | $ 114.286 |
| 17 | GO by CZL | 500 GRIS/OSC JOGGIN FRISADO MELANGE | `0170050013` | 1 | 1.06 | 1.48 | 1.57 | 19.1 | **2** | $ 8.606 |
| 515 | ELEMENTO MEDIAS | 104 C/S SOQUETE KIDS T.2 | `5151104251` | 14 | 52.71 | 0.41 | 21.90 | 19.2 | **30** | $ 29.673 |
| 264 | Hush Puppies / Sti | HZNP 155132 NEUS NEGRO ZAPA ACORD COMB | `264PNEUS00` | 1 | 1.17 | 1.33 | 1.56 | 19.2 | **2** | $ 120.000 |
| 42 | Marta/Zurley | 67.X1809 BOTELLA TERMICA  AMAYRA 500ML | `0427180951` | 1 | 2.19 | 0.71 | 1.56 | 19.3 | **2** | $ 21.942 |
| 668 | Topper | 25871 VIGO KIDS BLANCO/AZUL ZAPA TENNIS  | `6682587101` | 4 | 6.10 | 1.01 | 6.17 | 19.4 | **8** | $ 224.796 |
| 264 | Hush Puppies / Sti | HXAP55028 PIPA NEGRO ZAPA  ACORD 1 ABROJ | `2645502800` | 1 | 1.55 | 0.96 | 1.49 | 20.1 | **2** | $ 73.172 |
| 641 | Gustavo E. Garcia | 59 SURTIDOS MEDIA CASUAL ESTAMPADA | `6415900051` | 43 | 47.61 | 1.34 | 64.01 | 20.2 | **85** | $ 104.805 |
| 641 | Gustavo E. Garcia | GO741 SOQUETE DEP RESISTENCE PLUS | `641GO74100` | 17 | 16.67 | 1.42 | 23.73 | 21.5 | **30** | $ 39.825 |
| 641 | Gustavo E. Garcia | GO481 MEDIA ALTA PROLITE CREW | `641GO48100` | 13 | 11.12 | 1.63 | 18.16 | 21.5 | **23** | $ 48.760 |
| 669 | La Chapelle | 16UM6509 PAÑUELO DE SEDA | `6696509751` | 1 | 2.12 | 0.65 | 1.37 | 21.8 | **2** | $ 4.798 |
| 641 | Gustavo E. Garcia | GO440 SOQUETE DEP DUAL POWER | `641GO44000` | 11 | 17.48 | 0.86 | 14.97 | 22.0 | **19** | $ 23.769 |
| 515 | ELEMENTO MEDIAS | 950 MEDIA 1/2 CANA HOMBRE ESTAMPA | `5151195051` | 35 | 42.65 | 1.10 | 46.97 | 22.4 | **59** | $ 110.228 |
| 594 | Atomik | WKC272 NEGRO ZAPA DEP 2 ABROJOS COMB | `594WK27200` | 7 | 7.20 | 1.29 | 9.28 | 22.6 | **12** | $ 220.800 |
| 42 | Marta/Zurley | 67.519 CINTO DAMA AMAYRA | `0426751951` | 2 | 1.67 | 1.46 | 2.43 | 24.7 | **3** | $ 21.573 |
| 42 | Marta/Zurley | 67.T4021 BUFANDA  COMB DET FLECO AMAYRA | `042T402151` | 2 | 1.74 | 1.39 | 2.42 | 24.8 | **3** | $ 22.923 |
| 668 | Topper | 88346 TERRE MID NEGRO BOTA URB DET PICAD | `6688834600` | 6 | 4.05 | 1.79 | 7.23 | 24.9 | **8** | $ 333.775 |
| 770 | Jaguar | 4328 BLANCO/ROSA/BORDO ZAPA URB ACORD CO | `7700432801` | 3 | 3.43 | 1.05 | 3.60 | 25.0 | **4** | $ 121.475 |
| 42 | Marta/Zurley | 65.B519 BILLETERA WILSON DET COSTURA | `0426551951` | 2 | 1.83 | 1.30 | 2.38 | 25.2 | **3** | $ 15.633 |
| 641 | Gustavo E. Garcia | 1413 SURTIDOS SOQUETE CORTO ESTAMPADO | `6411413051` | 17 | 15.23 | 1.31 | 19.90 | 25.6 | **23** | $ 28.152 |
| 42 | Marta/Zurley | 62.T6104 SURTIDOS BUFANDA UNICROSS LINEA | `0426104551` | 2 | 1.83 | 1.27 | 2.33 | 25.8 | **3** | $ 11.313 |
| 770 | Jaguar | 4317 BLANCO/VERDE ZAPA URB ACORD ABROJO  | `7700431714` | 2 | 1.83 | 1.25 | 2.29 | 26.2 | **3** | $ 65.183 |
| 594 | Atomik | REECE CRUDO/BEIGE ZAPA URB AC REF TPU | `594REECE15` | 4 | 3.82 | 1.19 | 4.55 | 26.4 | **5** | $ 228.395 |
| 770 | Jaguar | 4306 BEIGE/AQUA/BLANCO ZAPA URB ACORD CO | `7700430627` | 5 | 4.50 | 1.26 | 5.66 | 26.5 | **6** | $ 175.927 |
| 515 | ELEMENTO MEDIAS | 1850 MEDIA 1/2 CANA BEBE LISA T.1 | `5151185051` | 21 | 16.14 | 1.46 | 23.58 | 26.7 | **26** | $ 19.767 |
| 515 | ELEMENTO MEDIAS | 953 SOQUETE ALTO HOMBRE LISO | `5151195351` | 15 | 8.98 | 1.87 | 16.78 | 26.8 | **19** | $ 28.130 |
| 669 | La Chapelle | 34UM5082 BUFANDA SURTIDA | `6695082751` | 2 | 2.17 | 1.00 | 2.17 | 27.6 | **2** | $ 13.678 |
| 515 | ELEMENTO MEDIAS | 912 MEDIA 1/2 CANA HOMBRE LISA | `5151191251` | 119 | 79.68 | 1.61 | 128.30 | 27.8 | **138** | $ 214.851 |
| 641 | Gustavo E. Garcia | MJ8 C/S SOQUETE DAMA LISO | `641MJ08051` | 33 | 55.54 | 0.64 | 35.49 | 27.9 | **38** | $ 38.646 |
| 713 | Picadilly / Chocol | 7183 NEGRO ZAPA URB ACORD DET COST | `7137183000` | 3 | 2.10 | 1.53 | 3.21 | 28.1 | **3** | $ 59.998 |
| 641 | Gustavo E. Garcia | MJ6 SURTIDOS SOQUETE DAMA ESTAMPADO | `641MJ06051` | 27 | 33.12 | 0.87 | 28.72 | 28.2 | **30** | $ 30.510 |
| 668 | Topper | 26405 RETRO PACER NEGRO/BEIGE ZAPA AC CO | `6682640500` | 8 | 4.45 | 1.90 | 8.47 | 28.3 | **9** | $ 312.160 |
| 515 | ELEMENTO MEDIAS | 101L.3 SOQUETE DAMA PACK X3 | `5150310151` | 49 | 33.02 | 1.53 | 50.65 | 29.0 | **52** | $ 188.968 |
| 17 | GO by CZL | 503 GRIS PANTALON OVERSIZE RECTO RUSTICO | `017P503113` | 2 | 1.44 | 1.42 | 2.05 | 29.3 | **2** | $ 8.606 |
| 641 | Gustavo E. Garcia | 1412 NEGRO SOQUETE TOBILLERA HOMBRE | `6411412000` | 9 | 8.14 | 1.11 | 9.01 | 30.0 | **9** | $ 11.016 |

## ATENCION — 30-45 d

| Prov | Marca | Modelo / Descripción | CSR | Stock | Vel.real | Factor est. | Vel.aj. | Días rest. | Pedir | Inv. |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 641 | Gustavo E. Garcia | 65 SURTIDOS MEDIA CASUAL 3D | `6416500051` | 73 | 52.85 | 1.36 | 72.15 | 30.4 | **71** | $ 102.560 |
| 515 | ELEMENTO MEDIAS | 401 MEDIA 1/3 DAMA ESTAMPA | `5151040151` | 56 | 72.91 | 0.76 | 55.27 | 30.4 | **55** | $ 69.403 |
| 594 | Atomik | WKC326 BLANCO ZAPA URB ACORD DET PICADO | `594CH32601` | 2 | 3.96 | 0.48 | 1.92 | 31.2 | **2** | $ 41.600 |
| 515 | ELEMENTO MEDIAS | 104 C/S SOQUETE KIDS T.1 | `5151104151` | 24 | 28.61 | 0.78 | 22.42 | 32.1 | **21** | $ 20.771 |
| 641 | Gustavo E. Garcia | MJ18 SURTIDOS SOQUETE INVISIBLE C/ANTIDE | `641MJ18051` | 26 | 25.00 | 0.96 | 24.13 | 32.3 | **22** | $ 29.799 |
| 42 | Marta/Zurley | 65.B517 BILLETERA WILSON C/DIVISIONES DE | `0426551751` | 5 | 2.46 | 1.85 | 4.56 | 32.9 | **4** | $ 20.844 |
| 311 | SOFT | 6300 AZUL/NEGRO ZAPA DEP TEJIDA COMB | `3110630002` | 1 | 1.01 | 0.90 | 0.91 | 33.1 | **1** | $ 19.515 |
| 594 | Atomik | WKC260 ROSA ZAPA DEP TEJIDA C/CAPSULA | `594WK26019` | 1 | 1.90 | 0.48 | 0.91 | 33.1 | **1** | $ 16.000 |
| 264 | Hush Puppies / Sti | HZGP 555022 FERBY GRIS ZAPA ACORD COMB D | `2645502213` | 5 | 3.51 | 1.28 | 4.50 | 33.3 | **4** | $ 134.632 |
| 641 | Gustavo E. Garcia | GO410 SOQUETE DEP ULTIMATE FLOAT | `641GO41000` | 22 | 16.67 | 1.18 | 19.67 | 33.5 | **17** | $ 21.267 |
| 264 | Hush Puppies / Sti | HJY 640409 MISHA 2.0 ROSA/ORO PANCHA C/D | `2646440919` | 2 | 4.18 | 0.43 | 1.78 | 33.7 | **2** | $ 115.000 |
| 641 | Gustavo E. Garcia | MJ2 NEGRO MEDIA TOBILLERA LISA | `641MJ02000` | 31 | 17.59 | 1.56 | 27.54 | 33.8 | **24** | $ 28.944 |
| 515 | ELEMENTO MEDIAS | 011 C/S SOQUETE INVISIBLE HOMBRE | `5150001151` | 32 | 60.87 | 0.45 | 27.61 | 34.8 | **23** | $ 28.246 |
| 641 | Gustavo E. Garcia | GO441 SOQUETE DEP AIR CROSS | `641GO44100` | 18 | 10.92 | 1.40 | 15.28 | 35.3 | **13** | $ 16.263 |
| 770 | Jaguar | 4022 NEGRO BOTA URB CORDON ABROJO | `7700402200` | 6 | 5.76 | 0.88 | 5.05 | 35.6 | **4** | $ 92.149 |
| 669 | La Chapelle | 34UM5086 BUFANDA SURTIDA | `6695086751` | 2 | 1.83 | 0.91 | 1.66 | 36.1 | **1** | $ 7.829 |
| 42 | Marta/Zurley | 62.503 CINTO UNICROSS DENIM | `0426550351` | 3 | 2.40 | 1.02 | 2.44 | 36.9 | **2** | $ 13.842 |
| 669 | La Chapelle | 34UC2121 GUANTE MOTO C/POLAR | `6694212151` | 2 | 1.33 | 1.18 | 1.57 | 38.1 | **1** | $ 3.039 |
| 328 | Almacen de Moda | CAMPERA NEGRO DET COSTURA | `328HCCOS00` | 6 | 3.15 | 1.48 | 4.65 | 38.7 | **3** | $ 48.000 |
| 328 | Almacen de Moda | MEDIAS FUTBOL KIDS C/ANTIDESLIZANTE | `3283418051` | 10 | 13.05 | 0.59 | 7.64 | 39.3 | **5** | $ 15.000 |
| 668 | Topper | TOPPER OFERTA - SIN CAMBIO SIN GARANTIA | `668XFROF51` | 8 | 5.13 | 1.16 | 5.94 | 40.4 | **4** | $ 142.000 |
| 515 | ELEMENTO MEDIAS | 104L.3 SOQUETE  T.2 KIDS X3 | `5151042351` | 2 | 2.33 | 0.62 | 1.46 | 41.2 | **1** | $ 989 |
| 264 | Hush Puppies / Sti | HZNP155137 SEAN NEGRO ZAPA URB ACORD DET | `2645513700` | 1 | 1.27 | 0.57 | 0.73 | 41.3 | **0** | $ 0 |
| 669 | La Chapelle | 16UM6503 PAÑUELO DE SEDA | `6696503751` | 3 | 2.00 | 1.08 | 2.17 | 41.5 | **1** | $ 2.399 |
| 42 | Marta/Zurley | 67.T4334 GUANTE AMAYRA DET BORDADO | `0427433451` | 13 | 9.20 | 1.00 | 9.20 | 42.4 | **5** | $ 13.950 |
| 264 | Hush Puppies / Sti | HZGP555020 VENNER GRIS/LILA/LIMA ZAPA DE | `2645502013` | 5 | 2.71 | 1.30 | 3.52 | 42.7 | **2** | $ 75.238 |
| 669 | La Chapelle | 16UM6586 CINTO DAMA HEB DORADA | `6696658651` | 2 | 2.92 | 0.47 | 1.37 | 43.7 | **1** | $ 3.199 |
| 328 | Almacen de Moda | RELOJ SURTIDOS DAMA | `328RE70000` | 5 | 3.69 | 0.92 | 3.39 | 44.2 | **2** | $ 5.960 |

## PLANIFICAR — 45-60 d

| Prov | Marca | Modelo / Descripción | CSR | Stock | Vel.real | Factor est. | Vel.aj. | Días rest. | Pedir | Inv. |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 669 | La Chapelle | 34UM5099 BUFANDA SURTIDA | `6695099751` | 3 | 1.75 | 1.14 | 2.00 | 45.0 | **1** | $ 3.158 |
| 311 | SOFT | SB2278 NEGRO ZAPA DEP PLAT DET COMB | `3117227800` | 3 | 3.16 | 0.63 | 1.99 | 45.3 | **1** | $ 32.921 |
| 264 | Hush Puppies / Sti | HZN 650110 ATENEA NEGRO/GRIS ZAPA URB AC | `2646511000` | 3 | 1.17 | 1.67 | 1.95 | 46.2 | **1** | $ 62.500 |
| 515 | ELEMENTO MEDIAS | 402E MEDIA 1/3 HOMBRE ESTAMPA | `5151140251` | 180 | 92.28 | 1.26 | 116.56 | 46.3 | **53** | $ 76.933 |
| 594 | Atomik | AFTER VIOLETA/ROSA ZAPA URB CORD ABROJO  | `594AFTER62` | 2 | 2.25 | 0.57 | 1.29 | 46.7 | **1** | $ 27.895 |
| 656 | Le Coq / Kappa / C | FLEXAGON ENERGY TR 4 GRIS/NEGRO/ROSA ZAP | `656FETR413` | 2 | 1.30 | 0.98 | 1.27 | 47.3 | **1** | $ 41.375 |
| 42 | Marta/Zurley | 62.T6226 SURTIDOS GUANTES MOTO UNICROSS | `0422622651` | 12 | 7.19 | 1.06 | 7.59 | 47.4 | **3** | $ 12.123 |
| 668 | Topper | 25792 WIND V GRIS/ROSA ZAPA DEP AC DET C | `6682579213` | 4 | 6.61 | 0.38 | 2.51 | 47.8 | **1** | $ 36.645 |
| 641 | Gustavo E. Garcia | CL09 C/S MEDIA VESTIR LISA PUÑO SOFT | `641CL09051` | 20 | 31.67 | 0.40 | 12.52 | 47.9 | **5** | $ 6.120 |
| 641 | Gustavo E. Garcia | MJ21 MEDIA CASUAL CAÑA 1/3 ESTAMPA | `641MJ21051` | 17 | 10.46 | 1.00 | 10.49 | 48.6 | **4** | $ 4.824 |
| 328 | Almacen de Moda | 2020 RELOJ SURTIDOS HOMBRE | `328RELOJ00` | 8 | 3.38 | 1.45 | 4.90 | 48.9 | **2** | $ 4.176 |
| 641 | Gustavo E. Garcia | GO444 SOQUETE DEP FOOT BOOST | `641GO44400` | 47 | 18.86 | 1.51 | 28.52 | 49.4 | **10** | $ 12.510 |
| 770 | Jaguar | 4304 BLANCO/AZUL/ROSA ZAPA URB ACORD C/P | `7700430401` | 6 | 2.70 | 1.35 | 3.65 | 49.4 | **1** | $ 27.487 |
| 594 | Atomik | WKC114 GRIS/TOPO ZAPA DEP TEJIDA C/CAPSU | `594WK11413` | 8 | 5.84 | 0.82 | 4.82 | 49.8 | **2** | $ 36.800 |
| 641 | Gustavo E. Garcia | MJ2 C/S MEDIA TOBILLERA LISA | `641MJ02051` | 26 | 18.28 | 0.86 | 15.64 | 49.9 | **5** | $ 6.030 |
| 641 | Gustavo E. Garcia | 63 SURTIDOS SOQUETE ANTIDESLIZANTE ESTAM | `6416300051` | 74 | 40.94 | 1.08 | 44.10 | 50.3 | **14** | $ 18.837 |
| 668 | Topper | 25872 VIGO KIDS NEGRO ZAPA TENNIS ACORD  | `6682587200` | 10 | 6.34 | 0.94 | 5.97 | 50.3 | **2** | $ 56.199 |
| 594 | Atomik | WKC103 NEGRO ZAPA DEP TEJIDA CAPSULA | `594WK10300` | 3 | 2.44 | 0.73 | 1.78 | 50.5 | **1** | $ 17.200 |
| 641 | Gustavo E. Garcia | GO470 MEDIA 1/4 INVENCIBLE STRENGHT | `641GO47000` | 84 | 33.33 | 1.48 | 49.30 | 51.1 | **15** | $ 25.650 |
| 668 | Topper | 25824 T350 MESH NEGRO/GRIS/BEIGE ZAPA SN | `6682582400` | 12 | 4.46 | 1.56 | 6.96 | 51.7 | **2** | $ 68.364 |
| 594 | Atomik | WKC114 NEGRO ZAPA DEP TEJIDA C/CAPSULA | `594WK11400` | 7 | 7.83 | 0.52 | 4.06 | 51.7 | **1** | $ 18.400 |
| 770 | Jaguar | 9359 GRIS/AZUL ZAPA DEP ACORD DET BASE | `7700935913` | 3 | 1.56 | 1.12 | 1.74 | 51.7 | **0** | $ 0 |
| 656 | Le Coq / Kappa / C | FLEXAGON ENERGY TR 4 NEGRO/NEGRO/GRIS ZA | `656FLFC410` | 7 | 2.67 | 1.51 | 4.05 | 51.9 | **1** | $ 33.617 |
| 669 | La Chapelle | 34UC2111 GUANTE MOTO C/POLAR | `6694211151` | 5 | 1.96 | 1.48 | 2.89 | 51.9 | **1** | $ 2.429 |
| 668 | Topper | 25783 BORO III OLIVA/NEGRO ZAPA DEP AC D | `6682578314` | 10 | 5.22 | 1.10 | 5.76 | 52.1 | **2** | $ 55.194 |
| 42 | Marta/Zurley | 62.B1130 BILLETERA UNICROSS C/DIVISIONES | `042B113051` | 3 | 1.72 | 0.99 | 1.71 | 52.7 | **0** | $ 0 |
| 328 | Almacen de Moda | MEDIAS FINAS 3x250- $100 c/u | `3280160000` | 13 | 6.75 | 1.09 | 7.38 | 52.8 | **2** | $ 1.284 |
| 668 | Topper | 26206 STRONG PACE III AZUL/GRIS ZAPA DEP | `6682620602` | 10 | 6.31 | 0.89 | 5.64 | 53.2 | **1** | $ 30.110 |
| 42 | Marta/Zurley | 62.T6103 SURTIDOS BUFANDA UNICROSS LISO | `0426103551` | 3 | 1.75 | 0.95 | 1.67 | 54.0 | **0** | $ 0 |
| 641 | Gustavo E. Garcia | 55 SURTIDOS MEDIA TERMICA ESTAMPADA | `6415500051` | 63 | 15.06 | 2.28 | 34.39 | 55.0 | **6** | $ 10.422 |
| 668 | Topper | 25782 BORO III NEGRO/GRIS ZAPA DEP AC DE | `6682578200` | 13 | 5.61 | 1.23 | 6.91 | 56.4 | **1** | $ 27.597 |
| 515 | ELEMENTO MEDIAS | 014 SOQUETE INVISIBLE HOMBRE PACK X3 | `5150001451` | 8 | 10.12 | 0.42 | 4.21 | 56.9 | **0** | $ 0 |
| 641 | Gustavo E. Garcia | MJ15 SURTIDOS MEDIA TERMICA PUÑO LIGHT | `641MJ15051` | 94 | 31.98 | 1.53 | 48.95 | 57.6 | **4** | $ 6.498 |
| 594 | Atomik | WKC109 NEGRO PANCHA TEJIDA C/DIRECTO CAP | `594WK10900` | 4 | 3.09 | 0.67 | 2.07 | 58.0 | **0** | $ 0 |
| 42 | Marta/Zurley | 68.T4314 SURTIDO GUANTE INFLUENCER LISOS | `0426431451` | 3 | 1.91 | 0.81 | 1.55 | 58.2 | **0** | $ 0 |
| 515 | ELEMENTO MEDIAS | 201 MEDIA DAMA LISA SURTIDO | `5151020151` | 163 | 67.04 | 1.25 | 83.74 | 58.4 | **4** | $ 5.415 |
| 328 | Almacen de Moda | CINTO REDONDO C/OJALES | `328T340100` | 4 | 4.27 | 0.47 | 2.00 | 60.0 | **0** | $ 0 |

## Resumen por proveedor (sólo urgencias)

| # | Proveedor (fantasía) | CRÍT | URG | ATN | PLAN | Σ CSR | Σ Pares | Σ Inversión |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 515 | ELEMENTO MEDIAS | 18 | 10 | 4 | 3 | 35 | 3.462 | $ 4.296.039 |
| 264 | Hush Puppies / Stitching / American Pie | 12 | 4 | 4 | 1 | 21 | 69 | $ 3.581.515 |
| 668 | Topper | 1 | 4 | 1 | 6 | 12 | 59 | $ 2.204.773 |
| 594 | Atomik | 6 | 3 | 2 | 5 | 16 | 86 | $ 1.642.018 |
| 311 | SOFT | 9 | 0 | 1 | 1 | 11 | 63 | $ 1.103.464 |
| 656 | Le Coq / Kappa / Crocs | 5 | 0 | 0 | 2 | 7 | 30 | $ 1.040.027 |
| 641 | Gustavo E. Garcia | 8 | 11 | 5 | 8 | 32 | 773 | $ 990.643 |
| 770 | Jaguar | 2 | 5 | 1 | 2 | 10 | 32 | $ 790.565 |
| 669 | La Chapelle | 13 | 2 | 4 | 2 | 21 | 138 | $ 719.583 |
| 17 | GO by CZL | 10 | 2 | 0 | 0 | 12 | 89 | $ 635.220 |
| 42 | Marta/Zurley | 9 | 6 | 3 | 4 | 22 | 95 | $ 502.706 |
| 328 | Almacen de Moda | 4 | 1 | 3 | 3 | 11 | 97 | $ 316.650 |
| 713 | Picadilly / Chocolate / West Coast | 0 | 1 | 0 | 0 | 1 | 3 | $ 59.998 |
| 87 | seawalk | 2 | 0 | 0 | 0 | 2 | 9 | $ 59.118 |
| 664 | Rimon Cassis | 1 | 0 | 0 | 0 | 1 | 1 | $ 4.799 |

## Proveedores con CRÍTICOS (borradores generados en `_scripts_oneshot/`)

- **Prov 17 — GO by CZL**: 10 CSR críticos · 85 pares · $ 618.008
- **Prov 42 — Marta/Zurley**: 9 CSR críticos · 65 pares · $ 328.961
- **Prov 87 — seawalk**: 2 CSR críticos · 9 pares · $ 59.118
- **Prov 264 — Hush Puppies / Stitching / American Pie**: 12 CSR críticos · 51 pares · $ 2.776.929
- **Prov 311 — SOFT**: 9 CSR críticos · 61 pares · $ 1.051.028
- **Prov 328 — Almacen de Moda**: 4 CSR críticos · 75 pares · $ 90.230
- **Prov 515 — ELEMENTO MEDIAS**: 18 CSR críticos · 2.233 pares · $ 2.633.638
- **Prov 594 — Atomik**: 6 CSR críticos · 58 pares · $ 989.328
- **Prov 641 — Gustavo E. Garcia**: 8 CSR críticos · 200 pares · $ 245.854
- **Prov 656 — Le Coq / Kappa / Crocs**: 5 CSR críticos · 28 pares · $ 965.035
- **Prov 664 — Rimon Cassis**: 1 CSR críticos · 1 pares · $ 4.799
- **Prov 668 — Topper**: 1 CSR críticos · 9 pares · $ 356.949
- **Prov 669 — La Chapelle**: 13 CSR críticos · 128 pares · $ 679.054
- **Prov 770 — Jaguar**: 2 CSR críticos · 5 pares · $ 113.072

## Notas metodológicas

- **`SIN_VENTA`** (CSR sin datos en tabla `vel_real_articulo` y sin ventas 12m): excluidos del reporte.
- **`FUERA_TEMP`** (factor estacional abr-jun < 0.3 sobre 3 años de historia): excluidos del reporte; se recomienda revisar en ventana de ingreso del producto.
- **Cantidad a pedir** = objetivo 60 días de cobertura − stock actual. No se aplicó redondeo a curva del proveedor (requiere paso manual o pipeline `paso3`).
- **Inversión** usa `precio_costo` actual de `articulo`, sin descuento de proveedor ni bonificaciones. Números indicativos.
- **Fuente stock**: suma de todos los depósitos (`msgestionC.dbo.stock.stock_actual`). Si se desea excluir depósitos específicos (ej. showroom), ajustar en el análisis.
- **Advertencia vel_real**: la tabla materializada se recalculó el 2026-03-31 (19 días de antigüedad al cierre del reporte). Para decisiones de compra grandes, revisar `AUDIT_VEL_REAL_20260325.md` (7 gaps documentados, sync copias #2/#3/#4 pendiente).
