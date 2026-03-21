# paso4_insertar_pedido.py
# Inserta un pedido completo en pedico2 (cabecera) y pedico1 (detalle).
#
# TABLAS REALES (verificado con paso1):
#   pedico2 — cabecera de pedido de compra
#   pedico1 — detalle (renglones)
#
# PK fija para H4: empresa='H4', codigo=8, letra='X', sucursal=1
# numero y orden son autoincrementales (MAX+1)
#
# EJECUTAR:
#   python paso4_insertar_pedido.py --dry-run    ← solo imprime SQL
#   python paso4_insertar_pedido.py --ejecutar   ← escribe en BD

import sys
import pyodbc
from datetime import date, datetime
from config import CONN_COMPRAS, EMPRESA_DEFAULT, BD_BASE_H4, PROVEEDORES

# ── CONSTANTES DE PEDIDO DE COMPRA ──────────────────────────
CODIGO_PEDIDO = 8       # tipo comprobante = pedido de compra
LETRA_PEDIDO  = "X"
SUCURSAL_PEDIDO = 1

# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def get_tabla_base(tabla: str, empresa: str = None) -> str:
    """
    Retorna el nombre completo de la tabla base según la empresa.
    En DELL-SVR (producción), pedico2/pedico1 de msgestionC son vistas UNION ALL.
    Para H4, la tabla real está en MSGESTION03.dbo.
    Para CALZALINDO estaría en MSGESTION01.dbo.
    Si la empresa no requiere tabla base, retorna el nombre simple.
    """
    emp = empresa or EMPRESA_DEFAULT
    if emp == "H4":
        return f"{BD_BASE_H4}.dbo.{tabla}"
    elif emp == "CALZALINDO":
        return f"MSGESTION01.dbo.{tabla}"
    return tabla  # fallback: usa la vista


def get_proximo_numero(cursor, empresa: str = None) -> int:
    """Obtiene el próximo número disponible para pedico2."""
    tabla = get_tabla_base("pedico2", empresa)
    cursor.execute(
        f"SELECT ISNULL(MAX(numero), 0) + 1 FROM {tabla} WHERE codigo = ?",
        CODIGO_PEDIDO
    )
    return cursor.fetchone()[0]


def get_proxima_orden(cursor, empresa: str = None) -> int:
    """Obtiene la próxima orden disponible para pedico2.
    El campo orden es numeric(2,0) — máximo 99.
    Si MAX+1 > 99, vuelve a 1 (no es parte del PK, solo ordenamiento visual).
    """
    tabla = get_tabla_base("pedico2", empresa)
    cursor.execute(
        f"SELECT ISNULL(MAX(orden), 0) + 1 FROM {tabla} WHERE codigo = ?",
        CODIGO_PEDIDO
    )
    orden = cursor.fetchone()[0]
    if orden > 99:
        orden = 1
    return orden


# ──────────────────────────────────────────────────────────────
# INSERT PRINCIPAL
# ──────────────────────────────────────────────────────────────

