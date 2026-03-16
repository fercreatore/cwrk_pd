# Proceso de Vinculación de Imágenes de Artículos

## Ubicación de imágenes en el server 111
```
F:\Macroges\Imagenes
```

## Vinculación SQL (tabla `imagen`)

Para vincular una imagen a un artículo, se usa un INSERT en la tabla `imagen` y
una función SQL de Macroges que genera el nombre del archivo:

```sql
-- Obtener nombre de imagen para un artículo
SELECT dbo.f_sql_nombre_imagen(
    empresa,      -- 1
    tipo,         -- 'AR' (artículo)
    sistema,      -- 0
    codigo,       -- 0
    letra,        -- (vacío)
    sucursal,     -- (0)
    numero,       -- codigo_corto (= codigo del artículo)
    orden,        -- (0)
    renglon,      -- (0)
    extencion     -- 'jpg' o 'png'
) AS nombre_imagen
FROM imagen
WHERE numero = codigo_corto
  AND codigo = 0
  AND tipo = 'AR'
  AND empresa = 1
  AND sistema = 0
```

- `codigo_corto` = campo `codigo` de `msgestion01art.dbo.articulo` (PK del artículo)
- La función `dbo.f_sql_nombre_imagen()` devuelve el nombre del archivo que Macroges espera
- El archivo se guarda en `F:\Macroges\Imagenes\` con ese nombre

## Fuente de imágenes: Lesedife

- **Web catálogo**: https://lesedife.com
- **Email cuenta**: pagos@calzalindo.com.ar
- **Código cliente**: 16710
- **Tutorial**: video WhatsApp 2026-03-12 (cómo descargar fotos de la web)

### Proceso manual actual
1. Entrar a lesedife.com con las credenciales
2. Buscar el artículo por código de proveedor (ej: 67.0800130)
3. Descargar la imagen del producto
4. Renombrar según lo que devuelve `f_sql_nombre_imagen()`
5. Copiar a `F:\Macroges\Imagenes\`
6. INSERT en tabla `imagen`

### TODO: Automatización
- Script Python que:
  1. Tome la lista de artículos nuevos (del alta masiva)
  2. Haga login en lesedife.com
  3. Descargue las imágenes por código de proveedor
  4. Use `f_sql_nombre_imagen()` para obtener el nombre correcto
  5. Copie a `F:\Macroges\Imagenes\`
  6. Haga INSERT en tabla `imagen`
- Requiere: investigar la estructura de la web de Lesedife (login, URLs de imágenes)
- El video tutorial tiene el paso a paso visual
