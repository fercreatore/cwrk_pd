#!/usr/bin/env python3
# app_carga.py — Interfaz web para operadores (Streamlit)
#
# FLUJO AUTOMÁTICO:
#   1. Subir PDF/imagen de factura
#   2. OCR extrae texto automáticamente
#   3. Detecta proveedor por CUIT (busca en DB)
#   4. Parsea artículos, precios, cantidades
#   5. Auto-completa todo → listo para procesar
#
# EJECUTAR:
#   streamlit run app_carga.py
#
# INSTALAR (una sola vez):
#   pip install streamlit pyodbc Pillow PyMuPDF

import os
import sys
import json
import io
import logging
from datetime import date, datetime

import streamlit as st
from PIL import Image

log = logging.getLogger("app_carga")

# Soporte HEIC (iPhone)
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_SUPPORT = True
except ImportError:
    HEIC_SUPPORT = False

# Agregar directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

# ── Cache de conexión DB ──
@st.cache_resource
def _get_db_connection():
    """Conexión persistente a SQL Server."""
    import pyodbc
    from config import CONN_ARTICULOS
    try:
        return pyodbc.connect(CONN_ARTICULOS, timeout=10)
    except Exception as e:
        log.error(f"Error conectando a DB: {e}")
        return None

# ── Imports del proyecto ──
from config import PROVEEDORES, calcular_precios

# OCR de facturas
try:
    from ocr_factura import parsear_pdf_factura, parsear_factura_archivo, FacturaOCR
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False

# Parseo de Excel/CSV (notas de pedido)
try:
    from paso5_parsear_excel import parsear_nota, leer_archivo, normalizar_columnas, limpiar_datos
    EXCEL_DISPONIBLE = True
except ImportError:
    EXCEL_DISPONIBLE = False

# Proveedores dinámicos desde DB
try:
    from proveedores_db import (
        buscar_proveedor_por_cuit,
        buscar_proveedor_por_nombre,
        obtener_pricing_proveedor,
        obtener_marcas_proveedor,
        auto_detectar_proveedor_factura,
        listar_proveedores_con_fantasia,
        detectar_proveedor_por_texto,
    )
    PROVEEDORES_DB_DISPONIBLE = True
except ImportError:
    PROVEEDORES_DB_DISPONIBLE = False

# Carga de facturas
try:
    from paso8_carga_factura import (
        Factura, LineaFactura, procesar_factura, parsear_factura_wake,
        guardar_factura_json, detectar_marca, obtener_color_code,
        construir_sinonimo, buscar_articulo_por_sinonimo,
        COLORES_CONOCIDOS, PREFIJO_MARCA,
    )
    CARGA_DISPONIBLE = True
except ImportError:
    CARGA_DISPONIBLE = False


# ══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN STREAMLIT
# ══════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Carga de Facturas — H4/Calzalindo",
    page_icon="👟",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estado de sesión
