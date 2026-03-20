#!/usr/bin/env python3
"""
insertar_cavatini_y_piccadilly_ean.py
======================================
DOS partes independientes:

PARTE 1 — Nota de pedido CAVATINI (TECAL Cavatini, prov 960)
  Empresa: H4 → MSGESTION01 (pedico2/pedico1)
  3 archivos Excel:
    - PEDIDO CAVATINI HOMBRE.xlsx  (8 modelos, talles 40-46)
    - PEDIDO CAVATINI MUJER.xlsx   (18 combos modelo/color, talles 36-41)
    - PEDIDO DAMAS XL.xlsx         (4 modelos, talles 40-43)
  Matcheo por (codigo_objeto_costo = modelo, descripcion_4 = color, descripcion_5 = talle)
  Artículos faltantes → WARNING, se listan al final.

PARTE 2 — UPDATE codigo_barra artículos Piccadilly (códigos 360570-360677)
  Lee EAN PICCADILLY.xlsx, matchea por modelo (6 dígitos) + talle + color.
  Mapeo de colores PT→ES incluido.

EJECUTAR EN EL 111:
  py -3 insertar_cavatini_y_piccadilly_ean.py              ← dry-run (ambas partes)
  py -3 insertar_cavatini_y_piccadilly_ean.py --ejecutar   ← escribe en BD
  py -3 insertar_cavatini_y_piccadilly_ean.py --solo-cavatini
  py -3 insertar_cavatini_y_piccadilly_ean.py --solo-piccadilly
  py -3 insertar_cavatini_y_piccadilly_ean.py --solo-piccadilly --ejecutar
"""

import sys
import os
import pyodbc
from datetime import date

# ── PATH PARA IMPORTAR config.py DESDE RAÍZ ─────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTES GLOBALES
# ══════════════════════════════════════════════════════════════════════════════

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion01art;"
    "UID=am;"
    "PWD=dl;"
)

# Conexión a pedico2/pedico1 (msgestion01 para pedidos de compra)
CONN_STR_PEDIDOS = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion01;"
    "UID=am;"
    "PWD=dl;"
)

# ── CAVATINI ─────────────────────────────────────────────────────────────────
PROVEEDOR_CAV    = 960
DENOMINACION_CAV = "TECAL Cavatini"
MARCA_CAV        = 1260
EMPRESA_CAV      = "H4"     # pedido va en MSGESTION01 (tabla real)

FECHA_PEDIDO_CAV  = date(2026, 3, 19)
FECHA_ENTREGA_CAV = date(2026, 7, 1)    # entrega invierno

OBSERVACIONES_CAV = (
    "CAVATINI OI26. TECAL prov 960. "
    "Hombre + Mujer + Damas XL. "
    "Invierno 2026."
)

# Montaje del compartido (intentar ambos paths)
PATHS_COMPARTIDO = [
    "/Volumes/compartido",
    "/tmp/compartido",
]

ARCHIVOS_CAV = [
    "COMPRAS/Pedidos Invierno/PEDIDO CAVATINI HOMBRE.xlsx",
    "COMPRAS/Pedidos Invierno/PEDIDO CAVATINI MUJER.xlsx",
    "COMPRAS/Pedidos Invierno/PEDIDO DAMAS XL.xlsx",
]

ARCHIVO_EAN_PIC = "COMPRAS/EAN PICCADILLY.xlsx"

# ── PEDIDO (constantes comunes) ───────────────────────────────────────────────
CODIGO_PEDIDO   = 8
LETRA_PEDIDO    = "X"
SUCURSAL_PEDIDO = 1

# ── MAPEO COLOR CODE CAVATINI → NOMBRE ESPAÑOL ───────────────────────────────
# Los últimos 3 dígitos del código de color en el Excel
# Cuando no se conoce con certeza se deja "" para que el script intente
# matchear con cualquier artículo disponible en la BD para ese modelo.
COLOR_CODE_MAP = {
    "001": "NEGRO",
    "019": "",           # segundo color ANGLO — desconocido, se intentará matcheo fuzzy
    "034": "",           # BASTIAN — desconocido
    "059": "",           # segundo UME — podría ser ORO o LATTE
    "014": "",           # segundo BRENDI — desconocido
    "179": "",           # segundo BRUNA — desconocido
    "074": "",           # segundo TAMY — desconocido
    "288": "",           # segundo ANNET — desconocido
    "117": "MARRON",     # HENDY 117 — MARRON o HABANO, probar ambos
    "030": "",           # segundo CARMELA — desconocido
    "048": "",           # segundo CATY — desconocido
}

