"""
Fix artículos Estado='U' con stock > 0 en depósito 5
12 artículos, 14 pares → pasar a Estado='V' (vigente)
Generado: 25-mar-2026
"""
import sys
import os

# Agregar path del proyecto para importar config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import get_connection_string
    import pyodbc
except ImportError:
    # Fallback directo si config no está disponible
    import pyodbc

CODIGOS = [
    1517,    # 001805000140 BOTA AEROBIC BLANCO (1 par)
    200843,  # 006144201925 BOTA 2 ELAST NUDE (2 pares)
    203810,  # 021660000041 MOCASIN NAUTICO NEGRO (1 par)
    16203,   # 021908000036 1/2 BOTA BADANA NEGRO (1 par)
    142884,  # 024570001440 ZAPATILLA VERDE/CAMUF (2 pares)
    26938,   # 046400002638 MOCASIN GAMUZA TOSTADO (1 par)
    186289,  # 103252300226 NAUTICO AZUL/SUELA (1 par)
    133500,  # 226614001141 ZAPATO ACORDONADO MARRON (1 par)
    179729,  # 336730001524 BOTA ALTA BEIGE (1 par)
    200790,  # 726CORSA0233 CORSANO NAUTICO AZUL (1 par)
    152683,  # 932094900029 CHENOA BOTA NEGRO (1 par)
    152679,  # 932094900432 CHENOA BOTA ROJO (1 par)
]

def main():
    conn_str = (
        "DRIVER={SQL Server};"
        "SERVER=192.168.2.111;"
        "DATABASE=msgestion01art;"
        "UID=am;PWD=dl"
    )

    print(f"Conectando a 192.168.2.111 / msgestion01art...")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Verificar estado actual
    placeholders = ','.join(['?' for _ in CODIGOS])
    cursor.execute(
        f"SELECT Codigo, Codigo_sinonimo, Descripcion_1, Estado "
        f"FROM articulo WHERE Codigo IN ({placeholders})",
        CODIGOS
    )
    rows = cursor.fetchall()

    print(f"\n--- Estado ANTES del update ---")
    u_count = 0
    for r in rows:
        estado = r.Estado.strip()
        print(f"  {r.Codigo:>8} | {r.Codigo_sinonimo} | {estado} | {r.Descripcion_1}")
        if estado == 'U':
            u_count += 1

    if u_count == 0:
        print(f"\nNingún artículo en estado 'U'. Nada que hacer.")
        conn.close()
        return

    print(f"\n{u_count} artículos en estado 'U'. Actualizando a 'V'...")

    cursor.execute(
        f"UPDATE articulo SET Estado = 'V' WHERE Codigo IN ({placeholders}) AND Estado = 'U'",
        CODIGOS
    )
    affected = cursor.rowcount
    conn.commit()

    print(f"UPDATE ejecutado: {affected} filas afectadas.")

    # Verificar después
    cursor.execute(
        f"SELECT Codigo, Codigo_sinonimo, Estado FROM articulo WHERE Codigo IN ({placeholders})",
        CODIGOS
    )
    rows = cursor.fetchall()
    print(f"\n--- Estado DESPUÉS del update ---")
    for r in rows:
        print(f"  {r.Codigo:>8} | {r.Codigo_sinonimo} | {r.Estado.strip()}")

    conn.close()
    print(f"\nListo. {affected} artículos pasados de 'U' a 'V'.")

if __name__ == "__main__":
    main()
