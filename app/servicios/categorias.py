"""Categorías: crear, renombrar, desactivar, reactivar y listar como árbol (RF-03).

Reglas que aplica
  RN-20  Tipo INGRESO o EGRESO.
  RN-21  Máximo dos niveles: el padre de una subcategoría debe ser raíz. La
         base no lo impide (prueba test_limite_conocido_la_base_acepta_un_tercer_nivel);
         lo impide este servicio, que es el único camino para crear categorías.
  RN-22  El padre y el tipo no cambian: el único cambio posible es el nombre.
  RN-23  La subcategoría toma el tipo de su padre (la base lo exige con una FK).
  RN-24  Nombre único entre hermanas activas (lo garantiza la base; aquí se
         traduce el error).
  RN-25  No se borra: se desactiva. Desactivar una raíz desactiva también sus
         subcategorías, en la misma transacción.
  RN-06  Una categoría de otro usuario responde igual que una inexistente.
"""

import psycopg
from psycopg import errors

from app.entidades.categoria import Categoria, RamaCategoria, TipoCategoria
from app.errores import ErrorNegocio, NoEncontrado
from app.repositorios.categorias import CategoriaRepositorio

MENSAJE_NOMBRE_REPETIDO = "Ya existe una categoría activa con ese nombre en el mismo nivel."


