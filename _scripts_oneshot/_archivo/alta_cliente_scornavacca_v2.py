"""
Alta de cliente Rodolfo Scornavacca en tabla clientes (msgestion03).
NO toca ventas2.cuenta (es NULL como hace el POS).

Ejecutar en 111: py -3 alta_cliente_scornavacca_v2.py
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

# Verificar que no exista ya
cursor.execute("""
    SELECT numero, denominacion FROM msgestion03.dbo.clientes
    WHERE nume_documento = 6072883 OR denominacion LIKE '%SCORNAVACCA%'
""")
existente = cursor.fetchone()
if existente:
    print(f"Ya existe: numero={existente[0]}, {existente[1]}")
    conn.close()
    exit()

# Obtener siguiente numero
cursor.execute("SELECT ISNULL(MAX(numero), 0) + 1 FROM msgestion03.dbo.clientes")
nuevo_numero = cursor.fetchone()[0]
print(f"Numero de cliente: {nuevo_numero}")

# Insertar
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
    nuevo_numero,
    'SCORNAVACCA, RODOLFO',
    'Mitre 3689, Matheu, Rosario',
    2000,
    '+543416230030',
    'C',
    '',
    96,
    6072883,
    2,
    'COWORK-TN',
    'TIENDANUBE-COWORK',
    datetime.now(),
    'frutosliquidos47@gmail.com',
    'Scornavacca',
    'Rodolfo',
    'TN-ID:262362777, TN-ORDER:133',
)

conn.commit()
print(f"Cliente #{nuevo_numero} SCORNAVACCA, RODOLFO creado OK.")
conn.close()
