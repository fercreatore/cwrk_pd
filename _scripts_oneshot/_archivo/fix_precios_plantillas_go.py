# fix_precios_plantillas_go.py
# Corrige precios de TODAS las plantillas GO by CLZ (150-154)
# El precio que se pasó como precio_fabrica era en realidad el precio_1.
# Ahora precio_fabrica = costo China × TC BNA venta ($1,415)
# Ejecutar en 111 con: py -3 fix_precios_plantillas_go.py

import pyodbc

# --- Configuración ---
SERVER = '192.168.2.111'
USER = 'am'
PASS = 'dl'
DATABASE = 'msgestion01art'

TC = 1415.00  # Tipo de cambio BNA venta 12-mar-2026

# --- Modelos ---
# Cada modelo: (nombre, codigos, precio_1_correcto, costo_usd)
MODELOS = [
    {
        'nombre': '150 PLANTILLA DEPORTIVA RUNNING',
        'codigos': [359262, 359264, 359266, 359268, 359270, 359272],
        'precio_1': 12999.00,
        'costo_usd': 1.47,
    },
    {
        'nombre': '151 PLANTILLA DEPORTIVA RESPIRABLE',
        'codigos': [359273, 359275, 359277, 359279, 359281, 359283],
        'precio_1': 9999.00,
        'costo_usd': 1.35,
    },
    {
        'nombre': '152 PLANTILLA DEPORTIVA SOPORTE',
        'codigos': [359284, 359286, 359288, 359290, 359292],
        'precio_1': 24999.00,
        'costo_usd': 2.73,
    },
    {
        'nombre': '153 PLANTILLA DEPORTIVA SOPORTE Y RESPIRACION',
        'codigos': [359293, 359295, 359297, 359299, 359301, 359303],
        'precio_1': 22999.00,
        'costo_usd': 2.07,
    },
    {
        'nombre': '154 PLANTILLA MEMORY FOAM',
        'codigos': [359304, 359306, 359308, 359310],
        'precio_1': 12999.00,
        'costo_usd': 1.78,
    },
]

# Utilidades fijas para precio_2, precio_3, precio_4
UTIL_2 = 124
UTIL_3 = 60
UTIL_4 = 45


def calcular_precios(modelo):
    """Calcula todos los precios a partir del costo USD y precio_1 objetivo."""
    precio_fabrica = round(modelo['costo_usd'] * TC, 2)
    precio_1 = modelo['precio_1']

    # utilidad_1 se recalcula: precio_1 = precio_fabrica * (1 + util/100)
    utilidad_1 = round((precio_1 / precio_fabrica - 1) * 100, 2)

    precio_2 = round(precio_fabrica * (1 + UTIL_2 / 100), 2)
    precio_3 = round(precio_fabrica * (1 + UTIL_3 / 100), 2)
    precio_4 = round(precio_fabrica * (1 + UTIL_4 / 100), 2)
    precio_costo = precio_fabrica

    return {
        'precio_fabrica': precio_fabrica,
        'precio_costo': precio_costo,
        'precio_1': precio_1,
        'precio_2': precio_2,
        'precio_3': precio_3,
        'precio_4': precio_4,
        'utilidad_1': utilidad_1,
        'utilidad_2': UTIL_2,
        'utilidad_3': UTIL_3,
        'utilidad_4': UTIL_4,
    }


# --- Main ---
print("=" * 70)
print("FIX PRECIOS — PLANTILLAS GO by CLZ (150 a 154)")
print(f"TC BNA venta: ${TC:,.2f}")
print("=" * 70)

# Pre-calcular todo
for m in MODELOS:
    m['precios'] = calcular_precios(m)
    p = m['precios']
    print(f"\n--- {m['nombre']} ({len(m['codigos'])} talles) ---")
    print(f"  Costo USD:       ${m['costo_usd']}")
    print(f"  precio_fabrica:  ${p['precio_fabrica']:,.2f}")
    print(f"  precio_costo:    ${p['precio_costo']:,.2f}")
    print(f"  precio_1:        ${p['precio_1']:,.2f}  (utilidad_1: {p['utilidad_1']:.2f}%)")
    print(f"  precio_2:        ${p['precio_2']:,.2f}  (utilidad_2: {UTIL_2}%)")
    print(f"  precio_3:        ${p['precio_3']:,.2f}  (utilidad_3: {UTIL_3}%)")
    print(f"  precio_4:        ${p['precio_4']:,.2f}  (utilidad_4: {UTIL_4}%)")
    print(f"  Códigos:         {m['codigos']}")

print("\n" + "=" * 70)

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

    total_filas = 0

    for m in MODELOS:
        p = m['precios']
        codigos_str = ','.join(str(c) for c in m['codigos'])

        # Verificar ANTES
        cursor.execute(f"""
            SELECT codigo, precio_1, precio_fabrica, utilidad_1
            FROM articulo
            WHERE codigo IN ({codigos_str})
            ORDER BY codigo
        """)
        print(f"\n--- {m['nombre']} — ANTES ---")
        for row in cursor.fetchall():
            print(f"  cod={row.codigo}  p1={row.precio_1}  pfab={row.precio_fabrica}  util1={row.utilidad_1}")

        # UPDATE
        sql_update = f"""
            UPDATE articulo
            SET precio_1 = ?,
                precio_2 = ?,
                precio_3 = ?,
                precio_4 = ?,
                precio_fabrica = ?,
                precio_costo = ?,
                utilidad_1 = ?,
                utilidad_2 = ?,
                utilidad_3 = ?,
                utilidad_4 = ?,
                fecha_modificacion = GETDATE()
            WHERE codigo IN ({codigos_str})
        """

        cursor.execute(sql_update, (
            p['precio_1'], p['precio_2'], p['precio_3'], p['precio_4'],
            p['precio_fabrica'], p['precio_costo'],
            p['utilidad_1'], p['utilidad_2'], p['utilidad_3'], p['utilidad_4']
        ))
        filas = cursor.rowcount
        total_filas += filas
        print(f"  UPDATE: {filas} filas")

        # Verificar DESPUÉS
        cursor.execute(f"""
            SELECT codigo, precio_1, precio_fabrica, precio_2, precio_3, precio_4, utilidad_1
            FROM articulo
            WHERE codigo IN ({codigos_str})
            ORDER BY codigo
        """)
        print(f"  DESPUÉS:")
        for row in cursor.fetchall():
            print(f"  cod={row.codigo}  p1={row.precio_1}  pfab={row.precio_fabrica}  p2={row.precio_2}  p3={row.precio_3}  p4={row.precio_4}  util1={row.utilidad_1}")

    conn.commit()
    print(f"\n{'=' * 70}")
    print(f"✅ COMMIT OK — {total_filas} artículos actualizados en total")
    print(f"{'=' * 70}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    if 'conn' in dir():
        conn.rollback()
        print("ROLLBACK ejecutado")
finally:
    if 'conn' in dir():
        conn.close()
        print("Conexión cerrada")
