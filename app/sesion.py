"""Sesión del usuario y el decorador @requiere_sesion.

La sesión es la cookie firmada de Flask (ARQUITECTURA.md, sección 6). Lo único
que se guarda en ella es id_usuario. Como está firmada con SECRET_KEY, el
navegador puede leerla pero no cambiarla sin que el servidor lo note.

RN-05: el id_usuario de toda operación sale de aquí, nunca del JSON ni de la URL.
"""

import functools

from flask import session

from app.entidades.usuario import Usuario
from app.errores import NoAutenticado


def iniciar(usuario: Usuario) -> None:
    """Guarda al usuario en la sesión. Antes borra lo que hubiera de una sesión anterior."""
    session.clear()
    session["id_usuario"] = usuario.id_usuario


def cerrar() -> None:
    session.clear()


def requiere_sesion(vista):
    """Decorador: la ruta solo se ejecuta si hay sesión, y recibe el id_usuario.

    Uso:
        @cuentas_bp.get("/cuentas")
        @requiere_sesion
        def listar(id_usuario):
            ...

    Un decorador es una función que "envuelve" a otra: hace algo antes (aquí,
    revisar la sesión) y luego llama a la original. Si no hay sesión, lanza
    NoAutenticado y la respuesta es 401 en JSON.
    """

    @functools.wraps(vista)   # conserva el nombre de la función original (Flask lo necesita)
    def envoltura(*args, **kwargs):
        id_usuario = session.get("id_usuario")
        if id_usuario is None:
            raise NoAutenticado()
        return vista(*args, id_usuario=id_usuario, **kwargs)

    return envoltura
