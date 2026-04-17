"""
Importar imágenes de Google/DDG para productos sin foto.

Pipeline: Buscar en DDG → Descargar → Validar → Procesar (resize/optimize)
         → INSERT en producto_imagenes (PG) → Subir al VPS via SCP → URL pública

USO:
    # Ver productos sin foto
    python3 -m multicanal.importar_imagenes --listar-sin-foto --limit 20

    # Importar foto para un producto específico (dry-run)
    python3 -m multicanal.importar_imagenes --familia 77600841 --dry-run

    # Importar en lote los primeros N sin foto
    python3 -m multicanal.importar_imagenes --lote 10 --dry-run

    # Ejecutar de verdad
    python3 -m multicanal.importar_imagenes --familia 77600841

    # Test: solo buscar en DDG sin descargar
    python3 -m multicanal.importar_imagenes --test "pantufla rosa cerrada mujer"
"""

import argparse
import os
import re
import subprocess
import sys
import time
import tempfile
from io import BytesIO
from pathlib import Path

import psycopg2
import requests
from PIL import Image

from multicanal.imagenes import PG_CONN_STRING, IMAGE_BASE_URL

# ── Config ──
VPS_HOST = "200.58.109.125"
VPS_PORT = 4393
VPS_IMAGE_DIR = "/var/www/imagenes"
VPS_USER = "root"

IMG_MIN_SIZE = 400       # px mínimo ancho o alto
IMG_TARGET_SIZE = 1200   # px máximo
IMG_QUALITY = 85
IMG_FORMAT = "JPEG"
IMG_MAX_KB = 500

TIMEOUT_DESCARGA = 15
TIMEOUT_BUSQUEDA = 10
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Carpeta temporal local para imágenes descargadas
LOCAL_CACHE = os.path.join(os.path.dirname(__file__), '_imagenes_cache')


# ══════════════════════════════════════════════════════════════
# BÚSQUEDA (DDG)
# ══════════════════════════════════════════════════════════════

def buscar_ddg(query: str, cantidad: int = 8) -> list[dict]:
    """Busca imágenes en DuckDuckGo. Retorna lista de {url, width, height, title}."""
    headers = {"User-Agent": USER_AGENT}
    resultados = []

    try:
        # Obtener token vqd
        resp = requests.get("https://duckduckgo.com/",
                            params={"q": query}, headers=headers,
                            timeout=TIMEOUT_BUSQUEDA)
        vqd_match = re.search(r'vqd=["\']([^"\']+)["\']', resp.text)
        if not vqd_match:
            vqd_match = re.search(r'vqd=([\d-]+)', resp.text)
        if not vqd_match:
            print(f"    WARN: No se pudo obtener token DDG")
            return []
        vqd = vqd_match.group(1)

        # Buscar imágenes
        params = {"l": "ar-es", "o": "json", "q": query, "vqd": vqd,
                  "f": ",,,,,", "p": "1", "v7exp": "a"}
        resp = requests.get("https://duckduckgo.com/i.js",
                            params=params, headers=headers,
                            timeout=TIMEOUT_BUSQUEDA)
        data = resp.json()
        for item in data.get("results", [])[:cantidad]:
            url = item.get("image", "")
            if url:
                resultados.append({
                    "url": url,
                    "width": item.get("width", 0),
                    "height": item.get("height", 0),
                    "title": item.get("title", ""),
                    "source": item.get("source", ""),
                })
    except Exception as e:
        print(f"    Error DDG: {e}")

    return resultados


