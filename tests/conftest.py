"""Configuración compartida de las pruebas de FINANCIA+.

ESTADO: escrito y revisado a mano. TODAVÍA NO SE HA EJECUTADO.

Requisitos para ejecutar las pruebas (lo hará el equipo más adelante):
  1. Una base PostgreSQL de pruebas con la migración 0001 ya aplicada.
  2. La variable de entorno DATABASE_URL_PRUEBAS apuntando a esa base, con un
     rol que sea dueño de las tablas (ver .env.example).
  3. Las dependencias de requirements.txt instaladas (pytest y psycopg).

Cada prueba recibe una conexión con una transacción abierta que, al terminar,
se deshace con ROLLBACK. Ninguna prueba deja datos en la base.
"""

import os
import pathlib

import psycopg
import pytest
from dotenv import load_dotenv

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
