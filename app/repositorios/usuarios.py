"""SQL de la tabla usuario."""

import psycopg

from app.entidades.usuario import Usuario


class UsuarioRepositorio:
    def __init__(self, con: psycopg.Connection):
        self.con = con

    def insertar(self, nombre: str, correo: str, clave_hash: str) -> Usuario:
        fila = self.con.execute(
            """
            INSERT INTO usuario (nombre, correo, clave_hash)
            VALUES (%s, %s, %s)
            RETURNING id_usuario, nombre, correo, clave_hash, activo, creado_en
            """,
            (nombre, correo, clave_hash),
        ).fetchone()
        return Usuario(**fila)

    def obtener(self, id_usuario: int) -> Usuario | None:
        fila = self.con.execute(
            """
            SELECT id_usuario, nombre, correo, clave_hash, activo, creado_en
              FROM usuario
             WHERE id_usuario = %s
            """,
            (id_usuario,),
        ).fetchone()
        return Usuario(**fila) if fila else None

    def obtener_por_correo(self, correo: str) -> Usuario | None:
        """Única consulta que no filtra por id_usuario: al iniciar sesión todavía no se conoce.

        El correo debe llegar ya normalizado (minúsculas, sin espacios): así está guardado (RN-01).
        """
        fila = self.con.execute(
            """
            SELECT id_usuario, nombre, correo, clave_hash, activo, creado_en
              FROM usuario
             WHERE correo = %s
            """,
            (correo,),
        ).fetchone()
        return Usuario(**fila) if fila else None
