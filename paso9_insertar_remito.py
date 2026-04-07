# paso9_insertar_remito.py
# Inserta un remito de ingreso (codigo=7) en compras2/compras1/comprasr/movi_stock/stock.
#
# Tablas afectadas (por empresa):
#   - {base}.dbo.compras2      (cabecera)
#   - {base}.dbo.compras1      (renglones)
#   - {base}.dbo.comprasr      (extensión remito)
#   - {base}.dbo.movi_stock    (movimientos de stock — serie='')
#   - {base}.dbo.stock         (stock actual — serie=' ' con espacio, fila consolidada)
#
# Opcionalmente vincula con pedido existente:
#   - {base01+base03}.dbo.pedico1_entregas  (vinculación — se actualiza en AMBAS bases)
#   - {base01+base03}.dbo.pedico1           (UPDATE cantidad_entregada — en AMBAS bases)
#
# CHANGELOG:
#   v2 (05-abr-2026):
#     - FIX: serie en stock = ' ' (espacio), no '' — coincide con ERP (MERGE con serie=' ')
#     - FIX: leer proveedor de BD (zona, cuit, cond_iva, denominacion) en lugar de solo config.py
#     - FIX: validación número 0 (falsy) — usar explicit check > 0
#     - FIX: pedico1_entregas se actualiza en AMBAS bases (01 y 03) como hace el ERP
#     - FIX: comprasr incluye direccion del proveedor (no string vacio)
#     - ADD: sp_sync_pedidos al final (refresca cache pedidos pendientes)
#     - ADD: get_remitos_cargados() para historial en app_carga
#     - ADD: soporte codigo=36 (devolucion) ademas de codigo=7 (ingreso)
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

CODIGO_REMITO     = 7       # remito de ingreso
CODIGO_DEVOLUCION = 36      # devolucion (NC de compra)
LETRA_REMITO      = "R"
DEPOSITO_DEFAULT  = 11


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
    """DEPRECADA — retorna ''. Serie en compras1/movi_stock = '' (vacio).
    Serie en tabla stock = ' ' (espacio) — ver SQL_STOCK_*."""
    return ''


def get_proxima_orden(cursor, base: str, codigo: int, sucursal: int, numero: int) -> int:
    """Proxima orden para un remito con mismo codigo+sucursal+numero."""
    cursor.execute(f"""
        SELECT ISNULL(MAX(orden), 0) + 1
        FROM {base}.dbo.compras2
        WHERE codigo = ? AND letra = ?
          AND sucursal = ? AND numero = ?
    """, codigo, LETRA_REMITO, sucursal, numero)
    return int(cursor.fetchone()[0])


def get_proveedor_db(cursor, cuenta: int) -> dict:
    """
    Lee datos del proveedor de la BD. Fallback a config.py si no existe.
    """
    try:
        cursor.execute("""
            SELECT TOP 1
                ISNULL(RTRIM(denominacion),'') as denominacion,
                ISNULL(zona, 1) as zona,
                ISNULL(RTRIM(condicion_iva),'I') as condicion_iva,
                ISNULL(RTRIM(cuit),'') as cuit,
                ISNULL(RTRIM(direccion),'') as direccion
            FROM msgestionC.dbo.proveedores
            WHERE numero = ?
        """, cuenta)
        row = cursor.fetchone()
        if row:
            return {
                "denominacion": row[0],
                "zona":         int(row[1]) if row[1] else 1,
                "condicion_iva": row[2] or 'I',
                "cuit":         row[3] or '',
                "direccion":    row[4] or '',
            }
    except Exception as e:
        log.warning(f"No se pudo leer proveedor {cuenta} de BD: {e}")

    # Fallback a config.py
    prov_cfg = PROVEEDORES.get(cuenta, {})
    return {
        "denominacion": prov_cfg.get("nombre", str(cuenta)),
        "zona":         prov_cfg.get("zona", 1),
        "condicion_iva": prov_cfg.get("condicion_iva", "I"),
        "cuit":         prov_cfg.get("cuit", ""),
        "direccion":    "",
    }


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
        usuario, usuario_creacion, host_creacion,
        provincia, cuenta_y_orden
    ) VALUES (
        ?, 'R', ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?,
        ?, 0, ?,
        'S', 'V', ?, ?, ?,
        'N', '1 ', 'N',
        0, 2, 2,
        ?, GETDATE(),
        'COWORK', 'COWORK', 'APP-CARGA',
        'C', 'N'
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
        ?, 'R', ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        'S', 'V', ?, ?, ?,
        'G', ?, '1 ',
        ?, ?,
        0, 0,
        0, 0,
        ?, ?, '',
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
        ?, 'R', ?, ?, ?,
        0, 0, ?,
        'S', 'N', ?,
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
        ?, 'R',
        ?, ?, ?,
        ?, ?, ?, ?,
        'N', 7, '',
        ?, ?, GETDATE(), 'WB'
    )
