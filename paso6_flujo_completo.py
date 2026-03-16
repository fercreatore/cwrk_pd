# paso6_flujo_completo.py
# Orquesta todos los pasos: parsea el Excel, resuelve artículos,
# calcula períodos, e inserta el pedido.
#
# EJECUTAR:
#   python paso6_flujo_completo.py archivo.xlsx --proveedor "BAGUNZA SA" --dry-run
#   python paso6_flujo_completo.py archivo.xlsx --proveedor "BAGUNZA SA" --ejecutar
#
# Si no se pasa --proveedor, lo pide interactivamente.

import sys
import argparse
from datetime import date, datetime

from paso2_buscar_articulo import buscar_por_codigo, buscar_por_descripcion, obtener_industria, dar_de_alta
from paso3_calcular_periodo import calcular_periodo, warning_destiempo
from paso4_insertar_pedido import insertar_pedido
from paso5_parsear_excel import parsear_nota
from config import EMPRESA_DEFAULT, CONN_COMPRAS
import pyodbc


def buscar_proveedor(denominacion: str) -> dict | None:
    """Busca el código numérico del proveedor por nombre."""
    sql = """
        SELECT TOP 1 numero, denominacion
        FROM proveedores
        WHERE denominacion LIKE ?
        ORDER BY numero
    """
    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, f"%{denominacion}%")
            row = cursor.fetchone()
            if row:
                return {"numero": row[0], "denominacion": row[1]}
    except Exception as e:
        print(f"  ERROR buscando proveedor: {e}")
    return None


def resolver_articulo(renglon: dict, dry_run: bool) -> dict | None:
    """
    Para un renglón de la nota, resuelve el artículo:
    - Si tiene código → busca directamente
    - Si no tiene → busca por descripción
    - Si no existe → pide confirmación y da de alta
    Retorna dict con datos del artículo o None si no se pudo resolver.
    """
    articulo = None

    # 1. Buscar por código si viene en la nota
    if renglon.get("codigo_articulo") and str(renglon["codigo_articulo"]).strip() not in ["", "nan"]:
        try:
            codigo = int(float(renglon["codigo_articulo"]))
            articulo = buscar_por_codigo(codigo)
            if articulo:
                print(f"    ✅ Encontrado por código {codigo}: {articulo['descripcion']}")
                return articulo
            else:
                print(f"    ⚠️  Código {codigo} no existe en la base.")
        except (ValueError, TypeError):
            pass

    # 2. Buscar por descripción
    descripcion = renglon.get("descripcion", "")
    talle = renglon.get("talle")
    candidatos = buscar_por_descripcion(descripcion, talle)

    if len(candidatos) == 1:
        articulo = buscar_por_codigo(candidatos[0]["codigo"])
        print(f"    ✅ Encontrado por descripción: {articulo['descripcion']}")
        return articulo

    if len(candidatos) > 1:
        print(f"    ⚠️  {len(candidatos)} artículos encontrados para '{descripcion}':")
        for i, c in enumerate(candidatos[:5], 1):
            print(f"       {i}. [{c['codigo']}] {c['descripcion']} | talle: {c['talle']} | marca: {c['nombre_marca']}")
        print("       → Se necesita intervención manual para elegir. Renglón omitido.")
        return None

    # 3. No existe — dar de alta
    print(f"    ❌ Artículo '{descripcion}' NO encontrado en la base.")
    if dry_run:
        print(f"    [DRY RUN] Se daría de alta — completar datos en producción.")
        return None

    print(f"\n    📝 Completar datos para dar de alta '{descripcion}':")
    print(f"       (Presionar Enter para omitir campos opcionales)")

    subrubro_str = input("       subrubro (código numérico): ").strip()
    marca_str    = input("       marca (código numérico): ").strip()
    linea_str    = input("       linea (1=Ver 2=Inv 3=Pre 4=Atemp 5=Cole 6=Seg): ").strip()
    sinonimo     = input("       codigo_sinonimo: ").strip()

    if not all([subrubro_str, marca_str, linea_str]):
        print("    → Datos incompletos. Renglón omitido.")
        return None

    nuevo_codigo = dar_de_alta({
        "descripcion_1":   descripcion,
        "codigo_sinonimo": sinonimo or descripcion[:10],
        "subrubro":        int(subrubro_str),
        "marca":           int(marca_str),
        "linea":           int(linea_str),
        "proveedor":       renglon.get("proveedor", ""),
        "precio_1":        float(renglon.get("precio", 0)),
    }, dry_run=False)

    if nuevo_codigo:
        return buscar_por_codigo(nuevo_codigo)
    return None


