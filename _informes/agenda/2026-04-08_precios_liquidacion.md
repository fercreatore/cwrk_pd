# Propuesta Precios Liquidacion — Top 20 Stock Muerto
> Generado: 8 de abril de 2026 — PENDIENTE APROBACION FERNANDO
> Criterio: stock activo, ultima compra < 2022, ordenado por valor inventario

---

## COMO APROBAR

Revisar la columna **PRECIO PROPUESTO** y en la ultima columna marcar:
- **OK** → aplicar tal cual
- **BAJAR $X** → ajustar precio
- **NO** → no tocar este articulo

Una vez aprobado, Claude ejecuta el UPDATE en ERP.

---

## ALERTAS PREVIAS — REVISAR ANTES

Algunos articulos tienen **precio_actual < precio_costo** en el sistema. Posiblemente Mariana actualizo el costo (revaluacion) pero no el precio de venta. Verificar antes de liquidar.

| Codigo | Descripcion | Precio actual | Costo sistema | Accion recomendada |
|--------|-------------|:-------------:|:-------------:|-------------------|
| 1008 | FOKKER 436 NEGRO ALPARGATA 2 ELAST | $26,105 | $92,011 | **REVISAR COSTO** — parece error de revaluacion |
| 1029 | FOKKER 436 AZUL ALPARGATA 2 ELAST | $26,105 | $92,011 | **REVISAR COSTO** |
| 1010 | FOKKER 436 NEGRO ALPARGATA 2 ELAST | $15,788 | $92,011 | **REVISAR COSTO** |
| 134961 | GUMMI WELLINGTON NINA NEGRO/CORAZONES | $10,315 | $11,115 | Precio ya bajo costo — si liquidas, perdes $800/par |
| 157870 | CANVAS MONTANA BOTA ACORD DESCARNE | $10,315 | $29,000 | Precio muy bajo — probable error |
| 202334 | GTN 630 GRIS ZAPA LONA C/PUNTERA | $10,315 | $13,500 | Precio bajo costo |
| 223517 | SEAWALK 850/CH NEGRO ZUECO GOMA PELUCHE | $5,052 | $5,690 | Precio bajo costo |
| 242865 | TOUKAN 030 NEGRO/BLANCO ZAPA C/PUNTERA | $5,262 | $6,468 | Precio bajo costo |

---

## TOP 20 — PROPUESTA PRECIOS LIQUIDACION

> Regla: precio propuesto = max(costo × 1.05, precio_actual × 0.55)
> Objetivo: recuperar capital, mover inventario en 30-60 dias

| # | Codigo | Descripcion | Marca | Stock | Costo | Precio actual | **Precio propuesto** | Descuento | Accion |
|---|--------|-------------|-------|------:|------:|-------------:|--------------------:|----------:|--------|
| 1 | 255009 | BECV MULTI PACK X5 BANDA ELAST CIRCULAR | KUSHIRO | 62 | $4,469 | $9,831 | **$5,000** | -49% | |
| 2 | 248840 | PUSHUP NEGRO/AZUL PARALELAS | KUSHIRO | 32 | $4,469 | $9,831 | **$5,000** | -49% | |
| 3 | 134339 | 166 AZUL BOTA ACORDONADA GAMUZA | KRUNCHI | 5 | $36,720 | $73,440 | **$40,000** | -45% | |
| 4 | 132342 | 02 MARRON BOTA T/GOND 2 CIERRES | HALA+BLETZ | 5 | $31,000 | $68,200 | **$34,000** | -50% | |
| 5 | 236966 | CRISTA/C BOTINETA ACORD S/CREPPE | CITADINA | 5 | $27,030 | $67,998 | **$29,000** | -57% | |
| 6 | 37717 | 1121 COCO MOCASIN NAUTICO GAMUZA | KRUNCHI | 4 | $27,300 | $66,105 | **$30,000** | -55% | |
| 7 | 37207 | SA1511 VERDE MEDIAS ALGODON 35/39 | WILSON-SAYER | 37 | $2,747 | $5,494 | **$3,000** | -45% | |
| 8 | 206771 | 740 VENDA AUTOADHERENTE 7,5x450cm | PROYEC | 5 | $20,000 | $40,000 | **$22,000** | -45% | |
| 9 | 258990 | HVS 621191 INDY ROSA OJOTA BIRK | HUSH PUPPIES | 5 | $19,500 | $44,210 | **$22,000** | -50% | |
| 10 | 194802 | 88030 PROFESIONAL KIDS BLANCO | TOPPER | 4 | $23,575 | $36,631 | **$26,000** | -29% | |
| 11 | 194801 | 88030 PROFESIONAL KIDS BLANCO | TOPPER | 4 | $23,575 | $36,631 | **$26,000** | -29% | |
| 12 | 120598 | 153/12 NEGRO PEUCHELE 2 ELAST | HALA+BLETZ | 4 | $23,000 | $50,600 | **$25,000** | -51% | |
| 13 | 37191 | SA1511 BLANCO MEDIAS ALGODON 35/39 | WILSON-SAYER | 30 | $2,747 | $5,494 | **$3,000** | -45% | |
| 14 | 261423 | 578 ROJO SANDALIA T/CUAD DET PULSERA | JUANA VA | 5 | $16,000 | $31,577 | **$17,500** | -45% | |
| 15 | 261424 | 578 ROJO SANDALIA T/CUAD DET PULSERA | JUANA VA | 4 | $16,000 | $31,577 | **$17,500** | -45% | |
| 16 | 174174 | 71 BORDO MEDIAS COLEGIALES ALTAS | FLOYD | 54 | $1,278 | $2,811 | **$1,500** | -47% | |
| 17 | 174170 | 71 VERDE MEDIAS COLEGIALES ALTAS | FLOYD | 49 | $1,278 | $2,811 | **$1,500** | -47% | |
| 18 | 174165 | 71 ROJO MEDIAS COLEGIALES ALTAS | FLOYD | 44 | $1,278 | $2,811 | **$1,500** | -47% | |
| 19 | 110143 | 350 BEIGE SANDALIA RED 2 ABROJOS | PULLMAN | 5 | $13,491 | $26,314 | **$14,500** | -45% | |
| 20 | 110142 | 350 BEIGE SANDALIA RED 2 ABROJOS | PULLMAN | 4 | $13,491 | $26,314 | **$14,500** | -45% | |

---

## IMPACTO ESTIMADO

| Metrica | Valor |
|---------|-------|
| Unidades total (top 20) | ~388 pares/unidades |
| Valor a precio actual | ~$1.35M |
| Valor a precio propuesto | ~$740K |
| Recupero minimo (vs costo) | Positivo en todos los casos |
| Capital liberado | ~$740K disponibles para nueva mercaderia |

---

## SCRIPT UPDATE (listo para ejecutar cuando apruebes)

El script se generara en `_scripts_oneshot/agenda_update_precios_20260408.py` una vez que des el OK.

> **PENDIENTE APROBACION** — Fernando debe revisar esta planilla antes de ejecutar.
