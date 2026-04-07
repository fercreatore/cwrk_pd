#!/usr/bin/env python3
"""
Insertar pedido EL FARAON - Invierno 2026
Proveedor: 118 (EL FARAON)
Empresa: CALZALINDO -> INSERT en msgestion01.dbo.pedico2 + pedico1
414 pares, monto ~$5.661.426

Fuente Excel: PEDIDO FARAON.xlsx
  - Filas 2-6: datos (5 filas de producto)
  - Col A: ARTICULO (55, 255, 360)
  - Col B: COLOR (Azul, Negro, Rosa, Red negro)
  - Cols C-AA: talles 22 a 46 con cantidades
  - Col AB: TOTAL pares
  - Col AC: PRECIO 23/34  (talles 23-34)
  - Col AD: PRECIO 35-40  (talles 35-40)
  - Col AE: PRECIO 41-45  (talles 41-45)
  - Col AG: SUBRUBRO

ESPECIAL: 3 precios distintos por rango de talle.

Uso:
  python insertar_faraon.py                  # dry run (default)
  python insertar_faraon.py --dry-run        # dry run explicito
  python insertar_faraon.py --ejecutar       # INSERT real
"""

import sys
import os
import pyodbc
from datetime import date

try:
    import openpyxl
except ImportError:
    print("ERROR: pip install openpyxl")
    sys.exit(1)

# ── CONFIGURACION ──────────────────────────────────────────
DRY_RUN = True  # default, override con --ejecutar

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;DATABASE=msgestion01;"
    "UID=am;PWD=dl;TrustServerCertificate=yes;Encrypt=no"
)

PROVEEDOR = 118
DENOMINACION = "EL FARAON"
FECHA = date.today().strftime('%Y%m%d')

TOTAL_ESPERADO_PARES = 414
TOTAL_ESPERADO_MONTO = 5661426

# Ruta al Excel - intentar varias ubicaciones
EXCEL_PATHS = [
    "/Volumes/compartido/COMPRAS/INVIERNO 2026/El Faraon/Pedidos 05-02 faraon/PEDIDO FARAON.xlsx",
    os.path.join(os.path.dirname(__file__), "..", "_excel_pedidos", "PEDIDO_FARAON.xlsx"),
    r"C:\cowork_pedidos\_excel_pedidos\PEDIDO_FARAON.xlsx",
]

# Mapeo de columnas del Excel (0-indexed)
# C=2 es talle 22, D=3 es talle 23, ... AA=26 es talle 46
# Pero segun el usuario: cols C-AA = talles 22 a 46 (25 columnas)
COL_ARTICULO = 0   # A
COL_COLOR = 1      # B
# Talles: columnas C(2) a AA(26) = talles 22 a 46
COL_TALLE_INICIO = 2   # C = talle 22
TALLE_INICIO = 22
TALLE_FIN = 46
COL_TOTAL = 27     # AB
COL_PRECIO_23_34 = 28  # AC
COL_PRECIO_35_40 = 29  # AD
COL_PRECIO_41_45 = 30  # AE
# AG = 32 (subrubro, no se usa para insert)

# Filas de datos (1-indexed en Excel, 0-indexed en openpyxl iter)
FILA_DATOS_INICIO = 2  # Excel row 2
FILA_DATOS_FIN = 6     # Excel row 6 (inclusive)


def encontrar_excel():
    """Busca el Excel en las rutas posibles."""
    for path in EXCEL_PATHS:
        if os.path.exists(path):
            return path
    print("ERROR: No se encontro el Excel en ninguna ruta:")
    for p in EXCEL_PATHS:
        print(f"  - {p}")
    print("\nCopiar el Excel a _excel_pedidos/PEDIDO_FARAON.xlsx y reintentar.")
    sys.exit(1)


