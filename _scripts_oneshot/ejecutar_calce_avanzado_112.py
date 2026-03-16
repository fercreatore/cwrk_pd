# -*- coding: utf-8 -*-
"""
Ejecuta crear_calce_avanzado.sql en el servidor 112 (replica).
Separa por GO y ejecuta cada batch.
"""
import pyodbc
import sys
import os

SQL_FILE = os.path.join(os.path.dirname(__file__),
    '..', '_informes', 'calzalindo_informes_DEPLOY', 'sql', 'crear_calce_avanzado.sql')

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.112,1433;"
    "DATABASE=omicronvt;"
    "UID=am;PWD=dl;"
    "TrustServerCertificate=yes;"
)

def main():
    print("Leyendo SQL:", os.path.abspath(SQL_FILE))
    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        sql_full = f.read()

    # Separar por GO (solo lineas que son exactamente "GO")
    batches = []
    current = []
    for line in sql_full.split('\n'):
        if line.strip().upper() == 'GO':
            batch = '\n'.join(current).strip()
            if batch:
                batches.append(batch)
            current = []
        else:
            current.append(line)
    # ultimo batch sin GO final
    if current:
        batch = '\n'.join(current).strip()
        if batch:
            batches.append(batch)

    print("Batches a ejecutar:", len(batches))
    print("Conectando a 192.168.2.112 (omicronvt)...")

    conn = pyodbc.connect(CONN_STR, autocommit=True)
    cursor = conn.cursor()

    for i, batch in enumerate(batches, 1):
        first_line = batch.split('\n')[0][:80]
        print(f"\n--- Batch {i}/{len(batches)}: {first_line}")
        try:
            cursor.execute(batch)
            # Consumir todos los resultsets (para PRINT y SELECT)
            while True:
                try:
                    rows = cursor.fetchall()
                    if rows:
                        for row in rows:
                            print("  ", row)
                except pyodbc.ProgrammingError:
                    pass  # no result set (DDL, UPDATE, etc)
                if not cursor.nextset():
                    break
            print("  OK")
        except Exception as e:
            print(f"  ERROR: {e}")
            # Continuar con el siguiente batch si es posible
            if "CREATE PROCEDURE" in batch or "DROP" in batch:
                print("  (continuando...)")
            else:
                print("  ABORTANDO.")
                sys.exit(1)

    cursor.close()
    conn.close()
    print("\n========================================")
    print("  CALCE AVANZADO ejecutado en 112 OK!")
    print("========================================")

if __name__ == '__main__':
    main()
