#!/usr/bin/env python3
"""
sync_auditorias_111.py
Sincroniza resultados de auditorias desde Stock_Auditorias_Movims (112)
hacia t_articulos_last_audit (111/omicronvt).

Para cada articulo, trae la auditoria MAS RECIENTE del 112 y actualiza/inserta
en el 111 con cantidad_diferencia, resultado_auditoria y fecha.

Prerequisito: ejecutar fix_t_articulos_last_audit.sql en el 111 primero.

Uso:
    python sync_auditorias_111.py                    # sync completo
    python sync_auditorias_111.py --dryrun           # solo mostrar que haria
    python sync_auditorias_111.py --depo 0           # solo deposito central
    python sync_auditorias_111.py --desde 2026-01-01 # solo auditorias desde fecha

Ejecutar en: Mac o servidor 111/112 (tiene OpenSSL legacy fix incluido)
"""

import argparse
import os
import platform
import sys
from datetime import datetime

# ── FIX SSL: OpenSSL 3.x no permite TLS 1.0 (SQL Server 2012) ──
if platform.system() != "Windows":
    ssl_conf = "/tmp/openssl_legacy.cnf"
    if not os.path.exists(ssl_conf):
        with open(ssl_conf, "w") as f:
            f.write(
                "openssl_conf = openssl_init\n"
                "[openssl_init]\nssl_conf = ssl_sect\n"
                "[ssl_sect]\nsystem_default = system_default_sect\n"
                "[system_default_sect]\n"
                "MinProtocol = TLSv1\nCipherString = DEFAULT@SECLEVEL=0\n"
            )
    os.environ.setdefault("OPENSSL_CONF", ssl_conf)

import pyodbc  # noqa: E402


# ── CONEXIONES ───────────────────────────────────────────────────
CONN_112 = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.112;"
    "DATABASE=clz_ventas_SQL;"
    "UID=meta106;"
    "PWD=Meta106#;"
    "TrustServerCertificate=yes;"
)

CONN_111 = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=omicronvt;"
    "UID=am;"
    "PWD=dl;"
    "TrustServerCertificate=yes;"
)


def parse_args():
    p = argparse.ArgumentParser(description="Sync auditorias 112 -> 111")
    p.add_argument("--dryrun", action="store_true",
                    help="Solo mostrar que haria, sin escribir")
    p.add_argument("--depo", type=int, default=None,
                    help="Filtrar por depo_macro (ej: 0=central, 2=norte)")
    p.add_argument("--desde", type=str, default=None,
                    help="Solo auditorias desde fecha YYYY-MM-DD")
    return p.parse_args()


def fetch_auditorias_112(desde=None):
    """
    Lee Stock_Auditorias_Movims del 112.
    Retorna dict: codigo -> {fechahora, cantidad_diferencia} (la mas reciente).
    """
    print(f"[112] Conectando a clz_ventas_SQL...")
    conn = pyodbc.connect(CONN_112, timeout=30)
    cursor = conn.cursor()

    # La tabla tiene: codigo, cantidad_diferencia, fechahora (entre otros)
    # Queremos la auditoria mas reciente por codigo
    where = ""
    if desde:
        where = f"WHERE sam.fechahora >= '{desde}'"

    sql = f"""
        SELECT
            sam.codigo,
            sam.cantidad_diferencia,
            sam.fechahora
        FROM clz_ventas_SQL.dbo.Stock_Auditorias_Movims sam
        {where}
    """

    print(f"[112] Ejecutando query...")
    cursor.execute(sql)
    rows = cursor.fetchall()
    print(f"[112] {len(rows)} registros leidos de Stock_Auditorias_Movims")

    # Agrupar: por codigo, quedarse con la mas reciente
    result = {}
    for row in rows:
        codigo = row.codigo
        fechahora = row.fechahora
        cant_dif = row.cantidad_diferencia

        if codigo not in result or fechahora > result[codigo]["fechahora"]:
            result[codigo] = {
                "fechahora": fechahora,
                "cantidad_diferencia": int(cant_dif) if cant_dif is not None else 0,
            }

    print(f"[112] {len(result)} articulos unicos con auditoria mas reciente")
    conn.close()
    return result


