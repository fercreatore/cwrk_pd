#!/usr/bin/env python3
"""
borrador_pedidos_criticos_2026-03-21.py
=======================================
BORRADOR GENERADO AUTOMÁTICAMENTE — NO EJECUTAR SIN REVISAR

Pedidos urgentes detectados por el agente de reposición.
Verificar cantidades, precios y disponibilidad con el proveedor antes de insertar.
Fecha: 2026-03-21
"""

# RESUMEN DE CRÍTICOS POR PROVEEDOR:
"""
Proveedor 17 (GO by CZL): 1 modelos, ~11 unidades
  - 260PU GALLETITA ZAPATO FOLCLORE CLASICO T/SEP | stock=1 | dias=5 | pedir=11 | precio_ref=$23,000

Proveedor 311 (ROFREVE): 3 modelos, ~52 unidades
  - SF60 PLATA OJOTA MODA DET GLITTER | stock=3 | dias=9 | pedir=17 | precio_ref=$14,854
  - SF60 NEGRO OJOTA MODA DET GLITTER | stock=3 | dias=9 | pedir=17 | precio_ref=$14,739
  - SF60 BLANCO OJOTA MODA DET GLITTER | stock=4 | dias=11 | pedir=18 | precio_ref=$14,854

Proveedor 515 (SARANG TONGSANG SRL): 11 modelos, ~1512 unidades
  - 104 C/S SOQUETE KIDS T.3 | stock=2 | dias=2 | pedir=53 | precio_ref=$989
  - 022 C/S SOQUETE INVISIBLE LISO | stock=5 | dias=3 | pedir=105 | precio_ref=$1,142
  - 202 MEDIA DAMA ESTAMPA SURTIDO | stock=4 | dias=3 | pedir=71 | precio_ref=$0
  - 102L C/S SOQUETE LISO HOMBRE | stock=24 | dias=4 | pedir=306 | precio_ref=$1,128
  - 401R MEDIA 1/3 DAMA RAYADO | stock=15 | dias=6 | pedir=150 | precio_ref=$0
  - 101 C/S SOQUETE DAMA ESTAMPADO | stock=4 | dias=6 | pedir=40 | precio_ref=$1,339
  - 402L MEDIA 1/3 HOMBRE LISA | stock=21 | dias=10 | pedir=99 | precio_ref=$0
  - 102D C/S SOQUETE DEPORTIVO HOMBRE | stock=137 | dias=12 | pedir=554 | precio_ref=$1,315
  - 023 SOQUETE INVISIBLE ESTAMPADO | stock=8 | dias=12 | pedir=32 | precio_ref=$0
  - 953 SOQUETE ALTO HOMBRE LISO | stock=15 | dias=13 | pedir=56 | precio_ref=$0
  - 105 C/S SOQUETE KIDS T.4 | stock=15 | dias=15 | pedir=46 | precio_ref=$1,196

Proveedor 594 (VICBOR SRL): 1 modelos, ~8 unidades
  - SAND NEGRO ZUECO PLAYERO FAJA LISA | stock=1 | dias=7 | pedir=8 | precio_ref=$20,274

Proveedor 641 (FLOYD MEDIAS): 1 modelos, ~53 unidades
  - MJ20 MEDIA CASUAL CAÑA 1/3 ESTAMPA | stock=15 | dias=13 | pedir=53 | precio_ref=$1,206

Proveedor 656 (DISTRINANDO DEPORTES S.A.): 1 modelos, ~15 unidades
  - C205434 CROCBAND PLATFORM CLOG AZUL/BLANCO ZU | stock=1 | dias=4 | pedir=15 | precio_ref=$0

Proveedor 664 (RIMON CASSIS E HIJOS SA): 2 modelos, ~28 unidades
  - NASSAU AZUL/GRIS/VERDE OJOTA T/ANCHA COMB | stock=2 | dias=6 | pedir=17 | precio_ref=$16,216
  - NASSAU GRIS/NEGRO OJOTA T/ANCHA COMB | stock=3 | dias=13 | pedir=11 | precio_ref=$16,216

Proveedor 668 (ALPARGATAS S.A.I.C.): 2 modelos, ~25 unidades
  - 25792 WIND V GRIS/ROSA ZAPA DEP AC DET COMB | stock=3 | dias=9 | pedir=17 | precio_ref=$36,645
  - 50210 SQUAT II NEGRO/LIMA ZAPA DEP C/DIRECTO | stock=2 | dias=12 | pedir=8 | precio_ref=$0

Proveedor 713 (DISTRINANDO MODA S.A.): 1 modelos, ~42 unidades
  - 121-1-5 BEIGE SANDALIA BAJA C/ELASTICO CAP CO | stock=4 | dias=5 | pedir=42 | precio_ref=$35,000

"""

# Para insertar pedidos, ver paso4_insertar_pedido.py + config.py
# Ejemplo de estructura:
#
# pedido = {
#     "proveedor": 515,  # SARANG TONGSANG SRL
#     "empresa": "CALZALINDO",  # o "H4"
#     "renglones": [
#         {"articulo": 12345, "cantidad": 10, "precio": 850.0},
#         # ...
#     ]
# }
#
# Para obtener codigos de artículo:
# SELECT codigo, descripcion_1, descripcion_5, codigo_sinonimo
# FROM msgestion01art.dbo.articulo
# WHERE codigo_sinonimo LIKE '5151102251%'
# ORDER BY descripcion_5

print("Este script es solo un borrador de referencia.")
print("Ver app_pedido_auto.py o paso4_insertar_pedido.py para inserción real.")