def construir_queries(marca_nombre: str, descripcion: str, color: str = "") -> list[str]:
    """Construye queries de búsqueda optimizadas."""
    desc_upper = descripcion.upper()

    # Detectar tipo
    tipo = "calzado"
    for palabra, t in [("PANTUF", "pantufla"), ("CHINELA", "chinela"),
                       ("SANDAL", "sandalia"), ("BOTA", "bota"),
                       ("BORCEGO", "borcego"), ("ZAPATILLA", "zapatilla"),
                       ("ZAPA ", "zapatilla"), ("OJOTA", "ojota")]:
        if palabra in desc_upper:
            tipo = t
            break

    # Extraer modelo (primer token numérico o alfanumérico)
    tokens = descripcion.split()
    modelo = tokens[0] if tokens else ""

    queries = []
    color_principal = color.split("/")[0].strip() if color else ""

    if marca_nombre:
        if color_principal:
            queries.append(f"{marca_nombre} {modelo} {color_principal} {tipo}")
        queries.append(f"{marca_nombre} {modelo} {tipo}")
    if color_principal:
        queries.append(f"{modelo} {color_principal} {tipo}")
    queries.append(f"{descripcion[:40]} {tipo}")

    return queries


# ══════════════════════════════════════════════════════════════
# DESCARGA Y PROCESAMIENTO
# ══════════════════════════════════════════════════════════════

def descargar_imagen(url: str):
    """Descarga y valida una imagen. Retorna PIL Image o None."""
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=TIMEOUT_DESCARGA, stream=True)
        resp.raise_for_status()

        contenido = b""
        for chunk in resp.iter_content(chunk_size=8192):
            contenido += chunk
            if len(contenido) > 10 * 1024 * 1024:
                return None

        img = Image.open(BytesIO(contenido))
        w, h = img.size
        if w < IMG_MIN_SIZE or h < IMG_MIN_SIZE:
            return None
        return img
    except Exception:
        return None


def procesar_imagen(img: Image.Image) -> bytes:
    """Procesa imagen: RGB, resize, optimize. Retorna bytes JPEG."""
    # Convertir a RGB
    if img.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Resize
    w, h = img.size
    ratio = min(IMG_TARGET_SIZE / w, IMG_TARGET_SIZE / h)
    if ratio < 1:
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    # Optimize quality
    calidad = IMG_QUALITY
    while calidad >= 40:
        buf = BytesIO()
        img.save(buf, format=IMG_FORMAT, quality=calidad, optimize=True)
        if buf.tell() / 1024 <= IMG_MAX_KB:
            return buf.getvalue()
        calidad -= 5

    buf = BytesIO()
    img.save(buf, format=IMG_FORMAT, quality=40, optimize=True)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════
# INSERTAR EN POSTGRESQL
# ══════════════════════════════════════════════════════════════

def insertar_en_pg(conn, producto_base: str, cod_familia: str,
                   nro_imagen: int, ext: str = ".jpg"):
    """INSERT en producto_imagenes. Retorna id o None."""
    path_relativo = f"{producto_base[0]}/{producto_base}"
    archivo_final = f"{producto_base}-{nro_imagen:02d}{ext}"

    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO producto_imagenes
                (cod_familia, producto_base, nro_imagen, path_relativo,
                 archivo_final, estado, ext)
            VALUES (%s, %s, %s, %s, %s, 'activo', %s)
            RETURNING id
        """, (cod_familia, producto_base, nro_imagen, path_relativo,
              archivo_final, ext))
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None
    except Exception as e:
        conn.rollback()
        print(f"    Error INSERT PG: {e}")
        return None


# ══════════════════════════════════════════════════════════════
# SUBIR AL VPS
# ══════════════════════════════════════════════════════════════

def subir_al_vps(imagen_bytes: bytes, path_relativo: str, archivo_final: str) -> bool:
    """Sube imagen al VPS via SCP. Retorna True si OK."""
    destino_dir = f"{VPS_IMAGE_DIR}/{path_relativo}"
    destino_file = f"{destino_dir}/{archivo_final}"

    # Guardar en temp local
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp.write(imagen_bytes)
        tmp_path = tmp.name

    try:
        # Crear directorio en VPS
        subprocess.run(
            ["ssh", "-p", str(VPS_PORT), f"{VPS_USER}@{VPS_HOST}",
             f"mkdir -p {destino_dir}"],
            timeout=10, capture_output=True
        )
        # Copiar archivo
        result = subprocess.run(
            ["scp", "-P", str(VPS_PORT), tmp_path,
             f"{VPS_USER}@{VPS_HOST}:{destino_file}"],
            timeout=30, capture_output=True
        )
        if result.returncode == 0:
            return True
        else:
            print(f"    Error SCP: {result.stderr.decode()[:100]}")
            return False
    except Exception as e:
        print(f"    Error subiendo al VPS: {e}")
        return False
    finally:
        os.unlink(tmp_path)


def guardar_local(imagen_bytes: bytes, path_relativo: str, archivo_final: str) -> str:
    """Guarda imagen en cache local. Retorna path."""
    destino_dir = os.path.join(LOCAL_CACHE, path_relativo)
    os.makedirs(destino_dir, exist_ok=True)
    destino = os.path.join(destino_dir, archivo_final)
    with open(destino, 'wb') as f:
        f.write(imagen_bytes)
    return destino


# ══════════════════════════════════════════════════════════════
# LISTAR PRODUCTOS SIN FOTO
# ══════════════════════════════════════════════════════════════

def listar_sin_foto(limit=20):
    """Lista productos activos en PG que no tienen imagen."""
    conn = psycopg2.connect(PG_CONN_STRING)
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.familia_id, p.nombre, p.nombre_mg, p.estado,
               m.nombre as marca
        FROM productos p
        LEFT JOIN prod_marcas m ON p.marca_id = m.id
        WHERE p.activo = true
        AND p.imagen_principal IS NULL
        AND NOT EXISTS (
            SELECT 1 FROM producto_imagenes pi
            WHERE pi.cod_familia = p.familia_id AND pi.estado = 'activo'
        )
        ORDER BY p.id
        LIMIT %s
    """, (limit,))
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return rows


