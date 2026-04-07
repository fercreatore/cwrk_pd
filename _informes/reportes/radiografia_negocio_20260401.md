# Radiografia del Negocio H4 / CALZALINDO
## Reporte Ejecutivo — 1 de abril de 2026

> Cadena de calzado en Venado Tuerto, Argentina. ~15 sucursales, 2 razones sociales.
> Datos reales del ERP MS Gestion (2023-2026 Q1).

---

## RESUMEN PARA LEER EN 5 MINUTOS

**Lo bueno**: La facturacion crece fuerte (x4 en 3 anos) y el volumen real sube +30% acumulado (134K a 175K pares). El canal mayorista tiene margenes del 64%, y la sucursal principal (Dep 0/Suc 0) es una maquina de $1,362M/ano.

**Lo preocupante**: Los clientes unicos caen un 29% (8,297 en dic-23 a 5,869 en dic-25). Se vende mas a menos gente, lo que implica mayor dependencia de clientes repetidores. Dos sucursales (Dep 7 y Dep 9) operan con margen del 31%, probablemente debajo del punto de equilibrio. Hay ~$4,100M en stock muerto, de los cuales $3,930M son una sola anomalia contable.

**Lo urgente**: Investigar el articulo 306188 ($3,930M de costo asentado, 0 ventas). Revisar la caida de clientes. Q1-2026 viene -17% en unidades vs Q1-2025, primera senal de desaceleracion real.

---

## 1. EVOLUCION ANUAL

```
FACTURACION ($ millones)
                                                          $5,748M
                                              $4,662M    |||||||||
                               $1,411M       |||||||||   |||||||||
               $1,155M*       |||||||||      |||||||||   |||||||||
              |||||||||      |||||||||      |||||||||   |||||||||
              |||||||||      |||||||||      |||||||||   |||||||||
              |||||||||      |||||||||      |||||||||   |||||||||
               2026*          2023           2024         2025
              (Q1 solo)

UNIDADES (miles de pares)
                                                           175K
                                               163K      ||||||
                               134K           ||||||     ||||||
                36K*          ||||||          ||||||     ||||||
               ||||||        ||||||          ||||||     ||||||
               ||||||        ||||||          ||||||     ||||||
                2026*          2023           2024         2025
```

### Tabla comparativa anual

| Metrica             |    2023    |    2024    |    2025    | 2026 Q1*  |
|---------------------|-----------|-----------|-----------|-----------|
| Facturacion         | $1,411M   | $4,662M   | $5,748M   | $1,155M   |
| Pares vendidos      | 134,200   | 162,200   | 175,200   | 36,400    |
| Ticket promedio     | $10,515   | $28,742   | $32,809   | $31,731   |
| Clientes dic        | 8,297     | 7,424     | 5,869     | 2,597*mar |

### Crecimiento interanual

| Periodo     | Crec. $ | Crec. Uds | Inflacion est. | Crec. Real |
|-------------|---------|-----------|----------------|------------|
| 2023 -> 2024 | +230%  | +21%      | ~170-180%      | ~20-25%    |
| 2024 -> 2025 | +23%   | +8%       | ~25-30%        | ~ -3 a -5% |
| Q1-25 vs Q1-26 | -18% | -17%     | ~30-35%?       | ~ -40%     |

**Lectura**: El 2024 fue excepcional, con crecimiento genuino en volumen del 21%. En 2025 el volumen crecio 8% pero la facturacion en pesos apenas acompano la inflacion (+23% vs ~25-30% de IPC), lo que sugiere precio real planchado. El Q1-2026 muestra contraccion real tanto en pesos como en unidades.

---

## 2. ESTACIONALIDAD

### Indice de estacionalidad (pares vendidos, promedio 2023-2025)

