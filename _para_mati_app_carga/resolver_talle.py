# resolver_talle.py
# Módulo que encadena las 3 capas del sistema de talles para normalización.
#
# Capa 1: equivalencias_talles       → tabla maestra AR↔EU↔US↔UK↔BR↔cm
# Capa 2: aliases_talles             → limpia basura de descripcion_5
# Capa 3: regla_talle_subrubro       → decide tipo_talle y si acepta medio punto
#
# Uso principal:
#   from resolver_talle import resolver_talle, TalleResuelto
#   resultado = resolver_talle("38Ç", subrubro=49)
#   # resultado.normalizado = "38"
#   # resultado.tipo = "CALZADO"
#   # resultado.acepta_mp = True
#   # resultado.equivalencias = {ar:38, eu:38.0, us_h:7.0, us_m:8.5, ...}
#
# También:
#   resultado = resolver_talle("M8", subrubro=47)
#   # resultado.normalizado = "39"  (US mujer 8 → AR 39 por alias)
#
#   resultado = resolver_talle("41½", subrubro=47)
#   # resultado.normalizado = "41.5"  (½ → .5)
#   # resultado.acepta_mp = True (running acepta medio punto)
#
# Cache: las tablas se leen UNA vez y se cachean en memoria.
# Para refrescar: resolver_talle.invalidar_cache()
#
# EJECUTAR en: 111 (producción) o Mac (con pyodbc al 111)
# Requiere: las 3 tablas creadas por crear_equivalencias_calzado_iram.sql
#           y fix_capas_2_y_3.sql

import logging
from dataclasses import dataclass, field
from typing import Optional

import pyodbc

from config import CONN_COMPRAS

log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# DATACLASS DE RESULTADO
# ══════════════════════════════════════════════════════════════

@dataclass
class Equivalencias:
    """Equivalencias internacionales de un talle AR."""
    talle_ar: Optional[float] = None
    largo_pie_cm: Optional[float] = None
    mondopoint_mm: Optional[int] = None
    talle_eu: Optional[float] = None
    talle_br: Optional[float] = None
    talle_uk: Optional[float] = None
    talle_us_hombre: Optional[float] = None
    talle_us_mujer: Optional[float] = None


@dataclass
class TalleResuelto:
    """Resultado completo de la resolución de un talle."""
    original: str = ""            # lo que vino en descripcion_5 (ej: "38Ç")
    normalizado: str = ""         # talle limpio (ej: "38")
    tipo_talle: str = ""          # CALZADO, INDUMENTARIA, OJOTA, ACCESORIO, etc.
    acepta_mp: bool = False       # si el subrubro acepta medio punto
    subrubro: Optional[int] = None
    resuelto_por: str = ""        # "directo", "alias", "reebok_us", "sin_regla"
    equivalencias: Optional[Equivalencias] = None
    es_valido: bool = True        # False si no se pudo resolver
    advertencia: str = ""         # mensaje de warning si hay algo raro


# ══════════════════════════════════════════════════════════════
# CACHE EN MEMORIA
# ══════════════════════════════════════════════════════════════

_cache_aliases: dict = {}          # {(tipo_talle, alias): talle_resuelto}
_cache_reglas: dict = {}           # {codigo_subrubro: (tipo_talle, acepta_mp)}
_cache_equivalencias: dict = {}    # {talle_ar_float: Equivalencias}
_cache_cargado: bool = False


def invalidar_cache():
    """Fuerza recarga de las tablas en la próxima llamada."""
    global _cache_cargado
    _cache_aliases.clear()
    _cache_reglas.clear()
    _cache_equivalencias.clear()
    _cache_cargado = False
    log.info("Cache de talles invalidado")


