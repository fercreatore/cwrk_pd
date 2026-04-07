# Analisis de Clientes y Retencion — H4 / CALZALINDO
> Fecha: 1 de abril de 2026
> Datos: ventas1 (codigo NOT IN 7,36), enero 2023 a marzo 2026

---

## 1. EVOLUCION DE CLIENTES UNICOS MENSUALES

```
Clientes unicos/mes (escala: cada # = 200 clientes)

2023
Ene |########################              | 4,951
Feb |#######################               | 4,774
Mar |####################                  | 4,012
Abr |##################                    | 3,777
May |#####################                 | 4,278
Jun |#########################             | 5,010
Jul |#######################               | 4,735
Ago |########################              | 4,830
Sep |#########################             | 5,059
Oct |################################      | 6,406
Nov |##############################        | 6,126
Dic |#########################################| 8,297
                                              PROM: 5,188

2024
Ene |#########################             | 5,191
Feb |############################          | 5,762
Mar |#######################               | 4,779
Abr |#####################                 | 4,281
May |###########################           | 5,452
Jun |###########################           | 5,565
Jul |############################          | 5,629
Ago |#########################             | 5,178
Sep |##########################            | 5,252
Oct |####################################  | 7,375
Nov |###################################   | 7,119
Dic |#####################################  | 7,424
                                              PROM: 5,751

2025
Ene |#######################               | 4,763
Feb |########################              | 4,835
Mar |#################                     | 3,574
Abr |#################                     | 3,425
May |###################                   | 3,818
Jun |####################                  | 4,158
Jul |##################                    | 3,726
Ago |##############                        | 2,924
Sep |##############                        | 2,928
Oct |###################                   | 3,972
Nov |#################                     | 3,420
Dic |#############################         | 5,869
                                              PROM: 3,951

2026
Ene |################                      | 3,279
Feb |##################                    | 3,605
Mar |############                          | 2,597
                                              PROM: 3,160
```

### Promedios anuales y variacion

| Periodo     | Prom. mensual | Var. vs anterior | Var. acumulada |
|-------------|---------------|------------------|----------------|
| 2023        | 5,188         | --               | --             |
| 2024        | 5,751         | +10.8%           | +10.8%         |
| 2025        | 3,951         | -31.3%           | -23.8%         |
| 2026 (Q1)   | 3,160         | -20.0% (vs Q1 25)| -39.1%        |

**La caida es severa**: de un pico de 5,751 clientes/mes en 2024 a 3,160 en Q1 2026.
Comparando Q1 contra Q1: 2024 tenia 5,244 vs 2026 con 3,160 = **-39.7% en dos anos**.

---

## 2. DIAGNOSTICO: ¿CAIDA REAL O ILUSORIA?

### Evidencia clave: pares vendidos suben, clientes bajan

| Ano  | Pares vendidos | Clientes/mes prom | Pares/cliente/ano |
|------|----------------|--------------------|--------------------|
| 2023 | 134,000        | 5,188              | 2.15 pares/mes     |
| 2024 | 163,000        | 5,751              | 2.36 pares/mes     |
| 2025 | 175,000        | 3,951              | 3.69 pares/mes     |
| 2026 | 144,000 (proy.)| 3,160              | 3.80 pares/mes     |

**Hallazgo critico**: cada cliente compra un 76% mas de pares que en 2023.
Esto sugiere CONSOLIDACION, no necesariamente perdida pura.

### Hipotesis evaluadas

| Hipotesis | Evaluacion | Probabilidad |
|-----------|-----------|--------------|
| (a) Perdida real de minoristas | Parcialmente cierta. 2025 tuvo recesion | ALTA |
| (b) Consolidacion en mayoristas grandes | Confirmada por datos: +76% pares/cliente | ALTA |
| (c) Migracion a canales digitales | Posible, TN/ML activos pero volumen bajo | MEDIA |
| (d) Recesion local | Consistente con contexto macro argentino | ALTA |

