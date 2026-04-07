#!/usr/bin/env python3
"""
Llena articulo_proveedor para artículos GO by CLZ (marca 17).
- Artículos con proveedor 457 (ZOTZ) → agrega 11 (TIMMi) como alternativo
- Artículos con proveedor 11 (TIMMi) → agrega 457 (ZOTZ) como alternativo
- También agrega el proveedor original (para que la tabla tenga ambos)

Ejecutar en el servidor 111 o via pyodbc remoto.
    py -3 llenar_articulo_proveedor_go.py --dry-run
    py -3 llenar_articulo_proveedor_go.py --ejecutar
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ejecutar', action='store_true')
    parser.add_argument('--dry-run', action='store_true', default=True)
    args = parser.parse_args()

    if args.ejecutar:
        args.dry_run = False

    # Conexión
    try:
        from config import CONN_ARTICULOS
        import pyodbc
        conn = pyodbc.connect(CONN_ARTICULOS, timeout=15)
    except Exception:
        import pyodbc
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=192.168.2.111;DATABASE=msgestion01art;"
            "UID=am;PWD=dl;TrustServerCertificate=yes;Encrypt=no",
            timeout=15
        )

    cursor = conn.cursor()

    # Obtener artículos GO by CLZ con proveedor ZOTZ o TIMMi
    cursor.execute("""
        SELECT a.codigo, a.codigo_sinonimo, a.codigo_barra, a.descripcion_1,
               a.proveedor, a.marca, a.rubro, a.subrubro
        FROM articulo a
        WHERE a.marca = 17 AND a.estado = 'V' AND a.proveedor IN (457, 11)
        ORDER BY a.codigo
    """)
    articulos = cursor.fetchall()
    cols = [d[0] for d in cursor.description]

    print(f"Artículos GO by CLZ (ZOTZ + TIMMi): {len(articulos)}")

    # Verificar qué ya existe en articulo_proveedor
    cursor.execute("SELECT codigo, codigo_proveedor FROM articulo_proveedor WHERE codigo_proveedor IN (11, 457)")
    existentes = set((int(r[0]), int(r[1])) for r in cursor.fetchall())
    print(f"Registros existentes en articulo_proveedor: {len(existentes)}")

    inserts = []
    for row in articulos:
        art = dict(zip(cols, row))
        codigo = int(art['codigo'])
        prov_original = int(art['proveedor'])
        prov_alternativo = 11 if prov_original == 457 else 457
        sinonimo = (art['codigo_sinonimo'] or '').strip()
        barcode = int(art['codigo_barra'] or 0)
        desc = (art['descripcion_1'] or '').strip()
        marca = int(art['marca'] or 0)
        rubro = int(art['rubro'] or 0)
        subrubro = int(art['subrubro'] or 0)

        # Insertar proveedor original si no existe
        if (codigo, prov_original) not in existentes:
            inserts.append((codigo, sinonimo, '', prov_original, barcode, marca, desc, rubro, subrubro))

        # Insertar proveedor alternativo si no existe
        if (codigo, prov_alternativo) not in existentes:
            inserts.append((codigo, sinonimo, '', prov_alternativo, barcode, marca, desc, rubro, subrubro))

    print(f"INSERTs a ejecutar: {len(inserts)}")

    if args.dry_run:
        print("\n=== DRY RUN — No se ejecuta nada ===")
        for i, ins in enumerate(inserts[:20]):
            print(f"  {i+1}. Art {ins[0]} → Prov {ins[3]}: {ins[6][:50]}")
        if len(inserts) > 20:
            print(f"  ... y {len(inserts) - 20} más")
        print(f"\nTotal: {len(inserts)} registros")
        print("Ejecutar con: --ejecutar")
        return

    # Ejecutar INSERTs
    sql_insert = """
        INSERT INTO articulo_proveedor
            (codigo, codigo_art_prov, codigo_parte, codigo_proveedor,
             codigo_barra, marca, descripcion, rubro, subrubro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    ok = 0
    errores = 0
    for ins in inserts:
        try:
            cursor.execute(sql_insert, ins)
            ok += 1
        except Exception as e:
            errores += 1
            if errores <= 5:
                print(f"  ERROR art {ins[0]} prov {ins[3]}: {e}")

    conn.commit()
    print(f"\n✅ Insertados: {ok}")
    print(f"❌ Errores: {errores}")
    print(f"Total articulo_proveedor ahora debería tener ~{ok + len(existentes)} registros para GO by CLZ")

if __name__ == '__main__':
    main()
