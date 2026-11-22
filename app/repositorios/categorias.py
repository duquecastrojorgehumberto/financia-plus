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

    def listar(self, id_usuario: int) -> list[Categoria]:
        """Todas las categorías del usuario: primero las raíces, luego las subcategorías."""
        filas = self.con.execute(
            """
            SELECT id_categoria, id_usuario, id_padre, nombre, tipo, activa, creado_en
              FROM categoria
             WHERE id_usuario = %s
             ORDER BY tipo, id_padre NULLS FIRST, nombre
            """,
            (id_usuario,),
        ).fetchall()
        return [self._a_entidad(f) for f in filas]
