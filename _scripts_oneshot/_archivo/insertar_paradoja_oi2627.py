#!/usr/bin/env python3
"""
insertar_paradoja_oi2627.py
Pedido PARADOJA SHOES S.A — OI/PV 2026-27 — CALZALINDO (msgestion01)

Incluye:
  1. Alta artículos faltantes: 4000 NEGRO BOTA (T36-40) + Z70 CRISTAL (T37, T39)
  2. Pedido 1: Botas 5 modelos + Z30 ENT1 — entrega abr/may'26
  3. Pedido 2: Z70 ENT1              — entrega jul/ago'26
  4. Pedido 3: Z30 ENT2 curva real   — entrega oct/nov'26

EJECUTAR (desde C:\\cowork_pedidos en el 111 o desde el 112):
  py -3 _scripts_oneshot\\insertar_paradoja_oi2627.py --dry-run
  py -3 _scripts_oneshot\\insertar_paradoja_oi2627.py --ejecutar
"""
import sys
import pyodbc
from datetime import date
from paso4_insertar_pedido import insertar_pedido

CONN_ART = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;DATABASE=msgestion01art;"
    "UID=am;PWD=dl;TrustServerCertificate=yes"
)

# ── ARTÍCULOS FALTANTES ──────────────────────────────────────────────────────
# Copiamos estructura de plantilla: rubro=1, subrubro=15, marca=999, proveedor=999
# grupo="5", linea=2, tipo_iva="G", utilidad_1=100/2=124/3=60/4=45
# cuenta_compras="1010601", cuenta_ventas="4010100"
# precio_4 = precio_1 × 0.725 (mismo coef. de 3610)

NUEVOS_ARTICULOS = [
    # ── 4000 NEGRO BOTA (5 talles) ─────────────────────────────
    # costo=25400, PVP=50800 (mismo markup 2× del resto de Paradoja)
    {"sin": "999040000036", "d1": "4000 NEGRO BOTA", "d3": "4000 BOTA",
     "d4": "NEGRO", "d5": "36", "p1": 50800, "p2": 56896, "p3": 40640,
     "p4": 36830, "costo": 25400, "obj": "4000"},
    {"sin": "999040000037", "d1": "4000 NEGRO BOTA", "d3": "4000 BOTA",
     "d4": "NEGRO", "d5": "37", "p1": 50800, "p2": 56896, "p3": 40640,
     "p4": 36830, "costo": 25400, "obj": "4000"},
    {"sin": "999040000038", "d1": "4000 NEGRO BOTA", "d3": "4000 BOTA",
     "d4": "NEGRO", "d5": "38", "p1": 50800, "p2": 56896, "p3": 40640,
     "p4": 36830, "costo": 25400, "obj": "4000"},
    {"sin": "999040000039", "d1": "4000 NEGRO BOTA", "d3": "4000 BOTA",
     "d4": "NEGRO", "d5": "39", "p1": 50800, "p2": 56896, "p3": 40640,
     "p4": 36830, "costo": 25400, "obj": "4000"},
    {"sin": "999040000040", "d1": "4000 NEGRO BOTA", "d3": "4000 BOTA",
     "d4": "NEGRO", "d5": "40", "p1": 50800, "p2": 56896, "p3": 40640,
     "p4": 36830, "costo": 25400, "obj": "4000"},
    # ── Z70 CRISTAL ZUECO T37 y T39 ─────────────────────────────
    # mismos precios que T38 ya cargado (código 357923)
    {"sin": "999Z70110137", "d1": "Z70 CRISTAL ZUECO FAJA T/ACRILICO",
     "d3": "Z70 ZUECO FAJA T/ACRILICO", "d4": "CRISTAL", "d5": "37",
     "p1": 61600, "p2": 68320, "p3": 44800, "p4": 44660, "costo": 30800,
     "obj": "Z701"},
    {"sin": "999Z70110139", "d1": "Z70 CRISTAL ZUECO FAJA T/ACRILICO",
     "d3": "Z70 ZUECO FAJA T/ACRILICO", "d4": "CRISTAL", "d5": "39",
     "p1": 61600, "p2": 68320, "p3": 44800, "p4": 44660, "costo": 30800,
     "obj": "Z701"},
]