def leer_excel(path):
    """
    Lee el Excel y retorna lista de dicts con los datos del pedido.
    Cada dict: {art_prov, color, talles: {talle: qty}, precio_23_34, precio_35_40, precio_41_45, total_excel}
    """
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active

    # Leer todas las filas en memoria
    rows = list(ws.iter_rows(min_row=FILA_DATOS_INICIO, max_row=FILA_DATOS_FIN, values_only=True))
    wb.close()

    pedido = []
    for row_idx, row in enumerate(rows):
        if row is None or row[COL_ARTICULO] is None:
            continue

        art_prov = str(row[COL_ARTICULO]).strip()
        color = str(row[COL_COLOR] or "").strip()

        # Leer cantidades por talle
        talles = {}
        for col_offset in range(TALLE_FIN - TALLE_INICIO + 1):
            talle = TALLE_INICIO + col_offset
            col_idx = COL_TALLE_INICIO + col_offset
            if col_idx < len(row):
                qty = row[col_idx]
                if qty and isinstance(qty, (int, float)) and qty > 0:
                    talles[talle] = int(qty)

        # Total del Excel (para verificacion)
        total_excel = int(row[COL_TOTAL] or 0) if COL_TOTAL < len(row) and row[COL_TOTAL] else 0

        # Precios por rango de talle
        precio_23_34 = row[COL_PRECIO_23_34] if COL_PRECIO_23_34 < len(row) else None
        precio_35_40 = row[COL_PRECIO_35_40] if COL_PRECIO_35_40 < len(row) else None
        precio_41_45 = row[COL_PRECIO_41_45] if COL_PRECIO_41_45 < len(row) else None

        # Convertir precios a float, None si vacio
        def to_price(v):
            if v is None or v == "" or v == "-":
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        precio_23_34 = to_price(precio_23_34)
        precio_35_40 = to_price(precio_35_40)
        precio_41_45 = to_price(precio_41_45)

        total_calculado = sum(talles.values())

        print(f"  Excel fila {FILA_DATOS_INICIO + row_idx}: "
              f"Art {art_prov:>4s} {color:12s} "
              f"pares={total_calculado:3d} (excel={total_excel:3d}) "
              f"precios: {precio_23_34}/{precio_35_40}/{precio_41_45}")

        if total_excel > 0 and total_calculado != total_excel:
            print(f"    WARN: suma talles ({total_calculado}) != total Excel ({total_excel})")

        if not talles:
            print(f"    WARN: fila sin cantidades, saltando")
            continue

        pedido.append({
            "art_prov": art_prov,
            "color": color,
            "talles": talles,
            "precio_23_34": precio_23_34,
            "precio_35_40": precio_35_40,
            "precio_41_45": precio_41_45,
            "total_excel": total_excel,
        })

    return pedido


def get_precio_por_talle(talle, precio_23_34, precio_35_40, precio_41_45):
    """Determina el precio segun el rango de talle."""
    if 23 <= talle <= 34:
        if precio_23_34 is None:
            raise ValueError(f"Talle {talle} esta en rango 23-34 pero no hay precio definido")
        return precio_23_34
    elif 35 <= talle <= 40:
        if precio_35_40 is None:
            raise ValueError(f"Talle {talle} esta en rango 35-40 pero no hay precio definido")
        return precio_35_40
    elif 41 <= talle <= 45:
        if precio_41_45 is None:
            raise ValueError(f"Talle {talle} esta en rango 41-45 pero no hay precio definido")
        return precio_41_45
    elif talle == 22:
        # Talle 22 podria usar precio 23-34 o no existir
        if precio_23_34 is not None:
            return precio_23_34
        raise ValueError(f"Talle 22: sin precio (ni 23-34 definido)")
    elif talle == 46:
        if precio_41_45 is not None:
            return precio_41_45
        raise ValueError(f"Talle 46: sin precio (ni 41-45 definido)")
    else:
        raise ValueError(f"Talle {talle} fuera de rango conocido (22-46)")


