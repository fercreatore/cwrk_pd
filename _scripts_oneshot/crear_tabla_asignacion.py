# crear_tabla_asignacion.py
# Crea la tabla proveedor_asignacion_base en omicronvt
# Mapea cada proveedor (por código numérico) a empresa H4/CALZALINDO y base msgestion03/msgestion01.
#
# Lógica de asignación:
#   1. Consulta facturas (compras2) 2024-2026 en ambas bases (01 y 03)
#   2. Si un proveedor factura SOLO en base 01 → CALZALINDO
#   3. Si un proveedor factura SOLO en base 03 → H4
#   4. Si factura en ambas → asigna según mayor volumen (>= 65% → esa base)
#   5. Override manual desde config.py para proveedores con empresa explícita
#   6. Default para proveedores sin historial de facturación → H4
#
# EJECUTAR EN EL 111:
#   cd C:\cowork_pedidos && set PYTHONPATH=C:\cowork_pedidos && py -3 _scripts_oneshot\crear_tabla_asignacion.py --ejecutar

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import pyodbc

# ── Conexión directa a omicronvt en 111 ──
CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=omicronvt;"
    "UID=am;PWD=dl;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=15;"
)

# ── Overrides manuales desde config.py ──
# proveedor_codigo → (empresa, base)
OVERRIDES = {
    104: ("CALZALINDO", "msgestion01"),   # GTN - 100% base 01
    236: ("CALZALINDO", "msgestion01"),   # CONFORTABLE - 100% base 01
    668: ("H4",         "msgestion03"),   # ALPARGATAS
    594: ("H4",         "msgestion03"),   # VICBOR / WAKE
    656: ("H4",         "msgestion03"),   # DISTRINANDO / REEBOK
    561: ("H4",         "msgestion03"),   # SOUTER / RINGO
    614: ("H4",         "msgestion03"),   # CALZADOS BLANCO / DIADORA
    44:  ("H4",         "msgestion03"),   # AMPHORA
    42:  ("H4",         "msgestion03"),   # LESEDIFE
}


