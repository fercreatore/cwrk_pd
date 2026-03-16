#!/usr/bin/env python3
"""
fix_desc1_wake.py — Corrige descripcion_1 y descripcion_3 flojas de artículos WAKE
====================================================================================
Los artículos _I26/_V26 se cargaron solo con "MODELO COLOR" sin tipo de calzado.
Este script busca el tipo del modelo base y actualiza las descripciones.

Ejemplo:
  ANTES:  WKC496_I26 ROSA
  DESPUES: WKC496_I26 ROSA ZAPA DEP CORD/ELAST DET ABROJ

EJECUTAR EN EL 111:
  py -3 fix_desc1_wake.py              ← dry-run, solo muestra
  py -3 fix_desc1_wake.py --ejecutar   ← escribe en producción
"""

import sys
import re
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

CONN = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVIDOR};"
    f"DATABASE=msgestion01art;"
    f"UID=am;PWD=dl;"
    f"{EXTRAS}"
)


def main():
    import pyodbc
    dry_run = "--ejecutar" not in sys.argv

    print(f"\n{'='*70}")
    print(f"  FIX DESCRIPCIONES WAKE — {'DRY-RUN' if dry_run else 'PRODUCCIÓN'}")
    print(f"{'='*70}")

    conn = pyodbc.connect(CONN, timeout=10)
    cursor = conn.cursor()

    # 1) Buscar artículos WAKE con desc1 floja (solo modelo+color, sin tipo)
    #    Criterio: marca=746 AND desc1 tiene máximo 2 "palabras" (modelo + color)
    cursor.execute("""
        SELECT codigo, RTRIM(descripcion_1) as desc1, RTRIM(descripcion_3) as desc3,
               RTRIM(descripcion_4) as color
        FROM articulo
        WHERE marca = 746 AND estado = 'V'
          AND descripcion_1 LIKE 'WKC%'
    """)

    todos = cursor.fetchall()

    # Filtrar los que tienen desc1 floja (solo 2 partes: modelo + color)
    flojos = []
    for row in todos:
        codigo, desc1, desc3, color = row
        partes = desc1.strip().split()
        if len(partes) <= 2:
            flojos.append((codigo, desc1, desc3, color))

    print(f"  Artículos WAKE total: {len(todos)}")
    print(f"  Con descripción floja: {len(flojos)}")

    if not flojos:
        print("  ✅ No hay descripciones flojas que corregir")
        conn.close()
        return

    # 2) Para cada modelo base, buscar el tipo de calzado de artículos bien cargados
    tipo_cache = {}

    def obtener_tipo(modelo_con_sufijo):
        modelo_base = re.sub(r'_[IV]\d{2}$', '', modelo_con_sufijo)
        if modelo_base in tipo_cache:
            return tipo_cache[modelo_base]

        cursor.execute("""
            SELECT TOP 1 RTRIM(descripcion_1)
            FROM articulo
            WHERE descripcion_1 LIKE ? AND marca = 746 AND estado = 'V'
              AND LEN(RTRIM(descripcion_1)) > ?
            ORDER BY codigo DESC
        """, [f"{modelo_base} %", len(modelo_base) + 10])

        row = cursor.fetchone()
        tipo = ""
        if row:
            partes = row[0].split()
            if len(partes) >= 3:
                tipo = " ".join(partes[2:])

        tipo_cache[modelo_base] = tipo
        return tipo

    # 3) Actualizar
    actualizados = 0
    sin_tipo = 0

    for codigo, desc1, desc3, color in flojos:
        partes = desc1.strip().split()
        modelo = partes[0] if partes else ""
        color_desc = partes[1] if len(partes) > 1 else color

        tipo = obtener_tipo(modelo)

        if not tipo:
            # Modelos 100% nuevos sin referencia base → default "ZAPA DEP" (son todos WAKE Sport)
            tipo = "ZAPA DEP"
            print(f"  ℹ️  [{codigo:6d}] {desc1:<35s} — sin base, usando default '{tipo}'")

        nueva_desc1 = f"{modelo} {color_desc} {tipo}"[:60]
        nueva_desc3 = f"{modelo} {tipo}"[:40]

        print(f"  [{codigo:6d}] {desc1:<35s} → {nueva_desc1}")

        if not dry_run:
            cursor.execute("""
                UPDATE articulo
                SET descripcion_1 = ?, descripcion_3 = ?
                WHERE codigo = ?
            """, [nueva_desc1, nueva_desc3, codigo])

        actualizados += 1

    if not dry_run:
        conn.commit()

    conn.close()

    print(f"\n{'='*70}")
    print(f"  Actualizados: {actualizados}")
    print(f"  Sin tipo (no se tocaron): {sin_tipo}")
    print(f"  {'DRY-RUN — nada escrito' if dry_run else 'PRODUCCIÓN — cambios guardados'}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
