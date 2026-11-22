"""Transferencias entre cuentas propias, con sus cargos (RF-06, RF-07).

Reglas que aplica
  RN-33  Una transferencia es UNA fila con origen y destino distintos; sin categoría.
  RN-34  Cero o más cargos; cada cargo es un EGRESO normal, con su categoría, que
         apunta a la transferencia (id_transferencia).
  RN-35  El cargo sale de la cuenta de origen y lleva la fecha de la transferencia.
  RN-36  El usuario escribe el valor real del cargo; el sistema no calcula tarifas.
  RN-37  Transferencia y cargos se guardan en UNA transacción: todos o ninguno (CA-03).
  RN-38  Anular una transferencia anula sus cargos vigentes, en la misma transacción (CA-04).
  RN-72  No se cambia la cuenta de origen de una transferencia que tiene cargos.
  RN-12  Las dos cuentas deben estar activas para registrar, corregir, anular o reactivar.
  RN-06  Transferencia, cuenta o categoría de otro usuario: "no encontrado".

Flujo del registro (ARQUITECTURA.md, sección 5.2)
    BEGIN
      revisar las dos cuentas (FOR SHARE)
      INSERT la transferencia
      por cada cargo: revisar su categoría (FOR SHARE) e INSERT el EGRESO
    COMMIT   -- si cualquier paso falla: ROLLBACK, y no queda nada

Orden de los bloqueos, siempre el mismo para evitar deadlocks: primero la
transferencia, después sus cargos, después las cuentas y las categorías.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import psycopg

from app.entidades.movimiento import EstadoMovimiento, Movimiento, TipoMovimiento, TransferenciaConCargos
from app.errores import ErrorNegocio, NoEncontrado
from app.repositorios.movimientos import MovimientoRepositorio
from app.servicios.validaciones import validar_dinero
from app.servicios.verificaciones import MENSAJE_CUENTA_ARCHIVADA, VerificadorDeUso


@dataclass(frozen=True)
class DatosCargo:
    """Un cargo: valor real (RN-36), categoría de egreso y descripción opcional."""

    monto: Decimal
    id_categoria: int
    descripcion: str | None = None


@dataclass(frozen=True)
class DatosTransferencia:
    id_cuenta_origen: int
    id_cuenta_destino: int
    monto: Decimal
    fecha: date
    descripcion: str | None = None
    cargos: list[DatosCargo] = field(default_factory=list)


class TransferenciaServicio:
    def __init__(self, con: psycopg.Connection):
        self.con = con
        self.movimientos = MovimientoRepositorio(con)
        self.verificar = VerificadorDeUso(con)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def obtener(self, id_usuario: int, id_transferencia: int) -> TransferenciaConCargos:
        detalle = self.movimientos.obtener_detalle(id_usuario, id_transferencia)
        if detalle is None or detalle.movimiento.tipo != TipoMovimiento.TRANSFERENCIA:
            raise NoEncontrado("No se encontró la transferencia.")
        return TransferenciaConCargos(detalle, self.movimientos.listar_cargos(id_usuario, id_transferencia))

    # ------------------------------------------------------------------
    # Acciones: cada una es UNA transacción
    # ------------------------------------------------------------------

    def registrar(self, id_usuario: int, datos: DatosTransferencia) -> TransferenciaConCargos:
        """RN-33 a RN-37. Si un cargo falla, se deshace también la transferencia (CA-03)."""
        descripcion = self._validar_transferencia(datos.id_cuenta_origen, datos.id_cuenta_destino,
                                                  datos.monto, datos.descripcion)
        cargos = [(c, self._validar_cargo(c)) for c in datos.cargos]
        with self.con.transaction():
            self.verificar.cuenta_activa(id_usuario, datos.id_cuenta_origen)
            self.verificar.cuenta_activa(id_usuario, datos.id_cuenta_destino)
            transferencia = self.movimientos.insertar_transferencia(
                id_usuario, datos.id_cuenta_origen, datos.id_cuenta_destino, datos.monto, datos.fecha, descripcion)
            for cargo, descripcion_cargo in cargos:
                self._insertar_cargo(id_usuario, transferencia, cargo, descripcion_cargo)
        return self.obtener(id_usuario, transferencia.id_movimiento)

    def agregar_cargo(self, id_usuario: int, id_transferencia: int, cargo: DatosCargo) -> TransferenciaConCargos:
        """Agrega un cargo que se olvidó al registrar la transferencia."""
        descripcion = self._validar_cargo(cargo)
        with self.con.transaction():
            transferencia = self._bloquear_vigente(id_usuario, id_transferencia, "agregarle cargos")
            self._cuentas_activas(id_usuario, transferencia)
            self._insertar_cargo(id_usuario, transferencia, cargo, descripcion)
        return self.obtener(id_usuario, id_transferencia)

    def corregir(self, id_usuario: int, id_transferencia: int, datos: DatosTransferencia) -> TransferenciaConCargos:
        """RN-72. Los cargos no se tocan aquí, salvo su fecha, que sigue a la de la transferencia (RN-35)."""
        if datos.cargos:
            raise ErrorNegocio("Los cargos se corrigen uno por uno, no al corregir la transferencia.")
        descripcion = self._validar_transferencia(datos.id_cuenta_origen, datos.id_cuenta_destino,
                                                  datos.monto, datos.descripcion)
        with self.con.transaction():
            transferencia = self._bloquear_vigente(id_usuario, id_transferencia, "corregirla")
            cargos = self.movimientos.bloquear_cargos(id_usuario, id_transferencia)
            if datos.id_cuenta_origen != transferencia.id_cuenta and cargos:
                raise ErrorNegocio("La cuenta de origen no se puede cambiar porque la transferencia tiene "
                                   "cargos. Anúlela y regístrela de nuevo.")
            self._cuentas_activas(id_usuario, transferencia,
                                  "Una cuenta de la transferencia está archivada. Reactívela para corregirla.")
            for id_cuenta in {datos.id_cuenta_origen, datos.id_cuenta_destino} - {
                    transferencia.id_cuenta, transferencia.id_cuenta_destino}:
                self.verificar.cuenta_activa(id_usuario, id_cuenta)
            self.movimientos.corregir_transferencia(
                id_usuario, id_transferencia, datos.id_cuenta_origen, datos.id_cuenta_destino,
                datos.monto, datos.fecha, descripcion)
            self.movimientos.cambiar_fecha_cargos(id_usuario, id_transferencia, datos.fecha)
        return self.obtener(id_usuario, id_transferencia)

    def corregir_cargo(self, id_usuario: int, id_transferencia: int, id_cargo: int,
                       cargo: DatosCargo) -> TransferenciaConCargos:
        """De un cargo se corrigen monto, categoría y descripción (RN-72). Cuenta y fecha
        son siempre las de la transferencia (RN-35)."""
        descripcion = self._validar_cargo(cargo)
        with self.con.transaction():
            transferencia = self._bloquear_vigente(id_usuario, id_transferencia, "corregir sus cargos")
            actual = next((c for c in self.movimientos.bloquear_cargos(id_usuario, id_transferencia)
                           if c.id_movimiento == id_cargo), None)
            if actual is None:
                raise NoEncontrado("No se encontró el cargo en esta transferencia.")
            if not actual.esta_vigente():
                raise ErrorNegocio("El cargo está anulado. Reactívelo para corregirlo.")
            self._cuentas_activas(id_usuario, transferencia,
                                  "Una cuenta de la transferencia está archivada. Reactívela para corregirla.")
            if cargo.id_categoria != actual.id_categoria:
                self.verificar.categoria_utilizable(id_usuario, cargo.id_categoria, TipoMovimiento.EGRESO)
            self.movimientos.corregir_cargo(id_usuario, id_cargo, cargo.id_categoria, cargo.monto, descripcion)
        return self.obtener(id_usuario, id_transferencia)

    def anular(self, id_usuario: int, id_transferencia: int) -> TransferenciaConCargos:
        """RN-38, CA-04: la transferencia y sus cargos vigentes, en una transacción."""
        with self.con.transaction():
            transferencia = self._bloquear(id_usuario, id_transferencia)
            if not transferencia.esta_vigente():
                raise ErrorNegocio("La transferencia ya está anulada.")
            cargos = self.movimientos.bloquear_cargos(id_usuario, id_transferencia)
            self._cuentas_activas(id_usuario, transferencia,
                                  "Una cuenta de la transferencia está archivada. Reactívela primero.")
            self.movimientos.cambiar_estado(id_usuario, id_transferencia, EstadoMovimiento.ANULADO)
            for cargo in cargos:
                if cargo.esta_vigente():
                    self.movimientos.cambiar_estado(id_usuario, cargo.id_movimiento, EstadoMovimiento.ANULADO)
        return self.obtener(id_usuario, id_transferencia)

    def reactivar(self, id_usuario: int, id_transferencia: int) -> TransferenciaConCargos:
        """RN-71. Solo la transferencia: cada cargo se reactiva aparte.

        Al anular, no se guarda cuáles cargos estaban vigentes y cuáles ya se
        habían anulado solos; reactivarlos todos podría revivir un cargo que el
        usuario había anulado a propósito.
        """
        with self.con.transaction():
            transferencia = self._bloquear(id_usuario, id_transferencia)
            if transferencia.esta_vigente():
                raise ErrorNegocio("La transferencia ya está vigente.")
            self._cuentas_activas(id_usuario, transferencia,
                                  "Una cuenta de la transferencia está archivada. Reactívela primero.")
            self.movimientos.cambiar_estado(id_usuario, id_transferencia, EstadoMovimiento.VIGENTE)
        return self.obtener(id_usuario, id_transferencia)

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _bloquear(self, id_usuario: int, id_transferencia: int) -> Movimiento:
        movimiento = self.movimientos.obtener_para_actualizar(id_usuario, id_transferencia)
        if movimiento is None or movimiento.tipo != TipoMovimiento.TRANSFERENCIA:
            raise NoEncontrado("No se encontró la transferencia.")
        return movimiento

    def _bloquear_vigente(self, id_usuario: int, id_transferencia: int, accion: str) -> Movimiento:
        transferencia = self._bloquear(id_usuario, id_transferencia)
        if not transferencia.esta_vigente():
            raise ErrorNegocio(f"La transferencia está anulada. Reactívela para {accion}.")
        return transferencia

    def _cuentas_activas(self, id_usuario: int, transferencia: Movimiento,
                         mensaje: str = MENSAJE_CUENTA_ARCHIVADA) -> None:
        """Las dos cuentas de la transferencia deben estar activas (RN-12)."""
        for id_cuenta in (transferencia.id_cuenta, transferencia.id_cuenta_destino):
            self.verificar.cuenta_activa(id_usuario, id_cuenta, mensaje)

    def _insertar_cargo(self, id_usuario: int, transferencia: Movimiento, cargo: DatosCargo,
                        descripcion: str | None) -> Movimiento:
        """RN-34, RN-35: EGRESO con la cuenta de origen y la fecha de la transferencia."""
        self.verificar.categoria_utilizable(id_usuario, cargo.id_categoria, TipoMovimiento.EGRESO)
        return self.movimientos.insertar_cargo(
            id_usuario, transferencia.id_movimiento, transferencia.id_cuenta, cargo.id_categoria,
            cargo.monto, transferencia.fecha, descripcion)

    @staticmethod
    def _validar_transferencia(origen: int, destino: int, monto: Decimal, descripcion: str | None) -> str | None:
        if origen == destino:
            raise ErrorNegocio("La cuenta de origen y la de destino deben ser distintas.")
        validar_dinero(monto, "El monto de la transferencia", permitir_cero=False)
        return _limpiar_descripcion(descripcion)

    @staticmethod
    def _validar_cargo(cargo: DatosCargo) -> str | None:
        validar_dinero(cargo.monto, "El monto del cargo", permitir_cero=False)
        return _limpiar_descripcion(cargo.descripcion)


def _limpiar_descripcion(descripcion: str | None) -> str | None:
    """Sin espacios alrededor; si queda vacía, None (no hay descripción)."""
    if descripcion is None:
        return None
    descripcion = descripcion.strip()
    if descripcion == "":
        return None
    return descripcion
