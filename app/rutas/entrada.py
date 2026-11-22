"""Lectura del cuerpo JSON de una petición: comprueba su FORMA, no las reglas de negocio.

"¿Llegó el campo? ¿Es texto?" se revisa aquí. "¿El correo ya existe?" lo
decide el servicio.
"""

from flask import request

from app.errores import ErrorNegocio


def leer_textos(*campos: str) -> dict[str, str]:
    """Devuelve {campo: texto} con los campos pedidos; si falta alguno o no es texto, 400."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorNegocio("El cuerpo de la petición debe ser un objeto JSON.")
    resultado = {}
    for campo in campos:
        valor = datos.get(campo)
        if not isinstance(valor, str):
            raise ErrorNegocio(f"Falta el campo '{campo}' o no es texto.")
        resultado[campo] = valor
    return resultado