def alta_articulos(dry_run=True):
    """Crea artículos faltantes. Retorna dict {sinonimo: codigo}."""
    cod_map = {}
    with pyodbc.connect(CONN_ART, timeout=10) as conn:
        cursor = conn.cursor()
        conn.autocommit = False
        for art in NUEVOS_ARTICULOS:
            cursor.execute("SELECT codigo FROM articulo WHERE codigo_sinonimo = ?", art["sin"])
            row = cursor.fetchone()
            if row:
                cod_map[art["sin"]] = row[0]
                print(f"  ✓ Ya existe {art['sin']} → código {row[0]}")
                continue
            if dry_run:
                print(f"  [DRY] Alta pendiente: {art['sin']} — {art['d1']} T{art['d5']}")
                cod_map[art["sin"]] = None
                continue
            cursor.execute("SELECT ISNULL(MAX(codigo),0)+1 FROM articulo")
            nuevo = cursor.fetchone()[0]
            # codigo_barra: para sinonimos numéricos usar el entero; alfanuméricos → 0
            try:
                barra = int(art["sin"])
            except ValueError:
                barra = 0
            cursor.execute("""
                INSERT INTO articulo (
                    codigo, descripcion_1, descripcion_3, descripcion_4, descripcion_5,
                    codigo_sinonimo, codigo_barra,
                    precio_1, precio_2, precio_3, precio_4,
                    precio_costo, precio_fabrica, precio_sugerido,
                    marca, rubro, subrubro, proveedor, grupo, linea,
                    calificacion, factura_por_total,
                    alicuota_iva1, alicuota_iva2, tipo_iva,
                    utilidad_1, utilidad_2, utilidad_3, utilidad_4,
                    cuenta_compras, cuenta_ventas, cuenta_com_anti,
                    estado, numero_maximo, tipo_codigo_barra, stock, moneda,
                    formula, descuento, descuento_1, descuento_2, descuento_3, descuento_4,
                    codigo_objeto_costo, usuario, fecha_alta
                ) VALUES (
                    ?,?,?,?,?,  ?,?,
                    ?,?,?,?,    ?,?,?,
                    999,1,15,999,'5',2,
                    'G','N',
                    21,10.5,'G',
                    100,124,60,45,
                    '1010601','4010100','1010601',
                    'V','S','C','S',0,
                    1,0,0,0,0,0,
                    ?,       'COWORK',GETDATE()
                )
            """, (
                nuevo, art["d1"], art["d3"], art["d4"], art["d5"],
                art["sin"], barra,
                art["p1"], art["p2"], art["p3"], art["p4"],
                art["costo"], art["costo"], art["costo"],
                art["obj"]
            ))
            conn.commit()
            cod_map[art["sin"]] = nuevo
            print(f"  ✅ Alta: {art['sin']} → código {nuevo} ({art['d1']} T{art['d5']})")
    return cod_map


# ── ARTÍCULOS EXISTENTES (fijos) ─────────────────────────────────────────────
# Botas
A3610 = {36: 344850, 37: 344851, 38: 344852, 39: 344853, 40: 344854}
A6100 = {36: 345126, 37: 345127, 38: 345128, 39: 345129, 40: 345130}
A4200 = {36: 345131, 37: 345132, 38: 345133, 39: 345134, 40: 345135}
A6000 = {35: 343149, 36: 343150, 37: 343151, 38: 343152, 39: 343153, 40: 343154}
A3150 = {36: 343155, 37: 343156, 38: 343157, 39: 343158, 40: 343159}
# Z30 ACRILICO
AZ30 = {35: 349203, 36: 349204, 37: 349205, 38: 349206,
        39: 349207, 40: 349208, 41: 352332, 42: 352333, 43: 352334}
