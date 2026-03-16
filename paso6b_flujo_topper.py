# paso6b_flujo_topper.py
# Orquestador específico para notas de pedido de Topper (formato SAP pivoteado).
#
# Flujo:
#   1. Parsea el Excel con paso5b_parsear_topper (una hoja = un pedido mensual)
#   2. Para cada pedido mensual:
#      a. Resuelve artículos por código SAP (buscar_por_codigo_sap)
#      b. Calcula período de compra (paso3)
#      c. Inserta cabecera + renglones (paso4)
#
# Reglas de negocio Topper:
#   - Proveedor fijo: ALPARGATAS S.A.I.C. (cuenta 668)
#   - Marca fija: TOPPER (código 314)
#   - Cada hoja mensual (ENE 26, FEB 26...) → pedido separado
#   - Fecha entrega = último día del mes de la hoja
#   - Fecha pago = fecha entrega + 60 días
#   - Forma de pago: cuenta corriente
#   - Período: se calcula según industria del subrubro del artículo
#
# EJECUTAR:
#   python paso6b_flujo_topper.py "TOPPER CALZADO COMPLETO.xlsx" --dry-run
#   python paso6b_flujo_topper.py "TOPPER CALZADO COMPLETO.xlsx" --ejecutar

import sys
import argparse
from datetime import date, datetime

from paso5b_parsear_topper import parsear_topper, PROVEEDOR_CUENTA, PROVEEDOR_NOMBRE, FORMA_PAGO_TEXT, MARCA_TOPPER
from paso2_buscar_articulo import buscar_por_codigo_sap, buscar_por_codigo, obtener_industria, dar_de_alta
from paso3_calcular_periodo import calcular_periodo, warning_destiempo
from paso4_insertar_pedido import insertar_pedido
from config import EMPRESA_DEFAULT, PROVEEDORES, calcular_precios


# ── MAPEOS TOPPER: Excel → BD ────────────────────────────────

# Género del Excel (col 0) → rubro de la BD
# rubros: 1=DAMAS, 3=HOMBRES, 4=NIÑOS, 5=NIÑAS, 6=UNISEX
GENERO_A_RUBRO = {
    "HOMBRE":  3,
    "HOMBRES": 3,
    "MUJER":   1,
    "MUJERES": 1,
    "DAMA":    1,
    "DAMAS":   1,
    "NIÑO":    4,
    "NIÑOS":   4,
    "NIÑA":    5,
    "NIÑAS":   5,
    "UNISEX":  6,
    "KIDS":    4,
    "INFANTIL":4,
    "JUNIOR":  4,
}

# Categoría del Excel (col 41) → subrubro de la BD
# Basado en subrubros Topper existentes en la base
CATEGORIA_A_SUBRUBRO = {
    "RUNNING":     47,
    "TRAINING":    49,
    "SNEAKERS":    55,
    "CASUAL":      52,
    "TENNIS":      48,
    "OUTDOOR":     51,
    "BASKET":      50,
    "SKATER":      53,
    "BOTINES PISTA":45,
    "BOTIN PISTA": 45,
    "BOTIN INDOOR":54,
    "INDOOR":      54,
    "FUTBOL":      45,
    "PANCHA":      35,
    "OJOTAS":      11,
    "SANDALIAS":   12,
    "PANTUFLA":    60,
    # Indumentaria
    "REMERAS":     57,
    "REMERA":      57,
    "PANTALON":    23,
    "CAMPERA":     46,
    "CAMPERAS":    46,
    "BUZO":        61,
    "CALZA":       62,
    "MALLA":       63,
    # Accesorios
    "MOCHILAS":    25,
    "BOLSOS":      30,
    "MEDIAS":      29,
    "PELOTAS":     33,
}

