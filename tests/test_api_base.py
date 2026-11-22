"""Pruebas del esqueleto de la API (Tarea 6).

Qué verifican
    * GET /api/salud responde {"bd": "ok"} con la base de pruebas, y 503 sin base.
    * La protección CSRF (ARQUITECTURA.md, sección 6): una petición que
      modifica datos sin JSON o sin el encabezado X-Requested-With: financia
      es rechazada; con los dos, pasa.
    * ErrorNegocio y NoEncontrado se convierten en JSON con su código HTTP.

Cómo están hechas
    Usan el cliente de pruebas de Flask: simula peticiones HTTP sin levantar
    un servidor. La aplicación se crea con la fábrica create_app() y una
    configuración que apunta a la base de PRUEBAS con el rol financia_app.
    Como todavía no hay rutas que modifiquen datos, se agregan rutas de
    prueba solo dentro de estas pruebas.
"""

import os

import pytest

from app import create_app
from app.config import Config
from app.errores import ErrorNegocio, NoEncontrado
from conftest import url_app_en_base_de_pruebas

ENCABEZADO_OK = {"X-Requested-With": "financia"}


def crear_app_de_prueba(database_url: str):
    app = create_app(Config(secret_key=os.environ.get("SECRET_KEY", "clave-de-prueba"),
                            database_url=database_url))
    app.config["TESTING"] = True

    # Rutas solo para estas pruebas.
    @app.post("/api/prueba/eco")
    def eco():
        return {"recibido": True}

    @app.get("/api/prueba/error-negocio")
    def error_negocio():
        raise ErrorNegocio("La cuenta tiene saldo; no se puede archivar.")

    @app.get("/api/prueba/no-encontrado")
    def no_encontrado():
        raise NoEncontrado()

    return app


@pytest.fixture
def cliente():
    return crear_app_de_prueba(url_app_en_base_de_pruebas()).test_client()


# ---------------------------------------------------------------------
# GET /api/salud
# ---------------------------------------------------------------------

def test_salud_con_base_disponible(cliente):
    """Tarea 6: /api/salud responde {"bd": "ok"} cuando hay conexión."""
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"bd": "ok"}


def test_salud_sin_base_responde_503_sin_detalles_tecnicos():
    """ARQUITECTURA 6: sin base, 503 y ningún detalle técnico en la respuesta."""
    app = crear_app_de_prueba("postgresql://nadie:nada@127.0.0.1:1/no_existe")
    respuesta = app.test_client().get("/api/salud")
    assert respuesta.status_code == 503
    assert respuesta.get_json() == {"bd": "error"}


# ---------------------------------------------------------------------
# CSRF (ARQUITECTURA.md, sección 6)
# ---------------------------------------------------------------------

def test_csrf_peticion_correcta_pasa(cliente):
    """Control: JSON + encabezado propio llega a la ruta."""
    respuesta = cliente.post("/api/prueba/eco", json={}, headers=ENCABEZADO_OK)
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"recibido": True}


def test_csrf_rechaza_formulario(cliente):
    """Un formulario HTML de otro sitio envía form-data, no JSON: 415."""
    respuesta = cliente.post("/api/prueba/eco", data={"monto": "1000"}, headers=ENCABEZADO_OK)
    assert respuesta.status_code == 415
    assert "error" in respuesta.get_json()


def test_csrf_rechaza_json_sin_encabezado(cliente):
    """JSON sin X-Requested-With: financia: 403."""
    respuesta = cliente.post("/api/prueba/eco", json={})
    assert respuesta.status_code == 403
    assert respuesta.get_json() == {"error": "Petición rechazada por seguridad."}


def test_csrf_rechaza_encabezado_con_otro_valor(cliente):
    respuesta = cliente.post("/api/prueba/eco", json={}, headers={"X-Requested-With": "XMLHttpRequest"})
    assert respuesta.status_code == 403


@pytest.mark.parametrize("metodo", ["put", "patch", "delete"])
def test_csrf_aplica_a_todos_los_metodos_que_modifican(cliente, metodo):
    respuesta = getattr(cliente, metodo)("/api/prueba/eco", json={})
    assert respuesta.status_code == 403


def test_csrf_no_afecta_las_lecturas(cliente):
    """GET no modifica datos: no necesita el encabezado."""
    assert cliente.get("/api/salud").status_code == 200


# ---------------------------------------------------------------------
# Errores convertidos a JSON
# ---------------------------------------------------------------------

def test_error_negocio_responde_400_con_su_mensaje(cliente):
    respuesta = cliente.get("/api/prueba/error-negocio")
    assert respuesta.status_code == 400
    assert respuesta.get_json() == {"error": "La cuenta tiene saldo; no se puede archivar."}


def test_no_encontrado_responde_404(cliente):
    """RN-05: inexistente o ajeno, la misma respuesta 404."""
    respuesta = cliente.get("/api/prueba/no-encontrado")
    assert respuesta.status_code == 404
    assert respuesta.get_json() == {"error": "No se encontró el recurso."}


def test_ruta_inexistente_responde_json(cliente):
    """La API nunca responde HTML, tampoco en sus errores."""
    respuesta = cliente.get("/api/no-existe")
    assert respuesta.status_code == 404
    assert respuesta.is_json