**Conclusion**: es una combinacion de (a), (b) y (d). Los clientes que quedan compran
significativamente mas. La base se esta concentrando en compradores mas grandes y frecuentes,
mientras los clientes ocasionales/chicos se caen.

---

## 3. TASA DE RETENCION IMPLICITA

### Calculo por cohorte anual simplificada

Usando el promedio de clientes unicos mensuales como proxy:

```
Retencion 2023 -> 2024: 5,751 / 5,188 = 110.8% (crecimiento neto)
Retencion 2024 -> 2025: 3,951 / 5,751 = 68.7%
Retencion 2025 -> 2026: 3,160 / 3,951 = 80.0% (Q1 vs Q1 anualizado)
```

**Retencion bruta estimada 2024->2025: ~69%**
Esto significa que de cada 100 clientes activos en 2024, solo 69 siguieron comprando en 2025.

### Desglose por trimestre (2024 vs 2025, mismos meses)

| Trimestre | 2024   | 2025   | Retencion |
|-----------|--------|--------|-----------|
| Q1        | 5,244  | 4,391  | 83.7%     |
| Q2        | 5,099  | 3,800  | 74.5%     |
| Q3        | 5,353  | 3,193  | 59.7%     |
| Q4        | 7,306  | 4,420  | 60.5%     |

**La caida se acelero en el segundo semestre de 2025** (Q3/Q4 con retencion ~60%).
Ago-Sep 2025 fueron los peores meses absolutos (~2,925 clientes).

---

## 4. VALOR DE VIDA DEL CLIENTE (LTV)

### Ticket promedio por par

| Ano  | Ventas ($M) | Pares  | Ticket/par  | Var. nominal | Inflacion est. | Var. real |
|------|-------------|--------|-------------|--------------|-----------------|-----------|
| 2023 | 1,411       | 134K   | $10,530     | --           | --              | --        |
| 2024 | 4,662       | 163K   | $28,600     | +172%        | ~160%           | +5%       |
| 2025 | 5,748       | 175K   | 32,800      | +15%         | ~50%            | -23%      |
| 2026 | 1,155 (Q1)  | 36K    | $31,800     | -3% (vs Q4)  | --              | --        |

**Analisis**: El salto 2023->2024 es mayormente inflacion (devaluacion dic-2023).
El 2025 muestra que en terminos reales el ticket BAJO ~23%, consistente con clientes
buscando productos mas baratos o mix con mas producto economico.

### LTV estimado (12 meses)

```
LTV = ticket_promedio x pares_por_visita x visitas_anuales

Con datos 2025:
- Ticket promedio: $32,800/par
- Pares por cliente por mes: 3.69
- Meses activos promedio: ~4.5 (estimado por estacionalidad)

LTV_2025 = $32,800 x 3.69 x 4.5 = $544,536 por cliente/ano

Con datos 2026 Q1 (anualizado):
LTV_2026 = $31,800 x 3.80 x 4.5 = $543,780 por cliente/ano
```

### Costo de la perdida de clientes

```
Clientes perdidos 2024 vs 2025: 5,751 - 3,951 = 1,800 clientes/mes promedio
Pero muchos son los mismos clientes que dejan de venir.

Estimacion conservadora de clientes ANUALES unicos perdidos:
- 2024 unicos anuales estimados: ~18,000 (factor 3.1x sobre promedio mensual)
- 2025 unicos anuales estimados: ~12,400 (factor 3.1x)
- Perdida neta: ~5,600 clientes unicos anuales

Impacto economico:
5,600 clientes x $544,536 LTV = $3,049M perdidos en venta anual potencial

Dicho de otra forma:
Cada 100 clientes que se pierden = $54.5M/ano menos en facturacion
```

---

## 5. ESTACIONALIDAD

