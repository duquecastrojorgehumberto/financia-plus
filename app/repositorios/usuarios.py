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

    def cambiar_clave_hash(self, id_usuario: int, clave_hash: str) -> None:
        """Reemplaza el hash de la contraseña. Nunca recibe la contraseña misma (RN-02)."""
        self.con.execute(
            "UPDATE usuario SET clave_hash = %s WHERE id_usuario = %s",
            (clave_hash, id_usuario),
        )

    def listar_todos(self) -> list[Usuario]:
        """Todos los usuarios, del más antiguo al más nuevo.

        Como obtener_por_correo, no filtra por id_usuario: la usa SOLO el script de
        administración scripts/cambiar_clave.py (para quien olvidó con qué correo se
        registró), nunca una ruta de la API.
        """
        filas = self.con.execute(
            """
            SELECT id_usuario, nombre, correo, clave_hash, activo, creado_en
              FROM usuario
             ORDER BY creado_en, id_usuario
            """
        ).fetchall()
        return [Usuario(**f) for f in filas]
