"""
Parser de CSVs de tenencia descargados de brokers argentinos.
Soporta: Cocos Capital, IOL (InvertirOnline).
Cada broker tiene su formato — detectamos automáticamente.
"""
import os
import csv
import glob as globmod
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Dólar MEP aproximado — se puede actualizar manualmente o via API
DOLAR_MEP = 1180.0

# Clasificación automática de activos por ticker/nombre
ASSET_CLASS_RULES = [
    # Bonos soberanos argentinos (incluye tickers IOL con sufijo C/D)
    (r"\b(AL30|AL35|AL41|AE38|GD30|GD35|GD38|GD41|GD46|TX2[0-9]|T[2-6]X[0-9]|BONCER|BONO.*TESORO|BONO.*REP)", "Bonos Soberanos AR"),
    (r"\bAL41C\b|AL30C|GD30C|GD35C|GD38C|AE38C", "Bonos Soberanos AR"),
    # Bopreal (bonos del BCRA para importadores)
    (r"\bBOPREAL\b|BPC7C|BPD7C|BPE7C", "Bonos Soberanos AR"),
    # FCI
    (r"\bFCI\b|COCOSPPA|COCOUSDPA", "FCI / Money Market"),
    # Crypto related (antes de CEDEARs para que IBIT/MSTR/BITF matcheen acá)
    (r"\b(IBIT|MSTR|COIN|BITF|BITFC)\b|BITCOIN|CRYPTO|BITFARMS", "Crypto"),
    # CEDEARs (genérico — matchea "Cedear" en el nombre)
    (r"\bCEDEAR\b", "CEDEARs"),
    # Acciones argentinas
    (r"\b(TRAN|AUSO|TGNO4|GGAL|YPF|PAMP|TXAR|ALUA|BBAR|SUPV|COME|CRES|EDN|LOMA|MIRG|BYMA|CEPU|VALO|DGCU2|TECO2|TGSU2)\b", "Acciones AR"),
    # ON (Obligaciones Negociables)
    (r"\bON\b|OBLIGACION", "ONs"),
]


def classify_asset(instrument_name, ticker=""):
    """Clasifica un instrumento por su nombre/ticker."""
    text = f"{instrument_name} {ticker}".upper()
    for pattern, asset_class in ASSET_CLASS_RULES:
        if re.search(pattern, text):
            return asset_class
    # Default
    if "CEDEAR" in text:
        return "CEDEARs"
    if any(w in text for w in ["BONO", "BOND", "LETRA"]):
        return "Bonos Soberanos AR"
    return "Otros"


def parse_cocos_csv(filepath, owner="", source="Cocos"):
    """
    Parsea CSV de tenencia (formato genérico con ;).
    Funciona para Cocos, IOL manual, o cualquier CSV con columnas:
    instrumento;cantidad;precio;moneda;total
    """
    positions = []
    cash = []

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader, None)
        if not header:
            return positions, cash

        for row in reader:
            if len(row) < 5:
                continue
            instrumento = row[0].strip()
            cantidad_str = row[1].strip().replace(".", "").replace(",", ".")
            precio_str = row[2].strip().replace(".", "").replace(",", ".")
            moneda = row[3].strip()
            total_str = row[4].strip().replace(".", "").replace(",", ".")

            try:
                cantidad = float(cantidad_str)
                precio = float(precio_str)
                total = float(total_str)
            except ValueError:
                continue

            # Filas de saldo en efectivo (ARS, USD, EXT)
            if instrumento in ("ARS", "USD", "EXT"):
                if abs(total) > 0.01:
                    cash.append({
                        "currency": instrumento if instrumento != "EXT" else "USD",
                        "amount": total,
                        "source": "Cocos",
                        "owner": owner,
                    })
                continue

            # Extraer ticker del paréntesis: "CEDEAR AMAZON.COM, INC (AMZN)" → "AMZN"
            ticker_match = re.search(r"\(([A-Z0-9]+)\)\s*$", instrumento)
            ticker = ticker_match.group(1) if ticker_match else instrumento[:10]

            # Limpiar nombre
            name = re.sub(r"\s*\([A-Z0-9]+\)\s*$", "", instrumento).strip()

            asset_class = classify_asset(instrumento, ticker)

            # Convertir a USD si es ARS
            if moneda == "ARS":
                price_usd = precio / DOLAR_MEP
                total_usd = total / DOLAR_MEP
            else:
                price_usd = precio
                total_usd = total

            positions.append({
                "ticker": ticker,
                "name": name,
                "asset_class": asset_class,
                "qty": cantidad,
                "current_price_ars": precio if moneda == "ARS" else precio * DOLAR_MEP,
                "current_price_usd": price_usd,
                "market_value_ars": total if moneda == "ARS" else total * DOLAR_MEP,
                "market_value_usd": total_usd,
                "currency_original": moneda,
                "source": source,
                "owner": owner,
            })

    return positions, cash


