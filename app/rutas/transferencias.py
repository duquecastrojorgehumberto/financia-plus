"""Rutas de transferencias con cargos (RF-06, RF-07). Todas exigen sesión.

    POST /api/transferencias                          -> 201 {transferencia}
         {id_cuenta_origen, id_cuenta_destino, monto: "200000", fecha: "2026-11-01", descripcion?,
          cargos?: [{monto: "800", id_categoria, descripcion?}, ...]}
    GET  /api/transferencias/<id>                     -> 200 {transferencia}   con sus cargos
    PUT  /api/transferencias/<id>                     -> 200 {transferencia}   corregir (sin cargos)
         {id_cuenta_origen, id_cuenta_destino, monto, fecha, descripcion?}
    POST /api/transferencias/<id>/anular              -> 200 {transferencia}   con sus cargos (RN-38)
    POST /api/transferencias/<id>/reactivar           -> 200 {transferencia}   solo la transferencia
    POST /api/transferencias/<id>/cargos              -> 201 {transferencia}   agregar un cargo
         {monto, id_categoria, descripcion?}
    PUT  /api/transferencias/<id>/cargos/<id_cargo>   -> 200 {transferencia}   corregir un cargo
         {monto, id_categoria, descripcion?}

Un cargo se anula o reactiva solo con /api/movimientos/<id_cargo>/anular y /reactivar.
Las transferencias aparecen en el historial: GET /api/movimientos?tipo=TRANSFERENCIA.

Cada transferencia en JSON trae sus campos de movimiento, la lista "cargos" y
"total_cargos" (suma de los cargos vigentes).
"""

from flask import Blueprint, jsonify

from app.bd import obtener_conexion
from app.rutas import entrada
from app.servicios.transferencias import DatosCargo, DatosTransferencia, TransferenciaServicio
from app.sesion import requiere_sesion

transferencias_bp = Blueprint("transferencias", __name__, url_prefix="/api/transferencias")

CAMPOS_TRANSFERENCIA = ("id_cuenta_origen", "id_cuenta_destino", "monto", "fecha", "descripcion")
CAMPOS_CARGO = ("monto", "id_categoria", "descripcion")


def _servicio() -> TransferenciaServicio:
    return TransferenciaServicio(obtener_conexion())


def _leer_cargo(datos: dict) -> DatosCargo:
    entrada.solo_campos(datos, *CAMPOS_CARGO)
    return DatosCargo(
        monto=entrada.dinero(datos, "monto"),
        id_categoria=entrada.entero(datos, "id_categoria"),
        descripcion=entrada.texto_opcional(datos, "descripcion"),
    )


def _leer_transferencia(datos: dict, cargos: list[DatosCargo]) -> DatosTransferencia:
    return DatosTransferencia(
        id_cuenta_origen=entrada.entero(datos, "id_cuenta_origen"),
        id_cuenta_destino=entrada.entero(datos, "id_cuenta_destino"),
        monto=entrada.dinero(datos, "monto"),
        fecha=entrada.fecha(datos, "fecha"),
        descripcion=entrada.texto_opcional(datos, "descripcion"),
        cargos=cargos,
    )


@transferencias_bp.post("")
@requiere_sesion
def registrar(id_usuario):
    datos = entrada.leer_cuerpo()
    entrada.solo_campos(datos, *CAMPOS_TRANSFERENCIA, "cargos")
    cargos = [_leer_cargo(c) for c in entrada.lista_de_objetos(datos, "cargos")]
    transferencia = _servicio().registrar(id_usuario, _leer_transferencia(datos, cargos))
    return jsonify(transferencia=transferencia.datos_publicos()), 201


@transferencias_bp.get("/<int:id_transferencia>")
@requiere_sesion
def ver(id_usuario, id_transferencia):
    return jsonify(transferencia=_servicio().obtener(id_usuario, id_transferencia).datos_publicos())


@transferencias_bp.put("/<int:id_transferencia>")
@requiere_sesion
def corregir(id_usuario, id_transferencia):
    datos = entrada.leer_cuerpo()
    entrada.solo_campos(datos, *CAMPOS_TRANSFERENCIA)
    transferencia = _servicio().corregir(id_usuario, id_transferencia, _leer_transferencia(datos, []))
    return jsonify(transferencia=transferencia.datos_publicos())


@transferencias_bp.post("/<int:id_transferencia>/anular")
@requiere_sesion
def anular(id_usuario, id_transferencia):
    return jsonify(transferencia=_servicio().anular(id_usuario, id_transferencia).datos_publicos())


@transferencias_bp.post("/<int:id_transferencia>/reactivar")
@requiere_sesion
def reactivar(id_usuario, id_transferencia):
    return jsonify(transferencia=_servicio().reactivar(id_usuario, id_transferencia).datos_publicos())


@transferencias_bp.post("/<int:id_transferencia>/cargos")
@requiere_sesion
def agregar_cargo(id_usuario, id_transferencia):
    cargo = _leer_cargo(entrada.leer_cuerpo())
    transferencia = _servicio().agregar_cargo(id_usuario, id_transferencia, cargo)
    return jsonify(transferencia=transferencia.datos_publicos()), 201


@transferencias_bp.put("/<int:id_transferencia>/cargos/<int:id_cargo>")
@requiere_sesion
def corregir_cargo(id_usuario, id_transferencia, id_cargo):
    cargo = _leer_cargo(entrada.leer_cuerpo())
    transferencia = _servicio().corregir_cargo(id_usuario, id_transferencia, id_cargo, cargo)
    return jsonify(transferencia=transferencia.datos_publicos())