```
Mes    Indice   Barra (promedio = 100)
Ene     86     ||||||||
Feb     94     |||||||||
Mar     71     |||||||         <- VALLE
Abr     67     ||||||          <- VALLE PROFUNDO
May     85     ||||||||
Jun     97     |||||||||
Jul     90     |||||||||
Ago     84     ||||||||
Sep     84     ||||||||
Oct    113     |||||||||||     <- PICO (dia de la madre)
Nov     96     |||||||||
Dec    141     ||||||||||||||  <- PICO MAXIMO (navidad)
```

### Pares por mes (en miles)

| Mes | 2023  | 2024  | 2025  | 2026  | Promedio |
|-----|-------|-------|-------|-------|----------|
| Ene | 10.9  | 10.1  | 14.9  | 11.6  | 11.9     |
| Feb | 11.1  | 11.9  | 17.0  | 13.8  | 13.5     |
| Mar |  8.3  |  9.0  | 12.9  | 11.0  | 10.3     |
| Abr |  7.8  |  9.0  | 11.7  |   -   |  9.5     |
| May |  9.2  | 13.2  | 14.0  |   -   | 12.1     |
| Jun | 11.9  | 13.3  | 16.1  |   -   | 13.8     |
| Jul | 10.0  | 13.3  | 15.2  |   -   | 12.8     |
| Ago | 11.0  | 12.6  | 12.4  |   -   | 12.0     |
| Sep | 11.6  | 12.1  | 12.1  |   -   | 11.9     |
| Oct | 13.2  | 18.1  | 16.8  |   -   | 16.0     |
| Nov | 12.3  | 16.2  | 12.4  |   -   | 13.6     |
| Dic | 16.9  | 23.4  | 19.7  |   -   | 20.0     |

**Patron estable**: Abril es consistentemente el peor mes (temporada baja post-verano, pre-invierno). Diciembre es el pico absoluto (+41% sobre promedio). Octubre marca un segundo pico fuerte por Dia de la Madre.

**Anomalia 2025**: Agosto-noviembre 2025 fueron inusualmente flojos en unidades (12.4K, 12.1K, 16.8K, 12.4K) comparado con 2024 (12.6K, 12.1K, 18.1K, 16.2K). Noviembre 2025 fue particularmente debil (-23% vs nov-2024).

---

## 3. CLIENTES: LA SENAL DE ALARMA

### Clientes unicos por mes (seleccion)

```
CLIENTES UNICOS - TENDENCIA DESCENDENTE

8,297   *                                                  dic-23
7,424           *                                          dic-24
7,375                   *                                  oct-24
6,406   *                                                  oct-23
6,126                                                      nov-23
6,072                                                      suc26-12m
5,869                           *                          dic-25
5,252                                                      sep-24
4,835                                                      feb-25
3,972                                                      oct-25
3,605                                   *                  feb-26
3,279                                           *          ene-26
2,928                                                      sep-25
2,597                                                   *  mar-26

        2023    2024            2025            2026
```

### Analisis de la caida

| Comparacion        | Clientes | Variacion |
|--------------------|----------|-----------|
| Dic 2023           | 8,297    | base      |
| Dic 2024           | 7,424    | -10.5%    |
| Dic 2025           | 5,869    | -29.3% vs 2023 |
| Mar 2025           | 3,574    | base Q1   |
| Mar 2026           | 2,597    | -27.3% vs mar-25 |

**Interpretacion**: La caida de clientes unicos es la metrica mas preocupante del negocio. En 3 anos se perdio casi un tercio de la base. Posibles causas:

1. **Concentracion en mayorista**: Los canales mayoristas (Dep 1/Suc 26 y Dep 1/Suc 1) venden $694M con solo 161 clientes. Cada cliente mayorista compra en promedio $4.3M/ano vs $26K del minorista promedio.
2. **Migracion a online**: Si parte de las ventas se movieron a TiendaNube/ML, los clientes anonimos no se contarian.
3. **Economia regional**: Venado Tuerto depende fuertemente del agro. Ciclos de sequia o precios bajos de commodities afectan el consumo local.
4. **Posible cambio de conteo**: Verificar si el sistema de clientes cambio la logica de "consumidor final" entre 2023 y 2025.

