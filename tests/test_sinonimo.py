"""
Tests para construir_sinonimo() y obtener_color_code().
Correr: py -3 -m pytest tests/test_sinonimo.py -v
O desde Claude Code: pytest tests/test_sinonimo.py -v

Tests offline (sin DB): test_sinonimo_*
Tests online (requieren DB): test_db_*
"""
import sys
import os
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


# ══════════════════════════════════════════════════════════════════
# TESTS OFFLINE — lógica pura, sin DB
# ══════════════════════════════════════════════════════════════════

def test_sinonimo_comoditas_239_negro():
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("239", "00", "40", proveedor=776)
    assert r == "776239000040", f"Esperaba 776239000040, obtuve {r}"

def test_sinonimo_comoditas_1127_gris():
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("1127", "13", "36", proveedor=776)
    assert r == "776112701336", f"Esperaba 776112701336, obtuve {r}"

def test_sinonimo_comoditas_1127_manteca():
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("1127", "15", "36", proveedor=776)
    assert r == "776112701536", f"Esperaba 776112701536, obtuve {r}"

def test_sinonimo_comoditas_239_azul():
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("239", "02", "40", proveedor=776)
    assert r == "776239000240", f"Esperaba 776239000240, obtuve {r}"

def test_sinonimo_comoditas_239_verde():
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("239", "14", "38", proveedor=776)
    assert r == "776239001438", f"Esperaba 776239001438, obtuve {r}"

def test_sinonimo_juana_va_1059_negro():
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("1059", "00", "39", proveedor=938)
    assert r == "938105900039", f"Esperaba 938105900039, obtuve {r}"

def test_sinonimo_topper_5_digitos():
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("52100", "00", "42", proveedor=668)
    assert r == "668521000042", f"Esperaba 668521000042, obtuve {r}"

def test_sinonimo_wake_wkc215():
    """WKC se limpia a 215, right-padded."""
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("WKC215", "00", "31", proveedor=594)
    assert r == "594215000031", f"Esperaba 594215000031, obtuve {r}"

def test_sinonimo_reebok_con_codigo_objeto_costo():
    """Cuando se pasa codigo_objeto_costo explícito, usarlo directo."""
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("FLEXAGON", "01", "40", proveedor=656,
                           codigo_objeto_costo="LIP26")
    assert r == "656LIP260140", f"Esperaba 656LIP260140, obtuve {r}"

def test_sinonimo_reebok_con_cod5_fetr4():
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("RBK1100033358", "13", "40", proveedor=656,
                           codigo_objeto_costo="FETR4")
    assert r == "656FETR41340", f"Esperaba 656FETR41340, obtuve {r}"

def test_sinonimo_reebok_con_cod5_zazul():
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("RBK1100033358", "02", "43", proveedor=656,
                           codigo_objeto_costo="ZAZUL")
    assert r == "656ZAZUL0243", f"Esperaba 656ZAZUL0243, obtuve {r}"

def test_sinonimo_largo_siempre_12():
    from paso8_carga_factura import construir_sinonimo
    for modelo in ["1", "12", "123", "1234", "12345"]:
        r = construir_sinonimo(modelo, "00", "38", proveedor=776)
        assert len(r) == 12, f"Modelo '{modelo}' generó sinónimo de {len(r)} chars: {r}"

def test_sinonimo_talle_medio_punto():
    """Talles con medio punto se truncan a entero."""
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("239", "00", "39.5", proveedor=776)
    assert r == "776239000039", f"Esperaba 776239000039, obtuve {r}"
    assert len(r) == 12

def test_sinonimo_right_padding():
    """Verifica que usa right-pad (ljust), NO left-pad (zfill)."""
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("239", "00", "40", proveedor=776)
    cod_prov = r[3:8]
    assert cod_prov == "23900", f"Padding incorrecto: cod_prov='{cod_prov}', esperaba '23900'"

def test_formato_3_5_2_2():
    """Formato: {prov:3}{cod:5}{color:2}{talle:2} = 12 dígitos."""
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("598", "13", "38", proveedor=776)
    assert len(r) == 12
    assert r[:3] == "776"      # proveedor 3 dígitos
    assert r[3:8] == "59800"   # codigo_prov 5 chars (right-padded)
    assert r[8:10] == "13"     # color 2 dígitos
    assert r[10:12] == "38"    # talle 2 dígitos

def test_sinonimo_sin_proveedor_usa_000():
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("239", "00", "40", proveedor=0)
    assert r[:3] == "000"

def test_sinonimo_proveedor_2_digitos():
    from paso8_carga_factura import construir_sinonimo
    r = construir_sinonimo("239", "00", "40", proveedor=42)
    assert r[:3] == "042"


# ══════════════════════════════════════════════════════════════════
# TESTS ONLINE — requieren conexión a DB (réplica 112 o prod 111)
# Se skipean si no hay conexión disponible
# ══════════════════════════════════════════════════════════════════

def _db_disponible():
    """Chequea si hay conexión a la DB."""
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


@requires_db
def test_db_obtener_color_code_negro():
    from paso8_carga_factura import obtener_color_code
    assert obtener_color_code("NEGRO") == "00"

