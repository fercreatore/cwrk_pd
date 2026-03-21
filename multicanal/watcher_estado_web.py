# -*- coding: utf-8 -*-
"""
Watcher de estado_web — Publica automáticamente en TiendaNube artículos
marcados con estado_web='A' en el ERP.

Flujo:
  1. Consulta artículos con estado_web='A' en msgestion01art
  2. Compara contra publicaciones.db (SQLite) para encontrar los nuevos
  3. Para los nuevos: llama publicar_producto_nuevo() para publicar en TN
  4. Para los ya publicados: sincroniza stock y precio si cambiaron
  5. Registra todo en publicaciones.db

El campo estado_web tiene estos valores en el ERP:
  - 'A' = Activo para web (10,372 artículos) → PUBLICAR
  - 'V' = Visible (65,409 artículos) → no publicar (futuro?)
  - NULL = sin estado web (283,565 artículos)

USO:
    # Dry run — muestra qué publicaría sin hacer nada
    python -m multicanal.watcher_estado_web --dry-run

    # Ejecutar una vez
    python -m multicanal.watcher_estado_web

    # Loop cada 10 minutos
    python -m multicanal.watcher_estado_web --loop

    # Solo un CSR específico
    python -m multicanal.watcher_estado_web --csr 272220004835 --dry-run
"""

import json
import os
import sqlite3
import sys
import time
import pyodbc
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multicanal.tiendanube import TiendaNubeClient, cargar_config
from multicanal.precios import calcular_precio_canal, cargar_reglas, REGLAS_DEFAULT
from multicanal.imagenes import imagenes_para_tn, urls_producto

# ── Config ──

ERP_CONN_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion01art;"
    "UID=am;PWD=dl;"
    "Encrypt=no;"
)

SQLITE_DB = os.path.join(os.path.dirname(__file__), 'publicaciones.db')
REGLAS_FILE = os.path.join(os.path.dirname(__file__), 'reglas_canales.json')
LOOP_INTERVAL = 600  # 10 minutos


# ── SQLite: registro de publicaciones ──

def _init_db(conn):
    """Crea tablas si no existen (idempotente)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS publicaciones_tn (
            codigo_sinonimo TEXT PRIMARY KEY,
            codigo_erp INTEGER,
            descripcion TEXT,
            product_id_tn INTEGER,
            precio_tn REAL,
            stock_tn INTEGER,
            fecha_publicacion TEXT,
            fecha_sync TEXT,
            estado TEXT DEFAULT 'publicado'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS log_watcher (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            accion TEXT,
            codigo_sinonimo TEXT,
            detalle TEXT
        )
    """)
    conn.commit()


def _get_db():
    conn = sqlite3.connect(SQLITE_DB)
    _init_db(conn)
    return conn


def obtener_publicados() -> dict:
    """Retorna {codigo_sinonimo: row_dict} de todo lo ya publicado en TN."""
    conn = _get_db()
    cursor = conn.execute(
        "SELECT codigo_sinonimo, codigo_erp, product_id_tn, precio_tn, stock_tn "
        "FROM publicaciones_tn WHERE estado = 'publicado'"
    )
    resultado = {}
    for row in cursor.fetchall():
        resultado[row[0]] = {
            'codigo_sinonimo': row[0],
            'codigo_erp': row[1],
            'product_id_tn': row[2],
            'precio_tn': row[3],
            'stock_tn': row[4],
        }
    conn.close()
    return resultado


def registrar_publicacion(csr, codigo_erp, descripcion, product_id_tn,
                          precio_tn, stock_tn):
    """Registra un producto publicado en TN."""
    conn = _get_db()
    conn.execute("""
        INSERT OR REPLACE INTO publicaciones_tn
        (codigo_sinonimo, codigo_erp, descripcion, product_id_tn,
         precio_tn, stock_tn, fecha_publicacion, fecha_sync, estado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'publicado')
    """, (csr, codigo_erp, descripcion, product_id_tn,
          precio_tn, stock_tn,
          datetime.now().isoformat(), datetime.now().isoformat()))
    conn.commit()
    conn.close()


def registrar_sync(csr, precio_tn, stock_tn):
    """Actualiza fecha de último sync."""
    conn = _get_db()
    conn.execute("""
        UPDATE publicaciones_tn
        SET precio_tn = ?, stock_tn = ?, fecha_sync = ?
        WHERE codigo_sinonimo = ?
    """, (precio_tn, stock_tn, datetime.now().isoformat(), csr))
    conn.commit()
    conn.close()