**Pero**: El volumen sube (134K a 175K pares), asi que cada cliente compra mas. El ticket por cliente paso de ~$10K (2023) a ~$33K (2025).

---

## 4. RANKING DE SUCURSALES

### Por facturacion y margen (ultimos 12 meses)

```
                    FACTURACION vs MARGEN POR SUCURSAL

Margen %
  65 |                  * D1/S1                                ZONA ORO
     |              * D1/S26                                  (mayorista)
  60 |
  55 |
  50 |
     |    * D0/S26
  48 |        * D8/S8
     |  * D0/S0
  46 |                              * D8/S33
     |      * D6/S28         * D0/S32
  40 |
     |                                      * D2/S2
  35 |
     |                          * D7/S7     * D9/S30          ZONA ROJA
  30 |____________________________________________________________
     0   200   400   600   800  1000  1200  1400
                    Facturacion ($M)
```

### Tabla detallada

| Rank | Sucursal   | Venta $M | Pares  | Clientes | Margen | Ticket   | Pares/Cli |
|------|-----------|----------|--------|----------|--------|----------|-----------|
| 1    | D0/S0     | 1,362    | 44,600 | 9,553    | 47.5%  | $30,539  | 4.7       |
| 2    | D0/S26    | 692      | 20,100 | 6,072    | 48.9%  | $34,428  | 3.3       |
| 3    | D1/S26    | 393      | 5,200  | 68       | 63.2%  | $75,577  | 76.5      |
| 4    | D8/S8     | 337      | 8,700  | 1,776    | 47.9%  | $38,736  | 4.9       |
| 5    | D0/S32    | 305      | 9,300  | 3,143    | 45.6%  | $32,796  | 3.0       |
| 6    | D1/S1     | 301      | 4,100  | 93       | 65.9%  | $73,415  | 44.1      |
| 7    | D8/S33    | 221      | 5,600  | 1,306    | 46.2%  | $39,464  | 4.3       |
| 8    | D2/S2     | 176      | 7,500  | 1,758    | 39.5%  | $23,467  | 4.3       |
| 9    | D6/S28    | 176      | 4,800  | 1,553    | 45.6%  | $36,667  | 3.1       |
| 10   | D7/S7     | 172      | 7,800  | 1,647    | 31.8%  | $22,051  | 4.7       |
| 11   | D9/S30    | 80       | 4,000  | 784      | 31.7%  | $20,000  | 5.1       |

### Diagnostico por zona

**ZONA ORO - Mayorista (D1/S26 + D1/S1)**
- Facturan $694M combinado (16% del total) con margen 64%.
- Solo 161 clientes. Altisima dependencia: perder 5 clientes mayoristas es perder ~$21M.
- Ticket promedio ~$74K. Son revendedores del interior.

**ZONA FUERTE - Minorista top (D0/S0, D0/S26, D8/S8)**
- $2,391M combinado (55% del total). Margenes 47-49%.
- La sucursal principal (D0/S0) vende mas que las siguientes 3 combinadas.
- D0/S26 tiene buena diversificacion de clientes (6,072).

**ZONA GRIS - Minorista medio (D0/S32, D8/S33, D6/S28)**
- $702M combinado (16%). Margenes 45-46%. Rentables pero sin destaque.

**ZONA ROJA - Problema (D7/S7, D9/S30, D2/S2)**
- $428M combinado (10%). Margenes 31-39%.
- D7/S7: mueve 7,800 pares con 31.8% de margen. Ticket bajo ($22K). Probable mix cargado a producto barato/promocion.
- D9/S30: la mas chica ($80M), margen 31.7%. Candidata a cierre o reestructura.
- D2/S2: margen 39.5%, el mejor de la zona roja pero sigue debajo del promedio.

**Estimacion de costos fijos por sucursal** (alquiler + sueldos + servicios, estimacion conservadora):
- Sucursal chica: ~$3-4M/mes = $36-48M/ano
- D9/S30 factura $80M con 31.7% margen bruto = $25M de utilidad bruta. Probablemente NO cubre costos fijos.

