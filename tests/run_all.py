#!/usr/bin/env python3
"""
run_all.py — Ejecuta todos los tests y genera reporte Markdown
===============================================================
Genera: _informes/test_results_YYYY-MM-DD.md
"""

import os
import sys
import unittest
import io
import traceback
from datetime import date

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(BASE_DIR, '..')
INFORMES_DIR = os.path.join(ROOT_DIR, '_informes')

sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, BASE_DIR)


def run_suite(test_module_name, label):
    """Ejecuta un módulo de tests y retorna (passed, failed, errors, details)."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    try:
        mod = __import__(test_module_name)
        suite = loader.loadTestsFromModule(mod)
    except Exception as e:
        return 0, 0, 1, [f"ERROR importando {test_module_name}: {e}\n{traceback.format_exc()}"]

    # Correr con output capturado
    stream = io.StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=2)
    result = runner.run(suite)

    details = []
    passed = result.testsRun - len(result.failures) - len(result.errors)

    for test, tb in result.failures:
        details.append(f"FAIL: {test}\n{tb}")
    for test, tb in result.errors:
        details.append(f"ERROR: {test}\n{tb}")

    return passed, len(result.failures), len(result.errors), details


def generar_reporte(resultados):
    """Genera el markdown del reporte."""
    hoy = date.today().isoformat()
    total_pass = sum(r['passed'] for r in resultados)
    total_fail = sum(r['failed'] for r in resultados)
    total_err = sum(r['errors'] for r in resultados)
    total = total_pass + total_fail + total_err

    estado_global = "PASS" if (total_fail + total_err) == 0 else "FAIL"

    lines = [
        f"# Test Results — {hoy}",
        "",
        f"**Estado global: {'PASS' if estado_global == 'PASS' else 'FAIL'}** "
        f"({total_pass}/{total} passed)",
        "",
        "## Resumen",
        "",
        "| Suite | Tests | Passed | Failed | Errors | Estado |",
        "|-------|-------|--------|--------|--------|--------|",
    ]

    for r in resultados:
        total_suite = r['passed'] + r['failed'] + r['errors']
        ok = (r['failed'] + r['errors']) == 0
        lines.append(
            f"| {r['label']} | {total_suite} | {r['passed']} | {r['failed']} | "
            f"{r['errors']} | {'PASS' if ok else 'FAIL'} |"
        )

    lines.append("")

    # Detalle de fallos
    any_details = any(r['details'] for r in resultados)
    if any_details:
        lines.append("## Detalle de Fallos")
        lines.append("")
        for r in resultados:
            if r['details']:
                lines.append(f"### {r['label']}")
                lines.append("")
                lines.append("```")
                for d in r['details']:
                    lines.append(d)
                lines.append("```")
                lines.append("")

    return "\n".join(lines)


def main():
    print("=" * 60)
    print("  Testing Automatico — app_reposicion.py")
    print("=" * 60)
    print()

    suites = [
        ("test_datos", "Datos SQL Server"),
        ("test_modelo", "Modelo Reposicion"),
        ("test_ui", "UI / Importacion"),
    ]

    resultados = []
    for module_name, label in suites:
        print(f"\n--- {label} ({module_name}) ---")
        passed, failed, errors, details = run_suite(module_name, label)
        resultados.append({
            'label': label,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'details': details,
        })
        status = "PASS" if (failed + errors) == 0 else "FAIL"
        print(f"  {passed} passed, {failed} failed, {errors} errors → {status}")

    # Generar reporte
    reporte = generar_reporte(resultados)

    os.makedirs(INFORMES_DIR, exist_ok=True)
    hoy = date.today().isoformat()
    ruta = os.path.join(INFORMES_DIR, f"test_results_{hoy}.md")
    with open(ruta, 'w') as f:
        f.write(reporte)

    total_fail = sum(r['failed'] for r in resultados)
    total_err = sum(r['errors'] for r in resultados)

    print(f"\n{'=' * 60}")
    print(f"  Reporte guardado en: {ruta}")
    if (total_fail + total_err) == 0:
        print("  RESULTADO GLOBAL: PASS")
    else:
        print(f"  RESULTADO GLOBAL: FAIL ({total_fail} failures, {total_err} errors)")
    print(f"{'=' * 60}")

    return 0 if (total_fail + total_err) == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
