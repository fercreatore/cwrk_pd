#!/usr/bin/env python3
"""
insertar_lesedife.py — Inserción de 2 pedidos LESEDIFE S.A.
=========================================================================
NP 0000-00466962: Unicross/Amayra/Wilson (187 items, 1293 unidades, 19% desc)
NP 0000-00467731: Disney/Marvel (51 items, 636 unidades, 19% desc)

Empresa: H4 → MSGESTION03
Proveedor: 42 (LESEDIFE S.A.)

ESTADO (12 mar 2026):
  - TODOS los 238 artículos ya existen en la BD (dados de alta por SST manualmente)
  - NO se necesita alta masiva (Fase 1 eliminada)
  - Pedido #1134065 ya tiene 37 renglones (254 pares) de NP466962
  - Faltan 150 renglones (1039 pares) de NP466962 → pedido complementario
  - NP467731 no tiene pedido → pedido nuevo (51 renglones, 636 pares)

PROCESO:
  Fase 0 — FIX: proveedor=NULL (4 arts), descripción (1 art), precios viejos (16+51 arts)
  Fase 1 — INSERT pedido complemento NP466962 (150 renglones, 1039 pares)
  Fase 2 — INSERT pedido nuevo NP467731 (51 renglones, 636 pares)

DESCUENTO: 19% en ambas NPs (confirmado por factura A 0108-00142330).
  NOTA: La factura muestra "Bon. por volumen 50%" pero es FALSO —
  ese 50% es la división interna entre ABI y H4, NO un descuento real.
  → precio_costo = precio_lista × 0.81 (descuento real 19%).

EJECUTAR EN EL 111:
  py -3 insertar_lesedife.py --dry-run     ← solo muestra, no escribe
  py -3 insertar_lesedife.py --ejecutar    ← escribe en producción
"""

import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import pyodbc
from datetime import date, datetime
from config import CONN_COMPRAS, calcular_precios

# ══════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════

PROVEEDOR = 42       # LESEDIFE S.A.
MARCA = 42
EMPRESA = "H4"
BD_BASE = "MSGESTION03"

# Descuento y utilidades: se leen de config.py PROVEEDORES[42]
# (descuento=19%, util1=120%, util2=144%, util3=60%, util4=45%)

# Artículos ya en pedido #1134065 (37 renglones, 254 pares) — NO re-insertar
ARTS_EN_PEDIDO_1134065 = {
    246172, 290994, 311213, 343690, 343729, 344298, 344299, 344301,
    344304, 344305, 344306, 344867, 345037, 351228, 351485, 352842,
    358597, 358598, 359661, 360307, 360308, 360310, 360311, 360312,
    360313, 360314, 360315, 360316, 360317, 360318, 360319, 360320,
    360321, 360322, 360323, 360324, 360325,
}

# ══════════════════════════════════════════════════════════════
# ARTÍCULOS CON PROVEEDOR NULL (necesitan UPDATE proveedor=42)
# ══════════════════════════════════════════════════════════════

ARTS_PROVEEDOR_NULL = [351485, 352842, 358597, 358598]

# ══════════════════════════════════════════════════════════════
# ARTÍCULOS CON DESCRIPCIÓN ERRÓNEA
# ══════════════════════════════════════════════════════════════

FIXES_DESCRIPCION = [
    {
        "codigo": 351485,
        "campo": "descripcion_1",
        "viejo": "67.C3217.1 NEGRO BANDOLERA AMAYRA",
        "nuevo": "67.C3217.1 NEGRO CARTERA AMAYRA",
    },
]

# ══════════════════════════════════════════════════════════════
# ARTÍCULOS CON PRECIO DESACTUALIZADO (NP466962 — arts viejos)
# precio_np es el precio de lista NUEVO de la NP
# ══════════════════════════════════════════════════════════════