# Grupo (material) más común por subrubro en Topper
# Determinado por análisis de la BD existente
SUBRUBRO_A_GRUPO_DEFAULT = {
    47: "15",   # RUNNING → MACRAMÉ
    49: "15",   # TRAINING → MACRAMÉ
    55: "15",   # SNEAKERS → MACRAMÉ
    52: "5",    # CASUAL → PU (o "2"=LONA, depende)
    48: "5",    # TENNIS → PU
    51: "15",   # OUTDOOR → MACRAMÉ
    50: "5",    # BASKET → PU
    53: "4",    # SKATER → GAMUZA
    45: "5",    # BOTINES PISTA → PU
    54: "5",    # BOTIN INDOOR → PU
    35: "15",   # PANCHA → MACRAMÉ
    57: "17",   # REMERAS → TELA
    23: "17",   # PANTALON → TELA
    46: "17",   # CAMPERAS → TELA
    61: "17",   # BUZO → TELA
    62: "17",   # CALZA → TELA
    63: "17",   # MALLA → TELA
    25: "17",   # MOCHILAS → TELA
    30: "17",   # BOLSOS → TELA
    29: "17",   # MEDIAS → TELA
    33: "5",    # PELOTAS → PU
    11: "11",   # OJOTAS → PVC
    12: "17",   # SANDALIAS → TELA
    60: "17",   # PANTUFLA → TELA
}


def inferir_rubro(genero: str) -> int:
    """Convierte género del Excel al código de rubro de la BD."""
    g = genero.strip().upper()
    return GENERO_A_RUBRO.get(g, 6)  # default UNISEX


def inferir_subrubro(categoria: str) -> int | None:
    """Convierte categoría del Excel al código de subrubro de la BD."""
    c = categoria.strip().upper()
    # Primero intento exacto
    if c in CATEGORIA_A_SUBRUBRO:
        return CATEGORIA_A_SUBRUBRO[c]
    # Intento parcial
    for key, val in CATEGORIA_A_SUBRUBRO.items():
        if key in c or c in key:
            return val
    return None


def inferir_grupo(subrubro: int) -> str:
    """Retorna el grupo (material) más probable para un subrubro Topper."""
    return SUBRUBRO_A_GRUPO_DEFAULT.get(subrubro, "15")


# Mapeo descripcion_4 (color principal) → código de color (2 dígitos)
# Basado en tabla colores de msgestionC y análisis de sinónimos existentes
COLOR_A_CODIGO = {
    "NEGRO":     "00",
    "BLANCO":    "01",
    "AZUL":      "02",
    "AERO":      "03",
    "ROJO":      "04",
    "TURQUESA":  "05",
    "LILA":      "06",
    "FUCSIA":    "07",
    "JEAN":      "08",
    "NARANJA":   "09",
    "CHAROL":    "10",
    "MARRON":    "11",
    "COCO":      "12",
    "GRIS":      "13",
    "VERDE":     "14",
    "BEIGE":     "15",
    "MUSGO":     "16",
    "ROSA":      "19",
    "PLATA":     "20",
    "CAMEL":     "22",
    "COBRE":     "23",
    "CORAL":     "24",
    "NUDE":      "25",
    "AQUA":      "27",
    "CELESTE":   "28",
    "ORO":       "29",
    "BORDO":     "30",
    "AMARILLO":  "35",
    "SUELA":     "41",
    "MULTICOLOR":"51",
    "VIOLETA":   "62",
}


def inferir_codigo_color(descripcion_4: str) -> str:
    """
    Infiere el código de color (2 dígitos) a partir de descripcion_4.

    Lógica:
    1. Toma el primer color antes de "/" (ej: "NEGRO/BLANCO" → "NEGRO")
    2. Busca en el mapeo COLOR_A_CODIGO
    3. Si no encuentra, retorna "00" (negro por defecto)
    """
    if not descripcion_4:
        return "00"

    # Tomar color principal (antes de la primera /)
    color_principal = descripcion_4.strip().upper().split("/")[0].strip()

    # Buscar exacto
    if color_principal in COLOR_A_CODIGO:
        return COLOR_A_CODIGO[color_principal]

    # Buscar parcial (por si tiene "GRIS ANTAR" o similar)
    for nombre, codigo in COLOR_A_CODIGO.items():
        if nombre in color_principal or color_principal in nombre:
            return codigo

    return "00"  # default NEGRO


# ──────────────────────────────────────────────────────────────
# RESOLVER ARTÍCULOS POR CÓDIGO SAP
# ──────────────────────────────────────────────────────────────