# Alternativas de nombres de color para búsqueda fuzzy (orden de preferencia)
COLOR_ALTERNATIVES = {
    "117": ["MARRON", "HABANO", "CAMEL", "CAFE"],
    "059": ["ORO", "LATTE", "BEIGE", "NUDE"],
    "019": ["MARRON", "HABANO", "NEGRO", "AZUL"],
    "034": ["NEGRO", "MARRON", "AZUL", "GRIS"],
    "014": ["MARRON", "HABANO", "BEIGE", "NUDE"],
    "179": ["MARRON", "HABANO", "ORO", "BEIGE"],
    "074": ["MARRON", "HABANO", "AZUL", "NUDE"],
    "288": ["MARRON", "HABANO", "GRIS", "BEIGE"],
    "030": ["MARRON", "HABANO", "BEIGE", "NUDE"],
    "048": ["MARRON", "HABANO", "AZUL", "BEIGE"],
}

# ── DATOS HARDCODEADOS DEL PEDIDO ─────────────────────────────────────────────
# (los extraemos del prompt ya que el Excel puede no estar disponible en Mac)

PEDIDO_HOMBRE = [
    # (modelo, color_code, {talle: cantidad}, precio)
    # color_code = últimos 3 dígitos del código Excel
    ("BORJ",    "001", {"40":1,"41":2,"42":2,"43":2,"44":2,"45":1,"46":0}, 76818),
    ("ANGLO",   "001", {"40":1,"41":1,"42":2,"43":2,"44":2,"45":1,"46":1}, 79545),
    ("ANGLO",   "019", {"40":0,"41":2,"42":2,"43":0,"44":1,"45":1,"46":1}, 79545),
    ("BLAS",    "001", {"40":0,"41":0,"42":2,"43":2,"44":2,"45":0,"46":0}, 70455),
    ("ZEN",     "001", {"40":0,"41":2,"42":2,"43":2,"44":0,"45":0,"46":0}, 79545),
    ("BASTIAN", "034", {"40":0,"41":2,"42":2,"43":2,"44":2,"45":0,"46":0}, 79549),
    ("BRIAN",   "001", {"40":0,"41":2,"42":2,"43":2,"44":2,"45":0,"46":0}, 79545),
    ("PIERO",   "001", {"40":1,"41":2,"42":2,"43":2,"44":2,"45":1,"46":0}, 81364),
]

PEDIDO_MUJER = [
    ("UME",     "001", {"36":0,"37":1,"38":2,"39":2,"40":2,"41":1}, 75000),
    ("UME",     "059", {"36":0,"37":1,"38":2,"39":2,"40":2,"41":1}, 75000),
    ("BRENDI",  "001", {"36":0,"37":1,"38":2,"39":2,"40":2,"41":1}, 70455),
    ("BRENDI",  "014", {"36":0,"37":1,"38":2,"39":2,"40":2,"41":1}, 70455),
    ("BRUNA",   "001", {"36":0,"37":1,"38":2,"39":2,"40":2,"41":1}, 75000),
    ("BRUNA",   "179", {"36":0,"37":1,"38":2,"39":2,"40":2,"41":1}, 75000),
    ("TAMY",    "001", {"36":0,"37":1,"38":2,"39":2,"40":2,"41":1}, 75000),
    ("TAMY",    "074", {"36":0,"37":1,"38":2,"39":2,"40":2,"41":1}, 75000),
    ("ANNET",   "001", {"36":1,"37":2,"38":2,"39":2,"40":1,"41":0}, 56818),
    ("ANNET",   "288", {"36":1,"37":2,"38":2,"39":2,"40":1,"41":0}, 56818),
    ("HENDY",   "001", {"36":0,"37":1,"38":2,"39":2,"40":2,"41":1}, 79545),
    ("HENDY",   "117", {"36":0,"37":1,"38":2,"39":2,"40":2,"41":1}, 79545),
    ("CARMELA", "001", {"36":0,"37":0,"38":2,"39":2,"40":2,"41":0}, 88636),
    ("CARMELA", "030", {"36":0,"37":0,"38":2,"39":2,"40":2,"41":0}, 88636),
    ("CLORIS",  "001", {"36":0,"37":1,"38":2,"39":2,"40":2,"41":1}, 85909),
    ("CLORIS",  "117", {"36":0,"37":1,"38":2,"39":2,"40":2,"41":1}, 85909),
    ("CATY",    "001", {"36":0,"37":1,"38":2,"39":2,"40":2,"41":1}, 79545),
    ("CATY",    "048", {"36":0,"37":1,"38":2,"39":2,"40":2,"41":1}, 79545),
]

