#!/usr/bin/env python3
"""
insertar_amphora_excel.py — Limpia y recarga pedido Amphora completo
====================================================================
PASO 1: Borra pedido viejo #1134073 (pedico1 + pedico2)
PASO 2: Borra 10 articulos malos (361300-361309, 0 movimientos)
PASO 3: Crea 19 articulos nuevos con sinonimo correcto 044{cod5}{color}{talle}
PASO 4: Inserta pedido nuevo (32 items, 53 pares, $2,291,000)

13 articulos ya existen (buenos), 19 se crean.

EJECUTAR EN EL 111:
  py -3 insertar_amphora_excel.py --dry-run
  py -3 insertar_amphora_excel.py --ejecutar
"""

import sys
import pyodbc
import socket
from datetime import date, datetime

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

# -- CONSTANTES ----------------------------------------------------------
BASE = "MSGESTION01"
PROVEEDOR = 44
DENOMINACION = "AMPHORA"
MARCA = 44
GRUPO = "5"
RUBRO = 1
FECHA = date(2026, 3, 16)
PEDIDO_VIEJO = 1134073
ARTS_BORRAR = list(range(361300, 361310))  # 361300-361309

# Colores: codigo 2 digitos
COLOR = {
    "NEGRO": "01", "BLANCO": "02", "BEIGE": "05",
    "CAMEL": "07", "TAUPE": "08", "CAFE": "10",
    "CAFE OSCURO": "13", "BLANCO ESPECIAL": "57",
}

# Talle/tamano cartera: codigo 2 digitos
TAMANO = {
    "BANANO": "01", "RINONERA": "01",
    "BANDOLERA": "02",
    "MOCHILA": "03",
    "CARTERA": "04",
    "PORTA NOTEBOOK": "05",
}

# Subrubro
SUBRUBRO = {
    "MOCHILA": 25, "BANANO": 39, "RINONERA": 39,
    "BANDOLERA": 39, "CARTERA": 18, "PORTA NOTEBOOK": 18,
}

def det_color(desc):
    d = desc.upper()
    for c in ["CAFE OSCURO", "BLANCO ESPECIAL", "NEGRO", "BLANCO", "BEIGE", "CAMEL", "TAUPE", "CAFE"]:
        if c in d:
            return c, COLOR[c]
    return "NEGRO", "01"

def det_tamano(desc):
    d = desc.upper()
    if "PORTA NOTEBOOK" in d: return "05"
    for k, v in TAMANO.items():
        if k in d: return v
    return "04"

def det_subrubro(desc):
    d = desc.upper()
    if "PORTA NOTEBOOK" in d: return 18
    for k, v in SUBRUBRO.items():
        if k in d: return v
    return 18

def det_cod5(desc):
    """Primeras 5 letras del nombre del modelo."""
    return desc.split()[0].upper()[:5].ljust(5)

def construir_sinonimo(desc):
    """044 + cod5 + color(2) + tamano(2) = 12 digitos."""
    _, cc = det_color(desc)
    tt = det_tamano(desc)
    c5 = det_cod5(desc)
    return f"044{c5}{cc}{tt}"

