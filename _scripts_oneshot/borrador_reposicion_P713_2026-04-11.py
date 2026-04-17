#!/usr/bin/env python3
"""
borrador_reposicion_P713_2026-04-11.py
============================================================
BORRADOR GENERADO AUTOMÁTICAMENTE POR agente-reposicion
NO EJECUTAR SIN REVISAR cantidades, precios y curvas de talle

Proveedor: 713 — DISTRINANDO MODA (Picadilly)
Empresa (routing): H4
Fecha análisis: 2026-04-11
Método: quiebre reconstruido + velocidad real + factor estacional mayo

RESUMEN:
  - 12 líneas (8 CRÍTICO, 4 URGENTE)
  - 97 unidades
  - $1,636,013 s/IVA (precio costo ref.)
"""

# =========================================================
# LÍNEAS SUGERIDAS (CSR = modelo+color, falta abrir curva talle)
# =========================================================

LINEAS = [
    {
        "csr": "713174CN12",
        "desc": "1174 CAFE/NEGRO ZAPA TREKKING",
        "stock": 1,
        "vel_ajust_mensual": 12.3,
        "cobertura_dias": 2.4,
        "meses_quebrados": 11,
        "compra_sugerida": 24,
        "precio_ref": 9999,
        "costo_total_ref": 239976,
        "urgencia": "CRITICO",
    },
    {
        "csr": "7132024500",
        "desc": "20245-09 NEGRO SAND TACO SEP",
        "stock": 0,
        "vel_ajust_mensual": 3.6,
        "cobertura_dias": 0.0,
        "meses_quebrados": 9,
        "compra_sugerida": 7,
        "precio_ref": 27499,
        "costo_total_ref": 192493,
        "urgencia": "CRITICO",
    },
    {
        "csr": "7132111511",
        "desc": "121-1-15 MARRON SANDALIA BAJA",
        "stock": 1,
        "vel_ajust_mensual": 2.5,
        "cobertura_dias": 12.0,
        "meses_quebrados": 9,
        "compra_sugerida": 4,
        "precio_ref": 34999,
        "costo_total_ref": 139996,
        "urgencia": "CRITICO",
    },
    {
        "csr": "7131211100",
        "desc": "0121-1-1 NEGRO SANDALIA BAJA",
        "stock": -1,
        "vel_ajust_mensual": 0.62,
        "cobertura_dias": -48.0,
        "meses_quebrados": 12,
        "compra_sugerida": 2,
        "precio_ref": 34999,
        "costo_total_ref": 69998,
        "urgencia": "CRITICO",
    },
    {
        "csr": "7136217001",
        "desc": "5262-1-70 PERLA SANDALIA",
        "stock": 0,
        "vel_ajust_mensual": 0.62,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 1,
        "precio_ref": 34999,
        "costo_total_ref": 34999,
        "urgencia": "CRITICO",
    },
    {
        "csr": "7131510115",
        "desc": "0015-10-1 BEIGE SANDALIA",
        "stock": 0,
        "vel_ajust_mensual": 0.6,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 1,
        "precio_ref": 34999,
        "costo_total_ref": 34999,
        "urgencia": "CRITICO",
    },
    {
        "csr": "7132450901",
        "desc": "20245-09 BLANCO SANDALIA T/SEP",
        "stock": 0,
        "vel_ajust_mensual": 0.7,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 1,
        "precio_ref": 27499,
        "costo_total_ref": 27499,
        "urgencia": "CRITICO",
    },
    {
        "csr": "7132727500",
        "desc": "27275 HOY SLIDE NEGRO CHINELA",
        "stock": 0,
        "vel_ajust_mensual": 0.6,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 1,
        "precio_ref": 7649,
        "costo_total_ref": 7649,
        "urgencia": "CRITICO",
    },
    {
        "csr": "713174NR00",
        "desc": "1174 NEGRO/ROJO ZAPA TREKKING",
        "stock": 33,
        "vel_ajust_mensual": 36.6,
        "cobertura_dias": 27.0,
        "meses_quebrados": 11,
        "compra_sugerida": 40,
        "precio_ref": 9999,
        "costo_total_ref": 399960,
        "urgencia": "URGENTE",
    },
    {
        "csr": "7131211515",
        "desc": "121-1-5 BEIGE SANDALIA BAJA",
        "stock": 4,
        "vel_ajust_mensual": 6.9,
        "cobertura_dias": 17.4,
        "meses_quebrados": 8,
        "compra_sugerida": 10,
        "precio_ref": 34999,
        "costo_total_ref": 349990,
        "urgencia": "URGENTE",
    },
    {
        "csr": "7138003325",
        "desc": "238003-3 NUDE ZUECO",
        "stock": 2,
        "vel_ajust_mensual": 2.82,
        "cobertura_dias": 21.3,
        "meses_quebrados": 7,
        "compra_sugerida": 4,
        "precio_ref": 19169,
        "costo_total_ref": 76676,
        "urgencia": "URGENTE",
    },
    {
        "csr": "7135710310",
        "desc": "571003 NEGRO/NEGRO SANDALIA",
        "stock": 1,
        "vel_ajust_mensual": 1.75,
        "cobertura_dias": 17.1,
        "meses_quebrados": 6,
        "compra_sugerida": 2,
        "precio_ref": 30889,
        "costo_total_ref": 61778,
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
#     "proveedor": 713,
#     "empresa": "H4",
#     "fecha": "2026-04-11",
#     "renglones": [  # armar con articulo (codigo numerico), cantidad, precio
#         # {"articulo": 12345, "cantidad": 10, "precio": 1127.0},
#     ],
# }
# # insertar_pedido(pedido)  # descomentar cuando esté revisado

PROV = 713

if __name__ == "__main__":
    print("Borrador P" + str(PROV) + " — " + str(len(LINEAS)) + " lineas sugeridas")
    for l in LINEAS:
        print("  " + l["urgencia"].ljust(8) + " " + l["csr"] + " cob=" + str(l["cobertura_dias"]) + "d stk=" + str(l["stock"]) + " pedir=" + str(l["compra_sugerida"]) + " " + l["desc"])