"""

# FIX v2: serie=' ' (espacio) en stock — fila consolidada del ERP
# El ERP usa MERGE con serie=' '. Equivalente con UPDATE/INSERT.
SQL_STOCK_UPDATE = """
    UPDATE {base}.dbo.stock
    SET stock_actual = ISNULL(stock_actual, 0) + ?
    WHERE deposito = ? AND articulo = ? AND serie = ' '
"""

SQL_STOCK_INSERT = """
    INSERT INTO {base}.dbo.stock (deposito, articulo, serie, stock_actual)
    VALUES (?, ?, ' ', ?)
"""

SQL_STOCK_EXISTS = """
    SELECT 1 FROM {base}.dbo.stock
    WHERE deposito = ? AND articulo = ? AND serie = ' '
"""

SQL_ENTREGAS_EXISTS = """
    SELECT 1 FROM {base}.dbo.pedico1_entregas
    WHERE codigo=8 AND letra='X' AND sucursal=? AND numero=? AND orden=? AND renglon=?
"""

SQL_ENTREGAS_UPDATE = """
    UPDATE {base}.dbo.pedico1_entregas
    SET cantidad = ISNULL(cantidad,0) + ?, fecha_entrega = ?
    WHERE codigo=8 AND letra='X' AND sucursal=? AND numero=? AND orden=? AND renglon=?
"""

SQL_ENTREGAS_INSERT = """
    INSERT INTO {base}.dbo.pedico1_entregas
        (codigo, letra, sucursal, numero, orden, renglon, articulo, cantidad, deposito, fecha_entrega)
    VALUES (8, 'X', ?, ?, ?, ?, ?, ?, ?, ?)
