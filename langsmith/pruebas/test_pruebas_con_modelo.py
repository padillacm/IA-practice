"""Pruebas del notebook 10: la caché de peticiones en la CI.

Estas prueban un mecanismo del SDK del que depende una recomendación fuerte del curso
—«cachea las llamadas al modelo y tendrás pruebas deterministas»—. Si deja de funcionar,
el consejo pasa a ser malo y hay que enterarse aquí.
"""

from __future__ import annotations

import inspect
import pathlib
import shutil

import requests

from utils import curso


def _clasificar(url: str, **kwargs) -> dict:
    return requests.post(url, json={"mensaje": "cobro duplicado"}, **kwargs).json()


def test_el_plugin_de_pytest_esta_registrado():
    import importlib.metadata as metadata

    registrados = [p.value for d in metadata.distributions() for p in d.entry_points
                   if p.group == "pytest11"]
    assert any("langsmith" in v for v in registrados)


def test_la_cache_repite_con_el_proveedor_apagado(tmp_path):
    """La demostración central del notebook 10.

    Se graba una llamada, se apaga el servidor, y la misma llamada devuelve lo mismo.
    """
    cassette = tmp_path / "clasifica.yaml"

    with curso.servidor_de_modelo({"categoria": "facturacion"}) as proveedor:
        with curso.cache_de_pruebas(cassette):
            primera = _clasificar(proveedor.url)
        assert proveedor.llamadas == 1
        assert cassette.exists()

        proveedor.apagar()

        with curso.cache_de_pruebas(cassette):
            segunda = _clasificar(proveedor.url)

    assert primera == segunda == {"categoria": "facturacion"}
    assert proveedor.llamadas == 1        # la segunda no llegó al proveedor


def test_la_cache_es_ciega_a_los_cambios_del_proveedor(tmp_path):
    """La contrapartida del método, dicha en el notebook y fijada aquí.

    Protege de las regresiones de TU código; no ve que el proveedor cambió el modelo
    bajo el mismo nombre. Por eso hace falta el trabajo semanal que regenera.
    """
    cassette = tmp_path / "clasifica.yaml"

    with curso.servidor_de_modelo({"categoria": "facturacion"}) as proveedor:
        with curso.cache_de_pruebas(cassette):
            _clasificar(proveedor.url)

        proveedor.cambiar_respuesta({"categoria": "otros"})
        assert _clasificar(proveedor.url) == {"categoria": "otros"}      # la realidad

        with curso.cache_de_pruebas(cassette):
            assert _clasificar(proveedor.url) == {"categoria": "facturacion"}   # la caché


def test_la_grabacion_no_guarda_las_cabeceras_de_la_peticion(tmp_path):
    """Si esto cambiara, subir las grabaciones al repositorio publicaría la clave.

    Es la comprobación más importante de este fichero: no vigila una afirmación del
    material, vigila que seguir el consejo del curso no filtre un secreto.
    """
    cassette = tmp_path / "con_clave.yaml"
    CLAVE = "sk-proj-ESTO-ES-MI-CLAVE"

    with curso.servidor_de_modelo() as proveedor:
        with curso.cache_de_pruebas(cassette):
            _clasificar(proveedor.url, headers={"Authorization": f"Bearer {CLAVE}",
                                                "X-Cliente": "acme-s-a"})

    texto = cassette.read_text(encoding="utf-8")
    assert CLAVE not in texto
    assert "acme-s-a" not in texto


def test_test_tracking_false_desactiva_tambien_la_cache():
    """El hallazgo del notebook 10, leído del código del SDK.

    `if disable_tracking: return func(...)` — con el seguimiento apagado, el decorador
    llama a la función directamente y el contexto de la caché no se ejecuta. O sea que
    por ese camino «no subir» y «cachear» son incompatibles, sin error ni aviso.
    """
    from langsmith.testing import _internal

    fuente = inspect.getsource(_internal.test)
    assert "disable_tracking = ls_utils.test_tracking_is_disabled()" in fuente
    # El retorno temprano que se salta todo lo que envuelve, incluida la caché.
    assert "if disable_tracking:" in fuente
    assert fuente.count("return func(*test_args, **test_kwargs)") >= 1


def test_la_cache_suelta_funciona_con_el_seguimiento_apagado(tmp_path, monkeypatch):
    """La salida a la trampa anterior: `with_optional_cache` como contexto suelto."""
    monkeypatch.setenv("LANGSMITH_TEST_TRACKING", "false")
    cassette = tmp_path / "suelta.yaml"

    with curso.servidor_de_modelo() as proveedor:
        with curso.cache_de_pruebas(cassette):
            _clasificar(proveedor.url)
        proveedor.apagar()
        with curso.cache_de_pruebas(cassette):
            assert _clasificar(proveedor.url) == {"categoria": "facturacion"}

    assert cassette.exists()


def test_el_servidor_de_mentira_cuenta_y_retrasa():
    """El ayudante del curso, que es lo que permite medir el ahorro de verdad."""
    import time

    with curso.servidor_de_modelo({"x": 1}, latencia=0.02) as proveedor:
        inicio = time.time()
        for _ in range(3):
            _clasificar(proveedor.url)
        transcurrido = time.time() - inicio

    assert proveedor.llamadas == 3
    assert transcurrido >= 0.05      # la latencia se aplica de verdad