def log_accion(accion, csr, detalle):
    """Registra una acción en el log."""
    conn = _get_db()
    conn.execute(
        "INSERT INTO log_watcher (timestamp, accion, codigo_sinonimo, detalle) "
        "VALUES (?, ?, ?, ?)",
        (datetime.now().isoformat(), accion, csr, detalle)
    )
    conn.commit()
    conn.close()


# ── Consultas ERP ──

def obtener_articulos_web(conn_erp, estado_web='A', csr_filtro=None) -> list:
    """
    Obtiene artículos con estado_web dado, agrupados por producto_base
    (primeros 10 chars del codigo_sinonimo = un modelo/color).

    Retorna lista de dicts, un registro por variante (talle).
    """
    where_extra = ""
    params = []

    if csr_filtro:
        # Filtrar por CSR específico o por producto_base (primeros 10)
        if len(csr_filtro) > 10:
            where_extra = "AND a.codigo_sinonimo = ?"
            params = [csr_filtro]
        else:
            where_extra = "AND a.codigo_sinonimo LIKE ? + '%'"
            params = [csr_filtro]
    else:
        where_extra = "AND a.estado_web = ?"
        params = [estado_web]

    cursor = conn_erp.cursor()
    cursor.execute(f"""
        SELECT a.codigo, a.descripcion_1, a.precio_costo, a.precio_venta,
               a.codigo_sinonimo, a.moneda, a.marca, a.estado, a.estado_web,
               m.denominacion AS marca_nombre,
               ISNULL(s.stock_total, 0) AS stock
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN msgestion01art.dbo.marca m ON m.codigo = a.marca
        LEFT JOIN (
            SELECT articulo, SUM(stock_actual) AS stock_total
            FROM msgestionC.dbo.stock
            WHERE deposito IN (0, 1)
            GROUP BY articulo
        ) s ON s.articulo = a.codigo
        WHERE a.codigo_sinonimo IS NOT NULL
          AND a.codigo_sinonimo <> ''
          AND a.estado IN ('V', 'U')
          {where_extra}
        ORDER BY a.codigo_sinonimo
    """, params)

    cols = ['codigo', 'descripcion', 'precio_costo', 'precio_venta',
            'codigo_sinonimo', 'moneda', 'marca', 'estado', 'estado_web',
            'marca_nombre', 'stock']

    resultado = []
    for row in cursor.fetchall():
        d = {}
        for i, col in enumerate(cols):
            val = row[i]
            if isinstance(val, str):
                val = val.strip()
            d[col] = val
        d['stock'] = int(d['stock'] or 0)
        d['precio_costo'] = float(d['precio_costo'] or 0)
        d['precio_venta'] = float(d['precio_venta'] or 0)
        d['moneda'] = int(d['moneda'] or 0)
        resultado.append(d)

    return resultado


def agrupar_por_modelo(articulos: list) -> dict:
    """
    Agrupa artículos por producto_base (primeros 10 chars del CSR).
    Cada grupo = un producto en TN con variantes por talle.

    Retorna {producto_base: [articulos]}.
    """
    grupos = {}
    for art in articulos:
        csr = art.get('codigo_sinonimo', '')
        if len(csr) < 10:
            continue
        base = csr[:10]
        if base not in grupos:
            grupos[base] = []
        grupos[base].append(art)
    return grupos


# ── Publicación en TN ──

