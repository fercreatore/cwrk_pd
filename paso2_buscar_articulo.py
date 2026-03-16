# paso2_buscar_articulo.py
# Módulo de búsqueda y alta de artículos.
#
# Funciones principales:
#   buscar_por_codigo(codigo)           → devuelve artículo o None
#   buscar_por_descripcion(desc, talle) → devuelve lista de candidatos
#   obtener_industria(subrubro)         → devuelve industria del agrupador
#   dar_de_alta(datos_articulo)         → inserta en articulo, devuelve nuevo código
#
# EJECUTAR: python paso2_buscar_articulo.py

import pyodbc
from config import CONN_ARTICULOS, CONN_ANALITICA, CONN_COMPRAS

# Normalización de talles (3 capas) — lazy import, no falla si no existen tablas
_resolver_talle_ok = False
try:
    from resolver_talle import talle_para_descripcion_5 as _tpd5
    _resolver_talle_ok = True
except ImportError:
    pass

# ──────────────────────────────────────────────────────────────
# BÚSQUEDA
# ──────────────────────────────────────────────────────────────

def buscar_por_codigo(codigo: int) -> dict | None:
    """
    Busca un artículo por código numérico.
    Retorna dict con datos del artículo o None si no existe.
    """
    # NOTA: marcas, lineas y subrubro con datos están en msgestionC, no en msgestion01art
    sql = """
        SELECT
            a.codigo, a.descripcion_1, a.codigo_sinonimo,
            a.descripcion_5,
            a.subrubro, a.marca, a.linea, a.rubro,
            m.descripcion AS nombre_marca,
            l.descripcion AS nombre_linea,
            s.descripcion AS nombre_subrubro
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN msgestionC.dbo.marcas m ON a.marca = m.codigo
        LEFT JOIN msgestionC.dbo.lineas l ON a.linea = l.codigo
        LEFT JOIN msgestionC.dbo.subrubro s ON a.subrubro = s.codigo
        WHERE a.codigo = ?
    """
    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, codigo)
            row = cursor.fetchone()
            if row:
                return {
                    "codigo": row[0],
                    "descripcion": row[1],
                    "codigo_sinonimo": row[2],
                    "talle": row[3],           # descripcion_5
                    "subrubro": row[4],
                    "marca": row[5],
                    "linea": row[6],
                    "rubro": row[7],
                    "nombre_marca": row[8],
                    "nombre_linea": row[9],
                    "nombre_subrubro": row[10],
                }
            return None
    except Exception as e:
        print(f"ERROR en buscar_por_codigo: {e}")
        return None


def buscar_por_descripcion(descripcion: str, talle: str = None) -> list:
    """
    Busca artículos por descripción (LIKE) y opcionalmente por talle (descripcion_5).
    Retorna lista de dicts. Si hay más de 10 resultados, pide que sea más específico.
    """
    # NOTA: marcas con datos están en msgestionC
    sql = """
        SELECT TOP 20
            a.codigo, a.descripcion_1, a.codigo_sinonimo,
            a.descripcion_5, a.subrubro, a.marca,
            m.descripcion AS nombre_marca
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN msgestionC.dbo.marcas m ON a.marca = m.codigo
        WHERE a.descripcion_1 LIKE ?
          AND a.subrubro > 0
    """
    params = [f"%{descripcion}%"]

    if talle:
        sql += " AND a.descripcion_5 = ?"
        params.append(talle)

    sql += " ORDER BY a.descripcion_1"

    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [
                {
                    "codigo": r[0],
                    "descripcion": r[1],
                    "codigo_sinonimo": r[2],
                    "talle": r[3],
                    "subrubro": r[4],
                    "marca": r[5],
                    "nombre_marca": r[6],
                }
                for r in rows
            ]
    except Exception as e:
        print(f"ERROR en buscar_por_descripcion: {e}")
        return []