def fetch_existing_111(depo_filter=None):
    """
    Lee t_articulos_last_audit del 111.
    Retorna dict: (codigo, depo_macro) -> {id, fecha, cantidad_diferencia, resultado_auditoria}
    """
    print(f"[111] Conectando a omicronvt...")
    conn = pyodbc.connect(CONN_111, timeout=30)
    cursor = conn.cursor()

    where = ""
    if depo_filter is not None:
        where = f"WHERE depo_macro = {depo_filter}"

    sql = f"""
        SELECT id, codigo, depo_macro, fecha, cantidad_diferencia, resultado_auditoria
        FROM omicronvt.dbo.t_articulos_last_audit
        {where}
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    print(f"[111] {len(rows)} registros leidos de t_articulos_last_audit")

    result = {}
    for row in rows:
        key = (row.codigo, row.depo_macro)
        result[key] = {
            "id": row.id,
            "fecha": row.fecha,
            "cantidad_diferencia": row.cantidad_diferencia,
            "resultado_auditoria": row.resultado_auditoria,
        }

    conn.close()
    return result


def fetch_articulo_info(codigos):
    """
    Para INSERTs de articulos nuevos, buscar info basica en articulo (111).
    Retorna dict: codigo -> {codigo_sinonimo, codigo_barra, marca, marca_descrip,
                             proveedor, proveedor_descrip, descrip}
    """
    if not codigos:
        return {}

    print(f"[111] Buscando info de {len(codigos)} articulos nuevos...")
    conn = pyodbc.connect(CONN_111, timeout=30)
    cursor = conn.cursor()

    # Procesar en batches de 500
    result = {}
    codigos_list = list(codigos)
    batch_size = 500

    for i in range(0, len(codigos_list), batch_size):
        batch = codigos_list[i:i + batch_size]
        placeholders = ",".join(str(c) for c in batch)
        sql = f"""
            SELECT
                a.Codigo as codigo,
                a.Codigo_Sinonimo as codigo_sinonimo,
                a.Codigo_Barra as codigo_barra,
                a.Marca as marca,
                m.descripcion as marca_descrip,
                a.proveedor as proveedor,
                p.denominacion as proveedor_descrip,
                a.descripcion_1 as descrip
            FROM msgestion01art.dbo.articulo a
            LEFT JOIN msgestion01art.dbo.marcas m ON a.marca = m.codigo
            LEFT JOIN msgestion01art.dbo.proveedores p ON a.proveedor = p.numero
            WHERE a.Codigo IN ({placeholders})
        """
        cursor.execute(sql)
        for row in cursor.fetchall():
            result[row.codigo] = {
                "codigo_sinonimo": (row.codigo_sinonimo or "").strip(),
                "codigo_barra": row.codigo_barra,
                "marca": row.marca,
                "marca_descrip": (row.marca_descrip or "").strip(),
                "proveedor": row.proveedor,
                "proveedor_descrip": (row.proveedor_descrip or "").strip(),
                "descrip": (row.descrip or "").strip(),
            }

    conn.close()
    return result


def sync(auditorias_112, existing_111, depo_filter, dryrun):
    """
    Compara auditorias del 112 con lo existente en 111 y genera UPDATEs/INSERTs.
    """
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updates = []
    inserts_codigos = set()
    inserts = []
    sin_cambio = 0

    # Mapear codigos existentes por codigo (sin importar depo)
    existing_by_codigo = {}
    for (codigo, depo), data in existing_111.items():
        if codigo not in existing_by_codigo:
            existing_by_codigo[codigo] = []
        existing_by_codigo[codigo].append((depo, data))

    for codigo, aud in auditorias_112.items():
        fecha_aud = aud["fechahora"]
        cant_dif = aud["cantidad_diferencia"]
        resultado = "OK" if cant_dif == 0 else "DIFERENCIA"

        # Si fecha_aud es datetime, convertir a date para comparacion con campo 'fecha'
        if hasattr(fecha_aud, "date"):
            fecha_date = fecha_aud.date()
        else:
            fecha_date = fecha_aud

        if codigo in existing_by_codigo:
            # Articulo existe en 111 — UPDATE todas sus filas (todos sus depositos)
            for depo, data in existing_by_codigo[codigo]:
                if depo_filter is not None and depo != depo_filter:
                    continue

                # Comparar si hay cambio real
                old_fecha = data["fecha"]
                old_cant = data["cantidad_diferencia"]
                old_resultado = data["resultado_auditoria"]

                if (old_fecha == fecha_date
                        and old_cant == cant_dif
                        and old_resultado == resultado):
                    sin_cambio += 1
                    continue

                updates.append({
                    "id": data["id"],
                    "fecha": fecha_date,
                    "cantidad_diferencia": cant_dif,
                    "resultado_auditoria": resultado,
                    "fecha_actualizacion": ahora,
                })
        else:
            # Articulo NO existe en 111 — marcar para INSERT
            inserts_codigos.add(codigo)
            inserts.append({
                "codigo": codigo,
                "fecha": fecha_date,
                "cantidad_diferencia": cant_dif,
                "resultado_auditoria": resultado,
                "fecha_actualizacion": ahora,
            })

    return updates, inserts, inserts_codigos, sin_cambio


def execute_updates(updates, dryrun):
    """Ejecuta UPDATEs en el 111."""
    if not updates:
        print(f"  Sin UPDATEs pendientes.")
        return

    if dryrun:
        print(f"  [DRYRUN] {len(updates)} UPDATEs pendientes. Primeros 5:")
        for u in updates[:5]:
            print(f"    id={u['id']} fecha={u['fecha']} cant_dif={u['cantidad_diferencia']} "
                  f"resultado={u['resultado_auditoria']}")
        return

    print(f"  Ejecutando {len(updates)} UPDATEs...")
    conn = pyodbc.connect(CONN_111, timeout=60)
    cursor = conn.cursor()

    sql = """
        UPDATE omicronvt.dbo.t_articulos_last_audit
        SET fecha = ?,
            cantidad_diferencia = ?,
            resultado_auditoria = ?,
            fecha_actualizacion = ?
        WHERE id = ?
    """

    batch_size = 500
    done = 0
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i + batch_size]
        for u in batch:
            cursor.execute(sql, (
                u["fecha"],
                u["cantidad_diferencia"],
                u["resultado_auditoria"],
                u["fecha_actualizacion"],
                u["id"],
            ))
        conn.commit()
        done += len(batch)
        if done % 2000 == 0 or done == len(updates):
            print(f"    {done}/{len(updates)} UPDATEs ejecutados")

    conn.close()
    print(f"  UPDATEs completados: {len(updates)}")


def execute_inserts(inserts, inserts_codigos, dryrun):
    """Ejecuta INSERTs en el 111 para articulos que no estaban en t_articulos_last_audit."""
    if not inserts:
        print(f"  Sin INSERTs pendientes.")
        return

    # Buscar info del articulo para completar las columnas
    art_info = fetch_articulo_info(inserts_codigos)

    if dryrun:
        print(f"  [DRYRUN] {len(inserts)} INSERTs pendientes. Primeros 5:")
        for ins in inserts[:5]:
            cod = ins["codigo"]
            info = art_info.get(cod, {})
            print(f"    codigo={cod} sinonimo={info.get('codigo_sinonimo', '?')} "
                  f"fecha={ins['fecha']} cant_dif={ins['cantidad_diferencia']} "
                  f"resultado={ins['resultado_auditoria']}")
        return

    print(f"  Ejecutando {len(inserts)} INSERTs...")
    conn = pyodbc.connect(CONN_111, timeout=60)
    cursor = conn.cursor()

    sql = """
        INSERT INTO omicronvt.dbo.t_articulos_last_audit
            (codigo, codigo_sinonimo, codigo_barra, fecha, depo_macro, depo_macro_descrip,
             marca, marca_descrip, proveedor, proveedor_descrip, descrip,
             cantidad_diferencia, resultado_auditoria, fecha_actualizacion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    # INSERT con depo_macro = 0 (deposito central) por defecto
    # porque Stock_Auditorias_Movims no tiene campo deposito
    batch_size = 500
    done = 0
    for i in range(0, len(inserts), batch_size):
        batch = inserts[i:i + batch_size]
        for ins in batch:
            cod = ins["codigo"]
            info = art_info.get(cod, {})
            cursor.execute(sql, (
                cod,
                info.get("codigo_sinonimo", ""),
                info.get("codigo_barra"),
                ins["fecha"],
                0,  # depo_macro default = central
                "DEPOSITO CENTRAL",
                info.get("marca"),
                info.get("marca_descrip", ""),
                info.get("proveedor"),
                info.get("proveedor_descrip", ""),
                info.get("descrip", ""),
                ins["cantidad_diferencia"],
                ins["resultado_auditoria"],
                ins["fecha_actualizacion"],
            ))
        conn.commit()
        done += len(batch)
        if done % 2000 == 0 or done == len(inserts):
            print(f"    {done}/{len(inserts)} INSERTs ejecutados")

    conn.close()
    print(f"  INSERTs completados: {len(inserts)}")


def main():
    args = parse_args()
    print("=" * 60)
    print("sync_auditorias_111.py")
    print(f"  Modo: {'DRYRUN (no escribe)' if args.dryrun else 'EJECUCION REAL'}")
    print(f"  Filtro depo: {args.depo if args.depo is not None else 'todos'}")
    print(f"  Desde: {args.desde or 'sin limite'}")
    print("=" * 60)

    # 1. Leer auditorias del 112
    auditorias_112 = fetch_auditorias_112(desde=args.desde)
    if not auditorias_112:
        print("No se encontraron auditorias en el 112. Nada que hacer.")
        return

    # 2. Leer estado actual del 111
    existing_111 = fetch_existing_111(depo_filter=args.depo)

    # 3. Calcular diferencias
    updates, inserts, inserts_codigos, sin_cambio = sync(
        auditorias_112, existing_111, args.depo, args.dryrun
    )

    # 4. Resumen
    print()
    print("=" * 60)
    print("RESUMEN:")
    print(f"  Articulos en 112 (auditados):    {len(auditorias_112):,}")
    print(f"  Registros en 111 (existentes):   {len(existing_111):,}")
    print(f"  UPDATEs a ejecutar:              {len(updates):,}")
    print(f"  INSERTs a ejecutar:              {len(inserts):,}")
    print(f"  Sin cambio:                      {sin_cambio:,}")
    print("=" * 60)
    print()

    # 5. Ejecutar
    execute_updates(updates, args.dryrun)
    execute_inserts(inserts, inserts_codigos, args.dryrun)

    print()
    print("Listo." if not args.dryrun else "DRYRUN completo (no se escribio nada).")


if __name__ == "__main__":
    main()