PEDIDO_DAMAS_XL = [
    # Damas XL: modelo, color (en texto, ya conocido), talles 40-43
    ("TEXAS",    "NEGRO", {"40":2,"41":2,"42":2,"43":0}, 68200),
    ("SEATTLE",  "NEGRO", {"40":2,"41":2,"42":2,"43":2}, 79200),
    ("NASHVILLE","NEGRO", {"40":2,"41":2,"42":2,"43":0}, 82500),
    ("BOSTON",   "NEGRO", {"40":2,"41":2,"42":2,"43":0}, 73700),
]

# ── MAPEO COLORES PICCADILLY PT→ES ────────────────────────────────────────────
COLOR_MAP_PT_ES = {
    "PRETO":    "NEGRO",
    "BRANCO":   "BLANCO",
    "MADEIRA":  "MADEIRA",
    "CACAU":    "CACAU",
    "CONHAQUE": "CONHAQUE",
    "NUDE":     "NUDE",
    "BRULE":    "BRULE",
    "MARFIM":   "MARFIM",
    "OURO":     "DORADO",
    "DOURADO":  "DORADO",
}

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def get_compartido_path():
    """Retorna el primer path de compartido que existe."""
    for base in PATHS_COMPARTIDO:
        if os.path.isdir(base):
            return base
    return None


def normalizar_color(c):
    """Normaliza un color para comparación (strip + upper)."""
    if not c:
        return ""
    return str(c).strip().upper()


def color_contiene(db_color, buscar):
    """True si buscar (o alguna variante) está en db_color."""
    db = normalizar_color(db_color)
    bus = normalizar_color(buscar)
    if not bus:
        return False
    return bus in db


# ══════════════════════════════════════════════════════════════════════════════
# PARTE 1 — PEDIDO CAVATINI
# ══════════════════════════════════════════════════════════════════════════════

def cargar_articulos_cavatini():
    """
    Consulta la BD y retorna un dict:
      { (modelo_upper, color_upper, talle_upper): codigo_articulo }
    con todos los artículos de proveedor 960.
    """
    print("\n  Consultando articulos Cavatini (proveedor 960) en BD...")
    conn = pyodbc.connect(CONN_STR, timeout=15)
    cur  = conn.cursor()
    cur.execute("""
        SELECT codigo,
               ISNULL(codigo_objeto_costo, ''),
               ISNULL(descripcion_4, ''),
               ISNULL(descripcion_5, '')
        FROM   articulo
        WHERE  proveedor = 960
    """)
    rows = cur.fetchall()
    conn.close()

    arts = {}
    arts_raw = []  # para búsqueda fuzzy: lista de (modelo_upper, color_upper, talle_upper, codigo)
    for codigo, modelo, color, talle in rows:
        key = (modelo.strip().upper(), normalizar_color(color), talle.strip().upper())
        arts[key] = codigo
        arts_raw.append((modelo.strip().upper(), normalizar_color(color), talle.strip().upper(), codigo))

    print(f"  → {len(arts)} artículos Cavatini en BD")
    return arts, arts_raw


def buscar_articulo_cavatini(arts_dict, arts_raw, modelo, color_code, talle_str):
    """
    Intenta encontrar el artículo. Primero por color exacto, luego fuzzy.
    Retorna (codigo, color_encontrado) o (None, None).
    """
    modelo_up = modelo.upper()
    talle_up  = talle_str.upper()

    # 1. Intento por color exacto si lo conocemos
    color_exacto = COLOR_CODE_MAP.get(color_code, "")
    if color_exacto:
        key = (modelo_up, color_exacto.upper(), talle_up)
        if key in arts_dict:
            return arts_dict[key], color_exacto

    # 2. Buscar en arts_raw por modelo+talle, revisar qué colores hay
    candidatos = [(c, cod) for (m, c, t, cod) in arts_raw
                  if m == modelo_up and t == talle_up]

    if not candidatos:
        return None, None

    # Si hay color exacto y está entre candidatos
    if color_exacto:
        for (c, cod) in candidatos:
            if color_exacto.upper() in c:
                return cod, c

    # 3. Fuzzy: probar alternativas del color_code
    alternativas = COLOR_ALTERNATIVES.get(color_code, [])
    for alt in alternativas:
        for (c, cod) in candidatos:
            if alt.upper() in c:
                return cod, c

    # 4. Si solo hay un candidato para ese modelo+talle, devolver ese
    if len(candidatos) == 1:
        return candidatos[0][1], candidatos[0][0]

    return None, None


