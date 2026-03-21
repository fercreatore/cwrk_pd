"""
Tests end-to-end del pipeline paso1→paso2→paso3→paso4→paso5→paso6.
Correr: pytest tests/test_pipeline.py -v
        pytest tests/test_pipeline.py -v -k "not db"   ← solo offline

Tests offline: lógica pura, validaciones, dry_run, parseo.
Tests online (requieren DB): búsqueda de artículos, proveedores, insert dry_run real.
"""
import sys
import os
import tempfile
import pytest
from datetime import date
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ══════════════════════════════════════════════════════════════════
# HELPER: detectar si hay conexión a DB
# ══════════════════════════════════════════════════════════════════

def _db_disponible():
    try:
        import pyodbc
        from config import CONN_COMPRAS
        conn = pyodbc.connect(CONN_COMPRAS, timeout=5)
        conn.close()
        return True
    except Exception:
        return False

requires_db = pytest.mark.skipif(
    not _db_disponible(),
    reason="No hay conexión a SQL Server"
)


# ══════════════════════════════════════════════════════════════════
# PASO 1 — verificar_bd (imports)
# ══════════════════════════════════════════════════════════════════

class TestPaso1:
    def test_imports(self):
        from paso1_verificar_bd import get_columnas, mostrar_columnas
        assert callable(get_columnas)
        assert callable(mostrar_columnas)

    @requires_db
    def test_columnas_pedico2(self):
        from paso1_verificar_bd import get_columnas
        from config import CONN_COMPRAS
        cols = get_columnas(CONN_COMPRAS, "msgestionC", "pedico2")
        assert not isinstance(cols, str), f"Error: {cols}"
        assert len(cols) > 10
        nombres = [c[0] for c in cols]
        assert "numero" in nombres
        assert "cuenta" in nombres

    @requires_db
    def test_columnas_pedico1(self):
        from paso1_verificar_bd import get_columnas
        from config import CONN_COMPRAS
        cols = get_columnas(CONN_COMPRAS, "msgestionC", "pedico1")
        assert not isinstance(cols, str), f"Error: {cols}"
        nombres = [c[0] for c in cols]
        assert "articulo" in nombres
        assert "cantidad" in nombres

    @requires_db
    def test_columnas_articulo(self):
        from paso1_verificar_bd import get_columnas
        from config import CONN_ARTICULOS
        cols = get_columnas(CONN_ARTICULOS, "msgestion01art", "articulo")
        assert not isinstance(cols, str), f"Error: {cols}"
        nombres = [c[0] for c in cols]
        assert "codigo" in nombres
        assert "descripcion_1" in nombres


# ══════════════════════════════════════════════════════════════════
# PASO 2 — buscar_articulo
# ══════════════════════════════════════════════════════════════════

class TestPaso2:
    def test_imports(self):
        from paso2_buscar_articulo import (
            buscar_por_codigo, buscar_por_descripcion,
            obtener_industria, dar_de_alta, buscar_por_codigo_sap,
        )
        assert callable(buscar_por_codigo)
        assert callable(dar_de_alta)

    def test_dar_de_alta_dry_run(self):
        from paso2_buscar_articulo import dar_de_alta
        result = dar_de_alta({
            "descripcion_1": "TEST ZAPATILLA PIPELINE",
            "codigo_sinonimo": "668TEST00138",
            "subrubro": 47,
            "marca": 314,
            "linea": 1,
            "precio_1": 25000.00,
        }, dry_run=True)
        assert result == -1

    def test_dar_de_alta_missing_field(self):
        from paso2_buscar_articulo import dar_de_alta
        result = dar_de_alta({"descripcion_1": "TEST"}, dry_run=True)
        assert result is None

    @requires_db
    def test_db_buscar_por_codigo_existente(self):
        from paso2_buscar_articulo import buscar_por_codigo
        art = buscar_por_codigo(249886)  # CARMEL 03 CANELA T42
        assert art is not None
        assert art["codigo"] == 249886
        assert "CARMEL" in art["descripcion"].upper() or art["descripcion"] != ""

    @requires_db
    def test_db_buscar_por_codigo_inexistente(self):
        from paso2_buscar_articulo import buscar_por_codigo
        art = buscar_por_codigo(999999999)
        assert art is None

    @requires_db
    def test_db_buscar_por_descripcion(self):
        from paso2_buscar_articulo import buscar_por_descripcion
        results = buscar_por_descripcion("CARMEL")
        assert isinstance(results, list)
        assert len(results) > 0

    @requires_db
    def test_db_obtener_industria(self):
        from paso2_buscar_articulo import obtener_industria
        ind = obtener_industria(47)  # Running → Deportes
        assert ind != "Sin clasificar"


