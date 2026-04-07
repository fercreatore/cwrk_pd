"""
UPDATE PRECIOS LIQUIDACION — TOP 20 STOCK MUERTO
Semana 7-11 abr 2026

ESTADO: PENDIENTE APROBACION FERNANDO
Ejecutar solo despues de que Fernando revise _informes/agenda/2026-04-06_precios_liquidacion.md

Instruccion: comentar/descomentar las lineas de modelos aprobados.
"""

import pyodbc
import sys
from datetime import datetime

# Conexion SQL Server
conn_str = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=192.168.2.111;DATABASE=msgestion01art;'
    'UID=am;PWD=dl;TrustServerCertificate=yes'
)

# MODELOS APROBADOS PARA LIQUIDACION
# Fernando: descomentar los que aprueba, dejar comentados los que no
MODELOS_APROBADOS = [
    # (modelo, precio_liq)
    # ('96000331', 80831.57599999999),  # CAVATINI | 20-0331 EROS NEGRO NAUTICO ACORD COLEGIA | stk=22 | act=$115,473 | -30%
    # ('26450223', 83800),  # MERRELL | CZS 650223 AGILITY PEAK 5 NEGRO ZAPA ACO | stk=12 | act=$209,473 | -60%
    # ('05722560', 43200),  # GONDOLINO | 2256 CRUDO GUILLERMINA CALADA ABROJO T/G | stk=17 | act=$108,000 | -60%
    # ('31100B22', 23400),  # SOFT | B22 LIMA/NEGRO/NARANJA BOTIN CAMPO AC ME | stk=29 | act=$58,526 | -60%
    # ('26455311', 75400),  # CATERPILLAR | RZN 155311 DECADE NEGRO ZAPA URB ACORD | stk=9 | act=$188,421 | -60%
    # ('656WORLD', 66900),  # REEBOK | ERS WORLD NEGRO/GRIS/CRUDO ZAPA SNEAKER  | stk=8 | act=$167,368 | -60%
    # ('561NUR01', 38100),  # RINGO | NURU 01 NEGRO/HUESO ZAPA URB BAJA ACORD  | stk=14 | act=$95,200 | -60%
    # ('26414020', 75400),  # CATERPILLAR | RZNN 140020 TOUGH  NEGRO ZAPA URB BAJA A | stk=7 | act=$188,421 | -60%
    # ('561VIP01', 52200),  # RINGO | VIPER 01 BLANCO/NEGRO ZAPA SNEAKK ACORD  | stk=10 | act=$130,400 | -60%
    # ('264RAM12', 103700),  # CATERPILLAR | RAM 125314 FOUNDER SUELA BORCEGO ACORD D | stk=5 | act=$259,350 | -60%
    # ('722UADRA', 56000),  # OLYMPIKUS | QUADRA DORADO/MULTI ZAPA BASKET  ACORD C | stk=9 | act=$139,999 | -60%
    # ('66825906', 27114.228),  # TOPPER | 25906 CANDUN GRIS/NEGRO BOTA BASKET TEJI | stk=12 | act=$104,947 | -74%
    # ('26414528', 83800),  # HUSH PUPPIES | HAN 145288 HESTON NEGRO BORCEGO AC COMB  | stk=6 | act=$209,473 | -60%
    # ('099GRETA', 55600),  # LADY STORK | GRETA BEIGE BOTA C/CIERRE DET CADENA | stk=9 | act=$139,122 | -60%
    # ('561JOEL1', 62600),  # RINGO | JOEL 01 NOBUCK MAIZ BORCEGO ACORD DET CU | stk=8 | act=$156,400 | -60%
    # ('561TRAFU', 50000),  # RINGO | TRAFUL 01 NEGRO/GRIS ZAPA TREKK AC DET C | stk=10 | act=$125,000 | -60%
    # ('213LIRIO', 35200),  # PASOTTI | LIRIO NEGRO/VISON ZAPA URB DET CIERRE LA | stk=14 | act=$88,000 | -60%
    # ('31100B12', 23400),  # SOFT | B12 BLANCO/NEGRO BOTIN CAMPO AC DET MANC | stk=21 | act=$58,526 | -60%
    # ('10311210', 26400),  # KRUNCHI | 1121 NEGRO MOCASIN NAUTICO GAMUZA ACORDO | stk=18 | act=$66,105 | -60%
    # ('80814266', 27500),  # PENALTY | 214266 VIENTO Y2 NEGRO/LIMA BOTIN CAMPO  | stk=17 | act=$68,733 | -60%
]

if not MODELOS_APROBADOS:
    print('No hay modelos aprobados. Descomentar las lineas aprobadas por Fernando.')
    sys.exit(0)

print(f'Ejecutando UPDATE para {len(MODELOS_APROBADOS)} modelos...')
print(f'Timestamp: {datetime.now()}')
print()

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    updated = 0
    for modelo, precio_liq in MODELOS_APROBADOS:
        # Verificar precio actual antes de actualizar
        cursor.execute('SELECT codigo, precio, descripcion FROM articulo WHERE codigo = ?', modelo)
        row = cursor.fetchone()
        if not row:
            print(f'  SKIP {modelo}: no encontrado en articulo')
            continue
        precio_actual = row.precio
        print(f'  UPDATE {modelo} | {row.descripcion[:40]} | ${precio_actual:,.0f} -> ${precio_liq:,.0f}')
        cursor.execute('UPDATE msgestion01art.dbo.articulo SET precio = ? WHERE codigo = ?', precio_liq, modelo)
        updated += 1
    
    conn.commit()
    print()
    print(f'OK: {updated} articulos actualizados')
    conn.close()

except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)