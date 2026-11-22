"""Ajustes de saldo (RF-17).

El usuario no escribe encima del saldo (no se puede: el saldo no se guarda,
se calcula). Indica el SALDO REAL que ve en su banco, y el sistema registra la
diferencia como un movimiento visible, fechado, con motivo y anulable (D-12).

Reglas que aplica
  RN-50  Diferencia = saldo real − saldo calculado.
  RN-51  Positiva → AJUSTE_AUMENTO; negativa → AJUSTE_DISMINUCION; cero → nada.
         El monto guardado es siempre positivo (el valor absoluto).
  RN-52  Motivo obligatorio; sin categoría.
  RN-53  Los ajustes no son ingresos ni gastos (eso lo respeta el resumen, Tarea 14).
  RN-54  Queda en el historial y se anula o reactiva en /api/movimientos.
  RN-55  Cálculo y registro en UNA transacción que BLOQUEA la fila de la cuenta.
  RN-12  La cuenta debe estar activa.

Flujo (ARQUITECTURA.md, sección 5.4)
    BEGIN
      SELECT ... FROM cuenta ... FOR UPDATE     -- nadie registra movimientos en ella
      calcular el saldo
      diferencia = saldo real − saldo calculado
      si diferencia ≠ 0: INSERT del ajuste
    COMMIT

Por qué el bloqueo: sin él, otro movimiento podría registrarse entre el cálculo
y el INSERT, y el ajuste quedaría calculado con un saldo viejo. Con FOR UPDATE,
si otra transacción está insertando un movimiento en la cuenta, el ajuste espera
a que termine y lo incluye en el cálculo (prueba con dos conexiones reales en
tests/test_ajustes.py).
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import psycopg

from app.entidades.cuenta import CuentaConSaldo
from app.entidades.movimiento import MovimientoDetalle, TipoMovimiento
from app.errores import ErrorNegocio, NoEncontrado
from app.repositorios.cuentas import CuentaRepositorio
from app.repositorios.movimientos import MovimientoRepositorio
from app.servicios.validaciones import validar_dinero
from app.servicios.verificaciones import MENSAJE_CUENTA_ARCHIVADA, VerificadorDeUso

TIPOS_AJUSTE = (TipoMovimiento.AJUSTE_AUMENTO, TipoMovimiento.AJUSTE_DISMINUCION)


@dataclass(frozen=True)
class ResultadoAjuste:
    """Qué pasó al ajustar: el saldo antes, la cuenta después y el ajuste (None si no hizo falta)."""

    saldo_anterior: Decimal
    cuenta: CuentaConSaldo
    ajuste: MovimientoDetalle | None

    def datos_publicos(self) -> dict:
        return {
            "saldo_anterior": f"{self.saldo_anterior:.2f}",
            "cuenta": self.cuenta.datos_publicos(),
            "ajuste": self.ajuste.datos_publicos() if self.ajuste else None,
        }


class AjusteServicio:
    def __init__(self, con: psycopg.Connection):
        self.con = con
        self.cuentas = CuentaRepositorio(con)
        self.movimientos = MovimientoRepositorio(con)
        self.verificar = VerificadorDeUso(con)

    def ajustar(self, id_usuario: int, id_cuenta: int, saldo_real: Decimal, motivo: str,
                fecha: date | None = None) -> ResultadoAjuste:
        """RN-50 a RN-55. Sin fecha, el ajuste queda con la fecha de hoy."""
        # El saldo real puede ser negativo (RN-14: una cuenta puede estar en negativo).
        validar_dinero(abs(saldo_real), "El saldo real", permitir_cero=True)
        motivo = self._motivo_valido(motivo)
        fecha = fecha or date.today()

        with self.con.transaction():
            cuenta = self.cuentas.obtener_para_actualizar(id_usuario, id_cuenta)   # FOR UPDATE (RN-55)
            if cuenta is None:
                raise NoEncontrado("No se encontró la cuenta.")
            if not cuenta.activa:
                raise ErrorNegocio(MENSAJE_CUENTA_ARCHIVADA)
            saldo_calculado = self.cuentas.obtener_con_saldo(id_usuario, id_cuenta).saldo
            diferencia = saldo_real - saldo_calculado
            ajuste = None
            if diferencia != 0:
                tipo = TipoMovimiento.AJUSTE_AUMENTO if diferencia > 0 else TipoMovimiento.AJUSTE_DISMINUCION
                ajuste = self.movimientos.insertar_ajuste(id_usuario, tipo, id_cuenta, abs(diferencia),
                                                          fecha, motivo)

        detalle = self.movimientos.obtener_detalle(id_usuario, ajuste.id_movimiento) if ajuste else None
        return ResultadoAjuste(saldo_anterior=saldo_calculado,
                               cuenta=self.cuentas.obtener_con_saldo(id_usuario, id_cuenta),
                               ajuste=detalle)

    def corregir(self, id_usuario: int, id_ajuste: int, fecha: date, motivo: str) -> MovimientoDetalle:
        """Solo la fecha y el motivo. Si el monto estaba mal, se anula el ajuste y se hace otro
        con el saldo real correcto: el monto no es un dato que el usuario escribe, sale de un cálculo."""
        motivo = self._motivo_valido(motivo)
        with self.con.transaction():
            ajuste = self.movimientos.obtener_para_actualizar(id_usuario, id_ajuste)
            if ajuste is None or ajuste.tipo not in TIPOS_AJUSTE:
                raise NoEncontrado("No se encontró el ajuste.")
            if not ajuste.esta_vigente():
                raise ErrorNegocio("El ajuste está anulado. Reactívelo para corregirlo.")
            self.verificar.cuenta_activa(id_usuario, ajuste.id_cuenta,
                                         "La cuenta del ajuste está archivada. Reactívela para corregirlo.")
            self.movimientos.corregir_ajuste(id_usuario, id_ajuste, fecha, motivo)
        return self.movimientos.obtener_detalle(id_usuario, id_ajuste)

    @staticmethod
    def _motivo_valido(motivo: str) -> str:
        """RN-52: el motivo es obligatorio (la base también lo exige: ck_movimiento_forma)."""
        motivo = motivo.strip()
        if not motivo:
            raise ErrorNegocio("El motivo del ajuste es obligatorio.")
        return motivo
