#!/usr/bin/env python3
"""
auto_markup.py — Sistema automático de actualización de precios
================================================================
Reemplaza la tarea manual de Mariana de actualizar precios en el ERP.

Qué hace:
  1. Lee todos los artículos vigentes (estado='V') con precio_fabrica > 0
  2. Para cada artículo, busca las reglas de pricing del proveedor (config.py o DB)
  3. Recalcula precio_costo y precio_1..4 según las utilidades configuradas
  4. Compara contra los precios actuales en el ERP
  5. Genera UPDATE para los que difieren (tolerancia configurable)

Modos:
  python auto_markup.py                     # Análisis: muestra qué cambiaría
  python auto_markup.py --dry-run           # Igual que arriba
  python auto_markup.py --ejecutar          # Aplica los UPDATEs en producción
  python auto_markup.py --proveedor 668     # Solo artículos de un proveedor
  python auto_markup.py --marca 314         # Solo artículos de una marca
  python auto_markup.py --tolerancia 5      # Solo cambios > 5% (default: 1%)
  python auto_markup.py --csv               # Exporta análisis a CSV

IMPORTANTE:
  - Corre en 111 (producción) o 112 (con pyodbc al 111)
  - UPDATE va directo a msgestion01art.dbo.articulo (tabla compartida)
  - Proveedores con utilidad_1 = 0 (ej: GTN) se saltan (pricing manual)
"""

import sys
import os
import csv
import socket
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pyodbc

# ── Conexión ──
_hostname = socket.gethostname().upper()
if _hostname in ("DELL-SVR", "DELLSVR"):
    SERVIDOR = "localhost"
else:
    SERVIDOR = "192.168.2.111"

CONN_STR = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={SERVIDOR};"
    f"DATABASE=msgestion01art;"
    f"UID=am;PWD=dl;"
    f"TrustServerCertificate=yes;Encrypt=no;"
)

# Tolerancia default: solo actualizar si la diferencia es > 1%
TOLERANCIA_PCT = 1.0

# Proveedores a saltear (pricing manual o sin utilidades configuradas)
SKIP_PROVEEDORES = set()


def cargar_reglas_pricing():
    """
    Carga las reglas de pricing desde config.py PROVEEDORES dict.
    Retorna {proveedor_id: {descuento, utilidad_1..4, formula, ...}}
    """
    try:
        from config import PROVEEDORES
    except ImportError:
        print("WARN: No se pudo importar config.py, usando solo reglas de DB")
        return {}

    reglas = {}
    for prov_id, prov in PROVEEDORES.items():
        # Saltear proveedores sin utilidades (pricing manual)
        if prov.get("utilidad_1", 0) == 0 and prov.get("utilidad_2", 0) == 0:
            SKIP_PROVEEDORES.add(prov_id)
            continue

        reglas[prov_id] = {
            "nombre": prov.get("nombre", f"PROV {prov_id}"),
            "descuento": prov.get("descuento", 0),
            "utilidad_1": prov.get("utilidad_1", 0),
            "utilidad_2": prov.get("utilidad_2", 0),
            "utilidad_3": prov.get("utilidad_3", 0),
            "utilidad_4": prov.get("utilidad_4", 0),
            "formula": prov.get("formula", 1),
            "descuento_1": prov.get("descuento_1", 0),
            "descuento_2": prov.get("descuento_2", 0),
        }
    return reglas


