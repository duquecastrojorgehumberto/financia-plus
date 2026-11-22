"""Validaciones de dinero que comparten varios servicios (RN-10, RN-30, RNF-08).

Se revisan aquí, con un mensaje claro, para que el usuario no reciba el error
técnico de PostgreSQL y para que la base no redondee en silencio: numeric(14,2)
guardaría 10.005 como 10.01 sin avisar.
"""

from decimal import Decimal

from app.errores import ErrorNegocio

DINERO_MAXIMO = Decimal("999999999999.99")   # lo máximo que cabe en numeric(14,2)


def validar_dinero(valor: Decimal, nombre: str, *, permitir_cero: bool) -> None:
    """nombre va al inicio del mensaje, por ejemplo "El saldo inicial" o "El monto"."""
    if permitir_cero and valor < 0:
        raise ErrorNegocio(f"{nombre} no puede ser negativo.")
    if not permitir_cero and valor <= 0:
        raise ErrorNegocio(f"{nombre} debe ser mayor que cero.")
    if valor > DINERO_MAXIMO:
        raise ErrorNegocio(f"{nombre} es demasiado grande.")
    if valor.as_tuple().exponent < -2:
        raise ErrorNegocio(f"{nombre} admite máximo 2 decimales.")