def _cargar_cache():
    """Lee las 3 tablas de la DB y las cachea en memoria."""
    global _cache_cargado
    if _cache_cargado:
        return

    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()

            # ── Capa 2: aliases ──
            cursor.execute("""
                SELECT tipo_talle, alias, talle_resuelto
                FROM msgestion01.dbo.aliases_talles
            """)
            for row in cursor.fetchall():
                tipo = row[0].strip().upper()
                alias = row[1].strip()
                resuelto = row[2].strip()
                _cache_aliases[(tipo, alias)] = resuelto
                # También guardar en mayúsculas por si viene variado
                _cache_aliases[(tipo, alias.upper())] = resuelto

            # ── Capa 3: reglas por subrubro ──
            cursor.execute("""
                SELECT codigo_subrubro, tipo_talle, acepta_mp
                FROM msgestion01.dbo.regla_talle_subrubro
            """)
            for row in cursor.fetchall():
                sub = int(row[0])
                tipo = row[1].strip().upper()
                mp = bool(row[2])
                _cache_reglas[sub] = (tipo, mp)

            # ── Capa 1: equivalencias maestras ──
            cursor.execute("""
                SELECT talle_original, largo_pie_cm, mondopoint_mm,
                       talle_eu, talle_br, talle_uk,
                       talle_us_hombre, talle_us_mujer
                FROM msgestion01.dbo.equivalencias_talles
                WHERE tipo_talle = 'CALZADO'
            """)
            for row in cursor.fetchall():
                try:
                    ar = float(row[0])
                except (ValueError, TypeError):
                    continue
                _cache_equivalencias[ar] = Equivalencias(
                    talle_ar=ar,
                    largo_pie_cm=float(row[1]) if row[1] else None,
                    mondopoint_mm=int(row[2]) if row[2] else None,
                    talle_eu=float(row[3]) if row[3] else None,
                    talle_br=float(row[4]) if row[4] else None,
                    talle_uk=float(row[5]) if row[5] else None,
                    talle_us_hombre=float(row[6]) if row[6] else None,
                    talle_us_mujer=float(row[7]) if row[7] else None,
                )

        _cache_cargado = True
        log.info(
            f"Cache talles cargado: {len(_cache_aliases)} aliases, "
            f"{len(_cache_reglas)} reglas, {len(_cache_equivalencias)} equivalencias"
        )

    except Exception as e:
        log.error(f"Error cargando cache de talles: {e}")
        # Si falla, trabajamos sin cache — las funciones usan fallbacks


# ══════════════════════════════════════════════════════════════
# NORMALIZACIÓN DE TEXTO
# ══════════════════════════════════════════════════════════════

def _limpiar_talle_texto(valor: str) -> str:
    """Limpieza básica antes de buscar en aliases."""
    s = str(valor).strip()
    # Reemplazar ½ unicode por .5
    s = s.replace("½", ".5").replace("¹⁄₂", ".5")
    # Quitar espacios internos
    s = s.replace(" ", "")
    return s


def _es_numerico_talle(s: str) -> Optional[float]:
    """Intenta parsear como número. Retorna float o None."""
    try:
        return float(s.replace(",", "."))
    except (ValueError, TypeError):
        return None


# ══════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════

