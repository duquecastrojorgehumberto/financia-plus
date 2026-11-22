"""Entidad Usuario: una fila de la tabla usuario (MODELO_DATOS.md, sección 4.1)."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Usuario:
    id_usuario: int
    nombre: str
    correo: str
    # repr=False: si alguien imprime el objeto (por ejemplo en un registro de errores),
    # el hash de la contraseña no aparece.
    clave_hash: str = field(repr=False)
    activo: bool
    creado_en: datetime

    def datos_publicos(self) -> dict:
        """Lo que se puede enviar al navegador. Nunca incluye clave_hash (RN-02)."""
        return {"id_usuario": self.id_usuario, "nombre": self.nombre, "correo": self.correo}
