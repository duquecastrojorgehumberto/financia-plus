"""Conexión con PostgreSQL y manejo de transacciones.

Cómo se usa en la aplicación
  * Cada petición HTTP usa UNA conexión. obtener_conexion() la abre la primera
    vez que se pide y la guarda en flask.g (un espacio que dura lo que dura la
    petición). Al terminar la petición, cerrar_conexion() la cierra siempre,
    aunque haya habido un error.
  * La conexión está en modo autocommit: cada sentencia suelta se confirma
    sola. Cuando una acción necesita VARIAS sentencias juntas (por ejemplo, una
    transferencia y sus cargos, ARQUITECTURA.md 5.2), el servicio las agrupa así:

        with self.con.transaction():      # BEGIN
            repo.insertar(...)
            repo.insertar(...)
                                          # COMMIT al salir del bloque sin errores
                                          # ROLLBACK si salta cualquier excepción

    Regla del proyecto: una acción del usuario = un método de servicio = una transacción.
  * Las filas llegan como diccionarios ({"id_cuenta": 1, "nombre": ...}), lo
    que facilita convertirlas en entidades: Cuenta(**fila).
"""

import psycopg
from flask import current_app, g
from psycopg.rows import dict_row


class BaseDatos:
    """Sabe cómo conectarse a la base. La aplicación crea un solo objeto de esta clase."""

    def __init__(self, url: str):
        self._url = url   # el guion bajo indica "uso interno": nadie de afuera debería leerla

    def conectar(self) -> psycopg.Connection:
        """Abre una conexión nueva, en autocommit y con filas como diccionarios."""
        return psycopg.connect(self._url, autocommit=True, row_factory=dict_row, connect_timeout=5)

    def esta_disponible(self, con: psycopg.Connection) -> bool:
        """True si la base responde a una consulta mínima."""
        return con.execute("SELECT 1 AS uno").fetchone()["uno"] == 1

    def liberar(self, con: psycopg.Connection) -> None:
        """Devuelve la conexión al terminar la petición: aquí, la cierra.

        Las pruebas usan una subclase que redefine conectar() y liberar() para
        trabajar siempre con la misma conexión y deshacer todo al final
        (tests/test_autenticacion.py). Es el mismo método con otro comportamiento.
        """
        con.close()


def obtener_conexion() -> psycopg.Connection:
    """Devuelve la conexión de la petición actual; la abre si todavía no existe."""
    if "con" not in g:
        bd: BaseDatos = current_app.extensions["financia_bd"]
        g.con = bd.conectar()
    return g.con


def cerrar_conexion(_error=None) -> None:
    """Cierra la conexión de la petición, si se abrió. Flask la llama al final de cada petición."""
    con = g.pop("con", None)
    if con is not None:
        current_app.extensions["financia_bd"].liberar(con)