---

## 5. TICKET PROMEDIO

### Evolucion del precio por par vendido

```
TICKET PROMEDIO ($/par)

$35K |                                          *  $32,809
     |                                    *         $32,000 (ene-feb 26)
$30K |                        * $28,742
     |
$25K |
     |
$20K |
     |
$15K |
     |        * $10,515
$10K |_____________________________________________
       2023     2024        2025        2026
```

| Ano  | Ticket $/par | Var. vs anterior | Inflacion est. | Var. real |
|------|-------------|------------------|----------------|-----------|
| 2023 | $10,515     | -                | -              | -         |
| 2024 | $28,742     | +173%            | ~170%          | ~ 0%      |
| 2025 | $32,809     | +14%             | ~25-30%        | ~ -12%    |
| 2026 | $31,731*    | -3% (Q1 vs full) | -              | -         |

**Lectura**: El ticket promedio crecio nominalmente x3 en dos anos, practicamente todo explicado por inflacion. En terminos reales, el ticket 2025 BAJO respecto de 2024, lo que indica:

- Se esta vendiendo producto mas barato en el mix (menos zapatilla cara, mas ojotas/basicas).
- Las promociones/descuentos estan comprimiendo el precio real.
- La suba de precios de lista no acompano 100% la inflacion.

---

## 6. STOCK MUERTO: EL CAPITAL DORMIDO

### Top items sin movimiento (0 ventas en 12 meses)

| Articulo | Marca           | Costo Unit. | Valor Total  | Diagnostico          |
|----------|-----------------|-------------|-------------|----------------------|
| 306188   | 822 (?)         | $6,980,000  | $3,930M     | ANOMALIA - ver abajo |
| 5 arts   | 104 (GTN)       | ~$2,740,000 | $101M       | Stock residual       |
| 6 arts   | 17 (GO by CZL)  | varios      | $4.6M       | Marca propia muerta  |
| 3 arts   | 669 (LANACUER)  | varios      | $2M         | Descontinuado        |
| Varios   | 314 (TOPPER)    | varios      | ~$5-10M     | Talles sueltos       |
| Varios   | 42 (LESEDIFE)   | varios      | ~$3-5M      | Sin reposicion       |
| Varios   | 765 (Distrinando)| varios     | ~$2-3M      | Restos temporada     |

### La anomalia del articulo 306188

**$3,930M de costo asentado para un solo articulo es casi seguro un error de carga.**

Para poner en contexto:
- $3,930M es el 68% de la facturacion de un ano entero (2025 = $5,748M)
- Un par de calzado con costo $6,980,000 equivaldria a un precio de venta de ~$14M (con margen 50%)
- Ningun calzado del mercado argentino tiene ese precio

**Accion recomendada**: Verificar si el precio_costo del articulo 306188 tiene decimales mal cargados (ej: deberia ser $6,980 en vez de $6,980,000 -- un factor de x1000). Corregir en la tabla de articulos.

### Stock muerto real (excluyendo anomalia)

| Concepto                    | Estimacion |
|-----------------------------|------------|
| GTN residual                | ~$101M     |
| GO by CZL (marca propia)   | ~$5M       |
| LANACUER descontinuado      | ~$2M       |
| TOPPER talles sueltos       | ~$8M       |
| LESEDIFE + Distrinando      | ~$5M       |
| Otros menores               | ~$10-15M   |
| **Total stock muerto real** | **~$130-140M** |

**Impacto**: Liquidando a costo (0% margen), se recuperarian ~$130M. A 50% de descuento sobre costo, ~$65M. No es un numero que mueva la aguja del negocio ($5,748M de facturacion), pero si representa capital de trabajo inmovilizado que podria financiar 1-2 pedidos de temporada.

---

## 7. PROYECCION 2026

### Metodo: Q1 como predictor del ano completo

