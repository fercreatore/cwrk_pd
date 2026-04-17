#!/usr/bin/env python3
"""
borrador_reposicion_P594_2026-04-11.py
============================================================
BORRADOR GENERADO AUTOMÁTICAMENTE POR agente-reposicion
NO EJECUTAR SIN REVISAR cantidades, precios y curvas de talle

Proveedor: 594 — VICBOR (Atomik/Wake/Footy)
Empresa (routing): H4
Fecha análisis: 2026-04-11
Método: quiebre reconstruido + velocidad real + factor estacional mayo

RESUMEN:
  - 12 líneas (9 CRÍTICO, 3 URGENTE)
  - 220 unidades
  - $4,101,575 s/IVA (precio costo ref.)
"""

# =========================================================
# LÍNEAS SUGERIDAS (CSR = modelo+color, falta abrir curva talle)
# =========================================================

LINEAS = [
    {
        "csr": "594OHIO001",
        "desc": "OHIO BLANCO ZAPA DEP ABROJO",
        "stock": 6,
        "vel_ajust_mensual": 17.93,
        "cobertura_dias": 10.0,
        "meses_quebrados": 10,
        "compra_sugerida": 30,
        "precio_ref": 25354,
        "costo_total_ref": 760620,
        "urgencia": "CRITICO",
    },
    {
        "csr": "594BLUSH25",
        "desc": "BLUSH NUDE ZUECO PLAYERO",
        "stock": 0,
        "vel_ajust_mensual": 17.72,
        "cobertura_dias": 0.0,
        "meses_quebrados": 8,
        "compra_sugerida": 35,
        "precio_ref": 20273,
        "costo_total_ref": 709555,
        "urgencia": "CRITICO",
    },
    {
        "csr": "594ASAND00",
        "desc": "SAND NEGRO ZUECO PLAYERO FAJA",
        "stock": 1,
        "vel_ajust_mensual": 11.4,
        "cobertura_dias": 2.6,
        "meses_quebrados": 6,
        "compra_sugerida": 22,
        "precio_ref": 20273,
        "costo_total_ref": 446006,
        "urgencia": "CRITICO",
    },
    {
        "csr": "594WKC7210",
        "desc": "WKC072 NEGRO/NEGRO ZAPA DEP",
        "stock": 3,
        "vel_ajust_mensual": 13.62,
        "cobertura_dias": 6.6,
        "meses_quebrados": 9,
        "compra_sugerida": 24,
        "precio_ref": 18400,
        "costo_total_ref": 441600,
        "urgencia": "CRITICO",
    },
    {
        "csr": "594TFEEL00",
        "desc": "RESTFEEL NEGRO CHINELA FAJA",
        "stock": 1,
        "vel_ajust_mensual": 8.51,
        "cobertura_dias": 3.5,
        "meses_quebrados": 7,
        "compra_sugerida": 16,
        "precio_ref": 23322,
        "costo_total_ref": 373152,
        "urgencia": "CRITICO",
    },
    {
        "csr": "594BLUSH00",
        "desc": "BLUSH NEGRO ZUECO PLAYERO",
        "stock": -5,
        "vel_ajust_mensual": 13.76,
        "cobertura_dias": -10.9,
        "meses_quebrados": 10,
        "compra_sugerida": 33,
        "precio_ref": 9145,
        "costo_total_ref": 301785,
        "urgencia": "CRITICO",
    },
    {
        "csr": "5940031600",
        "desc": "WKC316 NEGRO ZAPA DEP TEJIDA",
        "stock": 0,
        "vel_ajust_mensual": 6.25,
        "cobertura_dias": 0.0,
        "meses_quebrados": 8,
        "compra_sugerida": 13,
        "precio_ref": 19600,
        "costo_total_ref": 254800,
        "urgencia": "CRITICO",
    },
    {
        "csr": "594WK26900",
        "desc": "WKC269 NEGRO ZAPA DEP",
        "stock": 0,
        "vel_ajust_mensual": 7.71,
        "cobertura_dias": 0.0,
        "meses_quebrados": 8,
        "compra_sugerida": 15,
        "precio_ref": 15200,
        "costo_total_ref": 228000,
        "urgencia": "CRITICO",
    },
    {
        "csr": "594KC18200",
        "desc": "WKC182 NEGRO ZAPA DEP",
        "stock": 0,
        "vel_ajust_mensual": 2.5,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 5,
        "precio_ref": 18400,
        "costo_total_ref": 92000,
        "urgencia": "CRITICO",
    },
    {
        "csr": "594WK11400",
        "desc": "WKC114 NEGRO ZAPA DEP TEJIDA",
        "stock": 7,
        "vel_ajust_mensual": 8.76,
        "cobertura_dias": 24.0,
        "meses_quebrados": 10,
        "compra_sugerida": 11,
        "precio_ref": 18400,
        "costo_total_ref": 202400,
        "urgencia": "URGENTE",
    },
    {
        "csr": "594BLUSH14",
        "desc": "BLUSH VERDE ZUECO PLAYERO",
        "stock": 5,
        "vel_ajust_mensual": 7.0,
        "cobertura_dias": 21.4,
        "meses_quebrados": 7,
        "compra_sugerida": 9,
        "precio_ref": 20273,
        "costo_total_ref": 182457,
        "urgencia": "URGENTE",
    },
    {
        "csr": "594WK25500",
        "desc": "WKC255 NEGRO PANCHA",
        "stock": 4,
        "vel_ajust_mensual": 5.7,
        "cobertura_dias": 21.1,
        "meses_quebrados": 6,
        "compra_sugerida": 7,
        "precio_ref": 15600,
        "costo_total_ref": 109200,
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
#      get_tabla_base("pedico2", "H4")
# 5. Verificar descuento/bonificación proveedor en config.py
# 6. Correr en el servidor 111 (producción)

# =========================================================
# PLANTILLA (comentada — NO EJECUTA)
# =========================================================
# from config import get_conn, get_tabla_base, PROVEEDORES
# from paso4_insertar_pedido import insertar_pedido
#
# pedido = {
#     "proveedor": 594,
#     "empresa": "H4",
#     "fecha": "2026-04-11",
#     "renglones": [  # armar con articulo (codigo numerico), cantidad, precio
#         # {"articulo": 12345, "cantidad": 10, "precio": 1127.0},
#     ],
# }
# # insertar_pedido(pedido)  # descomentar cuando esté revisado

PROV = 594

if __name__ == "__main__":
    print("Borrador P" + str(PROV) + " — " + str(len(LINEAS)) + " lineas sugeridas")
    for l in LINEAS:
        print("  " + l["urgencia"].ljust(8) + " " + l["csr"] + " cob=" + str(l["cobertura_dias"]) + "d stk=" + str(l["stock"]) + " pedir=" + str(l["compra_sugerida"]) + " " + l["desc"])
