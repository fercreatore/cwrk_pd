# PROMPT: Reposición Inteligente v3 — 10 Agentes Paralelos

## CONTEXTO GLOBAL (para TODOS los agentes)

Archivo principal: `app_reposicion.py` (Streamlit, ~1900 líneas).
Base de datos: SQL Server 2012 vía pyodbc (conexión en `config.py`).
PostgreSQL: `postgresql://guille:Martes13%23@200.58.109.125:5432/clz_productos` (embeddings).

### Conexión SQL Server
```python
from config import CONN_COMPRAS, CONN_ARTICULOS, get_conn_string
# O directamente:
# pyodbc.connect("DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.2.111;DATABASE=msgestionC;UID=am;PWD=dl;TrustServerCertificate=yes")
```

### Tablas clave
- `msgestion01art.dbo.articulo` — PK=`codigo`, campos: `rubro`, `subrubro`, `proveedor`, `marca`, `precio_fabrica`, `descripcion_1..5`, `estado`
- `msgestionC.dbo.stock` — `articulo`, `deposito`, `stock_actual`
- `msgestionC.dbo.ventas1` — `articulo`, `cantidad`, `fecha`, `codigo` (EXCLUIR codigo IN (7,36))
- `msgestionC.dbo.compras1` / `compras2` — compras, `fecha_comprobante`, campo proveedor en compras2 NO es `auxiliar`
- `msgestion01.dbo.subrubro` — lookup `codigo` → `descripcion`
- `msgestion01art.dbo.marcas` — `codigo` → `descripcion`
- `msgestion01.dbo.equivalencias_talles_calzado` — mapeo talles
- `msgestion01.dbo.regla_talle_subrubro` — tipo talle por subrubro
- `msgestion01.dbo.aliases_talles` — alias → talle resuelto

### Constantes estándar
```python
DEPOS_SQL = '(0,1,2,3,4,5,6,7,8,9,11,12,14,15,198)'
EXCL_VENTAS = '(7,36)'  # remitos internos
RUBRO_GENERO = {1: 'DAMAS', 3: 'HOMBRES', 4: 'NIÑOS', 5: 'NIÑAS', 6: 'UNISEX'}
MESES_HISTORIA = 12
```

### Regla obligatoria: Quiebre de stock
SIEMPRE reconstruir stock mes a mes hacia atrás. Meses con stock_inicio <= 0 = QUEBRADO.
Velocidad REAL = ventas de meses NO quebrados / cantidad de meses NO quebrados.

### SQL Server 2012: NO soporta TRY_CAST. Usar ISNUMERIC() + CAST().

---

## AGENTE 1: presupuesto_pares()

**Objetivo**: Función que calcula el presupuesto en PARES para un proveedor dado un período destino.

```python
@st.cache_data(ttl=3600)
def presupuesto_pares(proveedor_num: int, mes_inicio: int, mes_fin: int) -> dict:
    """
    Presupuesto = pares vendidos del mismo proveedor en el mismo período del año anterior.

    Args:
        proveedor_num: número de proveedor en msgestion01.dbo.proveedores
        mes_inicio: mes inicio período destino (ej: 3 = marzo)
        mes_fin: mes fin período destino (ej: 6 = junio)

    Returns:
        {
            'total_pares': int,
            'por_mes': {3: 165, 4: 92, 5: 114, 6: 104},
            'articulos_distintos': int,
            'periodo_ref': '2025-03 a 2025-06'
        }
    """
```

**Query base**:
```sql
SELECT MONTH(v.fecha) as mes, SUM(v.cantidad) as pares, COUNT(DISTINCT v.articulo) as arts
FROM msgestionC.dbo.ventas1 v
JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
WHERE v.codigo NOT IN (7,36)
  AND a.proveedor = @proveedor
  AND v.fecha >= @fecha_inicio AND v.fecha < @fecha_fin
GROUP BY MONTH(v.fecha)
```

