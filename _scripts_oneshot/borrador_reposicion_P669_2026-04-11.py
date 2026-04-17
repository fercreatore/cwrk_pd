#!/usr/bin/env python3
"""
borrador_reposicion_P669_2026-04-11.py
============================================================
BORRADOR GENERADO AUTOMÁTICAMENTE POR agente-reposicion
NO EJECUTAR SIN REVISAR cantidades, precios y curvas de talle

Proveedor: 669 — LANACUER/LA CHAPELLE
Empresa (routing): H4
Fecha análisis: 2026-04-11
Método: quiebre reconstruido + velocidad real + factor estacional mayo

RESUMEN:
  - 12 líneas (12 CRÍTICO, 0 URGENTE)
  - 111 unidades
  - $897,676 s/IVA (precio costo ref.)
"""

# =========================================================
# LÍNEAS SUGERIDAS (CSR = modelo+color, falta abrir curva talle)
# =========================================================

LINEAS = [
    {
        "csr": "6692780251",
        "desc": "12UO7802 VALIJA CARRY ON 20'",
        "stock": 1,
        "vel_ajust_mensual": 4.89,
        "cobertura_dias": 6.1,
        "meses_quebrados": 7,
        "compra_sugerida": 9,
        "precio_ref": 34000,
        "costo_total_ref": 306000,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6695084751",
        "desc": "34UM5084 BUFANDA SURTIDA",
        "stock": 0,
        "vel_ajust_mensual": 16.72,
        "cobertura_dias": 0.0,
        "meses_quebrados": 10,
        "compra_sugerida": 33,
        "precio_ref": 6155,
        "costo_total_ref": 203115,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6696513751",
        "desc": "16UM6513 ALMOHADA DE VIAJE",
        "stock": 1,
        "vel_ajust_mensual": 6.06,
        "cobertura_dias": 4.9,
        "meses_quebrados": 5,
        "compra_sugerida": 11,
        "precio_ref": 8799,
        "costo_total_ref": 96789,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6696514751",
        "desc": "16UM6514 ALMOHADA DE VIAJE",
        "stock": 0,
        "vel_ajust_mensual": 5.14,
        "cobertura_dias": 0.0,
        "meses_quebrados": 5,
        "compra_sugerida": 10,
        "precio_ref": 8799,
        "costo_total_ref": 87990,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6696518751",
        "desc": "16UM6518 ALMOHADA DE VIAJE",
        "stock": 0,
        "vel_ajust_mensual": 3.64,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 7,
        "precio_ref": 7039,
        "costo_total_ref": 49273,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6696515751",
        "desc": "16UM6515 ALMOHADA DE VIAJE",
        "stock": 0,
        "vel_ajust_mensual": 3.64,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 7,
        "precio_ref": 6399,
        "costo_total_ref": 44793,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6695093751",
        "desc": "34UM5093 BUFANDA SURTIDA",
        "stock": -1,
        "vel_ajust_mensual": 2.57,
        "cobertura_dias": -11.7,
        "meses_quebrados": 12,
        "compra_sugerida": 6,
        "precio_ref": 6209,
        "costo_total_ref": 37254,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6696563751",
        "desc": "16UM6563 CINTO DE DAMA",
        "stock": 0,
        "vel_ajust_mensual": 2.57,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 5,
        "precio_ref": 3679,
        "costo_total_ref": 18395,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6696565751",
        "desc": "16UM6565 CINTO DE DAMA",
        "stock": 0,
        "vel_ajust_mensual": 2.57,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 5,
        "precio_ref": 3439,
        "costo_total_ref": 17195,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6694124751",
        "desc": "34UM4124 PAÑUELO SEDA",
        "stock": 1,
        "vel_ajust_mensual": 4.18,
        "cobertura_dias": 7.2,
        "meses_quebrados": 4,
        "compra_sugerida": 7,
        "precio_ref": 2399,
        "costo_total_ref": 16793,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6696572751",
        "desc": "16UM6572 CINTO DE DAMA",
        "stock": 0,
        "vel_ajust_mensual": 2.57,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 5,
        "precio_ref": 2559,
        "costo_total_ref": 12795,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6692292351",
        "desc": "342292 GUANTE TEJIDO GRUESO",
        "stock": 0,
        "vel_ajust_mensual": 2.79,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 6,
        "precio_ref": 1214,
        "costo_total_ref": 7284,
        "urgencia": "CRITICO",
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
#     "proveedor": 669,
#     "empresa": "H4",
#     "fecha": "2026-04-11",
#     "renglones": [  # armar con articulo (codigo numerico), cantidad, precio
#         # {"articulo": 12345, "cantidad": 10, "precio": 1127.0},
#     ],
# }
# # insertar_pedido(pedido)  # descomentar cuando esté revisado

PROV = 669

if __name__ == "__main__":
    print("Borrador P" + str(PROV) + " — " + str(len(LINEAS)) + " lineas sugeridas")
    for l in LINEAS:
        print("  " + l["urgencia"].ljust(8) + " " + l["csr"] + " cob=" + str(l["cobertura_dias"]) + "d stk=" + str(l["stock"]) + " pedir=" + str(l["compra_sugerida"]) + " " + l["desc"])