def construir_detalle(cur, pedido):
    """
    Busca cada articulo/color/talle en la DB por proveedor y construye
    la lista de renglones a insertar.
    Retorna (detalle, errores) donde detalle es lista de
    (codigo_articulo, sinonimo, descripcion, cantidad, precio)
    NOTA: la tabla articulo NO tiene columnas 'talle' ni 'color'.
    El talle se extrae de los ultimos 2 digitos de codigo_sinonimo.
    El color se extrae de descripcion_1.
    """
    # Traer todos los articulos del proveedor 118
    # El talle va en los ultimos 2 digitos de codigo_sinonimo
    cur.execute("""
        SELECT a.codigo, a.descripcion_1, a.codigo_sinonimo,
               RIGHT(a.codigo_sinonimo, 2) as talle_sino
        FROM msgestion01art.dbo.articulo a
        WHERE a.proveedor = ?
          AND a.estado = 'V'
        ORDER BY a.codigo_sinonimo
    """, PROVEEDOR)
    rows = cur.fetchall()
    print(f"\nArticulos proveedor {PROVEEDOR} en DB: {len(rows)}")

    if not rows:
        print("ERROR CRITICO: No se encontraron articulos para este proveedor.")
        print("Verificar que proveedor=118 tenga articulos con estado='V' en msgestion01art.dbo.articulo")
        return [], ["No hay articulos del proveedor en la DB"]

    # Mostrar muestra
    print("\nMuestra (primeros 20):")
    for row in rows[:20]:
        cod = row.codigo
        desc = (row.descripcion_1 or "").strip()
        sino = (row.codigo_sinonimo or "").strip()
        talle = (row.talle_sino or "").strip()
        print(f"  {cod:>8}  sino={sino:16s}  talle={talle:5s}  {desc}")

    # Indexar por sinonimo completo
    by_desc_color_talle = {}
    by_sino = {}

    for row in rows:
        cod = row.codigo
        desc = (row.descripcion_1 or "").strip()
        sino = (row.codigo_sinonimo or "").strip()
        talle = (row.talle_sino or "").strip()

        if sino:
            by_sino[sino] = (cod, desc, sino, talle, "")

        desc_upper = desc.upper()
        key = (desc_upper, "", talle)
        by_desc_color_talle[key] = (cod, desc, sino)

    detalle = []
    errores = []

    for item in pedido:
        art_prov = item["art_prov"]
        color = item["color"].upper()
        p1 = item["precio_23_34"]
        p2 = item["precio_35_40"]
        p3 = item["precio_41_45"]

        print(f"\n--- Art {art_prov} Color {color} ---")

        # Buscar articulos que matcheen este art/color en la DB
        # Estrategia: buscar por descripcion que contenga el numero de art Y el color
        matched = {}  # talle_str -> (codigo, descripcion, sinonimo)

        # Normalizacion de color para match
        color_variants = [color]
        if color == "AZUL":
            color_variants.extend(["AZ", "AZUL"])
        elif color == "RED NEGRO":
            color_variants.extend(["ROJO", "RED", "RD NGO", "RD NEGRO", "RED NGR"])
        elif color == "ROSA":
            color_variants.extend(["RS", "ROSA"])
        elif color == "NEGRO":
            color_variants.extend(["NGO", "NGR", "NEGRO"])

        # Buscar en DB directamente por descripcion_1 (sin columna color ni talle)
        # Talle se extrae de los ultimos 2 digitos de codigo_sinonimo
        for color_var in color_variants:
            if matched:
                break
            cur.execute("""
                SELECT a.codigo, a.descripcion_1, a.codigo_sinonimo,
                       RIGHT(a.codigo_sinonimo, 2) as talle_sino
                FROM msgestion01art.dbo.articulo a
                WHERE a.proveedor = ?
                  AND a.estado = 'V'
                  AND a.descripcion_1 LIKE ?
                  AND a.descripcion_1 LIKE ?
                ORDER BY a.codigo_sinonimo
            """, PROVEEDOR,
                f"%{art_prov}%",
                f"%{color_var}%")
            found = cur.fetchall()
            if found:
                for r in found:
                    t = (r.talle_sino or "").strip()
                    if t:
                        matched[t] = (r.codigo, (r.descripcion_1 or "").strip(), (r.codigo_sinonimo or "").strip())

        # Si no encontro con color, intentar solo por art (para revisar que existe)
        if not matched:
            cur.execute("""
                SELECT a.codigo, a.descripcion_1, a.codigo_sinonimo,
                       RIGHT(a.codigo_sinonimo, 2) as talle_sino
                FROM msgestion01art.dbo.articulo a
                WHERE a.proveedor = ?
                  AND a.estado = 'V'
                  AND a.descripcion_1 LIKE ?
                ORDER BY a.codigo_sinonimo
            """, PROVEEDOR, f"%{art_prov}%")
            found_any = cur.fetchall()
            if found_any:
                print(f"  No matcheo color '{color}', pero hay {len(found_any)} arts con art_prov '{art_prov}':")
                for r in found_any[:10]:
                    print(f"    {r.codigo:>8} {(r.descripcion_1 or '').strip():40s} "
                          f"talle={(r.talle_sino or '').strip()}")
                errores.append(f"Art {art_prov} Color {color}: color no matchea en DB. Revisar manualmente.")
            else:
                errores.append(f"Art {art_prov}: NO existe en DB con proveedor {PROVEEDOR}")
                print(f"  *** NO se encontro Art {art_prov} en DB")
            continue

        print(f"  Encontrados: {len(matched)} talles en DB")

        # Generar renglones
        for talle, cantidad in sorted(item["talles"].items()):
            if cantidad <= 0:
                continue

            try:
                precio = get_precio_por_talle(talle, p1, p2, p3)
            except ValueError as e:
                errores.append(str(e))
                print(f"  T{talle} x{cantidad} -> ERROR PRECIO: {e}")
                continue

            talle_str = str(talle)
            if talle_str in matched:
                cod_art, desc_art, sino_art = matched[talle_str]
                detalle.append((cod_art, sino_art, desc_art, cantidad, precio))
                print(f"  T{talle:2d} x{cantidad:2d} @ ${precio:>10,.0f}  -> cod={cod_art} {desc_art[:40]}")
            else:
                errores.append(f"Art {art_prov} Color {color} Talle {talle}: no existe en DB")
                print(f"  T{talle:2d} x{cantidad:2d} @ ${precio:>10,.0f}  -> *** TALLE NO ENCONTRADO ***")

    if errores:
        print(f"\n{'='*60}")
        print(f"ERRORES DE MAPEO ({len(errores)}):")
        for e in errores:
            print(f"  - {e}")
        print(f"{'='*60}")

    return detalle, errores


