# paso7_buscar_imagenes.py
# Módulo de búsqueda y descarga de imágenes web para artículos.
#
# Busca imágenes de productos (calzado) en internet, las descarga
# con resolución apta para tienda web, y las guarda con naming estándar.
#
# Funciones principales:
#   buscar_imagenes(query, cantidad=5)       → lista de URLs de imágenes
#   descargar_imagen(url, destino)            → descarga y valida resolución
#   procesar_articulo(codigo, descripcion)    → busca, descarga y asocia imagen
#   procesar_lote(lista_articulos)            → procesamiento masivo
#
# Backends de búsqueda:
#   - DuckDuckGo (default, sin API key)
#   - Google Custom Search (requiere API key en config)
#
# EJECUTAR: python paso7_buscar_imagenes.py [codigo_articulo]

import os
import re
import sys
import json
import time
import hashlib
import logging
from pathlib import Path
from io import BytesIO
from urllib.parse import quote_plus, urlparse

import requests
from PIL import Image

# ── CONFIGURACIÓN ────────────────────────────────────────────────

# Carpeta donde se guardan las imágenes descargadas
CARPETA_IMAGENES = os.path.join(os.path.dirname(__file__), "imagenes_articulos")

# Especificaciones técnicas para imágenes web
IMG_MIN_WIDTH  = 800    # ancho mínimo aceptable (px)
IMG_MIN_HEIGHT = 800    # alto mínimo aceptable (px)
IMG_TARGET_WIDTH  = 1200  # ancho objetivo para resize
IMG_TARGET_HEIGHT = 1200  # alto objetivo para resize
IMG_MAX_FILESIZE_KB = 500  # tamaño máximo del archivo final (KB)
IMG_FORMAT = "WEBP"     # formato de salida (WEBP = mejor compresión para web)
IMG_QUALITY = 85        # calidad de compresión (1-100)
IMG_BACKGROUND = (255, 255, 255)  # fondo blanco para transparencias

# Búsqueda
MAX_RESULTADOS = 10      # cantidad máxima de resultados por búsqueda
TIMEOUT_DESCARGA = 15    # timeout para descarga de imagen (seg)
TIMEOUT_BUSQUEDA = 10    # timeout para búsqueda (seg)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Google Custom Search (opcional — dejar vacío para usar DuckDuckGo)
GOOGLE_API_KEY = ""
GOOGLE_CX = ""  # Custom Search Engine ID