def contar_sin_foto():
    """Cuenta productos sin foto."""
    conn = psycopg2.connect(PG_CONN_STRING)
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM productos p
        WHERE p.activo = true
        AND p.imagen_principal IS NULL
        AND NOT EXISTS (
            SELECT 1 FROM producto_imagenes pi
            WHERE pi.cod_familia = p.familia_id AND pi.estado = 'activo'
        )
    """)
    count = cur.fetchone()[0]
    conn.close()
    return count


# ══════════════════════════════════════════════════════════════
# IMPORTAR: PIPELINE COMPLETO
# ══════════════════════════════════════════════════════════════

def importar_para_familia(familia_id: str, dry_run=True, max_imagenes=2):
    """
    Pipeline completo para una familia de productos:
    1. Busca datos del producto en PG
    2. Construye query de búsqueda
    3. Busca en DDG
    4. Descarga la mejor imagen
    5. Procesa (resize, optimize)
    6. INSERT en producto_imagenes (PG)
    7. Sube al VPS (o guarda local si no hay SSH)
    """
    print(f"\n  Familia: {familia_id}")

    # 1. Datos del producto
    conn = psycopg2.connect(PG_CONN_STRING)
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.nombre, p.nombre_mg, p.familia_id,
               m.nombre as marca
        FROM productos p
        LEFT JOIN prod_marcas m ON p.marca_id = m.id
        WHERE p.familia_id = %s
        LIMIT 1
    """, (familia_id,))
    row = cur.fetchone()
    if not row:
        print(f"    Producto no encontrado en PG para familia {familia_id}")
        conn.close()
        return {'ok': False, 'error': 'not_found'}

    pg_id, nombre, nombre_mg, fam_id, marca = row
    desc = nombre_mg or nombre or ''
    marca_nombre = marca or ''

    # Extraer color del nombre_mg
    color = ""
    if nombre_mg:
        parts = nombre_mg.split()
        if len(parts) >= 2:
            # Segundo token suele ser el color
            possible_color = parts[1] if not parts[1].isdigit() else (parts[2] if len(parts) > 2 else "")
            if possible_color.upper() not in ('PANTUFLA', 'ZAPATILLA', 'SANDALIA', 'BOTA', 'CHINELA'):
                color = possible_color

    print(f"    Producto: {desc}")
    print(f"    Marca: {marca_nombre} | Color: {color}")

    # Verificar si ya tiene imagen (a nivel producto_base, no familia)
    # Una familia puede tener imagenes de un color pero no de otro

    # 2. Buscar variantes para obtener producto_base
    cur.execute("""
        SELECT DISTINCT LEFT(pv.codigo_sinonimo, 10) as producto_base
        FROM producto_variantes pv
        WHERE pv.producto_id = %s
        AND pv.codigo_sinonimo IS NOT NULL
        LIMIT 5
    """, (pg_id,))
    producto_bases = [r[0] for r in cur.fetchall() if r[0]]

    if not producto_bases:
        print(f"    Sin codigo_sinonimo, no se puede generar naming")
        conn.close()
        return {'ok': False, 'error': 'no_sku'}

    # Filtrar producto_bases que ya tienen imagen
    producto_bases_sin_foto = []
    for pb in producto_bases:
        cur.execute("""
            SELECT COUNT(*) FROM producto_imagenes
            WHERE producto_base = %s AND estado = 'activo'
        """, (pb,))
        if cur.fetchone()[0] == 0:
            producto_bases_sin_foto.append(pb)

    if not producto_bases_sin_foto:
        print(f"    Todos los colores ya tienen imagen, skip")
        conn.close()
        return {'ok': True, 'skipped': True}

    producto_bases = producto_bases_sin_foto
    print(f"    Producto bases sin foto: {producto_bases[:3]}")

    # 3. Construir queries y buscar
    queries = construir_queries(marca_nombre, desc, color)
    print(f"    Queries: {queries[:2]}")

    imagenes_importadas = []

    for query in queries:
        if len(imagenes_importadas) >= max_imagenes:
            break

        resultados = buscar_ddg(query)
        print(f"    DDG '{query[:40]}': {len(resultados)} resultados")

        # Ordenar por resolución
        resultados.sort(key=lambda r: r.get("width", 0) * r.get("height", 0), reverse=True)

        for res in resultados:
            if len(imagenes_importadas) >= max_imagenes:
                break

            url = res['url']
            print(f"    Probando: {url[:70]}...")

            if dry_run:
                imagenes_importadas.append({
                    'url': url,
                    'width': res.get('width', 0),
                    'height': res.get('height', 0),
                    'dry_run': True,
                })
                print(f"    [DRY RUN] Se descargaría {res.get('width')}x{res.get('height')}")
                break

            # 4. Descargar
            img = descargar_imagen(url)
            if not img:
                continue

            # 5. Procesar
            img_bytes = procesar_imagen(img)
            size_kb = len(img_bytes) / 1024
            print(f"    Descargada: {img.size[0]}x{img.size[1]} → {size_kb:.0f}KB")

            # 6. INSERT en PG para CADA producto_base (cada color)
            nro = len(imagenes_importadas) + 1
            pb = producto_bases[0]  # Primer producto_base
            path_relativo = f"{pb[0]}/{pb}"
            archivo_final = f"{pb}-{nro:02d}.jpg"

            pg_img_id = insertar_en_pg(conn, pb, familia_id, nro)
            if pg_img_id:
                print(f"    INSERT PG OK (id={pg_img_id})")
            else:
                print(f"    INSERT PG FALLÓ")

            # 7. Subir al VPS o guardar local
            ok_vps = subir_al_vps(img_bytes, path_relativo, archivo_final)
            if ok_vps:
                url_publica = f"{IMAGE_BASE_URL}/{path_relativo}/{archivo_final}"
                print(f"    VPS OK: {url_publica}")
            else:
                local_path = guardar_local(img_bytes, path_relativo, archivo_final)
                url_publica = f"(local) {local_path}"
                print(f"    VPS falló, guardado local: {local_path}")

            imagenes_importadas.append({
                'url_origen': url,
                'producto_base': pb,
                'archivo': archivo_final,
                'url_publica': url_publica if ok_vps else None,
                'local_path': local_path if not ok_vps else None,
                'pg_id': pg_img_id,
                'size_kb': size_kb,
            })
            time.sleep(0.5)
            break  # Una imagen buena por query es suficiente

        time.sleep(1)

    conn.close()

    return {
        'ok': len(imagenes_importadas) > 0,
        'familia_id': familia_id,
        'descripcion': desc,
        'imagenes': imagenes_importadas,
    }


