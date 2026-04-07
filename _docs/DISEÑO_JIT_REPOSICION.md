# DISEÑO TÉCNICO: Sistema JIT de Reposición
## Caso Piloto: MASKOTA SRL (prov 220) — Pantuflas Personaje (subrubro 60)
> Versión: 1.0 — 31 de marzo de 2026

---

## Resumen Ejecutivo

Con un lead time de **15 días**, MASKOTA permite implementar un modelo JIT real: en lugar de comprar los 162 pares de invierno 2026 en un solo pedido en abril ($2.96M), se puede arrancar con ~65 pares (~$1.18M) y reordenar cada 2 semanas según el ritmo real de ventas. El capital inmovilizado se reduce en un 55-60% durante los primeros 30 días de temporada.

---

## 1. Modelo de Decisión (Fórmulas Exactas)

### 1.1 Velocidad de Venta Ajustada

```
vel_diaria_base = vel_real_mensual / 30

vel_diaria_ajustada = vel_diaria_base × factor_estacional(mes_actual)
```

Donde `vel_real_mensual` es la velocidad calculada por el algoritmo v3 (excluyendo meses con quiebre de stock).

El factor estacional para pantuflas (subrubro 60) se construye a partir de los datos históricos de ventas por mes. La distribución del invierno 2025 arroja:

| Mes | Ventas 2025 | % del total | Factor est. |
|-----|-------------|-------------|-------------|
| Abr | 3 | 2.5% | 0.30 |
| May | 18 | 14.9% | 1.79 |
| Jun | 38 | 31.4% | 3.77 |
| Jul | 32 | 26.4% | 3.17 |
| Ago | 22 | 18.2% | 2.18 |
| Sep | 8 | 6.6% | 0.79 |

*(Base: 121 pares, factor normalizado sobre vel promedio mensual de 10.1 pares/mes durante la temporada)*

La ESTACIONALIDAD_MENSUAL global (0.73 para abril, 0.93 para mayo, 1.05 para junio) aplica a la cartera general. Para pantuflas los factores son más pronunciados y se deben calcular con `factor_estacional_subrubro(60)`.

### 1.2 Días de Stock Disponible

```
dias_stock = stock_actual / vel_diaria_ajustada
```

Interpretación: si `dias_stock <= lead_time + safety_days` → disparar pedido.

### 1.3 Safety Stock (fórmula existente en app_reposicion.py)

```python
# Función calcular_safety_stock() — línea 579 de app_reposicion.py
lt_meses = lead_time_dias / 30.0           # 15/30 = 0.5
safety = z * std_mensual * sqrt(lt_meses)  # z=1.645 para 95%
```

Con datos de pantuflas personaje (std estimada de ±8 pares/mes en pico):
```
safety_stock = 1.645 × 8 × sqrt(0.5) = 1.645 × 8 × 0.707 ≈ 9 pares
```

### 1.4 Punto de Reorden

```
punto_reorden = vel_diaria_ajustada × lead_time_dias + safety_stock

Ejemplo en junio (pico):
  vel_diaria_junio = (38/30) × 3.77 ≈ 4.8 pares/día  [ajustado]
  — Nota: vel_diaria_base en pico = ~1.35 p/día; el factor amplifica para el mes pico

  vel_diaria_base = 121 pares / (153 días may-sep) ≈ 0.79 p/día promedio temporada
  vel_diaria_junio = 0.79 × (38/20.1) ≈ 1.49 p/día  [usando distribución real]

  punto_reorden_junio = 1.49 × 15 + 9 = 22 + 9 = 31 pares
  punto_reorden_mayo  = 0.59 × 15 + 9 = 9  + 9 = 18 pares
  punto_reorden_julio = 1.06 × 15 + 9 = 16 + 9 = 25 pares
```

### 1.5 Cantidad de Reposición

```
cantidad_pedido = MAX(0, CEIL(vel_diaria_ajustada × horizonte - stock_actual + safety_stock))

horizonte = 30 días (1 mes de cobertura por pedido en temporada activa)
           = 45 días (en pre-temporada o post-temporada)
```

