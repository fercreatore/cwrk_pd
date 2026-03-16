#!/usr/bin/env python3
"""
Verificar si los 12 artículos WKC215 V26 YOUTH existen en el 111 (producción).
Si no existen, los inserta.

Ejecutar desde la Mac:
  OPENSSL_CONF=/tmp/openssl_legacy.cnf python3 verificar_e_insertar_111.py
"""
import pyodbc, sys

CONN_STR_ART = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion01art;"
    "UID=am;PWD=dl;"
    "TrustServerCertificate=yes;"
    "Encrypt=Optional;"
)
CONN_STR_C = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestionC;"
    "UID=am;PWD=dl;"
    "TrustServerCertificate=yes;"
    "Encrypt=Optional;"
)

# ── Datos de los 12 artículos ────────────────────────────────────
ARTICULOS = [
    # (codigo, desc1, desc3, color, talle, cod_barra, cod_sinonimo)
    (360001, 'WKC215 V26 NEGRO ZAPA URB ABROJO CORD YOUTH', 'WKC215 V26 ZAPA URB ABROJ CORD', 'NEGRO', '31', 594282150031, '594WK2150031'),
    (360002, 'WKC215 V26 NEGRO ZAPA URB ABROJO CORD YOUTH', 'WKC215 V26 ZAPA URB ABROJ CORD', 'NEGRO', '32', 594282150032, '594WK2150032'),
    (360003, 'WKC215 V26 NEGRO ZAPA URB ABROJO CORD YOUTH', 'WKC215 V26 ZAPA URB ABROJ CORD', 'NEGRO', '33', 594282150033, '594WK2150033'),
    (360004, 'WKC215 V26 NEGRO ZAPA URB ABROJO CORD YOUTH', 'WKC215 V26 ZAPA URB ABROJ CORD', 'NEGRO', '34', 594282150034, '594WK2150034'),
    (360005, 'WKC215 V26 NEGRO ZAPA URB ABROJO CORD YOUTH', 'WKC215 V26 ZAPA URB ABROJ CORD', 'NEGRO', '35', 594282150035, '594WK2150035'),
    (360006, 'WKC215 V26 NEGRO ZAPA URB ABROJO CORD YOUTH', 'WKC215 V26 ZAPA URB ABROJ CORD', 'NEGRO', '36', 594282150036, '594WK2150036'),
    (360007, 'WKC215 V26 NUDE ZAPA URB ABROJO CORD YOUTH',  'WKC215 V26 ZAPA URB ABROJ CORD', 'NUDE',  '31', 594282150331, '594WK2150331'),
    (360008, 'WKC215 V26 NUDE ZAPA URB ABROJO CORD YOUTH',  'WKC215 V26 ZAPA URB ABROJ CORD', 'NUDE',  '32', 594282150332, '594WK2150332'),
    (360009, 'WKC215 V26 NUDE ZAPA URB ABROJO CORD YOUTH',  'WKC215 V26 ZAPA URB ABROJ CORD', 'NUDE',  '33', 594282150333, '594WK2150333'),
    (360010, 'WKC215 V26 NUDE ZAPA URB ABROJO CORD YOUTH',  'WKC215 V26 ZAPA URB ABROJ CORD', 'NUDE',  '34', 594282150334, '594WK2150334'),
    (360011, 'WKC215 V26 NUDE ZAPA URB ABROJO CORD YOUTH',  'WKC215 V26 ZAPA URB ABROJ CORD', 'NUDE',  '35', 594282150335, '594WK2150335'),
    (360012, 'WKC215 V26 NUDE ZAPA URB ABROJO CORD YOUTH',  'WKC215 V26 ZAPA URB ABROJ CORD', 'NUDE',  '36', 594282150336, '594WK2150336'),
]

INSERT_ART = """
INSERT INTO msgestion01art.dbo.articulo (
    codigo, descripcion_1, descripcion_3, descripcion_4, descripcion_5,
    codigo_barra, codigo_sinonimo, marca, rubro, subrubro,
    precio_fabrica, descuento, descuento_1, descuento_2, descuento_3, descuento_4,
    precio_costo, precio_sugerido,
    precio_1, precio_2, precio_3, precio_4,
    utilidad_1, utilidad_2, utilidad_3, utilidad_4,
    formula, calificacion, factura_por_total, grupo,
    alicuota_iva1, alicuota_iva2, tipo_iva,
    cuenta_compras, cuenta_ventas, cuenta_com_anti,
    linea, estado, proveedor, moneda,
    numero_maximo, tipo_codigo_barra, stock,
    codigo_objeto_costo, nomenclador_arba, alicuota_rg5329,
    fecha_alta, fecha_ult_compra, usuario, abm, fecha_hora, fecha_modificacion
) VALUES (
    ?, ?, ?, ?, ?,
    ?, ?, 746, 4, 52,
    15000, 20, 0, 0, 0, 0,
    12000, 12000,
    24000, 26880, 19200, 17400,
    100, 124, 60, 45,
    1, 'G', 'N', '5',
    21, 10.5, 'G',
    '1010601', '4010100', '1010601',
    1, 'V', 594, 0,
    'S', 'C', 'S',
    'WK215', '', 0,
    GETDATE(), GETDATE(), 'AM', 'A', GETDATE(), GETDATE()
)
"""

