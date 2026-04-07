#!/usr/bin/env python3
"""
Insertar pedido John Foos (DISTRIGROUP SRL, proveedor 860) - Invierno 2026
Empresa: CALZALINDO -> INSERT en msgestion01.dbo.pedico2 + pedico1
88 pares, monto ~$4.216.744

Fuente: /compras/INVIERNO 2026/FreeTime_Distrigroup (JohnFoos)/Pedido Distrigroup 18-02/PEDIDO DISTRIGROUP JOHN FOOS.xlsx

Detalle del Excel (13 filas de producto):
  Row 0:  182 NEGRO          T38x2, T39x1, T40x1, T42x2, T45x1           = 7p  @ $45.833
  Row 1:  182 BLANCO         T35x2, T37x1, T38x2, T40x1, T42x1, T43x1,
                              T44x1, T45x1                                 = 9p  @ $45.833
  Row 2:  184 NEGRO          T35x1, T36x1, T39x2, T40x2, T41x2, T43x1   = 9p  @ $46.833
  Row 3:  182 tween NEGRO    T31x2, T33x2                                 = 4p  @ $37.721
  Row 4:  182 totally NEG/N  T38x1, T40x2, T44x1                         = 4p  @ $45.833
  Row 5:  164 flashback NEGRO T35x1, T36x1, T37x1, T38x2, T39x1,
                              T40x2, T42x1, T43x1                         = 10p @ $48.889
  Row 6:  182 all night NEGRO T36x1, T37x1, T38x1, T39x2, T40x2, T41x1,
                              T42x1                                        = 9p  @ $51.666
  Row 7:  182 all night BLANCO T35x1, T36x1, T37x1, T38x2, T39x2, T40x2,
                              T41x2, T42x1, T43x1, T44x1, T45x1          = 15p @ $51.666
  Row 8:  752 NEGRO          T37x1, T38x1, T39x2, T40x2                  = 6p  @ $50.000
  Row 9:  182 tween BLANCO   T31x1, T33x1                                = 2p  @ $37.721
  Row 10: 752 BLANCO         T37x1, T39x1                                = 2p  @ $50.000
  Row 11: 184 NEGRO/NEGRO    T36x2, T37x1, T38x1, T41x1, T42x1, T43x1   = 7p  @ $46.833
  Row 12: 182 avenue NEGRO   T38x1, T39x1, T40x1, T42x1                  = 4p  @ $48.889
  TOTAL: 88 pares, $4.216.744

Mapeo articulos en DB (msgestion01art.dbo.articulo, marca=860, estado='V'):
  182 NEGRO/BLANCO    -> 182 ZAPA ACRD C/PUNTERA   sinonimo 860182000X (color NEGRO/BLANCO)
  184 NEGRO           -> 184 BOTA ACORD C/PUNTERA   sinonimo 860184000X (color NEGRO/BLANCO)
  184 NEGRO/NEGRO     -> 184 BOTA ACORD C/PUNTERA   sinonimo 860184001X (color NEGRO/NEGRO)
  182 tween           -> 182 TWEEN ZAPA AC C/PUNT   sinonimo 860182TW
  182 totally         -> 182 TOTALLY BLACK ZAPA AC  sinonimo 860182TB
  164 flashback       -> 164 FLASHBACK 1/2 BOTA     sinonimo 860164D0
  182 all night NEGRO -> 182 ALL NIGHT ZAPA AC       sinonimo 860182A0 (color NEGRO)
  182 all night BLANCO-> 182 ALL NIGHT ZAPA AC       sinonimo 860182A0 (color BLANCO, codigo 1x)
  752                 -> 752 PLATAFORMA ZAPA C/PUNT  sinonimo 860752L0
  182 avenue          -> 182 AVENUE ZAPA AC COST     sinonimo 860182AV

PRECIOS: se usa el precio acordado del pedido (Excel), no el precio_fabrica de la DB.
  752: Excel $50.000 vs DB $53.889 -> se graba $50.000
  182 base: Excel $45.833 vs DB $49.721 -> se graba $45.833
"""

import pyodbc
from datetime import date

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;DATABASE=msgestion01;"
    "UID=am;PWD=dl;TrustServerCertificate=yes;Encrypt=no"
)

PROVEEDOR = 860
DENOMINACION = "DISTRIGROUP SRL"
OBS = "Pedido John Foos Invierno 2026. 88 pares. $4.216.744"
FECHA = date.today().strftime('%Y%m%d')