# Mapeo de marcas → nombre para búsqueda web
MARCAS_BUSQUEDA = {
    746: "Wake",
    314: "Topper",
    794: "Atomik",
    515: "Ciudadela",
    # Agregar más marcas según necesidad
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("img_search")


# ══════════════════════════════════════════════════════════════════
# BACKEND: DuckDuckGo Image Search (sin API key)
# ══════════════════════════════════════════════════════════════════

def _buscar_ddg(query: str, cantidad: int = 5) -> list[dict]:
    """
    Busca imágenes en DuckDuckGo.
    Retorna lista de dicts con: url, thumbnail, width, height, title, source
    """
    resultados = []
    headers = {"User-Agent": USER_AGENT}

    # Paso 1: obtener token vqd
    try:
        resp = requests.get(
            "https://duckduckgo.com/",
            params={"q": query},
            headers=headers,
            timeout=TIMEOUT_BUSQUEDA
        )
        # Extraer vqd token del HTML
        vqd_match = re.search(r'vqd=["\']([^"\']+)["\']', resp.text)
        if not vqd_match:
            # Intentar formato alternativo
            vqd_match = re.search(r'vqd=([\d-]+)', resp.text)
        if not vqd_match:
            log.warning("No se pudo obtener token DDG, intentando método alternativo")
            return _buscar_ddg_alt(query, cantidad)
        vqd = vqd_match.group(1)
    except Exception as e:
        log.error(f"Error obteniendo token DDG: {e}")
        return _buscar_ddg_alt(query, cantidad)

    # Paso 2: buscar imágenes
    try:
        params = {
            "l": "ar-es",
            "o": "json",
            "q": query,
            "vqd": vqd,
            "f": ",,,,,",
            "p": "1",
            "v7exp": "a",
        }
        resp = requests.get(
            "https://duckduckgo.com/i.js",
            params=params,
            headers=headers,
            timeout=TIMEOUT_BUSQUEDA
        )
        data = resp.json()
        for item in data.get("results", [])[:cantidad]:
            resultados.append({
                "url": item.get("image", ""),
                "thumbnail": item.get("thumbnail", ""),
                "width": item.get("width", 0),
                "height": item.get("height", 0),
                "title": item.get("title", ""),
                "source": item.get("source", ""),
            })
    except Exception as e:
        log.error(f"Error buscando imágenes DDG: {e}")

    return resultados


def _buscar_ddg_alt(query: str, cantidad: int = 5) -> list[dict]:
    """
    Método alternativo usando DuckDuckGo Lite.
    Menos resultados pero más estable.
    """
    resultados = []
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(
            "https://lite.duckduckgo.com/lite/",
            params={"q": f"{query} zapatilla calzado", "kl": "ar-es"},
            headers=headers,
            timeout=TIMEOUT_BUSQUEDA
        )
        # Extraer URLs de imágenes de los resultados
        urls = re.findall(r'https?://[^\s"<>]+\.(?:jpg|jpeg|png|webp)', resp.text, re.IGNORECASE)
        for url in urls[:cantidad]:
            resultados.append({
                "url": url, "thumbnail": url,
                "width": 0, "height": 0,
                "title": "", "source": urlparse(url).netloc,
            })
    except Exception as e:
        log.error(f"Error en búsqueda DDG alternativa: {e}")
    return resultados


# ══════════════════════════════════════════════════════════════════
# BACKEND: Google Custom Search (requiere API key)
# ══════════════════════════════════════════════════════════════════

def _buscar_google(query: str, cantidad: int = 5) -> list[dict]:
    """
    Busca imágenes usando Google Custom Search API.
    Requiere GOOGLE_API_KEY y GOOGLE_CX configurados.
    """
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        log.warning("Google API key no configurada, usando DuckDuckGo")
        return _buscar_ddg(query, cantidad)

    resultados = []
    try:
        params = {
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CX,
            "q": query,
            "searchType": "image",
            "num": min(cantidad, 10),
            "imgSize": "large",
            "safe": "active",
        }
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
            timeout=TIMEOUT_BUSQUEDA
        )
        data = resp.json()
        for item in data.get("items", []):
            img = item.get("image", {})
            resultados.append({
                "url": item.get("link", ""),
                "thumbnail": img.get("thumbnailLink", ""),
                "width": img.get("width", 0),
                "height": img.get("height", 0),
                "title": item.get("title", ""),
                "source": item.get("displayLink", ""),
            })
    except Exception as e:
        log.error(f"Error buscando en Google: {e}")
    return resultados


# ══════════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL DE BÚSQUEDA
# ══════════════════════════════════════════════════════════════════

def buscar_imagenes(query: str, cantidad: int = MAX_RESULTADOS, backend: str = "auto") -> list[dict]:
    """
    Busca imágenes de productos en internet.

    Args:
        query: texto de búsqueda (ej: "Wake WKC215 zapatilla negro")
        cantidad: cantidad máxima de resultados
        backend: "ddg", "google", o "auto" (prueba google primero si hay key)

    Returns:
        Lista de dicts con: url, thumbnail, width, height, title, source
    """
    if backend == "auto":
        if GOOGLE_API_KEY and GOOGLE_CX:
            resultados = _buscar_google(query, cantidad)
            if resultados:
                return resultados
        return _buscar_ddg(query, cantidad)
    elif backend == "google":
        return _buscar_google(query, cantidad)
    else:
        return _buscar_ddg(query, cantidad)


def construir_query(marca_nombre: str, modelo: str, color: str = "",
                    tipo: str = "zapatilla") -> str:
    """
    Construye una query de búsqueda optimizada para calzado.

    Args:
        marca_nombre: nombre de la marca (ej: "Wake", "Topper")
        modelo: código/nombre del modelo (ej: "WKC215", "SENDAI")
        color: color del producto (ej: "NEGRO", "BLANCO/AZUL")
        tipo: tipo de producto (ej: "zapatilla", "borcego", "sandalia")
    """
    partes = [marca_nombre, modelo]
    if color:
        # Tomar solo el primer color si hay compuestos
        color_principal = color.split("/")[0].strip()
        partes.append(color_principal)
    partes.append(tipo)
    return " ".join(partes)