class CategoriaServicio:
    def __init__(self, con: psycopg.Connection):
        self.con = con
        self.categorias = CategoriaRepositorio(con)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def listar_arbol(self, id_usuario: int, tipo: str | None = None,
                     incluir_inactivas: bool = False) -> list[RamaCategoria]:
        """Las categorías como árbol: cada raíz con sus subcategorías.

        Sin incluir_inactivas, solo aparecen las activas (las que se pueden usar
        en un movimiento nuevo).
        """
        tipo_filtro = self._tipo_valido(tipo) if tipo is not None else None
        ramas: dict[int, RamaCategoria] = {}
        for c in self.categorias.listar(id_usuario):   # vienen primero las raíces
            if tipo_filtro is not None and c.tipo != tipo_filtro:
                continue
            if not incluir_inactivas and not c.activa:
                continue
            if c.es_subcategoria():
                rama = ramas.get(c.id_padre)
                if rama is not None:                   # su raíz pasó los filtros
                    rama.subcategorias.append(c)
            else:
                ramas[c.id_categoria] = RamaCategoria(raiz=c)
        return list(ramas.values())

    def obtener(self, id_usuario: int, id_categoria: int) -> Categoria:
        categoria = self.categorias.obtener(id_usuario, id_categoria)
        if categoria is None:
            raise NoEncontrado("No se encontró la categoría.")
        return categoria

    # ------------------------------------------------------------------
    # Acciones: cada una es UNA transacción
    # ------------------------------------------------------------------

    def crear(self, id_usuario: int, nombre: str, tipo: str | None = None,
              id_padre: int | None = None) -> Categoria:
        """Crea una raíz (con tipo) o una subcategoría (con id_padre; el tipo sale del padre)."""
        nombre = self._nombre_valido(nombre)
        try:
            with self.con.transaction():
                if id_padre is None:
                    if tipo is None:
                        raise ErrorNegocio("Indique el tipo de la categoría: INGRESO o EGRESO.")
                    tipo_categoria = self._tipo_valido(tipo)
                else:
                    padre = self.categorias.obtener_para_actualizar(id_usuario, id_padre)
                    if padre is None:
                        raise NoEncontrado("No se encontró la categoría padre.")
                    if padre.es_subcategoria():
                        raise ErrorNegocio("Solo hay dos niveles: una subcategoría no puede tener "
                                           "subcategorías.")
                    if not padre.activa:
                        raise ErrorNegocio("La categoría padre está desactivada.")
                    if tipo is not None and self._tipo_valido(tipo) != padre.tipo:
                        raise ErrorNegocio(f"Una subcategoría tiene el tipo de su padre ({padre.tipo}).")
                    tipo_categoria = padre.tipo
                categoria = self.categorias.insertar(id_usuario, nombre, tipo_categoria, id_padre)
        except errors.UniqueViolation as error:
            self._traducir_nombre_repetido(error, MENSAJE_NOMBRE_REPETIDO)
        return categoria

    def renombrar(self, id_usuario: int, id_categoria: int, nombre: str) -> Categoria:
        """RN-22: el nombre es lo único que cambia."""
        nombre = self._nombre_valido(nombre)
        try:
            with self.con.transaction():
                categoria = self._bloquear(id_usuario, id_categoria)
                if not categoria.activa:
                    raise ErrorNegocio("La categoría está desactivada. Reactívela para cambiarle el nombre.")
                self.categorias.renombrar(id_usuario, id_categoria, nombre)
        except errors.UniqueViolation as error:
            self._traducir_nombre_repetido(error, MENSAJE_NOMBRE_REPETIDO)
        return self.obtener(id_usuario, id_categoria)

    def desactivar(self, id_usuario: int, id_categoria: int) -> tuple[Categoria, int]:
        """RN-25, CA-14. Devuelve la categoría y cuántas subcategorías se desactivaron con ella.

        Sus movimientos no cambian: siguen en el historial y en los totales.
        """
        with self.con.transaction():
            categoria = self._bloquear(id_usuario, id_categoria)
            if not categoria.activa:
                raise ErrorNegocio("La categoría ya está desactivada.")
            self.categorias.cambiar_activa(id_usuario, id_categoria, False)
            subcategorias = 0
            if not categoria.es_subcategoria():
                subcategorias = self.categorias.desactivar_subcategorias(id_usuario, id_categoria)
        return self.obtener(id_usuario, id_categoria), subcategorias

    def reactivar(self, id_usuario: int, id_categoria: int) -> Categoria:
        """Reactiva solo esta categoría. Una subcategoría necesita a su padre activo.

        Orden de los bloqueos: siempre primero el padre y después la hija, igual
        que desactivar(). Si dos transacciones bloquearan en orden contrario,
        cada una podría quedarse esperando a la otra (deadlock).
        """
        try:
            with self.con.transaction():
                id_padre = self.obtener(id_usuario, id_categoria).id_padre   # no cambia nunca (RN-22)
                padre = self._bloquear(id_usuario, id_padre) if id_padre is not None else None
                categoria = self._bloquear(id_usuario, id_categoria)
                if categoria.activa:
                    raise ErrorNegocio("La categoría ya está activa.")
                if padre is not None and not padre.activa:
                    raise ErrorNegocio("Primero reactive la categoría padre.")
                self.categorias.cambiar_activa(id_usuario, id_categoria, True)
        except errors.UniqueViolation as error:
            self._traducir_nombre_repetido(error, "Ya existe otra categoría activa con ese nombre en el "
                                                  "mismo nivel. Cámbiele el nombre a esa antes de "
                                                  "reactivar esta.")
        return self.obtener(id_usuario, id_categoria)

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _bloquear(self, id_usuario: int, id_categoria: int) -> Categoria:
        categoria = self.categorias.obtener_para_actualizar(id_usuario, id_categoria)
        if categoria is None:
            raise NoEncontrado("No se encontró la categoría.")
        return categoria

    @staticmethod
    def _nombre_valido(nombre: str) -> str:
        nombre = nombre.strip()
        if not nombre:
            raise ErrorNegocio("El nombre de la categoría es obligatorio.")
        return nombre

    @staticmethod
    def _tipo_valido(tipo: str) -> TipoCategoria:
        try:
            return TipoCategoria(tipo)
        except ValueError:
            raise ErrorNegocio("El tipo de categoría debe ser INGRESO o EGRESO.") from None

    @staticmethod
    def _traducir_nombre_repetido(error: errors.UniqueViolation, mensaje: str):
        """Si el error es del índice de nombres entre hermanas activas, lo cambia por un
        mensaje en español; cualquier otro error se vuelve a lanzar tal cual."""
        if error.diag.constraint_name == "uq_categoria_hermanas_activas":
            raise ErrorNegocio(mensaje) from error
        raise error