INSERT_PROV = """
INSERT INTO msgestionC.dbo.articulos_prov (codigo, proveedor, codigo_proveedor, porc_gan)
VALUES (?, 594, 'WK215', NULL)
"""

def main():
    solo_verificar = '--solo-verificar' in sys.argv

    # ── Verificar artículos ──────────────────────────────────────
    print("Conectando a 192.168.2.111 (msgestion01art)...")
    cn_art = pyodbc.connect(CONN_STR_ART, timeout=10)
    cur = cn_art.cursor()

    cur.execute("""
        SELECT codigo, descripcion_1, descripcion_4 AS color,
               descripcion_5 AS talle, codigo_sinonimo,
               precio_fabrica, precio_costo, precio_1
        FROM msgestion01art.dbo.articulo
        WHERE codigo BETWEEN 360001 AND 360012
        ORDER BY codigo
    """)
    rows = cur.fetchall()

    if rows:
        print(f"\n✅ Encontrados {len(rows)} artículos en el 111:")
        print(f"{'Código':<8} {'Descripción':<46} {'Color':<8} {'Talle':<6} {'Sinónimo':<14} {'PFab':>8} {'PCosto':>8} {'P1':>8}")
        print("─" * 120)
        for r in rows:
            print(f"{r.codigo:<8} {r.descripcion_1:<46} {r.color:<8} {r.talle:<6} {r.codigo_sinonimo:<14} {r.precio_fabrica:>8.0f} {r.precio_costo:>8.0f} {r.precio_1:>8.0f}")
    else:
        print("\n⚠️  No hay artículos 360001-360012 en el 111.")

    # ── Verificar articulos_prov ─────────────────────────────────
    print("\nConectando a 192.168.2.111 (msgestionC)...")
    cn_c = pyodbc.connect(CONN_STR_C, timeout=10)
    cur_c = cn_c.cursor()

    cur_c.execute("""
        SELECT codigo, proveedor, codigo_proveedor
        FROM msgestionC.dbo.articulos_prov
        WHERE codigo BETWEEN 360001 AND 360012
        ORDER BY codigo
    """)
    rows_prov = cur_c.fetchall()

    if rows_prov:
        print(f"✅ Encontrados {len(rows_prov)} registros en articulos_prov del 111.")
    else:
        print("⚠️  No hay registros en articulos_prov del 111.")

    if solo_verificar:
        print("\n(Modo solo verificar — no se inserta nada)")
        cn_art.close()
        cn_c.close()
        return

    # ── Insertar si faltan ───────────────────────────────────────
    if not rows:
        print("\n📦 Insertando 12 artículos en msgestion01art.dbo.articulo...")
        for art in ARTICULOS:
            cur.execute(INSERT_ART, art)
        cn_art.commit()
        print("✅ 12 artículos insertados en articulo.")
    else:
        print(f"\nYa existen {len(rows)} artículos — no se insertan.")

    if not rows_prov:
        print("📦 Insertando 12 registros en msgestionC.dbo.articulos_prov...")
        for art in ARTICULOS:
            cur_c.execute(INSERT_PROV, (art[0],))
        cn_c.commit()
        print("✅ 12 registros insertados en articulos_prov.")
    else:
        print(f"Ya existen {len(rows_prov)} registros en articulos_prov — no se insertan.")

    # ── Verificación final ───────────────────────────────────────
    print("\n── Verificación final ──────────────────────────────────")
    cur.execute("""
        SELECT codigo, descripcion_1, descripcion_4 AS color,
               descripcion_5 AS talle, precio_fabrica, precio_1
        FROM msgestion01art.dbo.articulo
        WHERE codigo BETWEEN 360001 AND 360012
        ORDER BY codigo
    """)
    for r in cur.fetchall():
        print(f"  {r.codigo}  {r.descripcion_1:<46}  {r.color:<6}  T{r.talle}  PFab={r.precio_fabrica:.0f}  P1={r.precio_1:.0f}")

    cn_art.close()
    cn_c.close()
    print("\n🏁 Listo!")


if __name__ == '__main__':
    main()
