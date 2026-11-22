"""Ingresos, egresos e historial; corregir, anular y reactivar (RF-04, RF-05, RF-14, RF-16).

Reglas que aplica
  RN-30  Cuenta, monto > 0, fecha y una sola categoría; descripción opcional.
  RN-31  La categoría de un ingreso es de INGRESO; la de un egreso, de EGRESO (CA-05).
         La base también lo exige (fk_movimiento_categoria); aquí se revisa antes
         para dar un mensaje claro.
  RN-12  Una cuenta archivada no recibe movimientos nuevos, y sus movimientos no
         se corrigen, anulan ni reactivan.
  RN-25  Una categoría desactivada no se usa en un movimiento nuevo (CA-14).
  RN-06  Cuenta, categoría o movimiento de otro usuario: "no encontrado" (CA-06).
  RN-70  Anular cambia el estado; nada se borra (CA-13).
  RN-71  Un anulado se puede reactivar.
  RN-72  Se corrigen monto, fecha, categoría, cuenta y descripción; el tipo no.
  RN-73  Al corregir se actualiza actualizado_en.

Qué queda para otras tareas
  * Transferencias y cargos (registrar, corregir, anular en cascada): Tarea 11.
    Aquí se rechaza anular o reactivar una TRANSFERENCIA (dejaría sus cargos
    sin anular) y corregir un cargo (su cuenta y fecha dependen de la transferencia).
  * Registrar y corregir ajustes: Tarea 12. Anularlos y reactivarlos ya funciona (RN-54).

Bloqueos (para que nada cambie entre la revisión y el cambio)
  * El movimiento que se corrige, anula o reactiva: FOR UPDATE.
  * La cuenta y la categoría que se usan: FOR SHARE. Varias transacciones
    pueden usarlas a la vez, pero archivar la cuenta o desactivar la
    categoría tiene que esperar a que terminen.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import psycopg

from app.entidades.categoria import Categoria
from app.entidades.cuenta import Cuenta
from app.entidades.movimiento import EstadoMovimiento, Movimiento, MovimientoDetalle, TipoMovimiento
from app.errores import ErrorNegocio, NoEncontrado
from app.repositorios.categorias import CategoriaRepositorio
from app.repositorios.cuentas import CuentaRepositorio
from app.repositorios.movimientos import MovimientoRepositorio
from app.servicios.validaciones import validar_dinero

TIPOS_INGRESO_EGRESO = (TipoMovimiento.INGRESO, TipoMovimiento.EGRESO)


@dataclass(frozen=True)
class DatosMovimiento:
    """Lo que el usuario escribe para registrar o corregir un ingreso o un egreso."""

    id_cuenta: int
    id_categoria: int
    monto: Decimal
    fecha: date
    descripcion: str | None = None


@dataclass(frozen=True)
class FiltroHistorial:
    """Filtros del historial (RF-14). Un valor en None significa "sin filtrar por esto"."""

    desde: date | None = None
    hasta: date | None = None
    id_cuenta: int | None = None
    tipo: str | None = None
    id_categoria: int | None = None
    estado: str | None = None


class MovimientoServicio:
    def __init__(self, con: psycopg.Connection):
        self.con = con
        self.movimientos = MovimientoRepositorio(con)
        self.cuentas = CuentaRepositorio(con)
        self.categorias = CategoriaRepositorio(con)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def historial(self, id_usuario: int, filtro: FiltroHistorial) -> list[MovimientoDetalle]:
        """RF-14. Incluye los anulados (CA-13: siguen visibles), salvo que se filtre por estado."""
        if filtro.desde and filtro.hasta and filtro.desde > filtro.hasta:
            raise ErrorNegocio("La fecha inicial no puede ser posterior a la fecha final.")
        if filtro.tipo is not None:
            self._enum_valido(TipoMovimiento, filtro.tipo, "El tipo de movimiento")
        if filtro.estado is not None:
            self._enum_valido(EstadoMovimiento, filtro.estado, "El estado")
        return self.movimientos.listar(
            id_usuario, desde=filtro.desde, hasta=filtro.hasta, id_cuenta=filtro.id_cuenta,
            tipo=filtro.tipo, id_categoria=filtro.id_categoria, estado=filtro.estado)

    def obtener(self, id_usuario: int, id_movimiento: int) -> MovimientoDetalle:
        detalle = self.movimientos.obtener_detalle(id_usuario, id_movimiento)
        if detalle is None:
            raise NoEncontrado("No se encontró el movimiento.")
        return detalle

    # ------------------------------------------------------------------
    # Acciones: cada una es UNA transacción
    # ------------------------------------------------------------------

    def registrar(self, id_usuario: int, tipo: str, datos: DatosMovimiento) -> MovimientoDetalle:
        """RF-04 y RF-05: registra un ingreso o un egreso."""
        tipo_movimiento = self._enum_valido(TipoMovimiento, tipo, "El tipo de movimiento")
        if tipo_movimiento not in TIPOS_INGRESO_EGRESO:
            raise ErrorNegocio("Aquí solo se registran ingresos y egresos. Las transferencias y los "
                               "ajustes tienen su propio registro.")
        descripcion = self._validar_datos(datos)
        with self.con.transaction():
            self._cuenta_activa(id_usuario, datos.id_cuenta)
            self._categoria_utilizable(id_usuario, datos.id_categoria, tipo_movimiento)
            movimiento = self.movimientos.insertar_ingreso_o_egreso(
                id_usuario, tipo_movimiento, datos.id_cuenta, datos.id_categoria,
                datos.monto, datos.fecha, descripcion)
        return self.obtener(id_usuario, movimiento.id_movimiento)

    def corregir(self, id_usuario: int, id_movimiento: int, datos: DatosMovimiento) -> MovimientoDetalle:
        """RN-72: corrige un ingreso o egreso VIGENTE. El tipo se conserva."""
        descripcion = self._validar_datos(datos)
        with self.con.transaction():
            movimiento = self._bloquear(id_usuario, id_movimiento)
            if movimiento.tipo not in TIPOS_INGRESO_EGRESO or movimiento.es_cargo():
                raise ErrorNegocio("Aquí solo se corrigen ingresos y egresos. Las transferencias, sus "
                                   "cargos y los ajustes se corrigen desde su propio registro.")
            if not movimiento.esta_vigente():
                raise ErrorNegocio("El movimiento está anulado. Reactívelo para corregirlo.")
            self._cuenta_activa(id_usuario, movimiento.id_cuenta,
                                "La cuenta del movimiento está archivada. Reactívela para corregirlo.")
            if datos.id_cuenta != movimiento.id_cuenta:
                self._cuenta_activa(id_usuario, datos.id_cuenta)
            if datos.id_categoria != movimiento.id_categoria:
                # Una categoría nueva debe poder usarse; si no cambia, se conserva aunque
                # se haya desactivado después (el movimiento no es nuevo).
                self._categoria_utilizable(id_usuario, datos.id_categoria, movimiento.tipo)
            self.movimientos.corregir(id_usuario, id_movimiento, datos.id_cuenta, datos.id_categoria,
                                      datos.monto, datos.fecha, descripcion)
        return self.obtener(id_usuario, id_movimiento)

    def anular(self, id_usuario: int, id_movimiento: int) -> MovimientoDetalle:
        """RN-70, CA-13: deja de contar, pero sigue en el historial."""
        with self.con.transaction():
            movimiento = self._bloquear_para_cambiar_estado(id_usuario, id_movimiento)
            if not movimiento.esta_vigente():
                raise ErrorNegocio("El movimiento ya está anulado.")
            self.movimientos.cambiar_estado(id_usuario, id_movimiento, EstadoMovimiento.ANULADO)
        return self.obtener(id_usuario, id_movimiento)

    def reactivar(self, id_usuario: int, id_movimiento: int) -> MovimientoDetalle:
        """RN-71: vuelve a contar.

        Un cargo solo se reactiva si su transferencia está vigente. Orden de los
        bloqueos: primero la transferencia y después el cargo, el mismo orden en
        que anular una transferencia bloquea sus cargos (Tarea 11). Bloquear en
        órdenes distintos puede dejar dos transacciones esperándose (deadlock).
        """
        with self.con.transaction():
            # id_transferencia nunca cambia, así que se puede leer sin bloqueo para saber el orden.
            id_transferencia = self.obtener(id_usuario, id_movimiento).movimiento.id_transferencia
            transferencia = self._bloquear(id_usuario, id_transferencia) if id_transferencia else None
            movimiento = self._bloquear_para_cambiar_estado(id_usuario, id_movimiento)
            if movimiento.esta_vigente():
                raise ErrorNegocio("El movimiento ya está vigente.")
            if transferencia is not None and not transferencia.esta_vigente():
                raise ErrorNegocio("Este cargo pertenece a una transferencia anulada. "
                                   "Reactive primero la transferencia.")
            self.movimientos.cambiar_estado(id_usuario, id_movimiento, EstadoMovimiento.VIGENTE)
        return self.obtener(id_usuario, id_movimiento)

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _bloquear(self, id_usuario: int, id_movimiento: int) -> Movimiento:
        movimiento = self.movimientos.obtener_para_actualizar(id_usuario, id_movimiento)
        if movimiento is None:
            raise NoEncontrado("No se encontró el movimiento.")
        return movimiento

    def _bloquear_para_cambiar_estado(self, id_usuario: int, id_movimiento: int) -> Movimiento:
        """Comprobaciones comunes de anular y reactivar."""
        movimiento = self._bloquear(id_usuario, id_movimiento)
        if movimiento.tipo == TipoMovimiento.TRANSFERENCIA:
            raise ErrorNegocio("Las transferencias se anulan y reactivan junto con sus cargos, "
                               "desde el registro de transferencias.")
        self._cuenta_activa(id_usuario, movimiento.id_cuenta,
                            "La cuenta del movimiento está archivada. Reactívela primero.")
        return movimiento

    def _cuenta_activa(self, id_usuario: int, id_cuenta: int,
                       mensaje_archivada: str = "La cuenta está archivada: no admite movimientos.") -> Cuenta:
        cuenta = self.cuentas.obtener_para_usar(id_usuario, id_cuenta)
        if cuenta is None:
            raise NoEncontrado("No se encontró la cuenta.")
        if not cuenta.activa:
            raise ErrorNegocio(mensaje_archivada)
        return cuenta

    def _categoria_utilizable(self, id_usuario: int, id_categoria: int, tipo: TipoMovimiento) -> Categoria:
        categoria = self.categorias.obtener_para_usar(id_usuario, id_categoria)
        if categoria is None:
            raise NoEncontrado("No se encontró la categoría.")
        if categoria.tipo != tipo:
            raise ErrorNegocio(f"La categoría '{categoria.nombre}' es de tipo {categoria.tipo}; "
                               f"un movimiento de tipo {tipo} necesita una categoría de tipo {tipo}.")
        if not categoria.activa:
            raise ErrorNegocio(f"La categoría '{categoria.nombre}' está desactivada.")
        return categoria

    @staticmethod
    def _validar_datos(datos: DatosMovimiento) -> str | None:
        """RN-30. Devuelve la descripción limpia: sin espacios alrededor, o None si queda vacía."""
        validar_dinero(datos.monto, "El monto", permitir_cero=False)
        if datos.descripcion is None:
            return None
        return datos.descripcion.strip() or None

    @staticmethod
    def _enum_valido(enum, valor: str, nombre: str):
        try:
            return enum(valor)
        except ValueError:
            opciones = ", ".join(enum)
            raise ErrorNegocio(f"{nombre} no es válido. Opciones: {opciones}.") from None
