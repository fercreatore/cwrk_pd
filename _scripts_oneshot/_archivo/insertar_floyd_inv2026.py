"""
Script de inserción: Pedido Floyd Medias — Invierno 2026
Empresa: CALZALINDO → msgestion01
Proveedor: 641 (Floyd)
Total: 409 docenas = 4,908 pares | $7,370,110

Fuente: PEDIDO_FLOYD_INV2026.xlsx hoja ENTERO
Archivo de partes/entregas: PEDIDO_FLOYD_PARTES.xlsx (Marzo/Abril/Mayo)

NOTAS IMPORTANTES:
- Los artículos Floyd están dados de alta en el ERP en PARES (no docenas).
  Cantidad en pedico1 = docenas × 12.
- precio_unitario = precio_fabrica del ERP.
  Verificar contra factura real cuando llegue (Floyd puede tener precios actualizados).
- Artículo 1423 C/S: el ERP solo tiene variante Negro (305127) y Blanco (305126).
  Floyd pide "C/S" (colores surtidos). Usar código Negro como aproximación o
  dar de alta el C/S antes de insertar.
- Artículo 1424: Floyd pide "Blanco/Negro" → se mapea a ERP 641142405101 (B/N). OK.
- Discrepancia de versiones: INV2026 ENTERO = 409 doc / $7.37M
  PARTES Hoja1 = 458 doc / $8.84M (incluye Go711, Go710, Go740, Go413, Go473,
  Go480, Go600, Go800 en 3 colores, Go812 extra, Go810).
  CONFIRMAR con el usuario cuál versión es definitiva antes de insertar.

ESTRUCTURA pedico1 (columnas usadas):
  numero, orden, articulo, cantidad, precio, descuento, descuento_1, descuento_2,
  talle, color, deposito, usuario, estado, codigo=8, letra='X', sucursal=1
"""

import sys
import os

# Asegurar que config.py esté disponible
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyodbc
from config import get_conn_string as get_connection_string

# ─── PARÁMETROS DEL PEDIDO ────────────────────────────────────────────────────
EMPRESA   = "CALZALINDO"   # → msgestion01
PROVEEDOR = 641
DESCUENTO_PROV = 0          # Verificar: Floyd puede tener descuento. Confirmar con factura.
DESCUENTO_BON  = 0          # Bonificación adicional (si aplica)

# ─── DETALLE ──────────────────────────────────────────────────────────────────
# Formato: (codigo_articulo_erp, cantidad_pares, precio_unitario, descripcion)
# cantidad = docenas × 12 (los artículos Floyd están en PARES en el ERP)
# precio_unitario = precio_fabrica del ERP (ajustar si la factura difiere)

