"""
test_autorepo.py — Suite de tests unitarios del motor de autocompensación inter-depósito.

Cubre los módulos de autorepo/:
  - umbrales      (clasificar_stock, safety_stock_poisson, es_escasez_cronica)
  - routing       (validar_ruta, empresa_de_deposito)
  - costos        (costo_transferencia, conviene_transferir, tipo_ruta)
  - scoring       (calcular_score, afinidad_marca_local_lift, ABCXYZ_SCORE)
  - curva_talles  (wasserstein_1d, shrinkage_james_stein, riesgo_drag_effect)
  - dep4_monitor  (clasificar_frenado)
  - decisor       (skippeado si aún no existe)

Sin conexión SQL. Data sintética dentro de cada test.

Run:
    python3 -m pytest _tests/test_autorepo.py -v
"""
from __future__ import annotations

import os
import sys

import pytest

# Asegurar que el worktree root está en sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


from autorepo.umbrales import (  # noqa: E402
    UMBRALES_V1,
    clasificar_stock,
    es_escasez_cronica,
    safety_stock_poisson,
)
from autorepo.costos import (  # noqa: E402
    COSTOS_V1,
    beneficio_esperado,
    conviene_transferir,
    costo_transferencia,
    tipo_ruta,
)
from autorepo.routing import (  # noqa: E402
    DEPOS_AUTOREPO_F1,
    empresa_de_deposito,
    validar_ruta,
)
from autorepo.scoring import (  # noqa: E402
    ABCXYZ_SCORE,
    SCORE_MIN_ACEPTACION,
    InputScore,
    afinidad_marca_local_lift,
    calcular_score,
)
from autorepo.curva_talles import (  # noqa: E402
    riesgo_drag_effect,
    shrinkage_james_stein,
    wasserstein_1d,
)
from autorepo.dep4_monitor import (  # noqa: E402
    ArticuloFrenado,
    clasificar_frenado,
)


# ============================================================================
# UMBRALES
# ============================================================================


def test_umbral_quiebre_critico_menos_7dias():
    """stock=3 / vel=1 par/dia → 3 días cobertura → QUIEBRE_CRITICO."""
    e = clasificar_stock(
        articulo=1,
        deposito=8,
        stock_actual=3,
        vel_diaria=1.0,
        abcxyz_clase='AX',
        subrubro=15,
        temporada_activa=True,
        dias_sin_venta=1,
        dias_sin_compra=30,
    )
    assert e.estado == 'QUIEBRE_CRITICO'
    assert e.dias_cobertura == pytest.approx(3.0, rel=0.01)


def test_umbral_sobrestock_temporada_activa():
    """200 pares / 2 ppd = 100 días cobertura > 75 (temp activa) → SOBRESTOCK."""
    e = clasificar_stock(
        articulo=2,
        deposito=8,
        stock_actual=200,
        vel_diaria=2.0,
        abcxyz_clase='BY',
        subrubro=20,
        temporada_activa=True,
        dias_sin_venta=5,
        dias_sin_compra=60,
    )
    assert e.estado == 'SOBRESTOCK'
    # Umbral temporada activa: 75 días
    assert UMBRALES_V1['sobrestock_temp_activa_dias'] == 75


def test_umbral_dead_stock():
    """Stock > 0, vel=0, sin venta > 90 días, sin compra > 180 → DEAD_STOCK."""
    e = clasificar_stock(
        articulo=3,
        deposito=8,
        stock_actual=10,
        vel_diaria=0.0,
        abcxyz_clase='CZ',
        subrubro=30,
        temporada_activa=False,
        dias_sin_venta=120,
        dias_sin_compra=240,
    )
    assert e.estado == 'DEAD_STOCK'


def test_safety_stock_poisson_AX():
    """Con vel=1, LT=2, service_level AX (0.97): ss >= 0 y razonable."""
    ss = safety_stock_poisson(
        vel_diaria=1.0,
        lead_time_dias=2,
        service_level=0.97,
    )
    assert ss >= 0
    # Para λ=2, ppf(0.97) sobre Poisson ≈ 5 → ss ≈ 3
    # Con fallback normal, ss = ceil(1.88 * sqrt(2)) ≈ 3
    assert ss <= 10  # sanity cap

    # Vel 0 → ss 0
    assert safety_stock_poisson(0, 2, 0.97) == 0
    # Lead time 0 → ss 0
    assert safety_stock_poisson(1.0, 0, 0.97) == 0


def test_es_escasez_cronica_true_para_12m_quebrados():
    """11/12 meses quebrados hist, 1/3 meses recientes → CRÓNICO (ratio 1/11 < 0.66)."""
    assert es_escasez_cronica(articulo=1, meses_quebrados_12m=11, meses_quebrados_3m=1) is True

    # 4/12 < 75% → no crónico
    assert es_escasez_cronica(articulo=2, meses_quebrados_12m=4, meses_quebrados_3m=3) is False

    # 9/12 hist, 9/3? — imposible, pero ratio alto: 3/9 = 0.33 < 0.66 → crónico
    assert es_escasez_cronica(articulo=3, meses_quebrados_12m=9, meses_quebrados_3m=3) is True


