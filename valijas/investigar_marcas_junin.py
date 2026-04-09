#!/usr/bin/env python3
"""
Investigación: por qué las marcas no matchean en msgestion03 ventas1
y generación de segmentos para campaña personalizada Junín.

Ejecutar desde Mac con VPN activa:
  OPENSSL_CONF=/tmp/openssl_legacy.cnf python3 valijas/investigar_marcas_junin.py
"""
import os, sys, json
from datetime import datetime

# OpenSSL legacy config for SQL Server 2012
OPENSSL_CONF_CONTENT = """\
openssl_conf = openssl_init
[openssl_init]
ssl_conf = ssl_sect
[ssl_sect]
system_default = system_default_sect
[system_default_sect]
CipherString = DEFAULT:@SECLEVEL=0
"""
openssl_path = "/tmp/openssl_legacy.cnf"
if not os.path.exists(openssl_path):
    with open(openssl_path, "w") as f:
        f.write(OPENSSL_CONF_CONTENT)
os.environ["OPENSSL_CONF"] = openssl_path

import pyodbc

# === CONEXIONES ===
CONN_111 = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=192.168.2.111;DATABASE=msgestion03;"
    "UID=am;PWD=dl;TrustServerCertificate=yes;Encrypt=no"
)
CONN_112 = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=192.168.2.112;DATABASE=clz_ventas_SQL;"
    "UID=meta106;PWD=Meta106#;TrustServerCertificate=yes;Encrypt=no"
)

EXCL_MARCAS = (1316, 1317, 1158, 436)
EXCL_CODIGOS = (7, 36)
DEPOSITOS_JUNIN = (7, 8)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_conn_111():
    return pyodbc.connect(CONN_111, timeout=30)


def get_conn_112():
    return pyodbc.connect(CONN_112, timeout=30)