# -- 32 ITEMS: (barcode_numeric, art_existente, descripcion, cantidad, precio, markup) --
# art_existente = codigo si ya existe, None si hay que crear
ITEMS = [
    (4042423200001,  None,   "AMARANTA MOCHILA NEGRO",                      2, 42000),
    (4036421460001,  None,   "ANGELA CARTERA DOS ASAS NEGRO",               2, 44500),
    (4036421460008,  361253, "ANGELA CARTERA DOS ASAS TAUPE",               1, 44500),
    (40424027701,    None,   "BENIN CARTERA PORTA NOTEBOOK NEGRO",          2, 54500),
    (40423407501,    361247, "CAMELEON BANANO NEGRO",                        2, 39500),
    (4036421760001,  361254, "CHARLOTE MOCHILA NEGRO",                      2, 39500),
    (4036421760013,  361255, "CHARLOTE MOCHILA CAFE OSCURO",                1, 39500),
    (4036421780001,  361256, "CHARLOTE BANDOLERA NEGRO",                    2, 37000),
    (4036421780013,  361257, "CHARLOTE BANDOLERA CAFE OSCURO",              1, 37000),
    (40433905201,    330121, "CHIARA BANDOLERA NEGRO",                      2, 39500),
    (4043423450001,  None,   "ELIZA CARTERA DOS ASAS NEGRO",                2, 44500),
    (4043423450005,  None,   "ELIZA CARTERA DOS ASAS BEIGE",                2, 44500),
    (40424026901,    350024, "INGLATERRA BANDOLERA NEGRO",                  2, 39500),
    (4036421820001,  361251, "JENIFER CARTERA DOS ASAS TRES DIV NEGRO",     2, 49500),
    (4036421820010,  361252, "JENIFER CARTERA DOS ASAS TRES DIV CAFE",      1, 49500),
    (4006421040001,  361258, "JULIA CARTERA DOS ASAS NEGRO",                2, 39500),
    (40422745501,    361246, "KIRKLI MOCHILA NEGRO",                        2, 44500),
    (4043423500001,  None,   "MACARENA MOCHILA NEGRO",                      1, 42000),
    (4043423500013,  None,   "MACARENA MOCHILA CAFE OSCURO",                1, 42000),
    (4043423530001,  None,   "MAGDALENA CARTERA DOS ASAS NEGRO",            2, 44500),
    (4043423550001,  None,   "MAGDALENA BANDOLERA NEGRO",                   2, 39500),
    (4043423550057,  None,   "MAGDALENA BANDOLERA BLANCO ESPECIAL",         1, 39500),
    (40434035401,    345619, "MAGGIE CARTERA DOS ASAS NEGRO",               2, 44500),
    (40434035405,    None,   "MAGGIE CARTERA DOS ASAS BEIGE",               1, 44500),
    (40434035413,    None,   "MAGGIE CARTERA DOS ASAS CAFE OSCURO",         1, 44500),
    (4043424100001,  None,   "MAIDA CARTERA CORTE RECTO NEGRO",             2, 44500),
    (4043424100007,  None,   "MAIDA CARTERA CORTE RECTO CAMEL",             1, 44500),
    (4043424100013,  None,   "MAIDA CARTERA CORTE RECTO CAFE OSCURO",       1, 44500),
    (4043423900001,  None,   "MARGARET CARTERA DOS ASAS NEGRO",             2, 44500),
    (4043423900010,  None,   "MARGARET CARTERA DOS ASAS CAFE",              2, 44500),
    (4043423970001,  None,   "MARGOT CARTERA DOS ASAS NEGRO",               2, 44500),
    (4043423970013,  None,   "MARGOT CARTERA DOS ASAS CAFE OSCURO",         2, 44500),
]

