# PROYECTO: CARGA AUTOMÁTICA DE NOTAS DE PEDIDO
## Instrucciones para Cowork — H4 / Calzalindo

> Seguí los pasos EN ORDEN. Cada paso tiene criterio de éxito.
> Antes de arrancar cada paso, leé el archivo `.py` correspondiente — tiene comentarios detallados.
> Si algo falla, anotá el error y pasá al siguiente paso si es posible.

---

## CONTEXTO RÁPIDO

- **Negocio**: cadena de calzado en Venado Tuerto, Argentina
- **ERP**: MS Gestión sobre SQL Server 2012 RTM (192.168.2.111 producción)
- **Réplica**: 192.168.2.112 (solo SELECT, conectada vía MCP sql-replica)
- **Bases**: `msgestion01` (CALZALINDO), `msgestion03` (H4), `msgestion01art` (artículos compartidos), `msgestionC` (VIEWs combinadas, NO insertar), `omicronvt` (analítica)
- **Objetivo**: cargar notas de pedido desde Excel/CSV/PDF a las tablas `pedico2` (cabecera) y `pedico1` (detalle)
- **Lógica clave**: si el artículo no existe → darlo de alta primero; si existe → ir directo al pedido

---

## ESTRUCTURA DE ARCHIVOS

```
cowork_pedidos/
├── INSTRUCCIONES_COWORK.md     ← este archivo
├── CLAUDE.md                   ← contexto completo del proyecto
├── BITACORA_DESARROLLO.md      ← historial detallado por fecha
├── config.py                   ← conexión SQL Server + proveedores configurados
├── paso1_verificar_bd.py       ← verificar conexión y estructura de tablas
├── paso2_buscar_articulo.py    ← lógica de búsqueda/alta de artículo (dar_de_alta)
├── paso3_calcular_periodo.py   ← cálculo de período OI/PV/H1/H2
├── paso4_insertar_pedido.py    ← INSERT en pedico2 + pedico1 (con routing empresa→base)
├── paso5_parsear_excel.py      ← parseo de archivo Excel/CSV
├── paso6_flujo_completo.py     ← orquesta todos los pasos anteriores
├── _scripts_oneshot/           ← scripts de inserción puntuales por proveedor
│   ├── insertar_knu_gtn.py         ✅ EJECUTADO — 124 pares GTN
│   ├── insertar_carmel_ringo.py    ✅ EJECUTADO — 30 pares CARMEL CANELA
│   ├── insertar_diadora.py         ✅ EJECUTADO — 48 pares DIADORA
│   ├── insertar_atomik_runflex.py  ✅ EJECUTADO — 120 pares ATOMIK RUNFLEX
│   ├── insertar_piccadilly.py      ⏳ PENDIENTE — 288 pares PICCADILLY
│   └── insertar_footy.py           ⏳ PENDIENTE — 552 pares FOOTY LICENCIAS
└── tests/
```

---

## REGLAS DE NEGOCIO PARA ARTÍCULOS

### Creación de artículo (dar_de_alta)

Cada **artículo × talle** es un registro independiente en `msgestion01art.dbo.articulo`.
PK = campo `codigo` (autoincremental). Los campos clave son:

| Campo | Qué es | Ejemplo |
|-------|--------|---------|
| `descripcion_1` | Descripción larga (hasta 60 chars) | `PPX3941 LILA ZAPA SUBLIM C/LUZ PEPPA` |
| `descripcion_3` | Descripción corta (hasta 40 chars) | `PPX3941 ZAPA SUBLIM C/LUZ PEPPA FOOTY` |
| `descripcion_4` | Color | `LILA` |
| `descripcion_5` | Talle | `26` |
| `codigo_sinonimo` | Código auxiliar (12 chars, único) | `950PPX394126` |
| `marca` | Código de marca (de tabla marcas) | `139` (FOOTY) |
| `subrubro` | Clasificación producto | `49` (zapatillas), `60` (pantuflas) |
| `rubro` | Género | `4` (niños), `5` (niñas) |
| `grupo` | Subgrupo | `"5"` (nenes), `"17"` (nenas) |
| `linea` | Temporada | `1` (verano), `2` (invierno) |
| `proveedor` | Código proveedor | `950` |
| `precio_costo` | Precio de costo | `24900` |
| `utilidad_1..4` | Márgenes (contado/lista/intermedio/mayo) | `100 / 124 / 60 / 45` |
| `formula` | Fórmula de precio | `1` |

### Talles — Regla binumeral (IMPORTANTE)

Para productos **binumerales** (pantuflas, ojotas, zuecos dobles, etc.):

> **SIEMPRE usar el talle MAYOR del par como valor en `descripcion_5`**

| Talle real | Se carga como |
|------------|---------------|
| 25/26 | `26` |
| 27/28 | `28` |
| 29/30 | `30` |
| 31/32 | `32` |
| 33/34 | `34` |
| 35/36 | `36` |
| 37/38 | `38` |
| 42/43 | `43` |

Esto estandariza y evita problemas con caracteres especiales en el campo talle.

### Marca ≠ Proveedor

La marca y el proveedor pueden ser códigos distintos. Ejemplos:
- FOOTY: marca=139, proveedor=950 (TIVORY TRADING CO S.A.)
- DIADORA: marca=675, proveedor=614 (CALZADOS BLANCO S.A.)
- ATOMIK: marca=594, proveedor=594 (VICBOR SRL) — en este caso coinciden

Siempre verificar en BD antes de asumir.

---

## REGLAS PARA NOTA DE PEDIDO (pedico2 + pedico1)

### Estructura del pedido

