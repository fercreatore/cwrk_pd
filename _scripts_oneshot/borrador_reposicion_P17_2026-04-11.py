#!/usr/bin/env python3
"""
borrador_reposicion_P17_2026-04-11.py
============================================================
BORRADOR GENERADO AUTOMÁTICAMENTE POR agente-reposicion
NO EJECUTAR SIN REVISAR cantidades, precios y curvas de talle

Proveedor: 17 — GO BY CZL (marca propia)
Empresa (routing): CALZALINDO
Fecha análisis: 2026-04-11
Método: quiebre reconstruido + velocidad real + factor estacional mayo

RESUMEN:
  - 6 líneas (2 CRÍTICO, 4 URGENTE)
  - 128 unidades
  - $2,011,054 s/IVA (precio costo ref.)
"""

# =========================================================
# LÍNEAS SUGERIDAS (CSR = modelo+color, falta abrir curva talle)
# =========================================================

LINEAS = [
    {
        "csr": "017WS06601",
        "desc": "WS066 HIELO/PLATA ZAPA DEP AC FITNESS",
        "stock": 0,
        "vel_ajust_mensual": 1.81,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 4,
        "precio_ref": 29999,
        "costo_total_ref": 119996,
        "urgencia": "CRITICO",
    },
    {
        "csr": "0171150513",
        "desc": "505 GRIS PANTALON COLEGIAL C/BOLSILLOS",
        "stock": 0,
        "vel_ajust_mensual": 2.87,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 6,
        "precio_ref": 1686,
        "costo_total_ref": 10116,
        "urgencia": "CRITICO",
    },
    {
        "csr": "0171402651",
        "desc": "SDL4026 OXFORD MOCHILA 2 CIERRES P/NOTEBOOK 18'",
        "stock": 29,
        "vel_ajust_mensual": 37.6,
        "cobertura_dias": 23.1,
        "meses_quebrados": 8,
        "compra_sugerida": 46,
        "precio_ref": 22977,
        "costo_total_ref": 1056942,
        "urgencia": "URGENTE",
    },
    {
        "csr": "4570026022",
        "desc": "260PU GALLETITA ZAPATO FOLCLORE CLASICO",
        "stock": 8,
        "vel_ajust_mensual": 13.82,
        "cobertura_dias": 17.4,
        "meses_quebrados": 12,
        "compra_sugerida": 20,
        "precio_ref": 23700,
        "costo_total_ref": 474000,
        "urgencia": "URGENTE",
    },
    {
        "csr": "017DANCE01",
        "desc": "GO DANCE BLANCO/BLANCO ZAPA DANZA",
        "stock": 3,
        "vel_ajust_mensual": 5.51,
        "cobertura_dias": 16.3,
        "meses_quebrados": 0,
        "compra_sugerida": 8,
        "precio_ref": 30000,
        "costo_total_ref": 240000,
        "urgencia": "URGENTE",
    },
    {
        "csr": "017CMFLL51",
        "desc": "CAMISETA $4.999 M/CORTA",
        "stock": 29,
        "vel_ajust_mensual": 36.69,
        "cobertura_dias": 23.7,
        "meses_quebrados": 10,
        "compra_sugerida": 44,
        "precio_ref": 2500,
        "costo_total_ref": 110000,
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
#     "proveedor": 17,
#     "empresa": "CALZALINDO",
#     "fecha": "2026-04-11",
#     "renglones": [  # armar con articulo (codigo numerico), cantidad, precio
#         # {"articulo": 12345, "cantidad": 10, "precio": 1127.0},
#     ],
# }
# # insertar_pedido(pedido)  # descomentar cuando esté revisado

PROV = 17

if __name__ == "__main__":
    print("Borrador P" + str(PROV) + " — " + str(len(LINEAS)) + " lineas sugeridas")
    for l in LINEAS:
        print("  " + l["urgencia"].ljust(8) + " " + l["csr"] + " cob=" + str(l["cobertura_dias"]) + "d stk=" + str(l["stock"]) + " pedir=" + str(l["compra_sugerida"]) + " " + l["desc"])