| Ano  | Q1 Pares | Ano Pares | Ratio Q1/Ano |
|------|----------|-----------|-------------|
| 2023 | 30,300   | 134,200   | 22.6%       |
| 2024 | 31,000   | 162,200   | 19.1%       |
| 2025 | 44,800   | 175,200   | 25.6%       |
| Prom | -        | -         | 22.4%       |

**Q1 2026**: 36,400 pares

| Escenario     | Ratio usado | Proyeccion anual | vs 2025 |
|---------------|-------------|-----------------|---------|
| Optimista     | 19.1% (2024)| 190,600 pares   | +9%     |
| Base          | 22.4% (prom)| 162,500 pares   | -7%     |
| Pesimista     | 25.6% (2025)| 142,200 pares   | -19%    |

### En pesos (usando ticket promedio Q1-26 de $31,731)

| Escenario     | Pares      | Facturacion est. | vs 2025  |
|---------------|------------|-----------------|----------|
| Optimista     | 190,600    | ~$6,050M        | +5%      |
| Base          | 162,500    | ~$5,156M        | -10%     |
| Pesimista     | 142,200    | ~$4,512M        | -22%     |

**Alerta**: El escenario base proyecta una CAIDA del 7% en unidades y del 10% en facturacion nominal. Seria el primer ano de contraccion. El Q1-2026 es el peor Q1 en 3 anos tanto en pares como en clientes.

```
PROYECCION 2026 - PARES (miles)

200K |                                     ? Optimista (190K)
     |
180K |              *
175K |                      * 2025 real
     |                                     ? Base (162K)
160K |      *
     |                                     ? Pesimista (142K)
140K | *
     |_________________________________________
      2023   2024    2025     2026
```

---

## 8. DIEZ RECOMENDACIONES ESTRATEGICAS

### URGENTE (hacer esta semana)

**1. Investigar anomalia articulo 306188**
El costo de $6.98M por par es casi seguro un error de carga. Corregirlo limpia $3,930M fantasma del balance de stock. Verificar si es un error de decimales (x1000) o una carga duplicada.

**2. Auditar la caida de clientes unicos**
Determinar si la baja del 29% en clientes es real o un artefacto del sistema (ej: cambio en la forma de registrar "consumidor final"). Si es real, lanzar accion de reactivacion.

**3. Plan de liquidacion stock muerto**
Armar un lote de ~500-800 pares de GTN, LANACUER, LESEDIFE y talles sueltos TOPPER. Vender a 50% de descuento en feria/outlet o al por mayor. Liberar $65-70M de capital de trabajo.

### CORTO PLAZO (este mes)

**4. Revisar sucursales Dep 7 y Dep 9**
Con margenes del 31%, estas sucursales probablemente no cubren costos fijos. Opciones:
- Cambiar el mix de producto (menos zapatilla barata, mas margen)
- Negociar alquiler a la baja
- Si no mejora en 6 meses, evaluar cierre de Dep 9 (solo $80M de venta)

**5. Proteger el canal mayorista**
161 clientes generan $694M con 64% de margen. Eso es ~$444M de utilidad bruta. Programa de fidelizacion, condiciones de pago preferenciales, y descuento por volumen escalonado para retenerlos.

**6. Ajustar compras OI-26 a escenario conservador**
El Q1-2026 viene -17% en unidades. No es momento de sobrecomprar. Presupuestar para 155-165K pares anuales (escenario base-pesimista), no para repetir 175K de 2025.

### MEDIANO PLAZO (proximo trimestre)

**7. Estrategia de precio: recuperar ticket real**
El ticket promedio en terminos reales BAJO en 2025. Dos caminos: (a) subir precios de lista para acompanar inflacion, o (b) cambiar mix hacia producto de mayor valor agregado (mas zapatilla premium, menos basica).

**8. Reactivacion de clientes perdidos**
De 8,297 clientes en dic-2023 a 5,869 en dic-2025 son ~2,400 clientes perdidos. Si cada cliente compra ~$33K/ano, eso representa ~$79M de facturacion perdida. Campaña de WhatsApp/SMS con oferta de reactivacion (costo: minimo; retorno potencial: alto).