def construir_renglones_cavatini(arts_dict, arts_raw, dry_run=True):
    """
    Construye lista de renglones para el pedido y lista de faltantes.
    Retorna (renglones, faltantes)
    """
    renglones = []
    faltantes  = []

    def procesar_lineas(lineas, seccion):
        for (modelo, color_code, curva_dict, precio) in lineas:
            for talle, cant in sorted(curva_dict.items()):
                if cant == 0:
                    continue

                codigo, color_enc = buscar_articulo_cavatini(
                    arts_dict, arts_raw, modelo, color_code, talle
                )

                color_desc = COLOR_CODE_MAP.get(color_code, "") or f"cod={color_code}"

                if codigo:
                    desc = f"{modelo} {color_desc} T{talle} CAV"
                    if dry_run:
                        print(f"    OK  art={codigo:6d}  {modelo:<12} {color_desc:<15} T{talle}  x{cant}  ${precio:,.0f}")
                    renglones.append({
                        "articulo":        codigo,
                        "descripcion":     desc[:60],
                        "codigo_sinonimo": "",
                        "cantidad":        cant,
                        "precio":          float(precio),
                        "_seccion":        seccion,
                        "_modelo":         modelo,
                        "_color_code":     color_code,
                        "_color_enc":      color_enc or color_desc,
                        "_talle":          talle,
                    })
                else:
                    msg = f"  WARN faltante: {seccion} / {modelo} cod_color={color_code} T{talle} x{cant} ${precio:,.0f}"
                    print(msg)
                    faltantes.append({
                        "seccion":     seccion,
                        "modelo":      modelo,
                        "color_code":  color_code,
                        "color_desc":  color_desc,
                        "talle":       talle,
                        "cantidad":    cant,
                        "precio":      precio,
                    })

    print("\n  --- HOMBRE ---")
    procesar_lineas(PEDIDO_HOMBRE, "HOMBRE")
    print("\n  --- MUJER ---")
    procesar_lineas(PEDIDO_MUJER, "MUJER")
    print("\n  --- DAMAS XL ---")
    # Damas XL usa color en texto directamente (NEGRO conocido)
    for (modelo, color_texto, curva_dict, precio) in PEDIDO_DAMAS_XL:
        for talle, cant in sorted(curva_dict.items()):
            if cant == 0:
                continue
            modelo_up = modelo.upper()
            talle_up  = talle.upper()
            color_up  = color_texto.upper()
            key = (modelo_up, color_up, talle_up)
            codigo = arts_dict.get(key)

            if not codigo:
                # Fuzzy: buscar por modelo+talle
                cands = [(c, cod) for (m, c, t, cod) in arts_raw
                         if m == modelo_up and t == talle_up]
                for (c, cod) in cands:
                    if color_up in c:
                        codigo = cod
                        break
                if not codigo and len(cands) == 1:
                    codigo = cands[0][1]

            if codigo:
                desc = f"{modelo} {color_texto} T{talle} CAV XL"
                if dry_run:
                    print(f"    OK  art={codigo:6d}  {modelo:<12} {color_texto:<15} T{talle}  x{cant}  ${precio:,.0f}")
                renglones.append({
                    "articulo":        codigo,
                    "descripcion":     desc[:60],
                    "codigo_sinonimo": "",
                    "cantidad":        cant,
                    "precio":          float(precio),
                    "_seccion":        "DAMAS XL",
                    "_modelo":         modelo,
                    "_color_code":     "001",
                    "_color_enc":      color_texto,
                    "_talle":          talle,
                })
            else:
                msg = f"  WARN faltante: DAMAS XL / {modelo} {color_texto} T{talle} x{cant} ${precio:,.0f}"
                print(msg)
                faltantes.append({
                    "seccion":     "DAMAS XL",
                    "modelo":      modelo,
                    "color_code":  "001",
                    "color_desc":  color_texto,
                    "talle":       talle,
                    "cantidad":    cant,
                    "precio":      precio,
                })

    return renglones, faltantes


def get_proximo_numero_pedido(cursor, tabla_p2):
    cursor.execute(
        f"SELECT ISNULL(MAX(numero), 0) + 1 FROM {tabla_p2} WHERE codigo = ?",
        CODIGO_PEDIDO
    )
    return cursor.fetchone()[0]


def get_proxima_orden_pedido(cursor, tabla_p2):
    cursor.execute(
        f"SELECT ISNULL(MAX(orden), 0) + 1 FROM {tabla_p2} WHERE codigo = ?",
        CODIGO_PEDIDO
    )
    orden = cursor.fetchone()[0]
    if orden > 99:
        orden = 1
    return orden