# ============================================================================
# ROUTING
# ============================================================================


def test_validar_ruta_0_a_8_es_valida():
    """Central VT (0) → Junín (8): ruta válida F1, cross-empresa."""
    r = validar_ruta(0, 8)
    assert r.valida is True
    assert r.motivo_invalidez is None
    assert r.origen == 0
    assert r.destino == 8
    assert r.cross_empresa is True  # 0 default H4, 8 default CALZALINDO


def test_validar_ruta_4_excluida_f1():
    """Depósito 4 (Marroquinería) está fuera de F1."""
    r = validar_ruta(4, 8)
    assert r.valida is False
    assert r.motivo_invalidez == 'fuera_alcance_f1'


def test_validar_ruta_mismo_deposito_invalida():
    """origen == destino → mismo_deposito."""
    r = validar_ruta(8, 8)
    assert r.valida is False
    assert r.motivo_invalidez == 'mismo_deposito'


def test_empresa_default_dep_11_es_calzalindo():
    """Depósito 11 (Alternativo/Zapatería VT) default = CALZALINDO."""
    assert empresa_de_deposito(11) == 'CALZALINDO'
    assert empresa_de_deposito(0) == 'H4'
    assert empresa_de_deposito(8) == 'CALZALINDO'
    assert 0 in DEPOS_AUTOREPO_F1 and 11 in DEPOS_AUTOREPO_F1


# ============================================================================
# COSTOS
# ============================================================================


def test_costo_ruta_satelite_minimo_15():
    """Ruta satélite: mínimo 15 pares. 10 pares no cumple, 15 sí."""
    ev_bajo = costo_transferencia(origen=0, destino=8, pares=10, precio_promedio_par=20000)
    assert ev_bajo.ruta == 'satelite'
    assert ev_bajo.minimo_aplicable == 15
    assert ev_bajo.cumple_minimo is False

    ev_ok = costo_transferencia(origen=0, destino=8, pares=15, precio_promedio_par=20000)
    assert ev_ok.cumple_minimo is True


def test_costo_ruta_central_vt_sin_minimo():
    """Ruta central_vt (0 <-> 11): sin mínimo."""
    ev = costo_transferencia(origen=0, destino=11, pares=3, precio_promedio_par=25000)
    assert ev.ruta == 'central_vt'
    assert ev.minimo_aplicable == 0
    assert ev.cumple_minimo is True
    # Fijo central_vt = 8000
    assert ev.fijo == float(COSTOS_V1['fijo_remito_central_vt'])


def test_no_transferir_si_origen_tambien_vende():
    """prob_origen > 0.6 * prob_destino → origen_tambien_vende."""
    decision, razon, costo, benef = conviene_transferir(
        origen=0,
        destino=8,
        pares=20,
        precio_promedio_par=25000,
        margen_par=12000,
        prob_venta_destino=0.70,
        prob_venta_origen=0.60,  # 0.60 > 0.6 * 0.70 = 0.42 → bloquea
    )
    assert decision is False
    assert razon == 'origen_tambien_vende'


def test_beneficio_suficiente_con_alfa_1_3():
    """Caso clásico que cumple todas las reglas → conviene=True."""
    decision, razon, costo, benef = conviene_transferir(
        origen=0,
        destino=8,
        pares=20,
        precio_promedio_par=25000,
        margen_par=12000,
        prob_venta_destino=0.75,
        prob_venta_origen=0.20,
    )
    # Beneficio esperado = 12000*0.75*20 - 12000*0.20*20 = 180000 - 48000 = 132000
    # Costo = fijo 15000 + 20*500 + 20*25000*0.015 = 15000 + 10000 + 7500 = 32500
    # b/c = 132000/32500 = 4.06 > 1.30 → OK
    assert decision is True
    assert razon == 'conviene'
    assert costo > 0
    assert benef > 0
    assert (benef / costo) >= COSTOS_V1['alfa_colchon']


def test_tipo_ruta_mapea_correctamente():
    """Sanity: tipos de ruta principales."""
    assert tipo_ruta(0, 11) == 'central_vt'
    assert tipo_ruta(0, 8) == 'satelite'
    assert tipo_ruta(8, 7) == 'satelite_satelite'
    assert tipo_ruta(0, 99) is None


# ============================================================================
# SCORING
# ============================================================================