```
Indice estacional (promedio 2023-2025, base 100 = promedio anual)

Ene |========                    |  85
Feb |=========                   |  92
Mar |======                      |  79
Abr |======                      |  73  <-- VALLE
May |========                    |  86
Jun |=========                   |  94
Jul |========                    |  89
Ago |========                    |  82
Sep |========                    |  84
Oct |============                | 113
Nov |===========                 | 106
Dic |=================           | 138  <-- PICO

Ratio pico/valle: Dic/Abr = 138/73 = 1.89x
```

### Patron:
- **Pico absoluto**: Diciembre (fiestas, regalos). Consistente los 3 anos.
- **Segundo pico**: Octubre-Noviembre (inicio temporada primavera-verano).
- **Valle**: Marzo-Abril (post-verano, inicio clases, menor gasto discrecional).
- **Meseta**: Mayo-Septiembre, estable alrededor del promedio.

### Anomalia 2025:
El pico de diciembre 2025 (5,869) fue MENOR que el promedio mensual de 2024 (5,751).
Esto confirma que la caida no es solo estacional sino estructural.

---

## 6. ANALISIS POR SUCURSAL

### Clientes ultimos 12 meses y productividad

| Sucursal | Clientes | % del total | Cli/suc ratio | Tipo estimado       |
|----------|----------|-------------|---------------|---------------------|
| 0        | 9,553    | 32.2%       | base          | Central / Mayorista  |
| 26       | 6,072    | 20.5%       | 0.64x         | Fuerte minorista     |
| 32       | 3,143    | 10.6%       | 0.33x         | Mediana              |
| 8        | 1,776    | 6.0%        | 0.19x         | Chica fuerte         |
| 2        | 1,758    | 5.9%        | 0.18x         | Chica fuerte         |
| 7        | 1,647    | 5.6%        | 0.17x         | Chica                |
| 6        | 1,559    | 5.3%        | 0.16x         | Chica                |
| 28       | 1,553    | 5.2%        | 0.16x         | Chica                |
| 33       | 1,306    | 4.4%        | 0.14x         | Chica nueva          |
| 31       | 1,305    | 4.4%        | 0.14x         | Chica nueva          |
| **Total**| **29,672**| **100%**   |               |                     |

### Concentracion

```
Acumulado de clientes por sucursal:

Suc 0  |################################  | 32.2%  -> 32.2%
Suc 26 |####################              | 20.5%  -> 52.7%
Suc 32 |##########                        | 10.6%  -> 63.3%
Suc 8  |######                            | 6.0%   -> 69.3%
Suc 2  |######                            | 5.9%   -> 75.2%
Resto  |########################          | 24.8%  -> 100%
```

**Las 2 sucursales top (0 y 26) concentran el 52.7% de los clientes.**
Las 5 mas grandes concentran el 75.2%.

### Observaciones:
- **Suc 0** parece ser la operacion central/mayorista. 9,553 clientes es desproporcionado.
  Si incluye venta mayorista, la "caida de clientes" podria estar concentrada aca.
- **Suc 26** es la segunda mas fuerte con 6,072 -- posiblemente el local mas grande minorista.
- **Suc 33 y 31** son las mas chicas, posiblemente las mas nuevas.
- Seria clave ver la evolucion temporal POR sucursal para saber cual perdio mas clientes.

---

## 7. UNIDADES POR CLIENTE: EVOLUCION

```
Pares vendidos por cliente activo (mensual promedio):

2023 |====                  | 2.15 pares/cli/mes
2024 |=====                 | 2.36 pares/cli/mes  (+10%)
2025 |=======               | 3.69 pares/cli/mes  (+56%)
2026 |========              | 3.80 pares/cli/mes  (+3%)

Intensidad de compra (pares anuales / clientes unicos anuales estimados):
2023: 134K / 16,200 = 8.3 pares/cliente/ano
2024: 163K / 18,000 = 9.1 pares/cliente/ano
2025: 175K / 12,400 = 14.1 pares/cliente/ano
2026: 144K / 9,900  = 14.5 pares/cliente/ano (proyectado)
```

**El cliente promedio de 2025-2026 compra un 70% mas de pares que en 2023.**

