"""SQL de la tabla categoria."""

import psycopg

from app.entidades.categoria import Categoria, TipoCategoria


class CategoriaRepositorio:
    def __init__(self, con: psycopg.Connection):
        self.con = con

    @staticmethod
    def _a_entidad(fila: dict) -> Categoria:
        """Convierte una fila en Categoria; el tipo pasa de texto a TipoCategoria."""
        return Categoria(**{**fila, "tipo": TipoCategoria(fila["tipo"])})

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------

    def listar(self, id_usuario: int) -> list[Categoria]:
        """Todas las categorías del usuario: primero las raíces, luego las subcategorías."""
        filas = self.con.execute(
            """
            SELECT id_categoria, id_usuario, id_padre, nombre, tipo, activa, creado_en
              FROM categoria
             WHERE id_usuario = %s
             ORDER BY tipo, id_padre NULLS FIRST, lower(nombre)
            """,
            (id_usuario,),
        ).fetchall()
        return [self._a_entidad(f) for f in filas]

    def obtener(self, id_usuario: int, id_categoria: int) -> Categoria | None:
        fila = self.con.execute(
            """
            SELECT id_categoria, id_usuario, id_padre, nombre, tipo, activa, creado_en
              FROM categoria
             WHERE id_usuario = %s
               AND id_categoria = %s
            """,
            (id_usuario, id_categoria),
        ).fetchone()
        return self._a_entidad(fila) if fila else None

    def obtener_para_actualizar(self, id_usuario: int, id_categoria: int) -> Categoria | None:
        """Lee la categoría y bloquea su fila hasta el final de la transacción (FOR UPDATE).

        Mientras esté bloqueada, no se puede insertar un movimiento que la use
        (la revisión de la FK tiene que esperar). Solo tiene sentido dentro de
        "with con.transaction():".
        """
        fila = self.con.execute(
            """
            SELECT id_categoria, id_usuario, id_padre, nombre, tipo, activa, creado_en
              FROM categoria
             WHERE id_usuario = %s
               AND id_categoria = %s
               FOR UPDATE
            """,
            (id_usuario, id_categoria),
        ).fetchone()
        return self._a_entidad(fila) if fila else None

    # ------------------------------------------------------------------
    # Escritura
    # ------------------------------------------------------------------

    def insertar(self, id_usuario: int, nombre: str, tipo: TipoCategoria,
                 id_padre: int | None = None) -> Categoria:
        fila = self.con.execute(
            """
            INSERT INTO categoria (id_usuario, id_padre, nombre, tipo)
            VALUES (%s, %s, %s, %s)
            RETURNING id_categoria, id_usuario, id_padre, nombre, tipo, activa, creado_en
            """,
            (id_usuario, id_padre, nombre, str(tipo)),
        ).fetchone()
        return self._a_entidad(fila)

    def renombrar(self, id_usuario: int, id_categoria: int, nombre: str) -> None:
        """Solo cambia el nombre: el padre y el tipo no cambian nunca (RN-22)."""
        self.con.execute(
            "UPDATE categoria SET nombre = %s WHERE id_usuario = %s AND id_categoria = %s",
            (nombre, id_usuario, id_categoria),
        )

    def cambiar_activa(self, id_usuario: int, id_categoria: int, activa: bool) -> None:
        """Desactivar (False) o reactivar (True). Nunca se borra la fila (RN-25)."""
        self.con.execute(
            "UPDATE categoria SET activa = %s WHERE id_usuario = %s AND id_categoria = %s",
            (activa, id_usuario, id_categoria),
        )

    def desactivar_subcategorias(self, id_usuario: int, id_padre: int) -> int:
        """Desactiva las subcategorías activas de un padre. Devuelve cuántas cambió."""
        cursor = self.con.execute(
            """
            UPDATE categoria
               SET activa = false
             WHERE id_usuario = %s
               AND id_padre = %s
               AND activa
            """,
            (id_usuario, id_padre),
        )
        return cursor.rowcount
