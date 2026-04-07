# paso5_parsear_excel.py
# Lee una nota de pedido desde Excel o CSV y la normaliza
# a la estructura estándar del sistema.
#
# EJECUTAR: python paso5_parsear_excel.py ruta/al/archivo.xlsx
#           python paso5_parsear_excel.py ruta/al/archivo.csv
#
# El script intenta detectar automáticamente las columnas.
# Si no puede, muestra las columnas disponibles y pide confirmación.

import sys
import pandas as pd
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# MAPEO DE NOMBRES DE COLUMNAS
# Agregá aquí los nombres que usán tus proveedores.
# Formato: "nombre en el excel" → "nombre interno"
# ──────────────────────────────────────────────────────────────
MAPEO_COLUMNAS = {
    # Código artículo / modelo
    "codigo":           "codigo_articulo",
    "cod":              "codigo_articulo",
    "cod.":             "codigo_articulo",
    "codigo articulo":  "codigo_articulo",
    "art":              "codigo_articulo",
    "articulo":         "codigo_articulo",
    "modelo":           "codigo_articulo",
    "referencia":       "codigo_articulo",
    "ref":              "codigo_articulo",
    "ref.":             "codigo_articulo",
    "item":             "codigo_articulo",

    # Descripción
    "descripcion":      "descripcion",
    "descripción":      "descripcion",
    "producto":         "descripcion",
    "detalle":          "descripcion",
    "nombre":           "descripcion",
    "desc":             "descripcion",
    "descripcion_1":    "descripcion",

    # Cantidad
    "cantidad":         "cantidad",
    "cant":             "cantidad",
    "cant.":            "cantidad",
    "qty":              "cantidad",
    "unidades":         "cantidad",
    "pares":            "cantidad",
    "und":              "cantidad",

    # Precio
    "precio":           "precio",
    "precio unitario":  "precio",
    "precio unit":      "precio",
    "precio unit.":     "precio",
    "precio s/iva":     "precio",
    "p.unit":           "precio",
    "p.unit.":          "precio",
    "p unit":           "precio",
    "costo":            "precio",
    "precio mayorista": "precio",
    "precio lista":     "precio",
    "valor":            "precio",

    # Color
    "color":            "color",
    "descripcion_4":    "color",

    # Talle / sinónimo
    "talle":            "talle",
    "numero":           "talle",
    "número":           "talle",
    "nro":              "talle",
    "num":              "talle",
    "medida":           "talle",
    "descripcion_5":    "talle",
    "sinonimo":         "codigo_sinonimo",
    "sinónimo":         "codigo_sinonimo",
    "cod sinonimo":     "codigo_sinonimo",
    "codigo_sinonimo":  "codigo_sinonimo",
    "codigo sinonimo":  "codigo_sinonimo",
    "codigo barra":     "codigo_barra",
    "codigo_barra":     "codigo_barra",
    "ean":              "codigo_barra",

    # Proveedor
    "proveedor":        "proveedor",

    # Descuento
    "descuento":        "descuento",
    "bonificacion":     "descuento",
    "bonificación":     "descuento",
    "desc%":            "descuento",
    "dto":              "descuento",

    # Fechas
    "fecha entrega":    "fecha_entrega",
    "entrega":          "fecha_entrega",
    "fecha pago":       "fecha_pago",
    "vencimiento":      "fecha_pago",

    # Condiciones
    "condiciones":      "condiciones",
    "obs":              "observaciones",
    "observaciones":    "observaciones",
    "notas":            "observaciones",
}

COLUMNAS_OBLIGATORIAS = ["descripcion", "cantidad", "precio"]
COLUMNAS_RECOMENDADAS = ["codigo_articulo", "talle", "fecha_entrega"]


# ──────────────────────────────────────────────────────────────
# PARSEO
# ──────────────────────────────────────────────────────────────