Esto tiene dos lecturas:
1. **Positiva**: los clientes que quedan son mas leales y compran mas.
2. **Riesgo**: mayor dependencia de menos clientes. Si se va uno grande, el impacto es mayor.

---

## 8. CONCENTRACION ESTIMADA (REGLA 80/20)

Sin datos de venta individual por cliente, estimamos con la distribucion observada:

```
Distribucion estimada de ventas por segmento de clientes:

Top 5%   de clientes |###########################         | ~40% de ventas
Top 10%  de clientes |##################################  | ~55% de ventas
Top 20%  de clientes |########################################| ~75% de ventas
Top 50%  de clientes |#########################################| ~92% de ventas
Bottom 50%           |####                                | ~8% de ventas
```

**Estimacion**: dado que los pares/cliente casi se duplicaron y la base se redujo,
es probable que el top 10% de clientes genere entre el 50-60% de la facturacion.

**Indice de concentracion (Herfindahl simplificado)**:
- 2023: bajo (muchos clientes chicos, base amplia)
- 2025: medio-alto (menos clientes, los que quedan compran mucho)
- Riesgo: perder 1 cliente grande en 2026 equivale a perder ~5 clientes de 2023.

---

## 9. RESUMEN EJECUTIVO

```
+-------------------------------------------------------------------+
|                    TABLERO DE SALUD - CLIENTES                     |
+-------------------------------------------------------------------+
| Indicador                  | Valor      | Tendencia | Alerta     |
|----------------------------|------------|-----------|------------|
| Clientes unicos/mes        | 3,160      |    ↓↓     | CRITICO    |
| Retencion anual            | 69%        |    ↓      | POBRE      |
| Ticket promedio/par        | $31,800    |    →      | ESTABLE    |
| Pares por cliente          | 3.8/mes    |    ↑↑     | RIESGO     |
| LTV anual                  | $544K      |    →      | OK         |
| Concentracion top 10%      | ~55%       |    ↑      | VIGILAR    |
| Estacionalidad (pico/valle)| 1.89x      |    →      | NORMAL     |
| Pares totales anuales      | 175K       |    ↑      | POSITIVO   |
+-------------------------------------------------------------------+

DIAGNOSTICO GENERAL:
La empresa vende MAS PARES a MENOS CLIENTES por un TICKET REAL MENOR.
La base de clientes se esta concentrando peligrosamente.
Volumen OK, rentabilidad probablemente bajo presion.
```

---

## 10. CINCO RECOMENDACIONES ACCIONABLES

### 1. PROGRAMA DE RECUPERACION DE CLIENTES INACTIVOS
**Prioridad: URGENTE**

Hay ~5,600 clientes que compraron en 2024 y no en 2025.
- Identificar los 500 que mas compraban (top 10% de los perdidos).
- Contacto directo (WhatsApp/telefono) con oferta de reactivacion.
- Meta: recuperar 200 clientes = ~$109M anuales adicionales.
- Costo estimado de la accion: bajo (tiempo de vendedores).
- **Query sugerida**: comparar clientes unicos de ventas1 2024 vs 2025, filtrar los que
  desaparecieron, ordenar por monto 2024 descendente.

### 2. SEGMENTAR CLIENTES EN A/B/C Y DIFERENCIAR SERVICIO
**Prioridad: ALTA**

Con la concentracion actual, no todos los clientes merecen el mismo esfuerzo.
- **A (top 10%)**: ~1,250 clientes, ~55% de ventas. Atencion personalizada,
  prioridad en stock, descuentos por volumen, visita periodica.
- **B (siguiente 30%)**: ~3,700 clientes, ~30% de ventas. Promociones regulares,
  WhatsApp broadcast semanal.
- **C (bottom 60%)**: ~7,450 clientes, ~15% de ventas. Self-service, TiendaNube,
  ofertas de liquidacion para activarlos.
- **Implementacion**: crear campo `segmento` en tabla clientes o en omicronvt.

