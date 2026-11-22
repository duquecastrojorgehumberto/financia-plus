"""Rutas de cuentas (RF-02, RF-11). Todas exigen sesión.

    GET  /api/cuentas                      -> 200 {cuentas: [...]}   solo activas
    GET  /api/cuentas?archivadas=1         -> 200 {cuentas: [...]}   activas y archivadas
    POST /api/cuentas                      -> 201 {cuenta}           {nombre, tipo, saldo_inicial?}
    GET  /api/cuentas/<id>                 -> 200 {cuenta}
    PUT  /api/cuentas/<id>                 -> 200 {cuenta}           {nombre, tipo, saldo_inicial}
    POST /api/cuentas/<id>/archivar        -> 200 {cuenta}           solo con saldo 0 (CA-15)
    POST /api/cuentas/<id>/reactivar       -> 200 {cuenta}

Cada cuenta en JSON trae su saldo calculado como texto ("130000.00") y
"saldo_negativo" para mostrar el aviso de RN-14. Una cuenta de otro usuario
responde 404, igual que una que no existe (RN-06).

El id_usuario sale de la sesión (@requiere_sesion), nunca del cuerpo ni de la URL (RN-05).
"""

from decimal import Decimal

from flask import Blueprint, jsonify, request

from app.bd import obtener_conexion
from app.rutas import entrada
from app.servicios.cuentas import CuentaServicio
from app.sesion import requiere_sesion

cuentas_bp = Blueprint("cuentas", __name__, url_prefix="/api/cuentas")


def _servicio() -> CuentaServicio:
    return CuentaServicio(obtener_conexion())


@cuentas_bp.get("")
@requiere_sesion
def listar(id_usuario):
    incluir_archivadas = request.args.get("archivadas", "").lower() in ("1", "true", "si", "sí")
    cuentas = _servicio().listar(id_usuario, incluir_archivadas)
    return jsonify(cuentas=[c.datos_publicos() for c in cuentas])


@cuentas_bp.post("")
@requiere_sesion
def crear(id_usuario):
    datos = entrada.leer_cuerpo()
    saldo_inicial = entrada.dinero(datos, "saldo_inicial") if "saldo_inicial" in datos else Decimal("0")
    cuenta = _servicio().crear(id_usuario, entrada.texto(datos, "nombre"), entrada.texto(datos, "tipo"),
                               saldo_inicial)
    return jsonify(cuenta=cuenta.datos_publicos()), 201


@cuentas_bp.get("/<int:id_cuenta>")
@requiere_sesion
def ver(id_usuario, id_cuenta):
    return jsonify(cuenta=_servicio().obtener(id_usuario, id_cuenta).datos_publicos())


@cuentas_bp.put("/<int:id_cuenta>")
@requiere_sesion
def editar(id_usuario, id_cuenta):
    datos = entrada.leer_cuerpo()
    cuenta = _servicio().editar(id_usuario, id_cuenta, entrada.texto(datos, "nombre"),
                                entrada.texto(datos, "tipo"), entrada.dinero(datos, "saldo_inicial"))
    return jsonify(cuenta=cuenta.datos_publicos())


@cuentas_bp.post("/<int:id_cuenta>/archivar")
@requiere_sesion
def archivar(id_usuario, id_cuenta):
    return jsonify(cuenta=_servicio().archivar(id_usuario, id_cuenta).datos_publicos())


@cuentas_bp.post("/<int:id_cuenta>/reactivar")
@requiere_sesion
def reactivar(id_usuario, id_cuenta):
    return jsonify(cuenta=_servicio().reactivar(id_usuario, id_cuenta).datos_publicos())