@requires_db
def test_db_obtener_color_code_azul():
    from paso8_carga_factura import obtener_color_code
    assert obtener_color_code("AZUL") == "02"

@requires_db
def test_db_obtener_color_code_gris():
    from paso8_carga_factura import obtener_color_code
    assert obtener_color_code("GRIS") == "13"

@requires_db
def test_db_obtener_color_code_blanco():
    from paso8_carga_factura import obtener_color_code
    assert obtener_color_code("BLANCO") == "01"

@requires_db
def test_db_obtener_color_code_compuesto():
    """Colores compuestos usan el primer componente."""
    from paso8_carga_factura import obtener_color_code
    code = obtener_color_code("NEGRO/NEGRO/GRIS")
    assert code == "00"  # NEGRO

@requires_db
def test_db_obtener_color_code_beige():
    from paso8_carga_factura import obtener_color_code
    assert obtener_color_code("BEIGE") == "15"


@requires_db
def test_db_buscar_cod5_flexagon_energy():
    """El bug original: buscar cod5 para FLEXAGON ENERGY TR 4 del prov 656."""
    from paso8_carga_factura import buscar_codigo_objeto_costo
    cod5 = buscar_codigo_objeto_costo("FLEXAGON ENERGY TR 4 AZUL/BLANCO", 656)
    assert cod5 is not None, "No encontró cod5 para FLEXAGON ENERGY TR 4"
    assert len(cod5) == 5, f"cod5 debe ser 5 chars, obtuve '{cod5}' ({len(cod5)})"


@requires_db
def test_db_buscar_cod5_flexagon_force():
    from paso8_carga_factura import buscar_codigo_objeto_costo
    cod5 = buscar_codigo_objeto_costo("FLEXAGON FORCE 4 GRIS/LIMA", 656)
    assert cod5 is not None, "No encontró cod5 para FLEXAGON FORCE 4"


@requires_db
def test_db_construir_sinonimo_flexagon_auto():
    """TEST CLAVE: construir_sinonimo con auto-búsqueda de cod5.
    Simula lo que pasa cuando llega del OCR sin codigo_objeto_costo."""
    from paso8_carga_factura import construir_sinonimo, obtener_color_code
    color_code = obtener_color_code("AZUL")
    sinonimo = construir_sinonimo(
        "RBK1100033358",  # barcode del fabricante (lo que da el OCR)
        color_code, "43",
        proveedor=656,
        descripcion="FLEXAGON ENERGY TR 4 AZUL/BLANCO ZAPA DEP",
    )
    # Debe auto-detectar cod5 de DB, NO usar "11000" del barcode
    assert sinonimo[:3] == "656", f"Proveedor mal: {sinonimo[:3]}"
    assert sinonimo[10:] == "43", f"Talle mal: {sinonimo[10:]}"
    assert sinonimo[8:10] == "02", f"Color mal: {sinonimo[8:10]} (esperaba 02=AZUL)"
    # El cod5 NO debe ser "11000" (el bug viejo)
    cod5 = sinonimo[3:8]
    assert cod5 != "11000", f"BUG: cod5 sigue siendo '11000' del barcode RBK1100033358"
    assert len(sinonimo) == 12


@requires_db
def test_db_buscar_articulo_flexagon_existente():
    """Verifica que buscar_articulo_por_sinonimo encuentra FLEXAGON existente."""
    from paso8_carga_factura import buscar_articulo_por_sinonimo
    # Sinónimo real de DB: 656ZAZUL0243 = FLEXAGON ENERGY TR 4 AZUL T43
    art = buscar_articulo_por_sinonimo("656ZAZUL0243", proveedor=656)
    assert art is not None, "No encontró artículo con sinónimo 656ZAZUL0243"
    assert art["codigo"] == 360087
    assert "FLEXAGON" in art["descripcion_1"]


@requires_db
def test_db_flujo_completo_verificacion():
    """Simula el flujo _verificar_articulos de app_carga.py para FLEXAGON AZUL."""
    from paso8_carga_factura import (
        construir_sinonimo, obtener_color_code, buscar_articulo_por_sinonimo
    )
    # Datos como llegarían del OCR
    modelo = "RBK1100033358"
    color = "AZUL"
    talle = "43"
    proveedor = 656
    descripcion = "FLEXAGON ENERGY TR 4 AZUL ZAPA DEP ACORD COMB"

    # Paso 1: color code
    color_code = obtener_color_code(color)
    assert color_code == "02"

    # Paso 2: construir sinónimo (debe auto-buscar cod5)
    sinonimo = construir_sinonimo(
        modelo, color_code, talle, proveedor=proveedor,
        descripcion=descripcion, color=color,
    )
    assert len(sinonimo) == 12
    assert sinonimo[3:8] != "11000", f"BUG: cod5 = '11000' (del barcode)"

    # Paso 3: buscar artículo existente
    art = buscar_articulo_por_sinonimo(
        sinonimo, proveedor=proveedor,
        modelo=modelo, color=color, talle=talle,
    )
    # Debe encontrar el FLEXAGON AZUL T43 existente (código 360087)
    assert art is not None, f"No encontró artículo con sinónimo {sinonimo}"
    assert "FLEXAGON" in art["descripcion_1"]