# Mapeo subrubro → tipo abreviado para descripcion_1
# Formato: "SKU MODELO COLOR TIPO"
SUBRUBRO_A_TIPO = {
    47: "ZAPATILLA",     # RUNNING
    49: "ZAPATILLA",     # TRAINING
    55: "ZAPATILLA",     # SNEAKERS
    52: "ZAPATILLA",     # CASUAL
    48: "ZAPATILLA",     # TENNIS
    51: "ZAPATILLA",     # OUTDOOR
    50: "ZAPATILLA",     # BASKET
    53: "ZAPATILLA",     # SKATER
    45: "BOTIN",         # BOTINES PISTA
    54: "BOTIN",         # BOTIN INDOOR
    35: "PANCHA",        # PANCHA
    11: "OJOTA",         # OJOTAS
    12: "SANDALIA",      # SANDALIAS
    60: "PANTUFLA",      # PANTUFLA
    57: "REMERA",        # REMERAS
    23: "PANTALON",      # PANTALON
    46: "CAMPERA",       # CAMPERAS
    61: "BUZO",          # BUZO
    62: "CALZA",         # CALZA
    63: "MALLA",         # MALLA
    25: "MOCHILA",       # MOCHILAS
    30: "BOLSO",         # BOLSOS
    29: "MEDIAS",        # MEDIAS
    33: "PELOTA",        # PELOTAS
}


def sap_sin_cero(codigo_sap: str) -> str:
    """Quita ceros a la izquierda del código SAP. Ej: '026903' → '26903'."""
    return str(codigo_sap).strip().lstrip("0")


def nombre_a_sku(modelo: str) -> str:
    """
    Fallback: convierte nombre del modelo a SKU de 5 caracteres para el sinónimo.
    Solo se usa si no hay código SAP numérico disponible.
    Ej: 'SENDAI' → 'SENDA', 'NEBULA' → 'NEBUL'
    """
    limpio = "".join(c for c in modelo.upper() if c.isalpha())
    return limpio[:5].ljust(5, "X")


