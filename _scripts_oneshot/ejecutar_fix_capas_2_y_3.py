"""
Ejecutar fix_capas_2_y_3.sql en 192.168.2.111 - msgestion01
Sistema de talles 3 capas: Capa 2 (aliases_talles) y Capa 3 (regla_talle_subrubro)

Capa 1 (equivalencias_talles) ya existe en produccion.
Este script crea las tablas faltantes: aliases_talles y regla_talle_subrubro.

Ejecutar en 111: py -3 ejecutar_fix_capas_2_y_3.py
Ejecutar en 112: python ejecutar_fix_capas_2_y_3.py
Ejecutar en Mac: python3 ejecutar_fix_capas_2_y_3.py
"""

import pyodbc
import sys

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=192.168.2.111;"
    "DATABASE=msgestion01;"
    "UID=am;PWD=dl;"
    "TrustServerCertificate=yes"
)

# --- Batches separados (equivale a cada bloque entre GO en el .sql) ---

BATCH_DROP_ALIASES = """
IF OBJECT_ID('dbo.aliases_talles', 'U') IS NOT NULL
    DROP TABLE dbo.aliases_talles;
"""

BATCH_CREATE_ALIASES = """
CREATE TABLE dbo.aliases_talles (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    tipo_talle      VARCHAR(30)  NOT NULL,
    alias           VARCHAR(30)  NOT NULL,
    talle_resuelto  VARCHAR(30)  NOT NULL,
    observaciones   VARCHAR(100) NULL
);
"""

BATCH_INDEX_ALIASES = """
CREATE UNIQUE INDEX UX_aliases_tipo_alias
    ON dbo.aliases_talles (tipo_talle, alias);
"""

BATCH_INSERT_ALIASES_TYPOS = """
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', '38\u00c7',  '38', 'typo con caracter basura'),
('CALZADO', '38.',  '38', 'punto suelto'),
('CALZADO', '39.',  '39', 'punto suelto'),
('CALZADO', '40.',  '40', 'punto suelto'),
('CALZADO', '35.0', '35', 'decimal innecesario'),
('CALZADO', '36.0', '36', 'decimal innecesario'),
('CALZADO', '37.0', '37', 'decimal innecesario'),
('CALZADO', '38.0', '38', 'decimal innecesario'),
('CALZADO', '39.0', '39', 'decimal innecesario'),
('CALZADO', '40.0', '40', 'decimal innecesario'),
('CALZADO', '41.0', '41', 'decimal innecesario'),
('CALZADO', '42.0', '42', 'decimal innecesario'),
('CALZADO', '43.0', '43', 'decimal innecesario'),
('CALZADO', '44.0', '44', 'decimal innecesario'),
('CALZADO', '45.0', '45', 'decimal innecesario');
"""

BATCH_INSERT_ALIASES_DOBLES = """
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', '35/36',         '35', 'talle doble -> menor'),
('CALZADO', '37/38',         '37', 'talle doble -> menor'),
('CALZADO', '39/40',         '39', 'talle doble -> menor'),
('CALZADO', '41/42',         '41', 'talle doble -> menor'),
('CALZADO', '43/44',         '43', 'talle doble -> menor'),
('CALZADO', '38/39/40/41',   '38', 'rango amplio -> menor');
"""

BATCH_INSERT_ALIASES_OJOTAS = """
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', '0/1', '0/1', 'ojota fraccionada'),
('CALZADO', '1/2', '1/2', 'ojota fraccionada'),
('CALZADO', '2/3', '2/3', 'ojota fraccionada'),
('CALZADO', '3/4', '3/4', 'ojota fraccionada'),
('CALZADO', '4/5', '4/5', 'ojota fraccionada'),
('CALZADO', '5/6', '5/6', 'ojota fraccionada'),
('CALZADO', '6/7', '6/7', 'ojota fraccionada'),
('CALZADO', '7/8', '7/8', 'ojota fraccionada'),
('CALZADO', '8/9', '8/9', 'ojota fraccionada'),
('CALZADO', '9/0', '9/0', 'ojota fraccionada');
"""

BATCH_INSERT_ALIASES_US = """
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', 'M4',   '35',   'US mujer 4 -> AR 35'),
('CALZADO', 'M5',   '36',   'US mujer 5 -> AR 36'),
('CALZADO', 'M6',   '37',   'US mujer 6 -> AR 37'),
('CALZADO', 'M7',   '38',   'US mujer 7 -> AR 38'),
('CALZADO', 'M8',   '39',   'US mujer 8 -> AR 39'),
('CALZADO', 'M9',   '40',   'US mujer 9 -> AR 40'),
('CALZADO', 'M10',  '41',   'US mujer 10 -> AR 41'),
('CALZADO', 'W5',   '35',   'Women 5 -> AR 35'),
('CALZADO', 'W6',   '36',   'Women 6 -> AR 36'),
('CALZADO', 'W7',   '37',   'Women 7 -> AR 37'),
('CALZADO', 'W8',   '38',   'Women 8 -> AR 38'),
('CALZADO', 'W9',   '39',   'Women 9 -> AR 39'),
('CALZADO', 'W10',  '40',   'Women 10 -> AR 40'),
('CALZADO', 'M4/W6','36',   'Combo M4/W6 -> AR 36');
"""