Variante simplificada para UI:
```
cantidad_pedido = MAX(0, stock_objetivo - stock_actual)
stock_objetivo  = vel_diaria_ajustada × horizonte + safety_stock
```

### 1.6 Semáforo de Urgencia

| Condición | Color | Acción |
|-----------|-------|--------|
| `stock_actual <= safety_stock` | ROJO | Pedir HOY — riesgo de stockout antes de recibir |
| `stock_actual <= punto_reorden` | AMARILLO | Pedir esta semana — queda ~15 días de stock |
| `stock_actual > punto_reorden` | VERDE | OK — no reponer |

Fórmula de días hasta stockout para alertas:
```
dias_hasta_cero = stock_actual / vel_diaria_ajustada
ROJO    si dias_hasta_cero <= lead_time + 2
AMARILLO si dias_hasta_cero <= lead_time + 7
VERDE   en otro caso
```

---

## 2. Caso Maskotas — Simulación Invierno 2026

### 2.1 Parámetros Base

| Parámetro | Valor | Fuente |
|-----------|-------|--------|
| Lead time MASKOTA | 15 días | Contrato proveedor |
| Pedido total armado | 162 pares | Análisis OI26 |
| Valor total pedido | $2,960,000 | Precio costo |
| Precio costo promedio | $18,272/par | $2.96M / 162p |
| Ventas invierno 2025 | 121 pares | Histórico ERP |
| Ventas invierno 2024 | 188 pares (98% agotado) | Histórico ERP |
| Proyección 2026 | 162 pares | Promedio ajustado |
| Safety stock (95%) | 9 pares | Fórmula Poisson |

### 2.2 Stock Inicial Recomendado para Abril

**Estrategia JIT**: comprar lo que se va a vender en 30-35 días + safety stock.

Abril es mes de arranque lento (factor 0.30 del total):
```
Ventas proyectadas abril = 162 × 2.5% ≈ 4 pares
Ventas proyectadas mayo  = 162 × 14.9% ≈ 24 pares

Stock inicial abril = ventas_abril + ventas_mayo + safety_stock
                    = 4 + 24 + 9 = 37 pares mínimo

Con buffer de timing (pedido llega con 15 días de espera):
Stock inicial recomendado = 60-65 pares
Capital necesario en abril = 62 × $18,272 = $1,133,000 (vs $2,960,000 compra total)
AHORRO inicial = $1,827,000 (62% del capital)
```

### 2.3 Simulación Semana a Semana (Invierno 2026)

Supuestos: inicio temporada 1° de mayo. Primer pedido pasa en la primera semana de abril (stock llega ~15 de abril, 2 semanas antes de inicio).

| Semana | Período | Ventas est. | Stock inicio | Stock fin | Punto reorden | ¿Reponer? | Cantidad |
|--------|---------|-------------|-------------|-----------|---------------|-----------|----------|
| S0 (abr w1) | 1-7 abr | 1 | 62 | 61 | 18 | No | 0 |
| S1 (abr w2) | 8-14 abr | 1 | 61 | 60 | 18 | No | 0 |
| S2 (abr w3) | 15-21 abr | 2 | 60 | 58 | 18 | No | 0 |
| S3 (abr w4) | 22-30 abr | 1 | 58 | 57 | 18 | No | 0 |
| **S4 (may w1)** | **1-7 may** | **4** | **57** | **53** | **18** | **Pedir** | **30** |
| S5 (may w2) | 8-14 may | 5 | 53 | 48 | 18 | No | 0 |
| S6 (may w3) **[llega S4]** | 15-21 may | 6 | 78 | 72 | 22 | No | 0 |
| S7 (may w4) | 22-31 may | 7 | 72 | 65 | 22 | No | 0 |
| **S8 (jun w1)** | **1-7 jun** | **8** | **65** | **57** | **31** | **Pedir** | **35** |
| S9 (jun w2) | 8-14 jun | 9 | 57 | 48 | 31 | No | 0 |
| S10 (jun w3) **[llega S8]** | 15-21 jun | 10 | 83 | 73 | 31 | No | 0 |
| S11 (jun w4) | 22-30 jun | 9 | 73 | 64 | 28 | No | 0 |
| **S12 (jul w1)** | **1-7 jul** | **8** | **64** | **56** | **25** | **Pedir** | **25** |
| S13 (jul w2) | 8-14 jul | 8 | 56 | 48 | 25 | No | 0 |
| S14 (jul w3) **[llega S12]** | 15-21 jul | 7 | 73 | 66 | 20 | No | 0 |
| S15 (jul w4) | 22-31 jul | 7 | 66 | 59 | 20 | No | 0 |
| **S16 (ago w1)** | **1-7 ago** | **5** | **59** | **54** | **18** | **Pedir** | **12** |
| S17 (ago w2) | 8-14 ago | 5 | 54 | 49 | 18 | No | 0 |
| S18 (ago w3) **[llega S16]** | 15-21 ago | 5 | 61 | 56 | 15 | No | 0 |
| S19 (ago w4) | 22-31 ago | 6 | 56 | 50 | 15 | No | 0 |
| S20 (sep w1) | 1-7 sep | 3 | 50 | 47 | 10 | No | 0 |
| S21 (sep+) | resto | 5 | 47 | 42 | — | No reponer | — |