def leer_archivo(ruta: str) -> pd.DataFrame:
    """Lee Excel o CSV y retorna DataFrame crudo."""
    path = Path(ruta)
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")

    if path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(ruta, header=0)
    elif path.suffix.lower() == ".csv":
        # Intenta detectar separador
        df = pd.read_csv(ruta, sep=None, engine="python", encoding="utf-8-sig")
    else:
        raise ValueError(f"Formato no soportado: {path.suffix}. Usar .xlsx, .xls o .csv")

    return df


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renombra columnas usando el MAPEO_COLUMNAS.
    Las columnas que no estén en el mapeo se conservan como están.
    """
    # Limpiar nombres: minúsculas, sin espacios extra
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Aplicar mapeo
    df = df.rename(columns={k: v for k, v in MAPEO_COLUMNAS.items() if k in df.columns})

    return df


def validar_columnas(df: pd.DataFrame) -> list:
    """Retorna lista de columnas obligatorias que faltan."""
    return [c for c in COLUMNAS_OBLIGATORIAS if c not in df.columns]


def limpiar_datos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza básica:
    - Elimina filas completamente vacías
    - Convierte cantidad y precio a numérico
    - Normaliza textos
    """
    # Eliminar filas vacías
    df = df.dropna(how="all")

    # Cantidad
    if "cantidad" in df.columns:
        df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce")
        df = df[df["cantidad"] > 0]  # eliminar filas con cantidad 0 o inválida

    # Precio
    if "precio" in df.columns:
        # Limpiar símbolos de moneda
        if df["precio"].dtype == object:
            df["precio"] = df["precio"].astype(str).str.replace(r"[$,\s]", "", regex=True)
        df["precio"] = pd.to_numeric(df["precio"], errors="coerce").fillna(0)

    # Descripción: normalizar texto
    if "descripcion" in df.columns:
        df["descripcion"] = df["descripcion"].astype(str).str.strip().str.upper()

    # Talle
    if "talle" in df.columns:
        df["talle"] = df["talle"].astype(str).str.strip()

    return df.reset_index(drop=True)


def parsear_nota(ruta: str) -> pd.DataFrame | None:
    """
    Función principal: lee, normaliza y limpia una nota de pedido.
    Retorna DataFrame listo para usar en el flujo de carga.
    """
    print(f"\n📄 Leyendo: {ruta}")

    df = leer_archivo(ruta)
    print(f"  → {len(df)} filas, {len(df.columns)} columnas encontradas")
    print(f"  → Columnas originales: {list(df.columns)}")

    df = normalizar_columnas(df)
    print(f"  → Columnas normalizadas: {list(df.columns)}")

    faltantes = validar_columnas(df)
    if faltantes:
        print(f"\n⚠️  Columnas obligatorias no encontradas: {faltantes}")
        print("   Revisar el mapeo en MAPEO_COLUMNAS o ajustar el Excel.")
        return None

    # Avisar de recomendadas ausentes
    ausentes_rec = [c for c in COLUMNAS_RECOMENDADAS if c not in df.columns]
    if ausentes_rec:
        print(f"\n⚠️  Columnas recomendadas ausentes: {ausentes_rec}")
        print("   El sistema puede funcionar pero con datos incompletos.")

    df = limpiar_datos(df)
    print(f"\n✅ {len(df)} renglones válidos después de limpieza")

    return df


# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python paso5_parsear_excel.py ruta/al/archivo.xlsx")
        print("\nCrea un Excel de prueba con columnas:")
        print("  codigo | descripcion | cantidad | precio | talle | fecha_entrega")
        sys.exit(0)

    ruta = sys.argv[1]
    df = parsear_nota(ruta)

    if df is not None:
        print("\n📋 PREVIEW (primeras 5 filas):")
        print(df.head().to_string())

        print("\n📊 RESUMEN:")
        print(f"  Total renglones  : {len(df)}")
        if "cantidad" in df.columns:
            print(f"  Total unidades   : {df['cantidad'].sum():.0f}")
        if "precio" in df.columns and "cantidad" in df.columns:
            df["subtotal"] = df["precio"] * df["cantidad"]
            print(f"  Total importe    : ${df['subtotal'].sum():,.2f}")
        if "fecha_entrega" in df.columns:
            print(f"  Fechas entrega   : {df['fecha_entrega'].unique()}")

        print("\n✅ Paso 5 completo. DataFrame listo para paso 6.")
