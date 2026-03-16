# paso5b_parsear_topper.py
# Parser especializado para notas de pedido de Topper (formato SAP pivoteado).
#
# Estructura del Excel:
#   - Hojas mensuales: "ENE 26", "FEB 26", etc.
#   - Cada hoja = un pedido separado
#   - Filas = modelos+color, columnas 11-37 = talles (200..460 → talle 20..46)
#   - Col 8 = código SAP del proveedor (clave para matching en BD)
#   - Col 39 = precio lista (sin IVA)
#
# Matching en BD:
#   descripcion_1 empieza con el código SAP (ej: "025860 FAST 2.0 NEGRO...")
#   descripcion_5 = talle (ej: "41")
#
# Reglas de negocio Topper:
#   - Proveedor: ALPARGATAS S.A.I.C. (cuenta 668)
#   - Marca: TOPPER (código 314)
#   - Fecha entrega: último día del mes de cada hoja
#   - Fecha pago: 60 días después de la entrega
#   - Forma de pago: cuenta corriente
#
# EJECUTAR: python paso5b_parsear_topper.py "TOPPER CALZADO COMPLETO.xlsx"

import sys
import pandas as pd
from pathlib import Path
from datetime import date, timedelta
import calendar
import re

# ── CONSTANTES TOPPER ────────────────────────────────────────
PROVEEDOR_CUENTA = 668
PROVEEDOR_NOMBRE = "ALPARGATAS S.A.I.C."
MARCA_TOPPER     = 314
DIAS_PAGO        = 60        # fecha pago = fecha entrega + 60 días
FORMA_PAGO_TEXT  = "Cuenta corriente 60 días"

# ── LAYOUT DEL EXCEL SAP ────────────────────────────────────
FILA_INICIO_DATOS = 13       # primera fila con datos de artículos (0-indexed)
COL_GENERO        = 0
COL_CONT_NUEVO    = 1        # CONT o NUEVO
COL_MODELO        = 2
COL_COLOR         = 3
COL_DISPONIBILIDAD= 4
COL_RANGO_TALLES  = 5        # "35 AL 46"
COL_PVP           = 6
COL_CODIGO_SAP    = 8        # código artículo SAP del proveedor
COL_MES_LANZ      = 9
COL_CANT_TOTAL    = 38
COL_PRECIO_LISTA  = 39
COL_TOTAL_PESOS   = 40
COL_CATEGORIA     = 41
COL_MIX           = 42

# Columnas de talles: col 11=talle 200(20), col 12=talle 210(21), ..., col 37=talle 460(46)
TALLE_COL_INICIO  = 11
TALLE_COL_FIN     = 37       # inclusive
# El talle real = valor_header / 10 (ej: 350 → talle 35)

# ── MAPEO DE MESES ───────────────────────────────────────────
MESES = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12,
}


def parsear_nombre_hoja(nombre: str) -> date | None:
    """
    Convierte nombre de hoja "ENE 26" → date(2026, 1, 31) (último día del mes).
    """
    partes = nombre.strip().upper().split()
    if len(partes) != 2:
        return None
    mes_str, año_str = partes
    mes = MESES.get(mes_str[:3])
    if not mes:
        return None
    try:
        año = int(año_str)
        if año < 100:
            año += 2000
        ultimo_dia = calendar.monthrange(año, mes)[1]
        return date(año, mes, ultimo_dia)
    except (ValueError, TypeError):
        return None


def leer_talles_header(df: pd.DataFrame) -> dict:
    """
    Lee la fila 10 (headers de talles) y retorna {col_index: talle_int}.
    Ej: {11: 20, 12: 21, ..., 37: 46}
    """
    row = df.iloc[10]
    talles = {}
    for col_idx in range(TALLE_COL_INICIO, TALLE_COL_FIN + 1):
        val = row.iloc[col_idx]
        if pd.notna(val):
            try:
                talle_x10 = int(float(val))
                talle_real = talle_x10 // 10
                talles[col_idx] = talle_real
            except (ValueError, TypeError):
                pass
    return talles


def parsear_hoja_mensual(df: pd.DataFrame, nombre_hoja: str) -> list:
    """
    Parsea una hoja mensual y retorna lista de renglones despivoteados.
    Cada renglón = un artículo+talle con cantidad > 0.

    Retorna lista de dicts:
    {
        "codigo_sap":    str,    # código SAP del proveedor
        "modelo":        str,    # nombre del modelo
        "color":         str,
        "talle":         str,    # talle real (ej: "41")
        "cantidad":      int,
        "precio_lista":  float,  # precio unitario sin IVA
        "pvp":           float,  # precio venta público
        "genero":        str,
        "categoria":     str,
        "cont_nuevo":    str,    # CONT o NUEVO/LANZ
        "mes_hoja":      str,    # nombre de la hoja
    }
    """
    talles_map = leer_talles_header(df)
    if not talles_map:
        print(f"  ⚠️  No se encontraron headers de talles en {nombre_hoja}")
        return []

    renglones = []

    for row_idx in range(FILA_INICIO_DATOS, len(df)):
        row = df.iloc[row_idx]

        modelo = row.iloc[COL_MODELO]
        if pd.isna(modelo) or str(modelo).strip() == "":
            continue

        modelo = str(modelo).strip()
        color = str(row.iloc[COL_COLOR]).strip() if pd.notna(row.iloc[COL_COLOR]) else ""
        genero = str(row.iloc[COL_GENERO]).strip() if pd.notna(row.iloc[COL_GENERO]) else ""
        cont_nuevo = str(row.iloc[COL_CONT_NUEVO]).strip() if pd.notna(row.iloc[COL_CONT_NUEVO]) else ""
        categoria = str(row.iloc[COL_CATEGORIA]).strip() if pd.notna(row.iloc[COL_CATEGORIA]) else ""

        # Código SAP
        codigo_sap_raw = row.iloc[COL_CODIGO_SAP]
        try:
            codigo_sap = str(int(float(codigo_sap_raw)))
        except (ValueError, TypeError):
            codigo_sap = "0"

        # Precio lista (redondeado a 2 decimales)
        try:
            precio_lista = round(float(row.iloc[COL_PRECIO_LISTA]), 2)
        except (ValueError, TypeError):
            precio_lista = 0.0

        # PVP (redondeado a 2 decimales)
        try:
            pvp = round(float(row.iloc[COL_PVP]), 2)
        except (ValueError, TypeError):
            pvp = 0.0

        # Despivotear talles
        for col_idx, talle in talles_map.items():
            cant_raw = row.iloc[col_idx]
            if pd.notna(cant_raw):
                try:
                    cantidad = int(float(cant_raw))
                    if cantidad > 0:
                        renglones.append({
                            "codigo_sap":   codigo_sap,
                            "modelo":       modelo,
                            "color":        color,
                            "talle":        str(talle),
                            "cantidad":     cantidad,
                            "precio_lista": precio_lista,
                            "pvp":          pvp,
                            "genero":       genero,
                            "categoria":    categoria,
                            "cont_nuevo":   cont_nuevo,
                            "mes_hoja":     nombre_hoja,
                        })
                except (ValueError, TypeError):
                    pass

    return renglones