**Total reposiciones: 4 pedidos** (S4, S8, S12, S16) + stock inicial (S0)
**Total pares pedidos: 62 + 30 + 35 + 25 + 12 = 164 pares** ≈ pedido total

### 2.4 Comparación Capital Inmovilizado

| Escenario | Capital abril | Capital máximo | Rotación |
|-----------|--------------|----------------|---------|
| Compra masiva (todo en abril) | $2,960,000 | $2,960,000 | 1× temporada |
| **JIT con 4 reposiciones** | **$1,133,000** | **$1,515,000** | **4× temporada** |
| **Ahorro vs compra masiva** | **$1,827,000 (62%)** | **$1,445,000 (49%)** | |

---

## 3. Umbrales de Alerta por Modelo

Distribución del pedido 2026 (162 pares totales, ajustada por mix 2025):

| Modelo | Pares pedido | % mix | Vel/día (pico jun) | Punto reorden | Stock inicial JIT | 1a Reposición estimada |
|--------|-------------|-------|-------------------|---------------|------------------|----------------------|
| 310 Beige | 42 | 25.9% | 0.39 p/día | 15 pares | 16 pares | 15 de junio |
| Milfi | 33 | 20.4% | 0.31 p/día | 14 pares | 13 pares | 20 de junio |
| Capybara | 27 | 16.7% | 0.25 p/día | 13 pares | 11 pares | 25 de junio |
| Mundial | 21 | 13.0% | 0.19 p/día | 12 pares | 9 pares | 1 de julio |
| Stitch/Ohana | 21 | 13.0% | 0.19 p/día | 12 pares | 9 pares | 1 de julio |
| Otros modelos | 18 | 11.1% | 0.17 p/día | 11 pares | 9 pares | 5 de julio |
| **TOTAL** | **162** | 100% | | | **~67 pares** | |

**Notas de cálculo:**
- Vel/día pico = (pares_modelo / 162) × 1.49 p/día total en pico junio
- Punto reorden = vel_dia × 15 días lead time + safety_stock (2-3 pares por modelo)
- Stock inicial JIT = vel_dia × 30 días + safety_stock (cobertura 1 mes)
- Fechas estimadas asumen inicio de ventas el 1° de mayo con curva real 2025

**Modelos críticos (mayor riesgo de stockout):**
- **310 Beige**: top ventas, reposición más frecuente. Monitorear semanalmente.
- **Milfi**: segundo en volumen, alta probabilidad de quiebre si se retrasa pedido.
- **Capybara**: emparejado con Milfi en pico. Si el proveedor tiene demoras, afecta los 3 top juntos.

---

## 4. Roadmap de Implementación (3 Sprints)

### Sprint 1 — Esta semana (1-7 abril 2026)
**Objetivo: Motor JIT funcionando para Maskotas**

