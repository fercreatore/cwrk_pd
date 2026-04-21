# Cómo encontrar fotos de producto en el sistema

## Sistema de imágenes (2 capas)

### Capa 1 — Fotos del catálogo (VPS PostgreSQL + nginx)

Las fotos del catálogo se guardan en PostgreSQL (`clz_productos` en 200.58.109.125)
y se sirven públicamente vía nginx en el VPS.

**MCP disponible**: `mcp__postgres-clz__query` (solo SELECT)

#### Flujo para encontrar la URL de una foto

**Paso 1 — Obtener `familia_id` del producto en la tabla `productos`:**

```sql
SELECT id, nombre_mg, familia_id, marca_id
FROM productos
WHERE nombre_mg LIKE '8082%'   -- o el modelo que busques
```

El `familia_id` tiene formato `MMMFFFFF` donde MMM = código marca (2 dígitos) y FFFFF = modelo (4 dígitos).
Ejemplo: marca ALITA (id=24, código=13) + modelo 8082 → `familia_id = '01308082'`

**Paso 2 — Buscar imágenes en `producto_imagenes` usando `familia_id` como `cod_familia`:**

```sql
SELECT cod_familia, path_relativo, archivo_final, nro_imagen, estado
FROM producto_imagenes
WHERE cod_familia = '01308082'   -- el familia_id del paso 1
ORDER BY nro_imagen
```

**Paso 3 — Construir URL pública:**

```
https://n8n.calzalindo.com.ar/imagenes/{path_relativo}/{archivo_final}
```

Ejemplo: `path_relativo = '0/0130808200'`, `archivo_final = '0130808200-01.jpg'`
→ URL: `https://n8n.calzalindo.com.ar/imagenes/0/0130808200/0130808200-01.jpg`

⚠️ Si la URL da 404: las imágenes están en la BD pero no sincronizadas al servidor nginx todavía.
En ese caso usar **Capa 2** (archivo físico en el 111).

#### Query completa en un solo paso (ALITA como ejemplo):

```sql
SELECT
    p.nombre_mg,
    p.familia_id,
    pi.cod_familia,
    pi.path_relativo,
    pi.archivo_final,
    pi.nro_imagen,
    'https://n8n.calzalindo.com.ar/imagenes/' || pi.path_relativo || '/' || pi.archivo_final AS url_publica
FROM productos p
INNER JOIN producto_imagenes pi ON pi.cod_familia = p.familia_id
WHERE p.marca_id = 24           -- 24 = ALITA en prod_marcas
  AND pi.nro_imagen = 1
ORDER BY p.nombre_mg
```

#### Tabla de marcas — prod_marcas (PostgreSQL) cruzada con ERP

La tabla `prod_marcas` en PostgreSQL usa un `id` distinto al campo `marca` del ERP (`msgestion01art.dbo.articulo.marca`).
El campo `marca` del ERP está en `msgestion01art.dbo.marcas` (columnas: `codigo`, `descripcion`).

**Query para cruzar ambas** (cuando tenés el nombre):
```sql
-- PostgreSQL: familia_id empieza con el id en 4 dígitos
SELECT id, nombre FROM prod_marcas WHERE LOWER(nombre) LIKE '%alita%'
```

**Marcas principales con prefijo familia_id y código ERP:**

| marca_id_pg | nombre (PostgreSQL) | prefijo familia_id | código ERP (articulo.marca) |
|-------------|---------------------|-------------------|------------------------------|
| 24 | ALITA | 0130 | 13 |
| 58 | ATOMIK | 5493 | (buscar en ERP) |
| 211 | DIADORA | 6140 | 675 |
| 290 | FLOYD MEDIAS | 6410 | (buscar en ERP) |
| 326 | GO by CLZ | 0112 | (buscar en ERP) |
| 329 | GONDOLINO | 0570 | (buscar en ERP) |
| 347 | GTN | 1040 | 104 |
| 377 | HUSH PUPPIES | 2640 | (buscar en ERP) |
| 608 | PICCADILLY | 6561 | (buscar en ERP) |
| 597 | PENELOPE | 0230 | (buscar en ERP) |
| 648 | REEBOK | 6560 | 513 |
| 660 | RINGO | 2920 | (buscar en ERP) |
| 567 | OLYMPIKUS | 2643 | 722 |
| 758 | TOPPER | 6680 | 314 |
| 750 | TIMMIS | 0110 | (buscar en ERP) |
| 567 | OLYMPIKUS | 2643 | (buscar en ERP) |

**Tabla completa prod_marcas con productos:** ver archivo generado por el agente o consultar PG directamente.

**Regla para el prefijo familia_id:**
El `familia_id` en `productos` tiene formato: primeros 4 chars = prefijo marca.
Ejemplo ALITA: `marca_id_pg=24` → `familia_id = '01308082'` → prefijo = `0130`.
El prefijo NO es el `marca_id_pg` directamente — hay que leerlo de la tabla `productos`.

