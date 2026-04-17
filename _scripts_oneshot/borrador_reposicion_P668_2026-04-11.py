#!/usr/bin/env python3
"""
borrador_reposicion_P668_2026-04-11.py
============================================================
BORRADOR GENERADO AUTOMÁTICAMENTE POR agente-reposicion
NO EJECUTAR SIN REVISAR cantidades, precios y curvas de talle

Proveedor: 668 — ALPARGATAS/TOPPER
Empresa (routing): H4
Fecha análisis: 2026-04-11
Método: quiebre reconstruido + velocidad real + factor estacional mayo

RESUMEN:
  - 2 líneas (1 CRÍTICO, 1 URGENTE)
  - 75 unidades
  - $2,620,036 s/IVA (precio costo ref.)
"""

# =========================================================
# LÍNEAS SUGERIDAS (CSR = modelo+color, falta abrir curva talle)
# =========================================================

LINEAS = [
    {
        "csr": "6682832119",
        "desc": "28322 TIE BREAK II KIDS BLANCO/ROSA",
        "stock": 13,
        "vel_ajust_mensual": 28.33,
        "cobertura_dias": 13.8,
        "meses_quebrados": 10,
        "compra_sugerida": 44,
        "precio_ref": 30612,
        "costo_total_ref": 1346928,
        "urgencia": "CRITICO",
    },
    {
        "csr": "6682357900",
        "desc": "23579 X FORCER KIDS VELCRO",
        "stock": 20,
        "vel_ajust_mensual": 25.4,
        "cobertura_dias": 23.6,
        "meses_quebrados": 10,
        "compra_sugerida": 31,
        "precio_ref": 41068,
        "costo_total_ref": 1273108,
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
#     "proveedor": 668,
#     "empresa": "H4",
#     "fecha": "2026-04-11",
#     "renglones": [  # armar con articulo (codigo numerico), cantidad, precio
#         # {"articulo": 12345, "cantidad": 10, "precio": 1127.0},
#     ],
# }
# # insertar_pedido(pedido)  # descomentar cuando esté revisado

PROV = 668

if __name__ == "__main__":
    print("Borrador P" + str(PROV) + " — " + str(len(LINEAS)) + " lineas sugeridas")
    for l in LINEAS:
        print("  " + l["urgencia"].ljust(8) + " " + l["csr"] + " cob=" + str(l["cobertura_dias"]) + "d stk=" + str(l["stock"]) + " pedir=" + str(l["compra_sugerida"]) + " " + l["desc"])