PRECIOS_VIEJOS_466 = [
    {"codigo": 311213, "art_prov": "62.P5015",    "precio_np": 6790},
    {"codigo": 345037, "art_prov": "62.T6045",    "precio_np": 4690},
    {"codigo": 344867, "art_prov": "62.T6046",    "precio_np": 4790},
    {"codigo": 246172, "art_prov": "62.T6222",    "precio_np": 11490},
    {"codigo": 290994, "art_prov": "62.T6241",    "precio_np": 3190},
    {"codigo": 351228, "art_prov": "67.C26311R",  "precio_np": 18590},
    {"codigo": 343690, "art_prov": "67.T4016",    "precio_np": 7190},
    {"codigo": 344298, "art_prov": "67.T4022",    "precio_np": 10890},
    {"codigo": 343729, "art_prov": "67.T4023",    "precio_np": 8590},
    {"codigo": 344299, "art_prov": "67.T4027",    "precio_np": 9890},
    {"codigo": 344301, "art_prov": "67.T4255",    "precio_np": 5490},
    {"codigo": 344304, "art_prov": "67.T4330",    "precio_np": 3490},
    {"codigo": 344305, "art_prov": "67.T4333",    "precio_np": 2790},
    {"codigo": 344306, "art_prov": "67.T4334",    "precio_np": 2790},
    {"codigo": 358597, "art_prov": "67.C2959.1",  "precio_np": 9390},
    {"codigo": 358598, "art_prov": "67.C2959.2",  "precio_np": 9390},
]


# ══════════════════════════════════════════════════════════════
# CARGA DE DATOS DESDE JSON
# ══════════════════════════════════════════════════════════════

def cargar_datos():
    """Carga items y cross-reference desde JSON."""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    items_path = os.path.join(script_dir, "lesedife_items.json")
    cross_path = os.path.join(script_dir, "lesedife_cross.json")

    with open(items_path, encoding="utf-8") as f:
        items = json.load(f)

    with open(cross_path, encoding="utf-8") as f:
        cross = json.load(f)

    # Construir dict: articulo_prov → codigo_interno (primer match)
    mapa = {}
    for np_key in ["np466962", "np467731"]:
        for item in cross[np_key].get("found_items", []):
            art = item["articulo_prov"]
            codes = item.get("codigos_bd", [])
            if codes and art not in mapa:
                mapa[art] = codes[0]

    return items, mapa


# ══════════════════════════════════════════════════════════════
# FUNCIONES AUXILIARES
# ══════════════════════════════════════════════════════════════

def calcular_cadena_precios(precio_lista):
    """
    Calcula cadena de precios usando config.calcular_precios().
    precio_lista = precio_fabrica del proveedor (antes de descuento).
    Usa la configuración de PROVEEDORES[42] en config.py.
    """
    return calcular_precios(precio_lista, PROVEEDOR)


# ══════════════════════════════════════════════════════════════
# FASE 0: FIXES (proveedor NULL, descripción, precios)
# ══════════════════════════════════════════════════════════════

