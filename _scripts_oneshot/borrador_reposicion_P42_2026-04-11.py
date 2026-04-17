#!/usr/bin/env python3
"""
borrador_reposicion_P42_2026-04-11.py
============================================================
BORRADOR GENERADO AUTOMÁTICAMENTE POR agente-reposicion
NO EJECUTAR SIN REVISAR cantidades, precios y curvas de talle

Proveedor: 42 — LESEDIFE (Unicross/Amayra)
Empresa (routing): CALZALINDO
Fecha análisis: 2026-04-11
Método: quiebre reconstruido + velocidad real + factor estacional mayo

RESUMEN:
  - 14 líneas (12 CRÍTICO, 2 URGENTE)
  - 100 unidades
  - $596,688 s/IVA (precio costo ref.)
"""

# =========================================================
# LÍNEAS SUGERIDAS (CSR = modelo+color, falta abrir curva talle)
# =========================================================

LINEAS = [
    {
        "csr": "0428140212",
        "desc": "68.1402 MOCHILA INFLUENCER 17' PRINT",
        "stock": -3,
        "vel_ajust_mensual": 6.76,
        "cobertura_dias": -13.3,
        "meses_quebrados": 8,
        "compra_sugerida": 17,
        "precio_ref": 8451,
        "costo_total_ref": 143667,
        "urgencia": "CRITICO",
    },
    {
        "csr": "0426250600",
        "desc": "62.506 CINTO UNICROSS DENIM",
        "stock": 0,
        "vel_ajust_mensual": 5.91,
        "cobertura_dias": 0.0,
        "meses_quebrados": 9,
        "compra_sugerida": 12,
        "precio_ref": 5990,
        "costo_total_ref": 71880,
        "urgencia": "CRITICO",
    },
    {
        "csr": "042B112651",
        "desc": "62.B1126 BILLETERA UNICROSS C/DIVISIONES COMB",
        "stock": 0,
        "vel_ajust_mensual": 6.08,
        "cobertura_dias": 0.0,
        "meses_quebrados": 7,
        "compra_sugerida": 12,
        "precio_ref": 5841,
        "costo_total_ref": 70092,
        "urgencia": "CRITICO",
    },
    {
        "csr": "042B112551",
        "desc": "62.B1125 BILLETERA C/DIVISION UNICROSS",
        "stock": 0,
        "vel_ajust_mensual": 5.07,
        "cobertura_dias": 0.0,
        "meses_quebrados": 8,
        "compra_sugerida": 10,
        "precio_ref": 5841,
        "costo_total_ref": 58410,
        "urgencia": "CRITICO",
    },
    {
        "csr": "0427180951",
        "desc": "67.X1809 BOTELLA TERMICA AMAYRA 500ML",
        "stock": 0,
        "vel_ajust_mensual": 1.62,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 3,
        "precio_ref": 10971,
        "costo_total_ref": 32913,
        "urgencia": "CRITICO",
    },
    {
        "csr": "0427181151",
        "desc": "67.X1811 BOTELLA TERMICA AMAYRA 500ML",
        "stock": 0,
        "vel_ajust_mensual": 1.69,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 3,
        "precio_ref": 9801,
        "costo_total_ref": 29403,
        "urgencia": "CRITICO",
    },
    {
        "csr": "042H721651",
        "desc": "67.H7216.1 BROCHE PARA PELO AMAYRA",
        "stock": 0,
        "vel_ajust_mensual": 5.91,
        "cobertura_dias": 0.0,
        "meses_quebrados": 11,
        "compra_sugerida": 12,
        "precio_ref": 2331,
        "costo_total_ref": 27972,
        "urgencia": "CRITICO",
    },
    {
        "csr": "042H720851",
        "desc": "67.H7208.1 BROCHE PARA PELO AMAYRA",
        "stock": 0,
        "vel_ajust_mensual": 2.96,
        "cobertura_dias": 0.0,
        "meses_quebrados": 10,
        "compra_sugerida": 6,
        "precio_ref": 2421,
        "costo_total_ref": 14526,
        "urgencia": "CRITICO",
    },
    {
        "csr": "0426752400",
        "desc": "67.524 CINTO MUJER AMAYRA LISO",
        "stock": 0,
        "vel_ajust_mensual": 1.69,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 3,
        "precio_ref": 4581,
        "costo_total_ref": 13743,
        "urgencia": "CRITICO",
    },
    {
        "csr": "0422622651",
        "desc": "62.T6226 SURTIDOS GUANTES MOTO UNICROSS",
        "stock": 0,
        "vel_ajust_mensual": 1.69,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 3,
        "precio_ref": 4041,
        "costo_total_ref": 12123,
        "urgencia": "CRITICO",
    },
    {
        "csr": "0429645751",
        "desc": "67.B964 BILLETERA CH 2 CIERRE DET COST",
        "stock": 0,
        "vel_ajust_mensual": 1.55,
        "cobertura_dias": 0.0,
        "meses_quebrados": 12,
        "compra_sugerida": 3,
        "precio_ref": 3951,
        "costo_total_ref": 11853,
        "urgencia": "CRITICO",
    },
    {
        "csr": "042H720451",
        "desc": "67.H7204.1 BROCHE PARA PELO AMAYRA",
        "stock": 0,
        "vel_ajust_mensual": 0.84,
        "cobertura_dias": 0.0,
        "meses_quebrados": 11,
        "compra_sugerida": 2,
        "precio_ref": 2421,
        "costo_total_ref": 4842,
        "urgencia": "CRITICO",
    },
    {
        "csr": "0420600351",
        "desc": "91.0600003 CARPETA N3 GAME START C/CIERRE",
        "stock": 6,
        "vel_ajust_mensual": 8.44,
        "cobertura_dias": 21.3,
        "meses_quebrados": 9,
        "compra_sugerida": 11,
        "precio_ref": 8271,
        "costo_total_ref": 90981,
        "urgencia": "URGENTE",
    },
    {
        "csr": "042P603551",
        "desc": "67.P6035 PARAGUAS CORTO MANUAL AMAYRA 21'",
        "stock": 2,
        "vel_ajust_mensual": 2.39,
        "cobertura_dias": 25.1,
        "meses_quebrados": 0,
        "compra_sugerida": 3,
        "precio_ref": 4761,
        "costo_total_ref": 14283,
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
#     "proveedor": 42,
#     "empresa": "CALZALINDO",
#     "fecha": "2026-04-11",
#     "renglones": [  # armar con articulo (codigo numerico), cantidad, precio
#         # {"articulo": 12345, "cantidad": 10, "precio": 1127.0},
#     ],
# }
# # insertar_pedido(pedido)  # descomentar cuando esté revisado

PROV = 42

if __name__ == "__main__":
    print("Borrador P" + str(PROV) + " — " + str(len(LINEAS)) + " lineas sugeridas")
    for l in LINEAS:
        print("  " + l["urgencia"].ljust(8) + " " + l["csr"] + " cob=" + str(l["cobertura_dias"]) + "d stk=" + str(l["stock"]) + " pedir=" + str(l["compra_sugerida"]) + " " + l["desc"])
