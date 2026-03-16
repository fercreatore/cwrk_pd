# completar_action_team_134040.py
# Agrega renglones al pedido EXISTENTE #134040 (3302 ACTION TEAM — PALUBEL)
# para completar 3 meses de cobertura según análisis de quiebre.
#
# Pedido existente: 10 renglones, 32 pares
# Este script agrega: 23 renglones, 208 pares
# Total final: 33 renglones, 240 pares @ $24,000 = $5,760,000 + IVA
#
# ANÁLISIS DE QUIEBRE (ene 2023 - mar 2026):
#   - 3302 vende 94 pares/mes (vel real combinada NEGRO+CHOCO)
#   - Stock actual: 44 pares (0.5 meses)
#   - Pedido original: 32 pares → cobertura total 0.8 meses
#   - Split ventas: NEGRO 60% / CHOCO 40%
#   - Talles top: T42 (16%), T43 (16.6%), T44 (13.3%), T45 (10.4%)
#   - T45/T46 NO estaban en pedido y tienen 0.5m cobertura
#
# EJECUTAR EN EL 111:
#   py -3 completar_action_team_134040.py --dry-run     ← solo muestra
#   py -3 completar_action_team_134040.py --ejecutar    ← escribe en producción

import sys
import pyodbc
from datetime import date, datetime

# ── CONEXIÓN ───────────────────────────────────────────────
CONN_STR = (
    "DRIVER={SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=MSGESTION03;"
    "UID=am;PWD=dl"
)

# ── PEDIDO EXISTENTE ───────────────────────────────────────
NUMERO_PEDIDO = 134040
CODIGO = 8
LETRA = "X"
SUCURSAL = 1
ORDEN = 67
CUENTA = 217          # proveedor PALUBEL ACTION TEAM
PRECIO = 24000        # $24,000 por par (precio costo sin IVA)
FECHA = date(2026, 2, 20)
FECHA_ENTREGA = date(2026, 5, 5)

# ── RENGLONES DIFERENCIALES (23 líneas) ───────────────────
# Calculados como: necesario_3_meses - (stock_actual + pedido_existente)
# Solo se agregan los que necesitan más de lo que ya hay
renglones_nuevos = [
    # ── NEGRO (146 pares) ──
    {"renglon": 11, "articulo": 263985, "descripcion": "3302 NEGRO ZAPATILLA TREKKING ACORDONADA", "cantidad":  1, "talle": "36", "sinonimo": "217330200036"},
    {"renglon": 12, "articulo": 263984, "descripcion": "3302 NEGRO ZAPATILLA TREKKING ACORDONADA", "cantidad":  1, "talle": "37", "sinonimo": "217330200037"},
    {"renglon": 13, "articulo": 263983, "descripcion": "3302 NEGRO ZAPATILLA TREKKING ACORDONADA", "cantidad":  5, "talle": "38", "sinonimo": "217330200038"},
    {"renglon": 14, "articulo": 133731, "descripcion": "3302 NEGRO ZAPATILLA TREKKING ACORDONADA", "cantidad":  9, "talle": "39", "sinonimo": "217330200039"},
    {"renglon": 15, "articulo": 133732, "descripcion": "3302 NEGRO ZAPATILLA TREKKING ACORDONADA", "cantidad": 10, "talle": "40", "sinonimo": "217330200040"},
    {"renglon": 16, "articulo": 133733, "descripcion": "3302 NEGRO ZAPATILLA TREKKING ACORDONADA", "cantidad": 14, "talle": "41", "sinonimo": "217330200041"},
    {"renglon": 17, "articulo": 133734, "descripcion": "3302 NEGRO ZAPATILLA TREKKING ACORDONADA", "cantidad": 21, "talle": "42", "sinonimo": "217330200042"},
    {"renglon": 18, "articulo": 133735, "descripcion": "3302 NEGRO ZAPATILLA TREKKING ACORDONADA", "cantidad": 21, "talle": "43", "sinonimo": "217330200043"},
    {"renglon": 19, "articulo": 133736, "descripcion": "3302 NEGRO ZAPATILLA TREKKING ACORDONADA", "cantidad": 17, "talle": "44", "sinonimo": "217330200044"},
    {"renglon": 20, "articulo": 133737, "descripcion": "3302 NEGRO ZAPATILLA TREKKING ACORDONADA", "cantidad": 15, "talle": "45", "sinonimo": "217330200045"},
    {"renglon": 21, "articulo": 133738, "descripcion": "3302 NEGRO ZAPATILLA TREKKING ACORDONADA", "cantidad": 11, "talle": "46", "sinonimo": "217330200046"},
    {"renglon": 22, "articulo": 263977, "descripcion": "3302 NEGRO ZAPATILLA TREKKING ACORDONADA", "cantidad":  6, "talle": "47", "sinonimo": "217330200047"},
    # ── CHOCO (62 pares) ──
    {"renglon": 23, "articulo": 267205, "descripcion": "3302 CHOCO ZAPATILLA TREKKING ACORDONADA", "cantidad":  1, "talle": "37", "sinonimo": "217330200137"},
    {"renglon": 24, "articulo": 267204, "descripcion": "3302 CHOCO ZAPATILLA TREKKING ACORDONADA", "cantidad":  1, "talle": "38", "sinonimo": "217330200138"},
    {"renglon": 25, "articulo":  81434, "descripcion": "3302 CHOCO ZAPATILLA TREKKING ACORDONADA", "cantidad":  4, "talle": "39", "sinonimo": "217330200139"},
    {"renglon": 26, "articulo": 110401, "descripcion": "3302 CHOCO ZAPATILLA TREKKING ACORDONADA", "cantidad":  5, "talle": "40", "sinonimo": "217330200140"},
    {"renglon": 27, "articulo": 110402, "descripcion": "3302 CHOCO ZAPATILLA TREKKING ACORDONADA", "cantidad":  7, "talle": "41", "sinonimo": "217330200141"},
    {"renglon": 28, "articulo": 110403, "descripcion": "3302 CHOCO ZAPATILLA TREKKING ACORDONADA", "cantidad": 13, "talle": "42", "sinonimo": "217330200142"},
    {"renglon": 29, "articulo": 110404, "descripcion": "3302 CHOCO ZAPATILLA TREKKING ACORDONADA", "cantidad": 16, "talle": "43", "sinonimo": "217330200143"},
    {"renglon": 30, "articulo": 110405, "descripcion": "3302 CHOCO ZAPATILLA TREKKING ACORDONADA", "cantidad":  9, "talle": "44", "sinonimo": "217330200144"},
    {"renglon": 31, "articulo": 110406, "descripcion": "3302 CHOCO ZAPATILLA TREKKING ACORDONADA", "cantidad": 10, "talle": "45", "sinonimo": "217330200145"},
    {"renglon": 32, "articulo": 133730, "descripcion": "3302 CHOCO ZAPATILLA TREKKING ACORDONADA", "cantidad":  8, "talle": "46", "sinonimo": "217330200146"},
    {"renglon": 33, "articulo": 263978, "descripcion": "3302 CHOCO ZAPATILLA TREKKING ACORDONADA", "cantidad":  3, "talle": "47", "sinonimo": "217330200147"},
]