def resolver_talle(
    descripcion_5: str,
    subrubro: Optional[int] = None,
    proveedor: Optional[int] = None,
) -> TalleResuelto:
    """
    Resuelve un talle encadenando las 3 capas.

    Args:
        descripcion_5: valor crudo del campo descripcion_5 del artículo
        subrubro: código de subrubro (para Capa 3: saber tipo_talle)
        proveedor: código de proveedor (para reglas especiales, ej: Reebok)

    Returns:
        TalleResuelto con toda la información normalizada

    Flujo:
        1. Capa 3: subrubro → tipo_talle + acepta_mp
        2. Capa 2: (tipo_talle, descripcion_5) → talle_resuelto (alias)
        3. Si no hay alias → limpiar texto y verificar si es numérico directo
        4. Validar medio punto vs acepta_mp
        5. Capa 1: talle_normalizado → equivalencias internacionales
    """
    _cargar_cache()

    resultado = TalleResuelto(original=str(descripcion_5).strip())
    talle_limpio = _limpiar_talle_texto(descripcion_5)

    if not talle_limpio:
        resultado.es_valido = False
        resultado.advertencia = "descripcion_5 vacío"
        resultado.resuelto_por = "vacio"
        return resultado

    # ── CAPA 3: determinar tipo_talle desde subrubro ──
    tipo_talle = "CALZADO"  # default
    acepta_mp = False

    if subrubro is not None and subrubro in _cache_reglas:
        tipo_talle, acepta_mp = _cache_reglas[subrubro]
        resultado.subrubro = subrubro
    elif subrubro is not None:
        resultado.advertencia = f"Subrubro {subrubro} sin regla en regla_talle_subrubro"
        resultado.resuelto_por = "sin_regla"

    resultado.tipo_talle = tipo_talle
    resultado.acepta_mp = acepta_mp

    # ── CAPA 2: buscar alias ──
    alias_key = (tipo_talle, talle_limpio)
    alias_key_upper = (tipo_talle, talle_limpio.upper())

    talle_normalizado = None

    if alias_key in _cache_aliases:
        talle_normalizado = _cache_aliases[alias_key]
        resultado.resuelto_por = "alias"
    elif alias_key_upper in _cache_aliases:
        talle_normalizado = _cache_aliases[alias_key_upper]
        resultado.resuelto_por = "alias"
    else:
        # No hay alias → intentar directo
        talle_normalizado = talle_limpio
        resultado.resuelto_por = "directo"

    # ── Normalización numérica ──
    num = _es_numerico_talle(talle_normalizado)
    if num is not None:
        # Validar medio punto
        es_medio_punto = (num != int(num))
        if es_medio_punto and not acepta_mp:
            # Subrubro no acepta medio punto → truncar a entero
            talle_normalizado = str(int(num))
            resultado.advertencia = (
                f"Talle {num} tiene medio punto pero subrubro "
                f"{subrubro} no acepta MP → truncado a {int(num)}"
            )
        elif es_medio_punto:
            # Medio punto válido
            talle_normalizado = str(num)
        else:
            # Entero limpio
            talle_normalizado = str(int(num))

        # ── CAPA 1: buscar equivalencias ──
        ar_float = float(talle_normalizado) if _es_numerico_talle(talle_normalizado) else None
        if ar_float and ar_float in _cache_equivalencias:
            resultado.equivalencias = _cache_equivalencias[ar_float]
        elif ar_float and tipo_talle == "CALZADO":
            # Talle numérico válido pero fuera del rango 34-46
            if ar_float < 18 or ar_float > 50:
                resultado.advertencia = (
                    resultado.advertencia or
                    f"Talle {ar_float} fuera del rango calzado (18-50)"
                )

    resultado.normalizado = talle_normalizado
    return resultado


# ══════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES PARA EL PIPELINE
# ══════════════════════════════════════════════════════════════

def talle_para_sinonimo(descripcion_5: str, subrubro: Optional[int] = None) -> str:
    """
    Devuelve el talle como string de 2 dígitos para armar el sinónimo.
    Ej: "38Ç" → "38", "M8" → "39", "41½" → "41" (trunca MP para sinónimo)

    El sinónimo SIEMPRE usa 2 dígitos enteros (posiciones 11-12).
    """
    res = resolver_talle(descripcion_5, subrubro=subrubro)
    num = _es_numerico_talle(res.normalizado)
    if num is not None:
        return str(int(num)).zfill(2)[:2]
    # No numérico (ej: "UNICO", "XL") → "00"
    return "00"


def talle_para_descripcion_5(descripcion_5: str, subrubro: Optional[int] = None) -> str:
    """
    Devuelve el talle normalizado para guardar en descripcion_5.
    A diferencia del sinónimo, acá SÍ puede ir medio punto si el subrubro lo permite.
    Ej: "38Ç" → "38", "38.0" → "38", "41½" (running) → "41.5"
    """
    res = resolver_talle(descripcion_5, subrubro=subrubro)
    return res.normalizado


def obtener_equivalencias(talle_ar: float) -> Optional[Equivalencias]:
    """
    Dado un talle AR numérico, devuelve las equivalencias internacionales.
    Retorna None si no está en la tabla.
    """
    _cargar_cache()
    return _cache_equivalencias.get(talle_ar)


