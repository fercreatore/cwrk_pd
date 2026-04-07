"""
Fix FINAL factura B 1005814 — igualar campos al formato POS.
Ejecutar en 111: py -3 fix_factura_1005814_final.py
"""
import pyodbc

CONN = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion03;"
    "UID=am;PWD=dl;"
    "Encrypt=no;"
)

conn = pyodbc.connect(CONN, timeout=15)
cursor = conn.cursor()

print("Fix final factura B 1005814...")

cursor.execute("""
    UPDATE msgestion03.dbo.ventas2
    SET denominacion = 'SCORNAVACCA, RODOLFO',
        zona = 1,
        provincia = 'S',
        numero_cuit = '00000000000',
        copias = 1,
        viajante = 585,
        entregador = 0,
        calificacion = '',
        monto_exento = NULL,
        financiacion_general = NULL,
        monto_financiacion = NULL
    WHERE codigo = 1 AND letra = 'B' AND sucursal = 1 AND numero = 1005814
""")

rows = cursor.rowcount
conn.commit()
conn.close()

print(f"  ventas2 actualizada: {rows} fila(s)")
print("  Campos igualados al formato POS.")
