#!/usr/bin/env python3
"""
test_ui.py — Tests de importación y UI de app_reposicion.py
============================================================
Verifica que:
  - app_reposicion.py se importa sin errores
  - Todas las funciones principales existen
  - No hay AttributeErrors en funciones clave
  - Los tabs están definidos
"""

import os
import sys
import unittest
import importlib
from unittest.mock import MagicMock, patch

# Fix SSL
_ssl_conf = os.path.join(os.path.dirname(__file__), '..', '_scripts_oneshot', 'openssl_legacy.cnf')
_ssl_conf = os.path.abspath(_ssl_conf)
if os.path.exists(_ssl_conf):
    os.environ['OPENSSL_CONF'] = _ssl_conf

# Agregar raíz al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _setup_streamlit_mock():
    """Configura un mock completo de streamlit para importar sin UI."""
    mock_st = MagicMock()
    mock_st.session_state = {}
    mock_st.cache_data = lambda *a, **kw: (lambda f: f)

    # Mock tabs para que devuelvan context managers
    mock_tab = MagicMock()
    mock_tab.__enter__ = MagicMock(return_value=None)
    mock_tab.__exit__ = MagicMock(return_value=False)
    mock_st.tabs.return_value = [mock_tab] * 20

    # set_page_config no debería fallar
    mock_st.set_page_config = MagicMock()

    sys.modules['streamlit'] = mock_st
    return mock_st


class TestImportacion(unittest.TestCase):
    """Verifica que app_reposicion.py se importa sin errores."""

    @classmethod
    def setUpClass(cls):
        cls.st_mock = _setup_streamlit_mock()
        # Forzar reimport si ya estaba cacheado
        if 'app_reposicion' in sys.modules:
            del sys.modules['app_reposicion']

    def test_import_sin_errores(self):
        """app_reposicion.py se importa correctamente."""
        try:
            import app_reposicion
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Error al importar app_reposicion: {e}")

    def test_import_config(self):
        """config.py se importa correctamente."""
        try:
            import config
            self.assertTrue(hasattr(config, 'CONN_COMPRAS'))
            self.assertTrue(hasattr(config, 'PROVEEDORES'))
            self.assertTrue(hasattr(config, 'get_conn_string'))
        except Exception as e:
            self.fail(f"Error al importar config: {e}")


class TestFuncionesExisten(unittest.TestCase):
    """Verifica que las funciones principales del módulo existen."""

    @classmethod
    def setUpClass(cls):
        _setup_streamlit_mock()
        if 'app_reposicion' in sys.modules:
            del sys.modules['app_reposicion']
        cls.mod = importlib.import_module('app_reposicion')

    FUNCIONES_REQUERIDAS = [
        'proyectar_waterfall',
        'calcular_dias_cobertura',
        'calcular_roi',
        'analizar_quiebre_batch',
        'factor_estacional_batch',
        'obtener_pendientes',
        'cargar_resumen_marcas',
        'cargar_productos_por_marca',
        'cargar_productos_por_proveedor',
        'calcular_alertas_talles',
        'render_dashboard',
        'analizar_producto_detalle',
        'insertar_pedido_produccion',
        'buscar_sustitutos_embedding',
        'detectar_tendencias_emergentes',
        'calcular_curva_talle_ideal',
        'escaneo_canibalizacion_masivo',
    ]

    def test_funciones_existen(self):
        for nombre in self.FUNCIONES_REQUERIDAS:
            with self.subTest(funcion=nombre):
                self.assertTrue(
                    hasattr(self.mod, nombre),
                    f"Falta función: {nombre}"
                )
                self.assertTrue(
                    callable(getattr(self.mod, nombre)),
                    f"{nombre} no es callable"
                )


class TestConstantes(unittest.TestCase):
    """Verifica constantes clave."""

    @classmethod
    def setUpClass(cls):
        _setup_streamlit_mock()
        if 'app_reposicion' in sys.modules:
            del sys.modules['app_reposicion']
        cls.mod = importlib.import_module('app_reposicion')

    def test_ventanas_dias(self):
        self.assertEqual(self.mod.VENTANAS_DIAS, [15, 30, 45, 60])

    def test_depositos(self):
        self.assertIsInstance(self.mod.DEPOS_INFORMES, tuple)
        self.assertGreater(len(self.mod.DEPOS_INFORMES), 5)

    def test_exclusion_ventas(self):
        self.assertIn('7', self.mod.EXCL_VENTAS)
        self.assertIn('36', self.mod.EXCL_VENTAS)

    def test_exclusion_marcas_gastos(self):
        for m in ('1316', '1317', '1158', '436'):
            self.assertIn(m, self.mod.EXCL_MARCAS_GASTOS)