BATCH_INSERT_ALIASES_GENERICOS = """
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('CALZADO', 'U',     'UNICO', 'talle unico'),
('CALZADO', 'UNICO', 'UNICO', 'talle unico normalizado');
"""

BATCH_INSERT_ALIASES_INDUMENTARIA = """
INSERT INTO dbo.aliases_talles (tipo_talle, alias, talle_resuelto, observaciones) VALUES
('INDUMENTARIA', 'XS',    'XS',    'valido'),
('INDUMENTARIA', 'S',     'S',     'valido'),
('INDUMENTARIA', 'M',     'M',     'valido'),
('INDUMENTARIA', 'L',     'L',     'valido'),
('INDUMENTARIA', 'XL',    'XL',    'valido'),
('INDUMENTARIA', 'XXL',   'XXL',   'valido'),
('INDUMENTARIA', 'XXXL',  'XXXL',  'valido'),
('INDUMENTARIA', '2XL',   'XXL',   'alias numerico'),
('INDUMENTARIA', '3XL',   'XXXL',  'alias numerico'),
('INDUMENTARIA', '4XL',   'XXXXL', 'alias numerico'),
('INDUMENTARIA', 'XXXXXL','XXXXXL','talle especial');
"""

# --- CAPA 3: regla_talle_subrubro ---

BATCH_DROP_REGLA = """
IF OBJECT_ID('dbo.regla_talle_subrubro', 'U') IS NOT NULL
    DROP TABLE dbo.regla_talle_subrubro;
"""

BATCH_CREATE_REGLA = """
CREATE TABLE dbo.regla_talle_subrubro (
    id              INT IDENTITY(1,1) PRIMARY KEY,
    codigo_subrubro NUMERIC       NOT NULL,
    tipo_talle      VARCHAR(30)   NOT NULL,
    acepta_mp       BIT           DEFAULT 0,
    observaciones   VARCHAR(100)  NULL
);
"""

BATCH_INDEX_REGLA = """
CREATE UNIQUE INDEX UX_regla_talle_sub
    ON dbo.regla_talle_subrubro (codigo_subrubro);
"""

BATCH_INSERT_REGLA_CALZADO = """
INSERT INTO dbo.regla_talle_subrubro (codigo_subrubro, tipo_talle, acepta_mp, observaciones) VALUES
(1,  'CALZADO', 0, 'ALPARGATAS'),
(2,  'CALZADO', 0, 'BORCEGOS'),
(5,  'CALZADO', 0, 'CHATA'),
(7,  'CALZADO', 0, 'MOCASINES'),
(12, 'CALZADO', 0, 'SANDALIAS'),
(15, 'CALZADO', 0, 'BOTAS'),
(17, 'CALZADO', 0, 'GUILLERMINA'),
(19, 'CALZADO', 1, 'BOTINES TAPON - acepta MP'),
(20, 'CALZADO', 0, 'ZAPATO DE VESTIR'),
(21, 'CALZADO', 0, 'CASUAL'),
(35, 'CALZADO', 0, 'PANCHA'),
(37, 'CALZADO', 0, 'FRANCISCANA'),
(38, 'CALZADO', 0, 'MERREL'),
(40, 'CALZADO', 0, 'NAUTICO'),
(56, 'CALZADO', 0, 'FIESTA'),
(60, 'CALZADO', 0, 'PANTUFLA'),
(64, 'CALZADO', 0, 'ZAPATO DE TRABAJO'),
(65, 'CALZADO', 0, 'BOTA DE LLUVIA');
"""

BATCH_INSERT_REGLA_DEPORTIVO = """
INSERT INTO dbo.regla_talle_subrubro (codigo_subrubro, tipo_talle, acepta_mp, observaciones) VALUES
(45, 'CALZADO', 1, 'BOTINES PISTA'),
(47, 'CALZADO', 1, 'ZAPATILLA RUNNING'),
(48, 'CALZADO', 1, 'ZAPATILLA TENNIS'),
(49, 'CALZADO', 1, 'ZAPATILLA TRAINING'),
(50, 'CALZADO', 1, 'ZAPATILLA BASKET'),
(51, 'CALZADO', 1, 'ZAPATILLA OUTDOOR'),
(52, 'CALZADO', 1, 'ZAPATILLA CASUAL'),
(53, 'CALZADO', 1, 'ZAPATILLA SKATER'),
(54, 'CALZADO', 1, 'BOTIN INDOOR'),
(55, 'CALZADO', 1, 'ZAPATILLA SNEAKERS'),
(69, 'CALZADO', 1, 'ZAPATILLA HOCKEY');
"""