| Tarea | Archivo | Detalles técnicos |
|-------|---------|-------------------|
| Agregar `lead_times` por proveedor a config.py | `config.py` | Dict `LEAD_TIMES = {220: 15, 668: 45, 104: 21, ...}` |
| Función `calcular_decision_jit()` en app_reposicion.py | `app_reposicion.py` | Usa `calcular_safety_stock()` existente + nuevas fórmulas |
| Nuevo tab "Monitor JIT" (tab 11 o dentro de Armar Pedido) | `app_reposicion.py` | Tabla por modelo con semáforo ROJO/AMARILLO/VERDE |
| Filtrar por proveedor: selector "MASKOTA SRL (prov 220)" | Tab Monitor JIT | Piloto: solo prov 220 |
| Query stock actual por modelo desde msgestionC.dbo.stock | Tab Monitor JIT | JOIN con articulo por subrubro=60 y prov=220 |
| Cálculo vel_real desde vel_real_articulo (omicronvt) | Tab Monitor JIT | 46,794 filas disponibles en producción |

**Función `calcular_decision_jit()` — firma propuesta:**
```python
def calcular_decision_jit(
    stock_actual: int,
    vel_mensual: float,          # pares/mes desde vel_real_articulo
    std_mensual: float,          # desvío estándar
    lead_time_dias: int = 15,
    horizonte_dias: int = 30,
    service_level: float = 0.95,
    factor_estacional: float = 1.0,
) -> dict:
    """
    Returns:
      {
        vel_diaria_ajustada: float,
        dias_stock: float,
        safety_stock: int,
        punto_reorden: int,
        cantidad_pedido: int,
        urgencia: str,           # 'ROJO' | 'AMARILLO' | 'VERDE'
        dias_hasta_stockout: float,
        stock_objetivo: int,
      }
    """
```

**Estructura tab Monitor JIT — columnas:**
```
Modelo | Stock | Vel/día | Días stock | P.Reorden | Safety | Pedido sugerido | Urgencia
```

### Sprint 2 — Semana del 8-14 abril 2026
**Objetivo: Ciclo completo pedido → INSERT → tracking**

| Tarea | Archivo | Detalles técnicos |
|-------|---------|-------------------|
| Botón "Confirmar Pedido" en Monitor JIT | Tab Monitor JIT | Reutiliza lógica de tab "Armar Pedido" existente |
| INSERT automático via paso4_insertar_pedido.py | `paso4_insertar_pedido.py` | Empresa: CALZALINDO (msgestion01), prov 220 |
| Tabla `jit_ordenes_log` en omicronvt | Nueva tabla SQL | Columnas: fecha, proveedor, modelo, cantidad, estado, fecha_recepcion_real |
| Tracking lead time real vs prometido | App + tabla log | Para calcular KPI cumplimiento lead time |
| Notificación WhatsApp al disparar ROJO | `valijas/responder_agencias.py` o API directa | WhatsApp Fernando (+5493462672330) |

**SQL crear tabla log:**
```sql
CREATE TABLE omicronvt.dbo.jit_ordenes_log (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    fecha_pedido DATE NOT NULL,
    proveedor    INT NOT NULL,
    csr          VARCHAR(12),
    descripcion  VARCHAR(80),
    cantidad     INT NOT NULL,
    urgencia     VARCHAR(10),  -- ROJO/AMARILLO/VERDE
    pedico_numero INT,          -- numero en pedico2
    fecha_recepcion DATE,       -- completar al recibir
    lead_time_real INT,         -- DATEDIFF(day, fecha_pedido, fecha_recepcion)
    created_at   DATETIME DEFAULT GETDATE()
)
```

**Notificación WhatsApp — trigger:**
- Condición: cualquier modelo con urgencia = 'ROJO'
- Mensaje: "ALERTA STOCK: [Modelo] tiene solo [N] días de stock (punto de reorden: [P]). Pedir [Q] pares a MASKOTA."
- Canal: Chatwoot (ya configurado en valijas) o webhook directo

### Sprint 3 — Semana del 15-21 abril 2026
**Objetivo: Extensión a todos los proveedores + dashboard ejecutivo**