class TestTabsDefinidos(unittest.TestCase):
    """Verifica que los tabs principales están referenciados en el código."""

    def test_tabs_en_codigo(self):
        """Lee el source y verifica que los 9 tabs están definidos."""
        source_path = os.path.join(os.path.dirname(__file__), '..', 'app_reposicion.py')
        with open(source_path, 'r') as f:
            source = f.read()

        tabs_esperados = [
            'tab_surtido', 'tab_dashboard', 'tab_waterfall',
            'tab_optimizar', 'tab_curva', 'tab_canibal',
            'tab_emergentes', 'tab_pedido', 'tab_historial'
        ]
        for tab in tabs_esperados:
            with self.subTest(tab=tab):
                self.assertIn(tab, source, f"Tab {tab} no encontrado en source")


class TestSinAttributeErrors(unittest.TestCase):
    """Ejecuta funciones puras con inputs controlados para detectar AttributeErrors."""

    @classmethod
    def setUpClass(cls):
        _setup_streamlit_mock()
        if 'app_reposicion' in sys.modules:
            del sys.modules['app_reposicion']
        cls.mod = importlib.import_module('app_reposicion')

    def test_waterfall_no_attr_error(self):
        try:
            self.mod.proyectar_waterfall(1.0, 50, {m: 1.0 for m in range(1, 13)})
        except AttributeError as e:
            self.fail(f"AttributeError en proyectar_waterfall: {e}")

    def test_cobertura_no_attr_error(self):
        try:
            self.mod.calcular_dias_cobertura(1.0, 50, {m: 1.0 for m in range(1, 13)})
        except AttributeError as e:
            self.fail(f"AttributeError en calcular_dias_cobertura: {e}")

    def test_roi_no_attr_error(self):
        try:
            self.mod.calcular_roi(10000, 20000, 1.0, {m: 1.0 for m in range(1, 13)}, 10, 5)
        except AttributeError as e:
            self.fail(f"AttributeError en calcular_roi: {e}")

    def test_render_semaforo_no_attr_error(self):
        try:
            for status in ('rojo', 'amarillo', 'verde'):
                self.mod.render_semaforo(status)
        except AttributeError as e:
            self.fail(f"AttributeError en render_semaforo: {e}")


