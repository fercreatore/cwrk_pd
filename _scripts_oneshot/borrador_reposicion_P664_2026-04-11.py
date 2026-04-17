#!/usr/bin/env python3
"""
borrador_reposicion_P664_2026-04-11.py
============================================================
BORRADOR GENERADO AUTOMÁTICAMENTE POR agente-reposicion
NO EJECUTAR SIN REVISAR cantidades, precios y curvas de talle

Proveedor: 664 — RIMON CASSIS
Empresa (routing): H4
Fecha análisis: 2026-04-11
Método: quiebre reconstruido + velocidad real + factor estacional mayo

RESUMEN:
  - 7 líneas (4 CRÍTICO, 3 URGENTE)
  - 17 unidades
  - $255,138 s/IVA (precio costo ref.)
"""

# =========================================================
# LÍNEAS SUGERIDAS (CSR = modelo+color, falta abrir curva talle)
# =========================================================

LINEAS = [
    {
        "csr": "6641883315",
        "desc": "18833 GREICE SOFT PAPETE HUESO SANDALIA",
        "stock": 0,
        "vel_ajust_mensual": 0.3,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 1,
        "precio_ref": 26990,
        "costo_total_ref": 26990,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6641253100",
        "desc": "12531 LYON THONG AD NEGRO/CARAMELO",
        "stock": 0,
        "vel_ajust_mensual": 0.6,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 1,
        "precio_ref": 16990,
        "costo_total_ref": 16990,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6641253102",
        "desc": "12531 LYON THONG AD AZUL OJOTA",
        "stock": 0,
        "vel_ajust_mensual": 0.3,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 1,
        "precio_ref": 16990,
        "costo_total_ref": 16990,
        "urgencia": "CRITICO",
    },
    {
        "csr": "664ANGRA19",
        "desc": "ANGRA ROSA CHINELA FAJA",
        "stock": 0,
        "vel_ajust_mensual": 0.3,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 1,
        "precio_ref": 16945,
        "costo_total_ref": 16945,
        "urgencia": "CRITICO",
    },
    {
        "csr": "7222973202",
        "desc": "NASSAU AZUL/GRIS/VERDE OJOTA",
        "stock": 2,
        "vel_ajust_mensual": 2.85,
        "cobertura_dias": 21.1,
        "meses_quebrados": 6,
        "compra_sugerida": 4,
        "precio_ref": 16216,
        "costo_total_ref": 64864,
        "urgencia": "URGENTE",
    },
    {
        "csr": "7222973213",
        "desc": "NASSAU GRIS/NEGRO OJOTA",
        "stock": 2,
        "vel_ajust_mensual": 2.83,
        "cobertura_dias": 21.2,
        "meses_quebrados": 5,
        "compra_sugerida": 4,
        "precio_ref": 16216,
        "costo_total_ref": 64864,
        "urgencia": "URGENTE",
    },
    {
        "csr": "6648325800",
        "desc": "83258 SLIDE UNISEX NEGRO CHINELA",
        "stock": 3,
        "vel_ajust_mensual": 3.82,
        "cobertura_dias": 23.5,
        "meses_quebrados": 8,
        "compra_sugerida": 5,
        "precio_ref": 9499,
        "costo_total_ref": 47495,
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
#     "proveedor": 664,
#     "empresa": "H4",
#     "fecha": "2026-04-11",
#     "renglones": [  # armar con articulo (codigo numerico), cantidad, precio
#         # {"articulo": 12345, "cantidad": 10, "precio": 1127.0},
#     ],
# }
# # insertar_pedido(pedido)  # descomentar cuando esté revisado

PROV = 664

if __name__ == "__main__":
    print("Borrador P" + str(PROV) + " — " + str(len(LINEAS)) + " lineas sugeridas")
    for l in LINEAS:
        print("  " + l["urgencia"].ljust(8) + " " + l["csr"] + " cob=" + str(l["cobertura_dias"]) + "d stk=" + str(l["stock"]) + " pedir=" + str(l["compra_sugerida"]) + " " + l["desc"])