| Tarea | Archivo | Detalles técnicos |
|-------|---------|-------------------|
| Lead times para los 6 proveedores en config.py | `config.py` | Alpargatas 45d, GTN 21d, VICBOR 30d, Distrinando 30d, Ringo 21d, Calzados Blanco 30d |
| Selector de proveedor en Monitor JIT (no solo Maskotas) | Tab Monitor JIT | Dropdown proveedor, filtra tabla automáticamente |
| Dashboard KPIs (fill rate, rotación, GMROI) | Nueva sección | Métricas globales + por proveedor |
| Backtesting 2025 | Script oneshot | Simular JIT sobre ventas reales 2025, calcular ahorro vs compra masiva |
| Sync vel_real: actualizar copias #2/#3/#4 al algoritmo v3 | `_docs/AUDIT_VEL_REAL_20260325.md` | 7 gaps documentados pendientes |

**Parámetros lead time por proveedor (estimados):**
```python
# En config.py
LEAD_TIMES = {
    220: 15,   # MASKOTA SRL — pantuflas personaje (confirmado)
    104: 21,   # GTN "EL GITANO" — estimado
    668: 45,   # ALPARGATAS — lead time largo (importación)
    594: 30,   # VICBOR SRL — Atomik/Wake/Massimo
    656: 30,   # DISTRINANDO — Reebok
    561: 21,   # SOUTER (RINGO) — estimado
    614: 30,   # CALZADOS BLANCO (Diadora) — estimado
}
```

---

## 5. KPIs del Sistema JIT

### 5.1 Definiciones

| KPI | Fórmula | Objetivo | Medición |
|-----|---------|----------|---------|
| **Fill Rate** | (pares vendidos sin quiebre) / (pares demandados) | ≥ 95% | Semanal por modelo |
| **Capital inmovilizado promedio** | AVG(stock_pares × precio_costo) por semana | Reducir 50% vs 2025 | Mensual |
| **Rotación** | pares_vendidos_12m / stock_promedio_12m | ≥ 8× en temporada | Mensual |
| **Cumplimiento lead time** | pedidos_en_plazo / pedidos_totales × 100% | ≥ 85% | Por pedido |
| **Pedidos de emergencia** | pedidos con urgencia=ROJO / total pedidos | ≤ 10% | Mensual |
| **Stockout rate** | modelos_sin_stock × días / (modelos_total × días_temporada) | ≤ 5% | Por temporada |

### 5.2 Valores de Referencia (Maskotas)

| Métrica | Invierno 2024 | Invierno 2025 | Objetivo 2026 JIT |
|---------|--------------|--------------|-------------------|
| Pares vendidos | 188 (98% agotado) | 121 (quiebre crónico) | 155-165 (fill rate ≥ 95%) |
| Capital max inmovilizado | Desconocido | ~$2.2M (total) | $1.5M máximo |
| Reposiciones | 3 (manuales/reactivas) | 0-1 (sin sistema) | 4 planificadas |
| Semanas con stockout | ~4 semanas | ~6 semanas | ≤ 1 semana |
| Días a fin de stock | Ago (agotado) | Jul (quiebre) | Sep (fin natural) |

### 5.3 Backtesting Estimado (2025 con JIT)

Si en 2025 se hubiera usado JIT con 15 días de lead time:
- Stock inicial 1° mayo: ~50 pares (~$913K vs $2.2M)
- Reposición 1 (semana 3 mayo): +25 pares
- Reposición 2 (semana 1 junio): +30 pares
- Reposición 3 (semana 2 julio): +20 pares
- **Proyección ventas: 121 + ~15-20 pares recuperados de quiebres = ~140 pares**
- **Aumento de ventas estimado: +15% solo por eliminar quiebres**
- **Reducción capital máximo: ~35%**

El script de backtesting (`_scripts_oneshot/backtesting_jit_maskotas.py`) tomará las ventas reales de 2025 semana a semana y simulará el algoritmo de decisión para cuantificar el resultado exacto.

---

## 6. Arquitectura del Módulo JIT en app_reposicion.py

### 6.1 Flujo de datos

