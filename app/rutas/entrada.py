"""Lectura de los datos de una petición: comprueba su FORMA, no las reglas de negocio.

"¿Llegó el campo? ¿Es texto? ¿Es un número de dinero? ¿Es una fecha?" se revisa aquí.
"¿El saldo puede ser negativo?" o "¿el correo ya existe?" lo decide el servicio.

Hay funciones para el cuerpo JSON (texto, dinero, entero, fecha...) y para los
parámetros de la URL (?desde=2026-11-01&id_cuenta=3).
"""

from datetime import date
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


def entero_opcional(datos: dict, campo: str) -> int | None:
    """Un identificador opcional: un número entero JSON, o null / ausente."""
    valor = datos.get(campo)
    if valor is None:
        return None
    # bool es un tipo de int en Python (True == 1): se descarta a propósito.
    if not isinstance(valor, int) or isinstance(valor, bool):
        raise ErrorNegocio(f"El campo '{campo}' debe ser un número entero.")
    return valor


def entero(datos: dict, campo: str) -> int:
    """Un identificador obligatorio."""
    valor = entero_opcional(datos, campo)
    if valor is None:
        raise ErrorNegocio(f"Falta el campo '{campo}'.")
    return valor


def texto_opcional(datos: dict, campo: str) -> str | None:
    valor = datos.get(campo)
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise ErrorNegocio(f"El campo '{campo}' debe ser texto.")
    return valor


def _convertir_fecha(valor: str, campo: str) -> date:
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ErrorNegocio(f"El campo '{campo}' debe ser una fecha con el formato AAAA-MM-DD.") from None


def fecha(datos: dict, campo: str) -> date:
    """Una fecha obligatoria, como texto "2026-11-01"."""
    return _convertir_fecha(texto(datos, campo), campo)


def fecha_opcional(datos: dict, campo: str) -> date | None:
    """Una fecha opcional: texto "2026-11-01", o null / ausente."""
    if datos.get(campo) is None:
        return None
    return fecha(datos, campo)


def parametro_fecha(nombre: str) -> date | None:
    """?desde=2026-11-01 en la URL. Ausente o vacío: None."""
    valor = request.args.get(nombre, "")
    return _convertir_fecha(valor, nombre) if valor else None


def parametro_entero(nombre: str) -> int | None:
    """?id_cuenta=3 en la URL. Ausente o vacío: None."""
    valor = request.args.get(nombre, "")
    if not valor:
        return None
    if not valor.isdigit():
        raise ErrorNegocio(f"El parámetro '{nombre}' debe ser un número entero.")
    return int(valor)


def parametro_texto(nombre: str) -> str | None:
    return request.args.get(nombre) or None


def lista_de_objetos(datos: dict, campo: str) -> list[dict]:
    """Una lista opcional de objetos JSON, por ejemplo los cargos: [{...}, {...}]. Ausente: []."""
    valor = datos.get(campo)
    if valor is None:
        return []
    if not isinstance(valor, list) or not all(isinstance(v, dict) for v in valor):
        raise ErrorNegocio(f"El campo '{campo}' debe ser una lista de objetos.")
    return valor


def solo_campos(datos: dict, *permitidos: str) -> None:
    """Rechaza campos que la ruta no acepta, en lugar de ignorarlos en silencio."""
    sobrantes = sorted(set(datos) - set(permitidos))
    if sobrantes:
        raise ErrorNegocio(f"Campos no permitidos: {', '.join(sobrantes)}.")


def dinero_opcional(datos: dict, campo: str) -> Decimal | None:
    """Un valor de dinero opcional: texto "1000000", o null / ausente."""
    if datos.get(campo) is None:
        return None
    return dinero(datos, campo)


def leer_textos(*campos: str) -> dict[str, str]:
    """Devuelve {campo: texto} con los campos pedidos; si falta alguno o no es texto, 400."""
    datos = leer_cuerpo()
    return {campo: texto(datos, campo) for campo in campos}
