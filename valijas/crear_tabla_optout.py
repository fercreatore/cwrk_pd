#!/usr/bin/env python3
"""
Crea la tabla whatsapp_optout en PostgreSQL (clz_productos).
Ejecutar una sola vez:
    python3 valijas/crear_tabla_optout.py
"""
import psycopg2

CONN = "host=200.58.109.125 port=5432 dbname=clz_productos user=guille password=Martes13#"

SQL = """
CREATE TABLE IF NOT EXISTS whatsapp_optout (
    id SERIAL PRIMARY KEY,
    telefono VARCHAR(20) UNIQUE,
    nombre VARCHAR(200),
    cuenta VARCHAR(20),
    motivo VARCHAR(500),
    fecha_baja TIMESTAMP DEFAULT NOW(),
    origen VARCHAR(50)
);
"""

def main():
    conn = psycopg2.connect(CONN)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(SQL)
    print("Tabla whatsapp_optout creada (o ya existia).")
    cur.execute("SELECT COUNT(*) FROM whatsapp_optout")
    print(f"Registros actuales: {cur.fetchone()[0]}")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