def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]

    dry_run = modo != "--ejecutar"

    total_pares_nuevos = sum(r["cantidad"] for r in renglones_nuevos)
    total_negro = sum(r["cantidad"] for r in renglones_nuevos if "NEGRO" in r["descripcion"])
    total_choco = sum(r["cantidad"] for r in renglones_nuevos if "CHOCO" in r["descripcion"])
    total_monto_nuevo = total_pares_nuevos * PRECIO

    print(f"\n{'='*70}")
    print(f"COMPLETAR PEDIDO #134040 — 3302 ACTION TEAM (PALUBEL)")
    print(f"{'='*70}")
    print(f"  Renglones existentes: 10 (32 pares)")
    print(f"  Renglones a agregar:  {len(renglones_nuevos)} ({total_pares_nuevos} pares)")
    print(f"    NEGRO: {total_negro} pares")
    print(f"    CHOCO: {total_choco} pares")
    print(f"  Monto adicional: ${total_monto_nuevo:,.0f} + IVA")
    print(f"  TOTAL FINAL: {32 + total_pares_nuevos} pares | ${(32 + total_pares_nuevos) * PRECIO:,.0f}")
    print(f"  Base destino: MSGESTION03.dbo.pedico1")
    print(f"{'='*70}")

    print(f"\n  Renglones:")
    for r in renglones_nuevos:
        color = "NEGRO" if "NEGRO" in r["descripcion"] else "CHOCO"
        print(f"    R{r['renglon']:>2}: {color:<6} T{r['talle']:<3} x{r['cantidad']:>2}  (art {r['articulo']})")

    if dry_run:
        print(f"\n  >>> MODO DRY-RUN — no se escribió nada")
        print(f"  >>> Para ejecutar: py -3 completar_action_team_134040.py --ejecutar")
        return

    # ── CONFIRMACIÓN ──
    confirmacion = input(f"\n¿Confirmar INSERT de {total_pares_nuevos} pares en producción? (s/N): ").strip().lower()
    if confirmacion != "s":
        print("Cancelado.")
        return

    # ── CONEXIÓN ──
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()

    # ── Verificar que el pedido existe ──
    cursor.execute(
        "SELECT COUNT(*) FROM MSGESTION03.dbo.pedico2 WHERE numero = ? AND codigo = ?",
        NUMERO_PEDIDO, CODIGO
    )
    if cursor.fetchone()[0] == 0:
        print(f"ERROR: No se encontró pedido #{NUMERO_PEDIDO} en MSGESTION03.dbo.pedico2")
        conn.close()
        return

    # ── Verificar último renglón actual ──
    cursor.execute(
        "SELECT MAX(renglon) FROM MSGESTION03.dbo.pedico1 WHERE numero = ? AND codigo = ?",
        NUMERO_PEDIDO, CODIGO
    )
    max_renglon = cursor.fetchone()[0] or 0
    print(f"\n  Último renglón existente: {max_renglon}")

    if max_renglon >= 11:
        print(f"  ADVERTENCIA: Ya existen renglones >= 11. Ajustando numeración...")
        offset = max_renglon - 10
        for r in renglones_nuevos:
            r["renglon"] += offset

    # ── INSERT renglones ──
    inserted = 0
    for r in renglones_nuevos:
        try:
            cursor.execute("""
                INSERT INTO MSGESTION03.dbo.pedico1
                    (codigo, letra, sucursal, numero, orden, renglon,
                     articulo, descripcion, precio, unidades, cantidad,
                     descuento_reng1, descuento_reng2, deposito, estado,
                     fecha, fecha_entrega, cuenta, cantidad_facturada,
                     cantidad_devuelta, cantidad_entregada, cantidad_pagada,
                     monto_facturado, monto_devuelto, monto_entregado, monto_pagado,
                     descuento_general, bonificacion_general, financiacion_general,
                     condicion_iva, iva1, iva2, descripcion_2,
                     cuenta_y_orden, zona, pack, reintegro, cambio, transferencia,
                     serie, entregador, tipo_medida, moneda,
                     codigo_sinonimo, forma_pago, plan_canje,
                     cuenta_cc, cantidad_cancelada, campania,
                     codigo_proveedor, codigo_art_prov, codigo_parte,
                     unidad_usada, precio_lista, desc_especial, desc_aplicados,
                     isbn, precio_fabrica,
                     descuento_reng3, descuento_reng4, descuento_reng5,
                     sector_contable, sistema_cc, fecha_hora, fecha_pago)
                VALUES
                    (?, ?, ?, ?, ?, ?,
                     ?, ?, ?, 0, ?,
                     0, 0, 0, 'V',
                     ?, ?, ?, 0,
                     0, 0, 0,
                     0, 0, 0, 0,
                     0, 0, 0,
                     'I', 21, 10.5, '',
                     'N', 3, 'N', 'N', 'N', 'N',
                     ' ', 0, 0, 0,
                     ?, 0, 'N',
                     ?, 0, 20042005,
                     0, '                              ', '                              ',
                     '', 0, 0, '',
                     ?, 0,
                     0, 0, 0,
                     0, 2, ?, ?)
            """,
                CODIGO, LETRA, SUCURSAL, NUMERO_PEDIDO, ORDEN, r["renglon"],
                r["articulo"], r["descripcion"], PRECIO, r["cantidad"],
                FECHA, FECHA_ENTREGA, CUENTA,
                r["sinonimo"],
                CUENTA,
                r["sinonimo"],
                datetime.now(), FECHA_ENTREGA,
            )
            inserted += 1
            print(f"    ✅ R{r['renglon']:>2}: T{r['talle']} x{r['cantidad']} ({r['descripcion'][:30]}...)")
        except Exception as e:
            print(f"    ❌ R{r['renglon']:>2}: ERROR — {e}")

    # ── UPDATE pedico2 totales ──
    if inserted > 0:
        neto_nuevo = total_pares_nuevos * PRECIO
        iva_nuevo = round(neto_nuevo * 0.21)

        cursor.execute("""
            UPDATE MSGESTION03.dbo.pedico2
            SET importe_neto = importe_neto + ?,
                monto_iva1 = monto_iva1 + ?,
                importe_neto1 = importe_neto1 + ?,
                importe_iva1 = importe_iva1 + ?
            WHERE numero = ? AND codigo = ?
        """, neto_nuevo + iva_nuevo, iva_nuevo, neto_nuevo, iva_nuevo,
             NUMERO_PEDIDO, CODIGO)

        conn.commit()
        print(f"\n  ✅ {inserted}/{len(renglones_nuevos)} renglones insertados")
        print(f"  ✅ Totales pedico2 actualizados (+${neto_nuevo:,.0f} neto, +${iva_nuevo:,.0f} IVA)")
        print(f"  ✅ Pedido #{NUMERO_PEDIDO} ahora tiene {10 + inserted} renglones, {32 + total_pares_nuevos} pares")
    else:
        print(f"\n  ⚠️ No se insertó ningún renglón")

    conn.close()


if __name__ == "__main__":
    main()