# ══════════════════════════════════════════════════════════════════
# DESCARGA Y PROCESAMIENTO DE IMÁGENES
# ══════════════════════════════════════════════════════════════════

def descargar_imagen(url: str, timeout: int = TIMEOUT_DESCARGA) -> Image.Image | None:
    """
    Descarga una imagen desde una URL y la retorna como objeto PIL.
    Retorna None si falla o la imagen no cumple requisitos mínimos.
    """
    try:
        headers = {"User-Agent": USER_AGENT, "Referer": urlparse(url).scheme + "://" + urlparse(url).netloc}
        resp = requests.get(url, headers=headers, timeout=timeout, stream=True)
        resp.raise_for_status()

        # Verificar que sea una imagen
        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type and not url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            log.debug(f"No es imagen: {content_type} - {url[:80]}")
            return None

        # Limitar descarga a 10MB
        contenido = b""
        for chunk in resp.iter_content(chunk_size=8192):
            contenido += chunk
            if len(contenido) > 10 * 1024 * 1024:
                log.debug(f"Imagen demasiado grande (>10MB): {url[:80]}")
                return None

        img = Image.open(BytesIO(contenido))

        # Verificar resolución mínima
        w, h = img.size
        if w < IMG_MIN_WIDTH or h < IMG_MIN_HEIGHT:
            log.debug(f"Resolución baja ({w}x{h}): {url[:80]}")
            return None

        return img

    except Exception as e:
        log.debug(f"Error descargando {url[:80]}: {e}")
        return None


def procesar_imagen(img: Image.Image, destino: str) -> dict:
    """
    Procesa una imagen: convierte a RGB, redimensiona, optimiza y guarda.

    Args:
        img: imagen PIL
        destino: ruta completa donde guardar (sin extensión, se agrega automáticamente)

    Returns:
        dict con: path, width, height, size_kb, format
    """
    # Convertir a RGB si tiene alpha
    if img.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", img.size, IMG_BACKGROUND)
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Redimensionar manteniendo aspect ratio (fit dentro del target)
    w, h = img.size
    ratio = min(IMG_TARGET_WIDTH / w, IMG_TARGET_HEIGHT / h)
    if ratio < 1:  # Solo reducir, nunca ampliar
        new_w = int(w * ratio)
        new_h = int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    # Guardar en formato web
    ext = IMG_FORMAT.lower()
    if ext == "webp":
        path = f"{destino}.webp"
    elif ext == "jpeg" or ext == "jpg":
        path = f"{destino}.jpg"
        ext = "JPEG"
    else:
        path = f"{destino}.png"
        ext = "PNG"

    # Optimizar calidad para cumplir tamaño máximo
    calidad = IMG_QUALITY
    while calidad >= 40:
        buffer = BytesIO()
        img.save(buffer, format=IMG_FORMAT, quality=calidad, optimize=True)
        size_kb = buffer.tell() / 1024
        if size_kb <= IMG_MAX_FILESIZE_KB:
            break
        calidad -= 5

    # Guardar archivo final
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, format=IMG_FORMAT, quality=calidad, optimize=True)
    final_size = os.path.getsize(path) / 1024

    log.info(f"  Guardada: {os.path.basename(path)} ({img.size[0]}x{img.size[1]}, {final_size:.0f}KB, q={calidad})")

    return {
        "path": path,
        "width": img.size[0],
        "height": img.size[1],
        "size_kb": round(final_size, 1),
        "format": IMG_FORMAT,
    }


# ══════════════════════════════════════════════════════════════════
# PROCESAMIENTO DE ARTÍCULOS
# ══════════════════════════════════════════════════════════════════

