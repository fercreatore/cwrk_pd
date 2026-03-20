"""
Alta de cliente Rodolfo Scornavacca en tabla clientes (msgestion03)
y vinculación con factura B 1005814.

Datos de TiendaNube orden #133.

Ejecutar en 111: py -3 alta_cliente_scornavacca.py
"""

import pyodbc
from datetime import datetime

CONN = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion03;"
    "UID=am;PWD=dl;"
    "Encrypt=no;"
)

conn = pyodbc.connect(CONN, timeout=15)
cursor = conn.cursor()

# 1. Obtener siguiente numero de cliente
cursor.execute("SELECT ISNULL(MAX(numero), 0) + 1 FROM msgestion03.dbo.clientes")
nuevo_numero = cursor.fetchone()[0]
print(f"Siguiente numero de cliente: {nuevo_numero}")

# 2. Verificar que no exista ya (por DNI 06072883)
cursor.execute("""
    SELECT numero, denominacion FROM msgestion03.dbo.clientes
    WHERE nume_documento = 6072883 OR denominacion LIKE '%Scornavacca%'
""")
existente = cursor.fetchone()
if existente:
    print(f"  ¡Ya existe! numero={existente[0]}, denominacion={existente[1]}")
    print(f"  Vinculando a factura 1005814...")
    cursor.execute("""
        UPDATE msgestion03.dbo.ventas2
        SET cuenta = ?, cuenta_cc = 1
        WHERE codigo = 1 AND letra = 'B' AND sucursal = 1 AND numero = 1005814
    """, existente[0])
    conn.commit()
    conn.close()
    print("  Listo.")
    exit()

# 3. Insertar cliente con datos de TiendaNube
print("Insertando cliente Rodolfo Scornavacca...")
cursor.execute("""
    INSERT INTO msgestion03.dbo.clientes (
        numero, denominacion, direccion, codigo_postal,
        telefonos, condicion_iva, cuit,
        tipo_documento, nume_documento,
        tipo_comercio, usuario, observaciones,
        fecha_ingreso, e_mail,
        apellidos, nombres,
        observaciones_facturacion
    ) VALUES (
        ?, ?, ?, ?,
        ?, ?, ?,
        ?, ?,
        ?, ?, ?,
        ?, ?,
        ?, ?,
        ?
    )
""",
    nuevo_numero,                          # numero (PK)
    'SCORNAVACCA, RODOLFO',               # denominacion (formato APELLIDO, NOMBRE como POS)
    'Mitre 3689, Matheu',                 # direccion (billing_address + billing_number + locality)
    2000,                                  # codigo_postal (Rosario)
    '+543416230030',                       # telefonos
    'C',                                   # condicion_iva (consumidor final)
    '',                                    # cuit
    96,                                    # tipo_documento (96 = DNI, como POS-API-ML)
    6072883,                               # nume_documento (identification de TN)
    2,                                     # tipo_comercio (como POS-API-ML)
    'COWORK-TN',                           # usuario
    'TIENDANUBE-COWORK',                   # observaciones
    datetime.now(),                        # fecha_ingreso
    'frutosliquidos47@gmail.com',          # e_mail
    'Scornavacca',                         # apellidos
    'Rodolfo',                             # nombres
    'TN-ID:262362777, TN-ORDER:133',       # observaciones_facturacion (como ML pone ML-ID/ML-NICK)
)

rows = cursor.rowcount
print(f"  Cliente insertado: {rows} fila(s), numero={nuevo_numero}")

# 4. Vincular con factura B 1005814
print("Vinculando con factura B 1005814...")
cursor.execute("""
    UPDATE msgestion03.dbo.ventas2
    SET cuenta = ?, cuenta_cc = 1
    WHERE codigo = 1 AND letra = 'B' AND sucursal = 1 AND numero = 1005814
""", nuevo_numero)

rows2 = cursor.rowcount
print(f"  ventas2 actualizada: {rows2} fila(s)")

conn.commit()
conn.close()

print(f"\nListo. Cliente #{nuevo_numero} creado y vinculado a factura B 1005814.")