BATCH_INSERT_REGLA_OJOTAS = """
INSERT INTO dbo.regla_talle_subrubro (codigo_subrubro, tipo_talle, acepta_mp, observaciones) VALUES
(6,  'OJOTA', 0, 'CHINELA'),
(11, 'OJOTA', 0, 'OJOTAS'),
(13, 'OJOTA', 0, 'ZUECOS');
"""

BATCH_INSERT_REGLA_INDUMENTARIA = """
INSERT INTO dbo.regla_talle_subrubro (codigo_subrubro, tipo_talle, acepta_mp, observaciones) VALUES
(23, 'INDUMENTARIA', 0, 'PANTALON'),
(46, 'INDUMENTARIA', 0, 'CAMPERAS'),
(57, 'INDUMENTARIA', 0, 'REMERAS'),
(61, 'INDUMENTARIA', 0, 'BUZO'),
(62, 'INDUMENTARIA', 0, 'CALZA'),
(63, 'INDUMENTARIA', 0, 'MALLA'),
(70, 'INDUMENTARIA', 0, 'BOXER');
"""

BATCH_INSERT_REGLA_ACCESORIOS = """
INSERT INTO dbo.regla_talle_subrubro (codigo_subrubro, tipo_talle, acepta_mp, observaciones) VALUES
(3,  'ACCESORIO', 0, 'MAQUILLAJE'),
(10, 'ACCESORIO', 0, 'ACC. DEPORTIVOS'),
(18, 'ACCESORIO', 0, 'CARTERAS'),
(22, 'ACCESORIO', 0, 'CANILLERA'),
(24, 'ACCESORIO', 0, 'PARAGUAS'),
(25, 'ACCESORIO', 0, 'MOCHILAS'),
(26, 'ACCESORIO', 0, 'BILLETERAS'),
(27, 'ACCESORIO', 0, 'PLANTILLAS'),
(28, 'ACCESORIO', 0, 'CORDONES'),
(29, 'ACCESORIO', 0, 'MEDIAS'),
(30, 'ACCESORIO', 0, 'BOLSOS'),
(32, 'ACCESORIO', 0, 'COSMETICA DE CALZADO'),
(33, 'ACCESORIO', 0, 'PELOTAS'),
(39, 'ACCESORIO', 0, 'ACC. MARRO'),
(71, 'ACCESORIO', 0, 'RINONERA');
"""

BATCH_INSERT_REGLA_OTROS = """
INSERT INTO dbo.regla_talle_subrubro (codigo_subrubro, tipo_talle, acepta_mp, observaciones) VALUES
(58, 'CINTO',  0, 'CINTOS - talle cm cintura'),
(68, 'VALIJA', 0, 'VALIJAS - talle pulgadas'),
(59, 'CALZADO', 0, 'ROLLER/PATIN');
"""

# --- Verificacion ---

BATCH_VERIFY_ALIASES = """
SELECT 'aliases_talles' as tabla, tipo_talle, COUNT(*) as registros
FROM dbo.aliases_talles GROUP BY tipo_talle;
"""

BATCH_VERIFY_REGLA = """
SELECT 'regla_talle_subrubro' as tabla, tipo_talle, COUNT(*) as subrubros,
       SUM(CAST(acepta_mp AS INT)) as con_medio_punto
FROM dbo.regla_talle_subrubro GROUP BY tipo_talle;
"""

BATCH_VERIFY_SIN_CLASIFICAR = """
SELECT s.codigo, s.descripcion as subrubro_sin_regla
FROM dbo.subrubro s
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.regla_talle_subrubro r WHERE r.codigo_subrubro = s.codigo
)
AND s.codigo < 200
ORDER BY s.codigo;
"""