- **pedico2** = cabecera (1 registro por pedido)
- **pedico1** = detalle (1 registro por artículo/talle en el pedido)
- Tablas **compartidas** entre msgestion01 y msgestion03
- `codigo=8, letra='X', sucursal=1, estado='V', usuario='COWORK'`
- `numero` y `orden`: MAX+1 auto-incremental

### Routing empresa → base

| Empresa | Base para INSERT |
|---------|-----------------|
| H4 | `MSGESTION03.dbo.pedico2` / `pedico1` |
| CALZALINDO | `MSGESTION01.dbo.pedico2` / `pedico1` |

La función `get_tabla_base("pedico2", "H4")` en `paso4_insertar_pedido.py` resuelve esto automáticamente.

**IMPORTANTE**: Se inserta en UNA sola base. No hay duplicación.

### Proceso de carga (script oneshot típico)

```
1. Definir MODELOS[] con: art_code, color, licencia/marca, precio, talles[(talle, cantidad)]
2. Verificar totales contra Excel/factura
3. Fase 1 — dar_de_alta(): crea artículos que no existen
4. Fase 2 — insertar_pedido(): crea cabecera + renglones
5. Anti-duplicado: buscar en observaciones si ya se insertó
6. Dry-run primero (--ejecutar para escribir de verdad)
```

### Cabecera del pedido (pedico2)

```python
cabecera = {
    "empresa":           "H4",           # o "CALZALINDO"
    "cuenta":            950,            # número proveedor
    "denominacion":      "TIVORY...",    # nombre proveedor
    "fecha_comprobante": date(2026,2,20),# fecha pedido
    "fecha_entrega":     date(2026,5,15),# entrega estimada
    "observaciones":     "Pedido FOOTY...",  # texto libre (usar para anti-dup)
}
```

### Renglones del pedido (pedico1)

```python
renglones = [{
    "articulo":        360550,     # codigo del artículo (de dar_de_alta)
    "descripcion":     "PPX3941 LILA ZAPA SUBLIM C/LUZ PEPPA",
    "codigo_sinonimo": "",
    "cantidad":        3,          # pares para este talle
    "precio":          24900,      # precio unitario
}]
```

---

## PIPELINE DE EJECUCIÓN

### Requisitos previos
- Python en 111: usar `py -3` (NO `python` que es 2.7)
- Scripts en `C:\cowork_pedidos\`
- Deploy desde Mac: `cd _sync_tools && ./deploy.sh scripts`

### Ejecución de script oneshot

```bash
# 1. Deploy al servidor
cd ~/Desktop/cowork_pedidos/_sync_tools
./deploy.sh scripts

# 2. En el 111 (vía RDP o SSH)
cd C:\cowork_pedidos\_scripts_oneshot

# 3. Dry-run primero
py -3 insertar_footy.py

# 4. Ejecución real
py -3 insertar_footy.py --ejecutar
```

### Verificación post-inserción

```sql
-- Verificar cabecera
SELECT numero, cuenta, denominacion, observaciones, monto_general
FROM msgestionC.dbo.pedico2
WHERE codigo=8 AND cuenta=950
ORDER BY numero DESC

-- Verificar renglones
SELECT renglon, articulo, descripcion, cantidad, precio
FROM msgestionC.dbo.pedico1
WHERE numero = {NUMERO_PEDIDO}
ORDER BY renglon
```

---

## PROVEEDORES CONFIGURADOS

| # | Proveedor | Marca | Empresa | Notas |
|---|-----------|-------|---------|-------|
| 668 | ALPARGATAS S.A.I.C. | TOPPER (314) | H4 | desc 6%, util1 98.9% |
| 104 | "EL GITANO" - GTN | GTN (104) | CALZALINDO | 100% base 01 |
| 594 | VICBOR SRL | ATOMIK (594) / WAKE (746) | H4 | desc 50.05%+bonif |
| 656 | DISTRINANDO DEPORTES | REEBOK (513) | H4 | desc en factura |
| 561 | Souter S.A. | RINGO/CARMEL (294) | H4 | sin descuento |
| 614 | CALZADOS BLANCO S.A. | DIADORA (675) | H4 | bonif 5% |
| 713 | DISTRINANDO MODA S.A. | PICCADILLY (656) | H4 | desc 7% ctdo |
| 950 | TIVORY TRADING CO S.A. | FOOTY (139) | H4 | 10% ctdo 10 días |

---

## CAMPOS QUE CONFUNDEN

- Artículos: PK es `codigo` (NO `numero`, NO `articulo`)
- Stock: campo `stock_actual` (NO `cantidad`) en `msgestionC.dbo.stock`
- Proveedor: campo `denominacion` (NO `nombre_proveedor`)
- Compras2: `monto_general` y `concepto_gravado` (NO existe `importe_neto`)
- Ventas: EXCLUIR siempre codigo 7 y 36 (remitos internos)
- SQL Server 2012 RTM: **NO soporta TRY_CAST** → usar `ISNUMERIC() + CAST()`
- msgestionC: solo VIEWs → NUNCA insertar ahí (error 4406)

---

## NOTAS TÉCNICAS

- Remitos tienen codigo 7 y 36 — EXCLUIR siempre de análisis de ventas
- Facturas = codigo 1 (suman), Notas de Crédito = codigo 3 (restan)
- Las marcas tienen campo `descripcion` (NO `nombre`) en `msgestion01art.dbo.marcas`
- El talle está en `articulo.descripcion_5`
- Para industria de un artículo: JOIN con `omicronvt.dbo.agrupador_subrubro`
- Para proyección de compras: SIEMPRE hacer análisis de quiebre de stock primero
- MCP sql-replica conecta a réplica 112 (solo SELECT). INSERT solo por Python en 111.