def _input_score_base(**over) -> InputScore:
    """Input base 'urgente' para ajustar por test."""
    base = dict(
        articulo=100,
        origen=0,
        destino=8,
        stock_origen=40,
        stock_destino=1,
        vel_origen_dia=0.2,
        vel_destino_dia=1.5,
        p95_vel_categoria=2.0,
        abcxyz_clase='AX',
        margen_pct=45.0,
        afinidad_marca_local=0.8,
        dias_stock_origen=120,
        factor_estacional=1.0,
        riesgo_drag=0.0,
    )
    base.update(over)
    return InputScore(**base)


def test_score_estacional_cero_apaga_todo():
    """EST < 0.3 → score = 0 (gate)."""
    inp = _input_score_base(factor_estacional=0.1)
    r = calcular_score(inp)
    assert r.score == 0.0
    assert r.aceptable is False


def test_score_drag_penalty_40():
    """riesgo_drag=1.0 → penal_drag explícito = 40 puntos (default)."""
    inp_sin = _input_score_base(riesgo_drag=0.0)
    inp_con = _input_score_base(riesgo_drag=1.0)
    r_sin = calcular_score(inp_sin)
    r_con = calcular_score(inp_con)
    # El campo penal_drag debe ser exactamente 40.0 (riesgo=1.0 * max=40)
    assert r_con.penal_drag == pytest.approx(40.0, abs=0.01)
    # Score con drag debe ser estrictamente menor (penalización efectiva)
    assert r_con.score < r_sin.score
    # La caída total incluye penal_drag + pérdida en componente curva_ok (peso 5)
    # Diferencia esperada: 40 (penal) + 5 (curva_ok factor=1→0) = 45
    delta = r_sin.score - r_con.score
    assert 35 <= delta <= 50


def test_score_caso_urgente_alto():
    """Caso clásico urgente (destino roto + exceso origen + AX + temp activa) → aceptable."""
    inp = _input_score_base()
    r = calcular_score(inp)
    assert r.score > 0
    assert r.score >= SCORE_MIN_ACEPTACION
    assert r.aceptable is True
    # Componentes clave
    assert r.componentes['EST'] == pytest.approx(1.0)
    assert r.componentes['ABCXYZ'] == pytest.approx(ABCXYZ_SCORE['AX'])


def test_abcxyz_lookup_completo():
    """Las 9 clases principales están en el lookup con orden esperado."""
    assert ABCXYZ_SCORE['AX'] > ABCXYZ_SCORE['AY'] > ABCXYZ_SCORE['AZ']
    assert ABCXYZ_SCORE['AX'] > ABCXYZ_SCORE['BX']
    assert ABCXYZ_SCORE['BX'] > ABCXYZ_SCORE['BY'] > ABCXYZ_SCORE['BZ']
    assert ABCXYZ_SCORE['CZ'] < ABCXYZ_SCORE['CX']
    assert ABCXYZ_SCORE['AX'] == 1.0
    for clase in ('AX', 'AY', 'AZ', 'BX', 'BY', 'BZ', 'CX', 'CY', 'CZ'):
        assert clase in ABCXYZ_SCORE


def test_afinidad_marca_lift_neutro_con_denominador_cero():
    """ventas_local_total=0 → 0.5 neutral. lift=1 → 0.5. lift≥2 → 1.0."""
    # Denominador 0
    assert afinidad_marca_local_lift(10, 0, 100, 1000) == 0.5
    assert afinidad_marca_local_lift(10, 100, 100, 0) == 0.5

    # Lift neutro = 1.0 (marca en local igual share que cadena) → AFF = 0.5
    aff_neutro = afinidad_marca_local_lift(
        ventas_marca_local=50, ventas_local_total=500,
        ventas_marca_global=100, ventas_global_total=1000,
    )
    # share_local = 0.10, share_global = 0.10 → lift 1.0 → AFF = 0.5
    assert aff_neutro == pytest.approx(0.5)

    # Lift alto = marca concentrada en local (0.5 local vs 0.1 global) → capped 1.0
    aff_alto = afinidad_marca_local_lift(
        ventas_marca_local=250, ventas_local_total=500,
        ventas_marca_global=100, ventas_global_total=1000,
    )
    # lift = 0.5 / 0.1 = 5 → min(5/2, 1) = 1.0
    assert aff_alto == pytest.approx(1.0)


# ============================================================================
# CURVA TALLES
# ============================================================================


def test_wasserstein_curvas_iguales_cero():
    """Dos curvas idénticas → distancia 0."""
    c = {39: 0.2, 40: 0.3, 41: 0.3, 42: 0.2}
    assert wasserstein_1d(c, dict(c)) == pytest.approx(0.0, abs=1e-9)


