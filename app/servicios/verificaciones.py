"""Comprobaciones que comparten MovimientoServicio y TransferenciaServicio.

Antes de usar una cuenta o una categoría en un movimiento hay que revisar lo
mismo en los dos servicios: que exista y sea del usuario (RN-06), que la cuenta
esté activa (RN-12) y que la categoría esté activa y sea del tipo correcto
(RN-25, RN-31). En lugar de copiar ese código, los dos servicios CONTIENEN un
objeto VerificadorDeUso y le piden la revisión (composición).

Las lecturas usan FOR SHARE: mientras dure la transacción, nadie puede archivar
la cuenta ni desactivar la categoría (ver CuentaRepositorio.obtener_para_usar).
"""

import psycopg

from app.entidades.categoria import Categoria
from app.entidades.cuenta import Cuenta
from app.entidades.movimiento import TipoMovimiento
from app.errores import ErrorNegocio, NoEncontrado
from app.repositorios.categorias import CategoriaRepositorio
from app.repositorios.cuentas import CuentaRepositorio

MENSAJE_CUENTA_ARCHIVADA = "La cuenta está archivada: no admite movimientos."


class VerificadorDeUso:
    def __init__(self, con: psycopg.Connection):
        self.cuentas = CuentaRepositorio(con)
        self.categorias = CategoriaRepositorio(con)

    def cuenta_activa(self, id_usuario: int, id_cuenta: int,
                      mensaje_archivada: str = MENSAJE_CUENTA_ARCHIVADA) -> Cuenta:
        cuenta = self.cuentas.obtener_para_usar(id_usuario, id_cuenta)
        if cuenta is None:
            raise NoEncontrado("No se encontró la cuenta.")
        if not cuenta.activa:
            raise ErrorNegocio(mensaje_archivada)
        return cuenta

    def categoria_utilizable(self, id_usuario: int, id_categoria: int, tipo: TipoMovimiento) -> Categoria:
        categoria = self.categorias.obtener_para_usar(id_usuario, id_categoria)
        if categoria is None:
            raise NoEncontrado("No se encontró la categoría.")
        if categoria.tipo != tipo:
            raise ErrorNegocio(f"La categoría '{categoria.nombre}' es de tipo {categoria.tipo}; "
                               f"un movimiento de tipo {tipo} necesita una categoría de tipo {tipo}.")
        if not categoria.activa:
            raise ErrorNegocio(f"La categoría '{categoria.nombre}' está desactivada.")
        return categoria