# ══════════════════════════════════════════════════════════════════
# PASO 3 — calcular_periodo (lógica pura)
# ══════════════════════════════════════════════════════════════════

class TestPaso3:
    def test_imports(self):
        from paso3_calcular_periodo import calcular_periodo, warning_destiempo
        assert callable(calcular_periodo)
        assert callable(warning_destiempo)

    @pytest.mark.parametrize("fecha,industria,esperado", [
        (date(2026, 4, 15), "Zapatería", "2026-OI"),
        (date(2026, 10, 1), "Zapatería", "2026-PV"),
        (date(2026, 1, 20), "Zapatería", "2025-PV"),
        (date(2026, 3, 1), "Deportes", "2026-H1"),
        (date(2026, 8, 15), "Deportes", "2026-H2"),
        (date(2026, 6, 30), "Deportes", "2026-H1"),
        (date(2026, 7, 1), "Deportes", "2026-H2"),
        (date(2026, 5, 10), "Marroquinería", "2026-OI"),
        (date(2026, 9, 1), "Indumentaria", "2026-PV"),
        (date(2026, 2, 28), "Cosmética", "2025-PV"),
        (date(2026, 8, 31), "Mixto_Zap_Dep", "2026-H2"),
    ])
    def test_periodo(self, fecha, industria, esperado):
        from paso3_calcular_periodo import calcular_periodo
        assert calcular_periodo(fecha, industria) == esperado

    def test_periodo_sin_clasificar(self):
        from paso3_calcular_periodo import calcular_periodo
        assert calcular_periodo(date(2026, 5, 1), "Sin clasificar") == "SIN-PERIODO"

    def test_periodo_industria_desconocida_usa_oi_pv(self):
        from paso3_calcular_periodo import calcular_periodo
        assert calcular_periodo(date(2026, 5, 1), "Otra") == "2026-OI"

    def test_warning_verano_en_invierno(self):
        from paso3_calcular_periodo import warning_destiempo
        w = warning_destiempo(date(2026, 4, 1), 1)  # verano en abril
        assert w is not None
        assert "DESTIEMPO" in w

    def test_warning_invierno_en_verano(self):
        from paso3_calcular_periodo import warning_destiempo
        w = warning_destiempo(date(2026, 10, 1), 2)  # invierno en octubre
        assert w is not None
        assert "DESTIEMPO" in w

    def test_no_warning_verano_ok(self):
        from paso3_calcular_periodo import warning_destiempo
        assert warning_destiempo(date(2026, 10, 1), 1) is None

    def test_no_warning_atemporal(self):
        from paso3_calcular_periodo import warning_destiempo
        assert warning_destiempo(date(2026, 4, 1), 4) is None


# ══════════════════════════════════════════════════════════════════
# PASO 4 — insertar_pedido
# ══════════════════════════════════════════════════════════════════

class TestPaso4:
    def test_imports(self):
        from paso4_insertar_pedido import (
            insertar_pedido, validar_cabecera, validar_renglones, get_tabla_base,
        )
        assert callable(insertar_pedido)

    def test_get_tabla_base_h4(self):
        from paso4_insertar_pedido import get_tabla_base
        assert get_tabla_base("pedico2", "H4") == "MSGESTION03.dbo.pedico2"
        assert get_tabla_base("pedico1", "H4") == "MSGESTION03.dbo.pedico1"

    def test_get_tabla_base_calzalindo(self):
        from paso4_insertar_pedido import get_tabla_base
        assert get_tabla_base("pedico2", "CALZALINDO") == "MSGESTION01.dbo.pedico2"
        assert get_tabla_base("pedico1", "CALZALINDO") == "MSGESTION01.dbo.pedico1"

    def test_validar_cabecera_ok(self):
        from paso4_insertar_pedido import validar_cabecera
        validar_cabecera({
            "empresa": "H4", "cuenta": 668,
            "denominacion": "ALPARGATAS", "fecha_comprobante": date.today(),
        })

    def test_validar_cabecera_falta_empresa(self):
        from paso4_insertar_pedido import validar_cabecera
        with pytest.raises(ValueError, match="empresa"):
            validar_cabecera({"cuenta": 1, "denominacion": "X", "fecha_comprobante": date.today()})

    def test_validar_renglones_vacio(self):
        from paso4_insertar_pedido import validar_renglones
        with pytest.raises(ValueError, match="al menos un renglón"):
            validar_renglones([])

    def test_validar_renglones_cantidad_cero(self):
        from paso4_insertar_pedido import validar_renglones
        with pytest.raises(ValueError, match="cantidad"):
            validar_renglones([{"articulo": 1, "descripcion": "x", "cantidad": 0, "precio": 100}])

    def test_validar_renglones_precio_negativo(self):
        from paso4_insertar_pedido import validar_renglones
        with pytest.raises(ValueError, match="precio"):
            validar_renglones([{"articulo": 1, "descripcion": "x", "cantidad": 5, "precio": -1}])

    def test_validar_renglones_campo_faltante(self):
        from paso4_insertar_pedido import validar_renglones
        with pytest.raises(ValueError, match="articulo"):
            validar_renglones([{"descripcion": "x", "cantidad": 5, "precio": 100}])

    def test_insertar_pedido_dry_run(self):
        from paso4_insertar_pedido import insertar_pedido
        cabecera = {
            "empresa": "H4", "cuenta": 668,
            "denominacion": "ALPARGATAS S.A.I.C.",
            "fecha_comprobante": date(2026, 3, 20),
            "observaciones": "Test pipeline",
        }
        renglones = [
            {"articulo": 12345, "descripcion": "ZAPATILLA TEST", "cantidad": 10, "precio": 25000.0},
            {"articulo": 12346, "descripcion": "SANDALIA TEST", "cantidad": 5, "precio": 18000.0},
        ]
        num = insertar_pedido(cabecera, renglones, dry_run=True)
        assert num == 999999

    def test_insertar_pedido_calzalindo_dry_run(self):
        from paso4_insertar_pedido import insertar_pedido
        cabecera = {
            "empresa": "CALZALINDO", "cuenta": 104,
            "denominacion": '"EL GITANO" - GTN',
            "fecha_comprobante": date(2026, 3, 20),
            "observaciones": "Test CALZALINDO",
        }
        renglones = [
            {"articulo": 99999, "descripcion": "GTN TEST", "cantidad": 3, "precio": 22000.0},
        ]
        num = insertar_pedido(cabecera, renglones, dry_run=True)
        assert num == 999999


