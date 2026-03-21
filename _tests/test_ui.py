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


if __name__ == '__main__':
    unittest.main(verbosity=2)
