# fix_precios_150_plantilla.py
# Corrige precios de GO by CLZ - 150 PLANTILLA DEPORTIVA RUNNING
# El precio que se pasó como precio_fabrica era en realidad el precio_1 deseado.
# Contado objetivo: $12,999 = precio_1 * 0.95
# Ejecutar en 111 con: py -3 fix_precios_150_plantilla.py

import pyodbc

# --- Configuración ---
SERVER = '192.168.2.111'
USER = 'am'
PASS = 'dl'
DATABASE = 'msgestion01art'

# Códigos de los 6 talles de la 150 PLANTILLA DEPORTIVA RUNNING
CODIGOS = [359262, 359264, 359266, 359268, 359270, 359272]

# --- Cálculo de precios ---
CONTADO_OBJETIVO = 12999.00
UTILIDAD_1 = 120  # se mantiene
UTILIDAD_2 = 144  # se mantiene

# precio_1 = contado / 0.95
PRECIO_1 = round(CONTADO_OBJETIVO / 0.95, 2)  # 13683.16

# precio_fabrica = precio_1 / (1 + utilidad_1/100)
PRECIO_FABRICA = round(PRECIO_1 / (1 + UTILIDAD_1 / 100), 2)  # 6219.62

# precio_2 = precio_fabrica * (1 + utilidad_2/100)
PRECIO_2 = round(PRECIO_FABRICA * (1 + UTILIDAD_2 / 100), 2)  # 15175.87

# precio_3 y precio_4 = precio_fabrica (utilidad 0)
PRECIO_3 = PRECIO_FABRICA
PRECIO_4 = PRECIO_FABRICA

# precio_costo = precio_fabrica
PRECIO_COSTO = PRECIO_FABRICA

print("=" * 60)
print("FIX PRECIOS - 150 PLANTILLA DEPORTIVA RUNNING")
print("=" * 60)
print(f"Contado objetivo:  ${CONTADO_OBJETIVO:,.2f}")
print(f"precio_1:          ${PRECIO_1:,.2f}")
print(f"precio_2:          ${PRECIO_2:,.2f}")
print(f"precio_3:          ${PRECIO_3:,.2f}")
print(f"precio_4:          ${PRECIO_4:,.2f}")
print(f"precio_fabrica:    ${PRECIO_FABRICA:,.2f}")
print(f"precio_costo:      ${PRECIO_COSTO:,.2f}")
print(f"Contado check:     ${PRECIO_1 * 0.95:,.2f}")
print(f"Artículos a actualizar: {len(CODIGOS)}")
print(f"Códigos: {CODIGOS}")
print("=" * 60)

conn_str = (
    f"DRIVER={{SQL Server}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"UID={USER};"
    f"PWD={PASS}"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    codigos_str = ','.join(str(c) for c in CODIGOS)

    # Verificar estado ANTES
    cursor.execute(f"""
        SELECT codigo, precio_1, precio_fabrica, precio_costo
        FROM articulo
        WHERE codigo IN ({codigos_str})
        ORDER BY codigo
    """)
    print("\nANTES:")
    for row in cursor.fetchall():
        print(f"  codigo={row.codigo}  precio_1={row.precio_1}  precio_fabrica={row.precio_fabrica}  precio_costo={row.precio_costo}")

    # UPDATE
    sql_update = f"""
        UPDATE articulo
        SET precio_1 = ?,
            precio_2 = ?,
            precio_3 = ?,
            precio_4 = ?,
            precio_fabrica = ?,
            precio_costo = ?,
            fecha_modificacion = GETDATE()
        WHERE codigo IN ({codigos_str})
    """

    cursor.execute(sql_update, (PRECIO_1, PRECIO_2, PRECIO_3, PRECIO_4, PRECIO_FABRICA, PRECIO_COSTO))
    filas = cursor.rowcount
    print(f"\nUPDATE: {filas} filas actualizadas")

    # Verificar estado DESPUÉS
    cursor.execute(f"""
        SELECT codigo, precio_1, precio_fabrica, precio_costo, precio_2
        FROM articulo
        WHERE codigo IN ({codigos_str})
        ORDER BY codigo
    """)
    print("\nDESPUÉS:")
    for row in cursor.fetchall():
        print(f"  codigo={row.codigo}  precio_1={row.precio_1}  precio_fabrica={row.precio_fabrica}  precio_costo={row.precio_costo}  precio_2={row.precio_2}")

    conn.commit()
    print(f"\n✅ COMMIT OK — {filas} artículos actualizados")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    if 'conn' in dir():
        conn.rollback()
        print("ROLLBACK ejecutado")
finally:
    if 'conn' in dir():
        conn.close()
        print("Conexión cerrada")