def parsear_topper(ruta: str) -> dict:
    """
    Función principal. Lee el Excel completo de Topper y retorna un dict:
    {
        "proveedor": {...},
        "pedidos": [
            {
                "mes": "ENE 26",
                "fecha_entrega": date(2026, 1, 31),
                "fecha_pago": date(2026, 4, 1),
                "renglones": [...],
                "total_pares": int,
                "total_importe": float,
            },
            ...
        ]
    }
    """
    path = Path(ruta)
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")

    print(f"\n📄 Leyendo nota de pedido Topper: {ruta}")
    xl = pd.ExcelFile(ruta)

    # Detectar hojas mensuales
    hojas_mensuales = []
    for nombre in xl.sheet_names:
        fecha = parsear_nombre_hoja(nombre)
        if fecha:
            hojas_mensuales.append((nombre, fecha))

    if not hojas_mensuales:
        print("❌ No se encontraron hojas mensuales (ENE 26, FEB 26, etc.)")
        return None

    print(f"  → {len(hojas_mensuales)} meses encontrados: {[h[0] for h in hojas_mensuales]}")

    pedidos = []
    total_pares_global = 0
    total_renglones_global = 0

    for nombre_hoja, fecha_entrega in hojas_mensuales:
        df = pd.read_excel(xl, sheet_name=nombre_hoja, header=None)
        renglones = parsear_hoja_mensual(df, nombre_hoja)

        if not renglones:
            print(f"  ⚠️  {nombre_hoja}: sin renglones con cantidad")
            continue

        total_pares = sum(r["cantidad"] for r in renglones)
        total_importe = sum(r["precio_lista"] * r["cantidad"] for r in renglones)
        fecha_pago = fecha_entrega + timedelta(days=DIAS_PAGO)

        pedidos.append({
            "mes":            nombre_hoja,
            "fecha_entrega":  fecha_entrega,
            "fecha_pago":     fecha_pago,
            "renglones":      renglones,
            "total_pares":    total_pares,
            "total_importe":  total_importe,
        })

        modelos_unicos = len(set((r["codigo_sap"], r["modelo"], r["color"]) for r in renglones))
        print(f"  ✅ {nombre_hoja}: {modelos_unicos} modelos, {len(renglones)} renglones (talles), {total_pares} pares, ${total_importe:,.0f}")
        total_pares_global += total_pares
        total_renglones_global += len(renglones)

    print(f"\n📊 RESUMEN TOTAL:")
    print(f"  Pedidos (meses)  : {len(pedidos)}")
    print(f"  Renglones totales: {total_renglones_global}")
    print(f"  Pares totales    : {total_pares_global}")
    print(f"  Proveedor        : {PROVEEDOR_NOMBRE} (cuenta {PROVEEDOR_CUENTA})")
    print(f"  Forma de pago    : {FORMA_PAGO_TEXT}")

    return {
        "proveedor": {
            "cuenta": PROVEEDOR_CUENTA,
            "denominacion": PROVEEDOR_NOMBRE,
        },
        "marca_codigo": MARCA_TOPPER,
        "pedidos": pedidos,
    }


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python paso5b_parsear_topper.py 'TOPPER CALZADO COMPLETO.xlsx'")
        sys.exit(0)

    ruta = sys.argv[1]
    resultado = parsear_topper(ruta)

    if resultado:
        print("\n📋 DETALLE POR MES:")
        for pedido in resultado["pedidos"]:
            print(f"\n  ─── {pedido['mes']} ───")
            print(f"  Fecha entrega: {pedido['fecha_entrega']}")
            print(f"  Fecha pago   : {pedido['fecha_pago']}")
            print(f"  Renglones    : {len(pedido['renglones'])}")
            print(f"  Pares        : {pedido['total_pares']}")

            # Mostrar primeros 5 renglones
            for r in pedido["renglones"][:5]:
                print(f"    SAP:{r['codigo_sap']:>6} | {r['modelo']:<20} {r['color']:<25} T:{r['talle']:>2} x{r['cantidad']:>2} @ ${r['precio_lista']:>10,.0f}")
            if len(pedido["renglones"]) > 5:
                print(f"    ... y {len(pedido['renglones'])-5} renglones más")

        print("\n✅ Parseo completo. Listo para paso 6.")