def importar_lote(limit=10, dry_run=True):
    """Importa imágenes para los primeros N productos sin foto."""
    print(f"\n{'='*60}")
    print(f"  IMPORTAR IMÁGENES EN LOTE {'[DRY RUN]' if dry_run else '[REAL]'}")
    print(f"  Límite: {limit} productos")
    print(f"{'='*60}")

    sin_foto = listar_sin_foto(limit=limit)
    print(f"\n  {len(sin_foto)} productos sin foto encontrados\n")

    exitosos = 0
    fallidos = 0
    skipped = 0

    for i, prod in enumerate(sin_foto, 1):
        print(f"\n[{i}/{len(sin_foto)}] {'─'*40}")
        resultado = importar_para_familia(prod['familia_id'], dry_run=dry_run)
        if resultado.get('skipped'):
            skipped += 1
        elif resultado.get('ok'):
            exitosos += 1
        else:
            fallidos += 1
        time.sleep(2)

    print(f"\n{'='*60}")
    print(f"  RESUMEN: {exitosos} importados, {skipped} skip, {fallidos} fallidos")
    print(f"{'='*60}")


# ══════════════════════════════════════════════════════════════
# SUBIR CACHE LOCAL AL VPS (batch)
# ══════════════════════════════════════════════════════════════