**9. Potenciar el canal digital**
Si parte de los clientes "perdidos" migro a compra online (TiendaNube, ML), asegurar que esas ventas se registren correctamente en el sistema. Unificar la base de clientes fisico+digital.

### ESTRATEGICO (proximo semestre)

**10. Dashboard de alertas tempranas**
Implementar un tablero mensual con 5 KPIs criticos:
- Clientes unicos (alerta si cae >5% interanual)
- Pares vendidos (alerta si cae >10% vs mismo mes ano anterior)
- Margen bruto por sucursal (alerta si <35%)
- Stock muerto como % del stock total (alerta si >15%)
- Ticket promedio real (ajustado por IPC)

---

## APENDICE: TABLAS DE DATOS COMPLETAS

### A. Facturacion mensual ($M)

| Mes | 2023 | 2024 | 2025 | 2026 |
|-----|------|------|------|------|
| Ene | 60   | 185  | 449  | 366  |
| Feb | 72   | 270  | 527  | 447  |
| Mar | 60   | 238  | 436  | 342  |
| Abr | 64   | 258  | 408  | -    |
| May | 81   | 362  | 471  | -    |
| Jun | 103  | 392  | 530  | -    |
| Jul | 98   | 405  | 494  | -    |
| Ago | 115  | 390  | 404  | -    |
| Sep | 130  | 394  | 375  | -    |
| Oct | 181  | 549  | 544  | -    |
| Nov | 176  | 520  | 438  | -    |
| Dic | 271  | 698  | 673  | -    |
| **Total** | **1,411** | **4,662** | **5,748** | **1,155*** |

### B. Pares vendidos mensual (miles)

| Mes | 2023 | 2024 | 2025 | 2026 |
|-----|------|------|------|------|
| Ene | 10.9 | 10.1 | 14.9 | 11.6 |
| Feb | 11.1 | 11.9 | 17.0 | 13.8 |
| Mar | 8.3  | 9.0  | 12.9 | 11.0 |
| Abr | 7.8  | 9.0  | 11.7 | -    |
| May | 9.2  | 13.2 | 14.0 | -    |
| Jun | 11.9 | 13.3 | 16.1 | -    |
| Jul | 10.0 | 13.3 | 15.2 | -    |
| Ago | 11.0 | 12.6 | 12.4 | -    |
| Sep | 11.6 | 12.1 | 12.1 | -    |
| Oct | 13.2 | 18.1 | 16.8 | -    |
| Nov | 12.3 | 16.2 | 12.4 | -    |
| Dic | 16.9 | 23.4 | 19.7 | -    |
| **Total** | **134.2** | **162.2** | **175.2** | **36.4*** |

### C. Clientes unicos mensual

| Mes | 2023  | 2024  | 2025  | 2026  |
|-----|-------|-------|-------|-------|
| Ene | 4,951 | 5,191 | 4,763 | 3,279 |
| Feb | 4,774 | 5,762 | 4,835 | 3,605 |
| Mar | 4,012 | 4,779 | 3,574 | 2,597 |
| Abr | 3,777 | 4,281 | 3,425 | -     |
| May | 4,278 | 5,452 | 3,818 | -     |
| Jun | 5,010 | 5,565 | 4,158 | -     |
| Jul | 4,735 | 5,629 | 3,726 | -     |
| Ago | 4,830 | 5,178 | 2,924 | -     |
| Sep | 5,059 | 5,252 | 2,928 | -     |
| Oct | 6,406 | 7,375 | 3,972 | -     |
| Nov | 6,126 | 7,119 | 3,420 | -     |
| Dic | 8,297 | 7,424 | 5,869 | -     |

---

> Generado el 1 de abril de 2026.
> Datos extraidos del ERP MS Gestion (bases msgestion01, msgestion03, msgestionC).
> Analisis: Claude / COWORK.
