"""Entidad Movimiento: una fila de la tabla movimiento (MODELO_DATOS.md, sección 4.4).

Movimiento es UNA sola clase para los cinco tipos, igual que la tabla (D-03):
el atributo tipo dice cuál es. No hay herencia (ARQUITECTURA.md, sección 3.1).

MovimientoDetalle agrega los NOMBRES de la cuenta, la cuenta destino y la
categoría, para mostrarlos en el historial sin que la interfaz tenga que
buscarlos. Igual que CuentaConSaldo, contiene un Movimiento (composición).
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum


class TipoMovimiento(StrEnum):
    """Valores del CHECK ck_movimiento_tipo."""

    INGRESO = "INGRESO"
    EGRESO = "EGRESO"
    TRANSFERENCIA = "TRANSFERENCIA"
    AJUSTE_AUMENTO = "AJUSTE_AUMENTO"
    AJUSTE_DISMINUCION = "AJUSTE_DISMINUCION"


class EstadoMovimiento(StrEnum):
    """Valores del CHECK ck_movimiento_estado. Solo VIGENTE cuenta (RN-70)."""

    VIGENTE = "VIGENTE"
    ANULADO = "ANULADO"


@dataclass(frozen=True)
class Movimiento:
    id_movimiento: int
    id_usuario: int
    tipo: TipoMovimiento
    id_cuenta: int                 # en una transferencia: la cuenta de origen
    id_cuenta_destino: int | None  # solo TRANSFERENCIA
    id_categoria: int | None       # obligatoria en INGRESO y EGRESO
    id_transferencia: int | None   # solo en un EGRESO que es cargo de una transferencia
    monto: Decimal
    fecha: date
    descripcion: str | None
    estado: EstadoMovimiento
    creado_en: datetime
    actualizado_en: datetime

    def esta_vigente(self) -> bool:
        return self.estado == EstadoMovimiento.VIGENTE

    def es_cargo(self) -> bool:
        """True si es un EGRESO que pertenece a una transferencia (RN-34)."""
        return self.id_transferencia is not None


@dataclass(frozen=True)
class MovimientoDetalle:
    movimiento: Movimiento
    nombre_cuenta: str
    nombre_cuenta_destino: str | None
    nombre_categoria: str | None

    def datos_publicos(self) -> dict:
        """Para el navegador: dinero como texto, fechas en formato ISO (2026-11-01)."""
        m = self.movimiento
        return {
            "id_movimiento": m.id_movimiento,
            "tipo": str(m.tipo),
            "estado": str(m.estado),
            "fecha": m.fecha.isoformat(),
            "monto": f"{m.monto:.2f}",
            "descripcion": m.descripcion,
            "id_cuenta": m.id_cuenta,
            "nombre_cuenta": self.nombre_cuenta,
            "id_cuenta_destino": m.id_cuenta_destino,
            "nombre_cuenta_destino": self.nombre_cuenta_destino,
            "id_categoria": m.id_categoria,
            "nombre_categoria": self.nombre_categoria,
            "id_transferencia": m.id_transferencia,
            "creado_en": m.creado_en.isoformat(),
            "actualizado_en": m.actualizado_en.isoformat(),
        }


@dataclass(frozen=True)
class TransferenciaConCargos:
    """Una transferencia y sus cargos (RN-34): lo que el usuario ve como UNA operación.

    En la base son varias filas de movimiento; aquí se agrupan (composición).
    """

    transferencia: MovimientoDetalle
    cargos: list[MovimientoDetalle]

    def total_cargos_vigentes(self) -> Decimal:
        return sum((c.movimiento.monto for c in self.cargos if c.movimiento.esta_vigente()), Decimal("0"))

    def datos_publicos(self) -> dict:
        return {
            **self.transferencia.datos_publicos(),
            "cargos": [c.datos_publicos() for c in self.cargos],
            "total_cargos": f"{self.total_cargos_vigentes():.2f}",
        }