def ar_a_us(talle_ar: float, genero: str = "hombre") -> Optional[float]:
    """Convierte talle AR a US. genero: 'hombre' o 'mujer'."""
    equiv = obtener_equivalencias(talle_ar)
    if equiv:
        return equiv.talle_us_hombre if genero == "hombre" else equiv.talle_us_mujer
    return None


def us_a_ar(talle_us: float, genero: str = "hombre") -> Optional[float]:
    """Convierte talle US a AR. genero: 'hombre' o 'mujer'."""
    _cargar_cache()
    campo = "talle_us_hombre" if genero == "hombre" else "talle_us_mujer"
    for equiv in _cache_equivalencias.values():
        val = getattr(equiv, campo)
        if val is not None and abs(val - talle_us) < 0.01:
            return equiv.talle_ar
    return None


def info_subrubro(codigo_subrubro: int) -> Optional[tuple]:
    """Retorna (tipo_talle, acepta_mp) para un subrubro, o None."""
    _cargar_cache()
    return _cache_reglas.get(codigo_subrubro)


# ══════════════════════════════════════════════════════════════
# CLI PARA TESTING
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    # Casos de prueba
    tests = [
        # (descripcion_5, subrubro, descripcion_caso)
        ("38Ç", 49, "typo con basura → training"),
        ("38.0", 7, "decimal innecesario → mocasín"),
        ("35/36", 60, "talle doble → pantufla"),
        ("M8", 47, "US mujer → running"),
        ("41½", 47, "medio punto → running (acepta)"),
        ("41½", 7, "medio punto → mocasín (NO acepta)"),
        ("41.5", 49, "medio punto decimal → training (acepta)"),
        ("XL", 57, "indumentaria → remera"),
        ("2XL", 61, "alias indumentaria → buzo"),
        ("3/4", 11, "ojota fraccionada"),
        ("U", 10, "talle único → accesorios"),
        ("43", 51, "talle directo → outdoor"),
        ("W6", 47, "Women US 6 → running"),
        ("", 49, "vacío"),
        ("39", None, "sin subrubro"),
        ("39", 999, "subrubro inexistente"),
    ]

    print("=" * 80)
    print("TESTS resolver_talle — 3 Capas")
    print("=" * 80)

    for desc5, sub, caso in tests:
        res = resolver_talle(desc5, subrubro=sub)
        equiv_str = ""
        if res.equivalencias:
            e = res.equivalencias
            equiv_str = f" | EU:{e.talle_eu} US_H:{e.talle_us_hombre} US_M:{e.talle_us_mujer} cm:{e.largo_pie_cm}"

        warn = f" ⚠ {res.advertencia}" if res.advertencia else ""
        print(
            f"  '{desc5}' sub={sub} ({caso})\n"
            f"    → normalizado='{res.normalizado}' tipo={res.tipo_talle} "
            f"mp={res.acepta_mp} por={res.resuelto_por}{equiv_str}{warn}"
        )

    # Test funciones auxiliares
    print("\n" + "=" * 40)
    print("FUNCIONES AUXILIARES")
    print("=" * 40)
    print(f"  talle_para_sinonimo('38Ç', 49) = '{talle_para_sinonimo('38Ç', 49)}'")
    print(f"  talle_para_sinonimo('M8', 47) = '{talle_para_sinonimo('M8', 47)}'")
    print(f"  talle_para_descripcion_5('41½', 47) = '{talle_para_descripcion_5('41½', 47)}'")
    print(f"  talle_para_descripcion_5('41½', 7) = '{talle_para_descripcion_5('41½', 7)}'")

    print(f"\n  ar_a_us(40, 'hombre') = {ar_a_us(40, 'hombre')}")
    print(f"  ar_a_us(38, 'mujer')  = {ar_a_us(38, 'mujer')}")
    print(f"  us_a_ar(9, 'hombre')  = {us_a_ar(9, 'hombre')}")
    print(f"  us_a_ar(8.5, 'mujer') = {us_a_ar(8.5, 'mujer')}")

    print(f"\n  info_subrubro(47) = {info_subrubro(47)}")
    print(f"  info_subrubro(57) = {info_subrubro(57)}")
    print(f"  info_subrubro(11) = {info_subrubro(11)}")

    print("\n✅ Tests completados")