def procesar_nota(ruta_archivo: str, nombre_proveedor: str, dry_run: bool = True,
                  fecha_pago: date = None, observaciones: str = ""):
    """
    Flujo completo:
    1. Parsear archivo
    2. Buscar proveedor
    3. Para cada renglón: resolver artículo + calcular período
    4. Insertar pedido
    """
    print(f"\n{'='*60}")
    print(f"  CARGA DE NOTA DE PEDIDO")
    print(f"  Archivo   : {ruta_archivo}")
    print(f"  Proveedor : {nombre_proveedor}")
    print(f"  Modo      : {'DRY RUN' if dry_run else '🚨 EJECUCIÓN REAL'}")
    print(f"{'='*60}")

    # ── 1. Parsear ──
    df = parsear_nota(ruta_archivo)
    if df is None:
        print("❌ No se pudo parsear el archivo. Abortando.")
        return

    # ── 2. Proveedor ──
    proveedor = buscar_proveedor(nombre_proveedor)
    if not proveedor:
        print(f"❌ Proveedor '{nombre_proveedor}' no encontrado. Verificar nombre exacto.")
        return
    print(f"\n✅ Proveedor: [{proveedor['numero']}] {proveedor['denominacion']}")

    # ── 3. Resolver renglones ──
    renglones_ok = []
    renglones_error = []

    print(f"\n🔍 Resolviendo {len(df)} renglones...")

    for i, row in df.iterrows():
        renglon_dict = row.to_dict()
        print(f"\n  Renglón {i+1}: {renglon_dict.get('descripcion','?')} | cant: {renglon_dict.get('cantidad')} | talle: {renglon_dict.get('talle','?')}")

        articulo = resolver_articulo(renglon_dict, dry_run)
        if not articulo:
            renglones_error.append(renglon_dict)
            continue

        # Calcular período
        industria = obtener_industria(articulo["subrubro"])
        fecha_entrega_raw = renglon_dict.get("fecha_entrega")
        try:
            if fecha_entrega_raw and str(fecha_entrega_raw) not in ["", "nan", "NaT"]:
                fecha_entrega = pd.to_datetime(fecha_entrega_raw).date()
            else:
                fecha_entrega = date.today()
                print(f"    ⚠️  Sin fecha de entrega — usando hoy ({fecha_entrega})")
        except Exception:
            fecha_entrega = date.today()

        periodo = calcular_periodo(fecha_entrega, industria)
        print(f"    📅 Industria: {industria} | Período: {periodo}")

        # Warning destiempo
        if articulo.get("linea"):
            w = warning_destiempo(fecha_entrega, articulo["linea"])
            if w:
                print(f"    {w}")

        renglones_ok.append({
            "articulo":        articulo["codigo"],
            "descripcion":     articulo["descripcion"],
            "codigo_sinonimo": articulo.get("codigo_sinonimo", ""),
            "cantidad":        float(renglon_dict["cantidad"]),
            "precio":          float(renglon_dict.get("precio", 0)),
            "periodo_compra":  periodo,
        })

    # ── Resumen ──
    print(f"\n{'─'*50}")
    print(f"  Renglones OK     : {len(renglones_ok)}")
    print(f"  Renglones con error: {len(renglones_error)}")

    if not renglones_ok:
        print("❌ No hay renglones válidos para insertar. Abortando.")
        return

    # ── 4. Insertar ──
    cabecera = {
        "empresa":            EMPRESA_DEFAULT,
        "cuenta":             proveedor["numero"],
        "denominacion":       proveedor["denominacion"],
        "fecha_comprobante":  date.today(),
        "fecha_vencimiento":  fecha_pago,
        "observaciones":      observaciones,
    }

    numero = insertar_pedido(cabecera, renglones_ok, dry_run=dry_run)

    print(f"\n{'='*60}")
    if dry_run:
        print("  DRY RUN completado. Revisar output y ejecutar con --ejecutar")
    else:
        print(f"  ✅ PEDIDO CARGADO — Número: {numero}")
    print(f"{'='*60}\n")


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import pandas as pd  # importar acá para no romper si no está instalado

    parser = argparse.ArgumentParser(description="Carga nota de pedido desde Excel/CSV")
    parser.add_argument("archivo",      help="Ruta al archivo Excel o CSV")
    parser.add_argument("--proveedor",  help="Nombre del proveedor (parcial)", default="")
    parser.add_argument("--fecha-pago", help="Fecha de pago YYYY-MM-DD", default="")
    parser.add_argument("--obs",        help="Observaciones adicionales", default="")
    parser.add_argument("--dry-run",    action="store_true", default=True)
    parser.add_argument("--ejecutar",   action="store_true", default=False)

    args = parser.parse_args()

    dry_run = not args.ejecutar

    nombre_proveedor = args.proveedor
    if not nombre_proveedor:
        nombre_proveedor = input("Nombre del proveedor: ").strip()

    fecha_pago = None
    if args.fecha_pago:
        try:
            fecha_pago = date.fromisoformat(args.fecha_pago)
        except ValueError:
            print(f"⚠️  Fecha de pago inválida: {args.fecha_pago}. Se omite.")

    if args.ejecutar:
        confirmacion = input("\n🚨 ¿Confirmar ejecución real? (s/N): ").strip().lower()
        if confirmacion != "s":
            print("Cancelado.")
            sys.exit(0)

    procesar_nota(
        ruta_archivo=args.archivo,
        nombre_proveedor=nombre_proveedor,
        dry_run=dry_run,
        fecha_pago=fecha_pago,
        observaciones=args.obs,
    )
