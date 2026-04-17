#!/usr/bin/env python3
"""
borrador_reposicion_P264_2026-04-11.py
============================================================
BORRADOR GENERADO AUTOMÁTICAMENTE POR agente-reposicion
NO EJECUTAR SIN REVISAR cantidades, precios y curvas de talle

Proveedor: 264 — GRIMOLDI (Hush Puppies/Merrell)
Empresa (routing): H4
Fecha análisis: 2026-04-11
Método: quiebre reconstruido + velocidad real + factor estacional mayo

RESUMEN:
  - 12 líneas (8 CRÍTICO, 4 URGENTE)
  - 25 unidades
  - $1,317,487 s/IVA (precio costo ref.)
"""

# =========================================================
# LÍNEAS SUGERIDAS (CSR = modelo+color, falta abrir curva talle)
# =========================================================

LINEAS = [
    {
        "csr": "2646000200",
        "desc": "HZN 660002 WINNIE NEGRO ZAPA DEP",
        "stock": 0,
        "vel_ajust_mensual": 1.02,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 2,
        "precio_ref": 62500,
        "costo_total_ref": 125000,
        "urgencia": "CRITICO",
    },
    {
        "csr": "2645500815",
        "desc": "HZYP 655008 COMPETITION BEIGE ZAPA DEP",
        "stock": 0,
        "vel_ajust_mensual": 1.02,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 2,
        "precio_ref": 60000,
        "costo_total_ref": 120000,
        "urgencia": "CRITICO",
    },
    {
        "csr": "2645510800",
        "desc": "HZN 655108 COMPETITION NEGRO ZAPA DEP",
        "stock": 0,
        "vel_ajust_mensual": 1.02,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 2,
        "precio_ref": 60000,
        "costo_total_ref": 120000,
        "urgencia": "CRITICO",
    },
    {
        "csr": "2645520206",
        "desc": "HZQ 655002 WINNIE ZAPA DEP ACORD",
        "stock": 0,
        "vel_ajust_mensual": 1.02,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 2,
        "precio_ref": 55000,
        "costo_total_ref": 110000,
        "urgencia": "CRITICO",
    },
    {
        "csr": "2645501615",
        "desc": "HZY 655016 PARK BEIGE ZAPA TREKK",
        "stock": 0,
        "vel_ajust_mensual": 1.02,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 2,
        "precio_ref": 55000,
        "costo_total_ref": 110000,
        "urgencia": "CRITICO",
    },
    {
        "csr": "2646452600",
        "desc": "HZN 645261 AVILA NEGRO ZAPA URB",
        "stock": 0,
        "vel_ajust_mensual": 1.02,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 2,
        "precio_ref": 52500,
        "costo_total_ref": 105000,
        "urgencia": "CRITICO",
    },
    {
        "csr": "2645535100",
        "desc": "HZNP655351 SENSE NEGRO ZAPA DEP",
        "stock": 0,
        "vel_ajust_mensual": 1.02,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 2,
        "precio_ref": 49500,
        "costo_total_ref": 99000,
        "urgencia": "CRITICO",
    },
    {
        "csr": "2646017228",
        "desc": "CSE 660172 NODA CELESTE SANDALIA NAUTICA",
        "stock": 0,
        "vel_ajust_mensual": 1.02,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 2,
        "precio_ref": 47500,
        "costo_total_ref": 95000,
        "urgencia": "CRITICO",
    },
    {
        "csr": "2646440919",
        "desc": "HJY 640409 MISHA 2.0 ROSA/ORO PANCHA",
        "stock": 2,
        "vel_ajust_mensual": 3.14,
        "cobertura_dias": 19.1,
        "meses_quebrados": 7,
        "compra_sugerida": 4,
        "precio_ref": 57500,
        "costo_total_ref": 230000,
        "urgencia": "URGENTE",
    },
    {
        "csr": "2645502002",
        "desc": "HZAP55020 BENTON AZUL ZAPA TREKK",
        "stock": 1,
        "vel_ajust_mensual": 1.67,
        "cobertura_dias": 18.0,
        "meses_quebrados": 1,
        "compra_sugerida": 2,
        "precio_ref": 36586,
        "costo_total_ref": 73172,
        "urgencia": "URGENTE",
    },
    {
        "csr": "2645502800",
        "desc": "HXAP55028 PIPA NEGRO ZAPA ACORD",
        "stock": 1,
        "vel_ajust_mensual": 1.35,
        "cobertura_dias": 22.2,
        "meses_quebrados": 1,
        "compra_sugerida": 2,
        "precio_ref": 36586,
        "costo_total_ref": 73172,
        "urgencia": "URGENTE",
    },
    {
        "csr": "2646351300",
        "desc": "HZN 650234 BLED NEGRO ZAPA DEP",
        "stock": 1,
        "vel_ajust_mensual": 1.24,
        "cobertura_dias": 24.3,
        "meses_quebrados": 0,
        "compra_sugerida": 1,
        "precio_ref": 57143,
        "costo_total_ref": 57143,
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
#     "proveedor": 264,
#     "empresa": "H4",
#     "fecha": "2026-04-11",
#     "renglones": [  # armar con articulo (codigo numerico), cantidad, precio
#         # {"articulo": 12345, "cantidad": 10, "precio": 1127.0},
#     ],
# }
# # insertar_pedido(pedido)  # descomentar cuando esté revisado

PROV = 264

if __name__ == "__main__":
    print("Borrador P" + str(PROV) + " — " + str(len(LINEAS)) + " lineas sugeridas")
    for l in LINEAS:
        print("  " + l["urgencia"].ljust(8) + " " + l["csr"] + " cob=" + str(l["cobertura_dias"]) + "d stk=" + str(l["stock"]) + " pedir=" + str(l["compra_sugerida"]) + " " + l["desc"])