def resolver_articulo_sap(codigo_sap: str, talle: str, modelo: str, color: str,
                          genero: str, categoria: str,
                          precio_lista: float, pvp: float,
                          dry_run: bool) -> dict | None:
    """
    Busca un artículo por código SAP + talle.
    Si no existe, intenta darlo de alta (tanto en dry_run como ejecución).

    Sinónimo: 668 + SKU(5 chars del nombre) + CC(color) + TT(talle)
    Para talles de modelo existente: copia el patrón del sinónimo y cambia últimos 2.
    Para modelos nuevos: arma sinónimo con nombre_a_sku().

    Retorna dict con:
      codigo, descripcion, codigo_sinonimo, talle, subrubro, marca, linea, rubro
    O None si no se pudo resolver.
    """
    # Buscar en BD por código SAP del proveedor + talle
    resultados = buscar_por_codigo_sap(codigo_sap, talle)

    if len(resultados) == 1:
        return resultados[0]

    if len(resultados) > 1:
        print(f"    ⚠️  {len(resultados)} artículos para SAP:{codigo_sap} T:{talle} — usando primero")
        return resultados[0]

    # ── No encontrado — dar de alta ──
    sku = sap_sin_cero(codigo_sap)  # "026903" → "26903"

    # Calcular precios con la cadena correcta del proveedor
    precios = calcular_precios(precio_lista, PROVEEDOR_CUENTA)

    # Buscar sin talle para obtener datos del modelo (subrubro, linea, etc.)
    modelo_existente = buscar_por_codigo_sap(codigo_sap)
    if modelo_existente:
        # CASO 1: Talle nuevo de modelo existente — copiar patrón del sinónimo
        ref = modelo_existente[0]
        sub = ref["subrubro"]

        # Sinónimo: 668 + SKU(5 dígitos) + color_code(2) + talle(2)
        sin_ref = ref.get("codigo_sinonimo", "")
        if sin_ref and len(sin_ref) >= 10:
            sinonimo = sin_ref[:10] + str(talle).zfill(2)
        else:
            cod_color = inferir_codigo_color(color)
            sinonimo = f"668{sku.zfill(5)}{cod_color}{str(talle).zfill(2)}"

        # Descripción: SKU MODELO COLOR TIPO (todo MAYÚSCULA)
        tipo = SUBRUBRO_A_TIPO.get(sub, "")
        desc1 = f"{sku} {modelo} {color} {tipo}".strip().upper()
        desc3 = f"{sku} {modelo} {tipo}".strip().upper()

        datos_alta = {
            "descripcion_1":    desc1,
            "descripcion_3":    desc3,
            "descripcion_4":    color.upper(),
            "descripcion_5":    str(talle),
            "codigo_sinonimo":  sinonimo,
            "subrubro":         sub,
            "marca":            ref["marca"],
            "linea":            ref["linea"],
            "rubro":            ref.get("rubro", inferir_rubro(genero)),
            "grupo":            inferir_grupo(sub),
            "proveedor":        PROVEEDOR_CUENTA,
            "codigo_proveedor": sku,     # para articulos_prov
            "moneda":           0,
            **precios,                   # precio_fabrica, descuento, precio_costo, precios, utilidades, formula
        }

        print(f"    📝 Alta talle nuevo: {desc1} | sin={sinonimo}")
        nuevo_codigo = dar_de_alta(datos_alta, dry_run=dry_run)
        if nuevo_codigo:
            if dry_run:
                return {
                    "codigo": nuevo_codigo,
                    "descripcion": desc1,
                    "codigo_sinonimo": sinonimo,
                    "subrubro": sub,
                    "marca": ref["marca"],
                    "linea": ref["linea"],
                    "rubro": ref.get("rubro", inferir_rubro(genero)),
                }
            return buscar_por_codigo(nuevo_codigo)
    else:
        # CASO 2: Modelo totalmente nuevo — inferir datos del Excel
        rubro = inferir_rubro(genero)
        subrubro = inferir_subrubro(categoria)

        # Sinónimo: 668 + SKU(5 dígitos) + color_code(2) + talle(2)
        cod_color = inferir_codigo_color(color)
        sinonimo = f"668{sku.zfill(5)}{cod_color}{str(talle).zfill(2)}"

        if subrubro:
            tipo = SUBRUBRO_A_TIPO.get(subrubro, "")
            desc1 = f"{sku} {modelo} {color} {tipo}".strip().upper()
            desc3 = f"{sku} {modelo} {tipo}".strip().upper()

            datos_alta = {
                "descripcion_1":    desc1,
                "descripcion_3":    desc3,
                "descripcion_4":    color.upper(),
                "descripcion_5":    str(talle),
                "codigo_sinonimo":  sinonimo,
                "subrubro":         subrubro,
                "marca":            MARCA_TOPPER,
                "linea":            1,  # default Verano
                "rubro":            rubro,
                "grupo":            inferir_grupo(subrubro),
                "proveedor":        PROVEEDOR_CUENTA,
                "codigo_proveedor": sku,     # para articulos_prov
                "moneda":           0,
                **precios,
            }
            print(f"    📝 Alta modelo nuevo: {desc1} | sin={sinonimo}")
            nuevo_codigo = dar_de_alta(datos_alta, dry_run=dry_run)
            if nuevo_codigo:
                if dry_run:
                    return {
                        "codigo": nuevo_codigo,
                        "descripcion": desc1,
                        "codigo_sinonimo": sinonimo,
                        "subrubro": subrubro,
                        "marca": MARCA_TOPPER,
                        "linea": 1,
                        "rubro": rubro,
                    }
                return buscar_por_codigo(nuevo_codigo)
        else:
            print(f"    ❌ SAP:{codigo_sap} categoría '{categoria}' no mapeada.")
            print(f"       Modelo: {modelo} | Color: {color} | Talle: {talle} | Género: {genero}")

    return None


# ──────────────────────────────────────────────────────────────
# FLUJO PRINCIPAL POR PEDIDO MENSUAL
# ──────────────────────────────────────────────────────────────