def procesar_articulo(codigo: int, descripcion: str, marca: int = 0,
                      color: str = "", max_imagenes: int = 3,
                      carpeta: str = CARPETA_IMAGENES) -> list[dict]:
    """
    Busca, descarga y guarda imágenes para un artículo.

    Args:
        codigo: código del artículo
        descripcion: descripcion_1 del artículo
        marca: código de marca (para mapear nombre de búsqueda)
        color: color del artículo (descripcion_4)
        max_imagenes: cantidad máxima de imágenes a descargar
        carpeta: carpeta base donde guardar

    Returns:
        Lista de dicts con info de cada imagen guardada
    """
    marca_nombre = MARCAS_BUSQUEDA.get(marca, "")

    # Extraer modelo de la descripción (primera palabra suele ser el modelo)
    partes_desc = descripcion.split()
    modelo = partes_desc[0] if partes_desc else ""

    # Determinar tipo de calzado desde la descripción
    desc_upper = descripcion.upper()
    tipo = "zapatilla"
    if "BORCEGO" in desc_upper:
        tipo = "borcego"
    elif "SANDAL" in desc_upper:
        tipo = "sandalia"
    elif "OJOTA" in desc_upper:
        tipo = "ojota"
    elif "BOTA" in desc_upper:
        tipo = "bota"
    elif "ZAPATO" in desc_upper:
        tipo = "zapato"
    elif "CHINELA" in desc_upper:
        tipo = "chinela"

    # Construir queries de búsqueda (probar varias combinaciones)
    queries = []
    if marca_nombre:
        queries.append(construir_query(marca_nombre, modelo, color, tipo))
        queries.append(f"{marca_nombre} {modelo} calzado")
    queries.append(f"{modelo} {color} {tipo}".strip())

    log.info(f"Artículo {codigo}: {descripcion}")
    log.info(f"  Queries: {queries}")

    imagenes_guardadas = []
    urls_probadas = set()

    for query in queries:
        if len(imagenes_guardadas) >= max_imagenes:
            break

        resultados = buscar_imagenes(query, cantidad=MAX_RESULTADOS)
        log.info(f"  Búsqueda '{query}': {len(resultados)} resultados")

        # Ordenar por resolución (mayor primero)
        resultados.sort(key=lambda r: r.get("width", 0) * r.get("height", 0), reverse=True)

        for resultado in resultados:
            if len(imagenes_guardadas) >= max_imagenes:
                break

            url = resultado["url"]
            if not url or url in urls_probadas:
                continue
            urls_probadas.add(url)

            # Descargar y validar
            img = descargar_imagen(url)
            if img is None:
                continue

            # Guardar con naming estándar: {codigo}_{n}.webp
            n = len(imagenes_guardadas) + 1
            destino = os.path.join(carpeta, str(codigo), f"{codigo}_{n}")
            info = procesar_imagen(img, destino)
            info["url_origen"] = url
            info["query"] = query
            imagenes_guardadas.append(info)

            # Pausa entre descargas para no ser bloqueado
            time.sleep(0.5)

        time.sleep(1)  # Pausa entre búsquedas

    if not imagenes_guardadas:
        log.warning(f"  No se encontraron imágenes válidas para artículo {codigo}")
    else:
        log.info(f"  Total: {len(imagenes_guardadas)} imágenes guardadas")

    return imagenes_guardadas


def procesar_lote(articulos: list[dict], carpeta: str = CARPETA_IMAGENES,
                  max_imagenes: int = 3) -> dict:
    """
    Procesa un lote de artículos buscando imágenes para cada uno.

    Args:
        articulos: lista de dicts con keys: codigo, descripcion, marca, color
        carpeta: carpeta base donde guardar
        max_imagenes: imágenes por artículo

    Returns:
        dict con: total, exitosos, fallidos, detalle (lista)
    """
    total = len(articulos)
    exitosos = 0
    fallidos = 0
    detalle = []

    log.info(f"Procesando lote de {total} artículos...")

    for i, art in enumerate(articulos, 1):
        log.info(f"\n[{i}/{total}] ─────────────────────────────────")
        try:
            imagenes = procesar_articulo(
                codigo=art["codigo"],
                descripcion=art.get("descripcion", ""),
                marca=art.get("marca", 0),
                color=art.get("color", ""),
                max_imagenes=max_imagenes,
                carpeta=carpeta,
            )
            if imagenes:
                exitosos += 1
            else:
                fallidos += 1
            detalle.append({
                "codigo": art["codigo"],
                "descripcion": art.get("descripcion", ""),
                "imagenes": imagenes,
                "ok": bool(imagenes),
            })
        except Exception as e:
            log.error(f"Error procesando artículo {art.get('codigo')}: {e}")
            fallidos += 1
            detalle.append({
                "codigo": art.get("codigo"),
                "descripcion": art.get("descripcion", ""),
                "imagenes": [],
                "ok": False,
                "error": str(e),
            })

        # Pausa entre artículos
        time.sleep(2)

    log.info(f"\n{'='*50}")
    log.info(f"RESUMEN: {exitosos}/{total} exitosos, {fallidos} fallidos")

    return {
        "total": total,
        "exitosos": exitosos,
        "fallidos": fallidos,
        "detalle": detalle,
    }


