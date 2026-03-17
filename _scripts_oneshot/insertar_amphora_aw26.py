#!/usr/bin/env python3
# insertar_amphora_aw26.py
# Alta artículos + Pedido + Remito — AMPHORA AW2026
# Factura A 00015-00009639 del 16/03/2026
# Remito proveedor: 5000078194
# 21 artículos, 36 unidades, $1,537,000 neto
# Empresa: H4 → MSGESTION03 (factura a HACHE CUATRO SRL)
#
# EJECUTAR EN EL 111:
#   py -3 insertar_amphora_aw26.py --dry-run     <- solo muestra
#   py -3 insertar_amphora_aw26.py --ejecutar    <- escribe en produccion

import sys
import pyodbc
import socket
from datetime import date, datetime

# -- AUTO-DETECT SERVER vs MAC -----------------------------------------
_hostname = socket.gethostname().upper()
if _hostname in ("DELL-SVR", "DELLSVR"):
    SERVIDOR = "localhost"
    DRIVER = "ODBC Driver 17 for SQL Server"
    EXTRAS = ""
else:
    SERVIDOR = "192.168.2.111"
    DRIVER = "ODBC Driver 18 for SQL Server"
    EXTRAS = "TrustServerCertificate=yes;Encrypt=no;"

def get_conn(base):
    return (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVIDOR};"
        f"DATABASE={base};"
        f"UID=am;PWD=dl;"
        f"{EXTRAS}"
    )

# -- CONSTANTES --------------------------------------------------------
PROVEEDOR = 44
DENOMINACION = "AMPHORA"
MARCA = 44
GRUPO = "5"
RUBRO = 1
ESTADO = "V"
UTILIDAD_1 = 100  # 100% markup
UTILIDAD_2 = 124
UTILIDAD_3 = 60
UTILIDAD_4 = 45
SUBRUBRO = 18     # carteras/accesorios
LINEA = 4         # todo el año

FACTURA = "A 00015-00009639"
REMITO_PV = 5000  # sucursal del remito (punto de venta)
REMITO_NUM = 78194  # numero del remito
FECHA_FACTURA = date(2026, 3, 16)
FECHA_HOY = date(2026, 3, 16)

# Empresa destino: H4 (HACHE CUATRO SRL)
BASES_PEDIDO = ["MSGESTION01"]  # pedico2/pedico1 son VIEWs en 03 → tabla real en 01
BASE_REMITO = "MSGESTION03"  # remito va a H4

DEPOSITO = 11

# -- TALLES CARTERA (tamaño) ------------------------------------------
# 01=XS (riñonera/portacelular), 02=S (bandolera chica),
# 03=M (mochila), 04=L (cartera dos asas), 05=XL (porta notebook)
TALLE_MAP = {
    "RIÑONERA": "01",
    "BANDOLERA": "02",
    "MOCHILA": "03",
    "CARTERA": "04",
    "PORTA NOTEBOOK": "05",
}

def detectar_talle(detalle):
    """Detecta talle (tamaño) del producto Amphora por tipo."""
    d = detalle.upper()
    if "PORTA NOTEBOOK" in d:
        return "05"
    if "RIÑONERA" in d or "PORTACELULAR" in d:
        return "01"
    if "MOCHILA" in d:
        return "03"
    if "CARTERA" in d:
        return "04"
    if "BANDOLERA" in d:
        return "02"
    return ""

