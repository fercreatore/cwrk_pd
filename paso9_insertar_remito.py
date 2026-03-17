# paso9_insertar_remito.py
# Inserta un remito de ingreso (codigo=7) en compras2/compras1/comprasr/movi_stock/stock.
#
# Tablas afectadas (por empresa):
#   - {base}.dbo.compras2      (cabecera)
#   - {base}.dbo.compras1      (renglones)
#   - {base}.dbo.comprasr      (extensión remito)
#   - {base}.dbo.movi_stock    (movimientos de stock)
#   - {base}.dbo.stock         (stock actual — serie YYMM + resumen ' ')
#
# Opcionalmente vincula con pedido existente:
#   - {base}.dbo.pedico1_entregas  (vinculación)
#   - {base}.dbo.pedico1           (UPDATE cantidad_entregada)
#
# EJECUTAR:
#   python paso9_insertar_remito.py --dry-run
#   python paso9_insertar_remito.py --ejecutar

import sys
import pyodbc
import logging
from datetime import date, datetime
from config import CONN_COMPRAS, EMPRESA_DEFAULT, BD_BASE_H4, PROVEEDORES

log = logging.getLogger("insertar_remito")

CODIGO_REMITO = 7       # remito de ingreso
LETRA_REMITO  = "R"
DEPOSITO_DEFAULT = 11


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────

def get_base_remito(empresa: str = None) -> str:
    """Retorna la base real donde insertar el remito."""
    emp = empresa or EMPRESA_DEFAULT
    if emp == "H4":
        return "MSGESTION03"
    elif emp == "CALZALINDO":
        return "MSGESTION01"
    raise ValueError(f"Empresa desconocida: {emp}")


def get_serie_yymm(fecha: date = None) -> str:
    """Serie YYMM para compras1 y stock."""
    f = fecha or date.today()
    return f"{f.year % 100:02d}{f.month:02d}"


def get_proxima_orden(cursor, base: str, sucursal: int, numero: int) -> int:
    """Próxima orden para un remito con mismo sucursal+numero."""
    cursor.execute(f"""
        SELECT ISNULL(MAX(orden), 0) + 1
        FROM {base}.dbo.compras2
        WHERE codigo = ? AND letra = ?
          AND sucursal = ? AND numero = ?
    """, CODIGO_REMITO, LETRA_REMITO, sucursal, numero)
    return int(cursor.fetchone()[0])


# ──────────────────────────────────────────────────────────────
# SQL TEMPLATES
# ──────────────────────────────────────────────────────────────

SQL_REMITO_CAB = """
    INSERT INTO {base}.dbo.compras2 (
        codigo, letra, sucursal, numero, orden,
        deposito, cuenta, cuenta_cc, denominacion,
        fecha_comprobante, fecha_proceso, fecha_contable,
        concepto_gravado, concepto_no_gravado, monto_general,
        estado_stock, estado, zona, condicion_iva, numero_cuit,
        contabiliza, consignacion, venta_anticipada,
        moneda, sistema_cc, sistema_cuenta,
        fecha_vencimiento, fecha_hora,
        usuario, usuario_creacion, host_creacion
    ) VALUES (
        7, 'R', ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?,
        ?, 0, ?,
        'S', 'V', ?, ?, ?,
        'N', '1 ', 'N',
        0, 2, 2,
        ?, GETDATE(),
        'COWORK', 'COWORK', 'APP-CARGA'
    )
"""

SQL_REMITO_DET = """
    INSERT INTO {base}.dbo.compras1 (
        codigo, letra, sucursal, numero, orden, renglon,
        articulo, descripcion, precio, cantidad, deposito,
        estado_stock, estado, operacion, fecha, cuenta,
        calificacion, condicion_iva, consignacion,
        cantidad_entregada, monto_entregado,
        cantidad_devuelta, cantidad_pagada,
        monto_devuelto, monto_pagado,
        unidades, cantidad_original, serie,
        venta_anticipada, financiacion_general,
        fecha_hora, usuario_creacion, host_creacion
    ) VALUES (
        7, 'R', ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        'S', 'V', '+', ?, ?,
        'G', 'I', '1 ',
        ?, ?,
        0, 0,
        0, 0,
        ?, ?, ?,
        'N', 0,
        GETDATE(), 'COWORK', 'APP-CARGA'
    )
"""

