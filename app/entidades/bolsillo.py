"""Entidades de bolsillos (MODELO_DATOS.md, secciones 4.5 y 4.6).

  * Bolsillo         -> una fila de la tabla bolsillo. Es "con meta" si tiene
                        monto_objetivo (D-08): no hay columna de tipo ni tabla de metas.
  * ValorBolsillo    -> una fila del historial (bolsillo_valor).
  * BolsilloConValor -> un Bolsillo MÁS su valor actual (el registro más
                        reciente del historial, D-09), por composición, igual
                        que CuentaConSaldo.

Un bolsillo no tiene relación con cuentas ni movimientos (D-10): es una reserva
virtual. Por eso aquí no aparece ninguna cuenta.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

CIEN = Decimal("100")
CENTESIMA = Decimal("0.01")


@dataclass(frozen=True)
class Bolsillo:
    id_bolsillo: int
    id_usuario: int
    nombre: str
    descripcion: str | None
    monto_objetivo: Decimal | None
    fecha_objetivo: date | None
    activo: bool          # False = archivado (RN-49)
    creado_en: datetime

    def es_meta(self) -> bool:
        """D-08, RN-41: es un bolsillo con meta si tiene monto objetivo."""
        return self.monto_objetivo is not None


@dataclass(frozen=True)
class ValorBolsillo:
    id_bolsillo_valor: int
    id_bolsillo: int
    valor: Decimal
    registrado_en: datetime

    def datos_publicos(self) -> dict:
        return {"valor": f"{self.valor:.2f}", "registrado_en": self.registrado_en.isoformat()}


@dataclass(frozen=True)
class BolsilloConValor:
    bolsillo: Bolsillo
    valor_actual: Decimal

    def progreso_porcentaje(self) -> Decimal | None:
        """RN-48: valor actual ÷ monto objetivo, en porcentaje con 2 decimales. Puede pasar
        de 100. Un bolsillo sin meta no tiene progreso (None)."""
        if not self.bolsillo.es_meta():
            return None
        return (self.valor_actual / self.bolsillo.monto_objetivo * CIEN).quantize(CENTESIMA)

    def datos_publicos(self) -> dict:
        b = self.bolsillo
        progreso = self.progreso_porcentaje()
        return {
            "id_bolsillo": b.id_bolsillo,
            "nombre": b.nombre,
            "descripcion": b.descripcion,
            "es_meta": b.es_meta(),
            "monto_objetivo": f"{b.monto_objetivo:.2f}" if b.es_meta() else None,
            "fecha_objetivo": b.fecha_objetivo.isoformat() if b.fecha_objetivo else None,
            "valor_actual": f"{self.valor_actual:.2f}",
            "progreso_porcentaje": f"{progreso:.2f}" if progreso is not None else None,
            "activo": b.activo,
            "creado_en": b.creado_en.isoformat(),
        }
