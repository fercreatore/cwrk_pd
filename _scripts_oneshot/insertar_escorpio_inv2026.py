"""
Script de inserción: Pedido Escorpio (Botas de Lluvia Niños) — Invierno 2026
Empresa: CALZALINDO → msgestion01
Proveedor: 896 — CALZADOS ARGENTINOS SA (nombre_fantasia: "Escorpio Seguridad (botas de goma)")
Total: 60 pares | ~$515,000

Fuente: CLAUDE.md (resumen pedidos invierno 2026)

NOTAS IMPORTANTES:
- Talles DOBLES: 23/24, 25/26, 27/28, 29/30, 31/32, 33/34
  En el ERP cada artículo tiene UN talle (el par). Se usa el talle par: 24, 26, 28, 30, 32, 34.
- Artículo 050 AMARILLO BOTA DE LLUVIA S/CUELLO (proveedor 896, modelo 050)
  Talles 24-34 con códigos ERP: 359214, 264156, 264157, 264158, 264159, 264160
- Precio ERP vigente: $9,340.80
  ATENCIÓN: El precio ERP da monto total de $560,448 (vs. $515,000 estimado).
  Si el precio correcto es $8,583.33 (para exactamente $515K), actualizar PRECIO_UNITARIO
  antes de ejecutar con --ejecutar. Confirmar con Fernando / lista de precios Escorpio.
- Distribución: 10 pares por talle (igual por todos los 6 talles)
- Empresa: CALZALINDO → INSERT en msgestion01

ESTRUCTURA pedico1 (columnas usadas):
  codigo, letra, sucursal, numero, orden, articulo, cantidad, precio,
  descuento, descuento_1, usuario, estado
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyodbc
from config import get_conn_string

# ─── PARÁMETROS DEL PEDIDO ────────────────────────────────────────────────────
EMPRESA        = "CALZALINDO"   # → msgestion01
PROVEEDOR      = 896            # CALZADOS ARGENTINOS SA / Escorpio Seguridad
DESCUENTO_PROV = 0              # Sin descuento (confirmar con lista de precios)
DESCUENTO_BON  = 0              # Sin bonificación adicional

# PRECIO UNITARIO: El ERP tiene $9,340.80 pero el estimado es $515K / 60 = ~$8,583.33
# Usar el precio del ERP como base. Si hay diferencia, actualizar antes de --ejecutar.
PRECIO_UNITARIO = 9340.80       # precio_fabrica del ERP — VERIFICAR CONTRA FACTURA REAL

# ─── DETALLE ──────────────────────────────────────────────────────────────────
# Talles dobles 23/24, 25/26, 27/28, 29/30, 31/32, 33/34
# En ERP: un artículo por talle (el par), 10 pares cada talle
# Formato: (codigo_erp, cantidad_pares, precio_unitario, descripcion, talle_erp)

DETALLE = [
    # (cod_erp,  qty, precio,           descripcion,                   talle_double)
    (359214,    10,  PRECIO_UNITARIO,   '050 AMARILLO BOTA LLUVIA T23/24',  '24'),
    (264156,    10,  PRECIO_UNITARIO,   '050 AMARILLO BOTA LLUVIA T25/26',  '26'),
    (264157,    10,  PRECIO_UNITARIO,   '050 AMARILLO BOTA LLUVIA T27/28',  '28'),
    (264158,    10,  PRECIO_UNITARIO,   '050 AMARILLO BOTA LLUVIA T29/30',  '30'),
    (264159,    10,  PRECIO_UNITARIO,   '050 AMARILLO BOTA LLUVIA T31/32',  '32'),
    (264160,    10,  PRECIO_UNITARIO,   '050 AMARILLO BOTA LLUVIA T33/34',  '34'),
]

# ─── VALIDACIONES PREVIAS ─────────────────────────────────────────────────────
total_pares  = sum(d[1] for d in DETALLE)
monto_total  = sum(d[1] * d[2] for d in DETALLE)
print(f"Total líneas detalle: {len(DETALLE)}")
print(f"Total pares: {total_pares}")
print(f"Monto total (precio_fabrica): ${monto_total:,.2f}")
assert total_pares == 60, f"Se esperaban 60 pares, hay {total_pares}"
print("Validación OK: 60 pares")
print(f"NOTA: Monto al precio ERP = ${monto_total:,.2f} (estimado original ~$515,000)")
print("      Si el precio real difiere, actualizar PRECIO_UNITARIO antes de --ejecutar")


def insertar_pedido_escorpio(dry_run=True):
    """
    Inserta el pedido Escorpio en pedico2 (cabecera) y pedico1 (detalle).
    dry_run=True: muestra qué se haría sin ejecutar nada.
    """
    conn_str = get_conn_string("msgestion01")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # ── 1. Calcular próximo número de pedido ──────────────────────────────────
    cursor.execute(
        "SELECT MAX(CAST(numero AS INT)) FROM MSGESTION01.dbo.pedico2 "
        "WHERE codigo=8 AND letra='X' AND sucursal=1"
    )
    row = cursor.fetchone()
    ultimo_num  = row[0] if row[0] else 0
    nuevo_numero = ultimo_num + 1

    cursor.execute(
        "SELECT MAX(orden) FROM MSGESTION01.dbo.pedico2 "
        "WHERE codigo=8 AND letra='X' AND sucursal=1"
    )
    row = cursor.fetchone()
    ultimo_orden = row[0] if row[0] else 0
    nuevo_orden  = (ultimo_orden + 1) if (ultimo_orden + 1) <= 99 else 1

    import datetime
    hoy = datetime.date.today().strftime("%Y%m%d")

    # Buscar nombre proveedor
    cursor.execute("SELECT denominacion FROM MSGESTION01.dbo.proveedores WHERE numero=?", (PROVEEDOR,))
    row = cursor.fetchone()
    nombre_prov = row[0] if row else f"PROVEEDOR {PROVEEDOR}"

    print(f"\n{'='*60}")
    print(f"PEDIDO A INSERTAR:")
    print(f"  Número:     {nuevo_numero}")
    print(f"  Orden:      {nuevo_orden}")
    print(f"  Proveedor:  {PROVEEDOR} — {nombre_prov}")
    print(f"  Empresa:    {EMPRESA} → MSGESTION01")
    print(f"  Fecha:      {hoy}")
    print(f"  Pares:      {total_pares}")
    print(f"  Monto:      ${monto_total:,.2f}")
    print(f"  Líneas:     {len(DETALLE)}")
    print(f"{'='*60}")
    print()
    for i, (art_cod, qty, precio, desc_art, talle) in enumerate(DETALLE, 1):
        print(f"  [{i}] art={art_cod}, talle={talle}, qty={qty}, precio={precio:.2f} — {desc_art}")

    if dry_run:
        print(f"\n[DRY RUN] No se ejecutó nada.")
        print("Para insertar: python _scripts_oneshot/insertar_escorpio_inv2026.py --ejecutar")
        conn.close()
        return

    # ── 2. INSERT pedico2 (cabecera) ──────────────────────────────────────────
    sql_cab = """
    INSERT INTO MSGESTION01.dbo.pedico2
        (codigo, letra, sucursal, numero, orden,
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
         observaciones)
    VALUES
        (8, 'X', 1, ?, ?,
         0, ?, ?,
         ?, GETDATE(),
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
         ?)
    """
    obs = f"Pedido Escorpio Botas Lluvia Invierno 2026. {total_pares} pares. ${monto_total:,.0f}"
    cursor.execute(sql_cab, (
        nuevo_numero, nuevo_orden,
        PROVEEDOR, nombre_prov,
        hoy,
        PROVEEDOR,
        obs,
    ))
    print(f"pedico2 insertado: numero={nuevo_numero}, orden={nuevo_orden}")

    # ── 3. INSERT pedico1 (detalle) ───────────────────────────────────────────
    sql_det = """
    INSERT INTO MSGESTION01.dbo.pedico1
        (codigo, letra, sucursal, numero, orden, renglon,
         articulo, descripcion, precio, cantidad,
         descuento_reng1, descuento_reng2,
         estado, fecha,
         cuenta,
         codigo_sinonimo)
    VALUES
        (8, 'X', 1, ?, ?, ?,
         ?, ?, ?, ?,
         ?, ?,
         'V', CONVERT(datetime, ?, 112),
         ?,
         ?)
    """
    for i, (art_cod, qty, precio, desc_art, talle) in enumerate(DETALLE, 1):
        cursor.execute(sql_det, (
            nuevo_numero, nuevo_orden, i,
            art_cod, desc_art, precio, qty,
            DESCUENTO_PROV, DESCUENTO_BON,
            hoy,
            PROVEEDOR,
            '',
        ))
        print(f"  [{i}] art={art_cod}, talle={talle}, qty={qty} — {desc_art}")

    conn.commit()
    print(f"\nPedido Escorpio insertado exitosamente.")
    print(f"pedico2 número {nuevo_numero} | {len(DETALLE)} líneas | {total_pares} pares | ${monto_total:,.2f}")
    conn.close()


if __name__ == "__main__":
    dry_run = "--ejecutar" not in sys.argv
    if dry_run:
        print("\n*** MODO DRY RUN — para ejecutar: python insertar_escorpio_inv2026.py --ejecutar ***\n")
    insertar_pedido_escorpio(dry_run=dry_run)
