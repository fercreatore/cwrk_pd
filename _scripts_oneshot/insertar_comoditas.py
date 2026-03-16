# insertar_comoditas.py
# Inserta pedido COMODITAS SA — Pantuflas Invierno 2026
# 468 pares, 5 modelos, 11 colores
#
# MODELOS EXISTENTES: 598, 1127, 239 (artículos ya en DB)
# MODELOS NUEVOS: 1619, 1246 (requieren alta de artículos primero)
#
# ANÁLISIS "CAMPEONES":
#   1127 = #3 modelo Comoditas (261 pares en 3 años)
#   598  = top seller (236 pares, oculto en grupo NULL)
#   239  = sólido medio (100 pares)
#   1619 = NUEVO sin historial
#   1246 = NUEVO sin historial
#
# EJECUTAR EN EL 111:
#   py -3 insertar_comoditas.py --dry-run     ← solo muestra, no escribe
#   py -3 insertar_comoditas.py --ejecutar    ← escribe en producción

import sys
import pyodbc
from datetime import date, datetime
from paso4_insertar_pedido import insertar_pedido
from config import CONN_ARTICULOS, CONN_COMPRAS

# ══════════════════════════════════════════════════════════════
# PARTE 1: ALTA DE ARTÍCULOS NUEVOS (1619 y 1246)
# ══════════════════════════════════════════════════════════════

# Artículos nuevos a crear. Códigos empiezan en 361244 (MAX actual: 361243)
# Se basan en la estructura de artículos existentes de Comoditas (marca=776, subrubro=60)

# Referencia: 1127 para 1619 (individual T37-T41), 598 para 1246 (binumeral T36/T38/T40)
# Utilidades copiadas de artículos existentes de Comoditas:
#   utilidad_1=100, utilidad_2=124, utilidad_3=60, utilidad_4=45

