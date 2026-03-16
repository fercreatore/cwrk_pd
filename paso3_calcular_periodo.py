# paso3_calcular_periodo.py
# Calcula el período de compra (OI/PV o H1/H2) según industria y fecha de entrega.
#
# Reglas de negocio:
#   Zapatería / Marroquinería / Indumentaria / Cosmética:
#     Mar–Ago  → {año}-OI
#     Sep–Feb  → {año}-PV  (si mes >= 9) ó {año-1}-PV (si mes <= 2)
#
#   Deportes / Mixto_Zap_Dep:
#     Ene–Jun  → {año}-H1
#     Jul–Dic  → {año}-H2
#
# EJECUTAR: python paso3_calcular_periodo.py

from datetime import date

# Industrias que usan OI/PV
INDUSTRIAS_OI_PV = {"Zapatería", "Marroquinería", "Indumentaria", "Cosmética"}
# Industrias que usan H1/H2
INDUSTRIAS_H1_H2 = {"Deportes", "Mixto_Zap_Dep"}


def calcular_periodo(fecha_entrega: date, industria: str) -> str:
    """
    Retorna el período de compra como string.
    Ejemplos: '2026-OI', '2026-PV', '2026-H1', '2026-H2'
    
    Si la industria no es reconocida, usa OI/PV por defecto.
    Si industria es 'Sin clasificar', retorna 'SIN-PERIODO'.
    """
    if industria == "Sin clasificar":
        return "SIN-PERIODO"

    año = fecha_entrega.year
    mes = fecha_entrega.month

    if industria in INDUSTRIAS_H1_H2:
        if 1 <= mes <= 6:
            return f"{año}-H1"
        else:
            return f"{año}-H2"
    else:
        # OI/PV (Zapatería y el resto)
        if 3 <= mes <= 8:
            return f"{año}-OI"
        elif mes >= 9:
            return f"{año}-PV"
        else:  # enero-febrero
            return f"{año - 1}-PV"


def warning_destiempo(fecha_entrega: date, linea_articulo: int) -> str | None:
    """
    Detecta si la compra es 'a destiempo'.
    
    linea_articulo:
        1 = Verano    → temporada normal Sep-Feb
        2 = Invierno  → temporada normal Mar-Ago
        3 = Pretemporada → siempre OK
        4 = Atemporal → siempre OK
        5 = Colegial  → siempre OK
        6 = Seguridad → siempre OK
    
    Retorna mensaje de warning o None si está OK.
    """
    mes = fecha_entrega.month

    if linea_articulo == 1:  # Verano
        # Comprar verano en plena temporada de invierno es a destiempo
        if 3 <= mes <= 8:
            return (
                f"⚠️ COMPRA A DESTIEMPO: artículo de VERANO comprado en mes {mes} "
                f"(temporada Otoño-Invierno). Verificar si es correcto."
            )
    elif linea_articulo == 2:  # Invierno
        if mes >= 9 or mes <= 2:
            return (
                f"⚠️ COMPRA A DESTIEMPO: artículo de INVIERNO comprado en mes {mes} "
                f"(temporada Primavera-Verano). Verificar si es correcto."
            )

    return None  # OK


# ──────────────────────────────────────────────────────────────
# PRUEBAS — deben pasar todos los casos
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    casos = [
        # (fecha, industria, esperado)
        (date(2026, 4, 15),  "Zapatería",     "2026-OI"),
        (date(2026, 10, 1),  "Zapatería",     "2026-PV"),
        (date(2026, 1, 20),  "Zapatería",     "2025-PV"),   # ene-feb → temporada anterior
        (date(2026, 3, 1),   "Deportes",      "2026-H1"),
        (date(2026, 8, 15),  "Deportes",      "2026-H2"),
        (date(2026, 6, 30),  "Deportes",      "2026-H1"),
        (date(2026, 7, 1),   "Deportes",      "2026-H2"),
        (date(2026, 5, 10),  "Marroquinería", "2026-OI"),
        (date(2026, 9, 1),   "Indumentaria",  "2026-PV"),
        (date(2026, 2, 28),  "Cosmética",     "2025-PV"),
        (date(2026, 8, 31),  "Mixto_Zap_Dep", "2026-H2"),
    ]

    print("\n🧪 TESTS DE PERÍODO DE COMPRA")
    print(f"  {'Fecha':<15} {'Industria':<20} {'Esperado':<12} {'Resultado':<12} {'Estado'}")
    print(f"  {'-'*75}")
    errores = 0
    for fecha, industria, esperado in casos:
        resultado = calcular_periodo(fecha, industria)
        ok = resultado == esperado
        estado = "✅" if ok else "❌"
        if not ok:
            errores += 1
        print(f"  {str(fecha):<15} {industria:<20} {esperado:<12} {resultado:<12} {estado}")

    print(f"\n  → {len(casos)-errores}/{len(casos)} tests pasaron")

    print("\n🧪 TESTS DE COMPRA A DESTIEMPO")
    casos_dt = [
        (date(2026, 4, 1), 1, "VERANO en mes 4 → debería dar warning"),
        (date(2026, 4, 1), 2, "INVIERNO en mes 4 → OK"),
        (date(2026, 10, 1), 1, "VERANO en mes 10 → OK"),
        (date(2026, 10, 1), 2, "INVIERNO en mes 10 → debería dar warning"),
        (date(2026, 4, 1), 4, "ATEMPORAL → siempre OK"),
    ]
    for fecha, linea, descripcion in casos_dt:
        w = warning_destiempo(fecha, linea)
        print(f"\n  {descripcion}")
        print(f"  → {w if w else 'OK — sin warning'}")

    print("\n✅ Paso 3 completo.")
