#!/usr/bin/env python3
"""
borrador_reposicion_P515_2026-04-11.py
============================================================
BORRADOR GENERADO AUTOMÁTICAMENTE POR agente-reposicion
NO EJECUTAR SIN REVISAR cantidades, precios y curvas de talle

Proveedor: 515 — ELEMENTO MEDIAS
Empresa (routing): CALZALINDO
Fecha análisis: 2026-04-11
Método: quiebre reconstruido + velocidad real + factor estacional mayo

RESUMEN:
  - 13 líneas (11 CRÍTICO, 2 URGENTE)
  - 3,209 unidades
  - $3,629,289 s/IVA (precio costo ref.)
"""

# =========================================================
# LÍNEAS SUGERIDAS (CSR = modelo+color, falta abrir curva talle)
# =========================================================

LINEAS = [
    {
        "csr": "5151140451",
        "desc": "404 MEDIA 1/3 ESTAMPA T.3",
        "stock": 275,
        "vel_ajust_mensual": 600.9,
        "cobertura_dias": 13.7,
        "meses_quebrados": 11,
        "compra_sugerida": 927,
        "precio_ref": 942,
        "costo_total_ref": 873234,
        "urgencia": "CRITICO",
    },
    {
        "csr": "5151310251",
        "desc": "102D C/S SOQUETE DEPORTIVO HOMBRE",
        "stock": 55,
        "vel_ajust_mensual": 324.15,
        "cobertura_dias": 5.1,
        "meses_quebrados": 11,
        "compra_sugerida": 593,
        "precio_ref": 1127,
        "costo_total_ref": 668311,
        "urgencia": "CRITICO",
    },
    {
        "csr": "5150010251",
        "desc": "102L C/S SOQUETE LISO HOMBRE",
        "stock": 14,
        "vel_ajust_mensual": 246.64,
        "cobertura_dias": 1.7,
        "meses_quebrados": 10,
        "compra_sugerida": 479,
        "precio_ref": 1127,
        "costo_total_ref": 539833,
        "urgencia": "CRITICO",
    },
    {
        "csr": "5151105451",
        "desc": "105 C/S SOQUETE KIDS T.4",
        "stock": 5,
        "vel_ajust_mensual": 110.44,
        "cobertura_dias": 1.4,
        "meses_quebrados": 7,
        "compra_sugerida": 216,
        "precio_ref": 1113,
        "costo_total_ref": 240408,
        "urgencia": "CRITICO",
    },
    {
        "csr": "5151240151",
        "desc": "401R MEDIA 1/3 DAMA RAYADO",
        "stock": 15,
        "vel_ajust_mensual": 83.71,
        "cobertura_dias": 5.4,
        "meses_quebrados": 6,
        "compra_sugerida": 152,
        "precio_ref": 1514,
        "costo_total_ref": 230128,
        "urgencia": "CRITICO",
    },
    {
        "csr": "5151105551",
        "desc": "105 C/S SOQUETE KIDS T.5",
        "stock": 17,
        "vel_ajust_mensual": 105.32,
        "cobertura_dias": 4.8,
        "meses_quebrados": 7,
        "compra_sugerida": 194,
        "precio_ref": 1113,
        "costo_total_ref": 215922,
        "urgencia": "CRITICO",
    },
    {
        "csr": "5151040251",
        "desc": "402L MEDIA 1/3 HOMBRE LISA",
        "stock": 19,
        "vel_ajust_mensual": 68.55,
        "cobertura_dias": 8.3,
        "meses_quebrados": 6,
        "compra_sugerida": 118,
        "precio_ref": 1741,
        "costo_total_ref": 205438,
        "urgencia": "CRITICO",
    },
    {
        "csr": "5151104351",
        "desc": "104 C/S SOQUETE KIDS T.3",
        "stock": -1,
        "vel_ajust_mensual": 46.34,
        "cobertura_dias": -0.6,
        "meses_quebrados": 12,
        "compra_sugerida": 94,
        "precio_ref": 989,
        "costo_total_ref": 92966,
        "urgencia": "CRITICO",
    },
    {
        "csr": "5154052051",
        "desc": "405 MEDIA 1/3 ESTAMPA T.4",
        "stock": 0,
        "vel_ajust_mensual": 31.07,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 62,
        "precio_ref": 1365,
        "costo_total_ref": 84630,
        "urgencia": "CRITICO",
    },
    {
        "csr": "515101D151",
        "desc": "101D SOQUETE DAMA DEPORTIVO",
        "stock": -1,
        "vel_ajust_mensual": 25.94,
        "cobertura_dias": -1.2,
        "meses_quebrados": 12,
        "compra_sugerida": 53,
        "precio_ref": 1205,
        "costo_total_ref": 63865,
        "urgencia": "CRITICO",
    },
    {
        "csr": "5150110251",
        "desc": "102R C/S SOQUETE RAYADO HOMBRE",
        "stock": 4,
        "vel_ajust_mensual": 29.47,
        "cobertura_dias": 4.1,
        "meses_quebrados": 10,
        "compra_sugerida": 55,
        "precio_ref": 1127,
        "costo_total_ref": 61985,
        "urgencia": "CRITICO",
    },
    {
        "csr": "5151020151",
        "desc": "201 MEDIA DAMA LISA SURTIDO",
        "stock": 211,
        "vel_ajust_mensual": 228.06,
        "cobertura_dias": 27.8,
        "meses_quebrados": 11,
        "compra_sugerida": 245,
        "precio_ref": 1353,
        "costo_total_ref": 331485,
        "urgencia": "URGENTE",
    },
    {
        "csr": "5151110151",
        "desc": "101L C/S SOQUETE DAMA LISO",
        "stock": 10,
        "vel_ajust_mensual": 15.37,
        "cobertura_dias": 19.5,
        "meses_quebrados": 10,
        "compra_sugerida": 21,
        "precio_ref": 1004,
        "costo_total_ref": 21084,
        "urgencia": "URGENTE",
    },
]

