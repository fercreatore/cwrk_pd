#!/usr/bin/env python3
"""
OCR / Parser de facturas en PDF.
Extrae texto del PDF con PyMuPDF y parsea artículos, cantidades, precios.

Soporta:
  - Facturas de Distrinando (Reebok, Crocs)
  - Facturas de Wake (Industrias AS S.A.)
  - Formato genérico con detección automática

Uso:
  from ocr_factura import parsear_pdf_factura
  datos = parsear_pdf_factura("/path/to/factura.pdf")
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("ocr_factura")


# ══════════════════════════════════════════════════════════════════
# MAPEO DE COLORES REEBOK (inglés/código interno → español)
# ══════════════════════════════════════════════════════════════════
# Los colores Reebok vienen como códigos abreviados: VECNAV, FTWWHT, etc.
# Hay que traducirlos al español que usa el sistema MacroGest.

COLORES_REEBOK = {
    # Básicos
    "BLACK": "NEGRO", "BLK": "NEGRO", "CBLACK": "NEGRO",
    "WHITE": "BLANCO", "WHT": "BLANCO", "FTWWHT": "BLANCO", "CHALK": "BLANCO",
    "GREY": "GRIS", "GRY": "GRIS", "PUGRY": "GRIS", "CDGRY": "GRIS",
    "MGREYH": "GRIS", "FLGRY": "GRIS", "CLGRY": "GRIS", "STEELY": "GRIS",
    # Azules
    "NAVY": "AZUL", "VECNAV": "AZUL", "CONAVY": "AZUL", "HOOBLU": "AZUL",
    "BLUE": "AZUL", "RBKBLU": "AZUL", "BATBLU": "AZUL", "EACOBL": "AZUL",
    # Rojos
    "RED": "ROJO", "VECRED": "ROJO", "INSRED": "ROJO",
    # Verdes
    "GREEN": "VERDE", "SGREEN": "VERDE", "HARGRN": "VERDE",
    # Rosas / Lilas
    "PINK": "ROSA", "PROPNK": "ROSA", "PIXPNK": "ROSA",
    "LILAC": "LILA", "INFLIL": "LILA", "PURPRN": "LILA",
    # Marrones / Beige
    "BROWN": "MARRON", "UTIBRO": "MARRON",
    "BEIGE": "BEIGE", "SAHARA": "BEIGE", "STUCCO": "BEIGE",
    "TAN": "BEIGE", "SOFCAM": "BEIGE",
    # Naranja / Amarillo
    "ORANGE": "NARANJA", "SEMORC": "NARANJA",
    "YELLOW": "AMARILLO", "ALERTY": "AMARILLO",
    # Especiales
    "SILVMT": "PLATA", "GOLDMT": "DORADO",
}


def traducir_color_reebok(color_code: str) -> str:
    """
    Traduce código de color Reebok (VECNAV/FTWWHT/HOOBLU) a español (AZUL/BLANCO).
    Toma los 2 primeros componentes significativos (ignora el tercero si es similar).
    """
    if not color_code:
        return ""

    partes = [p.strip().upper() for p in color_code.split("/") if p.strip()]
    colores_es = []
    vistos = set()

    for parte in partes:
        color_es = COLORES_REEBOK.get(parte, "")
        if not color_es:
            # Intentar match parcial
            for key, val in COLORES_REEBOK.items():
                if key in parte or parte in key:
                    color_es = val
                    break
        if color_es and color_es not in vistos:
            colores_es.append(color_es)
            vistos.add(color_es)

    if colores_es:
        return "/".join(colores_es[:2])  # máx 2 colores como en el sistema
    return color_code  # devolver original si no se pudo traducir


@dataclass
class LineaOCR:
    """Una línea/artículo extraído del PDF."""
    codigo_producto: str = ""
    descripcion: str = ""
    color: str = ""
    talle: str = ""
    cantidad: int = 0
    precio_unitario: float = 0.0
    precio_total: float = 0.0
    codigo_barra: str = ""
    descuento: float = 0.0
    # Campos MacroGest para articulo table
    descripcion_1: str = ""  # "FLEXAGON ENERGY TR 4 AZUL/BLANCO ZAPA DEP AC COMB" (160 chars)
    descripcion_2: str = ""  # null generalmente
    descripcion_3: str = ""  # "FLEXAGON ENERGY TR 4 ZAPA DEP AC COMB" (modelo+tipo, SIN color) (90 chars)
    descripcion_4: str = ""  # "AZUL/BLANCO" (color en español) (90 chars)
    descripcion_5: str = ""  # "41" (talle entero) (90 chars)


@dataclass
class FacturaOCR:
    """Datos extraídos de una factura PDF."""
    proveedor: str = ""
    cuit_proveedor: str = ""
    tipo_comprobante: str = ""      # FA, FB, FC, RM, etc.
    letra: str = ""                 # A, B, C
    numero: str = ""                # 00001-00039295
    fecha: str = ""
    cliente: str = ""
    cuit_cliente: str = ""
    condicion_venta: str = ""       # CONTADO, CTA CTE, etc.
    subtotal: float = 0.0
    iva: float = 0.0
    total: float = 0.0
    lineas: list = field(default_factory=list)
    texto_crudo: str = ""           # texto completo extraído
    paginas: int = 0


def extraer_texto_pdf(pdf_bytes: bytes) -> tuple[str, int]:
    """Extrae texto de un PDF. Intenta PyMuPDF primero, fallback a pdfplumber."""
    # Intentar PyMuPDF (más rápido)
    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        textos = []
        for page in doc:
            textos.append(page.get_text())
        doc.close()
        texto = "\n".join(textos)
        if texto.strip():
            return texto, len(textos)
    except ImportError:
        log.info("PyMuPDF no disponible, usando pdfplumber")
    except Exception as e:
        log.warning(f"PyMuPDF falló ({e}), usando pdfplumber")

    # Fallback: pdfplumber (más robusto con PDFs complejos)
    try:
        import pdfplumber
        import io
        pdf = pdfplumber.open(io.BytesIO(pdf_bytes))
        textos = []
        for page in pdf.pages:
            textos.append(page.extract_text() or "")
        n_pages = len(textos)
        pdf.close()
        return "\n".join(textos), n_pages
    except ImportError:
        raise ImportError(
            "Ni PyMuPDF ni pdfplumber están instalados.\n"
            "Instalar uno: pip install PyMuPDF  o  pip install pdfplumber"
        )


def extraer_texto_imagen(img_bytes: bytes) -> str:
    """Extrae texto de una imagen (JPG, PNG, HEIC) usando OCR (pytesseract)."""
    try:
        import pytesseract
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(img_bytes))
        # Convertir a RGB si es necesario
        if img.mode != "RGB":
            img = img.convert("RGB")
        texto = pytesseract.image_to_string(img, lang="spa")
        return texto
    except ImportError:
        log.warning("pytesseract no instalado — instalar: pip install pytesseract")
        # Fallback: intentar con PyMuPDF OCR
        try:
            import fitz
            doc = fitz.open(stream=img_bytes, filetype="png")
            page = doc[0]
            texto = page.get_text("text")
            doc.close()
            if texto.strip():
                return texto
        except Exception:
            pass
        raise ImportError(
            "Para OCR de imágenes instalar: pip install pytesseract\n"
            "Y Tesseract: brew install tesseract (Mac) o descargar de github.com/tesseract-ocr"
        )


def detectar_proveedor(texto: str) -> str:
    """Detecta el proveedor a partir del texto de la factura."""
    texto_upper = texto.upper()
    if "DISTRINANDO" in texto_upper:
        return "DISTRINANDO"
    elif "INDUSTRIAS AS" in texto_upper or "WAKE" in texto_upper:
        return "WAKE"
    elif "ALPARGATAS" in texto_upper:
        return "ALPARGATAS"
    return "DESCONOCIDO"


def parsear_cabecera(texto: str, factura: FacturaOCR):
    """Extrae datos de cabecera de la factura."""
    # Tipo y número de comprobante
    # Distrinando: "▌FACTURA" sin letra visible, pero N° tiene formato 0039-00273749
    m = re.search(r'FACTURA\s*([A-C])', texto, re.IGNORECASE)
    if m:
        factura.tipo_comprobante = "FA"
        factura.letra = m.group(1).upper()
    elif re.search(r'FACTURA', texto, re.IGNORECASE):
        factura.tipo_comprobante = "FA"

    # Número: buscar patrón 0039-00273749 o Nro: XXXX-XXXXXXXX
    m = re.search(r'(?:N[°º]|Nro\.?)\s*[:\s]*(\d{4,5}[-–]\d{6,8})', texto)
    if not m:
        # Distrinando: Fecha: N°: ... 04/03/2026  0039-00273749
        m = re.search(r'(\d{4}[-–]\d{8})', texto)
    if m:
        factura.numero = m.group(1).replace("–", "-")

    # Fecha — Distrinando: "04/03/2026" suelto en el texto, o "Fecha: XX/XX/XXXX"
    m = re.search(r'(?:FECHA|Fecha)\s*[:\s]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', texto, re.IGNORECASE)
    if not m:
        # Buscar fecha suelta formato DD/MM/YYYY
        m = re.search(r'(\d{2}/\d{2}/\d{4})', texto)
    if m:
        factura.fecha = m.group(1)

    # CUIT proveedor — el primero que aparece suele ser del emisor
    cuits = re.findall(r'(\d{2}[-–]\d{8}[-–]\d{1})', texto)
    if cuits:
        factura.cuit_proveedor = cuits[0].replace("-", "").replace("–", "")
    else:
        m = re.search(r'C\.?U\.?I\.?T\.?\s*[:\s]*([\d\-–]+)', texto)
        if m:
            factura.cuit_proveedor = m.group(1).replace("-", "").replace("–", "")

    # Cliente — buscar después de "Señor(es):" o "Cliente:"
    m = re.search(r'Se[ñn]or(?:\(es\)|es)?\s*[:\s]*(.+?)(?:\n|Direcc)', texto, re.IGNORECASE)
    if m:
        factura.cliente = m.group(1).strip()
    else:
        m = re.search(r'Cliente\s*[:\s]*(.+?)(?:\n|Domicilio)', texto, re.IGNORECASE)
        if m:
            factura.cliente = m.group(1).strip()

    # CUIT cliente (segundo CUIT encontrado)
    if len(cuits) >= 2:
        factura.cuit_cliente = cuits[1].replace("-", "").replace("–", "")

    # Condición de venta — limitar a máx 60 chars (el OCR todo-en-una-línea se pasa)
    m = re.search(r'Cond(?:ici[oó]n)?\.?\s*de\s*Venta\s*[:\s]*(.+?)(?:\n|Responsable|▌|FACTURA|$)', texto, re.IGNORECASE)
    if m:
        cond = m.group(1).strip()
        # Limpiar: tomar hasta el primer CUIT o palabra clave
        cond = re.split(r'\d{2}-\d{8}-\d|Responsable|▌', cond)[0].strip()
        factura.condicion_venta = cond[:80]

    # Letra de factura — Distrinando: puede estar como "01A" al inicio
    if not factura.letra:
        m = re.search(r'\b01([A-C])\b', texto)
        if m:
            factura.letra = m.group(1)

    # Totales — Distrinando usa formato argentino: "793.721,90 ARS"
    # El OCR puede mezclar formatos: "651,660.02" (US) vs "793.721,90" (ARG)
    def _parse_monto_arg(s: str) -> float:
        """Parsea monto en formato argentino (punto=miles, coma=decimal)
        o formato US (coma=miles, punto=decimal). Auto-detecta."""
        s = s.strip()
        # Si tiene coma seguida de exactamente 2 dígitos al final → ARG
        if re.match(r'^[\d.]+,\d{2}$', s):
            return float(s.replace(".", "").replace(",", "."))
        # Si tiene punto seguido de exactamente 2 dígitos al final → US
        if re.match(r'^[\d,]+\.\d{2}$', s):
            return float(s.replace(",", ""))
        # Fallback: tratar como argentino
        return float(s.replace(".", "").replace(",", "."))

    # Distrinando especial: "793.721,90 ARS ▌Total:" (total al final con ▌)
    # Y bloque: "Total Percep. IIBB:: Total IVA: Descuento: Subtotal:  0,00 ARS  136.848,60 ARS  5.213,28 ARS  651.660,02 ARS"
    # Los valores ARS después de "Subtotal:" corresponden a: [Perc IIBB? / Descuento, IVA, Perc IIBB, Subtotal]
    # El mayor valor ARS suele ser el subtotal

    # Primero intentar el total general
    # Formato 1 (pdfplumber): "▌Total: 793.721,90 ARS" (más confiable, buscar primero)
    # Formato 2 (fitz): "793.721,90 ARS ▌Total:" (en la misma línea, sin salto)
    m_total_general = re.search(r'▌Total:\s*([\d.,]+)\s*ARS', texto)
    if not m_total_general:
        m_total_general = re.search(r'([\d.,]+)\s*ARS[ \t]*▌Total:', texto)  # sin \n
    if m_total_general:
        try:
            factura.total = _parse_monto_arg(m_total_general.group(1))
        except ValueError:
            pass

    # Extraer subtotal e IVA con patrones específicos
    # Subtotal: buscar "Subtotal:" seguido de monto ARS
    m_sub = re.search(r'Subtotal:\s*([\d.,]+)\s*ARS', texto, re.IGNORECASE)
    if m_sub:
        try:
            factura.subtotal = _parse_monto_arg(m_sub.group(1))
        except ValueError:
            pass

    # IVA: buscar "Total IVA:" seguido de monto ARS
    m_iva = re.search(r'Total\s+IVA:\s*([\d.,]+)\s*ARS', texto, re.IGNORECASE)
    if not m_iva:
        # Fallback: "IVA_21" seguido de montos, tomar el último
        m_iva = re.search(r'IVA[_\s]21.*?([\d.,]+)\s*(?:ARS|$)', texto, re.IGNORECASE)
    if m_iva:
        try:
            factura.iva = _parse_monto_arg(m_iva.group(1))
        except ValueError:
            pass

    # Fallback: patrones estándar
    if factura.total == 0:
        for pattern, attr in [
            (r'TOTAL\s+Pesos?\s*[\$\s]*([\d.,]+)', 'total'),
            (r'SUBTOTAL\s*[\$\s]*([\d.,]+)', 'subtotal'),
            (r'NETO\s*[\$\s]*([\d.,]+)', 'subtotal'),
        ]:
            m = re.search(pattern, texto, re.IGNORECASE)
            if m:
                try:
                    v = _parse_monto_arg(m.group(1))
                    current = getattr(factura, attr, 0)
                    if v > current:
                        setattr(factura, attr, v)
                except (ValueError, AttributeError):
                    pass


def parsear_distrinando(texto: str, factura: FacturaOCR):
    """
    Parser específico para facturas de Distrinando Deportes (Reebok, Crocs, etc.).

    Formato real del OCR (ejemplo):
        RBK1100033358---M12 8/13 (11232111)  651,660.02  10  3.00  67,181.45
        FLEXAGON ENERGY TR 4 - VECNAV/FTWWHT/HOOBLU -  M12 8/13 (11232111)

    Patrón de código: RBK + dígitos + ---M{pares} {talle_ini}/{talle_fin} ({ean_parcial})
    M12 8/13 = 12 pares, talles del 8 al 13 (numeración US → convierte a ARG)
    Precio unitario = por par, bonificación en %

    Colores Reebok vienen como código: VECNAV/FTWWHT/HOOBLU (3 componentes separados por /)
    """
    factura.proveedor = "DISTRINANDO DEPORTES S.A."

    # ══════════════════════════════════════════════════════════════
    # Tabla de conversión US → ARG para calzado Reebok
    # Hombre: offset +32 (US 7=39, US 8=40, ..., US 15=47)
    # Mujer:  offset +30 (US 5=35, US 6=36, ..., US 11=41)
    # Kids:   offset +31 (US 1=32, ...)
    # Medios puntos: US 8.5 → ARG "40½" (carácter Unicode ½ para etiqueta)
    # ══════════════════════════════════════════════════════════════
    US_A_ARG_HOMBRE = {
        7: 39, 7.5: 39.5, 8: 40, 8.5: 40.5, 9: 41, 9.5: 41.5,
        10: 42, 10.5: 42.5, 11: 43, 11.5: 43.5, 12: 44, 12.5: 44.5,
        13: 45, 14: 46, 15: 47, 16: 48,
    }
    US_A_ARG_MUJER = {
        5: 35, 5.5: 35.5, 6: 36, 6.5: 36.5, 7: 37, 7.5: 37.5,
        8: 38, 8.5: 38.5, 9: 39, 9.5: 39.5, 10: 40, 10.5: 40.5,
        11: 41, 11.5: 41.5,
    }

    # Sufijo estándar para zapatillas Reebok en el sistema
    SUFIJO_TIPO = "ZAPA DEP AC COMB"

    def _parse_monto(s: str) -> float:
        """Parsea monto en formato ARG (651.660,02) o US (651,660.02)."""
        s = s.strip()
        if re.match(r'^[\d.]+,\d{2}$', s):  # ARG: 651.660,02
            return float(s.replace(".", "").replace(",", "."))
        if re.match(r'^[\d,]+\.\d{2}$', s):  # US: 651,660.02
            return float(s.replace(",", ""))
        return float(s.replace(".", "").replace(",", "."))

    def _us_a_arg(talle_us: float, talle_ini: float) -> str:
        """Convierte talle US a ARG, auto-detectando hombre/mujer por rango.
        Regla: si el talle mínimo US de la curva es <= 6 → mujer (+30), sino → hombre (+32).
        Medios puntos usan carácter ½: 40.5 → '40½' (cabe en la etiqueta)."""
        if talle_ini <= 6:
            talle_arg = US_A_ARG_MUJER.get(talle_us, talle_us + 30)
        else:
            talle_arg = US_A_ARG_HOMBRE.get(talle_us, talle_us + 32)
        # Formatear: entero como "41", medio punto como "41½"
        if isinstance(talle_arg, float) and talle_arg != int(talle_arg):
            return f"{int(talle_arg)}½"
        return str(int(talle_arg))

    # ── Buscar "Pares:" como validación ──
    m_pares_total = re.search(r'Pares:\s*(\d+)', texto)
    pares_factura = int(m_pares_total.group(1)) if m_pares_total else 0

    # ── Buscar pedido de cliente referencia ──
    m_pedido = re.search(r'Pedidos?\s*de\s*cliente\s*(\d+)', texto, re.IGNORECASE)
    pedido_ref = m_pedido.group(1) if m_pedido else ""

    # ── Buscar descripción y color Reebok ──
    # FLEXAGON ENERGY TR 4 - VECNAV/FTWWHT/HOOBLU
    m_desc = re.search(
        r'([A-Z][A-Z0-9\s.]+?)\s*[-–]\s*([A-Z]{3,}/[A-Z]{3,}(?:/[A-Z]{3,})?)',
        texto, re.IGNORECASE
    )
    desc_modelo = m_desc.group(1).strip() if m_desc else ""
    color_code_orig = m_desc.group(2).strip() if m_desc else ""
    # Traducir color inglés → español
    color_es = traducir_color_reebok(color_code_orig)

    # Construir descripciones según formato DB MacroGest:
    # desc_1: "FLEXAGON ENERGY TR 4 AZUL/BLANCO ZAPA DEP AC COMB" (full, 160 chars)
    # desc_2: null
    # desc_3: "FLEXAGON ENERGY TR 4 ZAPA DEP AC COMB" (modelo+tipo SIN color, 90 chars)
    # desc_4: "AZUL/BLANCO" (color español, 90 chars)
    # desc_5: "41" (talle entero, se setea por línea)
    desc_1_base = f"{desc_modelo} {color_es} {SUFIJO_TIPO}".strip()[:160]
    desc_3 = f"{desc_modelo} {SUFIJO_TIPO}".strip()[:90]
    desc_4 = color_es[:90]

    # ── Buscar artículos RBK ──
    # Patrón: RBK1100033358---M12 8/13 (11232111)  651,660.02  10  3.00  67,181.45

    for m_rbk in re.finditer(r'(RBK\d{10,14})[-—]+(M\d+)\s+(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*\((\d+)\)', texto, re.IGNORECASE):
        codigo_rbk = m_rbk.group(1)
        total_pares = int(m_rbk.group(2)[1:])  # M12 → 12
        talle_ini = float(m_rbk.group(3).replace(",", "."))
        talle_fin = float(m_rbk.group(4).replace(",", "."))
        ean_parcial = m_rbk.group(5)

        # Buscar los números que vienen después: precio_unit, bonif%, cantidad, total_linea
        # NOTA: el orden en el PDF de Distrinando (columnas) es:
        #   Precio | %Bonif | Cantidad | Total
        # Pero entre el match RBK y los números puede haber texto descriptivo
        # con números sueltos (ej: "TR 4", "8/13") que hay que filtrar.
        pos_after = m_rbk.end()
        texto_after = texto[pos_after:pos_after + 200]

        # Extraer números significativos: ignorar dígitos sueltos (1-2 chars)
        # que son parte de la descripción (ej: "TR 4", "M12")
        # Un número válido de factura tiene formato: 67,181.45 o 651.660,02 o 3.00 o 10
        numeros_raw = re.findall(r'([\d.,]+)', texto_after)
        # Filtrar: quedarnos solo con números que parezcan montos/cantidades reales
        # (al menos 2 dígitos, o es un decimal tipo "3.00")
        numeros = []
        for n in numeros_raw:
            digitos = n.replace(",", "").replace(".", "")
            # Aceptar si: tiene 2+ dígitos, O es un decimal con punto/coma
            if len(digitos) >= 2 or ("." in n or "," in n):
                numeros.append(n)

        precio_unit = 0
        bonif_pct = 0
        precio_total_linea = 0
        cantidad_factura = 0

        if len(numeros) >= 4:
            # El orden varía según el extractor (fitz vs pdfplumber).
            # fitz:       Total, Cantidad, Bonif%, Precio
            # pdfplumber: Precio, Bonif%, Cantidad, Total
            # Solución: clasificar por valor, no por posición.
            try:
                # SOLO los primeros 4 números. Más allá hay basura
                # (ej: "12","13" del repetido "M12 8/13" en la línea siguiente)
                valores = []
                for n in numeros[:4]:
                    try:
                        valores.append((_parse_monto(n), n))
                    except ValueError:
                        continue

                # Separar: montos grandes (>100) vs chicos (<=100)
                grandes = sorted([(v, n) for v, n in valores if v > 100], reverse=True)
                chicos = [(v, n) for v, n in valores if v <= 100]

                # El mayor es el total de línea, el segundo mayor es precio unitario
                if len(grandes) >= 2:
                    precio_total_linea = grandes[0][0]
                    precio_unit = grandes[1][0]
                elif len(grandes) == 1:
                    precio_unit = grandes[0][0]

                # Entre los chicos: bonif% tiene decimales (3.00), cantidad no (10)
                for v, n in chicos:
                    if v < 20 and ("." in n or "," in n):
                        bonif_pct = v
                    elif v > 0 and cantidad_factura == 0:
                        cantidad_factura = int(v)

            except (ValueError, IndexError) as e:
                log.warning(f"Error parseando números post-RBK: {numeros[:6]} - {e}")
                for n in numeros:
                    try:
                        v = _parse_monto(n)
                        if 1000 < v < 500000 and precio_unit == 0:
                            precio_unit = v
                    except ValueError:
                        continue
        elif len(numeros) >= 1:
            # Buscar el número más probable como precio unitario
            for n in numeros:
                try:
                    v = _parse_monto(n)
                    if 1000 < v < 500000:
                        precio_unit = v
                        break
                except ValueError:
                    continue

        # Validar: si pares_factura dice 12 y total_pares dice 12, ok
        if pares_factura > 0 and total_pares != pares_factura:
            log.warning(f"Pares M{total_pares} != Pares factura {pares_factura}")

        # Generar talles US — paso entero primero, medio solo si necesario
        talles_us = []
        t = talle_ini
        while t <= talle_fin:
            talles_us.append(t)
            t += 1
            if len(talles_us) > 20:
                break

        # Usar paso 0.5 SOLO si paso 1 no divide bien en total_pares
        # M12 8/13 → 6 talles con paso 1 → 12/6=2 pares c/u → OK
        # M11 8/13 → 6 talles con paso 1 → 11/6 no es entero → probar paso 0.5 (11 talles) → 11/11=1 → OK
        n_step1 = len(talles_us)
        if n_step1 > 0 and total_pares % n_step1 != 0:
            talles_half = []
            t = talle_ini
            while t <= talle_fin:
                talles_half.append(t)
                t += 0.5
                if len(talles_half) > 30:
                    break
            # Preferir medio paso si distribuye mejor
            n_half = len(talles_half)
            if n_half > 0 and (total_pares % n_half == 0 or
                               abs(total_pares - n_half) < abs(total_pares - n_step1)):
                talles_us = talles_half

        if not talles_us:
            talles_us = [talle_ini]

        # Distribución de pares por talle
        pares_por_talle = max(1, total_pares // len(talles_us))
        resto = total_pares - (pares_por_talle * len(talles_us))

        for idx, talle_us in enumerate(talles_us):
            talle_arg = _us_a_arg(talle_us, talle_ini)
            cant = pares_por_talle + (1 if idx < resto else 0)
            if cant > 0:
                desc_5 = str(talle_arg)
                linea_ocr = LineaOCR(
                    codigo_producto=codigo_rbk,
                    descripcion=desc_1_base,
                    color=color_es,
                    talle=desc_5,
                    cantidad=cant,
                    precio_unitario=precio_unit,
                    precio_total=round(cant * precio_unit, 2),
                    codigo_barra=ean_parcial,
                    descuento=bonif_pct,
                    descripcion_1=desc_1_base,
                    descripcion_2="",
                    descripcion_3=desc_3,
                    descripcion_4=desc_4,
                    descripcion_5=desc_5,
                )
                factura.lineas.append(linea_ocr)

    # Si no encontró con el patrón RBK, intentar parseo más flexible
    if not factura.lineas:
        log.info("Patrón RBK no matcheó, intentando parseo flexible...")
        _parsear_distrinando_flexible(texto, factura)


def _parsear_distrinando_flexible(texto: str, factura: FacturaOCR):
    """
    Parser flexible para Distrinando cuando el regex completo no matchea.
    Busca patrones parciales en el texto OCR.
    """
    SUFIJO_TIPO = "ZAPA DEP AC COMB"

    # Tablas US → ARG (medios puntos con ½)
    US_A_ARG_HOMBRE = {
        7: 39, 7.5: 39.5, 8: 40, 8.5: 40.5, 9: 41, 9.5: 41.5,
        10: 42, 10.5: 42.5, 11: 43, 11.5: 43.5, 12: 44, 12.5: 44.5,
        13: 45, 14: 46, 15: 47, 16: 48,
    }
    US_A_ARG_MUJER = {
        5: 35, 5.5: 35.5, 6: 36, 6.5: 36.5, 7: 37, 7.5: 37.5,
        8: 38, 8.5: 38.5, 9: 39, 9.5: 39.5, 10: 40, 10.5: 40.5,
        11: 41, 11.5: 41.5,
    }

    # Buscar código RBK
    m_codigo = re.search(r'(RBK\d{10,14})', texto, re.IGNORECASE)
    codigo_rbk = m_codigo.group(1) if m_codigo else ""

    # Buscar M{pares} {ini}/{fin}
    m_talles = re.search(r'M(\d+)\s+(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)', texto)
    total_pares = 0
    talle_ini = 0.0
    talle_fin = 0.0
    if m_talles:
        total_pares = int(m_talles.group(1))
        talle_ini = float(m_talles.group(2).replace(",", "."))
        talle_fin = float(m_talles.group(3).replace(",", "."))

    # Buscar EAN parcial
    m_ean = re.search(r'\((\d{8,13})\)', texto)
    ean = m_ean.group(1) if m_ean else ""

    # Buscar precio unitario
    precios = re.findall(r'(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})', texto)
    precio_unit = 0
    bonif = 0

    if precios:
        valores = []
        for p in precios:
            try:
                v = float(p.replace(".", "").replace(",", "."))
                valores.append(v)
            except ValueError:
                continue
        if valores:
            unitarios = [v for v in valores if 1000 < v < 500000]
            if unitarios:
                precio_unit = min(unitarios)

    # Buscar bonificación
    m_bonif = re.search(r'(\d+[.,]\d+)\s*%?\s*(?:Bonif|bonif|desc)', texto, re.IGNORECASE)
    if not m_bonif:
        m_bonif = re.search(r'%Bonif.*?(\d+[.,]\d+)', texto, re.IGNORECASE)
    if m_bonif:
        bonif = float(m_bonif.group(1).replace(",", "."))

    # Buscar descripción y color
    m_desc = re.search(
        r'([A-Z][A-Z0-9\s.]+?)\s*[-–]\s*([A-Z]{3,}/[A-Z]{3,}(?:/[A-Z]{3,})?)',
        texto, re.IGNORECASE
    )
    desc_modelo = ""
    color_code = ""
    if m_desc:
        desc_modelo = m_desc.group(1).strip()
        color_code = m_desc.group(2).strip()

    # Traducir color a español
    color_es = traducir_color_reebok(color_code) if color_code else ""

    # Construir descripciones MacroGest
    desc_1_base = f"{desc_modelo} {color_es} {SUFIJO_TIPO}".strip()[:160]
    desc_3 = f"{desc_modelo} {SUFIJO_TIPO}".strip()[:90]
    desc_4 = color_es[:90]

    # Buscar "Pares:" como validación
    m_pares = re.search(r'Pares:\s*(\d+)', texto)
    if m_pares and total_pares == 0:
        total_pares = int(m_pares.group(1))

    if not total_pares or not precio_unit:
        log.warning(f"No se pudo extraer datos suficientes: pares={total_pares}, precio={precio_unit}")
        return

    # Generar talles
    talles_us = []
    if talle_ini and talle_fin:
        t = talle_ini
        while t <= talle_fin:
            talles_us.append(t)
            t += 1
            if len(talles_us) > 20:
                break
        if len(talles_us) != total_pares:
            talles_us = []
            t = talle_ini
            while t <= talle_fin:
                talles_us.append(t)
                t += 0.5
                if len(talles_us) > 30:
                    break

    if not talles_us:
        talles_us = [0]

    # Auto-detectar hombre/mujer: talle_ini <= 6 → mujer
    es_mujer = talle_ini <= 6

    pares_por_talle = max(1, total_pares // len(talles_us)) if talles_us else total_pares
    resto = total_pares - (pares_por_talle * len(talles_us)) if talles_us else 0

    def _format_talle(talle_raw) -> str:
        """Formatea talle: entero como '41', medio punto como '41½'."""
        if isinstance(talle_raw, float) and talle_raw != int(talle_raw):
            return f"{int(talle_raw)}½"
        return str(int(talle_raw)) if isinstance(talle_raw, (int, float)) else str(talle_raw)

    for idx, talle_us in enumerate(talles_us):
        if talle_us == 0:
            talle_str = ""
        elif es_mujer:
            talle_raw = US_A_ARG_MUJER.get(talle_us, talle_us + 30)
            talle_str = _format_talle(talle_raw)
        else:
            talle_raw = US_A_ARG_HOMBRE.get(talle_us, talle_us + 32)
            talle_str = _format_talle(talle_raw)

        cant = pares_por_talle + (1 if idx < resto else 0)
        if cant > 0:
            desc_5 = talle_str
            linea_ocr = LineaOCR(
                codigo_producto=codigo_rbk,
                descripcion=desc_1_base,
                color=color_es,
                talle=desc_5,
                cantidad=cant,
                precio_unitario=precio_unit,
                precio_total=round(cant * precio_unit, 2),
                codigo_barra=ean,
                descuento=bonif,
                descripcion_1=desc_1_base,
                descripcion_2="",
                descripcion_3=desc_3,
                descripcion_4=desc_4,
                descripcion_5=desc_5,
            )
            factura.lineas.append(linea_ocr)

    log.info(f"Distrinando flexible: {len(factura.lineas)} líneas, {total_pares} pares")


def parsear_wake(texto: str, factura: FacturaOCR):
    """Parser específico para facturas de Wake (Industrias AS S.A.)."""
    factura.proveedor = "INDUSTRIAS AS S.A."

    # Wake usa formato:
    # Código EAN + WKC215 V26 MOD.YOUTH NEGRO + Pack info
    # Detalle de Talles/Curva: 31 AL 36 X15 2,3,3,3,2,2

    lineas_texto = texto.split('\n')
    i = 0
    current_art = None

    while i < len(lineas_texto):
        linea = lineas_texto[i].strip()

        # Buscar línea de artículo Wake: contiene WKC o WK seguido de modelo
        m_wk = re.search(r'(WKC?\d{3})\s+(V\d+\s+)?(?:MOD\.?\s*)?(\w+)\s+(NEGRO|NUDE|BLANCO|GRIS|AZUL|ROJO)',
                         linea, re.IGNORECASE)
        if m_wk:
            modelo = m_wk.group(1)
            variante = (m_wk.group(2) or "").strip()
            tipo = m_wk.group(3)
            color = m_wk.group(4).upper()

            # Buscar precio en la misma línea
            precios = re.findall(r'([\d\.,]+)\s*$', linea)
            precio = 0
            if precios:
                p = precios[-1].replace(".", "").replace(",", ".")
                try:
                    precio = float(p)
                except ValueError:
                    pass

            current_art = {
                "modelo": modelo,
                "variante": f"{variante} {tipo}".strip(),
                "color": color,
                "precio": precio,
            }

        # Buscar curva de talles
        m_curva = re.search(r'(\d+)\s*AL\s*(\d+)\s*X\s*(\d+)\s+([\d,\s]+)', linea, re.IGNORECASE)
        if m_curva and current_art:
            talle_ini = int(m_curva.group(1))
            talle_fin = int(m_curva.group(2))
            total_pares = int(m_curva.group(3))
            curva_str = m_curva.group(4).strip()
            curva = [int(x.strip()) for x in curva_str.split(",") if x.strip().isdigit()]

            talles = list(range(talle_ini, talle_fin + 1))

            if len(curva) == len(talles):
                for t, c in zip(talles, curva):
                    if c > 0:
                        linea_ocr = LineaOCR(
                            codigo_producto=current_art["modelo"],
                            descripcion=f"{current_art['modelo']} {current_art['variante']} {current_art['color']}",
                            color=current_art["color"],
                            talle=str(t),
                            cantidad=c,
                            precio_unitario=current_art["precio"] / total_pares if total_pares > 0 else 0,
                        )
                        factura.lineas.append(linea_ocr)

            current_art = None

        i += 1


def parsear_generico(texto: str, factura: FacturaOCR):
    """Parser genérico — intenta extraer cualquier patrón tabular."""
    lineas_texto = texto.split('\n')
    for linea in lineas_texto:
        linea = linea.strip()
        if not linea or len(linea) < 10:
            continue

        # Buscar patrón: algo que tenga un número (cantidad) y un precio
        m = re.match(r'^(.+?)\s+(\d+)\s+[\$]?\s*([\d\.,]+)\s+[\$]?\s*([\d\.,]+)$', linea)
        if m:
            desc = m.group(1).strip()
            cant = int(m.group(2))
            precio_u = float(m.group(3).replace(".", "").replace(",", "."))
            precio_t = float(m.group(4).replace(".", "").replace(",", "."))

            if cant > 0 and precio_u > 100:  # filtrar ruido
                linea_ocr = LineaOCR(
                    descripcion=desc,
                    cantidad=cant,
                    precio_unitario=precio_u,
                    precio_total=precio_t,
                )
                factura.lineas.append(linea_ocr)


def parsear_factura_archivo(file_bytes: bytes, filename: str = "") -> FacturaOCR:
    """
    Parsea cualquier tipo de archivo: PDF, JPG, PNG, HEIC.
    Detecta formato por nombre o magic bytes.
    """
    nombre = filename.lower()
    if nombre.endswith(".pdf") or file_bytes[:5] == b"%PDF-":
        return parsear_pdf_factura(file_bytes)
    else:
        # Es imagen: JPG, PNG, HEIC, etc.
        texto = extraer_texto_imagen(file_bytes)
        factura = FacturaOCR(texto_crudo=texto, paginas=1)
        parsear_cabecera(texto, factura)
        proveedor = detectar_proveedor(texto)
        log.info(f"Proveedor detectado (imagen): {proveedor}")
        if proveedor == "DISTRINANDO":
            parsear_distrinando(texto, factura)
        elif proveedor == "WAKE":
            parsear_wake(texto, factura)
        else:
            parsear_generico(texto, factura)
        log.info(f"Líneas extraídas: {len(factura.lineas)} | Total: ${factura.total:,.2f}")
        return factura


def parsear_pdf_factura(pdf_bytes: bytes) -> FacturaOCR:
    """
    Función principal: recibe bytes del PDF, extrae texto,
    detecta proveedor y parsea los datos.

    Retorna FacturaOCR con todos los datos extraídos.
    """
    texto, paginas = extraer_texto_pdf(pdf_bytes)
    factura = FacturaOCR(texto_crudo=texto, paginas=paginas)

    # Cabecera (proveedor, fecha, número, totales)
    parsear_cabecera(texto, factura)

    # Detectar proveedor y usar parser específico
    proveedor = detectar_proveedor(texto)
    log.info(f"Proveedor detectado: {proveedor} | Páginas: {paginas}")

    if proveedor == "DISTRINANDO":
        parsear_distrinando(texto, factura)
    elif proveedor == "WAKE":
        parsear_wake(texto, factura)
    else:
        parsear_generico(texto, factura)

    log.info(f"Líneas extraídas: {len(factura.lineas)} | Total: ${factura.total:,.2f}")
    return factura


# ── CLI para testing ──
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python ocr_factura.py <archivo.pdf>")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO)

    with open(sys.argv[1], "rb") as f:
        pdf_bytes = f.read()

    factura = parsear_pdf_factura(pdf_bytes)

    print(f"\n{'═'*60}")
    print(f"Proveedor:  {factura.proveedor}")
    print(f"Factura:    {factura.tipo_comprobante} {factura.letra} {factura.numero}")
    print(f"Fecha:      {factura.fecha}")
    print(f"Cliente:    {factura.cliente}")
    print(f"Condición:  {factura.condicion_venta}")
    print(f"Subtotal:   ${factura.subtotal:,.2f}")
    print(f"IVA:        ${factura.iva:,.2f}")
    print(f"Total:      ${factura.total:,.2f}")
    print(f"{'─'*60}")
    print(f"Artículos extraídos: {len(factura.lineas)}")
    for i, l in enumerate(factura.lineas, 1):
        print(f"  {i:>3}. [{l.codigo_producto}] {l.descripcion[:45]} "
              f"T:{l.talle} x{l.cantidad} ${l.precio_unitario:,.2f}")
    print(f"{'═'*60}")

    # Mostrar texto crudo si se pide con --verbose
    if "--verbose" in sys.argv:
        print("\n── TEXTO CRUDO ──")
        print(factura.texto_crudo)
