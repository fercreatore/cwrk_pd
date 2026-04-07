"""
Agrega abstracción "Bloch Dance Sneaker" (id=13) a omicronvt.dbo.t_abstracciones
y linkea todos los artículos Go Dance (marca 17, sinónimos DANCE/ANCES/ANCCH) via atrib_4.
"""
import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;DATABASE=omicronvt;"
    "UID=am;PWD=dl;TrustServerCertificate=yes"
)
cursor = conn.cursor()

# OP 1 — nueva abstracción id=13
cursor.execute("""
INSERT INTO omicronvt.dbo.t_abstracciones (id, codigo, descripcion, obs)
VALUES (13, '13', 'Bloch Dance Sneaker',
'Zapatilla de danza con suela separada (split sole). Bloch es la marca de referencia mundial en calzado de danza, fundada en Australia en 1932. La suela separada permite mayor flexibilidad en el metatarso para giros y pasos de jazz, hip-hop y danza contemporanea. La version Go by CLZ incluye camara de aire en el talon.')
""")
print("Abstraccion 13 (Bloch Dance Sneaker) insertada.")

# OP 2 — linkear artículos danza Go Dance (marca 17, prefijos DANCE/ANCES/ANCCH)
cursor.execute("""
UPDATE msgestion01art.dbo.articulo
SET atrib_4 = 13
WHERE marca = 17
  AND (codigo_sinonimo LIKE '017DANCE%'
    OR codigo_sinonimo LIKE '017ANCES%'
    OR codigo_sinonimo LIKE '017ANCCH%')
""")
filas = cursor.rowcount
print(f"Articulos actualizados con atrib_4=13: {filas}")

conn.commit()
conn.close()
print("OK.")