def verificar_totales(detalle):
    """Verifica pares y monto total contra lo esperado."""
    total_pares = sum(d[3] for d in detalle)
    total_monto = sum(d[3] * d[4] for d in detalle)
    print(f"\nVerificacion pre-insercion:")
    print(f"  Renglones:      {len(detalle)}")
    print(f"  Pares totales:  {total_pares}  (esperado: {TOTAL_ESPERADO_PARES})")
    print(f"  Monto total:    ${total_monto:,.0f}  (esperado: ~${TOTAL_ESPERADO_MONTO:,.0f})")

    if total_pares != TOTAL_ESPERADO_PARES:
        print(f"  *** ATENCION: diferencia de {total_pares - TOTAL_ESPERADO_PARES} pares")

    diff_monto = abs(total_monto - TOTAL_ESPERADO_MONTO)
    if diff_monto > 1000:
        pct = diff_monto / TOTAL_ESPERADO_MONTO * 100
        print(f"  *** ATENCION: diferencia de ${diff_monto:,.0f} en monto ({pct:.1f}%)")

    return total_pares, total_monto


def main():
    global DRY_RUN

    if len(sys.argv) > 1:
        if sys.argv[1] == "--ejecutar":
            DRY_RUN = False
        elif sys.argv[1] == "--dry-run":
            DRY_RUN = True

    print("=" * 60)
    print(f"PEDIDO EL FARAON - Invierno 2026")
    print(f"Proveedor: {PROVEEDOR} - {DENOMINACION}")
    print(f"Empresa: CALZALINDO (msgestion01)")
    print(f"Modo: {'DRY RUN' if DRY_RUN else 'EJECUCION REAL'}")
    print("=" * 60)

    # 1. Leer Excel
    excel_path = encontrar_excel()
    print(f"\nLeyendo Excel: {excel_path}")
    pedido = leer_excel(excel_path)
    print(f"\nFilas de producto leidas: {len(pedido)}")

    grand_total = sum(sum(item["talles"].values()) for item in pedido)
    print(f"Total pares del Excel: {grand_total} (esperado: {TOTAL_ESPERADO_PARES})")

    if not pedido:
        print("ERROR: No se leyeron datos del Excel.")
        sys.exit(1)

    # 2. Conectar a SQL y buscar articulos
    print(f"\nConectando a {CONN_STR.split('SERVER=')[1].split(';')[0]}...")
    conn = pyodbc.connect(CONN_STR, timeout=15)
    cur = conn.cursor()

    # 3. Construir detalle mapeando contra DB
    detalle, errores = construir_detalle(cur, pedido)

    if not detalle:
        print("\nERROR: No se pudo construir ningun renglon. Revisar mapeo de articulos.")
        conn.close()
        sys.exit(1)

    # 4. Verificar totales
    total_pares, total_monto = verificar_totales(detalle)

    OBS = f"Pedido El Faraon Invierno 2026. {total_pares} pares. ${total_monto:,.0f}"

    if errores:
        print(f"\nHay {len(errores)} errores de mapeo.")

    # 5. Dry run o ejecucion
    if DRY_RUN:
        print(f"\n{'='*60}")
        print("[DRY RUN] Detalle completo:")
        print(f"{'='*60}")
        for i, (cod, sino, desc, cant, precio) in enumerate(detalle, 1):
            rango = "23-34" if 23 <= int((sino or "00")[-2:] or 0) <= 34 else "35-40" if 35 <= int((sino or "00")[-2:] or 0) <= 40 else "41-45"
            print(f"  {i:3d}. [{cod:>8}] {desc[:40]:40s} x{cant:2d} @ ${precio:>10,.0f}  sino={sino}")
        print(f"\n[DRY RUN] Total: {total_pares} pares, ${total_monto:,.0f}")
        print("[DRY RUN] Ningun dato fue escrito en la base.")
        print(f"\nPara ejecutar: python {sys.argv[0]} --ejecutar")
        conn.close()
        return

    # ── EJECUCION REAL ─────────────────────────────────────
    if errores:
        resp = input(f"\nHay {len(errores)} errores. Continuar con INSERT parcial? (S/N): ")
        if resp.strip().upper() != 'S':
            print("Cancelado.")
            conn.close()
            return

    resp = input(f"\nConfirmar INSERT de {total_pares} pares, ${total_monto:,.0f} en msgestion01? (S/N): ")
    if resp.strip().upper() != 'S':
        print("Cancelado.")
        conn.close()
        return

    # Calcular proximo numero y orden
    cur.execute("SELECT ISNULL(MAX(numero), 0) + 1 FROM pedico2 WHERE codigo = 8")
    numero = cur.fetchone()[0]
    cur.execute("SELECT ISNULL(MAX(orden), 0) + 1 FROM pedico2 WHERE codigo = 8")
    orden = cur.fetchone()[0]
    if orden > 99:
        orden = 1

    print(f"\nInsertando pedido numero={numero}, orden={orden}...")

    # Verificar que el numero no exista
    cur.execute("""
        SELECT COUNT(*) FROM pedico2
        WHERE codigo=8 AND letra='X' AND sucursal=1 AND numero=?
    """, numero)
    if cur.fetchone()[0] > 0:
        print(f"ERROR: Pedido {numero} ya existe!")
        conn.close()
        return

    # INSERT cabecera pedico2
    cur.execute("""
        INSERT INTO pedico2 (
            codigo, letra, sucursal, numero, orden,
            deposito, cuenta, denominacion,
            fecha_comprobante, fecha_proceso,
            descuento_general, monto_descuento,
            bonificacion_general, monto_bonificacion,
            financiacion_general, monto_financiacion,
            iva1, monto_iva1, iva2, monto_iva2,
            monto_impuesto, monto_exento,
            importe_neto,
            estado, condicion_iva,
            copias, usuario,
            campo, sistema_cc, moneda, sector,
            forma_pago, tipo_vcto_pago, tipo_operacion, tipo_ajuste,
            medio_pago, cuenta_cc,
            plan_canje, cuenta_y_orden, pack, reintegro, cambio, transferencia,
            concurso, entregador,
            observaciones
        ) VALUES (
            8, 'X', 1, ?, ?,
            0, ?, ?,
            CONVERT(datetime, ?, 112), GETDATE(),
            0, 0,
            0, 0,
            0, 0,
            21, 0, 10.5, 0,
            0, 0,
            0,
            'V', 'I',
            1, 'COWORK',
            0, 2, 0, 0,
            0, 0, 0, 0,
            ' ', ?,
            'N', 'N', 'N', 'N', 'N', 'N',
            'N', 0,
            ?
        )
    """, numero, orden,
        PROVEEDOR, DENOMINACION,
        FECHA,
        PROVEEDOR,
        OBS)

    # INSERT renglones pedico1
    for i, (cod_art, sinonimo, descripcion, cantidad, precio) in enumerate(detalle, 1):
        cur.execute("""
            INSERT INTO pedico1 (
                codigo, letra, sucursal, numero, orden, renglon,
                articulo, descripcion, precio, cantidad,
                descuento_reng1, descuento_reng2,
                estado, fecha,
                cuenta,
                codigo_sinonimo
            ) VALUES (
                8, 'X', 1, ?, ?, ?,
                ?, ?, ?, ?,
                0, 0,
                'V', CONVERT(datetime, ?, 112),
                ?,
                ?
            )
        """, numero, orden, i,
            cod_art, descripcion, precio, cantidad,
            FECHA,
            PROVEEDOR,
            sinonimo)

    conn.commit()
    print(f"\nPEDIDO INSERTADO EXITOSAMENTE:")
    print(f"  Numero:     {numero}")
    print(f"  Orden:      {orden}")
    print(f"  Proveedor:  {PROVEEDOR} - {DENOMINACION}")
    print(f"  Empresa:    CALZALINDO (msgestion01)")
    print(f"  Pares:      {total_pares}")
    print(f"  Monto:      ${total_monto:,.0f}")
    print(f"  Renglones:  {len(detalle)}")

    # Verificacion post-insert
    cur.execute(
        "SELECT COUNT(*), SUM(cantidad) FROM pedico1 WHERE numero=? AND orden=?",
        numero, orden
    )
    vrow = cur.fetchone()
    print(f"\nVerificacion DB: {vrow[0]} renglones, {vrow[1]} pares en pedico1")

    print(f"\nVerificar en SSMS:")
    print(f"  SELECT * FROM msgestion01.dbo.pedico2 WHERE numero={numero} AND codigo=8")
    print(f"  SELECT * FROM msgestion01.dbo.pedico1 WHERE numero={numero} AND codigo=8")
    conn.close()


if __name__ == '__main__':
    main()
