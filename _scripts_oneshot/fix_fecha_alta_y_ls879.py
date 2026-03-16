"""
fix_fecha_alta_y_ls879.py
=========================
1) Pone fecha_alta a todos los artículos creados por COWORK que tienen NULL
   - Diadora (360527-360546): 2026-03-12
   - Atomik RUNFLEX (360547-360569): 2026-03-12
   - Footy/Tivory (360570-360778): 2026-03-12

2) Renombra ST879 → LS879 en:
   - msgestion01art.dbo.articulo (descripcion_1)
   - msgestion03.dbo.pedico1 (descripcion) del pedido #1134071

Ejecutar en 192.168.2.111:
  py -3 fix_fecha_alta_y_ls879.py          # DRY RUN
  py -3 fix_fecha_alta_y_ls879.py --ejecutar
"""

import pyodbc
import sys

DRY_RUN = "--ejecutar" not in sys.argv

CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "UID=am;PWD=dl;"
)

# --- Lotes de artículos con su fecha de alta ---
LOTES_FECHA = [
    # (desde, hasta, fecha, descripción)
    (360527, 360546, '2026-03-12', 'Diadora'),
    (360547, 360569, '2026-03-12', 'Atomik RUNFLEX'),
    (360570, 360778, '2026-03-12', 'Footy/Tivory'),
]

# --- Artículos ST879 → LS879 (códigos 360773-360778) ---
ST879_CODES = list(range(360773, 360779))  # 360773 a 360778


def main():
    if DRY_RUN:
        print("=" * 60)
        print("  DRY RUN — no se modifica nada")
        print("  Usar: py -3 fix_fecha_alta_y_ls879.py --ejecutar")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  EJECUTANDO EN PRODUCCIÓN")
        print("=" * 60)

    conn = pyodbc.connect(CONN_STR, autocommit=False)
    cur = conn.cursor()

    total_fecha = 0
    total_rename = 0

    # ========================================
    # PARTE 1: fecha_alta
    # ========================================
    print("\n--- PARTE 1: Corregir fecha_alta NULL ---")

    for desde, hasta, fecha, desc in LOTES_FECHA:
        # Contar cuántos tienen NULL
        cur.execute("""
            SELECT COUNT(*) FROM msgestion01art.dbo.articulo
            WHERE codigo BETWEEN ? AND ? AND fecha_alta IS NULL
        """, desde, hasta)
        cnt = cur.fetchone()[0]

        if cnt == 0:
            print(f"  {desc} ({desde}-{hasta}): ya tienen fecha_alta, skip")
            continue

        print(f"  {desc} ({desde}-{hasta}): {cnt} artículos → fecha_alta = {fecha}")

        if not DRY_RUN:
            cur.execute("""
                UPDATE msgestion01art.dbo.articulo
                SET fecha_alta = ?
                WHERE codigo BETWEEN ? AND ? AND fecha_alta IS NULL
            """, fecha, desde, hasta)
            print(f"    → {cur.rowcount} actualizados")
            total_fecha += cur.rowcount
        else:
            total_fecha += cnt

    # ========================================
    # PARTE 2: Renombrar ST879 → LS879
    # ========================================
    print("\n--- PARTE 2: Renombrar ST879 → LS879 ---")

    NEW_DESC = 'LS879 BLANCO AZUL ZAPATILLA COLEGIAL SKATE 1 ABROJO'
    placeholders = ','.join(['?'] * len(ST879_CODES))

    # 2a) En artículos (descripcion_1)
    cur.execute(f"""
        SELECT codigo, descripcion_1
        FROM msgestion01art.dbo.articulo
        WHERE codigo IN ({placeholders})
    """, *ST879_CODES)
    arts = cur.fetchall()

    for art in arts:
        old_desc = art.descripcion_1.strip()
        if old_desc != NEW_DESC:
            print(f"  Artículo {art.codigo}: '{old_desc}' → '{NEW_DESC}'")
            if not DRY_RUN:
                cur.execute("""
                    UPDATE msgestion01art.dbo.articulo
                    SET descripcion_1 = ?
                    WHERE codigo = ?
                """, NEW_DESC, art.codigo)
                total_rename += 1
        else:
            print(f"  Artículo {art.codigo}: ya tiene descripción correcta, skip")

    # 2b) En pedico1 del pedido #1134071
    cur.execute(f"""
        SELECT articulo, descripcion
        FROM msgestion03.dbo.pedico1
        WHERE numero = 1134071 AND codigo = 8 AND letra = 'X' AND sucursal = 1
        AND articulo IN ({placeholders})
    """, *ST879_CODES)
    peds = cur.fetchall()

    for ped in peds:
        old_desc = ped.descripcion.strip()
        if old_desc != NEW_DESC:
            print(f"  Pedido art {ped.articulo}: '{old_desc}' → '{NEW_DESC}'")
            if not DRY_RUN:
                cur.execute("""
                    UPDATE msgestion03.dbo.pedico1
                    SET descripcion = ?
                    WHERE numero = 1134071 AND codigo = 8 AND letra = 'X'
                    AND sucursal = 1 AND articulo = ?
                """, NEW_DESC, ped.articulo)
                total_rename += 1
        else:
            print(f"  Pedido art {ped.articulo}: ya tiene descripción correcta, skip")

    # ========================================
    # PARTE 3: Actualizar detalle etiqueta (descripcion_3 y descripcion_4)
    # ========================================
    print("\n--- PARTE 3: Corregir detalle etiqueta ---")

    NEW_DESC3 = 'LS879 ZAPATILLA COLEGIAL SKATE 1 ABROJO FOOTY'
    NEW_DESC4 = 'BLANCO AZUL'

    cur.execute(f"""
        SELECT codigo, descripcion_3, descripcion_4
        FROM msgestion01art.dbo.articulo
        WHERE codigo IN ({placeholders})
    """, *ST879_CODES)
    etiq = cur.fetchall()

    for e in etiq:
        d3 = (e.descripcion_3 or '').strip()
        d4 = (e.descripcion_4 or '').strip()
        cambios = []
        if d3 != NEW_DESC3:
            cambios.append(f"desc3: '{d3}' → '{NEW_DESC3}'")
        if d4 != NEW_DESC4:
            cambios.append(f"desc4: '{d4}' → '{NEW_DESC4}'")

        if cambios:
            print(f"  Artículo {e.codigo}: {', '.join(cambios)}")
            if not DRY_RUN:
                cur.execute("""
                    UPDATE msgestion01art.dbo.articulo
                    SET descripcion_3 = ?, descripcion_4 = ?
                    WHERE codigo = ?
                """, NEW_DESC3, NEW_DESC4, e.codigo)
        else:
            print(f"  Artículo {e.codigo}: etiqueta ya correcta, skip")

    # ========================================
    # COMMIT o resumen
    # ========================================
    print("\n" + "=" * 60)
    if DRY_RUN:
        print(f"DRY RUN completado:")
        print(f"  - fecha_alta: {total_fecha} artículos se actualizarían")
        print(f"  - ST879→LS879: {len(arts) + len(peds)} registros se renombrarían")
        print("Ejecutar con --ejecutar para aplicar cambios")
        conn.rollback()
    else:
        conn.commit()
        print(f"EJECUTADO OK:")
        print(f"  - fecha_alta: {total_fecha} artículos actualizados")
        print(f"  - ST879→LS879: {total_rename} registros renombrados")

    conn.close()


if __name__ == "__main__":
    main()