class TestFiltroMarcaBugFix(unittest.TestCase):
    """Tests para el bug fix del filtro de marca.

    Bug: al cambiar entre modo Marca y Proveedor, el indice del selectbox
    persistia en session_state causando que se seleccione la marca incorrecta
    o IndexError si la lista cambiaba de tamano.

    Fix aplicado:
    1. Reset del indice al cambiar de modo (session_state cleanup)
    2. Bounds check antes de acceder a codigos_marca[sel_idx]
    3. Cache en cargar_resumen_marcas() (faltaba @st.cache_data)
    """

    def test_source_has_modo_filtro_prev_tracking(self):
        """Verifica que el fix trackea el modo anterior para detectar cambios."""
        source_path = os.path.join(os.path.dirname(__file__), '..', 'app_reposicion.py')
        with open(source_path, 'r') as f:
            source = f.read()
        self.assertIn('_modo_filtro_prev', source,
                       "Falta tracking de modo_filtro anterior para reset")

    def test_source_has_marca_filtro_reset(self):
        """Verifica que el indice marca_filtro se resetea al cambiar de modo."""
        source_path = os.path.join(os.path.dirname(__file__), '..', 'app_reposicion.py')
        with open(source_path, 'r') as f:
            source = f.read()
        self.assertIn("st.session_state['marca_filtro'] = 0", source,
                       "Falta reset de marca_filtro a 0 al cambiar de modo")

    def test_source_has_prov_filtro_reset(self):
        """Verifica que el indice prov_filtro se resetea al cambiar de modo."""
        source_path = os.path.join(os.path.dirname(__file__), '..', 'app_reposicion.py')
        with open(source_path, 'r') as f:
            source = f.read()
        self.assertIn("st.session_state['prov_filtro'] = 0", source,
                       "Falta reset de prov_filtro a 0 al cambiar de modo")

    def test_source_has_bounds_check_marca(self):
        """Verifica bounds check en sel_idx para codigos_marca."""
        source_path = os.path.join(os.path.dirname(__file__), '..', 'app_reposicion.py')
        with open(source_path, 'r') as f:
            source = f.read()
        self.assertIn('sel_idx >= len(codigos_marca)', source,
                       "Falta bounds check para sel_idx en codigos_marca")

    def test_source_has_bounds_check_prov(self):
        """Verifica bounds check en sel_idx_p para codigos_prov."""
        source_path = os.path.join(os.path.dirname(__file__), '..', 'app_reposicion.py')
        with open(source_path, 'r') as f:
            source = f.read()
        self.assertIn('sel_idx_p >= len(codigos_prov)', source,
                       "Falta bounds check para sel_idx_p en codigos_prov")

    def test_source_has_cache_resumen_marcas(self):
        """Verifica que cargar_resumen_marcas tiene @st.cache_data."""
        source_path = os.path.join(os.path.dirname(__file__), '..', 'app_reposicion.py')
        with open(source_path, 'r') as f:
            source = f.read()
        # Check that the cache decorator appears right before def cargar_resumen_marcas
        idx_func = source.index('def cargar_resumen_marcas')
        # Look in the 100 chars before the function definition
        preceding = source[max(0, idx_func - 100):idx_func]
        self.assertIn('cache_data', preceding,
                       "cargar_resumen_marcas() falta @st.cache_data decorator")

    def test_excl_marcas_gastos_in_source(self):
        """Verifica que EXCL_MARCAS_GASTOS incluye las 4 marcas de gastos."""
        source_path = os.path.join(os.path.dirname(__file__), '..', 'app_reposicion.py')
        with open(source_path, 'r') as f:
            source = f.read()
        for marca in ('1316', '1317', '1158', '436'):
            self.assertIn(marca, source,
                           f"Marca de gastos {marca} falta en EXCL_MARCAS_GASTOS")

    def test_filter_mode_reset_logic(self):
        """Simula el cambio de modo y verifica que session_state se limpia."""
        # Simular session_state como dict
        session_state = {
            '_modo_filtro_prev': 'Marca',
            'marca_filtro': 5,
            'prov_filtro': 3,
        }

        # Simular cambio a Proveedor
        modo_filtro = "Proveedor"
        prev_modo = session_state.get('_modo_filtro_prev', None)
        if prev_modo is not None and prev_modo != modo_filtro:
            if modo_filtro == "Marca" and 'marca_filtro' in session_state:
                session_state['marca_filtro'] = 0
            elif modo_filtro == "Proveedor" and 'prov_filtro' in session_state:
                session_state['prov_filtro'] = 0
        session_state['_modo_filtro_prev'] = modo_filtro

        # prov_filtro should be reset to 0, marca_filtro untouched
        self.assertEqual(session_state['prov_filtro'], 0)
        self.assertEqual(session_state['marca_filtro'], 5)
        self.assertEqual(session_state['_modo_filtro_prev'], 'Proveedor')

    def test_filter_mode_reset_marca(self):
        """Simula cambio de Proveedor a Marca y verifica reset."""
        session_state = {
            '_modo_filtro_prev': 'Proveedor',
            'marca_filtro': 8,
            'prov_filtro': 2,
        }

        modo_filtro = "Marca"
        prev_modo = session_state.get('_modo_filtro_prev', None)
        if prev_modo is not None and prev_modo != modo_filtro:
            if modo_filtro == "Marca" and 'marca_filtro' in session_state:
                session_state['marca_filtro'] = 0
            elif modo_filtro == "Proveedor" and 'prov_filtro' in session_state:
                session_state['prov_filtro'] = 0
        session_state['_modo_filtro_prev'] = modo_filtro

        self.assertEqual(session_state['marca_filtro'], 0)
        self.assertEqual(session_state['prov_filtro'], 2)

    def test_bounds_check_prevents_index_error(self):
        """Verifica que bounds check clampea indice fuera de rango."""
        codigos_marca = [None, 515, 294, 104]  # 4 items
        sel_idx = 7  # stale index, out of range

        if sel_idx >= len(codigos_marca):
            sel_idx = 0

        self.assertEqual(sel_idx, 0)

    def test_bounds_check_valid_index_unchanged(self):
        """Verifica que bounds check no afecta indices validos."""
        codigos_marca = [None, 515, 294, 104]
        sel_idx = 2

        if sel_idx >= len(codigos_marca):
            sel_idx = 0

        self.assertEqual(sel_idx, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
