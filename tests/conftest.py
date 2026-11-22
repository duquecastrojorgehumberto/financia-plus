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
import uuid
from datetime import date
from decimal import Decimal

import psycopg
import pytest
from dotenv import load_dotenv
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from psycopg.rows import dict_row

from app import create_app
from app.bd import BaseDatos
from app.config import Config
from app.servicios.autenticacion import AutenticacionServicio
from app.servicios.categorias import CategoriaServicio
from app.servicios.cuentas import CuentaServicio
from app.servicios.movimientos import DatosMovimiento

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


# ---------------------------------------------------------------------
# Para probar servicios y rutas, que sí hacen COMMIT.
#
# Se usa UNA conexión que ya tiene una transacción abierta: dentro de ella,
# el "with con.transaction():" de cada servicio se convierte en un SAVEPOINT,
# y al final de la prueba se deshace todo con ROLLBACK. Así las pruebas no
# dejan datos aunque el código de la aplicación confirme sus transacciones.
# ---------------------------------------------------------------------

class BaseDatosDePrueba(BaseDatos):
    """Entrega siempre la misma conexión y no la cierra: la prueba hace ROLLBACK al final.

    Es una subclase de BaseDatos que redefine conectar() y liberar(): la
    aplicación la usa sin saber que es distinta (polimorfismo).
    """

    def __init__(self, con: psycopg.Connection):
        self._con = con

    def conectar(self) -> psycopg.Connection:
        return self._con

    def liberar(self, con: psycopg.Connection) -> None:
        pass


@pytest.fixture
def con_tx():
    """Conexión como financia_app a la base de pruebas, con filas como diccionarios
    y una transacción ya abierta (lo que hagan los servicios serán SAVEPOINT)."""
    conexion = psycopg.connect(url_app_en_base_de_pruebas(), row_factory=dict_row)
    conexion.execute("SELECT 1")   # abre la transacción externa
    try:
        yield conexion
    finally:
        conexion.rollback()
        conexion.close()


@pytest.fixture
def cliente_api(con_tx):
    """Cliente HTTP de Flask sobre la aplicación real, usando la conexión con_tx."""
    config = Config(secret_key=os.environ.get("SECRET_KEY", "clave-de-prueba"),
                    database_url="no-se-usa")
    app = create_app(config, bd=BaseDatosDePrueba(con_tx))
    app.config["TESTING"] = True
    return app.test_client()


# ---------------------------------------------------------------------
# Para probar bloqueos entre DOS conexiones: los datos deben estar confirmados
# (una transacción abierta no deja ver sus filas a otra conexión).
# ---------------------------------------------------------------------

@pytest.fixture
def cuenta_confirmada():
    """Usuario, categoría y cuenta CONFIRMADOS en la base de pruebas (los ve otra conexión).

    Se crean y se borran con el rol dueño (DATABASE_URL_PRUEBAS), que sí puede borrar.
    """
    admin = psycopg.connect(os.environ["DATABASE_URL_PRUEBAS"], autocommit=True)
    admin.execute("SET lock_timeout = '5s'")   # la limpieza nunca se queda esperando para siempre
    correo = f"bloqueo.{uuid.uuid4().hex[:10]}@prueba.example"
    u = admin.execute("INSERT INTO usuario (nombre, correo, clave_hash) VALUES ('Bloqueo', %s, 'h') "
                      "RETURNING id_usuario", (correo,)).fetchone()[0]
    cat = admin.execute("INSERT INTO categoria (id_usuario, nombre, tipo) VALUES (%s, 'Salario', 'INGRESO') "
                        "RETURNING id_categoria", (u,)).fetchone()[0]
    c = admin.execute("INSERT INTO cuenta (id_usuario, nombre) VALUES (%s, 'Nequi') "
                      "RETURNING id_cuenta", (u,)).fetchone()[0]
    try:
        yield u, cat, c
    finally:
        admin.execute("DELETE FROM movimiento WHERE id_usuario = %s", (u,))
        admin.execute("DELETE FROM cuenta WHERE id_usuario = %s", (u,))
        admin.execute("DELETE FROM categoria WHERE id_usuario = %s", (u,))
        admin.execute("DELETE FROM usuario WHERE id_usuario = %s", (u,))
        admin.close()


# ---------------------------------------------------------------------
# Un "mundo" de datos para probar movimientos y transferencias.
# ---------------------------------------------------------------------

FECHA = date(2026, 11, 1)


class Mundo:
    """Un usuario con dos cuentas activas y sus categorías por defecto."""

    def __init__(self, con):
        self.con = con
        correo = f"mov.{uuid.uuid4().hex[:10]}@prueba.example"
        self.u = AutenticacionServicio(con).registrar("Ana", correo, "clave-segura-123").id_usuario
        cuentas = CuentaServicio(con)
        self.nequi = cuentas.crear(self.u, "Nequi", "BILLETERA_DIGITAL", Decimal("100000")).cuenta.id_cuenta
        self.nubank = cuentas.crear(self.u, "Nubank", "AHORROS", Decimal("0")).cuenta.id_cuenta
        arbol = CategoriaServicio(con).listar_arbol(self.u)
        raices = {r.raiz.nombre: r for r in arbol}
        self.salario = raices["Salario"].raiz.id_categoria
        self.alimentacion = raices["Alimentación"].raiz.id_categoria
        self.mercado = next(s.id_categoria for s in raices["Alimentación"].subcategorias if s.nombre == "Mercado")
        self.transporte = raices["Transporte"].raiz.id_categoria
        self.impuestos = raices["Impuestos y comisiones"].raiz.id_categoria

    def datos(self, monto="1000", *, cuenta=None, categoria=None, fecha=FECHA, descripcion=None):
        return DatosMovimiento(id_cuenta=cuenta or self.nequi, id_categoria=categoria or self.alimentacion,
                               monto=Decimal(monto), fecha=fecha, descripcion=descripcion)

    def saldo(self, cuenta=None) -> Decimal:
        return CuentaServicio(self.con).obtener(self.u, cuenta or self.nequi).saldo

    def transferencia(self, monto="200000", estado="VIGENTE") -> int:
        """Transferencia Nequi -> Nubank, con SQL directo (Tarea 11 pendiente)."""
        return self.con.execute(
            "INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_cuenta_destino, monto, fecha, estado) "
            "VALUES (%s, 'TRANSFERENCIA', %s, %s, %s, %s, %s) RETURNING id_movimiento",
            (self.u, self.nequi, self.nubank, Decimal(monto), FECHA, estado),
        ).fetchone()["id_movimiento"]

    def cargo(self, id_transferencia, monto="800", estado="VIGENTE") -> int:
        return self.con.execute(
            "INSERT INTO movimiento (id_usuario, tipo, id_cuenta, id_categoria, id_transferencia, monto, fecha, estado) "
            "VALUES (%s, 'EGRESO', %s, %s, %s, %s, %s, %s) RETURNING id_movimiento",
            (self.u, self.nequi, self.impuestos, id_transferencia, Decimal(monto), FECHA, estado),
        ).fetchone()["id_movimiento"]

    def ajuste(self, monto="500") -> int:
        return self.con.execute(
            "INSERT INTO movimiento (id_usuario, tipo, id_cuenta, monto, fecha, descripcion) "
            "VALUES (%s, 'AJUSTE_DISMINUCION', %s, %s, %s, 'Cuadre con el banco') RETURNING id_movimiento",
            (self.u, self.nequi, Decimal(monto), FECHA),
        ).fetchone()["id_movimiento"]
