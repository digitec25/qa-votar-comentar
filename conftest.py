"""
conftest.py - Captura de evidencias automáticas para la suite de pruebas.

Genera una captura de pantalla por cada test (PASSED / FAILED / SKIPPED) en
./evidencias/ con nombre <resultado>_<test>_<timestamp>.png, y la incrusta
en el reporte HTML (pytest-html) en base64, para que reporte.html sea
realmente autocontenido y portable.
"""

import os
import base64
import datetime
import pytest

EVID_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidencias")
os.makedirs(EVID_DIR, exist_ok=True)


def _driver_from_item(item):
    for fname in ("driver", "car_page", "logged_in_car"):
        if fname in getattr(item, "funcargs", {}):
            obj = item.funcargs[fname]
            return getattr(obj, "driver", obj)
    return None


def _slug(texto):
    return "".join(c if (c.isalnum() or c in "-_") else "_" for c in texto)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when != "call":
        return

    driver = _driver_from_item(item)
    if driver is None:
        return

    resultado = "PASSED" if report.passed else ("FAILED" if report.failed else "SKIPPED")
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{resultado}_{_slug(item.name)}_{ts}.png"
    ruta = os.path.join(EVID_DIR, fname)

    try:
        driver.save_screenshot(ruta)
        print(f"\n[EVIDENCIA] {resultado} -> {ruta}")
    except Exception as e:
        print(f"\n[EVIDENCIA] No se pudo capturar ({item.name}): {e}")
        return

    # Incrustar en el reporte HTML en base64 (autocontenido, sin enlaces externos)
    try:
        pytest_html = item.config.pluginmanager.getplugin("html")
        if pytest_html:
            with open(ruta, "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode("ascii")
            # 'extras' (plural) es el atributo vigente; se hace fallback a 'extra'
            extras = list(getattr(report, "extras", getattr(report, "extra", [])))
            extras.append(pytest_html.extras.image(b64, mime_type="image/png"))
            report.extras = extras
    except Exception:
        pass
