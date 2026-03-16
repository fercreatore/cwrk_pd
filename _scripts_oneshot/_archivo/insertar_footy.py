#!/usr/bin/env python3
"""
insertar_footy.py — Alta artículos + Nota de pedido FOOTY LICENCIAS INV 26
=============================================================================
Proveedor: 950 (TIVORY TRADING CO S.A.)
Marca: 139 (FOOTY)
Empresa: H4 → MSGESTION03

Pedido de calzado licencias invierno 2026:
  32 líneas (31 artículos únicos — PFRZ6110 aparece 2 veces)
  552 pares total
  $12,724,800 bruto

Licencias: STITCH, FROZEN, PEPPA, SPIDERMAN, AVENGERS, PAW PATROL, LOTSO

Líneas de producto:
  PRO     $31,200 — zapatilla deportiva c/luz LED, EVA ultraliviana
  PLUS    $24,900 — zapatilla sublimada c/luz, abrojo+elástico
  MODA    $34,900 — zapatilla urbana toalla bordada, cordones
  POP     $19,900 — zapatilla textil c/luz, abrojo+elástico
  PANTUFLA $14,900-$17,500 — pantufla sintética, suela antideslizante

Condiciones: 90 días | 10% desc contado 10 días

EJECUTAR EN EL 111:
  py -3 insertar_footy.py                ← dry-run
  py -3 insertar_footy.py --ejecutar     ← escribe en producción
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONN_COMPRAS

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════

PROVEEDOR    = 950
DENOMINACION = "TIVORY TRADING CO S.A."
EMPRESA      = "H4"
MARCA        = 139       # FOOTY (en tabla marcas)
LINEA        = 2         # Invierno

FECHA_PEDIDO  = date(2026, 2, 20)   # fecha del pedido original
FECHA_ENTREGA = date(2026, 5, 15)   # entrega estimada

# Descuento contado 10 días = 10%
DESC_CONTADO = 10.0

# Utilidades estándar FOOTY calzado (de artículos existentes prov 950)
UTILIDAD_1 = 100    # contado
UTILIDAD_2 = 124    # lista
UTILIDAD_3 = 60     # intermedio
UTILIDAD_4 = 45     # mayorista
FORMULA    = 1

OBSERVACIONES = ("Pedido FOOTY Licencias INV 2026. "
                 "TIVORY TRADING CO S.A. 32 líneas, 552 pares, $12,724,800. "
                 "Cond: 90 días, 10% desc ctdo 10 días.")


# ══════════════════════════════════════════════════════════════
# MODELOS — 31 artículos únicos (PFRZ6110 con cantidades dobladas)
# ══════════════════════════════════════════════════════════════
#
# rubro: 4=NIÑOS, 5=NIÑAS
# subrubro: 49=Zapatillas, 60=Pantuflas
# grupo: "17"=nenas, "5"=nenes
#
# Para pantuflas binumerales: se usa siempre el talle MAYOR del par
# (25/26 → "26", 27/28 → "28", etc.) — convención estándar del negocio
# Para zapatillas: talles simples ("22", "23", etc.)

MODELOS = [
    # ── PEPPA (rubro 5 = nenas) ──────────────────────────────
    {
        "art_code": "PPX3941", "color": "LILA",
        "licencia": "PEPPA", "linea_footy": "PLUS",
        "desc_corta": "ZAPA SUBLIM C/LUZ",
        "rubro": 5, "subrubro": 49, "grupo": "17",
        "precio": 24900, "es_pantufla": False,
        "talles": [("22", 3), ("23", 4), ("24", 4), ("25", 4), ("26", 3)],
    },
    {
        "art_code": "PPX938", "color": "ROSA",
        "licencia": "PEPPA", "linea_footy": "PRO",
        "desc_corta": "ZAPA DEP C/LUZ",
        "rubro": 5, "subrubro": 49, "grupo": "17",
        "precio": 31200, "es_pantufla": False,
        "talles": [("22", 2), ("23", 3), ("24", 3), ("25", 2), ("26", 2)],
    },
    {
        "art_code": "PPX942", "color": "ROSA",
        "licencia": "PEPPA", "linea_footy": "PRO",
        "desc_corta": "ZAPA DEP C/LUZ",
        "rubro": 5, "subrubro": 49, "grupo": "17",
        "precio": 31200, "es_pantufla": False,
        "talles": [("22", 2), ("23", 3), ("24", 3), ("25", 2), ("26", 2)],
    },
    {
        "art_code": "PPX5947", "color": "ROSA",
        "licencia": "PEPPA", "linea_footy": "PRO",
        "desc_corta": "ZAPA DEP C/LUZ",
        "rubro": 5, "subrubro": 49, "grupo": "17",
        "precio": 31200, "es_pantufla": False,
        "talles": [("22", 2), ("23", 3), ("24", 3), ("25", 2), ("26", 2)],
    },
    {
        "art_code": "PPX3953", "color": "ROSA",
        "licencia": "PEPPA", "linea_footy": "PLUS",
        "desc_corta": "ZAPA SUBLIM C/LUZ",
        "rubro": 5, "subrubro": 49, "grupo": "17",
        "precio": 24900, "es_pantufla": False,
        "talles": [("22", 3), ("23", 4), ("24", 4), ("25", 4), ("26", 3)],
    },
    {
        "art_code": "PPP6123", "color": "ROSA",
        "licencia": "PEPPA", "linea_footy": "PANTUFLA",
        "desc_corta": "PANTUFLA",
        "rubro": 5, "subrubro": 60, "grupo": "17",
        "precio": 14900, "es_pantufla": True,
        "talles": [("26", 6), ("28", 6), ("30", 6), ("32", 6)],
    },
    {
        "art_code": "PPP6124", "color": "ROSA",
        "licencia": "PEPPA", "linea_footy": "PANTUFLA",
        "desc_corta": "PANTUFLA",
        "rubro": 5, "subrubro": 60, "grupo": "17",
        "precio": 14900, "es_pantufla": True,
        "talles": [("26", 6), ("28", 6), ("30", 6), ("32", 6)],
    },

    # ── PAW PATROL (rubro 4 = nenes) ─────────────────────────
    {
        "art_code": "PWX3585", "color": "GRIS",
        "licencia": "PAW PATROL", "linea_footy": "PLUS",
        "desc_corta": "ZAPA SUBLIM C/LUZ",
        "rubro": 4, "subrubro": 49, "grupo": "5",
        "precio": 24900, "es_pantufla": False,
        "talles": [("23", 3), ("24", 3), ("25", 3), ("26", 3), ("27", 3), ("28", 3)],
    },

    # ── STITCH (rubro 5 = nenas) ─────────────────────────────
    {
        "art_code": "ST2898", "color": "CELESTE",
        "licencia": "STITCH", "linea_footy": "MODA",
        "desc_corta": "ZAPA TOALLA",
        "rubro": 5, "subrubro": 49, "grupo": "17",
        "precio": 34900, "es_pantufla": False,
        "talles": [("30", 2), ("31", 2), ("32", 2), ("33", 2), ("34", 2), ("35", 1), ("36", 1)],
    },
    {
        "art_code": "ST2897", "color": "CELESTE",
        "licencia": "STITCH", "linea_footy": "MODA",
        "desc_corta": "ZAPA TOALLA",
        "rubro": 5, "subrubro": 49, "grupo": "17",
        "precio": 34900, "es_pantufla": False,
        "talles": [("30", 2), ("31", 2), ("32", 2), ("33", 2), ("34", 2), ("35", 1), ("36", 1)],
    },
    {
        "art_code": "ST3891", "color": "CELESTE",
        "licencia": "STITCH", "linea_footy": "PLUS",
        "desc_corta": "ZAPA SUBLIM C/LUZ",
        "rubro": 5, "subrubro": 49, "grupo": "17",
        "precio": 24900, "es_pantufla": False,
        "talles": [("25", 3), ("26", 3), ("27", 3), ("28", 3), ("29", 3), ("30", 3)],
    },
    {
        "art_code": "ST3889", "color": "CELESTE",
        "licencia": "STITCH", "linea_footy": "PLUS",
        "desc_corta": "ZAPA SUBLIM C/LUZ",
        "rubro": 5, "subrubro": 49, "grupo": "17",
        "precio": 24900, "es_pantufla": False,
        "talles": [("25", 3), ("26", 3), ("27", 3), ("28", 3), ("29", 3), ("30", 3)],
    },
    {
        "art_code": "ST5877", "color": "CELESTE",
        "licencia": "STITCH", "linea_footy": "PRO",
        "desc_corta": "ZAPA DEP C/LUZ",
        "rubro": 5, "subrubro": 49, "grupo": "17",
        "precio": 31200, "es_pantufla": False,
        "talles": [("25", 2), ("26", 2), ("27", 2), ("28", 2), ("29", 2), ("30", 2)],
    },
    {
        "art_code": "ST881", "color": "CELESTE",
        "licencia": "STITCH", "linea_footy": "PRO",
        "desc_corta": "ZAPA DEP C/LUZ",
        "rubro": 5, "subrubro": 49, "grupo": "17",
        "precio": 31200, "es_pantufla": False,
        "talles": [("25", 2), ("26", 2), ("27", 2), ("28", 2), ("29", 2), ("30", 2)],
    },
    {
        "art_code": "ST879", "color": "CELESTE",
        "licencia": "STITCH", "linea_footy": "PRO",
        "desc_corta": "ZAPA DEP C/LUZ",
        "rubro": 5, "subrubro": 49, "grupo": "17",
        "precio": 31200, "es_pantufla": False,
        "talles": [("25", 2), ("26", 2), ("27", 2), ("28", 2), ("29", 2), ("30", 2)],
    },
    # Pantuflas STITCH
    {
        "art_code": "PST6113", "color": "CELESTE",
        "licencia": "STITCH", "linea_footy": "PANTUFLA",
        "desc_corta": "PANTUFLA",
        "rubro": 5, "subrubro": 60, "grupo": "17",
        "precio": 17500, "es_pantufla": True,
        "talles": [("26", 4), ("28", 4), ("30", 4), ("32", 4), ("34", 4), ("36", 4)],
    },
    {
        "art_code": "PST6115", "color": "CELESTE",
        "licencia": "STITCH", "linea_footy": "PANTUFLA",
        "desc_corta": "PANTUFLA",
        "rubro": 5, "subrubro": 60, "grupo": "17",
        "precio": 17500, "es_pantufla": True,
        "talles": [("28", 4), ("30", 4), ("32", 4), ("34", 4), ("36", 4), ("38", 4)],
    },
    {
        "art_code": "PST6116", "color": "ROSA",
        "licencia": "STITCH", "linea_footy": "PANTUFLA",
        "desc_corta": "PANTUFLA",
        "rubro": 5, "subrubro": 60, "grupo": "17",
        "precio": 17500, "es_pantufla": True,
        "talles": [("28", 4), ("30", 4), ("32", 4), ("34", 4), ("36", 4), ("38", 4)],
    },

    # ── FROZEN (rubro 5 = nenas) ─────────────────────────────
    {
        "art_code": "FRZ3152", "color": "LILA",
        "licencia": "FROZEN", "linea_footy": "PLUS",
        "desc_corta": "ZAPA SUBLIM C/LUZ",
        "rubro": 5, "subrubro": 49, "grupo": "17",
        "precio": 24900, "es_pantufla": False,
        "talles": [("23", 3), ("24", 3), ("25", 3), ("26", 3), ("27", 3), ("28", 3)],
    },
    # Pantufla FROZEN — PFRZ6110 aparece 2 veces en pedido (2 tareas = 48 pares)
    {
        "art_code": "PFRZ6110", "color": "LILA",
        "licencia": "FROZEN", "linea_footy": "PANTUFLA",
        "desc_corta": "PANTUFLA",
        "rubro": 5, "subrubro": 60, "grupo": "17",
        "precio": 14900, "es_pantufla": True,
        # 2 tareas × (6,6,6,6) = (12,12,12,12) = 48 pares
        "talles": [("26", 12), ("28", 12), ("30", 12), ("32", 12)],
    },

    # ── LOTSO (rubro 5 = nenas) ──────────────────────────────
    {
        "art_code": "LT2451", "color": "ROSA",
        "licencia": "LOTSO", "linea_footy": "MODA",
        "desc_corta": "ZAPA TOALLA",
        "rubro": 5, "subrubro": 49, "grupo": "17",
        "precio": 34900, "es_pantufla": False,
        "talles": [("26", 1), ("27", 1), ("28", 2), ("29", 2), ("30", 2), ("31", 2), ("32", 2)],
    },

    # ── SPIDERMAN (rubro 4 = nenes) ──────────────────────────
    {
        "art_code": "SP5613", "color": "ROJO",
        "licencia": "SPIDERMAN", "linea_footy": "PRO",
        "desc_corta": "ZAPA DEP C/LUZ",
        "rubro": 4, "subrubro": 49, "grupo": "5",
        "precio": 31200, "es_pantufla": False,
        "talles": [("24", 2), ("25", 2), ("26", 2), ("27", 2), ("28", 2), ("29", 1), ("30", 1)],
    },
    {
        "art_code": "SP5612", "color": "ROJO",
        "licencia": "SPIDERMAN", "linea_footy": "PRO",
        "desc_corta": "ZAPA DEP C/LUZ",
        "rubro": 4, "subrubro": 49, "grupo": "5",
        "precio": 31200, "es_pantufla": False,
        "talles": [("24", 2), ("25", 2), ("26", 2), ("27", 2), ("28", 2), ("29", 1), ("30", 1)],
    },
    {
        "art_code": "SP5690", "color": "ROJO",
        "licencia": "SPIDERMAN", "linea_footy": "PRO",
        "desc_corta": "ZAPA DEP C/LUZ",
        "rubro": 4, "subrubro": 49, "grupo": "5",
        "precio": 31200, "es_pantufla": False,
        "talles": [("24", 2), ("25", 2), ("26", 2), ("27", 2), ("28", 2), ("29", 1), ("30", 1)],
    },
    {
        "art_code": "SP3696", "color": "ROJO",
        "licencia": "SPIDERMAN", "linea_footy": "PLUS",
        "desc_corta": "ZAPA SUBLIM C/LUZ",
        "rubro": 4, "subrubro": 49, "grupo": "5",
        "precio": 24900, "es_pantufla": False,
        "talles": [("25", 3), ("26", 3), ("27", 3), ("28", 3), ("29", 3), ("30", 3)],
    },
    {
        "art_code": "SP3695", "color": "ROJO",
        "licencia": "SPIDERMAN", "linea_footy": "PLUS",
        "desc_corta": "ZAPA SUBLIM C/LUZ",
        "rubro": 4, "subrubro": 49, "grupo": "5",
        "precio": 24900, "es_pantufla": False,
        "talles": [("25", 3), ("26", 3), ("27", 3), ("28", 3), ("29", 3), ("30", 3)],
    },
    {
        "art_code": "SP3697", "color": "ROJO",
        "licencia": "SPIDERMAN", "linea_footy": "PLUS",
        "desc_corta": "ZAPA SUBLIM C/LUZ",
        "rubro": 4, "subrubro": 49, "grupo": "5",
        "precio": 24900, "es_pantufla": False,
        "talles": [("25", 3), ("26", 3), ("27", 3), ("28", 3), ("29", 3), ("30", 3)],
    },
    {
        "art_code": "SP0689", "color": "ROJO",
        "licencia": "SPIDERMAN", "linea_footy": "POP",
        "desc_corta": "ZAPA TEXTIL C/LUZ",
        "rubro": 4, "subrubro": 49, "grupo": "5",
        "precio": 19900, "es_pantufla": False,
        "talles": [("25", 3), ("26", 3), ("27", 3), ("28", 3), ("29", 3), ("30", 3)],
    },
    # Pantuflas SPIDERMAN
    {
        "art_code": "PSP6118", "color": "ROJO",
        "licencia": "SPIDERMAN", "linea_footy": "PANTUFLA",
        "desc_corta": "PANTUFLA",
        "rubro": 4, "subrubro": 60, "grupo": "5",
        "precio": 14900, "es_pantufla": True,
        "talles": [("26", 4), ("28", 4), ("30", 4), ("32", 4), ("34", 4), ("36", 4)],
    },
    {
        "art_code": "PSP6119", "color": "ROJO",
        "licencia": "SPIDERMAN", "linea_footy": "PANTUFLA",
        "desc_corta": "PANTUFLA",
        "rubro": 4, "subrubro": 60, "grupo": "5",
        "precio": 17500, "es_pantufla": True,
        "talles": [("26", 4), ("28", 4), ("30", 4), ("32", 4), ("34", 4), ("36", 4)],
    },

    # ── AVENGERS (rubro 4 = nenes) ───────────────────────────
    {
        "art_code": "AV0455", "color": "SURTIDO",
        "licencia": "AVENGERS", "linea_footy": "PRO",
        "desc_corta": "ZAPA DEP C/LUZ",
        "rubro": 4, "subrubro": 49, "grupo": "5",
        "precio": 19900, "es_pantufla": False,
        "talles": [("26", 2), ("27", 2), ("28", 2), ("29", 2), ("30", 2), ("31", 1), ("32", 1)],
    },
]


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

# Tabla de colores FOOTY (extraída de artículos existentes en BD)
COLOR_CODES = {
    "NEGRO":    "00",
    "BLANCO":   "01",
    "AZUL":     "02",
    "ROJO":     "04",
    "LILA":     "06",
    "VIOLETA":  "06",
    "FUCSIA":   "07",
    "GRIS":     "13",
    "PLATA":    "13",
    "ROSA":     "19",
    "CELESTE":  "28",
    "SURTIDO":  "51",
}


def generar_sinonimo(art_code, color, talle):
    """
    Genera codigo_sinonimo de 12 chars, formato FOOTY estándar:
    950 + art_num (5 dígitos) + color (2 dígitos) + talle (2 dígitos)

    Ejemplo: PPX3941 LILA T22 → 950039410622
    """
    import re
    # Extraer parte numérica del código de artículo
    nums = re.findall(r'\d+', art_code)
    art_num = int("".join(nums)) if nums else 0
    art_str = f"{art_num:05d}"[-5:]   # últimos 5 dígitos

    # Código de color
    cc = COLOR_CODES.get(color.upper().strip(), "00")

    # Talle (2 dígitos)
    tt = f"{int(talle):02d}"

    return f"950{art_str}{cc}{tt}"


def construir_desc1(art_code, color, desc_corta, licencia):
    """desc1: ART COLOR TIPO LICENCIA FOOTY (max ~60 chars)."""
    return f"{art_code} {color} {desc_corta} {licencia}"[:60]


def construir_desc3(art_code, desc_corta, licencia):
    """desc3: ART TIPO LICENCIA FOOTY (sin color)."""
    return f"{art_code} {desc_corta} {licencia} FOOTY"[:40]


# ══════════════════════════════════════════════════════════════
# FASE 1: ALTA DE ARTÍCULOS
# ══════════════════════════════════════════════════════════════

def fase1_alta_articulos(dry_run=True):
    """Crea todos los artículos FOOTY licencias usando dar_de_alta()."""
    from paso2_buscar_articulo import dar_de_alta

    modo = "DRY RUN" if dry_run else "EJECUCIÓN REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 1: ALTA DE ARTÍCULOS FOOTY LICENCIAS INV 26 — {modo}")
    print(f"{'='*70}")

    articulos_creados = {}
    total = 0
    errores = 0

    for modelo in MODELOS:
        art_code = modelo["art_code"]
        color = modelo["color"]
        licencia = modelo["licencia"]
        linea_f = modelo["linea_footy"]
        precio = modelo["precio"]
        n_talles = len(modelo["talles"])
        n_pares = sum(c for _, c in modelo["talles"])

        print(f"\n  {art_code} {color} — {licencia} {linea_f} — "
              f"{n_talles} talles, {n_pares} pares @ ${precio:,}")

        # Precio costo = precio sin descuento (desc contado se aplica al pagar)
        precio_costo = precio

        for talle, cant in modelo["talles"]:
            desc1 = construir_desc1(art_code, color, modelo["desc_corta"], licencia)
            desc3 = construir_desc3(art_code, modelo["desc_corta"], licencia)
            desc4 = color
            desc5 = talle
            sinonimo = generar_sinonimo(art_code, color, talle)

            datos = {
                "descripcion_1":    desc1,
                "descripcion_3":    desc3,
                "descripcion_4":    desc4,
                "descripcion_5":    desc5,
                "codigo_sinonimo":  sinonimo,
                "subrubro":         modelo["subrubro"],
                "marca":            MARCA,
                "linea":            LINEA,
                "rubro":            modelo["rubro"],
                "grupo":            modelo["grupo"],
                "proveedor":        PROVEEDOR,
                "codigo_proveedor": art_code,
                "precio_fabrica":   precio,
                "descuento":        0,
                "descuento_1":      0,
                "descuento_2":      0,
                "precio_costo":     precio_costo,
                "precio_sugerido":  round(precio_costo, 2),
                "utilidad_1":       UTILIDAD_1,
                "utilidad_2":       UTILIDAD_2,
                "utilidad_3":       UTILIDAD_3,
                "utilidad_4":       UTILIDAD_4,
                "precio_1":         round(precio_costo * (1 + UTILIDAD_1 / 100), 2),
                "precio_2":         round(precio_costo * (1 + UTILIDAD_2 / 100), 2),
                "precio_3":         round(precio_costo * (1 + UTILIDAD_3 / 100), 2),
                "precio_4":         round(precio_costo * (1 + UTILIDAD_4 / 100), 2),
                "formula":          FORMULA,
            }

            codigo = dar_de_alta(datos, dry_run=dry_run)
            key = (art_code, talle)
            if codigo and codigo > 0:
                articulos_creados[key] = codigo
                total += 1
            elif codigo == -1:
                # Ya existe
                articulos_creados[key] = -1
                total += 1
            else:
                errores += 1

    print(f"\n  Resumen Fase 1: {total} artículos "
          f"{'simulados' if dry_run else 'creados'}, {errores} errores")
    return articulos_creados


# ══════════════════════════════════════════════════════════════
# FASE 2: INSERTAR NOTA DE PEDIDO
# ══════════════════════════════════════════════════════════════

def fase2_insertar_pedido(articulos_creados, dry_run=True):
    """Inserta la nota de pedido con todos los renglones."""
    from paso4_insertar_pedido import insertar_pedido

    modo = "DRY RUN" if dry_run else "EJECUCIÓN REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 2: NOTA DE PEDIDO FOOTY LICENCIAS INV 26 — {modo}")
    print(f"{'='*70}")

    # Anti-duplicado
    if not dry_run:
        import pyodbc as _pyo
        _c = _pyo.connect(CONN_COMPRAS)
        _cur = _c.cursor()
        _cur.execute(
            "SELECT numero FROM MSGESTION03.dbo.pedico2 "
            "WHERE codigo=8 AND cuenta=950 AND observaciones LIKE '%FOOTY Licencias INV 2026%'"
        )
        _dup = _cur.fetchone()
        _c.close()
        if _dup:
            print(f"  ⚠️  YA EXISTE pedido FOOTY INV 2026 → #{_dup[0]}")
            print(f"  → SALTANDO para evitar duplicado")
            return _dup[0]

    cabecera = {
        "empresa":           EMPRESA,
        "cuenta":            PROVEEDOR,
        "denominacion":      DENOMINACION,
        "fecha_comprobante": FECHA_PEDIDO,
        "fecha_entrega":     FECHA_ENTREGA,
        "observaciones":     OBSERVACIONES,
    }

    renglones = []
    for modelo in MODELOS:
        art_code = modelo["art_code"]
        color = modelo["color"]
        licencia = modelo["licencia"]

        for talle, cant in modelo["talles"]:
            key = (art_code, talle)
            codigo = articulos_creados.get(key)
            if not codigo:
                print(f"  ⚠️  Sin código para {art_code} T{talle} — saltando")
                continue

            desc = construir_desc1(art_code, color, modelo["desc_corta"], licencia)

            renglones.append({
                "articulo":        codigo if codigo > 0 else 0,
                "descripcion":     desc[:60],
                "codigo_sinonimo": "",
                "cantidad":        cant,
                "precio":          modelo["precio"],
            })

    total_pares = sum(r["cantidad"] for r in renglones)
    total_bruto = sum(r["cantidad"] * r["precio"] for r in renglones)

    print(f"  Renglones: {len(renglones)}")
    print(f"  Total pares: {total_pares}")
    print(f"  Total bruto: ${total_bruto:,.0f}")

    if renglones:
        num = insertar_pedido(cabecera, renglones, dry_run=dry_run)
        print(f"  → Pedido FOOTY: número {num}")
        return num
    else:
        print(f"  ⚠️  No hay renglones para insertar")
        return None


# ══════════════════════════════════════════════════════════════
# VERIFICACIÓN
# ══════════════════════════════════════════════════════════════

def verificar_totales():
    """Verifica que los totales del script coincidan con el pedido Excel."""
    print(f"\n{'='*70}")
    print(f"  VERIFICACIÓN DE TOTALES")
    print(f"{'='*70}")

    total_pares = 0
    total_bruto = 0
    total_articulos = 0
    total_modelos = len(MODELOS)

    por_licencia = {}

    for m in MODELOS:
        pares_modelo = sum(c for _, c in m["talles"])
        bruto_modelo = pares_modelo * m["precio"]
        arts_modelo = len(m["talles"])

        total_pares += pares_modelo
        total_bruto += bruto_modelo
        total_articulos += arts_modelo

        lic = m["licencia"]
        if lic not in por_licencia:
            por_licencia[lic] = {"pares": 0, "bruto": 0, "modelos": 0}
        por_licencia[lic]["pares"] += pares_modelo
        por_licencia[lic]["bruto"] += bruto_modelo
        por_licencia[lic]["modelos"] += 1

    print(f"\n  Por licencia:")
    for lic, d in sorted(por_licencia.items()):
        print(f"    {lic:15s}  {d['modelos']:>2d} modelos  {d['pares']:>4d} pares  ${d['bruto']:>12,.0f}")

    print(f"\n  Total modelos:    {total_modelos}")
    print(f"  Total artículos:  {total_articulos} (cada talle = 1 artículo)")
    print(f"  Total pares:      {total_pares}")
    print(f"  Total bruto:      ${total_bruto:,.0f}")

    # Verificar contra Excel
    PARES_EXCEL = 552
    BRUTO_EXCEL = 12724800

    ok_pares = total_pares == PARES_EXCEL
    ok_bruto = total_bruto == BRUTO_EXCEL

    print(f"\n  ✅ Pares:  {total_pares} vs Excel {PARES_EXCEL} → {'OK' if ok_pares else '❌ DIFERENCIA'}")
    print(f"  ✅ Bruto:  ${total_bruto:,.0f} vs Excel ${BRUTO_EXCEL:,.0f} → {'OK' if ok_bruto else '❌ DIFERENCIA'}")

    if not ok_pares or not ok_bruto:
        print(f"\n  ⚠️  HAY DIFERENCIAS — revisar datos antes de ejecutar")
        return False
    return True


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

def main():
    dry_run = "--ejecutar" not in sys.argv

    if dry_run:
        print("=" * 70)
        print("  MODO DRY-RUN — No se escribe nada en la BD")
        print("  Agregar --ejecutar para escribir de verdad")
        print("=" * 70)
    else:
        print("=" * 70)
        print("  ⚠️  MODO EJECUCIÓN REAL — SE VA A ESCRIBIR EN LA BD")
        print("=" * 70)

    # Verificar totales primero
    if not verificar_totales():
        print("\n  ❌ Totales no coinciden — abortando")
        sys.exit(1)

    # Fase 1: Alta de artículos
    arts = fase1_alta_articulos(dry_run=dry_run)

    # Fase 2: Nota de pedido
    if arts:
        fase2_insertar_pedido(arts, dry_run=dry_run)
    else:
        print("\n  ❌ No se crearon artículos — no se puede crear pedido")

    print(f"\n{'='*70}")
    print(f"  {'DRY-RUN completado' if dry_run else 'EJECUCIÓN completada'}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