def fase0_fixes(dry_run=True):
    """Corrige artículos con proveedor NULL, descripción errónea y precios viejos."""
    modo = "DRY RUN" if dry_run else "EJECUCIÓN REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 0: FIXES — {modo}")
    print(f"{'='*70}")

    conn = None
    cursor = None
    if not dry_run:
        conn = pyodbc.connect(CONN_COMPRAS, timeout=10)
        cursor = conn.cursor()

    # ── 0a: Fix proveedor=NULL ──
    print(f"\n  ── 0a: Fix proveedor=NULL ({len(ARTS_PROVEEDOR_NULL)} artículos) ──")
    for codigo in ARTS_PROVEEDOR_NULL:
        print(f"    cod={codigo}: SET proveedor={PROVEEDOR}, marca={MARCA}")
        if not dry_run:
            try:
                cursor.execute("""
                    UPDATE msgestion01art.dbo.articulo
                    SET proveedor = ?, marca = ?
                    WHERE codigo = ? AND (proveedor IS NULL OR proveedor = 0)
                """, (PROVEEDOR, MARCA, codigo))
                print(f"      ✅ rows={cursor.rowcount}")
            except Exception as e:
                print(f"      ❌ Error: {e}")

    # ── 0b: Fix descripción ──
    print(f"\n  ── 0b: Fix descripción ({len(FIXES_DESCRIPCION)} artículos) ──")
    for fix in FIXES_DESCRIPCION:
        print(f"    cod={fix['codigo']}: '{fix['viejo']}' → '{fix['nuevo']}'")
        if not dry_run:
            try:
                cursor.execute("""
                    UPDATE msgestion01art.dbo.articulo
                    SET descripcion_1 = ?
                    WHERE codigo = ? AND descripcion_1 = ?
                """, (fix["nuevo"], fix["codigo"], fix["viejo"]))
                print(f"      ✅ rows={cursor.rowcount}")
            except Exception as e:
                print(f"      ❌ Error: {e}")

    # ── 0c: Actualizar precios viejos NP466962 (16 artículos) ──
    print(f"\n  ── 0c: Actualizar precios NP466962 ({len(PRECIOS_VIEJOS_466)} artículos) ──")
    for item in PRECIOS_VIEJOS_466:
        precios = calcular_cadena_precios(item["precio_np"])
        print(f"    cod={item['codigo']:>6} ({item['art_prov']:15s}): "
              f"fabrica=${item['precio_np']:>8,} costo=${precios['precio_costo']:>10,.2f} "
              f"p1=${precios['precio_1']:>10,.2f}")
        if not dry_run:
            try:
                cursor.execute("""
                    UPDATE msgestion01art.dbo.articulo
                    SET precio_fabrica = ?,
                        precio_costo = ?, precio_sugerido = ?,
                        precio_1 = ?, precio_2 = ?,
                        precio_3 = ?, precio_4 = ?,
                        utilidad_1 = ?, utilidad_2 = ?,
                        utilidad_3 = ?, utilidad_4 = ?,
                        descuento_1 = ?, formula = ?
                    WHERE codigo = ?
                """, (precios["precio_fabrica"],
                      precios["precio_costo"], precios["precio_sugerido"],
                      precios["precio_1"], precios["precio_2"],
                      precios["precio_3"], precios["precio_4"],
                      precios["utilidad_1"], precios["utilidad_2"],
                      precios["utilidad_3"], precios["utilidad_4"],
                      precios["descuento"], precios["formula"],
                      item["codigo"]))
                print(f"      ✅ rows={cursor.rowcount}")
            except Exception as e:
                print(f"      ❌ Error: {e}")

    # ── 0d: Cargar precios NP467731 (51 artículos con precio_fabrica=NULL) ──
    # Estos los lee del JSON directamente
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cross_path = os.path.join(script_dir, "lesedife_cross.json")
    with open(cross_path, encoding="utf-8") as f:
        cross = json.load(f)

    arts_467 = cross["np467731"]["found_items"]
    null_prices = [i for i in arts_467 if i.get("precio_fabrica_bd", [None])[0] is None]

    print(f"\n  ── 0d: Cargar precios NP467731 ({len(null_prices)} artículos con precio=NULL) ──")
    for item in null_prices:
        cod = item["codigos_bd"][0]
        precio_np = item["precio_np"]
        precios = calcular_cadena_precios(precio_np)
        if len(null_prices) <= 10 or null_prices.index(item) < 5 or null_prices.index(item) >= len(null_prices) - 2:
            print(f"    cod={cod:>6} ({item['articulo_prov']:15s}): "
                  f"fabrica=${precio_np:>8,} costo=${precios['precio_costo']:>10,.2f}")
        elif null_prices.index(item) == 5:
            print(f"    ... ({len(null_prices) - 7} más) ...")
        if not dry_run:
            try:
                cursor.execute("""
                    UPDATE msgestion01art.dbo.articulo
                    SET precio_fabrica = ?,
                        precio_costo = ?, precio_sugerido = ?,
                        precio_1 = ?, precio_2 = ?,
                        precio_3 = ?, precio_4 = ?,
                        utilidad_1 = ?, utilidad_2 = ?,
                        utilidad_3 = ?, utilidad_4 = ?,
                        descuento_1 = ?, formula = ?,
                        proveedor = CASE WHEN proveedor IS NULL THEN ? ELSE proveedor END,
                        marca = CASE WHEN marca IS NULL OR marca = 0 THEN ? ELSE marca END
                    WHERE codigo = ?
                """, (precios["precio_fabrica"],
                      precios["precio_costo"], precios["precio_sugerido"],
                      precios["precio_1"], precios["precio_2"],
                      precios["precio_3"], precios["precio_4"],
                      precios["utilidad_1"], precios["utilidad_2"],
                      precios["utilidad_3"], precios["utilidad_4"],
                      precios["descuento"], precios["formula"],
                      PROVEEDOR, MARCA, cod))
            except Exception as e:
                print(f"      ❌ cod={cod}: {e}")

    if not dry_run and conn:
        conn.commit()
        conn.close()
        print(f"\n  ✅ Fase 0 completada — cambios commiteados")
    else:
        print(f"\n  [DRY RUN] Fase 0 — nada escrito")


# ══════════════════════════════════════════════════════════════
# FASE 1: INSERT PEDIDO COMPLEMENTO NP466962
# ══════════════════════════════════════════════════════════════