# -- ITEMS DE FACTURA --------------------------------------------------
# (barcode, descripcion_factura, cantidad, precio_unitario_neto)
ITEMS = [
    ("040422745501",    "KIRKLI MOCHILA NEGRO",                      2, 44500.00),
    ("040423407501",    "CAMELEON RIÑONERA NEGRO",                   2, 39500.00),
    ("040433905201",    "CHIARA BANDOLERA NEGRO",                    2, 39500.00),
    ("040424027701",    "BENIN CARTERA PORTA NOTEBOOK NEGRO",        2, 54500.00),
    ("040424026901",    "INGLATERRA BANDOLERA NEGRO",                2, 39500.00),
    ("04036421820001",  "JENIFER CARTERA DOS ASAS TRES DIV NEGRO",   2, 49500.00),
    ("04036421820010",  "JENIFER CARTERA DOS ASAS TRES DIV CAFE",    1, 49500.00),
    ("04036421460008",  "ANGELA CARTERA DOS ASAS TAUPE",             1, 44500.00),
    ("04036421760001",  "CHARLOTE MOCHILA NEGRO",                    2, 39500.00),
    ("04036421760013",  "CHARLOTE MOCHILA CAFE OSCURO",              1, 39500.00),
    ("04036421780001",  "CHARLOTE BANDOLERA NEGRO",                  2, 37000.00),
    ("04036421780013",  "CHARLOTE BANDOLERA CAFE OSCURO",            1, 37000.00),
    ("04006421040001",  "JULIA CARTERA DOS ASAS NEGRO",              2, 39500.00),
    ("04042423200001",  "AMARANTA MOCHILA NEGRO",                    2, 42000.00),
    ("04043423450001",  "ELIZA CARTERA DOS ASAS NEGRO",              2, 44500.00),
    ("04043423500001",  "MACARENA MOCHILA NEGRO",                    1, 42000.00),
    ("04043423530001",  "MAGDALENA CARTERA DOS ASAS NEGRO",          2, 44500.00),
    ("04043423550001",  "MAGDALENA BANDOLERA NEGRO",                 2, 39500.00),
    ("04043423550057",  "MAGDALENA BANDOLERA BLANCO ESPECIAL",       1, 39500.00),
    ("04043423900001",  "MARGARET CARTERA DOS ASAS NEGRO",           2, 44500.00),
    ("04043423900010",  "MARGARET CARTERA DOS ASAS CAFE",            2, 44500.00),
]

# =====================================================================
# SQL TEMPLATES
# =====================================================================

SQL_ARTICULO = """
    INSERT INTO msgestion01art.dbo.articulo (
        codigo, descripcion_1, descripcion_3, descripcion_4, descripcion_5,
        codigo_barra, codigo_sinonimo, tipo_codigo_barra,
        marca, rubro, subrubro, grupo, proveedor, linea,
        codigo_objeto_costo,
        precio_fabrica, precio_costo, precio_sugerido,
        precio_1, precio_2, precio_3, precio_4,
        utilidad_1, utilidad_2, utilidad_3, utilidad_4,
        alicuota_iva1, alicuota_iva2, tipo_iva,
        formula, calificacion, estado,
        descuento, descuento_1, descuento_2, descuento_3, descuento_4,
        moneda, factura_por_total, numero_maximo, stock,
        cuenta_compras, cuenta_ventas, cuenta_com_anti,
        usuario, abm, fecha_alta, fecha_hora
    ) VALUES (
        ?, ?, ?, ?, ?,
        ?, ?, 'C',
        ?, ?, 18, ?, ?, 4,
        ?,
        ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?,
        21, 10.5, 'G',
        1, 'G', 'V',
        0, 0, 0, 0, 0,
        0, 'N', 'S', 'S',
        '1010601', '4010100', '1010601',
        'COWORK', 'A', GETDATE(), GETDATE()
    )
"""

SQL_PEDIDO_CAB = """
    INSERT INTO {base}.dbo.pedico2 (
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
        8, 'X', 1,
        ?, 1, 0,
        ?, ?,
        ?, ?,
        ?,
        0, 0, 0, 0, 0, 0,
        21, 0, 10.5, 0, 0,
        0, 0,
        'V', 1, 'I', '30708994002', 1,
        'N', 'N', 'N', 'N', 'N',
        0, 'COWORK', 0, 2, 0, 0,
        0, 'N', 0, 0, 0,
        ' ', ?, 'N'
    )
"""

SQL_PEDIDO_DET = """
    INSERT INTO {base}.dbo.pedico1 (
        codigo, letra, sucursal,
        numero, orden, renglon,
        articulo, descripcion, codigo_sinonimo,
        cantidad, precio,
        cuenta, fecha, fecha_entrega,
        estado
    ) VALUES (8, 'X', 1, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'V')
"""

SQL_REMITO_CAB = """
    INSERT INTO {base}.dbo.compras2 (
        codigo, letra, sucursal, numero, orden,
        deposito, cuenta, cuenta_cc, denominacion,
        fecha_comprobante, fecha_proceso, fecha_contable,
        concepto_gravado, concepto_no_gravado, monto_general,
        estado_stock, estado, zona, condicion_iva, numero_cuit,
        contabiliza, consignacion, venta_anticipada,
        moneda, sistema_cc, sistema_cuenta,
        fecha_vencimiento, fecha_hora,
        usuario, usuario_creacion, host_creacion
    ) VALUES (
        7, 'R', ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?,
        ?, 0, ?,
        'S', 'V', 1, 'I', '30708994002',
        'N', '1 ', 'N',
        0, 2, 2,
        ?, GETDATE(),
        'COWORK', 'COWORK', 'SCRIPT-AMPHORA'
    )
"""

