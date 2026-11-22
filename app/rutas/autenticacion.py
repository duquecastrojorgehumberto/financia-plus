"""Rutas de autenticación (RF-01).

    POST   /api/registro   {nombre, correo, clave}  -> 201 {usuario}   y deja la sesión iniciada
    POST   /api/sesion     {correo, clave}          -> 200 {usuario}   inicia sesión
    GET    /api/sesion                               -> 200 {usuario}   quién tiene la sesión (401 si nadie)
    DELETE /api/sesion                               -> 200 {mensaje}   cierra sesión

Como toda petición que modifica datos, POST y DELETE deben enviarse en JSON y
con el encabezado X-Requested-With: financia (app/csrf.py). DELETE puede
llevar un cuerpo vacío: {}.

Cada ruta: lee y valida la forma de los datos, llama a UN método del servicio
y responde JSON. No hay SQL ni reglas de negocio aquí.
"""

from flask import Blueprint, jsonify

from app import sesion
from app.bd import obtener_conexion
from app.errores import NoAutenticado
from app.rutas.entrada import leer_textos
from app.servicios.autenticacion import AutenticacionServicio

autenticacion_bp = Blueprint("autenticacion", __name__, url_prefix="/api")


@autenticacion_bp.post("/registro")
def registrar():
    datos = leer_textos("nombre", "correo", "clave")
    usuario = AutenticacionServicio(obtener_conexion()).registrar(
        datos["nombre"], datos["correo"], datos["clave"])
    sesion.iniciar(usuario)
    return jsonify(usuario=usuario.datos_publicos()), 201


@autenticacion_bp.post("/sesion")
def iniciar_sesion():
    datos = leer_textos("correo", "clave")
    usuario = AutenticacionServicio(obtener_conexion()).iniciar_sesion(datos["correo"], datos["clave"])
    sesion.iniciar(usuario)
    return jsonify(usuario=usuario.datos_publicos())


@autenticacion_bp.get("/sesion")
@sesion.requiere_sesion
def ver_sesion(id_usuario):
    try:
        usuario = AutenticacionServicio(obtener_conexion()).obtener_usuario_activo(id_usuario)
    except NoAutenticado:
        sesion.cerrar()   # la cookie apunta a un usuario que ya no puede entrar
        raise
    return jsonify(usuario=usuario.datos_publicos())


@autenticacion_bp.delete("/sesion")
def cerrar_sesion():
    sesion.cerrar()
    return jsonify(mensaje="Sesión cerrada.")