def fase1_pedido_466962(items, mapa, dry_run=True):
    """Inserta los 150 renglones que faltan de NP466962."""
    from paso4_insertar_pedido import insertar_pedido

    modo = "DRY RUN" if dry_run else "EJECUCIÓN REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 1: PEDIDO COMPLEMENTO NP466962 — {modo}")
    print(f"  (Pedido #1134065 ya tiene 37 renglones / 254 pares)")
    print(f"{'='*70}")

    # --- Anti-duplicado: verificar si ya existe un complemento ---
    if not dry_run:
        import pyodbc as _pyo
        _c = _pyo.connect(CONN_COMPRAS)
        _cur = _c.cursor()
        _cur.execute(
            "SELECT numero FROM MSGESTION03.dbo.pedico2 "
            "WHERE codigo=8 AND cuenta=42 AND observaciones LIKE '%466962 COMPLEMENTO%'"
        )
        _dup = _cur.fetchone()
        _c.close()
        if _dup:
            print(f"  ⚠️  YA EXISTE complemento NP466962 → pedido #{_dup[0]}")
            print(f"  → SALTANDO Fase 1 para evitar duplicado")
            return _dup[0]

    cabecera = {
        "empresa":           EMPRESA,
        "cuenta":            PROVEEDOR,
        "denominacion":      "LESEDIFE S.A.I.C.",
        "fecha_comprobante": date(2026, 2, 11),
        "fecha_entrega":     date(2026, 4, 15),
        "observaciones":     "NP 0000-00466962 COMPLEMENTO. Unicross/Amayra/Wilson. "
                             "Invierno 2026. 150 renglones adicionales. "
                             "Pedido original: #1134065 (37 renglones).",
    }

    renglones = []
    saltados = 0
    sin_codigo = 0

    for item in items.get("np466962", []):
        art = item["articulo_prov"]
        codigo = mapa.get(art)

        if not codigo:
            sin_codigo += 1
            continue

        # Saltar los que ya están en pedido #1134065
        if codigo in ARTS_EN_PEDIDO_1134065:
            saltados += 1
            continue

        renglones.append({
            "articulo":        codigo,
            "descripcion":     item["descripcion"][:60],
            "codigo_sinonimo": "",
            "cantidad":        item["cantidad"],
            "precio":          item["precio"],
        })

    print(f"  Saltados (ya en #1134065): {saltados}")
    if sin_codigo:
        print(f"  ⚠️  Sin código en mapa: {sin_codigo}")
    total_u = sum(r["cantidad"] for r in renglones)
    total_m = sum(r["cantidad"] * r["precio"] for r in renglones)
    print(f"  Renglones a insertar: {len(renglones)}")
    print(f"  Unidades: {total_u}")
    print(f"  Total bruto: ${total_m:,.0f}")
    print(f"  Bonif 19%: -${total_m * 0.19:,.0f}")
    print(f"  Neto: ${total_m * 0.81:,.0f}")

    if renglones:
        num = insertar_pedido(cabecera, renglones, dry_run=dry_run)
        print(f"  → Pedido complemento NP466962: número {num}")
        return num
    else:
        print(f"  ⚠️  No hay renglones para insertar")
        return None


# ══════════════════════════════════════════════════════════════
# FASE 2: INSERT PEDIDO NUEVO NP467731
# ══════════════════════════════════════════════════════════════

