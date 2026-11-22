"""Crea el archivo .env, el rol financia_admin y las bases financia y financia_pruebas.

Lo ejecuta scripts/preparar_windows.ps1; también se puede ejecutar solo.
Necesita la contraseña del superusuario "postgres" en la variable de entorno
FINANCIA_CLAVE_POSTGRES (el script de Windows la pide y la pasa sin guardarla).

Es seguro ejecutarlo varias veces: lo que ya existe no se vuelve a crear y
nunca se borra nada.
"""

import os
import pathlib
import secrets
import sys
from urllib.parse import urlparse

import psycopg
from psycopg import sql
from dotenv import dotenv_values

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ENV = RAIZ / ".env"
BASES = ("financia", "financia_pruebas")
ROL_ADMIN = "financia_admin"


def crear_env() -> None:
    """Crea .env a partir de .env.example con claves aleatorias. No toca un .env existente."""
    if ENV.exists():
        print(".env ya existe: se conserva.")
        return
    texto = (RAIZ / ".env.example").read_text(encoding="utf-8")
    clave_admin = secrets.token_urlsafe(18)
    clave_app = secrets.token_urlsafe(18)
    texto = texto.replace("SECRET_KEY=cambie-esta-clave-por-una-aleatoria", f"SECRET_KEY={secrets.token_hex(32)}")
    texto = texto.replace("financia_admin:CAMBIAR@", f"financia_admin:{clave_admin}@")
    texto = texto.replace("financia_app:CAMBIAR@", f"financia_app:{clave_app}@")
    ENV.write_text(texto, encoding="utf-8")
    print(".env creado con claves aleatorias (no se sube al repositorio).")


def main() -> int:
    clave_postgres = os.environ.get("FINANCIA_CLAVE_POSTGRES")
    if not clave_postgres:
        print("Falta FINANCIA_CLAVE_POSTGRES (contraseña del usuario postgres).")
        return 1

    crear_env()
    url_admin = dotenv_values(ENV)["DATABASE_URL_MIGRACIONES"]
    clave_admin = urlparse(url_admin).password

    try:
        con = psycopg.connect(host="localhost", port=5432, user="postgres",
                              password=clave_postgres, dbname="postgres", autocommit=True)
    except psycopg.OperationalError as error:
        print("No se pudo conectar como postgres. ¿La contraseña es correcta y el servicio está iniciado?")
        print(f"  {error}")
        return 1

    with con:
        existe = con.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROL_ADMIN,)).fetchone()
        accion = "ALTER" if existe else "CREATE"
        con.execute(sql.SQL(accion + " ROLE {} LOGIN PASSWORD {}").format(
            sql.Identifier(ROL_ADMIN), sql.Literal(clave_admin)))
        print(f"Rol {ROL_ADMIN}: {'actualizado' if existe else 'creado'}.")

        for base in BASES:
            if con.execute("SELECT 1 FROM pg_database WHERE datname = %s", (base,)).fetchone():
                print(f"Base {base}: ya existe.")
                continue
            # UTF8 desde template0: requisito de la migración 0001 (lower() con tildes).
            con.execute(sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8' TEMPLATE template0").format(
                sql.Identifier(base), sql.Identifier(ROL_ADMIN)))
            print(f"Base {base}: creada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
