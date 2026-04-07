#!/usr/bin/env python3
# fix_subrubro_amphora.py
# Asigna subrubro correcto a los 21 articulos Amphora AW26 (codigo 361246-361266)
# Subrubros: 18=CARTERAS, 25=MOCHILAS, 26=BILLETERAS, 30=BOLSOS
#
# EJECUTAR EN 111:
#   py -3 fix_subrubro_amphora.py

import pyodbc
import socket

_hostname = socket.gethostname().upper()
if _hostname in ("DELL-SVR", "DELLSVR"):
    SERVIDOR = "localhost"
    DRIVER = "ODBC Driver 17 for SQL Server"
    EXTRAS = ""
else:
    SERVIDOR = "192.168.2.111"
    DRIVER = "ODBC Driver 18 for SQL Server"
    EXTRAS = "TrustServerCertificate=yes;Encrypt=no;"

conn_str = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVIDOR};"
    f"DATABASE=msgestion01art;"
    f"UID=am;PWD=dl;"
    f"{EXTRAS}"
)

# Mapping: keyword in descripcion -> subrubro
# 18=CARTERAS (incluye "CARTERA", "PORTA NOTEBOOK")
# 25=MOCHILAS
# 39=ACC. MARRO (riñonera, bandolera)
SUBRUBRO_MAP = {
    "MOCHILA": 25,
    "RIÑONERA": 39,
    "BANDOLERA": 39,
    "PORTA NOTEBOOK": 18,
    "CARTERA": 18,
}

def detectar_subrubro(desc):
    d = desc.upper()
    if "PORTA NOTEBOOK" in d:
        return 18
    if "MOCHILA" in d:
        return 25
    if "RIÑONERA" in d:
        return 39
    if "BANDOLERA" in d:
        return 39
    if "CARTERA" in d:
        return 18
    return 18  # default carteras

conn = pyodbc.connect(conn_str, timeout=10)
cursor = conn.cursor()

# Get the 21 Amphora articles with NULL subrubro
cursor.execute("""
    SELECT codigo, descripcion_1, subrubro
    FROM articulo
    WHERE proveedor = 44 AND subrubro IS NULL AND estado = 'V'
    ORDER BY codigo
""")
rows = cursor.fetchall()
print(f"Articulos Amphora sin subrubro: {len(rows)}")

updated = 0
for row in rows:
    cod, desc, _ = row
    sub = detectar_subrubro(desc)
    cursor.execute("UPDATE articulo SET subrubro = ? WHERE codigo = ?", (sub, cod))
    print(f"  [{cod}] {desc} -> subrubro {sub}")
    updated += 1

conn.commit()
print(f"\n{updated} articulos actualizados.")
conn.close()
