#!/usr/bin/env python3
"""
Insertar pedido Escorpio Botas de Lluvia — Invierno 2026
Proveedor: 896 — CALZADOS ARGENTINOS SA
Empresa: CALZALINDO → msgestion01
Fuente Excel: PEDIDO ESCORPIO.xlsx

Talles dobles: 23/24, 25/26, 27/28, 29/30, 31/32, 33/34
60 pares total | Precio: $8,588 | Monto: $515,280

USO:
  python insertar_escorpio_lluvia.py               # DRY RUN (default)
  python insertar_escorpio_lluvia.py --ejecutar     # INSERT real
"""

import sys
import os
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyodbc
from config import get_conn_string

# ─── PARÁMETROS DEL PEDIDO ────────────────────────────────────────────────────
EMPRESA        = "CALZALINDO"   # → msgestion01
BASE           = "msgestion01"
PROVEEDOR      = 896            # CALZADOS ARGENTINOS SA / Escorpio
DESCUENTO_PROV = 0
DESCUENTO_BON  = 0

EXCEL_PATH = (
    "/Volumes/compartido/COMPRAS/Pedidos Invierno/"
    "Pedido Calzados Argentinos (escorpio lluvia) 18-02/"
    "PEDIDO ESCORPIO.xlsx"
)

# Mapping de talles dobles del Excel → talle ERP (se usa el talle par)
TALLES_DOBLES = ["23/24", "25/26", "27/28", "29/30", "31/32", "33/34"]

# Columnas Excel (0-indexed): D=23/24, E=25/26, F=27/28, G=29/30, H=31/32, I=33/34
# Col A=ARTICULO, Col B=COLOR, Col J=PRECIO
TALLE_COLS_START = 3   # column D (0-indexed)
TALLE_COLS_END   = 9   # column I inclusive (0-indexed)


def leer_excel(path):
    """Lee el Excel y retorna lista de dicts con los datos del pedido."""
    try:
        import openpyxl
    except ImportError:
        print("ERROR: openpyxl no instalado. Ejecutar: pip install openpyxl")
        sys.exit(1)

    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active

    filas = []
    for row in ws.iter_rows(min_row=2, values_only=True):  # skip header
        art_code = row[0]
        if art_code is None:
            continue

        color = str(row[1]).strip() if row[1] else ""
        precio = row[9]  # Col J (0-indexed)
        if precio is None or precio == 0:
            continue

        # Leer cantidades por talle (cols D-I = indices 3-8)
        cantidades = []
        for col_idx in range(TALLE_COLS_START, TALLE_COLS_END):
            val = row[col_idx]
            # Handle "x", "X", None, empty as 0
            if val is None or str(val).strip().lower() == 'x' or str(val).strip() == '':
                cantidades.append(0)
            else:
                try:
                    cantidades.append(int(float(str(val))))
                except (ValueError, TypeError):
                    cantidades.append(0)

        filas.append({
            "articulo_code": str(art_code).strip(),
            "color": color,
            "precio": float(precio),
            "cantidades": cantidades,  # one per talle doble
        })

    wb.close()
    return filas


def buscar_articulos_erp(cursor, art_code, color):
    """
    Busca artículos en msgestion01art.dbo.articulo por sinonimo que contenga
    el código del artículo y el color.
    Returns dict: talle_erp -> codigo_articulo
    """
    # Buscar por sinonimo que contenga el code del proveedor (ej: "50")
    # y que la denominacion contenga el color
    cursor.execute("""
        SELECT a.codigo, a.codigo_sinonimo, a.descripcion_1, a.talle, a.color
        FROM msgestion01art.dbo.articulo a
        WHERE a.proveedor = ?
          AND a.descripcion_1 LIKE '%LLUVIA%'
        ORDER BY a.talle
    """, (PROVEEDOR,))

    resultados = {}
    for row in cursor.fetchall():
        cod, sinon, denom, talle, col_erp = row
        # Map talle ERP to our talle doble
        if talle is not None:
            talle_str = str(talle).strip()
            resultados[talle_str] = {
                "codigo": cod,
                "sinonimo": sinon,       # from codigo_sinonimo
                "denominacion": denom,    # from descripcion_1
                "talle": talle_str,
                "color": col_erp,
            }

    return resultados


