"""
Analizador de demanda: cruza señales con catálogo y genera oportunidades.

Lee demanda_señales de los últimos N días, cruza con:
- Stock actual (ERP/PG)
- Si tiene foto (producto_imagenes PG)
- Si está publicado en TN (tn_mapping.db)

Genera ranking de oportunidades con acción sugerida.

USO:
    python3 -m multicanal.analizar_demanda --dias 30
    python3 -m multicanal.analizar_demanda --dias 7 --top 10
"""

import argparse
import os
import sqlite3

import psycopg2

from multicanal.demanda_db import consultar_top, consultar_sin_atender, stats, DB_PATH
from multicanal.imagenes import PG_CONN_STRING

MAPPING_DB = os.path.join(os.path.dirname(__file__), 'tn_mapping.db')


def enriquecer_con_catalogo(señales):
    """Cruza señales de demanda con el estado actual del catálogo."""
    pg_conn = psycopg2.connect(PG_CONN_STRING)
    pg_cur = pg_conn.cursor()

    # Cargar mapping TN
    tn_publicados = set()
    if os.path.exists(MAPPING_DB):
        sq = sqlite3.connect(MAPPING_DB)
        for row in sq.execute("SELECT pg_producto_id FROM tn_mapping"):
            tn_publicados.add(row[0])
        sq.close()

    for s in señales:
        desc = s.get('producto_desc', '')
        if not desc:
            continue

        # Buscar en PG por descripción
        palabras = desc.split()[:3]
        where_parts = []
        params = []
        for w in palabras:
            if len(w) >= 3:
                where_parts.append("p.nombre_mg ILIKE %s")
                params.append(f"%{w}%")

        if not where_parts:
            continue

        pg_cur.execute(f"""
            SELECT p.id, p.nombre_mg, p.familia_id, p.imagen_principal,
                   p.activo, p.estado
            FROM productos p
            WHERE {' AND '.join(where_parts)}
            AND p.activo = true
            LIMIT 5
        """, params)

        matches = pg_cur.fetchall()

        if matches:
            pg_id, nombre, familia, imagen, activo, estado = matches[0]
            s['pg_id'] = pg_id
            s['pg_nombre'] = nombre
            s['pg_familia'] = familia

            # Tiene foto?
            pg_cur.execute("""
                SELECT COUNT(*) FROM producto_imagenes
                WHERE cod_familia = %s AND estado = 'activo'
            """, (familia,))
            s['tiene_foto_actual'] = pg_cur.fetchone()[0] > 0

            # Publicado en TN?
            s['publicado_tn_actual'] = pg_id in tn_publicados

            # Stock? (consultar variantes)
            talle = s.get('talle')
            if talle:
                pg_cur.execute("""
                    SELECT SUM(pvs.stock_actual)
                    FROM producto_variantes pv
                    JOIN producto_variante_stock pvs ON pvs.variante_id = pv.id
                    WHERE pv.producto_id = %s AND pv.talle = %s
                    AND pvs.stock_actual > 0
                """, (pg_id, talle))
            else:
                pg_cur.execute("""
                    SELECT SUM(pvs.stock_actual)
                    FROM producto_variantes pv
                    JOIN producto_variante_stock pvs ON pvs.variante_id = pv.id
                    WHERE pv.producto_id = %s AND pvs.stock_actual > 0
                """, (pg_id,))

            stock_row = pg_cur.fetchone()
            s['stock_actual'] = int(stock_row[0] or 0) if stock_row else 0
        else:
            s['pg_id'] = None
            s['pg_nombre'] = None
            s['tiene_foto_actual'] = None
            s['publicado_tn_actual'] = None
            s['stock_actual'] = None

    pg_conn.close()
    return señales


def clasificar_oportunidad(s):
    """Clasifica una señal enriquecida en tipo de oportunidad."""
    if s.get('pg_id') is None:
        return 'NO_MATCH', 'Producto no identificado en catálogo'

    stock = s.get('stock_actual', 0) or 0
    foto = s.get('tiene_foto_actual', False)
    publicado = s.get('publicado_tn_actual', False)

    if stock > 0 and foto and not publicado:
        return 'PUBLICAR_YA', 'Tiene stock + foto, solo falta publicar en TN'
    elif stock > 0 and not foto and not publicado:
        return 'FOTO_Y_PUBLICAR', 'Tiene stock, importar foto de DDG y publicar'
    elif stock > 0 and foto and publicado:
        return 'OK', 'Ya está publicado y con stock'
    elif stock == 0 and (foto or publicado):
        return 'REPONER', 'Publicado/con foto pero SIN stock → señal de compra'
    elif stock == 0 and not foto:
        return 'REPONER_Y_FOTO', 'Sin stock ni foto → reponer + foto + publicar'
    else:
        return 'REVISAR', 'Requiere revisión manual'