def insertar_pedido(cabecera: dict, renglones: list, dry_run: bool = True, _standalone: bool = False):
    """
    Inserta la cabecera en pedico2 y los renglones en pedico1.
    Usa transacción: si falla cualquier renglón, hace rollback.

    Retorna el número de pedido generado, o None si falla.
    """
    validar_cabecera(cabecera)
    validar_renglones(renglones)

    ahora = datetime.now()

    # ── TABLAS BASE (evitar vistas UNION ALL que no aceptan INSERT) ──
    empresa = cabecera.get("empresa", EMPRESA_DEFAULT)
    tabla_p2 = get_tabla_base("pedico2", empresa)
    tabla_p1 = get_tabla_base("pedico1", empresa)

    # Datos del proveedor — config.py primero, BD como fallback
    prov_id = cabecera.get("cuenta", 0)
    prov_cfg = PROVEEDORES.get(prov_id)
    if not prov_cfg:
        try:
            from proveedores_db import obtener_pricing_proveedor
            import pyodbc as _pyodbc_tmp
            conn_tmp = _pyodbc_tmp.connect(CONN_COMPRAS, timeout=10)
            cur_tmp = conn_tmp.cursor()
            cur_tmp.execute(
                "SELECT denominacion, cuit, condicion_iva, zona "
                "FROM msgestionC.dbo.proveedores WHERE numero = ?", prov_id)
            row = cur_tmp.fetchone()
            conn_tmp.close()
            if row:
                prov_cfg = {
                    "nombre": (row.denominacion or "").strip(),
                    "cuit": (row.cuit or "").strip().replace("-", ""),
                    "condicion_iva": (row.condicion_iva or "I").strip(),
                    "zona": row.zona or 0,
                }
                prov_cfg.update(obtener_pricing_proveedor(prov_id))
        except Exception:
            pass
    if not prov_cfg:
        prov_cfg = {}

    # ── SQL CABECERA (pedico2) ────────────────────────────────
    # INSERT en tabla base (sin campo 'empresa' que es de la vista)
    sql_cabecera = f"""
        INSERT INTO {tabla_p2} (
            codigo, letra, sucursal,
            numero, orden, deposito,
            cuenta, denominacion,
            fecha_comprobante, fecha_proceso,
            observaciones,
            descuento_general, monto_descuento,
            bonificacion_general, monto_bonificacion,
            financiacion_general, monto_financiacion,
            iva1, monto_iva1, iva2, monto_iva2, monto_impuesto,
            importe_neto, monto_exento,
            estado, zona, condicion_iva, numero_cuit, copias,
            cuenta_y_orden, pack, reintegro, cambio, transferencia,
            entregador, usuario, campo, sistema_cc, moneda, sector,
            forma_pago, plan_canje, tipo_vcto_pago, tipo_operacion, tipo_ajuste,
            medio_pago, cuenta_cc, concurso
        ) VALUES (
            ?, ?, ?,
            ?, ?, 0,
            ?, ?,
            ?, ?,
            ?,
            0, 0, 0, 0, 0, 0,
            21, 0, 10.5, 0, 0,
            0, 0,
            'V', ?, ?, ?, 1,
            'N', 'N', 'N', 'N', 'N',
            0, 'COWORK', 0, 2, 0, 0,
            0, 'N', 0, 0, 0,
            ' ', ?, 'N'
        )
    """

    # ── SQL DETALLE (pedico1) ─────────────────────────────────
    # INSERT en tabla base (sin campo 'empresa')
    sql_detalle = f"""
        INSERT INTO {tabla_p1} (
            codigo, letra, sucursal,
            numero, orden, renglon,
            articulo, descripcion, codigo_sinonimo,
            cantidad, precio,
            cuenta, fecha, fecha_entrega,
            estado
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'V')
    """

    if dry_run:
        numero_simulado = 999999
        orden_simulada = 999
        print(f"\n[DRY RUN] ── CABECERA ({tabla_p2}) ──────────────────────")
        print(f"  empresa          = {empresa}")
        print(f"  codigo           = {CODIGO_PEDIDO}")
        print(f"  letra            = {LETRA_PEDIDO}")
        print(f"  sucursal         = {SUCURSAL_PEDIDO}")
        print(f"  numero           = {numero_simulado} (simulado — se calcula con MAX+1)")
        print(f"  orden            = {orden_simulada} (simulado — se calcula con MAX+1)")
        print(f"  cuenta           = {cabecera['cuenta']} ({cabecera['denominacion']})")
        print(f"  fecha_comprobante= {cabecera['fecha_comprobante']}")
        print(f"  observaciones    = {cabecera.get('observaciones','')}")

        print(f"\n[DRY RUN] ── DETALLE ({tabla_p1}) — {len(renglones)} renglón/es ──")
        for i, r in enumerate(renglones, 1):
            print(f"  {i:>3}. [{r['articulo']}] {r['descripcion'][:45]} x{r['cantidad']} ${r['precio']:,.2f}")

        print("\n[DRY RUN] Ningún dato fue escrito en la base.")
        return numero_simulado

    # ── EJECUCIÓN REAL ─────────────────────────────────────────
    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            conn.autocommit = False
            cursor = conn.cursor()

            numero = get_proximo_numero(cursor, empresa)
            orden = get_proxima_orden(cursor, empresa)

            # INSERT cabecera (sin campo 'empresa' — va en la tabla base)
            cursor.execute(sql_cabecera, (
                CODIGO_PEDIDO,
                LETRA_PEDIDO,
                SUCURSAL_PEDIDO,
                numero,
                orden,
                cabecera["cuenta"],
                cabecera["denominacion"],
                cabecera["fecha_comprobante"],
                ahora,   # fecha_proceso
                cabecera.get("observaciones", ""),
                prov_cfg.get("zona", 0),
                prov_cfg.get("condicion_iva", "I"),
                prov_cfg.get("cuit", ""),
                cabecera["cuenta"],   # cuenta_cc
            ))

            # INSERT renglones (sin campo 'empresa')
            fecha_entrega = cabecera.get("fecha_entrega", cabecera["fecha_comprobante"])
            for i, r in enumerate(renglones, 1):
                cursor.execute(sql_detalle, (
                    CODIGO_PEDIDO,
                    LETRA_PEDIDO,
                    SUCURSAL_PEDIDO,
                    numero,
                    orden,
                    i,          # renglon
                    r["articulo"],
                    r["descripcion"],
                    r.get("codigo_sinonimo", ""),
                    r["cantidad"],
                    r["precio"],
                    cabecera["cuenta"],
                    cabecera["fecha_comprobante"],
                    fecha_entrega,
                ))

            conn.commit()
            print(f"\n✅ Pedido insertado en {tabla_p2}. Número: {numero} | Orden: {orden} | Renglones: {len(renglones)}")
            return numero

    except Exception as e:
        print(f"\n❌ ERROR al insertar pedido: {e}")
        print("   Rollback ejecutado — ningún dato fue guardado.")
        if not _standalone:
            raise
        return None