**Ubicar**: después de las funciones de quiebre existentes (~línea 750).
**Usar**: `query_df()` que ya existe en el archivo.

---

## AGENTE 2: distribucion_genero()

**Objetivo**: Peso porcentual de ventas por género para un proveedor.

```python
@st.cache_data(ttl=3600)
def distribucion_genero(proveedor_num: int, mes_inicio: int, mes_fin: int) -> dict:
    """
    Returns:
        {
            1: {'nombre': 'DAMAS', 'pares': 209, 'pct': 0.44},
            3: {'nombre': 'HOMBRES', 'pares': 256, 'pct': 0.54},
            4: {'nombre': 'NIÑOS', 'pares': 10, 'pct': 0.02}
        }
    """
```

**Query**: Similar al agente 1, agregar `GROUP BY a.rubro`.
**Mapear**: rubro → nombre con `RUBRO_GENERO`.

---

## AGENTE 3: distribucion_color()

**Objetivo**: Peso porcentual de ventas por color para un proveedor × género.

```python
@st.cache_data(ttl=3600)
def distribucion_color(proveedor_num: int, rubro: int, mes_inicio: int, mes_fin: int) -> list[dict]:
    """
    Clasifica colores desde descripcion_1 del artículo.

    Returns: [
        {'color': 'NEGRO', 'pares': 144, 'pct': 0.56},
        {'color': 'AZUL', 'pares': 54, 'pct': 0.21},
        ...
    ]
    """
```

**Mapeo de colores** (CASE en SQL o post-proceso en Python):
```python
COLOR_KEYWORDS = {
    'NEGRO': ['NEGRO', 'BLACK', 'PRETO', 'CHUMBO'],
    'GRIS': ['GRIS', 'GREY', 'PLOMO', 'STEEL', 'CINZA'],
    'AZUL': ['AZUL', 'BLUE', 'MARINO', 'MARINHO', 'PETROLEO'],
    'BLANCO': ['BLANCO', 'WHITE', 'BRANCO'],
    'ROSA': ['ROSA', 'PINK', 'FUCSIA'],
    'BEIGE': ['BEIGE', 'ARENA', 'ARENITO', 'ALGODAO', 'MARFIL'],
    'ROJO': ['ROJO', 'RED', 'BORDO', 'VERMELHO'],
    'VERDE': ['VERDE', 'GREEN'],
}
```

Si no matchea ninguno → 'OTRO'. Hacer en Python, no en SQL (más mantenible).

---

## AGENTE 4: precio_techo()

**Objetivo**: Precio máximo razonable para pedir de un proveedor, basado en lo que realmente se vende.

```python
@st.cache_data(ttl=3600)
def precio_techo(proveedor_num: int, rubro: int, percentil: int = 90) -> dict:
    """
    Calcula el percentil del precio_fabrica de artículos VENDIDOS (no de catálogo).

    Returns:
        {
            'p50': 40540.0,
            'p75': 43243.0,
            'p90': 48648.0,   # <- este es el techo default
            'max': 108000.0,
            'articulos_analizados': 156
        }
    """
```

**Query**: JOIN ventas1 con articulo WHERE proveedor = X, traer precio_fabrica de los vendidos. Calcular percentiles con `np.percentile()` en Python.

**Importante**: Usar solo artículos que tuvieron al menos 1 venta en los últimos 12 meses. No incluir artículos muertos del catálogo.

---

## AGENTE 5: curva_talles_real()

**Objetivo**: Curva de demanda real por talle individual para un proveedor × género.

