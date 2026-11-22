"""Configuración de la aplicación, leída de las variables de entorno (archivo .env).

Ningún secreto se escribe en el código: SECRET_KEY y DATABASE_URL vienen del
entorno (ARQUITECTURA.md, sección 6). Si falta alguna, la aplicación no
arranca y lo dice con un mensaje claro.
"""

import os
import pathlib
from dataclasses import dataclass

from dotenv import load_dotenv

RAIZ = pathlib.Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Config:
    """Valores que la aplicación necesita para funcionar.

    frozen=True: una vez creada, la configuración no se puede modificar por
    accidente en otra parte del programa.
    """

    secret_key: str      # firma la cookie de sesión
    database_url: str    # conexión con el rol de la aplicación (financia_app)

    @classmethod
    def desde_entorno(cls) -> "Config":
        """Crea la configuración a partir de .env y de las variables del sistema.

        Es un "método de clase": se llama sobre la clase (Config.desde_entorno())
        y devuelve una instancia nueva. Es una forma alternativa de construir el objeto.
        """
        load_dotenv(RAIZ / ".env")
        faltan = [nombre for nombre in ("SECRET_KEY", "DATABASE_URL") if not os.environ.get(nombre)]
        if faltan:
            raise RuntimeError(f"Faltan variables de entorno: {', '.join(faltan)}. Revise el archivo .env.")
        return cls(
            secret_key=os.environ["SECRET_KEY"],
            database_url=os.environ["DATABASE_URL"],
        )
