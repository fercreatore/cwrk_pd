# Sistema de Serie en Stock — Hallazgos y Plan Barcode

> Documentado: 10 marzo 2026
> Basado en: análisis de datos reales del ERP MS Gestión (producción 111)

---

## 1. Cómo funciona la serie en el ERP hoy

### Campo `serie` en tabla `stock`
- Clave compuesta: `(deposito, articulo, serie)`
- Cada artículo puede tener MÚLTIPLES filas de stock con distintas series
- **Stock total de un artículo = SUM(stock_actual) de todas las series**

### Campo `serie` en tabla `movi_stock`
- Registra con qué serie se hizo cada movimiento
- Compras: serie depende de la base (ver abajo)
- Ventas/POS: siempre serie=' ' (espacio)

---

## 2. Comportamiento por base (CRÍTICO — son distintas)

### msgestion03 (H4 SRL)
| Operación | serie en movi_stock | serie en stock |
|-----------|-------------------|----------------|
| Compra/Remito (ERP) | `' '` (espacio) | Solo actualiza serie `' '` |
| Venta/POS | `' '` (espacio) | Solo actualiza serie `' '` |

**H4 no usa series YYMM**. Todo va a serie=' '. El stock es una sola fila por artículo/deposito.

### msgestion01 (CALZALINDO / ABI)
| Operación | serie en movi_stock | serie en stock |
|-----------|-------------------|----------------|
| Compra/Remito (ERP) | `'YYMM'` (ej '2603') | Solo actualiza serie `'YYMM'` |
| Venta/POS | `' '` (espacio) | Solo actualiza serie `' '` |

**CALZALINDO usa series YYMM para compras**. El stock tiene:
- Serie `' '`: acumula las BAJAS de ventas (va negativo)
- Serie `'YYMM'`: acumula las ALTAS de cada lote mensual (siempre positivo)
- **Stock real = SUM(todas las series)**

Ejemplo artículo 196897 en CALZALINDO dep 11:
```
serie ' ':   stock_actual = -71  (ventas acumuladas)
serie '2507': stock_actual =  12  (lote julio 2025)
serie '2509': stock_actual =   6  (lote septiembre 2025)
serie '2601': stock_actual =   9  (lote enero 2026)
serie '2603': stock_actual =   4  (lote marzo 2026)
─────────────────────────────────
TOTAL:                        -40  (este artículo tiene -40 en este depósito)
```

---

## 3. Campo `unidades` vs `cantidad`

En movi_stock y compras1:
- `cantidad`: unidades del artículo (pares, unidades, etc.)
- `unidades`: en el ERP nativo, **unidades = cantidad**
- `stock_unidades`: en stock, **stock_unidades = stock_actual**

El ERP no tiene implementada la serialización por unidad todavía. Ambos campos son iguales.

---

## 4. Comportamiento del ERP al ELIMINAR un remito

Cuando se borra un remito desde el ejecutable:
1. ✅ Elimina registros de `compras2`, `compras1`, `comprasr`, `movi_stock`
2. ✅ Revierte `stock_actual` en la serie correspondiente
3. ❌ **NO elimina** la fila de stock con serie YYMM (la deja con stock=0)
4. ❌ **NO toca** la serie `' '` si el movimiento era con serie YYMM

Esto significa que después de borrar un remito en CALZALINDO, queda una fila "fantasma" en stock con serie YYMM y stock=0. Es inofensiva pero se acumula.

---

## 5. Plan de serialización Barcode (futuro)

### Concepto
La serie ya ES YYMM+XXXX (8 dígitos). No es una extensión futura, es el formato definitivo:
```
Formato: YYMMXXXX
         ││││└┘└┘
         ││││  └── secuencial de unidad (0001 a 9999)
         └┘└┘
           └── año y mes del lote

Ejemplo: llegan 10 pares en marzo 2026
  26030001  → par 1
  26030002  → par 2
  26030003  → par 3
  ...
  26030010  → par 10
```

### Cada serie = 1 unidad física
- `stock_unidades = 1` por fila (siempre)
- `stock_actual = 1` por fila (mientras esté en stock)
- Se puede rastrear cada unidad individualmente
- Al vender, se da de baja la serie específica del par vendido

### Integración con código de barras
La serie se concatena al código de barras del artículo:
```
Código barra base:  17198710417
Con serie:          1719871041726030001
                    └── artículo ──┘└─ serie ─┘
```

### Estado actual
- El campo `serie` en stock/movi_stock YA soporta el formato (es varchar)
- Hoy se usa solo YYMM (4 dígitos) como identificador de lote sin serializar
- Las ventas/POS todavía usan serie=' ' (no dan de baja por serie individual)

### Lo que falta implementar
1. **Generación de serie secuencial** al crear remito: por cada unidad, crear serie YYMM+correlativo
2. **N filas de stock** en vez de 1: cada par = 1 fila con stock_actual=1, stock_unidades=1
3. **N registros movi_stock** en vez de 1: cada uno con cantidad=1, unidades=1
4. **Baja por serie** en ventas/POS: escanear barcode → leer serie → dar de baja esa fila específica
5. **Impresión de etiquetas** con código de barras completo (artículo + serie)

### Impacto en nuestro código web (`remito_crear()`)
Cuando se implemente:
- En vez de 1 fila stock con cantidad=N, crear N filas con cantidad=1 y serie=YYMMXXXX
- En vez de 1 registro movi_stock, crear N registros con cantidad=1, unidades=1
- Aplica solo a CALZALINDO (msg01). H4 (msg03) sigue con serie=' '

---

## 6. Estado actual del código web (`reportes.py`)

### Fix aplicado (10 mar 2026)
```python
# Dentro del loop: for empresa, base, dest_items in destinos:
serie = datetime.now().strftime('%y%m') if empresa == 'CALZALINDO' else ' '
```

- **CALZALINDO → msg01**: serie=YYMM, stock solo en serie YYMM
- **H4 → msg03**: serie=' ', stock solo en serie ' '
- `movi_stock.unidades = int(cant)` (= cantidad)
- `stock_unidades` se actualiza junto con `stock_actual`
- Un solo bloque de stock (sin doble conteo)

### PENDIENTE: sincronizar al 111
El reportes.py con el fix está en el Mac pero **aún no se confirmó que el 111 lo tenga**. El remito de prueba GO DANCE corrió con el código viejo.

---

## 7. Datos de referencia

### Usuarios en movi_stock
| Usuario | Origen |
|---------|--------|
| SST | ERP ejecutable (sucursal principal) |
| SS | ERP ejecutable (otra sucursal) |
| WB | Código web (nuestro `remito_crear()`) |
| POS(xxx) | Punto de venta |

### Remitos afectados por código WB (historial)
| Remito | Base | Artículos | Estado |
|--------|------|-----------|--------|
| 1926645 | msg03 | 8 arts PIRA/CAMILA | ✅ Limpiado (serie→' ', stock corregido) |
| 11112023 | msg03 | 1 art GO DANCE | ⚠️ Pendiente borrar + limpiar |