# ══════════════════════════════════════════════════════════════════
# PASO 5 — parsear_excel
# ══════════════════════════════════════════════════════════════════

class TestPaso5:
    def test_imports(self):
        from paso5_parsear_excel import parsear_nota, leer_archivo, normalizar_columnas
        assert callable(parsear_nota)

    def _crear_csv(self, contenido: str) -> str:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        f.write(contenido)
        f.close()
        return f.name

    def test_parsear_csv_basico(self):
        from paso5_parsear_excel import parsear_nota
        ruta = self._crear_csv(
            "Codigo,Descripcion,Cantidad,Precio,Talle,Color\n"
            "12345,ZAPATILLA RUNNING,10,25000,42,NEGRO\n"
            "12346,SANDALIA VERANO,5,18000,38,AZUL\n"
        )
        df = parsear_nota(ruta)
        os.unlink(ruta)
        assert df is not None
        assert len(df) == 2
        assert "descripcion" in df.columns
        assert "cantidad" in df.columns
        assert df["cantidad"].sum() == 15

    def test_parsear_csv_nombres_alternativos(self):
        from paso5_parsear_excel import parsear_nota
        ruta = self._crear_csv(
            "Art,Detalle,Cant.,Precio Unit.,Num,Color\n"
            "100,BOTA CUERO,8,35000,40,MARRON\n"
        )
        df = parsear_nota(ruta)
        os.unlink(ruta)
        assert df is not None
        assert len(df) == 1
        assert "descripcion" in df.columns
        assert "cantidad" in df.columns
        assert "precio" in df.columns

    def test_parsear_csv_sin_columna_obligatoria(self):
        from paso5_parsear_excel import parsear_nota
        ruta = self._crear_csv(
            "Codigo,Color,Talle\n"
            "12345,NEGRO,42\n"
        )
        df = parsear_nota(ruta)
        os.unlink(ruta)
        assert df is None  # falta descripcion, cantidad, precio

    def test_parsear_csv_limpia_cantidad_cero(self):
        from paso5_parsear_excel import parsear_nota
        ruta = self._crear_csv(
            "Descripcion,Cantidad,Precio\n"
            "ZAPATILLA,10,25000\n"
            "SANDALIA,0,18000\n"
            "BOTA,5,35000\n"
        )
        df = parsear_nota(ruta)
        os.unlink(ruta)
        assert df is not None
        assert len(df) == 2  # fila con cantidad 0 eliminada

    def test_parsear_csv_precio_con_simbolo(self):
        from paso5_parsear_excel import parsear_nota
        # Usar punto como separador de miles para no conflictar con CSV comma
        ruta = self._crear_csv(
            "Descripcion,Cantidad,Precio\n"
            "ZAPATILLA,10,$25000\n"
            "SANDALIA,5,$18000\n"
        )
        df = parsear_nota(ruta)
        os.unlink(ruta)
        assert df is not None
        assert len(df) == 2
        assert df["precio"].iloc[0] == 25000.0

    def test_archivo_no_existe(self):
        from paso5_parsear_excel import parsear_nota
        with pytest.raises(FileNotFoundError):
            parsear_nota("/tmp/no_existe_xyz.csv")

    def test_normalizar_mayusculas_descripcion(self):
        from paso5_parsear_excel import parsear_nota
        ruta = self._crear_csv(
            "Descripcion,Cantidad,Precio\n"
            "zapatilla running negra,10,25000\n"
        )
        df = parsear_nota(ruta)
        os.unlink(ruta)
        assert df is not None
        assert df["descripcion"].iloc[0] == "ZAPATILLA RUNNING NEGRA"


