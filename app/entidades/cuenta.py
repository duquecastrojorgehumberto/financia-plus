"""Entidad Cuenta: una fila de la tabla cuenta (MODELO_DATOS.md, sección 4.2).

El saldo NO es una columna de la tabla (D-11): se calcula con los movimientos.
Por eso hay dos clases:
  * Cuenta          -> exactamente lo que está guardado en la fila.
  * CuentaConSaldo  -> una Cuenta MÁS su saldo calculado. No hereda de Cuenta:
                       la contiene (composición). "Tiene una cuenta y un saldo".
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class TipoCuenta(StrEnum):
    """Valores permitidos por el CHECK ck_cuenta_tipo (D-16)."""

    EFECTIVO = "EFECTIVO"
    AHORROS = "AHORROS"
    CORRIENTE = "CORRIENTE"
    BILLETERA_DIGITAL = "BILLETERA_DIGITAL"
    OTRA = "OTRA"


@dataclass(frozen=True)
class Cuenta:
    id_cuenta: int
    id_usuario: int
    nombre: str
    tipo: TipoCuenta
    saldo_inicial: Decimal
    activa: bool          # False = archivada (RN-12)
    creado_en: datetime


@dataclass(frozen=True)
class CuentaConSaldo:
    cuenta: Cuenta
    saldo: Decimal

    def saldo_negativo(self) -> bool:
        """RN-14: un saldo negativo no se bloquea, pero se avisa."""
        return self.saldo < 0

    def datos_publicos(self) -> dict:
        """Lo que se envía al navegador. El dinero viaja como texto ("130000.00"), nunca float."""
        c = self.cuenta
        return {
            "id_cuenta": c.id_cuenta,
            "nombre": c.nombre,
            "tipo": str(c.tipo),
            "saldo_inicial": f"{c.saldo_inicial:.2f}",
            "saldo": f"{self.saldo:.2f}",
            "saldo_negativo": self.saldo_negativo(),
            "activa": c.activa,
            "creado_en": c.creado_en.isoformat(),
        }
