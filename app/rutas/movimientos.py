"""Rutas de ingresos, egresos e historial (RF-04, RF-05, RF-14, RF-16). Todas exigen sesión.

    GET  /api/movimientos                    -> 200 {movimientos: [...]}   historial, del más reciente al más antiguo
         filtros opcionales: ?desde=2026-11-01&hasta=2026-11-30&id_cuenta=3&tipo=EGRESO
                             &id_categoria=7&estado=VIGENTE
    POST /api/movimientos                    -> 201 {movimiento}
         {tipo: "INGRESO" | "EGRESO", id_cuenta, id_categoria, monto: "50000.00",
          fecha: "2026-11-01", descripcion?}
    GET  /api/movimientos/<id>               -> 200 {movimiento}
    PUT  /api/movimientos/<id>               -> 200 {movimiento}   corregir (RN-72); el tipo no se envía
         {id_cuenta, id_categoria, monto, fecha, descripcion?}
    POST /api/movimientos/<id>/anular        -> 200 {movimiento}
    POST /api/movimientos/<id>/reactivar     -> 200 {movimiento}

Una cuenta, categoría o movimiento de otro usuario responde 404 (RN-06, CA-06).
"""

from flask import Blueprint, jsonify

from app.bd import obtener_conexion
from app.rutas import entrada
from app.servicios.movimientos import DatosMovimiento, FiltroHistorial, MovimientoServicio
from app.sesion import requiere_sesion

movimientos_bp = Blueprint("movimientos", __name__, url_prefix="/api/movimientos")

CAMPOS_DATOS = ("id_cuenta", "id_categoria", "monto", "fecha", "descripcion")


def _servicio() -> MovimientoServicio:
    return MovimientoServicio(obtener_conexion())


def _leer_datos(datos: dict) -> DatosMovimiento:
    return DatosMovimiento(
        id_cuenta=entrada.entero(datos, "id_cuenta"),
        id_categoria=entrada.entero(datos, "id_categoria"),
        monto=entrada.dinero(datos, "monto"),
        fecha=entrada.fecha(datos, "fecha"),
        descripcion=entrada.texto_opcional(datos, "descripcion"),
    )


@movimientos_bp.get("")
@requiere_sesion
def historial(id_usuario):
    filtro = FiltroHistorial(
        desde=entrada.parametro_fecha("desde"),
        hasta=entrada.parametro_fecha("hasta"),
        id_cuenta=entrada.parametro_entero("id_cuenta"),
        tipo=entrada.parametro_texto("tipo"),
        id_categoria=entrada.parametro_entero("id_categoria"),
        estado=entrada.parametro_texto("estado"),
    )
    movimientos = _servicio().historial(id_usuario, filtro)
    return jsonify(movimientos=[m.datos_publicos() for m in movimientos])


@movimientos_bp.post("")
@requiere_sesion
def registrar(id_usuario):
    datos = entrada.leer_cuerpo()
    entrada.solo_campos(datos, "tipo", *CAMPOS_DATOS)
    movimiento = _servicio().registrar(id_usuario, entrada.texto(datos, "tipo"), _leer_datos(datos))
    return jsonify(movimiento=movimiento.datos_publicos()), 201


@movimientos_bp.get("/<int:id_movimiento>")
@requiere_sesion
def ver(id_usuario, id_movimiento):
    return jsonify(movimiento=_servicio().obtener(id_usuario, id_movimiento).datos_publicos())


@movimientos_bp.put("/<int:id_movimiento>")
@requiere_sesion
def corregir(id_usuario, id_movimiento):
    datos = entrada.leer_cuerpo()
    # RN-72: el tipo no cambia; si llega, se rechaza en lugar de ignorarlo.
    entrada.solo_campos(datos, *CAMPOS_DATOS)
    movimiento = _servicio().corregir(id_usuario, id_movimiento, _leer_datos(datos))
    return jsonify(movimiento=movimiento.datos_publicos())


@movimientos_bp.post("/<int:id_movimiento>/anular")
@requiere_sesion
def anular(id_usuario, id_movimiento):
    return jsonify(movimiento=_servicio().anular(id_usuario, id_movimiento).datos_publicos())


@movimientos_bp.post("/<int:id_movimiento>/reactivar")
@requiere_sesion
def reactivar(id_usuario, id_movimiento):
    return jsonify(movimiento=_servicio().reactivar(id_usuario, id_movimiento).datos_publicos())
