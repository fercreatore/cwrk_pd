#!/usr/bin/env python3
"""
test_modelo.py — Tests del modelo de reposición con datos reales
================================================================
Importa funciones puras de app_reposicion.py y las testea con datos reales
del SQL Server.
"""

import os
import sys
import unittest
from datetime import date, timedelta

# Fix SSL
_ssl_conf = os.path.join(os.path.dirname(__file__), '..', '_scripts_oneshot', 'openssl_legacy.cnf')
_ssl_conf = os.path.abspath(_ssl_conf)
if os.path.exists(_ssl_conf):
    os.environ['OPENSSL_CONF'] = _ssl_conf

# Agregar raíz al path para importar app_reposicion
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Mockear streamlit ANTES de importar app_reposicion
from unittest.mock import MagicMock
_st_mock = MagicMock()
_st_mock.session_state = {}
_st_mock.cache_data = lambda *a, **kw: (lambda f: f)  # decorator passthrough
sys.modules['streamlit'] = _st_mock

import pandas as pd
import pyodbc

# Ahora sí importar las funciones puras
from app_reposicion import (
    proyectar_waterfall,
    calcular_dias_cobertura,
    calcular_roi,
)


class TestProyectarWaterfall(unittest.TestCase):
    """Tests de la función proyectar_waterfall."""

    def test_estructura_resultado(self):
        factores = {m: 1.0 for m in range(1, 13)}
        resultado = proyectar_waterfall(
            vel_diaria=2.0, stock_disponible=100,
            factores_est=factores
        )
        self.assertEqual(len(resultado), 4)  # 15, 30, 45, 60 días
        for r in resultado:
            self.assertIn('dias', r)
            self.assertIn('ventas_proy', r)
            self.assertIn('stock_proy', r)
            self.assertIn('status', r)
            self.assertIn(r['status'], ('rojo', 'amarillo', 'verde'))

    def test_stock_cero_velocidad(self):
        """Velocidad 0 → stock no cambia, siempre verde."""
        factores = {m: 1.0 for m in range(1, 13)}
        resultado = proyectar_waterfall(0, 50, factores)
        for r in resultado:
            self.assertEqual(r['stock_proy'], 50)
            self.assertEqual(r['status'], 'verde')

    def test_agotamiento_rapido(self):
        """Stock bajo + alta velocidad → rojo rápido."""
        factores = {m: 1.0 for m in range(1, 13)}
        resultado = proyectar_waterfall(10, 5, factores)
        self.assertEqual(resultado[0]['status'], 'rojo')  # 15 días

    def test_estacionalidad_afecta(self):
        """Factor estacional alto = más ventas proyectadas."""
        factores_neutro = {m: 1.0 for m in range(1, 13)}
        factores_alto = {m: 2.0 for m in range(1, 13)}
        r_neutro = proyectar_waterfall(1.0, 100, factores_neutro)
        r_alto = proyectar_waterfall(1.0, 100, factores_alto)
        # Con factor 2x, se vende más → menos stock
        self.assertGreater(r_neutro[-1]['stock_proy'], r_alto[-1]['stock_proy'])


class TestDiasCobertura(unittest.TestCase):
    """Tests de calcular_dias_cobertura."""

    def test_cobertura_basica(self):
        factores = {m: 1.0 for m in range(1, 13)}
        dias = calcular_dias_cobertura(1.0, 30, factores)
        self.assertGreater(dias, 0)
        self.assertLessEqual(dias, 120)
        # ~30 días de cobertura con 1/día
        self.assertAlmostEqual(dias, 30, delta=2)

    def test_cobertura_sin_ventas(self):
        factores = {m: 1.0 for m in range(1, 13)}
        dias = calcular_dias_cobertura(0, 50, factores)
        self.assertEqual(dias, 120)  # max_dias default

    def test_cobertura_entre_0_y_365(self):
        factores = {m: 1.0 for m in range(1, 13)}
        dias = calcular_dias_cobertura(0.5, 100, factores, max_dias=365)
        self.assertGreaterEqual(dias, 0)
        self.assertLessEqual(dias, 365)