def obtener_regla_db(cursor, proveedor_id):
    """
    Fallback: obtener pricing del artículo más reciente de este proveedor.
    """
    cursor.execute("""
        SELECT TOP 1
            descuento, utilidad_1, utilidad_2, utilidad_3, utilidad_4,
            formula, descuento_1, descuento_2
        FROM articulo
        WHERE proveedor = ? AND estado = 'V' AND precio_fabrica > 0
        ORDER BY codigo DESC
    """, proveedor_id)
    row = cursor.fetchone()
    if not row:
        return None

    util1 = row.utilidad_1 or 0
    util2 = row.utilidad_2 or 0
    if util1 == 0 and util2 == 0:
        return None

    return {
        "nombre": f"PROV {proveedor_id} (DB)",
        "descuento": row.descuento or 0,
        "utilidad_1": util1,
        "utilidad_2": util2,
        "utilidad_3": row.utilidad_3 or 0,
        "utilidad_4": row.utilidad_4 or 0,
        "formula": row.formula or 1,
        "descuento_1": row.descuento_1 or 0,
        "descuento_2": row.descuento_2 or 0,
    }


def calcular_precios(precio_fabrica, regla):
    """Calcula la cadena completa de precios."""
    desc = regla["descuento"]
    precio_costo = round(precio_fabrica * (1 - desc / 100), 4)

    return {
        "precio_costo": round(precio_costo, 2),
        "precio_1": round(precio_costo * (1 + regla["utilidad_1"] / 100), 2),
        "precio_2": round(precio_costo * (1 + regla["utilidad_2"] / 100), 2),
        "precio_3": round(precio_costo * (1 + regla["utilidad_3"] / 100), 2),
        "precio_4": round(precio_costo * (1 + regla["utilidad_4"] / 100), 2),
    }


def diff_pct(actual, esperado):
    """Porcentaje de diferencia entre valor actual y esperado."""
    if esperado == 0:
        return 0 if actual == 0 else 100
    return abs(actual - esperado) / esperado * 100