# Z70 CRISTAL (T38 ya existe)
AZ70_T38 = 357923


def build_renglon(cod_map, sinonimo, desc, cantidad, precio):
    """Helper: construye un renglón de pedico1."""
    codigo = cod_map.get(sinonimo)
    return {
        "articulo":       codigo,
        "descripcion":    desc,
        "codigo_sinonimo": sinonimo,
        "cantidad":       cantidad,
        "precio":         precio,
    }


def main(dry_run=True):
    print("\n" + "="*65)
    print("PEDIDO PARADOJA OI/PV 2026-27 — CALZALINDO")
    print("="*65)

    # 1. Alta de artículos faltantes
    print("\n[1] ALTA DE ARTÍCULOS FALTANTES")
    print("-"*40)
    cod_map = alta_articulos(dry_run=dry_run)

    # Construir mapa completo (existentes + nuevos)
    full_map = {}
    # Botas existentes
    for t, c in A3610.items(): full_map[f"999036100{t:02d}0{t:02d}"[:12]] = c
    # Ojo: los sinonimos botas tienen formato 999036100036 etc, ya definidos arriba
    # Los nuevos 4000 y Z70 vienen de cod_map

    # ── PEDIDO 1: Botas + Z30 ENT1 (abr/may'26) ──────────────────────────────
    print("\n[2] PEDIDO 1 — BOTAS + Z30 ENT1 — entrega abr/may'26")
    print("-"*40)

    ren_p1 = []

    # 3610 BOTA BAJA — T36:3, T37:3, T38:6, T39:4, T40:4
    for talle, qty in [(36,3),(37,3),(38,6),(39,4),(40,4)]:
        ren_p1.append({"articulo": A3610[talle],
                       "descripcion": f"3610 NEGRO BOTA BAJA 1 CIERRE DET TALON T{talle}",
                       "codigo_sinonimo": f"99903610{talle:04d}"[:12],
                       "cantidad": qty, "precio": 24130})

    # 6100 BOTA T/SEP GMZA — T36:4, T37:4, T38:6, T39:4, T40:2
    for talle, qty in [(36,4),(37,4),(38,6),(39,4),(40,2)]:
        ren_p1.append({"articulo": A6100[talle],
                       "descripcion": f"6100 NEGRO BOTA T/SEP C/ALTA GMZA T{talle}",
                       "codigo_sinonimo": f"99906100{talle:04d}"[:12],
                       "cantidad": qty, "precio": 27940})

    # 4200 BOTA C/ALTA CIERRE — T36:2, T37:2, T38:4, T39:1, T40:4
    for talle, qty in [(36,2),(37,2),(38,4),(39,1),(40,4)]:
        ren_p1.append({"articulo": A4200[talle],
                       "descripcion": f"4200 NEGRO BOTA C/ALTA 1 CIERRE DET COST T{talle}",
                       "codigo_sinonimo": f"99904200{talle:04d}"[:12],
                       "cantidad": qty, "precio": 33020})

    # 6000 BOTA COSTURA — T35:2, T40:2
    for talle, qty in [(35,2),(40,2)]:
        ren_p1.append({"articulo": A6000[talle],
                       "descripcion": f"6000 NEGRO BOTA DET DE COSTURA T{talle}",
                       "codigo_sinonimo": f"99906000{talle:04d}"[:12],
                       "cantidad": qty, "precio": 25400})

    # 3150 BOTA HEBILLA — T39:2, T40:2
    for talle, qty in [(39,2),(40,2)]:
        ren_p1.append({"articulo": A3150[talle],
                       "descripcion": f"3150 NEGRO BOTA CANA ALTA DET HEBILLA T{talle}",
                       "codigo_sinonimo": f"99903150{talle:04d}"[:12],
                       "cantidad": qty, "precio": 31750})

    # 4000 BOTA NUEVA — T36:2, T37:2, T38:4, T39:4, T40:4
    for talle, qty in [(36,2),(37,2),(38,4),(39,4),(40,4)]:
        sin = f"99904000{talle:04d}"[:12]
        sin_full = f"999040000{talle:02d}"
        art_cod = cod_map.get(sin_full)
        ren_p1.append({"articulo": art_cod,
                       "descripcion": f"4000 NEGRO BOTA T{talle}",
                       "codigo_sinonimo": sin_full,
                       "cantidad": qty, "precio": 25400})

    # Z30 ENT1 (pinchados) — T35:1, T36:1, T37:0, T38:2, T39:2, T40:3, T41:2, T42:2, T43:2
    for talle, qty in [(35,1),(36,1),(38,2),(39,2),(40,3),(41,2),(42,2),(43,2)]:
        ren_p1.append({"articulo": AZ30[talle],
                       "descripcion": f"Z30 NEGRO CH SANDALIA FAJA T/ACRILICO T{talle}",
                       "codigo_sinonimo": f"99900Z3010{talle:02d}",
                       "cantidad": qty, "precio": 31000})  # costo estimado ~50% de PVP 62000

    cab_p1 = {
        "empresa":            "CALZALINDO",
        "cuenta":             999,
        "denominacion":       "PARADOJA SHOES S.A",
        "fecha_comprobante":  date(2026, 4, 6),
        "fecha_entrega":      date(2026, 5, 15),
        "observaciones":      "Botas OI2627 + Sandalia Z30 ENT1. Entrega abr/may26.",
    }

    pares_p1 = sum(r["cantidad"] for r in ren_p1)
    monto_p1 = sum(r["cantidad"] * r["precio"] for r in ren_p1)
    print(f"  Renglones: {len(ren_p1)} | Pares: {pares_p1} | Costo: ${monto_p1:,.0f}")
    for r in ren_p1:
        flag = " ⚠️ código pendiente" if r["articulo"] is None else ""
        print(f"    [{r['codigo_sinonimo']}] {r['descripcion'][:45]:<45} x{r['cantidad']:>2} ${r['precio']:>6,}{flag}")

    # ── PEDIDO 2: Z70 ENT1 (jul/ago'26) ─────────────────────────────────────
    print("\n[3] PEDIDO 2 — Z70 ZUECO ENT1 — entrega jul/ago'26")
    print("-"*40)

    ren_p2 = [
        {"articulo": cod_map.get("999Z70110137"),
         "descripcion": "Z70 CRISTAL ZUECO FAJA T/ACRILICO T37",
         "codigo_sinonimo": "999Z70110137", "cantidad": 2, "precio": 30800},
        {"articulo": AZ70_T38,
         "descripcion": "Z70 CRISTAL ZUECO FAJA T/ACRILICO T38",
         "codigo_sinonimo": "999Z70110138", "cantidad": 2, "precio": 30800},
        {"articulo": cod_map.get("999Z70110139"),
         "descripcion": "Z70 CRISTAL ZUECO FAJA T/ACRILICO T39",
         "codigo_sinonimo": "999Z70110139", "cantidad": 2, "precio": 30800},
    ]

    cab_p2 = {
        "empresa":            "CALZALINDO",
        "cuenta":             999,
        "denominacion":       "PARADOJA SHOES S.A",
        "fecha_comprobante":  date(2026, 4, 6),
        "fecha_entrega":      date(2026, 7, 15),
        "observaciones":      "Zueco Z70 ENT1. Entrega jul/ago26.",
    }

    pares_p2 = sum(r["cantidad"] for r in ren_p2)
    monto_p2 = sum(r["cantidad"] * r["precio"] for r in ren_p2)
    print(f"  Renglones: {len(ren_p2)} | Pares: {pares_p2} | Costo: ${monto_p2:,.0f}")
    for r in ren_p2:
        flag = " ⚠️ código pendiente" if r["articulo"] is None else ""
        print(f"    [{r['codigo_sinonimo']}] {r['descripcion']:<45} x{r['cantidad']:>2} ${r['precio']:>6,}{flag}")

    # ── PEDIDO 3: Z30 ENT2 curva vel_real (oct/nov'26) ───────────────────────
    print("\n[4] PEDIDO 3 — Z30 ENT2 — entrega oct/nov'26")
    print("-"*40)

    ren_p3 = []
    for talle, qty in [(35,1),(36,2),(37,3),(38,5),(39,4),(40,3),(41,2),(42,1),(43,1)]:
        ren_p3.append({"articulo": AZ30[talle],
                       "descripcion": f"Z30 NEGRO CH SANDALIA FAJA T/ACRILICO T{talle}",
                       "codigo_sinonimo": f"99900Z3010{talle:02d}",
                       "cantidad": qty, "precio": 31000})

    cab_p3 = {
        "empresa":            "CALZALINDO",
        "cuenta":             999,
        "denominacion":       "PARADOJA SHOES S.A",
        "fecha_comprobante":  date(2026, 4, 6),
        "fecha_entrega":      date(2026, 10, 15),
        "observaciones":      "Sandalia Z30 ENT2 curva vel_real. Entrega oct/nov26.",
    }

    pares_p3 = sum(r["cantidad"] for r in ren_p3)
    monto_p3 = sum(r["cantidad"] * r["precio"] for r in ren_p3)
    print(f"  Renglones: {len(ren_p3)} | Pares: {pares_p3} | Costo: ${monto_p3:,.0f}")
    for r in ren_p3:
        print(f"    [{r['codigo_sinonimo']}] {r['descripcion']:<45} x{r['cantidad']:>2} ${r['precio']:>6,}")

    # ── RESUMEN ───────────────────────────────────────────────────────────────
    total_pares = pares_p1 + pares_p2 + pares_p3
    total_monto = monto_p1 + monto_p2 + monto_p3
    print(f"\n{'='*65}")
    print(f"  TOTAL 3 PEDIDOS: {total_pares} pares — ${total_monto:,.0f}")
    print(f"  Pedido 1 (botas+Z30 ENT1): {pares_p1}p  ${monto_p1:,.0f}")
    print(f"  Pedido 2 (Z70):            {pares_p2}p  ${monto_p2:,.0f}")
    print(f"  Pedido 3 (Z30 ENT2):       {pares_p3}p  ${monto_p3:,.0f}")
    print(f"{'='*65}")

    if dry_run:
        print("\n  [DRY RUN] Nada fue escrito. Pasá --ejecutar para confirmar.")
        return

    # Validar que no haya artículos None (pendientes de alta)
    todos = ren_p1 + ren_p2 + ren_p3
    sin_codigo = [r for r in todos if r["articulo"] is None]
    if sin_codigo:
        print(f"\n  ❌ ERROR: {len(sin_codigo)} renglones sin código de artículo:")
        for r in sin_codigo:
            print(f"     {r['codigo_sinonimo']} — {r['descripcion']}")
        print("  Corregí el alta de artículos y volvé a ejecutar.")
        sys.exit(1)

    confirmacion = input("\n¿Confirmar INSERT en producción? (s/N): ").strip().lower()
    if confirmacion != "s":
        print("Cancelado.")
        sys.exit(0)

    n1 = insertar_pedido(cab_p1, ren_p1, dry_run=False)
    print(f"\n  ✅ Pedido 1 insertado: #{n1}")

    n2 = insertar_pedido(cab_p2, ren_p2, dry_run=False)
    print(f"  ✅ Pedido 2 insertado: #{n2}")

    n3 = insertar_pedido(cab_p3, ren_p3, dry_run=False)
    print(f"  ✅ Pedido 3 insertado: #{n3}")

    print(f"\n  Verificar:")
    print(f"    SELECT * FROM MSGESTION01.dbo.pedico2 WHERE numero IN ({n1},{n2},{n3})")
    print(f"    SELECT * FROM MSGESTION01.dbo.pedico1 WHERE numero IN ({n1},{n2},{n3})")


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "--dry-run"
    main(dry_run=(modo != "--ejecutar"))