SQL_ARTICULO = """
    INSERT INTO msgestion01art.dbo.articulo (
        codigo, codigo_sinonimo, codigo_barra,
        descripcion_1, descripcion_4, descripcion_5,
        proveedor, marca, grupo, rubro, subrubro,
        precio_4, utilidad_1,
        codigo_objeto_costo,
        estado
    ) VALUES (?, ?, ?, ?, ?, ?, 44, 44, '5', 1, ?, ?, 100, ?, 'V')
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


def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]
    dry_run = modo != "--ejecutar"

    total_uds = sum(i[3] for i in ITEMS)
    total_neto = sum(i[3] * i[4] for i in ITEMS)
    existentes = sum(1 for i in ITEMS if i[1] is not None)
    nuevos = sum(1 for i in ITEMS if i[1] is None)

    print(f"\n{'='*70}")
    print(f"AMPHORA AW2026 — PEDIDO COMPLETO LIMPIO")
    print(f"{'='*70}")
    print(f"  Servidor:          {SERVIDOR}")
    print(f"  Base:              {BASE}")
    print(f"  Items:             {len(ITEMS)} ({existentes} existentes + {nuevos} nuevos)")
    print(f"  Pares:             {total_uds}")
    print(f"  Neto:              ${total_neto:,.0f}")
    print(f"  Pedido a borrar:   #{PEDIDO_VIEJO}")
    print(f"  Arts a borrar:     {ARTS_BORRAR[0]}-{ARTS_BORRAR[-1]} ({len(ARTS_BORRAR)})")
    print(f"  Modo:              {'DRY-RUN' if dry_run else 'PRODUCCION'}")
    print(f"{'='*70}")

    print(f"\n  ARTICULOS EXISTENTES ({existentes}):")
    for bc, art, desc, cant, precio in ITEMS:
        if art is not None:
            print(f"    [{art:6d}] {desc[:50]:50s} x{cant} ${precio:,.0f}")

    print(f"\n  ARTICULOS A CREAR ({nuevos}):")
    for bc, art, desc, cant, precio in ITEMS:
        if art is None:
            sin = construir_sinonimo(desc)
            color_name, _ = det_color(desc)
            sub = det_subrubro(desc)
            print(f"    SIN:{sin} BC:{bc} {desc[:45]:45s} x{cant} ${precio:,.0f} sub={sub} col={color_name}")

    print(f"\n  TOTAL: {total_uds} pares — ${total_neto:,.0f}")

    if dry_run:
        print(f"\n  [DRY RUN] No se escribio nada.")
        try:
            with pyodbc.connect(get_conn("msgestionC"), timeout=5) as conn:
                conn.cursor().execute("SELECT 1")
                print(f"  Conexion OK")
        except Exception as e:
            print(f"  Conexion ERROR: {e}")
        return

    confirmacion = input(f"\n  Ejecutar? (s/N): ").strip().lower()
    if confirmacion != "s":
        print("  Cancelado.")
        sys.exit(0)

    conn = pyodbc.connect(get_conn(BASE), timeout=10, autocommit=False)
    cursor = conn.cursor()

    try:
        # PASO 1: Borrar pedido viejo
        print(f"\n--- PASO 1: Borrar pedido #{PEDIDO_VIEJO} ---")
        cursor.execute(f"DELETE FROM {BASE}.dbo.pedico1 WHERE numero = ? AND codigo = 8", PEDIDO_VIEJO)
        d1 = cursor.rowcount
        cursor.execute(f"DELETE FROM {BASE}.dbo.pedico2 WHERE numero = ? AND codigo = 8", PEDIDO_VIEJO)
        d2 = cursor.rowcount
        print(f"    pedico1: {d1} renglones, pedico2: {d2} cabecera")

        # PASO 2: Borrar articulos malos
        print(f"\n--- PASO 2: Borrar articulos {ARTS_BORRAR[0]}-{ARTS_BORRAR[-1]} ---")
        for cod in ARTS_BORRAR:
            cursor.execute("DELETE FROM msgestion01art.dbo.articulo WHERE codigo = ?", cod)
        print(f"    {len(ARTS_BORRAR)} articulos eliminados")

        # PASO 3: Crear articulos nuevos
        print(f"\n--- PASO 3: Crear {nuevos} articulos ---")
        cursor.execute("SELECT ISNULL(MAX(codigo), 0) FROM msgestion01art.dbo.articulo")
        next_cod = int(cursor.fetchone()[0]) + 1

        art_map = {}  # indice -> codigo_articulo
        for idx, (bc, art, desc, cant, precio) in enumerate(ITEMS):
            if art is not None:
                art_map[idx] = art
                continue

            codigo = next_cod
            next_cod += 1
            sin = construir_sinonimo(desc)
            color_name, color_code = det_color(desc)
            tamano = det_tamano(desc)
            sub = det_subrubro(desc)
            cod5 = det_cod5(desc)
            markup = round(precio * 1.45, 2)  # 45% markup como los existentes

            cursor.execute(SQL_ARTICULO, (
                codigo, sin, bc,
                desc, color_name, tamano,
                sub,
                markup, cod5,
            ))
            art_map[idx] = codigo
            print(f"    [{codigo}] {sin} {desc[:45]} sub={sub}")

        # PASO 4: Insertar pedido nuevo
        print(f"\n--- PASO 4: Insertar pedido ---")
        cursor.execute(f"SELECT ISNULL(MAX(numero),0)+1 FROM {BASE}.dbo.pedico2 WHERE codigo = 8")
        num_pedido = int(cursor.fetchone()[0])

        obs = f"AMPHORA AW2026 — {len(ITEMS)} arts, {total_uds} uds, ${total_neto:,.0f}"

        cursor.execute(SQL_PEDIDO_CAB.format(base=BASE), (
            num_pedido,
            PROVEEDOR, DENOMINACION,
            FECHA, datetime.now(),
            obs,
            PROVEEDOR,
        ))

        for reng, (bc, art_orig, desc, cant, precio) in enumerate(ITEMS, 1):
            art_cod = art_map[reng - 1]
            # Buscar el sinonimo real del articulo
            cursor.execute("SELECT codigo_sinonimo FROM msgestion01art.dbo.articulo WHERE codigo = ?", art_cod)
            row = cursor.fetchone()
            sin = row[0] if row else str(bc)

            cursor.execute(SQL_PEDIDO_DET.format(base=BASE), (
                num_pedido, reng,
                art_cod, desc, sin,
                cant, precio,
                PROVEEDOR,
                FECHA, FECHA,
            ))

        print(f"    NP #{num_pedido} — {len(ITEMS)} renglones, {total_uds} pares")

        conn.commit()

        print(f"\n{'='*70}")
        print(f"  COMMIT OK")
        print(f"  Pedido viejo #{PEDIDO_VIEJO}: BORRADO")
        print(f"  Arts malos 361300-361309: BORRADOS")
        print(f"  Arts nuevos: {nuevos} creados")
        print(f"  Pedido nuevo #{num_pedido}: {len(ITEMS)} renglones, {total_uds} pares")
        print(f"{'='*70}")

        # Verificar
        cursor.execute(f"""
            SELECT COUNT(*), SUM(cantidad)
            FROM {BASE}.dbo.pedico1
            WHERE numero = ? AND codigo = 8
        """, num_pedido)
        check = cursor.fetchone()
        print(f"\n  Verificacion: {check[0]} renglones, {check[1]} pares (debe ser 32/53)")

    except Exception as e:
        conn.rollback()
        print(f"\n  ERROR — ROLLBACK: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