SQL_REMITO_DET = """
    INSERT INTO {base}.dbo.compras1 (
        codigo, letra, sucursal, numero, orden, renglon,
        articulo, descripcion, precio, cantidad, deposito,
        estado_stock, estado, operacion, fecha, cuenta,
        calificacion, condicion_iva, consignacion,
        cantidad_entregada, monto_entregado,
        cantidad_devuelta, cantidad_pagada,
        monto_devuelto, monto_pagado,
        unidades, cantidad_original, serie,
        venta_anticipada, financiacion_general,
        fecha_hora, usuario_creacion, host_creacion
    ) VALUES (
        7, 'R', ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        'S', 'V', '+', ?, ?,
        'G', 'I', '1 ',
        ?, ?,
        0, 0,
        0, 0,
        ?, ?, '',
        'N', 0,
        GETDATE(), 'COWORK', 'SCRIPT-AMPHORA'
    )
"""

SQL_REMITO_EXT = """
    INSERT INTO {base}.dbo.comprasr (
        codigo, letra, sucursal, numero, orden,
        cupones, bultos, fecha_vencimiento,
        precio_financiado, sin_valor_declarado, direccion,
        sector, kg, cod_postal_trans, codigo_redespacho,
        cod_postal_redespacho, campo, valor_declarado,
        ENTREGADOR2, ENTREGADOR3, origen, destino,
        cp_transporte, km_flete, tarifa_flete, importe_flete,
        recorrido_codpos, dest_codpos, rem_codpos
    ) VALUES (
        7, 'R', ?, ?, ?,
        0, 0, ?,
        'S', 'N', '',
        0, 0, 0, 0,
        0, 0, 0,
        0, 0, 0, 0,
        0, 0, 0, 0,
        0, 0, 0
    )
"""

SQL_MOVI_STOCK = """
    INSERT INTO {base}.dbo.movi_stock (
        deposito, articulo, fecha,
        codigo_comprobante, letra_comprobante,
        sucursal_comprobante, numero_comprobante, orden,
        operacion, cantidad, precio, cuenta,
        vta_anticipada, sistema, serie,
        unidades, fecha_contable, fecha_proceso, usuario
    ) VALUES (
        ?, ?, GETDATE(),
        7, 'R',
        ?, ?, ?,
        '+', ?, ?, ?,
        'N', 7, '',
        ?, ?, GETDATE(), 'WB'
    )
"""

SQL_PEDICO1_ENTREGAS = """
    INSERT INTO {base}.dbo.pedico1_entregas (
        codigo, letra, sucursal, numero, orden,
        renglon, articulo, cantidad, deposito, fecha_entrega
    ) VALUES (8, 'X', 1, ?, 1, ?, ?, ?, ?, ?)
"""

SQL_PEDICO1_UPDATE = """
    UPDATE {base}.dbo.pedico1
    SET cantidad_entregada = ISNULL(cantidad_entregada, 0) + ?,
        monto_entregado = ISNULL(monto_entregado, 0) + ?
    WHERE codigo = 8 AND letra = 'X'
      AND sucursal = 1 AND numero = ? AND orden = 1 AND renglon = ?
"""


def extraer_nombre_producto(desc):
    """Extrae el nombre del producto (primera palabra) para codigo_objeto_costo."""
    return desc.split()[0].upper()[:30]


def extraer_color(desc):
    """Extrae el color de la descripción (última palabra/s)."""
    # Formato: "NOMBRE TIPO COLOR" ej: "KIRKLI MOCHILA NEGRO"
    _COLORES = [
        "NEGRO", "CAFE", "CAFE OSCURO", "TAUPE", "BLANCO ESPECIAL",
        "BLANCO", "MARRON", "GRIS", "NATURAL", "BEIGE",
    ]
    d = desc.upper()
    for c in _COLORES:
        if d.endswith(c):
            return c
    # Fallback: última palabra
    parts = desc.split()
    return parts[-1].upper() if parts else ""


def descripcion_3(desc):
    """Descripción corta para etiqueta (máx 26 chars)."""
    return desc[:26]


