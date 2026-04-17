#!/usr/bin/env python3
"""
borrador_reposicion_P311_2026-04-11.py
============================================================
BORRADOR GENERADO AUTOMÁTICAMENTE POR agente-reposicion
NO EJECUTAR SIN REVISAR cantidades, precios y curvas de talle

Proveedor: 311 — ROFREVE/SOFT
Empresa (routing): CALZALINDO
Fecha análisis: 2026-04-11
Método: quiebre reconstruido + velocidad real + factor estacional mayo

RESUMEN:
  - 8 líneas (6 CRÍTICO, 2 URGENTE)
  - 73 unidades
  - $862,894 s/IVA (precio costo ref.)
"""

# =========================================================
# LÍNEAS SUGERIDAS (CSR = modelo+color, falta abrir curva talle)
# =========================================================

LINEAS = [
    {
        "csr": "3110SF6000",
        "desc": "SF60 NEGRO OJOTA MODA DET GLITTER",
        "stock": 3,
        "vel_ajust_mensual": 10.8,
        "cobertura_dias": 8.3,
        "meses_quebrados": 7,
        "compra_sugerida": 19,
        "precio_ref": 11054,
        "costo_total_ref": 210026,
        "urgencia": "CRITICO",
    },
    {
        "csr": "3110SF6020",
        "desc": "SF60 PLATA OJOTA MODA DET GLITTER",
        "stock": 2,
        "vel_ajust_mensual": 8.1,
        "cobertura_dias": 7.4,
        "meses_quebrados": 7,
        "compra_sugerida": 14,
        "precio_ref": 11054,
        "costo_total_ref": 154756,
        "urgencia": "CRITICO",
    },
    {
        "csr": "3110SF6012",
        "desc": "SF60 BLANCO OJOTA MODA DET GLITTER",
        "stock": 4,
        "vel_ajust_mensual": 8.73,
        "cobertura_dias": 13.7,
        "meses_quebrados": 7,
        "compra_sugerida": 13,
        "precio_ref": 11054,
        "costo_total_ref": 143702,
        "urgencia": "CRITICO",
    },
    {
        "csr": "3112720014",
        "desc": "RA27200 NEGRO/GRIS/VERDE ZAPA DEP",
        "stock": 0,
        "vel_ajust_mensual": 1.59,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 3,
        "precio_ref": 16726,
        "costo_total_ref": 50178,
        "urgencia": "CRITICO",
    },
    {
        "csr": "3112720000",
        "desc": "RA27200 NEGRO/NEGRO/ROJO ZAPA DEP",
        "stock": 0,
        "vel_ajust_mensual": 1.59,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 3,
        "precio_ref": 16726,
        "costo_total_ref": 50178,
        "urgencia": "CRITICO",
    },
    {
        "csr": "3112720009",
        "desc": "RA27200 NEGRO/AZUL/NARANJA ZAPA DEP",
        "stock": 0,
        "vel_ajust_mensual": 1.59,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 3,
        "precio_ref": 16726,
        "costo_total_ref": 50178,
        "urgencia": "CRITICO",
    },
    {
        "csr": "311SB08006",
        "desc": "SB080 INDIGO OJOTA CONFORT",
        "stock": 4,
        "vel_ajust_mensual": 6.09,
        "cobertura_dias": 19.7,
        "meses_quebrados": 6,
        "compra_sugerida": 8,
        "precio_ref": 13472,
        "costo_total_ref": 107776,
        "urgencia": "URGENTE",
    },
    {
        "csr": "311SB09002",
        "desc": "SB090 AZUL/CELESTE OJOTA CONFORT",
        "stock": 5,
        "vel_ajust_mensual": 7.41,
        "cobertura_dias": 20.2,
        "meses_quebrados": 9,
        "compra_sugerida": 10,
        "precio_ref": 9610,
        "costo_total_ref": 96100,
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
#     "proveedor": 311,
#     "empresa": "CALZALINDO",
#     "fecha": "2026-04-11",
#     "renglones": [  # armar con articulo (codigo numerico), cantidad, precio
#         # {"articulo": 12345, "cantidad": 10, "precio": 1127.0},
#     ],
# }
# # insertar_pedido(pedido)  # descomentar cuando esté revisado

PROV = 311

if __name__ == "__main__":
    print("Borrador P" + str(PROV) + " — " + str(len(LINEAS)) + " lineas sugeridas")
    for l in LINEAS:
        print("  " + l["urgencia"].ljust(8) + " " + l["csr"] + " cob=" + str(l["cobertura_dias"]) + "d stk=" + str(l["stock"]) + " pedir=" + str(l["compra_sugerida"]) + " " + l["desc"])