# =========================================================
# PASOS PARA PASAR DE BORRADOR → PEDIDO REAL
# =========================================================
# 1. Revisar cada CSR contra el catálogo vigente del proveedor
#    y descartar discontinuados.
# 2. Para cada CSR, abrir la curva de talles usando:
#    SELECT a.codigo, a.descripcion_5 AS talle, s.stock_actual
#    FROM msgestion01art.dbo.articulo a
#    LEFT JOIN msgestionC.dbo.stock s ON s.articulo=a.codigo
#    WHERE LEFT(a.codigo_sinonimo,10) = '<CSR>'
#    ORDER BY a.descripcion_5
# 3. Aplicar curva ideal (ver calcular_curva_ideal en app_reposicion.py)
#    o usar distribución histórica del mismo CSR.
# 4. Construir el dict de pedido y pasarlo a paso4_insertar_pedido.py
#    respetando routing por empresa:
#      get_tabla_base("pedico2", "CALZALINDO")
# 5. Verificar descuento/bonificación proveedor en config.py
# 6. Correr en el servidor 111 (producción)

# =========================================================
# PLANTILLA (comentada — NO EJECUTA)
# =========================================================
# from config import get_conn, get_tabla_base, PROVEEDORES
# from paso4_insertar_pedido import insertar_pedido
#
# pedido = {
#     "proveedor": 515,
#     "empresa": "CALZALINDO",
#     "fecha": "2026-04-11",
#     "renglones": [  # armar con articulo (codigo numerico), cantidad, precio
#         # {"articulo": 12345, "cantidad": 10, "precio": 1127.0},
#     ],
# }
# # insertar_pedido(pedido)  # descomentar cuando esté revisado

PROV = 515

if __name__ == "__main__":
    print("Borrador P" + str(PROV) + " — " + str(len(LINEAS)) + " lineas sugeridas")
    for l in LINEAS:
        print("  " + l["urgencia"].ljust(8) + " " + l["csr"] + " cob=" + str(l["cobertura_dias"]) + "d stk=" + str(l["stock"]) + " pedir=" + str(l["compra_sugerida"]) + " " + l["desc"])