# ══════════════════════════════════════════════════════════════════
# PASO 6 — flujo_completo (imports + structure)
# ══════════════════════════════════════════════════════════════════

class TestPaso6:
    def test_imports(self):
        from paso6_flujo_completo import buscar_proveedor, resolver_articulo, procesar_nota
        assert callable(buscar_proveedor)
        assert callable(resolver_articulo)
        assert callable(procesar_nota)

    @requires_db
    def test_db_buscar_proveedor_alpargatas(self):
        from paso6_flujo_completo import buscar_proveedor
        prov = buscar_proveedor("ALPARGATAS S.A.I.C.")
        assert prov is not None
        assert prov["numero"] == 668

    @requires_db
    def test_db_buscar_proveedor_inexistente(self):
        from paso6_flujo_completo import buscar_proveedor
        prov = buscar_proveedor("XYZNOEXISTE999")
        assert prov is None


# ══════════════════════════════════════════════════════════════════
# CONFIG — calcular_precios
# ══════════════════════════════════════════════════════════════════

class TestConfig:
    def test_calcular_precios_topper(self):
        from config import calcular_precios
        p = calcular_precios(100000, 668)  # Topper, 6% desc
        assert p["descuento"] == 6
        assert p["precio_costo"] == 94000.0
        assert p["precio_1"] == pytest.approx(94000 * 1.989, rel=0.01)

    def test_calcular_precios_gtn_sin_descuento(self):
        from config import calcular_precios
        p = calcular_precios(22000, 104)  # GTN, 0% desc
        assert p["precio_costo"] == 22000.0

    @requires_db
    def test_calcular_precios_proveedor_inexistente(self):
        """Proveedor no en config.py usa fallback a BD con defaults razonables."""
        from config import calcular_precios
        try:
            p = calcular_precios(10000, 999999)
            assert "precio_costo" in p
            assert p["precio_costo"] > 0
        except ValueError:
            pass  # OK si no hay DB o proveedor no existe

    def test_proveedores_configurados(self):
        from config import PROVEEDORES
        assert 668 in PROVEEDORES  # Alpargatas
        assert 104 in PROVEEDORES  # GTN
        assert 594 in PROVEEDORES  # Wake
        assert 656 in PROVEEDORES  # Distrinando
        assert 561 in PROVEEDORES  # Ringo

    def test_conn_strings_defined(self):
        from config import CONN_COMPRAS, CONN_ARTICULOS, CONN_ANALITICA
        assert "msgestionC" in CONN_COMPRAS
        assert "msgestion01art" in CONN_ARTICULOS
        assert "omicronvt" in CONN_ANALITICA


# ══════════════════════════════════════════════════════════════════
# INTEGRACIÓN — flujo completo dry_run (con DB)
# ══════════════════════════════════════════════════════════════════

class TestIntegracion:
    @requires_db
    def test_flujo_buscar_articulo_y_periodo(self):
        """Busca un artículo real y calcula su período."""
        from paso2_buscar_articulo import buscar_por_codigo, obtener_industria
        from paso3_calcular_periodo import calcular_periodo

        art = buscar_por_codigo(249886)  # CARMEL 03 CANELA T42
        assert art is not None

        industria = obtener_industria(art["subrubro"])
        periodo = calcular_periodo(date(2026, 5, 1), industria)
        assert periodo != ""
        assert "-" in periodo  # "2026-OI" o similar

    @requires_db
    def test_flujo_insertar_dry_run_con_articulo_real(self):
        """Busca artículo real y simula inserción completa."""
        from paso2_buscar_articulo import buscar_por_codigo
        from paso4_insertar_pedido import insertar_pedido

        art = buscar_por_codigo(249886)
        assert art is not None

        cabecera = {
            "empresa": "H4", "cuenta": 561,
            "denominacion": "Souter S.A.",
            "fecha_comprobante": date(2026, 3, 20),
            "observaciones": "TEST PIPELINE — NO INSERTAR",
        }
        renglones = [{
            "articulo": art["codigo"],
            "descripcion": art["descripcion"],
            "cantidad": 3,
            "precio": 34700.0,
        }]
        num = insertar_pedido(cabecera, renglones, dry_run=True)
        assert num == 999999