def procesar_pedido_mensual(pedido: dict, dry_run: bool) -> dict:
    """
    Procesa un pedido mensual de Topper.

    Retorna dict con:
      numero_pedido, mes, renglones_ok, renglones_error, total_pares, total_importe
    """
    mes = pedido["mes"]
    fecha_entrega = pedido["fecha_entrega"]
    fecha_pago = pedido["fecha_pago"]
    renglones = pedido["renglones"]

    print(f"\n{'─'*60}")
    print(f"  📦 PEDIDO: {mes}")
    print(f"     Entrega : {fecha_entrega}")
    print(f"     Pago    : {fecha_pago}")
    print(f"     Renglones a procesar: {len(renglones)}")
    print(f"{'─'*60}")

    renglones_ok = []
    renglones_error = []
    codigos_sap_procesados = {}   # cache: (codigo_sap, talle) → articulo resuelto

    for i, r in enumerate(renglones, 1):
        codigo_sap = r["codigo_sap"]
        talle = r["talle"]
        modelo = r["modelo"]
        color = r["color"]
        cantidad = r["cantidad"]
        precio = r["precio_lista"]
        pvp = r.get("pvp", 0)
        genero = r.get("genero", "")
        categoria = r.get("categoria", "")
        cache_key = (codigo_sap, talle)

        # Buscar en cache primero
        if cache_key in codigos_sap_procesados:
            articulo = codigos_sap_procesados[cache_key]
        else:
            articulo = resolver_articulo_sap(
                codigo_sap, talle, modelo, color,
                genero, categoria,
                precio, pvp, dry_run
            )
            codigos_sap_procesados[cache_key] = articulo

            # Log solo la primera vez que se busca
            if articulo:
                print(f"  ✅ SAP:{codigo_sap:>6} T:{talle:>2} → [{articulo['codigo']}] {articulo['descripcion'][:50]}")
            else:
                print(f"  ❌ SAP:{codigo_sap:>6} T:{talle:>2} | {modelo} {color} — NO ENCONTRADO")

        if not articulo:
            renglones_error.append(r)
            continue

        # Calcular período
        industria = obtener_industria(articulo["subrubro"])
        periodo = calcular_periodo(fecha_entrega, industria)

        # Warning destiempo
        if articulo.get("linea"):
            w = warning_destiempo(fecha_entrega, articulo["linea"])
            if w:
                print(f"    {w}")

        renglones_ok.append({
            "articulo":        articulo["codigo"],
            "descripcion":     articulo["descripcion"],
            "codigo_sinonimo": articulo.get("codigo_sinonimo", ""),
            "cantidad":        cantidad,
            "precio":          round(precio, 2),
            "periodo_compra":  periodo,
        })

    # ── Resumen del pedido mensual ──
    print(f"\n  Resumen {mes}:")
    print(f"    Renglones OK     : {len(renglones_ok)}")
    print(f"    Renglones error  : {len(renglones_error)}")
    total_pares = sum(r["cantidad"] for r in renglones_ok)
    total_importe = sum(r["precio"] * r["cantidad"] for r in renglones_ok)
    print(f"    Pares resueltos  : {total_pares}")
    print(f"    Importe resuelto : ${total_importe:,.0f}")

    if not renglones_ok:
        print(f"  ⚠️  Sin renglones válidos para {mes}. Pedido omitido.")
        return {
            "numero_pedido": None,
            "mes": mes,
            "renglones_ok": 0,
            "renglones_error": len(renglones_error),
            "total_pares": 0,
            "total_importe": 0,
        }

    # Armar observaciones
    periodos_unicos = sorted(set(r["periodo_compra"] for r in renglones_ok))
    obs = f"{FORMA_PAGO_TEXT}. Entrega: {fecha_entrega}. "
    obs += f"Período: {', '.join(periodos_unicos)}. "
    obs += f"Nota de pedido TOPPER — {mes}."

    # ── Insertar pedido ──
    cabecera = {
        "empresa":           EMPRESA_DEFAULT,
        "cuenta":            PROVEEDOR_CUENTA,
        "denominacion":      PROVEEDOR_NOMBRE,
        "fecha_comprobante": date.today(),
        "fecha_vencimiento": fecha_pago,
        "fecha_entrega":     fecha_entrega,
        "observaciones":     obs,
    }

    numero = insertar_pedido(cabecera, renglones_ok, dry_run=dry_run)

    return {
        "numero_pedido": numero,
        "mes": mes,
        "renglones_ok": len(renglones_ok),
        "renglones_error": len(renglones_error),
        "total_pares": total_pares,
        "total_importe": total_importe,
    }


