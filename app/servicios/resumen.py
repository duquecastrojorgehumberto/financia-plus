"""Resumen financiero e indicadores (RF-13, RF-15). Solo lectura: no abre transacciones de escritura.

Indicadores (en este momento, sin periodo)
  RN-60  Saldo total = suma de los saldos de las cuentas ACTIVAS.
  RN-61  Total reservado = suma de los valores actuales de los bolsillos ACTIVOS.
  RN-62  Disponible = saldo total − total reservado.
  RN-63  Si el disponible es negativo, se avisa; no se bloquea nada (CA-10).

Resumen de un periodo (de "desde" a "hasta", ambas fechas incluidas)
  RN-64  Ingresos y egresos = movimientos VIGENTES de tipo INGRESO y EGRESO.
         Las transferencias no entran (no son ingreso ni gasto); sus cargos sí,
         porque son egresos (D-05).
  RN-53  Los ajustes NO son ingresos ni gastos: se muestran aparte.
  RN-27  El total de una categoría incluye el de sus subcategorías (CA-12).
         Cada categoría trae también su porcentaje sobre el total de su tipo
         (calculado aquí, con Decimal: la interfaz no calcula nada).

Resumen mensual (para el gráfico de ingresos y egresos)
  Por cada uno de los últimos N meses: ingresos, egresos y balance, con las
  mismas reglas RN-64 y RN-53. Los meses sin movimientos aparecen con 0.

Ninguno de estos datos se guarda en la base: todos se calculan al pedirlos (D-11).
"""

from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import psycopg

from app.entidades.movimiento import TipoMovimiento
from app.errores import ErrorNegocio
from app.repositorios.bolsillos import BolsilloRepositorio
from app.repositorios.cuentas import CuentaRepositorio
from app.repositorios.resumen import ResumenRepositorio

CERO = Decimal("0")
CIEN = Decimal("100")
UN_DECIMAL = Decimal("0.1")
MESES_MAXIMOS = 24


def _texto(valor: Decimal) -> str:
    return f"{valor:.2f}"


def porcentaje(parte: Decimal, total: Decimal) -> Decimal:
    """parte ÷ total × 100, redondeado a UN decimal (la mitad hacia arriba: 12.25 → 12.3).

    Todo con Decimal, nunca float. Si el total es 0 no hay de qué sacar porcentaje: 0.
    Por el redondeo, los porcentajes de una lista pueden sumar 99,9 o 100,1; es normal.
    """
    if total == 0:
        return CERO
    return (parte / total * CIEN).quantize(UN_DECIMAL, rounding=ROUND_HALF_UP)


def _texto_porcentaje(valor: Decimal) -> str:
    return f"{valor:.1f}"


@dataclass(frozen=True)
class Indicadores:
    saldo_total: Decimal
    total_reservado: Decimal

    def disponible(self) -> Decimal:
        """RN-62."""
        return self.saldo_total - self.total_reservado

    def disponible_negativo(self) -> bool:
        """RN-63: se muestra con un aviso; no bloquea nada."""
        return self.disponible() < 0

    def datos_publicos(self) -> dict:
        return {
            "saldo_total": _texto(self.saldo_total),
            "total_reservado": _texto(self.total_reservado),
            "disponible": _texto(self.disponible()),
            "disponible_negativo": self.disponible_negativo(),
        }


@dataclass
class TotalCategoria:
    """Una categoría raíz con su total consolidado (RN-27).

    total = directo (movimientos con la raíz misma) + la suma de sus subcategorías.
    """

    id_categoria: int
    nombre: str
    directo: Decimal = CERO
    subcategorias: list[dict] = field(default_factory=list)   # [{id_categoria, nombre, total}]

    def total(self) -> Decimal:
        return self.directo + sum((s["total"] for s in self.subcategorias), CERO)

    def datos_publicos(self, total_del_tipo: Decimal) -> dict:
        """total_del_tipo: la suma de todas las raíces del mismo tipo (ingresos o egresos).
        Cada porcentaje es sobre ese total, también el de cada subcategoría."""
        return {
            "id_categoria": self.id_categoria,
            "nombre": self.nombre,
            "total": _texto(self.total()),
            "porcentaje": _texto_porcentaje(porcentaje(self.total(), total_del_tipo)),
            "directo": _texto(self.directo),
            "porcentaje_directo": _texto_porcentaje(porcentaje(self.directo, total_del_tipo)),
            "subcategorias": [{"id_categoria": s["id_categoria"], "nombre": s["nombre"],
                               "total": _texto(s["total"]),
                               "porcentaje": _texto_porcentaje(porcentaje(s["total"], total_del_tipo))}
                              for s in self.subcategorias],
        }


def _categorias_publicas(categorias: list[TotalCategoria]) -> list[dict]:
    """Las raíces de UN tipo, cada una con su porcentaje sobre la suma de todas ellas."""
    total_del_tipo = sum((c.total() for c in categorias), CERO)
    return [c.datos_publicos(total_del_tipo) for c in categorias]