```python
@st.cache_data(ttl=3600)
def curva_talles_real(proveedor_num: int, rubro: int, meses: int = 12) -> dict:
    """
    Returns:
        {
            'curva': {
                '37': {'pares': 57, 'pct': 0.12},
                '38': {'pares': 69, 'pct': 0.15},
                '39': {'pares': 55, 'pct': 0.12},
                '40': {'pares': 61, 'pct': 0.13},
                '41': {'pares': 63, 'pct': 0.13},
                '42': {'pares': 58, 'pct': 0.12},
                '43': {'pares': 45, 'pct': 0.09},
                '44': {'pares': 16, 'pct': 0.03},
                '45': {'pares': 20, 'pct': 0.04},
                '46': {'pares': 1, 'pct': 0.00},
                '47': {'pares': 1, 'pct': 0.00},
                '48': {'pares': 2, 'pct': 0.00},
            },
            'total_pares': 475,
            'talle_pico': '38'
        }
    """
```

**Talle**: Viene en `descripcion_5` del artículo. Limpiar con RTRIM, filtrar vacíos.
**Corregir por quiebre**: Si un talle tuvo stock 0 durante meses, su velocidad aparente subestima la demanda. Aplicar la misma lógica de quiebre pero a nivel talle individual (stock por artículo, donde cada artículo = 1 talle).

---

## AGENTE 6: talles_escasez_cronica()

**Objetivo**: Detectar talles que históricamente siempre están en falta.

```python
@st.cache_data(ttl=3600)
def talles_escasez_cronica(rubro: int, subrubro: int = None, umbral_quiebre: float = 0.7) -> list[dict]:
    """
    Un talle tiene escasez crónica si estuvo quebrado > 70% de los meses analizados.

    Returns: [
        {'talle': '46', 'meses_quebrado': 11, 'meses_total': 12, 'pct_quiebre': 0.92},
        {'talle': '47', 'meses_quebrado': 10, 'meses_total': 12, 'pct_quiebre': 0.83},
        {'talle': '48', 'meses_quebrado': 12, 'meses_total': 12, 'pct_quiebre': 1.00},
    ]
    """
```

**Lógica**:
1. Para cada talle (desc_5) en el rubro, agrupar artículos
2. Reconstruir stock mes a mes (misma lógica de quiebre del sistema)
3. Si el talle tuvo stock <= 0 en > umbral_quiebre % de meses → escasez crónica
4. Estos talles se marcan SIEMPRE como críticos en el mapa de surtido

---

## AGENTE 7: UI Mapa Surtido — Drill-down por talle

**Objetivo**: Agregar nivel 3 al mapa de surtido existente (tab "Mapa Surtido").

**Flujo actual**:
1. Tabla género × categoría con semáforo de cobertura ← YA EXISTE
2. Click en una fila → pirámide de precios ← YA EXISTE
3. **NUEVO**: Debajo de la pirámide → tabla de talles individuales

**UI del nivel 3**:
```
📏 Cobertura por Talle — HOMBRES × ZAPATILLA TRAINING

| Talle | Stock | Vtas 12m | Vel.Real | Cob.Días | Estado        |
|-------|-------|----------|----------|----------|---------------|
| 37    | 45    | 120      | 12.5/m   | 108      | ✅ OK         |
| 38    | 52    | 145      | 14.2/m   | 110      | ✅ OK         |
| 39    | 38    | 130      | 13.0/m   | 88       | 🟡 MEDIO      |
| 40    | 41    | 138      | 13.5/m   | 91       | 🟡 MEDIO      |
| 41    | 35    | 142      | 14.0/m   | 75       | 🟡 MEDIO      |
| 42    | 28    | 125      | 12.8/m   | 66       | 🟠 BAJO       |
| 43    | 15    | 98       | 10.2/m   | 44       | 🔴 CRITICO    |
| 44    | 8     | 45       | 5.5/m    | 44       | 🔴 CRITICO    |
| 45    | 3     | 22       | 3.0/m    | 30       | 🔴 CRITICO    |
| 46    | 0     | 5        | —        | 0        | ⚫ ESCASEZ    |
| 47    | 0     | 2        | —        | 0        | ⚫ ESCASEZ    |
| 48    | 0     | 1        | —        | 0        | ⚫ ESCASEZ    |
```

**Colores semáforo**:
- CRITICO (<30 días): rojo
- BAJO (30-60): naranja
- MEDIO (60-120): amarillo
- OK (>120): verde
- ESCASEZ CRÓNICA: negro (siempre falta, independiente del stock)