# ──────────────────────────────────────────────────────────────
# VALIDACIONES
# ──────────────────────────────────────────────────────────────

def validar_cabecera(cabecera: dict):
    requeridos = ["empresa", "cuenta", "denominacion", "fecha_comprobante"]
    for campo in requeridos:
        if not cabecera.get(campo):
            raise ValueError(f"Campo requerido faltante en cabecera: {campo}")

def validar_renglones(renglones: list):
    if not renglones:
        raise ValueError("El pedido debe tener al menos un renglón.")
    for i, r in enumerate(renglones, 1):
        for campo in ["articulo", "descripcion", "cantidad", "precio"]:
            if r.get(campo) is None:
                raise ValueError(f"Renglón {i}: campo requerido faltante: {campo}")
        if r["cantidad"] <= 0:
            raise ValueError(f"Renglón {i}: cantidad debe ser mayor a 0")
        if r["precio"] < 0:
            raise ValueError(f"Renglón {i}: precio no puede ser negativo")


# ──────────────────────────────────────────────────────────────
# MAIN — PRUEBA CON DATO DE EJEMPLO
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]

    dry_run = modo != "--ejecutar"

    if dry_run:
        print("\n\u26a0\ufe0f  MODO DRY RUN — no se escribe nada en la base")
    else:
        print("\n\U0001f6a8 MODO EJECUCIÓN REAL — se escribirá en la base")
        confirmacion = input("   ¿Confirmar? (s/N): ").strip().lower()
        if confirmacion != "s":
            print("   Cancelado.")
            sys.exit(0)

    # Pedido de prueba
    cabecera_prueba = {
        "empresa":           "H4",
        "cuenta":            963,
        "denominacion":      "BAGUNZA SA",
        "fecha_comprobante": date(2026, 3, 10),
        "fecha_vencimiento": date(2026, 4, 10),
        "observaciones":     "30 días neto. Entrega 45 días. Período: 2026-OI",
    }

    renglones_prueba = [
        {
            "articulo":        12345,
            "descripcion":     "CHINELA VERANO BOCA JR",
            "codigo_sinonimo": "CHBOCA38",
            "cantidad":        24,
            "precio":          4500.00,
            "periodo_compra":  "2026-OI",
        },
        {
            "articulo":        12346,
            "descripcion":     "CHINELA VERANO RIVER",
            "codigo_sinonimo": "CHRIVER38",
            "cantidad":        24,
            "precio":          4500.00,
            "periodo_compra":  "2026-OI",
        },
    ]

    numero = insertar_pedido(cabecera_prueba, renglones_prueba, dry_run=dry_run, _standalone=True)

    if not dry_run and numero:
        print(f"\n\u2705 Verificar en SSMS:")
        print(f"   SELECT * FROM pedico2 WHERE numero = {numero} AND empresa = 'H4'")
        print(f"   SELECT * FROM pedico1 WHERE numero = {numero} AND empresa = 'H4'")