def publicar_modelo_tn(client, articulos: list, regla_tn, dry_run=True) -> dict:
    """
    Publica un modelo (grupo de variantes/talles) como un producto en TN.

    Args:
        client: TiendaNubeClient
        articulos: lista de dicts del mismo producto_base (diferentes talles)
        regla_tn: ReglaCanal para TiendaNube
        dry_run: si True, solo muestra sin publicar

    Returns:
        dict con resultado de la publicación
    """
    if not articulos:
        return {'ok': False, 'error': 'Sin artículos'}

    # Tomar datos del primer artículo como referencia
    ref = articulos[0]
    csr_base = ref['codigo_sinonimo'][:10]

    # Nombre: usar descripción sin el sufijo de talle
    nombre = ref['descripcion']
    # Limpiar talle del nombre si está incluido
    csr_full = ref['codigo_sinonimo']
    if len(csr_full) > 10:
        talle_suffix = csr_full[10:]
        for suffix in [f' T{talle_suffix}', f' {talle_suffix}']:
            if nombre.endswith(suffix):
                nombre = nombre[:-len(suffix)]
                break

    # Calcular precio
    costo = ref['precio_costo']
    if ref['moneda'] == 1:
        costo = costo * 1170.0  # TODO: parametrizar cotización USD

    precio_calc = calcular_precio_canal(costo, regla_tn)
    if 'error' in precio_calc:
        return {'ok': False, 'error': f"Error pricing: {precio_calc['error']}",
                'csr': csr_base}

    precio_tn = precio_calc['precio_venta']

    # Armar variantes (una por talle)
    variantes_tn = []
    stock_total = 0
    for art in articulos:
        stock = max(art['stock'], 0)
        stock_total += stock
        csr = art['codigo_sinonimo']
        talle = csr[10:] if len(csr) > 10 else ''

        variante = {
            'price': str(precio_tn),
            'stock': stock,
            'sku': csr,
        }
        if talle:
            variante['values'] = [{'es': f'Talle {talle}'}]
        variantes_tn.append(variante)

    # Obtener imágenes
    try:
        imagenes = imagenes_para_tn(csr_base)
    except Exception:
        imagenes = []

    # Armar payload
    payload = {
        'name': {'es': nombre},
        'published': True,
        'variants': variantes_tn,
    }
    if imagenes:
        payload['images'] = imagenes

    resultado = {
        'ok': True,
        'dry_run': dry_run,
        'csr_base': csr_base,
        'nombre': nombre,
        'variantes': len(variantes_tn),
        'stock_total': stock_total,
        'precio_tn': precio_tn,
        'margen_real': precio_calc.get('margen_real', 0),
        'imagenes': len(imagenes),
        'payload': payload,
    }

    if dry_run:
        return resultado

    # Publicar en TN
    try:
        resp = client.crear_producto(
            nombre=nombre,
            variantes=variantes_tn,
            images=imagenes if imagenes else None,
        )
        resultado['product_id_tn'] = resp.get('id')
        resultado['url_tn'] = resp.get('canonical_url', '')

        # Registrar en SQLite
        for art in articulos:
            registrar_publicacion(
                csr=art['codigo_sinonimo'],
                codigo_erp=art['codigo'],
                descripcion=art['descripcion'],
                product_id_tn=resp.get('id'),
                precio_tn=precio_tn,
                stock_tn=max(art['stock'], 0),
            )
        log_accion('publicar', csr_base,
                   f"OK product_id={resp.get('id')} vars={len(variantes_tn)} "
                   f"stock={stock_total} precio=${precio_tn:,.0f}")
    except Exception as e:
        resultado['ok'] = False
        resultado['error'] = str(e)
        log_accion('error_publicar', csr_base, str(e))

    return resultado


def sync_producto_existente(client, pub_info: dict, articulos: list,
                            regla_tn, dry_run=True) -> dict:
    """
    Sincroniza stock y precio de un producto ya publicado en TN.

    Compara stock y precio actual del ERP con lo registrado en publicaciones.db.
    Solo actualiza si hay diferencia.
    """
    product_id = pub_info['product_id_tn']
    csr_base = pub_info['codigo_sinonimo'][:10]

    # Recalcular precio
    ref = articulos[0]
    costo = ref['precio_costo']
    if ref.get('moneda') == 1:
        costo = costo * 1170.0

    precio_calc = calcular_precio_canal(costo, regla_tn)
    if 'error' in precio_calc:
        return {'ok': False, 'error': precio_calc['error']}

    precio_nuevo = precio_calc['precio_venta']
    stock_nuevo = sum(max(a['stock'], 0) for a in articulos)

    precio_cambio = abs(precio_nuevo - (pub_info.get('precio_tn') or 0)) > 1
    stock_cambio = stock_nuevo != (pub_info.get('stock_tn') or 0)

    if not precio_cambio and not stock_cambio:
        return {'ok': True, 'sin_cambio': True, 'csr_base': csr_base}

    resultado = {
        'ok': True,
        'dry_run': dry_run,
        'csr_base': csr_base,
        'product_id_tn': product_id,
        'precio_anterior': pub_info.get('precio_tn'),
        'precio_nuevo': precio_nuevo,
        'stock_anterior': pub_info.get('stock_tn'),
        'stock_nuevo': stock_nuevo,
        'precio_cambio': precio_cambio,
        'stock_cambio': stock_cambio,
    }

    if dry_run:
        return resultado

    # Actualizar en TN — necesitamos los variant_ids reales
    try:
        prod_tn = client.obtener_producto(product_id)
        for var in prod_tn.get('variants', []):
            sku = (var.get('sku') or '').strip()
            # Buscar el artículo ERP correspondiente
            art_match = next((a for a in articulos
                              if a['codigo_sinonimo'] == sku), None)
            if art_match:
                stock_var = max(art_match['stock'], 0)
                client.actualizar_variante(
                    product_id, var['id'],
                    precio=precio_nuevo if precio_cambio else None,
                    stock=stock_var if stock_cambio else None,
                )

        # Registrar sync
        for art in articulos:
            registrar_sync(art['codigo_sinonimo'], precio_nuevo, max(art['stock'], 0))

        log_accion('sync', csr_base,
                   f"precio={'$'+str(int(precio_nuevo)) if precio_cambio else 'sin cambio'} "
                   f"stock={stock_nuevo if stock_cambio else 'sin cambio'}")

    except Exception as e:
        resultado['ok'] = False
        resultado['error'] = str(e)
        log_accion('error_sync', csr_base, str(e))

    return resultado


