# -*- coding: utf-8 -*-
"""
REVALUACION Y LIQUIDACION DE STOCK MUERTO
==========================================
Compara productos sin ventas contra la piramide de precios de productos ACTIVOS
del mismo segmento (marca+rubro) para determinar su valor de mercado real.

Uso:
    python3 revaluar_stock_muerto.py                # Genera reporte completo
    python3 revaluar_stock_muerto.py --dryrun       # Solo muestra, no graba nada
    python3 revaluar_stock_muerto.py --csv           # Exporta CSV
    python3 revaluar_stock_muerto.py --wa            # Envia resumen por WhatsApp

Ejecutar desde Mac (usa MCP/pyodbc al 111 para consultas).
"""
import sys
import os
import json
import datetime
from collections import defaultdict

# Agregar path raiz para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Config conexion
try:
    from config import get_connection
    USE_PYODBC = True
except ImportError:
    USE_PYODBC = False

# ─── CONFIGURACION ──────────────────────────────────────────────────
MESES_SIN_VENTA_MINIMO = 6   # Para considerar "muerto"
STOCK_MINIMO = 3              # Unidades minimas para considerar
MARCAS_EXCLUIR = (1316, 1317, 1158, 436)  # Gastos
DEPOSITOS = '0,1,2,3,4,5,6,7,8,9,11,12,14,15,198'

# Factores de ajuste
FACTOR_ANTIGUEDAD = {
    'reciente': 1.0,      # < 6 meses
    '1_temporada': 0.92,  # 6-12 meses
    '2_temporadas': 0.85, # 12-18 meses
    'viejo': 0.75,        # > 18 meses
}
FACTOR_CURVA_ROTA = 0.80    # Si le faltan talles centrales (38-42)
FACTOR_CONTRAESTACION = 0.90 # Producto OI en PV o viceversa
FACTOR_BCG = {
    'ESTRELLA': 1.05,
    'VACA': 1.0,
    'INTERROGACION': 0.95,
    'PERRO': 0.85,
}
PISO_SOBRE_COSTO = 0.60  # Nunca vender debajo del 60% del costo real
DESCUENTO_LIQUIDACION = 0.30  # 30% off sobre valor de mercado


def get_db_connection():
    """Obtiene conexion a SQL Server 111."""
    if USE_PYODBC:
        return get_connection()
    else:
        # Alternativa: crear conexion directa
        import pyodbc
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=192.168.2.111,1433;"
            "UID=am;PWD=dl;"
            "TrustServerCertificate=yes;"
        )
        return pyodbc.connect(conn_str)


def query_db(conn, sql):
    """Ejecuta query y retorna lista de dicts."""
    cursor = conn.cursor()
    cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED")
    cursor.execute(sql)
    columns = [col[0] for col in cursor.description]
    rows = []
    for row in cursor.fetchall():
        rows.append(dict(zip(columns, row)))
    return rows