def parse_iol_csv(filepath, owner=""):
    """
    Parsea CSV/XLS de tenencia de IOL.
    IOL puede exportar como HTML disfrazado de XLS (movimientos) o CSV real.
    Este parser intenta ambos formatos.
    """
    # Por ahora, placeholder hasta tener un archivo real de tenencia IOL
    # El archivo actual es de movimientos, no de tenencia
    return [], []


def detect_owner_from_filename(filename):
    """Intenta detectar el dueño del archivo por el nombre."""
    name = filename.lower()
    # Patrones comunes: "cocos lu.csv", "iol fer.csv", etc.
    for token in ["lucia", " lu.", " lu ", "_lu_", "_lu.", "lu."]:
        if token in name:
            return "Lucia"
    # Archivo termina en "lu.csv" o "lu.xls"
    if name.endswith("lu.csv") or name.endswith("lu.xls") or name.endswith("lu.xlsx"):
        return "Lucia"
    for token in ["fer", "fernando", "fern"]:
        if token in name:
            return "Fernando"
    for token in ["ana", "ani"]:
        if token in name:
            return "Ana"
    return "Sin asignar"


def load_all_portfolios():
    """
    Carga todos los CSV/XLS de la carpeta data/.
    Retorna: (all_positions, all_cash, errors)
    """
    all_positions = []
    all_cash = []
    errors = []

    if not os.path.exists(DATA_DIR):
        return all_positions, all_cash, ["Carpeta data/ no existe"]

    files = globmod.glob(os.path.join(DATA_DIR, "*"))

    for filepath in files:
        filename = os.path.basename(filepath)
        owner = detect_owner_from_filename(filename)

        if filename.lower().endswith(".csv"):
            # Detectar source por nombre de archivo
            fname_lower = filename.lower()
            if "iol" in fname_lower:
                source = "IOL"
            elif "cocos" in fname_lower:
                source = "Cocos"
            else:
                source = "Manual"

            # Detectar formato por contenido
            try:
                with open(filepath, "r", encoding="utf-8-sig") as f:
                    first_line = f.readline()
                if "instrumento" in first_line.lower() and ";" in first_line:
                    positions, cash = parse_cocos_csv(filepath, owner=owner, source=source)
                    all_positions.extend(positions)
                    all_cash.extend(cash)
                else:
                    errors.append(f"{filename}: formato CSV no reconocido")
            except Exception as e:
                errors.append(f"{filename}: {e}")

        elif filename.lower().endswith((".xls", ".xlsx")):
            # IOL exporta HTML como .xls — por ahora solo log
            errors.append(f"{filename}: archivo de movimientos IOL (necesitamos tenencia, no movimientos)")

    return all_positions, all_cash, errors


if __name__ == "__main__":
    positions, cash, errors = load_all_portfolios()
    print(f"=== Posiciones: {len(positions)} ===")
    for p in positions:
        print(f"  [{p['owner']}] {p['ticker']:8s} | {p['asset_class']:20s} | {p['qty']:>10.2f} | US$ {p['market_value_usd']:>10.2f} | {p['source']}")
    print(f"\n=== Cash: {len(cash)} ===")
    for c in cash:
        print(f"  [{c['owner']}] {c['currency']} {c['amount']:,.2f} ({c['source']})")
    if errors:
        print(f"\n=== Errores: ===")
        for e in errors:
            print(f"  {e}")