# Formato: (codigo_articulo, codigo_sinonimo, descripcion, cantidad, precio_pedido)
DETALLE = [
    # ---- 182 NEGRO (182 ZAPA ACRD C/PUNTERA, color NEGRO/BLANCO, sino 860182000X) ----
    # T38x2, T39x1, T40x1, T42x2, T45x1 = 7 pares @ $45.833
    (240817, "860182000038", "182 ZAPA ACRD C/PUNTERA NEGRO T38",  2, 45833),
    (240818, "860182000039", "182 ZAPA ACRD C/PUNTERA NEGRO T39",  1, 45833),
    (240819, "860182000040", "182 ZAPA ACRD C/PUNTERA NEGRO T40",  1, 45833),
    (240821, "860182000042", "182 ZAPA ACRD C/PUNTERA NEGRO T42",  2, 45833),
    (240824, "860182000045", "182 ZAPA ACRD C/PUNTERA NEGRO T45",  1, 45833),

    # ---- 182 BLANCO (182 ZAPA ACRD C/PUNTERA, color BLANCO, sino 860182000X) ----
    # T35x2, T37x1, T38x2, T42x1, T43x1, T44x1, T45x1 = 9 pares @ $45.833
    (240803, "860182000135", "182 ZAPA ACRD C/PUNTERA BLANCO T35", 2, 45833),
    (240805, "860182000137", "182 ZAPA ACRD C/PUNTERA BLANCO T37", 1, 45833),
    (240806, "860182000138", "182 ZAPA ACRD C/PUNTERA BLANCO T38", 2, 45833),
    (240810, "860182000142", "182 ZAPA ACRD C/PUNTERA BLANCO T42", 1, 45833),
    (240811, "860182000143", "182 ZAPA ACRD C/PUNTERA BLANCO T43", 1, 45833),
    (240812, "860182000144", "182 ZAPA ACRD C/PUNTERA BLANCO T44", 1, 45833),
    (240813, "860182000145", "182 ZAPA ACRD C/PUNTERA BLANCO T45", 1, 45833),

    # ---- 184 NEGRO (184 BOTA ACORD C/PUNTERA, color NEGRO/BLANCO, sino 860184000X) ----
    # T35x1, T36x1, T39x2, T40x2, T41x2, T44x1 = 9 pares @ $46.833
    (240779, "860184000035", "184 BOTA ACORD C/PUNTERA NEGRO T35", 1, 46833),
    (240780, "860184000036", "184 BOTA ACORD C/PUNTERA NEGRO T36", 1, 46833),
    (240783, "860184000039", "184 BOTA ACORD C/PUNTERA NEGRO T39", 2, 46833),
    (240784, "860184000040", "184 BOTA ACORD C/PUNTERA NEGRO T40", 2, 46833),
    (240847, "860184000041", "184 BOTA ACORD C/PUNTERA NEGRO T41", 2, 46833),
    (240850, "860184000044", "184 BOTA ACORD C/PUNTERA NEGRO T44", 1, 46833),

    # ---- 182 TWEEN NEGRO (182 TWEEN ZAPA AC C/PUNT, color NEGRO, sino 860182TW0X) ----
    # T31x2, T33x2 = 4 pares @ $37.721
    (269054, "860182TW0031", "182 TWEEN ZAPA AC C/PUNTERA NEGRO T31", 2, 37721),
    (269056, "860182TW0033", "182 TWEEN ZAPA AC C/PUNTERA NEGRO T33", 2, 37721),

    # ---- 182 TOTALLY BLACK (182 TOTALLY BLACK ZAPA AC, sino 860182TB) ----
    # T38x1, T40x2, T44x1 = 4 pares @ $45.833
    (240839, "860182TB0038", "182 TOTALLY BLACK ZAPA AC NEGRO T38", 1, 45833),
    (240841, "860182TB0040", "182 TOTALLY BLACK ZAPA AC NEGRO T40", 2, 45833),
    (240845, "860182TB0044", "182 TOTALLY BLACK ZAPA AC NEGRO T44", 1, 45833),

    # ---- 164 FLASHBACK NEGRO (164 FLASHBACK 1/2 BOTA AC COST, sino 860164D0) ----
    # T35x1, T36x1, T37x1, T38x2, T39x1, T40x2, T42x1, T43x1 = 10 pares @ $48.889
    (250046, "860164D00035", "164 FLASHBACK 1/2 BOTA NEGRO T35", 1, 48889),
    (245937, "860164D00036", "164 FLASHBACK 1/2 BOTA NEGRO T36", 1, 48889),
    (245938, "860164D00037", "164 FLASHBACK 1/2 BOTA NEGRO T37", 1, 48889),
    (245939, "860164D00038", "164 FLASHBACK 1/2 BOTA NEGRO T38", 2, 48889),
    (245940, "860164D00039", "164 FLASHBACK 1/2 BOTA NEGRO T39", 1, 48889),
    (245941, "860164D00040", "164 FLASHBACK 1/2 BOTA NEGRO T40", 2, 48889),
    (269057, "860164D00042", "164 FLASHBACK 1/2 BOTA NEGRO T42", 1, 48889),
    (269058, "860164D00043", "164 FLASHBACK 1/2 BOTA NEGRO T43", 1, 48889),

    # ---- 182 ALL NIGHT NEGRO (182 ALL NIGHT ZAPA AC, color NEGRO, sino 860182A00X) ----
    # T36x1, T37x1, T38x1, T39x2, T40x2, T41x1, T42x1 = 9 pares @ $51.666
    (245950, "860182A00036", "182 ALL NIGHT ZAPA AC NEGRO T36",  1, 51666),
    (245949, "860182A00037", "182 ALL NIGHT ZAPA AC NEGRO T37",  1, 51666),
    (242917, "860182A00038", "182 ALL NIGHT ZAPA AC NEGRO T38",  1, 51666),
    (242918, "860182A00039", "182 ALL NIGHT ZAPA AC NEGRO T39",  2, 51666),
    (242919, "860182A00040", "182 ALL NIGHT ZAPA AC NEGRO T40",  2, 51666),
    (242920, "860182A00041", "182 ALL NIGHT ZAPA AC NEGRO T41",  1, 51666),
    (242921, "860182A00042", "182 ALL NIGHT ZAPA AC NEGRO T42",  1, 51666),

    # ---- 182 ALL NIGHT BLANCO (182 ALL NIGHT ZAPA AC, color BLANCO, sino 860182A001X) ----
    # T35x1, T36x1, T37x1, T38x2, T39x2, T40x2, T41x2, T42x1, T43x1, T44x1, T45x1 = 15p @ $51.666
    (257603, "860182A00135", "182 ALL NIGHT ZAPA AC BLANCO T35", 1, 51666),
    (251073, "860182A00136", "182 ALL NIGHT ZAPA AC BLANCO T36", 1, 51666),
    (245951, "860182A00137", "182 ALL NIGHT ZAPA AC BLANCO T37", 1, 51666),
    (245952, "860182A00138", "182 ALL NIGHT ZAPA AC BLANCO T38", 2, 51666),
    (245953, "860182A00139", "182 ALL NIGHT ZAPA AC BLANCO T39", 2, 51666),
    (245954, "860182A00140", "182 ALL NIGHT ZAPA AC BLANCO T40", 2, 51666),
    (245955, "860182A00141", "182 ALL NIGHT ZAPA AC BLANCO T41", 2, 51666),
    (245956, "860182A00142", "182 ALL NIGHT ZAPA AC BLANCO T42", 1, 51666),
    (245957, "860182A00143", "182 ALL NIGHT ZAPA AC BLANCO T43", 1, 51666),
    (245958, "860182A00144", "182 ALL NIGHT ZAPA AC BLANCO T44", 1, 51666),
    (259619, "860182A00145", "182 ALL NIGHT ZAPA AC BLANCO T45", 1, 51666),

    # ---- 752 NEGRO (752 PLATAFORMA ZAPA C/PUNT, color NEGRO, sino 860752L00X) ----
    # T37x1, T38x1, T39x2, T40x2 = 6 pares @ $50.000
    (242933, "860752L00037", "752 PLATAFORMA ZAPA NEGRO T37", 1, 50000),
    (242934, "860752L00038", "752 PLATAFORMA ZAPA NEGRO T38", 1, 50000),
    (242935, "860752L00039", "752 PLATAFORMA ZAPA NEGRO T39", 2, 50000),
    (242936, "860752L00040", "752 PLATAFORMA ZAPA NEGRO T40", 2, 50000),

    # ---- 182 TWEEN BLANCO (182 TWEEN ZAPA AC C/PUNT, color BLANCO, sino 860182TW01X) ----
    # T31x1, T33x1 = 2 pares @ $37.721
    (269047, "860182TW0131", "182 TWEEN ZAPA AC C/PUNTERA BLANCO T31", 1, 37721),
    (269049, "860182TW0133", "182 TWEEN ZAPA AC C/PUNTERA BLANCO T33", 1, 37721),

    # ---- 752 BLANCO (752 PLATAFORMA ZAPA C/PUNT, color BLANCO, sino 860752L001X) ----
    # T38x1, T40x1 = 2 pares @ $50.000
    (285146, "860752L00138", "752 PLATAFORMA ZAPA BLANCO T38", 1, 50000),
    (285148, "860752L00140", "752 PLATAFORMA ZAPA BLANCO T40", 1, 50000),

    # ---- 184 NEGRO/NEGRO (184 BOTA ACORD C/PUNTERA, color NEGRO/NEGRO, sino 860184001X) ----
    # T36x2, T37x1, T38x1, T41x1, T42x1, T43x1 = 7 pares @ $46.833
    (285150, "860184001036", "184 BOTA ACORD C/PUNTERA NEGRO/NEGRO T36", 2, 46833),
    (285151, "860184001037", "184 BOTA ACORD C/PUNTERA NEGRO/NEGRO T37", 1, 46833),
    (285152, "860184001038", "184 BOTA ACORD C/PUNTERA NEGRO/NEGRO T38", 1, 46833),
    (285155, "860184001041", "184 BOTA ACORD C/PUNTERA NEGRO/NEGRO T41", 1, 46833),
    (285156, "860184001042", "184 BOTA ACORD C/PUNTERA NEGRO/NEGRO T42", 1, 46833),
    (285157, "860184001043", "184 BOTA ACORD C/PUNTERA NEGRO/NEGRO T43", 1, 46833),

    # ---- 182 AVENUE NEGRO (182 AVENUE ZAPA AC COST, sino 860182AV) ----
    # T38x1, T39x1, T40x1, T43x1 = 4 pares @ $48.889
    (278728, "860182AV0038", "182 AVENUE ZAPA AC NEGRO T38", 1, 48889),
    (240785, "860182AV0039", "182 AVENUE ZAPA AC NEGRO T39", 1, 48889),
    (240786, "860182AV0040", "182 AVENUE ZAPA AC NEGRO T40", 1, 48889),
    (240789, "860182AV0043", "182 AVENUE ZAPA AC NEGRO T43", 1, 48889),
]


