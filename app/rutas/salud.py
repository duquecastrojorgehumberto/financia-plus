"""GET /api/salud: dice si la API está viva y si hay conexión con la base.

Sirve para comprobar rápido que todo está bien conectado (por ejemplo, al
arrancar el servidor o desde la interfaz React).

    200  {"bd": "ok"}      la base respondió
    503  {"bd": "error"}   no hay conexión (el detalle técnico va al registro del servidor)
"""

import psycopg
from flask import Blueprint, current_app, jsonify

from app.bd import obtener_conexion

salud_bp = Blueprint("salud", __name__, url_prefix="/api")


@salud_bp.get("/salud")
def salud():
    try:
        bd = current_app.extensions["financia_bd"]
        bd.esta_disponible(obtener_conexion())
    except psycopg.Error as error:
        current_app.logger.error("Sin conexión con la base de datos: %s", error)
        return jsonify(bd="error"), 503
    return jsonify(bd="ok")