def investigar_bug_marcas(conn):
    """Diagnóstico paso a paso del problema de marcas."""
    cur = conn.cursor()
    print("=" * 70)
    print("FASE 1: INVESTIGACIÓN BUG DE MARCAS")
    print("=" * 70)

    # Test 1: ¿Hay ventas en Junín?
    cur.execute("""
        SELECT COUNT(*) cnt, COUNT(DISTINCT cuenta) clientes
        FROM msgestion03.dbo.ventas1
        WHERE deposito IN (7,8) AND codigo NOT IN (7,36)
          AND fecha >= '2025-01-01'
    """)
    row = cur.fetchone()
    print(f"\n1) Ventas Junín desde 2025: {row.cnt:,} líneas, {row.clientes:,} clientes")

    # Test 2: ¿Qué tipo de dato es articulo en ventas1 vs codigo en articulo?
    cur.execute("""
        SELECT
            c.name as column_name, t.name as data_type, c.max_length, c.collation_name
        FROM msgestion03.sys.columns c
        JOIN msgestion03.sys.types t ON c.user_type_id = t.user_type_id
        WHERE c.object_id = OBJECT_ID('msgestion03.dbo.ventas1')
          AND c.name = 'articulo'
    """)
    v1_meta = cur.fetchone()
    print(f"\n2a) ventas1.articulo: type={v1_meta.data_type}, len={v1_meta.max_length}, collation={v1_meta.collation_name}")

    cur.execute("""
        SELECT
            c.name as column_name, t.name as data_type, c.max_length, c.collation_name
        FROM msgestion01art.sys.columns c
        JOIN msgestion01art.sys.types t ON c.user_type_id = t.user_type_id
        WHERE c.object_id = OBJECT_ID('msgestion01art.dbo.articulo')
          AND c.name = 'codigo'
    """)
    art_meta = cur.fetchone()
    print(f"2b) articulo.codigo:  type={art_meta.data_type}, len={art_meta.max_length}, collation={art_meta.collation_name}")

    # Test 3: ¿El campo marca en articulo es numérico o texto?
    cur.execute("""
        SELECT
            c.name, t.name as data_type, c.max_length, c.collation_name
        FROM msgestion01art.sys.columns c
        JOIN msgestion01art.sys.types t ON c.user_type_id = t.user_type_id
        WHERE c.object_id = OBJECT_ID('msgestion01art.dbo.articulo')
          AND c.name = 'marca'
    """)
    marca_meta = cur.fetchone()
    print(f"2c) articulo.marca:   type={marca_meta.data_type}, len={marca_meta.max_length}, collation={marca_meta.collation_name}")

    # Test 4: Sample de ventas1.articulo vs articulo.codigo
    cur.execute("""
        SELECT TOP 5 articulo, LEN(articulo) as len_art,
               CAST(articulo AS VARBINARY(20)) as hex_art
        FROM msgestion03.dbo.ventas1
        WHERE deposito IN (7,8) AND codigo NOT IN (7,36) AND fecha >= '2025-01-01'
    """)
    print("\n3) Sample ventas1.articulo:")
    for r in cur.fetchall():
        print(f"   '{r.articulo}' len={r.len_art} hex={r.hex_art.hex() if r.hex_art else 'NULL'}")

    cur.execute("""
        SELECT TOP 5 codigo, LEN(codigo) as len_cod,
               CAST(codigo AS VARBINARY(20)) as hex_cod
        FROM msgestion01art.dbo.articulo
    """)
    print("\n4) Sample articulo.codigo:")
    for r in cur.fetchall():
        print(f"   '{r.codigo}' len={r.len_cod} hex={r.hex_cod.hex() if r.hex_cod else 'NULL'}")

    # Test 5: JOIN directo — ¿funciona?
    cur.execute("""
        SELECT COUNT(*) cnt
        FROM msgestion03.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON a.codigo = v.articulo
        WHERE v.deposito IN (7,8) AND v.codigo NOT IN (7,36) AND v.fecha >= '2025-01-01'
    """)
    join_count = cur.fetchone().cnt
    print(f"\n5) JOIN directo ventas1.articulo = articulo.codigo: {join_count:,} filas")

    # Campos numéricos — COLLATE y TRIM no aplican
    collate_count = join_count
    trim_count = join_count
    both_count = join_count
    print(f"6) Campos numéricos — COLLATE/TRIM no necesarios. JOIN directo funciona.")

    # Test 9: ¿marca en articulo es numérica o texto? Sample
    cur.execute("""
        SELECT TOP 10 a.codigo, a.marca, a.descripcion_1, m.descripcion as marca_desc
        FROM msgestion01art.dbo.articulo a
        LEFT JOIN msgestion03.dbo.marcas m ON m.codigo = a.marca
        WHERE a.marca IS NOT NULL AND a.marca > 0
    """)
    print("\n9) Sample articulo + marca:")
    for r in cur.fetchall():
        print(f"   art={r.codigo}, marca={r.marca}, desc={r.descripcion_1[:40] if r.descripcion_1 else '?'}, marca_desc={r.marca_desc}")

    # Test 10: ¿Cuántos artículos tienen marca válida (numérica, no en excluidos)?
    cur.execute("""
        SELECT COUNT(*) total,
               SUM(CASE WHEN a.marca > 0 AND a.marca NOT IN (1316,1317,1158,436) THEN 1 ELSE 0 END) con_marca
        FROM msgestion01art.dbo.articulo a
    """)
    r = cur.fetchone()
    print(f"\n10) Artículos: {r.total:,} total, {r.con_marca:,} con marca válida")

    # Determine best JOIN method
    best_method = "direct"
    best_count = join_count
    if collate_count > best_count:
        best_method = "collate"
        best_count = collate_count
    if trim_count > best_count:
        best_method = "trim"
        best_count = trim_count
    if both_count > best_count:
        best_method = "collate+trim"
        best_count = both_count

    print(f"\n>>> MEJOR JOIN: {best_method} con {best_count:,} filas")
    print("=" * 70)
    return best_method