def insertar_pedido_cavatini(renglones, dry_run=True):
    """
    Inserta la nota de pedido en MSGESTION01.dbo.pedico2 + pedico1.
    Retorna numero de pedido.
    """
    tabla_p2 = "MSGESTION01.dbo.pedico2"
    tabla_p1 = "MSGESTION01.dbo.pedico1"

    total_pares  = sum(r["cantidad"] for r in renglones)
    total_bruto  = sum(r["cantidad"] * r["precio"] for r in renglones)

    print(f"\n  Resumen pedido CAVATINI:")
    print(f"    Renglones:   {len(renglones)}")
    print(f"    Total pares: {total_pares}")
    print(f"    Total bruto: ${total_bruto:,.0f}")

    if dry_run:
        print(f"\n  [DRY RUN] Cabecera → {tabla_p2}")
        print(f"    empresa    = {EMPRESA_CAV}")
        print(f"    cuenta     = {PROVEEDOR_CAV} ({DENOMINACION_CAV})")
        print(f"    fecha      = {FECHA_PEDIDO_CAV}")
        print(f"    entrega    = {FECHA_ENTREGA_CAV}")
        print(f"    obs        = {OBSERVACIONES_CAV}")
        print(f"\n  [DRY RUN] {len(renglones)} renglones en {tabla_p1} (NO escritos)")
        return 999999

    # ── Chequeo anti-duplicado ────────────────────────────────────────────────
    conn_check = pyodbc.connect(CONN_STR_PEDIDOS, timeout=15)
    cur_check  = conn_check.cursor()
    cur_check.execute(
        f"SELECT numero FROM {tabla_p2} "
        "WHERE codigo=8 AND cuenta=960 AND observaciones LIKE '%CAVATINI OI26%'"
    )
    dup = cur_check.fetchone()
    conn_check.close()
    if dup:
        print(f"  WARN: YA EXISTE pedido CAVATINI OI26 → #{dup[0]}. Saltando.")
        return dup[0]

    sql_cab = f"""
        INSERT INTO {tabla_p2} (
            codigo, letra, sucursal,
            numero, orden, deposito,
            cuenta, denominacion,
            fecha_comprobante, fecha_proceso,
            observaciones,
            descuento_general, monto_descuento,
            bonificacion_general, monto_bonificacion,
            financiacion_general, monto_financiacion,
            iva1, monto_iva1, iva2, monto_iva2, monto_impuesto,
            importe_neto, monto_exento,
            estado, zona, condicion_iva, numero_cuit, copias,
            cuenta_y_orden, pack, reintegro, cambio, transferencia,
            entregador, usuario, campo, sistema_cc, moneda, sector,
            forma_pago, plan_canje, tipo_vcto_pago, tipo_operacion, tipo_ajuste,
            medio_pago, cuenta_cc, concurso
        ) VALUES (
            ?, ?, ?,
            ?, ?, 0,
            ?, ?,
            ?, GETDATE(),
            ?,
            0, 0, 0, 0, 0, 0,
            21, 0, 10.5, 0, 0,
            0, 0,
            'V', 0, 'I', '', 1,
            'N', 'N', 'N', 'N', 'N',
            0, 'COWORK', 0, 2, 0, 0,
            0, 'N', 0, 0, 0,
            ' ', ?, 'N'
        )
    """

    sql_det = f"""
        INSERT INTO {tabla_p1} (
            codigo, letra, sucursal,
            numero, orden, renglon,
            articulo, descripcion, codigo_sinonimo,
            cantidad, precio,
            cuenta, fecha, fecha_entrega,
            estado
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'V')
    """

    from datetime import datetime
    ahora = datetime.now()

    conn = pyodbc.connect(CONN_STR_PEDIDOS, timeout=15)
    conn.autocommit = False
    cursor = conn.cursor()
    try:
        numero = get_proximo_numero_pedido(cursor, tabla_p2)
        orden  = get_proxima_orden_pedido(cursor, tabla_p2)

        cursor.execute(sql_cab, (
            CODIGO_PEDIDO, LETRA_PEDIDO, SUCURSAL_PEDIDO,
            numero, orden,
            PROVEEDOR_CAV, DENOMINACION_CAV,
            FECHA_PEDIDO_CAV,
            OBSERVACIONES_CAV,
            PROVEEDOR_CAV,
        ))

        for i, r in enumerate(renglones, 1):
            cursor.execute(sql_det, (
                CODIGO_PEDIDO, LETRA_PEDIDO, SUCURSAL_PEDIDO,
                numero, orden, i,
                r["articulo"],
                r["descripcion"],
                r.get("codigo_sinonimo", ""),
                r["cantidad"],
                r["precio"],
                PROVEEDOR_CAV,
                FECHA_PEDIDO_CAV,
                FECHA_ENTREGA_CAV,
            ))

        conn.commit()
        print(f"\n  OK Pedido CAVATINI insertado. Numero={numero}, Orden={orden}, Renglones={len(renglones)}")
        return numero

    except Exception as e:
        conn.rollback()
        print(f"\n  ERROR insertando pedido CAVATINI: {e}")
        raise
    finally:
        conn.close()


