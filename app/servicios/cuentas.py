"""Cuentas: crear, editar, archivar, reactivar y consultar con saldo (RF-02, RF-11).

Reglas que aplica
  RN-10  Nombre, tipo y saldo inicial (cero o positivo, máximo 2 decimales).
  RN-11  El saldo se calcula (CuentaRepositorio); nunca se guarda.
  RN-12  Solo se archiva con saldo calculado 0. Una cuenta archivada no se
         edita: primero se reactiva.
  RN-13  El saldo inicial solo cambia si la cuenta no tiene movimientos.
  RN-14  El saldo puede ser negativo: no se bloquea (CuentaConSaldo.saldo_negativo).
  RN-06  Una cuenta de otro usuario responde igual que una inexistente: NoEncontrado.

Las acciones que leen y luego escriben (editar, archivar, reactivar) bloquean
la fila de la cuenta al empezar la transacción (obtener_para_actualizar), para
que nadie registre un movimiento entre la revisión y el cambio (D-20).
"""

from decimal import Decimal

import psycopg
from psycopg import errors

from app.entidades.cuenta import Cuenta, CuentaConSaldo, TipoCuenta
from app.errores import ErrorNegocio, NoEncontrado
from app.repositorios.cuentas import CuentaRepositorio
from app.servicios.validaciones import validar_dinero

MENSAJE_NOMBRE_REPETIDO = "Ya tiene una cuenta activa con ese nombre."


class CuentaServicio:
    def __init__(self, con: psycopg.Connection):
        self.con = con
        self.cuentas = CuentaRepositorio(con)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def listar(self, id_usuario: int, incluir_archivadas: bool = False) -> list[CuentaConSaldo]:
        return self.cuentas.listar_con_saldo(id_usuario, incluir_archivadas)

    def obtener(self, id_usuario: int, id_cuenta: int) -> CuentaConSaldo:
        cuenta = self.cuentas.obtener_con_saldo(id_usuario, id_cuenta)
        if cuenta is None:
            raise NoEncontrado("No se encontró la cuenta.")
        return cuenta

    # ------------------------------------------------------------------
    # Acciones: cada una es UNA transacción
    # ------------------------------------------------------------------

    def crear(self, id_usuario: int, nombre: str, tipo: str, saldo_inicial: Decimal) -> CuentaConSaldo:
        nombre, tipo_cuenta = self._validar(nombre, tipo, saldo_inicial)
        try:
            with self.con.transaction():
                cuenta = self.cuentas.insertar(id_usuario, nombre, tipo_cuenta, saldo_inicial)
        except errors.UniqueViolation as error:
            self._traducir_nombre_repetido(error, MENSAJE_NOMBRE_REPETIDO)
        return self.obtener(id_usuario, cuenta.id_cuenta)

    def editar(self, id_usuario: int, id_cuenta: int, nombre: str, tipo: str,
               saldo_inicial: Decimal) -> CuentaConSaldo:
        nombre, tipo_cuenta = self._validar(nombre, tipo, saldo_inicial)
        try:
            with self.con.transaction():
                cuenta = self._bloquear(id_usuario, id_cuenta)
                if not cuenta.activa:
                    raise ErrorNegocio("La cuenta está archivada. Reactívela para editarla.")
                if saldo_inicial != cuenta.saldo_inicial and self.cuentas.tiene_movimientos(id_usuario, id_cuenta):
                    raise ErrorNegocio("El saldo inicial no se puede cambiar porque la cuenta ya tiene "
                                       "movimientos. Para corregir el saldo, registre un ajuste.")
                self.cuentas.actualizar(id_usuario, id_cuenta, nombre, tipo_cuenta, saldo_inicial)
        except errors.UniqueViolation as error:
            self._traducir_nombre_repetido(error, MENSAJE_NOMBRE_REPETIDO)
        return self.obtener(id_usuario, id_cuenta)

    def archivar(self, id_usuario: int, id_cuenta: int) -> CuentaConSaldo:
        """RN-12, CA-15: solo con saldo calculado 0. La fila queda bloqueada mientras se revisa."""
        with self.con.transaction():
            cuenta = self._bloquear(id_usuario, id_cuenta)
            if not cuenta.activa:
                raise ErrorNegocio("La cuenta ya está archivada.")
            saldo = self.cuentas.obtener_con_saldo(id_usuario, id_cuenta).saldo
            if saldo != 0:
                raise ErrorNegocio(f"La cuenta tiene un saldo de {saldo:.2f}. Para archivarla, el saldo "
                                   "debe ser 0: transfiéralo a otra cuenta o registre un ajuste.")
            self.cuentas.cambiar_activa(id_usuario, id_cuenta, False)
        return self.obtener(id_usuario, id_cuenta)

    def reactivar(self, id_usuario: int, id_cuenta: int) -> CuentaConSaldo:
        try:
            with self.con.transaction():
                cuenta = self._bloquear(id_usuario, id_cuenta)
                if cuenta.activa:
                    raise ErrorNegocio("La cuenta ya está activa.")
                self.cuentas.cambiar_activa(id_usuario, id_cuenta, True)
        except errors.UniqueViolation as error:
            self._traducir_nombre_repetido(error, "Ya tiene otra cuenta activa con ese nombre. Cámbiele "
                                                  "el nombre a esa cuenta antes de reactivar esta.")
        return self.obtener(id_usuario, id_cuenta)

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _bloquear(self, id_usuario: int, id_cuenta: int) -> Cuenta:
        cuenta = self.cuentas.obtener_para_actualizar(id_usuario, id_cuenta)
        if cuenta is None:
            raise NoEncontrado("No se encontró la cuenta.")
        return cuenta

    @staticmethod
    def _validar(nombre: str, tipo: str, saldo_inicial: Decimal) -> tuple[str, TipoCuenta]:
        """RN-10. Devuelve el nombre sin espacios alrededor y el tipo como TipoCuenta."""
        nombre = nombre.strip()
        if not nombre:
            raise ErrorNegocio("El nombre de la cuenta es obligatorio.")
        try:
            tipo_cuenta = TipoCuenta(tipo)
        except ValueError:
            opciones = ", ".join(TipoCuenta)
            raise ErrorNegocio(f"El tipo de cuenta no es válido. Opciones: {opciones}.") from None
        validar_dinero(saldo_inicial, "El saldo inicial", permitir_cero=True)
        return nombre, tipo_cuenta

    @staticmethod
    def _traducir_nombre_repetido(error: errors.UniqueViolation, mensaje: str):
        """Si el error es del índice de nombres de cuenta, lo cambia por un mensaje en español.

        La base es la que garantiza la unicidad (también entre dos peticiones
        simultáneas); el servicio solo traduce el error técnico. Cualquier otro
        error se vuelve a lanzar tal cual.
        """
        if error.diag.constraint_name == "uq_cuenta_nombre_activa":
            raise ErrorNegocio(mensaje) from error
        raise error