SQL_REMITO_EXT = """
    INSERT INTO {base}.dbo.comprasr (
        codigo, letra, sucursal, numero, orden,
        cupones, bultos, fecha_vencimiento,
        precio_financiado, sin_valor_declarado, direccion,
        sector, kg, cod_postal_trans, codigo_redespacho,
        cod_postal_redespacho, campo, valor_declarado,
        ENTREGADOR2, ENTREGADOR3, origen, destino,
        cp_transporte, km_flete, tarifa_flete, importe_flete,
        recorrido_codpos, dest_codpos, rem_codpos
    ) VALUES (
        7, 'R', ?, ?, ?,
        0, 0, ?,
        'S', 'N', '',
        0, 0, 0, 0,
        0, 0, 0,
        0, 0, 0, 0,
        0, 0, 0, 0,
        0, 0, 0
    )
"""

SQL_MOVI_STOCK = """
    INSERT INTO {base}.dbo.movi_stock (
        deposito, articulo, fecha,
        codigo_comprobante, letra_comprobante,
        sucursal_comprobante, numero_comprobante, orden,
        operacion, cantidad, precio, cuenta,
        vta_anticipada, sistema, serie,
        unidades, fecha_contable, fecha_proceso, usuario
    ) VALUES (
        ?, ?, GETDATE(),
        7, 'R',
        ?, ?, ?,
        '+', ?, ?, ?,
        'N', 7, ?,
        ?, ?, GETDATE(), 'WB'
    )
"""

SQL_STOCK_UPDATE = """
    UPDATE {base}.dbo.stock
    SET stock_actual = ISNULL(stock_actual, 0) + ?
    WHERE deposito = ? AND articulo = ? AND serie = ?
"""

SQL_STOCK_INSERT = """
    INSERT INTO {base}.dbo.stock (deposito, articulo, serie, stock_actual)
    VALUES (?, ?, ?, ?)
"""

SQL_STOCK_EXISTS = """
    SELECT 1 FROM {base}.dbo.stock
    WHERE deposito = ? AND articulo = ? AND serie = ?
"""


# ──────────────────────────────────────────────────────────────
# INSERT PRINCIPAL
# ──────────────────────────────────────────────────────────────

