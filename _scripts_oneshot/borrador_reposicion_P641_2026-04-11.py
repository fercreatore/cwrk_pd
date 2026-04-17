#!/usr/bin/env python3
"""
borrador_reposicion_P641_2026-04-11.py
============================================================
BORRADOR GENERADO AUTOMÁTICAMENTE POR agente-reposicion
NO EJECUTAR SIN REVISAR cantidades, precios y curvas de talle

Proveedor: 641 — FLOYD MEDIAS
Empresa (routing): H4
Fecha análisis: 2026-04-11
Método: quiebre reconstruido + velocidad real + factor estacional mayo

RESUMEN:
  - 5 líneas (3 CRÍTICO, 2 URGENTE)
  - 383 unidades
  - $428,857 s/IVA (precio costo ref.)
"""

# =========================================================
# LÍNEAS SUGERIDAS (CSR = modelo+color, falta abrir curva talle)
# =========================================================

LINEAS = [
    {
        "csr": "6416100051",
        "desc": "61 SURTIDOS SOQUETE CORTO ESTAMPADO",
        "stock": 35,
        "vel_ajust_mensual": 92.31,
        "cobertura_dias": 11.4,
        "meses_quebrados": 10,
        "compra_sugerida": 150,
        "precio_ref": 1021,
        "costo_total_ref": 153150,
        "urgencia": "CRITICO",
    },
    {
        "csr": "641CL09051",
        "desc": "CL09 C/S MEDIA VESTIR LISA",
        "stock": 23,
        "vel_ajust_mensual": 70.84,
        "cobertura_dias": 9.7,
        "meses_quebrados": 11,
        "compra_sugerida": 119,
        "precio_ref": 1224,
        "costo_total_ref": 145656,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6411412051",
        "desc": "1412 C/S SOQUETE TOBILLERA HOMBRE",
        "stock": -1,
        "vel_ajust_mensual": 15.03,
        "cobertura_dias": -2.0,
        "meses_quebrados": 12,
        "compra_sugerida": 31,
        "precio_ref": 1295,
        "costo_total_ref": 40145,
        "urgencia": "CRITICO",
    },
    {
        "csr": "641MJ08051",
        "desc": "MJ8 C/S SOQUETE DAMA LISO",
        "stock": 42,
        "vel_ajust_mensual": 45.17,
        "cobertura_dias": 27.9,
        "meses_quebrados": 12,
        "compra_sugerida": 48,
        "precio_ref": 1017,
        "costo_total_ref": 48816,
        "urgencia": "URGENTE",
    },
    {
        "csr": "6411414051",
        "desc": "1414 C/S SOQUETE CORTO LISO",
        "stock": 30,
        "vel_ajust_mensual": 32.38,
        "cobertura_dias": 27.8,
        "meses_quebrados": 12,
        "compra_sugerida": 35,
        "precio_ref": 1174,
        "costo_total_ref": 41090,
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
#     "proveedor": 641,
#     "empresa": "H4",
#     "fecha": "2026-04-11",
#     "renglones": [  # armar con articulo (codigo numerico), cantidad, precio
#         # {"articulo": 12345, "cantidad": 10, "precio": 1127.0},
#     ],
# }
# # insertar_pedido(pedido)  # descomentar cuando esté revisado

PROV = 641

if __name__ == "__main__":
    print("Borrador P" + str(PROV) + " — " + str(len(LINEAS)) + " lineas sugeridas")
    for l in LINEAS:
        print("  " + l["urgencia"].ljust(8) + " " + l["csr"] + " cob=" + str(l["cobertura_dias"]) + "d stk=" + str(l["stock"]) + " pedir=" + str(l["compra_sugerida"]) + " " + l["desc"])
