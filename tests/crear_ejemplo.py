import pandas as pd, os

# Crea un Excel de ejemplo para probar el paso 5 y 6
df = pd.DataFrame([
    {"codigo": 12345, "descripcion": "ZAPATILLA NIKE AIR MAX", "cantidad": 12, "precio": 8500, "talle": "38", "fecha_entrega": "2026-04-15"},
    {"codigo": 12346, "descripcion": "ZAPATILLA NIKE AIR MAX", "cantidad": 12, "precio": 8500, "talle": "39", "fecha_entrega": "2026-04-15"},
    {"codigo": "",    "descripcion": "CHINELA VERANO BOCA",    "cantidad": 24, "precio": 4500, "talle": "38", "fecha_entrega": "2026-04-20"},
    {"codigo": "",    "descripcion": "CHINELA VERANO RIVER",   "cantidad": 24, "precio": 4500, "talle": "39", "fecha_entrega": "2026-04-20"},
])
os.makedirs("tests", exist_ok=True)
df.to_excel("tests/ejemplo_pedido.xlsx", index=False)
print("✅ Creado: tests/ejemplo_pedido.xlsx")
