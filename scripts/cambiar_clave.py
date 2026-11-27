r"""Cambia la contraseña de un usuario que la olvidó (herramienta de administración).

Uso (desde la carpeta del proyecto, en PowerShell):
    .venv\Scripts\python scripts\cambiar_clave.py                 pide el correo y la contraseña nueva
    .venv\Scripts\python scripts\cambiar_clave.py ana@correo.com  pide solo la contraseña nueva
    .venv\Scripts\python scripts\cambiar_clave.py --listar        muestra el nombre y el correo de cada usuario

Por qué no "recupera" la contraseña
    La base no guarda la contraseña, solo su hash (RN-02): un resultado que no se puede
    deshacer. Por eso nadie puede ver una contraseña olvidada; lo único posible es
    poner una nueva. Este script la pide dos veces, sin mostrarla en pantalla
    (getpass), y guarda su hash con el mismo servicio que usa la aplicación.

Cómo se conecta
    Con la URL de la variable DATABASE_URL del archivo .env (el rol de la aplicación,
    financia_app, que puede modificar la tabla usuario). --variable usa otra variable.
"""

import argparse
import getpass
import os
import pathlib
import sys

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))   # para poder importar app/ al ejecutar el script directamente

from app.errores import ErrorNegocio, NoEncontrado  # noqa: E402
from app.servicios.autenticacion import AutenticacionServicio  # noqa: E402


def main(argumentos: list[str] | None = None) -> int:
    load_dotenv(RAIZ / ".env")
    parser = argparse.ArgumentParser(description="Cambia la contraseña de un usuario de FINANCIA+.")
    parser.add_argument("correo", nargs="?", help="correo del usuario (si no se da, se pregunta)")
    parser.add_argument("--listar", action="store_true", help="mostrar el nombre y el correo de cada usuario")
    parser.add_argument("--variable", default="DATABASE_URL",
                        help="variable de entorno con la URL de la base (por defecto DATABASE_URL)")
    args = parser.parse_args(argumentos)

    url = os.environ.get(args.variable)
    if not url:
        print(f"Falta la variable {args.variable} (revise el archivo .env).")
        return 1

    try:
        con = psycopg.connect(url, autocommit=True, row_factory=dict_row, connect_timeout=5)
    except psycopg.OperationalError:
        print("No se pudo conectar con la base de datos. ¿Está encendido PostgreSQL?")
        return 1

    with con:
        servicio = AutenticacionServicio(con)
        if args.listar:
            usuarios = servicio.listar_usuarios()
            if not usuarios:
                print("No hay usuarios registrados.")
            for u in usuarios:
                estado = "" if u.activo else "  (desactivado)"
                print(f"{u.nombre:<25} {u.correo}{estado}")
            return 0

        correo = args.correo or input("Correo del usuario: ")
        nueva = getpass.getpass("Contraseña nueva (no se ve al escribirla): ")
        if nueva != getpass.getpass("Repítala: "):
            print("Las dos contraseñas no coinciden: no se cambió nada.")
            return 1
        try:
            usuario = servicio.restablecer_clave(correo, nueva)
        except (ErrorNegocio, NoEncontrado) as error:
            print(f"{error} No se cambió nada.")
            return 1

    print(f"Listo: la contraseña de {usuario.nombre} ({usuario.correo}) se cambió.")
    print("Ya puede iniciar sesión con la contraseña nueva.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