# ── Flujo principal ──

def ejecutar_watcher(dry_run=True, csr_filtro=None, cotiz_usd=1170.0) -> dict:
    """
    Flujo principal del watcher.

    1. Lee artículos con estado_web='A' del ERP
    2. Agrupa por modelo (producto_base)
    3. Para cada modelo:
       - Si no está publicado en TN → publicar
       - Si ya está publicado → sync stock/precio
    """
    modo = "DRY RUN" if dry_run else "REAL"
    print(f"\n{'='*60}")
    print(f"  WATCHER ESTADO_WEB → TiendaNube [{modo}]")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if csr_filtro:
        print(f"  Filtro CSR: {csr_filtro}")
    print(f"{'='*60}\n")

    # Cargar regla de pricing TN
    reglas = cargar_reglas(REGLAS_FILE)
    regla_tn = reglas.get('tiendanube', REGLAS_DEFAULT.get('tiendanube'))

    # Inicializar cliente TN (necesario para publicar y sync)
    config = cargar_config()
    client = None
    if config.get('store_id') and config.get('access_token'):
        client = TiendaNubeClient(
            store_id=config['store_id'],
            access_token=config['access_token'],
        )
    elif not dry_run:
        print("ERROR: No hay config de TiendaNube para modo REAL.")
        return {'error': 'Sin config TN'}

    # 1. Leer artículos del ERP
    print("[1/4] Leyendo artículos con estado_web='A' del ERP...")
    conn_erp = pyodbc.connect(ERP_CONN_STRING, timeout=15)
    try:
        articulos = obtener_articulos_web(conn_erp, csr_filtro=csr_filtro)
    finally:
        conn_erp.close()
    print(f"       {len(articulos)} variantes encontradas.\n")

    if not articulos:
        print("  No hay artículos para procesar.")
        return {'total_variantes': 0, 'modelos': 0, 'nuevos': 0, 'sync': 0}

    # 2. Agrupar por modelo
    print("[2/4] Agrupando por modelo (producto_base)...")
    grupos = agrupar_por_modelo(articulos)
    print(f"       {len(grupos)} modelos únicos.\n")

    # 3. Comparar con publicaciones existentes
    print("[3/4] Comparando con publicaciones registradas...")
    publicados = obtener_publicados()

    modelos_nuevos = []
    modelos_sync = []

    for base, arts in grupos.items():
        # Verificar si alguna variante ya está publicada
        pub = None
        for art in arts:
            if art['codigo_sinonimo'] in publicados:
                pub = publicados[art['codigo_sinonimo']]
                break

        if pub:
            modelos_sync.append((base, arts, pub))
        else:
            modelos_nuevos.append((base, arts))

    print(f"       {len(modelos_nuevos)} modelos NUEVOS para publicar")
    print(f"       {len(modelos_sync)} modelos para SYNC stock/precio\n")

    # 4. Procesar
    print(f"[4/4] Procesando...")
    resultados_nuevos = []
    resultados_sync = []
    errores = []

    # 4a. Publicar nuevos
    if modelos_nuevos:
        print(f"\n  --- NUEVOS ({len(modelos_nuevos)}) ---")
        for base, arts in modelos_nuevos:
            ref = arts[0]
            stock_total = sum(max(a['stock'], 0) for a in arts)
            print(f"\n  [{base}] {ref['descripcion'][:40]} | "
                  f"{len(arts)} var | stock:{stock_total}")

            res = publicar_modelo_tn(client, arts, regla_tn, dry_run=dry_run)
            resultados_nuevos.append(res)

            if res.get('ok'):
                if dry_run:
                    print(f"    [DRY] ${res['precio_tn']:,.0f} | "
                          f"margen {res.get('margen_real',0)}% | "
                          f"{res.get('imagenes',0)} fotos")
                else:
                    print(f"    [OK]  product_id={res.get('product_id_tn')} | "
                          f"${res['precio_tn']:,.0f}")
            else:
                print(f"    [ERR] {res.get('error')}")
                errores.append(res)

    # 4b. Sync existentes
    if modelos_sync:
        print(f"\n  --- SYNC ({len(modelos_sync)}) ---")
        cambios = 0
        sin_cambio = 0
        for base, arts, pub in modelos_sync:
            res = sync_producto_existente(client, pub, arts, regla_tn,
                                         dry_run=dry_run)
            resultados_sync.append(res)

            if res.get('sin_cambio'):
                sin_cambio += 1
                continue

            cambios += 1
            if res.get('ok'):
                detalles = []
                if res.get('precio_cambio'):
                    detalles.append(f"${res['precio_anterior']:,.0f}→${res['precio_nuevo']:,.0f}")
                if res.get('stock_cambio'):
                    detalles.append(f"stock {res['stock_anterior']}→{res['stock_nuevo']}")
                estado = "[DRY]" if dry_run else "[OK] "
                print(f"  {estado} [{base}] {' | '.join(detalles)}")
            else:
                print(f"  [ERR] [{base}] {res.get('error')}")
                errores.append(res)

        print(f"  {sin_cambio} sin cambio, {cambios} actualizados")

    # Resumen
    print(f"\n{'='*60}")
    print(f"  RESUMEN {'(DRY RUN)' if dry_run else ''}")
    print(f"{'='*60}")
    print(f"  Variantes ERP:       {len(articulos)}")
    print(f"  Modelos únicos:      {len(grupos)}")
    print(f"  Nuevos publicados:   {len(resultados_nuevos)}")
    print(f"  Sync stock/precio:   {len(resultados_sync)}")
    if errores:
        print(f"  Errores:             {len(errores)}")
    print(f"{'='*60}\n")

    return {
        'total_variantes': len(articulos),
        'modelos': len(grupos),
        'nuevos': len(resultados_nuevos),
        'sync': len(resultados_sync),
        'errores': len(errores),
        'resultados_nuevos': resultados_nuevos,
        'resultados_sync': resultados_sync,
    }