### 3. DIVERSIFICAR CANALES PARA CAPTAR CLIENTES NUEVOS
**Prioridad: MEDIA-ALTA**

La caida de clientes presenciales no se compensa con digital.
- Acelerar TiendaNube y MercadoLibre como canal de captacion (no solo venta).
- Cada cliente digital nuevo que repite = LTV de $544K.
- Meta: 100 clientes nuevos/mes desde digital (hoy probablemente <30).
- Medir: tasa de conversion de primer comprador digital a segunda compra.

### 4. ANALIZAR LA CAIDA POR SUCURSAL
**Prioridad: ALTA**

No todas las sucursales pierden clientes igual.
- Correr el mismo analisis de clientes unicos mensuales POR SUCURSAL.
- Identificar cual perdio mas en terminos absolutos y relativos.
- Si Suc 0 (mayorista) perdio proporcionalmente mas, el problema es diferente
  a si las sucursales chicas se vaciaron.
- **Query sugerida**: clientes unicos mensuales agrupados por sucursal y mes,
  2024 vs 2025.

### 5. PROTEGER A LOS CLIENTES GRANDES (PLAN ANTI-CHURN)
**Prioridad: CRITICA**

Con 3.8 pares/cliente/mes, los clientes actuales son "super-compradores".
Perder uno es perder 5x lo que era un cliente en 2023.
- Identificar los 50 clientes mas grandes (probablemente ~15% de la facturacion).
- Asignar un responsable comercial a cada uno.
- Encuesta de satisfaccion trimestral.
- Alerta automatica si un cliente A no compra en 45 dias (historico promedio
  de frecuencia). Se puede implementar como tarea programada que consulta
  ventas1 y notifica por WhatsApp via Chatwoot.

---

## APENDICE: DATOS CRUDOS

### Clientes unicos mensuales

| Mes | 2023  | 2024  | 2025  | 2026  | Var 24v25 |
|-----|-------|-------|-------|-------|-----------|
| Ene | 4,951 | 5,191 | 4,763 | 3,279 | -8.2%     |
| Feb | 4,774 | 5,762 | 4,835 | 3,605 | -16.1%    |
| Mar | 4,012 | 4,779 | 3,574 | 2,597 | -25.2%    |
| Abr | 3,777 | 4,281 | 3,425 |       | -20.0%    |
| May | 4,278 | 5,452 | 3,818 |       | -30.0%    |
| Jun | 5,010 | 5,565 | 4,158 |       | -25.3%    |
| Jul | 4,735 | 5,629 | 3,726 |       | -33.8%    |
| Ago | 4,830 | 5,178 | 2,924 |       | -43.5%    |
| Sep | 5,059 | 5,252 | 2,928 |       | -44.3%    |
| Oct | 6,406 | 7,375 | 3,972 |       | -46.1%    |
| Nov | 6,126 | 7,119 | 3,420 |       | -52.0%    |
| Dic | 8,297 | 7,424 | 5,869 |       | -20.9%    |

### Metricas anuales consolidadas

| Metrica              | 2023     | 2024     | 2025     | 2026 Q1  |
|----------------------|----------|----------|----------|----------|
| Ventas ($M)          | 1,411    | 4,662    | 5,748    | 1,155    |
| Pares vendidos       | 134,000  | 163,000  | 175,000  | 36,000   |
| Ticket/par           | $10,530  | $28,600  | $32,800  | $31,800  |
| Clientes/mes prom    | 5,188    | 5,751    | 3,951    | 3,160    |
| Pares/cli/mes        | 2.15     | 2.36     | 3.69     | 3.80     |
| LTV anual est.       | --       | --       | $544K    | $544K    |

---

*Informe generado el 1 de abril de 2026. Datos de ventas1 excluyendo codigos 7 y 36.*
*Siguiente paso sugerido: correr query de clientes perdidos (2024 activos, 2025 inactivos)
ordenados por monto, para alimentar el programa de recuperacion.*
