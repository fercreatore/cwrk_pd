#!/usr/bin/env python3
"""
borrador_reposicion_P656_2026-04-11.py
============================================================
BORRADOR GENERADO AUTOMÁTICAMENTE POR agente-reposicion
NO EJECUTAR SIN REVISAR cantidades, precios y curvas de talle

Proveedor: 656 — DISTRINANDO DEP (Reebok)
Empresa (routing): H4
Fecha análisis: 2026-04-11
Método: quiebre reconstruido + velocidad real + factor estacional mayo

RESUMEN:
  - 7 líneas (5 CRÍTICO, 2 URGENTE)
  - 79 unidades
  - $2,581,024 s/IVA (precio costo ref.)
"""

# =========================================================
# LÍNEAS SUGERIDAS (CSR = modelo+color, falta abrir curva talle)
# =========================================================

LINEAS = [
    {
        "csr": "656G003800",
        "desc": "ENERGEN RUN 3 NEGRO/BLANCO/GRIS",
        "stock": 1,
        "vel_ajust_mensual": 14.48,
        "cobertura_dias": 2.1,
        "meses_quebrados": 11,
        "compra_sugerida": 28,
        "precio_ref": 31991,
        "costo_total_ref": 895748,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6562543402",
        "desc": "C205434 CROCBAND PLATFORM AZUL/BLANCO",
        "stock": 1,
        "vel_ajust_mensual": 3.88,
        "cobertura_dias": 7.7,
        "meses_quebrados": 3,
        "compra_sugerida": 7,
        "precio_ref": 31990,
        "costo_total_ref": 223930,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6562543413",
        "desc": "C205434 CROCBAND PLATFORM GRIS/ROSA",
        "stock": 0,
        "vel_ajust_mensual": 2.0,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 4,
        "precio_ref": 31990,
        "costo_total_ref": 127960,
        "urgencia": "CRITICO",
    },
    {
        "csr": "656NANX310",
        "desc": "NANO X3 NEGRO/BLANCO ZAPA CROSSFIT",
        "stock": 0,
        "vel_ajust_mensual": 1.33,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 3,
        "precio_ref": 34657,
        "costo_total_ref": 103971,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6562297215",
        "desc": "C202972 SANTA CRUZ CLEAN CUT KHAKI",
        "stock": 0,
        "vel_ajust_mensual": 1.04,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 2,
        "precio_ref": 36203,
        "costo_total_ref": 72406,
        "urgencia": "CRITICO",
    },
    {
        "csr": "656N133813",
        "desc": "ENERGEN RUN 3 GRIS/AZUL/LIMA",
        "stock": 13,
        "vel_ajust_mensual": 16.97,
        "cobertura_dias": 23.0,
        "meses_quebrados": 11,
        "compra_sugerida": 21,
        "precio_ref": 31991,
        "costo_total_ref": 671811,
        "urgencia": "URGENTE",
    },
    {
        "csr": "656ASSIC00",
        "desc": "NANO CLASSIC CORE NEGRO/BLANCO/GRIS",
        "stock": 8,
        "vel_ajust_mensual": 10.98,
        "cobertura_dias": 21.9,
        "meses_quebrados": 11,
        "compra_sugerida": 14,
        "precio_ref": 34657,
        "costo_total_ref": 485198,
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
#     "proveedor": 656,
#     "empresa": "H4",
#     "fecha": "2026-04-11",
#     "renglones": [  # armar con articulo (codigo numerico), cantidad, precio
#         # {"articulo": 12345, "cantidad": 10, "precio": 1127.0},
#     ],
# }
# # insertar_pedido(pedido)  # descomentar cuando esté revisado

PROV = 656

if __name__ == "__main__":
    print("Borrador P" + str(PROV) + " — " + str(len(LINEAS)) + " lineas sugeridas")
    for l in LINEAS:
        print("  " + l["urgencia"].ljust(8) + " " + l["csr"] + " cob=" + str(l["cobertura_dias"]) + "d stk=" + str(l["stock"]) + " pedir=" + str(l["compra_sugerida"]) + " " + l["desc"])
