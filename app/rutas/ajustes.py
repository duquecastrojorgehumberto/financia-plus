"""Rutas de ajustes de saldo (RF-17). Todas exigen sesión.

    POST /api/cuentas/<id>/ajustes   -> 201 {saldo_anterior, cuenta, ajuste}      si hubo diferencia
                                     -> 200 {saldo_anterior, cuenta, ajuste: null} si no hubo (RN-51)
         {saldo_real: "473500", motivo: "Compras no registradas", fecha?: "2026-11-20"}
    PUT  /api/ajustes/<id>           -> 200 {ajuste}   corregir la fecha y el motivo
         {fecha, motivo}

Un ajuste se anula o reactiva como cualquier movimiento: /api/movimientos/<id>/anular y /reactivar.
En el JSON del movimiento, el motivo es el campo "descripcion".
"""

from flask import Blueprint, jsonify

from app.bd import obtener_conexion
from app.rutas import entrada
from app.servicios.ajustes import AjusteServicio
from app.sesion import requiere_sesion

ajustes_bp = Blueprint("ajustes", __name__, url_prefix="/api")


@ajustes_bp.post("/cuentas/<int:id_cuenta>/ajustes")
@requiere_sesion
def ajustar(id_usuario, id_cuenta):
    datos = entrada.leer_cuerpo()
    entrada.solo_campos(datos, "saldo_real", "motivo", "fecha")
    resultado = AjusteServicio(obtener_conexion()).ajustar(
        id_usuario, id_cuenta, entrada.dinero(datos, "saldo_real"), entrada.texto(datos, "motivo"),
        entrada.fecha_opcional(datos, "fecha"))
    codigo = 201 if resultado.ajuste is not None else 200
    return jsonify(resultado.datos_publicos()), codigo


@ajustes_bp.put("/ajustes/<int:id_ajuste>")
@requiere_sesion
def corregir(id_usuario, id_ajuste):
    datos = entrada.leer_cuerpo()
    # El monto no se corrige: salió de un cálculo. Si llega, se rechaza.
    entrada.solo_campos(datos, "fecha", "motivo")
    ajuste = AjusteServicio(obtener_conexion()).corregir(
        id_usuario, id_ajuste, entrada.fecha(datos, "fecha"), entrada.texto(datos, "motivo"))
    return jsonify(ajuste=ajuste.datos_publicos())