NUEVOS_ARTICULOS = [
    # ── 1619 VERDE — PANTUFLA (individual, talles 37-41) ──
    # grupo "36" = mujer individual 36-41 (mismo que 1127)
    {"codigo": 361244, "desc1": "1619 VERDE PANTUFLA P/CERRADA", "desc3": "1619 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "37", "grupo": "36", "cod_sin": "776161902037", "cod_barra": 776161902037, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361245, "desc1": "1619 VERDE PANTUFLA P/CERRADA", "desc3": "1619 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "38", "grupo": "36", "cod_sin": "776161902038", "cod_barra": 776161902038, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361246, "desc1": "1619 VERDE PANTUFLA P/CERRADA", "desc3": "1619 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "39", "grupo": "36", "cod_sin": "776161902039", "cod_barra": 776161902039, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361247, "desc1": "1619 VERDE PANTUFLA P/CERRADA", "desc3": "1619 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "40", "grupo": "36", "cod_sin": "776161902040", "cod_barra": 776161902040, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361248, "desc1": "1619 VERDE PANTUFLA P/CERRADA", "desc3": "1619 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "41", "grupo": "36", "cod_sin": "776161902041", "cod_barra": 776161902041, "cod_obj": "16190", "precio_fab": 11422},

    # ── 1619 GRIS — PANTUFLA (individual, talles 37-41) ──
    {"codigo": 361249, "desc1": "1619 GRIS PANTUFLA P/CERRADA",  "desc3": "1619 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "37", "grupo": "36", "cod_sin": "776161901337", "cod_barra": 776161901337, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361250, "desc1": "1619 GRIS PANTUFLA P/CERRADA",  "desc3": "1619 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "38", "grupo": "36", "cod_sin": "776161901338", "cod_barra": 776161901338, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361251, "desc1": "1619 GRIS PANTUFLA P/CERRADA",  "desc3": "1619 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "39", "grupo": "36", "cod_sin": "776161901339", "cod_barra": 776161901339, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361252, "desc1": "1619 GRIS PANTUFLA P/CERRADA",  "desc3": "1619 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "40", "grupo": "36", "cod_sin": "776161901340", "cod_barra": 776161901340, "cod_obj": "16190", "precio_fab": 11422},
    {"codigo": 361253, "desc1": "1619 GRIS PANTUFLA P/CERRADA",  "desc3": "1619 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "41", "grupo": "36", "cod_sin": "776161901341", "cod_barra": 776161901341, "cod_obj": "16190", "precio_fab": 11422},

    # ── 1246 GRIS — PANTUFLA (binumeral, talles 36/38/40) ──
    # grupo "13" = mujer binumeral (mismo que 598)
    {"codigo": 361254, "desc1": "1246 GRIS PANTUFLA P/CERRADA",  "desc3": "1246 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "36", "grupo": "13", "cod_sin": "776124601336", "cod_barra": 776124601336, "cod_obj": "12460", "precio_fab": 13929},
    {"codigo": 361255, "desc1": "1246 GRIS PANTUFLA P/CERRADA",  "desc3": "1246 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "38", "grupo": "13", "cod_sin": "776124601338", "cod_barra": 776124601338, "cod_obj": "12460", "precio_fab": 13929},
    {"codigo": 361256, "desc1": "1246 GRIS PANTUFLA P/CERRADA",  "desc3": "1246 GRIS PANTU P/CERR", "desc4": "GRIS",   "desc5": "40", "grupo": "13", "cod_sin": "776124601340", "cod_barra": 776124601340, "cod_obj": "12460", "precio_fab": 13929},

    # ── 1246 VERDE — PANTUFLA (binumeral, talles 36/38/40) ──
    {"codigo": 361257, "desc1": "1246 VERDE PANTUFLA P/CERRADA", "desc3": "1246 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "36", "grupo": "13", "cod_sin": "776124602036", "cod_barra": 776124602036, "cod_obj": "12460", "precio_fab": 13929},
    {"codigo": 361258, "desc1": "1246 VERDE PANTUFLA P/CERRADA", "desc3": "1246 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "38", "grupo": "13", "cod_sin": "776124602038", "cod_barra": 776124602038, "cod_obj": "12460", "precio_fab": 13929},
    {"codigo": 361259, "desc1": "1246 VERDE PANTUFLA P/CERRADA", "desc3": "1246 VERD PANTU P/CERR", "desc4": "VERDE",  "desc5": "40", "grupo": "13", "cod_sin": "776124602040", "cod_barra": 776124602040, "cod_obj": "12460", "precio_fab": 13929},
]


def alta_articulos(dry_run=True):
    """Da de alta los artículos nuevos (1619 y 1246) en msgestion01art.dbo.articulo."""

    # Utilidades Comoditas (copiadas de artículos existentes marca 776)
    UTIL_1, UTIL_2, UTIL_3, UTIL_4 = 100, 124, 60, 45

    sql = """
        INSERT INTO msgestion01art.dbo.articulo (
            codigo, descripcion_1, descripcion_3, descripcion_4, descripcion_5,
            codigo_barra, codigo_sinonimo, tipo_codigo_barra,
            marca, rubro, subrubro, grupo, proveedor, linea,
            codigo_objeto_costo,
            precio_fabrica, precio_costo, precio_sugerido,
            precio_1, precio_2, precio_3, precio_4,
            utilidad_1, utilidad_2, utilidad_3, utilidad_4,
            alicuota_iva1, alicuota_iva2, tipo_iva,
            formula, calificacion, estado, estado_web,
            descuento, descuento_1, descuento_2, descuento_3, descuento_4,
            flete, porc_flete, porc_recargo, moneda,
            factura_por_total, numero_maximo, stock,
            cuenta_compras, cuenta_ventas, cuenta_vta_anti, cuenta_com_anti,
            usuario, abm, fecha_alta
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, 'C',
            776, 1, 60, ?, 776, 2,
            ?,
            ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            21, 10.5, 'G',
            1, 'G', 'V', 'V',
            0, 0, 0, 0, 0,
            0, 0, 0, 0,
            'N', 'S', 'S',
            '1010601', '4010100', '4010100', '1010601',
            'COWORK', 'A', GETDATE()
        )
    """

    if dry_run:
        print("\n[DRY RUN] ═══ ALTA DE ARTÍCULOS NUEVOS ═══")
        for art in NUEVOS_ARTICULOS:
            pf = art["precio_fab"]
            pc = pf  # sin descuento para Comoditas
            print(f"  {art['codigo']}: {art['desc1']} T{art['desc5']} | ${pf:,.0f} | sin={art['cod_sin']}")
        print(f"\n  Total: {len(NUEVOS_ARTICULOS)} artículos nuevos a crear")
        print("  [DRY RUN] Ningún artículo fue creado.\n")
        return True

    try:
        conn = pyodbc.connect(CONN_ARTICULOS, timeout=10)
        conn.autocommit = False
        cursor = conn.cursor()

        # Verificar que no existan ya
        codigos = [a["codigo"] for a in NUEVOS_ARTICULOS]
        placeholders = ",".join(["?"] * len(codigos))
        cursor.execute(f"SELECT codigo FROM msgestion01art.dbo.articulo WHERE codigo IN ({placeholders})", codigos)
        existentes = [r[0] for r in cursor.fetchall()]
        if existentes:
            print(f"⚠️  Artículos ya existentes: {existentes} — saltando alta")
            conn.close()
            return True  # no es error, ya existen

        for art in NUEVOS_ARTICULOS:
            pf = art["precio_fab"]
            pc = pf  # Comoditas sin descuento
            p1 = round(pc * (1 + UTIL_1 / 100), 2)
            p2 = round(pc * (1 + UTIL_2 / 100), 2)
            p3 = round(pc * (1 + UTIL_3 / 100), 2)
            p4 = round(pc * (1 + UTIL_4 / 100), 2)

            cursor.execute(sql, (
                art["codigo"], art["desc1"], art["desc3"], art["desc4"], art["desc5"],
                art["cod_barra"], art["cod_sin"],
                art["grupo"],
                art["cod_obj"],
                pf, pc, pc,
                p1, p2, p3, p4,
                UTIL_1, UTIL_2, UTIL_3, UTIL_4,
            ))
            print(f"  ✅ {art['codigo']}: {art['desc1']} T{art['desc5']}", flush=True)

        conn.commit()
        conn.close()
        print(f"\n✅ {len(NUEVOS_ARTICULOS)} artículos nuevos creados en msgestion01art")
        return True

    except Exception as e:
        print(f"\n❌ ERROR al crear artículos: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# PARTE 2: PEDIDO DE COMPRA
# ══════════════════════════════════════════════════════════════

cabecera = {
    "empresa":           "H4",              # Comoditas compras van a base03
    "cuenta":            98,                # COMODITAS SA
    "denominacion":      "COMODITAS SA",
    "fecha_comprobante": date(2026, 3, 14),
    "fecha_entrega":     date(2026, 4, 30), # ~6 semanas entrega
    "observaciones":     "Pedido pantuflas invierno 2026. 468 pares. "
                         "5 modelos (598, 1127, 1619, 1246, 239). "
                         "1619 y 1246 son modelos nuevos. "
                         "239 hombre duplicado a 144 pares.",
}

# ── RENGLONES ────────────────────────────────────────────────
# Precio = precio unitario de lista del proveedor (sin IVA)
#
# ARTÍCULOS EXISTENTES:
#   598 binumeral (T36/T38/T40) — ROSA, GRIS, NEGRO
#   1127 individual (T37-T41) — AERO, MANTECA
#   239 individual (T40-T45) — NEGRO, AZUL (cantidades DUPLICADAS)
#
# ARTÍCULOS NUEVOS (creados en PARTE 1):
#   1619 individual (T37-T41) — VERDE, GRIS
#   1246 binumeral (T38/T40) — GRIS, VERDE

renglones = [
    # ═══ 598 ROSA (binumeral) — 36 pares ═══
    {"articulo": 264863, "descripcion": "598 ROSA PANTUFLA P/CERRADA C/BASE DET BOTON",  "codigo_sinonimo": "776598001938", "cantidad": 16, "precio": 12904},  # T38
    {"articulo": 264864, "descripcion": "598 ROSA PANTUFLA P/CERRADA C/BASE DET BOTON",  "codigo_sinonimo": "776598001940", "cantidad": 20, "precio": 12904},  # T40

    # ═══ 598 GRIS (binumeral) — 36 pares ═══
    {"articulo": 264860, "descripcion": "598 GRIS PANTUFLA P/CERRADA C/BASE DET BOTON",  "codigo_sinonimo": "776598001338", "cantidad": 16, "precio": 12904},  # T38
    {"articulo": 264861, "descripcion": "598 GRIS PANTUFLA P/CERRADA C/BASE DET BOTON",  "codigo_sinonimo": "776598001340", "cantidad": 20, "precio": 12904},  # T40

    # ═══ 598 NEGRO (binumeral) — 36 pares ═══
    {"articulo": 264854, "descripcion": "598 NEGRO PANTUFLA P/CERRADA C/BASE DET BOTON", "codigo_sinonimo": "776598000038", "cantidad": 16, "precio": 12904},  # T38
    {"articulo": 264855, "descripcion": "598 NEGRO PANTUFLA P/CERRADA C/BASE DET BOTON", "codigo_sinonimo": "776598000040", "cantidad": 20, "precio": 12904},  # T40

    # ═══ 1127 AERO (individual) — 36 pares ═══
    {"articulo": 289994, "descripcion": "1127 AERO PANTUFLA P/CERRADA CUE PELUCHE",      "codigo_sinonimo": "776112700337", "cantidad":  6, "precio": 11565},  # T37
    {"articulo": 289995, "descripcion": "1127 AERO PANTUFLA P/CERRADA CUE PELUCHE",      "codigo_sinonimo": "776112700338", "cantidad":  8, "precio": 11565},  # T38
    {"articulo": 289996, "descripcion": "1127 AERO PANTUFLA P/CERRADA CUE PELUCHE",      "codigo_sinonimo": "776112700339", "cantidad":  8, "precio": 11565},  # T39
    {"articulo": 289997, "descripcion": "1127 AERO PANTUFLA P/CERRADA CUE PELUCHE",      "codigo_sinonimo": "776112700340", "cantidad":  8, "precio": 11565},  # T40
    {"articulo": 289998, "descripcion": "1127 AERO PANTUFLA P/CERRADA CUE PELUCHE",      "codigo_sinonimo": "776112700341", "cantidad":  6, "precio": 11565},  # T41

    # ═══ 1127 MANTECA (individual) — 36 pares ═══
    {"articulo": 264908, "descripcion": "1127 MANTECA PANTUFLA P/CERRADA CUE PELUCHE",   "codigo_sinonimo": "776112701537", "cantidad":  6, "precio": 11565},  # T37
    {"articulo": 264909, "descripcion": "1127 MANTECA PANTUFLA P/CERRADA CUE PELUCHE",   "codigo_sinonimo": "776112701538", "cantidad": 10, "precio": 11565},  # T38
    {"articulo": 264910, "descripcion": "1127 MANTECA PANTUFLA P/CERRADA CUE PELUCHE",   "codigo_sinonimo": "776112701539", "cantidad":  8, "precio": 11565},  # T39
    {"articulo": 264911, "descripcion": "1127 MANTECA PANTUFLA P/CERRADA CUE PELUCHE",   "codigo_sinonimo": "776112701540", "cantidad":  8, "precio": 11565},  # T40
    {"articulo": 264912, "descripcion": "1127 MANTECA PANTUFLA P/CERRADA CUE PELUCHE",   "codigo_sinonimo": "776112701541", "cantidad":  4, "precio": 11565},  # T41

    # ═══ 1619 VERDE (individual, NUEVO) — 36 pares ═══
    {"articulo": 361244, "descripcion": "1619 VERDE PANTUFLA P/CERRADA",                 "codigo_sinonimo": "776161902037", "cantidad":  4, "precio": 11422},  # T37
    {"articulo": 361245, "descripcion": "1619 VERDE PANTUFLA P/CERRADA",                 "codigo_sinonimo": "776161902038", "cantidad":  8, "precio": 11422},  # T38
    {"articulo": 361246, "descripcion": "1619 VERDE PANTUFLA P/CERRADA",                 "codigo_sinonimo": "776161902039", "cantidad": 10, "precio": 11422},  # T39
    {"articulo": 361247, "descripcion": "1619 VERDE PANTUFLA P/CERRADA",                 "codigo_sinonimo": "776161902040", "cantidad": 10, "precio": 11422},  # T40
    {"articulo": 361248, "descripcion": "1619 VERDE PANTUFLA P/CERRADA",                 "codigo_sinonimo": "776161902041", "cantidad":  4, "precio": 11422},  # T41

    # ═══ 1619 GRIS (individual, NUEVO) — 36 pares ═══
    {"articulo": 361249, "descripcion": "1619 GRIS PANTUFLA P/CERRADA",                  "codigo_sinonimo": "776161901337", "cantidad":  4, "precio": 11422},  # T37
    {"articulo": 361250, "descripcion": "1619 GRIS PANTUFLA P/CERRADA",                  "codigo_sinonimo": "776161901338", "cantidad":  8, "precio": 11422},  # T38
    {"articulo": 361251, "descripcion": "1619 GRIS PANTUFLA P/CERRADA",                  "codigo_sinonimo": "776161901339", "cantidad": 10, "precio": 11422},  # T39
    {"articulo": 361252, "descripcion": "1619 GRIS PANTUFLA P/CERRADA",                  "codigo_sinonimo": "776161901340", "cantidad": 10, "precio": 11422},  # T40
    {"articulo": 361253, "descripcion": "1619 GRIS PANTUFLA P/CERRADA",                  "codigo_sinonimo": "776161901341", "cantidad":  4, "precio": 11422},  # T41

    # ═══ 1246 GRIS (binumeral, NUEVO) — 36 pares ═══
    {"articulo": 361255, "descripcion": "1246 GRIS PANTUFLA P/CERRADA",                  "codigo_sinonimo": "776124601338", "cantidad": 16, "precio": 13929},  # T38
    {"articulo": 361256, "descripcion": "1246 GRIS PANTUFLA P/CERRADA",                  "codigo_sinonimo": "776124601340", "cantidad": 20, "precio": 13929},  # T40

    # ═══ 1246 VERDE (binumeral, NUEVO) — 36 pares ═══
    {"articulo": 361258, "descripcion": "1246 VERDE PANTUFLA P/CERRADA",                 "codigo_sinonimo": "776124602038", "cantidad": 16, "precio": 13929},  # T38
    {"articulo": 361259, "descripcion": "1246 VERDE PANTUFLA P/CERRADA",                 "codigo_sinonimo": "776124602040", "cantidad": 20, "precio": 13929},  # T40

    # ═══ 239 NEGRO (individual, hombre DUPLICADO) — 72 pares ═══
    {"articulo": 223048, "descripcion": "239 NEGRO PANTUFLA C/PUNTA INT CORDERITO",      "codigo_sinonimo": "776239000041", "cantidad":  8, "precio": 12727},  # T41
    {"articulo": 223049, "descripcion": "239 NEGRO PANTUFLA C/PUNTA INT CORDERITO",      "codigo_sinonimo": "776239000042", "cantidad": 16, "precio": 12727},  # T42
    {"articulo": 223050, "descripcion": "239 NEGRO PANTUFLA C/PUNTA INT CORDERITO",      "codigo_sinonimo": "776239000043", "cantidad": 16, "precio": 12727},  # T43
    {"articulo": 223051, "descripcion": "239 NEGRO PANTUFLA C/PUNTA INT CORDERITO",      "codigo_sinonimo": "776239000044", "cantidad": 16, "precio": 12727},  # T44
    {"articulo": 223052, "descripcion": "239 NEGRO PANTUFLA C/PUNTA INT CORDERITO",      "codigo_sinonimo": "776239000045", "cantidad": 16, "precio": 12727},  # T45

    # ═══ 239 AZUL (individual, hombre DUPLICADO) — 72 pares ═══
    {"articulo": 312186, "descripcion": "239 AZUL PANTUFLA C/PUNTA INT CORDERITO",       "codigo_sinonimo": "776239000241", "cantidad":  8, "precio": 12727},  # T41
    {"articulo": 312187, "descripcion": "239 AZUL PANTUFLA C/PUNTA INT CORDERITO",       "codigo_sinonimo": "776239000242", "cantidad": 16, "precio": 12727},  # T42
    {"articulo": 312188, "descripcion": "239 AZUL PANTUFLA C/PUNTA INT CORDERITO",       "codigo_sinonimo": "776239000243", "cantidad": 16, "precio": 12727},  # T43
    {"articulo": 312189, "descripcion": "239 AZUL PANTUFLA C/PUNTA INT CORDERITO",       "codigo_sinonimo": "776239000244", "cantidad": 16, "precio": 12727},  # T44
    {"articulo": 312190, "descripcion": "239 AZUL PANTUFLA C/PUNTA INT CORDERITO",       "codigo_sinonimo": "776239000245", "cantidad": 16, "precio": 12727},  # T45
]

# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]

    dry_run = modo != "--ejecutar"

    if dry_run:
        print("\n⚠️  MODO DRY RUN — no se escribe nada en la base")
    else:
        print("\n🚨 MODO EJECUCIÓN REAL — se escribirá en la base")
        confirmacion = input("   ¿Confirmar? (s/N): ").strip().lower()
        if confirmacion != "s":
            print("   Cancelado.")
            sys.exit(0)

    # ── Resumen del pedido ──
    total_pares = sum(r["cantidad"] for r in renglones)
    total_monto = sum(r["cantidad"] * r["precio"] for r in renglones)
    print(f"\n{'═'*60}")
    print(f"  PEDIDO COMODITAS SA — Invierno 2026")
    print(f"  {len(renglones)} renglones | {total_pares} pares | ${total_monto:,.0f}")
    print(f"{'═'*60}")

    # Detalle por modelo
    modelos = {}
    for r in renglones:
        mod = r["descripcion"].split()[0]
        col = r["descripcion"].split()[1]
        key = f"{mod} {col}"
        modelos.setdefault(key, 0)
        modelos[key] += r["cantidad"]
    for k, v in modelos.items():
        print(f"  {k:40s} {v:>4d} pares")
    print(f"  {'─'*44}")
    print(f"  {'TOTAL':40s} {total_pares:>4d} pares")

    # ── PASO 1: Alta de artículos nuevos ──
    print(f"\n{'─'*60}")
    print("  PASO 1: Alta de artículos nuevos (1619, 1246)")
    print(f"{'─'*60}")

    ok = alta_articulos(dry_run=dry_run)
    if not ok:
        print("❌ Falló la alta de artículos. Abortando.")
        sys.exit(1)

    # ── PASO 2: Insertar pedido ──
    print(f"\n{'─'*60}")
    print("  PASO 2: Insertar pedido de compra")
    print(f"{'─'*60}")

    numero = insertar_pedido(cabecera, renglones, dry_run=dry_run)

    if not dry_run and numero:
        print(f"\n✅ Verificar en SSMS:")
        print(f"   SELECT * FROM msgestionC.dbo.pedico2 WHERE numero = {numero} AND empresa = 'H4'")
        print(f"   SELECT * FROM msgestionC.dbo.pedico1 WHERE numero = {numero} AND empresa = 'H4'")
        print(f"   -- Debe haber {len(renglones)} renglones, {total_pares} pares")
