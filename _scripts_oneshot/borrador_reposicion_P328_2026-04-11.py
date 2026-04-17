#!/usr/bin/env python3
"""
borrador_reposicion_P328_2026-04-11.py
============================================================
BORRADOR GENERADO AUTOMÁTICAMENTE POR agente-reposicion
NO EJECUTAR SIN REVISAR cantidades, precios y curvas de talle

Proveedor: 328 — ALMACEN DE MODA (accesorios)
Empresa (routing): CALZALINDO
Fecha análisis: 2026-04-11
Método: quiebre reconstruido + velocidad real + factor estacional mayo

RESUMEN:
  - 4 líneas (3 CRÍTICO, 1 URGENTE)
  - 45 unidades
  - $144,982 s/IVA (precio costo ref.)
"""

# =========================================================
# LÍNEAS SUGERIDAS (CSR = modelo+color, falta abrir curva talle)
# =========================================================

LINEAS = [
    {
        "csr": "328PROPO11",
        "desc": "PRODUCTO EN PROMO x7MIL",
        "stock": 0,
        "vel_ajust_mensual": 5.6,
        "cobertura_dias": 0.0,
        "meses_quebrados": 1,
        "compra_sugerida": 11,
        "precio_ref": 11000,
        "costo_total_ref": 121000,
        "urgencia": "CRITICO",
    },
    {
        "csr": "990CAPOK51",
        "desc": "CARTAS POKEMON",
        "stock": 0,
        "vel_ajust_mensual": 12.07,
        "cobertura_dias": 0.0,
        "meses_quebrados": 9,
        "compra_sugerida": 24,
        "precio_ref": 500,
        "costo_total_ref": 12000,
        "urgencia": "CRITICO",
    },
    {
        "csr": "3280602000",
        "desc": "MEDIA MARRON CAPIBARA",
        "stock": 0,
        "vel_ajust_mensual": 3.02,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 6,
        "precio_ref": 1275,
        "costo_total_ref": 7650,
        "urgencia": "CRITICO",
    },
    {
        "csr": "328WD10000",
        "desc": "MEDIA BLANCA CAPIBARA",
        "stock": 2,
        "vel_ajust_mensual": 2.98,
        "cobertura_dias": 20.1,
        "meses_quebrados": 3,
        "compra_sugerida": 4,
        "precio_ref": 1083,
        "costo_total_ref": 4332,
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
#     "proveedor": 328,
#     "empresa": "CALZALINDO",
#     "fecha": "2026-04-11",
#     "renglones": [  # armar con articulo (codigo numerico), cantidad, precio
#         # {"articulo": 12345, "cantidad": 10, "precio": 1127.0},
#     ],
# }
# # insertar_pedido(pedido)  # descomentar cuando esté revisado

PROV = 328

if __name__ == "__main__":
    print("Borrador P" + str(PROV) + " — " + str(len(LINEAS)) + " lineas sugeridas")
    for l in LINEAS:
        print("  " + l["urgencia"].ljust(8) + " " + l["csr"] + " cob=" + str(l["cobertura_dias"]) + "d stk=" + str(l["stock"]) + " pedir=" + str(l["compra_sugerida"]) + " " + l["desc"])