def top_marcas_junin(conn, join_method):
    """Top 15 marcas vendidas en Junín con clientes únicos."""
    print("\n" + "=" * 70)
    print("FASE 2: TOP MARCAS VENDIDAS EN JUNÍN (dep 7,8)")
    print("=" * 70)

    # Build JOIN clause based on best method
    if join_method == "collate":
        join_clause = "a.codigo COLLATE SQL_Latin1_General_CP1_CI_AS = v.articulo COLLATE SQL_Latin1_General_CP1_CI_AS"
    elif join_method == "trim":
        join_clause = "RTRIM(LTRIM(a.codigo)) = RTRIM(LTRIM(v.articulo))"
    elif join_method == "collate+trim":
        join_clause = "RTRIM(LTRIM(a.codigo)) COLLATE SQL_Latin1_General_CP1_CI_AS = RTRIM(LTRIM(v.articulo)) COLLATE SQL_Latin1_General_CP1_CI_AS"
    else:
        join_clause = "a.codigo = v.articulo"

    cur = conn.cursor()
    query = f"""
        SELECT TOP 20
            m.descripcion as marca,
            a.marca as marca_codigo,
            COUNT(DISTINCT v.cuenta) as clientes_unicos,
            COUNT(*) as lineas_venta,
            SUM(v.total_item) as total_vendido,
            MAX(v.fecha) as ultima_venta
        FROM msgestion03.dbo.ventas1 v
        JOIN msgestion01art.dbo.articulo a ON {join_clause}
        JOIN msgestion03.dbo.marcas m ON m.codigo = a.marca
        WHERE v.deposito IN (7,8)
          AND v.codigo NOT IN (7,36)
          AND v.fecha >= '2024-01-01'
          AND a.marca NOT IN (1316,1317,1158,436)
          AND a.marca > 0
        GROUP BY m.descripcion, a.marca
        ORDER BY COUNT(DISTINCT v.cuenta) DESC
    """
    cur.execute(query)
    rows = cur.fetchall()

    marcas = []
    print(f"\n{'Marca':<25} {'Cod':>5} {'Clientes':>10} {'Líneas':>10} {'Total $':>15} {'Últ.Venta':>12}")
    print("-" * 80)
    for r in rows:
        marca_name = r.marca.strip() if r.marca else "?"
        print(f"{marca_name:<25} {r.marca_codigo:>5} {r.clientes_unicos:>10,} {r.lineas_venta:>10,} {r.total_vendido:>15,.0f} {r.ultima_venta.strftime('%Y-%m-%d') if r.ultima_venta else '?':>12}")
        marcas.append({
            "marca": marca_name,
            "marca_codigo": r.marca_codigo,
            "clientes_unicos": r.clientes_unicos,
            "lineas_venta": r.lineas_venta,
            "total_vendido": float(r.total_vendido) if r.total_vendido else 0,
            "ultima_venta": r.ultima_venta.strftime("%Y-%m-%d") if r.ultima_venta else None
        })

    return marcas, join_clause


def clientes_por_marca(conn, marcas, join_clause):
    """Para cada marca top, obtener lista de clientes que la compraron."""
    print("\n" + "=" * 70)
    print("FASE 3: CLIENTES POR MARCA")
    print("=" * 70)

    cur = conn.cursor()
    resultado = {}

    for m in marcas[:15]:
        marca_cod = m["marca_codigo"]
        marca_name = m["marca"]

        query = f"""
            SELECT
                v.cuenta,
                c.denominacion as nombre,
                MAX(v.fecha) as ultima_compra,
                SUM(v.total_item) as total_gastado,
                COUNT(*) as compras
            FROM msgestion03.dbo.ventas1 v
            JOIN msgestion01art.dbo.articulo a ON {join_clause}
            JOIN msgestion03.dbo.clientes c ON c.numero = v.cuenta
            WHERE v.deposito IN (7,8)
              AND v.codigo NOT IN (7,36)
              AND v.fecha >= '2024-01-01'
              AND a.marca = {marca_cod}
            GROUP BY v.cuenta, c.denominacion
            ORDER BY SUM(v.total_item) DESC
        """
        cur.execute(query)
        rows = cur.fetchall()

        clientes = []
        for r in rows:
            nombre = r.nombre.strip() if r.nombre else ""
            clientes.append({
                "cuenta": r.cuenta,
                "nombre": nombre,
                "ultima_compra": r.ultima_compra.strftime("%Y-%m-%d") if r.ultima_compra else None,
                "total_gastado": float(r.total_gastado) if r.total_gastado else 0,
                "compras": r.compras
            })

        resultado[marca_name] = clientes
        print(f"  {marca_name}: {len(clientes)} clientes")

    return resultado


def cruzar_telefonos(conn_112, clientes_por_marca_dict):
    """Cruzar con teléfonos de terceros en 192.168.2.112."""
    print("\n" + "=" * 70)
    print("FASE 4: CRUCE CON TELÉFONOS (192.168.2.112)")
    print("=" * 70)

    cur = conn_112.cursor()

    # Obtener todos los teléfonos de terceros de una sola vez
    all_cuentas = set()
    for clientes in clientes_por_marca_dict.values():
        for c in clientes:
            all_cuentas.add(c["cuenta"])

    if not all_cuentas:
        print("  No hay cuentas para cruzar.")
        return {}

    # Batch query — obtener todos los teléfonos
    # terceros.nro_mg = clientes.numero
    cuentas_list = ",".join(f"'{c}'" for c in all_cuentas)
    query = f"""
        SELECT nro_mg, telefono
        FROM terceros
        WHERE nro_mg IN ({cuentas_list})
          AND telefono IS NOT NULL AND telefono != ''
    """
    cur.execute(query)
    telefono_map = {}
    for r in cur.fetchall():
        tel = str(r.telefono).strip()
        # Normalizar teléfono argentino
        tel = tel.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").lstrip("+")
        # nro_mg is nvarchar, convert to int for matching with cuenta
        try:
            key = int(r.nro_mg)
        except (ValueError, TypeError):
            continue
        if tel.startswith("549") and len(tel) >= 12:
            telefono_map[key] = tel
        elif tel.startswith("54") and not tel.startswith("549"):
            telefono_map[key] = "549" + tel[2:]
        elif tel.startswith("0"):
            tel = tel[1:]
            if tel.startswith("15"):
                telefono_map[key] = "54911" + tel[2:]
            else:
                telefono_map[key] = "549" + tel
        elif len(tel) >= 10:
            telefono_map[key] = "549" + tel

    print(f"  Cuentas únicas: {len(all_cuentas)}")
    print(f"  Con teléfono: {len(telefono_map)}")

    # Enriquecer clientes con teléfono
    for marca, clientes in clientes_por_marca_dict.items():
        con_tel = 0
        for c in clientes:
            tel = telefono_map.get(c["cuenta"])
            if tel:
                c["telefono"] = tel
                con_tel += 1
        print(f"  {marca}: {con_tel}/{len(clientes)} con teléfono")

    return telefono_map


