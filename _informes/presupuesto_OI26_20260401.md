# Presupuesto de Compras OI26 por Industria

**Fecha:** 1 de abril de 2026
**Periodo:** OI26 (abril - agosto 2026)
**Fuente:** Ventas OI25 vs OI24, stock actual al 01-abr-2026

---

## 1. Resumen Ejecutivo

El presupuesto OI26 totaliza **$1,535.5M** en costo de compras proyectado, un **31.2%** por encima de los $1,137.8M ejecutados en OI25. De ese monto, **$5,476.0M** ya estan invertidos en stock actual, lo que refleja una situacion de sobre-stock general heredada de temporadas anteriores. Solo **tres industrias** (Zapateria, Mixto y Indumentaria) tienen espacio real para compras nuevas, totalizando **$202.8M** disponibles.

Deportes concentra el 89% del valor de stock y presenta un sobre-stock extremo de $4,151M por encima de su presupuesto, lo cual requiere atencion especial (ver seccion de analisis).

---

## 2. Factor Tendencia OI25 vs OI24

Calculado como `venta_costo_OI25 / venta_costo_OI24`, acotado entre 0.50 y 2.00:

| Industria | Vta Costo OI24 | Vta Costo OI25 | Factor | Interpretacion |
|-----------|---------------:|---------------:|-------:|----------------|
| Marroquineria | $49,170,140 | $85,028,274 | 1.729 | Crecimiento fuerte (+73%) |
| Zapateria | $173,621,804 | $284,323,709 | 1.638 | Crecimiento fuerte (+64%) |
| Cosmetica | $19,029,596 | $26,400,295 | 1.387 | Crecimiento moderado (+39%) |
| Indumentaria | $64,386,912 | $84,202,591 | 1.308 | Crecimiento moderado (+31%) |
| Mixto_Zap_Dep | $187,495,782 | $237,838,110 | 1.268 | Crecimiento moderado (+27%) |
| Deportes | $367,459,751 | $415,821,013 | 1.132 | Crecimiento leve (+13%) |
| Ferretero | $4,419,133 | $4,208,724 | 0.952 | Leve retroceso (-5%) |
| **TOTAL** | **$865,583,118** | **$1,137,822,716** | **1.314** | **+31% promedio ponderado** |

---

## 3. Presupuesto OI26 y Disponibilidad

`Presupuesto = Vta_Costo_OI25 x Factor`
`Disponible = Presupuesto - Stock_Costo_Actual`

| Industria | Presupuesto OI26 | Stock Actual | Disponible | Cobertura Stock | Estado |
|-----------|-----------------:|-------------:|-----------:|----------------:|--------|
| Deportes | $470,509,386 | $4,621,661,560 | -$4,151,152,174 | 9.8x | SOBRE-STOCK |
| Zapateria | $465,642,234 | $398,462,094 | $67,180,140 | 0.86x | COMPRAR |
| Mixto_Zap_Dep | $301,586,675 | $215,031,488 | $86,555,187 | 0.71x | COMPRAR |
| Marroquineria | $147,013,882 | $125,250,505 | $21,763,377 | 0.85x | COMPRAR (poco) |
| Indumentaria | $110,137,029 | $61,042,478 | $49,094,551 | 0.55x | COMPRAR |
| Cosmetica | $36,621,209 | $49,296,960 | -$12,675,751 | 1.35x | SOBRE-STOCK |
| Ferretero | $4,006,705 | $5,254,738 | -$1,248,033 | 1.31x | SOBRE-STOCK |
| **TOTAL** | **$1,535,517,120** | **$5,475,999,823** | — | — | — |

### Resumen de disponibilidad neta (solo industrias con espacio):

| Industria | Disponible | % del presupuesto |
|-----------|------------|-------------------|
| Mixto_Zap_Dep | $86,555,187 | 28.7% |
| Zapateria | $67,180,140 | 14.4% |
| Indumentaria | $49,094,551 | 44.6% |
| Marroquineria | $21,763,377 | 14.8% |
| **Total disponible** | **$224,593,255** | — |

---

## 4. Analisis de Margen por Industria (OI25)

