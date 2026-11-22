"""Bolsillos y metas (RF-08, RF-09, RF-10, RF-12).

Un bolsillo es una reserva virtual: el usuario escribe cuánto quiere tener
apartado, sin decir en qué cuenta está ese dinero (D-10, RN-40). Cambiar su
valor no es un ingreso ni un gasto y no toca ninguna cuenta (RN-47).

Reglas que aplica
  RN-41  Con meta si tiene monto objetivo (> 0); la fecha objetivo solo con monto.
  RN-42  El usuario escribe el valor directamente: no hay aportes ni retiros.
  RN-43  El valor no es negativo (cero sí).
  RN-44  Cada cambio de valor AGREGA un registro al historial.
  RN-45  Crear el bolsillo y su primer valor: una sola transacción.
  RN-46  Si el valor nuevo es igual al actual, no se agrega registro.
  RN-48  Progreso = valor ÷ monto objetivo (BolsilloConValor.progreso_porcentaje).
  RN-49  Se archiva con cualquier valor; conserva su historial.
  RN-06  Un bolsillo de otro usuario responde "no encontrado".
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import psycopg
from psycopg import errors

from app.entidades.bolsillo import Bolsillo, BolsilloConValor, ValorBolsillo
from app.errores import ErrorNegocio, NoEncontrado
from app.repositorios.bolsillos import BolsilloRepositorio
from app.servicios.validaciones import validar_dinero

MENSAJE_NOMBRE_REPETIDO = "Ya tiene un bolsillo activo con ese nombre."


@dataclass(frozen=True)
class DatosBolsillo:
    """Lo que el usuario escribe al crear o editar un bolsillo. Sin monto_objetivo: genérico."""

    nombre: str
    descripcion: str | None = None
    monto_objetivo: Decimal | None = None
    fecha_objetivo: date | None = None


class BolsilloServicio:
    def __init__(self, con: psycopg.Connection):
        self.con = con
        self.bolsillos = BolsilloRepositorio(con)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def listar(self, id_usuario: int, incluir_archivados: bool = False) -> list[BolsilloConValor]:
        return self.bolsillos.listar_con_valor(id_usuario, incluir_archivados=incluir_archivados)

    def obtener(self, id_usuario: int, id_bolsillo: int) -> BolsilloConValor:
        bolsillo = self.bolsillos.obtener_con_valor(id_usuario, id_bolsillo)
        if bolsillo is None:
            raise NoEncontrado("No se encontró el bolsillo.")
        return bolsillo

    def historial(self, id_usuario: int, id_bolsillo: int) -> list[ValorBolsillo]:
        """RF-12: los valores que ha tenido, del más reciente al más antiguo."""
        self.obtener(id_usuario, id_bolsillo)   # NoEncontrado si no es del usuario
        return self.bolsillos.historial(id_usuario, id_bolsillo)

    # ------------------------------------------------------------------
    # Acciones: cada una es UNA transacción
    # ------------------------------------------------------------------

    def crear(self, id_usuario: int, datos: DatosBolsillo, valor_inicial: Decimal = Decimal("0")) -> BolsilloConValor:
        """RN-45: el bolsillo y su primer valor, juntos o ninguno."""
        nombre, descripcion = self._validar(datos)
        validar_dinero(valor_inicial, "El valor del bolsillo", permitir_cero=True)
        try:
            with self.con.transaction():
                bolsillo = self.bolsillos.insertar(id_usuario, nombre, descripcion,
                                                   datos.monto_objetivo, datos.fecha_objetivo)
                self.bolsillos.insertar_valor(id_usuario, bolsillo.id_bolsillo, valor_inicial)
        except errors.UniqueViolation as error:
            self._traducir_nombre_repetido(error, MENSAJE_NOMBRE_REPETIDO)
        return self.obtener(id_usuario, bolsillo.id_bolsillo)

    def editar(self, id_usuario: int, id_bolsillo: int, datos: DatosBolsillo) -> BolsilloConValor:
        """Nombre, descripción y meta. Convertir un genérico en meta es llenar el monto
        objetivo (D-08); quitarlo lo vuelve genérico. El valor se cambia con cambiar_valor."""
        nombre, descripcion = self._validar(datos)
        try:
            with self.con.transaction():
                self._bloquear_activo(id_usuario, id_bolsillo, "editarlo")
                self.bolsillos.actualizar(id_usuario, id_bolsillo, nombre, descripcion,
                                          datos.monto_objetivo, datos.fecha_objetivo)
        except errors.UniqueViolation as error:
            self._traducir_nombre_repetido(error, MENSAJE_NOMBRE_REPETIDO)
        return self.obtener(id_usuario, id_bolsillo)

    def cambiar_valor(self, id_usuario: int, id_bolsillo: int, valor: Decimal) -> tuple[BolsilloConValor, bool]:
        """RN-42 a RN-46. Devuelve el bolsillo y si se agregó un registro (False si el valor no cambió).

        No toca ninguna cuenta ni movimiento (RN-47, CA-07).
        """
        validar_dinero(valor, "El valor del bolsillo", permitir_cero=True)
        with self.con.transaction():
            self._bloquear_activo(id_usuario, id_bolsillo, "cambiarle el valor")
            actual = self.bolsillos.obtener_con_valor(id_usuario, id_bolsillo).valor_actual
            registrado = valor != actual
            if registrado:
                self.bolsillos.insertar_valor(id_usuario, id_bolsillo, valor)
        return self.obtener(id_usuario, id_bolsillo), registrado

    def archivar(self, id_usuario: int, id_bolsillo: int) -> BolsilloConValor:
        """RN-49: con cualquier valor. Deja de sumar en el total reservado; conserva su historial."""
        with self.con.transaction():
            bolsillo = self._bloquear(id_usuario, id_bolsillo)
            if not bolsillo.activo:
                raise ErrorNegocio("El bolsillo ya está archivado.")
            self.bolsillos.cambiar_activo(id_usuario, id_bolsillo, False)
        return self.obtener(id_usuario, id_bolsillo)

    def reactivar(self, id_usuario: int, id_bolsillo: int) -> BolsilloConValor:
        try:
            with self.con.transaction():
                bolsillo = self._bloquear(id_usuario, id_bolsillo)
                if bolsillo.activo:
                    raise ErrorNegocio("El bolsillo ya está activo.")
                self.bolsillos.cambiar_activo(id_usuario, id_bolsillo, True)
        except errors.UniqueViolation as error:
            self._traducir_nombre_repetido(error, "Ya tiene otro bolsillo activo con ese nombre. Cámbiele "
                                                  "el nombre a ese antes de reactivar este.")
        return self.obtener(id_usuario, id_bolsillo)

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _bloquear(self, id_usuario: int, id_bolsillo: int) -> Bolsillo:
        bolsillo = self.bolsillos.obtener_para_actualizar(id_usuario, id_bolsillo)
        if bolsillo is None:
            raise NoEncontrado("No se encontró el bolsillo.")
        return bolsillo

    def _bloquear_activo(self, id_usuario: int, id_bolsillo: int, accion: str) -> Bolsillo:
        bolsillo = self._bloquear(id_usuario, id_bolsillo)
        if not bolsillo.activo:
            raise ErrorNegocio(f"El bolsillo está archivado. Reactívelo para {accion}.")
        return bolsillo

    @staticmethod
    def _validar(datos: DatosBolsillo) -> tuple[str, str | None]:
        """RN-41. Devuelve el nombre y la descripción limpios (sin espacios alrededor)."""
        nombre = datos.nombre.strip()
        if not nombre:
            raise ErrorNegocio("El nombre del bolsillo es obligatorio.")
        if datos.monto_objetivo is not None:
            validar_dinero(datos.monto_objetivo, "El monto objetivo", permitir_cero=False)
        if datos.fecha_objetivo is not None and datos.monto_objetivo is None:
            raise ErrorNegocio("La fecha objetivo solo se puede indicar si hay un monto objetivo.")
        descripcion = datos.descripcion.strip() if datos.descripcion is not None else ""
        return nombre, (descripcion or None)

    @staticmethod
    def _traducir_nombre_repetido(error: errors.UniqueViolation, mensaje: str):
        if error.diag.constraint_name == "uq_bolsillo_nombre_activo":
            raise ErrorNegocio(mensaje) from error
        raise error
