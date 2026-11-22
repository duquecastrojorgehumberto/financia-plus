"""Aplica en orden las migraciones pendientes de db/migraciones/ (Tarea 2).

Uso (desde la carpeta del proyecto, con el entorno virtual activo):
    python scripts/migrar.py                           # base principal (DATABASE_URL_MIGRACIONES)
    python scripts/migrar.py --variable DATABASE_URL_PRUEBAS   # base de pruebas

Cómo funciona
  * Crea, si no existe, la tabla de control migracion_aplicada (D-19). Es
    infraestructura: no forma parte de las seis tablas del modelo.
  * Recorre los archivos .sql en orden alfabético (0001_, 0002_, ...) y aplica
    los que no estén registrados.
  * Cada migración y su registro van en UNA transacción: o queda aplicada y
    anotada, o no queda nada. Por eso el script quita las líneas "BEGIN;" y
    "COMMIT;" del archivo (existen para poder ejecutarlo a mano con psql) y
    abre él mismo la transacción.
  * Se detiene en el primer error. Nunca borra nada.
"""

import argparse
import os
import pathlib
import re
import sys

import psycopg
from dotenv import load_dotenv

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "db" / "migraciones"

# Solo líneas que contienen exactamente BEGIN; o COMMIT; (con espacios opcionales).
LINEA_TRANSACCION = re.compile(r"^\s*(BEGIN|COMMIT)\s*;\s*$", re.IGNORECASE | re.MULTILINE)


def main() -> int:
    load_dotenv(RAIZ / ".env")
    parser = argparse.ArgumentParser(description="Aplica las migraciones pendientes.")
    parser.add_argument("--variable", default="DATABASE_URL_MIGRACIONES",
                        help="variable de entorno con la URL de la base (por defecto DATABASE_URL_MIGRACIONES)")
    args = parser.parse_args()

    url = os.environ.get(args.variable)
    if not url:
        print(f"Falta la variable {args.variable} (revise el archivo .env).")
        return 1

    archivos = sorted(CARPETA.glob("*.sql"))
    with psycopg.connect(url, autocommit=True) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS migracion_aplicada (
              nombre      text        PRIMARY KEY,
              aplicada_en timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        aplicadas = {fila[0] for fila in con.execute("SELECT nombre FROM migracion_aplicada")}
        pendientes = [a for a in archivos if a.name not in aplicadas]

        if not pendientes:
            print(f"[{args.variable}] No hay migraciones pendientes.")
            return 0

        for archivo in pendientes:
            sql = LINEA_TRANSACCION.sub("", archivo.read_text(encoding="utf-8"))
            print(f"[{args.variable}] Aplicando {archivo.name} ...", end=" ")
            try:
                with con.transaction():
                    con.execute(sql)
                    con.execute("INSERT INTO migracion_aplicada (nombre) VALUES (%s)", (archivo.name,))
            except psycopg.Error as error:
                print("ERROR")
                print(f"  {error}")
                print("  La migración no se aplicó (se deshizo completa). Corrija el archivo y vuelva a ejecutar.")
                return 1
            print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