def main():
    modo = "--dry-run"
    if len(sys.argv) > 1:
        modo = sys.argv[1]

    dry_run = modo != "--ejecutar"

    conn = pyodbc.connect(CONN_STR, timeout=15)
    cursor = conn.cursor()

    # ── Paso 1: Obtener todos los proveedores distintos de la vista combinada ──
    print("\n[1] Consultando proveedores desde msgestionC.dbo.proveedores...")
    cursor.execute("""
        SELECT DISTINCT p.proveedor, p.denominacion
        FROM msgestionC.dbo.proveedores p
        WHERE p.proveedor IS NOT NULL
          AND p.proveedor > 0
        ORDER BY p.proveedor
    """)
    proveedores = {int(row[0]): row[1].strip() if row[1] else '' for row in cursor.fetchall()}
    print(f"    {len(proveedores)} proveedores encontrados")

    # ── Paso 2: Contar facturas por proveedor en cada base ──
    print("[2] Contando facturas por base (2024-2026)...")

    # Base 01 (CALZALINDO)
    cursor.execute("""
        SELECT c.cuenta, COUNT(*) AS cnt, SUM(c.monto_general) AS monto
        FROM MSGESTION01.dbo.compras2 c
        WHERE c.fecha_comprobante >= '2024-01-01'
          AND c.codigo IN (1, 2) AND c.estado = 'V'
          AND c.cuenta IS NOT NULL AND c.cuenta > 0
        GROUP BY c.cuenta
    """)
    facturacion_01 = {}
    for row in cursor.fetchall():
        facturacion_01[int(row[0])] = {"cnt": int(row[1]), "monto": float(row[2] or 0)}

    # Base 03 (H4)
    cursor.execute("""
        SELECT c.cuenta, COUNT(*) AS cnt, SUM(c.monto_general) AS monto
        FROM MSGESTION03.dbo.compras2 c
        WHERE c.fecha_comprobante >= '2024-01-01'
          AND c.codigo IN (1, 2) AND c.estado = 'V'
          AND c.cuenta IS NOT NULL AND c.cuenta > 0
        GROUP BY c.cuenta
    """)
    facturacion_03 = {}
    for row in cursor.fetchall():
        facturacion_03[int(row[0])] = {"cnt": int(row[1]), "monto": float(row[2] or 0)}

    print(f"    Base 01: {len(facturacion_01)} proveedores con facturas")
    print(f"    Base 03: {len(facturacion_03)} proveedores con facturas")

    # ── Paso 3: Asignar empresa/base a cada proveedor ──
    print("[3] Asignando empresa/base...")
    asignaciones = []
    stats = {"OVERRIDE": 0, "SOLO_01": 0, "SOLO_03": 0, "MAYORIA_01": 0, "MAYORIA_03": 0, "DEFAULT_H4": 0}

    for prov_id, denominacion in sorted(proveedores.items()):
        # Override manual
        if prov_id in OVERRIDES:
            empresa, base = OVERRIDES[prov_id]
            asignaciones.append((prov_id, empresa, base, denominacion))
            stats["OVERRIDE"] += 1
            continue

        m01 = facturacion_01.get(prov_id, {"cnt": 0, "monto": 0})["monto"]
        m03 = facturacion_03.get(prov_id, {"cnt": 0, "monto": 0})["monto"]
        total = m01 + m03

        if total == 0:
            # Sin facturación reciente → default H4
            asignaciones.append((prov_id, "H4", "msgestion03", denominacion))
            stats["DEFAULT_H4"] += 1
        elif m03 == 0:
            asignaciones.append((prov_id, "CALZALINDO", "msgestion01", denominacion))
            stats["SOLO_01"] += 1
        elif m01 == 0:
            asignaciones.append((prov_id, "H4", "msgestion03", denominacion))
            stats["SOLO_03"] += 1
        elif (m01 / total) >= 0.65:
            asignaciones.append((prov_id, "CALZALINDO", "msgestion01", denominacion))
            stats["MAYORIA_01"] += 1
        else:
            # >= 35% en base 03 o más → H4
            asignaciones.append((prov_id, "H4", "msgestion03", denominacion))
            stats["MAYORIA_03"] += 1

    print(f"    Total asignaciones: {len(asignaciones)}")
    for k, v in stats.items():
        print(f"      {k}: {v}")

    # ── Paso 4: Crear tabla e insertar ──
    if dry_run:
        print(f"\n[DRY RUN] Se crearia la tabla omicronvt.dbo.proveedor_asignacion_base")
        print(f"          con {len(asignaciones)} filas.")
        print(f"\n  Primeros 20:")
        for prov_id, empresa, base, denom in asignaciones[:20]:
            print(f"    {prov_id:>6}  {empresa:<12}  {base:<14}  {denom[:50]}")
        print(f"\n  Para ejecutar:")
        print(f"  cd C:\\cowork_pedidos && set PYTHONPATH=C:\\cowork_pedidos && py -3 _scripts_oneshot\\crear_tabla_asignacion.py --ejecutar")
        conn.close()
        return

    # Modo ejecución
    print("\n[4] Creando tabla omicronvt.dbo.proveedor_asignacion_base...")
    confirmacion = input(f"    Insertar {len(asignaciones)} filas? (s/N): ").strip().lower()
    if confirmacion != "s":
        print("    Cancelado.")
        conn.close()
        return

    # DROP si existe
    cursor.execute("""
        IF OBJECT_ID('omicronvt.dbo.proveedor_asignacion_base', 'U') IS NOT NULL
            DROP TABLE omicronvt.dbo.proveedor_asignacion_base
    """)
    conn.commit()

    # CREATE
    cursor.execute("""
        CREATE TABLE omicronvt.dbo.proveedor_asignacion_base (
            proveedor       NUMERIC(10,0)   NOT NULL PRIMARY KEY,
            empresa         VARCHAR(20)     NOT NULL,
            base            VARCHAR(20)     NOT NULL,
            denominacion    VARCHAR(100)    NULL
        )
    """)
    conn.commit()
    print("    Tabla creada OK")

    # INSERT en batches
    inserted = 0
    for prov_id, empresa, base, denom in asignaciones:
        cursor.execute("""
            INSERT INTO omicronvt.dbo.proveedor_asignacion_base
                (proveedor, empresa, base, denominacion)
            VALUES (?, ?, ?, ?)
        """, prov_id, empresa, base, denom[:100] if denom else None)
        inserted += 1

    conn.commit()
    print(f"    {inserted} filas insertadas")

    # ── Resumen final ──
    cursor.execute("""
        SELECT empresa, COUNT(*) AS cant
        FROM omicronvt.dbo.proveedor_asignacion_base
        GROUP BY empresa
        ORDER BY empresa
    """)
    print(f"\n  Resumen por empresa:")
    for row in cursor.fetchall():
        print(f"    {row[0]:<12}  {row[1]:>4} proveedores")

    cursor.execute("SELECT COUNT(*) FROM omicronvt.dbo.proveedor_asignacion_base")
    total = cursor.fetchone()[0]
    print(f"\n  TOTAL: {total} proveedores mapeados en omicronvt.dbo.proveedor_asignacion_base")

    conn.close()
    print("\n  LISTO.")


if __name__ == "__main__":
    main()
