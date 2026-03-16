# paso7_reconstruir_colores.py
# Reconstruye / homogeneiza la tabla colores a partir de los dígitos 9-10
# del campo codigo_sinonimo en artículos existentes.
#
# Estructura del sinónimo (12 chars):
#   Pos 1-3  : proveedor (ej: 668 = ALPARGATAS)
#   Pos 4-8  : SKU (5 chars alfanumérico)
#   Pos 9-10 : código de color (2 dígitos)
#   Pos 11-12: talle (2 dígitos)
#
# Este script:
#   1. Extrae todos los pares (cod_color, descripcion_4) de sinónimos existentes
#   2. Determina el "color dominante" para cada código
#   3. Compara con la tabla colores actual
#   4. Genera SQL para insertar los códigos faltantes
#   5. Genera un reporte de inconsistencias (códigos usados con varios colores)
#
# EJECUTAR:
#   python paso7_reconstruir_colores.py --dry-run
#   python paso7_reconstruir_colores.py --ejecutar

import sys
import argparse
import pyodbc
from collections import defaultdict

from config import CONN_COMPRAS


def obtener_colores_actuales() -> dict:
    """Retorna dict {codigo: denominacion} de la tabla colores actual."""
    sql = "SELECT codigo, denominacion FROM msgestionC.dbo.colores ORDER BY codigo"
    colores = {}
    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for row in cursor.fetchall():
                colores[int(row[0])] = row[1].strip() if row[1] else ""
    except Exception as e:
        print(f"❌ Error leyendo tabla colores: {e}")
    return colores


def extraer_colores_sinonimos(marca: int = None) -> list:
    """
    Extrae pares (cod_color, descripcion_4, cantidad) de los sinónimos.

    Si marca se especifica, filtra solo esa marca.
    Retorna lista de dicts con: cod_color, descripcion_4, cantidad.
    """
    filtro_marca = f"AND a.marca = {marca}" if marca else ""

    sql = f"""
        SELECT
            SUBSTRING(a.codigo_sinonimo, 9, 2) AS cod_color,
            RTRIM(LTRIM(a.descripcion_4)) AS descripcion_4,
            COUNT(*) AS cantidad
        FROM msgestion01art.dbo.articulo a
        WHERE a.subrubro > 0
          AND a.codigo_sinonimo IS NOT NULL
          AND LEN(a.codigo_sinonimo) = 12
          AND a.descripcion_4 IS NOT NULL
          AND a.descripcion_4 <> ''
          {filtro_marca}
        GROUP BY SUBSTRING(a.codigo_sinonimo, 9, 2), RTRIM(LTRIM(a.descripcion_4))
        ORDER BY cod_color, cantidad DESC
    """

    resultados = []
    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for row in cursor.fetchall():
                resultados.append({
                    "cod_color": row[0],
                    "descripcion_4": row[1].strip() if row[1] else "",
                    "cantidad": row[2],
                })
    except Exception as e:
        print(f"❌ Error extrayendo colores de sinónimos: {e}")

    return resultados