def verificar_totales():
    total_pares = sum(d[3] for d in DETALLE)
    total_monto = sum(d[3] * d[4] for d in DETALLE)
    print("Verificacion pre-insercion:")
    print(f"  Renglones:      {len(DETALLE)}")
    print(f"  Pares totales:  {total_pares}  (esperado: 88)")
    print(f"  Monto total:    ${total_monto:,.0f}  (esperado: ~$4.216.744)")
    if total_pares != 88:
        raise ValueError(f"ERROR: Se esperaban 88 pares, hay {total_pares}")
    return total_pares, total_monto


def main():
    total_pares, total_monto = verificar_totales()

    conn = pyodbc.connect(CONN_STR)
    cur = conn.cursor()

    # Calcular proximo numero y orden
    cur.execute("SELECT ISNULL(MAX(numero), 0) + 1 FROM pedico2 WHERE codigo = 8")
    numero = cur.fetchone()[0]
    cur.execute("SELECT ISNULL(MAX(orden), 0) + 1 FROM pedico2 WHERE codigo = 8")
    orden = cur.fetchone()[0]
    if orden > 99:
        orden = 1
    print(f"\nProximo pedido: numero={numero}, orden={orden}")

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
    for i, (cod_art, sinonimo, descripcion, cantidad, precio) in enumerate(DETALLE, 1):
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
    print(f"  Pares:      {total_pares}")
    print(f"  Monto:      ${total_monto:,.0f}")
    print(f"  Renglones:  {len(DETALLE)}")

    # Verificacion post-insert
    cur.execute(
        "SELECT COUNT(*), SUM(cantidad) FROM pedico1 WHERE numero=? AND orden=?",
        numero, orden
    )
    vrow = cur.fetchone()
    print(f"\nVerificacion DB: {vrow[0]} renglones, {vrow[1]} pares en pedico1")
    conn.close()


if __name__ == '__main__':
    main()