defaults = {
    "factura_data": None,
    "resultado": None,
    "articulos_lista": [],
    "modo": "carga",
    "prov_detectado": None,      # proveedor auto-detectado
    "factura_ocr": None,         # resultado del OCR
    "auto_procesado": False,     # flag para evitar re-procesar
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ══════════════════════════════════════════════════════════════════

def _procesar_imagen_producto(img_bytes, agregar_logo=True, es_catalogo=True):
    """
    Procesa una imagen de producto para el ERP:
    1. Limpia fondo → blanco
    2. Quita badge 'ARTICULO XX' y textos decorativos (si es catálogo)
    3. Cuadra a 1200x1200
    4. Agrega logo Calzalindo arriba a la derecha

    Retorna bytes PNG de la imagen procesada.
    """
    import numpy as np

    FINAL_SIZE = 1200
    original = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = original.size
    arr = np.array(original, dtype=np.float32)

    if es_catalogo:
        # Crop: zona central donde está el calzado (30%-92% vertical, 5%-95% horizontal)
        y_top = int(h * 0.30)
        y_bot = int(h * 0.92)
        x_left = int(w * 0.05)
        x_right = int(w * 0.95)
        cropped_arr = arr[y_top:y_bot, x_left:x_right, :]
    else:
        cropped_arr = arr

    # Detectar color de fondo desde los bordes
    borde = max(20, int(min(cropped_arr.shape[:2]) * 0.02))
    bordes_px = np.concatenate([
        cropped_arr[:borde, :, :].reshape(-1, 3),
        cropped_arr[-borde:, :, :].reshape(-1, 3),
        cropped_arr[:, :borde, :].reshape(-1, 3),
        cropped_arr[:, -borde:, :].reshape(-1, 3),
    ])
    bg_color = np.median(bordes_px, axis=0)

    # Reemplazar fondo por blanco
    dist = np.sqrt(np.sum((cropped_arr - bg_color) ** 2, axis=2))
    brillo = np.mean(cropped_arr, axis=2)
    fondo = (dist < 40) | (brillo > 230)

    # Detectar piel (tonos cálidos) y limpiar
    r, g, b = cropped_arr[:, :, 0], cropped_arr[:, :, 1], cropped_arr[:, :, 2]
    es_piel = (r > 150) & (r > g) & (g > b) & ((r - b) > 30)
    mascara = fondo | es_piel

    result = cropped_arr.copy()
    result[mascara] = [255, 255, 255]

    if es_catalogo:
        # Limpiar zona inferior (piso, textos decorativos)
        ch = result.shape[0]
        result[int(ch * 0.85):, :] = [255, 255, 255]

    img_clean = Image.fromarray(result.astype(np.uint8))

    # Auto-crop contenido
    gray = np.mean(result, axis=2)
    mask = gray < 248
    rows_mask = np.any(mask, axis=1)
    cols_mask = np.any(mask, axis=0)

    if rows_mask.any() and cols_mask.any():
        rmin, rmax = np.where(rows_mask)[0][[0, -1]]
        cmin, cmax = np.where(cols_mask)[0][[0, -1]]
        pad = int(min(result.shape[1], result.shape[0]) * 0.04)
        rmin = max(0, rmin - pad)
        rmax = min(result.shape[0], rmax + pad)
        cmin = max(0, cmin - pad)
        cmax = min(result.shape[1], cmax + pad)
        cropped_final = img_clean.crop((cmin, rmin, cmax, rmax))
    else:
        cropped_final = img_clean

    # Cuadrado con fondo blanco
    canvas = Image.new("RGB", (FINAL_SIZE, FINAL_SIZE), (255, 255, 255))
    cw, ch = cropped_final.size
    margen = int(FINAL_SIZE * 0.06)
    area = FINAL_SIZE - 2 * margen
    ratio = min(area / cw, area / ch)
    new_w = int(cw * ratio)
    new_h = int(ch * ratio)
    resized = cropped_final.resize((new_w, new_h), Image.LANCZOS)
    x = (FINAL_SIZE - new_w) // 2
    y = (FINAL_SIZE - new_h) // 2
    canvas.paste(resized, (x, y))

    # Logo arriba a la derecha
    if agregar_logo:
        logo_path = os.path.join(
            os.path.dirname(__file__),
            "logos", "logo calczalindo web fotos recorte.png"
        )
        if os.path.exists(logo_path):
            logo_img = Image.open(logo_path).convert("RGBA")
            logo_w = int(FINAL_SIZE * 0.28)
            lr = logo_w / logo_img.width
            logo_h = int(logo_img.height * lr)
            logo_r = logo_img.resize((logo_w, logo_h), Image.LANCZOS)
            lm = int(FINAL_SIZE * 0.02)
            canvas_rgba = canvas.convert("RGBA")
            canvas_rgba.paste(logo_r, (FINAL_SIZE - logo_w - lm, lm), logo_r)
            canvas = canvas_rgba.convert("RGB")

    buf = io.BytesIO()
    canvas.save(buf, format="PNG", quality=95)
    return buf.getvalue()


def _vincular_foto_articulos(articulos_bd, foto_bytes, extension):
    """
    Vincula una foto a artículos existentes en el ERP:
    1. Obtiene el nombre de archivo vía f_sql_nombre_imagen()
    2. Copia la foto a F:\\Macroges\\Imagenes\\ (vía SMB)
    3. INSERT en tabla imagen

    articulos_bd: lista de dicts con 'codigo' (PK del artículo)
    foto_bytes: bytes de la imagen
    extension: 'jpg', 'png', etc.
    """
    import pyodbc
    from config import get_conn_string

    # Ruta SMB a la carpeta de imágenes del 111
    IMG_SMB_PATH = "/Volumes/macroges_imagenes"
    IMG_SMB_URL = "//administrador:cagr$2011@192.168.2.111/Macroges/Imagenes"
    IMG_WIN_PATH = r"F:\Macroges\Imagenes"

    resultados = {"ok": 0, "error": 0, "errores": []}

    try:
        # Conectar a la BD de producción (111)
        conn = pyodbc.connect(get_conn_string("msgestion01"), timeout=10)
        cursor = conn.cursor()

        for art in articulos_bd:
            codigo = art["codigo"]
            try:
                # 1. Verificar si ya tiene imagen
                cursor.execute(
                    "SELECT COUNT(*) FROM imagen WHERE tipo='AR' AND empresa=1 "
                    "AND sistema=0 AND codigo=0 AND numero=? AND renglon=1",
                    codigo
                )
                ya_existe = cursor.fetchone()[0] > 0

                # 2. Obtener nombre de archivo con la función de Macroges
                cursor.execute(
                    "SELECT dbo.f_sql_nombre_imagen(1,'AR',0,0,'',0,?,0,1,?) AS nombre",
                    codigo, extension
                )
                row = cursor.fetchone()
                if not row or not row.nombre:
                    resultados["error"] += 1
                    resultados["errores"].append(f"Cód {codigo}: f_sql_nombre_imagen devolvió NULL")
                    continue

                nombre_completo = row.nombre  # ej: \\DELL-SVR\Macroges\Imagenes\0001AR...png
                # Extraer solo el nombre del archivo
                nombre_archivo = nombre_completo.split("\\")[-1]

                # 3. Copiar foto al server
                import platform
                if platform.system() == "Windows":
                    import socket
                    import subprocess as _sp
                    hostname = socket.gethostname().upper()
                    if hostname in ("DELL-SVR", "DELLSVR"):
                        # En el propio server 111 — ruta local
                        ruta_destino = f"{IMG_WIN_PATH}\\{nombre_archivo}"
                    else:
                        # En otro Windows (ej: .112) — ruta UNC al 111
                        unc_share = "\\\\192.168.2.111\\Macroges"
                        # Mapear share con credenciales si no está conectado
                        try:
                            _sp.run(
                                ["net", "use", unc_share,
                                 "/user:administrador", "cagr$2011"],
                                capture_output=True, timeout=10,
                            )
                        except Exception:
                            pass  # ya conectado o error no fatal
                        ruta_destino = f"{unc_share}\\Imagenes\\{nombre_archivo}"
                    with open(ruta_destino, "wb") as f:
                        f.write(foto_bytes)
                else:
                    # Mac — usar SMB mount
                    import subprocess
                    if not os.path.ismount(IMG_SMB_PATH):
                        os.makedirs(IMG_SMB_PATH, exist_ok=True)
                        subprocess.run(
                            ["mount_smbfs", IMG_SMB_URL, IMG_SMB_PATH],
                            check=True, timeout=10
                        )
                    ruta_destino = f"{IMG_SMB_PATH}/{nombre_archivo}"
                    with open(ruta_destino, "wb") as f:
                        f.write(foto_bytes)

                # 4. INSERT en tabla imagen (si no existía)
                if not ya_existe:
                    cursor.execute(
                        "INSERT INTO imagen (empresa, tipo, sistema, codigo, letra, "
                        "sucursal, numero, orden, renglon, extencion) "
                        "VALUES (1, 'AR', 0, 0, '', 0, ?, 0, 1, ?)",
                        codigo, extension
                    )
                    conn.commit()

                resultados["ok"] += 1

            except Exception as e:
                resultados["error"] += 1
                resultados["errores"].append(f"Cód {codigo}: {e}")

        conn.close()

    except Exception as e:
        st.error(f"Error conectando a BD: {e}")
        return

    # Mostrar resultado
    if resultados["ok"] > 0:
        st.success(f"✅ Foto vinculada a {resultados['ok']} artículo(s)")
    if resultados["error"] > 0:
        st.error(f"❌ {resultados['error']} error(es):")
        for err in resultados["errores"]:
            st.caption(err)


def _buscar_articulos_proveedor(prov_id, modelos):
    """
    Busca en la BD si ya existen artículos del proveedor que coincidan
    con los modelos/referencias del Excel.

    El modelo puede ser ej "742" (3 dígitos) pero en el sinónimo (5 chars)
    aparece con padding de ceros: "74200", "07420", "00742".
    Busca todas las variantes.

    Retorna dict {modelo: [{codigo, sinonimo, desc1, color, talle}]}
    """
    if not prov_id:
        return {}
    try:
        import pyodbc
        from config import CONN_ARTICULOS
        conn = pyodbc.connect(CONN_ARTICULOS, timeout=10)
        cursor = conn.cursor()

        resultados = {}
        for modelo in modelos:
            modelo_str = str(modelo).strip()
            if not modelo_str or modelo_str == "SIN_MODELO":
                continue

            # Generar variantes de padding para sinónimo (5 chars)
            patterns = set()
            patterns.add(f"%{modelo_str}%")  # búsqueda amplia

            if modelo_str.isdigit() and len(modelo_str) < 5:
                # Padding derecha: 742 → 74200
                patterns.add(f"%{modelo_str.ljust(5, '0')}%")
                # Padding izquierda: 742 → 00742
                patterns.add(f"%{modelo_str.zfill(5)}%")
                # Padding centrado: 742 → 07420
                total_pad = 5 - len(modelo_str)
                left_pad = total_pad // 2
                centro = '0' * left_pad + modelo_str + '0' * (total_pad - left_pad)
                patterns.add(f"%{centro}%")

            # Construir condición OR dinámica
            conditions = " OR ".join(["a.codigo_sinonimo LIKE ?"] * len(patterns))
            conditions += " OR a.descripcion_1 LIKE ?"

            sql = f"""
                SELECT a.codigo, RTRIM(a.codigo_sinonimo) as sinonimo,
                       RTRIM(a.descripcion_1) as desc1,
                       RTRIM(ISNULL(a.descripcion_4,'')) as color,
                       RTRIM(ISNULL(a.descripcion_5,'')) as talle
                FROM msgestion01art.dbo.articulo a
                WHERE a.proveedor = ? AND a.estado = 'V'
                  AND ({conditions})
                ORDER BY a.codigo DESC
            """
            params = [prov_id] + list(patterns) + [f"%{modelo_str}%"]
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            if rows:
                # Deduplicar por código
                seen = set()
                unique = []
                for r in rows:
                    if r.codigo not in seen:
                        seen.add(r.codigo)
                        unique.append({
                            "codigo": r.codigo, "sinonimo": r.sinonimo,
                            "desc1": r.desc1, "color": r.color, "talle": r.talle,
                        })
                resultados[modelo_str] = unique

        conn.close()
        return resultados
    except Exception as e:
        log.error(f"Error buscando artículos proveedor {prov_id}: {e}")
        return {}


def _detectar_proveedor_auto(factura_ocr):
    """
    Detecta proveedor automáticamente desde los datos del OCR.
    Primero intenta por CUIT en DB, luego por nombre, luego config estática.
    """
    prov = None

    # 1. Buscar en DB por CUIT
    if PROVEEDORES_DB_DISPONIBLE and factura_ocr.cuit_proveedor:
        prov = buscar_proveedor_por_cuit(factura_ocr.cuit_proveedor)
        if prov:
            prov["_fuente"] = "DB (CUIT)"
            return prov

    # 2. Buscar en DB por nombre del proveedor detectado
    if PROVEEDORES_DB_DISPONIBLE and factura_ocr.proveedor:
        prov = buscar_proveedor_por_nombre(factura_ocr.proveedor)
        if prov:
            prov["_fuente"] = "DB (nombre)"
            return prov

    # 3. Buscar por texto libre (razón social completa del OCR)
    if PROVEEDORES_DB_DISPONIBLE and factura_ocr.proveedor:
        prov = detectar_proveedor_por_texto(factura_ocr.proveedor)
        if prov:
            prov["_fuente"] = "DB (texto)"
            return prov

    # 4. Fallback: buscar en config estática por CUIT
    if factura_ocr.cuit_proveedor:
        for pid, pcfg in PROVEEDORES.items():
            if pcfg.get("cuit", "").replace("-", "") == factura_ocr.cuit_proveedor:
                prov = dict(pcfg)
                prov["numero"] = pid
                prov["_fuente"] = "config.py"
                return prov

    return None


def _agrupar_lineas_ocr(lineas):
    """Agrupa líneas OCR por modelo+color → artículos con curva de talles."""
    grupos = {}
    for l in lineas:
        key = f"{l.codigo_producto}|{l.color}"
        if key not in grupos:
            grupos[key] = {
                "modelo": l.codigo_producto,
                "variante": "",
                "color": l.color,
                "talles": [],
                "curva": [],
                "precio_unitario": l.precio_unitario,
                "descuento_comercial": l.descuento,
                "codigo_barra": l.codigo_barra,
            }
        grupos[key]["talles"].append(l.talle)
        grupos[key]["curva"].append(l.cantidad)
        if len(l.descripcion) > len(grupos[key].get("variante", "")):
            grupos[key]["variante"] = l.descripcion
    return list(grupos.values())


def _procesar_archivo_auto(file_bytes, filename):
    """
    Proceso completo automático:
    1. OCR del archivo (PDF/imagen) o parseo Excel/CSV
    2. Detectar proveedor
    3. Agrupar artículos
    4. Guardar todo en session_state
    """
    nombre = filename.lower()

    # ── EXCEL / CSV ──────────────────────────────────────────
    if nombre.endswith((".xlsx", ".xls", ".csv")):
        return _procesar_excel_auto(file_bytes, filename)

    # ── PDF / IMAGEN (OCR) ───────────────────────────────────
    if nombre.endswith(".pdf"):
        factura_ocr = parsear_pdf_factura(file_bytes)
    else:
        factura_ocr = parsear_factura_archivo(file_bytes, filename)

    st.session_state["factura_ocr"] = factura_ocr

    # 2. Detectar proveedor
    prov = _detectar_proveedor_auto(factura_ocr)
    st.session_state["prov_detectado"] = prov

    # 3. Agrupar artículos
    if factura_ocr.lineas:
        st.session_state.articulos_lista = _agrupar_lineas_ocr(factura_ocr.lineas)
    else:
        st.session_state.articulos_lista = []

    st.session_state["auto_procesado"] = True
    return factura_ocr, prov


def _procesar_excel_auto(file_bytes, filename):
    """
    Parsea un Excel/CSV de nota de pedido y lo convierte al formato articulos_lista.

    Soporta DOS formatos:

    FORMATO HORIZONTAL (el más común en pedidos):
      ARTICULO | COLOR | 36 | 37 | 38 | 39 | 40 | TOTAL
      1336     | NEGRO |  2 |  2 |  4 |  4 |  4 |   16

    FORMATO VERTICAL (una fila por talle):
      modelo | color | talle | cantidad | precio
      1336   | NEGRO | 38    | 4        | 22000
    """
    import tempfile
    import pandas as pd

    # Guardar en temp para leerlo
    suffix = "." + filename.rsplit(".", 1)[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        # Leer SIN header para detectar formato
        if tmp_path.lower().endswith((".xlsx", ".xls")):
            df_raw = pd.read_excel(tmp_path, header=None)
        else:
            df_raw = pd.read_csv(tmp_path, sep=None, engine="python",
                                 encoding="utf-8-sig", header=None)
    except Exception as e:
        st.error(f"Error leyendo archivo: {e}")
        return None, None
    finally:
        os.unlink(tmp_path)

    if df_raw is None or len(df_raw) == 0:
        st.warning("El archivo no tiene datos")
        return None, None

    # ── DETECTAR FORMATO ──────────────────────────────────────
    # Buscar la fila header: la que contiene "ARTICULO" o "COLOR"
    # y columnas numéricas que parecen talles (22-45)
    formato = "desconocido"
    header_row = None
    col_articulo = None
    col_color = None
    cols_talles = {}   # {col_index: talle_num}
    col_total = None
    col_precio = None

    for idx, row in df_raw.iterrows():
        vals = [str(v).strip().upper() for v in row.values]
        # Buscar fila que tenga ARTICULO o ART o MODELO
        for ci, v in enumerate(vals):
            if v in ("ARTICULO", "ART", "MODELO", "REFERENCIA", "REF", "COD", "CODIGO"):
                header_row = idx
                col_articulo = ci
                break
        if header_row is not None:
            # Buscar COLOR en la misma fila
            for ci, v in enumerate(vals):
                if v == "COLOR":
                    col_color = ci
                elif v in ("TOTAL", "TOTALES", "TOT"):
                    col_total = ci
                elif v in ("PRECIO", "P.UNIT", "PRECIO UNIT", "COSTO"):
                    col_precio = ci
                else:
                    # Verificar si es un número de talle (22-45)
                    try:
                        num = int(float(v))
                        if 18 <= num <= 48:
                            cols_talles[ci] = num
                    except (ValueError, TypeError):
                        pass
            break

    if header_row is not None and len(cols_talles) >= 2:
        formato = "horizontal"
    else:
        formato = "vertical"

    st.session_state["excel_formato"] = formato

    # ── FORMATO HORIZONTAL ────────────────────────────────────
    if formato == "horizontal":
        articulos = []
        # Procesar filas de datos (después del header)
        ultimo_articulo = None
        for idx in range(header_row + 1, len(df_raw)):
            row = df_raw.iloc[idx]

            # Leer artículo (puede estar vacío si es continuación del anterior)
            art_val = row.iloc[col_articulo] if col_articulo is not None else None
            if pd.notna(art_val) and str(art_val).strip():
                ultimo_articulo = str(art_val).strip()
                # Limpiar .0 de floats leídos como número
                if ultimo_articulo.endswith(".0"):
                    ultimo_articulo = ultimo_articulo[:-2]

            # Leer color
            color_val = ""
            if col_color is not None:
                cv = row.iloc[col_color]
                if pd.notna(cv) and str(cv).strip():
                    color_val = str(cv).strip().upper()

            # Si no hay color, saltar (fila vacía o fila resumen)
            if not color_val:
                continue

            # Leer curva de talles
            talles = []
            curva = []
            for ci, talle_num in sorted(cols_talles.items(), key=lambda x: x[1]):
                cant_val = row.iloc[ci]
                try:
                    cant = int(float(cant_val))
                    if cant > 0:
                        talles.append(str(talle_num))
                        curva.append(cant)
                except (ValueError, TypeError):
                    pass

            if not talles:
                continue  # fila sin cantidades

            # Precio
            precio = 0
            if col_precio is not None:
                try:
                    precio = float(row.iloc[col_precio])
                except (ValueError, TypeError):
                    pass

            articulos.append({
                "modelo": ultimo_articulo or "SIN_MODELO",
                "variante": "",
                "color": color_val or "SIN_COLOR",
                "talles": talles,
                "curva": curva,
                "precio_unitario": precio,
                "descuento_comercial": 0,
                "codigo_barra": "",
            })

        st.session_state["articulos_lista"] = articulos
        st.session_state["factura_ocr"] = None
        st.session_state["auto_procesado"] = True
        st.session_state["excel_df"] = df_raw
        st.session_state["excel_filename"] = filename
        st.session_state["prov_detectado"] = None
        return None, None

    # ── FORMATO VERTICAL (legado) ─────────────────────────────
    # Usar df_raw con la primera fila como header
    df = df_raw.copy()
    df.columns = [str(c).strip() for c in df.iloc[0]]
    df = df.iloc[1:].reset_index(drop=True)

    df = normalizar_columnas(df)
    df = limpiar_datos(df)

    if df is None or len(df) == 0:
        st.warning("El Excel no tiene datos válidos")
        return None, None

    st.session_state["excel_df"] = df
    st.session_state["excel_filename"] = filename

    # Detectar columnas
    tiene_modelo = "codigo_articulo" in df.columns
    tiene_desc = "descripcion" in df.columns
    tiene_color = any(c in df.columns for c in ["color", "descripcion_4"])
    tiene_talle = any(c in df.columns for c in ["talle", "descripcion_5"])
    tiene_precio = "precio" in df.columns
    tiene_cantidad = "cantidad" in df.columns
    tiene_sinonimo = "codigo_sinonimo" in df.columns

    if "descripcion_4" in df.columns and "color" not in df.columns:
        df["color"] = df["descripcion_4"]
    if "descripcion_5" in df.columns and "talle" not in df.columns:
        df["talle"] = df["descripcion_5"]

    if tiene_modelo:
        df["modelo"] = df["codigo_articulo"].astype(str).str.strip()
    elif tiene_desc:
        df["modelo"] = df["descripcion"].astype(str).str.split().str[0]
    elif tiene_sinonimo:
        df["modelo"] = df["codigo_sinonimo"].astype(str).str.strip()
    else:
        df["modelo"] = "SIN_MODELO"

    if not tiene_color:
        df["color"] = df["descripcion"].astype(str).str.split().str[1:].str.join(" ") if tiene_desc else "SIN_COLOR"
    df["color"] = df["color"].astype(str).str.strip().str.upper()

    if not tiene_talle:
        df["talle"] = "UNICO"
    df["talle"] = df["talle"].astype(str).str.strip()

    if not tiene_precio:
        df["precio"] = 0
    if not tiene_cantidad:
        df["cantidad"] = 1

    articulos = []
    for (modelo, color), grupo in df.groupby(["modelo", "color"], sort=False):
        talles = grupo["talle"].tolist()
        curva = grupo["cantidad"].astype(int).tolist()
        precio = grupo["precio"].iloc[0] if tiene_precio else 0
        desc = max(grupo["descripcion"].astype(str).tolist(), key=len) if tiene_desc else ""
        dcto = grupo["descuento"].iloc[0] if "descuento" in grupo.columns else 0
        barra = str(grupo["codigo_barra"].iloc[0]) if "codigo_barra" in grupo.columns else ""

        articulos.append({
            "modelo": str(modelo).strip(),
            "variante": desc,
            "color": str(color).strip(),
            "talles": talles,
            "curva": curva,
            "precio_unitario": float(precio),
            "descuento_comercial": float(dcto),
            "codigo_barra": barra,
        })

    st.session_state["articulos_lista"] = articulos
    st.session_state["factura_ocr"] = None
    st.session_state["auto_procesado"] = True

    prov = None
    if "proveedor" in df.columns:
        prov_txt = str(df["proveedor"].iloc[0]).strip()
        if PROVEEDORES_DB_DISPONIBLE:
            prov = buscar_proveedor_por_nombre(prov_txt)
    # Si no detectó por columna, intentar por nombre de archivo
    if not prov and PROVEEDORES_DB_DISPONIBLE and filename:
        prov = detectar_proveedor_por_texto(filename)
        if prov:
            prov["_fuente"] = "nombre archivo"
    st.session_state["prov_detectado"] = prov

    return None, prov


# ══════════════════════════════════════════════════════════════════
# CLASIFICACIÓN AUTOMÁTICA (rubro/subrubro/grupo/linea)
# ══════════════════════════════════════════════════════════════════

# Tablas de lookup (codigo → descripcion)
RUBROS = {1: "DAMAS", 3: "HOMBRES", 4: "NIÑOS", 5: "NIÑAS", 6: "UNISEX"}
SUBRUBROS = {
    1: "ALPARGATAS", 2: "BORCEGOS", 5: "CHATA", 6: "CHINELA", 7: "MOCASINES",
    10: "ACC. DEPORTIVOS", 11: "OJOTAS", 12: "SANDALIAS", 13: "ZUECOS",
    15: "BOTAS", 17: "GUILLERMINA", 18: "CARTERAS", 19: "BOTINES TAPON",
    20: "ZAPATO DE VESTIR", 21: "CASUAL", 25: "MOCHILAS", 26: "BILLETERAS",
    27: "PLANTILLAS", 29: "MEDIAS", 30: "BOLSOS", 33: "PELOTAS",
    35: "PANCHA", 37: "FRANCISCANA", 40: "NAUTICO", 45: "BOTINES PISTA",
    46: "CAMPERAS", 47: "ZAPATILLA RUNNING", 48: "ZAPATILLA TENNIS",
    49: "ZAPATILLA TRAINING", 50: "ZAPATILLA BASKET", 51: "ZAPATILLA OUTDOOR",
    52: "ZAPATILLA CASUAL", 53: "ZAPATILLA SKATER", 55: "ZAPATILLA SNEAKERS",
    56: "FIESTA", 58: "CINTOS", 60: "PANTUFLA", 64: "ZAPATO DE TRABAJO",
    65: "BOTA DE LLUVIA", 68: "VALIJAS", 71: "RIÑONERA",
}
GRUPOS_MAT = {
    1: "CUERO", 2: "LONA", 4: "GAMUZA", 5: "PU", 6: "PECARI", 8: "JEAN",
    9: "TOALLA", 11: "P.V.C.", 13: "POLAR", 17: "TELA", 18: "GABARDINA",
    19: "PAÑO", 33: "CORDEROY", 34: "MICROFIBRA", 36: "PELUCHE",
    39: "GOMA EVA", 41: "LYCRA", 42: "NEOPRENE",
}
LINEAS = {1: "VERANO", 2: "INVIERNO", 3: "PRETEMPORADA", 4: "ATEMPORAL", 5: "COLEGIAL", 6: "SEGURIDAD"}

# Keywords para detectar subrubro desde texto del catálogo/descripción
_KEYWORDS_SUBRUBRO = {
    15: ["BOTA ", "BOTAS", "BOTITA", "BOTA CAÑA"],
    2:  ["BORCEGO", "BORCEGI"],
    19: ["BOTIN ", "BOTINES", "BOTINETA"],
    12: ["SANDALIA", "SAND "],
    11: ["OJOTA"],
    6:  ["CHINELA"],
    13: ["ZUECO"],
    17: ["GUILLERMINA", "GUILLE "],
    37: ["FRANCISCANA"],
    35: ["PANCHA"],
    7:  ["MOCASIN", "MOCASÍN"],
    40: ["NAUTICO", "NÁUTICO"],
    5:  ["CHATA", "CHATITA"],
    20: ["ZAPATO", "STILETTO"],
    56: ["FIESTA"],
    52: ["ZAPATILLA CASUAL", "ZAPA CASUAL", "ZAPA URB", "SNEAKER"],
    55: ["SNEAKERS", "SNEAKER"],
    47: ["RUNNING", "ZAPA DEP"],
    49: ["TRAINING", "ZAPA TRAIN"],
    50: ["BASKET"],
    60: ["PANTUFLA"],
    65: ["LLUVIA", "RAIN"],
    1:  ["ALPARGATA"],
    71: ["RIÑONERA", "RINONERA"],
    18: ["CARTERA"],
    25: ["MOCHILA"],
    30: ["BOLSO"],
    68: ["VALIJA"],
    21: ["TEXANA"],  # texanas → casual
}

# Keywords para detectar grupo (material) desde texto del catálogo
_KEYWORDS_GRUPO = {
    1:  ["CUERO VACUNO", "CUERO ", " CUERO"],
    4:  ["GAMUZA", "GAMUZ"],
    5:  ["PU ", " PU", "SINTETICO", "SINTÉTICO"],
    2:  ["LONA"],
    17: ["TELA"],
    34: ["MICROFIBRA", "ECOGAMUZA"],
    42: ["NEOPRENE"],
    11: ["PVC", "P.V.C"],
}


@st.cache_data(ttl=600)
def _obtener_historial_proveedor(prov_id):
    """
    Consulta el historial de clasificación del proveedor en la BD.
    Retorna el patrón más frecuente de rubro, subrubro, grupo, linea.
    """
    if not prov_id:
        return {}
    try:
        import pyodbc
        from config import CONN_ARTICULOS
        conn = pyodbc.connect(CONN_ARTICULOS, timeout=10)
        cursor = conn.cursor()

        # Distribución de clasificación para este proveedor
        cursor.execute("""
            SELECT rubro, subrubro, grupo, linea, COUNT(*) as cant
            FROM msgestionC.dbo.articulo
            WHERE proveedor = ? AND estado = 'V'
              AND rubro IS NOT NULL AND subrubro IS NOT NULL
            GROUP BY rubro, subrubro, grupo, linea
            ORDER BY cant DESC
        """, prov_id)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {}

        # Calcular el default más frecuente por cada campo
        from collections import Counter
        rubros_cnt = Counter()
        subrubros_cnt = Counter()
        grupos_cnt = Counter()
        lineas_cnt = Counter()
        combos = []

        for r in rows:
            rubros_cnt[r.rubro] += r.cant
            subrubros_cnt[r.subrubro] += r.cant
            if r.grupo:
                grupos_cnt[str(r.grupo).strip()] += r.cant
            if r.linea:
                lineas_cnt[r.linea] += r.cant
            combos.append({
                "rubro": r.rubro, "subrubro": r.subrubro,
                "grupo": str(r.grupo).strip() if r.grupo else "",
                "linea": r.linea, "cant": r.cant,
            })

        return {
            "default_rubro": rubros_cnt.most_common(1)[0][0] if rubros_cnt else 1,
            "default_subrubro": subrubros_cnt.most_common(1)[0][0] if subrubros_cnt else 52,
            "default_grupo": grupos_cnt.most_common(1)[0][0] if grupos_cnt else "5",
            "default_linea": lineas_cnt.most_common(1)[0][0] if lineas_cnt else 4,
            "rubros": dict(rubros_cnt.most_common(10)),
            "subrubros": dict(subrubros_cnt.most_common(15)),
            "grupos": dict(grupos_cnt.most_common(10)),
            "lineas": dict(lineas_cnt.most_common(6)),
            "combos": combos[:20],
            "total": sum(r.cant for r in rows),
        }
    except Exception as e:
        log.error(f"Error historial proveedor {prov_id}: {e}")
        return {}


def _clasificar_articulo(texto_pdf, nombre_catalogo, historial_prov):
    """
    Clasifica un artículo usando:
    1. Keywords del texto extraído del PDF (material, tipo de calzado)
    2. Nombre del catálogo (ej: 'BOTAS', 'TEXANAS')
    3. Historial del proveedor como fallback

    Retorna dict con rubro, subrubro, grupo, linea + descripción sugerida.
    """
    texto = (texto_pdf + " " + nombre_catalogo).upper()

    # --- Subrubro (tipo de calzado) ---
    subrubro = historial_prov.get("default_subrubro", 52)
    subrubro_nombre = SUBRUBROS.get(subrubro, "?")
    for sr_cod, keywords in _KEYWORDS_SUBRUBRO.items():
        if any(kw in texto for kw in keywords):
            subrubro = sr_cod
            subrubro_nombre = SUBRUBROS.get(sr_cod, "?")
            break

    # --- Grupo (material) ---
    grupo = historial_prov.get("default_grupo", "5")
    grupo_nombre = GRUPOS_MAT.get(int(grupo) if grupo.isdigit() else 0, "?")
    for gr_cod, keywords in _KEYWORDS_GRUPO.items():
        if any(kw in texto for kw in keywords):
            grupo = str(gr_cod)
            grupo_nombre = GRUPOS_MAT.get(gr_cod, "?")
            break

    # --- Rubro (género) — default del proveedor ---
    rubro = historial_prov.get("default_rubro", 1)
    # Override si hay pistas en el texto
    if any(kw in texto for kw in ["HOMBRE", "CABALLERO", " HOM "]):
        rubro = 3
    elif any(kw in texto for kw in ["NIÑO", "KIDS", "INFANTIL"]):
        rubro = 4
    elif any(kw in texto for kw in ["NIÑA"]):
        rubro = 5
    elif any(kw in texto for kw in ["UNISEX"]):
        rubro = 6
    rubro_nombre = RUBROS.get(rubro, "?")

    # --- Linea (temporada) — inferir del tipo ---
    linea = historial_prov.get("default_linea", 4)
    # Botas/borcegos → invierno, sandalias/ojotas → verano
    if subrubro in (15, 2, 19, 60, 65):
        linea = 2  # INVIERNO
    elif subrubro in (12, 11, 6):
        linea = 1  # VERANO
    # Si el catálogo dice OTÑ/INV → invierno
    if any(kw in texto for kw in ["OTOÑO", "OTÑO", "INVIERNO", "OTÑ"]):
        linea = 2
    elif any(kw in texto for kw in ["VERANO", "PRIMAVERA"]):
        linea = 1
    linea_nombre = LINEAS.get(linea, "?")

    # --- Color — detectar del texto del PDF ---
    _COLORES = [
        "NEGRO/CHAROL", "BLANCO/CHAROL", "NEGRO/BLANCO", "BLANCO/NEGRO",
        "NEGRO/COBRE", "BLANCO/PLATA", "BLANCO/SUELA", "GRIS/NEGRO",
        "NUDE/CH", "BEIGE/CH", "NEGRO/CH",
        "NEGRO", "BLANCO", "COBRE", "GRIS", "PLATA", "ROSA", "SUELA",
        "CAMEL", "NUDE", "VERDE", "CHOCOLATE", "MULTICOLOR", "NATURAL",
        "ORO", "ROJO", "AZUL", "BEIGE", "MARRON", "BORDO", "CELESTE",
        "FUCSIA", "LILA", "NARANJA", "SALMON", "CREMA", "HUESO",
        "MENTA", "TOPO", "TAUPE", "ARENA", "CENIZA", "CAFE",
    ]
    color_detectado = ""
    for c in _COLORES:
        if c in texto:
            color_detectado = c
            break

    # --- Descripción sugerida ---
    # Formato: COLOR TIPO MATERIAL (ej: "NEGRO BOTAS PU")
    desc_tipo = subrubro_nombre
    if subrubro == 21 and "TEXANA" in texto:
        desc_tipo = "TEXANA"
    desc_mat = grupo_nombre
    partes_desc = [p for p in [color_detectado, desc_tipo, desc_mat] if p]
    desc = " ".join(partes_desc)

    return {
        "rubro": rubro, "rubro_nombre": rubro_nombre,
        "subrubro": subrubro, "subrubro_nombre": subrubro_nombre,
        "grupo": grupo, "grupo_nombre": grupo_nombre,
        "linea": linea, "linea_nombre": linea_nombre,
        "color": color_detectado,
        "descripcion_sugerida": desc.strip(),
    }


# ══════════════════════════════════════════════════════════════════
# SIDEBAR — INFO PROVEEDOR (dinámico)
# ══════════════════════════════════════════════════════════════════

st.sidebar.title("⚙️ Configuración")

# Si hay proveedor auto-detectado, mostrarlo
prov_detectado = st.session_state.get("prov_detectado")
if prov_detectado:
    st.sidebar.success(f"🎯 Proveedor detectado: **{prov_detectado.get('nombre', '?')}**")
    st.sidebar.markdown(f"""
**Nro:** {prov_detectado.get('numero', '?')}
**CUIT:** {prov_detectado.get('cuit', '?')}
**Fuente:** {prov_detectado.get('_fuente', '?')}
**Marca:** {prov_detectado.get('marca', '?')}
**Descuento:** {prov_detectado.get('descuento', 0)}%
**Utilidades:** {prov_detectado.get('utilidad_1', 0)}% / {prov_detectado.get('utilidad_2', 0)}% / {prov_detectado.get('utilidad_3', 0)}% / {prov_detectado.get('utilidad_4', 0)}%
""")
    prov_id = prov_detectado.get("numero", 0)
    prov_nombre = prov_detectado.get("nombre", "")
    prov_config = prov_detectado
    marca_default = prov_detectado.get("marca", 0)
else:
    # Selector manual — todos los proveedores de la BD (con nombre_fantasia)
    @st.cache_data(ttl=300)
    def _cargar_proveedores_bd():
        """Carga todos los proveedores activos de la BD con nombre_fantasia (cache 5 min)."""
        try:
            provs = listar_proveedores_con_fantasia()
            # Armar opciones con label amigable que incluye nombre_fantasia
            # Ej: "Juana Va — 55.COM (Grupo) [892]" o "ALPARGATAS S.A.I.C. [1500]"
            opciones = {}
            for num, p in provs.items():
                fantasia = p.get("fantasia", "").strip()
                nombre = p.get("nombre", "").strip()
                cant = p.get("cant_articulos", 0)
                # Label: fantasia primero si existe (es lo que busca el usuario)
                if fantasia and len(fantasia) >= 3:
                    label = f"{fantasia} — {nombre} [{cant}]"
                else:
                    label = f"{nombre} [{cant}]"
                opciones[label] = num
            return opciones, provs
        except Exception as e:
            import logging
            logging.getLogger("app_carga").error(f"Error cargando proveedores BD: {e}")
            return {}, {}

    opciones_prov, provs_data = _cargar_proveedores_bd()

    if opciones_prov:
        prov_label = st.sidebar.selectbox(
            "Proveedor",
            sorted(opciones_prov.keys()),
            index=0,
            help=f"Escribí para buscar — {len(opciones_prov)} proveedores disponibles",
        )
        prov_id = opciones_prov[prov_label]
    else:
        # Fallback ultra-mínimo si la BD no conecta
        proveedores_lista = {v["nombre"]: k for k, v in PROVEEDORES.items()}
        prov_nombre_fb = st.sidebar.selectbox("Proveedor (config)", sorted(proveedores_lista.keys()))
        prov_id = proveedores_lista[prov_nombre_fb]

    # Obtener datos del proveedor seleccionado
    prov_info = provs_data.get(prov_id, {})
    prov_nombre = prov_info.get("nombre", "")

    # Pricing: primero config.py (overrides manuales), luego BD
    prov_config = PROVEEDORES.get(prov_id)
    if not prov_config:
        pricing = obtener_pricing_proveedor(prov_id)
        prov_config = {"nombre": prov_nombre, **pricing}
    marca_default = prov_config.get("marca", 0)

    # Mostrar info del proveedor
    st.sidebar.markdown(f"""
**Nro:** {prov_id}
**CUIT:** {prov_info.get('cuit', '?')}
**Cond. IVA:** {prov_info.get('condicion_iva', '?')}
**Zona:** {prov_info.get('zona', '?')}
**Artículos:** {prov_info.get('cant_articulos', 0)}
""")
    st.sidebar.markdown(f"""
**Marca:** {prov_config.get('marca', '?')}
**Descuento:** {prov_config.get('descuento', 0)}%
**Utilidades:** {prov_config.get('utilidad_1', 0)}% / {prov_config.get('utilidad_2', 0)}% / {prov_config.get('utilidad_3', 0)}% / {prov_config.get('utilidad_4', 0)}%
""")

# Campo para codigo_objeto_costo (5 chars) — solo relevante para artículos nuevos
st.sidebar.text_input(
    "Cód. Objeto Costo (5 letras, ej: LIP26)",
    value=st.session_state.get("codigo_objeto_costo", ""),
    max_chars=5,
    key="codigo_objeto_costo",
    help="Solo para artículos NUEVOS. Si existe en DB se auto-detecta.",
)

st.sidebar.divider()

# Tipo de comprobante (auto-detectado si hay OCR)
factura_ocr = st.session_state.get("factura_ocr")
tipo_default = 0
nro_default = ""
fecha_default = date.today()

if factura_ocr:
    if factura_ocr.tipo_comprobante == "FA":
        tipo_default = 0
    nro_default = factura_ocr.numero or ""
    if factura_ocr.fecha:
        try:
            # Intentar parsear DD/MM/YYYY
            parts = factura_ocr.fecha.split("/")
            if len(parts) == 3:
                fecha_default = date(int(parts[2]), int(parts[1]), int(parts[0]))
        except (ValueError, IndexError):
            pass

tipo_comp = st.sidebar.radio(
    "Tipo de comprobante",
    ["Factura (FC)", "Remito (RM)", "Nota de Pedido (NP)"],
    index=tipo_default,
)
tipo_code = {"Factura (FC)": "FC", "Remito (RM)": "RM", "Nota de Pedido (NP)": "NP"}[tipo_comp]

nro_factura = st.sidebar.text_input("Nro. Factura/Remito", nro_default)
fecha_factura = st.sidebar.date_input("Fecha", fecha_default)

st.sidebar.divider()
modo_test = st.sidebar.checkbox("🔒 Modo TEST (no inserta en DB)", value=True)


# ══════════════════════════════════════════════════════════════════
# FUNCIONES DE PROCESAMIENTO (definidas antes de usarse)
# ══════════════════════════════════════════════════════════════════

def _verificar_articulos(prov_id, marca_id):
    """Verifica si los artículos existen en la base."""
    if not CARGA_DISPONIBLE:
        st.error("Módulo paso8_carga_factura no disponible")
        return

    with st.spinner("Verificando artículos..."):
        resultados = []
        for art in st.session_state.articulos_lista:
            # codigo_objeto_costo del usuario (si lo ingresó) o auto-detectar
            cod_obj = st.session_state.get("codigo_objeto_costo", "")
            for talle in art["talles"]:
                color_code = obtener_color_code(art["color"], art["modelo"])
                sinonimo = construir_sinonimo(
                    art["modelo"], color_code, str(talle), marca_id,
                    codigo_objeto_costo=cod_obj,
                    descripcion=art.get("variante", art.get("modelo", "")),
                    color=art["color"],
                    proveedor=prov_id,
                )
                try:
                    existente = buscar_articulo_por_sinonimo(sinonimo)
                    resultados.append({
                        "modelo": art["modelo"], "color": art["color"],
                        "talle": talle, "sinonimo": sinonimo,
                        "existe": existente is not None,
                        "codigo": existente["codigo"] if existente else None,
                    })
                except Exception as e:
                    resultados.append({
                        "modelo": art["modelo"], "color": art["color"],
                        "talle": talle, "sinonimo": sinonimo,
                        "existe": None, "error": str(e),
                    })

        existentes = sum(1 for r in resultados if r.get("existe"))
        nuevos = sum(1 for r in resultados if r.get("existe") is False)
        errores = sum(1 for r in resultados if r.get("existe") is None)
        st.success(f"Verificación: {existentes} existentes, {nuevos} nuevos, {errores} errores")

        for r in resultados:
            if r.get("existe"):
                st.markdown(f"📦 {r['modelo']} {r['color']} T:{r['talle']} → **{r['sinonimo']}** = código {r['codigo']}")
            elif r.get("existe") is False:
                st.markdown(f"🆕 {r['modelo']} {r['color']} T:{r['talle']} → **{r['sinonimo']}** = NUEVO")
            else:
                st.markdown(f"❌ {r['modelo']} {r['color']} T:{r['talle']} → Error: {r.get('error')}")


def _procesar(prov_id, prov_nombre, marca_id, nro_factura, fecha, tipo, modo_test):
    """Procesa la factura (con o sin inserción)."""
    if not CARGA_DISPONIBLE:
        st.error("Módulo paso8_carga_factura no disponible")
        return

    datos = {
        "proveedor_id": prov_id,
        "proveedor_nombre": prov_nombre,
        "marca_id": marca_id,
        "numero_factura": nro_factura,
        "fecha": fecha.isoformat() if isinstance(fecha, date) else fecha,
        "tipo": tipo,
        "articulos": st.session_state.articulos_lista,
    }

    factura = parsear_factura_wake(datos)

    if modo_test:
        st.info("🧪 MODO TEST — simulación sin inserción")
        resultado = {
            "exitosos": len(factura.lineas), "fallidos": 0,
            "articulos_creados": 0, "articulos_existentes": 0,
            "lineas_procesadas": [], "errores": [], "modo_test": True,
        }
        cod_obj = st.session_state.get("codigo_objeto_costo", "")
        for linea in factura.lineas:
            color_code = obtener_color_code(linea.color, linea.modelo)
            sinonimo = construir_sinonimo(
                linea.modelo, color_code, linea.talle, marca_id,
                codigo_objeto_costo=cod_obj,
                descripcion=linea.descripcion_1 or linea.descripcion,
                color=linea.color,
                proveedor=prov_id,
            )
            try:
                existente = buscar_articulo_por_sinonimo(sinonimo)
                if existente:
                    resultado["articulos_existentes"] += 1
                    linea.codigo_articulo = existente["codigo"]
                    linea.articulo_existente = True
                else:
                    resultado["articulos_creados"] += 1
                    linea.articulo_creado = True
                    linea.codigo_articulo = 0
            except Exception:
                resultado["articulos_creados"] += 1
                linea.articulo_creado = True

            from dataclasses import asdict
            resultado["lineas_procesadas"].append(asdict(linea))

        st.session_state.resultado = resultado
        st.success("✅ Simulación completada — ver pestaña 'Resultado'")
    else:
        with st.spinner("Procesando factura..."):
            resultado = procesar_factura(factura)
            path = guardar_factura_json(factura, resultado)
            st.session_state.resultado = resultado
            st.success(f"✅ Completado — JSON: {path}")

    st.rerun()


# ══════════════════════════════════════════════════════════════════
# MAIN — CARGA AUTOMÁTICA
# ══════════════════════════════════════════════════════════════════

st.title("📋 Carga de Comprobantes — H4/Calzalindo")

tab_carga, tab_fotos, tab_resultado = st.tabs(["📦 Carga de Artículos", "📸 Fotos de Productos", "📊 Resultado"])

with tab_carga:
    # ── Upload de comprobante ──
    st.subheader("1. Subir Comprobante")
    img_factura = st.file_uploader(
        "Arrastrá o seleccioná: PDF/imagen (OCR) o Excel/CSV (nota de pedido)",
        type=["jpg", "jpeg", "png", "heic", "pdf", "xlsx", "xls", "csv"],
        key="img_factura",
    )

    if img_factura:
        nombre = img_factura.name.lower()
        img_bytes = img_factura.read()
        img_factura.seek(0)
        es_excel = nombre.endswith((".xlsx", ".xls", ".csv"))

        # ── Preview ──
        col_preview, col_info = st.columns([2, 1])

        with col_preview:
            if es_excel:
                # Preview tabla Excel
                st.markdown(f"📊 **{img_factura.name}** ({len(img_bytes)//1024} KB)")
                if st.session_state.get("auto_procesado") and "excel_df" in st.session_state:
                    df_preview = st.session_state["excel_df"]
                    formato_det = st.session_state.get("excel_formato", "?")
                    st.caption(f"Formato detectado: **{formato_det}** — talles van {'en columnas ↔' if formato_det == 'horizontal' else 'en filas ↕'}")
                    st.dataframe(df_preview.head(30), use_container_width=True, height=400)
            elif nombre.endswith(".pdf"):
                try:
                    import fitz
                    pdf_doc = fitz.open(stream=img_bytes, filetype="pdf")
                    page = pdf_doc[0]
                    pix = page.get_pixmap(dpi=150)
                    img_data = pix.tobytes("png")
                    st.image(img_data, caption=f"{img_factura.name} (pág 1/{len(pdf_doc)})", use_container_width=True)
                    pdf_doc.close()
                except ImportError:
                    st.info(f"📄 PDF: **{img_factura.name}** ({len(img_bytes)//1024} KB)")
                except Exception:
                    st.info(f"📄 PDF: **{img_factura.name}** ({len(img_bytes)//1024} KB)")

            elif nombre.endswith((".heic", ".heif")):
                if HEIC_SUPPORT:
                    try:
                        pil_img = Image.open(io.BytesIO(img_bytes))
                        st.image(pil_img, caption="Factura", use_container_width=True)
                    except Exception as e:
                        st.warning(f"No se pudo abrir HEIC: {e}")
                else:
                    st.warning("Formato HEIC no soportado. Instalar: `pip install pillow-heif`")
            else:
                try:
                    st.image(img_bytes, caption="Factura", use_container_width=True)
                except Exception:
                    pass

        # ── PROCESAMIENTO AUTOMÁTICO al subir archivo ──
        if not st.session_state.get("auto_procesado"):
            with col_info:
                if es_excel and EXCEL_DISPONIBLE:
                    with st.spinner("📊 Leyendo Excel..."):
                        try:
                            _, prov = _procesar_archivo_auto(img_bytes, img_factura.name)
                            arts = st.session_state.articulos_lista
                            total_pares = sum(sum(a["curva"]) for a in arts) if arts else 0

                            if prov:
                                st.success(f"✅ Proveedor: **{prov.get('nombre', '?')}**")
                            if arts:
                                st.success(
                                    f"✅ {len(arts)} artículos detectados\n\n"
                                    f"**{total_pares} pares**"
                                )
                            else:
                                st.warning("No se detectaron artículos. Verificá las columnas del Excel.")
                                if "excel_df" in st.session_state:
                                    st.markdown(f"Columnas: `{list(st.session_state['excel_df'].columns)}`")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error leyendo Excel: {e}")
                            import traceback
                            st.text(traceback.format_exc())

                elif es_excel and not EXCEL_DISPONIBLE:
                    st.error("Módulo paso5_parsear_excel no disponible")

                elif OCR_DISPONIBLE:
                    with st.spinner("🤖 Leyendo factura automáticamente..."):
                        try:
                            factura_ocr, prov = _procesar_archivo_auto(img_bytes, img_factura.name)

                            if prov:
                                st.success(f"✅ Proveedor: **{prov.get('nombre', '?')}**")
                            else:
                                st.warning("⚠️ Proveedor no detectado")

                            if factura_ocr and factura_ocr.lineas:
                                arts = st.session_state.articulos_lista
                                total_pares = sum(sum(a["curva"]) for a in arts)
                                st.success(
                                    f"✅ {len(factura_ocr.lineas)} items → {len(arts)} artículos\n\n"
                                    f"**{factura_ocr.tipo_comprobante} {factura_ocr.letra} {factura_ocr.numero}**\n\n"
                                    f"Fecha: {factura_ocr.fecha}\n\n"
                                    f"Total: **${factura_ocr.total:,.0f}**\n\n"
                                    f"Pares: {total_pares}"
                                )
                            else:
                                st.warning("No se extrajeron artículos")
                                if factura_ocr:
                                    with st.expander("Texto extraído (debug)"):
                                        st.text(factura_ocr.texto_crudo[:3000])

                            st.rerun()
                        except Exception as e:
                            st.error(f"Error OCR: {e}")
                            import traceback
                            st.text(traceback.format_exc())
                else:
                    st.info("Instalar PyMuPDF para OCR: `pip install PyMuPDF`")

        # ── Botón para re-procesar si ya se procesó ──
        if st.session_state.get("auto_procesado"):
            with col_info:
                factura_ocr = st.session_state.get("factura_ocr")
                if factura_ocr:
                    st.markdown(f"""
**Factura:** {factura_ocr.tipo_comprobante} {factura_ocr.letra} {factura_ocr.numero}
**Fecha:** {factura_ocr.fecha}
**Subtotal:** ${factura_ocr.subtotal:,.0f}
**IVA:** ${factura_ocr.iva:,.0f}
**Total:** ${factura_ocr.total:,.0f}
""")
                    if prov_detectado:
                        st.markdown(f"**Proveedor:** {prov_detectado.get('nombre', '?')} (#{prov_detectado.get('numero', '?')})")

                elif es_excel:
                    # Info para Excel
                    arts = st.session_state.articulos_lista
                    total_pares = sum(sum(a["curva"]) for a in arts) if arts else 0
                    total_monto = sum(sum(a["curva"]) * a["precio_unitario"] for a in arts) if arts else 0
                    st.markdown(f"""
**Archivo:** {st.session_state.get('excel_filename', '?')}
**Artículos:** {len(arts)}
**Total pares:** {total_pares}
**Total $:** ${total_monto:,.0f}
""")
                    if prov_detectado:
                        st.markdown(f"**Proveedor:** {prov_detectado.get('nombre', '?')} (#{prov_detectado.get('numero', '?')})")

                if st.button("🔄 Re-procesar"):
                    st.session_state["auto_procesado"] = False
                    st.session_state["prov_detectado"] = None
                    for k in ["excel_df", "arts_existentes_bd", "excel_formato"]:
                        st.session_state.pop(k, None)
                    st.rerun()

    st.divider()

    # ── Artículos extraídos ──
    st.subheader("2. Artículos Detectados")

    if st.session_state.articulos_lista:
        total_pares = 0
        total_monto = 0

        # Verificación automática contra BD si hay proveedor seleccionado
        arts_existentes = st.session_state.get("arts_existentes_bd", {})
        if not arts_existentes and prov_id:
            modelos = list(set(a["modelo"] for a in st.session_state.articulos_lista))
            arts_existentes = _buscar_articulos_proveedor(prov_id, modelos)
            st.session_state["arts_existentes_bd"] = arts_existentes

        for i, art in enumerate(st.session_state.articulos_lista):
            pares = sum(art["curva"])
            monto = pares * art["precio_unitario"]
            total_pares += pares
            total_monto += monto

            # Estado en BD
            modelo_key = str(art["modelo"]).strip()
            en_bd = arts_existentes.get(modelo_key, [])
            if en_bd:
                badge = f"📦 {len(en_bd)} en BD"
            else:
                badge = "🆕 NUEVO"

            col_art, col_del = st.columns([5, 1])
            with col_art:
                dcto_txt = f" | Bonif: {art['descuento_comercial']}%" if art.get('descuento_comercial', 0) > 0 else ""
                curva_txt = " | ".join(f"T{t}:{c}" for t, c in zip(art['talles'], art['curva']))
                st.markdown(
                    f"**{i+1}.** {badge} — `{art['modelo']}` "
                    f"**{art['color']}** — "
                    f"{curva_txt} "
                    f"({pares} pares)"
                    f"{dcto_txt}"
                )
                if en_bd:
                    with st.expander(f"Ver {len(en_bd)} artículos existentes del modelo {modelo_key}"):
                        for ab in en_bd[:20]:
                            st.caption(f"Cód: {ab['codigo']} | {ab['desc1']} | {ab['color']} T{ab['talle']} | Sin: {ab['sinonimo']}")
            with col_del:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.articulos_lista.pop(i)
                    if "arts_existentes_bd" in st.session_state:
                        del st.session_state["arts_existentes_bd"]
                    st.rerun()

        st.divider()
        col_tot1, col_tot2, col_tot3 = st.columns(3)
        with col_tot1:
            st.metric("Artículos", len(st.session_state.articulos_lista))
        with col_tot2:
            st.metric("Total Pares", total_pares)
        with col_tot3:
            st.metric("Total $", f"${total_monto:,.0f}")

        # Previsualización de precios con config del proveedor
        if prov_config and art.get("precio_unitario", 0) > 0:
            with st.expander("💰 Previsualización de Precios"):
                precio_fab = float(st.session_state.articulos_lista[0]["precio_unitario"])
                descuento = float(prov_config.get("descuento", 0))
                # Bonificación de factura → descuento_1
                bonif_factura = float(st.session_state.articulos_lista[0].get("descuento_comercial", 0))
                precio_costo = round(precio_fab * (1 - descuento / 100) * (1 - bonif_factura / 100), 2)

                cp1, cp2, cp3, cp4, cp5 = st.columns(5)
                with cp1:
                    st.metric("P. Fábrica", f"${precio_fab:,.0f}")
                with cp2:
                    desc_label = f"-{descuento:.0f}%"
                    if bonif_factura > 0:
                        desc_label += f" / Bonif -{bonif_factura:.0f}%"
                    st.metric("P. Costo", f"${precio_costo:,.0f}", delta=desc_label)
                with cp3:
                    u1 = float(prov_config.get("utilidad_1", 80))
                    st.metric("Contado (P1)", f"${precio_costo * (1 + u1/100):,.0f}")
                with cp4:
                    u2 = float(prov_config.get("utilidad_2", 100))
                    st.metric("Lista (P2)", f"${precio_costo * (1 + u2/100):,.0f}")
                with cp5:
                    u4 = float(prov_config.get("utilidad_4", 45))
                    st.metric("Mayorista (P4)", f"${precio_costo * (1 + u4/100):,.0f}")

        st.divider()

        # ── Botones de acción ──
        col_btn1, col_btn2, col_btn3 = st.columns(3)

        with col_btn1:
            if CARGA_DISPONIBLE and st.button("🔍 Verificar Artículos", use_container_width=True, type="secondary"):
                _verificar_articulos(prov_id, marca_default)

        with col_btn2:
            btn_label = "🧪 PROCESAR (TEST)" if modo_test else "🚀 PROCESAR E INSERTAR"
            btn_type = "secondary" if modo_test else "primary"
            if CARGA_DISPONIBLE and st.button(btn_label, use_container_width=True, type=btn_type):
                _procesar(prov_id, prov_nombre, marca_default, nro_factura,
                          fecha_factura, tipo_code, modo_test)

        with col_btn3:
            if st.button("🗑️ Limpiar Todo", use_container_width=True):
                for k in ["articulos_lista", "resultado", "prov_detectado", "factura_ocr", "auto_procesado"]:
                    st.session_state[k] = defaults.get(k)
                for k in ["excel_df", "arts_existentes_bd", "excel_formato", "excel_filename"]:
                    st.session_state.pop(k, None)
                st.rerun()

    else:
        st.info("📤 Subí una factura arriba para procesarla automáticamente, o agregá artículos manualmente:")

        # ── Formulario manual (colapsado si hay OCR) ──
        with st.expander("➕ Agregar artículo manualmente", expanded=not st.session_state.get("auto_procesado")):
            with st.form("agregar_articulo", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    modelo = st.text_input("Modelo (ej: WKC215, RBK1100033358)", "").upper()
                    variante = st.text_input("Variante / Descripción", "")
                with c2:
                    color = st.text_input("Color", "").upper()
                    precio_unit = st.number_input("Precio Unitario ($)", min_value=0.0, step=1000.0, value=0.0)

                c3, c4 = st.columns(2)
                with c3:
                    dcto_comercial = st.number_input("Bonificación (%)", min_value=0.0, max_value=100.0, step=1.0, value=0.0)
                with c4:
                    codigo_barra_fab = st.text_input("Código Barra", "")

                st.markdown("**Curva de Talles:**")
                todos_talles = [str(t) for t in range(22, 46)]  # 22-45
                talles_cols = st.columns(8)
                talles_input = {}
                for i, t in enumerate(todos_talles):
                    with talles_cols[i % 8]:
                        talles_input[t] = st.number_input(f"T.{t}", min_value=0, max_value=99, value=0, key=f"talle_{t}")

                submitted = st.form_submit_button("➕ Agregar", use_container_width=True)

                if submitted and modelo and precio_unit > 0:
                    talles = [t for t, c in talles_input.items() if c > 0]
                    curva = [c for c in talles_input.values() if c > 0]
                    if talles:
                        st.session_state.articulos_lista.append({
                            "modelo": modelo, "variante": variante, "color": color,
                            "talles": talles, "curva": curva,
                            "precio_unitario": precio_unit,
                            "descuento_comercial": dcto_comercial,
                            "codigo_barra": codigo_barra_fab,
                        })
                        st.rerun()


# ══════════════════════════════════════════════════════════════════
# TAB FOTOS
# ══════════════════════════════════════════════════════════════════

with tab_fotos:
    st.subheader("📸 Fotos de Productos")
    st.caption(
        "Subí un catálogo PDF o fotos sueltas. Se extraen las imágenes, "
        "se agrega el logo de Calzalindo y se vinculan al ERP."
    )

    if not st.session_state.articulos_lista:
        st.info("Primero cargá artículos en la pestaña de Carga para vincular fotos.")
    else:
        arts_existentes = st.session_state.get("arts_existentes_bd", {})

        # Modelos del pedido (para filtrar fotos del catálogo)
        modelos_pedido = set()
        for a in st.session_state.articulos_lista:
            modelos_pedido.add(str(a["modelo"]).strip())

        # ── MODO: Catálogo PDF o Fotos sueltas ──
        modo_foto = st.radio(
            "Fuente de fotos",
            ["📄 Catálogo PDF (extrae fotos automáticamente)", "🖼️ Fotos sueltas por modelo"],
            horizontal=True,
            key="modo_foto",
        )

        # ── CATÁLOGO PDF ──────────────────────────────────────────
        if "Catálogo PDF" in modo_foto:
            catalogo_pdf = st.file_uploader(
                "Subí el catálogo PDF del proveedor",
                type=["pdf"],
                accept_multiple_files=True,
                key="catalogo_pdf",
            )

            # Checkbox para agregar logo
            agregar_logo = st.checkbox("Agregar logo Calzalindo", value=True, key="chk_logo")

            if catalogo_pdf:
                # Inicializar fotos extraídas en session_state
                if "fotos_catalogo" not in st.session_state:
                    st.session_state["fotos_catalogo"] = {}

                if st.button("🔍 Extraer fotos del catálogo", key="btn_extraer_catalogo"):
                    import re
                    import fitz  # PyMuPDF — no requiere poppler

                    fotos = {}  # {articulo_num: {pagina, imagen_bytes, matched}}

                    with st.spinner("Extrayendo páginas del PDF..."):
                        for pdf_file in catalogo_pdf:
                            pdf_bytes = pdf_file.read()
                            pdf_file.seek(0)

                            try:
                                import io as _io
                                doc = fitz.open(stream=pdf_bytes, filetype="pdf")

                                for i, page in enumerate(doc):
                                    texto = (page.get_text() or "").upper()
                                    # ARTICUL0 con cero a veces (OCR confunde O/0)
                                    matches = re.findall(r"ARTICUL[O0]\s*(\d+)", texto)
                                    if not matches:
                                        continue

                                    art_num = matches[0]  # tomar el primero

                                    # Si ya tenemos este artículo, solo guardar si es mejor
                                    if art_num in fotos:
                                        continue  # tomar la primera aparición

                                    # Renderizar página como imagen (200 dpi)
                                    mat = fitz.Matrix(200/72, 200/72)
                                    pix = page.get_pixmap(matrix=mat)
                                    img_bytes = pix.tobytes("png")

                                    # Verificar si está en el pedido
                                    matched = art_num in modelos_pedido

                                    fotos[art_num] = {
                                        "pagina": i + 1,
                                        "imagen_bytes": img_bytes,
                                        "matched": matched,
                                        "pdf_name": pdf_file.name,
                                        "texto_pdf": texto,  # para clasificación
                                    }

                                doc.close()

                            except Exception as e:
                                st.error(f"Error procesando {pdf_file.name}: {e}")
                                continue

                    # Procesar imágenes: fondo blanco, cuadrado, logo
                    if fotos:
                        with st.spinner("Procesando imágenes (fondo blanco + logo)..."):
                            for art_num, fdata in fotos.items():
                                try:
                                    fdata["imagen_bytes"] = _procesar_imagen_producto(
                                        fdata["imagen_bytes"],
                                        agregar_logo=agregar_logo,
                                        es_catalogo=True,
                                    )
                                    fdata["con_logo"] = agregar_logo
                                except Exception as e:
                                    fdata["con_logo"] = False
                                    log.warning(f"Error procesando imagen art {art_num}: {e}")

                    # Clasificar cada artículo usando historial del proveedor
                    with st.spinner("Clasificando artículos..."):
                        historial = _obtener_historial_proveedor(prov_id)
                        for art_num, fdata in fotos.items():
                            clasif = _clasificar_articulo(
                                fdata.get("texto_pdf", ""),
                                fdata.get("pdf_name", ""),
                                historial,
                            )
                            fdata["clasificacion"] = clasif

                    st.session_state["fotos_catalogo"] = fotos

                    # Resumen
                    en_pedido = sum(1 for f in fotos.values() if f["matched"])
                    total = len(fotos)
                    st.success(
                        f"Se encontraron {total} artículos en el catálogo. "
                        f"{en_pedido} coinciden con el pedido cargado."
                    )

                # ── Mostrar fotos extraídas ──
                fotos_guardadas = st.session_state.get("fotos_catalogo", {})
                if fotos_guardadas:
                    st.divider()

                    # Primero los que coinciden con el pedido
                    fotos_pedido = {k: v for k, v in fotos_guardadas.items() if v["matched"]}
                    fotos_otras = {k: v for k, v in fotos_guardadas.items() if not v["matched"]}

                    def _mostrar_foto_con_clasificacion(art_num, fdata, arts_existentes, editable=True):
                        """Muestra foto + clasificación + descripción para un artículo."""
                        import io as _io

                        col_foto, col_clasif = st.columns([1, 1])

                        with col_foto:
                            st.image(
                                fdata["imagen_bytes"],
                                caption=f"Art. {art_num}",
                                use_container_width=True,
                            )
                            logo_tag = " +logo" if fdata.get("con_logo") else ""
                            st.caption(f"Pág {fdata['pagina']} — {fdata['pdf_name']}{logo_tag}")

                            # Vincular a BD
                            en_bd = arts_existentes.get(art_num, [])
                            if en_bd:
                                codigos = [str(ab["codigo"]) for ab in en_bd[:5]]
                                st.success(f"BD: {', '.join(codigos)}")
                                if st.button(f"🔗 Vincular foto", key=f"vincular_cat_{art_num}"):
                                    _vincular_foto_articulos(en_bd, fdata["imagen_bytes"], "png")
                            else:
                                st.warning("No encontrado en BD aún")

                        with col_clasif:
                            clasif = fdata.get("clasificacion", {})
                            if not clasif:
                                st.info("Sin clasificación")
                                return

                            st.markdown(f"**Descripción sugerida:**")
                            desc_key = f"desc_{art_num}"
                            # Formato: ART_PROV COLOR TIPO DETALLE (ej: "66 NEGRO BOTAS PU")
                            desc_base = clasif.get("descripcion_sugerida", "")
                            desc_default = f"{art_num} {desc_base}".strip()[:60]
                            new_desc = st.text_input(
                                "Descripción", value=desc_default, key=desc_key,
                                label_visibility="collapsed",
                            )

                            # Rubro (género)
                            rubro_opts = list(RUBROS.keys())
                            rubro_labels = [f"{k} — {v}" for k, v in RUBROS.items()]
                            rubro_default = rubro_opts.index(clasif["rubro"]) if clasif["rubro"] in rubro_opts else 0
                            sel_rubro = st.selectbox(
                                "Rubro (género)", rubro_labels,
                                index=rubro_default, key=f"rubro_{art_num}",
                            )

                            # Subrubro (tipo calzado)
                            subrubro_opts = list(SUBRUBROS.keys())
                            subrubro_labels = [f"{k} — {v}" for k, v in SUBRUBROS.items()]
                            subrubro_default = subrubro_opts.index(clasif["subrubro"]) if clasif["subrubro"] in subrubro_opts else 0
                            sel_subrubro = st.selectbox(
                                "Subrubro (tipo)", subrubro_labels,
                                index=subrubro_default, key=f"subrubro_{art_num}",
                            )

                            # Grupo (material)
                            grupo_opts = list(GRUPOS_MAT.keys())
                            grupo_labels = [f"{k} — {v}" for k, v in GRUPOS_MAT.items()]
                            grupo_val = int(clasif["grupo"]) if clasif["grupo"].isdigit() else 5
                            grupo_default = grupo_opts.index(grupo_val) if grupo_val in grupo_opts else 0
                            sel_grupo = st.selectbox(
                                "Grupo (material)", grupo_labels,
                                index=grupo_default, key=f"grupo_{art_num}",
                            )

                            # Linea (temporada)
                            linea_opts = list(LINEAS.keys())
                            linea_labels = [f"{k} — {v}" for k, v in LINEAS.items()]
                            linea_default = linea_opts.index(clasif["linea"]) if clasif["linea"] in linea_opts else 0
                            sel_linea = st.selectbox(
                                "Linea (temporada)", linea_labels,
                                index=linea_default, key=f"linea_{art_num}",
                            )

                            # Resumen
                            st.caption(
                                f"Auto: {clasif['rubro_nombre']} / "
                                f"{clasif['subrubro_nombre']} / "
                                f"{clasif['grupo_nombre']} / "
                                f"{clasif['linea_nombre']}"
                            )

                        st.divider()

                    if fotos_pedido:
                        st.markdown("### Artículos del pedido")
                        for art_num, fdata in fotos_pedido.items():
                            _mostrar_foto_con_clasificacion(art_num, fdata, arts_existentes)

                    if fotos_otras:
                        with st.expander(
                            f"Otros artículos del catálogo ({len(fotos_otras)}) — no están en el pedido"
                        ):
                            for art_num, fdata in fotos_otras.items():
                                _mostrar_foto_con_clasificacion(art_num, fdata, arts_existentes)

        # ── FOTOS SUELTAS ─────────────────────────────────────────
        else:
            st.caption(
                "Subí la foto del modelo+color. Al vincular, se copia a "
                "`F:\\Macroges\\Imagenes\\` y se registra en la tabla `imagen` del ERP."
            )

            # Agrupar por modelo+color
            modelos_unicos = []
            seen = set()
            for a in st.session_state.articulos_lista:
                key = f"{a['modelo']}|{a['color']}"
                if key not in seen:
                    seen.add(key)
                    modelos_unicos.append({"modelo": a["modelo"], "color": a["color"]})

            for mc in modelos_unicos:
                modelo_key = mc["modelo"]
                color_key = mc["color"]
                display_key = f"{modelo_key} {color_key}"

                en_bd = arts_existentes.get(modelo_key, [])
                en_bd_color = [
                    ab
                    for ab in en_bd
                    if color_key.upper() in (ab.get("color", "").upper())
                ]
                if not en_bd_color:
                    en_bd_color = en_bd

                col_titulo, col_estado = st.columns([3, 2])
                with col_titulo:
                    st.markdown(f"### {display_key}")
                with col_estado:
                    if en_bd_color:
                        codigos = [str(ab["codigo"]) for ab in en_bd_color[:5]]
                        st.success(f"BD: {', '.join(codigos)}")
                    else:
                        st.warning("Sin artículos en BD")

                foto = st.file_uploader(
                    f"Foto para {display_key}",
                    type=["jpg", "jpeg", "png", "webp"],
                    accept_multiple_files=False,
                    key=f"foto_{modelo_key}_{color_key}",
                )

                if foto:
                    col_img, col_info_foto = st.columns([1, 1])
                    with col_img:
                        foto_bytes_raw = foto.read()
                        foto.seek(0)

                        # Procesar: fondo blanco, cuadrada 1200x1200, logo top-right
                        try:
                            foto_display = _procesar_imagen_producto(
                                foto_bytes_raw, agregar_logo=True, es_catalogo=False
                            )
                        except Exception:
                            foto_display = foto_bytes_raw

                        st.image(foto_display, caption=display_key, use_container_width=True)

                    with col_info_foto:
                        foto_ext = foto.name.rsplit(".", 1)[-1].lower()
                        if foto_ext == "jpeg":
                            foto_ext = "jpg"
                        st.markdown(f"**Archivo:** {foto.name} ({foto.size // 1024} KB)")

                        if en_bd_color:
                            st.markdown("**Se vincula a:**")
                            for ab in en_bd_color[:10]:
                                st.caption(
                                    f"Cód {ab['codigo']} — {ab['desc1']} — "
                                    f"{ab['color']} T{ab['talle']}"
                                )

                            if st.button(
                                f"🔗 Vincular foto ({len(en_bd_color)} art.)",
                                key=f"vincular_{modelo_key}_{color_key}",
                            ):
                                _vincular_foto_articulos(
                                    en_bd_color, foto_display, "png"
                                )
                        else:
                            st.info("Artículos no encontrados en BD aún.")

                st.divider()


# ══════════════════════════════════════════════════════════════════
# TAB RESULTADO
# ══════════════════════════════════════════════════════════════════

with tab_resultado:
    if st.session_state.resultado:
        res = st.session_state.resultado
        st.subheader("📊 Resultado del Procesamiento")

        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        with col_r1:
            st.metric("Exitosos", res.get("exitosos", 0))
        with col_r2:
            st.metric("Existentes", res.get("articulos_existentes", 0))
        with col_r3:
            st.metric("Creados", res.get("articulos_creados", 0))
        with col_r4:
            st.metric("Fallidos", res.get("fallidos", 0), delta_color="inverse")

        if res.get("errores"):
            st.error("Errores:")
            for err in res["errores"]:
                st.markdown(f"- {err}")

        st.divider()
        st.subheader("Detalle por Artículo")

        for linea in res.get("lineas_procesadas", []):
            status = "✅" if linea.get("codigo_articulo", 0) > 0 else "❌"
            badge = "🆕" if linea.get("articulo_creado") else "📦" if linea.get("articulo_existente") else "❓"
            st.markdown(
                f"{status} {badge} **{linea.get('descripcion', '')}** T:{linea.get('talle', '')} "
                f"x{linea.get('cantidad', 0)} — "
                f"Código: **{linea.get('codigo_articulo', 0)}** — "
                f"Sinónimo: {linea.get('codigo_sinonimo', '')}"
            )
    else:
        st.info("Procesá una factura para ver los resultados acá.")


# ══════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════

st.sidebar.divider()
st.sidebar.markdown("""
**Sistema de Carga H4/Calzalindo**
v2.4 — Marzo 2026

Flujo: PDF/imagen (OCR) o Excel/CSV → Proveedor → Verificar → Cargar
Excel: soporta formato horizontal (talles en columnas) y vertical
Fotos: extrae de catálogo PDF + logo Calzalindo → vincula al ERP
""")
