"""Pruebas de los permisos del rol de la aplicación (migración 0002, Tarea 4).

Qué verifican
    Que, conectados como financia_app (el rol con el que trabaja la
    aplicación), la base:
      * RECHAZA cualquier DELETE (D-15, RN-70: nada se borra físicamente).
      * RECHAZA un UPDATE sobre bolsillo_valor (D-09, RN-44: historial de
        solo inserción).
      * PERMITE leer, insertar y modificar lo que la aplicación necesita
        (prueba de control: si esta falla, las demás no significan nada).

Cómo están hechas
    El permiso se comprueba ANTES de buscar filas, así que un
    "DELETE ... WHERE false" ya es rechazado aunque no borraría nada.
    Cada prueba usa la conexión con_app (conftest.py) y termina en ROLLBACK.

Ejecutar:
    pytest tests/test_permisos_bd.py -v
"""

import uuid
from decimal import Decimal

import pytest
from psycopg import errors, sql

TABLAS = ("usuario", "cuenta", "categoria", "movimiento", "bolsillo", "bolsillo_valor")


def test_conectado_como_rol_de_la_aplicacion(con_app):
    """D-15: las pruebas de este archivo de verdad usan financia_app, que no es dueño de las tablas."""
    assert con_app.execute("SELECT current_user").fetchone()[0] == "financia_app"
    duenos = {fila[0] for fila in con_app.execute(
        "SELECT tableowner FROM pg_tables WHERE schemaname = 'public' AND tablename = ANY(%s)",
        (list(TABLAS),),
    )}
    assert "financia_app" not in duenos


@pytest.mark.parametrize("tabla", TABLAS)
def test_delete_rechazado(con_app, tabla):
    """D-15, RN-70: financia_app no tiene permiso DELETE sobre ninguna tabla."""
    consulta = sql.SQL("DELETE FROM {} WHERE false").format(sql.Identifier(tabla))
    with pytest.raises(errors.InsufficientPrivilege):
        con_app.execute(consulta)


def test_update_sobre_bolsillo_valor_rechazado(con_app):
    """D-09, RN-44: un valor registrado en el historial no se modifica."""
    with pytest.raises(errors.InsufficientPrivilege):
        con_app.execute("UPDATE bolsillo_valor SET valor = 0 WHERE false")


@pytest.mark.parametrize("tabla", TABLAS)
def test_truncate_rechazado(con_app, tabla):
    """D-15: TRUNCATE también borraría datos; tampoco está permitido."""
    consulta = sql.SQL("TRUNCATE {}").format(sql.Identifier(tabla))
    with pytest.raises(errors.InsufficientPrivilege):
        con_app.execute(consulta)


def test_control_leer_insertar_y_modificar_permitido(con_app):
    """D-15 (control): la aplicación sí puede crear y actualizar datos, e insertar en el historial.

    También demuestra que las columnas IDENTITY funcionan sin permisos extra sobre secuencias.
    """
    correo = f"permisos.{uuid.uuid4().hex[:10]}@prueba.example"
    id_usuario = con_app.execute(
        "INSERT INTO usuario (nombre, correo, clave_hash) VALUES (%s, %s, %s) RETURNING id_usuario",
        ("Permisos", correo, "hash-de-prueba"),
    ).fetchone()[0]
    con_app.execute("UPDATE usuario SET nombre = %s WHERE id_usuario = %s", ("Permisos 2", id_usuario))

    id_bolsillo = con_app.execute(
        "INSERT INTO bolsillo (id_usuario, nombre) VALUES (%s, %s) RETURNING id_bolsillo",
        (id_usuario, "Viaje"),
    ).fetchone()[0]
    con_app.execute(
        "INSERT INTO bolsillo_valor (id_usuario, id_bolsillo, valor) VALUES (%s, %s, %s)",
        (id_usuario, id_bolsillo, Decimal("1000.00")),
    )

    fila = con_app.execute(
        """
        SELECT u.nombre, v.valor
          FROM usuario u
          JOIN bolsillo_valor v ON v.id_usuario = u.id_usuario
         WHERE u.id_usuario = %s
        """,
        (id_usuario,),
    ).fetchone()
    assert fila == ("Permisos 2", Decimal("1000.00"))


def test_sin_acceso_a_la_tabla_de_control_de_migraciones(con_app):
    """D-19: migracion_aplicada es infraestructura; la aplicación no la lee ni la cambia."""
    with pytest.raises(errors.InsufficientPrivilege):
        con_app.execute("SELECT count(*) FROM migracion_aplicada")