def main():
    dry_run = "--ejecutar" not in sys.argv

    if dry_run:
        print("\n*** MODO DRY RUN — para ejecutar: python insertar_escorpio_lluvia.py --ejecutar ***\n")

    # ── 1. Leer Excel ─────────────────────────────────────────────────────────
    if os.path.exists(EXCEL_PATH):
        print(f"Leyendo Excel: {EXCEL_PATH}")
        filas_excel = leer_excel(EXCEL_PATH)
        print(f"  Filas de datos: {len(filas_excel)}")
    else:
        print(f"WARN: Excel no accesible en {EXCEL_PATH}")
        print("      Usando datos hardcoded del pedido.")
        filas_excel = None

    # ── 2. Conectar BD ────────────────────────────────────────────────────────
    conn_str = get_conn_string(BASE)
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # ── 3. Buscar artículos ERP ───────────────────────────────────────────────
    print("\nBuscando artículos Escorpio (proveedor 896, LLUVIA) en ERP...")
    arts_erp = buscar_articulos_erp(cursor, "50", "AMARILLO")

    if arts_erp:
        print(f"  Encontrados {len(arts_erp)} artículos:")
        for t, info in sorted(arts_erp.items()):
            print(f"    talle={t} → cod={info['codigo']} | {info['denominacion']}")
    else:
        print("  WARN: No se encontraron artículos por proveedor. Usando códigos conocidos.")

    # ── 4. Armar detalle ──────────────────────────────────────────────────────
    # Mapping conocido de talle par ERP → codigo artículo ERP
    # (del script anterior insertar_escorpio_inv2026.py, verificado en BD)
    CODIGOS_CONOCIDOS = {
        "24": 359214,   # 23/24
        "26": 264156,   # 25/26
        "28": 264157,   # 27/28
        "30": 264158,   # 29/30
        "32": 264159,   # 31/32
        "34": 264160,   # 33/34
    }

    if filas_excel:
        # Usar datos del Excel
        fila = filas_excel[0]  # solo 1 fila de datos
        precio = fila["precio"]
        cantidades = fila["cantidades"]
        color = fila["color"]
    else:
        # Fallback hardcoded (del Excel: 12,12,12,12,x=0,12)
        precio = 8588.0
        cantidades = [12, 12, 12, 12, 0, 12]
        color = "Amarillo"

    DETALLE = []
    for i, talle_doble in enumerate(TALLES_DOBLES):
        qty = cantidades[i]
        if qty <= 0:
            continue

        # Talle par para lookup ERP
        talle_par = talle_doble.split("/")[1]

        # Buscar código ERP: primero en resultado BD, luego en conocidos
        cod_erp = None
        if arts_erp and talle_par in arts_erp:
            cod_erp = arts_erp[talle_par]["codigo"]
        elif talle_par in CODIGOS_CONOCIDOS:
            cod_erp = CODIGOS_CONOCIDOS[talle_par]

        if cod_erp is None:
            print(f"  ERROR: No se encontró artículo ERP para talle {talle_doble} (par={talle_par})")
            continue

        desc = f"050 {color.upper()} BOTA LLUVIA T{talle_doble}"
        DETALLE.append((cod_erp, qty, precio, desc, talle_doble))

    if not DETALLE:
        print("ERROR: No hay líneas de detalle para insertar.")
        conn.close()
        return

    # ── 5. Calcular totales ───────────────────────────────────────────────────
    total_pares = sum(d[1] for d in DETALLE)
    monto_total = sum(d[1] * d[2] for d in DETALLE)

    # ── 6. Obtener próximo número ─────────────────────────────────────────────
    cursor.execute(
        "SELECT MAX(CAST(numero AS INT)) FROM MSGESTION01.dbo.pedico2 "
        "WHERE codigo=8 AND letra='X' AND sucursal=1"
    )
    row = cursor.fetchone()
    ultimo_num = row[0] if row[0] else 0
    nuevo_numero = ultimo_num + 1

    cursor.execute(
        "SELECT MAX(orden) FROM MSGESTION01.dbo.pedico2 "
        "WHERE codigo=8 AND letra='X' AND sucursal=1"
    )
    row = cursor.fetchone()
    ultimo_orden = row[0] if row[0] else 0
    nuevo_orden = (ultimo_orden + 1) if (ultimo_orden + 1) <= 99 else 1

    hoy = datetime.date.today().strftime("%Y%m%d")

    # Buscar nombre proveedor
    cursor.execute("SELECT denominacion FROM MSGESTION01.dbo.proveedores WHERE numero=?", (PROVEEDOR,))
    row = cursor.fetchone()
    nombre_prov = row[0].strip() if row and row[0] else f"PROVEEDOR {PROVEEDOR}"

    observaciones = (
        f"Pedido Escorpio Lluvia Invierno 2026. "
        f"{total_pares} pares. ${monto_total:,.0f}. {nombre_prov}"
    )

    # ── 7. Resumen ────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"PEDIDO A INSERTAR:")
    print(f"  Numero:       {nuevo_numero}")
    print(f"  Orden:        {nuevo_orden}")
    print(f"  Proveedor:    {PROVEEDOR} — {nombre_prov}")
    print(f"  Empresa:      {EMPRESA} → MSGESTION01")
    print(f"  Fecha:        {hoy}")
    print(f"  Pares:        {total_pares}")
    print(f"  Monto:        ${monto_total:,.2f}")
    print(f"  Lineas:       {len(DETALLE)}")
    print(f"  Observaciones: {observaciones}")
    print(f"{'='*60}")
    print()

    for i, (art_cod, qty, precio, desc_art, talle) in enumerate(DETALLE, 1):
        print(f"  [{i}] art={art_cod:>6d}  talle={talle:5s}  qty={qty:2d}  "
              f"precio=${precio:,.2f}  subtotal=${qty*precio:,.2f}  — {desc_art}")

    print(f"\n  TOTAL: {total_pares} pares | ${monto_total:,.2f}")

    if dry_run:
        print(f"\n[DRY RUN] No se ejecuto nada.")
        print("Para insertar: python insertar_escorpio_lluvia.py --ejecutar")
        conn.close()
        return

    # ── 8. Confirmación ───────────────────────────────────────────────────────
    resp = input("\nConfirmar INSERT? (S/N): ")
    if resp.strip().upper() != 'S':
        print("Cancelado.")
        conn.close()
        return

    # ── 9. INSERT pedico2 (cabecera) ──────────────────────────────────────────
    sql_cab = """
    INSERT INTO MSGESTION01.dbo.pedico2
        (codigo, letra, sucursal, numero, orden, cuenta, denominacion,
         fecha_comprobante, estado, usuario, importe_neto, observaciones)
    VALUES
        (8, 'X', 1, ?, ?, ?, ?, ?, 'V', 'COWORK', ?, ?)
    """
    cursor.execute(sql_cab, (
        nuevo_numero, nuevo_orden,
        PROVEEDOR, nombre_prov,
        hoy,
        monto_total,
        observaciones,
    ))
    print(f"pedico2 insertado: numero={nuevo_numero}, orden={nuevo_orden}")

    # ── 10. INSERT pedico1 (detalle) ──────────────────────────────────────────
    sql_det = """
    INSERT INTO MSGESTION01.dbo.pedico1
        (codigo, letra, sucursal, numero, orden, articulo, cantidad, precio,
         descuento, descuento_1, usuario, estado)
    VALUES
        (8, 'X', 1, ?, ?, ?, ?, ?, ?, ?, 'COWORK', 'V')
    """
    for i, (art_cod, qty, precio, desc_art, talle) in enumerate(DETALLE, 1):
        cursor.execute(sql_det, (
            nuevo_numero, i,
            art_cod, qty, precio,
            DESCUENTO_PROV, DESCUENTO_BON,
        ))
        print(f"  [{i}] art={art_cod}, talle={talle}, qty={qty} — {desc_art}")

    conn.commit()
    print(f"\nPedido Escorpio Lluvia insertado exitosamente.")
    print(f"pedico2 numero {nuevo_numero} | {len(DETALLE)} lineas | "
          f"{total_pares} pares | ${monto_total:,.2f}")
    conn.close()


if __name__ == '__main__':
    main()
