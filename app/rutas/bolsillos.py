"""Rutas de bolsillos y metas (RF-08, RF-09, RF-10, RF-12). Todas exigen sesión.

    GET  /api/bolsillos                     -> 200 {bolsillos: [...]}   solo activos
    GET  /api/bolsillos?archivados=1        -> 200 {bolsillos: [...]}   también los archivados
    POST /api/bolsillos                     -> 201 {bolsillo}
         {nombre, descripcion?, monto_objetivo?, fecha_objetivo?, valor?}
         sin monto_objetivo: bolsillo genérico; valor: el primer valor (por defecto "0")
    GET  /api/bolsillos/<id>                -> 200 {bolsillo, historial: [{valor, registrado_en}, ...]}
    PUT  /api/bolsillos/<id>                -> 200 {bolsillo}
         {nombre, descripcion?, monto_objetivo?, fecha_objetivo?}   (el valor NO va aquí)
    POST /api/bolsillos/<id>/valor          -> 201 {bolsillo, registrado: true}    valor nuevo
                                            -> 200 {bolsillo, registrado: false}   era igual (RN-46)
         {valor: "350000"}
    POST /api/bolsillos/<id>/archivar       -> 200 {bolsillo}
    POST /api/bolsillos/<id>/reactivar      -> 200 {bolsillo}

Cada bolsillo en JSON trae "valor_actual", "es_meta" y "progreso_porcentaje"
("35.00"; null si no es meta). Un bolsillo de otro usuario responde 404 (RN-06).
"""

from decimal import Decimal

from flask import Blueprint, jsonify, request

from app.bd import obtener_conexion
from app.rutas import entrada
from app.servicios.bolsillos import BolsilloServicio, DatosBolsillo
from app.sesion import requiere_sesion

bolsillos_bp = Blueprint("bolsillos", __name__, url_prefix="/api/bolsillos")

CAMPOS_DATOS = ("nombre", "descripcion", "monto_objetivo", "fecha_objetivo")


def _servicio() -> BolsilloServicio:
    return BolsilloServicio(obtener_conexion())


def _leer_datos(datos: dict) -> DatosBolsillo:
    return DatosBolsillo(
        nombre=entrada.texto(datos, "nombre"),
        descripcion=entrada.texto_opcional(datos, "descripcion"),
        monto_objetivo=entrada.dinero_opcional(datos, "monto_objetivo"),
        fecha_objetivo=entrada.fecha_opcional(datos, "fecha_objetivo"),
    )


@bolsillos_bp.get("")
@requiere_sesion
def listar(id_usuario):
    incluir_archivados = request.args.get("archivados", "").lower() in ("1", "true", "si", "sí")
    return jsonify(bolsillos=[b.datos_publicos() for b in _servicio().listar(id_usuario, incluir_archivados)])


@bolsillos_bp.post("")
@requiere_sesion
def crear(id_usuario):
    datos = entrada.leer_cuerpo()
    entrada.solo_campos(datos, *CAMPOS_DATOS, "valor")
    valor = entrada.dinero_opcional(datos, "valor")
    bolsillo = _servicio().crear(id_usuario, _leer_datos(datos), valor if valor is not None else Decimal("0"))
    return jsonify(bolsillo=bolsillo.datos_publicos()), 201


@bolsillos_bp.get("/<int:id_bolsillo>")
@requiere_sesion
def ver(id_usuario, id_bolsillo):
    servicio = _servicio()
    bolsillo = servicio.obtener(id_usuario, id_bolsillo)
    historial = servicio.historial(id_usuario, id_bolsillo)
    return jsonify(bolsillo=bolsillo.datos_publicos(), historial=[v.datos_publicos() for v in historial])


@bolsillos_bp.put("/<int:id_bolsillo>")
@requiere_sesion
def editar(id_usuario, id_bolsillo):
    datos = entrada.leer_cuerpo()
    # El valor se cambia en /valor, para que cada cambio quede en el historial (RN-44).
    entrada.solo_campos(datos, *CAMPOS_DATOS)
    bolsillo = _servicio().editar(id_usuario, id_bolsillo, _leer_datos(datos))
    return jsonify(bolsillo=bolsillo.datos_publicos())


@bolsillos_bp.post("/<int:id_bolsillo>/valor")
@requiere_sesion
def cambiar_valor(id_usuario, id_bolsillo):
    datos = entrada.leer_cuerpo()
    entrada.solo_campos(datos, "valor")
    bolsillo, registrado = _servicio().cambiar_valor(id_usuario, id_bolsillo, entrada.dinero(datos, "valor"))
    return jsonify(bolsillo=bolsillo.datos_publicos(), registrado=registrado), (201 if registrado else 200)


@bolsillos_bp.post("/<int:id_bolsillo>/archivar")
@requiere_sesion
def archivar(id_usuario, id_bolsillo):
    return jsonify(bolsillo=_servicio().archivar(id_usuario, id_bolsillo).datos_publicos())


@bolsillos_bp.post("/<int:id_bolsillo>/reactivar")
@requiere_sesion
def reactivar(id_usuario, id_bolsillo):
    return jsonify(bolsillo=_servicio().reactivar(id_usuario, id_bolsillo).datos_publicos())
