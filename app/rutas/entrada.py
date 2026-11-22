"""Lectura del cuerpo JSON de una petición: comprueba su FORMA, no las reglas de negocio.

"¿Llegó el campo? ¿Es texto? ¿Es un número de dinero?" se revisa aquí.
"¿El saldo puede ser negativo?" o "¿el correo ya existe?" lo decide el servicio.
"""

from decimal import Decimal, InvalidOperation

from flask import request

from app.errores import ErrorNegocio


def leer_cuerpo() -> dict:
    """El cuerpo JSON como diccionario; si no es un objeto JSON, 400."""
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorNegocio("El cuerpo de la petición debe ser un objeto JSON.")
    return datos


def texto(datos: dict, campo: str) -> str:
    valor = datos.get(campo)
    if not isinstance(valor, str):
        raise ErrorNegocio(f"Falta el campo '{campo}' o no es texto.")
    return valor


def dinero(datos: dict, campo: str) -> Decimal:
    """Un valor de dinero llega como TEXTO ("150000.50") y se convierte a Decimal (RNF-08).

    Un número JSON (150000.5) se rechaza: el navegador lo maneja como float y
    podría perder centavos. Por eso la API exige texto.
    """
    valor = texto(datos, campo)
    try:
        numero = Decimal(valor.strip())
    except InvalidOperation:
        raise ErrorNegocio(f"El campo '{campo}' debe ser un número, por ejemplo \"150000.50\".") from None
    if not numero.is_finite():
        raise ErrorNegocio(f"El campo '{campo}' debe ser un número, por ejemplo \"150000.50\".")
    return numero


def leer_textos(*campos: str) -> dict[str, str]:
    """Devuelve {campo: texto} con los campos pedidos; si falta alguno o no es texto, 400."""
    datos = leer_cuerpo()
    return {campo: texto(datos, campo) for campo in campos}