```
vel_real_articulo (omicronvt, 46,794 filas)
    ↓ vel_mensual, std_mensual por CSR
factor_estacional_subrubro(60)
    ↓ factor por mes actual
calcular_decision_jit()
    ↓ {urgencia, cantidad_pedido, punto_reorden, ...}
Tab "Monitor JIT" (Streamlit)
    ↓ tabla con semáforo por modelo
Botón "Confirmar Pedido"
    ↓ paso4_insertar_pedido.py
INSERT pedico2 + pedico1 (msgestion01)
    ↓ log en jit_ordenes_log (omicronvt)
WhatsApp alert (si ROJO)
```

### 6.2 Query base para Monitor JIT

```sql
SELECT
    LEFT(a.codigo_sinonimo, 10) AS csr,
    RTRIM(a.descripcion_1) AS descripcion,
    SUM(ISNULL(s.stock_actual, 0)) AS stock_total,
    vr.vel_real_mensual,
    vr.std_mensual
FROM msgestion01art.dbo.articulo a
LEFT JOIN msgestionC.dbo.stock s ON s.articulo = a.codigo
LEFT JOIN omicronvt.dbo.vel_real_articulo vr
    ON vr.csr = LEFT(a.codigo_sinonimo, 10)
WHERE a.subrubro = 60          -- PANTUFLA
  AND a.proveedor = 220        -- MASKOTA SRL
  AND a.estado = 'V'
GROUP BY LEFT(a.codigo_sinonimo, 10), RTRIM(a.descripcion_1),
         vr.vel_real_mensual, vr.std_mensual
ORDER BY stock_total ASC       -- primero los más críticos
```

### 6.3 Integración con infraestructura existente

| Componente existente | Uso en JIT |
|---------------------|-----------|
| `calcular_safety_stock()` (línea 579) | Base del cálculo JIT — reutilizar directamente |
| `factor_estacional_subrubro(60)` (línea 816) | Factor estacional para vel ajustada |
| `SUBRUBRO_TEMPORADA[60]` (línea 191) | Ventana de venta/compra pantuflas |
| `clasificar_abc_xyz()` (línea 614) | Priorizar alertas en modelos A |
| Tab "Armar Pedido" | Reutilizar lógica INSERT para confirmar pedido JIT |
| `vel_real_articulo` (omicronvt) | Velocidad real ya disponible en producción |
| WhatsApp Fernando (CLAUDE.md) | Destino alertas ROJO |

---

## 7. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| MASKOTA se queda sin stock del modelo demandado | Media | Alto | Diversificar modelos en pedido inicial; pedir confirmación de disponibilidad al hacer reposición |
| Lead time real > 15 días (demoras) | Media | Medio | Usar lead time conservador de 18-20 días en cálculo; monitorear cumplimiento en jit_ordenes_log |
| Explosión de demanda inesperada (viralización) | Baja | Alto | Safety stock de 9 pares absorbe pico 1 semana; alerta ROJO se dispara antes |
| Proveedor cambia condiciones de pedido mínimo | Baja | Bajo | Adaptar horizonte: si pide mínimo 24 pares, ajustar cantidad_pedido mínima |
| Datos vel_real desactualizados | Alta | Medio | Ejecutar update vel_real_articulo antes de temporada (abril) |

---

## 8. Próximos Pasos Inmediatos

1. **Hoy**: Verificar lead time MASKOTA con Fernando (¿15 días es real o estimado?).
2. **Hoy**: Correr `SELECT * FROM omicronvt.dbo.vel_real_articulo WHERE csr LIKE 'MSK%' OR csr IN (...)` para confirmar que hay datos de Maskotas en la tabla.
3. **Esta semana**: Implementar Sprint 1 (función `calcular_decision_jit()` + tab Monitor JIT).
4. **Antes del 10 de abril**: Definir stock inicial exacto y generar script de primer pedido Maskotas.
5. **15 de abril**: Tener el sistema en producción antes del inicio de temporada.

---

*Documento generado el 31-03-2026. Actualizar con datos reales de vel_real al inicio de temporada.*