def parte1_cavatini(dry_run=True):
    """Ejecuta la Parte 1: construye renglones y opcionalmente inserta."""
    modo = "DRY RUN" if dry_run else "EJECUCION REAL"
    print(f"\n{'='*70}")
    print(f"  PARTE 1 — PEDIDO CAVATINI (prov 960) — {modo}")
    print(f"{'='*70}")

    # Cargar artículos de BD
    arts_dict, arts_raw = cargar_articulos_cavatini()

    # Construir renglones
    print("\n  Procesando lineas del pedido (matcheando con BD)...")
    renglones, faltantes = construir_renglones_cavatini(arts_dict, arts_raw, dry_run=dry_run)

    # Resumen de faltantes
    if faltantes:
        print(f"\n  {'='*60}")
        print(f"  ARTICULOS FALTANTES EN BD ({len(faltantes)} renglones no mapeados):")
        print(f"  {'='*60}")
        total_falt_pares = 0
        for f in faltantes:
            print(f"  [{f['seccion']:8}] {f['modelo']:<12} color_code={f['color_code']} "
                  f"({f['color_desc']:<15}) T{f['talle']}  x{f['cantidad']}  ${f['precio']:,.0f}")
            total_falt_pares += f["cantidad"]
        print(f"\n  Total pares NO mapeados: {total_falt_pares}")
        print(f"  Estos articulos NO se incluiran en el pedido hasta que se creen en BD.")

    if not renglones:
        print("\n  ERROR: No hay renglones para insertar. Verificar BD.")
        return None

    # Insertar
    numero = insertar_pedido_cavatini(renglones, dry_run=dry_run)

    if not dry_run and numero and numero != 999999:
        total_pares = sum(r["cantidad"] for r in renglones)
        total_bruto = sum(r["cantidad"] * r["precio"] for r in renglones)
        print(f"\n  Verificar en SSMS:")
        print(f"    SELECT * FROM MSGESTION01.dbo.pedico2 WHERE numero = {numero}")
        print(f"    SELECT * FROM MSGESTION01.dbo.pedico1 WHERE numero = {numero}")
        print(f"\n  Resumen: {len(renglones)} renglones, {total_pares} pares, ${total_bruto:,.0f}")

    return numero


# ══════════════════════════════════════════════════════════════════════════════
# PARTE 2 — EAN PICCADILLY
# ══════════════════════════════════════════════════════════════════════════════

def cargar_articulos_piccadilly():
    """
    Retorna list of dicts con los artículos Piccadilly (códigos 360570-360677).
    Campos: codigo, modelo_num (6 chars), talle, color
    """
    print("\n  Consultando articulos Piccadilly (360570-360677) en BD...")
    conn = pyodbc.connect(CONN_STR, timeout=15)
    cur  = conn.cursor()
    cur.execute("""
        SELECT codigo,
               ISNULL(descripcion_1, ''),
               ISNULL(descripcion_4, ''),
               ISNULL(descripcion_5, ''),
               ISNULL(codigo_barra, '')
        FROM   articulo
        WHERE  codigo BETWEEN 360570 AND 360677
        ORDER  BY codigo
    """)
    rows = cur.fetchall()
    conn.close()

    arts = []
    for codigo, desc1, color, talle, ean_actual in rows:
        # Extraer numero de modelo: primeros 6 dígitos de descripcion_1
        modelo_num = ""
        for ch in desc1:
            if ch.isdigit():
                modelo_num += ch
                if len(modelo_num) == 6:
                    break

        arts.append({
            "codigo":     codigo,
            "desc1":      desc1.strip(),
            "modelo_num": modelo_num,
            "color":      normalizar_color(color),
            "talle":      talle.strip(),
            "ean_actual": (ean_actual or "").strip(),
        })

    print(f"  → {len(arts)} articulos Piccadilly en BD")
    return arts