def test_wasserstein_curvas_desplazadas():
    """Dos curvas desplazadas un talle → distancia > 0 y mayor que curvas solapadas."""
    c1 = {39: 0.5, 40: 0.5}
    c2 = {40: 0.5, 41: 0.5}
    w_desplazada = wasserstein_1d(c1, c2)
    assert w_desplazada > 0

    # Curvas más desplazadas deben tener distancia mayor
    c3 = {42: 0.5, 43: 0.5}
    w_mas_desplazada = wasserstein_1d(c1, c3)
    assert w_mas_desplazada > w_desplazada

    # Monotonicidad: no-solapada > parcialmente solapada > iguales (=0)
    assert wasserstein_1d(c1, c1) == 0.0


def test_shrinkage_n_pequeno_domina_prior():
    """Con n muy chico (n=1) y k=100, λ=1/101 → domina casi totalmente el prior."""
    local = {42: 1.0}
    prior = {40: 0.3, 41: 0.3, 42: 0.2, 43: 0.2}
    mezcla = shrinkage_james_stein(local, prior, n_local=1, k=100)
    # Talle 42 en mezcla debería estar cerca del prior (0.2) más un pelín
    # λ = 1/101 ≈ 0.0099 → pct_42 = 0.0099*1 + 0.9901*0.2 = 0.0099 + 0.198 ≈ 0.208
    assert 0.15 < mezcla[42] < 0.25
    # La suma debe ser 1
    assert sum(mezcla.values()) == pytest.approx(1.0, abs=1e-6)


def test_drag_effect_cero_si_curva_estable():
    """Si transferís de un talle con sobrestock, completeness no se rompe → riesgo=0."""
    # Stock amplio en todos los talles
    stock = {39: 10, 40: 10, 41: 10, 42: 20, 43: 10, 44: 10}
    ideal = {39: 0.15, 40: 0.15, 41: 0.20, 42: 0.20, 43: 0.15, 44: 0.15}
    # Mover 5 de 42 (que tiene 20): queda 15, sigue cubriendo
    riesgo = riesgo_drag_effect(stock, ideal, talle_transferido=42, cantidad_transferida=5)
    assert riesgo == 0.0


def test_drag_effect_riesgo_alto_si_queda_roto():
    """Si vaciar un talle único rompe la cobertura drásticamente → riesgo > 0."""
    # Stock pequeño, 42 es único con algo
    stock = {40: 1, 41: 1, 42: 10, 43: 1, 44: 1}
    ideal = {40: 0.10, 41: 0.20, 42: 0.30, 43: 0.25, 44: 0.15}
    # Antes: comp alto. Transferir 10 de 42 lo deja en 0 → comp cae.
    riesgo = riesgo_drag_effect(stock, ideal, talle_transferido=42, cantidad_transferida=10)
    assert riesgo > 0.0


# ============================================================================
# DEP4 MONITOR
# ============================================================================


def _art(
    articulo=1, dias_sin_compra=500, capital_inmov=100_000.0, subrubro=1, stock=1
) -> ArticuloFrenado:
    return ArticuloFrenado(
        articulo=articulo,
        stock_dep4=stock,
        ventas_90d_dep4=0,
        ult_compra="2024-01-01",
        dias_sin_compra=dias_sin_compra,
        costo_cer_unit=capital_inmov / max(stock, 1),
        capital_inmov=capital_inmov,
        subrubro=subrubro,
        marca=100,
    )


def test_clasificar_frenado_remate_ult_compra_mayor_2anios():
    """dias_sin_compra > 730 → REMATE."""
    art = _art(dias_sin_compra=7600, capital_inmov=1_200_000)
    assert clasificar_frenado(art) == "REMATE"


def test_clasificar_frenado_transferible_con_capital_alto():
    """dias < 365 + capital > 200000 → TRANSFERIBLE."""
    art = _art(dias_sin_compra=200, capital_inmov=300_000)
    assert clasificar_frenado(art) == "TRANSFERIBLE"


def test_clasificar_frenado_revision_zona_intermedia():
    """Caso intermedio: 500 días, capital bajo → REVISION."""
    art = _art(dias_sin_compra=500, capital_inmov=60_000)
    assert clasificar_frenado(art) == "REVISION"


def test_clasificar_frenado_subrubro_desaparecido_es_remate():
    """Subrubro en set de desaparecidos → REMATE incluso si capital alto."""
    art = _art(dias_sin_compra=200, capital_inmov=500_000, subrubro=99)
    assert clasificar_frenado(art, subrubros_desaparecidos={99}) == "REMATE"


# ============================================================================
# DECISOR (skippeado si no existe)
# ============================================================================

_decisor_mod = pytest.importorskip(
    "autorepo.decisor",
    reason="autorepo.decisor aún no existe (se estará creando en paralelo)",
)


def test_decisor_caso_sintetico_genera_propuesta():
    """Si el módulo existe, al menos debe exponer una función decidir()."""
    assert hasattr(_decisor_mod, "decidir"), "autorepo.decisor debe exponer decidir()"