DETALLE = [
    # (codigo_erp,  pares, precio_fabrica, descripcion)
    ( 158689,   240,  1130.0, 'MJ8 C/S SOQUETE DAMA LISO'),
    ( 275218,   180,  2160.0, 'MJ19 SURTIDOS MEDIA TERMICA LISA'),
    ( 243203,   168,  1900.0, 'GO470 MEDIA 1/4 INVENCIBLE STRENGHT'),
    ( 158684,   168,  1305.0, '1414 C/S SOQUETE CORTO LISO'),
    ( 228258,   156,  1130.0, 'MJ6 SURTIDOS SOQUETE DAMA ESTAMPADO'),
    ( 243020,   120,  1805.0, 'MJ15 SURTIDOS MEDIA TERMICA PUÑO'),
    ( 243017,   132,  1505.0, 'MJ1 C/S MEDIA CASUAL LISA'),
    ( 243173,   120,  2610.0, '1418 C/S MEDIA TERMICA LISA'),
    ( 275219,   144,  1340.0, 'MJ2 NEGRO MEDIA TOBILLERA LISA'),
    ( 228262,   120,  1390.0, 'GO444 SOQUETE DEP FOOT BOOST'),
    ( 243021,    72,  1505.0, 'MJ18 SOQUETE INVISIBLE C/ANTIDESL'),
    ( 243195,   120,  1360.0, 'CL09 C/S MEDIA VESTIR LISA PUÑO SOFT'),
    ( 163369,   120,  1295.0, '1412 C/S SOQUETE TOBILLERA HOMBRE'),
    ( 275217,   108,  1505.0, 'MJ1 NEGRO MEDIA CASUAL LISA'),
    ( 158687,   120,  1340.0, 'MJ2 C/S MEDIA TOBILLERA LISA'),
    ( 228265,   108,  1475.0, 'GO741 SOQUETE DEP RESISTENCE PLUS'),
    ( 228261,   108,  1390.0, 'GO440 SOQUETE DEP DUAL POWER'),
    ( 343534,    96,  2345.0, '1408 MEDIA TOALLA C/PUÑO'),
    ( 224740,    96,  1390.0, 'GO410 SOQUETE DEP ULTIMATE FLOAT'),
    ( 275220,    96,  1805.0, '1420 C/S MEDIA CASUAL 2 RAYAS'),
    ( 343542,    84,  1340.0, 'MJ21 MEDIA CASUAL CAÑA 1/3 ESTAMPA'),
    ( 346958,    72,  1635.0, '1425 MEDIA CASUAL MORLEY ESTAMPADO'),
    ( 218958,    72,  1360.0, '1413 SURTIDOS SOQUETE CORTO ESTAMPADO'),
    ( 228257,    72,  1030.0, 'MJ13 NEGRO SOQUETE INVISIBLE LISO'),
    ( 228259,    60,  1390.0, 'GO441 SOQUETE DEP AIR CROSS'),
    ( 343538,    60,  1340.0, 'MJ20 MEDIA CASUAL CAÑA 1/3 ESTAMPA'),
    ( 343536,    60,  1000.0, '3000 C/S SOQUETE DE DAMA PACK X3'),
    ( 270010,    48,  2120.0, 'GO481 MEDIA ALTA PROLITE CREW'),
    ( 218959,    48,  1305.0, '1414 NEGRO SOQUETE CORTO LISO'),
    ( 270005,    36,  1620.0, 'GO472 MEDIA DEP SPORTY CAMOUFLAGE'),
    # ATENCIÓN: Floyd pide 1423 C/S pero ERP solo tiene Negro (305127) y Blanco (305126).
    # Usar Negro como aproximación. Confirmar con Fernando antes de ejecutar.
    ( 305127,    48,  1645.0, '1423 NEGRO MEDIA LISA CAÑA 1/3'),  # 4 doc C/S → Negro
    ( 284718,    48,  2665.0, 'GO803 NEGRO MEDIA FUTBOL NIÑO T3'),
    ( 218081,    36,  1135.0, 'MJ2 BLANCO MEDIA TOBILLERA LISA'),
    ( 243202,    48,  1360.0, '1412 NEGRO SOQUETE TOBILLERA HOMBRE'),
    ( 243019,    24,  2160.0, 'MJ12 SURTIDOS MEDIA TERMICA ESTAMPADA'),
    ( 343537,    36,  3200.0, '3010 C/S SOQUETE HOMBRE PACK X3'),
    ( 305127,    36,  1645.0, '1423 NEGRO MEDIA LISA CAÑA 1/3'),  # 3 doc Negro
    ( 228260,    24,  1685.0, 'GO442 SOQUETE DEP RESISTENCE PLUS'),
    ( 284720,    12,  2790.0, 'GO804 NEGRO MEDIA FUTBOL ADULTO T4'),
    ( 321833,    12,  3650.0, 'GO812 NEGRO PANTORRILLERA T5'),
    ( 243016,    36,  1275.0, 'MJ1 BLANCO MEDIA CASUAL LISA'),
    ( 218957,    24,  1295.0, '1412 BLANCO SOQUETE TOBILLERA'),
    # Floyd pide Blanco/Negro → ERP tiene B/N (359321). OK.
    ( 359321,    84,  1635.0, '1424 B/N MEDIA CASUAL CAÑA 1/3'),
    ( 284719,    12,  2665.0, 'GO803 ROJO MEDIA FUTBOL NIÑO T3'),
    ( 291730,    24,  2511.0, 'GO804 ROJO MEDIA FUTBOL ADULTO T4'),
    ( 284721,    12,  2790.0, 'GO804 MARINO MEDIA FUTBOL ADULTO T4'),
    # Artículos con talle (split por talle)
    ( 180913,   108,  1305.0, '59 SURTIDOS MEDIA CASUAL ESTAMPADA T1'),
    ( 180914,    24,  1305.0, '59 SURTIDOS MEDIA CASUAL ESTAMPADA T2'),
    ( 180915,   120,  1305.0, '59 SURTIDOS MEDIA CASUAL ESTAMPADA T3'),
    ( 180916,    36,  1305.0, '59 SURTIDOS MEDIA CASUAL ESTAMPADA T4'),
    ( 243184,    24,  1005.0, '63 SURTIDOS SOQUETE ANTIDESL ESTAMPADO T0'),
    ( 218985,    84,  1255.0, '63 SURTIDOS SOQUETE ANTIDESL ESTAMPADO T1'),
    ( 218986,    72,  1380.0, '63 SURTIDOS SOQUETE ANTIDESL ESTAMPADO T2'),
    ( 218987,    48,  1495.0, '63 SURTIDOS SOQUETE ANTIDESL ESTAMPADO T3'),
    ( 243188,    72,   940.0, '65 SURTIDOS MEDIA CASUAL 3D T0'),
    ( 243189,    48,  1150.0, '65 SURTIDOS MEDIA CASUAL 3D T1'),
    ( 243190,    24,  1285.0, '65 SURTIDOS MEDIA CASUAL 3D T2'),
    ( 243191,    72,  1475.0, '65 SURTIDOS MEDIA CASUAL 3D T3'),
    ( 243192,    36,  1605.0, '65 SURTIDOS MEDIA CASUAL 3D T4'),
    ( 180909,    24,  1220.0, '55 SURTIDOS MEDIA TERMICA ESTAMPADA T1'),
    ( 180910,    48,  1390.0, '55 SURTIDOS MEDIA TERMICA ESTAMPADA T2'),
    ( 180911,    48,  1805.0, '55 SURTIDOS MEDIA TERMICA ESTAMPADA T3'),
    ( 180912,    24,  1930.0, '55 SURTIDOS MEDIA TERMICA ESTAMPADA T4'),
    ( 346957,    24,  1135.0, '67 MEDIA CASUAL 1/3 CAÑA C/RAYAS T2'),
    ( 346932,    24,  1210.0, '67 MEDIA CASUAL 1/3 CAÑA C/RAYAS T3'),
    ( 346941,    24,  1295.0, '67 MEDIA CASUAL 1/3 CAÑA C/RAYAS T4'),
    ( 187873,    36,   955.0, '62 SOQUETE INVISIBLE ESTAMPADO T3'),
    ( 187872,    12,  1005.0, '62 SOQUETE INVISIBLE ESTAMPADO T4'),
    ( 346931,    12,   660.0, '300 PACK X3 LISO/EST BABY T00'),
    ( 346930,    48,   755.0, '300 PACK X3 LISO/EST BABY T0'),
    ( 344575,    24,  1015.0, '82 MEDIA LISA TOALLA T2'),
    ( 158691,    24,   800.0, '61 SOQUETE CORTO ESTAMPADO T1'),
    ( 343540,    24,  1210.0, '68 SURTIDOS MEDIA CASUAL CAÑA 1/3 T3'),
    ( 343541,    24,  1295.0, '68 SURTIDOS MEDIA CASUAL CAÑA 1/3 T4'),
]