# ─── PASO 1: PIRAMIDE DE PRECIOS DE MERCADO ─────────────────────────
def construir_piramide(conn):
    """
    Construye piramide de precios de productos ACTIVOS con ventas recientes.
    Agrupa por marca+rubro y calcula percentiles.
    """
    print("[1/5] Construyendo piramide de precios de mercado...")

    sql = """
    SELECT a.marca, m.descripcion as marca_nombre, a.rubro, r.descripcion as rubro_nombre,
           a.precio_1
    FROM msgestion01art.dbo.articulo a WITH (NOLOCK)
    LEFT JOIN msgestionC.dbo.marcas m WITH (NOLOCK) ON m.codigo = a.marca
    LEFT JOIN msgestionC.dbo.rubros r WITH (NOLOCK) ON r.codigo = a.rubro
    WHERE a.estado = 'V' AND a.precio_1 > 1000
      AND a.marca NOT IN (%s)
    ORDER BY a.marca, a.rubro, a.precio_1
    """ % ','.join(str(m) for m in MARCAS_EXCLUIR)

    rows = query_db(conn, sql)

    # Agrupar por marca+rubro
    piramide = defaultdict(lambda: {
        'precios': [], 'marca_nombre': '', 'rubro_nombre': ''
    })

    for r in rows:
        key = (r['marca'], r['rubro'])
        piramide[key]['precios'].append(float(r['precio_1']))
        piramide[key]['marca_nombre'] = (r['marca_nombre'] or '').strip()
        piramide[key]['rubro_nombre'] = (r['rubro_nombre'] or '').strip()

    # Calcular estadisticas
    resultado = {}
    for key, data in piramide.items():
        precios = sorted(data['precios'])
        n = len(precios)
        if n < 3:
            continue
        resultado[key] = {
            'marca': key[0],
            'rubro': key[1],
            'marca_nombre': data['marca_nombre'],
            'rubro_nombre': data['rubro_nombre'],
            'n': n,
            'p25': precios[n // 4],
            'mediana': precios[n // 2],
            'p75': precios[3 * n // 4],
            'promedio': sum(precios) / n,
            'min': precios[0],
            'max': precios[-1],
        }

    print("  %d segmentos marca+rubro con datos de mercado" % len(resultado))
    return resultado


# ─── PASO 2: STOCK MUERTO ───────────────────────────────────────────
def obtener_stock_muerto(conn):
    """
    Articulos con stock > STOCK_MINIMO y 0 ventas en 12 meses.
    Incluye sinonimo, talle, color para formato zapatero.
    """
    print("[2/5] Identificando stock muerto...")

    sql = """
    SELECT s_agg.articulo, a.descripcion_1,
           LTRIM(RTRIM(ISNULL(a.codigo_sinonimo,''))) as sinonimo,
           a.descripcion_5 as talle, a.descripcion_2 as color_desc,
           a.marca, m.descripcion as marca_nombre,
           a.rubro, r.descripcion as rubro_nombre,
           a.precio_costo, a.precio_fabrica, a.precio_1 as precio_actual,
           a.utilidad_1,
           a.fecha_ult_compra,
           s_agg.stock_total
    FROM (SELECT s.articulo, SUM(s.stock_actual) as stock_total
          FROM msgestionC.dbo.stock s WITH (NOLOCK)
          WHERE s.deposito IN (%s)
          GROUP BY s.articulo HAVING SUM(s.stock_actual) > %d) s_agg
    JOIN msgestion01art.dbo.articulo a WITH (NOLOCK) ON a.codigo = s_agg.articulo
    LEFT JOIN msgestionC.dbo.marcas m WITH (NOLOCK) ON m.codigo = a.marca
    LEFT JOIN msgestionC.dbo.rubros r WITH (NOLOCK) ON r.codigo = a.rubro
    LEFT JOIN (SELECT DISTINCT v.articulo FROM msgestionC.dbo.ventas1 v WITH (NOLOCK)
               WHERE v.codigo NOT IN (7,36) AND v.cantidad > 0
               AND v.fecha >= DATEADD(MONTH, -12, GETDATE())) vtas ON vtas.articulo = s_agg.articulo
    WHERE vtas.articulo IS NULL
      AND a.marca NOT IN (%s)
    ORDER BY a.marca, LTRIM(RTRIM(a.codigo_sinonimo))
    """ % (DEPOSITOS, STOCK_MINIMO, ','.join(str(m) for m in MARCAS_EXCLUIR))

    rows = query_db(conn, sql)

    # Clasificar y filtrar
    clean = []
    fantasmas = []
    recientes = []
    anomalias_precio = 0

    hoy = datetime.date.today()

    for r in rows:
        pc = float(r.get('precio_costo') or 0)
        p1 = float(r.get('precio_actual') or 0)

        # Anomalia de precio
        if pc > 500000 or p1 > 500000:
            anomalias_precio += 1
            continue

        # Clasificar por fecha de compra
        fc = r.get('fecha_ult_compra')
        if fc:
            try:
                if isinstance(fc, str):
                    fc_date = datetime.datetime.strptime(fc[:10], '%Y-%m-%d').date()
                else:
                    fc_date = fc.date() if hasattr(fc, 'date') else fc
                meses = (hoy.year - fc_date.year) * 12 + (hoy.month - fc_date.month)
            except:
                meses = 999  # sin fecha = viejo
        else:
            meses = 999

        r['meses_desde_compra'] = meses
        r['categoria'] = 'LIQUIDAR'

        # Compra < 6 meses = NO es muerto, es nuevo
        if meses < 6:
            r['categoria'] = 'RECIENTE'
            recientes.append(r)
            continue

        # Compra > 60 meses (5 años) o sin fecha = FANTASMA
        if meses > 60 or meses == 999:
            r['categoria'] = 'FANTASMA'
            fantasmas.append(r)
            continue

        clean.append(r)

    print("  (!) %d anomalias de precio excluidas" % anomalias_precio)
    print("  (!) %d articulos RECIENTES (<6m) excluidos — no son muertos" % len(recientes))
    print("  (!) %d articulos FANTASMA (>5 años) — probablemente no existen fisicamente" % len(fantasmas))
    print("  %d articulos REALES para liquidar" % len(clean))
    return clean, fantasmas, recientes


# ─── PASO 3: CLASIFICACION BCG POR MARCA ────────────────────────────
def obtener_bcg_marcas(conn):
    """Clasificacion BCG simplificada por marca."""
    print("[3/5] Obteniendo clasificacion BCG por marca...")

    sql = """
    SELECT a.marca,
           SUM(v.total_item) as venta_12m,
           SUM(v.precio_costo * v.cantidad) as costo_12m,
           SUM(v.cantidad) as uds_12m
    FROM msgestionC.dbo.ventas1 v WITH (NOLOCK)
    JOIN msgestion01art.dbo.articulo a WITH (NOLOCK) ON a.codigo = v.articulo
    WHERE v.fecha >= DATEADD(MONTH, -12, GETDATE())
      AND v.codigo NOT IN (7, 36) AND v.cantidad > 0
      AND a.marca NOT IN (%s)
    GROUP BY a.marca
    HAVING SUM(v.total_item) > 100000
    """ % ','.join(str(m) for m in MARCAS_EXCLUIR)

    rows = query_db(conn, sql)

    # Stock por marca
    sql_stock = """
    SELECT a.marca, SUM(s.stock_actual) as stock_total
    FROM msgestionC.dbo.stock s WITH (NOLOCK)
    JOIN msgestion01art.dbo.articulo a WITH (NOLOCK) ON a.codigo = s.articulo
    WHERE s.deposito IN (%s) AND a.marca NOT IN (%s)
    GROUP BY a.marca
    """ % (DEPOSITOS, ','.join(str(m) for m in MARCAS_EXCLUIR))

    stock_rows = query_db(conn, sql_stock)
    stock_map = {r['marca']: float(r['stock_total'] or 0) for r in stock_rows}

    # Calcular margen y rotacion
    margenes = []
    rotaciones = []
    marca_data = {}

    for r in rows:
        marca = r['marca']
        vta = float(r['venta_12m'] or 0)
        costo = float(r['costo_12m'] or 0)
        uds = float(r['uds_12m'] or 0)
        stock = stock_map.get(marca, 0)

        margen = (vta - costo) / vta if vta > 0 else 0
        rotacion = uds / stock if stock > 0 else 0

        margenes.append(margen)
        rotaciones.append(rotacion)
        marca_data[marca] = {'margen': margen, 'rotacion': rotacion}

    # Medianas para clasificar
    margenes.sort()
    rotaciones.sort()
    med_margen = margenes[len(margenes) // 2] if margenes else 0.5
    med_rotacion = rotaciones[len(rotaciones) // 2] if rotaciones else 2.0

    bcg = {}
    for marca, d in marca_data.items():
        if d['margen'] >= med_margen and d['rotacion'] >= med_rotacion:
            bcg[marca] = 'ESTRELLA'
        elif d['margen'] >= med_margen:
            bcg[marca] = 'VACA'
        elif d['rotacion'] >= med_rotacion:
            bcg[marca] = 'INTERROGACION'
        else:
            bcg[marca] = 'PERRO'

    print("  %d marcas clasificadas (med_margen=%.1f%%, med_rot=%.1fx)" % (
        len(bcg), med_margen * 100, med_rotacion))
    return bcg


# ─── PASO 4: REVALUACION ────────────────────────────────────────────
def revaluar(stock_muerto, piramide, bcg_marcas):
    """
    Aplica la ecuacion de revaluacion a cada articulo muerto.
    Retorna lista de propuestas agrupadas por modelo.
    """
    print("[4/5] Revaluando %d articulos..." % len(stock_muerto))

    hoy = datetime.date.today()
    mes_actual = hoy.month
    # OI = abril-septiembre, PV = octubre-marzo
    estamos_en_oi = 4 <= mes_actual <= 9

    modelos = defaultdict(lambda: {
        'items': [], 'marca': '', 'marca_nombre': '', 'rubro': '', 'rubro_nombre': '',
        'descripcion': '', 'stock_total': 0, 'capital_actual': 0,
        'valor_mercado_total': 0, 'precio_liq_total': 0, 'talles': {},
    })

    for art in stock_muerto:
        marca = art['marca']
        rubro = art['rubro']
        sin = str(art.get('sinonimo', '')).strip()
        modelo_key = sin[:-4] if len(sin) >= 5 else (sin or str(art['articulo']))

        precio_actual = float(art.get('precio_actual') or 0)
        precio_costo = float(art.get('precio_costo') or 0)
        stock = float(art.get('stock_total') or 0)
        talle = str(art.get('talle') or '00').strip()

        # --- Buscar precio de mercado en piramide ---
        precio_mercado = None

        # Nivel 1: misma marca + mismo rubro
        key = (marca, rubro)
        if key in piramide:
            precio_mercado = piramide[key]['mediana']

        # Nivel 2: misma marca (cualquier rubro)
        if precio_mercado is None:
            for (m, r), data in piramide.items():
                if m == marca:
                    precio_mercado = data['mediana']
                    break

        # Nivel 3: mismo rubro (cualquier marca)
        if precio_mercado is None:
            precios_rubro = [d['mediana'] for (m, r), d in piramide.items() if r == rubro]
            if precios_rubro:
                precio_mercado = sum(precios_rubro) / len(precios_rubro)

        # Nivel 4: fallback al precio actual
        if precio_mercado is None or precio_mercado <= 0:
            precio_mercado = precio_actual if precio_actual > 0 else precio_costo * 2

        # --- Factores de ajuste ---

        # Antiguedad (por fecha ultima compra)
        fecha_compra = art.get('fecha_ult_compra')
        if fecha_compra:
            try:
                if isinstance(fecha_compra, str):
                    fc = datetime.datetime.strptime(fecha_compra[:10], '%Y-%m-%d').date()
                else:
                    fc = fecha_compra.date() if hasattr(fecha_compra, 'date') else fecha_compra
                meses_desde_compra = (hoy.year - fc.year) * 12 + (hoy.month - fc.month)
            except:
                meses_desde_compra = 18
        else:
            meses_desde_compra = 18

        if meses_desde_compra > 18:
            f_ant = FACTOR_ANTIGUEDAD['viejo']
        elif meses_desde_compra > 12:
            f_ant = FACTOR_ANTIGUEDAD['2_temporadas']
        elif meses_desde_compra > 6:
            f_ant = FACTOR_ANTIGUEDAD['1_temporada']
        else:
            f_ant = FACTOR_ANTIGUEDAD['reciente']

        # BCG de la marca
        bcg_clase = bcg_marcas.get(marca, 'INTERROGACION')
        f_bcg = FACTOR_BCG.get(bcg_clase, 1.0)

        # Contraestacion (simplificado: si es calzado cerrado en PV o sandalia en OI)
        rubro_nombre = str(art.get('rubro_nombre') or '').upper()
        desc = str(art.get('descripcion_1') or '').upper()
        es_invierno = any(w in desc for w in ['BOTA', 'BORCEGO', 'ABRIG', 'POLAR', 'FRIZA'])
        es_verano = any(w in desc for w in ['SANDAL', 'OJOTA', 'CHINELA', 'SLIPPER'])
        f_estacion = 1.0
        if (es_invierno and not estamos_en_oi) or (es_verano and estamos_en_oi):
            f_estacion = FACTOR_CONTRAESTACION

        # --- Calcular valor de mercado ajustado ---
        valor_mercado = precio_mercado * f_ant * f_bcg * f_estacion

        # --- Precio de liquidacion ---
        precio_liq = valor_mercado * (1 - DESCUENTO_LIQUIDACION)

        # Piso: nunca debajo del X% del costo
        piso = precio_costo * PISO_SOBRE_COSTO if precio_costo > 0 else 0
        if piso > 0 and precio_liq < piso:
            precio_liq = piso

        # Si el precio actual ya es razonable (< valor_mercado * 0.8), no bajar mas
        if precio_actual > 0 and precio_actual <= valor_mercado * 0.85:
            precio_liq = max(precio_liq, precio_actual)

        # --- Agrupar por modelo ---
        m = modelos[modelo_key]
        m['marca'] = marca
        m['marca_nombre'] = str(art.get('marca_nombre') or '').strip()
        m['rubro'] = rubro
        m['rubro_nombre'] = str(art.get('rubro_nombre') or '').strip()
        m['descripcion'] = str(art.get('descripcion_1') or '').strip()
        m['bcg'] = bcg_clase
        m['stock_total'] += stock
        m['capital_actual'] += stock * precio_actual
        m['valor_mercado_total'] += stock * valor_mercado
        m['precio_liq_total'] += stock * precio_liq
        m['precio_mercado'] = valor_mercado
        m['precio_liquidacion'] = precio_liq
        m['precio_actual_unitario'] = precio_actual
        m['meses_desde_compra'] = meses_desde_compra
        m['factores'] = 'ant=%.2f bcg=%s(%.2f) est=%.2f' % (f_ant, bcg_clase, f_bcg, f_estacion)

        if talle not in m['talles']:
            m['talles'][talle] = 0
        m['talles'][talle] += int(stock)
        m['items'].append(art)

    # Convertir a lista ordenada por capital
    resultado = []
    for modelo_key, m in modelos.items():
        m['modelo'] = modelo_key
        m['recupero_estimado'] = m['precio_liq_total']
        m['diferencia_vs_actual'] = m['precio_liq_total'] - m['capital_actual']
        m['pct_cambio'] = ((m['precio_liquidacion'] / m['precio_actual_unitario'] - 1) * 100
                           if m['precio_actual_unitario'] > 0 else 0)
        resultado.append(m)

    resultado.sort(key=lambda x: x['capital_actual'], reverse=True)
    print("  %d modelos revaluados" % len(resultado))
    return resultado


# ─── PASO 5: REPORTE ────────────────────────────────────────────────
def generar_reporte(propuestas):
    """Genera reporte legible."""
    print("[5/5] Generando reporte...\n")

    total_stock = sum(p['stock_total'] for p in propuestas)
    total_capital = sum(p['capital_actual'] for p in propuestas)
    total_mercado = sum(p['valor_mercado_total'] for p in propuestas)
    total_recupero = sum(p['precio_liq_total'] for p in propuestas)

    print("=" * 70)
    print("REVALUACION STOCK MUERTO — %s" % datetime.date.today().strftime('%d/%m/%Y'))
    print("=" * 70)
    print()
    print("RESUMEN EJECUTIVO")
    print("-" * 40)
    print("  Modelos muertos:     %d" % len(propuestas))
    print("  Pares totales:       %s" % format(int(total_stock), ','))
    print("  Capital a precio actual:  $%s" % format(int(total_capital), ','))
    print("  Valor de mercado:         $%s" % format(int(total_mercado), ','))
    print("  Recupero por liquidacion: $%s" % format(int(total_recupero), ','))
    print("  Diferencia:               $%s" % format(int(total_recupero - total_capital), ','))
    print()

    # Top 20 por capital
    print("TOP 20 MODELOS POR CAPITAL INMOVILIZADO")
    print("-" * 70)
    print("%-12s %-25s %6s %12s %12s %7s %s" % (
        'Marca', 'Descripcion', 'Pares', 'Precio Actual', 'Precio Liq', 'Cambio', 'BCG'))
    print("-" * 70)

    for p in propuestas[:20]:
        desc = p['descripcion'][:25]
        marca = p['marca_nombre'][:12]
        print("%-12s %-25s %6d %12s %12s %+6.0f%% %s" % (
            marca, desc,
            int(p['stock_total']),
            '$' + format(int(p['precio_actual_unitario']), ','),
            '$' + format(int(p['precio_liquidacion']), ','),
            p['pct_cambio'],
            p['bcg'],
        ))

    return {
        'total_modelos': len(propuestas),
        'total_pares': int(total_stock),
        'capital_actual': int(total_capital),
        'valor_mercado': int(total_mercado),
        'recupero_liquidacion': int(total_recupero),
    }


def exportar_csv(propuestas, filename='stock_muerto_revaluado.csv'):
    """Exporta propuestas a CSV."""
    import csv
    filepath = os.path.join(os.path.dirname(__file__), '..', '_informes', filename)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Modelo', 'Marca', 'Descripcion', 'Rubro', 'BCG',
                     'Pares', 'Precio_Actual', 'Precio_Mercado', 'Precio_Liquidacion',
                     'Cambio_%', 'Capital_Actual', 'Recupero_Est', 'Factores', 'Talles'])
        for p in propuestas:
            talles_str = ' | '.join('%s:%d' % (t, s) for t, s in sorted(p['talles'].items()))
            w.writerow([
                p['modelo'], p['marca_nombre'], p['descripcion'], p['rubro_nombre'], p['bcg'],
                int(p['stock_total']), int(p['precio_actual_unitario']),
                int(p['precio_mercado']), int(p['precio_liquidacion']),
                '%.0f%%' % p['pct_cambio'],
                int(p['capital_actual']), int(p['precio_liq_total']),
                p['factores'], talles_str,
            ])
    print("\nCSV exportado: %s" % filepath)


def enviar_wa_resumen(resumen):
    """Envia resumen por WhatsApp a Fernando."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '_sync_tools', 'task_manager'))
    from meta_whatsapp import enviar_texto

    msg = """REVALUACION STOCK MUERTO — %s

%d modelos / %s pares muertos

Capital a precio actual: $%s
Valor de mercado real: $%s
Recupero estimado: $%s

Queres ver el detalle? Responde "si" y te mando el top 10.""" % (
        datetime.date.today().strftime('%d/%m/%Y'),
        resumen['total_modelos'],
        format(resumen['total_pares'], ','),
        format(resumen['capital_actual'], ','),
        format(resumen['valor_mercado'], ','),
        format(resumen['recupero_liquidacion'], ','),
    )

    r = enviar_texto('5493462672330', msg)
    print("\nWhatsApp enviado: %s" % ('OK' if r.get('ok') else r.get('error', 'error')))


# ─── MAIN ────────────────────────────────────────────────────────────
def main():
    dryrun = '--dryrun' in sys.argv
    exportar = '--csv' in sys.argv
    wa = '--wa' in sys.argv

    print("REVALUACION STOCK MUERTO")
    print("Fecha: %s" % datetime.date.today())
    print("Modo: %s\n" % ('DRY RUN' if dryrun else 'COMPLETO'))

    conn = get_db_connection()

    # Paso 1-3: Datos
    piramide = construir_piramide(conn)
    stock_muerto_raw = obtener_stock_muerto(conn)
    stock_liquidar, fantasmas, recientes = stock_muerto_raw
    bcg = obtener_bcg_marcas(conn)

    # Reporte fantasmas
    if fantasmas:
        n_fantasma = len(fantasmas)
        pares_fantasma = sum(float(f.get('stock_total', 0)) for f in fantasmas)
        print("\n  STOCK FANTASMA: %d articulos, %d pares" % (n_fantasma, int(pares_fantasma)))
        print("  Estos articulos tienen >5 años sin compra y 0 ventas.")
        print("  MUY PROBABLE que no existan fisicamente. Candidatos a dar de BAJA.\n")

    if recientes:
        n_rec = len(recientes)
        pares_rec = sum(float(f.get('stock_total', 0)) for f in recientes)
        print("  STOCK RECIENTE: %d articulos, %d pares (excluidos del analisis)\n" % (n_rec, int(pares_rec)))

    # Paso 4: Revaluar solo los reales
    propuestas = revaluar(stock_liquidar, piramide, bcg)

    # Paso 5: Reportar
    resumen = generar_reporte(propuestas)

    if exportar:
        exportar_csv(propuestas)

    if wa:
        enviar_wa_resumen(resumen)

    # Guardar JSON para la vista web
    json_path = os.path.join(os.path.dirname(__file__), '..', '_informes', 'stock_muerto_revaluado.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        # Limpiar items (no serializable) antes de guardar
        export = []
        for p in propuestas:
            e = {k: v for k, v in p.items() if k != 'items'}
            export.append(e)
        json.dump(export, f, ensure_ascii=False, indent=2, default=str)
    print("\nJSON guardado: %s" % json_path)

    conn.close()
    print("\nListo. %d modelos procesados." % len(propuestas))


if __name__ == '__main__':
    main()