def loop_watcher(dry_run=True, intervalo=LOOP_INTERVAL):
    """Ejecuta el watcher en loop cada N segundos."""
    print(f"Watcher iniciado — ejecutando cada {intervalo}s ({intervalo//60} min)")
    print(f"Modo: {'DRY RUN' if dry_run else 'REAL'}")
    print(f"Ctrl+C para detener.\n")

    while True:
        try:
            ejecutar_watcher(dry_run=dry_run)
        except Exception as e:
            print(f"[ERROR] {datetime.now().isoformat()} — {e}")
            log_accion('error_loop', '', str(e))

        print(f"Próxima ejecución en {intervalo}s...")
        time.sleep(intervalo)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Watcher estado_web → TiendaNube')
    parser.add_argument('--dry-run', action='store_true', default=False,
                        help='Solo mostrar qué haría sin publicar')
    parser.add_argument('--loop', action='store_true', default=False,
                        help='Ejecutar en loop cada 10 min')
    parser.add_argument('--csr', type=str, default=None,
                        help='Filtrar por codigo_sinonimo específico')
    parser.add_argument('--intervalo', type=int, default=LOOP_INTERVAL,
                        help='Intervalo en segundos para --loop (default: 600)')
    args = parser.parse_args()

    if args.loop:
        loop_watcher(dry_run=args.dry_run, intervalo=args.intervalo)
    else:
        ejecutar_watcher(dry_run=args.dry_run, csr_filtro=args.csr)