**Usar**: funciones de agentes 5 y 6.
**Ubicar**: dentro del tab Mapa Surtido, después del drill-down de pirámide de precios (~línea 1300+).

---

## AGENTE 8: UI Optimizar Compra — Rewrite con presupuesto en pares

**Objetivo**: Reescribir el tab "Optimizar Compra" para que use presupuesto en pares.

**Flujo nuevo**:
```
1. Sidebar inputs:
   - Proveedor (selectbox de proveedores activos)
   - Período destino: mes_inicio, mes_fin (default: mes actual → +3)
   - Condición pago: días (input, default 90)

2. Al seleccionar proveedor:
   - Mostrar presupuesto_pares() → "Presupuesto: 475 pares (basado en mar-jun 2025)"
   - Mostrar distribucion_genero() → torta/barra
   - Mostrar precio_techo() → "Precio techo P90: $48,648"

3. Tabla de asignación:
   - Por género: cuántos pares asignar (editable, default = % histórico)
   - Por color: cuántos pares por color (editable, default = % histórico)
   - Curva de talles: mostrar curva real vs curva proveedor

4. Resultado:
   - Grilla: modelo × color × talle → cantidad sugerida
   - Resumen: pares totales, monto, cuotas según condición de pago
   - Talles con escasez crónica marcados en rojo
```

**Usar**: funciones de agentes 1-6.
**Reemplazar**: la lógica actual del tab que usa presupuesto en $ y ROI por días.

---

## AGENTE 9: Fix CSS métricas + filtro subrubro

**Objetivo**: Arreglar dos bugs del tab Mapa Surtido.

**Bug 1 — Cuadros blancos**: Las métricas `st.metric()` del header tienen texto blanco sobre fondo blanco en dark mode. Fix con CSS:
```python
st.markdown("""
<style>
[data-testid="stMetricValue"] { color: #ffffff !important; }
[data-testid="stMetricLabel"] { color: #cccccc !important; }
[data-testid="stMetricDelta"] { color: #00cc00 !important; }
div[data-testid="stMetric"] {
    background-color: rgba(28, 131, 225, 0.1);
    border-radius: 8px;
    padding: 10px 15px;
}
</style>
""", unsafe_allow_html=True)
```

**Bug 2 — Falta filtro subrubro**: En el tab Mapa Surtido hay filtro de género y urgencia pero NO de categoría/subrubro. Agregar un `st.multiselect("Filtrar categoría", ...)` entre el filtro de género y el de urgencia.

**Bug 3 — NaN en urgencia sort**: Ya parcheado con `.dropna()`, verificar que no queden otros `.unique()` sin dropna.

---

## AGENTE 10: cargar_talles_categoria() — Fix NaN + escasez crónica

**Objetivo**: Arreglar la función `cargar_talles_categoria()` (~línea 955) que crashea con IntCastingNaNError.

**Error**: `(df['stock'] / df['vel_diaria']).astype(int)` explota cuando `vel_diaria = 0` (división por cero → inf).

**Fix**:
```python
cob_raw = df['stock'] / df['vel_diaria'].replace(0, np.nan)
df['cobertura_dias'] = cob_raw.fillna(9999).clip(upper=9999).astype(int)
```

**Agregar**: columna `escasez_cronica` (bool) usando `talles_escasez_cronica()` del agente 6.

**Agregar**: semáforo de estado:
```python
def estado_talle(row):
    if row['escasez_cronica']:
        return 'ESCASEZ'
    if row['cobertura_dias'] < 30:
        return 'CRITICO'
    if row['cobertura_dias'] < 60:
        return 'BAJO'
    if row['cobertura_dias'] < 120:
        return 'MEDIO'
    return 'OK'
```

---

## ORDEN DE INTEGRACIÓN