# ─── VALIDACIONES PREVIAS ─────────────────────────────────────────────────────
total_pares = sum(d[1] for d in DETALLE)
total_docenas = total_pares // 12
print(f"Total líneas detalle: {len(DETALLE)}")
print(f"Total pares: {total_pares}  ({total_docenas} docenas)")
assert total_pares == 4908, f"Se esperaban 4908 pares, hay {total_pares}"
assert total_docenas == 409, f"Se esperaban 409 docenas, hay {total_docenas}"
print("Validación OK: 409 docenas / 4,908 pares")


def insertar_pedido_floyd(dry_run=True):
    """
    Inserta el pedido Floyd en pedico2 (cabecera) y pedico1 (detalle).
    dry_run=True: solo muestra lo que se haría sin ejecutar nada.
    """
    conn_str = get_connection_string("msgestion01")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # ── 1. Calcular próximo número de pedido ──────────────────────────────────
    # Usar MAX+1 como en el pipeline estándar
    cursor.execute("SELECT MAX(CAST(numero AS INT)) FROM MSGESTION01.dbo.pedico2 WHERE codigo=8 AND letra='X' AND sucursal=1")
    row = cursor.fetchone()
    ultimo_num = row[0] if row[0] else 0
    nuevo_numero = ultimo_num + 1

    cursor.execute("SELECT MAX(orden) FROM MSGESTION01.dbo.pedico2 WHERE codigo=8 AND letra='X' AND sucursal=1")
    row = cursor.fetchone()
    ultimo_orden = row[0] if row[0] else 0
    nuevo_orden = (ultimo_orden + 1) if (ultimo_orden + 1) <= 99 else 1

    import datetime
    hoy = datetime.date.today().strftime("%Y%m%d")

    monto_total = sum(d[1] * d[2] for d in DETALLE)

    print(f"\n{'='*60}")
    print(f"PEDIDO A INSERTAR:")
    print(f"  Número: {nuevo_numero}")
    print(f"  Orden:  {nuevo_orden}")
    print(f"  Proveedor: {PROVEEDOR}")
    print(f"  Empresa: {EMPRESA} → MSGESTION01")
    print(f"  Fecha: {hoy}")
    print(f"  Pares: {total_pares} ({total_docenas} docenas)")
    print(f"  Monto total (precio_fabrica): ${monto_total:,.0f}")
    print(f"  Líneas detalle: {len(DETALLE)}")
    print(f"{'='*60}")

    if dry_run:
        print("\n[DRY RUN] No se ejecuta nada. Pasar dry_run=False para insertar.")
        conn.close()
        return

    # ── 2. INSERT pedico2 (cabecera) ──────────────────────────────────────────
    sql_cab = """
    INSERT INTO MSGESTION01.dbo.pedico2
        (codigo, letra, sucursal, numero, orden, deposito,
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
         medio_pago, cuenta_cc, concurso)
    VALUES
        (8, 'X', 1, ?, ?, 0,
         ?, 'FLOYD SRL',
         ?, GETDATE(),
         ?,
         0, 0, 0, 0, 0, 0,
         21, 0, 10.5, 0, 0,
         0, 0,
         'V', 0, 'I', '', 1,
         'N', 'N', 'N', 'N', 'N',
         0, 'COWORK', 0, 2, 0, 0,
         0, 'N', 0, 0, 0,
         ' ', ?, 'N')
    """
    obs = f"Pedido Floyd Medias Invierno 2026. 409 docenas / {total_pares} pares. $7.370.110"
    cursor.execute(sql_cab, (
        nuevo_numero, nuevo_orden,
        PROVEEDOR,
        hoy,
        obs,
        PROVEEDOR
    ))
    print(f"pedico2 insertado: numero={nuevo_numero}, orden={nuevo_orden}")

    # ── 3. INSERT pedico1 (detalle) ───────────────────────────────────────────
    sql_det = """
    INSERT INTO MSGESTION01.dbo.pedico1
        (codigo, letra, sucursal, numero, orden, renglon,
         articulo, descripcion, cantidad, precio,
         descuento_reng1, descuento_reng2,
         estado, fecha,
         cuenta)
    VALUES
        (8, 'X', 1, ?, ?, ?,
         ?, ?, ?, ?,
         ?, ?,
         'V', CONVERT(datetime, ?, 112),
         ?)
    """
    for i, (art_cod, qty, precio, desc_art) in enumerate(DETALLE, 1):
        cursor.execute(sql_det, (
            nuevo_numero, nuevo_orden, i,
            art_cod, desc_art, qty, precio,
            DESCUENTO_PROV, DESCUENTO_BON,
            hoy,
            PROVEEDOR,
        ))
        print(f"  [{i:>3}] art={art_cod}, qty={qty}, precio={precio:.1f} — {desc_art}")

    conn.commit()
    print(f"\nPedido Floyd insertado exitosamente.")
    print(f"pedico2 número {nuevo_numero} | {len(DETALLE)} líneas | {total_pares} pares ({total_docenas} doc)")
    conn.close()


if __name__ == "__main__":
    dry_run = "--ejecutar" not in sys.argv
    if dry_run:
        print("\n*** MODO DRY RUN — para ejecutar: python insertar_floyd_inv2026.py --ejecutar ***\n")
    insertar_pedido_floyd(dry_run=dry_run)
