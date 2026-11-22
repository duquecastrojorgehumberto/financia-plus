"""Errores de la aplicación y su conversión a respuestas JSON.

Los servicios lanzan estas excepciones cuando una regla de negocio no se
cumple; no saben nada de HTTP. Aquí se registra, una sola vez, cómo se
convierte cada una en una respuesta JSON:

    raise ErrorNegocio("La cuenta tiene saldo; no se puede archivar.")
        ->  400  {"error": "La cuenta tiene saldo; no se puede archivar."}

    raise NoEncontrado()
        ->  404  {"error": "No se encontró el recurso."}

    raise NoAutenticado()
        ->  401  {"error": "Debe iniciar sesión."}

Al usuario nunca se le muestra el error técnico (de Python o de PostgreSQL):
lo inesperado responde 500 con un mensaje genérico y el detalle queda en el
registro del servidor.
"""

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


class ErrorNegocio(Exception):
    """Una regla de negocio no se cumplió. El mensaje es para el usuario, en español."""

    codigo_http = 400

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje


class NoEncontrado(ErrorNegocio):
    """El recurso no existe o es de otro usuario. Los dos casos responden igual (RN-05).

    Hereda de ErrorNegocio y solo cambia el código HTTP y el mensaje por
    defecto; por eso el mismo manejador sirve para las dos clases.
    """

    codigo_http = 404

    def __init__(self, mensaje: str = "No se encontró el recurso."):
        super().__init__(mensaje)


class NoAutenticado(ErrorNegocio):
    """No hay sesión iniciada, o el correo o la contraseña no son correctos (401)."""

    codigo_http = 401

    def __init__(self, mensaje: str = "Debe iniciar sesión."):
        super().__init__(mensaje)


def registrar_manejadores(app: Flask) -> None:
    """Le dice a Flask cómo responder (en JSON) a cada tipo de error."""

    @app.errorhandler(ErrorNegocio)
    def _error_negocio(error: ErrorNegocio):
        # error.codigo_http es 400, 401 o 404 según la clase real del objeto (polimorfismo).
        return jsonify(error=error.mensaje), error.codigo_http

    @app.errorhandler(HTTPException)
    def _error_http(error: HTTPException):
        # Errores que produce Flask mismo: ruta inexistente (404), método no permitido (405)...
        mensajes = {
            404: "No se encontró el recurso.",
            405: "Método no permitido.",
        }
        return jsonify(error=mensajes.get(error.code, error.name)), error.code

    @app.errorhandler(Exception)
    def _error_inesperado(error: Exception):
        app.logger.exception("Error inesperado")
        return jsonify(error="Ocurrió un error inesperado. Intente de nuevo."), 500