def fase2_pedido_467731(items, mapa, dry_run=True):
    """Inserta pedido nuevo NP467731 (Disney/Marvel)."""
    from paso4_insertar_pedido import insertar_pedido

    modo = "DRY RUN" if dry_run else "EJECUCIÓN REAL"
    print(f"\n{'='*70}")
    print(f"  FASE 2: PEDIDO NUEVO NP467731 (Disney/Marvel) — {modo}")
    print(f"{'='*70}")

    # --- Anti-duplicado: verificar si ya existe ---
    if not dry_run:
        import pyodbc as _pyo
        _c = _pyo.connect(CONN_COMPRAS)
        _cur = _c.cursor()
        _cur.execute(
            "SELECT numero FROM MSGESTION03.dbo.pedico2 "
            "WHERE codigo=8 AND cuenta=42 AND observaciones LIKE '%467731%'"
        )
        _dup = _cur.fetchone()
        _c.close()
        if _dup:
            print(f"  ⚠️  YA EXISTE pedido NP467731 → #{_dup[0]}")
            print(f"  → SALTANDO Fase 2 para evitar duplicado")
            return _dup[0]

    cabecera = {
        "empresa":           EMPRESA,
        "cuenta":            PROVEEDOR,
        "denominacion":      "LESEDIFE S.A.I.C.",
        "fecha_comprobante": date(2026, 2, 11),
        "fecha_entrega":     date(2026, 4, 15),
        "observaciones":     "NP 0000-00467731. Disney/Marvel. Invierno 2026. Bonif 19%.",
    }

    renglones = []
    sin_codigo = 0

    for item in items.get("np467731", []):
        art = item["articulo_prov"]
        codigo = mapa.get(art)

        if not codigo:
            sin_codigo += 1
            print(f"  ⚠️  Sin código: {art} ({item['descripcion'][:40]})")
            continue

        renglones.append({
            "articulo":        codigo,
            "descripcion":     item["descripcion"][:60],
            "codigo_sinonimo": "",
            "cantidad":        item["cantidad"],
            "precio":          item["precio"],
        })

    if sin_codigo:
        print(f"  ⚠️  Total sin código: {sin_codigo}")

    total_u = sum(r["cantidad"] for r in renglones)
    total_m = sum(r["cantidad"] * r["precio"] for r in renglones)
    print(f"  Renglones: {len(renglones)}")
    print(f"  Unidades: {total_u}")
    print(f"  Total bruto: ${total_m:,.0f}")
    print(f"  Bonif 19%: -${total_m * 0.19:,.0f}")
    print(f"  Neto: ${total_m * 0.81:,.0f}")

    if renglones:
        num = insertar_pedido(cabecera, renglones, dry_run=dry_run)
        print(f"  → Pedido NP467731: número {num}")
        return num
    else:
        print(f"  ⚠️  No hay renglones para insertar")
        return None


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]

    dry_run = modo != "--ejecutar"

    print("─" * 70)
    print("  INSERTAR LESEDIFE — 2 Notas de Pedido (v2 — 12 mar 2026)")
    print("─" * 70)

    # Cargar datos
    items, mapa = cargar_datos()

    n466 = len(items.get("np466962", []))
    n467 = len(items.get("np467731", []))
    u466 = sum(i["cantidad"] for i in items.get("np466962", []))
    u467 = sum(i["cantidad"] for i in items.get("np467731", []))
    print(f"  NP 466962: {n466} items, {u466} unidades (Unicross/Amayra/Wilson)")
    print(f"  NP 467731: {n467} items, {u467} unidades (Disney/Marvel)")
    print(f"  Artículos mapeados: {len(mapa)} (todos existen en BD)")
    print(f"  Ya en pedido #1134065: {len(ARTS_EN_PEDIDO_1134065)} renglones")
    print(f"  Por insertar NP466962: ~150 renglones complementarios")
    print(f"  Por insertar NP467731: {n467} renglones (pedido nuevo)")

    if dry_run:
        print(f"\n⚠️  MODO DRY RUN — no se escribe nada")
    else:
        print(f"\n🚨 MODO EJECUCIÓN REAL")
        print(f"   Servidor: 192.168.2.111")
        print(f"   Empresa: {EMPRESA} → {BD_BASE}")
        print(f"   Proveedor: {PROVEEDOR} (LESEDIFE S.A.)")
        confirmacion = input("\n   ¿Confirmar? (s/N): ").strip().lower()
        if confirmacion != "s":
            print("   Cancelado.")
            sys.exit(0)

    # Fase 0: Fixes (proveedor NULL, descripción, precios)
    fase0_fixes(dry_run=dry_run)

    # Fase 1: Pedido complemento NP466962 (150 renglones)
    num1 = fase1_pedido_466962(items, mapa, dry_run=dry_run)

    # Fase 2: Pedido nuevo NP467731 (51 renglones)
    num2 = fase2_pedido_467731(items, mapa, dry_run=dry_run)

    print(f"\n{'='*70}")
    print(f"  PROCESO COMPLETO")
    print(f"{'='*70}")

    if not dry_run:
        print(f"\n  Verificar en SSMS:")
        if num1:
            print(f"    SELECT * FROM msgestionC.dbo.pedico1 WHERE numero = {num1} AND empresa = 'H4'")
        if num2:
            print(f"    SELECT * FROM msgestionC.dbo.pedico1 WHERE numero = {num2} AND empresa = 'H4'")
        print(f"    -- Pedido original NP466962:")
        print(f"    SELECT * FROM msgestionC.dbo.pedico1 WHERE numero = 1134065 AND empresa = 'H4'")