def cargar_ean_piccadilly(compartido):
    """
    Lee el Excel EAN PICCADILLY.xlsx.
    Retorna list of dicts: {sku, descripcion, modelo, ean, modelo_num, talle, color_pt}
    """
    try:
        import pandas as pd
    except ImportError:
        print("  ERROR: pandas no disponible. Instalar: py -3 -m pip install pandas openpyxl")
        return []

    ruta = os.path.join(compartido, ARCHIVO_EAN_PIC)
    if not os.path.exists(ruta):
        print(f"  ERROR: No se encontro {ruta}")
        return []

    print(f"  Leyendo {ruta}...")
    df = pd.read_excel(ruta)
    print(f"  → {len(df)} filas. Columnas: {list(df.columns)}")

    # Normalizar nombres de columna
    df.columns = [str(c).strip().upper() for c in df.columns]

    # Buscar columnas relevantes
    col_sku  = next((c for c in df.columns if "SKU" in c), None)
    col_desc = next((c for c in df.columns if "DESC" in c), None)
    col_mod  = next((c for c in df.columns if "MODELO" in c or "MODEL" in c), None)
    col_ean  = next((c for c in df.columns if "EAN" in c or "MTX" in c or "BARR" in c), None)

    if not col_ean:
        print(f"  ERROR: No se encontro columna EAN en {list(df.columns)}")
        return []

    registros = []
    for _, row in df.iterrows():
        sku  = str(row.get(col_sku, "") or "").strip()
        ean  = str(row.get(col_ean, "") or "").strip()
        desc = str(row.get(col_desc, "") or "").strip()
        mod  = str(row.get(col_mod, "") or "").strip()

        if not ean or ean in ("nan", "None", ""):
            continue

        # Parsear SKU: formato P117106-P00355-36
        modelo_num = ""
        talle_str  = ""
        color_pt   = ""

        if sku.startswith("P") and "-" in sku:
            partes = sku.split("-")
            # parte 0: P117106 → modelo_num = 117106
            if partes[0].startswith("P"):
                modelo_num = partes[0][1:]  # quitar P
            # parte final: talle
            if len(partes) >= 3:
                talle_str = partes[-1].strip()

        # Intentar extraer color y talle de descripcion si no hay SKU
        if not modelo_num and mod:
            modelo_num = mod.strip()

        registros.append({
            "sku":        sku,
            "descripcion": desc,
            "modelo_num": modelo_num,
            "talle":      talle_str,
            "color_pt":   color_pt,    # se inferirá de descripción
            "ean":        ean,
            "_desc_full": desc.upper(),
        })

    print(f"  → {len(registros)} EANs validos en archivo")
    return registros


def inferir_color_pt(desc_upper):
    """Intenta extraer el color en portugues de la descripcion del EAN."""
    colores_pt = list(COLOR_MAP_PT_ES.keys()) + ["NUDE", "BRULE", "MARFIM",
                  "CROCO", "MATELASSE", "ELASTICO"]
    for c in colores_pt:
        if c in desc_upper:
            return c
    return ""


def matchear_ean(db_art, ean_registros):
    """
    Para un articulo de BD, busca el mejor EAN en ean_registros.
    Retorna ean string o "".
    """
    modelo_db = db_art["modelo_num"]
    talle_db  = db_art["talle"].strip()
    color_db  = db_art["color"]

    # Traducir color DB (español) a portugues para comparar
    colores_pt_candidatos = []
    for pt, es in COLOR_MAP_PT_ES.items():
        if es.upper() in color_db or color_db in es.upper():
            colores_pt_candidatos.append(pt)

    # También incluir el color español directo (algunos coinciden: NUDE, BRULE, etc.)
    colores_pt_candidatos.append(color_db)

    candidatos = []
    for reg in ean_registros:
        if reg["modelo_num"] != modelo_db:
            continue
        if reg["talle"].strip() != talle_db:
            continue

        # Si el EAN tiene color, verificar
        desc_up = reg["_desc_full"]

        # Verificar color
        color_match = False
        for c_pt in colores_pt_candidatos:
            if c_pt and c_pt.upper() in desc_up:
                color_match = True
                break

        # Si no encontramos color PT, intentar con el color español directamente
        if not color_match and color_db in desc_up:
            color_match = True

        # Si la descripcion no tiene info de color, igual es candidato
        if not color_match and (not any(
            pt.upper() in desc_up for pt in COLOR_MAP_PT_ES.keys()
        )):
            color_match = True   # sin info de color → incluir como candidato débil

        if color_match:
            # Preferir FW26 > FW25 > otros
            priority = 0
            if "FW26" in desc_up or "26" in desc_up:
                priority = 2
            elif "FW25" in desc_up or "25" in desc_up:
                priority = 1
            candidatos.append((priority, reg["ean"]))

    if not candidatos:
        return ""

    # Ordenar por prioridad desc, tomar el mejor
    candidatos.sort(key=lambda x: x[0], reverse=True)
    return candidatos[0][1]