def analizar_y_reconstruir(marca: int = None, dry_run: bool = True):
    """
    Flujo principal:
    1. Lee colores actuales
    2. Extrae colores de sinónimos
    3. Determina color dominante por código
    4. Compara con tabla actual
    5. Genera SQL de actualización
    """
    print(f"\n{'='*65}")
    print(f"  RECONSTRUCCIÓN DE TABLA COLORES")
    if marca:
        print(f"  Filtro: marca = {marca}")
    print(f"  Modo: {'DRY RUN' if dry_run else 'EJECUCIÓN REAL'}")
    print(f"{'='*65}")

    # 1. Colores actuales
    colores_actuales = obtener_colores_actuales()
    print(f"\n📋 Colores en tabla actual: {len(colores_actuales)}")

    # 2. Extraer de sinónimos
    datos = extraer_colores_sinonimos(marca)
    if not datos:
        print("❌ No se encontraron datos en sinónimos.")
        return
    print(f"📋 Pares (cod_color, descripcion_4) encontrados: {len(datos)}")

    # 3. Agrupar: para cada cod_color, todas las descripcion_4 con su frecuencia
    agrupado = defaultdict(list)
    for d in datos:
        agrupado[d["cod_color"]].append((d["descripcion_4"], d["cantidad"]))

    print(f"📋 Códigos de color distintos en sinónimos: {len(agrupado)}")

    # 4. Analizar cada código
    codigos_ok = []          # existen en tabla y coinciden
    codigos_faltantes = []   # no existen en tabla colores
    codigos_inconsistentes = []  # existen pero con nombre diferente
    codigos_ambiguos = []    # un código apunta a muchos colores distintos

    print(f"\n{'─'*65}")
    print(f"  {'Cód':>3} {'En tabla':<20} {'En sinónimos (+ frecuente)':<25} {'Arts':>5} {'Variantes':>4} {'Estado'}")
    print(f"  {'─'*62}")

    for cod_str in sorted(agrupado.keys()):
        variantes = agrupado[cod_str]
        # Ordenar por frecuencia descendente
        variantes.sort(key=lambda x: x[1], reverse=True)

        color_dominante = variantes[0][0]
        total_arts = sum(v[1] for v in variantes)
        num_variantes = len(variantes)

        cod_num = int(cod_str)
        en_tabla = colores_actuales.get(cod_num, None)

        # Limpiar para comparación: quitar espacios, barra, etc.
        dom_limpio = color_dominante.split("/")[0].strip().upper()

        if en_tabla is None:
            estado = "FALTA"
            codigos_faltantes.append({
                "codigo": cod_num,
                "denominacion": color_dominante,
                "total_arts": total_arts,
                "variantes": num_variantes,
            })
        elif en_tabla.strip().upper() == dom_limpio or en_tabla.strip().upper() in color_dominante.upper():
            estado = "OK"
            codigos_ok.append(cod_num)
        else:
            estado = "DIFERENTE"
            codigos_inconsistentes.append({
                "codigo": cod_num,
                "en_tabla": en_tabla,
                "en_sinonimos": color_dominante,
                "total_arts": total_arts,
            })

        if num_variantes > 5:
            codigos_ambiguos.append({
                "codigo": cod_num,
                "color_dominante": color_dominante,
                "variantes": num_variantes,
                "total_arts": total_arts,
            })

        en_tabla_str = en_tabla if en_tabla else "—"
        print(f"  {cod_str:>3} {en_tabla_str:<20} {color_dominante:<25} {total_arts:>5} {num_variantes:>4}   {estado}")

    # 5. Resumen
    print(f"\n{'='*65}")
    print(f"  RESUMEN")
    print(f"{'='*65}")
    print(f"  Códigos OK (coinciden)     : {len(codigos_ok)}")
    print(f"  Códigos FALTANTES en tabla : {len(codigos_faltantes)}")
    print(f"  Códigos con nombre DIFERENTE: {len(codigos_inconsistentes)}")
    print(f"  Códigos muy AMBIGUOS (>5 variantes): {len(codigos_ambiguos)}")

    # 6. Generar SQL
    if codigos_faltantes:
        print(f"\n{'─'*65}")
        print(f"  SQL PARA INSERTAR CÓDIGOS FALTANTES ({len(codigos_faltantes)}):")
        print(f"{'─'*65}")
        for cf in codigos_faltantes:
            denominacion = cf["denominacion"][:25]  # max 25 chars
            sql = (f"INSERT INTO colores (codigo, denominacion, codigo_interno) "
                   f"VALUES ({cf['codigo']}, '{denominacion}', {cf['codigo']});")
            print(f"  {sql}")
            print(f"    -- {cf['total_arts']} artículos, {cf['variantes']} variantes")

    if codigos_inconsistentes:
        print(f"\n{'─'*65}")
        print(f"  INCONSISTENCIAS (código existe pero nombre no coincide):")
        print(f"{'─'*65}")
        for ci in codigos_inconsistentes:
            print(f"  Código {ci['codigo']:>2}: tabla='{ci['en_tabla']}' vs sinónimos='{ci['en_sinonimos']}' ({ci['total_arts']} arts)")

    if codigos_ambiguos:
        print(f"\n{'─'*65}")
        print(f"  CÓDIGOS AMBIGUOS (muchas variantes de descripcion_4):")
        print(f"{'─'*65}")
        for ca in codigos_ambiguos:
            print(f"  Código {ca['codigo']:>2}: '{ca['color_dominante']}' pero {ca['variantes']} variantes distintas ({ca['total_arts']} arts)")
            # Mostrar top 5 variantes
            variantes = agrupado[str(ca['codigo']).zfill(2)]
            for v_desc, v_cant in variantes[:5]:
                print(f"      {v_cant:>5}x  {v_desc}")

    # 7. Ejecutar si no es dry_run
    if not dry_run and codigos_faltantes:
        print(f"\n🚨 Insertando {len(codigos_faltantes)} colores faltantes...")
        try:
            with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
                cursor = conn.cursor()
                for cf in codigos_faltantes:
                    denominacion = cf["denominacion"][:25]
                    cursor.execute(
                        "INSERT INTO msgestionC.dbo.colores (codigo, denominacion, codigo_interno) VALUES (?, ?, ?)",
                        cf["codigo"], denominacion, cf["codigo"]
                    )
                    print(f"  ✅ Insertado: {cf['codigo']} = {denominacion}")
                conn.commit()
                print(f"\n✅ {len(codigos_faltantes)} colores insertados correctamente.")
        except Exception as e:
            print(f"❌ Error insertando colores: {e}")

    print(f"\n{'='*65}\n")

    return {
        "ok": codigos_ok,
        "faltantes": codigos_faltantes,
        "inconsistentes": codigos_inconsistentes,
        "ambiguos": codigos_ambiguos,
    }


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconstrucción tabla colores desde sinónimos")
    parser.add_argument("--marca", type=int, default=None,
                        help="Filtrar por marca (ej: 314 para Topper)")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--ejecutar", action="store_true", default=False)

    args = parser.parse_args()
    dry_run = not args.ejecutar

    analizar_y_reconstruir(marca=args.marca, dry_run=dry_run)