def generar_reporte(dias=30, top_n=20):
    """Genera el reporte de oportunidades."""
    print(f"\n{'='*70}")
    print(f"  REPORTE DE INTELIGENCIA DE DEMANDA")
    print(f"  Últimos {dias} días | Top {top_n}")
    print(f"{'='*70}\n")

    # Stats generales
    st = stats(dias)
    print(f"  Total señales: {st['total']}")
    if st['por_fuente']:
        print(f"  Por fuente: {st['por_fuente']}")
    if st['por_tipo']:
        print(f"  Por tipo: {st['por_tipo']}")
    print()

    if st['total'] == 0:
        print("  No hay señales registradas. Corré los colectores primero:")
        print("    python3 -m multicanal.colector_whatsapp --dias 7")
        print("    python3 -m multicanal.colector_tn --dias 7")
        return

    # Top productos demandados
    print(f"  {'─'*65}")
    print(f"  TOP {top_n} PRODUCTOS MÁS DEMANDADOS")
    print(f"  {'─'*65}\n")

    top = consultar_top(dias=dias, limit=top_n)
    top = enriquecer_con_catalogo(top)

    # Clasificar
    por_accion = {
        'PUBLICAR_YA': [],
        'FOTO_Y_PUBLICAR': [],
        'REPONER': [],
        'REPONER_Y_FOTO': [],
        'OK': [],
        'NO_MATCH': [],
        'REVISAR': [],
    }

    for s in top:
        accion, motivo = clasificar_oportunidad(s)
        s['accion'] = accion
        s['motivo'] = motivo
        por_accion[accion].append(s)

    # Imprimir por prioridad
    prioridades = [
        ('PUBLICAR_YA', '🟢 PUBLICAR YA (stock + foto, falta TN)'),
        ('FOTO_Y_PUBLICAR', '🟡 IMPORTAR FOTO + PUBLICAR (stock, sin foto)'),
        ('REPONER', '🔴 REPONER STOCK (publicado pero agotado)'),
        ('REPONER_Y_FOTO', '⚫ REPONER + FOTO (sin nada, pero demandado)'),
        ('OK', '✅ YA PUBLICADO (todo ok)'),
        ('NO_MATCH', '❓ NO IDENTIFICADO (revisar manualmente)'),
    ]

    for accion, titulo in prioridades:
        items = por_accion.get(accion, [])
        if not items:
            continue

        print(f"\n  {titulo} ({len(items)})")
        print(f"  {'─'*60}")

        for s in items:
            señales = s.get('señales', '?')
            desc = s.get('pg_nombre') or s.get('producto_desc', '?')
            talle = s.get('talle', '')
            stock = s.get('stock_actual', '?')
            fuentes = s.get('fuentes', '')

            talle_str = f" T:{talle}" if talle else ""
            stock_str = f" stk:{stock}" if stock is not None else ""
            print(f"    [{señales}x] {desc[:50]}{talle_str}{stock_str} | {fuentes}")

    # Resumen ejecutivo
    print(f"\n  {'='*65}")
    print(f"  RESUMEN EJECUTIVO")
    print(f"  {'='*65}")
    n_publicar = len(por_accion['PUBLICAR_YA'])
    n_foto = len(por_accion['FOTO_Y_PUBLICAR'])
    n_reponer = len(por_accion['REPONER']) + len(por_accion['REPONER_Y_FOTO'])
    n_ok = len(por_accion['OK'])

    if n_publicar:
        print(f"  → {n_publicar} productos listos para publicar en TN (tienen stock + foto)")
    if n_foto:
        print(f"  → {n_foto} productos necesitan foto (importar de DDG) y luego publicar")
    if n_reponer:
        print(f"  → {n_reponer} productos demandados SIN stock (señal de compra para Mati)")
    if n_ok:
        print(f"  → {n_ok} productos ya están bien publicados")

    if n_publicar > 0:
        print(f"\n  ACCIÓN INMEDIATA:")
        print(f"    python3 -m multicanal.watcher_estado_web --dry-run")
    if n_foto > 0:
        print(f"\n  IMPORTAR FOTOS:")
        for s in por_accion['FOTO_Y_PUBLICAR'][:5]:
            fam = s.get('pg_familia', '?')
            print(f"    python3 -m multicanal.importar_imagenes --familia {fam}")

    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analizador de demanda')
    parser.add_argument('--dias', type=int, default=30, help='Días hacia atrás')
    parser.add_argument('--top', type=int, default=20, help='Top N productos')
    args = parser.parse_args()

    generar_reporte(dias=args.dias, top_n=args.top)