def main():
    dry_run = "--dry-run" in sys.argv or "--dryrun" in sys.argv

    if dry_run:
        print("=== DRY RUN === (no se ejecuta nada)")
        print("Se crearian las siguientes tablas en msgestion01 (192.168.2.111):")
        print("  - dbo.aliases_talles (Capa 2: ~48 aliases de talles)")
        print("  - dbo.regla_talle_subrubro (Capa 3: ~48 reglas por subrubro)")
        print("Ejecutar sin --dry-run para aplicar.")
        return

    print("Conectando a 192.168.2.111 / msgestion01 ...")
    conn = pyodbc.connect(CONN_STR)
    conn.autocommit = True  # DDL requiere autocommit
    cursor = conn.cursor()

    # --- Pre-check: ver si las tablas ya existen ---
    cursor.execute("""
        SELECT
            CASE WHEN OBJECT_ID('dbo.aliases_talles', 'U') IS NOT NULL THEN 1 ELSE 0 END,
            CASE WHEN OBJECT_ID('dbo.regla_talle_subrubro', 'U') IS NOT NULL THEN 1 ELSE 0 END
    """)
    exists_aliases, exists_regla = cursor.fetchone()

    if exists_aliases or exists_regla:
        print(f"  aliases_talles: {'YA EXISTE' if exists_aliases else 'no existe'}")
        print(f"  regla_talle_subrubro: {'YA EXISTE' if exists_regla else 'no existe'}")
        resp = input("Las tablas se RECREARAN (DROP + CREATE). Continuar? (s/N): ")
        if resp.strip().lower() != 's':
            print("Cancelado.")
            conn.close()
            return

    # === CAPA 2: aliases_talles ===
    print("\n--- CAPA 2: aliases_talles ---")

    print("  DROP si existe...")
    cursor.execute(BATCH_DROP_ALIASES)

    print("  CREATE TABLE...")
    cursor.execute(BATCH_CREATE_ALIASES)

    print("  CREATE INDEX...")
    cursor.execute(BATCH_INDEX_ALIASES)

    print("  INSERT typos y decimales (15 filas)...")
    cursor.execute(BATCH_INSERT_ALIASES_TYPOS)

    print("  INSERT talles dobles (6 filas)...")
    cursor.execute(BATCH_INSERT_ALIASES_DOBLES)

    print("  INSERT ojotas fraccionadas (10 filas)...")
    cursor.execute(BATCH_INSERT_ALIASES_OJOTAS)

    print("  INSERT formato US (14 filas)...")
    cursor.execute(BATCH_INSERT_ALIASES_US)

    print("  INSERT genericos (2 filas)...")
    cursor.execute(BATCH_INSERT_ALIASES_GENERICOS)

    print("  INSERT indumentaria (11 filas)...")
    cursor.execute(BATCH_INSERT_ALIASES_INDUMENTARIA)

    print("Capa 2: aliases_talles OK")

    # === CAPA 3: regla_talle_subrubro ===
    print("\n--- CAPA 3: regla_talle_subrubro ---")

    print("  DROP si existe...")
    cursor.execute(BATCH_DROP_REGLA)

    print("  CREATE TABLE...")
    cursor.execute(BATCH_CREATE_REGLA)

    print("  CREATE INDEX...")
    cursor.execute(BATCH_INDEX_REGLA)

    print("  INSERT calzado clasico (18 filas)...")
    cursor.execute(BATCH_INSERT_REGLA_CALZADO)

    print("  INSERT calzado deportivo (11 filas)...")
    cursor.execute(BATCH_INSERT_REGLA_DEPORTIVO)

    print("  INSERT ojotas (3 filas)...")
    cursor.execute(BATCH_INSERT_REGLA_OJOTAS)

    print("  INSERT indumentaria (7 filas)...")
    cursor.execute(BATCH_INSERT_REGLA_INDUMENTARIA)

    print("  INSERT accesorios (15 filas)...")
    cursor.execute(BATCH_INSERT_REGLA_ACCESORIOS)

    print("  INSERT otros (3 filas)...")
    cursor.execute(BATCH_INSERT_REGLA_OTROS)

    print("Capa 3: regla_talle_subrubro OK")

    # === VERIFICACION ===
    print("\n========== RESUMEN 3 CAPAS ==========")

    print("\naliases_talles:")
    cursor.execute(BATCH_VERIFY_ALIASES)
    for row in cursor.fetchall():
        print(f"  {row.tipo_talle}: {row.registros} registros")

    print("\nregla_talle_subrubro:")
    cursor.execute(BATCH_VERIFY_REGLA)
    for row in cursor.fetchall():
        print(f"  {row.tipo_talle}: {row.subrubros} subrubros, {row.con_medio_punto} con medio punto")

    print("\nSubrubros sin clasificar (< 200):")
    cursor.execute(BATCH_VERIFY_SIN_CLASIFICAR)
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            print(f"  {row.codigo}: {row.subrubro_sin_regla}")
    else:
        print("  (ninguno)")

    # Verificar capa 1
    cursor.execute("""
        IF OBJECT_ID('dbo.equivalencias_talles', 'U') IS NOT NULL
            SELECT 'equivalencias_talles' as tabla, COUNT(*) as registros
            FROM dbo.equivalencias_talles
    """)
    row = cursor.fetchone()
    if row:
        print(f"\nCapa 1 (equivalencias_talles): {row.registros} registros")
    else:
        print("\nCapa 1 (equivalencias_talles): NO EXISTE - verificar!")

    print("\n=== 3 CAPAS COMPLETAS ===")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    main()