@dataclass(frozen=True)
class ResumenPeriodo:
    desde: date
    hasta: date
    ingresos: Decimal
    egresos: Decimal
    ajustes_aumento: Decimal
    ajustes_disminucion: Decimal
    categorias_ingreso: list[TotalCategoria]
    categorias_egreso: list[TotalCategoria]

    def balance(self) -> Decimal:
        """Ingresos − egresos del periodo. Los ajustes no entran (RN-53)."""
        return self.ingresos - self.egresos

    def datos_publicos(self) -> dict:
        return {
            "desde": self.desde.isoformat(),
            "hasta": self.hasta.isoformat(),
            "ingresos": _texto(self.ingresos),
            "egresos": _texto(self.egresos),
            "balance": _texto(self.balance()),
            "ajustes": {"aumentos": _texto(self.ajustes_aumento),
                        "disminuciones": _texto(self.ajustes_disminucion)},
            "categorias": {"ingresos": _categorias_publicas(self.categorias_ingreso),
                           "egresos": _categorias_publicas(self.categorias_egreso)},
        }


@dataclass(frozen=True)
class TotalMes:
    """Ingresos y egresos VIGENTES de un mes (RN-64). mes es el primer día del mes."""

    mes: date
    ingresos: Decimal
    egresos: Decimal

    def balance(self) -> Decimal:
        """Ingresos − egresos del mes. Los ajustes no entran (RN-53)."""
        return self.ingresos - self.egresos

    def datos_publicos(self) -> dict:
        return {
            "mes": self.mes.strftime("%Y-%m"),   # "2026-11"
            "ingresos": _texto(self.ingresos),
            "egresos": _texto(self.egresos),
            "balance": _texto(self.balance()),
        }


class ResumenServicio:
    def __init__(self, con: psycopg.Connection):
        self.cuentas = CuentaRepositorio(con)
        self.bolsillos = BolsilloRepositorio(con)
        self.resumen = ResumenRepositorio(con)

    def indicadores(self, id_usuario: int) -> Indicadores:
        """RN-60 a RN-63. Usa los mismos cálculos de saldo y valor actual que el resto de la API."""
        saldo_total = sum((c.saldo for c in self.cuentas.listar_con_saldo(id_usuario, incluir_archivadas=False)), CERO)
        reservado = sum((b.valor_actual for b in self.bolsillos.listar_con_valor(id_usuario, incluir_archivados=False)), CERO)
        return Indicadores(saldo_total=saldo_total, total_reservado=reservado)

    def periodo(self, id_usuario: int, desde: date | None = None, hasta: date | None = None) -> ResumenPeriodo:
        """RN-64, RN-53, RN-27. Sin fechas: el mes actual completo."""
        desde, hasta = self._periodo_valido(desde, hasta)
        por_tipo = self.resumen.totales_por_tipo(id_usuario, desde, hasta)
        ingresos, egresos = self._por_categoria(self.resumen.totales_por_categoria(id_usuario, desde, hasta))
        return ResumenPeriodo(
            desde=desde, hasta=hasta,
            ingresos=por_tipo.get(TipoMovimiento.INGRESO, CERO),
            egresos=por_tipo.get(TipoMovimiento.EGRESO, CERO),
            ajustes_aumento=por_tipo.get(TipoMovimiento.AJUSTE_AUMENTO, CERO),
            ajustes_disminucion=por_tipo.get(TipoMovimiento.AJUSTE_DISMINUCION, CERO),
            categorias_ingreso=ingresos,
            categorias_egreso=egresos,
        )

    def mensual(self, id_usuario: int, meses: int = 6, referencia: date | None = None) -> list[TotalMes]:
        """Los últimos `meses` meses hasta el de `referencia` (por defecto, hoy), del más antiguo
        al más reciente. Siempre devuelve exactamente `meses` elementos: los vacíos con 0."""
        if not 1 <= meses <= MESES_MAXIMOS:
            raise ErrorNegocio(f"El número de meses debe estar entre 1 y {MESES_MAXIMOS}.")
        ultimo_mes = (referencia or date.today()).replace(day=1)
        filas = self.resumen.totales_mensuales(id_usuario, ultimo_mes, meses)
        return [TotalMes(mes=f["mes"], ingresos=f["ingresos"], egresos=f["egresos"]) for f in filas]

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    @staticmethod
    def _periodo_valido(desde: date | None, hasta: date | None) -> tuple[date, date]:
        hoy = date.today()
        desde = desde or hoy.replace(day=1)
        hasta = hasta or hoy.replace(day=monthrange(hoy.year, hoy.month)[1])
        if desde > hasta:
            raise ErrorNegocio("La fecha inicial no puede ser posterior a la fecha final.")
        return desde, hasta

    @staticmethod
    def _por_categoria(filas: list[dict]) -> tuple[list[TotalCategoria], list[TotalCategoria]]:
        """RN-27: agrupa cada total bajo su categoría raíz. Devuelve (ingresos, egresos),
        cada lista ordenada de mayor a menor total."""
        raices: dict[int, TotalCategoria] = {}
        tipo_de_raiz: dict[int, str] = {}
        for f in filas:
            raiz = raices.setdefault(f["id_raiz"], TotalCategoria(f["id_raiz"], f["nombre_raiz"]))
            tipo_de_raiz[f["id_raiz"]] = f["tipo"]
            if f["id_padre"] is None:
                raiz.directo += f["total"]
            else:
                raiz.subcategorias.append({"id_categoria": f["id_categoria"], "nombre": f["nombre"],
                                           "total": f["total"]})
        for raiz in raices.values():
            raiz.subcategorias.sort(key=lambda s: (-s["total"], s["nombre"]))
        ordenadas = sorted(raices.values(), key=lambda r: (-r.total(), r.nombre))
        ingresos = [r for r in ordenadas if tipo_de_raiz[r.id_categoria] == TipoMovimiento.INGRESO]
        egresos = [r for r in ordenadas if tipo_de_raiz[r.id_categoria] == TipoMovimiento.EGRESO]
        return ingresos, egresos