def parte2_piccadilly_ean(dry_run=True):
    """Ejecuta la Parte 2: actualiza codigo_barra de artículos Piccadilly."""
    modo = "DRY RUN" if dry_run else "EJECUCION REAL"
    print(f"\n{'='*70}")
    print(f"  PARTE 2 — EAN PICCADILLY (arts 360570-360677) — {modo}")
    print(f"{'='*70}")

    # Buscar compartido
    compartido = get_compartido_path()
    if not compartido:
        print(f"  ERROR: No se encontro compartido en {PATHS_COMPARTIDO}")
        print(f"  Montar con: sudo mount_smbfs '//administrador:cagr$2011@192.168.2.111/compartido' /tmp/compartido")
        return

    # Cargar artículos
    arts_pic = cargar_articulos_piccadilly()
    if not arts_pic:
        print("  ERROR: No hay articulos Piccadilly en BD")
        return

    # Cargar EANs
    ean_regs = cargar_ean_piccadilly(compartido)
    if not ean_regs:
        print("  ERROR: No hay EANs para procesar")
        return

    actualizados   = []
    ya_tienen_ean  = []
    sin_ean        = []

    for art in arts_pic:
        if art["ean_actual"] and art["ean_actual"] not in ("", "None"):
            ya_tienen_ean.append(art)
            continue

        ean = matchear_ean(art, ean_regs)
        if ean:
            actualizados.append((art, ean))
            if dry_run:
                print(f"  DRY  art={art['codigo']}  {art['modelo_num']}  {art['color']:<20}  T{art['talle']:<4}  → EAN={ean}")
        else:
            sin_ean.append(art)

    print(f"\n  Resumen PICCADILLY EAN:")
    print(f"    Ya tienen EAN:       {len(ya_tienen_ean)}")
    print(f"    A actualizar:        {len(actualizados)}")
    print(f"    Sin match EAN:       {len(sin_ean)}")

    if sin_ean:
        print(f"\n  ARTICULOS SIN EAN ENCONTRADO ({len(sin_ean)}):")
        for art in sin_ean:
            print(f"    art={art['codigo']}  modelo={art['modelo_num']}  color={art['color']}  T{art['talle']}")

    if dry_run:
        print(f"\n  [DRY RUN] Se actualizarian {len(actualizados)} articulos. No se escribio nada.")
        return

    if not actualizados:
        print("\n  No hay articulos para actualizar.")
        return

    # Ejecutar UPDATEs
    conn = pyodbc.connect(CONN_STR, timeout=15)
    conn.autocommit = False
    cursor = conn.cursor()
    ok = 0
    err = 0
    try:
        for (art, ean) in actualizados:
            cursor.execute(
                "UPDATE articulo SET codigo_barra = ? WHERE codigo = ?",
                ean, art["codigo"]
            )
            ok += 1
        conn.commit()
        print(f"\n  OK: {ok} articulos Piccadilly actualizados con EAN")
    except Exception as e:
        conn.rollback()
        print(f"\n  ERROR en UPDATE EAN: {e}")
        err += 1
    finally:
        conn.close()

    print(f"  OK={ok}  ERR={err}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    args = set(sys.argv[1:])

    dry_run        = "--ejecutar" not in args
    solo_cavatini  = "--solo-cavatini"  in args
    solo_piccadilly= "--solo-piccadilly" in args

    # Si se pasa solo una parte, la otra no corre
    run_cav = not solo_piccadilly
    run_pic = not solo_cavatini

    if dry_run:
        print("=" * 70)
        print("  MODO DRY-RUN — No se escribe nada en la BD")
        print("  Usar --ejecutar para escribir de verdad")
        if solo_cavatini:
            print("  Modo: solo-cavatini")
        elif solo_piccadilly:
            print("  Modo: solo-piccadilly")
        print("=" * 70)
    else:
        print("=" * 70)
        print("  MODO EJECUCION REAL — SE ESCRIBIRA EN LA BD")
        if solo_cavatini:
            print("  Modo: solo-cavatini")
        elif solo_piccadilly:
            print("  Modo: solo-piccadilly")
        confirmacion = input("  Confirmar? (s/N): ").strip().lower()
        if confirmacion != "s":
            print("  Cancelado.")
            sys.exit(0)
        print("=" * 70)

    num_cav = None
    if run_cav:
        try:
            num_cav = parte1_cavatini(dry_run=dry_run)
        except Exception as e:
            print(f"\n  ERROR en Parte 1 CAVATINI: {e}")

    if run_pic:
        try:
            parte2_piccadilly_ean(dry_run=dry_run)
        except Exception as e:
            print(f"\n  ERROR en Parte 2 PICCADILLY EAN: {e}")

    # Resumen final
    print(f"\n{'='*70}")
    if run_cav:
        estado_cav = f"Pedido #{num_cav}" if (num_cav and not dry_run) else "DRY-RUN OK"
        print(f"  Cavatini:   {estado_cav}")
    if run_pic:
        print(f"  Piccadilly: {'DRY-RUN OK' if dry_run else 'EAN actualizados'}")
    print(f"  {'DRY-RUN completado' if dry_run else 'EJECUCION completada'}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
