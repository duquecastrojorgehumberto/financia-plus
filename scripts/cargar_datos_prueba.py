"""Carga db/semillas/datos_prueba.sql en una base de DESARROLLO (Tarea 15).

Uso (desde la carpeta del proyecto, con el entorno virtual):
    python scripts/cargar_datos_prueba.py                        # base principal (DATABASE_URL)
    python scripts/cargar_datos_prueba.py --variable OTRA_URL    # otra base

Cómo funciona
  * Se conecta con la URL de la variable indicada. Por defecto DATABASE_URL,
    es decir, con el rol de la aplicación (financia_app): el archivo solo
    tiene INSERT, así que no necesita más permisos.
  * Si los usuarios de demostración ya existen, no hace nada (se puede
    ejecutar varias veces sin duplicar).
  * Ejecuta el archivo completo en UNA transacción: o se cargan todos los
    datos o ninguno. Igual que scripts/migrar.py, quita las líneas "BEGIN;"
    y "COMMIT;" del archivo y abre él mismo la transacción.
  * Nunca borra nada.

No lo ejecute sobre la base de pruebas automáticas (financia_pruebas): las
pruebas cargan este archivo por su cuenta y lo deshacen al terminar.
"""

import argparse
import os
import pathlib
import re
import sys

import psycopg
from dotenv import load_dotenv

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ARCHIVO = RAIZ / "db" / "semillas" / "datos_prueba.sql"
LINEA_TRANSACCION = re.compile(r"^\s*(BEGIN|COMMIT)\s*;\s*$", re.IGNORECASE | re.MULTILINE)
CORREOS = ("ana@demo.example", "beto@demo.example", "carla@demo.example")


def sql_sin_transaccion() -> str:
    """El contenido del archivo sin las líneas BEGIN; y COMMIT; (las pruebas también lo usan)."""
    return LINEA_TRANSACCION.sub("", ARCHIVO.read_text(encoding="utf-8"))


def main() -> int:
    load_dotenv(RAIZ / ".env")
    parser = argparse.ArgumentParser(description="Carga los datos de prueba en una base de desarrollo.")
    parser.add_argument("--variable", default="DATABASE_URL",
                        help="variable de entorno con la URL de la base (por defecto DATABASE_URL)")
    args = parser.parse_args()

    url = os.environ.get(args.variable)
    if not url:
        print(f"Falta la variable {args.variable} (revise el archivo .env).")
        return 1

    with psycopg.connect(url) as con:
        ya = con.execute("SELECT count(*) FROM usuario WHERE correo = ANY(%s)", (list(CORREOS),)).fetchone()[0]
        if ya:
            print("Los datos de prueba ya están cargados en esta base: no se hizo nada.")
            return 0
        try:
            with con.transaction():
                con.execute(sql_sin_transaccion())
        except psycopg.Error as error:
            print("ERROR: no se cargó nada (la transacción se deshizo completa).")
            print(f"  {error}")
            return 1

    print("Datos de prueba cargados.")
    print("Usuarios: ana@demo.example, beto@demo.example, carla@demo.example")
    print("Contraseña de los tres (solo para esta demostración local): demo-financia-2026")
    print("Qué debe verse en cada uno: comentarios al inicio de db/semillas/datos_prueba.sql")
    return 0


if __name__ == "__main__":
    sys.exit(main())