def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]
    dry_run = modo != "--ejecutar"

    # Preparar items con talle y codigo_objeto_costo
    items_prep = []
    for barcode, desc, cant, precio in ITEMS:
        talle = detectar_talle(desc)
        cod_obj = extraer_nombre_producto(desc)
        items_prep.append((barcode, desc, cant, precio, talle, cod_obj))

    total_uds = sum(i[2] for i in items_prep)
    total_neto = sum(i[2] * i[3] for i in items_prep)

    print(f"\n{'='*70}")
    print(f"AMPHORA AW2026 — ALTA + PEDIDO + REMITO")
    print(f"Factura {FACTURA} del {FECHA_FACTURA}")
    print(f"Remito: R {REMITO_PV}-{REMITO_NUM}")
    print(f"{'='*70}")
    print(f"  Servidor:   {SERVIDOR}")
    print(f"  Artículos:  {len(items_prep)} nuevos en msgestion01art")
    print(f"  Pedido:     en {' + '.join(BASES_PEDIDO)}")
    print(f"  Remito:     en {BASE_REMITO} (H4)")
    print(f"  Depósito:   {DEPOSITO}")
    print(f"  Modo:       {'DRY-RUN' if dry_run else 'PRODUCCION'}")
    print(f"{'='*70}")
    print(f"\n  {'Barcode':<18} {'Producto':<45} {'T':>2} {'Cant':>4}  {'Precio':>10}")
    print(f"  {'-'*18} {'-'*45} {'-'*2} {'-'*4}  {'-'*10}")
    for bc, desc, cant, precio, talle, cod_obj in items_prep:
        print(f"  {bc:<18} {desc[:45]:<45} {talle:>2} {cant:>4}  ${precio:>10,.0f}")
    print(f"\n  TOTAL: {total_uds} unidades — ${total_neto:,.0f} neto + IVA ${total_neto * 0.21:,.0f} = ${total_neto * 1.21:,.0f}")
    print(f"{'='*70}")

    if dry_run:
        print(f"\n[DRY RUN] Ningún dato fue escrito.")
        print(f"\n  Probando conexión a {SERVIDOR}...", end=" ")
        try:
            with pyodbc.connect(get_conn("msgestionC"), timeout=5) as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1")
                print("OK")
        except Exception as e:
            print(f"ERROR: {e}")
        return

    # =====================================================================
    # EJECUTAR
    # =====================================================================
    print(f"\n>>> Conectando a {SERVIDOR}...")
    conn = pyodbc.connect(get_conn("msgestionC"), timeout=10, autocommit=False)
    cursor = conn.cursor()

    try:
        # 1. ALTA ARTÍCULOS
        print(f"\n--- 1. Alta de {len(items_prep)} artículos ---")
        cursor.execute("SELECT ISNULL(MAX(codigo), 0) FROM msgestion01art.dbo.articulo")
        next_codigo = int(cursor.fetchone()[0]) + 1

        art_map = {}  # barcode -> codigo_articulo
        for i, (bc, desc, cant, precio, talle, cod_obj) in enumerate(items_prep):
            codigo = next_codigo + i
            art_map[bc] = codigo
            color = extraer_color(desc)
            desc3 = descripcion_3(desc)
            pf = precio  # precio_fabrica
            pc = pf      # precio_costo (sin descuento para Amphora)
            p1 = round(pc * (1 + UTILIDAD_1 / 100), 2)
            p2 = round(pc * (1 + UTILIDAD_2 / 100), 2)
            p3 = round(pc * (1 + UTILIDAD_3 / 100), 2)
            p4 = round(pc * (1 + UTILIDAD_4 / 100), 2)
            cursor.execute(SQL_ARTICULO, (
                codigo, desc, desc3, color, talle,
                bc, bc,
                MARCA, RUBRO, GRUPO, PROVEEDOR,
                cod_obj,
                pf, pc, pc,
                p1, p2, p3, p4,
                UTILIDAD_1, UTILIDAD_2, UTILIDAD_3, UTILIDAD_4,
            ))
            print(f"    [{codigo}] {bc} = {desc} T{talle} color={color} ${pf:,.0f} → P1=${p1:,.0f}")

        # 2. PEDIDO (en ambas bases)
        print(f"\n--- 2. Pedido en MSGESTION01 (03 es VIEW) ---")
        # Buscar MAX en CADA base por separado para evitar race condition
        max_nums = []
        for b in BASES_PEDIDO:
            cursor.execute(f"SELECT ISNULL(MAX(numero), 0) FROM {b}.dbo.pedico2 WHERE codigo = 8")
            max_nums.append(int(cursor.fetchone()[0]))
        num_pedido = max(max_nums) + 1
        print(f"    Número pedido: {num_pedido} (MAX por base: {max_nums})")
        obs = f"AMPHORA AW2026 — Fact {FACTURA} — {len(items_prep)} arts, {total_uds} uds"

        for base in BASES_PEDIDO:
            cursor.execute(SQL_PEDIDO_CAB.format(base=base), (
                num_pedido,
                PROVEEDOR, DENOMINACION,
                FECHA_FACTURA, datetime.now(),
                obs,
                PROVEEDOR,
            ))
            for reng, (bc, desc, cant, precio, talle, cod_obj) in enumerate(items_prep, 1):
                art_cod = art_map[bc]
                cursor.execute(SQL_PEDIDO_DET.format(base=base), (
                    num_pedido, reng,
                    art_cod, desc, bc,
                    cant, precio,
                    PROVEEDOR,
                    FECHA_FACTURA, FECHA_FACTURA,
                ))
            print(f"    {base}: NP #{num_pedido} — {len(items_prep)} reng, {total_uds} uds")

        # 3. REMITO (solo en BASE_REMITO = msgestion03/H4)
        print(f"\n--- 3. Remito en {BASE_REMITO} ---")
        cursor.execute(f"""
            SELECT ISNULL(MAX(orden), 0) + 1
            FROM {BASE_REMITO}.dbo.compras2
            WHERE codigo = 7 AND letra = 'R'
              AND sucursal = {REMITO_PV} AND numero = {REMITO_NUM}
        """)
        orden_remito = int(cursor.fetchone()[0])

        cursor.execute(SQL_REMITO_CAB.format(base=BASE_REMITO), (
            REMITO_PV, REMITO_NUM, orden_remito,
            DEPOSITO, PROVEEDOR, PROVEEDOR, DENOMINACION,
            FECHA_FACTURA, FECHA_FACTURA, FECHA_FACTURA,
            total_neto, total_neto,
            FECHA_FACTURA,
        ))

        cursor.execute(SQL_REMITO_EXT.format(base=BASE_REMITO), (
            REMITO_PV, REMITO_NUM, orden_remito,
            FECHA_FACTURA,
        ))

        for reng, (bc, desc, cant, precio, talle, cod_obj) in enumerate(items_prep, 1):
            art_cod = art_map[bc]
            monto = round(precio * cant, 2)
            cursor.execute(SQL_REMITO_DET.format(base=BASE_REMITO), (
                REMITO_PV, REMITO_NUM, orden_remito, reng,
                art_cod, desc, round(precio, 2), cant, DEPOSITO,
                FECHA_FACTURA, PROVEEDOR,
                cant, monto,
                cant, cant,
            ))

        for reng, (bc, desc, cant, precio, talle, cod_obj) in enumerate(items_prep, 1):
            art_cod = art_map[bc]
            cursor.execute(SQL_MOVI_STOCK.format(base=BASE_REMITO), (
                DEPOSITO, art_cod,
                REMITO_PV, REMITO_NUM, orden_remito,
                cant, round(precio, 2), PROVEEDOR,
                cant, FECHA_FACTURA,
            ))

        print(f"    R {REMITO_PV}-{REMITO_NUM} orden {orden_remito} — {len(items_prep)} reng, {total_uds} uds")

        # 4. PEDICO1_ENTREGAS + UPDATE pedico1
        # pedico1_entregas es tabla real en ambas bases → insertar en ambas
        # pedico1 es VIEW en 03 → UPDATE solo en 01 (tabla real)
        print(f"\n--- 4. Vincular entregas con pedido ---")
        BASES_ENTREGAS = ["MSGESTION01", "MSGESTION03"]
        for base in BASES_ENTREGAS:
            for reng, (bc, desc, cant, precio, talle, cod_obj) in enumerate(items_prep, 1):
                art_cod = art_map[bc]
                monto = round(precio * cant, 2)
                cursor.execute(SQL_PEDICO1_ENTREGAS.format(base=base), (
                    num_pedido, reng, art_cod, cant, DEPOSITO, FECHA_FACTURA,
                ))
            print(f"    {base}: {len(items_prep)} entregas insertadas")
        # UPDATE pedico1 solo en MSGESTION01 (tabla real, 03 es VIEW)
        for reng, (bc, desc, cant, precio, talle, cod_obj) in enumerate(items_prep, 1):
            monto = round(precio * cant, 2)
            cursor.execute(SQL_PEDICO1_UPDATE.format(base="MSGESTION01"), (
                cant, monto, num_pedido, reng,
            ))
        print(f"    MSGESTION01: {len(items_prep)} pedico1 actualizados")

        # COMMIT
        conn.commit()
        print(f"\n{'='*70}")
        print(f"  COMMIT OK")
        print(f"  Artículos: {next_codigo} a {next_codigo + len(items_prep) - 1}")
        print(f"  Pedido: #{num_pedido}")
        print(f"  Remito: R {REMITO_PV}-{REMITO_NUM} orden {orden_remito}")
        print(f"{'='*70}")

    except Exception as e:
        conn.rollback()
        print(f"\n  !!! ERROR — ROLLBACK !!!")
        print(f"  {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