Los agentes 1-6 son funciones independientes (no tocan UI). Se pueden codear en paralelo.
Los agentes 7-8 dependen de 1-6 (usan las funciones).
Los agentes 9-10 son fixes independientes.

**Sugerencia de merge**:
1. Primero mergear 1-6 (funciones) + 9-10 (fixes)
2. Luego mergear 7-8 (UI) que usan las funciones

---

## VALIDACIÓN

Después de integrar todo, correr:
```bash
cd ~/Desktop/cowork_pedidos
OPENSSL_CONF=~/Desktop/cowork_pedidos/_scripts_oneshot/openssl_legacy.cnf streamlit run app_reposicion.py --server.port 8503
```

Verificar:
- [ ] Mapa Surtido: métricas se ven bien (no blancas)
- [ ] Mapa Surtido: filtro por categoría funciona
- [ ] Mapa Surtido: drill-down a talles individuales funciona
- [ ] Talles 46-48 marcados como ESCASEZ siempre
- [ ] Optimizar Compra: presupuesto muestra pares (no $)
- [ ] Optimizar Compra: distribución por color ponderada
- [ ] Optimizar Compra: precio techo filtra modelos caros
- [ ] No hay crashes por NaN/inf

---

## DATOS MACRO DEL NEGOCIO (contexto para decisiones de reposición)

### Patrón estacional (pares/mes, promedio 2023-2026)
| Mes | Pares | % vs promedio |
|-----|-------|---------------|
| Ene | 10,569 | 88% |
| Feb | 12,476 | 104% |
| Mar | 8,910 | 74% |
| Abr | 8,699 | 73% |
| May | 11,164 | 93% |
| Jun | 12,556 | 105% |
| Jul | 11,783 | 98% |
| Ago | 11,080 | 92% |
| Sep | 11,148 | 93% |
| Oct | 14,599 | 122% |
| Nov | 12,454 | 104% |
| Dic | 18,064 | 151% |

- **Promedio mensual**: ~11,958 pares
- **Total anual**: ~143,500 pares
- **Meses pico**: Dic (151%), Oct (122%)
- **Meses valle**: Mar-Abr (73-74%)

### Stock y cobertura (al 24/03/2026)
- Stock total: 226,076 pares
- Velocidad últimos 90d: 381 pares/día
- Cobertura global: 593 días — **ENGAÑOSA por quiebre a nivel SKU**

### Ciclo de compras (patrón real observado)
- **Sep-Oct**: compra fuerte (abastecimiento temporada dic)
- **Dic-Mar**: compra fuerte (abastecimiento temporada invierno)
- **Abr-Ago**: balance negativo (se vende más de lo que se compra, se consume stock)

### Ratio Compras/Ventas por era de artículos
| Era | Ratio pares | Ratio $ | Venta prom/mes |
|-----|-------------|---------|----------------|
| Anterior (≤2023) | 106% | 73% | 10,574 |
| Transición (2024) | 112% | 83% | 12,277 |
| Nuevo (2025+) | **75%** | 43% | 12,918 |

**HALLAZGO CLAVE**: El modelo nuevo compra 25% menos en pares de lo que vende.
Esto implica que se está drenando stock (o desabasteciendo sin querer).
La venta mensual subió pero la reposición no acompañó.

### Implicancia para reposición
Si el ratio C/V en pares es 75% y la cobertura global dice 593 días,
el negocio está perdiendo ventas por quiebre invisible.
**La app debe priorizar SKUs con velocidad real alta + stock 0,
no los que tienen stock alto con venta baja.**

### Campos SQL confirmados
```
Ventas:  ventas1.cantidad, ventas1.precio, ventas1.precio_costo, ventas1.total_item, ventas1.fecha
         codigo=1 (venta), codigo=3 (devolución, restar). Excluir codigo 7,36.
Compras: compras1.cantidad, compras1.precio, compras1.fecha, operacion='+'
Stock:   stock.stock_actual (NO cantidad)
Artículo: articulo.codigo (PK), articulo.marca
```