def obtener_industria(subrubro: int) -> str:
    """
    Devuelve la industria de un subrubro según agrupador_subrubro.
    La tabla tiene estructura: (id, nombre, subrubros_codigo)
    donde subrubros_codigo es un VARCHAR con códigos separados por comas.
    Solo se consideran los agrupadores principales (id 1-5).
    """
    sql = "SELECT id, nombre, subrubros_codigo FROM agrupador_subrubro WHERE id <= 5 ORDER BY id"
    try:
        with pyodbc.connect(CONN_ANALITICA, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            for row in cursor.fetchall():
                # Parsear la lista de subrubros separados por coma
                subrubros_str = row[2] if row[2] else ""
                subrubros_lista = [int(s.strip()) for s in subrubros_str.split(",") if s.strip().isdigit()]
                if subrubro in subrubros_lista:
                    return row[1]  # nombre de la industria
            return "Sin clasificar"
    except Exception as e:
        print(f"ERROR en obtener_industria: {e}")
        return "Sin clasificar"


def buscar_por_codigo_sap(codigo_sap: str, talle: str = None) -> list:
    """
    Busca artículos por código SAP del proveedor.
    En la BD, descripcion_1 empieza con el código SAP (puede tener 0 adelante).
    Ej: código SAP 25860 → descripcion_1 = '025860 FAST 2.0 NEGRO/BLANCO...'

    Si se pasa talle, filtra por descripcion_5.
    Retorna lista de dicts (puede haber varios talles del mismo modelo).
    """
    cod = str(codigo_sap).strip().lstrip("0")
    # Buscar con y sin cero adelante
    sql = """
        SELECT TOP 50
            a.codigo, a.descripcion_1, a.codigo_sinonimo,
            a.descripcion_5, a.subrubro, a.marca, a.linea, a.rubro,
            m.descripcion AS nombre_marca
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN msgestionC.dbo.marcas m ON a.marca = m.codigo
        WHERE (a.descripcion_1 LIKE ? OR a.descripcion_1 LIKE ?)
          AND a.subrubro > 0
    """
    params = [f"0{cod} %", f"{cod} %"]

    if talle:
        sql += " AND a.descripcion_5 = ?"
        params.append(str(talle).strip())

    sql += " ORDER BY a.descripcion_5"

    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [
                {
                    "codigo": r[0],
                    "descripcion": r[1],
                    "codigo_sinonimo": r[2],
                    "talle": r[3],
                    "subrubro": r[4],
                    "marca": r[5],
                    "linea": r[6],
                    "rubro": r[7],
                    "nombre_marca": r[8],
                }
                for r in rows
            ]
    except Exception as e:
        print(f"ERROR en buscar_por_codigo_sap: {e}")
        return []


# ──────────────────────────────────────────────────────────────
# ALTA DE ARTÍCULO
# ──────────────────────────────────────────────────────────────

def dar_de_alta(datos: dict, dry_run: bool = True) -> int | None:
    """
    Inserta un nuevo artículo en msgestion01art.dbo.articulo.
    También inserta en msgestionC.dbo.articulos_prov (link proveedor-SKU).

    datos (dict) — campos obligatorios y opcionales:

    OBLIGATORIOS:
        descripcion_1   : str   — desc. principal (ej: "26903 SENDAI GRIS ZAPATILLA")
        codigo_sinonimo : str   — código sinónimo (ej: "668269031336")
        subrubro        : int   — categoría (47=Running, 49=Training, 55=Sneakers, etc.)
        marca           : int   — código de marca (ej: 314=TOPPER)
        linea           : int   — temporada (1=Verano, 2=Invierno, 3=Pre, 4=Atemp, 5=Cole, 6=Seg)

    PRICING (calculados con config.calcular_precios):
        precio_fabrica  : float — precio base del proveedor
        descuento       : float — % descuento proveedor (ej: 6 para Topper)
        precio_costo    : float — precio_fabrica × (1 - descuento/100)
        precio_1..4     : float — precios de venta (Contado, Lista, Intermedio, Mayorista)
        utilidad_1..4   : float — % markup sobre precio_costo
        precio_sugerido : float — ≈ precio_costo
        formula         : int   — código de fórmula de markup (1 = estándar)
        descuento_1     : float — descuento línea 1 (generalmente 0)
        descuento_2     : float — descuento línea 2 (generalmente 0)

    OPCIONALES:
        descripcion_3   : str   — SKU + modelo sin color (ej: "26903 SENDAI ZAPATILLA")
        descripcion_4   : str   — solo el color (ej: "GRIS MAGNET/NEGRO/ROSA PEAC")
        descripcion_5   : str   — talle (ej: "38")
        rubro           : int   — género (1=DAMAS, 3=HOMBRES, 4=NIÑOS, 5=NIÑAS, 6=UNISEX)
        grupo           : str   — material/tipo (ej: "15"=MACRAMÉ, "17"=TELA, "5"=PU)
        proveedor       : int   — código numérico del proveedor (ej: 668=ALPARGATAS)
        codigo_proveedor: str   — SKU del proveedor para articulos_prov (ej: "26903")
        moneda          : int   — moneda (0=pesos, por defecto)

    NOTA IMPORTANTE: El campo `codigo` de la tabla articulo NO es autoincremental.
    Se calcula como MAX(codigo) + 1 dentro de una transacción.

    Si dry_run=True, solo imprime el SQL sin ejecutar.
    Retorna el nuevo código del artículo o None si falla.
    """
    campos_requeridos = ["descripcion_1", "codigo_sinonimo", "subrubro", "marca", "linea"]
    for campo in campos_requeridos:
        if campo not in datos:
            print(f"❌ Falta campo requerido: {campo}")
            return None

    sql_insert = """
        INSERT INTO msgestion01art.dbo.articulo (
            codigo,
            descripcion_1, descripcion_3, descripcion_4, descripcion_5,
            codigo_sinonimo,
            subrubro, marca, linea, rubro, grupo,
            proveedor,
            precio_fabrica, descuento, descuento_1, descuento_2,
            precio_costo, precio_sugerido,
            utilidad_1, utilidad_2, utilidad_3, utilidad_4,
            precio_1, precio_2, precio_3, precio_4,
            formula, moneda,
            stock,
            estado, fecha_hora_creacion
        ) VALUES (
            ?,
            ?, ?, ?, ?,
            ?,
            ?, ?, ?, ?, ?,
            ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            'S',
            'V', GETDATE()
        )
    """

    sql_artprov = """
        INSERT INTO msgestionC.dbo.articulos_prov (codigo, proveedor, codigo_proveedor)
        VALUES (?, ?, ?)
    """

    if dry_run:
        desc1 = datos['descripcion_1'][:50]
        sin = datos['codigo_sinonimo']
        t = datos.get('descripcion_5', '?')
        p = datos.get('precio_1', 0)
        print(f"       [ALTA DRY] {desc1} | sin={sin} T:{t} ${p:,.2f}")
        return -1  # código simulado para dry_run

    MAX_REINTENTOS = 5

    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            conn.autocommit = False
            cursor = conn.cursor()

            for intento in range(MAX_REINTENTOS):
                try:
                    # Obtener próximo código (NO es autoincremental)
                    # Usa UPDLOCK para minimizar colisiones con otros procesos
                    cursor.execute("""
                        SELECT ISNULL(MAX(codigo), 0) + 1
                        FROM msgestion01art.dbo.articulo WITH (UPDLOCK)
                    """)
                    nuevo_codigo = cursor.fetchone()[0]

                    # Normalizar talle (descripcion_5) con 3 capas si disponible
                    desc5_raw = datos.get("descripcion_5", "")
                    if _resolver_talle_ok and desc5_raw:
                        sub = datos.get("subrubro")
                        desc5_raw = _tpd5(str(desc5_raw), subrubro=sub)

                    params = (
                        nuevo_codigo,
                        datos["descripcion_1"],
                        datos.get("descripcion_3", ""),
                        datos.get("descripcion_4", ""),
                        desc5_raw,
                        datos["codigo_sinonimo"],
                        datos["subrubro"],
                        datos["marca"],
                        datos["linea"],
                        datos.get("rubro", 0),
                        datos.get("grupo", ""),
                        datos.get("proveedor", 0),
                        datos.get("precio_fabrica", 0),
                        datos.get("descuento", 0),
                        datos.get("descuento_1", 0),
                        datos.get("descuento_2", 0),
                        datos.get("precio_costo", 0),
                        datos.get("precio_sugerido", 0),
                        datos.get("utilidad_1", 0),
                        datos.get("utilidad_2", 0),
                        datos.get("utilidad_3", 0),
                        datos.get("utilidad_4", 0),
                        datos.get("precio_1", 0),
                        datos.get("precio_2", 0),
                        datos.get("precio_3", 0),
                        datos.get("precio_4", 0),
                        datos.get("formula", 0),
                        datos.get("moneda", 0),
                    )

                    cursor.execute(sql_insert, params)

                    # Insertar en articulos_prov si hay codigo_proveedor
                    cod_prov = datos.get("codigo_proveedor")
                    proveedor_id = datos.get("proveedor", 0)
                    if cod_prov and proveedor_id:
                        cursor.execute(sql_artprov, (nuevo_codigo, proveedor_id, str(cod_prov)))

                    conn.commit()
                    print(f"✅ Artículo creado: código={nuevo_codigo} | {datos['descripcion_1'][:40]}")
                    return nuevo_codigo

                except pyodbc.IntegrityError as ie:
                    # PK duplicada (SQLSTATE 23000) → reintentar con nuevo MAX
                    conn.rollback()
                    if intento < MAX_REINTENTOS - 1:
                        print(f"    ⚠️  Código {nuevo_codigo} duplicado, reintentando ({intento+2}/{MAX_REINTENTOS})...")
                    else:
                        print(f"❌ No se pudo insertar después de {MAX_REINTENTOS} intentos: {ie}")
                        return None

            return None
    except Exception as e:
        print(f"❌ ERROR al dar de alta artículo: {e}")
        return None


# ──────────────────────────────────────────────────────────────
# PRUEBAS
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🔍 PRUEBA 1: buscar artículo por código")
    # Reemplazar con un código real de tu base
    art = buscar_por_codigo(12345)
    if art:
        print(f"  ✅ Encontrado: {art['descripcion']} | Marca: {art['nombre_marca']} | Subrubro: {art['subrubro']}")
        industria = obtener_industria(art['subrubro'])
        print(f"  Industria: {industria}")
    else:
        print("  No encontrado (o código de prueba no existe)")

    print("\n🔍 PRUEBA 2: buscar por descripción")
    resultados = buscar_por_descripcion("NIKE")
    print(f"  Encontrados: {len(resultados)}")
    for r in resultados[:3]:
        print(f"    {r['codigo']} | {r['descripcion']} | talle: {r['talle']}")

    print("\n🧪 PRUEBA 3: dar de alta artículo (DRY RUN)")
    dar_de_alta({
        "descripcion_1": "ZAPATILLA PRUEBA TEST",
        "codigo_sinonimo": "PRUEBA001",
        "subrubro": 1,
        "marca": 1,
        "linea": 1,
        "proveedor": "PROVEEDOR TEST",
        "precio_1": 15000.00,
    }, dry_run=True)

    print("\n✅ Paso 2 completo.")
