"""Configuración compartida de las pruebas de FINANCIA+.

Requisitos para ejecutar las pruebas:
  1. Una base PostgreSQL de pruebas con todas las migraciones aplicadas.
  2. La variable de entorno DATABASE_URL_PRUEBAS apuntando a esa base, con un
     rol que sea dueño de las tablas (ver .env.example).
  3. DATABASE_URL con el rol de la aplicación (financia_app), para las
     pruebas de permisos y de la API.
  4. Las dependencias de requirements.txt instaladas (pytest y psycopg).

Cada prueba recibe una conexión con una transacción abierta que, al terminar,
se deshace con ROLLBACK. Ninguna prueba deja datos en la base.
"""

import os
import pathlib

import psycopg
import pytest
from dotenv import load_dotenv
from psycopg.conninfo import conninfo_to_dict, make_conninfo

# Lee .env de la raíz del proyecto (DATABASE_URL_PRUEBAS) sin sobrescribir variables ya definidas.
load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")


@pytest.fixture
def con():
    """Conexión a la base de pruebas. Todo lo que haga la prueba se deshace."""
    url = os.environ.get("DATABASE_URL_PRUEBAS")
    if not url:
        pytest.skip("Defina DATABASE_URL_PRUEBAS para ejecutar las pruebas de base de datos.")

    conexion = psycopg.connect(url)  # sin autocommit: la primera consulta abre la transacción
    try:
        yield conexion
    finally:
        conexion.rollback()
        conexion.close()


def url_app_en_base_de_pruebas() -> str:
    """URL del rol de la aplicación (financia_app) apuntando a la base de PRUEBAS.

    Usuario y contraseña salen de DATABASE_URL; el nombre de la base, de
    DATABASE_URL_PRUEBAS. Así ninguna prueba toca la base principal.
    """
    url_app = os.environ.get("DATABASE_URL")
    url_pruebas = os.environ.get("DATABASE_URL_PRUEBAS")
    if not url_app or not url_pruebas:
        pytest.skip("Defina DATABASE_URL y DATABASE_URL_PRUEBAS en .env.")
    base_pruebas = conninfo_to_dict(url_pruebas)["dbname"]
    return make_conninfo(url_app, dbname=base_pruebas)


@pytest.fixture
def con_app():
    """Conexión a la base de PRUEBAS con el rol de la aplicación. Todo termina en ROLLBACK."""
    conexion = psycopg.connect(url_app_en_base_de_pruebas())
    try:
        yield conexion
    finally:
        conexion.rollback()
        conexion.close()