def subir_cache_al_vps():
    """Sube todas las imágenes del cache local al VPS via SCP."""
    if not os.path.exists(LOCAL_CACHE):
        print("No hay cache local")
        return

    archivos = list(Path(LOCAL_CACHE).rglob("*.jpg"))
    print(f"Subiendo {len(archivos)} imágenes al VPS...")

    ok = 0
    for f in archivos:
        rel = str(f.relative_to(LOCAL_CACHE))
        path_parts = rel.rsplit('/', 1)
        if len(path_parts) == 2:
            path_rel, archivo = path_parts
        else:
            continue

        with open(f, 'rb') as fh:
            if subir_al_vps(fh.read(), path_rel, archivo):
                ok += 1
                print(f"  OK: {rel}")
            else:
                print(f"  FAIL: {rel}")

    print(f"\nSubidos: {ok}/{len(archivos)}")


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Importar imágenes de Google/DDG')
    parser.add_argument('--listar-sin-foto', action='store_true', help='Listar productos sin imagen')
    parser.add_argument('--familia', help='Familia ID (8 chars) a importar')
    parser.add_argument('--lote', type=int, help='Importar N productos sin foto')
    parser.add_argument('--test', help='Solo buscar en DDG (query)')
    parser.add_argument('--subir-cache', action='store_true', help='Subir cache local al VPS')
    parser.add_argument('--dry-run', action='store_true', help='Preview sin descargar/insertar')
    parser.add_argument('--limit', type=int, default=20, help='Límite para listar-sin-foto')
    args = parser.parse_args()

    if args.test:
        print(f"\nBuscando: {args.test}")
        resultados = buscar_ddg(args.test)
        for i, r in enumerate(resultados, 1):
            print(f"\n  [{i}] {r['title'][:60]}")
            print(f"      URL: {r['url'][:100]}")
            print(f"      {r['width']}x{r['height']} | {r['source']}")

    elif args.listar_sin_foto:
        total = contar_sin_foto()
        print(f"\nTotal productos sin foto: {total:,}\n")
        productos = listar_sin_foto(limit=args.limit)
        for p in productos:
            print(f"  {p['familia_id']:10s} | {p.get('marca') or '':20s} | {(p.get('nombre_mg') or p.get('nombre') or ''):50s}")

    elif args.familia:
        print(f"\n{'='*60}")
        print(f"  IMPORTAR IMAGEN {'[DRY RUN]' if args.dry_run else '[REAL]'}")
        print(f"{'='*60}")
        importar_para_familia(args.familia, dry_run=args.dry_run)

    elif args.lote:
        importar_lote(limit=args.lote, dry_run=args.dry_run)

    elif args.subir_cache:
        subir_cache_al_vps()

    else:
        parser.print_help()
