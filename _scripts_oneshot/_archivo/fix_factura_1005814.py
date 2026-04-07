"""
Fix factura B 1005814 (Rodolfo Scornavacca / COWORK-TN).
Agrega campos faltantes que MS Gestión necesita para mostrarla:
  - fecha_hora
  - talonario = 1
  - libro_iva = 'N'
  - contabiliza = 'N'

Ejecutar en 111: py -3 fix_factura_1005814.py
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

print("Corrigiendo factura B 1005814 (Rodolfo Scornavacca)...")

cursor.execute("""
    UPDATE msgestion03.dbo.ventas2
    SET fecha_hora = ?,
        talonario = 1,
        libro_iva = 'N',
        contabiliza = 'N'
    WHERE codigo = 1 AND letra = 'B' AND sucursal = 1 AND numero = 1005814
""", datetime(2026, 3, 17, 13, 9, 22))

rows = cursor.rowcount
conn.commit()
conn.close()

print(f"  ventas2 actualizada: {rows} fila(s)")
print("Listo. La factura debería verse ahora en MS Gestión.")