def obtener_stock_junin(conn):
    """Obtener stock actual por marca en Junín + top productos con stock."""
    print("\n" + "=" * 70)
    print("FASE 5: STOCK ACTUAL EN JUNÍN POR MARCA")
    print("=" * 70)

    cur = conn.cursor()

    # Stock actual por marca en Junín
    query = """
        SELECT
            m.descripcion as marca,
            a.marca as marca_codigo,
            SUM(s.stock_actual) as stock_total,
            COUNT(DISTINCT s.articulo) as articulos_distintos
        FROM msgestionC.dbo.stock s
        JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
        JOIN msgestion03.dbo.marcas m ON m.codigo = a.marca
        WHERE s.deposito IN (7,8)
          AND s.stock_actual > 0
          AND a.marca NOT IN (1316,1317,1158,436)
          AND a.marca > 0
        GROUP BY m.descripcion, a.marca
        ORDER BY SUM(s.stock_actual) DESC
    """
    cur.execute(query)

    stock_data = {}
    print(f"\n  {'Marca':<25} {'Stock':>7} {'Arts':>6}")
    print("  " + "-" * 40)
    for r in cur.fetchall():
        marca = r.marca.strip() if r.marca else "?"
        print(f"  {marca:<25} {r.stock_total:>7,.0f} {r.articulos_distintos:>6}")
        stock_data[marca] = {
            "marca_codigo": int(r.marca_codigo),
            "stock_total": int(r.stock_total),
            "articulos_distintos": int(r.articulos_distintos),
            "productos": []
        }

    # Top productos con stock por marca (top 5 por marca, top 15 marcas)
    for marca in list(stock_data.keys())[:15]:
        marca_cod = stock_data[marca]["marca_codigo"]
        cur.execute(f"""
            SELECT TOP 5
                a.descripcion_1 as producto,
                s.articulo,
                SUM(s.stock_actual) as stock
            FROM msgestionC.dbo.stock s
            JOIN msgestion01art.dbo.articulo a ON a.codigo = s.articulo
            WHERE s.deposito IN (7,8)
              AND s.stock_actual > 0
              AND a.marca = {marca_cod}
            GROUP BY a.descripcion_1, s.articulo
            ORDER BY SUM(s.stock_actual) DESC
        """)
        for r in cur.fetchall():
            stock_data[marca]["productos"].append({
                "producto": r.producto.strip() if r.producto else "?",
                "articulo": int(r.articulo),
                "stock": int(r.stock)
            })

    return stock_data


def cargar_ya_enviados():
    """Cargar teléfonos que ya recibieron campaña."""
    sent = set()
    for fname in os.listdir(BASE_DIR):
        if fname.startswith("log_") and fname.endswith(".json"):
            try:
                with open(os.path.join(BASE_DIR, fname)) as f:
                    data = json.load(f)
                for r in data:
                    if r.get("status") == "sent":
                        sent.add(r.get("telefono", ""))
            except:
                pass
    master = os.path.join(BASE_DIR, "phones_already_sent.json")
    if os.path.exists(master):
        try:
            with open(master) as f:
                sent.update(json.load(f))
        except:
            pass
    return sent


def extraer_primer_nombre(nombre):
    """Extrae el primer nombre de 'APELLIDO, NOMBRE' o 'APELLIDO NOMBRE'."""
    if not nombre:
        return ""
    nombre = str(nombre).strip()
    if ',' in nombre:
        parts = nombre.split(',')
        if len(parts) >= 2:
            after = parts[1].strip()
            if after:
                return after.split()[0].title()
    words = nombre.split()
    if len(words) >= 2:
        return words[1].title()
    return nombre.title()