| Industria | Margen % | Uds OI25 | Ticket Neto Prom |
|-----------|:--------:|:--------:|-----------------:|
| Ferretero | 57.0% | 302 | $32,441 |
| Deportes | 52.0% | 15,444 | $56,147 |
| Marroquineria | 50.4% | 9,566 | $17,916 |
| Zapateria | 50.3% | 12,996 | $44,011 |
| Indumentaria | 48.4% | 4,913 | $33,204 |
| Mixto_Zap_Dep | 48.3% | 8,896 | $51,704 |
| Cosmetica | 48.1% | 16,719 | $3,045 |

---

## 5. Curva de Capital de Trabajo Mensual (estimada)

Distribucion del presupuesto disponible ($224.6M) segun estacionalidad tipica OI:

```
Mes        Peso%   Necesidad     Acumulado
---------- -----   ----------    ----------
Abril       30%    $67,377,977   $67,377,977
Mayo        25%    $56,148,314   $123,526,290
Junio       20%    $44,918,651   $168,444,941
Julio       15%    $33,688,988   $202,133,930
Agosto      10%    $22,459,326   $224,593,255

Capital de Trabajo Acumulado ($M)
$225 |                                              ****
     |                                         ****
$200 |                                    ****
     |                               ****
$175 |                          ****
     |                     ****
$150 |                ****
     |           ****
$125 |      ****
     | ****
$100 |
     |
 $75 |
     |****
 $50 |
     |
 $25 |
     +----+----+----+----+----+----+----+----+----+--
          Abr       May       Jun       Jul       Ago
```

**Mes pico de necesidad de caja: ABRIL** (concentra el 30% de las compras por inicio de temporada).

---

## 6. Anomalia Deportes: Stock $4,621M vs Presupuesto $470M

El stock de Deportes a costo ($4,621M) es 9.8 veces el presupuesto anual de la industria. Esto requiere investigacion:

- **Hipotesis 1 - Costos inflados en articulos de marca**: Si hay articulos con costo unitario desproporcionado (ej: importados con tipo de cambio alto), el stock valorizado se infla sin que las unidades (15,198) sean excesivas.
- **Hipotesis 2 - Stock viejo sin rotacion**: Articulos descontinuados que nunca se dieron de baja.
- **Hipotesis 3 - Error de datos**: Costos mal cargados o duplicados.

**Accion recomendada:** Auditar los TOP 20 articulos de Deportes por stock_costo, verificar que el costo unitario sea coherente con el precio de venta y la marca.

---

## 7. Recomendaciones

1. **Priorizar compras en Zapateria e Indumentaria**: Son las industrias con mejor relacion disponible/margen. Zapateria crece 64% interanual y tiene 50.3% de margen.

2. **Mixto_Zap_Dep tiene el mayor monto disponible** ($86.6M): Pero es la industria con menor margen (48.3%). Evaluar si el mix de productos justifica la inversion.

3. **Marroquineria: comprar con cautela** ($21.8M disponibles): El crecimiento es fuerte (+73%) pero el ticket es bajo ($17,916). Verificar que no sea inflacion de unidades con caida de ticket (patron similar al diagnosticado en Cosmetica e Indumentaria en t_presupuesto_industria).

4. **Cosmetica y Ferretero: NO comprar** hasta liquidar stock existente. Ambas tienen cobertura superior a 1x.

5. **Deportes: FRENAR compras y auditar stock**. Con 9.8x de cobertura, no se justifica ninguna compra nueva hasta entender la composicion del stock.

6. **Concentrar la caja en abril-mayo** (55% del presupuesto): Los proveedores clave deben tener las ordenes colocadas antes de fin de abril para asegurar entrega en temporada.

---

## 8. Tablas de Soporte en Produccion

| Tabla | Ultima actualizacion | Datos |
|-------|---------------------|-------|
| t_presupuesto_industria | 5-mar-2026 | Presupuesto OI/PV 2026 con factores |
| t_tendencia_facturacion | vigente | Ratios 26 vs 25 por mes |
| t_capital_trabajo_mensual | vigente | Distribucion mensual por industria |
| t_periodos_industria | vigente | OI mar-ago, PV sep-feb, H1/H2 |
| vel_real_articulo | 31-mar-2026 | Velocidad real con quiebre |

---

*Generado el 1 de abril de 2026. Datos basados en ventas reales OI24/OI25 y stock al cierre de marzo 2026.*
