"""Registro e inicio de sesión de usuarios (RF-01).

Reglas que aplica
  RN-01  El correo se guarda en minúsculas y sin espacios; no se repite.
  RN-02  La contraseña se guarda solo como hash (utilidades de Werkzeug).
  RN-26  Al registrarse, el usuario recibe sus categorías por defecto, en la
         MISMA transacción: o queda el usuario con todas sus categorías, o no
         queda nada.

Restablecer una contraseña olvidada (restablecer_clave) no es una pantalla de la
interfaz: lo usa quien administra la base, con scripts/cambiar_clave.py. Como la
contraseña solo se guarda como hash, no se puede "recuperar": se reemplaza por una nueva.

Este servicio no sabe nada de HTTP ni de la sesión del navegador: recibe
datos, devuelve un Usuario o lanza un ErrorNegocio. La ruta decide qué hacer
con eso.
"""

import psycopg
from psycopg import errors
from werkzeug.security import check_password_hash, generate_password_hash

from app.entidades.usuario import Usuario
from app.errores import ErrorNegocio, NoAutenticado, NoEncontrado
from app.repositorios.categorias import CategoriaRepositorio
from app.repositorios.usuarios import UsuarioRepositorio
from app.servicios.categorias_por_defecto import CATEGORIAS_POR_DEFECTO

LONGITUD_MINIMA_CLAVE = 8
MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos."


class AutenticacionServicio:
    def __init__(self, con: psycopg.Connection):
        self.con = con
        self.usuarios = UsuarioRepositorio(con)
        self.categorias = CategoriaRepositorio(con)

    # ------------------------------------------------------------------
    # Métodos públicos: cada uno es una acción del usuario.
    # ------------------------------------------------------------------

    def registrar(self, nombre: str, correo: str, clave: str) -> Usuario:
        """Crea el usuario y sus categorías por defecto en UNA transacción (RN-26)."""
        nombre = nombre.strip()
        correo = self._normalizar_correo(correo)
        self._validar_datos_de_registro(nombre, correo, clave)

        try:
            with self.con.transaction():
                usuario = self.usuarios.insertar(nombre, correo, generate_password_hash(clave))
                self._copiar_categorias_por_defecto(usuario.id_usuario)
        except errors.UniqueViolation as error:
            # Dos registros simultáneos con el mismo correo: la base tiene la última palabra (RN-01).
            if error.diag.constraint_name == "uq_usuario_correo":
                raise ErrorNegocio("Ya existe un usuario con ese correo.") from error
            raise
        return usuario

    def iniciar_sesion(self, correo: str, clave: str) -> Usuario:
        """Devuelve el usuario si el correo y la contraseña son correctos.

        Si el correo no existe, el usuario está desactivado o la contraseña no
        coincide, el mensaje es el mismo: así no se revela qué correos están
        registrados.
        """
        usuario = self.usuarios.obtener_por_correo(self._normalizar_correo(correo))
        if usuario is None or not usuario.activo or not check_password_hash(usuario.clave_hash, clave):
            raise NoAutenticado(MENSAJE_CREDENCIALES)
        return usuario

    def restablecer_clave(self, correo: str, nueva_clave: str) -> Usuario:
        """Reemplaza la contraseña del usuario de ese correo (RN-02: se guarda solo su hash).

        Misma regla que al registrarse: al menos 8 caracteres. Herramienta de
        administración: a diferencia de iniciar_sesion, sí dice si el correo no existe.
        """
        self._validar_clave(nueva_clave)
        with self.con.transaction():
            usuario = self.usuarios.obtener_por_correo(self._normalizar_correo(correo))
            if usuario is None:
                raise NoEncontrado("No hay ningún usuario con ese correo.")
            self.usuarios.cambiar_clave_hash(usuario.id_usuario, generate_password_hash(nueva_clave))
        return usuario

    def listar_usuarios(self) -> list[Usuario]:
        """Nombre y correo de todos los usuarios, para quien olvidó con qué correo se registró."""
        return self.usuarios.listar_todos()

    def obtener_usuario_activo(self, id_usuario: int) -> Usuario:
        """El usuario de la sesión. Si ya no existe o está desactivado, la sesión no vale."""
        usuario = self.usuarios.obtener(id_usuario)
        if usuario is None or not usuario.activo:
            raise NoAutenticado()
        return usuario

    # ------------------------------------------------------------------
    # Métodos internos (el guion bajo indica que solo los usa esta clase).
    # ------------------------------------------------------------------

    @staticmethod
    def _normalizar_correo(correo: str) -> str:
        """RN-01: minúsculas y sin espacios alrededor, igual que exige ck_usuario_correo."""
        return correo.strip().lower()

    def _validar_datos_de_registro(self, nombre: str, correo: str, clave: str) -> None:
        if not nombre:
            raise ErrorNegocio("El nombre es obligatorio.")
        parte_local, arroba, dominio = correo.partition("@")
        if not parte_local or not arroba or "." not in dominio or " " in correo:
            raise ErrorNegocio("El correo no es válido.")
        self._validar_clave(clave)
        if self.usuarios.obtener_por_correo(correo) is not None:
            raise ErrorNegocio("Ya existe un usuario con ese correo.")

    @staticmethod
    def _validar_clave(clave: str) -> None:
        """La misma regla al registrarse y al restablecer la contraseña."""
        if len(clave) < LONGITUD_MINIMA_CLAVE:
            raise ErrorNegocio(f"La contraseña debe tener al menos {LONGITUD_MINIMA_CLAVE} caracteres.")

    def _copiar_categorias_por_defecto(self, id_usuario: int) -> None:
        """Inserta cada categoría raíz y, con su id, sus subcategorías (mismo tipo, RN-23)."""
        for tipo, categorias in CATEGORIAS_POR_DEFECTO.items():
            for nombre_raiz, subcategorias in categorias:
                raiz = self.categorias.insertar(id_usuario, nombre_raiz, tipo)
                for nombre_sub in subcategorias:
                    self.categorias.insertar(id_usuario, nombre_sub, tipo, id_padre=raiz.id_categoria)