# ══════════════════════════════════════════════════════════════════
# ACTUALIZACIÓN DE BASE DE DATOS
# ══════════════════════════════════════════════════════════════════

def actualizar_db_imagenes(codigo: int, imagenes: list[dict], conn_string: str = None):
    """
    Actualiza los campos link_img2-5 y estado_web del artículo en la base.
    Las rutas se guardan relativas a la carpeta de imágenes del servidor web.

    Args:
        codigo: código del artículo
        imagenes: lista de dicts retornados por procesar_articulo
        conn_string: string de conexión ODBC (usa config.CONN_ARTICULOS si None)
    """
    if not imagenes:
        return

    if conn_string is None:
        from config import CONN_ARTICULOS
        conn_string = CONN_ARTICULOS

    import pyodbc

    # Mapear imágenes a campos link_img2-5
    campos = {}
    for i, img in enumerate(imagenes[:4]):
        campo = f"link_img{i + 2}"  # link_img2, link_img3, link_img4, link_img5
        # Guardar ruta relativa (el servidor web la completará)
        ruta_relativa = f"articulos/{codigo}/{os.path.basename(img['path'])}"
        campos[campo] = ruta_relativa

    if not campos:
        return

    set_clause = ", ".join(f"{k} = ?" for k in campos.keys())
    sql = f"UPDATE msgestion01art.dbo.articulo SET {set_clause}, estado_web = 'V' WHERE codigo = ?"
    params = list(campos.values()) + [codigo]

    try:
        with pyodbc.connect(conn_string, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            log.info(f"  DB actualizada: artículo {codigo}, campos: {list(campos.keys())}")
    except Exception as e:
        log.error(f"  Error actualizando DB para artículo {codigo}: {e}")


# ══════════════════════════════════════════════════════════════════
# UTILIDADES
# ══════════════════════════════════════════════════════════════════

def listar_articulos_sin_imagen(marca: int = None, limit: int = 50) -> list[dict]:
    """
    Consulta artículos activos sin imágenes cargadas.
    Útil para saber qué artículos necesitan fotos.
    """
    from config import CONN_COMPRAS
    import pyodbc

    sql = """
        SELECT a.codigo, a.descripcion_1, a.descripcion_4 as color, a.marca,
               m.descripcion as marca_nombre
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN msgestionC.dbo.marcas m ON a.marca = m.codigo
        WHERE a.estado = 'V'
          AND (a.link_img2 IS NULL OR a.link_img2 = '')
    """
    params = []
    if marca:
        sql += " AND a.marca = ?"
        params.append(marca)

    sql += f" ORDER BY a.codigo DESC OFFSET 0 ROWS FETCH NEXT {limit} ROWS ONLY"

    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [
                {
                    "codigo": r[0],
                    "descripcion": r[1],
                    "color": r[2] or "",
                    "marca": r[3],
                    "marca_nombre": r[4] or "",
                }
                for r in rows
            ]
    except Exception as e:
        log.error(f"Error consultando artículos: {e}")
        return []


def generar_reporte(resultado_lote: dict, archivo: str = None) -> str:
    """
    Genera un reporte legible del resultado del procesamiento de lote.
    """
    lineas = [
        "=" * 60,
        "REPORTE DE BÚSQUEDA DE IMÁGENES",
        "=" * 60,
        f"Total artículos: {resultado_lote['total']}",
        f"Exitosos: {resultado_lote['exitosos']}",
        f"Fallidos: {resultado_lote['fallidos']}",
        "-" * 60,
    ]
    for item in resultado_lote["detalle"]:
        status = "✓" if item["ok"] else "✗"
        lineas.append(f"\n{status} Artículo {item['codigo']}: {item['descripcion']}")
        if item["imagenes"]:
            for img in item["imagenes"]:
                lineas.append(f"    → {img['path']} ({img['width']}x{img['height']}, {img['size_kb']}KB)")
        elif item.get("error"):
            lineas.append(f"    ERROR: {item['error']}")
        else:
            lineas.append(f"    Sin imágenes encontradas")

    lineas.append("\n" + "=" * 60)
    texto = "\n".join(lineas)

    if archivo:
        with open(archivo, "w", encoding="utf-8") as f:
            f.write(texto)
        log.info(f"Reporte guardado en: {archivo}")

    return texto


# ══════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════

def main():
    """
    Uso desde línea de comandos:
        python paso7_buscar_imagenes.py                     → procesa Wake sin imagen
        python paso7_buscar_imagenes.py 360001              → procesa artículo específico
        python paso7_buscar_imagenes.py --marca 746         → todos los Wake sin imagen
        python paso7_buscar_imagenes.py --marca 314         → todos los Topper sin imagen
        python paso7_buscar_imagenes.py --test "Wake WKC215 negro zapatilla"
    """
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python paso7_buscar_imagenes.py <codigo>")
        print("  python paso7_buscar_imagenes.py --marca <codigo_marca>")
        print("  python paso7_buscar_imagenes.py --test <query>")
        print("  python paso7_buscar_imagenes.py --lote-nuevos")
        return

    if sys.argv[1] == "--test":
        # Solo buscar, no descargar
        query = " ".join(sys.argv[2:])
        print(f"\nBuscando: {query}")
        resultados = buscar_imagenes(query)
        for i, r in enumerate(resultados, 1):
            print(f"\n  [{i}] {r['title'][:60]}")
            print(f"      URL: {r['url'][:100]}")
            print(f"      Resolución: {r['width']}x{r['height']}")
            print(f"      Fuente: {r['source']}")
        return

    if sys.argv[1] == "--marca":
        marca = int(sys.argv[2])
        print(f"\nBuscando artículos sin imagen para marca {marca}...")
        articulos = listar_articulos_sin_imagen(marca=marca, limit=20)
        if not articulos:
            print("No se encontraron artículos sin imagen")
            return
        print(f"Encontrados {len(articulos)} artículos sin imagen")
        resultado = procesar_lote(articulos)
        print(generar_reporte(resultado))
        return

    if sys.argv[1] == "--lote-nuevos":
        # Procesar los artículos Wake recién creados (360001-360012)
        from config import CONN_COMPRAS
        import pyodbc
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT codigo, descripcion_1, descripcion_4, marca
                FROM msgestion01art.dbo.articulo
                WHERE codigo BETWEEN 360001 AND 360012
                ORDER BY codigo
            """)
            articulos = [
                {"codigo": r[0], "descripcion": r[1], "color": r[2] or "", "marca": r[3]}
                for r in cursor.fetchall()
            ]
        if articulos:
            # Para artículos del mismo modelo/color, procesar solo uno por color
            colores_vistos = set()
            articulos_unicos = []
            for art in articulos:
                key = (art["descripcion"], art["color"])
                if key not in colores_vistos:
                    colores_vistos.add(key)
                    articulos_unicos.append(art)
            resultado = procesar_lote(articulos_unicos)
            print(generar_reporte(resultado))
        return

    # Artículo específico por código
    try:
        codigo = int(sys.argv[1])
    except ValueError:
        print(f"Código inválido: {sys.argv[1]}")
        return

    from config import CONN_COMPRAS
    import pyodbc
    with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT codigo, descripcion_1, descripcion_4, marca
            FROM msgestion01art.dbo.articulo
            WHERE codigo = ?
        """, codigo)
        row = cursor.fetchone()
        if not row:
            print(f"Artículo {codigo} no encontrado")
            return

    art = {"codigo": row[0], "descripcion": row[1], "color": row[2] or "", "marca": row[3]}
    imagenes = procesar_articulo(**art)
    if imagenes:
        print(f"\n{'='*40}")
        print(f"Imágenes guardadas para artículo {codigo}:")
        for img in imagenes:
            print(f"  → {img['path']}")
            print(f"    {img['width']}x{img['height']}, {img['size_kb']}KB")


if __name__ == "__main__":
    main()