# ──────────────────────────────────────────────────────────────
# ORQUESTADOR PRINCIPAL
# ──────────────────────────────────────────────────────────────

def flujo_topper(ruta_archivo: str, dry_run: bool = True):
    """
    Flujo completo para una nota de pedido Topper.

    1. Parsea todas las hojas mensuales del Excel
    2. Para cada mes, resuelve artículos e inserta pedido
    3. Muestra resumen final
    """
    print(f"\n{'='*60}")
    print(f"  CARGA DE NOTA DE PEDIDO — TOPPER")
    print(f"  Archivo    : {ruta_archivo}")
    print(f"  Proveedor  : {PROVEEDOR_NOMBRE} (cuenta {PROVEEDOR_CUENTA})")
    print(f"  Modo       : {'DRY RUN' if dry_run else '🚨 EJECUCIÓN REAL'}")
    print(f"{'='*60}")

    # ── 1. Parsear Excel ──
    resultado = parsear_topper(ruta_archivo)
    if not resultado or not resultado["pedidos"]:
        print("❌ No se pudieron parsear pedidos del Excel. Abortando.")
        return

    pedidos = resultado["pedidos"]
    print(f"\n📋 {len(pedidos)} pedido/s mensual/es a procesar")

    # ── 2. Procesar cada pedido mensual ──
    resultados = []
    for pedido in pedidos:
        resultado_pedido = procesar_pedido_mensual(pedido, dry_run)
        resultados.append(resultado_pedido)

    # ── 3. Resumen final ──
    print(f"\n{'='*60}")
    print(f"  RESUMEN FINAL — TOPPER")
    print(f"{'='*60}")
    print(f"  {'Mes':<10} {'Pedido':<10} {'OK':>5} {'Error':>6} {'Pares':>7} {'Importe':>15}")
    print(f"  {'─'*55}")

    total_ok = 0
    total_err = 0
    total_pares = 0
    total_importe = 0

    for r in resultados:
        num = str(r["numero_pedido"]) if r["numero_pedido"] else "—"
        print(f"  {r['mes']:<10} {num:<10} {r['renglones_ok']:>5} {r['renglones_error']:>6} "
              f"{r['total_pares']:>7} ${r['total_importe']:>13,.0f}")
        total_ok += r["renglones_ok"]
        total_err += r["renglones_error"]
        total_pares += r["total_pares"]
        total_importe += r["total_importe"]

    print(f"  {'─'*55}")
    print(f"  {'TOTAL':<10} {'':10} {total_ok:>5} {total_err:>6} {total_pares:>7} ${total_importe:>13,.0f}")

    if total_err > 0:
        print(f"\n  ⚠️  {total_err} renglones no pudieron resolverse.")
        print(f"     Estos artículos probablemente necesitan alta manual en la BD.")

    if dry_run:
        print(f"\n  ℹ️  DRY RUN completado. Revisar output y ejecutar con --ejecutar")
    else:
        print(f"\n  ✅ {len([r for r in resultados if r['numero_pedido']])} pedidos cargados exitosamente.")

    print(f"{'='*60}\n")

    return resultados


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga nota de pedido TOPPER (SAP pivoteado)")
    parser.add_argument("archivo", help="Ruta al Excel de Topper (TOPPER CALZADO COMPLETO.xlsx)")
    parser.add_argument("--dry-run",  action="store_true", default=True,
                        help="Solo simula, no escribe en BD (por defecto)")
    parser.add_argument("--ejecutar", action="store_true", default=False,
                        help="Ejecuta la inserción real en la BD")

    args = parser.parse_args()
    dry_run = not args.ejecutar

    if args.ejecutar:
        print("\n🚨 MODO EJECUCIÓN REAL — se escribirá en la base de datos")
        print(f"   Proveedor : {PROVEEDOR_NOMBRE}")
        print(f"   Archivo   : {args.archivo}")
        confirmacion = input("   ¿Confirmar? (s/N): ").strip().lower()
        if confirmacion != "s":
            print("   Cancelado.")
            sys.exit(0)

    flujo_topper(args.archivo, dry_run=dry_run)