"""

SQL_PEDICO1_UPDATE = """
    UPDATE {base}.dbo.pedico1
    SET cantidad_entregada = ISNULL(cantidad_entregada,0) + ?,
        monto_entregado    = ISNULL(monto_entregado,0) + ?
    WHERE codigo=8 AND letra='X' AND sucursal=? AND numero=? AND orden=? AND renglon=?
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
        denominacion: str (opcional — se lee de BD si no viene),
        sucursal_remito: int (punto de venta del remito proveedor, > 0),
        numero_remito: int (numero del remito proveedor, > 0),
        fecha_comprobante: date,
        deposito: int (default 11),
        tipo: int (optional, 7=ingreso default, 36=devolucion),
        numero_pedido: int (opcional — para vincular pedido),
        sucursal_pedido: int (opcional, default 1),
        orden_pedido: int (opcional, default 1),
    }

    renglones: [{
        articulo: int,
        descripcion: str,
        cantidad: int,
        precio: float,
        renglon_pedido: int (opcional),
    }]

    Retorna: {"ok": True, "numero": N, "orden": O, "error": ""}
    """
    # FIX: no usar "if not" — falla con 0. Usar "is None".
    for campo in ["empresa", "cuenta", "fecha_comprobante"]:
        if cabecera.get(campo) is None:
            return {"ok": False, "numero": 0, "orden": 0,
                    "error": f"Campo requerido faltante: {campo}"}

    # FIX: validar > 0 para numericos (number_input default=0 es invalido)
    if int(cabecera.get("sucursal_remito") or 0) <= 0:
        return {"ok": False, "numero": 0, "orden": 0,
                "error": "sucursal_remito debe ser > 0"}
    if int(cabecera.get("numero_remito") or 0) <= 0:
        return {"ok": False, "numero": 0, "orden": 0,
                "error": "numero_remito debe ser > 0"}
    if not renglones:
        return {"ok": False, "numero": 0, "orden": 0,
                "error": "El remito debe tener al menos un renglón"}

    empresa   = cabecera["empresa"]
    base      = get_base_remito(empresa)
    sucursal  = int(cabecera["sucursal_remito"])
    numero    = int(cabecera["numero_remito"])
    fecha     = cabecera["fecha_comprobante"]
    deposito  = int(cabecera.get("deposito", DEPOSITO_DEFAULT))
    cuenta    = int(cabecera["cuenta"])
    tipo      = int(cabecera.get("tipo", CODIGO_REMITO))
    operacion = '+' if tipo == CODIGO_REMITO else '-'
    signo     = 1  if tipo == CODIGO_REMITO else -1

    # Totales
    total_neto = sum(r["cantidad"] * r["precio"] for r in renglones)
    total_uds  = sum(r["cantidad"] for r in renglones)

    if dry_run:
        log.info(f"[DRY RUN] Remito tipo={tipo} R{sucursal}-{numero} en {base}")
        log.info(f"  Empresa: {empresa} | Proveedor: {cuenta} | Fecha: {fecha} | Dep: {deposito}")
        log.info(f"  Renglones: {len(renglones)} | Pares: {total_uds} | Total: ${total_neto:,.0f}")
        for i, r in enumerate(renglones, 1):
            log.info(f"  {i:>3}. [{r['articulo']}] {str(r.get('descripcion',''))[:45]} x{r['cantidad']} ${r['precio']:,.2f}")
        return {"ok": True, "numero": numero, "orden": 0,
                "error": "", "dry_run": True, "total_pares": total_uds,
                "total_neto": total_neto}

    # ── EJECUCION REAL ─────────────────────────────────────────
    try:
        with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
            conn.autocommit = False
            cursor = conn.cursor()

            # Leer proveedor de BD (zona, cuit, condicion_iva, denominacion, direccion)
            prov         = get_proveedor_db(cursor, cuenta)
            denominacion = str(cabecera.get("denominacion") or prov["denominacion"])
            zona         = prov["zona"]
            cond_iva     = prov["condicion_iva"]
            cuit         = prov["cuit"]
            direccion    = (prov["direccion"] or "")[:100]

            # Orden del remito
            orden = get_proxima_orden(cursor, base, tipo, sucursal, numero)

            # 1. CABECERA compras2
            cursor.execute(SQL_REMITO_CAB.format(base=base), (
                tipo,
                sucursal, numero, orden,
                deposito, cuenta, cuenta, denominacion,
                fecha, fecha, fecha,
                total_neto, total_neto,
                zona, cond_iva, cuit,
                fecha,
            ))

            # 2. EXTENSION comprasr (incluye direccion del proveedor)
            cursor.execute(SQL_REMITO_EXT.format(base=base), (
                tipo, sucursal, numero, orden,
                fecha, direccion,
            ))

            # 3. RENGLONES compras1
            for reng, r in enumerate(renglones, 1):
                monto = round(float(r["precio"]) * int(r["cantidad"]), 2)
                desc  = str(r.get("descripcion", ""))[:60]
                cursor.execute(SQL_REMITO_DET.format(base=base), (
                    tipo, sucursal, numero, orden, reng,
                    int(r["articulo"]), desc,
                    round(float(r["precio"]), 2), int(r["cantidad"]), deposito,
                    operacion, fecha, cuenta,
                    cond_iva,
                    int(r["cantidad"]), monto,
                    int(r["cantidad"]), int(r["cantidad"]),
                ))

            # 4. MOVIMIENTOS DE STOCK (serie='' vacio, como el ERP)
            for reng, r in enumerate(renglones, 1):
                cursor.execute(SQL_MOVI_STOCK.format(base=base), (
                    deposito, int(r["articulo"]),
                    tipo, sucursal, numero, orden,
                    operacion, int(r["cantidad"]),
                    round(float(r["precio"]), 2), cuenta,
                    int(r["cantidad"]), fecha,
                ))

            # 5. STOCK (serie=' ' con espacio — fila consolidada del ERP)
            for r in renglones:
                delta = int(r["cantidad"]) * signo
                cursor.execute(SQL_STOCK_EXISTS.format(base=base),
                               (deposito, int(r["articulo"])))
                if cursor.fetchone():
                    cursor.execute(SQL_STOCK_UPDATE.format(base=base),
                                   (delta, deposito, int(r["articulo"])))
                else:
                    cursor.execute(SQL_STOCK_INSERT.format(base=base),
                                   (deposito, int(r["articulo"]), delta))

            # 6. VINCULAR PEDIDO (si viene numero_pedido)
            num_ped = cabecera.get("numero_pedido")
            suc_ped = int(cabecera.get("sucursal_pedido", 1))
            ord_ped = int(cabecera.get("orden_pedido", 1))
            if num_ped:
                num_ped = int(num_ped)
                # FIX: actualizar en AMBAS bases como hace el ERP
                for base_ped in ["MSGESTION01", "MSGESTION03"]:
                    for reng, r in enumerate(renglones, 1):
                        reng_ped = int(r.get("renglon_pedido", reng))
                        monto_r  = round(float(r["precio"]) * int(r["cantidad"]), 2)
                        cant_r   = int(r["cantidad"])
                        try:
                            cursor.execute(SQL_ENTREGAS_EXISTS.format(base=base_ped),
                                           (suc_ped, num_ped, ord_ped, reng_ped))
                            if cursor.fetchone():
                                cursor.execute(SQL_ENTREGAS_UPDATE.format(base=base_ped),
                                               (cant_r, fecha,
                                                suc_ped, num_ped, ord_ped, reng_ped))
                            else:
                                cursor.execute(SQL_ENTREGAS_INSERT.format(base=base_ped),
                                               (suc_ped, num_ped, ord_ped, reng_ped,
                                                int(r["articulo"]), cant_r, deposito, fecha))
                            cursor.execute(SQL_PEDICO1_UPDATE.format(base=base_ped),
                                           (cant_r, monto_r,
                                            suc_ped, num_ped, ord_ped, reng_ped))
                        except Exception as ep:
                            log.warning(f"pedico1_entregas {base_ped} renglon {reng_ped}: {ep}")

            conn.commit()

        # 7. SP SYNC (refresca cache de pedidos pendientes — no critico)
        try:
            with pyodbc.connect(CONN_COMPRAS, timeout=5) as conn2:
                conn2.autocommit = True
                conn2.execute("EXEC omicronvt.dbo.sp_sync_pedidos")
        except Exception:
            pass

        log.info(f"✅ Remito en {base}. tipo={tipo} R{sucursal}-{numero} ord={orden} | "
                 f"{len(renglones)} renglones, {total_uds} pares")
        return {"ok": True, "numero": numero, "orden": orden,
                "error": "", "base": base, "total_pares": total_uds,
                "total_neto": total_neto}

    except Exception as e:
        log.error(f"❌ ERROR al insertar remito: {e}")
        return {"ok": False, "numero": numero, "orden": 0, "error": str(e)}


# ──────────────────────────────────────────────────────────────
# HISTORIAL — para mostrar en app_carga
# ──────────────────────────────────────────────────────────────

def get_remitos_cargados(empresa: str = None, dias: int = 60, proveedor: int = None) -> list:
    """
    Retorna lista de remitos cargados por la app (usuario='COWORK').
    Cada item: {fecha, proveedor_num, proveedor_nom, sucursal, numero, orden,
                arts, pares, monto, base}

    empresa: 'H4' | 'CALZALINDO' | None (ambas)
    dias: cuantos dias hacia atras buscar
    proveedor: filtrar por numero de proveedor (opcional)
    """
    bases = []
    if empresa in ("H4", None):
        bases.append("MSGESTION03")
    if empresa in ("CALZALINDO", None):
        bases.append("MSGESTION01")

    resultados = []
    for base in bases:
        try:
            filtro_prov = f"AND c2.cuenta = {int(proveedor)}" if proveedor else ""
            with pyodbc.connect(CONN_COMPRAS, timeout=10) as conn:
                cur = conn.cursor()
                cur.execute(f"""
                    SELECT
                        CONVERT(varchar,c2.fecha_comprobante,103) as fecha,
                        c2.cuenta as proveedor_num,
                        ISNULL(RTRIM(p.denominacion), CAST(c2.cuenta as varchar)) as proveedor_nom,
                        c2.sucursal, c2.numero, c2.orden,
                        COUNT(c1.renglon) as arts,
                        ISNULL(SUM(c1.cantidad), 0) as pares,
                        ISNULL(c2.monto_general, 0) as monto,
                        '{base}' as base
                    FROM {base}.dbo.compras2 c2
                    LEFT JOIN {base}.dbo.compras1 c1
                        ON  c1.codigo   = c2.codigo
                        AND c1.letra    = c2.letra
                        AND c1.sucursal = c2.sucursal
                        AND c1.numero   = c2.numero
                        AND c1.orden    = c2.orden
                    LEFT JOIN msgestionC.dbo.proveedores p ON p.numero = c2.cuenta
                    WHERE c2.codigo = 7
                      AND c2.letra  = 'R'
                      AND c2.usuario IN ('COWORK', 'WB', 'APP-CARGA')
                      AND c2.fecha_comprobante >= DATEADD(day, -{int(dias)}, GETDATE())
                      {filtro_prov}
                    GROUP BY c2.fecha_comprobante, c2.cuenta, p.denominacion,
                             c2.sucursal, c2.numero, c2.orden, c2.monto_general
                    ORDER BY c2.fecha_comprobante DESC
                """)
                for row in cur.fetchall():
                    resultados.append({
                        "fecha":         row[0],
                        "proveedor_num": row[1],
                        "proveedor_nom": row[2],
                        "sucursal":      row[3],
                        "numero":        row[4],
                        "orden":         row[5],
                        "arts":          row[6],
                        "pares":         int(row[7]),
                        "monto":         float(row[8]),
                        "base":          row[9],
                    })
        except Exception as e:
            log.warning(f"get_remitos_cargados {base}: {e}")

    resultados.sort(key=lambda x: x["fecha"], reverse=True)
    return resultados


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
        print("\n🚨 MODO EJECUCION REAL — se escribira en la base")
        confirmacion = input("   ¿Confirmar? (s/N): ").strip().lower()
        if confirmacion != "s":
            print("   Cancelado.")
            sys.exit(0)

    # Ejemplo de prueba
    cab = {
        "empresa": "H4",
        "cuenta": 44,
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

    if dry_run:
        print("\n--- Historial remitos COWORK (ultimos 30 dias) ---")
        hist = get_remitos_cargados(dias=30)
        for r in hist[:10]:
            print(f"  {r['fecha']}  {r['proveedor_nom']:<30}  "
                  f"R{r['sucursal']}-{r['numero']}  {r['pares']}p  "
                  f"${r['monto']:,.0f}  [{r['base']}]")