def generar_segmentos(clientes_por_marca_dict, stock_nuevo, ya_enviados):
    """Genera segmentos_junin.json."""
    print("\n" + "=" * 70)
    print("FASE 6: GENERANDO segmentos_junin.json")
    print("=" * 70)

    segmentos = []
    resumen_total = {"marcas": 0, "clientes_con_tel": 0, "clientes_sin_tel": 0, "ya_campaneados": 0}

    for marca, clientes in sorted(clientes_por_marca_dict.items(),
                                    key=lambda x: len(x[1]), reverse=True):
        clientes_con_tel = [c for c in clientes if c.get("telefono")]
        clientes_sin_tel = [c for c in clientes if not c.get("telefono")]
        ya_camp = sum(1 for c in clientes_con_tel if c.get("telefono") in ya_enviados)

        # Stock actual para esta marca
        stock_info = stock_nuevo.get(marca, {})
        productos = stock_info.get("productos", [])

        segmento = {
            "marca": marca,
            "marca_codigo": stock_info.get("marca_codigo"),
            "clientes": [],
            "stock_actual": {
                "total": stock_info.get("stock_total", 0),
                "articulos": stock_info.get("articulos_distintos", 0),
                "top_productos": productos[:10]
            },
            "stats": {
                "total_clientes": len(clientes),
                "con_telefono": len(clientes_con_tel),
                "sin_telefono": len(clientes_sin_tel),
                "ya_campaneados": ya_camp,
                "elegibles": len(clientes_con_tel) - ya_camp
            }
        }

        for c in clientes_con_tel:
            primer_nombre = extraer_primer_nombre(c["nombre"])
            segmento["clientes"].append({
                "cuenta": c["cuenta"],
                "nombre": c["nombre"],
                "primer_nombre": primer_nombre,
                "telefono": c["telefono"],
                "ultima_compra": c["ultima_compra"],
                "total_gastado": c["total_gastado"],
                "compras": c["compras"],
                "ya_campaneado": c["telefono"] in ya_enviados
            })

        segmentos.append(segmento)
        resumen_total["marcas"] += 1
        resumen_total["clientes_con_tel"] += len(clientes_con_tel)
        resumen_total["clientes_sin_tel"] += len(clientes_sin_tel)
        resumen_total["ya_campaneados"] += ya_camp

        elegibles = len(clientes_con_tel) - ya_camp
        tiene_stock = "SI" if stock_info.get("stock_total", 0) > 0 else "NO"
        print(f"  {marca:<25} {len(clientes):>4} clientes | {len(clientes_con_tel):>4} con tel | {elegibles:>4} elegibles | stock nuevo: {tiene_stock}")

    # Guardar
    output_path = os.path.join(BASE_DIR, "segmentos_junin.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "generado": datetime.now().isoformat(),
            "depositos": list(DEPOSITOS_JUNIN),
            "periodo_ventas": "2024-01-01 a hoy",
            "resumen": resumen_total,
            "segmentos": segmentos
        }, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n  Archivo: {output_path}")
    print(f"  Marcas: {resumen_total['marcas']}")
    print(f"  Clientes con tel: {resumen_total['clientes_con_tel']}")
    print(f"  Ya campaneados: {resumen_total['ya_campaneados']}")
    print(f"  Elegibles nuevos: {resumen_total['clientes_con_tel'] - resumen_total['ya_campaneados']}")

    return segmentos


def main():
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Conectando a 192.168.2.111...")

    conn = get_conn_111()
    print("OK")

    # Fase 1: Investigar bug
    join_method = investigar_bug_marcas(conn)

    # Fase 2: Top marcas
    marcas, join_clause = top_marcas_junin(conn, join_method)

    # Fase 3: Clientes por marca
    clientes_dict = clientes_por_marca(conn, marcas, join_clause)

    # Fase 4: Cruzar teléfonos
    print(f"\nConectando a 192.168.2.112...")
    conn_112 = get_conn_112()
    print("OK")
    cruzar_telefonos(conn_112, clientes_dict)
    conn_112.close()

    # Fase 5: Stock actual
    stock_nuevo = obtener_stock_junin(conn)
    conn.close()

    # Fase 6: Generar segmentos
    ya_enviados = cargar_ya_enviados()
    print(f"\n  Teléfonos ya campaneados (todas las campañas): {len(ya_enviados)}")
    segmentos = generar_segmentos(clientes_dict, stock_nuevo, ya_enviados)

    print("\n" + "=" * 70)
    print("COMPLETADO. Siguiente paso: crear template en Meta y enviar_junin_personalizado.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