def insertar_remito(cabecera: dict, renglones: list, dry_run: bool = True) -> dict:
    """
    Inserta un remito de ingreso completo.

    cabecera: {
        empresa: "H4" | "CALZALINDO",
        cuenta: int (proveedor),
        denominacion: str,
        sucursal_remito: int (punto de venta del remito proveedor),
        numero_remito: int (numero del remito proveedor),
        fecha_comprobante: date,
        deposito: int (default 11),
        observaciones: str (opcional),
        numero_pedido: int (opcional — para vincular con pedido existente),
    }

    renglones: [{
        articulo: int (codigo artículo),
        descripcion: str,
        cantidad: int,
        precio: float (precio unitario neto),
        codigo_sinonimo: str (opcional),
    }]

    Retorna: {"ok": True, "numero": N, "orden": O, "error": ""}
    """
    # Validar
    for campo in ["empresa", "cuenta", "denominacion", "sucursal_remito",
                   "numero_remito", "fecha_comprobante"]:
        if not cabecera.get(campo):
            return {"ok": False, "numero": 0, "orden": 0,
                    "error": f"Campo requerido faltante: {campo}"}
    if not renglones:
        return {"ok": False, "numero": 0, "orden": 0,
                "error": "El remito debe tener al menos un renglón"}

    empresa = cabecera["empresa"]
    base = get_base_remito(empresa)
    sucursal = cabecera["sucursal_remito"]
    numero = cabecera["numero_remito"]
    fecha = cabecera["fecha_comprobante"]
    deposito = cabecera.get("deposito", DEPOSITO_DEFAULT)
    cuenta = cabecera["cuenta"]
    denominacion = cabecera["denominacion"]
    serie = get_serie_yymm(fecha)

    # Pricing del proveedor
    prov_cfg = PROVEEDORES.get(cuenta, {})
    zona = prov_cfg.get("zona", 1)
    cond_iva = prov_cfg.get("condicion_iva", "I")
    cuit = prov_cfg.get("cuit", "")

    # Totales
    total_neto = sum(r["cantidad"] * r["precio"] for r in renglones)
    total_uds = sum(r["cantidad"] for r in renglones)

    if dry_run:
        log.info(f"[DRY RUN] Remito R {sucursal}-{numero} en {base}")
        log.info(f"  Proveedor: {cuenta} - {denominacion}")
        log.info(f"  Fecha: {fecha} | Depósito: {deposito}")
        log.info(f"  Renglones: {len(renglones)} | Pares: {total_uds} | Total: ${total_neto:,.0f}")
        for i, r in enumerate(renglones, 1):
            log.info(f"  {i:>3}. [{r['articulo']}] {r['descripcion'][:45]} x{r['cantidad']} ${r['precio']:,.2f}")
        return {"ok": True, "numero": numero, "orden": 0,
                "error": "", "dry_run": True, "total_pares": total_uds,
                "total_neto": total_neto}

    # ── EJECUCIÓN REAL ─────────────────────────────────────────
    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            conn.autocommit = False
            cursor = conn.cursor()

            # Orden del remito
            orden = get_proxima_orden(cursor, base, sucursal, numero)

            # 1. CABECERA compras2
            cursor.execute(SQL_REMITO_CAB.format(base=base), (
                sucursal, numero, orden,
                deposito, cuenta, cuenta, denominacion,
                fecha, fecha, fecha,
                total_neto, total_neto,
                zona, cond_iva, cuit,
                fecha,
            ))

            # 2. EXTENSIÓN comprasr
            cursor.execute(SQL_REMITO_EXT.format(base=base), (
                sucursal, numero, orden,
                fecha,
            ))

            # 3. RENGLONES compras1
            for reng, r in enumerate(renglones, 1):
                monto = round(r["precio"] * r["cantidad"], 2)
                cursor.execute(SQL_REMITO_DET.format(base=base), (
                    sucursal, numero, orden, reng,
                    r["articulo"], r["descripcion"],
                    round(r["precio"], 2), r["cantidad"], deposito,
                    fecha, cuenta,
                    r["cantidad"], monto,
                    r["cantidad"], r["cantidad"], serie,
                ))

            # 4. MOVIMIENTOS DE STOCK
            for reng, r in enumerate(renglones, 1):
                cursor.execute(SQL_MOVI_STOCK.format(base=base), (
                    deposito, r["articulo"],
                    sucursal, numero, orden,
                    r["cantidad"], round(r["precio"], 2), cuenta,
                    serie,
                    r["cantidad"], fecha,
                ))

            # 5. ACTUALIZAR STOCK (serie YYMM + resumen ' ')
            for r in renglones:
                for s in [serie, " "]:
                    cursor.execute(SQL_STOCK_EXISTS.format(base=base),
                                   (deposito, r["articulo"], s))
                    if cursor.fetchone():
                        cursor.execute(SQL_STOCK_UPDATE.format(base=base),
                                       (r["cantidad"], deposito, r["articulo"], s))
                    else:
                        cursor.execute(SQL_STOCK_INSERT.format(base=base),
                                       (deposito, r["articulo"], s, r["cantidad"]))

            conn.commit()
            log.info(f"✅ Remito insertado en {base}. R {sucursal}-{numero} orden {orden} | "
                     f"{len(renglones)} renglones, {total_uds} pares")
            return {"ok": True, "numero": numero, "orden": orden,
                    "error": "", "base": base, "total_pares": total_uds,
                    "total_neto": total_neto}

    except Exception as e:
        log.error(f"❌ ERROR al insertar remito: {e}")
        return {"ok": False, "numero": numero, "orden": 0, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# MAIN — PRUEBA
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]
    dry_run = modo != "--ejecutar"

    if dry_run:
        print("\n⚠️  MODO DRY RUN — no se escribe nada en la base")
    else:
        print("\n🚨 MODO EJECUCIÓN REAL — se escribirá en la base")
        confirmacion = input("   ¿Confirmar? (s/N): ").strip().lower()
        if confirmacion != "s":
            print("   Cancelado.")
            sys.exit(0)

    # Ejemplo de prueba
    cab = {
        "empresa": "H4",
        "cuenta": 44,
        "denominacion": "AMPHORA",
        "sucursal_remito": 5000,
        "numero_remito": 99999,
        "fecha_comprobante": date.today(),
        "deposito": 11,
    }
    reng = [
        {"articulo": 999999, "descripcion": "TEST REMITO", "cantidad": 1, "precio": 1000.0},
    ]

    resultado = insertar_remito(cab, reng, dry_run=dry_run)
    print(f"\nResultado: {resultado}")