def main():
    # ── Parse args ──
    dry_run = "--ejecutar" not in sys.argv
    filtro_prov = None
    filtro_marca = None
    tolerancia = TOLERANCIA_PCT
    exportar_csv = "--csv" in sys.argv

    for i, arg in enumerate(sys.argv):
        if arg == "--proveedor" and i + 1 < len(sys.argv):
            filtro_prov = int(sys.argv[i + 1])
        if arg == "--marca" and i + 1 < len(sys.argv):
            filtro_marca = int(sys.argv[i + 1])
        if arg == "--tolerancia" and i + 1 < len(sys.argv):
            tolerancia = float(sys.argv[i + 1])

    print("=" * 80)
    print(f"AUTO MARKUP — Actualización automática de precios")
    print(f"Modo: {'DRY RUN (análisis)' if dry_run else 'EJECUCION REAL'}")
    print(f"Tolerancia: {tolerancia}% (solo cambios mayores)")
    if filtro_prov:
        print(f"Filtro proveedor: {filtro_prov}")
    if filtro_marca:
        print(f"Filtro marca: {filtro_marca}")
    print(f"Servidor: {SERVIDOR}")
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)

    # ── Cargar reglas ──
    reglas = cargar_reglas_pricing()
    print(f"\nReglas cargadas de config.py: {len(reglas)} proveedores")
    if SKIP_PROVEEDORES:
        print(f"Proveedores saltados (sin utilidades): {sorted(SKIP_PROVEEDORES)}")

    # ── Conectar ──
    print(f"\nConectando a {SERVIDOR}...")
    conn = pyodbc.connect(CONN_STR, timeout=15)
    cursor = conn.cursor()

    # ── Query artículos ──
    where_clauses = ["a.estado = 'V'", "a.precio_fabrica > 0"]
    params = []

    if filtro_prov:
        where_clauses.append("a.proveedor = ?")
        params.append(filtro_prov)
    if filtro_marca:
        where_clauses.append("a.marca = ?")
        params.append(filtro_marca)

    # Excluir marcas de gastos
    where_clauses.append("a.marca NOT IN (1316, 1317, 1158, 436)")

    sql = f"""
        SELECT a.codigo, a.descripcion_1, a.proveedor, a.marca,
               a.precio_fabrica, a.precio_costo,
               a.precio_1, a.precio_2, a.precio_3, a.precio_4,
               a.descuento, a.utilidad_1, a.utilidad_2, a.utilidad_3, a.utilidad_4,
               a.formula
        FROM articulo a
        WHERE {' AND '.join(where_clauses)}
        ORDER BY a.proveedor, a.codigo
    """
    cursor.execute(sql, params)
    articulos = cursor.fetchall()
    print(f"Artículos vigentes encontrados: {len(articulos)}")

    # ── Analizar ──
    cambios = []
    sin_regla = set()
    proveedores_vistos = set()
    cache_reglas_db = {}

    for art in articulos:
        prov_id = int(art.proveedor or 0)
        if prov_id == 0 or prov_id in SKIP_PROVEEDORES:
            continue

        proveedores_vistos.add(prov_id)

        # Buscar regla: primero config.py, luego DB
        regla = reglas.get(prov_id)
        if not regla:
            if prov_id not in cache_reglas_db:
                cache_reglas_db[prov_id] = obtener_regla_db(cursor, prov_id)
            regla = cache_reglas_db[prov_id]
        if not regla:
            sin_regla.add(prov_id)
            continue

        precio_fab = float(art.precio_fabrica or 0)
        if precio_fab <= 0:
            continue

        # Calcular precios correctos
        esperado = calcular_precios(precio_fab, regla)

        # Comparar con actual
        actual = {
            "precio_costo": float(art.precio_costo or 0),
            "precio_1": float(art.precio_1 or 0),
            "precio_2": float(art.precio_2 or 0),
            "precio_3": float(art.precio_3 or 0),
            "precio_4": float(art.precio_4 or 0),
        }

        # Verificar si hay diferencia significativa
        max_diff = max(
            diff_pct(actual["precio_costo"], esperado["precio_costo"]),
            diff_pct(actual["precio_1"], esperado["precio_1"]),
            diff_pct(actual["precio_2"], esperado["precio_2"]),
            diff_pct(actual["precio_3"], esperado["precio_3"]),
            diff_pct(actual["precio_4"], esperado["precio_4"]),
        )

        if max_diff > tolerancia:
            cambios.append({
                "codigo": art.codigo,
                "descripcion": (art.descripcion_1 or "").strip()[:50],
                "proveedor": prov_id,
                "marca": int(art.marca or 0),
                "precio_fabrica": precio_fab,
                "actual": actual,
                "esperado": esperado,
                "max_diff_pct": round(max_diff, 1),
                "regla_fuente": "config" if prov_id in reglas else "DB",
            })

    # ── Resultados ──
    print(f"\nProveedores analizados: {len(proveedores_vistos)}")
    if sin_regla:
        print(f"Proveedores sin regla (no se tocan): {len(sin_regla)}")
    print(f"Artículos que necesitan actualización: {len(cambios)}")

    if not cambios:
        print("\nTodos los precios están correctos. Nada que actualizar.")
        conn.close()
        return

    # Agrupar por proveedor
    from collections import defaultdict
    por_prov = defaultdict(list)
    for c in cambios:
        por_prov[c["proveedor"]].append(c)

    print(f"\n{'='*80}")
    print(f"DETALLE DE CAMBIOS ({len(cambios)} artículos)")
    print(f"{'='*80}")

    for prov_id in sorted(por_prov.keys()):
        items = por_prov[prov_id]
        nombre = reglas.get(prov_id, {}).get("nombre", f"PROV {prov_id}")
        print(f"\n--- Proveedor {prov_id}: {nombre} ({len(items)} arts) ---")
        print(f"{'Codigo':>8} {'Descripcion':50} {'P.Fab':>9} {'P1.Act':>9} {'P1.Esp':>9} {'Diff%':>6}")

        for c in items[:20]:  # max 20 por prov en pantalla
            print(f"{c['codigo']:>8} {c['descripcion']:50} "
                  f"{c['precio_fabrica']:>9,.0f} "
                  f"{c['actual']['precio_1']:>9,.0f} "
                  f"{c['esperado']['precio_1']:>9,.0f} "
                  f"{c['max_diff_pct']:>5.1f}%")
        if len(items) > 20:
            print(f"  ... y {len(items) - 20} más")

    # ── Resumen impacto ──
    print(f"\n{'='*80}")
    print("RESUMEN POR PROVEEDOR")
    print(f"{'Proveedor':>8} {'Nombre':30} {'Arts':>6} {'Cambio P1 prom':>15}")
    print("-" * 65)
    for prov_id in sorted(por_prov.keys()):
        items = por_prov[prov_id]
        nombre = reglas.get(prov_id, {}).get("nombre",
                 cache_reglas_db.get(prov_id, {}).get("nombre", f"PROV {prov_id}"))
        cambio_promedio = sum(
            c['esperado']['precio_1'] - c['actual']['precio_1'] for c in items
        ) / len(items)
        signo = "+" if cambio_promedio > 0 else ""
        print(f"{prov_id:>8} {nombre[:30]:30} {len(items):>6} {signo}${cambio_promedio:>12,.0f}")

    # ── Exportar CSV ──
    if exportar_csv:
        csv_path = os.path.join(os.path.dirname(__file__), '..', '_informes',
                                f'auto_markup_{datetime.now().strftime("%Y%m%d")}.csv')
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['codigo', 'descripcion', 'proveedor', 'marca',
                           'precio_fabrica', 'p_costo_act', 'p_costo_esp',
                           'p1_act', 'p1_esp', 'p2_act', 'p2_esp',
                           'p3_act', 'p3_esp', 'p4_act', 'p4_esp',
                           'max_diff_pct', 'fuente_regla'])
            for c in cambios:
                writer.writerow([
                    c['codigo'], c['descripcion'], c['proveedor'], c['marca'],
                    c['precio_fabrica'],
                    c['actual']['precio_costo'], c['esperado']['precio_costo'],
                    c['actual']['precio_1'], c['esperado']['precio_1'],
                    c['actual']['precio_2'], c['esperado']['precio_2'],
                    c['actual']['precio_3'], c['esperado']['precio_3'],
                    c['actual']['precio_4'], c['esperado']['precio_4'],
                    c['max_diff_pct'], c['regla_fuente'],
                ])
        print(f"\nCSV exportado: {csv_path}")

    # ── Ejecutar o dry run ──
    if dry_run:
        print(f"\n[DRY RUN] No se aplicó ningún cambio.")
        print(f"Para ejecutar: python auto_markup.py --ejecutar")
        if not exportar_csv:
            print(f"Para exportar CSV: python auto_markup.py --csv")
        conn.close()
        return

    # ── EJECUCION REAL ──
    print(f"\n{'!'*80}")
    print(f"APLICANDO {len(cambios)} UPDATES en msgestion01art.dbo.articulo...")
    print(f"{'!'*80}")

    resp = input(f"Confirmar? (S/N): ").strip().upper()
    if resp != 'S':
        print("Cancelado.")
        conn.close()
        return

    update_sql = """
        UPDATE articulo
        SET precio_costo = ?,
            precio_1 = ?,
            precio_2 = ?,
            precio_3 = ?,
            precio_4 = ?,
            precio_sugerido = ?
        WHERE codigo = ?
    """

    updated = 0
    errores = 0
    for c in cambios:
        try:
            e = c['esperado']
            cursor.execute(update_sql, (
                e['precio_costo'],
                e['precio_1'],
                e['precio_2'],
                e['precio_3'],
                e['precio_4'],
                e['precio_costo'],  # precio_sugerido = precio_costo
                c['codigo'],
            ))
            updated += 1
        except Exception as ex:
            print(f"  ERROR art {c['codigo']}: {ex}")
            errores += 1

    conn.commit()
    print(f"\nActualización completada:")
    print(f"  Actualizados: {updated}")
    print(f"  Errores:      {errores}")
    print(f"  Total:        {len(cambios)}")

    conn.close()


if __name__ == '__main__':
    main()