---

### Capa 2 — Fotos del ERP (SQL Server 111, carpeta Macroges)

Las fotos vinculadas al ERP están en `F:\Macroges\Imagenes\` del servidor 111.
Accesibles desde Mac vía SMB: `//administrador:cagr$2011@192.168.2.111/Macroges/Imagenes`

La tabla `imagen` del SQL Server registra qué artículos tienen foto vinculada al ERP.
Columnas clave: `tipo='AR'`, `empresa=1`, `numero` = código del artículo, `extencion`.

**Verificar si un artículo tiene foto en el ERP:**

```sql
-- Via MCP sql-replica (apunta al 111)
SELECT i.numero, i.extencion, i.nombre_archivo
FROM imagen i
WHERE i.tipo = 'AR'
  AND i.empresa = 1
  AND i.sistema = 0
  AND i.numero IN (
    SELECT codigo
    FROM msgestion01art.dbo.articulo
    WHERE marca = 13  -- ALITA
  )
```

El nombre de archivo lo genera la función `dbo.f_sql_nombre_imagen()` del ERP.
Para descargarlo vía SMB: montar `//192.168.2.111/Macroges/Imagenes` y leer el archivo.

---

### Capa 3 — Código Python (multicanal/imagenes.py)

Si estás en contexto de código Python, usar directamente:

```python
from multicanal.imagenes import get_imagen_articulo, urls_producto

# Por codigo_sinonimo (12 chars)
url = get_imagen_articulo('013080820036')

# Por familia_id / producto_base (10 chars)  
urls = urls_producto('0130808200')
```

La función busca en PostgreSQL (VPS) y construye la URL nginx automáticamente.

---

## Ejemplo completo: fotos de los 4 modelos ALITA invierno 2026

Estos 4 modelos ingresaron en abril 2026 (familia_id en PG confirmado):

| Modelo ERP       | familia_id | URL foto principal |
|------------------|------------|-------------------|
| 8082 NEGRO MOCASIN C/COSTURAS COMB  | 01308082 | https://n8n.calzalindo.com.ar/imagenes/0/0130808200/0130808200-01.jpg |
| 8086 NEGRO MOCASIN DET COSTURAS     | 01308086 | https://n8n.calzalindo.com.ar/imagenes/0/0130808600/0130808600-01.jpg |
| 8087 VISON MOCASIN C/COSTURAS COMB  | 01308087 | (sin imágenes en PG al 17-abr-2026) |
| 5182 NEGRO BOTA C/CIERRE DET HEBILLA| 01305182 | https://n8n.calzalindo.com.ar/imagenes/0/0130518200/0130518200-01.jpg |

Si las URLs anteriores dan 404, las fotos están en PG pero no en nginx todavía.
Alternativa: bajarlas vía SMB desde `F:\Macroges\Imagenes\` en el 111.

---

## Estado fotos ALITA invierno 2026 (al 17-abr-2026)

Las fotos físicas están en `F:\Macroges\Imagenes\` del servidor 111 (confirmado vía SMB).
Los registros en `producto_imagenes` (PG) existen pero nginx da 404 — archivos aún no sincronizados al VPS.

| Modelo | familia_id | archivo_origen (Macroges) | nginx URL | SMB OK |
|--------|------------|--------------------------|-----------|--------|
| 8082 NEGRO MOCASIN C/COSTURAS COMB | 01308082 | `0001AR0000000-0000000000000336288000001.jpg` | 404 | ✅ 1.1MB |
| 8086 NEGRO MOCASIN DET COSTURAS | 01308086 | `0001AR0000000-0000000000000336286000001.jpg` | 404 | ✅ 1.1MB |
| 5182 NEGRO BOTA C/CIERRE DET HEBILLA | 01305182 | `0001AR0000000-0000000000000336287000001.jpg` | 404 | ✅ 1.1MB |
| 8087 VISON MOCASIN C/COSTURAS COMB | 01308087 | (sin registro en PG) | — | — |

Para bajar las fotos vía SMB desde Mac:
```bash
mount_smbfs '//administrador:cagr$2011@192.168.2.111/Macroges' /tmp/macroges_mount
cp /tmp/macroges_mount/Imagenes/0001AR0000000-0000000000000336288000001.jpg /tmp/
```

---

## Error común que cometí (no repetir)

❌ **MAL**: Buscar en `producto_imagenes` con `cod_familia = '8082'` o `'01308082'` directamente sin pasar por la tabla `productos` para obtener el `familia_id` correcto.

✅ **BIEN**: Ir siempre a `productos` primero para obtener `familia_id`, luego joinear con `producto_imagenes` usando ese valor como `cod_familia`.

La razón: el `familia_id` en `productos` incluye el prefijo de marca (`013` para ALITA), no es solo el número de modelo.