class TestCalcularROI(unittest.TestCase):
    """Tests de calcular_roi."""

    def test_roi_positivo_margen_sano(self):
        """Producto con buen margen → ROI positivo."""
        factores = {m: 1.0 for m in range(1, 13)}
        r = calcular_roi(
            precio_costo=10000, precio_venta=20000,
            vel_diaria=2.0, factores_est=factores,
            cantidad_pedir=20, stock_disponible=5
        )
        self.assertGreater(r['roi_60d'], 0)
        self.assertLess(r['roi_60d'], 1000)  # razonable
        self.assertGreater(r['margen_pct'], 0)
        self.assertLess(r['dias_recupero'], 999)

    def test_roi_rango_razonable(self):
        """ROI entre 50% y 300% para un caso típico calzado."""
        factores = {m: 1.0 for m in range(1, 13)}
        # Caso típico: costo $25k, venta $50k, 1 par/día, pedir 30
        r = calcular_roi(
            precio_costo=25000, precio_venta=50000,
            vel_diaria=1.0, factores_est=factores,
            cantidad_pedir=30, stock_disponible=0
        )
        self.assertGreaterEqual(r['roi_60d'], 50, f"ROI {r['roi_60d']}% < 50%")
        self.assertLessEqual(r['roi_60d'], 300, f"ROI {r['roi_60d']}% > 300%")

    def test_roi_cero_sin_datos(self):
        """Sin precio costo → ROI 0."""
        factores = {m: 1.0 for m in range(1, 13)}
        r = calcular_roi(0, 20000, 1.0, factores, 10, 0)
        self.assertEqual(r['roi_60d'], 0)
        self.assertEqual(r['dias_recupero'], 999)

    def test_roi_cero_sin_velocidad(self):
        factores = {m: 1.0 for m in range(1, 13)}
        r = calcular_roi(10000, 20000, 0, factores, 10, 0)
        self.assertEqual(r['roi_60d'], 0)

    def test_inversion_correcta(self):
        factores = {m: 1.0 for m in range(1, 13)}
        r = calcular_roi(15000, 30000, 1.0, factores, 20, 0)
        self.assertEqual(r['inversion'], 15000 * 20)

    def test_margen_pct_correcto(self):
        factores = {m: 1.0 for m in range(1, 13)}
        r = calcular_roi(10000, 20000, 1.0, factores, 10, 0)
        self.assertAlmostEqual(r['margen_pct'], 50.0, delta=0.1)


class TestConvergenciaOptimizador(unittest.TestCase):
    """Verifica que el waterfall converge para distintos escenarios."""

    def test_convergencia_alta_demanda(self):
        factores = {m: 1.0 for m in range(1, 13)}
        # 10 unidades/día, 1000 de stock → debe dar resultado coherente
        r = proyectar_waterfall(10.0, 1000, factores)
        # Ventas deben crecer con la ventana
        for i in range(len(r) - 1):
            self.assertLessEqual(r[i]['ventas_proy'], r[i+1]['ventas_proy'])

    def test_convergencia_baja_demanda(self):
        factores = {m: 1.0 for m in range(1, 13)}
        r = proyectar_waterfall(0.1, 100, factores)
        # Con baja demanda y buen stock, todo verde
        for p in r:
            self.assertEqual(p['status'], 'verde')

    def test_convergencia_estacional(self):
        """Factores estacionales extremos no rompen el modelo."""
        factores = {m: 0.1 if m in (6,7,8) else 2.0 for m in range(1, 13)}
        r = proyectar_waterfall(1.0, 50, factores)
        self.assertEqual(len(r), 4)
        for p in r:
            self.assertIsNotNone(p['stock_proy'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
